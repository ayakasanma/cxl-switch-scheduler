# CXL Approved Spec v1.0 Decision Register

Updated 2026-10-13 (Asia/Taipei). Full specification status: APPROVED v1.0, Project owner,2026-10-13. Implementation gate: OPEN for controlled Claude milestones; progress remains separately recorded.

## Classification and sources

Exactly one primary category is assigned to each item:

| Category | Meaning |
| --- | --- |
| USER_CONFIRMED | Explicit direct user confirmation, including S0 section1's instruction to preserve previously approved decisions. Approval applies only to the stated item. |
| SPECIFIED_IN_PRIOR_DOCUMENTS | Restored prior-document requirement supplied through S0 sections2–4. Included in RC, not independently mislabeled as explicit user approval. |
| PROPOSED_DEFAULT_PENDING_APPROVAL | Agent recommendation completing an unstated detail; approve with the RC or amend it. |
| REQUIRES_USER_DECISION | Remaining correctness-affecting choice or the explicit final release approval. |
| OPTIONAL_OR_DEFERRED | Supplemental/deferred work or execution information outside the main architecture gate. |

S0 = [user reconciliation request](../docs/sources/USER_RECONCILIATION_REQUEST_2026-10-13.md). S1 = earlier direct user six-decision message, retained through Git history and v0.2. S3 is the owner's direct Option A approval and common-framework instruction on2026-10-13. All frozen items are now approved as specified or retained project defaults. Original Revised Proposal/First Progress Report files are not available locally; SPECIFIED_IN_PRIOR_DOCUMENTS means user-supplied account of them, not independent primary-source inspection. See [SPEC_REVIEW.md](../docs/SPEC_REVIEW.md).

## Reconciled decisions

D01–D24 preserve the old register IDs while replacing stale blanket TBDs. New IDs isolate unstated details rather than reopening specified design behavior.

| ID | Item | Category | Reconciled requirement / recommendation | Source or outstanding action |
| --- | --- | --- | --- | --- |
| D01 | Scope/exclusions | SPECIFIED_IN_PRIOR_DOCUMENTS | Descriptor-level scheduling; no CXL packet/coherence/credit engine or real DRAM controller. | S0 §2. No protocol-version decision needed for this baseline. |
| D02 | Topology | USER_CONFIRMED | N=request sources 4/8/16; M=1 Memory Output, implicit destination. | S0 §1; resolves previous uncertainty about N. |
| D03 | Descriptor/service | USER_CONFIRMED | Full105: Tag32/Address32/Opcode1/Length8/Payload32; atomic equal-cost service, at most one fire per cycle, Length adds no cycles. No memory-ID bits. | S0 §1; takes precedence over Tag-only proposal. |
| D04 | FIFO capacity | USER_CONFIRMED | D=16 entries per source, included in baseline. | S0 §1; no depth/boundary TBD. |
| D05 | Interface | SPECIFIED_IN_PRIOR_DOCUMENTS | Ready/valid inputs/output; push[h]=valid&&ready; fire=out_valid&&out_ready; held descriptor/source/context stable. | S0 §2. Approved presentation default in D30. |
| D06 | FCFS | SPECIFIED_IN_PRIOR_DOCUMENTS | Timestamp at push,32 bits per entry; oldest head, ascending-source ties, modular order with outstanding age<2^31 cycles; directed wrap test. | S0 §3. D29 supplies counter initialization detail only. |
| D07 | RR | SPECIFIED_IN_PRIOR_DOCUMENTS | First nonempty from polling position, at most 10 fires per source turn; advance at quantum/emptiness; stalls consume none; no unused timestamps. | S0 §3. Exact edge convention is Q2/D26. |
| D08 | FAI main policy | SPECIFIED_IN_PRIOR_DOCUMENTS | W=5,000,000; per-source B and total S=sum(B); all configured N in average; exact UP/DOWN inequalities; H/B_H/L/B_L two-window hysteresis and S=0 cancellation. | S0 §3; derived main semantic table in spec §8. Counter interval is Q3/D27. |
| D09 | Output arbitration/service | USER_CONFIRMED | Sole memory output, one atomic accepted descriptor/fire maximum per cycle; no Length-weighted service. | S0 §1. |
| D10 | FIFO timing/backpressure | SPECIFIED_IN_PRIOR_DOCUMENTS | Common per-source FIFO, readiness from beginning occupancy, no bypass, new pushes eligible next cycle, correct push/pop, fire-only dequeue/quota consumption. | S0 §2. Full-plus-pop cannot accept a push. |
| D11 | Extra fairness guarantees | OPTIONAL_OR_DEFERRED | Do not invent universal bounded starvation or a numerical fairness target beyond specified policy/metrics. | Counts/waiting metrics are required in D18; any additional theorem/threshold needs later scope. |
| D12 | Cycle/retention rules | SPECIFIED_IN_PRIOR_DOCUMENTS | Retain selected source/class/quota over stalls; FAI window still advances; closing fire included, new classes visible following cycle; parallel classification baseline. | S0 §§2–3. Global window/class changes do not cancel a held grant. |
| D13 | Clock/reset kind | SPECIFIED_IN_PRIOR_DOCUMENTS | Single clock, synchronous active-low reset. | S0 §2; supersedes imported async-reset default. |
| D14 | Primary parameter/matrix | USER_CONFIRMED | Three policies by N4/8/16, D16,M1,full 105: nine primary synthesis configurations. | S0 §1; no supplemental variant replaces these. |
| D15 | Malformed/unsupported cases | USER_CONFIRMED | Reject unsupported baseline parameters and invalid TB scenarios; no silent drops. Reset is a separate epoch; preserve all fields rather than invent decoder errors. | Spec §§3–5/9. No destination-ID validation is needed for M1. |
| D16 | Responses/observability | USER_CONFIRMED | TB generates responses and matches tags; no synthesized response tracking. FAI B/S are actual policy state, not a TB-only substitution. | S0 §1; selection/source observation proposal D30. |
| D17 | Regression requirements | SPECIFIED_IN_PRIOR_DOCUMENTS | 20 seeds/configuration, initially 100,000 cycles; W64/256 stress; at least one production W test across three complete windows; directed FIFO/stall/order/quota/wrap/FAI boundary tests. | S0 §4. Detailed reproducibility defaults D31. |
| D18 | Required metrics | SPECIFIED_IN_PRIOR_DOCUMENTS | Accepted-transfer rate, mean/P99 acceptance-to-fire waiting, per-source fires, generation-to-acceptance delay. | S0 §4; retained estimator/phase conventions in spec §10. |
| D19 | Reference/scoreboard | SPECIFIED_IN_PRIOR_DOCUMENTS | Independent Python model per policy; all 105 bits, loss/duplication/order, TB tagged responses. | S0 §4; supersedes imported mandatory C11/DPI-C reference guidance. |
| D20 | Formal/CDC/SystemC/UVM | OPTIONAL_OR_DEFERRED | No required CDC flow in this single-clock baseline; formal/extra coverage or heavy frameworks not automatically installed/required. | Existing scope and explicit tool boundaries. |
| D21 | Complete-switch PPA/method | SPECIFIED_IN_PRIOR_DOCUMENTS | Include common FIFOs and policy metadata; exclude TB; freeze library/PVT/clock/SDC/effort/settings; total/FF/combinational area,WNS,critical paths; pilot common clock; attempt annotated pre-layout power or explain inability. | S0 §4. The 5ns adder constraint is not final scheduler timing. |
| D22 | Commercial tools/library | USER_CONFIRMED | FastX DC/PT + SAED32; existing university assets remain external. | S0 §1/S1; known module/corner is user-reported, not new verified access. |
| D23 | Repository/local tooling | USER_CONFIRMED | Continue sole cxl-scheduler repo; local WSL Verilator/cocotb verification. | S0/S1; installation passed environment-only checks before this RC task. |
| D24 | Full release approval | USER_CONFIRMED | Spec v1.0 and Q1–Q3 approved; retained defaults accepted where consistent. Controlled implementation authorized, no completion claim. | S3; specs/APPROVAL.md. |
| D25 | Initial policy state: Q1 | USER_CONFIRMED | RR pointer0, all FAI H, High first; reset pending transitions/quota/counters/valid state. | S3 explicit Q1. |
| D26 | Turn/empty edge details: Q2 | USER_CONFIRMED | RR post-edge occupancy/mandatory quantum advance; FAI alternating10-fire visits, discard residual quota, no banking/window-reset, held context retained. | S3 explicit Q2. |
| D27 | B/S accounting scope: Q3 | USER_CONFIRMED | Window-local B/S; fire increments only; closing fire included, classify then clear, next-cycle classes; S=sum(B). | S3 explicit Q3; previous ambiguity resolved. |
| D28 | Reset payload/epoch detail | USER_CONFIRMED | Clear validity/pointers/control, not all invalid FIFO bits; no handshakes during reset; TB clears outstanding epoch. | Not a change to specified synchronous active-low reset. |
| D29 | Timestamp timebase detail | USER_CONFIRMED | Free-running32-bit non-reset cycle counter, start0, includes stalls, pre-edge value stored on push. | Maintains supplied same-cycle ties/modular ordering. |
| D30 | Packing/port/timing presentation | USER_CONFIRMED | Listed MSB-first105-bit packing; source sideband outside descriptor; no mandatory extra output stage; preserve exact cycle/hold contract. | Spec §§3/5. No destination bits or added response interface. |
| D31 | Test/metric defaults | USER_CONFIRMED | Seeds509..528, one long production-window test per FAI N, fixed offered phase plus labeled drain, nearest-rank P99, unique outstanding TB tags/abstract completions. | No model/test implementation now. All estimator/defaults must be identical across policies. |
| D32 | RR quantum1 | SPECIFIED_IN_PRIOR_DOCUMENTS | Planned supplementary comparison, distinct from primary quantum10 matrix. | S0 §3; NOT_RUN, not one of nine primary results. |
| D33 | Literal alternate FAI buffer check | USER_CONFIRMED | Algorithm-2 target-priority Buffer variant approved; KEEP/idle preserves Buffer. N4 comparisons after primary nine; N8/16 expansion conditional. | S3 supplied paper account/citation, PDF not locally inspected. |
| D34 | FastX access/pilot numbers | OPTIONAL_OR_DEFERRED | Supply connection/auth/library paths for future execution; derive/freeze timing profile from actual pilots. | Missing execution inputs, not reopened FIFO/policy decisions. No run performed. |
| D35 | Count/arithmetic bounds | USER_CONFIRMED | Production23-bit B/S; >=31-bit unsigned widened threshold intermediates; use common32-bit representation. | S3 overrides RC mathematical-minimum30-bit observation. |

## Approved Q1–Q3 and Option A

Q1: RR polling source0, all Main FAI H, High first. Reset clears pending transitions, quota use, counters and valid state.

Q2: post-push/pop RR emptiness, quantum expiration advances regardless of replacement, stalls consume no quota. High/Low visits allow up to10 fires, empty visits relinquish residual quota, no banking, and no independent window quota reset. Held source/class/quota survives stalls and classifications.

Q3: B/S are window-local. Fire-only increments, closing-edge inclusion before classification, next-window clearing and next-cycle classification explicitly resolve the prior wording. Maintain S=sum(B).

Option A: RC1 Main H/B_H/L/B_L retains previous effective priority until two supporting windows; KEEP/opposing/S=0 cancels pending Main states. Supplementary Algorithm-2 uses stable H/L or Buffer with immediate target priority; UP/DOWN from Buffer settles H/L, and KEEP/idle retains Buffer. These behaviors must not be mixed.

The single-output10/10 alternation, common FIFO/hold/timing/sink/synthesis boundary, reset initialization and window accounting are project-defined reconstruction/choices shared by both variants. They are not claimed to be cycle-identical IEEE dispatch. Paper behavior is documented from the owner's supplied account; no local IEEE PDF inspection is claimed.

## Retained defaults and deferred execution

Packing/port names, invalid FIFO data treatment, timestamp initialization, Python reference/seed/metric conventions and no extra output stage are retained where consistent with S3. There is no remaining correctness-critical decision in this baseline. A newly discovered contradiction must be escalated before an incompatible implementation.

Multi-memory outputs, APR and other optional extensions are explicitly deferred. RR quantum1 remains supplemental. Formal/CDC/SystemC/UVM are not automatic requirements. FastX connection data and pilot-derived numerical timing constraints remain execution prerequisites; no remote/PPA result exists.

## Approval and workflow evidence

APPROVED v1.0 by Project owner on2026-10-13 (Asia/Taipei); specs/APPROVAL.md contains the machine-readable gate plus approved baseline/supplement and deferred features. Spec freeze Git hash is recorded after commit in docs/STATUS.md/task manifests.

At freeze all RTL/models/testbenches remain NOT_STARTED and scheduler verification/PPA NOT_RUN. Subsequent status changes require actual file/test evidence. Claude Code RTL Agent Team implements and verifies; Codex independently reviews. First milestones are common FIFO/descriptor, common hold/output control, FCFS and RR; review these before FAI integration. No rat-auto-design or early PPA sweep.
