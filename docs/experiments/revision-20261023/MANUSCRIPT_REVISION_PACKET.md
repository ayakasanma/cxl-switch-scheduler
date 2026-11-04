# Manuscript revision approval packet

Prepared 2026-10-27 in the existing Sol/high scope. **PROPOSED CHANGES ONLY; manuscript unchanged.** This is author approval material, not an applied patch, publication-readiness certification, completed re-review, or new experiment. No new literature search or independent inspection of original papers is claimed.

## Target and checkpoint

**Revision3 applicability:** The494/56-of60 checkpoint and pending-N proposals below are preserved historical revision2 material. The appended **CURRENT498 / FULL60 SUPERSEDING ADDENDUM** governs every new manuscript claim and replaces the applicability of those pending-N instructions. All60 are now accepted; proposed target selection and final manuscript/manifest/PDF approval remain pending.

There are two distinct entry files. `docs/final-report/main.tex:53` includes `sections/hotnets-body.tex`; its historical abstract at `docs/final-report/sections/hotnets-body.tex:2` already correctly states Main's38.22–39.27% area premium relative to RR. Preserve that correct statement. Separately, `docs/final-report/main-v3.tex:54` includes `sections/hotnets-body-v3.tex`, the original review target. This packet **proposes main-v3.tex as a revision target**; it does not establish owner selection, designate it the current compiled default, or attribute v3's errors to the main.tex artifact. Target selection remains an unresolved approval decision; no user clarification is requested at this preparation stage.

In this packet, **B:Lx** means the exact current line x of `docs/final-report/sections/hotnets-body-v3.tex` only. All F1–F16 edit locations and proposed replacement passages below are conditional on approval of that proposed v3 target. Their hashes/excerpts are saved in the ignored evidence directory. They are not edits to `hotnets-body.tex`. McClintock's `E/final-evidence-gap-review-20261027/REVIEW.md` supplies the target reconciliation and confirms the historical manifest/PDF bindings are internally consistent; this packet does not diagnose corruption or an inverse-denominator error in the main.tex abstract.

The accepted checkpoint is **494 PASS /4 RUNNING /0 NOT_RUN /0 FAIL /0 UNRESOLVED**, from parent N16-25 adoption. N expansion is **56/60 accepted**: N8 sealed30 + prior N16 FCFS509 resource1 + N16 non-FCFS sealed25. The last four FCFS/N16 rows are not sealed/adopted. At this amendment the parent reports all four raw PASS and the runner finalizing, without the final seal; this is provided status, not a fresh queue inspection or acceptance. **Full60 analysis guard remains CLOSED.** Count resource1 once. Do not create a complete N16/FCFS comparison from unsealed raw results.

Older report introductions sometimes retain their original pending status. Use explicit later scope-matched adoption receipts and the current issue-ledger disposition for accepted status; retain earlier records as history. Conversely, a report's broad narrative does not supersede its raw scope. This packet does not update any shared status document.

## Approval order

1. **P0—correct material interpretation:** F1 denominator; F10 overall ranking; F6/F15 obsolete SQ/demand mechanism narrative; F9 confirmation vs exploration; F2/F14 proof scope. These affect abstract and conclusion as well as body text.
2. **P1—integrate accepted results:** F3 robustness and qualified partial N expansion; F4 adapted baselines; F5 service accounting; F7 sensitivity/depth; F8 area attribution; F11 timing limitations; F12 matched trained power; F16 evidence tiers.
3. **P2—release mechanics after approved edits:** F13 regenerate selected tables/figures/macros and evidence cutoff, then compile, inspect PDF, bind artifact hashes, and conduct independent re-review. Those actions are proposed, not performed here.

## Evidence registry

All paths are repository-relative. `docs/experiments/revision-20261023/` is abbreviated **R/**; `.setup-logs/implementation/revision-20261024/` is **E/**. `source-anchors.json` in `E/manuscript-revision-packet-20261027/` binds the inspected input hashes. The following are evidence scopes, not interchangeable global PASS statements.

| Key | Report / source anchor | Accepted scope and qualification |
| --- | --- | --- |
| C | R/CONFIRMATION_RESULTS.md; E/parent-continuation-20261025T0028/core-independent-arithmetic.json and dac-independent-arithmetic.json; E/parent-continuation-20261025T0410/heavy-share-check.json | Core120 and DAC20, seeds529–548, complete20-seed paired confirmation; finite synthetic N4 scope. |
| R | R/ROBUSTNESS_RESULTS.md; E/power-index/robustness-sealed-20261026t1518/release.json; E/parent-continuation-20261026T1518/robustness-index-adoption.json; current ISSUE_LEDGER F3/F6 narrative disposition | Core180 + DAC10 accepted; six core settings, only two DAC readiness settings; seeds509–513 descriptive. Strict release SHA256 `1fea76a9c574f2b47a3c6b94299f62748db0ad3d19cf80d341af13f082397af2`. |
| N | E/parent-continuation-20261027T0202/n8-adoption.json and n8-arithmetic-check.json; E/parent-continuation-20261027T0248/n16-25-adoption.json and n16-25-arithmetic-check.json | N8 all30 and N16 non-FCFS25 accepted; resource1 separate. N8 means available; N16 non-FCFS comparisons allowed only within complete same-policy cohorts. Full60 not adopted. |
| S | R/SENSITIVITY_RESULTS.md; E/power-index/sensitivity-20261025/release.json | Main-1W5, High-quota15, RR-quantum25, exploratory, unchanged defaults. |
| D | R/DEPTH_RESULTS.md; E/power-index/depth-completion-20261025t1022/statistics.json | D8/16/32 performance45; D8/D32 PPA not measured. |
| A | R/ADAPTATION_RESULTS.md; E/power-index/adaptation-results-20261025T1555/release.json; current ISSUE_LEDGER F6 | Nine retained-state role-switch RTL runs; three seeds, no separate training; whole-role latency is not a recovery-time distribution. |
| Q | docs/experiments/main-sq/BASELINE_DIAGNOSIS.md:128–180 | Actual production seed509 tag-linked replay; SQ1/SQ2 fixed-slot offline screens fail the stated benefit objective. Not SQ RTL results. |
| B | R/BASELINES.md, final source-complete acceptance section; R/METHOD_DIFFERENCES.md | Six-policy correctness36 lint/15 model/226 cocotb, source-complete run20261023T171608Z_276; explicit FAI/BLISS adaptations; novelty not established. |
| H | R/AREA_ATTRIBUTION.md; docs/ppa/primary-20261021-v2.json; scripts/revision_matrix.py source_chain arithmetic | Primary-nine complete cell areas and disjoint mapped-leaf attribution; library area units; count-definition residuals retained. |
| P | R/DAC_PPA_RESULTS.md; artifacts/fastx/revision-dac-ppa-20261023T190649Z/ | N4 DAC2 matched TT/25ns pre-layout PPA and equivalence to its own netlist. Not DAC2 trained power or physical signoff. |
| W | R/TRAINED_POWER_RESULTS.md; E/parent-continuation-20261026T0906/index-final18-adoption.json | Exact18 captures/9 A/B policy-seed rows, FCFS/RR10/Main, N4 seeds509–511. Policy-specific static and table-range qualifications retained. |
| F | docs/FORMAL_EQUIVALENCE_2026-10-21.md; docs/ppa/formality-20261021.json; artifacts/fastx/revision-bridges-20261023T185951Z/; current ISSUE_LEDGER F2/F14 | Historical14 scoped proofs retained; six later FCFS/RR bridges accepted; three current-Main bridges already retained; DAC own-netlist proof separate. No theorem of scheduling correctness. |

## F1—v3-only area denominator correction (P0)

**Exact targets:** B:L14–15, L61–63, L350–353, L386–389; denominator-bearing generated values in `docs/final-report/generated/results.tex:18–25`. L61 and L350 use the Main-over-RR denominator correctly; preserve those numbers while fixing the reversed statements at L14/L386.

**Entry-specific disposition:** This correction concerns the proposed v3 target, not the already-correct abstract loaded by `main.tex`. The active historical body's Main-over-RR statement must remain intact; do not mechanically replace its correct denominator because v3 contains the inverse error. Generated values require review only if their proposed revision use changes, not because an active-data defect has been established.

**Proposed replacement:** “Across N=4,8,16, Main's complete mapped cell area is38.22–39.27% above RR10; equivalently, RR10 is27.65–28.20% below Main. Main is4.97–5.89% above FCFS.” Use `(Main−RR)/RR` and `(Main−RR)/Main` explicitly in the calculation record. Remove “stronger overall” from this arithmetic sentence.

**Anchors/limits:** H. Cell area includes the complete common boundary and policy-required state. These percentages are neither selector-only costs nor physical-area reductions. The two denominator ranges cannot be substituted for one another.

## F2—source chain (P0)

**Exact targets:** B:L190–207 and L238–240; add source provenance after the implementation contract at L191–198. Historical data macros at `docs/final-report/main-v3.tex:16–17` must retain their own source identity until explicitly regenerated.

**Proposed replacement:** “The primary mapped source759f86b24f13ed5984c19034eeeea2ca43b0e971 and later performance sourcec8e7ea8c0e4530572b3abf5b14ea9958e24f1789 are not byte-identical. Retained Main N4/8/16 bridges and six accepted FCFS/RR N4/8/16 source bridges connect the specified later references to the original mapped implementations. New experimental cohorts retain their own exact source manifests and archived inputs.”

**Anchors/limits:** F, B, Q and each report's source closure. Common core canonical source digest `800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86` is distinct from a commit, matrix digest, source-ZIP digest, or mapped-netlist hash. Bridges support those exact parameter/source pairs, not re-synthesized PPA predictions or every newly added baseline's mapped implementation. Do not propagate old Main proof to DAC2.

## F3—workload and N scope (P1; full60 blocked)

**Exact targets:** B:L2–8, L36–44, L65–69, L217–240, L380–390. Insert robustness/N subsections after L309 without silently extending the original15-run denominator.

**Proposed replacement:** “Results concern synthetic equal-cost descriptor arbitration, not a full CXL memory system. Accepted N4 robustness covers six fixed perturbations across six policies and five exploration seeds. N8 has30 accepted runs. N16 currently has26 accepted runs, including one reused FCFS resource case and25 non-FCFS cases; four FCFS runs remain unsealed, so complete60-run N-expansion results are pending.”

**Numerical text available now:** N8 A/B mean run-P99: FCFS20.0/37.6; RR1 2.0/20.2; RR10 12.0/21.0; Main10.0/27.6; Algorithm-2 10.0/28.2; BLISS-inspired2.0/37.0 cycles. Main B is+6.6 cycles vs RR10. In accepted complete N16 non-FCFS cohorts, Main B34.8 vs RR10 24.4 retains a+10.4-cycle disadvantage. Do not construct a full N16 FCFS mean from resource509 plus three raw results.

**Anchors/limits:** N, R. At D16, moving N4→8→16 changes sparse source count3→7→15, aggregate expected sparse rate3/128→7/128→15/128, and total FIFO slots64→128→256. Heavy generation remains1/cycle; total offered generation expectation is131/128,135/128,143/128. No cross-N trace pairing, CI, or isolated scaling claim. Heavy-id3 permutes source0/3 from reset; it is not a retained-state role change. No new analysis or queue inspection is part of this packet.

## F4—baseline adaptations and novelty (P1)

**Exact targets:** B:L82–105, L190–207, L218–219. Add an explicit baseline-method table near L107 before presenting six-policy results.

**Proposed replacement:** “We compare FCFS, RR1, RR10, Main, the approved Algorithm-2 target-priority Buffer reconstruction, and a BLISS-inspired descriptor adaptation under one shared transfer contract. Main retains the previous effective class in pending states; Algorithm-2 uses its target priority. Neither reproduces the complete FAI-CXL system cycle-for-cycle. BLISS-inspired scheduling retains streak/reset and10000-cycle clearing conventions but replaces DRAM row-hit ordering with admitted-head age/source ID.”

**Anchors/limits:** B, C. BLISS change→counter0/repeat→increment/>4→blacklist implies first blacklist on the sixth fresh same-source service; clear/fire precedence is a declared project edge convention. No application IPC/slowdown or original DRAM result is reproduced. Replace B:L103–105's broad “no directly comparable” assertion with “Our comparison fixes this project's complete descriptor/FIFO/hold boundary; comparability to other systems is limited by their different interfaces and buffering.” Existing local method notes support attribution, not an exhaustive novelty finding. A literature/novelty assessment remains separate and is not performed here.

## F5—service, utilization and demand (P1)

**Exact targets:** B:L9–11, L130–144, L176–180, L326–345.

**Proposed replacement:** “Phase throughput is total fires / phase cycles. Eligible-ready utilization is total fires / ready cycles with a beginning-of-cycle nonempty local FIFO. Heavy-service fraction is heavy fires / all phase fires. These quantities have different denominators. Offered presentation cycles, generated requests, accepted requests, fired requests, local FIFO occupancy and external producer backlog are recorded separately.”

**Anchors/limits:** R, A, Q. Keep original ready-always saturated1.0 results scoped to those intervals; backpressure runs need not deliver1 fire/clock. All20 paired DAC/Main robustness A/B endpoints have zero bubbles and eligible-ready utilization1.0; maximum Main-minus-DAC heavy fraction0.006521880910454575 percentage points. Confirmation maximum0.001953125pp is a separate check below the predeclared0.01pp guard. Training backlog persists in heavy050/heavy090; those settings do not establish unsaturated low-load behavior. Measured heavy residual expectation1−3/128 is not normalized offered share128/131. No fairness guarantee follows from either ratio.

## F6—mechanism attribution and failed SQ remedy (P0)

**Exact targets:** B:L182–187, L283–295, L304–324, L393–394. Replace, rather than append to, the assertion that SQ is the justified direct next step.

**Proposed replacement:** “Tag-linked production replay supports shared-class quota interference in the diagnosed trained-B case, where the class map is already fixed and sparse admission has no FIFO-full events. It does not establish that fixed-visit within-High rotation remedies the tail. On representative seed509, actual Main pooled P99 is24 cycles; offline fixed-slot SQ1/SQ2 give24/25, observed max31→34/34, and source2 P99 21→28/29. Their prespecified benefit gate fails. These are offline screens, not new SQ RTL measurements.”

**Anchors/limits:** Q, S, A. Main-1W B20.8→21.0 in the matched exploration control does not show a steady-profile benefit. Earlier effective classification in retained-state adaptation does not lower whole-role sparse waiting: Algorithm-2/Main-1W mean sparse wait is higher than Main across all three roles. Do not infer a recovery-time distribution from whole-role histograms. Tail request-wait exposures overlap in wall time and must not be described as causal percentages of execution time. Keep the diagnosed observation separate from untested PW/BQ hypotheses.

## F7—sensitivity and frozen defaults (P1)

**Exact targets:** B:L150–152, L162–170, L217–240, L311–324; insert a sensitivity paragraph before hardware comparison L347.

**Proposed replacement:** “Prespecified exploration sweeps retain the default parameters. RR quantum1/4/8/10/16 and Main High quota5/10/20 produce profile-dependent tails. In the quota sweep, Main B mean P99 is32.2/20.8/17.0 cycles; A stays10.0. Main-1W A/B is10.0/21.0. These observations do not select a new default or establish a free benefit.”

**Anchors/limits:** S, D. Main-1W and Algorithm-2 have model pin-equivalent effective transitions at10/10; they are not independent mechanisms. D8/16/32 FCFS A P99 is10.0/18.2/35.2 and B23.4/33.8/51.6; RR10 sparse P99 stays11.0/17.2, Main A stays10 and B20.6/20.8/20.8. Depth changes admission history as well as storage. No tuning, exploration CI, depth-area optimum, or D8/D32 hardware claim.

## F8—whole area and disjoint attribution (P1)

**Exact targets:** B:L17, L62–63, L112–115, L347–363, L392–393; `docs/final-report/generated/hardware_cost_v2.tex:12` and caption at L57–65; `generated/results.tex:18–25`.

**Proposed replacement:** “Complete mapped cell area includes descriptor storage, ordering metadata, policy logic and common logic. A separate disjoint leaf audit attributes each mapped instance once; the legacy FIFO-subtree92.40–98.63% includes metadata and control and is not a descriptor-bit-only fraction. At N16/D16, descriptor storage is26880 bits; FCFS/Main additionally retain8192 timestamp bits, whereas RR omits unnecessary ordering state.”

**Anchors/limits:** H, P, D. Nine historic designs reconcile540590 expanded leaves with zero unresolved ownership, within printed-area precision. Preserve cell-count-definition residuals rather than silently equating tool number_of_cells to leaf counts. DAC2 N4 whole cell area109794.784709 vs Main110089.845892 (−0.2680185%) and+3 registers is a complete-design observation, not isolated credit logic savings. Keep library units, hierarchy-vs-leaf accounting, and whole-boundary charges; D8/D32 PPA absent.

## F9—confirmation and sampling unit (P0)

**Exact targets:** B:L5–8, L36–50, L218–219, L242–260, L263–309, L380–386; obsolete five-seed macros `generated/hog_sparse_results.tex:47–70` and figure inclusion B:L273.

**Proposed replacement:** “Seeds509–513 are exploration; confirmation uses frozen parameters and20 new seeds529–548. Each run contributes one pooled-sparse generation-to-fire nearest-rank P99 per arm. Paired differences use the same seed/intended trace; sources, requests and A/B are not independent repetitions. Intervals use the declared10000 paired-seed bootstrap resamples and RNG20261023 only for complete confirmation cohorts.”

**Ready replacement table:**

| Policy | Confirmation A mean run-P99 | Confirmation B mean run-P99 |
| --- | ---: | ---: |
| FCFS | 18.10 | 33.45 |
| RR1 | 2.00 | 16.65 |
| RR10 | 11.00 | 17.70 |
| Main | 10.00 | 21.05 |
| Algorithm-2 | 10.00 | 21.35 |
| BLISS-inspired | 1.15 | 33.00 |
| DAC2 | 1.10 | 12.35 |

**Ready paired wording:** Main−FCFS A−8.10 [−8.25,−8.00], B−12.40 [−13.25,−11.55] cycles; Main−RR10 A−1.00 [−1.00,−1.00], B+3.35 [+2.25,+4.45], with B improving only1/20. DAC2−Main A−8.90 [−9.00,−8.75], B−8.70 [−9.50,−7.90],20/20 improve each. Brackets are existing paired95% confirmation intervals; no new interval is calculated here.

**Anchors/limits:** C. Preserve original five-seed findings as historical/exploratory if retained, with their own figure/table labels. Do not replace only prose while leaving generated5-seed figures as apparent confirmation. Do not add stage quantiles or merge cohorts into a request-level confidence interval.

## F10—retain negative results; remove overall winner (P0)

**Exact targets:** B:L14, L20–21, L52–54, L65–69, L297–309, L385–394.

**Proposed replacement:** “Policy tradeoffs depend on workload, service target and implementation cost. Main improves sparse tails over FCFS in the default trained confirmation cohort, but its B mean run-P99 exceeds RR10 by3.35 cycles. In burst32 exploration, Main B88.8 vs RR10 74.4 is+14.4 cycles, and Main also exceeds FCFS87.0 by1.8. N8 Main B27.6 vs RR10 21.0 and accepted partial-N16 Main B34.8 vs RR10 24.4 retain the same direction. No workload weighting defines an overall winner.”

**Anchors/limits:** C, R, N. DAC2's N4 improvement is a different allocation policy, not retroactive evidence that unmodified Main wins. Lower area, single-arrival P99, burst P99 and entitlement targets must be reported independently. Do not claim final N16 comparison completion or full60 adoption.

## F11—timing/PPA boundary (P1)

**Exact targets:** B:L18–19, L60–61, L209–215, L348–353, L365–371, L391; `generated/hardware_cost_v2.tex:57–65`.

**Proposed replacement:** “The nine primary mapped designs meet evaluated setup, hold and electrical checks at25ns under the common SAED32 RVT TT0.78V/25°C pre-layout wire-load profile. The140 constant-disabled primary checks remain disclosed. DAC2 N4 meets the matched profile with setup/hold slack+10.398800/+0.038578ns; its68 propagated-constant-disabled checks remain untested checks.”

**Anchors/limits:** H, P. No APR, routed/extracted parasitics, clock-tree, multicorner/PVT or physical signoff;25ns closure is not Fmax. Keep required metadata/common storage and constraints in comparisons. Do not add the DAC disabled checks to the primary count or call rounded coverage100%.

## F12—trained power with retained qualifications (P1)

**Exact targets:** B:L56–57, L214–215, L373–375; `generated/hardware_cost_v2.tex:60–65` and cold macros `generated/results.tex:27–51`. Add a separate trained-power table; preserve cold/boundary panels as distinct historical experiments.

**Proposed replacement:** “Matched trained-power estimates cover FCFS/RR10/Main, N4/D16, seeds509–511 and separate A/B windows. Mean total A/B estimates are FCFS3.35600/3.35600mW, RR10 2.55967/2.56000mW and Main3.46667/3.46600mW. These are descriptive arithmetic means of printed estimates, not confirmation intervals.”

**Anchors/limits:** W. A measures100000 cycles/2.5ms after actual10M training; B measures102400/2.56ms after replaying training+A+1024 guard. Units are printed W, converted to mW; use all18 component rows/ranges from W for the detailed table. TT/25ns zero-delay/no-SDF pre-layout estimates include clock internal power. FCFS/RR qualified table-domain check_power warnings are not clean checks. Constant-leaf gaps FCFS32/Main34 and disabled arcs64/68 remain qualified; RR has no such constant gaps. Proven disconnected always-X paths are exact15/1/56 for FCFS/RR/Main; they are not newly accepted unknown activity. No transient X/Z is accepted. Different mapped topology/cell mix prevents attributing all power differences causally to policy. No energy/request, glitch or physical signoff claim. DAC2 trained power is not among these18 captures. Preserve original SSH255 transport history versus recovered actual EDA0; detached launchSSH0 is not EDA0.

## F13—artifact cutoff and reproducibility (P2)

**Exact targets:** `docs/final-report/main-v3.tex:18` PDF subject and L51 date; `docs/final-report/generated/evidence_manifest.json:2–4`; `docs/final-report/QA.md:45–58` and L95; B:L235–240 and L396–402.

**Proposed replacement:** “This revision distinguishes historical exploration, accepted confirmation/robustness and currently incomplete N expansion. Every reported cohort binds exact source, trace, configuration, result and archive hashes; proof and hardware artifacts retain their own scopes.” Replace cutoff/date only with the actual approved final revision cutoff, not this packet's preparation date or an anticipated full60 date.

**Anchors/limits:** C/R/N/W and their releases. After authorization, regenerate affected macros, plots and evidence manifest from selected accepted inputs into a fresh release; retain earlier versions and failures. Then compile and record actual PDF hash/page count plus visual QA of tables, figures, references and text. Do not claim current QA covers new data or that HEAD alone proves reproducibility. AI disclosure must reflect actual historical contributors and new Sol/high work; no Opus run is performed for this packet. No PDF build, citations verification or visual QA is performed here.

## F14—formal proof language (P0)

**Exact targets:** B:L18–19, L200–207, L321–323, L391.

**Proposed replacement:** “Scoped RTL-to-mapped-netlist equivalence checks support fidelity of identified implementations under recorded parameters and setup. They do not prove the scheduling specification, fairness target, workload validity or measured benefit. Historical14 scoped pairs, their propagated-constant exclusions, later six FCFS/RR source bridges, and the DAC2-to-own-netlist proof are reported as distinct evidence sets.”

**Anchors/limits:** F, P. DAC2 has9126 passing compare points (112 outputs+9014 registers), not another scheduling theorem. Do not invent an aggregated proof count without enumerating unique pairs and reconciling overlaps. Independent Python models, directed/random simulation, model-negative controls and formal equivalence each retain separate roles.

## F15—DAC allocation, screen and actual RTL evidence (P0)

**Exact targets:** B:L155–180, L185–187, L311–324, L393–394. Replace the unexecuted SQ/PW/BQ advancement narrative with the actual screen disposition and candidate.

**Proposed replacement:** “The approved MODEL_ONLY screen selected DAC2 for one bounded RTL implementation after its stated validation and feedback gate. DAC2 allocates service using locally active FIFO heads and declared2:1 weights; these are entitlement choices, not estimates of all upstream demand. Actual N4 confirmation reduces sparse P99 from Main10.00/21.05 to DAC2 1.10/12.35 cycles. Paired backpressure exploration gives Main→DAC2 A17.2→5.0/B32.6→20.4 under Bernoulli0.75 and A26.0→17.0/B34.0→27.0 under periodic48/64, five of five improve in each group.”

**Anchors/limits:** C, R, B, P, R/MODEL_SCREEN.md and R/DAC_RTL.md. Three active High/one Low weighted targets are2/7 per High,1/7 Low, not equal shares. TB-only producer backlog is not a selection input. MODEL_ONLY selection/AGE failures, literal model ablations, actual RTL benefit, correctness, mapped PPA and power are separate claims. Reuse approved thresholds; do not invent a new robustness gate or assert receiver-credit/UET protocol conformance. Original RCCC/NSCC version anchors in METHOD_DIFFERENCES are historical inspiration, not a new standards review.

## F16—production/pilot/intervention separation (P1)

**Exact targets:** B:L162–167, L196–207, L221–240, L291–295, L311–324; AI responsibility statement L401–402.

**Proposed replacement:** “W256 pilots establish infrastructure/sensitivity evidence only. Production W5M classification evidence uses actual window-closing fires and independently checked literal transitions. The retained Algorithm-2 production20M/four-window and Main production/stall evidence remain valid within their own contracts. Continuous role-switch adaptation is a separate30M-cycle retained-state experiment with training_cycles=0, despite generic '-trained' filenames.”

**Anchors/limits:** A, B, Q, docs/phase-5-verification/M6-long-results.md. Adaptation starts source0 heavy, switches0→3 at10M and returns at20M, without reset/drain between roles; static heavy-id3 robustness does not substitute for it. Earlier class changes do not imply faster measured recovery or better whole-role sparse latency. Full60 guard remains closed until parent adopts the last four sealed rows; raw PASS files are not sealed group acceptance. Neither preserved failures nor a new model screen should be relabelled an accepted RTL intervention.

## Proposed abstract/conclusion claim spine (author approval needed)

Use this content to replace the contradictory abstract/body/conclusion together, rather than silently editing only the abstract:

> In a common single-output descriptor switch, arbitration changes sparse waiting while service capacity and complete hardware costs remain explicit. On twenty frozen-parameter N4 confirmation seeds, Main lowers mean run-P99 relative to FCFS by8.10 cycles for independent sparse arrivals and12.40 for bursts, but its burst P99 exceeds RR10 by3.35 cycles. The separately allocated DAC2 policy lowers Main's corresponding P99 by8.90 and8.70 cycles under this synthetic workload. Exploratory robustness retains unfavorable Main burst cases. Main's mapped area is38.22–39.27% above RR10, equivalent to RR10 being27.65–28.20% below Main. Timing, equivalence and matched trained-power estimates support only their declared pre-layout/source scopes, not system-level benefit or physical signoff.

**Historical revision2 wording, no longer applicable to a new manuscript:** “N8 is complete; N16/FCFS and the full60-run expansion remain pending adoption.” Revision3 must instead use the adopted full60 results in the superseding addendum. The approved choice may retain the historical five-seed abstract as a separate earlier version, but it must not present it as the revised twenty-seed study.

## Approval decisions and release checks

The author can approve P0 claim corrections and the listed P1 insertions with the revision3 full60 addendum, and select a fresh publication cutoff/release. Full60 evidence is no longer deferred; selecting the manuscript target and applying/releasing the revision still require approval. Approval of this packet is not implied by its existence. Literature novelty and final venue framing remain author decisions; this local packet supplies no new citation validation.

Before actual manuscript revision: bind this packet and both entry/body hashes; select and approve the actual target and exact replacement scopes; preserve correct existing claims and prior files; regenerate coupled figures/macros only for the approved revision; verify all numbers against selected accepted cohorts; keep the negative Main findings; rebuild/visually inspect the final artifact; obtain independent review. No final-report source, generated data, PDF, DEVELOPMENT_REPORT, ISSUE_LEDGER, EXECUTION, frozen analysis, simulator or SSH state is changed by this packet.

Evidence directory: `E/manuscript-revision-packet-20261027/` contains the current source excerpts/line map, source anchors, denominator check, before/after hashes, bounded local selfcheck and release. It records a harmless initial manuscript-inventory failure on an inaccessible existing virtualenv link; the inventory was narrowed to manuscript/source/document files without altering the link or any input.

## CURRENT498 / FULL60 SUPERSEDING ADDENDUM

Revision3, 2026-10-27. This addendum supersedes only the applicability of historical pending-N statements in the Target/checkpoint, evidence registry N, F3, F10, F16 and proposed abstract/conclusion instructions. It does not erase the revision2 checkpoint or authorize manuscript edits. Exact revision2 packet/release/evidence-manifest bytes are retained in `E/manuscript-revision-packet-20261027/archive-revision2/`.

**Current accepted evidence:** final strict matrix **498 PASS /0 RUNNING /0 NOT_RUN /0 FAIL /0 UNRESOLVED**; full N expansion **60 unique accepted runs /120 A-B endpoints /24 cohorts /8 same-N pairs**. Count the prior N16 FCFS509 resource case exactly once: resource1 +N8 accepted30 +N16 non-FCFS25 +N16 FCFS510–513 four =60. Numeric analysis and `N_EXPANSION_RESULTS.md` are now parent-adopted after independent no-findings review. New manuscript N claims must use this complete accepted evidence, not the historical56/60 or unsealed-four checkpoint.

| N | Policy | A mean run-P99 (cycles) | B mean run-P99 (cycles) |
| ---: | --- | ---: | ---: |
| 8 | FCFS | 20.0 | 37.6 |
| 8 | Main | 10.0 | 27.6 |
| 8 | RR10 | 12.0 | 21.0 |
| 16 | FCFS | 22.0 | 41.8 |
| 16 | Main | 10.0 | 34.8 |
| 16 | RR10 | 13.0 | 24.4 |

**Replacement for the historical F3 pending-N proposal:** “The complete accepted N-expansion experiment covers N8/N16, six policies and five exploration seeds509–513, sixty unique runs. At N16, FCFS/Main/RR10 mean run-P99 is22.0/10.0/13.0 cycles in A and41.8/34.8/24.4 in B. Main B improves over FCFS by7.0 cycles but remains10.4 cycles above RR10. N8 Main B27.6 versus RR10 21.0 retains a6.6-cycle disadvantage. Main has0/5 improved B seeds versus RR10 at both N values.” Full six-policy tables and all24 cohorts/8 pairs remain in the adopted report and bound analysis, rather than being re-estimated in this packet.

**Replacement abstract/conclusion N sentence, if N results are included:** “The complete N8/N16 exploration retains the profile-dependent tradeoff: Main's burst mean run-P99 exceeds RR10 by6.6 and10.4 cycles, respectively.” Keep confirmation Main B+3.35 and burst32+14.4 disadvantages elsewhere as already proposed. Do not call Main or RR10 an overall winner.

**Limits remain unchanged:** paired statistics compare policies within the same N/seed/arm/intended trace;509–513 are exploration, no CI or cross-N trace pairing. N changes aggregate sparse load (N−1 sources at1/128 each), competition and FIFO storage (N×16 slots) together. All120 measured phases have zero avoidable bubbles and eligible-ready utilization1.0 with separate fire/eligible/ready/cycle denominators; this is not general link utilization or complete producer-demand observation. No DAC2 N8/N16 performance, new hardware-cost experiment, physical signoff or causal scaling claim is authorized by these data.

**Exact adoption and source bindings:**

- `E/parent-continuation-20261027T0325/final498-adoption.json`, SHA256 `16445cbcbcc10be603e619405fd7c170605c3c0694398a88bb30b2b387f430c4`.
- `E/power-index/final498-20261027/snapshot/index/matrix-coverage.json`, SHA256 `1defb1bbebe31948b5a2834e3510bfcda660190a8630732593bb2169c462f668`.
- `E/parent-continuation-20261027T0325/n60-report-adoption.json`, SHA256 `54ab9d38df70a6efdb22cccfc5c14781c8e4751f46109af31130e40e1d05a33f`.
- `R/N_EXPANSION_RESULTS.md`, SHA256 `e64149b686c8b326f6baa4881108c2d9abff59ddc8e8c07bf74f03c383dc0e7c`.
- `E/n-expansion-analysis-20261027/full60-output/analysis.json`, SHA256 `c196865abf056e552a380bcfd461bd8acec421f8e177c8c6644e7d5718639786`.
- `E/n-expansion-analysis-20261027/full60-release.json`, SHA256 `c6255e142c21750d2ed6c4c19ad3b561ff342116f38666772c260c984a5689e7`.

**Concrete approval scope:** main-v3 remains a proposed, conditional revision target, not an owner-selected/current compiled default. Preserve `main.tex:53` → `hotnets-body.tex` and its correct Main-over-RR abstract; v3-only F1 correction remains scoped as above. A new manuscript must integrate accepted full60 evidence rather than defer it. Final claim-to-evidence manifest, selected generated tables/figures, manuscript revision, compiled PDF/hash/page count/visual QA and independent postrevision review are still **PENDING APPROVAL / NOT PERFORMED**. Final498 and report adoption do not imply paper adoption or permission to edit either manuscript entry. This amendment performs no new analysis, analysis tests, simulation, SSH or manuscript write.
