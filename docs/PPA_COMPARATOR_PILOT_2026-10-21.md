# Shared comparator: functional acceptance and Main N16 pilot

Date:2026-10-21 (Asia/Taipei). **FULL_FUNCTIONAL_REGRESSION_ACCEPTED; MAIN16_SINGLE_PILOT_MET.** Original nine-case measurements remain unchanged. Power, Algorithm-2 and post-layout/multicorner signoff remain unrun.

## Change and source

Native Claude Code2.1.304 / RTL Agent Team0.14.6 `rtl-coder`, requested Opus5.5/medium, session322c1671-e1c8-4f12-a942-50d733089ea1, exit0. All74 inspected assistant response records report `claude-opus-5-5`. Codex independently reviewed and audited results. No fallback.

RTL commit `d82f1b54ca54af2344ad07d914680547003f526f` changes only the shared `cxl_fcfs_sel.ts_older` expression. The lower-bit borrow/MSB-XOR expression and separate equality check preserve unsigned modular ordering, ties and half-range behavior. No pipeline, storage, FIFO, hold, policy, interface or Spec change. FCFS/Main share the edit; RR has no added timestamp storage. [Independent review](../reviews/phase-4-rtl/codex-comparator-review.md).

Actual source for the clean synthesis export: `b257ee8d878b94c14fb7ad78d03ff0ddb2ee7ee6`. Only this selector's RTL hash differs from the old Main16 pilot: `3418505168ca4a0c93422101f1e1a7a042833c935e0f9b021661535b7b6a2c20`. Spec stays frozen at1af80967. Later documentation-only commits do not change tested RTL or exported flow.

## Functional evidence

Both native and independent actual new-vs-old RTL comparisons passed21configurations/81,108,288vectors. The all-width argument is mathematical derivation;32-bit tests are finite, not machine-checked formal equivalence. Codex fixed the test baseline to pre-changeb54aa64 and verified identical-source rejection. [Focused evidence](phase-5-verification/ts-older-comparator-20261021.md).

| Scope | Actual PASS | Run ID |
| --- | ---: | --- |
| M1 | 286 | 20261020T190753Z_4587 |
| M2 | 526 | 20261020T190823Z_5191 |
| M3 | 550 | 20261020T165234Z_2953 |
| M4 | 430 | 20261020T190924Z_6959 |
| M4-q1 | 195 | 20261020T191009Z_7942 |
| M5 units | 805 | 20261020T165357Z_386 |
| FCFS primary | 60 | 20261020T165716Z_534 |
| RR primary | 60 | 20261020T170247Z_5075 |
| Main primary | 60 | 20261020T172737Z_382 |
| Main stress | 30 | 20261020T170825Z_8460 |
| Main production | 3 | 20261020T173518Z_3766 |

Original raw JUnit and strict lint were independently checked: zero failures/errors/skips, no simulation-build relaxations. Expected Algorithm-2 rejections are separate from test counts. Repeated Python collections do not represent unique additional RTL coverage.

Primary180/180 run records match each policy's accepted old baseline and fixed intended traffic hashes. Stress30 covers18million trace cycles with four states/all16 transition-evidence combinations in each run. Production3 covers60million actual non-reset measured cycles,12complete W5,000,000windows; all outstanding drained. New/old stress and production functional metrics match exactly after excluding specifically identified host runtime/speed/RSS fields. No skipped time or state preload.

The first batch received SIGHUP exit129 during Main primary, leaving37/60 partial results. This interrupted run is NOT_ACCEPTED_INCOMPLETE. A full Main primary rerun and all remaining stages completed exit0; original failure/interruption logs remain. Nine completed stages verified76functional source hashes before and after; final sources still match. Details and raw evidence paths: [development record](DEVELOPMENT_REPORT.md).

## Same-profile commercial comparison

Actual DC/PT W-2024.09 on FastX backendFastX-NN. Same SAED32 RVT TT0.78V25°C,25ns, uncertainty0.1/0.05ns, I/O0/2ns, transitions0.1ns, FO4output load2.656828fF, ForQA/top WLM, compile-medium, one DC core, normally timed synchronous reset. No exceptions or changed service timing. Cap075 profile remains **PILOT**, canonical SHA256 `51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f`.

| Main N16 result | Previous cap075 /aa89771 | New comparator /b257ee8 |
| --- | ---: | ---: |
| Total cell area (library units) | 437228.837383 | 437622.506788 |
| FF cells | 35773 | 35773 |
| PT setup slack ns | -0.907946 | +1.158148 |
| PT hold slack ns | +0.085328 | +0.084335 |
| Setup/hold violated checks | 32 | 0 |
| PT cap/slew violations | 0/0 | 0/0 |
| Untested timing checks | 0 | 0 |

Setup slack improves2.066094ns; total area increases393.669405units (+0.09004%). All143344PT checks are tested and met. DC/PT/wrapper exit0 is independently corroborated by raw status markers, reports, result/source hashes, emitted constraints and mapped storage accounting.

The new worst path runs FIFO0 read pointer tosource3 class state. Selector delay along this path is16.676499ns (previous pilot's worst path selector20.314253ns); endpoints and mapping differ, so these are path-specific observations, not a cell-by-cell matched delay proof. FIFO and hold subtree areas also change through mapping/loading, even though their RTL is unchanged. A total-switch delta is not pure selector cost or a claim of Fmax.

390temporary library max-capacitance limits applied/restored;20undefined library outputs skipped. SDC contains no cap overlay; fresh PT uses original library. The additional readonly DC survey checks116993used output driver pins, all with positive original limits and zero ordinary/CCS capacitance violations;20constant pseudo drivers are separately excluded. Source netlist/SDC unchanged by the survey. Library file SHA256 remains `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`; no library/license/executable downloaded.

Machine-readable results: [JSON](ppa/comparator-main16-20261021.json). Ignored raw results: `artifacts/fastx/comparator-cap075-main-n16-20261021a/`; driver survey: `artifacts/fastx/comparator-full-loads-main16-20261021a/`.

## Adoption and next gate

The comparator is accepted functionally; this single pilot establishes measured Main16 setup/hold/electrical closure under the stated pre-layout method. It does not replace or repair the old nine-case dataset. Next, freeze a common revised measurement profile and run/review all nine configurations with identical sources and methodology. Keep original measurements for provenance; do not mix old/default and new/cap075 cases in one primary comparison. Algorithm-2 remains a separate supplementary task after the common baseline review.

No power, physical/multicorner or commercial formal-equivalence result is claimed. This pilot does not establish adaptive fairness benefits or paper cycle-identical reproduction.
