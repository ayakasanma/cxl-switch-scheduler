"""Independent source-placement sensitivity audit; reads actual runner/JUnit/pin metrics."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from audit_descriptor_followup import ROOT, read, require, sha, table, validate


SUBSETS = tuple(s for k in (1, 2, 3) for s in combinations(range(4), k))


def mechanism(counts, low):
    """Two partial ten-fire class visits bound class skew by20, not a fitted tolerance."""
    require(len(counts) == 4 and all(isinstance(v, int) and v >= 0 for v in counts), 'service counts')
    require(tuple(low) in SUBSETS, 'Low subset')
    high = tuple(h for h in range(4) if h not in low)
    totals = [sum(counts[h] for h in group) for group in (low, high)]
    require(abs(totals[0]-totals[1]) <= 20, 'class quota count bound')
    # Equal-demand empty-start streams and oldest-first service: allow the two cut boundaries.
    for group in (low, high):
        require(max(counts[h] for h in group)-min(counts[h] for h in group) <= 2,
                'within-class source count bound')
    return totals


def validate_placement(d):
    validate(d, sensitivity=True)
    low = tuple(d['low_sources'])
    require(low in SUBSETS, 'Low subset')
    require(d['seed'] == 509 and d['window'] == 256, 'sensitivity parameters')
    expected_counts = [102 // len(low) if h in low else 12 for h in range(4)]
    cfg = d['trace_config']
    require(cfg == dict(generator='descriptor-placement-traffic-v1', case='placement', seed=509,
                        warmup=512, measurement=240, window=256, n_src=4, low_sources=list(low),
                        training_counts=expected_counts, quiet_closing_cycles=4, fill_cycles=128,
                        measured_generation_per_source_per_cycle=1, ready=1), 'trace configuration')
    require(d['trace_generated_per_source'] == [2*x+240 for x in expected_counts], 'generated population')
    require(d['trace_ready_cycles'] == 752, 'ready trace')
    windows = d['training_windows']
    require(len(windows) == 2, 'training windows')
    for i, w in enumerate(windows):
        require(w['closing_trace_cycle'] == (i+1)*256-1, 'actual closing cycle')
        require(w['counts'] == expected_counts and w['total'] == sum(expected_counts), 'training counters')
        evidence = ['UP' if 40*b < 3*w['total'] else 'DOWN' if 4*b > w['total'] else 'KEEP'
                    for b in w['counts']]
        require(w['evidence'] == evidence == ['DOWN' if h in low else 'KEEP' for h in range(4)],
                'independent threshold classification')
        if d['policy_param'] == 2:
            require(w['classes'] == [('B_H' if i == 0 else 'L') if h in low else 'H' for h in range(4)],
                    'class placement')
    m = d['metrics']['phases']['measurement']
    require(m['generated'] == [240]*4 and m['fires'] == 239 and m['ready'] == 240,
            'equal measured demand/capacity')
    require(all(v >= 112 for v in m['fifo_nonempty_ready']), 'source eligibility')
    start = d['metrics']['snapshots']['measurement_start']
    require(start['fifo_occupancy'] == start['producer_backlog'] == [0]*4, 'empty measurement start')
    if d['policy_param'] == 2:
        c = d['contention']
        require(c['fill_cycles'] == 128 and c['post_fill_cycles'] == c['both_classes_eligible_cycles'] == 112,
                'both-class post-fill eligibility')
        counts = c['per_source_fires_after_fill']
        require(sum(counts) == 112, 'post-fill transfer population')
        mechanism(counts, low)
        for suffix, values in (('measurement', m['fired']), ('after_fill', counts)):
            totals = {name:sum(values[h] for h in group)
                      for name,group in (('Low',low),('High',tuple(h for h in range(4) if h not in low)))}
            require(c['class_fires_'+suffix] == totals and
                    c['class_share_'+suffix] == {name:v/sum(values) for name,v in totals.items()},
                    'class summary arithmetic')
        require(all(c['complete_visits'][name] > 0 for name in ('High', 'Low')), 'complete class visits')
    return low


def audit(base, output):
    require(not output.exists() or not any(output.iterdir()), 'use fresh output')
    summary, gate = read(base/'summary.json'), read(base/'followup_scope.json')
    require(summary['overall'] == 'PASS' and summary['milestone_acceptance_scope'], 'accepted scope')
    require(not summary['sim_build_relaxations'] and not summary['infrastructure_only'] and
            not summary['production_evidence'], 'runner evidence labels')
    require(gate['full_scope'] and not gate['problems'] and gate['valid_runs'] == gate['expected_runs'] == 42,
            'full matrix gate')
    for step in summary['steps']:
        require(step['status'] == 'PASS', 'failed/incomplete step')
        require(all(v == 0 for v in step.get('exit_codes', {}).values()), 'nonzero command exit')
        if 'junit' in step:
            xml = ET.parse(base/step['junit']).getroot()
            require(list(xml.iter('testcase')) and not any(list(xml.iter(k)) for k in ('failure', 'error', 'skipped')),
                    'raw JUnit')
    seen, traces, inputs, runs, sources = set(), {}, [], [], []
    for step in (s for s in summary['steps'] if s['kind'] == 'cocotb'):
        files = [base/p for p in step['artifacts'] if p.endswith('descriptor_followup_metrics.json')]
        require(len(files) == 1, 'metrics artifact')
        path = files[0]
        d = read(path)
        low = validate_placement(d)
        params = {**step['default_params'], **step['params']}
        require(params['N_SRC'] == 4 and params['POLICY'] == d['policy_param'] and
                params['FAI_W'] == 256 and params['RR_QUANTUM'] == 10 and step['seed'] == 509,
                'executed parameters')
        key = (low, d['policy_param'])
        require(key not in seen, 'duplicate case')
        seen.add(key)
        trace = (d['trace_sha256'], d['trace_config'], d['trace_generated_per_source'])
        require(low not in traces or traces[low] == trace, 'different exogenous trace across policies')
        traces[low] = trace
        inputs.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
        m = d['metrics']['phases']['measurement']
        counts = m['fired']
        jain = sum(counts)**2/(4*sum(v*v for v in counts))
        common = dict(low_sources=','.join(map(str, low)), low_count=len(low), policy=d['policy'])
        runs.append({**common, 'fires_per_cycle': m['fires']/m['cycles'], 'jain_equal_demand': jain,
                     'low_service_share': sum(counts[h] for h in low)/m['fires'],
                     'real_non_reset_cycles': d['real_non_reset_cycles'], 'drain_cycles': d['drain_cycles'],
                     'trace_sha256': d['trace_sha256'], 'avoidable_bubbles': m['avoidable_bubbles']})
        for h in range(4):
            row = {**common, 'source': h, 'class': ('Low' if h in low else 'High') if d['policy_param'] == 2 else 'N/A',
                   'generated': m['generated'][h], 'accepted': m['accepted'][h], 'fired': counts[h],
                   'service_share': counts[h]/m['fires'], 'fifo_nonempty_ready': m['fifo_nonempty_ready'][h],
                   'occupancy_mean': m['occupancy'][h]['mean'],
                   'producer_backlog_mean': m['producer_backlog'][h]['mean']}
            row['post_fill_fired'] = d['contention']['per_source_fires_after_fill'][h] if d['policy_param'] == 2 else None
            for kind in ('initial','inter_service','left_censored_completed','right_censored'):
                gap = m['gaps'][h]['samples'].get(kind, {})
                for unit in ('wall_cycles','eligible_ready_opportunities'):
                    for stat in ('count','mean','p99_nearest_rank','max'):
                        row[f'gap_{kind}_{unit}_{stat}'] = gap.get(unit, {}).get(stat)
            for axis in ('generation', 'acceptance'):
                for stage, hist in d['metrics']['latency_by_cohort'][axis]['measurement'][h].items():
                    for stat in ('mean', 'p99_nearest_rank', 'max'):
                        row[f'{axis}_{stage}_{stat}'] = hist[stat]
            sources.append(row)
    require(seen == {(s, p) for s in SUBSETS for p in range(3)} and len(traces) == 14, 'exact matrix')
    source_before = read(base/'source_hashes.json')
    runtime = {p:digest for p,digest in source_before.items()
               if Path(p).suffix != '.md' and not Path(p).name.startswith(('audit_', 'test_audit_'))}
    require(all(sha(ROOT/p) == digest for p, digest in runtime.items()), 'simulation source changed after execution')
    output.mkdir(parents=True, exist_ok=True)
    table(output/'runs.csv', runs)
    table(output/'per_source.csv', sources)
    result = dict(status='PASS', actual_runs=len(runs), matched_trace_groups=len(traces),
                  real_non_reset_cycles=sum(r['real_non_reset_cycles'] for r in runs),
                  warmup_cycles=42*512, measurement_cycles=42*240,
                  drain_cycles=sum(r['drain_cycles'] for r in runs),
                  evidence_scope='N4 W256 finite sensitivity, not production or statistical replication', inputs=inputs)
    (output/'audit.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    audit(ROOT/'artifacts/implementation/DF-placement'/args.run, args.output)
