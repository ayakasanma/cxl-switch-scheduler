# Experimental baseline verification

## Material Passport

- Origin: owner-approved revision execution, 2026-10-23.
- Scope: opt-in single-output experimental top; accepted policies/interfaces unchanged.
- Verification: diagnostic subset passed; first complete run failed RR structure checks.
- Performance, source bridges and RTL-to-netlist equivalence are separate evidence.

## Sources and responsibility

Native Claude Code / RTL Agent Team authored the experimental RTL, independent
BLISS/Main-variant models, and correctness testbench. Actual model was
`claude-opus-5-5`, medium effort. Codex independently reviewed the sources and
added strict execution orchestration, configuration tests and the Makefile.

The top selects FCFS, RR, Main, Algorithm-2 or BLISS. Nondefault quotas and
Main-1W use a separate experimental scheduler. RR retains no unused timestamps.
The accepted top and policy implementations are not edited by this extension.

`scripts/run_revision_baselines.py` reuses the accepted strict runner, requires
zero skipped applicable tests, and archives exact source bytes, hashes, numeric
tool exits and the complete/subset distinction. Its 36 cases cover N4/8/16,
depth8/16/32, RR quantum1/4/8/10/16, High quota5/10/20, Main-1W and production
window parameters. W256 directed classification checks are sensitivity tests;
selecting W5M does not alone establish two-window performance training.

## Retained failures and native repairs

Initial diagnostic `20261023T100620Z_647` failed BLISS and Main-variant tests.
The testbench read registers before closing-edge assignments settled; its
variant coverage counter omitted class changes; random reset timing prevented
the required uninterrupted BLISS clearing interval; some directed edge
expectations were incomplete.

The native repair invocation is retained under
`.setup-logs/implementation/revision-20261023/baseline-test-repair/`.
Only `sim/experimental/test_experiment_top.py` was assigned for source edits.
It now compares pre-edge pins and settled post-edge policy state, checks exact
BLISS edges9999/10000/20000 including held grants, counts variant window events,
and reserves an uninterrupted BLISS clearing interval while retaining random
reset checks. No RTL or oracle change was needed.

First repaired subset `20261023T101320Z_1077` retained one failed BLISS test.
Final repaired subset `20261023T101410Z_1489` passed three lint cases, all15
native model unit tests, and21 cocotb tests (5 FCFS,8 BLISS,8 Main-variant),
with no skips and stable source hashes. It is explicitly a three-case subset.
Native process exit0 is recorded; its terminal record also reports a stop-hook
error, so functional acceptance uses actual strict-runner/JUnit evidence.

The parent executed the complete36 cases as
`artifacts/implementation/revision-baseline/20261023T101627Z_2445`.
All36 strict lint cases and15 native model tests passed. Of36 dynamic
configurations,27 passed and nine RR cases failed the same structure assertion:
the constant-only `gen_no_arrival_ts` scope is optimized away by Verilator.
Those cases' remaining pin/model/reset/hold/random tests passed. This is still
a failed complete run, with exit1 and stable source hashes; consult
`summary.json` and `baseline_scope.json` together.

A separate native repair invocation under `baseline-rr-structure-repair/` owns
only the testbench. Its required correction checks the absence of real
timestamp counter/storage and zero timestamp outputs instead of requiring a
visible empty generate scope. Strong checks are retained; dynamic acceptance
and performance launch remain pending a successful full rerun.

## Separate checks and limits

An independent read-only audit retained96 legal strict-lint checks and18
invalid-configuration rejections, with stable hashes. DEPTH0 is rejected by
the inherited zero-size FIFO cast before the explicit guard; that distinction
is preserved. Lint does not establish dynamic correctness or equivalence.

Main-1W at quota10/10 has the same effective transition rule and external
behavior as Algorithm-2, despite different internal encoding. Unit lockstep
checks cover this overlap; it is not a second independent causal mechanism.

Performance production must wait for complete correctness acceptance and
source-matched six-policy/N16 resource pilots. The six missing historical
FCFS/RR source bridges remain blocked by remote authentication. No new
experimental mapped netlist, DC/PT result or equivalence proof is implied.

## Full dynamic acceptance at approved99400de, 2026-10-24

The next native structure-repair invocation ended with explicit429/session
quota exhaustion. The owner-authorized Sol/high fallback completed only the
testbench repair; recorded actual model is codex/gpt-6.1-sol, high effort.
Its checks traverse actual hierarchy, require real descriptor/timestamp
storage where applicable, and require RR timestamp/counter absence plus zero
head timestamps. The constant-only empty generate scope is not required.
No RTL or reference-model change accommodated the tests.

Its two-RR diagnostic20261023T102832Z_9245 passed2 lint,15 model tests and
10 cocotb tests. Full run20261023T171119Z_303 then passed all36 lint cases,
15 model tests and226 cocotb tests with zero failures/errors/skips.
Parent archive audit found that run's ZIP omitted the newly imported
sim/common/hier_util.py, although the runtime tests passed.

The runner source list now explicitly includes that helper and a focused
regression protects the dependency (two runner configuration testsPASS).
Fresh full run20261023T171608Z_276 passes the same36 lint,15 model and
226 cocotb tests, exit0, stable sources, complete_matrix=true. Its sources.zip
includes the helper. This is the source-complete baseline correctness
acceptance used before performance pilots. Earlier failures and the prior
passing-but-incomplete archive remain intact.

Runtime187.7s for the first passing full run and149.3s for the source-complete
repeat is host execution time, not scheduler latency or a comparative metric.
These directed/random correctness results do not constitute the planned
production performance matrix, source bridges or candidate equivalence.
