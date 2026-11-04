# Common framework contract review

Reviewer: Codex, 2026-10-13 (Asia/Taipei).
Reviewed authority: approved v1.0 at 1af80967bbc2fb83224f4725c4fb450889e69c62; docs/phase-3-uarch/common_framework.md.

Scope: document-level architecture refinement before Claude Phase4/5 delegation. This is not an RTL review, simulation result, synthesis result or plugin Phase3 research-completion claim.

PASS for bounded first assignment: organization preserves full105/N4/8/16/D16/M1, no bypass/beginning occupancy, synchronous reset, same common FIFO/hold/timing, necessary FCFS metadata and absent RR timestamps. FCFS/RR turn/timestamp rules match frozen spec. Shared hold must retain FAI context in later integration. Independent models and actual fail-fast WSL checks are required. No newly discovered correctness-critical contradiction.

Review gate: Claude may implement/test only descriptor/FIFO, common output control, FCFS/model and RR/model. Codex independently reviews actual common architecture and RTL/test evidence before FAI. Microarchitecture coding details can be chosen within approved timing; any inconsistent pipeline/semantics change needs escalation.
