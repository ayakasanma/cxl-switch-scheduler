# CXL Scheduler 方法學獨立審查

**日期：** 2026-11-05  
**範圍：** 目前稿件、PDF 渲染、2026-11-02 更新證據與 bound aggregates；唯讀審查。  
**判定：** 4 項可定位問題（3 MAJOR、1 MINOR），無 CRITICAL。主要結論在縮小措辭後可保留；現有證據不足以支持三項較強措辭。

## 發現

### F1 — MAJOR — W256 的「Sparse P99」實際上是 12–32 筆完成樣本的最大值

**定位：** `docs/final-report/sections/hotnets-body-v3.tex:245`（W256 的 `d2`/`I` 與「Sparse P99」）、`:264`（表列「Sparse P99 Δ」）、`:296`（結論「modifies Sparse P99 by at most one cycle」）。

**證據：** `artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json` 的 `counts.sparse_completed_per_mixed_job_range` = `[12, 32]`；同檔 `limitations` 明載「Small completed Sparse cohorts make per-run nearest-rank P99 equal to the sampled maximum.」

**為何是問題：** 每個 mixed job 只有 12–32 筆完成的 Sparse 請求時，nearest-rank P99 就是樣本最大值。W256 的 −1 cycle 與 7/20 gate 是最大值差，不是尾端百分位差；表格卻標成 P99。這不推翻 W256 的 `NOT_CONFIRMED`，但會讓讀者把一個小樣本極值當成可重複的尾端估計。摘要中的 12→11 是 five-seed W5M production（完整 cohort），不是 W256；兩者不應混用同一個 P99 標籤。

**最小修正：** 將 W256 指標改為「observed maximum Sparse G→F latency（每個 mixed job 12–32 筆完成）」並在表註明 n；保留原本 15/20 gate 與 `NOT_CONFIRMED`。只縮小措辭不需要新實驗。

**新實驗：** 若仍要保留 W256 的 P99 標籤，需要加大每個 run 的 Sparse 完成數；只改標籤則不需要。

### F2 — MAJOR — 公平性結論混合 fixed-class model 與 RTL，且「eliminate skew」與實測份額不符

**定位：** `docs/final-report/sections/hotnets-body-v3.tex:294`（「they eliminate single-Low class-quota skew」與「per-source fairness under asymmetric class cardinality」）；`:239`（CGOF (2:1) 為 Low 1/7、每個 High 2/7）；`:241`（fixed-class model）；`:272`（near-load RTL 為 B_H/H/H/H，所有來源有效 High）。

**證據：** `artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/aggregate.json` 的 `finite_heavy.groups` 顯示 high_weight 1/2、`classifier_transitions` 為 1；RTL confirmation 沒有進入非對稱類別競爭。1/7 與 2/7 是 `:239` 的 fixed-class 配置目標；其 measured counterparts（Figure 6/Table 3）是 model control，不是 RTL。

**為何是問題：** CGOF (2:1) 並沒有消除 skew；它把 Main 的「單一 Low 取得 1/2、每個 High 取得 1/6」換成「Low 1/7、每個 High 2/7」的宣告式 1:2 加權。Low 仍只拿到每個 High 的一半。其次，near-load RTL 全部維持有效 High，無法檢驗 asymmetric class cardinality 下的 per-source fairness；把這項 fairness 放進「strongest overall」的 RTL 範圍，會讓 reviewer 認為證據等級被抬高。

**最小修正：** 改寫為「replace the 1/2-versus-1/6 class-quota skew with the declared 1:2 per-source weighting; weighted fairness is exact under those weights, raw per-source equality is not claimed.」並把非對稱類別公平性明確歸給 fixed-class model control；RTL 只主張 all-High near-load 行為。只縮小措辭不需要新實驗。

**新實驗：** 若要在 RTL 保留 asymmetric class cardinality 下的 per-source fairness，需要 mixed-class、非對稱類別的 RTL cohort；現有 RTL 不足以支持。

### F3 — MAJOR — 結論用「confirming」描述一個 NOT_CONFIRMED 的 W256 與 five-seed 描述性 W5M

**定位：** `docs/final-report/sections/hotnets-body-v3.tex:296`：「The twenty-seed W256 ordering confirmation (NOT_CONFIRMED) and five-seed W5M production exploration show that eligible round-robin ordering modifies Sparse P99 by at most one cycle in Q2 while raising Q1 worst-case Heavy gaps, confirming that per-source credit allocation rather than intra-eligible ordering is the primary lever.」

**證據：** `artifacts/implementation/cgof-rtl-ordering-confirmation/acceptance-20261101T045246Z.json` 的 `primary.verdict` = `NOT_CONFIRMED`，`primary.gates.joint_strict_improvements` = 7、`joint_strict_required` = 15；`artifacts/implementation/cgof-rtl-ordering-w5m-production/acceptance-w5m-campaign-20261102T154205Z.json` 的 `status` = `COMPLETE_DESCRIPTIVE_EXPLORATION`，`claims_not_made` 明載「no inference from five seeds to a confirmatory population」。

**為何是問題：** 一個未達 gate 的 confirmation 與一個 five-seed exploration 不能 confirm primary lever。資料與「allocation 是主要槓桿」一致，但這是跨實驗的效果量對比，不是由 ordering campaigns 建立的普遍機制。用 confirming 會把 NOT_CONFIRMED 的證據等級反轉。

**最小修正：** 改為「is consistent with per-source credit allocation being the primary lever; the ordering campaigns do not confirm a universal ordering effect.」保留 W256 的 negative result 與 W5M 的 descriptive 標籤。不需要新實驗。

**新實驗：** 否；這是措辭與證據等級的修正。

### F4 — MINOR — 最終句的「complete hardware cost」超出實際量測邊界

**定位：** `docs/final-report/sections/hotnets-body-v3.tex:296` 最後一句「complete hardware cost」；對照 `:219`「single-corner pre-layout measurements; routing and clock-tree effects remain outside the measured implementation boundary」、`:290`「CGOF's area and timing measurements leave its power comparison open」、`:214` 表註「CGOF power is unmeasured」。

**為何是問題：** 稿件量到的是 cell area 與 evaluated setup/hold timing，且是單一角點、pre-layout；power 未量、routing/clock tree 未含。最終句用 complete hardware cost 會讓 takeaway 看起來包含 power 與 post-layout，超出實際證據。

**最小修正：** 改為「complete pre-layout area and evaluated timing cost」或「mapped cell area and evaluated setup/hold timing」。只縮小措辭不需要新實驗。

**新實驗：** 若要保留廣義的 complete hardware cost，需要 CGOF gate-level SAIF power 與 post-layout 量測；現階段不必要。

## 可確認的結論

- **C1 主比較的控制成立。** 20 個 paired seeds 的 A/B trace hash 全部相同；Main 與 CGOF 的 common RTL、Main RTL 檔案相同，source hash 差異來自新增的 CGOF 檔案、測試 driver 與 `AGENTS.md`，不是 Main/common RTL 的行為改動。Arm A 每個 run 有 2,263–2,412 筆 Sparse 完成（seed 529 為 2,388）、Arm B 固定 2,400 筆；P99 約為第 23–24 大的 order statistic，足夠支持 10.00/21.05 對 1.10/12.35 這個大差距的 scheduler-boundary 結論。CIs 是 seed-level，不是 request-level；稿件已如此說明。
- **C2 的數值與 aggregate 一致。** 20 seeds、40 pairs、5M Heavy；Sparse P99 3/4、max gap 9.45/10.85 與 `confirmation-finite-heavy-fixed-20261029/aggregate.json` 相符。CIs `[3,3]`、`[4,4]`、`[1,1]` 會退化，是因為 20 個 seeds 都給出相同的整數值；表註已寫「pointwise 95% CIs summarize seeds」，這是 seed cohort 的區間，不應讀成 population precision。1-cycle 差異是離散 service-round 效應。
- **C3 的 negative result 正確。** 20 seeds、160 jobs、80 pairs；7/20 joint strict improvements，低於預先規定的 15/20，`NOT_CONFIRMED` 的判定正確。唯一的問題是 F1 的 P99 標籤。
- **C4 是 descriptive。** 5 seeds、40 jobs、20 pairs；沒有 CI，稿件標為 descriptive exploration，沒有作 population inference。這是正確的。
- **C5/C6 與 C7 的 tier 分離正確。** C5/C6 是 `MODEL_ONLY`，沒有 application/system latency 主張；C7 是 single-seed、`confidence_intervals: null`，稿件標為 exploratory。這些標籤與 evidence matrix 一致。
- **Hardware 的面積算術正確。** N4 CGOF (2:1) 109,794.78 對 Main 110,089.85 的 −0.268% 無誤；six mappings 的 zero reported timing violations 是 evaluated checks，不是完整 timing closure。CGOF power 未量，稿件已揭露。

## 未覆蓋與不能確認

- 沒有 CXL system-level response latency、completed bytes、application slowdown；稿件列為 `NOT_RUN`。
- 沒有 CGOF gate-level SAIF power；不能說 CGOF 的 complete hardware cost 已被完整量測。
- 沒有 multi-seed W5M dynamic role-switch 或 under/over RTL confirmation；C7 是 single seed，不能外推。
- 沒有 RTL 的 asymmetric class cardinality fairness；這項目前只有 fixed-class model。
- 沒有 independent model validation；acceptance 明載 same-executor cross-check，不是 independent model validation。
- 沒有 population-level inference beyond the fixed 20-seed cohort/workload；所有 CIs 都是 conditional。
- 沒有 formal Pareto proof 支持 strongest overall operating point；這是 evaluated workloads 內的 bounded selection。
- Hash binding 只證明檔案身份，不證明科學正確性；本次沒有把 hash 當成 validation。

## 優先順序

1. **先修 F1 與 F2（純文字）。** 這兩項直接影響 abstract/table/conclusion 的可辯護性；改標籤與改寫 fairness 句子即可，不需要新實驗。
2. **再修 F3 與 F4（純文字）。** 把 confirming 改為 consistent with，把 complete hardware cost 改為 complete pre-layout area and evaluated timing cost。
3. **若作者要保留更強主張，才需要新實驗：** W256 的更大 Sparse cohort（保留 P99）、mixed-class RTL（保留 RTL fairness）、CGOF power/post-layout（保留廣義 complete hardware cost）。這些不是縮小現有 claim 的必要條件。

## 實際檢視

已讀：`docs/final-report/main-v3.tex`；`docs/final-report/sections/hotnets-body-v3.tex`（全 299 行，重點 53–130、197–296）；PDF `docs/final-report/cxl-scheduler-revised-20261102.pdf` 的文字抽取（pages 1–12，含 Figures 7–9 的圖說與數值）；`docs/final-report/generated/update_20261102_results.tex`；`docs/final-report/update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md`；`aggregate-current-20261029.json`；`confirmation-finite-heavy-fixed-20261029/aggregate.json`；`acceptance-20261101T045246Z.json`；`acceptance-w5m-campaign-20261102T154205Z.json`；`.setup-logs/implementation/revision-20261024/power-index/final498-20261027/snapshot/analysis/analysis.json` 的 endpoints/trace hashes；original 與 CGOF run 的 `source_hashes_before.json`；`generated/revision_v3_evidence_manifest.json`；`generate_revision_v3.py` 的 binding 邏輯。

未做：修改稿件、重跑實驗、重跑分析、SSH、讀取其他審查者的 verdict 文件。PDF 只做文字抽取與相關圖說核對，沒有做 pixel-level figure inspection。
