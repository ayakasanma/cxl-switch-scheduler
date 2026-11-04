# October 28 report revision: acceptance record

Date: 2026-10-28 (Asia/Taipei). Status: **ACCEPTED**.

The revised report follows the owner's five-step narrative: pooling contention; FAI and transitional Buffer; executable FAI-inspired RTL and paper differences; common measurement; results and applicability. The release is an 11-page English course report with seven figures, six tables and nineteen cited references. This acceptance covers the manuscript, evidence presentation and rendered artifact.

## Roles and actual execution

| Role | Model / execution identity | Delivered work |
| --- | --- | --- |
| Primary author | GPT-6.1 Sol/high, `01a18133-bdee-75a3-ac7d-854470d0a44b` | Complete five-section body and driver |
| Data and figures | GPT-6.1 Sol/high, `01a18133-c5b5-7493-824e-697ce2519023` | Evidence-bound tables; five editable SVG/vector PDF/PNG figures; generator tests |
| Independent evidence review | GPT-6.1 Sol/high, `01a18136-49a6-7620-b117-71bd001b8e86` | Raw-data and interpretation review of latest evidence |
| Editorial preparation | agy `gemini-3.8-flash-high`, high, conversation `cc8a39c6-641d-4417-99c3-faea38834c2f` | Completed brief; exit 0, 160.52 s |
| Full-draft language review | agy `gemini-3.8-flash-high`, high, conversation `1ccd2d69-42d5-44b6-94b7-18ed29cba063` | Isolated full-body edit; exit 0, 722.66 s |
| Orchestration and acceptance | Codex GPT-6 parent | Selective editorial acceptance, evidence interpretation, source integration, compilation, page inspection |

Both agy stream initialization events confirm the requested available model ID. The preparation invocation's unavailable `--mode auto` fell back to the CLI default; the final review omitted that option. Invocation-local model/effort settings were used. Prompts, streams, stderr, exit receipts, frozen Sol/Gemini drafts and diffs are retained under `.setup-logs/report-improvement-20261028/`. Author and figure scope receipts are [AUTHOR_HANDOFF.md](AUTHOR_HANDOFF.md) and [FIGURE_HANDOFF.md](FIGURE_HANDOFF.md).

ARS-Codex academic-paper revision and writing-quality guidance informed the narrative and editorial review. The authors consulted local Pond, CXL introduction, FAI-CXL, BLISS, STFM, Gupta/McKeown and Mandal WRR texts. Figure production used the Data visualize-data workflow and existing Matplotlib vector generation. The PDF workflow governed final rendering and inspection.

## Editorial adjudication

The parent retained Sol's scientific draft and selectively adopted Gemini's clearer descriptions of request waiting, shared capacity and priority allocation. The parent also clarified the memory-operation motivation, defined P99, improved sentence flow and removed repetitive equivalence disclaimers. The full Gemini rewrite was not substituted wholesale.

Specific rejected changes included KEEP becoming “no state transition” (Main cancels a pending transition on KEEP), nonreset windows becoming “active” cycles, trained Heavy arrivals becoming acceptance-dependent, an added burst-length interpretation, omission of held refill snapshots, credit-conditioned utilization denominators, dropped requests in a lossless/backpressured FIFO, physical-layout descriptions of cell area, total power becoming switching-only power, and general/near-optimal/unchanged-completion claims. Its assertion of 100% token preservation did not establish semantic fidelity and was not used as acceptance evidence. The earlier style brief's incorrect 28 nm library, invented FAI expansion and stateless RR examples were also rejected.

The accepted manuscript retains window terminology, precise generation/admission/fire semantics, source populations, arithmetic, result directions and measured scope. Model overload and near-load RTL have separate captions; the tradeoff figure contains model data only. A neutral results heading and connected explanations carry the argument. The acknowledgment records completed drafting, editorial review and parent acceptance.

## Professor feedback and evidence acceptance

| Requested improvement | Accepted implementation |
| --- | --- |
| Explain FAI and Buffer | Section 2 explains delivered service, thresholds, pending priority and cancellation with Figure 2. Buffer is distinguished from the request FIFO. |
| Explain CXL motivation and relation to packet scheduling | Section 1 connects pooling, convergence on shared paths, memory-operation waiting and hardware arbitration cost; acknowledges shared queueing mechanisms with packet switches. |
| Clarify original Section 4.5 | Section 3.2 is explicitly titled “FAI-Inspired Class Arbitration and Window Updates.” |
| Define controlled PPA comparison | Section 4.3 defines power, hardware timing and cell area, common constraints and complete storage/control costs; queueing is measured separately. |
| Incorporate completed latest results | Section 5 includes N4 confirmation, sensitivity, allocation controls, finite-Heavy model and production RTL, all six CGOF mappings and qualified baseline power. |

Independent review reconciled all E2–E5 numeric rows with their local raw artifacts. The accepted interpretation preserves the following:

- All short model controls finish before W5M; initial maps determine their allocation conditions. They do not establish learned demotion or Buffer performance.
- Three-window common-demand RTL uses bounded producers (256 generated-but-unaccepted requests per source). B_H remains effective High; active counts and final conservation are distinct.
- Fixed-horizon rate fields that mix drain counts with active denominators are excluded. The source defect remains recorded for future analysis; no model code was changed here.
- Model Sparse P99 averages run-level pooled-Sparse nearest-rank P99s; Heavy maxima use the stated uncensored active-gap estimator. Old RTL maximum-across-runs is separately identified.
- Model overload and single-seed near-load RTL differ in load, work and boundary count. N8/N16 CGOF results establish hardware cost/timing, while behavioral confirmation is N4.
- The six mappings use complete cell area and evaluated timing checks. Constant-disabled checks, unread-state equivalence qualifications and unmeasured CGOF power remain explicit.

Detailed conditions and the fixed-class 24.9962% rounding correction are in [EVIDENCE_SUPPLEMENT.md](EVIDENCE_SUPPLEMENT.md) and the figure handoff. H1–H5 retain their planned status and integration conditions in the separate hypothesis protocol.

## Validation performed

| Check | Outcome |
| --- | --- |
| Planning snapshot | All 52 source hashes matched at intake. At release only the intended driver/body differ; the other 50 pinned files remain unchanged. |
| Table/report suite | 10/10 PASS after final integration, 31.963 s, exit 0 |
| Figure suite | 5/5 PASS after final integration, 13.937 s, exit 0 |
| Manuscript structure | Five sections, seven included figures, six tables, 22 unique labels, 16 resolved cross-references; all 19 bibliography keys cited and all citations resolve |
| LaTeX | Two final PDFLaTeX passes, exit 0; no overfull boxes, undefined references, LaTeX or package warnings |
| PDF | 11 Letter pages; all pages rendered at 120 dpi and visually inspected; zero off-page text boxes |
| Final-layout recheck | Pages 1–5 and 9–11 re-inspected after final edits; pages 6–8 pixel-identical to previously inspected renders |
| Acronyms | ARS advisory checker run on extracted text; manually reviewed extraction/order/hyphenation flags. Technical definitions are present; policy/library/venue identifiers and UP/DOWN/KEEP are retained as names/state labels. P99 and DRAM were explicitly expanded. |

The figure suite covers source binding, raw histogram/count calculations, vector outputs and label scope. Full-width figures retain readable labels; paired figures/tables share placement, table captions appear in numerical order, and references use balanced columns. The installed `balance` package was used without installing new software. Ordinary underfull line-spacing notices were inspected; they are not hidden failures.

An initial PowerShell option-parsing failure produced no PDF and was repaired by passing arguments through Python subprocess with an absolute output directory. Preliminary unresolved-reference warnings were cleared by the final two-pass build. The figure unit's initial stale prose expectations were updated to the owner-authorized Main shorthand and new report structure; substantive data contracts were preserved. No failed check was waived.

## Release and follow-up

[revision-release.json](revision-release.json) is the current machine-readable acceptance record, output hash inventory and figure-to-manuscript map. The original [agent-handoff.json](agent-handoff.json) and two plans remain byte-for-byte frozen as reproducible generator inputs; their old status describes the planning snapshot. Agents load the release record before treating an old report hash or old NOT_APPLIED status as current.

No new RTL/model simulation, synthesis, STA, power or application experiment ran during this revision. H1–H5 remain planned; CGOF power and full-system response/application benefits remain unmeasured. This task did not independently reverify every external bibliography entry on the web or perform a venue-specific submission-format audit.
