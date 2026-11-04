# CXL Scheduler Spec v1.0 — Approved Baseline

**Revision:** v1.0, approved 2026-10-13 (Asia/Taipei), derived from RC1 commit a518e1e.

**State:** APPROVED — Project owner, Option A. Primary baseline: FCFS, RR, FAI-inspired Main; approved supplement: FAI Algorithm-2 variant.

**Implementation gate:** OPEN for the controlled Claude Code implementation/verification milestones. Approval is not progress: at specification freeze, RTL/models/tests remain NOT_STARTED and scheduler checks/PPA NOT_RUN. Follow the current execution record in docs/STATUS.md.

## 1. Authority and source evidence

This release derives from RC1 at a518e1e and the owner's direct Option A approval on 2026-10-13, called **S3** below and summarized in docs/SPEC_REVIEW.md. S3 resolves Q1–Q3, approves the Main/Algorithm-2 distinction, mandates at least 31-bit widened unsigned threshold arithmetic and the common RTL framework, and retains nonarchitectural RC defaults. The earlier [reconciliation request](../docs/sources/USER_RECONCILIATION_REQUEST_2026-10-13.md) is **S0**. Prior-document provenance remains distinct from the later release approval.

The original CXL Scheduler Revised Proposal and ECE509 First Progress Report are not present locally or in the supplied attachment directory. Their contents are known here through S0's account only. No original page numbers, direct quotations, complete source inspection or original-document dates are claimed. [SPEC_REVIEW.md](../docs/SPEC_REVIEW.md) records this limitation.

Decision categories and their history are in DECISIONS.md. Previously proposed nonarchitectural defaults below are retained by S3 as approved project defaults, not as paper-defined behavior. No unresolved correctness-critical question remains in this frozen baseline.

The approved full descriptor supersedes an older Tag-only proposal. Prior-report claims that FCFS/RR were implemented or verified are not local project evidence. At specification freeze no scheduler implementation or result exists; current progress is recorded separately in docs/STATUS.md.

## 2. Confirmed baseline and scope

USER_CONFIRMED by S0 section 1 and earlier direct messages:

- N means request sources, with primary values 4,8,16.
- D=16 FIFO entries per source; M=1 Memory Output.
- Full105-bit descriptor: Tag32, Address32, Opcode1, Length8, Payload32.
- Equal-cost atomic descriptor service, with at most one completed output transfer per cycle. Length does not increase service cycles or quota cost.
- Compare FCFS, RR and FAI-inspired in nine primary synthesis configurations.
- Response generation and tag matching stay in the Testbench; response latency is outside scheduler service accounting.
- No destination-memory ID is added to the descriptor; M=1 is the implicit sole destination.
- Local verification uses WSL Verilator/cocotb; commercial synthesis/STA uses UIUC FastX DC/PT and SAED32.

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 2: this is a descriptor-level study, with no CXL packet engine, coherence, link-credit protocol or real DRAM controller. First Progress Report references to routing do not authorize another memory output or destination bits in this baseline. Multi-output routing is OPTIONAL_OR_DEFERRED.

## 3. Descriptor and logical ports

Store and transport all 105 bits intact. Policy metadata is separate and cannot substitute for descriptor storage.

| Field | Width | Baseline role | Approved packed slice |
| --- | ---: | --- | --- |
| Tag | 32 | Preserved; TB response correlation. | [104:73] |
| Address | 32 | Preserved; no multi-memory selection. | [72:41] |
| Opcode | 1 | Preserved; equal service cost. | [40] |
| Length | 8 | Preserved; no extra service cycles. | [39:32] |
| Payload | 32 | Preserved; no additional payload beats implied. | [31:0] |
| Total | 105 | 32+32+1+8+32=105. | [104:0] |

RETAINED_PROJECT_DEFAULT: pack fields in listed order, most to least significant bit. These are approved project offsets, not a recovered paper packing. The scheduler treats descriptor contents as opaque. Real memory read/write semantics are outside baseline scope; any later functional memory model cannot change the approved atomic service cost.

Retained logical port names/layout (tool-compatible representation is allowed without changing the contract):

| Signal | Logical width | Meaning |
| --- | --- | --- |
| clk, rst_n | 1 each | Single clock; synchronous active-low reset. |
| i_in_valid, o_in_ready | N each | Per-source handshake. |
| i_in_desc | N descriptors of105 bits | Input data. |
| o_out_valid, i_out_ready | 1 each | Single memory-output handshake. |
| o_out_desc | 105 | Complete selected descriptor. |
| o_out_source | ceil(log2(N)) | Selected source sideband for TB observation; outside the105-bit descriptor. |

Tool-compatible flattening may preserve the logical widths. No response tracker/port or simulation-only timestamp-preload/debug port is implied in RTL.

## 4. Cycle-level FIFO/handshake contract

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 2. Cycle c is the interval before its closing rising edge. Arbitration and readiness use beginning-of-cycle state; edge commits become visible in c+1.

- One FIFO per source, with common descriptor storage/semantics across all policies. Policy metadata/state may differ.
- push[h] = in_valid[h] && in_ready[h].
- fire = out_valid && out_ready.
- Only fire dequeues the selected request and consumes quota. Selection without acceptance is not service.
- in_ready[h] depends only on beginning-of-cycle occupancy: occupancy[h] < D when not in reset. It does not predict a same-edge pop to accept into a full FIFO.
- No empty-FIFO bypass: a descriptor accepted at edge c becomes eligible no earlier than cycle c+1 and cannot fire at its accepting edge.
- An input producer retains its valid descriptor until push. During output stalls, output valid, all 105 descriptor bits, selected source and pending transfer's class/quota context remain stable; later arrivals cannot preempt it.
- Up to one push per source may occur per edge; at most one output fire occurs. Per-source FIFO order is preserved.

Define pop[h] as fire for the selected source. Simultaneous update rules:

| push[h] | pop[h] | Next occupancy and pointers |
| ---: | ---: | --- |
| 0 | 0 | Unchanged. |
| 1 | 0 | +1; advance tail after writing. |
| 0 | 1 | -1; advance head. |
| 1 | 1 | Unchanged; advance both, preserving order. |

A full FIFO refuses push even when its head fires that edge. An empty FIFO may push but cannot pop that edge. Under these rules simultaneous push/pop requires a previously nonempty, nonfull FIFO. No accepted request may be overwritten or dropped.

**Stall clarification:** stable associated state means retained grant/descriptor/quota context, not every global register. FIFOs may still accept input during a downstream stall. The FAI window clock continues and classifications may change at a window edge; those updates cannot alter the held output. This reconciles S0's hold requirement with its explicit continuously advancing window.

## 5. Clock, reset and output timing

SPECIFIED_IN_PRIOR_DOCUMENTS: one clock, synchronous active-low reset. There is no baseline CDC boundary or asynchronous reset.

APPROVED reset detail: a rising edge with rst_n=0 clears occupancy/pointers, held-grant validity, pending transitions, used quotas, served counters, timestamp cycle counter and window index. RR polling starts at source0. All Main FAI sources initialize H, with High class first. Algorithm-2 initializes stable High with no pending Buffer state. Handshakes/output valid are inactive during reset. Invalid FIFO data/timestamp bits need not be physically cleared. Reset starts a new TB epoch.

APPROVED_COMMON_FRAMEWORK selection timing: one shared switch_top, one common FIFO implementation and one common output/stall controller for every policy/FAI interpretation. Select from eligible beginning-of-cycle heads without an extra mandatory output pipeline stage; retain an offered transfer if stalled. Empty visits/quota renewal cannot cause control-only bubbles when eligible work exists. Do not duplicate common blocks or add policy-dependent stages, bypass or buffering without explicit architectural approval. Identical descriptor/FIFO/output/sink timing and synthesis boundary apply to all nine configurations; only necessary policy logic/metadata may differ.

Q1/Q2 are resolved by S3; initialization and turn rules are binding project microarchitecture, not claims of cycle-identical paper dispatch.

## 6. Shared FCFS timestamp selector

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 3:

- A successful input handshake assigns a 32-bit arrival timestamp stored per FIFO entry for FCFS and FAI-inspired.
- Oldest eligible FIFO head wins. Equal timestamps, including same-cycle ties, use ascending source ID.
- Modular ordering assumes every outstanding request remains outstanding less than2^31 cycles. Exactly-half-range comparisons are outside valid environment assumptions.
- Timestamp wraparound is a required directed test.
- FAI uses this shared selector within a class. RR must not contain unused timestamps or an unused arrival counter/selector.

For unequal a,b, a is older than b when 0 < ((b-a) mod2^32) < 2^31. Equal values use source ID; each source maintains its own FIFO order. All simultaneous pushes receive the same cycle timestamp.

RETAINED_PROJECT_DEFAULT: use a free-running32-bit cycle counter starting at0, advancing on all non-reset cycles, including stalls. A push stores its pre-edge value. A directed wrap test may initialize simulation-only state near wrap consistently in the independent model, without a synthesized debug interface. Instantiate this counter/storage only for policies needing arrival metadata.

## 7. Round Robin

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 3:

- From the current polling position, circularly choose the first nonempty source.
- A source turn allows at most 10 successful descriptor transfers. Length does not alter cost.
- Advance after consuming the quantum or when the selected source becomes empty. Skip empty sources.
- Stalls retain selection/turn context and do not consume quantum.
- Quantum=1 is supplementary, not one of the nine primary configurations.
- RR excludes unnecessary timestamp storage and timestamp-selection state.

USER_CONFIRMED Q2: evaluate source emptiness after all same-edge pushes/pops. A final head firing with a replacement push leaves the source nonempty, retaining its turn unless quantum expires. Quantum expiry advances regardless of replacement; stalls consume no quota. When all sources are empty, retain polling position without consuming quota.

## 8. FAI-inspired main interpretation

Option A keeps the RC1 four-state H/B_H/L/B_L Main interpretation as the FAI-inspired policy in all nine primary experiments. The approved Algorithm-2 supplement is separately identified in section8.6. Neither claims a cycle-identical reproduction of the paper's dispatch in this project's one-output switch.

### 8.1 Window accounting and thresholds

- Production W=5,000,000 cycles. The window index advances on every non-reset cycle, including downstream stalls, independently of memory responses.
- B[h] counts source h's successful transfers; S counts all successful transfers in the same accounting interval, S=sum(B[h]).
- B/S are window-local: only fire increments one B[h] and S. Include the closing-edge fire, classify, then clear for the next measurement window. S=sum(B[h]) is maintained throughout. S3 explicitly approves the boundary clear; it is not a phantom fire or consumed quota.
- The service average includes all N configured sources, including inactive/empty sources.
- Use closing-window counts including the closing-edge fire and exact widened integer comparisons:

| Evidence | Condition |
| --- | --- |
| UP | 10*N*B[h] < 3*S |
| DOWN | N*B[h] > S |
| KEEP | Otherwise, including equality. |

No floating-point approximation, rounded division or truncated multiplication. S=0 follows the explicit no-service rule below.

USER_CONFIRMED Q3: accounting is per window, not lifetime cumulative. Clearing follows classification from closing counts; new classification is visible the following cycle. An idle measurement window has zero service. Main cancels pending transitions on such a window; Algorithm-2 handles it as KEEP without that extra cancellation.

### 8.2 Four states and effective priority

H and L mean effective High/Low. Buffer B_H preserves previous High while a decrease is pending; B_L preserves previous Low while an increase is pending. Two consecutive windows supporting the same change switch effective class. Neutral/opposing evidence cancels pending changes. S=0 cancels pending changes while preserving effective class.

| Current / effective | UP | DOWN | KEEP | S=0 |
| --- | --- | --- | --- | --- |
| H / High | H | B_H | H | H |
| B_H / High | H | L | H | H |
| L / Low | B_L | L | L | L |
| B_L / Low | H | L | L | L |

This approved Main table preserves the prior effective class in its buffer state. All sources initialize H. KEEP, opposing evidence and S=0 cancel pending Main transitions as shown. These Main cancellation rules must not be applied to the Algorithm-2 supplement.

### 8.3 Class scheduling and held grants

- High/Low quotas are10/10 successful transfers.
- Within the chosen effective class, use shared FCFS timestamp/head selection.
- Skip empty classes without unnecessary idle cycles.
- Retain a selected source/class/quota context across stalls and any intervening classifications.
- A held descriptor cannot be preempted by a new class map. Its eventual fire is charged to its retained grant context; subsequent unlocked selections use the current effective classes.

USER_CONFIRMED Q2: alternate High then Low visits, at most10 fires per visit. Empty classes relinquish unused quota; no credit banking. Renew quota on a new visit. A sole nonempty class renews/continues without a bubble; both empty retains the turn without service consumption. Windows do not independently reset class-turn quota. Held grants retain their source/class/quota context through stalls and classification boundaries. This single-output alternation is a project-defined reconstruction shared by both FAI variants; the paper's per-cycle description does not uniquely define it.

### 8.4 Closing-edge order

On the Wth non-reset edge of a window:

1. Commit any offered transfer using its retained pre-edge source/class/quota context.
2. Compute B_close[h]=B[h]+fire_from_h and S_close=S+fire.
3. Classify all N sources **in parallel** from closing counts and current four-state values; apply S=0 cancellation where appropriate.
4. Expose new classification in the following cycle, clear B/S after using closing values, and set window index0 for the next window.
5. Preserve any stalled grant through the boundary. It completes with its retained context before unlocked selection uses the new classes.

Nonclosing edges advance the index and count fires normally. Do not replace parallel classification with a serialized classifier or arbitrary multicycle/false-path exceptions.

Retained index convention: start at0; pre-edge index W-1 is the closing edge and includes its fire. Reset edges are not window cycles.

### 8.5 Derived widths and supplementary interpretations

Window-local counting gives 0<=B[h]<=S<=W. Production W=5,000,000 uses 23-bit B/S counters and a 23-bit window index. Although800,000,000 is the mathematical maximum10*N*B for N16 and fits30 bits, S3 mandates **at least 31-bit widened unsigned threshold intermediates**. Use a common 32-bit unsigned representation for production comparisons; zero-extend operands before multiplication/addition. Do not truncate, sign-extend or divide to classify. Stress-window widths may be parameter-derived, but primary production settings stay fixed. These are logical bounds/contracts, not mapped-area results.

W=64/256 are stress-verification variants, not primary synthesis windows. The approved Algorithm-2 interpretation below is supplemental, initially N4, and never replaces Main in the primary matrix.

### 8.6 Approved supplementary Algorithm-2 interpretation

The owner supplies the Algorithm2 behavior/citation: J. Li et al., "FAI-CXL: An Efficient Hardware-Accelerated Fairness-Aware CXL Memory Pool Management with Fine-Grained Cacheline-Level Interleaving," IEEE ICPADS2025, Algorithm2,page5. No IEEE PDF is locally available/inspected in this task; the following behavior is documented from the owner's supplied account, not a claimed local PDF transcription.

Use stable High, stable Low, or Buffer with stored priority metadata p in {High,Low}. A Buffer request is immediately serviced in stored target class p. Unlike Main, Buffer does not retain the previous effective class.

| State | UP | DOWN | KEEP / zero-service window |
| --- | --- | --- | --- |
| Stable High | Stable High | Buffer,p=Low | Stable High |
| Stable Low | Buffer,p=High | Stable Low | Stable Low |
| Buffer,p=High | Stable High | Stable Low | Buffer,p=High |
| Buffer,p=Low | Stable High | Stable Low | Buffer,p=Low |

Idle zero-service naturally yields KEEP and does not cancel Buffer. Thresholds, window-local B/S, closing-edge inclusion, common FIFO/output controller and project single-output10/10 alternation are shared. Only state-transition/effective-class interpretation differs. Do not claim cycle-identical paper dispatch; distinguish the owner's paper-behavior account from project microarchitecture assumptions.

Implement via separate parameter/selection in the shared switch framework. After nine Main configurations complete, run N4 functional/behavior/synthesis comparisons between Main and Algorithm-2. Expand to N8/16 only if differences materially affect PPA conclusions and time permits. The Main matrix remains unchanged; no supplementary result is claimed now.

## 9. Verification requirements

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 4 unless marked retained defaults. No scheduler verification result is implied by specification approval.

- Independent Python models for FCFS, RR and main FAI, developed under the controlled implementation workflow. Compare cycle-level acceptance, eligibility, selection/fire and state accounting, not only eventual response totals. Do not copy RTL control code as the reference.
- Directed tests: FIFO empty/full, full-plus-pop readiness, simultaneous push/pop, no bypass/next-cycle eligibility, synchronous reset, stalls, FIFO and policy ordering/ties, quotas, timestamp wrap, four-state FAI transitions, S=0, threshold equality, closing-edge inclusion, and held grants spanning classification changes.
- 20 reproducible random seeds per primary configuration, initially 100,000 active cycles each:180 primary runs across nine configurations, all NOT_RUN. Use comparable generated traffic and downstream-ready traces.
- FAI stress tests W=64 and W=256. A100,000-cycle production-window run does not reach a W=5,000,000 boundary and cannot prove window behavior.
- At least one W=5,000,000 test spans three complete windows: at least 15,000,000 non-reset window cycles. Retained coverage default: one such test per FAI N value. Supplementary tests do not expand the nine synthesis configurations.
- Scoreboards check descriptor integrity, accepted-request conservation, no loss/duplication, ordering and policy selection. TB-generated tagged responses match outstanding requests exactly once. Response delay/reordering never charges quota or B/S.
- RETAINED_PROJECT_DEFAULT: globally unique outstanding tags, reuse only after response, reset epochs, abstract tagged-completion memory model; functional DRAM/read-write modeling is outside scope.
- Preserve source/configuration, seed, tools, logs and failure trace. Required absent/skipped/failed runs cannot count as PASS.

Retained reproducible defaults: seeds509..528, no warmup, explicit bounded ready/stall patterns plus directed long stalls, fixed offered-traffic measurement interval, then a separately reported drain/response-completion phase. Formal proofs, CDC signoff, UVM/SystemC and numerical coverage thresholds are OPTIONAL_OR_DEFERRED unless subsequently required; plugin templates do not create new baseline obligations.

## 10. Required metrics

Report phase boundaries, active cycles and outstanding/censored samples. These required metrics come from S0 section 4; estimator details are retained project defaults.

| Metric | Definition |
| --- | --- |
| Accepted-transfer rate | Completed output descriptors (fire) / measured non-reset cycles; physical maximum1. Also report input push count/rate separately; summed input acceptance can exceed1 while queues fill. |
| Mean/P99 acceptance-to-fire waiting time | Fire-edge cycle minus input push-edge cycle; includes queueing/stalls, not response latency. No bypass implies minimum1 cycle. |
| Per-source service counts | Fires for each configured source over the same interval, including zero-service sources; not only the last FAI window counts. |
| Generation-to-acceptance delay | Push-edge cycle minus TB generation cycle; distinct from scheduler waiting and response time. Report generated but unaccepted requests separately. |

RETAINED_PROJECT_DEFAULT: arithmetic mean, nearest-rank P99 at sorted1-based rank ceil(0.99*K), N/A for no samples. Include drain-completed waits for requests accepted during measurement, exclude drain fires from offered-phase rate, and label incomplete/censored samples. Use identical intended source-generation/downstream-ready traces; record differing actual input acceptance caused by policy backpressure. Equal-cost service does not claim byte-weighted fairness.

## 11. Primary synthesis/STA and PPA

| Policy | N=4,D=16,M=1 | N=8,D=16,M=1 | N=16,D=16,M=1 |
| --- | --- | --- | --- |
| FCFS | NOT_RUN | NOT_RUN | NOT_RUN |
| RR quantum10 | NOT_RUN | NOT_RUN | NOT_RUN |
| FAI W=5,000,000;10/10 | NOT_RUN | NOT_RUN | NOT_RUN |

Keep the nine baseline configurations unchanged. RR quantum1, reduced FAI windows and N=4 alternate buffer interpretation remain supplementary.

SPECIFIED_IN_PRIOR_DOCUMENTS via S0 section 4:

- Synthesize the complete switch: common descriptor FIFOs, selection/output control and policy metadata/state. Exclude TB memory models, response tracking and simulation-only instrumentation.
- Descriptor storage alone is N*16*105 bits:6,720/13,440/26,880 for N=4/8/16. FCFS/FAI add32*N*16 timestamp bits:2,048/4,096/8,192, plus actual policy state. RR omits timestamps. These are logical storage counts, not mapped FF counts/area.
- Do not blackbox FIFO storage or omit its area/timing while claiming complete-switch PPA. No characterized SRAM macro is supplied; the common storage boundary must be completely mapped/accounted for.
- Hold technology library, PVT, clock, SDC, synthesis effort and optimization settings constant. Preserve actual versions, source/config hashes and commands.
- Also freeze clock uncertainty, I/O constraints, output loads, input transitions, wire-load estimation methodology and reporting scripts. Compare total switch cost and policy-specific overhead under the same common framework; no common-block changes to favor one policy.
- Report total mapped cell area, FF count/area and combinational area, WNS and critical paths. Account for any other sequential category so totals reconcile. No NanGate45 proxy or hardcoded NAND2 conversion.
- Determine one common clock target through pilot runs after implementation authorization, then freeze the shared clock/SDC profile for all nine. The prior5ns registered-adder smoke constraint is not a scheduler target. Do not use different relaxed targets per policy/N.
- Attempt activity-annotated pre-layout power when supported. Report activity window/source, annotation coverage, capability/license/library assumptions. Otherwise document the concrete limitation; no fabricated power or equivalent claim for an unannotated fallback.
- Keep parallel FAI classification on normally timed paths; no arbitrary multicycle/false-path exceptions.

Selected FastX environment: module Synopsys_x86-64/2024, user-reported DC/PT W-2024.09 and SAED32 RVT saed32rvt_tt0p78v25c.db. Actual remote access, library path and capability/license checks remain pending. No project synthesis/STA has run. Numerical clock/I/O-delay/load values belong in the pilot-derived common timing profile; no values are invented here and these execution prerequisites do not reopen specified FIFO/policy semantics.

## 12. Approval and controlled implementation

Q1–Q3 are explicitly approved by the Project owner on2026-10-13. Retained nonarchitectural RC defaults are approved where consistent with S3. No newly discovered correctness-critical contradiction remains; any later conflict must be reported, not silently changed.

The approved common framework is a single switch_top with policy-selectable scheduling. Claude Code with RTL Agent Team is the primary implementation/verification agent; Codex orchestrates and independently reviews. Verify CLI/plugin/frozen-spec access and file/tool permissions before delegation. Preserve per-task prompts, execution logs, changed-file list, Git diff and actual test evidence. No simultaneous conflicting writes.

First controlled milestones: shared descriptor/FIFO, common output/stall control, FCFS plus independent Python model, then RR plus model. Run WSL Verilator lint/cocotb tests after each; stop and repair failures before advancement. Independently review the common architecture and actual results before FAI integration. The frozen Main and Algorithm-2 definitions guide subsequent milestones; supplementary comparisons follow completion of the nine primary configurations.

Do not invoke rat-auto-design or restart architecture research. Use focused Phase4/5 skills. If programmatic Claude delegation is blocked, report it and request interactive Claude execution; do not silently substitute Codex-authored RTL. Do not start a nine-configuration PPA sweep before integrated functional verification. Actual remote synthesis/STA/power remains unrun until successful executions establish results.

specs/APPROVAL.md records the owner authorization. Record the frozen Git revision in docs/STATUS.md and task manifests once committed. Approval does not mark implementation/tests complete.

## 13. Revision history

| Revision | Change | Approval |
| --- | --- | --- |
| v0.1 | Initial scaffold. | Not fully approved. |
| v0.2 | Six scope/tool decisions and separate WSL setup. | Individual confirmations only. |
| v1.0 RC1 | Restored supplied cycle contract, policies, verification/PPA and source/default distinctions. | RELEASE_CANDIDATE, NOT_APPROVED. |
| v1.0 | Owner-approved Q1–Q3/Option A, >=31-bit threshold arithmetic, shared framework and controlled Claude milestones; nonarchitectural defaults retained. | APPROVED2026-10-13, Project owner. |
