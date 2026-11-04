# Measurement and Diagnosis Evidence

Date: 2026-10-29 Asia/Taipei.
Scope: `MODEL_ONLY` and `SCHEDULER_RTL` measurement/diagnosis evidence for
FAI-inspired and CGOF. `REAL_CXL/APPLICATION` remains not run.

The public synthesis, including the current comparison tables and claim
boundaries, is [DIAGNOSIS_SUMMARY.md](DIAGNOSIS_SUMMARY.md).

## Current evidence status

| Evidence | Status |
| --- | --- |
| Equal-demand confirmation, seeds 6201-6220 | `PASS`, 180/180 jobs, 0 failures, source stable |
| Fixed-class confirmation, seeds 6201-6220 | `PASS`, 100/100 jobs, 0 failures, source stable |
| Finite-Heavy confirmation, seeds 6201-6220 | `PASS`, 300/300 jobs, 0 failures, source stable |
| Accepted scheduler RTL endpoint analysis | 960 accepted endpoints; scheduler-boundary only |
| CGOF W256 quota checks | 1:1 and 2:1 observed at the expected per-round quotas |
| Common-demand production RTL, seed 6201, three W5M windows | `PASS`, two quota settings, 0 failures, source stable |
| Finite-Heavy production RTL, seed 6201, mixed/isolated x two quota settings | `PASS`, four jobs, two pairs, source stable |
| Repaired finite-Heavy confirmation, seeds 529–548 | `PASS`, 80 jobs, 40 mixed/isolated pairs, one effective-High boundary per job |
| Current-source CGOF (2:1) trained replay | 30 runs, 60 A/B endpoints; 20-seed confirmation and two 5-seed readiness explorations |

Latest report integration: [October 29 release](../../final-report/update-20261029/revision-release.json), [theory and evidence](../../final-report/update-20261029/THEORY_AND_EVIDENCE.md). The repaired finite-Heavy confirmation supersedes the earlier one-seed-only status; the three-window common-demand case remains one seed.

Evidence roots:

- `artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/`
- `artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json`

- `artifacts/implementation/cgof-rtl-diagnosis/20261027T203657Z_1135/`
- `artifacts/implementation/cgof-rtl-diagnosis/20261027T195414Z_1179/`

The three confirmation manifests were independently verified with
`scripts/run_diagnosis.py --verify-manifest`. The summaries report
`source_stable=true`. Fairness is now measured at both the model and accepted
scheduler-RTL boundaries. Finite-Heavy completion and service gaps are
measured in the model and in twenty-seed RTL mixed/isolated confirmation. The latter crosses one W5M boundary with all sources remaining effective High. The RTL common-demand run covers three live-classifier windows at one seed; finite-work multi-window adaptation remains follow-up work.

## W256 smoke

The W256 run below is retained as a contract and plumbing check, not as
confirmation evidence.

```powershell
C:\ProgramData\anaconda3\python.exe scripts/run_diagnosis.py `
  --output artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z `
  --smoke --window 256 --heavy-work 20 --windows 1 `
  --seeds 6101 --profiles under near over
```

Evidence root:
`artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z/`

| Item | Result |
| --- | --- |
| Run status | PASS |
| Jobs | 27 expected / 27 completed / 0 failed |
| Matrix | 9 policies x 3 load profiles x seed 6101 |
| Source stability | true |
| Comparison records | 18 `NOT_RUN` (smoke disables inference) |
| Scope | `MODEL_ONLY`, `production_evidence=false` |
| Manifest digest | `5b25f6bca497165e497d58a8e667230081ae0b726c788dcd5240a0ee23304781` |
| Summary digest | `5a70ab871ae64d5481aa95697e288a5021eee248e9b746696fbc0fdf3a848627` |

File-level SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `manifest.json` | `FD3ADFAC90CB29AC358BB01748FB63D6DE4ACF88DC71C08EEDE27BD2AF634526` |
| `summary.json` | `22549FC0A84120A67B54FA00C22FBC0E00E965EB6C931DCC198F3C871FA62501` |

The manifest was independently verified with:

```powershell
C:\ProgramData\anaconda3\python.exe scripts/run_diagnosis.py `
  --verify-manifest artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z/manifest.json
```

That check returned `status: PASS` and the same manifest digest. The runner
checked source bytes again after the jobs; no source changed during execution.

## What the harness measures

The implemented model matrix recognizes the following metrics and guards:

- fairness: raw Jain, active-service Jain, demand-share L1/max error,
  weighted Jain/share error, and quota-share L1 error;
- latency: generation-to-acceptance, acceptance-to-fire, and
  generation-to-fire distributions, with per-run P99;
- Heavy work: finite-work completion ratio, mixed/isolated span and throughput
  ratios, active fire rate, and wall-clock/ready-opportunity service gaps;
- accounting: generated/accepted/fired conservation, pending work, censored
  samples, closing-cycle inclusion, backlog conditions, and avoidable bubbles;
- statistics: paired seed/run comparisons and 10,000-replicate paired bootstrap
  only after a complete declared non-smoke cohort.

`fire/cycle` is a scheduler model service rate. It is not measured memory
bandwidth. Generation-to-fire latency is not memory-response latency.

## Claim boundaries

- The smoke result is descriptive only. Its 18 comparison records are
  `NOT_RUN`, so it cannot support a policy ranking or a novelty claim.
- The model-only Heavy completion comparison is not a CXL application
  slowdown measurement.
- Common-demand and finite-Heavy RTL now pass at the scheduler boundary, but
  each has only one seed; neither is an application or calibrated CXL result.
- Real completed memory bandwidth, CXL issue-to-response latency,
  application slowdown, maximum application slowdown, and calibrated
  full-system validation remain **not run**.
- A W5M run requires `--window 5000000 --production-reviewed`; a W256 run
  requires explicit `--smoke`.
- If WRR/IWRR or eligible-RR controls explain an apparent sparse-latency gain,
  retain the diagnostic result and stop the algorithm-novelty claim.
- `artifacts/` is local evidence and must be preserved with the workspace; a
  clean Git checkout alone does not contain the raw run directories.

## Literature boundary

The source-verified comparison matrix and claim limits are in
[LITERATURE.md](LITERATURE.md). The mechanism comparison includes DRR,
WRR/IWRR, pFS, CCSP, FAI-CXL, and MemChannel. CGOF is evaluated here; the
project does not claim that the name or scheduler has been proven novel.
