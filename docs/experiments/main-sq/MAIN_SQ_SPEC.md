# Main-SQ candidate and design-screen contract

Status: **SCREENED / NOT_IMPLEMENTED**. The owner made RTL implementation conditional
on a demonstrated plausible benefit from within-class arbitration. That gate failed for
the diagnosed trained-burst endpoint. This document defines the diagnostic screen precisely; it is
not an amendment to Spec v1.0 or a claim of an implemented SQ scheduler.

## Preserved architectural boundary

Any future separately selectable SQ must preserve N4/8/16, D16, M1, descriptor105,
the common FIFO/input/output-hold/timing contract, no bypass, no extra visible pipeline,
per-source FIFO order and fire-only charging. Accepted Main retains its previous-effective
four-state classifier, W5M, B/S counters/thresholds, two-window hysteresis and class10/10.
No original policy encoding or metadata storage is silently replaced.

## Precisely evaluated software screen

The offline analysis reassigns **observed Main High slots**, holding sparse admission cycles
and the L/H/H/H map fixed. It checks capacity, order, completion and total completion-time
sum. It is an order-only counterfactual, not an RTL simulator or an independent golden model
for a new scheduler. The observed Low slots and their quota phase remain unchanged.

| Rule | Screen definition |
| --- | --- |
| Selection/ties | Search cyclically from a persistent High source pointer among sources1/2/3; choose the first nonempty FIFO. No timestamp tie break. |
| Source sub-quota | SQ1 permits1 and SQ2 permits2 successful High fires per source turn. Only a successful observed High slot charges it. |
| Empty mid-turn | After pop and accepted pushes, if the selected FIFO is empty, advance the pointer and discard residual credit. Skip currently empty sources without spending a slot. |
| Simultaneous push/pop | Select from pre-edge queues. Append admissions afterward. Refuse the fixed-admission assumption if a source was full before the edge, even if popped on that edge. |
| Class visits | Preserve the actual Main class-slot sequence; preserve source pointer and partial SQ2 use across Low service. This is one explicit carry policy, not every possible refill policy. |
| Held grants/class changes | Not modelled: the diagnosed B interval has ready1 and fixed classes. A synthesizable candidate would need retained source/sub-quota context across stalls and reclassification. |
| Initialization | B starts with empty sparse FIFOs after the guard. Evaluate initial pointer1/2/3; sub-quota usage initially0. These are sensitivity settings, not independent random samples. |
| Waiting guarantees | None claimed. Finite observed maximum is not WCET or a universal starvation bound. Overload, arbitrary stalls and changing class membership are outside the screen. |
| FCFS property | Intentionally gives up within-class FCFS, while preserving each source's FIFO order. No strict global FCFS claim. |

When only one High source is nonempty, every available High slot still serves it. If any
shadow FIFO would refuse an observed admission, or the shadow cannot consume an observed
High slot, the screen rejects its own assumptions instead of silently changing traffic.

## Gate before a future RTL contract

If a future, separately justified screen supports SQ, resolve general N/class pointer state,
sub-quota context encoding, class-entry/removal, held-grant charging at a classification
boundary and reset behavior in a separate reviewed extension. Explicitly specify timestamp
retention/pruning; do not silently attribute storage savings to selector-only improvements.
The common hold controller remains shared. Unknown-policy negative elaboration checks
must move when adding policy codes4/5; the current2-bit enum is fully occupied.

No Main-HQ or Main-AGE implementation is authorized by this document.
