# Revision RTL performance harness

Python-only implementation for the approved revision. The matrix emitted by
`scripts/revision_matrix.py` remains a plan. This runner executes an explicitly
selected subset and never claims completion of all 498 rows.
The core plan is468 unconditional rows (459 RTL and9 power), plus30 conditional
rows. The30 heavy-ID row identities require the parent's corrected fresh matrix
snapshot; this harness does not rewrite that snapshot.

## Scope and ownership

New implementation files are `scripts/run_revision_experiments.py`,
`scripts/test_revision_experiments.py`, `sim/experimental/revision_traffic.py`,
`sim/experimental/test_revision_performance.py`, and
`sim/experimental/test_revision_traffic.py`. Native Claude owns the experimental
RTL, `revision_baselines.py`, baseline units and experimental correctness TB.
Parent owns the experimental Makefile and correctness runner. Accepted RTL,
accepted models, Main-SQ, manuscript and parent ledgers
are not modified by this task.

Parameters are `N_SRC`, `POLICY`, `DEPTH`, `RR_QUANTUM`, `FAI_W`, `HIGH_QUOTA`,
and `MAIN_1W`. POLICY 0/1/2/3/4 selects FCFS/RR/Main/Algorithm-2/BLISS.
RR1/RR10 differ through quantum; Main-1W uses POLICY2 and MAIN_1W=1.
N4/8/16, D8/16/32, RR quantum1/4/8/10/16, High quota5/10/20
(Low10) and Main-1W are supported without changing accepted FAI defaults.
Conditional insight and VCS/SAIF power rows are explicitly refused.

Main-1W/Q10 has the same effective pin behavior as Algorithm-2 under the native
models; only internal state encoding differs. Native's explicit reduction test
records this. Their approved matrix rows remain separate but do not provide
independent causal evidence for two different scheduling behaviors.

## Traffic and measurement

Default N4 uses the existing HOG `Traffic` directly, including generator config,
per-source RNG streams, descriptor order, tags and trace SHA256. Confirmation
seeds529..548 remain separate from exploration509..513. W256 pilots refuse seeds
outside509..513. N expansion preserves the per-source sparse probability1/128.

Production training is exactly two actual W5M windows. A generates independent
sparse arrivals for100,000 cycles. B generates100 blocks of8 arrivals per sparse
source at seeded offsets in1024-cycle blocks (102,400 cycles). Default A/B guards
are1024 cycles. Measurement and guards end before the third production close.
W256 runs retain these measured durations and cross additional short windows:
they are sensitivity/resource evidence, never W5M training evidence.

Rate, readiness and burst robustness changes only measured/guard traffic:
Bernoulli-ready0.75, periodic-ready48/64, heavy0.5/0.9, or burst32 every4096 (25 blocks).
Training arrivals, descriptors and readiness match the default exactly. Ready
and heavy draws have separate seeded streams.

Heavy-ID3 instead permutes the canonical heavy0 trace from reset, including
training, A/B and guards: source0 and source3 exchange complete exogenous
streams. Descriptor payloads, serial tags, canonical event order and readiness
remain identical under relabeling; descriptor RNG streams follow their mapped
sources. Config records `source_permutation=[3,1,2,0]` and
`perturbation_after_training=false` for this arm. Both guards remain1024 cycles.
This corrects the earlier heavy0-training/heavy3-measurement implementation,
which confounded source-ID robustness with adaptation and old-heavy backlog and
required an extended guard. No production used that implementation. The separate
adaptation arm retains its roles and queue history. Parent owns the matrix-row
flag amendment and preserves the original matrix-initial archive.
Guard failures fail the run.

Adaptation is six actual windows with heavy0.8, roles0->3->0 every2W. It preserves
all queues through role changes, records each two-window phase, then drains every
generated descriptor. It has no artificial reset or backlog removal at a role
boundary.

`--cold A` and `--cold B` are independent reset-start lanes. The generator alone
advances through the corresponding trained prefix, preserving the exact measured
arrivals, tags, descriptor RNG, heavy RNG and ready RNG. No prefix requests,
backlog, scheduler state or time skips enter the RTL. Cold A runs A and its guard;
cold B runs B and its guard. They never run a sequential A-then-B replay labeled
as independent cold B.
These are optional explicit lanes and required where the separate screening
protocol requests them. The core matrix does not require cold A/B copies of all
498 rows; its default confirmation subset is120 trained runs.

The reused `StreamProducers` exposes only its oldest pending full descriptor per
source. Valid/data remain held until actual acceptance. The scheduler and oracle
receive only current offers and sink readiness. Producer backlog, future
arrivals, generation timestamps and cohort labels remain private to accounting.

Every real edge compares readiness, valid, selected source and all105 descriptor
bits with an independent oracle. FCFS/RR/Main/Algorithm-2 defaults use their
accepted models. BLISS, High quota variants and Main-1W use native's new models.
A separate pin FIFO enforces beginning-of-cycle full readiness, no full-plus-pop
acceptance, no bypass, order/integrity, stable output hold and conservation.
Only actual fires charge the oracle. Two synchronous reset edges precede cycle0.
No model-only result can carry the RTL evidence label.

Per-phase raw outputs include generated, offered-valid cycles, accepted, fired,
producer backlog, FIFO occupancy and wall/ready-opportunity source gaps. The
per-phase eligible-ready opportunities count the joint condition of sink ready
and any beginning-of-cycle FIFO occupancy. Eligible-ready utilization is total
phase fires divided by this count, or null for an empty denominator. Idle-ready
cycles and nonempty stalled cycles are excluded. Avoidable bubbles count joint
eligible-ready cycles without a fire and assert zero; this denominator is
observed directly each cycle rather than reconstructed from marginal counts.
Exact generation cohorts include per-source and pooled-sparse direct histograms for
G2A, A2F and G2F, sample counts, mean, P50/P90/P99/P99.9/max. Heavy samples are
retained per source and excluded from the sparse pool by the generation-time
role. Phase-boundary gaps use the existing explicit censoring convention.

Sparse cohorts must complete in their background-on guards. At training end
the cold generation cohort must be complete, but newer sparse work is retained:
sparse arrivals continue throughout training and may occur on its final edge.
At A/B guard ends both the measured sparse cohorts and all sparse queues must
be complete, because those guards generate no new sparse work.
Heavy generation stops only at the declared fixed active end. Final drain keeps
ready1 and drains all generated producer work plus accepted work, with a bound
derived from actual pending requests. No truncation of overload work is allowed.
The harness records actual closing-window fire counts and effective model classes.

## Runner and freeze

Run in WSL after sourcing the existing project environment. Wait for native's
explicit source-freeze handoff before using `--source-ready`. A stable hash alone
does not establish that an active native writer has finished.

```bash
source scripts/wsl_env.sh
python -m pytest sim/experimental/test_revision_traffic.py scripts/test_revision_experiments.py -q -p no:cacheprovider
python scripts/run_revision_experiments.py --pilot --seed 509 --source-ready \
  --output artifacts/implementation/revision-performance/pilot-n4-seed509 -j 3 --make-jobs 2
python scripts/run_revision_experiments.py --pilot --seed 509 --n-src 16 \
  --policy FCFS,MAIN,BLISS --source-ready \
  --output artifacts/implementation/revision-performance/pilot-n16-seed509 -j 3 --make-jobs 2
```

The N16 resource pilot records peak RSS and actual producer backlog growth.
The sum of the largest concurrent process peak RSS values must remain within70%
of starting available memory. The runner also samples system MemAvailable every
0.25 seconds during execution and replay, records its minimum and peak memory
growth, and rejects growth exceeding70% of starting available memory. Concurrent
work contributes to this system measurement. These are conservative observed
resource gates, not a physical-memory proof or a projection of W5M backlog size.
Production N16 requires a reviewed pilot at least as large as the requested N.
No production is launched by this implementation task.

After parent review, a selected production example (not executed here) is:

```bash
python scripts/run_revision_experiments.py --group n4-confirmation --seed 529 \
  --source-ready --production-reviewed \
  --reviewed-pilot artifacts/implementation/revision-performance/pilot-n4-seed509 \
  --output artifacts/implementation/revision-performance/n4-confirmation-seed529 -j 3 --make-jobs 2
```

`--n-src` and `--policy` restrict the declared subset before execution. Example:
`--group n-expansion --seed 509 --n-src 16 --policy FCFS,MAIN,BLISS`.
No arguments launch the entire plan. Seeds must exist in the selected group.
Output must be a fresh child under `artifacts/implementation/revision-performance`;
existing output is never reused.

The runner reuses `run_verify.Run` lint, pytest, compile, make, simulation,
timeouts, tool exits, diagnostic checks, JUnit parsing and required-artifact
checks. It freezes selected job JSON once, archives exact transitive RTL/Python/
TB/config bytes in `sources.zip`, and hashes those bytes before and after.
Mutable `EXECUTION.md` is archived as context but excluded from runtime integrity
hashes. Other workers' unrelated `experimental.py` is excluded.
The final dependency list explicitly names the imported policy-model modules
and common helpers (`traffic_trace.py` and the archived native TB's
`hier_util.py`). It does not glob arbitrary future helper/model/RTL additions.
An isolation test verifies that new DAC-only files do not enter this freeze.
Source changes invalidate the run. Production also requires a passed reviewed
pilot with identical executable source hashes.

The freeze dependencies are the experimental filelist and all listed RTL,
accepted/native policy models, common simulation helpers, legacy traffic
helpers, performance traffic/TB/units, native baseline units/correctness TB,
experimental Makefile, strict runner, revision runner/matrix/statistics,
environment script and frozen specification/approval files. The current native
repair to `test_experiment_top.py` therefore blocks freeze even though the
performance TB is independent. Wait for parent acceptance of the repaired
baseline correctness suite and explicit source release before either pilot.
Run N4 six-policy and N16 FCFS/Main/BLISS pilots sequentially, each with at most
three simulations and two make jobs, leaving the other three worker slots for
the active model queue. Do not overlap these pilots with the parent's RTL
correctness workload unless parent releases the RTL slots.

`frozen-spec.json`, `config.json`, `commands.txt`, `versions.txt`, before/after
hashes, raw logs/JUnit, metrics, trace pairings, failures, summary and the scope
gate are preserved. `evidence.zip` bundles them with `sources.zip`, excluding
build intermediates. Successful metrics are independently checked against a
fresh intended-trace replay. Trace-equivalent policies must use the same digest;
default FCFS/Main training-pin digests must also agree.

Missing jobs/artifacts, NOT_RUN, failed/skipped/empty tests, nonzero or missing
tool exits, changed sources, failed guards, unfinished cohorts, incorrect direct
histograms or unavailable resource measurement cannot pass. Cocotb failure
context is copied as `revision_failure.json` even when no metrics file is written.
Pre-simulation failures remain in strict step logs and numeric exits.

## Evidence so far

Initial Windows checks:9 traffic tests and6 runner tests passed, exits0.
After independent cold-lane and source-freeze fixes:11 traffic tests and7 runner
tests passed, exits0. Expanded hold/conservation tests brought traffic to13.
The latest WSL eligible-ready pure check passed25 tests, exit0 (16 traffic and9
runner), recorded in
`.setup-logs/implementation/revision-20261023/performance/wsl-units-eligible-ready.log`.
The added tests distinguish idle-ready and nonempty-stalled cycles from joint
eligible-ready opportunities, check null utilization for an empty denominator,
and deliberately inject a bubble to verify both counting and failure.
The preceding static-permutation check passed23 tests, exit0; its raw log is
`.setup-logs/implementation/revision-20261023/performance/wsl-units-static-permutation.log`.
It compares the complete canonical/permuted W256 trace at N4 and N16 across
training, A/B and both guards, checks independent cold replays, and checks that
source0 remains in the sparse cold-cohort pool when source3 is heavy.
The primary W256 trace hashes captured before this change remain:

```text
seed509 cfffb58a5233aaa4b018d95e6a2a7606edc92d0daae784189c1b214e7219b984
seed529 bc01f0a168c8519ba35260335160ddf73ee1ade904915368e9a596069d969620
```

These fixed hashes are unit assertions in addition to legacy-generator equality.
The prior22-test checkpoint log remains available as `wsl-units-checkpoint.log`.
The model adapter reset/API self-check covers all459 unconditional RTL rows:
FCFS75, RR160, Main83, Algorithm-2 63, BLISS60, quota/Main-1W variants18;
exit0, recorded in `model-adapter-api.log` in the same directory. This check
constructs independent models only and is not RTL evidence.
Earlier raw command logs are in the assigned ignored
`.setup-logs/implementation/revision-20261023/performance/` directory.

Replacement-writer handoff: full36 artifact
`revision-baseline/20261023T171119Z_303` is PASS, outer exit0, stable source
hashes,36 lint/15 model/226 applicable cocotb tests, no skips. Parent explicitly
released performance sources after this correctness pass. Parent then repaired
the baseline runner's omission of newly imported `sim/common/hier_util.py` from
its own archive and started a source-complete full36 rerun4109. No RTL/TB edit
was made for that archive repair. The performance archive already includes all
common Python helpers and now explicitly requires `hier_util.py`; a regression
test checks the archived bytes. The expected baseline-runner-only change
explains the first current-source prerequisite audit mismatch; the original
baseline archive and its correctness result are retained.

The replacement writer's initial pure suite passes28 tests, exit0 (18 traffic,
10 runner), in `wsl-units-handoff-final.log` under the ignored performance
evidence directory. It adds complete cold A/B permutation traces through their
guards, blocked-producer offered/accepted/backlog accounting, archive inclusion,
and result-gate corruption tests for utilization and per-source conservation.
The final result gate checks the joint denominator, zero bubbles, null empty
utilization, offered/accepted bounds, per-source drain, and one backlog/occupancy
sample per real phase cycle. Executable sources are frozen by the runner before
each pilot and rechecked afterward.

While parent rerun4109 is active, pilots use one simulation worker/buildjobs2.
Parent subsequently confirmed the source-complete
`revision-baseline/20261023T171608Z_276` PASS:36 lint,15 model and226 cocotb tests,
zero skips, exit0/stable; this writer independently verified its archived
source bytes including `hier_util.py`. Parent released three performance
workers/buildjobs2, with native DAC capped at two and the global cap at six.
N4 six-policy W256 precedes N16 W256 resource evidence. Parent then authorized
one real-W5M resource pilot after W256 passes: N16 FCFS seed509, one worker.
It uses the existing reviewed-pilot/source-match gates and the exploration
`n-expansion` row; it is not confirmation or a production-batch launch.
Confirmation and production batches remain NOT_RUN. Final actual pilot paths and
results are appended after execution. Pure units are not RTL performance evidence.

First N4 attempt `pilot-n4-seed509-handoff` failed before simulation: the partial
runner used an output-local build path containing `Coding Space`, rejected by
GNU Make. All6 lint and43 unit tests passed; all6 make exits were2, with no RTL
results accepted. Exact failed sources, commands, logs and scope remain archived.
The runner now follows `run_verify.Run`'s existing `CXL_BUILD_ROOT` or default
`~/.cache/cxl-scheduler/build` convention, with a regression test for both paths.
The repaired pure suite passes29 tests, exit0 (18 traffic/11 runner), recorded
in `wsl-units-build-cache-fix.log`.

That fresh cache-fix pilot completed PASS6/6, six lint and44 unit tests, no
failures/skips, stable source hashes; wall223.9s, one simulation worker/build2.
Only after it ended, the writer narrowed the dependency list to the explicit
import closure, dropping nine unrelated common helpers. This is an archive
scope fix; traffic and performance TB bytes are unchanged. Final pure checks
pass30 tests (18 traffic/12 runner), exit0, in `wsl-units-final-freeze.log`.
Final executable freeze contains39 files, including the complete native TB and
`hier_util.py`. Its receipt is `final-freeze-handoff.json` in the ignored
performance evidence directory. Runner SHA256:
`cfdfe2c67cd272048e6a802a54a5e1215c546860986c8a662ab8dfc25e17d8a3`.
Fresh N4 `pilot-n4-seed509-finalfreeze` binds all six policies to these final
bytes; subsequent N16 and W5M resource pilots must match those bytes.

Final-freeze N4 PASS6/6: six lint,45 unit tests (18 traffic/12 runner/15 native),
six RTL tests, zero failures/skips,1,258,194 actual nonreset cycles total.
All six traces equal the fixed seed509 hash above; producer peak backlog4724,
maximum process RSS46,728KiB, starting available memory15,273,156KiB,
peak observed system growth1,455,644KiB (below70%). Wall104.318s at three
workers/build2. All before/after hashes and archived source bytes independently
verified. `n4-independent-audit.json` records this and the prior cache-fix pass.
N16 W256 `pilot-n16-seed509-finalfreeze` runs FCFS/Main/BLISS at three
workers/build2 under the same39-file source freeze.

This N16 pilot failed at cycle511 for all three policies: the training-boundary
check incorrectly required all sparse queues empty even though arrivals
continue through the final training edge. This was a harness boundary assertion,
with no policy pin/oracle mismatch; failure JSON/logs remain in that artifact.
The correction retains all pending work and checks completion of the earlier
cold cohort at training end. Full sparse-queue emptiness remains mandatory at
A/B guard ends. A new regression covers both W256 and W5M and confirms that
unfinished cold cohorts still fail. This changes traffic-helper bytes and
supersedes the preceding final-freeze receipt; fresh source-matched N4/N16
pilots are required before the W5M resource run or parent core launch.

The repaired pure suite passes31 tests (19 traffic/12 runner), exit0, recorded
in `wsl-units-training-boundary-fix.log`. Additional direct checks in
`boundary-output-checks.json` reject pending work at both A/B guard ends and
reject output root/outside-root/existing-directory targets. No generator
quiet period or guard extension was introduced. The repaired traffic-helper
SHA256 is `750b01dd50494b53f76c13b7dd601d4d2f8301ac3779b63ccdbfc2dc3f37ffbb`.
`trainingfix-freeze-handoff.json` supersedes the earlier freeze receipt and
explicitly marks older matched-power preparation source bindings invalidated.
Runner and performance TB hashes remain unchanged.

Fresh repaired N4 `pilot-n4-seed509-trainingfix` passes all6 lint and6 RTL jobs
plus46 unit tests (52 tests total), zero failures/skips, stable39-file freeze.
Fresh repaired N16 `pilot-n16-seed509-trainingfix` runs three policies under
these same source bytes. The runtime projection uses459 unconditional RTL
rows and4,862,001,600 active cycles before drains, including nine30M-cycle
adaptation rows. Any estimate from the resource pilot is a scheduling forecast,
not completed matrix evidence.

Repaired N16 W256 PASS3/3 (FCFS/Main/BLISS): three lint,46 unit and three
RTL tests (49 total), zero failures/skips,686,040 actual nonreset cycles total.
All three traces match
`122711673113e5378a22bc7cf1f9e4a2e97baaedd470bc66538f232d29dc07fe`.
Maximum process RSS60,760KiB, peak producer backlog23,705; starting available
memory15,286,128KiB and peak observed system growth1,470,580KiB, both memory
gates PASS. Wall90.358s, three workers/build2. Archive bytes and source stability
were independently checked; N4/N16/current39-source maps match exactly.
`trainingfix-pilots-independent-audit.json` records both repaired pilots.

The explicitly authorized one-row resource run started UTC2026-10-23 17:32:17:
`resource-n16-fcfs-seed509-w5m-trainingfix`, launcher PID288, tool session22224,
one simulation worker/build2. It selects `--group n-expansion --seed 509
--n-src 16 --policy FCFS --source-ready --production-reviewed --reviewed-pilot
artifacts/implementation/revision-performance/pilot-n16-seed509-trainingfix`.
The full output is under `artifacts/implementation/revision-performance/`;
the matching outer log is under the ignored performance evidence directory.
`resource-launch-handoff.json` preserves the source-bound launch receipt.
The real simulator PID is709. All lint/46 unit checks passed before actual
simulation began. Two actual5M training windows, measured A/B, guards and full
drain are required; no confirmation seed is used. Core queue remains NOT_RUN
until resource PASS and parent review of the final result/memory.

`owned-scope-audit.json` compares this source freeze with the first retained
attempt: only the owned runner/runner tests/traffic helper/traffic tests changed;
RTL, models, matrix and native TB are unchanged. The performance TB is unchanged.
All39 current source hashes match. No manuscript file was written by this task.
