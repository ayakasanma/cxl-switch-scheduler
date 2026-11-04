# 最新報告改進計畫：從共享記憶體競爭到排程行為與硬體成本

日期：2026-10-28，Asia/Taipei。狀態：可供修稿使用的計畫，尚未套用到論文。

本計畫依使用者指定的五步閱讀順序，使用 ARS-Codex 的 academic-paper 結構設計與寫作品質檢查方法。材料來自本機論文全文、目前 v3 原稿、已接受的實驗資料及 10 月 28 日診斷結果。這次產出是章節與證據配置；後續假說及必要實驗另見 [HYPOTHESES_AND_EXPERIMENTS.md](HYPOTHESES_AND_EXPERIMENTS.md)。Agent 入口為 [agent-handoff.json](agent-handoff.json)，包含來源 SHA-256、章節順序、既有結果與待辦實驗索引。

## 1. 全文要回答的問題

主問題：多個來源共享一條記憶體服務路徑時，服務歷史分類與服務配額如何改變請求的等待分布，而這些選擇需要多少完整 RTL 硬體成本？

建議論述主軸：CXL pooling 讓記憶體容量可跨 host 配置，也使通往共享資源的路徑成為競爭點。FAI 以服務歷史辨識 host，並透過過渡狀態調整優先權；將這個概念轉成 RTL，需要明確定義分類、配額與資料傳輸的關係。在共同平台上，這些規則會重新分配等待時間。最新結果進一步顯示：類別配額與每來源配額造成不同的服務分布；縮短 Sparse 尾端等待，也可能拉長 Heavy 的服務間隔。硬體量測則說明這些行為選擇的實作代價。

全文用三個問題推進：

1. **機制問題**：分類結果如何變成下一次服務機會？Buffer 解決什麼時間尺度的問題？
2. **行為問題**：誰少等了、誰多等了，服務份額與服務間隔是否也改變？
3. **實作問題**：FIFO、排序 metadata、分類與仲裁邏輯各付出多少成本？

建議工作標題：*From Service Classes to Hardware Costs: An RTL Study of CXL-Inspired Switch Scheduling*。保留課程報告定位，不新增投稿或篇幅要求。主文暫配約 4,400 個英文詞，圖表與參考文獻另計，完成內容後再依課程規定排版。

## 2. 從現有論文學習的結構與論述方式

以下依本次實際閱讀的本機版本與段落整理；借用的是論證結構，不搬用句子或他文的效能數字。

| 論文與已讀位置 | 論述如何推進 | 在本報告的具體用法 |
| --- | --- | --- |
| [Pond](../lit-review/fulltexts/pond.txt)，Introduction 的 Motivation、Limitations、Our work、Artifacts | 先說容量浪費與效能需求，再解釋 pooling 的機會及延遲代價，最後落到設計選擇與量測 | §1 先建立 pooling 的目的，再帶出共享路徑競爭；不要第一段就列七種 policy 或實驗筆數 |
| [CXL introduction](../lit-review/fulltexts/cxl_intro.txt)，§1、Figure 1 | 先說 memory/coherency semantics，再逐層建立互連背景 | §1 用 load/store 存取 pooled memory 的路徑圖解釋 scheduler 所在位置；補足 CXL 與一般封包排程的關係 |
| [FAI-CXL](../lit-review/fulltexts/fai.txt)，§II、§III-C、§IV-C、Algorithm 2、§V | 先介紹 pooling/interleaving，再用 host 間競爭帶出排程，接著交代 window 與 Buffer | §2 按「服務觀察 → 分類 → 過渡 → 服務」介紹；原文、Main、Algorithm-2 的差異放在讀者已理解目的之後 |
| [BLISS](../lit-review/fulltexts/bliss.txt)，§II–VI，尤其 Key Observations、Implementation、RTL Synthesis Methodology | 從干擾問題提煉設計觀察，接到簡單機制、所需儲存與比較邏輯，再定義實驗 | §3 將每個狀態對應到其用途；§4 先定義行為與硬體量測；§5 再回答成本是否值得。使用本機題名 *Achieving High Performance and Fairness at Low Cost* 的版本，修稿時核對 bibliography，勿與另一篇同系列技術報告的題名/年份混用 |
| [STFM](../lit-review/fulltexts/stfm.txt)，Abstract、§1 及 Figure 1 說明 | 先定義共享時相對於獨享時的 slowdown，才評價公平性 | §4 先定義公平性的參照：等需求、指定權重或 mixed/isolated；§5 讓公平性指標回答對應問題，不把服務比例直接當應用進度 |
| [Gupta and McKeown](../lit-review/fulltexts/gupta.txt)，開頭與 The scheduling algorithm | 先交代 port、slot、queue 與 matching 約束，再談高速實作 | §3 先畫共同服務邊界，再定義 fire、FIFO eligibility 與 hold；讓硬體細節有位置與目的 |
| [Mandal et al., WRR analysis](../lit-review/fulltexts/wrr_arxiv.txt)，Abstract、§I，本機 arXiv v2 | 先定義 arbitration 的權重與服務時間，再連到等待時間模型與實驗驗證 | §4 分開描述「分配多少機會」與「機會以何順序出現」；推導適用條件後再比較結果。此檔是 NoC WRR 論文，並非 Tabatabaee 等人的 IWRR 論文 |

背景與 related work 改成隨問題出現：pooling 文獻放 §1，FAI/BLISS 放 §2–3，公平性與 weighted scheduling 放 §4。需要更完整比較的文獻表放附錄。這樣每次引用都解答當下讀者的問題。

## 3. 章節藍圖與段落銜接

### §1 CXL Pooling and Shared-Path Contention（約 600 詞）

**讀者離開本節時應理解：容量共享帶來效益，但對同一條路徑的同時請求需要仲裁。**

段落順序：容量分散與 pooling 的目的；CXL 的 cacheable load/store 記憶體存取；多個 host 在共同 egress 或下游資源競爭；Heavy 與 Sparse 的短例子；本研究的三個問題。圖 1 左側畫 host/switch/memory，右側放大本專案的單輸出切片。

CXL 與一般封包排程的共同點是有限服務能力、排隊、仲裁與 backpressure。研究動機著重記憶體共享場景中的干擾，以及 FAI 類策略的 RTL 成本。不要以「Ethernet 不在乎 latency」來區分，也不要以固定大小交易作為 CXL 獨有特性：Gupta 的封包 switch 同樣使用固定大小內部 cell。應用可能因記憶體等待而受影響是研究背景；本專案的量測單位在 §4 定義。

**接到 §2 的邏輯**：不同 host 的服務需求與等待情形不同，因此引入會依近期服務歷史調整分類的 FAI。

### §2 FAI: Service History, Priority, and Transitional Buffer（約 650 詞）

**讀者離開本節時應能用自己的話解釋 Buffer。**

先用 Heavy 連續送件、Sparse 偶爾送件的例子，說明低使用量來源可能受到排隊干擾。介紹原始 FAI-CXL 的 pool manager、interleaving 與 scheduler 三部分，然後聚焦 scheduler。每個 window 記錄各 host 成功獲得的服務，與平均服務量比較，產生 UP/DOWN/KEEP。

先講直覺，再放公式：低於平均的 30% 產生 UP、高於平均產生 DOWN，其餘 KEEP；平均包含所有設定的來源。這是服務歷史分類，資料來源是成功 fire。需求尚未進入 FIFO 的部分，在量測設計中另行觀察。

用兩條時間線說明本專案 Main：`H → B_H → L` 與 `L → B_L → H`。第一個支持變動的 window 先形成待確認狀態，第二個同方向 window 才改變有效服務類別；KEEP、相反證據、零服務 window 取消待確認狀態。把「Buffer 是分類狀態」標在時間線上，避免與 request FIFO 混淆。

時間線旁明確分成「原論文文字的設計意圖」及「本專案的確定規則」。原文 §IV-C 說 Buffer 保留前一優先權，Algorithm 2 的 `P_last` 賦值則會在 Buffer 中採用目標類別。因此 Main 與 Algorithm-2 reconstruction 都保留在比較中。狀態機展示平滑的機制；它是否改善 burst/role-switch 的實際延遲，交由 H1 實驗判定。

**接到 §3 的邏輯**：概念中的一次分類與一次服務，在 RTL 中必須有唯一的 clock-edge 行為。

### §3 From FAI to an Executable RTL Contract（約 750 詞）

**讀者離開本節時應理解：分類、分配服務額度、選擇 request 是三個相連的步驟。**

先說共同資料路徑：N 個 depth-D FIFO、105-bit descriptor、單一輸出及 ready/valid。用一張小圖定義 `fire = valid && ready`，只有 fire 消耗服務額度與移除 FIFO head；stall 時持有 descriptor 及 grant context。Length 保留為 descriptor 欄位，每筆消耗一次原子服務。

依用途交代 Main 的狀態：B[h]/S 服務計數器、四態分類、類別 quota、排序 timestamp、held grant。window 關閉時先計入 closing fire，再分類與清零；已經輸出的 stalled request 延續原先 grant。位寬與完整轉移表放 compact table/附錄，主文解釋理由。

用一個差異表交代 original FAI concept、Main、Algorithm-2：Buffer 的有效類別、KEEP/idle、單輸出 10/10 alternation。將原 §4.5 的內容明確命名為 **FAI-Inspired Class Arbitration and Window Updates**，不再讓它看起來像所有 policy 共用規則。

最後才引入 CGOF，作為比較分配單位的設計：Main 每次給一個類別最多十次服務；CGOF 將 credit 指派給各個來源，選最老的 eligible head。沿用四態分類，權重為 High:Low 1:1 或 2:1；credits 用完後 refill，fire 才提交，hold 保留 context。這些是本地服務額度，與 CXL link flow-control credits 分開命名。

**接到 §4 的邏輯**：已定義可重現的服務規則，接著建立能同時觀察等待、分配與硬體成本的共同實驗。

### §4 Common Platform and Measurement Method（約 800 詞）

**讀者離開本節時應知道每一個結果量了什麼、如何比較。**

先列 platform 與 policies，再列 traffic、metrics、硬體量測，最後交代統計。模型的 WRR/IWRR controls 與已有 RTL policies 在方法表用不同列呈現。N4 的新 seed confirmation、N8/N16 五 seed exploration、最新模型 20 seed、單 seed production RTL，各有自己的實驗單位。

等待時間用 request 的 generation、acceptance、fire 三個時點：`L_GF = L_GA + L_AF`。這個等式對每筆 request 成立，各段 P99 不具一般可加性。主圖的 mean run-P99 是先算每次 run 的 P99，再跨 seed 平均；不要改成 pooled P99。Heavy 用服務份額、gap P99、每 run 最大 gap，以及 mixed/isolated completion ratio 觀察。

公平性先說目標：等需求看等份額；指定權重看相對權重的份額；異質需求同時呈現 demand-share error 與 Sparse-only Jain。Raw Jain 可作描述值，但評價必須對應目標。完整 drain 的服務份額也要搭配 measurement-phase 與 subwindow 數據，因為所有有限工作完成後，份額會受到輸入總量直接決定。

PPA 首次完整寫作 **power, performance, and area**，在本節再次定義：power 是指定活動的估計，performance 是硬體 timing，area 是完整設計的 library cell area。行為上的 latency/throughput 另有明確指標。共用 FIFO、interface、服務容量、library、corner、clock 與工具約束；各 policy 必要的 metadata 計入成本。RR 無 timestamp，FCFS/FAI/CGOF 有 timestamp。

統計以 seed 配對，同一比較共用 generation 與 sink-ready 輸入。原 N4 confirmation 使用 seeds 529–548、10,000 次 paired bootstrap。診斷模型 seeds 6201–6220 另外成組；不得合併成 40 seeds。確定性的等需求結果報精確份額，不以零寬 CI 增強可信度。完整實驗 ID、hash 與 EDA warnings 移入 evidence supplement；主文保留影響數值解讀的條件。

**接到 §5 的邏輯**：先回答觀察到什麼，再以控制組解釋機制，最後衡量硬體代價與適用場景。

### §5 Results, Mechanism Diagnosis, and Implications（約 1,600 詞）

順序固定為：5.1 Main 與 FCFS/RR 的 tail 差異；5.2 class quota 與 per-source credits；5.3 Sparse 收益與 Heavy 代價；5.4 完整硬體成本；5.5 使用條件與後續問題。約略分配 300/350/350/350/250 詞。

5.1 先用既有七 policy 的 N4 圖建立現象：Main 改善 FCFS，但 burst 下 RR10 更低。RR quantum、class quota、FIFO depth 敏感度用來提出「分配服務機會如何影響 tail」這個問題。N8/N16 對 Main/RR10 的結果延續同一比較，勿用它代替 CGOF 擴展效能資料。

5.2 再用 fixed-class 機制控制解釋：當 Low 有一個 host、High 有三個 host，Main 的 10/10 是兩個類別各半；CGOF 1:1 是每來源各四分之一；CGOF 2:1 是 Low 1/7、每個 High 2/7。這是固定分類、持續 backlog 的分配算術。接著展示 live-classifier 等需求 RTL：兩種 CGOF 都取得接近各四分之一，途中 B_H 仍保持 effective High，說明「權重參數不同」不表示所有場景都產生不同份額。排序的額外作用交給 H2 的 matched controls；既有 continuous-backlog 的零差異只描述該情境。

5.3 將 Sparse P99 與 Heavy gap 放同一張圖，依 evidence tier 分 panel。20-seed 模型與單 seed RTL 分開標註。說明 Heavy 的總完成時間與短期等待節奏是不同問題；把實際的 gap 成本與 tail 收益一起呈現。

5.4 回到最初的硬體問題：先給完整 baseline area breakdown，再給最新 CGOF 六組 area/STA。N4 CGOF 2:1 與 Main 完整面積接近，RR 成本較低；由 timestamp、policy 與 common logic 解釋。呈現 existing baseline power，CGOF 欄位留作未量測。1:1 的 dead classifier state 要在實作表註腳解釋，使讀者理解 observable equivalence 與綜合結果。

5.5 將結果轉成選擇原則：重視實作成本可看 RR；重視所測 Sparse tail 可看 CGOF，同時衡量 Heavy gap 與明確配置的份額。說明一筆一服務的 scheduler 模型、W5M、backpressure 與 fan-in 的條件。系統 response/application 指標列成下一層研究問題，而非在每段重複否定句。

## 4. 必須帶入的已完成結果

### E1：既有 N4 RTL confirmation，20 seeds 529–548

資料：[revision_v3_results.tex](../generated/revision_v3_results.tex)、[plot-data.json](../generated/figures/plot-data.json)。A 為獨立到達、B 為 burst；數值為 Sparse generation-to-fire mean run-P99，單位 cycles。

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 18.10 | 33.45 |
| RR1 | 2.00 | 16.65 |
| RR10 | 11.00 | 17.70 |
| FAI-inspired | 10.00 | 21.05 |
| Algorithm-2 | 10.00 | 21.35 |
| BLISS-inspired | 1.15 | 33.00 |
| CGOF (2:1) | 1.10 | 12.35 |

CGOF 2:1 相對 Main 的 paired delta 為 A -8.90，95% CI [-9.00, -8.75]；B -8.70，CI [-9.50, -7.90]。Main 相對 RR10 的 B delta 為 +3.35，CI [2.25, 4.45]。N8/N16 的五 seed exploration 中，Main 的 B P99 為 27.60/34.80，RR10 為 21.00/24.40。

### E2：10 月 28 日模型分配控制

資料：[DIAGNOSIS_SUMMARY.md](../../experiments/diagnosis-20261027/DIAGNOSIS_SUMMARY.md)。Equal-demand 180 jobs、fixed-class 100 jobs、finite-Heavy 300 jobs 均已完成；三組各使用 seeds 6201–6220。

| Fixed-class、equal-demand、持續 backlog | Low / High / High / High 服務份額 | 用途 |
| --- | --- | --- |
| Main 10/10 | 49.9975 / 16.6708 / 16.6658 / 16.6658% | 類別各半，類別內再分配 |
| CGOF 1:1 | 25.0013 / 25.0013 / 25.0013 / 24.9963% | 每來源近似等額 |
| CGOF 2:1 | 14.2857 / 28.5714 / 28.5714 / 28.5714% | 明確的 High:Low 權重 |

正常 live-classifier 的模型等需求端點中，Main、FCFS、RR10 與兩種 CGOF 皆接近各 25%。固定 WRR/IWRR 2:1 的目標則是 40/20/20/20%；以 weighted Jain 評估。分類名稱 High/Low 與需求名稱 Heavy/Sparse 必須分開。

### E3：有限 Heavy 的最新模型結果與 RTL 結果

20-seed MODEL_ONLY overload，W5M、N4/D16：

| Policy | Sparse P99 | 平均每 run 最大 Heavy gap | Heavy completion ratio，mixed/isolated |
| --- | ---: | ---: | ---: |
| Main | 28.30 | 7.00 | 1.2002146 |
| CGOF 1:1 | 4.15 | 7.55 | 1.2004486 |
| CGOF 2:1 | 4.85 | 9.55 | 1.2004373 |
| WRR 2:1 | 10.00 | 7.35 | 1.2003968 |
| IWRR 2:1 | 8.70 | 7.35 | 1.2004261 |

CGOF 2:1 相對 Main：Sparse P99 delta -23.45，CI [-23.80, -23.15]；最大 Heavy gap delta +2.55，CI [2.10, 3.00]。Completion ratio delta +0.0002227，throughput ratio delta -0.0001544；用數值表達幅度，避免將「接近」寫成已證明統計等價。

production RTL run `20261027T195414Z_1179`：seed 6201、finite Heavy 5,000,000 requests、兩 quota 各 mixed/isolated。兩種 quota 的 active cycles 都為 6,248,272 / 6,248,269，completion ratio 1.00000048。Sparse P99 為 1:1 的 3 cycles、2:1 的 4 cycles；Heavy 最大 gap 為 9/10，isolated 為 7；Heavy G-to-F P99 為 mixed 23、isolated 7。此組資料顯示 completion ratio 相同，但 gap 與 Sparse P99 可不同。與上表使用不同情境，圖中不得直接拼成相同 workload 的五 policy RTL 比較。

### E4：三個完整 window 的等需求 RTL

run `20261027T203657Z_1135`，seed 6201、N4/D16、三個 W5M windows。兩種 CGOF 的 measurement fires 都是 3,750,000 / 3,750,000 / 3,750,000 / 3,749,999；加 drain 後 generated = accepted = fired = 15,001,085。

兩個設定的 raw classifier trace 都是第一個邊界 `[B_H, B_H, B_H, H]`，第二、第三個邊界 `[H, H, H, H]`。`B_H` 仍以 High 服務，因此這些邊界的 effective class 全為 High，不能寫成三個 host 已降為 Low。這也解釋此例沒有形成不同類別間的權重競爭；相同結果不代表一般混合類別場景中權重無效。各來源 G-to-F P99 都是 1,086 cycles，外部 producer backlog 是此情境的重要等待來源。段落說明量測邊界，不把各段 P99 當作一般可相加的量。

### E5：最新 CGOF 六組完整 area/STA

資料：[CGOF_RTL_PPA.md](../../experiments/diagnosis-20261027/CGOF_RTL_PPA.md) 與同目錄診斷摘要。D16、W5M、TT 0.78 V/25 C、25 ns；area 為 library cell-area units，slack 為 ns。

| Policy | N | 完整 cell area | Setup slack | Hold slack |
| --- | ---: | ---: | ---: | ---: |
| CGOF 1:1 | 4 | 106163.066946 | +12.683299 | +0.034898 |
| CGOF 1:1 | 8 | 212027.006396 | +8.135937 | +0.054674 |
| CGOF 1:1 | 16 | 423513.448454 | +3.158005 | +0.078278 |
| CGOF 2:1 | 4 | 109794.784709 | +10.398800 | +0.038578 |
| CGOF 2:1 | 8 | 218863.734160 | +5.675092 | +0.103860 |
| CGOF 2:1 | 16 | 436771.124393 | +1.248813 | +0.084335 |

六組報告皆為零 timing violations。1:1 的 mapped proof 有 138/230/414 個 unread classifier-accounting DFF，使用 observable-boundary equivalence 的範圍描述。2:1 N4 的 9,126 compare points 全通過。完整 correctness matrix 有 463 tests，另有 17 model unit tests。

N4 Main area 110089.845892，CGOF 2:1 相差 -0.268019%；完整設計成本相近，top glue 亦有小幅差異。既有 Main 對 RR10 的完整 area 增幅跨 N 為 38.22–39.27%。N4 baseline power 的三 seed A/B 均值：FCFS 3.356/3.356 mW、RR10 2.559667/2.560000 mW、Main 3.466667/3.466000 mW；沿用原本 zero-delay/no-SDF、ideal-clock 活動與 table-range 註記。CGOF power 尚無結果，不能從 area 推算。

## 5. 圖表與現稿的具體搬移

| 現有內容 | 改後位置與動作 |
| --- | --- |
| Introduction 的 498 rows、accepted/source-bound 等敘述 | 實驗規模移 §4 表格，hash、接受流程移 evidence supplement；引言聚焦問題與研究路徑 |
| Related Work and Adaptation Boundaries | 分配到 §1–4 對應問題；完整文獻比較留附錄 |
| Six Baselines 中的 FAI 計數/分類及 Buffer 說明 | 概念放 §2；可執行規則放 §3；參數表放 §4 |
| CGOF 在摘要/引言過早出場 | 摘要按背景、方法、結果順序簡述；主文 §3 在 class quota 定義後介紹，§5 先展示 Main 現象再診斷 |
| 原六張結果圖 | 保留 confirmation 與 sensitivity；加入 Buffer 時間線、fixed-class 份額圖、Sparse/Heavy tradeoff 圖；合併重複結果 panel |
| 原 N4-only CGOF hardware 表 | 換成 E5 六列；保留 N4 成本比較及 dead-state/coverage 註腳 |
| diagnosis 仍只有 W256 smoke 的敘述 | 更新為 E2–E5 的已完成工作；既有 498-row matrix、960 endpoint reanalysis、580 model jobs 與新增 RTL/PPA 分開計數 |
| 舊 NOT_RUN/status 段落 | 以 dated experiment summary 和 raw binding 更新。STATUS、PROGRESS_TRACKER、README 中 10/27 checkpoint 尚有過時狀態，修稿時一併同步，歷史紀錄保留 |

圖表先回答一個問題，再接下一個問題。硬體 panel 的 N8/N16 結果不能用來填補 CGOF N8/N16 behavioral confirmation；舊 endpoint reanalysis 中的顯示名稱應回查原 policy/configuration identity 後才重用。

## 6. 寫作方式與教授回饋對照

每段先給讀者需要理解的機制或觀察，再附數據與解釋。將有效範圍寫成量測條件，集中在方法表、圖說與末節。避免在引言連續列「我們沒有證明什麼」，也不把限制刪掉而放大結論。

| 教授回饋 | 完成修稿的判準 |
| --- | --- |
| FAI 太簡短、Buffer 如何平滑 | §2 有服務歷史直覺、兩條時間線；讀者能區分分類狀態、有效類別、FIFO |
| CXL 背景與 Ethernet 比較 | §1 有 memory access 路徑、共享競爭點、通用仲裁共同點與本研究的 CXL 動機 |
| §4.5 是否屬於 FAI | §3 明確命名 FAI arbitration/update；common contract 與 policy-specific rules 分開 |
| PPA 與 controlled comparison 不清楚 | §4 展開縮寫並定義三個量，列固定條件與需要計入的 policy metadata |

## 7. 實作順序與完成檢查

1. 讀取 agent-handoff.json；檢查來源 hash 與資料可讀性。若來源有新結果，先更新本計畫的 evidence snapshot，再決定新增段落。
2. 按 §1–5 重組 v3 可編輯本文，先完成背景、Buffer 例子與共同方法，再填結果。原始 progress report 保留。
3. 擴充既有 generate_revision_v3.py 與 figure generator，使 E2–E5 從具來源綁定的 JSON/reports 產表；先處理 raw policy identity，勿直接從顯示名稱推斷 configuration。不要手改 generated numerical rows。
4. 製作圖 1 架構切片、圖 2 Buffer 時間線，以及結果 panels。每張圖說標示 metric、單位、N/D/W、seed 數與 MODEL_ONLY/RTL/pre-layout 類型。
5. 更新相依 tests、evidence manifest、README 與 QA；執行既有 report/figure checks、縮寫/引用檢查、兩次 LaTeX 編譯與逐頁檢視。頁碼/檔名/日期只在成功產出後更新。
6. 檢查五步閱讀順序、FAI/Main/Algorithm-2 差異、P99 estimator、Heavy/Sparse 與 High/Low 命名，以及各結果是否連回一個研究問題。

本計畫已完成來源閱讀與結果交叉對照；後續假說尚無新增測試結果。H1–H5 的狀態由獨立實驗檔管理，當結果支持、反駁或只適用於部分情境，都應按其實際方向修稿。
