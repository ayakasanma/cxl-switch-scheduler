# CXL Switch Scheduler

A cycle-accurate study of how a CXL memory-pooling switch should arbitrate between a
bandwidth-hungry host and hosts that send requests only occasionally.

## The problem in one paragraph

Several servers share a memory pool through one CXL switch, so every request leaves
through a single egress port. One host behaves like a hog and keeps the port busy; the
others send a request every few hundred cycles. Under first-come-first-served the rare
request queues behind the hog's deep backlog and its 99th-percentile wait explodes. If
you instead give the quiet hosts a fixed slice, the hog loses regularity and, under
overload, finishes later. The question this repository answers is what a switch can do
in hardware, using only the information it already holds, to protect the rare request
without wrecking the hog.

## What is in the box

| Path | Contents |
| --- | --- |
| `rtl/` | Synthesizable SystemVerilog: shared FIFO, hold controller, FCFS, RR, FAI-inspired and CGOF |
| `refc/` | Independent Python reference models and their tests |
| `sim/` | cocotb testbenches, diagnosis traffic, accounting and measurement runners |
| `scripts/` | Regression, diagnosis, analysis and statistics runners |
| `specs/` | Approved specification, decisions and approval record |
| `docs/` | Experiment records, plans, review notes and the project outline |
| `evidence/` | Selected machine-readable acceptance records for the numbers below |

Start with [docs/PROJECT_STORY_AND_GAPS_OUTLINE.md](docs/PROJECT_STORY_AND_GAPS_OUTLINE.md)
for the narrative, and [docs/DEVELOPMENT_REPORT.md](docs/DEVELOPMENT_REPORT.md) for the
dated record of what was run.

## The four schedulers

`FCFS` is the baseline. `RR10` visits each source and allows up to ten consecutive
fires; it stores no timestamps and is the smallest design. `FAI-inspired` reproduces the
FAI-CXL idea: a window-based classifier labels each source High or Low from its recent
service count, and a 10:10 class quota alternates between the two classes.

`CGOF` keeps the same classifier but moves the quota from the class to each source:
a source with positive credit and a non-empty queue joins the eligible set, and the
oldest eligible request fires. Credits refill per source, 2 for High and 1 for Low in
the 2:1 configuration. That single change removes the class-size skew that hurts the
original design when one class holds one host and the other holds three.

## Headline results

On the twenty-seed N4 confirmation with the classifier trained to steady state,
CGOF (2:1) cuts the rare-request generation-to-fire P99 from 10.00 to 1.10 cycles for
independent arrivals and from 21.05 to 12.35 cycles for bursty arrivals, against
FAI-inspired. In the area report, CGOF (2:1) needs 109,794.8 cells against 110,089.8
for FAI-inspired at N4, so the gain does not cost area.

The parts that are easy to get wrong are recorded as plainly as the wins:

- Ordering inside the eligible set is a second-order effect. At W256 it moved one cycle
  in 7 of 20 seeds and was formally `NOT_CONFIRMED`; at W5M production it produced
  11/11/12/11 cycles across four policy/ordering combinations.
- When every source is effectively High, 1:1 beats 2:1 on the rare-request tail (3 vs 4
  cycles), because a larger credit budget lets one source fire twice per round.
- Under overload the protection has a price: in the model, the hog's completion time
  grows by about 834 cycles, and its worst service gap grows by one to two cycles.

## Evidence levels

Every claim carries the level of the evidence behind it, and the levels are not
interchangeable:

- `SCHEDULER_RTL` means a cocotb run against the actual RTL.
- `MODEL_ONLY` means the Python reference model.
- `NOT_RUN` means nobody has measured it.

The multi-window role-switch campaign is planned and frozen but not run, so it is
`NOT_RUN`. Application slowdown, CXL.mem end-to-end latency and gate-level power for
CGOF are also `NOT_RUN`. The statistics runners keep the model-derived results labelled
as such.

## Running it

The Python model and analysis run on any machine with Python 3.12:

```bash
python -m pytest -q refc/tests sim/experimental/test_diagnosis_source_book.py
python scripts/cgof_diagnosis_model.py --job job.json --output result.json --policy "CGOF(2:1)"
python scripts/analyze_dynamic_role_switch.py --results results/*.json --output report.json
```

RTL simulation needs Verilator and cocotb, which this project runs inside Ubuntu WSL:

```bash
source scripts/wsl_env.sh
python scripts/run_rtl_diagnosis.py --smoke --mode finite-heavy --policy both \
  --seed 7301 --window 256 --windows 4 --heavy-work 896 --profile near
```

`scripts/run_rtl_diagnosis.py` selects CGOF with `--policy 1:1|2:1|both` and Main with
`--policy main|all`. A W5M run requires `--production-reviewed` and takes hours per job.

## Where the numbers come from

`evidence/` holds the acceptance records: the G1 model replay, the A2 short-window
RTL/model comparison, the A3 Main W5M anchors, the pilot campaign and its measured
cost. Each record names its inputs by SHA-256, so a reviewer can trace a number back to
the file that produced it. Full run directories stay out of the repository because they
are large; the acceptance records are the index into them.

## Status

The scheduler RTL, the reference models, the diagnosis harness and the statistics
tooling are in place. What remains is the experiment backlog in
[docs/EXPERIMENTS_BACKLOG.md](docs/EXPERIMENTS_BACKLOG.md): the W5M multi-window
campaign, under- and over-load RTL points, CGOF power, and system-level simulation.
