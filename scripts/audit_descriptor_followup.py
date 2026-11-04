"""Independent raw-evidence audit for the owner-scoped N4 follow-up (no simulator/model import)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').exists())
PHASES = ('warmup', 'measurement', 'drain')
POLICIES = ('FCFS', 'RR', 'FAI_MAIN')
STAGES = ('generation_to_acceptance', 'acceptance_to_fire', 'generation_to_fire')
LOADS = ('load030', 'load090', 'load120', 'ready075')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def hist(h):
    samples = sorted((int(k), v) for k, v in h['histogram'].items())
    require(all(k >= 0 and isinstance(v, int) and v > 0 for k, v in samples), 'invalid histogram bins')
    count = sum(v for _, v in samples)
    total = sum(k * v for k, v in samples)
    require(h['count'] == count and h['distinct_values'] == len(samples), 'histogram count')
    require(h['mean'] == (total / count if count else None), 'histogram mean')
    require(h['min'] == (samples[0][0] if count else None) and h['max'] == (samples[-1][0] if count else None), 'histogram extrema')
    p99 = None
    if count:
        rank, cumulative = (99 * count + 99) // 100, 0
        for k, v in samples:
            cumulative += v
            if cumulative >= rank:
                p99 = k
                break
    require(h['p99_nearest_rank'] == p99, 'histogram P99')
    return count, total


def all_histograms(value):
    if isinstance(value, dict):
        if 'histogram' in value:
            hist(value)
        else:
            for child in value.values():
                all_histograms(child)
    elif isinstance(value, list):
        for child in value:
            all_histograms(child)


def validate(d, infrastructure=False, sensitivity=False):
    require(d['schema'] == 'cxl-descriptor-followup-v1', 'schema')
    policy = d['policy_param']
    require(policy in range(3) and d['policy'] == POLICIES[policy] and d['n_src'] == 4, 'policy/N')
    require(d['infrastructure_only'] is infrastructure, 'wrong infrastructure scope')
    require(not (infrastructure and sensitivity), 'conflicting evidence scopes')
    require(d['case'] in (('placement',) if sensitivity else (*LOADS, 'finite', 'trained')), 'case')
    if sensitivity:
        require(d.get('sensitivity_evidence') is True and d['production_evidence'] is False,
                'sensitivity evidence labels')
        require((d['window'], d['warmup_cycles'], d['measurement_cycles']) == (256, 512, 240),
                'short-window sensitivity lengths')
    elif not infrastructure:
        require(d['window'] == 5000000, 'production window changed')
        expected = (10000000, 100000) if d['case'] == 'trained' else (0, 1024) if d['case'] == 'finite' else (10000, 100000)
        require((d['warmup_cycles'], d['measurement_cycles']) == expected, 'wrong full length')
    require(d['production_evidence'] is (d['case'] == 'trained' and not infrastructure), 'production label')
    require(d['outstanding_after_drain'] == d['generated_unaccepted_after_drain'] == 0, 'incomplete drain')
    require(d['drain_cycles'] <= d['drain_bound'], 'drain bound')
    all_histograms(d['metrics'])
    m = d['metrics']
    rows = m['phases']
    require(set(rows) == set(PHASES), 'phase set')
    require(rows['warmup']['cycles'] == d['warmup_cycles'] and rows['measurement']['cycles'] == d['measurement_cycles'], 'phase length')
    require(rows['drain']['cycles'] == d['drain_cycles'], 'drain length')
    require(sum(r['cycles'] for r in rows.values()) == d['real_non_reset_cycles'], 'actual cycle total')
    for phase, r in rows.items():
        cycles = r['cycles']
        for key in ('generated', 'accepted', 'fired'):
            require(len(r[key]) == 4 and all(isinstance(x, int) and x >= 0 for x in r[key]), 'per-source count')
        require(r['fires'] == sum(r['fired']) == r['eligible_ready'], 'fire eligibility/bubbles')
        require(r['avoidable_bubbles'] == 0 and r['idle_ready'] == r['ready'] - r['fires'], 'ready accounting')
        require(r['fires'] <= r['ready'] <= cycles, 'ready range')
        require(r['successful_slot_utilization'] == (r['fires'] / cycles if cycles else None), 'slot denominator')
        require(r['ready_opportunity_utilization'] == (r['fires'] / r['ready'] if r['ready'] else None), 'ready denominator')
        require(r['fires'] + r['idle_ready'] + r['output_stall_cycles'] + r['idle_not_ready'] == cycles, 'cycle partition')
        for h in range(4):
            require(r['occupancy'][h]['count'] == r['producer_backlog'][h]['count'] == cycles, 'state samples')
            require(r['occupancy'][h]['max'] is None or r['occupancy'][h]['max'] <= 16, 'FIFO depth')
            require(0 <= r['fifo_nonempty_ready'][h] <= r['fifo_nonempty'][h] <= cycles, 'eligible source cycles')
            for gap in r['gaps'][h]['samples'].values():
                wall, ready = gap['wall_cycles'], gap['eligible_ready_opportunities']
                require(wall['count'] == ready['count'], 'gap pairing')
                require(hist(ready)[1] <= hist(wall)[1], 'gap excludes sink stalls')
    for h in range(4):
        gen = sum(rows[p]['generated'][h] for p in PHASES)
        acc = sum(rows[p]['accepted'][h] for p in PHASES)
        fired = sum(rows[p]['fired'][h] for p in PHASES)
        require(gen == acc == fired == d['trace_generated_per_source'][h], 'per-source whole population')
    total = sum(d['trace_generated_per_source'])
    require(total == d['responses']['issued'] == d['responses']['completed'], 'response conservation')
    require(rows['drain']['generated'] == [0] * 4, 'generation continued during drain')
    for axis, count_key in (('generation', 'generated'), ('acceptance', 'accepted')):
        for phase in PHASES:
            for h in range(4):
                latency = m['latency_by_cohort'][axis][phase][h]
                require(all(latency[s]['count'] == rows[phase][count_key][h] for s in STAGES), 'latency cohort population')
                a, b, direct = (hist(latency[s])[1] for s in STAGES)
                require(a + b == direct, 'direct latency sum across same population')
    completions = m['completion_cohorts']
    for h in range(4):
        for p in PHASES:
            require(sum(completions[p][a][f][h] for a in PHASES for f in PHASES) == rows[p]['generated'][h], 'generation completion matrix')
            require(sum(completions[g][p][f][h] for g in PHASES for f in PHASES) == rows[p]['accepted'][h], 'acceptance completion matrix')
            require(sum(completions[g][a][p][h] for g in PHASES for a in PHASES) == rows[p]['fired'][h], 'fire completion matrix')
    for name, snap in m['snapshots'].items():
        for h, row in enumerate(snap['per_source']):
            require(sum(v['count'] for v in row['producer_pending_by_generation'].values()) == snap['producer_backlog'][h], 'producer censor snapshot')
            require(sum(v['count'] for v in row['fifo_pending_by_acceptance'].values()) == snap['fifo_occupancy'][h], 'accept censor snapshot')
            require(sum(v['count'] for v in row['fifo_pending_generation_age'].values()) == snap['fifo_occupancy'][h], 'generation FIFO snapshot')
    require(m['snapshots']['drain_end']['fifo_occupancy'] == m['snapshots']['drain_end']['producer_backlog'] == [0]*4, 'drain end state')
    if d['case'] == 'finite':
        require(total == 4096 and d['trace_generated_per_source'] == [1024]*4, 'finite batch population')
    if d['case'] == 'trained':
        require(len(d['training_windows']) == 2, 'two training windows')
        for i, w in enumerate(d['training_windows']):
            require(w['closing_trace_cycle'] == (i+1)*d['window']-1, 'actual closing index')
            require(w['total'] == sum(w['counts']), 'training S=sumB')
            evidence = ['UP' if 40*b < 3*w['total'] else 'DOWN' if 4*b > w['total'] else 'KEEP' for b in w['counts']]
            require(w['evidence'] == evidence == ['DOWN','KEEP','KEEP','KEEP'], 'independent threshold')
            if policy == 2:
                require(w['classes'] == [['B_H','H','H','H'],['L','H','H','H']][i], 'literal expected classes')
        if policy == 2 and not infrastructure:
            c = d['contention']
            require(c['both_classes_eligible_cycles'] == c['post_fill_cycles'] == 100000-c['fill_cycles'], 'two-class actual contention')
            require(sum(c['per_source_fires_after_fill']) == c['post_fill_cycles'], 'post-fill service')
            require(all(c['complete_visits'][k] > 0 for k in ('High','Low')), 'class visits')
    return d


def table(path, rows):
    require(bool(rows), 'empty output table')
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runs', nargs=3, required=True, help='DF-controls DF-finite DF-trained run IDs')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    require(not args.output.exists() or not any(args.output.iterdir()), 'use fresh audit output')
    args.output.mkdir(parents=True, exist_ok=True)
    runs, phase_rows, source_rows, inputs, traces = [], [], [], [], {}
    matrices = {
        'DF-controls': {(c,p,s) for c in LOADS for p in range(3) for s in (509,510,511)},
        'DF-finite': {('finite',p,509) for p in range(3)},
        'DF-trained': {('trained',p,509) for p in range(3)},
    }
    for scope, run_id in zip(matrices, args.runs):
        base = ROOT/'artifacts/implementation'/scope/run_id
        summary, gate = read(base/'summary.json'), read(base/'followup_scope.json')
        require(summary['overall']=='PASS' and summary['milestone_acceptance_scope'] and not summary['sim_build_relaxations'], 'summary scope')
        require(gate['full_scope'] and not gate['infrastructure_only'] and not gate['problems'], 'full result gate')
        for step in summary['steps']:
            require(step['status']=='PASS', 'non-PASS execution step')
            if 'exit_codes' in step:
                require(all(v==0 for v in step['exit_codes'].values()), 'nonzero command exit')
            if 'junit' in step:
                xml = ET.parse(base/step['junit']).getroot()
                require(list(xml.iter('testcase')) and not any(list(xml.iter(t)) for t in ('failure','error','skipped')), 'raw JUnit')
        seen = set()
        for step in (s for s in summary['steps'] if s['kind']=='cocotb'):
            files = [base/p for p in step['artifacts'] if p.endswith('descriptor_followup_metrics.json')]
            require(len(files)==1, 'missing/extra metrics')
            f=files[0]
            d=validate(read(f))
            key=(d['case'],d['policy_param'],d['seed'])
            require(key not in seen, 'duplicate case')
            seen.add(key)
            tk=(d['case'],d['seed'])
            trace=(d['trace_sha256'],d['trace_config'],d['trace_generated_per_source'],d['trace_ready_cycles'])
            require(tk not in traces or traces[tk]==trace, 'mismatched exogenous stimulus')
            traces[tk]=trace
            inputs.append(dict(scope=scope,run_id=run_id,path=f.relative_to(ROOT).as_posix(),sha256=sha(f)))
            common=dict(case=d['case'],policy=d['policy'],seed=d['seed'])
            runs.append({**common,'warmup_cycles':d['warmup_cycles'],'measurement_cycles':d['measurement_cycles'],
                         'drain_cycles':d['drain_cycles'],'real_non_reset_cycles':d['real_non_reset_cycles'],
                         'trace_sha256':d['trace_sha256'],'total_generated':sum(d['trace_generated_per_source']),
                         'simulation_wall_s':d['total_wall_s'],'peak_rss_kib':d['peak_rss_kib']})
            for phase,r in d['metrics']['phases'].items():
                phase_rows.append({**common,'phase':phase,'cycles':r['cycles'],'generated':sum(r['generated']),
                                   'accepted':sum(r['accepted']),'fires':r['fires'],'ready':r['ready'],'idle_ready':r['idle_ready'],
                                   'stall_cycles':r['output_stall_cycles'],'avoidable_bubbles':r['avoidable_bubbles'],
                                   'successful_slot_utilization':r['successful_slot_utilization'],
                                   'ready_opportunity_utilization':r['ready_opportunity_utilization']})
                for h in range(4):
                    row={**common,'phase':phase,'source':h,'generated':r['generated'][h],'accepted':r['accepted'][h],
                         'fires':r['fired'][h],'service_share':r['fired'][h]/r['fires'] if r['fires'] else None,
                         'fifo_nonempty_cycles':r['fifo_nonempty'][h],'fifo_nonempty_ready':r['fifo_nonempty_ready'][h],
                         'occupancy_mean':r['occupancy'][h]['mean'],'producer_backlog_mean':r['producer_backlog'][h]['mean']}
                    for stage in STAGES:
                        for stat in ('count','mean','p99_nearest_rank','max'):
                            row['generation_cohort_'+stage+'_'+stat]=d['metrics']['latency_by_cohort']['generation'][phase][h][stage][stat]
                            row['acceptance_cohort_'+stage+'_'+stat]=d['metrics']['latency_by_cohort']['acceptance'][phase][h][stage][stat]
                    for kind in ('initial','inter_service','left_censored_completed','right_censored'):
                        gap=r['gaps'][h]['samples'].get(kind,{})
                        for unit in ('wall_cycles','eligible_ready_opportunities'):
                            for stat in ('count','mean','p99_nearest_rank','max'):
                                row[f'gap_{kind}_{unit}_{stat}']=gap.get(unit,{}).get(stat)
                    source_rows.append(row)
        require(seen==matrices[scope], 'exact matrix')
        require(gate['valid_runs']==gate['expected_runs']==len(seen), 'gate count')
    require(len(runs)==42 and len(traces)==14, 'full matrix total')
    table(args.output/'runs.csv',runs)
    table(args.output/'phases.csv',phase_rows)
    table(args.output/'per_source.csv',source_rows)
    audit=dict(status='PASS',actual_runs=len(runs),trace_groups=len(traces),inputs=inputs,
               real_non_reset_cycles=sum(r['real_non_reset_cycles'] for r in runs),
               warmup_cycles=sum(r['warmup_cycles'] for r in runs),
               measurement_cycles=sum(r['measurement_cycles'] for r in runs),
               drain_cycles=sum(r['drain_cycles'] for r in runs),
               claims='N4 mechanistic single-seed trained/finite comparisons; three control seeds; no application/steady-state/WCET inference')
    (args.output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {len(runs)} actual RTL runs;14 matching trace groups; all populations completed')


if __name__=='__main__':
    main()
