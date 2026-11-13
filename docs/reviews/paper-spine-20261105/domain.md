# Domain Review — CXL Scheduler Manuscript

日期：2026-11-05
範圍：唯讀獨立 domain review；只使用現有稿件與已綁定證據。未修改稿件、未重跑實驗／分析、未 SSH、未讀取其他 reviewer 的 verdict。

## 結論

數值本身與目前 bound evidence 基本一致；我沒有發現核心數據造假或算錯。需要修正的是 claim 的範圍與歸因：稿件在幾個地方把「其中一個 variant 的優點」寫成「所有 CGOF settings 的優點」，並把一個 1-cycle 的 ordering 實驗寫成 allocation 是「primary lever」。這些是 reviewer 最容易直接引用表格反駁的地方。

| ID | 嚴重度 | 主要位置 | 問題 |
|---|---|---|---|
| D1 | Major | sections/hotnets-body-v3.tex:296 | 以 quota × ordering 實驗推論「per-source credit allocation 是 primary lever」，超出實驗設計 |
| D2 | Major | sections/hotnets-body-v3.tex:294 | 用複數「CGOF settings」合併 1:1 的等份公平與 2:1 的 41–89% 改善 |
| D3 | Major | sections/hotnets-body-v3.tex:282,288,290,294 | 「complete hardware cost」不含 CGOF power；1:1 面積不是同功能比較 |
| D4 | Minor | sections/hotnets-body-v3.tex:294 | overload 的 Heavy gap 範圍 1–2.55 混用了 near-load 與 overload |
| D5 | Minor | sections/hotnets-body-v3.tex:2 | 摘要的「universal improvement」與預註冊 15/20 gate 不一致 |

## D1 [Major] credit vs ordering 的歸因超過實驗設計

**位置**：sections/hotnets-body-v3.tex:296（「confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever」）；相關 :245、:276；摘要 :2。

**證據**：
- W256 confirmation：artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json 的 primary：d1 在 20/20 seeds 為 0；d2 與 interaction 為 −1 的只有 7/20，其餘 13/20 為 0，mean −0.35；verdict = NOT_CONFIRMED，gate 要求至少 15/20 joint strict improvements。
- W5M production：artifacts/implementation/cgof-rtl-ordering-w5m-production/acceptance-w5m-campaign-20261102T154205Z.json 的 summaries：5/5 seeds 為 S = 11/11/12/11（Q1-OF/Q1-RR/Q2-OF/Q2-RR），d1 = 0、d2 = −1、I = −1；Q1 Heavy max gap +1.6 cycles，Q2 為 −0.2。
- 生成表：docs/final-report/generated/update_20261102_results.tex:5-9 與稿件 :245 的數字一致。

**為何會被質疑**：這句話把兩個不同的對比混在一起。Q1→Q2 是 quota ratio 的改變；OF→RR 是 eligible ordering 的改變。兩者在資料中都只有最多 1 cycle 的 effect；而且在 OF 下 Q2 反而比 Q1 差 1 cycle（12 vs. 11），不是一個單向的 allocation 優勢。真正大的差距是 Main→CGOF（8.9/8.7 cycles），但這組 campaign 沒有重跑 Main，也沒有把「class quota vs per-source credit」與 ordering 做 factorial 分離。因此「primary lever」是超出資料的排序，且把「allocation unit」和「quota ratio」混為一談。

**最小修正**：改成 scope 明確的句子，例如：「Within CGOF, changing the 1:1→2:1 quota and OF→RR ordering each shifts Sparse P99 by at most one cycle in the tested regimes; the W256 confirmation is NOT_CONFIRMED and the W5M result is a five-seed descriptive tradeoff. These campaigns do not isolate the larger Main→CGOF difference; that difference is consistent with changing the allocation unit, but is not established here as the primary lever.」

**新實驗**：不需要新實驗即可改成上述較窄表述。若一定要保留「primary lever」的強主張，才需要把 Main 納入同一 factorial（allocation unit × ordering），或對 Main→CGOF 的差距做可辨識的分解；這不是目前稿件防禦性版本的必要條件。

## D2 [Major] 用複數「CGOF settings」合併 1:1 與 2:1 的互斥優點

**位置**：sections/hotnets-body-v3.tex:294（「they eliminate single-Low class-quota skew and reduce trained Sparse P99 by 41–89% relative to Main」）；相關 :239、摘要 :2。

**證據**：
- docs/final-report/generated/improvement_results.tex:24 的 fixed-class 表：FAI-inspired 49.9975/16.6708/16.6658/16.6658；CGOF (1:1) 25.0013/25.0013/25.0013/24.9962；CGOF (2:1) 14.2857/28.5714/28.5714/28.5714。
- docs/final-report/generated/revision_v3_results.tex:7 的 confirmation 表只有 CGOF (2:1) 的 1.10/12.35；CGOF (1:1) 的 trained A/B 沒有出現在此表。
- 41–89% 的算法是 1 − 12.35/21.05 ≈ 41.3% 與 1 − 1.10/10.00 = 89%，兩者都是 CGOF (2:1)。

**為何會被質疑**：CGOF (1:1) 才是 fixed-class 下每來源 25/25/25/25 的等份 variant；CGOF (2:1) 的 Low 是 14.29%、每個 High 是 28.57%，仍然是 1:2 的 per-source skew。說「they eliminate single-Low class-quota skew」對 2:1 不成立；說「reduce trained Sparse P99 by 41–89%」則只有 2:1 的數據。複數「CGOF settings」把 1:1 的公平性和 2:1 的尾端改善拼成同一個 claim，reviewer 只要對照 fixed-class 表就能反駁。

**最小修正**：拆成 variant-specific 的兩句：
- 「CGOF (1:1) equalizes per-source shares (25/25/25/25 in the fixed-class control).」
- 「CGOF (2:1) implements a 2:1 High:Low credit weighting; in the trained N4 A/B cohort it reduces Sparse P99 by 41–89% relative to Main, while the single Low source receives half the share of each High source in the fixed-class control.」

同時明確定義 fairness target：若目標是 per-source equal share，1:1 是對應 variant；若目標是 class-weighted 1:2 share，2:1 是對應 variant。不要把 2:1 稱為 per-source fair。

**新實驗**：不需要新實驗即可改成上述拆分。若一定要保留「CGOF settings（複數）同時消除 skew 又降低 41–89%」的單一 claim，才需要補 CGOF (1:1) 的 trained A/B，或重新設計一個同時滿足等份與 2:1 權重的 credit assignment；這已超出目前證據。

## D3 [Major] 「complete hardware cost」不含 CGOF power，且 1:1 面積不是同功能比較

**位置**：sections/hotnets-body-v3.tex:282（小節標題「Complete Hardware Cost」）、:290（「CGOF's area and timing measurements leave its power comparison open」）、:294（「complete pre-layout hardware cost」）、:288（1:1 的 classifier dead-state optimization）。

**證據**：
- docs/final-report/generated/improvement_evidence_manifest.json 的六個 hardware entries 全部是 power_status: "NOT_RUN"。
- docs/final-report/generated/improvement_results.tex:9 的 CGOF hardware 表只有 cell area、setup、hold；docs/final-report/generated/revision_v3_results.tex:63 的 power 表只有 FCFS/RR10/FAI-inspired。
- :288 明說 1:1 的 equal class weights 讓 classifier outputs 對 observable selection 無關，因此可以 dead-state optimize；這使 1:1 的 106,163.07 不是與 Main 同功能的完整成本。2:1 的 109,794.78（−0.268%）才是保留 classifier 的 like-for-like 面積比較。

**為何會被質疑**：稿件在標題與結論使用「complete hardware cost」，但 CGOF 的 power 沒有量測；area + timing 不是完整 PPA。另一方面，−3.567% 的 1:1 面積是因為 classifier 被優化掉，不能和 2:1 的 −0.268% 並列成同一種「complete cost」。稿件在硬體小節有揭露，但標題與結論的措辭仍會讓 reviewer 認為作者把「area/timing」寫成「complete hardware cost」。

**最小修正**：把 :282 與 :294 的「complete hardware cost」改成「complete area and timing cost」或「pre-layout area and STA」；在同一句加註「CGOF power is not measured」。面積比較以 2:1 為主；1:1 明確標成 observable-equivalent、classifier dead-state optimized，不作為與 Main 同功能的完整成本。

**新實驗**：不需要新實驗即可改成上述限定。若一定要保留「complete hardware cost」的強主張，才需要 CGOF gate-level SAIF power，以及一個保留 classifier 的 1:1 mapping；這兩項都是新實驗。

## D4 [Minor] overload 的 Heavy gap 範圍 1–2.55 混用了 near-load 與 overload

**位置**：sections/hotnets-body-v3.tex:294（「under overload contention they trade 1–2.55 additional cycles of worst-case Heavy inter-service gap」）。

**證據**：
- docs/final-report/generated/improvement_results.tex:36 的 model overload 表：Main 7.00；CGOF (1:1) 7.55（+0.55）；CGOF (2:1) 9.55（+2.55）。
- 同一份 generated results 的 production RTL 表（near-load，seed 6201）：CGOF (1:1) 9、CGOF (2:1) 10；二十-seed near-load RTL confirmation 是 9.45/10.85（+1.40），見稿件 :253 與 tab:finite-rtl。

**為何會被質疑**：句子說「under overload」，但 1.40 是 near-load RTL，不是 overload；overload 的 CGOF (1:1) 實際是 +0.55，低於 1。這個範圍把 near-load 的 +1.40 放進 overload 的下界，會讓讀者以為 overload 的最小代價是 1 cycle。

**最小修正**：改成「Under model overload, the CGOF 1:1/2:1 maximum Heavy gap is +0.55/+2.55 cycles versus Main; in the near-load RTL confirmation, 2:1 is +1.40 cycles versus 1:1.」這樣保留了 tradeoff，也把 cohort 分開。

**新實驗**：不需要。

## D5 [Minor] 摘要的「universal improvement」與預註冊 gate 不一致

**位置**：sections/hotnets-body-v3.tex:2（「not confirmed as a universal improvement at W256 (7/20 seeds, mean −0.35 cycle)」）；對照 :245（「at least 15/20 joint strict improvements」）。

**證據**：artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json 的 primary.gates：joint_strict_improvements = 7、joint_strict_required = 15；rule 是「No d2/I reversal in all 20 seeds and joint d2<=-1,I<=-1 in at least 15/20」；verdict = NOT_CONFIRMED。

**為何會被質疑**：「universal」暗示 20/20 seeds 都必須改善；實際 gate 允許 5/20 不改善，只要求沒有 reversal 且至少 15/20 joint strict。正文 :245 是精確的，摘要把 gate 寫成 universal，會讓統計範圍看起來比實際更強。

**最小修正**：改成「not confirmed at the pre-registered 15/20 joint strict improvement gate (7/20 seeds; mean −0.35 cycle)」。不需要新實驗。

## 我認為正確、應保留的結論

- **C1/C2/C3/C4 的主要數值與 bound evidence 一致**：C1 的 1.10/12.35、paired −8.90/−8.70；C2 的 3/4、9.45/10.85、+1.00/+1.40、3.05/3.00；C3 的 d1=0 in 20/20、d2/I mean −0.35、7/20、NOT_CONFIRMED；C4 的 S=11/11/12/11、d1=0、d2=I=−1、Q1 Hmax +1.6、Q2 −0.2、A=0。這些都能在 aggregate-current-20261029.json、confirmation-finite-heavy-fixed-20261029/aggregate.json、兩個 ordering acceptance JSON 與 update_20261102_results.tex 中對到。
- **FAI Main 與 FAI-ImmBuf 的區分是清楚的**：稿件明確說 Main 是 previous-effective-class hysteresis，ImmBuf 是 immediate-target reconstruction；10/10 class alternation 標成 project-defined，沒有宣稱與 FAI 原論文 cycle-identical。這個邊界應保留。
- **CXL extrapolation 的邊界是適當的**：稿件把 evaluated slice 限定為 single-output、equal-cost 105-bit descriptor，明確不宣稱 CXL protocol conformance、coherence、system-level response latency、completed bandwidth 或 application slowdown；C8 也把這些列為 NOT_RUN。這是正確的 scope，不需要弱化。
- **single-boundary finite-Heavy RTL 與 trained A/B、model overload 是分開的 cohort**：稿件反覆標明 near-load、one boundary、W5M 5M Heavy，沒有把 3/4 cycles 與 trained 1.10/12.35 混在一起。這個分離應保留。
- **C1 的 source-hash 混合不是 finding**：我對照了 confirmation-cgof-split-a-20261028/source_hashes_before.json 與 confirmation-cgof-resume-20261029c/source_hashes_before.json；兩者唯一差異是 AGENTS.md，RTL 檔案相同。因此我沒有把 source_variants 列為 provenance 問題。這是對 recorded hashes 的核對，不是對 RTL 的重新驗證。

## 實際檢視的檔案

- docs/final-report/main-v3.tex、docs/final-report/sections/hotnets-body-v3.tex（全文 299 行）。
- docs/final-report/cxl-scheduler-revised-20261102.pdf（pdftotext 文字抽取；未逐頁目視所有圖）。
- docs/final-report/generated/update_20261102_results.tex、generated/improvement_results.tex、generated/revision_v3_results.tex。
- docs/final-report/update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md、update-20261102/ACCEPTANCE_20261102.md。
- artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json、confirmation-finite-heavy-fixed-20261029/aggregate.json。
- artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json、cgof-rtl-ordering-w5m-production/acceptance-w5m-campaign-20261102T154205Z.json。
- generated/improvement_evidence_manifest.json 的 hardware entries 與 limits。

## 未覆蓋

- 沒有重跑 RTL、model、synthesis 或 STA；沒有重算任何統計。
- 沒有逐頁目視所有 figures，也沒有逐筆檢查 raw traces；只核對了 manuscript、generated tables、aggregate/acceptance JSON 與 PDF 文字。
- 沒有獨立重讀 FAI-CXL 原論文 Algorithm 2 的全文；稿件對 Main/ImmBuf 的描述我按現有文字接受，未把它當作本次 domain finding。
- 沒有直接檢查 commercial synthesis reports 的原始檔案；硬體數字以 improvement_evidence_manifest.json 與 generated table 的綁定值為準。
- 沒有讀取其他 reviewer 的 verdict；沒有用 hash 的存在推論科學正確性。

## 優先順序

1. **D2（variant conflation）**：先修 abstract 與 :294。這是最容易被表格直接反駁的 claim，且影響 fairness 這個核心賣點。
2. **D1（credit vs ordering attribution）**：修 :296 的 conclusion。資料支持較窄的「both effects are at most one cycle; the Main→CGOF gap is not isolated here」。
3. **D3（complete hardware cost）**：改標題與結論的措辭；用 2:1 作 like-for-like 面積比較，1:1 標明 dead-state optimized；加註 CGOF power NOT_RUN。
4. **D5（gate wording）**：把 abstract 的 universal 改成 pre-registered 15/20 gate。
5. **D4（1–2.55 range）**：把 overload 與 near-load 的數字分開寫。

以上 1–5 都不需要新實驗；全部是縮小或精確化現有 claim。只有在作者要保留更強版本（primary lever、complete hardware cost、CGOF settings 的單一公平/改善 claim）時，才需要 D1–D3 中列出的新實驗。
