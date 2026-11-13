# CXL 論文審查與優先修訂方案

日期：2026-11-05。方法：paper-spine，Devil’s Advocate、Methodology、Domain 三個獨立視角，加上主審對照。

**判定：既有核心結果可保留；結論需要修訂，現階段不宜宣稱整體最佳或 allocation 的主導因果已獲確認。優先以現有證據修正五項問題，無須先增加實驗。**

審查對象為現行 `docs/final-report/main-v3.tex`、`sections/hotnets-body-v3.tex`，以及已發布的 [2026-11-02 PDF](../../final-report/cxl-scheduler-revised-20261102.pdf)（15 頁，10 圖、9 表）。下列行號指本次讀取的現行 body（299 行），PDF 頁碼指發布版。來源與 PDF 有文字差異，見 R4。

本輪只新增審查文件，未改論文、RTL、runner、原始資料或既有圖表；未啟動、接續或重跑任何實驗。其他工作流中的新 campaign 不納入本版論文的已確認證據。

## 優先問題

### R1｜重大：結論把小幅非零代價寫成維持不變

**位置與原文：** [body:294](../../final-report/sections/hotnets-body-v3.tex#L294)，PDF pp.13–14：`preserving long-run Heavy completion and throughput`；同句稱 overload gap 代價為 `1--2.55` cycles。

**直接證據：** body:251 明列 model overload 的 completion ratio：Main 1.2002146、CGOF (2:1) 1.2004373，差 **+0.0002227**；Heavy throughput-ratio 差 **−0.0001544**。body:249 的 Heavy 平均每輪最大 gap 為 Main 7.00、CGOF (1:1) 7.55、(2:1) 9.55，對 Main 的差應為 **+0.55／+2.55 cycles**。body:272 的 near-load mixed−isolated 則另有 +3.05／+3.00 completion cycles，不能拿其他情境的零差覆蓋這些差異。

**審查者會反對：** 小幅變化仍是取捨；「維持不變」與結果段矛盾。`1--2.55` 也不是兩個 overload 設定相對 Main 的正確範圍。

**具體修正：** 寫成「model overload 下，CGOF (2:1) 的大幅 Sparse-tail 改善伴隨較小、非零的 Heavy completion／throughput 代價」，保留上述數字。將 overload 的 +0.55／+2.55，與 near-load RTL 的 2:1−1:1 gap **+1.40 cycles** 分開。

**新實驗：不需要。** 信心高。來源：主審 E1、Domain D4；數字可直接對照已生成表與正文。

### R2｜重大：ordering 對照未識別 allocation 是主要因果

**位置與原文：** [body:296](../../final-report/sections/hotnets-body-v3.tex#L296)，PDF p.14：`confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever`。

**直接證據：** body:245、Table 8，以及 [W256 analysis](../../../artifacts/implementation/cgof-rtl-ordering-confirmation/analysis-20261101T045246Z.json) 的 `primary_summary`：Q1 的 RR−OF 為 0（20/20）；Q2 與 interaction 在 7/20 為 −1，其餘 13/20 為 0，均值 −0.35，未達 15/20 gate，判定 `NOT_CONFIRMED`。四組都已有 per-source credits；實驗操弄的是 budget 與 eligible ordering，沒有交叉操弄 **class allocation vs. per-source allocation**。

W5M 五 seeds 是獨立的描述性探索，四設定 Sparse P99 為 11／11／12／11。結論的 `while raising Q1 worst-case Heavy gaps` 也應只歸給 W5M：其均值 +1.6；W256 的 Q1 gap 差是 **0（0/20 有差）**，見 generated/update_20261102_results.tex:6、8。

**審查者會反對：** 未確認 ordering 的優越性，不等於確認另一機制主導，更不是 ordering 等效或無效的證明。allocation 單位與 credit budget 不是同一因素。

**具體修正：** 刪除 `confirming ... primary lever`。分別報告 W256 未達 gate、W5M 的 1-cycle Sparse 差與 Q1 gap 代價；將固定類別份額的解釋歸給 allocation 算術，將 Main→CGOF 的改善保留為完整策略對比。摘要 body:2 的 `universal improvement` 改成「未達預先指定的 15/20 joint strict improvement gate」。Claim matrix C3 明確寫「確認實驗完成，superiority 未確認」，不標成零效應已確認。

**新實驗：限縮主張不需要。** 只有要保留「allocation 是主要因果」時，才需同 workload 下可識別 allocation 單位與 ordering 的對照。不能只增加現有 quota×ordering 的 seeds 便視為已識別。信心高。來源：Devil D1/D3、Methodology F3、Domain D1/D5、主審 E2。

### R3｜重大：跨情境的整體最佳與 variant 合併主張過強

**位置與原文：** [body:294](../../final-report/sections/hotnets-body-v3.tex#L294)，PDF pp.13–14：`strongest overall operating point across the three specified objectives`；隨後以複數 `they` 概括 1:1／2:1 的公平性與 trained P99 改善 41–89%。

**直接證據：** trained A/B 的 **10.00→1.10、21.05→12.35** 屬於 **CGOF (2:1)**，未提供 1:1 的 matched trained A/B 對照。near-load finite-Heavy RTL 則是 1:1 的 Sparse P99／Heavy max gap **3.00／9.45**，優於 2:1 的 **4.00／10.85**；N4 1:1 面積也較小。RR10 又有較低面積。固定非對稱類別下的 1/7、2/7 份額來自 model control；near-load RTL confirmation 的來源均為 effective High。相關位置：body:239–245、249–253、284–290；generated/revision_v3_results.tex 與 improvement_results.tex。

**審查者會反對：** 各情境不是同一份共同量測下的完整排名；列出三個目標、再說不是 universal winner，仍無法推出 overall strongest。1:1 的等份與 2:1 的 trained tail 數字也不能合併成兩個設定都有的成績。

**具體修正：** 改為條件式選擇：trained N4 A/B 中 2:1 相對 Main 的 tail／area 對比；固定類別 model 中 1:1 的等份、2:1 的指定加權份額；near-load RTL 中 1:1 的較佳 temporal regularity；RR 的面積優勢。把 41–89% 明確綁定 2:1。刪除 `strongest overall`，不新增任意綜合分數。

結論的 hardware 概括宜寫「含共用儲存與控制的 mapped cell area／evaluated timing」，與 body:219、290 的 pre-layout／power 未量測範圍一致。

**新實驗：不需要。** 若另要比較 1:1 與 2:1 的 trained 表現，才需新增同輸入對照；那是擴大主張，不是本輪修訂前提。信心中高。來源：Devil D2/D4、Methodology F2/F4、Domain D2/D3、主審 E3。

### R4｜重大（交付一致性）：現行來源修正尚未反映在發布 PDF

**位置與原文：** body:20、294；發布 PDF pp.1、13；[publication-20261102.json](../../final-report/publication-20261102.json) 的 source dependencies；[acceptance](../../final-report/update-20261102/ACCEPTANCE_20261102.md)。

**直接證據：** 現行 body:20 的 `The analogy does not establish CXL protocol conformance...` 等補充句，發布 PDF p.1 沒有；現行 body:294 以 `Within the evaluated N4 behavioral workloads...` 限縮，發布 PDF p.13 仍為 `Across the three specified objectives and measured scope...`。來源、PDF 的內容差異已直接比對，並非只憑檔案標記判斷。

**審查者會反對：** 修正過的 LaTeX 與交付讀者的版本不同，現行修正不能由舊 PDF acceptance 代為驗收。這不使原始量測失效，也不代表既有工作樹修改應被撤回。

**具體修正：** 論文修訂批准後，從明確指定的來源重建新版 PDF，讓發布索引、圖表、claim matrix 與驗收記錄指向同一版；保留歷史版及其適用範圍。

**新實驗：不需要。** 需要重新編譯、定位核對及成品目視檢查。信心高。來源：主審 E5。

### R5｜次要：W256 小樣本 P99 的解讀條件應隨結果呈現

**位置與原文：** [body:245](../../final-report/sections/hotnets-body-v3.tex#L245) 的 `Sparse P99`、body:264 的 Table 8；body:122 定義 nearest-rank。

**直接證據：** W256 analysis 的 `limitations` 已明載 P99 等於 sampled maximum。主審讀取 80 個 mixed jobs 的 `role_counts.sparse.fired`：每輪 **12–32 筆**；全部滿足 `ceil(0.99*n)=n`。

**審查者會反對：** 正文未把樣本量與結果放在一起，讀者容易將短 cohort 的極值解讀成穩定尾分布估計。20 seeds 的 bootstrap 不增加每輪的 Sparse 樣本量。

**具體修正：** 保留原預註冊 nearest-rank P99 名稱與 gate，在 Table 8／圖 10(a) 註明「每輪 Sparse n=12–32，因此此處 P99 等於觀測最大值」；與較長 W5M cohort 分開解讀。

**新實驗：不需要。** 若要改為穩態 population-tail 主張，才需不同採樣設計。信心高。來源：Methodology F1、主審 E4。

## 應保留的正確結果

| 結果 | 本輪判斷與適用範圍 |
|---|---|
| trained N4 A/B | Main Sparse P99 10.00／21.05，CGOF (2:1) 1.10／12.35；改善 8.90／8.70 cycles，即 89%／約 41.3%。已檢視的表格與 aggregate 相符。 |
| finite-Heavy RTL | 20 seeds 下 1:1／2:1 的 Sparse P99 3／4、平均每輪 Heavy max gap 9.45／10.85；保留單一 W5M 邊界與 all-effective-High 條件。 |
| ordering | W256 未達 superiority gate；W5M 五 seeds 的 11／11／12／11 與 Q1 gap +1.6 是描述性取捨。負面結果應保留。 |
| allocation | 固定類別且持續 backlog 時，Main 的 singleton Low 得 1/2、各 High 得 1/6；CGOF 2:1 的 1/7／2/7 符合指定權重。 |
| area／timing | N4 2:1 面積相對 Main −0.268%；六個 CGOF mappings 通過其已評估的 25 ns checks。這是既有 pre-layout 結果，未在本輪重新執行 EDA。 |
| scope | FAI Main 與 FAI-ImmBuf 的區別、project-defined 10/10 重建、single-output／equal-cost descriptor 邊界都應保留。 |

## 修訂順序

1. **先修結論的事實與因果：R1、R2。** 交付可直接對上既有表格的 Heavy 代價與兩個 ordering cohorts 結論；同步修摘要 gate 用語與 C3 語意。
2. **再修貢獻定位：R3。** 拆開 1:1／2:1、model／RTL、trained／finite-work，改成有條件的政策選擇。保留現有圖表及負面結果。
3. **補齊結果解讀：R5。** 將 W256 樣本數／極值註解直接放進相關表圖，不改數據或預註冊門檻。
4. **同步交付版本：R4。** 從批准後的來源建 PDF，確認受影響的摘要、結論、圖表與來源索引一致；完成成品視覺 QA。
5. **獨立複審。** 三個視角先讀修訂稿與證據，再對照 R1–R5，逐項判定是否結案；不得只以編譯成功或驗收標籤結案。此次尚未修稿，因此尚未執行修訂後複審。

本路線沒有以新增實驗作前置條件。多 seed 動態 RTL、under／over RTL、CGOF power、latency-recovery 與 CXL 系統整合，仍是擴大主張的後續工作，不阻擋這次依既有結果完成修訂。

## 獨立意見的主審裁定

- **加權份額不是錯誤。** 2:1 的 Low 得每個 High 一半是指定目標；原文 body:126、239 已區分 weighted／equal-share fairness。未採納「非等份就不公平」的判斷。R3 保留的是證據層級、variant 歸屬及 overall 排名問題。
- **1:1 的 dead-state optimization 是合理成本。** body:288 已揭露 classifier 對 observable selection 無效；不要求保留無用硬體，也不因其被最佳化就否定面積數字。未量 CGOF power 已在正文揭露，不能據此要求本輪補 APR 或完整 PPA。僅建議總結使用明確的 area／timing 名稱。
- **小樣本 nearest-rank P99 在數學上成立。** 未採納「保留 P99 名稱必須補實驗」的要求；R5 定為次要解讀問題，以補 n 與 maximum 註解解決。
- **不把 quota budget 當成 allocation 單位。** W256 個別 seed 的 quota 差可大於一 cycle；不採用「所有 quota 效果最多一 cycle」的表述。R2 只將 0–1 cycle 限定於已觀測的 ordering 對比。
- **新穎性未獲反證或認證。** 沒有新檢索外部文獻，不提出憑印象的 novelty／closest-baseline 重大缺陷，也不宣稱已完成文獻覆蓋。

獨立原始紀錄：[Devil’s Advocate](devil.md)、[Methodology](methodology.md)、[Domain](domain.md)；主審直接證據：[editor-evidence.md](editor-evidence.md)。各紀錄保留原始判斷，本報告為採納、合併與校準後的修訂依據。工具讀取紀錄可追溯至本次對話；完整 token／成本 telemetry 未提供，未以零值替代。

## 審查限制

未重跑 simulation、bootstrap、formal、synthesis、STA 或 power；未逐筆重建所有 raw traces；未新查外部文獻或獨立核驗全部引用。已讀發布 PDF 文字並局部目視 pp.13–14，未完成全 15 頁視覺 QA。本輪判斷支持沿用已檢視的核心結果，不構成完整實驗重現、全面新穎性驗證或投稿認證。
