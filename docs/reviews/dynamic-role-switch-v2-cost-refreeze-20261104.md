# v2 cost re-freeze

日期：2026-11-04。狀態：**FROZEN_V2_COST_REV2**。

原 v2 成本表（`dynamic-role-switch-plan-v2-lean-20261103.md` §3）以每 job
0.347 h 估算，確認階段 600 個 model job 約 45 h。實際量測後，該數字建立在兩個
錯誤前提上：一是用 200k cycles 的 bench 外推，二是 runner 用 thread pool 啟動。
兩者都已修正，本文以修正後的量測重新凍結預算。

## 量測

| 項目 | 值 | 來源 |
| --- | ---: | --- |
| 單 process 完整記帳 | 16,785 cycles/s（0.362 h/job） | 300k cycles 量測 |
| 7 process 並行 | 13,547 cycles/s each（0.449 h/job） | 同上 |
| 10 process | 11,728 cycles/s（0.518 h/job） | 同上 |
| 15 process | 9,272 cycles/s（0.656 h/job） | 同上 |
| pilot 實跑 30 jobs、6 workers | wall 8,249.3 s（2.291 h），job 合計 48,508.8 s，單 job 最大 2,183.2 s | `evidence/pilot-manifest.json` |
| A3 四個 Main W5M RTL、jobs=2、與 6 個 model process 併行 | wall 15,328.4 s（4.26 h） | run `20261103T224623Z_714733` |
| A2 36 個 W256 RTL 加 4 個 directed、jobs=2 | wall 215.2 s | run `20261103T181252Z_20159` |
| G1 20 個 W5M 模型重播、7 個 subprocess | wall 3,783 s，單 job 1,108–1,349 s | run 2026-11-03T10:56–11:59Z |

過程式（process）啟動後，單 job 成本與凍結估計相差約 4%；thread 版本慢 6.5 倍，
該版本已停用。

## 預算

確認階段共 600 個 model job（20 seeds × 30），加 A4 兩個 Main W5M RTL 錨點。

| 項目 | 7 process | 15 process |
| --- | ---: | ---: |
| 600 model jobs 線性 wall | 86 批 × 0.449 = 38.6 h | 40 批 × 0.656 = 26.2 h |
| 加 20% 營運保留 | 46.3 h | 31.5 h |
| A4 兩個 RTL（jobs=2，一批） | 4.2 h | 4.2 h |
| 機器合計 | 50.5 h | 35.7 h |
| 人工：逐 seed 稽核 0.5 h × 20 + 彙總 | 18 h | 18 h |

pilot 與 A3 已花費的時間另計（pilot 2.29 h、A3 兩輪合計約 8.6 h）。

## 新的硬上限

| 限制 | 值 |
| --- | ---: |
| 單一 model job | 1.5 h |
| 單一 RTL job | 3 h |
| 單一 seed 的模擬 | 4 h |
| 模擬累積 | 60 h |
| campaign 含稽核與等待 | 80 h |
| 含前置工程 | 95 h |

超過任一上限即停止並另提修訂，不得提高並行度或縮減矩陣追進度。

## 未變的部分

矩陣（N4、W5M、四窗、heavy_work 17.5M、near、D16，五案例 × 三政策 × 雙 lane）、
seed 清冊、單一主終點、P1–P3 對比、1 cycle 工程差異、exact 單尾檢定、Holm
step-down 與配對 bootstrap 全部沿用原凍結文件，不因重新估價而改動。
