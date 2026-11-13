# 在其他裝置繼續 CXL 工作

2026-11-14 同步以 `cxl-scheduler` 的 `experiment/main-sq`、來源基線 `0b83fe1` 及當時未提交的最新文件為準，沿用 GitHub `main` 的既有發布歷史。11 月 11 日 v5 文字潤稿、PDF、驗證紀錄，以及最新 RTL、模型、實驗腳本、研究與驗收文件一起同步。這次沒有修改排程器功能或新增實驗結果。

## 下載與更新

新裝置執行：

~~~sh
git clone --branch main https://github.com/ayakasanma/cxl-switch-scheduler.git
cd cxl-switch-scheduler
~~~

已從這個 GitHub 倉庫 clone、且目前在 `main` 的裝置，先提交或 stash 自己的修改，再執行：

~~~sh
git pull --ff-only origin main
~~~

原始本機 `cxl-scheduler` 有獨立的研究提交歷史，`gh-export` 也保留原本的修改。不要直接將這兩個工作目錄當成乾淨的 GitHub `main` 執行上述 pull。新裝置請從 GitHub clone；後續裝置工作以同一個 `main` 為共同基線。

## 報告與研究資料

- [最新 v5 PDF，15 頁](../../output/pdf/cxl-scheduler-humanized-20261111.pdf)、[LaTeX 與驗收入口](../final-report/README.md)。
- [11 月 2 日歷史發布紀錄](../final-report/publication-20261102.json)維持原本的 PDF 與主文；本機主文的另一份版本另存於 [source-snapshots/hotnets-body-v3.tex](source-snapshots/hotnets-body-v3.tex)。
- [另一工作樹尚未合併的 v3 修改](quirky-hodgkin-v3-unmerged.patch)獨立保存，沒有套用到 v5。
- [同步清單、每檔雜湊與未納入內容](sync-20261114.json)。

隨附的 [report-inputs.tar.gz](../evidence/sync-20261114/report-inputs.tar.gz) 包含 746 個報告固定輸入、二十種子動態確認資料、容量實驗摘要／manifest，以及文字編輯驗證記錄。需要這些資料時，從 repo 根目錄解開：

~~~sh
tar -xzf docs/evidence/sync-20261114/report-inputs.tar.gz
~~~

解開後會還原至原本 `artifacts/` 和 `.setup-logs/` 相對路徑；這些目錄依既有慣例仍受 Git 忽略。解壓縮會寫入封包列出的路徑，請在新 clone 使用，或先備份自己相同位置的資料。

公開副本遮蔽本機帳號路徑、機器／站點識別及主機指紋。同步清單分別記錄原檔與實際 Git 內容的 SHA-256，並標明 Git 依既有規則轉換為 LF 換行的文字檔。歷史驗收紀錄與 generator 內的原始雜湊沒有改寫；封包中 22 個經遮蔽的資料檔會與原始固定雜湊不同。這份封包可用於繼續分析，但不代表所有歷史證據鏈已完整重建。編譯最新報告直接使用 repo 內已保存的 TeX 表格與圖檔，無須重跑資料產生器。

仍留在原裝置的必要原始資料包括容量實驗 30 個逐週期 JSON（合計 13.32 GiB，逐檔路徑與大小見同步清單），以及其餘未封裝的原始模擬／功耗／EDA captures。部分 trace 超過 GitHub 單檔 100 MiB 限制；沒有刪除、改寫或把它們誤稱為已同步。若工作需要逐週期重播或完整歷史原始證據，仍須另外搬移這些本機資料。機器設定、登入資料、工具／建置暫存及下載的第三方論文全文也保留在原裝置；文獻索引、書目和擷取腳本已納入。

WSL 與商業 EDA 環境須依 [環境紀錄](../ENVIRONMENT.md) 和 [WSL 設定](../WSL_SETUP.md) 在新裝置配置；Git 不會同步安裝工具、帳號或大學 cell library。
