# RTL / mapped-netlist equivalence —2026-10-21

**ACCEPTED_FOR_THE_LISTED_SOURCE_AND_PARAMETER_PAIRS.** Actual FastX Formality W-2024.09
completed14 equivalence cases with strict setup, plus one intentionally failing negative control.
Codex independently executed and audited raw reports. No RTL, approved Spec, mapped netlist,
synthesis/STA profile or accepted power dataset was changed.

## Cases and source scope

Primary mapped/reference source is `759f86b24f13ed5984c19034eeeea2ca43b0e971`.
Supplementary/current RTL source is `c8e7ea8c0e4530572b3abf5b14ea9958e24f1789`.
All cases use N as listed, D16, full105, RR quantum10, FAI W5,000,000 and the approved M1
common `switch_top` boundary. Both source manifests and all seven read RTL files were
hash-checked against their exact Git revisions. Original SAED32 RVT TT DB SHA-256 remains
`844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`.

| Group | Policy | N | Passing compare points | Constant registers not compared |
| --- | --- | --- | --- | --- |
| Primary | FCFS | 4 | 8967 | 1 |
| Primary | RR | 4 | 6893 | 1 |
| Primary | Main | 4 | 9123 | 0 |
| Primary | FCFS | 8 | 17793 | 1 |
| Primary | RR | 8 | 13672 | 1 |
| Primary | Main | 8 | 18049 | 0 |
| Primary | FCFS | 16 | 35443 | 1 |
| Primary | RR | 16 | 27227 | 1 |
| Primary | Main | 16 | 35899 | 0 |
| Supplement | Main | 4 | 9123 | 0 |
| Supplement | Algorithm-2 | 4 | 9123 | 0 |
| Current Main RTL / original primary netlist | Main | 4 | 9123 | 0 |
| Current Main RTL / original primary netlist | Main | 8 | 18049 | 0 |
| Current Main RTL / original primary netlist | Main | 16 | 35899 | 0 |

Primary9 batch ran UTC04:29:33–04:50:57 on FastX-NN. Supplementary N4 pair ran
UTC04:38:40–04:40:31; current Main bridges N8/N16 ran UTC04:47:11–04:54:17 and N4 ran
UTC04:48:38–04:49:33. All14 `fm_shell` exits0 and `verify` returns1. Each has zero failing,
aborted, unverified or unmatched compare points, active black boxes, user constants and
don't-verify exclusions. Passing output ports are112/117/126 for N4/8/16; passing DFF points
plus explicitly un-compared constant registers reconcile to the full register counts.
The14 proofs are not14 distinct primary synthesis configurations.

## Setup and negative control

Reference SystemVerilog with `SYNTHESIS` defined is read and parameterized before loading
the implementation DB/netlist. The accepted DC `default.svf` guidance is retained, with
accepted/rejected guidance counts in the evidence. `synopsys_auto_setup=false`, default
`verification_set_undriven_signals="binary:X"`, and
`verification_verify_directly_undriven_output=true`. No manual constants, compare-point cuts,
state exclusions or implementation rewrites were applied to the accepted cases.

Separate post-match diagnostics for all primary9 report **0 undriven nets**. Initial setup
can show unconnected implementation leftovers before matching; the original pre-match
`report_undriven_nets` explicitly says it is not available yet. These stages are retained
separately. Supplement/bridge runs retain strict undriven-output verification but do not
have a separate post-match undriven-net report. Whole-library unused power-cell model warnings
and HDL signed-to-unsigned warnings remain in raw evidence; active-design black boxes are0.

An isolated copy of RR N4's mapped netlist was modified to invert only `o_out_valid`.
Formality correctly failed exactly that matched output point:6892 other points pass,
0 aborted/unverified. The outer expected-mismatch test exits0. Accepted netlists were untouched.

Retained setup failures: the first pilot loaded implementation DB before establishing the
reference and failed FM-236/reference setup; a CRLF shell failed before EDA startup. Neither
is accepted equivalence evidence. A lexical old/current Main N4 netlist equality check also
failed; semantic equivalence is established by the direct bridge proof instead. The parent
post-match audit initially expected a different literal zero-net message; it was corrected
to the actual `0 Undriven nets:` report, then all14 cases were re-audited.

## Evidence and limits

[Machine-readable audit](ppa/formality-20261021.json) includes exact source/report SHA-256,
counts, guidance, warnings and evidence directories. Raw own-design reports are in
`artifacts/fastx/formality-primary9/`, `formality-supplement-n4/`,
`formality-current-main-bridge/`, `formality-current-main-bridge-n4/`,
`formality-postmatch/` and `formality-negative1/`. Orchestration/audit logs are under
`.setup-logs/power-20261021/`. University DB, models, licenses and executables stay on FastX.

For a repeat using retained accepted own-design inputs on FastX, select a fresh scratch directory
and the exact archived Tcl for the group. Example primary case, with paths set in the shell:

```bash
module load Synopsys_x86-64/2024
# CXL_FM_ACCEPTED: accepted case directory with manifest, RTL, default.svf, run_config.tcl, output/.
# CXL_FM_TCL: retained formality-primary9/reports/equiv.tcl (or its remote original).
# CXL_FM_SCRATCH: a new directory; keep old reports intact.
export CXL_FM_ACCEPTED
mkdir "$CXL_FM_SCRATCH"
cd "$CXL_FM_SCRATCH"
mkdir reports
/usr/bin/timeout 15m fm_shell -f "$CXL_FM_TCL" > reports/fm.log 2>&1
```

The supplemental pair's archived Tcl permits policy3; bridge Tcl also requires
`CXL_FM_REFERENCE_ROOT` pointing at the accepted C8 RTL directory. Use its matching N4 or N8/16
script and the original mapped-case `CXL_FM_ACCEPTED`. Hash every input before/after, require
actual `verify_return=1` and no errors/failing/aborted/unverified/unmatched points, and inspect
setup, exclusions, constants, black boxes and guidance. A tool exit alone is insufficient.
These artifacts are ignored measurement evidence, so a fresh clone must restore them from the
accepted retained run; do not synthesize substitute evidence or copy proprietary assets.

This verifies RTL/netlist equivalence for the specified sources, parameters and library setup.
It does not prove the RTL against the English specification or cover APR, multiple corners,
analog behavior or physical power. Existing independent functional/reference tests remain
required and are not replaced by these proofs.
