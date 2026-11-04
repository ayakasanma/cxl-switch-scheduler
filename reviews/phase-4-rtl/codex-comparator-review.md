# Independent shared comparator review —2026-10-21

Scope: frozen Spec v1.0 at1af80967, candidate fromb54aa645480b891c349bf4b5814f8b6f66034a01. Review by Codex; implementation and focused verification by native RTL Agent Team `rtl-coder`, Opus5.5/medium, session322c1671-e1c8-4f12-a942-50d733089ea1, exit0. All74 inspected assistant response records report `claude-opus-5-5`; no fallback or permission denial.

## RTL and architecture

The sole RTL diff is `cxl_fcfs_sel.ts_older`: unsigned lower-bit magnitude comparison produces subtraction borrow, MSB XOR produces modular difference sign, and input inequality replaces difference nonzero. For W>=2, split a/b into high bit and low W-1 bits. With borrow=[b_low<a_low], modular subtraction has high bit `(b_high-a_high-borrow) mod2`, equal to their XOR; a modular difference is zero iff a=b. Thus the two expressions agree for every pair of known binary inputs, including equality and exact half-range. This is mathematical review of the actual expression, not a machine-checked formal proof or an assertion about arbitrary X/Z simulation semantics.

Tree structure, eligibility, lowest-ID ties, ports, timestamp width and combinational timing contract are unchanged. Call sites are FCFS in `switch_top` and the common selector in `cxl_fai_main_sched`. FIFO, output hold, models, existing testbenches, policy state/window arithmetic, filelists and synthesis constraints are unchanged. RR still omits arrival metadata. No architecture conflict found.

Candidate selector SHA256: `3418505168ca4a0c93422101f1e1a7a042833c935e0f9b021661535b7b6a2c20`. Native before/after hashes and the only functional tracked-file diff agree with this scope.

## Evidence independently inspected

- Native comparison run20261020T165027Z_1281:21 configurations,81,108,288 vectors, ALL_PASS; actual edited selector and Git baseline modules instantiated together. General proof is hand-derived; 32-bit tests are finite. Reduced-width configurations that sample masks are explicitly distinguished in the [native report](../../docs/phase-5-verification/ts-older-comparator-20261021.md).
- M3 run20261020T165234Z_2953:550 tests in32 raw JUnit files, zero failure/error/skip;12 strict lint configurations, no diagnostics or simulation-build relaxations.
- M5 run20261020T165357Z_386:805 tests in32 raw JUnit files, zero failure/error/skip;27 strict lint configurations,9 structural probes and3 expected Algorithm-2 rejections. Expected rejections are not simulated tests.
- Three deliberately broken comparator copies each fail W4 and W32 tests. Only isolated mutant builds relax fatal warnings; acceptance builds retain strict gates. Existing Verible style findings are not represented as passing lint.

Audit code/output and original evidence are under ignored `.setup-logs/implementation/comparator-20261021/` and `artifacts/implementation/`. These tests reuse the unchanged independent Python models.

## Review correction and acceptance boundary

The native verification script defaulted to HEAD. After committing the candidate this could compare the candidate against itself. Codex corrected this infrastructure-only issue: default baseline is fixed to pre-rewriteb54aa64, and identical source files are rejected. The native results remain valid because their recorded resolved base isb54aa64 with a different source hash. The corrected script is independently rerun; see [development record](../../docs/DEVELOPMENT_REPORT.md) for its outcome and later regression evidence.

Final follow-up: **FULL_FUNCTIONAL_REGRESSION_ACCEPTED; MAIN16_SINGLE_PILOT_MET**. All required primary/stress/production/common/RR scopes completed and raw JUnit/lint/full_scope/source hashes were independently checked. Partial Main primary interrupted by SIGHUP is preserved and replaced by a complete60-run pass. Production3 covers60million measured cycles/12windows; stress and production functional metrics match old results except identified host runtime/speed/RSS fields.

Actual same-profile FastX Main16/sourceb257ee8 reports setup+1.158148ns, hold+0.084335ns, zero timing/electrical violations and0untested, area437622.506788, FF35773.390limits restored;116993used driver pins audited, original library hash unchanged. See [measurement and exact test IDs](../../docs/PPA_COMPARATOR_PILOT_2026-10-21.md). No further RTL change is required by this review. This accepts the shared comparator functionally and the measured single pilot; original nine-case results remain historical, a common revised nine-case dataset is still pending, and no power/physical/multicorner/formal-tool result is implied.
