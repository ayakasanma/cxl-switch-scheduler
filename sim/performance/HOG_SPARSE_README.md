# Heavy source and sparse sources

Run from this repository in Ubuntu WSL, after `source scripts/wsl_env.sh`:

```
python -m pytest sim/performance/tests/test_hog_sparse.py
python scripts/run_hog_sparse.py HS-pilot -j3 --make-jobs 2
# Only after independent pilot review:
python scripts/run_hog_sparse.py HS-main -j3 --make-jobs 2
```

The launcher extends the existing strict runner registry and reuses its lint, Verilator,
make, cocotb, numeric-exit and JUnit gates. HS-pilot is three W256/seed509 sensitivity
runs; it never implies formal acceptance. HS-main is exactly policies0/1/2 times
seeds509–513, W5M. Neither scope changes RTL or the independent TB/reference models.

Cycle0 is the first non-reset edge. Two real W windows train heavy source0, offering
one full105 descriptor every active cycle; sparse sources1–3 independently offer with
probability1/128. A lasts100000 cycles, then a1024-cycle heavy-on sparse completion
guard. B lasts102400 cycles; each sparse host generates eight descriptors at one
uniform seeded offset in each of100 blocks of1024 cycles. Its1024-cycle guard also
keeps the heavy host active. All generated work, including heavy backlog, drains after
both checked guards. Ready is1 throughout. Pending input descriptors stay offered
until accepted; no backlog is dropped. Arrival, burst-offset and descriptor RNG streams
are separate per source; canonical config/event/ready trace hashes exclude policy.

Raw `hog_sparse_metrics.json` contains `metrics.phases` (training,A,A_guard,B,B_guard,
drain), `metrics.cohorts` (cold,A,B), snapshots, arrival contexts and Main phase contexts.
Sparse generation cohorts retain direct generation-to-fire and both stage histograms,
per-source and pooled; P99 is exact nearest-rank, never a sum of stage P99s. Cold is
production-only `[2W-101024,2W-1024)` and must complete before2W. Actual FCFS/Main
interface digests over the entire first2W must match. Every Main classification closure
and next-cycle activation is checked by the existing independent TB. The first two
heavy windows must be DOWN, sparse staysHigh; production classes remainL/H/H/H through
both measured profiles and guards. Pilot later classifications proceed normally.

All source request/response counts conserve through final drain. Sparse cohorts complete
before background generation stops. Snapshot ages are right-censored at the next-cycle
boundary; producer/FIFO occupancy sampling is pre-edge, after current generation.
Occupancy/gap/latency histograms reuse existing StreamStats/Gaps. Backlog/all-pending age
summaries use constant-memory count/mean/min/max/end; no warmup heavy latency histogram
or completed-request history is retained. Heavy latency is omitted because this is a
finite overload experiment, while its counters/backlog and full drain remain recorded.

Evidence lives under `artifacts/implementation/HS-{pilot,main}/<run-id>/`: commands,
versions/config, strict logs/JUnit/numeric exits, copied raw metrics,
`source_hashes_before.json`, `source_hashes_after.json`, and `hog_sparse_scope.json`.
The independent scope gate regenerates complete active traces, checks exact matrix,
histograms, cohorts, phases, labels, guards, cold pins, and source freeze. Every long
simulation has a24-hour timeout; final drain additionally uses an explicit queue-count
bound. Failures/partial jobs remain failures. Progress and peakRSS are logged every250k
real edges, and peakRSS/wall time are saved per run. No favorable latency criterion is
required: negative benefit is a valid scientific result. No application/WCET claim follows.
