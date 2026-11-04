# Shared timestamp comparator rewrite (`cxl_fcfs_sel.ts_older`) — focused verification, 2026-10-21

Status: **FOCUSED_CHECKS_PASS; FULL_REGRESSION_PENDING (parent); SYNTHESIS_NOT_RUN.**
Author: native RTL Agent Team `rtl-coder` (Claude Code, model `claude-opus-5-5`, medium effort), no subagents.
Base: HEAD `b54aa645480b891c349bf4b5814f8b6f66034a01`, working tree clean at start. Frozen Spec
`specs/CXL_SPEC.md` sha256 `797a5cdf…a4cf` (last commit `1af80967…`), `specs/APPROVAL.md` sha256
`a4675fbf…ca7c`, both unchanged after the task. Raw logs: `.setup-logs/implementation/comparator-20261021/native/` (ignored).

## 1. Motivation and scope

The cap075 Main N16 pilot (docs/PPA_CLOSURE_DIAGNOSIS_2026-10-20.md, final Main16 section) still fails
setup by −0.907946 ns. The worst path goes through four 32-bit timestamp subtractor levels of the shared
`cxl_fcfs_sel` tree (about 120 carry cells, 20.31 ns in the selector). The old `ts_older` built the full
difference `d = b − a` and then checked `d != 0` (a zero-detect after the whole borrow chain) and `!d[MSB]`.

The change rewrites only the body of `ts_older`. The tree, ports, eligibility handling, ascending-ID
tie-break, source IDs, `TS_W` parameter (still ≥ 2, not hard-coded) and all other files are unchanged.
The change adds no registers, stages, bypass or timestamp shortening, and does not touch Main/class
windows or metadata. FCFS (`switch_top` POLICY=0) and Main (`cxl_fai_main_sched`) at N4/8/16 share the
same module, so this one edit covers every instance.

```systemverilog
// before                                   // after
logic [TS_W-1:0] diff;                      logic borrow, d_msb;
diff     = b - a;                           borrow   = (b[TS_W-2:0] < a[TS_W-2:0]);
ts_older = (diff != '0) && !diff[TS_W-1];   d_msb    = b[TS_W-1] ^ a[TS_W-1] ^ borrow;
                                            ts_older = (a != b) && !d_msb;
```

## 2. Mathematical derivation (all TS_W ≥ 2, all bit vectors)

Let W = TS_W and a, b ∈ [0, 2^W). Split each value as x = x_h·2^(W−1) + x_l, where x_h ∈ {0,1} and
x_l ∈ [0, 2^(W−1)). Let β = [b_l < a_l]. Define d_l = b_l − a_l + β·2^(W−1). Then d_l ∈ [0, 2^(W−1)).

b − a = (b_h − a_h − β)·2^(W−1) + d_l, so d = (b − a) mod 2^W = ((b_h − a_h − β) mod 2)·2^(W−1) + d_l.

* **MSB:** d[W−1] = (b_h − a_h − β) mod 2 = b_h ⊕ a_h ⊕ β. This is the RTL `d_msb`.
* **Zero test:** d = 0 ⇔ b ≡ a (mod 2^W) ⇔ a = b, because both are in [0, 2^W). This is the RTL `a != b`.

So (d ≠ 0) ∧ ¬d[W−1] ≡ (a ≠ b) ∧ ¬(b_h ⊕ a_h ⊕ β) for every input pair. No environment assumption is
used. The two boundary cases agree:

* Ties (a = b): false in both forms, so the lower ID wins.
* Exactly half range (d = 2^(W−1), so d[W−1] = 1): false in both forms, outside the spec-6 environment
  assumption.

`ts_older` is pure and is the only thing that changed, so every tree node and both module outputs are
the same function of (i_eligible, i_head_ts) for every N_SRC and TS_W. This argument is a hand
derivation, not a tool-checked formal proof.

## 3. Tool availability and proof method

WSL has `source scripts/wsl_env.sh`, Verilator 5.052, Verible, Python 3.12.3, cocotb 2.1.0 and pytest
9.1.1. It has **no** yosys, sby, eqy, z3, boolector, bitwuzla, yices or iverilog, and no `z3`/`pysmt`
Python module (`tool-inventory.txt`). I did not install z3. An SMT query would only prove a transcribed
copy of the expression, not the RTL, and it would need a network install. I chose machine checks that
run the actual RTL instead. **No SMT/formal equivalence proof is claimed.**

### Self-check

The self-check is `scripts/check_ts_older_equiv.sh` together with `scripts/ts_older_equiv/tb_ts_older_equiv.sv`.
The TB is simulation-only and is not in any filelist. For each configuration the script builds one
Verilator `--binary` with strict flags (`-Wall -Wpedantic -Werror-IMPLICIT`, no waivers). Each build
contains:

* `u_dut`: the working-tree `rtl/common/cxl_fcfs_sel.sv`.
* `u_base`: the module from `git show <BASE_REV>:rtl/common/cxl_fcfs_sel.sv`, renamed
  `cxl_fcfs_sel_head_base`. Its source hash is recorded.

Every vector gets the following checks:

1. DUT and base outputs are equal bit for bit.
2. `o_valid == |i_eligible`, and the winner is eligible.
3. For N_SRC = 2: the winner matches the spec-6 definition computed with 64-bit integers,
   `0 < (b−a) mod 2^W < 2^(W−1)`. This reference does not depend on either RTL expression.
4. For clustered vectors: the winner is the lowest-ID oldest eligible source by unwrapped age. In these
   vectors all eligible ages are below 2^(W−1)−1, and the window can straddle the wrap.

## 4. Results

Run `20261020T165027Z_1281` (UTC; 2026-10-21 local) passed every configuration with exit 0 and 0 errors:
**ALL_PASS**, 70.1 s.

| Config | Coverage | Vectors |
| --- | --- | ---: |
| N2, TS_W 2..10 | **exhaustive** over all timestamp pairs × all 4 eligible masks | 64 … 4,194,304 |
| N2, TS_W 11, 12 | **exhaustive** over all timestamp pairs; all-eligible mask + 2 random masks per pair | 12,582,912; 50,331,648 |
| N4, TS_W 2..4 | **exhaustive** over all timestamp vectors × all 16 masks | 4,096; 65,536; 1,048,576 |
| N4, TS_W 5; N8, TS_W 2 | **exhaustive** over all timestamp vectors; all-eligible + 2 random masks | 3,145,728; 196,608 |
| N2, TS_W 32, boundary | structured pairs at both orientations × all masks: 0/1/2/3, 2^31±0..2, 2^32−1..−3, alternating patterns, every 2^k and 2^k−1; each value against value+δ for δ ∈ {0, ±1, ±2, ±(2^31−1), ±2^31, ±(2^31+1), ±2^k, ±(2^k−1)} | 140,800 |
| N2/4/8/16, TS_W 32, seeds 509..512 | 1,000,000 uniform random + 1,000,000 clustered per N; clustered spans 2 / 17 / 2^30 / 2^31−1, `now` just past the wrap, just before it, or random | 2,000,000 each |

Every N2 vector is also checked against the integer spec reference. In total 81,108,288 vectors were
checked with zero mismatches.

### Negative controls

Negative-control file: `mutant-controls.log`. Three mutants of the new function were built outside the
repo, each run at TS_W 4 (exhaustive) and TS_W 32 (boundary). Each of the six runs exited 1:

* **`!d_msb` without the `a != b` guard:** first mismatch is a tie, `ts == 00`.
* **`<=` instead of `<` for the borrow:** first mismatch is a half-range pair, `0x80000000` vs `0`.
* **Borrow dropped:** first mismatch is `0x00000001` vs `0x00000000`.

These mutant builds used `-Wno-fatal`, because the borrow-dropped mutant leaves `borrow` unused. That
relaxation applies only to these negative-control builds; acceptance builds use the strict flags.

### Claim boundary

* **Machine-checked exhaustive equivalence of the actual edited RTL and the HEAD RTL:** only the reduced
  (N, TS_W) configurations listed above.
* **TS_W = 32:** structured boundary vectors plus fixed-seed random vectors. This is strong evidence,
  **not** a proof.
* **General TS_W:** the hand derivation in section 2.

## 5. Lint and existing unit regression (unchanged tests, runner, models)

**Direct strict Verilator lint** (`lint-direct.log`): `cxl_fcfs_sel` with
`verilator --lint-only -Wall -Wpedantic -Werror-IMPLICIT` at N_SRC 2/4/8/16 × TS_W 2/3/32. All 12
configurations exited 0 with no warnings.

**Verible:** 7 style findings, identical in kind and count to HEAD:

* `L_` localparam naming versus Verible's default regex.
* `[0:N-1]` unpacked arrays.

The edit introduces no new Verible findings.

**Existing runner, unmodified** (`scripts/run_verify.sh` sha256 `d7345a27…`, `scripts/run_verify.py`
sha256 `c4892e8b…`, `sim/cxl_fcfs_sel/test_cxl_fcfs_sel.py` sha256 `acaeeb10…`):

| Scope | Run ID | Result | Tests (fail/err/skip) | Content |
| --- | --- | --- | --- | --- |
| M3 | `20261020T165234Z_2953` | PASS, exit 0, 65.5 s | 550 (0/0/0) | 12 strict lint, 3 expected rejections, 235 pytest, 30 cocotb jobs / 315 tests (standalone `cxl_fcfs_sel` N4/8/16 and `switch_top` FCFS N4/8/16, seeds 509..513) |
| M5 | `20261020T165357Z_386` | PASS, exit 0, 99.6 s | 805 (0/0/0) | 27 strict lint, 9 structural probes, 3 expected rejections, 235 pytest, 30 cocotb jobs / 570 tests (Main `switch_top` N4/8/16 × W64/256 × seeds 509..513) |

Both runs report `milestone_acceptance_scope=true`, empty `sim_build_relaxations`, `not_run=0` and 32
JUnit files each. Raw evidence is in `artifacts/implementation/{M3,M5}/<run-id>/`. The tested RTL hash
is `34185051…2c20` in the equivalence run, M3 and M5, and it matches the final file.

**Invocation note:** the first M3 attempt used the brief's literal spelling `--make-jobs2` and was
rejected by argparse (exit 2) before running anything (`M3-console-argerror.log`). It was re-run as
`-j 8 --make-jobs 2`.

## 6. Not done / open

* No stress, primary, production, M1/M2/M4 or Algorithm-2 scopes were run. The parent owns the broad
  regression. Next command:
  `source scripts/wsl_env.sh && scripts/run_verify.sh <scope> -j 8 --make-jobs 2` for each accepted scope.
* **No timing claim.** The rewrite separates the equality test from the borrow chain and only needs the
  borrow-out of a 31-bit magnitude comparison. DC may still map that to a ripple structure. Any
  improvement is unproven until an actual FastX DC/PT run exists.
* No SMT/formal tool was available. The equivalence evidence is bounded as stated in section 4.
