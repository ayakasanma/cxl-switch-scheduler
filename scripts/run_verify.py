#!/usr/bin/env python3
"""Fail-fast lint / pytest / cocotb runner for the controlled CXL scheduler milestones.

Invoke through scripts/run_verify.sh (WSL, after ``source scripts/wsl_env.sh``).

Every step is a real tool invocation whose exit code AND result file are checked:

* lint    : ``verilator --lint-only -Wall -Wpedantic -Werror-IMPLICIT``. No ``-Wno-*`` of any
            kind; a non-zero exit or any ``%Warning``/``%Error`` line in the log is a FAIL.
* pytest  : JUnit XML must exist, tests > 0, failures == errors == skipped == 0, exit code 0.
* cocotb  : Verilator build + run. Results XML must exist, tests > 0 (and equal to the declared
            ``expect_tests`` when given), failures == errors == skipped == 0, every process exit
            code 0, and the seed recorded in the XML must equal the requested seed.
* elab_reject : NEGATIVE elaboration check, a separate step kind. The same strict lint command is
            run on a configuration that must NOT elaborate (an unimplemented policy of
            switch_top). The step is satisfied only by a non-zero exit AND exactly one USERFATAL
            with the declared intentional message AND no diagnostic other than the declared
            consequences of the absent logic. Its status is XREJECT ("expected rejection - not a
            simulation pass"); it never has a test count and adds nothing to the test totals.
            With ``expect_undriven``/``expect_unused`` the reported pin sets must match exactly.
* elab_probe : structural control. The exact cocotb simulation-build verilate command (strict
            flags, diagnostics fatal) for a configuration, followed by its ``elab_checks`` on the
            generated model; no make, no simulation, never a test. Used for the FCFS positive
            metadata controls next to the RR absence checks.
* scope   : full-scope gate of a primary random-regression milestone (``primary_scope``). FAILS
            unless every declared (N, seed) run passed with the declared measured length, no
            ``--seeds`` override and no ``--lint-only`` were used, and each run's metrics JSON
            carries the trace SHA-256 that the runner regenerates independently. With
            ``reference_hashes`` the regenerated hash must also equal the tracked record (TSV)
            exactly, and the record must cover exactly the declared matrix; ``expect_fields``
            pins further metrics fields (e.g. policy). Never a test.
            ``run_scope`` (M5-stress / M5-production) is the analogous gate over an (N, FAI_W,
            seed) matrix: every run PASS, exact requested/measured cycles, no smoke label, nothing
            outstanding after the drain, the TB's closed-window count (exactly cycles // W and
            >= ``min_windows`` for production) and, where declared, all 16 Main transitions.

Timeouts: each command has a timeout (default STEP_TIMEOUT_S); a cocotb entry may declare its own
``timeout_s`` for the simulation process (long stress / production runs), ``--cocotb-timeout``
overrides it. A timeout kills the process and FAILS the step (exit 124).

Infrastructure smoke (``--infra-smoke --cycles C [--n-src ..] [--seeds ..]``, only for scopes that
declare ``smoke_env``): runs the scope's harness with C cycles instead of its declared length and
exports CXL_INFRA_SMOKE=1 to the test. The result is labelled INFRA_SMOKE_PASS / INFRA_SMOKE_FAIL,
``milestone_acceptance_scope`` is false, scope gates are not evaluated and the evidence goes to
artifacts/implementation/<milestone>-infra-smoke/. It is never milestone evidence; it exists to
measure throughput / memory for planning the real runs.

Per-run result files a cocotb test writes into its run directory (``artifacts``: trace hashes,
metrics JSON) are copied into ``results/`` of the evidence directory; a required file that is
missing fails the step.

A missing or empty XML is a FAIL. The runner stops at the first failing step (remaining steps are
recorded as NOT_RUN) unless ``--keep-going`` is given; either way a failure gives exit status 1.

Simulation-build warning policy: the cocotb build uses exactly the lint strictness
(``-Wall -Wpedantic -Werror-IMPLICIT``, warnings fatal) plus the flags cocotb needs
(``--vpi --public-flat-rw``). SIM_BUILD_RELAXATIONS below is the single place where a relaxation
for the simulation build may be declared; it is empty, i.e. nothing is relaxed.

Evidence: artifacts/implementation/<milestone>/<run-id>/ (never deleted by this script).
Build directories: ${CXL_BUILD_ROOT:-$HOME/.cache/cxl-scheduler/build}/<milestone>/<run-id>/<job>.
Git is used read-only (rev-parse / status).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

FROZEN_SPEC_COMMIT = "1af80967bbc2fb83224f4725c4fb450889e69c62"

LINT_FLAGS = ["--lint-only", "-Wall", "-Wpedantic", "-Werror-IMPLICIT"]
SIM_STRICT_FLAGS = ["-Wall", "-Wpedantic", "-Werror-IMPLICIT"]
# Verilator warnings relaxed for the SIMULATION build only, as (flag, reason). Lint is never
# relaxed. Keep this empty unless a relaxation is unavoidable, and report every entry.
SIM_BUILD_RELAXATIONS: List[tuple] = []
SIM_TIMESCALE = "1ns/1ps"
STEP_TIMEOUT_S = 3600

# --------------------------------------------------------------------------------------------
# Declarative milestone table.
#
# Later serial milestones append entries here. Each implemented entry has:
#   lint   : list of {name, top, filelist, params}
#   elab_reject : list of {name, top, filelist, params, expect_message, allowed_undriven,
#                          allowed_unused}  (negative elaboration checks, see the file header)
#   elab_probe  : list of {name, top, filelist, params, elab_checks}  (structural controls)
#   pytest : list of {name, target, min_tests}
#   cocotb : list of {name, top, filelist, params, default_params, test_dir, test_module, seeds,
#                     env, expect_tests, elab_checks}
# ``params`` become -G<NAME>=<value> and are exported to cocotb tests as CXL_PARAM_<NAME>.
# ``default_params`` are NOT passed to Verilator (the RTL default applies); they are only exported
# as CXL_PARAM_<NAME> so the test can verify on the DUT that the default has the expected value.
# ``seeds`` expands to one independent job (own build directory) per seed.
# ``elab_checks`` are source-of-truth checks on the Verilated model of that exact parameter set:
#   {glob, pattern, expect: "present"|"absent", why}.
# An entry with "implemented": False (or a name missing from the table) makes the runner exit
# non-zero; it can never pass silently. Integrated milestones are expected to add one cocotb entry
# per policy and N (4/8/16) and a separate long random-regression milestone entry.
# --------------------------------------------------------------------------------------------

# Only TS_EN is overridden with -G. DEPTH/DESC_W/TS_W stay at their RTL defaults, which come from
# cxl_sched_pkg: overriding them on the command line leaves the package constants L_FIFO_DEPTH,
# L_DESC_W and L_TS_W unreferenced and strict lint then (correctly) reports UNUSEDPARAM. The
# baseline values are still exported to the tests, which verify them on the DUT pins.
_FIFO_PARAMS_TS0 = {"TS_EN": 0}
_FIFO_PARAMS_TS1 = {"TS_EN": 1}
_FIFO_DEFAULTS = {"DEPTH": 16, "DESC_W": 105, "TS_W": 32}
_M1_SEEDS = [509, 510, 511, 512, 513]
_GENERATED = "Vtop*.h"
# Pinned pytest counts. refc/tests = 54 (FIFO/common/FCFS models) + 39 RR model tests (d09db33)
# + 103 FAI Main model tests (M5, refc/tests/test_fai_main_model.py) = 196, + 45 FAI Algorithm-2
# model tests (M6, refc/tests/test_fai_alg2_model.py; actual collection) = 241; a different count
# (e.g. silently uncollected RR or FAI tests) FAILS. sim/common/tests = 23 (input hold, traffic
# trace, tag responses; d09db33) + 16 M5 tests of the pure-Python FAI stress/production stimulus and
# streaming-statistics helpers (sim/common/tests/test_fai_stream.py) = 39. Every milestone that runs
# the full sim/common/tests collection (M3, M4, M5) pins this actual total.
_REFC_EXPECT_TESTS = 241
_TB_UTILS_EXPECT_TESTS = 45

# ----- M2 ---------------------------------------------------------------------------------------
# Fixture (sim-only, real cxl_desc_fifo x N + real cxl_out_hold): one configuration per N. CTX_W
# and TS_EN are fixture parameters with literal defaults, so overriding them is lint-clean. N=16
# uses CTX_W=1, the width switch_top currently instantiates; N=8 also enables arrival metadata.
_M2_SEEDS = [509, 510, 511, 512, 513]
_FIXTURE_CONFIGS = [
    {"N_SRC": 4, "CTX_W": 4, "TS_EN": 0},
    {"N_SRC": 8, "CTX_W": 6, "TS_EN": 1},
    {"N_SRC": 16, "CTX_W": 1, "TS_EN": 0},
]
_FIXTURE_DEFAULTS = {"DEPTH": 16, "DESC_W": 105, "TS_W": 32}
_FIXTURE_FILELIST = "sim/cxl_common_ctrl/filelist_fixture.f"
_FIXTURE_EXPECT_TESTS = 15
# Standalone hold controller (top = cxl_out_hold, test-driven heads). DESC_W stays at its
# package default (see the UNUSEDPARAM note above) and is exported to the test for a pin check.
_HOLD_CONFIGS = [
    {"N_SRC": 4, "CTX_W": 5},
    {"N_SRC": 8, "CTX_W": 1},
    {"N_SRC": 16, "CTX_W": 3},
]
_HOLD_DEFAULTS = {"DESC_W": 105}
_HOLD_EXPECT_TESTS = 7
_POLICY_NAMES = ["POLICY_FCFS", "POLICY_RR", "POLICY_FAI_MAIN", "POLICY_FAI_ALG2"]
# M3: POLICY_FCFS (0) is implemented; M4: POLICY_RR (1) is implemented; M5: POLICY_FAI_MAIN (2)
# is implemented; M6: the supplementary POLICY_FAI_ALG2 (3, spec 8.6) is implemented. All four
# encodings of cxl_sched_pkg::policy_e therefore elaborate. Until M6 every milestone that linted
# several switch_top policies (M2..M5) carried 3 XREJECT for the then-unimplemented POLICY=3; since
# M6 that stale rejection is REPLACED by the strict rejection of the first value outside policy_e,
# POLICY=4 (switch_top default branch: "is not a cxl_sched_pkg::policy_e encoding"), again at
# N4/8/16 = 3 XREJECT with exact diagnostics. POLICY=3 now gets strict positive lint/probes in M6.
_UNKNOWN_POLICIES = [4]
# Pins of the absent policy-slot part B of switch_top: exactly these signals, and nothing else, are
# reported undriven / unused while the selected policy branch is an intentional $fatal. Since M3
# the arrival timestamp (policy-slot part A) is always driven (counter for FCFS/FAI, '0 for RR and
# unknown encodings), so arrival_ts is no longer undriven. M4/M5 derived this set from the actual
# Verilator output of the then-$fatal POLICY=3 branch; M6 re-derived it from the actual output of
# POLICY=4 N4/8/16 (TS_EN=0, default branch) with both FAI branches present: identical, 1 USERFATAL
# + these 3 undriven + these 6 unused, "Exiting due to 10 warning(s)".
_SLOT_UNDRIVEN = ["cand_valid", "cand_source", "cand_ctx"]
_SLOT_UNUSED = ["head_ts", "fifo_count", "push", "grant_ctx", "grant_held", "fire"]
_SWITCH_FILELIST = "rtl/filelist_switch.f"
_SWITCH_DEFAULTS = {"DEPTH": 16, "DESC_W": 105, "TS_W": 32}


def _hold_lint(params: dict) -> dict:
    return {
        "name": f"cxl_out_hold_n{params['N_SRC']}_ctx{params['CTX_W']}",
        "top": "cxl_out_hold",
        "filelist": "rtl/filelist_common.f",
        "params": params,
    }


def _fixture_lint(params: dict) -> dict:
    return {
        "name": f"cxl_common_ctrl_fixture_n{params['N_SRC']}",
        "top": "cxl_common_ctrl_fixture",
        "filelist": _FIXTURE_FILELIST,
        "params": params,
    }


def _switch_reject(n_src: int, policy: int) -> dict:
    return {
        "name": f"switch_top_n{n_src}_policy{policy}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": policy},
        "expect_message": f"switch_top: POLICY={policy} is not a cxl_sched_pkg::policy_e encoding",
        "allowed_undriven": _SLOT_UNDRIVEN,
        "allowed_unused": _SLOT_UNUSED,
        # exact sets: every declared consequence must actually be reported, once
        "expect_undriven": _SLOT_UNDRIVEN,
        "expect_unused": _SLOT_UNUSED,
    }


def _switch_rejects() -> List[dict]:
    return [_switch_reject(n, policy) for n in (4, 8, 16) for policy in _UNKNOWN_POLICIES]


def _switch_fcfs_lint(n_src: int) -> dict:
    return {
        "name": f"switch_top_n{n_src}_fcfs",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 0},
    }


def _fcfs_sel_lint(n_src: int) -> dict:
    return {
        "name": f"cxl_fcfs_sel_n{n_src}",
        "top": "cxl_fcfs_sel",
        "filelist": "rtl/filelist_common.f",
        "params": {"N_SRC": n_src},
    }


def _switch_rr_lint(n_src: int, quantum: Optional[int] = None) -> dict:
    """switch_top POLICY=1. ``quantum`` None = the RTL default RR_QUANTUM (10, the primary value)."""
    params = {"N_SRC": n_src, "POLICY": 1}
    if quantum is not None:
        params["RR_QUANTUM"] = quantum
    return {
        "name": f"switch_top_n{n_src}_rr" + ("" if quantum is None else f"_q{quantum}"),
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": params,
    }


def _rr_sched_lint(n_src: int, quantum: int) -> dict:
    return {
        "name": f"cxl_rr_sched_n{n_src}_q{quantum}",
        "top": "cxl_rr_sched",
        "filelist": "rtl/filelist_common.f",
        "params": {"N_SRC": n_src, "QUANTUM": quantum},
    }


# ----- M3 ---------------------------------------------------------------------------------------
_M3_SEEDS = [509, 510, 511, 512, 513]
_M3_SEL_EXPECT_TESTS = 7
_M3_SWITCH_EXPECT_TESTS = 14  # 13 + test_14_measurement_boundary_input_hold (C1 regression)
# Primary FCFS random regression (spec 9): 20 seeds 509..528 x N 4/8/16 x 100,000 cycles = 60 runs.
_PRIMARY_SEEDS = list(range(509, 529))
_PRIMARY_CYCLES = 100000
_PRIMARY_METRICS = "fcfs_primary_metrics.json"


def _switch_fcfs_elab_checks() -> List[dict]:
    return [
        {
            "glob": _GENERATED,
            "pattern": r"arrival_cnt_q",
            "expect": "present",
            "why": "FCFS: the shared 32-bit arrival counter is in the Verilated model (spec 6)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"ts_mem_q",
            "expect": "present",
            "why": "FCFS: per-entry timestamp storage exists (spec 6, 11)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"held_source_q",
            "expect": "present",
            "why": "control: the common hold controller state is in the model",
        },
        {
            "glob": _GENERATED,
            "pattern": r"u_fcfs_sel",
            "expect": "present",
            "why": "FCFS: the shared oldest-head selector instance is in the model",
        },
    ]


def _fcfs_sel_cocotb(n_src: int) -> dict:
    return {
        "name": f"cxl_fcfs_sel_n{n_src}",
        "top": "cxl_fcfs_sel",
        "filelist": "rtl/filelist_common.f",
        "params": {"N_SRC": n_src},
        "default_params": {"TS_W": 32},
        "test_dir": "sim/cxl_fcfs_sel",
        "test_module": "test_cxl_fcfs_sel",
        "seeds": _M3_SEEDS,
        "env": {},
        "expect_tests": _M3_SEL_EXPECT_TESTS,
        "elab_checks": [
            {
                "glob": _GENERATED,
                "pattern": r"i_eligible",
                "expect": "present",
                "why": "control: the selector ports are in the Verilated model",
            },
        ],
    }


def _switch_fcfs_cocotb(n_src: int) -> dict:
    return {
        "name": f"switch_top_fcfs_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 0},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fcfs",
        "test_module": "test_switch_fcfs",
        "seeds": _M3_SEEDS,
        "env": {},
        "expect_tests": _M3_SWITCH_EXPECT_TESTS,
        "elab_checks": _switch_fcfs_elab_checks(),
        "artifacts": [{"file": "fcfs_short_random.json", "required": True}],
    }


def _switch_fcfs_primary_cocotb(n_src: int) -> dict:
    return {
        "name": f"switch_top_fcfs_primary_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 0},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fcfs",
        "test_module": "test_switch_fcfs_primary",
        "seeds": _PRIMARY_SEEDS,
        "env": {"CXL_PRIMARY_CYCLES": _PRIMARY_CYCLES},
        "expect_tests": 1,
        "elab_checks": _switch_fcfs_elab_checks(),
        "artifacts": [{"file": _PRIMARY_METRICS, "required": True}],
    }


# ----- M4 ---------------------------------------------------------------------------------------
# RR: directed + short random unit scope with the M3 seed set; quantum 10 (primary) uses the RTL
# default RR_QUANTUM (not passed with -G, exported to the test which proves 10 by exact-quota
# checks); quantum 1 (supplementary, D32) is passed with -G and lives in the separate M4-q1 scope.
_M4_SEEDS = [509, 510, 511, 512, 513]
_M4_SWITCH_EXPECT_TESTS = 13
_RR_QUANTUM_PRIMARY = 10
_RR_QUANTUM_SUPP = 1
_RR_PRIMARY_METRICS = "rr_primary_metrics.json"
# The FCFS primary intended traces, recorded verbatim at M3 (Codex review): M4 must replay them.
_PRIMARY_REFERENCE_HASHES = "reviews/evidence/M3-primary-v2-trace-hashes.tsv"


def _switch_rr_elab_checks() -> List[dict]:
    # The absence patterns are exactly the names that the FCFS positive controls show PRESENT
    # (M3 FCFS cocotb elab_checks and the M4 FCFS elab_probe steps), so absence is meaningful.
    return [
        {
            "glob": _GENERATED,
            "pattern": r"arrival_cnt_q",
            "expect": "absent",
            "why": "RR: no arrival counter (spec 6, 7: RR excludes unused arrival metadata)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"ts_mem_q",
            "expect": "absent",
            "why": "RR: no per-entry timestamp storage (spec 6, 7, 11)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"u_fcfs_sel",
            "expect": "absent",
            "why": "RR: no oldest-head timestamp selector (spec 6, 7)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"u_rr_sched__DOT__ptr_q",
            "expect": "present",
            "why": "RR state: polling pointer is in the Verilated model",
        },
        {
            "glob": _GENERATED,
            "pattern": r"u_rr_sched__DOT__used_q",
            "expect": "present",
            "why": "RR state: used quota of the current turn is in the Verilated model",
        },
        {
            "glob": _GENERATED,
            "pattern": r"desc_mem_q",
            "expect": "present",
            "why": "control: the common 105-bit descriptor storage is in the model (spec 3, 11)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"held_source_q",
            "expect": "present",
            "why": "control: the common hold controller state is in the model",
        },
    ]


def _switch_fcfs_probe(n_src: int) -> dict:
    """FCFS positive structural control in the RR milestones: the same verilate command as a
    cocotb build, checked only (no make, no simulation, no test)."""
    return {
        "name": f"switch_top_fcfs_n{n_src}_metadata_control",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 0},
        "elab_checks": _switch_fcfs_elab_checks()
        + [
            {
                "glob": _GENERATED,
                "pattern": r"u_rr_sched",
                "expect": "absent",
                "why": "FCFS: no RR policy block",
            },
        ],
    }


def _switch_rr_cocotb(n_src: int, quantum: int) -> dict:
    params = {"N_SRC": n_src, "POLICY": 1}
    defaults = dict(_SWITCH_DEFAULTS)
    if quantum == _RR_QUANTUM_PRIMARY:
        defaults["RR_QUANTUM"] = quantum  # RTL default, not overridden
    else:
        params["RR_QUANTUM"] = quantum
    return {
        "name": f"switch_top_rr_q{quantum}_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": params,
        "default_params": defaults,
        "test_dir": "sim/switch_top_rr",
        "test_module": "test_switch_rr",
        "seeds": _M4_SEEDS,
        "env": {},
        "expect_tests": _M4_SWITCH_EXPECT_TESTS,
        "elab_checks": _switch_rr_elab_checks(),
        "artifacts": [{"file": "rr_short_random.json", "required": True}],
    }


def _switch_rr_primary_cocotb(n_src: int) -> dict:
    return {
        "name": f"switch_top_rr_primary_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 1},
        "default_params": {**_SWITCH_DEFAULTS, "RR_QUANTUM": _RR_QUANTUM_PRIMARY},
        "test_dir": "sim/switch_top_rr",
        "test_module": "test_switch_rr_primary",
        "seeds": _PRIMARY_SEEDS,
        "env": {"CXL_PRIMARY_CYCLES": _PRIMARY_CYCLES},
        "expect_tests": 1,
        "elab_checks": _switch_rr_elab_checks(),
        "artifacts": [{"file": _RR_PRIMARY_METRICS, "required": True}],
    }


# ----- M5 ---------------------------------------------------------------------------------------
# FAI-inspired Main (POLICY=2, spec 8.1-8.5, docs/phase-3-uarch/fai_main.md). Four separate scopes:
#   M5            : directed + short random UNIT scope, N4/8/16 x stress windows FAI_W 64 and 256
#                   (passed with -G), seeds 509..513, 19 tests per job; production W=5,000,000
#                   (the RTL default) is linted and structurally probed.
#   M5-stress     : long random W64 / W256 regressions, N4/8/16 x seeds 509..513 (30 runs), every
#                   cycle checked; cycle counts below give 6,250 nominal W64 windows and 3,125
#                   nominal W256 windows per run (resets restart the window; the test requires >= 80 %
#                   of the nominal count to close and all 16 transitions).
#   M5-primary    : primary random regression at the production window, N4/8/16 x seeds 509..528 x
#                   100,000 measured cycles = 60 runs on the M3 intended traces (tracked hashes). NO
#                   window closes in 100,000 cycles (W = 5,000,000): every source stays H, so the
#                   selection is expected to equal FCFS; this does NOT prove window adaptation.
#   M5-production : production W = 5,000,000 (RTL default, not passed with -G), N4/8/16, one run per N
#                   of _PRODUCTION_CYCLES real non-reset cycles = 4 complete windows (>= 3 required,
#                   spec 9), actual simulated edges: no time skip, no state deposit/preload, every
#                   cycle checked by the oracle + independent pin/history layers with bounded memory.
_M5_SEEDS = [509, 510, 511, 512, 513]
_M5_SWITCH_EXPECT_TESTS = 19
_FAI_W_STRESS = [64, 256]
_FAI_W_PRODUCTION = 5000000
_HELD_CTX_RE = r"CData/\*{msb}:0\*/ switch_top__DOT__u_out_hold__DOT__held_ctx_q;"
# M5-stress cycle counts per window (measured trace cycles of one run; see sim/switch_top_fai/
# test_switch_fai_stress.py for the trace design). Timeouts are per simulation process.
_STRESS_SEEDS = [509, 510, 511, 512, 513]
_STRESS_CYCLES = {64: 400000, 256: 800000}
_STRESS_METRICS = "fai_stress_metrics.json"
_STRESS_TIMEOUT_S = 2 * 3600
# M5-primary: the M3/M4 primary seeds/length/profile and the tracked intended-trace record.
_FAI_PRIMARY_METRICS = "fai_primary_metrics.json"
_FAI_PRIMARY_TIMEOUT_S = 2 * 3600
# M5-production: 4 complete production windows per N (>= 3 required by spec 9).
_PRODUCTION_SEED = 509
_PRODUCTION_CYCLES = 4 * _FAI_W_PRODUCTION
_PRODUCTION_MIN_WINDOWS = 3
_PRODUCTION_METRICS = "fai_production_metrics.json"
_PRODUCTION_TIMEOUT_S = 8 * 3600


def _switch_fai_lint(n_src: int, fai_w: Optional[int] = None) -> dict:
    """switch_top POLICY=2. ``fai_w`` None = the RTL default FAI_W (5,000,000, production)."""
    params = {"N_SRC": n_src, "POLICY": 2}
    if fai_w is not None:
        params["FAI_W"] = fai_w
    return {
        "name": f"switch_top_n{n_src}_fai" + ("" if fai_w is None else f"_w{fai_w}"),
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": params,
    }


def _fai_sched_lint(n_src: int, window: int) -> dict:
    return {
        "name": f"cxl_fai_main_sched_n{n_src}_w{window}",
        "top": "cxl_fai_main_sched",
        "filelist": "rtl/filelist_common.f",
        "params": {"N_SRC": n_src, "W": window},
    }


def _held_ctx_check(bits: int, why: str) -> dict:
    return {
        "glob": _GENERATED,
        "pattern": _HELD_CTX_RE.format(msb=bits - 1),
        "expect": "present",
        "why": why,
    }


def _switch_fai_elab_checks() -> List[dict]:
    fai = "switch_top__DOT__gen_policy_fai_main__DOT__u_fai_sched__DOT__"
    checks = [
        {
            "glob": _GENERATED,
            "pattern": r"arrival_cnt_q",
            "expect": "present",
            "why": "FAI: the shared 32-bit arrival counter is in the Verilated model (spec 6)",
        },
        {
            "glob": _GENERATED,
            "pattern": r"ts_mem_q",
            "expect": "present",
            "why": "FAI: per-entry arrival timestamp storage exists (spec 6, fai_main.md 1)",
        },
        {
            "glob": _GENERATED,
            "pattern": fai + r"u_fcfs_sel",
            "expect": "present",
            "why": "FAI: the shared oldest-head selector is instantiated inside the FAI block",
        },
        {
            "glob": _GENERATED,
            "pattern": r"u_rr_sched",
            "expect": "absent",
            "why": "FAI: no RR policy block",
        },
        _held_ctx_check(5, "FAI: the common hold controller carries the 5-bit {class, used} context"),
    ]
    for reg in ("cls_q", "idx_q", "b_q", "s_q", "turn_q", "used_q"):
        checks.append(
            {
                "glob": _GENERATED,
                "pattern": fai + reg + ";",
                "expect": "present",
                "why": f"FAI Main state register {reg} is in the Verilated model (fai_main.md 2)",
            }
        )
    return checks


def _switch_fai_probe(n_src: int) -> dict:
    """FAI positive structural control (production default W): verilate only, no test."""
    return {
        "name": f"switch_top_fai_n{n_src}_metadata_control",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 2},
        "elab_checks": _switch_fai_elab_checks(),
    }


def _switch_fcfs_probe_m5(n_src: int) -> dict:
    """M5 FCFS control: the M4 FCFS probe plus the unchanged 1-bit hold context, no FAI block."""
    probe = _switch_fcfs_probe(n_src)
    probe["name"] = f"switch_top_fcfs_n{n_src}_ctx_control"
    probe["elab_checks"] = probe["elab_checks"] + [
        _held_ctx_check(1, "FCFS keeps the 1-bit (constant 0) hold context"),
        {"glob": _GENERATED, "pattern": r"u_fai_sched", "expect": "absent", "why": "FCFS: no FAI policy block"},
    ]
    return probe


def _switch_rr_probe_m5(n_src: int) -> dict:
    """M5 RR control: still no arrival metadata / selector, 1-bit hold context, no FAI block."""
    return {
        "name": f"switch_top_rr_n{n_src}_ctx_control",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 1},
        "elab_checks": _switch_rr_elab_checks()
        + [
            _held_ctx_check(1, "RR keeps the 1-bit (constant 0) hold context"),
            {"glob": _GENERATED, "pattern": r"u_fai_sched", "expect": "absent", "why": "RR: no FAI policy block"},
        ],
    }


def _switch_fai_cocotb(n_src: int, fai_w: int) -> dict:
    return {
        "name": f"switch_top_fai_w{fai_w}_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 2, "FAI_W": fai_w},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fai",
        "test_module": "test_switch_fai",
        "seeds": _M5_SEEDS,
        "env": {},
        "expect_tests": _M5_SWITCH_EXPECT_TESTS,
        "elab_checks": _switch_fai_elab_checks(),
        "artifacts": [{"file": "fai_short_random.json", "required": True}],
    }


def _switch_fai_stress_cocotb(n_src: int, fai_w: int, policy: int = 2) -> dict:
    alg2 = policy == 3
    return {
        "name": f"switch_top_fai{'_alg2' if alg2 else ''}_stress_w{fai_w}_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": policy, "FAI_W": fai_w},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fai",
        "test_module": "test_switch_fai_stress",
        "seeds": _STRESS_SEEDS,
        "env": {"CXL_STRESS_CYCLES": _STRESS_CYCLES[fai_w]},
        "expect_tests": 1,
        "timeout_s": _STRESS_TIMEOUT_S,
        "elab_checks": _switch_fai_alg2_elab_checks() if alg2 else _switch_fai_elab_checks(),
        "artifacts": [{"file": "fai_alg2_stress_metrics.json" if alg2 else _STRESS_METRICS, "required": True}],
    }


def _switch_fai_primary_cocotb(n_src: int) -> dict:
    return {
        "name": f"switch_top_fai_primary_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 2},
        "default_params": {**_SWITCH_DEFAULTS, "FAI_W": _FAI_W_PRODUCTION},
        "test_dir": "sim/switch_top_fai",
        "test_module": "test_switch_fai_primary",
        "seeds": _PRIMARY_SEEDS,
        "env": {"CXL_PRIMARY_CYCLES": _PRIMARY_CYCLES},
        "expect_tests": 1,
        "timeout_s": _FAI_PRIMARY_TIMEOUT_S,
        "elab_checks": _switch_fai_elab_checks(),
        "artifacts": [{"file": _FAI_PRIMARY_METRICS, "required": True}],
    }


def _switch_fai_production_cocotb(n_src: int, policy: int = 2) -> dict:
    alg2 = policy == 3
    return {
        "name": f"switch_top_fai{'_alg2' if alg2 else ''}_production_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        # FAI_W is NOT passed with -G: the RTL default (5,000,000) is the configuration under test;
        # the test proves it on the DUT (23-bit index/B/S widths and the closing positions).
        "params": {"N_SRC": n_src, "POLICY": policy},
        "default_params": {**_SWITCH_DEFAULTS, "FAI_W": _FAI_W_PRODUCTION},
        "test_dir": "sim/switch_top_fai",
        "test_module": "test_switch_fai_production",
        "seeds": [_PRODUCTION_SEED],
        "env": {"CXL_PRODUCTION_CYCLES": _PRODUCTION_CYCLES},
        "expect_tests": 1,
        "timeout_s": _PRODUCTION_TIMEOUT_S,
        "elab_checks": _switch_fai_alg2_elab_checks() if alg2 else _switch_fai_elab_checks(),
        "artifacts": [{"file": "fai_alg2_production_metrics.json" if alg2 else _PRODUCTION_METRICS, "required": True}],
    }


def _fai_lints_all() -> List[dict]:
    """Strict positive lint of every supported Main configuration: switch_top POLICY=2 and the
    standalone cxl_fai_main_sched, N4/8/16 x FAI_W 64 / 256 / 5,000,000 (switch_top: the RTL
    default, not passed with -G)."""
    return (
        [_switch_fai_lint(n, w) for w in _FAI_W_STRESS for n in (4, 8, 16)]
        + [_switch_fai_lint(n) for n in (4, 8, 16)]
        + [_fai_sched_lint(n, w) for w in _FAI_W_STRESS + [_FAI_W_PRODUCTION] for n in (4, 8, 16)]
    )


# ----- M6 ---------------------------------------------------------------------------------------
# Supplementary FAI Algorithm-2 (POLICY=3, spec 8.6, docs/phase-3-uarch/fai_alg2.md): the same
# cxl_fai_main_sched with INTERP=1 in switch_top gen_policy_fai_alg2. Initial supplementary scope
# is N4 (spec 8.5/8.6): directed + short random cocotb at the stress windows W64/W256 x seeds
# 509..513, plus a production-parameter SMOKE (RTL default W=5,000,000, no window closes). N8/16
# get strict positive lint and structural probes only (no supplementary experiments).
_M6_SEEDS = [509, 510, 511, 512, 513]
_M6_ALG2_EXPECT_TESTS = 16
_M6_SMOKE_SEED = 509
_M6_SMOKE_CYCLES = 20000
_FAI_INTERP_ALG2 = 1


def _switch_fai_alg2_lint(n_src: int, fai_w: Optional[int] = None) -> dict:
    """switch_top POLICY=3. ``fai_w`` None = the RTL default FAI_W (5,000,000, production)."""
    params = {"N_SRC": n_src, "POLICY": 3}
    if fai_w is not None:
        params["FAI_W"] = fai_w
    return {
        "name": f"switch_top_n{n_src}_fai_alg2" + ("" if fai_w is None else f"_w{fai_w}"),
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": params,
    }


def _fai_sched_alg2_lint(n_src: int, window: int) -> dict:
    return {
        "name": f"cxl_fai_main_sched_alg2_n{n_src}_w{window}",
        "top": "cxl_fai_main_sched",
        "filelist": "rtl/filelist_common.f",
        "params": {"N_SRC": n_src, "W": window, "INTERP": _FAI_INTERP_ALG2},
    }


def _fai_alg2_lints_all() -> List[dict]:
    return (
        [_switch_fai_alg2_lint(n, w) for w in _FAI_W_STRESS for n in (4, 8, 16)]
        + [_switch_fai_alg2_lint(n) for n in (4, 8, 16)]
        + [_fai_sched_alg2_lint(n, w) for w in _FAI_W_STRESS + [_FAI_W_PRODUCTION] for n in (4, 8, 16)]
    )


def _fai_interp_reject() -> dict:
    """cxl_fai_main_sched with an unsupported interpretation selector: rejected for that reason only
    (standalone block, no other consequence: exactly 1 USERFATAL, nothing undriven / unused)."""
    return {
        "name": "cxl_fai_main_sched_interp2",
        "top": "cxl_fai_main_sched",
        "filelist": "rtl/filelist_common.f",
        "params": {"INTERP": 2},
        "expect_message": "cxl_fai_main_sched: INTERP=2 is not supported (0 Main, 1 Algorithm-2)",
        "allowed_undriven": [],
        "allowed_unused": [],
        "expect_undriven": [],
        "expect_unused": [],
    }


def _switch_fai_alg2_elab_checks() -> List[dict]:
    fai = "switch_top__DOT__gen_policy_fai_alg2__DOT__u_fai_sched__DOT__"
    checks = [
        {"glob": _GENERATED, "pattern": r"arrival_cnt_q", "expect": "present",
         "why": "FAI_ALG2: the shared 32-bit arrival counter is in the Verilated model (spec 6)"},
        {"glob": _GENERATED, "pattern": r"ts_mem_q", "expect": "present",
         "why": "FAI_ALG2: per-entry arrival timestamp storage exists (spec 6, fai_alg2.md 1)"},
        {"glob": _GENERATED, "pattern": fai + r"u_fcfs_sel", "expect": "present",
         "why": "FAI_ALG2: the shared oldest-head selector is instantiated inside the FAI block"},
        {"glob": _GENERATED, "pattern": r"gen_policy_fai_main", "expect": "absent",
         "why": "FAI_ALG2: separate selection, the Main branch is not elaborated"},
        {"glob": _GENERATED, "pattern": r"u_rr_sched", "expect": "absent", "why": "FAI_ALG2: no RR policy block"},
        _held_ctx_check(5, "FAI_ALG2: the unchanged common hold controller carries the same 5-bit context"),
    ]  # fmt: skip
    for reg in ("cls_q", "idx_q", "b_q", "s_q", "turn_q", "used_q"):
        checks.append(
            {
                "glob": _GENERATED,
                "pattern": fai + reg + ";",
                "expect": "present",
                "why": f"FAI_ALG2 state register {reg} is in the Verilated model (fai_alg2.md 2)",
            }
        )
    return checks


def _switch_fai_alg2_probe(n_src: int) -> dict:
    """FAI_ALG2 positive structural control (production default W): verilate only, no test."""
    return {
        "name": f"switch_top_fai_alg2_n{n_src}_metadata_control",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 3},
        "elab_checks": _switch_fai_alg2_elab_checks(),
    }


def _switch_fai_alg2_cocotb(n_src: int, fai_w: int) -> dict:
    return {
        "name": f"switch_top_fai_alg2_w{fai_w}_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": n_src, "POLICY": 3, "FAI_W": fai_w},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fai_alg2",
        "test_module": "test_switch_fai_alg2",
        "seeds": _M6_SEEDS,
        "env": {},
        "expect_tests": _M6_ALG2_EXPECT_TESTS,
        "elab_checks": _switch_fai_alg2_elab_checks(),
        "artifacts": [
            {"file": "fai_alg2_short_random.json", "required": True},
            {"file": "fai_alg2_class_dynamics.json", "required": True},
        ],
    }


def _switch_fai_alg2_smoke_cocotb(n_src: int) -> dict:
    return {
        "name": f"switch_top_fai_alg2_production_smoke_n{n_src}",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        # FAI_W is NOT passed with -G: the RTL default (5,000,000) is the configuration under test.
        "params": {"N_SRC": n_src, "POLICY": 3},
        "default_params": {**_SWITCH_DEFAULTS, "FAI_W": _FAI_W_PRODUCTION},
        "test_dir": "sim/switch_top_fai_alg2",
        "test_module": "test_switch_fai_alg2_production_smoke",
        "seeds": [_M6_SMOKE_SEED],
        "env": {"CXL_SMOKE_CYCLES": _M6_SMOKE_CYCLES},
        "expect_tests": 1,
        "elab_checks": _switch_fai_alg2_elab_checks(),
        "artifacts": [{"file": "fai_alg2_production_smoke.json", "required": True}],
    }


# M6-compare: Main (POLICY=2) and Algorithm-2 (POLICY=3) replay the IDENTICAL intended class-dynamics
# trace (fai_stream.make_fai_stress_trace, same seed / N / length / W) with every harness layer
# active; scripts/compare_fai_interps.py then diffs the records (observations, no fairness claim).
_COMPARE_CYCLES = {64: 64000, 256: 128000}  # 1,000 / 500 nominal windows
_COMPARE_RECORD = "fai_compare_record.json"


def _switch_fai_compare_cocotb(policy: int, fai_w: int) -> dict:
    tag = {2: "main", 3: "alg2"}[policy]
    return {
        "name": f"switch_top_fai_compare_{tag}_w{fai_w}_n4",
        "top": "switch_top",
        "filelist": _SWITCH_FILELIST,
        "params": {"N_SRC": 4, "POLICY": policy, "FAI_W": fai_w},
        "default_params": _SWITCH_DEFAULTS,
        "test_dir": "sim/switch_top_fai_alg2",
        "test_module": "test_switch_fai_compare",
        "seeds": _M6_SEEDS,
        "env": {"CXL_COMPARE_CYCLES": _COMPARE_CYCLES[fai_w]},
        "expect_tests": 1,
        "elab_checks": _switch_fai_elab_checks() if policy == 2 else _switch_fai_alg2_elab_checks(),
        "artifacts": [{"file": _COMPARE_RECORD, "required": True}],
    }


def _fixture_cocotb(params: dict) -> dict:
    ts_en = bool(params["TS_EN"])
    return {
        "name": f"cxl_common_ctrl_n{params['N_SRC']}",
        "top": "cxl_common_ctrl_fixture",
        "filelist": _FIXTURE_FILELIST,
        "params": params,
        "default_params": _FIXTURE_DEFAULTS,
        "test_dir": "sim/cxl_common_ctrl",
        "test_module": "test_cxl_common_ctrl",
        "seeds": _M2_SEEDS,
        "env": {},
        "expect_tests": _FIXTURE_EXPECT_TESTS,
        "elab_checks": [
            {
                "glob": _GENERATED,
                "pattern": r"held_source_q",
                "expect": "present",
                "why": "control: the real cxl_out_hold state is in the Verilated model",
            },
            {
                "glob": _GENERATED,
                "pattern": r"desc_mem_q",
                "expect": "present",
                "why": "control: the real cxl_desc_fifo storage is in the Verilated model",
            },
            {
                "glob": _GENERATED,
                "pattern": r"ts_mem_q",
                "expect": "present" if ts_en else "absent",
                "why": "arrival-metadata storage exists exactly when TS_EN=1 (spec 6)",
            },
        ],
    }


def _hold_cocotb(params: dict) -> dict:
    return {
        "name": f"cxl_out_hold_n{params['N_SRC']}_ctx{params['CTX_W']}",
        "top": "cxl_out_hold",
        "filelist": "rtl/filelist_common.f",
        "params": params,
        "default_params": _HOLD_DEFAULTS,
        "test_dir": "sim/cxl_out_hold",
        "test_module": "test_cxl_out_hold",
        "seeds": _M2_SEEDS,
        "env": {},
        "expect_tests": _HOLD_EXPECT_TESTS,
        "elab_checks": [
            {
                "glob": _GENERATED,
                "pattern": r"held_source_q",
                "expect": "present",
                "why": "control: the held-grant registers are in the Verilated model",
            },
        ],
    }


# Status of a satisfied negative elaboration check. It is neither PASS nor a test.
XREJECT = "XREJECT"
XREJECT_LABEL = "expected rejection — not a simulation pass"
_DIAG_RE = re.compile(r"^%(Warning|Error)(?:-([A-Z0-9_]+))?: (.*)$")

MILESTONES: Dict[str, dict] = {
    "M1": {
        "description": "Descriptor package + common per-source FIFO (cxl_desc_fifo), TS_EN=0/1",
        "implemented": True,
        "lint": [
            {
                "name": "cxl_desc_fifo_ts0",
                "top": "cxl_desc_fifo",
                "filelist": "rtl/filelist_common.f",
                "params": _FIFO_PARAMS_TS0,
            },
            {
                "name": "cxl_desc_fifo_ts1",
                "top": "cxl_desc_fifo",
                "filelist": "rtl/filelist_common.f",
                "params": _FIFO_PARAMS_TS1,
            },
        ],
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
        ],
        "cocotb": [
            {
                "name": "cxl_desc_fifo_ts0",
                "top": "cxl_desc_fifo",
                "filelist": "rtl/filelist_common.f",
                "params": _FIFO_PARAMS_TS0,
                "default_params": _FIFO_DEFAULTS,
                "test_dir": "sim/cxl_desc_fifo",
                "test_module": "test_cxl_desc_fifo",
                "seeds": _M1_SEEDS,
                "env": {},
                "expect_tests": 9,
                "elab_checks": [
                    {
                        "glob": _GENERATED,
                        "pattern": r"ts_mem_q",
                        "expect": "absent",
                        "why": "TS_EN=0 must elaborate no timestamp memory (spec 6, RR)",
                    },
                    {
                        "glob": _GENERATED,
                        "pattern": r"desc_mem_q",
                        "expect": "present",
                        "why": "control: descriptor storage is visible in the same files",
                    },
                ],
            },
            {
                "name": "cxl_desc_fifo_ts1",
                "top": "cxl_desc_fifo",
                "filelist": "rtl/filelist_common.f",
                "params": _FIFO_PARAMS_TS1,
                "default_params": _FIFO_DEFAULTS,
                "test_dir": "sim/cxl_desc_fifo",
                "test_module": "test_cxl_desc_fifo",
                "seeds": _M1_SEEDS,
                "env": {},
                "expect_tests": 9,
                "elab_checks": [
                    {
                        "glob": _GENERATED,
                        "pattern": r"ts_mem_q",
                        "expect": "present",
                        "why": "control: with TS_EN=1 the timestamp memory is visible, so its "
                        "absence for TS_EN=0 is a meaningful observation",
                    },
                ],
            },
        ],
    },
    "M2": {
        "description": "Common output hold controller + common FIFO integration (sim-only "
        "candidate-injection fixture); switch_top FCFS, RR and FAI_MAIN (production default "
        "FAI_W) strict positive lint N4/8/16; unknown POLICY=4 rejected at elaboration "
        "(3 XREJECT; was POLICY=3 before M6); refc pytest pinned",
        "implemented": True,
        "lint": [_hold_lint(c) for c in _HOLD_CONFIGS]
        + [_fixture_lint(c) for c in _FIXTURE_CONFIGS]
        + [_switch_fcfs_lint(n) for n in (4, 8, 16)]
        + [_switch_rr_lint(n) for n in (4, 8, 16)]
        + [_switch_fai_lint(n) for n in (4, 8, 16)],
        "elab_reject": _switch_rejects(),
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
        ],
        "cocotb": [_fixture_cocotb(c) for c in _FIXTURE_CONFIGS]
        + [_hold_cocotb(c) for c in _HOLD_CONFIGS],
    },
    "M3": {
        "description": "FCFS policy: switch_top POLICY=0 + shared selector + independent Python "
        "model; directed + short random cocotb N4/8/16 (unit scope, seeds 509..513); RR and "
        "FAI_MAIN strict positive lint controls, unknown POLICY=4 rejected (3 XREJECT; was POLICY=3 "
        "before M6); refc pytest pinned",
        "implemented": True,
        "lint": [_switch_fcfs_lint(n) for n in (4, 8, 16)]
        + [_fcfs_sel_lint(n) for n in (4, 8, 16)]
        + [_switch_rr_lint(n) for n in (4, 8, 16)]
        + [_switch_fai_lint(n) for n in (4, 8, 16)],
        "elab_reject": _switch_rejects(),
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
            {"name": "tb_trace_utils", "target": "sim/common/tests", "min_tests": 1, "expect_tests": _TB_UTILS_EXPECT_TESTS},
        ],
        "cocotb": [_fcfs_sel_cocotb(n) for n in (4, 8, 16)] + [_switch_fcfs_cocotb(n) for n in (4, 8, 16)],
    },
    "M3-primary": {
        "description": "FCFS primary random regression: switch_top POLICY=0, N4/8/16 x 20 seeds "
        "509..528 x 100,000 measured cycles = 60 runs (spec 9/10)",
        "implemented": True,
        "lint": [_switch_fcfs_lint(n) for n in (4, 8, 16)],
        "cocotb": [_switch_fcfs_primary_cocotb(n) for n in (4, 8, 16)],
        # Full-scope gate: the runner FAILS unless exactly these runs all pass with this length,
        # the table's own seeds (no --seeds override), not lint-only, with a metrics JSON whose
        # trace hash the runner recomputes independently.
        "primary_scope": {
            "expected_runs": 60,
            "seeds": _PRIMARY_SEEDS,
            "n_src": [4, 8, 16],
            "cycles": _PRIMARY_CYCLES,
            "profile": "primary",
            "metrics_file": _PRIMARY_METRICS,
            "schema": "cxl-m3-fcfs-primary-v1",
        },
    },
    "M4": {
        "description": "RR policy: switch_top POLICY=1 (cxl_rr_sched) + independent Python RR oracle; "
        "directed + short random cocotb N4/8/16 at the primary quantum 10 (RTL default; unit scope, "
        "seeds 509..513). Quantum 1 is the separate supplementary scope M4-q1. FCFS and FAI_MAIN "
        "strict positive lint + structural probes, unknown POLICY=4 rejected (3 XREJECT; was POLICY=3 "
        "before M6); refc pytest pinned",
        "implemented": True,
        "lint": [_switch_rr_lint(n, q) for q in (_RR_QUANTUM_PRIMARY, _RR_QUANTUM_SUPP) for n in (4, 8, 16)]
        + [_rr_sched_lint(n, q) for q in (_RR_QUANTUM_PRIMARY, _RR_QUANTUM_SUPP) for n in (4, 8, 16)]
        + [_switch_fcfs_lint(n) for n in (4, 8, 16)]
        + [_switch_fai_lint(n) for n in (4, 8, 16)],
        "elab_reject": _switch_rejects(),
        "elab_probe": [_switch_fcfs_probe(n) for n in (4, 8, 16)] + [_switch_fai_probe(n) for n in (4, 8, 16)],
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
            {"name": "tb_trace_utils", "target": "sim/common/tests", "min_tests": 1, "expect_tests": _TB_UTILS_EXPECT_TESTS},
        ],
        "cocotb": [_switch_rr_cocotb(n, _RR_QUANTUM_PRIMARY) for n in (4, 8, 16)],
    },
    "M4-q1": {
        "description": "SUPPLEMENTARY RR quantum 1 (D32, not a primary configuration): switch_top "
        "POLICY=1 RR_QUANTUM=1 directed + short random cocotb N4/8/16 (seeds 509..513)",
        "implemented": True,
        "lint": [_switch_rr_lint(n, _RR_QUANTUM_SUPP) for n in (4, 8, 16)]
        + [_rr_sched_lint(n, _RR_QUANTUM_SUPP) for n in (4, 8, 16)],
        "elab_probe": [_switch_fcfs_probe(n) for n in (4, 8, 16)],
        "cocotb": [_switch_rr_cocotb(n, _RR_QUANTUM_SUPP) for n in (4, 8, 16)],
    },
    "M4-primary": {
        "description": "RR primary random regression: switch_top POLICY=1 quantum 10, N4/8/16 x 20 "
        "seeds 509..528 x 100,000 measured cycles = 60 runs on the M3 intended traces (spec 9/10)",
        "implemented": True,
        "lint": [_switch_rr_lint(n) for n in (4, 8, 16)],
        "elab_probe": [_switch_fcfs_probe(n) for n in (4, 8, 16)],
        "cocotb": [_switch_rr_primary_cocotb(n) for n in (4, 8, 16)],
        # Full-scope gate as M3-primary, plus: every run's intended-trace hash (recomputed by the
        # runner) must equal the tracked FCFS record EXACTLY, and the metrics must name RR/Q10.
        "primary_scope": {
            "expected_runs": 60,
            "seeds": _PRIMARY_SEEDS,
            "n_src": [4, 8, 16],
            "cycles": _PRIMARY_CYCLES,
            "profile": "primary",
            "metrics_file": _RR_PRIMARY_METRICS,
            "schema": "cxl-m4-rr-primary-v1",
            "reference_hashes": _PRIMARY_REFERENCE_HASHES,
            "expect_fields": {"policy": "RR", "policy_param": 1, "rr_quantum": _RR_QUANTUM_PRIMARY},
        },
    },
    "M5": {
        "description": "FAI-inspired Main policy (POLICY=2, cxl_fai_main_sched) UNIT scope: strict positive "
        "lint switch_top N4/8/16 x FAI_W 64/256/default 5,000,000 + standalone cxl_fai_main_sched + "
        "FCFS/RR(q10,q1) lint controls; unknown POLICY=4 rejected (3 XREJECT; POLICY=3 before M6); structural "
        "probes (FAI metadata/state/5-bit context; FCFS and RR without FAI block, RR without "
        "timestamps); refc pytest (pinned) + TB utils; 19-case cocotb test_switch_fai at N4/8/16 x stress "
        "W64/W256 (6 configs x seeds 509..513 = 30 jobs)",
        "implemented": True,
        "lint": _fai_lints_all()
        + [_switch_fcfs_lint(n) for n in (4, 8, 16)]
        + [_switch_rr_lint(n, q) for q in (None, _RR_QUANTUM_SUPP) for n in (4, 8, 16)],
        "elab_reject": _switch_rejects(),
        "elab_probe": [_switch_fai_probe(n) for n in (4, 8, 16)]
        + [_switch_fcfs_probe_m5(n) for n in (4, 8, 16)]
        + [_switch_rr_probe_m5(n) for n in (4, 8, 16)],
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
            {"name": "tb_trace_utils", "target": "sim/common/tests", "min_tests": 1, "expect_tests": _TB_UTILS_EXPECT_TESTS},
        ],
        "cocotb": [_switch_fai_cocotb(n, w) for w in _FAI_W_STRESS for n in (4, 8, 16)],
    },
    "M5-stress": {
        "description": "FAI Main long random STRESS: switch_top POLICY=2 at FAI_W 64 and 256 (-G), N4/8/16 "
        f"x seeds {_STRESS_SEEDS[0]}..{_STRESS_SEEDS[-1]} = 30 runs; W64 {_STRESS_CYCLES[64]:,} / W256 "
        f"{_STRESS_CYCLES[256]:,} trace cycles per run (window-scaled class-dynamics trace with stalls, "
        "idle/S=0 windows, overload, resets), every cycle oracle + independent checks, all 16 "
        "(state x evidence) transitions required per run",
        "implemented": True,
        "lint": [_switch_fai_lint(n, w) for w in _FAI_W_STRESS for n in (4, 8, 16)],
        "cocotb": [_switch_fai_stress_cocotb(n, w) for w in _FAI_W_STRESS for n in (4, 8, 16)],
        "smoke_env": ["CXL_STRESS_CYCLES"],
        "run_scope": {
            "name": "stress_full_matrix",
            "n_src": [4, 8, 16],
            "fai_w": _FAI_W_STRESS,
            "seeds": _STRESS_SEEDS,
            "metrics_file": _STRESS_METRICS,
            "schema": "cxl-m5-fai-stress-v1",
            "cycles_by_w": _STRESS_CYCLES,
            "require_all_transitions": True,
        },
    },
    "M5-primary": {
        "description": "FAI Main primary random regression: switch_top POLICY=2 at the production FAI_W "
        "5,000,000 (RTL default), N4/8/16 x 20 seeds 509..528 x 100,000 measured cycles = 60 runs on the "
        "M3 intended traces (tracked hashes, spec 9/10). NO window closes in 100,000 cycles: all sources "
        "stay H and selection is expected to equal FCFS (checked); NOT evidence of window adaptation",
        "implemented": True,
        "lint": [_switch_fai_lint(n) for n in (4, 8, 16)],
        "elab_probe": [_switch_fai_probe(n) for n in (4, 8, 16)],
        "cocotb": [_switch_fai_primary_cocotb(n) for n in (4, 8, 16)],
        "smoke_env": ["CXL_PRIMARY_CYCLES"],
        "primary_scope": {
            "expected_runs": 60,
            "seeds": _PRIMARY_SEEDS,
            "n_src": [4, 8, 16],
            "cycles": _PRIMARY_CYCLES,
            "profile": "primary",
            "metrics_file": _FAI_PRIMARY_METRICS,
            "schema": "cxl-m5-fai-primary-v1",
            "reference_hashes": _PRIMARY_REFERENCE_HASHES,
            "expect_fields": {
                "policy": "FAI_MAIN",
                "policy_param": 2,
                "fai_w": _FAI_W_PRODUCTION,
                "windows_closed_measurement": 0,
                "fcfs_equivalence_checked_cycles": _PRIMARY_CYCLES,
            },
        },
    },
    "M5-production": {
        "description": f"FAI Main PRODUCTION windows: switch_top POLICY=2 at the RTL default FAI_W "
        f"5,000,000, N4/8/16 x seed {_PRODUCTION_SEED}, {_PRODUCTION_CYCLES:,} real non-reset cycles per "
        f"run = {_PRODUCTION_CYCLES // _FAI_W_PRODUCTION} complete windows (>= {_PRODUCTION_MIN_WINDOWS} "
        "required), no time skip / state deposit / smaller W; every cycle oracle + independent checks "
        "with bounded memory; designed per-window share skew drives H->B_H->L->B_L->H and cancellations",
        "implemented": True,
        "lint": [_switch_fai_lint(n) for n in (4, 8, 16)],
        "elab_probe": [_switch_fai_probe(n) for n in (4, 8, 16)],
        "cocotb": [_switch_fai_production_cocotb(n) for n in (4, 8, 16)],
        "smoke_env": ["CXL_PRODUCTION_CYCLES"],
        "run_scope": {
            "name": "production_full_matrix",
            "n_src": [4, 8, 16],
            "fai_w": [_FAI_W_PRODUCTION],
            "seeds": [_PRODUCTION_SEED],
            "metrics_file": _PRODUCTION_METRICS,
            "schema": "cxl-m5-fai-production-v1",
            "cycles_by_w": {_FAI_W_PRODUCTION: _PRODUCTION_CYCLES},
            "min_windows": _PRODUCTION_MIN_WINDOWS,
            "require_all_transitions": False,
        },
    },
    "M6": {
        "description": "SUPPLEMENTARY FAI Algorithm-2 (POLICY=3, spec 8.6; cxl_fai_main_sched INTERP=1 in "
        "gen_policy_fai_alg2) UNIT scope: strict positive lint switch_top FAI_ALG2 N4/8/16 x FAI_W "
        "64/256/default 5,000,000 + standalone INTERP=1, all Main/FCFS/RR(q10,q1) lint controls; unknown "
        "POLICY=4 rejected at N4/8/16 + INTERP=2 rejected (4 XREJECT); structural probes (FAI_ALG2 "
        "metadata/state/5-bit context without Main block; unchanged Main/FCFS/RR probes); refc pytest + "
        "TB utils; 16-case cocotb test_switch_fai_alg2 at N4 x stress W64/W256 (2 configs x seeds "
        "509..513 = 10 jobs) + 1 production-parameter smoke N4 (default W, no closing)",
        "implemented": True,
        "lint": _fai_alg2_lints_all()
        + _fai_lints_all()
        + [_switch_fcfs_lint(n) for n in (4, 8, 16)]
        + [_switch_rr_lint(n, q) for q in (None, _RR_QUANTUM_SUPP) for n in (4, 8, 16)],
        "elab_reject": _switch_rejects() + [_fai_interp_reject()],
        "elab_probe": [_switch_fai_alg2_probe(n) for n in (4, 8, 16)]
        + [_switch_fai_probe(n) for n in (4, 8, 16)]
        + [_switch_fcfs_probe_m5(n) for n in (4, 8, 16)]
        + [_switch_rr_probe_m5(n) for n in (4, 8, 16)],
        "pytest": [
            {"name": "refc_models", "target": "refc/tests", "min_tests": 1, "expect_tests": _REFC_EXPECT_TESTS},
            {"name": "tb_trace_utils", "target": "sim/common/tests", "min_tests": 1, "expect_tests": _TB_UTILS_EXPECT_TESTS},
        ],
        "cocotb": [_switch_fai_alg2_cocotb(4, w) for w in _FAI_W_STRESS] + [_switch_fai_alg2_smoke_cocotb(4)],
    },
    "M6-stress": {
        "description": "SUPPLEMENTARY Algorithm-2 N4 long stress: W64/256 x seeds 509..513, "
        "400,000/800,000 cycles, all 16 state/evidence transitions and shared checks per run",
        "implemented": True,
        "lint": [_switch_fai_alg2_lint(4, w) for w in _FAI_W_STRESS],
        "cocotb": [_switch_fai_stress_cocotb(4, w, policy=3) for w in _FAI_W_STRESS],
        "smoke_env": ["CXL_STRESS_CYCLES"],
        "run_scope": {
            "name": "alg2_stress_full_matrix", "n_src": [4], "fai_w": _FAI_W_STRESS,
            "seeds": _STRESS_SEEDS, "metrics_file": "fai_alg2_stress_metrics.json",
            "schema": "cxl-m6-fai-alg2-stress-v1", "cycles_by_w": _STRESS_CYCLES,
            "require_all_transitions": True,
            "states": ["STABLE_HIGH", "BUFFER_P_LOW", "STABLE_LOW", "BUFFER_P_HIGH"],
            "expect_fields": {"policy": "FAI_ALG2", "policy_param": 3},
        },
    },
    "M6-production": {
        "description": "SUPPLEMENTARY Algorithm-2 N4 production: seed509, default W5,000,000 "
        "(no -G), 20,000,000 real non-reset cycles / four windows, every-cycle checks, bounded memory",
        "implemented": True,
        "lint": [_switch_fai_alg2_lint(4)],
        "elab_probe": [_switch_fai_alg2_probe(4)],
        "cocotb": [_switch_fai_production_cocotb(4, policy=3)],
        "smoke_env": ["CXL_PRODUCTION_CYCLES"],
        "run_scope": {
            "name": "alg2_production_full_matrix", "n_src": [4], "fai_w": [_FAI_W_PRODUCTION],
            "seeds": [_PRODUCTION_SEED], "metrics_file": "fai_alg2_production_metrics.json",
            "schema": "cxl-m6-fai-alg2-production-v1",
            "cycles_by_w": {_FAI_W_PRODUCTION: _PRODUCTION_CYCLES},
            "min_windows": _PRODUCTION_MIN_WINDOWS, "require_all_transitions": False,
            "expect_fields": {"policy": "FAI_ALG2", "policy_param": 3, "production_evidence": True},
        },
    },
    "M6-compare": {
        "description": "SUPPLEMENTARY Main vs Algorithm-2 behavior RECORDS: switch_top POLICY=2 and POLICY=3, "
        f"N4 x FAI_W 64 / 256 x seeds {_M6_SEEDS[0]}..{_M6_SEEDS[-1]} (20 runs), identical intended "
        f"class-dynamics traces of {_COMPARE_CYCLES[64]:,} / {_COMPARE_CYCLES[256]:,} cycles, every cycle "
        "checked by all harness layers; diff with scripts/compare_fai_interps.py (observations only)",
        "implemented": True,
        "lint": [_switch_fai_lint(4, w) for w in _FAI_W_STRESS] + [_switch_fai_alg2_lint(4, w) for w in _FAI_W_STRESS],
        "cocotb": [_switch_fai_compare_cocotb(p, w) for p in (2, 3) for w in _FAI_W_STRESS],
    },
}


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def parse_seeds(text: str) -> List[int]:
    """'509..513', '509,511' or a mix like '1,5..7'."""
    seeds: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty seed element in {text!r}")
        if ".." in part:
            lo_s, hi_s = part.split("..", 1)
            lo, hi = int(lo_s), int(hi_s)
            if hi < lo:
                raise ValueError(f"descending seed range {part!r}")
            seeds.extend(range(lo, hi + 1))
        else:
            seeds.append(int(part))
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"duplicate seeds in {text!r}")
    if any(s < 0 for s in seeds):
        raise ValueError("seeds must be non-negative")
    return seeds


def junit_counts(xml_path: Path) -> dict:
    """Count test cases in a JUnit XML by element, cross-checked against suite attributes.

    Raises ValueError for a missing, empty or unparsable file.
    """
    if not xml_path.is_file():
        raise ValueError(f"results XML missing: {xml_path}")
    if xml_path.stat().st_size == 0:
        raise ValueError(f"results XML empty: {xml_path}")
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"results XML unparsable: {xml_path}: {exc}") from exc

    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for case in root.iter("testcase"):
        counts["tests"] += 1
        kinds = {child.tag for child in case}
        counts["failures"] += int("failure" in kinds)
        counts["errors"] += int("error" in kinds)
        counts["skipped"] += int("skipped" in kinds)

    # If a suite declares totals they must not report more problems than the elements show.
    attr = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    declared = False
    for suite in root.iter("testsuite"):
        for key in attr:
            if suite.get(key) is not None:
                declared = True
                attr[key] += int(suite.get(key))
    if declared:
        for key in ("failures", "errors", "skipped"):
            counts[key] = max(counts[key], attr[key])
        if attr["tests"] != counts["tests"]:
            raise ValueError(
                f"results XML inconsistent: suite declares {attr['tests']} tests, "
                f"{counts['tests']} testcase elements found: {xml_path}"
            )

    seed = None
    for prop in root.iter("property"):
        if prop.get("name") == "random_seed":
            seed = prop.get("value")
    counts["xml_random_seed"] = seed
    return counts


def judge_counts(counts: dict, expect_tests: Optional[int] = None, min_tests: int = 1) -> List[str]:
    """Return the list of reasons the counts are not a clean pass (empty list = clean)."""
    problems = []
    if counts["tests"] <= 0:
        problems.append("no test cases in results XML")
    if counts["tests"] < min_tests:
        problems.append(f"only {counts['tests']} tests, at least {min_tests} required")
    if expect_tests is not None and counts["tests"] != expect_tests:
        problems.append(f"{counts['tests']} tests in results XML, exactly {expect_tests} declared")
    for key in ("failures", "errors", "skipped"):
        if counts[key] != 0:
            problems.append(f"{key}={counts[key]} (must be 0)")
    return problems


class Run:
    def __init__(self, args, repo_root: Path) -> None:
        # Nothing below may fail on user input: argument errors are rejected in main() before a
        # run directory is created.
        self.args = args
        self.repo = repo_root
        self.milestone = args.milestone
        self.entry = MILESTONES[self.milestone]
        self.run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"_{os.getpid()}"
        # Infrastructure smoke runs (--infra-smoke) are never milestone evidence: they live in a
        # separate evidence directory so they cannot be mistaken for (or overwrite latest.txt of)
        # the registered scope.
        self.smoke = bool(args.infra_smoke)
        evidence_name = self.milestone + ("-infra-smoke" if self.smoke else "")
        self.milestone_dir = self.repo / "artifacts" / "implementation" / evidence_name
        self.out = self.milestone_dir / self.run_id
        self.out.mkdir(parents=True, exist_ok=False)
        (self.out / "logs").mkdir()
        (self.out / "junit").mkdir()
        build_root = Path(
            os.environ.get("CXL_BUILD_ROOT") or "~/.cache/cxl-scheduler/build"
        ).expanduser()
        self.build_root = build_root / self.milestone / self.run_id
        self.steps: List[dict] = []
        self.lock = threading.Lock()
        self.abort = threading.Event()
        self.t0 = time.time()
        self.seeds_override = args.seed_list
        self.n_filter = args.n_src_list

    def acceptance_scope(self) -> bool:
        """True only for a full run of the table's own matrix (no override/filter/smoke)."""
        return not (self.args.lint_only or self.seeds_override is not None or self.n_filter or self.smoke)

    def sim_timeout(self, cfg: dict) -> int:
        if self.args.cocotb_timeout is not None:
            return self.args.cocotb_timeout
        return int(cfg.get("timeout_s", STEP_TIMEOUT_S))

    # ----- evidence -----------------------------------------------------------------------------

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.out))
        except ValueError:
            return str(path)

    def record_command(self, step: str, cmd: List[str], cwd: Path, env_extra: Optional[dict]) -> None:
        with self.lock, open(self.out / "commands.txt", "a", encoding="utf-8") as f:
            f.write(f"# step: {step}\n# cwd: {cwd}\n")
            for key in sorted(env_extra or {}):
                f.write(f"# env: {key}={shlex.quote(str(env_extra[key]))}\n")
            f.write(shlex.join(cmd) + "\n\n")

    def exec(
        self,
        step: str,
        cmd: List[str],
        cwd: Path,
        log: Path,
        env_extra: Optional[dict] = None,
        timeout_s: int = STEP_TIMEOUT_S,
    ) -> int:
        """Run one command in the foreground, appending stdout+stderr to the step log. A command
        still running after ``timeout_s`` is killed and reported as exit code 124 (a FAIL)."""
        self.record_command(step, cmd, cwd, env_extra)
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (env_extra or {}).items()})
        with open(log, "ab") as f:
            f.write(f"\n===== $ {shlex.join(cmd)}\n===== cwd: {cwd}\n===== timeout: {timeout_s}s\n".encode())
            f.flush()
            try:
                proc = subprocess.run(
                    cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout_s
                )
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = 124
                f.write(f"\n===== TIMEOUT after {timeout_s}s\n".encode())
            except OSError as exc:
                code = 127
                f.write(f"\n===== could not execute: {exc}\n".encode())
            f.write(f"\n===== exit code: {code}\n".encode())
        return code

    def capture(self, cmd: List[str]) -> str:
        try:
            proc = subprocess.run(
                cmd, cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120
            )
            return f"$ {shlex.join(cmd)}\n{proc.stdout.rstrip()}\n(exit {proc.returncode})\n"
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"$ {shlex.join(cmd)}\nFAILED TO RUN: {exc}\n"

    def write_versions(self) -> None:
        py = sys.executable
        chunks = [
            f"run_id: {self.run_id}\nfrozen_spec_commit: {FROZEN_SPEC_COMMIT}\n",
            self.capture(["verilator", "--version"]),
            self.capture([py, "--version"]),
            self.capture([py, "-c", "import cocotb; print('cocotb', cocotb.__version__)"]),
            self.capture([py, "-c", "import pytest; print('pytest', pytest.__version__)"]),
            self.capture(["make", "--version"]),
            self.capture([os.environ.get("CXX", "g++"), "--version"]),
            self.capture(["uname", "-srm"]),
            self.capture(["git", "rev-parse", "HEAD"]),
            self.capture(["git", "status", "--short"]),
        ]
        (self.out / "versions.txt").write_text("\n".join(chunks), encoding="utf-8")

    def write_config(self, plan: dict) -> None:
        config = {
            "milestone": self.milestone,
            "description": self.entry["description"],
            "run_id": self.run_id,
            "argv": sys.argv[1:],
            "scope": "lint-only" if self.args.lint_only else "full",
            "keep_going": self.args.keep_going,
            "jobs": self.args.jobs,
            "seeds_override": self.seeds_override,
            "n_src_filter": self.n_filter,
            "infra_smoke": (
                {"cycles": self.args.cycles, "env": self.entry.get("smoke_env", []),
                 "label": "INFRASTRUCTURE SMOKE - NOT milestone evidence"}  # fmt: skip
                if self.smoke
                else None
            ),
            "cocotb_timeout_override_s": self.args.cocotb_timeout,
            "default_step_timeout_s": STEP_TIMEOUT_S,
            "lint_flags": LINT_FLAGS,
            "sim_strict_flags": SIM_STRICT_FLAGS,
            "sim_build_relaxations": [list(r) for r in SIM_BUILD_RELAXATIONS],
            "sim_timescale": SIM_TIMESCALE,
            "waves": False,
            "build_root": str(self.build_root),
            "frozen_spec_commit": FROZEN_SPEC_COMMIT,
            "plan": plan,
        }
        (self.out / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def add_step(self, step: dict) -> None:
        with self.lock:
            self.steps.append(step)
            status = step["status"]
            detail = ""
            if "tests" in step:
                detail = (
                    f" tests={step['tests']} failures={step['failures']} "
                    f"errors={step['errors']} skipped={step['skipped']}"
                )
            if step.get("reason"):
                detail += f" [{step['reason']}]"
            print(f"[{status:7s}] {step['name']}{detail}", flush=True)
            if status == "FAIL":
                print(f"          log: {self.out / step['log']}", flush=True)
                if not self.args.keep_going:
                    self.abort.set()
            self.write_summary(final=False)

    def write_summary(self, final: bool) -> str:
        statuses = [s["status"] for s in self.steps]
        if "FAIL" in statuses:
            overall = "FAIL"
        elif not final:
            overall = "RUNNING"
        elif "NOT_RUN" in statuses or not statuses:
            overall = "FAIL"
        else:
            overall = "PASS"
        if self.smoke and overall in ("PASS", "FAIL"):
            # Executed steps judged as usual, but labelled: a smoke run is never acceptance.
            overall = f"INFRA_SMOKE_{overall}"
        full_scope = self.acceptance_scope()
        if "primary_scope" in self.entry or "run_scope" in self.entry:
            scope_steps = [s for s in self.steps if s.get("kind") == "scope"]
            full_scope = full_scope and bool(scope_steps) and all(s["status"] == "PASS" for s in scope_steps)
        declared = self.entry.get("primary_scope") or self.entry.get("run_scope")
        summary = {
            "milestone": self.milestone,
            "run_id": self.run_id,
            "overall": overall,
            "scope": "lint-only" if self.args.lint_only else ("infra-smoke" if self.smoke else "full"),
            "infra_smoke": self.smoke,
            "n_src_filter": self.n_filter,
            "declared_scope": declared,
            # Only a full-scope run with the table's own seeds is milestone acceptance evidence.
            "milestone_acceptance_scope": full_scope,
            "wall_time_s": round(time.time() - self.t0, 3),
            "counts": {
                "steps": len(statuses),
                "pass": statuses.count("PASS"),
                # Negative elaboration checks: expected rejections, never simulation passes and
                # never part of the test totals below.
                "expected_rejection": statuses.count(XREJECT),
                "fail": statuses.count("FAIL"),
                "not_run": statuses.count("NOT_RUN"),
                "tests": sum(s.get("tests", 0) for s in self.steps),
                "failures": sum(s.get("failures", 0) for s in self.steps),
                "errors": sum(s.get("errors", 0) for s in self.steps),
                "skipped": sum(s.get("skipped", 0) for s in self.steps),
            },
            "sim_build_relaxations": [list(r) for r in SIM_BUILD_RELAXATIONS],
            "status_legend": {XREJECT: XREJECT_LABEL},
            "steps": sorted(self.steps, key=lambda s: s["order"]),
        }
        tmp = self.out / "summary.json.tmp"
        tmp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.out / "summary.json")
        return overall

    # ----- steps --------------------------------------------------------------------------------

    @staticmethod
    def gflags(params: dict) -> List[str]:
        return [f"-G{name}={value}" for name, value in params.items()]

    def not_run(self, order: int, kind: str, name: str, why: str) -> None:
        self.add_step({"order": order, "kind": kind, "name": name, "status": "NOT_RUN", "reason": why})

    def lint_step(self, order: int, cfg: dict) -> None:
        name = f"lint:{cfg['name']}"
        log = self.out / "logs" / f"lint_{cfg['name']}.log"
        cmd = (
            ["verilator"]
            + LINT_FLAGS
            + ["--top-module", cfg["top"]]
            + self.gflags(cfg["params"])
            + ["-f", cfg["filelist"]]
        )
        t = time.time()
        code = self.exec(name, cmd, self.repo, log)
        text = log.read_text(encoding="utf-8", errors="replace")
        diagnostics = [ln for ln in text.splitlines() if re.match(r"^%(Warning|Error)", ln)]
        problems = []
        if code != 0:
            problems.append(f"exit code {code}")
        if diagnostics:
            problems.append(f"{len(diagnostics)} Verilator diagnostic line(s)")
        self.add_step(
            {
                "order": order,
                "kind": "lint",
                "name": name,
                "status": "FAIL" if problems else "PASS",
                "reason": "; ".join(problems),
                "exit_codes": {"verilator": code},
                "diagnostics": len(diagnostics),
                "params": cfg["params"],
                "top": cfg["top"],
                "filelist": cfg["filelist"],
                "log": self.rel(log),
                "wall_time_s": round(time.time() - t, 3),
            }
        )

    def elab_reject_step(self, order: int, cfg: dict) -> None:
        """Negative elaboration check: the strict lint command must be rejected for the declared
        intentional reason and for nothing else. Never a test, never a simulation pass."""
        name = f"elab_reject:{cfg['name']}"
        log = self.out / "logs" / f"elab_reject_{cfg['name']}.log"
        cmd = (
            ["verilator"]
            + LINT_FLAGS
            + ["--top-module", cfg["top"]]
            + self.gflags(cfg["params"])
            + ["-f", cfg["filelist"]]
        )
        t = time.time()
        code = self.exec(name, cmd, self.repo, log)
        text = log.read_text(encoding="utf-8", errors="replace")
        loc = r"\S+:\d+:\d+: "
        fatal_re = re.compile("^" + loc + re.escape(cfg["expect_message"]) + "$")
        undriven_re = re.compile("^" + loc + r"Signal is not driven: '(\w+)'$")
        unused_re = re.compile("^" + loc + r"Signal is not used: '(\w+)'$")
        exit_re = re.compile(r"^Exiting due to (\d+) warning\(s\)$")
        fatal_hits = 0
        coded = 0
        exit_counts: List[int] = []
        undriven: List[str] = []
        unused: List[str] = []
        unexpected: List[str] = []
        for line in text.splitlines():
            m = _DIAG_RE.match(line)
            if not m:
                continue
            severity, diag_code, body = m.groups()
            if diag_code is not None:
                coded += 1
            if severity == "Warning" and diag_code == "USERFATAL" and fatal_re.match(body):
                fatal_hits += 1
            elif severity == "Warning" and diag_code == "UNDRIVEN" and undriven_re.match(body):
                sig = undriven_re.match(body).group(1)
                undriven.append(sig)
                if sig not in cfg["allowed_undriven"]:
                    unexpected.append(line)
            elif severity == "Warning" and diag_code == "UNUSEDSIGNAL" and unused_re.match(body):
                sig = unused_re.match(body).group(1)
                unused.append(sig)
                if sig not in cfg["allowed_unused"]:
                    unexpected.append(line)
            elif severity == "Error" and diag_code is None and exit_re.match(body):
                exit_counts.append(int(exit_re.match(body).group(1)))
            else:
                unexpected.append(line)
        problems = []
        if code == 0:
            problems.append("elaboration was NOT rejected (exit code 0)")
        if fatal_hits != 1:
            problems.append(f"intentional USERFATAL message found {fatal_hits} time(s), exactly 1 required")
        if unexpected:
            problems.append(f"{len(unexpected)} diagnostic(s) outside the declared rejection: {unexpected[0]}")
        if exit_counts != [coded]:
            problems.append(f"exit line(s) {exit_counts} do not account for the {coded} diagnostics seen")
        if "expect_undriven" in cfg and sorted(undriven) != sorted(cfg["expect_undriven"]):
            problems.append(f"undriven pins {sorted(undriven)} != declared {sorted(cfg['expect_undriven'])}")
        if "expect_unused" in cfg and sorted(unused) != sorted(cfg["expect_unused"]):
            problems.append(f"unused pins {sorted(unused)} != declared {sorted(cfg['expect_unused'])}")
        self.add_step(
            {
                "order": order,
                "kind": "elab_reject",
                "name": name,
                "status": "FAIL" if problems else XREJECT,
                "label": XREJECT_LABEL,
                "reason": "; ".join(problems),
                "exit_codes": {"verilator": code},
                "expect_message": cfg["expect_message"],
                "userfatal_hits": fatal_hits,
                "undriven_policy_slot_pins": sorted(undriven),
                "unused_policy_slot_pins": sorted(unused),
                "unexpected_diagnostics": unexpected,
                "params": cfg["params"],
                "top": cfg["top"],
                "filelist": cfg["filelist"],
                "log": self.rel(log),
                "wall_time_s": round(time.time() - t, 3),
            }
        )

    def pytest_step(self, order: int, cfg: dict) -> None:
        name = f"pytest:{cfg['name']}"
        log = self.out / "logs" / f"pytest_{cfg['name']}.log"
        xml = self.out / "junit" / f"pytest_{cfg['name']}.xml"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            cfg["target"],
            "-v",
            "-p",
            "no:cacheprovider",
            "-o",
            "junit_family=xunit2",
            f"--junitxml={xml}",
        ]
        t = time.time()
        code = self.exec(name, cmd, self.repo, log, {"PYTHONDONTWRITEBYTECODE": "1"})
        step = {
            "order": order,
            "kind": "pytest",
            "name": name,
            "exit_codes": {"pytest": code},
            "target": cfg["target"],
            "log": self.rel(log),
            "junit": self.rel(xml),
        }
        problems = [] if code == 0 else [f"exit code {code}"]
        try:
            counts = junit_counts(xml)
            counts.pop("xml_random_seed")
            step.update(counts)
            problems += judge_counts(counts, expect_tests=cfg.get("expect_tests"), min_tests=cfg.get("min_tests", 1))
        except ValueError as exc:
            problems.append(str(exc))
        step["status"] = "FAIL" if problems else "PASS"
        step["reason"] = "; ".join(problems)
        step["wall_time_s"] = round(time.time() - t, 3)
        self.add_step(step)

    def cocotb_env(self, cfg: dict, seed: int, xml: Path) -> dict:
        import cocotb_tools.config as cocotb_config
        import find_libpython

        libpython = find_libpython.find_libpython()
        if libpython is None:
            raise RuntimeError("libpython not found for the active interpreter")
        test_dir = self.repo / cfg["test_dir"]
        pythonpath = [str(test_dir), str(self.repo / "sim" / "common")] + [p for p in sys.path if p]
        env = {
            "COCOTB_TOPLEVEL": cfg["top"],
            "COCOTB_TEST_MODULES": cfg["test_module"],
            "TOPLEVEL_LANG": "verilog",
            "COCOTB_RANDOM_SEED": str(seed),
            "COCOTB_RESULTS_FILE": str(xml),
            "COCOTB_TRUST_INERTIAL_WRITES": "1",
            "PYGPI_PYTHON_BIN": sys.executable,
            "GPI_USERS": f"{libpython};{cocotb_config.pygpi_entry_point()}",
            "PYTHONPATH": os.pathsep.join(pythonpath),
            "PYTHONDONTWRITEBYTECODE": "1",
            # Line-visible progress in the step log during long (stress / production) runs; output
            # buffering only, no functional effect.
            "PYTHONUNBUFFERED": "1",
            "CXL_REPO_ROOT": str(self.repo),
            "CXL_MILESTONE": self.milestone,
        }
        overlap = set(cfg["params"]) & set(cfg.get("default_params", {}))
        if overlap:
            raise RuntimeError(f"{cfg['name']}: {sorted(overlap)} in both params and default_params")
        for key, value in {**cfg.get("default_params", {}), **cfg["params"]}.items():
            env[f"CXL_PARAM_{key}"] = str(value)
        env.update({k: str(v) for k, v in cfg.get("env", {}).items()})
        if self.smoke:
            # Shortened, explicitly labelled infrastructure run: the test sees CXL_INFRA_SMOKE=1
            # and must label its result as not-evidence (production refuses short runs otherwise).
            for var in self.entry["smoke_env"]:
                env[var] = str(self.args.cycles)
            env["CXL_INFRA_SMOKE"] = "1"
        env["CXL_SIM_TIMEOUT_S"] = str(self.sim_timeout(cfg))
        return env

    def verilate_cmd(self, cfg: dict, build: Path) -> List[str]:
        """The cocotb simulation-build verilate command (also used verbatim by elab_probe steps)."""
        import cocotb_tools.config as cocotb_config

        libs = cocotb_config.libs_dir
        verilator_cpp = cocotb_config.share_dir / "lib" / "verilator" / "verilator.cpp"
        return (
            [
                "verilator",
                "-cc",
                "--exe",
                "-Mdir",
                str(build),
                "--top-module",
                cfg["top"],
                "--vpi",
                "--public-flat-rw",
                "--prefix",
                "Vtop",
                "-o",
                cfg["top"],
                "-LDFLAGS",
                f"-Wl,-rpath,{libs} -L{libs} -lcocotbvpi_verilator",
                "--timescale",
                SIM_TIMESCALE,
            ]
            + SIM_STRICT_FLAGS
            + [flag for flag, _reason in SIM_BUILD_RELAXATIONS]
            + self.gflags(cfg["params"])
            + [str(verilator_cpp), "-f", cfg["filelist"]]
        )

    @staticmethod
    def run_elab_checks(cfg: dict, build: Path, log: Path) -> tuple:
        """Apply cfg['elab_checks'] to the generated model files. Returns (results, problems)."""
        results: List[dict] = []
        problems: List[str] = []
        for chk in cfg.get("elab_checks", []):
            files = sorted(glob.glob(str(build / chk["glob"])))
            hits = []
            for path in files:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
                if re.search(chk["pattern"], text):
                    hits.append(Path(path).name)
            if not files:
                ok = False
                note = "no generated files matched the glob"
            else:
                ok = bool(hits) if chk["expect"] == "present" else not hits
                note = f"{len(files)} files scanned, {len(hits)} with a match"
            results.append({**chk, "ok": ok, "note": note, "hits": hits})
            with open(log, "ab") as f:
                f.write(
                    f"\n===== elab_check /{chk['pattern']}/ in {chk['glob']} expect "
                    f"{chk['expect']}: {'OK' if ok else 'FAIL'} ({note})\n".encode()
                )
            if not ok:
                problems.append(f"elab check /{chk['pattern']}/ expected {chk['expect']}: {note}")
        return results, problems

    def elab_probe_step(self, order: int, cfg: dict) -> None:
        """Structural control: run the exact cocotb verilate command for a configuration and apply
        its elab_checks to the generated model. No make, no simulation, never a test."""
        name = f"elab_probe:{cfg['name']}"
        log = self.out / "logs" / f"elab_probe_{cfg['name']}.log"
        build = self.build_root / f"elab_probe_{cfg['name']}"
        build.mkdir(parents=True, exist_ok=False)
        t = time.time()
        if not cfg.get("elab_checks"):
            raise SystemExit(f"run_verify: elab_probe {cfg['name']} declares no elab_checks")
        code = self.exec(name, self.verilate_cmd(cfg, build), self.repo, log)
        text = log.read_text(encoding="utf-8", errors="replace")
        diagnostics = [ln for ln in text.splitlines() if re.match(r"^%(Warning|Error)", ln)]
        problems = [] if code == 0 else [f"verilate exit code {code}"]
        if diagnostics:
            problems.append(f"{len(diagnostics)} Verilator diagnostic line(s)")
        results: List[dict] = []
        if code == 0:
            results, chk_problems = self.run_elab_checks(cfg, build, log)
            problems += chk_problems
        self.add_step(
            {
                "order": order,
                "kind": "elab_probe",
                "name": name,
                "status": "FAIL" if problems else "PASS",
                "reason": "; ".join(problems),
                "exit_codes": {"verilate": code},
                "params": cfg["params"],
                "top": cfg["top"],
                "filelist": cfg["filelist"],
                "build_dir": str(build),
                "elab_checks": results,
                "log": self.rel(log),
                "wall_time_s": round(time.time() - t, 3),
            }
        )

    def cocotb_job(self, order: int, cfg: dict, seed: int) -> None:
        job = f"{cfg['name']}_seed{seed}"
        name = f"cocotb:{job}"
        if self.abort.is_set():
            self.not_run(order, "cocotb", name, "skipped by fail-fast after an earlier failure")
            return
        log = self.out / "logs" / f"cocotb_{job}.log"
        xml_final = self.out / "junit" / f"cocotb_{job}.xml"
        build = self.build_root / job
        run_dir = build / "run"
        run_dir.mkdir(parents=True, exist_ok=False)
        xml_local = run_dir / "results.xml"
        step = {
            "order": order,
            "kind": "cocotb",
            "name": name,
            "top": cfg["top"],
            "filelist": cfg["filelist"],
            "params": cfg["params"],
            "default_params": cfg.get("default_params", {}),
            "test_module": f"{cfg['test_dir']}/{cfg['test_module']}.py",
            "seed": seed,
            "build_dir": str(build),
            "log": self.rel(log),
            "junit": self.rel(xml_final),
            "exit_codes": {},
        }
        t = time.time()
        problems: List[str] = []

        verilate = self.verilate_cmd(cfg, build)
        code = self.exec(name, verilate, self.repo, log)
        step["exit_codes"]["verilate"] = code
        if code != 0:
            problems.append(f"verilate exit code {code}")

        if not problems:
            make = ["make", "-j", str(self.args.make_jobs), "-C", str(build), "-f", "Vtop.mk", "VM_TRACE=0"]
            code = self.exec(name, make, self.repo, log)
            step["exit_codes"]["make"] = code
            if code != 0:
                problems.append(f"make exit code {code}")

        if not problems:
            step["elab_checks"], chk_problems = self.run_elab_checks(cfg, build, log)
            problems += chk_problems

        if not problems:
            env = self.cocotb_env(cfg, seed, xml_local)
            step["sim_timeout_s"] = self.sim_timeout(cfg)
            step["env"] = {k: env[k] for k in sorted(env) if k.startswith("CXL_") and k != "CXL_REPO_ROOT"}
            t_sim = time.time()
            code = self.exec(name, [str(build / cfg["top"])], run_dir, log, env, timeout_s=step["sim_timeout_s"])
            step["sim_wall_time_s"] = round(time.time() - t_sim, 3)
            step["exit_codes"]["simulation"] = code
            if code == 124:
                problems.append(f"simulation TIMEOUT after {step['sim_timeout_s']}s")
            elif code != 0:
                problems.append(f"simulation exit code {code}")
            if xml_local.is_file():
                shutil.copyfile(xml_local, xml_final)
            try:
                counts = junit_counts(xml_final)
                xml_seed = counts.pop("xml_random_seed")
                step.update(counts)
                step["xml_random_seed"] = xml_seed
                problems += judge_counts(counts, expect_tests=cfg.get("expect_tests"))
                if xml_seed is None:
                    problems.append("results XML does not record random_seed")
                elif str(xml_seed) != str(seed):
                    problems.append(f"results XML random_seed={xml_seed}, requested {seed}")
            except ValueError as exc:
                problems.append(str(exc))
            # Per-run result files written by the test into its run directory (trace hash,
            # metrics). Copied into the evidence directory; a declared required file must exist.
            step["artifacts"] = []
            for art in cfg.get("artifacts", []):
                src = run_dir / art["file"]
                dst = self.out / "results" / f"cocotb_{job}__{art['file']}"
                if src.is_file():
                    dst.parent.mkdir(exist_ok=True)
                    shutil.copyfile(src, dst)
                    step["artifacts"].append(self.rel(dst))
                elif art.get("required"):
                    problems.append(f"required result file {art['file']} was not written by the test")

        step["status"] = "FAIL" if problems else "PASS"
        step["reason"] = "; ".join(problems)
        step["wall_time_s"] = round(time.time() - t, 3)
        self.add_step(step)

    def primary_scope_step(self, order: int, scope: dict) -> None:
        """Full-scope gate of a primary random-regression milestone (never a test).

        FAILS unless: no --seeds override, not lint-only, every (N, seed) of the declared matrix
        has a PASS cocotb step (exactly ``expected_runs``), and every run's metrics JSON records the
        requested seed/N/profile, exactly ``cycles`` measured cycles and a trace SHA-256 equal to
        the runner's own independent regeneration of the intended trace."""
        name = "scope:primary_full_matrix"
        t = time.time()
        problems: List[str] = []
        if self.args.lint_only:
            problems.append("lint-only run: the primary regression did not run")
        if self.seeds_override is not None:
            problems.append(f"seed override {self.seeds_override}: not the declared seed set {scope['seeds'][0]}..{scope['seeds'][-1]}")
        sys.path.insert(0, str(self.repo / "sim" / "common"))
        import traffic_trace  # the same generator the tests use

        ref: Optional[Dict[tuple, str]] = None
        if scope.get("reference_hashes"):
            ref, ref_problems = self._load_reference_hashes(scope)
            problems += ref_problems
        runs = []
        by_key = {}
        for s in self.steps:
            if s.get("kind") == "cocotb":
                by_key[(s.get("params", {}).get("N_SRC"), s.get("seed"))] = s
        for n_src in scope["n_src"]:
            for seed in scope["seeds"]:
                st = by_key.get((n_src, seed))
                if st is None:
                    problems.append(f"run N{n_src} seed {seed} missing")
                    continue
                if st["status"] != "PASS":
                    problems.append(f"run N{n_src} seed {seed} status {st['status']}")
                    continue
                path = self.out / "results" / f"cocotb_{st['name'].split(':', 1)[1]}__{scope['metrics_file']}"
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    problems.append(f"run N{n_src} seed {seed}: metrics unreadable: {exc}")
                    continue
                expect_hash = traffic_trace.make_trace(seed, n_src, scope["cycles"], scope["profile"]).sha256
                checks = {
                    "schema": (data.get("schema"), scope["schema"]),
                    "seed": (data.get("seed"), seed),
                    "n_src": (data.get("n_src"), n_src),
                    "profile": (data.get("profile"), scope["profile"]),
                    "requested_cycles": (data.get("requested_cycles"), scope["cycles"]),
                    "measured_cycles": (data.get("measured_cycles"), scope["cycles"]),
                    "trace_sha256": (data.get("trace_sha256"), expect_hash),
                    "trace.sha256": (data.get("trace", {}).get("sha256"), expect_hash),
                    "outstanding_after_drain": (data.get("wait_acceptance_to_fire", {}).get("outstanding_after_drain"), 0),
                }
                if ref is not None:
                    # The runner's own regeneration must equal the tracked record of the intended
                    # trace (same generator/config/profile as the reference policy run).
                    checks["reference_trace_sha256"] = (expect_hash, ref.get((n_src, seed)))
                for key, value in scope.get("expect_fields", {}).items():
                    checks[key] = (data.get(key), value)
                bad = [f"{k}={got!r} (expected {exp!r})" for k, (got, exp) in checks.items() if got != exp]
                if bad:
                    problems.append(f"run N{n_src} seed {seed}: " + ", ".join(bad))
                    continue
                runs.append((n_src, seed, data, self.rel(path)))
        if len(runs) != scope["expected_runs"]:
            problems.append(f"{len(runs)} valid full-length runs, exactly {scope['expected_runs']} required")
        self._write_primary_summary(scope, runs, problems, ref)
        self.add_step(
            {
                "order": order,
                "kind": "scope",
                "name": name,
                "status": "FAIL" if problems else "PASS",
                "reason": "; ".join(problems[:6]) + (f"; ... {len(problems) - 6} more" if len(problems) > 6 else ""),
                "valid_runs": len(runs),
                "expected_runs": scope["expected_runs"],
                "cycles_per_run": scope["cycles"],
                "summary": "primary_summary.json",
                "log": "primary_summary.json",
                "wall_time_s": round(time.time() - t, 3),
            }
        )

    def _load_reference_hashes(self, scope: dict) -> tuple:
        """Read the tracked intended-trace hash record (TSV n_src, seed, trace_sha256). It must
        cover exactly the declared (N, seed) matrix, once each. Returns (dict, problems)."""
        path = self.repo / scope["reference_hashes"]
        problems: List[str] = []
        table: Dict[tuple, str] = {}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return {}, [f"reference hash record unreadable: {path}: {exc}"]
        if not lines or lines[0].split("\t") != ["n_src", "seed", "trace_sha256"]:
            return {}, [f"reference hash record {scope['reference_hashes']}: unexpected header"]
        for ln in lines[1:]:
            if not ln.strip():
                continue
            cols = ln.split("\t")
            if len(cols) != 3 or not re.fullmatch(r"[0-9a-f]{64}", cols[2]):
                problems.append(f"reference hash record: malformed row {ln!r}")
                continue
            key = (int(cols[0]), int(cols[1]))
            if key in table:
                problems.append(f"reference hash record: duplicate row for N{key[0]} seed {key[1]}")
            table[key] = cols[2]
        expected = {(n, s) for n in scope["n_src"] for s in scope["seeds"]}
        if set(table) != expected:
            problems.append(
                f"reference hash record covers {len(table)} (N, seed) pairs, the declared matrix "
                f"{len(expected)}: missing {sorted(expected - set(table))[:4]}, extra {sorted(set(table) - expected)[:4]}"
            )
        return table, problems

    def _write_primary_summary(self, scope: dict, runs: list, problems: List[str], ref=None) -> None:
        def agg(vals):
            vals = [v for v in vals if v is not None]
            if not vals:
                return None
            return {"min": min(vals), "mean": sum(vals) / len(vals), "max": max(vals), "count": len(vals)}

        per_n = {}
        for n_src in scope["n_src"]:
            rs = [d for n, _s, d, _p in runs if n == n_src]
            w = [d["wait_acceptance_to_fire"] for d in rs]
            per_n[f"N{n_src}"] = {
                "runs": len(rs),
                "accepted_transfer_rate": agg([d["accepted_transfer_rate"] for d in rs]),
                "input_push_rate": agg([d["input_push_rate"] for d in rs]),
                "wait_mean_all_completed": agg([x["all_completed"]["mean"] for x in w]),
                "wait_p99_all_completed": agg([x["all_completed"]["p99_nearest_rank"] for x in w]),
                "wait_max_all_completed": agg([x["all_completed"]["max"] for x in w]),
                "censored_at_measurement_end": agg([x["censored_at_measurement_end"] for x in w]),
                "gen_to_accept_mean": agg([d["generation_to_acceptance"]["mean"] for d in rs]),
                "gen_to_accept_p99": agg([d["generation_to_acceptance"]["p99_nearest_rank"] for d in rs]),
                "generated_but_unaccepted": agg([d["generated_but_unaccepted"] for d in rs]),
                "fires_measurement_total": sum(d["fires_measurement"] for d in rs),
                "input_push_count_total": sum(d["input_push_count"] for d in rs),
                "min_per_source_service": min((min(d["per_source_service_measurement"]) for d in rs), default=None),
                "responses_completed_total": sum(d["responses"]["completed"] for d in rs),
            }
            if rs and all("rr_turns_measurement" in d for d in rs):
                t = [d["rr_turns_measurement"] for d in rs]
                per_n[f"N{n_src}"]["rr_turns_expired_total"] = sum(x["turns_expired"] for x in t)
                per_n[f"N{n_src}"]["rr_turns_emptied_total"] = sum(x["turns_emptied"] for x in t)
                per_n[f"N{n_src}"]["drain_only_pushes_total"] = sum(d["drain_only"]["pushes"] for d in rs)
            if rs and all("fai_measurement" in d for d in rs):
                # FAI Main at the production window: no window closes in the primary length.
                per_n[f"N{n_src}"]["fai_windows_closed_total"] = sum(d["windows_closed_measurement"] for d in rs)
                per_n[f"N{n_src}"]["fcfs_equivalence_checked_cycles_total"] = sum(
                    d["fcfs_equivalence_checked_cycles"] for d in rs
                )
                per_n[f"N{n_src}"]["drain_only_pushes_total"] = sum(d["drain_only"]["pushes"] for d in rs)
        summary = {
            "scope": f"{scope['expected_runs']} runs = N {scope['n_src']} x seeds {scope['seeds'][0]}..{scope['seeds'][-1]} "
            f"x {scope['cycles']} measured cycles, profile {scope['profile']}",
            "full_scope": not problems,
            "problems": problems,
            "reference_hashes": scope.get("reference_hashes"),
            "reference_hash_matches": (
                sum(1 for n, s, d, _p in runs if ref.get((n, s)) == d["trace_sha256"]) if ref is not None else None
            ),
            "valid_runs": len(runs),
            "per_n": per_n,
            "runs": [
                {
                    "n_src": n,
                    "seed": s,
                    "trace_sha256": d["trace_sha256"],
                    "measured_cycles": d["measured_cycles"],
                    "accepted_transfer_rate": d["accepted_transfer_rate"],
                    "input_push_rate": d["input_push_rate"],
                    "wait_mean": d["wait_acceptance_to_fire"]["all_completed"]["mean"],
                    "wait_p99": d["wait_acceptance_to_fire"]["all_completed"]["p99_nearest_rank"],
                    "censored_at_measurement_end": d["wait_acceptance_to_fire"]["censored_at_measurement_end"],
                    "generated_but_unaccepted": d["generated_but_unaccepted"],
                    "per_source_service_measurement": d["per_source_service_measurement"],
                    "metrics_json": p,
                }
                for n, s, d, p in sorted(runs, key=lambda r: (r[0], r[1]))
            ],
        }
        (self.out / "primary_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        lines = [f"{n}\t{s}\t{d['trace_sha256']}" for n, s, d, _p in sorted(runs, key=lambda r: (r[0], r[1]))]
        (self.out / "trace_hashes.tsv").write_text("n_src\tseed\ttrace_sha256\n" + "\n".join(lines) + "\n", encoding="utf-8")

    def run_scope_step(self, order: int, scope: dict) -> None:
        """Full-scope gate of the M5 stress / production matrices (never a test).

        FAILS unless: not lint-only, no --seeds override, every (N, FAI_W, seed) of the declared
        matrix has exactly one PASS cocotb step, and its metrics JSON records the requested seed /
        N / window, ``cycles_by_w[W]`` requested AND measured non-reset cycles, no infra-smoke
        label, nothing outstanding after the drain, the TB's own count of closed windows (exactly
        measured // W and >= ``min_windows`` when declared), and with ``require_all_transitions``
        all 16 (state x evidence) Main transitions reached in that run."""
        name = f"scope:{scope['name']}"
        t = time.time()
        problems: List[str] = []
        if self.args.lint_only:
            problems.append("lint-only run: the scope did not run")
        if self.seeds_override is not None:
            problems.append(f"seed override {self.seeds_override}: not the declared seed set")
        if self.n_filter:
            problems.append(f"N filter {self.n_filter}: not the declared matrix")
        all16 = sorted(f"{s}/{e}" for s in scope.get("states", ("H", "B_H", "L", "B_L"))
                       for e in ("UP", "DOWN", "KEEP", "S0"))
        by_key: Dict[tuple, dict] = {}
        for s in self.steps:
            if s.get("kind") != "cocotb":
                continue
            p = {**s.get("default_params", {}), **s.get("params", {})}
            key = (p.get("N_SRC"), p.get("FAI_W"), s.get("seed"))
            if key in by_key:
                problems.append(f"duplicate run {key}")
            by_key[key] = s
        runs = []
        expected_keys = {(n, w, seed) for n in scope["n_src"] for w in scope["fai_w"] for seed in scope["seeds"]}
        if not expected_keys or set(by_key) != expected_keys:
            problems.append("executed run matrix differs from the declared nonempty matrix")
        for n_src in scope["n_src"]:
            for fai_w in scope["fai_w"]:
                for seed in scope["seeds"]:
                    tag = f"N{n_src} W{fai_w} seed {seed}"
                    st = by_key.get((n_src, fai_w, seed))
                    if st is None:
                        problems.append(f"run {tag} missing")
                        continue
                    if st["status"] != "PASS":
                        problems.append(f"run {tag} status {st['status']}")
                        continue
                    path = self.out / "results" / f"cocotb_{st['name'].split(':', 1)[1]}__{scope['metrics_file']}"
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, ValueError) as exc:
                        problems.append(f"run {tag}: metrics unreadable: {exc}")
                        continue
                    cycles = scope["cycles_by_w"][fai_w]
                    windows = data.get("windows_closed_measurement")
                    checks = {
                        "schema": (data.get("schema"), scope["schema"]),
                        "seed": (data.get("seed"), seed),
                        "n_src": (data.get("n_src"), n_src),
                        "fai_w": (data.get("fai_w"), fai_w),
                        "requested_cycles": (data.get("requested_cycles"), cycles),
                        "measured_cycles": (data.get("measured_cycles"), cycles),
                        "infra_smoke": (data.get("infra_smoke"), False),
                        "outstanding_after_drain": (data.get("outstanding_after_drain"), 0),
                    }
                    checks.update({k: (data.get(k), v) for k, v in scope.get("expect_fields", {}).items()})
                    if "min_windows" in scope:
                        checks["windows_closed_measurement"] = (windows, cycles // fai_w)
                        if not isinstance(windows, int) or windows < scope["min_windows"]:
                            problems.append(f"run {tag}: {windows} complete windows, >= {scope['min_windows']} required")
                    elif not isinstance(windows, int) or windows <= 0:
                        problems.append(f"run {tag}: windows_closed_measurement={windows!r}")
                    if scope.get("require_all_transitions"):
                        checks["transitions_reached"] = (sorted(data.get("transitions_reached") or []), all16)
                    bad = [f"{k}={got!r} (expected {exp!r})" for k, (got, exp) in checks.items() if got != exp]
                    if bad:
                        problems.append(f"run {tag}: " + ", ".join(bad))
                        continue
                    runs.append(
                        {
                            "n_src": n_src,
                            "fai_w": fai_w,
                            "seed": seed,
                            "measured_cycles": data["measured_cycles"],
                            "windows_closed_measurement": windows,
                            "transitions_reached": len(data.get("transitions_reached") or []),
                            "sim_wall_time_s": st.get("sim_wall_time_s"),
                            "metrics_json": self.rel(path),
                        }
                    )
        expected = len(scope["n_src"]) * len(scope["fai_w"]) * len(scope["seeds"])
        if len(runs) != expected:
            problems.append(f"{len(runs)} valid full-length runs, exactly {expected} required")
        summary = {"scope": scope, "full_scope": not problems, "problems": problems, "valid_runs": len(runs), "runs": runs}
        out_name = f"{scope['name']}_summary.json"
        (self.out / out_name).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        self.add_step(
            {
                "order": order,
                "kind": "scope",
                "name": name,
                "status": "FAIL" if problems else "PASS",
                "reason": "; ".join(problems[:6]) + (f"; ... {len(problems) - 6} more" if len(problems) > 6 else ""),
                "valid_runs": len(runs),
                "expected_runs": expected,
                "summary": out_name,
                "log": out_name,
                "wall_time_s": round(time.time() - t, 3),
            }
        )

    # ----- orchestration ------------------------------------------------------------------------

    def plan(self) -> dict:
        cocotb_jobs = []
        if not self.args.lint_only:
            for cfg in self.entry.get("cocotb", []):
                seeds = self.seeds_override if self.seeds_override is not None else cfg["seeds"]
                if not seeds:
                    raise SystemExit(f"run_verify: cocotb entry {cfg['name']} has no seeds")
                if self.n_filter and cfg["params"].get("N_SRC") not in self.n_filter:
                    continue
                cocotb_jobs += [(cfg, seed) for seed in seeds]
        if self.n_filter and not self.args.lint_only and not cocotb_jobs:
            raise SystemExit(f"run_verify: --n-src {self.n_filter} selects no cocotb job of {self.milestone}")
        return {
            "lint": self.entry.get("lint", []),
            "elab_reject": self.entry.get("elab_reject", []),
            "elab_probe": self.entry.get("elab_probe", []),
            "pytest": [] if self.args.lint_only else self.entry.get("pytest", []),
            "cocotb": cocotb_jobs,
        }

    def execute(self) -> int:
        plan = self.plan()
        self.write_versions()
        self.write_config(
            {
                "lint": plan["lint"],
                "elab_reject": plan["elab_reject"],
                "elab_probe": plan["elab_probe"],
                "pytest": plan["pytest"],
                "cocotb": [{**cfg, "seeds": None, "seed": seed} for cfg, seed in plan["cocotb"]],
            }
        )
        (self.milestone_dir / "latest.txt").write_text(self.run_id + "\n", encoding="utf-8")
        print(f"run_verify: milestone {self.milestone} run-id {self.run_id}", flush=True)
        print(f"run_verify: evidence {self.out}", flush=True)
        if not plan["lint"]:
            raise SystemExit(f"run_verify: milestone {self.milestone} declares no lint configuration")

        order = 0
        skip = "skipped by fail-fast after an earlier failure"
        for cfg in plan["lint"]:
            order += 1
            if self.abort.is_set():
                self.not_run(order, "lint", f"lint:{cfg['name']}", skip)
            else:
                self.lint_step(order, cfg)
        for cfg in plan["elab_reject"]:
            order += 1
            if self.abort.is_set():
                self.not_run(order, "elab_reject", f"elab_reject:{cfg['name']}", skip)
            else:
                self.elab_reject_step(order, cfg)
        for cfg in plan["elab_probe"]:
            order += 1
            if self.abort.is_set():
                self.not_run(order, "elab_probe", f"elab_probe:{cfg['name']}", skip)
            else:
                self.elab_probe_step(order, cfg)
        for cfg in plan["pytest"]:
            order += 1
            if self.abort.is_set():
                self.not_run(order, "pytest", f"pytest:{cfg['name']}", skip)
            else:
                self.pytest_step(order, cfg)

        if plan["cocotb"]:
            workers = max(1, min(self.args.jobs, len(plan["cocotb"])))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = []
                for cfg, seed in plan["cocotb"]:
                    order += 1
                    futures.append((pool.submit(self.cocotb_job, order, cfg, seed), order, cfg, seed))
                for fut, job_order, cfg, seed in futures:
                    try:
                        fut.result()
                    except Exception as exc:  # runner defect: never a silent pass
                        self.add_step(
                            {
                                "order": job_order,
                                "kind": "cocotb",
                                "name": f"cocotb:{cfg['name']}_seed{seed}",
                                "status": "FAIL",
                                "reason": f"runner exception: {exc!r}",
                                "log": f"logs/cocotb_{cfg['name']}_seed{seed}.log",
                                "seed": seed,
                            }
                        )

        # Full-scope gates. Not evaluated for an infrastructure smoke run (which is labelled
        # INFRA_SMOKE_* and never acceptance evidence, see write_summary).
        if "primary_scope" in self.entry and not self.smoke:
            order += 1
            self.primary_scope_step(order, self.entry["primary_scope"])
        if "run_scope" in self.entry and not self.smoke:
            order += 1
            self.run_scope_step(order, self.entry["run_scope"])

        overall = self.write_summary(final=True)
        self.print_table(overall)
        return 0 if overall in ("PASS", "INFRA_SMOKE_PASS") else 1

    def print_table(self, overall: str) -> None:
        print("")
        print(f"{'step':44s} {'status':8s} {'tests':>5s} {'fail':>5s} {'err':>5s} {'skip':>5s}")
        for s in sorted(self.steps, key=lambda s: s["order"]):
            cols = [str(s.get(k, "-")) for k in ("tests", "failures", "errors", "skipped")]
            print(f"{s['name']:44s} {s['status']:8s} {cols[0]:>5s} {cols[1]:>5s} {cols[2]:>5s} {cols[3]:>5s}")
        rejected = sum(1 for s in self.steps if s["status"] == XREJECT)
        if rejected:
            print(
                f"\n{XREJECT} = {XREJECT_LABEL}: {rejected} negative elaboration check(s), "
                "0 tests, not counted in any test total."
            )
        scope = " (lint-only scope: NOT milestone acceptance)" if self.args.lint_only else ""
        if self.seeds_override is not None:
            scope += " (seed override: NOT the milestone seed set)"
        if self.n_filter:
            scope += f" (N filter {self.n_filter}: NOT the milestone matrix)"
        if self.smoke:
            scope += f" (INFRASTRUCTURE SMOKE, {self.args.cycles} cycles: NOT milestone evidence, scope gates not evaluated)"
        print(f"\nrun_verify: {self.milestone} {overall}{scope}  [{time.time() - self.t0:.1f}s]")
        print(f"run_verify: summary {self.out / 'summary.json'}", flush=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_verify.sh", description="Fail-fast lint/pytest/cocotb runner (see file header)."
    )
    parser.add_argument("milestone", nargs="?", help="milestone name, e.g. M1")
    parser.add_argument("--seeds", help="override cocotb seeds: a..b or comma list")
    parser.add_argument("--lint-only", action="store_true", help="run only the lint configurations")
    parser.add_argument("--keep-going", action="store_true", help="run every step even after a failure")
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="parallel cocotb jobs, each in its own build directory (default: min(8, cores))",
    )
    parser.add_argument("--make-jobs", type=int, default=2, help="make -j inside each cocotb build")
    parser.add_argument("--list", action="store_true", help="list the milestone table and exit")
    parser.add_argument(
        "--cocotb-timeout",
        type=int,
        default=None,
        help="override the per-simulation timeout in seconds (default: the entry's timeout_s, else "
        f"{STEP_TIMEOUT_S}); recorded in config/summary",
    )
    parser.add_argument(
        "--infra-smoke",
        action="store_true",
        help="INFRASTRUCTURE SMOKE (never milestone evidence): run the scope's harness with --cycles "
        "instead of its declared length (only scopes that declare smoke_env); scope gates are not "
        "evaluated; evidence goes to artifacts/implementation/<milestone>-infra-smoke/",
    )
    parser.add_argument("--cycles", type=int, default=None, help="cycle count of an --infra-smoke run")
    parser.add_argument("--n-src", help="with --infra-smoke only: restrict cocotb jobs to these N (comma list)")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)

    if args.list:
        for name, entry in MILESTONES.items():
            state = "implemented" if entry.get("implemented") else "NOT IMPLEMENTED"
            print(f"{name}: {state} - {entry['description']}")
            print("    " + _plan_counts(entry))
        return 0
    if not args.milestone:
        parser.print_usage(sys.stderr)
        print("run_verify: a milestone is required", file=sys.stderr)
        return 2
    if args.milestone not in MILESTONES:
        print(
            f"run_verify: milestone {args.milestone!r} is not defined "
            f"(known: {', '.join(MILESTONES)}). Nothing was run; this is not a pass.",
            file=sys.stderr,
        )
        return 2
    if not MILESTONES[args.milestone].get("implemented"):
        print(
            f"run_verify: milestone {args.milestone} "
            f"({MILESTONES[args.milestone]['description']}) is declared but not implemented in the "
            "runner table. Nothing was run; this is not a pass.",
            file=sys.stderr,
        )
        return 2
    if args.jobs < 1 or args.make_jobs < 1:
        print("run_verify: -j/--make-jobs must be >= 1", file=sys.stderr)
        return 2
    try:
        args.seed_list = parse_seeds(args.seeds) if args.seeds else None
    except ValueError as exc:
        print(f"run_verify: bad --seeds value: {exc}", file=sys.stderr)
        return 2
    entry = MILESTONES[args.milestone]
    if args.infra_smoke:
        if not entry.get("smoke_env"):
            print(f"run_verify: {args.milestone} declares no smoke_env; --infra-smoke is not available", file=sys.stderr)
            return 2
        if args.cycles is None or args.cycles < 1 or args.lint_only:
            print("run_verify: --infra-smoke needs --cycles >= 1 and no --lint-only", file=sys.stderr)
            return 2
    elif args.cycles is not None or args.n_src:
        print("run_verify: --cycles / --n-src are only valid with --infra-smoke", file=sys.stderr)
        return 2
    if args.cocotb_timeout is not None and args.cocotb_timeout < 1:
        print("run_verify: --cocotb-timeout must be >= 1", file=sys.stderr)
        return 2
    try:
        args.n_src_list = sorted({int(x) for x in args.n_src.split(",")}) if args.n_src else None
    except ValueError:
        print(f"run_verify: bad --n-src value {args.n_src!r}", file=sys.stderr)
        return 2
    return Run(args, Path(args.repo_root).resolve()).execute()


def _plan_counts(entry: dict) -> str:
    """One-line truthful plan of a table entry, computed from the entry itself."""
    cocotb = entry.get("cocotb", [])
    jobs = sum(len(c["seeds"]) for c in cocotb)
    tests = sum(len(c["seeds"]) * c.get("expect_tests", 0) for c in cocotb)
    parts = [
        f"lint={len(entry.get('lint', []))}",
        f"elab_reject(XREJECT)={len(entry.get('elab_reject', []))}",
        f"elab_probe={len(entry.get('elab_probe', []))}",
        "pytest=" + (",".join(f"{p['target']}:{p.get('expect_tests')}" for p in entry.get("pytest", [])) or "0"),
        f"cocotb configs={len(cocotb)} jobs={jobs} tests={tests}",
    ]
    envs = sorted({f"{k}={v}" for c in cocotb for k, v in c.get("env", {}).items()})
    if envs:
        parts.append("env " + " ".join(envs))
    timeouts = sorted({c.get("timeout_s", STEP_TIMEOUT_S) for c in cocotb})
    if cocotb:
        parts.append("sim timeout(s)=" + "/".join(str(t) for t in timeouts))
    if "primary_scope" in entry:
        parts.append(f"gate primary_full_matrix({entry['primary_scope']['expected_runs']} runs)")
    if "run_scope" in entry:
        rs = entry["run_scope"]
        parts.append(f"gate {rs['name']}({len(rs['n_src']) * len(rs['fai_w']) * len(rs['seeds'])} runs)")
    if entry.get("smoke_env"):
        parts.append("infra-smoke via " + ",".join(entry["smoke_env"]))
    return "; ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
