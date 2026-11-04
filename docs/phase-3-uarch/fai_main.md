# FAI-inspired Main (POLICY=2) implementation derivation

Authority: approved Spec v1.0 at `1af80967bbc2fb83224f4725c4fb450889e69c62`, sections 4, 5, 6, 8.1-8.5, Q1-Q3 (D08, D12, D25-D27, D35), and the accepted common framework (`common_framework.md`, `reviews/phase-4-rtl/codex-common-review.md`). This document derives implementation-level semantics only. It changes no approved architecture, timing, FIFO, hold or descriptor contract. It records no implemented or tested RTL; results live in `docs/phase-5-verification/M5-results.md`. Algorithm-2 (POLICY=3, spec 8.6) is specified separately in fai_alg2.md and implemented by the shared scheduler with INTERP=1; Main remains the default INTERP=0. Current results and limits are in docs/STATUS.md and M6-results.md.

## 1. Placement in the common framework

- The same `switch_top`, N `cxl_desc_fifo` (D16, full105, `TS_EN=1`), one `cxl_out_hold`, and the same ports, sink and timing. FAI adds only policy-slot logic: no pipeline, bypass, buffer, debug or preload port.
- Arrival metadata: the existing shared 32-bit free-running counter and per-entry timestamps (FCFS/FAI only). RR stays without timestamps.
- The class/quota context of the offered grant uses the generic `cxl_out_hold` context (`CTX_W`) without changing hold behavior. FCFS and RR keep `CTX_W=1`. FAI uses `CTX_W = 1 (class) + 4 (visit fires already charged, 0..9) = 5`.
- One `cxl_fcfs_sel` instance selects inside the chosen effective class. Its eligible mask is `head_valid` restricted to that class. Modular-oldest timestamp order applies, with ties going to ascending source ID and age < 2^31.
- Parameter `FAI_W` (window cycles), default 5,000,000. Supported values: 5,000,000 (production/primary) and stress-only 64 and 256. Any other value fails elaboration. Counters are parameter-derived: index `ceil(log2 W)` bits, B/S `ceil(log2(W+1))` bits. Both are 23 bits at production W and 6/7 and 8/9 bits at W64/W256.

## 2. State

| State | Meaning | Reset (spec 5, Q1) |
| --- | --- | --- |
| `cls[h]` in {H, B_H, L, B_L} | Main four-state class; effective High iff H or B_H | all H |
| `idx` | window index 0..W-1 | 0 |
| `B[h]`, `S` | window-local successful-fire counts, `S = sum(B)` always | 0 |
| `turn` in {High, Low}, `used` 0..9 | class of the current visit, successful fires already charged to it | High, 0 |
| held grant (common hold) | source + context {class, used} of a stalled offer | invalid |

## 3. Candidate (beginning-of-cycle state only)

`elig_hi = head_valid & effHigh`, `elig_lo = head_valid & ~effHigh`. The current classes are those visible this cycle.

1. If the `turn` class has an eligible head: the candidate is the FCFS-oldest head of that class, with context {turn, used}. The visit continues.
2. Otherwise, if the other class has an eligible head: the candidate is the FCFS-oldest head of the other class, with context {other, 0}. This is a new visit with renewed quota. The unused quota of the empty `turn` class is relinquished (no banking).
3. Otherwise there is no candidate and nothing is consumed (both-empty retains the turn).

The candidate never depends on `i_out_ready`, fire or pop of the same cycle. Whenever any head is valid a candidate exists, so there are no control-only bubbles (spec 5, 8.3). While a grant is held, the hold controller ignores the candidate (spec 4, 8.3).

## 4. Edge update (every non-reset edge)

Let `fire`, the offered source `g` and the offered context `{Cg, Ug}` come from the common hold controller. These are the retained values if held, which can differ from this cycle's candidate. Let `pop[h] = fire && g == h`.

**Quota/visit (spec 8.3, Q2; RR-Q2 analogue).** Only on `fire`:
- `n = Ug + 1`.
- `class_live` is true iff some source `h` whose effective class in the class map of this cycle equals `Cg` has post-edge occupancy `count[h] + push[h] - pop[h] > 0`. Same-edge replacement or new pushes count.
- If `n == 10`, the visit expires: `turn <- not Cg`, `used <- 0`. This holds even with replacement or a still-nonempty class. Otherwise, if `!class_live`, the visit empties: `turn <- not Cg`, `used <- 0`, and the unused quota is relinquished. Otherwise the visit continues: `turn <- Cg`, `used <- n`.
- Without `fire` (idle, both empty, stall/held), `turn`/`used` are unchanged. Windows and classifications never reset `turn`/`used` independently (Q2).

Derived convention: at a closing edge, `class_live` uses the class map in force during the closing cycle, not the new classification. Spec 8.4 step 1 commits the transfer and its quota context before step 3 classifies. Steps 4/8.1 expose the new classification only in the following cycle. Any visit then continuing into a class the new map leaves empty is relinquished by rule 3.2 in the next cycle without a bubble.

**Window accounting (spec 8.1, 8.4, Q3).** On every non-reset edge, including stalls and idle cycles:
- If `idx != W-1` (non-closing edge): `idx <- idx+1`, `B[g] += fire`, `S += fire`.
- If `idx == W-1` (closing edge), with every source classified in parallel in the same edge:
  1. `B_close[h] = B[h] + pop[h]`, `S_close = S + fire`. The closing-edge fire is included and charged to its retained context for quota as above.
  2. Using unsigned 32-bit intermediates with zero-extended operands:
     - UP iff `(10*N)*B_close[h] < 3*S_close`
     - DOWN iff `N*B_close[h] > S_close`
     - KEEP otherwise, including equality
     - S0 iff `S_close == 0` (explicit Main cancellation; all B are then 0 and it coincides with KEEP)
     - UP and DOWN are mutually exclusive.
  3. `cls[h] <-` the table below, from the current `cls[h]` and the evidence.
  4. `B <- 0`, `S <- 0`, `idx <- 0`. The new `cls` is visible from the next cycle.
  5. A held grant is unaffected and later fires with its retained {source, class, used}.

| Current / effective | UP | DOWN | KEEP | S=0 |
| --- | --- | --- | --- | --- |
| H / High | H | B_H | H | H |
| B_H / High | H | L | H | H |
| L / Low | B_L | L | L | L |
| B_L / Low | H | L | L | L |

Bounds: `0 <= B[h] <= S <= W`, and at N16, W5,000,000 the maximum product is 800,000,000 < 2^32. Truncation, sign extension, division, rounding, serialized or multicycle classification, and false-path workarounds are all forbidden.

**Reset edge (`rst_n=0`).** All state in section 2 returns to reset values. The common blocks clear occupancy, pointers, held validity and the arrival counter. Reset edges are not window cycles: the first non-reset edge after reset has pre-edge `idx=0`, and the W-th non-reset edge closes the window.

## 5. Verification-relevant consequences

- Under the primary 100,000-cycle traces with W=5,000,000, no window closes. Every source stays H, every visit is High and an empty Low class renews High immediately. The selected source sequence therefore equals FCFS for an identical acceptance history. This is an observation for cross-checking, not a substitute for the separately required W64/W256 stress and three-window production evidence.
- Externally visible decisions derived above that reviewers should confirm: the post-edge class-emptiness rule (RR-Q2 analogue), and the closing-edge class map used for `class_live`. No other new choice is introduced. Neither changes the frozen Spec text.
