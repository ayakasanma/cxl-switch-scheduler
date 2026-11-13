# FastX CGOF1/A/509 direct pilot — 2026-11-07

## Result

CGOF1/A/509 的 gate-level replay、SAIF 與 PrimeTime power 已完成並保留可重現證據。這是 `509/A` 單一 production case 的 pre-layout、zero-delay、no-SDF 功耗量測；整個 `509–511/A–B` cohort 仍為 INCOMPLETE，長 backlog drain 仍未驗證。

| 項目 | 結果 |
|---|---|
| Host / account | `fastx4-NN.ews.illinois.edu` / `chiang22` |
| Run | `cgof-power-owner-direct-20261106t210852z` |
| VCS full64 compile | `0`；`W-2024.09_Full64` |
| Gate replay | `0`；10,100,000 cycles，100,000 measured cycles |
| SAIF | semantic recheck `0`；scope `tb/dut`，duration `2,500,000 ns` |
| PrimeTime continuation | `0`；same netlist/SDC/SAIF/SAED32 DB |
| Net annotation | 28,458 / 28,458，`100.00%` |
| Fully annotated leaf cells | 27,750 / 27,784，`99.88%` |
| FF clock pins | 8,998 / 8,998；net `clk`；activity source `file` |
| Long backlog drain | `UNVERIFIED` |

PrimeTime 使用既有專案流程：SAED32 RVT `tt0p78v25c`、0.78 V、25 °C、25 ns clock、`ForQA` top wire-load model。結果單位是 W：

| Component | Power |
|---|---:|
| Internal | `0.001328` |
| Switching | `0.00001818` |
| Leakage | `0.002069` |
| Total | `0.003416` |

`check_power` 回報無 load/ramp range issue；PrimeTime 只留下 constant propagation / loop-breaking disabled-arc warning，完整 `disable-timing.rpt` 已保存。20 個 always-X records 對應 mapped topology/interface review 已列出的 arithmetic carry 與 comparator outputs；沒有 transient X/Z。

## Matched baseline

`matched-baseline-509A.json` 重用既有 accepted FCFS/RR10/Main rows，沒有重跑 baseline。共同 trace、profile、D16、10,000,000 warmup、100,000 measured cycles 與 2,500,000 ns window 已核對。既有 baseline total power 為 FCFS `0.003356 W`、RR10 `0.002559 W`、Main `0.003466 W`；CGOF1/A/509 為 `0.003416 W`。這些數值是同條件下的單 case 比較，不代表 cohort 統計或論文結論。

## Reproducibility

- Package SHA256: `6427b0334d68fff13a4836ca0798044c187f7b4e4e78224eebd771b5ecad117a`
- Netlist SHA256: `35f30ca8837ea50c47decc02aca046b264baf6c124eed9f07b7891cf24c4035a`
- SDC SHA256: `bd77ddccaf1cbc40a80ee8fe3c260c942ede05b84802d09f9448db290c90d4b4`
- SAED32 DB SHA256: `844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094`
- Cell model SHA256: `d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286`
- Profile SHA256: `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`
- Frozen source archive SHA256: `a35aeb5f47b5727017c7b49b0ead735f9071fe4bb210bfe919a7caeba14e1b98`
- Executed bounded runner SHA256: `b96d09a25e9269355a7c6d489fd1feaa01c0246352105735c4f226736bf76aa0`

完整命令與 exit statuses 位於 `.setup-logs/implementation/fastx-power-20261107/owner-direct-pilot/replay-budget-retry/`；PrimeTime continuation 命令與 receipt 位於 `.setup-logs/implementation/fastx-power-20261107/owner-direct-pilot/pt-continuation/`。

## Evidence

- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-semantic-review.json`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/pilot-audit-local.json`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/payload/execution/activity.saif`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/power.rpt`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/power-hierarchy.rpt`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/annotated.rpt`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/not-annotated.rpt`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/disable-timing.rpt`
- `artifacts/implementation/fastx-power-20261107/remote-pilot/attempt-04-budget-retry/power-review/registers-and-clock-pins.rpt`

## Limitations

Only `CGOF1/A/509` is measured. The remaining eleven CGOF inputs are not released, no additional campaign was started, and no paper or cohort-level result is upgraded. This estimate excludes SDF, SPEF, APR, physical clock-tree, glitch and silicon effects.
