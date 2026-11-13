# P1 執行紀錄（2026-11-06）

這一輪做了三件事：把 20-seed 確認結果寫進報告正文、啟動 under/over 配對、檢查 drain 定向錨點
可行性。第三項撞到凍結 harness 的既有斷言，需要新協定才能繼續，先停在這裡。

## 1. 報告正文

新增 `docs/final-report/main-v4.tex` 與 `sections/hotnets-body-v4.tex`，內容是 v3 加上
`Dynamic Workload Confirmation` 小節。v3 的 tex 與 PDF 都沒有動（PDF 仍是
`27c51bb6…`）。v4 建兩次，15 頁、0 undefined reference、0 overfull hbox，PDF 是
`5db23f55…`。驗收：`docs/reviews/report-v4-acceptance-20261106.json`。

正文寫的是：三個對比全部通過、P1 與 P2 的區間零寬是端點性質、統計維持 `MODEL_ONLY`、
RTL 錨點仍只有 A3 與 A4、C7 不動。

## 2. under／over 配對

新 runner `scripts/run_capacity_absorption.py`：每個 (profile, seed) 跑 6 個 job
（3 政策 × 2 lane），端點是 Heavy 完工時間差（mixed − isolated）與比值，逐 job 檢查
`fired == accepted == sum(generated)`。

**需要你裁定的一點**：heavy 工作量必須依負載縮放。`under` 的 heavy 生成機率是 0.25，
17.5M 筆需要約 70M cycles，遠超過 24M 的 active 上限，job 會直接 FAIL。目前用

| profile | heavy_p | heavy 筆數 | 完成所需 cycles |
| --- | --- | --- | --- |
| under | 0.25 | 4,000,000 | 約 16M |
| over | 1.00 | 17,500,000 | 約 17.5M |

W256 冒煙（seed 8101，三個 profile）全部 PASS，守恆成立，方向也對：under 差 0、
near 差 8、over 差 201–204 cycles。這個縮放改動了 C5 原本的工作量定義，所以結果只能算
「同方向的獨立重現」，不能直接說是把 C5 升級成 RTL。

W5M 正式跑已啟動：5 個 seed（8101–8105）× 2 個 profile × 6 job = 60 個 job、6 個 worker，
log 在 `.setup-logs/implementation/p1-under-over-20261106/under-over.log`。

## 3. drain 定向錨點：卡住，需要新協定

想法是把 cut 放在 heavy 還沒生成完的時候，讓清理路徑面對長 backlog。實測
（`artifacts/implementation/cgof-rtl-diagnosis/20261106T024943Z_3488`，W256、
`--max-active-cycles 850`、heavy 896）兩個 job 都 FAIL，log 裡的斷言是：

```
assert False + where False = <DiagnosisTraffic>.heavy_complete
```

也就是說凍結的 harness 在進入 drain 之前就要求 heavy 生成完畢，**不允許提前切**。
因此「定向長 backlog drain」在現行協定下做不出來，只有 A3 那個自然出現的 2-cycle drain
可以引用。要繼續只有兩條路：

1. 新增一個允許「未完成 heavy 就切」的 harness 模式（改 `cgof_diagnosis_traffic.py` 與
   相關測試，重新凍結來源與驗收）——這是新協定，需要你同意。
2. 放棄定向測試，報告維持「自然 drain 一次、定向未做」。

在沒有裁決前我不動 harness。

## 4. latency_recovery

定義已經寫在 `p1-experiment-designs-20261104.md`（角色切換後到 Sparse P99 回到 ±1 cycle
穩態帶的 cycle 數，滑動窗 5,000）。目前缺的是量測管線：現有 runner 只輸出整段 P99，
沒有逐窗時間序列，所以要先加一個「逐窗 P99 序列」輸出。這同樣是改 runner，等 drain 的
裁決一起處理比較省事。

## 成本現況

- 已完成：報告 v4（0 機器小時）、under/over 冒煙（數秒）。
- 執行中：under/over 60 個 W5M job，6 worker，估計 4 小時。
- 未動用：drain RTL（3 job，約 3.6 小時）、latency_recovery（模型 8 小時起）。

