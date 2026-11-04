# Six baseline source bridges

Status: **BLOCKED before remote preflight; 0/6 new proofs executed.**

Latest follow-up: approved archived trust was recovered exactly. Host verification
now succeeds; the remaining blocker is SSH authentication (`Permission denied`,
outer exit255), before remote shell startup. Initial missing-trust wording below
is history.

## Final attempt accounting

Exactly **three SSH preflight transport attempts** occurred. Every attempt
returned numeric outer exit255 with empty stdout before remote shell startup.
There were **zero remote preflight executions, zero tool/license probes, zero
Formality processes, zero proof cases started, zero report downloads, and zero
new accepted bridges (0/6)**. Offline unit tests, `ssh -G`, `ssh-keygen -F`,
local file reads and Bash syntax checks are not connection or proof attempts.

| Run ID suffix | Start UTC on 2026-10-23 | End UTC | Outer exit | Stage and cause |
| --- | --- | --- | ---: | --- |
| 093504Z | 09:35:06.390499 | 09:35:06.611283 | 255 | Original temporary pinned trust file absent |
| 094145Z | 09:41:47.157257 | 09:41:50.470498 | 255 | Recovered task-local key; runner option path incorrectly split at workspace space |
| 094351Z | 09:43:53.223734 | 09:43:53.555409 | 255 | Correct task-local pin; authentication denied |

Each full run ID is `revision-bridges-20261023T<suffix>`. Raw logs, exact
requests, scripts, per-attempt runner hashes and numeric exits remain in separate
immutable attempt directories. Later recovery diagnostics do not replace those
original logs or their outcomes.

The final sanitized SSH error is
**`Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password)`**.
This proves that the corrected strict-trust attempt reached authentication and
the available noninteractive authentication did not succeed. It does not prove
a wrong password, account lockout, key revocation, or socket expiration; none was
diagnosed or guessed. `BatchMode=yes` is preserved, so this runner cannot prompt
for a password. No authentication retry occurred after this denial.

The actionable prerequisite is a valid authenticated session or accepted
noninteractive credential using the owner's existing access workflow, preserving
the approved destination, account, strict pin and private/global configuration.
No new key approval is needed. After authentication is restored, the same runner
must still execute current input/hash/tool/license preflight and all six proofs.
Tool exit and wrapper exit for the six cases are **NOT_RUN**, never zero by default.

## Authorized trust recovery follow-up

Read-only inspection found the exact approved `ssh-ed25519` key in
`.setup-logs/FastX-NN/known_hosts`. The computed fingerprint equals the
private configuration's `USER_CONFIRMED_AND_PINNED` fingerprint:

`SHA256:REDACTED`

The entry matches the configured destination. Exact decoded public-key bytes
also match existing Windows `known_hosts` and `known_hosts.old`. WSL home trust
files and the old temporary pinned file are absent. No network key scan or
new trust discovery was used.

The archived and task-local trust files have identical SHA256:

`c6b15609c872e1bcb46dc77245fe5e6971bfef96cb19d6faa6ef92a01af2aee7`

The runner now checks approval state, exact fingerprint, destination association,
algorithm and uniqueness, then copies only that approved entry into fresh own
logs. Strict checking and all reviewed transport options remain enabled; only
the invocation-local trust path changes. Global/private config remains untouched.

Attempt `revision-bridges-20261023T094145Z` exposed a runner quoting bug:
OpenSSH's `-o` config parser split the workspace path containing a space.
That attempt failed host verification before remote shell startup. The fixed
runner quotes the path inside the option value. Offline `ssh -G` confirms the
exact effective path and strict checking; offline `ssh-keygen -F` finds the entry.
An initial offline interpretation incorrectly tokenized rendered `ssh -G` output;
corrected validation compares its entire effective value. These checks made no
network connections.

Corrected attempt `revision-bridges-20261023T094351Z` passes the trust stage,
then fails with `Permission denied`, outer exit255. No host-key error is present;
stdout is empty, and neither remote shell nor EDA starts. No further retry or
credential/socket/config change was attempted.

Latest ignored evidence:
`.setup-logs/implementation/revision-20261023/bridges/revision-bridges-20261023T094351Z/`
contains `trust-recovery.json`, `trust-comparison-and-auth-blocker.json`,
task-local `known_hosts`, raw private transport logs, numeric exits, exact source
provenance, unchanged-local-reference evidence and eight passing offline tests.
The parent must restore authentication through the approved access workflow.
Recovered evidence does not require new host-key approval.

Owner authorized formal-tooling implementation and execution on 2026-10-23.
This work changes no RTL, models, existing reports, paper, shared status, or accepted
evidence. No commit was made. The runner uses the existing pinned connection and
read-only SSH executor; it does not alter configuration or accept new host keys.

## Exact source scope

Current reference bytes match supplementary source
`c8e7ea8c0e4530572b3abf5b14ea9958e24f1789`: seven RTL files and
`rtl/filelist_switch.f`. Each is compared with both the supplementary SHA256
manifest and the exact Git blob before any connection. Local reference hashes
were independently recomputed after the failed connection and remain identical.

Mapped source is `759f86b24f13ed5984c19034eeeea2ca43b0e971`.
The six original primary-v2 netlists, manifests, and run configurations are
locally hash-checked against `docs/ppa/formality-20261021.json`.
Original RTL Git blobs also reconcile with that formal manifest.

| Case | Original result directory under `artifacts/fastx/` | Required passing points | New proof |
| --- | --- | ---: | --- |
| FCFS N4 | primary-20261021-v2-fcfs-n4 | 8967 | NOT_RUN |
| RR10 N4 | primary-20261021-v2-rr-n4 | 6893 | NOT_RUN |
| FCFS N8 | primary-20261021-v2-fcfs-n8 | 17793 | NOT_RUN |
| RR10 N8 | primary-20261021-v2-rr-n8 | 13672 | NOT_RUN |
| FCFS N16 | primary-20261021-v2-fcfs-n16 | 35443 | NOT_RUN |
| RR10 N16 | primary-20261021-v2-rr-n16 | 27227 | NOT_RUN |

Implementation file in each directory: `output/switch_top.syn.v`.
Common parameters: D16, M1, descriptor105, RR quantum10, W5,000,000.
Frozen profile canonical SHA256:
`6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`.
Original library SHA256:
`844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`.
No library, license, PDK, or executable is uploaded or downloaded.

## Implemented execution and audit

`scripts/run_revision_bridges.py` creates fresh timestamped local logs, remote
scratch, and own report-output directories. It reuses SSH options from the
reviewed `.setup-logs/FastX-NN/remote.py` and invokes its read-only
`ssh_exec.py`. It does not invoke the helpers that write into their old log paths.

The runner derives accepted remote case locations from retained source manifests,
checks their containment within the configured work root, and pins the configured
library to the original accepted library. Private connection details occur only
in ignored execution artifacts.

Preflight would upload only current own RTL and new tooling to fresh scratch,
check every accepted payload hash, mapped netlist/SVF/manifest hash, current
reference hash, original library hash, and generated checker/Tcl hash. It would
load the existing configured Synopsys module, locate Formality, and run a bounded
license/library-read smoke check. This preflight did not run remotely.

Each subsequent proof uses `/usr/bin/timeout 15m fm_shell`, the accepted SVF,
strict audited setup, current reference RTL, and the untouched original netlist.
Before/after hashes are independently computed, not copied. A shell trap preserves
case reports and numeric wrapper exits even on failure. The added post-match
`report_undriven_nets` is mandatory.

The audit requires numeric local outer, remote wrapper, and tool exits of zero;
`verify_return=1`; exact expected passing points and output counts; full register
reconciliation including separately reported constant registers; no failing,
aborted, unverified, or unmatched points; no user constants, exclusions, active
black boxes, multiply-driven nets, or user setup overrides; strict undriven
settings and zero post-match undriven nets; SVF guidance; and no tool errors.
It records each report SHA256 and compares all transferred report hashes with
hashes computed remotely. Download extraction rejects traversal, links/devices,
duplicate files, unexpected types, and oversized archives.

## Actual attempt and concrete blocker

Run ID: `revision-bridges-20261023T093504Z`.

One pinned SSH attempt ran from **2026-10-23T09:35:06.390499Z** to
**2026-10-23T09:35:06.611283Z**, numeric outer exit **255**. Strict host-key
verification failed because the selected WSL known-hosts store lacked a trusted
key for the destination. There was no changed-host-key warning. Stdout was empty;
the remote preflight shell and EDA jobs did not start. No retry, alternate host,
socket guess, host-key acceptance, or configuration repair was attempted.

At this initial checkpoint the missing trust was unresolved. The later
owner-authorized recovery above supersedes that trust blocker. Authentication,
current license availability, and remote input existence/hashes remain unverified.

Ignored evidence root:
`.setup-logs/implementation/revision-20261023/bridges/revision-bridges-20261023T093504Z/`

- `provenance.json`: exact reference/input hashes, original source pair, generated
  Tcl hash, executed runner hash, and orchestration Git HEAD.
- `preflight.sh`, `preflight.stdin`, `preflight.request.json`: exact attempted
  preflight and transport request; private, ignored, do not paste into reports.
- `preflight.stdout.log`, `preflight.stderr.log`, `preflight.exit.json`: raw
  transport evidence, timestamps, and numeric exit.
- `result.json`: blocked execution; no case results.
- `connection-failure.json`: sanitized diagnosis and zero retry/job counts.
- `local-reference-after.json`: independently recomputed local source hashes.
- `shell-syntax-checks.json`: real WSL Bash syntax-check exits for preflight
  and all six generated case shells.

There is no new accepted proof artifact directory and no PASS claim.

## Offline validation and repeat command

Run from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s scripts -p test_revision_bridges.py -v
# Only after authentication is restored through the existing access workflow:
python -B scripts/run_revision_bridges.py --execute
```

The offline suite checks all six original report schemas, accepted-report
accounting, rejected report corruptions, unsafe archive paths/types, all six
generated case configurations, the timeout, and host-key failure classification.
Old proof fixtures validate the parser; they do not constitute current bridges.
Initial test development incorrectly assumed at least 30 setup rows; actual
Formality W-2024.09 reports contain 28. The final validator explicitly requires
all 28 named commands and zero values, and rejects a missing row or override.
The failed initial test is not a formal result.

An initial local Bash syntax command used incorrect shell escaping for the
workspace space and failed to locate the script. The corrected argument-list
invocation checked the preflight and all six shells successfully, exit0 each.
This was an offline command error with no remote contact.

The final runner includes post-attempt diagnostic and validation refinements.
Its final code is offline-tested; the preserved provenance hash identifies the
earlier runner bytes used for each connection attempt. All three attempts are
counted above; no remote attempt followed the final authentication denial.

## Provenance draft for the parent ledger

Codex implemented formal-only six-bridge tooling in the authorized new paths.
Actual local reference/Git/mapped-input checks completed; offline tests and seven
Bash syntax checks passed. Three pinned SSH preflight transports returned exit255:
missing original trust, a repaired trust-path quoting bug, then authentication
denial with the exact recovered approved pin. No remote shell or EDA ran.
Six bridge proofs,
remote hashes, current tool/license checks, and independent new-proof acceptance
remain NOT_RUN. Existing 14 accepted formal source/parameter pairs remain history.

## Owner-requested reconnection diagnosis: 2026-10-24

The owner requested another connection check. A fresh pinned SSH probe
(`ssh-diagnosis/20261023T184836Z`) established the server connection and
matched the approved host key, then exited255 at authentication.
The configured control socket is missing. Historical close receipts show that
the previous authenticated master was deliberately closed after completed work;
the local connection record also records that closed state. Current WSL has no
SSH key directory or SSH agent socket, and the Windows SSH agent is stopped.
The batch helper cannot prompt for password authentication (`BatchMode=yes`).
This is not evidence of a network outage or an invalid password.

An owner-terminal helper is prepared at the ignored path
`.setup-logs/implementation/revision-20261024/ssh-diagnosis/login.py`.
It restores only the already approved task-local host pin, requests interactive
authentication directly through SSH, and opens the configured master with an
eight-hour persistence limit. No password enters the helper, command arguments
or log files. After a successful batch probe it starts the existing six-bridge
runner. Argument/trust/input-immutability selfchecks and all eight bridge unit
tests passed; interactive login and the six remote proofs remain unrun.

### Authentication restored; proofs executing

The owner completed interactive authentication at2026-10-23T18:59:49Z
(2026-10-24 Taipei). Both login and the authenticated batch probe exited0.
Run `revision-bridges-20261023T185951Z` passed remote preflight and started
the six sequential proofs. FCFS N4, RR N4 and FCFS N8 wrapper exits are0
at this checkpoint; remaining execution and the independent downloaded-report
audit are pending. This supersedes the authentication blocker above without
reclassifying the earlier failed attempts.

### Six proofs completed and parent-rechecked

Run `revision-bridges-20261023T185951Z` completed PASS with six tool/wrapper
exits0 and fetch exit0. Parent reran the strict validator on every downloaded
case and independently matched every downloaded report hash to the remote
hash manifest. No failing, aborted, unverified or unmatched points, active
blackboxes, user constants, user exclusions or post-match undriven nets were
accepted. Each case separately accounts for one optimized constant register;
it is not a user-imposed constant or an omitted state bit.

| Case | Passing compare points | Compared registers | Accounted constant registers |
|---|---:|---:|---:|
| FCFS N4 | 8967 | 8855 | 1 |
| RR N4 | 6893 | 6781 | 1 |
| FCFS N8 | 17793 | 17676 | 1 |
| RR N8 | 13672 | 13555 | 1 |
| FCFS N16 | 35443 | 35317 | 1 |
| RR N16 | 27227 | 27101 | 1 |

Artifact: `artifacts/fastx/revision-bridges-20261023T185951Z/`.
These complete the six missing current-RTL/original-mapped-netlist source
bridges in the declared configurations. They do not replace workload
experiments, prove every RTL revision or parameter, or extend physical signoff.
