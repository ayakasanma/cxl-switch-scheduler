"""Read-only independent audit of heavy/sparse pin metrics and strict runner evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from audit_descriptor_followup import ROOT, all_histograms, hist, read, require, sha, table

POLICIES = ('FCFS', 'RR', 'FAI_MAIN')
PHASES = ('training', 'A', 'A_guard', 'B', 'B_guard', 'drain')
STAGES = ('generation_to_acceptance', 'acceptance_to_fire', 'generation_to_fire')


def pooled(hists):
    combined = Counter()
    for h in hists:
        hist(h)
        combined.update({int(k):v for k,v in h['histogram'].items()})
    count = sum(combined.values())
    total = sum(k*v for k,v in combined.items())
    cumulative, p99 = 0, None
    for k,v in sorted(combined.items()):
        cumulative += v
        if p99 is None and cumulative >= (99*count+99)//100:
            p99 = k
    return dict(count=count, mean=total/count if count else None,
                min=min(combined) if count else None, max=max(combined) if count else None,
                p99_nearest_rank=p99, distinct_values=len(combined),
                histogram={str(k):v for k,v in sorted(combined.items())})


def validate(d, pilot=False):
    require(d['schema'] == 'cxl-hog-sparse-v1', 'schema')
    policy, seed = d['policy_param'], d['seed']
    require(policy in range(3) and d['policy'] == POLICIES[policy] and seed in range(509,514), 'policy/seed')
    w = 256 if pilot else 5_000_000
    t, end = 2*w, 2*w+204448
    require(d['n_src'] == 4 and d['window'] == w and d['training_cycles'] == t and d['active_cycles'] == end,
            'N/window/timeline')
    require(d['trace_config'] == dict(generator='cxl-hog-sparse-traffic-v1',seed=seed,window=w,
            n_src=4,depth=16,desc_w=105,heavy_source=0,heavy_per_cycle=1,sparse_probability=[1,128],
            burst_size=8,burst_block_cycles=1024,burst_blocks=100,burst_offset_inclusive=[0,1023],ready=1,
            phase_cycles=dict(zip(PHASES[:-1],(t,100000,1024,102400,1024))),
            timing='cycle0 first nonreset; generate before edge; half-open phases',
            rng='independent arrival/offset/descriptor stream per source'), 'exogenous trace specification')
    require(d['params'] == dict(N_SRC=4,DEPTH=16,DESC_W=105,TS_W=32,RR_QUANTUM=10,FAI_W=w,POLICY=policy),
            'executed parameters')
    require(d['production_evidence'] is (not pilot) and d['sensitivity_evidence'] is pilot and
            d['infrastructure_only'] is False, 'evidence labels')
    require(d['trace_ready_cycles'] == d['heavy_generation_end'] == end and d['sparse_guard_complete'] is True,
            'background/ready/guard marker')
    require(d['cold_pin_cycles'] == t and len(d['cold_pin_sha256']) == len(d['trace_sha256']) == 64,
            'pin/trace digest scope')
    require(all(c in '0123456789abcdef' for c in d['trace_sha256']+d['cold_pin_sha256']), 'digest format')
    require(0 < d['drain_cycles'] <= d['drain_bound'] and d['real_non_reset_cycles'] == end+d['drain_cycles'],
            'real cycles/drain')
    require(d['outstanding_after_drain'] == d['generated_unaccepted_after_drain'] == 0, 'incomplete drain')
    m = d['metrics']
    all_histograms(m)
    rows = m['phases']
    require(set(rows) == set(PHASES), 'phase set')
    lengths = (t,100000,1024,102400,1024,d['drain_cycles'])
    gen, acc, fire = [0]*4, [0]*4, [0]*4
    names = ('training_end','A_end','A_guard_end','B_end','B_guard_end','drain_end')
    boundary = 0
    for phase,n,name in zip(PHASES,lengths,names):
        row = rows[phase]
        require(row['cycles'] == row['ready'] == n, 'phase length/ready')
        require(row['fires'] == sum(row['fired']) == row['eligible_ready'] and row['avoidable_bubbles'] == 0,
                'fire eligibility')
        require(row['fires']+row['idle_ready']+row['output_stall_cycles']+row['idle_not_ready'] == n and
                row['idle_ready'] == n-row['fires'] and row['output_stall_cycles'] == row['idle_not_ready'] == 0,
                'cycle partition')
        require(row['successful_slot_utilization'] == row['ready_opportunity_utilization'] == row['fires']/n,
                'utilization denominator')
        require(row['generated'][0] == (0 if phase == 'drain' else n), 'early heavy stop')
        if phase in ('A_guard','B_guard','drain'):
            require(row['generated'][1:] == [0]*3, 'new sparse work during guard/drain')
        if phase in ('A','B'):
            require(row['fires'] == n, 'measured capacity')
        for key in ('generated','accepted','fired'):
            require(len(row[key]) == 4 and all(type(v) is int and v >= 0 for v in row[key]), 'source event counts')
        for h in range(4):
            gen[h] += row['generated'][h]
            acc[h] += row['accepted'][h]
            fire[h] += row['fired'][h]
            occupancy, backlog = row['occupancy'][h], row['producer_backlog'][h]
            require(occupancy['count'] == backlog['count'] == n and occupancy['max'] <= 16, 'state samples')
            require(row['full'][h] == occupancy['histogram'].get('16',0), 'full occupancy samples')
            require(0 <= row['fifo_nonempty_ready'][h] == row['fifo_nonempty'][h] <= n, 'eligible cycles')
            require(backlog['min'] >= 0 and backlog['min'] <= backlog['mean'] <= backlog['max'] and
                    backlog['min'] <= backlog['end'] <= backlog['max'], 'backlog moments')
            for gap in row['gaps'][h]['samples'].values():
                require(gap['wall_cycles'] == gap['eligible_ready_opportunities'], 'ready1 gap units')
        boundary += n
        snap = m['snapshots'][name]
        require(snap['next_trace_cycle'] == boundary and
                snap['producer_backlog'] == [g-a for g,a in zip(gen,acc)] and
                snap['fifo_occupancy'] == [a-f for a,f in zip(acc,fire)], 'snapshot conservation')
        for h,s in enumerate(snap['per_source']):
            ages = s['all_pending_ages']
            require(ages['producer_generation_age']['count'] == snap['producer_backlog'][h] and
                    ages['fifo_generation_age']['count'] == ages['fifo_acceptance_age']['count'] == snap['fifo_occupancy'][h],
                    'pending ages population')
        if phase in ('A_guard','B_guard','drain'):
            require(snap['producer_backlog'][1:] == snap['fifo_occupancy'][1:] == [0]*3, 'sparse guard incomplete')
    require(gen == acc == fire == d['trace_generated_per_source'], 'whole source population')
    require(sum(gen) == d['responses']['issued'] == d['responses']['completed'], 'response population')
    require(gen[0] == end and rows['B']['generated'][1:] == [800]*3, 'offered heavy/burst population')
    require(m['snapshots']['drain_end']['producer_backlog'] == m['snapshots']['drain_end']['fifo_occupancy'] == [0]*4,
            'drain end state')
    require(set(m['cohorts']) == {'cold','A','B'}, 'cohort set')
    for cohort,c in m['cohorts'].items():
        require(c['generated_per_source'] == c['completed_per_source'] and c['completed_per_source'][0] == 0,
                'incomplete generation cohort')
        allowed = ('training',) if cohort == 'cold' else (cohort,cohort+'_guard')
        require(set(c['completed_by_phase']) == set(PHASES), 'completion phase set')
        require(all(not any(v) for p,v in c['completed_by_phase'].items() if p not in allowed),
                'completion after heavy-off/boundary')
        for h in range(4):
            require(sum(v[h] for v in c['completed_by_phase'].values()) == c['completed_per_source'][h],
                    'completion distribution')
            if cohort != 'cold':
                require(c['generated_per_source'][h] == (0 if h == 0 else rows[cohort]['generated'][h]),
                        'measured sparse cohort')
            elif pilot:
                require(c['generated_per_source'][h] == 0, 'pilot cold label')
            stage_totals = []
            for stage in STAGES:
                count,total = hist(c['per_source'][h][stage])
                require(count == c['completed_per_source'][h], 'cohort histogram population')
                stage_totals.append(total)
            require(stage_totals[0]+stage_totals[1] == stage_totals[2], 'direct latency identity')
        for stage in STAGES:
            require(c['pooled_sparse'][stage] == pooled([c['per_source'][h][stage] for h in (1,2,3)]),
                    'pooled sparse histogram')
        end_name = 'training_end' if cohort == 'cold' else cohort+'_guard_end'
        for h,s in enumerate(m['snapshots'][end_name]['per_source']):
            require(all(v['count'] == 0 for v in s['sparse_pending_by_generation_cohort'][cohort].values()),
                    'censored completion at guard')
        if cohort in ('A','B'):
            cut = m['snapshots'][cohort+'_end']
            for h,s in enumerate(cut['per_source']):
                ages = s['sparse_pending_by_generation_cohort'][cohort]
                count = ages['producer_generation_age']['count']+ages['fifo_generation_age']['count']
                require(count == c['generated_per_source'][h]-c['completed_by_phase'][cohort][h] and
                        ages['fifo_generation_age']['count'] == ages['fifo_acceptance_age']['count'], 'censor cut population')
    windows = d['windows']
    require(len(windows) == d['real_non_reset_cycles']//w and len(windows) >= 2, 'actual window count')
    for i,record in enumerate(windows):
        counts, total = record['counts'], record['total']
        require(record['closing_trace_cycle'] == (i+1)*w-1 and len(counts) == 4 and total == sum(counts),
                'window accounting')
        evidence = ['S0' if not total else 'UP' if 40*b < 3*total else 'DOWN' if 4*b > total else 'KEEP' for b in counts]
        require(record['evidence'] == evidence, 'independent threshold')
        if i < 2:
            require(evidence[0] == 'DOWN' and all(v != 'DOWN' for v in evidence[1:]), 'training class evidence')
    if policy == 2:
        require([r['classes'] for r in windows[:2]] == [['B_H','H','H','H'],['L','H','H','H']], 'natural training classes')
        if not pilot:
            for p in ('A','A_guard','B','B_guard'):
                require(m['main_contexts'][p]['class_maps'] == {'L/H/H/H':rows[p]['cycles']}, 'measured class map')
        for cohort,contexts in m['arrival_contexts'].items():
            require([sum(row.values()) for row in contexts] == m['cohorts'][cohort]['generated_per_source'], 'arrival context count')
            for row in contexts:
                for encoded,n in row.items():
                    ctx = json.loads(encoded)
                    require(n > 0 and ctx['turn'] in (0,1) and 0 <= ctx['used'] <= 10 and
                            ctx['remaining'] == 10-ctx['used'] and ctx['held'] == 0, 'passive quota context')
    return d


def audit(base, output, pilot=False):
    require(not output.exists() or not any(output.iterdir()), 'use fresh output')
    summary, gate = read(base/'summary.json'), read(base/'hog_sparse_scope.json')
    require(summary['overall'] == 'PASS' and not summary['sim_build_relaxations'], 'strict runner status')
    require(summary['milestone_acceptance_scope'] is (not pilot) and summary['production_evidence'] is (not pilot)
            and summary['sensitivity_evidence'] is pilot and summary['infrastructure_only'] is False,
            'summary evidence scope')
    count = 3 if pilot else 15
    require(gate['schema'] == 'cxl-hog-sparse-scope-v1' and gate['declared_matrix_complete'] and
            gate['full_scope'] is (not pilot) and gate['production_evidence'] is (not pilot) and
            gate['sensitivity_evidence'] is pilot and gate['infrastructure_only'] is False and
            not gate['problems'] and gate['valid_runs'] == gate['expected_runs'] == count and
            gate['paired_trace_groups'] == (1 if pilot else 5), 'complete scope gate')
    for step in summary['steps']:
        require(step['status'] == 'PASS', 'failed/incomplete execution step')
        require(all(v == 0 for v in step.get('exit_codes',{}).values()), 'nonzero process exit')
        if 'junit' in step:
            xml = ET.parse(base/step['junit']).getroot()
            require(list(xml.iter('testcase')) and not any(list(xml.iter(k)) for k in ('failure','error','skipped')), 'raw JUnit')
    expected = {(p,s) for p in range(3) for s in ((509,) if pilot else range(509,514))}
    seen, traces, cold, inputs, runs, profiles, sources = set(), {}, {}, [], [], [], []
    for step in (s for s in summary['steps'] if s['kind'] == 'cocotb'):
        paths = [base/p for p in step['artifacts'] if p.endswith('hog_sparse_metrics.json')]
        require(len(paths) == 1, 'metrics artifact')
        path = paths[0]
        d = validate(read(path),pilot)
        key = (d['policy_param'],d['seed'])
        require(key not in seen and key in expected, 'duplicate/unexpected job')
        seen.add(key)
        require(step['seed'] == d['seed'] and {**step['default_params'],**step['params']} == d['params'], 'actual runner parameters')
        trace = (d['trace_config'],d['trace_sha256'],d['trace_generated_per_source'],d['trace_ready_cycles'])
        require(d['seed'] not in traces or traces[d['seed']] == trace, 'different exogenous trace')
        traces[d['seed']] = trace
        cold[key] = d['cold_pin_sha256']
        inputs.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        common = dict(policy=d['policy'],seed=d['seed'])
        runs.append({**common,'real_non_reset_cycles':d['real_non_reset_cycles'],'drain_cycles':d['drain_cycles'],
                     'trace_sha256':d['trace_sha256'],'cold_pin_sha256':d['cold_pin_sha256'],
                     'generated_total':sum(d['trace_generated_per_source'])})
        for profile in ('cold','A','B'):
            c = d['metrics']['cohorts'][profile]
            row = {**common,'profile':profile,'sparse_generated':sum(c['generated_per_source']),
                   'sparse_completed':sum(c['completed_per_source'])}
            if profile in ('A','B'):
                phase = d['metrics']['phases'][profile]
                row.update(fires_per_cycle=phase['fires']/phase['cycles'],heavy_fires=phase['fired'][0],
                           heavy_fires_per_cycle=phase['fired'][0]/phase['cycles'],
                           heavy_backlog_mean=phase['producer_backlog'][0]['mean'],
                           heavy_backlog_end=d['metrics']['snapshots'][profile+'_end']['producer_backlog'][0])
            for stage in STAGES:
                for field in ('count','mean','p99_nearest_rank','max'):
                    row[stage+'_'+field] = c['pooled_sparse'][stage][field]
            profiles.append(row)
            for h in (1,2,3):
                r = {**common,'profile':profile,'source':h,'generated':c['generated_per_source'][h],
                     'completed':c['completed_per_source'][h]}
                for stage in STAGES:
                    for field in ('mean','p99_nearest_rank','max'):
                        r[stage+'_'+field] = c['per_source'][h][stage][field]
                sources.append(r)
    require(seen == expected, 'incomplete exact matrix')
    for seed in traces:
        require(cold[(0,seed)] == cold[(2,seed)], 'pre-classification FCFS/Main actual pins differ')
    before, after = read(base/'source_hashes_before.json'), read(base/'source_hashes_after.json')
    require(before == after, 'source changed during execution')
    runtime = {p:h for p,h in before.items() if Path(p).suffix != '.md' and not Path(p).name.startswith(('audit_','test_audit_'))}
    require(all(sha(ROOT/p) == h for p,h in runtime.items()), 'simulation sources changed after execution')
    output.mkdir(parents=True,exist_ok=True)
    table(output/'runs.csv',runs)
    # Cold rows deliberately lack throughput fields. Use union columns for heterogeneous cohorts.
    columns = list(dict.fromkeys(k for r in profiles for k in r))
    table(output/'profiles.csv',[{k:r.get(k) for k in columns} for r in profiles])
    table(output/'sources.csv',sources)
    deltas = []
    by_key = {(r['policy'],r['seed'],r['profile']):r for r in profiles}
    for seed in traces:
        for profile in ('A','B'):
            main = by_key[('FAI_MAIN',seed,profile)]
            for baseline in ('FCFS','RR'):
                other = by_key[(baseline,seed,profile)]
                p99 = 'generation_to_fire_p99_nearest_rank'
                require(main['sparse_generated'] == other['sparse_generated'], 'different sparse population')
                delta = other[p99]-main[p99]
                deltas.append(dict(seed=seed,profile=profile,baseline=baseline,baseline_p99=other[p99],main_p99=main[p99],
                                   reduction_cycles=delta,reduction_percent=100*delta/other[p99]))
    table(output/'paired.csv',deltas)
    result = dict(status='PASS',actual_runs=len(runs),matched_trace_groups=len(traces),pilot=pilot,
                  real_non_reset_cycles=sum(r['real_non_reset_cycles'] for r in runs),
                  training_cycles=len(runs)*(512 if pilot else 10_000_000),
                  measured_cycles=len(runs)*202400,guard_cycles=len(runs)*2048,
                  drain_cycles=sum(r['drain_cycles'] for r in runs),inputs=inputs,
                  interpretation='paired five-seed descriptive comparison only; benefit not a correctness gate')
    (output/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'inputs'}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',required=True)
    ap.add_argument('--pilot',action='store_true')
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    audit(ROOT/'artifacts/implementation'/('HS-pilot' if args.pilot else 'HS-main')/args.run,args.output,args.pilot)
