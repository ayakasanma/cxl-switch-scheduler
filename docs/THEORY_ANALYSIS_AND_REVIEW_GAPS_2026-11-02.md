# CXL Switch 排程器：實驗理論分析、審查回應與待補實驗總覽

**更新日期**：2026-11-02（涵蓋至 `W5M` Production Ordering Campaign 與 `P0–P4` 證據審查修補完成）  
**證據層級**：`MODEL_ONLY`（模型機制控制）、`SCHEDULER_RTL`（サイクル精確之 RTL 模擬与 SAED32 Pre-layout PPA / Formality / 閘級功耗）  
**未涵蓋邊界**：`REAL_CXL / APPLICATION`（端到端 CXL.mem 協定延遲、DRAM 完成頻寬、CPU 應用程式 IPC / Slowdown 尚未實測）

---

## 一、以目前實驗結果可穩固提出的四大理論與分析

### 1. 配額分配單位理論：類別配額（Class Quota）vs. 逐源點數（Per-Source Credit）
* **機制本質**：
  * **FAI-inspired（Main，類別配額 10:10）**：將所有主機（Source）分為 `High` 與 `Low` 兩個類別（Class），兩個類別輪流享有各 10 次成功傳送（Fire）的配額，類內再以最老請求優先（Oldest-First）競爭。
  * **CGOF（Credit-Gated Oldest-First，逐源點數 1:1 或 2:1）**：保留相同的歷史服務量分類器，但將配額（Credit）直接綁定在「每一個獨立主機」上。當活躍主機皆耗盡點數時，依其當前有效類別（Effective Class）統一補點（Refill），在有點數（Eligible）的主機中挑選最老請求（OF）或輪流服務（Eligible-RR）。
* **核心分析與實證結論**：
  1. **固定分類且持續積壓（Continuous Backlog）下的分配算術**：
     * 在 1 個 `Low` 主機、3 個 `High` 主機且皆塞滿請求時，Main 的類別配額會給予單一 `Low` 主機 **50%** 的總輸出服務，而 3 個 `High` 主機必須平分另外 50%（各約 **16.67%**），導致整體的服務公平性（Raw Jain Index）降至 **0.7500**（的需求偏差 L1 達 0.50）。
     * 相對地，CGOF 的長期服務份額嚴格收斂至個人權重比例 $w_i / \sum_j w_j$。在 `CGOF (2:1)` 下，1 個 `Low` 與 3 個 `High` 的長期份額精確收斂至 $1/7 \approx 14.29\%$ 與 $2/7 \approx 28.57\%$（Raw Jain **0.9423**，Weighted Jain **1.0**）。
  2. **長期份額相同 $\neq$ 短期尾端延遲相同（Refill 與 Eligibility 相位效應）**：
     * 在 20-seed 有限 Heavy 工作（Finite-Heavy）RTL 確認實驗（Seeds `529–548`，80 runs）中，所有主機在唯一一次視窗結算後皆維持有效 `High`（`B_H/H/H/H`）。此時 `CGOF (1:1)` 與 `CGOF (2:1)` 的**相對權重比完全相同（皆為等權重）**，但每輪發放的絕對點數預算分別為 1 點與 2 點。
     * 實測結果顯示：`CGOF (1:1)` 的偶發請求（Sparse）P99 為 **3.00 cycles**、重負載（Heavy）最大服務間隔（Max Wall Gap）平均為 **9.45 cycles**；而 `CGOF (2:1)` 則分別上升至 **4.00 cycles**（+1.00 cycle, 95% CI `[1, 1]`）與 **10.85 cycles**（+1.40 cycles, 95% CI `[1.10, 1.75]`）。
     * **微觀因果證明（Credit Refill Trace v2）**：固定到達序列與出口可用率（Readiness），僅將每源絕對點數從 1 改為 2，在 5 個到達相位中有 3 個相位清楚觀測到在 Cycle 4 或 Cycle 7 因「點數重補（Refill）」或「資格集合（Eligibility Set）」不同而產生第一次服務順序分歧。這證明了**較粗的點數輪次（Larger Absolute Credit Budget）會拉長重補週期，改變偶發請求插入的微觀相位**。

### 2. 剩餘容量吸收理論（Slack Absorption Theory）：何時保護散戶不傷大戶？
* **機制本質**：
  * 當系統同時存在持續發送請求的「大戶（Heavy）」與偶發請求的「散戶（Sparse）」時，優先服務散戶是否必然拖慢大戶的總完工時間（Completion Time）？
* **核心分析與實證結論**：
  * 透過 W5M（500 萬 cycles）20-Seed 預註冊模型確認實驗（Seeds `6201–6220`）與 P0 共同生成視野（Common Generation Horizon）追蹤，證實其行為由**總需求率（Offered Load）相對於下游出口可用率（Sink Readiness）的邊界**決定：
    1. **未飽和 / 接近飽和區間（Under / Near Load，例如總產生率 $0.86 <$ 出口可用率 $0.90$）**：
       * 散戶請求主要填補了大戶自身未產生請求的「空檔（未用服務機會）」。
       * 在 Near Load 下，雖然大戶在過程中會出現平均最大 **5.00 個 descriptors** 的暫時累積落後（Transient Lag），但在觀察期內 **20/20 個 Seeds 全部追回（Recovered）**。
       * 因此，大戶在混合執行（Mixed）與獨佔執行（Isolated）下的最終完工時間差在 Under Load 為 **0 cycles（95% CI `[0, 0]`）**，在 Near Load RTL（Seeds `529–548`）下平均僅相差 **3.00～3.05 cycles**（完工時間比 `1.00000048`，幾乎為 1）。
    2. **超載區間（Over Load，總產生率 $>$ 出口可用率）**：
       * 空檔不敷使用，散戶服務直接排擠大戶的服務機會。此時 W5M 模型確認實驗中，混合執行的大戶完工時間比獨佔執行平均多出 **834.25 cycles**（95% CI `[820.4, 849.3]`，完工時間比 `1.03755`），顯著超過預先宣告的 20-cycle 容忍邊界。

### 3. 排序正交分解理論（Quota vs. Ordering Orthogonality）：選最老（OF）還是輪流選（RR）？
* **機制本質**：
  * 為了回答「CGOF 的低延遲究竟來自逐源點數（Credit Quota），還是來自最老優先（Oldest-First）排序？」，實驗將 CGOF 的配額（`Q1 = 1:1`、`Q2 = 2:1`）與合格主機內的排序規則（`OF = Oldest-First`、`RR = Eligible-Round-Robin`）進行 $2 \times 2$ 正交拆解。
* **核心分析與實證結論（含最新 W256 160-run 確認與 W5M 40-run Production RTL）**：
  1. **配額與活躍集合（Quota & Active Set）是主導槓桿，排序（Ordering）僅產生 $\le 1$ cycle 的二階微調**：
     * 在 **W256 20-Seed 預註冊 RTL 確認（Seeds `6501–6520`，160 runs）** 中：`Q1 (1:1)` 下 RR 與 OF 的 Sparse P99 差值 $d_1$ 在 **20/20 個 Seeds 全為 0**；`Q2 (2:1)` 下的差值 $d_2$ 與交互作用 $I = d_2 - d_1$ 僅在 **7/20 個 Seeds 為 $-1$ cycle**，其餘 **13/20 個 Seeds 全為 0（平手）**，平均僅 $-0.35$ cycle，未達預註冊要求的 15/20 門檻（判定為 `NOT_CONFIRMED`）。
  2. **W5M Production RTL（Seeds `6601–6605`，40 runs，每 run 約 625 萬 cycles）的精確取捨**：
     * 在真實 500 萬 cycle 視窗、單一分類邊界下，5 個 Seeds 的 Mixed Sparse P99 在四種設定（`Q1-OF / Q1-RR / Q2-OF / Q2-RR`）下**全部一致為 `11 / 11 / 12 / 11` cycles**（5/5 seeds 皆為 $d_1 = 0, d_2 = -1, I = -1$）。
     * 然而，切換為 `Eligible-RR` 在 `Q1 (1:1)` 下會使大戶的最壞服務間隔（Heavy Max Wall Gap）比 `OF` 增加 **$+1$ 至 $+2$ cycles**（平均 $+1.6$ cycles）。
     * 此外，大戶完工時間差 $A = C_{\text{mixed}} - C_{\text{isolated}}$ 在同一個 Seed 的四種設定中**完全相同**（RR 減 OF 在 10/10 組比較中全為 0）。
     * **結論**：`Eligible-RR` 在 2:1 配額下可換取 1 cycle 的 Sparse P99 改善，但在 1:1 配額下會墊高 Heavy 的最壞停頓間隔；兩者為描述性取捨（Descriptive Tradeoff），**不存在通用贏家（No Universal Winner）**。

### 4. 雙窗遲滯緩衝（Buffer Hysteresis）與觀測邊界理論（Readiness & Admission Boundary）
* **機制本質與實證結論**：
  1. **Buffer 狀態機的「抗雜訊 vs. 反應延遲」取捨，且「分類穩定時間 $\neq$ 排隊延遲恢復」**：
     * Main 的 4 狀態機（`H, B_H, L, B_L`）在進入 `B_H / B_L` 時**保留原有效類別（Prior-Hold）**，需連續兩個視窗同向證據才改變有效優先級；而 **`FAI-ImmBuf`**（原論文 Algorithm 2 之立即目標優先級重構，於歷史實驗產物中標記為 `Algorithm-2`）則在進入 Buffer 時**立即切換為目標有效類別（Immediate-Target）**，且遇 `KEEP` 時永久滯留於 Buffer。
     * 在 **Buffer Transition-Only（78 replays/window）** 中，單一視窗的短暫突波雜訊下，Main 的有效類別翻轉次數為 **0 次**（完全濾除），而單窗控制（Main-1W）與 `FAI-ImmBuf`（`Algorithm-2`）皆翻轉 **2 次**；但在持續角色反轉下，Main 需 **448～704 cycles**（依切換相位 `0 / 64 / 255` 之混合窗 B/S 證據而定，非固定 2W 常數）才穩定，比 Main-1W（192～448 cycles）慢一個視窗。
     * 在 **Buffer Closed-Loop（720 runs）** 中證實：分類器何時穩定（Settle Delay）與該角色請求的尾端等待（Cohort G$\to$F P99）是不同物理量，不可由「分類翻轉少」或「提早切換」直接推論延遲必然較低。
  2. **下游阻塞形狀（Readiness Temporal Shape）與 FIFO 深度（Admission Boundary）**：
     * 相同平均可用率（如 75% 或 90% ready）下，集中連續卡頓（Periodic / Bursty Stall）會比分散隨機卡頓（Bernoulli / Spread）大幅推升 Wall-Clock P99（例如 90% ready 下從 **3 cycles 升至 11 cycles**，75% ready trained-B 下從 **20.40 升至 27.00 cycles**），但扣除卡頓後的 `Eligible-Ready Gap P99` 維持 **2 cycles** 不變。
     * 將 FIFO 深度由 `D16` 縮減為 `D8`（單種子動態 RTL 驗證），大戶的總延遲（`G->F P99 = 20 cycles`）完全不變，但等待位置從「進入 FIFO 後等待（`A->F P99` 由 18 降至 16）」轉移至「進入 FIFO 前的外部阻塞（`G->A P99` 由 2 升至 11）」。

---

## 二、回答「審查建議（Evidence Review）」的具體清單與最新實驗標註

| 編號 | 審查建議指出的問題 / 潛在漏洞 | 最新完成的修正與實驗數據（2026-10-30 ～ 2026-11-02） | 狀態 |
| :---: | :--- | :--- | :---: |
| **R1** | **提早截斷（Early Cutoff）與強制排空（Forced Drain）疑慮**：Heavy 完成即停止生成 Sparse，且 Drain 時強制 `ready=1`，是否切掉尾端請求或掩蓋終局延遲？ | **P0 契約修正 + 120 組 Arrival Phase 實驗**：導入與政策無關的共同生成視野 $H$，Heavy 完成後仍繼續生成完整宣告的 Sparse 請求；Drain 沿用真實 `scenario.ready(k)`；追蹤逐 cycle 累積差 $\text{lag}(k)$，證實 Near Load 下中途平均落後 5 筆但在觀察期內 **20/20 全數追回**。 | ✅ **已解決** |
| **R2** | **RTL 缺乏 Eligible-RR 排序控制與檔名碰撞**：無法在真實硬體模擬中分離 Quota 與 Ordering 的效果。 | **P1 端到端接線 + W256 (160 RTL runs) + W5M Production (40 RTL runs)**：打通 `--ordering`，完成 20-seed W256 預註冊確認（7/20 改善、13/20 平手，`NOT_CONFIRMED`）與 5-seed W5M Production（耗時 30.7h，S=11/11/12/11，$I=-1$）。 | ✅ **已解決** |
| **R3** | **配額偏差（Quota Error）只看關窗最後 1 cycle 快照**：若窗內前面為空、最後一刻才進件，會誤判為不遵守配額。 | **P2 逐 Cycle 預決策積壓檢查（`cxl-quota-predecision-backlog-v1`）**：要求整個 active 視窗的**每一個 pre-decision cycle** 所有主機本地 FIFO 皆非空才列入配額誤差統計；不合格或舊資料明確標為 `UNAVAILABLE/null`（不轉為 0）。 | ✅ **已解決** |
| **R4** | **Held Grant（下游卡頓握住授權）時 Refill 快照失真**：用當下候選人反推，導致跨 Stall 的補點紀錄錯誤。 | **P3 三層 Refill 觀測（`cxl-credit-refill-trace-v2`）**：分離 `candidate_*`、`offered_*`（握住授權當下之快照）與 `committed_*`（實際 Fire 扣點快照），並驗證完整輸入序列。 | ✅ **已解決** |
| **R5** | **統計指標混淆（Self-Delta CI、Completion Ratio 語意、分位數相加）**：`phase0` 減自己印出 `[0,0]` CI、完工比與完成率同名。 | **P4 輸出契約升級**：拆開 `mixed_isolated_effects` 與 `phase_effects`；正名為 `heavy_completion_time_ratio_mixed_over_isolated`；探索/Smoke 強制 `CI=null`；嚴格區分 `G->A / A->F / G->F` 與 `Wall / Ready Gap`。 | ✅ **已解決** |
| **R6** | **Buffer 狀態機過度推論**：不能直接把「狀態切換次數少」當成「延遲降低」，也不能假設任意相位皆固定 2W 恢復。 | **獨立 Buffer Transition (156 replays) + Closed-Loop (720 runs)**：量化三個相位（0/64/255）的真實穩定延遲，以 CGOF(1:1) 通過 120/120 負控制，並將 `latency_recovery` 明確標註為獨立未定義門檻。 | ✅ **已解決** |
| **R7** | **Manifest 缺檔靜默略過（Silent File Filtering）**：`is_file()` 會在缺檔時靜默跳過雜湊檢查。 | **P0 強制檔案清單**：建立輸出前強制檢查所有必要來源與計畫檔，缺一即報完整路徑並以非零退出。 | ✅ **已解決** |

---

## 三、還缺哪些實驗才能「徹底補強」所有審查意見？（Gap Analysis）

雖然上述方法論與配額/排序機制已經補齊，但若對標**頂會（Top-tier Architecture / Systems 會議）或嚴格審查者的最終要求**，目前仍有以下 **5 項未跑（`NOT_RUN`）或僅有單種子/模型證據的缺口**，按投資報酬率（優先級）排列如下：

### 🔴 第一優先（高價值、現有環境可直接跑完的實驗）

1. **多視窗動態適應與角色切換的多種子 RTL 確認（Multi-seed Dynamic & Role-Switch RTL Confirmation，補強 H1 / H3）**
   * **目前缺口**：跨越 4 個 W5M 視界、實體主機角色切換（`[0,0,1,1]`）、Bursty vs. Spread Readiness 與 D8 深度的真實 RTL 實驗（`cgof-dynamic-20261030`），目前**只有 1 個 Seed（`7291`，20 runs）**，沒有信賴區間（`CI: null`）。
   * **需補實驗**：將這組動態 finite-Heavy 與角色切換協定擴展至預註冊的多種子（例如 5～20 個 held-out seeds），並在同一個有限工作框架下加入 `Main`（及 `WRR/IWRR`）的 RTL 對照，證明跨多個 W5M 邊界與角色互換時，CGOF 的收益具有統計重現性。

2. **將「容量吸收（Under / Near / Over Load）」從 Model 推進至 W5M Production RTL（補強 Follow-up B / H3）**
   * **目前缺口**：證明「Under/Near 完工差為 0、Over 完工差 +834 cycles」的 20-seed 確認實驗（`B-arrival-phase-confirmation-20261030`）目前是 **`MODEL_ONLY`**；而 Production RTL 的 20-seed finite-Heavy 確認只跑了 `near` 一種負載。
   * **需補實驗**：在 W5M Production RTL 上補跑 `under` 與 `over` 負載的 Mixed/Isolated 配對確認，讓「剩餘容量吸收理論」擁有完整的硬體模擬支撐。

3. **修復既有 `test_revision_power_vectors.py` 的 14 個測試腳本錯誤，並視需求補齊 CGOF 閘級功耗（Gate-Level Power）**
   * **目前缺口**：
     1. 全域 Python 測試中有 14 個既有錯誤（`ExperimentalSwitchModel` 收到 `policy='Main'` 的參數相容問題），雖不影響核心結果，但修好可讓全域回歸 100% 綠燈。
     2. 目前的 SAED32 PrimePower 閘級功耗實驗（18 組 cold + 3 組 N4 boundary）只涵蓋 `FCFS / RR10 / Main`，**尚未跑 `CGOF` 的 SAIF 閘級功耗**，且 `CGOF (1:1)` 合成網表中有 `23*(N+2)` 個未讀取的分類器暫存器（Dead State，因 1:1 不需依賴分類結果改變權重）尚未在 RTL 中透過參數裁切來展示「移除分類器後的極致省面積/省電版本」。

### 🟡 第二優先（延伸敏感度與閉迴路恢復門檻）

4. **定義並實測「Buffer 延遲恢復時間（Latency Recovery Horizon）」與 N8/N16、D32 效能擴展（補強 H1 / H4）**
   * **目前缺口**：目前 Buffer Closed-Loop 實驗僅為 W256 模型探索（Seeds `6101–6105`），且將 `latency_recovery` 標為 `NOT_DEFINED_THIS_ROUND`。此外，N8/N16 雖已完成合成與面積/時序（STA）驗收，但尚未跑多視窗 finite-Heavy 的延遲分位數對照。
   * **需補實驗**：事先定義何謂「角色切換後 Sparse P99 恢復至穩態區間」的數學門檻，並在 W5M 下比較 `Main (Prior-Hold)`、`Main-1W` 與 `FAI-ImmBuf (Immediate-Target, Algorithm-2)` 的真實排隊恢復曲線。

### ⚪ 第三優先（系統級大工程，建議在論文中列為 Scoped Limitation / Future Work）

5. **全系統 CXL.mem 模擬器或硬體平台對接（End-to-End CXL Response & Application Slowdown，補強 H5）**
   * **目前缺口**：目前所有 `fire/cycle` 都是排程器出口的 Descriptor 速率，`G->F` 是排程器等待週期，**不是** DRAM 控制器、CXL.mem 協定層、雙向 Link Flow-Control Credit 與處理器 Cache Miss 閉迴路下的實際記憶體回應延遲（Issue-to-Response Latency）或應用程式減速比（Application Slowdown / IPC）。
   * **處理建議**：除非團隊準備接入 `CXL-DMSim` 或 `gem5` 跑完整 CPU Trace，否則在現階段報告中**維持現有的嚴謹誠實聲明**（「本研究聚焦於可重現之 Switch 仲裁硬體邊界與 PPA 成本，系統級 DRAM/Link 閉迴路列為後續整合工作」），切勿把 Descriptor 指標直接改口稱為記憶體頻寬或應用效能。

---

## 四、關鍵決策解答：Algorithm-2 改名建議與「CGOF 是否總體最強？」

### Q1：為了可讀性，`Algorithm-2` 應該要改名嗎？
**強烈建議改名（或在首次定義後全面使用具機制意義的名稱）！**

* **為什麼要改？**
  對沒把 FAI-CXL 原論文第 5 頁背下來的讀者或審查者來說，`Algorithm-2` 是一個**毫無語意資訊的代號**。讀者看到圖表裡的 `Main` vs. `Algorithm-2`，根本無法直覺聯想到這兩者的差別在於「進入 Buffer 狀態時，到底保留原本優先級，還是立刻切換成目標優先級」。
* **建議怎麼改？（不破壞既有程式碼與 Artifact 雜湊的做法）**
  * **保留內部程式碼與 JSON Key 不變**（繼續用 `ALG2` / `Algorithm-2`，確保所有 SHA-256 驗證 100% 通過）。
  * **在論文與簡報的顯示名稱（LaTeX Macro `\Alg` 與圖表 Legend）改用自解釋名稱**。推薦以下三種方案（擇一）：
    1. **`FAI-ImmBuf`（或 `FAI-Immediate-Buffer`）** vs. 把 Main 稱為 **`FAI-HoldBuf`（或 `FAI-Hysteresis`）**：最推薦！一眼就看出一個是「進 Buffer 立刻換等級（Immediate）」，一個是「進 Buffer 先憋住原等級（Hold / Hysteresis）」。
    2. **`FAI-Eager`（急切切換版）** vs. **`FAI-Conservative`（保守雙窗版）**：白話好懂，適合口頭報告與簡報。
    3. **`FAI-TargetBuf`（目標緩衝版）** vs. **`FAI-PriorBuf`（原態緩衝版）**：精確對應 RTL 狀態機裡 `P_last` 存的是 Target 還是 Prior。
  * 在論文第 2 節只要寫一句話交代：*「為提升可讀性，本文將遵循原論文 Algorithm 2 第 13/18 行立即指派目標優先級之實作稱為 **FAI-ImmBuf**（於部分實驗產物中標記為 `Algorithm-2`）。」* 這樣既保持 100% 溯源誠實，又讓文章可讀性大幅提升。

---

### Q2：目前 `CGOF` 應該總體最強是嗎？
**答案是：「在我們的重點場景（保護偶發請求尾端延遲 + 維持跨主機公平性 + 硬體面積成本）下，CGOF 確實是綜合表現最優秀的 Pareto 最佳解；但不能在報告裡無條件寫它『在所有指標上全面最強（Universal Winner）』。」**

更精確、在審查者面前無懈可擊的定位如下：

#### 🏆 為什麼說 CGOF 綜合表現最強（三大硬核優勢）：
1. **偶發請求（Sparse Tail Latency）保護力斷層第一**：
   * 在 20-seed 訓練後 RTL 確認實驗中：
     * **獨立到達（Arm A）**：Sparse P99 從 FCFS 的 `18.10`、RR10 的 `11.00`、FAI-inspired (Main) 的 `10.00` cycles，直接被 **CGOF (2:1) 壓低到 `1.10` cycles**（幾乎零等待，20/20 seeds 全面勝出）。
     * **突發到達（Arm B）**：Main 的 Sparse P99 為 `21.05` cycles（甚至輸給 RR10 的 `17.70`），而 **CGOF (2:1) 壓低到 `12.35` cycles**（比 Main 減少 `8.70` cycles，20/20 seeds 全面勝出）。
   * 在有限 Heavy 模型超載（Overload）下，CGOF (2:1) 的 Sparse P99 為 **`4.85` cycles**，遠優於 Main 的 `28.30`、WRR 的 `10.00` 與 IWRR 的 `8.70` cycles。
2. **徹底修補了 Main 的「類別配額不公平（Class-Size Skew）」漏洞**：
   * 當 1 個 Low 與 3 個 High 持續競爭時，Main 會讓單一 Low 主機獨吞 50% 服務（Jain 掉到 `0.75`）；而 `CGOF (1:1)` 與 `CGOF (2:1)` 因為把點數發給個人，Jain 公平性分別維持在 **`1.0000`** 與 **`0.9423`（加權 Jain `1.0`）**。
3. **硬體成本（PPA）沒有變貴，甚至比 Main 略小且全數通過 25ns 時序**：
   * 在 SAED32（N4/N8/N16）合成與 PrimeTime 驗證下，6 組 CGOF 全部 `0` 違規通過：
   * 以 N4 為例：`CGOF (2:1)` 總面積為 `109,794.8`（比 Main 的 `110,089.8` **還小 0.268%**，Setup Slack `+10.40 ns`）；而 `CGOF (1:1)` 總面積更只有 `106,163.1`（比 Main **小 3.57%**，Setup Slack `+12.68 ns`）。

#### ⚠️ 為什麼不能寫成「無條件全面最強」（必須誠實揭露的三個 Trade-off）：
1. **對大戶（Heavy）的單次最大停頓間隔（Max Service Gap）有代價**：
   * 因為 CGOF 讓每個散戶都有獨立點數可以插隊，當 3 個散戶同時來插隊時，大戶被迫連讓三次。因此在模型超載（Overload）下，CGOF (2:1) 的大戶最大服務間隔為 **`9.55` cycles**，比 Main 的 `7.00` cycles 及 WRR/IWRR 的 `7.35` cycles **多了約 2.2～2.55 cycles**。
2. **如果完全只看硬體面積與時序（不管最老優先與動態分類），純 `RR10` 才是硬體最省的**：
   * `RR10` 不需要存 32-bit 到達時間戳（Timestamps）也不用比較器樹，面積比 FCFS / Main / CGOF 小了約 **24%～28%**（N4 面積僅 `79,047` vs. CGOF `109,795`）。
3. **在 `CGOF (1:1)` 與 `CGOF (2:1)` 之間，要看負載情境選**：
   * 在還沒有進入 Low 分類（大家都還是 Effective High）的 Near-Load 有限工作下，`CGOF (1:1)` 的 Sparse P99（`3.00` cycles）與 Heavy Max Gap（`9.45` cycles）其實都比 `CGOF (2:1)`（`4.00` 與 `10.85` cycles）更好！`CGOF (2:1)` 的優勢是在已經完成訓練、需要區分 High/Low 權重保護時才會發揮。

> **💡 寫進論文與報告的黃金結論句（建議直接採用）**：  
> *「**CGOF 並非在不付出任何代價下支配所有指標的萬能排程器，而是解決了 FAI 類別配額失衡（Class-Quota Skew）與突發尾端延遲（Burst Tail）的最佳架構演進。** 在與 FAI-inspired 幾乎相同的硬體面積預算下（N4 面積差異 $-0.27\%$），CGOF 透過將配額粒度由『類別』細化至『主機來源』，將偶發請求之 P99 延遲大幅降低 41%～89%（Arm B: $21.05 \to 12.35$ cycles; Arm A: $10.00 \to 1.10$ cycles），並消除單一低負載主機獨佔半數頻寬之不公平現象；其唯一交換代價為重負載主機在極端擁塞下增加約 1～2.5 cycles 之最大瞬時服務間隔，而長期吞吐量與完工時間則維持不變。」*
