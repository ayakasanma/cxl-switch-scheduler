# Instructor Review Brief

Read-only framing review of `main.tex`; line numbers refer to the current report. No RTL, results, or `main.tex` were changed.

## 1. Five grade-impacting objections

### P1. The title and abstract promise a CXL switch, but the evidence covers one arbitration slice
**Invited by:** title, `main.tex:39` ("CXL Switch Schedulers"); abstract, `main.tex:45` ("shared SystemVerilog switch framework", "complete switch cost"); Introduction, `main.tex:51` ("complete switch cost"); boundary, `main.tex:100` ("single-output baseline needs no destination-ID field or address-based memory selection") and `main.tex:62` (no transport, coherence, or link-credit engine).

**Why it costs grade:** A skeptical reader will treat "CXL switch scheduler" as a claim about a multi-port switch with routing, destinations, protocol handling, and contention across outputs. The design is actually an N-input, one-output descriptor arbiter with FIFOs. The report discloses this later, but the first impression is the overclaim.

**One-sentence repair:** Retitle and rewrite the abstract/opening as a "single-output descriptor-level arbitration slice for a CXL memory path," state in the first paragraph that no CXL transport, destination routing, or full switch is implemented, and keep "switch" only as context for where the slice would sit.

### P2. Related Work is a scope disclaimer, not a literature review
**Invited by:** Related Work and Scope, `main.tex:56` (FAI-CXL summary plus exclusion), `main.tex:58` (Algorithm-2 ambiguity), `main.tex:60` (BLISS as one paragraph), `main.tex:62` (frozen-specification scope); bibliography, `main.tex:347-349` (two external works plus the authors' artifact).

**Why it costs grade:** The section never establishes the CXL pooling/switch design space, the memory-scheduling lineage behind FCFS and RR, or the prior hardware-cost studies that make this comparison interesting. It answers "what did we not implement?" better than "what conversation does this join?" Three references, one self-citation, and one BLISS paragraph are thin for a final report.

**One-sentence repair:** Replace the section with the five-paragraph outline below, using peer-reviewed CXL pooling/switch work and memory-scheduler hardware studies, and end each paragraph with the precise gap this report addresses rather than another disclaimer.

### P3. "FAI-inspired Main" is neither a faithful FAI reproduction nor a fairness evaluation
**Invited by:** contributions, `main.tex:53` (distinction between two FAI interpretations); Related Work, `main.tex:58` (pseudocode-versus-prose ambiguity); policy definition, `main.tex:145` (10/10 one-output dispatch is a "project-defined assumption"); supplementary results, `main.tex:317-319` (single N=4 pair, -0.028626% area, run-to-run variation uncharacterized); Discussion, `main.tex:328-329` (no application fairness, IPC, or general fairness bound).

**Why it costs grade:** The primary baseline follows the prose's previous-effective-class hysteresis, while the paper's pseudocode is represented by a separate supplementary variant. Calling the primary design "Main FAI" invites the question "which FAI algorithm?", and the report has no fairness metric, no application workload, and only one N=4 comparison for the interpretation distinction. The honest answer is that this is an FAI-derived controller and an ambiguity study, not an FAI implementation or fairness result.

**One-sentence repair:** Rename the designs as "FAI-derived hysteresis" and "Algorithm-2-style variant," move the interpretation comparison out of the contribution list into a bounded case study, and state explicitly that neither variant reproduces FAI-CXL or establishes fairness.

### P4. "PPA" overstates a power experiment that never exercises adaptive behavior in the primary runs
**Invited by:** abstract, `main.tex:45` ("PPA" in the title, "Qualified activity-based power estimates preserve the ordering"); power method/results, `main.tex:263` ("No Main production window closes in these runs; all sources remain High"), `main.tex:274` (RR < FCFS < Main), `main.tex:294` (boundary sample has 50x the natural classification-event density and is not production-average power); Discussion, `main.tex:331-332` (zero-delay, no SDF, wire-load estimates, unmeasured trained-state power at N=8/16).

**Why it costs grade:** The cold-start matrix cannot support a scheduler-PPA conclusion because Main never classifies in it. The measured ordering is dominated by FIFO size, clocked storage, and leakage; the one warmed sample is deliberately event-enriched and only N=4. The report says this in the fine print, but the abstract and title still sell PPA.

**One-sentence repair:** Replace "PPA evaluation" with "area, timing, and qualified cold-start power estimates," remove the power ordering from headline claims or label it workload-specific, and do not present any power difference as evidence for or against adaptive scheduling.

### P5. The "identical datapath" and verification claims are stronger than the comparison actually is
**Invited by:** abstract, `main.tex:45` ("identical datapath and synthesis conditions"); Introduction, `main.tex:51` ("only the policy and its necessary metadata vary") and `main.tex:53` ("explicitly specified and verified common RTL framework"); parameter table, `main.tex:77` (RR omits 32 arrival bits per entry); results, `main.tex:236` and `main.tex:323` (total-area percentage is dominated by the FIFO denominator); verification, `main.tex:172` and `main.tex:174` (14 pairs support RTL/netlist equivalence, not English-specification correctness); timing, `main.tex:257` (140 untested checks remain).

**Why it costs grade:** "Only the policy varies" is false in the storage sense: RR deliberately has no timestamps, while FCFS and FAI pay for them. The 14 equivalence checks are useful implementation-consistency checks, but they are not 14 independent proofs of correctness, and one constant register per FCFS/RR case is explicitly not compared. The report knows this; the headline does not.

**One-sentence repair:** Rewrite the claim as "shared RTL shell and synthesis recipe, with policy-required metadata intentionally different," report whole-switch and policy-subtree deltas as separate diagnostics, and describe equivalence as "RTL-to-mapped-netlist consistency for specified pairs" rather than verification of the specification.

## 2. Are the contributions proportionate to the evidence?

**No as currently framed; yes only as a modest course-scale implementation study after reframing.**

The strongest evidence is the controlled nine-configuration area/STA matrix: one RTL shell, one SAED32 library/profile, N = 4/8/16, complete 105-bit descriptors, depth-16 standard-cell FIFOs, and visible setup/hold/electrical results. The report also does unusually good bookkeeping: it separates whole-switch from policy-subtree area, discloses that FIFOs occupy 92.40-98.63% of mapped area, reports 140 untested timing checks, and states that Main16 has only 1.158 ns of setup margin at 25 ns. That supports a reproducible **descriptor-level hardware-cost case study**, not a general CXL switch PPA result.

The contribution list is not yet proportionate because it leans on four items of unequal strength:

1. The common framework is real, but "verified" must be scoped to independent models, directed/random tests, and RTL/netlist consistency; it is not a proof that the English specification is correct.
2. The two-interpretation distinction is a legitimate observation, but the hardware evidence is one N=4 pair, one mapping, and a -0.028626% total-area difference with no run-to-run characterization. That is a small negative result, not a headline contribution.
3. The area/STA comparison is the paper's core and is proportionate to a course project; the 4.97-5.89% Main-over-FCFS and 38.22-39.27% Main-over-RR numbers are conditional on depth-16 standard-cell FIFOs and the frozen pre-layout flow.
4. The power work is exploratory. Three cold seeds, all sources High, no production window closure, no SDF, no routing/clock-tree power, and one event-enriched N=4 boundary sample do not support a PPA or energy-efficiency claim.

After retitling and deleting the PPA/FAI-reproduction implications, the defensible contribution is: a reusable single-output arbitration harness; a measured area/timing sensitivity study across source count; a documented FAI pseudocode/prose ambiguity with an N=4 hardware probe; and qualified cold-start power observations. That is enough for ECE 509 if presented as an implementation-and-measurement study, not as a new CXL scheduler or a full-switch evaluation.

## 3. Recommended five-paragraph related-work outline

Target: **910 words total** (within the requested 800-950 range). Each paragraph should end with a one-sentence "gap/delta" statement. Cite the artifact only as a reproducibility supplement, not as related work.

### Paragraph 1: CXL pooled memory and the switch context (about 160 words)

Define CXL pooled memory and the role of a switch in connecting hosts to shared Type-3 memory. Anchor with the CXL specification and the pooling systems already named by FAI-CXL (for example DirectCXL and Pond), then narrow from system-level pooling to the arbitration decision among request sources. Explain that a production switch must handle ports, virtual links, destination routing, coherence/ordering, credits, and multiple memory targets, whereas this report isolates one single-output descriptor scheduler. End with the gap: system papers establish why scheduling matters, but they do not isolate the standard-cell cost of the arbitration policy itself.

**Budget:** 160 words.

### Paragraph 2: FCFS, round robin, and memory-scheduling foundations (about 180 words)

Trace the baseline policies to memory-controller scheduling: FCFS/FR-FCFS uses arrival order and row-buffer awareness, while round robin uses a pointer and a service quantum to avoid starvation. Explain the hardware implications that matter here: FCFS needs arrival timestamps and an oldest-head comparator; RR needs a polling pointer and quota state; neither is free, and their metadata requirements differ. Cite FR-FCFS and a representative RR/QoS treatment, then connect to the report's FCFS and RR10 baselines. End with the gap: prior work compares performance under a memory-system model, not complete-switch area and timing under one RTL boundary.

**Budget:** 180 words.

### Paragraph 3: Fairness-aware and adaptive schedulers (about 210 words)

Move from static policies to class- or history-based adaptation. Summarize BLISS's argument that fairness mechanisms can impose logic, storage, and critical-path costs, and summarize FAI-CXL's windowed bandwidth measurement, priority adjustment, and cacheline-level interleaving. Explain why FAI-CXL is the closest anchor but not a numerical baseline: it is evaluated in ChampSim/Ramulator at system level, while this report implements a much smaller descriptor scheduler. Note the pseudocode/prose ambiguity in Algorithm 2 and the project-defined 10/10 one-output dispatch. End with the gap: there is little controlled evidence on how much of an adaptive scheduler's cost is policy logic versus FIFO-resident metadata, especially as source count grows.

**Budget:** 210 words.

### Paragraph 4: Hardware-cost and pre-layout evaluation methods (about 190 words)

Review how prior scheduler work justifies hardware claims: RTL synthesis, standard-cell area, critical-path or slack analysis, and activity-based power. Use BLISS as the anchor for treating area and critical path as first-class scheduler costs. Explain why denominator and boundary choices matter: standard-cell FIFOs can dominate total area; wire-load estimates and one corner are not APR signoff; zero-delay simulation omits SDF-dependent activity; cold-start power can miss trained behavior. Mention equivalence and independent models as consistency checks rather than proofs. End with the gap: a useful comparison needs a frozen flow, explicit boundary, and separated whole-switch versus policy-subtree accounting, which is what this report attempts.

**Budget:** 190 words.

### Paragraph 5: Synthesis, positioning, and precise gap (about 170 words)

Synthesize the three literatures: CXL systems motivate pooled-memory scheduling; memory-scheduler work motivates FCFS, RR, and fairness-aware policies; hardware-cost studies motivate controlled RTL/PPA measurement. State the narrow gap this report fills: a descriptor-level, single-output, pre-layout comparison of FCFS, RR10, and an FAI-derived hysteresis controller across N = 4/8/16, with policy-required metadata included and the FAI ambiguity exposed. State the boundaries in the same paragraph: no full switch, no CXL transport, no application fairness/IPC, no APR or multi-corner signoff, and only qualified cold-start power. End with a contribution sentence that matches the evidence: "a reproducible hardware-cost case study," not "a new CXL switch scheduler."

**Budget:** 170 words.

**Total:** 160 + 180 + 210 + 190 + 170 = **910 words**.

## 4. Claims to soften or delete

| Current claim | Location | Required change |
|---|---|---|
| "Hardware Implementation and PPA Evaluation of CXL Switch Schedulers" | title, `main.tex:39` | Replace "CXL Switch Schedulers" and "PPA Evaluation" with "Descriptor-Level Arbitration Schedulers for a Single CXL Memory Output" or equivalent; delete PPA from the title unless the abstract is reduced to area/timing plus qualified power estimates. |
| "shared SystemVerilog switch framework" / "complete switch cost" | abstract `main.tex:45`; Introduction `main.tex:51` | Say "shared SystemVerilog arbitration shell" and "single-output slice cost"; reserve "switch" for the surrounding CXL system. |
| "identical datapath and synthesis conditions" | abstract `main.tex:45` | Say "shared RTL shell and synthesis recipe"; explicitly note that policy-required metadata differs, especially RR's omitted timestamps (`main.tex:77`). |
| "Main FAI" | abstract `main.tex:45`; notation `main.tex:35`; Discussion `main.tex:328` | Rename to "FAI-derived hysteresis" or "Main hysteresis variant"; do not imply a faithful FAI-CXL implementation. |
| "fairness-aware" | abstract `main.tex:45` | Use "fairness-oriented" or "FAI-inspired" and add "no fairness metric or application-level fairness result is reported." |
| "All nine primary configurations meet setup, hold, and electrical constraints" | abstract `main.tex:45`; Results `main.tex:253` | Say "no setup, hold, or original-limit electrical violations were reported at 25 ns under the frozen pre-layout profile"; avoid the signoff-like word "closure." |
| "14 RTL/netlist equivalence checks support correctness" | abstract `main.tex:45`; contributions `main.tex:53`; verification `main.tex:172-174` | Say "14 specified RTL/netlist pairs support implementation consistency"; state that equivalence does not prove the English specification and that one constant register per FCFS/RR case is not compared. |
| "Qualified activity-based power estimates preserve the ordering RR < FCFS < Main" | abstract `main.tex:45`; power results `main.tex:274` | Keep the number but label it "cold-start, all-High workload, three seeds"; add that it reflects FIFO/leakage and does not measure adaptive-scheduler efficiency. |
| "production-length classification tests" | abstract `main.tex:45` | Say "full-window classification regressions" or "production-window-length tests"; the claim is about window length, not production workload coverage. |
| "Algorithm-2 ... negligible total-area impact" | Conclusion `main.tex:340`; results `main.tex:317-319` | Say "a 0.028626% total-area difference in one N=4, single-run mapping"; delete "negligible" as a general conclusion and note that N=8/16 and run-to-run variation are unmeasured. |
| "The final report replaces the planned outcomes in the first progress report with actual accepted evidence." | Introduction `main.tex:53` | Delete; it is course-process commentary, not a technical contribution, and it invites scrutiny of milestones rather than the work. |
| "The resulting contribution is a reproducible, evidence-backed descriptor-level implementation study." | Conclusion `main.tex:340` | Keep only if "reproducible" is qualified by the external university libraries/EDA licenses (`main.tex:335`) and the narrow single-output boundary. |

## 5. Three likely demo questions and defensible answers

### Q1. "Where is the CXL switch? You have one output, no destinations, and no protocol engine."

**Answer:** Correct: the synthesized boundary is a single-output arbitration slice, not a full CXL switch. The report explicitly excludes CXL transport, coherence/link credits, destination routing, and a real DRAM model (`main.tex:62`), and the single-output baseline needs no destination-ID field (`main.tex:100`). The contribution is the controlled cost of the scheduler and its required metadata, not switch compliance.

### Q2. "Is your Main design actually FAI-CXL's Algorithm 2, and why should I trust the comparison?"

**Answer:** It is not claimed to be cycle-identical. The paper's pseudocode assigns the target class on buffer entry, while the prose describes preserving the previous priority; Main follows the prose's previous-effective-class hysteresis, and the supplementary variant follows the pseudocode's immediate target-class behavior (`main.tex:58`, `main.tex:143-145`). The 10/10 one-output dispatch is a project-defined reconstruction. The defensible claim is that the report exposes the ambiguity and measures one N=4 consequence, not that it reproduces FAI-CXL.

### Q3. "Main has the highest power and the tightest timing. Why would anyone choose it?"

**Answer:** This report does not claim that anyone should. The cold-start power ordering is measured under an all-High workload where Main never classifies (`main.tex:263`), and the values include FIFO/clocked storage and leakage rather than incremental scheduler energy (`main.tex:276`). Main's N=16 setup margin is 1.158 ns at 25 ns, and FIFO subtrees are 92.40-98.63% of area (`main.tex:236`, `main.tex:253`). The result is a cost boundary for follow-on system-level study, not a performance or energy recommendation.

---

**Bottom line:** The report is technically careful and already discloses most limitations, but its framing still sells a full-switch PPA result and an FAI reproduction. Retitle it, narrow the claims, replace the related-work section, and the evidence becomes proportionate to a solid ECE 509 implementation case study.
