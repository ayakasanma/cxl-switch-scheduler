# CXL Scheduler：本階段收尾小結

日期：2026-10-17，Asia/Taipei。本階段 **M1–M5 功能整合已驗收**；下一階段由 Project owner 在 UIUC FastX 執行商用 synthesis／STA。這不是整個專案或 PPA 完成宣告。

## 已固定的設計

- Approved Spec v1.0：`1af80967bbc2fb83224f4725c4fb450889e69c62`。
- 已測試的程式快照：`cefbbb0bda8dab21c9dd962378041fc5e0c4a426`。
- 功能驗收文件提交：`3006b232bec6e7e239bf3a5e51341daff1ccf6e2`。
- 同一個 `switch_top`，N=4/8/16、每來源 FIFO D=16、單一輸出 M=1。
- Descriptor 共105 bits：Tag32、Address32、Opcode1、Length8、Payload32。
- FCFS、RR quantum10、FAI-inspired Main 共用 FIFO、輸出 hold、ready/valid 與對外時序。RR 不儲存不需要的 timestamp；FCFS/Main 保留 arrival metadata。
- Main 採 H/B_H/L/B_L、保留舊有效優先權的遲滯；production W=5,000,000，B/S/index23-bit、unsigned32-bit threshold arithmetic。單輸出10/10交替是專案重建，不是論文逐週期重現。

## 實際驗證結果

| 項目 | 結果 | 說明 |
| --- | --- | --- |
| Main M5 unit | Claude、Codex 各805 PASS | 每次196 reference pytest +39 helper pytest +570 cocotb；27 lint、9 structural probes，3 ALG2 expected rejections另計。 |
| Main stress | 30/30 PASS | N4/8/16 × W64/256 ×5 seeds；共1,800萬 trace cycles，每組均達16種 Main state/evidence transitions。 |
| Main primary | 60/60 PASS | 20 seeds ×3個 N，各100,000 measured cycles；60個 intended trace hashes均符合既有 FCFS紀錄。 |
| Main production | 3/3 PASS | 每個 N 實跑2,000萬 non-reset measured cycles／4個完整視窗，合計6,000萬週期、12個視窗。 |
| M1/M2/M3/M4/RR1回歸 | 全部 PASS | 分別286／526／550／430／195 tests；reference/helper重複收集不能當成額外獨立 RTL coverage。 |
| 三政策主要功能矩陣 | 180/180 PASS | FCFS60 + RR60 + Main60；**不是九組 PPA 結果**。 |

最終測試範圍均為零 failure/error/skip/NOT_RUN。Primary 在首次分類前全為 High，與 FCFS mirror一致；分類與遲滯的證據來自獨立 stress／production，不能把 primary結果解讀成公平性結論。

最初 stress 有7 FAIL／9 executed、21 NOT_RUN，原因是最後量測週期的 full-FIFO fire，其 next-cycle-ready 落在第一個 drain週期。Claude 修正了 TB 統計邊界，新增 directed test19；完整30組重跑通過。RTL、reference model與共同 framework未因這項修正改動，原始失敗紀錄保留。

## 分工、工具與保存位置

Claude Code／RTL Agent Team 是 RTL、模型與驗證程式的主要作者；Codex負責協調、獨立審查及實際回歸執行。此次使用的實際 inference model為 Opus5.5，explicit high effort。最後的 func-verifier 已寫出 `PASS_M5_MAIN_FUNCTIONAL`、兩份報告及 manifest後，最後摘要 API 才遇到429，CLI exit1；不能宣稱該 CLI 自然成功。當時回報的13:50重置時間只是一筆歷史估計，本次收尾沒有重新探測額度或調用 Claude。

WSL工具：Python3.12.3、Verilator5.052、cocotb2.1.0、pytest9.1.1。既有 repository／toolchain／全域登入與路由設定保留。

- [目前狀態](STATUS.md)、[進度](PROGRESS_TRACKER.md)。
- [逐項功能驗證與限制](phase-5-verification/M5-integration-results.md)。
- [Claude requirement traceability](../reviews/phase-5-verify/M5-functional-verification.md)。
- [Codex獨立驗收](../reviews/phase-4-rtl/codex-fai-main-review.md)。
- 本機 raw logs／JUnit／metrics：`artifacts/implementation/<scope>/<run-id>/`。
- 本機 session logs／diff／hash／audit：`.setup-logs/implementation/resume-20261017/`。這兩處被 Git忽略，請保留本機原件；交接壓縮包只帶受控來源與文字報告，不包含全部 raw logs。

## 尚未執行與下一步

FastX access／scheduler DC、PT、STA、power與九組 PPA均 **NOT_RUN／NOT_VERIFIED**。既有 registered-adder smoke是 owner提供的環境證據，並非 scheduler測量。Formal、CDC、數值 coverage、RTL mutation沒有完成或 PASS宣告。

Algorithm-2補充版本仍未實作；待主要九組 synthesis完成後，先做 N4對照，再視影響與時間決定 N8/16。Multi-output、APR等擴充延後。

下一步請依 [FastX手動交接手冊](FASTX_HANDOFF.md)：上傳來源包 → module/tool/library preflight → pilot → 固定共同 PPA profile → 九組 DC/PT → 回收報告。現在沒有新的重大 Spec歧義需要拍板；尚缺的是實際 library路徑、工具可用性，以及根據 pilot凍結的共同測量條件。
