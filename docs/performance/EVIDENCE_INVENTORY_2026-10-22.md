# Descriptor performance：既有證據盤點

2026-10-22，owner已確定descriptor-only範圍；**Final報告不修改**。
Codex獨立讀取實作、原始metrics/summary/JUnit與hash記錄後分類，不把先前報告摘要直接當成新實驗。
主研究問題為共同synthesized switch boundary／受控流量下的服務行為與硬體成本。

## 可直接重用

| 證據 | 選定run ID | 範圍 | 可用資料／限制 |
| --- | --- | --- | --- |
| M3-primary | 20261020T165716Z_534 | FCFS/POLICY0，N4/8/16×seeds509..528，60runs | primary100k；吞吐、push、完整accepted-cohort wait、accepted-subset gen-delay、per-source counts、stall/fullFIFO counters |
| M4-primary | 20261020T170247Z_5075 | RR/POLICY1，quantum10，60runs | 同一trace版本／參數；20pairedseeds，不將RR1混入 |
| M5-primary | 20261020T172737Z_382 | Main/POLICY2，W5M，60runs | 同一trace；每cycleFCFS mirror；100k內allHigh、0closing，不代表適應性收益 |
| M5-stress | 20261020T170825Z_8460 | N4/8/16×W64/256×seeds509..513，30runs | W64 400ktracecycles、W256 800k；各run全部16state/evidence bins、class flip/held context等 |
| M5-production | 20261020T173518Z_3766 | N4/8/16，seed509，W5M，20M/run | 60M真實nonresetcycles／12windows；每組4closing records、B/S/held/fire/classes |
| M6-stress | 20261021T011237Z_23789 | Algorithm-2 N4×W64/256×5seeds，10runs | 6Mtracecycles；僅補充correctness／reconstruction，不進primarymatrix |
| M6-production | 20261021T011237Z_23785 | Algorithm-2 N4，seed509，W5M，20M | 四真實windows；不擴N8/16，不當三policyperformanceentry |
| Primary PPA v2 | docs/ppa/primary-20261021-v2.json | 完整9組共同method | Total switch含FIFO/必要metadata；SAED32RVT TT0.78V25C，25ns ForQA/top、compilemedium；140constant-disabledchecks保留 |
| Supplement PPA | docs/ppa/algorithm2-n4-20261021.json | Main/Algorithm-2同source N4pair | separate condition；小面積差不代表一般等價 |
| Power | docs/ppa/power-20261021.json、power-supplement-20261021.json | 原seed5099組、補18cold與3boundary | zero-delay/SAIF，coldX、table-rangewarnings；boundary50×classificationeventdensity，非productionaverage |
| Formality | docs/ppa/formality-20261021.json | 14specific RTL/netlistpairs+negativecontrol | 連接currentMain與primarynetlist；不是英文Specformalcorrectness |

實際執行 `python scripts/audit_descriptor_performance.py --output artifacts/performance/20261022-archive-audit` 通過：
180primaryjobs逐一確認summary與rawJUnit、零skips/errors/failures、compile/make/simulationexit0、完整矩陣、
同N/seed外生trace60組由現有generator重新產生並比對完整trace summary/hash。
44個選定longjobs同樣核對rawJUnit/status；production20M/四窗/S=sumB明確assert。
這是**archive audit，新增RTL cycles=0**。

Primary啟動時HEAD為b54aa64且帶comparator改動，不能僅寫「當時clean759f86b」。
保留的76filefunctional manifest中，選定RTL、共用run_trace、三policyprimarytests與trafficgenerator的hash
已逐一對乾淨759f86b的Git blob核對；後續Algorithm-2共用code改動由既有functional/bridge證據另述。
完整選定source檔清單見[archived audit](archived-audit.json)。

## 需補量測的缺口

| 欄位 | 舊primary是否可直接取得 | 作法 |
| --- | --- | --- |
| Whole-runrate/push/wait mean/P99/per-source share | 是 | 直接使用180舊紀錄；本次不為這些欄位無故重跑 |
| Intendedphase配置／ready/generation | 可重建且hash核對 | 只能當外生stimulus，不能推造policy實際phaseaccept/fire |
| Per-phase actual counters/cohort latency | 無原始per-phase觀測 | 共用run_trace加旁路量測，先N4seed509三policypilot；必要矩陣重放只補此缺口，舊結果保留 |
| Mean/max producer backlog與FIFO occupancy | 舊primary只有tailbacklog及fullFIFO cycles | 以pin事件推導accepted−deliveredoccupancy並明列pre/post-edge取樣；不能從fullcycles反推出meanoccupancy |
| Longest continuously-backlogged servicegap | 未獨立記錄 | 不把maxacceptedwait冒充starvationbound；若本次無新增該儀表，維持明列缺口 |
| IPC／application slowdown／完整CXLlinkutilization | 不在目前模型 | 本階段不補；gem5futurework、授權／版本盤點與N4pilot延後 |

新儀表不改stimulus、oracle、FIFO/hold或service契約。accepted-phase等待需納入draincompleted，
generation-phase延遲需同時列未接受cohort與截尾age，避免只看成功收進FIFO的短尾樣本。
所有新measurement均保留新runID，不覆寫accepted原資料。

## 不可直接比較／必須限定解讀

- Primary是100k、warmup0、initialreset3excluded、無measurementreset；Main不分類。
  Production20M是另外設計的0.55load流量，不能作為另一policy的primary對照。
- Stress有reset、drop、W64/256、hotspot/flip/idle/stall/saturate等phase；tracecycles與nonresetcycles不同。
  它建立指定boundarycorrectness，不是production穩態公平性／primarythroughput樣本。
- Production三個N各只有seed509，不能畫成20seedCI或聲稱所有16transition覆蓋。
  三組皆9bins：H/UP,H/KEEP,H/DOWN,B_H/UP,B_H/KEEP,B_H/DOWN,L/UP,L/KEEP,B_L/UP。
  未覆蓋H/S0,B_H/S0,L/DOWN,L/S0,B_L/DOWN,B_L/KEEP,B_L/S0；production held_cls_change=0。
  Mainstress30runs各16bins均有、涵蓋heldclasschange，但不是補造成production觀測。
- Algorithm-2/Main的pairedstress、N4same-methodsynthesis只支持該條件的觀察，不代表一般行為或PPA等價。
- 所有primary有producerunacceptedbacklog；generation-delay統計是acceptedsubset。
  drain後acceptedcohort全完成，不表示所有generatedwork完成；drainready1改變尾端等待條件，已明列。
- `full_cycles`是至少一FIFO滿的cycles，`all_full_cycles`是全部FIFO滿；兩者都不是積分occupancy。
- PPA v1/pilots保留失敗，不與v2拼表。Power不同workload/phasecut/seed，不能差分成classifierenergy。
- Raw equal-service-share不是unequaldemand下唯一公平目標。保留offeredshare與actualservice一起呈現。

## 失敗與不完整run

[完整歷史索引](archived-run_history.csv)保留選定scope下所有既有summary之runID、原status、testcount與hash。
RUNNING可能是已中斷後未完成的checkpoint，**不代表現在有job在跑**，也不標成PASS。
例如M5-primary20261020T172119Z_10354只有37tests，未採納；完整replacement382採納。
M3/M4初始失敗、M5stress測試邊界修復前失敗均留在索引，不刪除或用完成run覆寫。
舊PASS但未選的重複run是歷史重複證據，不加總成更多獨立樣本。

## 已重用的整體結果（不是新執行）

每格是20個seed的run-level arithmetic mean，P99欄是mean of20runP99，不是pool全部request後的P99。
完整SD／t19 95%meaninterval與paired differences見[summary](archived-seed_summary.csv)、
[paired deltas](archived-paired_differences.csv)。這些區間只描述此synthetictracefamily，不能推論applicationpopulation。

| N | Policy | Fires/cycle | Mean accept→fire (cycles) | Mean runP99 (cycles) |
| ---: | --- | ---: | ---: | ---: |
|4|FCFS|0.7267305|84.4717|447.10|
|4|RR10|0.7267305|84.1882|462.95|
|4|Main|0.7267305|84.4717|447.10|
|8|FCFS|0.7385690|164.7517|797.35|
|8|RR10|0.7385690|163.8238|845.40|
|8|Main|0.7385690|164.7517|797.35|
|16|FCFS|0.7322920|332.4395|1568.55|
|16|RR10|0.7322920|329.7100|1609.30|
|16|Main|0.7322920|332.4395|1568.55|

同N/seed下FCFS/Main的fires、accepted、mean/P99wait與boundarybacklog實際相同。
這符合allHighMain的FCFSmirror，不是adaptivefairness優勢。RR平均wait較低而runP99mean較高是本tracefamily觀察，
須連同phase、offeredload及producerdelay解讀，不泛化成所有負載的latency排序。

## 工作範圍及權限

Owner確認project-ownedtraffic；此處不使用SPEC或未確認外部workload。FastX的允許結論僅為：
「目前帳號可見環境未確認 SPEC 安裝或使用授權。」本次沒有新的SSH查核或全校授權判定。
本階段不做gem5integration、traceextraction或閉迴路實驗。Final六頁body條件保留為下次寫作限制。

本次native Claude Code2.1.306/plugin0.14.6已查驗並實際呼叫focusedworkflow，requestedOpus5.5/medium。
session6f0f88a0-fc44-44b5-b154-cf1ceab97f0a在agent產生工作前weekly429／CLIexit1，無nativeimplementationPASS。
依owner既有授權改GPT6.1Sol/high補儀表/pilot；Codex獨立審查。原prompt/settings/stream/stderr/exit與dirtysnapshot保留在
`.setup-logs/implementation/descriptor-perf-20261022/`。

後續缺口補測已完成並另行審查：三N4pilots與180/180fullprimaryPASS，新增18.3M measuredRTLcycles。
新phase/cohort/backlog/occupancy觀測、原欄位逐項一致與保留檔案hash檢查見
[新測試紀錄](TEST_RECORD_2026-10-22.md)、[replay audit](phase-audit.json)。
上方「需補」表指原始archive缺欄位；本次已補phase/state觀測，獨立backloggedservicegap仍未量測。
