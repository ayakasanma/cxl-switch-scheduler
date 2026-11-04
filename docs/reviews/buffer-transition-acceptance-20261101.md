# Buffer transition-only screening：獨立驗收計畫（2026-11-01）

本文件是契約與驗收設計，不是 runner 通過證明。以本次使用者契約為準，延續 `evidence-review-fixes-plan-20261101.md:77–83` 的後續獨立 MODEL_ONLY 任務；P0–P4 不重開。只新增本文件，主線負責修改 runner/tests；不派 agents、不修改 production、spec、歷史 artifacts、manuscript 或其他文件，不執行 reset/clean/revert/stash/commit。

角色要求為 GPT6Astra(high) 計畫／獨立 reviewer、監督者派 auto/deepseek 執行；本 reviewer 未啟動任何委派，亦無可驗證的實際模型／effort 回應欄位，不將使用者指定值冒充執行 provenance。主線應保留其實際 agent/model/effort 紀錄。

## 讀取範圍與實作接點

已讀 `AGENTS.md`、指定計畫段落、draft `scripts/run_buffer_transition_screen.py` 及其 `scripts/test_run_buffer_transition_screen.py`；核對 `fai_main_model.py` 的 `threshold_evidence`、`MAIN_TRANSITIONS`、`EFFECTIVE_CLASS`，`revision_baselines.py` 的 `MAIN_1W_TRANSITIONS`，以及 `fai_alg2_model.py` 的 `ALG2_TRANSITIONS`、`ALG2_EFFECTIVE_CLASS`。另核對既有批准／spec／狀態文件及 `ADAPTATION_RESULTS.md:60,62,108` 的證據邊界。

主線最小接點為 runner 的輸入生成、重播、event metrics、schema/hash/CLI/self-check，以及既有 test 中 `run_case/run_screen/self_check` callers 與舊 schema 斷言。共享 threshold/tables/maps 只重用，無需改動；本次搜尋 scripts/refc/docs/reviews 未找到其他 runner consumer。沒有必要新增套件、RTL、config 或 exports。舊 evidence-only fixtures 可作獨立定向 control，不能冒充新 role/phase 矩陣。

## 最小驗收流程與通過條件

1. **凍結單次輸入並核對 service conservation。** W=256，N=4；cycle 0 是 reset 完成後第一個可觀測 cycle，所有來源 Main/1W=`H`、Alg2=`STABLE_HIGH`。先重播 3W baseline warmup，之後不再 reset。source0 sparse/heavy 的 period16 service counts 分別為 `[1,5,5,5]`／`[13,1,1,1]`；須記錄具體 slot 排序與 period 起點／role 切換時的索引規則，counts 比例不能唯一決定混合窗。每 cycle 最多一個 source fire，先產生共同外生 service sequence，再計算每窗 `B[4], S`；驗證非負整數、`S=sum(B)<=W`，closing fire 包含在內，窗後清零。完整 baseline 窗應為 `[16,80,80,80]`／`[208,16,16,16]`、S=256。逐來源呼叫既有 `threshold_evidence(4,B[h],S)`；不得由 phase、role 或期待的 transition 預填 evidence。這是 synthetic service-role input，不是 arrival/demand、scheduler 選出的 service 或 closed loop。
2. **先單一接線 case，再覆蓋完整小矩陣。** phase=`0,64,255`，role change 在 `r=768+phase`，新 role 自 cycle r 的 fire 起生效。兩方向 sparse→heavy（target Low）、heavy→sparse（target High）；短 noise duration=`128,256,384`，在 `r+duration` 返回 baseline；persistent 至少 1024 cycles。最小主矩陣為 `3 phases × 2 directions × (3 noise + 1 persistent)=24` 個共同輸入，三 variants 共 72 條 replay，controls 另計。noise 的進入與 return 是兩個不同 event，各自計量；return 後實際重播足夠長的 baseline（最小固定方案可取 4W），不能把尾端補算成觀測。persistent 建議先固定恰 4W，任一延長需在三 variants 共用的輸入生成時決定，不可依各 variant settle 補跑不同長度。若有 seed，先記單 seed 接線，再宣告探索 seed；若採固定 slot 序列則記 deterministic/seed=null，不能捏造多 seed 證據。
3. **重播 shared tables 並稽核同源性。** 同 case 三 variants 的整個 warmup、active、return/tail 的所有 B/S、closing cycles、來源索引都逐項相同，不能只比 source0 或總 S；保存共同 input hash 並核對 canonical counts 完全相等。每窗四來源皆經原表更新，effective mapping 各用原定義。heavy baseline 的 source0 須由 warmup 自 allH 走到 Low，不能直接 preload Low，也不能把 allH + UP 誤充 heavy→sparse。有效 input 的 evidence 及 state replay 與共享函式逐列吻合才算 harness PASS。
4. **依下節的 event 區間計量並驗證五個反例。** 每個 event 都有 first support close、first effective-visible、stable settle、post-settle observed cycles 與 reason；反例中的缺觀測、未 settle 或合法過濾應得到明確狀態，不應造成 execution failure。新實作須留下最小有意義 tests/self-check；先跑 `scripts/test_run_buffer_transition_screen.py` 與 runner self-check，再驗收一次 W256 完整小矩陣與新輸出。缺證據只記 NOT_RUN/PENDING，不以舊 evidence-only tests 全過代替。
5. **驗收輸出與可重現性。** 使用不同於舊 evidence-only v1 的 schema/contract version；保存 W、N、role/phase/duration、reset/warmup、slot 排序規則、實際 cycles/counts 長度、每個 close 的 B/S/evidence/state/effective、event 邊界與 metrics。manifest 記錄實際執行命令、環境／工具版本、seed 或 deterministic、Git HEAD、dirty source snapshot hashes、runner/test/threshold/tables/maps 的來源路徑及 SHA256、輸入與結果 hash、實際 agent/model/effort（未知明示 UNKNOWN）。hash 需定義 canonical serialization 與排除自身 hash 欄位，並能重算；HEAD 單獨不足以識別 dirty source。另存新結果、拒絕覆寫歷史檔；舊新 schema 不可默默混用。所有結果固定 `scope=MODEL_ONLY`、`latency_recovery=NOT_MEASURED`；execution/harness status 與 event completeness 分欄。

## 時間與 event metric 的精確口徑

- 第 i 窗（i 從 0 起）closing index=`(i+1)W-1`，表更新後的新 state/effective visible=`close+1`。保留 close 及 visible 兩欄，不能把兩者視為同一 cycle。
- 實際服務序列長度為 T 時，只觀測 `[0,T)`。若保存的是 K 個完整窗 counts，且沒有另行實際重播尾端，T=`K*W`；若逐 cycle 重播部分尾窗，T 為真實長度，部分窗不得提前 classify。最後 close 可有 visible=T 的邊界紀錄，但該 state 在本次觀測中有 0 cycles，不能算 observed attainment 或補上 W。
- 每個 event 使用 `[a,e)`：a 為 role change cycle（初始 baseline 若輸出則 a=0），e 為下一次 role change 或 T，取較早者。noise 的 target event 不能借用 return 區間湊 post-settle cycles；同理 return 不能借用 noise 之前的 target 命中。
- `first_support_close` 是 event 中第一個 `a<=close<e` 且 evidence 支持該 source0 target 的 close：Low 用 DOWN，High 用 UP。必須來自實際混合窗 counts，不必等到完整新 role 窗。沒有則 null；已有 target 也不補造支持 close。若 close+1=e，只是邊界更新，沒有 event 內的新 state 觀測。
- `first_effective_visible`：若 cycle a 已是 target effective，記 a（初始 baseline 記 0），標記 `already_target=true`，不算新 flip；否則取 event 內首次實際 target-visible cycle。真實 effective flip 由前後 effective 不同判定，不能由 target 命中次數推導。已 target 的 state 可能是 Buffer，這不等於 stable。
- `stable_settle` 是最早的實際觀測 cycle s，使 `[s,e)` 每個 cycle 均保持 **target stable state**；Main/1W 只認 H/L，Alg2 只認 STABLE_HIGH/STABLE_LOW。中途離開後再回來必須從最後的持續 suffix 起算，不能取第一次 stable hit。若從 a 起就 stable 且維持到 e，記 a；有效 target 但一直 Buffer 時為 null。
- `postsettle_observation_cycles=e-s`，s 為 null 時記 null 並給原因；終點邊界 state 可另記 0 observed cycles。只有真實 stable suffix 至少 W cycles 才為 COMPLETE，少於 W 或未 settle 為 INCOMPLETE。建議 reasons 區分 `NO_TARGET_EFFECTIVE`、`NO_STABLE_SETTLE`、`POSTSETTLE_LT_W`；它們不是 process failure。noise 被 Main 過濾、target 未達，是合法分類觀測，不要求所有 72 replay 的所有 events 都 COMPLETE。
- 各時間可另附相對 a 的 classifier timing delta；不命名為 latency recovery。零 flip、先 effective、較短 settle 或 INCOMPLETE 都不能推論 latency benefit，亦不能由兩次支持 close 宣稱任意 phase 固定 2W recovery。

## 五個具體風險／反例（驗收 fixtures，不是本次實跑結果）

| # | 輸入與預期 | 必須抓出的錯誤 |
| --- | --- | --- |
| 1 | **phase255 的混合窗**：取明示示例 slot 排序 sparse=`[0,1,1,1,1,1,2,2,2,2,2,3,3,3,3,3]`、heavy=`[0×13,1,2,3]`，使用全域 `cycle%16`。sparse→heavy 在 r=1023 切換時，closing cycle 1023 的新 slot 仍是 source3，因此該窗 B=`[16,80,80,80]`、S=256，source0 evidence 仍 UP。下一 close1279 才 DOWN；1W/Alg2 首 effective Low=1280，Main=1536（兩次 DOWN），不是 r+2W=1535。 | 不得預填「phase 所在窗已 DOWN」，不得忽略 closing fire 或將 close 當 visible；slot 排序不同時應由其真實 counts 求值，不能硬套此示例數字。 |
| 2 | **最後 close 沒有免費尾窗**：allH 的定向 replay，實際只有兩個完整 heavy 窗（512 cycles），source0 產生 DOWN,DOWN。Main 的 L、Alg2 的 STABLE_LOW 在 visible512 才成立；T=512，本次沒有任何 stable-L observation。 | draft 的 `(len(rows)+1)*W` 會將 T 錯寫 768，虛構 256 cycles 並誤標 COMPLETE。尾窗不足一整 W 也須按實際長度計算，不能向上補齊。 |
| 3 | **initial/already-target 與假雙向**：allH + 持續 sparse，source0 effective High 從 cycle0 就存在，不能報 first High=256 或新增一個 flip。真正 heavy→sparse case 必須先重播三個 heavy baseline 窗，source0 在 r 前已 stable Low，UP 後才計量新 High。Main 過濾 noise 後 return 時若一直 stable baseline，return 的 first effective/settle 應從 return cycle 計，不重用 cycle0。 | 初始狀態未入 metrics、warmup 被跳過、首次 target 命中冒充 flip，以及拿 allH+UP 當 upward adaptation 的錯誤。 |
| 4 | **第一次 stable hit 不等於 settle**：allH 的定向 source0 evidence DOWN,DOWN,UP,UP,DOWN,DOWN，可由六窗 heavy,heavy,sparse,sparse,heavy,heavy counts 產生；若 metric fixture 以 `[0,1536)`、target Low 檢查 Main，L 曾在512成立，但1024離開，1536才重新 L（不在觀測內），因此沒有維持到終點的 stable-L suffix。正式 role 矩陣則應依 role changes 分割 event，不能合併成一個 target 事件。 | draft 取第一個 stable row=512 的算法會假報穩定；同一錯誤也會讓短 noise 借用 return/tail 時間，將應 INCOMPLETE 的 event 判 COMPLETE。 |
| 5 | **單 DOWN + KEEP／S0 controls**：從 allH，第一窗用 `[208,16,16,16]`、S256；後續至少4W 分別用 `[64,64,64,64]`、S256（KEEP）或全0、S0。兩個 controls 均由 service/counts 推 evidence，三 variants 共用。Alg2 在256進 BUFFER_P_LOW、effective Low，後續永遠 Buffer；Main 在256為 B_H/High，512回 H/High；1W 在256成 L/Low 並保持 stable。 | Alg2 effective Low 不得當 stable Low；KEEP/S0 不得套用 Main 的取消規則。Alg2 為合法 INCOMPLETE/NO_STABLE_SETTLE，Main 對 Low 未達亦合法；不能因它們 incomplete 將 execution 判失敗，也不能稱為低延遲優勢。這是 control，並非 noise 後返回 sparse 的角色實驗。 |

## 審查快照與限制

讀取時 HEAD=`99400ded42cc63c3b206bd5d13f51d36344b2689`；工作樹已有大量既有變更。以下為本次讀取的 SHA256，不代表主線修改後版本；新驗收須重新記錄實際執行 sources。

| Source | SHA256 |
| --- | --- |
| `scripts/run_buffer_transition_screen.py` | `e84e8582367ae3534ab333f1ba30b8d578c1025a02edf7f044327633a711bc54` |
| `scripts/test_run_buffer_transition_screen.py` | `9412415dbec898903f45d44019d4a154eab4708bbfee537998f18578a7da53b1` |
| `refc/cxl_model/fai_main_model.py` | `7f2bbdfb9b3ba20d82f0965136f1458efebf157dc844364aa40696aa6ad8c381` |
| `refc/cxl_model/revision_baselines.py` | `2fe8204bb992df429ca85b535dd43a692ce4839c4ae1d0f899e927fe140b4d81` |
| `refc/cxl_model/fai_alg2_model.py` | `bd97a7fcfaa53326dd9b737f088e9c371ba5288b6df7acaac08c02361fbea070` |

本次完成靜態來源／契約核對與表格手推；未執行 runner、tests、RTL、closed-loop 或新矩陣，未宣稱 implementation PASS。歷史 adaptation 證據只支持 classifier timing 與 latency recovery 必須分開，不能由本文件升級為 Buffer 效能結論。
