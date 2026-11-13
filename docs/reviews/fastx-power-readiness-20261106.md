# FastX CGOF 功耗接手驗收：2026-11-06

狀態：**INCOMPLETE；CGOF power unmeasured**。本輪交付可執行的輸入稽核工具、
遠端只讀 preflight 與實際證據索引，尚未交付 CGOF SAIF 或功耗數字。
未執行新的 confirmation、RTL 模擬、綜合或功耗工作。長 backlog drain 仍未驗證。

## 實際完成的工作

- `scripts/audit_fastx_power.py`：以原 repository 為只讀 evidence root，逐目錄核對
  confirmation manifest、cohort、job identity、trace hash 與當前 source hashes；
  檢查兩個 N4 CGOF DC/PT bundle 的 download receipt、網表、SDC、來源和報表；
  檢查兩個 Formality download bundle 與既有 trained-power acceptance index。
  結果輸出到本 worktree 下全新的 `artifacts/` 子目錄，拒絕覆寫、路徑逸出與
  linked path。缺件、無效 JSON、重複完整 seed 目錄均保留於報告，不拼接目錄。
- `scripts/fastx_power_preflight.sh`：只輸出 backend、帳號、module、工具路徑／
  版本命令的 exit、本人 process 摘要、allocation 指標和指定輸入檔 hash。
  版本查詢使用 `/usr/bin/timeout`；不啟動分析、不建立遠端目錄，不列出 license
  環境變數。脚本 exit 0 表示完成盤點，並不代表工具 license 或功耗驗收通過。
- `scripts/test_audit_fastx_power.py`：8 項合成證據測試通過，包括部分目錄不拼接、
  完整目錄重複、identity／trace 錯配、source drift、網表破壞、嚴格 JSON 與
  輸出範圍／覆寫保護。這些是工具測試，不能算 scheduler verification。

主機是 Jay_workshop；僅在 host 建立的 `sharp-bohr` worktree 寫檔。
原 repository 的 README 與未追蹤文件未被改動。起始 revision 為
`a3f4d8b1865c9af24eb86776274cc8c98428adc3`。未建立 branch 或 commit。

## 當前產物與活動工作

本機實際稽核得到 23 個 confirmation 目錄：7401–7420 各有一個包含 30 jobs、
manifest 與 cohort 的完整目錄；另有 7401 的空目錄、7405 的 12-job 中斷目錄、
7407 的 6-job 中斷目錄。沒有缺少或重複的完整 seed。
完整目錄的 embedded identity／trace 核對及所列 source 對當前原 repository 的
雜湊比對均無差異。本輪標示 `COMPLETE_FILES_OBSERVED`，不取代既有 per-seed
acceptance，不重新執行統計或模擬。11/5 的 7405 24/30 快照已過時。

WSL process snapshot 仍觀察到另一項 `run_capacity_absorption.py` 工作，
五個 seeds 8101–8105、under／over、W5M、6 workers；未接管或停止。
FastX process 觀察僅涵蓋實際連入的 backend，不代表學校所有 backend 沒有工作。

## 可沿用的輸入

| 輸入 | 本輪實際核對 | 使用邊界 |
|---|---|---|
| CGOF1 N4 DC/PT | download receipt 所列檔案全部 hash 相符；7 個 RTL／filelist hashes 相符；遠端網表與 SDC hash 相符 | HIGH_WEIGHT=1、N4、D16、W5M、cgof_unit_top |
| CGOF2 N4 DC/PT | 同上 | HIGH_WEIGHT=2；其餘共同參數相同 |
| 兩組 Formality 報表 | receipt 所列檔案 hash 相符 | 保留原 scoped equivalence 限制；未重新做 formal acceptance |
| Trained baseline | 固定 acceptance index hash 相符；18 個唯一 policy／seed／arm identities 完整 | FCFS、RR10、Main；509／510／511；A／B；本輪未重新驗收 raw capture |
| DB 與 cell model | 遠端可讀並取得相同 hash | SAED32 RVT TT0.78V25C；專有資產留在學校 |

共同 profile canonical SHA256：
`6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`。
條件為 25ns／40MHz、理想 clock、ForQA/top wire-load、無 APR／SPEF／SDF。
DB SHA256：`844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`。
標準 cell model SHA256：`d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286`。
另發現 verilog_pg model，hash 不同，不得替換為同一輸入。

既有 trained A 的 warmup／量測為 10,000,000／100,000 cycles，B 為
10,101,024／102,400 cycles。兩者分開保留，不與 cold 或 boundary captures 混用。
既有 netlist 不必重新綜合；不採用設計稿中的 classifier register 手動裁除建議。

## SSH 與環境的實測結果

直接從 agent terminal 呼叫指定 `fastx-connect.ps1 -RemoteCommand` 成功。
先前桌面互動路徑不穩定，之後已依主人指示改為 terminal。當時本機 helper／skill
已更新；其目前呼叫方式與最早讀取版本不同，未修改 helper 或全域登入設定。
backend、私有絕對路徑與完整命令保存在 ignored logs，不寫入可攜式設定。

| 檢查 | 實際結果 |
|---|---|
| account／backend | chiang22；terminal 首次 FastX-NN，後續只讀命令 FastX-NN |
| module | Synopsys_x86-64/2024，load exit 0 |
| dc_shell -version | W-2024.09，exit 1；保留此非零 exit，不當 license PASS |
| pt_shell -version | W-2024.09，exit 0；未做 license checkout 驗證 |
| vcs | command -v exit 0；未編譯或執行 simulator |
| scheduler／allocation | srun／salloc／sbatch／squeue／qstat／bsub 不在目前 PATH；三種 allocation ID 均 UNSET |
| 遠端功耗 | NOT_RUN；annotation coverage、leakage／internal／switching／total 均未量測 |

第一版 preflight 的 module stderr 被 PowerShell helper 視為錯誤，呼叫 exit 1；
修正為將遠端命令的 stderr 與 stdout 一起擷取後，完整 v2 preflight exit 0。
所有內部命令的非零 exit 仍保留。這個修復只改善證據擷取，不改 EDA 結果。

## 真正的剩餘依賴

1. **功耗 cohort freeze**：既有 baseline 是 509–511、A／B；P1 設計稿卻將
   P1 seeds 定為 8101–8105，而 CGOF power 僅寫「三 seeds」，未選定哪三個及
   arm。設計稿明示不是凍結協定。若採新 P1 seeds，必須產生相同 seeds 的
   baseline；若擴充舊 trained cohort，需明確記錄沿用 509–511／A／B 的決策。
   目前不能用不同 cohort 直接計算 CGOF 對 baseline 的差值。
2. **CGOF activity／PT adapter**：既有 exporter、tb_power、run_power_pilot 與
   power_pt 固定 switch_top、policy IDs 0/1/2，CGOF 則是 cgof_unit_top 與
   HIGH_WEIGHT=1/2。不能把 baseline vector 或 policy 名稱換字就當 CGOF 量測。
   Freeze 後應沿用 stimulus、reference checks 與共用功耗方法，另補 top/config
   adapter 的驗證；不得更動已驗收 netlist 或另加 policy-dependent pipeline。
3. **允許的 compute 執行位置**：目前未找到可驗證的 allocation／長 EDA 執行
   規則，module help 沒有補充此資訊。不能由連線、版本或歷史成功推定。
   需先取得實際可用的學校 compute 路徑／執行許可，再做一次有界 pilot；
   pilot 才驗證實際 license、gate-level replay、SAIF scope／duration／coverage、
   PT power 報表及四個 power components。

本輪未另外開長 EDA、license 測試或新的遠端 run 目錄。其餘 FastX 候選依賴為：
under／over RTL 必須先有已凍結模型配對與 matched RTL jobs；directed drain 的
harness 完成條件尚未處理；latency recovery 尚無可驗收的 accounting pipeline。
這些項目不由本輪自動放行。

## 路由與審查

- 主模型：Cindy live runtime `codex`／`group/gpt-6.1-sol-2`／high，
  provider_id `magpie-18cf0ecc`。負責遠端唯一協調、工具實作及整合驗收。
- 來源盤點：agy 1.5.1／`gemini-3.8-flash-high`／high，只讀原件與產物；
  init receipt 確認 model ID。反覆 provider error 後仍未交付最終報告，主模型
  以完整 prompt 與 PID 核對身分後停止本任務的 worker；process exit -1。
  其零散讀取不列為獨立驗收，來源／產物由主模型直接核實。
- 環境／流程審查：相同 Flash 路由，exit 3，`UNAVAILABLE`／503，
  provider 回報該 model 無容量；沒有成功報告，未靜默改派其他模型。
- 實作前獨立審查：agy／`gemini-4-argon-high`／high，exit 0，
  結論 ADOPT WITH CONCRETE CORRECTIONS。已採用 input-root 分流、partial
  directory 分類、來源分層、輸出隔離與有界 preflight。
  審查提到的部分報表名稱和「manifest job SHA entries」不符合實際 schema，
  實作改核對真實 filenames／trace identities，另存新觀察的 file hashes。
- agy 請求 `--mode auto`，但帳號不支援，CLI 回退 default mode；init
  receipt 是 `permission_mode=always-proceed`。不得將此次執行稱為 auto。
  Effort high 為 invocation request；沒有供應商層級的推理深度證明。

## 可重現命令與證據索引

`EvidenceRoot` 指向原 repository；命令從本 worktree 執行。

```powershell
./.venv-fastx-power/Scripts/python.exe scripts/audit_fastx_power.py --evidence-root $EvidenceRoot --out artifacts/implementation/fastx-power-20261106/a-fresh-audit
./.venv-fastx-power/Scripts/python.exe -m unittest discover -s scripts -p test_audit_fastx_power.py -v
wsl -e bash -n scripts/fastx_power_preflight.sh
```

| 本輪命令／產物 | exit／狀態 |
|---|---|
| audit，input-audit-final | 2；刻意 fail-closed，INCOMPLETE |
| unittest，8 tests | 0；8 passed，無 skip |
| bash -n | 0；僅 shell syntax |
| remote-preflight-v2 | 0；盤點完成，非功耗驗收 |
| remote-inputs／remote-model | 0／0；只讀 hash 與 module help |

可開啟的主要產物：

- `artifacts/implementation/fastx-power-20261106/input-audit-final/audit.json`
  及同目錄 `SHA256SUMS`：本輪逐檔 inventory 與判定。
- `.setup-logs/implementation/fastx-power-20261106/`：prompts、各 worker stream／
  stderr／exit、完整 remote command／stdout／stderr／exit、test logs、
  local-jobs snapshot、source inventory、Git diff 與 artifact 索引。

這些 ignored 產物必須隨工作交接保留；只有 tracked 文件而沒有上述證據時，
不得將本輪報告當成新的功耗結果。所有功耗若後續完成，也只屬 pre-layout
gate-level estimation，不能稱為實體晶片量測。
