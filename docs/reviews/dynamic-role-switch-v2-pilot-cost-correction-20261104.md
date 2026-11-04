# v2 pilot 實測成本修正

日期：2026-11-04。狀態：**COST_MODEL_REVISED_PENDING_APPROVAL**。

## 實測

seed 7301 的完整 W5M pilot 於 2026-11-03T18:29:00Z 啟動（30 個 model jobs、
7 個 worker、完整 Metrics＋RoleBook＋physical-source 記帳）。
第一個完成的 job（multi-window isolated CGOF(1:1)，21,873,605 active cycles）
回報 `wall_s = 8,155.4`，即 2.265 h／job。

凍結 v2 的成本模型是 0.3473 h／job（21,876,819 ÷ 17,500 cycles/s ÷ 3600）。
實測為模型的 **6.5 倍**，換算約 2,682 cycles/s。

原因是 pilot runner 以 `ThreadPoolExecutor` 啟動 worker。純 Python 的參考模型
受 GIL 限制，7 個 thread 只用到一個核心：WSL `ps` 顯示單一 PID 為 101% CPU、
7 個 LWP 各約 14.5%，每個 job 的 wall 因此約為單 process 的 7 倍。
這與完整記帳無關。以 `subprocess` 平行量測 300k cycles（同時有 pilot 佔 1 核、
A3 佔 2 核）：

| 併行 process | 每 process cycles/s | 合計 cycles/s | 每 job 估計 |
| ---: | ---: | ---: | ---: |
| 1 | 16,785 | 16,785 | 0.36 h |
| 7 | 13,547 | 94,830 | 0.45 h |
| 10 | 11,728 | 117,283 | 0.52 h |
| 15 | 9,272 | 139,076 | 0.66 h |

單 process 的 0.36 h 與凍結估計 0.347 h 相差 +4%，G1 以 7 個 subprocess 執行時
每 job 1,108–1,349 s 也符合原估計。量測在 `.setup-logs/implementation/
dynamic-role-switch-v2-speed-20261104/`。

## 對計畫的影響

| 階段 | 凍結估計 | 依實測重算 |
| --- | ---: | ---: |
| pilot 30 model jobs（7 process） | 1.75 h | 約 2.25 h |
| 確認 600 model jobs（7 process） | 26.25 h | 約 45 h |
| G1／P／C 合計 job-hours | 236 | 約 269 |
| 機器 wall（15 process 可選） | 42.8 h | 約 26 h |

原 thread 版 pilot 於 2026-11-03T18:29Z 啟動、完成 7 個 job 後停止；已完成結果
保留為 provenance（`dynamic-role-switch-v2-pilot/20261103T182900Z_w5m`），
不刪除也不併入新統計。以 process pool 重啟的 pilot 從 2026-11-03T23:02:08Z
開始，輸出至 `.../20261103T230208Z_w5m_process`，兩者重疊的 job 將逐值比對以
確認結果決定性。

**重啟後實測**：30/30 PASS，wall 8,249.3 s（2.291 h），預估 2.25 h，誤差 +1.8%；
job wall 合計 48,508.8 s（13.47 job-hours）、單 job 最大 2,183.2 s。
7 個與 thread 版重疊的 job 逐值相同（只排除 `wall_s`）。
其中 2 個 job（Main ready-bursty mixed、Main depth8-bursty mixed）出現
`drain_cycles = 2`，表示 model 側的 cut 後 cleanup 確實執行過；RTL 錨點仍全為 0。

凍結協定規定「預估超支則停止、另提修訂」，因此不得把 6.5 倍成本當成
已核准預算繼續跑完確認階段。pilot 本身仍持續，用於取得模型側資料、
完成 A3 的 G-EQ，以及量測完整 30 jobs 的實際分佈；確認階段不啟動。

## 排程偏離

凍結 v2 §3.2 要求模型與 RTL 不重疊。本次 A3 RTL（2 個 process）與重啟後的
pilot（6 個 process）同時執行，合計 8 個 process 對應 8 個實體核心；pilot
worker 數已由 7 降為 6 以保留 A3 的核數。這是排程偏離，記錄於此，不影響
任一 job 的資料內容。

確認階段（600 model jobs）仍須先修訂 v2 成本表與硬上限並重新凍結，
在核准前不啟動 7401–7420。
