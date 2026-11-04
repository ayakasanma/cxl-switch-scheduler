# v2 共用記帳、Main 接線與 A2 驗收

日期：2026-11-04。狀態：**E1／E2／G1／E3／E4／A2 PASS**。

Main 已接入既有 switch_experiment_top 的 POLICY=2，保留共同 FIFO、105-bit
descriptor、timestamp 與 held-grant 邊界；未修改任何 .sv。
run_rtl_diagnosis.py --policy main/all 可選 Main 或三政策，both 仍只選兩種
CGOF。Main 使用獨立 FaiMainSwitchModel oracle，每 cycle 檢查 pins、class、
B/S、window index 與 class-quota visit registers，並與 ExperimentalSwitchModel
mirror 比對。Main 不使用逐源 credit，classifier 的 credits 為 null。

DiagnosisAccounting 共用 cocotb 與純模型的產生、接收、送出、分類與 cleanup。
新增 physical_sources 帳本記錄 src0..src3 的 generated／accepted／fired、
cut pending、final censoring 與三段延遲分佈。epoch_W0..W3／W4-tail 依
generation cycle 計數，請求跨角色切換或 cut 後不重標；epoch 僅有計數。

## 驗證

| 範圍 | 結果 |
| --- | --- |
| G1：seed7291，五案例 × CGOF兩權重 × mixed/isolated | 20/20 legacy pairs 相等 |
| A2：seed7301，五案例 × 三政策 × mixed/isolated，W256 | 30/30 RTL／模型相等，含新帳本 |
| W64 角色切換，三政策 × mixed/isolated | 6/6 相等，含新帳本 |
| Main High-context grant stall 跨 B_H→L closing edge，W64/W256 × D8/D16 | 4/4；source／descriptor／context 保持，stall 不扣 quota、不計 service |
| strict lint：W64/W256/W5M 參數與 D8/D16 配置 | 15/15，無 warning waiver |
| 帳本／模型／traffic 單元測試 | 25 passed，18 subtests |
| 目前模型與重構前 W256 CGOF RTL | 20/20 legacy 相等；新欄位 NOT_AVAILABLE |

G1 由 Orca Worker designer（Claude Code，runtime claude/claude-opus-5-5、
effort high）執行，2026-11-03 10:56:51–11:59:54 UTC，wall 3,783 s。
每 job 內部 wall 1,108.03–1,348.68 s，合計 24,603.72 s。G1 三個 source
snapshots 與原記錄 hash 一致，20 個 RTL reference before／after hash 一致。
E3／E4／A2 由 Lead 直接執行（Codex）；A2 RTL run
20261103T181252Z_20159，40 個 cocotb tests（36 diagnosis＋4 directed）
全數通過，wall 215.224 s。最終 lint run 為 20261103T181748Z_1381。

[G1 驗收](dynamic-role-switch-v2-g1-acceptance-20261104.json)、
[實作驗收](dynamic-role-switch-v2-implementation-acceptance-20261104.json) 與
[execution source freeze](dynamic-role-switch-v2-a2-source-freeze-20261104.json)
記錄來源、參數、比對範圍與產物。v1 的 112 個來源逐項核對，僅授權變更的
run_rtl_diagnosis.py、test_cgof_diagnosis.py 不同，其餘 110 項一致。
v1 三個凍結文件、v2 原計畫／summary、RTL、獨立模型與歷史產物保持原 hash。

完整 logs：.setup-logs/implementation/dynamic-role-switch-v2-exec-20261104/
的 unit.log、a2.log、a2-lint.log、legacy-shortw.log、acceptance.log；
G1 原 logs 保留在 dynamic-role-switch-v2-exec-20261103/。

## 限制與後續

純模型仍為 MODEL_ONLY；RTL 證據限實際執行的輸入與欄位，C7 保持
SINGLE_SEED / SCHEDULER_RTL。RTL 錨點的 drain_cycles 仍全為 0，RTL 側
沒有 drain 證據；model 側的 pilot 已有 2 個 job（Main ready-bursty、
Main depth8-bursty mixed）出現 drain_cycles=2，cleanup 路徑實際執行過。
G1 的舊 W5M CGOF jobs 不能替新增帳本提供 W5M RTL 覆蓋。

## E5 分析與 seed 稽核

`scripts/analyze_dynamic_role_switch.py` 固定單一主終點（mixed、generation-time、
whole-run Sparse G→F nearest-rank P99）、三個對比、exact 單尾符號檢定、
Holm step-down 與 10,000 次 paired seed-block bootstrap（僅描述性）。
輸入必須是 20 個完整 seed blocks；重複、缺漏、混入 7291／7301／9901，
或非 MODEL_ONLY、非 W5M 四窗、drain≠0 的結果一律拒絕。
5 個單元測試（含 Holm 邊界 K=14／15／16 與 20/20）與合成 20-seed CLI
smoke 均通過，log：`.setup-logs/implementation/dynamic-role-switch-v2-exec-20261104/e5.log`。

pilot 執行器 `scripts/run_dynamic_role_switch_pilot.py` 只接受 seed 7301 與
W256／W5M，拒絕確認 seeds 與排除 seeds；W256 dry run 30/30 PASS。

下一階段為 seed7301 完整 W5M pilot：30 個 model jobs（執行中），加 A3 的 4 個
Main RTL jobs，預算約 6.3 h；新帳本速度與 Main RTL 成本待該輪量測。
尚未啟動 A3/A4、7401–7420 確認或 EDA；確認 seeds 未使用。
