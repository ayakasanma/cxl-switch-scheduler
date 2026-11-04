"""Plot independently audited RTL tails and the explicitly qualified offline design screen."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['svg.hashsalt'] = 'cxl-main-sq-diagnosis-v1'

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--audit',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
args = ap.parse_args()
data = json.loads(args.audit.read_text())
assert data['status']=='PASS' and data['window'] in (256,5_000_000)
args.output.mkdir(parents=True,exist_ok=True)
main = data['results'][2]
screens = main['software_fixed_slot_screen']
chosen = [next(r for r in screens if r['quantum']==q and r['initial_pointer']==1) for q in (1,2)]
for q,row in zip((1,2),chosen):
    assert all(r['pooled']==row['pooled'] and r['per_source']==row['per_source'] for r in screens if r['quantum']==q), 'pointer variation requires explicit presentation'

fig,(ax,wait) = plt.subplots(2,1,figsize=(8.2,7),layout='constrained')
names = ['Source 1','Source 2','Source 3','Pooled']
rows = [(r['policy'].replace('FAI_MAIN','Main').replace('RR','RR10'),r['actual_rtl'],False) for r in data['results']]
rows += [(f'SQ{q} offline',row,True) for q,row in zip((1,2),chosen)]
colors = ['#0072B2','#009E73','#D55E00','#CC79A7','#E69F00']
for i,((label,row,offline),color) in enumerate(zip(rows,colors)):
    ys = [row['per_source'][str(h)]['p99'] for h in (1,2,3)]+[row['pooled']['p99']]
    ax.bar([x+(i-2)*.15 for x in range(4)],ys,width=.145,label=label,color=color,
           hatch='///' if offline else None,edgecolor='white',linewidth=.5)
ax.set(xticks=range(4),xticklabels=names,ylabel='Generation-to-fire P99 (cycles)')
ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=5,frameon=False,fontsize=9)
ax.grid(axis='y',alpha=.15)
ax.set_axisbelow(True)

tail = main['representative_tail'][:6]
components = [('g2a','Producer serialization','#BBBBBB'),('predecessor_fires','Own-source predecessor fires','#0072B2'),
              ('low','Low fires while waiting','#D55E00'),('other','Other High fires while waiting','#009E73'),
              ('own','Own successful fire','#555555')]
bottom = [0]*len(tail)
for key,label,color in components:
    heights = [r['head_low']+r['nonhead_low'] if key=='low' else r['head_other']+r['nonhead_other'] if key=='other' else 1 if key=='own' else r[key] for r in tail]
    wait.bar(range(len(tail)),heights,bottom=bottom,label=label,color=color,width=.66)
    bottom = [a+b for a,b in zip(bottom,heights)]
assert bottom==[r['g2f'] for r in tail]
wait.set(xticks=range(len(tail)),xticklabels=[f"s{r['source']} / tag {r['tag']}" for r in tail],ylabel='Generation-to-fire latency (cycles)')
wait.tick_params(axis='x',labelsize=8)
wait.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
wait.grid(axis='y',alpha=.15)
wait.set_axisbelow(True)
window = 'W5M production replay' if data['window']==5_000_000 else 'W256 infrastructure pilot'
fig.suptitle(f'N4 / seed 509 / {window}\nSQ bars are offline fixed-slot screens, not candidate RTL measurements',fontsize=11)
fig.supxlabel('Top: nearest-rank per-run P99, no error bars. Bottom: six longest observed Main requests.\nWait components are request-cycle exposures; one grant may delay several requests.',fontsize=9)
svg = args.output/'diagnosis.svg'
fig.savefig(svg,metadata={'Date':None})
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
fig.savefig(args.output/'diagnosis.png',dpi=160)
print('PASS: source-backed diagnostic figure, no inferred candidate RTL result')
