# Supplementary power replay: tests and execution boundary

The accepted nine-case cold-reset seed509 estimates at `4007f99` remain the primary power
dataset. This test-only extension adds two supplementary modes addressing the cold-only and
single-seed gaps. It
changes no RTL, independent model, approved Spec, synthesis profile, mapped netlist, SDC or
PrimeTime script. Parent Codex owns actual commercial execution and adoption. Implementation
continues the interrupted native func-verifier work under the owner's GPT-6.1 Sol/high quota
fallback; the original/resume prompts, native partial diff, failures, fixes and local evidence
are retained in `.setup-logs/implementation/power-extension-sol-20261021/`.

## Fixed modes and provenance

The default command still exports the v1 cold seed509, 100,000-cycle replay. Its deterministic
vector plaintext/gzip bytes are unchanged. Metadata source hashes necessarily identify the
new tooling; old payloads and reports are preserved.

```sh
python scripts/export_power_vectors.py --policy rr --n 4 --out NEW_DIRECTORY
python scripts/export_power_vectors.py --mode cold-seed --seed 510 --policy rr --n 4 --out NEW_DIRECTORY
python scripts/export_power_vectors.py --mode boundary-n4 --seed 509 --policy fai-main --n 4 --out NEW_DIRECTORY
```

Cold supplementation permits only seeds510/511 and the existing nine policy/N configurations.
It reuses the unchanged `traffic_trace.make_trace` primary profile. For each seed/N the intended
generation/ready trace is identical across policies, while actual acceptance remains separate.
These runs remain cold/all-H for Main and make no classification-power claim.

The boundary mode permits only seed509/N4, with FCFS/RR/Main and true production W=5,000,000.
It uses unchanged `ProductionTraffic` and `StreamProducers`, exactly 9,999,500 warmup cycles
followed by 100,000 measured cycles: 10,099,500 checked non-reset cycles in all. Three initial
synchronous reset edges are outside both phases. No time skip, state preload, reduced production
window or reset at the phase cut is allowed. Every real warmup and measured cycle has the same
reference-model pin, full105 producer hold and conservation checks. The gate TB consumes all
rows and compares ready/valid and valid source/full105 pins; it has no policy oracle.

The literal independent Main expectations are:

| Global closing cycle (zero based) | Phase | Evidence by source | Classes visible the following cycle |
| --- | --- | --- | --- |
| 4,999,999 | Warmup | DOWN, DOWN, UP, DOWN | B_H, B_H, H, B_H |
| 9,999,999 | Measured index499 | DOWN, UP, KEEP, DOWN | L, H, H, L |

The exporter checks exact closing-edge fire inclusion, Bsum=S, cleared B/S/index, widened
integer inequalities and next-cycle class visibility. The unchanged model also checks its
window invariants every committed cycle. Held grants retain their class/quota context. The
first expected closing is stalled/held; the second carries a fire. Metadata distinguishes all,
warmup and measured generated/accepted/service populations, cutoff/end outstanding populations,
state continuity, per-class measured service and closing records. Gate results independently
report warmup/measured/all acceptance/fire totals and each source's populations. Class and
High/Low labels in metadata are model evidence; this TB does not directly probe mapped internal
class registers. Gate pin replay must agree through the boundary and subsequent service.

SAIF begins at the phase cut without resetting the DUT or discarding pending producers. Its
duration remains exactly 100,000 x25ns =2,500,000ns. The second closing lies after499 pre-boundary
cycles; the new class map is visible at measured index500, followed by99,500 post-boundary
cycles. **This deliberately boundary-focused estimate includes one classification per100,000
measured cycles, rather than the production frequency of one per5,000,000.** It tests real
classification and subsequent activity; it is not representative steady-state/production-average
power and does not close every long-run power limitation.

The v2 header is `43585032 MODE_ID N TOTAL WARMUP MEASURED SEED POLICY_ID 25000 3`.
Mode1 is supplementary cold; mode2 is the production boundary run. Row layout is unchanged
from v1. Model histories are trimmed every65,536 cycles, and `StreamProducers` retains pending
entries rather than every acceptance. Gzip writing, SHA-256 and runner decompression stream
with bounded buffers. The long run has no flat10M trace or per-cycle result history. The gzip,
expanded ASCII file and simulator build still need disk space; inspect actual file sizes and
available remote space before upload/execution. The TB prints progress every1M checked cycles
for the long mode, including its current phase.

## Local tests and their scope

Run the impacted suites with:

```sh
python -m unittest discover -s scripts -p 'test_power*.py' -v
```

The original power-flow suite retains qualified check_power table-range handling and rejects
fatal/missing-table/function/unknown diagnostic shapes. Supplementary tests cover:

- Exact legacy v1 vector hashes and a full100k v1 replay through the actual common TB.
- Deterministic distinct seeds510/511, intended-trace pairing across all policies/N, and fixed
  seed/N/mode/window/period/descriptor/overwrite guards. Tests do not invoke full boundary export.
- Separate phase counters, held-context continuity, full/refused producers at the phase cut,
  no bypass, closing fire inclusion/clear/class visibility, widened arithmetic and mutations.
- Bounded retained model histories and identical per-cycle pins with and without an observation
  cut. The cut changes accounting and activity collection only.
- Result population/phase corruption and SAIF scope/duration/unknown-clock/transition-count
  corruption. Finite-window endpoint counts permit the observed `2*measured_cycles-1` or ideal
  `2*measured_cycles` clock transitions.
- Strict Verilator builds of the **actual** common TB with actual FCFS/RR/Main RTL, using only
  explicitly labelled W256 local fixtures; all three replay768 cycles with495 warmup/273 measured.
  Bad headers, truncated/extra rows and ready/valid/source/full105 mutations must fail.
- True four-state Icarus fixed-pin fixtures reject X on ready, valid, valid source, full105 and
  replay clock. These fixtures implement no scheduler. A known-value control must pass.
- Fixture mode9 is refused by the production runner and production TB compilation. It can run
  only with local fixture/no-SAIF compile flags and cannot be labelled production power evidence.

Verilator builds use its default timescale argument for RTL modules that have no timescale;
warnings remain fatal. Windows can run the Python and Tcl-stub tests; WSL runs actual simulator
checks. Its minimal Python environment lacks Tkinter, so the existing Tcl-stub test is explicitly
skipped there and runs on Windows. Icarus12.0 is unpacked in the existing user-local WSL tool
directory, with no system configuration changes. Actual test totals/logs and repaired failures
are in the evidence directory's final READY record. These fixtures establish tooling behavior,
not newly measured production classification or power results.

## Parent review and remaining execution

After frozen-code review, generate fresh exclusive payload directories for all18 cold-seed cases
and the three N4 boundary cases. Check paired intended hashes and all/warmup/measured populations.
For the long Main export, require the literal two closing trajectories and positive measured
High/Low service. If a real failure occurs, preserve its partial output and diagnose it before
advancing. Do not reinterpret a shortened fixture as a completed production export.

The existing parent upload/execution process uses the updated runner; `sta/power_pt.tcl` is
unchanged. Review actual VCS compile/replay/SAIF and PT units, annotation/source/clock coverage,
check_power quality, unused-output warnings and immutable hashes as required by `POWER_METHOD.md`.
New seeds/boundary estimates stay supplementary and inherit the zero-delay/prelayout limitations.
No actual supplementary gate/SAIF/PT result is claimed until those runs and independent review
complete. The parent separately owns any equivalence verification; this extension claims none.

APR/extracted parasitics, SDF glitches/physical clock tree, multiple PVT corners, representative
steady-state power, Algorithm-2 power and broader trained-state workloads remain deferred.

## Actual execution outcome —2026-10-21

All18 cold and3 real-boundary cases completed and passed independent raw/diagnostic/hash review.
See [accepted supplementary results](POWER_SUPPLEMENT_2026-10-21.md) and
[machine-readable evidence](ppa/power-supplement-20261021.json). Earlier NOT_RUN text above
describes the tooling-freeze boundary. No fixture was substituted for the real10,099,500-cycle
runs; no RTL/model/Spec/profile/PT script changed. Limits, repaired diagnostics and source
versions are preserved in the result and development reports.
