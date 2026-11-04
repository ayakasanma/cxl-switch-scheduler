# RTL Agent Team setup and reproduction

The official source is [babyworm/rtl-agent-team](https://github.com/babyworm/rtl-agent-team). This setup uses the documented Claude Code CLI installation path:

```powershell
claude plugin marketplace add babyworm/rtl-agent-team
claude plugin install rtl-agent-team
claude plugin list --json
```

Observed installation on 2026-10-13 (Asia/Taipei): `rtl-agent-team@rtl-agent-marketplace`, version `0.14.6`, user scope, enabled. Marketplace source revision: `56c02875d77bd7b6d44fe9c5acd27d7d03f34b12`. Claude Code version: `2.1.289`. Verify the installed version on reproduction; the marketplace's latest release may differ. Do not silently claim that a newer plugin has the same behavior.

The source/cache lives in the user's Claude plugin directories, outside this repository. The plugin is not vendored. No optional SystemVerilog LSP plugin or other marketplace plugin was installed by this task.

## Run the required skills through Claude Code

From the repository root:

```powershell
claude
```

In the Claude Code session:

```text
/rtl-agent-team:rat-setup
/rtl-agent-team:rat-init-project
```

Retain the constraints in `AGENTS.md` and project `CLAUDE.md`: audit first, install only the WSL Verilator/cocotb/minimal tools now explicitly approved by the user, no global rule deployment, no design/implementation workflow, and omit the generic `rtl/include/template_module.sv` that the initializer normally offers. The directories, guides, rules, generic filelist/Makefile templates, and EDA wrappers are environment scaffolding. Their example top names, reset/memory defaults, tool preferences and coverage thresholds are not approved scheduler requirements. Use `docs/WSL_SETUP.md` for the selected reproducible runtime.

Initial print-mode attempts for both skills failed before execution because Claude's OAuth session was expired. The user reauthenticated, and the attempts were retried. `docs/ENVIRONMENT.md` and `docs/STATUS.md` record the final observed outcomes. Raw session logs are local and ignored under `.setup-logs/`; they are not portable configuration or project verification.

If authentication expires in a future run, use `claude auth login --claudeai` and complete the browser sign-in. `claude auth status` alone was insufficient evidence of a usable session in the initial attempt.

The final `rat-setup` audit completed with verdict NOT READY and no installs. Project initialization deployed its scaffolding, but its optional diagram fallback was blocked: Claude's automatic approval review classified `.claude/rules/diagram-rules.md` as sensitive, and the noninteractive session had no approval surface. The blocked write was not retried or bypassed. The exact proposed file is [diagram-rules.pending.md](diagram-rules.pending.md). To finish that optional step, run `claude` interactively in the repository, request deployment of those exact contents to `.claude/rules/diagram-rules.md`, and approve the sensitive-file write there. The scope is docs/reviews diagram guidance only; no global convention change or RTL generation is needed. The initial skill's empty result and exit 0 do not establish full initialization completion.

## Historical wizard choices and current authorization

No dependency installation was authorized during the original audit. The user subsequently explicitly authorized Verilator, cocotb and necessary open-source verification/build tools in WSL on 2026-10-13. That authorization satisfies the installation choice for this scoped environment; do not ask again. The official [rat-setup skill](https://github.com/babyworm/rtl-agent-team/blob/56c02875d77bd7b6d44fe9c5acd27d7d03f34b12/skills/rat-setup/SKILL.md) opt-in policy still applies to unrelated additional installs/configuration.

The original wizard categories and their current scope are:

| Prompt | Choice required |
| --- | --- |
| Q1: required tools | WSL minimal Verilator/cocotb/build/lint toolchain is now authorized. Heavy SystemC/CDC remains outside that automatic scope; the full RAT profile may remain NOT READY. |
| Q2: recommended/optional tools | Necessary JSON/lint/build/test helpers are within WSL scope. Yosys/SymbiYosys, LSP, fallback simulators and waveform GUIs remain deferred unless needed. |
| Q2b: commercial environment | Confirm detected local tools or supply a valid local setup command; FastX's module must not be treated as a local command. |
| Q2c: target library | Existing `.lib` path or skip for plugin Liberty configuration. FastX's `.db` is a separate DC/PT setting; no `.lib` path is known. |
| Q3: global conventions | Yes/no to writing global Claude rules and a diagram block. Project-local rules suffice for this repository. |
| Q4: test dependencies | Isolated WSL cocotb/pytest and necessary dependencies are authorized. Avoid unrelated codec/data packages simply because the generic wizard lists them. |

SystemC and a CDC tool are required by the plugin's full pipeline audit but their relevance to this scheduler's scope remains unresolved. Heavy SystemC/CDC, Docker, cloud, and unrelated EDA installations remain deferred. Compatible pinned Verilator/cocotb and dedicated WSL runtime choices are made and verified by the setup scripts; see `docs/WSL_SETUP.md`. Do not install into the machine's Anaconda environment.

## Reproduction checks

- `python scripts/check_environment.py --json`
- `python scripts/check_environment.py --json --wsl` on this Windows host.
- `claude plugin list --json`
- `python scripts/remote_eda.py preflight --config scripts/fastx.config.local.json` after local configuration exists: plan only.
- `git status --short --branch`

These are environment checks. They do not establish scheduler correctness, PPA, or successful university synthesis/STA.

The existing `rat_config.json` and `config.mk` are retained as the initial plugin-generated portable scaffold, with no machine EDA executable/library paths. Their `detected:false` values describe the pre-install scan and are not the current WSL tool inventory. Activate `scripts/wsl_env.sh`; wrappers find installed executables through PATH. Run the environment audit inside that activated WSL shell for current evidence. `cdc: structural` is only a built-in wrapper preference, not an installed CDC signoff tool. Any future refreshed machine paths/connection overrides belong in ignored local configuration rather than a committed portable snapshot.

Imported command limitations: `scripts/run_sim.sh` defaults to Icarus, so pass `--sim verilator` explicitly. The generic `make lint` target prefixes tool commands with Make's ignore-error operator and also tries optional slang; its zero exit status is not lint evidence. Use the fail-fast direct lint/integration checks in `scripts/smoke_wsl_toolchain.py` for current infrastructure evidence. Scheduler regression targets will be reviewed against the approved design before being used as acceptance gates.
