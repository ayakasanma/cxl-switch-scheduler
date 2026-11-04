#!/usr/bin/env python3
"""Offline CGOF DC/PT and Formality preparation; never contacts an EDA host."""

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

import prepare_ppa_run as base

sys.path.insert(0, str(base.ROOT))
import run_revision_cgof_experiments as gates

ROOT = base.ROOT
OUTPUT_ROOT = ROOT / ".setup-logs/implementation/revision-20261023/cgof-ppa"
PROFILE = "syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json"
PROFILE_SHA = base.ALG2_PROFILE_SHA256
TEMPLATE = "artifacts/fastx/formality-current-main-bridge/reports/equiv.tcl"
TEMPLATE_SHA = "6f48a8fac946ff02e2394955e75bb2ecf8cbed5b3676c827f2c8c6200c46cdf5"
TOP = "cgof_unit_top"
FILELIST = "rtl/experimental/filelist_cgof_unit.f"
SOURCES = [
    "rtl/include/cxl_sched_pkg.sv", "rtl/common/cxl_desc_fifo.sv",
    "rtl/common/cxl_out_hold.sv", "rtl/common/cxl_fcfs_sel.sv",
    "rtl/experimental/cxl_cgof_sched.sv", "rtl/experimental/cgof_unit_top.sv",
]
NETLIST = f"output/{TOP}.syn.v"
SDC = f"output/{TOP}.syn.sdc"
RUN = "cxl-ppa-syn-cgof2-n4"
REFERENCE = "r:/WORK/cgof_unit_top_N_SRC4_DEPTH16_FAI_W5000000_HIGH_WEIGHT2"
SUPPORTED_N = (4, 8, 16)
SUPPORTED_HIGH_WEIGHT = (1, 2)
OWN_FILES = ("scripts/prepare_revision_cgof_ppa.py", "scripts/test_prepare_revision_cgof_ppa.py",
             "docs/experiments/diagnosis-20261027/README.md")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"shared template changed at {old!r}")
    return text.replace(old, new)


def run_name(n_src=4, high_weight=2):
    if n_src not in SUPPORTED_N or high_weight not in SUPPORTED_HIGH_WEIGHT:
        raise ValueError("CGOF PPA supports N_SRC=4/8/16 and HIGH_WEIGHT=1/2")
    return f"cxl-ppa-syn-cgof{high_weight}-n{n_src}"


def reference(n_src=4, high_weight=2):
    if n_src not in SUPPORTED_N or high_weight not in SUPPORTED_HIGH_WEIGHT:
        raise ValueError("CGOF PPA supports N_SRC=4/8/16 and HIGH_WEIGHT=1/2")
    return (f"r:/WORK/{TOP}_N_SRC{n_src}_DEPTH16_FAI_W5000000_"
            f"HIGH_WEIGHT{high_weight}")


def parameters(n_src=4, high_weight=2):
    if n_src not in SUPPORTED_N or high_weight not in SUPPORTED_HIGH_WEIGHT:
        raise ValueError("CGOF PPA supports N_SRC=4/8/16 and HIGH_WEIGHT=1/2")
    params = base.parameters("fai-main", n_src)
    del params["POLICY"], params["RR_QUANTUM"]
    params.update(top_module=TOP, policy_name="CGOF", DEPTH=16, HIGH_WEIGHT=high_weight,
                  elab_parameters=f"N_SRC={n_src},DEPTH=16,FAI_W=5000000,"
                                  f"HIGH_WEIGHT={high_weight}")
    params["expected"].update(
        policy_module="cxl_cgof_sched",
        forbidden_modules=["cxl_rr_sched", "cxl_fai_main_sched", "cxl_fai_variant_sched"])
    # Declared RTL state, not an assertion about optimized mapped flip-flop count.
    params["declared_state_bits"] = dict(
        descriptor_storage=n_src*16*105, timestamp_storage=n_src*16*32,
        fifo_read_write_pointers=n_src*2*4, fifo_occupancy=n_src*5, arrival_counter=32,
        hold_valid=1, hold_source=(n_src - 1).bit_length(),
        hold_context=(n_src + 1) if high_weight > 1 else 1,
        classes=n_src*2, window_index=23, per_source_fire_counters=n_src*23,
        total_fire_counter=23,
        credits=n_src * (high_weight.bit_length()))
    params["declared_total_state_bits"] = sum(params["declared_state_bits"].values())
    params["threshold_arithmetic_bits"] = 32
    params["hold_descriptor_storage"] = "selected FIFO head retained until fire; no separate descriptor bank"
    return params


def render_config(params, library, profile, run_name_value=None):
    compat = dict(params, POLICY=2, RR_QUANTUM=10)
    name = run_name_value or run_name(params["N_SRC"], params["HIGH_WEIGHT"])
    text = base.run_config("syn", name, compat, library, SOURCES, profile, PROFILE_SHA).decode("ascii")
    for old, new in [
        ("set TOP_MODULE {switch_top}", f"set TOP_MODULE {{{TOP}}}"),
        ("set PARAM_POLICY 2\n", ""), ("set PARAM_RR_QUANTUM 10\n", ""),
        (f"set NETLIST_FILE {{{base.NETLIST}}}", f"set NETLIST_FILE {{{NETLIST}}}"),
        (f"set SDC_FILE {{{base.SDC}}}", f"set SDC_FILE {{{SDC}}}"),
    ]:
        text = replace_once(text, old, new)
    return (text + f"set PARAM_DEPTH 16\nset PARAM_HIGH_WEIGHT {params['HIGH_WEIGHT']}\n").encode("ascii")


def render_dc_pt_runner(library, profile, run_name_value=None, netlist=None):
    name = run_name_value or RUN
    netlist = netlist or NETLIST
    text = base.render_run_sh(dict(RUN_NAME=name, MODE="syn", TARGET_LIBRARY=library,
                                  LIBRARY_SHA256=profile["library"]["sha256"],
                                  PROFILE_STATUS=profile["status"], NETLIST=netlist, SDC=SDC)).decode("ascii")
    text = replace_once(text, "module[[:space:]]+switch_top", f"module[[:space:]]+{TOP}")
    text = replace_once(text, "netlist has no switch_top module", f"netlist has no {TOP} module")
    return replace_once(text, 'sha256sum -- "$NETLIST" "$SDC" > logs/dc-handoff.sha256',
                        'sha256sum -- "$NETLIST" "$SDC" default.svf > logs/dc-handoff.sha256').encode("ascii")


def render_formal(template, params=None):
    if sha(template) != TEMPLATE_SHA:
        raise ValueError("audited Formality bridge template hash changed")
    params = params or parameters()
    text = template.decode("ascii")
    n_src, high_weight = params["N_SRC"], params["HIGH_WEIGHT"]
    text = replace_once(
        text, "$PARAM_N_SRC ni {8 16} || $PARAM_POLICY != 2 ||\n"
        "     $PARAM_RR_QUANTUM != 10 || $PARAM_FAI_W != 5000000",
        f"$TOP_MODULE ne \"{TOP}\" || $PARAM_N_SRC != {n_src} || $PARAM_DEPTH != 16 ||\n"
        f"     $PARAM_HIGH_WEIGHT != {high_weight} || $PARAM_FAI_W != 5000000")
    text = replace_once(text, " set base $::env(CXL_FM_ACCEPTED)",
                        " set base [file dirname [file normalize [info script]]]")
    text = replace_once(text, "$::env(CXL_FM_REFERENCE_ROOT)/$name", "$base/$name")
    text = text.replace("switch_top", TOP)
    text = replace_once(
        text, f"r:/WORK/{TOP}_N_SRC${{PARAM_N_SRC}}_POLICY${{PARAM_POLICY}}_RR_QUANTUM10_FAI_W5000000",
        reference(n_src, high_weight))
    return replace_once(
        text, " redirect reports/unmatched.rpt {report_unmatched_points}",
        " redirect reports/undriven-after-match.rpt {report_undriven_nets}\n"
        " redirect reports/unmatched.rpt {report_unmatched_points}").encode("ascii")


FORMAL_RUNNER = r"""#!/usr/bin/env bash
# Separate, parent-reviewed invocation AFTER DC/PT; never accepted PPA or formal PASS.
set -euo pipefail
umask 022
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
test ! -e formal
grep -qx COMMANDS_COMPLETED_REVIEW_REQUIRED execution-status.txt
sha256sum --strict -c SHA256SUMS
sha256sum --strict -c logs/dc-handoff.sha256
printf '%s  %s\n' '@@LIBRARY_SHA@@' '@@LIBRARY@@' | sha256sum --strict -c -
mkdir formal
exec > >(tee formal/wrapper.log) 2>&1
trap 'rc=$?; printf "wrapper=%s\n" "$rc" > formal/wrapper-exit.txt' EXIT
if type module >/dev/null 2>&1; then
  module load "${EDA_MODULE:-Synopsys_x86-64/2024}"
  module list > formal/module-list.txt 2>&1
fi
command -v fm_shell > formal/tool-path.txt
test -x /usr/bin/timeout
date -u +%FT%TZ > formal/start-utc.txt
sha256sum -- @@INPUTS@@ > formal/source-before.sha256
cd formal
mkdir reports
set +e
/usr/bin/timeout 15m fm_shell -f ../equiv.tcl < /dev/null > reports/fm.log 2>&1
rc=$?
set -e
printf 'fm=%s\n' "$rc" > reports/exits.txt
cd ..
date -u +%FT%TZ > formal/end-utc.txt
sha256sum -- @@INPUTS@@ > formal/source-after.sha256
cmp formal/source-before.sha256 formal/source-after.sha256
sha256sum --strict -c SHA256SUMS
sha256sum --strict -c logs/dc-handoff.sha256
test "$rc" -eq 0
grep -qx 'verify_return=1' formal/reports/result.txt
grep -qx CXL_FM_COMMANDS_COMPLETED_REVIEW_REQUIRED formal/reports/fm.log
if grep -E '^[[:space:]]*(Error|ERROR|Fatal|FATAL)[[:space:]]*:|^CXL_FM_ERROR:' formal/reports/*; then
  exit 1
fi
find formal -type f ! -name RESULT_SHA256SUMS ! -name wrapper.log ! -name wrapper-exit.txt -print0 |
  sort -z | xargs -0 sha256sum > formal/RESULT_SHA256SUMS
printf 'COMMANDS_COMPLETED_REVIEW_REQUIRED\nNo automatic formal acceptance; review every compare point and setup report.\n' > formal/execution-status.txt
"""


def prepare(library, output, native_directory, n_src=4, high_weight=2):
    if sys.flags.optimize:
        raise ValueError("optimized Python is forbidden by the reused native validators")
    library = base.validate_library(library)
    profile, raw = base.load_profile(ROOT / PROFILE, library)
    if sha(base.canonical_json(profile)) != PROFILE_SHA:
        raise ValueError("only the frozen matched primary TT25ns cap075-v2 profile is allowed")
    bindings = gates.verify_native(native_directory)  # Read archived evidence only; no tests/EDA.
    native_scope = json.loads((native_directory / "cgof_scope.json").read_text())
    template = base.safe_repo_file(ROOT, TEMPLATE).read_bytes()
    state = base.source_state(ROOT)
    names = sorted(set(gates.source_paths()) | {
        base.APPROVAL, base.DC_SCRIPT, base.PT_SCRIPT,
        "scripts/prepare_ppa_run.py", PROFILE, TEMPLATE, *OWN_FILES})
    contents = {name: base.safe_repo_file(ROOT, name).read_bytes() for name in names}
    listed = [line.split("//", 1)[0].strip() for line in contents[FILELIST].decode().splitlines()]
    if [line for line in listed if line] != SOURCES:
        raise ValueError("native CGOF filelist order/membership changed")
    for name in SOURCES + [FILELIST]:
        if sha(contents[name]) != native_scope["source_hashes_before"][name]:
            raise ValueError("CGOF source differs from accepted native archive: " + name)
    approval = base.approval_record(contents[base.APPROVAL])
    payload_name = run_name(n_src, high_weight)
    name = payload_name
    params = parameters(n_src, high_weight)
    files = {name: contents[name] for name in SOURCES + [FILELIST, base.APPROVAL,
                                                       base.DC_SCRIPT, base.PT_SCRIPT]}
    files.update({
        "run_config.tcl": render_config(params, library, profile),
        "parameters.json": (json.dumps(params, indent=2)+"\n").encode("ascii"),
        "profile.json": (json.dumps(profile, indent=2, sort_keys=True)+"\n").encode("ascii"),
        "run.sh": render_dc_pt_runner(library, profile, name),
        "equiv.tcl": render_formal(template, params),
        "expected/dc_status.rpt": base.dc_marker("syn", name, params).replace(b"switch_top", TOP.encode()),
        "expected/pt_status.rpt": base.pt_marker(name).replace(b"switch_top", TOP.encode()),
    })
    dc_required = [p.replace("switch_top", TOP) for p in base.DC_REQUIRED_SYN]
    dc_required += ["reports/dc_cap_optimization.rpt", "default.svf"]
    files["expected/dc_required.txt"] = ("\n".join(dc_required)+"\n").encode("ascii")
    files["expected/pt_required.txt"] = ("\n".join(base.PT_REQUIRED)+"\n").encode("ascii")
    formal_inputs = SOURCES + ["run_config.tcl", "manifest.json", "equiv.tcl",
                              NETLIST, SDC, "default.svf", library]
    files["run-formal.sh"] = FORMAL_RUNNER.replace(
        "@@INPUTS@@", " ".join("'" + name + "'" for name in formal_inputs)).replace(
        "@@LIBRARY_SHA@@", profile["library"]["sha256"]).replace(
        "@@LIBRARY@@", library).encode("ascii")
    records = []
    for name in SOURCES + [FILELIST]:
        blob = base.git_blob_id(contents[name])
        committed = base.head_blob(ROOT, state["head"], name)
        records.append(dict(path=name, sha256=sha(contents[name]), git_blob=blob,
                            head_blob=committed, matches_head=blob == committed,
                            acceptance="accepted-native-source-hash"))
    manifest = dict(
        schema="cxl-revision-cgof-ppa-preparation-v1", generator=OWN_FILES[0],
        prepared_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        run_name=payload_name, parameters=params, source={**state, "exported_files": records},
        approval=approval, native_directory=str(native_directory.resolve()),
        native_bindings=bindings, input_sha256={n: sha(b) for n, b in contents.items()},
        profile_canonical_sha256=PROFILE_SHA, profile_source_sha256=sha(raw),
        target_library=dict(remote_path=library, sha256=profile["library"]["sha256"],
                            content_bundled=False),
        formal_reference=reference(n_src, high_weight), formal_template_sha256=TEMPLATE_SHA,
        required_outputs=dict(dc=dc_required, pt=base.PT_REQUIRED),
        status="PREPARED_NOT_RUN", remote_execution_authorized=False,
        limitations="Pre-layout comparative area/STA only; power NOT_RUN; no physical signoff.",
        file_sha256={n: sha(b) for n, b in sorted(files.items())})
    files["manifest.json"] = (json.dumps(manifest, indent=2)+"\n").encode("ascii")
    files["SHA256SUMS"] = "".join(f"{sha(b)}  {n}\n" for n, b in sorted(files.items())).encode("ascii")
    base.check_payload(files)
    if any(base.safe_repo_file(ROOT, n).read_bytes() != b for n, b in contents.items()):
        raise ValueError("preparation input changed during freeze")
    if any(gates.sha(Path(p)) != h for p, h in bindings.items()):
        raise ValueError("accepted native evidence changed during freeze")
    output = output.resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output == OUTPUT_ROOT.resolve():
        raise ValueError("output must be a fresh child of the adapter's ignored log directory")
    output.mkdir(parents=True, exist_ok=False)
    payload = output / payload_name
    for name, data in files.items():
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    base.write_tar(output / "payload.tar", payload_name, files, state["head_commit_time"])
    result = dict(status="PREPARED_NOT_RUN", output=str(output), payload=str(payload),
                  payload_tar_sha256=sha((output / "payload.tar").read_bytes()),
                  source_manifest_sha256=sha(files["manifest.json"]),
                  commands_after_parent_review=[f"cd <fresh-remote-root>/{payload_name} && bash ./run.sh",
                                                f"cd <fresh-remote-root>/{payload_name} && bash ./run-formal.sh"])
    (output / "preparation.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, help="existing remote .db path; never read locally")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--native-directory", required=True, type=Path,
                        help="complete correctness run matching the current CGOF sources")
    parser.add_argument("--n-src", type=int, choices=SUPPORTED_N, default=4)
    parser.add_argument("--high-weight", type=int, choices=SUPPORTED_HIGH_WEIGHT, default=2)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.library, args.output, args.native_directory,
                                 args.n_src, args.high_weight), indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
