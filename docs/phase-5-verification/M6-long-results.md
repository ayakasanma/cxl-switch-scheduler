# Algorithm-2 N4 long functional verification and supplementary PPA preparation

2026-10-21 Asia/Taipei. **LONG_FUNCTIONAL_ACCEPTED; supplementary PPA was not run at this checkpoint and subsequently completed in the separate [supplement report](../PPA_FAI_SUPPLEMENT_2026-10-21.md).** Base1cec68d; no RTL/model/Spec/DC/PT Tcl/profile changes. Codex independently reviewed raw evidence and completed reporting after the fallback worker's API429 interruption. This report does not claim the worker finished its final turn.

Owner-authorized GPT6.1 Sol/high (`/root/sol_alg2_long`, explicitly selected model/effort, fork_turns none) continued after native Claude Opus5.5/medium exhausted its session allowance. The earlier native task completed the RTL; this fallback changed verification/tooling only. Provenance and exact commands/scripts/exits/source hashes are in `.setup-logs/implementation/alg2-long-sol-20261021/`; native failed follow-ups remain in `alg2-production-20261021/` and `alg2-long-workflow-20261021/`.

The existing stress/production loops now select their literal expectations, hierarchy and metric labels from the explicitly selected interpretation. Main defaults are retained. Algorithm-2's four production class rows are written by hand from8.6, independently of the oracle. No duplicated production loop, state deposit, skipped time or smaller production window. The runner requires a nonempty exact matrix, actual lengths, valid full-window counts and matching policy/schema; negative infrastructure tests cover missing/short/smoke/subset/extra/empty/wrong-policy evidence.

| Scope | Run ID | Actual outcome |
| --- | --- | --- |
| M6 directed + production-parameter smoke |20261021T010228Z_16709|447 PASS=241reference+45helpers+161cocotb; strict lint/probes/rejections retained|
| Main M5 unit regression |20261021T010341Z_17581|856 PASS=241reference+45helpers+570cocotb|
| Algorithm-2 long stress |20261021T011237Z_23789|10/10 PASS; N4×W64/256×seeds509..513,400k/800k cycles each;6million total trace cycles|
| Algorithm-2 production |20261021T011237Z_23785|1/1 PASS;20million measured nonreset cycles,4fullW5M windows;57additional drain cycles|
| Parent final small checks |codex-review/final-small.xml|329/329 PASS: reference/helpers/scope gates/comparison utility|
| PPA infrastructure Windows |ppa-windows.log|40 PASS,8platform skips|
| PPA infrastructure WSL final |ppa-wsl-final.log|34 PASS,14platform skips,2885subtests PASS|

Platform skips are explicitly unexecuted on that host: Windows skips POSIX-shell tests; WSL lacks the Python tkinter Tcl interpreter for Tcl-stub tests, which run on Windows. These are infrastructure checks with fake tools/Tcl stubs, not Synopsys validation. No tool was installed to eliminate complementary platform skips.

Production closes at actual nonreset edges5M/10M/15M/20M, B/S sums2747980/2749750/2749186/2750244. Post-window source0..3 classes:

1. BufferLow,BufferLow,StableHigh,BufferLow.
2. StableLow,StableHigh,StableHigh,StableLow.
3. BufferHigh,BufferLow,BufferLow,StableLow.
4. StableHigh,StableLow,BufferLow,BufferHigh.

Independent Codex checks recompute inequalities from closing B/S and verify these literal trajectories, closing fire at windows2/4, held offers across windows1/3, every pin/history/oracle assertion and zero outstanding after drain. Tagged responses issued/completed10997179/10997179. Every long stress run covers all16Algorithm-2 state/evidence pairs, including KEEP and zero-service Buffer retention. Source hashes captured before both long scopes match after completion and the current files. Production elapsed4136.8s at runner level; longstress484.8s. No prior Main long suite was relabelled as new evidence.

The PPA preparer adds explicit `--supplementary-alg2` for `--policy fai-alg2 --n-src 4`; without opt-in or withN8/16/wrong policy it rejects. Primary policy mapping remains exactlythree×three=9. The Algorithm-2 payload includes full6720descriptor bits and2048timestamp bits, the same scheduler module/common boundary, and explicit supplementary metadata. Synthesis requires the exact frozen cap075-v2 profile canonical6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d. Existing flow Tcl/constraints/library remain unchanged. No actual supplementary synthesis is implied by payload tests.

Comparison utility validates array lengths, hashes and binary fire/reset fields, rejects empty/unpaired/corrupt records, and labels partial matrices `full_matrix=false`. Parent reapplied it to all20accepted earlier actual records: full10pair matrix valid, results preserved.

Failures retained: an initial CRLF shell-script attempt, an old PPA rejection-message test expecting “primary nine” instead of the newly explicit opt-in error, and the first WSL PPA failure are preserved. The guard was retained and only the expected message updated; parent final WSL rerun exits0. Worker ended with API429 after long tests completed, before writing this report; parent verified results rather than treating the agent error as a test failure or completion. No warning waiver or test skip was silently counted as PASS.

Evidence: `.setup-logs/implementation/alg2-long-sol-20261021/codex-review/long-functional-audit.json`, raw runner/JUnit/results under the run IDs above, long-sources-before.sha256 and matching after-check, platform logs/exits and parent fallback provenance. Next: clean commit/export and actual same-source MainN4/Algorithm-2N4 FastX measurement using the unchanged v2 profile. Power, physical/multicorner/formal and N8/16 supplement remain unrun/deferred.
