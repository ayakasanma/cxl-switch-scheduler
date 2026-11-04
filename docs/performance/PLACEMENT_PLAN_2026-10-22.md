# Owner-approved source-placement and class-cardinality sensitivity

Status: ACCEPTED42/42 actual RTL runs; [results and limitations](PLACEMENT_RESULTS_2026-10-22.md).
This extends the accepted [controlled follow-up](FOLLOWUP_RESULTS_2026-10-22.md).
The owner authorized tests1/2: vary source position and number of Low sources.
Final report remains on hold: no manuscript edits, compilation or rendering.

## Question and controlled matrix

Does Main's observed half-output allocation follow class membership rather than source0,
and how does equal per-class quota translate into per-source service as class sizes change?
N4, D16, M1, descriptor105, FCFS/RR10/Main; all fourteen nonempty proper Low-source subsets
(four singleton, six pairs, four triples), each with all three policies:42 simulations.
Seed509 is a descriptor-data choice, not independent arrival-schedule randomization.
Use the same external generated trace and ready stimulus per subset across policies;
record actual acceptance/completion separately. These are mechanistic placements, not42
independent random samples or an extension of the primary180 matrix.

## Naturally trained, explicitly shortened windows

Use supported stress W256 and two real windows (512 cycles), then240 measurement cycles,
entirely before the next closing at767. No state deposit, time skip, classifier freeze or RTL/model change.
Each target Low source generates floor(floor(2W/5)/k) requests per training window;
each remaining source generates floor(W/20). Spread these over W-4 slots, with four quiet
closing slots. Verify actual fire counters and exact integer thresholds: target sources
DOWN, others KEEP, Main B_H then L. All other sources stay H. Measurement generates one
descriptor/source/cycle, sink ready1. After128 fill cycles both classes and every source
must remain eligible. Verify fixed classes and full10-fire visits during measurement.

This is **short-window sensitivity**, not W5M production evidence, infrastructure-only
smoke, steady-state adaptation or a proof of all source/workload invariance. Production
W5M/two-window evidence is reused from the previous accepted experiment, not relabelled.
Stop generation and complete all pending producer/FIFO/response work with a checked timeout.
Drain may cross later classification boundaries; do not pool its evolving classes with
the fixed-class measurement. Latency cohorts include later completions and retain boundary
censor snapshots, as in the existing follow-up contract.

## Expected mechanism and acceptance

For simultaneously backlogged classes,10/10 visits predict approximately half the output
per class. With k Low sources, per-source targets are1/(2k) Low and1/[2(4-k)] High:
1L/3H predicts50%/16.67%,2L/2H25%/25%,3L/1H16.67%/50%. Finite visits, same-cycle ties and
window/measurement boundaries may produce small count offsets; derive count bounds from
incomplete visits and oldest-first order, never assume cycle-identical permutations.
For equal persistent demand, ideal limiting source-service Jain is0.75/1/0.75 respectively.
These are predictions to check, not measured results or a universal fairness objective.

The first pilot attempted W4096 and failed strict lint before any simulation because the
existing top-level parameter guard only supports production W5M or stress W64/256.
The failed run/exit is retained. The corrected plan uses W256,512 training+240 measurement,
with112 post-fill slots. This avoids RTL changes or waived diagnostics; the short observation
requires explicit finite-count/boundary interpretation rather than precise limiting shares.

Use existing strict Verilator/cocotb/oracle and model-free pin-history checks every cycle.
First pilot one subset per cardinality across three policies; then freeze implementation,
review and execute the full42. Preserve numeric outer exits, raw JUnit, source/trace hashes,
failed/incomplete attempts, exact matrix, generated/accepted/fired populations, classes,
per-source shares/latencies/gaps, partial/full visits and phase-labelled metrics. Independently
audit actual reports and reject wrong subset/labels/missing matrix/corrupt statistics.
Old scopes and hashes must remain compatible; no change to accepted RTL/refc/Spec/PPA.

Native Claude Code RTL Agent Team Opus5.5/medium is invoked first. Actual quota exhaustion
allows the owner's GPT6.1Sol/high fallback; preserve provenance and single-writer ownership.
Codex independently reviews and owns records. No SSH, PPA rerun, gem5, external workload,
Algorithm-2 expansion or new dependency is needed.
