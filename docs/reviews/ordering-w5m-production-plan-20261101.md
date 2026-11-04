# Ordering W5M production pilot 與五 seed 描述性探索計畫

日期：2026-11-01。版本：`ordering_w5m_production_v1`。
狀態：`PLAN_ONLY / EXECUTION_NOT_RUN`。本次只新增本計畫；以下命令均未執行。
Supervisor 在派工前封存本檔 SHA-256，之後不得按結果改寫計畫。

## 1. 任務、權限與 provenance

在既有 repository、現有 RTL/model/TB/runner 上，執行真正的
`W=5,000,000`、N4/D16、有限 Heavy 工作量之 quota × ordering 比較。
先只派 seed **6601** 的 production pilot；完整驗收後才依序派
**6602、6603、6604、6605**，每 seed 都先驗收才放行下一個。
每 seed 恰為 8 jobs、4 mixed/isolated pairs。

本計畫者唯讀檢查本機文件、source、歷史 aggregate 與 summaries，沒有
啟動 simulation、pytest、EDA 或另一個 agent。Supervisor 負責派工與
獨立驗收，預定 executor requested route 為 `auto/deepseek-v4.1-flash`。
本次 planner 的 requested catalog slug／effort 未由可檢查呼叫記錄提供，
記 `NOT_RECORDED`；planner、executor、reviewer 的
**backend effective model 均為 `UNKNOWN`**，除非另有實際 backend 回應證據。
不要複製先前計畫的 Astra slug 作為本次身分，也不要把 auto/deepseek
route、CLI 接受參數或成功完成工作當成 backend identity。
派工時保存 requested model、effort、invocation path、session/task ID、
fallback、prompt、stream/stdout/stderr、exit 與 supervisor disposition。

不得改 RTL、model、spec、collector、runner、測試、全域設定或 service routing；
只可在新的 ignored campaign namespace 寫執行／稽核證據。
這次不更新 STATUS、PROGRESS_TRACKER、DEVELOPMENT_REPORT、論文或歷史計畫。
若需要修改既有程式才能完成，停止並報告；不得由 executor 偷做修補。
本輪不是新的 RTL implementation 委派。

## 2. 已讀證據與凍結輸入

依 AGENTS.md、CXL_SPEC v1.0、APPROVAL、DECISIONS、SPEC_REVIEW、
STATUS、PROGRESS_TRACKER、ENVIRONMENT 與下列兩份 ordering 文件定義邊界。
保留 fire-only、全 105-bit descriptor、共同 FIFO/hold、reset、
closing-fire 計入後分類、下一 cycle visible、active/drain 分開等契約。
這是 CGOF 補充研究；不取代 primary nine 或 spec §9 的多完整窗驗證。

以下 SHA-256 是本次本機讀取所得；不是要求把歷史檔更新到新來源。
表內 `ordering/` 代表 `artifacts/implementation/cgof-rtl-ordering-confirmation/`；
`finite/` 代表 `artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/`。

| 檔案 | SHA-256 |
| --- | --- |
| `AGENTS.md` | `c75cf2ac002481c687fb43296f548b156470eb691a532599607d1da3095e480d` |
| `specs/CXL_SPEC.md` | `797a5cdf01d2f769f44ca45225a33cc0510b04a408a8ff847e1db1c80928a4cf` |
| `docs/STATUS.md` | `06170dbdd0e87febcc1149382bff20824e0c39f4b3fc4b5f9a8f8a20e12beb57` |
| `docs/reviews/evidence-review-followup-20261101.md` | `731c25da9977ecf79c85ba6320f8e9fced09a8a47e04c46824592b890d8916a0` |
| `docs/reviews/ordering-rtl-confirmation-plan-20261101.md` | `e68ab2ef3506029e2b719d6d80eadec3dcf6277debe1b13a5a674309f28c93ec` |
| `ordering/acceptance-20261101T045246Z.json` | `abdde975d65137f01620c3c32f5f901df55d242b691cb379a6e36b3cfb354989` |
| `ordering/manifest-20261101T045246Z.json` | `5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384` |
| `finite/aggregate.json` | `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d` |
| `finite/manifest.json` | `2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407` |

現有 Git HEAD 為 `99400ded42cc63c3b206bd5d13f51d36344b2689`，有既存
dirty/untracked files；不可 reset/clean/stash。實際來源以逐檔 SHA 為準。
ordering manifest 的 `source_hashes_before` 與 `source_hashes_after`
共 31 檔，本次全部與現檔一致，包含 untracked 使用中 source。
以該 manifest 的固定 raw hash 引用完整 source map，另 pin spec 與本計畫。
關鍵目前來源如下：

| Source | SHA-256 |
| --- | --- |
| `scripts/run_rtl_diagnosis.py` | `86c886e5de3ed6d230df1cb77f7ad9ae0e8b89c5b4033d32e1d1cfbf2da2f4b9` |
| `sim/experimental/test_cgof_diagnosis.py` | `64acddf82fb311d6bfc1dfbad5191e88a7bf8a6c2c0f0c22346213be82db039a` |
| `sim/experimental/cgof_diagnosis_traffic.py` | `6a0f1d641e4c99d1dd820dc514caeb1c88b67c3c8394a764d58828c77b2a77b9` |
| `refc/cxl_model/diagnosis.py` | `1b817ceda2a41806f17fee4ebd21da5637b3c5798e19b3716a766e11d3622619` |
| `scripts/test_run_rtl_diagnosis.py` | `9fc16708c204865922dc366ecf89c83dd514c736a4c9f6c301c30cf8e894f743` |

歷史解讀固定如下：

- W256 seeds 6501–6520 為 160 jobs／80 pairs；主要規則結果
  `NOT_CONFIRMED`，joint improvement 7/20，不能改寫成確認成功。
- 舊 W5M finite-heavy seeds 529–548 為 80 jobs／40 pairs，僅 OF、
  Q1/Q2，Heavy work=5,000,000、windows=1、near、Bernoulli ready。
  本次讀取其 20 個原始 scope/summary：80 jobs 都只跨一個 close，
  old/new class 僅 H/B_H；active cycles 範圍 6,248,005–6,251,434。
  20 份 summary raw hashes 皆與 aggregate 的 `inputs_sha256` 相符。
- 該舊 aggregate 的來源與目前 ordering source 不同，且 ready pattern
  不同，只提供成本／可行性先例，不作新 ordering 對照或額外 seed。
- seed6301 的 W256 Heavy=1024 曾在第二 close 進入 L，雖 execution
  PASS，fixed-effective-High manipulation 失敗；保留這個警示與原始失敗。

## 3. 唯一凍結矩陣與 stop horizon

| 因子 | 本輪固定值 |
| --- | --- |
| Evidence / top | `SCHEDULER_RTL` / `cgof_unit_top` |
| N / D / M / descriptor | 4 / 16 / 1 / 105 bits |
| 真實 classifier W | **5,000,000 cycles**；production 23-bit counters、32-bit comparison intermediates |
| Mode / windows | `finite-heavy` / `1` |
| Heavy | **5,000,000 requests**，固定 source0，不切角色、不重置、不預載狀態 |
| Profile | `near`：Heavy p=.80，Sparse sources1–3 各 p=.02 |
| Active ready | `bursty`、p=.90、period100；k%100=0…89 ready，90…99 stall |
| Cut | 最後一筆 Heavy fire 所在 cycle；`C=completion_cycle+1` |
| Active cap | `--max-active-cycles 8000000`；未完成即失敗，不加長 |
| Drain | 不再生成；沿用既有強制 ready=1 cleanup 與既有 drain bound，無 reset |
| Quotas | Q1=High:Low 1:1；Q2=2:1；Low weight 固定1 |
| Ordering | OF=`oldest-first`；RR=`eligible-round-robin`（不是 primary RR10） |
| Lanes | 每設定都有 mixed、isolated；isolated 只移除 Sparse arrivals |
| Seeds | 6601 pilot，之後 6602→6603→6604→6605；共至多5個，不替換 |
| Local resources | 同時最多2個 jobs，`--jobs 2 --make-jobs 1`；絕不平行 seeds |

`windows=1` 是 traffic config 參數，**不是讓 classifier 在第一 close 停止**。
Finite-heavy mode 由 Heavy completion 終止，不能用此參數宣稱 close 數。
本輪要求每 job 實際跨且只跨一個 close：window0、cycle4,999,999，
新狀態 cycle5,000,000 可見，且 `5,000,000 < C <= 8,000,000`、
`C+drain_cycles < 10,000,000`。因此確有 close 後 active 觀測，
第二 close9,999,999 不得落入 active 或 drain。
預期 C 約6.25M，只是規劃估算，不能代替實測 gate。

無 time skip、縮窗替代、state deposit、warmup/training、classifier freeze、
額外 output staging、低工作量 smoke 或 role-switch。Pilot 本身就是
8 個真正 W5M jobs，不另跑 W256 當 production pilot。

## 4. Manipulation 與研究問題

從 reset 的 all H 開始，使用
`cxl_model.fai_main_model.EFFECTIVE_CLASS` 和 `HIGH`：
`H/B_H -> High`，`L/B_L -> Low`。不可用 `state == "H"` 代替此映射。
逐 job 檢查唯一 close 的四來源 `old_classes`、`classes` 都為有效 High；
H→B_H 是合法 state transition，**不是有效 High→Low**。
檢查關閉前狀態連續性、close phase/index/cycle、Heavy source0、B/S 與
threshold transition，並依既有 per-cycle oracle 與 pin-history checks
確認 RTL 對應；close 記錄是 harness/model 記錄，不偽稱獨立 DUT raw trace。

本輪科學問題是：在一個真實 production close、全程有效 High 的有限
工作協定中，quota × eligible ordering 對 completed Sparse run-P99 的
描述性差值為何，並付出何種 Heavy interruption／completion 代價？
實體 state 可以變，effective service class 不變；本輪不能證明 Low
transition 後的適應、latency recovery 或穩態 tail。

**多窗分支不在本計畫內。** 若任一 job 有第二 close、有效 Low，或未跨
第一 close，manipulation gate FAIL，停止其後 seeds，保留已執行資料為
`OUT_OF_DESIGN`，不得重新命名為成功的 dynamic exploration。
若將來另做多窗，必須在新計畫中把問題改成「共同 exogenous arrivals/ready
下，live classifier→service→classifier feedback 的整個有限協定效果」，
固定 Heavy work、close 數／觀測 horizon、Low exposure 與 cohort，再決定
是否能做 phase-specific 分析。Low 出現後，不得把全程 latency 差當成
fixed-class ordering estimand；現有 whole-run histograms 也不能事後切出
Low-only P99。那是新實驗，不能靠延長本輪 seed 或換 seed 完成。

## 5. 最小 primary／secondaries 與分析單位

只有一個 **descriptive primary contrast**：每 seed 的 interaction
`I=d2-d1`，其中 `d_q=S(Qq,RR)-S(Qq,OF)`，S 是 mixed job 的
`generation_roles.latency.sparse.generation_to_fire.p99_nearest_rank`。
保留四個 S、d1、d2 和 I，單位 cycles；負 I 只表示 Q2 的 RR−OF 差值
比 Q1 更負，不自動表示 Q2-RR 較好。

S 的 population 是該 job 在 Heavy completion cut 前（包含 cut cycle）
生成的所有 Sparse requests，含 drain 完成的等待；不是 active-only P99。
不同設定的 cut 可能不同，完整 Sparse cohorts 可能不等。
**本輪事前選擇 protocol-defined finite-cohort descriptive estimand**：
共同外生生成規則＋各自 completion stopping＋ready=1 drain 的整體結果。
它不等於 W256 計畫要求完整 matched cohorts 的 confirmatory estimand。
完整 cohort hashes／counts／end cycles 必須公開；不等時標
`PROTOCOL_COHORTS_DIFFER`，仍可描述 I，但不得說同一批 requests 的
個體 latency causal effect。完整 cohort 相等是診斷欄，不是挑樣本 gate；
共同 prefix 不等、完整 Heavy work 不等或 replay 不符則是 control FAIL。
無論 cohorts 是否相等，五 seed 都不升格為 confirmation。

只保留兩個 secondary endpoint families，不挑有利結果增加端點：

1. Mixed Heavy `Hmax=d.heavy.max_wall_gap`；核對等於
   `generation_roles.heavy_gaps.samples.inter_service.wall_cycles.max`。
   每 quota 報 RR−OF；僅 active accepted-minus-fired backlog 的 completed
   inter-service gaps，不混 initial、empty-terminated 或 censored gaps。
2. 每設定 `A=C_mixed-C_isolated`，單位 cycles；每 quota 報其 RR−OF。
   原始 C、Heavy first/last release、completion 與 drain cycles 同列。

Sparse count/max/mean/histogram、Heavy gap-kind counts/censoring、Q1 及
isolated 的端點相等／差異是完整性／解釋診斷，不新增 ranking 或 test。
原始資料保留既有 A→F、G→A 與 per-source counters，但不把它們升為
新 secondary claims。Q1 ordering 相等是觀察，不預設為必過 gate；
不同 ordering 在單一 active source 也可能有非同一內部 credit history。

以包含8 jobs的 **seed block** 為單位，等權報原值、mean、median、
min/max、負／零／正數；不 pool requests 或拿40 jobs作40個獨立樣本。
無 p-value、CI、bootstrap、power、20-seed門檻、winner、noninferiority
或依正負號提前停止。P99 由 histogram 整數 rank `(99*n+99)//100`
重算；W5M cohort 不再假設 P99=max。必需 primary 空／missing 為 gate FAIL；
isolated Sparse 空是預期 N/A。任何 missing 不轉0。

Pilot 若通過全部 gates，保留為這五個預定 exploratory seeds 的一員；
不能同時算作獨立 pilot 加五 seeds。最後狀態僅
`COMPLETE_DESCRIPTIVE_EXPLORATION`、`PILOT_ONLY` 或 `STOPPED_INCOMPLETE`。
發生 stop 時列出所有已見端點，但不做「成功 seeds 子集」的主要總結。

## 6. 成本與固定資源預算

成本來自上述 finite aggregate 列出的 **20 個 summary.json**，不是 W256
wall time 按 W 比例放大，也不是僅看 batch 起訖時間。舊每 seed 為4 jobs、
jobs=2；不同批次存在其他 seeds 同時執行，故 wall time 有競爭差異。

| 舊 seed／run | `summary.wall_time_s` | 約分鐘 |
| --- | ---: | ---: |
| 529 / `20261028T215003Z_4833` | 2725.119 | 45.42 |
| 530 / `20261028T223529Z_126801` | 2839.011 | 47.32 |
| 531 / `20261029T003213Z_4511` | 4093.160 | 68.22 |
| 548 / `20261029T025022Z_373221` | 5249.118 | 87.49 |
| 20 seeds 的 mean／range | 4321.5148 / 2725.119–5249.118 | 72.03 / 45.42–87.49 |

舊四個 cocotb steps 的 wall time 加總平均8618.8092s，range
5405.697–10484.081s，約為 seed wall 的兩倍，與 jobs=2 相符。
新8 jobs、相同 Heavy work、仍jobs=2，粗估 **1.5–2.9小時/seed**，
中心約2.4小時；五 seeds 約 **7.6–14.6小時 simulation/build**，
另加每 seed streaming replay／人工 gate，規劃總量約 **10–20小時**。
新 bursty ready、RR source、cache／主機負載不同，以上不是保證。
約50M active cycles/seed、250M/5 seeds，另有少量 drain；不跳 cycle。

固定上限：每 seed runner **6小時**，其後 audit **1小時**；campaign
從首個 seed 開始最多 **36小時**（包括等待／review），另允許30s kill grace。
每個命令 cap 還要受剩餘 campaign 時間限制。Pilot gate 記錄實測 wall、
audit wall、peak RSS（可用時）、artifact/build bytes；只更新預估 ETA，
不得因此改 jobs、工作量、profile、seed、端點或 deadline。
未能在上限內完成／審完就是 STOP，不延長或改小 W。
Preflight 查 repository 與現有 WSL build cache 所在檔案系統空間，至少
各有10GiB可用；不足即停止，不能刪歷史 runs 或別人的 cache。
此門檻是資源保留，不是已量測的磁碟需求。

## 7. Preflight（執行者未來執行）

全部在既有 Ubuntu WSL、repository root、隔離 Python 環境中執行。
先確保沒有其他 source writer、同 namespace runner 或本輪 active job。
保存 Git HEAD/branch、tracked/untracked inventory、完整 diff、31-source map、
spec/plan hash、額外 preflight test/audit script hashes、tool/OS版本。
以結構化 job/config/manifest 查 seeds6601–6605 的歷史使用情形，包含
ignored artifacts 與失敗/partial runs；文件中提到 seed 不算已執行。
若已使用任何一個 seed，停止並報告，不自動挑6606。

新 namespace 固定 `artifacts/implementation/cgof-rtl-ordering-w5m-production/`。
首次建立前必須不存在；supervisor 建立 exclusive campaign record 後才派工。
保留 command transcript，或用 exclusive output capture stdout/stderr；
以下省略外部 transcript UI 的包裝，但不得省略實際保存。

```bash
source scripts/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/scripts:$PWD/refc:$PWD/sim/experimental:$PWD"
test ! -e artifacts/implementation/cgof-rtl-ordering-w5m-production
git rev-parse HEAD
git status --short
git diff --stat
sha256sum docs/reviews/ordering-w5m-production-plan-20261101.md
python -B --version
verilator --version
python -B -c 'import cocotb,pytest; print("cocotb",cocotb.__version__,"pytest",pytest.__version__)'
/usr/bin/timeout --kill-after=30s 600s python -B - <<'PY'
import hashlib, json
from pathlib import Path
import run_rtl_diagnosis as r
p = Path('artifacts/implementation/cgof-rtl-ordering-confirmation/manifest-20261101T045246Z.json')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384'
m = json.loads(p.read_text())
assert r.freeze_sources() == m['source_hashes_before'] == m['source_hashes_after']
assert len(m['source_hashes_before']) == 31
assert r.sha(Path('specs/CXL_SPEC.md')) == '797a5cdf01d2f769f44ca45225a33cc0510b04a408a8ff847e1db1c80928a4cf'
assert r.sha(Path('scripts/test_run_rtl_diagnosis.py')) == '9fc16708c204865922dc366ecf89c83dd514c736a4c9f6c301c30cf8e894f743'
print('SOURCE_PREFLIGHT_PASS; scheduler execution not yet performed')
PY
/usr/bin/timeout --kill-after=30s 600s python -B -m pytest -q -p no:cacheprovider \
  scripts/test_run_rtl_diagnosis.py \
  sim/experimental/test_cgof_diagnosis_traffic.py \
  refc/tests/test_diagnosis.py
```

歷史相同 targeted preflight 是35 tests／6 subtests；本次仍須實跑核對
collection、exit與fail/error/skip，不能照抄 PASS。另核對表內 context hashes。
不重跑 repository-wide power-vector suite；既有14個相關 errors不因此結案。
不增加 W256 smoke。由 supervisor 在 seed6601 前凍結 read-only audit helper，
存新 namespace，做小型 synthetic self-check：interaction sign、ties、P99、
H/B_H mapping、第二close／Low拒絕、hash/config mismatch、cut vs final censor、
cohort mismatch之描述性標籤及stop後不放行。不得 import 執行歷史 audit main
或照抄其中 W256/20-seed assumptions；不改既有測試檔。

## 8. Exact runner argv 與逐 seed 派工

現有 runner 支援全部參數；以 process-local `r.NAME` 覆寫隔離 namespace，
不編輯 runner。`--production-reviewed` 是 runner 開關，不表示結果已驗收。
下面 function 在同一 WSL shell 定義。由 supervisor 一次只呼叫一個 seed，
**不是自動五 seed loop**。完整 review PASS 記錄建立後才可下次呼叫。

```bash
ordering_w5m_start=$(date +%s)
run_ordering_w5m_seed() {
  local ordering_seed="$1"
  local ordering_left=$((129600 - $(date +%s) + ordering_w5m_start))
  (( ordering_left > 0 )) || return 124
  local ordering_cap=21600
  (( ordering_left >= ordering_cap )) || ordering_cap=$ordering_left
  /usr/bin/timeout --kill-after=30s "${ordering_cap}s" \
    python -u -B - "$ordering_seed" <<'PY'
import hashlib, json, sys
from pathlib import Path
import run_rtl_diagnosis as r
seed = int(sys.argv[1])
assert seed in (6601, 6602, 6603, 6604, 6605)
p = Path('artifacts/implementation/cgof-rtl-ordering-confirmation/manifest-20261101T045246Z.json')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384'
pin = json.loads(p.read_text())['source_hashes_before']
assert r.freeze_sources() == pin
r.NAME = 'cgof-rtl-ordering-w5m-production'
argv = ['--production-reviewed', '--window', '5000000',
        '--mode', 'finite-heavy', '--policy', 'both', '--ordering', 'both',
        '--seed', str(seed), '--windows', '1', '--depth', '16',
        '--profile', 'near', '--heavy-work', '5000000',
        '--ready-pattern', 'bursty', '--ready-period', '100',
        '--max-active-cycles', '8000000', '--jobs', '2', '--make-jobs', '1']
print(json.dumps({'runner': 'scripts/run_rtl_diagnosis.py',
                  'namespace': r.NAME, 'argv': argv}), flush=True)
raise SystemExit(r.main(argv))
PY
}
run_ordering_w5m_seed 6601
```

此 wrapper 不自動完成 gates；exit0 不能放行。Supervisor 保存 pilot
gate record 並逐項通過下一節後，才一次派以下一條（不是批次貼上）：

```bash
run_ordering_w5m_seed 6602
# STOP for complete supervisor gate; then, only on PASS:
run_ordering_w5m_seed 6603
# STOP for complete supervisor gate; then, only on PASS:
run_ordering_w5m_seed 6604
# STOP for complete supervisor gate; then, only on PASS:
run_ordering_w5m_seed 6605
```

跨 shell 時保存原始 campaign start、function定義、已耗時間，不能重置預算。
Supervisor 調用 read-only audit 時用 `/usr/bin/timeout --kill-after=30s`
與 `min(3600, remaining_campaign_seconds)`；audit command、script hash、
stdout/stderr／exit 同樣保存。不能把 wrapper 的 `sys.argv=[seed]` 誤判為
完整 runner argv；完整 argv 必須由此記錄、configs、params、logs交叉核對。

## 9. 每 seed 必過 gates：全部 PASS 才可放行

各 gate 都要記 `PASS/FAIL/NOT_RUN`、evidence path/hash與reviewer；沒有
檢查不能填 PASS。Pilot 和後續四個 seeds 使用完全相同 gates。

1. **Execution**：runner exit0、summary overall PASS、13/13 steps
   （4 lint＋1 traffic pytest＋8 cocotb），8 unique jobs／4 unique pairs。
   9份JUnit：1份traffic含5 cases、8份RTL各1 case；無fail/error/skip、
   XREJECT、warning relaxation或failure JSON。讀 build/lint/sim logs，不只看exit。
   Scope `smoke=false`、`production_reviewed=true`、`SCHEDULER_RTL`。
2. **Identity**：精確 `(seed,quota,ordering,lane)` 笛卡兒集合，Q1/Q2 ×
   OF/RR × mixed/isolated；job、params、compiled lint/build（含ELIGIBLE_RR
   0/1與FAI_W5000000）、trace_config皆與矩陣一致。Heavy source預設0，
   `heavy_sources=None`，沒有role switching；不能漏掉isolated或重複OF冒充RR。
3. **Source/integrity**：31檔 before=after=pin=現檔；sources.zip member
   名稱、數目與逐member SHA全符。spec與plan保持原hash。Raw results等於
   scope內嵌results；重算pairs，identity不碰撞；summary run_id與directory相符。
   本輪沒有修改既有source／歷史artifact，失敗與timeout檔不能被清除。
4. **Manipulation**：嚴格套用§3–4；唯一active close4,999,999，window0，
   all effective High，C及active+drain界限通過。核對四來源window-fired counts
   的B與S=sum(B)、含closing fire的exact unsigned threshold transition。
   保留held-grant／credit/refill／coverage counters；未命中的bin不宣稱coverage。
5. **Input controls**：逐job重播 `DiagnosisTraffic` 的完整active trace，
   重算 `trace_sha256`、generated、ready_count、Heavy首末release與config。
   每seed跨八jobs比完整5M Heavy `(generation_cycle,source,descriptor)`
   sequence及hash；相同ready在共同active prefix；mixed/isolated config
   除include_sparse外一致。四mixed設定的完整inputs在各對共同active prefix
   逐一相同；四isolated同理。記prefix長度，不把prefix標為全run相同。
   同時記各mixed完整Sparse cohort的ordered hash/count與equality旗標。
6. **Accounting**：Heavy completed=true且work=generated=fired=5M；
   completion=C−1；每role/source generated=accepted=fired；全局守恆、
   final request censor=0、producer/FIFO/held全清、active avoidable_bubbles=0。
   分列active-cut pending、drain completed、final censor；不得把cleanup的
   ready=1變成bursty、或拿drain fire算active throughput。
7. **Endpoints**：重算histogram count/max/mean/nearest-rank；primary S
   皆可用；Hmax duplicate path一致、A由raw C重算。分開所有gap kinds及
   censored counts；無有利方向／Q1相等門檻。Cohort診斷按§5固定解讀。
8. **Resource/release**：runner與audit未timeout，campaign未超時；可用空間
   仍過門檻；supervisor完成獨立raw/config/log/hash審核，記本seed放行決定。

重播採 streaming hashes，保留完整事件順序，不建5M個Python tuples的大表。
重用既有generator，必須傳release ordinal避免每cycle重算先前機會造成O(T²)。
只做外生traffic重播，不另跑8份Python scheduler model；原simulation的
cycle oracle與pin-history verification繼續全程啟用。可在同一streaming pass
對各job cut／共同prefix endpoints取hash snapshots，避免重複掃數千萬cycles。
完整raw trace digest依既有序列化重算；新增Heavy/Sparse cohort hash另記
encoding版本，不把不同canonicalization的digest硬比。Audit helper在pilot前封存。

## 10. 失敗處理、artifacts與analysis schema

**任何 gate FAIL：立即禁止下一 seed**；所有後續seed標NOT_RUN，不替換seed、
不重試失敗run、不改cap/profile/workload，不因效應方向決定重跑。
現有runner內部 `keep_going=True`，可能在同seed失敗後仍完成其餘jobs；
不能宣稱原runner具備first-failing-job fail-fast。Supervisor若已觀察到
material failure，停止派工並只終止本campaign已識別的process group，保存
已啟動／未啟動jobs。timeout124/137、exception、缺scope或partial output
皆保留原狀，不能把summary缺失補成成功。修復／重啟另需版本化計畫，
不得在本計畫悄悄補同seed或換seed。

新的runner run directories本身exclusive create；保留 `config.json`、
`commands.txt`、`versions.txt`、`summary.json`、`diagnosis_scope.json`、
`sources.zip`、`logs/`、`junit/`、`results/`及失敗輸出。只有新namespace的
`latest.txt`可由runner前移，不能用它挑選最好的run；舊namespace連pointer也不碰。
Campaign manifest、per-seed gate、input audit、analysis與command records
全部用exclusive create，修正audit則另編attempt檔，保留舊檔與差異理由。
所有raw/derived檔逐檔SHA-256；manifest自身hash由外層acceptance記錄，避免循環。
Machine paths／connection details只留ignored logs，不加入tracked計畫。

最小可機讀 schema（欄位語意固定，命名可直用以下）：

```text
manifest: schema=cxl-ordering-w5m-production-manifest-v1,
  plan{path,sha256}, evidence_kind, matrix, historical_inputs{path:sha256},
  provenance{requested_model,effort,invocation,session_id,backend_effective_model},
  git{head,branch,dirty_inventory,diff_artifact}, tools, source_hashes_before/after,
  commands[{exact_argv,env,start,end,stdout,stderr,exit,signal,timeout}],
  seeds[6601..6605]{role,run_id,status,gate_path,stop_reason},
  artifacts{path:sha256}, resource_usage, observed_counts, expected_counts

gate: schema=cxl-ordering-w5m-production-gate-v1,
  seed,run_id,plan_sha256,source_map,execution,identity,source_integrity,
  manipulation,input_controls,accounting,endpoints,resource,reviewer,
  disposition=PASS|FAIL|NOT_RUN, evidence_refs, reasons, next_seed_released

analysis: schema=cxl-ordering-w5m-production-analysis-v1,
  status, planned_seeds=[6601,6602,6603,6604,6605], valid_seed_count,
  jobs[{seed,q,ordering,lane,raw_path,raw_sha256,C,drain_cycles,
        heavy_work,first_release,last_release,completion,
        closes[{cycle,visible_cycle,phase,old_states,new_states,old_effective,new_effective}],
        sparse{count,p99,max,mean,histogram,cohort_hash},Hmax,gap_kind_counts,
        cut_pending,drain_completed,final_censor,eligibility,reason}],
  pairs[{seed,q,ordering,mixed_C,isolated_C,A,heavy_sequence_hash,
         common_prefix_cycles,ready_prefix_hash}],
  seed_rows[{seed,S_Q1_OF,S_Q1_RR,S_Q2_OF,S_Q2_RR,d1,d2,I,
             Hmax_delta_Q1,Hmax_delta_Q2,A_delta_Q1,A_delta_Q2,
             full_sparse_cohort_equal,cohort_label,gate_status}],
  summaries{I,d1,d2,Hmax_deltas,A_deltas: count,mean,median,min,max,negative,zero,positive},
  missing_cells, failures, limitations
```

全部五seed完成才有40job rows、20pair rows、5seed primary rows；pilot
僅8／4／1。Campaign最多20 lint configs、5 traffic invocations／25 cases、
40 RTL tests、45 JUnit files；preflight重複tests不加作獨特coverage。
Raw refs與availability欄位必須包含所有planned cells與停止原因。
分析先由executor產生，再由supervisor讀原始結果核對，不宣稱不同backend獨立性。

最終只可寫：指定N4/D16/W5M、near/bursty、5M finite Heavy、單一close、
有效High協定下，這至多五seed的描述性interaction與兩項Heavy代價。
Execution PASS不等於performance claim成立。不得宣稱20-seed confirmation、
stationary tail、一般winner、statistical equivalence、multi-window adaptation、
CQI/CXL/application benefit、memory bandwidth、PPA/STA/power或新formal/CDC signoff。
歷史W256與W5M資料不可混入新seed denominator；不更新舊論文／release snapshot。
