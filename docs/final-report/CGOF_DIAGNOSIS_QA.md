# CGOF Diagnosis Revision QA

Date: 2026-10-27 Asia/Taipei.
This receipt covers the final report generated from the accepted 498-row
evidence plus the separate MODEL_ONLY diagnosis harness. It does not promote
the smoke run into production evidence or claim CGOF algorithm novelty.

## Final PDF

- Source: `main-v3.tex`
- PDF: `output/pdf/cxl-scheduler-v3-cgof-diagnosis-final-20261027T092103Z.pdf`
- Pages: 12, US Letter
- SHA-256:
  `E277786796638EE3F1DDCABF0CFE87BBF79AC67CDBB3EDC988614FF33C233FCD`
- First compile: exit 0
- Second compile: exit 0
- Final diagnostics: zero overfull boxes, undefined references/citations, or
  LaTeX/package warnings. Twenty-seven underfull horizontal boxes remain; the
  final text page was visually inspected and no clipping or overlap was found.
- Public naming: `CGOF` is defined once as `Credit-Gated Oldest-First`; settings
  appear as `CGOF (1:1)` and `CGOF (2:1)`, and the baseline is `FAI-inspired`.
  A text scan found no `DAC1`/`DAC2`, former-name, or historical-rename text.
- All 12 rendered pages were inspected. The first visual pass found overlapping
  tick labels in Figure 1; the figure generator was changed to wrap
  `FAI-inspired`, then all 12 pages were rebuilt and reinspected.

The final PDF is a revised course-report artifact. It is not an external
peer-review acceptance, physical signoff, full-system CXL measurement, or
application slowdown study.

## Generated data and figures

Commands:

```powershell
C:\ProgramData\anaconda3\python.exe docs/final-report/generate_revision_v3.py --out-dir docs/final-report/generated
C:\ProgramData\anaconda3\python.exe docs/final-report/generate_revision_figures.py
C:\ProgramData\anaconda3\python.exe -m pytest -q docs/final-report/test_generate_revision_v3.py docs/final-report/test_revision_figures.py
```

- Generator tests: 8 passed.
- Figures: six vector PDF/SVG/PNG outputs plus `plot-data.json` and
  `figure-manifest.json`.
- `revision_v3_results.tex` SHA-256:
  `8e8675907d91d9739a27db6d1319b1f403ca032a13b81ee4f154eaabf40b2b26`
- The generated table values remain bound to the hash-pinned 498-row evidence;
  the Figure 1 change affects label layout only, not measured values.

## Separate MODEL_ONLY smoke

- Evidence: `artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z/`
- Result: 27/27 jobs PASS, 0 failures, source-stable.
- Manifest digest:
  `5b25f6bca497165e497d58a8e667230081ae0b726c788dcd5240a0ee23304781`
- Summary digest:
  `5a70ab871ae64d5481aa95697e288a5021eee248e9b746696fbc0fdf3a848627`
- All 18 comparison records are `NOT_RUN` because this is a smoke run.
- The run verifies runner/manifest/metric plumbing only. It is not a W5M,
  exploration, confirmation, RTL-control, or application result.

The model evidence and report evidence are deliberately separate. The report's
accepted 498-row RTL matrix is not augmented by the smoke jobs, and the smoke
does not inherit the report's confirmation claims.
