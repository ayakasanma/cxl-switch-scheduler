# 九組 FastX DC/PT 量測結果 —2026-10-20

狀態：**9/9 實驗指令完成並經獨立核對；時序以各組實際slack判定，電氣規則仍為 OPEN，未接受為 signoff。** 功耗未執行。此報告只記錄實際執行，未修改 Scheduler RTL、模型、Testbench 或 frozen Spec。**Setup8/9 MET、hold9/9 MET；FAI Main N16有32個setup違規，最差−0.870709ns。FCFS N16僅+0.000811ns（約0.81ps），不能視為穩健收斂。**

來源：Spec v1.0 `1af80967bbc2fb83224f4725c4fb450889e69c62`；功能驗收 RTL `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`；本次共同 flow/量測來源 `081f8a219911909bda8472ae4b257d3e6ed3122d`。九個 bundle 均由該乾淨提交匯出，所有 RTL、flow、參數與來源 manifest 已檢查。

共同 profile canonical SHA256：`6baba481319955c0a0425e7fb50a20eed3c8c1a224f2a90ee86a60afd92783af`。Library SHA256：`844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`。完整獨立 audit JSON SHA256：`14f28f9c83126fbc376885c3077b8a445b6d4e44d1ff1ee826cb700a08dda23d`。可機讀的摘要、來源hash與九組數字見 [results JSON](ppa/primary-20261020-v1.json)。

## 共同條件

實際 FastX Design Compiler/PrimeTime W-2024.09，SAED32 RVT `tt0p78v25c`（0.78V/25C）。N=4/8/16，D=16，M=1，完整105-bit descriptor，RR quantum10、FAI W=5,000,000。完整 switch 包括 FIFO、arrival metadata、hold controller 與 policy state；無 SRAM macro、blackbox 或政策專用 pipeline。

時脈25ns；setup/hold uncertainty0.1/0.05ns；input/output min/max delay0/2ns；input/clock transition0.1ns；output load2.656828fF（實測 reference inverter 輸入電容的FO4）。固定 ForQA/top wire-load estimate，DC auto selection 關閉，`compile -map_effort medium`、DC單核心。同步 reset 正常計時，沒有 false/multicycle/case-analysis exceptions。

面積單位為 library area units，未另宣稱物理面積單位。Cell area 排除獨立列出的 net-estimated area。這是典型 corner、ideal clock、pre-layout QA wire-load 的共同量測；不代表佈局後寄生、CTS、多 corner signoff 或 Fmax。完整設定見 [frozen profile](../syn/profiles/saed32-rvt-tt-25ns-forqa-v1.json)。

## 總體硬體與 STA

| N | Policy | Total cell area | Combinational | Sequential area | FF cells | PT worst setup ns | PT worst hold ns | Timing |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | FCFS | 103009.394 | 44474.946 | 58534.448 | 8856 | +9.860374 | +0.049066 | MET |
| 4 | RR10 | 78521.603 | 33706.865 | 44814.738 | 6782 | +20.523260 | +0.103864 | MET |
| 4 | FAI Main | 108913.413 | 49353.748 | 59559.665 | 9011 | +7.318300 | +0.050358 | MET |
| 8 | FCFS | 206479.551 | 89672.423 | 116807.128 | 17677 | +3.763228 | +0.103860 | MET |
| 8 | RR10 | 157209.161 | 67634.072 | 89575.089 | 13556 | +19.612915 | +0.080139 | MET |
| 8 | FAI Main | 217096.925 | 98604.314 | 118492.611 | 17932 | +0.930581 | +0.103860 | MET |
| 16 | FCFS | 411575.288 | 178200.945 | 233374.343 | 35318 | +0.000811 | +0.103860 | MET |
| 16 | RR10 | 314506.002 | 135421.902 | 179084.100 | 27102 | +18.758562 | +0.103860 | MET |
| 16 | FAI Main | 436249.875 | 199858.842 | 236391.033 | 35773 | -0.870709 | +0.079660 | NOT_MET |

每組皆核對：cell area = combinational + noncombinational（macro area0）；無 latch。QOR leaf cell count 與輸出 mapped netlist 的階層展開計數相符，逐一 reference 的數量×報告單元面積也核對總面積（允許報告6位小數的四捨五入）。`report_area` aggregate Number of cells 與 mapped-leaf 計數分開記錄，不假定其等於 QOR leaf+hierarchy。RR netlist 另外確認沒有 timestamp bank/counter；FCFS/Main 保留必要 arrival metadata。

| N | Policy | PT worst setup startpoint | Endpoint |
| ---: | --- | --- | --- |
| 4 | FCFS | `gen_fifo_1__u_fifo/rd_ptr_q_reg_0_` | `o_out_desc[76]` |
| 4 | RR10 | `rst_n` | `o_in_ready[3]` |
| 4 | FAI Main | `gen_fifo_1__u_fifo/rd_ptr_q_reg_0_` | `gen_policy_fai_main_u_fai_sched/cls_q_reg_3__1_` |
| 8 | FCFS | `gen_fifo_1__u_fifo/rd_ptr_q_reg_1_` | `o_out_desc[76]` |
| 8 | RR10 | `gen_policy_rr_u_rr_sched/ptr_q_reg_0_` | `o_out_desc[76]` |
| 8 | FAI Main | `gen_fifo_5__u_fifo/rd_ptr_q_reg_1_` | `gen_policy_fai_main_u_fai_sched/cls_q_reg_2__1_` |
| 16 | FCFS | `gen_fifo_5__u_fifo/rd_ptr_q_reg_0_` | `o_out_desc[103]` |
| 16 | RR10 | `gen_policy_rr_u_rr_sched/ptr_q_reg_0_` | `o_out_desc[79]` |
| 16 | FAI Main | `gen_fifo_9__u_fifo/rd_ptr_q_reg_1_` | `gen_policy_fai_main_u_fai_sched/cls_q_reg_13__1_` |

路徑含所有 normally timed synchronous reset/ready/descriptor/classification，未為 parallel FAI 更新額外給予 multicycle。讀取最差 slack 時必須同時辨識 path group 與 I/O delays；不能直接把25ns減去slack冒稱支援的Fmax。

## 硬體分項與比較

| N | Policy | FIFO subtrees含metadata | Policy subtree | Common hold | Top logic/arrival helpers | Switch額外面積相對RR |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | FCFS | 100974.463 | 887.471 | 809.449 | 338.012 | 24487.791 (31.19%) |
| 4 | RR10 | 77442.761 | 261.768 | 808.940 | 8.133 | 0.000 (0.00%) |
| 4 | FAI Main | 100971.413 | 6739.136 | 856.719 | 346.144 | 30391.811 (38.71%) |
| 8 | FCFS | 202057.445 | 2196.058 | 1799.340 | 426.708 | 49270.390 (31.34%) |
| 8 | RR10 | 154886.793 | 507.526 | 1798.577 | 16.265 | 0.000 (0.00%) |
| 8 | FAI Main | 202056.175 | 12752.946 | 1844.831 | 442.973 | 59887.764 (38.09%) |
| 16 | FCFS | 402755.983 | 4964.195 | 3376.811 | 478.299 | 97069.286 (30.86%) |
| 16 | RR10 | 309747.155 | 1249.626 | 3476.690 | 32.530 | 0.000 (0.00%) |
| 16 | FAI Main | 403749.178 | 28682.692 | 3310.226 | 507.780 | 121743.873 (38.71%) |

各分項只加總直接 subtree 與 top-local logic，沒有重複加總 parent/child。Policy subtree 不含 FIFO 內的 timestamp storage；「相對RR額外面積」是完整 switch 差值，包含必要 metadata 與同一套 compile 對各組的 mapping 差異，不能誤稱純 selector 邏輯成本。共用 RTL 相同不要求 mapped gate/size 在不同 policy context 下完全相同。

## 尚未關閉的電氣規則與 coverage

| N | Policy | DC slew nets | DC cap nets | PT cap pins | PT slew pins | PT timing checks violated | Untested checks |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | FCFS | 31 | 0 | 1118 | 31 | 0 | 64 |
| 4 | RR10 | 0 | 0 | 1067 | 0 | 0 | 0 |
| 4 | FAI Main | 32 | 0 | 1077 | 32 | 0 | 68 |
| 8 | FCFS | 0 | 0 | 2069 | 0 | 0 | 4 |
| 8 | RR10 | 0 | 0 | 2119 | 0 | 0 | 0 |
| 8 | FAI Main | 0 | 0 | 2058 | 0 | 0 | 4 |
| 16 | FCFS | 0 | 0 | 4423 | 0 | 0 | 0 |
| 16 | RR10 | 0 | 0 | 4260 | 0 | 0 | 0 |
| 16 | FAI Main | 4 | 0 | 4200 | 4 | 32 | 0 |

Main N16的32項timing違規均為setup；coverage共143344項，143312 met、32 violated、0 untested。Timing report最差−0.870709ns，constraint report記錄−0.870720ns，保留各報告原有精度。先前20ns pilot是不同mapping run，不能用其結果取代這次25ns失敗。

DC 與 PT 的 capacitance violation 數量有差異，兩者原始報告均保留，未以 DC 零違規取代 PT 結果。Capacitance/slew 是 OPEN finding，不能以正 setup/hold slack 當成全面收斂，也未放寬 library 限制或偷偷加入 timing exceptions。實際 incremental-only-design-rule pilot 沒有消除初始 slew 違規；後續若修正流程，需共同更新並重跑全部九組，不得只調整某個 policy。

- N4 FCFS：constant_disabled=64；完整原因見各組 `pt_coverage_untested.rpt` 與 `pt_disable_timing.rpt`。
- N4 FAI Main：constant_disabled=68；完整原因見各組 `pt_coverage_untested.rpt` 與 `pt_disable_timing.rpt`。
- N8 FCFS：constant_disabled=4；完整原因見各組 `pt_coverage_untested.rpt` 與 `pt_disable_timing.rpt`。
- N8 FAI Main：constant_disabled=4；完整原因見各組 `pt_coverage_untested.rpt` 與 `pt_disable_timing.rpt`。

Untested 的具體 pin/reason 需與 constant-disabled arcs 一起閱讀；不以四捨五入100%冒充全部檢查執行。

## 實際驗證、來源與限制

九組的 module/tool/library/profile/configuration、batch exit0、完成標記、必要報告、Error/Fatal/diagnostics 掃描與 source/result SHA256 均核對。所有 case 使用同一份 RTL 與 profile，沒有政策專用的 constraint/effort/path exception。

原有功能驗收180/180與 Main production-window 測試仍有效；本次未修改 RTL，也沒有將36個 runner infrastructure tests 冒充新的 scheduler 功能 coverage。Windows/WSL 各28PASS/8平台相關略過，獨立集合核對確認36項均至少在其中一個環境實際執行。原始失敗、修正、版本查詢 rc1、echo 誤判及 PT 報告 filter 修正均保留於 [執行紀錄](PPA_EXECUTION_2026-10-20.md)。

Power = NOT_RUN：未進行 workload SAIF/VCD activity annotation、coverage 與所需 power capability/license 驗證；沒有 vectorless 替代數字。Formality/商用等價、物理實作、多corner、Algorithm-2仍未執行。短 primary 功能 trace 未到 production window，不能用這組硬體面積推論已量得 FAI 適應性收益。

## 警告與審查來源

原始 log保留 SDC-2（SDC2.1由2.2 reader讀取）、PTE-003（constant-disabled arcs）、TIM-134（高fanout估算使用1000）、VER-941（parameter guard診斷字串）、VER-318（常數source ID型別轉換）、DDB-24、UCN-4，以及各組適用的constant-connection/unconnected DW carry等訊息。已核對輸出的clock/I/O/reset設定與實際path timing，不宣稱「無警告」；尤其高fanout/QA wireload限制應與area/STA結果一起閱讀。沒有因警告而悄悄改變架構或關閉檢查。詳細分類見 [methodology review](../reviews/phase-5-verify/FastX-PPA-methodology-review.md)。

Native RTL Agent Team實際以Opus5.5/high完成runner與三輪修正；另一個native synthesis-reviewer遇到實際HTTP429/session limit、CLI exit1且未寫成報告。依owner2026-10-20授權，審查改由GPT6.1 Sol/high完成；沒有把未完成的Claude任務冒充完成。Owner同時改定未來Opus呼叫使用medium，本次已啟動的high任務未重啟。Codex另做來源/hash/結果/面積核對，原始delegate logs/diffs與fallback provenance都保留。

## 自行驗收

1. 檢查 `syn/profiles/saed32-rvt-tt-25ns-forqa-v1.json` 與各 case 的 profile/manifest 雜湊一致。
2. 開啟下列各組原始 area、timing、constraints 與 coverage；正 slack 與 OPEN DRC 必須同時閱讀。
3. 核對 `RESULT_SHA256SUMS` 與 `download-manifest.json`，並在 Git 檢查 RTL/Spec 未被本階段改寫。

- N4 FCFS：[area](../artifacts/fastx/primary-20261020-v1-fcfs-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fcfs-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fcfs-n4/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fcfs-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fcfs-n4/reports/pt_coverage_untested.rpt)。
- N4 RR10：[area](../artifacts/fastx/primary-20261020-v1-rr-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-rr-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-rr-n4/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-rr-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-rr-n4/reports/pt_coverage_untested.rpt)。
- N4 FAI Main：[area](../artifacts/fastx/primary-20261020-v1-fai-main-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fai-main-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fai-main-n4/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fai-main-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fai-main-n4/reports/pt_coverage_untested.rpt)。
- N8 FCFS：[area](../artifacts/fastx/primary-20261020-v1-fcfs-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fcfs-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fcfs-n8/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fcfs-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fcfs-n8/reports/pt_coverage_untested.rpt)。
- N8 RR10：[area](../artifacts/fastx/primary-20261020-v1-rr-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-rr-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-rr-n8/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-rr-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-rr-n8/reports/pt_coverage_untested.rpt)。
- N8 FAI Main：[area](../artifacts/fastx/primary-20261020-v1-fai-main-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fai-main-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fai-main-n8/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fai-main-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fai-main-n8/reports/pt_coverage_untested.rpt)。
- N16 FCFS：[area](../artifacts/fastx/primary-20261020-v1-fcfs-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fcfs-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fcfs-n16/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fcfs-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fcfs-n16/reports/pt_coverage_untested.rpt)。
- N16 RR10：[area](../artifacts/fastx/primary-20261020-v1-rr-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-rr-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-rr-n16/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-rr-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-rr-n16/reports/pt_coverage_untested.rpt)。
- N16 FAI Main：[area](../artifacts/fastx/primary-20261020-v1-fai-main-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261020-v1-fai-main-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261020-v1-fai-main-n16/reports/pt_timing_min.rpt)、[DRC](../artifacts/fastx/primary-20261020-v1-fai-main-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261020-v1-fai-main-n16/reports/pt_coverage_untested.rpt)。

原始 evidence 位於本機 ignored `artifacts/fastx/primary-20261020-v1-*/` 與 FastX `~/cxl/experiments/` 對應新子目錄；沒有下載 `.db/.lib`、license 或 proprietary executables。Git保存流程、frozen profile與摘要，raw logs/netlists/SDCs/result hashes 保存在本機與遠端。

後續[收斂診斷與實際high-effort pilot](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md)保留為另一份執行紀錄：三個抽查pin的DC/PT差異已定位到receiver-load計算值，FCFS N4 high-effort未改善結果。原始九組數字、profile與OPEN狀態不變，沒有用pilot取代失敗組合。

再後續的cap075 FCFS N4 pilot已實際達到原始library限制下PT電容/slew0/0，setup+9.881229ns、hold+0.033790ns，面積103730.908806（約+0.70%）；390暫時限制已還原。原始FCFS4全部1118違規的load差異已完成逐pin核對，新映射全27231driver也有原始定義限制且0CCS cap違規。這是另一個PILOTprofile的單組結果；Main16及九組整體OPEN狀態不變，詳見同份診斷的實際cap075結果。

相同cap075 profile的Main N16 pilot也已完成：電容/slew0/0，但仍有32setup違規、最差−0.907946ns，hold+0.085328ns，面積437228.837383（約+0.2244%）。原始九組表格不以新pilot替換；候選仍PILOT，不宣稱完整時序收斂，詳見診斷的Main16結果。
