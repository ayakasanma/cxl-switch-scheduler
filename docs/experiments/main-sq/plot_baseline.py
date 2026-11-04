"""Reproduce the accepted representative burst-tail figure; no new RTL results."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['svg.hashsalt'] = 'cxl-main-sq-baseline-v1'

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
audit = json.loads((ROOT/'docs/performance/hog-sparse-audit.json').read_text())
hashes = {row['path']:row['sha256'] for row in audit['inputs']}
fig, ax = plt.subplots(figsize=(6.4, 3.1), layout='constrained')
for policy, name, color in [(0,'FCFS','#0072B2'),(1,'RR10','#009E73'),(2,'Main','#D55E00')]:
    path = f'artifacts/implementation/HS-main/20261022T034507Z_311/results/cocotb_hs_p{policy}_w5000000_seed509__hog_sparse_metrics.json'
    raw = (ROOT/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == hashes[path], 'accepted input changed'
    data = json.loads(raw)['metrics']['cohorts']['B']['pooled_sparse']['generation_to_fire']
    hist = sorted((int(k),v) for k,v in data['histogram'].items())
    assert sum(v for _,v in hist) == data['count'] == 2400
    cumulative, x, y = 0, [0], [1.0]
    for value, count in hist:
        cumulative += count
        x.append(value)
        y.append(1-cumulative/data['count'])
    ax.step(x,y,where='post',label=f"{name} (P99={data['p99_nearest_rank']})",color=color)
ax.axhline(.01,color='#888888',linestyle=':',linewidth=.8)
ax.set(xlim=(0,46),ylim=(0,.08),xlabel='Generation-to-fire latency (cycles)',
       ylabel='Fraction with latency > x', title='Accepted N4 burst cohort, seed 509 (2,400 sparse requests)')
ax.grid(alpha=.2)
fig.legend(loc='outside upper center',ncol=3,frameon=False)
svg = HERE/'baseline_burst_tail.svg'
fig.savefig(svg,metadata={'Date':None})
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
fig.savefig(HERE/'baseline_burst_tail.png',dpi=160)
print('PASS: accepted hashes/counts; figure is archive evidence, zero new RTL cycles')
