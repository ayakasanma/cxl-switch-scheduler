# Main-SQ verification record

## Actual completed checks

| Check | Status | Evidence |
| --- | --- | --- |
| Archived HS-main15 exact results/trace groups | PASS | Fresh independent archive audit;15 runs, five groups; zero new RTL cycles. |
| Installed Claude/RTL Agent Team | PASS | CLI2.1.306, plugin0.14.6; actual Opus5.5/medium focused workflow and testbench-dev invocations. |
| New passive-recorder unit fixtures | PASS after repairs | Six cases; original two failing attempts retained in native stream/tool-output extraction. |
| Existing heavy/sparse traffic units | PASS |26 cases in the pilot. |
| Strict Verilator pilot lint/build | PASS | Three policy configurations, no warning relaxations. |
| W256 passive RTL pilot | PASS | MSQ-pilot/20261023T082655Z_633, three simulations, actual outer exit0,32 units, scope PASS. |
| Independent request/trace reconstruction | PASS | Every pilot request agrees with native recorder; stable metrics equal the accepted pilot. |
| Offline screen controls | PASS | Six tests/14 subtests: exact ranks, corruption, simultaneous-generation conservation, one eligible source, partial SQ2 across Low, full-before-pop rejection. |
| Oldest-head positive control | PASS | All2,400 pilot High grants match independently reconstructed oldest accepted heads. |
| Original source/evidence preservation | PASS at checkpoint |694 protected files, plus264 earlier raw metrics hash-identical. Final is not edited/built/rendered. |

## Production replay — PASS

`MSQ-main/20261023T083405Z_1850` started UTC2026-10-23T08:34:05.525004 at source
`3e457cc`, three policies, N4/W5M/seed509, jobs3/buildjobs2. It completed UTC09:21:11.092159,
actual outer exit0 after2825.623s. All three strict lint sets,32 unit cases, three RTL
simulations and scope gate PASS. Raw JUnit has zero failures/errors/skips; every tool
exit is0. Both110-file before/after runtime manifests match and current runtime files
match them. All nonvolatile metrics equal the old seed509 records exactly.

Production executes31,333,251 nonreset cycles:30M training,607,200 measurement,6,144 guards,
719,907 drain. With the pilot the total is31,962,468:30,001,536 training,1,214,400 measurement,
12,288 guards,734,244 drain. Initial reset edges are excluded. These are six actual RTL
cases, one seed at two W settings, not six independent random seeds. The32 native unit
cases are repeated in the two scopes, not64 distinct tests.

The runner explicitly compares all nonvolatile original metrics with the accepted
`HS-main/20261022T034507Z_311`. The parent audit additionally reconstructs all sparse
producer/FIFO events from the gzip trace, checks raw JUnit/exits, repeats the exact
histogram/rank calculation, and joins identical tags across policies.

## Candidate implementation checks

SQ RTL, its independent behavioral golden model, directed/random regression and
own-netlist Formality are **NOT_RUN**, because the [benefit gate failed](BASELINE_DIAGNOSIS.md).
The requested five-policy workload matrix and candidate downstream-stall/dynamic cases
are likewise NOT_RUN by that conditional stop. Existing Main
correctness and14 prior equivalence pairs remain accepted history, not SQ verification.
No RTL assertion or warning requirement has been waived.

The plugin's stale six-entry RTL-modified hook list is retained; it is not evidence of
new RTL edits. Git and byte hashes show all existing RTL/model/test sources preserved.

## Reproduction

```sh
source scripts/wsl_env.sh
CXL_MSQ_REFERENCE=artifacts/implementation/HS-pilot/20261022T034155Z_369 \
  python scripts/run_main_sq_diagnosis.py MSQ-pilot -j 3 --make-jobs 2
CXL_MSQ_REFERENCE=artifacts/implementation/HS-main/20261022T034507Z_311 \
  python scripts/run_main_sq_diagnosis.py MSQ-main -j 3 --make-jobs 2
python -m unittest discover -s docs/experiments/main-sq -p test_trace_analysis.py
python docs/experiments/main-sq/analyze_trace.py --run RUN_DIRECTORY --output FRESH_AUDIT_DIRECTORY
```

Use fresh output directories; preserve failed/incomplete attempts. Instrumentation assumes
ready1/no bubbles in this specific experiment; it is not a generic stalled-traffic recorder.

The [2.2MB raw bundle](production-replay-seed509.tar.gz) contains the actual production
results/traces, raw JUnit, source snapshots, accepted references and a portable summary
projection. Extraction into a fresh directory and a fresh independent audit both PASS;
all reconstructed statistics match the original-directory audit. Original full logs and
summary remain in the unmodified local artifact directory. This re-audit adds zero RTL cycles.
