# 證據審查後續：Arrival Phase、Ordering 與 Buffer Screening

日期：2026-11-01。狀態：bounded screening，不是 confirmation。

## 證據範圍

| 類型 | 本次執行 | 可支持 | 不可支持 |
| --- | --- | --- | --- |
| Arrival phase | `MODEL_ONLY`，W256，exploration seeds 6101–6105，profiles under/near/over，phases 0/128/256/384，兩種 CGOF oldest-first 配額 | 修正後共同 generation horizon、ready drain、完整 cohort 與 lag 的可執行性；此 bounded workload 的方向 | 20-seed confirmation、W5M production、統計等價、CXL response 或 application benefit |
| Ordering smoke | `SCHEDULER_RTL`，W256，seed 6201，1:1／2:1 × oldest-first／eligible-RR | ordering 已完整接到 build、testbench、job、result identity；四種設定可獨立通過 | 多 seed 排序優劣、PPA、一般 workload 的 universal winner |
| Ordering correction exploration | `SCHEDULER_RTL`，W256，fresh seeds 6401–6405，near/bursty，Heavy work 256，40 jobs／20 pairs | 固定 effective High 下，這五個 seed 的 quota × ordering 原始端點與配對差值 | confirmation、一般排序或優勢、W5M、PPA、CXL／application 結果 |
| Buffer transition | `MODEL_ONLY`，固定共同 B/S counts，W256 與 W64 各 78 replay，無隨機 seeds | phase、持續時間與 transition／effective mapping 的機制檢查；實際 stable suffix 與觀測不足的區分 | closed-loop queueing／latency recovery、RTL、統計確認或一般 Buffer 效益 |
| Buffer closed-loop | `MODEL_ONLY`，W256，exploration seeds 6101–6105，CGOF2 與 CGOF1 各含 live／1W／all-High frozen | 共同 arrivals／ready 下的 service→class→service 回饋、generation-role latency、CGOF1 classifier leakage 負控制 | latency recovery、分類器排序或一般延遲優勢、production W5M、RTL／CXL／application 結果 |

原始證據：

- Arrival summary：`artifacts/implementation/evidence-review-arrival-20261101T072532Z/summary.json`
- Arrival manifest SHA-256：`ce48722a47d44a7a386bc33c733da13bcc45b1da3d9e69a799cb7d1cfdc15a94`
- Arrival summary SHA-256：`54d292cf31837f4d5c7ed5edb8f37900e828c27de8b22ab69248201d755174c6`
- RTL scope：`artifacts/implementation/cgof-rtl-diagnosis/20261031T232608Z_1153/diagnosis_scope.json`
- RTL run：4 lint configurations、5 traffic pytest、8 cocotb jobs、source stable PASS

## Arrival Phase

共 120 個 phase/profile/seed/policy pairs，全部 status `PASS`，完整 Heavy arrivals、ready sequence 與 Sparse work multiset 配對成立。每個 config/profile 有 20 個 observations，即 5 seeds × 4 phases。

| Config | Profile | Passing | Mean terminal Heavy delta (cycles) | Mean time ratio | Mean max lag (descriptors) | Recovered | Equivalence margin |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CGOF 1:1 oldest | under | 20/20 | 0.00 | 1.000000 | 1.25 | 20/20 | 20/20 |
| CGOF 1:1 oldest | near | 20/20 | 0.00 | 1.000000 | 5.00 | 20/20 | 20/20 |
| CGOF 1:1 oldest | over | 20/20 | 85.20 | 1.150000 | 75.60 | 20/20 | 0/20 |
| CGOF 2:1 oldest | under | 20/20 | 0.00 | 1.000000 | 1.25 | 20/20 | 20/20 |
| CGOF 2:1 oldest | near | 20/20 | 0.00 | 1.000000 | 4.95 | 20/20 | 20/20 |
| CGOF 2:1 oldest | over | 20/20 | 85.20 | 1.150000 | 75.60 | 20/20 | 0/20 |

四個 phase 對 terminal Heavy delta 的 aggregate 都是 28.40 cycles；這個數字混合 under/near/over 與兩種配額，不應解讀成 phase effect。真正的 profile 分解是 under/near 為零差、over 才有顯著完成代價。

最窄可保留主張：

> 在這組 W256 finite-work screening 中，Sparse arrival phase 沒有改變 under/near 的最終 Heavy 完成差；near 仍出現平均最大 5 個 descriptor 的暫時落後，且都在 observation 內追回。Over 則出現約 85 cycles 的完成代價。

這支持「終點差為零不代表過程完全沒有干擾」，但不支持「所有 phase 統計等價」。五個 exploration seeds 與 W256 不構成 confirmation。

## Ordering RTL

四種設定都通過 lint 與 cocotb；mixed/isolated 的 Heavy work 均完成，結果 identity 不再碰撞。

| High:Low | Ordering | Mixed active cycles | Isolated active cycles | Active-cycle ratio | Mixed Sparse G→F P99 | Mixed Heavy max gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1:1 | oldest-first | 331 | 325 | 1.02 | 4 | 7 |
| 1:1 | eligible-RR | 331 | 325 | 1.02 | 4 | 7 |
| 2:1 | oldest-first | 331 | 325 | 1.02 | 5 | 5 |
| 2:1 | eligible-RR | 331 | 325 | 1.02 | 4 | 6 |

這是單一 seed 的機制 smoke，不是 ordering benchmark。1:1 在此案例沒有可辨識差異；2:1 顯示 Sparse P99 與 Heavy gap 的方向相反，不能宣稱任一種 ordering 普遍較好。

## Buffer Transition：2026-11-01 新增

此為 P0–P4 之後的獨立 screening；原修正計畫快照與來源 hash 不改寫。GPT6Astra 的指定入口 `gpt-6-astra/high` 負責驗收計畫與獨立複審，`auto/deepseek-v4.1-flash` 負責測試，監督者實作 runner、修正邊界與測試 oracle、獨立執行並保存證據。這些是實際 spawn 參數；工具未回傳後端 effective model，manifest 明示 UNKNOWN，不把 routing 名稱當後端驗證。

重用既有 `threshold_evidence`、三種 transition tables 及各自 effective mapping，未修改 shared model 或 RTL。每 cycle 一筆外生 service，以明列 period16 slots 產生四來源 B/S；source0 sparse/heavy 的完整窗分別為 `[16,80,80,80]`／`[208,16,16,16]`（W256）。這是 synthetic service-role evidence，沒有模擬 arrival、FIFO 或 service→class→service 回饋。

主矩陣：三個 baseline warmup windows、phase `0/W4/W-1`、兩個方向、noise `W/2/W/3W/2` 與 persistent `>=4W`，共 24 個共同輸入。另加 DOWN→KEEP、DOWN→S0 兩個控制，三 variants 共 78 replay／W。W256 與 W64 各有 `20 COMPLETE / 58 INCOMPLETE`，全部 replay 與 B/S input pairing PASS。`INCOMPLETE` 表示該 case 至少一個角色區間內未達並保留目標 stable state 至少 W；合法的 noise filtering 也會產生此狀態，不視為執行失敗。

W256 persistent 的 source0 時間，均為相對於角色變更的 cycles：

| Direction | Phase | Main effective／stable delay | Main-1W effective／stable delay | FAI-ImmBuf (`Algorithm-2`) effective／stable delay |
| --- | ---: | ---: | ---: | ---: |
| sparse→heavy | 0 | 512／512 | 256／256 | 256／512 |
| sparse→heavy | 64 | 448／448 | 192／192 | 192／448 |
| sparse→heavy | 255 | 513／513 | 257／257 | 257／513 |
| heavy→sparse | 0 | 512／512 | 256／256 | 256／512 |
| heavy→sparse | 64 | 704／704 | 448／448 | 448／704 |
| heavy→sparse | 255 | 513／513 | 257／257 | 257／513 |

這些 18 條 persistent replay 全有至少 W 的實際 post-settle 觀測。phase64 的方向差來自混合窗 B/S 的 UP/DOWN 閾值，不能預填為支持性 evidence；phase255 的變更 cycle1023 所屬窗仍可能保留舊 evidence。兩次支持性 close 不代表任意相位下固定 2W 的角色反應。

在 phase0、長 W 的 sparse→heavy→sparse noise 中，Main 的 source0 effective flips 為 0，Main-1W／FAI-ImmBuf（`Algorithm-2`）各 2。KEEP／S0 控制則確認 FAI-ImmBuf 可以一直 effective Low、一直停在 Buffer 而沒有 stable Low。這些只辨識分類規則，不能從 flips 較少推論等待較低。

觀測契約：close=`(i+1)W-1`、visible=`close+1`；event 為 `[role_change,next_change)`，最後一個 event 截於實際 `T=len(counts)*W`。visible=T 的終點 snapshot 只記零觀測 timing，`*_observed=false`，不增加一個 W，也不抹除 `[0,T)` 已觀測到的 stable suffix。`latency_recovery` 全為 `NOT_MEASURED`。

驗證：既有三種模型 163 tests 加新 Buffer 17 tests，合計 **180 passed、115 subtests passed**；WSL Python3.12.3／pytest9.1.1。W256／W64 CLI self-check、完整 counts hash 與 current／archived source hashes 核對均 PASS。首次測試整合的錯誤、修正與實際 delegated provenance 保留於新 manifest；較廣回歸先前的 14 個 power-vector errors 不因本輪 PASS 而消失，本輪未重跑全域回歸。

證據：

- 驗收計畫：`docs/reviews/buffer-transition-acceptance-20261101.md`
- 原始輸出、source snapshot、測試 log 與 manifest：`artifacts/implementation/buffer-transition-screen/20261031T234344Z/`
- Manifest raw-file SHA256：`66bb7863873e584ddca31b9c2882c46a30b041c1a6759fe3e359f4399e86441d`
- W256 output raw-file SHA256：`7cccbb640a972b04fabe5426373d2a50fc5fe43c03f34002fd1047caf2d909b2`
- W64 output raw-file SHA256：`26c503b476633e8b1a72cf2d823cf581442607fc2f68c967add51635fa9b6a99`

重跑時另選新 output；runner 以 exclusive create 拒絕覆寫：

```bash
source scripts/wsl_env.sh
python -B -m pytest -q scripts/test_run_buffer_transition_screen.py \
  refc/tests/test_fai_main_model.py refc/tests/test_fai_alg2_model.py \
  sim/experimental/test_baseline_models.py
python -B scripts/run_buffer_transition_screen.py --window 256 \
  --self-check --output <new-directory>/screen-w256.json
```

## Buffer Closed-loop：2026-11-01 新增

本階段依 `docs/reviews/buffer-closed-loop-plan-20261101.md` 建立獨立
`scripts/run_buffer_closed_loop.py` 與測試，不 import transition-only runner，
也不把共同外生 B/S replay 當成本輪結果。`ExperimentalSwitchModel` 僅新增
optional `classifier="live"`；live／1W 分別重用已接受的 Main／Main-1W
tables，frozen 從 reset 到 drain 每 cycle 斷言 all H。FIFO、hold、credit
refill、oldest-first selector 與既有 default callers 的行為沿用原模型。

規劃 agent 本輪指定 GPT6Astra(high)，spawn 回報 `Unknown model`；依
owner-approved fallback 使用 `group/gpt-6.1-sol`、high，agent
`01a1949c-5d71-70d1-b0d9-cd5aa5829868` 撰寫計畫並唯讀複審。
`auto/deepseek-v4.1-flash`、agent
`01a1949e-95ff-7a72-84c6-5778ad14fdb8` 交付測試；監督者完成 runner、
修正並補強反例測試、執行與封存。這些是請求／routing identity，
backend effective model 仍為 `UNKNOWN`，不宣稱本輪成功啟動 Astra。

固定 N4/D16、single output、W256，over offered-load fixture：
熱來源每 cycle 一筆，其餘各 p=.05，ready p=.9。`down` 是 R0→R3，
`up` 是 R3→R0，兩者是實體熱來源的角色排序；正式 event 都觀察
**新熱來源的 Low target**，不是以 direction 字面推定 High/Low。
3W baseline 後在 `r=3W+phase` 切換，phase 為 0/64/255；noise
duration 為 128/256/384，return tail 為 4W；persistent horizon
為 r+4W。baseline 僅作 `CONTEXT_ONLY`。

生成 horizon 與 max drain=4W 對六個 variants 相同。Drain 不生成新
request、不 reset、沿用同一 ready trace。生成時固定 R0／R3／
R0_return（反向為 R3／R0／R3_return）與 hot/sparse 屬性，
不依 fire 時角色重標。全 run、每 role、每 source 保存 G→A／A→F／
G→F nearest-rank distributions、active/drain completion、producer
backlog、FIFO occupancy、right-censor；空 latency count=0，其餘
統計為 null。Gap 重用 `followup.Gaps`，wall 與 eligible-ready 分開，
角色與 drain 邊界保留 censoring。

W64／W256 各 12-run self-check、seed6101 的 W256 144-run smoke
與下列 exploration 全部執行成功。Smoke 使用的 seed6101 也是
exploration 成員，不能加總為第六個獨立 seed。

| Exploration seed | Scenarios | Variants | COMPLETE events | INCOMPLETE events | 最大實際 drain cycles |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6101 | 24 | 144 | 96 | 156 | 714 |
| 6102 | 24 | 144 | 96 | 156 | 661 |
| 6103 | 24 | 144 | 96 | 156 | 699 |
| 6104 | 24 | 144 | 96 | 156 | 726 |
| 6105 | 24 | 144 | 96 | 156 | 661 |
| Total | 120 | 720 | 480 | 780 | 726 |

所有 120 組六 variants 的 arrivals／descriptors／ready／role schedule／
horizon hash 配對 PASS。CGOF1 三 modes 的完整 action hash、counts、
latency、gaps、FIFO/backlog metrics 在 120/120 組完全一致；這是
classifier leakage 負控制。CGOF2 在 120/120 組有至少一個 mode 的
action trace 不同，只記為 descriptive difference，未進行 ranking、
CI 或 p-value。跨六 variants 合計 generated=fired=1,735,614，
final censored=0；這是重複共同 workload 的總量，不是獨立 request
replicates。共有 289,269 個獨特情境內的共同生成事件；五個 seeds
仍是唯一 exploration seed 數。

`COMPLETE` event 僅表示新熱來源有至少 W 個真正的 post-settle
observed cycles。780 個 INCOMPLETE 包含 live 未到 target 180、
1W 未到 target 80／post-settle 不足 W 100，以及 frozen 未到 Low
420；固定 all-High 的 frozen 本來就不適應 Low target。
它們不是 runner failures。全 720 runs 的 drain 都在 4W 內清空；
刻意將 ready 全設為 0 的反例另驗證保留 backlog、null 未完成
latency 與 `RIGHT_CENSORED_AT_DRAIN_BUDGET`。

CGOF2 persistent 的 30 個 hot-source events，每 mode 的 live／1W
均為 30 COMPLETE；stable delay 範圍分別為 448–513／192–257
cycles，frozen 皆未達 Low。這是本輪 workload 的 classifier timing。
例如 seed6101、phase0、R0→R3 persistent，僅列 R3 generation cohort：

| CGOF2 classifier | Hot-source stable delay | R3 hot G→F P99 | R3 sparse G→F P99 |
| --- | ---: | ---: | ---: |
| live | 512 | 529 | 657 |
| 1W | 256 | 529 | 574 |
| frozen | null | 529 | 496 |

這個已明列的單一 fixture 顯示 class timing 與 cohort waiting 是不同
觀測量；不構成 frozen 較佳適應或任一 mode 的一般排序。
全輸出皆明列 `latency_recovery="NOT_DEFINED_THIS_ROUND"`。
close 與 close+1 visible 分欄，event 是半開區間；終點 visible=T
僅記零觀測，不借用 drain 或下一角色時間。Stable timing 取最後
可維持至 event end 的 suffix，不取最早命中。

最終 WSL Python3.12.3／pytest9.1.1 回歸：
**245 passed、224 subtests passed in23.73s**，exit0，涵蓋新 closed-loop
23 tests、experimental／diagnosis 42 tests 與先前 transition／Main／
Alg2／baseline 180 tests。新增反例包含 16 個 Main-1W table entries、
每 cycle frozen、跨角色 cohort、no-demand null、ready=0 drain、
最後 close／suffix reset／zero-flips，以及 descriptor／ready／horizon
mismatch、source drift、CGOF1 class leakage 與 exclusive output。

初次整合的 collection/import failure、histogram integer-key 導致
JSON round-trip hash 改變、測試遞迴把 histogram key 當字串等錯誤，
已修正並保留 logs；canonical histogram serialization 重用
`diagnosis.jsonable`。此 PASS 不涵蓋先前較廣回歸的 14 個
power-vector errors。

Sol/high reviewer 另以 W64 probes 核對 terminal／最後 suffix、共同
ready drain、跨角色歸屬、descriptor pin hash、CGOF1 equality 與
persistent phases。最初把新熱來源誤解為 High target，以及未看到獨立
manifest capture 的兩項疑慮，經查明契約與 artifact 後均撤回；
reviewed scope 無剩餘 material finding。Reviewer 未重跑 W256 長矩陣，
該矩陣與封存後逐項驗證由監督者執行；複審與裁定另存同目錄
`acceptance.json`。

證據均在新目錄：

- 計畫：`docs/reviews/buffer-closed-loop-plan-20261101.md`，原始 SHA256
  `3b9cf6364a6479388ba49e3c5b6dc6c3eb4f12ef7a7a09ce1e3c83fce04860fe`。
- 執行／來源／命令／stdout／stderr／before-after hash：
  `artifacts/implementation/buffer-closed-loop/20261101T015630Z/manifest.json`，
  raw SHA256 `d95bcdd4a38adddaa44a53be39fad3fc8d21007d63d0251d98d7c84bfd3a984a`。
- Exploration：同目錄 `exploration-6101-6105.json`，raw SHA256
  `f9a769b87e77334c9e4b5e03e5f7e16d2d07807460153392bd9b5e60095f53b4`。
- Smoke：同目錄 `smoke-6101.json`，raw SHA256
  `cbc0818f2179dd77fce0b3ecb7f5edf7b8e9c9060ed78911a18188a88c0a749c`。

最小重跑命令如下；output 必須另選新路徑，runner 拒絕覆寫：

```bash
source scripts/wsl_env.sh
python -B -m pytest -q scripts/test_run_buffer_closed_loop.py \
  refc/tests/test_experimental.py refc/tests/test_diagnosis.py
python -B scripts/run_buffer_closed_loop.py --window 256 --seeds 6101-6105 \
  --output <new-directory>/exploration-6101-6105.json
```

## Ordering RTL：五個 fresh seeds 的修正版 exploration

本輪為 `SCHEDULER_RTL` bounded five-seed exploration。原計畫
`ordering-rtl-exploration-plan-20261101.md` 使用 Heavy work 1024；
seed6301 的 `20261101T024757Z_2732` 雖有 13/13 execution steps
PASS，但 close255 為 B_H、close511 已為 L，固定 effective High
前提 `NOT_HELD`。已停止 6302–6305，保留原計畫與完整失敗設計
證據，不把 6301 endpoints 納入新分析。

其後凍結獨立 correction plan
`docs/reviews/ordering-rtl-exploration-correction-20261101.md`，
SHA256 `955ac86ae7cc6785f298ceaf58a78027eedf8e89034e9476969ffaeabc18a7d6`。
固定 N4/D16/W256、near（Heavy p=.8、Sparse 各 p=.02）、
ready p=.9 的 bursty period100、Heavy work256、source0，
四設定 Q1-OF／Q1-RR／Q2-OF／Q2-RR 各有 mixed／isolated。
每個 seed 執行後先驗 manipulation，再執行下一個 seed。

規劃／複審仍指定 GPT6Astra(high)，spawn 回報 `Unknown model`，
使用 owner-approved `group/gpt-6.1-sol`、high fallback，agent
`01a194fd-9121-76b3-842c-50384ba7dd6a`。執行為
`auto/deepseek-v4.1-flash`，agent
`01a19500-b3d5-79c3-a045-d0879c4683a0`；監督者獨立重播輸入、
檢查 artifacts、建立分析與驗收。Backend effective model 均記
`UNKNOWN`，不把請求／routing label 當後端識別證據。

| Seed | Run ID | Jobs／pairs | Active cycles 範圍 | Manipulation |
| --- | --- | --- | ---: | --- |
| 6401 | `20261101T025305Z_3219` | 8／4 PASS | 326–328 | HELD |
| 6402 | `20261101T025436Z_7803` | 8／4 PASS | 330–332 | HELD |
| 6403 | `20261101T025606Z_12313` | 8／4 PASS | 328–332 | HELD |
| 6404 | `20261101T025739Z_16918` | 8／4 PASS | 331–336 | HELD |
| 6405 | `20261101T025918Z_21788` | 8／4 PASS | 326–331 | HELD |

合計 20 lint configurations、25 traffic pytest tests 與40 cocotb
jobs 全過，沒有 failure/error/skip。前置較廣 targeted regression
82 passed／40 subtests；correction 前另有35 passed／6 subtests。
這些包含重複的 traffic tests，不能加總為獨特 RTL coverage。
每個 job 只有 window0 的 active close255，old/new states 僅 H/B_H，
close 在 active end 以前且 active<512。全部 Heavy generated=fired
256。31 個 source files 的 before/after、五個 ZIP 與 audit-time
現檔逐一相符；Git HEAD 為99400ded…2689，dirty worktree 保留。

監督者另核對40個 raw JSON 與 scope 內資料、job/params/ELIGIBLE_RR
identity、45份 JUnit（40 RTL＋5 traffic scopes），並從每份
`trace_config` 重建完整 active arrivals/descriptors/ready，重算
`trace_sha256` 全部相符。20組 mixed/isolated configs 除
`include_sparse` 外一致，Heavy+ready 在 min(active cycles) 的
`reconstructed_declared_prefix_sha256` 全部相同。另有40個
setting-contrast共同 prefix 核對。這是重建輸入與完整 trace hash
交叉核對；沒有宣稱 artifacts 保存了分離的 observed Heavy-prefix hash。

跨40 jobs generated=accepted=fired=10,672；這是不同設定的重播總量，
不是10,672個獨立 seed replicates。五個 mixed jobs 在 active cut
各有一筆 Sparse 未完成，皆在1 cycle drain完成：6402 Q2-OF與6404
四設定。最終 right-censor=0。Sparse G→F採 **full-run completed
generation cohort，包含 drain completion**；active-cut pending、
drain completed 與 final censor 分欄，不能把 pending 當零延遲或
最終遺失。Heavy gaps僅含 active backlog episodes，initial、
inter-service、empty-terminated及censored類別分開。
本RTL harness的drain沿用既有`ready=1`契約；bursty ready只適用
active interval，不把drain結果推廣為持續bursty readiness下的結果。

下表每格為 mixed lane 的「Sparse G→F P99／Heavy max wall gap」，
單位均為cycles，採原始nearest-rank統計：

| Seed | Q1-OF | Q1-RR | Q2-OF | Q2-RR |
| --- | ---: | ---: | ---: | ---: |
| 6401 | 11／11 | 11／11 | 11／11 | 11／11 |
| 6402 | 11／12 | 11／12 | 12／11 | 11／12 |
| 6403 | 7／12 | 7／12 | 8／13 | 7／12 |
| 6404 | 11／11 | 11／11 | 12／11 | 11／11 |
| 6405 | 12／13 | 12／13 | 13／14 | 12／13 |

五seed各mixed lane的Sparse完成數為23/22/18/28/17；這些小cohort
的nearest-rank P99等於該run樣本最大值，不能解讀成已穩健估計尾部分布。

Q2-OF→Q2-RR 的 candidate−reference 差值如下；ready gap單位為
eligible ready opportunities，其餘為cycles：

| Seed | Sparse P99 Δ | Heavy max wall Δ | Heavy wall P99 Δ | Heavy ready P99 Δ |
| --- | ---: | ---: | ---: | ---: |
| 6401 | 0 | 0 | -1 | -1 |
| 6402 | -1 | +1 | -1 | 0 |
| 6403 | -1 | -1 | 0 | 0 |
| 6404 | -1 | 0 | 0 | 0 |
| 6405 | -1 | -1 | 0 | 0 |

Q1 ordering 的四個端點在五個 seeds皆相同；isolated各設定的端點
與active cycles在同seed內也相同。這些是已輸出端點的相同，
不宣稱保留了完整action trace等價證明。Q2在四個seeds的Sparse
P99差1cycle，但Heavy max方向有正有負，不能宣布一般winner。
全部40個setting contrasts與20個pair-ratio contrasts均保存原值、
candidate、reference及delta；不作score、rank、CI或p-value。
Active-cycle ratio的範圍為1.003030303–1.015337423，不是byte、
bandwidth或throughput ratio。不同設定以各自Heavy完成停止Sparse
生成，prefix matched不代表一般情況下完整Sparse cohort必定相同。

外層wrapper有兩次不同的啟動失敗：原6301的quoting錯誤，以及
corrected6401的function變數傳遞使`--seed`為空；都在建立run之前
停止。改以明確參數呼叫後，五個fresh seeds依序成功，沒有替換
失敗seed或重跑已產生結果的seed。原始preflight、wrapper error、
runner與checker命令/輸出/exit已從executor transcript的
CommandExecution records選出封存；沒有單一aggregate shell process，
不宣稱存在單一campaign OS exit code。

新campaign證據均在
`artifacts/implementation/cgof-rtl-ordering-exploration/`：

- Manifest：`correction-manifest-20261101T030414Z.json`，SHA256
  `4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b`。
- Analysis：`correction-analysis-20261101T030414Z.json`，SHA256
  `76da0716572feea212b57a39cd8b382aabc7eb9f46205cc694ff44aff07a5fe8`。
- Pair audit：`correction-pair-audit-20261101T030414Z.json`，SHA256
  `c5fe80a1cdb5d7a13dcad4b3213da23be672f70e8093621c6e99828161a0dc76`。
- Command records：`correction-command-records-20261101T030735Z.json`，
  SHA256 `2f8d60bfb8642cf7c62d5ff058fcdc9e3334f2f5a6251dab07bd178b10919793`。
- `correction-audit-source-20261101T030414Z.py` 與獨立audit log、
  82-test前置log均封存；所有輸出以exclusive create拒絕覆寫。

Runner summary的`scope="full"`只表示其所有指定steps有執行；
`diagnosis_scope.smoke=true`及本輪frozen plan共同界定bounded
W256 exploration，不能把runner scope解讀為production或confirmation。
未修改RTL、model、spec、主論文或歷史artifacts；僅新增審核證據及
更新本輪開發／狀態文件。

Sol/high reviewer另獨立核對全部40個trace hash、20pairs、40setting
contrasts、20pair-ratio contrasts、五個source ZIP與180份run files，
未發現阻擋本輪bounded驗收的material finding。初審六項問題
（runner scope、drain cohort、重建prefix標籤、active close關係、
latest pointer與跨seed identity）均在新audit處理。原manipulation
失敗與外層command失敗未改寫為PASS。驗收及複審裁定：
`artifacts/implementation/cgof-rtl-ordering-exploration/correction-acceptance-20261101T030414Z.json`。

## H2 ordering：預先登記的二十 seed RTL confirmation

依owner補充，Astra改由 **Codex CLI** 呼叫成功：requested catalog slug
`codex/gpt-6-astra`、reasoning `high`。先前subagent-spawn的
`Unknown model`屬不同呼叫路徑，不能代表CLI結果。Planner及executor
的backend effective model均為`UNKNOWN`，不以routing名稱推定實際模型。
Codex擔任監督與審核，`auto/deepseek-v4.1-flash`負責逐seed執行。

凍結計畫：`ordering-rtl-confirmation-plan-20261101.md`，SHA256
`e68ab2ef3506029e2b719d6d80eadec3dcf6277debe1b13a5a674309f28c93ec`。
該檔的`EXECUTION_NOT_RUN`保留planning snapshot語意；實際完成狀態
記在本節及新manifest，不回寫預先計畫。N4/D16/W256、near、
Heavy work256/source0、bursty active ready=.9/period100、四設定
Q1-OF/Q1-RR/Q2-OF/Q2-RR × mixed/isolated固定不變。獨立分析單位
是包含八jobs的seed block；fresh seeds6501–6520不與6401–6405
探索樣本合併，也未換seed、追加樣本或因結果提早停止。

執行共20/20seeds、160/160RTL jobs、80/80pairs、
80/80lint configurations、20traffic invocations/100cases；
180份JUnit無failure/error/skipped。每seed為13/13steps PASS。
Preflight另為35passed、6subtests，不重複計為額外RTL coverage。
31source files在before/after、20份source ZIP及audit-time一致，
source manifest SHA256為
`3fc28d71a390e25d1bfe831d504d5a037303fc89591a56d9088f0bab1aca9692`。
全部jobs只有active/window0/close255且有效High；active317–339
cycles。160完整input trace重播、80mixed/isolated Heavy+ready
prefix及160setting prefixes核對通過。完整Sparse arrival lists
在同seed四個mixed設定間20/20一致，並非僅count或prefix相同。

Generated=accepted=fired=42,620，final request censoring=0。
本批Sparse active-cut pending=0、drain completed=0，160jobs
都未需要drain。量測仍採full-run completed generation cohort，
包含既有ready=1 cleanup契約，不改為active-only或持續bursty
drain的counterfactual。每run Sparse cohort僅12–32requests，
nearest-rank P99等於該run樣本最大值，不能解讀成stationary tail。
Heavy gap仍分initial/inter-service/empty-terminated/censored種類，
主端點只取active accepted-minus-fired inter-service episodes。

主要定義保持凍結：`d1=Q1-RR−Q1-OF`、
`d2=Q2-RR−Q2-OF`、`I=d2−d1`，端點為mixed Sparse G→F P99。

| 主要contrast | 負／零／正 seeds | Mean | Median | Range |
| --- | ---: | ---: | ---: | ---: |
| d1 | 0／20／0 | 0 | 0 | 0 |
| d2 | 7／13／0 | -0.35 | 0 | -1–0 |
| I | 7／13／0 | -0.35 | 0 | -1–0 |

Strict joint improvements發生於6503、6504、6505、6508、6509、
6510、6516，其餘13seeds為tie。所有execution/manipulation/
estimand gates通過且無primary reversal，但只有 **7/20** 同時滿足
`d2<=-1 && I<=-1`，低於事前要求 **15/20**，因此主要裁定為
**`NOT_CONFIRMED`**。不能改稱沒有effect、equivalence或OF優勝，
也不能用有利的secondary endpoint取代主要判定。

完整analysis保存160job rows、80lane pairs、160setting contrasts、
80completion contrasts、20primary rows，以及各lane次要interaction、
A=mixed−isolated active cycles及R=mixed/isolated ratio對照。
每個可用summary都有20個seed；isolated Sparse明列null/N/A。
Q1兩ordering的五個輸出端點在兩lane共40個比較皆相同；isolated
四設定相對Q1-OF共60個比較皆相同。這只表示端點相同，不是完整
action-trace等價證明或equivalence test。

Q2-RR−Q2-OF的mixed Heavy max/wall-P99/ready-P99均值分別為
-0.10/-0.15/-0.10；前兩者單位cycles，最後是eligible ready
opportunities。三者在2/3/2seeds各減1，其餘為tie。所有A/R的
ordering/quota contrasts及interaction皆為零；每setting的A仍為
0–6cycles、R為1–1.01875，不是bandwidth或byte ratio。
所有四組contrast、interaction與逐seed原值均保存，無score、
ranking、CI、p-value或一般winner宣稱。

審核過程保留四次attempt：第一次把wrapper `config.argv=[seed]`
誤當完整runner argv而拒絕；修正後第二次通過。第三次修正次要
彙總須同時按factor/lane/reference/candidate分組；第四次補齊
原計畫已要求的次要interaction、完成時間對照及端點相同檢查。
這些只讀重算未重跑實驗；四次log與較早衍生檔皆保留。主要rows、
規則及`NOT_CONFIRMED`結論不變。完整命令由凍結計畫、
seed-wrapper command records、scope/config及runner logs交叉核對。
各seed各自exit0；不創造不存在的單一campaign OS exit code。

本輪canonical證據位於
`artifacts/implementation/cgof-rtl-ordering-confirmation/`：

- Manifest：`manifest-20261101T045246Z.json`，SHA256
  `5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384`。
- Analysis：`analysis-20261101T045246Z.json`，SHA256
  `101b1c1c8ee4327b99104af267761c98f17182205f4154e7e2f7825bf2e0c954`。
- Pair audit：`pair-input-audit-20261101T045246Z.json`，SHA256
  `1e479cfcca502b7167375b1a36e27a374fecdd73388b830de2f3ec4f50cc8426`。
- Commands：`command-records-20261101T044617Z.json`，SHA256
  `e78f4fdfc5a14be1eed4b241025dc0f6f1024e4c3013232bd17d8f7f4771eb87`。
- `audit-source-20261101T045246Z.py`、Astra CLI planning logs與
  audit logs封存；`acceptance-20261101T045246Z.json`綁定上述
  雜湊及四份開發／狀態文件before/after，所有新輸出拒絕覆寫。

本輪為bounded `SCHEDULER_RTL` confirmation。Execution PASS與
主要claim `NOT_CONFIRMED`分開，不把runner `scope="full"`升格為
W5M/production signoff。未修改RTL、model、spec、主論文或舊證據；
既有14個power-vector errors仍未解決，不屬於本輪PASS。

## 本輪後仍未執行

- W5M production arrival matrix 與其20-seed confirmation；本輪W256結果不替代它。
- 本ordering follow-up的新formal/CDC、PPA、EDA signoff。
- Buffer latency recovery threshold 與其獨立驗證、新 Buffer RTL。
- CXL completed bandwidth、issue-to-response latency、application slowdown。
