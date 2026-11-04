# Source placement and class cardinality — accepted RTL sensitivity

**ACCEPTED:42/42 actual Verilator/cocotb runs PASS**, independent raw-evidence audit PASS,
all process exits0 and no failed/error/skipped JUnit cases. Owner authorized the two
[planned checks](PLACEMENT_PLAN_2026-10-22.md). Final report stays untouched/unbuilt.

## What ran and what it establishes

N4/D16/M1/full105, FCFS, RR quantum10, Main. Every nonempty proper subset of source IDs
is naturally trained as Low: four singleton subsets, six pairs and four triples, each
with all three policies. Seed509 changes descriptor contents; these deterministic placements
are not independent random seeds or confidence-interval samples. Same subset has identical
external offered trace/ready across policies;14 trace groups are hash-checked. Actual
acceptance and completion are recorded separately.

Run `DF-placement/20261022T024651Z_297`, captured outer exit0,147.356s. Actual nonreset
cycles63,498:21,504 training,10,080 measurement,31,914 drain/response completion. Initial
126 reset edges are excluded. Each run uses supported stress W256,512 real training cycles
and240 measurement cycles. No state deposit, time skip, classification freeze or RTL change.
The measurement ends at trace cycle751, before next closing767; the first128 slots fill
queues, leaving112 continuously backlogged slots. Clock10ns is a simulation convention;
latency stays in cycles, separate from the25ns synthesis constraint.

Per training window, each of k target Low sources generates102//k requests; every other
source generates12. Requests spread over252 cycles, then four quiet slots. All actually
fire before closing: observed B/S and exact thresholds yield DOWN on targets and KEEP on
others. Main closes B_H then L on exactly those targets. The fixed class set is checked on
every measurement cycle. Both classes stay eligible after fill; complete visits require
10 successful transfers. Every generated request and abstract response is drained, including
producer pending work. Later drain can reclassify; its latency completions are retained but
its evolving class distribution is not pooled with fixed-class measurement service shares.

This is **short-window mechanism sensitivity**, not additional W5M evidence or a steady-state
adaptation study. The previous real two-W5M trained experiment remains the production-window
evidence for1L/3H. Scaling that evidence to all placements or later adaptation is not claimed.

## Observed class and source allocation

All42 measurement intervals produce239 transfers/240 cycles = **0.995833 transfers/cycle**,
zero avoidable bubbles; the one initial ready/idle slot follows no-bypass empty-start timing.
Every source generates240 requests and remains FIFO-nonempty/ready for239 measured slots.
There is no total-throughput advantage among policies in these cases.

Below, shares use the239 measured transfers. Ranges span source identities and placements;
they are descriptive finite-count ranges, not error bars or statistical intervals.

| Main trained class sizes | Placements | Share per Low source | Share per High source | Equal-demand source-service Jain |
| --- | ---: | ---: | ---: | ---: |
|1L /3H|4|50.2092%|16.3180–16.7364%|0.746836|
|2L /2H|6|25.1046%|24.6862–25.1046%|0.999947|
|3L /1H|4|16.7364%|49.7908%|0.753138|

For every placement, Main class totals are Low120/High119. After fill they are Low53/High59
over112 slots; the different cut phase explains that finite offset. All runs retain complete
and partial visits, left/right boundary context and censored service gaps. Completed measured
visits are12 Low/11 High plus nine High fires in the right partial visit. Within each class,
post-fill source counts differ by at most one. The declared acceptance bounds were20 class
count skew (two ten-fire boundary cuts) and2 within-class source spread, not fitted percent
tolerances. Observed post-fill skew is6. These gates are for this controlled symmetric trace,
not proofs of a general starvation bound.

FCFS and RR give each source59 or60 measured fires (24.6862–25.1046%), Jain0.999947 in all
placements. Small differences in which source gets59 remain visible; no cycle-identical
source permutation is claimed. Main's approximately half-output recipient follows the class
and its cardinality, rather than a permanent source0 preference. In3L/1H, the sole High source
gets119 fires while each Low gets40; in1L/3H the sole Low gets120. In2L/2H, shares approach
one quarter each. This supports the per-class quota explanation for the prior W5M observation.

Jain here describes service-count equality under equal persistent offered demand and actual
joint eligibility. It does not measure application slowdown, enforce uniform allocation
under unequal demand, or establish that the original paper has the same dispatch behavior.
The project's single-output10/10 reconstruction is the subject of this observation.

## Latency and reproducible evidence

[Per-source data](placement-per_source.csv) preserve generated/accepted/fired counts, source
shares, occupancy/backlog means, exact mean/P99/max stage and direct latency, cohort labels,
wall/ready service gaps and censor populations. Full histograms and snapshots remain in raw
run artifacts. Generation/acceptance cohorts include later drain completions; their delays
therefore may reflect later class changes. Use fixed-interval service counts for the clean
class-cardinality comparison; do not attribute whole-cohort latency to frozen classes.
Observed maxima are not WCET/starvation guarantees. No stage-P99 summing or completed-only
cohort exclusion is used. No claim about application IPC, slowdown, DRAM bytes/s or complete
CXL link utilization is made.

Durable records: [independent audit](placement-audit.json),[run index](placement-runs.csv),
[summary ranges](placement-summary.json),[source/execution provenance](placement-source-execution.json).
These supplement the accepted primary180 and previous42 follow-up; pilots/replays are not
new independent workload samples. Existing PPA and all functional RTL/model files remain unchanged.

```sh
source scripts/wsl_env.sh
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-placement-pilot -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-placement -j 3 --make-jobs 2
python scripts/audit_descriptor_placement.py --run RUN_ID --output FRESH_AUDIT_DIRECTORY
```

## Execution provenance, failures and review

Actual native Claude Code2.1.306/plugin0.14.6 focused invocation requested Opus5.5/medium,
session2ba93411-d537-4805-aca1-1290f21f43c2; weekly429, child exit1 after205.071s, no code
changes. The wrapper saved exit1 then hit a console UnicodeEncodeError; both are retained.
Owner-authorized GPT6.1Sol/high fallback implemented five isolated verification files, froze
them, and Codex independently reviewed inputs, code, pilot, full matrix and raw reports.

First pilot `20261022T024254Z_281` failed lint/exit1: proposed W4096 violates the existing
RTL parameter allowlist. All simulations were NOT_RUN. This was corrected to supported
stress W256 without modifying RTL or suppressing diagnostics. Passed pilot
`20261022T024506Z_270` exit0: three strict lint configurations,98 WSL unit cases and nine
real RTL simulations, independently validated. Pilot cycles13,605 are separate from the
63,498 formal cycles and are not independent placements beyond the complete42.

Parent six histogram/quota unit tests plus11 subtests pass; ten intentional actual-evidence
mutations are rejected (bad labels/subset/window/config/class/fire count/P99/response/class
summary/window count). Existing42 follow-up raw audit passes again, adding0 RTL cycles.
Full42 also runs98 units, three strict lint parameter sets, and strict compile/make/sim per job.
All failed/incomplete attempts remain archived, never silently discarded.

Before final adoption,188 pre-existing dirty Final/literature files and52 protected
RTL/refc/Spec/PPA files were byte-identical. Execution froze99 source files. After acceptance,
only README text encoding was repaired and the read-only audit's replay check was restricted
to simulation sources (excluding documentation and audit scripts themselves); all executable
simulation sources are unchanged and the42 raw audit passed again. Original execution hashes
and the postprocessing hashes are separate in the provenance record. No RTL rerun is implied
by that documentation/audit repair. No SSH, new synthesis/power, gem5 or Algorithm-2 expansion.

## Research implication

Together with accepted N4/8/16 synthesis and controlled functional/performance evidence, the
project connects a reproducible common switch implementation to its service-allocation cost.
RR10 has lower whole-switch area; FCFS/Main require arrival metadata. Main adds about4.97–5.89%
total area over FCFS under the frozen synthesis methodology, while these contention cases
show redistribution rather than increased aggregate capacity. Class-level allocation can
reduce source equality when class sizes differ. This is a measured tradeoff, not evidence
that one scheduler is universally optimal. Physical signoff/application-level conclusions
remain outside this descriptor-level course-study scope.
