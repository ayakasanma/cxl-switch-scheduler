# FAI Algorithm-2 supplement (POLICY=3) implementation derivation

Authority: approved Spec v1.0 at `1af80967bbc2fb83224f4725c4fb450889e69c62`, section 8.6 (with the shared 4, 5, 6, 8.1, 8.3–8.5), D33, Option A in `specs/DECISIONS.md`, and the accepted Main derivation `fai_main.md`. This document derives implementation-level semantics only. It changes no approved architecture, timing, FIFO, hold, descriptor or Main contract. It records no test result; results live in `docs/phase-5-verification/M6-results.md`.

The Algorithm-2 behavior is the owner's supplied account of J. Li et al., FAI-CXL, IEEE ICPADS 2025, Algorithm 2, page 5. No IEEE PDF was inspected locally. Paper behavior here means the state table and immediate target-priority service. The single-output 10/10 alternation, window accounting, reset initialization and common framework are shared project reconstructions. No cycle-identical paper dispatch is claimed.

## 1. Placement: same scheduler block, one compile-time interpretation selector

- `switch_top` POLICY=3 elaborates `gen_policy_fai_alg2.u_fai_sched`. This is the same `cxl_fai_main_sched` module with `INTERP=1` (Algorithm-2). Main stays `gen_policy_fai_main.u_fai_sched`, with `INTERP` left at its default 0 (Main). Any other `INTERP` fails elaboration.
- Both branches share, unchanged: the N `cxl_desc_fifo` (D16, full 105, `TS_EN=1`); the shared 32-bit arrival counter `gen_arrival_ts.arrival_cnt_q`; one `cxl_out_hold`; the 5-bit grant context `{class, used}` (`L_CTX_W=5` for both FAI interpretations); one in-class `cxl_fcfs_sel`; and the candidate, visit/quota, B/S, window-index and threshold logic. Neither branch adds a pipeline, bypass, buffer, debug or preload port.
- `FAI_W`: 5,000,000 production, or 64/256 stress, with the same parameter-derived widths (23-bit B/S/index at production) and 32-bit unsigned zero-extended threshold intermediates.
- Unknown `POLICY` (>= 4) still fails with `switch_top: POLICY=%0d is not a cxl_sched_pkg::policy_e encoding`.

## 2. State encoding (2 bits per source, `cls_q[h]`)

The bit roles are the same as Main's register (bit0 = effective Low, bit1 = buffer flag). The meaning of the buffer bit differs, so Algorithm-2 uses its own enum names:

| Encoding | Algorithm-2 state | Effective class |
| --- | --- | --- |
| 2'b00 | STABLE_HIGH (`A2_STABLE_HIGH`) | High |
| 2'b01 | STABLE_LOW (`A2_STABLE_LOW`) | Low |
| 2'b10 | Buffer, p=High (`A2_BUFFER_P_HIGH`) | High (= target p) |
| 2'b11 | Buffer, p=Low (`A2_BUFFER_P_LOW`) | Low (= target p) |

In Algorithm-2, bit0 is the stored target p. A Buffer is therefore serviced in its target class immediately, with no previous-class retention. The Main names `CLS_B_H` / `CLS_B_L` (previous effective class kept while a change is pending) are never used for Algorithm-2. Reset (spec 5): every source STABLE_HIGH (2'b00), no pending Buffer, visit (High, 0). Reset edges are not window cycles.

## 3. Closing-edge transition (spec 8.6), the only interpretation difference

Evidence comes from the shared closing counts: UP iff `10*N*B_close < 3*S_close`, DOWN iff `N*B_close > S_close`, KEEP otherwise. A zero-service window (`S_close == 0`) naturally gives neither UP nor DOWN, so it is KEEP. Algorithm-2 applies no S=0 cancellation (spec 8.1 Q3).

| Current | UP | DOWN | KEEP / zero-service |
| --- | --- | --- | --- |
| STABLE_HIGH | STABLE_HIGH | Buffer,p=Low | STABLE_HIGH |
| STABLE_LOW | Buffer,p=High | STABLE_LOW | STABLE_LOW |
| Buffer,p=High | STABLE_HIGH | STABLE_LOW | Buffer,p=High |
| Buffer,p=Low | STABLE_HIGH | STABLE_LOW | Buffer,p=Low |

All N sources are classified in parallel on the closing edge. The new state is visible in the next cycle, then B/S/index clear. The closing-edge fire is included and charged to its retained context.

## 4. Unchanged shared rules (from `fai_main.md` sections 3–4)

- Candidate: continue the visit class if it has an eligible head (context {turn, used}), else the other class with {other, 0}, else none. The candidate uses beginning-of-cycle state only. In-class selection is FCFS-oldest with ascending-ID ties.
- Visit/quota: only fire changes it. Each fire is charged to the actually offered (possibly held) grant context. `n == 10` expires the visit. Otherwise post-edge class emptiness under the closing cycle's class map relinquishes the visit. Otherwise the visit continues.
- A held grant keeps its source/class/quota through stalls, Buffer target changes and any number of closings (idle windows included). Its fire is charged to the retained context, and later unlocked selections use the current map.

## 5. Verification-relevant consequences

- At W=5,000,000 with 100,000-cycle traces no window closes, so Algorithm-2 equals Main and FCFS for identical acceptance. Meaningful Main/Algorithm-2 behavior comparisons therefore need W64/W256 changing-class workloads.
- The difference from Main is observable after one DOWN (or UP from Low) window: Main keeps the previous class in B_H/B_L, while Algorithm-2 services the new target at once. On KEEP or an idle window, Main cancels a pending change; Algorithm-2 keeps the Buffer and its target.
