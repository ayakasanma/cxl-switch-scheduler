# Source and adaptation boundaries

## Material Passport

- Origin: approved revision plan; direct inspection of locally available full texts.
- Status: source distinctions checked; novelty claim and new performance remain unproved.
- This is an experiment-method record, not a manuscript revision.

## FAI

Primary local source: `docs/final-report/lit-review/fulltexts/fai.pdf`; corresponding
text `fai.txt:461-478` contains Algorithm2, and `fai.txt:755-764` gives evaluation
parameters. The inspected original supplies per-host B, a transitional Buffer with
stored target priority, within-class FCFS, RR10, High/Low10 and W5 million/theta0.3.
The project's Main previous-effective-class hysteresis is a separately declared
reconstruction. Algorithm-2 target-priority Buffer is retained as another policy.
Neither is described as a cycle-identical implementation of the full paper/system.

Main-1W retains the same thresholds, window, metadata, FIFO/hold and service cost;
UP immediately makes effective High, DOWN Low, KEEP/zero retains effective class.
The implementation has its own stable-state encoding. Inspection of the accepted
Algorithm-2 transition table reveals that its effective class follows this same
rule for every state/evidence pair. At the default10/10 quota the two therefore
have the same pin behavior from reset, despite different internal class encodings.
The15 baseline-model unit tests include a literal-table check and randomized
cycle comparisons of this relationship. This is model evidence; RTL comparison
is still pending. Preserve the approved matrix, but treat equal results as an
expected consistency control, not independent evidence for two distinct mechanisms.
The comparison against Main isolates effective-transition delay.
Quota sweeps isolate class allocation rather than changing source ordering as well.
Existing Algorithm-2 production20M/four W5M windows are real evidence to retain.

## BLISS

Primary local source: `docs/final-report/lit-review/fulltexts/bliss.pdf`, sectionIV-A/B.
The text version `bliss.txt:473-500` makes the service-counter convention explicit.
On a changed application the counter becomes0; a repeated application increments it.
Blacklisting occurs when the updated counter exceeds4, followed by counter reset0.
With this convention the first blacklist in a fresh same-source streak occurs on the
sixth service. Clearing interval10000 is in `bliss.txt:490-491` and `:623-624`.

| Mechanism | Original | Descriptor adaptation |
| --- | --- | --- |
| Identity | Application/hardware context | Request source |
| Streak event | Issued memory request | Successful descriptor fire only |
| Counter | Change->0; repeat->increment; >4->blacklist/reset0 | Preserve this convention, including first-service/no-previous handling |
| Priority | Nonblacklisted, then row hit, then older | Nonblacklisted, then oldest admitted FIFO head/source-ID |
| Periodic clear | Every10000 cycles | Nonreset cycles; explicit clear-before-next-cycle observation |
| Boundary ordering | No project RTL edge contract | Clear wins simultaneous new blacklist; last/count still update |
| Output stall | DRAM command context | Common retained grant; clear cannot preempt it |
| Cost | DRAM scheduler context | Whole descriptor/FIFO/timestamp/hold/policy boundary |

Idle and output stalls do not count as service or reset the consecutive-service streak.
This adaptation is called BLISS-inspired descriptor scheduling. Omitting row hits and
using equal-cost descriptors rules out a direct claim about original DRAM BLISS results.
The clear/fire ordering is an experimental convention to test, not an original-paper
hardware timing claim.

## RCCC and NSCC inspiration

Version anchors supplied in the approved plan are UE1.0 p359 (RCCC) and UE1.0.2
section3.6.13 p377 (NSCC). Preserve these exact version anchors; do not present them as
an exhaustive statement of the latest UET release.

DAC uses local valid heads and declared per-source weights. It does not observe every
unsatisfied upstream request and does not implement receiver-issued network credits.
2:1 class weights establish service entitlement; they are not a measured flow-demand
estimate. DAC replaces class visit allocation, unlike Main-SQ's fixed-visit reordering.

AGE uses admitted-head age plus locally counted ready opportunities. It neither measures
network RTT nor consumes ECN. The fast/slow feedback analogy motivates an experimental
question; it does not establish protocol conformance, stability or new scheduling theory.
The max-gap selector and rescue cap must be evaluated against age-only and normal Main.

## Novelty and claims gate

Until the matched controls, ablations, literature comparison and confirmation runs exist,
describe DAC/AGE as experimental mechanisms inspired by prior ideas. Baseline source
attribution does not establish novelty. A candidate selected for limited RTL resources
is not an overall winner. No application slowdown, full-CXL fairness, flow-level demand,
hard starvation bound or network congestion-control result follows from these experiments.
