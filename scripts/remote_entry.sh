#!/usr/bin/env bash
# Uploaded only by remote_eda.py; no university libraries or executables are copied.
set -euo pipefail

load_eda() {
  if ! type module >/dev/null 2>&1; then
    if [[ -z "${EDA_MODULE_INIT:-}" ]]; then
      echo 'The module command is unavailable. Configure module_init with the university-approved initialization script.' >&2
      exit 2
    fi
    [[ -r "$EDA_MODULE_INIT" ]] || { echo 'Configured module_init is not readable.' >&2; exit 2; }
    # This existing host script is supplied by the university, never uploaded.
    source "$EDA_MODULE_INIT"
  fi
  type module >/dev/null 2>&1 || { echo 'module_init did not define module.' >&2; exit 2; }
  module load "$EDA_MODULE"
  command -v dc_shell >/dev/null || { echo 'dc_shell is unavailable after module load.' >&2; exit 2; }
  command -v pt_shell >/dev/null || { echo 'pt_shell is unavailable after module load.' >&2; exit 2; }
  [[ -r "$EDA_TARGET_LIBRARY" && -f "$EDA_TARGET_LIBRARY" ]] || {
    echo 'Configured target_library is not a readable file on this host.' >&2
    exit 2
  }
}

mode="${1:-}"
case "$mode" in
  preflight|syn|sta) ;;
  *) echo 'Expected preflight, syn, or sta.' >&2; exit 2 ;;
esac
: "${EDA_MODULE:?Missing EDA_MODULE}"
: "${EDA_TARGET_LIBRARY:?Missing EDA_TARGET_LIBRARY}"
load_eda

if [[ "$mode" == preflight ]]; then
  printf 'Remote host: '
  hostname
  printf 'Remote OS: '
  uname -s
  printf 'Module: %s\n' "$EDA_MODULE"
  dc_shell -version
  pt_shell -version
  printf 'Target library is readable: %s\n' "$EDA_TARGET_LIBRARY"
  echo 'Preflight checks passed. No synthesis or STA was performed.'
  exit 0
fi

: "${EDA_JOB_DIR:?Missing EDA_JOB_DIR}"
: "${EDA_TOP_MODULE:?Missing EDA_TOP_MODULE}"
cd -- "$EDA_JOB_DIR"
[[ -f run_config.tcl && -f ARCHITECTURE_APPROVAL.md ]] || {
  echo 'Missing generated run configuration or architecture approval record.' >&2
  exit 2
}
mkdir -- reports output
if [[ "$mode" == syn ]]; then
  dc_shell -f syn/dc.tcl 2>&1 | tee reports/dc.log
  tool_log=reports/dc.log
  [[ -s "output/${EDA_TOP_MODULE}.syn.v" && -s "output/${EDA_TOP_MODULE}.syn.sdc" ]] || {
    echo 'Synthesis did not produce a nonempty netlist and SDC.' >&2
    exit 3
  }
else
  pt_shell -f sta/pt.tcl 2>&1 | tee reports/pt.log
  tool_log=reports/pt.log
fi
[[ -f reports/run_status.rpt ]] && grep -Fxq 'STATUS: SUCCESS' reports/run_status.rpt || {
  echo 'The Tcl script did not reach its completion marker.' >&2
  exit 3
}
if grep -Eq '(^|[[:space:]])(Error:|Fatal:|EDA_FAILURE:)' "$tool_log"; then
  echo 'The tool log contains an error, fatal diagnostic, or Tcl failure marker.' >&2
  exit 3
fi
echo 'Tool commands completed. Review reports and timing coverage before accepting results.'
