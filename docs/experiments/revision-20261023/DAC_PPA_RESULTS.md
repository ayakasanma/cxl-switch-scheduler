# DAC2 N4 matched pre-layout result

Run: `artifacts/fastx/revision-dac-ppa-20261023T190649Z/`.
Upload, DC, PT, Formality and download exited0. Parent and separate independent
formal and area/STA reviewers accepted the actual reports within this scope.
This is measured synthesis/STA and mapped-equivalence evidence, not physical
signoff or an accepted performance improvement.

## Bound configuration

- Native accepted DAC2, N4/D16, full105-bit descriptors, W5M, High weight2.
- Payload SHA256:
  `017d58f88edce7b62494466fd571ad6f70230105ba379a6350e0ca61281b8b96`.
- Manifest SHA256:
  `759586524658dbbc93bf005d76e2e9df98c03c23560ded9283044e47ed14becf`.
- Download tar SHA256:
  `735dd77847fc2dc4c0690a6a895a48e8149e9bee0148758990ac0330352cae94`.
- Original frozen TT0.78V/25C, 25ns, ForQA/top, medium-compile,
  cap075-v2 profile. All61 preparation inputs were rechecked unchanged
  after execution. The complete FIFO, arrival metadata, policy, credit and
  hold state remains in the synthesized/formal boundary.

## Actual report facts

| Item | Observed |
|---|---:|
| Total cell area | 109794.784709 |
| Combinational area | 50198.523048 |
| Noncombinational area | 59596.261661 |
| Macro/blackbox area | 0 |
| Sequential cells / declared native state bits | 9014 / 9014 |
| Worst reported setup slack, ns | +10.398800 |
| Worst reported hold slack, ns | +0.038578 |
| Violated timing checks | 0 |
| Met timing checks | 36348 |
| Untested timing checks | 68 |
| Passing formal output bits / registers | 112 / 9014 |
| Total passing compare points | 9126 |

`area_summary.rpt` reconciles combinational plus noncombinational area to
total cell area. Net interconnect area is separate; do not substitute total
area for total cell area or sum parent/child hierarchy rows twice.
The existing matched Main N4 cell area is110089.845892. Any comparison
must preserve the same pre-layout methodology and retain the entire
hardware boundary; the small difference is not a general area-efficiency claim.

## Timing coverage and formal scope

Parent matched all68 untested pin/check pairs to the propagated-constant
arcs in `pt_disable_timing.rpt`:64 arrival-counter D=0 setup/hold checks
and four checks on the SETB=1 pins of two window-counter registers.
The latter constants are explicit in the mapped netlist. They remain
disclosed untested checks; the rounded tool percentage is not100% coverage.
The first one-off parser expected every cell name on a separate line and
missed the four inline SETB rows. Supporting both actual report layouts
resolved that parser assertion without changing reports or acceptance rules.

Formal reports show `verify_return=1`, all9126 points passing and
zero post-match undriven nets. Setup reports record9014 reference and
implementation registers, zero blackboxes/multiple-driven nets and
zero user-specified setup overrides. Compare-point exclusions, constants,
SVF guidance, final source bindings and all empty failure reports were
independently reviewed. All28 user setup commands are0/0. Failing, aborted,
unverified, unmatched and constant-register counts are0. SVF guidance has
122 accepted and12 rejected uniquify operations, with0 unsupported/unprocessed;
the complete proof succeeds. The original SVF stays remote; local review uses
its bound handoff hashes and actual tool reports.

## Independent area attribution and retained count limitation

Independent recursive expansion finds29255 leaf cells:20241 combinational
and9014 sequential. Summing leaf reference areas gives109794.784711002126,
only0.000002002126 above the reported total due to report precision.
The leaves include6720 descriptor FF,2048 timestamp FF,32 arrival-counter FF,
154 policy FF,8 hold FF and52 FIFO pointer/occupancy FF. No storage or policy
state was removed for this comparison.

Matched Main N4 has9011 registers and total cell area110089.845892.
DAC2 adds3 registers; sequential area increases13.723778 while combinational
area decreases308.784961. The net cell-area difference is-295.061183
(-0.2680185%). This is an observed complete-design comparison, not an
isolated area attribution to credits or a physical-area saving.

The tool's number_of_cells29345 exceeds leaf cells by90; only27 nonleaf
hierarchy occurrences are found, leaving63 unexplained by that counting
interpretation. Main has the same residual. Cell-count semantics remain
unresolved even though independent leaf-area reconciliation passes.
Do not silently equate the reported cell count with leaf count.

Independent evidence:
`.setup-logs/implementation/revision-20261023/dac-ppa/independent-formal-audit-20261023T191704Z.json`
and `independent-review-20261023T191716Z/` in the same directory
(audit, two leaf CSV files and output hashes).

No APR/extracted parasitics, multicorner or physical signoff was run.
Matched trained-HOG power and the full candidate confirmation cohort
remain pending. PPA timing feasibility does not satisfy the performance
adoption gate by itself.
