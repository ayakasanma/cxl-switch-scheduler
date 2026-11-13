# CXL Scheduler 開發與實驗總紀錄

更新：2026-10-21（Asia/Taipei）。本檔是持續更新的工程紀錄與總報告素材；原始 Spec、測試、合成報告仍是各項主張的依據。只記錄實際結果，規劃不算完成，工具指令 exit0 不等於功能、時序或 signoff 驗收。

最新完成：共同v2九組（source759f86b、canonical6f4777f0…）全部實跑並通過Codex與native獨立審查，接受為**pre-layout comparative area／STA**資料。Setup／hold／電氣9/9 MET；最小setup+1.158148ns，542065used output-driver pins均通過原始limit核對。140個untested checks全部constant_disabled，非全測／physical signoff。完整新表與review見[PPA_RESULTS_2026-10-21](PPA_RESULTS_2026-10-21.md)及第9節；前面原v1／pilot歷史保留，不混用。

## 1. 目前總結與報告邊界

Spec v1.0 已由 Project owner 於2026-10-13批准。FCFS、RR10、FAI-inspired Main 已完成既有功能驗收，原始九組 DC/PT 量測完成。原始 Main N16 setup 未達標，九組均有電氣違規。後續 cap075 方法在 FCFS4、Main16 兩組 pilot 消除原始 library 限制下的電容/slew 違規，但 Main16 仍有32個setup違規、最差−0.907946ns。功耗尚未量測，Algorithm-2 尚未實作。

2026-10-21 共用時間戳比較器的等價改善已完成完整功能回歸；新的Main16同cap075條件pilot實際DC/PT完成，setup+1.158148ns、hold+0.084335ns，timing／電氣違規與untested皆0，area437622.506788。這是單組新來源量測，不能替換原始九組矩陣；全輸出driver-load核對與後續共同九組重測另記。

總報告可以使用的結論：已建立可重現、共用硬體框架下的三政策實作與驗證；已完成原始九組硬體成本／時序量測及兩組電氣收斂pilot；共享比較器改善後已通過完整功能回歸，並實際量得Main16單組setup／hold／電氣皆達標。尚不可聲稱：新共同九組全部收斂、功耗優勢、佈局後signoff、Main的實測公平性收益、Algorithm-2結果或cycle-identical IEEE paper重現。

## 2. 問題、架構與批准範圍

本專案是UIUC ECE509的CXL-inspired descriptor-level switch scheduler研究，不包含CXL封包、coherence、link-credit engine或真實DRAM controller。Memory output固定M=1，N=4/8/16個request sources，每來源D=16個FIFO entries。完整105-bit descriptor：Tag32、Address32、Opcode1、Length8、Payload32；每次成功fire是等成本atomic transfer，Length不增加服務週期。Response tracking與tag matching留在testbench。

一個policy-selectable `switch_top` 共用descriptor representation、FIFO實作、佔用量與握手語意、output hold/stall控制、memory sink抽象、可見選擇時序與合成邊界。禁止用政策專用pipeline/bypass/buffering偏袒某政策。RR不儲存未使用timestamp；FCFS/Main保留32-bit arrival metadata。

| 政策／決策 | 批准行為 |
| --- | --- |
| FCFS | 比較各eligible FIFO head的arrival timestamp；同時到達取較小source ID；modular age假設未完成request的age小於2^31週期。 |
| RR10 | reset pointer0；每visit最多10個成功fire；stall不消耗quota；以post-edge push/pop occupancy判斷下一週期eligibility；quota到期必須前進。 |
| Main FAI | H/B_H/L/B_L四狀態；buffer保留原有效priority，第二個支持window才改變；KEEP與零服務window取消pending transition。 |
| Class visits | High/Low最多10個成功transfer交替；空class放棄餘額、不bank；window邊界不獨立重置quota；held grant保留source/class/quota context。 |
| Window | production W=5,000,000；B[h]/S是window-local fire counters，closing-edge fire先納入再分類；次週期生效，清空下一window counters，S=sum(B)。 |
| Arithmetic | production B/S為23-bit；threshold是32-bit unsigned widened arithmetic。 |
| Algorithm-2補充 | 另一個獨立variant：Buffer立即以stored target priority服務；KEEP/idle保留Buffer；先N4比較，後續擴大視PPA影響與時間。尚未實作。 |

主九組是FCFS/RR10/Main × N4/8/16。Multi-memory outputs、APR與其他選配延後。High/Low單輸出10/10 dispatch是本專案重建，不能冒稱原paper唯一指定的cycle行為。IEEE Algorithm2引用與行為來源為owner提供；未宣稱本地看過未取得的PDF。

權威文件：[CXL_SPEC](../specs/CXL_SPEC.md)、[APPROVAL](../specs/APPROVAL.md)、[DECISIONS](../specs/DECISIONS.md)、[Spec review](SPEC_REVIEW.md)。

## 3. 可重現環境與代理分工

唯一repository沿用 `cxl-scheduler`，無第二個專案checkout。Windows原生Claude Code搭配RTL Agent Team；WSL Ubuntu的Python3.12.3、Verilator5.052、cocotb2.1.0、pytest9.1.1執行開源驗證。詳見[WSL setup](WSL_SETUP.md)與[環境紀錄](ENVIRONMENT.md)。

商用實驗在實際可登入的UIUC FastX執行：`Synopsys_x86-64/2024` module，DC/PT W-2024.09，既有SAED32 RVT `tt0p78v25c` library。Library/PDK/license/executables留在校方主機，未複製進repo；帳密與機器絕對路徑不寫入本檔或Git。SSH使用owner已批准的pinned host key，未關閉host-key checking。

Codex負責協調、獨立審查、實際remote orchestration與此報告。Claude Code RTL Agent Team是主要實作／驗證agent；2026-10-20 owner將後續Opus5.5 effort改為medium，額度耗盡可用GPT6.1 Sol/high續接。代理實際啟動、回應model、退出狀態與fallback均需記錄。不可把無報告的失敗session當成已完成工作。各任務採單一寫入者；Codex維護本檔，實作agent不並行改寫本檔。

## 4. 版本與已驗收功能基線

| 版本 | 用途與限制 |
| --- | --- |
| `a518e1e` | Spec RC1。 |
| `1af80967bbc2fb83224f4725c4fb450889e69c62` | owner批准的frozen Spec v1.0。 |
| `cefbbb0bda8dab21c9dd962378041fc5e0c4a426` | 既有已驗證功能來源，修正M5 testbench closing-boundary accounting。 |
| `3006b23` | Main功能驗收紀錄。 |
| `081f8a219911909bda8472ae4b257d3e6ed3122d` | 原始九組乾淨export／共同量測flow。 |
| `046721b0130c93819887645e0face3d9a300372d` | cap075精確float32回讀修復；成功FCFS4 pilot來源。 |
| `aa89771d5b5bc48bb7e054d8a8df9558de32b4ee` | cap075 Main16 pilot來源；功能RTL與原九組相同。 |
| `b54aa645480b891c349bf4b5814f8b6f66034a01` | 2026-10-20電氣pilot／剩餘setup失敗收尾紀錄；本輪比較器改善起點。 |
| `d82f1b54ca54af2344ad07d914680547003f526f` | 共享比較器候選、實際RTL對比harness及focused review；單元已過，完整回歸／新PPA另記，不代表timing closure。 |

既有功能驗收不是本輪新RTL的驗收：

| 範圍 | 實際通過 | Run ID |
| --- | ---: | --- |
| M1 descriptor/FIFO | 286 | `20261017T034126Z_13943` |
| M2 common output/hold | 526 | `20261017T034156Z_14547` |
| M3 FCFS | 550 | `20261017T034300Z_16317` |
| M4 RR10 | 430 | `20261017T034404Z_18077` |
| RR1 supplement | 195 | `20261017T034453Z_19058` |
| Main unit | 805 | `20261017T012755Z_5680` native；`20261017T012115Z_2007`獨立執行 |
| Main stress | 30 runs | `20261017T013952Z_8032` |
| Main primary | 60 runs | `20261017T015238Z_9805` |
| Main production | 3 runs | `20261017T015838Z_13196` |

Main805包含196reference pytest、39TB-helper pytest及570cocotb；每次完整unit也檢查27strict lint configurations、9structural probes及3個Algorithm-2預期拒絕。重複收集的Python測試不算新的獨特RTL coverage。

主功能matrix共180/180：FCFS60、RR60、Main60；相同intended traffic/ready trace，記錄backpressure造成的actual acceptance差異。短primary不會關閉production window，不能據此量得適應性收益。Main stress為18million trace cycles；production三個N各20million實際non-reset measured cycles，共60million、12完整windows，沒有time skip或state preload。詳見[STATUS](STATUS.md)、[M5 results](phase-5-verification/M5-results.md)與[獨立功能審查](../reviews/phase-4-rtl/codex-fai-main-review.md)。

曾發生的M5長測試失敗：7FAIL/2PASS、21NOT_RUN。原因為testbench把closing measurement fire後的ready觀察錯要求納入已凍結的measurement snapshot；第一個drain cycle才擁有該觀察。`cefbbb0`只修TB accounting與新增directed case，未改RTL/model/Spec；保留原失敗log，完整重跑後才驗收。

## 5. 原始九組合成／STA量測

共同條件：完整switch、105bit、D16/M1；TT0.78V/25°C；25ns clock，setup/hold uncertainty0.1/0.05ns；I/O min/max delay0/2ns；input/clock transition0.1ns；output load2.656828fF；ForQA/top wire-load estimate，DC auto selection off；compile-medium、DC單核心；synchronous reset正常timed，無false/multicycle/case-analysis exceptions。面積是library area units，未驗證為µm²；不從slack推算Fmax。

| N | 政策 | Cell area | FF cells | PT setup ns | PT hold ns | PT cap/slew違規 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | FCFS | 103009.393996 | 8856 | +9.860374 | +0.049066 | 1118/31 |
| 4 | RR10 | 78521.602529 | 6782 | +20.523260 | +0.103864 | 1067/0 |
| 4 | Main | 108913.413301 | 9011 | +7.318300 | +0.050358 | 1077/32 |
| 8 | FCFS | 206479.551075 | 17677 | +3.763228 | +0.103860 | 2069/0 |
| 8 | RR10 | 157209.161099 | 13556 | +19.612915 | +0.080139 | 2119/0 |
| 8 | Main | 217096.925035 | 17932 | +0.930581 | +0.103860 | 2058/0 |
| 16 | FCFS | 411575.287966 | 35318 | +0.000811 | +0.103860 | 4423/0 |
| 16 | RR10 | 314506.001866 | 27102 | +18.758562 | +0.103860 | 4260/0 |
| 16 | Main | 436249.874914 | 35773 | −0.870709 | +0.079660 | 4200/4 |

九組DC/PT指令均完成exit0，不等於九組timing pass。Main16有32setup違規；FCFS16只約0.81ps正裕量，不代表穩健收斂。所有組合cap規則OPEN。Coverage未測試項目FCFS4=64、Main4=68、FCFS8/Main8各4，均具體constant_disabled，不能以報告四捨五入100%冒充全測。Main16則0untested。

完整來源／profile／library／result hashes、硬體分項與raw-report links：[九組結果](PPA_RESULTS_2026-10-20.md)、[JSON](ppa/primary-20261020-v1.json)、[執行紀錄](PPA_EXECUTION_2026-10-20.md)、[獨立審查](../reviews/phase-5-verify/FastX-PPA-methodology-review.md)。原始profile canonical SHA256 `6baba481319955c0a0425e7fb50a20eed3c8c1a224f2a90ee86a60afd92783af`。

## 6. 電氣收斂診斷、失敗與兩組pilot

FCFS4全26731個mapped output-pin load資料，以ordinary/static與CCS receiver maximum load差異，逐pin重現1118個PT違規；ordinary/DC檢查為0。最小ordinary/maxCCS比值0.7725474722，先前三樣本推估0.85不覆蓋全population。這是FCFS4的完整比對，非全library／所有N的通用界限。

原生DC canary確認既有`lib_pin max_capacitance` application attribute可在記憶體中收緊：INVX2/Y16→13.6fF，實際DRC對相同net得到−2.117124fF；還原後恢復。未寫入`.db`。採候選cap075，compile期間乘0.75，所有390定義限制在compile後及失敗時還原；20未定義library outputs明確略過，兩組pilot的所有實際使用driver均有原始正限制。

第一個完整candidate在compile前因requested50.76502425/readback50.765026停止：8applied/9attempted均還原，未當成合成成功。原生precision canary確認float32儲存＋六位小數回報；`046721b`按精確表示方式檢查，不加入任意容差。最終44個工具流程測試跨Windows／WSL均至少實跑一次，非新的scheduler coverage。

| Pilot | 變更／實際結果 | 處置 |
| --- | --- | --- |
| FCFS4 high effort | 與medium mapped module bodies相同；area/slack/cap/slew均未改善。 | 不採納，未擴大sweep。 |
| FCFS4 cap075/medium | area103730.908806（+0.7004%）；FF8856；setup+9.881229/hold+0.033790ns；cap/slew0/0；64constant-disabled untested。 | 單組pilot通過，非全專案signoff。 |
| Main16 cap075/medium | area437228.837383（+0.2244%）；FF35773；setup−0.907946/hold+0.085328ns；cap/slew0/0；32setup違規、0untested。 | 電氣改善，timing未達標；保留失敗，不採為全九組新baseline。 |

兩個pilot均實際DC/PT與wrapper exit0，390/390限制還原，SDC無cap overlay外洩，fresh PT讀原始library。FCFS4新27231、Main16新116345個used output pins全有正原始limit，CCS/ordinary均0cap違規。Library SHA256始終 `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`。

候選profile canonical SHA256 `51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f`，維持PILOT。完整過程含失敗、remote backend、傳輸與數值校準：[收斂診斷](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md)。

## 7. 時序瓶頸與2026-10-21比較器候選

原始Main16最差路徑FIFO9讀指標→source13 class state，arrival25.729298ns。共用FCFS selector約20.249199ns，其中四個32-bit ripple subtractor、120carry cells佔約18.095890ns。Tree本來已balanced；問題不是16來源串行掃描。輸出descriptor payload mux不在這條class-state path。

cap075 Main16最差改為FIFO15讀指標→source12 class state，arrival25.749029ns；selector20.314253ns，後段走`fire→pop[12]→B_close→160*B_close→class`，而原始最差尾端走S_close。只改舊S乘法路徑可能留下新的B路徑；不允許漏算closing fire或加multicycle掩蓋問題。

本輪scope：保留balanced tree，只尋找`ts_older`行為等價寫法。候選由lower-bit borrow與MSB XOR得到modular difference sign，嚴格保留nonzero、wrap、ties、exact-half-range及TS_W>=2。若採用，FCFS與Main同時使用；RR不額外插入timestamp。沒有新pipeline、storage、policy-specific bypass。

本輪執行紀錄（待實際結果更新，不是完成宣告）：

| 項目 | 狀態／證據 |
| --- | --- |
| 起點 | clean `b54aa645480b891c349bf4b5814f8b6f66034a01`；Spec1af80967不改。 |
| Native agent | Claude Code2.1.304、RTL Agent Team0.14.6 `rtl-coder`；session `322c1671-e1c8-4f12-a942-50d733089ea1`，要求Opus5.5/medium；實際response model `claude-opus-5-5`，最終exit0，無fallback。 |
| Spec／權限probe | agent已讀frozen Spec；實際Bash/Write probe成功，證據為native `tool-inventory.txt`、`write-probe.txt`及stream。 |
| Comparator候選 | d82f1b5；數學等價審查、實際RTL比較與完整功能回歸通過，未改Spec／pipeline／FIFO／policy語意。 |
| 等價證明／有限檢查 | selector hash `3418505168ca4a0c93422101f1e1a7a042833c935e0f9b021661535b7b6a2c20`；實際新舊RTL共21組、81,108,288向量均無不一致，run `20261020T165027Z_1281`。基準HEAD當時解析為b54aa64。32-bit部分為邊界及4個N的任意／clustered隨機，非完整窮舉。未使用SMT。 |
| 新RTL lint／M3 unit | `scripts/run_verify.sh M3 -j 8 --make-jobs 2` exit0，550PASS，12strict lint；run `20261020T165234Z_2953`。Codex獨立核對32份JUnit，零failure/error/skip、無build relaxations。 |
| 新RTL M5 unit | `scripts/run_verify.sh M5 -j 8 --make-jobs 2` exit0，805PASS，27strict lint、9structural probes、3expected rejections；run `20261020T165357Z_386`。Codex獨立核對32份JUnit，零failure/error/skip、無build relaxations。 |
| 更廣回歸與production | 原batch完成前三scope後受SIGHUP中斷；resume1剩餘六scope已全部exit0。9個完成stage前後76功能來源hash均通過；最後功能來源亦一致。原始JUnit、full_scope與新舊metrics已獨立核對。 |
| 新候選DC/PT | Main16探索性cap075 pilot DC/PT/wrapper exit0，setup+1.158148／hold+0.084335ns，0timing/electrical violations、0untested；單組結果不替換共同九組。 |

本輪原始prompt、response stream、stderr、exit、before-hashes與diff在ignored `.setup-logs/implementation/comparator-20261021/native/`。報告僅引用必要證據與結果，不內嵌憑證、完整library或大量機器log。

2026-10-21首輪檢查遇到驗證harness問題，非已證實RTL功能失敗：boundary stimulus的動態array迴圈／wrap stimulus先行修正，之後N4 build因N2 boundary branch的concatenation寬度收到strict Verilator WIDTHEXPAND而exit1。agent保留strict warning gate、加入明確寬度cast後重跑。舊tool results保留在完整stream，Codex另存觀察到的console snapshot；尚未把失敗當成PASS或放寬warning。新的比較直接實例化working-tree selector與Git baseline改名module，另用integer／unwrapped-age oracle核對；32-bit測試是有限抽樣，不是完整formal signoff。

三個隔離mutant（移除tie guard、borrow改成<=、移除borrow）分別在W4窮舉及W32邊界測試被偵測，六次模擬均非零退出。此negative control的第三個mutant刻意留下unused borrow，因此隔離mutant build使用非fatal warning；正式21組檢查與M3/M5未放寬strict flags。預設Verible style另回報既有命名／array樣式衝突，未宣稱Verible全綠。M3首次指令把`--make-jobs 2`誤打成`--make-jobs2`，parser exit2、尚未執行測試，修正後完整M3 exit0；原argument-error log保留。

Codex審查發現新腳本預設baseline=HEAD，未來commit後可能讓新舊來源相同；Codex已將此驗證基礎設施預設固定為完整b54aa64 commit，並拒絕來源完全相同的比較。現有native21組結果仍有效，因summary明記實際baseline b54aa64與新舊不同hash；修正後的腳本另行獨立執行。更廣回歸已開始；單元通過不等於新RTL已完成production或PPA驗收。native詳細推導與檢查見[比較器結果](phase-5-verification/ts-older-comparator-20261021.md)。

修正後獨立run `20261020T165753Z_1026`：同樣21組、81,108,288向量ALL_PASS，程序exit0；script hash `d3aad33f9c7e36bd90b0c6a16ea8a6ae00eec6dd239f46010a414afa78328515`。提交d82f1b5後，以HEAD明確指定相同來源，確實exit2並顯示`refusing identical DUT and baseline sources`；不是意外零向量PASS。此腳本以Git executable mode100755保存。獨立[RTL／共同架構審查](../reviews/phase-4-rtl/codex-comparator-review.md)未發現新增架構衝突。Native74個assistant response records均為Opus5.5，最終result success、無permission denial；原本prompt／diff／logs完整保留。

### 本輪主要／長時間回歸追蹤

| Scope | 狀態／實際結果 | Run ID |
| --- | --- | --- |
| M3-primary | 60/60 PASS，100,000 cycles/run；raw JUnit與full_scope核對通過；60筆summary run records與既有FCFS基線完全相同。 | `20261020T165716Z_534` |
| M4-primary | 60/60 PASS；raw JUnit/full_scope通過；60筆run records與舊RR基線完全相同。FCFS與RR共120個trace hashes均符合固定FCFS record。 | `20261020T170247Z_5075` |
| Main stress | 30/30 PASS，18million trace cycles；raw JUnit/full_scope通過，每run四狀態／16轉換均出現。完整功能metrics與舊stress結果相同，僅主機wall-time、cycles/s與RSS欄位有差異。 | `20261020T170825Z_8460` |
| Main primary | 完整重跑60/60 PASS；raw JUnit/full_scope通過，60筆run records與舊Main基線相同；三政策primary共180/180。 | `20261020T172737Z_382` |
| Main production | 3/3 PASS；每個N實際20million non-reset measured cycles、四完整W5,000,000視窗，共60million／12視窗，不time skip或preload；排空outstanding=0。功能metrics與舊production相同，僅主機效能欄位不同。 | `20261020T173518Z_3766` |
| M1 | 286PASS；raw JUnit已核對。 | `20261020T190753Z_4587` |
| M2 | 526PASS；raw JUnit已核對。 | `20261020T190823Z_5191` |
| M4 | 430PASS；raw JUnit已核對。 | `20261020T190924Z_6959` |
| M4-q1 | 195PASS；raw JUnit已核對。 | `20261020T191009Z_7942` |

執行前的Main16本地export紀錄（其後已完成實跑）：乾淨來源`b257ee8d878b94c14fb7ad78d03ff0ddb2ee7ee6`，payload SHA256 `f122192ee6ca7f4d9cc5d0f86f7325a7bb3377c86ebf87d5c334e9df31771093`，相同cap075 canonical profile `51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f`。位置：ignored `artifacts/ppa-prep/comparator-cap075-main-n16-20261021a/`。初次指定不存在parent及非artifacts輸出位置被既有guard拒絕，改用允許目錄後exit0；沒有因此變更guard。這是可重現payload，實際量測結果另列下方。

2026-10-21已依原批准host key重新登入FastX，唯讀preflight exit0：backend `fastx4-NN.ews.illinois.edu`，DC/PT均為W-2024.09既有路徑，library雜湊仍為844d4474…，home/cxl所在檔案系統空間足夠。原始log `.setup-logs/FastX-NN/remote/170852-comparator-readonly-preflight.*`（延用既有helper目錄，不代表執行日期為20日）。未下載library，尚未合成新RTL；task SSH master完成後須關閉，未保存憑證。

續接時實際觀察到中斷：原batch於2026-10-21 01:25:53 Asia/Taipei收到SIGHUP，exit129；WSL其後重啟，無殘留模擬／SSH master。已完成的M3-primary、M4-primary、M5-stress保留有效；Main primary run20261020T172119Z_10354僅部分完成，原summary停留RUNNING但程序已不存在，**NOT_ACCEPTED_INCOMPLETE**，不是完整PASS，也不是RTL功能失敗。原始log／summary不覆寫，另記interruption JSON。以`.setup-logs/implementation/comparator-20261021/regression-resume1/`重跑完整Main primary及後續階段，不重跑前三個已完成scope。尚未合成候選。

執行順序更新：完整Main primary重跑通過後（主矩陣180/180、Main stress30/30、focused units均過），production run `20261020T173518Z_3766`啟動並持續模擬。Codex將**單組探索性Main16 pilot**改為與production並行，以利用長測試等待時間；不是新九組sweep，也不提前採納／宣布功能或時序驗收。候選最終採納仍以production、共同／RR回歸與實際PPA審查為gate。此更新取代本輪先前「所有回歸完成後才開始任何合成」的執行排序，沒有放寬任何測試／PPA條件。

重新登入後第一次remote helper在master認證尚未完成時遭BatchMode拒絕（SSH255），沒有建立遠端run。確認master `-O check`成功後，使用同一不可覆寫stage腳本重試；payload21檔及SHA驗證通過才會執行。失敗與重試log分別保留`173811-comparator-cap075-main16-run.*`與`comparator-cap075-main16-run-retry1.*`。啟動時列RUNNING，最終DC/PT與wrapper均exit0。

pilot此次backend實際為`fastx4-NN.ews.illinois.edu`（17:39:04 UTC觀察），與先前readonly preflight的4-23分開。remote root `~/cxl/experiments/comparator-cap075-main-n16-20261021a/cxl-ppa-syn-fai-main-n16`；sourceb257ee8、cap075 profile／library／clock等與已準備manifest一致。`dc_shell -version`的非零退出附有效W-2024.09 banner，沿用既有flow列為informational，不拿版本查詢退出代表compile成功。

### 本輪Main16實際量測與採納界線

| Same cap075 Main16 | 舊aa89771 | 新b257ee8 |
| --- | ---: | ---: |
| Total cell area（library units） | 437228.837383 | 437622.506788 |
| FF cells | 35773 | 35773 |
| PT setup slack ns | -0.907946 | +1.158148 |
| PT hold slack ns | +0.085328 | +0.084335 |
| Timing violated／untested checks | 32／0 | 0／0 |
| PT cap／slew violations | 0／0 | 0／0 |

setup改善2.066094ns，總面積增加393.669405units（+0.09004%）；143344個PT checks全tested/met。390/390暫時限制還原，SDC未帶出cap overlay，fresh PT讀原始library。完整116993used output-driver pins皆有正原始限制、ordinary／CCS零cap違規；20constant pseudo drivers另列。driver survey只read/relink，不compile、不改mapped netlist/SDC，前後source hashes一致。兩次download allowlist與remote/local hashes均過，未下載proprietary assets。

新最差path是FIFO0 read pointer→source3 class state；該path selector區段16.676499ns。舊cap075最差path selector20.314253ns，兩者endpoint/mapping不同，不冒稱逐cell同路徑差。雖FIFO／hold RTL未改，mapped subtree area也因load／mapping變化而不同；總面積差不能叫純selector成本。

**採納：共享比較器功能驗收通過；Main16單組pre-layout pilot timing／electrical達標。未替換原始九組dataset，cap075 profile仍PILOT。** 下一步凍結共同新methodology、相同來源重測並審查九組，之後再進行Algorithm-2補充及activity-based power。完整數值、驗證run IDs與raw paths見[本輪收尾報告](PPA_COMPARATOR_PILOT_2026-10-21.md)與[JSON](ppa/comparator-main16-20261021.json)。

最終遠端唯讀核對再次確認library hash未變、dc_exit=0／pt_exit=0及survey source-before/after一致。task SSH master以`-O exit`正常關閉（exit0）；Windows互動式保持連線wrapper隨後exit1，僅為關閉後wrapper狀態，不改寫已完成remote腳本exit0。resume1 foreground batch回收exit0，無繼續中的模擬或EDA job。原中斷、認證race、harness及parser失敗均保留，沒有靜默捨棄。

## 8. 總報告撰寫規則與尚缺工作

本檔按「原始baseline／改動候選／新量測」區分版本。總報告比較表必須使用同一已審查共同methodology，不能把舊medium九組、high pilot與cap075兩組混成同一公平比較。政策subtree與完整switch差值分開；完整差值含metadata與mapping context，不能稱純selector cost。

後續必需：共用比較器等價／功能回歸、實際合成改善評估、同一採納方法的九組重測與審查。Algorithm-2補充仍獨立；power需要真實workload activity annotation與能力／coverage確認；商用equivalence、APR、post-layout與multicorner未跑。Formal不應把局部combinational proof誤稱完整switch等價signoff。

每次更新至少記錄：日期、來源commit／dirty-file hashes、agent與actual model／effort、改動原因、實際commands／run IDs／exit、PASS/FAIL/SKIP/NOT_RUN、失敗原因與修復範圍、原始證據位置、是否改變共同條件、採納／拒絕與下一步。進度總覽同步[STATUS](STATUS.md)、[PROGRESS_TRACKER](PROGRESS_TRACKER.md)與[續接說明](RESUME_CLAUDE.md)。

## 9. 2026-10-21共同v2九組量測（已完成與驗收）

本輪起點clean `e131f85f1164725ab7a3d186a8b8fbccd574ae27`，沿用已驗收比較器及完整功能結果，不重跑未變更RTL的長回歸。新增`saed32-rvt-tt-25ns-forqa-cap075-v2` profile作為共同固定方法；除profile_id、status與review metadata外，與成功cap075 pilot全部欄位完全相同。25ns、TT corner、I/O、uncertainty、transition、FO4、ForQA/top、compile-medium／one core及0.75記憶體內限制收緊均未改；PT仍以原始library限制驗收。FROZEN只表示固定比較方法，不表示九組已達標。原v1與PILOT profile保留。

v2 canonical SHA256 `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`。Codex已以既有validator實際檢查並assert所有非metadata欄位相同。Claude Code2.1.304／RTL Agent Team0.14.6已再次確認；實際native `synthesis-reviewer` session`b73c8c4f-2906-4b42-956e-098749f8d110`以Opus5.5/medium完成exit0，68個assistant response records均為`claude-opus-5-5`，無fallback／permission denial。Read/Bash/Write probe成功，已讀frozen Spec與actual pilot／functional gates。97/97 profile綁定檢查通過；Windows generator suite44collected、36PASS、8有明確platform原因的SKIP，屬流程基礎測試，不是scheduler coverage。最初Windows Python收到POSIX path而失敗，改用Windows path後檢查exit0，原失敗log保留。審查[PASS_COMMON_METHOD](../reviews/phase-5-verify/common-profile-v2-review.md)，唯一執行前條件是提交profile並從單一clean commit準備九組。native logs／prompt／diff位於`.setup-logs/implementation/rebaseline-20261021/native-review/`；Codex單獨維護本報告，native只寫指定review。凍結時九組仍NOT_RUN，方法通過不預先代表數值達標。

本輪SSH以原批准pinned key登入，唯讀preflight exit0：backend `fastx4-NN.ews.illinois.edu`，DC/PT W-2024.09既有路徑，library hash844d4474…未變，遠端新control目錄不存在、可安全新建，home/cxl空間足夠。證據`.setup-logs/FastX-NN/remote/230812-v2-preflight.*`。後續依相同source/profile依序執行FCFS／RR／Main × N4/8/16；工具或傳輸失敗保留並停止，不能以exit0代替timing／電氣／coverage審查。預定每組另做唯讀used-driver負載核對，確認0.75 remap後不靠未定義library限制漏檢。Power與Algorithm-2本輪尚未開始。

方法凍結commit `759f86b24f13ed5984c19034eeeea2ca43b0e971`已解決native review的MJ-1（先提交、clean export）。9份manifest全部`worktree_clean=true`、相同source759f86b／canonical6f4777f0…；8個RTL files hashes與已驗收comparator pilot逐檔相同，沒有新的RTL變更。準備清單`.setup-logs/FastX-NN/v2-prepared-inventory.json`，封包`artifacts/ppa-prep/primary-20261021-v2-{policy}-n{N}/`。9份21檔payload上傳與SHA核對均通過，remote staging exit0，log`231337-v2-stage-all.*`。

九組已實際啟動，RUNNING，尚未驗收。沿用原先順序／fail-fast控制script，只改新prefix：`.setup-logs/FastX-NN/primary-20261021-v2-run.sh`，remote control `~/cxl/experiments/primary-20261021-v2-control/`；每case保存開始／結束UTC與exit、獨立console、原始DC/PT reports及hash。來源／方法不可在case之間改動，report updates不影響已提交export。原始v1／pilot目錄完全保留。最終仍需逐組原始數值、constraints、coverage reasons、mapped storage、library restoration與used-driver負載核對。

早期觀察（不是完整九組驗收）：FCFS4、RR4工具與wrapper均exit0，84files/case已經allowlist取回且hash驗證；FCFS4 setup+13.071612／hold+0.033790ns、0timing／電氣違規，但64untested皆`constant_disabled`，不宣稱全tested；RR4 setup+20.519341／hold+0.049066ns、27356checks全tested/met。其餘仍依序執行。最後獨立總audit會逐組核對，未完成者保持NOT_RUN／RUNNING。

進度觀察：已完成8/9工具命令，最後Main16 RUNNING。N8 FCFS／RR／Main setup分別+8.714740／+19.669725／+5.713676ns，hold皆+0.103860ns；N16 FCFS setup+3.891612／hold+0.103860ns，RR setup+18.694050／hold+0.095469ns。已取回的所有結果均0timing／電氣違規。N4 Main有68untested、N8 FCFS與Main各4untested，皆明確`constant_disabled`；RR全tested，N16 FCFS全tested。原始six-case audit已核對source/result/SDC/storage/area/reference/coverage，最後仍須完整nine-case與used-driver audit。數字屬v2同方法，不能拼入原v1 table。

九組最後均完成exit0（remote case-exits UTC23:13:50至23:38:41，即Asia/Taipei2026-10-21 07:13:50至07:38:41），整批wrapper exit0。756個own report／netlist／SDC／manifest檔案已依allowlist取回，無proprietary assets。完整原始audit核對profile/source/result hashes、原始library、SDC完整I/O/clock/reset、mapped cell／reference area、storage metadata與coverage，9/9timing與電氣MET；140個untested分屬FCFS4=64／Main4=68／FCFS8=4／Main8=4，皆`constant_disabled`，不宣稱全九組全tested。Main16重跑結果與pilot相同：area437622.506788、FF35773、setup+1.158148／hold+0.084335ns。機讀[新九組摘要](ppa/primary-20261021-v2.json)先標記review PENDING；driver surveys正在執行，native最終結果審查尚未完成，不能把命令完成當最終採納。

九組唯讀driver survey其後全部exit0，90個reports經allowlist取回，hash驗證通過。逐pin核對542065個used output drivers原始limit均defined／positive，ordinary／CCS cap violations皆0；80個constant pseudo-drivers另列。netlist／SDC source-before/after一致，survey不compile、不寫netlist。各組pin數FCFS4=27243／RR4=20719／Main4=29458／FCFS8=54818／RR8=41529／Main8=58674／FCFS16=109599／RR16=83032／Main16=116993。證據`.setup-logs/FastX-NN/v2-nine-full-load-audit.json`與`artifacts/fastx/primary-20261021-v2-loads-*/`。native synthesis-reviewer已實際續接同一session、要求Opus5.5/medium，審查全部新結果／警告／constraints／storage／load等證據；最終review尚未完成，仍保持採納PENDING，Codex維護[新九組報告](PPA_RESULTS_2026-10-21.md)。

### 最終審查、失敗紀錄與採納

Native synthesis-reviewer最終完成exit0，verdict[ACCEPTED_FOR_PRE-LAYOUT_COMPARATIVE_AREA_STA](../reviews/phase-5-verify/primary-v2-results-review.md)。獨立492/492 assertions通過，重新計算hash／mapped storage／area／SDC／coverage／driver loads；67個實際assistant response records均為Opus5.5、effort medium，無fallback／permission denial。同session期間有一次API `server_error` mid-response，synthetic錯誤record保留，隨後恢復並實際寫出review／checks／inventory，未將錯誤本身當完成。

Native首次strict check因九組emitted SDC `set_load 2.65683`與profile2.656828fF不完全相等而exit1。檢查確認DC固定五位小數serialization且舊pilot／v1相同，依實際表示精度使用5e-6fF界限，差值2e-6fF，最終492checks過。原strict失敗outputs保留，沒有更動profile、SDC或電氣limit。Codex再算area partition發現review概略FIFO占比93–98%應為92.40–98.63%，已標明Codex數值校正，不影響verdict／raw results。

原始檢查確認完整descriptor storage=N*16*105bits；FCFS／Main timestamp=N*16*32＋32bit counter，RR無timestamp。Disabled arcs僅propagated constant，沒有user／case／loop停用。所有九組390/390限制還原、20undefined library outputs未被用來漏檢；542065實際driver limits皆正，0ordinary／CCS超限。資料核對見`.setup-logs/FastX-NN/codex-v2-stage-checks.json`及native-results-review內原始Python／JSON／logs。

| N | Policy | Cell area（library units） | FF cells | Setup ns | Hold ns | Untested |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | FCFS | 103970.058316 | 8856 | +13.071612 | +0.033790 | 64 |
| 4 | RR10 | 79047.172316 | 6782 | +20.519341 | +0.049066 | 0 |
| 4 | Main | 110089.845892 | 9011 | +10.496409 | +0.039940 | 68 |
| 8 | FCFS | 208437.730604 | 17677 | +8.714740 | +0.103860 | 4 |
| 8 | RR10 | 158260.808962 | 13556 | +19.669725 | +0.103860 | 0 |
| 8 | Main | 219344.574607 | 17932 | +5.713676 | +0.103860 | 4 |
| 16 | FCFS | 416886.135213 | 35318 | +3.891612 | +0.103860 | 0 |
| 16 | RR10 | 316614.126327 | 27102 | +18.694050 | +0.095469 | 0 |
| 16 | Main | 437622.506788 | 35773 | +1.158148 | +0.084335 | 0 |

九組timing／電氣皆MET；只有上表四組共140constant_disabled未測checks。Main相對FCFS完整switch面積增幅N4/8/16為5.89%／5.23%／4.97%，相對RR為39.27%／38.60%／38.22%；差值含必要metadata與mapping context。最小setup margin在Main16，pre-layout wireload／ideal clock下達標不代表加入physical parasitics後仍保證達標。沒有Fmax、功耗、公平收益或paper cycle-identical主張。

全部實驗與survey及846個own files取回／hash驗證完成後，額外remote收尾查詢遇SSH master timeout／broken pipe；該查詢無輸出，終止卡住的唯讀程序後helper exit241。重新連線也未正常返回並結束，最後本機`ps -C ssh`確認無殘留SSH程序。既有九組library logs與最後成功完整control讀取均證實844d4474…未變；不把失敗收尾查詢冒稱再次核對成功。失敗／重試紀錄保留，沒有影響先前EDA／survey／transfer exit0。

**最終採納：v2取代舊v1作為新的共同pre-layout area／STA比較資料，舊資料完整保留作歷史。不是physical／multicorner／commercial-equivalence signoff。** 更新[JSON](ppa/primary-20261021-v2.json)、[結果報告](PPA_RESULTS_2026-10-21.md)、STATUS／TRACKER／RESUME。下一milestone為獨立Algorithm-2 N4實作／功能與行為驗證，再採同方法合成比較；power需另外建立實際activity annotation與coverage／工具能力。架構／Spec決策無新阻塞，沒有在本輪開啟RTL實作。

## 2026-10-21 VPN恢復與Algorithm-2補充實作啟動

Owner通知VPN重連並授權續推。現有唯一repo仍為cxl-scheduler，開始時HEAD `f0a75c5b08ec178c4e75acd9687167673447bb96`，工作目錄乾淨；未重建repo／工具。依Spec8.6，九組主實驗完成後開始獨立Algorithm-2 N4，不將其替換Main或加入主九組。共同FIFO／output hold／timestamp／10-fire visits／window accounting／timing contract不變，只實作核准的Buffer target-priority與KEEP/idle retention。Codex先核對AGENTS／批准文件／相關現有RTL、model、TB與runner callers；無新架構決策。

使用已批准host key、原有WSL SSH helper重新實際登入FastX backend `fastx4-NN.ews.illinois.edu`。唯讀preflight保留於`.setup-logs/FastX-NN/remote/001012-alg2-reconnect-preflight.*`；library仍為SHA256 `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`。DC `-version`實際列W-2024.09但exit1，故原`set -e`探測停在DC，沒有將PT未執行冒稱成功；後續`001024-alg2-tool-version-status.*`分別記錄DC_VERSION_EXIT=1與PT_VERSION_EXIT=0，兩工具版本均W-2024.09。該探測不compile、不合成、不算新scheduler結果，無下載proprietary資產或存密碼。

Native Claude Code2.1.304/plugin RTL Agent Team0.14.6確認啟用。以實際CLI `--agent rtl-agent-team:rtl-coder --model claude/claude-opus-5-5 --effort medium --permission-mode acceptEdits --allowedTools 'Read Write Edit Bash Glob Grep'`啟動fresh session `77281b50-edbf-4a55-9539-a77ad9d0736d`，stream真實model欄為`claude-opus-5-5`。完整prompt／settings／before-hashes／PID／stream／stderr與結束時diff inventory由`.setup-logs/implementation/alg2-20261021/native/launch.py`保留。要求先證明frozen Spec讀取與ignored Write/Bash，再依Spec先完成abstract reference、後讀RTL實作，model-free TB另定transition table。單一native writer負責RTL/model/TB/runner/focused M6文件；Codex獨占本報告與status/tracker/resume。尚未宣稱功能或PPA驗收；未用fallback。

### 獨立模型與共同架構先行檢查（尚非M6驗收）

Native實際完成ignored Write/Bash/WSL probe、frozen Spec blob一致性與model provenance核對，先從Spec／abstract Main contract寫Algorithm-2模型及tests，之後才讀FAI RTL body。初次Main+Algorithm-2模型148tests通過。Codex另以`git show f0a75c5:refc/cxl_model/*`載入修改前模型，對修改後Main模型跑N4/8/16 × W64/256/5,000,000，每組30,000週期，共270,000週期，比較所有view／edge records、class/window/visit state，含持續push／stall／reset／backpressure，9/9一致。前後model source hashes穩定；證據`.setup-logs/implementation/alg2-20261021/codex-review/main-model-parity.{json,stdout.log,stderr.log,exit.txt}`與可重跑Python保存。不把模型一致當RTL等價證明。

Codex實際WSL執行`python -m pytest refc/tests sim/common/tests -q --junitxml=.../reference-helper.xml`，280/280通過（241reference＋39helper），18.78秒；stdout／JUnit／exit保留於同codex-review目錄。此時RTL／TB仍在建置，尚無新Algorithm-2 cocotb結果。初步diff確認FIFO／out_hold／FCFS selector未更動，Main default分支／hierarchy保留，POLICY3使用同一FAI scheduler的compile-time INTERP=1及共同5bit context，只在closing transition套用target-priority table。

Native早期quick lint helper把所有非空stdout都當FAIL，誤將Verilator成功的普通summary（rc0、無warning/error）標成FAIL；原`quick_lint_1.log`保留，不能冒稱該helper exit0。真正功能/驗收lint將使用既有runner的diagnostic解析與嚴格flags；POLICY4及INTERP2的預期USERFATAL另算負面驗證，不算功能PASS。

### M6定向與行為比較完成／獨立限範圍採納

Native session最終exit0，無quota fallback。共同FAI新增compile-time INTERP=1，Main default0保留原classification，switch_top POLICY3使用相同module／5bit context。新增獨立abstract Algorithm-2 model與TB literal8.6 table，無改FIFO/out_hold/FCFS selector、pipeline、ports、Spec或constraints。

第一輪M6 `20261021T002805Z_856`確實FAIL：8failed jobs、3NOT_RUN，已啟動8jobs中共有10test failures，未接續合成。test09原要求2次tie，但情境實際只有1次；native重推情境，加上明確較舊高ID勝出並精確要求tie=1／older-win=1。test16 W256 seeds509/510未觸發BufferHigh/UP，刺激由48windows延長為100windows（W64由96至200），保留transition checks；native報告將缺少的state誤寫BufferLow/UP，Codex在review指出原log是BufferHigh/UP。修改僅測試刺激／期望，RTL/model/harness未因此改動。

第二輪M6 `20261021T003108Z_1588` PASS，最終穩定source再跑 `20261021T004406Z_12107` PASS441：241reference＋39helpers＋160cocotb（N4,W64/256,5seeds,16tests）＋1production-parameter20k smoke。另45strict lint、12structure probes、4XREJECT（POLICY4×N4/8/16及INTERP2），不是功能test counts，未放寬warning。Smoke無W5M closing，明確不能算完整production驗證。

共同baseline六scope實際回歸全部PASS：M1 `20261021T003658Z_4971`331；M2 `20261021T003730Z_5556`571；M3 `20261021T003840Z_7305`595；M4 `20261021T003951Z_9043`475；M4-q1 `20261021T004043Z_10025`195；M5 `20261021T003506Z_3137`850。增加的45modeltests是各scope重複pytest collection，不是額外RTL獨立coverage。先前longMain30stress／60primary／3production本輪未重跑，舊結果僅其歷史source有效；本輪受限採納根據unit／模型parity與generated-code structural比較，不假稱新longregression。

M6-compare `20261021T004131Z_10929`20/20PASS，10pairs（N4,W64/256,seeds509..513），每pair相同intended source／ready／reset hash，總1,920,000tracecycles。W64兩版本fires合計Main223685／Alg2223695，W256 Main443530／Alg2443513；Low-visit fires由147649至180706、290994至369579。每pair的offer與actualpush時序均有差異，不能假裝acceptance完全相同；meanwait在10組中8組Alg2較高，不能由分類較快推出latency/fairness優勢。完整per-run表／JSON與metrics保留。Comparison discovery第一次未找到runner加前綴的artifact，已修正匹配`*__fai_compare_record.json`並加test，6/6script tests PASS；不是丟棄missing records。

原inline WSL batch錯把`$m`展成空而無scope啟動，`unit-regressions-attempt1-VOID-no-milestone-arg.log`保留；改成saved bash script後六scope全完成。`m6-run1/2.log`inline EXIT echoes不可靠，以runner JSON／final saved-script exit判定。Native stop-hook曾因marker未識別擋結束，實際讀hook且在真實PASS evidence後寫verification marker，未waive／delete tracking，最後exit0。

Codex獨立raw audit驗證全部accepted JUnit elements、每run counts與零fail/skip/NOT_RUN；20records的lengths／digests／push/fire/per-source counts／response completion／zerooutstanding、完整10pair矩陣與shared intended hashes／reset/closing positions。最終M6前後source hash一致並對實際檔案核對。審查[ACCEPT_DIRECTED_AND_BEHAVIOR_SCOPE_ONLY](../reviews/phase-4-rtl/codex-fai-alg2-review.md)。證據`.setup-logs/implementation/alg2-20261021/codex-review/unit-behavior-audit.json`，native[focused results](phase-5-verification/M6-results.md)。更新status/tracker與stale local guide pointers；完整Algorithm-2長stress／production與補充PPA仍NOT_RUN，下一步依相同profile補齊，未擴N8/16。

### 長視窗與補充PPA入口後續任務（進行中）

上列受限milestone已提交 `1cec68d8cca6dcb132f000fa72e5de45f3468383`，提交後工作目錄乾淨。接著依既有授權啟動新的native RTL Agent Team `func-verifier`，session `9a30d2e0-4d95-4f42-bb1a-67362c1441ab`，actual`claude-opus-5-5`/medium，無fallback。新task完整prompt/settings/before-hashes/PID/stream/stderr位於`.setup-logs/implementation/alg2-production-20261021/native/`。它獨占驗證與preparer檔案；Codex仍獨占status/本報告。禁止RTL/model/架構變更。

任務為最小共用production/stress harness解讀選擇，N4 Algorithm-2實際20,000,000non-resetcycles／4個W5Mwindows、較長W64/256十組stress，嚴格完整scope gates及Main/M6回歸；另外準備primary-nine之外顯式opt-in的Algorithm-2 N4 PPA入口及boundary/storage/payload tests，保留原profile/Tcl/constraints。實際合成由Codex在功能驗收與clean export之後才執行。預定測試不算已完成，不宣稱production或新PPA結果。

Session9a30d2e0實際在讀取階段收到Claude服務端safety-classifier停止訊息，未修改任何source／test／focused report、未啟動longrun。CLI最終exit0／result success但result文字空白，**不算工作成功**；stderr/stream完整保留，未報quota耗盡，故沒有擅自使用僅針對quota授權的Sol fallback。Codex保持已提交1cec68d成果，改以一次官方focused skill invocation `/rtl-agent-team:rtl-p5s-func-verify M6-long`重試純功能驗證，沒有重送被隱藏的response、改全域route或降低檢查。新invoke logs在`.setup-logs/implementation/alg2-long-workflow-20261021/native/`，允許Skill/Task以執行plugin指定workflow，要求實際agents均Opus5.5/medium與序列寫入。補充PPA入口暫不交給這次純verification任務；仍NOT_RUN。

官方workflow retry session `33d5c612-e591-4b35-83f2-f076cb4c58d7`實際連續10次HTTP429後明確回報「hit your session limit，resets12pm(Asia/Taipei)」，`result.is_error=true`；無Tool執行／source變更。CLI在最終error後仍未結束，Codex核對PID24908的ProcessName/Path確為本task的claude.exe，僅終止此CLI；不冒稱自然exit0。已保存API retry／最終error／launcher exit與diff記錄。這才觸發owner2026-10-20明確核准的quota fallback；未將前一classifier失敗誤當quota。

接續以multi-agent實際指定 `gpt-6.1-sol` / `high`，task `/root/sol_alg2_long`，從既有1cec68d與先前完整task prompt續接，不重建repo、工具或架構。該worker獨占剩餘verification/preparer/comparisonvalidation檔案，禁止spawn其他writer／RTL/model/Spec改動／SSH／commit；parent獨立審查且維護status/本報告。新證據目錄`.setup-logs/implementation/alg2-long-sol-20261021/`；尚未將計畫中的longtests/PPA標PASS。

### Sol延續實際長測試完成與Codex驗收

Sol/high以原Main streaming production/stress機制新增最小解讀選擇，Algorithm-2 literal四視窗state rows由Spec8.6手推，不從oracle算expected；Main defaults/schema保留。新增M6-stress/production gates要求完整非空矩陣、policy/schema/cycles、all16transitions或完整四視窗，missing/subset/smoke/extra/wrongpolicy等以小test驗證拒絕；RTL/model/Spec/DC/PTTcl/profile未改。

M6 units `20261021T010228Z_16709`447PASS（241reference+45helpers+161cocotb），MainM5 `20261021T010341Z_17581`856PASS。M6-stress `20261021T011237Z_23789`10/10PASS，N4×W64/256×5seeds400k/800kcycles，共6milliontracecycles，各run全16state/evidencepairs。M6-production `20261021T011237Z_23785`1/1PASS，實際20millionmeasurednonresetcycles，四W5Mwindows，另57draincycles，共20,000,057nonresetedges。runnerelapsed4136.8s／stress484.8s；longsourcesbefore與afterhash全部一致。

Production新classes按source0..3依序：[BPL,BPL,SH,BPL]、[SL,SH,SH,SL]、[BPH,BPL,BPL,SL]、[SH,SL,BPL,BPH]；Sclose2747980／2749750／2749186／2750244，Bsum各相等。視窗1/3held跨界，2/4closingfire；responses10997179issued/10997179completed，drainoutstanding0。Codex直接審查JUnit／每scopefullgate／countercycles／inequalities／literaltrajectory／all16coverage／sourcehashes，不以agent聲明代替結果；`codex-review/long-functional-audit.json`PASS。

同時準備explicit supplementary-alg2N4opt-in；原POLICIES仍三政策×三N=9，refuse無optin/N8/16/wrongpolicy/錯profile。Payload含6720descriptorbits＋2048timestamps、相同module／boundary，frozenv2profile canonical6f4777f0…。新增comparisonarraylength／digest／binaryfire-reset驗證與fullmatrix標籤，parent重驗前20records10pairs全有效。所有小checks最終329/329PASS，17.75s。PPAinfra Windows40PASS/8platformskips，WSLfinal34PASS/14platformskips/2885subtests；兩host的POSIX／Tclinterpreter測項互補，skip不算PASS，無EDA工具宣稱。

保留失敗：第一savedbash含CRLF；第一WSL PPAinfra1FAIL源自舊assert期望「primary nine」而新guard回explicit opt-in error，僅修正testexpectedmessage未移除guard，parentfinalWSLrerunexit0。Solworker在longtests已完成後，finalturn收到API429並終止，尚未寫focused report／結案，不將該agenterror當測試失敗或完成訊號。Codex接手剩餘read-onlyaudit／infra rerun／報告，以[長測試記錄](phase-5-verification/M6-long-results.md)記載實際source/commands/outcomes。採納LONG_FUNCTIONAL_ACCEPTED，可進cleancommit/export和同方法MainN4/Alg2N4補充合成；目前仍無新PPA結果。無新owner架構決策。

### 同source補充合成／STA啟動

長驗證及preparer提交 `c8e7ea8c0e4530572b3abf5b14ea9958e24f1789`，clean export兩case：MainN4與Algorithm-2N4，profile皆frozenv2 canonical6f4777f0…。兩manifest source／exportedfiles／expectedstorage完全相同，只policyselector與supplementmetadata不同；payload tar SHA256分別c8437759…／e9dbcd56…。每份21ownfiles，無proprietarylibrary/licenses/executables。原primarynine結果保持其source/provenance不被覆寫。

長測試期間SSH master／tmp known_hosts不再存在，首次strictconnect因此拒絕（沒有放寬hostkey）；從先前已批准pinnedkey檔還原並實際核對SHA256:REDACTED，再登入。新backend `fastx4-NN.ews.illinois.edu`。stage兩個全新remoteexperimentdirectories並sha256驗證成功，labels `supplement-20261021-main-n4`／`supplement-20261021-alg2-n4`。本次不重跑原九組，只為新variant準備同sourceMain對照。

2026-10-21UTC02:57:57（Taipei10:57:57）實際啟動遠端serialbatchPID592827，root`~/cxl/experiments/supplement-20261021-pair`，先Main後Alg2，前case失敗即停。batch／case exits/status／host／timestamps都寫在該目錄。log／exactlaunchscript在`.setup-logs/fastx-alg2-20261021/`及既有remotehelperlogs；未改profile/Tcl/constraints/RTL。當下仍RUNNING，不把PID或成功上傳當合成結果；後續須actualDC/PT成功、allowlistedretrieval與independentraw/SDC/storage/library/load審查。

### Algorithm-2 N4補充合成／STA實際完成與採納

Main UTC02:57:58–02:59:51，Alg2 UTC02:59:51–03:01:35，兩組DC/PT/wrapper全部exit0，batchstatusCOMMANDS_COMPLETED_REVIEW_REQUIRED；此marker仍不是最終採納。168ownresultsfiles經既有allowlist取回，無DB/lib/license/executable/DDC；source/manifests/profile/hash/sourceclean已驗證。Main重跑數字精確等於先前primaryv2N4：area110089.845892，sequentialcells9011，setup+10.496409／hold+0.039940ns。

Alg2area110058.332037，sequentialcells9011，setup+10.547482／hold+0.039940ns。同sourcepair總面積差−31.513855libraryunits（−0.0286255783%），policy-subtree7143.9879→7120.8608（−0.323728%），setupslack差+0.051073ns。共同RTL的mappedFIFO／holdsubtrees因mappingcontext略不同，故總差與policy-subtree差分開報，不能把差值宣稱純policygatecount，也不假設libraryunits=µm²／NAND2。僅singlemapping/corner測量，沒有variation/Fmax/power主張。

每組36404timingchecks=36336MET+0violated+68untested，untested均constant_disabled；沒有user/case/looparcdisabling例外。DC及PTsetup/hold/electrical皆MET；每組390temporarymaxcaplimits還原、20undefinedlibraryoutputtargets明列，原DB未改。Codexrawpairaudit重新核對mappedhierarchy/referencearea／full6720descriptor+2048timestampstorage＋commoncounter／allportsclockresetSDC／profile/sourcehashes／completionmarkers／warnings/errors／resultchecksums，保存`.setup-logs/fastx-alg2-20261021/pair-independent-audit.json`。

接著兩組read-onlydriver surveys各exit0，10+10ownreports取回，Main29458／Alg229448useddriverpins全都有positive/defined原始caplimits、0ordinary/CCS超限，9constantpseudodrivers各自另列。Survey不compile／不寫netlist，before/afterSDC/netlisthashes相同。`pair-full-load-audit.json`PASS。UTC03:03:39最後remote唯讀check實際exit0，兩case_RESULT_HASHES=OK且librarySHA256仍844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094，與前次連線收尾timeout歷史不同，本次明確成功。

**採納ACCEPTED_FOR_SUPPLEMENTARY_PRE_LAYOUT_AREA_STA**，與完整N4longfunctional一起完成核准補充milestone。新的[報告](PPA_FAI_SUPPLEMENT_2026-10-21.md)與[JSON](ppa/algorithm2-n4-20261021.json)記錄來源、方法、數字、coverage／限制／agentprovenance，原九組primarydataset未取代。Main與Alg2在20identicalstimulusrecords有明顯selection/acceptancetiming差，但N4總面積差約0.029%、FF相同、timing皆MET，不實質改變primaryhardwarecost結論。依owner「material才擴」條件，N8/16supplementdeferred，無新增owner架構決策需問。Power/activityannotation、physical、多corner、commercialformal仍NOT_RUN，不以功能／areaSTA測量代替。NativeClaude與Sol後續429已記錄；本次補充結果是Codex獨立rawaudits採納，沒有虛構freshnative synthesis-reviewerverdict。

## 2026-10-21 Activity-annotated power能力確認與方法延續

Owner再度要求續推。從clean`abe14394aa6919e7501c2db67e70459ee1a605f7`核對既有sole repo、approvedspec和已驗收area/STA；依Spec11「supported時attemptactivity-annotatedprelayoutpower」接續，不開新RTL/架構。NativeCLI已是2.1.305，RTLAgentTeam仍0.14.6啟用；實際power-analyzer invocation要求Opus5.5/medium，log`.setup-logs/implementation/power-method-20261021/native/`。連續10次HTTP429後明確sessionlimit/reset12pmTaipei，沒有實際inference/model欄或review，CLIexit1；不能把requestedmodel當已產生分析。依ownerquota授權改spawn`/root/sol_power_flow`，modelgpt-6.1-sol/efforthigh/forknone，獨占新verification/powerinfra，parent獨占report/status與SSH，無共同檔案衝突。

SSH使用既有approvedpinnedkey重新登入FastX-NN。第一次remotehelper在master尚未登入完成就執行，exit255，保留而重試；tool discovery的`find|head`受pipefail得到141，只是SIGPIPE，不是工具/授權缺失。後續改用精確probe。第一猜測`saed32nm_rvt.v`不存在，probev1exit2；保留後搜尋同RVT目錄，實際檔名`lib/rvt/verilog/saed32nm.v`，hash`d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286`，RVTmodule名確認；沒有下載/改寫任何cellmodel。

實際PTW2024.09 `power_enable_analysis=true`並checkout`PrimePower`license，`read_saif/read_vcd/report_switching_activity/check_power/update_power/report_power`均可用，mappedMainN4link成功。初probe讀SDCdefault版本產生2warnings，原因為已發出的SDC2.1與tooldefault不同；下一probe顯式`read_sdc -version2.1`，不靜音warning或改constraints。Detailedhelp直接來自現場tool，smallsyntaxreports保留於`artifacts/fastx/power-pt-syntax-20261021-v1/`，不是猜測API。

遠端VCS實際編譯既有mappedMainN4＋原remoteRVTmodel＋ignoredcapabilityTB，`-full64 -sverilog +delay_mode_zero +notimingcheck -debug_access+all`，compile0／sim0。三個resetedges後100idlecycles×25ns，透過`$set_toggle_region(tb.dut)`／`$toggle_start/stop/report`產生5.1MBSAIF，TIMESCALE1ns／DURATION2500，exactscope為tb/dut。Logs`artifacts/fastx/power-saif-smoke-20261021-v1/reports/`及`.setup-logs/power-20261021/saif-smoke.sh`。**這只是gateSAIF能力smoke，沒有workloadpower/coverage/functional/physicalsignoff主張**；後續必須真實pinreplay對independentmodel、排reset/drain活動視窗、驗annotationcoverage/default來源，zero-delay不含SDF/glitches/physicalclocktree。

### RR N4 workload pilot與工具回報校準

Sol/high完成獨立model pin-vector exporter、共用gate replay TB、isolated PTpower Tcl、runner、evidence checker及method文件，source凍結後parent才上傳。Windows7/7小測試、WSL6PASS/1明確Tkinter skip（Windows已覆蓋）、bash syntax、Verilator5.052 isolated stub syntax零warnings；這些不是gate功能結果。Native power-analyzer quota失敗已記錄，無虛構native review。

實際FastX pilot `power-20261021-rr-n4-pilot1` compile/sim/PT皆exit0；100,000cycles全105bit/source/ready/valid四態逐cycle比對成功。接受72698、fire72634、截止outstanding64（每source16），來源intendedtrace98db926f…。三resetedges在外，無drain，SAIF tb/dut、1ns×2,500,000duration。起訖negedge的事件排序留下199999clocktransitions、TX0，各6782FFclockpins皆file-source0.0799996transitions/ns；這是固定2.5ms窗的endpoint效應，不虛報200000。21276/21276nets與20660/20660leaf完全標註；toggle/static兩表全file、zero defaults/propagated/unannotated，427primaryinputnets亦全file。仍不等於每個內部state皆被激發。

原checker要求字串`check_power succeeded`，實際W2024.09輸出2out_of_range ramps/1load和0，故shell exit1且matrix停止。原attempt及rawreports完整保存，未抹除失敗。獨立diagnosis `power-rr-n4-pilot-diagnosis1` PTexit0證明兩ramp為共同hold未使用RRcontext `i_cand_ctx[0]`的constant0，兩pin實際toggle0/file；load0為`o_grant_ctx[0]`無loadpins，toggle0/file。disabletiming僅propagatedconstant，PTE-003保留；不是user exception或timingloop。本項保留作librarytable低端外插的限定，不能宣稱check_power乾淨PASS，也不改原netlist/constraints以消除warning。

VCS6736個TFIPC warnings逐項核對：6735DFFX1_RVT省略QNoutput、1共同hold省略o_grant_held output；remote唯讀modelportquery實際確認D/CLK均input、Q/QN均output，沒有下載model。所有被警告instance的必要inputs完整，無其他warningcode／runtimeerror，未靜音。Parent `.setup-logs/power-20261021/audit_case.py`核對每個FFclock、所有warninginstances、coverage來源、powerWunits、sum rounding、immutablehashes，pilotaudit保存；raw SAIF留FastX。Pilot total2.600e-3W僅此coldreset/zero-delay/prelayout/workload的有條件估計，非production/physical/glitchsignoff或FAItrained結果。新checker依現場格式修正後須重跑小測試、凍結source；九組正式matrix目前尚未啟動。


### 九組活動標註功耗實測完成與受限採納

Power tooling提交`f1e58de`，checkpoint提交`c0658fbad1ade809821809306adb4b62e1bff235`；九組向量均從clean c0658fb產生，source/file hashes逐項封裝；同N intended trace相同，policy-dependent actual接受序列分開保留。僅使用既有primary-v2 source759f86b的mapped netlists/SDC，不重新compile，不改RTL/model/Spec/profile/DC/STA。Native power-analyzer先前quota失敗、owner授權Sol/high fallback與parent獨立執行／採納仍如上記錄，沒有fresh native power review verdict。

FastX-NN serialbatch UTC03:50:55–04:07:10（Taipei11:50:55–12:07:10），九組VCScompile/sim/PT/wrapper全部exit0，每組100000checkedcycles/2500000ns，共900000cycles。N4 aggregate接受/fire72698/72634，N8 75764/75637，N16 76131/75908，三政策各N總數相同但RR各source實際population不同，不把sameintendedtraffic當sameacceptance。截止未drain，outstanding總數64/127/223。Main全部allH、無W5M分類邊界；productionlong功能證據不等於此短活動窗已訓練。

PT報告總功耗mW：N4 FCFS3.397/RR2.600/Main3.500；N8 6.728/5.175/6.924；N16 13.4/10.3/13.8。保留原報告精度，不能補造有效位數。N16 RR最初parent加總assert以固定0.1%判斷而失敗，實際PT總值只印0.0103W；修正獨立audit，使用每欄最後顯示位數的半個量化單位相加作精確rounding bound，保留delta/bound及原string，非放寬功能test。所有九組以最終audit重驗PASS。Internal包含clockpinpower，但沒有CTS／routing／SDFglitch；不可當實際chip／productionpower。

553754/553754nets的toggle/static兩表皆activityfile-source，default/propagated/unannotatednets0；172007個FFclockpin逐一file-source0.0799996/ns、SAIF199999TC/TX0。70個未完全標註leaf精確對應literalconstantcellpins；獨立remote九case診斷exit0，逐pin確認impliedtoggle0與正確static0/1，clockfile-rate/.5已知。Implied是這些無net的constantpins，不與nettable的0implied混稱。三個resetedges在窗外，但start的resetdeassert轉換包含一次；文件已明列。

FCFS/RR六case check_power result0，皆2ramp/1load；remote逐case connectivity/activity診斷證明18個issuepins皆zero-toggle/file、constant0，涉及unusedcandidatecontext與無loadgrantcontext。Main三case check_power result1。所有warnings保留、有條件外插估計，不宣稱cleanpowercheck或signoff。PTE-003所有actualdisabledarcs僅propagatedconstants，沒有user/loopbreaking例外。171145個TFIPC逐instance/實際mappedmodule port signature核對，全部是unusedoutputomissions，無requiredinputmissing；原library四種DFFports的remote唯讀query均成功，未下載model。

九case各27ownreports＝243files，另finalhashcheck7files、diagnosis19files經allowlist取回。MainN8第一次在PT尚未結束時只取回14files，audit正確因missingptexit拒絕；此partial目錄保留，完整27files另取`power-fai-main-n8-final`，只有final採納。Parent warning-audit第一次只支援RRporttypes而拒絕FCFS comparator／第二DFFtype，改成按mappednetlist完整module介面與實際line查接線；沒有略過未知cell。第一次diagnostic audit對內層idx使用top相對名而查不到，改成唯一hierarchical suffix匹配並assert唯一；最終70constantcells/18rangepins全確認。另早期inline文件更新碰Windowscp1252讀取失敗，沒有覆寫文件；改用saved UTF8 Python完成。這些是保留的infra失敗，非隱藏RTL修正。

Final remoteimmutablecheckexit0，九組acceptedmanifest/netlist/SDC/config與poweruploadedsource、DB/modelhash皆未改，stageexits全0。RawSAIF留FastX。獨立完整audit在`.setup-logs/power-20261021/*-independent-audit.json`，含rawreportsha、units、roundedcomponent核對、clock/pin/annotation／source hashes；最後dataset[power JSON](ppa/power-20261021.json)與[power report](POWER_RESULTS_2026-10-21.md)可供總報告引用。原area/STA與frozenprofile的歷史power.status不改，另建本dataset。

採納**ACCEPTED_AS_QUALIFIED_COLD_RESET_PRELAYOUT_ESTIMATES**，不叫physical／multicorner／trainedFAI／Algorithm2power／commercialformal完成。Windows9/9 focusedchecks、WSL8PASS+1Tkinter skip互補；parent再跑Windows9/9、九組rawaudit與九組診斷／hash成功。Spec/RTL/model/原synthesisprofile不變，故未重跑既有longfunctionalregressions。下一milestone為從已驗收功能、九組area/STA、N4Alg2補充及受限power資料整理總報告；若需主張適應後FAI功耗，另做真實長活動窗及多seed，不能以本批代替。沒有新的owner架構決策。

收尾UTC04:13:35最後readonly遠端命令exit0，九份原SAIFhash與採納audit逐一相同，所有immutableinput再次sha256check通過。互動SSHshell收到exit後顯示sharedconnectionclosed（launcher exit1，非EDA結果），確認taskmaster PID769仍在後，以同一pinnedkey/socket的`ssh -O exit`明確關閉，只處理本task連線。最後文件檢查覆蓋新report／JSON／method的本地links、完整九矩陣/來源/量測數字/rawhashes、Spec/RTL/profile無diff與Gitwhitespace；不以文件檢查代替新功能回歸。

## 2026-10-21 補齊必要測試：多seed與真實分類後活動

Owner要求「繼續補齊需要的測試」，由clean4007f99續接。既有Main N4/8/16 production60millioncycles／Algorithm-2N4 production20millioncycles已驗收，不無故重跑。實際缺口為新powerflow只有cold100k/seed509；規劃新增seed510/511的同矩陣coldgate replay，及N4Main真實9,999,500cycle預熱+100000cycle活動窗（跨第二個W5Mclosing、接續分類後狀態），同N4 FCFS/RR用相同intendedproductiontrace對照。不得縮W／預載／跳時間；舊九組dataset不覆寫。預定工作不是PASS。

NativeClaude Code2.1.305／RTLAgentTeam0.14.6已實際查驗，啟動func-verifier session40d98956-6075-445a-974d-f310ee13d3b7，invocation-local Opus5.5/medium，stream真實modelclaude-opus-5-5已確認。Prompt／settings／beforehashes／PID／stream／stderr保存`.setup-logs/implementation/power-extension-20261021/native/`。唯一nativewriter擁有powerexport/check/TB/runner/tests與focusedplan；parent獨占report/status／SSH／獨立審查。先做boundedinfra／v1相容性／guard／phase-accounting測試並凍結，再由parent批准實際完整export／remoteexecution，不能把小Wfixture當production。

新SSH第一次因tmpknownhosts不在而strict拒絕，沒有關閉檢查；從先前已核准pinned檔重驗SHA256:REDACTED並還原，再登入成功。ActualbackendFastX-NN，UTC04:20:20preflightexit0，VCS/PT路徑存在、原DB844d4474…與cellmodeld4bf5a3e…hash不變，home25GiB尚餘約23.5GiB、三N4acceptednetlists存在。沒有新EDA結果或library下載；credential不存檔。後續依真實test／longrun結果更新。

### Native補測中斷與授權fallback

第一native session40d98956實際只寫partial `scripts/check_power_replay.py`／`scripts/export_power_vectors.py`，尚未完成TB／runner／測試，對話壓縮後API safeguards以reasoning_extraction中斷，exit1。保留diff／所有stream，沒有將partial當可用或改用Codex寫RTL。以新的精簡focusedtask重試，logs`.setup-logs/implementation/power-extension-resume-20261021/native/`，actualclaude-opus-5-5/medium；此session後來明確HTTP429weeklylimit（Oct22 15:00Taipei reset），resultis_errortrue／CLIexit1，沒有完成新測試。

這次明確quota訊息才觸發owner已核准fallback，接續既有`/root/sol_power_flow`，保留其明確gpt-6.1-sol/high設定，由同一熟悉原powerflow的worker完成partial及小測試；兩nativewriter均已退出，無同檔並寫。新evidence `.setup-logs/implementation/power-extension-sol-20261021/`，parent仍獨占報告與remoteEDA。只規劃bounded驗證＋freeze，full10Mexport／commercial補測尚未啟動。

### 獨立 RTL/netlist Formality 檢查接續

既有review指出commercial equivalence未做，故parent獨立補正確性驗證。FastX-NN實際fm_shell W2024.09啟動exit0，工具help取自現場，不靠猜測license或API。原acceptedcase保留default.svf，可直接以各case自帶RTL／manifest／相同params及原DB比較已採納netlist，不重新合成。這是Codex獨立review活動，非替代Claude/Sol設計RTL；orchestration scripts/logs在ignored`.setup-logs/power-20261021/formality-*`，驗證結果須後續rawaudit後採納。

最初RRN4pilot1因先載入implementationDB再切reference而FM-236/無reference停止；不是RTL不等價，exit1與報告保留。修正readreference+set_top先行，pilot2實際6893comparepoints等價；但auto_setup啟用的undriven策略需核對，故pilot3使用synopsys_auto_setup=false、verification_verify_directly_undriven_output=true，保留defaultbinary:X，仍6893PASS、0failing/aborted/unmatched、1constantreg未比較。Dont_verify/userconstants皆None。scope限定的blackbox報告與setupstatistics確認實際switch無blackbox；整庫未使用的power-cellmodel warnings另留，不將全library blackbox表誤認activehierarchy。中間WindowsCRLFsavedbash在set-pipefail前拒絕，無任何EDA啟動，改LF後才執行。

接著啟動同嚴格設定primary9 serialbatch，UTC04:29:33開始，timeout15min/case、failure即停，仍RUNNING。負向控制另複製RRN4mappednetlist僅反轉topo_out_valid，沒有修改production來源；實際verifyFAILED，唯一failure精確o_out_valid，6892其餘PASS、0aborted/unverified，外層EXPECTED_MISMATCH_DETECTED／exit0；此證明checker可抓錯，不冒稱該故意突變case等價。各case含sourcebefore/afterhashes、原RTLmanifest／SVF／DB，reportsetup／guidance／constants／dontverify／status，獨立postmatchdiagnostics用來列undriven網路。原power與area/STA資料不覆寫。

### Formality十四案例完成、獨立採納

primary9全部完成UTC04:50:57；supplement Main/Alg2N4 pair完成04:40:31；currentMain C8 RTL對原759mappednetlist bridges N4/8/16最後04:54:17完成。14/14 fm_shell exit0、verify_return1，0failing/aborted/unverified/unmatched/activeblackbox/userconstants/dontverify。FCFS/RR primary六case各1constantreg未比較，其他0；passingDFF+constantreg與registertotal逐項一致。primary9 postmatch diagnostics皆0undrivennets；setup前implementation可有未連接leftovers，原undriven.rpt在match前不可用，兩階段不混稱。原嚴格auto_setup=false/binary:X/直接undrivenoutputverify不變。參考七RTL檔逐一對Git blob SHA，mapped/config/manifest/DB/SVF等before/afterhash及14次finalremotehashcheck全部通過（UTC04:59:54）。全部rawreporthash／warnings／SVFguidance保留[JSON](ppa/formality-20261021.json)，詳見[equivalence報告](FORMAL_EQUIVALENCE_2026-10-21.md)。這是specifiedsource/param RTL-netlistequivalence，不是英文Spec formalcorrectness。N4 lexicalnetlist比較失敗由直接semanticbridge解決，沒有謊稱textequal。獨立postmatchaudit初用錯誤零網路字串而拒絕，讀raw後改成實際0 Undriven nets:，再全14重新audit成功。

### Power補測工具凍結與parent複驗

Sol/high完成六個assignedfiles後freeze，沒有RTL/model/Spec/profile/sta變更，沒有SSH或commercialtest。parent檢閱export/check/runner/commonTB/test及命令結果，獨立Windows23tests=18PASS5明列simulatorskips，WSL23=22PASS1TkinterTclskip（Windows補足）均exit0；bash-n通過。三policy實際RTL strictVerilatorbuild零warning、各768cyclephasefixture，共2304cycle；actuallegacyRR100k；14格式／pinmutation拒絕；Icarus真正四態Xready/valid/source/full105/clock五拒絕及knowncontrol／fixtureproductionguard通過。沒有-Wno-fatal或縮productionW來報結果。原v1defaultgzip/plaintextbitwisehash相同；18coldcase與三productionboundary此刻尚未跑。證據.setup-logs/implementation/power-extension-sol-20261021/READY.md、parent-windows-tests.txt、parent-wsl-tests.txt與parent-simulator-runs/。

原nativepartial經owner明確授權GPT6.1Sol/high接續，非freshnativePASS。保留timescale/Icarus/sscanf/fixtureassumption失敗修復、worker-final.diff及source-hashes-final.json；parent僅改plan中「explicitly requested」為cold-only/singleseed缺口說明及clocknotation，沒有code功能修正。凍結後預計cleancommit再full10Mexport與commercialruns；只有實跑完成及rawaudit後更新結果。Boundary活動窗為刻意跨classification的100k sample，classification頻率1/100k不是natural1/5M，不能當productionaveragepower。

### Clean export、實際補測啟動與中途核查

凍結提交43bf9755810cb5ce920b14cc16deb258f352f150，Gitclean後WSL產生18cold510/511 exports（UTC05:01:10–05:02:55），各100kcycle；Mainboundary export05:01:10–05:09:02，FCFS05:11:21–05:16:53，RR05:16:53–05:22:36，各10,099,500actualmodelcycles、warmup9,999,500＋measure100000，W5M不縮窗。三boundarygzip各約208MB、streamtar/upload/hash檢查，只傳六個project-ownedfiles，原DB/model/netlist/SDC不動。所有實際exportexit0、clean來源43bf975，literal兩closing與held/fire/S=sumB/clear核查成功。Main第一closingB=(883155,881279,102611,883078),S2750123且heldHigh/source3/used5；第二B=(1099386,103310,447616,1097318),S2747630含closing source3 fire，classes下一cycleL,H,H,L。量測model High44207fires、Low10901fires；這些先是model evidence，尚不能當未完成gate結果。

獨立streamingpin比較：六coldseed/N FCFS/Main pair共600k列一致；boundary pair前10M列相同，第一次差異正好global10000000，第二closing9999999的下一cycle；之後11173列不同、validsource9589、validfull105 11169、inputready571、inputvalid94、inputdesc924，sinkready與outputvalid零差異。相同intendedproductionhash f231af66…；actualacceptance/backpressure差異分開保留。這是檔案關係檢查，不灌水成新增RTLcycles；待各gate rawaudit成功後才把兩者綁定實際pin結果。

FastXseed510RRN4先pilot（05:02:17啟動）compile/sim/PT/shell0，actualrawaudit通過後才啟動17case serial補測05:04:29，fail即停。N4Main長gate05:12:18、FCFS05:18:46、RR05:26:03分別nohup啟動，各獨立exclusiveexecution、不縮warmup、三小時outerbound，PT仍1core；截至UTC05:27尚RUNNING，不報power結果。已完成coldcases逐一allowlist取回與audit，14/18通過；monitor-cold.py（local session84045）與monitor-boundary.py（18705）保留remotequery/audit/fetchlog；jobs與PID在各remote batch檔，斷線亦保留。首Mainstarter因Windows generated CRLF在set-pipefail前拒絕，無EDA啟動；生成器改明確LF並在local remote.py加CR字元拒絕，修後成功，原失敗保留。

額外唯讀SAIF核查發現cold初始化TX不能等同fileannotation已知。RRseed510N4 pilot29731個SAIFrecords中21841曾TX、0TZ；最大資料record初始化TX1287ns，另rot_valid[1]全窗TX。獨立PT實際確認gen_policy_rr_u_rr_sched/rot_valid[1]為1net/0pins/0ports孤立宣告；不是有效介面X或activeundriven。原四態逐cycle有效介面比對通過，clockTX0。不要將alias/port重複record數當uniquePTnet數，也不以此估算power加權誤差。準備21case同樣knownness＋constant/range-pin診斷，須全測完後實跑。初inspector未支援DURATION2500000.00而拒絕，修正為實際數字格式，knowncontrol＋3個hierarchy/residency/truncation突變拒絕通過；原probe failure保留。

另發現Synopsysmodule把timeout解析到自帶cmlp/cerberus版本，已完成的case留20m idlewatchdog（bash parent只有sleep20m child）。沒有影響已完成的EDAexit。後續RRstarter明確/usr/bin/timeout；不改任何runner/PT方法。嚴格驗證本task run-owned.sh命令、同UID、completedcase cwd、run-status及shell_exit0、唯一sleep20m/3hchild後，只清理8個已完成own idlewatchdogs，未終止activeEDA或licensehelper。最後還需在全部完成後再清理剩餘ownwatchdogs。禁止廣泛pkill或清理其他工作。

FinalFormalityhash時間精確為UTC04:59:54開始、04:59:55結束；早先JSON「at04:59:54」指啟動，最終文件會用區間更正。所有accepted14sourcehash仍未改。下一步完成18cold＋3boundary gate/SAIF/PT，診斷42rangepins與literalconstant/alwaysXrecords，再finalhashcheck、結果report/JSON、更新statuses與commit；不得以RUNNING/PID代替PASS。

### 補測實際全部完成與受限採納

18coldseed510/511所有compile/sim/PT/shellexit0，pilot＋17case batch最後UTC05:36:40完成，parent18rawaudits05:37:19全通過。新增1800000checkedcycles；逐組原netlist/SDC/config/manifest、uploadedTB/checker/runner/PT、gzip/plaintext、DB/model起訖hash皆相同。三policy/N/seed grouping intendedhash一致，FCFS/Main cold600krows相同。三個coldseed總功耗排序均RR<FCFS<Main，N16列印精度有限，不能宣稱數值完全相同或statisticalsignificance。

真實boundary gate三case每組10099500cycles、warmup9999500＋measure100000，無減W/預載/跳時間/phasecutreset。FCFS05:18:46啟動，完整gate CPU1595.91秒；Main05:12:18啟動、RR05:26:03啟動。各1Mprogress、全部validfull105/source/ready/valid逐cycle與independentPython一致。FCFSrawaudit05:46:36、Main05:50:42、RR05:52:45成功，全三compile/sim/PT/shell0。總新增gatecycles32,098,500，warmup29,998,500＋measured2,100,000，勿把model export或pin檔比較再加成RTLcycle。Main過兩次實際productionclosing，模型B/S/ctx/classes符合literalexpectation，gate外部pins一致；TB沒直接probe mappedclassregisters，藉既有RTLproductionprobes＋Formalitybridge補強，不能冒稱有新internalgateprobe。

N4boundary PT totalmW FCFS3.383/RR2.586/Main3.495，三case measured接受55109/fire55108，per-source及cut/end populations分別保存。Main modelHigh44207/Low10901fires，不當作gate直接classprobe。窗內分類頻率1/100k比natural1/5M高50倍，是boundary-focused sample，不是steady-state/productionaveragepower；cold與此workload不同不能用差額隔離classifierpower。原seed509primarypower9／areaSTA／profile歷史status不改寫，新dataset獨立保存。

21case independentrawaudit累計1,186,585nets toggle/static file來源、368,663FFclockpins全file，clockTC199999/TX0、duration2.5ms，每組100k量測risingedges。206literalconstantcells逐pinimpliedstatic/toggle與clock核對，42rangeissuepins皆unusedconstantcontext/zero-loadcontext、toggle0/file。Main7case check_power1，其餘14case仍各2ramp/1load且result0，保留qualifiedtableextrapolation限制。366814TFIPC逐instance確認unusedoutput omissions，無必要input缺接；PTE003僅constantarcs。原unannotatedleaf不報100%coverage，fileannotation也不是全state激發或全程known。

SAIFknownness21份完成：cold有限transientTX、最長單record82737ns（3.30948%窗，非powerweightederrorbound），預熱後三measurement窗transientTX0/TZ0。1476case-localalwaysXrecords逐net唯一解析、0leafconnections/0topports/hierpins僅out；包含孤立rot_valid與unusedcomparatoroutputs。原0pins要求發現hierout1pin後拒絕，獨立PT report_net證明0driver/0load再按實際leafconnectivity收斂，全部21重新診斷；不是略過activeunknown。SAIFalias/port重複不能當unique-net數。ColdTX推定未resetstorage在未寫入/invalid期，residency摘要本身沒有time位置，不能宣稱已直接定位每段X時序。

獨立診斷的失敗與修復：DURATION實際小數格式最初parser拒絕；module選舊Python無removeprefix而exit1，改compatible slicing並重驗knowncontrol/3mutations。diagnosis3完整21loop exit0，但parent檢閱最終PTsummary抓出6errors，追到redirectedN16 reports的empty get_cells SEL005（這三netlist沒有DFFSSRX literalconstantcell），原audit只查主log而漏掉。已撤provisional採納文件並保存ignored版本，改quietcollection＋明確CONSTANT_CELL_COUNT=0、只重跑受影響6N16的完整唯讀診斷。最後每份採納pins/saifreports逐檔Error/Fatal0、修復PTsummary0errors，再重新audit21全通過；沒有用exit0/marker掩蓋errors。歷史原nine-diagnostics亦有同類3emptyqueryerror，本次對相同N16netlist補足0inventory證據，原measurementvalue/raw不覆寫。

採納diagnosis15case用artifacts/fastx/power-supplementary-diagnostics3/reports，6N16用diagnostics4-n16/reports；原失敗保留。Final21immutableinput＋SAIFcheck UTC05:53:05開始exit0，另postreviewUTC06:01:55再核14Formalityinputs／21powerinputs及SAIF全不變。原DB/model均未下載／更動。各ownremotejobs完成，嚴格identity/cwd/exit確認後清除19個completedidlewatchdogs（17coldvendor20m＋2boundaryvendor3h），GNUtimeout RR不留此問題；無activeEDA或licensehelper終止。NativeOpus5.5mediumpartial/guard、freshweekly429及ownerSolhighfallback皆保留，無新nativePASS背書。

本地parent23testcases在Windows18PASS5simskips／WSL22PASS1Tclskip互補，五codeSHA與43bf975一致；執行時HEAD4007f99待提交，不能說當時clean43bf975。ActualstrictRTLfixtures2304cycles／v1RR100k及14mutation／5trueXrejects為infra證據，不當productionresults。最後檔案／JSON／links／source/status一致性查核另留local log；RTL/models/Spec/profile/PT自freeze不變，沒有無故重跑已採納longregression。

完整新[補充結果](POWER_SUPPLEMENT_2026-10-21.md)、[機讀資料](ppa/power-supplement-20261021.json)、[Formality](FORMAL_EQUIVALENCE_2026-10-21.md)已備總報告使用。採納QUALIFIED_SUPPLEMENTARY_PRELAYOUT，非physicalsignoff／英文Specformalcorrectness；APR、SDFglitch/CTS/multicorner、Alg2power、trainedN8/16及更廣workload仍deferred，沒有新owner架構決策。下一milestone整理總報告，並保留以上限制。

最終N16六case修復query UTC06:03:23啟動、06:07前後完成exit0；實際PTsummary只印「4 warnings,119 informationals」而省略zero-error欄位，所有case pins/saif與主log逐檔沒有Error/Fatal，非硬要求工具一定列出字串0errors。原6emptyqueryerrors仍保留superseded目錄與provisional文件。補充finalaudit、rawhash、doclinks/count/sourcecheck均通過，UTC06:08:11最後FastXreadonlyquery確認activeownedpowerbatches為空。之後明確ssh -O exit只關本taskmaster，control命令exit0／Exit request sent；原互動shell隨之sharedconnectionclosed/launcherexit1，這是關線不是EDA失敗。沒有activewriter或remotejob，credentials未存檔，所有需補測項目已完成而限制仍明列。


## 2026-10-21 Academic final report / LaTeX delivery

Owner requested an academic total report matching the first progress report, then explicitly
selected LaTeX editing/rendering. Work continues in the sole existing repository from clean
9141dfe3303d60b2f00747811eee80cb16db7269. No Claude/Opus, SSH, synthesis or scheduler simulation
was launched for report preparation. Codex authored the manuscript and independently checked
accepted evidence; no RTL/model/Spec/profile/result-dataset change.

The actual parent-folder ECE509.pdf is a five-page English two-column progress report with the
title Hardware Implementation and PPA Evaluation of CXL Switch Schedulers and author line Jay
Chiang / Daniel Chou. All five pages were extracted/rendered/inspected. The supplied eight-page
FAI-CXL PDF was also available now: metadata and Algorithm2 page5 were read, with the complete
page visually inspected; BLISS metadata/abstract supplied contextual related work. The PDF
hashes and precise inspection scope are in docs/final-report/README.md. Historical Spec approval
statements about then-unavailable PDFs were preserved, not retroactively rewritten. Algorithm2
stored-target state operations agree with the approved supplementary interpretation; the paper
does not uniquely fix our one-output10/10 schedule. No new architecture decision follows.

Created a dedicated docs/final-report LaTeX project using the desktop project tool, kept its
main.tex open in the native editor and actually compiled it successfully. Source follows the
progress report's Letter/Times/two-column/numbered academic layout; includes abstract, related
work, common framework, policy semantics, functional/equivalence evidence, frozen methodology,
primary area/STA, qualified power and derived whole-switch energy, Algorithm2 supplement,
threats to validity, conclusion, factual AI-use acknowledgment, references and reproduction
appendix. Author names follow the supplied title page; no human contribution allocation invented.

Numerical table rows and PGFPlots vector coordinates are generated from five accepted result
JSONs plus the frozen profile by standard-library-only generate_results.py. Canonical input
hashes are pinned; complete matrices, margins, equivalence outcomes, shared traffic hashes,
power ordering and fire counts checked. Repeat generation is deterministic. An in-memory
one-unit primary-area mutation is rejected before writing, with original JSON/output unchanged.
Do not count these reporting checks as new RTL coverage. Energy uses reported total watts times
measured seconds divided by measured fires; leakage included, printed N16 precision respected.

Native editor compile success and standalone MiKTeX25.12 PDFLaTeX final two-pass exit0 were
actually observed. First local export used the wrong relative generator path and stopped on
missing fancyhdr with installer disabled; corrected the path and replaced that dependency with
standard page styles. No package/system install. Bitmap default monospace was replaced with
embedded Type1 Courier. Draft float/justification/orphan issues were fixed and all final eight
pages rendered at125dpi and inspected. Final log has0overfull/0underfull-vbox/0undefined refs or
citations/0missing glyph/0LaTeX errors;15underfull-hbox notices remain, paragraphs visually
reviewed with no clipping/overlap. MiKTeX update reminder retained, no update performed.

Local delivery output/pdf/cxl-scheduler-final-report.pdf:8pages,177632bytes,SHA256
89e16f6debdb60704bcfb4140032df7c913d03ac9785fbd14cb575b5bc6e50ed. All9fontsubsets embeddedType1,
noType3. Exact inputs and final checks in generated/evidence_manifest.json and QA.md. PDF/build
products are ignored; editable source/generated table inputs and QA are tracked and reproducible.
Source main.tex is multifile, include generated/results.tex when moving it. Raw commercial
artifacts remain ignored/local and require deliberate archival for transfer; no proprietary
libraries, models, licenses or credentials added.

Report consolidates actual accepted primaryv2, supplementaryN4,14Formality pairs,27cold and
3true-boundary power cases without mixing old pilots or treating repeated exports/tests as new
RTLcoverage. Explicit limits:140constant-disabled timing checks, FCFS/RR table-range warnings,
coldtransientX,50xboundary-eventdensity, noFmax/fullCXL/generalizedfairness/physicalsignoff,
Algorithm2power/trainedN8/16/naturallyweightedlongaveragepower deferred. Owner wording and any
course-specific submission/page-limit check remain; no submission or grade acceptance claimed.


## 2026-10-22 Application-performance evaluation plan (not executed)

Owner requested planning three-policy same-application IPC/throughput/speedup,
application slowdown, latency/fairness and memory-bandwidth/link-utilization comparisons.
Codex used ARS experiment-agent plan guidance inline, with current project context rather
than reopening approved architecture. Added docs/APPLICATION_EVALUATION_PLAN.md v0.1;
status PLAN_ONLY/UNVERIFIED, all implementation/runs NOT_RUN. No Claude/model delegation,
SSH, simulator installation, trace download, RTL/model/Spec/profile/result modification.

The checkout already contains uncommitted final-report/literature/section changes at entry;
those were read for context and left untouched. New plan is a separate document linked by
additive STATUS/PROGRESS_TRACKER entries. It is not a claim of revised PDF compilation or
adoption of pending manuscript content as verified application evidence.

Plan distinguishes open-loop descriptor traces (identical intended timestamps/ready hashes,
different acceptance allowed) from closed-loop CPU/memory comparisons (same application and
initial model, policy-dependent request/ready timing caused by completion feedback). Defines
matched pooled-path alone baseline, normalized IPC, weighted/harmonic speedup, maximum/mean
slowdown, Jain on normalized progress with zero-progress handling, generation/acceptance
latency cohorts and drain/censoring, useful-byte backend goodput versus M1 slot utilization.
105-bit descriptor/32-bit payload/Length do not establish transferred cacheline bytes. Proposed
64B/request external mapping gives an analytical2.56GB/s dispatch ceiling at25ns, not a CXL
line-rate or measured bandwidth claim. Real wire utilization needs an explicit link model.

N4-first proposed4mixes*3sourceplacements*3policies=36shared runs plus keyed isolation runs;
not36independent samples, not an automatic full sweep. Production W5M retained, warmup and
measurement windows explicit; CPU and switch cycle domains separate. Frozen timestamp lifetime,
32-bit address mapping, memory-controller policy and feedback/return-path assumptions retained
as adapter validation items. No guarantee FAI will improve aggregate throughput or fairness.

Official ChampSim and CMU-SAFARI/ramulator2 READMEs searched/opened2026-10-22 to establish
candidate instruction/IPC frontend and DRAM timing-backend roles. Candidate versions and actual
coupling remain unverified, no existing project adapter claimed. Existing BLISS supplied PDF
Sec6.3 was consulted for metrics context, but no new external performance numbers were reused.
Plan formulas, pairing/cohorts, local links and matrix arithmetic checked independently; these
are document checks, not simulation or application validation. Owner choices remaining: A-only
versus Bclosed-loop scope, actuallegalapplicationtrace/inputset, fixed64Bgoodput/slotutilization
versus addedCXLwiremodel. No fixed hardware architecture decision was reopened.

## 2026-10-22 — Owner-scoped descriptor performance gaps closed; Final untouched

Owner confirmed descriptor-level RTL/project-owned workloads only; gem5 deferred, Algorithm-2
supplementary and outside the primary matrix. Latest steering explicitly holds Final edits/builds.
The old v0.1 application plan is superseded by v0.2; no application/byte/link decision is needed
for this stage. No new RTL/architecture, reference model, Spec, synthesis profile or PPA change.

[Evidence inventory](performance/EVIDENCE_INVENTORY_2026-10-22.md) records reusable/incomparable
and missing evidence, failures/incomplete siblings, exact accepted run/source hashes. Actual audit
verified180 archived primary and44 long/stress raw JUnit jobs; regenerated60 primary trace groups
match complete summaries/hash. This is0 new RTL cycles. Original Main production3x20M and
stress30cases are reused, with production9/16 bins versus stress16/16 explicitly separated.

Actual Claude Code2.1.306/plugin0.14.6 invocation of focused
`/rtl-agent-team:rtl-p5s-func-verify descriptor-performance-phase-gaps`, requested Opus5.5/medium,
session6f0f88a0-fc44-44b5-b154-cf1ceab97f0a failed exit1 weekly429 before implementation.
Owner-authorized GPT6.1Sol/high fallback wrote passive recorder/common-TB observer/hand tests;
Codex reviewed independently. Fallback frozen before full replay; no concurrent source writes.
Native prompt/settings/stream/stderr/exit, fallback diff/hashes/pilots and parent commands/JUnit
are preserved in ignored .setup-logs/implementation/descriptor-perf-20261022. No native PASS claim.

Three actual N4seed509 infrastructure pilots100k each pass (M3:20261022T002800Z_277;
M4:20261022T002816Z_442; M5:20261022T002816Z_445); no milestone-scope inflation. Initial ignored
launcher path/import failure before simulation retained, repaired before pilots. Parent's first
pytest launch used nonexistent Ubuntu-24.04, retried installed Ubuntu successfully:27 tests plus
10 subtests PASS/no skips. Hand fixtures and rejection controls cover cohort/histogram/FIFO-depth,
partition, legacy mutation, raw-JUnit failure, nonzero exits and incomplete/relaxed acceptance.

Actual full180 replay, primary100k, FCFS/RR10/Main, N4/8/16,seeds509..528:
M3-primary/20261022T003252Z_406; M4-primary/20261022T003252Z_407;
M5-primary/20261022T003252Z_404. All180 cocotb cases/fullscope gates PASS, zero failures/errors/skips;
nine lint configurations and metadata controls pass. Three scopes ran concurrently with -j3,
--make-jobs2; elapsed FCFS866.94s/RR854.48s/Main1127.81s (not independent serial costs).
New measured RTL cycles18M+0.3Mpilot=18.3M; reset/drain/model/file audits not added to that count.

Parent replay audit compares every original nested metric except host wall time, validates180
JUnit/exits, matrix, original trace hashes, phase cycle/ready partitions, histograms/cohorts,
depth bounds and pooled histograms: PASS. No silent metric drift. New records:1,080 pooled-kind
rows,10,080 source rows, run-level20-seed mean/sampleSD/t19 95% intervals and paired deltas.
[Detailed outcome/reproduction](performance/TEST_RECORD_2026-10-22.md),
[phase audit](performance/phase-audit.json),[source/execution manifest](performance/replay-source-execution.json).

Warmup0/initial3reset excluded; no measurement reset. Same offered/ready traces; actual acceptance
can differ. Accepted-phase waits include measured accepts fired in C1 ready1 drain; generation-phase
waits are measurement-accepted subset with censored count/age snapshots. Boundary-held drain-only
accepts stay excluded, other producer backlog does not drain. Occupancy is pre-edge pin-history
state, backlog sampled pre-push/post-edge; no full time series/internal hardware probe claimed.
Idle phases can dispatch carried-over work. Main100k closes no W5M windows, allHigh/FCFS mirror;
primary is not adaptive fairness evidence. Source shares require offered-demand context.
Unmeasured continuously-backlogged service gap is a remaining gap, not a starvation bound.

Final acceptance checks:188 pre-existing manuscript/literature files and58 frozen functional
files hash-identical; protected RTL/refc/specs/syn/sta/docs/ppa diff empty. No Final edit/compile/
render, SSH, workload download or new PPA result. No active test batch/writer remains for this task.
FastX wording remains only:「目前帳號可見環境未確認 SPEC 安裝或使用授權。」No new license audit.
IPC/application slowdown, byte bandwidth/full CXL utilization and gem5 integration remain deferred.

## 2026-10-22 — Controlled descriptor follow-up implemented; real long runs active

Owner accepted the independent review's four tests; scope recorded in
[follow-up plan](performance/FOLLOWUP_PLAN_2026-10-22.md),
[execution/result record](performance/FOLLOWUP_RESULTS_2026-10-22.md). Final report remains on
hold, including its identified policy-subtree transcription error; no edits/build/render.
No architecture/RTL/refc/Spec/PPA, SSH, external workload, Algorithm-2 matrix or gem5 work.

Native CLI2.1.306/plugin0.14.6 verified; focused workflow actually requested Opus5.5/medium.
Sessionb257b3e2-ae45-498c-a0db-d6edee42dba3 returned weekly429 after195.141s,exit1, no implementation.
Owner-authorized GPT6.1Sol/high fallback /root/sol_perf_followup wrote/froze five isolated files,
reused strict run_verify build/execution and existing per-policy cycle-exact oracles/pin rules.
Parent independent audit code imports no new instrument/model to recompute histogram statistics.
Before full scopes parent73 tests/16 subtests pass, including43 new unit/rejection tests.
Final frozen pilot DF-pilot/20261022T012452Z_282 INFRA_SMOKE_PASS, captured processexit0,
21 actual cocotb cases/nine strict lint sets. W64/256 pilots are not W5M production evidence.

Retain all four pilot attempts: first summary's overbroad acceptance flag corrected, original
record not overwritten; attempts1/2 have empty outer-exit files, numeric exit NOT_RECORDED.
Attempts3/4 actual process0 recorded. Raw simulations passed; no failed simulation relabelled.
Code, source manifest, patch, prompts/settings/streams/exits/pilot evidence/failure-rejection checks
retained under .setup-logs/implementation/descriptor-followup-20261022. Single writer frozen.

Formal scopes launched concurrently, each -j3/--make-jobs2:
DF-controls/20261022T012724Z_281:36/36actual cases runnerPASS/exit0, elapsed397.469s;
DF-finite/20261022T012724Z_283:3/3actual cases runnerPASS/exit0, elapsed20.110s;
DF-trained/20261022T012724Z_287:three10Mreal-warmup+100k cases RUNNING, no aggregateacceptance yet.
Parent independent partialaudit all39 completed metrics PASS;9 intentional actual-evidence mutations
correctly rejected. Longsource hashes97files stable;188 dirtyFinal/lit and52 protectedfiles unchanged.

Fixedload controls separate generation0.3/0.9/1.2 underready1, plus0.6 with periodicready0.75;
seeds509..511,10kwarmup+100kmeasurement,complete all producer/FIFO/response work after generation
stops. Finite batch4096 completes fullcommonpopulation, direct g2fP99, explicit measurement/drain.
New per-source latency/cohort/censor snapshots, FIFO/backlog, initial/interservice clock/readygap
and bubble/slot metrics; continuouslyFIFOeligible work distinct from producerbacklog/sinkstall.
No stageP99summing, no pendinggap reported as complete, no WCET/starvation theorem claim.

Trained case uses realW5M and exact counts designed source0DOWN twice, othersKEEP. No preload/
time skip. After10M warmup expectedLow/H/H/H then persistent equal offered demand for100k.
This is a deliberate finite classification-state transient, not a full-window response to changed
load or evidence of general fairness. Expensive seed509 mechanism study only; controls3seeds,
no primary20-seed t19 interval reused. Fullresult acceptance and finalreport adoption stillpending.

## 2026-10-22 — Controlled follow-up accepted:42actual RTL runs, class-quota limitation observed

Source tooling checkpoint662c0e547d392cf37c5a03d7156c7f81db6b43a4; full scopes started at dirty
fe728d0 before checkpoint commit. Runtime97filemanifest retained:93exactGitblob byte matches,
4CRLF/LF-only matches (two parentauditscripts and two existingSpecfiles), all functional content
reconciles to662c0e5. Final independent audit PASS42formalruns/14matched intendedtracegroups,
actualrawJUnit/strictbuildexits/scope/length/params/histogram/cohort/snapshot/conservation checks.
All three captured outer exits0. No oracle-only export or JSONaudit counted as RTL cycles.

Run IDs: DF-controls20261022T012724Z_281 (36/36), DF-finite20261022T012724Z_283 (3/3),
DF-trained20261022T012724Z_287 (3/3). Full trained outerelapsed2471.797s, about41minutes;
controls397.469s, finite20.110s, scopes concurrent. Every trained policy really ran10M warmup,
100kmeasurement andcompleteproducer/FIFO/responsedrain. Actualformalnonresetcycles35,376,594:
warmup30,360,000;measurement3,903,072;drain/response1,113,522;126initialresetcyclesexcluded.
Selectedfinal21casepilot46,167nonresetcycles separate; historicalrepeatedpilots not newseeds.
Parent73tests/16subtests PASS and9actual-evidencemutations correctlyrejected (noadditionalRTL).

[Detailed accepted results](performance/FOLLOWUP_RESULTS_2026-10-22.md) and durablefollowup-*.CSV/
JSON recordsource/runtimehashes,42rawmetricpaths/digests,per-sourcecohorts/gaps,three-seedSD/min/
maxandrawexecution. Rawhistograms/reportsremainignoredartifacts, no largegeneratedlogs inGit.

Main actualclosingclassesB_H/H/H/H thenL/H/H/H fromtwoW5Mwindows; source0DOWN,otherKEEP,
closingB/Sexactcounterchecked,nextcyclepinschecked. No preload/time skip/reducedW productionlabel.
During100kmeasurement every source generates100krequests and is FIFO-nonempty/ready99,999cycles.
Allthreepolicies throughput0.99999, zeroavoidablebubbles. Main source0Low receives50.001%fires,
threeHighsources~16.667%each, versus~25%each FCFS/RR. Jainofequal-demand descriptorservice
Main0.7499925 versusFCFS/RR0.9999999997; do not call this an applicationfairness result.
Completeobservedeligible-readygapmaxFCFS4/RR31/Main13, withright/leftcensoredgaps separate.

This directlyexposes an approvedreconstruction limitation: classvisits10/10 allocateperclass,
sooneLowhost competes forhalf ofoutput whilethreeHighhostssharetheotherhalf. Higherclasslabel
alone doesnotimplymoreper-hostservice. Observedsourceinequality is notsilentlyfixed asRTLbug;
changing quotas/dispatch wouldneednewarchitectureapproval. NouniversalFAIbenefit claimed.
Mainmeasurementgenerationcohortmeanwaittofire:source0~49,996cycles,others~183,335–183,337,
comparedtoFCFS~150,000each. Allpolicywholecohortmean150,001; pooledP99FCFS/RR297,001,
Main297,334. AcceptedmeasurementcohortwaitP99FCFS63/RR75/Main97; populationslabelled.

Fixedcontrols3seedmeans demonstratecapacity/producerqueueing:FCFS ready1load1.2 fires1/cycle,
measurement-generationcohort meanG2A11,989.813+A2F62.866=G2F12,052.679,endingproducerpending
21,977mean;finite-windowoverload,notstationarydelay. Belowcapacitycohortsendingproducerpending0.
Finite4096generatedallcompleted foreachpolicy:globalG2Fmean2234.666748,P994415,max4469cycles;
per-sourcewaitsdiffer. Fixedcompletion/generationtimesumidentity explainsidenticalglobalmean,
notuniversalP99equality. Everyrequestcompletedonlyunderdocumentedfinitegeneration/drainpolicy.

Limitations:trainedmeasurement shorterthanthirdW,oneexpensiveseed,N4only,nochanged-loadlater
reclassification/recovery,source-placementinvariance,applicationIPC/slowdown/DRAMbandwidth/full
CXLutilization orWCET/starvationproof. FurtherN8/16/trainedpower/gem5/Algorithm-2matrixdeferred.
Finalchecks188dirtyFinal/litfiles,52protectedfiles,97frozenruntimefilesallunchanged. NoFinal
edit/build/render,SSH,Spec/RTL/model/PPAchange. Alltaskscopes/writersfinished; no activejobremains.

## 2026-10-22 — Source placement and class cardinality accepted

Owner authorized only the two recommended additions: move trained Low among source IDs and
vary class sizes1L/3H,2L/2H,3L/1H. [Plan](performance/PLACEMENT_PLAN_2026-10-22.md),
[actual results](performance/PLACEMENT_RESULTS_2026-10-22.md), placement-*.CSV/JSON preserve
the complete matrix and provenance. All14 nonempty proper Low subsets×FCFS/RR10/Main=42.
No RTL/refc/Spec/PPA changes; Final188 pre-existing dirty files remain byte-identical/unbuilt.

Actual Claude2.1.306/plugin0.14.6 focused workflow requested Opus5.5/medium,
session2ba93411-d537-4805-aca1-1290f21f43c2, weekly429/childexit1 after205.071s before writes.
Wrapper saved childexit1 then consoleprint UnicodeEncodeError; both retained. Approved fallback
GPT6.1Sol/high /root/sol_placement_sensitivity wrote/froze five isolated test files; Codex
reviewed independently. No concurrent writer; worker completed before full-scope execution.
Ignored evidence .setup-logs/implementation/descriptor-placement-20261022 preserves exact prompt,
settings,stream,stderr,exit,diff,legacy golden trace hashes,source/protection snapshots,pilots,
full command/exits,audits and rejection controls. No credentials/proprietary assets added.

First pilot20261022T024254Z_281/exit1 failed strict lint on unsupported W4096; simulations
NOT_RUN. Corrected to existing supported stress W256,512 natural training+240 measuredcycles,
128fill/112postfill, entirely before thirdclassification. No parameter guard suppression or
RTL extension. Passed pilot20261022T024506Z_270/exit0:lint3,units98,realRTL9;13,605nonresetcycles
separate from formal matrix, not independent extra placements. Naturaltraining eachwindow:
102//k perLow and12perHigh,252 active+4quiet slots, actualB/S exact and two DOWN/KEEPwindows
produce B_H thenL only on targetsubset. Main measurementclasses checkedfixed; no preload/skip.

Formal DF-placement20261022T024651Z_297/outerexit0,147.356seconds: **42/42actualRTL PASS**,
98units/3strictlint and actualcompile/make/sim/JUnit clean. Rawindependentaudit42/14matched
externaltracegroupsPASS. Actual63,498nonresetcycles:21,504training+10,080measurement+31,914drain;
126resetedgesexcluded. Completeall generatedproducer/FIFO/responsework; classifyduringdrain
withoutpoolingdrainclassservice withfixedmeasurement. Exactstage/directlatencycohorts/P99,
censoring,gaps/backlog/occupancy and acceptancecountsremaininspectable. This is short-window
mechanistic sensitivity, not productionW5M or random/statistical replication/long-termfairness.

Everyrun239fires/240measurementcycles,0avoidablebubbles,everysourcegenerated240/nonemptyready239.
FCFS/RR eachsource59or60fires/Jain0.999947. MainallplacementsLow120/High119; postfillLow53/High59,
classsourcecountspread<=1,12fullLow/11fullHighvisitsplus9Highrightpartialfires. Mainshares:
1L50.2092%,3H16.3180–16.7364%/Jain0.746836;
2L25.1046%,2H24.6862–25.1046%/Jain0.999947;
3L16.7364%,1H49.7908%/Jain0.753138. Similarhalfoutputfollowstheclass, notpermanentsource0.
Finiteboundaryoffsetsexplicit, no cycleidenticalpermutationclaim. ReinforcespreviousW5M result:
classquota can redistributewaiting/service without increasingtotalcapacity and can reduce
per-sourceequality underunequalclasssizes. Higherprioritylabelaloneisnot aper-hostshareguarantee.

Parent6histogram/quota tests+11subtestsPASS,10actualevidencemutationscorrectlyrejected; old42rawaudit
PASSagain(0RTLcycles). All99executionmanifestfilesstablethroughfullrun/adoption,52protectedfiles
and188Finalfilesunchanged. AfteradoptionrepairREADMEtextencodingonly andmake readonlyaudit
replaycomparesimulationdependencies, excludingdocs/auditscriptsthemselves; retainoriginalasrun
andpostprocessinghashesseparately. No executable simulation change/no unnecessary rerun.
Final42rawauditPASSagain. No activeagentwriter/simulation/SSH remains. Application/gem5,
N8/16placementmatrix,production-windowallplacementadaptation,power/APR remainoutside taskscope.

## 2026-10-22 — Heavy-host/sparse-host experiment designed; previous evidence preserved

Owner clarified the intended latency-protection use case and requested an experiment design,
with prior tests retained. Codex inspected frozen Spec class/hold/quota rules and current
traffic/metrics implementation; used ARS experiment-agent plan workflow inline, no worker
or Claude invocation for this documentation-only task. No new RTL/model/test code or run.
[Plan](performance/HOG_SPARSE_PLAN_2026-10-22.md) is explicitly UNVERIFIED/NOT_RUN.

Design separates sparse latency from total throughput: one heavy host generates1/cycle,
three sparse hosts each1/128 Bernoulli; second equal-mean-load profile eight-request bursts
per1024-cycle block. Background stays active until measured sparse cohorts complete in
separate1024-cycle guards; only then full heavy-backlog drain. Primary endpoint direct
generation-to-fire sparseP99 vsFCFS; independent RR10 comparison; allseed/source outcomes,
means/tails, acceptance, heavy service/backlog and total outputslots retained. No expectation
of automatic RR10 advantage; both use ten-fire visits. EmptyHigh quota is relinquished so
heavy service is not permanently capped50%. No uniform-share fairness objective under
asymmetric demand, application IPC/slowdown or physical bandwidth claim.

Planned scope: W256 three-policy seed509 infrastructure/sensitivity pilot, then N4/D16/M1/
full105 productionW5M, seeds509–513×3policies=15 actualruns, two measured profiles/run.
Two real5Mwindows before trained measurement, no deposit/skip/frozenclasses. Cold control
near end of training checks effective-allHigh Main=FCFS; actualclosingfire/B/S/state evidence
required. Before finaldrain active length10,204,448 per formalrun;15run total153,066,720
active cycles planned, not executed. Productionmeasurement100k+102400 perrun, guards separate.
This may require hours based on earlier41minute three-policy10M runs; pilot costs/memory must
be recorded, not extrapolated as certainty. Five-seed summaries descriptive, no power/95%
population claim; no selective extra seeds, changing quotas or discarding losing profiles.

Preservation operation read31 tracked performance documents/data and all264 indexed raw
metrics (phaseprimary180+controlled42+placement42); everySHA256 matched current durable
audit. [Preservation manifest](performance/EVIDENCE_PRESERVATION_2026-10-22.json) adds file
hashes/sourcecommit a74d29c and previous suite checkpoints. Hash checks add0RTLcycles;
raw files/logs/failures remain in place, no overwrite/delete. Existing188 dirtyFinal/lit
files hashed for final continuity check; no Final edit/build/render. Plan and preservation
record only, implementation CLI remains explicitly NOT_IMPLEMENTED. Native Opus5.5/medium
and approved quota-triggered Sol/high fallback remain the future controlled workflow.

## 2026-10-22 — Heavy/sparse execution: pilot accepted, formal15 running

Owner explicitly authorized executing the saved plan. Native Claude2.1.306/plugin0.14.6
focused /rtl-agent-team:rtl-p5s-func-verify hog-sparse-latency-experiment requested Opus5.5/
medium; sessionba43dac0-d728-4c88-9e91-25be271a795b weekly429/exit1 after248.676s beforewrites.
Global routing/auth untouched. Approvedfallback GPT6.1Sol/high /root/sol_hog_sparse implemented
fiveNEWverification files, noexistingRTL/model/test/Spec/PPA edits. Codex independently reviewed
and owns two new read-only audit/test scripts and records. Workerfrozen/completed beforefullrun.
Tooling+pilot checkpoint70bc6006eaecaaa93b5c9a56939a9a3e2bcf633b; runtime started from906ac86
withthese isolatednewfiles dirty, exactfrozenbytehashes retained. Sourcefiles notchangedduringrun.

Actual strictpilotHS-pilot20261022T034155Z_369/outerexit0:3lint/26units/3RTL/completegatePASS,
actual629,217nonresetcycles (1536training+607200measurement+6144guards+14337drain),9resetexcluded.
Parentrawaudit3/3/1matchedtrace PASS and13actualevidencemutationsrejected; parent3pooledtail
unitchecksPASS. Firstpilot20261022T033946Z_567 realRTL/unitsPASS butouterexitcaptureblank due
crossshell expansion; numericexit NOT_RECORDED. CorrectedPython subprocessunits02/pilot02
numericexit0captured, bothattemptsretained. Repeats notindependentperformance samples.

Pilot A/B direct sparseP99FCFS18/34,RR11/18,Main10/23cycles:preliminaryW256sensitivityonly,
notproductionbenefit. Negative Main/RRburstcomparison retained. PilotpeakRSS~50MiB/job; prior
10Mtriplet~41min andcurrentpilotcostsupportseveralhoursbudget, notguaranteedETA. Heavybacklog
boundedonlybyfinitegeneration, noheavywarmuplatencyhist/ever-growingcompleted-tagset retained.

FullHS-main20261022T034507Z_311 launchedUTC03:45:02 with-j6/--make-jobs2 (resource-only
adjustment fromplaninitial3jobs;WSL16logicalCPU/~14GiBavailable). Exact15jobs,N4/D16/M1/full105,
FCFS/RR10/Main×seeds509–513,W5M,real10Mtraining+two sparseprofiles/guards+completeallworkdrain.
Initiallint3/units26PASS; sixsimulationsrunning. Formalaggregate NOT_ACCEPTED untilalljobs,
strictactualexits/rawJUnit/source/trace/cohort/guards/coldpins/independenttailauditfinish.

Entrybaseline348protectedfiles,including188existingdirtyFinal/litfiles,byte-identical afterpilot
andstartup. Original264rawmetricsand31trackedperformancerecordsremainpreserved viaearlier
manifest; nooldresultsoverwrite. Ignored .setup-logs/implementation/hog-sparse-20261022 hasnative
prompt/settings/stream/stderr/exit,workerpatch/hashes/commands/pilots/exits,parentaudits/negative
controls/sourcefreeze/protection/fullprocess/progress. NoSSH/PPA/gem5/Algorithm2orFinalbuild.
Live/acceptedoutcome trackedseparately in performance/HOG_SPARSE_RESULTS_2026-10-22.md.

## 2026-10-22 — Heavy/sparse production15 accepted; intended latency protection observed

**ACCEPTED15/15actualRTL PASS**, HS-main20261022T034507Z_311, fullouterexit0. StartedUTC03:45:02,
ended05:45:13,elapsed7210.594seconds (~2h00m11s). Allstrictlint3/units26/compile/make/simulation
andrawJUnitPASS,zerofailure/error/skip. Fivepairedexternaltracegroups,15runexactmatrix,
30measuredprofileobservations,fullscopegateandindependentCodexauditPASS. Nofailedproduction
simulation/seedexclusion/timeout; originalpilotcapturedefectandcorrectedrepeatsremainarchived.

Actual156,657,531nonresetRTLcycles:150,000,000training+3,036,000measurement+30,720heavy-on
guards+3,590,811drain/response.45initialresetedgesexcluded. Nooracleexport/audit/hashregeneration
countedasRTL. EveryMainnaturallyclosesB_H/H/H/HthenL/H/H/HattwoW5Mboundaries,actualB/S/fire
thresholdchecks; measuredandguardclassesfixedthroughbeforethirdwindow. Full10McoldpinFCFS/
Mainhashesmatchfor5seeds,exactcoldperseedhistogramsmatch. Sparsecohortsgeneratedequalscompleted
whileheavygenerationcontinuesguards;finaldraincompleteallheavyproducer/FIFO/responses.

MainintendedusecaseissupportedvsFCFSwithqualifiedRRcomparison. Five-runmeanofrunP99cycles:
isolatedAFCFS18.2(range18–19),RR11(all11),Main10(all10);burstBFCFS33.8(31–36),RR17.2(17–18),
Main20.8(17–24). MeanpairedpercentP99reductionMainvsFCFS45.0292%A/38.6401%B; vsRR9.0909%A,
negative20.7843%B (Mainworse4seeds,1tie;nostrongeruniversalclaim). DirectmeanlatencyA16.3921/
5.5979/5.5296 andB23.2989/9.1693/9.3243 forFCFS/RR/Main. Sparseper-sourceP99all15source-seed
pairsimprovevsFCFSinbothprofiles; AvsRR14improve/1tie, BvsRR1improve/4tie/10worse. Sources
withinarunarecorrelated,noseparateindependentreplications. ObservedmaxlatenotWCET.

ColdMain=FCFSmean16.3842/P9918;Mainprotectionwaitsfor2Whysteresis. Differentcold/trainedtime
cohortsnotidenticalrequests; matchedcrosspolicytracesareprimarycomparisons. Ageneration->accept
mean0, Bmean3.5allpolicies from8descsourceinjection; measuredirectG2FP99,notsumstageP99.
All30measuredintervalsthroughput1.0/zeroavoidablebubbles. Heavyhostretains~97.67%ofcapacity,
notpermanent50%:emptyHighvisitsrelinquishquota. Aheavyfiremeans.976728/.976726/.976724 for
FCFS/RR/Main; B.97657617/.97656445/.97656445. Smallcutboundarydifferences, noloadlossclaim.
Heavybacklog~236932atAend/~239332atBendexpectedfiniteoverload;completefinaldrain,notstationary
heavywait. This explainslatencybenefitwithouttotalcapacitygain andpreservesprior equal-demand
classcardinalityresultsratherthanrejectingthem. MainburstHighclasssharedquota vsRRpersource
isaplausiblemechanisticexplanation,notaseparatecausalablationorpermissiontochangearchitecture.

[Results](performance/HOG_SPARSE_RESULTS_2026-10-22.md) withhog-sparse-audit/runs/profiles/
sources/paired/summary/source-executionCSV/JSON retaincounts/cohorts/exactrawdigests/seedSD/
minmaxandprovenance. Rawhistograms/contextatarrival/visits/gaps/occupancy/backlog/snapshots/window
recordsremaininartifactpaths. Fivefixedseeds,descriptiveeffectsizes,no95%populationCI/p-value,
noapplicationIPC/slowdown/CXLbytebandwidth/PPAupdate. Mainfiniteposttrainingmeasurementbefore
thirdW,no long-termadaptationclaim. ARS11/11fallacycategoriesreviewedwithstratification,
completegeneratedcohorts,pairedseeds,allnegativefindingsandclaimscopeexplicit.

Parentindependent3statunitsPASS/13actualevidencemutationsrejectedforpilotandformal. All106
as-runsourcehashesbefore/afteridentical;fivenewworkerfilesmatchcommit70bc600. Subsequent
doccheckpoint5e1d9e7changesnocoexecutedfiles. PerjobpeakRSS75.19–76.18MiB. Completeformal
sourcesarefrozenandprovenancedas906ac86plusnewfilebytehashesreconciledto70bc600,notmislabelled
clean906ac86. Prior264rawmetricsand348protectedfiles(including188dirtyFinal)rehashedunchanged.
NoFinaledit/build/render,SSH/newdependency/RTL/refc/Spec/PPA/gem5/Algorithm2changes. Allfullrun
processesandimplementationwriterhavefinished;onlydocumentationandfinalGitcheckpointremain.

## 2026-10-22 — Final report v2 release: Flash polish and four-panel evidence

Released [main-v2.pdf](final-report/main-v2.pdf) as the seven-page report (six body pages plus
one references page). GPT6.1Sol/high refined the evidence-led body; Gemini3.8Flash/high
(conversation62aca687-61fc-4872-8df9-ea5ac56d7672,265.69s) performed the language pass.
Codex restored the clean Flash body after layout experiments, fitted the figure and captions,
and verified that numerical values, citations, labels, and claim strength were preserved.
The new [four-panel hardware figure](final-report/generated/hardware_cost_v2.tex) adds the
N4 service-cost frontier to the accepted area, timing, and power evidence. Main reduces
sparseP99 by45.03%/38.64% versusFCFS at1.000000descriptor transfer/cycle; its area premium
is4.97–5.89% overFCFS, whileRR10 retains a burst-tail advantage. NoRTL, PPA, raw evidence,
Spec, refc, gem5, or Algorithm2 run was repeated or modified. Final checks: seven pages,
zeroLaTeX errors/overfull boxes/undefined references/missing glyphs, and visual inspection
of all figures and references.

## 2026-10-23 — Main-SQ diagnosis complete; conditional implementation gate fails

Branch experiment/main-sq starts from bb7f407623812c1866bafe2352a0433ffad263c8 in the same
checkout. Owner made source-sub-quota implementation conditional on an actual diagnosed
benefit; accepted Main/Spec/PPA and the existing Final manuscript must remain unchanged.
All original15 HS-main records/five matched groups were independently re-audited PASS,
with156,657,531 historical nonreset cycles rechecked, zero newly simulated by that audit.
Five-run mean G2F P99: singles FCFS18.2/RR11/Main10; bursts33.8/17.2/20.8. Mean paired
Main-vs-FCFS reductions45.0292%/38.6401%; Main worse thanRR on burst tail in4/5 seeds,1tie.

Actual native Claude2.1.306/plugin0.14.6 Opus5.5/medium focused workflow session
9f4e4095-5ccb-4e8c-ba98-7769a01f1c44 returned outer0/140.459s but internal safeguard stopped
before implementation. Smaller installed rtl-agent-team:testbench-dev session
9ab3c007-4b1b-4a3d-b32b-526bdc477b88 returned0/713.204s and wrote four new passive files:
sim/performance/main_sq_diagnosis.py, test_main_sq_diagnosis.py, tests/test_main_sq_diagnosis.py,
and scripts/run_main_sq_diagnosis.py. No fallback. Existing traffic coroutine/TBs/models/RTL
were not changed. Wrapper records observed pins/contexts without changing scheduling.
Stale six-entry plugin RTL-modified hook list is retained, not evidence of new RTL edits.

Two initial recorder unit failures (4fail/2pass then1fail/5pass) were repaired before the
actual RTL pilot: count-after-deletion, fixture age expectation, first-row generation and
fixture depth. Raw returned failures remain in native stream and extracted tool output;
complete standalone pytest logs were not captured for those first two attempts. No failed
RTL simulation is omitted. MSQ-pilot/20261023T082655Z_633 outer0/92.4s: strict lint3,
32unit cases (6new+26existing),3actualRTL PASS. W256 is infrastructure/sensitivity only.
All stable metrics exactly match the accepted HS-pilot;629,217 real nonreset cycles.

Source frozen f479a9f; plot-only deterministic fix3e457ccdfcdf0cbc2b2e9f380895b1c7d7b62e05.
MSQ-main/20261023T083405Z_1850 ran UTC08:34:05.525004–09:21:11.092159, outerexit0,
2825.623s, jobs3/buildjobs2. Verilator5.052/cocotb2.1.0/Python3.12.3 WSL; strict lint3,
32units/3RTL/JUnit/scope PASS, no failures/errors/skips. W5M/N4/seed509/FCFS/RR10/Main;
each trains10M real cycles, no preload/time skip. Every nonvolatile metric equals original
seed509; only active_wall_s,total_wall_s,peak_rss_kib are excluded. Before/after/current110
runtime hashes match. Production31,333,251 cycles; pilot+production31,962,468 actual
nonreset cycles =30,001,536 training+1,214,400 measurement+12,288 guards+734,244 drain.
Six actualRTL cases, one seed/twoW settings; repeated32units are not64 distinct tests.

Codex independently reconstructs every103,424-row B+guard trace/policy and all2,400 sparse
requests (800/source), all stage histograms/nearest ranks/cohort completion and paired tags.
All Main2,400 High grants match oldest accepted head; actual stable L/H/H/H throughout B.
Production G2F mean/P99/max: FCFS23.337917/34/38, RR9.273333/17/24, Main9.415/24/31.
All G2A mean3.5/P99=7, exact100 at each0..7/source, sparsefull0: batch serialization,
not FIFO blockage. Main beats FCFS on2400tags; vsRR31faster/2315ties/54slower. Throughput
and eligible-ready utilization1 in measured A/B; zero bubbles/stalls. Heavy service is
heavy fires/all measured fires (~97.66%), not demand satisfaction or equal-share fairness.

Diagnosis H1 directly supported:7 High expiries leave pending High, visits286x8+7x10+7x6,
unused credits600. H2 concentration exists (max6 same-source High grants with competition),
but the key tail already alternates2,1: ten High fires10171357..10171366 leave6 requests;
Low then10171367..10171376. Source2/tag10410514 g10171350/a10171357/f10171381, latency31
versusRR22/FCFS37. H3 explains cold adaptation, not fixed-class trained-B difference.
H4 full-FIFO delay rejected for sparse cohorts. Main tail>=P99 includes26ties; exposure
sum148serialization+132predecessor+262Low+129otherHigh+26ownfire=697 request-cycles,
not disjoint scheduler cycles or causal runtime percentages.

Offline SQ screen holds observed admissions/classes/High slots fixed, rotates subquota1/2,
preserves partial usage across Low, and rejects FIFO/slot inconsistency. All three starting
pointers agree: Main/SQ1/SQ2 P99=24/24/25, max31/34/34, source2P99=21/28/29. Means all9.415
by fixed-slot identity, not independent performance evidence. W256 also worsens23->24/25.
FAIL proposed persistent SQ benefit gate; do not implement for this diagnosed objective.
Not a universal rejection of every SQ/refill rule/workload. Main unchanged; all candidate
RTL/model/five-policy matrix/Formality/PPA/power NOT_RUN by conditional stop. Main-HQ is
a plausible class-capacity hypothesis requiring separate owner design decision/Low-service
safeguards, not measured benefit. Main-AGE lacks direct current justification. No SSH.

Three read-only Codex reviewers cover passive recorder, full production reconstruction,
and independently recomputed SQ schedules; agree with stop. Parent analysis6tests/14subtests
PASS. New scientific plots distinguish actual versus offline, external legends and cycles.
Curated raw bundle22files/2,192,355bytes SHA256
e2e75552d02885568eb05b7a6503b4e980c546922807759b5de9b2afbf7bea66 contains raw results/traces,
JUnit, source manifests, accepted reference metrics and portable gate-summary projection;
original full summary/logs remain locally. Fresh bundle replay audit exactly matches the
original-directory audit. Archive manifest hashes every payload. Audits add zero RTL cycles.

[Evidence index](experiments/main-sq/README.md), six required reports, source/config/tool
manifest, actual/screen CSVs, audited JSON and reproducible plots preserve the negative
result. Ignored .setup-logs/implementation/main-sq-20261023 contains native prompt/settings/
logs/exits/failures, source/protection inventories, commands and independent review output.
Preserved694disjoint original protected/source files including518Final,264earlier rawmetrics,
and the owner's pre-existing15-line Final-v2 development entry. No Final edit/build/render,
Spec/oldRTL/model/PPA change or new hardware measurement. New report append is separate
from the owner's entry in the Git index. All simulations/native writers have finished.

## 2026-10-23: approved revision program, initial implementation checkpoint

Owner explicitly approved implementation of the revised F1-F16 program, including
closed-loop DAC/AGE model screening and at most one gate-qualified new insight RTL.
This authorization preserves separate manuscript revision approval. The previous
Main-SQ completion above remains valid for that task; new revision workers are active.

Codex added immutable matrix generation/source-hash audits, paired-seed statistics,
an issue ledger, method/attribution differences and an execution record under
`docs/experiments/revision-20261023/`. The initial matrix contains498 planned jobs:
468 unconditional and30 conditional on a single insight winner. Generated NOT_RUN
rows are not experiment completion. Reanalysis of the original15 HOG runs recomputes
histograms, ranks and service without adding RTL cycles. F1's denominator correction
is Main38.22-39.27% above RR, equivalently RR27.65-28.20% below Main; the manuscript
has not been changed.

Disjoint Codex workers implement Python DAC/AGE models/screens, six missing formal
bridge orchestration, and a generalized performance harness. Native Claude Code
2.1.306 / RTL Agent Team0.14.6 remains the RTL implementer, actual Opus5.5/medium.
Its first testbench attempt returned a safeguard/temporary-CWD clarification with no
implementation, outerexit0. The RTL coder then created four experimental RTL files
and strict-lint evidence before a service safeguard rejection, outerexit1.
A fresh coder retry also ended exit1 with the same safeguard. This is not usage
exhaustion and does not trigger the authorized Sol fallback. A fresh native
testbench-dev invocation is tracked separately; functional acceptance remains open.
Exact prompts/settings/streams/errors/exits are in
`.setup-logs/implementation/revision-20261023/`.

Parent independent audit: matrix3, statistics3, experimental model13, screen runner7
and bridge tooling8 tests all PASS,34 total; source hashes stable through this audit.
All531 protected accepted RTL/spec/manuscript files match the entry snapshot.
Raw suite outputs and protection results are in `parent-audit/summary-initial.json`
under the same ignored evidence root. These checks do not establish RTL equivalence.
Parent review also identified incorrect delta-based candidate ranking; correction
to absolute worst cold/trained B mean P99 and a regression test are in progress.

Six missing FCFS/RR source bridges remain0/6. Three pinned SSH attempts started zero
remote shells/preflights/license probes/Formality processes. The missing temporary
trust material was restored only from the previously approved exact archived public
key; a local path-quoting defect was repaired. The latest attempt failed
noninteractive authentication, with no established cause beyond that denial.
No trust weakening, credential guessing, remote asset copying or PASS inference.
`BRIDGES.md` and `bridges/final-attempt-accounting.json` record the full history.

Core production matrix, candidate advancement/RTL/PPA, matched trained power,
approved paper revision and the subsequent independent three-reviewer re-review
remain incomplete. Subsequent checkpoints must report actual evidence, including
negative results, without replacing missing runs with short-window pilots.

### Revision execution checkpoint: source freeze and native testbench repairs

The insight worker froze15 transitive source dependencies and launched
`artifacts/implementation/insight-screen/production-sealed-20261023T101008Z`:
60 actual-W5M HOG configurations and eight four-window feedback configurations,
at most three model workers. All13 model and13 screen tests pass, as do
sealed W256 sensitivity pilots (12 HOG,8 feedback). Absolute worst cold/trained
B mean P99 now controls the resource-allocation tie-break, with a regression
test. First three production baseline configurations exited0; final screening
is pending and no DAC/AGE RTL candidate is authorized by these partial results.

Native Opus5.5/medium repaired the correctness testbench's closing-edge
sampling, coverage accounting, uninterrupted BLISS clear coverage, and exact
clear/held boundary schedules. The original failed diagnostic and a repaired
attempt retaining one BLISS failure are archived. Final diagnostic
`revision-baseline/20261023T101410Z_1489` passes three lint cases,15 model
tests and21 cocotb tests, no skips, stable sources. Native process exit0 is
recorded alongside a terminal stop-hook error; acceptance uses actual raw
strict-runner/JUnit evidence.

Parent full36 correctness run `20261023T101627Z_2445` then passed36 lint
cases and15 unit tests but failed nine RR configurations' structure assertion:
Verilator removes a constant-only empty generate scope. All other tests in
those cases passed; the complete run remains FAIL/exit1, with stable hashes.
Another native invocation exclusively owns the testbench repair, checking
actual timestamp-storage absence and constant outputs instead of visibility
of an empty scope. No RTL is changed to accommodate a test. Production
performance remains gated on a successful full rerun and matched pilots.

Parent reviewed the robustness generator before production: heavy-ID exchange
must permute source0/3 from reset, including training. Training heavy0 then
changing roles during measurement introduces backlog/adaptation and required
an extended guard; dedicated adaptation already measures that effect.
The initial matrix archive is retained. Source matrix flags are amended for
the30 affected rows; counts and seeds stay fixed, while their canonical IDs
change. A new immutable snapshot will accompany the corrected generator.
An explicit joint eligible-ready utilization denominator was also requested.

Independent parent checkpoint
`parent-audit/checkpoint-20261023T1022/summary.json` records42 tests passing
across six suites. All535 protected paths selected from the native RTL entry
snapshot match, as do15 sealed model dependencies. These are preservation and
Python checks, not added RTL performance/formal results. Offline area
attribution, trained-power preparation and a strict matrix evidence index are
assigned disjoint new-file scopes; their outputs are not yet accepted.

### Revision continuation at approved99400de: 2026-10-24

The owner confirmed534f92a and99400de as the expected Main-SQ handoff and
instructed continuation at99400ded42cc63c3b206bd5d13f51d36344b2689.
No existing manuscript/unrelated changes were reverted.

The full sealed MODEL_ONLY batch production-sealed-20261023T101008Z is complete:
60 HOG jobs and eight four-real-W5M feedback jobs, evaluation exit0, unchanged
15-file source set. Parent reloaded all68 reports through the strict WSL
source/ZIP/validation binding path and recomputed exactly the saved PASS gate
(.setup-logs/implementation/revision-20261024/screen-ingest-audit.json).
Initial Windows re-ingest correctly rejected WSL absolute artifact bindings;
the final check used WSL without weakening checks.

DAC2 alone advances: paired mean P99 Main to DAC2 is18.2->2.0 coldA,
33.8->16.0 coldB,10.0->1.0 trainedA,20.8->12.0 trainedB. All four endpoints
improve in all five exploration seeds. Maximum heavy-service fraction drop
is0.000068360043 (0.0068360043 percentage points). DAC1 ablation gives
2.0/16.4/2.0/16.4; therefore per-source allocation contributes separately
from historical2:1 weights. All six AGE settings show zero mean B change and
fail benefit screening. No confirmation seed or RTL benefit is inferred.
Native Opus5.5/medium RTL Agent Team is assigned only new isolated DAC source,
unit-top, filelist, test and runner paths; existing performance sources remain
released. Prompt/command/stream/settings/entry hashes are retained in
.setup-logs/implementation/revision-20261024/dac-native/.

The RR native structure repair ended with explicit429 session quota exhaustion.
The approved GPT6.1 Sol/high fallback repaired only testbench hierarchy checks,
with actual model/effort retained in sol-rr-structure-repair/provenance.json.
Diagnostic20261023T102832Z_9245 passed2 lint,15 model and10 cocotb tests.
Parent full36 rerun20261023T171119Z_303 passed36 lint,15 model tests and
all applicable dynamic tests, zero skips, stable hashes, exit0.
Archive review found its new hier_util.py import absent from sources.zip;
the runner dependency list and a regression check were corrected (2 testsPASS).
Full source-complete rerun20261023T171608Z_276 is retained separately.

Previous in-memory worker IDs were unavailable after handoff. Replacement
workers own the same disjoint performance/area/evidence-index/trained-power
paths. The paper remains read-only; remote source bridges/newPPA/power remain
blocked by the already documented noninteractive SSH authentication failure.

Source-complete baseline acceptance20261023T171608Z_276 is now final PASS:
36 lint configurations,15 independent-model tests and226 cocotb tests, zero
failures/errors/skips, stable sources, complete_matrix=true and exit0.
Parent independently checked every ZIP member against its manifest and current
bytes, including hier_util.py; archive SHA256
275b590f8f05d1b587e5e4ca8f407d9addd6b78a1f11628dbe695dcae8372076.
The separate baseline-archive-audit.json records this check.

The replacement performance writer repaired a pre-simulation GNU Make failure
caused by a build directory containing Coding Space. It now reuses the accepted
Linux cache/CXL_BUILD_ROOT convention, with a regression. The failed six-policy
pilot is retained. Final39-file freeze passes30 traffic/runner pure tests;
pilot-n4-seed509-finalfreeze passes all six policies, six lint and51 combined
unit/cocotb tests, zero skips,104.318s. This is W256 sensitivity evidence only.
N16 sensitivity and a real-W5M exploration resource run precede core production.
Static heavy-ID swap includes reset/training and preserves canonical descriptor
streams/tags. Joint eligible-ready utilization and per-source conservation
are now explicit validated result fields.

Offline F8 area attribution expands540,590 mapped leaves across all nine
historical primary archives, zero unresolved ownership, exact category sums
and precision-bounded Decimal reconciliation to total_cell_area.
An initial fixed tolerance rejected a small N16 RR report-rounding residual;
the repaired bound is derived from printed precision and explicitly retained.
Parent also required an independent test of whether hierarchy explains the
reported cell-count differences. Neither leaves nor leaves+nonleaf occurrences
matches number_of_cells; the discrepancy remains a warning, not an invented
explanation. Full table/leaf evidence is in AREA_ATTRIBUTION.md and
revision-area/continuation-20261024-hierarchy; this is not new synthesis.

The strict evidence index initially overrequired all three trained/cold lanes
for every core row and rejected the real runner's selected-production-subset
scope. Parent corrected both interpretations:120 core N4 jobs remain120 trained
A/B runs; optional cold evidence is separate; a fully completed selected bundle
can validate its declared rows while global matrix completion remains false.
Regression fixtures preserve rejection of partial/missing/hash-mismatched
evidence. No model or pilot contributes a production matrix PASS.

F12 local preparation passes14 tests, six short W256 exports and three full-B
W256 exports, with independent serialized replay and source ZIP checks. All18
three-policy/three-seed/A-B production commands are prepared. No W5M export,
native gate replay, SAIF or PT power was launched; modes12/13 need native
allowlist support and remote authentication remains blocked. Power work keeps
its approved lower priority than core confirmation/causal/robustness work.

### Continuation checkpoint: 2026-10-24, HEAD99400de

The owner explicitly confirmed the handoff at99400de; the parent verified
HEAD99400ded42cc63c3b206bd5d13f51d36344b2689 without changing commits.
A fresh comparison against the native DAC entry snapshot found535 protected
accepted-RTL/spec/manuscript files unchanged. Existing dirty paper artifacts
remain untouched.

Parent reran the final offline area18 tests, statistics4 tests and strict
evidence-index14 tests, all PASS. The final hierarchy-count audit retains
unexplained number_of_cells residuals in all nine cases; area reconciliation
and complete leaf attribution do not resolve that reporting-field definition.
Evidence index checkpoint index-06 records no production matrix PASS yet;
model screening and baseline correctness remain separate inventories.

The performance writer restored the historical training-boundary rule:
only the designated cold generation cohort must complete at that boundary.
Unmeasured late training arrivals may remain pending; A/B guards still require
all sparse queues drained. Fresh W256 pilot-n4-seed509-trainingfix and
pilot-n16-seed509-trainingfix pass. The real-W5M N16 FCFS seed509 resource run
resource-n16-fcfs-seed509-w5m-trainingfix is running; core production remains
gated on its complete validated source-bound result and memory assessment.

Native DAC session dac-native ended exit1 after1062.436s with service-side
reasoning_extraction, not quota exhaustion. It produced draft DAC scheduler,
standalone top/filelist and testbench, but no accepted correctness result.
A fresh native RTL Agent Team session dac-verification uses the same
Opus5.5/medium and only the isolated DAC source/test/runner/doc scope to finish
verification. No fallback model or existing performance dependency was changed.

The analysis adapter now exists with source-bound paired-run validation;
its initial28-test result comprises10 adapter,14 index and4 statistics tests.
It correctly reports zero accepted core runs and no bootstrap intervals at
this checkpoint. Review found optional cold payloads use a boolean in raw
results while lanes use cold-A/B labels; the index owner is correcting that
boundary and adding successful cold integration coverage before acceptance.

### Subsequent execution checkpoint: 2026-10-24

Native DAC verification now completed: Opus5.5/medium, installed RTL Agent Team,
exit0 after1042.885s. Run `revision-dac/20261023T174033Z_1699` records54
strict lint passes, six intentional invalid-parameter rejections,192 cocotb
passes across18 configurations,four runner tests and13 frozen-model unittest
tests, with zero failures/errors/skips and stable24-source closure. Parent
independently verified source ZIP bytes and current hashes. ZIP SHA256 is
`d2707bc5fc31e6ef11e8b4ef073a2047eca873892b78151b5e8fa370cd0634aa`.
The native writer fixed a combinational dependency warning, the model test
counting convention and directed test fixtures; the initial failed run and
mutation checks remain retained. Accepted default RTL and the39-source core
performance freeze were not changed. Production DAC benefit, full-four-window
RTL feedback, mapped equivalence and25ns timing remain unverified.

The repaired index passes16 tests, adapter14 and statistics4. Optional cold
evidence is correctly typed and separate from the120 trained confirmation
denominator. Adapter checkpoint `revision-current-analysis/20261024-adapter-03`
reports no accepted confirmation cohort and no bootstrap interval.

Parent prepared an exact459-row core queue, comprising458 queued jobs plus
the single real-W5M N16 FCFS seed509 resource row. Queue validation checks the
exact ID set, trained lane, source ZIP and unchanged pilot bindings, actual
resource process exit0, and three-worker memory estimate below70% of available
memory. All validation uses explicit checks that survive Python optimization.
The exit watcher binds the existing Windows WSL process handle, command and
creation time; it does not infer success from PID disappearance.

Read-only adversarial review exposed descendant cleanup after the group
leader exited; the parent repaired cleanup to check the whole owned group and
send KILL after its deadline. Six mock checks pass under normal and optimized
Python; a real isolated WSL TERM-ignoring descendant check also passes.
A malformed test context-manager fixture and an asynchronous KILL observation
race were repaired and rerun. No resource or unrelated process was stopped.
Independent final review found no remaining concrete launch blocker.
Supervisor session62785 is now running from
`.setup-logs/implementation/revision-20261024/production-supervisor`; it waits
for the actual resource receipt before validating and starting the core queue.
The resource was still running beyond6.25M cycles at this checkpoint.
Neither supervisor launch nor correctness acceptance contributes a production
matrix PASS. Candidate production and trained power remain separate gates;
remote authentication is still blocked and manuscript files remain read-only.

The released DAC performance harness now passes23 pure tests under Windows
and WSL. W256 seed509 pilots
`revision-dac-performance/pilot-dac2-seed509-w256-20261024` and
`pilot-dac1-seed509-w256-20261024` each pass one lint plus43 tests with zero
failures/errors/skips. Each executes209,699 actual non-reset cycles, including
4,739 drain cycles, on the same arrival trace. Both contribute zero production
matrix rows. DAC2 simulation wall time is55.217s, peak RSS49,044KiB; DAC1 is
40.867s,49,468KiB. These short runs do not establish W5M runtime or held-path
coverage; full native correctness supplies the separate held-path evidence.

Parent independently repeated23 tests and re-ingested the sealed screen,
native correctness, release and DAC2 pilot:102 native,275 screen and10 pilot
bindings validated. The53-file performance freeze is
`4eca15454a0ba1c75a88e5f0431f32730a50c02bc047fa8ca3a899715b206227`;
its shared39-file core freeze remains
`800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86`.
Independent read-only review found no concrete production blocker. Parent
authorized exactly30 frozen DAC2 production jobs, first ten robustness jobs
then20 confirmation jobs, one simulation worker/build2, stopping on a failed
group. No DAC1 production or confirmation-based tuning is authorized.
The launcher is being prepared in ignored logs; authorization is not an
assertion that production has started or passed. Index/analysis writers own
separate files outside both source closures to integrate conditional evidence
and explicitly validate shared-core compatibility for paired DAC2/Main runs.

The real-W5M N16 FCFS seed509 resource run subsequently finished PASS:
actual10M training plus measurement/drain,11,401,520 non-reset cycles,
simulation wall2698.33s and peak RSS220,044KiB. The complete runner reports
PASS after2785.7s; the Windows process-handle observer recorded the original
wrapper exit0 at2026-10-23T18:18:43.7193032Z. The supervisor's strict archive,
source and memory validation succeeded. Core queue PID4141 started the120-row
N4 confirmation group via runner4146 at18:18:51Z, three simulation workers and
build2. This is one accepted production row; the120-row group is running,
not accepted.

The DAC2 wrapper also started ten robustness rows at one simulation worker
and build2. Active evidence is
`revision-dac-performance/dac2-production-20261024-launcherfix-00-insight-robustness`,
wrapper3985, runner3988, tool session77602. The first launcher attempt was
controlled-stopped to repair its archive membership check, which omitted the
allowed context/EXECUTION.md member. Frozen53 performance sources and parameters
did not change. The initial wrapper exit143/child exit-15 and fresh repaired
launch are preserved; no confirmation seed had started at that handoff.
Eleven launcher selfchecks pass under the actual WSL environment. Parent
first invoked those Linux-specific launcher tests under Windows and observed
missing killpg/getsid errors, then reran in WSL with11/11 PASS; no production
source was changed for platform support.

The launch plan's original wording incorrectly attributed final go to a new
direct human message. An adjacent
`dac-performance/production-authorization-correction.json` records that the
sender was the parent agent acting within the already approved user plan.
Original bound launcher/plan bytes and hashes are preserved. This corrects
provenance, not the authorized scope. DAC2 performance remains pending and
the study has not completed its498-row matrix.

Conditional DAC indexing is now integrated without modifying either frozen
performance closure. The existing inspector dispatches the DAC schema,
validates its pinned53-source release, shared39 core hashes, sealed acceptance
blobs, exact conditional IDs and selected_policy, raw exits/JUnit and archives.
W256 and DAC1 records remain descriptive with zero matrix contribution.
Index checkpoint
`revision-evidence-index/20261024-index-01/index-09/matrix-coverage.json`
has SHA256
`aed7219fe93a5bf5f5782bb72d5c86a0e9231cfec0f654ba1257495a573717bf`
and reports1 PASS,130 RUNNING,367 NOT_RUN,0 FAIL,0 UNRESOLVED out of498.
RUNNING includes queued jobs in active bundles, not130 simultaneous workers.
Parent independently reran23 index,20 adapter and4 statistics tests, all PASS.

Analysis checkpoint
`revision-current-analysis/20261024-adapter-dac-index09-01/analysis.json`
reinspects saved-index evidence. It keeps core confirmation0/120, conditional
confirmation0/20 and robustness0/10 separate, with four descriptive W256
profile endpoints and no confirmatory intervals. Shared39 source compatibility,
exact arrivals/configuration and seed pairing are required for DAC2/Main
comparisons; full53 versus39 source manifests need not be identical. The two
production queues remain active and incomplete.

### Owner-requested SSH diagnosis, 2026-10-24

Continuing at owner-confirmed99400de, a fresh strict pinned SSH probe established
the server connection and matched the approved host key, then exited255 during
batch authentication. Evidence:
`.setup-logs/implementation/revision-20261024/ssh-diagnosis/20261023T184836Z`.
The configured master socket is absent; historical receipts explicitly record
its deliberate closure after earlier work. WSL has no SSH key directory or
agent socket, and Windows ssh-agent is stopped/disabled. No service outage,
password expiration or incorrect owner password was established.

Prepared ignored owner-terminal `ssh-diagnosis/login.py` to reuse the approved
pin and socket, obtain interactive authentication through SSH without logging
credentials, then start the existing six-bridge runner after a successful
authenticated batch probe. Its argument/trust/immutability selfchecks and eight
bridge unit tests PASS. No interactive login or EDA invocation occurred.
The core and DAC production supervisors remain active; incomplete bundle step
passes do not promote whole matrix rows. Read-only verification found zero
changes among539 RTL/spec/manuscript files in the DAC-native entry snapshot,
including the separately added native DAC RTL. No frozen performance source
was edited. Offline preparation of the matched DAC PPA/equivalence adapter is
assigned separately while authentication awaits the owner's terminal.

Independent index-10 audit at02:49:51 Taipei confirmed all four supervisor/runner
PIDs alive and unchanged frozen39/53 hashes. Three FCFS confirmation result
files (seeds529-531) passed local checks; the incomplete120-row bundle has not
received final acceptance. DAC robustness seed509 last logged8.25M cycles.
Index-10 remains1 PASS,130 declared RUNNING,367 NOT_RUN,0 FAIL/UNRESOLVED;
matrix-coverage SHA256:
`c79ccb3c4c8d2d930e67c4b4de313f38724e730f133192ff583ee13e7d93e429`.
The analysis documentation now correctly identifies the accepted resource row
as N16 n-expansion evidence, outside N4/DAC confirmation cohorts.

### SSH restored and matched DAC PPA authorized, 2026-10-24

The owner completed interactive authentication. Login and subsequent batch
probe exited0 at18:59:49-51Z; six-bridge run
`revision-bridges-20261023T185951Z` passed remote preflight. FCFS N4, RR N4
and FCFS N8 wrappers exited0; the full six-case/downloaded-report audit is
pending. The earlier authentication blocker is resolved, not a server failure.

The new offline DAC PPA adapter is frozen and independently reviewed without
a concrete launch blocker. Parent repeated11 unit tests, all PASS. Prepared
tar `dac-ppa/prepared-20261023T185811Z/payload.tar` has SHA256
`017d58f88edce7b62494466fd571ad6f70230105ba379a6350e0ca61281b8b96`;
manifest SHA256
`759586524658dbbc93bf005d76e2e9df98c03c23560ded9283044e47ed14becf`.
It binds the accepted native DAC2 N4/D16/W5M sources and the original frozen
TT25ns cap075-v2 profile, complete policy/metadata/hold/FIFO state and unchanged
DC/PT templates. Parent authorized one fresh-directory remote DC/PT invocation
followed by its own mapped-netlist equivalence, stopping on failure and
retaining all evidence. No new RTL or manuscript modification is authorized.
New Formality parameterized-name parsing, area/timing and compare-point results
remain unverified until actual reports are available.

Matched DAC execution actually started at2026-10-23T19:06:49Z under run
`revision-dac-ppa-20261023T190649Z`, launcher PID57768. Ten ignored-launcher
selfchecks pass (payload/current61 inputs, pinned SSH, sequential execution,
safe paths/archives, download hashes and no overwrite). The exact reviewed
payload uploaded with exit0; a separate read-only monitor exited0 and observed
remote wrapper PID197011 in RUNNING_DCPT. Tool version handling recognized
the existing W-2024.09 informational dc_shell version-query exit1 convention.
No synthesis/STA/formal acceptance follows from launch or version queries.
The first DAC robustness cocotb step also now exits0; its ten-row bundle
remains RUNNING and unaccepted as a complete cohort.

Six source bridges subsequently completed PASS at
`artifacts/fastx/revision-bridges-20261023T185951Z/`.
Parent independently reran audit_case for all six actual downloaded report
sets and matched the complete local report hashes against the remote manifest.
Passing compare points FCFS/RR N4,N8,N16 respectively:
8967/6893,17793/13672,35443/27227. Compared registers:
8855/6781,17676/13555,35317/27101, plus one accounted optimized constant
register per configuration. No user constants/exclusions, active blackboxes,
postmatch undriven nets or failing/aborted/unverified/unmatched points were
accepted. This closes the six missing declared source bridges, not workload
or unrestricted parameter verification.

During the separate native read-only power review, its owner updated one
exporter metadata status string to remove the now-resolved remote-auth blocker.
The review correctly records sources_unchanged=false and is not a production
freeze. Owner confirmed the sole source-map change and native read-only tools;
the core39/DAC53 closures are unchanged. No power production export was
launched, and the unrelated completed DAC PPA payload is unaffected.

Independent completed-report review accepts the six historical source bridges
and the new DAC mapped equivalence. DAC has9014 DFF +112 output bits =9126
passing points, zero failing/aborted/unverified/unmatched/constant registers,
all28 user setup commands0/0 and no user constants/exclusions/blackboxes.
Pre-match undriven0/40 resolves to0 post-match. SVF has122 accepted and12
rejected uniquify operations,0 unsupported/unprocessed; the proof succeeds.
The original SVF remains remote and is bound by handoff hashes.

Independent area/STA review also accepts the specified DAC2 N4 matched
pre-layout result: cell area109794.784709,9014 registers, worst reported
setup/hold slack+10.398800/+0.038578ns,36348 met/0 violated/68 untested.
All68 untested checks exactly match propagated-constant disabled arcs:
64 arrival-counter D=0 and4 counter SETB=1. Parent's first one-off parser
missed four inline SETB rows; handling the actual inline/wrapped formats
resolved the parser assertion without report or criterion changes.
Independent leaf area reconciles within0.000002002126 report precision.
Cell-count semantics retain a63-cell residual after including hierarchy;
matched Main has the same limitation. DAC versus Main total cell area differs
by-0.2680185%, with3 more registers. No power, physical-area, physical-signoff
or isolated-credit-area benefit is claimed.
Results and exact scope are recorded in DAC_PPA_RESULTS.md.

For F12, parent authorized the native RTL Agent Team/Opus5.5 medium writer to
extend only check_power_replay.py, sim/power/tb_power.sv and
test_power_extension.py for trained modes12/13, preserving legacy modes,
all warmup checks and measured-only annotation. These files are outside the
frozen39/53 closures. Native execution, tests, fresh power freeze and
production export remain separate gates; no production power export has run.

The native power implementation actually launched at19:19:41Z with PID85452,
Opus5.5/medium and installed rtl-agent-team:rtl-coder. Its invocation permits
only the three assigned files and bounded sequential native tests.
Parent caught a prompt field typo: the exporter uses smoke_cycles, not
smoke_measured_cycles; an adjacent correction receipt preserves the original
prompt and requires matching the actual exporter schema without an alias.
This is a pending implementation/testing item, not accepted mode support.

Parent conditionally authorized exactly one actual-W5M Main/seed509/A export
plus serialized independent audit only after native success, meaningful
bounded tests, a separate Codex review without a concrete blocker, a fresh
explicit power source/evidence freeze, unchanged core39/DAC53 and resource
checks. No other17 exports or remote VCS/power run are authorized at this
stage. The conditional producer has not started at this checkpoint.

At03:20:36 Taipei, parent found zero changes among539 protected RTL/spec/
manuscript files. Core N4 has six completed PASS cocotb steps and DAC robustness
has one, with zero failed steps; both whole bundles remain RUNNING and
incomplete. These are progress counts, not accepted complete-cohort totals.


## 2026-10-24 owner model override and interrupted-queue inspection

The owner explicitly requested temporarily stopping new Opus calls and assigning
its remaining work to GPT6.1 Sol. This supersedes the quota-only fallback trigger
for this session. Two explicit gpt-6.1-sol/high delegates were accepted by the
agent API: trained-power three-file implementation and interrupted-queue recovery.
The prior agent handles were unavailable in this runtime; fresh delegates preserve
the existing scope and evidence instead of starting another Opus invocation.

At08:53 Taipei, WSL process inspection found none of the former core/DAC
supervisor/runner PIDs3985,3988,4141,4146, nor simulator/runner processes.
Both durable queue files still said RUNNING; those statuses are stale. The cause
of interruption is unknown. Core N4 contains39 raw result JSONs and DAC robustness
contains7, with no failed steps in the saved summaries. These counts are progress
only, not complete-bundle or paired-cohort acceptance. Recovery must preserve
all original files and run only independently validated outstanding work.

Both exact frozen source closures (core39 and DAC53) remain unchanged. All539
protected RTL/spec/manuscript files also match the native-entry hashes.
No manuscript edits were made. Evidence and explicit delegate/model settings:
`.setup-logs/implementation/revision-20261024/sol-handoff-20261024T0853/receipt.json`.

The failed native power stream was inspected directly: its terminal event has
subtype=success but is_error=true and an actual HTTP429/session-limit message.
CLI exit1 and unchanged assigned files remain the operative outcome; the
misleading event subtype is not a successful implementation. WSL reports uptime
22 minutes at08:55 Taipei, consistent with a fresh instance but insufficient to
establish why the previous queues stopped. Current available memory is14,954MiB
and local C: free space116GiB; recovery retains the prior worker limits.

The Sol writer released the three-file trained-power patch. Parent's independent
review found that self-consistent zero-service closing counts could initially
coexist with an impossible declared Main class transition. The writer reproduced
two failing mutations, tied evidence to the class transition, and reran the
45-test WSL suite:44 pass/one missing-Tcl skip, no failures. Windows19 contracts
include the Tcl test and pass. Parent independently reran all five new trained
contracts and verified released source hashes. The patched replay retains legacy
modes and measured-only annotation; synthetic header/SAIF fixtures are not power.

A fresh33-file power source archive and independent review receipt are under
`revision-20261024/power-parent-review-20261024T0904`. Exactly one actualW5M
Main/seed509/A exporter launched at09:04 Taipei with Windows PID5104, including
its serialized independent replay. Output is
`artifacts/fastx/revision-trained-power-main-A-s509-20261024T0904`. Its process
exit, source stability and complete audit remain pending. This is not a SAIF/PT
measurement; the other17 exports and remote power await first-case acceptance.
Core39/DAC53 are unchanged after the patch. All remaining frozen sources stay
read-only during this export.

Queue recovery's exact source/JUnit/exit/config audit identifies39 core and7
DAC completed raw runs eligible for reuse, not yet sealed matrix acceptance.
Its ignored adapter retains original Run finalization and does not change frozen
runner code: it copies hash-checked original logs/XML/results only for validated
cache hits, executes missing jobs, then reruns the original full-result validation
and archive creation. Recovery code/plan/origin receipts are archived separately
in each new bundle. Fourteen recovery tests pass. Parent reviewed the source,
cache failure guards, tool environment, process cleanup and Windows-owned WSL
handles, then authorized this exact prepared continuation. The plan retains all
488 queued jobs (458 core plus30 DAC), reusing46 completed simulations; the
resource row remains separate. Global budget stays core3/DAC1 plus one power
producer. Initial preparation wrongly required six N16 pilots; actual accepted
pilots are three N16 policies and six N4 policies. Correcting that invented
guard preserved the failed preparation and did not rerun or weaken real evidence.
Prepared plan: `queue-recovery/prepared-20261024T0108Z/plan.json`. Actual
relaunch/PIDs are recorded by its Windows wrapper; authorization is not completion.

Actual recovery launch confirmed at2026-10-24T01:06:21Z (09:06 Taipei):
Windows owner PID19492 retains WSL handles85712(core)/70372(DAC). WSL lane
supervisors380/383 and active group children394/395 are live. Initial strict
lint and unit steps pass; completed cache reuse and remaining simulations are
not yet a finalized bundle. Durable handle receipts and new artifacts are under
`queue-recovery/prepared-20261024T0108Z/windows-owned-20261024T010621Z` and
its sibling `runs/`. Parent authorization and the actual launch are separate
recorded events; no completed-cohort inference or manuscript edit was made.

### 2026-10-24 09:18 Taipei: continuation audit and remaining power preparation

Parent independently observed WSL core/DAC lane and group processes alive,
with all four actual simulators near100% CPU after about590 seconds. Windows
supervisor19492 and Main509A exporter5104 are also alive. The first power
capture still lacks final metadata/audit/exit; it is not accepted power evidence.

Sol's index sidecar completed three bounded recovery/archive compatibility
tests and invoked the unchanged index/analysis CLIs, both exit0. The strict
snapshot remains1 PASS/130 declared RUNNING/367 NOT_RUN; incomplete groups
are not promoted from raw PASS steps. The two sidecar agents continue using
gpt-6.1-sol/high; no Opus invocation occurred.

Remote-power preparation confirms the standalone checker uses only standard
library imports and matches the released hash. Its strict master probe exits255
because the old local control socket no longer exists after the observed WSL
restart; no credential failure or remote tool/license outage is inferred.
Parent reviewed the one-case automatic VCS/replay/PT plan, conditional on
completed export acceptance and authenticated preflight. No upload or tool run
has been authorized to bypass these checks. Sidecars now prepare tested,
bounded one-case remote execution and the remaining17 sequential exports,
without launching them or editing any frozen source.

Parent's independent source check passes39 core,53 DAC performance and33 power
dependencies, plus535 protected accepted RTL/spec/manuscript files, zero changes.
The exact check result is under
`revision-20261024/parent-continuation-20261024T0118Z/source-check.json`.
Issue ledger and execution notes now distinguish accepted six-case bridges,
accepted DAC pre-layout proof/timing, live comparative jobs and unmeasured
matched power. Manuscript revision and independent re-review remain pending.

Parent reran the statistics/matrix suites from `scripts/`:seven tests pass,
including fixed bootstrap pairing, cohort rejection, seed separation and
window/activity boundaries. The first invocation from the repository root
used package-style test names and failed imports because these existing tests
expect `scripts/` on the import path; correcting the invocation resolved both
import errors without a source change.

At09:19 Taipei the first Main509A exporter finished vector generation:
10100000 rows and205735748 gzip bytes, metadata status
`EXPORTED_INDEPENDENT_AUDIT_PENDING_GATE_NOT_RUN`. Its two actual closes are
cycles4999999/9999999, transitioning heavy source H->B_H->L while the three
sparse sources remainH. The integrated independent serialized replay is still
running. This records generation progress only, not audit or power acceptance.

At09:27 Taipei parent independently reran13 remote-executor tests and14
remaining-export orchestration tests, all pass. Review found and the Sol writer
fixed the download location for the actual `reports/run-status.txt`; the
corresponding shell-path regression passes. Remote execution also binds the
external exporter exit, final audit, exact payload and runtime sources, and
does fresh tool/disk/pinned-input checks before upload. No remote run occurred.
Interactive terminal PID10788 now runs the strict-pin reconnect helper only;
it reads authentication directly from the terminal and does not rerun bridges.
The current environment has no available configured identity file, SSH agent
or master socket; this does not imply remote credentials are invalid.

The remaining17-export adapter is released and parent reviewed. Its final
plan SHA256 is
`a7ef124d8e30204957b0e459cf0e770376855c033f3ea7cca2e6c8cbf87a8e68`.
Parent launched Windows supervisor7008, observed
`WAITING_EXISTING_FIRST_EXPORT_NO_RERUN`. It retains a verified native handle
to5104 (executable and creation time checked), requires actual process exit0
plus the existing wrapper exit receipt and completed source-bound serialized
audit, then writes a bound local acceptance receipt and runs exactly17 further
captures sequentially. Any failure/drift stops without automatic retry or
overwrite. It cannot bypass the first audit and has no remote/EDA stage.
No second power producer was started. Evidence, frozen scripts, tests and
parent launch authorization are under
`power-parent-review-20261024T0904/remaining-plan/`.

At09:30 Taipei the recovered core bundle contains42 raw performance result
JSONs, versus39 imported originals:three new actual simulations completed
successfully (RR1 seed548, RR10 seeds529/530), with their strict cocotb steps
exit0 and no failures/errors/skips. Three successor simulators are live.
The DAC bundle still contains its seven imported results and one running
simulation. Neither group is sealed yet, so these additional raw successes
do not change accepted matrix counts or justify confirmation intervals.

At09:30:20 Taipei the original Main509A exporter and serialized audit
actually completed exit0:10100000 rows, elapsed1558.342 seconds including
679.501 seconds of independent audit. Its native retained handle also observed
exit0. The continuation then stopped safely on an adapter error: the existing
wrapper writes integer `exit`, whereas the newly reviewed reader expected
`exit_code`. Parent missed that actual-schema mismatch in the first review.
No remaining capture started and the successful first export is retained.

Parent's subsequent actual-export validation found a second adapter mismatch:
the exporter freezes32 dependencies, while the broader parent33 freeze also
contains independent `scripts/test_power_extension.py`. Every shared source
hash matches and there are no exporter-only entries. The remote adapter had
incorrectly required these two scopes to be identical. Sol is repairing the
exact32-source projection while retaining checks on all33 parent inputs, and
the shared first-exit reader with real-schema regression tests. Neither finding
is a scheduler failure or grounds to rerun the successful export. Original
artifacts, stopped supervisor and failed parent validation remain preserved;
details are in `parent-continuation-20261024T0118Z/power-first-integration-findings.json`.

At09:35 parent repeated actual first-export validation with the repaired exact
projection:PASS, including actual gzip/text count and hashes, archive contents,
all33 current parent inputs,32 exported dependencies, four mapped inputs,
audit/phase/closing/cut-state consistency, original exit0 and retained native
exit0. The full model replay was not repeated. Receipt:
`parent-continuation-20261024T0118Z/power-first-actual-acceptance.json`.
All17 repaired remote-executor tests pass independently. The local Main509A
payload is206325760 bytes with SHA256
`e76160b19d3116eb9e46e09b2eb0e06eda2b184dd9a8cb1bb21d22d6c8636af3`;
it is prepared and accepted for the one-case remote scope, not uploaded.

The Sol exit-schema repair uses one shared reader for the exact original
pid/exit/UTC-finish schema and retains later child exit_code records unchanged.
Parent independently repeated16 tests, all pass. A fresh plan binds the repaired
scripts; old plans, stopped supervisor and failed tests remain intact.
At09:37:19 parent launched the direct remaining17 batch, Windows PID46420;
actual first child FCFS/A/seed509 PID73864 is running. New plan SHA256:
`e7fa1616d6d537da1c487b718f636ee239cbd411bbbe6676ccf2be5f77e374fe`.
Its accepted first receipt and launch authorization are in
`remaining-plan/prepared-exitfix-20261024t0133z/`. No first export rerun, new
paper edit or Opus invocation occurred. SSH authentication and all actual remote
gate/SAIF/PT power stages remain pending.

At09:39 parent reviewed and independently repeated all five one-case
authentication-watch tests:PASS. Parent verified the released watcher and all
fixed payload/runtime/acceptance bindings, then launched Windows watcher77520.
Observed status is `WAITING_EXACT_AUTH_RECEIPT`, remote execution count0.
It waits for the exact interactive login result, actual successful probe bytes
and a live local master, then invokes the already accepted Main509A remote
executor once. Any failure retains its claim/logs and stops without retry.
It cannot create another payload, launch other exports or grant semantic power
acceptance. Receipt: `power-sol/remote-preparation/parent-watch-launch.json`.
The current interactive authentication remains pending; previously successful
bridges/PPA are not rerun.

Final09:40 parent source check still passes core39, DAC53, power33 and535
protected accepted RTL/spec/manuscript files, zero differences. Raw result
counts remain42 core/seven DAC, including the three newly completed core runs.
The direct17-export batch and core/DAC queues continue in background; no complete
cohort or measured power claim follows. Check result:
`parent-continuation-20261024T0118Z/final-source-and-raw-check.json`.


## Continuation checkpoint2026-10-24 ~13:02 Taipei

The current WSL boot ID is `a5f75540-6cdf-4cc5-8e3a-6f9e2808c840`,
different from the prior recovered queue's `44b0c61b-26e3-4c63-83ac-444ef2900868`.
Old Windows/WSL lane handles were absent; old RUNNING receipts were stale.
This establishes another kernel-instance change, not its cause. No successful
raw result was discarded. Parent revalidated frozen core39/DAC53 and the
interrupted raw steps before resuming the identical immutable recovery plan.

The DAC robustness bundle `runs/dac/00-insight-robustness/attempt000`
passed independent `inspect_performance_bundle` with zero problems: all10
actual production RTL rows accepted. Core confirmation retains60/120 successful
raw runs; DAC confirmation retains1/20. Neither partial group establishes a
complete confirmation cohort. New attempt001 receipts reuse those61 raw runs;
the completed robustness group is skipped after its own strict acceptance.
Parent Windows supervisor68980 owns the new core/DAC WSL handles. Four actual
simulators (three core, one DAC) were observed alive at ~99%CPU. No frozen
simulation code was changed and no actual failed simulation was silently retried.

Strict index/analysis snapshot `queue-recovery/index-handoff/snapshot-20261024t0510z`
exits0/0 and reports11/498 PASS,140 declared RUNNING,347 NOT_RUN,
zero FAIL/UNRESOLVED. RUNNING includes queued rows, not140 workers. The11
accepted rows are ten DAC robustness plus the prior N16 resource run. Partial
confirmation cohorts do not produce confidence intervals or benefit claims.
Core39/DAC53, all33 power dependencies and539 protected RTL/spec/manuscript
files matched their recorded hashes. Parent receipts are under
`queue-recovery/continuation-1258/`.

The previous remote power reconnect had exited255 without executing EDA.
A fresh interactive approved pinned reconnect now succeeded at
`power-sol/remote-preparation/login-20261024T050140Z`: login0, exact
read-only probe0, strict host checking true, zero EDA/bridge jobs. The former
watcher is not restarted against its failed receipt. Sol/high is preparing
continuation against the new successful receipt, with read-only target checks
before the already approved single Main509A payload can execute. The six
accepted bridges and DAC PPA are retained without reruns.

The Windows local power progress records six completed additional captures
and an interrupted active FCFS/B/seed510; its old native batch/child PIDs are
absent. Sol/high is validating completed captures and preparing a scoped
continuation; this stale RUNNING status is not called live. All paper files
remain untouched. No Opus invocation was made.


## Accepted continuation launches2026-10-24 ~13:09 Taipei

Local power validation accepts7/18 exact W5M serialized captures with native
exit0, independent audit, hash/ZIP/contracts and frozen33/mapped12 checks.
The accepted seven are Main509A plus FCFS509A/B, RR509A/B, Main509B and FCFS510A.
The former active FCFS510B has no completed audit/native exit receipt and is
retained as interrupted with unknown termination cause. It is not relabelled
as a failed methodology result or overwritten. Sol/high prepared exact eleven
remaining identities under fresh `continuation-1258/recovery11/captures`.
Parent repeated the read-only native recovery validation exit0, checked exact
plan/runner bytes, and launched Windows producer72684 once. Its first child39912
is actually running FCFS510B. One producer, original contracts, source guards,
native child exits and stop-on-first-error remain enforced; no successful
capture is regenerated. Recovery plan SHA256:
`e50df4b0af36e43be7f3f295f34d74c151fe5b869d3fed572ca7485212c41ff9`.

Remote continuation uses the actual new SSH login/probe PASS and the unchanged
accepted Main509A payload/executor. Read-only exact-target checks observed no
existing directory or matching process. Parent independently repeated12
resume tests PASS and checked released script/plan hashes. The timestamp guard
repair addresses a synthetic same-second folder precision edge case; the real
current login already passed before that fix. Both old reviews remain intact.
Parent launched single remote executor8816 with reviewed plan SHA256
`24b5e2a737d7282d34d6e3f8e54d10e674760d31d05a1e4f4876c4503a56d030`.
The shared exclusive claim exists, actual remote preflight and upload both
exit0, and the power stage is in progress. No replay/SAIF/PT or semantic
acceptance is granted yet. No completed bridges/PPA were rerun.

Source-bound acceptance/launch receipts:
`power-parent-review-20261024T0904/continuation-1258/` and
`power-sol/remote-preparation/continuation-1258/`. Core/DAC four-worker
continuation remains alive. No Opus call, manuscript edit or commit occurred.


## Measured continuation checkpoint2026-10-24 13:36 Taipei

Parent independently inspected three newly completed Main production runs,
seeds529/530/531, through the unchanged recovery validator. Raw identity,
configuration, actual tool exits, JUnit, source archive and payload checks pass.
Core confirmation now has63/120 successful raw runs; full-group sealing and
confidence intervals remain pending. Receipt:
`queue-recovery/continuation-1258/raw-checkpoint-1336.json`.
This checkpoint does not promote partial raw rows into the strict11/498 count.

FCFS510B local trained-power capture completed in its fresh recovery path with
native exit0 and independent audit. Parent rechecked contract, sources/mapping,
completed file hashes and recorded exit. Eight/18 local captures are now
accepted; RR510A is running. This yields four complete local A/B capture pairs,
not four accepted power matrix rows. Receipt:
`power-parent-review-20261024T0904/continuation-1258/parent-checkpoint-1332.json`.
The ongoing single native producer retains all ten remaining identities.

A bounded read-only remote monitor verified actual simv execution, no compile
or simulation failure lines, about1.5k CPU seconds and ongoing vector-file
position advance. At13:34 the replay had reached7,000,000 warmup cycles;
it was not waiting for authentication or license checkout. Compile warnings
are8973 TFIPC and one ICTA-SI. Prior exact-mapped MainN4/model diagnostics
already classified8973 omitted-output TFIPC warnings; current warning identity
and the one ICTA-SI message are being checked against that evidence, not waived.
No SAIF/PT semantic acceptance or power benefit is claimed. Monitor evidence:
`power-sol/remote-preparation/continuation-1258/monitor-1332/`.

The remaining17 remote-case adapter is being prepared/tested in an isolated
ignored scope. It cannot launch before the first case's independent semantic
receipt. Current frozen producers/executor/payloads, accepted bridges/PPA and
manuscript are unchanged. No Opus invocation or commit occurred.


### 2026-10-24 13:48 continuation: first trained power returned; semantic review pending

Owner-directed continuation uses GPT6.1 Sol/high for delegated work and makes no
Opus call. HEAD remains owner-approved99400de; manuscript remains read-only.
The first Main509A trained gate/SAIF/PT job returned all28 allowlisted files with
remote exit0. Parent recomputed all28 file hashes, checked identical source
before/after inventories, compile/sim/PT/shell exits0, exact10,100,000 gate cycles
and100,000 measured cycles. SAIF duration is2,500,000ns; clockTC199999,TX0;
all9011 unique FFclock pins have file-derived activity0.0799996. PrimeTime reports
3.466e-03W for this single case and no check_power issues. This is a reported
pre-layout TT25ns, zero-delay/no-SDF ideal-clock estimate; it is not yet a
semantically adopted result or a comparative power benefit. Independent review
is classifying the34 leaf constant-pin gaps and unconnected-output unknown
SAIF records. Evidence: prepared-parent-20261024t013541z/parent-returned-evidence.json
under the ignored power-sol/remote-preparation scope. Parent's initial ad-hoc
check incorrectly required unscoped clk net names; it was corrected to allow
hierarchy-local clk nets while preserving exact pin/activity checks. No RTL or
runtime change was made for this check.

RR510A local capture independently passed native-exit, existing export-validator,
source/mapped/audit/hash checks without repeating a full10M model replay. Local
accepted captures now9/18; RR510B is running. Receipt:
power-parent-review-20261024T0904/continuation-1258/parent-checkpoint-1351.json.
Core N4 confirmation has63/120 successful raw cocotb runs and DAC confirmation
2/20, both groups still RUNNING/unsealed; no partial bootstrap is computed.
DAC robustness10/10 remains sealedPASS. Four WSL simulators are active. Parent
rechecked core39, DAC53, power33 and539 protected RTL/spec/manuscript files;
all hashes match their frozen entry inventories.

Remaining17 remote adapter is being finished in its exclusive ignored scope;
no additional remote power case has been launched. A separate Sol/high writer
owns only the evidence-index ingestion/tests/documentation to support strict
A/B power-row acceptance. Each of nine matched power rows requires both arms'
actual reviewed remote evidence; one local capture or one returned arm cannot
complete a matrix row. Existing frozen simulation/power sources are unchanged.


### 2026-10-24 13:53 first matched trained power arm semantically adopted

Independent Sol/high review adopted only Main509A trained pre-layout power with
no blocking issues. Parent independently compared the56 scoped always-X SAIF
paths against the hash-pinned prior linked-PT report: all have zero top ports,
leaf connections and nonoutput hierarchy pins. The34 deficient leaf cells match
32 literal-zero D pins and two literal-one SETB pins, with68 actual propagated-
constant disabled arcs. No new simulation or proprietary library query was
needed for these already-proven disconnected identities. This does not assert
that all SAIF records are known or all leaf pins annotated.

Reported power is3.466mW (switching0.01918mW, internal1.331mW,
leakage2.116mW; rounded printed quantities). Scope remains zero-delay/no-SDF,
ideal clock, pre-layout TT25ns; no physical signoff or cross-policy benefit.
Independent evidence is in power-sol/remote-preparation/continuation-1258/
semantic-main509a/semantic-review.json. Parent bound the exact review, prepared
payload, all28 returned hashes and command transcript in
power-parent-review-20261024T0904/continuation-1258/remote-matrix/
first-main509a-semantic.json. This one arm contributes zero completed A/B power
matrix rows. The remaining17 adapter still requires its own final reviewed
release before launch, and each returned case needs its individual review.


### 2026-10-24 13:54 remaining17 remote trained-power execution started

Parent repeated all13 isolated adapter testsPASS, verified the actual first
semantic release and first FCFS509A native capture, then launched the frozen
serial remaining17 executor as WindowsPID46196. PlanSHA is
10c1b353a83267ba3e0f2719961fb6907855ccf9071074dda2c44514118563e7;
adapterSHA152ef345420a6d2713b079c87eadcd2dd9f6d5d8d5adbfba5d4573abee2c033f.
First FCFS509A preflight/upload exits0 and power stage is running. It uses exact
existing mapped assets, strict-pinned SSH, exclusive claims and no automatic
retry. Local capture readiness is checked per case, with bounded waits on the
live producer. Only exact-hash execution/vectors.txt and duplicate payload.tar
inside each newly owned successful case can be removed after verified download;
canonical gzip/localpayload/reports/SAIF and every failed/old/first artifact stay.
Storage checks reserve4GiB plus one active-case budget. Parent authorization,
launch, output and progress are under continuation-1258/remote-matrix/. Initial
test fixture relied on the actual parent receipt being absent; it was corrected
to an isolated missing temporary path, with the failed run retained. Independent
semantic review remains required for every returned arm; no additional power
row is accepted merely by starting this executor. No frozen39/53/33 runtime or
manuscript source was edited.


### 2026-10-24 13:56 strict power evidence index extension checked

Sol/high extended the existing evidence index in its assigned three-file scope.
Parent repeated all28 index testsPASS; worker also reports20 analysis regression
testsPASS. Matched power ingestion checks native audits, exact source/mapped ZIPs,
trace/configuration, payload/runtime, four remote stage exits, returned hashes,
raw replay/PT audits and parent-pinned independent semantic releases. Parent
approved only the actual Main509A semantic receipt hash. The actual first case
now passes the strict case check but still contributes zero completed power rows
because B is missing. All nine power rows require individual accepted A and B;
model/smoke/cold/W256 results cannot complete them. Evidence is under
power-index/parent-review.json. Core and DAC producers and the remaining17
remote executor are still live; no full498 completion or partial CI is claimed.


### 2026-10-24 15:15 continuation: local progress and remote transport interruption

Owner requested continued execution. Parent accepted14/18 local trained power
captures after native-exit, frozen-source/mapped, serialized audit and file-hash
checks via the existing validator; no full model replay was duplicated.
Local producer is generating RR511A. Parent checked72/120 core N4 confirmation
raw jobs and4/20 DAC confirmation raw jobs through unchanged inspect_partial;
identities, exit/JUnit/parameters/payload and source ZIP checks pass. Groups
remain unsealed, without partial bootstrap. Four WSL simulation workers remain
active. DAC robustness10/10 stays sealedPASS. Source inventories core39/DAC53/
power33 and539 protected RTL/spec/manuscript files still match.

A fresh original-lane index/analysis snapshot completed0:
queue-recovery/index-handoff/snapshot-20261024t0715z. Adding the independently
accepted single Main509A power arm produces the explicit combined snapshot
power-index/combined-20261024t0715z:11PASS,140declaredRUNNING,346NOT_RUN,
1UNRESOLVED of498. The unresolved row is Main509 power missing its accepted B
arm, not a detected hardware failure. DeclaredRUNNING counts queued rows, not
workers. No new power pair or complete confirmation cohort is claimed.

At15:12:21 the first remaining remote FCFS509A power transport returnedSSH255;
its bounded result fetch also returned255. Preflight/upload previously passed0.
Shared master check now reports missing socket; read-only probe returned mux
broken pipe. Windows executor46196 exited and preserved STOPPED_NO_AUTORETRY,
its claim, transcript and failed transports. Remote VCS/PT exit/progress/state
are unknown; SSH255 is not an EDA failure or success. No rerun/reupload/next-case
launch was performed. Independent diagnosis is under power-sol/remote-preparation/
continuation-1258/semantic-remaining/monitor-1512/. Owner terminal authentication
must restore the existing approved strict-pinned master before read-only
inspection/recovery of that SAME remote directory. The existing reconnect.py
performs only login plus exact probe and does not rerun bridges/EDA. A Sol/high
sidecar is preparing a bounded inspect/fetch recovery path with tests, without
network or execution authorization. Local captures and simulation queues continue.

Parent ran the independent reusable power reviewer five selfchecksPASS; its
policy-specific acceptance still requires actual downloaded results. No Opus,
commit, frozen runtime change or manuscript edit occurred.


### 2026-10-24 15:28 Taipei - restored SSH and recovered FCFS509A semantic acceptance

Owner completed authentication. The strict-pinned login/probe succeeded and the
existing FCFS509A remote run was inspected and downloaded without rerun, upload,
signal or cleanup. Original power/fetch SSH255 remains intact; recovery inspect
and fetch exited0 independently. Returned compile/sim/PT/shell exits are all0.
Parent independently verified all28 downloaded hashes, repeated the six recovery
review guard tests PASS and reran the semantic reviewer into a separate directory.
The actual10.1M-cycle replay includes100k measured cycles and2.5MnsSAIF; all8856
FF clocks use file activity,27689/27689 nets are annotated and32 leaf gaps match
constant disabled state. Three exact prior table-range warnings trace to static
zero-activity nets in the new SAIF. Adopt the single FCFS509A estimate3.356mW as
qualified TT25ns prelayout zero-delay power only, preserving the extrapolation
limits; no unconditional check_power PASS or cross-policy benefit is claimed.

Parent acceptance: power-parent-review-20261024T0904/continuation-1258/remote-matrix/
parent-fcfs509a-semantic-1528/parent-release.json, SHA256
846560b2efffdb832d417b5e95adbc77cf3660a187258eaf75b7b75dec09c008.
It releases preparation/review of the original remaining16 cases under a new
exclusive continuation, without restarting the claimed interrupted17-case
executor. Original first-case failure history remains evidence. No next remote
case had launched at this checkpoint; a Sol/high writer is preparing that bounded
continuation and another is adding explicit recovered-evidence index ingestion.

Local unchanged inspect_partial validates75/120 core confirmation and4/20 DAC
confirmation raw successes, with groups still unsealed; DAC robustness10/10
remains sealedPASS. Four WSL simulators are live. Local trained captures remain
14/18 accepted, with RR511A in progress at the last producer snapshot. Parent
revalidated completed captures using existing serialized-audit/hash/source
validation without duplicating full replay. Inventories core39/DAC53/power33 and
539 protected RTL/spec/manuscript files still match. No partial-cohort bootstrap,
Opus invocation, commit or manuscript edit was performed.


### 2026-10-24 15:29 Taipei - remaining16 remote continuation launched

Parent reviewed continue16.py, repeated five continuation guard tests PASS,
checked exact sixteen jobs excluding both accepted first cases, then launched
reviewed plan da9de61b1a90abef76beea922e8d584b6d59257ccb1cda8f71e4e41c90c1b009.
Code SHA256 b4b5ae7636a76342af6cfb5e80d535fa210d3c02fd2ac8017c6813177e95e1bf.
Native Windows PID18840; parent PTY session49859 retains stdout/stderr and will
record final exit separately. The approved master check succeeded; first case
FCFS509B preflight/upload both exited0 and its power request is running. A new
exclusive claim/progress preserves original interrupted17-case scope and SSH255
history. No recovered first-case rerun occurred. Scope is one serial remote job,
stop-on-failure without automatic retry, exact-hash owned-derived cleanup only;
every downloaded case still needs independent semantic acceptance. The frozen
continuation and all three frozen experiment input inventories stay unchanged.
Evidence: remote-matrix/continue-remaining16-1523/execution/progress.json and
execution/fcfs-B-s509/transport/{preflight,upload}.exit.json under the same ignored
power-parent-review continuation root. No additional power pair is accepted by
this launch, and the full498 matrix remains incomplete.


At15:30 Taipei parent accepted the completed local RR511A capture using the
existing validator (native exit0, metadata/audit/source ZIP/gzip and mapped-source
bindings), bringing trained power inputs to15/18; RR511B is active. Receipt:
power-parent-review-20261024T0904/continuation-1258/parent-checkpoint-1530.json.
This is capture acceptance only, not three additional gate/PT power results.


### 2026-10-24 15:48 Taipei - parent accepts recovered-power index and new captures

Parent reviewed the explicit recovered-power ingestion diff, independently ran
33 index tests plus20 analysis tests PASS (zero skips/failures), verified release
file hashes, and regenerated the strict index and analysis under
power-index/recovery-implementation/parent-acceptance-1548/. Original FCFS509A
transport power/fetch255 remains stored; independent inspect/fetch0 and actual
compile/sim/PT/shell0 are separate checked evidence. Raw archive members,
exact remote input paths/hashes, original history and pinned qualified semantic
receipts are all required. No manifest may nominate an arbitrary trust anchor.

Strict matrix remains11PASS,140declaredRUNNING,345NOT_RUN,2UNRESOLVED/498. The
two unresolved matched-power rows have accepted A arms but lack accepted B arms;
there is no complete accepted matched-power pair. Parent validates77/120 core
confirmation raw runs and5/20 DAC confirmation raw runs with unchanged
inspect_partial; these groups remain unsealed and have no partial bootstrap.
Four WSL simulators remain live near100%CPU. DAC robustness10/10 sealedPASS stays
accepted. Source inventories core39/DAC53/power33 and539 protected files match.
See queue-recovery/continuation-1258/parent-checkpoint-1550.json (actualUTC inside).

Parent additionally accepted local RR511B after native exit0 and the unchanged
metadata/audit/gzip/source ZIP/mapped validator; local trained captures are16/18,
Main511A now active. Receipt: power-parent-review-20261024T0904/continuation-1258/
parent-checkpoint-1547.json. These are serialized input captures, not new gate/PT
power estimates. Remote16 continuation PID18840 remains onFCFS509B with
preflight/upload0, checked remote inputs, no returned final EDA result yet.
Parent inspected/tested the local-only60s semantic watcher (one testPASS); it
waits for completed downloaded evidence before review, treating pending cases as
pending rather than failed. No duplicate launch, Opus, frozen-source change,
commit or manuscript modification occurred.


### 2026-10-24 17:00 Taipei - trained captures complete; returned power review calibration

Parent checked the completed local recovery11 producer status, native exit0 for
all11 jobs, exact metadata/audit/gzip/source ZIP hashes, phase conservation and
frozen/mapped bindings using the existing validator. Together with the previously
accepted seven captures, all18/18 matched trained power input captures are now
accepted. This does not imply completion of their VCS/SAIF/PT or semantic matrix.
Receipt: power-parent-review-20261024T0904/continuation-1258/
parent-all18-captures-1700.json (actual UTC included).

Remote continuation returned FCFS509B,RR509A,RR509B. Parent independently checked
all28 downloaded hashes per case and preflight/upload/power/fetch/owned-derived
cleanup exits0. Main509B is currently running. The local semantic watcher stopped
on FCFS509B with `FF clock missing, default, unknown or incorrect rate`; retain
that blocked receipt. Initial exact diagnosis: SAIF TC204799/duration2560000ns
is0.079999609375 while PT prints0.0799996, a9.375e-9 display-rounding difference
that the old1e-10 absolute reviewer check rejects. Every clock row is file-sourced;
A's199999/2500000 equals its printed rate. Sol/high reviewer is reproducing this
in a new ignored scope with bounded decimal-display tests, not changing frozen
power/runtime or past accepted reviewer bytes. No B semantic acceptance is
waived; actual full review must pass after any justified reviewer correction.
Index's raw contract has no same hardcoded per-FF text tolerance; it still awaits
new independently accepted semantic releases for these three cases.

Parent unchanged inspect_partial validates84/120 core and7/20 DAC confirmation
raw successes. Groups remain unsealed, no partial CI. Core39/DAC53/power33 and
539 protected files all still match; four WSL simulators remain active. DAC
robustness10/10 remains sealedPASS. No new Opus, duplicate experiment, commit or
manuscript edit occurred. Full498 matrix and independent post-revision review
remain incomplete.


### 2026-10-24 17:05 Taipei - calibrated semantic review accepts three returned cases

Sol/high reproduced the B-arm failure under the immutable base reviewer's1e-10
comparison, then created a separate calibrated caller. It requires exact equality
to the expected six-significant-digit PT display, followed by the original
FF-count/identity/net/file-source checks; no blanket tolerance increase. Original
reviewer, frozen33 runtime, old blocked receipt and prior accepted receipts remain
unchanged. Six tests cover A/B displayed rates, adjacent-digit/zero/excess-precision
errors, default/missing/wrong/duplicate clocks, pending completion and new range
activity. Parent independently repeated all six PASS, reran full FCFS509B/RR509A/
RR509B semantic review into a separate directory, and matched the worker's
receipts exactly except checkedUTC. Fixed callerSHA:
53e49f6dcf97412a32503f9d505869836f1acade03176773e04494ceb021f87a.

All three cases are accepted as qualified single TT25ns zero-delay prelayout
observations; their exact prior three range warnings are mapped to current SAIF
zero-activity nets. Printed totals are FCFS509B3.355mW,RR509A2.559mW,RR509B2.559mW.
These are one seed's descriptive observations, not cross-seed confidence intervals
or a general policy winner. Parent evidence: semantic-remaining/
parent-calibration-1703/parent-release.json. Explicit parent standard wrappers
under remote-matrix/parent-standard-release-1705/ bind actual native exits,
metadata/audit/vector/sourceZIP, prepared payload, remote results/transcript,
report hashes, calibrated/base reviewer hashes and independent semantic receipt.
The index writer is integrating only these three approved anchors, with mutation
and prior-compatibility tests. FCFS509/RR509 pair-level index promotion is pending
that strict reindex; do not predeclare two matrix PASS rows. Main509B still active.
No new EDA, source/runtime modification, Opus, commit or manuscript edit was used
to repair this local reviewer calibration.


### 2026-10-24 17:09 Taipei - two matched power rows strictly accepted

Parent reviewed the minimal calibrated standard-contract index patch, reran36
index+20analysis tests PASS (zero skips/failures), verified all released file
hashes and independently regenerated index+analysis under
power-index/standard-implementation-1705/parent-acceptance-1709/.
IndexSHA2561c108014343e22bfe5332cfc992a3094f3c63726757baf8589f98b796ae84f95.
FCFS509 and RR509 matched A/B rows are now strictPASS. Overall498 matrix:
13PASS,140declaredRUNNING,344NOT_RUN,1UNRESOLVED. Remaining unresolved power row
is Main509 missing acceptedB; other seeds remain unrun/unaccepted as appropriate.
All three qualified static table-domain warnings remain explicit. This is two
one-seed matched observations, no cross-seed power CI or overall policy winner.

Parent's initial three-case manifest mistakenly nominated native_exit as the
native-receipt field; actual receipts use exit_code. The writer caught the error,
kept the original manifest immutable and created the explicit corrected manifest
with tests proving wrong native field fails closed. No native exit evidence or
accepted wrapper bytes were edited. Index accepts only the three exact approved
standard pins, their actual replay/PT schemas, and calibrated/base reviewer
hashes; legacy and recovered transport255 contracts remain compatible. New
mutation tests reject altered audits/reviewer sources/contracts and missingB.
No frozen runtime, accepted old receipt, duplicate run, Opus, commit or manuscript
change was required. Main509B remote replay and four local simulations continue.


### 2026-10-25 00:30 Taipei - overnight confirmation and remote transport audit

Continued the approved F1-F16 experiment workflow at owner-approved99400de;
no Opus, manuscript edit or commit. Parent verified core39/DAC53/power33 and
539 protected RTL/spec/manuscript hashes unchanged. Receipt:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261025T0028/source-check.json`.
Four statistics regression tests passed locally with zero skips/failures.

Core recovery `00-n4-confirmation/attempt001` now has strict runner PASS and
`revision_scope.json` PASS with120/120 valid jobs, zero problems, all244 steps
PASS and166 tests with zero failures/errors/skips. `01-one-window-causal/attempt000`
has5-job scope PASS. Independent strict reindex/analysis is being regenerated;
these group results do not complete the498-row matrix. High-quota group is
actively simulating with three workers. DAC confirmation20/20 cocotb results
and strict runner PASS precede its ongoing serialized Traffic reconstruction
and final scope seal; summary production_evidence=false/matrix_contribution0
at this checkpoint must not be promoted prematurely. DAC robustness10 remains
sealed accepted evidence.

Remote continuation stopped2026-10-24T10:42:12Z onMain509B: upload0,
power SSH255 and bounded fetch255/zero-byte archive. The three preceding cases
FCFS509B/RR509A/RR509B retain their accepted reports. Parent inspected actual
transcript; no remote EDA exit is available forMain509B. Sol/high read-only
master check now returns255 because the approved socket is absent; no password
or authentication input was captured. Original255 evidence remains intact,
with no rerun/upload/cleanup or automatic continuation. New bounded existing-
result recovery is being prepared offline; actual owner authentication and
read-only inspection must precede any result acceptance or remaining12 jobs.
All18 accepted local power inputs remain available; only two matched power
rows currently have strict acceptance.


### 2026-10-25 00:38 Taipei - complete RTL confirmation and independent arithmetic

DAC's serialized exogenous replay/source/binding validation completed with
scope PASS, production_evidence=true,20 matrix rows, zero problems. Evidence
ZIP finalized and lane supervisor reports both groups exit0/COMPLETED.
Independent strict sealed snapshot under power-index/continuation-20261025/
sealed-snapshot-20261024T163321Z accepts core120, Main1W5, DACconfirmation20,
DACrobustness10, N16resource1 and two power rows:158/498PASS. At snapshot time
Highquota15 was in final validation (UNRESOLVED rather than FAIL); Main509B
is the other unresolved row. No incomplete-cohort CI was calculated.

Parent independently recomputed nearest-rank histograms and exact paired
trace hashes from120core and20DAC results, then the fixed10000-resample
bootstrap. Main vsRR10: A delta-1 cycle CI[-1,-1], B+3.35 CI[2.25,4.45].
DAC2 vsMain: A1.10vs10 meanrunP99, delta-8.9 CI[-9,-8.75]; B12.35vs21.05,
delta-8.7 CI[-9.5,-7.9]; both20/20 seeds improve. New concise evidence record:
docs/experiments/revision-20261023/CONFIRMATION_RESULTS.md. This does not
establish an overall winner or equal-weight fairness. Main backpressure
comparators remain queued, so DAC robustness has no paired benefit claim.

Parent found an independent index reporting defect: aggregate
matrix_contribution_from_insight is hardcoded0 although conditional group
counts correctly accept30 and total158 is correct. Assigned minimal reporter
correction plus regression to the index writer outside frozen39/53/33;
original snapshots retained. No simulation or acceptance rule change.
MainB read-only recovery and semantic recipes are prepared offline; parent
repeated5recovery+4recipe tests PASS, alongside4statistics tests. Actual owner
SSH authentication is still required before any remote inspection/fetch.


### 2026-10-25 00:40 Taipei - corrected strict index173/498

Minimal insight-count reporting fix accepted after37index+20analysis testsPASS;
parent independently repeated37index testsPASS. Original deficient aggregate
snapshot retained. Corrected strict index/analysis:
power-index/continuation-20261025/conditional-count-fix/snapshot-20261024T163817Z/.
Counts173PASS/25declaredRUNNING/299NOT_RUN/1UNRESOLVED/0FAIL; accepted insight
contribution30, W256contribution0. Highquota15 now sealedPASS and the live core
queue has advanced to RRquantum ordinal3. Three actual workers, not25workers.
Parent receipt parent-continuation-20261025T0028/parent-release.json binds
actual index/analysis hashes and independently reproduced confirmation results.
No frozen runtime, old evidence, manuscript or commit changed. Main509B
remains the sole unresolved row in this snapshot, pending owner SSH login and
bounded read-only recovery. Full matrix and paper revision/re-review incomplete.


### 2026-10-25 04:10 Taipei - owner authentication restored; Main509B recovered

Owner completed the existing reconnect workflow. Actual login/probe receipts
under power-sol/remote-preparation/login-20261024T200709Z both exit0 with exact
sentinel. Parent reused that established connection; no password was used,
stored or passed by the agent. Frozen MainB read-only recovery plan/code hashes
matched the previously reviewed release and a fresh actual probe was bound.

Existing Main509B reports were fetched without upload, rerun, signal or cleanup.
Actual remote compile/sim/PT/shell exits are all0, process list empty, exact28
allowlisted files match source/payload and remote inspection hashes. Original
SSH255/fetch255 remains preserved. Recovery root: remote-matrix/
recover-mainb-20261025t0027/attempt/. Parent ran the frozen calibrated recovery
semantic recipe into semantic-remaining/continuation-20261025/
recovered-main509b-parent-0409/receipt.json: ADOPTED_SINGLE_TRAINED_PRELAYOUT_CASE,
no blocking issues,10203424total/102400measured cycles,2560000nsSAIF,9011FF
clocks,30112annotated nets,34exactconstantleaves/68constantarcs,56previously
proved disconnected always-X paths, no transientX/Z or table-range issues.
Printed total3.465mW remains a single TT25ns zero-delay prelayout observation.
Independent re-review and strict matched-row index integration are pending.

Core queue completed RRquantum25 with scopePASS and now runs depth ordinal4.
A new read-only strict index checkpoint and exact remaining12 remote serial
continuation are being prepared bySol/high. No completed cases are rerun.


### 2026-10-25 04:20 Taipei - Main509B indexed; exact remaining12 launched

Independent Main509B semantic receipt matches the parent review except its
check timestamp. Parent accepted the minimal explicit recovered-evidence index
extension after independently repeating40index+20analysis tests (60PASS).
The initial root-directory unittest invocation failed on module search paths;
rerunning from scripts/ completed all60 tests without code changes or skips.
Parent directly reinspected all six seed509 case contracts:6PASS. Original
power/fetch255 records remain separate from recovered actual EDA exits0.

Strict snapshot power-index/main509b-implementation-20261025/
snapshot-20261024T201624Z/index/matrix-coverage.json reports199PASS,
45declaredRUNNING,254NOT_RUN,0FAIL,0UNRESOLVED of498; three matched power rows
are accepted, with both A/B cases for each of FCFS,RR10,Main seed509.
No confidence interval is drawn from a partial power cohort.

Parent repeated6 exact-continuation checks and performed a fresh real strict
existing-master sentinel probe0 without login or credentials. Reviewed plan
2898f74f66bd0a4e978e503e3ec93ffa3ccf66980fdc0bf767c530062eee7db5
was launched once at04:17:45Taipei under remote-matrix/
continue-remaining12-20261025t0410/. Windows supervisor57320/child87248;
parent-launch.json and eventual parent-launch.exit.json retain native exits.
This is original17 jobs[5:] only, seeds510/511, serialone, stop first failure,
no automatic retry. All six completed seed509 cases are excluded. Firstcase
FCFS510A preflight/upload exits0; power execution is still in progress.
Every returned case remains subject to independent semantic review before
matrix adoption. No original claimed executor was restarted.

Local depth45 remains active with three actual simulator processes near99%CPU;
RUNNING45 denotes declared rows, not45workers. No completed case was rerun.
Parent source guard verified core39,DAC53,power33 and protected539 files all
unchanged. Parent acceptance evidence:parent-continuation-20261025T0418/
acceptance.json. No Opus was called; existing Sol/high workers continue.
Manuscript, physical signoff and full-matrix completion remain pending.


### 2026-10-25 07:31 Taipei - four seed510 power cases independently adopted

Actual continuation12 progress returned FCFS510A/B and RR510A/B, with Main510A
active. All four returned cases have actual transport/compile/sim/PT/shell
exits0 and verified28-file hashes. Independent Sol/high semantic review under
semantic-remaining/seed510-review-20261025t0725/ adopted all four cases, retaining
known static-pin table-range qualification. Parent independently reran the
complete calibrated semantic checks into parent-seed510-review-0732/; receipts
match exactly except checked_utc. No full10M vector regeneration or EDA rerun.
FCFS510A/B reported total3.356mW each; RR510A/B2.560mW each. These remain
TT25ns zero-delay/no-SDF prelayout observations with exact reviewed warnings,
not physical signoff or a complete power cohort inference.

Parent standard acceptance releases and cumulative10-case manifest are in
parent-continuation-20261025T0728/power-acceptance/. Minimal existing-contract
index pin update is assigned to Sol/high; pending strict reindex, last accepted
aggregate remains199/498. No original SSH255 evidence was overwritten.

Depth raw summary has24/45 cocotb simulations PASS,72recorded steps PASS, with
three live simulators near100%CPU; group still unsealed. Parent independently
reran sealed sensitivity analysis:45runs,90profile endpoints,18five-seed tables,
90same-seed default pairs, no CI, no parameter tuning. Report accepted at
SENSITIVITY_RESULTS.md. High quota5 worsened trainedB mean run-P99 by11.4cycles;
quota20 improved it by3.8cycles with A unchanged. Main1W B changed+0.2cycles,
not a consistent benefit. Class budgets and closed-loop history differ, so no
free fairness or general winner claim is made.

The existing sensitivity script regenerated its statistics UTC/digest during
parent reproduction. A subsequent assertion against the original byte digest
failed, was investigated, and is explicitly documented in checkpoint.json;
the original release receipt and tracked report are unchanged. This is not a
frozen-source mismatch. Core39,DAC53,power33 and protected539 all match.
Parent receipt:parent-continuation-20261025T0728/checkpoint.json.
Manuscript stays read-only; no Opus calls or commits.


### 2026-10-25 07:33 Taipei - strict index201/498; five power pairs

Parent accepted only the four exact standard seed510 release hashes in the
existing index allowlist. The indexer schema and semantic acceptance logic are
unchanged. Parent independently repeated41index+20analysis tests:61PASS, then
directly checked all10 actual case contracts and release/source hashes.
Strict snapshot power-index/seed510-implementation-20261025/
snapshot-20261024T233121Z/ reports201PASS,45declaredRUNNING,252NOT_RUN,
0FAIL,0UNRESOLVED of498. Five of nine matched A/B power rows are complete;
10of18 individual activity captures have adopted returned power evidence.
Main510 and all511 power pairs remain unaccepted. The producer inputs for
all18 captures were already accepted; this count concerns remote output review.

Parent receipt:parent-continuation-20261025T0728/index-acceptance.json.
Core/DAC confirmation inference is unchanged. No partial power-cohort CI or
cross-profile overall ranking. Depth45 remains unsealed; no raw result is
promoted merely because its cocotb step passed. Existing local/remote queues
continue without duplicate jobs. Manuscript remains read-only.


### 2026-10-25 10:26 Taipei - depth45 sealed; adaptation active; remote transport stopped

Depth45 scope is PASS with45valid jobs,94steps/91tests,zero failures/errors/
skips. Parent independently ran the existing strict bundle inspector:sourceZIP,
evidenceZIP, exact configs/traces/rows/JUnit/exit/source binding all PASS.
Core queue advanced ordinal4exit0 to adaptation9 ordinal5 with three live
simulators near100%CPU. Parent fresh strict index and analysis both exit0:
246PASS/9declaredRUNNING/243NOT_RUN/0FAIL/0UNRESOLVED of498; power remains5/9
accepted pairs. Adaptation raw summary has no completed cocotb job yet.
Index/analysis and parent release:parent-continuation-20261025T1025/.

Remote continuation12 stopped at Main510A. Power SSHouter255 ended07:57:22,
fetch255 ended07:57:23; parent supervisor exit1. The first four seed510 cases
remain accepted. Actual master-control check at10:22:47 exits255 because the
configured Unix control socket does not exist. This establishes transport/
authenticated-session unavailability only, not VPN root cause or actual EDA
failure. Main510A remote EDA exit remains UNKNOWN until real inspection.
No blind rerun, upload, cleanup or continuation restart was attempted.

Sol/high prepared an exact existing-case read-only Main510A recovery using the
frozen earlier verified inspect/fetch implementation. Parent identified copied
MainB labels; author fixed both labels and added assertions before release.
Parent repeated all5 testsPASS, checked exact plan9b81a4efeaf10234ea0ccadff253f86d
db00b4dc3ed79042aa6c26e8a5c068bd and source freeze. Recovery has NOT executed;
it requires an actual restored-master sentinel probe. Prior failed transport
records and failed drafts are retained; remaining seven never-started cases
are not silently resumed. No credential was used or logged by the agent.

Core39,DAC53,power33,protected539 remain unchanged. Depth descriptive analysis
and independent adversarial evidence review are underway; no extra parameter
selection, confidence interval or full-system claim. No Opus, manuscript edits
or commits. Full matrix/power cohort and manuscript re-review remain pending.


### 2026-10-25 10:33 Taipei - independent depth review adopted; adaptation still active

Parent adopted the corrected independent depth45 audit after rehashing all six
release members, the released depth report, and all39 frozen source files.
Audit status is NO_OBSERVED_DATA_DEFECT with45actual RTL rows/91existing JUnit
tests and no issues. The first15class flags were an audit expectation error;
its failed snapshot remains preserved. Literal Main H+DOWN enters B_H on the
first closing window, then B_H+DOWN enters L. No RTL/result change was needed.
Parent receipt:parent-continuation-20261025T1030/depth-independent-adoption.json.

Depth findings retain generation/admission distinctions and drain completions.
For representative seed509, heavy generation-to-fire P99 remains239925cycles
across depths while internal waiting changes7/15/31cycles. Sparse cohorts
complete under background-on guards. No throughput improvement, depth-specific
PPA optimum or general fairness/starvation bound is inferred.

At10:30, adaptation9 has0completed raw jobs and three live simulators near100%
CPU, observed around4.75M-5Mcycles. No strict promotion or partial-cohort CI.
Strict matrix remains246PASS/9declaredRUNNING/243NOT_RUN of498. The existing
HOG analyzer does not analyze the continuous role-switch adaptation cohort;
independent interpretation is being prepared without new simulation or tuning.

Actual SSH master-control check at10:30:37 returned255:configured socket absent.
No newer owner login/probe receipt exists. No remote login, recovery, EDA,
password handling, upload or cleanup was performed. Main510A actual remote
EDA status is still unknown; reviewed exact inspect/fetch recovery is frozen.
Remaining-seven offline continuation preparation may proceed, but execution
requires restored authentication and accepted Main510A recovered semantics.
No manuscript edits, Opus calls or commits.


### 2026-10-25 15:57 Taipei - restored SSH; Main510A recovered/adopted; exact7 launched

Owner restored authentication via login-20261025T074858Z; login and exact
strict-pinned sentinel both exit0. Sidecar also verified a fresh sentinel and
created the frozen parent-auth binding. Parent exclusive-create attempt found
the existing binding and did not overwrite it; the reviewed recovery helper
validated that receipt and successfully inspected/fetched existing Main510A.
No EDA rerun/upload/signal/cleanup was performed for that recovered case.
Parent independently rehashed all28files and actual compile/sim/PT/shell exits0.
Original power/fetch255 evidence remains intact.

Independent recovered semantic review and parent repeat both adopt Main510A;
parent repeated14focused testsPASS. Actual10.1Mcycles/100kmeasured,SAIF2.5Mns,
9011FFclocks,30112nets,34constantleafgaps/68constantarcs and56previously-proved
disconnected always-X paths are retained. No check_power table issues. Reported
power3.467mW is a single TT25ns ideal-clock/zero-delay prelayout case, not a
complete-cohort or physical-signoff comparison. Parent receipt SHA
63d1278c39245511d136f4d6413c6eed49b2274f04325d9ec75f594cad655c66.

Parent reviewed exact remaining7 adapter and repeated5testsPASS. All semantic,
source/history/payload and fresh-auth gates passed before new exclusive claim.
Started WindowsPID54984 at15:55:52, plan56197ceafef65e02922217cd5b0a34f263e347
b588ad7b248ccc2eefd48f7e7b. Actual progress RUNNING_SERIAL_REMAINING7, active
Main510B; its preflight/upload exit0 observed. Exactly Main510B plus six511
cases; no completed-case retries. Stop-first-failure/no-autoretry and per-case
semantic acceptance remain mandatory. New ignored execution scope:
remote-matrix/continue-remaining7-prepared-20261025t1033/.

Local adaptation9 is now sealedPASS; parent direct strict inspection accepts9
configs with no problems/failures. Fresh worker index/analysis exit0 reports
255PASS/180declaredRUNNING/63NOT_RUN of498. Robustness180 is active; no raw
partial job is promoted. Adaptation classifier/role-switch interpretation is
being audited separately because the HOG analyzer excludes this schema.
Power has11individually adopted captures, still5completeA/B rows pending
Main510B; strict index extension for recovered Main510A remains under review.

Parent guards core39,DAC53,power33,protected539 allunchanged. No Opus, credential
use, manuscript edits or commits. Overall matrix and manuscript re-review
remain incomplete. Receipts:parent-continuation-20261025T1550/.


### 2026-10-26 01:34 Taipei - adaptation interpretation adopted; robustness93 raw; Main510B transport loss

Parent repeated45index+20analysis testsPASS and adopted the exact Main510A
index extension. Eleven accepted single captures yield5completeA/Bpower rows;
Main510A alone creates one explicit unresolved pair, not a sixth PASS. Fresh
strict snapshot/index+analysis exit0:255PASS/180declaredRUNNING/62NOT_RUN/
1UNRESOLVED/0FAIL of498. Parent rehashed all snapshot release members.
Robustness has93/180raw successful simulations but remains unsealed; three
actualsimulators advanceCPUtime, so raw93 does not promote formalrows.

Independent adversarial review of adaptation9 finds no material discrepancy:
54windows/216literal transitions/405latency distributions/three complete
Alg2-Main1W observable pairs/104report table rows/55existingJUnit cases match.
Parent adopted the report and preserved its reviewed original bytes/hash.
One prose precision correction changes22numericexit0 to21toolsteps numeric0
plus one derivedscopePASS. Numeric results, source and reporttables unchanged.
Direct frozen-v1 audit correctly detected that reporthash change; noassertion
was waived. Parent reran all5mutation tests against the exact archived report
bytes:PASS. Parent asserts the current report differs only by that one sentence.
Evidence:parent-continuation-20261026T0124/adoption.json and
adaptation-independent-20261026t0124/RELEASE.json.

Observed adaptation result:Alg2/Main1W classes react at5M versusMain10Mcycles
after alignedroleswitches, but earlier classification does not reduce sparse
whole-role latency here; heavymeanwait is lower and sparsemeanwait higher.
Main settles at phaseend. No latencyrecoverybound, per-windowP99, independent
Alg2/1Wmechanism, fullcyclecrossRTLproof or universalwinner is inferred.
Three explorationseeds only; negative results retained.

Remote exact7 stopped atMain510B:powerSSH255 ended2026-10-25 17:56:29Taipei
after7218.474seconds, fetch255 followed. Noneofremaining6waslaunched. Actual
remoteEDAexit remainsUNKNOWN. Currentmastercheck2026-10-26 01:24:43 exits255
because configuredsocketmissing; noownerloginor remoteinspection attempted.
Existingcase-only recovery is being prepared; no blind rerun, upload, signal
or cleanup. Repeatedapproximately2htransportloss is underread-onlydiagnosis,
notattributed toVPN orEDAwithout evidence.

Core39,DAC53,power33,protected539 unchanged byparenthashguards. NoOpus,
passwordhandling, manuscriptedits orcommits. Wholematrix/powercohort and
post-approved-manuscript independentre-review remainincomplete.


### 2026-10-26 05:11 Taipei - robustness114 raw; recovery12 tests; SSH master still absent

Parent adopted the source-bound read-only0505 checkpoint after independently
rehashing every released member. Strict matrix remains255PASS/180declaredRUNNING/
62NOT_RUN/1UNRESOLVED/0FAIL of498. Robustness114/180raw successful simulations
(+21 since0128) remains unsealed and contributes0formalPASS. Three actual
simulators advance CPU; no new simulation or partial-cohort CI was launched.
N8remaining30 and N16remaining29 are not started; existingN16resourcePASS retained.
Evidence:parent-continuation-20261026T0505/worker-progress/release.json and
parent-continuation-20261026T0508/checkpoint-adoption.json.

Parent independently repeated all12 exactMain510B recovery tests:PASS, exit0,
with exact released code/plan/test hashes recorded in0508/main510b-tests-12.json.
Prior six-test receipt remains unchanged. Current05:07:55 mastercheck exits255:
configured Unixcontrolsocket missing. No credential, login, upload, EDA retry,
existingcase recovery or cleanup was performed. ActualMain510B EDA remains
UNKNOWN; prepared recovery can inspect/fetch only the original existingcase.
Sol/high prepares detached remaining6 transport offline; implementation and
independent review are pending, and no remaining6 case is authorized to launch
before actualMain510B semantic acceptance plus freshauthenticatedprobe.

Parent refreshed the issue-ledger table to reflect accepted sensitivity/depth/
adaptation and11remote captures/fivecompletepowerpairs. This changes status
prose only, not manuscript/results. Parent currenthashguards:core39/DAC53/
power33/protected539 allunchanged. NoOpus, manuscript edits or commit.
Wholematrix, powercohort, finalPDFQA and post-approved-manuscript independent
three-reviewer re-review remain incomplete.


### 2026-10-26 05:22 Taipei - detached remaining6 offline implementation reviewed; execution gated

Sol/high froze exactremaining6seed511 detached transport; codeSHA02de40a162802d04
ad90cbbe5f3996b16adbf07bee5649c3ff3cad2bcbd2c7fb, planSHAf5d3a1f3f486e2e00e7c
bffe952010c3695d837474ae0264029c908c67a9be78. Parent rehashed full releaseinventory,
independently repeated15unit testsPASS and actualWSLharmlessfixturePASS:wrapper7,
duplicate launch refused. Parent AST-checks prove copied nativefixture launch/
pollfunctions andWORKERbytes match released source. No realEDA/network.
Independent Sol/high reviewer repeated15isolatedtests and reports no blocking
findings; parent adopted exactreview hashes. Evidence:parent-continuation-
20261026T0508/detached-parent-checks.json, detached-adoption.json, and
detached-independent-20261026t0508/RELEASE.json.

The independent review's parent-native-report label user-provided describes
its received message, not the origin of the measurement: parent tooling actually
executed that nativefixture and retained raw outputs/exit in parentchecks.
Frozen independentreview remains unchanged; adjacentadoption clarifies provenance.

Implementation readiness is separate from execution: actualMain510B recovered
semantic acceptance and freshstrictmasterprobe are absent. No newcase launched,
oldclaims not restarted, no cleanup. New detachedcontract distinguishes actual
inspectedEDA0 from SSHlaunch0 and grants no automaticstandardindex acceptance.
Real schoolhost disconnect survival and actualdetachedresult semantic/index
integration remain unverified. Localcorequeue continues; fullmatrix incomplete.
NoOpus, manuscriptedit orcommit.


### 2026-10-26 05:37 Taipei - Main510B recovered/adopted; exact6 detached execution started

Owner restored authentication. Parent verified an actual strict existingmaster
probe0/exactsentinel, then executed only frozenMain510B existing-result recovery.
Actual compile/sim/PT/shell exits0, idle state,28download hashes and identical
source-before/after are verified. Original power/fetch255 remain unchanged;
no Main510B EDA rerun, upload or cleanup. Independent Sol/high semantics adopt
the actual B case,102,400measured cycles/2,560,000ns,9011FFclocks/30112nets,
34exactconstant annotation gaps, no check_power issues. Printed total3.466mW
is a single TT25ns zero-delay prelayout result, not a completed-powercohort claim.

Parent repeated semantic execution and full direct14test entrypoint:PASS.
Semantic receipts differ only by checked_utc. Initial byte-level receipt check
correctly noticed timestamps; initial unittestdiscover collected8 recoverytests
because directentrypoint adds6frozen calibrationtests. Both procedural facts
and the final actual14PASS are retained in0524/semantic-adoption-check-notes.json.
Parent semantic releaseSHAa99c7cb934407753df9ed1d394b314c08d05f26c998f4d7228071c9
b420a2f92 passes exact6 mainb_gate. Twelve singlecaptures are semantically
accepted; strict sixthpowerpair index extension is in progress.

Parent reviewed the minimal Windows-owned wrapper and independently repeated
its4tests, including an actual harmless nativechildexit7. Freshstrictprobe and
existing adopted exact6 implementation gates passed. At05:34:58Taipei the
reviewed wrapper72940 launched controller36688. Firstcasefcfs-A-s511 preflight,
upload, detachedlaunch and firstpoll all exit0; actual remotePID142335 with
bound startticks is ACTIVE. ActualEDAexit remainsUNKNOWN_RUNNING, notPASS.
Six exactseed511cases execute serially; no oldclaimedexecutor restarted.
Ontransportfailure the controller stops, retaining the pendingcase for read-only
recovery; detachedsurvival under actualschoolhostdisconnect remains untested.
No automaticstandardforeground-contract index acceptance is granted.

Evidence:parent-continuation-20261026T0524/main510b-recovery-check.json,
main510b-semantic-adoption.json, remaining6-launch-review.json and
remaining6-actual-launch.json; native wrapper receipts underremote-matrix/
continue6-windows-launch-20261026t0524/job. Toolsession66779 owns the wrapper.
Localcore robustness remains114/180raw and unsealed at0524; three simulators
continue. Prior strictmatrix255/498 remains untilnewindexadoption. NoOpus,
passwordhandling, manuscriptedit orcommit.


### 2026-10-26 05:42 Taipei - Main510B exact index adopted;256/498 formalPASS

Parent adopted the exact Main510B-only index extension and new cumulative12case
manifest. Author49index+20analysis PASS; parent independently repeated49index
PASS; independent Sol/high reviewer49PASS with no concrete findings. Parent
rehashes final source/artifact inventory and independentrelease; sources remain
frozen during checks. Actual12captures/6completeA/Bpowerpairs are strictly
accepted. Snapshot256PASS/180declaredRUNNING/62NOT_RUN/0UNRESOLVED/0FAIL of498.
Main510A/B pair now completes one additional row; no unsealedrobustness, seed511
or runningdetachedcase is promoted. Historical snapshots and original255 stay.

Evidence:power-index/main510b-index-20261026T0534/release.json SHA710c64eacc6ac611
d08d6f53899d6828a0270c8dee1b4682c350948924fd3263 and parent-continuation-
20261026T0524/index-main510b-adoption.json. Parentreviewed wrappers and actual
Main510B receipt are pinned, not generic recovered-case approvals.

Exact6seed511 serialqueue remains on firstFCFSA with realremoteACTIVE polls.
Frozencontroller/wrapper unchanged. Necessary detached-result semanticcaller
is assigned toSol/high in a separate ignoredscope; it must use explicit actual
poll/inspection evidence and preserve calibrated raw checks, never fabricate a
foregroundpower receipt. Actual511semantic/index acceptance remains pending.
No additional EDA/PPAclaim, manuscriptedit, Opus orcommit.

### 2026-10-26 06:18 Taipei - Core120 raw; first detached511 result returned

Parent continued the existing queues without duplicate simulation or remote EDA.
Read-only worker checkpoint confirms120/180 robustness raw results PASS
(FCFS/Main/RR1/RR10 thirty each), zero recorded failures/errors/skips; three
ALG2 simulators advance CPU. The group remains unsealed and contributes no
new strict rows. Formal matrix remains256PASS/180declaredRUNNING/62NOT_RUN.

Detached FCFS511A returned actual wrapper/compile/sim/PT/shell exits0 and28
hashed files. Queue automatically advanced to FCFS511B. Semantic/index adoption
is pending. Parent's first actual semantic review stopped on upload command
reconstruction mismatch; required-member set literal order is under targeted
review, not waived. A separate unit test also incorrectly assumed the live
case was still pending after it completed; test fixture repair is assigned.
These are review-tool issues under investigation, not established EDA defects.
Failed receipt remains in detached-semantic-20261026t0540/parent-fcfs-A-s511-0619.

Parent source check confirms core39, DAC53, power33 and protected539 files
unchanged. Evidence: parent-continuation-20261026T0618/worker-progress and
parent-source-check/source-guard.json. No manuscript edit, commit, Opus call,
password use or additional experiment was performed.

### 2026-10-26 06:23 Taipei - First detached511 capture independently adopted

Root cause of the upload comparison failure was confirmed: the frozen upload
helper renders an unordered Python string set in process-dependent order.
The local reviewer now canonicalizes only string-literal set order inside the
upload command. All other Python source bytes, SSH argv, payload hashes and
trust/transport checks remain exact. Changed members, code, hash, limits and
options are rejected. Two different PYTHONHASHSEED processes reproduce the
original mismatch. The stale pending test now uses synthetic pending evidence.
Old blocked reviews and original release are retained; no raw evidence changed.

Author10tests, parent10tests and independent10tests PASS. Actual independent
and parent FCFS511A semantic receipts agree except checked_utc. Parent rehashed
all bound rawtransport and launchcontext files before adopting the exact case:
parent-continuation-20261026T0618/parent-fcfs511a-semantic.json SHA
b401165cc68e36c0cf29601f95de4ae6bfa9218f4af6cfb7903415edaff7c89f.
8856 FFclocks and complete27689 net annotation are checked; printed total
3.356mW retains exact prior static-pin range warnings. Actual wrapper and all
EDA exits0 are separately evidenced; no foregroundpower exit file is invented.

This is one accepted capture, not an A/B matrix row. Strict detached index
integration is assigned to Sol/high; previous256 formalPASS remains pending
its review. Serial queue continues FCFS511B. No simulation/EDA rerun, manuscript
edit, Opus invocation or credential handling.

### 2026-10-26 06:31 Taipei - Detached index extension adopted;13 captures/six pairs

Parent reviewed the final three-file index change, rehashed the complete writer
release/artifact inventory, directly inspected actual FCFS511A through the new
index path, and independently repeated55 index plus20 analysis tests:PASS.
Independent Sol/high reviewer55PASS, all49 legacy test functions unchanged,
all13 actual cases PASS and prior12 case objects/records unchanged, no concrete
findings. The index only loads the pinned read-only detached validator; it never
calls its output-producing reviewer, controller or SSH. Fake foreground receipts,
unapproved cases, changed proofs and unpinned semantic releases are rejected.

Parent acceptance: parent-continuation-20261026T0618/index-detached-adoption.json
SHA33cca816ef03da81af2f9c047ae68e8c63a1fe3656b2d58302a37c6209cc991a.
Writer release power-index/index-detached-20261026t0623/release.json SHA
27ca17c1349b553e6ffe16a56a63569d12c3e1b750b89b120a57b7494f805c9f;
its snapshot/index and snapshot/analysis preserve complete prior cohorts.
Current matrix256PASS/180declaredRUNNING/61NOT_RUN/1UNRESOLVED/0FAIL of498.
The unresolved row is accepted FCFS511A awaiting B; not a hardware failure.
No formalPASS gain, incomplete-cohort CI or unsealed robustness promotion.
Serial remote queue remains FCFS511B active; local core queue remains active.
No new simulation/EDA, manuscript edit, Opus or credential use.

### 2026-10-26 06:39 Taipei - FCFS511 pair closed;257/498 formalPASS

Latest observation supersedes the earlier B-active checkpoint: FCFS511B also
returned and the serial queue advanced to RR511A. Unchanged reviewer4d04...
independent and parent actual B reviews agree except checked_utc. Exact28hashes,
actual wrapper/EDA0,8856 FFclocks,102,400 measured cycles/2,560,000ns/TC204799,
source and static-pin range qualification are checked. Printed total3.357mW is
qualified prelayout evidence. No full reviewer unit rerun was needed for the
unchanged source. Parent B release SHA2b6888ef0c6a3a87ba3c05b069514e5e30a860af708
2e41050aa8e7344df280f is separately pinned.

The minimal existing detached index branch now accepts only the two adopted
FCFS511 arms. Author56 index tests and parent independent56 PASS, including
complete-pair/duplicate rejection; analysis20 regression is reused from the
unchanged earlier release, while the new actual index and analysis CLI both
execute exit0. Independent final review reports no concrete findings and
confirms14 actual cases/seven pairs, unchanged prior13 records and raw B
qualification. Parent rehashes both releases/artifacts, directly inspects B
through the final index and adopts the exact final files.

Current strict matrix257PASS/180declaredRUNNING/61NOT_RUN/0UNRESOLVED/0FAIL.
This closes one power row, not the remaining study. Final acceptance:
parent-continuation-20261026T0618/index-detached-pair-adoption.json SHA
062997432cead942458dc1b02a270cf8b52976a1e0001fb665ff793f4280ba03.
Writer release:power-index/index-detached-pair-20261026t0636/release.json SHA
3c6a6a334bd965ac49656997b661d23a4ff4b71c3e848e341d6f42084fa3dd32.

Local read-only inspector validates123/180 raw robustness PASS, zero failures,
errors or skips; three actual simulators advance CPU and summary remains
RUNNING/unsealed. Evidence:final-local-check/checkpoint.json. Parent final
source-guard-final.json confirms39/53/33/protected539 unchanged. No duplicated
simulation, extra EDA launch, password handling, manuscript edit, Opus or commit.

### 2026-10-26 09:10 Taipei - All remote power commands finished; final four semantics adopted

The detached six-case controller completed with actual Windows child exit0 at
08:26:26 Taipei. All six returned result manifests match their observed hashes;
no remote process or simulation was restarted. This supersedes the earlier
RR511A-active checkpoint. Parent and independent Sol/high actual semantic calls
for RR511A/B and Main511A/B match except checked_utc. All exact28 returned hashes,
launch/inspection proofs, source bindings, actual EDA exits0 and policy-specific
annotation/clock/constant-path checks passed. RR retains the exact three prior
static-pin table-range qualifications; Main has no table issues. Parent adopted
the exact four cases in parent-continuation-20261026T0906/final4-adoption.json.
This brings semantic acceptance to18/18 captures; final index integration and
nine-pair descriptive reporting are in progress, not yet strict matrix promotion.

Fresh read-only inspect_partial validates138/180 core robustness raw runs, zero
errors/failures/skips. Three live simulator processes advance CPU; the group is
still RUNNING and unsealed, contribution0. N8/remainingN16 groups have not started.
Evidence:checkpoint-20261026-current/checkpoint.json. Parent source-guard.json
confirms core39/DAC53/power33/protected539 unchanged. Existing strict snapshot
remains257PASS/180declaredRUNNING/61NOT_RUN of498 until new index acceptance.
No SSH/EDA rerun, new Opus call, password handling, manuscript edit or commit.

### 2026-10-26 09:15 Taipei - Matched trained power fully indexed:18 captures/nine pairs

Parent adopted the final three-file index release after rehashing all three
sources and20 writer artifacts, independently repeating57 index tests (16.350s,
exit0), directly inspecting the last four actual cases through the final common
index path, and checking the independent no-findings release/artifacts. The
previous14 manifest objects remain byte-equivalent as parsed objects; exact
RR/Main511 releases are pinned. Sixteen independent changed-proof/identity
mutations fail closed. No foreground power exit receipt is fabricated.

Acceptance:parent-continuation-20261026T0906/index-final18-adoption.json.
Writer:power-index/index-detached-final4-20261026t0912/release.json SHA
 d8ac633b07b71af588a8a4c3a79fc877416651510ffe7a52739c3a14864401e7.
Independent:final18-index-independent-20261026/RELEASE.json SHA
 f6f456b2920b698366149683ed5e004da8050c361f53f6826600d906a7ac8eed.
The strict snapshot and analysis both exited0:259PASS/180declaredRUNNING/
59NOT_RUN/0FAIL/0UNRESOLVED of498. All18 matched trained captures/nine A/B
rows are accepted; historical cold/boundary power stays separate. Static-pin
range qualifications, disconnected-X/constant-path proofs and prelayout limits
remain. No full-study completion, physical signoff or manuscript fix is implied.
The descriptive three-seed power report is being finalized. No extra simulation,
remote call, Opus invocation or commit was needed for this index adoption.

### 2026-10-26 09:23 Taipei - Trained-power descriptive report accepted

TRAINED_POWER_RESULTS.md is generated and accepted for exact18 captures/nine
pairs. Report SHA d1fa1aa3f624b22cc5d04f32c09988e29129cb8ac1c38575bfaf9c4de0311aad.
The reproducible standard-library analysis records printed internal/switching/
leakage/total W values, six policy/arm summaries across exploratory seeds509-511,
observed ranges, matched trace/profile/window checks and policy-specific static
qualifications. Four author selfchecks pass. Parent independently checks18 row
identities,24 component mean/range statistics and six matched trace groups;
independent Sol/high report review reports no findings. No confirmation CI or
causal/physical/general power claim is added. Mean total mW A/B:FCFS3.356/3.356,
RR10 2.5596667/2.560,Main3.4666667/3.466; extra mean digits are arithmetic only.

First analysis rejected an incorrect assumption that B warmup equalled its10M
training. Exact per-arm expectations were corrected (B warmup10,101,024,
measured102,400,total10,203,424); failed log retained and final18 analysis passed.
A later introductory prose clarification changes no numeric code/results;
original generating source bytes/hash are archived rather than silently rebound.
Writer release SHA de013ee77aad3ede0fa2505c32d554d38cd6b158249c401c7525cfe635913b0e.
Independent report release SHA921f85f1a92ccd5a9cb462d74c13668c4637798a132e94877f47d2da9d3fe349.
Parent acceptance:parent-continuation-20261026T0906/power-report-adoption.json.
F12 matched trained activity evidence is complete; manuscript wording/PDF QA
and physical signoff remain outside this acceptance. Core robustness is still
unsealed; strict matrix remains259PASS/180RUNNING/59NOT_RUN of498. No extra
simulation/remote EDA, Opus, password handling, manuscript edit or commit.


## 2026-10-26 15:29 Taipei - robustness180 strict acceptance

Parent adopted the sealed180-run trained-robustness bundle after independent
strict bundle inspection and rehashing all19 artifacts of the Sol/high index
release. The canonical39-source closure and DAC53/power33/protected539 guards
remain unchanged. Acceptance receipt:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261026T1518/robustness-index-adoption.json`.

The accepted snapshot is
`power-index/robustness-sealed-20261026t1518/snapshot` under the ignored
revision-20261024 evidence root:439PASS/30declaredRUNNING/29NOT_RUN of498,
zeroFAIL/UNRESOLVED. Robustness contributes180 exact valid jobs,364PASS steps
(363 numeric tool exits0 plus one derived scope) and226 retained tests, zero
fail/errors/skips. No tests or simulations were rerun for this adoption.

Parent independently matched ten DAC2/Main backpressure runs by seed, exact
configuration and arrival trace, recomputed20 profile P99 endpoints, checked
phase cycles/ready counts, zero avoidable bubbles and drained outstanding/backlog.
Mean DAC2-minus-Main run-P99 deltas are -12.2/-12.2 cycles for Bernoulli0.75 A/B
and -9/-7 for periodic48/64 A/B; every group improves for5/5 exploration seeds.
The maximum decrease in heavy phase fire fraction is0.006521880910454575
percentage points. These are descriptive509-513 comparisons without CI.
The unfavorable Main burst32 B result is retained:88.8 versus RR10 74.4 cycles.
This evidence does not establish a universal ranking or full demand estimation.

At15:26, supervisor288 and N8 group3655652 were live with three simulators
3657370/3657386/3657402 at99.9%CPU. Thirty declared N8 rows are active;29 N16
rows follow. Unsealed N8 results are not PASS. The robustness narrative report
and independent narrative review remain pending separate adoption. Parent
updated current ledger/confirmation/analysis status; historical checkpoints,
manuscript and frozen simulation inputs were preserved. No SSH was needed.


### 2026-10-26 15:31 Taipei - independent robustness evidence review adopted

Sol/high independent reviewer found no concrete issue in the sealed180-run
group or strict439-row accepted snapshot. It independently checked39 source
files/archive,183 JUnit files/226 tests,30 matched trace groups,8,100
histogram/conservation checks,24 core comparisons and20 DAC/Main endpoints.
Parent rehashed the release and all8 bound artifacts before adopting it:
`parent-continuation-20261026T1518/robustness-independent-adoption.json`.
Independent release SHA256:
`6618a75740ec5d4136806ae7eb8fcf80d5f6441443a8add5a14269433c5abd07`.
The robustness narrative report remains pending and was explicitly excluded
from this adoption. No new simulation, unchanged test rerun or SSH occurred.


## 2026-10-26 16:07 Taipei - robustness narrative adopted; N8 progressing

The Sol/high robustness writer froze `ROBUSTNESS_RESULTS.md` and its analysis;
parent verified8 released artifact hashes and205 bound input hashes, plus20
service pairs with exact integer Fraction arithmetic. The independent Sol/high
review verified72 summaries,24 core plus4 DAC comparisons and20 service rows,
with no concrete findings. Parent accepted the report only after rehashing
that independent release and all writer/report bindings:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261026T1600/robustness-report-adoption.json`.
Report SHA256: `9493e7c765f94fb078ce1a1013077f4c93a3c669ea45189f2b53d7982c0d8a48`.
Independent narrative release SHA256:
`99ec78ae039d46d521500c629969554aa9df26cb2d8339bee57ffb64f62074da`.
The frozen report's initial pending-review statement is superseded by the
adjacent parent adoption receipt, preserving its generating bytes.

The report retains the unfavorable Main burst32 B comparison, distinct
phase-service/generation-cohort denominators, exploration-only509-513 scope
without CI, and DAC coverage limited to two readiness perturbations. Parent
also checked concrete seed509 Main A heavy-rate examples: heavy050 retains
at least187450 producer requests and heavy090 at least227355 during the phase.
Both have100000 phase fires. Thus these lower-arrival-rate measurements are
not unsaturated low-load experiments. Evidence:
`parent-continuation-20261026T1600/load-interpretation-check.json`.

Prepared N8/16 analysis reuses exactly60 existing identities, including the
already accepted N16 resource case once and59 queued cases. Parent identified
a provenance field named canonical_source_sha256 that held the matrix-script
hash rather than the core39 closure. The ignored readiness writer preserved
all original bytes, renamed it matrix_script_sha256 and added core_source_sha256;
parent verified the corrected release and60 unique IDs. This was a preparation
metadata naming repair, not an RTL/evidence defect; no prepared commands ran.
Corrected readiness release SHA256:
`38088bb6bb7f5b205eb2acac12e0e329a7579119ef83a2d263da03e59bd7a62d`.

At16:06, N8 has6 successful raw cocotb steps of30, no failed recorded step,
and three live simulators at99.7%CPU. The group is unsealed and contributes
no new accepted rows:439PASS/30declaredRUNNING/29NOT_RUN of498. After N8,
remaining N16 cases are25 plus4, preserving resource1 separately. Current
source guards again match core39, DAC53, power33 and protected539. Receipt:
`parent-continuation-20261026T1600/current-checkpoint.json`.
No new simulations, SSH, unchanged suite reruns or manuscript edits occurred
in this reporting/adoption work. Final498 closure, paper revision approval,
PDF QA and independent post-revision three-seat review remain outstanding.


## 2026-10-27 02:09 Taipei - N8 sealed30 independently adopted

The existing core queue completed ordinal7 with exit0 and moved to ordinal8.
N8 has30 exact valid jobs,64PASS steps and76 retained JUnit testcases, zero
fail/errors/skips/notrun. Thirty lint,30 cocotb and3 Python tool steps have
numeric exits0; one derived scope step has no process exit. Parent independently
strict-inspected the bundle, recomputed60 sparse generation-cohort histogram
endpoints, verified five same-seed traces across all six policies, zero drain
outstanding/backlog and zero avoidable bubbles. No runs or unchanged suites
were rerun.

The new strict index/analysis exited0, preserving all prior439 accepted records
and all18 matched-power captures/nine pairs. Parent rehashed16 writer artifacts,
compared12 cohort summaries to independent arithmetic, then adopted after the
Sol/high independent audit found no concrete findings. New current matrix:
469PASS/25declaredRUNNING/4NOT_RUN of498, zeroFAIL/UNRESOLVED. Adoption:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261027T0202/n8-adoption.json`.
Writer release SHA256:
`da7dbdfb2b21172aa90c2e20b6f1b9eee9328d17e727078d68fa1e8717335ff6`.
Independent release SHA256:
`5c7b8a3bd1f97e37fe06ea0addad8ae487f27d3ab38e6cb2748516531c6a49cb`.
SourceZIP SHA256:
`49790bc5af693f4c84d97fd543ffbdc92062f7e28c26f54b06d18446e4cae94b`.
EvidenceZIP SHA256:
`dbe63d50b69b9db655c2c5e1e0de1518b56c3f369a68a93937ac4bae767fd5d3`.

N8 mean run-P99 A/B cycles (five exploratory seeds509-513): FCFS20/37.6,
RR1 2/20.2, RR10 12/21, Main10/27.6, Algorithm-2 10/28.2, BLISS2/37.
Main beats FCFS by10cycles in both profiles, beats RR10 by2 in A and loses
by6.6 in B. These are descriptive same-N comparisons without CI or an overall
winner. N8 has seven sparse sources, expected aggregate7/128 requests/cycle
and128 FIFO slots; cross-N load/storage changes prohibit a fixed-demand causal
interpretation or equal trace pairing across N.

An ignored Sol/high preparation additionally checked N8 service denominators
and exact60 inventory (including the prior N16 resource case once), with a
full60 missing-adoption guard that correctly rejects incomplete evidence.
Parent verified all8 prepared artifacts; no full60 summary or tracked N report
was produced. The independent auditor initially assumed29 running N16 rows;
it corrected its own expectation to25 active plus4 notyetstarted, preserving
failed audit bytes. This was an audit assumption error, not an index defect.

At02:08:51, ordinal8 has24/25 successful raw cocotb steps, one actual N16
simulator1101166 at99.7%CPU, and no final scope/archive seal. Ordinal9 four
remaining FCFS cases are not started. Raw outputs contribute no new PASS.
The accepted N expansion count is31/60 (N8 thirty plus N16 resource one).
Core39/DAC53/power33/protected539 remain unchanged. Parent updated current
ledger/confirmation/analysis pointers, preserving manuscript and historical
checkpoints. Full498 closure, full N report/review, separately approved paper
revision, final PDF QA and post-revision independent three-seat review remain
pending. This adoption used no SSH or new simulations.


## 2026-10-27 02:55 Taipei - N16 non-FCFS25 independently adopted

The core queue completed ordinal8 with exit0. This exact25-run N16 group
covers RR1/RR10/Main/Algorithm-2/BLISS, five exploration seeds509-513 each;
it has54PASS steps and71 retained JUnit tests, zero fail/errors/skips/notrun.
Step accounting is25lint+25cocotb+3Python numeric-exit0 tools plus one derived
scope without process exit. Parent independently strict-inspected its source
and evidence archives, recomputed50 pooled-sparse histogram endpoints from
per-source populations, and checked exact seed traces, drain zero and bubbles
zero. Sources remain frozen core39/DAC53/power33/protected539.

Strict index and analysis exited0. Parent rehashed all19 release artifacts,
confirmed all460 prior performance records and the full18-capture/nine-pair
power block unchanged, and matched all10 non-FCFS N16 cohort summaries to
independent arithmetic. The independent Sol/high review found no findings:
25 identities,39 sources/archive,71 tests and3,825 histogram/conservation checks
passed. Parent adopted only these25 sealed jobs:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261027T0248/n16-25-adoption.json`.
Current accepted matrix is494PASS/4declaredRUNNING/0NOT_RUN of498, zeroFAIL
orUNRESOLVED. N expansion is56/60 accepted:30 N8 plus26 N16 including the
previous FCFS seed509 resource case once.

Writer release SHA256:
`28e93e36aaf78ff0ae2bc690c043905b9be1a0edb9790bb29547eb61cb0aaad2`.
Independent release SHA256:
`d0998809fbfd43fb335bc84af52b7c04f120db9cf96d25e254de34f04fc8deb4`.
SourceZIP SHA256:
`532e0815544e12a9bf09de1dd542a7e89506560728006839dab78fa41f82c6ad`.
EvidenceZIP SHA256:
`8764bc062fd9687ce757a00a99441c6f7f6406b5e6311f0b0c6b86f47a118c4c`.

Descriptive N16 Main meanrun-P99 A/B is10/34.8 cycles versus RR10 13/24.4.
Main improves A by3 but regresses B by10.4; every B seed regresses, and this
negative result remains explicit. Algorithm-2 A/B is10/35.2, RR1 3/23.4,
BLISS2/41.6. No CI on five exploratory seeds. Only the two Main/RR10 N16
comparisons are complete; no five-seed FCFS mean or complete FCFS pairing is
invented. N16 has15 sparse sources, expected sparse aggregate15/128 and256
localFIFOslots; it is not a fixed-load cross-N experiment.

At02:54:15 the final ordinal9 four FCFS/N16 cases are active, with zero
completed raw cocotb steps yet, three live simulators1234852/1234868/1234884
at99.9%CPU, no scope seal and zero failed recorded steps. Four declared rows
do not mean four concurrent workers. They are not promoted. Full60 report and
full498 closure remain gated on final seal, source/evidence checks and parent
independent adoption. Parent updated current ledger/confirmation/analysis;
no simulation was restarted, unchanged suite rerun, SSH used, or manuscript
modified for this adoption. Separate paper revision approval, final PDF QA and
independent post-revision Devil's Advocate/Methodology/Domain review remain
pending.


## Final498 experiment acceptance2026-10-27

All498 declared rows are sealed and accepted after independent review:
468 unconditional plus30 DAC insight rows; zero RUNNING/NOT_RUN/FAIL/UNRESOLVED.
The exact498 matrix IDs retain the prior494 rows,485 prior performance records,
and all18 power captures/nine complete pairs without change. N expansion60
counts the earlier FCFS/N16/seed509 resource case once. Final four FCFS/N16
runs pass12 steps/50 tests, zero failures/errors/skips. Core lane ordinals0-9
all exited0 and active is null. No simulation was restarted for this adoption.

Strict snapshot: power-index/final498-20261027/snapshot under ignored
revision-20261024 evidence. Writer release SHA256:
75399940a90fa0973552e78ee1c64341b47b6b0873fa96dc3e29ac4bfa113771.
Independent release SHA256:
d2f0b08e211a2b9822709641aa8499d2c3aa6918a516ac79f27a59b8600bf2cc.
Parent adoption: parent-continuation-20261027T0325/final498-adoption.json.
Parent separately rehashed15 release artifacts, re-inspected the final bundle,
recomputed all8 sparse P99 endpoints and checked drain/bubbles; an initial
diagnostic field-name mistake was corrected without modifying evidence.
Core39/DAC53/power33/protected539 files remain unchanged.

Full60 descriptive analysis/report is authorized from this exact accepted
index; narrative adoption remains pending. MANUSCRIPT_REVISION_PACKET.md
contains proposed F1-F16 edits only. The main.tex original body already uses
the correct Main-over-RR denominator; the reviewed v3 is a separate proposed
revision target, not an owner-selected replacement entry. No manuscript, PDF,
SSH or unchanged test suite was modified/run for this checkpoint. Separate
manuscript approval, final PDF QA and independent post-revision three-seat
review remain pending. Matrix PASS is not automatic closure of paper claims.


## Full60 N expansion report adoption2026-10-27

N_EXPANSION_RESULTS.md is independently reviewed and parent-accepted, SHA256
e64149b686c8b326f6baa4881108c2d9abff59ddc8e8c07bf74f03c383dc0e7c.
The frozen full60 analysis covers120 A/B endpoints,24 five-seed cohorts and8
same-N pairs; all78 input hashes and24 means/8 comparisons match the parent
independent raw-histogram/service checks. Writer release:
c6255e142c21750d2ed6c4c19ad3b561ff342116f38666772c260c984a5689e7.
Independent report release:
8e3c216b5092f5764f1a2837f9ee8ffc08adcc29992d94e81ce88059d8545f23.
Parent receipt: parent-continuation-20261027T0325/n60-report-adoption.json.

N16 FCFS mean run-P99 A/B is22/41.8, Main10/34.8 and RR10 13/24.4.
Main beats FCFS in each seed/arm but loses B to RR10 by10.4cycles; N8 B
regression is6.6cycles. Allfive B seeds regress at eachN. Exploration results
have no CI. Aggregate sparse demand7/128 versus15/128 and storage128 versus256
slots change withN; no isolated scaling causality, DAC N8/16 benefit or general
throughput improvement is inferred. All measured A/B eligible-ready opportunities
are served, while overloaded producer backlog remains distinct from localFIFO
occupancy and drains at experiment end.

This closes the planned N expansion experiment/report gap, not manuscript
revision, final evidence-manifest/PDF QA or independent post-revision paper
review. EXPERIMENT_COMPLETION.md records all498 accepted matrix rows and exact
receipts. No new simulation, SSH, source change or unchanged test-suite rerun
was needed for the analysis/report adoption.


## Revision packet ready for owner approval2026-10-27

The revision3 MANUSCRIPT_REVISION_PACKET.md is parent-reviewed after independent
delta review without findings. Packet SHA256:
aa95572ad11f1f8f64093baa50339c44599d0fcbd9d394123d90b1e8041b2081.
Independent release SHA256:
c51f9b566d5410e18b74751eec843a4beedba9601d725c1265777c31d1050f35.
The addendum supersedes historical494/56-of60 pending-N statements with the
adopted498/all60 results while preserving archived revision2 bytes. Proposed
main-v3 target remains conditional; main.tex historical body is preserved.
Parent readiness receipt: parent-continuation-20261027T0325/packet-readiness.json.
No manuscript revision authorization is inferred. Next owner decision is the
revision target and approval of concrete F1-F16 replacements; PDF QA and
independent three-seat post-revision review follow only after approved edits.
## 2026-10-27 approved manuscript revision started

The owner explicitly approved revising `docs/final-report/main-v3.tex` and its included
`sections/hotnets-body-v3.tex`, coupled generated presentation data, PDF QA and independent
Devil's Advocate/Methodology/Domain re-review. The revision3 packet's earlier approval-pending
language is superseded by that approval, while historical manuscripts, release receipts and
failed attempts remain preserved. Entry bytes and approval are archived under
`.setup-logs/implementation/revision-20261024/manuscript-revision-20261027/`.

The completed experiment matrix remains498/498 PASS; this manuscript task launches no new
simulation or remote EDA. Sol/high authors have disjoint scopes for the v3 body and new v3
numeric generator/manifest; the parent owns the driver, build, visual QA and integration.
Three reviewers are separated from manuscript authorship. This is a local advisory re-review,
not a journal decision, independent model-error guarantee or submission certification.
Historical native Claude contributions remain credited; no new Opus invocation is made.
The parent verified core39, DAC53 and power33 sources unchanged at revision entry; only
explicitly approved paper files may differ from the former539-file manuscript guard.
The first build and post-revision findings are pending and are not marked PASS here.


## 2026-10-27 v3 revision, final PDF QA and scoped re-review complete

The owner explicitly approved the v3 manuscript revision. This supersedes earlier
approval-pending/manuscript-pending notes without changing their historical receipts.
All498 experiment rows remain accepted PASS; no experiment, SSH, EDA or Opus was
launched for this revision. The historical main.tex/body and frozen core39/DAC53/power33
inputs remain preserved. Sol/high handled bounded author/data/reviewer tasks; the
parent integrated the driver, corrections, build and visual QA.

Round1 found one Major release-evidence gap and three Minor reporting issues:
missing exact bridge/replay/leaf-audit/screen bindings; N-expansion table locator;
DAC reset/mid-round credit contract; numerical disjoint-area presentation. The
repair binds588 existing records, adds the N4 category-area subset table and exact
state/locator wording, and separates performance-index scope from supplemental
proof/diagnostic records. No new experiments were requested or used to close these.
The historical initial findings and pre-repair freezes remain unchanged.

The parent independently repeated allfour final generator tests PASS, rehashed
all18 repaired-data release artifacts, compiled twice with exits0, and visually
inspected allnine rendered pages plus contact sheet. Final log: zero overfull or
undefined references/citations;29 underfull hboxes and the MiKTeX update-check notice
are retained. Final PDF output/pdf/cxl-scheduler-v3-revised-20261027.pdf SHA256:
892abcf3102c17bb75a5825ded5628368cf86a1c8397a727819136cb7a776400.

Devil's Advocate DA-R1, Methodology M-R1-01 and Domain W1/W2/U1/U2 are closed in
scoped round2 with no open scoped findings. Parent checked actual release/child
report hashes before adoption. See PAPER_REREVIEW.md and V3_REVISION_QA.md for
exact role releases, findings, F1-F16 dispositions, prioritized completed roadmap
and limits. Parent receipt: manuscript-revision-20261027/parent-round2-adoption.json
under .setup-logs/implementation/revision-20261024/.

Final reviewable bundle: output/pdf/cxl-scheduler-v3-release-20261027.zip; exact
archive/manifest hashes are recorded separately under the same manuscript scope's
final-release/archive-receipt.json. The bundle contains paper, presentation data,
review records and hash locators, not all raw experiments or proprietary inputs.
This is local uncalibrated advisory review, not external peer-review acceptance,
independent model-error assurance, physical signoff or full-system CXL validation.
No commit or publication was requested or performed.


## 2026-10-27 圖形版完成

使用同一 498/498 PASS 證據補入六張向量圖：確認集、配對 CI、敏感度、robustness／背壓、N 擴展、面積／功耗。最新 PDF `output/pdf/cxl-scheduler-v3-graphical-20261027.pdf`，12 頁，SHA256 `98ad620446224cb2eacf76abb5c7cb3761d7b21c0a6cfdd3971baf1ede3f6bcb`。六項資料／圖表測試與兩次編譯通過，零超欄及未解析引用；12 頁 contact sheet 與六個含圖頁完成視覺檢查。Sol/high 獨立複核的兩項 P3 排版問題已修復結案；無新實驗需求。Core39/DAC53/power33 全數未變，原 PDF/ZIP 保留。精確圖表數據、SVG/PDF/PNG、manifest 與 QA 見 `docs/final-report/generated/figures/`、`GRAPHICAL_EDITION_QA.md`。未重跑 simulation/SSH/EDA，也未 commit。


## 2026-10-27 FAI-inspired/CGOF measurement diagnosis

Implemented a separate MODEL_ONLY diagnosis harness without changing the
accepted 498-row experiment matrix. Public method names are CGOF
(Credit-Gated Oldest-First), with `CGOF (1:1)` and `CGOF (2:1)` settings;
the baseline is FAI-inspired. Immutable evidence keys containing old internal
identifiers remain unchanged.

`refc/cxl_model/diagnosis.py` adds the paired finite-Heavy scenario, WRR/IWRR
and eligible-RR controls, per-source latency histograms, demand-referenced
fairness, quota error, completion/span/throughput ratios, service gaps,
conservation and censoring checks. `scripts/run_diagnosis.py` freezes a
tamper-evident manifest before execution, requires a new output directory,
preserves failed jobs, forbids W256 inference, requires
`--production-reviewed` for W5M, and performs 10,000 paired seed/run
bootstraps only for a complete declared non-smoke cohort.

Tests: `270 passed` in `refc/tests`; the targeted diagnosis runner/model suite
also passed `18` tests before the full run. The final W256 smoke
`artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z`
passed 27/27 jobs with source stability, manifest digest
`5b25f6bca497165e497d58a8e667230081ae0b726c788dcd5240a0ee23304781`
and summary digest
`5a70ab871ae64d5481aa95697e288a5021eee248e9b746696fbc0fdf3a848627`.
All 18 smoke comparison records are NOT_RUN by design. `--verify-manifest`
returned PASS.

The first W256 smoke at `w256-smoke-20261027T171246Z` is retained as a
superseded checkpoint; later source changes make it stale. No W5M,
exploration, confirmation, RTL control, system or application experiment was
run. Scheduler fire is not memory bandwidth, and generation-to-fire is not
memory-response latency.

The report was regenerated from the same hash-pinned evidence. Six figures
were rebuilt; Figure 1's `FAI-inspired` tick label was wrapped after visual
inspection found overlap. Final PDF
`output/pdf/cxl-scheduler-v3-cgof-diagnosis-final-20261027T092103Z.pdf`
is 12 pages with SHA256
`E277786796638EE3F1DDCABF0CFE87BBF79AC67CDBB3EDC988614FF33C233FCD`.
Two compiles exited 0; no overfull, undefined-reference, or LaTeX/package warning
remained, and all 12 pages were inspected. Report tests passed 8/8. The 27
underfull horizontal-box notices and MiKTeX update notice remain environment/
typesetting diagnostics, not measured-result failures.

Evidence and limits: `docs/experiments/diagnosis-20261027/README.md`,
`docs/experiments/diagnosis-20261027/LITERATURE.md`,
`docs/MEASUREMENT_DIAGNOSIS_PLAN.md`, and `docs/final-report/CGOF_DIAGNOSIS_QA.md`.
No simulation, SSH, EDA, commit, or publication was performed for this
documentation/QA step.

## 2026-10-28 CGOF complete correctness and matched N4 synthesis/STA

The owner authorized the full correctness matrix followed by one matched N4
run. Codex rechecked the completed matrix
`artifacts/implementation/revision-cgof/20261027T222326Z_1164`: 152 steps
(145 PASS, seven expected rejections), 463 tests, zero failures/errors/skips,
model unit tests 17/17, `complete_matrix=true`, `stable=true`, both exits 0.
Source hashes and archive
`c202a407c50d3bbb0f7dd0daaf3d6618b623ce70ea065e95ca49ec5e8702353f`
were reverified. Earlier environment failures remain preserved.

After owner-authorized SSH authentication, Codex staged the previously
reviewed payload and ran DC/PT, reviewed reports, then ran the separate
Formality wrapper. No RTL, model or global service configuration changed.
Credentials were not written to project files. Payload SHA-256 is
`d1aee52ed4daa0d55c0c2f074e854819e617fa07fe0229f89d1ac284f5fcbeed`;
manifest SHA-256 is
`2c042f78b04acbb1245c8147643f27b8dd529f31fc06f96fae2a9060d444107e`.
All 62 preparation inputs remained unchanged. The original preparation
manifest is preserved rather than rewritten as an execution result.

CGOF (2:1), N4/D16/M1/W5M, uses the unchanged TT25ns cap075-v2 profile,
SAED32 RVT library and W-2024.09 tools. DC, PT and Formality exited 0.
Total cell area is 109794.784709; sequential cells are 9014. Worst reported
setup/hold slack is +10.398800/+0.038578 ns, with zero reported constraint
violations. All 68 untested checks are constant-disabled arcs, not user
timing exceptions. Formality returned `verify_return=1`: 9126 passing
points (112 outputs, 9014 registers), zero failing/aborted/unverified/
unmatched points, zero active blackboxes/post-match undriven nets, and no
user constants/exclusions. Twelve uniquify guidance rejections, 40
pre-match implementation undriven nets and library power-metadata warnings
are retained and disclosed alongside the successful full proof.

Raw results: `artifacts/fastx/cgof-ppa-dcpt-20261028T0723/` and
`artifacts/fastx/cgof-ppa-formal-20261028T0727/`. Remote commands/exits,
final source/handoff hash checks and safe report downloads are preserved
under `.setup-logs/FastX-NN/`. Parent JSON audits are in the raw
result directories. No proprietary library/license/executable was copied.

Public results and limits:
`docs/experiments/diagnosis-20261027/CGOF_RTL_PPA.md` and
`DIAGNOSIS_SUMMARY.md` in that directory. CGOF (1:1), N8/N16 synthesis,
workload power, APR and physical signoff were not run in this step.
`REAL_CXL/APPLICATION` remains `NOT_RUN`; synthesis/STA does not measure
completed memory bandwidth, CXL response latency or application slowdown.

A separate read-only Codex subagent (Hooke,
`01a17fad-a188-7833-9a8f-fd36b0b2ce85`, inherited model with actual runtime
model/effort unavailable) accepted pre-layout comparative area/STA with
caveats. Its independently expanded 29255 leaf cells sum to 109794.784711,
within 0.000002 of the report. All 9014 registers reconcile by function.
The clean archived FAI-inspired N4 comparator has cell area 110089.845892,
9011 registers, and setup/hold slack +10.496409/+0.039940 ns.
Profile JSON and applied-profile reports match byte-for-byte. The observed
CGOF cell-area delta is -295.061183 (-0.268019%), while setup slack decreases
0.097609 ns. Top-level glue differs by four AND2 gates (8.132608 area);
the full difference is not isolated policy overhead. Both report-cell
counts exceed leaf counts by 90; after 27 nonleaf occurrences, 63 remain
unresolved under that count interpretation. TIM-134 high-fanout estimation
and 68 untested timing checks prevent physical/timing-signoff claims.
The review did not exhaustively enumerate each displayed slack line or
each comparator disabled-check reason. These limitations are retained in
`independent-area-sta-review.json` beside the DC/PT raw results. No new
experiment or file edit was performed by the reviewer.

## Report improvement plan and experiment handoff - 2026-10-28

The owner requested an ARS-Codex report-improvement plan grounded in the local
literature and latest results, with unsupported explanations recorded separately
as testable hypotheses. Codex (GPT-6 parent session; no delegated model run)
created `docs/final-report/improvement-20261028/IMPROVEMENT_PLAN.md`,
`HYPOTHESES_AND_EXPERIMENTS.md`, and `agent-handoff.json`. The report README
links this handoff, and AGENTS.md directs subsequent writing agents to load it.

The plan follows pooling contention, FAI/Buffer, executable RTL, common
measurement, and results/implications. Local Pond, CXL introduction, FAI-CXL,
BLISS, STFM, Gupta/McKeown, and Mandal WRR texts informed the structure.
Existing N4 confirmation and power results are combined with the October 28
model diagnosis, single-seed production RTL, and six CGOF area/STA summaries.
Source hashes bind the evidence snapshot. Raw common-demand RTL traces confirm
the first closing classes are B_H/B_H/B_H/H: all remain effective High.
This distinction is retained when explaining equal results for the two weights.

The five proposed hypothesis groups cover Buffer adaptation, allocation versus
ordering, multi-window Heavy/Sparse replication, admission waiting, and eventual
system-level translation. Each has controls, metrics, contrary outcomes and
integration conditions; all new experiment tasks remain PLANNED. This task
does not change RTL, rerun simulations/EDA, or rewrite/compile the manuscript.

Planning-artifact validation checked the seven-policy confirmation table against
existing plot data, all 580 model job counts against raw summaries, all six CGOF
area/setup/hold values against downloaded reports, and both raw common-demand
classifier traces. The handoff hashes 52 source files; this is a local evidence
cross-check, not a fresh simulation or EDA run.


## Applied report improvement and acceptance — 2026-10-28

The owner authorized executing the report plan with GPT-6.1 Sol/high as primary author and figure agent, agy Gemini 3.8 Flash/high for language review, and Codex as orchestrator/acceptance reviewer. Parallel agents produced the manuscript, five evidence-bound vector figures and an independent raw-evidence audit. The exact identities and invocation receipts are in `docs/final-report/improvement-20261028/REVISION_QA.md`; ignored raw prompts/streams are under `.setup-logs/report-improvement-20261028/`.

The accepted main-v3 report has five sections in the prescribed sequence, seven figures, six tables and nineteen citations. It includes the twenty-seed N4 RTL confirmation, older sensitivity and qualified power, 580 completed diagnosis model jobs, separate single-seed production RTL, and six CGOF full-design area/STA mappings. Five new figures cover the pooled-memory path, Main Buffer transitions, source allocation, Heavy/Sparse tradeoff and CGOF hardware cost. Generated products bind 471 evidence inputs; numerical values are derived from raw phase counts, histograms and timing/area reports.

The independent audit corrected crucial interpretation boundaries: W5M configured is not a closed window in the short model runs; B_H remains effectively High; common-demand RTL producers throttle at 256 pending unaccepted requests; model overload and RTL near-load are separate populations; old CGOF behavioral confirmation is N4; and inter-service gap estimators differ across cohorts. Known fixed-horizon rate fields mixing drain numerators with active denominators were excluded and recorded for later repair. No model/RTL code was changed in this report task.

Gemini's complete isolated rewrite finished successfully (model `gemini-3.8-flash-high`, effort high, conversation `1ccd2d69-42d5-44b6-94b7-18ed29cba063`, exit 0, 722.66 s). Parent review accepted useful sentence-level edits and rejected changed KEEP/generation/refill/utilization/power semantics and stronger unsupported claims. The complete editorial rewrite was not adopted wholesale. Final text defines PPA and P99, explains the original FAI interpretations, motivates CXL without overstating differences from packet switching, and presents conditions as part of the measured argument.

Final checks: table/report tests10/10 (31.963 s), figure tests5/5 (13.937 s), two PDFLaTeX passes with exit0 and no overfull/undefined/LaTeX/package warnings, resolved nineteen citation keys and twenty-two labels, and visual review of all eleven rendered Letter pages. Zero extracted text boxes lie off-page. The initial native-command option error was repaired; no failed check was waived. Existing local `balance` supports reference-column layout; no dependency installation occurred.

Deliverables: `output/pdf/cxl-scheduler-revised-20261028.pdf`, editable `docs/final-report/main-v3.tex` plus its body, improvement figures, acceptance record and `revision-release.json`. Original planning files/hashes remain immutable because the generators depend on them; release metadata describes the applied version. H1–H5 retain PLANNED experiment status. No new simulation, synthesis, STA, power or system/application experiment was launched.

## Resource-limited finite-Heavy RTL confirmation - 2026-10-29

The owner authorized resuming the paused measurements. Codex checked the
completed aggregate at
`artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json`:
60 performance cohort endpoints and ten finite-Heavy exploration pairs are
already accepted. The current diagnosis runner's source hashes match the
completed seed-509 production scope exactly. Existing results are preserved.

The next batch is recorded in
`artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-20261029/manifest.json`
(SHA-256
`e050023c4790c3ad8556382406882d22d754200af589777395f0046b3c9158b7`).
It fixes held-out seeds 529-548, N4/D16/W5M, one window, 5,000,000 Heavy
requests, the near-load profile, both CGOF quota settings, and mixed/isolated
lanes: 80 planned simulations and 40 completion pairs. This is single-window
confirmation; it does not cover multi-window finite-Heavy stress.

The existing runner is invoked with `--production-reviewed --mode finite-heavy
--policy both --window 5000000 --windows 1 --heavy-work 5000000 --profile near
--jobs 2 --make-jobs 1` and each manifest seed. The batch inherits Linux
CPU affinity 14,15, nice 10 and best-effort I/O priority 7. Only one seed is
active at a time. A batch lock prevents duplicate invocation, source hashes
are checked before each seed, and each completed seed must have four passing
results, two pairs, stable sources and zero failures/errors/skips. Failures
stop the batch without automatic retry. A `STOP_AFTER_SEED` marker allows
the queue to stop between seeds. Completed evidence is never deleted.

The initial detached launcher exited before starting the batch; no experiment
result was produced by that attempt. The foreground persistent execution
started successfully (session 56938, Linux batch PID 267402). Its first
run is `20261028T202434Z_267411` (UTC run ID; October 29 locally).
Both lint configurations and all four traffic tests passed at startup. The two
isolated lanes and all top-level RTL checks passed. Both mixed lanes then failed
at the finite-Heavy cut with one Sparse request counted as generated but not as
completed (`124545` versus `124544`). The failure is deterministic across both
quota settings and preserves `generated = accepted = fired`; it is therefore a
diagnosis-cohort attribution defect, not evidence of an RTL request loss. The
cohort lookup uses the current `drain_started` phase even when classifying a
request by its generation cycle, so work generated on the final active edge can
be omitted from the finite-Heavy completed cohort. No automatic retry was
performed. The batch stopped with exit code 1 under
`confirmation-finite-heavy-20261029`, which contains the manifest, logs,
seven complete steps, two explicit mixed failure records, and no accepted
confirmation seed.

Bash syntax validation and the existing aggregation self-check passed. No RTL,
classifier, model, measurement collector or diagnosis source was changed; no
RTL implementation agent was invoked. The orchestrator's exact model/effort
fields are not exposed by this runtime. Repair and a fresh confirmation batch
require owner authorization after the failure.

The owner authorized repair and rerun. The diagnosis traffic now assigns a
request to the finite-Heavy cohort by its generation cycle, retaining the
closing active cycle after the Heavy cut and excluding only later drain
generations. A regression assertion covers that boundary. The targeted traffic
suite passed 4/4, and a new W256 RTL smoke run
`20261028T214920Z_2654` passed both quotas in mixed and isolated lanes (four
simulations, two pairs, stable sources).

The repaired production confirmation is a new, non-overwriting batch at
`artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029`
(manifest SHA-256
`2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407`;
diagnosis-traffic source SHA-256
`de773579475a0e3b15ed488045801d16a6b16849d9b38c9bdab4e2a3ffe29498`).
It keeps the same 20 held-out seeds and 80-run matrix, binds the prior failed
batch and smoke evidence, and uses the same two-core/low-priority resource
limit. Session 27469 completed seed 529 with all four lanes passing, two pairs,
stable sources and zero failures/errors/skips
(`20261028T215003Z_4833`); seed 530 is running. The previous failed batch
remains intact as negative evidence.

The repaired batch then completed all 20 held-out seeds (529-548): 80 RTL
results, 40 mixed/isolated pairs, one stable source variant, conservation and
Heavy completion checked, and every scope PASS. The final 12 simulations ran
as six seeds with two workers each under the owner-approved higher-resource
limit. The batch wrapper exited 1 only after simulation completion because the
aggregator correctly refused to combine the repaired confirmation source with
the older exploration source in one aggregate. No RTL job failed and no
experiment was rerun.

The aggregator now permits either a complete exploration stage or a complete
confirmation stage, while still rejecting partial seed sets and unexpected
seeds. Its self-check covers both stage-only cases. The new non-overwriting
confirmation aggregate is
`artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/aggregate.json`
with SHA-256
`0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d`.
It uses 10,000 paired bootstrap resamples. CGOF (1:1) and CGOF (2:1) both
complete Heavy work (mixed/isolated active-cycle ratios `1.000000488` and
`1.000000480`), with Sparse P99 `3` and `4` cycles and maximum Heavy gaps
`9.45` and `10.85` cycles respectively. Sparse-only Jain is `0.999993735`
for both settings; raw Jain remains dominated by the intentional Heavy share.

`DIAGNOSIS_SUMMARY.md` records the held-out result and keeps it explicitly
single-window. Multi-window finite-Heavy stress, backpressure, role switching,
real completed memory bandwidth, CXL response latency, application slowdown,
calibrated system validation and physical signoff remain NOT_RUN.

## 2026-10-29 — latest-result manuscript, figures and theory acceptance

The owner requested the latest completed experiments to be incorporated into report figures, data and theory. Codex coordinated three parallel GPT-6.1 Sol/high agents: author `01a18625-2ccc-7561-a331-7d1e694ba514`, figure/data `01a18625-2915-7f12-a7d3-e09d307be97a`, and independent evidence reviewer `01a18625-2637-7070-98e9-c4805ad5c8e9`. agy `gemini-3.8-flash-high` with high effort reviewed changed prose (exit 0, 290.34 s); the parent selectively accepted edits and corrected the replay attribution. Roles, model receipts and editorial dispositions are in `docs/final-report/update-20261029/REVISION_QA.md` and local `.setup-logs/report-update-20261029/`.

The repaired finite-Heavy confirmation aggregate `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d` and current-source performance aggregate `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097` supply the update. The new versioned generator recomputes raw metrics and saved bootstrap intervals from 241 bound inputs: 80 finite jobs/40 pairs across 20 seeds and 30 replay runs/60 endpoints. Its five tests pass, including missing/duplicate input rejection and histogram mismatches. Final regeneration records the documentation-only AGENTS change; executable evidence sources remain consistent. The old generator pins and 19 historical generated products remain unchanged.

Two new SVG/PDF/PNG figures show paired finite-work seed values and readiness confirmation/exploration, with corresponding generated tables. In near-load RTL, 1:1/2:1 yields Sparse run-P99 3/4, mean run-maximum Heavy gap 9.45/10.85, and mean mixed-minus-isolated completion 3.05/3.00 cycles. Every job crosses one W5M boundary and remains effective High. The manuscript therefore distinguishes absolute credit budgets from normalized entitlements, and the near-load quota comparison from the older overload Main-to-CGOF result. The current CGOF-only replay reproduces 1.10/12.35 on the same A/B seeds; it does not create new Main samples. Readiness exploration compares nominal, not exactly realized, 75% availability.

Independent review also distinguished generation-cohort latency from active-count fairness, excluded the failed unrepaired batch, documented the completed-scope evidence despite stale launcher status, and corrected three public-summary transcription/interpretation errors (B_H effective class, fixed-class share rounding, Sparse Jain). The model candidate screen and its non-improving age-rescue settings remain exploratory context in the audit. `THEORY_AND_EVIDENCE.md`, `hypothesis-status.json` and `FOLLOWUP_EXPERIMENTS.md` provide supported statements and falsifiable refill/phase/capacity experiments. H3 advances to partial multi-seed single-boundary support; broader adaptation and system effects remain unrun.

The final PDF is `output/pdf/cxl-scheduler-revised-20261029.pdf`, 13 pages, 9 figures, 7 tables and 19 references, SHA-256 `3cf656cedf4a245b8f48c3198cb3106636ae6bb116c1323d2cd46156e2e07782`. Two final PDFLaTeX passes exited 0; all 13 rendered pages and new figures were visually checked. One harmless 1.7849 pt page-balancing vertical-box diagnostic is explicitly recorded; no clipping, overlapping content or unresolved references remains. The new source/release navigation supersedes dated checkpoints without rewriting their history. This report task launched no simulation or EDA work. Final output/source hashes and read order are in `docs/final-report/update-20261029/revision-release.json`.

## Dynamic finite-Heavy screen and production probe - 2026-10-30

The owner authorized the remaining dynamic scope: multi-window finite-Heavy,
physical role switching, a minimal ready-backpressure comparison, and D8/D32
depth sensitivity. No scheduler RTL was changed. The existing diagnosis model,
traffic collector, runner and analyzer were extended to preserve
generation-time roles through classifier changes and drain.

The frozen model screen completed all 90 mixed/isolated pairs at W256, four
nominal windows, Heavy work `3.5W`, exploration seeds `6101-6105`, and both
CGOF quota settings. Every case crossed four active classifier boundaries.
Mean Sparse generation-to-fire P99 for FAI-inspired / CGOF (1:1) /
CGOF (2:1) was `12.6/4.0/4.2` cycles for multi-window, `14.8/5.4/6.6` for
role switching, `11.8/2.6/3.2` for spread readiness, and `18.0/11.2/11.0`
for bursty readiness. Mean maximum Heavy gaps were `6.2/4.2/5.2`,
`6.6/4.2/5.6`, `5.2/3.6/4.0`, and `11.6/11.2/11.4` cycles respectively.
These are exploratory model results, not production or held-out confirmation.

The D8/D32 rule required at least a one-cycle Sparse-P99 or maximum-Heavy-gap
change in three of five paired seeds. Neither depth met that primary rule.
D8 nevertheless moved Heavy admission wait outside the FIFO while leaving
total generation-to-fire latency unchanged, so one D8 production case was
selected to validate the measurement boundary. D32 was not selected for RTL.

The non-overwriting production batch is
`artifacts/implementation/cgof-dynamic-20261030` (manifest SHA-256
`527a9206c16e0198f6ae6067f37b6652d72009eb956acfbdffa9cb85a529a03a`).
It uses one fresh seed `7291`, N4/W5M, four nominal windows, `17.5M` finite
Heavy requests, near load, and five cases: multi-window, role switch, spread,
bursty and D8 bursty. Each case has both quota settings and paired
mixed/isolated lanes, for 20 simulations and 10 pairs. A W256 RTL smoke
matched a separate model execution exactly for active horizon and
generation-role counts, bursts, latency histograms, gaps and fairness.

The batch completed with status `PASS` and exit code 0 under the authorized
ten-simulation limit, with affinity restricted to the host's 16 logical
processors, low CPU and I/O priority, and no automatic retry. All ten lint
gates, all five traffic-test suites, 20 RTL results and 10 mixed/isolated
pairs passed. Every result crossed four actual active W5M classifier
boundaries and completed all `17.5M` Heavy requests. Generation-role and
physical-source conservation passed, with no Sparse generation-cohort
requests censored at active cutoff.

The five case/run bindings are:

| Case | Run under `artifacts/implementation/cgof-rtl-diagnosis/` |
| --- | --- |
| Multi-window | `20261029T182230Z_52851` |
| Role switch | `20261029T182230Z_52853` |
| Ready spread | `20261029T182230Z_52850` |
| Ready bursty | `20261029T182230Z_52849` |
| D8 bursty | `20261029T182230Z_52852` |

The final aggregate is
`artifacts/implementation/cgof-dynamic-20261030/aggregate.json`, SHA-256
`e8a398b18348a99a3a20fc89e1d0086b5c75b31db093b9e1e9ebecbd76d649e8`.
Codex independently reconstructed all ten rows from the five scopes using
`scripts/analyze_cgof_dynamic.py:validate_run`, exactly matching the saved
rows and all 30 result/scope/summary bindings. Archived and current
executable source hashes match one stable variant. The analyzer digest and
all three protected-document hashes match the frozen manifest. The W256
screen and depth-observability receipts retain SHA-256
`b89a5b0b6543840b83916550590e446e5cf03a0a5335c3d5f26d7ff6b364b2e3`
and `38d97ce240618b21b485149c1f30068ea4c99e21b1705331d273cfb43f1bfb33`.
The independent W256 smoke receipt is
`artifacts/implementation/cgof-dynamic-20261030/smoke-independent-check.json`.
No scheduler RTL or historical release snapshot changed during acceptance.

Production observations follow; gaps are P99 / maximum, in the named clock
boundary. Completion ratio is mixed/isolated active cycles.

| Case | Policy | Sparse generation-to-fire P99 | Heavy wall gap P99 / max | Heavy ready-opportunity gap P99 / max | Completion ratio |
| --- | --- | ---: | ---: | ---: | ---: |
| Multi-window, D16 | CGOF (1:1) | 3 | 3 / 10 | 2 / 4 | 1.0000002286 |
| Multi-window, D16 | CGOF (2:1) | 4 | 3 / 11 | 2 / 7 | 1.0000002286 |
| Role switch, D16 | CGOF (1:1) | 3 | 3 / 9 | 2 / 4 | 1.0000002743 |
| Role switch, D16 | CGOF (2:1) | 4 | 3 / 11 | 2 / 7 | 1.0000002743 |
| Ready spread, D16 | CGOF (1:1) | 3 | 3 / 5 | 2 / 4 | 1.0000001828 |
| Ready spread, D16 | CGOF (2:1) | 3 | 3 / 8 | 2 / 7 | 1.0000001828 |
| Ready bursty, D16 | CGOF (1:1) | 11 | 11 / 14 | 2 / 4 | 1.0000002286 |
| Ready bursty, D16 | CGOF (2:1) | 11 | 11 / 17 | 2 / 7 | 1.0000002286 |
| Ready bursty, D8 | CGOF (1:1) | 11 | 11 / 14 | 2 / 4 | 1.0000002286 |
| Ready bursty, D8 | CGOF (2:1) | 11 | 11 / 17 | 2 / 7 | 1.0000002286 |

Mixed completion takes four extra cycles for spread readiness, five for
multi-window/bursty/D8 and six for role switching. These observed differences
have no predeclared equivalence margin. Equal nominal 90% readiness is
realized as `0.8999999863` for spread and `0.9000001143` for bursty. The
bursty trace raises Sparse P99 and Heavy wall-gap P99 from 3 to 11 cycles,
while Heavy ready-opportunity gap P99 stays 2. This isolates a diagnostic
distinction between stall arrangement and available service opportunities.

All static-role cases show one effective source-class change:
`[B_H,H,H,H] -> [L,H,H,H]`, then retain that map. The physical Heavy
schedule `[0,0,1,1]` instead gives
`[B_H,H,H,H] -> [L,H,H,H] -> [B_L,B_H,H,H] -> [H,L,H,H]`,
three effective source-class changes across the four actual boundaries.
The generation-time role collector preserves old Heavy and Sparse cohorts
after the physical source changes roles; Buffer states retain the prior
effective class.

All mixed rows have demand-share L1 zero and Sparse demand-normalized Jain 1.
Static-role Sparse raw Jain is approximately `0.999997`; role-switch Sparse
raw Jain is `0.898643` and all-source raw Jain is `0.545057`. Role exposure
times differ, so raw shares alone are not a fairness verdict. These
active-count measures have all Sparse work completed at cutoff and do not
establish transient quota compliance.

Sparse generation-to-acceptance P99 is zero throughout; its
acceptance-to-fire P99 equals the total values above. Under bursty readiness,
both quota settings have Heavy generation-to-acceptance /
acceptance-to-fire / generation-to-fire P99 of `2/18/20` at D16 and
`11/16/20` at D8. Sparse total P99 stays 11. Component percentiles are not
additive. The D8 result confirms that smaller FIFOs can move waiting before
admission without changing total waiting in this trace; the negative D32
screen is retained, with no D32 production claim.

Final local acceptance used the existing WSL environment:
`PYTHONPATH=. python3 -B scripts/analyze_cgof_dynamic.py --self-check
artifacts/implementation/cgof-rtl-diagnosis/20261029T181127Z_23048`
passed. The targeted command
`PYTHONPATH=. python3 -B -m pytest -q refc/tests/test_diagnosis.py
sim/experimental/test_cgof_diagnosis_traffic.py scripts/test_run_diagnosis.py
scripts/test_run_rtl_diagnosis.py scripts/test_analyze_rtl_diagnosis.py`
passed 40 tests and 18 subtests in 3.01 seconds. The scheduled task is Ready
and no CGOF simulation process remains active.

ARS-Codex experiment validation informed the acceptance. The eleven
interpretation-fallacy checks were reviewed: cases, roles and quota settings
remain separate; requests are not independent seed replicates; completed and
censored work is accounted for; the D8 diagnostic selection and negative D32
screen are disclosed; and no general causal, equivalence, significance or
system-performance claim is inferred. The saved aggregate has
`confidence_intervals: null` because this is one fresh seed. The dynamic RTL
batch contains CGOF only; FAI-inspired comparisons remain exploratory W256
model evidence. This advances the multi-window and admission-boundary
diagnosis, not the older held-out single-window sample size.

`DIAGNOSIS_SUMMARY.md` now records `SCHEDULER_RTL PASS (single-seed)`.
Multi-seed dynamic confirmation, a broad backpressure/load sweep, D32 RTL,
real CXL completed bandwidth, response latency, application slowdown,
calibrated system validation and APR/signoff remain `NOT_RUN`.

## 2026-11-01：證據審查後的 Buffer transition screening

在既有 P0–P4 實驗契約／觀測器修正後，依 owner「繼續推進」建立
獨立 MODEL_ONLY Buffer screening。原計畫與歷史結果不改寫。實際委派
`gpt-6-astra`、reasoning=`high`（agent
`01a1944e-433b-7da2-9347-7625fcb50ccf`）撰寫驗收計畫並獨立複審；
`auto/deepseek-v4.1-flash`（agent
`01a1944e-c43f-7d52-b32d-9ead1539a500`）實作測試。監督者完成 runner、
修正測試 oracle、執行驗收與封存。上述為請求參數；工具沒有回傳 effective
model，manifest 明確記 UNKNOWN，不宣稱已驗證 routing 後端。

實際新增／修改：`scripts/run_buffer_transition_screen.py`、
`scripts/test_run_buffer_transition_screen.py`、
`docs/reviews/buffer-transition-acceptance-20261101.md` 及
`docs/reviews/evidence-review-followup-20261101.md`。重用既有 threshold、
Main／Main-1W／Algorithm-2 tables/maps，沒有修改 shared model、RTL、
accepted spec、主論文或歷史 artifacts。新 schema
`cxl-buffer-transition-screen-v2` 取代本次未驗收的 evidence-only draft，
不會將其結果與舊 schema 合併。

每 W 有 24 組共同外生 B/S 輸入（phase0/W4/W-1、兩方向、noise
W/2/W/3W/2 或 persistent>=4W），另加 DOWN→KEEP／S0 兩組控制；
三 variants 共 78 replay。W256／W64 各 78 replay 與 input pairing
PASS，20 COMPLETE、58 INCOMPLETE。INCOMPLETE 是角色區間內 target
stable suffix 觀測不足 W 或未達，不代表 runner failure。固定 slots
沒有隨機 seed replicates，不能作統計確認。

修掉 draft 的假尾窗及首次 stable hit 誤作 settle：實際終點只用
`T=len(counts)*W`，close 與下一 cycle visible 分開；角色 event 用半開
區間，不能借下一角色的觀測時間；visible=T 明列零觀測，也不抹除終點
以前實測 stable suffix。Alg2 target-effective 與 stable-state 分開。
原始 counts、每個 close 的四來源轉移、slot 排序與 hash 均可核對。

實際驗證環境 WSL project venv，Python3.12.3／pytest9.1.1：
`python -B -m pytest -q scripts/test_run_buffer_transition_screen.py
refc/tests/test_fai_main_model.py refc/tests/test_fai_alg2_model.py
sim/experimental/test_baseline_models.py`，結果 **180 passed、
115 subtests passed in18.51s**，exit0。初次整合有8個失敗（含
subtests）：補 metadata validation，修正兩處測試錯誤期待及邊界回歸後
全過；一次探索命令指定不存在的 baseline test path，no tests ran，
已改成上述真實路徑，未將失敗列 PASS。Astra 最終獨立五個定向 probes
通過，無剩餘 finding。

W256 persistent 的 Main source0 effective delay 為448–704cycles，
1W／Alg2為192–448cycles；Alg2 stable delay與Main一致。這些是
synthetic service-role classifier timing，不是需求到達或 queueing
latency recovery。phase0、長 W 的 down/up-return noise 中 source0
effective flips 為Main0、1W2、Alg2為2，不能據此宣稱延遲收益。

原始證據、來源 snapshot、重跑命令、實際 provenance 與 source/current
hash 核對：
`artifacts/implementation/buffer-transition-screen/20261031T234344Z/manifest.json`，
raw SHA256
`66bb7863873e584ddca31b9c2882c46a30b041c1a6759fe3e359f4399e86441d`。
本地過程與失敗 logs 在
`.setup-logs/implementation/buffer-transition-20261031T233258Z/`；
持久摘要與完整表在
`docs/reviews/evidence-review-followup-20261101.md`。

仍為 NOT_RUN：closed-loop CGOF2 live／1W／frozen 及CGOF1負控制、
新 Buffer RTL、W5M production／20-seed confirmation、新 EDA/PPA、
CXL/application。先前較廣 Python 回歸的14個 power-vector errors
仍保留為既有未解問題，本輪沒有重跑或宣稱全域綠燈。未 commit。

## 2026-11-01：Buffer closed-loop MODEL_ONLY screening

接續 transition-only screening，按 owner「繼續推進」完成獨立
closed-loop runner/test。指定 GPT6Astra(high) 的 spawn 回傳
`Unknown model`；本輪規劃／唯讀複審改用 owner-approved
`group/gpt-6.1-sol`、high，agent
`01a1949c-5d71-70d1-b0d9-cd5aa5829868`，計畫為
`docs/reviews/buffer-closed-loop-plan-20261101.md`。
`auto/deepseek-v4.1-flash`、agent
`01a1949e-95ff-7a72-84c6-5778ad14fdb8` 交付測試；監督者完成
runner、整合／補強測試、實際執行及 evidence acceptance。所有
backend effective model 均因工具未回傳欄位而記 `UNKNOWN`，
不把 fallback routing 冒充 Astra 或後端驗證。

本輪程式範圍：新增 `scripts/run_buffer_closed_loop.py` 與
`scripts/test_run_buffer_closed_loop.py`，在 experimental model
新增 optional classifier（預設 live），沿用既有 Main／Main-1W
tables 及 common FIFO/hold/credit/oldest-first 路徑。frozen 從
reset 到 drain 每 cycle 都驗 all H。既有 default callers 的
differential tests 仍通過。沒有修改 frozen spec、RTL、主論文、
歷史 manifest 或 transition runner。

固定 N4/D16/W256、over（熱來源 p1、其他各 p.05、ready p.9）；
3W baseline，phase0/64/255，noise duration128/256/384 與
persistent4W；return tail4W；所有 variants 在共同 H 停止生成。
down/up 分別是 R0→R3／R3→R0，觀察新熱來源 Low target；
不把 up 字面當 High target。Drain 沿用同一 ready，最多4W，
未完成保留 right-censor。角色 ID 在 generation 固定，跨角色與
drain 完成仍計原 cohort。每 role/source 的 G→A/A→F/G→F
採 nearest-rank，no-demand／未完成不填零。FIFO/backlog
histograms 與 wall/ready gaps 分開；重用 followup.Gaps 與
diagnosis.jsonable，未重寫 selector。

本輪新 schema `cxl-buffer-closed-loop-screen-v1`，manifest
`cxl-buffer-closed-loop-manifest-v1`。W64/W256 self-check各12
variants、W256 seed6101 smoke144 variants 全過；其後
6101–6105 exploration 共120共同情境、720 variants，status
PASS。Smoke 的6101重用於 exploration，不增加獨立 seed 數。
120/120 組 inputs pairing 與 CGOF1 三 modes 的 action、
counts、cohort latency、gaps、FIFO/backlog 完全一致負控制
PASS；CGOF2 在120組皆有 descriptive action 差異，不作
ranking、CI、p-value 或一般優勢宣稱。

Exploration 的 measured events 為480 COMPLETE／780
INCOMPLETE；INCOMPLETE 分為live未達Low180、1W未達Low80／
post-settle不足W100、frozen固定High420。這是觀測狀態而非
execution failure。跨 variants generated=fired=1,735,614，
final censored=0，最大 drain726cycles（上限1024）；共同
inputs 內實際生成289,269 events，六次重播不是獨立樣本。
刻意全ready0測試則保留未完成 population與null GF，正確標記
`RIGHT_CENSORED_AT_DRAIN_BUDGET`。

CGOF2 persistent 每mode30events：live/1W各30COMPLETE，
hot-source stable delay448–513／192–257cycles；frozen不達Low。
seed6101/phase0/R0→R3的R3 cohort，live/1W/frozen之hot GF P99
皆529、sparse GF P99為657/574/496。這只是該fixture分布，
不能據此推論 frozen 的適應收益或一般 mode 排序。
`latency_recovery=NOT_DEFINED_THIS_ROUND` 全程保留；
class settle 沒有升格為 latency recovery。

最終實際命令（先 source scripts/wsl_env.sh）：
`python -B -m pytest -q scripts/test_run_buffer_closed_loop.py
refc/tests/test_experimental.py refc/tests/test_diagnosis.py
scripts/test_run_buffer_transition_screen.py refc/tests/test_fai_main_model.py
refc/tests/test_fai_alg2_model.py sim/experimental/test_baseline_models.py`，
WSL Python3.12.3／pytest9.1.1，**245 passed、224 subtests
passed in23.73s**，exit0。單獨 closed-loop＋experimental／
diagnosis 為65passed、109subtests。新增完整1W table、frozen、
跨角色、drain、空cohort、terminal/suffix、input/source mismatch、
CGOF1 leakage、exclusive-output反例。

DeepSeek交接時runner未完成，測試有3failures/5errors；
整合01先遇 followup 的 traffic_trace import path缺失，
整合02遇 weak recursive test與integer histogram keys的
JSON round-trip hash差異，均修正並保留原logs。原對話
read_thread tool讀取失敗，沿用已保存的本地計畫與證據紀錄，
沒有據此新增未取得來源的claim。

新證據目錄：
`artifacts/implementation/buffer-closed-loop/20261101T015630Z/`。
包含source snapshots、Git HEAD/dirty diff、Python/pytest版本、
每命令argv/exit/status/stdout/stderr、完整raw輸出與hash、
before-after source stability。Manifest raw SHA256：
`d95bcdd4a38adddaa44a53be39fad3fc8d21007d63d0251d98d7c84bfd3a984a`；
exploration raw SHA256：
`f9a769b87e77334c9e4b5e03e5f7e16d2d07807460153392bd9b5e60095f53b4`。
完整配置／event計數／限制／重跑命令見
`docs/reviews/evidence-review-followup-20261101.md`。原transition
manifest仍為66bb7863…86441d，計畫仍為3b9cf636…04860fe；
October29 manuscript driver/body仍符合原release記錄。
Sol/high另做W64邊界／drain／cohort／CGOF1／persistent probes；
新熱來源target與獨立manifest的兩項初始疑慮經核對後撤回，
reviewed scope無剩餘material finding。Reviewer未重跑W256矩陣；
監督者另驗raw/canonical hash、全部control metrics與source snapshots，
驗收及裁定存於同目錄`acceptance.json`。

仍未執行：W5M production／20-seed confirmation、新Buffer RTL／
formal／CDC／PPA／EDA、latency recovery threshold、CXL response
或application量測。先前較廣回歸的14個power-vector errors
未在本輪修復或重跑；本輪PASS不表示全域回歸全綠。未commit。

## 2026-11-01：H2 quota × ordering RTL 修正版五個 seed exploration

依owner「繼續推進」延續既有H2 ordering問題，未修改RTL/model。
Planner/reviewer指定GPT6Astra(high)回報`Unknown model`，
使用已核准`group/gpt-6.1-sol` high fallback，agent
`01a194fd-9121-76b3-842c-50384ba7dd6a`。Executor為
`auto/deepseek-v4.1-flash`，agent
`01a19500-b3d5-79c3-a045-d0879c4683a0`；監督者建立獨立輸入
重播、來源／JUnit／raw-result核對及campaign analysis。
Backend effective model皆為`UNKNOWN`；未宣稱成功啟動Astra。
Git HEAD仍為`99400ded42cc63c3b206bd5d13f51d36344b2689`、
branch `experiment/main-sq`，原dirty worktree完整保留，未commit。

先凍結`docs/reviews/ordering-rtl-exploration-plan-20261101.md`，
Heavy work1024、fresh seeds6301–6305。第一個6301 run
`20261101T024757Z_2732`執行13/13steps PASS，但close255為B_H、
close511轉L，固定effective High control不成立。已停止6302–6305；
不分析該run的quota/ordering endpoints，不刪除失敗設計。
原summary SHA256
`4e87dd9ed18794d160df26fe7e7076b9d638a799f3b6a5562a165b0b3d933b1d`
與scope SHA256
`c386ad2fa3e0e62a734b7a03392728f9a99bef5cf8ee25fbce703467ba4d46a0`
在最終audit仍相同。

其後另凍結correction plan
`docs/reviews/ordering-rtl-exploration-correction-20261101.md`
（SHA256 `955ac86ae7cc6785f298ceaf58a78027eedf8e89034e9476969ffaeabc18a7d6`），
改為Heavy work256及fresh seeds6401–6405；其餘固定N4/D16/W256、
near（Heavy p.8、Sparse各p.02）、bursty ready p.9/period100、
source0、Q1/Q2 × oldest-first/eligible-RR × mixed/isolated。
每seed後先驗control再執行下一seed，不依結果增刪seed或設定。

修正版run IDs依序為`20261101T025305Z_3219`、
`20261101T025436Z_7803`、`20261101T025606Z_12313`、
`20261101T025739Z_16918`、`20261101T025918Z_21788`。
五seed全為13/13steps PASS：共20lint configurations、25traffic tests、
40cocotb jobs、20mixed/isolated pairs。每lane Heavy256/256，
active326–336cycles，只有active/window0/close255，old/new
states僅H/B_H；manipulation HELD。31sources在五run的
before/after、ZIP及audit-time現檔一致。

WSL使用既有Python3.12.3／pytest9.1.1／cocotb2.1.0／
Verilator5.052。前置targeted回歸82passed／40subtests（7.33s）；
correction前35passed／6subtests（0.99s），包含
`scripts/test_run_rtl_diagnosis.py`、
`sim/experimental/test_cgof_diagnosis_traffic.py`、
`refc/tests/test_diagnosis.py`。重複traffic tests不是額外獨特RTL
coverage；先前14個power-vector errors不屬於本輪PASS。

實際WSL seed command以下列參數依序替換6401–6405：

```bash
source scripts/wsl_env.sh
export PYTHONPATH="$PWD/scripts:$PWD"
timeout --foreground 1800 \
  python -B -c 'import sys, run_rtl_diagnosis as r; r.NAME="cgof-rtl-ordering-exploration"; raise SystemExit(r.main(sys.argv[1:]))' \
  --smoke --window 256 --mode finite-heavy --policy both --ordering both \
  --seed 6401 --windows 1 --depth 16 --profile near --heavy-work 256 \
  --ready-pattern bursty --ready-period 100 --jobs 1 --make-jobs 1
```

Supervisor audit另驗40raw JSON、45JUnit files與全部source ZIP。
從serialized trace_config重建scenario，完整active input的hash與
每份trace_sha256相同；20mixed/isolated共同Heavy+ready prefix
及40setting-contrast共同prefix均配對。Prefix欄明示reconstructed
declared input，未聲稱有分離的observed Heavy-prefix artifact。
Nearest-rank P99另從histogram重算；Heavy max與pooled gap path
交叉核對；40個setting contrasts與20個pair-ratio contrasts保存
reference/candidate/delta，不計score/rank/CI/p-value。

全部generated=accepted=fired=10,672，final censored=0。
五個Sparse request在active cut尚未完成，皆於1-cycle drain完成：
6402 Q2-OF與6404四個mixed設定。Latency採full-run generation
cohort，包含drain，與active-cut pending/final censor分欄。
Gap只計active backlog episodes，initial/inter-service/
empty-terminated/censored保留原分類。Active-cycle ratio
1.003030303–1.015337423不是byte或bandwidth ratio。
Drain沿用既有RTL harness的ready=1，未外推為持續bursty drain。
各seed的mixed Sparse完成樣本數23/22/18/28/17，因此本輪
nearest-rank Sparse P99等於各run的樣本最大值，尾部推論受限。

本輪Q1兩種ordering四端點在五seed皆相同；Q2-OF→Q2-RR的
Sparse P99 delta依seed為0/-1/-1/-1/-1cycles，Heavy max gap
delta為0/+1/-1/0/-1cycles。Ready/wall P99及完整原值另見analysis。
這是五seed bounded方向觀測，不能宣稱一般quota/ordering優勝、
equivalence、confirmation或application benefit。

外層有原6301 quoting failure與corrected6401 function-wrapper
`--seed`空值failure，均在runner建立run前停止。改為明確參數後
五seed依序成功；沒有重跑已有結果或改選seed。另有兩次只讀
診斷命令失敗（PowerShell pipeline parser、未source環境找不到
python），保留transcript records。沒有單一campaign shell process，
因此只記各command實際exit，不創造aggregate OS exit code。
原始command/stdout-stderr/exit/start-end從executor transcript的
CommandExecution records選出封存，沒有複製私人推理或整個session。

新campaign manifest：
`artifacts/implementation/cgof-rtl-ordering-exploration/correction-manifest-20261101T030414Z.json`，
raw SHA256 `4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b`。
同namespace的analysis SHA256為
`76da0716572feea212b57a39cd8b382aabc7eb9f46205cc694ff44aff07a5fe8`，
pair-audit SHA256為
`c5fe80a1cdb5d7a13dcad4b3213da23be672f70e8093621c6e99828161a0dc76`。
`correction-command-records-20261101T030735Z.json`保存外層執行證據；
audit source、self-check、stdout與82-test log亦封存。
詳細表格見`docs/reviews/evidence-review-followup-20261101.md`。

Sol/high final只讀複審另重播40個trace hashes，核對20pairs、
40setting contrasts、20pair-ratio contrasts與180份run files，
未發現阻擋bounded驗收的material finding。初審六項標籤／identity／
cohort邊界問題皆在audit處理；沒有以統計推論升格本輪scope。
新`correction-acceptance-20261101T030414Z.json`封存review裁定、
補充command records與開發文件變更hash，原manifest不覆寫。

本輪為SCHEDULER_RTL scheduler-boundary evidence。Runner的
`summary.scope="full"`只指指定steps完整執行，不能升格為W5M/
production/confirmation；scope另有`smoke=true`。未改RTL、
model、frozen spec、主論文或歷史artifacts。未跑本ordering
follow-up的confirmation、W5M、formal/CDC/PPA/EDA、新Buffer
RTL、latency-recovery threshold、CXL/application量測；既有
October29 confirmation保留其原範圍。

## 2026-11-01：Astra CLI計畫與H2 ordering二十seed確認完成

Owner指定Astra透過Codex CLI呼叫，本輪成功使用
`codex exec --json -m codex/gpt-6-astra`及invocation-local
`model_reasoning_effort="high"`完成凍結計畫
`docs/reviews/ordering-rtl-confirmation-plan-20261101.md`。
Plan SHA256：
`e68ab2ef3506029e2b719d6d80eadec3dcf6277debe1b13a5a674309f28c93ec`。
先前agent-spawn `Unknown model`未當作CLI失敗；本輪無planner
fallback。Requested model與實際backend分開，effective model
維持`UNKNOWN`。CLI JSONL/final output另封存。

Codex擔任監督，`auto/deepseek-v4.1-flash` agent
`01a19500-b3d5-79c3-a045-d0879c4683a0`逐一執行fresh seeds
6501–6520；executor backend同為`UNKNOWN`。沿用現有RTL、
runner與collector，未改spec/model/RTL。固定N4/D16/W256、
finite-heavy near、Heavy256/source0、Heavy p=.8、各Sparse p=.02、
active ready bursty .9/period100、Q1/Q2 × OF/eligible-RR ×
mixed/isolated，`--jobs 1 --make-jobs 1`。不混入6401–6405探索
結果，不替換或重跑seed，也不根據結果改計畫。

Preflight35passed／6subtests，exit0。Campaign於
2026-11-01T04:06:10Z開始、04:42:16Z最後seed完成，
runner wall-time合計1784.936s。實際WSL invocation是凍結計畫
seed-wrapper，以下節錄其runner呼叫，seed依6501–6520順序替換：

```python
import run_rtl_diagnosis as r
r.NAME = "cgof-rtl-ordering-confirmation"
seed = 6501
argv = ["--smoke", "--window", "256", "--mode", "finite-heavy",
        "--policy", "both", "--ordering", "both", "--seed", str(seed),
        "--windows", "1", "--depth", "16", "--profile", "near",
        "--heavy-work", "256", "--ready-pattern", "bursty",
        "--ready-period", "100", "--jobs", "1", "--make-jobs", "1"]
code = r.main(argv)
```

完整外層命令、stdout/stderr、UTC起迄與exit封存於command records。Inner
`config.argv=[seed]`是wrapper process argv，不能冒充完整runner
command。20個seed各自13/13steps PASS，沒有單一campaign OS
process，因此不虛構aggregate exit code。模型切換前一次preflight
wrapper被中止且無seed執行，之後原命令通過；其記錄未刪除。

實際完成160RTL jobs、80mixed/isolated pairs、80lint configs、
20traffic invocations／100cases；180份JUnit沒有failure/error/
skipped。20seed皆source stable；31source hashes、source ZIP、
160完整trace重播、80lane-pair prefixes、160setting prefixes
全通過。Source manifest SHA256為
`3fc28d71a390e25d1bfe831d504d5a037303fc89591a56d9088f0bab1aca9692`。
每job只有active close255、states H/B_H，effective High全程成立。
Active317–339cycles；每seed四mixed設定的完整Sparse generation
cohort相同，20/20通過。Generated=accepted=fired=42,620，
final request censoring=0、Sparse active-cut pending=0、
drain completed=0，全部jobs的drain_cycles=0。

主要端點是full-run Sparse generation→fire nearest-rank P99；
契約包含ready=1 drain，不能據此宣稱active-only或持續bursty
drain結果。每run僅12–32Sparse requests，P99等於樣本最大值。
主要d1=Q1-RR−Q1-OF在20seeds全零；d2=Q2-RR−Q2-OF與
I=d2−d1在7seeds為−1cycle、13seeds為零，兩者mean−.35、
median0、range−1–0。沒有reversal，但joint strict改善僅7/20，
未達預先15/20門檻，故裁定 **`NOT_CONFIRMED`**。
這不證明no effect、equivalence或oldest-first優勝。

次要資料完整保留160job rows、80lane-pair rows、
160setting contrasts、80completion contrasts、20primary rows，
各lane的Heavy/Sparse/active-duration interaction與A/R summaries。
Isolated Sparse為null/N/A；可用summary每格20seeds。Q1
ordering端點40比較、isolated各設定60比較皆相同，但不是
action-trace等價證明。Q2 ordering的mixed Heavy max/wall-P99/
ready-P99 mean delta為−.10/−.15/−.10；A/R所有setting contrasts
及interaction為零，A本身0–6cycles、R為1–1.01875。
Gap種類與單位分開，不作policy score/rank/CI/p-value或一般winner。

Supervisor audit保留四attempt及所有衍生版本：01錯把wrapper argv
當完整runner command而拒絕；02修正後PASS；03修正次要summary
按完整factor/lane/reference/candidate分組；04補齊原先計畫要求
的次要interaction、A/R與equality輸出。僅重算保存資料，未再跑
實驗，主要rows與verdict保持不變。Audit self-check涵蓋signed
interaction、ties、14/15門檻、reversal、missing/cohort mismatch、
nearest-rank及不可把missing當零。較早衍生檔完整保留。

Canonical證據位於
`artifacts/implementation/cgof-rtl-ordering-confirmation/`：
manifest `manifest-20261101T045246Z.json`，SHA256
`5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384`；
analysis SHA256
`101b1c1c8ee4327b99104af267761c98f17182205f4154e7e2f7825bf2e0c954`；
pair audit SHA256
`1e479cfcca502b7167375b1a36e27a374fecdd73388b830de2f3ec4f50cc8426`。
`command-records-20261101T044617Z.json` SHA256
`e78f4fdfc5a14be1eed4b241025dc0f6f1024e4c3013232bd17d8f7f4771eb87`。
`acceptance-20261101T045246Z.json`綁定計畫、canonical analysis、
logs、前次已驗收證據及四文件before/after。詳細對照表在
`docs/reviews/evidence-review-followup-20261101.md`。

本輪execution/integrity/manipulation PASS，主要claim未確認；
原五seed探索不升格也不混算。未改主論文或歷史generator inputs。
未跑W5M ordering production、新EDA/PPA/formal/CDC、Buffer
latency recovery、CXL response/bandwidth或application量測。
既有14個power-vector errors未處理，與本批PASS分開。

## 2026-11-02：W5M ordering production五seed描述性探索完成

Owner指定Astra透過Codex CLI撰寫計畫、Codex擔任監督並派工；計畫凍結於
`docs/reviews/ordering-w5m-production-plan-20261101.md`，SHA256
`ee96755baaf1d38fc9470a8565b92b247813f061b1e86c93ece88dd008179063`。
本輪維持描述性：不升格confirmation、不pool 40 jobs、不宣稱winner、
equivalence或latency recovery；W256的`NOT_CONFIRMED`與其分母不變。
最終狀態為`COMPLETE_DESCRIPTIVE_EXPLORATION`。

Planner以`codex exec --json -m codex/gpt-6-astra`、high執行，log為
`.setup-logs/implementation/ordering-w5m-production-20261101/astra-plan.jsonl`
（SHA256 `2fafc72c197ee4d323bcdcdd971185c608928336a1c58d82a18ac645dc758f19`）；
requested model與effective backend分開，backend維持`UNKNOWN`。Executor原定
`auto/deepseek-v4.1-flash`，但目前的sub-agent roster未提供該backend（僅
`gpt-6.1-sol`變體）。因此6602–6605（含6602重啟）由supervisor以凍結wrapper
執行，6601與6602首次啟動走原executor路徑。此偏離連同invocation records
記入manifest provenance；executor effective backend同為`UNKNOWN`。

6602首次啟動在lint/pytest後約3分鐘、尚無任何cocotb job時中止；原因為
generated completion writer的Python string literal含實際換行，simulation後
會SyntaxError且不產生runner-completion.json（exit code遺失）。該attempt
已終止並保留
`aborted-attempt-seed-6602-20261102T084039Z.json`（SHA256
`bf3308b7a7f1f35d04128fd5dc811369a3656f91e2a61f69e85ba75bc8d1fdbc`）及
run dir `20261102T083522Z_17626`；重啟後8 jobs全部完成並通過gates，
aborted run不貢獻任何資料，也不計入audit。

凍結矩陣：N4/D16、W5,000,000 finite-heavy、Heavy 5,000,000/source0、near
（Heavy p=.80、Sparse各.02）、bursty ready p=.90/period100、Q1=1:1與
Q2=2:1、OF與eligible-RR、mixed/isolated、`--jobs 2 --make-jobs 1`、
active cap 8,000,000、campaign cap 36h。每job必須只跨cycle4,999,999的
唯一close，且`5,000,000<C<=8,000,000`；不得有第二close、有效Low或
未跨第一close。

| seed | run_id | runner s | audit s | S Q1-OF/Q1-RR/Q2-OF/Q2-RR | d1 | d2 | I | Hmax RR−OF Q1/Q2 | A |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |
| 6601 pilot | `20261101T084343Z_36851` | 5625.636 | NOT_RECORDED | 11/11/12/11 | 0 | −1 | −1 | +2/0 | 3 |
| 6602 | `20261102T083916Z_28524` | 5467 | 394.456 | 11/11/12/11 | 0 | −1 | −1 | +2/0 | 0 |
| 6603 | `20261102T102609Z_1337` | 5474 | 397.268 | 11/11/12/11 | 0 | −1 | −1 | +1/0 | 7 |
| 6604 | `20261102T121108Z_2787` | 5429 | 401.774 | 11/11/12/11 | 0 | −1 | −1 | +2/0 | 1 |
| 6605 | `20261102T135444Z_2822` | 5544 | 403.445 | 11/11/12/11 | 0 | −1 | −1 | +1/−1 | 8 |

Campaign自2026-11-01T08:43:43Z至2026-11-02T15:27:08Z，30.72h，在36h
上限內（deadline 2026-11-02T20:43:43Z）。Runner wall合計27,539.636s，
audit合計1,596.943s；pilot的audit wall未記錄，僅保留gate hash。五seed
皆通過八個gate：execution、identity、source integrity、manipulation、
input controls、accounting、endpoints、resource/release。

實際完成40 RTL jobs、20 mixed/isolated pairs、20 lint configurations、
5 traffic invocations／25 cases、40 RTL tests與45 JUnit files。每job只有
active close4,999,999、四來源old classes皆H且classes為`[B_H,H,H,H]`、
effective High全程成立、`FULL_SPARSE_COHORT_MATCH`、final censored=0、
cut pending=0、drain completions=0、drain_cycles=0；completion約6.25M
cycles。Mixed Sparse cohort為374,935–376,862 requests。31個pinned
sources在before/after/pin/worktree一致，source ZIP members與per-member
SHA相符；每seed完整active trace重播、8個Heavy sequences共用digest、
mixed四設定的Sparse cohort相等，全部通過。

主要端點：五seed的S皆為11/11/12/11（Q1-OF/Q1-RR/Q2-OF/Q2-RR），
d1=0、d2=−1、I=−1，5/5一致。這只表示Q2的RR−OF差比Q1更負1 cycle，
不表示RR全面較好。Mixed Heavy max-gap：Q1 OF固定14、RR為15–16；Q2 OF
固定17、RR為16–17；RR−OF為Q1 +2/+2/+1/+2/+1（mean+1.6）、Q2
0/0/0/0/−1（mean−0.2）。A=Cmixed−Cisolated在每seed的四個設定相同
（3/0/7/1/8 cycles），其RR−OF對比10/10為0；mixed與isolated completion
最多差8 cycles。RR在此work-saturated協定下以Q1較大的worst-case Heavy
gap換取Q2 mixed Sparse P99少1 cycle；這是描述性tradeoff，不是ranking。

Audit修訂如實保留：v1未用於結果（mixed delta在原設計下不等於paired A
delta）；v2用於結果，改為paired mixed-minus-isolated A值，並檢查runner
wall cap、10GiB free space與zero avoidable bubbles；v3、v4的gate先後因
list-vs-scalar assertion及105-bit descriptor packing失敗，未用於結果；
v5以string setting keys修正seed_row序列化並以固定的14-byte big-endian
descriptor重播，產出保留的PASS gates。6601的gate檔案
`gate-6601-20261101T101830Z.json`、`...101846Z.json`與中斷的
`...101901Z.json`全部保留。任何audit修訂都只重算已保存資料，沒有重跑
simulation。Correction record
`audit-version-record-correction-20261102T083432Z.json`修正原v2紀錄的
`seed_6601_started_before_v2_freeze`：v2 freeze時間為
2026-11-01T08:42:31.878Z，pilot runner start為08:43:43.058Z，實際晚72s；
原檔保留不變，correction為正式紀錄。

限制：五seed僅描述性，不做population inference、CI、p-value或winner；
planner與executor的effective backend皆`UNKNOWN`；6601 audit wall未記錄；
helper的`"resource":"PASS"`是常數（真正assertion為wall<21,600s、
run volume≥10GiB與supervisor檢查），`gap_kind_counts`把eligible_ready與
wall_cycles兩個dimension相加而重複計數，cohort/Heavy digest只用本campaign
encoding，threshold arithmetic依賴runner的per-cycle oracle。未跑新
formal/PPA/CDC/EDA、CXL response/bandwidth、application或latency
recovery，也未改主論文、RTL、model、spec、runner或tests。

Canonical證據在
`artifacts/implementation/cgof-rtl-ordering-w5m-production/`：
manifest `manifest-w5m-campaign-20261102T154205Z.json`，SHA256
`de7f657240ed4dc24c46be3e2166893502dbd2b229aebedf6cc07739649edee5`；
acceptance `acceptance-w5m-campaign-20261102T154205Z.json`，SHA256
`9b3f8588f87b6fe980b6181bb61f1224907686242ec24e1e89e4dba8c455ffab`；
campaign analysis SHA256
`76c1ac380a594787531ba597cc71bf06267cad690bd3bdf51109a48724d50b3c`；
audit helper SHA256
`8ca98ac20a063d0965d0e9a4b1c9e3e276d43d4c700fd9ee8875a6920d8f1c8a`；
correction SHA256
`d91f6574aea7dac9afcf07cba4e882c09ad9ae98fad77fd088c55f614075b8d4`。
五個PASS gate：6601 `fb2b6658fa6a9fa5ca52dd6c5e057e0a2586a3bc2d495db192aaca0b737c2b53`、
6602 `67524ff90e3dc8e58d10194b219182b5e5c271dcec09f93eca96bde5c650ef4e`、
6603 `688d6ef898a1661b0bdfd2c1da3ce33d42b6256b0091d57657d1faff8a0593be`、
6604 `c353aa354145a6e27b3da6704a9a9cad0af8e37f93a2b2ce6ce7c2f517216818`、
6605 `e2068925fb52284534ada8fef326e1446824077d5e72cddecd42c633877b6afe`。
每個seed的release、analysis、command record、runner stdout/stderr與gate
路徑列於manifest；新檔皆以exclusive-create寫入，歷史artifacts未改。

## 2026-11-03：多視窗動態／角色切換 RTL 計畫凍結，尚未執行

Owner要求先完成第一優先缺口的實驗計畫、成本與seed清單並commit，
同時整理兩位reviewer的回饋。本輪授權僅planning與commit，沒有啟動
RTL實作、模擬或EDA。主計畫與機器入口為
docs/reviews/dynamic-role-switch-rtl-plan-20261103.md／.json；外部hash receipt為
docs/reviews/dynamic-role-switch-rtl-freeze-20261103.json。
狀態FROZEN_PROTOCOL_NOT_RUN，執行狀態BLOCKED_ON_MAIN_AND_AUDIT_IMPLEMENTATION。

Orca Worker reviewer-2（fe32ywtpnoekmp81ca1l95mr，requested
auto/gemini-4-argon／high）整理初稿，Lead覆核並修正；保留另一位
reviewer（fzfqgpl9p81gsljob6qhey68）的報告scope、non-blocking gap、
C1/C2 provenance與不混算證據等回饋，另採納reviewer-2的五案例／Main
對照／角色反轉／深度比較建議。八項回饋採納／延後表在計畫§0及JSON。
RR10延後，其他四缺口不混跑；現有報告的限定主張保持，不能以20seeds
或完成執行就自動把C7升格CONFIRMED。

依Owner既有偏好，Worker以Codex CLI呼叫codex/gpt-6-astra／high、
read-only一次，exit0，thread 01a1a06d-07d7-7c21-8d9a-8160055293bc。
Effective backend UNKNOWN。Astra明示只審提供的條件／數字，未讀檔，
不是raw-data獨立核對；prompt中轉義控制字元亦保留。Lead直接核讀
五個scope/config/summary與原始碼，修正ready80→90%、period及Sparse
count、生成率解釋、不存在CLI、5seed確認／optional stopping、統計法
歧義、Main自然class差異選樣、事後截cohort、舊C4成本誤述與過低磁碟
估算。Worker原稿與所有Astra輸出保留於ignored
.setup-logs/implementation/dynamic-role-switch-rtl-plan-20261103/。

唯一矩陣：N4／W5M／Heavy17.5M／near（Heavy .8、Sparse各.02、ready .9）、
oldest-first、Main 10:10／CGOF1:1／CGOF2:1、mixed／isolated；五案例為
multi-window、role-switch [0,0,1,1]、ready-spread、ready-bursty、
depth8-bursty。每seed30jobs／15pairs；工程pilot7301獨立，正式7401–7420，
總630jobs／315pairs，推論僅20個完整seed blocks。整個finite-cohort協定
含各自Heavy completion cut及ready=1 cleanup；來源／生成角色雙帳本、
source-local Heavy gaps、cohort差異與全部censoring明列。

Main尚未接入現有CGOF診斷runner。先完成Main wrapper/model/held-grant、
W64/W256 lint/cocotb、CGOF零退化、audit/analysis介面與source freeze，
再談執行；本輪沒有把未實作的policy all冒充已可用命令。

主終點只有mixed Sparse whole-run G→F P99；P1/P3為Main−CGOF2:1，
分別role-switch/multi-window，P2為role-switch CGOF2:1−CGOF1:1。
固定1cycle工程差異、exact單尾binomial跨seed事件檢定與三比較Holm .05；
10,000次配對seed-block bootstrap區間僅描述性。Heavy gap與A為次要代價。
首5seeds不是提前確認方案；任何未完成／timeout／缺格停止後續，不能挑
成功子集、換seed或提高並行度趕上限。

20個舊CGOF步驟均值6332.058s，總35.1781 job-hours；五run wall合計
17.6335h。Main速度未量測。630jobs在jobs2下線性554.06h、範圍
533.21–578.26h，含20%假設保留量664.87h。另加逐seed audit預算42h與
final8h，campaign估714.87h；工程16–24h另計，整體730.87–738.87h。
硬上限：每job3h、seed simulation34h、audit4h、simulation累積680h、
campaign含等待810h，加工程842h。最多jobs2／make-jobs1，不平行seeds。
舊records約3.223MiB的630job外推101.53MiB不是完整磁碟估算；build cache、
scratch／新ledger與RSS待pilot量測。兩volume起始各100GiB free、保留20GiB，
pilot投影另加50%headroom；不足停，不刪歷史cache/runs。

來源索引逐path/hash覆核，含112項來源；DEVELOPMENT_REPORT的append前
snapshot另存以避免追加紀錄使pin立即失效。計畫MD／JSON hash由獨立receipt
綁定、無self-reference。所有execution/PPA/formal/RTL gates本輪仍NOT_RUN。

Lead驗證：verify_final_plan.py核對112項來源hash、五案例現有CLI parser、
630jobs／315pairs、三個primary及實測成本算術，PASS；完整log在上述目錄
lead-final-validation-scoped.log。初次全JSON掃描因耗時中止，改用本機
metadata命名JSON的scalar/list seed欄位搜尋，無歷史命中；不涵蓋JSONL、
escaped命令或外部電腦，不宣稱全域無碰撞，開跑前必重查。
規劃資料整理helper曾有根目錄與generator pop處理錯誤，修正後PASS；
失敗log保留，未因此重跑或變更任何既有實驗。

## 2026-11-03 精簡版 v2 備選提案（文件層級，未授權執行）

Owner要求以Astra協助檢視並精簡第一優先缺口的多視窗／角色切換計畫。
Orca Worker designer（claude-code／claude-opus-5-5，runtime回報high；
原始manifest記為session default，兩者並列保留）提出v2；Lead覆核後
保留為與v1並列的獨立備選，v1仍為FROZEN_PROTOCOL_NOT_RUN且不因本文件
作廢。v2為PROPOSED_NOT_FROZEN，本身不授權Main harness實作、campaign、
新模擬或EDA。

v2的核心問題是lockstep檢查能支持到哪裡。既有cocotb job的check()會逐
cycle比對RTL與模型；同一job內PASS可讓兩者餵給同一記帳程式的排程輸入
一致，但不足以證明獨立model runner能逐值重現所有指標，也沒有替未跑
RTL的seed提供RTL覆蓋。v2因此把統計來源改為650個純模型jobs，另用RTL
錨點做G-EQ；主分類維持MODEL_ONLY，另以rtl_anchor_coverage描述實際
錨點，不新增證據等級，也不提升C7。

預設錨點為A1（重用seed7291的20個CGOF W5M jobs，僅legacy欄位）、
A2（seed7301短W，Main與CGOF回歸，legacy＋new）、A3（seed7301 Main
4個W5M jobs）、A4（seed7401 Main role-switch mixed＋isolated 2個
W5M jobs）。合計新增6個Main W5M jobs。G-EQ-legacy與G-EQ-new分開：
舊輸出缺少的欄位標NOT_AVAILABLE，不以0或skip視為PASS；新欄位只在
新錨點與短W回歸核對，A1重用不能替新欄位補證據。預設方案中CGOF的
W5M新欄位覆蓋為0，另列2個RTL jobs的備選，未併入預設預算。

drain裁定沿用v1 §3.1與test_cgof_diagnosis.py：cut後以ready=1 cleanup，
bound為2·(producer_backlog＋fifo_occupancy)＋128，不reset；
scenario.ready只用於active。既有20個W5M錨點的drain_cycles皆為0，
全案drain行為維持NOT_EXERCISED，不作為任何錨點的gate；日後改採
scenario-ready drain須另立協定、另命名並重新freeze。

成本重新以「模型與RTL不重疊、模型最多7個process、RTL最多2個、逐seed
release」估算：G1／P／C累計約236 job-hours（不等於實測CPU-hours），
機器wall線性42.8h、加20%營運保留51.3h，人時約28.5–33.5h，合計約
80–85h，硬上限117h；完整runner速度、7個完整記帳process競爭、Main
RTL速度與pilot重跑均未計入或未量測。方案B（每確認seed都有RTL）估計
約235–243h，保留量已與純線性欄位分開。

七個MODEL_ONLY探針（seed9901五個探索、seed7291兩個重播）以repo外
script執行，輸出與provenance在ignored
.setup-logs/implementation/dynamic-role-switch-v2-probes-20261103/；
七個exit code皆NOT_RECORDED（背景&的wait一律回0），完成依據是最後
一行寫出的JSON與空stderr；iso.py前兩版未保留。7291對照只比6欄位×
2政策共12/12相等，histogram、G→A／A→F、Heavy gaps、cohort、fairness、
trace等未比；probe另有輕量記帳、單reset edge與較寬drain guard差異，
不能宣稱完整協定等價。seed7301只用於工程測速與W256 invariance，
9901列為排除，7401–7420未使用。

兩位reviewer回饋均納入：reviewer的B1／B2 non-blocking、C7不升級、
W256 NOT_CONFIRMED與W5M descriptive分離、逐path hash；reviewer-2的
五案例／Main對照／角色反轉／D8要求以模型擴展，Main僅6個W5M錨點，
RR10與其他四缺口延後或不在本計畫。檔案hash：v2 md
3a5ff663c15d5b573dfcd847d7c059e471e0a3435e786382bc9efe144188b051，
summary JSON ec8c25d2792e9e7fdaf04bcc9cb7181fe8a84dc93139319950bdce55a2d94249；
v1三個凍結檔與tracked RTL／model／tests／runner均無變動。

## 2026-11-04：v2 共用記帳、Main 接線與 A2 通過

Owner授權照v2推進，並同意designer停止時由Lead接手。Orca Worker
designer完成E1/E2、W256重構前後20/20零退化、模型／traffic測試
22 passed（18 subtests）、短W模型對RTL20/20，以及G1 seed7291的
20個W5M模型重播。G1記錄batch_exit=0、compare_exit=0，20/20 legacy
pairs逐值一致；2026-11-03 10:56:51–11:59:54 UTC，wall3783s，
job內部wall合計24603.72s。

Lead接續完成E3/E4/A2，未修改任何.sv、獨立模型、spec或歷史實驗。
共用DiagnosisAccounting保留collector語意；SourceBook新增physical
source與generation-epoch計數、cut pending/final censoring、per-source
三段延遲分佈。epoch只作計數，沒有phase/epoch P99。Main經既有
switch_experiment_top POLICY=2與FaiMainSwitchModel oracle接入，保留
共同FIFO/hold/timing；每cycle核對class/B/S/index/turn/used與模型
mirror，Main credit為null。runner新增main/all，both仍表示兩CGOF。

A2 run 20261103T181252Z_20159：W256五案例×三政策×雙lane30/30
與模型相等，W64角色反轉6/6相等，均含新帳本。另4個Main directed
tests覆蓋W64/W256×D8/D16：High-context grant stall跨B_H→L closing
edge，source/descriptor/context保持，stall不扣quota或計service。
40個cocotb tests全數PASS，wall215.224s。最終strict lint run
20261103T181748Z_1381共15個唯一參數配置PASS，含W5M、D8/D16。
unit25 passed＋18 subtests，current model對重構前CGOF W256的
20組legacy欄位全數相等，新欄位NOT_AVAILABLE。

驗收文件為docs/reviews/dynamic-role-switch-v2-implementation-acceptance-
20261104.md/.json、dynamic-role-switch-v2-g1-acceptance-20261104.json、
dynamic-role-switch-v2-a2-source-freeze-20261104.json。112個v1來源核對
僅2個授權collector/runner程式變更，其餘110項保持原hash；v1三凍結
文件與v2原計畫/summary未改。G1 source snapshots與原記錄hash一致，
該輪不能為新增帳本補證據。

pytest source-book/model/traffic → PASS（25 tests），log：
.setup-logs/implementation/dynamic-role-switch-v2-exec-20261104/unit.log。
run_dynamic_role_switch_a2.py → PASS（36 diagnosis pairs＋4 directed），
log：同目錄a2.log。run_dynamic_role_switch_a2.py --lint-only → PASS
（15配置），log：a2-lint.log。current model versus legacy W256 RTL →
PASS（20 pairs），log：legacy-shortw.log。acceptance.py → PASS
（36 pairs／4 directed／15 lint／112 inputs），log：acceptance.log。

MODEL_ONLY分類與C7 SINGLE_SEED/SCHEDULER_RTL保持；drain仍
NOT_EXERCISED。E5分析/seed audit工具尚待實作；A3/A4、完整W5M
pilot與7401–7420確認未啟動，確認seeds未用；沒有啟動EDA。

E5隨後完成：scripts/analyze_dynamic_role_switch.py固定單一主終點
（mixed、generation-time whole-run Sparse G→F nearest-rank P99）、
P1–P3、exact單尾符號檢定、Holm step-down與10000次paired seed-block
bootstrap（描述性）。seed稽核拒絕重複、缺漏、7291/7301/9901混入，
以及非MODEL_ONLY、非W5M四窗或drain≠0的輸入。5個單元測試（含
K=14/15/16與20/20邊界）與合成20-seed CLI smoke PASS，log：
.setup-logs/implementation/dynamic-role-switch-v2-exec-20261104/e5.log。
scripts/run_dynamic_role_switch_pilot.py只接受seed7301與W256/W5M，
拒絕確認與排除seeds；W256 dry run 30/30 PASS。

seed7301的完整W5M pilot（30個model jobs、7 workers）於2026-11-03
18:29Z啟動，輸出artifacts/implementation/dynamic-role-switch-v2-pilot/
20261103T182900Z_w5m，log：pilot-w5m.log；A3的4個Main W5M RTL jobs
排在model pilot完成之後，尚未啟動。

實測修正：pilot第一個完成的W5M job（multi-window isolated CGOF(1:1)、
21,873,605 active cycles、完整Metrics/RoleBook/SourceBook記帳）回報
wall 8,155.4s（2.265h），是凍結模型0.3473h/job的6.5倍（約2,682
cycles/s）。該模型來自只跑200k cycles、未跨W5M close的bench外推；
相同併發下7個輕量probe曾達19,000 cycles/s，故差異主要來自完整記帳，
而非WSL或7-process併發，但尚未以profile分離各collector成本。
依此重算：pilot約11.4h（原1.75h）、確認600 jobs約198h（原26.25h）、
G1/P/C job-hours約1,540（原236）、機器wall約210h（原42.8h）。
凍結協定要求預估超支即停止另提修訂，故確認階段不啟動；pilot續跑以
取得模型側資料與A3的G-EQ，修訂方向見docs/reviews/dynamic-role-switch-
v2-pilot-cost-correction-20261104.md（profile先行／接受較高預算／
縮小isolated矩陣，三者皆需重新凍結）。

A3（4個Main W5M錨點：role-switch mixed+isolated、multi-window mixed、
depth8-bursty mixed，seed7301，jobs2）於2026-11-03T22:46:23Z啟動，
run id 20261103T224623Z_714733；5項strict lint與source_book pytest
先行PASS，4個W5M cocotb jobs執行中。W256 dry run 4/4 PASS。

成本根因更正：設計者查核後發現超支來自pilot runner的ThreadPoolExecutor；
純Python模型受GIL限制，7個thread只使用1個核心（WSL ps：單一PID 101% CPU、
7個LWP各約14.5%），每個job wall約為單process的7倍，與完整記帳無關。
Lead自行確認程式L63確為ThreadPoolExecutor，G1的model_batch雖也用
ThreadPoolExecutor，但每項以subprocess.run啟動，故仍為真平行並符合原估。
subprocess量測（pilot佔1核、A3佔2核）：1 process 16,785 cycles/s（0.36h）、
7 process各13,547（合計94,830）、10 process各11,728、15 process各9,272。
單process 0.36h與凍結0.347h相差+4%。
據此重算：pilot約2.25h、確認600 jobs約45h（7 process）、G1/P/C約269
job-hours，15 process可選約26h wall。
處理：停止thread版pilot（已完成7個job，保留於
dynamic-role-switch-v2-pilot/20261103T182900Z_w5m作provenance），
pilot-runner改用ProcessPoolExecutor，並以process pool於2026-11-03T23:02:08Z
重啟（輸出20261103T230208Z_w5m_process、6 workers，保留2核給A3；確認6個
worker各約100% CPU）。重疊job將逐值比對確認決定性。此次模型與RTL同時
執行屬排程偏離，已記錄；確認階段仍須先修訂成本表並重新凍結。

process版pilot於2026-11-04T01:19:38Z完成：30/30 PASS、無失敗，wall 8,249.3s
（2.291h，預估2.25h，誤差+1.8%），job wall合計48,508.8s（13.47 job-hours）、
單job最大2,183.2s。與thread版重疊的7個job逐值相同（僅排除wall_s），
證明thread→process改動不影響結果。其中Main ready-bursty mixed與Main
depth8-bursty mixed出現drain_cycles=2，model側cut後cleanup確實執行；
RTL錨點drain仍全為0，故RTL drain證據仍缺。

分析器修正：原endpoint()把drain_cycles≠0判為不合格，與凍結協定「主要
Sparse P99包含drain完成者」矛盾；已移除該檢查並以測試確認drain=2仍可
計入，5個單元測試與合成20-seed CLI smoke重跑PASS。
驗收：docs/reviews/dynamic-role-switch-v2-pilot-acceptance-20261104.json。

A3完成：run 20261103T224623Z_714733，4個Main W5M錨點（role-switch
mixed/isolated、multi-window mixed、depth8-bursty mixed，seed7301、
active cap 24,000,000）全部cocotb PASS，5項lint與pytest PASS，wall
15,328.4s（4.26h）。首次G-EQ以pilot的40M-cap模型結果比對時4/4不符，
唯一差異是job.max_active_cycles（24M vs 40M）；cap從未觸發（active
21,873,610），但job規格不同不能算嚴格G-EQ。故以A3的原始job規格
重播4個model jobs（4 process，2026-11-04T03:47:11Z啟動，輸出
artifacts/implementation/dynamic-role-switch-v2-a3-model/
20261104T031500Z_a3spec），再比對結果4/4逐欄位相同，包含新的
physical_sources帳本（4/4 EQUAL）。

A3的source-stability gate未通過：執行期間有3個檔案被改動
（analyze_dynamic_role_switch.py、run_dynamic_role_switch_pilot.py、
run_rtl_diagnosis.py的source-index清單），三者都不在模擬路徑上，但
依凍結規則不得waive，故A3記為engineering evidence而非frozen-gate
PASS，狀態A3_JOBS_PASS_GEQ_PASS_SOURCE_GATE_FAILED，差異存於
.setup-logs/implementation/dynamic-role-switch-v2-exec-20261104/
a3-source-diff.json。RTL四個錨點的drain_cycles皆為0，RTL drain仍
NOT_EXERCISED。pilot矩陣的active cap已由40M改回凍結的24M。
驗收：docs/reviews/dynamic-role-switch-v2-a3-acceptance-20261104.json。

## 2026-11-06 FastX CGOF power input audit and remote preflight

Result: INCOMPLETE; CGOF power remains unmeasured. The detailed receipt and
reproduction index are in `docs/reviews/fastx-power-readiness-20261106.md`.
This task writes only the host-created sharp-bohr worktree at starting revision
`a3f4d8b1865c9af24eb86776274cc8c98428adc3`; original-repository inputs are read-only.

Cindy live runtime confirms Codex `group/gpt-6.1-sol-2`, provider
`magpie-18cf0ecc`, high effort. Read-only agy Gemini3.8 Flash/high inventory and
flow-review workers were assigned independently. The inventory worker was stopped
by its verified task-owned PID after repeated provider errors and no final report
(exit -1); its partial reads are not accepted as an independent review.
Flow review failed with exit3,
provider UNAVAILABLE/503. Preimplementation agy Gemini4 Argon/high review exited0,
ADOPT WITH CONCRETE CORRECTIONS. CLI auto mode was unavailable for this account;
actual init permission_mode was always-proceed/default. No model substitution or
global configuration change was made. Prompts, init receipts, streams, errors and
exits are preserved under `.setup-logs/implementation/fastx-power-20261106/`.

Implemented `audit_fastx_power.py`, its eight synthetic contract tests, and
`fastx_power_preflight.sh`. The audit observed twenty complete 30-job seed
directories7401-7420 plus three interrupted attempts, without directory stitching
or campaign reruns. It checked both N4 CGOF mapped bundles, current source hashes,
Formality download receipts and the pinned eighteen-capture trained-power index.
These observations do not reaccept the campaign or raw baseline power captures.
The separate WSL capacity-absorption runner and its six workers remain untouched.

Native terminal helper RemoteCommand succeeded; observed backends FastX-NN and
FastX-NN, account chiang22. The Synopsys2024 module loaded; DC W-2024.09 -version
returned1 and PT W-2024.09 -version returned0. Remote CGOF1/2 netlists/SDCs,
SAED32 DB and standard cell-model hashes matched locally recorded inputs. A first
preflight failed because native PowerShell treated remote module stderr as an
error; v2 captures remote stderr in stdout while retaining each command's exit.
No allocation ID or scheduler executable was observed, and permitted long-EDA
compute placement remains unverified. No license checkout or power analysis was run.

Validation: eight unittest cases pass with exit0 and no skips; WSL bash syntax
check exit0; actual input audit exit2 (deliberate INCOMPLETE); remote v2 preflight
and input/model hash checks exit0. Audit output is
`artifacts/implementation/fastx-power-20261106/input-audit-final/audit.json`,
with its SHA256SUMS. These are tooling checks, not new RTL lint/simulation/formal
or PPA results.

Remaining gates: freeze exact CGOF power seeds/arms/stimulus against either the
historical509-511 A/B cohort or a fully matched new baseline; implement and verify
cgof_unit_top/HIGH_WEIGHT adapters for the switch_top-only activity/PT flow;
verify allowed compute placement before a bounded license/replay/SAIF/power pilot.
No SAIF annotation coverage or leakage/internal/switching/total power exists from
this task; no netlist pruning, paper-result upgrade or long-backlog drain claim.

## 2026-11-07 FastX CGOF frozen cohort and offline activity adapter

Result remains INCOMPLETE; CGOF power is unmeasured and long-backlog drain is
unverified. Owner selected seeds509/510/511 with separate A/B arms and supplied
the local fastx-ews references/eda-rules.md. That reference explicitly prohibits
long EDA on shared login nodes but contains no approved compute node/allocation
or launch command. No remote EDA, license checkout, uploads or new run directories.

Implemented scripts/export_cgof_power_vectors.py and two new contract-test files;
updated the audit's owner-cohort status and added a guarded CGOF configuration
branch in sta/power_pt.tcl. No HDL or accepted netlist changes. Exact parameters,
hashes, commands, exits, routes and acceptance limits are recorded in
docs/reviews/fastx-power-readiness-20261107.md and the ignored artifact-index.json
under artifacts/implementation/fastx-power-20261107. Only sharp-bohr is writable;
the original repository remains read-only, with its existing README change intact.

The freeze verified the eighteen pinned FCFS/RR10/Main baseline metadata/semantic/
native/archive receipts and six per-seed/arm traffic identities, plus both accepted
CGOF1/2 mapped netlist/SDC/config/profile/library/source contexts. It does not
rehash historical giant vector payloads or reaccept historical power. One traffic
source differs only in CRLF/LF bytes; exact normalized-content comparison and both
raw hashes are retained, while substantive drift remains rejected. No proprietary
cell library, PDK, executable or license was copied.

Four actual W256 model-only fixtures cover both weights and A/B at seed509.
A has512 warmup+64 measured rows; B retains101536 warmup+64 measured rows.
All exports and serialized re-audits exit0; a repeated CGOF1/A fresh export has
identical vector text/gzip/archive hashes. Independent passive FIFO/arrival/credit/
classification bookkeeping checks every pin row and conservation beside the
reference model. These are not hardware replay, SAIF or power evidence. Production
10M training exports/captures remain unrun. The actual readonly inventory observes
twenty complete7401-7420 seed directories and three excluded incomplete attempts,
no complete-source drift/missing/duplicate; no confirmation campaign was started.

Validation: CGOF vectors11, CGOF Tcl5, audit8 and unchanged revision vectors14
tests pass. Unchanged power extension discovers22:14 pass and8 Linux simulator
checks skip on Windows. Total52 passed/8 skipped; skips are not PASS. Tcl tests use
a real interpreter and stop before the first EDA command. Existing revision tests
first exited5 with zero tests because ignored mapped inputs were absent from the
worktree; staging twelve project-generated baseline files read-only with SHA
receipts restored those unchanged tests. Early freeze failures and repaired-test
evidence are preserved. bash syntax and git diff --check exit0. No new scheduler
RTL lint/simulation/formal/CDC result is claimed.

Main runtime was rechecked via Cindy get_session_runtime: Codex
group/gpt-6.1-sol-2/high, provider magpie-18cf0ecc. Independent preimplementation
review: agy gemini-4-argon-high/requested high, exit0/SUCCESS. Adopted corrections
include real B fixture warmup, receipt variants, paths, passive credit ledger and
CGOF Tcl guards. --mode auto was unavailable; actual default/always-proceed mode
is retained, and provider reasoning depth is not attested. Separate readonly
Gemini3.8 Flash/high baseline and implementation checks timed out at240s/180s,
exit3 without a final review; neither counts as independent acceptance. No silent
route substitution, recursive workers or global routing/settings changes.

Native Claude Code2.1.318/RTL Agent Team0.14.6 testbench preflight requested
claude-opus-5-5/medium/rtl-agent-team:testbench-dev, but returned exit1/HTTP403
subscription authentication api_error, no model inference. This is not established
allowance exhaustion. AGENTS requires native Claude RTL delegation and permits
Sol/high fallback specifically for exhausted allowance; the testbench remains
unchanged pending restored Claude or explicit authorization for this403 fallback.
The reviewed remaining scope is CGOF testbench adapter, SAIF/PT checker, bounded
runner, actual RTL fixtures and a single permitted remote gate-level pilot.

Own-terminal fastx-connect.ps1 -RemoteCommand refresh exits0, accountchiang22 on
observed backendFastX-NN. No own EDA observed on that backend; other backends are
not covered. No allocation IDs observed. Initial local WSL filter failed because
rg was absent, exit127; corrected ps/filter exit0 found no matching project runners
at that instant. Explicit native wsl.exe/Ubuntu host/process/tool receipt is retained.
No other active job was stopped or taken over. Power components/SAIF coverage
remain NOT_RUN; no claim is promoted to chip power or physical signoff.

### 2026-11-07 continuation: owner-selected Claude retry, adapter and local integration

The owner explicitly chose to retain Claude and retry the403 instead of accepting
the proposed Sol substitution. Native Claude preflight and implementation both
exited0. Claude Code2.1.318 / RTL Agent Team0.14.6 invoked
claude-opus-5-5, requested medium, firstParty; init and modelUsage confirm actual
inference. Provider reasoning depth is not attested. No global routing/authentication
settings were changed. The prior403 failure is retained as history and is resolved.

Claude alone wrote sim/power/tb_power.sv and scripts/test_cgof_power_tb.py. The TB
adds45 lines and preserves baseline text byte-for-byte after removing its CGOF
branches. W256 fixtures explicitly select weights1/2 and ELIGIBLE_RR0; production
uses the unparameterized retained mapped top. Canonical CGOF V2 headers constrain
N4, policy IDs3/4, seeds509-511 and exact A/B warmup/measured durations. Mode9
requires both fixture and NO_SAIF defines. Existing baseline allowlists are unchanged.

Parent Codex independently inspected the diff and reran the actual local suite:
10/10, no skips, exit0. Four strict Verilator5.052 builds exercise both weights
and fixture/production header guards. Actual W256 A/B RTL pin replays include
B's101536-cycle warmup. Icarus12 pin-only stubs check four-state rejection; they
implement no scheduler and supply no scheduler functional acceptance. Production
header-only tests do not validate mapped weight1 topology. Commercial toggle
tasks, mapped gate simulation, SAIF and power remain unrun. Claude's own separate
10/10 run is retained but not double-counted in the integrated totals.

Parent owns scripts/check_cgof_power_replay.py, scripts/run_cgof_power_pilot.sh
and scripts/test_cgof_power_checker.py. The checker binds current source/archive/
mapping/profile/library/model hashes, training closings, per-phase conservation,
replay totals, all SAIF signal records, clock/residency/X/Z, PT components/units/
coverage and FF clock provenance. Constant-X signals, annotation source tables,
warnings and disabled arcs remain subject to semantic review. Synthetic parser
fixtures never constitute measured power, and method acceptance is never automatic.
The runner is single-directory/single-core with fixed stage timeouts and native
command/log/exit receipts, source-before/after checks, compute/payload checks before
tools and refusal to reuse an execution directory. A compute receipt records
independently verified school permission; valid-looking JSON alone grants none.

Independent integration found and repaired a duplicate-SAIF-path key mismatch,
payload string/Path hashing bug and missing revision_matrix.py in the frozen
import closure. Tests cover successful isolated synthetic payload binding and
source/mapping/archive/vector/audit tampering, missing compute, fixture refusal,
rerun refusal and mutated production training closings. Failed intermediate
receipts remain alongside the passing ones. The first unchanged Linux legacy
run failed with7 errors because its Windows worktree gitdir path could not be
resolved by Linux Git. Invocation-local GIT_DIR/GIT_WORK_TREE targeting the same
worktree repaired the environment, without changing Git config or tests.

Integrated unique totals: CGOF vectors11, Tcl5, audit8, unchanged revision vectors14,
CGOF checker/runner10, unchanged legacy power extension22, CGOF TB10:80 passed,
0 skipped, all native exits0. Both shell syntax and git diff checks are separately
recorded. This includes actual local RTL fixture replay, not a commercial gate
replay or a new scheduler formal/CDC claim. Commands and complete stdout/stderr/
exits are in .setup-logs/implementation/fastx-power-20261107/verify_integration.py
and its receipts; exact CLI prompts/streams/receipts retain per-task provenance.

Four new fixtures-current exports and serialized audits exit0 with current
adapter/checker/runner/test hashes. Old fixtures and the pre-Claude artifact index
are preserved as historical snapshots. Offline prepare_payload.py verifies the
archive and extracts explicit safe manifest paths exclusively, with no overwrite,
network or EDA. A separately unpacked fixture imports successfully under WSL and
passes runner syntax, exit0. Production model export is completed below; mapped
gate capture remains unrun.
No proprietary assets were downloaded or packaged.

Only Host-created sharp-bohr is writable. Original tracked status remains the
owner's M README.md; no commits, branch switches or cleanup. This continuation
performs no new SSH or remote write. Existing SSH connectivity is not license or
allocation evidence. Current EDA rules require written instructor/EWS/EngrIT
permission for a named FastX execution node, or a verified Campus Cluster
allocation with actual Synopsys installation/license. FastX has no observed batch
scheduler; Slurm is not a FastX prerequisite. Neither permitted route is currently
established, so mapped replay/SAIF/power are BLOCKED. The next remote action is one bounded
CGOF1/A/509 pilot on verified permitted compute, followed by semantic acceptance
before any expansion. No jobs were stopped/taken over and no confirmation or
7406-7420 campaign was released. CGOF power remains unmeasured, all four power
components and annotation coverage NOT_RUN, long backlog drain UNVERIFIED.
The updated readiness report and artifact index are the handoff entry points;
all future estimates remain pre-layout zero-delay, not physical-chip measurement.

### 2026-11-07 owner-provided FastX execution and power-method context

Read the original repository's PPA_EXECUTION_2026-10-20.md, FASTX_HANDOFF.md and
POWER_METHOD.md directly. Historical document and raw receipt bindings are in
artifacts/implementation/fastx-power-20261107/historical-context/historical-context.json.
capture_historical_context.py exits0 and records the original tracked status as
the existing M README.md. No original file was modified.

The October17 handoff is an unvalidated direct-Bash template. The October20
execution record and actual nine-element independent audit establish historical
DC/PT execution with v1 profile6baba481, setup8/9 and OPEN electrical closure;
power was NOT_RUN at that checkpoint. These remain historical accepted records,
not new runs. POWER_METHOD establishes the existing VCS plus PrimeTime power
flow with the cap075 v2 profile6f4777f0, original SAED32 RVT TT0.78V25C DB,
ForQA/top,25ns and zero-delay/noSDF. No new PrimePower flow is substituted.
The frozen18 trained baseline captures and seeds509-511/A,B remain authoritative;
the historical cold100K seed509 dataset is not a matched replacement.

The actual old RR pilot raw exits are compile0,sim0,pt0,shell_exit1, with the
complete100000-cycle replay marker. This proves historical tool execution and
retains its shell audit rejection; it does not promote that raw pilot to PASS.
Historical direct FastX execution does not satisfy the current Skill's written
course/node permission gate or prove current CGOF license checkout. No mandatory
Slurm route is invented and no Campus Cluster/account substitution is made.

One local production CGOF1/A/509 model export was launched with W5000000,
10000000 warmup and100000 measured cycles, followed by its serialized independent
ledger audit. It uses frozen current runtime sources and a new worktree artifact
directory. Exact command/stdout/stderr/native exit are retained under the ignored
historical-context/production-export.* logs. This is input preparation, not EDA,
SAIF or power. No accepted baseline or confirmation campaign is rerun.

Production export completed2026-11-07 04:05:12-04:20:27 Asia/Taipei
(2026-11-06 20:05:12-20:20:27 UTC), exporter and launcher native exits0.
The local monitor budget was5400s; actual duration914.6s, no timeout or export
restart. The ownership-bound monitor handoff and original wrapper status are
preserved separately from the successful export's native status. Command:

```powershell
& ./.venv-fastx-power/Scripts/python.exe -B scripts/export_cgof_power_vectors.py --evidence-root $EvidenceRoot --weight 1 --seed 509 --arm A --window 5000000 --out artifacts/implementation/fastx-power-20261107/production-pilot-cgof1-A-s509
```

Exact argv and the read-only evidence root are in production-export.receipt.json.

All10100000 serialized rows passed the independent FIFO/credit/class ledger
audit. Actual production metadata also passes check_cgof_power_replay.check_metadata.
Training closings4999999/9999999 include the closing fire before clearing B/S,
with next classes B_H,H,H,H then L,H,H,H. The exogenous trace is the pinned509/A
c49208b8ef08899cbf6557c14ab53c57d4429abf7651456abe07aa5d6851d8f9.
Model accepted10100014, fires10099999 and cut/end outstanding15,0,0,0 satisfy
conservation; no drain is inserted. Gzip205703129bytes has SHA256
97bb724fd8727321b14b5f76e6a77e6ee7e7d5f45b91faf6aad82b877d0cf1a1;
source archive SHA256a35aeb5f47b5727017c7b49b0ead735f9071fe4bb210bfe919a7caeba14e1b98.

verify_production_payload.py runs prepare_production_payload.py, then an isolated
WSL Ubuntu Python import and Bash syntax check inside production-payload-cgof1-A-s509.
Both native exits0. Preparation reuses the completed serialized audit with exact
receipt/audit/source/archive/vector and destination-byte bindings instead of
replaying the settled10100000 rows again. All source manifest members are
explicitly verified and exclusively extracted. No proprietary library/PDK/tool
is included. Complete command/output/error/exit receipts are indexed.

The80-test integration result remains applicable: runtime sources were not edited
during or after the production export. This adds one real production model/input
acceptance, not another counted unit test or a mapped hardware/power result.
The other eleven CGOF inputs are not prepared or released. Remote replay/SAIF/PT
power remain BLOCKED by the current written execution-location permission gate;
annotation and all four power components remain unmeasured, long backlog drain
UNVERIFIED. No new SSH, remote upload/write, commercial job or baseline rerun.

### Owner-authorized direct CGOF1/A/509 pilot — 2026-11-07

The owner explicitly requested removing the additional written-permission gate
and executing directly. The local FastX Skill and its eda-rules/connection-pitfalls
references now permit one direct bounded pilot with one core, existing stage
timeouts, a fresh remote directory, and actual site/tool restrictions. No new
instructor/EWS/EngrIT letter or Campus Cluster allocation is required by the agent.
This records owner authorization without claiming institutional permission.
The three prior rule files are backed up in ignored owner-direct-pilot logs.

Native Windows OpenSSH key/agent preflight was rejected; the dedicated key was
absent and the agent unavailable (outer command exit1). A visible native SSH
console was opened on Jay_workshop using strict known-host checking. It requires
manual owner password entry, consistent with the task's credential restriction.
The helper's stored DPAPI credential was not accessed. Cindy ask_owner returned
UNSUPPORTED because its input handoff is unavailable on Windows; the real SSH
console remains the owner's remote-desktop input location.

The launch script streams the existing production payload through the same SSH
connection after backend/account/jobs/load/module/runtime and input inspection,
then invokes the frozen runner once. It preserves command output, native exits,
the actual backend-bound owner receipt, and allowed reports/SAIF for review.
No scheduler or allocation is fabricated, no baseline is rerun, and no unrelated
job is stopped. Current status is WAITING_INTERACTIVE_SSH; VCS/PT power checkout,
gate replay, SAIF, annotation and power remain unrun/unmeasured. The current
report is docs/reviews/fastx-power-direct-pilot-20261107.md.

### FastX production pilot execution — 2026-11-07

Authentication succeeded through the local FastX Skill helper and its existing
DPAPI credential. The chat-provided value was not persisted or added to argv,
logs or project files. The unauthenticated task-owned native prompt was closed;
its exit -1 and zero-byte output are retained. No credential or manual sign-in
request remains pending. Task-local AsyncSSH/SFTP support uses the helper's
existing credential lifecycle and pinned known_hosts, without transferring the
Skill directory. The exact helper command and transport argv are in ignored
owner-direct-pilot logs.

Two infrastructure attempts are preserved separately. Attempt01 returned
payload=1/shell_exit=1 because download-manifest.json is a local download receipt
absent from the accepted remote bundle. The runner now reads the fresh payload's
mapped copy after cmp verifies all six actual remote inputs byte-for-byte against
that copy; the accepted bundle remains unchanged. Attempt02 passed payload but
returned compile=127/source_check=1/shell_exit=1: module loads inside the piped
preflight group were confined to a subshell, leaving the parent without VCS/PT
and using system Python3.9. Loading Synopsys2024 and Python3.12.10 in the parent
bootstrap shell resolves that environment error. Neither attempt produced power
and neither is accepted as a scheduler simulation. Their raw receipts and
allowed reports are retained in attempt-01-input-metadata and attempt-02-environment.

The current fresh run, cgof-power-owner-direct-20261106t204718z, began at
2026-11-07 04:47 Asia/Taipei. Actual backend/account, full paths, exact package
hash, compute receipt, modules, resources, commands and native exits are in
transport.receipt.json and the remote bootstrap/evidence archive. The existing
production payload was reused without repeating its completed 10.1M-row model
audit. Both compile and compile-log-audit returned0; the actual VCS_Full64
mapped gate replay is running with one core and a1200s stage limit. The standalone
vcs -ID diagnostic returned1 because it selected a nonexistent32-bit compiler;
the successful -full64 compile and runtime banners establish the actual version.
The diagnostic remains a failed query, not a claimed tool check PASS.

prepare_matched_baseline.py produced matched-baseline-509A.json, exit0. It uses
the pinned accepted18 index, frozen metadata and semantic receipts for only
509/A FCFS/RR10/Main. Existing total powers are3.356/2.559/3.466mW. It preserves
policy-specific admissions, fires and cut/end outstanding work. Common trace,
profile, depth and measurement/training durations match CGOF's prepared input.
This is preparation for comparison, not a baseline rerun or new acceptance.

No frozen runtime sources changed. Existing80 passed/0 skipped remains the
applicable integration result. Claude Code2.1.318/rtl-agent-team:testbench-dev
with claude-opus-5-5, medium effort, firstParty remains the RTL adapter author;
the successful owner-selected retry resolved the earlier403. Codex retains
orchestration, read-only independent review and report ownership. Remote EDA is
serialized under the main coordinator; no new duplicate worker or campaign runs.
Full mapped replay, SAIF, PT power and semantic acceptance remain pending at this
checkpoint. CGOF power remains UNMEASURED; long backlog drain UNVERIFIED.

At2026-11-07 05:08 Asia/Taipei the1200s simulation limit expired after the
8M-cycle progress marker. Actual exits: payload0, compile0, compile-log-audit0,
sim124, source_check0, shell_exit1. Archive/download exited0 and the full failure
is preserved in remote-pilot/attempt-03-bounded-replay. No complete replay, SAIF
or PT power exists for that attempt. No functional mismatch was reported before
the timeout; this is incomplete verification, not an8M-cycle acceptance.

Only after that process and evidence download completed, a fresh retry
cgof-power-owner-direct-20261106t210852z was launched at05:08:49 Taipei. The
same210204160-byte package and frozen runtime sources are retained. An external
operational runner changes only the observed-insufficient sim budget1200s to
3600s, with outer6400s/transport6650s bounds. Its SHA256 is
b96d09a25e9269355a7c6d489fd1feaa01c0246352105735c4f226736bf76aa0;
the original frozen runner remains8500583676df52ef6077cb272b70670453f93b15c6c206a262cd4ad07a9d4a40.
The executed copy is retained in the evidence archive and its change is explicit
in the bootstrap. No vector/model re-export, preload, cycle skip, stimulus change,
baseline rerun or parallel EDA is used. Exact new backend and command are in
owner-direct-pilot/replay-budget-retry/transport.receipt.json.

inspect_mapped_topology.py observed27784 leaf cells,8998 clock pins and34
literal-pin cells from the exact frozen CGOF1 netlist, exit0. The read-only
FastX inspect_cell_interfaces.py review binds the original cell-model/netlist
hashes, finds no missing input/inout or unknown ports, and records disconnected
QN/carry/comparator/hold outputs as port-direction metadata only. The model and
library source remain on FastX. Its helper exit0 and full command/output are
retained in cell-interface-review.command.txt/cell-interface-review.json. These
reports support later SAIF/annotation review and do not grant power acceptance.

### 2026-11-07 — CGOF1/A/509 gate-level power evidence

The owner-authorized FastX retry completed on backend `fastx4-NN.ews.illinois.edu` as run `cgof-power-owner-direct-20261106t210852z`. The frozen CGOF1/A/509 package, mapped netlist, SAED32 RVT model/DB, profile and vectors were reused without a source or stimulus change. Full64 VCS compile exited `0`; the 10,100,000-cycle replay exited `0` with 100,000 measured cycles, 2,500,000 ns SAIF duration, clock `TC=199999`, and no functional mismatch.

The first remote replay audit stopped before PrimeTime because the checker classified the legal SAIF signal name `TC` as a duplicate activity field. The parser was corrected to distinguish field frames from signal frames, and the regression suite completed `11` discovered tests with `10` passed and `1` existing skip. A power-only PrimeTime continuation then reused the completed replay and SAIF in a new remote report directory; it exited `0`. No simulation or baseline rerun was performed after the parser correction.

Final local semantic audit exited `0`: 39,912 SAIF records, no transient X/Z, 28,458/28,458 nets annotated, 27,750/27,784 leaf cells fully annotated, and 8,998/8,998 register clock pins sourced from the `clk` net with file activity. PrimeTime reported internal `0.001328 W`, switching `0.00001818 W`, leakage `0.002069 W`, total `0.003416 W`; `check_power` reported zero load/ramp range issues. Existing matched baseline rows were reused without rerun: FCFS `0.003356 W`, RR10 `0.002559 W`, Main `0.003466 W`.

This result measures one CGOF1/A/509 case only. The remaining `509–511/A–B` cases, cohort-level claims, long backlog drain, and physical-chip power remain incomplete or unverified. Raw remote evidence, continuation reports, source hashes, commands and receipts are indexed under `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/`; the semantic summary is `power-semantic-review.json`.

### 2026-11-07 — Remaining eleven CGOF captures and directed backlog drain

Owner explicitly authorized finishing the eleven remaining frozen captures and adding long backlog drain. Codex started the existing production exporter for CGOF1/A/510, then added scripts/run_cgof_power_cohort.py to prepare the remaining exact matrix and coordinate one remote VCS/PrimeTime case at a time. Two focused orchestration tests passed; Bash syntax check exited 0. Initial remote preflight on FastX-NN showed no account EDA process and approximately 5.7 GB available home storage. Existing accepted CGOF1/A/509 and FCFS/RR10/Main captures are reused.

The transport uses the existing FastX helper environment; local exports and audits use the project Python environment. Each fresh run preserves source/package/library/profile bindings, commands, native exits, SAIF, annotation and power reports. The existing 3,600-second simulation retry budget is used per case. Expanded vectors are disposable only after the source-before/after check passes; compressed original inputs and reports remain available.

Native Claude Code claude-opus-5-5, requested medium effort, installed rtl-agent-team:testbench-dev, is the sole writer of new directed-drain verification files. Its stream confirms the requested model ID; provider-internal reasoning effort is not exposed. The additive Main/CGOF1/CGOF2 directed tests retain production W parameters and explicitly identify reset/all-High scope. They exercise finite producer/FIFO backlog, cutoff, drain greater than ten cycles, full105/hold/oracle checks and complete conservation. No existing frozen implementation source, historical A3 artifact, confirmation campaign or paper is modified.

Current execution and acceptance are recorded in docs/reviews/fastx-power-cohort-extension-20261107.md and artifacts/implementation/fastx-power-20261107/cohort-extension/execution-index.json. Full cohort and new drain remain incomplete until actual results and independent review are available.

### 2026-11-07 — Directed long-backlog drain accepted; power extension active

Native Claude Code `claude-opus-5-5`, requested medium effort, implemented the additive testbench and runner in `sim/experimental/test_directed_backlog_drain.py`, `scripts/run_directed_backlog_drain.py` and `scripts/test_directed_backlog_drain.py`. No scheduler RTL or frozen power source changed. Run `20261106T230245Z_18888` passed all seven strict verification steps: three Verilator lint steps, nine pytest tests and three one-test cocotb runs. Total: twelve tests, zero failures, errors or skips; all commands exited zero. The source archive and all 51 before/after/current source hashes agree. Codex independently checked raw JUnit, native exit records and the per-configuration result JSON against a separate model replay, then wrote `parent-acceptance.json`, exit zero.

Main, CGOF1 and CGOF2 each started from reset/all-High with N4/D16/full105/W5M. After 512 stalled generation cycles, the cutoff contained producer backlog `[359,229,167,104]` and FIFO occupancy `[16,16,16,16]`. Restoring ready and stopping generation drained 923 descriptors in 923 cycles; final generated/accepted/fired counts were `[375,245,183,120]` per source, with zero outstanding. The held grant remained stable for 511 cycles and fired first on release. Every edge retained native model/full105/hold checks, followed by two quiescent cycles. No classification window closed. This accepts directed long drain only; historical A3, trained-class claims, latency/fairness and paper results are unchanged.

Reproduction: under WSL, `source scripts/wsl_env.sh && PYTHONDONTWRITEBYTECODE=1 timeout 2400 python scripts/run_directed_backlog_drain.py --execute --jobs 2`. Full build/lint/simulation commands, tool versions, JUnit and source archive are under `artifacts/implementation/fastx-power-20261107/directed-drain/20261106T230245Z_18888/`. Parent review command: `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_directed_drain.py`, exit zero.

The existing power coordinator completed the CGOF1/A/510 vector export and serialized audit, then reached actual VCS compile and compile-log-audit exit zero on FastX; gate replay is active. The other ten additional captures remain queued in the same process. The eighteen existing accepted FCFS/RR10/Main rows were assembled with their original metadata, acceptance and exit bindings and matched trace/profile/windows in `cohort-extension/matched-baseline-509-511-AB.json`, exit zero; no baseline rerun or new acceptance campaign occurred. A Cindy continuation bound to this conversation checks every twenty minutes and only wakes the parent for a new completed case or error. Schedule `213559e5-1778-4839-b449-f9b37c1c4284` stops after full acceptance. The power cohort remains INCOMPLETE.

### 2026-11-07 — CGOF1/A/510 matched gate-power accepted

The original coordinator PID 40540 remains active with two local exporters and one serialized remote case. At 07:54 Asia/Taipei, CGOF1/B/509 had passed compile and reached 9,000,000 checked warmup cycles; coordinator stderr was empty and its exit file was absent. No accepted capture or directed drain was rerun. A read-only FastX helper invocation reached FastX-NN; that backend's process list does not describe the existing run on FastX-NN.

Codex independently accepted CGOF1/A/510 in `cohort-extension/cgof1-A-s510/parent-acceptance.json`. Actual compile, replay, SAIF/PrimeTime, tool-log audits, source-before/after, shell and local-audit exits are zero. The VCS version probe's exit 1 remains separate. Source binding checks covered 39 current source files, the archive, all 54 remote before/after files, frozen mapping and library/model/profile hashes. All 28,458 nets have file activity; 27,750/27,784 leaf cells are fully annotated, with the 34 exceptions explained by literal D/SETB pins. All 8,998 FF clock pins resolve through hierarchy to clk and file activity at 0.0799996/ns. There are no transient X/Z records; twenty constant-X records correspond to omitted arithmetic/comparator outputs. The sole PTE-003 warning covers 68 propagated constant arcs; check_power reports no range issues.

CGOF1/A/510 powers are internal 0.001328 W, switching 0.00001820 W, leakage 0.002070 W, total 0.003416 W. Existing matched seed-510/A totals are FCFS 0.003356 W, RR10 0.002560 W and Main 0.003467 W: CGOF1 deltas +1.79%, +33.44% and -1.47%. Trace/profile/PVT/window bindings and baseline receipt hashes agree. CGOF1/RR10/Main each accepted and fired [97654,809,772,765] during measurement; FCFS accepted [97655,809,772,765], fired [97655,809,771,765], and retained one additional source-2 descriptor at the end. The acceptance preserves these service differences.

Parent-review command: `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof1_A510.py`, exit 0. Native remote command, stage exits, power components, hashes and warnings are in the acceptance receipt and original reports. The accepted scope is one pre-layout zero-delay/no-SDF averaged gate estimate; the full twelve-case cohort remains INCOMPLETE, and paper/physical-chip claims are unchanged. Directed long backlog drain retains its previously accepted twelve-test result.

### 2026-11-07 — B/509 and B/510 accepted; interrupted coordinator recovered

At 08:17–08:28 Asia/Taipei, original coordinator PID 40540 was absent with no native exit receipt, empty stderr and stdout last changed at 08:15:57. The machine had not rebooted. Shared remote logs showed B/510 progressing from eight to nine million checked warmup cycles on its original FastX-NN run. The alias preflight reached another backend, so that backend's process list was not treated as proof of original run failure. Cause of coordinator disappearance remains unproven. No unrelated process was stopped.

Codex CLI independently accepted CGOF1/B/509 and CGOF1/B/510 with `accept_cgof1_power_case.py cgof1-B-s509` and `... cgof1-B-s510`, both exit 0. Their parent receipts retain all stage/source/package/library/profile/report bindings, original commands, matched seed/arm/window, actual admissions and outstanding work, annotation, FF clocks, unknown-state review, constant-arc warnings and all power components. B/509 internal/switching/leakage/total are 1.328/0.01794/2.069/3.415 mW; B/510 are 1.328/0.01794/2.070/3.416 mW. Against their respective FCFS/RR10/Main baselines the total deltas are +1.7884/+33.4506/-1.4430 percent and +1.7878/+33.4375/-1.4426 percent. Existing baseline captures were not rerun.

After verifying absence of every task coordinator/exporter, the parent preserved the original index and resumed the same batch with ignored operational script `cohort-remaining/resume_cohort.py`, exclusive Windows file lock and a detached launcher. This script imports the existing orchestration helpers; it changes no frozen source or stimulus. The first two launcher attempts exited 1; the second recorded the actual missing-python PATH error. Using the already installed absolute Python executable repaired launch; no tool install or global setting change occurred. All attempt receipts are retained. Three focused recovery checks passed, exit 0: reuse complete exports and reject modified hashes, recover original remote completion without relaunch, and refuse to relaunch after an unproven completion timeout.

Recovered coordinator PID 41940 collected B/510 only after its original remote exit and complete archive existed, checked the remote/local archive hash, then ran local replay/SAIF/PT audit and parent review, all exit 0. The original B/510 capture was not replayed. Only then did it launch the missing CGOF1/A/511 on observed backend FastX-NN, run `cgof-power-cgof1-a-s511-20261107t002827z`; compile and compile-log-audit exited 0 and replay is active. Fully completed exports are reused; interrupted CGOF2 exports remain intact and only missing cases receive fresh export-recovery subdirectories. Local concurrency remains two export tasks and remote concurrency one bounded single-core case. New remote wrappers detach from the SSH transport while preserving original stage limits and completion evidence.

The active logs are now `recovery.stdout.txt`, `recovery.stderr.txt` and `recovery.exit.txt`; original coordinator logs and absent original exit are preserved. Continuation and the scheduler precheck use the active logs and detect coordinator disappearance so a stale local index cannot permanently silence recovery. The current accepted total is four of twelve including reused A/509; eight power cases remain incomplete. Directed drain retains its original twelve-test acceptance without rerun. No final cohort artifact-index/SHA completion, paper upgrade or silicon-power claim is made. Detailed records and new receipt links are in `docs/reviews/fastx-power-cohort-extension-20261107.md`.

### 2026-11-07 — CGOF1/A/511 accepted; original B/511 replay active

At 09:12–09:14 Asia/Taipei, the single recovery coordinator PID 41940 remained active with empty stderr and no exit receipt. Codex CLI performed the read-only parent review directly; no new agent, coordinator, campaign, accepted capture replay or drain rerun was started. CGOF1/A/511 completed on FastX-NN as `cgof-power-cgof1-a-s511-20261107t002827z`; all execution/audit stages and parent review exited zero, with informational VCS version exit 1 preserved. The command was `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof1_power_case.py cgof1-A-s511`.

The new parent receipt verifies 39 current/archive sources, 54 before/after remote hashes, frozen mapping/library/model/profile, replay/SAIF/report bindings, all 8,998 FF clocks, full 28,458-net annotation, the same 34 literal-pin leaf exceptions and twenty disconnected constant-X outputs. No transient X/Z or check_power range issue was observed. The sole PTE-003 warning again covers 68 propagated constant arcs. The local package and original bootstrap payload checksum, plus evidence archive SHA256, were independently checked. Powers are internal 1.328, switching 0.01822, leakage 2.070 and total 3.416 mW. Matched seed-511/A baseline totals are FCFS 3.356, RR10 2.560 and Main 3.467 mW, giving +1.7878%, +33.4375% and -1.4710% respectively. All four policies accepted/fired [97595,777,815,813], retaining [15,0,0,0] outstanding across the measurement window.

The same coordinator has advanced to B/511 run `cgof-power-cgof1-b-s511-20261107t005455z`; original shared logs showed seven million warmup cycles at 09:13, compile/audit exit zero. The read-only helper invocation reached FastX-NN, whose process list does not describe the original FastX-NN backend. The three missing/interrupted CGOF2 exports have finished their model/serialized-pin audits with native exit zero; that preparation does not constitute gate-power acceptance. Current power acceptance is five of twelve including the reused A/509. B/511 and all six CGOF2 captures still require completion and parent review. Directed drain retains its earlier twelve-test acceptance. The follow-up receipt, hashes, command/SSH logs and active-state marker are preserved under `cohort-remaining/followup-20261107T0112Z-*`; the overall cohort remains INCOMPLETE with no paper or physical-chip result upgrade.

### 2026-11-07 — CGOF1/B/511 accepted; original CGOF2/A/509 replay active

During the 09:37 Asia/Taipei continuation, Codex CLI independently accepted the original B/511 capture on FastX-NN with `accept_cgof1_power_case.py cgof1-B-s511`, exit 0. Compile, replay, SAIF/PrimeTime, log audits, source consistency, shell and local audit exits are zero; informational VCS version exit 1 is retained. The parent receipt binds 39 current/archive sources, 54 remote before/after files, the frozen mapping/library/model/profile, SAIF and reports. Net annotation is 28,458/28,458, leaf annotation 27,750/27,784, and all 8,998 FF clocks have clk/file activity. The 34 literal-pin exceptions, twenty disconnected constant-X outputs and sole 68-constant-arc PTE-003 warning are explained against the mapped topology; there is no transient X/Z or check_power range issue.

Internal/switching/leakage/total are 1.328/0.01793/2.071/3.417 mW. Matched seed-511/B baseline totals are FCFS 3.357, RR10 2.561 and Main 3.467 mW, giving CGOF1 total deltas +1.7873%, +33.4244% and -1.4422%. All four policies accepted and fired [100000,800,800,800], retaining [15,0,0,0] outstanding across the original 102,400-cycle measurement window after 10,101,024 warmup cycles. Full commands, versions, hashes, power components and baseline bindings remain in `cohort-extension/cgof1-B-s511/parent-acceptance.json`.

The single coordinator PID 41940 remains active with empty stderr and no native exit receipt, now running original CGOF2/A/509 `cgof-power-cgof2-a-s509-20261107t012153z`. Read-only FastX helper exit 0 observed five million checked warmup cycles in shared logs and compile/audit exit 0. Its alias backend was FastX-NN, so its local process list does not establish original FastX-NN job status. No coordinator, agent or campaign was added; accepted captures and directed drain were not rerun, and no frozen source changed. Operational recorder `record_followup_20261107T0137Z.py` exited 0, additionally checking all five extension packages, bootstrap payload checks and evidence archives, then preserving a continuation snapshot, review receipt, follow-up hashes and the precheck state marker. All six CGOF1 captures are now accepted, six of twelve total; six CGOF2 captures still require gate-power completion and topology-specific parent review. Directed drain retains its earlier twelve-test acceptance. The overall cohort remains INCOMPLETE, and no final global artifact closure, paper update or physical-chip claim is made.

### 2026-11-07 — first CGOF2 capture A/509 accepted with structural unknown-state review

At 10:00–10:05 Asia/Taipei, Codex CLI independently reviewed the original CGOF2/A/509 run `cgof-power-cgof2-a-s509-20261107t012153z` on FastX-NN. Command `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-A-s509` exited 0. Compile, replay, SAIF/PrimeTime, all log audits, source-before/after, shell and local audit exits are zero; informational VCS version exit 1 remains separate. Current/archive source checks cover 39 files and 54 remote before/after bindings, CGOF2 HIGH_WEIGHT=2 mapped netlist/SDC, library/model/profile, package/payload, compressed vectors, SAIF and evidence/report hashes. The reviewer resolves preparation inputs using the index export_directory, preserving canonical remote evidence and parent receipts. Frozen sources and capture inputs are unchanged.

CGOF2 annotation is 30,022/30,022 nets, 29,221/29,255 leaf cells and 9,014 clk/file FF clocks. The 34 literal-pin leaf exceptions and sole PTE-003 for 68 propagated constant arcs are accounted for; check_power reports no range issue. All 42,138 SAIF records were audited with no transient X/Z. Unlike CGOF1, CGOF2 has 56 constant-X records. A scoped frozen-netlist review classifies every record: 24 omitted arithmetic/comparator outputs, 16 trimmed unused arithmetic output bits, and sixteen unconnected alias wires with no local consumers. The four multiplier PRODUCT[2:0] and FS_1/SUM[0] bits are absent from internal logic and terminate in parent SYNOPSYS_UNCONNECTED wires. No live output or consumed gate-input X was waived. The parent receipt retains all 56 structural explanations.

New ignored operational checker review_cgof2_unknowns.py initially failed its self-check, exit 1, because scalar-output parsing did not handle a shared comparator output declaration. After correcting declaration parsing, check_cgof2_unknown_review.py attempt02 exited 0: original evidence passed and all three unsafe in-memory mutations were rejected (live X path, restored trimmed SUM[0], and a new consumer of an unconnected alias). The original failed logs and exit remain intact. This changes only parent-review tooling; no RTL/TB repair, delegation or replay occurred. The successful parent command then wrote a new receipt with reviewer source hashes.

CGOF2/A/509 internal/switching/leakage/total are 1.331/0.01895/2.112/3.462 mW. Matched FCFS/RR10/Main totals are 3.356/2.559/3.466 mW, giving +3.1585%, +35.2872% and -0.1154%. CGOF2 accepted and fired [97716,788,745,751], retaining [15,0,0,0] outstanding across the 100,000-cycle window after ten million warmup cycles. Baseline admissions/fires and boundary-work differences are preserved; matched traffic is not claimed to be identical service. Differences describe reported pre-layout estimates, without statistical or silicon claims.

PID 41940 remains the sole active coordinator with empty stderr and no completion exit. It has advanced to CGOF2/B/509 `cgof-power-cgof2-b-s509-20261107t015525z`; read-only helper exit 0 observed two million checked warmup cycles and compile/audit exit 0 through shared logs. The alias landed on FastX-NN, whose process list does not describe the original FastX-NN execution. Recorder record_followup_20261107T0200Z.py exited 0, verified all six completed extension packages/payload checks/evidence archives, and updated continuation, review receipt, follow-up hashes and the exact precheck state marker. Accepted power is now seven of twelve; five CGOF2 captures remain incomplete. The existing twelve-test directed-drain acceptance is retained without rerun. Final global artifact-index/SHA256SUMS closure awaits all twelve acceptances; the cohort remains INCOMPLETE.

### 2026-11-07 — CGOF2/B/509 accepted; original A/510 replay active

During the 10:47 Asia/Taipei continuation, Codex CLI independently reviewed CGOF2/B/509 and accepted it at 10:50. Command `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-B-s509` exited 0. The original run `cgof-power-cgof2-b-s509-20261107t015525z` completed on FastX-NN. Compile, replay, SAIF/PrimeTime, all log audits, source checks, shell, local audit and parent exits are zero; informational VCS version exit 1 is retained. Source revision a3f4d8b1865c9af24eb86776274cc8c98428adc3, 39 current/archive sources, 54 remote before/after bindings, frozen HIGH_WEIGHT=2 mapping/library/model/profile, package/payload, vectors, SAIF and report/evidence hashes match. The existing auditor uses the index export_directory; no frozen source, RTL or TB was changed, and no new review agent was used.

This B window retains 10,101,024 warmup and 102,400 measured cycles, duration 2,560,000 ns. Annotation is 30,022/30,022 nets and 29,221/29,255 leaf cells, with all 9,014 clk/file FF clocks. The 34 literal D/SETB exceptions and 56 structurally unused constant-X records (24 omitted outputs, sixteen trimmed output bits, sixteen unconnected aliases) were reviewed against the frozen mapped netlist; no transient X/Z was observed. The sole PTE-003 covers 68 propagated constant arcs, and check_power reports no range issue. Internal/switching/leakage/total are 1.331/0.01858/2.112/3.461 mW. Matched seed-509/B FCFS/RR10/Main totals are 3.355/2.559/3.465 mW, giving +3.1595%, +35.2481%, -0.1154%. All four components and matching conditions are retained in the parent receipt; these are pre-layout zero-delay/no-SDF estimates, not physical-chip measurements or statistical comparisons.

CGOF2 accepted/fired [100000,800,800,800], retaining [15,0,0,0] outstanding. FCFS accepted [100008,800,800,800], fired [100007,793,800,800], and ended [16,7,0,0]; RR10/Main accepted [100002,800,800,800], fired [100001,799,800,800], and ended [16,1,0,0]. Baselines all began [15,0,0,0] outstanding; conservation and original trace/profile/PVT/25 ns/window bindings were checked, without claiming identical service from matched traffic. Baselines and directed drain were not rerun.

The sole coordinator PID 41940 remains alive, stderr empty and active exit absent. It advanced to original A/510 `cgof-power-cgof2-a-s510-20261107t022929z`; read-only FastX skill/helper exit 0 observed six million checked warmup cycles, compile/audit exit zero and remote exit pending. The alias reached FastX-NN while the original run hostname receipt remains FastX-NN; its process list is not used as evidence about the original backend. Operational recorder record_followup_20261107T0247Z.py binds all seven completed extension packages/payload checks/evidence archives, updates continuation, the follow-up review and SHA256SUMS, and writes the same state structure used by precheck. Eight of twelve captures are now accepted including the reused pilot; four CGOF2 captures remain incomplete. The existing twelve-test long-drain acceptance is preserved. Final global artifact closure and schedule shutdown await full parent acceptance; overall INCOMPLETE.

The recorder's first attempt exited 1 before any continuation/state writes: Windows PowerShell redirected SSH stdout as UTF-16, while the reader assumed UTF-8 and raised UnicodeDecodeError. After adding BOM-based UTF-16/UTF-8 decoding in this ignored operational recorder only, attempt02 exited 0, recording accepted_total=8, RUNNING, stderr_bytes=0 and coordinator_exit=null. Both attempts retain separate stdout/stderr/exit evidence; no capture, RTL or TB rerun was needed.

### 2026-11-07 — CGOF2/A/510 accepted; original B/510 replay active

At the 11:14 Asia/Taipei continuation, Codex CLI independently accepted the original A/510 run `cgof-power-cgof2-a-s510-20261107t022929z` on FastX-NN. Command `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_power_case.py cgof2-A-s510` exited 0. Compile, replay, SAIF/PrimeTime, log audits, source check, shell, local audit and parent exits are zero; informational VCS version exit 1 remains separate. Revision a3f4d8b1865c9af24eb86776274cc8c98428adc3, 39 current/archive sources, 54 remote before/after bindings, package/payload, frozen CGOF2 mapping/library/model/profile, vectors, SAIF and reports/evidence hashes match. The reviewer uses the index export_directory. No frozen source, RTL or TB was changed, and no agent, coordinator or campaign was added.

The A window is 10,000,000 warmup plus 100,000 measured cycles, SAIF duration 2,500,000 ns. Annotation is 30,022/30,022 nets and 29,221/29,255 leaf cells, with all 9,014 FF clocks on clk/file activity. All 34 literal D/SETB exceptions and 56 structurally unused constant-X records were accounted for (24 omitted outputs, sixteen trimmed output bits, sixteen unconnected aliases), without transient X/Z. The sole PTE-003 covers 68 propagated constant arcs; check_power reports no load/ramp range issue. Internal/switching/leakage/total are 1.331/0.01897/2.112/3.462 mW. Matched seed-510/A FCFS/RR10/Main totals are 3.356/2.560/3.467 mW, giving +3.1585%, +35.2344% and -0.1442%. These remain descriptive pre-layout zero-delay/no-SDF averaged gate estimates.

CGOF2, RR10 and Main accepted/fired [97654,809,772,765], retaining [15,0,0,0] outstanding. FCFS accepted [97655,809,772,765], fired [97655,809,771,765], and outstanding changed from [15,0,0,0] to [15,0,1,0]. Matched trace/profile/PVT/25 ns/window and conservation were checked while retaining actual admission/service differences. The parent receipt contains all components, hashes, commands and matched bindings; accepted captures, baselines and directed drain were not rerun.

PID 41940 remains the sole active coordinator, with empty stderr and no completion exit. Original B/510 `cgof-power-cgof2-b-s510-20261107t030331z` is active using index export_directory `export-recovery-cgof2-B-s510-20261107T002822Z`; the original partial is preserved. Read-only FastX skill/helper exit 0 observed three million checked warmup cycles, compile/audit exit 0 and remote exit pending through shared logs. The alias reached FastX-NN, while the original run hostname receipt is FastX-NN; alias processes do not establish original backend activity. Recorder record_followup_20261107T0314Z.py exited 0, additionally verifying all eight completed extension packages/payload checks/evidence archives and writing continuation, snapshot, follow-up review/SHA256SUMS and exact precheck state. Accepted captures are now nine of twelve including the reused pilot; B/510, A/511 and B/511 remain incomplete. Existing long-drain acceptance remains twelve tests, three configurations each 923 cycles and zero outstanding. Global artifact closure and existing schedule shutdown await all twelve parent acceptances; overall INCOMPLETE, without paper or silicon claim upgrades.

### 2026-11-07 — recovery export B/510 accepted; original A/511 replay active

During the 11:57 Asia/Taipei continuation, Codex CLI independently reviewed original B/510 `cgof-power-cgof2-b-s510-20261107t030331z`, completing acceptance at 11:58. The original reviewer first exited 1 with FileNotFoundError before creating a receipt: it assumed cgof2-B-s510.tar, but coordinator package(directory) names the preserved package from export_directory. The actual package is export-recovery-cgof2-B-s510-20261107T002822Z.tar. Initial logs/exit and the old reviewer remain unchanged. A separately saved ignored operational reviewer accept_cgof2_export_package.py resolves that basename from the index and additionally validates package_bytes. Command `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-B-s510` exited 0, recorded in accept-cgof2-B510.attempt02.*.txt. The original 212,418,560-byte package SHA256 is 2466efc23b241b98426acc6ecdc27812bb446e53f8726ffb2ef98b1a06473192, matching the index, remote command and original bootstrap payload check. No package or capture was regenerated. Use this reviewer for the remaining recovery A/511 and canonical B/511 exports.

The original backend is FastX-NN. Compile, replay, SAIF/PrimeTime, all log audits, source consistency, shell, local audit and parent exits are zero; informational VCS version exit 1 is preserved separately. Revision a3f4d8b1865c9af24eb86776274cc8c98428adc3, 39 current/archive sources, 54 remote before/after bindings, frozen mapping/library/model/profile, vectors, SAIF/reports/evidence hashes match. The index recovery export supplies metadata/audit/source-freeze/vectors while canonical directories retain remote evidence and parent receipts. B retains 10,101,024 warmup and 102,400 measured cycles, duration 2,560,000 ns. All 30,022 nets, 29,221/29,255 leaf cells and 9,014 clk/file FF clocks were checked. The 34 literal-pin exceptions, 56 structurally unused constant-X records and sole PTE-003 for 68 propagated constant arcs are explained; no transient X/Z or check_power range issue was observed.

Internal/switching/leakage/total are 1.331/0.01859/2.113/3.462 mW. Matched seed-510/B FCFS/RR10/Main totals are 3.356/2.560/3.466 mW, giving +3.1585%, +35.2344% and -0.1154%. All four policies accepted/fired [100000,800,800,800] and retained [15,0,0,0] outstanding; trace/profile/PVT/25 ns/window bindings and conservation match. These are descriptive pre-layout zero-delay/no-SDF averaged gate estimates, without physical-chip or paper claim upgrades.

The sole coordinator PID 41940 remains alive, stderr empty and completion exit absent, advancing to A/511 cgof-power-cgof2-a-s511-20261107t033809z using the preserved recovery export. Read-only FastX skill/helper exit 0 observed five million checked warmup cycles, compile/audit exit zero and remote exit pending. Alias backend FastX-NN differs from original run hostname FastX-NN; its process list is not evidence about original backend activity. Recorder record_followup_20261107T0357Z.py exited 0, verified all nine completed extension packages by basename/bytes/SHA256 plus payload checks/evidence archives, and updated continuation, snapshot, review/SHA256SUMS, the remaining reviewer/package rule and exact precheck state. Accepted power is ten of twelve including the reused pilot; A/511 and B/511 remain incomplete. No frozen source changed, no new agent/coordinator/campaign was started, and no accepted capture, baseline or directed drain was rerun. The existing twelve-test directed drain remains accepted with 923 cycles and zero outstanding in each configuration. Overall INCOMPLETE; final global artifact closure and schedule shutdown await twelve parent acceptances.

### 2026-11-07 — recovery export A/511 accepted; final original B/511 replay active

At 12:21 Asia/Taipei, Codex CLI independently accepted original A/511 cgof-power-cgof2-a-s511-20261107t033809z on FastX-NN. Command `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-A-s511` exited 0. Preparation input comes from index export_directory export-recovery-cgof2-A-s511-20261107T002822Z, with canonical remote evidence/parent receipt and preserved original partial. The same original package basename, bytes and SHA256 d4f38678dea0a415800a1ed941fedd1e5543c89fe0f8b6e9e217e7948063ce8b match index, remote command and bootstrap payload check; no package or capture was regenerated.

Compile, replay, SAIF/PrimeTime, all log audits, source consistency, shell, local audit and parent exits are zero; informational VCS version exit 1 is retained separately. Revision a3f4d8b1865c9af24eb86776274cc8c98428adc3, 39 current/archive sources, 54 remote before/after bindings, frozen mapping/library/model/profile, vectors and SAIF/reports/evidence hashes match. A retains ten million warmup and 100,000 measured cycles, duration 2,500,000 ns. Annotation is 30,022/30,022 nets and 29,221/29,255 leaf cells; all 9,014 FF clocks have clk/file activity. The 34 literal-pin exceptions, 56 structurally unused constant-X records and sole PTE-003 for 68 propagated constant arcs are accounted for. No transient X/Z or check_power range issue was observed.

Internal/switching/leakage/total are 1.331/0.01898/2.112/3.462 mW. Matched seed-511/A FCFS/RR10/Main totals are 3.356/2.560/3.467 mW, giving +3.1585%, +35.2344% and -0.1442%. All four policies accepted/fired [97595,777,815,813], retaining [15,0,0,0] outstanding; original trace/profile/PVT/25 ns/window bindings and conservation match. Full components, commands, exits and hashes remain in the canonical parent receipt. Differences remain descriptive pre-layout zero-delay/no-SDF estimates at tool report precision, without statistical, paper or silicon upgrades.

The sole coordinator PID 41940 remains alive with empty stderr and absent completion exit, running final B/511 cgof-power-cgof2-b-s511-20261107t041318z. Read-only FastX skill/helper exit 0 observed two million checked warmup cycles, compile/audit zero and remote exit pending in shared logs. The alias reached FastX-NN; original run hostname remains FastX-NN, so alias processes are not evidence about original backend activity. Recorder record_followup_20261107T0421Z.py exited 0, verified all ten completed extension package bytes/hashes, original bootstrap payload checks and evidence archives, then updated continuation, snapshot, review/SHA256SUMS and exact precheck state. Eleven of twelve captures are accepted including the reused pilot; only B/511 awaits completion and parent review. No agent/coordinator/campaign was added, no frozen source changed and no accepted capture, baseline or drain was rerun. The twelve-test directed drain retains 923 cycles and zero outstanding in each configuration. Overall remains INCOMPLETE; final global artifact closure and shutdown of the existing continuation schedule await the last original capture.

### 2026-11-07 13:13 Asia/Taipei — authorized FastX cohort and directed drain accepted

Final status: ACCEPTED_AUTHORIZED_SCOPE. All twelve CGOF power captures (HIGH_WEIGHT=1/2, seeds 509–511, separate A/B arms), eighteen reused accepted baseline captures and the directed long backlog drain are accepted. Final original CGOF2/B/511 completed on FastX-NN without relaunch; `.venv-fastx-power/Scripts/python.exe -B .setup-logs/implementation/fastx-power-20261107/cohort-remaining/accept_cgof2_export_package.py cgof2-B-s511` exited 0. Compile, sim/replay, SAIF/PT, source/log/shell/local audits are 0, retaining informational VCS version exit 1. Internal/switching/leakage/total are 1.331/0.01858/2.114/3.463 mW. Package SHA256 is 20083ed97ad011c2d57e715aba0702841dc59f6e2381a5589b23e9466fa01dfa; original remote evidence hash is 46dc74b8226ec82d54dce509484a61279bb8efb24f6964a3b702dd118b83eb0a. Recovery coordinator exit is genuinely 0 with empty stderr; original PID 40540 exit remains unknown.

The ignored operational finalizer `cohort-remaining/finalize_cohort.py` exited 0 and checked 435 file bindings: all eleven extension package bytes/hashes, evidence/SAIF/reports, current/archive frozen sources, reused baseline receipts, and directed-drain sources/JUnit/results. It also performed final parent structural/hash review of the existing CGOF1/A/509 capture, preserving original replay-audit/shell exit 1, corrected local checker exit 0 and PT-only continuation exit 0. The retained preparation NOT_RUN and observation-time INCOMPLETE/semantic-review-required records are historical; final-acceptance.json supplies current aggregate scope. No accepted capture, baseline, drain, frozen RTL/TB/exporter/checker/STA source or failed partial directory was regenerated or changed. A console-only UTF-8 read initially encountered a UTF-16 audit; the BOM-aware reader used for final acceptance handled the original bytes without modifying evidence.

Matched total power in mW (FCFS/RR10/Main/CGOF1/CGOF2): 509/A 3.356/2.559/3.466/3.416/3.462; 509/B 3.355/2.559/3.465/3.415/3.461; 510/A 3.356/2.560/3.467/3.416/3.462; 510/B 3.356/2.560/3.466/3.416/3.462; 511/A 3.356/2.560/3.467/3.416/3.462; 511/B 3.357/2.561/3.467/3.417/3.463. Twelve pairwise comparisons retain seed/arm, exact exogenous trace, profile/library/PVT, 25 ns and original windows. Actual admissions/fires/boundary outstanding remain policy-specific and conserved. CGOF1 vs Main ranges from -1.4710% to -1.4422%; CGOF2 from -0.1442% to -0.1154%, descriptive at report precision, without pooled statistics or significance claims.

All net activity is annotated (CGOF1 28,458; CGOF2 30,022); leaf annotation is 27,750/27,784 and 29,221/29,255. The 34 literal D/SETB exceptions are explained, with 8,998/9,014 clk/file FF clocks. No transient X/Z; 20/56 constant-X records are structurally unused. Sole PTE-003 covers 68 propagated constant arcs; check_power has no load/ramp range issues. Directed drain reuses parent-acceptance.json under 20261106T230245Z_18888: twelve tests, no failure/error/skip, Main/CGOF1/CGOF2 each 923 drained cycles/descriptors, outstanding zero. Cutoff producer backlog 859 plus FIFO 64; reset/all-High seed7301, no window close.

Current artifact-index.json v3 links final-acceptance.json, the full thirty-row four-component matched-comparison.json/MATCHED_COMPARISON.md, source freeze, twelve case bindings, directed-drain acceptance and the old immutable pre-cohort-closure index snapshot. SHA256SUMS seals current evidence and documentation. The existing follow-up schedule 213559e5-1778-4839-b449-f9b37c1c4284 is paused at closure, preserving its history; no other schedule or process is changed. Main route remains Codex CLI group/gpt-6.1-sol-2/high (live runtime checked); existing RTL/TB and directed drain provenance remains Claude Code claude-opus-5-5/requested medium/rtl-agent-team:testbench-dev. No new delegation. Full commands, exits and source/package/library/model/profile hashes are available through the index and per-case receipts.

This closes the authorized measurement/evidence task only. Power remains pre-layout zero-delay/no-SDF averaged gate estimation without APR/SPEF/physical clock tree/glitch/silicon. Historical baseline vector bytes were not rehashed. Directed all-High drain does not validate trained-class evolution, general fairness or system latency. No manuscript, hypothesis integration, physical-chip result or unrelated expensive campaign is promoted.

### 2026-11-07 — CGOF 功耗與本次實驗中文結果紀錄

依主人要求，新增 [CGOF_POWER_RESULTS_2026-11-07.md](CGOF_POWER_RESULTS_2026-11-07.md)，集中保存十二組 CGOF internal/switching/leakage/total、六組 seed/arm 的五政策 matched total、各 baseline 的配對差異範圍、activity/FF clock/unknown-state/warning 驗收、保留的失敗歷史，以及定向長 backlog drain 的實際結果。這是既有完成實驗的文件整理；未重跑 accepted captures、十八組 baseline 或 drain，未新增代理或遠端 EDA 工作。

文件整理前於 2026-11-07 15:35（Asia/Taipei）執行 ignored operational checker：node .setup-logs/implementation/fastx-power-20261107/result-record/audit_record.mjs，exit 0；重新只讀核對 448 項 final-receipt bindings 與 448 項現有 SHA256SUMS entries，零差異。最終實驗狀態維持 ACCEPTED_AUTHORIZED_SCOPE，十二組功耗與十二個 drain tests 通過。CGOF1 total 3.415–3.417 mW，配對 Main 約低 1.44–1.47%；CGOF2 total 3.461–3.463 mW，配對 Main 約低 0.12–0.14%，兩者均高於 FCFS/RR10。配對範圍僅作描述，沒有 pooled mean、統計顯著性或晶片結論。

Main/CGOF1/CGOF2 的獨立 drain 皆從 859 producer + 64 FIFO backlog 排空，923 cycles、generated=accepted=fired=923、outstanding=0；工程 seed 7301、reset/all-High、無 window close，不擴張至 trained-class、多視窗適應或一般公平性。本頁與新增摘要沿用原 frozen sources、library/PVT/profile/window 與 Claude RTL/TB provenance；本次未重新證實新的模型路由。文件整理前 artifact-index/SHA256SUMS/開發報告另存 pre-result-record-20261107T073501Z snapshot，原 final-acceptance 及所有 capture 證據不變；目前索引與校驗清單另綁定新增摘要及更新後開發報告。


### 2026-11-11 — v5 academic-humanizer language revision

At the owner's request, the current Codex parent directly applied the already-loaded academic-humanizer v0.3.3 rules to the latest accepted v5 report. Original body/driver/PDF hashes matched report-v5-acceptance-20261108.json (internal date 2026-11-09). No extra native CLI or SKILL.md shell read, delegate, experiment, EDA invocation or scientific-status change was introduced.

The edit makes 69 local changes across 43 paragraphs, improving sentence structure, reference clarity and applicability. The ordered 826 numeric literals, 123 inline math spans, three display-math environments, 17 body citation commands, 56 labels/references, 12 float blocks, section/command order and blank-line positions remain identical. Numeric-token counts include identifiers and are not experimental-unit counts. Original driver/bibliography, generated tables/figures, historical releases and accepted v5 PDF remain unchanged. Model/RTL, exploratory/confirmation, power-capture and negative-result qualifications are retained.

Two sequential PDFLaTeX passes exited 0, producing output/pdf/cxl-scheduler-humanized-20261111.pdf (15 pages). Final log has zero undefined references, overfull boxes or rerun requests; underfull hbox spacing warnings remain. Host inspect_pdf read all 15 Letter pages with verdict ok and zero blank pages. Parent reviewed all-page thumbnails and the full results/conclusion page. git diff --check passed. Original title-page/bibliography dates remain; the editorial date is recorded separately.

Deliverable, examples, full change log, preservation checks, PDF inspection and release hashes: docs/final-report/humanized-20261111/. Original snapshots, audit/patch and build logs: .setup-logs/academic-humanizer-20261111/. Acceptance is editorial/content-preservation/PDF acceptance only; no experiment evidence was re-run or upgraded.
