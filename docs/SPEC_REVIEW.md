# Spec v1.0 Approved Source Reconciliation and Review

Date: 2026-10-13 (Asia/Taipei). Outcome: **APPROVED v1.0**, Project owner, Option A. Q1–Q3 are resolved by direct approval; RTL implementation/verification/PPA progress remains separately recorded.

## 0. Current owner approval (S3)

The direct2026-10-13 owner message approves Q1 source0/all H/High first/reset clearing, Q2 post-edge RR occupancy and fixed class visits/held context, and Q3 window-local fire counts/closing inclusion/clear/next-cycle classification. Production B/S are23 bits; threshold intermediates must be at least31-bit widened unsigned (project32-bit representation).

Option A freezes Main's RC1 previous-effective-priority hysteresis for the primary nine. It approves a separate Algorithm-2 target-priority Buffer variant, initially N4 after the nine primary configurations. The supplied citation is J. Li et al., FAI-CXL, IEEE ICPADS2025, Algorithm2,page5. No IEEE PDF is locally present/inspected. This source account is user-supplied, not independent publication verification.

Algorithm-2: stable Low+UP enters Buffer with target High; stable High+DOWN enters Buffer with target Low. Any Buffer+UP becomes stable High; Buffer+DOWN becomes stable Low; KEEP/idle stays Buffer with its stored target. Buffer service uses target priority immediately. Main instead retains prior effective priority and cancels pending states on KEEP/opposing/zero service. These remain distinct test/model variants.

The paper account does not uniquely determine single-output per-cycle High/Low alternation. The approved common10/10 alternation, equal-cost service, FIFO/hold/timing framework and measurement windows are explicit project reconstructions shared by both variants; no cycle-identical paper dispatch is claimed. Common RTL must not be rewritten or staged differently by policy. No unresolved correctness-critical contradiction is found in these approved changes.

## 1. Inputs actually available

| Source | Evidence available | Use / limitation |
| --- | --- | --- |
| S0: [user reconciliation request](sources/USER_RECONCILIATION_REQUEST_2026-10-13.md) | Exact supplied attachment text preserved locally. | §1 reiterates approved decisions; §§2–4 restores reported prior cycle-level/verification/PPA requirements; §5 distinguishes source status from progress; §6 requests RC only. |
| S1: earlier direct six-decision message | Prior conversation and commit d1c9d02. | Full105 descriptor, M1/TB tracking, nine experiments, WSL tools and FastX flow, no completed scheduler work. |
| S2: local v0.2 spec/decisions/status | Clean pre-edit commit d1c9d02,73 tracked files. | Previous scaffold and verified environment records. Excessive design TBDs are superseded where S0 provides actual semantics. |
| Original CXL Scheduler Revised Proposal | Not in repository/CXL workspace or this attachment directory. | Older Tag-only representation is known through S0's account. No original text/page claim. |
| ECE509 First Progress Report | Not in repository/CXL workspace or this attachment directory. | Full descriptors/routing/TB tracking and prior semantics are known through S0, not independent inspection. |

The raw S0 attachment SHA256 before Git text normalization was `B50F1DC85167CF36E05646D102204A0616FCC4B215FB60FAF89B94CE6578D119`. The preserved Markdown content is the request itself, not a reconstructed Proposal or Progress Report. Its Git object is the portable content reference; CRLF/LF normalization can change file-byte hashes without changing text.

No user-owned source was overwritten or deleted. The initial66 files and subsequent WSL/spec work remain in Git history. This task stays in the single existing `cxl-scheduler` checkout. Toolchain installation/smoke evidence is preserved; no new tool installation, remote invocation or scheduler test was needed for this document-only revision.

## 2. Historical RC reconciliation map (superseded by S3 where noted)

| Issue in v0.2 / older source account | Restored RC treatment | Provenance / resolution |
| --- | --- | --- |
| N meaning/depth unknown | N=request sources 4/8/16, D=16 per source, M1. | USER_CONFIRMED, S0 §1. Remove generic topology/depth questions. |
| Tag-only versus full descriptors | Store/transport all 105 bits; no destination-memory ID. | USER_CONFIRMED latest full 105 precedence. Proposed packing is explicitly separate. |
| Routing language in latest report | Implicit sole memory destination, not permission for a CXL packet engine/multi-output router. | S0 §§1–2 baseline bounds the report's routing language. |
| Transaction cost/Length unclear | One equal-cost atomic descriptor per fire; at most one fire/cycle; Length adds no service cycles. | USER_CONFIRMED, S0 §1. No weighted-byte service or extra beat engine. |
| FIFO/handshake timing unknown | Shared per-source FIFO; beginning occupancy readiness, no bypass, following-cycle eligibility, simultaneous push/pop rules, fire-only dequeue/quota. | SPECIFIED_IN_PRIOR_DOCUMENTS, S0 §2. |
| Async reset/plugin defaults | Single clock, synchronous active-low reset. | Restored S0 §2 overrides imported generic reset rule. Reset invalid-data/epoch detail is proposed. |
| Output state stable versus advancing FAI window | Hold the descriptor/source/grant/quota context; allow independent FIFO pushes and global window/classification updates. | Both statements in S0 must hold. Freezing every register would contradict explicit window advancement during stalls. |
| FCFS algorithm unspecified |32-bit push timestamps, oldest eligible head, source-ID ties, modular age assumption, directed wrap test. | Restored S0 §3. Exact free-running counter/reset presentation is proposed. |
| RR semantics unspecified | Poll first nonempty;10 successful transfers max/turn; fire-only charge; advance at emptiness/quantum; no timestamp storage. | Restored S0 §3; quantum1 retained as separate supplement. Edge emptiness/init details are Q1/Q2. |
| FAI label without definition | Exact threshold inequalities, all-source average, main H/B_H/L/B_L table, two-window hysteresis, cancellation/S0 behavior,10/10 classes, FCFS within class. | Restored S0 §3 main interpretation; no unspecified completion-feedback dependency. |
| FAI boundary/timing open | Closing fire included, class changes following cycle, held context retained, window advances through stalls, classification parallel. | Restored S0 §3. No arbitrary serialized classifier/timing exception. |
| B/S interval / fire-only update wording | Explicit recommended per-window accounting, labeled proposal. | S0 does not state resetting versus cumulative counting. A window clear needs clarification if "update only on fire" prohibits all non-reset changes. Q3 is not silently resolved; widths are conditional. |
| Literal buffer interpretation | Separate initial N4 interpretation check, no baseline substitution. | S0 §3; exact original pseudocode missing, supplemental execution deferred. |
| C11/SystemC reference template | Independent Python model for each policy. | Restored S0 §4 takes precedence; no new heavy frameworks required. |
| Random/FAI verification unspecified |20 seeds/config,100,000 cycles initially; W64/256 stress; production W5,000,000 across at least three windows. | Restored S0 §4. Short primary runs alone cannot test production-window transitions. |
| Metrics unspecified | Output transfer rate, mean/P99 push-to-fire wait, all-source counts, generation-to-push delay. | Restored S0 §4; rate/input-count distinction and estimator/phase defaults are explicit. |
| PPA boundary open | Complete switch, common full-descriptor FIFOs and policy state; exclude TB memories/responses. RR does not pay unused timestamp cost. | Restored S0 §4. No omitted/blackboxed storage in a full-switch result. |
| Clock/power treated as large architecture TBD | Actual pilot-derived common clock; all nine use same library/PVT/SDC/effort/settings. Attempt annotated pre-layout power or report concrete limitation. | Restored S0 §4. Prior5ns adder smoke is not a scheduler target. |
| Earlier report FCFS/RR completion claims | NOT_STARTED / NOT_RUN in repository status. | S0 §5 explicitly rejects progress inference. |

## 3. Consistency checks and illustrative boundary reasoning

These are document-level arithmetic/logic checks, not scheduler simulation:

- Descriptor widths sum to105; proposed slices cover104..0 exactly without overlap. Source sideband is separate; no destination bit added.
- Primary matrix remains3 policies by 3 N values=9. D16, M1 and full descriptor apply to all. RR1/reduced windows/alternate interpretation are clearly supplemental.
- Full-plus-pop readiness: beginning occupancy16 gives ready0; output may pop to15, but a push is not accepted that same edge. Empty-plus-push cannot also fire. Occupancy1 with simultaneous accepted push/pop stays1.
- Earliest new-request transfer is the edge after its push, satisfying no bypass and a minimum one-cycle push-to-fire waiting time.
- FCFS wrap example: a=`0xFFFFFFFE`, b=`0x00000001`; modular b-a=3, so a is older within the stated age bound. Exactly2^31 separation is outside assumptions; equal timestamps use source ID.
- B_H is still High until a second DOWN; KEEP/UP returns to H. B_L is still Low until a second UP; KEEP/DOWN returns to L. With S=0, pending states cancel to their prior effective class.
- Threshold equality:10*N*B=3*S is not UP, and N*B=S is not DOWN. Comparison widening is required; division-based approximations can misclassify boundaries.
- Closing fire increments B/S before classification. No-fire window edges still advance/classify; under approved Q3, an idle window yields S=0 and cancels Main pending transitions; Algorithm-2 retains Buffer.
- Approved window-local widths: baseline W5,000,000 needs 23-bit counts/index; max10*16*W=800,000,000 requires 30-bit unsigned arithmetic. The hardware contract additionally mandates >=31-bit unsigned threshold intermediates; use32 bits. No lifetime-cumulative alternative is authorized.
- Full descriptor logical storage:6,720/13,440/26,880 bits; per-entry timestamp metadata for FCFS/FAI:2,048/4,096/8,192. These numbers are not measured mapped-cell area.
- 20 seeds across 9 configurations yields180 initial primary random runs.100,000 cycles cannot reach a 5,000,000-cycle closing edge; three production windows require at least 15,000,000 non-reset cycles.

## 4. Historical RC questions — now resolved by S3

RC1 identified the following gaps. The owner now explicitly accepts the recommendations in Q1–Q3; they are no longer open architecture questions:

| Question | Recommendation | Reason / effect |
| --- | --- | --- |
| Q1: initial policy control state | RR polls source 0. FAI starts all H, High first, no pending changes and zero used counters/quota. | Deterministic, symmetric initialization; supplied summary did not define class/turn initialization. |
| Q2: exact turn/empty boundary | RR tests post-push/pop occupancy. FAI alternates10-fire visits, relinquishes residual quota at emptiness, no credit banking/window quota reset; held old context completes first. | Resolves replacement-on-pop and class-change/stall traces without extra bubbles or fabricated credits. |
| Q3: served-count interval | Window-local B/S, classify with closing fire included, then clear for next window. | Idle-window S=0 cancellation, recent-workload adaptation and finite widths; fire-only update wording needs explicit clarification for clearing. Cumulative counting needs a different overflow contract. |

Other RC defaults retained by S3: packing/logical port names, no additional mandatory output stage, reset clearing/epochs, timestamp timebase, deterministic seeds, measurement/drain/P99 conventions, and abstract TB tagged completions. They are not mislabeled prior-document requirements, and they do not create another open-ended architecture review.

Missing original reports limit independent provenance verification; Algorithm-2 behavior is now explicitly supplied by the owner. Original PDF provenance remains unverified; FastX connection/library data are execution prerequisites. The numeric common clock/load/SDC profile will be pilot-derived after approved RTL exists, not guessed now. No current area, timing, power, fairness or scheduler coverage result is claimed.

## 5. Approved release and controlled implementation

Spec v1.0 and consistent nonarchitectural defaults are approved by Project owner on2026-10-13 (Asia/Taipei); specs/APPROVAL.md now records the authorization. The frozen commit is recorded after commit in docs/STATUS.md and delegation manifests. Prior source categories describe provenance, not a remaining approval gap.

Common FIFO/descriptor, common output hold, FCFS/model and RR/model are the first controlled implementation milestones. Claude Code RTL Agent Team is the primary implementation/verification agent; Codex independently reviews the shared architecture/RTL/test results before FAI integration. No concurrent conflicting writes. Run WSL lint/cocotb tests after each milestone and stop at failures. Any delegation blocker must be reported instead of silently replacing Claude with Codex-authored RTL.

Approval does not mark any test or PPA complete. At freeze, all scheduler implementation is NOT_STARTED and checks/PPA NOT_RUN. No nine-configuration PPA sweep before integrated functional verification; no synthesis/STA/power claim without real successful executions. Multi-memory, APR and other optional extensions remain deferred.

## 6. Freeze consistency check

Documentation consistency PASS: machine-readable approval, 105-bit packing, 3x3 matrix, Q1-Q3, distinct Main/Algorithm-2 tables and >=31-bit arithmetic. No RTL before freeze. Historical RC holds labeled; setup retained. No scheduler/remote results implied.
