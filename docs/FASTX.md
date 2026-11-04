# FastX integration — prepared, access pending

Owner-operated FastX desktop handoff: [中文手動操作手冊](FASTX_HANDOFF.md) and [2026-10-17階段小結](STAGE_SUMMARY_2026-10-17.md). That route uses an exported source snapshot and a manually parameterized copy of the DC template. It does not depend on giving Codex SSH access, and it does not add nine-configuration selection to the generic remote runner below. The manual procedure still requires validation on FastX.

The user confirmed this as the primary commercial flow on 2026-10-13: DC/PT with SAED32, FCFS/RR/FAI-inspired at N=4,8,16, baseline M=1 and full105-bit descriptors. All nine synthesis experiments remain NOT_RUN. WSL open-source verification does not replace this commercial experiment matrix. No proxy NanGate45 area conversion applies.

Approved Spec v1.0 includes D16 common per-source FIFOs in the complete synthesized switch, RR quantum10 and production FAI W5,000,000/quotas10/10. Include actual policy metadata/control, exclude TB memories/responses, and keep all nine runs on a pilot-derived common clock/SDC/library/PVT/effort/optimization profile. The prior5ns adder smoke target is not final. Attempt annotated pre-layout power if supported or document the limitation. These approved requirements are not synthesis results. Functional M1-M5 integration is accepted; commercial measurement is pending.

No remote SSH, Design Compiler, or PrimeTime invocation has been verified by this repository setup. No synthesis, STA, or PPA results have been generated for this project.

The user reports that the following environment is validated on the university FastX host, including a successful standalone registered-adder synthesis/STA smoke test:

- Module: `Synopsys_x86-64/2024`
- Design Compiler: `W-2024.09`
- PrimeTime: `W-2024.09`
- SAED32 RVT library: `saed32rvt_tt0p78v25c.db`

That prior smoke test is user-provided evidence. It has not been repeated here and is not a scheduler result. The university installation and its libraries are not assumed to exist on the local Windows computer.

## Configure access

Copy `scripts/fastx.config.example.json` to `scripts/fastx.config.local.json`. The latter must remain ignored by Git. Fill the authorized SSH hostname, account, a dedicated absolute Linux `remote_work_root`, and the existing absolute university `target_library` path. The expected library filename alone does not establish its directory.

Set `module_init` to the existing university-approved module initialization script if `module` is unavailable in a noninteractive login shell. Leave it empty when the login shell already initializes modules. The scripts use Bash and the host's `tar`, `hostname`, and `uname`; they do not install dependencies. `identity_file` is optional and refers to an existing local SSH key; neither it nor any other authentication material is uploaded.

The runner uses OpenSSH with `BatchMode=yes`, a connection timeout, and `StrictHostKeyChecking=yes`. Arrange approved SSH/VPN access and verify the host fingerprint outside this runner first. It never weakens host-key checking, guesses a host or account, prompts for passwords, or changes SSH configuration.

From the repository root, using the available Python executable:

```powershell
python scripts/remote_eda.py preflight --config scripts/fastx.config.local.json
python scripts/remote_eda.py preflight --config scripts/fastx.config.local.json --execute
```

Without `--execute`, every operation validates configuration and prints a plan without contacting the host. Missing connection/library fields produce an actionable configuration error. Executed preflight loads the configured module, checks both tool commands, prints their actual version banners, and checks library readability. It does not synthesize or analyze timing and creates no remote run directory. A zero exit status from a real preflight establishes those limited checks only; it does not prove license checkout or a successful design run.

## Approved architecture and pending handoff

Spec v1.0 is approved at `1af80967bbc2fb83224f4725c4fb450889e69c62`; `specs/APPROVAL.md` already contains the actual Project owner approval dated2026-10-13. M1-M5 functional integration is accepted at source `cefbbb0`. Do not recreate the approval record or request a second blanket architecture approval. The runner's mechanical approval-field check remains applicable.

The current generic remote config/DC template **does not yet select N/policy parameters for the nine configurations**: `syn/dc.tcl` only elaborates the configured top. Reviewed parameter plumbing, exact source lists, per-run parameter manifests and one pilot-derived common PPA profile are still required. The runner is an unvalidated remote execution template, not a complete sweep. No clock/load/wire-load/effort value is frozen by this document.

After approved RTL and constraints exist, set `top_module`, explicitly list repository-relative `rtl_files` and `constraint_files` for synthesis, or `sta_netlist_files` and `sta_constraint_files` for PrimeTime. Use forward slashes in these lists even on Windows. The local repository path may contain spaces. Inputs must be regular files inside the repository and cannot be symlinks. Source paths, top names, and downloaded outputs must use ordinary portable filenames; Windows device names, invalid characters, and trailing dots/spaces are rejected. RTL inputs allow `.v`, `.sv`, `.vh`, and `.svh`; constraints allow `.sdc`; STA netlists allow `.v`. No default clock, reset, IO delay, timing exception, or operating corner is invented.

```powershell
python scripts/remote_eda.py syn --config scripts/fastx.config.local.json
python scripts/remote_eda.py syn --config scripts/fastx.config.local.json --execute
python scripts/remote_eda.py sta --config scripts/fastx.config.local.json
python scripts/remote_eda.py sta --config scripts/fastx.config.local.json --execute
```

Every executed design run creates a new timestamp/UUID directory under `<remote_work_root>/runs/` and refuses to overwrite an existing run directory. Only the explicit input files, fixed runner/Tcl templates, a copy of the approval record, and generated path-only Tcl configuration are uploaded. No entire-repository or home-directory synchronization is performed. Generated reports and logs (`reports/*.rpt`, `reports/*.log`), netlists (`output/*.v`), and SDC (`output/*.sdc`) are the only permitted downloads; archives reject unexpected files and symlinks. Outputs are stored in ignored `artifacts/fastx/<run-id>/` with an input SHA-256 manifest, normalized configuration excluding the SSH key path, Git revision/worktree status, and actual exit codes. Remote run directories are retained for inspection; there is no automatic cleanup.

The DC template performs elaboration/linking, reads explicit constraints, compiles, and writes area/timing/QoR reports, netlist, and SDC. The PT template reads explicit netlist/SDC and writes setup/hold, constraint, coverage, and check-timing reports. Each Tcl script writes a completion marker only after its commands complete. The Bash entry checks that marker, rejects tool `Error:`/`Fatal:` diagnostics even when a tool exits zero, and checks nonempty DC netlist/SDC outputs. These templates require validation on the real university host. Successful commands alone do not establish timing closure: inspect link/check-timing warnings, unconstrained paths, coverage, violations, and the suitability of the approved constraints. The manifest's `TOOL_COMMANDS_COMPLETED` status records execution, not architecture acceptance or timing closure.

The current configuration supports one target `.db` library. Additional link libraries, multiple corners, parasitics, activity-based power, and tool-specific settings require reviewed extensions when the design needs them. No power result or completed PPA milestone is claimed.

## Pending prerequisites

- Authorized SSH hostname/account and any required VPN or jump-host arrangement.
- Verified host key and working noninteractive authentication.
- Writable dedicated remote project directory.
- Absolute module initialization path if needed.
- Existing absolute SAED32 RVT library path on FastX and permission to use it.
- Actual preflight execution and tool/license verification on that host.
- Approved specification/interface already exist; prepare the exact shared switch_top source list, N/policy parameter selection and pilot-derived timing constraints.
- Approved STA corner, netlist/SDC handoff, coverage criteria, and any power methodology.

Never copy university standard-cell libraries, PDKs, licenses, or proprietary executables into the repository or its artifacts.
