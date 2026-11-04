# Controlled RTL implementation assignment

Frozen approved Spec v1.0: 1af80967bbc2fb83224f4725c4fb450889e69c62; owner approval2026-10-13 (Asia/Taipei).
Implementer/verifier: native Claude Code RTL Agent Team0.14.6.
Orchestrator/independent reviewer: Codex.

## Serial task scope

M1 descriptor package + shared optional-metadata FIFO; actual WSL lint/cocotb FIFO tests.
M2 shared output/stall controller + common switch boundary; actual hold/timing tests.
M3 FCFS + independent Python model; timestamp ties/wrap/order/integrity/reference tests.
M4 RR + independent Python model; post-edge occupancy/quantum/stall/skip tests.
Stop at failed tests and repair; Codex reviews common framework and completed evidence before FAI integration. No concurrent conflicting writes. No rat-auto-design, architectural restart, synthesis sweep, heavy dependency installation or frozen spec edits.

Later M5 Main FAI/model; M6 separately selected Algorithm-2/model; M7 integrated nine-configuration randomized/directed/stress/production-window verification. PPA follows integration. Supplementary N4 comparisons follow primary nine completion.

## Evidence

Each Claude task preserves prompt, native CLI stream/stderr/exit, changed-file inventory, Git diff and test result files under ignored .setup-logs/implementation. Durable execution summary/review in docs/reviews identifies actual evidence. Plugin verification markers may be written only after real checks pass; no verification waiver.

Preflight confirms CLI/plugin, frozen-spec read, ordinary file write and WSL commands before implementation. A stale legacy hook tracker containing only file globs (*.sv/*.svh/*.v/*.vh) was archived as legacy-edit-tracker.txt and cleared after confirming zero RTL files; this repaired false tracking, not a verification waiver. Subsequent real RTL requires real lint/tests.

FastX SSH/account/library path and pilot numerical constraints remain pending. No synthesis/STA/power run is claimed. Original IEEE PDF is absent; supplied Algorithm-2 behavior is owner evidence only.

## Observed preflight result

Native CLI2.1.289 and installed/enabled plugin0.14.6 verified. A real noninteractive session read frozen approval/spec/AGENTS, confirmed commit, wrote the ignored probe file and successfully ran WSL setup_wsl.sh --check. Exit0, no permission denials. Focused Phase4/5 skills and plugin agent types were visible. Preflight did not generate RTL or count as scheduler verification.

## Current bounded outcome

M1 and M2 completed and independently verified. M2 source:7febabbb67584c0d5df65e8e77394127abfd8422. Claude reached session limit again during final housekeeping; reported reset16:20 Asia/Taipei. M3/M4 and FAI NOT_STARTED. The next controlled task is M3 FCFS, then M4 RR; original approved plan persists.
