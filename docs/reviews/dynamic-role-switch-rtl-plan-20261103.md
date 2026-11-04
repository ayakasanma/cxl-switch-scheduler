# 多視窗動態／角色切換 RTL：凍結實驗計畫與成本估算

日期：2026-11-03。狀態：**FROZEN_PROTOCOL_NOT_RUN**。
執行就緒度：**BLOCKED_ON_MAIN_AND_AUDIT_IMPLEMENTATION**。
本輪授權為規劃、成本估算與 commit；未啟動模擬、RTL 實作或 EDA。
機器入口：[dynamic-role-switch-rtl-plan-20261103.json](dynamic-role-switch-rtl-plan-20261103.json)。
研究協定凍結與程式可執行分開；日後實作不能偷偷更改研究設計。

## 0. 兩位 reviewer 的回饋整合

來源一：Orca Worker reviewer（fzfqgpl9p81gsljob6qhey68）的方向 A／B3、claim matrix 與 gap review。
來源二：Orca Worker reviewer-2（fe32ywtpnoekmp81ca1l95mr）的完整故事與五缺口大綱（commit 9d59fe8）。
兩份審查不是兩份獨立實驗證據。逐項來源／決策另列 JSON reviewers。

| ID | 來源與回饋 | 採納／延後方式 | 對應 |
| --- | --- | --- | --- |
| R1 | reviewer：B1/B2 不阻擋現有報告，C7 單種子，C5/C6 模型證據 | 採納；此為擴充研究，原報告不升格 | §1、§5 |
| R2 | reviewer：W256 NOT_CONFIRMED 與 W5M 描述性結果不可混算；無無條件 Pareto 贏家 | 採納；只研究新協定的 Main/CGOF 效果 | §3、§5 |
| R3 | reviewer：C1/C2 曾綁錯 hash，24 項來源須各自驗證 | 採納；逐 path 驗證 hash，不只驗證來源數量 | §9 |
| R4 | reviewer-2：四視窗、角色反轉、ready 形狀、D8/D16 需要多種子 RTL | 採納；五案例固定、20 正式 seed blocks | §2、§5 |
| R5 | reviewer-2：加入 Main 及 RR10 | Main 必要；RR10 延後另凍結計畫，不因觀測到 null 就臨時追加 | §2、§4 |
| R6 | 兩位 reviewer：區分生成角色／實體來源及延遲／間隔 | 採納；雙帳本、逐來源 Heavy gap、單筆恆等式 | §3 |
| R7 | reviewer-2：其餘四缺口與 B3 修復 | 延後 under/over、功耗／裁切、恢復／規模與系統級；B3 已完成 | §1 |
| R8 | Astra：拆開線性成本與保留量；Main 先通過 gates | 採納；Lead 再修 raw-config、CLI、統計及資源假設 | §4–§9 |

原始文件入口：docs/PROJECT_STORY_AND_GAPS_OUTLINE.md、docs/THEORY_ANALYSIS_AND_REVIEW_GAPS_2026-11-02.md、docs/final-report/update-20261102/CLAIM_EVIDENCE_MATRIX_20261102.md 與 ACCEPTANCE_20261102.md。

## 1. 研究問題與證據邊界

問題：共同外生生成／ready 規則下，跨四個真實 W5M 分類邊界與實體角色反轉時，Main 類別配額與 CGOF 逐源配額如何改變 Sparse 尾端等待、Heavy 服務間隔及完成時間？
既有 seed7291 五案例、20jobs／10pairs 僅為 SINGLE_SEED。本輪規劃不改寫該標記。
Main 的 service→class→service 回饋是介入的一部分；不能假定 Main 必然較差，也不能刪除 class 軌跡不如預期的 seeds。

不測 under/over、CGOF 閘級功耗、分類器裁切、N8/N16、正式 latency_recovery 或 CXL/application。
state settling 不等於 latency recovery。W256 ordering NOT_CONFIRMED 與 W5M 五 seed DESCRIPTIVE 不混入本輪。
20 seeds 是固定研究規模，並非 power 保證；跑完不自動 CONFIRMED，也不能推出普遍贏家或等價。

## 2. 唯一凍結矩陣

共同條件：N4、單輸出、105-bit descriptor、32-bit arrival metadata、W=5,000,000、windows=4、finite Heavy work=17,500,000、near、oldest-first。
near 真實參數為 Heavy p=.80、每個非 Heavy 來源 Sparse p=.02、ready p=.90。
約21.875M active cycles 主要來自 Heavy 生成速率 .80，不是出口 ready=.80。
政策：Main（approved Prior-Hold、class 10:10）、CGOF-1:1、CGOF-2:1；每格必有 mixed／isolated。

| case順序 | D | Heavy來源表（最後值延續） | ready規則 | seed7291 run尾碼 |
| --- | ---: | --- | --- | --- |
| multi-window | 16 | [0] | Bernoulli p=.90 | 52851 |
| role-switch | 16 | [0,0,1,1] | Bernoulli p=.90 | 52853 |
| ready-spread | 16 | [0] | period100，90 slots均勻分散 | 52850 |
| ready-bursty | 16 | [0] | period100，前90 ready／後10 stall | 52849 |
| depth8-bursty | 8 | [0] | period100，前90 ready／後10 stall | 52852 |

spread使用既有公式 floor((position+1)*90/100)>floor(position*90/100)，不是4-on/1-off；bursty不是40-on/10-off。
每 seed = 5 cases × 3 policies × 2 lanes = **30 RTL jobs／15 mixed-isolated pairs**。
Pilot + 20 seeds = **630 jobs／315 pairs**；正式分析僅600jobs／300pairs。
RR10不納入。若增加會多210jobs；以舊CGOF均值代理約369.37 job-hours，RR10實際速度未量測。須另提計畫，不能按本輪結果追加。

active cap固定 **24,000,000 cycles**；reset後含drain的非reset cycles必須 **<25,000,000**。
每job恰好四個active closes：4,999,999／9,999,999／14,999,999／19,999,999。
windows=4本身不會停止classifier；不得延長至第五close補資料。

## 3. 輸入、cohort與量測契約

### 3.1 Whole-protocol有限cohort

保留既有finite-heavy協定：生成器依seed/cycle/source產生外生arrivals與ready，Heavy生成滿17.5M後停止；Sparse持續到各job最後一筆Heavy fire（包含該cycle）。
cut後不再生成，沿用 **ready=1 cleanup**，drain bound為cut時 2*(producer_backlog+fifo_occupancy)+128，不reset。
主要Sparse P99包括各自cut前生成的全部Sparse requests及drain完成者；不是active-only、共同固定horizon或phase-only。

同case/seed的完整Heavy生成序列必須相同，ready及Sparse共同active prefix亦須相同，以full streaming replay重新計算digest。
不同policy cut可能不同，完整Sparse count/hash可不同：全部公開，標 PROTOCOL_COHORTS_DIFFER，仍估計whole-protocol效果。
禁止事後截前min(count)個requests替代主要終點，禁止把不同cohorts當成同一批requests的個體因果效果。
未來若改共同horizon或scenario-ready drain，須另凍結、另命名，不能混跑。

### 3.2 雙帳本與指標

- 帳本A：依heavy_source(generation_cycle)固定生成時Heavy/Sparse角色；切換後未完成request不得重標。
- 帳本B：physical src0..src3的generated/accepted/fired/pending/censoring，與可由資料核對的分佈、digest；新per-source latency欄位須先實作驗證。
- 單request G→F=(G→A)+(A→F)，P99不可相加。Nearest-rank為ceil(.99*n)；n=0為null，isolated Sparse為N/A。
- Heavy gap沿用RoleBook/Gaps：同一physical source、active階段、accepted-minus-fired Heavy backlog條件內的completed inter_service episodes；不把不同來源Heavy fires相連、不跨empty episode，不混initial／terminated_by_empty／cut-censored。
- wall_cycles與eligible-ready opportunities各報histogram/count/P99/max；兩dimension的count不可相加冒充episode數。
- Heavy completion C=last Heavy fire+1；A=Cmixed−Cisolated。A=0、ordering delta=0、完成率=1不同；time ratio獨立命名。
- epoch_W0/W1/W2/W3及W4-tail的生成cohort只作計數／角色診斷。未先freeze並驗證epoch histogram不得做phase P99；不能從whole-run histogram回推Low-only或切換後恢復。

### 3.3 狀態／配額觀測

逐close記old/new classes、B/S、closing fire、counter clear及下一cycle生效；H/B_H映射effective High，L/B_L映射effective Low。
class紀錄來自model/harness，需和DUT pins逐cycle對齊，不能偽稱獨立raw-DUT分類軌跡。
quota compliance要求整窗pre-decision backlog，不用最後一cycle快照；缺資料標null，不當零。
refill v2分candidate／offered-held／committed-fire；Main class quota與CGOF source credit保留各自語義。
seed7291靜態case曾有1次effective transition，role-switch曾有3次；這是背景，**不是要求所有Main/seeds複製相同轉移次數的gate**。
若缺少預期effective-Low或角色效應，報 MECHANISM_NOT_EXPOSED、保留所有協定結果並收窄機制解釋，不換seed。

## 4. Main接線與開跑前gates

現有scripts/run_rtl_diagnosis.py的policy只接受1:1／2:1／both，top為cgof_unit_top；尚無Main診斷路徑。
Main RTL已存在於rtl/common/cxl_fai_main_sched.sv；須重用approved語義，不重寫另一策略。
未來接線須相同FIFO、105-bit payload、timestamp、hold/controller、sink timing及D8/D16邊界，不加policy-dependent pipeline/bypass/buffer。
CLI未來新增main／all；both仍表示兩CGOF。這是 **NOT_IMPLEMENTED介面契約**。

| Gate | 未來必交證據（本輪NOT_RUN） |
| --- | --- |
| M1 | strict lint／編譯，含production W及D8/D16；warning不靜默忽略 |
| M2 | Main獨立模型逐cycle對齊，W64/W256、四窗、角色切換、三ready形狀、D8/D16 |
| M3 | stall跨quota/class/window邊界，source/desc/context保持，只在fire扣額計數 |
| M4 | request identity、守恆、雙帳本/gap-kind、trace重播、缺檔fail-closed |
| M5 | 固定輸入下舊CGOF對照零退化；歷史artifacts/hashes不改 |
| M6 | runner/collector/analyzer、Main模型/RTL、compile defines、source ZIP重新freeze |

還須完成Main模型policy=FAI-inspired映射、完整輸入重播、raw/JUnit/timeout驗證與§5 exact統計；摘要不可預設PASS。
工程8–16h＋gates/review8h，合計16–24h、硬上限32h。不是10分鐘保證。逾時保持NOT_READY，不以缺Main子集當成完整campaign。

## 5. Seeds、統計與判定

獨立工程pilot：**7301**，30jobs；不混入推論、不根據效果挑選case/endpoint/seed。
正式順序：**7401, 7402, 7403, 7404, 7405, 7406, 7407, 7408, 7409, 7410, 7411, 7412, 7413, 7414, 7415, 7416, 7417, 7418, 7419, 7420**。
排除7291、舊508–548／6101–6605及保留7101–7105／7201–7220。
本地seed搜尋不證明其他電腦／外部實驗未用；開跑前重查結構化seed欄位與command records。碰撞先修訂整份協定再freeze，不臨時換成功seed。

**唯一主要終點**：mixed生成時Sparse全run G→F nearest-rank P99（cycles）。

| ID | case | delta（正值表示左側較差） | 工程差異 |
| --- | --- | --- | ---: |
| P1 | role-switch | Main − CGOF-2:1 | ≥1 cycle |
| P2 | role-switch | CGOF-2:1 − CGOF-1:1 | ≥1 cycle |
| P3 | multi-window | Main − CGOF-2:1 | ≥1 cycle |

Heavy gap與A是重要次要代價，不再混入主要檢定家庭。五案例／三政策全報原值、delta、mean/median/min/max與正零負數，不挑有利case。

方法固定：
1. n=20個完整seed blocks，不能用630jobs、requests或windows充作獨立樣本。
2. 每P計算K=sum(delta_s>=1)；採 **exact單尾binomial/sign事件檢定**，虛無為Pr_seed(delta_s>=1)<=.5。p=sum(comb(20,k), k=K..20)/2**20。平手、反方向、低於margin均計非成功，不刪除。這是seed-sampling詮釋下的跨seed重現性假設，不是所有workloads母體保證。
3. 僅三個P的p作Holm step-down，FWER=.05，p相同按ID排序；adjusted p取前序max並cap1。
4. 每P須Holm adjusted p≤.05 **且mean(delta)≥1 cycle**才SUPPORTED_WITHIN_PROTOCOL，否則NOT_CONFIRMED。負效應照實報。oracle正確且全跑完僅COMPLETE_VALID_EXECUTION。
5. paired bootstrap B=10,000、rng seed20261103，以整個seed block共同重抽樣；mean difference的percentile95%CI為名目、未多重校正的描述區間，不代替exact p、不證等價。使用Python stdlib random.Random(seed).randrange(20)，sorted10000值採nearest-rank第250及9750。
6. 7401–7405僅進度記帳，不是最小確認方案，不可看方向後選擇擴到20或提前成功。early stop只報STOPPED_INCOMPLETE及全部已見數值，不對成功子集做confirmatory inference。

missing不可轉0，不用pilot／舊7291補n。正式campaign不預留選擇性rerun、換seed；工具失敗也保留並停止，重啟須新版本及failure provenance。

## 6. 未來命令與逐seed release

以下只列未來規格，不在本輪執行。WSL先定位repo並source scripts/wsl_env.sh，不假設.venv/bin/activate。
現有CGOF支援的role-switch argv（7301是工程pilot）：

    python scripts/run_rtl_diagnosis.py --production-reviewed --mode finite-heavy --policy both
      --ordering oldest-first --seed 7301 --window 5000000 --windows 4
      --heavy-work 17500000 --profile near --depth 16 --heavy-sources 0 0 1 1
      --ready-pattern bernoulli --ready-period 100 --max-active-cycles 24000000
      --jobs 2 --make-jobs 1

上列換行僅為閱讀，實際使用JSON matrix.cases.argv_cgof_supported陣列，不拼接shell字串。
此時僅4jobs、為介面核對模板，**不批准先消耗held-out seeds跑CGOF子集**。
Main gates完成後只把policy both改為新實作all；其餘case/depth/heavy-sources/ready依JSON固定順序展開。
不使用不存在的seeds／depths／role-sequence／skip-pytest／out-dir旗標。
namespace由invocation-local wrapper設定runner NAME，使用runner分配的唯一run_id，不改global routing、不覆寫舊目錄。
每seed依case表順序，最多jobs2、make-jobs1、不平行seeds；完成整seed由supervisor保存release才放行下一個。

- execution/identity：5 scopes、30 jobs、15 pairs的完整cartesian set；summary overall=PASS，逐step/compile defines核對；JUnit無failure/error/skip，outer/build/sim皆exit0。
- source/control：pins/ZIP/config一致；full streaming replay與共同prefix digest正確；完整cohort差異照實標記。
- accounting：Heavy generated=accepted=fired=17.5M；每source與生成role守恆；final censor=0；cut pending=drain completed；完整排空。
- manipulation/oracle：四個active closes無第五close；含closing fire的arithmetic、各自policy state/pins和模型一致。外生角色表固定，不要求Main複製CGOF的3次transition。
- metrics：重算histogram/nearest-rank、source-local gap及G/A/F identity；isolated無Sparse，不假定三policy內部credit/history/latency逐值相等。
- resource：job≤3h、seed simulation≤34h、audit≤4h；保存wall、RSS、bytes、free space、stderr/exit及總預算餘額。

缺格、oracle/input失配、timeout、第五close或超支即停後續seed，保留所有資料。不得縮W/work/case/policy或提高jobs趕deadline。
自然class回饋差異按§3解釋，不誤作oracle失敗。工程pilot若需修correctness bug，先新source freeze並留attempt，不能把已看過結果當成新的held-out證據。

## 7. 實測成本與硬預算

來源為7291五份summary的20個cocotb步驟，path/hash/step/config在JSON cost.baseline_runs；不是由W256按W乘比例。

| baseline run_id | ready／D | run wall秒（jobs2） | 每job秒範圍 | 第一mixed job Sparse數 |
| --- | --- | ---: | ---: | ---: |
| 20261029T182230Z_52849 | bursty / D16 | 12,663.130 | 6,110.625–6,550.970 | 1,312,570 |
| 20261029T182230Z_52850 | spread / D16 | 12,611.574 | 6,134.364–6,475.665 | 1,312,569 |
| 20261029T182230Z_52851 | bernoulli / D16 | 12,674.273 | 6,182.519–6,489.904 | 1,312,569 |
| 20261029T182230Z_52852 | bursty / D8 | 12,705.253 | 6,095.056–6,608.655 | 1,312,570 |
| 20261029T182230Z_52853 | bernoulli / D16 | 12,826.211 | 6,093.804–6,589.692 | 1,313,003 |

單job均值6,332.058s、範圍6,093.804–6,608.655s；job wall總和35.1781h、五run wall相加17.6335h。
job-hours是既有並行環境各process wall的和，不是量測單獨執行或CPU-hours。
Main未量測，先以CGOF成本代理；historical build/cache條件與新工程可能不同。

| 階段 | jobs | pairs | job-hours均值 | jobs2線性wall h | simulation預算：線性×1.20 h |
| --- | ---: | ---: | ---: | ---: | ---: |
| pilot | 30 | 15 | 52.77 | 26.38 | 31.66 |
| confirmation | 600 | 300 | 1055.34 | 527.67 | 633.21 |
| total | 630 | 315 | 1108.11 | 554.06 | 664.87 |

完整630jobs線性範圍533.21–578.26h、均值554.06h，20%保留後664.87h。
20%是營運假設，不是量測上界或CI；Main/collector可能更慢，超支依既定規則停，不能改矩陣。
舊C4是Heavy5M、bursty90%/period100、40jobs、active約6.25M；runner合計27,539.636s，含等待campaign span30.72h、cap36h。
不是Heavy3.5M／80% ready／4.38Mcycles。工作量不同，不沿用36h上限。

### 7.1 完整工作預算

| 項目 | 規劃預算 | 硬上限／規則 |
| --- | --- | --- |
| Main接線、audit/分析與gates | 16–24h（工程8–16h＋驗證review8h） | 32h；未完成NOT_READY |
| Pilot7301 simulation | 26.38h線性，含保留31.66h | 34h，加audit2h／cap4h |
| 正式20seeds simulation | 527.67h線性，含保留633.21h | 每seed34h，全21seeds simulation累積cap680h |
| 21次seed audit | 工程估2h/seed，合計42h，未實測 | 4h/seed，包含full replay與人工release |
| 最終aggregate／完整性／報告 | 8h | 12h |
| Pilot起至最終交付 | **714.87h≈29.79天** | **810h＝33.75天**，含等待與中斷 |
| 加上前置工程 | **730.87–738.87h≈30.45–30.79天** | **842h≈35.08天** |

810h取21*(34h simulation+4h audit)+12h final，並同時受680h simulation cap限制。
campaign deadline在pilot開始時固定；目前未設定起訖日期，也未宣稱已預約主機或能持續運轉數週。
可以更正ETA，不能看pilot效果改seed/endpoint/margin/jobs/cap；預估超支則停止、另提修訂。
7401–7405記帳點含pilot180jobs：simulation線性158.30h、含保留189.96h；不是可提前驗收的替代主方案。

### 7.2 磁碟與記憶體

舊五run保留檔案約3.223MiB，按630/20外推約101.53MiB，**只指該些目錄保留的JSON/log/XML/ZIP記錄，不是總磁碟需求**。
WSL cache、新Main build、new ledger、audit scratch/trace與peak I/O未涵蓋；RSS未量測，不承諾<250MiB或不會爆滿。
repo與WSL cache所在volume各至少100GiB free；同volume不能把同一free space加兩次。
每seed開始／完成量測free/retained/scratch bytes與peak RSS。pilot量測後以剩餘工作投影加50%headroom，保留每volume20GiB floor；不夠即停，不刪歷史runs或他人cache。
禁止production VCD/FST全波形，只在短W工程gate診斷。並行度固定2，jobs4/6不在此協定，不承諾理想線性加速。

## 8. 未來產物與成功範圍

所有execution gates目前NOT_RUN。新namespace為artifacts/implementation/cgof-dynamic-confirmation-20261103/。
必留pre-campaign source/config/schema freeze、commands/exit、pilot、各seed raw/scopes/JUnit、source ZIP、streaming input digests、release、完整30job/15pair rows、primary deltas、bootstrap與Holm exact-test結果、failures/missing/cohort標記、resource records及manifest。
required-file缺檔fail-closed；wrapper argv不冒充完整外層命令，time/exit不得臆測。
有效完成標COMPLETE_VALID_EXECUTION，各P另判SUPPORTED_WITHIN_PROTOCOL或NOT_CONFIRMED；不自動把整個C7改CONFIRMED。
四窗state執行成功與普遍動態適應改善不同；所有新結果需另經report integration review。

## 9. Astra、Lead覆核與來源凍結

Orca Worker reviewer-2（requested auto/gemini-4-argon／high）整理初稿；依使用者既有偏好以Codex CLI單次呼叫codex/gpt-6-astra／high、read-only，exit0，thread 01a1a06d-07d7-7c21-8d9a-8160055293bc。
effective backend無可驗證欄位，標UNKNOWN。日誌保存在.setup-logs/implementation/dynamic-role-switch-rtl-plan-20261103/（ignored），詳見JSON provenance及source pins。
Astra明確表示只審閱提供條件與數字，未讀檔／執行工具；其prompt還含轉義造成的控制字元。故不算獨立raw-data核對。
Lead直接核讀scope/config/summary與code後，修正：ready80→90%、period/Sparse數、生成率解釋、不存在CLI、5seed確認／optional stopping、多終點檢定歧義、Main class選樣gate、事後截共同cohort、舊C4誤述、jobs6選項及未量測RSS／磁碟承諾。
初稿與Astra回覆原樣保留，不偽稱Astra核准了後續修改。

JSON frozen_source_index含 **112** 項實際path→SHA256，包含兩reviewer材料、初稿105項來源及必要實作來源。
C1綁da0a2fd16a40f2ee...，C2綁0f39a3c5e8342c44...，各自核對。
DEVELOPMENT_REPORT需追加本輪紀錄，所以pin其append前snapshot（ignored），不pin即將變動的工作檔。
MD不嵌JSON當前hash，JSON不hash自身；外部freeze receipt綁兩檔hash及source-index digest，避免循環。
這些是規劃基線hash，Main/audit日後實作會改部分source，須保留舊基線並另建execution freeze，不覆寫歷史pins。
