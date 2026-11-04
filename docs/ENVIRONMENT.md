# Environment audit — 2026-10-13

Latest observed follow-up2026-10-21: the existing Windows/WSL toolchain is preserved, with a
small user-local Icarus12.0 addition for actual four-state replay guards; see [WSL supplement](WSL_SETUP.md).
Native Claude Code2.1.305/RTL Agent Team0.14.6 was verified. Native Opus5.5/medium exhausted weekly
quota after a guarded partial attempt; owner-authorized Sol/high completed the test tooling.
Actual FastX DC/PT/VCS/Formality W-2024.09 access and original SAED32 DB/model hashes are verified.
The revised primary9 area/STA matrix meets setup/hold/electrical gates; qualified cold power9
and [Formality14 source/parameter pairs](FORMAL_EQUIVALENCE_2026-10-21.md) are accepted.
New supplementary power tests are running separately; [STATUS](STATUS.md) records their actual
outcome. Later dated results supersede the initial audit and2026-10-20 closure state below.

The Synopsys module prepends its own `timeout` before the OS binary. For project orchestration,
use explicit `/usr/bin/timeout`; the vendor wrapper was observed leaving idle sleep watchdogs
after completed cases. Only positively identified completed task-owned watchdogs were cleaned;
no global shell/module setting, active EDA job or license helper was changed.

Current FastX follow-up2026-10-20: owner-authorized, strictly pinned SSH access, module `Synopsys_x86-64/2024`, actual DC/PT W-2024.09 license use and existing SAED32 RVT library read/hash are VERIFIED. All nine scheduler DC/PT measurements completed under one frozen25ns profile:8/9 setup MET,9/9 hold MET; Main N16 has32 setup violations, worst−0.870709ns. Electrical closure remains OPEN in all nine; power is NOT_RUN. See [actual results](PPA_RESULTS_2026-10-20.md), [execution history](PPA_EXECUTION_2026-10-20.md) and [STATUS](STATUS.md). Initial pending-access/no-RTL statements below are historical. The sole repository and local/WSL setup are preserved; no proprietary asset was copied locally.

## Current follow-up

The following tables preserve the **initial pre-install audit**, not current WSL availability. On 2026-10-13 the user explicitly selected and authorized the WSL Verilator/cocotb/minimal verification toolchain, plus FastX DC/PT/SAED32 for commercial runs. The selected WSL profile is now installed and checked: Verilator5.052, cocotb2.1.0, pytest9.1.1, Verible v0.0-4296-g0f262651 and required build/runtime tools. Real temporary-fixture lint and simulator/VPI integration passed. Evidence and reproduction are maintained in `docs/WSL_SETUP.md`; `docs/PROGRESS_TRACKER.md` separates this environment work from unstarted scheduler work. No second repository was created.

Audit date uses Asia/Taipei. This task ran locally on `WORKSTATION`, Microsoft Windows 11 Home, version `10.0.26300`, 64-bit. The interactive shell is PowerShell Core `7.6.5`. The starting workspace is `C:\Users\USER\Documents\Coding Space\CXL`; it was empty and had no Git repository. A new repository was initialized in `cxl-scheduler` on branch `main`, without replacing any existing repository.

No SSH or FastX session indicators were present. Windows, Git Bash, Ubuntu WSL2, and the university FastX host are separate environments. An installed local SSH client and an existing known-hosts file do not establish university access. No SSH host/account configuration was supplied or guessed.

## Initial observed local tools (before authorized WSL installation)

| Tool | Windows / Git Bash | Ubuntu WSL |
| --- | --- | --- |
| Git | 2.51.1.windows.1 | 2.43.0. |
| Python | Anaconda 3.13.5; pip 25.1; no `python3` command. | Python 3.12.3. |
| Node.js | 22.21.0. | 18.19.1. |
| npm | 11.13.0. | 9.2.0. |
| Claude Code | Native CLI 2.1.289. | Windows npm launcher responds as 2.1.128; WSL authentication/plugin state was not verified. |
| Bash | Git Bash 5.2.37 available at `C:\Program Files\Git\bin\bash.exe`; the Windows PATH `bash.exe` is the WSL launcher. | WSL2 Linux environment available. |
| C/C++ compiler | Strawberry MinGW-W64 GCC/G++ 13.2.0. | GCC/G++ 13.3.0. |
| make | No `make` command; `mingw32-make` present per Claude audit. | GNU Make 4.3. |
| pytest | 8.3.4. | Not found in audited Python. |
| numpy | 2.1.3 per Claude audit. | Not found in audited Python. |
| cocotb / cocotb-bus / hjson | Not found in audited Python. | Not found in audited Python. |
| Verilator / Icarus / VVP | Not found on audited PATH. | Not found on audited PATH. |
| lint | Neither Verible nor slang found. | Neither Verible nor slang found. |
| SystemC | Not detected. Git Bash `pkg-config` failed with missing Perl `Pod::Usage`, so that query is inconclusive. | Not detected. |
| CDC | No svlens, SpyGlass, VC CDC, or Questa CDC command found. | Same. |
| Synthesis/formal/waveforms | Yosys, SymbiYosys, GTKWave absent. | Same. |
| Optional infrastructure | jq, slang-server, sv2v, sv-renamer, sv_to_ipxact, Docker absent. | Same. |
| Commercial EDA | DC, PT, VCS, Xcelium, Questa, Genus, equivalence/debug tools absent from audited PATH. | Same. |
| SSH | Windows OpenSSH available. | Remote university connectivity not tested. |
| Tcl | Anaconda Tcl interpreter 8.6.14; used for mock template checks. | Not required for the audit. |

Presence checks establish executable visibility, not license availability, compatibility, or successful RTL builds. Searches were scoped to the available command paths and package environments; they do not prove software is absent everywhere on disk. WSL Ubuntu was started for the read-only audit; no packages or profiles were modified.

## Claude Code and RTL Agent Team

The official marketplace-add and plugin-install commands both exited successfully. `claude plugin list --json` confirmed `rtl-agent-team@rtl-agent-marketplace` version `0.14.6`, enabled, user scope. The marketplace source revision is `56c02875d77bd7b6d44fe9c5acd27d7d03f34b12`. Installation is user-local, outside the project. That initial plugin-install step installed no system-wide software; the later explicitly authorized WSL prerequisite packages are recorded in `docs/WSL_SETUP.md`. No Windows system-wide software was installed by either step.

The verified plugin installation belongs to the native Windows Claude Code user configuration. The older Claude launcher visible inside WSL is a separate invocation environment; its authentication and plugin discovery must be verified if WSL is selected for future development. Local version visibility alone does not establish shared plugin state.

Both initial skill attempts failed with `Failed to authenticate: OAuth session expired and could not be refreshed`, despite `claude auth status` reporting logged-in. The user completed reauthentication. A subsequent audit attempt was restricted by the calling process's tool permissions; it produced no audit data. The final read-only `/rtl-agent-team:rat-setup` invocation through Claude Code exited 0 with no tool permission denials and completed the actual audit. Its verdict is **NOT READY**, because required tools are missing. The audit wrote no `.setup-complete` marker or machine environment configuration, and deployed no global rules.

`/rtl-agent-team:rat-init-project` ran through Claude Code and executed the official initialization scripts. It deployed directories, coding/verification rules, directory guides, filelist/Makefile templates, and generic EDA wrappers. It preserved existing project files and intentionally omitted all sample RTL. The calling process exited 0, but Claude's automatic approval review denied writing the optional `.claude/rules/diagram-rules.md` as a sensitive configuration file because there was no interactive approval surface. The final result text was empty; exit 0 alone is not a claim of full skill completion. That optional write remains pending, with proposed contents in `docs/diagram-rules.pending.md`. `docs/STATUS.md` records this limitation. Raw local invocation logs are ignored under `.setup-logs/`.

## University environment and evidence boundary

The user reports a validated standalone registered-adder DC/PT smoke test on FastX with module `Synopsys_x86-64/2024`, Design Compiler/PrimeTime `W-2024.09`, and SAED32 RVT `saed32rvt_tt0p78v25c.db`. This is user-provided evidence. It has not been reproduced by this task and does not establish this repository's synthesis/STA success.

Remote synthesis/STA templates are prepared. **Remote access, module loading, tool license checkout, library path, and actual project runs remain pending.** No proprietary university asset was copied. Configure and verify access using `docs/FASTX.md`.

## Initial missing prerequisites and subsequent decisions

- RESOLVED by user: WSL is the local open-source verification environment. Native Windows/Anaconda is preserved.
- AUTHORIZED by user: compatible Verilator/cocotb and necessary lint/build tools, using an isolated project-dedicated WSL environment. See `docs/WSL_SETUP.md` for actual installation/verification status; no repeated installation approval is needed.
- Decide whether full plugin-pipeline SystemC/CDC requirements apply to the approved scheduler scope. Their installation remains deferred and needs explicit approval.
- Optional formal/waveform/LSP tools remain deferred until needed. Necessary approved test/build/lint/JSON prerequisites may be installed within the WSL setup scope; their current versions/evidence are recorded separately.
- Decide whether to deploy global Claude conventions; project-local setup is the current scope.
- Supply FastX SSH host/account, verified host key/authentication/VPN requirements, remote work path, module initialization if needed, and the existing absolute university `.db` path.
- Six scope/tool decisions are confirmed in Spec v0.2; the remaining architecture questions are grouped as R1–R5 in `specs/DECISIONS.md`. Explicit exact-revision approval is still required before RTL work.
- Define top module, source list, timing constraints/corner, metrics, workloads, and verification acceptance criteria after architecture review.

No scheduler correctness, lint, simulation, formal, CDC, synthesis, STA, or PPA results exist.

## Subsequent approval (2026-10-13)

Spec v1.0 and Q1–Q3/Option A are now approved; the earlier v0.2/RC approval holds above are historical. Existing local WSL/toolchain evidence remains valid. Approval does not verify FastX access or scheduler RTL/PPA.
