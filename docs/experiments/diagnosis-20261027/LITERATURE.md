# Literature and claim boundary

Checked 2026-10-27. Scope: the allocation/order/observation diagnosis study.
Full-text availability and inspected portions are recorded separately from metadata.
No search can certify that a mechanism is novel.

| Work | Evidence inspected | Relevant mechanism | Comparison required |
|---|---|---|---|
| Shreedhar and Varghese, *Efficient Fair Queueing Using Deficit Round Robin*, SIGCOMM 1995 / ToN 1996 | Prior research session inspected the paper; current Stanford fetch timed out and ACM returned 403 | Deficit accounting across turns and variable packet cost | CGOF overwrite credits and equal-cost descriptors cannot inherit DRR guarantees |
| Tabatabaee, Le Boudec and Boyer, *Interleaved Weighted Round-Robin: A Network Calculus Analysis*, IEICE 2021, DOI 10.1587/transcom.2021ITI0001 | Publisher metadata/abstract and author arXiv v3, introduction and WRR/IWRR definitions | WRR gives a consecutive burst up to the source weight; IWRR spreads opportunities over subrounds | Implement independent WRR/IWRR model controls; same shares do not imply same delays |
| Xi, Arakawa, Murata, Ge and Feng, *Packet-Mode Scheduling with Proportional Fairness for Input-Queued Switches*, 2005, DOI 10.1093/ietcom/e88-b.11.4274 | Author-hosted PDF, sections 3.1–3.3, equations 3–7 | Positive-credit RR master; unrestricted RR fallback; active/waking credit increments at dynamic frame boundaries; negative debt allowed | CGOF uses accepted-head age and overwrites all-source credit vectors at exhaustion, with no negative debt |
| Akesson, Steffens, Strooisma and Goossens, *Real-Time Scheduling Using Credit-Controlled Static-Priority Arbitration*, RTCSA 2008 | Author-hosted PDF, overview and sections 4.1–4.3 | Rate regulator separates eligibility from static-priority selection; incremental service bounds depend on allocated rate | Separating allocation and selection is established; CGOF exhaustion refill differs from rate accrual |
| *FAI-CXL: An Efficient Hardware-Accelerated Fairness-Aware CXL Memory Pool Management with Fine-Grained Cacheline-Level Interleaving*, ICPADS 2025, DOI 10.1109/ICPADS67057.2025.11322896 | Existing project source/spec record; IEEE fetch in this session returned a JavaScript/bot challenge | Exact original pseudocode/full-system details are not newly verified in this session | Retain FAI-inspired wording and project reconstruction boundary; no new full-text performance claims |
| Guo, Shriver and Liu, *Building A CSFQ-Inspired Transport for Switched CXL Memory Pooling*, NSDI 2026, pp. 969–986 | Official USENIX proceedings metadata and abstract; prior research inspected proceedings PDF | MemChannel controls competing memory streams across a real switched CXL pooling path with sender-driven transport and admission/rate control | CXL interference/isolation is established; scheduler findings need boundary mapping and eventual application evidence |

Sources:

- DRR author/course copy: https://web.stanford.edu/class/ee384x/EE384X/papers/DRR.pdf
- WRR/IWRR publisher: https://www.jstage.jst.go.jp/article/transcom/E104.B/12/E104.B_2021ITI0001/_article
- WRR/IWRR author preprint: https://arxiv.org/html/2003.08372v3
- pFS author PDF: https://www.anarg.jp/achievements/annual_report/web2005/papers/kang05IEICE_packetmodefairscheduling.pdf
- CCSP author PDF: https://www.akesson.nl/files/pdf/ccsp-akesson.pdf
- FAI-CXL publisher: https://ieeexplore.ieee.org/document/11322896
- MemChannel official proceedings: https://www.usenix.org/conference/nsdi26/presentation/guo-zerui

These links are literature inputs, not implementation instructions.
The author preprint and final WRR/IWRR publication have different dates; the
implementation must cite the exact version whose algorithm it follows.
No latency-rate theorem, worst-case delay bound or starvation bound transfers to
CGOF without a proof under this project's FIFO, hold, classifier and arrival assumptions.

The measurement contribution must survive matched-allocation controls. If simple
WRR/IWRR or eligible-RR controls explain the Sparse improvement, report that result.
An unexplained difference alone is not proof of algorithm novelty.

## Observation diagnosis

Prior inspected source: Izu and Vallejo, *Impact of Network Fairness on the
Performance of Parallel Systems*, AusPDC 2019, DOI 10.1145/3290688.3290706.
The earlier inspection identified bounded queues and delayed age timestamps as
relevant context. This session did not refetch its full text. Treat observation
boundaries as a known methodological concern; novelty requires a new supported
finding about this scheduler, not merely pointing out that admission hides demand.

Sonntag and Reinig's ANSS 2008 WRR paper remains metadata/abstract-level evidence
in the prior investigation. Do not assert exact refill equivalence from that record.
