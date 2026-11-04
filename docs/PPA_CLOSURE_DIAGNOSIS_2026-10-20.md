# Timing / electrical closure diagnosis —2026-10-20

**DIAGNOSIS_COMPLETE; CLOSURE_OPEN.** This follows the [nine measured configurations](PPA_RESULTS_2026-10-20.md), not a replacement result set. Main N16 still fails setup; all nine retain electrical findings. Frozen Spec, RTL, models, testbench and the original25ns/medium profile remain unchanged. No timing exception, disabled library rule or additional stage is adopted.

## Same-net DC/PT capacitance diagnosis

Codex reconnected with the already owner-approved pinned SSH key and successfully ran DC/PT W-2024.09 on FastX. This login landed on a different backend than the primary sweep; the module/library identity and existing shared-home run files were used. A new probe directory reloaded the **same original FCFS N4 mapped netlist and SDC**, applied the original TT/ForQA/top settings, and ran reports only. Both tool processes exited0, exact completion markers were present, and before/after netlist/SDC SHA256 checks passed. No compile or netlist write occurred in these probes.

The discrepancy is reproduced at the **same driver pins**, with identical library limits. In the reloaded DC check, `actual_max_net_capacitance` / `total_capacitance_max` values are lower than its named CCS receiver-capacitance values; PT's checked load agrees with DC's larger CCS values. This identifies the observed check/report difference, not the original compiler's internal optimization cost model or a complete CCS waveform timing mode:

| Driver pin | Driver | DC checked load fF | DC CCS maximum fF | PT checked load fF | Library limit fF |
| --- | --- | ---: | ---: | ---: | ---: |
| `gen_fifo_2__u_fifo/U2427/Y` | INVX2_RVT | 15.717124 | 17.801981 | 17.801979 | 16 |
| `gen_fifo_2__u_fifo/U2469/Y` | NBUFFX2_RVT | 15.884809 | 17.594511 | 17.594509 | 16 |
| `gen_arrival_ts_arrival_cnt_q_reg_12_/Q` | DFFSSRX1_RVT | 7.758416 | 8.549581 | 8.549581 | 8 |

For U2427, both tools' detailed net reports give17 loads, wire capacitance7.48563fF and maximum receiver-pin capacitance10.3163fF, totaling about17.802fF. This rules out a different fanout/wire-load or16fF limit as the explanation at that pin. The smaller DC checked value is below16; the CCS/PT value exceeds it. The pin-load accounting difference explains these sampled disagreements. This is direct evidence for three pins in one configuration, not a proof that every pin in all nine cases has the same cause or that a particular synthesis switch repairs it.

The baseline re-read reproduces **DC0 vs PT1118 capacitance violations**. Separate diagnostic sensitivity reports temporarily toggled each available variable and restored its original value:

- `timing_library_max_cap_from_lookup_table`: DC and PT.
- `timing_enable_library_max_cap_lookup_table`, `timing_enable_max_cap_precedence`, `timing_max_capacitance_limit_from_library_only`: PT only; not visible in DC.
- `report_capacitance_use_ccs_receiver_model`: both tools.
- `lib_pin_using_cap_from_ccs`, `timing_use_enhanced_capacitance_modeling`: DC only; not visible in PT.

None of these individual trials changes the DC0/PT1118 violation counts. Disabling DC enhanced-capacitance modeling changes its displayed net total to15.7171fF; that is a diagnostic display/model sensitivity, **not a repair or permission to suppress PT checks**. The exact internal control needed to make synthesis optimize against the PT load model is not established. No trial setting was propagated to the primary flow/profile.

Evidence is in local ignored `artifacts/fastx/closure-cap-20261020e/` and `closure-cap-20261020f/`, each with a validated download manifest, tool logs, reports, source hash checks and exact exits. Their remote originals are under `~/cxl/probes/` with matching names. The first attempt, `closure-cap-20261020d`, failed because the probe passed numeric0/1 to a variable requiring literal true/false; its failure/logs are preserved. The repaired fresh probes both succeeded. Attribute-enumeration warnings for unset/unavailable values are retained; no clean-warning claim is made. No library, license or executable was downloaded.

## Main N16 critical path

The owner-authorized **GPT6.1 Sol/high** fallback independently inspected the actual PT/DC paths, mapped connectivity and corresponding RTL. The worst path is FIFO9 read pointer to Main source13 class state: PT arrival25.729298ns, required24.858589ns, slack−0.870709ns. There are32 violated setup checks. No RTL bug follows merely from this timing failure.

| Section of the first PT path | Increment ns |
| --- | ---: |
| FIFO clock-to-Q and timestamp-head read | 0.932283 |
| Shared FCFS oldest-head selector | 20.249199 |
| Common held/unheld grant, head-valid and fire control | 0.776995 |
| Closing S increment | 0.441790 |
| `3*S_close` arithmetic | 2.367185 |
| UP comparison and class/reset/window-closing control | 0.961846 |
| Total arrival | 25.729298 |

The shared selector is **already a balanced four-level tree**. Each level maps a32-bit timestamp subtraction to a ripple chain; the observed first path traverses120 full-adder carry cells across four subtractors. The subtract sections account for18.095890ns, about70.33% of arrival; the complete selector accounts for about78.70%. This is stronger evidence than a generic claim that FAI classification alone is too slow.

The tail uses the closing-cycle `fire` to update S before classifying, exactly as approved Q3 requires. This path does **not** traverse the105-bit descriptor payload mux; it does traverse common grant/valid/fire control. The constant multiply is already strength-reduced in the mapped circuit, so rewriting `3*S` as shifts/adds alone is not evidence of improvement. Existing reports do not establish high fanout as the dominant cause; that requires actual pin transition/load/fanout evidence.

Detailed stage boundaries, mapped port/net connections, raw first path and read hashes are preserved in ignored `.setup-logs/FastX-NN/closure-sol/`. The independent review made no tracked changes and did not run synthesis. Parent Codex owns the new remote electrical diagnostics.

## Actual isolated high-effort pilot

Codex then used the existing preparation/transfer/`run.sh` flow for one **FCFS N4 PILOT** with `compile -map_effort high`. Every external/library/clock/ForQA/reset condition and DC single-core limit remained the same. Clean export/source commit is `d5d5a2b92a2e345db3e9c1044c81920b56c8b03e`; its RTL/flow hashes match the original baseline. The candidate profile is `saed32-rvt-tt-25ns-forqa-high-pilot-20261020`, canonical SHA256 `cc0eb4afd8c80b9478da9274327e5faff873f46d3f62824737a7dabeb406897c`, status PILOT, not FROZEN.

Both actual DC/PT batches and their wrapper exited0 with exact markers, strict error scans, all mandatory reports and source/result/transfer hashes checked. The applied profile and echoed actual compile command confirm high effort was used. Results:

| FCFS N4 | Cell area, library units | FF | PT setup ns | PT hold ns | PT cap / slew violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen medium baseline | 103009.393996 | 8856 | +9.860374 | +0.049066 | 1118 /31 |
| High-effort pilot | 103009.393996 | 8856 | +9.860374 | +0.049066 | 1118 /31 |

The emitted mapped Verilog module bodies are byte-identical after excluding generated header comments. Coverage is likewise35712 met /35776 total /0 violated /64 constant-disabled untested. This pilot demonstrates **no measured improvement at FCFS N4**, particularly no electrical repair. It does not prove high effort would have no effect at Main N16; that experiment was not run. High is not adopted and no replacement nine-case sweep is launched on the strength of this unsuccessful electrical pilot.

Raw evidence: ignored `artifacts/fastx/closure-high-pilot-fcfs-n4-20261020/` (83 validated own files) and the matching new FastX `~/cxl/experiments/` directory. Audit: `.setup-logs/FastX-NN/closure-high-pilot-independent-audit.json`. The reused primary audit has exactly two profile-expectation substitutions for this separate run (PILOT/high instead of FROZEN/medium); its expectation diff is retained alongside it, with all hash/error/structure/area/SDC/coverage checks preserved. No scheduler functional tests were rerun because no RTL/model/TB changed; these EDA checks are not new functional coverage.

Sol/high independently checked the new diagnostic transfers/source hashes, three pin-load samples, sensitivity reports and high-pilot actual High-effort mapping banner, all77 result hashes and83 transfer hashes, mapped module bodies and SDC commands. No review blocker was found; this accepts the evidence and bounded diagnosis, not electrical closure. Its check records are in `.setup-logs/FastX-NN/closure-sol/`. The task-specific SSH master was closed after collection (`ssh -O exit` returned0; the interactive wrapper ended1, separately from successful EDA commands).

## Common closure sequence and acceptance gates

1. **Completed common-effort experiment:** the isolated FCFS N4 high-effort pilot above did not improve its mapped circuit or electrical results. Retain it as a measured negative result; do not present it as a new accepted common methodology or extrapolate it into an unrun Main N16 result.
2. **Electrical repair candidate:** establish a supported synthesis-side way to optimize against the load model PT actually checks, or conservatively tighten synthesis-only limits with measured justification. Keep the original PT/library limits and common external assumptions. Check representative FIFO/control/arrival nets and every final cap/slew violation; do not lower reporting fidelity or call a setting toggle closure. Any constraint/optimization addition becomes an explicit new common methodology with a new profile/hash and equal treatment of all nine.
3. **If mapping effort is insufficient, target the shared comparator:** preserve the balanced tree,32-bit modular ordering, strict ties and ascending source ID. An equivalent low-bit borrow/MSB comparison or grouped carry implementation is a candidate shared by FCFS and Main at all N. It requires an actual delegated implementation, bitvector equivalence checks, wrap/tie/eligibility tests, lint and the accepted regressions before synthesis. No comparator rewrite has been made here.
4. **Only if still needed, consider Main closing-threshold precomputation:** compute no-fire/fire-to-self/fire-to-other threshold cases from beginning state, then select using the actual fire/grant. Preserve closing-fire inclusion,32-bit unsigned intermediates, S=sum(B), parallel class updates, hold context and next-cycle visibility. This can increase area and synthesis may re-share it; it is a candidate, not a measured improvement. No extra register or altered timing contract is included.
5. **Adopt only after evidence:** evaluate actual area, setup/hold and cap/slew under the proposed common flow, retain all previous failures, then rerun the same nine configurations if the method is selected. No mixed medium/high policy comparison, policy-specific clocks/stages, false/multicycle paths, shortened timestamps, omitted metadata or serialized classification. RTL changes additionally require the project-mandated functional/structural verification before the sweep.

No new correctness-critical Spec contradiction or architecture decision was found. The next choices above are engineering experiments within the existing scope; a policy-specific pipeline or changed cycle contract would need explicit owner architectural approval. Power, supplementary Algorithm-2, equivalence and physical/multicorner signoff remain separate uncompleted work.

## Full FCFS N4 load population and native tightening canary

The subsequent report-only DC run, `closure-full-loads-20261020b`, enumerated **26731 mapped cell output pins** with resolved positive original library limits. The netlist reader reports26556 leaf instances:26554 mapped library cells matching the original QOR, plus two constant pseudo drivers. Those two `**logic_0**` / `**logic_1**` pins are explicitly listed and excluded from driver-library calibration; no missing library pin is silently treated as zero. Every remaining row records ordinary maximum load, CCS rise/fall maxima and its actual driver limit.

Independent parsing reproduces the **exact1118 original PT capacitance-violating pin names**, with their required/actual loads agreeing within0.00001fF; DC ordinary loads give0 violations. Thus the earlier three-pin explanation is now reconciled for the full FCFS N4 violating set. Other N/policy sets have not yet had this per-pin reconciliation. The lowest ordinary/maximum-CCS ratio across this population is **0.7725474722**, at `gen_fifo_0__u_fifo/U4233/Y`; its loads are1.123780fF ordinary versus1.454642fF maximum CCS. The observed driver-limit bins are8fF (24308 pins),16fF (2422) and64fF (1). A0.85 uniform margin inferred only from the earlier samples would not bound the full population.

A separate native DC canary verified actual support for changing the **existing application attribute** `max_capacitance` on an output library pin in memory. `INVX2_RVT/Y` changed from16 to13.6fF; the unchanged U2427 net then reported required13.600000, actual15.717124 and slack−2.117124fF. Restoring16fF restored the original zero DC cap violations. This verifies both setter/readback and DRC-engine use, not yet the result of a new synthesis. The university `.db` SHA256 stayed unchanged. The native `set_max_capacitance` command documents clock/port/design scope; a single global absolute cap would not represent the same percentage margin for all three driver-limit bins.

The next isolated synthesis candidate uses **0.75 times each defined positive original output-library-pin cap limit**, a conservative exploratory value below the measured minimum ratio. It is an extra DC optimization guardband, not a claim that the two receiver models have become identical or a universal bound for remapped circuits. Original limits must be restored before final reports/SDC export; a fresh PT process must load the original library and meet its unchanged limits. The candidate does not change receiver capacitances, timing tables, PVT, clock/I/O assumptions or RTL. It is not adopted into the original frozen profile.

Evidence: ignored `artifacts/fastx/closure-full-loads-20261020b/`, `closure-cap-canary-20261020a/` and `.setup-logs/FastX-NN/full-load-and-canary-audit.json`. Both actual DC batches exited0, markers/error scans and transfer hashes passed, and the original source netlist/SDC remained unchanged. The initial full-load attempt `closure-full-loads-20261020a` failed on a constant pseudo driver's absent library pin; its logs are retained and it is not counted as complete. The fresh successful run records those constants explicitly. No proprietary asset was copied.

The authorized Sol/high agent implemented the optional factor in the existing preparer/DC flow, with no PT/RTL/Spec change. Codex independently reviewed the schema, config, mandatory restoration report and error paths. Infrastructure tests execute43 unique cases across Windows35PASS/8platform skips and WSL30PASS/13different platform skips, with no jointly skipped test. These cover invalid scale/schema, actual stub compile-time tightening, restoration after success/failed compile/partial apply and rejection of false/throwing/no-op restoration. An absent-field byte comparison preserves all nine old run-config files, required-output lists and wrapper scripts. Logs, diffs, hashes and test-union evidence are under `.setup-logs/FastX-NN/closure-sol-next/implementation/`.

The separately named [cap075 PILOT profile](../syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-pilot-v1.json) keeps medium effort and the original numeric library/clock/I/O/ForQA conditions. Its canonical SHA256 is `51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f`. Full-loop compilation/restoration must still be validated in an actual fresh FastX run; code tests and the earlier setter canary alone do not establish closure.

The first full-loop pilot exported clean flow commit `4a3e9fc9d12a9f99d3db71ef05f5057bfe9fc065` and correctly stopped **before compile** on an exact readback mismatch: requested50.76502425fF versus reported50.765026fF on an additional output cell's67.686699fF original limit. Eight limits had applied; all nine attempted edits restored successfully. No final netlist or accepted result was produced. Failure artifacts are preserved at `artifacts/fastx/closure-cap075-pilot-fcfs-n4-20261020-failed/`; this is not a successful synthesis or waived check.

A fresh native precision canary identified float32 storage plus six-decimal attribute reporting. On `TNBUFFX8_RVT/Y`, tool-native `binary format f` / `binary scan f` predicts50.7650260925 for the first requested value, matching reported50.765026. Requests50.765024/50.765020/50.765000 yield50.765022/50.765018/50.764999 respectively;12 and6 remain exact. Original67.686699 restores correctly. The representation-aware repair must compare against that exact measured conversion, retain rejection of incorrect/no-op writes, and keep positive tightened values and original-limit restoration mandatory. It does not relax PT limits or introduce a broad error tolerance. Evidence: `artifacts/fastx/closure-cap-precision-20261020a/` and the preserved command/logs.

The Sol/high repair was independently reviewed and committed at `046721b0130c93819887645e0face3d9a300372d`. Windows36PASS/8platform skips and WSL30PASS/14different skips cover **44 unique actually executed infrastructure tests**, including all six native readback fixtures, a whole-flow float32 apply/restore and rejection of rounding that erases tightening. No tests are jointly skipped. Generator/PT/RTL/profile numeric settings are unchanged by this repair. The fresh full-loop candidate is exported from that clean commit; its original failed directory is retained.

## Actual cap075 FCFS N4 pilot result

The fresh `closure-cap075-pilot-fcfs-n4-20261020b` run completed actual DC/PT and wrapper exit0 from clean source046721b, with the same candidate profile/hash above. Every mandatory report, exact completion marker, source/result/transfer hash and strict error scan passed. Its390 defined output-library limits were temporarily tightened and all390 restored;20 library outputs have undefined max caps and were explicitly skipped. No library file was written. A subsequent native full enumeration of the new netlist finds **27231 used output pins, all with positive original library limits**, so none of those20 undefined library outputs is used in this mapping.

| FCFS N4 | Cell area, library units | FF cells | PT setup ns | PT hold ns | PT cap / slew violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original medium baseline | 103009.393996 | 8856 | +9.860374 | +0.049066 | 1118 /31 |
| Cap075 medium pilot | 103730.908806 | 8856 | +9.881229 | +0.033790 | **0 /0** |

Area increases721.514810 library units, about0.70%; mapped leaf cells increase26554→27054, while FF count remains8856. All required FIFO/arrival/hold structure remains present, with no latch/macro. PT has0 violated timing checks,35712 met and64 constant-disabled untested out of35776, exactly the original untested pattern. The emitted SDC has no cap-target or attribute overlay commands; the normal clock/reset/I/O/load checks remain intact. The fresh PT process uses the original unmodified `.db`, and the original library SHA256 was rechecked after synthesis. The new full-driver CCS and ordinary calculations both give0 cap violations against the original limits. This is a successful **FCFS N4 pre-layout pilot** under these assumptions, not all-nine or physical/multicorner signoff.

Evidence: `artifacts/fastx/closure-cap075-pilot-fcfs-n4-20261020b/` (84 own files: the original83 plus the required cap-restoration report), `closure-full-loads-cap075-20261020a/` and `.setup-logs/FastX-NN/cap075-pilot-independent-audit.json`. Remote backend for this continuation is `FastX-NN`; libraries remain on FastX. The original1118/31 failure, unsuccessful high-effort pilot and pre-compile rounding failure are preserved. An audit-only assumption that no library output had an undefined cap was corrected to the observed20; subsequent used-pin enumeration establishes their irrelevance to this particular mapping. No EDA check was waived.

The candidate remains PILOT. Next evaluate the same method at Main N16 before considering a full common-profile comparison. The old Main N16 setup failure is not cleared by FCFS4's result, and no per-policy clock/effort/margin changes are authorized by this pilot.

## Actual cap075 Main N16 pilot result and disposition

The same candidate profile and medium effort were actually run at Main N16, production W5,000,000, from clean source `aa89771d5b5bc48bb7e054d8a8df9558de32b4ee`. The source/flow/profile precheck confirms identical RTL and candidate flow to the successful FCFS4 pilot. DC/PT and the wrapper exited0, with exact markers, required reports, strict error scans and result/transfer hashes checked. DC elapsed905seconds;390 temporary library limits were applied and all390 restored before reports/export. The `.db` hash remains the original844d4474…; no cap overlay commands appear in the emitted SDC.

| Main N16 | Cell area, library units | FF cells | PT setup ns | PT hold ns | PT cap / slew violations | Setup checks violated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original medium baseline | 436249.874914 | 35773 | −0.870709 | +0.079660 | 4200 /4 | 32 |
| Cap075 medium pilot | 437228.837383 | 35773 | **−0.907946** | +0.085328 | **0 /0** | **32** |

The electrical repair works for this second measured pilot, at978.962469 additional area units (about0.2244%). It **does not repair setup**: worst slack is37.237ps more negative than the baseline. Worst path is now FIFO15 `rd_ptr_q_reg_0_` to Main `cls_q_reg_12__1_`, arrival25.749029ns and required24.841084ns. The constraint report records−0.907938ns; both report values are retained. All143344 timing checks are tested:143312 met and32 setup violated, no untested/hold violation. Positive hold and zero cap/slew do not make this a timing-accepted design.

Sol/high independently verified78result hashes and84transfer hashes, source/profile/restoration, original-library/SDC acceptance and the used-pin survey. The new first path still traverses four timestamp subtractors/120carry cells; the shared selector contributes20.314253ns. Its later path is now `fire → pop[12] → B_close → 160*B_close → class`, rather than the original worst path's global-S branch. This supports prioritizing the shared comparison logic; optimizing only the old `3*S_close` tail would miss the new worst branch. Detailed connectivity/stage evidence and the final independent verdict are under `.setup-logs/FastX-NN/closure-sol-next/review/main16-cap075-final-findings.md`.

The remapped full-driver report enumerates **116345 used output pins**, every one with a defined positive original limit, with0ordinary/CCS cap violations. Netlist-reader115602 leaf instances include20 constant pseudo drivers;115582 mapped library leaves reconcile to QOR. Thus the20 skipped undefined library outputs are unused here too. This survey was fetched only after completion: an earlier transfer attempted while the TSV was growing correctly failed tar's changed-file check and was not accepted; a separate final download passed all hashes.

Raw evidence: `artifacts/fastx/closure-cap075-pilot-main-n16-20261020a/` (84 files), `closure-full-loads-main16-cap075-20261020a-final/`, `.setup-logs/FastX-NN/cap075-main16-independent-audit.json` and `remapped-full-load-audit.json`. Main16 ran on FastX backend `FastX-NN`. The connection used for FCFS4 had closed before staging Main16; the first stage attempt failed strict host-key checking with no remote mutation. The already-approved pinned key and authentication were restored, then the new directory was staged successfully. No host-key checks were bypassed. An audit-local electrical-status classifier was corrected to exclude setup rows from cap/slew status; the raw measured failure never changed.

**Disposition: two pilot electrical successes, Main16 setup NOT_MET, candidate still PILOT, no replacement nine-case sweep.** Further repetitions of only the cap margin do not address the established shared-comparator timing chain. Next is a delegated, behavior-preserving shared timestamp-comparison candidate with bitvector equivalence/wrap/tie tests and the required functional regression before synthesis. No RTL change is made by this diagnostic stage, and no additional stage, serialized classifier or timing exception is implied. Original frozen profile/nine results, all failed attempts and power NOT_RUN remain preserved.
