Continue in the existing `cxl-scheduler` repository. Do not recreate the project.

I have reviewed the current `specs/CXL_SPEC.md` and `specs/DECISIONS.md` against the original CXL Scheduler Revised Proposal and ECE509 First Progress Report.

The current documents contain too many TBD items because they do not fully incorporate the previously documented cycle-level design specification.

Your task is to reconcile the documents and prepare a **Spec v1.0 Release Candidate**, not to start RTL implementation yet.

### 1. Preserve previously approved decisions

- N = 4, 8, 16 request sources
- D = 16 FIFO entries per source
- M = 1 memory output
- Full 105-bit descriptor: Tag32, Address32, Opcode1, Length8, Payload32
- Equal-cost atomic descriptor service, at most one completed transfer per cycle
- Length does not increase the number of service cycles
- FCFS, RR, and FAI-inspired policies
- Response generation and tag matching remain in the testbench
- No destination-memory ID added to the 105-bit baseline descriptor
- Nine primary synthesis configurations
- University FastX DC/PT + SAED32, with local WSL Verilator/cocotb verification

### 2. Incorporate the previously specified interface contract

- One per-source FIFO, shared across all policy implementations
- Single clock and synchronous active-low reset
- Ready/valid request and output interfaces
- `push[h] = in_valid[h] && in_ready[h]`
- `fire = out_valid && out_ready`
- Only `fire` dequeues a request and consumes scheduling quota
- The complete output descriptor, selected source, and associated state must remain stable during stalls
- No empty-FIFO bypass
- Newly accepted descriptors become eligible no earlier than the following cycle
- Input readiness depends on FIFO occupancy at the beginning of the cycle
- Correct simultaneous push/pop behavior
- No CXL packet engine, coherence, link credits, or real DRAM controller

### 3. Restore the documented scheduling semantics

**FCFS**
- Timestamp assigned when input handshake succeeds
- 32-bit arrival timestamp stored per FIFO entry
- Oldest eligible FIFO head wins
- Same-cycle ties resolved by ascending source ID
- Modular timestamp ordering, assuming outstanding requests remain less than 2^31 cycles
- Timestamp wraparound is a required directed test

**Round Robin**
- Select the first nonempty source from the current polling position
- Maximum 10 successful transfers per source turn
- Advance after consuming the quantum or when the selected source becomes empty
- Downstream stalls do not consume quantum
- Quantum=1 is a supplementary experiment
- RR must not contain unnecessary timestamp storage

**FAI-inspired**
- W = 5,000,000 cycles
- Each source has a served counter B[h]
- S counts all successful transfers, with S = sum(B[h])
- Both counters update only on `fire`
- The average includes all configured sources
- UP if 10*N*B[h] < 3*S
- DOWN if N*B[h] > S
- KEEP otherwise, including equality
- Main states: H, B_H, L, B_L
- Buffer states preserve the previous effective priority for one window
- Two consecutive windows supporting the same change are required to switch effective class
- Neutral/opposing evidence cancels pending transitions
- S=0 cancels pending transitions while preserving effective class
- High/Low class quotas are 10/10
- Within-class ordering is FCFS using the shared timestamp selector
- Empty classes are skipped without unnecessary idle cycles
- The selected source/class/quota context is retained across downstream stalls
- Window counter advances even during stalls
- The closing-edge transfer is included in classification
- New classification takes effect in the following cycle
- Parallel classification is the primary baseline; do not introduce arbitrary multicycle exceptions
- The alternative literal-pseudocode buffer interpretation is a separately reported interpretation check, initially at N=4, not a replacement for the main policy

### 4. Restore verification and PPA requirements

Verification:
- Independent Python reference models for each policy
- Directed tests for FIFO boundaries, stalls, ordering, quotas, timestamp wraparound, FAI transitions and window boundaries
- 20 reproducible random seeds per configuration, initially 100,000 cycles each
- FAI stress tests with W=64 and W=256
- At least one W=5,000,000 test spanning three complete windows
- Scoreboard checks descriptor integrity, loss, duplication, ordering, and TB-generated tagged responses
- Report accepted-transfer rate, mean/P99 acceptance-to-fire waiting time, per-source service counts, and generation-to-acceptance delay

PPA:
- Synthesize the complete switch including common descriptor FIFOs and policy-specific metadata/state
- Exclude TB memory models and response tracking
- Hold technology library, PVT, clock, SDC, synthesis effort, and optimization settings constant
- Report total mapped cell area, FF and combinational components, WNS, and critical paths
- Determine the common clock target through pilot runs; the earlier 5 ns adder smoke-test constraint is not a final scheduler clock target
- Attempt activity-annotated pre-layout power estimation when supported, otherwise document the limitation
- Keep the baseline nine configurations unchanged

### 5. Resolve the decision register correctly

Update `specs/CXL_SPEC.md` and `specs/DECISIONS.md`.

Classify each item as one of:
- USER_CONFIRMED
- SPECIFIED_IN_PRIOR_DOCUMENTS
- PROPOSED_DEFAULT_PENDING_APPROVAL
- REQUIRES_USER_DECISION
- OPTIONAL_OR_DEFERRED

Do not confuse a statement in an earlier report with an explicit user approval.

Pay special attention to the difference between the older Tag-only Proposal and the latest First Progress Report, which describes full descriptors, routing, and testbench response tracking. The approved full 105-bit descriptor takes precedence.

Do not treat statements claiming FCFS/RR were already implemented or verified as actual project progress. They are NOT_STARTED.

### 6. Produce a reviewable release candidate

Prepare:

- `specs/CXL_SPEC.md` as Spec v1.0 RC
- Updated `specs/DECISIONS.md`
- `docs/SPEC_REVIEW.md` containing source reconciliation and unresolved questions

Only ask for genuinely unresolved architectural or correctness-critical decisions. Present recommended defaults and rationale.

Do not generate Scheduler RTL, invoke rat-auto-design, or mark the full specification approved until I explicitly approve Spec v1.0.