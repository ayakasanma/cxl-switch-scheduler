# V3 修訂與交付 QA

使用者於 2026-10-27 明確批准修訂 `main-v3.tex` 及其 body、資料呈現、
PDF QA 與三角色獨立複審。本次不更動歷史 `main.tex` 流程，不重跑已完成的
498 項實驗，也不以歷史 QA 代替新版檢查。

## 來源與資料

- 入口：`main-v3.tex`；正文：`sections/hotnets-body-v3.tex`。
- `generated/results.tex` 保留歷史數據；新增
  `generated/revision_v3_results.tex` 與 `revision_v3_evidence_manifest.json`
  由 `generate_revision_v3.py` 產生。
- 數值來自 accepted evidence，保留確認／探索 seeds、baseline 改編、
  負面結果、DAC 不同 entitlement、scope 與 warnings。
- core39、DAC53、power33 的凍結來源均與原執行雜湊一致。
  舊 539-file guard 中的預期差異僅為使用者批准的 v3 正文／driver／README／QA。
- 舊 manuscript、round1 PDF、初判與失敗 build 均保留，不追寫舊 receipts。

## 已觀察到的 build 修復

1. PowerShell 將未整體加引號的 output-directory option 拆開；改以 Python
   subprocess argv 執行。README 同時提供完整 option 加引號的 PowerShell 指令。
2. `\newcommand` 不接受含數字的 control-word 名稱；
   `\RevisionP99A/B` 改為 `\RevisionPninetyNineA/B`，generator 與測試同步修復，
   確認數值不變。修復後三項 generator 測試由 parent 獨立重跑全通過，
   writer 另完成實際 LaTeX table fixture。
3. accounting equation 改為三列 aligned，解除 21.36 pt 欄寬溢出；
   正文遺漏空格局部修復，不改數據。

首次成功的凍結 round1 PDF 為九頁，SHA256
`5ca3f9f4e483830dadbc32495e902892432e6968e44c6de37398d0ab6f775092`。
兩次編譯均 exit0，零 overfull／未解析引用；29 個 underfull hbox 保留。
Parent 曾逐一檢視全部九頁及 contact sheet，未發現裁切、重疊或破損表格。
此雜湊不是後續 reviewer 修復版的最終雜湊。

## 工具、審查與限制

實際排版工具為 pdfTeX 3.141592653-2.6-1.40.28（MiKTeX 25.12）、
LaTeX2e 2025-11-01；render 使用 PyMuPDF 1.27.1。
MiKTeX 額外提示尚未檢查更新；沒有為此更新系統套件。
Underfull 是保留的行距診斷，不等於零排版 warning；視覺 QA 另行判定。

複審的初判、嚴重度、精確位置、修正及是否需要新實驗詳見
`../experiments/revision-20261023/PAPER_REREVIEW.md`。
三角色是本機 advisory、未校準，沒有外部編輯／同行接受或模型錯誤獨立性保證。
最終 scoped review 僅驗證各角色指出的修正，不宣稱重作整個 raw-data audit。

功耗為 TT／25 ns、zero-delay／no-SDF、ideal-clock 的 pre-layout 估計；
保留 FCFS／RR 的 static-pin range warnings、constant leaf gaps 與 disabled checks。
沒有 DAC power、APR、multicorner、實機 CXL 或 application-level fairness 驗證。
Ignored `.setup-logs/` 與 `artifacts/` 是重現所需依賴；
只有 tracked files 的 clone 不足以還原完整研究。

最終 build／render／review hash 與交付包定位記錄於本檔後續的「最終驗收」。

## 最終驗收：2026-10-27

交付 PDF：`output/pdf/cxl-scheduler-v3-revised-20261027.pdf`，**九頁**。
最終 SHA256：
`892abcf3102c17bb75a5825ded5628368cf86a1c8397a727819136cb7a776400`。
這是 reviewer 修復後的實際 PDF，不沿用 round1 雜湊。

- 修復範圍：DAC reset／mid-round credit 說明、N-expansion locator、
  N4 disjoint area table，以及六組 bridge／SQ replay／primary-nine audit／
  68-job model gate 的既有證據閉包；588 records 全部綁定。
- Generator 四項測試由 parent 獨立重跑，4 PASS、0 failure、0 skip；
  新增測試涵蓋分類面積 reconciliation 與補件雜湊拒絕變造。
- 雙次 `pdflatex` 實際 exit 均為 0；最終 log 零 overfull、
  零 undefined references/citations。29 個 underfull hbox 及 MiKTeX
  尚未檢查更新的環境提示保留，未宣稱零 warning。
- 全部九頁重新 render，parent 逐一檢視九頁與 contact sheet，
  未見裁切、重疊、未解析表格或破損引用；面積表與原有各表均可辨讀。
- 三角色 scoped round2 無未結問題；未新增實驗、SSH、EDA 或 commit。
  其 release 與子報告雜湊由 parent 實際核對。

精確 receipt 與 render 位於：
`.setup-logs/implementation/revision-20261024/manuscript-revision-20261027/`
的 `review-round2/`、`parent-round2-adoption.json`、`final-release/`。
`review-round2/input-manifest.json` 保持 reviewer 接收時的不可變狀態；
其中當時的 visual-QA-pending 由獨立 parent adoption receipt 結案，
而非回寫初始 freeze。兩次 build argv 沿用 `build/command.json`；
實際 stdout、final log、抽取文字與 PNG 均保留。

資料補件 release SHA256：
`bd8f5f020b1ccc4ee60f228eb57e0e8b397540130c849030b1bd24b09274a828`。
最終 generated manifest SHA256：
`1fd621185ffdc5697a8ae3b5c1bf8557a9d490e81cdd374888676cb468d084ff`。
修訂 body SHA256：
`7dd7593eac5298def4245a620001894f909c3c6957b3078ed984948bb2dd93ed`。

Reviewable 交付包：`output/pdf/cxl-scheduler-v3-release-20261027.zip`。
其獨立 `archive-receipt.json` 記錄 ZIP 與 release-manifest 的雜湊，
ZIP 內含逐檔雜湊、原稿到修訂稿 diff、local TeX input inventory、
paper/data/review 文件與必要補件 locators。原始實驗 archive 與商業工具
依賴不複製進此 ZIP，也不宣稱此 ZIP 是完整 clean-room reproduction。
# 圖形版補件

2026-10-27 使用同一已驗收資料補入六張向量結果圖；最新 PDF 為
`output/pdf/cxl-scheduler-v3-graphical-20261027.pdf`（12 頁）。
此文件原有九頁 QA 屬前一版；新增版本的完整紀錄見
[GRAPHICAL_EDITION_QA.md](GRAPHICAL_EDITION_QA.md)。原交付雜湊未變。

