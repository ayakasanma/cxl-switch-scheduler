# P1 實驗設計（2026-11-04）

四個 P1 項目要跑什麼、多少成本、通過條件是什麼。這是設計稿，不是凍結協定；開跑前
要另立 freeze 收據並 pin 住 runner 與來源雜湊。

種子配置：P1 一律用 `8101`–`8105`。`7401`–`7420` 保留給確認組，`7301` 是工程 pilot，
`7291`／`9901` 永久排除。`8101`–`8105` 目前沒有被任何 artifact 引用。

## 4. under／over 配對

問題：容量吸收目前是 20-seed `MODEL_ONLY`（under 差 0.00 cycles、over 差 +834.25
cycles），只有 near 這一個點有 RTL 證據。

設計：每個 seed 每個 profile 6 個 job（3 政策 × 2 lane），兩個 profile 共 60 個 job，
W5M、4 視窗、heavy work 17,500,000、N4、D16。runner 尚未存在，需新增
`scripts/run_capacity_absorption.py`，直接複用 `cgof_diagnosis_model.run` 與
`run_rtl_diagnosis.make_job`，輸出格式沿用 pilot manifest。

端點：Heavy 完工時間差（mixed − isolated），逐 seed 配對。通過條件：under 的差落在
±20 cycles 內，over 的差為正且落在 +820…+850 cycles 桶，符號與量級和 C5 一致。

成本：60 個模型 job、7 個 process 約 5.4 h。RTL 錨點 20 個 job（每個 profile、每個
政策 2 個）約 18 h；`run_rtl_diagnosis.py --profile under|over` 已支援，不需改 RTL。

## 5. CGOF 閘級功耗

缺什麼：FCFS 3.356 mW、RR10 2.560 mW、Main 3.467 mW 都有 SAIF 功耗，CGOF 沒有，
所以面積論點完整、功耗論點空白。

步驟：用既有 activity harness 產生 3 個 seed × 兩個政策的 SAIF → PrimePower → 記錄
activity 檔與其 hash。另外把 `CGOF(1:1)` 網表裁掉沒被讀取的分類器暫存器（N4 138 個），
面積與功耗各給一組數字。

卡點：FastX 的 EDA 席位要人工登入，帳密不進 repo、不進文件。

## 6. latency_recovery 與 N8／N16

定義（本輪才第一次寫下）：角色切換後的 cycle 數，直到被切換進來的來源其 Sparse P99
回到穩態帶（±1 cycle）。滑動窗 5,000 cycles，量到穩定為止，上限 4M cycles。

量測：W5M、role-switch 案例、`Main` 與 `CGOF(2:1)`、seed `8101`–`8103`。N8／N16 用
multi-window 案例、5 個 seed，只跑模型（RTL 端目前只有 PPA 數據）。

成本：約 8 h model、20 h RTL。

## 7. drain 錨點

現況：A3 的 `depth8-bursty` mixed 錨點自然在 cut 時仍有佇列，drain 2 個 cycle，
`fired == accepted == 18,815,149`；同 job 的模型重播也是 `drain_cycles = 2`。其餘三個
錨點與 20 個 legacy 錨點都是空佇列收尾。

還缺定向測試：把 cut 放在 heavy backlog 內（`--max-active-cycles` 調到 heavy 尚未完成），
讓 drain 長到能檢查順序而不只是長度 1。成本：3 個 RTL job 約 6 h。

## 執行順序

1. under／over 模型配對（5.4 h，不碰到 RTL）
2. drain 定向錨點（6 h RTL）
3. latency_recovery 模型側（8 h）
4. under／over RTL 錨點（18 h）
5. 功耗（需 FastX，排在最後）

