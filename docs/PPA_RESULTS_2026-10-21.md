# 共同 v2 九組 FastX DC/PT 結果 —2026-10-21

狀態：**九組實際命令完成，原始報告、driver-load與native結果審查通過；setup／hold及電氣規則9/9 MET，接受為pre-layout area／STA比較資料。** 有140個constant-disabled未測timing checks，不能宣稱全九組全tested。Power NOT_RUN；這是pre-layout比較，不是physical／multicorner signoff。

## 共同來源與方法

九組均由乾淨來源`759f86b24f13ed5984c19034eeeea2ca43b0e971`準備／執行。RTL與已完整驗收的共用比較器`d82f1b54ca54af2344ad07d914680547003f526f`相同，Spec仍為批准v1.0 commit1af80967。沒有改RTL、模型、TB、FIFO／hold、服務時序或政策專用pipeline。

[凍結profile](../syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json) canonical SHA256 `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`；[native共同方法審查](../reviews/phase-5-verify/common-profile-v2-review.md) PASS_COMMON_METHOD。相同105bit、N4/8/16、D16、M1；RR10、Main W5,000,000。

實際FastX backendFastX-NN，DC/PT W-2024.09；SAED32 RVT TT0.78V25°C，library SHA256 `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`。25ns clock，setup／hold uncertainty0.1／0.05ns，I/O delay min／max0／2ns，input／clock transition0.1ns，output load2.656828fF，固定ForQA/top WLM，auto selection off，compile-medium，DC one core。同步reset正常計時，無false／multicycle／case-analysis exceptions。

唯一相較原v1的流程方法差異：DC compile期間在記憶體內將既有library output-pin max-capacitance乘0.75，compile後還原所有原限制，再產生report／netlist／SDC；fresh PT使用原始library驗收。沒有修改library檔案或放寬PT限制。v2與成功cap075 pilot的全部數值／流程設定相同，僅profile識別與凍結metadata不同。

面積為library area units，不換算µm²／NAND2等價，不從slack推算Fmax。完整switch包括所有FIFO、政策必要metadata與共同控制；RR不含無用timestamp。共用RTL在不同政策的mapping context下可有不同gate sizing／buffer area。

## 完整 switch 面積與 STA

| N | Policy | Cell area | Comb area | Sequential area | FF cells | Setup ns | Hold ns |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | FCFS | 103970.058316 | 45419.345105 | 58550.713211 | 8856 | +13.071612 | +0.033790 |
| 4 | RR10 | 79047.172316 | 34232.434461 | 44814.737855 | 6782 | +20.519341 | +0.049066 |
| 4 | FAI Main | 110089.845892 | 50507.308009 | 59582.537883 | 9011 | +10.496409 | +0.039940 |
| 8 | FCFS | 208437.730604 | 91631.619506 | 116806.111098 | 17677 | +8.714740 | +0.103860 |
| 8 | RR10 | 158260.808962 | 68685.211782 | 89575.597180 | 13556 | +19.669725 | +0.103860 |
| 8 | FAI Main | 219344.574607 | 100840.781535 | 118503.793071 | 17932 | +5.713676 | +0.103860 |
| 16 | FCFS | 416886.135213 | 183513.824960 | 233372.310253 | 35318 | +3.891612 | +0.103860 |
| 16 | RR10 | 316614.126327 | 137530.534272 | 179083.592055 | 27102 | +18.694050 | +0.095469 |
| 16 | FAI Main | 437622.506788 | 201218.766809 | 236403.739979 | 35773 | +1.158148 | +0.084335 |

每組area／QOR／reference與mapped netlist展開leaf inventory相互核對，macro／blackbox area為0，總面積與comb＋sequential一致。所有時序與電氣結論均讀自本組PT原始報告，未以DC零違規替代PT。

## 硬體分項與政策成本

| N | Policy | FIFO含metadata | Policy subtree | Common hold | Top／arrival helpers |
| ---: | --- | ---: | ---: | ---: | ---: |
| 4 | FCFS | 101672.8508 | 1131.9574 | 812.2442 | 353.0059 |
| 4 | RR10 | 77966.8062 | 263.0390 | 809.1945 | 8.1326 |
| 4 | FAI Main | 101724.9502 | 7143.9879 | 859.7692 | 361.1386 |
| 8 | FCFS | 203421.9444 | 2767.6281 | 1797.3064 | 450.8515 |
| 8 | RR10 | 155930.5626 | 512.8626 | 1801.1185 | 16.2652 |
| 8 | FAI Main | 203434.6519 | 13596.4499 | 1846.3562 | 467.1167 |
| 16 | FCFS | 406836.0107 | 6038.4614 | 3475.1651 | 536.4979 |
| 16 | RR10 | 311832.9154 | 1268.6869 | 3479.9938 | 32.5304 |
| 16 | FAI Main | 406858.3751 | 26673.1754 | 3525.4856 | 565.4704 |

表內subtree僅加總直接子階層與top-local logic，不重複計parent／child。FIFO項包含FCFS／Main必要arrival metadata；Main相對FCFS／RR的完整switch差值包含metadata與mapping差異，不能叫純selector成本。沒有刻意以不同FIFO、buffering或pipeline偏袒政策。

N4 Main相對FCFS完整面積+5.89%，相對RR+39.27%；N8 Main相對FCFS完整面積+5.23%，相對RR+38.60%；N16 Main相對FCFS完整面積+4.97%，相對RR+38.22%。

## Coverage、電氣與負載核對

| N | Policy | Tested/met | Violated | Untested | PT cap／slew |
| ---: | --- | ---: | ---: | ---: | --- |
| 4 | FCFS | 35712 | 0 | 64 | 0／0 |
| 4 | RR10 | 27356 | 0 | 0 | 0／0 |
| 4 | FAI Main | 36336 | 0 | 68 | 0／0 |
| 8 | FCFS | 70946 | 0 | 4 | 0／0 |
| 8 | RR10 | 54462 | 0 | 0 | 0／0 |
| 8 | FAI Main | 71966 | 0 | 4 | 0／0 |
| 16 | FCFS | 141524 | 0 | 0 | 0／0 |
| 16 | RR10 | 108660 | 0 | 0 | 0／0 |
| 16 | FAI Main | 143344 | 0 | 0 | 0／0 |

140個未測checks分屬FCFS4=64、Main4=68、FCFS8=4、Main8=4，原因逐項為`constant_disabled`；其餘配置全tested。具體pin與disabled arcs保存於各組`pt_coverage_untested.rpt`／`pt_disable_timing.rpt`。它們不計為違規，也不假裝已被測到。

每組390個暫時library限制均applied/restored，20個未定義library outputs明確略過；SDC不含cap overlay。原始library hash一致，PT使用原限制。九組額外唯讀driver surveys合計542065個used output-driver pins，每個皆有正原始limit、ordinary／CCS負載均未超限，另列80個constant pseudo-drivers。survey不compile、不改netlist／SDC，前後雜湊一致；transfer與source hashes全部通過。這建立本九個netlist的實測證據，不代表0.75是全library通用界限。

## 警告、證據與限制

原始DC訊息包括VER-941（parameter guard的`$fatal`診斷字串）、VER-318（常數型別轉換）、TIM-134（高fanout使用1000估算）、LINT-99及各組適用的UCN／DW未連接carry等訊息。PT保留SDC-2版本提示與PTE-003 disabled-arcs提示。這些需要與`check_design`、emitted SDC及actual disabled-arcs清單一起閱讀；不宣稱「無警告」，也不偷偷改RTL或關閉檢查。

[Native結果審查](../reviews/phase-5-verify/primary-v2-results-review.md)已實際以RTL Agent Team synthesis-reviewer／Opus5.5 medium完成，CLI exit0，492/492檢查通過。67個實際assistant response records均為`claude-opus-5-5`；一次mid-response server_error保留後恢復，無fallback。審查重新計算原始資料，不只引用Codex摘要；確認disabled timing arcs只有propagated-constant flag，沒有user／case／loop停用，完整descriptor／arrival storage符合Spec且RR無timestamp。

Native首次嚴格SDC負載相等檢查發現工具將2.656828fF輸出為2.65683fF，九組及舊pilot／v1都相同；修正為符合實際五位小數輸出的5e-6fF界限，差值2e-6fF，原始失敗檢查保留。這是report serialization精度核對，沒有改profile／SDC或放寬電氣驗收。Codex最後核對面積分項，FIFO占比範圍為92.40–98.63%，已修正review中的概略範圍。

全部九組開始／結束／exit保存在remote control與本機case-exits紀錄。原始資料經allowlist取回並核對source／result／transfer hashes、必要reports、工具／library／profile／結構與constraints。沒有下載`.db/.lib/.ddc`、licenses或工具執行檔。原始v1與pilot目錄及[原v1結果](PPA_RESULTS_2026-10-20.md)完整保留，不能與v2拼成同一公平比較表；跨v1／v2差異不能單獨歸因於比較器，Main16同cap075 pilot比較見[前階段結果](PPA_COMPARATOR_PILOT_2026-10-21.md)。

所有實驗／survey／取回都完成後，額外remote收尾查詢因SSH master timeout／broken pipe未取得新輸出，終止該卡住的唯讀查詢，失敗與重連紀錄保留。已確認本機無SSH殘留程序。library在九組及最後完整control讀取時均有相同hash證據；不把失敗收尾查詢當成成功，也不影響之前已完成／取回的命令結果。

功能驗收沿用已完成的180/180 primary、30/30 Main stress、3/3 production（60million實際measured cycles／12windows）及完整共同／政策unit回歸；本輪沒有RTL變更，不把generator基礎測試冒充新的scheduler coverage。短primary不到分類視窗，這組硬體成本不能證明適應性公平收益。

Power、Algorithm-2、商用形式等價、APR、post-layout寄生、CTS、multicorner均NOT_RUN。下一個獨立milestone是Algorithm-2 N4補充實作／功能與行為驗證，之後同方法合成比較；activity-based power需另驗證工具能力與annotation coverage。

完整版本、agent/model／effort、命令、失敗修復、run IDs與採納紀錄：[DEVELOPMENT_REPORT](DEVELOPMENT_REPORT.md)。機讀來源與完整數值：[v2 JSON](ppa/primary-20261021-v2.json)。

## 自行驗收原始報告

- N4 FCFS：[area](../artifacts/fastx/primary-20261021-v2-fcfs-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fcfs-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fcfs-n4/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fcfs-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fcfs-n4/reports/pt_coverage_untested.rpt)。
- N4 RR10：[area](../artifacts/fastx/primary-20261021-v2-rr-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-rr-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-rr-n4/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-rr-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-rr-n4/reports/pt_coverage_untested.rpt)。
- N4 FAI Main：[area](../artifacts/fastx/primary-20261021-v2-fai-main-n4/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fai-main-n4/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fai-main-n4/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fai-main-n4/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fai-main-n4/reports/pt_coverage_untested.rpt)。
- N8 FCFS：[area](../artifacts/fastx/primary-20261021-v2-fcfs-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fcfs-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fcfs-n8/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fcfs-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fcfs-n8/reports/pt_coverage_untested.rpt)。
- N8 RR10：[area](../artifacts/fastx/primary-20261021-v2-rr-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-rr-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-rr-n8/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-rr-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-rr-n8/reports/pt_coverage_untested.rpt)。
- N8 FAI Main：[area](../artifacts/fastx/primary-20261021-v2-fai-main-n8/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fai-main-n8/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fai-main-n8/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fai-main-n8/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fai-main-n8/reports/pt_coverage_untested.rpt)。
- N16 FCFS：[area](../artifacts/fastx/primary-20261021-v2-fcfs-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fcfs-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fcfs-n16/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fcfs-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fcfs-n16/reports/pt_coverage_untested.rpt)。
- N16 RR10：[area](../artifacts/fastx/primary-20261021-v2-rr-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-rr-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-rr-n16/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-rr-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-rr-n16/reports/pt_coverage_untested.rpt)。
- N16 FAI Main：[area](../artifacts/fastx/primary-20261021-v2-fai-main-n16/reports/area.rpt)、[setup](../artifacts/fastx/primary-20261021-v2-fai-main-n16/reports/pt_timing_max.rpt)、[hold](../artifacts/fastx/primary-20261021-v2-fai-main-n16/reports/pt_timing_min.rpt)、[constraints](../artifacts/fastx/primary-20261021-v2-fai-main-n16/reports/pt_constraints.rpt)、[coverage](../artifacts/fastx/primary-20261021-v2-fai-main-n16/reports/pt_coverage_untested.rpt)。
