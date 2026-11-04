#!/usr/bin/env bash
# Source from a WSL Bash shell; does not change .bashrc or machine configuration.
# This project-dedicated tool environment lives on the Linux filesystem.
export CXL_TOOL_HOME="${CXL_TOOL_HOME:-$HOME/.local/opt/cxl-scheduler}"
export CXL_VENV="${CXL_VENV:-$HOME/.local/share/cxl-scheduler/venvs/py312-cocotb210}"
export PATH="$CXL_VENV/bin:$CXL_TOOL_HOME/verilator-5.052/bin:$CXL_TOOL_HOME/verible-v0.0-4296-g0f262651/bin:$PATH"
# Installed-prefix Verilator locates its own runtime; a inherited Git-build root
# could silently select a different tool runtime and must not override it.
unset VERILATOR_ROOT
export SIM=verilator
export PYTHONNOUSERSITE=1
