# 新結果之後需要補的機制實驗

日期：2026-10-29；最後核對：2026-10-30。狀態：PARTIAL EVIDENCE；A、B 兩項追蹤實驗已完成 `MODEL_ONLY` 階段，尚未取得同條件的 production RTL 確認；本檔其餘已完成部分只採 2026-10-30 的 single-seed 動態證據。先前列出的預測不能當作量測結果加入主文。沿用 [H1–H5 原協定](../improvement-20261028/HYPOTHESES_AND_EXPERIMENTS.md) 的來源凍結、配對、守恆、統計與報告納入規則；完整狀態以 [hypothesis-status.json](hypothesis-status.json) 為準。

## 已完成（2026-10-30）

證據目錄：[`cgof-dynamic-20261030`](../../../artifacts/implementation/cgof-dynamic-20261030/aggregate.json)，aggregate SHA-256 `e8a398b18348a99a3a20fc89e1d0086b5c75b31db093b9e1e9ebecbd76d649e8`。以下均為單一 fresh seed `7291` 的 descriptive probe，`confidence_intervals: null`，且 production RTL 只有 CGOF 設定。

- **Multi-window finite-Heavy：`SCHEDULER_RTL PASS (single-seed)`。** 5 個 case、20 個 RTL 結果、10 組 mixed/isolated 配對；每個結果都跨過四個實際 active W5M classifier 邊界，Heavy 工作全數完成。
- **Physical role switching：`MODEL_ONLY PASS; SCHEDULER_RTL PASS (single-seed)`。** Heavy source schedule `[0,0,1,1]` 產生三次有效 source-class transition；generation-time role 與 drainage cohort 均保留。
- **Minimal backpressure controls：`MODEL_ONLY PASS; SCHEDULER_RTL PASS (single-seed)`。** ready spread 與 bursty 的 realized ready fraction 分別為 `0.8999999863`、`0.9000001143`；在幾乎相同 availability 下，bursty 使 Sparse P99 與 Heavy wall-gap P99 同時由 3 升至 11，而 Heavy ready-opportunity gap P99 維持 2。這是最小的 ready-stall 對照，不是完整回壓矩陣。
- **D8 admission-boundary diagnostic：`MODEL_ONLY PASS; SCHEDULER_RTL PASS (single-seed)`。** D16 的 Heavy generation-to-acceptance P99 為 2、acceptance-to-fire P99 為 18；D8 改為 11、16，generation-to-fire P99 均為 20。這顯示等待位置移到 admission 前，不能推論 completion equivalence。D32 未通過預先篩選規則，未跑 production RTL。

上述結果沒有事先宣告 equivalence margin；小幅 completion-time 差異不得寫成「實質相同」。scheduler `fire/cycle` 也不是 memory bandwidth，generation-to-fire 不是 CXL response latency。

## A. 絕對 credit 大小是否透過 refill／re-entry 改變 tail？

**狀態：MODEL_ONLY PASS（2026-10-30）。**

**結果：** 既有 RTL decision trace 缺少 `credits`、`eligible`、`refill`、`held`、`re-entry` 與 `high_weight`，不足以建立 paired counterfactual，因此改以相同 arrivals／ready／all-High 的 deterministic replay，只把每來源絕對 High credit 從 1 改為 2。五個 Sparse 起點的結果為：起點 2 在 cycle 4、起點 4 在 cycle 7 首次因 refill 分歧；起點 6 在 cycle 7 首次因 eligibility 分歧；起點 3、5 沒有 selection divergence。全部 replay 均完成 drain 且守恆。這支持「絕對 credit 大小會透過 refill／re-entry 改變服務時序，且效果依 arrival phase 換位」，但不是普遍 latency bound。

證據：[`decision-trace.json`](../../../artifacts/implementation/followup-20261030/A-credit-refill/decision-trace.json)，SHA-256 `0c351647d5d27efe5a4d580053b3053e1facbbd8a4a9e8fbbbbc4a312026c704`。測試：`3 passed`。此結果不替代 W5M performance confirmation。

**現有證據：** 20-seed near-load RTL 都為 effective High，1:1 與 2:1 的相對份額目標相同，但 Sparse P99 與 Heavy 最大 gap 不同。兩者只在一個 seed 的 Heavy 完成時間相差一 cycle。程式及 coverage 已確認 eligibility、re-entry 與 refill 行為受到執行。

**待驗證解釋：** 二個 credits 保留的 eligibility 使 intermittent arrival 遭遇不同的服務序列；差異由 active set 與 refill 相位共同決定。

**最小實驗：** 先分析可取得的既有 decision trace；必要時以獨立短 model trace 重播相同 arrivals/ready、固定全 High，僅改每來源 budget 1／2。記錄 source ID、generation/accept/fire、oldest head、eligible set、remaining credits、refill snapshot、hold 以及 re-entry。把 Sparse arrival 逐步平移到 refill 前後，保留同一 burst 大小及總工作量。所有 trace 在共同的固定 horizon 量測並完成 drain，避免以不同 Heavy 完成時刻停止生成而引入不同 Sparse 尾端事件。這項 trace 實驗只解釋機制，主性能確認仍用 W5M。

**預期佐證：** 找出第一個服務順序分歧，將多出的等待 cycles 對應到 eligibility／refill 決策；變更 arrival 相位時，差異的位置隨之移動。若 trace 差異來自 producer、hold 或不同輸入，先修正對照。若 budget 改變但差異不隨預定事件變動，需修正該解釋。

**後續 agent 必交：** 逐筆 paired trace、首個分歧與後續傳播、各 phase 的效果量，以及可重現命令與 hashes。只將可由 trace 支持的部分寫為機制結論，不由單個 trace 推出普遍 latency 上限。

## B. 完成時間差很小，是否因 near profile 尚有平均剩餘容量？

**狀態：MODEL_ONLY PASS（2026-10-30；W5M exploration + 20-seed held-out confirmation）。**

**結果：** 先以 seeds `6101–6105`、`under/near/over`、phases `0/1/2`、兩種 CGOF 配額跑 90 個 W5M model pairs；再以未參與篩選的 seeds `6201–6220` 對 `under` 與 `over` 跑 80 個 confirmation pairs。兩批均 PASS，Heavy/Sparse 輸入配對與完整工作守恆成立，10,000 次 paired bootstrap 已啟用。確認結果：`under` 的 mixed−isolated Heavy 完成時間差為 `0` cycles，兩種配額的 95% CI 均為 `[0,0]`，全部落在預先宣告的 20-cycle（約 0.1%）margin 內；`over` 平均多 `834.25` cycles，95% CI `[820.4,849.3]`，completion ratio `1.0375525`，全部超出 margin。探索階段把 Sparse arrival 平移 1–2 cycles，Sparse P99 變化僅 `0–0.4` cycles，完成時間差為 `0`。因此目前支持「near/under 的未用服務機會吸收 Sparse 工作；跨過容量後才出現明確 Heavy 完成代價」，不支持 arrival phase 是主要因素。

證據：[`W5M exploration summary`](../../../artifacts/implementation/followup-20261030/B-arrival-phase-w5m-current-20261030/summary.json)（SHA-256 `a46c5b7506d92f233a5216833e0099b3527bf8c257a027c2483974901e16bcdb`）與 [`held-out confirmation summary`](../../../artifacts/implementation/followup-20261030/B-arrival-phase-confirmation-20261030/summary.json)（SHA-256 `92afb0f1bd189942864eb853286195d398de2cefcf3503c8fae1d1f2c268c9ac`）；兩批的 source hashes 完全相同。這些是 `MODEL_ONLY` 結果，不是 production RTL、application slowdown 或 calibrated CXL 證據。

**現有證據：** 名目生成率 0.86 requests/cycle、ready 機率 0.9；mixed 比 isolated 平均多 3.05／3.00 cycles。這是 observed effect；上列 B 實驗已另外在執行前宣告 20-cycle／0.1% 的 completion margin。

**待驗證解釋：** Sparse 工作主要利用 Heavy 未提供工作的服務機會，使有限 Heavy 的最後完成時間變化小；當總負載跨過容量或 arrival 與不可服務區段對齊時，此現象可能改變。

**最小實驗：** 在原 finite-work mixed/isolated 框架先做 under／near／over 探索，再對最具辨識力的配置做新 seed 確認。固定 quota、sink-ready trace 與 Heavy 工作量；另做 arrival 相位對照。需記錄實際 generated demand、ready opportunities、空 FIFO／非空 FIFO 下的空轉、active／drain 長度、Heavy 完成時刻、Sparse 等待及未完成事件。若研究分類反應，工作量必須足以跨過至少三個 W5M 邊界，並由 raw boundary trace 確認實際有效分類變化。

**預期佐證：** 在較低負載，Sparse 服務與 Heavy 無工作時段重疊較多；跨越容量後，這些機會不足且 Heavy 完成差／backlog 明顯變化。若變化主要由 class transition 或 backpressure 長段引起，改採分階段解釋。確認前先決定實務容忍範圍，才可進行「完成時間實質相同」的 equivalence 檢驗。

**後續 agent 必交：** 各負載／相位的配對效果、實際容量與 demand、boundary maps、ready-opportunity 與 wall-gap 指標；不得將 descriptor 完成時間替代 application slowdown。

## 其他未完成項目

仍為 `NOT_RUN`：A、B 的同條件 production RTL confirmation、multi-seed dynamic held-out confirmation、broad backpressure/load matrix、D32 production RTL、multi-seed general confirmation、H2 的 intermittent-arrival matched quota × ordering RTL controls、H5 的 calibrated CXL／application measurements，以及 APR/physical signoff。2026-10-30 dynamic probe 只完成單一 seed 的角色切換、四窗與最小 ready-stall 對照；不能把它外推成多 seed 重現、完整回壓矩陣或 application slowdown。後續執行先確認 runner 支援範圍，不能以不存在的參數推定能完成這些對照。
