# Main-DAC RTL candidate (DAC2) and 1:1 ablation (DAC1): correctness verification

Status: **correctness matrix PASS** (observed locally, WSL Verilator 5.052 / cocotb, 2026-10-24).
EXPERIMENTAL and opt-in only. Not integrated into `switch_experiment_top`, no production
performance, no PPA, no real four-window W5M production feedback (later work).

## Scope and sources

- Approved base: HEAD `99400de`; DAC files are untracked working-tree drafts of the previous
  native session (ended with service error `reasoning_extraction`), completed here.
- Agent: Claude Code RTL Agent Team native session, Opus 5.5, medium effort. No child agents.
- Oracle: frozen `refc/cxl_model/experimental.py` `ExperimentalSwitchModel` policies `DAC2`/`DAC1`
  (unchanged; sha256 prefix `c190cab351f93497`). MODEL_ONLY gate stays sealed at
  `artifacts/implementation/insight-screen/production-sealed-20261023T101008Z/evaluation/summary.json`;
  nothing was retuned.
- RTL: `rtl/experimental/cxl_dac_sched.sv` (policy), `dac_unit_top.sv` (standalone top reusing the
  unchanged `cxl_desc_fifo`, `cxl_out_hold`, `cxl_fcfs_sel`), `filelist_dac_unit.f`.
- Mechanism (as in the model): per-source credits; eligible = active head with credit; when no
  active source has credit the same selection is a refill (`High ? HIGH_WEIGHT : 1` for every
  source, overwriting unused credit, no bubble); oldest eligible head by the FCFS selector; only a
  fire commits `snapshot - onehot(grant)`. The held grant context `{class snapshot, refill}`
  (DAC1: `{refill}`) makes a held offer commit exactly the model's `Choice.credits`. Main four-state
  B/S classification, closing fire included, 32-bit threshold intermediates.

## Repair made in this session

| Finding | Repair |
|---|---|
| Simulation build (`--vpi`, warnings fatal) failed with `UNOPTFLAT` on `i_fire/i_grant_source/i_grant_ctx`: shared `always_comb` blocks computed candidate terms (`has_credit`, `class_high`) together with grant terms, a false loop through `cxl_out_hold`. `--lint-only` did not report it. | Split those blocks into candidate-side and grant-side `always_comb`. No logic change. |
| Frozen model tests use unittest `subTest`; pytest 9 JUnit totals (31) != testcase elements (13), so the strict pytest step rejects them. | The runner runs that file with `python -m unittest -v` instead: exit 0, `Ran 13 tests`, final line exactly `OK` (no skips). |
| DAC1 never hit the re-entry counter in the directed test (src1 spends its only credit on the refill). | Added step (c): src N-1, idle at the last refill, arrives and fires on its round credit without a refill (both weights). |
| Tautological reset `idx` check, and the reset-coverage assertion was already satisfied by the startup resets. | `idx == 0` asserted; random test now requires >= 1 random reset. |

## Runner

`scripts/run_revision_dac.py` (pattern of `run_revision_baselines.py`) registers milestone
`revision-dac` in the strict `run_verify` engine (`-j 2 --make-jobs 2 --keep-going`; build cache
`$HOME/.cache/cxl-scheduler/build`, no spaces):

- lint: 54 strict configurations, N4/8/16 x DEPTH 8/16/32 x W64/256/5,000,000 x HIGH_WEIGHT 2/1;
- elab_reject: N_SRC 2/32, DEPTH 4, FAI_W 128, HIGH_WEIGHT 0/3, each exactly its own `$fatal`;
- pytest: `scripts/test_revision_dac.py` (4 tests); unittest: frozen model tests (13);
- cocotb `sim/experimental/test_dac_sched.py`, seed 509, 18 configurations (DAC2 and DAC1 each:
  N4/8/16 at D16 W64 and W5M, N4 D16 W256, N4 D8 W64, N8 D32 W256), 11 tests at W64/256 and
  10 at W5M, exact test filter and count, `dac_checks.json` required per run;
- all transitive sources hashed before/after and archived in `sources.zip`.

## Result

Command (WSL):

```
cd scripts && source wsl_env.sh && python run_revision_dac.py --jobs 2
```

Evidence: `artifacts/implementation/revision-dac/20261023T174033Z_1699/` (`summary.json`,
`dac_scope.json`, `junit/`, `logs/`, `results/`, `sources.zip` sha256 `d2707bc5fc31e6ef…`).
Exit 0; overall PASS; 54 lint PASS; 6 XREJECT; 18/18 cocotb PASS; 196 tests (192 cocotb + 4
pytest), 0 failures, 0 errors, 0 skipped; every verilate/make/simulation exit 0; seed 509
recorded; sources stable; frozen model unittest 13 OK. Session log:
`.setup-logs/implementation/revision-20261024/dac-verification/session/full-run1.log`.

Earlier diagnostic runs (failures above): `20261023T173727Z_976` and `20261023T173901Z_1312`.

## Mutation sanity check (not acceptance evidence)

`.setup-logs/.../dac-verification/session/mutation_check.sh` builds mutated copies under
`$HOME/.cache` (N4 D16 W64 DAC2, 5,000 random cycles). Unmutated control 11/11 PASS. Each mutant
was detected: no refill overwrite (2 tests fail), live refill instead of held snapshot (2),
closing fire excluded from B (1, model comparison), closing fire excluded from S (2, thresholds
and long stall).

## Remaining

- Integration into `switch_experiment_top`, DAC PPA, and real four-window W5M production
  feedback are not done.
- Single seed per configuration (unit scope); W5M thresholds checked by state injection, not by
  simulating complete production windows.
