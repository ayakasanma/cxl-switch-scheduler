# CXL 排程研究的 Related Work 搜尋與匯入（2026-11-08）

本次用 Paper Search MCP 做定向搜尋：CXL memory pooling、tiering、interference、fairness、scheduler，再沿著 FAI、Pond、BLISS 等核心工作擴展。這是可重現的定向文獻集，不宣稱涵蓋所有研究。

- 候選去重後：**57** 筆；匯入程序建立 **54** 筆新 parent；主集合目前 **87** 筆。
- 已取得並驗證全文：**57** 筆；待取得：**0** 筆。
- 驗證方式：PDF magic、可讀頁數、前 3 頁題名 token coverage、SHA256。
- 本輪開始前的 44 篇 PDF：**44/44** SHA256 保持一致。

## 最值得先讀的幾篇

- **Building A CSFQ-Inspired Transport for Switched CXL Memory Pooling**：在切換式 CXL 池上控制競爭流的頻寬與干擾；最值得與本研究的本地輸出仲裁對照。（已取得全文）
- **Equilibria: Fair Multi-Tenant CXL Memory Tiering At Scale**：多租戶公平與干擾隔離的系統層對照；公平對象是記憶體分層而非逐次輸出仲裁。（已取得全文）
- **Space-Control: Process-Level Isolation for Sharing CXL-based Disaggregated Memory**：CXL 跨主機程序隔離；補充後續整合須考慮的安全邊界。（已取得全文）
- **Interleaved Weighted Round-Robin: A Network Calculus Analysis**：直接支援 IWRR 對照：長期權重相同時，交錯順序仍會改變短期服務與延遲。（已取得全文）
- **MISE: Providing performance predictability and improving fairness in shared main memory systems**：以服務速率估計記憶體競爭造成的 slowdown，補充 shared／isolated 完成時間對照的研究脈絡。（已取得全文）

## 與目前 CXL 報告的關係

- **MemChannel** 處理跨主機、交換器與記憶體池之間的傳輸與 admission；你的工作處理單一輸出端的角色分類、服務順序與配額仲裁。兩者是不同層次。
- **Equilibria、Space-Control、MISE、MemGuard** 提供多租戶隔離、可預測性與資源保留的比較背景。
- **DRR、IWRR、WF²Q、PAR-BS、Staged Memory Scheduling** 是服務順序、公平分配、burst/backlog 與硬體排程比較的基礎。
- **Systematic CXL Memory Characterization** 與 **Dissecting CXL Memory Performance** 保留為兩筆；它們有重疊評估脈絡，但標題、作者集合與版本不同，分開引用。
- 兩個 **CXLMemSim** 也分開保留：一個是 arXiv 軟體模擬器版本，另一個是 CXL 3.0 後續出版短文。

## 檔案與 Zotero

- 全文：docs/final-report/lit-review/related-work-20261108/fulltexts/
- CSV 索引：related-work-index.csv
- 待下載清單：manual-download-list.md
- Zotero 子集合：Related Work — 2026-11-08（父集合 CXL Scheduler Literature）
- Paper Search 證據與下載回執：D:/ResearchTools/logs/cxl-related-work-20261108/
- BibTeX：related-work.bib
- 手機可搜索索引：related-work-index.html

## IEEE Chrome 補下載驗收

2026-11-08 透過 agent-desktop 操作已登入 Chrome，新增 **11** 篇 IEEE Xplore 全文。新增檔案均核對出版頁題名、PDF 題名、頁數及 SHA256，Zotero 的全文附件與待取回標籤均已讀回核實。原有 **33/33** 篇全文校驗值保持一致。逐篇結果見 [IEEE下載與驗證紀錄](IEEE下載與驗證紀錄.md)。

## 其餘 13 篇 Computer Use 補齊

2026-11-08 透過 agent-desktop 操作 Chrome，再取得 13 篇完整內容：10 篇 ACM、1 篇 Elsevier、1 篇 Wiley 原始 PDF，另 1 篇出版網頁列印 PDF。全數已放進 fulltexts 並讀回驗證 Zotero 附件。

**Is CXL the Way Forward for Server Memory?** 的出版頁提供完整俄文文章，本地保存為 Chrome 列印 PDF；以原文題名、作者、DOI、文章結尾及參考文獻核對，Zotero 附件亦已標明版本。其餘 12 篇的前三頁題名 token coverage 均為 100%。

檔案索引共 57 篇全文，其中 56 篇為既有或本次取得的論文 PDF，1 篇為出版網頁列印版。逐篇結果見 [剩餘論文下載與驗證紀錄](剩餘論文下載與驗證紀錄.md)，完整校驗清單見 [SHA256SUMS](SHA256SUMS.txt)。
