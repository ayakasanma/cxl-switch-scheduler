# 後續假說與實驗：提供修稿 agent 的證據工作清單

日期：2026-10-28，Asia/Taipei。狀態：PLANNED；本次未執行下列新實驗。

本檔列出可合理提出、但仍需要額外驗證的機制解釋。**預期結果是可被推翻的預測，不是實測數值。** 既有結果與新增實驗的界線見 [改進計畫 E1–E5](IMPROVEMENT_PLAN.md)。機器入口為 [agent-handoff.json](agent-handoff.json)。主報告可以先完成，不必等所有假說。

## 共用執行與納入規則

- 先讀 AGENTS.md、凍結規格、實驗 runner 與既有 manifest，保留 Main 與 Algorithm-2 的定義。優先沿用現有 model、trace 與 runner；W256 用於 plumbing，主要結論用 W5,000,000。
- 新實驗使用獨立輸出目錄，保存 source/config/traffic hashes、命令、run ID、seed、退出狀態、原始 metrics、檢查結果及失敗原因。不可覆寫 529–548 或 6201–6220 的既有資料。
- 建議新探索 seeds 7101–7105，確認 seeds 7201–7220；執行前搜尋 manifests 確認尚未用於同一假說的調參，若已用過則選新範圍並記錄。同一組比較用配對生成序列與 sink-ready 序列。20 seeds 是與既有工作一致的起始規模，不是 power analysis 保證。
- 先凍結 primary contrasts、工作量、統計方法與工程上有意義的最小差異，再跑 confirmation。探索資料可決定追加範圍，確認結果不得回頭用來挑選最好的參數。現階段不預設正向效應大小。
- 保留 generated/accepted/fired conservation、未完成/censored requests、完整 drain、各階段時間、window 邊界與 held-grant context。統計單位是 seed/run；相同確定性序列重複執行不會增加獨立證據。
- 服務份額需同時有 measurement-phase、固定長度 subwindow 與全 run 的定義。若完成後所有輸入都已服務，全 run demand-share 接近零可由守恆導出，需用時間上的分配確認機制。
- 支持方向的 CI、效應大小與所有條件一併報告。若要主張「相同」或「無實質差異」，先定 equivalence margin，再做相應比較；CI 包含零本身不證明等價。負向與無法區分的結果同樣納入。
- `report_integration_ready` 僅在來源、結果與對應 claim 經檢查後設為 true。結果方向記為 SUPPORTED、REFUTED、MIXED 或 INCONCLUSIVE；實驗跑完不代表假說成立。

## H1：Buffer 的抗短暫變化能力，是否轉化成可觀察的延遲/穩定性取捨？

**狀態／優先序**：PARTIAL_EVIDENCE，P1。報告位置 §2、§5.3。

已知：Main 狀態轉移要求兩次連續同方向證據才改變 effective class。這個規則已確定；現有 20-seed A/B 結果並未單獨證明 Buffer 改善所有情境。Algorithm-2 與 one-window control 在預設 quota 的有效行為有重疊，不能當作兩份獨立支持。

待驗證預測：對只出現一個 window 的分類擾動，Main 的 effective-class changes 少於立即更新控制；當角色持續反轉，Main 會多等待一次支持性 window，因而可能延後 Sparse 的延遲恢復。

**最小實驗**：先以相同 closing-window B/S 序列重播 Main 與 one-window transition，將分類規則與排程造成的回饋分開。再用相同 arrival/sink trace 跑完整 closed-loop Main、one-window control、Algorithm-2；配置相同 10/10 quota、N4/D16/W5M。包含一-window burst、持續至少三-window 的 Heavy/Sparse 角色交換，以及 burst 對 window 邊界的不同相位。使用至少六個 windows，保留 warmup、擾動與恢復。

**必要輸出**：每個 window 的 B/S、UP/DOWN/KEEP、encoded/effective class；effective flips；從角色變動到 effective-class change 的 cycles/windows；按 generation cohort 計算的 G-to-F P99、Heavy gap，至少保留 transition 前後分段。

**支持條件**：replay 證實單次擾動被濾除，closed-loop 在指定脈衝情境減少有效類別切換；持續角色反轉顯示相應反應延遲。只有 tail 也改善的情境才寫「改善延遲」。

**推翻／修正條件**：類別切換少但 tail 更差，則寫穩定與適應速度的取捨；若 workload 未產生預定 UP/DOWN，視為 manipulation 未成立，不能以零差異判斷 Buffer 無效。

**支援狀態**：已有 Main/Algorithm-2/one-window 機制與 adaptation 測試；需先查現有 manifest 是否包含上述相位控制，再決定是否增補 trace/instrumentation。不得把 shortened-window 結果直接換算成 production 性能。

## H2：Sparse tail 的變化主要來自配額單位，還是 eligible requests 的排序？

**狀態／優先序**：PARTIAL_EVIDENCE，P1。報告位置 §5.2。

已知：固定分類、持續 backlog 下，class quota 與 source credit 的份額不同；continuous-backlog 的既有 oldest-first/eligible-RR endpoint 差異為零。這支持做機制拆解，但無法概括所有 burst/間歇到達情境。

待驗證預測：穩定飽和時，配額決定長期分配；間歇來源重新活躍及 burst 聚集時，選擇順序可能額外改變短期 tail，即使服務份額接近。

**最小實驗**：先沿用 run_diagnosis.py 的 quota x ordering 控制：CGOF 1:1/2:1 各配 oldest-first/eligible-RR，加入 Main 與 WRR/IWRR。固定 class map 與 live classifier 分兩組。N4/D16/W5M，equal continuous backlog 與 under/near/over 的 sparse/burst traces；同一 source 權重向量、相同 refill/active-set 規則的兩個排序變體成對比較。WRR/IWRR 另外列出權重與 arrival eligibility 定義，避免把近似份額當成完全相同控制。

**必要輸出**：固定時間窗 service shares、target-normalized error、Sparse mean run-P99、Heavy gap P99/max、每次 eligible set 與 refill/grant 決策。先以 source/slot trace 對照確定干預只改了宣告的因素。

**支持條件**：quota 干預改變份額；在份額相近的排序對照中，tail 有可重現差異。若排序對照沒有工程上有意義的差異，採用「此負載主要由配額/active-set 行為解釋」的較窄結論。

**推翻／修正條件**：排序差異由不同 refill、class map 或 admission 邊界造成，先修控制再推論；若 WRR/IWRR 同樣達到目標，將結論定位為可用簡單加權仲裁取得的行為。

**可加入的條件式算術**：固定 class、所有來源持續 backlog、固定 quota、無額外 bubbles 時，Main 每個 class 的服務比例由其 quota 比決定；CGOF 每來源份額由 weight/sum(weights) 決定。這些是該簡化條件下的分配關係。一般 worst-case latency/starvation theorem 仍需另行形式推導，不由有限測試推出。

**支援狀態**：模型主要 controls 已存在，優先重用並補齊缺少情境；選出最有辨識力的情境再做 RTL。production RTL diagnosis runner 目前只接受 CGOF 兩種權重；Main/WRR/IWRR 或排序變體不能靠未存在的 CLI 旗標執行。

## H3：Sparse 收益與 Heavy 服務間隔代價，能否跨 seed、跨分類邊界維持？

**狀態／優先序**：PARTIAL_EVIDENCE，P1，最直接的新增 RTL 證據。報告位置 §5.3。

已知：模型 overload 的 CGOF 2:1 將 Sparse P99 從 28.30 降到 4.85，最大 Heavy gap 從 7.00 升到 9.55；單 seed RTL finite-Heavy 看到不同的 gap 與 Sparse P99，但兩 quota completion ratio 相同。

待驗證預測：在原設定附近，Sparse tail 與短期 Heavy gap 形成取捨，而 Heavy 總完成時間的差異小於 tail 的相對變化。其成立區域由 load、arrival burst 與分類過渡決定。

**最小實驗**：先複製既有 RTL common-demand/finite-Heavy 的兩 quota 設定到五個探索 seed；確認配置後用二十個新 seed。common-demand 至少三個 W5M windows。finite-Heavy 使用 under/near/over、mixed/isolated 成對；先在探索確認 Heavy work 足以跨越至少三個完整分類邊界，再凍結 work 與 active-cycle budget。記錄的末次 fire 必須證實跨越邊界，不能只憑 --windows 數值判定。

**必要輸出**：每個 seed 的 Sparse P99、Heavy gap P99/max、Heavy completion ratio、throughput ratio、全部 boundary class maps；測量期、drain 與外部 producer backlog 分開。各 gap 同時報 wall cycles 與 ready opportunities，避免把 sink stall 歸因於 scheduler。

**支持條件**：配對 seed 重現 tail/gap 的方向與負載條件；任何「completion 差異小」需對照事先定義的工程容忍範圍。若要直接比較 Main/WRR/IWRR，需先擴充且驗證同邊界 RTL harness。

**推翻／修正條件**：部分負載或角色交換下收益消失，按情境呈現；若 Heavy gap 的增加並非政策造成，改用 ready-opportunity gap 與 held-context trace 排除混淆。

**第二階段敏感度**：先選一個最有辨識力的負載，單因素擴展 N8/N16、D8/D32、periodic/隨機 backpressure、role switch。原 runner 硬編碼項目需先檢查；新增參數先驗證共同時序，不能改寫既有資料。硬體已完成 N8/N16 synthesis，不等於此項 latency replication 完成。

## H4：FIFO 深度造成的 tail 差異，有多少來自 admission 之前的等待？

**狀態／優先序**：HYPOTHESIS，P2。報告位置 §4 metric 說明、§5.1 sensitivity。

已知：D sweep 圖顯示各政策反應不同；等需求 RTL 的 G-to-F P99 為 1,086 cycles，external backlog 在該情境佔重要部分。據此尚無法說所有 depth 效應都由觀察邊界造成。

待驗證預測：相同 offered trace 下，改變 D 可將等待移到 FIFO 內外，從 acceptance 才起算的指標可能呈現與 generation 起算不同的趨勢。

**最小實驗**：N4、D8/16/32、W5M，相同 policy/traffic/sink-ready/producer capacity；先追蹤相同 request IDs 的 g/a/f，確認工作生成不依賴 DUT acceptance。若現有 producer 有 bounded backlog，明確保存其容量、阻塞規則與 offered/generated 的區別。只在一個獨立對照中變更 producer capacity。

**必要輸出**：逐筆 L_GA、L_AF、L_GF、三者分布、joint relationship、FIFO occupancy、external backlog、completion counts/censoring；不可把 marginal P99 相加當總 P99。

**支持條件**：逐筆分解揭示等待在 admission 前後的移動，且 G-to-F 與 A-to-F 的 policy/depth 比較出現有方向的差別。

**推翻／修正條件**：在共同 offered traffic 下仍有相同幅度的 G-to-F 改善，表示不只是等待位置移動；保留實際改善並分析 grant/occupancy 改變。若 offered traffic 被 DUT 改變，先修比較契約。

**支援狀態**：既有 traces 與 latency decomposition 可先分析；只有缺少必要欄位才新增 instrumentation/跑實驗。此項優先於擴大無差別 benchmark matrix。

## H5：scheduler tail 的改善，是否傳遞到 CXL response 與應用進度？

**狀態／優先序**：UNTESTED，P3，可作後續工作，非本次報告完成條件。報告位置 §5.5。

待驗證預測：當共同 switch egress 排隊佔請求回應延遲的重要部分，縮短 sparse scheduler tail 可能縮短 response tail；若瓶頸主要在 DRAM、link/credit 或其他元件，效果可能降低。

**必要前提**：取得可校準的 CXL platform 或 system simulator，先以測量/驗證過的 link、switch、memory service 與 backpressure 參數建立 baseline。明確區分 CXL.mem/coherence、請求/回應路徑、讀寫資料成本及 outstanding requests。

**最小實驗**：沿用 Main、RR10、CGOF 的等價服務定義，選 memory-intensive 與 latency-sensitive workload 混合，使用 isolated/mixed 成對執行；對瓶頸位置做至少一組干預。量 completed bytes/s、issue-to-response P99、application slowdown/max slowdown，以及 scheduler waiting 在 response latency 中的比例。

**支持條件**：確認 scheduler 的等待改善與 response/application 指標有對應，並能指出適用的 bottleneck 區域。

**推翻／修正條件**：response/application 差異小或轉差，保留 scheduler 層結果，將系統因素寫成實測解釋。不得用 fire/cycle 或 fixed-delay TB response 代填應用結果。

**支援狀態**：現有單輸出 descriptor 平台不足以直接執行；先建校準計畫與資源估計，後續取得相應執行範圍再進行。此檔不會自動啟動平台部署。

## 可重用入口與範例命令

下列命令是既有 CLI 所支援的起點，**本次未執行**。Windows 的模型 runner 可用專案現有 Python；RTL runner 在 Ubuntu WSL 專案環境執行。

```powershell
python -B scripts/run_diagnosis.py --verify-manifest artifacts/implementation/diagnosis-20261027/finite-heavy-confirmation-20261028T014300Z/manifest.json
```

```bash
source scripts/wsl_env.sh
python -B scripts/run_rtl_diagnosis.py --production-reviewed --window 5000000 --windows 3 --mode common-demand --policy both --seed 7101 --jobs 1 --make-jobs 1
python -B scripts/run_rtl_diagnosis.py --production-reviewed --window 5000000 --windows 3 --mode finite-heavy --policy both --seed 7101 --profile near --heavy-work 15000000 --jobs 1 --make-jobs 1
```

第二條 RTL 命令的 heavy-work 是供探索的起始值，需由 boundary trace 判定是否符合 H3，不能把它視為已驗證的三-window 設定。`--seed` 是單一值；多 seed 需逐一提交與彙整。現有 runner 不提供通用 N/D 或所有 baseline 的參數；這些擴展應沿用專案 RTL/驗證工作流程。

## 實驗後交接格式

對每個 hypothesis ID 保存：run IDs、source/config/trace hashes、實際矩陣與 seed、primary contrast、metric definition、estimated effect/CI、conservation/censoring/coverage checks、反例、outcome、可納入章節及具體 claim。同步 agent-handoff.json 的狀態與結果路徑。`report_integration_ready=true` 表示可將已核對的結果按實際方向寫入，不表示支持原假說。
