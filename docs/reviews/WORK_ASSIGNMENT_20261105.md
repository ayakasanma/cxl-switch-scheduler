# CXL Scheduler：2026-11-05 review 後工作分配

本分配表根據 C:\Users\USER\Downloads\REVIEW_1104_ZH.md、
C:\Users\USER\Downloads\OPTIMIZATION_PLAN_1104.md，以及 2026-11-05
實際檔案與程序狀態整理。它把「已完成的證據」、「正在執行的工作」與
「尚未開始的計畫」分開，避免把 plan 當成 result。

## 目前基線（以實際 artifact 為準）

- branch：experiment/main-sq。
- working tree 已有使用者修改：README.md 4 行；README.zh-TW.md 與大量
  docs/final-report 生成物未追蹤。任何 worker 不得 reset、清理或覆蓋這些檔案。
- P0 cost refreeze 已完成；clean A3 已完成：20261104T063359Z_1495，4/4 RTL、
  4/4 G-EQ、source stable。
- A4 seed 7401 已完成：20261104T120647Z_900331，2/2 RTL、2/2 G-EQ；它是
  Main implementation anchor，沒有 CGOF RTL anchor。
- confirmation artifact：7401–7404 各有完整 30-job 目錄；7405 的
  20261104T190951Z_seed7405 目前仍由 runner 寫入，最新盤點為 18 個 job 檔，
  尚無完整 manifest/cohort，不能算完成。舊的 20261104T172158Z_seed7405 只有
  12 個檔案，也不能與新目錄拼成一個 seed result。
- 7406–7420 目前沒有可升級為 confirmation result 的完整目錄；
  .setup-logs/.../analyzer-smoke/jobs 裡的同名檔是 smoke 輸入/檢查資料，不是
  20-seed campaign 的完成證據。
- /tmp/cxl-resume.sh 仍在 WSL 執行 7405（6 個 Python worker）。不得另開第二個
  campaign，也不得在 source freeze 尚未結束前改 runner/RTL。

## 工作包與分工

| ID | 工作 | 類型／可寫範圍 | 實際路由 | 依賴與驗收 |
|---|---|---|---|---|
| A | confirmation artifact/status audit | 只讀；不可啟動新 campaign | DeepSeek v4.1 Flash max；Cindy Session 的 codex host route（實際 route 需以 task card 為準） | 逐 seed 列出 manifest、30-job 完整性、PASS/FAIL、audit；核對 WSL runner；明確決定 7405 完成後是否從 7406 繼續。 |
| B | final-report LaTeX wording repair | 隔離 worktree；只改 docs/final-report/sections/hotnets-body-v3.tex | GPT 6.1 Sol high；Cindy Session 的 codex host route | 套用 review 指定 7 項文字修正；不得新增實驗或改 RTL/runner；回報 diff 與編譯/grep 驗證命令。 |
| C | runner/integration gap audit | 只讀；不可改 shared source、不可跑昂貴實驗 | Gemini 3.8 Flash high；Cindy Session 的 codex host route | 對照現有 scripts/tests，列出 P1/P2 每項檔案、命令、缺口、依賴、驗收條件；特別覆蓋 8-case re-entry、quota fail-closed、ordering/job identity。 |
| D | drain metadata repair design | 先只讀；source freeze 結束後才可由單一 writer 修改 | 複雜跨檔工作由主模型指定 GPT 6.1 Sol；目前先不啟動寫入 | 釐清 drain_cycles=0,0,0,2 與 scope NOT_EXERCISED 的衝突；設計 derived metadata 重建輸入/輸出 hash。長 backlog directed drain 仍維持 NOT_EXERCISED。 |

## 實驗與整合的後續順序

1. 先等待/稽核 7405：只沿用現有 runner。7405 通過 per-seed audit 後，才可逐 seed
   釋放 7406–7420；任何 incomplete cohort、source drift、超時或 audit mismatch 都停下。
2. P0.5 metadata：由單一 writer 修正 derived record；不要把自然出現的 2-cycle
   drain 寫成完整 long-backlog drain proof。
3. P1 smoke 與 offline audit：先完成 repo-root path/dependency smoke，以及
   physical source/generation/cohort 欄位完整性核對；缺欄位輸出 INCOMPLETE。
4. P2 runner/integration：依 C 的盤點結果實作 8-case candidate/offered/committed/
   held/refill/re-entry、quota sustained-backlog fail-closed、oldest-first vs
   eligible-RR same-input/job-identity smoke。W64/W256 優先，先不跑 W5M。
5. P1 experiments：under/over-load RTL pairs、CGOF gate-level SAIF/PrimePower、
   latency recovery + N8/N16 finite-heavy、directed long-backlog RTL drain。每項都要有
   實際 log、source hash、命令、版本與停止條件。
6. 20-seed aggregate：只在上述 gate 完成且 7401–7420 每個 seed 都有完整 30-job
   artifact、per-seed audit 通過後，才做 aggregate；未完成時保持 MODEL_ONLY/
   NOT_CONFIRMED，不把計畫文字升級成結果。

## 共同驗收規則

- 不修改使用者既有 README 或未追蹤 final-report 生成物；不使用 git reset --hard、
  git clean 或大範圍覆蓋。
- 實驗結果以 artifact/log 為準；未執行的檢查不得標 PASS。
- A3 drain metadata 可修正，但 directed long-backlog drain 未完成前，報告仍標
  NOT_EXERCISED。
- C3 拆成 NULL_CONFIRMED 與 SUPERIORITY_NOT_CONFIRMED；不使用 equivalence、
  ordering invalid 或 universal no benefit。
- CGOF 只在已量測的 latency/fairness/area/timing scope 內描述；power 未量測時不宣稱
  完整 PPA winner。

## 工作狀態

- A：初輪與 review/plan 補充對映均已完成；目前 7405 目錄實際有 24 個 job 檔，仍未視為完整 seed。
- B：已完成隔離 worktree 修正，已將唯一目標檔案整合回主工作樹；`git diff --check` 通過，PDFLaTeX 驗證由 worker 回報 exit 0。
- C：只讀 runner/integration 稽核已完成，9 項缺口已納入下方清單。
- D：待 A/C 回報且 7405 source freeze 結束後再派，避免與活動 runner 競爭 shared source。

## Workstream C 回報後的實作缺口（2026-11-05）

C 已依 `C:\Users\USER\Downloads\REVIEW_1104_ZH.md` 與
`C:\Users\USER\Downloads\OPTIMIZATION_PLAN_1104.md` 完成只讀盤點。現有
scripts/tests 多數只提供參數解析、局部單元測試或既有 near-profile 證據，不能把
計畫項目當成已完成結果。

| 優先 | 項目 | 現況 | 下一個可驗收產出 | 前置條件 |
|---|---|---|---|---|
| P0 | 7405→7406 campaign gate | 7405 完成前不可放行 7406；不可開第二條鏈 | 7405 manifest `jobs=30 / failed=[]`、per-seed audit PASS，再記錄逐 seed release | 現有 runner 完成、source freeze 維持 |
| P1 | under/over-load pairs | profile 參數已存在，8101–8105 模型/RTL pairs 尚未跑 | 配對 mixed−isolated 結果、固定 seed/source hash、under/over gate | 7405 完成、source 解凍 |
| P1 | runner path/dependency smoke | 有 WSL/tool smoke，但缺 repo-root import 與缺依賴 fail-fast | `scripts/smoke_imports.py` 或等價單一入口 | 先定義 PYTHONPATH/package 規範 |
| P1 | physical source/generation/cohort audit | 目前主要驗 seed/case 組合，未逐來源驗 physical fields | 缺欄位輸出 `INCOMPLETE`；驗 `pending==0` 與守恆式 | job 遵守 physical-sources schema |
| P1 | 8-case refill/re-entry | 有局部 unit tests，未與 diagnosis runner 端到端聯調 | W64/W256 逐 cycle candidate/offered/committed/held/refill/re-entry 對齊 | 不改 RTL；短週期 smoke |
| P1 | quota sustained-backlog | `refc` 有 fail-closed 判定，active accounting 尚無全 cycle history | predecision history、缺歷史/混入 drain 回傳 `UNAVAILABLE`/`null` | shared accounting 設計完成 |
| P2 | latency recovery + N8/N16 | accounting 尚未實作 recovery window；缺 5-seed finite-heavy cohort | 8101–8103 W5M recovery 與 N8/N16 5-seed 帳本 | accounting 修正、機器時間 |
| P2 | directed long-backlog drain | A3 scope metadata 硬編碼 `NOT_EXERCISED`；尚無定向長 drain | backlog cut、drain >10 cycles、`fired==accepted` 證據 | D 修 metadata、source 解凍、約 6h RTL |
| P2 | CGOF gate-level power/SAIF | CGOF 1:1/2:1 尚無 SAIF/PrimePower | 3 seeds × 2 policies SAIF、SHA-256、leakage/internal/switching | FastX/SAED32 授權與網表 |
| P2 | oldest-first vs eligible-RR | 目前只有參數/輸出路徑 unit tests | 同 trace/ready 的 W64/W256 分歧與 job identity smoke | 不改 selector；結果維持描述性 |

### 目前決策

1. 先收口 7405，再做 per-seed audit；未通過不得釋放 7406。
2. source freeze 解除後，先做低成本 P1 smoke/offline audit 與 8-case integration，
   再安排 P1 under/over pairs。
3. D 只處理 drain derived metadata；長 backlog directed drain 完成前仍標
   `NOT_EXERCISED`。
4. CGOF power 未有 SAIF/PrimePower 前，報告維持 `power unmeasured`；C3 維持
   `NULL_CONFIRMED` 與 `SUPERIORITY_NOT_CONFIRMED`。
5. 20-seed aggregate 必須等 7401–7420 每個 seed 均有完整 30-job artifact、
   per-seed audit PASS 後才能執行。

## A 補充對映後的 release gate

A 以明確 review/plan 路徑重新對照後，將 campaign gate 收緊如下：

- P0 clean A3 已閉合：`20261104T063359Z_1495` 為 4/4 RTL、4/4 G-EQ，
  `source_stable=true`，48 個 source hash 與 campaign 一致；release 文件仍應補記
  clean run id。
- P0.5 drain derived metadata 尚未閉合；`a3_scope.json` 頂層仍可能是
  `NOT_EXERCISED`，而 job 層已有 `drain_cycles=2`。長 backlog directed drain 仍不
  得宣稱完成。
- Review 要求的 step 2 short directed runner integration 尚無產物；因此即使
  7405 完成，也不能直接把 7406 當成已通過 gate 的 confirmation seed。
- 7405 目前實際盤點為 24/30；必須等 manifest `jobs=30 / failed=[]`、cohort、
  per-seed audit 後，先處理 P0.5 與 step 2，再決定是否續跑 7406。
- 論文文字目前以工作樹實際檔案為準；controlled PPA、strongest operating
  point scope、single-seed hypothesis-generating 等修正已存在。若後續 grep 發現
  C3 claim matrix 仍使用 `CONFIRMED`，只修該文字層，不改 campaign source。

## 白話版：問題、負責人與先後順序

目前的核心問題是「資料還沒完整、流程還沒串完、報告有些地方可能寫得比證據更滿」。
這不是要立刻重寫整個系統，而是先把證據鏈補齊，再擴大實驗。

| 順序 | 要做的事 | 負責人 | 完成標準 | 目前狀態 |
|---|---|---|---|---|
| 1 | 把目前這一輪跑完並確認沒有漏件 | 實驗監看者 A；主模型最後核對 | 30/30 結果、沒有失敗工作、產生完整索引與單輪稽核 | 7405 目前 24/30，進行中 |
| 2 | 暫停放行，檢查資料來源和排空記錄是否一致 | 記錄修復者 D；主模型驗收 | 實際測到的排空數字與報告欄位一致，長時間排空仍明確標示未驗證 | 尚未開始，等待目前一輪結束 |
| 3 | 做一個短而完整的流程測試 | 流程整合者 C／E；主模型驗收 | 從資料產生、排隊、執行到完成，每一步的識別與數字都能對上 | 目前只有零散單元測試 |
| 4 | 檢查環境和資料欄位 | 流程整合者 C／E | 從專案根目錄可直接啟動；缺套件會立即報錯；缺資料會標示不完整 | 部分已有，尚未形成單一入口 |
| 5 | 修正論文與報告中的說法 | 文件修訂者 B（GPT 6.1 Sol）；主模型複核 | 沒量到的功耗不寫成勝者；單一 seed 不寫成普遍結論；已測與未測清楚分開 | 主要文字修正已完成，仍需檢查 claim matrix |
| 6 | 前置檢查通過後，才繼續後面的 seed | 實驗監看者 A；主模型決定是否放行 | 前四步都通過，且來源版本沒有變動，才開始下一個 seed | 尚未放行 7406 |
| 7 | 補做壓力、排空、不同排程策略和功耗測試 | 實驗執行者（由主模型指定 GPT 6.1 Sol）；C／D 提供驗收 | 每項都有真實 log、來源版本、停止條件與可重現命令 | 尚未執行 |
| 8 | 最後才做整體統計與結論 | 主模型＋獨立複核者 | 所有 seed 完整、每輪稽核通過後，才做總體統計和論文結論 | 尚未開始 |

### 白話版判斷

- 現在最重要的是把正在跑的資料收乾淨，不要急著增加新的實驗。
- 已完成的資料可以保留，但每個 seed 只能代表它自己，不能直接代表整體效果。
- 沒有實測的功耗、長時間排空和系統級延遲，都先寫成「尚未驗證」。
- 每個階段都要留下命令、版本、log 和結果索引，下一個人才能重現。
- 主模型負責排序、整合和最後放行；各工作者只負責自己的範圍，不直接改動別人的活動實驗。

