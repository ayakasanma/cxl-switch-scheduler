# 確認性實驗啟動紀錄（v2 confirmation campaign）

狀態：`RELEASED_MODEL_PHASE`。本紀錄只授權模型階段與 seed 7401 的 A4 RTL 錨點；
其餘十九個 seed 逐一釋放，規則見下方「釋放與停止條件」。

## 依據

| 文件 | SHA-256 |
| --- | --- |
| `docs/reviews/dynamic-role-switch-plan-v2-lean-20261103.md` | `3a5ff663c15d5b573dfcd847d7c059e471e0a3435e786382bc9efe144188b051` |
| `docs/reviews/dynamic-role-switch-plan-v2-lean-20261103-summary.json` | `ec8c25d2792e9e7fdaf04bcc9cb7181fe8a84dc93139319950bdce55a2d94249` |
| `docs/reviews/dynamic-role-switch-v2-cost-refreeze-20261104.json` | `4d21ab744feac973f3ba8c6f92990a1ccbc3926b28cac4fffee4d194516a7319` |
| `scripts/run_dynamic_role_switch_pilot.py` | `326358a5b69b6732b365fe3c45efb76cc4d362e162b3ffb45b736496ea49e15d` |
| `scripts/run_rtl_diagnosis.py` | `4283478aed9fafdcc0cd37ac8e6a64b213793e68a2d4723e07ca07921afd9587` |
| `scripts/analyze_dynamic_role_switch.py` | `5d3386f034b43d403aae1903afbff6a8fd5531f0b03d043cc27d3729b7b7911b` |

來源 pin 集合沿用 `run_rtl_diagnosis.source_paths()` 的 48 個檔案；runner 在開跑時把整組
雜湊寫進 `cohort.json`，RTL 端則寫進 `diagnosis_scope.json` 的 `source_hashes` 與
`source_hashes_after`。

## 種子與矩陣

- 確認組：`7401`–`7420`，共 20 個。排除 `7291`（A1 重播）、`7301`（工程 pilot）、`9901`（探索 probe）。
- 每個 seed 30 個模型 job：5 個案例（`multi-window`、`role-switch`、`ready-spread`、`ready-bursty`、`depth8-bursty`）× 3 個政策（`FAI-inspired`、`CGOF(1:1)`、`CGOF(2:1)`）× 2 條 lane（mixed、isolated），W5M、4 個視窗、heavy work 17,500,000、`profile=near`、N4。
- 端點：mixed lane、generation-time Sparse 全期 G→F nearest-rank P99。
- 統計：P1（role-switch，Main − CGOF(2:1)）、P2（role-switch，CGOF(1:1) − CGOF(2:1)）、P3（multi-window，Main − CGOF(2:1)），exact 單尾符號檢定、Holm step-down、FWER 0.05、margin 1 cycle，另附 10,000 次 paired bootstrap（僅描述）。
- 證據等級：`MODEL_ONLY` 統計加 RTL 錨點。C7 維持 `SINGLE_SEED`，本輪不升級任何 claim。

## 成本

measured basis 見 cost refreeze rev2：單 process 16,785 cycles/s（0.362 h/job）、7 process 13,547（0.449 h/job）。

| 階段 | job 數 | 機器時間 |
| --- | --- | --- |
| 模型（20 seeds × 30） | 600 | 38.6 h（7 workers，含 20% 保留 46.3 h） |
| A4 RTL（seed 7401，Main role-switch mixed+isolated） | 2 | 預算 4.2 h（cost rev2 的 `a4_rtl_h`）；實測預期 2.1 h（A3 四 job 兩批 15,328 s，單批 2.13 h） |
| 逐 seed 稽核 | — | 機械步驟 0.5 h/seed；預算 18 人時（cost rev2 的 `audit_person_h`） |

硬上限沿用 frozen caps：model job 1.5 h、RTL job 3.0 h、seed 4.0 h、simulation total 60 h、campaign 80 h、overall 95 h。任一上限被觸及就停跑並改版，不以拉高平行度追進度。

### 上限歸屬

- `seed_simulation 4.0 h` 套在單一 seed 的模型區塊：30 個 job、7 個 process，實測 2.25 h。
- `rtl_job 3.0 h` 套在每一個 A4 job：單批 2.13 h。
- A4 不計入 `seed_simulation`。理由是 cost rev2 把 600 個模型 job 與 `a4_rtl_h` 分成兩列，並另外給了 RTL 專屬上限；把錨點算進 seed 區塊會讓兩列預算重複計一次。
- 若把 `seed_simulation` 讀成「模型加錨點」，seed 7401 為 2.25 + 2.13 = 4.38 h，超過 4.0 h，確認階段要在 7401 之後停下並重新凍結。這個讀法與 cost rev2 的分列不一致，因此本輪不採用；上限本身沒有調整。

## 釋放與停止條件

1. A3 的四個錨點先過同規格 G-EQ（新 RTL 對 `20261104T031500Z_a3spec` 的模型重播），
   才開始 seed 7401。
2. seed 7401：模型 30 job → A4 RTL → 再比一次 G-EQ。
3. 7401 通過後逐一釋放 7402–7420；每個 seed 跑完先做 per-seed audit（`--seeds <seed>`），
   通過才釋放下一個。
4. 停止條件：任何 job `FAIL`、牆鐘超過上表任一個上限、模型或 RTL 執行期間來源雜湊
   變動、G-EQ 未達 4/4（A3）或 2/2（A4）。
5. 模型與 RTL 不重疊執行；同時最多 7 個模型 process、2 個 RTL job。

## 尚未納入本輪

- P1：under／over 負載配對、CGOF 閘級功耗、`latency_recovery` 與 N8／N16 有限工作。
- RTL drain：A3 的 `depth8-bursty` mixed 錨點在 cut 時仍有佇列，自然 drain 2 個 cycle，
  `fired == accepted == 18,815,149`，模型重播同為 2。清理路徑走過一次；把 cut 放進長
  backlog 的定向錨點還沒跑，那部分維持 `NOT_EXERCISED`。注意
  `scripts/run_dynamic_role_switch_a3.py` 把 `drain=NOT_EXERCISED` 寫成常數，本次
  `a3_scope.json` 因此與逐錨點結果矛盾；修這個常數要等本輪來源凍結結束。
- P2：CXL.mem 端到端與應用程式 slowdown，維持 scoped limitation。
