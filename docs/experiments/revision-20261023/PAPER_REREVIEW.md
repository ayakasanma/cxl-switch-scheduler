# 修訂稿三角色複審

本報告記錄使用者於 2026-10-27 批准修訂後的對抗式複審。實驗矩陣已完成
498/498 PASS；本輪處理論文、證據連結與交付品質，不重新執行實驗。

這是 Devil's Advocate、Methodology、Domain 三角色的本機諮詢審查。
各角色先固定準則，再閱讀凍結修訂稿與證據，最後對照 F1–F16；
初判前不提供作者回覆、writer self-review 或其他角色的意見。
原始準則卡未完整保留，部分準則由原稿與 issue ledger 重建。
本輪未校準，角色分離不代表錯誤獨立；不宣稱外部同儕審查、編輯接受，
或完整 ARS schema 認證。子任務沿用使用者指定的 Sol/high，沒有新 Opus。

## 初輪發現與修正

下列位置一律指向凍結 round1 的
`docs/final-report/sections/hotnets-body-v3.tex`，避免後續增行造成定位混淆。
精確原始報告、雜湊與逐項判定保留於
`.setup-logs/implementation/revision-20261024/manuscript-revision-20261027/`。

| 問題／嚴重度 | 精確證據位置 | Reviewer 為何反對 | 具體修正 | 新實驗？ |
| --- | --- | --- | --- | --- |
| DA-R1／Major：證據交付閉包不完整 | round1 body:212–213、335–354、550–558、642–650；manifest inputs；final498 index 的 formal_bridges / insight_screen | 498 個效能／功耗項目不能代替額外的來源橋接、SQ replay、leaf audit 或模型篩選證據。原有結果可能正確，但 reviewer 無法從此次凍結包驗證這些精確主張。 | 將既有六組 FCFS/RR bridge 的來源／netlist／報告鏈、原 SQ 診斷與篩選、primary-nine disjoint leaf audit、68-job model screen/gate 納入 hash-bound manifest；保留舊 freeze，不重寫舊 index 為已索引。 | 否；補既有資料連結，不重跑。 |
| M-R1-01／Minor：表格定位不精確 | round1 body:476–477；generated table:42–60 | 表內有 24 cohorts，八項 same-N contrasts 在綁定分析中，不在表格欄列內。 | 改寫成「表格摘要 24 cohorts；綁定分析報告八項 same-N contrasts」。數值不變。 | 否。 |
| W1／Minor：DAC round-state 契約漏述 | round1 body:171–179；DAC RTL:232–235、249–270、299–355 | 未說明 reset credits=0，以及分類改變不會重算本輪額度，讀者可能誤作 live reweighting。 | 明訂 credits 歸零、本輪 credits 跨分類變更保留；新權重在下次 refill 採用，stalled offer 使用凍結 snapshot。 | 否；既有 RTL／model 已定義。 |
| W2／Minor：缺少面積分類數字 | round1 body:549–558；既有 disjoint leaf audit | 敘述 audit 存在、提供 bit counts，仍不足以量化 timestamp 與 policy 的面積成本。 | 加入 N4 FCFS/RR/Main 非重疊分類面積表，標明為九組 audit 的子集；各分類加總對齊完整面積，完整九組輸出另綁定。 | 否；不新增 synthesis。 |

Domain 的 U1、U2 是六組 bridge 與 primary-nine audit 的綁定驗證限制，
與 DA-R1 重疊；不是額外兩個實驗失敗。初輪未建立 Critical 缺陷；
Methodology 無科學方法 blocker。以上不將「缺少此次 release 的連結」
誤寫成「原始證據不存在」。

## F1–F16 的處置邊界

| 原問題 | 修訂內容與驗收依據 |
| --- | --- |
| F1 算術 | Main 高於 RR 38.22–39.27%；RR 低於 Main 27.65–28.20%，分母分開。 |
| F2 來源一致性 | 歷史 14 組 proof、三組 Main bridge、六組 FCFS/RR bridge、DAC own-netlist proof 分開說明，不重複計數。 |
| F3 外部效度 | 全 180 robustness 與 60 N expansion 納入；限定單輸出 descriptor slice，N 同時改變 aggregate demand 與 storage。 |
| F4 新穎性與 baseline | 六 baseline 加唯一 DAC2 候選；FAI／BLISS 改編差異明列，不宣稱新發明 weighted credits 或原文 cycle equivalence。 |
| F5 吞吐與公平 | 分開 offered／accepted／fired／backlog、F/T、F/E、Fh/F；DAC 2:1 entitlement 不等於等權公平或完整需求估計。 |
| F6 因果 | 綁定代表性 replay 與被否決的 SQ screen；保留 quota、Main-1W、適應性負面結果，不將相關性擴大為完整因果分解。 |
| F7 敏感度 | quantum／quota／depth 使用探索 seeds，沒有確認後調參；Main-1W 與 Alg2 的預設重疊明說。 |
| F8 面積 | 完整邊界成本與 disjoint category area 一起報告，保留 cell-count semantic residual；沒有 D8/D32 PPA optimum。 |
| F9 統計 | 確認以 20 個 paired seed/run 為單位，固定 10,000 bootstrap；pointwise、generator-conditional。探索、power、N expansion 無確認 CI。 |
| F10 排名 | 保留 Main 對 RR10 的 burst 劣勢；沒有任意 profile 加權的 overall winner。 |
| F11 PPA | TT／25 ns／pre-layout、critical path 與 disabled checks 均限定範圍，不聲稱 physical signoff。 |
| F12 功耗 | 18 captures／9 A/B pairs，cold／boundary／trained 分開；保留 static gaps、range warnings 與未測 DAC power。 |
| F13 重現性 | 修訂版 generator／manifest／來源／PDF／複審 receipts 對應同一 release；ignored raw archives 仍是必要交付依賴。 |
| F14 formal 推論 | RTL-to-netlist 等價不證明 workload、公平性或完整規格正確。 |
| F15 需求推論 | B/S 是 realized service；DAC 僅讀 local heads，沒有 testbench backlog 或未來 arrivals。 |
| F16 證據層級 | W256 fixture、MODEL_ONLY 篩選、實際 W5M 訓練、retained-state adaptation、proof 與 power 不混算 repetitions。 |

## 優先修訂路線

1. 先補 DA-R1 證據閉包，同時解決 Domain U1/U2；以既有 exact records 驗證，不以額外測試掩蓋交付缺口。
2. 完成 W1、W2、M-R1-01 的局部文字／表格修正，維持原始數值、選定參數及所有負面結果。
3. 對修復版執行 generator 驗證、LaTeX 雙次編譯、逐頁 render QA；由原 reviewer 對各自問題做限定複驗。
4. 封存最終來源／資料／PDF／review hash 與差異，更新 ledger。沒有新增實驗、commit 或投稿要求。

初輪與修復版的判定分開保留。最終 scoped re-review 與 PDF release 以本報告後續
「修復版驗收」段落及 `docs/final-report/V3_REVISION_QA.md` 的精確 receipt 為準。

## 修復版驗收：2026-10-27

三角色均已完成 scoped round2；parent 檢查其 release 與所列報告的實際雜湊，
採納所有修復。**沒有未結的 scoped findings，沒有要求新增實驗。**
初輪的一項 Major 與三項 Minor 原判保留，沒有改寫為一開始就通過。

| 角色 | 修復版判定 | 精確 release SHA256 |
| --- | --- | --- |
| Devil's Advocate | DA-R1 resolved。驗證 588 record pins、六組 bridge、SQ replay/screen endpoints、九組 leaf audit、68-job gate。 | `a2c6cc6a06089b043d23c94b1df7908c159ac3b893dcc312d6b5eeee6745955b` |
| Methodology | M-R1-01 closed；統計主張與原 performance／power macros 未變，沒有新問題。 | `5e7009ae6ad171209a982369d3f649b4021923386afe25e285933a04c34848e1` |
| Domain | W1/W2 fully addressed；U1/U2 的既有證據鏈驗證限制解除。 | `3087fa8e9c53d5497bcc93d6ff92b2cb0031533b84404bfb53b23c5e11cb520a` |

Release 路徑分別為前述 ignored manuscript scope 下的
`devils-advocate/ROUND2_RELEASE.json`、`methodology/ROUND2_RELEASE.json`、
`domain/round2-RELEASE.json`。限定複驗的最終 body SHA256：
`7dd7593eac5298def4245a620001894f909c3c6957b3078ed984948bb2dd93ed`。
最終 evidence manifest SHA256：
`1fd621185ffdc5697a8ae3b5c1bf8557a9d490e81cdd374888676cb468d084ff`。

Parent 驗收 receipt 為同 scope 的 `parent-round2-adoption.json`。
九頁 PDF 已重新雙次編譯及逐頁視覺檢查；四項 generator tests 獨立重跑全通過。
F1–F16 在本輪已定義的修訂範圍內均已有處置與證據，沒有以追加實驗
消除 reviewer 意見的需求。這不代表一般化公平、新演算法優先權、真實系統效益、
physical signoff 或外部投稿接受已被證明；它們是保留的研究邊界。

優先路線 1–4 已完成。下一步屬作者選擇的外部投稿／新研究範圍，
不構成本次交付未完成的必要工作。重現仍需保留 ignored 原始證據，
最終 reviewable ZIP 只封存論文、資料呈現、review 與 hash locators。
# 2026-10-27 圖形版 scoped 複核補件

同一已驗收資料新增六張結果圖，未重跑實驗。Sol/high 獨立核對圖表資料、
配對 CI、cohort 與新 sensitivity 圖；兩項 P3（標籤相接、圖例遮點）
已修復並複核結案，最終沒有未結圖表問題。此補件不把原三角色 verdict
套用為新版所有 bytes 的重新全面審查；全篇排版由 parent 另行驗證。
詳見 `docs/final-report/GRAPHICAL_EDITION_QA.md` 與 ignored
`graphics-20261027/independent/followup-closure.md`。不需新實驗。

