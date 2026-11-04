# Main-SQ hardware-cost comparison

Status: **SQ synthesis/STA/Formality/power NOT_RUN**. The causal diagnosis gate did not
support implementing the proposed SQ candidates. There is no SQ RTL/netlist, so there
is no measured SQ area, slack, power, or equivalence result to report. No FastX invocation
has been made for this task. No timing target or accepted library constraint was changed.

## Accepted reference costs

The following are existing N4 whole-switch measurements, independently cross-checked
against the original summaries; they are not new measurements.

| Policy | Total area | Comb area | Sequential area | FF | Policy subtree | Setup slack ns | Hold slack ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FCFS |103970.058316|45419.345105|58550.713211|8856|1131.9574|13.071612|0.033790|
| RR10 |79047.172316|34232.434461|44814.737855|6782|263.0390|20.519341|0.049066|
| Main |110089.845892|50507.308009|59582.537883|9011|7143.9879|10.496409|0.039940|
| SQ1 |NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|
| SQ2 |NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|NOT_RUN|

Area is in **library area units**; no unvalidated conversion to um²/NAND2. Subtree reports
are rounded to four decimals. Whole-switch deltas include required metadata and changes
to mapped shared logic; they are not pure selector cost. N16 Main's +1.158148ns setup
slack at25ns is a constraint on future arbitration depth, not an SQ timing prediction.

Source: [primary JSON](../../ppa/primary-20261021-v2.json), mapped source
`759f86b24f13ed5984c19034eeeea2ca43b0e971`, frozen Spec `1af80967…`; current Main bridge
proofs connect the October22 simulation RTL to those original Main netlists.

## Frozen methodology for any future candidate pilot

- DC/PT W2024.09, SAED32 RVT TT0.78V25C; the complete synthesized switch boundary.
- Common profile `saed32-rvt-tt-25ns-forqa-cap075-v2`, canonical SHA256
  `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`.
- 25ns, setup/hold uncertainty0.1/0.05ns, I/O min/max0/2ns, transition0.1ns,
  outputload2.656828fF, ForQA/top wire-load, autoselectionoff, compilemedium, one core.
- Temporary in-memory DC cap target0.75 is restored before outputs; fresh PT uses original
  DB limits. This neither edits the proprietary library nor relaxes acceptance.
- Functional correctness before N4 synthesis, own RTL-to-own-netlist Formality, then a
  justified N8/16 expansion. New policies intentionally differ behaviorally from old Main.
- Collect paths, sequential/comb/whole/policy area, FF and all electrical checks; do not
  accept an improved tail with failed25ns timing.

Existing power evidence is activity-dependent pre-layout VCS/SAIF/PT estimation, with
recorded range/extrapolation qualifications. It was **not measured with these heavy/sparse
traces**, and does not estimate SQ power. No physical routing/CTS/glitch/multicorner signoff
is implied. All proprietary assets remain external to this repository.
