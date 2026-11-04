# Evidence supplement for the October 28 report revision

This supplement accompanies `main-v3.tex`. It records provenance and implementation qualifications that support the paper's methodology and results. It does not add experimental observations. Final compilation and editorial acceptance are recorded separately in `REVISION_QA.md`.

## Evidence populations

| Population | Experimental unit and source | Use in the report |
| --- | --- | --- |
| Accepted 498-row matrix | 489 performance jobs and nine power pairs (18 A/B captures); `../generated/revision_v3_evidence_manifest.json` | Original confirmation, sensitivity, expansion, and baseline power |
| N4 confirmation | Paired seeds 529-548; seven policy endpoints; nearest-rank run-P99 averaged across runs | Sparse generation-to-fire waiting and paired policy contrasts |
| N8/N16 baseline expansion | Five exploration seeds 509-513; six baselines | Descriptive fan-in comparison; CGOF behavioral expansion is not supplied by this cohort |
| Existing RTL endpoint reanalysis | 960 endpoints from existing traces; `../../experiments/diagnosis-20261027/DIAGNOSIS_SUMMARY.md` | Additional service-share/gap descriptors; not 960 independent new runs |
| Model confirmation | Equal-demand 180, fixed-class 100, finite-Heavy 300 jobs; each family seeds 6201-6220 | Allocation controls and finite-Heavy diagnosis, separately from RTL |
| Common-demand production RTL | `20261027T203657Z_1135`; seed 6201; two CGOF weights; three W5M windows | Live-classifier service trace and measurement-phase shares |
| Finite-Heavy production RTL | `20261027T195414Z_1179`; seed 6201; mixed/isolated x two weights | Finite-work completion, Sparse waiting, and Heavy gaps at the RTL boundary |
| CGOF implementation matrix | Two weights x N4/N8/N16, D16/W5M; `../../experiments/diagnosis-20261027/CGOF_RTL_PPA.md` | Complete mapped area and timing under the common pre-layout profile |

The three model manifests have the recorded logical digests:

- Equal-demand: `dd4ccc8fc7c0861483dacba976b9933c4d7d8634ab28df2f89d8cb7d40509cde`.
- Fixed-class: `739a6704972d5c2c969157bea27b3360d90a54e0699ffc67738ffb9cbea78bea`.
- Finite-Heavy: `1f67b0a09ffccd8ccff0f9f1550edb871c8b2f9f040bc72dd1972a803360e84d`.

`agent-handoff.json` preserves the planning snapshot's file-byte hashes. The new `../generated/improvement_evidence_manifest.json` binds the data used to generate the revision's additional tables and figures. Logical manifest digests and file-byte SHA-256 values are different fields. The historical source hashes are retained when the paper itself changes.

## Definitions and controls

Generation, acceptance, and fire define per-request waiting stages. The stage sum holds request by request; marginal quantiles need not add. Mean run-P99 describes the arithmetic mean of run-level percentiles, not a percentile of the pooled request population.

Heavy and Sparse identify arrival roles. High and Low identify effective service classes. Main's `B_H` keeps effective High and `B_L` keeps effective Low. In both common-demand RTL weight configurations, the first recorded boundary is `[B_H, B_H, B_H, H]`; the next two are all `H`. These recorded states all provide effective High service. A state encoding change alone is not an effective class change.

Class quotas and per-source weights specify different allocation targets. The fixed-class model assigns one Low and three High sources. The 10/10 Main scheduler splits service between the two classes, while CGOF 1:1 and 2:1 allocate per-source credits. Fixed WRR/IWRR controls must be interpreted with their own source weight vectors. Raw Jain, demand-share error, and weighted Jain answer different questions.

Finite-Heavy completion ratios compare mixed with isolated work under the same policy. The existing model overload cohort and the single-seed RTL finite-work case use different workloads. Their endpoint values belong in separate panels/tables. A small numerical difference is reported as such; no equivalence test or application slowdown estimate is implied.

Independent source review established that the equal-demand and fixed-class models run for 20,000 active cycles. Finite-Heavy model lanes process 20,000 Heavy requests in 24,861-80,895 active cycles. Although W is configured to 5M, none closes a classification window; the live-classifier variants remain in their initial all-High assignment. The fixed-class experiment begins at L/H/H/H. These experiments isolate allocation before adaptation. Model overload uses Heavy/Sparse arrival probabilities 1.0/0.05 per Sparse source and sink-ready probability 0.9; production finite-Heavy RTL uses 0.8/0.02 and ready 0.9 with 5,000,000 Heavy requests.

The common-demand RTL producers have a generated-but-unaccepted backlog cap of 256 per source and throttle generation when full. The result describes bounded saturated producers. Sparse model P99 pools sources 1-3 within each run before taking the percentile, then averages over seeds. Heavy wall gaps are uncensored, FIFO-nonempty inter-service intervals during active measurement; consecutive fires have gap one, and sink stalls contribute. The new model table averages per-run maxima, whereas the old endpoint reanalysis reports a maximum across per-run maxima.

The equal-demand fixed-horizon model's `heavy_active_fire_rate` and `heavy_throughput_ratio_mixed_over_isolated` fields mix after-drain Heavy counts with an active-cycle denominator. They are excluded from the report; allocation uses active-phase fire counts. The finite-work ratios finish Heavy work before the cut and do not have that particular mismatch. The underlying metric implementation remains unchanged by this document task; the issue is retained for a future targeted repair.

## Hardware conditions and diagnostics

The primary library is SAED32 RVT at TT 0.78 V and 25 C. The shared clock constraint is 25 ns. Area includes descriptor storage, necessary ordering metadata, policy logic, and output control. Library cell area is separate from estimated interconnect area. The common wire-load and fanout estimates describe pre-layout implementation conditions.

The six CGOF area/STA configurations report zero timing violations. The 1:1 mapped-equivalence runs have 138/230/414 unread classifier-accounting DFFs at N4/N8/N16, respectively; the accepted scope is observable-boundary equivalence. The 1:1 proof logs also report 8/16/32 unmatched unread reference points optimized away at N4/N8/N16. These are distinct from the matched unread accounting DFFs; successful observable-boundary verification is not an all-register equivalence claim. The 2:1 N4 proof passes 9,126 compare points. The complete CGOF correctness matrix contains 463 tests, plus a separate 17-test model suite.

For N4, Main and CGOF 2:1 use matched profile/library/common-block bindings, with different top-level glue. Four AND2 push gates contribute 8.132608 library-area units of their full-design difference. The observed -0.268019% area difference is a complete-design comparison. The CGOF N4 reports retain 68 constant-disabled timing checks. Reported cell counts and expanded leaf counts have different counting conventions; the detailed area audit reconciles leaf area without double-counting hierarchy.

CGOF power is unmeasured. Existing baseline trained-power results use mapped-netlist zero-delay/no-SDF activity and an ideal clock at the shared 25 ns period. FCFS/RR static-pin table-range diagnostics and activity-coverage details are retained in the original evidence. Area/STA passing at one period does not establish maximum frequency or routed power.

## Deferred empirical questions

The five groups in `HYPOTHESES_AND_EXPERIMENTS.md` remain planned extensions: Buffer adaptation, allocation-versus-order controls, multi-seed/multi-window RTL replication, admission waiting, and calibrated system translation. Their predicted outcomes are not inputs to the paper's result tables. Future agents record actual supporting, mixed, negative, or inconclusive outcomes before adding related empirical claims.

## Reproduction boundary

Local raw artifacts and `.setup-logs` are required for regeneration; a Git-only checkout does not contain the full experimental archive. Proprietary libraries and EDA executables remain on the original licensed host. This revision uses the existing completed evidence and introduces no RTL or policy change.
