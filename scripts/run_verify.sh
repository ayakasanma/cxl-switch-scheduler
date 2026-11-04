#!/usr/bin/env bash
# Fail-fast verification runner for the controlled CXL scheduler milestones.
#
# Usage (from a WSL Bash shell, any working directory):
#   source scripts/wsl_env.sh
#   scripts/run_verify.sh <milestone> [--seeds a..b|a,b,c] [--lint-only] [--keep-going] [-j N]
#   scripts/run_verify.sh --list
#
# The milestone table and all checking logic live in scripts/run_verify.py. This wrapper only
# verifies that the documented tool environment is active and never installs or changes anything.
# Exit status: 0 = every executed step passed, 1 = at least one step failed, 2 = usage error or
# undefined/unimplemented milestone.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

for tool in verilator python make git; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "run_verify: required tool '${tool}' is not on PATH (source scripts/wsl_env.sh first)" >&2
    exit 2
  fi
done

if ! python -c 'import cocotb, cocotb_tools.config, find_libpython, pytest' >/dev/null 2>&1; then
  echo "run_verify: the active python lacks cocotb/pytest (source scripts/wsl_env.sh first)" >&2
  exit 2
fi

cd "${REPO_ROOT}"
export PYTHONDONTWRITEBYTECODE=1
exec python "${SCRIPT_DIR}/run_verify.py" --repo-root "${REPO_ROOT}" "$@"
