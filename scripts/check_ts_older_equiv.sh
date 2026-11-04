#!/usr/bin/env bash
# check_ts_older_equiv.sh — self-check of the cxl_fcfs_sel ts_older rewrite (WSL, Verilator).
#
# Builds scripts/ts_older_equiv/tb_ts_older_equiv.sv against BOTH the working-tree
# rtl/common/cxl_fcfs_sel.sv and the baseline cxl_fcfs_sel.sv taken from git (BASE_REV, renamed
# to cxl_fcfs_sel_head_base), then runs the configuration list below. Every run must print PASS
# and exit 0; the first failure stops the script (fail-fast).
#
# Claim scope: exhaustive over all inputs only for the listed reduced (N_SRC, TS_W) builds;
# TS_W = 32 runs are structured boundary + fixed-seed random vectors, NOT a proof.
#
# Usage: source scripts/wsl_env.sh; scripts/check_ts_older_equiv.sh <log_dir> [BASE_REV]
set -euo pipefail

LOG_DIR="${1:?usage: check_ts_older_equiv.sh <log_dir> [BASE_REV]}"
# Keep the pre-rewrite source fixed after the candidate is committed.
BASE_REV="${2:-b54aa645480b891c349bf4b5814f8b6f66034a01}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)_$$"
BUILD="${CXL_EQUIV_BUILD:-$HOME/.cache/cxl-scheduler/ts_older_equiv}/$STAMP"
mkdir -p "$LOG_DIR" "$BUILD"
LOG_DIR="$(cd "$LOG_DIR" && pwd)"

cd "$REPO"
PKG=rtl/include/cxl_sched_pkg.sv
DUT=rtl/common/cxl_fcfs_sel.sv
TB=scripts/ts_older_equiv/tb_ts_older_equiv.sv
BASE="$BUILD/cxl_fcfs_sel_head_base.sv"

BASE_COMMIT="$(git rev-parse "$BASE_REV")"
git show "$BASE_COMMIT:$DUT" > "$BUILD/base_orig.sv"
if cmp -s "$BUILD/base_orig.sv" "$DUT"; then
  echo "refusing identical DUT and baseline sources" >&2
  exit 2
fi
sed 's/^module cxl_fcfs_sel #(/module cxl_fcfs_sel_head_base #(/' "$BUILD/base_orig.sv" > "$BASE"
grep -q '^module cxl_fcfs_sel_head_base #(' "$BASE" || { echo "base rename failed"; exit 2; }

SUMMARY="$LOG_DIR/summary.txt"
{
  echo "run_id=$STAMP"
  echo "repo_head=$(git rev-parse HEAD)"
  echo "base_rev=$BASE_REV base_commit=$BASE_COMMIT"
  echo "verilator=$(verilator --version)"
  sha256sum "$PKG" "$DUT" "$TB" "$0"
  echo "$(sha256sum < "$BUILD/base_orig.sv" | cut -d' ' -f1)  git:$BASE_COMMIT:$DUT"
  echo "$(sha256sum < "$BASE" | cut -d' ' -f1)  base_renamed"
} > "$SUMMARY"

# name N_SRC TS_W MODE N_RAND SEED
CONFIGS=(
  "exh_n2_w2   2  2 0 0 1" "exh_n2_w3   2  3 0 0 1" "exh_n2_w4   2  4 0 0 1"
  "exh_n2_w5   2  5 0 0 1" "exh_n2_w6   2  6 0 0 1" "exh_n2_w7   2  7 0 0 1"
  "exh_n2_w8   2  8 0 0 1" "exh_n2_w9   2  9 0 0 1" "exh_n2_w10  2 10 0 0 1"
  "exh_n2_w11  2 11 0 0 1" "exh_n2_w12  2 12 0 0 1"
  "exh_n4_w2   4  2 0 0 1" "exh_n4_w3   4  3 0 0 1" "exh_n4_w4   4  4 0 0 1"
  "exh_n4_w5   4  5 0 0 1" "exh_n8_w2   8  2 0 0 1"
  "bnd_n2_w32  2 32 1 0 1"
  "rnd_n2_w32  2 32 2 1000000 509" "rnd_n4_w32  4 32 2 1000000 510"
  "rnd_n8_w32  8 32 2 1000000 511" "rnd_n16_w32 16 32 2 1000000 512"
)

for cfg in "${CONFIGS[@]}"; do
  read -r name n w mode nrand seed <<< "$cfg"
  mdir="$BUILD/$name"
  echo "=== $name (N_SRC=$n TS_W=$w MODE=$mode N_RAND=$nrand SEED=$seed)"
  verilator --binary -Wall -Wpedantic -Werror-IMPLICIT -j 0 --Mdir "$mdir" \
    --top-module tb_ts_older_equiv -o sim \
    -GN_SRC="$n" -GTS_W="$w" -GMODE="$mode" -GN_RAND="$nrand" -GSEED="$seed" \
    "$PKG" "$DUT" "$BASE" "$TB" > "$LOG_DIR/$name.build.log" 2>&1 \
    || { echo "BUILD FAIL $name"; tail -40 "$LOG_DIR/$name.build.log"; echo "$name BUILD_FAIL" >> "$SUMMARY"; exit 1; }
  set +e
  "$mdir/sim" > "$LOG_DIR/$name.run.log" 2>&1
  rc=$?
  set -e
  grep '^RESULT' "$LOG_DIR/$name.run.log" || true
  if [[ $rc -ne 0 ]] || ! grep -qx 'PASS' "$LOG_DIR/$name.run.log"; then
    echo "RUN FAIL $name rc=$rc"; tail -30 "$LOG_DIR/$name.run.log"
    echo "$name FAIL rc=$rc" >> "$SUMMARY"; exit 1
  fi
  echo "$name PASS rc=0 $(grep '^RESULT' "$LOG_DIR/$name.run.log")" >> "$SUMMARY"
done
echo "ALL_PASS" >> "$SUMMARY"
echo "ALL_PASS (summary: $SUMMARY)"
