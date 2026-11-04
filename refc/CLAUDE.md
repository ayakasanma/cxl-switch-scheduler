# C Reference Model

Project override: approved Spec v1.0 requires independent Python cycle-level models. Independent FIFO/common/FCFS/RR/Main FAI models are implemented and functionally verified in cxl_model/; Algorithm-2 has a separate abstract model and accepted N4 directed/behavior scope; full production-window verification remains pending. Current evidence and limits are in ../docs/STATUS.md and ../docs/phase-5-verification/M5-results.md. C11/DPI-C conventions below remain inactive imported examples. Preserve serial Claude authorship and real WSL verification; no SystemC installation is required.

## Standards

- **Language**: C11 (`-std=c11`). C++ is NOT used for reference models
- **Model type**: Functional model — no clock, no reset, pure algorithm
- **External memory**: Access functions must be abstracted (callback/function pointer)
- **DPI-C**: Primary integration method with SystemVerilog

## Directory Structure

```
refc/
├── src/              # Flat source (single-module ref model)
├── {module}/         # Per-module ref model (multi-module projects)
├── include/          # Common headers
├── build/            # Build output (.so for DPI-C)
├── test/             # Ref model unit tests
└── vectors/          # Test vectors
    ├── perf/         # Performance test vectors
    └── conformance/  # Conformance test vectors
```

## Build

```bash
gcc -std=c11 -shared -fPIC -o build/lib{module}_ref.so src/*.c -Iinclude
```

<!-- rat-version: 0.7.7 -->
