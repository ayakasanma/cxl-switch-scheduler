# 配額、時間尺度與排隊：2026-10-29 更新

本檔提供最新報告的機制解釋與後續研究入口。數值來自已完成的實驗；本次修稿沒有啟動新的 RTL 或 EDA 工作。原始 10 月 28 日計畫及 hash 保持不變，最新狀態由本目錄的 release 與 hypothesis-status.json 提供。

## 1. 從共享路徑到服務分配

CXL pooling 讓多個主機使用共享容量，也讓它們的請求在交換器出口、下游連線或記憶體裝置競爭。這份報告選定單出口 descriptor switch：每個成功 fire 完成一筆等成本服務。研究問題是誰先取得服務，以及實現這個決策所需的完整硬體成本。

FAI 使用最近收到的服務量形成分類。服務少可能來自需求少、尚未 admission，或先前排程造成的等待，因此分類計數不是純粹的需求估計。Main 的 Buffer 保留原 effective class，要求下一個 window 的支持性證據才完成切換；KEEP 或無服務會取消待決轉移。這是可由狀態規則確定的行為。它是否改善某種負載的 tail，需另看該負載的觀察結果。

## 2. 已確立的條件式分配關係

在分類固定、每個來源持續有工作、無額外空轉的條件下，Main 的 High/Low quota 決定兩類各自取得的服務機會；類內的來源再分享類別額度。10/10 配額與一個 Low、三個 High 來源對應約 1/2、1/6、1/6、1/6。

CGOF 把配額放在來源上。在相同持續 backlog 條件下，來源 i 的長期份額為 w_i / sum(w)。固定 Low/High/High/High、High:Low=2:1 對應 1/7、2/7、2/7、2/7。這是具明確假設的算術關係；一般 burst arrival 的等待上限需要額外推導。

新 finite-Heavy RTL 的全部 80 個 mixed/isolated jobs 都在 cycle 4,999,999 記錄唯一一次分類邊界，由 H/H/H/H 變為 B_H/H/H/H；所有來源仍為 effective High。1:1 與 2:1 的來源相對權重相同，但每輪初始 credit 分別是一與二。相對份額相同不代表 eligible 集合、refill 時刻及逐筆服務順序相同。這個區別解釋了為何應同時觀察長期份額與短期服務間隔。

## 3. 新增的 finite-Heavy 確認證據

來源：`artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/aggregate.json`，SHA-256 `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d`。

設定：N4/D16，W5,000,000，5,000,000 筆 Heavy 工作，near profile；20 seeds 529–548，各含兩個 quota × mixed/isolated，共 80 次 RTL 執行、40 個完成時間配對。這些 seeds 保留於五個探索 seeds 509–513 之外；它們與舊 A/B 實驗使用相同編號，不能加總成原 A/B 結論的另一批獨立 seeds。

| 指標：跨 seed 的平均 | CGOF (1:1) | CGOF (2:1) |
| --- | ---: | ---: |
| Sparse 每 run P99，cycles | 3.00 [3.00, 3.00] | 4.00 [4.00, 4.00] |
| Heavy 每 run 最大 wall gap，cycles | 9.45 [9.15, 9.75] | 10.85 [10.45, 11.35] |
| Heavy gap P99，cycles | 3.00 [3.00, 3.00] | 3.00 [3.00, 3.00] |
| Heavy mixed/isolated 完成時間比 | 1.000000488 [1.000000224, 1.000000808] | 1.000000480 [1.000000224, 1.000000800] |
| Heavy mixed − isolated 完成時間，cycles | 3.05 [1.45, 5.05] | 3.00 [1.40, 5.00] |

方括號為 10,000 次 bootstrap 的 95% 區間，統計單位為 seed。2:1 減 1:1 的配對 Sparse P99 差為 +1 [1, 1]，Heavy 最大 gap 差為 +1.40 [1.10, 1.75]，完成時間比差為 −8.00e−9 [−2.40e−8, 0]。最大 gap 的表列值是「每 run 最大值的平均」，不是所有 runs 的最大值。

Sparse 延遲以 active 期間生成的 cohort 計算，包含在 drain 才完成的請求；fairness 則取 active 期間的 generated/fired counts。只有三個 mixed jobs 在 active 截止時尚有一筆 Sparse 未完成，因此 demand-share error 接近零很大程度反映接近完成的工作守恆，不能單獨代表短時間內的公平分配。

這組結果呈現較粗 credit rounds 的時間分配差異：2:1 的 Sparse P99 與 Heavy 最大間隔皆較大，Heavy gap P99 則相同。它沒有顯示 2:1 在這個 near profile 的優勢。較早 model overload 中 Main 到 CGOF 的 Sparse 改善與 Heavy gap 代價，是另一組負載與另一個比較。

near profile 的生成機率為 Heavy 0.8、每個 Sparse 0.02，sink-ready 機率為 0.9。總生成率 0.86 低於平均服務機會 0.9，提供理解完成時間差僅數 cycles 的背景。要把「剩餘容量吸收 Sparse 工作」提升為已驗證因果解釋，仍需改變負載與 arrival 相位的對照；目前完成時間比不構成應用 slowdown 或統計等價的證明。

## 4. 相同名目 readiness，等待分布仍有差異

來源：`artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json`，SHA-256 `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097`。CGOF (2:1) 的現行來源執行共 30 runs、60 A/B endpoints。

| Sink readiness | Seeds | A：獨立 Sparse P99 | B：burst Sparse P99 |
| --- | --- | ---: | ---: |
| Always | 529–548，20 個確認 seeds | 1.10 | 12.35 |
| Bernoulli 0.75 | 509–513，5 個探索 seeds | 5.00 | 20.40 |
| Periodic 48/64 | 509–513，5 個探索 seeds | 17.00 | 27.00 |

兩種名目 75% readiness 的時間分布不同：連續不 ready 的區段會改變可用服務機會之間的距離。有限 trace 的實際 ready 比例也有小幅差異，這組比較尚未完全隔離時間形狀與實際容量。因此平均容量、尾延遲與 wall gap 要共同呈現。Always 與另外兩列的 seed 集合不同；圖形分開標示確認與探索，不將它們畫成同一批 paired samples 的曲線。Always 結果重現原有 CGOF A/B 數值，而不是新一輪所有政策的比較。

## 5. 後續 agent 的納入規則

- H1：Buffer 暫態過濾規則已定義；Main 保留原有效類別（Prior-Hold），而 `FAI-ImmBuf`（原論文 Algorithm 2 立即目標優先級重構，於實驗產物中標記為 `Algorithm-2`）在進入 Buffer 時立即採用目標類別。延遲／穩定性效果仍需 controlled role-switch 與 window-phase 實驗。
- H2：固定分類的配額算術已有證據；間歇到達下 ordering、active-set 與 refill 的獨立作用仍需控制。
- H3：本次新增多 seed、單分類邊界的 finite-Heavy RTL 結果，可直接納入主文。跨至少三個邊界、under/near/over、角色交換與該 finite-work harness 的背壓敏感度仍待執行。
- H4：FIFO 深度與 admission 前後等待的逐筆分解沒有新增結果。
- H5：CXL response、completed bytes 與 application slowdown 沒有新增結果。

後續實驗沿用 [原假說協定](../improvement-20261028/HYPOTHESES_AND_EXPERIMENTS.md) 的必要輸出、可推翻預測與納入條件。最新機器狀態以 [hypothesis-status.json](hypothesis-status.json) 為準；本檔不啟動實驗。
