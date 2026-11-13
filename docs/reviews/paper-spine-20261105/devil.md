# Devil's Advocate 獨立審查

日期：2026-11-05  
範圍：docs/final-report/main-v3.tex、sections/hotnets-body-v3.tex、cxl-scheduler-revised-20261102.pdf、generated/update_20261102_results.tex、update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md，以及相關綁定證據。  
限制：只讀；未修改稿件、未跑實驗、未重跑分析、未 SSH、未讀其他審查者的審查結論。以下 hash/manifest 只當作檔案身份，不當作科學正確性的證明。

## 先說可確認的部分

- C1/C2 的主要數字與我看到的表格/JSON 一致：CGOF (2:1) 的 1.10/12.35 cycles、20/20 seeds 改善、finite-Heavy 的 3/4 cycles 與 9.45/10.85 cycles，均能在綁定表中對上。
- C3 的 W256 結果 正確地標成 NOT_CONFIRMED（7/20 joint strict improvements，gate 15/20），沒有被寫成成功。
- C4 的 W5M 5-seed 結果 正確地標成 descriptive exploration，且 Q1 gap 的 +1.6 cycles 只在五個種子中描述，沒有冒充二十種子確認。
- 稿件對 CXL 邊界是誠實的：single-output descriptor slice，不明示 CXL protocol、cache coherence 或 application-level equivalence。
- 1:1 與 2:1 在 near-load finite-Heavy 的差異（3 vs. 4 cycles；9.45 vs. 10.85 cycles）在正文與表格中一致。

這些是正確的結論；下面的問題不否定量測，而是主張的範圍與因果歸屬。

## 問題

### D1（重大）「primary lever」的因果結論不被配額×排序實驗支持

位置：docs/final-report/sections/hotnets-body-v3.tex:296（PDF p.14）。原句：「confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever.」

證據：artifacts/implementation/cgof-rtl-ordering-confirmation/analysis-20261101T045246Z.json#primary_rows。以 W256 的 Sparse P99 為例，Q2-OF−Q1-OF（配額主效應）為 0 在 12/20、+1 在 6/20、−1 在 1/20、−10 在 1/20（seed 6508），平均 −0.25 cycles；排序效應 d2 為 0 在 13/20、−1 在 7/20，平均 −0.35 cycles。也就是說，平均而言排序效應沒有比配額效應小，兩者都不到一個 cycle；唯一的大幅配額變化是單一 seed 的 −10 cycles。W5M 5-seed 則是 Q1-OF 11、Q2-OF 12（配額 +1，較差），Q2-RR 11（排序 −1，較好）。（Table 8 只印 d1/d2/I；配額主效應是我從 primary_rows 的 S 值讀出。）現有資料不支持「credit allocation 是主要槓桿」的穩定排序。

為什麼是問題：這句話把一個沒有被識別出來的因果主效應寫成結論。配額與排序在 W256/W5M 是兩個 factor；平均效應接近，且配額的大效應只出現在一個 seed。這會讓讀者以為實驗已分離出主要機制，實際上只看到兩個小且不穩定的對比。

最小修正：刪除「primary lever」，改成「in these cohorts, the mean Sparse-P99 changes from quota and ordering were both about one cycle or less; the experiments do not establish a stable ranking between them」。若一定要保留配額的單一 seed 觀察，應明寫「one seed showed a 10-cycle quota reduction; this was not a stable main effect」。

新實驗：不需要即可縮回。若作者要保留「credit allocation is the primary lever」，需要一個有足夠檢定力的 factorial quota×ordering 設計（或更多 seeds 的預先註冊主效應分析），不能靠現有 20 seeds 的事後平均。這是「保留更強主張」才需要的實驗，不是縮回主張的必要條件。

### D2（重大）「strongest overall operating point」沒有定義聚合規則，且與 1:1 的優勢不一致

位置：docs/final-report/sections/hotnets-body-v3.tex:294（PDF p.13–14）。原句：「CGOF provides the strongest overall operating point across the three specified objectives...」

證據：
- docs/final-report/generated/revision_v3_results.tex:18：trained A/B confirmation 只有 CGOF (2:1)，沒有 CGOF (1:1)。
- docs/final-report/generated/improvement_results.tex:42-43：model overload 中 1:1 的 Sparse P99/Heavy gap 是 4.15/7.55，2:1 是 4.85/9.55。
- docs/final-report/generated/improvement_results.tex:57-58：production RTL 中 1:1 是 3/9，2:1 是 4/10。
- docs/final-report/generated/improvement_results.tex:14,17：N4 area 1:1 是 106,163.066946，2:1 是 109,794.784709。
- 稿件自己在 :294 也承認 1:1 的 Sparse tail 與 maximum Heavy gap 都比 2:1 好。

為什麼是問題：「strongest overall」不是量測量，而是需要事先定義權重或 dominance 的判斷。現在唯一支持 2:1 的 trained A/B 證據沒有 1:1 對照；在 Sparse tail、Heavy gap 與 area 這三個共同量測上，1:1 反而更好；2:1 只在 model overload 的 completion ratio 上有極小優勢（1.2004373 vs. 1.2004486）。把 2:1 寫成整體最佳，會讓讀者以為三個目標已被同一個設定同時勝出，但資料只支持「2:1 在 trained A/B 這個未測 1:1 的比較中大幅降低 Sparse tail」。

最小修正：把句子改成 範圍明確的版本，例如：「In the trained A/B cohort, CGOF (2:1) is the tested configuration and gives the largest measured Sparse-tail reduction versus Main. In the near-load finite-work, model-overload, and area comparisons, CGOF (1:1) is better. The evidence does not identify a single best CGOF setting across workloads.」同時保留「not a universal winner」的邊界。

新實驗：不需要即可縮回。若作者要保留「2:1 is strongest overall」，需要 trained A/B 的 CGOF (1:1) 對照，以及一個預先宣告的多目標聚合規則（或 dominance 證明）。這是保留更強主張才需要的實驗。

### D3（次要）W256 的 Q1 Heavy-gap 被錯歸給兩個 campaign

位置：docs/final-report/sections/hotnets-body-v3.tex:296（PDF p.14）。原句把「the twenty-seed W256 ordering confirmation ... and five-seed W5M production exploration」並列，說兩者都「raising Q1 worst-case Heavy gaps」。

證據：docs/final-report/generated/update_20261102_results.tex:6：W256 的 Heavy max gap Δ，Q1-RR 是 +0.00，註記 0/20 Q1 diff；同檔 :8：W5M 的 Q1 才是 +1.6（+2,+2,+1,+2,+1）。W256 的 JSON primary_rows 也顯示 Q1 的 d1 全部為 0。

為什麼是問題：這是 conclusion 段落的局部事實錯配。Abstract 已經正確把 +1.6 限縮到「five-seed W5M production runs」，但結論把 W256 也拉進來，讀者會以為二十種子確認支持 Q1 gap 上升。實際上 W256 的 Q1 gap 沒有變。

最小修正：改成「W256 found no Q1 gap change (0/20); the five-seed W5M exploration observed +1.6 cycles (descriptive).」把兩個 campaign 的結果分開寫。

新實驗：不需要；現有表格已足夠。

### D4（次要）「per-source fairness」實際上是 weighted fairness，不是等比例 per-source fairness

位置：docs/final-report/sections/hotnets-body-v3.tex:294（PDF p.13–14）說「per-source fairness under asymmetric class cardinality」；同稿 :239 明確寫 CGOF (2:1) 給 Low 1/7、每個 High 2/7。

證據：docs/final-report/generated/improvement_results.tex:31 的 fixed-class shares 是 14.2857 / 28.5714 / 28.5714 / 28.5714；fixed-class shares 本身已足以證明 2:1 是依權重的 fairness，不是每個 source 拿到相同份額。

為什麼是問題：「per-source fairness」單獨讀會理解成 equal per-source shares；但 2:1 的 Low 只拿到每個 High 的一半。稿件其實已經有 weighted Jain 與 1:1 的 equal-share 版本，這個標籤會讓貢獻聽起來比量測更強。

最小修正：改成「weighted fairness under the stated 2:1 weights」，並補一句「CGOF (1:1) is the equal-share variant; the 2:1 setting intentionally gives Low half the per-source share of each High」。若語意是「消除單一 Low 佔 50% 的 class-quota skew」，就把「skew」限定成 class-cardinality skew，不要寫成一般 per-source fairness。

新實驗：不需要；fixed-class shares、weighted Jain 與 1:1 資料已足夠。若作者要主張 equal per-source fairness，應改用 1:1 的結果，而不是 2:1。

## 未覆蓋與次要觀察

- 新穎性：我只做了有限的新穎性檢查，沒有檢索外部文獻，也沒有和 prior per-source credit / DRR / WRR / FAI-CXL 的實作做完整比較。因此我不主張任何 novelty defect；只能說稿件內部把貢獻定位為 RTL reconstruction + CGOF study，沒有宣稱首創性。外部 novelty 仍未覆蓋。
- 硬體完整性：generated/revision_v3_results.tex:83 與 docs/experiments/revision-20261023/DAC_PPA_RESULTS.md:38,49,58 顯示 N4 CGOF (2:1) 有 68 個 constant-disabled untested timing checks；稿件 :214 只說「constant-disabled checks remain disclosed in the raw coverage reports」，沒有給 68 這個數字。CGOF power is unmeasured 也已明說。因為稿件沒有宣稱所有 timing arcs 都 tested，我沒把它升為正式 finding；但若空間允許，應把 68 與「pre-layout area/timing」的範圍寫清楚，避免「complete hardware cost」被讀成完整 PPA。
- 視覺檢查：我看的是 PDF text extraction 與 page layout（p.9–14 的 tables/figures/captions），沒有做 pixel-level 的每個 figure 檢查；不從 hash 或 build 成功推論 visual readiness。
- Hash/manifest：我看到 hash-bound manifests，但只把它們當檔案身份。沒有重跑，也沒有把 hash 當成數值或因果正確性的證明。

## 優先順序

1. P0：先修 :296。刪除「primary lever」，把 W256 的 Q1 gap 與 W5M 的 +1.6 分開；這是最容易被 reviewer 直接抓到的因果/事實問題。
2. P1：修 :294 的「strongest overall」。把 2:1 限定在 trained A/B，把 1:1 在 finite-Heavy/model/area 的優勢寫明，取消「單一最佳設定」的暗示；同一段把「per-source fairness」改成「weighted fairness」。
3. P2：若版面允許，補上 68 個 constant-disabled untested checks 與「pre-layout area/timing」的範圍；這不影響主要結論，但能避免硬體 claim 被過度解讀。
4. 修完後只重讀受影響的段落與表格，不需要新實驗。若作者要保留更強主張，才需要：trained A/B 的 CGOF (1:1)、有檢定力的 quota×ordering factorial、CGOF SAIF power、以及把 constant-disabled arcs 打開的 STA。這些是「retain stronger claim」的條件，不是本輪縮回主張的必要條件。

## 實際檢視清單

- docs/final-report/main-v3.tex（全 91 行）
- docs/final-report/sections/hotnets-body-v3.tex（全 299 行）
- docs/final-report/cxl-scheduler-revised-20261102.pdf（15 頁；text extraction；p.9–14 的 tables/figures/captions）
- docs/final-report/generated/update_20261102_results.tex
- docs/final-report/update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md
- docs/final-report/generated/revision_v3_results.tex
- docs/final-report/generated/improvement_results.tex
- artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json（primary, counts, limitations）
- artifacts/implementation/cgof-rtl-ordering-confirmation/analysis-20261101T045246Z.json（primary_rows, secondary_contrast_summaries, setting_contrasts）
- artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json（performance.cohorts）
- docs/experiments/revision-20261023/DAC_PPA_RESULTS.md 與 docs/DEVELOPMENT_REPORT.md 的 68 untested 段落
- 未讀 docs/reviews/ 下其他審查者的審查結論；未修改稿件；未跑實驗、重跑分析或 SSH。




