# 編輯核對：現行論文與既有證據

日期：2026-11-05。範圍：唯讀審查；未修改論文、未執行新實驗。

審查對象：`docs/final-report/sections/hotnets-body-v3.tex` 與已發布的 `docs/final-report/cxl-scheduler-revised-20261102.pdf`（15 頁）。行號指現行 LaTeX；發布 PDF 保留原頁碼。

## E1：總結與非零 Heavy 代價矛盾（MAJOR，高信心）

- 位置：body:294；PDF pp.13–14，`preserving long-run Heavy completion and throughput`。
- 證據：body:251 明列 Main completion ratio 1.2002146、CGOF (2:1) 1.2004373，差 +0.0002227；Heavy throughput-ratio 差 −0.0001544。body:272 另有 near-load mixed−isolated +3.00/+3.05 cycles。
- 異議：小幅代價不等於不變，且不同 workload／比較基準的零差不能互相替代。
- 修正：改為「Sparse tail 改善伴隨較小、非零的 Heavy completion／throughput 代價」，指定 model overload 與對照策略；保留原數字。body:294 的 overload gap 範圍也應按設定分列：1:1 為 7.55−7.00=+0.55，2:1 為 +2.55 cycles；不可合稱 1–2.55。
- 新實驗：不需要。

## E2：allocation 主因的因果判斷超過 ordering 對照（MAJOR，高信心）

- 位置：body:296；PDF p.14，`confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever`。
- 證據：body:245；`artifacts/implementation/cgof-rtl-ordering-confirmation/analysis-20261101T045246Z.json` 的 `primary_summary`：Q1 delta 全 0、Q2 delta −1 只有 7/20、gate 15/20，`NOT_CONFIRMED`。四組都已有 per-source credits，未交叉操弄 class allocation vs. per-source allocation。W5M 五 seeds 的結果為描述性。
- 異議：未確認 ordering 優越性不能確認另一個機制的主導因果，也不是 ordering 等效證明。
- 修正：限縮為已測 all-effective-High workloads 中 ordering 的 Sparse P99 差異為 0–1 cycle，並列 Q1 Heavy gap 代價；allocation 機制另由固定類別分配算術支持。C3 類別建議寫「確認實驗已完成；superiority 未確認」，避免將 `CONFIRMED` 誤讀成零效應確認。
- 新實驗：限縮主張不需要；只有堅持比較「主要因果」時才需要相同 workload 的 allocation × ordering 對照。

## E3：整體最佳缺少共同排序依據（MAJOR，中高信心）

- 位置：body:294；PDF p.13，`strongest overall operating point across the three specified objectives`。
- 證據：body:239（固定類別份額）、249–253（model overload 與 near RTL）、284–294（硬體與選擇）；各比較的政策、負載與證據層級不同。body:294 本身列 RR10 更小與 CGOF 1:1/2:1 取捨；body:296 列 CGOF power 為未完成。
- 異議：列出三個目標仍不足以推導整體排序；「不是 universal winner」不能建立 scoped overall winner。
- 修正：以條件式選擇陳述具體比較：相對 Main 的 trained tail／area 改善、固定類別的目標份額、near RTL 1:1 的 regularity 優勢、RR 的面積優勢。移除 strongest overall；不需要新增評分或任意目標加權。
- 新實驗：不需要。

## E4：W256 P99 實為小樣本最大值，正文未說明（MINOR，高信心）

- 位置：body:122、245，Table 8／Figure 10(a)。
- 證據：ordering analysis 的 `limitations` 明列 P99 等於 sampled maximum。主審讀取其 80 個 mixed jobs 的 `role_counts.sparse.fired`，每 run 合計 12–32；nearest-rank `ceil(0.99*n)=n` 全部成立。正文有 nearest-rank 定義，但沒有這項樣本規模說明。
- 異議：讀者容易將短任務的極值比較當成穩定尾分布；20 seeds 的配對統計不增加單輪尾端樣本量。
- 修正：Table 8／圖註及段落加上每輪 Sparse n=12–32、P99 等於樣本最大值；保持 `NOT_CONFIRMED`，W5M 描述另列。
- 新實驗：不需要；若要宣稱 stationary P99 則需不同的採樣設計，屬範圍擴張。

## E5：現行來源與發布 PDF 不同（MAJOR，高信心）

- 位置：body:20、294；PDF p.1、13；`docs/final-report/publication-20261102.json` 的 `source_dependencies`。
- 證據：現行 body:20 的 Ethernet/CXL 類比邊界句未出現在發布 PDF p.1；body:294 新增 `Within the evaluated N4 behavioral workloads...`，發布 PDF p.13 仍是 `Across the three specified objectives and measured scope...`。這是文字差異，不只是檔案標記不同。
- 異議：現有來源修正尚未交付到發布 PDF，不能以舊 acceptance 表示現稿已驗收。
- 修正：修訂批准後，由一份明確的權威來源重建 PDF，更新發布索引與驗收記錄；保留舊版。沿用既有實驗與歷史 acceptance 的適用範圍。
- 新實驗：不需要；需重新編譯及受影響頁面的圖文核對。

## 核對方法與覆蓋

直接讀取 LaTeX、發布索引、claim matrix、ordering analysis 與已發布 PDF 文字；檢視 PDF pp.13–14 圖文。所有檢查僅為定位具體主張差異及樣本解讀。工具紀錄保留於本次對話，PDF 擷取與局部預覽存於 `.setup-logs/implementation/paper-spine-review-20261105/`。未取得完整工作階段 token／成本統計，telemetry unavailable。

未重跑模擬、PPA、formal 或 bootstrap；未新檢索外部文獻；不是全 15 頁視覺 QA，亦不是文獻新穎性或引用完整性的認證。
