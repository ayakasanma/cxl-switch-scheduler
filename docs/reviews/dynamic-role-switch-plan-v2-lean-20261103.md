# 多視窗動態／角色切換：精簡版實驗計畫 v2（獨立備選提案）

日期：2026-11-03。狀態：**PROPOSED_NOT_FROZEN**。
本提案本身不授權任何執行（確認 campaign、Main RTL 實作、新模擬）；是否納入版本由 Lead 處理。
v2 是與 [v1 計畫](dynamic-role-switch-rtl-plan-20261103.md)（`FROZEN_PROTOCOL_NOT_RUN`）並列的獨立備選，**不表示 v1 作廢**，也不建立 freeze receipt。
v2 不提升既有 C7（`SINGLE_SEED`／`SCHEDULER_RTL`）。探索 seed 9901 不是確認樣本。

可追蹤的摘要：[dynamic-role-switch-plan-v2-lean-20261103-summary.json](dynamic-role-switch-plan-v2-lean-20261103-summary.json)。其中記錄每個 probe 的完整 SHA-256、7291 對照、成本公式與 reviewer 處理方式。本文所有關鍵結論都能在這兩份可追蹤檔案中找到。
本機原始 provenance（已被 gitignore，未搬進 Git）：`.setup-logs/implementation/dynamic-role-switch-v2-probes-20261103/`（repo-relative）。

## 0. 結論

| 項目 | v1 | v2 |
| --- | --- | --- |
| 研究問題；5 案例 × 3 政策 × 2 lane；630 jobs | 固定 | 不變 |
| Seeds；主要終點；P1–P3；exact sign＋Holm；bootstrap | 固定 | 不變（P1 方向也不依 probe 調整） |
| 統計來源 | 630 個 W5M RTL jobs | 650 個純模型 jobs（含 7291 replay 20 個） |
| 新增 W5M RTL jobs | 630 | 6 個，全部為 Main |
| 證據主分類 | `SCHEDULER_RTL` | **`MODEL_ONLY`**，另以 `rtl_anchor_coverage` metadata 描述實際的 RTL 錨點（§2.3） |
| 時間（§3，皆為估計） | 731–739 h（硬上限 842 h） | 機器 wall 預算 51.3 h ＋ 人時約 29–34 h，**合計約 80–85 h（硬上限 117 h）** |

## 1. 理論審查

### T1｜lockstep 檢查的範圍

`sim/experimental/test_cgof_sched.py` 的 `Harness.cycle()`（L219–243）每個 cycle 的流程：在下降沿 `ReadOnly` 時執行 `check()`，上升沿時 `model.commit()`，+1 ns 後執行 `check_policy_state()`（L241）與 `after_edge()`。

逐 cycle 比對 RTL 與 model 的項目（`check()`，L261–284）：
- `o_in_ready`（L266）、`o_out_valid`（L267）
- `out_valid=1` 時的 `out_source` 與 105-bit `out_desc`（L269）
- `grant_held`（L271）
- model 的 `choice().source`（L273）、grant context 的 credit snapshot（L275）
- 每個有效 head 的 `head_ts`（L278–281）
- policy registers：`cls_q`、`idx_q`、`b_q`、`s_q`、`credit_q`、RR pointer（L282、L337–351）

不依賴 model 的 pin 規則（L286–335、L353–419）：
- reset 抑制、ready 與佔用量一致、無 bypass、offer 為 oldest
- stall hold、refill／eligible 選擇與 class snapshot
- fire 才扣 credit、window idx 與 closing edge、scoreboard pop

指標記帳：`test_cgof_diagnosis.py` 的 `edge()`（L78–135）、`revision_traffic.Metrics.observe`（L191–242，含 L208／L213／L214／L216／L226 的 assert）與 `RoleBook.observe`，只使用已被 assert 的 pins、model 的 `windows_closed`／`classes()`／`credits`，以及外生 traffic。

未逐 cycle 直接比對的內部狀態：FIFO 中非 head 的條目，以及 arrival counter（只透過 `head_ts` 間接比對）。

可推論：在**同一個** RTL job 中，若 `check()` 全部 PASS，記帳程式收到的排程輸入，就等於把 model 輸出餵給同一份記帳程式時的輸入。

不可推論：
1. `check()` PASS 本身**不**證明另一個獨立的 model runner 能逐值重現所有 latency 指標。要做到這點，必須同時滿足以下條件並經 G-EQ 驗證：
   - 呼叫同一份記帳程式；
   - reset 序列相同（`Harness.start()` 為 1＋`reset(2)` 個 reset edge）；
   - traffic／ready／descriptor 的 RNG 路徑相同；
   - drain 規則相同。
2. 沒跑 RTL 的 seed 沒有 RTL 覆蓋。
3. 若分歧只出現在未錨定的輸入上，就不會被發現。

### T1a｜7291 部分端點對照與適用範圍

來源：RTL run `20261029T182230Z_52853`（role-switch，CGOF 1:1／2:1 mixed），對照 model probe `v7291_c11`／`v7291_c21`。
結果：6 個欄位 × 2 個政策，12/12 相等。
比對欄位：`active_cycles` 對 `cut`（21,876,819）、active＋drain、4 個 closing cycle、4 次 close 後的 class、Sparse G→F count（1,313,003）、Sparse G→F nearest-rank P99（3／4）。
未比對：histogram／min／max／mean、G→A、A→F、所有 Heavy gaps 與 completion、`metrics` 的 phases／cohorts、fairness、`service_shares`、`generation_roles` 的 counts／at_cut／bursts、accepted／fired 總數、`trace_sha256`。probe 的 per-source P99 在 RTL schema 中沒有對應欄位。

probe.py／bench.py 與正式協定的差異：

| 項目 | probe／bench | 正式（cocotb diagnosis／v1） |
| --- | --- | --- |
| 記帳 | probe 用輕量記帳（沒有 Metrics／RoleBook），Sparse 以 `source != heavy(generation)` 判定 | 完整 Metrics＋RoleBook |
| reset | probe 只有 1 個 reset edge | 3 個 reset edge；影響未驗證 |
| drain | probe 用 `ready=1`，guard 1e6 cycles | **已裁定（Lead，2026-11-03）**：cut 後採 `ready=1` cleanup，bound＝2·(producer_backlog＋fifo_occupancy)＋128，與 v1 §3.1 及 `test_cgof_diagnosis.py` L160–165 一致。`cgof_diagnosis_traffic.py` 的 `scenario.ready` 只用於 active 階段。差異僅在 probe 的 guard 較寬 |

**drain 裁定的後果**：
- 既有 20 個 W5M RTL 錨點的 `drain_cycles` 全部是 0，所以 drain 行為**仍未經 RTL 驗證**，全案狀態為 `NOT_EXERCISED`，列為 remaining gap，不得寫成已驗證，也不作為任何錨點的 gate（§2.2）。
- 日後若改採 scenario-ready drain，必須另立協定、另行命名並重新 freeze，不得與本協定混跑。
| 長度 | bench 只跑 200k cycles，未跨過第一個 W5M close（4,999,999），也沒有角色切換 | 四個 close 加 tail |

7291 這兩項，以及全部 20 個 legacy 7291 RTL jobs，`drain_cycles` 都是 0，所以本次**完全沒有驗證真實 drain 行為**。
結論：本次只是部分端點相符，**不能**用來支持完整協定的等價。

### T2｜isolated lane 與政策無關（僅有縮小規模的模型證據）

三種政策都是 work-conserving，isolated lane 只有 Heavy，所以 fire 時刻只由 arrivals／ready 決定。
`iso.py` 以 seed 7301、W256、4 個 windows、heavy_work 900 跑三種形狀，三種政策的 isolated fire digest 都相同。W5M 下未驗證。
v2 保留每個政策各自的 isolated job；「三政策 isolated C 相同」列為 pilot gate，失敗即停，不自動省略。

### T3｜role-switch class 軌跡與 P1 方向風險（保留）

FSM 推導與 7291 RTL、9901 的四個 probe 都一致：close0 為 `B_H,H,H,H`，close1 為 `L,H,H,H`，close2 為 `B_L,B_H,H,H`，close3 為 `H,L,H,H`。
風險：W2–W3 期間 src0 已轉為 Sparse，卻仍是有效 Low；Main 的 10:10 類別配額理論上可能保護 src0，使 v1 P1 的單尾方向不成立。
9901 探索觀察（`MODEL_ONLY`，非證據）：role-switch 下 Main P99 為 19（src0 為 13），CGOF-2:1 為 4，CGOF-1:1 為 3。
這不用來調整 v1 已凍結的 P1。之後若新增或修改檢定，必須另行凍結，且不得使用 7291／9901／7301 作為確認。

### T4｜exact＋Holm 的實際門檻（規則不變）

n=20 的 exact 單尾 p 值：K=14 時 .0576591，K=15 時 .0206947，K=16 時 .00590897。
Holm step-down 的門檻依 p 排序依序為 .05/3、.05/2、.05：
- 最小的 p 必須 ≤ .0167，即 K ≥ 16；
- 第一步通過後，第二步只需 ≤ .025、第三步 ≤ .05，K ≥ 15 即可；
- K=14 在任何一步都不通過。

任一步失敗，其後全部不拒絕。各個 P 仍須同時滿足 `mean(delta) ≥ 1`。這段只是說明，**不修改** v1 的規則。
既有 W5M 證據（C2 的 CI `[1.00,1.00]`、C4 為 5/5）顯示跨 seed 變異小，但這只是背景，不構成 power 保證。

### T5／T6

T5：四個 windows 與 W5M 不可縮短。Main 需要 close2／close3 才能完成反轉；heavy_work 縮到 16.2M 只省約 7%，卻會改變 cohort，不採用。
T6：三個次要案例不在主要檢定家庭內。Main 的 D8／bursty hold 由 A2 短 W 與 A3 覆蓋；CGOF 的這部分只有 7291 legacy RTL。

## 2. 精簡設計

### 2.1 純模型 runner

- 將 `edge()` 的 per-cycle 記帳抽成共用模組，cocotb test 與 model runner 呼叫同一份程式。
- model runner 用 `view()`／`commit()` 取代 `Harness.cycle()`，並重現 reset 序列、RNG 路徑與 drain 規則。
- 輸出沿用 RTL 結果的 schema，排除 `native_coverage`、`native_cgof`、`input_hold_checks`。
- Main 使用 `ExperimentalSwitchModel("FAI-inspired")`；M2 重跑 `refc/tests/test_experimental.py`，確認它與 harness oracle `FaiMainSwitchModel` 等價。
- 雙帳本沿用 v1 §3.2；帳本 B 的新欄位是新增實作。

### 2.2 RTL 錨點與 G-EQ

| 錨點 | seed | 內容 | 新 W5M RTL | 可比對欄位 |
| --- | --- | --- | ---: | --- |
| A1 | 7291 | 既有 20 個 CGOF jobs（5 案例 × 1:1／2:1 × 2 lane） | 0 | 只有 G-EQ-legacy |
| A2 | 7301 | Main W256 5 案例 × 2 lane；另加 CGOF W256 回歸 5 案例 × 1:1／2:1 × 2 lane | 0（短 W） | legacy＋new |
| A3 | 7301 | Main：role-switch mixed＋isolated、multi-window mixed、depth8-bursty mixed | 4 | legacy＋new |
| A4 | 7401（本輪未用） | Main：role-switch mixed＋isolated | 2 | legacy＋new |

- **G-EQ-legacy**：比對凍結 7291 輸出中已存在的欄位（`generation_roles`、`heavy`、`metrics`、`fairness`、`service_shares`、`classifier`、`trace_sha256`、`accepted`、`fired`、`active_cycles`、`drain_cycles`、`generated`、`ready_cycles`），必須逐值相等。舊輸出沒有的欄位一律標 `NOT_AVAILABLE`，不當成 0，也不以 skip 視為 PASS。
- **G-EQ-new**：新增的共用記帳欄位與帳本 B 欄位，只能在 A3／A4 的 6 個新 Main W5M 錨點，以及 A2 的短 W CGOF 回歸上核對。A2 必須跨過 4 個 close、包含角色切換，並比對 legacy＋new 欄位。drain 行為不在 A2 可驗證的範圍內；若短 W 自然出現 `drain_cycles>0`，只記錄，不作為 gate。
- **A1 的重用無法為新欄位補任何證據。** 預設方案中，CGOF 的 W5M RTL 對新欄位的涵蓋為 0。若需要，另見備選「v2＋CGOF-W5M」（§3.3），不併入 6 個 Main 錨點的預算。
- 26 個 W5M 輸入要分開說明：其中 20 個是 legacy（CGOF，只有 legacy 欄位），6 個是新增（Main，legacy＋new）。既有 20 個 W5M 錨點都沒有 drain>0。drain 不是任何錨點（A1–A4）的 gate；新錨點若自然出現 drain>0 只記錄，全案 drain 維持 `NOT_EXERCISED`。G-EQ-legacy 中 `drain_cycles` 逐值相等（例如皆為 0），不構成 drain 行為的驗證。
- 任一項不等即停止，不得以模型數據替代。A3＋G-EQ 通過後才能進入確認；A4 失敗則依協定停止。

可支持的主張：在上列錨點輸入、上列欄位範圍內，model 與 RTL 逐值相等。
不可支持的主張：20 個確認 seed 都有 RTL；Main 在 ready-spread／ready-bursty D16 有 W5M RTL；任何 W5M 的 RTL drain 證據。

### 2.3 證據分類

主分類維持專案既有的 **`MODEL_ONLY`**。另附 `rtl_anchor_coverage` metadata，列出錨點、seed、可比欄位與 PASS／NOT_AVAILABLE／NOT_EXERCISED 狀態。這只是描述，不是新的證據等級，也不取代任何既有分級。C7 不升級。各個 P 依 v1 判為 SUPPORTED_WITHIN_PROTOCOL 或 NOT_CONFIRMED，並附 `MODEL_ONLY` 的限制說明。

### 2.4 Source hash 管理

v1 的 112 項 source pins 保留為不可變的基線對照，**不得沿用**到改碼後的程式。
新的 runner、共用模組、Main harness、gates 與 audit，另建獨立的 execution source freeze；原本已 pin 的檔案若被改動（例如重構後的 `test_cgof_diagnosis.py`），要逐檔記錄「基線 hash → 新 hash」，不覆寫 v1 的 pins。

### 2.5 沿用 v1 的規則

沿用 v1 §3／§5／§6／§8：cohort 規則、雙帳本、gap、`MECHANISM_NOT_EXPOSED`、missing 不轉 0、不換 seed、不做選擇性重跑、出錯即停並保留 provenance，以及逐 seed release。

## 3. 成本與排程（全部為估計）

### 3.1 已有量測與限制

| 量測 | 數值 | 限制 |
| --- | --- | --- |
| bench：完整 Metrics＋RoleBook，單一 process | 17,718／17,376 cycles/s（CGOF-2:1／Main） | 只跑 200k cycles，未跨 close |
| 7 個 probe 並行（輕量記帳） | 每個 21.87M cycles，耗時 1,148–1,220 s | 記帳較少；沒有同工作量的串行／並行對照，**無法推論是否有資源競爭** |
| 10:18:11Z 快照 | working set 14–20 MiB，high-water 23.6–24.1 MiB | 只是當時的快照，不是完整 runner 的峰值保證 |
| RTL（7291 CGOF） | 每 job 6,332.058 s（`--jobs 2`） | Main 未量測，以此代替 |

完整 runner、8 個 process 並行，以及角色切換後的多窗記帳，都**未量測**。

### 3.2 保守排程（模型與 RTL 不重疊；模型最多 7 個 process、RTL 最多 2 個；seed 逐一 release）

公式：model job ＝ 21,876,819／17,500／3600 ＝ 0.3473 h；RTL job ＝ 1.7589 h；每階段 wall ＝ ceil(jobs／workers) × job 時間；預算 ＝ wall × 1.2（營運保留，不是量測得到的上界）。job-hours 是各 job wall 估計的加總，不等於實測的 CPU-hours。

| 階段 | 串行依賴 | jobs | 批次 | 累計 job-h | wall 線性 | wall 預算 | 硬上限 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E | 工程：共用模組、runner、帳本 B、Main harness、audit、review | — | — | — | — | 人時 13–18 | 24 |
| G0 | E 之後：A2 短 W，M1–M6 | 30 個短 W RTL | — | <1 | ≤0.5（未量測） | — | 2 |
| G1 | G0 之後：A1 replay＋G-EQ-legacy | 20 model | 3 | 6.95 | 1.04 | 1.25 | 2 |
| P | G1 之後：7301 model 30 → A3 RTL 4 → G-EQ → release | 30＋4 | 5＋2 | 17.45 | 5.25 | 6.30 | 8 |
| C | P 通過後：7401 model 30 → A4 RTL 2 → G-EQ（失敗即停）→ 7402–7420 逐 seed | 600＋2 | 每 seed 5，加 1 | 211.87 | 36.48 | 43.78 | 50 |
| 稽核 | 每個 seed 完成後 | — | — | — | — | 人時 0.5 × 21 ＝ 10.5 | 21 |
| G-EQ 覆核／最終報告 | — | — | — | — | — | 人時 1＋4 | 2＋8 |
| **合計** | | 650 model＋6 RTL＋30 短 W | | **約 236** | 機器 42.8 | 機器 51.3＋0.5；人時 28.5–33.5；**約 80–85** | **117** |

未計入預算：
- 若 pilot 發現 correctness bug，要建立新的 source freeze 並重跑整個 P 階段（每次約 6.3 h wall 預算，另加稽核）。
- Main RTL 的實際速度。
- 7 個完整記帳 process 並行時的競爭。

### 3.3 可選項目（不作為預設）

- **8 個 model process**：每個 seed 需 4 個批次，C 階段 model wall 約 27.78 h。8 個 process 並行從未量測，不保證。
- **v2＋CGOF-W5M**：多跑 2 個 RTL jobs（7301 role-switch mixed，CGOF 1:1／2:1），為 CGOF 的新欄位提供 W5M RTL 證據。成本 3.52 job-h、wall 線性 1.76 h、預算 2.11 h。這是另一個備選。
- **isolated 每案例每 seed 只跑一次**：需先通過 T2 gate，並另行核准修改矩陣。

### 3.4 方案 B（每個確認 seed 都有 RTL）

每 seed 跑 7 個 RTL jobs，21 個 seed 共 147 個 jobs。

| 欄位 | 數值 |
| --- | ---: |
| 累計 job-h（147 × 6,332.058／3600） | 258.56 |
| `jobs2` 純線性 wall（÷2） | 129.28 h |
| 逐 seed release 的批次 wall（21 × ceil(7/2) ＝ 84 批） | 147.75 h |
| ＋20% 保留 | 177.30 h |
| 稽核（v1 估計 2 h／seed，未量測） | 42 h |
| 工程（v1 估計） | 8–16 h |
| 最終報告 | 8 h |
| 合計（估計） | 約 235–243 h |

先前寫的 309 job-h／155 h 已含 20% 保留，現在拆成上表的各欄位。

## 4. Seed 清冊

| Seed | 本輪使用方式 | 未來角色 |
| --- | --- | --- |
| 7301 | 工程用途兩次：bench（W5M 前 200k cycles，只量 throughput）；iso（W256，isolated invariance） | 工程 pilot（v1 原本就不納入推論） |
| 7291 | 2 個 model replay，與既有 RTL 對照 | A1；排除於確認之外 |
| 9901 | 5 個 W5M 探索 probe，另有 1 次 smoke 被 timeout 中止 | 排除，不得作為確認 |
| 7401–7420 | 未使用 | 確認用；7401 另作為 A4 |

## 5. 對照兩位 reviewer

| 來源 | 缺口 | v2 的處理 | 仍未補的 RTL 缺口 |
| --- | --- | --- | --- |
| reviewer B1；reviewer-2 缺口 1 | 多視窗、角色、ready、D8 的多 seed 驗證，加上 Main 對照 | 以模型擴展到 20 個 seed × 5 案例 × 3 政策 | Main 的 W5M RTL 只有 6 個；ready-spread／bursty D16 沒有 Main W5M RTL；CGOF 新欄位沒有 W5M RTL；7402–7420 沒有 RTL；drain 行為 `NOT_EXERCISED`（既有錨點沒有 drain>0） |
| reviewer-2 R5 | RR10 | 延後，另行凍結計畫 | 全部 |
| reviewer R1／R2 | C7 不升級；W256 與 W5M 不混用 | 主分類維持 `MODEL_ONLY`，C7 不動 | — |
| reviewer R3 | hash 逐項驗證 | v1 pins 作為不可變基線，另建獨立 freeze（§2.4） | — |
| 兩位的 R6 | 雙帳本、gap | 沿用 v1 §3.2；帳本 B 欄位以 G-EQ-new 驗證 | CGOF 的 W5M 部分 |
| reviewer B2；reviewer-2 缺口 2–5 | under／over、功耗、恢復、N8／N16、系統級 | 不在本計畫範圍內 | 全部 |

## 6. 待 Lead 處理

1. 是否保留 v2 作為獨立備選，或改採方案 B，或只維持 v1。
2. 是否另加「v2＋CGOF-W5M」的 2 個 RTL jobs。

已定案、不再待決：drain 採 cut 後 `ready=1` cleanup（§1 T1a）；RTL 驗證狀態仍為 `NOT_EXERCISED`。
