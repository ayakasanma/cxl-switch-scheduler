# Controlled common framework microarchitecture

Authority: approved Spec v1.0 at 1af80967bbc2fb83224f4725c4fb450889e69c62. This document refines implementation organization within that cycle contract; it records no implemented/tested RTL. Claude implements serially, Codex reviews independently.

## Shared blocks and timing

1. Descriptor package: exact 105-bit MSB-first approved slices, policy identifiers, no source/destination/tag tracking in payload.
2. One reusable per-source FIFO, D16 for baseline: beginning count determines ready, no empty bypass, simultaneous push/pop preserves count/order, full refuses push even on pop. Synchronous active-low reset clears control/validity. Descriptor contents remain opaque.
3. Arrival metadata is an elaboration-time FIFO option for FCFS/FAI only. Optional per-entry32-bit timestamp and shared cycle counter are absent for RR, including no dummy timestamp bank. Identical descriptor FIFO pointers/occupancy/handshake logic across policies. FCFS/FAI use one modular oldest-head selector with ascending-source ties.
4. One common output hold controller accepts a policy candidate and its context, selects existing heads combinationally without an extra mandatory output stage, and latches the offered grant on a stalled edge. The selected head cannot pop until fire, preserving data. Held source/context cannot change under later pushes/classification. Release on fire or reset. Future FAI must extend/use generic context in this shared block, not duplicate output control.
5. One switch_top connects N identical FIFOs and shared output control to an elaboration-time selected policy. Flattened input vectors are acceptable if widths/source indexing preserve logical ports. No policy-dependent bypass, pipelines or extra buffering. Input readiness remains independent of output ready.

Reset suppresses handshakes and clears held validity, pointers/count/control/cycle state. Source valid/count reflect pre-edge occupancy; accepted push becomes a head only in the following cycle. Source selection cannot manufacture a pop without common output fire. Data/source are meaningful while output valid. No synthesized debug timestamp preload port.

## First policy milestones

FCFS selects modular-oldest eligible head. Equal timestamps choose lowest source ID. The cycle counter advances every non-reset edge including stalls; push captures the pre-edge value. Directed wrap test may adjust simulation-only internal time/model together.

RR starts pointer0, primary quantum10. A selected turn is continued while post-edge source occupancy is positive and quota remains; expiry advances regardless of replacement push. Circular skipping creates no control bubble. Stalls do not consume quota and cannot replace the held grant. Quantum1 is separately tested. RR has no arrival metadata.

FAI is a later milestone after common/FCFS/RR review; neither Main nor Algorithm-2 may be integrated by this first assignment. Production widths and class/window semantics remain the frozen spec; no unsupported stub may masquerade as an implemented FAI policy.

## Verification boundary

Each milestone requires fail-fast Verilator lint and real cocotb execution in WSL. Verify FIFO empty/full/full-plus-pop/simultaneous push-pop/no-bypass/reset, hold under long stalls/new arrivals, FCFS ties/wrap/order, RR quota/empty/replacement/quantum1. Independent Python queue/policy models must derive expected traces from abstract approved semantics, not translating RTL expressions. Whole105-bit integrity, conservation, source ordering, acceptance/fire and reset epochs are checked. Testbench responses remain outside RTL.

Reproducible random phase uses identical intended arrivals/ready traces across policies, with acceptance variation recorded. Full primary180-run and production FAI regressions remain a later integrated acceptance gate; partial first-milestone tests must be labeled accordingly. No skipped checks count as pass. Preserve command/config/seed/version/stdout/exit/JUnit/diff.

## Synthesis preparation

Do not execute PPA now. Generic common framework retains complete mapped FIFO/policy state. FastX methodology freezes SAED32 RVT corner, pilot-derived common clock, uncertainty/I/O/load/transition/wire-load/effort/reporting. No proxy area or unrun results. The generic scaffold make lint is not acceptance evidence because it ignores errors; create/use a dedicated fail-fast verification runner.
