# Synthesis Flow

## CXL Project Synthesis/STA Policy

The approved commercial flow is UIUC FastX Design Compiler and PrimeTime with the university SAED32 library. No project synthesis or STA has run. The previous imported TSMC28/NanGate45 proxy policy is superseded for this project.

| Item | Policy |
|------|--------|
| **Target** | SAED32 RVT on FastX; known environment uses `saed32rvt_tt0p78v25c.db`. Actual host path must be supplied. |
| **Tools** | Module `Synopsys_x86-64/2024`; known DC/PT version W-2024.09, access still unverified here. |
| **Experiment matrix** | FCFS, RR quantum10, main FAI W5,000,000/quotas10/10 by N=4,8,16; D16,M1,full105; nine configurations, all NOT_RUN. |
| **Area metric** | Report actual library-based DC area and declared synthesized boundary. Do not divide by the old NanGate45 constant 0.798. |
| **Memory/queues** | Include common per-source D16 descriptor FIFOs and policy metadata/control. No FIFO blackboxes or omitted area/timing. RR excludes unused timestamp storage. TB memories/responses are excluded. |
| **SDC** | Pilot-derived common scheduler clock, then identical library/PVT/SDC/effort/optimization for all nine. The5ns adder smoke target is not final. Parallel FAI classification stays normally timed, no arbitrary multicycle exceptions. |
| **Power** | Attempt activity-annotated pre-layout estimation if supported; report actual capability/annotation limitation otherwise. No results yet. |

## sv2v Conversion Policy

| Tool | Input | Why sv2v |
|------|-------|---------|
| Yosys (synthesis) | sv2v-converted `.v` | Yosys SV support incomplete |
| SymbiYosys (formal) | sv2v-converted `.v` | Uses Yosys frontend internally |
| verilator/slang | `.sv` directly | Full SV support, no conversion needed |

## Primary Commercial Flow

```bash
# Preflight plan only after local connection configuration exists:
python scripts/remote_eda.py preflight --config scripts/fastx.config.local.json
# Synthesis/STA plans remain gated on real specification approval and design inputs:
python scripts/remote_eda.py syn --config scripts/fastx.config.local.json
python scripts/remote_eda.py sta --config scripts/fastx.config.local.json
```

See `docs/FASTX.md` for explicit execution, restricted transfers, and required inputs. Local Yosys/formal wrappers remain optional scaffolding and do not replace the nine commercial experiments or authorize another library.

## Directory Structure (DC-standard)

```
syn/
├── db/               # Binary databases (.ddc, .db, .genus_db)
├── vnet/             # Gate-level netlists (.v, .json)
├── svf/              # Setup Verification Flow (.svf, DC only)
├── scr/              # Generated scripts (.tcl, .ys) + replay/
├── rpt/              # Reports (area, timing, power, qor)
├── log/              # Synthesis logs
├── temp/             # Cache and temporary files
├── work/             # Tool work directories
├── scripts/          # Runner scripts (run_syn.sh, run_formality.sh, etc.)
└── constraints/      # SDC constraint files
    └── design.sdc
```

<!-- rat-version: 0.8.20 -->
