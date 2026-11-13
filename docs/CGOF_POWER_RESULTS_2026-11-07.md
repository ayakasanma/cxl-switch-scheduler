# CGOF 功耗與定向長 backlog drain：2026-11-07 結果紀錄

## 驗收結論與證據性質

最終實驗驗收時間為 2026-11-07 13:12:44（Asia/Taipei），狀態 **ACCEPTED_AUTHORIZED_SCOPE**。CGOF(1:1) 與 CGOF(2:1) 各完成 seeds 509–511 × A/B，共 **12/12 captures**；其中既有 CGOF1/A/509 重用，其餘十一組補齊。FCFS、RR10、Main 的十八組既有 accepted baseline 重用，未重跑。

本頁整理已完成的 FastX gate-level replay／SAIF／PrimeTime 功耗估算及獨立 scheduler RTL drain；未啟動新量測。2026-11-07 15:35 的文件整理前只讀校驗，448 項 receipt bindings 與 448 項 SHA256SUMS entries 全部一致，exit 0。原件為 [最終父審](../artifacts/implementation/fastx-power-20261107/cohort-extension/final-acceptance.json)、[完整四項功耗與配對比較](../artifacts/implementation/fastx-power-20261107/cohort-extension/MATCHED_COMPARISON.md) 及 [機器可讀資料](../artifacts/implementation/fastx-power-20261107/cohort-extension/matched-comparison.json)。

## 固定比較條件

- N4、D16、full105、W=5,000,000；oldest-first，ELIGIBLE_RR=0，HIGH_WEIGHT=1/2 對應 CGOF1/CGOF2。
- 沿用 frozen mapped netlist、SDC、ForQA/top、SAED32 RVT TT、0.78 V、25 °C、25 ns clock。
- A：10,000,000 warmup + 100,000 measured cycles，SAIF 2,500,000 ns。
- B：10,101,024 warmup + 102,400 measured cycles，SAIF 2,560,000 ns。
- 只比較同 seed、同 arm、同外生 trace/profile/PVT/clock/window。A/B 分開，不合併成統計樣本；相同輸入 trace 不代表相同 admissions/fires，實際邊界 outstanding 保留於 JSON。
- 來源 revision 為 a3f4d8b1865c9af24eb86776274cc8c98428adc3；完整 source/package/library/model/profile hashes、工具版本、命令與 exits 由 [artifact-index.json](../artifacts/implementation/fastx-power-20261107/artifact-index.json) 連到各組 receipt。

## 十二組 CGOF 四項功耗

單位均為 mW；保留工具報表的 total，分項 rounding 後的和可能與 total 不同。

| Seed/arm | CGOF | Internal | Switching | Leakage | Total |
|---|---|---:|---:|---:|---:|
| 509/A | 1:1 | 1.328 | 0.01818 | 2.069 | 3.416 |
| 509/B | 1:1 | 1.328 | 0.01794 | 2.069 | 3.415 |
| 510/A | 1:1 | 1.328 | 0.01820 | 2.070 | 3.416 |
| 510/B | 1:1 | 1.328 | 0.01794 | 2.070 | 3.416 |
| 511/A | 1:1 | 1.328 | 0.01822 | 2.070 | 3.416 |
| 511/B | 1:1 | 1.328 | 0.01793 | 2.071 | 3.417 |
| 509/A | 2:1 | 1.331 | 0.01895 | 2.112 | 3.462 |
| 509/B | 2:1 | 1.331 | 0.01858 | 2.112 | 3.461 |
| 510/A | 2:1 | 1.331 | 0.01897 | 2.112 | 3.462 |
| 510/B | 2:1 | 1.331 | 0.01859 | 2.113 | 3.462 |
| 511/A | 2:1 | 1.331 | 0.01898 | 2.112 | 3.462 |
| 511/B | 2:1 | 1.331 | 0.01858 | 2.114 | 3.463 |

## 與既有 baseline 配對比較

下表 total 單位為 mW。

| Seed/arm | FCFS | RR10 | Main | CGOF 1:1 | CGOF 2:1 |
|---|---:|---:|---:|---:|---:|
| 509/A | 3.356 | 2.559 | 3.466 | 3.416 | 3.462 |
| 509/B | 3.355 | 2.559 | 3.465 | 3.415 | 3.461 |
| 510/A | 3.356 | 2.560 | 3.467 | 3.416 | 3.462 |
| 510/B | 3.356 | 2.560 | 3.466 | 3.416 | 3.462 |
| 511/A | 3.356 | 2.560 | 3.467 | 3.416 | 3.462 |
| 511/B | 3.357 | 2.561 | 3.467 | 3.417 | 3.463 |

各配對使用 (CGOF total / baseline total − 1) × 100%。以下是六個配對的觀察範圍，不是平均值、信賴區間或顯著性。

| CGOF | 相對 FCFS | 相對 RR10 | 相對 Main |
|---|---:|---:|---:|
| 1:1 | +1.7873～+1.7884% | +33.4244～+33.4896% | −1.4710～−1.4422% |
| 2:1 | +3.1576～+3.1595% | +35.2206～+35.2872% | −0.1442～−0.1154% |

白話解讀：在這些固定條件下，CGOF1 的 total 約 3.416 mW，較 Main 低約 1.45%；CGOF2 約 3.462 mW，與 Main 很接近。兩者都高於 FCFS 與 RR10，因此這批結果支持「補齊了功耗成本比較」，並不支持全面省電或普遍優於所有 baseline。CGOF2 相對 Main 的差異尤其小，須受報表精度與估算方法限制。

## Activity、warnings 與失敗歷史

CGOF1 net annotation 為 28,458/28,458，leaf 為 27,750/27,784；CGOF2 分別為 30,022/30,022、29,221/29,255。各有 34 個 literal D/SETB leaf 例外，已核對；全部 8,998/9,014 個 FF clocks 都是 clk/file activity。無 transient X/Z；20/56 個 constant-X records 均有結構上未使用的解釋。唯一 PTE-003 warning 對應 68 個 propagated constant arcs；check_power 無 load/ramp range issue。

新十一組的 replay/SAIF/PT、source/log/shell/local audits 與最終父審通過。VCS version probe exit 1 單獨保存。重用 CGOF1/A/509 的原 replay-audit/shell exit 1、修正後 local checker exit 0 與 PT-only continuation exit 0 全部保留；最終父審直接核對同份 capture，沒有重跑。原 coordinator PID 40540 的 exit 未知；單一 recovery coordinator 的 exit 為 0、stderr 0 bytes。失敗與 preparation NOT_RUN/中途 INCOMPLETE 紀錄維持原樣，最新整體狀態由 final-acceptance.json 決定。

## 定向長 backlog drain

沿用已驗收 run 20261106T230245Z_18888，engineering seed 7301，與功耗 cohort 分開。Main、CGOF1、CGOF2 皆從 reset/all-High 開始；sink 暫停 512 cycles，留下 producer backlog 859 筆及 FIFO 64 筆，再停止生成並恢復 ready。

| 檢查 | CGOF1 | CGOF2 | Main |
|---|---:|---:|---:|
| cutoff producer backlog | 859 | 859 | 859 |
| cutoff FIFO occupancy | 64 | 64 | 64 |
| 實際 drain cycles | 923 | 923 | 923 |
| generated = accepted = fired | 923 | 923 | 923 |
| 最終 outstanding | 0 | 0 | 0 |
| input-hold checks | 3706 | 3709 | 3740 |

held grant 維持 511 cycles，恢復 ready 後第一筆確實送出；逐週期 full105 scoreboard、獨立模型、hold 與逐 source conservation 均通過，最後保留兩個 quiescent cycles。原 9 個 pytest tests 加 3 個 cocotb tests 共十二個，無 failure/error/skip；三組 lint 與父審亦通過。證據為 [directed-drain parent acceptance](../artifacts/implementation/fastx-power-20261107/directed-drain/20261106T230245Z_18888/parent-acceptance.json)。

這證明此定向 fixture 的積壓能完整排空，未丟失或重複 descriptor；沒有 window close，不能推論 trained-class 演進、多視窗適應、一般公平性或系統延遲。

## 執行、角色與可重現性

既有 RTL/TB 與 drain 由 Claude Code、rtl-agent-team:testbench-dev、claude-opus-5-5、requested medium 實作；provider 內部 reasoning depth 未證實。既有統籌與父審紀錄為 Codex CLI、group/gpt-6.1-sol-2、high。本次只整理文件及只讀校驗，未委派代理、未發 EDA/模型執行請求。

歷史實際命令與 exit：

- drain：source scripts/wsl_env.sh && PYTHONDONTWRITEBYTECODE=1 timeout 2400 python scripts/run_directed_backlog_drain.py --execute --jobs 2；exit 0，各 lint/build/sim 子命令見該 run commands.txt。
- 最後一組父審：.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-B-s511；exit 0。
- 原批次封存：.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/finalize_cohort.py；exit 0。
- 本次文件核對：node .setup-logs/implementation/fastx-power-20261107/result-record/audit_record.mjs；exit 0。此命令只校驗 bytes/hash，不重跑實驗。

詳細歷程另見 [本輪 review](reviews/fastx-power-cohort-extension-20261107.md) 與 [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md)。原批次與續接已完成，排程已暫停；本次不重新啟動。

## 採用與仍未驗證的範圍

採用為本次固定 cohort 的 **pre-layout、zero-delay/no-SDF、平均 gate-level 功耗估算**，及獨立定向 RTL 排空證據。無 APR/SPEF、實體 clock tree、glitch 或實體晶片功耗量測；歷史 baseline vector bytes 本輪未重新雜湊。這次記錄不修改論文、不升級 hypothesis integration，不自動放行其他昂貴 campaign。
