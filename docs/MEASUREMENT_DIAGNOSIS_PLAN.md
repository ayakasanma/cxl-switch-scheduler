# FAI-inspired 與 CGOF：量測與診斷研究計畫

日期：2026-10-27。狀態：實作及快速驗證中；production 確認結果依實際執行紀錄更新。
本文是研究與驗收合約，不表示下列實驗已完成。

## Material Passport

- Task: implement the author-approved measurement/diagnosis study.
- Contribution: measurement and causal diagnosis at the scheduler boundary.
- Evidence boundary: model screens, RTL checks and system measurements are separate.
- Human-subject data: none.
- Next gate: independent correctness review, then exploration, then frozen confirmation.

## 1. 名稱與設定識別

方法名稱統一為 **CGOF（Credit-Gated Oldest-First）**。
等額與加權服務是同一方法的不同設定：

| 方法 | High:Low 配額 | 排序 |
|---|---|---|
| CGOF | 1:1 | oldest-first |
| CGOF | 2:1 | oldest-first |
| credit-gated eligible round-robin control | 1:1 | eligible round-robin |
| credit-gated eligible round-robin control | 2:1 | eligible round-robin |

同圖標示 `CGOF (1:1)`、`CGOF (2:1)`；表格使用獨立配額欄位。
主分類排程方法稱為 **FAI-inspired**。不新增編號或歷史名稱說明。
方法、配額、排序、分類模式、N、D、W、負載、回壓及 seed 都是設定識別的一部分。
不同設定不得共用結果主鍵或覆蓋彼此。
封存輸入的內容及雜湊維持完整；呈現名稱不能成為合併資料的依據。

CGOF 的 credit 是仲裁服務權額，不是 CXL 協定的接收緩衝 flow-control credit。
active 定義是來源 FIFO 非空。沒有 eligible 來源時，以當下分類建立所有來源
的 refill 候選向量；真正 fire 才提交該向量並扣除所選來源的一份權額。
refill 覆寫餘額，不累積 deficit；inactive 來源不阻止 refill，重入不額外補額。
分類變更影響下一次 refill。held grant 保留所選來源及 refill／分類快照。

## 2. 研究問題與可否證假說

研究主張聚焦於配額、排序與量測邊界如何影響公平性、Sparse 尾延遲及 Heavy 效能。
CGOF 是受評估的機制；不預先宣稱演算法首創。

| 問題 | 干預與對照 | 可否證條件 |
|---|---|---|
| 收益是否只是配額改變？ | 1:1／2:1 × oldest-first／eligible RR，另有 WRR／IWRR | 固定配額後差異消失，則收益主要由配額解釋 |
| Sparse 保護對 Heavy 有何代價？ | 同 seed、同工作 Heavy 獨跑／共跑；Sparse 持續到 Heavy 完成 | 比較完成時間、分窗服務率及 backlog，不能只看短窗平均吞吐 |
| delivered service 是否被誤認為需求？ | 分離 generation、producer backlog、FIFO occupancy、fire 及跨窗分類 | 若限制前需求和服務觀測沒有產生可區分結果，不擴大該假說 |

配額與排序控制共用 FIFO、分類器、refill 和 output-hold 語意。
eligible RR 僅在 fire 後把 polling pointer 移至所選來源的下一個來源。
它不是標準 WRR；WRR／IWRR 是另列的模型基準。
固定類別只用於模型的配額檢查，不替代實際分類器的 production RTL 證據。
WRR／IWRR 的動態權重採樣時點、空佇列跳過與 held context 要隨結果記錄。

## 3. 指標與統計合約

| 面向 | 必要輸出 | 解讀邊界 |
|---|---|---|
| allocation | 每來源 generated／accepted／fired、服務份額、配額目標與誤差 | 政策符合度和共同公平目標分開 |
| fairness | 原始 Jain 與按明確需求／權重參照正規化的 Jain | 不等需求下，低原始 Jain 不能直接判不公平 |
| latency | generation→acceptance、acceptance→fire、generation→fire 分布與每 run P99 | fire 不等於 memory response |
| Heavy | fire/cycle、固定子視窗服務率、backlog 起訖／成長、有限工作完成時間 | 不以 drain 完成證明穩態穩定 |
| completion | burst release→最後 fire，及同 seed 同工作獨跑比值 | 未完成標示 censored，不刪除或當成零 |
| gaps | wall-clock 與 ready-opportunity 間隔 | 分開 producer+FIFO backlog 與僅 FIFO backlog，保留首段及右截尾 |
| observation | 每分類窗需求、服務、分類、配額與外部／內部 backlog | 診斷服務量與需求的落差，不能直接歸因 |
| correctness | generated = accepted + producer pending；accepted = fired + FIFO pending | 包含 cohort、guard 及 drain 的守恆 |
| utilization | avoidable bubbles、ready opportunities、有效輸出轉移 | fire/cycle 不是實測 memory bandwidth |

份額誤差必須記錄目標向量、計算區間及需求前提。固定全 backlog 時，
權額為 `w_i / sum(w)`；未持續 backlog 的來源不得直接套用飽和份額當通用公平目標。
共同需求目標若使用 demand-capped allocation，須記錄容量與估計需求來源。
沒有服務、沒有參照或沒有完成樣本時回傳 null／unavailable，不編造 P99 或 Jain。

cohort 在 generation 時固定。跨 phase、guard、drain 的完成仍歸回原 cohort；
每來源的未接受、已接受未完成與右截尾工作都要保留。
有限 Heavy 工作使用 burst ID；獨跑和共跑使用同一組 Heavy release／descriptor。
Sparse 干擾在 Heavy 完成前持續；超時則保留未完成狀態。
服務間隔須明訂是否包含服務端點；主圖統一採「兩次服務 cycle 的差」。

主要統計單位為 seed／run。配對比較使用同一組外生 arrivals、descriptors 及
ready schedule；不能按每個政策各自的完成時間改變先前輸入。
報告每次執行 P99 的平均和 paired delta，使用 10,000 次 paired bootstrap
取得 95% 區間；不可把請求或來源當獨立重複實驗。
探索結果不能標為確認；確認前固定候選、情境、比較方向、指標與圖表。

## 4. 第一階段與凍結順序

第一階段目標為 2–4 週。以下是工作順序，不是承諾完成日期。

| 順序 | 工作 | 通過條件 |
|---|---|---|
| 第一週 | 統一名稱、核對證據／文獻、凍結比較及指標 | 設定可識別、原始數值未改、manifest 先於執行 |
| 第二週 | 模型二因子對照、WRR／IWRR、有限 Heavy 與觀測診斷 | 模型單元檢查與守恆通過，保留反例 |
| 第三週 | 依既有委派流程補最小 RTL 控制組 | lint、獨立模型、定向與隨機 regression 通過 |
| 第四週 | 必要敏感度、production 長跑、圖表與 go/no-go | 確認 seeds 未參與選擇，負結果／未執行項目完整 |

預設 N4、D16、M1、full105、W5,000,000。探索 seeds 為 6101–6105；
確認 seeds 為 6201–6220，不能拿確認資料調參或挑情境。
freeze 時檢查 manifest 內兩組 seed 不重疊且不同於既有 509–513／529–548。
每份 manifest 綁定完整設定、原始碼雜湊、比較與輸出位置；輸出必須使用新目錄。
原始碼變更後要重新 freeze，不沿用舊 manifest。

主要確認包含 Sparse A／B，新增情境最多兩種：機制區分案例與負控制。
新增情境先在探索 seeds 篩選，再把其定義及是否採納寫入確認 manifest；
不得在確認結果出現後替換。
N8／N16、D8／D32、回壓、角色切換每次只變一項。
W256 只作快速驗證／敏感度，不能自動升格為 production。
長時間實驗至少跨三個實際 production 分類窗；分開低於、接近及超過容量的負載。
訓練後只量測 100k cycles 的資料不能被稱為長期穩態。

先重用既有事件追蹤及統計，只新增 burst ID、必要時段與來源狀態。
單元測試及 stress smoke 不計入確認樣本數。

## 5. 驗收與主圖

- 名稱、配額、排序一致；兩種配額的請求紀錄及數值不得因改名而改變。
- 覆蓋 refill、inactive overwrite、重入、分類切換、同齡 tie、wrap、held grant。
- 固定類別驗證預期服務份額；實際分類器另用多窗測試。
- 新 RTL 依原委派流程實作，Codex 獨立審查；保存模型差異、lint、JUnit、exit。
- 保存 timeout、失敗、負結果與 NOT_RUN；不得只收集成功的來源或 cohort。
- 論文圖：配額誤差、配額×排序、Sparse–Heavy 取捨、延遲分解、
  跨視窗吞吐／backlog。模型篩選圖與確認圖分開標示。

## 6. 系統驗證進入條件

只有核心發現經干預支持、超出配額算術、跨獨立負載／seeds 成立，且與文獻仍有
明確差異，才投入完整系統整合。先驗證平台存取、事件邊界、時脈和負載校準。
後續量測 completed bytes/s、issue→response latency、application slowdown 與
maximum slowdown，使用同工作獨跑基準。
本階段不由 descriptor Length 或 fire/cycle 推算已量測的 CXL bandwidth。
若簡單配額基準已解釋收益，保留診斷結果，停止演算法首創主張。
APR、全矩陣 PPA 與完整系統整合延後；仲裁改善未必轉化為應用收益。

## 7. 文獻差異與證據規則

文獻機制矩陣見 `experiments/diagnosis-20261027/LITERATURE.md`。
DRR、WRR／IWRR、pFS、CCSP 的相關性是既有研究對照，不表示已證明 CGOF 首創。
FAI-inspired 的單輸出排程是專案重建，不能聲稱與完整 FAI-CXL 系統 cycle-identical。
MemChannel 必須按已正式出版的 NSDI 2026 研究處理，不能列作只有 preprint。
來源核實程度、讀取範圍、機制差異及不可繼承的理論保證一併記錄。
