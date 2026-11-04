# CXL Scheduler Approved Implementation Scope

Read AGENTS.md, specs/CXL_SPEC.md v1.0, specs/APPROVAL.md, specs/DECISIONS.md, docs/SPEC_REVIEW.md, docs/STATUS.md and docs/PROGRESS_TRACKER.md. Owner approval resolves the RC1 hold: controlled RTL/model/testbench work is authorized through RTL Agent Team focused Phase4/5 skills. No rat-auto-design, architecture restart, unrelated dependencies or global config changes.

Claude Code RTL Agent Team implements/verifies; Codex independently reviews. Owner update2026-10-20: future Opus5.5 calls use medium effort for current execution/review work. If Claude allowance runs out, GPT6.1 Sol/high is explicitly authorized to continue; record the fallback and preserve file ownership/evidence. Already-running high-effort calls need not be restarted. One writer at a time. First common descriptor/FIFO, common hold/output, FCFS and RR with independent Python models. Stop and repair failed tests; stop before FAI integration until the common architecture/evidence review is complete. Preserve task logs/diff/results. Native CLI executes WSL tools via the documented source scripts/wsl_env.sh profile.

One shared switch_top/FIFO/output controller with identical cycle contract for all policies. N4/8/16,D16,M1,full105,atomic service. RR no unused timestamps; FCFS/FAI arrival metadata included. Main FAI and target-priority Algorithm-2 are distinct. >=31-bit unsigned threshold arithmetic, use32 bits; B/S production23 bits. Single-output10/10 alternation is project reconstruction, no cycle-identical paper claim.

FastX DC/PT/SAED32 is commercial flow. Do not blackbox FIFOs, use NanGate45/TSMC28 proxy, infer async reset, require C11/SystemC/UVM, or report unrun PPA. No nine sweep before successful integration. Imported managed guidance below is subordinate to the frozen spec.

<!-- RAT:START -->
## RTL Project (managed by rtl-agent-team plugin)

### Directory Map

```
specs/          Input specifications and datasheets
refc/           C reference model (DPI-C compatible, C11)
bfm/            Bus Functional Models (C++17 SystemC TLM-2.0)
rtl/            Synthesizable SystemVerilog (IEEE 1800-2009)
  common/       Shared utilities (ICG, synchronizer, CDC primitives)
  include/      Packages, defines
  top/          Top-level integration
sim/            Simulation & testbenches
  formal/       SVA formal verification (.sby configs)
  cdc/          CDC analysis
lint/           Lint flow (scripts/ + reports/)
syn/            Synthesis flow (scripts/ + reports/)
docs/           Design documentation (phase-1 ~ phase-7)
reviews/        Phase gate review verdicts
```

### Build System

```
make sim TOP=<module>        Simulate (verilator)
make lint                    Lint (verilator + verible + slang)
make syn TOP=<module>        Synthesize (yosys)
make formal TOP=<module>     Formal verify (SymbiYosys)
make help                    All targets + commercial EDA options (_xrun, _vcs, _dc, ...)
```

### Phase Pipeline → Directory Mapping

| Phase | Primary Artifacts | Reviews |
|-------|-------------------|---------|
| P1 Research | `docs/phase-1-research/` | `reviews/phase-1-research/` |
| P2 Architecture | `docs/phase-2-architecture/` + `refc/` | `reviews/phase-2-architecture/` |
| P3 μArch/BFM | `docs/phase-3-uarch/` + `bfm/` | `reviews/phase-3-uarch/` |
| P4 RTL+Unit | `rtl/` + `sim/` + `docs/phase-4-rtl/` | `reviews/phase-4-rtl/` |
| P5 Verify | `formal/` + `docs/phase-5-verify/` | `reviews/phase-5-verify/` |
| P6 Design Note | — | `reviews/phase-6-review/` |
| P7 Exploration | `docs/phase-7-exploration/` (optional) | — |

### Rules & Conventions

- Coding conventions: `.claude/rules/rtl-coding-conventions.md`
- Verification gate: `.claude/rules/rtl-verification-gate.md`
- Per-directory details: see `CLAUDE.md` in each subdirectory
<!-- RAT:END -->
