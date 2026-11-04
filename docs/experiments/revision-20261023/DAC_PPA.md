# DAC2 matched N4 DC/PT and equivalence preparation

Status: OFFLINE PREPARATION ONLY. No DAC synthesis, STA, equivalence or power
result is claimed. Parent review of the source-bound payload and commands is
required before any remote execution. SSH network/host-key verification was
reported complete by the parent; interactive authentication is pending and the
old master was explicitly closed. This adapter never opens SSH or restores it.

## Minimal changes and existing flow inspection

Only three new files are needed: `scripts/prepare_revision_dac_ppa.py`, its
offline unit tests, and this document. The caller uses this adapter instead of
`scripts/prepare_ppa_run.py`. No shared helper, frozen 39/53-file closure, RTL,
manuscript, profile or shared report is edited.

The shared helper hardcodes switch_top/filelist/primary policy parameter names
and requires RTL to match HEAD. The native DAC sources are accepted by an
archived run but are currently untracked. The adapter records their actual Git
blob/HEAD status and requires byte equality to the accepted native archive via
the existing read-only `verify_native` gate. It does not claim committed RTL.
The accepted run is `revision-dac/20261023T174033Z_1699`.

DC and PT Tcl already consume top, source list, elaboration parameters, output
paths, structure expectations and profile settings through run_config.tcl.
They are copied without modification. The adapter uses the existing profile
loader, constraint renderer, shell renderer, payload allowlist and tar writer.
Small exact-match replacements adapt the generated config and shell's fixed
top check. Drift at an adaptation point fails preparation.

The actual prior formal bridge is
`artifacts/fastx/formality-current-main-bridge/reports/equiv.tcl`, also used by
`scripts/run_revision_bridges.py`. Its SHA256 is pinned to
`6f48a8fac946ff02e2394955e75bb2ecf8cbed5b3676c827f2c8c6200c46cdf5`.
The generated equiv.tcl changes only configuration/top/source locations and
adds the bridge's post-match undriven report. It retains SVF guidance,
auto_setup=false, verification of directly undriven outputs, and all
setup/constants/exclusion/match/verify/status diagnostics.

## Matched configuration and complete storage boundary

DAC2 only: dac_unit_top, N_SRC=4, DEPTH=16, FAI_W=5000000, HIGH_WEIGHT=2,
one output, full 105-bit descriptors, 32-bit arrival timestamps.
The filelist contains the package, common FIFO/hold/oldest-head selector,
cxl_dac_sched and native dac_unit_top; nothing is blackboxed or substituted.

| Declared RTL state | Bits |
| --- | ---: |
| 4 x 16 x 105 descriptor storage | 6720 |
| 4 x 16 x 32 timestamp storage | 2048 |
| FIFO read/write pointers and occupancy | 52 |
| Shared arrival counter | 32 |
| Hold valid/source/context (1+2+5) | 8 |
| Four two-bit classes | 8 |
| Window index | 23 |
| Four B counters and S counter | 115 |
| Four two-bit credits | 8 |
| Total declared state | 9014 |

The held descriptor remains in the selected FIFO head until fire; no separate
105-bit hold bank exists. Hold context includes refill and all four class
snapshot bits. Closing comparisons use the unchanged 32-bit arithmetic.
The inherited DC precompile lower bound is 8768 descriptor/timestamp bits.
The inventory is declared RTL state, not an expected optimized mapped register
count; DC/PT report registers and latches, and all policy state remains in the
elaborated native design and formal reference.

Use the frozen primary profile saed32-rvt-tt-25ns-forqa-cap075-v2:
canonical SHA256
`6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`.
SAED32 RVT TT 0.78V/25C library SHA256
`844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`.
Clock 25ns, setup/hold uncertainty 0.1/0.05ns, transition 0.1ns;
input/output min/max delay 0/2ns, input transition 0.1ns,
output load 2.656828fF; fixed ForQA/top; compile medium.
The same in-memory 0.75 cap tightening is restored before reporting/export;
PT reads the original DB. No timing exceptions or acceptance relaxation.

## Offline caller and later source-bound commands

Run from the repository root, supplying the existing private remote DB path:

```text
python -B scripts/prepare_revision_dac_ppa.py --library <existing-remote-db-path> --output .setup-logs/implementation/revision-20261023/dac-ppa/<fresh-id>
python -B -m unittest -v scripts/test_prepare_revision_dac_ppa.py
```

The output is exclusive and never overwritten. It contains the prepared
directory, payload.tar, preparation.json with the tar and manifest SHA256,
per-file SHA256SUMS, native evidence bindings, generator/input hashes, actual
Git state, configuration and declared-state inventory. No library is bundled.
The parent must bind the tar digest before uploading to a fresh remote root.
After review and restored authentication, the proposed remote caller is:

```text
cd <fresh-remote-root>/cxl-ppa-syn-dac2-n4 && bash ./run.sh
cd <fresh-remote-root>/cxl-ppa-syn-dac2-n4 && bash ./run-formal.sh
```

These are sequential separate invocations, not authorization to execute them.
The shared DC/PT shell checks tool exits, error diagnostics, library hash,
required reports, no timing exceptions, and unchanged netlist/SDC/SVF handoff.
Formality checks the payload and handoff hashes plus the original library hash,
records pre/post source/netlist/SDC/SVF/library hashes, actual exit/timeout, dates,
tool path, module list and the complete reports. No user constants,
compare-point exclusions or blackbox commands are introduced.

The parameterized Formality reference name follows the prior bridge convention:
`r:/WORK/dac_unit_top_N_SRC4_DEPTH16_FAI_W5000000_HIGH_WEIGHT2`.
Native Synopsys elaboration of this new name is not locally validated. A naming
or other tool incompatibility must fail the remote run, not be waived.

Both wrappers stop at COMMANDS_COMPLETED_REVIEW_REQUIRED. Formal review must
confirm successful verify/status, all 112 output bits, every nonconstant
register plus accounted constants, zero failing/aborted/unverified/unmatched
points, zero active blackboxes/post-match undriven nets, no user constants or
excluded points, safe setup and usable SVF guidance. Register/compare-point
totals must come from actual DAC reports, not copied Main/FCFS totals.
Review area reconciliation, setup/hold/electrical violations and STA coverage
from actual reports. This is pre-layout comparative area/STA; no extracted
parasitics, physical/multicorner signoff, workload power or PPA PASS is implied.

## Local validation record

The initial eight-test attempt had two failures caused by an incorrect 9114-bit
expected total in the test/document. The adapter's computed total was already
9014; the expected values were corrected. The first log is retained as
`.setup-logs/implementation/revision-20261023/dac-ppa/offline-tests-attempt1.log`.
The expanded suite checks the actual accepted native archive, immutable tar
contents and hashes, no overwrite, native-gate rejection, exact matched
constraint rendering, complete state inventory, real bridge adaptation,
template drift rejection, Tcl config evaluation and Bash syntax. It never
launches DC/PT/Formality/simulation or opens a network connection.
Final Windows run: 11 tests PASS, 1.073 seconds, unittest exit 0. Both generated
shells passed Git Bash `bash -n`; Tcl config evaluation and formal Tcl syntax
completeness passed in Tcl 8.6. These are offline checks, not Synopsys validation.
Final test results are recorded in `offline-tests-final.log` beside that log;
the concrete prepared payload is identified by its own preparation.json.
No EDA was launched.
