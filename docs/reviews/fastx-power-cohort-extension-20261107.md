# CGOF 功耗 cohort 與定向長 backlog drain — 2026-11-07

本次執行沿用既有 CGOF1/A/509，補齊其餘十一組。凍結條件為 N4、D16、full105、W=5,000,000、oldest-first、ELIGIBLE_RR=0，HIGH_WEIGHT=1/2，seeds 509–511，A/B 各自保留。既有 FCFS/RR10/Main 十八組 accepted captures 作 matched baseline，不重跑。

功耗採既有 mapped netlist、SDC、SAED32 RVT TT 0.78 V / 25 °C、25 ns、ForQA/top。A 是 10,000,000 warmup + 100,000 measured cycles；B 是 10,101,024 warmup + 102,400 measured cycles。SAIF 僅覆蓋原量測窗。

## 執行紀錄

- 工作目錄：Host 建立的 sharp-bohr worktree；原 repository 只讀。
- 續跑入口：scripts/run_cgof_power_cohort.py；本機同時最多兩個向量準備工作，FastX EDA 一次一組、一核心。
- SSH 沿用本機 FastX helper 與既有 credential lifecycle；host-key verification 保持啟用。連線資訊與完整本機命令保存在 ignored logs。
- 新批次初始 backend 為 fastx4-NN.ews.illinois.edu，帳號 chiang22，未觀察到既有本帳號 EDA 工作；home 可用約 5.7 GB。
- 每組新建 remote run directory，保留壓縮向量、source archive、netlist/SDC、執行 runner、所有 exits/logs/SAIF/PT reports。來源前後一致檢查成功後，刪除本組可重建的展開向量，避免家目錄容量不足。
- 個別 replay 最長 3,600 秒，沿用既有 compile/PT 限時；個別 runner 最長 6,400 秒。失敗保留證據並停止後續遠端 case。
- execution-index.json 記錄每組真實狀態、package/evidence hash、命令、remote/local exit 及四項功耗；命令完成仍需主模型語意驗收。

## 長 backlog drain

另新增定向 scheduler RTL 測試：Main、CGOF1、CGOF2，N4/D16/full105、W=5,000,000，engineering seed 7301。從 reset/all-High 開始，有限生成且暫停 sink，明確留下 FIFO 與 producer backlog；停止生成後恢復 ready，持續逐週期獨立模型、full105 FIFO 與 hold 檢查，直到全部工作完成。

驗收需有 cutoff backlog、超過 10 cycles 的實際 drain、逐 source conservation、generated=accepted=fired，以及最後 producer/FIFO outstanding=0。這是獨立定向測試；不變更功耗量測窗，也不改寫歷史 A3 的 0/0/0/2-cycle 紀錄。

Claude Code / rtl-agent-team:testbench-dev 為新 RTL 驗證程式的唯一實作者，請求 claude-opus-5-5、medium；stream 已回傳相同 model ID。Codex 負責批次執行、來源/報表核對與最終驗收。worker 不使用 SSH、不執行遠端 EDA，也不更動既有凍結來源。

定向長 drain 已通過獨立驗收。正式 run 為 `20261106T230245Z_18888`，三組均從 reset/all-High 起始，先以 ready=0 生成 512 cycles，再停止生成並恢復 ready。

| 項目 | CGOF1 | CGOF2 | Main |
|---|---:|---:|---:|
| cutoff producer backlog | 859 | 859 | 859 |
| cutoff FIFO occupancy | 64 | 64 | 64 |
| 實際 drain cycles | 923 | 923 | 923 |
| generated = accepted = fired | 923 | 923 | 923 |
| final outstanding | 0 | 0 | 0 |
| input-hold checks | 3706 | 3709 | 3740 |
| closed windows | 0 | 0 | 0 |

cutoff 的逐來源 producer backlog 為 `[359,229,167,104]`，FIFO 各為 16；最終逐來源 generated/accepted/fired 均為 `[375,245,183,120]`。held grant 維持 511 cycles，恢復 ready 後第一筆確實送出；逐週期 full105 scoreboard、獨立模型、hold 與 conservation 檢查持續到最後兩個 quiescent cycles。

`summary.json` 記錄 7/7 steps PASS：3 組 Verilator lint、9 個 pytest tests、3 組 cocotb 各 1 test，共 12 tests，failures/errors/skipped 均為 0，所有執行步驟 exit 0。`parent-acceptance.json` 另核對 51 份 source 的 archive/current/before/after hash、原始 JUnit、各配置的模型重播與 conservation，exit 0。執行入口為 `source scripts/wsl_env.sh && PYTHONDONTWRITEBYTECODE=1 timeout 2400 python scripts/run_directed_backlog_drain.py --execute --jobs 2`；完整 lint/build/sim 命令在該 run 的 `commands.txt`。

## 功耗續跑狀態

截至 2026-11-07 07:54（Asia/Taipei），CGOF1/A/510 已通過父審，與沿用的 CGOF1/A/509 合計兩組；其餘十組仍由既有 coordinator PID 40540 執行。CGOF1/B/509 已完成 9,000,000 warmup cycles，compile 與 compile-log-audit exit 均為 0；coordinator stderr 為空，尚未產生結束 exit。完整 18 筆既有 baseline 與 matched trace/profile/window、metadata/acceptance/exit receipt bindings 已整理到 `cohort-extension/matched-baseline-509-511-AB.json`，整理命令 exit 0，未重跑 baseline。

CGOF1/A/510 的 VCS compile、simulation、replay audit、PrimeTime、tool-log audits、source check、shell 與 local audit exits 全為 0。VCS version probe exit 1 另行保留。父審核對 39 份目前來源、source archive、54 項遠端 before/after hashes、frozen mapping、library/model/profile、SAIF 與 reports bindings，exit 0。原始 exporter metadata 的 NOT_RUN 欄位保留準備時狀態；實際驗收以該組 `parent-acceptance.json` 為準。

SAIF annotation 為 28,458/28,458 nets 與 27,750/27,784 leaf cells；34 個 leaf 例外均有 frozen mapped netlist 的 D/SETB literal pins。全部 8,998 個 FF clock pins 經 hierarchy 對應到頂層 clk，activity source 都為 file、toggle rate 0.0799996/ns。39,912 筆 SAIF records 無 transient X/Z；20 個全程 X 僅出現在未連接的 arithmetic carry/comparator outputs。唯一 PT warning 為 PTE-003，68 個 disabled arcs 對應 propagated constants：64 個 D=0 setup/hold arcs 與四個 SETB=1 arcs。`check_power` 無 load/ramp range issues。

同 seed 510、arm A 的 matched 比較如下，單位 mW。各政策沿用相同 trace hash、profile、PVT、25 ns、10,000,000 warmup 與 100,000 measured cycles。

| 政策 | internal | switching | leakage | total | CGOF1 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF1 | 1.328 | 0.01820 | 2.070 | 3.416 | — |
| FCFS | 1.306 | 0.01781 | 2.032 | 3.356 | +1.79% |
| RR10 | 0.9995 | 0.01345 | 1.547 | 2.560 | +33.44% |
| Main | 1.332 | 0.01921 | 2.116 | 3.467 | −1.47% |

CGOF1、RR10 與 Main 的 measured accepted/fired 均為 `[97654,809,772,765]`，cut/end outstanding 均為 `[15,0,0,0]`。FCFS accepted 為 `[97655,809,772,765]`、fired 為 `[97655,809,771,765]`，outstanding 從 `[15,0,0,0]` 變為 `[15,0,1,0]`；父審保留這些實際接受量與 window 邊界差異，未把 matched traffic 說成相同逐筆服務。

父審命令：`.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof1_A510.py`，exit 0；完整 remote command、stage exits、source/package/library/profile hashes、warnings、baseline receipt bindings 與四項功耗存於 [CGOF1/A/510 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-A-s510/parent-acceptance.json)。原 remote run 為 `cgof-power-cgof1-a-s510-20261106t230327z`，實際 backend `fastx4-NN.ews.illinois.edu`。本輪只讀 SSH alias preflight 另落在 `fastx4-NN.ews.illinois.edu`；該 backend 的 process 清單不被當作原工作的狀態證據。

同一 Cindy 對話已綁定每 20 分鐘的自動續接，只有新完成 case 或錯誤才啟動驗收；達成完整功耗目標後停止。排程 ID 為 `213559e5-1778-4839-b449-f9b37c1c4284`。coordinator 持續負責串行執行，續接僅審查既有結果與處理本任務的實際失敗。

## 證據位置

### 2026-11-07 08:30 續接查證與恢復

本輪另通過 CGOF1/B/509、CGOF1/B/510 父審；連同既有 A/509、A/510，目前為 **4/12**。每組實際 replay、SAIF/PrimeTime、來源前後一致性、tool-log audits、shell 與 local audit 均 exit 0，父審命令亦 exit 0。兩組 B 窗均為 10,101,024 warmup、102,400 measured cycles、2,560,000 ns。39 份 current source、54 項 remote before/after hashes、package/source archive/library/model/profile、SAIF/report bindings 均核對一致。annotation 為 28,458/28,458 nets、27,750/27,784 leaf；全部 8,998 FF clocks 為 file activity。34 個 literal-pin leaf 例外、20 個 disconnected constant-X outputs、無 transient X/Z，唯一 PTE-003 僅含 68 個 propagated constant arcs。

| 新驗收 case | internal mW | switching mW | leakage mW | total mW | 對 FCFS | 對 RR10 | 對 Main |
|---|---:|---:|---:|---:|---:|---:|---:|
| CGOF1/B/509 | 1.328 | 0.01794 | 2.069 | 3.415 | +1.79% | +33.45% | −1.44% |
| CGOF1/B/510 | 1.328 | 0.01794 | 2.070 | 3.416 | +1.79% | +33.44% | −1.44% |

對應 seed/arm 的 baseline total 分別為 509/B：FCFS 3.355、RR10 2.559、Main 3.465 mW；510/B：FCFS 3.356、RR10 2.560、Main 3.466 mW。各政策實際 admissions、fires、cut/end outstanding 仍逐筆保留於 parent receipt，未將同一 exogenous trace 說成同一服務結果。

原 coordinator PID 40540 已不存在，原 stdout 最後更新於 08:15:57；stderr 0 bytes、原 exit receipt 缺失，結束原因未證實。此時原 backend FastX-NN 的 B/510 仍在共享 run 目錄持續產生 replay 進度，不能因本機 coordinator 消失就判定遠端失敗。本輪先保全原索引及 process-loss receipt，確認沒有其他本機 coordinator/exporter，再以 exclusive lock 恢復**同一批次與索引**。原 B/510 完成後才收回既有 evidence，核對遠端 archive SHA256、完整 tar 與 exit receipt，未重新執行該 capture。其 remote exit、local audit、parent acceptance 都為 0。

恢復入口為 ignored logs 的 `resume_cohort.py`，PID 41940；原 `scripts/run_cgof_power_cohort.py` 及所有 frozen RTL/TB/exporter/checker/STA sources 保持不變。Windows WMI detached launcher 的第一次嘗試 exit 1；加入錯誤記錄後查明環境找不到 `python`，第二次亦 exit 1。改為呼叫現有絕對 Python executable 後啟動成功；未安裝或替換工具，失敗 receipts 均保留。三項 focused recovery tests 通過、exit 0：重用完備 export 並拒絕 hash drift、只收回既有 remote completion、未完成逾時不重啟 replay。實際遠端收回另提供 B/510 成功證據。

恢復後先啟動唯一的 CGOF1/A/511，run `cgof-power-cgof1-a-s511-20261107t002827z`，backend FastX-NN；compile 與 compile-log-audit exit 0，replay 執行中。其餘完備 exporter 產物沿用；中斷且尚未驗收的 CGOF2/B/510 與 CGOF2/A/511 保留原目錄，僅於各自新建 `export-recovery-...` 子目錄補缺失 export；本機仍最多兩個 exporter 工作，遠端一次一組、一核心。新 remote wrapper 用 nohup 啟動，仍受原有 stage timeout 約束，避免本機 transport 結束就喪失工作追蹤。

目前主協調與驗收由本輪 Codex CLI 執行；未新增審查代理，未變更 Claude RTL/TB 路由。active coordinator logs 改見 `cohort-remaining/recovery.stdout.txt`、`recovery.stderr.txt`、`recovery.exit.txt`（執行中缺失為正常；不替原 coordinator 偽造 exit）。`continuation.json` 與 precheck 改為辨識這組 active logs/PID；precheck 也會偵測 coordinator 消失，避免索引停住後永遠略過。原 logs、索引快照與中斷 export 均保留。排程仍只續接本任務，完整驗收後才停止；目前整體 **INCOMPLETE**，八組仍待完成及父審。長 drain 沿用原已驗收結果，未重跑。

### 2026-11-07 09:14 — CGOF1/A/511 父審通過

本輪單一 coordinator PID 41940 仍存活；未另啟 coordinator、未重跑既有 capture 或定向 drain。新增 CGOF1/A/511 父審通過，連同既有 A/509 與前述三組，目前 **5/12**。原 run `cgof-power-cgof1-a-s511-20261107t002827z` 在 FastX-NN 完成；compile、sim、replay audit、PrimeTime、tool-log audits、source check、shell、local audit 與父審 exit 均為 0。VCS version probe exit 1 依原紀錄保留。

父審確認 39 份 current source 與 archive、54 項遠端 before/after bindings、mapped netlist/SDC、library/model/profile、SAIF 與 reports hashes；另核對本機 package SHA256、原 bootstrap 的 payload 校驗成功紀錄及 evidence archive SHA256。SAIF 為 100,000 measured cycles、2,500,000 ns，annotation 28,458/28,458 nets、27,750/27,784 leaf cells，8,998 FF clocks 全為 clk/file activity。34 個 literal-pin 例外、20 個 disconnected constant-X outputs、無 transient X/Z；唯一 PTE-003 warning 仍僅含 68 個 propagated constant arcs，check_power 無 load/ramp 問題。

| 同 seed 511 / arm A 政策 | internal mW | switching mW | leakage mW | total mW | CGOF1 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF1 | 1.328 | 0.01822 | 2.070 | 3.416 | — |
| FCFS | 1.306 | 0.01782 | 2.032 | 3.356 | +1.79% |
| RR10 | 0.9995 | 0.01346 | 1.547 | 2.560 | +33.44% |
| Main | 1.332 | 0.01922 | 2.116 | 3.467 | −1.47% |

四種政策此窗的 accepted/fired 均為 `[97595,777,815,813]`，cut/end outstanding 均為 `[15,0,0,0]`。Matched trace/profile/PVT、25 ns、10M warmup、100K measured window 與原 baseline receipts 綁定一致；沒有重跑十八組 baseline。父審命令為 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof1_power_case.py cgof1-A-s511`，exit 0。完整四項功耗、stage exits、warnings、來源 hashes 與原 remote command 見 [CGOF1/A/511 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-A-s511/parent-acceptance.json)。

CGOF1/B/511 已由同一 coordinator 串行啟動，run `cgof-power-cgof1-b-s511-20261107t005455z`；09:13 的只讀共享目錄查證顯示 7,000,000 checked warmup cycles，compile 與 compile-log-audit exit 0，尚未完成 SAIF/PT/父審。該次 alias 查詢落在 FastX-NN，其 process 清單不代表原 FastX-NN 工作。中斷恢復的 CGOF2/B/510、CGOF2/A/511，以及原缺失的 CGOF2/B/511 exports 已各自 audit exit 0；這些僅是輸入準備完成，CGOF2 六組功耗仍未驗收。active stderr 0 bytes、exit receipt 尚未產生；整體仍 **INCOMPLETE，七組待完成及父審**。本輪記錄為 `cohort-remaining/followup-20261107T0112Z-review.json`，同目錄保留父審/SSH logs、exits 與本輪 SHA256SUMS；最後將與 precheck 相同的 active state 寫入 marker。

- 即時批次索引：artifacts/implementation/fastx-power-20261107/cohort-extension/execution-index.json
- 個別 capture：同目錄的 cgof1/cgof2、A/B、s509/s510/s511 目錄
- CGOF1/A/510 父審：artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-A-s510/parent-acceptance.json
- CGOF1/B/509 父審：[parent-acceptance.json](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-B-s509/parent-acceptance.json)，exit 0
- CGOF1/B/510 父審：[parent-acceptance.json](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-B-s510/parent-acceptance.json)，exit 0
- coordinator 恢復紀錄：`.setup-logs/implementation/fastx-power-20261107/cohort-remaining/followup-20261107T0017Z-review.json`；新舊 logs、失聯查證、索引快照、三項 recovery tests 與 operational source SHA256SUMS 均在同目錄
- 補充 package 核對：`recovery-package-audit.stdout.txt`、`recovery-package-audit.stderr.txt`、`recovery-package-audit.exit.txt`，確認 A/510、B/509、B/510 本機 tar SHA256 與原 remote payload 校驗，exit 0
- 既有單組驗收：artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-semantic-review.json
- 既有 cohort freeze：artifacts/implementation/fastx-power-20261107/cohort-freeze-final/cohort.json
- 長 drain 驗收：artifacts/implementation/fastx-power-20261107/directed-drain/20261106T230245Z_18888/parent-acceptance.json
- 長 drain 原始結果與命令：同一 run 的 directed_drain_scope.json、summary.json、commands.txt、junit/、logs/、results/、sources.zip
- matched baseline：artifacts/implementation/fastx-power-20261107/cohort-extension/matched-baseline-509-511-AB.json
- 本輪命令、worker prompt/stream 與 transport logs：.setup-logs/implementation/fastx-power-20261107/cohort-remaining/

### 2026-11-07 09:37 續接 — CGOF1/B/511 父審通過

CGOF1/B/511 的原 run `cgof-power-cgof1-b-s511-20261107t005455z` 已在 FastX-NN 完成，主模型自行父審通過；連同既有 A/509，目前 **6/12**，CGOF1 六組均已有個別驗收。命令為 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof1_power_case.py cgof1-B-s511`，exit 0；stdout/stderr/exit 均保存在 `cohort-remaining/accept-cgof1-B511.*.txt`。compile、sim、replay audit、PT、tool-log audits、source check、shell 與 local audit 均 exit 0；VCS version probe 的 exit 1 原樣保留。

本次核對 39 份 current/archive sources、54 項 remote before/after bindings、mapped netlist/SDC、library/model/profile、SAIF/report hashes，以及本機 package SHA256、原 bootstrap payload 校驗紀錄與 evidence archive SHA256。annotation 為 28,458/28,458 nets、27,750/27,784 leaf；8,998 FF clocks 皆為 clk/file activity。34 個 literal-pin leaf 例外及 20 個 disconnected constant-X outputs 均逐項對應 frozen topology；無 transient X/Z。唯一 PTE-003 為 68 個 propagated constant arcs，check_power 無 load/ramp range issue。

| 同 seed 511 / arm B 政策 | internal mW | switching mW | leakage mW | total mW | CGOF1 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF1 | 1.328 | 0.01793 | 2.071 | 3.417 | — |
| FCFS | 1.306 | 0.01754 | 2.034 | 3.357 | +1.7873% |
| RR10 | 0.9991 | 0.01309 | 1.549 | 2.561 | +33.4244% |
| Main | 1.331 | 0.01874 | 2.117 | 3.467 | −1.4422% |

四政策沿用相同 seed/arm、trace/profile/PVT、25 ns、10,101,024 warmup 與 102,400 measured cycles，SAIF duration 為 2,560,000 ns。四者本窗 accepted/fired 均為 `[100000,800,800,800]`，cut/end outstanding 均為 `[15,0,0,0]`。完整原命令、版本、exits、來源 hashes、warnings、四項功耗與 baseline bindings 見 [CGOF1/B/511 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof1-B-s511/parent-acceptance.json)。

唯一 coordinator PID 41940 實查仍存活，stderr 0 bytes，active exit receipt 尚未產生。原批次已串行接續 CGOF2/A/509，run `cgof-power-cgof2-a-s509-20261107t012153z`；本輪 FastX helper 只讀查證 exit 0，共享 run 已到 5,000,000 checked warmup cycles，compile/audit exit 0。alias 落在 FastX-NN，其 process 清單不代表原 FastX-NN 工作。未另開 coordinator、代理或 campaign，未重跑 accepted captures 或 directed drain，未變更 frozen sources。

本輪 `record_followup_20261107T0137Z.py` exit 0，補充核對目前五個 extension captures 的本機 package、payload 校驗與 evidence archive，更新 `continuation.json`、`followup-20261107T0137Z-review.json`、本輪 SHA256SUMS 及與 precheck 相同結構的 `last-followup-state.json`。CGOF2 六組仍待實際 gate-power 完成與父審；輸入須優先使用 index 的 `export_directory`，不能以 CGOF1 固定 topology 假定其驗收。整體仍 **INCOMPLETE**，全域 artifact-index/SHA256SUMS 的完成封存留待全十二組驗收後。長 drain 保留原十二 tests 通過結果，未重跑。

### 2026-11-07 10:00 續接 — 首組 CGOF2/A/509 父審通過

原 coordinator PID 41940 實查仍存活、stderr 0 bytes、active exit receipt 尚未產生；CGOF2/A/509 已在 FastX-NN 完成原 run `cgof-power-cgof2-a-s509-20261107t012153z`。主模型獨立核對後，父審於 10:04 通過，目前 **7/12**；其餘五組 CGOF2 仍待完成與父審。既有 CGOF1 六組、baseline 十八組及 directed long drain 均未重跑。

命令為 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-A-s509`，exit 0。compile、sim、replay audit、PrimeTime、tool-log audits、source check、shell 與 local audit exits 全為 0，VCS version probe exit 1 仍單獨保留。39 份 current/archive sources、54 項遠端 before/after bindings、CGOF2 HIGH_WEIGHT=2 mapping、library/model/profile、package、vectors 與 evidence archive hashes 均核對一致。父審輸入由 index 的 `export_directory` 解析；remote evidence 與 receipt 保留於 canonical case 目錄，沒有改動 frozen sources。

首組 CGOF2 實際 annotation 為 30,022/30,022 nets、29,221/29,255 leaf；9,014 FF clocks 全為 clk/file activity，toggle rate 0.0799996/ns。34 個 leaf annotation 例外仍為 literal D/SETB pins。42,138 筆 SAIF records 無 transient X/Z；56 筆恆定 X 經本組 frozen netlist 逐項核對，分別為 24 個未連接的 carry/comparator outputs、16 個已裁剪且未使用的 arithmetic output bits，以及其 16 個無 consumer 的連接線。四個 multiplier 的 PRODUCT[2:0] 與 FS_1/SUM[0] 均無內部用途，父層只接到 SYNOPSYS_UNCONNECTED wires；沒有放行 consumed gate input 或 live output 的 X。完整 56 筆解釋保留在 parent receipt 的 `unknown_activity.records`。唯一 PTE-003 對應 68 個 propagated constant arcs，check_power 無 load/ramp range issue。

新增 operational reviewer `review_cgof2_unknowns.py` 的首次自檢 exit 1：解析器未支援 `output LT, GT, EQ, LE, GE, NE;` 的共用宣告。修正宣告解析後，`check_cgof2_unknown_review.py` 第二次 exit 0：原結構通過，三個記憶體內的錯誤變體皆被拒絕，包括 X 改到 live path、啟用原裁剪 SUM[0]、以及對 unconnected wire 新增 consumer。兩次 stdout/stderr/exit 原樣保留；這是父審工具修正，不是 RTL/TB 或 capture 修復。

| 同 seed 509 / arm A 政策 | internal mW | switching mW | leakage mW | total mW | CGOF2 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF2 | 1.331 | 0.01895 | 2.112 | 3.462 | — |
| FCFS | 1.306 | 0.01779 | 2.032 | 3.356 | +3.1585% |
| RR10 | 0.9995 | 0.01343 | 1.546 | 2.559 | +35.2872% |
| Main | 1.331 | 0.01918 | 2.116 | 3.466 | −0.1154% |

匹配條件仍為原 seed/arm、trace/profile/PVT、25 ns、10,000,000 warmup、100,000 measured cycles，SAIF duration 2,500,000 ns。CGOF2 accepted/fired 均為 `[97716,788,745,751]`，cut/end outstanding 均為 `[15,0,0,0]`；FCFS/RR10/Main 的 admissions、fires 及邊界 outstanding 差異逐項保留在 [CGOF2/A/509 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof2-A-s509/parent-acceptance.json)。Matched trace 不代表相同逐筆服務；上述小幅差異僅為工具報表精度下的本窗估算，沒有統計顯著性或晶片量測結論。

同一 coordinator 已串行接續 CGOF2/B/509，原 run `cgof-power-cgof2-b-s509-20261107t015525z`；本輪 helper 只讀 SSH exit 0，共享 log 顯示 2,000,000 checked warmup cycles、compile/audit exit 0。alias 此次到 FastX-NN，其 process 清單不代表原 FastX-NN 工作。未另開 coordinator、未委派審查代理。`record_followup_20261107T0200Z.py` exit 0，核對目前六組 extension packages/payload checks/evidence archives，更新 `continuation.json`、本輪 review receipt、SHA256SUMS 與 `last-followup-state.json`。本輪命令、失敗/修復自檢、父審及 SSH logs 均在 `cohort-remaining/followup-20261107T0200Z-*` 與 `accept-cgof2-A509.*.txt`。全域完成封存仍待十二組全部父審通過，整體保持 **INCOMPLETE**。

### 2026-11-07 10:47 續接 — CGOF2/B/509 父審通過

本輪由 Codex CLI 自行只讀審查原 capture，於 10:50 通過 CGOF2/B/509，累計 **8/12**。命令為 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-B-s509`，exit 0。原 run `cgof-power-cgof2-b-s509-20261107t015525z` 在 FastX-NN 完成；compile、replay、SAIF/PrimeTime、tool-log audits、source check、shell、local audit 與父審 exits 全為 0，VCS version probe exit 1 單獨保留。來源 revision 為 `a3f4d8b1865c9af24eb86776274cc8c98428adc3`；39 份 current/archive sources、54 項 before/after bindings、package/payload、library/model/profile、vectors、SAIF/report 與 evidence hashes 均核對一致。沒有更動 frozen sources 或新派代理。

B 窗為 10,101,024 warmup 加 102,400 measured cycles，SAIF duration 2,560,000 ns。annotation 30,022/30,022 nets、29,221/29,255 leaf；9,014 個 FF clocks 全為 clk/file activity。34 個 literal D/SETB leaf 例外、56 筆結構上未使用的 constant-X records（24 omitted outputs、16 trimmed output bits、16 unconnected aliases）逐項核對；無 transient X/Z。唯一 PTE-003 為 68 個 propagated constant arcs，check_power 無 load/ramp range issue。

| 同 seed 509 / arm B 政策 | internal mW | switching mW | leakage mW | total mW | CGOF2 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF2 | 1.331 | 0.01858 | 2.112 | 3.461 | — |
| FCFS | 1.306 | 0.01755 | 2.032 | 3.355 | +3.1595% |
| RR10 | 0.9991 | 0.01309 | 1.547 | 2.559 | +35.2481% |
| Main | 1.331 | 0.01873 | 2.116 | 3.465 | −0.1154% |

匹配既有 seed/arm、trace/profile/PVT、25 ns 與原量測窗，未重跑 baseline。CGOF2 accepted/fired 均為 `[100000,800,800,800]`，cut/end outstanding 均為 `[15,0,0,0]`。FCFS accepted/fired 為 `[100008,800,800,800]` / `[100007,793,800,800]`，end outstanding `[16,7,0,0]`；RR10/Main accepted/fired 為 `[100002,800,800,800]` / `[100001,799,800,800]`，end outstanding `[16,1,0,0]`，各 baseline cut outstanding 均 `[15,0,0,0]`。完整差異及 hashes 保留於 [CGOF2/B/509 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof2-B-s509/parent-acceptance.json)；同 trace 不代表逐筆服務相同。

唯一 coordinator PID 41940 仍存活，stderr 0 bytes、exit 尚未產生，已串行接續 `cgof-power-cgof2-a-s510-20261107t022929z`。沿用本機 fastx-ews Skill/helper 的只讀 SSH exit 0，原共享 run 顯示 6,000,000 checked warmup cycles，compile/audit exit 0、remote exit pending。alias 實際到 FastX-NN，原 run 的 hostname receipt 為 FastX-NN；alias process 清單不能代替原 backend 的工作狀態。未新增 coordinator、未重跑 accepted capture 或長 drain。`record_followup_20261107T0247Z.py` 核對已完成七組 extension 的 package/payload/evidence，更新 continuation、review receipt、本輪 SHA256SUMS 與同結構去重 state；全域完成封存及停止 schedule 留待十二組父審全部通過。其餘四組 CGOF2 仍待完成，整體 **INCOMPLETE**。

進度 recorder 第一次 exit 1：Windows PowerShell 產生的 SSH stdout 為 UTF-16，原讀取器假定 UTF-8 而拋出 `UnicodeDecodeError`。失敗發生在 continuation/state 寫入之前；原 stdout/stderr/exit 全部保留。補入 BOM 編碼判斷後，第二次 `record_followup_20261107T0247Z.py` exit 0，確認 accepted_total=8、coordinator RUNNING、stderr_bytes=0、coordinator_exit=null。此修正僅限 ignored operational recorder，未變更 capture 或 RTL/TB。

### 2026-11-07 11:14 續接 — CGOF2/A/510 父審通過

本輪 Codex CLI 自行審查既有 `cgof-power-cgof2-a-s510-20261107t022929z`，於 11:14 通過父審，累計 **9/12**。父審命令為 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-A-s510`，exit 0。原 run backend 為 FastX-NN；compile、sim/replay、SAIF/PrimeTime、tool-log audits、source check、shell、local audit 與父審 exit 均 0，VCS version probe exit 1 單獨保留。revision `a3f4d8b1865c9af24eb86776274cc8c98428adc3`、39 份 current/archive sources、54 項 remote before/after bindings、package/source/library/model/profile、vectors/SAIF/reports/evidence hashes 均核對一致；沿用 index export_directory，未修改 frozen sources。

A 窗為 10,000,000 warmup 加 100,000 measured cycles、SAIF 2,500,000 ns。annotation 30,022/30,022 nets、29,221/29,255 leaf；全部 9,014 FF clocks 為 clk/file activity。34 個 literal D/SETB leaf 例外與 56 個結構上未使用的 constant-X records（24 omitted outputs、16 trimmed output bits、16 unconnected aliases）逐項核對；無 transient X/Z。唯一 PTE-003 為 68 個 propagated constant arcs，check_power 無 load/ramp range issue。

| 同 seed 510 / arm A 政策 | internal mW | switching mW | leakage mW | total mW | CGOF2 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF2 | 1.331 | 0.01897 | 2.112 | 3.462 | — |
| FCFS | 1.306 | 0.01781 | 2.032 | 3.356 | +3.1585% |
| RR10 | 0.9995 | 0.01345 | 1.547 | 2.560 | +35.2344% |
| Main | 1.332 | 0.01921 | 2.116 | 3.467 | −0.1442% |

CGOF2、RR10、Main 的 accepted/fired 均為 `[97654,809,772,765]`，cut/end outstanding 均 `[15,0,0,0]`；FCFS accepted `[97655,809,772,765]`、fired `[97655,809,771,765]`，outstanding 由 `[15,0,0,0]` 變為 `[15,0,1,0]`。Matched seed/arm、trace/profile/PVT、25 ns 與原量測窗一致，保留實際 admissions/fires 差異，不把同 trace 說成逐筆服務相同。完整命令、hashes、stage exits 與比較在 [CGOF2/A/510 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof2-A-s510/parent-acceptance.json)。

唯一 coordinator PID 41940 仍存活，stderr 0 bytes、active exit receipt 尚未產生，已串行接續 CGOF2/B/510 `cgof-power-cgof2-b-s510-20261107t030331z`；其輸入為 index 指定的 `export-recovery-cgof2-B-s510-20261107T002822Z`，原 partial 保留。FastX Skill/helper 只讀 SSH exit 0，原共享 run 顯示 3,000,000 checked warmup cycles、compile/audit exit 0、remote exit pending；alias 此次到 FastX-NN，而原 run hostname receipt 為 FastX-NN，未將 alias process 清單當作原 backend 狀態。未新增 coordinator 或審查代理、未重跑 accepted captures、baseline 或 directed drain。

`record_followup_20261107T0314Z.py` exit 0，核對八組完成的 extension packages、bootstrap payload checks 與 evidence archives，寫入 continuation snapshot、本輪 review receipt/SHA256SUMS 與同 precheck 結構的 `last-followup-state.json`。長 drain 保留既有十二 tests、三配置各 923 cycles/outstanding 0 的驗收。剩 CGOF2/B/510、A/511、B/511 待完成及父審，整體 **INCOMPLETE**；全域 artifact-index/SHA256SUMS 封存與停止既有續接排程留待全十二組驗收後。

### 2026-11-07 11:57 續接 — CGOF2/B/510 recovery capture 父審通過

本輪 Codex CLI 自行核對原 `cgof-power-cgof2-b-s510-20261107t030331z`，11:58 父審通過，累計 **10/12**。首次使用 `accept_cgof2_power_case.py cgof2-B-s510` exit 1：審查工具假定封包為 canonical case basename，找不到 `cgof2-B-s510.tar`；實際 coordinator 的 `package(directory)` 依 export_directory basename 建立 `export-recovery-cgof2-B-s510-20261107T002822Z.tar`。此時尚未寫入 parent receipt；原失敗 stdout/stderr/exit 保留，不能當 capture 失敗或另開 replay。

另存 ignored operational reviewer `accept_cgof2_export_package.py`，保留原 reviewer 與所有已接受 receipt 的 source hash。新 reviewer 依 index export_directory basename 定位原封包，額外核對 package_bytes；其餘驗收條件相同。命令 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-B-s510` exit 0，logs 為 `accept-cgof2-B510.attempt02.*.txt`。原封包 212,418,560 bytes、SHA256 `2466efc23b241b98426acc6ecdc27812bb446e53f8726ffb2ef98b1a06473192`，與 index、原 remote command 與 bootstrap payload 校驗一致；未重建封包、未重跑 capture。後續 A/511 也須使用這個 reviewer 解析其 recovery export，B/511 canonical export 同樣適用。

原 backend FastX-NN；compile、sim/replay、SAIF/PrimeTime、tool-log audits、source check、shell、local audit 與父審 exits 全 0，VCS version probe exit 1 單獨保留。revision `a3f4d8b1865c9af24eb86776274cc8c98428adc3`、39 份 current/archive sources、54 項 remote before/after bindings、mapping/library/model/profile、vectors/SAIF/report/evidence hashes 均核對一致。B 窗 10,101,024 warmup、102,400 measured cycles、SAIF 2,560,000 ns；annotation 30,022/30,022 nets、29,221/29,255 leaf，9,014 FF clocks 均為 clk/file activity。34 個 literal-pin 例外與 56 個結構上未使用的 constant-X records 逐項核對，無 transient X/Z；唯一 PTE-003 對應 68 個 propagated constant arcs，check_power 無 range issue。

| 同 seed 510 / arm B 政策 | internal mW | switching mW | leakage mW | total mW | CGOF2 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF2 | 1.331 | 0.01859 | 2.113 | 3.462 | — |
| FCFS | 1.306 | 0.01755 | 2.033 | 3.356 | +3.1585% |
| RR10 | 0.9991 | 0.01309 | 1.548 | 2.560 | +35.2344% |
| Main | 1.331 | 0.01874 | 2.117 | 3.466 | −0.1154% |

四個政策在這個 seed/arm 的 accepted/fired 均為 `[100000,800,800,800]`，cut/end outstanding 均 `[15,0,0,0]`；matched trace/profile/PVT、25 ns 與原量測窗核對一致。完整命令、package path/hash、stage exits、annotation/X/warnings 與 matched 比較見 [CGOF2/B/510 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof2-B-s510/parent-acceptance.json)。baseline 十八組與 directed drain 未重跑，frozen sources 未改，未委派審查代理。

唯一 coordinator PID 41940 仍存活，stderr 0 bytes、active exit receipt 尚未產生；已串行接續 A/511 `cgof-power-cgof2-a-s511-20261107t033809z`，輸入為 index 指定的 recovery export。FastX Skill/helper 只讀 SSH exit 0，原共享 run 顯示 5,000,000 checked warmup cycles、compile/audit exit 0、remote exit pending；alias 實際到 FastX-NN，原 run hostname receipt 為 FastX-NN，alias process 清單不代表原 backend。`record_followup_20261107T0357Z.py` exit 0，核對九組 extension 的原 package bytes/hash、payload checksum 與 evidence archives，更新 continuation、原快照、本輪 review/SHA256SUMS、package 定位規則與同 precheck 結構的去重 state。剩 A/511、B/511 待完成及父審；長 drain 沿用十二 tests、三配置各 923 cycles/outstanding 0。整體 **INCOMPLETE**；全域封存及停止既有排程仍待十二組全部驗收。

### 2026-11-07 12:21 續接 — CGOF2/A/511 父審通過

本輪 Codex CLI 自行核對原 `cgof-power-cgof2-a-s511-20261107t033809z`，12:21 通過父審，累計 **11/12**。命令 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-A-s511` exit 0；原 backend 為 FastX-NN。index 指向 `export-recovery-cgof2-A-s511-20261107T002822Z`，實際沿用同名原 tar，package SHA256 `d4f38678dea0a415800a1ed941fedd1e5543c89fe0f8b6e9e217e7948063ce8b` 與 index、package_bytes、原 remote command 及 bootstrap payload 校驗一致；canonical 仍保存 remote evidence/parent receipt，原 partial 保留。未重建套件、未重跑 capture。

compile、sim/replay、SAIF/PrimeTime、tool-log audits、source check、shell、local audit 與父審 exits 全為 0，VCS version probe exit 1 單獨保留。revision `a3f4d8b1865c9af24eb86776274cc8c98428adc3`、39 份 current/archive sources、54 項 remote before/after bindings、mapping/library/model/profile、vectors、SAIF/reports/evidence hashes 均核對一致。A 窗保持 10,000,000 warmup、100,000 measured cycles、SAIF 2,500,000 ns；annotation 30,022/30,022 nets、29,221/29,255 leaf，9,014 FF clocks 均為 clk/file activity。34 個 literal-pin 例外與 56 個結構上未使用的 constant-X records 已逐項核對，無 transient X/Z。唯一 PTE-003 對應 68 個 propagated constant arcs，check_power 無 range issue。

| 同 seed 511 / arm A 政策 | internal mW | switching mW | leakage mW | total mW | CGOF2 相對 total |
|---|---:|---:|---:|---:|---:|
| CGOF2 | 1.331 | 0.01898 | 2.112 | 3.462 | — |
| FCFS | 1.306 | 0.01782 | 2.032 | 3.356 | +3.1585% |
| RR10 | 0.9995 | 0.01346 | 1.547 | 2.560 | +35.2344% |
| Main | 1.332 | 0.01922 | 2.116 | 3.467 | −0.1442% |

四個政策在這個 seed/arm 的 accepted/fired 均 `[97595,777,815,813]`，cut/end outstanding 均 `[15,0,0,0]`；matched trace/profile/PVT、25 ns 與原量測窗保持一致。完整命令、package path/hash、stage exits、annotation/X/warnings 與比較見 [CGOF2/A/511 parent acceptance](../../artifacts/implementation/fastx-power-20261107/cohort-extension/cgof2-A-s511/parent-acceptance.json)。此小幅 total 差異限工具報表精度下的本窗估算，不是統計或晶片結論。

唯一 coordinator PID 41940 仍存活，stderr 0 bytes、active exit receipt 尚未產生；正執行最後一組 B/511 `cgof-power-cgof2-b-s511-20261107t041318z`。FastX Skill/helper 只讀 SSH exit 0，原共享 run 顯示 2,000,000 checked warmup cycles、compile/audit exit 0、remote exit pending；alias 此次到 FastX-NN，原 run hostname receipt 為 FastX-NN，alias process 清單不代表原 backend。`record_followup_20261107T0421Z.py` exit 0，核對十組 extension 的原 package bytes/hash、payload checks 與 evidence archives，更新 continuation、原快照、本輪 review/SHA256SUMS 及同 precheck 結構的去重 state。未新增 coordinator、審查代理或 campaign，未變更 frozen sources，未重跑任何 accepted capture、baseline 或 directed drain。長 drain 保留十二 tests、各 923 cycles/outstanding 0；整體 **INCOMPLETE**，全域封存及停止既有排程留待最後一組實際驗收。

## 2026-11-07 13:13 最終驗收與封存

本任務已達成 **ACCEPTED_AUTHORIZED_SCOPE：12/12 CGOF captures、18 組重用 baseline、定向長 drain 12 tests 通過**。前述時間點的 INCOMPLETE 是保留的歷史快照；最新驗收以本節及 [final-acceptance.json](../../artifacts/implementation/fastx-power-20261107/cohort-extension/final-acceptance.json) 為準。

最後 CGOF2/B/511 原 run `cgof-power-cgof2-b-s511-20261107t041318z` 在 FastX-NN 完成，沒有重啟。父審命令 `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-B-s511` exit 0；compile、sim、replay/SAIF audit、PT、log/source/shell/local audits 全為 0，VCS version probe 1 另行保留。internal/switching/leakage/total 為 **1.331/0.01858/2.114/3.463 mW**。原 package SHA256 `20083ed97ad011c2d57e715aba0702841dc59f6e2381a5589b23e9466fa01dfa`；remote evidence SHA256 `46dc74b8226ec82d54dce509484a61279bb8efb24f6964a3b702dd118b83eb0a`。

下表每列只比較同 seed、arm、exogenous trace、PVT/profile/clock/量測窗，單位 mW；沒有合併 A/B。完整三十組四項功耗、十二組 matched deltas、actual admissions/fires/outstanding、命令與 receipt/hash bindings 見 [可讀比較報告](../../artifacts/implementation/fastx-power-20261107/cohort-extension/MATCHED_COMPARISON.md) 與 [機器可讀比較](../../artifacts/implementation/fastx-power-20261107/cohort-extension/matched-comparison.json)。

| Seed/arm | FCFS total | RR10 total | Main total | CGOF1 total | CGOF2 total |
|---|---:|---:|---:|---:|---:|
| 509/A | 3.356 | 2.559 | 3.466 | 3.416 | 3.462 |
| 509/B | 3.355 | 2.559 | 3.465 | 3.415 | 3.461 |
| 510/A | 3.356 | 2.560 | 3.467 | 3.416 | 3.462 |
| 510/B | 3.356 | 2.560 | 3.466 | 3.416 | 3.462 |
| 511/A | 3.356 | 2.560 | 3.467 | 3.416 | 3.462 |
| 511/B | 3.357 | 2.561 | 3.467 | 3.417 | 3.463 |

CGOF1 對 FCFS/RR10/Main 的 matched total 差異範圍分別為 +1.7873～+1.7884%、+33.4244～+33.4896%、−1.4710～−1.4422%；CGOF2 分別為 +3.1576～+3.1595%、+35.2206～+35.2872%、−0.1442～−0.1154%。範圍只是各配對觀察值，不是 pooled mean、信賴區間或顯著性。保留報表精度與 rounding，不從這些小差異推論實體功耗改善。

全組 net annotation 為 CGOF1 28,458/28,458、CGOF2 30,022/30,022；leaf 為 27,750/27,784 與 29,221/29,255，34 個 literal D/SETB 例外已核對；全部 8,998/9,014 FF clocks 是 clk/file activity。無 transient X/Z；20/56 個 constant-X records 均有結構上未使用的解釋；唯一 PTE-003 是 68 個 propagated constant arcs，check_power 無 load/ramp range issue。

`finalize_cohort.py` 是本輪新增於 ignored logs 的證據整合程式，exit 0；重新只讀核對 435 項 file bindings，包含所有新 package bytes/hash、evidence/SAIF/reports、current/archive sources、十八組既有 baseline receipt bindings 與長 drain 的 sources/JUnit/results。既有 CGOF1/A/509 的原 replay-audit/shell exit 1、修正後 local checker exit 0 與 PT-only continuation exit 0 全部保留；最終父審直接核對同份 capture 的 topology/constant-X/FF clocks/disabled arcs/報表及 matched 條件，未重跑 capture。各 preparation NOT_RUN、舊 semantic review required 與觀察當時的 INCOMPLETE receipt 不覆寫。

恢復 coordinator PID 41940 已正常完成，`recovery.exit.txt` 真實值 0、stderr 0 bytes；原 coordinator PID 40540 的 exit 仍未知。只讀 SSH/helper 本輪 exit 0，alias 到 FastX-NN、原共享 run hostname 為 FastX-NN；判斷完成依原 run 的 remote exit、stage exits 與 evidence hash。未建立新 coordinator、未停止他人程序、未新增 agent/campaign。長 drain 沿用原 `20261106T230245Z_18888`：三配置各 923 cycles/923 筆/outstanding 0，12 tests 無 failure/error/skip，沒有重跑。

主模型實際路由為 Codex CLI `group/gpt-6.1-sol-2` / high，Cindy live runtime 核對；RTL/TB 與 directed drain 仍為 Claude Code `claude-opus-5-5` / requested medium / `rtl-agent-team:testbench-dev`，本輪沒有 RTL/TB 修改或新委派。全域索引更新到 [artifact-index.json](../../artifacts/implementation/fastx-power-20261107/artifact-index.json)；舊索引及原 SHA256SUMS 保存於 `snapshots/pre-cohort-closure/`。本任務的既有自動續接 `213559e5-1778-4839-b449-f9b37c1c4284` 在封存時暫停，保留歷史。

## 限制

本次指定功耗 cohort 與定向長 drain 已驗收；功耗仍屬 pre-layout、zero-delay、no-SDF gate-level estimate，不包含實體 clock tree、SPEF、APR、glitch 或 silicon。歷史 baseline 巨大 vector bytes 未重新 hash；沿用原 accepted receipts 與 traffic-source/trace bindings。定向 drain 是 reset/all-High、engineering seed 7301，沒有 window close，不代表 trained-class 演化、公平性或系統延遲驗證。未升級論文或實體晶片結果，也不放行其他昂貴 campaign。
