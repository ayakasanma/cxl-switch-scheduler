# Archived primary-nine leaf area attribution

Continuation completed locally on 2026-10-24 from repository HEAD
`99400ded42cc63c3b206bd5d13f51d36344b2689`. This is an offline audit of the
nine `artifacts/fastx/primary-20261021-v2-{fcfs,rr,fai-main}-n{4,8,16}`
archives. The separate `*-loads-*` archives are excluded.

**Observed result:** all nine areas reconcile, all archived result checksums
verify, and all 540,590 expanded leaf instances have exactly one ownership
category. Unresolved ownership is zero in every case. All nine cases are
`PASS_WITH_WARNINGS` because the archived `number_of_cells` field matches
neither expanded leaves nor expanded leaves plus hierarchical instances.
The initial blanket "field inconsistent" interpretation is superseded by the
explicit definition checks below.

## Method

The audit parses structural mapped Verilog and every local Design Compiler
`reference.rpt` section, recursively expands hierarchy to full instance paths,
and checks local reference counts and hierarchical `h` attributes against the
netlist. Reused module definitions are expanded once per occurrence; cycles,
duplicate paths, missing sections, and malformed statements are rejected.
Parent hierarchy areas are not added to child leaf areas.

For each local leaf-cell reference row, the per-instance area is Decimal
`row.total_area / row.count`, quantized to 12 decimal places. The printed
`Unit Area` is checked for agreement within 0.00001, but is not multiplied by
the leaf count: its six-digit rounding would accumulate error. Values remain
in the archived report's area units; no NAND2 or technology conversion is used.

Every leaf enters exactly one of these categories, in this precedence order:

- `policy`: any ancestor starts with `cxl_fcfs_sel`, `cxl_rr_sched`, or
  `cxl_fai_main_sched`, including arithmetic beneath that policy.
- `descriptor_storage`: under `cxl_desc_fifo`, with `desc_mem_q_reg` in the
  leaf instance name.
- `timestamp_storage`: under `cxl_desc_fifo`, with `gen_ts_ts_mem_q_reg` in
  the leaf instance name.
- `common`: other FIFO logic, `cxl_out_hold`, `switch_top_DW` arithmetic,
  and direct top-level cells. Top-level arrival-counter cells are common.
- `unresolved`: any remaining ownership, retained explicitly with examples.

Storage-bit checks enforce N x 16 x 105 descriptor registers and N x 16 x 32
timestamp registers for FCFS/Main. RR has zero timestamp registers and zero
top-level arrival-counter registers. These are mapped-name attribution rules,
not a claim that all combinational logic supporting storage belongs to its
storage category.

Category areas sum exactly to allocated leaf area. The signed residual is
`leaf_area - total_cell_area`; subtracting it from the category sum gives
the archived summary exactly. The reconciliation tolerance is the larger of
0.00001 and the sum of half-last-printed-digit bounds for every
occurrence-weighted leaf reference row total and the summary total, plus
0.5e-12 per allocated leaf. The bound assumes the report fields are rounded
to their printed precision. Each case records both bounds and its residual;
residuals are not assigned to an ownership category.

The first full continuation run stopped at N16 RR with residual
-0.000010013969, just outside the original fixed 0.00001 tolerance. It is
preserved as failed evidence. The final precision-derived N16 RR bound is
0.000201541402; the largest bound across the nine cases is 0.000458058349.
The largest observed absolute residual is 0.000010013969.

## Measured attribution

Areas in this table are rounded to six decimals for display; JSON and leaf
ledgers retain twelve decimals. All unresolved counts and areas are zero.
The final column is archived `number_of_cells` minus expanded leaf count.

| Case | Leaves | Descriptor | Timestamp | Policy | Common | Count delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N4 FCFS | 27,156 | 44404.041137 | 13532.660156 | 1131.957370 | 44901.399654 | +46 |
| N4 RR | 20,660 | 44404.041137 | 0.000000 | 263.039041 | 34380.092136 | +11 |
| N4 Main | 29,344 | 44404.041139 | 13532.660157 | 7143.987889 | 45009.156711 | +90 |
| N8 FCFS | 54,674 | 88808.082274 | 27065.320312 | 2767.628141 | 89796.699875 | +28 |
| N8 RR | 41,413 | 88808.082273 | 0.000000 | 512.862592 | 68939.864092 | +19 |
| N8 Main | 58,499 | 88808.082277 | 27065.320313 | 13596.449942 | 89874.722079 | +102 |
| N16 FCFS | 109,343 | 177616.164547 | 54130.640624 | 6038.461402 | 179100.868638 | +50 |
| N16 RR | 82,803 | 177616.164547 | 0.000000 | 1268.686851 | 137729.274919 | +35 |
| N16 Main | 116,698 | 177616.164555 | 54130.640626 | 26673.175380 | 179202.526231 | +188 |

### Hierarchical count definition follow-up

The follow-up computes nonleaf instance occurrences from the existing recursive
expansion as `sum(module_occurrences.values()) - 1`, excluding the root design.
It counts occurrences, not unique module definitions. An independent recursive
walk that adds one for each hierarchical instance and visits its children
confirmed every result; occurrence-weighted local hierarchical instance counts
also agree. Combinational-plus-sequential counts equal leaves in all nine.

| Case | Reported cells | Leaves | Nonleaf occurrences | Reported minus leaves | Reported minus leaves and nonleaves |
| --- | ---: | ---: | ---: | ---: | ---: |
| N4 FCFS | 27,202 | 27,156 | 10 | 46 | 36 |
| N4 RR | 20,671 | 20,660 | 6 | 11 | 5 |
| N4 Main | 29,434 | 29,344 | 27 | 90 | 63 |
| N8 FCFS | 54,702 | 54,674 | 18 | 28 | 10 |
| N8 RR | 41,432 | 41,413 | 10 | 19 | 9 |
| N8 Main | 58,601 | 58,499 | 47 | 102 | 55 |
| N16 FCFS | 109,393 | 109,343 | 34 | 50 | 16 |
| N16 RR | 82,838 | 82,803 | 18 | 35 | 17 |
| N16 Main | 116,886 | 116,698 | 87 | 188 | 101 |

Thus hierarchy alone does not exactly explain any of the nine archived
counts. This is an observed mismatch against two tested definitions, not
proof that the original EDA field is erroneous. Its remaining semantics are
unresolved. The corrected script recognizes `CONSISTENT` for a leaf-only
match, `CONSISTENT_INCLUDING_HIERARCHY` for a leaf-plus-nonleaf match, and
`UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH` otherwise. Only the last adds a count
warning. No hierarchy area is added to the leaf area attribution.

## Executed checks and artifacts

Commands executed from the repository root:

```powershell
python -m unittest discover -s scripts -p test_revision_area_audit.py -v
python scripts/revision_area_audit.py --output artifacts/implementation/revision-area/continuation-20261024-hierarchy/results.json
```

The final unit suite has **18 passing tests**, zero failures/errors/skips.
It covers duplicate paths/category overlap, missing references and hierarchy
attributes, truncated reports and malformed netlists, recursive reuse and
cycles, checksum/manifest corruption, RR timestamp exclusion, all five
ownership categories, exact Decimal partition, deterministic totals, refusal
to overwrite evidence, repeated-module area/count accounting, area mismatch
rejection, and enforcement of the printed-precision rounding bound.
The added follow-up test covers exact leaf-only and hierarchy-inclusive counts
without count warnings, plus an unexplained remainder that still warns.
The reused-module test also checks nonleaf occurrence multiplicity.

An additional executed ledger check reopened all nine gzip CSVs, verified
their SHA-256 hashes, checked unique paths and allowed categories, and
recomputed each category's count and Decimal area. All 540,590 rows agree
with the JSON. It also checked each exact category/residual/summary identity
and each residual against its recorded tolerance. The fresh audit's areas,
attribution, input provenance, and all nine inventory hashes exactly match the
retained rounded audit. All prior output-file hashes still verify.

Final ignored evidence directory:
`artifacts/implementation/revision-area/continuation-20261024-hierarchy/`

- `results.json`: nine-case summary, input paths and hashes, archive source
  revisions, storage checks, cell-type category breakdowns, residuals/warnings.
- `results-leaves/*-leaves.csv.gz`: nine deterministic compressed per-leaf
  inventories with netlist/report line numbers, local row inputs, ownership
  rationale, and allocated areas.
- `tests.txt`: captured final 18-test execution.
- `verification.json`: independent recursive counts, ledger verification,
  preservation checks against the rounded audit, and test exit status.
- `OUTPUT_SHA256SUMS`: hashes of all final output files and both audit/test
  sources (`repo:` entries are relative to the repository root).

Each input archive's entire `RESULT_SHA256SUMS` is checked, including the
mandatory netlist/reference/summary entries. The manifest parameters must
match `parameters.json` and its recorded hash. The JSON additionally archives
SHA-256 values for all six audit inputs per case. This verifies consistency
with the locally archived checksum records, not independent authenticity of
the original EDA run.

Final hierarchy-aware audit hashes:

```text
results.json:
f16bb5cf57351f23eccc9d0f2a93a63492db72bf04309064e5d3bdfbed61b183
scripts/revision_area_audit.py:
566283bc786c635a66f5ce8dd0586249c0040f7c3fd399650f032ebb151c0f50
scripts/test_revision_area_audit.py:
31ad6fd77441ac52dc44a60e0dcdf9cb090fea48fa46779ba76b148e8daba984
```

Earlier outputs were retained without overwrite:
`continuation-20261024-rounded/` retains the original 17-test audit and its
superseded count-field classification; its results JSON SHA-256 remains
`8d6e54862a3a258470eabbc5fe333e76e1fe688eafc13983b5efca1cab861d0c`.
Its source hashes describe the earlier source version.
`continuation-probe-20261024/` contains the initial N4 FCFS probe;
`continuation-20261024/` contains partial ledgers from the failed fixed-tolerance
run and no completed results JSON. The prior author's timestamped outputs
were also left intact. The CLI default creates a fresh timestamp directory;
explicit existing JSON outputs or inventory directories are refused.

## Changes from the handed-off partial implementation

- Simplified source-line calculation without changing its correct result;
  corrected the test's mistaken line-10 expectation to line 9.
- Removed the blanket rejection of repeated module occurrences and weighted
  reference leaf counts by occurrence, exposing the expanded reference count.
- Replaced only the aggregate leaf/summary fixed tolerance with the derived
  printed/allocation rounding bound, preserving exact residual reporting.
- Added four focused tests: reused-module full audit, all ownership categories,
  area mismatch rejection, and precision-bound acceptance/rejection.
- Added this report and fresh ignored evidence. Only the two owned Python
  files and this owned document were edited.
- Follow-up: count nonleaf occurrences excluding the root, recognize either
  count definition, record both count residuals, and replace the blanket
  inconsistency label and summary key with unexplained-mismatch terminology.
  Added one three-case test and extended two existing tests.

No SSH, synthesis/STA rerun, RTL, manuscript, shared report, baseline, or
performance edits were performed. This audit does not establish physical
area, timing, power, or correctness of the scheduler logic.
