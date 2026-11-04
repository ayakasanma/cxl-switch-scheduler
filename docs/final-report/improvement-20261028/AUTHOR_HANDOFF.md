# Primary-author handoff — frozen for parent review

Date: 2026-10-28, Asia/Taipei.

Status: AUTHOR SOURCE FROZEN. Parent may launch the final Gemini language edit on an isolated copy. No further writer changes are pending.

## Assigned files changed

- `docs/final-report/sections/hotnets-body-v3.tex`: complete five-section manuscript, approximately 4,450 prose words including abstract/acknowledgment and excluding floats/equations (simple source-token estimate). Seven full-width figures: all five improvement figures plus existing confirmation and sensitivity. All four assigned improvement table macros are used.
- `docs/final-report/main-v3.tex`: revised title/date/PDF metadata; includes `generated/improvement_results.tex`; preserves established LaTeX style and bibliography; updates version-specific references and artifact description.
- `docs/final-report/improvement-20261028/AUTHOR_HANDOFF.md`: this receipt.

No generator, test, generated-data, README, QA, handoff JSON, RTL, model, or other user file was written. An oversized initial shell write failed before execution; the manuscript was then written in bounded chunks. An initial bibliography replacement assertion stopped before saving main-v3.tex; it was corrected and checked.

## Narrative and evidence integrated

Exactly five sections: pooling contention; FAI purpose and Buffer; executable RTL; common comparison methodology; results and applicability. Results follow Main/baseline tails, allocation, Heavy/Sparse tradeoff, complete cost, applicability. H1–H5 remain future work expressed in ordinary prose without internal IDs.

E1–E5 are integrated. Main versus FCFS/RR10 and all seven N4 confirmation endpoints remain. Five-seed fan-in, sensitivity, adverse burst stress, backpressure, and retained-state adaptation are bounded to their original cohorts. Model allocation, finite-Heavy results, separate production RTL, six-config CGOF area/STA, complete primary area decomposition, and baseline qualified power are included.

Applied the independent review `.setup-logs/report-improvement-20261028/evidence-review.md`:

- Equal-demand/fixed-class models observe only 20,000 cycles; maps remain initial all High / L,H,H,H. Finite-Heavy models use 20,000 Heavy requests and finish before any W5M classification. No learned demotion, Buffer smoothing, or convergence is attributed to these results.
- Model overload and RTL near-load regimes are separate. Production finite RTL uses five million Heavy requests, one seed and one boundary B_H/H/H/H, still effective High throughout.
- Three-window common-demand RTL has first boundary B_H/B_H/B_H/H, all effective High, followed by all H. Producers suppress new generation at 256 generated-but-unaccepted requests per source. Reported G-to-F latency is explicitly conditioned on bounded producers.
- No erroneous fixed-horizon model rate fields are used. Completion ratios use inclusive active durations. Weighted WRR/IWRR source vector (2,1,1,1) is distinguished from fixed-class CGOF (1,2,2,2).
- Sparse P99 is mean per-run pooled-Sparse nearest-rank P99; gap instrumentation excludes censored/initial/emptiness-terminated intervals. Old RTL maximum-across-runs and model mean-of-run-maxima are distinguished.
- The 1:1 equivalence caption discloses both 138/230/414 matched unread accounting flip-flops and 8/16/32 unmatched unread reference points. Positive timing slack is scoped to evaluated pre-layout checks; CGOF power remains unmeasured.

## Citation/version handling

Actual local Pond introduction, BLISS observations/implementation/synthesis methodology, STFM abstract/introduction, FAI Section IV-C and Algorithm 2, Gupta scheduling contract, and Mandal WRR abstract/introduction were consulted. The existing BLISS entry was already the correct ICCD 2014 title, *Achieving High Performance and Fairness at Low Cost*, DOI 10.1109/ICCD.2014.6974655; it is preserved. Do not replace it with the different BLISS technical-report title/version.

Pond now cites the actual local arXiv:2203.00241v4 (October 21, 2022), explicitly identified as the ASPLOS 2023 preprint, avoiding conflation of the inspected version with proceedings metadata. Added Mandal et al., arXiv:2108.09534v2 (August 12, 2023), *Theoretical Analysis and Evaluation of NoCs with Weighted Round-Robin Arbitration*. This source is not Tabatabaee et al.'s IWRR paper. Existing other bibliography entries were preserved; no new external bibliographic verification was performed.

The frozen spec's historical statement that no local FAI PDF was available predates the actual local extracted full text. Current prose cites the observed Section IV-C/Algorithm 2 distinction without rewriting the historical spec.

## Checks actually completed

- At intake, every source_files SHA-256 recorded in agent-handoff.json matched current bytes (including manuscript base and evidence).
- Read AGENTS.md, both read_order plans, specification/approval/decision/review/status context, source summaries, selected original texts, editorial brief and independent evidence review.
- Read-only static assertions passed: exactly five numbered sections; citation keys resolve; reference labels resolve and are unique; LaTeX environments and braces balance; every input/figure path exists; all four generated macros resolve; all seven figures are figure*; no H1–H5 IDs in public prose.
- Manual first-use check expanded CXL, RTL, FIFO, FCFS, RR, CGOF, WRR, IWRR, PPA, STA, RVT, TT and SDF; N4/N8/N16 and D16/W5M notation is defined. Parent may run its standard acronym tool.
- No simulation, EDA, new experiment, test rerun, external model call, or external chat message was performed by this writer.

## Parent acceptance and compilation

All required generated inputs and figures exist at this handoff; source is ready for final Gemini language review and parent compilation. Parent owns final PDF compilation, float placement and page inspection. No PDF/build success is claimed by this writer. Keep model/RTL regime and aggregation distinctions intact during polishing, and review generated figure/table labels against the corrected captions.

The acknowledgment accurately records Sol/high drafting and Gemini 3.8 Flash/high editorial preparation. It labels final Gemini polish and parent acceptance review as planned. Update those statements only after their actual completion. Model designation follows the assignment; writer does not independently attest the orchestration runtime model field.

Frozen source SHA-256:

- main-v3.tex: `bd98ad1b2d62111983d85df406b31df1541c5362219e472b2b3deaad9707377f`
- hotnets-body-v3.tex: `832daf43d88d2efca58c7a958db8306bbaa03717e28c47c0ea80258e21adfcda`
