# Owner-approved performance follow-up —2026-10-22

Status: implemented and accepted;42/42 formal RTL runs PASS with independent raw-evidence audit.
This document retains the design/measurement plan; [actual results](FOLLOWUP_RESULTS_2026-10-22.md)
record run IDs, hashes, limitations and observed service redistribution.
Owner accepted the independent review recommendations. Final report remains on hold: no edits,
builds or renders, including the separately identified policy-subtree transcription error.
Use only existing project RTL, models, WSL tools and self-authored descriptor traffic. No SSH,
PPA rerun, application/gem5 integration, external workload or Algorithm-2 matrix expansion.

## Frozen implementation boundary

N4, D16, M1, descriptor105, FCFS/RR10/Main and the shared switch_top. No RTL/model/Spec changes.
Use existing strict Verilator runner, independent policy TB/oracle, pin-history checks and tagged
responses. Do not replace real simulation with model exports. Keep old primary180 evidence intact.

## Small, complementary matrix

| Scope | Configurations | Purpose |
| --- | --- | --- |
| Trained competition | N4 seed509, three policies; W5M,10M real warmup+100k measurement | Naturally form Main classes, then compare simultaneously eligible classes under contention |
| Fixed loads | Four cases×seeds509..511×three policies=36 | Separate offered load, sink capacity and policy ordering |
| Finite batch | Seed509, three policies,4096 requests total/1024 per source | Complete the same generated work and measure direct generation-to-fire latency |

Trained warmup: total intended0.55/cycle, source0 approximately0.40 and each other source0.05,
ready1, starting allH. Expected independent evidence: source0 DOWN in both windows; others KEEP
(0.05/0.55 is above the0.3/N UP threshold). Expected closing classes: B_H/H/H/H, then L/H/H/H.
Measurement switches to persistent offered demand on all sources. This deliberate load change is
a finite trained-state transient, not stationary fairness or recovery after another full window.
No state deposit, time skip or shortened production W. Both classes must actually remain eligible
after filling; complete10/10 visits, partial boundary visits and per-source redistribution labelled.

Controls: separate reset/run,10k warmup+100k measurement, total offered0.30/0.90/1.20 with ready1;
fourth case offered0.60 with deterministic periodic ready duty0.75. Identical exogenous traffic
and ready per case/seed across policies; actual acceptance may differ. These short Main cases
remain allH. Overload and changing-phase means are finite-window statistics, not stationary delay.

Finite batch: same4096 uniquely tagged descriptors, fixed per-source burst release pattern and
explicit ready trace. Stop generation, keep all pending producers running, complete every request
and response. Record generation interval versus completion/drain separately; bound drain and fail
on missing completion. This differs from the existing primary boundary-only drain and must not
silently redefine that old measurement. Direct per-request generation-to-fire P99; never add
two stage P99s. Observed max is not WCET or a general starvation guarantee.

## Measurement and acceptance

- Record per-source generated/accepted/fired, latency histograms/count/mean/P99/max for each
  stage and direct generation-to-fire, phase/cohort identities and censored age snapshots.
- Separate warmup, measured accepts/generations, carryover, drain and open/censored samples.
  Preserve input hold and no-bypass rules at every boundary. Use one trace-relative time base.
- Service gaps apply while FIFO is continuously nonempty; distinguish initial wait, inter-service
  gap, termination by emptying and still-open right-censored gaps. Count clock cycles and eligible
  ready opportunities separately, so downstream stalls are not mistaken for scheduler starvation.
- Record output ready/fire/idle-ready, FIFO-nonempty ready opportunities and avoidable bubbles.
  Successful-slot utilization equals fires/cycle for M1; ready-opportunity utilization has a
  different denominator. Per-source service share requires demand/eligible-backlog context.
- Keep warmup memory bounded: pending queues, histograms and periodically trimmed model logs;
  no permanent list/set of millions of completed warmup requests.
- Start with small controls and an explicitly reduced-window **infrastructure-only** training
  pilot, production_evidence=false. It is not W5M evidence or an independent performance sample.
- Require actual lint, compile/make/simulation exits0, raw JUnit no failures/errors/skips, exact
  matrix/params/workload hashes, pin/oracle/conservation checks, hand-derived metric unit tests
  and rejection controls. Keep every failure/incomplete attempt; never silently waive a check.
- Report expensive trained/finite cases as mechanistic single-seed evidence. Three control
  seeds describe sensitivity; do not reuse the primary20-seed t19 interval or claim generality.

Codex owns independent audit and development record. Native Claude Code RTL Agent Team is the
implementation workflow; actual quota exhaustion allows the owner's Sol/high fallback. Preserve
prompts/settings/streams/exits, changed-file diff, source hashes and execution logs in ignored
`.setup-logs/implementation/descriptor-followup-20261022/`. Adopt only actual completed results.
