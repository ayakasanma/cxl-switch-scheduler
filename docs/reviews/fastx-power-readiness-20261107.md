# FastX CGOF power readiness — 2026-11-07

CGOF1/A/509 已完成 production gate-level replay、SAIF 與 PrimeTime 功耗估算，
total 為 **3.416 mW**。完整 509–511／A–B／HIGH_WEIGHT=1、2 cohort 仍為
**INCOMPLETE（1/12 measured）**，長 backlog drain 為 **UNVERIFIED**。
單組量測與原始報表見 [direct pilot](fastx-power-direct-pilot-20261107.md)。

## 已完成的單組結果

| 項目 | 實際證據 |
|---|---|
| Configuration | CGOF1；N4、D16、105-bit、W=5,000,000、oldest-first、ELIGIBLE_RR=0 |
| Stimulus | seed 509、arm A；10,000,000 warmup + 100,000 measured cycles |
| VCS full64 compile / gate replay | exit 0 / 0；10,100,000 cycles，全 105-bit pin replay |
| SAIF | scope tb/dut；2,500,000 ns；39,912 records；transient X/Z=0 |
| PrimeTime power | continuation exit 0；W-2024.09，averaged power |
| Net activity annotation | 28,458 / 28,458；100.00% file activity |
| Fully annotated leaf cells | 27,750 / 27,784；99.88% |
| FF clock pins | 8,998 / 8,998；clk、file；0.0799996 transitions/ns |
| check_power | succeeded；load/ramp range issues=0 |
| Internal / switching / leakage / total | 1.328 / 0.01818 / 2.069 / 3.416 mW |

SAIF annotation 與 switching coverage 是不同指標；前者是活動來源覆蓋率，
後者只計算至少切換一次的 nets。此 case 的 toggled-net coverage 為 81.22%。
20 個 always-X records 對應未連接的 arithmetic carry/comparator outputs，
其 port direction 與 mapped topology 證據已保留。disabled timing arcs 的原始
report 亦保留，不能由 summary warning 推論全部 arc 的原因。

## 已凍結的比較條件

主人指定 seeds **509、510、511**，各自保留 A、B arms，CGOF1/CGOF2
的 HIGH_WEIGHT 分別為 1/2，對應 1:1/2:1。既有 FCFS/RR10/Main 十八個
accepted captures 為 matched baseline，不混用 8101–8105 或其他 cohort。

| 共同比較條件 | 凍結值 |
|---|---|
| PVT / clock / wire load | SAED32 RVT TT 0.78 V、25 °C；25 ns；ForQA/top、ideal clock |
| Profile SHA256 | 6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d |
| Baseline index SHA256 | 9d26aa70fa688c068311b70c20c9a2583eae4a9c63e7abba0a9355e3d895c61e |
| CGOF1 mapped bundle | cgof-ppa-dcpt-cgof1-n4-20261028 |
| CGOF2 mapped bundle | cgof-ppa-dcpt-20261028T0723 |
| Arm A warmup / measured | 10,000,000 / 100,000 cycles |
| Arm B warmup / measured | 10,101,024 / 102,400 cycles |

509/A 既有 baseline totals 為 FCFS 3.356、RR10 2.559、Main 3.466 mW；
CGOF1 為 3.416 mW。同 exogenous trace、profile 與 measurement window 下，
各政策實際 admissions、fires 和 outstanding work 仍保留各自數值。
Baseline 沒有重跑、重新驗收或重新讀取巨大 historical vector bytes。

## 實作、路由與驗證

只在 Host 建立的 sharp-bohr worktree 寫入；原 repository 保持只讀。
主模型負責 Python/Tcl、runner、遠端執行、證據整合與驗收。
Native Claude Code 2.1.318／RTL Agent Team 0.14.6 的
claude-opus-5-5、requested medium 是 testbench adapter 的唯一作者。
Preimplementation review 使用 agy gemini-4-argon-high、requested high。
完整命令、模型回執、來源與執行紀錄保存在 ignored logs 及 DEVELOPMENT_REPORT。

CGOF exporter 固定 cohort、source/package/profile bindings，匯出完整 pin trace，
以獨立 credit/FIFO/class ledger 逐 cycle 覆核。CGOF testbench 保留 baseline
guards，支援兩個 weights 與 A/B，無 preload、跳過 training 或輸出覆寫。
PrimeTime 分支使用相同 netlist、SDC、library/PVT 與 profile。

本機 integration 已有 80 passed / 0 skipped 的 Linux 證據；最近一次 Windows
checker regression 為 10 passed / 1 platform skip、exit 0。這些是不同執行紀錄，
不能相加或把 skip 當成通過。實際完整 replay/SAIF/power checker exit 0。

## 重現與證據

詳細命令、各階段 exit、package/library/profile/source hashes，以及單組報表
位於下列 worktree 相對路徑；完整 command receipts 保存了必要的機器絕對路徑。

- artifacts/implementation/fastx-power-20261107/artifact-index.json
- artifacts/implementation/fastx-power-20261107/cohort-freeze-final/cohort.json
- artifacts/implementation/fastx-power-20261107/matched-baseline-509A.json
- artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-semantic-review.json
- 同一 attempt 的 payload/execution/reports/replay.txt、payload/execution/activity.saif
- 同一 attempt 的 power-review/ 內 power、annotation、clock、units、check_power、disabled-arc reports
- .setup-logs/implementation/fastx-power-20261107/owner-direct-pilot/replay-budget-retry/
- .setup-logs/implementation/fastx-power-20261107/owner-direct-pilot/pt-continuation/

## Limitations

目前只有 CGOF1/A/509 的實際功耗；其餘十一個 CGOF captures 尚未執行或接受。
此為 pre-layout、zero-delay、no-SDF gate-level estimate，未包含 APR、SPEF、
實體 clock tree、glitch 或 silicon effects。完整 cohort、長 backlog drain、
系統級延遲與論文結果均未升級。其他 RTL/EDA 工作仍需各自的 source、harness、
functional/gate acceptance 與資源依賴，不自動放行其他 campaign。
