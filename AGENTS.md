# CXL Scheduler agent instructions

## Approved scope and controlled delegation

Read specs/CXL_SPEC.md v1.0, specs/APPROVAL.md, specs/DECISIONS.md, docs/SPEC_REVIEW.md, docs/STATUS.md and docs/PROGRESS_TRACKER.md. The Project owner approved Option A/Q1–Q3 on2026-10-13 and authorized implementation. Do not treat obsolete RC holds as active. Approval is not completed progress.

- Work only in this existing repository. No rat-auto-design or restarted architecture pipeline.
- Claude Code with installed RTL Agent Team is the primary RTL implementation/verification agent. Codex orchestrates and independently reviews. Do not silently replace blocked Claude delegation with Codex-authored RTL.
- Owner update2026-10-20: future Claude Opus5.5 invocations use **medium** effort for the current execution/review work; this supersedes the earlier blanket high-effort preference. If Claude's usage allowance is exhausted, the owner explicitly authorizes **GPT6.1 Sol with high effort** to continue the remaining work instead of waiting for the reset. This is an approved fallback, not an unapproved model substitution. Calls already launched with high effort need not be restarted. Verify actual model fields for root/delegated work, preserve per-task provenance, and record any fallback. Preserve global settings and service routing; use invocation-local model/effort settings.
- Verify native CLI/plugin, frozen-spec access and noninteractive tool/file permissions before delegating. Preserve prompt, stream/output/error logs, changed-file inventory, Git diff and test evidence for each task in ignored .setup-logs/implementation and durable summaries.
- Avoid simultaneous writes: one assigned implementation task writes the shared files; Codex reviews read-only while it runs. Repair real failed tests before advancing, never waive them silently.
- First implement/verify descriptor+common FIFO, common output/stall controller, FCFS+independent Python model, then RR+model. Review common architecture and actual results before FAI integration.
- One policy-selectable switch_top shares the descriptor/FIFO/output-hold/sink/timing/synthesis boundary. Only necessary policy logic/metadata differs. No policy-dependent pipelines/bypass/buffering without approval. RR has no unused timestamps; FCFS/FAI retain arrival metadata.
- N=request sources4/8/16, D16, M1, full105, equal-cost atomic service. Reset synchronous active-low, RR pointer0, all Main FAI H/High first. Q1–Q3 are resolved.
- Main FAI keeps RC1 previous-effective-class four-state hysteresis. Algorithm-2 is a separate approved target-priority Buffer interpretation with KEEP/idle retention, never substituted into the primary nine. Single-output10/10 alternation is a common project reconstruction, not cycle-identical paper behavior.
- Production W5,000,000 uses23-bit B/S and >=31-bit widened unsigned comparison intermediates; use32-bit arithmetic. Counts are window-local, closing fire included before clear/class changes.
- Main nine-configuration PPA follows integrated functional verification. Supplementary N4 variant comparisons follow primary nine completion; N8/16 expansion only if material/time permits. Multi-memory/APR/optional extensions deferred.
- Update statuses from actual files/tests, not planned work or old report completion claims. No local IEEE PDF inspection is claimed without a real inspected file.

## Repository and tool boundaries

- Preserve existing files and user configuration. Never reset another repository or overwrite user templates.
- Keep RTL Agent Team directory conventions. `scripts/` holds reproducible regression/PPA orchestration; `sta/` holds PrimeTime scripts.
- Use the installed Claude Code plugin for `/rtl-agent-team:rat-setup` and `/rtl-agent-team:rat-init-project`. Do not silently recreate a skill invocation outside Claude Code.
- Read `docs/ENVIRONMENT.md` for the observed host/tool split. Windows, Git Bash, WSL, and FastX are distinct execution environments.
- The user explicitly approved installing Verilator, cocotb, and necessary open-source verification/build tools in Ubuntu WSL on 2026-10-13. Proceed with compatible pinned versions, essential WSL package prerequisites, lint tooling, and isolated Python dependencies without asking again. This does not authorize Windows system-wide changes, heavy SystemC/CDC dependencies, Docker images, cloud services, or unrelated EDA packages.
- Keep absolute machine paths and connection details in ignored local configuration. Do not place private credentials in tracked files.
- Never copy university cell libraries, PDKs, license files, or proprietary EDA executables into this repository. Library paths point to files already present on FastX.
- Primary synthesis/STA is FastX Design Compiler/PrimeTime with SAED32, not a NanGate45/TSMC28 proxy. Do not apply the plugin's hardcoded NAND2 area conversion as a project metric.
- Approved v1.0 requirements override plugin defaults: single clock/synchronous active-low reset, independent Python reference models, complete common FIFO storage and policy state in PPA. Do not impose mandatory extra output staging, SRAM macros, C11/DPI-C or numerical coverage defaults. Never blackbox FIFOs or include unused RR timestamps in a claimed primary comparison.
- Do not guess SSH hosts/users, disable host-key verification, or claim FastX access without a successful invocation.

## Verification and evidence

- Keep infrastructure checks separate from actual scheduler lint/simulation/regression. Each authorized RTL milestone needs real lint and cocotb evidence; missing/skipped runs are not PASS.
- A generic temporary toolchain-only HDL/cocotb fixture may validate lint, compilation, and simulator/VPI operation. Keep it outside project RTL/scheduler testbench directories, with generated files in ignored artifacts or a WSL cache. It must implement no scheduler features and must not change scheduler verification/PPA status to complete.
- After future approved RTL changes, require lint, a meaningful unit/reference-model test, simulation regression, and applicable assertions/formal/CDC checks. Document missing tools and waivers; do not mark unrun checks PASS.
- For synthesis/STA, preserve command, source revision, configuration, tool/module versions, selected library corner, logs, exit status, timing constraints, and reports. Check tool-reported errors as well as process status.
- State whether results are observed locally, verified remotely, provided by the user, or pending. The user reports a standalone registered-adder DC/PT smoke test on FastX; it is not a scheduler result.
- Do not report area, delay, power, fairness, throughput, coverage, or completed milestones without inspectable evidence from this project.

## Collaboration

For report planning or revision, load `docs/final-report/improvement-20261028/agent-handoff.json` and its two `read_order` documents. Check the recorded source hashes against current evidence, preserve the owner's five-step narrative, and consult each hypothesis's results and integration status before adding a claim. This handoff does not itself launch experiments.

For the applied October 28 revision, also load `docs/final-report/improvement-20261028/revision-release.json` and `REVISION_QA.md` in that directory. The original handoff and plans are immutable generator inputs: their pre-revision manuscript hashes and `PLAN_COMPLETE_NOT_APPLIED` status describe the planning snapshot. The release record supplies current output hashes, acceptance status, and unchanged follow-up experiment status. Do not refresh the frozen planning hashes merely to match an edited manuscript.

For the latest October 29 report, load `docs/final-report/update-20261029/revision-release.json`, its `read_order`, and `hypothesis-status.json`. This release adds the completed twenty-seed finite-Heavy RTL confirmation and current-source CGOF replay. H3 has partial single-boundary support; multi-window adaptation and system-level outcomes remain follow-up work. Preserve October 28 planning/release snapshots. Regenerate new figures with `generate_update_20261029.py`; the old generator retains its historical evidence pins.

Owner update2026-10-21: maintain `docs/DEVELOPMENT_REPORT.md` as the detailed development/experiment record and source for the final project report. Record actual source revisions, agent/model/effort, commands/run IDs, checks, failures/repairs, evidence locations, methodology changes and adoption decisions; keep planned/unrun work distinct. Codex owns this report while implementation agents write assigned code. Never include credentials or proprietary assets.

Keep changes focused and reproducible. Use a project-dedicated isolated Python environment; under WSL it may live in the user's Linux home for Linux filesystem performance. Tool release sources and caches remain outside the repository; use release archives instead of creating another project checkout. Keep generated reports and temporary session logs out of Git. Follow the controlled implementation milestones and independently review evidence before FAI integration. Stop/escalate real blockers or new correctness-critical contradictions; the approved specification is not silently changed.
