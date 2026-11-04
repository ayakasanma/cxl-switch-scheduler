# Ordering RTL exploration correction plan

Date: 2026-11-01. Status: `PLANNED_CORRECTED_EXPLORATION`.
Scope: `SCHEDULER_RTL`, N4/D16/W256, five fresh seeds, 40 jobs, 20
mixed/isolated pairs. This remains a bounded exploratory matrix, not
confirmation, production evaluation, PPA, formal/CDC, CXL-response, bandwidth,
application, or latency-recovery evidence.

## Provenance

- Requested planning model: `GPT6Astra(high)`.
- Spawn result: `Unknown model`; no Astra run is claimed.
- Owner-approved fallback: `group/gpt-6.1-sol`, high effort.
- Backend effective model: `UNKNOWN`; a routing/request label is not backend
  model evidence.
- Repository: `C:\Users\USER\Documents\Coding Space\CXL\cxl-scheduler`.
- Branch: `experiment/main-sq`.
- HEAD: `99400ded42cc63c3b206bd5d13f51d36344b2689`.
- The worktree contains pre-existing user changes and untracked files. Preserve
  them. Do not reset, clean, stash, commit, replace, or rewrite evidence.

This file is read-only planning. It does not alter the original plan,
the failed run, the 6201 smoke, source code, or historical artifacts.

## Preserved failed design and run

Original design:

- `docs/reviews/ordering-rtl-exploration-plan-20261101.md`
- SHA-256 at correction-planning time:
  `181900933e327c7b29efee2100f277da44d16b25752b4d700e341a4d29991444`
- Fixed `heavy_work=1024`, seeds `6301-6305`.

Failed seed-6301 evidence:

- Run root:
  `artifacts/implementation/cgof-rtl-ordering-exploration/20261101T024757Z_2732/`
- `summary.json` SHA-256:
  `4e87dd9ed18794d160df26fe7e7076b9d638a799f3b6a5562a165b0b3d933b1d`
- `diagnosis_scope.json` SHA-256:
  `c386ad2fa3e0e62a734b7a03392728f9a99bef5cf8ee25fbce703467ba4d46a0`
- `sources.zip` SHA-256:
  `3f27e11abdc4a5653a6e47cdbfcf1ab7ce6fdce62e296b5709a02488451f6db4`
- `commands.txt` SHA-256:
  `2433c2dea878d7ac605e508bf946bb74885e4f83377084354f427b1061189a72`
- `config.json` SHA-256:
  `36fa3338b135debfe7f04236185bc8eb3b82ef40383bb6a06b2e8980881c3401`

The run's execution checks passed, but its scientific manipulation control did
not. All eight jobs had `active_cycles=1283` and classifier closes at
`255, 511, 767, 1023, 1279`. Source 0 was `B_H` (effective High) after the first
close, then `L` (effective Low) after the second close. Across the eight jobs,
the observed `old_classes`/`classes` snapshots contain `L`, so the fixed-class
premise is `NOT_HELD`. Seeds `6302-6305` were correctly not executed.

Do not reuse seed 6301, reinterpret its endpoints, or mix it into the corrected
matrix. It remains failure/manipulation evidence only.

## Corrected bounded matrix

Change only the treatment length and seed set:

| Factor | Corrected value |
| --- | --- |
| Sources / depth / window | N4 / D16 / W256 |
| Mode | `finite-heavy` |
| Offered load | `near` |
| Heavy work | **256 requests per lane** |
| Heavy source schedule | Default source 0 (`--windows 1`) |
| Sink readiness | `bursty`, `ready_p=0.90`, period 100 |
| Quotas | `CGOF(1:1)` and `CGOF(2:1)` |
| Orderings | `oldest-first` and `eligible-round-robin` |
| Lanes | `mixed` and `isolated` |
| Fresh seeds | **6401, 6402, 6403, 6404, 6405** |

The four setting IDs remain:

| ID | High:Low | Ordering |
| --- | --- | --- |
| `Q1-OF` | 1:1 | oldest-first |
| `Q1-RR` | 1:1 | eligible-round-robin |
| `Q2-OF` | 2:1 | oldest-first |
| `Q2-RR` | 2:1 | eligible-round-robin |

Each `(seed, setting)` has one `mixed` and one `isolated` lane:

- 5 seeds × 4 settings × 2 lanes = **40 jobs**.
- 5 seeds × 4 settings = **20 mixed/isolated pairs**.
- Per seed: 8 jobs, 4 pairs, 4 matched ordering contrasts and 4 matched quota
  contrasts after separating lanes.

Do not add seeds, profiles, ready patterns, role switching, depths, or windows
after seeing results. The new output timestamps must be later than the failed
run; the evidence namespace remains:

```text
artifacts/implementation/cgof-rtl-ordering-exploration/<new-run-id>/
```

## Required manipulation check

Run the manipulation check after each seed command and before launching the next
seed. A seed passes only when all four conditions hold for all eight jobs:

1. `diagnosis_scope.json` has status `PASS`, 8 results, 4 finite-Heavy pairs,
   and `source_stable=true`.
2. `data.classifier` is nonempty; at least one window close was observed.
3. Every state in both `old_classes` and `classes` maps to effective `High`
   through `cxl_model.fai_main_model.EFFECTIVE_CLASS`. `H` and `B_H` are allowed;
   any `L`, `B_L`, unknown state, or other effective class fails the control.
4. The run remains within the first classification window:
   `active_cycles < 512` and every observed `closing_cycle` is `255`.

If the active interval ends before close 255, any non-High effective state
appears, or a second close appears, stop immediately with
`MANIPULATION_NOT_HELD`. Preserve that run and do not execute later seeds.
Execution failure and manipulation failure are distinct: the former invalidates
the harness result; the latter invalidates only the fixed-class interpretation.

## Corrected metric paths

In `diagnosis_scope.json`, endpoint paths start at `results[].data`. In an
individual raw `results/*.json`, remove the `results[].data` wrapper:

| Endpoint | Correct canonical path |
| --- | --- |
| Sparse completed G→F P99 | `data.generation_roles.latency.sparse.generation_to_fire.p99_nearest_rank` |
| Heavy max wall gap | `data.heavy.max_wall_gap` |
| Heavy pooled max wall gap cross-check | `data.generation_roles.heavy_gaps.samples.inter_service.wall_cycles.max` |
| Heavy wall-gap P99 | `data.generation_roles.heavy_gaps.samples.inter_service.wall_cycles.p99_nearest_rank` |
| Heavy ready-opportunity P99 | `data.generation_roles.heavy_gaps.samples.inter_service.eligible_ready_opportunities.p99_nearest_rank` |
| Mixed/isolated active-cycle ratio | `finite_heavy_pairs[].heavy_active_cycle_ratio_mixed_over_isolated` |

`data.heavy.max_wall_gap` must be non-null and equal to the pooled diagnostic
cross-check; mismatch is a harness failure. Sparse P99 is `UNAVAILABLE`, not
zero, when its completed count is zero. The active-cycle ratio is not a
completed-byte, bandwidth, or throughput ratio.

For every job retain `active_cycles`, `drain_cycles`, generated/accepted/fired,
generation-role cohorts, classifier rows, Heavy completion, Sparse censoring,
native coverage, and credit/refill counters. For every matched contrast report
reference value, candidate value, and `candidate - reference`.

## No-ranking and no-inference rules

- Sparse endpoints apply only to mixed lanes.
- Do not aggregate quotas, orderings, lanes, or seeds into a score or rank.
- Do not compute p-values, confidence intervals, equivalence margins, or a
  universal winner in this round.
- Five seeds are exploratory. Repeating a direction on all five permits only a
  bounded directional observation.
- `fire/cycle` is not memory bandwidth; G→F is not CXL response latency.
- No PPA, formal/CDC, calibrated CXL, application slowdown, W5M production, or
  system-level conclusion is supported.

## Exact execution commands

The manipulation checker below reads the newly updated namespace-local
`latest.txt`; it does not modify historical evidence.

```bash
cd '/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler'
source scripts/wsl_env.sh
set -euo pipefail
export PYTHONPATH="$PWD/scripts:$PWD"

PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider \
  scripts/test_run_rtl_diagnosis.py \
  sim/experimental/test_cgof_diagnosis_traffic.py \
  refc/tests/test_diagnosis.py

check_manipulation() {
  local scope_file="$1"
  python -B - "$scope_file" <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "refc"))
from cxl_model.fai_main_model import EFFECTIVE_CLASS, HIGH

path = Path(sys.argv[1])
scope = json.loads(path.read_text(encoding="utf-8"))
if scope.get("status") != "PASS":
    raise SystemExit("MANIPULATION_NOT_HELD: scope status is not PASS")
if len(scope.get("results", ())) != 8 or len(scope.get("finite_heavy_pairs", ())) != 4:
    raise SystemExit("MANIPULATION_NOT_HELD: expected 8 results and 4 pairs")
if scope.get("source_stable") is not True:
    raise SystemExit("MANIPULATION_NOT_HELD: source hashes changed")

for item in scope["results"]:
    data = item["data"]
    closes = data.get("classifier") or []
    if not closes:
        raise SystemExit(
            f"MANIPULATION_NOT_HELD: no close in {item['job']['lane']} "
            f"{item['job']['high_weight']}:{item['job']['ordering']}"
        )
    if data["active_cycles"] >= 512:
        raise SystemExit("MANIPULATION_NOT_HELD: active interval leaves first window")
    for row in closes:
        if row["closing_cycle"] != 255:
            raise SystemExit("MANIPULATION_NOT_HELD: close outside first window")
        states = list(row["old_classes"]) + list(row["classes"])
        if any(EFFECTIVE_CLASS[state] != HIGH for state in states):
            raise SystemExit(
                f"MANIPULATION_NOT_HELD: non-High state in {states!r}"
            )

print(f"MANIPULATION_HELD: {path.parent.name}")
PY
}

run_order_seed() {
  local seed="$1"
  local root="$PWD/artifacts/implementation/cgof-rtl-ordering-exploration"
  timeout --foreground 1800 \
    python -B -c 'import sys, run_rtl_diagnosis as r; r.NAME="cgof-rtl-ordering-exploration"; raise SystemExit(r.main(sys.argv[1:]))' \
      --smoke --window 256 --mode finite-heavy --policy both --ordering both \
      --seed "$seed" --windows 1 --depth 16 --profile near --heavy-work 256 \
      --ready-pattern bursty --ready-period 100 --jobs 1 --make-jobs 1
  local run_id
  run_id="$(cat "$root/latest.txt")"
  check_manipulation "$root/$run_id/diagnosis_scope.json"
}

run_order_seed 6401
run_order_seed 6402
run_order_seed 6403
run_order_seed 6404
run_order_seed 6405
```

`--smoke` is the existing W256/bounded-run guard, not a confirmation label.
The `r.NAME` override preserves the requested namespace while the runner creates
fresh timestamp/PID output directories. The failed
`20261101T024757Z_2732` directory remains untouched.

## Expected execution and acceptance

Per seed, expect 4 lint configurations, 1 traffic pytest target, 8 cocotb jobs,
and 4 finite-Heavy pairs. Across all five seeds: 20 lint configurations, 5
traffic pytest invocations, 40 cocotb jobs, and 20 pairs. Use
`--jobs 1 --make-jobs 1`; cap each seed at 30 minutes and the campaign at 3
hours.

A complete campaign additionally requires:

- every lint/compile/simulation/pytest step PASS with no skipped required step;
- source hashes unchanged before/after each run;
- each lane generated=fired=256 Heavy requests and fully drained;
- generation-role generated=accepted=fired conservation;
- mixed/isolated scenario configs equal after removing `include_sparse`, with
  the deterministic Heavy+ready prefix hash equal through
  `min(mixed.active_cycles, isolated.active_cycles)`;
- all fixed parameters agree with this plan;
- a pair-input audit, corrected endpoint analysis, and artifact hashes are
  recorded without changing any historical run.

## Artifacts and stop rules

Keep every new run directory

```text
artifacts/implementation/cgof-rtl-ordering-exploration/<new-run-id>/
  config.json
  commands.txt
  versions.txt
  summary.json
  diagnosis_scope.json
  sources.zip
  logs/
  junit/
  results/
```

After all five seeds, create new files in the same namespace:

```text
correction-manifest-<UTC-timestamp>.json
correction-pair-audit-<UTC-timestamp>.json
correction-analysis-<UTC-timestamp>.json
```

The manifest must include the failed-design reference and hashes, requested and
fallback model provenance, backend `UNKNOWN`, Git HEAD/dirty snapshot, tool
versions, exact commands, run IDs, source before/after hashes, and hashes of all
new evidence. The analysis JSON must contain one row per job and one row per
matched contrast, with corrected paths, units, orientation, null/censoring
status, and no confidence interval.

Stop and preserve evidence on any source drift, collision, missing artifact,
failed build/simulation/assertion, pair mismatch, conservation failure, timeout,
or `MANIPULATION_NOT_HELD`. Never repair a failure by deleting a seed, changing
the workload after inspection, overwriting a run, or selecting a favorable
artifact. Infrastructure retries require a new timestamp/PID and a retained
original failure record.

## Scope exclusions

No W5M, extra seeds, extra profiles, role switching, D8/D32, W64, Main/WRR/IWRR
expansion, Buffer feedback, RTL policy change, PPA/STA, formal/CDC, calibrated
CXL/application experiment, or report-main-text integration.
