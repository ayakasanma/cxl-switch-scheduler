# 證據審查修正計畫：最小可執行版本

日期：2026-11-01。交接對象：`auto/deepseek`；監督者逐階段驗收。本次僅建立本計畫，未修改實作、未派工。

基準：workspace `C:\Users\USER\Documents\Coding Space\CXL\cxl-scheduler`，HEAD `99400ded42cc63c3b206bd5d13f51d36344b2689`，含既有未提交及未追蹤檔案。下列行號對應本次調查版本，執行時以函式名重新定位。已閱讀 `AGENTS.md`、相關實作與測試、指定文件及引用對話「6Pro審查建議」；對話建議須經本地證據核對，不能視為已實作。

## 目標、非目標與已存在的修正

本 patch 僅修正實驗契約、ordering 接線、quota 資格判定、trace 觀測及統計標籤。保持現有 selector、credit commit、Buffer 狀態轉移及預設政策不變。不得把 MODEL_ONLY、W256 smoke、single-seed 或 scheduler RTL 證據升級為 production 統計確認、一般延遲優勢、CXL response latency、memory bandwidth、PPA 或全系統效益。原「早停掩蓋重大終局損失」強假說已在對話中撤回；新實驗應量測，不預設結論。

| 已修／已存在，勿重做 | 本地證據 |
| --- | --- |
| eligible RR selector、fire-only pointer、held grant 與 credit commit | `rtl/experimental/cxl_cgof_sched.sv:257`、`:272`、`:308`、`:363`、`:389`；`refc/cxl_model/experimental.py:118`、`:193` |
| Model ordering 與 oracle 已支援兩種順序 | `refc/cxl_model/diagnosis.py:121`、`:136`、`:166`；`sim/experimental/test_cgof_sched.py:82`、`:130` |
| 兩種 ordering 都保留 timestamps；不是不同硬體成本邊界 | `rtl/experimental/cgof_unit_top.sv:65` |
| Generation-time role、跨窗／drain cohort 已存在；closing-cycle 歸屬已修 | `refc/cxl_model/diagnosis.py:364`、`:1102`；`sim/experimental/cgof_diagnosis_traffic.py:154`、`:201` |
| Held refill／re-entry 定向檢查已存在 | `sim/experimental/test_cgof_sched.py:599`、`:909`；沿用，不重寫 scheduler |
| 審查提及的三個依賴在 workspace 都存在 | `sim/common/traffic_trace.py`、`sim/performance/followup.py`、`sim/switch_top_fai/fai_stream.py`；問題是缺檔時靜默略過，不是目前缺檔 |

`docs/IMPLEMENTATION_PLAN.md:1` 是既有 RTL M1–M4 計畫，不是外部審查修補草案；不得覆寫。保留歷史 evidence、handoff manifest、hash 與已發表數字。

## P0：required-file 與 arrival 契約（先做）

修改位置：`scripts/run_diagnosis.py:51 source_paths()`、`:74 source_hashes()`、`:189 freeze_manifest()`；`scripts/run_arrival_phase_diagnosis.py:49 ArrivalPhaseScenario`、`:102 _source_hashes()`、`:165 run_pair()`、`:300 _input_pairing()`、`:362 run_matrix()`；`refc/cxl_model/diagnosis.py:1244 DiagnosisLane`、`:1467 run()`、`:1706 run_lane()`。

1. 必要來源採明確清單，缺少任一檔案立即報完整 missing paths 並非零退出；驗證應在建立結果目錄／執行工作前完成。刪除 `is_file()` 靜默過濾；涵蓋 arrival runner/test 的實際依賴。缺檔測試只刪除 temporary fixture，不能動真實來源。
2. 為 arrival 增加明確、可選的 common-generation 執行契約；shared runner 的舊呼叫預設保持原行為。`fixed_horizon=True` 目前仍會因 Heavy 完成而 break，不能當成此修正。
3. 共同 generation horizon `H` 與政策無關，至少涵蓋全部有限 Heavy release 與 Sparse support；生成區間為 `[0,H)`。Heavy 提前完成仍繼續生成宣告的 Sparse 工作。記錄 `generation_end_exclusive=H`、實際 Heavy 最後 fire cycle、完整 cohort 最後 fire cycle，三者不可共用 `cut_cycle`。
4. `k>=H` 不再生成，但繼續 `scenario.ready(k)`，直到 producer pending 與 FIFO 都清空。設獨立 bounded drain；逾時保留 generated/accepted/fired/uncompleted 與失敗狀態，未完成的 endpoint 為 null。禁止以 forced-ready drain 冒充同一實驗。
5. 重用 `CohortBook`，保留全生成 cohort 的 G→A、A→F、G→F。實際 emitted Sparse multiset 必須等於宣告 support；目前 `sparse_work_sha256()` 只證明理論 workload。混合／隔離配對核對完整共同 Heavy arrivals 與 ready 序列，跨 phase 核對相同 Sparse work multiset；不得只比最短 prefix、硬寫 true，或對空成功集合回報通過。
6. 保存對齊 post-edge cycle 的累積 Heavy fires，計算 `lag(k)=F_isolated(k)-F_mixed(k)`，含最大 lag、終點 lag、恢復 cycle；可存可無損重建的 change points。對較早結束 lane 延續其最終累積值至共同觀察終點。恢復定義為最後一次正 lag 後首次回到非正值；從未正 lag 或觀察期未恢復均為 null，另列原因／censoring。producer pending 與 FIFO backlog 分開記錄。

驗收／tests：擴充 `scripts/test_run_arrival_phase_diagnosis.py`、`scripts/test_run_diagnosis.py`、`refc/tests/test_diagnosis.py`。涵蓋 Heavy 先完成、Sparse 最後 release、stall 延伸到 drain、逾時、錯配／空輸入、lag 恢復與右設限、缺必要檔、legacy run 行為不變。已重現反例：seed6101／near／quota1／oldest／Heavy work8／phase_horizon128／W256，現版 cut11、Sparse 實際生成0，但宣告工作6且 PASS；修後必須生成完整6筆並依原 ready 排空。完成時間分母仍採 Heavy 實際完成 cycle+1，不能改用 H。

## P1：ordering 端到端接線（不改 RTL selector）

修改位置：`scripts/run_rtl_diagnosis.py:30 row()`、`:34 params()`、`:38 job_id()`、`:43 output_name()`、`:47 make_job()`、`:71 config()`、`:97 configs()`、`:163 load_results()`、`:179 paired_results()`、`:214 main()`（含 lint name）；`sim/experimental/test_cgof_diagnosis.py:43`、`:61 Harness`、`:180 result`。

1. 新增 CLI `--ordering oldest-first|eligible-round-robin|both`，預設 oldest-first。job.ordering → `ELIGIBLE_RR` → 現有 `CXL_PARAM_*` → Harness/model → serialized result 必須一致。將 TB 的 `ELIGIBLE_RR==0` 改成 job/parameter/oracle 一致性檢查。
2. Job、build/lint、結果檔與失敗紀錄 identity 均包含 ordering；其餘會改變工作內容的 seed/profile/window/work/roles/ready/bounds 亦不得碰撞，可對既有 job 的 canonical payload 加短 hash，不另造 registry。
3. 配對 key 包含 ordering 及其餘實驗條件，唯 lane 不同；檢出 duplicate、missing lane、job/params/result 不一致即失敗，禁止覆蓋或靜默略過。common-horizon 與 legacy finite-Heavy 契約不可混配。本階段不把 P0 新 arrival 契約移植到 RTL finite-Heavy runner。
4. 歷史 consumer `scripts/aggregate_cgof_diagnosis.py:245 finite_rows()`（identity 在270）及 `scripts/analyze_cgof_dynamic.py:53 validate_run()` 仍假設 oldest／固定結果數。最小修正為明確拒絕非 oldest 或 mixed-order 新輸入；不擴寫封存報告產生器。`scripts/analyze_rtl_diagnosis.py` 處理另一種輸入，無須順便改寫。

驗收／tests：擴充 `scripts/test_run_rtl_diagnosis.py`，檢查兩種參數與名稱隔離、預設、duplicate/missing/mismatch、跨 ordering 不混配；在既有 consumer tests 加拒收案例。下方雙 ordering RTL smoke 預期12 jobs、4 finite-Heavy pairs，全部 PASS；再跑既有涵蓋兩種 ordering 的 correctness subset。既有 timestamp、held/refill 斷言必須保留。

## P2：quota backlog 資格（每個 predecision cycle）

修改位置：`refc/cxl_model/diagnosis.py:591 quota_summary()`、`:1207 _classifier_row()`、`:1318 DiagnosisLane._observe_edge()`、`:1431` 窗結束 counter reset；`refc/tests/test_diagnosis.py:190` 及新增回歸案例。

1. 現版只看 closing snapshot 的 producer backlog + FIFO，不能證明整窗 backlog。利用既有 predecision `begin_occ` 累計 observed cycles、active-phase cycles、all-source-local-FIFO-nonempty cycles；每個 cycle 都觀察，包含 !ready、held、idle，不能只看 ready/fire cycle。
2. 只有完整 W cycles、全部屬 active、每個來源 local FIFO 全窗非空才 eligible。外部 producer pending 不能替代 FIFO；closing snapshot 留作診斷。partial／active-drain 混窗排除；舊資料無 history 標 UNAVAILABLE；沒有 eligible window 時 aggregate 為 null，不是0；不合法 counter／維度須拒絕。
3. 此量仍是合格窗內服務份額偏差，不升級成完整 refill-round quota compliance／公平性定理；RTL 原本未提供此歷史的 evidence 保持 unavailable，不以 model 統計冒充 RTL 量測。

驗收／tests：實際 `run_lane` writer→JSON→summary 測試，不只手刻 snapshot。已重現 W64、Heavy work65、Sparse 僅k63進入：fire counts `[63,0,0,0]`、closing FIFO `[1,1,1,1]`，現版仍 eligible且L1=1.5；修後必須排除。另測 all-backlogged 完整後續窗通過、external-only 排除、stall中曾空但ready時全非空仍排除、missing/partial/drain/malformed，以及 null 的下游處理。

## P3：candidate／offered／committed refill 觀測

修改位置：`scripts/run_credit_refill_trace.py:34 inspect_existing_trace()`、`:86 replay()`、`:217 compare()`、`:266` input pairing；`scripts/test_run_credit_refill_trace.py`。

1. 分開記錄 live candidate refill、實際 offered/held grant 的來源／origin cycle／classes／credit snapshot，以及僅 fire 時存在的 committed snapshot。用 test-side hold tracker 保留原 offer，不以目前 candidate 反推 held grant。first activation 與 active→empty→active re-entry 分開。
2. 驗證 no-fire credit 不變，fire 後等於實際提交 snapshot 扣 winner；不要修改 scheduler/model 的 credit 演算法。觀測欄位明示 MODEL-derived，不把 model context 編碼稱為 RTL 訊號。
3. `compare()` 核對完整 active generation 與 ready 輸入，不依 first divergence 截短；沒有 divergence 也必須比對，錯配須使結果失敗。完整掃描 trace 必要欄位，不只第一列。

驗收／tests：`run_shift(5)` quota2 cycle6 現版寫 `refill=false/snapshot=null`，但 choice snapshot `[2,2,2,2]`、credit `[2,0,2,2]→[2,1,2,2]`；新欄位須表達 held grant 的 committed refill。補 held跨stall、classifier close跨held、真re-entry、首次activation、divergence後輸入改變、無divergence及ready錯配測試。沿用現有 RTL held/refill correctness tests，不加新 RTL ports。

## P4：輸出語意、統計與簡短文件

修改位置：`scripts/run_arrival_phase_diagnosis.py:122 _summary_row()`、`:239 _paired_effects()`、`:319 _manifest()`、`:477` summary；`refc/cxl_model/diagnosis.py:661 endpoint_metrics()`；在本計畫追加「實作後欄位對照／驗收」即可，不擴寫主文或覆寫歷史報告。

1. 明確分開 mixed-vs-isolated 及 phase-vs-phase0。現有 `paired_effects` 屬後者；新增明確名稱／estimand 與 baseline/candidate。phase0-vs-phase0 為 self-comparison，不輸出可誤讀為療效／等效證據的 CI。缺 baseline／缺 seed 為 incomplete，不能 KeyError；smoke/W256 即使恰好有全套 seeds 也必須 descriptive，CI=null。
2. `completion_ratio` 明確命名為 `heavy_completion_time_ratio_mixed_over_isolated`，較低較好；與 `fired/generated` 的 completion fraction 分開。新 arrival 契約中 time ratio 用真正 Heavy completion duration。`fire/cycle` 標 scheduler event rate；僅在工作數及時段定義一致時才與時間比互為倒數，平均倒數不等於倒數平均。
3. G→A P99 + A→F P99 不等於 G→F P99；run maxima 的平均不叫 global maximum；gap 區分 wall／ready-opportunity，保留 censoring，重用 `sim/performance/followup.py:113` 的既有機制。equivalence 必須有事先 margin 與正確配對 endpoint，不能由 p-value／零 self-delta 推定。
4. 新 arrival／trace／改變語意的 summary 採版本化 schema 或明確 contract version；只對定義完全相同的欄位保留 deprecated alias。舊 forced-ready、舊 quota snapshot、舊 trace 不補造缺少的 history；consumer 無法解讀須明確拒收／UNAVAILABLE。新結果另存新目錄，保留舊 artifacts 與 hashes。

驗收／tests：缺 phase0／缺seed、全探索seed的W256 smoke、self-comparison、非零混合隔離效果但phase0 self-delta=0、ratio方向／null／分母、舊新契約拒絕混合。現有 `B-arrival-phase-confirmation-20261030/summary.json` 只有phase0，80/80 PASS但 `paired_effects` 全為self-delta=0；不可解讀為 mixed/isolated 無差異，也不改寫該歷史檔。

## Buffer：NOT_IN_THIS_PATCH

本 patch 只保留驗證邊界文字，不新增 Buffer runner、classifier mode 或 RTL。現有 `refc/cxl_model/fai_main_model.py:63 MAIN_TRANSITIONS`、`revision_baselines.py:75 MAIN_1W_TRANSITIONS`／`:312 FaiVariantSwitchModel`、`fai_alg2_model.py:46 ALG2_TRANSITIONS` 足供後續重用；CGOF 目前在 `experimental.py:222` 固定 MAIN transitions。

後續獨立任務最小規格：先用相同 B/S 序列比較 Main／1W／Alg2 的 transition 與正確 effective mapping；再另做閉迴路 CGOF2 live／1W／frozen（CGOF1 negative control），保持 arrivals/ready 相同。模型 W256，phase取0、W/4、W-1，短噪音取W/2、W、3W/2，persistent至少4W；實際settle後須有至少W的可測區間，否則 INCOMPLETE。先單seed接線，再宣告探索seed；各自記錄role change、evidence close、下一cycle effective-visible、實測latency recovery及generation-role cohort。禁止從少flip推論低延遲，或從兩次支持close推論任意phase都有固定2W recovery。

`docs/experiments/revision-20261023/ADAPTATION_RESULTS.md:60`、`:62`、`:108` 已明述 classifier timing≠latency recovery、Main在phase末才settle、該profile提早分類未改善Sparse等待；這些邊界應保留。完整Buffer矩陣、production RTL確認、WRR新對照、完整refill-round accounting、RTL/EDA/PPA改造均為 **NOT_IN_THIS_PATCH**。

## 測試命令與交接

Baseline：監督者最新回報相關64個Python tests全過；本計畫作者先前較窄集合實跑57 passed、36 subtests passed（6.51s），兩者範圍不同，不相加。已做上述唯讀反例probe；本次未跑RTL/EDA或新大矩陣。

在WSL Ubuntu執行，各階段先跑相關檔，完成後再跑下列集合；若P1新增consumer tests，須一併列入監督者的既有64-test集合。命令中的 `--ordering` 是P1新增後才可使用的選項。

```bash
cd '/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler'
source scripts/wsl_env.sh
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider \
  scripts/test_run_arrival_phase_diagnosis.py scripts/test_run_credit_refill_trace.py \
  scripts/test_run_diagnosis.py scripts/test_run_rtl_diagnosis.py \
  refc/tests/test_diagnosis.py refc/tests/test_experimental.py \
  sim/experimental/test_cgof_diagnosis_traffic.py
python scripts/run_rtl_diagnosis.py --smoke --window 256 --mode both \
  --policy both --ordering both --seed 6201 --windows 1 --heavy-work 256 \
  --jobs 1 --make-jobs 1
python scripts/run_revision_cgof.py --subset w64-n4-d16-all-identities --jobs 1
```

執行前確認runner預設輸出目錄不會覆寫既有artifact；必要時使用其既有輸出選項指定新的日期目錄。P0 smoke以測試中的小H／stall反例覆蓋，不開production長跑。RTL命令失敗或環境不足須如實列阻塞，不能以Python PASS取代。

- [ ] 單一writer依P0→P1→P2→P3→P4落實；每階段交付最小diff、回歸結果與一個可檢查JSON例。監督者確認後再進下一階段。
- [ ] 開始先記錄dirty狀態、實際檔案hash與執行代理資訊；保留使用者既有變更，不reset／clean／改歷史manifest。行號漂移以函式名定位。
- [ ] 實作範圍僅本計畫列出的runner、diagnosis/model觀測、TB接線、相關tests及欄位說明；不改 `rtl/` selector／Buffer、accepted spec、報告主文及封存結果。
- [ ] 確認全部生成工作、ready drain、cohort、lag、quota資格、ordering identity與三層refill語意各有失敗反例測試；null/UNAVAILABLE不能悄悄轉成0或PASS。
- [ ] 交付新schema/契約及舊格式處理方式；不能直接比較新舊arrival數字，也不能把新ordering送入未更新的歷史aggregator。
- [ ] 重跑受影響Python與P1 RTL檢查，記錄命令／退出碼／jobs-pairs數；只宣稱實際跑過的驗證。保留MODEL_ONLY與smoke限制。
- [ ] Buffer及其他NOT_IN_THIS_PATCH項目只交接後續規格，不自行展開。超出本清單先回報監督者，完成時列實際改檔、未跑檢查與剩餘風險。

## 實作後欄位對照／驗收（2026-11-01）

狀態：P0–P4 的 bounded 修正已落地；Buffer、production matrix 與新 EDA 未執行。

### 實際改檔

- `scripts/run_diagnosis.py`、`scripts/test_run_diagnosis.py`
- `scripts/run_arrival_phase_diagnosis.py`、`scripts/test_run_arrival_phase_diagnosis.py`
- `refc/cxl_model/diagnosis.py`、`refc/tests/test_diagnosis.py`
- `scripts/run_rtl_diagnosis.py`、`scripts/test_run_rtl_diagnosis.py`
- `sim/experimental/test_cgof_diagnosis.py`
- `scripts/run_credit_refill_trace.py`、`scripts/test_run_credit_refill_trace.py`
- `scripts/aggregate_cgof_diagnosis.py`、`scripts/analyze_cgof_dynamic.py`

未修改 RTL selector、accepted spec、Buffer 狀態轉移、歷史 artifact/manifests 或主論文。

### 新契約與相容性

- Arrival：新輸出為 `cxl-arrival-phase-model-v2`／`cxl-arrival-phase-manifest-v2`；使用 `cxl-arrival-common-generation-v1`，共同 generation horizon、scenario-ready bounded drain、完整 cohort、Heavy lag change points 均明確記錄。舊 `paired_effects` 與 `completion_ratio` 只作 deprecated alias；正式欄位為 `phase_effects`、`mixed_isolated_effects`、`heavy_completion_time_ratio_mixed_over_isolated`。
- Required sources：不再用 `is_file()` 靜默過濾；缺任一必要檔會在建立 output 前失敗並列完整路徑。
- Quota：`cxl-quota-predecision-backlog-v1` 只在完整 active window、每個 predecision cycle 每來源 local FIFO 非空時計入 aggregate；closing snapshot 降為 diagnostic only。缺 history 或未達條件輸出 `UNAVAILABLE`／`null`，不轉成 0。
- Ordering：RTL CLI、job、build params、testbench、result 與 pair key 均帶 `oldest-first`／`eligible-round-robin`。舊 aggregator 明確拒收非 oldest-first；RTL active-cycle ratio 另列 `heavy_active_cycle_ratio_mixed_over_isolated`，舊 completion-ratio 名稱保留為 deprecated alias。
- Refill trace：`cxl-credit-refill-trace-v2` 分開 `candidate_*`、`offered_*`、`committed*`。held grant 保留 latch cycle 的 snapshot/refill，不再用目前 candidate 反推；輸入比對掃完整 generation/ready 序列。

### 實際驗證

- 相關 Python 集合：`89 passed in 4.48s`
  - 命令：`PYTHONPATH=. python -B -m pytest -q scripts/test_run_diagnosis.py scripts/test_run_arrival_phase_diagnosis.py refc/tests/test_diagnosis.py refc/tests/test_experimental.py sim/experimental/test_cgof_diagnosis_traffic.py scripts/test_run_rtl_diagnosis.py scripts/test_run_credit_refill_trace.py scripts/test_analyze_rtl_diagnosis.py`
- Arrival self-check：PASS；三相位 shared Sparse work 均為 12，full Heavy/ready 與 Sparse multiset match。
- Arrival W256 smoke：PASS；2 jobs，`phase_effects=2`、`mixed_isolated_effects=2`、新 time-ratio 欄位存在。
- Credit trace `run_shift(5)` cycle 6：candidate refill false、offered/committed refill true、origin cycle 5、committed snapshot `[2,2,2,2]`、credits after `[2,1,2,2]`。
- RTL W256 bounded smoke：PASS，run `artifacts/implementation/cgof-rtl-diagnosis/20261031T231138Z_1186`；4 jobs、2 finite-Heavy pairs、source stable；lint rr0/rr1、mixed/isolated 全 PASS。
- 較廣 Python 回歸：`703 passed, 16 skipped, 14 errors in 137.36s`。14 個 errors 全在未觸碰的 `scripts/test_revision_power_vectors.py`，根因同為既有 `ExperimentalSwitchModel` 收到 `policy='Main'`；不列為本修正 PASS，也不在本 patch 修。

### 未跑與風險

- `NOT_RUN`：W5M production、20-seed confirmation、full RTL matrix、Buffer 新矩陣、CXL response／bandwidth／application、EDA/PPA。
- 新 required-source 清單包含本計畫文件與實作依賴；源碼或此文件改動後必須重新 freeze，不能拿舊 manifest 當 current-source 證據。
- 舊 arrival/refill/quota 輸出沒有新的 history 或 common-generation 欄位，保持不可升級、不可與新數字直接合併；需要歷史結論時使用原封存 artifacts。
- `completion_ratio`、`paired_effects`、`heavy_completion_ratio_mixed_over_isolated` 是過渡 alias，不應再作為新圖表或 reviewer-facing 名稱。
