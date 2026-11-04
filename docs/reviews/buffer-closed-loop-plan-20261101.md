# Buffer closed-loop live／1W／frozen：獨立 screening 計畫（2026-11-01）

本文件是第二階段關閉迴路 screening 的契約與獨立 review 計畫，不是結果或通過證明。只新增本文件；不修改 runner、模型、RTL、spec、manuscript、歷史 artifact 或其他文件，不執行 reset/clean/revert/stash/commit，也不啟動 agents。

角色 provenance：使用者指定 GPT6Astra(high)；本輪 spawn 入口回報 `Unknown model`，依 `AGENTS.md` 的 owner-approved fallback 使用 `group/gpt-6.1-sol`、`high`。這是 invocation routing，不是 backend effective model；任何後續 manifest 若無工具回傳欄位，必須明示 `backend_effective_model=UNKNOWN`，不得冒充。

## 1. 範圍與重用邊界

- 僅做 `MODEL_ONLY` closed-loop：CGOF2（`high_weight=2`）為主測，CGOF1（`high_weight=1`）為負控制；固定 `N=4`、`D=16`、`W=256`、single output 與既有 oldest-first selector。
- 直接重用 `ExperimentalSwitchModel` 的 FIFO/hold/controller、held credit snapshot、CGOF credit refill、`MAIN_TRANSITIONS`、`MAIN_1W_TRANSITIONS`；不新增或改寫 selector。
- 新 runner 與 test 必須是獨立檔案，例如 `scripts/run_buffer_closed_loop_screen.py`、`scripts/test_run_buffer_closed_loop_screen.py`；不得 import `scripts/run_buffer_transition_screen.py`，也不得把 transition-only schema、counts 或 artifact 當成本輪輸入或結果。
- 每個 variant 只 reset 一次建立初始狀態；角色切換、return、drain 均不 reset。`initial classes=all H`，不得預載 Low 或預填目標類別。

## 2. Modes 的精確語義

| mode | 分類器 | 精確語義 |
| --- | --- | --- |
| `live` | accepted Main 四態 | 使用 `MAIN_TRANSITIONS`；H/B_H/L/B_L 依每個實際 closing counts/evidence 更新。 |
| `1w` | accepted Main-1W | 使用 `MAIN_1W_TRANSITIONS`；UP→H、DOWN→L，KEEP/S0 保留原 effective class，且不得自行改表。 |
| `frozen` | all-High 固定分類 | 從 reset 後到觀測結束，四來源 class 恆為 `H`；記錄 close counts/evidence 供稽核，但不套用 transition，不改分類。CGOF2 因此四來源 credit 皆為 2，CGOF1 因此皆為 1。 |

`frozen` 不是「在第一個 role change 時凍結 live 當下類別」，也不是更好的適應策略。依 prior review 的 `CGOF1:1 live/frozen pins 相同、CGOF2 不同`：CGOF1 三 modes 的 scheduler action 必須不受 classifier/class 影響；CGOF2 的 class/credit 可以影響動作，但這不構成效能排序。

## 3. Workload、角色與時間軸

- 固定 `over` offered-load fixture：熱來源每 cycle 產生機率 1.0，其餘來源各 0.05，`ready_p=0.9`；這是 backlog / closed-loop stress fixture，不是容量或 CXL 結果。所有 variant 共用同一 seed、arrivals、descriptors 與 ready sequence。
- 基準角色 `R0`：source0 為熱來源。3W warmup 後，第一角色切換在 `r=3W+phase`，目標角色 `R3`：source3 為熱來源。
- `phase` 固定為 `0, W/4, W-1`。短 noise duration `d` 固定為 `W/2, W, 3W/2`；在 `r+d` 切回 `R0_return`，return 後至少保留 `4W` generation tail。persistent case 不切回，`R3` 至少保留 `4W`。
- 所有 case 使用 policy-independent common generation horizon：persistent `H=r+4W`；短 noise `H=r+d+4W`。生成結束後才進入 bounded drain；drain 沿用同一 `scenario.ready(k)`，不製造 ready=1，也不把 drain 當新 generation role。
- `heavy_work` 由共同輸入在上述 horizon 內實際宣告的熱來源事件數計算，不可由任一 policy 的完成時間回推；每個 variant 都必須在同一 `H` 停止新生成。
- `phase`、`duration`、`r`、`H`、role 排序、period/slot 規則與 `max_drain_cycles=4W` 都寫入 config/hash。drain 未清空時保留 backlog 並標記 right-censored，不延長該 policy 的觀測。

## 4. Event 與 generation-role cohort

- 每次 generation 時以當下 role interval 指定 `role_id`（`R0`、`R3`、`R0_return`）；request 的 role 從 generation 帶到 acceptance、fire 與 drain，完成時不得依 current role 重標。request 在 `R0` 生成、於 `R3` fire，仍計入 `R0`。
- 正式 measured events 為切換/return：`[role_change, next_change)`；`R0` 初始 warmup 只作 `CONTEXT_ONLY`，不計 adaptive benefit。短 noise 的 `R3` event 可因 `d<W` 而合法 `INCOMPLETE`；return event 至少 4W。
- 每個 event 記錄：
  - `role_change_cycle`、`end_exclusive`、`role_id`、`hot_source`、`observations_cycles`；
  - 實際 close 的 `close_cycle`、`B[4]`、`S`、`evidence[4]`、old/new classes；
  - `first_support_close`（target High 用 UP、Low 用 DOWN，僅限該 event 內實際 close）；
  - `first_effective_visible`、`effective_change_count`、`already_target`；
  - `first_stable_visible`、`stable_suffix_start`、`post_settle_cycles`；
  - per-source generated/accepted/fired/censored 與 status/reason。
- `close` 是 closing edge；新 class 只在 `close+1` 可見。若 `close+1 == event_end`，只能記錄終點 snapshot，`post_settle_cycles=0`，不得補一個 W。
- `first_stable_visible` 必須是可維持到 event end 的 stable suffix 起點；中途離開後再回來只取最後 suffix。`post_settle_cycles=end-s` 只用真實已執行的 cycles。
- event 的 `status=COMPLETE` 僅表示 target hot source 在該 event 內有至少 W 個 post-settle observed cycles；不代表效能改善。W 不足、未 settle、未見 target class、right-censor 都記 `INCOMPLETE` 並附原因。cold-source rows 可以各自 `INCOMPLETE_OR_NOT_APPLICABLE`，不阻擋 hot-source event 的觀測狀態。
- drain 是 completion phase，不是 role-switch event；在 drain 完成的 request 仍歸屬其 generation role，另記 `completed_in_drain=true`。

## 5. Latency 與最小 metric

- 本輪明確只量 generation-role cohort latency，不發明 latency-recovery threshold：輸出 `latency_recovery="NOT_DEFINED_THIS_ROUND"`，另以真正已 fire 的 generation cohort 報告 `G→A`、`A→F`、`G→F`。
- 每 role × source × stage 記錄 count、mean、P50、P95、P99、max；quantile 採 nearest-rank，空樣本所有統計為 `null`，不把未 fire、no-demand 或 censored request 當 0。right-censored count 另列。
- 全 run 與每個 event 記錄 generated、accepted、fired_active、fired_drain、unaccepted_at_cut、accepted_unfired_at_cut，並核對 generated=accepted+producer backlog、accepted=fired+FIFO occupancy。
- ready/wall gaps 重用 `followup.Gaps` 概念：per source 的 initial、inter-service、empty-terminated、right-censored episodes，同時保留 wall cycles 與 eligible-ready opportunities；不可把兩者混算。
- FIFO/backlog 記錄 per-source occupancy/backlog count/mean/max/histogram、held cycles、output-stall cycles、avoidable bubbles；不把 drain completion 當長期穩定證據。
- class timing 與 request latency 分欄。`class_settle` 可能早於、等於或晚於 G→F；不得把 settle 當 latency recovery，也不得由 flips 少、zero flips 或 already-target 推論 benefit。

## 6. 配對與負控制

- 對同一 `(seed, case)`，六個 variant（2 weights × 3 modes）必須有相同 `scenario_sha256`、arrival sequence hash、ready sequence hash、role schedule hash、common horizon 與 descriptor multiset；任何 mismatch 是 harness failure，不是可比較差異。
- 每個 variant 的 `action_trace_sha256` 只包含 ready、input valid/descriptor、accepted、fired source/descriptor、held source/descriptor 與 cycle index，不含 class/classifier 名稱。CGOF1 live/1W/frozen 的 action trace、計數、G→A/A→F/G→F、gaps、FIFO/backlog 必須逐項相等；class trajectory 可以不同，但不影響 selector。若任一行為不同，標記 classifier leakage 並停止該 control。
- CGOF2 三 modes 只作 descriptive comparison；可記錄差異與 pinned smoke fixture，但不做統計 ranking、CI、p-value、winner 或普遍優勢宣稱。CGOF1 的 equality 也不能升格成 CGOF2 行為保證。

## 7. 必要反例 / tests

全部是施行後的定向 fixtures；`INCOMPLETE` 或 no-demand 是觀測狀態，不是 execution failure。

| 反例 | 必須抓到的錯誤 |
| --- | --- |
| arrivals/ready mismatch | 改一個 descriptor、ready bit 或 horizon；runner 拒收並顯示 hash/sequence 差異。 |
| generation role after switch | R0 生成、R3 fire 的 request 必須計入 R0；以 fire-time role 實作必須失敗。 |
| drain/right-censor | drain budget 用盡仍未 fire；G→F/分位數為 null，censored count 保留，狀態為 INCOMPLETE，不丟資料、不轉成 0。 |
| no-demand latency | 某 role/source 零 generated；count=0，mean/P50/P95/P99/max 全 null，不能除以零或填 0。 |
| frozen not all-High | 用必然 DOWN 的 counts；frozen 每 cycle 仍 all `H`，且不套 transition；live/1W按各自表更新。 |
| 1W table wrong | 對四個 Main state × 四個 evidence 直接比對 `MAIN_1W_TRANSITIONS`；替換成 Main 或自行簡化必須失敗。 |
| last-close no extra W | 只有 `T` 個實際 cycles，最後 close 的 visible=`T` 只有 0 dwell；不得產生 `T+W` 或虛構 post-settle。 |
| zero flips | target 已在起點或全程未 flip；不得產生 recovery、benefit 或「較快」結論。 |
| CGOF1 class leakage | CGOF1 讓 class/credit 改變任一 action；三 modes action trace 不等即失敗；另以高權重 fixture 驗證 CGOF2 可以不同。 |
| overwriting evidence | 新輸出目錄使用 exclusive create；第二次輸出不存在時必須失敗且不覆寫舊檔、不留下半成品。 |
| settle/latency 混用 | class settle fixture 與 G→F fixture 分開；任何把 settle 寫成 user latency recovery 的輸出必須被 assertion 拒絕。 |

## 8. Schema、hash、provenance 與命令

建議 schema：`cxl-buffer-closed-loop-screen-v1`；manifest：`cxl-buffer-closed-loop-manifest-v1`。新 schema 不與 transition-only schema 混用，舊 consumer 遇到未知版本必須拒收。

最小 payload：

```json
{
  "schema": "cxl-buffer-closed-loop-screen-v1",
  "scope": "MODEL_ONLY",
  "contract_version": "cxl-buffer-closed-loop-v1",
  "identity": {"seed": 6101, "cohort": "smoke", "window": 256, "n_src": 4, "depth": 16},
  "workload": {"profile": "over", "phase": 0, "duration": null, "role_schedule": []},
  "inputs": {"scenario_sha256": "", "arrival_sha256": "", "ready_sha256": "", "role_schedule_sha256": ""},
  "variants": [{"policy_id": "CGOF2_live", "classifier": "live", "high_weight": 2,
               "execution_status": "COMPLETE", "events": [], "roles": {}, "metrics": {},
               "censoring": {}, "action_trace_sha256": ""}],
  "pairing": {"input_equal": true, "cgof1_control_equal": true, "cgof2_descriptive_only": true},
  "latency_recovery": "NOT_DEFINED_THIS_ROUND",
  "limitations": []
}
```

Hash 規則：canonical JSON（UTF-8、`sort_keys=True`、compact separators），hash 對不含自身 hash 欄位的 payload 計算；另存 raw file SHA256。必須保存：runner/test、`experimental.py`、`diagnosis.py`、`common_ctrl_model.py`、`fai_main_model.py`、`revision_baselines.py`、`followup.py` 的 source hashes；Git HEAD；dirty source snapshot；Python/pytest 版本；實際命令、run id、exit status、stdout/stderr、輸出位置；requested model/effort、fallback、`backend_effective_model=UNKNOWN`（若無回應欄位）。輸出使用新的 artifacts 目錄與 exclusive create；before/after source hash 不同即失敗。

後續施行命令（先實作 runner/test；本計畫未執行）：

```bash
source scripts/wsl_env.sh
python -B -m pytest -q scripts/test_run_buffer_closed_loop_screen.py \
  refc/tests/test_experimental.py refc/tests/test_diagnosis.py
python -B scripts/run_buffer_closed_loop_screen.py --window 256 --depth 16 \
  --seed 6101 --max-drain-windows 4 --self-check \
  --output <new-directory>/smoke-6101.json
python -B scripts/run_buffer_closed_loop_screen.py --window 256 --depth 16 \
  --seeds 6101 6102 6103 6104 6105 --max-drain-windows 4 --self-check \
  --output <new-directory>/exploration-6101-6105.json
```

先完成單 seed 6101 wiring smoke，再跑 6101–6105 exploration；不做 20-seed confirmation、W5M、RTL/PPA、formal/CDC、CXL response 或 application 推論。

## 9. INCOMPLETE 與限制

- `execution_status` 回答 runner 是否完成、輸入是否一致、是否發生 selector/class-leakage；`evidence_status` 回答 event/drain 觀測是否足夠；兩者不可合併。
- `INCOMPLETE` reasons 至少區分：`NO_TARGET_CLASS`、`NO_STABLE_SETTLE`、`POST_SETTLE_LT_W`、`RIGHT_CENSORED_AT_HORIZON`、`RIGHT_CENSORED_AT_DRAIN_BUDGET`、`NO_DEMAND`。合法 INCOMPLETE 不是測試失敗。
- 本輪只支持 synthetic closed-loop 機制與 cohort latency；不支持 CGOF2 統計優勢、frozen 較佳適應、latency recovery、CXL/application benefit、production W5M 或 RTL 行為。
- 現有 `ExperimentalSwitchModel.frozen` 在 close 後寫回 all-H；語義上等於固定 all-H，但 runner 仍須每 cycle 斷言四來源皆 H，避免把「凍結當下狀態」誤當 frozen。現有 `class_changes` 的 cycle 欄位也不能直接當成 `effective-visible`；新輸出必須分開 `evidence_close_cycle` 與 `effective_visible_cycle`。

## 10. Review snapshot（非執行證據）

本文件建立時 HEAD=`99400ded42cc63c3b206bd5d13f51d36344b2689`，工作樹已有既有 dirty changes。以下只記錄閱讀時的 source snapshot；施行時必須重新 hash。

| Source | SHA256 |
| --- | --- |
| `refc/cxl_model/experimental.py` | `225f549839e8a267fe5c2b010f87a8e64bd0c59291d011869906362dd563330e` |
| `refc/cxl_model/diagnosis.py` | `1b817ceda2a41806f17fee4ebd21da5637b3c5798e19b3716a766e11d3622619` |
| `refc/cxl_model/common_ctrl_model.py` | `f35544ad94266029210f8884c01a97bd747958c7531868b17bfad71556a797d4` |
| `refc/cxl_model/fai_main_model.py` | `7f2bbdfb9b3ba20d82f0965136f1458efebf157dc844364aa40696aa6ad8c381` |
| `refc/cxl_model/revision_baselines.py` | `2fe8204bb992df429ca85b535dd43a692ce4839c4ae1d0f899e927fe140b4d81` |
| `sim/performance/followup.py` | `090e750c2d6b96e8b085907f3f0d32f7659b8e04066490932e227d8bc7d73d7f` |
| `refc/tests/test_experimental.py` | `a51afda0f013a49fe51a2a1ae95314eaf2dc1aa43058d48d0096abd1dc26bb88` |
| `refc/tests/test_diagnosis.py` | `40fc2476db1012f084a26475ea35331e90e04c6cc352b2eb7b393a1f25fb69ae` |

本次只做唯讀來源核對與計畫撰寫；未執行新 runner、tests、RTL、EDA、W5M 或 exploration matrix，故不宣稱任何 performance/PASS 結論。
