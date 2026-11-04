# CXL Scheduler Specification Approval

Architecture status: APPROVED
Specification: v1.0
Approved specification: v1.0
Approved by: Project owner
Approver: Project owner
Approved on: 2026-10-13
Approval date: 2026-10-13 (Asia/Taipei)
Approved baseline: FCFS, RR, FAI-inspired Main
Approved supplementary interpretation: FAI Algorithm-2 variant
Explicitly deferred features: multi-memory outputs, APR, and other optional extensions

Basis: the owner's direct Option A approval, Q1–Q3 decisions, shared-framework mandate and controlled implementation instructions, applied to RC1 at a518e1e. Retain consistent nonarchitectural defaults. Production W=5,000,000 uses23-bit B/S and at least31-bit widened unsigned threshold arithmetic (common32-bit project representation).

Main retains prior effective class through buffer states; Algorithm-2 Buffer immediately uses stored target class and retains it on KEEP/idle. The common single-output High/Low alternation is a project reconstruction, not a cycle-identical paper reproduction. The paper behavior/citation is owner-supplied; no local IEEE PDF inspection is claimed.

The frozen specification commit is recorded in docs/STATUS.md and delegated-task manifests after this file is committed. This authorization is not evidence of completed RTL, regression, synthesis, STA or power.
