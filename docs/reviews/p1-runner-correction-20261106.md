# P1 runner correction and decision baseline (2026-11-06)

This record corrects the earlier P1 execution note and the reviewer decision
summary. It does not authorize or restart a production campaign.

## C5 workload

The frozen C5 manifest at
`artifacts/implementation/followup-20261030/B-arrival-phase-confirmation-20261030/manifest.json`
specifies `heavy_work: 20000`, W=5,000,000 and phase horizon 5,000. Its command
is `scripts/run_arrival_phase_diagnosis.py --production-reviewed ... --heavy-work
20000 --phase-horizon 5000`. The 17,500,000-request burst belongs to the new
four-window workload, not this C5 baseline.

Consequently, choosing 4,000,000 under-load requests is a new workload choice,
not a necessary downscaling of C5. A direct C5 reproduction and a new multi-window
capacity experiment must have separate protocols and acceptance criteria.
The +834.25-cycle C5 endpoint is not a fixed target for a different burst size.

## Interrupted production attempt and overwritten evidence

Attempt: `artifacts/implementation/capacity-absorption/20261106T024926Z_w5m`.
The log reports under-load seeds 8101-8104 finished, but output filenames omitted
the seed. Each later seed overwrote the previous seed's six raw result files.
At inspection, five retained files contain seed 8105 and one contains seed 8104;
there is no final manifest and no active runner process. This attempt is
`INCOMPLETE_NOT_ACCEPTED`; its stdout is not a substitute for missing raw jobs.
The interruption cause is unknown. Existing files and logs are retained.

## Repair and short verification

`scripts/run_capacity_absorption.py` now includes seed and profile in filenames,
creates result files exclusively, rejects repeated seeds/profiles and invalid
worker counts, includes its own source hash, and checks source drift at completion.
Missing metrics or incomplete Heavy completion cannot pass conservation checks.
The manifest schema is `cxl-capacity-absorption-v2`.

W256 verification uses two seeds, two profiles, three policies and two lanes:
24 distinct result files and 12 conserved pairs. Reusing the output directory
fails without modifying results; duplicate seed/profile and zero-worker inputs
are rejected. Full log:
`.setup-logs/implementation/p1-under-over-20261106/runner-fix-20261106T094244Z.log`.
No production rerun was launched. The completed 600-job confirmation is separate
and was not rerun or edited.

## Remaining decisions

- Capacity experiment: define either faithful C5 reproduction or a separate
  multi-window workload, then freeze the matrix, work sizes, budgets and gates
  before running. The scaled defaults in the runner are not a frozen protocol.
- Directed drain: the attempted early cut failed the Heavy-completion assertion.
  That demonstrates this particular cut is unsupported; it does not prove that
  no long-backlog case can exist under any allowed trace. A3's natural two-cycle
  drain remains limited evidence.
- Latency recovery: define source/cohort attribution, sample counts, baseline
  band, consecutive recovery windows and censoring before collecting windowed
  metrics. Retain `NOT_DEFINED`/unrun status until those are fixed.

Adding a separately versioned harness does not invalidate historical results.
Historical source snapshots and acceptance hashes must remain available, and new
runs need their own freeze and verification. No new run is guaranteed to pass.
