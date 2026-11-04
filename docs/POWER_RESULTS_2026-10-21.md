# Activity-annotated pre-layout power —2026-10-21

本頁保留原seed509九組dataset。後續[Formality等價驗證](FORMAL_EQUIVALENCE_2026-10-21.md)與補充測試
進度見[STATUS](STATUS.md)；本頁下方「未執行」範圍描述原批次，不代表後續工作狀態。原數據未改寫。

狀態：**九組 gate replay／PrimeTime 命令實際完成，採納為有條件的 cold-reset pre-layout 功耗估計。** 共900,000cycles逐cycle比對獨立模型。六組FCFS/RR的check_power仍有constant-context table-range警告，不能稱clean power signoff。Main三組default check_power成功；所有組都受短視窗、zero-delay和無實體設計限制。

## 方法與來源

Frozen Spec v1.0 `1af80967`；power tooling/export source `c0658fbad1ade809821809306adb4b62e1bff235`（乾淨）；重用原primary-v2 mapped source `759f86b24f13ed5984c19034eeeea2ca43b0e971` 的netlist及SDC，沒有重新合成。原[area/STA資料](PPA_RESULTS_2026-10-21.md)與frozen profile不改寫，profile power.status=NOT_RUN是當時資料狀態；本次為獨立[JSON資料](ppa/power-20261021.json)。完整流程見[POWER_METHOD](POWER_METHOD.md)。

FastX Synopsys VCS/PrimeTime W-2024.09，實際取得PrimePower license。原SAED32 RVT TT0.78V25C DB、ForQA/top WLM、相同25ns clock與既有I/O constraints；原DB及Verilog cell model僅在FastX讀取，未下載／修改。九組compile/sim/PT/wrapper皆exit0，最後remote hash check成功。

每組使用seed509、100000cycles、同N相同intended traffic與sink-ready；三個同步resetedges在活動窗外，無drain/preload/warmup。量測2,500,000ns/2.5ms；起點的reset解除轉換包含在活動中，並非排除全部reset相關切換。有效輸出以四態逐cycle核對source/full105與ready/valid，X/Z失敗；outstanding在cutoff保留。此trace三政策的aggregate acceptance/fire totals相同，但RR的per-source populations與FCFS/Main不同，不能把intended traffic相同當作實際接受序列相同。JSON分別保留每source counts。

**Main在100000cycles內沒有跨W=5000000分類邊界，仍全High。** 本批不能支持trained-state power、分類切換功耗或公平性結論；Algorithm-2 power未執行。

## 完整 switch 功耗

下表由PT報告的W乘1000轉為mW；報告原始有效位數保留，四捨五入導致分量和可能略異。Internal包含FF clock-pin internal power，ideal clock network未做CTS，不代表真實clock-tree功耗。

| N | Policy | Internal mW | Switching mW | Leakage mW | Total mW | Range ramps/loads |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | fcfs | 1.307 | 0.01773 | 2.073 | 3.397 | 2/1 |
| 4 | rr | 0.9979 | 0.01136 | 1.591 | 2.600 | 2/1 |
| 4 | fai-main | 1.333 | 0.01964 | 2.147 | 3.500 | 0/0 |
| 8 | fcfs | 2.585 | 0.02185 | 4.121 | 6.728 | 2/1 |
| 8 | rr | 1.980 | 0.01251 | 3.183 | 5.175 | 2/1 |
| 8 | fai-main | 2.626 | 0.02418 | 4.274 | 6.924 | 0/0 |
| 16 | fcfs | 5.141 | 0.02587 | 8.236 | 13.4 | 2/1 |
| 16 | rr | 3.941 | 0.01276 | 6.364 | 10.3 | 2/1 |
| 16 | fai-main | 5.211 | 0.02838 | 8.521 | 13.8 | 0/0 |

總功耗包括共同FIFO／必要metadata／hold／policy；policy subtree原始power row保留在JSON，不能把全部差異叫純selector成本。只有單一corner／seed／mapping，無誤差條件或統計顯著性主張；不從這批值推算實際系統節能。

## 標註與警告審查

| N | Policy | Annotated nets | Fully annotated leaf cells | FF clock pins reviewed | TFIPC warnings |
| ---: | --- | ---: | ---: | ---: | ---: |
| 4 | fcfs | 27689/27689 | 27124/27156 | 8856 | 8815 |
| 4 | rr | 21276/21276 | 20660/20660 | 6782 | 6736 |
| 4 | fai-main | 30112/30112 | 29310/29344 | 9011 | 8973 |
| 8 | fcfs | 55712/55712 | 54672/54674 | 17677 | 17595 |
| 8 | rr | 42639/42639 | 41413/41413 | 13556 | 13465 |
| 8 | fai-main | 59996/59996 | 58497/58499 | 17932 | 17857 |
| 16 | fcfs | 111389/111389 | 109343/109343 | 35318 | 35156 |
| 16 | rr | 85250/85250 | 82803/82803 | 27102 | 26922 |
| 16 | fai-main | 119691/119691 | 116698/116698 | 35773 | 35626 |

所有nets與primary-input nets的toggle/static-probability來源均為activity file，default/propagated/unannotated為0。葉節點不足數精確對應直接literal-constant cell pins，原SAIF不含這些無net的pin活動；remote逐pin診斷核對常數及clock/reset活動，沒有當成100%leaf annotation。這是annotation coverage，不是state excitation或numerical functional coverage。

每個FF clock pin皆file-source0.0799996 transitions/ns：2.5ms窗在negedge起訖的VCS事件排序記錄199999transitions、TX0；量測仍含100000risingedges。無缺失／未知時鐘或補造default activity。

FCFS/RR每組check_power result0，2個ramp0、1個load0低於power table最小值。remote connectivity/activity/disable-timing診斷將其定位到未使用constant candidate context及無負載grant-context輸出；zero toggle，無主動data-path超範圍或missing table/function。仍保留為外插限定，不修改library/netlist/SDC、不exclude check、沒有宣稱乾淨成功。Main三組check_power result1。PTE-003的實際disabled arcs僅propagated constants，無user/loop-breaking例外。

全部VCS TFIPC逐instance對mapped module介面核對：只有未使用output腳位（DFF QN、比較器未用比較結果、共同hold狀態輸出），必要inputs全部已接；原library四種DFFport directions在FastX唯讀確認。未靜音warning，所有raw logs保留。初RRpilot checker因錯認check_power字串而exit1，後續校準只讓table-range-only diagnostics以qualified status保存，未知warning/missing tables/functions/fatal仍拒絕；原失敗attempt未覆蓋。

## 證據與限制

Raw reports：`artifacts/fastx/power-{policy}-n{N}/reports/`，採納的每組各27files；Main N8例外為`power-fai-main-n8-final/reports/`（先前未完成的14files另留原目錄，不採納）。vectors/metadata：`artifacts/power-20261021/{policy}-n{N}/`；SAIF與商用編譯產物留FastX。ignored`.setup-logs/power-20261021/`保存命令、upload/archive/source hashes、獨立audit、batch與diagnosis。JSON保存每個raw report SHA256、source/trace/acceptance/FFclock/issue明細。原始library/model未取回。

Native RTL Agent Team power-analyzer實際以Opus5.5/medium要求啟動，但HTTP429 session quota在inference前失敗，沒有native power審查結論；owner已授權的Sol/high完成tooling和校準，Codex執行與獨立採納，沒有虛構model推理或agent背書。Windows9/9focused tests PASS；WSL8PASS+1Tkinter skip（Windows已覆蓋），shell syntax/Verilator isolated TB syntax通過。既有RTL/models/Spec/profile未改，無需重跑已採納長功能回歸。

本次不含SDF/glitch activity、extracted parasitics、APR／routing／CTS、多corner、commercial equivalence/formal、長視窗trained FAI power或其他seeds。下一階段可由現有完整功能／area／STA與本次受限power資料整理總報告；若要主張適應後FAI功耗，需另外設計並驗證真實W5M長活動視窗，不能以本批代替。
