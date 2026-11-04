# Matched trained-power results: exploratory seeds509–511

All18 captures and all9 matched A/B policy/seed power pairs have completed parent and independent index adoption. This report verifies their raw bindings and summarizes the printed PrimeTime estimates. This analysis did not rerun simulation or remote EDA, or alter source inputs.

## Measurement scope

N4, depth16, full105-bit descriptors, FCFS / RR10 (quantum10) / Main; common25ns (40MHz) clock, SAED32 RVT `tt0p78v25c`, frozen mapped source revision `759f86b24f13ed5984c19034eeeea2ca43b0e971` and common profile. Each capture replays actual10,000,000 training cycles; B additionally replays A and the guard before its own measurement starts.

| Arm | Measured cycles | SAIF duration | Total replayed cycles | Window |
|---|---:|---:|---:|---|
| A | 100,000 | 2,500,000 ns (2.5 ms) | 10,100,000 | trained A only |
| B | 102,400 | 2,560,000 ns (2.56 ms) | 10,203,424 | trained B only, following A and1,024 guard cycles |

Reported power is an average over that arm’s annotated interval. A/B are distinct windows and are summarized separately. Training, A or guard cycles preceding B are replayed without being included in B SAIF duration.

The exact `power.rpt` declarations are `Dynamic Power Units = 1 W`, `Leakage Power Units = 1 W`, `Time Units = 1 ns`; `units.rpt` prints `Time_unit : 1e-09 Second`. Table values below preserve the original printed W tokens. Clock-pin internal power is included in internal power. Wire-load mode is `top`, model `ForQA`; this is zero-delay/no-SDF prelayout estimation.

## All18 printed estimates

| Policy | Seed | Arm | Internal (W) | Switching (W) | Leakage (W) | Total (W) |
|---|---:|---|---:|---:|---:|---:|
| FCFS | 509 | A | 1.306e-03 | 1.779e-05 | 2.032e-03 | 3.356e-03 |
| FCFS | 509 | B | 1.306e-03 | 1.755e-05 | 2.032e-03 | 3.355e-03 |
| FCFS | 510 | A | 1.306e-03 | 1.781e-05 | 2.032e-03 | 3.356e-03 |
| FCFS | 510 | B | 1.306e-03 | 1.755e-05 | 2.033e-03 | 3.356e-03 |
| FCFS | 511 | A | 1.306e-03 | 1.782e-05 | 2.032e-03 | 3.356e-03 |
| FCFS | 511 | B | 1.306e-03 | 1.754e-05 | 2.034e-03 | 3.357e-03 |
| RR10 | 509 | A | 9.995e-04 | 1.343e-05 | 1.546e-03 | 2.559e-03 |
| RR10 | 509 | B | 9.991e-04 | 1.309e-05 | 1.547e-03 | 2.559e-03 |
| RR10 | 510 | A | 9.995e-04 | 1.345e-05 | 1.547e-03 | 2.560e-03 |
| RR10 | 510 | B | 9.991e-04 | 1.309e-05 | 1.548e-03 | 2.560e-03 |
| RR10 | 511 | A | 9.995e-04 | 1.346e-05 | 1.547e-03 | 2.560e-03 |
| RR10 | 511 | B | 9.991e-04 | 1.309e-05 | 1.549e-03 | 2.561e-03 |
| Main | 509 | A | 1.331e-03 | 1.918e-05 | 2.116e-03 | 3.466e-03 |
| Main | 509 | B | 1.331e-03 | 1.873e-05 | 2.116e-03 | 3.465e-03 |
| Main | 510 | A | 1.332e-03 | 1.921e-05 | 2.116e-03 | 3.467e-03 |
| Main | 510 | B | 1.331e-03 | 1.874e-05 | 2.117e-03 | 3.466e-03 |
| Main | 511 | A | 1.332e-03 | 1.922e-05 | 2.116e-03 | 3.467e-03 |
| Main | 511 | B | 1.331e-03 | 1.874e-05 | 2.117e-03 | 3.467e-03 |

## Descriptive mean and observed range

Each cell is arithmetic mean [minimum, maximum] across exactly the three exploratory seeds509,510,511, in **mW**. Means are computed with Decimal from the printed W tokens, then displayed to six significant digits; extra mean digits are arithmetic, not additional measurement precision. Ranges describe these observations and are not confidence intervals. Component sums need only agree with printed totals within their rounding bounds.

| Policy | Arm (n=3) | Internal mW | Switching mW | Leakage mW | Total mW |
|---|---|---:|---:|---:|---:|
| FCFS | A | 1.30600 [1.30600, 1.30600] | 0.0178067 [0.0177900, 0.0178200] | 2.03200 [2.03200, 2.03200] | 3.35600 [3.35600, 3.35600] |
| FCFS | B | 1.30600 [1.30600, 1.30600] | 0.0175467 [0.0175400, 0.0175500] | 2.03300 [2.03200, 2.03400] | 3.35600 [3.35500, 3.35700] |
| RR10 | A | 0.999500 [0.999500, 0.999500] | 0.0134467 [0.0134300, 0.0134600] | 1.54667 [1.54600, 1.54700] | 2.55967 [2.55900, 2.56000] |
| RR10 | B | 0.999100 [0.999100, 0.999100] | 0.0130900 [0.0130900, 0.0130900] | 1.54800 [1.54700, 1.54900] | 2.56000 [2.55900, 2.56100] |
| Main | A | 1.33167 [1.33100, 1.33200] | 0.0192033 [0.0191800, 0.0192200] | 2.11600 [2.11600, 2.11600] | 3.46667 [3.46600, 3.46700] |
| Main | B | 1.33100 [1.33100, 1.33100] | 0.0187367 [0.0187300, 0.0187400] | 2.11667 [2.11600, 2.11700] | 3.46600 [3.46500, 3.46700] |

## Qualified warnings, annotation and static gaps

| Policy | FF clock pins | File-annotated nets / total | Fully annotated leaves / total | Constant leaf gaps / disabled arcs | Proven disconnected always-X paths | check_power per capture |
|---|---:|---:|---:|---:|---:|---|
| FCFS | 8856 | 27689 / 27689 | 27124 / 27156 | 32 / 64 | 15 | {'ramp': 2, 'load': 1} |
| RR10 | 6782 | 21276 / 21276 | 20660 / 20660 | 0 / 0 | 1 | {'ramp': 2, 'load': 1} |
| Main | 9011 | 30112 / 30112 | 29310 / 29344 | 34 / 68 | 56 | {'ramp': 0, 'load': 0} |

These policy-specific counts are invariant across the six captures of each policy and match the accepted semantic receipts. All nets have file activity; the leaf annotation gaps are the exact mapped literal-constant leaves with reviewed disabled timing arcs. The always-X paths are the exact previously proven disconnected output/alias paths; they are retained limitations, not newly treated as toggling known nets. No transientX/Z was accepted.

FCFS/RR check_power table-domain warnings remain qualified estimates: the warning pin/range identities must match the accepted prior mapped topology and current SAIF zero activity. A qualified `check_power` failure is not relabelled a clean check. Main’s no-range-issue cases are kept distinct. The per-case range details and dispositions remain in analysis.json and the bound raw/semantic receipts. No new per-pin remote query or physical signoff is claimed.

## Matching, provenance and limits

The complete identity set is3 policies ×3 seeds ×2 arms, with no duplicates or exclusions. For each seed/arm, the traffic SHA is equal across policies; the common project/runtime source closure, accepted source revision, period/corner/profile and measured-window lengths also agree. Each policy uses its own accepted mapped netlist/SDC; mapped hashes and source ZIP bytes are not required to match across policies. Native exporter exits, complete audits and all28 downloaded-file hashes are verified through existing contracts.

All18 cases use the existing frozen index case inspector, including its detached validator for the six seed511 cases and the adopted parent/independent semantic receipts. Original foreground transport255 histories in recovered cases stay unchanged; recovered actual EDA0 is separate. Detached launchSSH0 is not EDA0 and no foreground power.exit.json is fabricated. Successful derived remote cleanup does not remove the retained canonical local evidence.

Seeds509–511 are exploration seeds, not confirmation samples. No confirmation confidence interval, p-value, hypothesis test or population generalization is justified by these three observations. A/B means and ranges remain separate because their durations and traffic windows differ. No cold/boundary power observations enter the tables; historical boundary data are used only for accepted topology/static-gap proof.

Policy comparisons describe these particular mapped implementations and their input traces. FF/net/leaf counts and cell mix differ by policy; leakage and internal clock power therefore reflect different implementations. Matching inputs/profile does not make topology identical or isolate scheduler-policy causality. No energy-per-request, throughput/latency tradeoff, causal performance benefit, dynamic glitch, APR/routed parasitic, clock-tree or physical power signoff claim is made.

## Reproducibility and adoption inputs

Generated by the standard-library script [analyze.py](../../../.setup-logs/implementation/revision-20261024/trained-power-results-20261026/analyze.py). It creates a new output directory and never modifies inputs. Input anchors:

- 14-case manifest SHA256: `4ea44d99bb693e7a569d55cca705ce977ad7e4e6c4f1a03156bfc14bb3497332`.
- final4 adoption SHA256: `f2676fc281f0957163105bf4636f83d7d3faa8c4ca30345d8dbee7cf452026b9`.
- ready18 manifest SHA256: `9d26aa70fa688c068311b70c20c9a2583eae4a9c63e7abba0a9355e3d895c61e`.
- frozen index release SHA256: `d8ac633b07b71af588a8a4c3a79fc877416651510ffe7a52739c3a14864401e7`.
- parent/independent final18 adoption SHA256: `78aaef88589fd9ee785740de3d11441a389f0a7ba317d8b0190f417517a3db53`.

The cumulative18 manifest is copied unchanged from the frozen final4 index release; its first14 case records equal the prior manifest and its final4 wrappers match the parent adoption receipt. analysis.json retains printed tokens, Decimal summaries, traffic/source/mapped hashes, policy qualifications and per-case metadata/native/parent/semantic/raw-report references. The cumulative power index is already parent/independent adopted by the hash-bound final18 adoption receipt. This copied analysis manifest adds no new acceptance or trust anchor.
