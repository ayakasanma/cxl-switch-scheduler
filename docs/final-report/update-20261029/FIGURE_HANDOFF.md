# Oct29 data and figure handoff

Status: **COMPLETE / FROZEN**, 2026-10-29 Asia/Taipei. Bounded figure/data work by GPT-6.1 Sol; parent retains manuscript integration and acceptance. Applied ARS experiment-agent validation and Data visualize-data guidance. No simulation or EDA ran.

## Integration contract

Include `generated/update_20261029_results.tex` after the previous generated inputs. It defines `\UpdateFiniteHeavyTable` and `\UpdatePerformanceTable`. Both are tabular bodies using the report's existing booktabs package; the parent owns table environments, captions, labels and placement.

Use these two vector figures in full-width `figure*` environments at `width=\textwidth` (designed at **7.1 inches**). Each also has an editable SVG with text elements and a 300-dpi PNG:

- `generated/figures/update-20261029/finite-heavy-confirmation.pdf`
- `generated/figures/update-20261029/readiness-confirmation.pdf`

`plot-data.json` contains all recomputed seed rows, summaries, metric definitions and direct input hashes. `figure-manifest.json` and `generated/update_20261029_manifest.json` contain matching export/source bindings. The latter hashes **241 consumed files**, including raw results, scopes, frozen source records, current executable sources and the fresh read-only aggregator/statistics helpers.

## Finite-Heavy confirmation: figure, table and caption

The repaired batch contains **80 PASS raw lane results, 40 mixed/isolated pairs, 20 seeds529–548**, two High:Low quotas. All twenty run scopes are stable PASS. The old failed batch `confirmation-finite-heavy-20261029` / run `20261028T202434Z_267411` is excluded: its cutoff classification omitted a Sparse completion. The historical top-level batch status is not used as completion evidence. The repaired aggregate is independently recomputed from all scoped raw results.

| High:Low | Mean run Sparse P99, 95% CI | Mean of Heavy run maxima, 95% CI | Mean paired Heavy completion delay, 95% CI |
| --- | --- | --- | --- |
| 1:1 | 3 [3,3] cycles | 9.45 [9.15,9.75] cycles | 3.05 [1.45,5.05] cycles |
| 2:1 | 4 [4,4] cycles | 10.85 [10.45,11.35] cycles | 3 [1.4,5] cycles |

The mean mixed/isolated inclusive completion ratios are 1.00000048799413 [1.000000224015324,1.0000008079500087] for1:1 and 1.0000004799951348 [1.0000002240008359,1.0000007999618958] for2:1. The plot uses **cycle differences** instead of a near-one ratio bar. It retains each seed observation, connects the same seed across quotas and overlays means and pointwise95% bootstrap intervals.

The paired quota contrast2:1 minus1:1 is +1 [1,1] cycle in Sparse run-P99 and +1.4 [1.1,1.75] cycles in Heavy run maximum gap. These are seed-level paired effects, separate from each arm's interval. Completion differences describe scheduler last-fire times; they are not application slowdown, response-latency measurements, a hard maximum bound or an equivalence test.

**Suggested caption:** Finite-Heavy RTL confirmation across20 seeds529–548 on the N4, D16 platform with W=5,000,000 cycles and5,000,000 Heavy requests. Heavy arrivals use p=0.8, each Sparse source p=0.02 and sink readiness p=0.9. Lines connect the same seed across High:Low quotas; diamonds show means and brackets give pointwise95% bootstrap intervals. Sparse values are the means of run-level pooled-Sparse generation-to-fire P99s; Heavy gap values are the means of active-phase run maxima. Completion delay is the paired mixed-minus-isolated last-fire cycle difference. Each lane crosses one classification boundary, reaching B_H/H/H/H while all sources remain effective High.

Estimator details for manuscript integration:

- Sparse P99 uses the **generation cohort**, including requests completed during drain. Three mixed lanes retain one Sparse request at the Heavy completion cutoff; these requests are included after drain. All generation-cohort counts conserve.
- Fairness/service shares use the **active phase before drain**. They should not be described as full-drain generation shares.
- Heavy wall gap is the interval between consecutive services while its FIFO remains nonempty, including sink stalls; initial, empty-terminated and censored intervals are excluded. Aggregate run maxima are means, not the maximum across all runs or a deterministic bound.
- All eighty raw lanes cross exactly one boundary to B_H/H/H/H. B_H retains effective High. This cohort measures the quota/ordering behavior in that state; it does not demonstrate effective demotion to Low or long-term adaptation.
- Pairing is by seed and exogenous generator configuration. Sparse generation stops at Heavy completion. In seed542 mixed runs, quota1:1 lasts6,250,789 active cycles and2:1 lasts6,250,788, so the realized trace hashes differ by the ending prefix; the matched generator configuration is identical. No identical-length-trace claim is made.

## Readiness confirmation: figure, table and caption

Latest CGOF2 performance evidence contains **30 raw runs, 60 A/B endpoints**:20 always-ready confirmation runs (seeds529–548) plus10 readiness runs (two schedules, seeds509–513). Each raw run contributes A and B. Six prior split directories retain RUNNING summaries; every present step is PASS, their completed endpoints are joined with the resumed PASS runs, and the full expected endpoint/seed grid is required. The generator does not label the partial directory runs themselves as completed.

| Stage | Sink readiness | Seeds | A: independent arrivals | B: bursts |
| --- | --- | --- | --- | --- |
| Confirmation | Always ready |20 |1.10 [1.00,1.25] |12.35 [11.80,12.90] |
| Exploration | Bernoulli0.75 |5 |5.00 |20.40 |
| Exploration | Periodic48/64 |5 |17.00 |27.00 |

Values are mean run Sparse P99s in cycles. Only confirmation has inferential intervals. The chart separates stages with whitespace, background and a divider, retaining observations and means without connecting the20-seed and5-seed groups. It contains current-source CGOF2 endpoints only; it does not imply a fresh Main rerun.

**Suggested caption:** CGOF(2:1) Sparse generation-to-fire waiting under independent arrivals(A) and bursts(B), using N4, D16, W=5,000,000 cycles and10,000,000 training cycles. Always-ready confirmation uses20 seeds529–548; readiness exploration uses5 seeds509–513 per schedule. Points show run-level P99s, diamonds and error bars show confirmation means with pointwise95% bootstrap intervals, and horizontal marks show exploration means. Bernoulli0.75 and periodic48/64 compare two temporal readiness patterns at the same nominal75% availability.

Nominal and realized availability differ slightly: Bernoulli realized rates range75.000–75.215% in A and74.801758–75.161133% in B; periodic rates are75.008% in A and75% in B. The comparison supports the observed schedule-specific waiting pattern; it does not isolate temporal structure from every finite-sample availability difference.

## Source and statistical validation

- Sealed repaired aggregate SHA-256: `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d`.
- Repaired manifest SHA-256: `2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407`.
- Prior/current baseline aggregate SHA-256: `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097`.
- Direct scopes and raw results are hash checked; embedded scoped finite result data match the corresponding raw files. Histograms independently reproduce Sparse P99/count and Heavy gap extrema/P99. Inclusive active cycles equal Heavy last-fire cycle+1.
- Existing `scripts/aggregate_cgof_diagnosis.py` recomputes all per-seed rows, finite summaries/quota contrasts and performance cohorts from raw inputs. All saved summaries and intervals compare exactly. It uses10,000 deterministic keyed percentile-bootstrap resamples at the seed/run unit. Intervals are pointwise, without a family-wise correction; no p-values or equivalence claim is added.
- Finite source hashes agree across all20 scopes and with the repaired manifest/current executables. Performance source variants differ only in `AGENTS.md`; no executable source differs. Before/after hashes are checked where completed scopes exist, and the frozen source records bind earlier partial split endpoints.
- Legacy Oct28 generators, pins and products remain untouched. Their mutable evidence document/script paths have legitimately drifted, so this task does **not** rerun or relax the historical pipeline. Parent may reuse released products using immutable Oct28 release output hashes.
- ARS statistical fallacy scan:11/11 considered. Arms, readiness schedules and stages stay separate (aggregation/ecological risks); the entire expected seed grid is required (selection/survivorship); paired run differences preserve their intended scope; base-rate/diagnostic and pre/post regression questions are inapplicable. CI precision is not a practical-equivalence result, local maxima are not a universal bound, and no causal/application-level extrapolation is made. Multiple displayed intervals retain their pointwise qualification.

## Reproduction and own acceptance receipt

From the repository root:

```powershell
C:/ProgramData/anaconda3/python.exe -B docs/final-report/generate_update_20261029.py
C:/ProgramData/anaconda3/python.exe -B -m pytest -q -p no:cacheprovider docs/final-report/test_update_20261029.py
```

Final targeted receipt: **5/5 PASS**,5.71s, exit0 after the final metadata/footer edits. Tests cover raw summary reconstruction, unique/complete seed/quota grids, histogram mismatch rejection, explicit inferential tiers, editable SVG text,7.1-inch export width, output hashes and identical figure/table data. All six exports were regenerated. Both PNGs were visually inspected; the finite figure's initial title collision was repaired, and the readiness footer now reads “Exploration compares readiness patterns at the same nominal75% availability.” Parent also reported both previews readable. Every figure uses at least8-point annotation text at its designed width.

Frozen files:

| File | SHA-256 |
| --- | --- |
| `generate_update_20261029.py` | `8ddd10edd95cf086949bbee34140f8dff28fb57b571fb2b9eccda23f4532e5cf` |
| `test_update_20261029.py` | `9f78ac0d2e874250394f14d4d8edaccdc3adbe360b19dcf68f6dda6d29247b2f` |
| `generated/update_20261029_results.tex` | `cf5881c18654d95002ca0da464e2d486c6081fa6123fd9abb53e5585a799b775` |
| `generated/update_20261029_manifest.json` | `faa70baa3e2dda8261f902c8b1d8edd3748c49506ed4c8932c5687b5b216c68a` |

Changed only the assigned new generator/test, generated Oct29 TeX/manifests/figure directory, and this handoff. No existing report/generator/product was changed. Full manuscript compilation and integrated page placement remain with the parent.
