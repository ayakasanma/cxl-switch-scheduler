# CGOF correctness and N4/N8/N16 synthesis/STA

Date: 2026-10-28 Asia/Taipei. Evidence tier: `SCHEDULER_RTL`.

The approved sequence was the complete correctness matrix followed by a
matched synthesis/STA matrix. Five additional configurations and Formality
runs now cover CGOF (1:1) at N4/N8/N16 and CGOF (2:1) at N8/N16. The original
N4 CGOF (2:1) result is retained below as the matched comparator. The
preparation manifests remain immutable preparation records, not execution
status.

## Correctness

Run: `artifacts/implementation/revision-cgof/20261027T222326Z_1164`.

- `complete_matrix=true`, `stable=true`, runner and scope exits both zero.
- 152 steps: 145 PASS, seven expected rejections, zero failed or unrun steps.
- 463 tests, zero failures, errors or skips; separate model unit tests 17/17.
- Source archive SHA-256:
  `c202a407c50d3bbb0f7dd0daaf3d6618b623ce70ea065e95ca49ec5e8702353f`.
- Before/after source hashes and the archive were independently rechecked.
  No RTL or model changes were made for this PPA execution.
- The earlier Windows environment failure is retained; it is not an RTL
  correctness failure.

Reproduce from Ubuntu WSL with the project environment:

```bash
source scripts/wsl_env.sh
python -B scripts/run_revision_cgof.py --complete-matrix --jobs 2
```

## Bound synthesis configuration

All runs use D16/M1, full 105-bit descriptors, W5,000,000 and
`ELIGIBLE_RR=0`. The complete descriptor FIFOs, arrival metadata, policy state
and shared output-hold boundary are included. CGOF (1:1) uses
`HIGH_WEIGHT=1`; CGOF (2:1) uses `HIGH_WEIGHT=2`.

Design Compiler, PrimeTime and Formality are W-2024.09. The unchanged frozen
TT 0.78 V / 25 C, 25 ns, cap075-v2 profile and SAED32 RVT library were used.
Power remains `NOT_RUN`; this is a pre-layout comparative area/STA experiment.

| Binding | SHA-256 |
| --- | --- |
| Payload tar | `d1aee52ed4daa0d55c0c2f074e854819e617fa07fe0229f89d1ac284f5fcbeed` |
| Preparation manifest | `2c042f78b04acbb1245c8147643f27b8dd529f31fc06f96fae2a9060d444107e` |
| Canonical profile | `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d` |
| Library, kept remote | `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094` |
| Mapped netlist | `2e589206b19524938ce4345d8773141c692318a5884cf54092abc8c8047daa76` |
| Generated SDC | `f7de441d8e9f0611114d70275b7434015ff6b698b2c966041987ce8d357577e5` |
| SVF, kept remote | `52ebcd212c7aff0ead98788eaa5ea0157d38f6c7fa4833c50544184d7cadf0b3` |

## Observed PPA matrix

| Policy | N | Total cell area | Comb. cells | Seq. cells | PT worst setup (ns) | PT worst hold (ns) | Coverage met/total | Formal passing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CGOF (1:1) | 4 | 106163.066946 | 18786 | 8998 | +12.683299 | +0.034898 | 36284/36352 | 8972 |
| CGOF (1:1) | 8 | 212027.006396 | 37718 | 17915 | +8.135937 | +0.054674 | 71958/72022 | 17802 |
| CGOF (1:1) | 16 | 423513.448454 | 75423 | 35748 | +3.158005 | +0.078278 | 143244/143244 | 35460 |
| CGOF (2:1) | 8 | 218863.734160 | 40386 | 17947 | +5.675092 | +0.103860 | 72026/72030 | 18064 |
| CGOF (2:1) | 16 | 436771.124393 | 80587 | 35812 | +1.248813 | +0.084335 | 143500/143500 | 35938 |

All five new runs report zero violated timing checks. Untested checks remain
68 at 1:1/N4, 64 at 1:1/N8, four at 2:1/N8, and zero at 1:1/N16 and 2:1/N16.
The 1:1/N4 and 1:1/N8 cases therefore do not claim complete timing-check
coverage.

Formality reports `Verification SUCCEEDED`, `verify_return=1`, zero
failing/aborted/unverified/unmatched points, no user constants and no
compare-point exclusions for every new configuration. For CGOF (1:1), however,
Formality leaves accounting state unread: 138 DFFs at N4, 230 at N8 and 414 at
N16. The counts equal `23 * (N_SRC + 2)`, corresponding to classifier
accounting state with no observable consumer when `HIGH_WEIGHT=1`; the
implementation also optimizes away `cls_q`. The defensible claim is therefore
observable-boundary equivalence with disclosed unread/dead state, not full
all-register equivalence. Both CGOF (2:1) runs have no unread compare points.

### Existing N4 CGOF (2:1) comparator

| Item | Observed |
| --- | ---: |
| DC / PT / Formality command exit | 0 / 0 / 0 |
| Total cell area, library area units | 109794.784709 |
| Combinational area | 50198.523048 |
| Noncombinational area | 59596.261661 |
| Macro/blackbox area | 0 |
| Sequential cells / declared state bits | 9014 / 9014 |
| Worst reported setup slack, ns | +10.398800 |
| Worst reported hold slack, ns | +0.038578 |
| DC / PT reported constraint violations | 0 / 0 |
| Met / violated / untested timing checks | 36348 / 0 / 68 |
| Passing output bits / registers | 112 / 9014 |
| Total passing formal compare points | 9126 |
| Failing / aborted / unverified / unmatched points | 0 / 0 / 0 / 0 |

The area components reconcile to total cell area within report rounding.
Net-interconnect area is separate and is not added to the comparative cell
area. A separate read-only audit expanded 29255 leaf cells and summed their
reference areas to 109794.784711, within 0.000002 of the reported total.
Registers reconcile exactly: 6720 descriptor bits + 2048 timestamps + 52 FIFO
control bits + 32 arrival-counter bits + 154 policy bits + eight hold bits.

Reported cell count is 29345, exceeding expanded leaves by 90. Both methods
have that difference. There are 27 nonleaf occurrences; the remaining 63
are unresolved under that counting interpretation. This does not affect
leaf-area or register reconciliation. Reported counts are not leaf counts.

### Matched FAI-inspired comparison

The comparator is
`artifacts/fastx/primary-20261021-v2-fai-main-n4/`. Its `profile.json` and
`profile_applied.rpt` are byte-identical to this run. Library bindings and
common FIFO/hold/selection/package RTL were also checked.

| Item | FAI-inspired | CGOF (2:1) | CGOF minus FAI-inspired |
| --- | ---: | ---: | ---: |
| Total cell area | 110089.845892 | 109794.784709 | -295.061183 (-0.268019%) |
| Sequential cells | 9011 | 9014 | +3 |
| Worst reported setup slack, ns | +10.496409 | +10.398800 | -0.097609 |
| Worst reported hold slack, ns | +0.039940 | +0.038578 | -0.001362 |

This is a small complete-design difference, not an isolated credit-logic
area benefit. CGOF uses a standalone top while the comparator uses a
parameterized top. Four AND2 push gates account for 8.132608 of the area
difference in top-level glue; policy, FIFO and hold contributions are
-278.541824, -8.640895 and +0.254144 respectively. Interface and storage
boundaries match, but the top glue is not identical. Both methods have zero
reported constraint violations at the frozen 25 ns period.

All 68 untested timing checks are disclosed: 64 arrival-counter D=0 checks
and four SETB=1 checks on two window-counter registers. They correspond to
propagated constants, not user timing exceptions. The rounded coverage
percentage is not a claim of 100% tested coverage.

Formality returned `verify_return=1`, with no active blackboxes, no post-match
undriven nets, no user constants or compare-point exclusions, and all 28
user-setup commands at zero. The 40 pre-match implementation undriven nets,
12 rejected uniquify guidance operations and unlinked library power-cell
metadata warnings remain in the evidence; the full proof succeeds.

Other retained diagnostics include assertion-string/sign conversions,
hierarchical naming, high-fanout wire-load estimation, optimized arithmetic
ports and SDC-version warnings. They are not hidden by a zero exit status.
No Error/Fatal or unresolved-reference failure was observed.
In particular, TIM-134 caps the clock-net fanout estimate at 1000 despite
9014 sequential loads; absolute pre-layout timing may be optimistic.
Only 20 paths are displayed in each timing report; full analysis-coverage
counts establish the reported zero-violation result.

## Evidence and review

- CGOF (1:1) DC/PT reports and mapped netlists:
  `artifacts/fastx/cgof-ppa-dcpt-cgof1-n4-20261028/`,
  `artifacts/fastx/cgof-ppa-dcpt-cgof1-n8-20261028/` and
  `artifacts/fastx/cgof-ppa-dcpt-cgof1-n16-20261028/`.
- CGOF (2:1) N8/N16 DC/PT reports and mapped netlists:
  `artifacts/fastx/cgof-ppa-dcpt-cgof2-n8-20261028/` and
  `artifacts/fastx/cgof-ppa-dcpt-cgof2-n16-20261028/`.
- CGOF (1:1) Formality reports:
  `artifacts/fastx/cgof-ppa-formal-cgof1-n4-20261028/`,
  `artifacts/fastx/cgof-ppa-formal-cgof1-n8-20261028/` and
  `artifacts/fastx/cgof-ppa-formal-cgof1-n16-20261028/`.
- CGOF (2:1) N8/N16 Formality reports:
  `artifacts/fastx/cgof-ppa-formal-cgof2-n8-20261028/` and
  `artifacts/fastx/cgof-ppa-formal-cgof2-n16-20261028/`.
- Existing matched CGOF (2:1) N4 DC/PT and Formality reports:
  `artifacts/fastx/cgof-ppa-dcpt-20261028T0723/` and
  `artifacts/fastx/cgof-ppa-formal-20261028T0727/`.
- Parent reviews:
  `parent-pre-formal-review.json` and `parent-formal-review.json` in those
  respective directories.
- Separate read-only area/STA review:
  `independent-area-sta-review.json` in the DC/PT directory. Verdict:
  `ACCEPT_WITH_CAVEATS_FOR_PRE_LAYOUT_COMPARATIVE_AREA_STA_ONLY`.
- Remote final-hash review:
  `.setup-logs/FastX-NN/remote/232646-cgof-ppa-formal-final-hashes-20261028`.

Upload, downloaded report checksums, all 62 preparation inputs, source
before/after bindings and DC-to-PT/Formality netlist/SDC/SVF hashes were
checked. Proprietary library, license and executable assets were not copied.
Every file listed in each new directory's `download-manifest.json` was
re-hashed locally with zero mismatches. Formal `FM_INFO` side files were not
downloaded, so their hashes were not independently rechecked.
The raw wrappers report `COMMANDS_COMPLETED_REVIEW_REQUIRED`; acceptance
requires review of the reports, not that marker alone.
The independent reviewer reconciled leaf area, registers, hierarchy and
the matched profile. Exhaustive independent re-enumeration of every
displayed slack line and each comparator disabled-check reason was not
completed; the full coverage totals and worst slacks were checked.

No APR, extracted parasitics, multicorner signoff or workload power was run.
This result establishes implementation feasibility within the stated
boundary. It does not measure completed memory bandwidth, CXL response
latency or application slowdown. Those remain `REAL_CXL/APPLICATION: NOT_RUN`.
