# Data and figure handoff — October 28 manuscript revision

Status: COMPLETE; generation source and evidence frozen; final targeted checks passed. This unit edited only its assigned generator, tests, improvement outputs and this handoff. ARS academic-paper visualization and Data visualize-data workflows were applied. No external chat messages, new simulations or EDA runs were performed.

## Regeneration

Run from the repository root, in this order:

```powershell
python -B docs/final-report/generate_revision_v3.py --improvement-only
python -B docs/final-report/generate_revision_figures.py --improvement-only
python -B -m unittest discover -s docs/final-report -p test_generate_revision_v3.py -v
python -B -m unittest discover -s docs/final-report -p test_revision_figures.py -v
```

The new flags write only the improvement products. The existing no-flag generator behavior and E1 figure files are preserved. Figure generation checks the table generator hash, generated TeX hash and all 471 bound evidence inputs before plotting. The table generator validates the handoff bytes, its evidence pins, raw area and timing tokens, and aggregate hashes of all 100 fixed-class and 300 finite-Heavy raw job files. Selected plotted model metrics are recomputed from raw histograms, phase counts and inclusive durations. There are no added dependencies; the existing Matplotlib/NumPy renderer is reused.

## Fixed integration names

`generated/improvement_results.tex` defines exactly:

- `\ImprovementCgofHardwareTable`: six policy/N rows, complete cell area, setup and hold ns (6 decimals).
- `\ImprovementFiniteHeavyModelTable`: five overload MODEL_ONLY rows; Sparse mean run-P99, mean per-run maximum Heavy gap, mean mixed/isolated completion ratio.
- `\ImprovementProductionRtlTable`: two separate near-profile, seed-6201 RTL rows; Sparse P99, Heavy maximum gap and mixed/isolated completion ratio.
- `\ImprovementFixedClassTable`: three policies, four sources; measurement shares in percent (4 decimals).

Each of the following has editable-text SVG, vector PDF and 300-DPI PNG at `generated/figures/improvement/<name>.<ext>`:

| Name | Suggested placement | Caption content / scope |
|---|---|---|
| pooling-path | Section 1, full-width `figure*` | Shared CXL request path and the modeled descriptor slice. Solid arrows are forward requests. Dashed `in_ready` goes only FIFO→source; dashed `out_ready` only sink→held output. Admission uses beginning occupancy; arbitration eligibility is independent of sink readiness. Fire commits dequeue and service accounting. This schematic does not add pipeline stages. |
| buffer-transition | Section 2, full-width `figure*` | Main rule examples H→B_H→L and L→B_L→H, plus cancellation. B_H retains High, B_L retains Low; same-direction support in two windows changes effective class. Illustrative specified rules, not measured Buffer benefit. |
| allocation-shares | Section 5 allocation, full-width `figure*` | MODEL_ONLY N4/D16, configured W5M, initial L/H/H/H, continuous equal demand, 20,000-cycle observation BEFORE any classifier boundary. Denominator is 19,999 active-phase fires; drain excluded. Seeds 6201–6220 yield identical shares. Main uses class-level 10/10; CGOF uses source credits. |
| heavy-sparse-tradeoff | Section 5 tradeoff, full-width `figure*` | MODEL_ONLY overload, N4/D16, configured W5M, Heavy work 20,000, seeds 6201–6220. Heavy p=1, each Sparse p=.05, ready p=.9. No classification boundary occurs; class-aware policies remain initially all High. Sparse latency is the mean across seeds of within-run pooled-Sparse G-to-F nearest-rank P99, including requests completed during forced-ready cleanup. Heavy interval is mean across seeds of each run's maximum uncensored FIFO-nonempty inter-service wall-cycle gap. Gap includes sink stalls; excludes initial-service, empty-terminated and censored intervals. Two panels have independent cycle scales; paired contrast CIs are printed separately. |
| cgof-hardware | Section 5 hardware, full-width `figure*` | Six pre-layout SAED32 RVT TT 0.78V/25°C D16/W5M cases at 25ns. Left: complete library cell area (thousands); right: worst reported setup slack. Exact setup/hold and area values are in the table. Untested checks 1:1 N4/N8/N16=68/64/0; 2:1=68/4/0. CGOF power unmeasured. |

All five figures are 7.1 inches wide with minimum 8pt annotation text. Include at full text width; do not shrink to one column. Preview images were inspected, crowded footnotes were separated from axis labels, patterned share bars have clear text backgrounds, and every PDF's extracted text bounding boxes lie inside the page. Direct labels plus hatching/line styles preserve meaning without color. Formal color-vision simulation and final in-manuscript page layout are delegated to parent acceptance.

`figure-manifest.json` binds every exported byte plus `plot-data.json`, the table manifest, renderer version and source transformation hashes. Its figure/table trace records caption claims and limitations; supported-manuscript-claim links are left empty for the primary author to establish against final prose.

## Source caveats that must survive integration

Read `.setup-logs/report-improvement-20261028/evidence-review.md`; all its scope corrections relevant to these figures are incorporated.

1. W5M is a configured classification threshold, not proof of model training or adaptation. Fixed-map and equal-demand models have only 20,000 active cycles. Finite Heavy is 20,000 requests; it ends before any W5M boundary. Never attribute these gains to learned demotion or Buffer adaptation.
2. The RTL table is a separate near-profile workload (Heavy p=.8, each Sparse p=.02, ready p=.9; Heavy work 5M; seed6201). It has one B_H/H/H/H boundary, still all effective High. Two CGOF variants only. No RTL panel is embedded in the model figure; the RTL table carries that distinct context.
3. Common-demand RTL has three W5M windows and bounded producers (256 per source), hence acceptance-throttled actual generation. It produces 15,001,085 total requests; active service counts are 3,750,000/3,750,000/3,750,000/3,749,999. First boundary B_H/B_H/B_H/H preserves all effective High, followed by all H. Do not describe an unbounded one-request-per-source-per-cycle emitted workload or effective demotion.
4. Fixed-horizon endpoint `heavy_active_fire_rate` and throughput ratio mix drain numerators with active-only denominators. These are not used by any generated table or figure. Fixed-class allocation comes only from active phase counts. Unequal demand is not declared unfair from raw Jain; no raw Jain is charted.
5. The model Heavy gap is a **mean of run maxima**. The old RTL reanalysis uses a **maximum of run maxima**; captions are not interchangeable. Completion ratios are inclusive active-duration mixed/isolated ratios, not application slowdown, and mean reciprocal quantities must not be interchanged.
6. Small correction to the plan's rounded fixed-class CGOF1 source3 share: raw count 4,999 / 19,999 ×100 = 24.99624981249%, which rounds to **24.9962%** at four decimals, not 24.9963%. Source0–2 are 5,000/19,999 each. Figure labels use two decimals; the exact generated table uses four.
7. Hardware area excludes net-interconnect area, is not physical/post-layout area, and does not predict CGOF power. Zero reported timing violations does not erase untested checks. Formality claims are not generated here; parent should retain the independent review's matched/unmatched unread-state caveats.
8. H1–H5 remain future work. No baseline E1 output, prose, driver, README, QA or hypothesis index was edited by this unit.

## File inventory

- `docs/final-report/generate_revision_v3.py`
- `docs/final-report/generate_revision_figures.py`
- `docs/final-report/test_generate_revision_v3.py`
- `docs/final-report/test_revision_figures.py`
- `docs/final-report/generated/improvement_results.tex`
- `docs/final-report/generated/improvement_evidence_manifest.json`
- `docs/final-report/generated/figures/improvement/`: five PDF/SVG/PNG triples, `plot-data.json`, `figure-manifest.json`
- `docs/final-report/improvement-20261028/FIGURE_HANDOFF.md`

## Checks and frozen hashes

- `generate_revision_v3.py` SHA-256: `bc8e34bf4741b1051699c7c8d2d3a2bcdb25b9eb6342b66d467435bc08fd4d30`.
- `generate_revision_figures.py` SHA-256: `6070fb2cfd65be6d2e1640cfdf09d524015b69ad76865168008401e9f75ab403`.
- `generated/improvement_results.tex` SHA-256: `7a77999c59c5cae4f54985b4e9987981bd11d9dc0e5186aecf61d0781d1aa62d`.
- `generated/improvement_evidence_manifest.json` SHA-256: `d2e424095f0bcb7719f1d5cba1d2b1a379dd5fcccddbf32635eccf188023121c`.
- `generated/figures/improvement/figure-manifest.json` SHA-256: `0ed877479dfa6da7d9f908acbb69f541ccabcb8708115fcc1279fb17b176e27d`.

- Table/report suite: **10/10 PASS**, 35.028s, exit 0 (includes 5 new evidence tests and 5 historical tests).
- Figure suite: **5/5 PASS**, 25.052s, exit 0 (includes 2 new export/binding tests and 3 historical tests).
- Initial combined run found two obsolete expectations within one historical prose test: it prohibited the now-authorized Main shorthand and required deleted literal table/disclaimer wording. Updated only those wording expectations; retained public generated policy names, historical-alias rejection and numeric contracts. The full report suite then passed.
- All five PNGs visually inspected after relevant changes: no text overlap or clipping. Five PDF text-box checks found zero off-page or overlapping text boxes. SVG tests confirm editable text and evidence-tier labels; export hashes match.
- Original generated v3 results, v3 evidence manifest and E1 plot-data retain their handoff SHA-256 values. No historical figure regeneration occurred.
- No new model/RTL simulation, synthesis, STA, power, full manuscript compilation or formal color-vision simulation was run by this unit. Final document page placement remains parent acceptance.
