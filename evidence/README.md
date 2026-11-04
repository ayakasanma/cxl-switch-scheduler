# Evidence records

Each file is an acceptance record produced by a run, kept small enough to read.
Full run directories (waveforms, build trees, per-job logs) stay outside the
repository; these records name their inputs by SHA-256 so a number can be traced
back to the artifact that produced it.

| File | What it covers |
| --- | --- |
| `pilot-manifest.json` | Seed 7301 W5M pilot: 30 model jobs, per-job wall time and trace hash |
| `pilot-determinism.json` | The seven pilot jobs re-run after the launch fix, compared field by field |
| `g1-legacy-compare.json` | Seed 7291 model replay against the frozen W5M RTL results |
| `a2-short-window-scope.json` | W256 RTL/model comparison for three policies across five cases |
| `a2-lint-scope.json` | The strict lint configurations used for those builds |
| `a3-main-geq.json` | Four Main W5M anchors against model replays of the same job specification |

The human-readable acceptance summaries live in `docs/reviews/`.
