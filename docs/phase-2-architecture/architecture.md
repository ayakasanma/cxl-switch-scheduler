# CXL Baseline Architecture — Approved Spec v1.0

State: APPROVED, Project owner, 2026-10-13 (Asia/Taipei). Authority: specs/CXL_SPEC.md and specs/APPROVAL.md. This is an architecture contract, not implementation or verification evidence.

## Common framework

- One policy-selectable switch_top, N=4/8/16 request sources, common D=16 per-source FIFOs, M=1.
- Full 105-bit descriptors; source observation sideband is separate. Responses/tag tracking belong in TB.
- Single clock, synchronous active-low reset. Beginning-occupancy ready, no empty bypass, pushes eligible following cycle. Full FIFO refuses push even with same-edge pop.
- One equal-cost atomic fire maximum per cycle, no Length-based service cost.
- One common output hold controller. Descriptor/source/grant context stays stable through stalls; input pushes and FAI classification may continue. No policy-dependent pipeline or common-block duplication.
- FCFS/FAI store 32-bit arrival timestamps per entry; same-cycle ties use ascending source ID, modular age bound is less than 2^31 cycles. RR contains no unused timestamp storage/counter/selector.

## Approved policy details

RR starts polling source 0. Quantum10 counts successful fires only. Eligibility for continuation uses post-edge push/pop occupancy; expiry advances even with replacement push. Stalls consume no quota.

Main FAI starts all H, High first, with cleared pending transitions/quotas/counters/validity. H/B_H/L/B_L preserves prior effective priority until a second supporting window. KEEP/opposing/zero-service cancels pending transitions.

FAI uses window-local B/S, includes closing-edge fire before classification, clears for the next window, and makes new classification visible following cycle. S=sum(B). Production W=5,000,000, 23-bit B/S and at least31-bit widened unsigned comparisons; common32-bit intermediates. High/Low alternate visits of at most10 fires, skip empty classes without control bubbles, no banking or independent window quota reset; held old-class context completes first.

Algorithm-2 is separately selected: stable Low+UP -> Buffer target High; stable High+DOWN -> Buffer target Low; Buffer+UP -> stable High, Buffer+DOWN -> stable Low. Buffer uses target priority immediately and KEEP/idle retains Buffer. These are the owner's paper-behavior account, not an inspected local PDF. Shared one-output10/10 alternation is a project reconstruction, not cycle-identical paper dispatch.

## Execution and PPA boundary

Claude RTL Agent Team implements serial descriptor/FIFO, common hold controller, FCFS/model, RR/model milestones. Actual WSL lint/cocotb checks gate each milestone; Codex independently reviews before FAI integration. At freeze all RTL/models/tests are NOT_STARTED and scheduler checks NOT_RUN.

Primary PPA remains nine FCFS/RR10/Main FAI by N4/8/16. Include complete FIFO/control/policy storage; identical library/PVT/clock/uncertainty/I/O/load/transition/wire-load/effort/reporting profile, pilot-derived and frozen. FastX access and all project synthesis/STA/power remain unverified/unrun. Supplementary N4 Algorithm-2 functional/behavior/synthesis comparisons follow the primary nine. Multi-memory/APR/extensions remain deferred. No rat-auto-design.
