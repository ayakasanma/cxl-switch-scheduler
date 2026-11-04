#!/usr/bin/env bash
# Execute inside a dedicated uploaded replay payload; all machine paths are arguments.
set -euo pipefail
if test "$#" -ne 5; then
  printf 'usage: bash scripts/run_power_pilot.sh CASE_ROOT N POLICY CELL_MODEL DB\n' >&2
  exit 2
fi
case_root=$1
n=$2
policy=$3
cell_model=$4
db=$5
payload=$(pwd)
test -f metadata.json
test -f vectors.txt.gz
mkdir execution
cd execution
mkdir reports
audit_sources() {
  sha256sum "$cell_model" "$db" "$case_root/run_config.tcl" "$case_root/output/switch_top.syn.v" \
    "$case_root/output/switch_top.syn.sdc" "$payload/metadata.json" "$payload/vectors.txt.gz" \
    "$payload/sim/power/tb_power.sv" "$payload/sta/power_pt.tcl" \
    "$payload/scripts/check_power_replay.py" "$payload/scripts/run_power_pilot.sh"
}
trap 'code=$?; audit_sources > reports/source-after.sha256; printf "shell_exit=%s\n" "$code" >> reports/exits.txt' EXIT
run_stage() {
  local stage=$1
  shift
  local code
  set +e
  "$@" > "reports/$stage.log" 2>&1
  code=$?
  set -e
  printf '%s=%s\n' "$stage" "$code" >> reports/exits.txt
  test "$code" -eq 0
}
export POWER_CASE_ROOT="$case_root" POWER_SAIF="$PWD/activity.saif" POWER_REPORT_DIR="$PWD/reports"
export POWER_N="$n" POWER_POLICY="$policy" POWER_DB="$db"
python3 - "$payload" "$n" "$policy" "$case_root" <<'PY'
import gzip, hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / 'scripts'))
from check_power_replay import check_payload_mode
m = json.loads((root / 'metadata.json').read_text())
check_payload_mode(m, int(sys.argv[2]), sys.argv[3])
assert m['profile_canonical_sha256'] == '6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d'
for rel in ('sim/power/tb_power.sv', 'sta/power_pt.tcl', 'scripts/check_power_replay.py', 'scripts/run_power_pilot.sh'):
    assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == m['source_sha256'][rel], rel
for rel, expected in m['accepted_case_sha256'].items():
    assert hashlib.sha256((pathlib.Path(sys.argv[4]) / rel).read_bytes()).hexdigest() == expected, rel
def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for data in iter(lambda: handle.read(65536), b''):
            digest.update(data)
    return digest.hexdigest()
assert digest_file(root / 'vectors.txt.gz') == m['vectors_gzip_sha256']
digest = hashlib.sha256()
with gzip.open(root / 'vectors.txt.gz', 'rb') as source, pathlib.Path('vectors.txt').open('xb') as destination:
    for data in iter(lambda: source.read(65536), b''):
        digest.update(data)
        destination.write(data)
assert digest.hexdigest() == m['vectors_text_sha256']
PY
printf '%s  %s\n' d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286 "$cell_model" | sha256sum -c -
printf '%s  %s\n' 844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094 "$db" | sha256sum -c -
audit_sources > reports/source.sha256
date -u +%FT%TZ > reports/start-utc.txt
command -v vcs pt_shell > reports/tool-paths.txt
run_stage compile vcs -full64 -sverilog +delay_mode_zero +notimingcheck -debug_access+all -timescale=1ns/1ps \
  "+define+POWER_N_SRC=$n" -top tb "$cell_model" "$case_root/output/switch_top.syn.v" \
  "$payload/sim/power/tb_power.sv" -o simv
run_stage sim ./simv -no_save +vectors=vectors.txt +result=reports/replay.txt +saif=activity.saif
python3 "$payload/scripts/check_power_replay.py" --metadata "$payload/metadata.json" \
  --result reports/replay.txt --saif activity.saif > reports/replay-audit.json
run_stage pt pt_shell -f "$payload/sta/power_pt.tcl"
python3 "$payload/scripts/check_power_replay.py" --metadata "$payload/metadata.json" \
  --result reports/replay.txt --saif activity.saif --pt-reports reports > reports/pilot-audit.json
audit_sources > reports/source-after.sha256
cmp reports/source.sha256 reports/source-after.sha256
printf 'COMMANDS_COMPLETED_SEMANTIC_REVIEW_REQUIRED\n' > reports/run-status.txt
