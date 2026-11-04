# FastX 手動執行交接手冊

適用：2026-10-17 已驗收的 FCFS／RR10／FAI Main，N=4/8/16、D16、M1、full105。從 **FastX桌面內的 Bash終端** 操作即可，不必先提供 SSH給 Codex。完整階段結果見[小結](STAGE_SUMMARY_2026-10-17.md)。

**執行狀態：以下是尚未在 FastX驗證的操作範本，不是已成功的 synthesis／STA結果。** 本階段沒有更動已驗收 RTL，也沒有執行商用工具。先做一個 pilot，遇到 analyze/link/constraint錯誤就停下保留 log，不要跳過後繼續九組。

## 1. 傳輸並確認來源

本機交接產物在 `artifacts/handoff/<交接commit>/`：`cxl-scheduler-fastx-<short>.tar.gz`、`SHA256SUMS`、`manifest.json`。請用現有的檔案傳輸方式，把 tar.gz與SHA256SUMS放進同一個 FastX資料夾。這是既有 repository的來源快照，沒有 `.git`，不建立第二個開發 repository。

在該資料夾開終端，先確認 hash；下面 `CXL_PACKAGE` 填實際上傳檔名：

```bash
set -euo pipefail
sha256sum -c SHA256SUMS
export CXL_PACKAGE="$PWD/cxl-scheduler-fastx-FILL_COMMIT.tar.gz"
test -f "$CXL_PACKAGE"
export CXL_TRANSFER_ROOT="$(mktemp -d "$HOME/cxl-fastx.XXXXXX")"
tar -xzf "$CXL_PACKAGE" -C "$CXL_TRANSFER_ROOT"
export CXL_SOURCE_ROOT="$CXL_TRANSFER_ROOT/cxl-scheduler"
cd "$CXL_SOURCE_ROOT"
sha256sum -c FILE_SHA256SUMS
cat SOURCE_REVISION.txt
```

保留 `SOURCE_REVISION.txt`、`HANDOFF_MANIFEST.json` 與 `FILE_SHA256SUMS`，以免把不同版本的 RTL或文件混用。不要把 university `.db`、PDK、license或工具程式複製進來源包。

## 2. 確認 module、工具與 library

library絕對路徑請從你先前已成功的 adder腳本／學校環境設定取得；以下佔位路徑必須替換。若 `module` 不存在，使用學校提供的初始化方式，不要猜初始化檔路徑。

```bash
module load Synopsys_x86-64/2024
export CXL_TARGET_LIBRARY='/FILL_EXISTING_PATH/saed32rvt_tt0p78v25c.db'
test -f "$CXL_TARGET_LIBRARY"
test -r "$CXL_TARGET_LIBRARY"
export CXL_RUN_ROOT="$CXL_TRANSFER_ROOT/runs"
mkdir "$CXL_RUN_ROOT"
{
  date -Is
  hostname
  uname -s
  module list
  command -v dc_shell
  dc_shell -version
  command -v pt_shell
  pt_shell -version
  sha256sum "$CXL_TARGET_LIBRARY"
  cat "$CXL_SOURCE_ROOT/SOURCE_REVISION.txt"
} 2>&1 | tee "$CXL_RUN_ROOT/preflight.log"
```

預期 module=`Synopsys_x86-64/2024`、DC/PT=`W-2024.09`、SAED32 RVT TT0.78V25°C。檔案可讀和 version命令成功，仍不代表 compile／license checkout成功；真正 pilot成功才有該次工具執行證據。

## 3. 共同 profile：先 pilot，再凍結

建立一個只放本次設定的目錄，所有九組都使用它：

```bash
export CXL_PROFILE_ROOT="$CXL_TRANSFER_ROOT/profile"
mkdir "$CXL_PROFILE_ROOT"
```

用 FastX文字編輯器建立 `profile/common.sdc`。先填 **pilot候選值**；確認 library時間／電容單位後才填數字，不要假設固定為 ns／pF。以下 `FILL_ME` 故意不給預設值。輸入 delay含同步 reset `rst_n`，不要對它設 false path，也不要把它固定為1而移除 reset邏輯。

```tcl
set PERIOD FILL_ME
set SETUP_UNCERTAINTY FILL_ME
set HOLD_UNCERTAINTY FILL_ME
set INPUT_DELAY_MIN FILL_ME
set INPUT_DELAY_MAX FILL_ME
set OUTPUT_DELAY_MIN FILL_ME
set OUTPUT_DELAY_MAX FILL_ME
set INPUT_TRANSITION FILL_ME
set CLOCK_TRANSITION FILL_ME
set OUTPUT_LOAD FILL_ME
foreach name {PERIOD SETUP_UNCERTAINTY HOLD_UNCERTAINTY INPUT_DELAY_MIN INPUT_DELAY_MAX OUTPUT_DELAY_MIN OUTPUT_DELAY_MAX INPUT_TRANSITION CLOCK_TRANSITION OUTPUT_LOAD} {
    if {![string is double -strict [set $name]] || [set $name] < 0} {
        error "Fill nonnegative numeric profile value: $name"
    }
}
if {$PERIOD <= 0} {error "PERIOD must be positive"}
if {$INPUT_DELAY_MIN > $INPUT_DELAY_MAX || $OUTPUT_DELAY_MIN > $OUTPUT_DELAY_MAX} {
    error "Delay MIN must not exceed MAX"
}
create_clock -name core_clk -period $PERIOD [get_ports clk]
set_clock_uncertainty -setup $SETUP_UNCERTAINTY [get_clocks core_clk]
set_clock_uncertainty -hold $HOLD_UNCERTAINTY [get_clocks core_clk]
set_clock_transition $CLOCK_TRANSITION [get_clocks core_clk]
set inputs [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay -min $INPUT_DELAY_MIN -clock core_clk $inputs
set_input_delay -max $INPUT_DELAY_MAX -clock core_clk $inputs
set_output_delay -min $OUTPUT_DELAY_MIN -clock core_clk [all_outputs]
set_output_delay -max $OUTPUT_DELAY_MAX -clock core_clk [all_outputs]
set_input_transition $INPUT_TRANSITION $inputs
set_load $OUTPUT_LOAD [all_outputs]
```

另建 `profile/dc-methodology.tcl`，指定 **同一個、library確實存在的 wire-load model**，關閉自動隨面積換模型：

```tcl
set_app_var auto_wire_load_selection false
set_wire_load_mode top
set_wire_load_model -name FILL_LIBRARY_WIRE_LOAD_MODEL
```

先用已驗證 adder環境／DC中的 `help`、`man`、library報告確認單位、可用 wire-load與上述命令。若 library沒有可用模型，先停在 pilot，帶回報告討論共同 interconnect估計；不要默默用不同預設模型或宣稱已做 post-layout分析。

本手冊維持既有範本的 `compile`，不混用 `compile_ultra` 或不同 effort。記錄工具版本、啟動環境、相關 setup檔的 hash，以及所有實際設定。先用 N4 FCFS檢查流程，必要時加 N16 Main評估候選時脈；先前 adder的5ns並非正式 target。最後把 library/PVT、clock/uncertainty、I/O、transition/load、wire-load、compile設定、報表命令寫進 `profile/PROFILE.txt`，標明 `FROZEN`和日期。profile若改動，先前 pilot只算 pilot；正式九組必須全部用凍結版本重新跑。

## 4. 補上手動 DC parameter selection

舊 `scripts/remote_eda.py`／`syn/dc.tcl` 沒有九組參數切換；**不要只改資料夾名字後跑九次預設 FCFS N4**。此處採手動工作副本，不修改已驗收 RTL，也不宣稱舊遠端 runner已支援 sweep。

先建立唯一的 DC範本副本：

```bash
export CXL_DC_TEMPLATE="$CXL_TRANSFER_ROOT/dc-manual.tcl"
cp "$CXL_SOURCE_ROOT/syn/dc.tcl" "$CXL_DC_TEMPLATE"
```

用文字編輯器打開 `dc-manual.tcl`，找到：

```tcl
    elaborate $TOP_MODULE
    current_design $TOP_MODULE
```

替換為：

```tcl
    if {![elaborate $TOP_MODULE -parameters $ELAB_PARAMETERS]} {
        error "Parameterized elaboration failed"
    }
    set actual_top [get_object_name [current_design]]
    if {$actual_top ne $TOP_MODULE} {rename_design $actual_top $TOP_MODULE}
    current_design $TOP_MODULE
    redirect reports/elaboration.rpt {report_design}
    redirect reports/ports.rpt {report_port -verbose}
```

這會顯式選參數，並把可能帶 parameter suffix的 elaborated top統一命名為 `switch_top`，以配合既有 PT腳本。請在當地 W-2024.09 用 `help elaborate`、`help current_design`、`help rename_design` 確認版本語法；任何錯誤都保留 log，不可改回預設參數掩蓋問題。`elaborate -parameters` 的依據是 Synopsys原廠[HDL Compiler reference manual](https://book.huihoo.com/pdf/crafting-a-chip-a-practical-guide-to-the-uofu-vlsi-cad-flow/synopsys/hdlcv_10.pdf)的 command interface；這份舊版文件不能替代當地2024工具驗證。

## 5. 跑一組 pilot，再跑九組

將下面整段貼進同一個 Bash終端，定義 `run_cxl_case`。它每次建立新目錄、保存參數及 profile hash，使用同一份完整 RTL清單、DC範本與 PT範本。路徑使用一般 Linux檔名，避免含 `{`、`}` 或換行。

```bash
run_cxl_case() (
  set -euo pipefail
  policy="$1"
  n="$2"
  label="$3"
  case "$policy:$n" in
    0:4|0:8|0:16|1:4|1:8|1:16|2:4|2:8|2:16) ;;
    *) echo 'Expected POLICY 0/1/2 and N 4/8/16' >&2; exit 2 ;;
  esac
  case_root="$CXL_RUN_ROOT/$label"
  mkdir "$case_root"
  trap 'rc=$?; printf "%s\n" "$rc" > "$case_root/exit-code.txt"; exit "$rc"' EXIT
  mkdir "$case_root/syn" "$case_root/sta" "$case_root/reports" "$case_root/output"
  (cd "$CXL_SOURCE_ROOT"; sha256sum -c FILE_SHA256SUMS) > "$case_root/source-verification.log"
  cp "$CXL_DC_TEMPLATE" "$case_root/syn/dc.tcl"
  cp "$CXL_SOURCE_ROOT/sta/pt.tcl" "$case_root/sta/pt.tcl"
  cp "$CXL_SOURCE_ROOT/SOURCE_REVISION.txt" "$case_root/SOURCE_REVISION.txt"
  printf 'POLICY=%s\nN_SRC=%s\nRR_QUANTUM=10\nFAI_W=5000000\nD=16\nM=1\nDESC_W=105\n' "$policy" "$n" > "$case_root/parameters.txt"
  sha256sum "$CXL_TARGET_LIBRARY" "$CXL_PROFILE_ROOT/common.sdc" "$CXL_PROFILE_ROOT/dc-methodology.tcl" "$CXL_DC_TEMPLATE" "$CXL_SOURCE_ROOT/sta/pt.tcl" > "$case_root/profile-sha256.txt"
  cat > "$case_root/run_config.tcl" <<EOF
set TOP_MODULE switch_top
set ELAB_PARAMETERS {N_SRC=$n,POLICY=$policy,RR_QUANTUM=10,FAI_W=5000000}
set TARGET_LIBRARY {$CXL_TARGET_LIBRARY}
set RTL_FILES [list \
 {$CXL_SOURCE_ROOT/rtl/include/cxl_sched_pkg.sv} \
 {$CXL_SOURCE_ROOT/rtl/common/cxl_desc_fifo.sv} \
 {$CXL_SOURCE_ROOT/rtl/common/cxl_out_hold.sv} \
 {$CXL_SOURCE_ROOT/rtl/common/cxl_fcfs_sel.sv} \
 {$CXL_SOURCE_ROOT/rtl/common/cxl_fai_main_sched.sv} \
 {$CXL_SOURCE_ROOT/rtl/common/cxl_rr_sched.sv} \
 {$CXL_SOURCE_ROOT/rtl/top/switch_top.sv}]
set CONSTRAINT_FILES [list {$CXL_PROFILE_ROOT/common.sdc} {$CXL_PROFILE_ROOT/dc-methodology.tcl}]
set STA_NETLIST_FILES [list {$case_root/output/switch_top.syn.v}]
set STA_CONSTRAINT_FILES [list {$case_root/output/switch_top.syn.sdc}]
EOF
  cd "$case_root"
  set +e
  dc_shell -f syn/dc.tcl 2>&1 | tee reports/dc.log
  dc_rc=("${PIPESTATUS[@]}")
  set -e
  printf 'dc_shell=%s\ntee=%s\n' "${dc_rc[@]}" > reports/dc-exit.txt
  test "${dc_rc[0]}" -eq 0
  test "${dc_rc[1]}" -eq 0
  grep -Fxq 'STATUS: SUCCESS' reports/run_status.rpt
  if grep -Eq '(^|[[:space:]])(Error:|Fatal:|EDA_FAILURE:)' reports/dc.log; then exit 3; fi
  test -s output/switch_top.syn.v
  test -s output/switch_top.syn.sdc
  mv reports/run_status.rpt reports/dc_status.rpt
  set +e
  pt_shell -f sta/pt.tcl 2>&1 | tee reports/pt.log
  pt_rc=("${PIPESTATUS[@]}")
  set -e
  printf 'pt_shell=%s\ntee=%s\n' "${pt_rc[@]}" > reports/pt-exit.txt
  test "${pt_rc[0]}" -eq 0
  test "${pt_rc[1]}" -eq 0
  grep -Fxq 'STATUS: SUCCESS' reports/run_status.rpt
  if grep -Eq '(^|[[:space:]])(Error:|Fatal:|EDA_FAILURE:)' reports/pt.log; then exit 3; fi
  mv reports/run_status.rpt reports/pt_status.rpt
  echo 'COMMANDS_COMPLETED_REVIEW_REQUIRED' > execution-status.txt
)
```

先跑 pilot；若重跑，換新 label，避免覆寫：

```bash
set -euo pipefail
run_cxl_case 0 4 pilot_fcfs_n4_v1
```

先檢查下一節的報告。**DC/PT exit0和 completion marker只代表命令完成，不代表 timing closure或 PPA驗收**。profile、DC範本或 source有修正就另留版本／hash，再跑 pilot。不要將 `FILL_ME` 或未核對的 wire-load留在正式設定。

profile已凍結且 pilot沒有未解釋的 link／timing-coverage問題後，才執行：

```bash
set -euo pipefail
test -s "$CXL_PROFILE_ROOT/PROFILE.txt"
grep -Fxq 'FROZEN' "$CXL_PROFILE_ROOT/PROFILE.txt"
sha256sum "$CXL_TARGET_LIBRARY" "$CXL_PROFILE_ROOT/common.sdc" "$CXL_PROFILE_ROOT/dc-methodology.tcl" "$CXL_PROFILE_ROOT/PROFILE.txt" "$CXL_DC_TEMPLATE" "$CXL_SOURCE_ROOT/sta/pt.tcl" > "$CXL_RUN_ROOT/frozen-profile.sha256"
for policy in 0 1 2; do
  for n in 4 8 16; do
    sha256sum -c "$CXL_RUN_ROOT/frozen-profile.sha256"
    run_cxl_case "$policy" "$n" "main_p${policy}_n${n}"
  done
done
```

| POLICY | 政策 | N |
| --- | --- | --- |
| 0 | FCFS | 4、8、16 |
| 1 | RR，quantum10 | 4、8、16 |
| 2 | FAI-inspired Main，W5,000,000 | 4、8、16 |

不要跑 POLICY3、W64/256、RR1當主要 PPA，亦不要移除 FIFO、reset邏輯或 metadata，或為單一 policy換 pipeline／bypass／compile設定。

## 6. 你可以驗收什麼

| 檢查 | 看哪裡／通過條件 |
| --- | --- |
| 真的是不同 N／policy | `parameters.txt`、DC elaboration log、`elaboration.rpt`、`ports.rpt`；N4/8/16 的 i_in_desc為420/840/1680 bits、valid/ready為4/8/16 bits。policy hierarchy須對應 FCFS／RR／Main；不能只看資料夾名稱。 |
| source／共同條件相同 | `SOURCE_REVISION.txt`、FILE_SHA256SUMS、九份 profile-sha256、凍結 profile；除 N／policy與必要 metadata外，條件一致。 |
| 無缺 library／未解決 module | DC/PT log與 `check_design.rpt`／`check_timing.rpt`；無 unresolved references、blackbox或無法解釋的 missing timing arc。RR沒有 timestamp；FCFS/Main有需要的 arrival storage。 |
| 面積 | DC `area.rpt`、`qor.rpt`：完整 switch的 cell area及 hierarchical breakdown。保留 FIFO和 metadata；不要把總面積差直接當成純 scheduler cell面積，亦不可把父子階層重複加總。 |
| 時序 | PT `timing_max.rpt`、`timing_min.rpt`、`constraints.rpt`、`check_timing.rpt`、`coverage.rpt`；記錄 setup/hold slack、unconstrained/untested原因，不可只看一條正 slack路徑。clock目標不等於實際最大頻率。 |
| 是否只有 pre-layout | 沒有 P&R／SPEF，本流程是共同 wire-load假設下的 pre-layout比較，不能稱為 post-route signoff。 |
| 功耗 | 既有範本不產生 activity-annotated power；先標 `NOT_RUN`。若有 power license，再設計三政策相同 intended traffic／ready traces、記錄 actual acceptance差異的活動註記流程。沒有活動證據的 vectorless數字不可當成真實 workload功耗。 |

請勿因警告數很多而整批忽略。若只是 Verilator通過但 DC不接受某種 SV／array／elaboration語法，先把完整 error與來源行數帶回，不自行改架構或放寬驗證。

## 7. 帶回什麼

第一次做完 pilot就可先帶回 `preflight.log`、source revision、`parameters.txt`、profile設定／hash、`exit-code.txt`、兩份工具 log、`reports/*-exit.txt` 與 `reports/*.rpt`。正式九組完成後，逐組再加 `execution-status.txt`、`run_config.tcl`、`source-verification.log`、`output/switch_top.syn.v` 與 `output/switch_top.syn.sdc`。

只打包上述自己的設定／結果；不要打包整個 home、`work/`、university library、license或工具安裝目錄。若需要結果表，每組保留：policy、N、來源commit、library/PVT/hash、profile hash、DC/PT版本、總cell area、setup/hold slack、coverage／未約束項目與功耗狀態。任何 failed／missing run都標明，不湊成9/9 PASS。

將這些結果交回後，Codex可先做一致性／coverage／方法審查，再決定是否能接受主要九組結果；之後才接 Algorithm-2 N4補充比較。目前沒有任何 scheduler synthesis、STA或power數字可引用。
