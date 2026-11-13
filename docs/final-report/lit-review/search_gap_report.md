# CXL Scheduler Literature Search and Gap Report

Prepared: 2026-10-21  
Scope: targeted, non-systematic literature search for hardware implementation and PPA evidence relevant to CXL switch scheduling

## Scope and Result

This pass treats the 20 sources supplied by the user as an exclusion set and searches for
additional peer-reviewed work connecting CXL memory pooling or interference to arbitration,
QoS/fairness, and hardware implementation cost. It is deliberately targeted and does not
claim systematic-review coverage.

Twenty new sources were retained. Each has a Crossref record and a successful DOI
resolver redirect, checked on 2026-10-21. No retained DOI is `UNVERIFIED`. The set includes
peer-reviewed workshops as well as full conferences and journals; workshop items are useful
for architecture and current-system evidence, but should not be presented as the strongest
PPA evidence.

**Main finding.** The retained literature establishes three separate facts: CXL switches and
pools are now real enough to be prototyped and measured; multi-host CXL creates latency,
bandwidth, and fairness problems; and both DRAM controllers and network switches have
hardware mechanisms for QoS and fair queueing. Within this targeted pass, however, no paper
provides a controlled, like-for-like area/timing/power comparison of alternative CXL
switch-side arbitration policies under one RTL boundary. That is the narrow gap this
literature review can responsibly identify.

## New Candidate Sources

Check notation: `C200` means `https://api.crossref.org/works/<DOI>` returned HTTP 200;
`D302` means `https://doi.org/<DOI>` returned HTTP 302 to a publisher or repository landing
page.

### CXL Switching, Pooling, and Hardware Architecture

1. **Miryeong Kwon; Seungjun Lee; Donghyun Gouk; Hongjoo Jung; Eojin Ryu; Seyeong Huh;
   Junseok Moon; Hyein Woo; Junhee Kim; Kyungkuk Nam; Jinwoo Baek; Hyunkyu Choi;
   Woojin Choi; Yongjin Cho; Myoungsoo Jung.** "A Silicon-Proven Unified Low-Latency CXL
   Controller and Port-Based Routing Switch for Memory-Centric Fabrics." *2026 ACM/IEEE
   53rd Annual International Symposium on Computer Architecture (ISCA)*, 2026, pp. 688-702.
   DOI: `10.1109/ISCA66397.2026.00060`. **Relevance:** This is the closest direct hardware
   precedent, presenting a 4 nm CXL controller and port-based routing switch with fixed-cycle
   hardware pipelines for routing and arbitration. **Check:** C200; D302 to IEEE Xplore.

2. **Laurin Martins; Alexander Baumstark; Andreas Becher; Kai-Uwe Sattler.**
   "Characterizing Multi-Host CXL 2.0: Latency, Bandwidth, and Synchronization Costs."
   *Proceedings of the 22nd International Workshop on Data Management on New Hardware
   (DaMoN '26)*, 2026, pp. 1-8. DOI: `10.1145/3789237.3809131`. **Relevance:** It measures a
   commercially available switched CXL 2.0 pool across multiple hosts, observing latency and
   bandwidth penalties and discussing fair sharing and synchronization constraints that
   motivate arbitration work.
   **Check:** C200; D302 to ACM Digital Library.

3. **Daniel S. Berger; Daniel Ernst; Huaicheng Li; Pantea Zardoshti; Monish Shah;
   Samir Rajadnya; Scott Lee; Lisa Hsu; Ishwar Agarwal; Mark D. Hill; Ricardo Bianchini.**
   "Design Tradeoffs in CXL-Based Memory Pools for Public Cloud Platforms." *IEEE Micro*,
   vol. 43, no. 2, 2023, pp. 30-38. DOI: `10.1109/MM.2023.3241586`. **Relevance:** It frames
   pool size, reach, and topology as coupled performance, virtualization, management, and
   deployment-cost decisions that constrain where a switch scheduler can sit. **Check:** C200;
   D302 to IEEE Xplore.

4. **Xingyu Chen; Fei Wang; Yuan Tian; Shan Zhao; Xiaoyong Xue; Xiaoyang Zeng.** "PipeCHX:
   A High-Bandwidth-Low-Latency Hybrid CXL Memory Controller." *IEEE Transactions on Very
   Large Scale Integration (VLSI) Systems*, vol. 34, no. 4, 2026, pp. 1253-1266.
   DOI: `10.1109/TVLSI.2026.3658749`. **Relevance:** Its FPGA prototype explicitly addresses
   controller area pressure, collisions, throughput, and latency, making it a useful
   implementation-level comparator for CXL datapath and control overhead. **Check:** C200;
   D302 to IEEE Xplore.

5. **Taejeong Kim; Junbum Park; Yongho Lee; Seokin Hong.** "DDLM: Demand-Aware Dynamic Link
   Width Management for Energy-Efficient CXL Memory." *2025 IEEE 43rd International
   Conference on Computer Design (ICCD)*, 2025, pp. 201-208.
   DOI: `10.1109/ICCD65941.2025.00035`. **Relevance:** It adds queue-based congestion
   monitoring and energy-aware control to a CXL memory path, providing PPA-adjacent evidence
   that runtime queue state can drive hardware power/performance tradeoffs. **Check:** C200;
   D302 to IEEE Xplore.

6. **Yuhong Zhong; Daniel S. Berger; Pantea Zardoshti; Enrique Saurez; Jacob Nelson;
   Antonis Psistakis; Joshua Fried; Asaf Cidon.** "My CXL Pool Obviates Your PCIe Switch."
   *Proceedings of the Workshop on Hot Topics in Operating Systems (HotOS '25)*, 2025,
   pp. 58-66. DOI: `10.1145/3713082.3730393`. **Relevance:** It argues that a CXL memory pool
   can replace a costly PCIe switch for device pooling, directly motivating CXL fabric
   flexibility and hardware-cost tradeoffs. **Check:** C200; D302 to ACM Digital Library.

7. **Tianchan Guan; Yijin Guan; Zhaoyang Du; Jiacheng Ma; Boyu Tian; Zhao Wang; Teng Ma;
   Zheng Liu; Yang Kong; Yuan Xie; Mingyu Gao; Guangyu Sun; Hongzhong Zheng; Dimin Niu.**
   "MemTunnel: A CXL-Based Rack-Scale Host Memory Pooling Architecture for Cloud Service."
   *IEEE Transactions on Parallel and Distributed Systems*, vol. 36, no. 11, 2025,
   pp. 2182-2197. DOI: `10.1109/TPDS.2025.3598190`. **Relevance:** It proposes and
   FPGA-prototypes a symmetric, memory-semantic rack-scale CXL pooling architecture with low
   hardware overhead, giving concrete fabric and endpoint context for scheduler placement.
   **Check:** C200; D302 to IEEE Xplore.

8. **Albert Cho; Anish Saxena; Moinuddin Qureshi; Alexandros Daglis.** "CoAXIAL: A
   CXL-Centric Memory System for Scalable Servers." *SC24: International Conference for High
   Performance Computing, Networking, Storage and Analysis*, 2024, pp. 1-15.
   DOI: `10.1109/SC41406.2024.00101`. **Relevance:** It evaluates replacing server DDR
   interfaces with CXL and links pin-efficient bandwidth to request queueing delays, clarifying
   why CXL fabric organization affects memory-service pressure. **Check:** C200; D302 to IEEE
   Xplore.

9. **Shu-Ting Wang; Weitao Wang.** "Aurelia: CXL Fabric with Tentacle." *Proceedings of the
   4th Workshop on Resource Disaggregation and Serverless*, 2023, pp. 29-36.
   DOI: `10.1145/3605181.3626287`. **Relevance:** It treats addressing, routing, and transport
   as network layers to scale CXL fabrics toward thousands of endpoints, directly motivating
   scalable switch state and routing decisions. **Check:** C200; D302 to ACM Digital Library.

10. **Albert Cho; Alexandros Daglis.** "StarNUMA: Mitigating NUMA Challenges with Memory
    Pooling." *2024 57th IEEE/ACM International Symposium on Microarchitecture (MICRO)*,
    2024, pp. 997-1012. DOI: `10.1109/MICRO61859.2024.00077`. **Relevance:** It places
    shared "vagabond" pages in a single-hop CXL pool to reduce multi-hop NUMA latency and
    queueing, showing the system value and interference sensitivity of CXL fabric topology.
    **Check:** C200; D302 to IEEE Xplore.

11. **Chenjiu Wang; Ke He; Ruiqi Fan; Xiaonan Wang; Wei Wang; Qinfen Hao.** "CXL over
    Ethernet: A Novel FPGA-based Memory Disaggregation Design in Data Centers." *2023 IEEE
    31st Annual International Symposium on Field-Programmable Custom Computing Machines
    (FCCM)*, 2023, pp. 75-82. DOI: `10.1109/FCCM57271.2023.00017`. **Relevance:** Its
    FPGA-based remote-memory prototype puts cache and congestion control on the critical
    access path, providing a concrete disaggregated implementation reference even though it
    is not native CXL switch arbitration. **Check:** C200; D302 to IEEE Xplore.

### CXL Interference, Fairness, and Evaluation Methods

12. **Roberto Gioiosa; Bo Fang; Lenny Guo; Andres Marquez.** "Hardware-Software
    Co-Development for Emerging CXL Architectures." *Proceedings of the International
    Symposium on Memory Systems (MEMSYS '25)*, 2025, pp. 1-7.
    DOI: `10.1145/3767110.3767113`. **Relevance:** It combines a CXL full-system emulator,
    allocator, and benchmark suite, including a switch-attached configuration, giving a
    method for studying scheduler effects before silicon is available. **Check:** C200; D302
    to ACM Digital Library.

13. **Wenda Tang; Yiduo Wang; Yanwen Wang; Jie Wu.** "Leave No One Behind: Fair and
    Efficient Tiered Memory Management for Multi-Applications." *Proceedings of the 54th
    International Conference on Parallel Processing (ICPP '25)*, 2025, pp. 699-709.
    DOI: `10.1145/3754598.3754626`. **Relevance:** Vulcan explicitly targets multi-tenant
    interference and QoS-aware fair partitioning for tiered memory, providing a fairness
    formulation and metrics that a hardware scheduler study should acknowledge. **Check:**
    C200; D302 to ACM Digital Library.

### Fairness, QoS, and Hardware Scheduling Foundations

14. **Robert MacDavid; Xiaoqi Chen; Jennifer Rexford.** "Scalable Real-Time Bandwidth
    Fairness in Switches." *IEEE INFOCOM 2023 - IEEE Conference on Computer Communications*,
    2023, pp. 1-10. DOI: `10.1109/INFOCOM53939.2023.10228997`. **Relevance:** AHAB implements
    max-min bandwidth fairness entirely in the switch data plane using bounded sketch state
    instead of per-user queues, a strong precedent for trading exactness against hardware
    state. **Check:** C200; D302 to IEEE Xplore.

15. **Aswathy N S; Arnab Sarkar; Hemangee Kapoor.** "A Predictable QoS-aware Memory Request
    Scheduler for Soft Real-time Systems." *ACM Transactions on Embedded Computing Systems*,
    vol. 22, no. 2, 2023, pp. 1-25. DOI: `10.1145/3561052`. **Relevance:** It converts
    per-request latency budgets into urgency-based memory arbitration, supplying a concrete
    QoS policy that can be compared with age- or quota-based CXL schedulers. **Check:** C200;
    D302 to ACM Digital Library.

16. **Aswathy N.S.; Hemangee K. Kapoor.** "Migration-aware slot-based memory request
    scheduler to guarantee QoS in DRAM-PCM hybrid memories." *Journal of Systems
    Architecture*, vol. 152, 2024, Art. 103174.
    DOI: `10.1016/j.sysarc.2024.103174`. **Relevance:** It proposes slot-based,
    migration-aware QoS scheduling for heterogeneous memory, illustrating how additional
    migration state complicates a memory-side arbiter. **Check:** C200; D302 to Elsevier.

17. **Hyuk-Jun Lee; Eui-Young Chung.** "Scalable QoS-Aware Memory Controller for
    High-Bandwidth Packet Memory." *IEEE Transactions on Very Large Scale Integration (VLSI)
    Systems*, vol. 16, no. 3, 2008, pp. 289-301. DOI: `10.1109/TVLSI.2007.915367`.
    **Relevance:** It uses hashing and a bounded reorder buffer plus feedback control to make
    a QoS-aware memory controller scale with output-queue count, a useful hardware-state
    precedent for shared CXL pools. **Check:** C200; D302 to IEEE Xplore.

18. **Ali Abbasi; Danesh Germchi; Amin Katani; Mohamed Hassan; Rodolfo Pellizzoni.**
    "OpenDRAM: A Modular, High-performance Soft Memory Controller for DDR4 DRAM." *ACM
    Transactions on Reconfigurable Technology and Systems*, vol. 18, no. 4, 2025,
    pp. 1-27. DOI: `10.1145/3772724`. **Relevance:** It synthesizes an extensible FPGA memory
    controller and prototypes five command schedulers while measuring scheduling
    aggressiveness against maximum frequency, providing a close methodological precedent for
    policy-level hardware cost. **Check:** C200; D302 to ACM Digital Library.

19. **Kieran McLaughlin; Dwayne Burns; Ciaran Toal; Colm McKillen; Sakir Sezer.** "Fully
    hardware based WFQ architecture for high-speed QoS packet scheduling." *Integration*,
    vol. 45, no. 1, 2012, pp. 99-109. DOI: `10.1016/j.vlsi.2011.01.001`. **Relevance:** It
    presents a fully hardware-based weighted-fair-queueing architecture, providing a direct
    implementation precedent for tag, queue, and arbitration logic in a switch datapath.
    **Check:** C200; D302 to Elsevier.

20. **Onur Mutlu; Thomas Moscibroda.** "Parallelism-Aware Batch Scheduling: Enhancing both
    Performance and Fairness of Shared DRAM Systems." *2008 International Symposium on
    Computer Architecture (ISCA)*, 2008, pp. 63-74. DOI: `10.1109/ISCA.2008.7`.
    **Relevance:** PAR-BS uses request batches and bank-parallelism-aware priorities to improve
    fairness while preserving throughput, making it a useful algorithmic baseline for
    implementation-cost comparisons. **Check:** C200; D302 to IEEE Xplore.

## Rejected or Screened-Out Candidates

These identifiers were examined but are not appropriate for the peer-reviewed core list.
DOI checks were still performed so that the reasons are auditable.

| Candidate | Reason for rejection | DOI check |
|---|---|---|
| Mercury: QoS-Aware Tiered Memory System. DOI: `10.48550/arXiv.2412.08938` | Highly relevant QoS/tiering topic, but the record is an arXiv preprint rather than a peer-reviewed venue paper. | Crossref 404; DataCite 200 as `Preprint`; `doi.org` 302 to arXiv. Resolved, not Crossref-indexed. |
| Equilibria: Fair Multi-Tenant CXL Memory Tiering At Scale. DOI: `10.48550/arXiv.2602.08800` | Very tempting because it names fair multi-tenant CXL tiering, but it is an arXiv preprint with no verified peer-reviewed venue. | Crossref 404; DataCite 200 as `Preprint`; `doi.org` 302 to arXiv. Resolved, not Crossref-indexed. |
| Host Congestion Control. DOI: `10.1145/3603269.3604878` | Peer-reviewed SIGCOMM work, but its control point is the end host and network transport, not the CXL switch's memory-request arbitration or PPA. | C200; D302 to ACM Digital Library. |
| CXL-Tracer: Accurate, Full-System Memory Tracing on Commercial Hardware via CXL Memory. DOI: `10.1109/LCA.2026.3673181` | Useful instrumentation and observability work, but it does not study arbitration, QoS, or scheduler hardware cost. | C200; D302 to IEEE Xplore. |
| CXL-ECC: an Efficient LRC-based on-CXL-Memory-eXpander-Controller ECC to Enhance Reliability and Performance of DRAM Error Correction. DOI: `10.1109/DAC63849.2025.11133097` | Tempting because it is a CXL expander-controller hardware paper, but its contribution is ECC reliability, not scheduling or fair arbitration. | C200; D302 to IEEE Xplore. |
| FANS: A Fairness-Aware and QoS-Enhanced Scheduler for ZNS SSDs in Shared Environments. DOI: `10.1109/TCAD.2026.3674444` | "Fairness-aware" and "QoS-enhanced" are relevant terms, but the device boundary is a ZNS SSD rather than a CXL memory fabric or switch. | C200; D302 to IEEE Xplore. |

### Included systems comparison: MemChannel

Corrected 2026-10-27 using official USENIX proceedings: Guo, Shriver and Liu,
*Building A CSFQ-Inspired Transport for Switched CXL Memory Pooling*, NSDI 2026,
pp. 969–986, https://www.usenix.org/conference/nsdi26/presentation/guo-zerui .
This is a published systems comparison, covering transport and admission control
across switched CXL memory pooling. Its arXiv record does not replace the
peer-reviewed publication or justify screening it out as an unreviewed preprint.

## Search Gap Assessment

1. **CXL switch and fabric papers provide architecture but rarely policy-level PPA.**
   ISCA 2026 is silicon-proven and explicitly includes hardware arbitration, while MemTunnel,
   CoAXIAL, Aurelia, StarNUMA, and CXL-over-Ethernet establish implementation and topology
   choices. They do not isolate FCFS, round robin, and fairness-aware policies under one RTL
   boundary with comparable area, timing, and power accounting.

2. **CXL system studies establish the interference and fairness problem.** DaMoN 2026,
   Pond-adjacent pool design work, Vulcan, and the user's CXL-interference sources show that
   multi-host sharing creates nontrivial latency, bandwidth, coherence, and tenant-fairness
   costs. Their metrics are predominantly application, trace, or full-system metrics rather
   than standard-cell or netlist metrics.

3. **Hardware scheduling precedents are split across device boundaries.** The TVLSI memory
   controller, OpenDRAM, hardware WFQ, AHAB, TECS QoS scheduler, and PAR-BS show how to reason
   about priority, tags, batches, bounded state, and feedback. None combines CXL switch
   semantics with a like-for-like PPA comparison of alternative arbitration policies.

4. **Actionable gap for this report.** A defensible course-report claim is therefore narrow:
   build one CXL-oriented descriptor-level arbitration slice, hold the datapath and synthesis
   recipe fixed, vary only the policy and policy-required metadata, and report area, timing,
   and qualified power separately. The contribution is a hardware-cost case study, not a new
   CXL switch, a production fairness guarantee, or a replacement for full-system evaluation.

## One-Page Search Log

| Item | Record |
|---|---|
| Date | 2026-10-21 |
| Objective | Find peer-reviewed work connecting CXL pooling/interference to arbitration, QoS/fairness, and hardware implementation or PPA cost. |
| Databases and APIs | Crossref REST API (metadata and DOI verification); OpenAlex API (discovery and citation chasing); `doi.org` resolver (redirect checks); DataCite API (preprint records for rejected arXiv candidates); Semantic Scholar Graph API (abstract cross-checks only, with intermittent HTTP 429). |
| Crossref query families | `CXL switch scheduler fairness QoS`; `CXL memory pool bandwidth fairness arbitration`; `CXL switch hardware architecture`; `CXL switch arbitration`; `CXL memory pooling QoS`; `CXL fabric switch architecture`; `CXL memory controller arbitration hardware`; `CXL multi-tenant memory fairness`; `CXL pooling interference fairness`; `input-queued switch scheduling fairness hardware`; `hardware fair queueing packet scheduler VLSI`; `memory controller scheduling QoS hardware implementation area power`; `switch scheduling fairness hardware implementation`; `memory controller QoS hardware area`; `fair queueing hardware FPGA`. |
| OpenAlex query families | `CXL memory pooling`; `CXL memory disaggregation`; `CXL QoS`; `CXL switch`; `CXL fabric architecture`; `CXL routing switch`; `CXL fairness`; `CXL multi-tenant memory`; title/abstract probes for `CXL switch`, `CXL fabric`, `CXL pooling`, `CXL memory pool`, and `CXL arbitration`. |
| Citation chasing | Backward and forward traversal from Pond, A Case Against CXL Memory Pooling, and BLISS; FAI-CXL used as a known-item anchor; DOI/title checks for newly surfaced CXL switch, pool, and QoS records. |
| Screening rules | Prefer CXL work from 2022-2026; retain older classic memory-controller and switch-scheduling papers only when they inform arbitration or hardware implementation; require DOI resolution; exclude preprints, instrumentation-only work, storage-device QoS, ECC, and coherence-only papers unless they directly motivate fabric scheduling or hardware cost. Filter false positives where "CXL" means corneal cross-linking or unrelated history. |
| Verification | Queried `https://api.crossref.org/works/<DOI>` and checked `https://doi.org/<DOI>` for every candidate. All 20 retained records returned Crossref HTTP 200 and a DOI resolver HTTP 302. The seven rejected records were also checked; the three arXiv DOIs resolve through `doi.org` but are DataCite preprints, not Crossref journal/conference records. |
| Outcome | 20 new peer-reviewed candidates retained; 7 tempting but unsuitable records rejected. No systematic-review or PRISMA-completeness claim is made. |

## Recommended Priority Sources

1. `10.1109/ISCA66397.2026.00060` - direct silicon CXL controller/router with hardware
   routing and arbitration; highest architectural relevance.
2. `10.1145/3789237.3809131` - empirical multi-host switched CXL 2.0 latency, bandwidth, and
   fair-sharing evidence.
3. `10.1109/TVLSI.2026.3658749` - FPGA CXL controller prototype with explicit area, latency,
   and collision tradeoffs.
4. `10.1109/MM.2023.3241586` - pool topology and deployment-cost constraints for public-cloud
   CXL.
5. `10.1109/INFOCOM53939.2023.10228997` - scalable switch-side bandwidth fairness with bounded
   state rather than per-user queues.
6. `10.1109/TVLSI.2007.915367` - hardware QoS memory controller with scalable buffering and
   feedback control.
7. `10.1145/3772724` - synthesizable memory-controller study that compares scheduler variants
   against maximum frequency.
8. `10.1016/j.vlsi.2011.01.001` - fully hardware WFQ architecture, the clearest fair-queueing
   implementation precedent.

## Verification Notes

- Crossref supplied the author lists, titles, venues, years, volumes, and pages used above.
- `10.1109/ISCA.2008.7` was selected for PAR-BS because Crossref maps it to the full ISCA
  proceedings record. The ACM SIGARCH newsletter version, `10.1145/1394608.1382128`, was not
  used as the primary record.
- The three arXiv entries in the reject table are not presented as peer-reviewed evidence.
  Their DOI redirects resolve, but their records are DataCite preprints.
- Workshop status is explicit in the venue strings. HotOS, DaMoN, WORDS, and MEMSYS items
  should be treated as peer-reviewed context rather than as substitutes for full-conference
  or journal PPA evidence.
