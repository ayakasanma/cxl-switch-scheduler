# N4 descriptor follow-up test plan

This isolated suite extends `scripts/run_verify.py` through
`scripts/run_descriptor_followup.py`. It changes no old runner scope, RTL, model,
Spec, PPA flow, primary evidence, literature source or final report.

## Declared scopes

| Scope | Matrix | Warmup / measurement |
| --- | --- | --- |
| `DF-pilot` | 12 fixed-load + 3 full-size finite + 6 W64/W256 trained infrastructure jobs; seed509 | controls128/1024; trained2W/512; finite0/1024 |
| `DF-controls` | four cases × seeds509..511 × FCFS/RR10/Main =36 | 10,000 /100,000 |
| `DF-finite` | seed509 × three policies =3 | 4096 requests generated over1024 cycles, then complete all work |
| `DF-trained` | seed509 × three policies =3 | real10,000,000 /100,000; RTL-default W5,000,000 |
| `DF-placement-pilot` | Low subsets `(2,)`, `(0,3)`, `(0,1,2)` × three policies =9 | real512 /240; W256 sensitivity |
| `DF-placement` | all14 nonempty proper Low subsets × three policies =42 | real512 /240; W256 sensitivity |

`DF-pilot` is always infrastructure-only: top-level status `INFRA_SMOKE_PASS`
requires all ordinary strict checks and the declared pilot matrix gate, while
`milestone_acceptance_scope=false` and `production_evidence=false`. Its full-size
finite runs repeat the same4096 work, not independent samples. Full scopes remain
NOT_RUN until explicitly executed. No shortened window is production evidence.

Placement uses `case=placement`, `low_sources`, `sensitivity_evidence=true`,
`production_evidence=false`, `infrastructure_only=false`. The nine-case pilot is
not full-matrix acceptance. Its trace configuration records the subset, version,
window, training counts, quiet slots, fill length and measured demand. Legacy case
configuration, random seeding and trace hashes remain unchanged.

For Low cardinality k, every training window generates `102//k` descriptors per
Low source and12 per High source, spread over252 cycles followed by four quiet
cycles. Closing successful-fire counts must equal generation counts in both
windows; Main must progress to B_H then L on exactly the target sources. The240
measured cycles end strictly before the next classification. All measured Main
class pins stay fixed, and both classes must be eligible throughout the112
cycles following the128-cycle fill. Drain remains separately measured and may
include later classifications; all generated descriptors/responses must complete.

After fill, complete class visits require10 fires. Two boundary cuts contribute
at most10 fires each, bounding the Low/High count difference by20; equal-demand
FCFS within a class differs by at most one source completion at each cut, giving
a per-class source-count spread bound of2. These are finite count gates, not
fitted percentage tolerances. Class shares approach1/2; individual Low/High shares
approach `1/(2k)` / `1/(2(4-k))`. Expected equal-demand Jain is about0.75 for k1/3
and1 for k2. Source permutations can retain small boundary/tie offsets.

## Traffic and boundaries

All intended traffic is streaming and policy-independent. The trace SHA256 covers
canonical configuration, every warmup/measurement cycle, its ready bit, and source
and all105 descriptor bits for every generation. The acceptance gate independently
regenerates this hash once per case/seed/window. Tags are unique monotonic32-bit
serials; only pending producer/FIFO/response records are retained, never a completed
tag history. Oracle informational logs are cleared every4096 simulated cycles.

Controls use independent per-source Bernoulli generation at total0.30/0.90/1.20
with ready1, or total0.60 with ready low on cycle `k%4==3`. Source randomness and
descriptors use a seeded private RNG whose seed includes the full trace config.

Training evenly spreads exactly `floor(.40W)` source0 generations and `floor(.05W)`
for each other source over each window's first `W-4` cycles; its last four cycles
are quiet and ready is1. Independent closing-fire counts must give source0 DOWN,
others KEEP. Main must close at literal B_H/H/H/H then L/H/H/H, and the next actual
cycle's class pins are checked. No state deposits or clock skipping occur. Measurement
then generates one descriptor per source per cycle. This is a finite overload transient,
not a stationary or full-window recovery experiment. Production checks both classes
actually eligible on every measured cycle after a fixed128-cycle fill, counts complete
10-fire class visits and labels partial/boundary visits. Equal class quotas imply no
general per-source or application fairness advantage.

Finite traffic releases32 descriptors per source at cycles31,63,...,1023: exactly
1024/source and4096 total. The sink follows the absolute periodic ready trace above.
After the fixed generation interval, every pending producer stays active with normal
valid/hold behavior. Drain keeps the same absolute-cycle ready function, stops all
generation, and completes the entire generated population and every tagged response.
Its bound is `2*(producer pending + FIFO pending)+128` cycles. All three scopes use this
full-population drain; the old primary boundary-only drain is untouched.

## Metric contract (`cxl-descriptor-followup-v1`)

`metrics.phases` separates warmup, measurement and drain counters. It includes per-source
generated/accepted/fired, pre-edge pin-history FIFO occupancy, producer backlog sampled
after current-cycle generation and before acceptance, per-source FIFO-nonempty cycles
and FIFO-nonempty sink-ready opportunities. Output cycles partition exactly into fire,
idle-ready, valid-output sink stall, and idle-not-ready. Any eligible-ready non-fire bubble
fails. Fire/cycle and fire/ready have explicitly different denominators.

`latency_by_cohort.generation` and `.acceptance` each contain per-source exact integer
histograms with count, arithmetic mean, nearest-rank P99 and extrema for generation→push,
push→fire and directly generation→fire. Cohorts are half-open warmup/measurement/drain
intervals, and include every later drain completion of their cohort. Direct P99 is never
the sum of stage P99s. `completion_cohorts[generation][acceptance][fire]` records all phase
crossings. Drain acceptance cohorts remain distinct from measurement acceptance cohorts.

Snapshots at measurement start, measurement end and drain end record producer pending
generation ages by generation cohort, FIFO pending acceptance ages by acceptance cohort,
and FIFO pending generation ages by generation cohort. Snapshot boundary `k` is the next
trace cycle, so ages are `k-event_cycle`. End-of-measurement snapshots remain the observed
right-censored cut even though full-population drain later completes those requests.

Per-source service gaps count only continuously FIFO-nonempty episodes. Initial delay
includes the first eligible slot; inter-service gaps count slots after the previous fire.
Wall cycles and eligible sink-ready opportunities have separate histograms. Empty-episode
termination is recorded separately. Each phase boundary right-censors the old open gap
and left-censors the new continuation; such completions never enter full initial/inter-fire
gap histograms. Producer-only backlog is never called scheduler-eligible work.

All reported performance timing comes from input/output pins and their reconstructed
history. Existing cycle-exact policy oracles, pin rules, descriptor/order/conservation,
input hold, no bypass, and tagged responses check every real RTL cycle. Models provide
correctness checks, not performance exports.

## Reproduction and evidence

In Ubuntu WSL at the existing repository root:

```bash
source scripts/wsl_env.sh
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-pilot -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-controls -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-finite -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-trained -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-placement-pilot -j 3 --make-jobs 2
# Only after the independent pilot review:
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-placement -j 3 --make-jobs 2
```

Do not use seed/filter/length overrides as declared-scope evidence. Each scope runs strict
lint, meaningful pytest unit/rejection checks, real Verilator compile/make/simulation and
exact raw JUnit checks using the unchanged existing engine. Each output directory under
`artifacts/implementation/<scope>/<run-id>/` retains commands, versions, params, stdout,
JUnit, per-run metrics, source hashes and the independent matrix/hash gate. The task log
under `.setup-logs/implementation/descriptor-followup-20261022/sol/` preserves attempts,
the frozen added-file diff/manifest, old-source byte preservation, final numeric process
exits and pilot cost measurements. Missing, failed, skipped or incomplete work is not PASS.

Early pilots take about56 seconds including21 independent builds at `-j3`. They are too
short to predict full cost precisely. Their active-loop rates suggest roughly25–45 minutes
for the three concurrent10M training jobs, plus the400k-descriptor completion and histogram
export; budget an hour or more. Controls should take minutes, finite scopes about10 seconds.
Full trained jobs have a conservative24-hour per-simulator timeout. Large transient backlog
and exact age/latency histograms can consume substantially more memory than these pilots;
warmup storage remains bounded by pending work, finite histogram domains and4096-cycle log
trimming. Observed maxima are not WCET or general starvation guarantees.
