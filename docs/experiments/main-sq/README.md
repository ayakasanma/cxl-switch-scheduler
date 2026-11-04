# Main-SQ experimental extension

## Material Passport

- Origin: owner Main-SQ optimization task, 2026-10-23 (Asia/Taipei).
- Baseline HEAD: `bb7f407623812c1866bafe2352a0433ffad263c8`.
- Development branch: `experiment/main-sq`, in the sole existing repository.
- Verification status: baseline archive and actual RTL causal replay **PASS**; proposed persistent SQ1/SQ2 benefit gate **FAIL**. Candidate implementation and PPA **NOT_RUN**.
- Research question: can source sub-quotas improve sparse-burst tails while retaining isolated-request protection, capacity and hardware efficiency?

This is a separate experimental extension. The accepted Main, frozen Spec v1.0, prior
performance/PPA evidence and existing Final manuscript are preserved. No adoption is implied.

## Execution gates

1. Recompute the accepted five-seed results from original raw artifacts.
2. Reproduce a paired representative case on actual RTL with passive grant/request traces.
3. Attribute tail delay to class visits, other High sources, admission and adaptation.
4. Implement SQ1/SQ2 only if the evidence supports a plausible within-class benefit.
5. If implemented, verify correctness before controlled performance and N4 DC/PT/Formality.
6. Main-HQ and Main-AGE require a separate evidence-backed design decision.

The owner explicitly permits stopping at gate 4 with a narrower recommendation if SQ
does not address the measured bottleneck. Unexecuted phases will remain NOT_RUN.

## Evidence preservation

Ignored execution root: `.setup-logs/implementation/main-sq-20261023/`. It contains the
entry dirty-file hashes, protected-file hashes, original dirty development-report snapshot,
native CLI prompt/settings/stream/stderr/numeric exit and new audits/replays. No credentials
or proprietary assets belong in tracked records.

The first preservation attempt encountered an inaccessible WSL `lit-review/.venv/lib64`
symlink from Windows and stopped before native invocation. The repaired inventory enumerates
Git-tracked and nonignored report files without traversing that environment; it does not
remove or modify the link. The original failure is retained in the session tool record.

Independent archive audit, executed 2026-10-23:

```sh
python scripts/audit_hog_sparse.py --run 20261022T034507Z_311 \
  --output .setup-logs/implementation/main-sq-20261023/accepted-baseline-audit
```

Actual exit 0: 15 accepted RTL records, five matched stimulus groups, 156,657,531 recorded
nonreset cycles rechecked. This archive audit adds **zero new RTL simulation cycles**.

New reports and raw indexes are stored here; the Final manuscript is outside this task.

## Completed outcome

Production `MSQ-main/20261023T083405Z_1850` reproduces accepted seed509 exactly, excluding
only three declared runtime/RSS fields. Together with the W256 pilot it adds six actual
baseline RTL runs and31,962,468 nonreset cycles. All strict lint/build/JUnit gates and
independent trace reviews pass. The original32 unit cases repeat, rather than becoming
64 distinct tests.

Seven High visits expire with pending High work. Offline fixed-slot SQ1/SQ2 yields
pooled P99=24/25 versus actual Main24, and maximum34 versus Main31; source2 also regresses.
The task's conditional gate therefore closes **without SQ RTL/model/PPA implementation**.
This is a narrow negative design screen, not an RTL result or universal rejection of SQ.
Accepted Main stays unchanged. Main-HQ/Main-AGE require a separate decision.

| Deliverable | Contents |
| --- | --- |
| [BASELINE_DIAGNOSIS.md](BASELINE_DIAGNOSIS.md) | Original five-seed audit, four hypotheses, actual grant/tag evidence and gate. |
| [MAIN_SQ_SPEC.md](MAIN_SQ_SPEC.md) | Exact offline screen rules; unresolved general hardware contract is not approved. |
| [VERIFICATION_RESULTS.md](VERIFICATION_RESULTS.md) | Actual commands/exits/cycle counts, failures/repairs and unrun candidate checks. |
| [PERFORMANCE_COMPARISON.md](PERFORMANCE_COMPARISON.md) | Actual versus offline distributions, service/congestion and sampling limits. |
| [PPA_COMPARISON.md](PPA_COMPARISON.md) | Accepted baseline costs/profile; candidate costs NOT_RUN. |
| [RECOMMENDATION.md](RECOMMENDATION.md) | Stop decision, retained Main and conditional HQ/AGE assessment. |
| [data/](data/) | Machine-readable actual/screen CSVs, full audit and execution/source provenance. |
| [diagnosis.svg](diagnosis.svg) / [baseline_burst_tail.svg](baseline_burst_tail.svg) | Reproducible, explicitly labeled scientific plots. |

## Portable raw evidence and reproduction

The [production raw bundle](production-replay-seed509.tar.gz) is2,192,355 bytes/22 files,
SHA256 `e2e75552d02885568eb05b7a6503b4e980c546922807759b5de9b2afbf7bea66`.
It contains actual result JSON/gzip traces, raw JUnit, source manifests, accepted reference
metrics and a hash manifest. Its summary is explicitly a **portable gate-field projection**;
the original summary hash is retained. Full original logs/summary and native execution
records remain in the local ignored artifact/execution roots. The bundle is project-owned
data, with no simulator binaries, proprietary libraries or credentials.

From the repository root, use fresh output directories (Python3.12+ for extraction):

```sh
python -m tarfile -e docs/experiments/main-sq/production-replay-seed509.tar.gz \
  artifacts/msq-portable-replay --filter=data
python docs/experiments/main-sq/analyze_trace.py \
  --run artifacts/msq-portable-replay --output artifacts/msq-portable-audit
python -m unittest discover -s docs/experiments/main-sq -p test_trace_analysis.py
python docs/experiments/main-sq/plot_diagnosis.py \
  --audit docs/experiments/main-sq/data/production_audit.json \
  --output docs/experiments/main-sq
```

The archive hash must match above. Every payload file is covered by `BUNDLE_MANIFEST.json`;
the archive SHA256 also protects the manifest itself.
Fresh extracted-bundle and original-directory audits agree on all statistics and paired
examples. Plotting uses installed Matplotlib3.10.0; it adds no RTL cycles. The archived
baseline CDF can also be regenerated with `python docs/experiments/main-sq/plot_baseline.py`
when the original HS-main artifact directory is present; that script verifies the accepted
input hashes before plotting. See
[verification](VERIFICATION_RESULTS.md) to rerun the expensive actual WSL RTL scopes only
when needed. No new SSH/FastX run is required to inspect this record.
