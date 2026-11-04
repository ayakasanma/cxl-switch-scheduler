# RTL fairness and Heavy diagnosis

> Public synthesis: [DIAGNOSIS_SUMMARY.md](DIAGNOSIS_SUMMARY.md). This
> generated table is relabeled to public policy names; the raw JSON remains
> unchanged for provenance. Use the public summary for comparisons and claim
> boundaries.

- Source: `C:\Users\USER\Documents\Coding Space\CXL\cxl-scheduler\.setup-logs\implementation\revision-20261024\power-index\final498-20261027\snapshot\analysis\analysis.json`
- SHA-256: `89170cfbe0bb449c25ebbe782203b1695550b7b6bb9e467bae8d6bb00b483061`
- Accepted endpoints: 960
- Scope: scheduler-boundary RTL evidence; no CXL application measurement.

## Cohort summaries

| Policy | Profile | Group | Ready | N/D/W | Heavy src | Seeds | Raw Jain | Active Jain | Sparse Jain | Heavy fire/ready | Heavy share | Max wall gap |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CGOF (2:1) | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| CGOF (2:1) | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| CGOF (2:1) | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| CGOF (2:1) | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266152 | 0.266152 | 0.999404 | 0.969018 | 0.969018 | 13 |
| CGOF (2:1) | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266177 | 0.266177 | 0.999404 | 0.968971 | 0.968971 | 23 |
| CGOF (2:1) | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080058 | 0.080058 | 0.998534 | 0.883048 | 0.883048 | 11 |
| CGOF (2:1) | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139719 | 0.139719 | 0.998969 | 0.945640 | 0.945640 | 7 |
| CGOF (2:1) | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262084 | 0.262084 | 0.999386 | 0.976581 | 0.976581 | 6 |
| CGOF (2:1) | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| CGOF (2:1) | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| CGOF (2:1) | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| CGOF (2:1) | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| CGOF (2:1) | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266305 | 0.266305 | 0.999999 | 0.968735 | 0.968735 | 21 |
| CGOF (2:1) | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266297 | 0.266297 | 1.000000 | 0.968750 | 0.968750 | 27 |
| CGOF (2:1) | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080100 | 0.080100 | 1.000000 | 0.882812 | 0.882812 | 11 |
| CGOF (2:1) | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139814 | 0.139814 | 1.000000 | 0.945312 | 0.945312 | 11 |
| CGOF (2:1) | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262092 | 0.262092 | 0.999999 | 0.976565 | 0.976565 | 11 |
| CGOF (2:1) | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| BLISS | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 5 |
| BLISS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 5 |
| BLISS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 5 |
| BLISS | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266153 | 0.266153 | 0.999408 | 0.969015 | 0.969015 | 10 |
| BLISS | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266178 | 0.266178 | 0.999408 | 0.968969 | 0.968969 | 21 |
| BLISS | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080059 | 0.080059 | 0.998537 | 0.883042 | 0.883042 | 10 |
| BLISS | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139719 | 0.139719 | 0.998972 | 0.945638 | 0.945638 | 6 |
| BLISS | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262084 | 0.262084 | 0.999388 | 0.976581 | 0.976581 | 6 |
| BLISS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 5 |
| BLISS | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 17 |
| BLISS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 17 |
| BLISS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 17 |
| BLISS | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266298 | 0.266298 | 0.999996 | 0.968748 | 0.968748 | 20 |
| BLISS | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266287 | 0.266287 | 0.999997 | 0.968768 | 0.968768 | 25 |
| BLISS | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080098 | 0.080098 | 0.999999 | 0.882826 | 0.882826 | 25 |
| BLISS | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139810 | 0.139810 | 0.999998 | 0.945326 | 0.945326 | 25 |
| BLISS | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262092 | 0.262092 | 0.999999 | 0.976566 | 0.976566 | 17 |
| BLISS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 10 |
| CGOF (2:1) | trained-A | insight-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262084 | 0.262084 | 0.999388 | 0.976581 | 0.976581 | 5 |
| CGOF (2:1) | trained-A | insight-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266153 | 0.266153 | 0.999408 | 0.969015 | 0.969015 | 10 |
| CGOF (2:1) | trained-A | insight-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266178 | 0.266178 | 0.999408 | 0.968969 | 0.968969 | 20 |
| CGOF (2:1) | trained-B | insight-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 7 |
| CGOF (2:1) | trained-B | insight-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266309 | 0.266309 | 1.000000 | 0.968727 | 0.968727 | 13 |
| CGOF (2:1) | trained-B | insight-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266297 | 0.266297 | 1.000000 | 0.968750 | 0.968750 | 21 |
| FCFS | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 3 |
| FCFS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 3 |
| FCFS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 3 |
| FCFS | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266149 | 0.266149 | 0.999406 | 0.969023 | 0.969023 | 14 |
| FCFS | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266175 | 0.266175 | 0.999408 | 0.968974 | 0.968974 | 19 |
| FCFS | trained-A | depth | always | 4/16/5000000 | 0 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 3 |
| FCFS | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080054 | 0.080054 | 0.998524 | 0.883070 | 0.883070 | 5 |
| FCFS | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139716 | 0.139716 | 0.998967 | 0.945650 | 0.945650 | 4 |
| FCFS | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262085 | 0.262085 | 0.999385 | 0.976579 | 0.976579 | 4 |
| FCFS | trained-A | depth | always | 4/32/5000000 | 0 | 5 | 0.262005 | 0.262005 | 0.999406 | 0.976730 | 0.976730 | 3 |
| FCFS | trained-A | depth | always | 4/8/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 3 |
| FCFS | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 3 |
| FCFS | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 4 |
| FCFS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 4 |
| FCFS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 4 |
| FCFS | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266298 | 0.266298 | 0.999996 | 0.968748 | 0.968748 | 15 |
| FCFS | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266287 | 0.266287 | 0.999997 | 0.968768 | 0.968768 | 25 |
| FCFS | trained-B | depth | always | 4/16/5000000 | 0 | 5 | 0.262086 | 0.262086 | 0.999997 | 0.976576 | 0.976576 | 4 |
| FCFS | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080098 | 0.080098 | 0.999999 | 0.882826 | 0.882826 | 14 |
| FCFS | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139810 | 0.139810 | 0.999998 | 0.945326 | 0.945326 | 7 |
| FCFS | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262092 | 0.262092 | 0.999999 | 0.976566 | 0.976566 | 5 |
| FCFS | trained-B | depth | always | 4/32/5000000 | 0 | 5 | 0.262085 | 0.262085 | 0.999996 | 0.976578 | 0.976578 | 5 |
| FCFS | trained-B | depth | always | 4/8/5000000 | 0 | 5 | 0.262091 | 0.262091 | 0.999999 | 0.976568 | 0.976568 | 5 |
| FCFS | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 6 |
| FAI-inspired | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266152 | 0.266152 | 0.999410 | 0.969018 | 0.969018 | 11 |
| FAI-inspired | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266178 | 0.266178 | 0.999407 | 0.968969 | 0.968969 | 22 |
| FAI-inspired | trained-A | depth | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 6 |
| FAI-inspired | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080059 | 0.080059 | 0.998535 | 0.883044 | 0.883044 | 11 |
| FAI-inspired | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139719 | 0.139719 | 0.998971 | 0.945640 | 0.945640 | 8 |
| FAI-inspired | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262086 | 0.262086 | 0.999386 | 0.976577 | 0.976577 | 6 |
| FAI-inspired | trained-A | depth | always | 4/32/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-A | depth | always | 4/8/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| FAI-inspired | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999407 | 0.976724 | 0.976724 | 7 |
| FAI-inspired | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266302 | 0.266302 | 0.999998 | 0.968740 | 0.968740 | 21 |
| FAI-inspired | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266297 | 0.266297 | 1.000000 | 0.968750 | 0.968750 | 27 |
| FAI-inspired | trained-B | depth | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 21 |
| FAI-inspired | trained-B | high-quota | always | 4/16/5000000 | 0 | 5 | 0.262091 | 0.262091 | 0.999999 | 0.976568 | 0.976568 | 6 |
| FAI-inspired | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080100 | 0.080100 | 1.000000 | 0.882812 | 0.882812 | 11 |
| FAI-inspired | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139814 | 0.139814 | 1.000000 | 0.945312 | 0.945312 | 11 |
| FAI-inspired | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262092 | 0.262092 | 0.999999 | 0.976565 | 0.976565 | 11 |
| FAI-inspired | trained-B | depth | always | 4/32/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 11 |
| FAI-inspired | trained-B | depth | always | 4/8/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| FAI-inspired | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| FAI-inspired | trained-A | one-window-causal | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| FAI-inspired | trained-B | one-window-causal | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 11 |
| RR | trained-A | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 4 |
| RR | trained-A | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR | trained-A | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262006 | 0.262006 | 0.999408 | 0.976728 | 0.976728 | 7 |
| RR | trained-A | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| RR | trained-A | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 5 |
| RR | trained-B | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 4 |
| RR | trained-B | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR | trained-B | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262088 | 0.262088 | 0.999998 | 0.976572 | 0.976572 | 17 |
| RR | trained-B | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 9 |
| RR | trained-B | rr-quantum | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 17 |
| RR1 | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 3 |
| RR1 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 4 |
| RR1 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 4 |
| RR1 | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266153 | 0.266153 | 0.999408 | 0.969015 | 0.969015 | 10 |
| RR1 | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266178 | 0.266178 | 0.999408 | 0.968969 | 0.968969 | 20 |
| RR1 | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080059 | 0.080059 | 0.998537 | 0.883042 | 0.883042 | 7 |
| RR1 | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139719 | 0.139719 | 0.998972 | 0.945638 | 0.945638 | 5 |
| RR1 | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262084 | 0.262084 | 0.999388 | 0.976581 | 0.976581 | 4 |
| RR1 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262008 | 0.262008 | 0.999408 | 0.976724 | 0.976724 | 4 |
| RR1 | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 4 |
| RR1 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 4 |
| RR1 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 4 |
| RR1 | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266306 | 0.266306 | 1.000000 | 0.968732 | 0.968732 | 10 |
| RR1 | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266297 | 0.266297 | 1.000000 | 0.968750 | 0.968750 | 19 |
| RR1 | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080100 | 0.080100 | 1.000000 | 0.882812 | 0.882812 | 6 |
| RR1 | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139814 | 0.139814 | 1.000000 | 0.945312 | 0.945312 | 4 |
| RR1 | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262092 | 0.262092 | 1.000000 | 0.976565 | 0.976565 | 4 |
| RR1 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 4 |
| RR10 | trained-A | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266150 | 0.266150 | 0.999402 | 0.969020 | 0.969020 | 11 |
| RR10 | trained-A | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266177 | 0.266177 | 0.999404 | 0.968971 | 0.968971 | 22 |
| RR10 | trained-A | depth | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080058 | 0.080058 | 0.998533 | 0.883046 | 0.883046 | 11 |
| RR10 | trained-A | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139718 | 0.139718 | 0.998968 | 0.945642 | 0.945642 | 7 |
| RR10 | trained-A | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262084 | 0.262084 | 0.999387 | 0.976580 | 0.976580 | 6 |
| RR10 | trained-A | depth | always | 4/32/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | depth | always | 4/8/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-A | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262007 | 0.262007 | 0.999404 | 0.976726 | 0.976726 | 6 |
| RR10 | trained-B | trained-robustness | always | 4/16/5000000 | 3 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 25 |
| RR10 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR10 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR10 | trained-B | trained-robustness | bernoulli-0.75 | 4/16/5000000 | 0 | 5 | 0.266302 | 0.266302 | 0.999998 | 0.968740 | 0.968740 | 30 |
| RR10 | trained-B | trained-robustness | periodic-48/64 | 4/16/5000000 | 0 | 5 | 0.266297 | 0.266297 | 1.000000 | 0.968750 | 0.968750 | 33 |
| RR10 | trained-B | depth | always | 4/16/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR10 | trained-B | n-expansion | always | 16/16/5000000 | 0 | 5 | 0.080100 | 0.080100 | 1.000000 | 0.882812 | 0.882812 | 41 |
| RR10 | trained-B | n-expansion | always | 8/16/5000000 | 0 | 5 | 0.139814 | 0.139814 | 1.000000 | 0.945312 | 0.945312 | 25 |
| RR10 | trained-B | n4-confirmation | always | 4/16/5000000 | 0 | 20 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 25 |
| RR10 | trained-B | depth | always | 4/32/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR10 | trained-B | depth | always | 4/8/5000000 | 0 | 5 | 0.262093 | 0.262093 | 1.000000 | 0.976564 | 0.976564 | 17 |
| RR10 | trained-B | trained-robustness | always | 4/16/5000000 | 0 | 5 | 0.262094 | 0.262094 | 1.000000 | 0.976562 | 0.976562 | 31 |

Raw Jain includes the Heavy source and is expected to be low under asymmetric demand. It is not by itself a fairness verdict. Sparse Jain excludes the configured Heavy source.

## Unavailable measurements

- `joint_backlog_quota_compliance`: RTL endpoints expose per-source backlog summaries, not a joint per-cycle all-source backlog trace.
- `dynamic_weighted_cgof_entitlement`: RTL endpoints do not expose the dynamic per-window class trajectory needed to reconstruct CGOF (2:1) entitlements.
- `finite_heavy_completion`: RTL endpoints have no finite Heavy workload, burst ID, or burst completion trace.
- `completed_memory_bandwidth`: No calibrated CXL platform or completed-byte measurement is present.
- `memory_response_latency`: Generation-to-fire is scheduler waiting, not an issue-to-response CXL measurement.
- `application_slowdown`: No application or calibrated CXL system harness is present.
