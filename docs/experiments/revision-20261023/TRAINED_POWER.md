# F12 matched trained HOG activity preparation

Updated: 2026-10-24 Asia/Taipei (2026-10-23 UTC). Source HEAD:
`99400ded42cc63c3b206bd5d13f51d36344b2689`, with working-tree source hashes.
Status: exporter, independent serialized-pin replay and per-case source archives
implemented; resumed bounded smoke matrix passed against stable shared sources.
Production W=5,000,000 exports, native gate replay, SAIF collection, and DC/PT power
have NOT RUN. Owner now reports restored SSH login; this task has not independently
invoked the remote tools. Native modes12/13 remain unsupported. No license,
tool availability, or power capability is inferred from historical results.

Only the two new Python scripts and this note are implementation deliverables.
Existing scripts, native testbench, RTL, manuscript, and shared reports are untouched.
Runtime evidence uses fresh ignored `artifacts/fastx/revision-trained-power-*` directories.

## Fixed experiment contract

FCFS, RR quantum10, Main; N4, D16, full105 descriptors, period25,000ps and three
reset edges before cycle0. Seeds509..513 are exploration seeds. Planned power
replication uses509,510,511, consistent with `scripts/revision_matrix.py`;
512,513 remain additional exploration, not confirmation.

| Payload | Real training | Further premeasurement replay | Measured interval, half-open |
| --- | --- | --- | --- |
| A, mode12 | [0,10,000,000), two W5M windows | None | [10,000,000,10,100,000) |
| B, mode13 | [0,10,000,000), two W5M windows | A plus 1,024-cycle A guard | [10,101,024,10,203,424) |

Each payload starts from reset and replays every preceding edge. B reexecutes the
same training/A/guard prefix; it does not reset at the B cut or deposit classes,
FIFO state, timestamps, quota, or producer state. Pending work crosses each cut.
No guard or training cycles belong in measured activity. There is no drain within
either export; outstanding accepted and generated-but-unaccepted work is reported.

Traffic is the existing `sim/experimental/revision_traffic.py` matched-power
configuration: heavy source0, one heavy request/cycle, always ready; sparse
Bernoulli1/128 in training/A; B has eight-request bursts at seeded offsets in each
1,024-cycle block. Source descriptor RNG streams and generation are exogenous.
This default reproduces `sim/performance/hog_sparse.py`; source-specific input
handshakes depend on policy and therefore need not match between policies.

Production Main must actually close at cycles4,999,999 and9,999,999. The exporter
requires the independently specified HOG class sequence
`[B_H,H,H,H] -> [L,H,H,H]`. The reused closing checker verifies widened integer
thresholds, closing-fire inclusion and B/S/index clear. No third production
closing occurs before either measurement ends.

## Implementation and evidence checks

`scripts/export_revision_power_vectors.py` reuses the existing deterministic gzip,
v2 eight-column row writer, accepted FCFS/RR/Main models, producer hold checker,
phase replay, closing checker, mapped-case inventory and canonical profile hash.
The v2 header is:

```text
43585032 MODE N TOTAL WARMUP MEASURED SEED POLICY PERIOD_PS RESET_EDGES
```

Rows are unchanged: decimal cycle index, then hexadecimal input valid, packed
input descriptors, sink ready, expected input ready, output valid, source, descriptor.

Every export is reread from gzip and checked with `ExperimentalSwitchModel`,
a separate scheduler policy implementation, and an independent deque ledger.
The audit regenerates the exogenous events/producer offers, checks all pin widths,
full-before-pop readiness, no bypass/bubbles, ordering/full105 integrity, input hold,
per-source accepted-minus-fired occupancy, generated conservation, phase totals,
and cut/end occupancy. The two models share accepted common control primitives and
classification helpers; this is not an entirely independent mathematical oracle.
It is not RTL or gate equivalence.
For Main, the independent audit also compares every closing's B/S totals,
threshold evidence and old/new classes against export metadata and checks B/S/index
at the measurement cut and end. `audit.json` retains the independently replayed
`main_closings`; real training is never replaced with a deposited trained state.

Metadata records exact commands, interpreter/platform, source revision, source
hash inventory, mapped netlist/SDC/run-config/manifest hashes, text/gzip hashes,
phase runtime, training closings, cut/end state and numeric exit. Audit records
each traffic phase's pin hash, cycle count and source acceptance/fire totals.
Sources and mapped inputs must agree before/after checks. Fresh output directories
are mandatory; failure evidence is retained in `failure.json`. A failed independent
audit never receives the completed status. No cell library, PDK or license is copied.

Each new case first writes `source-freeze.zip`, containing the exact inventoried
project source bytes (including both exporter and tests) and the four mapped
case inputs under `mapped/`. ZIP timestamps and entry order are deterministic.
Metadata binds the archive SHA256. Independent audit checks its hash, exact
inventory and every archived file hash, then still requires agreement with live
sources and mapped inputs. The archive preserves a recoverable snapshot; it does
not waive source-change rejection or prove equivalence to the old mapped netlist.
Old cases without archives remain historical evidence for the prior exporter;
this archive-requiring revision does not upgrade them or overwrite their outputs.

## Native replay integration still required

The existing `scripts/check_power_replay.py` allows only the old cold-seed and
boundary modes. `sim/power/tb_power.sv` has the same fixed mode allowlist.
Consequently the unchanged `scripts/run_power_pilot.sh` deliberately rejects F12
metadata before VCS. The new modes are not disguised as accepted old datasets.
This is an explicit integration prerequisite in addition to remote authentication.

An authorized native owner must add exact production guards for mode12/mode13,
N4, seeds509..513, the table's exact warmup/measured lengths, existing clock/reset
and policy guards, and W5M in the metadata checker. W256 sensitivity headers must
remain refused by the production path. Preserve measurement-only toggle collection,
all warmup pin checks, and exact per-phase/source result totals.
No native testbench or existing checker was edited in this task.

The new script accepts actual future `--gate-result`, optional `--saif` and
`--pt-reports` with `--audit`. Gate totals use the existing v2 result format.
SAIF checks require measured-only duration, tb/dut scope, known clock time and
2M or2M-1 clock transitions. PT report checking reuses the existing `check_pt`;
annotation semantics, all FF clocks, units, table-range qualifications and method
acceptance still require review. A totals-only check never claims power completion.
The tests' generated gate/SAIF text is synthetic checker-test input only.

Use `prepare_ppa_run.py` only through its existing approved fresh-case/profile
workflow if a new mapped case is later required; this exporter does no synthesis.
It binds existing accepted primary-v2 cases at759f86b and hashes current model/RTL
references separately. The missing current-to-old FCFS/RR formal bridge proofs
remain unproven; exporting vectors does not close that gap.

## Resumed local validation, 2026-10-24 Asia/Taipei

Final bounded ignored evidence:
`artifacts/fastx/revision-trained-power-handoff-20261023T172600Z/`.
The isolated standard-library-only interpreter is `venv/Scripts/python.exe`
inside the earlier `revision-trained-power-resume-20261023T171520Z` directory.
That earlier run passed its checks, but preceded the final addition of the
transitively imported `scripts/revision_matrix.py` to the source inventory.
The intermediate `revision-trained-power-complete-20261023T172100Z` matrix also
passed before the final independent closing-statistics checks were added.
`commands.json` records exact commands, PIDs, UTC
start/end times, elapsed seconds and numeric exits; each command has separate
stdout/stderr logs. `source-inventory.json` records the source freeze.

- All 14 unit tests passed, exit0. The original eleven checks are retained;
  three new checks exercise exact source/mapped archive bytes, deterministic archives,
  archive corruption, no overwrite and source change during freezing with retained
  failure evidence and no completed metadata/audit, plus training closing-count
  and cut/end window-statistics mutations.
- Six sequential seed509 W256 sensitivity exports passed, exit0: FCFS/RR/Main,
  A/B, each with64 measured cycles. A has576 rows; B has101,600 rows, including
  the full100,000-cycle A replay and1,024-cycle guard. All six independently audit
  their serialized pins and source archives.
- `prefix-comparison.json` verifies each policy's576 A rows exactly equal the
  beginning of its B replay, excluding the intentionally different header.
  Exogenous trace hashes match across all three policies separately for each arm.
- Three further sequential full-B W256 sensitivity exports passed, exit0, at
  203,936 rows per policy. Each replays512 training,100,000 A,1,024 guard and
  all102,400 B cycles. All100 burst blocks execute; each sparse source accepts
  800 B requests. Full-B traces match across policies, A prefixes remain exact,
  and the source inventory agrees before/after the run. Evidence is in
  `full-b-commands.json`, `full-b-summary.json`, `*-B-full/` and their logs.
  Observed wall times including independent audits were approximately19s FCFS,
  19s RR and22s Main; these do not establish W5M resource measurements.
- `production-commands.json` contains18 exact W5M commands for policies
  FCFS/RR/Main, seeds509/510/511 and armsA/B, all `PREPARED_NOT_RUN`.
  Unit checks cover exact plans for all five exploration seeds509..513.

The current traffic source hash is
`243d301f96346b72677e6438eedea66a954a2d44dc83b818783a0cfec5ebf961`,
matching the source seen after the historical interrupted run. The resumed matrix
confirmed source stability before/after all six cases. Every completed case has
`metadata.json`, `audit.json`, `source-freeze.zip` and `vectors.txt.gz`.
These are model/pin checks, not RTL, gate replay, SAIF or power acceptance.

Local W5M export appears feasible from the bounded sequential timings and streamed
gzip output, but production runtime, peak memory and disk use remain unmeasured.
No production process was launched, so there is no production PID or log to report.
Parent review requires Planck to confirm release of shared `revision_traffic.py`
before a fresh production source freeze. The archives above are sensitivity-run
snapshots, not an approved production freeze. Then the parent's explicit one-worker
resource approval is required before launching one seed509 exploration case.
Parent reports possible allocation of three performance plus two native DAC jobs;
process snapshots alone do not reserve a slot. The prepared18-case list is not
launch authorization. Parent reports full baseline source-complete PASS
`20261023T171608Z_276`; this task does not independently accept that baseline.
No native mode allowlist or SSH authentication repair was attempted.

## Current source and native preparation review

Read-only inspection at UTC2026-10-23 19:05 (October24 Asia/Taipei) found all18
prepared command plans still satisfy the fixed contract, their recorded interpreter
exists and their output paths remain unused. The commands are reusable templates,
not current production evidence. HEAD remains99400de.

The traffic source now hashes to
`750b01dd50494b53f76c13b7dd601d4d2f8301ac3779b63ccdbfc2dc3f37ffbb`.
The performance writer's
`.setup-logs/implementation/revision-20261023/performance/trainingfix-freeze-handoff.json`
explicitly invalidates the older power preparation binding. The change adjusts
`Metrics.guard`'s training-boundary assertion; `Traffic` generation is unchanged.
Current files match all39 core and53 DAC frozen-source entries exactly. Source
agreement and this release receipt permit preparation against those bytes, but
do not constitute parent GO for a power export.

Owner reports restored SSH login and six active formal bridges. This task did not
invoke SSH or infer bridge completion, VCS/PT readiness or power acceptance.
The prior `REMOTE_AUTH` metadata blocker was removed; the native allowlist remains
blocked. The exporter still performs no network or EDA operation.

Native read-only inspection confirms Python `check_mode` only accepts supplementary
modes1/2 and explicitly allowed local fixture9; the gate testbench likewise has no
mode12/13 case. `run_power_pilot.sh` rejects trained metadata before VCS through
`check_payload_mode`, and the final checker also needs the schema extension.
Exact required guards are:

| Mode | N | W | Seeds | Warmup | Measured | Total | Measured duration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12/A | 4 | 5000000 | 509..513 | 10000000 | 100000 | 10100000 | 2500000ns |
| 13/B | 4 | 5000000 | 509..513 | 10101024 | 102400 | 10203424 | 2560000ns |

Both retain the existing policy/clock/reset/FIFO/descriptor guards. Production
must reject W256 sensitivity metadata. Training still means actual10000000
replayed edges, and toggle collection covers only the measured cut.

Minimal proposed native assignment: `scripts/check_power_replay.py`,
`sim/power/tb_power.sv` and bounded extension tests in
`scripts/test_power_extension.py`. All are outside both frozen source sets.
The shell runner already imports the common guard and uses generic v2 totals;
no shell change is currently justified. Keep a separate trained-mode contract
branch/table: expanding `SUPPLEMENTARY_MODES` would also expose new choices in
the old exporter, whose non-cold traffic path is not the matched HOG generator.
No shared power file or testbench has been assigned or edited by this task.

Native Claude Opus5.5/medium was invoked for a read-only scope review, restricted
to Read/Grep/Glob with MCP disabled. Prompt, command, stream, stderr and source
inventory are under
`.setup-logs/implementation/revision-20261024/trained-power-review-20261023T190500Z/`.
The exporter14-test suite passed again against the new traffic bytes; its log is
`exporter-units.log` there. This includes small temporary W256 fixtures only.

The previous full-B projection remains approximately0.67..0.70GiB plaintext or
194..197MiB gzip per production case, plus about0.4..0.5MiB source archive;
allow250MiB gzip or1GiB including plaintext per case. Eighteen sequential exports
project to about3.43GiB gzip and5hours; neither is an actual production measurement.
No W5M export has launched. Parent reserves at most one future local slot and must
give GO before a fresh source-bound seed509 exploration export.

## Historical interrupted validation

Durable final evidence:
`artifacts/fastx/revision-trained-power-final-20261023T102218Z/`.
`commands.json` records command arrays, UTC start/end times and numeric exits.
The earlier `revision-trained-power-smoke-20261023T102035Z` directory is retained
as preliminary evidence; source hashes from it predate the final checker additions.

The final run attempted:

- Eleven standard-library tests, including pin mutations, truncated/extra rows,
  phase-counter tampering, gzip/source-hash corruption, fresh-output rejection,
  deterministic gzip, invalid configurations and existing-runner refusal.
- Six sequential W256 sensitivity exports, seed509: each policy, each arm.
  Short measured intervals are64 cycles. A replays512 training cycles, for576 rows.
  B replays512 training +100,000 A +1,024 guard cycles, for101,600 rows.
  Small-window Main classification continues during A/guard, so these are not
  production-trained state or power evidence.
- Each export's own independent serialized replay and hash checks. Five exports
  exited0: FCFS A/B, RR A/B, Main A. Main B exited1 at the final source check.
- `production-commands.json`: thirty exact W5M command arrays (five seeds,
  three policies, two arms), all PREPARED_NOT_RUN. Eighteen correspond to the
  planned three-seed power subset.

All eleven tests exited0. Five export commands exited0 and one exited1.
During Main B's independent replay, `sim/experimental/revision_traffic.py` changed:

```text
before 6b11899ccace079e052bd4b1aa6276d009ec54b4e8045aa22c8d6d482371125e
after  243d301f96346b72677e6438eedea66a954a2d44dc83b818783a0cfec5ebf961
```

The failed case retains its complete vectors, pending-status metadata and
`failure.json`; it has no completed `audit.json` or success exit. Earlier successful
exports describe the older source snapshot and will fail a new audit against the
changed working tree. They must not be promoted as evidence for the new snapshot.
The postmatrix prefix comparison was not reached. No dependent rerun was launched.
A coordinated stable traffic snapshot is required before rerunning the smoke
matrix and taking a production slot. No shared dependency was edited here.

Per-case metadata and completed audits hold exact hashes and phase counts.
There is no actual gate replay, SAIF or PT report in these smoke directories.

## Production commands and resource constraint

Run from the repository root with bytecode disabled. A single example:

```powershell
python -B scripts/export_revision_power_vectors.py --policy fai-main --seed 509 --arm A --plan
python -B scripts/export_revision_power_vectors.py --policy fai-main --seed 509 --arm A --out artifacts/fastx/revision-trained-power-UNIQUE-main-A-s509
python -B scripts/export_revision_power_vectors.py --audit artifacts/fastx/revision-trained-power-UNIQUE-main-A-s509
python -B scripts/test_revision_power_vectors.py
```

Omitting `--window` means actual W5M. Use a fresh, unique destination for every
case; select `--arm B` for its separately measured interval. There are no background
workers inside this exporter. Execute the prepared commands sequentially only when
the parent's global six-worker cap has room. The audit replays the complete
serialized run, so each production payload entails roughly10M exporter edges plus
roughly10M independent checker edges and a large pin file.

The observed workload had three production model workers and a native RTL launch
configured for up to three jobs. Their changing shared allocation did not establish
a reserved production slot. Only bounded sensitivity checks ran here; no additional
W5M process was launched. `workload-preflight.txt` preserves the local observed
process evidence. Parent coordination is required before taking a production slot;
no job was stopped, rescheduled or retried by this exporter.


## Superseding actual production checkpoint2026-10-24 13:33 Taipei

The historical W256/source-drift records above remain sensitivity/failed evidence.
They do not describe the current production capture snapshot. The released
trained-mode12/13 support preserves legacy modes and is bound to frozen33
parent dependencies; Main509A actual W5M capture and independent serialized
replay were accepted first. The parent later accepted six additional captures
from the original remaining17 producer, and now one from its interruption-safe
continuation: eight of18 local captures are accepted. Successful captures have
native exit0, independent audit, exact sources/mapped files, phase/conservation
checks, compressed/text hashes and source ZIPs. No complete10M model replay
was repeated merely to inspect completed artifacts.

Accepted local captures: FCFS509A/B, RR509A/B, Main509A/B, FCFS510A/B.
This makes four local A/B pairs, not four completed power matrix rows.
The current producer is serially generating RR510A and retains the ten remaining
identities. Interrupted FCFS510B bytes from the previous producer remain intact;
a fresh output produced the newly accepted capture. Unknown interruption
causes are not changed to a claimed scheduler/audit failure.

Current local receipts:
`.setup-logs/implementation/revision-20261024/power-parent-review-20261024T0904/continuation-1258/`.
The parent independently checked the new FCFS510B capture in
`parent-checkpoint-1332.json`. The immutable recovery plan is
`e50df4b0af36e43be7f3f295f34d74c151fe5b869d3fed572ca7485212c41ff9`.
No frozen simulation, power runtime or manuscript source was changed.

For the first actual remote Main509A gate/SAIF/PT case, fresh strict-pinned SSH
login and exact probe passed. The reviewed original payload was uploaded once
following read-only idle-target inspection. Remote preflight/upload exits are0;
the power stage is pending. Its accepted executor explicitly requires measured-
window SAIF duration/scope, gate replay totals, source stability and PT reports.
An exit0 alone does not grant semantic power acceptance: clock pin coverage,
annotation-source tables, units and table-range diagnostics must also be reviewed.
Until that review, all nine matched power matrix rows remain unaccepted.
Existing cold/boundary power and pre-layout PPA retain their original scope.


### 2026-10-24 13:53 first matched trained power arm semantically adopted

Independent Sol/high review adopted only Main509A trained pre-layout power with
no blocking issues. Parent independently compared the56 scoped always-X SAIF
paths against the hash-pinned prior linked-PT report: all have zero top ports,
leaf connections and nonoutput hierarchy pins. The34 deficient leaf cells match
32 literal-zero D pins and two literal-one SETB pins, with68 actual propagated-
constant disabled arcs. No new simulation or proprietary library query was
needed for these already-proven disconnected identities. This does not assert
that all SAIF records are known or all leaf pins annotated.

Reported power is3.466mW (switching0.01918mW, internal1.331mW,
leakage2.116mW; rounded printed quantities). Scope remains zero-delay/no-SDF,
ideal clock, pre-layout TT25ns; no physical signoff or cross-policy benefit.
Independent evidence is in power-sol/remote-preparation/continuation-1258/
semantic-main509a/semantic-review.json. Parent bound the exact review, prepared
payload, all28 returned hashes and command transcript in
power-parent-review-20261024T0904/continuation-1258/remote-matrix/
first-main509a-semantic.json. This one arm contributes zero completed A/B power
matrix rows. The remaining17 adapter still requires its own final reviewed
release before launch, and each returned case needs its individual review.


### 2026-10-25 07:33 Taipei - strict index201/498; five power pairs

Parent accepted only the four exact standard seed510 release hashes in the
existing index allowlist. The indexer schema and semantic acceptance logic are
unchanged. Parent independently repeated41index+20analysis tests:61PASS, then
directly checked all10 actual case contracts and release/source hashes.
Strict snapshot power-index/seed510-implementation-20261025/
snapshot-20261024T233121Z/ reports201PASS,45declaredRUNNING,252NOT_RUN,
0FAIL,0UNRESOLVED of498. Five of nine matched A/B power rows are complete;
10of18 individual activity captures have adopted returned power evidence.
Main510 and all511 power pairs remain unaccepted. The producer inputs for
all18 captures were already accepted; this count concerns remote output review.

Parent receipt:parent-continuation-20261025T0728/index-acceptance.json.
Core/DAC confirmation inference is unchanged. No partial power-cohort CI or
cross-profile overall ranking. Depth45 remains unsealed; no raw result is
promoted merely because its cocotb step passed. Existing local/remote queues
continue without duplicate jobs. Manuscript remains read-only.
