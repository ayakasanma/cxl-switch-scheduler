# CXL Switch Scheduler 專案全面審查與改進建議（2026-11-07）

- **審查日期**：2026-11-07（Asia/Taipei）
- **基線分支與 Commit**：`experiment/main-sq` @ `a3f4d8b`（2026-11-06 17:49 +0800）
- **審查範圍**：
  1. 論文修訂版 `docs/final-report/main-v4.tex`、`sections/hotnets-body-v4.tex`（SHA-256 `e8d41c55...`）與 `main-v4.pdf`（SHA-256 `c8008bd1...`）
  2. 已完成之 20-seed 動態確認實驗（`dynamic-role-switch-v2-confirmation-acceptance-20261106.json`，seeds `7401–7420`，600 `MODEL_ONLY` jobs + A3/A4 RTL 錨點）
  3. **最新完成**之 5-seed 多視窗容量吸收配對實驗（`artifacts/implementation/capacity-absorption/20261106T094757Z_w5m-frozen/`，seeds `8101–8105`，60 `MODEL_ONLY` jobs）
  4. 先前審查與分配紀錄（`docs/reviews/paper-spine-20261105/REVIEW_ZH.md`、`WORK_ASSIGNMENT_20261105.md`、`owner-decisions-A-20261106.json`）
  5. 外部三方審查打包工具鏈（`output/handoff/`）

---

## 一、最新實驗結果驗收與量化分析

### 1.1 多視窗容量吸收配對實驗（`20261106T094757Z_w5m-frozen`）—— **驗收通過（60/60 PASS）**

Commit `a3f4d8b` 啟動的背景 60-job 實驗已於 `2026-11-06T13:01:35Z`（台北時間 21:01:35）正常結束。本輪獨立核對結果已寫入 [`docs/reviews/capacity-absorption-acceptance-20261107.json`](capacity-absorption-acceptance-20261107.json)，所有凍結閘門（[`capacity-absorption-freeze-20261106.json`](capacity-absorption-freeze-20261106.json)）全數通過：

- **執行完整性**：60 個 seed-qualified 原始 JSON 檔（5 seeds `8101–8105` × 2 profiles `under/over` × 3 policies `FAI-inspired / CGOF(1:1) / CGOF(2:1)` × 2 lanes `mixed/isolated`）與 `manifest.json`（SHA-256 `8bd05324...`）皆完整，`failed: []`。
- **守恆與完工檢查**：30 組配對（60 jobs）100% 滿足 `fired == accepted == sum(generated)` 且 `heavy.completed == true`。
- **來源穩定性**：49 個追蹤原始檔（含 `scripts/run_capacity_absorption.py` SHA-256 `89db76a5...`）在執行前後 **0 雜湊漂移**。
- **時間上限**：總牆鐘時間 `11,618 s`（`3.23 h`，遠低於 `60 h` 模擬上限）；單波（6 jobs）最慢 `1,592.5 s`（`0.442 h`，遠低於 `1.5 h` 單 job 上限）。

#### 量化結果摘要（$W=5{,}000{,}000$、4 視窗、N4/D16、$\text{ready\_p}=0.90$、5 seeds `8101–8105`）

| Profile（Heavy 工作量） | 政策 | Mixed − Isolated Heavy 完工差（cycles，mean ± 95% t-CI） | Heavy 完工比值（mixed / isolated） | Mixed Sparse G→F P99（5 seeds） | Mixed Sparse G→F mean / max（cycles） | Mixed Heavy wall-gap P99 / max（cycles） |
| --- | --- | --- | --- | --- | --- | --- |
| **`under`**（$4\times 10^6$，`heavy_p=0.25`、`sparse_p=0.02`） | `FAI-inspired` | **0.00 ± 0.00**（全 5 seeds 皆為 0） | **1.00000000 ± 0.00000000** | `[4, 4, 4, 4, 4]` | `1.4536` / `15–18` | `3` / `7–8` |
| **`under`**（$4\times 10^6$，`heavy_p=0.25`、`sparse_p=0.02`） | `CGOF(1:1)` | **0.00 ± 0.00**（全 5 seeds 皆為 0） | **1.00000000 ± 0.00000000** | `[3, 3, 3, 3, 3]` | `1.2055` / `8–9` | `3` / `8–10` |
| **`under`**（$4\times 10^6$，`heavy_p=0.25`、`sparse_p=0.02`） | `CGOF(2:1)` | **0.00 ± 0.00**（全 5 seeds 皆為 0） | **1.00000000 ± 0.00000000** | `[3, 3, 3, 3, 3]` | `1.2759` / `8–9` | `3` / `9–11` |
| **`over`**（$1.75\times 10^7$，`heavy_p=1.00`、`sparse_p=0.05`） | `FAI-inspired` | **+3,889,105.40 ± 1,360.90**（`3,887,682–3,890,379`） | **1.20000215 ± 0.00006469** | `[27, 27, 27, 27, 27]` | `12.8376` / `38–40` | `5` / `18–19`（mean `18.8`） |
| **`over`**（$1.75\times 10^7$，`heavy_p=1.00`、`sparse_p=0.05`） | `CGOF(1:1)` | **+3,889,105.80 ± 1,361.33**（`3,887,682–3,890,380`） | **1.20000217 ± 0.00006471** | `[4, 4, 4, 4, 4]` | `1.4185` / `14–15` | `4` / `11`（mean `11.0`） |
| **`over`**（$1.75\times 10^7$，`heavy_p=1.00`、`sparse_p=0.05`） | `CGOF(2:1)` | **+3,889,105.80 ± 1,361.33**（`3,887,682–3,890,380`） | **1.20000217 ± 0.00006471** | `[4, 4, 4, 4, 4]` | `1.5655` / `14–17` | `4` / `13–14`（mean `13.6`） |

#### 關鍵機制洞見（可強化論文敘事）

1. **`under` 負載下的跨視窗完全容量吸收**：在 `under` 負載下（總到達率 $0.25 + 3\times 0.02 = 0.31 < \text{ready\_p}=0.90$），執行跨越三道分類邊界（分類軌跡 `H/H/H/H -> B_H/H/H/H -> L/H/H/H -> L/H/H/H`，約 $1.6\times 10^7$ cycles），三種政策的 mixed 與 isolated Heavy 完工週期在全部 5 個 seed 上完全一致（差距 **0 cycles**）。同時，`CGOF(1:1)` 與 `CGOF(2:1)` 仍將 Sparse G→F P99 由 `4` 降至 `3` cycles、最大延遲由 `15–18` 降至 `8–9` cycles。
2. **`over` 負載下的服務守恆率與多視窗分類轉態效應**：
   - 當 Heavy 持續飽和（`heavy_p = 1.0`）且三個 Sparse 來源各以 `0.05` 到達（合計 `0.15 / cycle`）時，只要不丟包且不餓死 Sparse，Heavy 可分得之有效服務率必由 isolated 的 $0.90$ 降至 $0.90 - 0.15 = 0.75\text{ / cycle}$。因此理論完工時間比值為 $\frac{0.90}{0.75} = 1.200000$，理論完工週期差為 $0.20 \times \frac{17{,}500{,}000}{0.90} \approx 3{,}888{,}888.9\text{ cycles}$。
   - 實測三種政策的完工比值皆收斂於 `1.200002`；`CGOF(1:1)` 與 `CGOF(2:1)` 相對 `FAI-inspired` 的 Heavy 完工週期差在 5 個 seed 上僅為 `[0, 0, +1, +1, 0]` cycles（平均 **+0.40 cycles**，佔總長 2,333 萬 cycles 的 $1.7\times 10^{-8}$）。
   - **與單窗 C5 的關鍵差異**：在跨越四個 W5M 視窗的 `over` 執行中，前兩窗（`0–10M` cycles）Heavy 處於有效 High（`H` 與 `B_H`），`FAI-inspired` 在同類別內採全局 oldest-first，使新到達的 Sparse 請求排在滿載（D16）的 Heavy 佇列之後；進入後兩窗（`t >= 10M`）Heavy 轉為 `L` 後，`FAI-inspired` 的 10/10 類別輪替又使 Heavy 在三個 Sparse 佇列有積壓時遭遇連續 High 服務加下游 stall，導致 `FAI-inspired` 的 Sparse G→F P99 升至 **27 cycles**、Heavy max wall gap 達 **18–19 cycles**。反觀 `CGOF(1:1)` 與 `CGOF(2:1)` 透過逐來源信用額度限制單次輪替長度，將 Sparse G→F P99 壓低 **85.2%（27 → 4 cycles）**，且 Heavy max wall gap 反較 `FAI-inspired` 更低（**11.0 / 13.6 vs. 18.8 cycles**）。
3. **證據邊界定位**：依 `capacity-absorption-freeze-20261106.json`，本實驗必須明確標記為 **`MODEL_ONLY` 多視窗同方向獨立容量吸收驗證**，不宣稱為舊 C5（`heavy_work=20,000`、`phase_horizon=5,000`）的原規格重現，亦不升級為 RTL 確認。

---

### 1.2 20-Seed 動態確認實驗（`7401–7420`，600 jobs）與 A3/A4 錨點狀態

- **狀態**：已於 `fe08d25` 結案並寫入 `docs/final-report/sections/hotnets-body-v4.tex`（`94cdc0f`、`a3f4d8b`）。
- **主要結論**：
  - **P1**（`role-switch`：Main − CGOF 2:1）：20/20 seeds 全為 `+15` cycles（exact sign test $p = 9.54\times 10^{-7} < 0.0167$，`SUPPORTED_WITHIN_PROTOCOL`）。
  - **P2**（`role-switch`：CGOF 1:1 − CGOF 2:1）：20/20 seeds 全為 `+1` cycle（$p = 9.54\times 10^{-7} < 0.025$，`SUPPORTED_WITHIN_PROTOCOL`）。
  - **P3**（`multi-window`：Main − CGOF 2:1）：18 個 seed 為 `+14` cycles、2 個 seed 為 `+13` cycles，均值 `+13.9` cycles（95% bootstrap CI `[13.75, 14.00]`，$p = 9.54\times 10^{-7} < 0.05$，`SUPPORTED_WITHIN_PROTOCOL`）。
- **已揭露限制**：P1 與 P2 在每個 seed 上的差值皆為常數（15 與 1），使 paired bootstrap 區間寬度為 0；`hotnets-body-v4.tex` 已正確將此列為四視窗端點的結構特性，而非獨立抽樣變異的證據，並維持統計為 `MODEL_ONLY`、C7 為 `SINGLE_SEED`（RTL 錨點僅 A3 `7301` 4/4 與 A4 `7401` 2/2）。

---

## 二、專案與論文改進建議（供 Host 執行）

以下改進建議依「論文實質正確性與抗審稿攻擊力」排序，分為 **P0（強烈建議在定稿或下一輪發布前完成，無需跑新實驗）** 與 **P1（工程與衛生改進）**。

### P0-1：同步最新 60-job 容量吸收實驗之狀態檔與論文 v4 正文

1. **更新狀態紀錄**：
   - `docs/reviews/owner-decisions-A-20261106.json`：將 `capacity.status` 由 `"RUNNING"` 更新為 `"COMPLETED_AND_ACCEPTED"`，並補上 `acceptance: "docs/reviews/capacity-absorption-acceptance-20261107.json"` 與 `manifest: "artifacts/implementation/capacity-absorption/20261106T094757Z_w5m-frozen/manifest.json"`。
   - `docs/EXPERIMENTS_BACKLOG.md`：將 Status 表第 4 項（`Under/over pairs`）更新為已完成 5-seed、60-job `MODEL_ONLY` 多視窗容量吸收驗證（RTL under/over 錨點則依主人 A 裁決保留為未來工作）。
2. **寫入 `docs/final-report/sections/hotnets-body-v4.tex`**：
   - 在 `\subsection{Dynamic Workload Confirmation}` 末尾加入 5-seed（`8101–8105`、60 `MODEL_ONLY` jobs）多視窗容量吸收結果：`under`（4M Heavy）三政策完工差皆為 `0` cycles 且 CGOF 將 Sparse P99 由 `4` 降至 `3` cycles；`over`（17.5M Heavy）三政策完工比值皆為 `1.200002`（CGOF 與 Main 平均僅差 `+0.40` cycles），同時 CGOF 將跨視窗 Sparse P99 由 `27` 降至 `4` cycles、Heavy max wall gap 由 `18.8` 降至 `11.0/13.6` cycles。明確標註其為獨立多視窗 `MODEL_ONLY` 驗證，非舊 C5 重現或 RTL 升級。
   - 在 `Table~\ref{tab:cohorts}`（`hotnets-body-v4.tex:96–116`）補入 11/04–11/06 新增的兩組 cohort（20-seed dynamic confirmation `7401–7420` + A3/A4 RTL anchors；5-seed multi-window capacity absorption `8101–8105`），並將表題更新為 `through November 6, 2026`。

### P0-2：落實 `paper-spine-20261105/REVIEW_ZH.md` 尚未套用之四項高優先級文字修訂（R1、R2、R3、R5）

經比對 `hotnets-body-v4.tex`，11/05 的 `commit 22b34a3` 套用了 7 處小幅用詞修飾，但 `paper-spine-20261105/REVIEW_ZH.md` 指出的 **R1、R2、R3、R5 四項核心論證漏洞** 仍留在 `hotnets-body-v4.tex` 中，6Pro 三方審查極可能再次命中：

1. **R1（`hotnets-body-v4.tex:300`，把小幅非零代價寫成維持不變 & 數字範圍誤差）**：
   - **現況**：`under overload contention they trade 1--2.55 additional cycles of worst-case Heavy inter-service gap while preserving long-run Heavy completion and throughput`
   - **問題**：單窗 model overload（`body-v4.tex:249–251`）中，Main、CGOF(1:1)、CGOF(2:1) 的 Heavy 平均最大 gap 為 `7.00 / 7.55 / 9.55` cycles，差距應為 **`+0.55` 與 `+2.55` cycles**（非 `1--2.55`）；completion ratio 差 `+0.0002227`、throughput-ratio 差 `-0.0001544`，屬微小但非零的取捨，寫成 `preserving` 會被審稿人質疑與前文表格矛盾。
   - **建議改寫**：`in single-window model overload they trade +0.55 (1:1) and +2.55 (2:1) additional cycles of mean maximum Heavy inter-service gap and a +0.00022 completion-ratio increment for large Sparse-tail reductions (while in four-window overload both CGOF settings match Main's 1.200002 completion ratio within +0.40 cycles and lower maximum Heavy gaps from 18.8 to 11.0--13.6 cycles)`。
2. **R2（`hotnets-body-v4.tex:2, 302` 與 `CLAIM_EVIDENCE_MATRIX_20261102.md:9`，將 ordering 未確認過度推論為 allocation 主導因果）**：
   - **現況**：`hotnets-body-v4.tex:302` 寫 `confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever`，且把 `while raising Q1 worst-case Heavy gaps` 混寫在 W256 與 W5M 兩組實驗之後；`CLAIM_EVIDENCE_MATRIX_20261102.md:9` 的 C3 Tier 仍標 `CONFIRMED`。
   - **問題**：quota × ordering 的四個實驗組全部都已使用 per-source credits，並未交叉操弄「class quota vs. per-source credit」；因此 ordering 未達 15/20 門檻只能證明「在已具備 per-source credit 下，將 oldest-first 換成 eligible-RR 未帶來一致改善」，不能直接作「per-source allocation 是主因」的因果識別。此外 W256 的 Q1 Heavy gap 差為 `0`（0/20 seeds），只有 W5M 5-seed 探索出現 `+1.6` cycles。
   - **建議改寫**：
     - `hotnets-body-v4.tex:2`（Abstract）：將 `not confirmed as a universal improvement at W256` 改為 `not confirmed under the preregistered 15/20 joint strict-improvement gate at W256`。
     - `hotnets-body-v4.tex:302`：改為 `The twenty-seed W256 ordering confirmation (\code{NOT\_CONFIRMED}) shows zero Q1 difference and a $-1$-cycle Q2 Sparse P99 change in only 7/20 seeds (below the 15/20 gate), while the five-seed W5M production exploration trades a one-cycle Q2 Sparse P99 reduction against a $+1.6$-cycle mean Q1 maximum Heavy gap; within credit-gated scheduling, replacing oldest-first with eligible round-robin therefore yields no confirmed tail advantage.`
     - `docs/final-report/update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md:9`：將 C3 Tier 由 `CONFIRMED` 改為 `NULL_CONFIRMED / SUPERIORITY_NOT_CONFIRMED`。
3. **R3（`hotnets-body-v4.tex:300`，跨情境 `strongest overall` 與 `1:1`/`2:1` 成績混用）**：
   - **現況**：`the CGOF settings provide the strongest overall operating point across the three specified objectives ... they eliminate single-Low class-quota skew and reduce trained Sparse P99 by 41--89% relative to Main`
   - **問題**：trained N4 A/B 的 `41--89%`（`10.00 -> 1.10`、`21.05 -> 12.35`）只測了 `CGOF (2:1)`，沒有 `CGOF (1:1)` 的 trained A/B 對照；而在 near-load RTL 中 `1:1` 優於 `2:1`（`3 vs. 4`、`9.45 vs. 10.85`）。
   - **建議改寫**：刪除 `strongest overall operating point`，改為條件式總結：明確將 trained A/B 的 `41--89%` 綁定 `CGOF (2:1)`（面積較 Main `-0.268%`），將固定類別下消除單一 Low 配額偏斜與加權/等份分配分別歸給 `CGOF (2:1)` 與 `CGOF (1:1)`，並保留 (i)(ii)(iii) 三條操作邊界。
4. **R5（`hotnets-body-v4.tex:245, 264`，W256 小樣本 P99 等於單輪最大值之揭露）**：
   - **現況**：未在正文或 Table 8 說明 W256 每輪 Sparse 請求數僅 $n=12\text{--}32$。
   - **建議改寫**：在 `hotnets-body-v4.tex:245`（或 Table 8 caption）補一句：`Because each W256 mixed run contains $n=12\text{--}32$ Sparse requests ($\lceil 0.99n\rceil=n$), the preregistered nearest-rank P99 equals the per-run maximum in this short-window screen.`

### P1-1：排版微調與交付檔案同步（R4）

1. **消除 `main-v4.pdf` 的 `1.5849pt` 垂直 overfull vbox**：目前 `main-v4.log` 有一處 `Overfull \vbox (1.5849pt too high)`（已於 `owner-decisions-A-20261106.json` 揭露）。在納入上述 P0-1/P0-2 文字微調後，可微調該頁段落間距或圖表 `\vspace`，使 `main-v4.pdf` 維持 15 頁且達成 `0 undefined references / 0 overfull hbox / 0 overfull vbox`。
2. **同步 `output/pdf/` 與 `README`**：目前 `output/pdf/` 最新檔仍為 `cxl-scheduler-revised-20261102.pdf`（v3），建議將編譯驗收後的 `main-v4.pdf` 複製為 `output/pdf/cxl-scheduler-revised-20261106-v4.pdf`（並保留 `20261102.pdf` 作歷史對照）。

### P1-2：工程與儲存空間衛生（不影響現有已驗收證據）

1. **補註 Clean A3 Run ID**：在 `docs/reviews/dynamic-role-switch-v2-confirmation-release-20261104.md` 補記 clean A3 run ID `20261104T063359Z_1495` 與最終驗收收據 `dynamic-role-switch-v2-confirmation-acceptance-20261106.json`。
2. **A3 `a3_scope.json` 常數與衍生紀錄**：`scripts/run_dynamic_role_switch_a3.py:80` 硬編碼 `drain="NOT_EXERCISED"`，已在 `dynamic-role-switch-v2-a3-acceptance-20261104.json` 與 `hotnets-body-v4.tex:302` 正確註明「自然觸發一次 2-cycle drain（`depth8-bursty` mixed，`fired == accepted == 18,815,149`），定向長 backlog drain 因凍結 harness 要求 `heavy_complete` 而未執行」。為維持 48 檔來源雜湊與已完成的 660 個確認/容量 jobs 完全一致，**建議不要修改 `scripts/run_dynamic_role_switch_a3.py`**，維持現行衍生紀錄說明即可。
3. **`over` 原始 JSON 檔案體積注意事項**：`artifacts/implementation/capacity-absorption/20261106T094757Z_w5m-frozen/` 中 30 個 `over` 原始 JSON 檔共佔 **14 GB**（單檔 273–687 MB），原因是 `over` 下 Heavy 的 pre-admission Wait（$G\rightarrow A$ 與 $G\rightarrow F$）隨時間線性累積至約 583 萬 cycles，產生數百萬個獨立直方圖鍵。打包腳本已透過 `ART_NAMES` 與 `3 MB` 上限自動排除這些巨型單一 seed 檔（只收 `15 KB` 的 `manifest.json` 與 `capacity-absorption-acceptance-20261107.json`）。

---

## 三、GPT-6 Pro 三方審查最新壓縮包（2026-11-07）準備狀態

為讓 GPT-6 Pro 進行最新一輪三方審查（Devil's Advocate ／ Methodology ／ Domain），已完成以下準備：

1. **新增 2026-11-07 打包設定與導讀包**：
   - [`output/handoff/bundle-src-20261107/START_HERE_ZH.md`](../../output/handoff/bundle-src-20261107/START_HERE_ZH.md)：完整涵蓋至 2026-11-07 的專案進度（11/02 v3 PDF、11/06 v4 PDF、20-seed 600-job 動態確認、clean A3 與 A4 RTL 錨點、5-seed 60-job 多視窗容量吸收結果、主人 A/A/A 裁決，以及本審查報告）。
   - [`output/handoff/bundle-src-20261107/DISCUSSION_PROMPT_ZH.md`](../../output/handoff/bundle-src-20261107/DISCUSSION_PROMPT_ZH.md)：專為 **GPT-6 Pro 三方審查（Devil's Advocate、Methodology、Domain + 主審綜合裁定）** 設計的單輪高資訊密度審查指令，聚焦審查最新 v4 論文與全套實驗證據鏈。
   - [`output/handoff/build_bundle_20261107.py`](../../output/handoff/build_bundle_20261107.py)：相較 11/04 版，新增收錄 `docs/final-report/main-v4.pdf`（同步至包內 `output/pdf/cxl-scheduler-revised-20261106-v4.pdf`）、`.setup-logs/implementation/p1-under-over-20261106/` 執行日誌、最新驗收 JSON 與本審查報告，並排除 14 GB 的巨型 raw seed JSON 與排版暫存檔。
2. **已預先打包並通過 `VERIFY_BUNDLE.py` 校驗**：
   - 壓縮包路徑：`cxl-scheduler/output/handoff/cxl-scheduler-agent-essentials-20261107.zip`
   - 校驗檔路徑：`cxl-scheduler/output/handoff/cxl-scheduler-agent-essentials-20261107.zip.sha256`
   - 若 Host 先套用上述 P0-1／P0-2 的 `hotnets-body-v4.tex` 文字修訂並重新編譯 `main-v4.pdf`，只需在 `cxl-scheduler` 目錄下重跑一行命令即可刷新最終壓縮包：
     ```bash
     wsl python3 output/handoff/build_bundle_20261107.py
     ```
