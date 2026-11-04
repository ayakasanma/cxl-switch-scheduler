# 補充測試與功耗 —2026-10-21

**21/21 實際 gate replay／SAIF／PrimeTime 命令完成，獨立審查後有條件採納。**
新增兩個cold seeds的18組，及FCFS/RR/Main N4的三組真實分類邊界測試。
共32,098,500逐cycle gate比對，其中29,998,500為預熱、2,100,000為量測週期。
另已完成[14組 RTL/netlist等價驗證](FORMAL_EQUIVALENCE_2026-10-21.md)。

## 固定方法與來源

Frozen Spec v1.0 `1af80967`不變。Clean tooling/export source `43bf9755810cb5ce920b14cc16deb258f352f150`；
重用原primary-v2 mapped source `759f86b24f13ed5984c19034eeeea2ca43b0e971`的netlist/SDC。
原nine-case [seed509 dataset](POWER_RESULTS_2026-10-21.md)、[area/STA](PPA_RESULTS_2026-10-21.md)
與profile未覆寫；新資料在[補充JSON](ppa/power-supplement-20261021.json)。
FastX-NN實際VCS/PT W-2024.09/PrimePower、原SAED32 RVT TT0.78V25C DB、ForQA/top WLM、25ns及相同I/O條件。
未改RTL/model/FIFO/hold/pipeline/Spec/profile/PT script，未重合成。所有stage exits0，最後21組remote immutable-input及SAIF hashes再次通過。

## Cold seed敏感度

每seed/N三政策的intended generation/ready hash相同，actual acceptance/per-source populations分開保留。
新增18組各100k，Main全H、沒有W5M closing。FCFS/Main六pair共600k列pin相同；此檔案比較不額外計RTLcycles。
下表保留PT總功耗列印有效位數；N16列印值相同不等於底層活動或未列印數字完全相同。

| N | Policy | Seed509 mW | Seed510 mW | Seed511 mW |
| ---: | --- | ---: | ---: | ---: |
| 4 | fcfs | 3.397 | 3.399 | 3.398 |
| 4 | rr | 2.600 | 2.602 | 2.600 |
| 4 | fai-main | 3.500 | 3.501 | 3.500 |
| 8 | fcfs | 6.728 | 6.729 | 6.725 |
| 8 | rr | 5.175 | 5.175 | 5.173 |
| 8 | fai-main | 6.924 | 6.924 | 6.920 |
| 16 | fcfs | 13.4 | 13.4 | 13.4 |
| 16 | rr | 10.3 | 10.3 | 10.3 |
| 16 | fai-main | 13.8 | 13.8 | 13.8 |

三seed皆RR < FCFS < Main；這只支持本cold workload與此mapping/corner的排序，不是統計顯著性、實際系統節能或公平性結論。
Total包含共同FIFO及必要metadata等成本，不能把全部差額叫純selector成本。

## 真實W5M分類邊界：N4

三政策各9,999,500實際預熱＋100,000量測，共10,099,500 checked cycles，沒有縮W、預載、跳時間或phase-cut reset。
相同未改ProductionTraffic/StreamProducers，三resetedges在外，持續保留FIFO、pending producers、held grant及quota context，無drain。
每一預熱/量測cycle皆full105/source/ready/valid比對；SAIF僅最後100k＝2,500,000ns。

Main literal model closing0在global4,999,999且held/stalled：B_H,B_H,H,B_H；closing1在9,999,999且有fire：L,H,H,L。
closing fire計入B/S、S=sum(B)、清零與下一cycle class可見均核對。
第二closing在measured index499，下一cycle500生效；model記錄量測High44207/Low10901fires。
共同gate TB不直接讀mapped class registers；class標籤是模型證據，gate外部pins全程相符，另有既有RTL production probes及Formality橋接。

FCFS/Main長向量前10M列相同，第一個差異恰在global10,000,000；之後11173列不同，sink-ready與output-valid無差異，
valid-source9589、valid-full105 11169列不同。Input-ready571列及upstream呈現差異也保留；不將same intended traffic當same acceptance。

| Policy (N4) | Internal mW | Switching mW | Leakage mW | Total mW | Measured accepts/fires |
| --- | ---: | ---: | ---: | ---: | ---: |
| fcfs | 1.309 | 0.01912 | 2.056 | 3.383 | 55109/55108 |
| rr | 1.001 | 0.01453 | 1.570 | 2.586 | 55109/55108 |
| fai-main | 1.334 | 0.02043 | 2.141 | 3.495 | 55109/55108 |

**此窗刻意包含一次分類／100k cycles，天然production則一次／5M（事件密度50倍）。**
它是跨真實邊界、含分類後狀態的限定樣本，不能當steady-state/production-average功耗；cold與本窗workload不同，不能將差額隔離成分類器功耗。

## 活動品質、X與警告

21組1,186,585/1,186,585 nets之toggle/static皆file來源；368,663 FF clock pins逐一核對。
206個未完全標註leaf精確對應literal-constant cell pins，逐pin驗證implied常數與clock；不冒稱100%leaf annotation。
42個table-range issue pins皆zero-toggle/file、constant unused context或zero-load context輸出。
Main7組check_power成功；FCFS/RR14組仍各2ramp/1load，保留外插限制，沒有變成clean signoff。
366,814個TFIPC warnings逐instance/port核對皆未使用output omissions，無必要input缺接；PTE-003僅propagated constant arcs。

額外S-expression SAIF residency audit區分annotation與knownness：cold有有限transient TX，三個預熱後量測窗則無transient TX、全組無TZ。
全窗always-X declarations逐一在linked PT唯一解析，確認0 leaf connections/0 top ports，
若有hierarchical pins僅允許out方向；共1476個case-local records，包含未使用的比較器輸出宣告，沒有接到active leaf邏輯；clock TX0。
SAIF aliases/ports會重複，record數不是unique net coverage，TX residency也不是power-weighted error bound。
Cold單一record最長transient TX為82,737ns，占2.5ms窗3.30948%；不能忽略或把它說成所有值已知。
依未reset資料儲存與有效介面四態pin全部通過，推定cold transient TX來自未寫入/invalid資料；SAIF residency摘要本身不提供X發生的時間位置。
不得由file annotation推出所有state已被激發或全程無X。

## 本地測試、失敗修復與證據

本地23個test cases在互補平台皆有PASS：Windows18PASS/5simulator skips；WSL22PASS/1Tcl skip（Windows補足）。
三policy strict Verilator實際RTL/TB fixtures共2304cycles、legacy RR100k；14格式/pin突變拒絕、Icarus五種真X/clock拒絕及known control通過。
unit執行時base4007f99帶待提交tooling；五個code file SHA與後續43bf975完全一致。Fixture W256只驗證工具，不充當production evidence。
Native RTL Agent Team Opus5.5/medium實際partial後遭guard中斷，新session明確weekly429；owner授權Sol/high完成工具，Codex獨立執行/審查，沒有新的native PASS背書。

保留修復：TB timescale、Icarus fgets/runtime paths、sscanf回傳與extra-field guard、light fixture hold假設；parent的CRLF starter與SAIF小數duration parser失敗也保留。
module的vendor timeout留下completed-case idle watchdog，後續用explicit /usr/bin/timeout；只清除已驗明本task完成的idle timers，未終止active EDA或license helper。
SAIF獨立診斷先因module選到較舊Python不支援removeprefix而停止，改版本相容切片後繼續；
原0pins規則又拒絕unused comparator hierarchical output，實際PT report_net確認0drivers/0loads，
改成逐net嚴格核對unique、0leafconnections、0topports及hierpins僅out，再重新執行全部21組；未豁免active unknown。
最終讀PT diagnostics summary又抓到6個N16 empty get_cells查詢錯誤（被redirect，原audit僅查主log而漏掉）。
暫撤provisional report、保留失敗raw，修成quiet collection並明確assert inventory0，重跑受影響六case的完整唯讀診斷；
最終case reports逐檔無Error/Fatal，修復PT summary0errors。原九組歷史diagnostic也有同類3個empty-query錯誤；
本次對相同三N16 netlist補足明確zero-inventory查核，原量測值與raw不改寫，沒有豁免tool error。
詳見[測試計畫](POWER_EXTENSION_TEST_PLAN.md)、[WSL重現](WSL_SETUP.md)、[方法](POWER_METHOD.md)與[完整開發記錄](DEVELOPMENT_REPORT.md)。

Raw own reports在 `artifacts/fastx/power-supp-{mode}-s{seed}-{policy}-n{N}/reports/`；vectors/metadata在
`artifacts/power/supplement-20261021/`；診斷15個case在 `artifacts/fastx/power-supplementary-diagnostics3/reports/`，
六個N16修復後case在 `artifacts/fastx/power-supplementary-diagnostics4-n16/reports/`；原失敗／superseded reports保留。
命令、native/Sol provenance、source/report SHA、失敗attempt及audits保留ignored `.setup-logs/`，機讀結果含個別證據hash。
University library/model/licenses/executables及raw SAIF留FastX，沒有下載到repository。

未做APR/routing/CTS、SDF glitch、多corner、Algorithm-2 power、trained N8/16與更廣workloads，亦非英文Spec formal proof。
沒有新correctness-critical規格矛盾或需要owner決定的架構事項；下一milestone是以已驗收功能、area/STA、Alg2N4、Formality及受限power資料整理總報告。
