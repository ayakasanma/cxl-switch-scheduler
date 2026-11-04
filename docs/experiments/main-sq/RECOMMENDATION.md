# Main-SQ decision and narrower next step

## Decision

**PASS: baseline reproduction and diagnosis. FAIL: proposed persistent SQ1/SQ2 benefit
gate. Stop before candidate RTL implementation.** This follows the owner's explicit
conditional gate; it is not a waived verification requirement or a successful SQ result.

The original five-seed results are independently reproducible. Main provides useful
trained sparse-request protection relative to FCFS: mean paired P99 reductions45.0292%
for singles and38.6401% for eight-request bursts. RR10 is one cycle worse than Main for
isolated requests but has a lower mean burst P99 (17.2 versus20.8). No policy universally
dominates, and application-level performance is outside this descriptor study.

Actual production seed509 traces identify seven High quota expirations with High work
remaining. A representative tail already alternates High sources, then waits through a
ten-transfer Low visit. All2,400 Main High grants obey oldest-accepted-head selection.
There is some within-class concentration, but changing that order alone fails the
prespecified endpoint: Main/SQ1/SQ2 pooled P99 is24/24/25, with maxima31/34/34. SQ2's
small source3 improvement does not excuse its source2 regression21→29. Sparse admission
backpressure is absent, and classification stays L/H/H/H throughout trained B.

## Owner-facing completion record

| Requested assessment | Status | Conclusion |
| --- | --- | --- |
| Initial P99 independently reproduced | PASS | Original15-run/five-seed archive re-audit plus exact stable-metric representative actual RTL replay. |
| Burst bottleneck diagnosis | PASS | Direct class-quota exhaustion evidence; H2 alone is an ineffective remedy here, H3 is a separate cold-start limit, H4 rejected for sparse full-FIFO delay. |
| Main-SQ RTL change | NOT_RUN | No SQ RTL or model. Only four new passive diagnostic files; original Main/FIFO/hold/interface untouched. |
| SQ1/SQ2 benefit | FAIL | Conditional offline order-only screen: neither improves pooled burst P99 and both worsen maximum/source2. Not an SQ RTL measurement. |
| Functional regression | PASS | Six actual baseline RTL simulations,31,962,468 nonreset cycles, strict lint/build/JUnit and independent trace audit. |
| SQ functional/Formality | NOT_RUN | Candidate implementation stopped at the diagnosis gate; old14 equivalence pairs remain baseline evidence only. |
| SQ area/timing/power overhead | NOT_RUN | No candidate netlist or FastX run; no estimated cost is substituted for measurement. |
| Accepted Main retention | PASS | Preserve it as the approved FAI-inspired baseline. Prefer policies according to measured goal, not a universal winner claim. |
| Main-HQ/Main-AGE implementation | NOT_RUN | Neither authorized by this decision; both require a separate evidence-backed design contract. |

## Main-HQ: plausible hypothesis, not a ready design

Class capacity is a more directly supported next hypothesis than within-class rotation.
A **bounded, separately selectable High-quota sensitivity study** could ask whether more
High service during overlapping sparse bursts reduces their tails without unacceptable
heavy/Low delay or cost. No Main-HQ benefit has been measured and no architecture change
is approved here. This evidence does not satisfy the original stronger condition of
testing HQ after adding per-source fairness; a new owner decision would be needed
to redirect the study directly from this diagnosis.

Before any implementation, define a maximum High visit, guaranteed Low opportunities,
dynamic backlog sampling, empty-class behavior and held-grant/window-boundary context.
Keep the common boundary and25ns profile. Include sparse singles, paired burst tails,
Low/heavy service and waiting, dynamic/stalled traffic and own-netlist equivalence; begin
with a small N4 pilot. Stop if gains merely shift excessive delay onto Low or add timing
depth that fails the accepted target. These are prerequisites for a future experiment,
not claims of completed checks or automatic authorization to proceed.

## Main-AGE: insufficient current justification

The observed31-cycle maximum is not a starvation proof, nor does the data establish
unbounded pathological head delay. An age rescue adds comparator/threshold/context cost
near an already tighter N16 path, while the clearest example is fixed class allocation.
Do not add Main-AGE without a distinct excessive-wait objective and evidence that bounded
rescue addresses it better than a class-quota change. No predicted PPA is claimed.

## Research outcome and boundary

The useful outcome is a **negative microarchitecture screen with an actual RTL-backed
mechanism**, preserving the accepted positive Main-versus-FCFS result and the RR burst
advantage. It narrows what needs optimization and avoids an unsupported policy extension.
It does not prove that all sub-quota definitions fail or that HQ would succeed.

The new production diagnosis is one N4 seed plus a shortened-window infrastructure
sensitivity. General candidate ordering/hold correctness, all-policy single-request nonregression, new hardware costs,
long-term adaptation and arbitrary sink stalls are unmeasured for SQ. Final manuscript,
approved specification, accepted RTL/PPA and previous results remain unchanged.
