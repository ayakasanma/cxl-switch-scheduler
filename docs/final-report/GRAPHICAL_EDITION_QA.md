# V3 圖形版：2026-10-27

前一版移除過時圖後，僅以新表格呈現結果，未滿足直觀閱讀需求。
本版保留精確表格與不利結果，新增六張實驗結果圖；沒有重跑或變更實驗。

交付：`output/pdf/cxl-scheduler-v3-graphical-20261027.pdf`，12 頁。
SHA256：`98ad620446224cb2eacf76abb5c7cb3761d7b21c0a6cfdd3971baf1ede3f6bcb`。
原九頁 PDF 與原 release ZIP 的雜湊維持不變。

| 圖 | 視覺化內容 | 統計與解讀邊界 |
|---|---|---|
| 1 | 七策略確認集 A/B P99 長條圖 | 20 seeds；平均 run-P99，非所有 requests 的合併 P99 |
| 2 | 六組配對差值與信賴區間 | 10,000 次 paired-seed bootstrap；pointwise 95%；保留 Main 對 RR10 的 B 退步 |
| 3 | RR quantum、High quota、FIFO depth 敏感度 | 五個探索 seeds；無 CI、未據此選確認集最佳參數 |
| 4 | 六設定 B 熱圖及 DAC 背壓 A/B 比較 | 五個探索 seeds；保留 burst-32 不利結果，DAC 僅兩種背壓 |
| 5 | N8/N16 六策略 A/B 曲線 | 五個探索 seeds；需求與 storage 隨 N 改變，沒有 DAC 外推 |
| 6 | 面積分項與 trained power | DAC 僅完整總面積；power 三 seeds、沒有 DAC power，TT/pre-layout 限制保留 |

圖檔由 `generate_revision_figures.py` 產生，同時輸出向量 PDF、可編輯 SVG、
預覽 PNG、`plot-data.json` 與 `figure-manifest.json`，置於 `generated/figures/`。
資料先經既有 `generate_revision_v3.render()` 的 hash/cohort/transitive 檢查；
沒有從文字摘要手抄數值，也沒有替個別策略長條圖杜撰信賴區間。

重現順序：

```powershell
python -B docs/final-report/generate_revision_figures.py
python -B -m unittest discover -s docs/final-report -p "test*revision*.py"
```

編譯使用原 README 的 MiKTeX 指令，jobname 改為
`cxl-scheduler-v3-graphical-20261027`。執行環境 Matplotlib 3.10.0；
沒有新增套件依賴。原始 evidence archives 仍須存在，封存包並非完整實驗環境。

實際驗證：原資料產生器四項與圖表兩項測試共六項通過；兩次 pdflatex
exit 0，零 Overfull、零未解析引用。Parent 檢視 12 頁 contact sheet、
逐頁檢視六個含圖 PDF 頁（5–10）及各圖 PNG，未見裁切或重疊。
Underfull 排版提示不等於實驗或資料失敗，原始 log 保留。
Core39、DAC53、power33 的來源雜湊全數未變。

Sol/high 唯讀獨立圖表複核發現兩個 P3：confirmation 標籤相接、
N 圖例遮住端點；兩者已修復並以新圖複核結案。所有六個配對 CI
與 34 個 sensitivity 點獨立核對；最終圖表範圍沒有未結問題，不需新實驗。
這是新增圖表的 scoped advisory review，不取代原三角色論文審查，
也不宣稱外部同儕審查或評估校準。

實際 argv、測試、兩次 build log、render、source guard 與獨立複核位於
`.setup-logs/implementation/revision-20261024/graphics-20261027/`。
