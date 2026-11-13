# Experiment backlog

What is still unrun, why it matters, and what it costs. Ordered so that each step
either unlocks the next one or closes a gap a reviewer already raised.

Measured basis for every estimate below: one W5M model job with full accounting takes
0.362 h alone (16,785 cycles/s) and 0.449 h per job at seven processes; one Main W5M RTL
job takes about 2.13 h and two run concurrently (A3: four jobs, two batches, 15,328 s).
The 2.27 h single-job figure in earlier notes came from the thread-parallel pilot, where
the GIL serialised the workers, and does not describe one process.

## Status (2026-11-04)

| # | Item | State | Next step |
| --- | --- | --- | --- |
| 1 | Cost re-freeze | done, `FROZEN_V2_COST_REV2` | none |
| 2 | Clean A3 re-run | done: `20261104T063359Z_1495`, source stable, 4/4 jobs, G-EQ 4/4, 12,149 s | none |
| 3 | Confirmation campaign | done: 20 seeds, 600 jobs, 0 failed, analysis complete (P1, P2 and P3 all SUPPORTED_WITHIN_PROTOCOL) | fold the verdicts into the report text |
| 4 | Under/over pairs | not started | six hours of model time at seven processes, no source change |
| 5 | CGOF gate-level power | not started | needs the FastX SAIF flow and a PrimePower slot |
| 6 | Latency recovery and N8/N16 | not started | define `latency_recovery` before measuring it |
| 7 | RTL drain anchor | one A3 anchor drained two cycles with conservation intact | add a directed cut inside a long backlog |
| 8 | System level | out of scope | keep as a stated limitation |

The campaign release record is
[dynamic-role-switch-v2-confirmation-release-20261104](reviews/dynamic-role-switch-v2-confirmation-release-20261104.md).

## P0 — required before any confirmation claim

### 1. Re-freeze the campaign cost model

The frozen plan still says 600 confirmation jobs cost 26 h. The process-parallel pilot
measured 45 h. Rewrite the cost table and the hard caps from the measured numbers, then
create a new freeze receipt. Nothing downstream should start before this, because the
old budget would be breached mid-campaign.

Steps: update the cost section with measured per-job and per-wave times → state the new
caps → issue a receipt that pins the plan hash → record it in `docs/DEVELOPMENT_REPORT.md`.

### 2. Re-run A3 with a clean source freeze

The four Main W5M anchors passed and matched the model, but three files were edited while
the run was in flight, so its source-stability gate failed. Re-run the same four jobs
with no concurrent edits and no source changes.

Cost: 4.3 h wall at two concurrent jobs. Acceptance: source hash identical before and
after, all four jobs PASS, G-EQ against the model at the same job specification.

### 3. Confirmation campaign, seeds 7401–7420

Question: does CGOF beat Main on the role-switch and multi-window tails across twenty
held-out seeds, with the frozen three-contrast Holm procedure?

600 model jobs at seven processes ≈ 45 h, plus the two A4 Main RTL anchors for seed 7401
(3.5 h) and the per-seed audit (0.5 h each). `scripts/analyze_dynamic_role_switch.py`
produces the verdicts; it already refuses incomplete cohorts and excluded seeds.

Steps: freeze → run seed 7401 model plus A4 RTL → G-EQ → release the remaining nineteen
seeds one at a time → audit each → aggregate → report.

## P1 — closes a reviewer gap

### 4. Under- and over-load pairs on W5M RTL

The capacity-absorption argument currently rests on a twenty-seed model result: zero
completion penalty under load, about +834 cycles when overloaded. Only the near-load
point has RTL evidence.

Design: mixed/isolated pairs at `profile=under` and `profile=over`, W5M, N4, D16, three
policies, five seeds. Cost: 60 model jobs at five processes ≈ 6 h, then 20 RTL anchors
≈ 18 h. Acceptance: the mixed-minus-isolated completion gap keeps the same sign and
magnitude bucket as the model result.

### 5. CGOF gate-level power

FCFS, RR10 and Main have SAIF-based power; CGOF has none. Without it the area argument
is complete but the power argument is empty.

Design: three seeds at N4, CGOF 1:1 and 2:1, PrimePower with the same activity harness
used for the existing three policies. Also emit the `1:1` netlist with the unused
classifier registers pruned so the area claim can quote both numbers.

Cost: roughly one day of EDA time on the FastX machine, plus half a day to wire the SAIF
flow. Acceptance: power per policy with the activity file and its hash recorded.

### 6. Latency recovery and larger N

`latency_recovery` was never defined for the closed-loop buffer experiments, and N8/N16
have PPA data but no finite-Heavy latency runs.

Design: define recovery as the cycle count from a role switch until the switched-in
source's P99 returns to its steady-state band, then measure it at W5M for Main and CGOF.
For N8/N16, run the multi-window case at five seeds. Cost: about 8 h model plus 20 h RTL.

### 7. RTL drain evidence

The cleanup path has been exercised once in hardware. In the first A3 run, the
`depth8-bursty` mixed anchor cut with work still queued, drained it in two cycles, and
finished with `fired == accepted == 18,815,149`; the model replay of the same job also
records `drain_cycles = 2`, so the two agree. The other three anchors and all twenty
legacy anchors cut with empty queues.

What is still missing is a directed test: a cut placed deliberately inside a heavy
backlog, at a depth and policy where the drain is long enough to check ordering rather
than length one. Cost: 3 jobs, about 6 h. Acceptance: `drain_cycles > 0`, every drained
request fired in arrival order, and conservation intact.

## P2 — system level, keep as a stated limitation

### 8. End-to-end memory and application impact

Everything here measures the switch boundary: cycles from generation to fire. CXL.mem
round-trip latency, DRAM bank conflicts and application slowdown need a different
simulator. Doing it properly means porting the scheduler into CXL-DMSim or gem5 and
re-running a workload suite; that is a separate project, and the current report should
keep saying so.

## Order of execution

1. Re-freeze the cost model (step 1) — half a day, unblocks everything.
2. Clean A3 re-run (step 2) — 4.3 h, can run overnight.
3. Confirmation campaign (step 3) — two days of wall time at seven processes.
4. Under/over RTL (step 4) and drain anchors (step 7) — one day each, independent.
5. Power (step 5) and latency recovery (step 6) — need the FastX machine.
6. System level (step 8) — only if the report needs it.
