#!/usr/bin/env bash
set -euo pipefail
if test "$#" -ne 5; then
  printf 'usage: bash scripts/run_cgof_power_pilot.sh CASE_ROOT WEIGHT CELL_MODEL DB COMPUTE_APPROVAL_JSON\n' >&2
  exit 2
fi
case_root=$1
weight=$2
cell_model=$3
db=$4
compute_approval=$5
case "$weight" in 1|2) ;; *) printf 'invalid CGOF weight\n' >&2; exit 2 ;; esac
payload=$(pwd -P)
test -f metadata.json
test -f vectors.txt.gz
test ! -e execution
mkdir execution
cd execution
mkdir reports
trap 'code=$?; printf "shell_exit=%s\n" "$code" >> reports/exits.txt' EXIT
run_stage() {
  local stage=$1 budget=$2 code
  shift 2
  printf '%q ' /usr/bin/timeout --signal=TERM --kill-after=20s "$budget" "$@" > "reports/$stage.command.txt"
  printf '\n' >> "reports/$stage.command.txt"
  set +e
  /usr/bin/timeout --signal=TERM --kill-after=20s "$budget" "$@" > "reports/$stage.log" 2>&1
  code=$?
  set -e
  printf '%s=%s\n' "$stage" "$code" >> reports/exits.txt
  test "$code" -eq 0
}
export OMP_NUM_THREADS=1 VCS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export POWER_CASE_ROOT="$case_root" POWER_SAIF="$PWD/activity.saif" POWER_REPORT_DIR="$PWD/reports"
export POWER_N=4 POWER_POLICY=CGOF POWER_HIGH_WEIGHT="$weight" POWER_DB="$db"
run_stage payload 300s python3 "$payload/scripts/check_cgof_power_replay.py" payload \
  --root "$payload" --case-root "$case_root" --weight "$weight" --cell-model "$cell_model" \
  --database "$db" --compute-approval "$compute_approval" --destination vectors.txt
cp reports/payload.log reports/payload-audit.json
finish_sources() {
  python3 - reports/payload-audit.json <<'PY'
import hashlib, json, pathlib, sys
bindings = json.loads(pathlib.Path(sys.argv[1]).read_text())['file_sha256']
for name, expected in bindings.items():
    with pathlib.Path(name).open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError('input changed during execution: ' + name)
print(json.dumps(dict(status='SOURCE_BEFORE_AFTER_IDENTICAL', file_sha256=bindings), indent=2))
PY
}
trap 'code=$?; set +e; finish_sources > reports/source-after.json 2> reports/source-after.stderr.txt; source_code=$?; printf "source_check=%s\nshell_exit=%s\n" "$source_code" "$code" >> reports/exits.txt; if test "$code" -eq 0; then exit "$source_code"; fi; exit "$code"' EXIT
date -u +%FT%TZ > reports/start-utc.txt
hostname -f > reports/hostname.txt
id -un > reports/account.txt
command -v vcs pt_shell python3 > reports/tool-paths.txt
module list > reports/module-list.txt 2>&1
set +e
/usr/bin/timeout 30s vcs -ID > reports/vcs-version.txt 2>&1
printf 'vcs_version=%s\n' "$?" >> reports/exits.txt
/usr/bin/timeout 30s pt_shell -version > reports/pt-version.txt 2>&1
printf 'pt_version=%s\n' "$?" >> reports/exits.txt
set -e
run_stage compile 900s vcs -full64 -sverilog -j1 +delay_mode_zero +notimingcheck -debug_access+all \
  -timescale=1ns/1ps +define+POWER_N_SRC=4 "+define+POWER_CGOF_WEIGHT=$weight" -top tb \
  "$cell_model" "$case_root/output/cgof_unit_top.syn.v" "$payload/sim/power/tb_power.sv" -o simv
run_stage compile-log-audit 30s python3 "$payload/scripts/check_cgof_power_replay.py" logs --reports reports --stage compile
run_stage sim 1200s ./simv -no_save +vectors=vectors.txt +result=reports/replay.txt +saif=activity.saif
run_stage sim-log-audit 30s python3 "$payload/scripts/check_cgof_power_replay.py" logs --reports reports --stage sim
run_stage replay-audit 120s python3 "$payload/scripts/check_cgof_power_replay.py" replay \
  --metadata "$payload/metadata.json" --result reports/replay.txt --saif activity.saif
cp reports/replay-audit.log reports/replay-audit.json
run_stage pt 900s pt_shell -f "$payload/sta/power_pt.tcl"
run_stage pt-log-audit 30s python3 "$payload/scripts/check_cgof_power_replay.py" logs --reports reports --stage pt
run_stage pilot-audit 120s python3 "$payload/scripts/check_cgof_power_replay.py" replay \
  --metadata "$payload/metadata.json" --result reports/replay.txt --saif activity.saif --pt-reports reports
cp reports/pilot-audit.log reports/pilot-audit.json
finish_sources > reports/source-after.json
printf 'COMMANDS_COMPLETED_SEMANTIC_REVIEW_REQUIRED\n' > reports/run-status.txt
