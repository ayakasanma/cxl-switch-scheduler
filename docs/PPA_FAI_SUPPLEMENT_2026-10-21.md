# FAI Main / Algorithm-2 N4 supplementary comparison

2026-10-21 Asia/Taipei. **ACCEPTED_FOR_SUPPLEMENTARY_PRE_LAYOUT_AREA_STA.** Both interpretations actually ran DC and PrimeTime on FastX-NN from clean source `c8e7ea8c0e4530572b3abf5b14ea9958e24f1789`, after N4 Algorithm-2 directed/behavior/long functional acceptance. This is a separate supplementary pair; the accepted primary-nine v2 dataset remains unchanged.

Both runs use the same shared switch_top, N4/D16/M1/full105, production W5M, timestamps, FIFO/output controller, synthesis boundary and frozen `saed32-rvt-tt-25ns-forqa-cap075-v2` profile. Canonical SHA2566f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d; SAED32 RVT TT0.78V25C,25ns, ForQA/top, compile-medium/onecore, same I/O/load/uncertainty constraints. DC's temporary0.75maxcap optimization targets are restored before final reports/export; PT uses the original DB. No timing exception or library-file edit.

| N4 measurement | Main | Algorithm-2 | Algorithm-2 minus Main |
| --- | ---: | ---: | ---: |
| Total cell area (library units) |110089.845892|110058.332037|−31.513855 (−0.028626%)|
| Sequential cells |9011|9011|0|
| Policy subtree area |7143.9879|7120.8608|−23.1271 (−0.323728%)|
| Setup slack (ns) |+10.496409|+10.547482|+0.051073|
| Hold slack (ns) |+0.039940|+0.039940|0|
| Setup/hold/electrical violations |0|0|0|
| Untested checks |68|68|both constant_disabled|

Main's repeated area/FF/setup/hold exactly match its earlier primary-v2 N4 result. For this same-source pair, both complete the commands with DC/PT/wrapper exit0. Each has36404 timing checks:36336met,0violated,68constant-disabled untested. These are retained limitations, not waived user paths. No case-analysis/multicycle/false-path or explicit arc-disabling exceptions were introduced.

Independent audits validate full descriptor storage6720bits and arrival storage2048bits plus shared counter, mapped hierarchy/reference area, all ports/clock/reset in emitted SDC, exact source/profile hashes, original DB hash844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094, mandatory completion markers and result hashes. Both cases restore390temporary limits;20undefined library outputs remain explicitly excluded from the optimization target and do not hide used drivers. Read-only driver surveys inspect29458Main and29448Algorithm-2 used output pins: all original limits positive/defined, zero ordinary or CCS capacitance violations;9constant pseudo-drivers per case separate. Surveys do not compile or rewrite the netlist, and before/after netlist/SDC hashes match.

Mapped FIFO/hold subtree areas differ slightly with mapping context despite shared RTL. Therefore the total delta and the policy-subtree delta are reported separately; neither is an isolated gate count. Area units are the library's reported units, without a µm²/NAND2 conversion. Slack is measured at25ns; no Fmax or power claim follows.

The two interpretations have measurable behavioral differences under identical W64/256 stress traces, including different accepted-push timing from backpressure. Earlier20record runs/10pairs were independently checked. Algorithm-2 charges more fires to Low visits in that workload; average wait is higher in8/10pairs. This does not establish a general fairness or latency advantage. See[M6 behavior results](phase-5-verification/M6-results.md) and[long verification](phase-5-verification/M6-long-results.md).

**Scope decision:** the N4 total-area difference is about0.029%, with identical sequential-cell counts and both timing checks met. It does not materially change the current primary hardware-cost conclusions. Under the owner's conditional expansion instruction, N8/16 supplementary synthesis is deferred. No architecture choice or Main-baseline replacement is inferred from this small single-run difference. Run-to-run variation and additional corners were not measured.

Native RTL Agent Team Opus5.5/medium authored the supplementary RTL/model/directed tests; owner-authorized Sol/high continued long verification/preparer work after Claude quota exhaustion. Codex independently reviewed and executed remote EDA, then audited retrieved raw results. No fresh native synthesis-reviewer verdict is claimed: both later model services returned429; acceptance here is the documented Codex independent raw audit.

Actual run times: MainUTC02:57:58–02:59:51, Algorithm-2UTC02:59:51–03:01:35 (Taipei10:57:58–11:01:35). Remote roots `~/cxl/experiments/supplement-20261021-{main,alg2}-n4`, batchPID592827 completed. Retrieved168own result files plus20survey reports by allowlist, no proprietary assets. Final remote read-only result/library-hash check exit0.

Machine-readable[results](ppa/algorithm2-n4-20261021.json); raw local evidence `artifacts/fastx/supplement-20261021-{main,alg2}-n4/` and `...-loads-{main,alg2}-n4/`; independent audits `.setup-logs/fastx-alg2-20261021/{pair-independent-audit,pair-full-load-audit}.json`, original commands/helper logs retained. Full engineering history is in[DEVELOPMENT_REPORT](DEVELOPMENT_REPORT.md).

Power/activity annotation, physical implementation, multicorner/commercial-equivalence signoff and supplementary N8/16 remain unrun/deferred. Paper state behavior is owner-supplied; the single-output10/10 arbitration remains the approved project reconstruction. No local IEEE PDF inspection or cycle-identical dispatch reproduction is claimed.
