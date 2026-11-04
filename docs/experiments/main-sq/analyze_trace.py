"""Independent trace audit and fixed-service-slot SQ design screen, NOT candidate RTL evidence."""
import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def stats(values):
    values = sorted(values)
    if not values:
        return dict(count=0,mean=None,max=None,p50=None,p95=None,p99=None,histogram={})
    n = len(values)
    return dict(count=n, mean=sum(values)/n, max=values[-1],
                **{f'p{p}':values[(p*n+99)//100-1] for p in (50,95,99)},
                histogram=dict(sorted(Counter(values).items())))


def observed(rows):
    queues = [deque() for _ in range(4)]
    producers = [deque() for _ in range(4)]
    requests = {}
    for row in rows:
        k = row['k']
        for h,t in row['gen']:
            assert t not in requests
            requests[t] = dict(source=h,tag=t,generation=k,head_low=0,head_other=0,
                               nonhead_low=0,nonhead_other=0,predecessor_fires=0)
            producers[h].append(t)
        for h in (1,2,3):
            assert len(queues[h]) == row['occ'][h]
            assert (queues[h][0] if queues[h] else None) == row['heads'][h]
            assert len(producers[h]) == row['pending'][h]
            for index,t in enumerate(queues[h]):
                r = requests[t]
                assert row['fire'] == 1
                src = row['src']
                if not index and src == h:
                    continue
                if index and src == h:
                    r['predecessor_fires'] += 1
                else:
                    r[('nonhead_' if index else 'head_')+('low' if src == 0 else 'other')] += 1
        if row['fire'] and row['src'] != 0:
            t = queues[row['src']].popleft()
            assert t == row['tag']
            requests[t]['fire'] = k
        for h,t in row['acc']:
            if h:
                assert row['in_ready'] >> h & 1 and row['occ'][h] < 16
                assert producers[h].popleft() == t
                requests[t]['acceptance'] = k
                queues[h].append(t)
    assert all(not q for q in queues+producers)
    for r in requests.values():
        r['g2a'] = r['acceptance']-r['generation']
        r['a2f'] = r['fire']-r['acceptance']
        r['g2f'] = r['fire']-r['generation']
        assert r['g2f'] == r['g2a']+r['head_low']+r['head_other']+r['nonhead_low']+r['nonhead_other']+r['predecessor_fires']+1
    return requests


def shadow(rows, requests, quantum, pointer):
    """Same observed High slots and sparse admissions; persistent RR source turn across visits.

    This intentionally isolates in-class order. It does NOT model training, new classification,
    a synthesizable implementation, or any claim of five-policy RTL performance.
    """
    assert quantum in (1,2) and pointer in (1,2,3)
    queues = [deque() for _ in range(4)]
    used, finished, peak = 0, {}, [0]*4
    for row in rows:
        k = row['k']
        chosen = None
        if row['ctx']['charged'] and row['ctx']['charged'][0] == 'High':
            assert row['fire'] == 1
            choices = [1+(pointer-1+i)%3 for i in range(3)]
            chosen = next((h for h in choices if queues[h]),None)
            assert chosen is not None, 'observed High slot unavailable in shadow'
            if chosen != pointer:
                used = 0
            t = queues[chosen].popleft()
            assert t not in finished
            finished[t] = k
            used += 1
        # Ready is pre-edge: same-edge pop does not permit an otherwise-full admission.
        for h,t in row['acc']:
            if h:
                pre = len(queues[h])+int(chosen == h)
                assert pre < 16, 'fixed-admission assumption invalid: shadow FIFO full'
                queues[h].append(t)
                peak[h] = max(peak[h],len(queues[h]))
        if chosen is not None:
            if used == quantum or not queues[chosen]:
                pointer,used = 1+chosen%3,0
            else:
                pointer = chosen
    assert set(finished) == set(requests) and all(not q for q in queues)
    assert sum(finished.values()) == sum(r['fire'] for r in requests.values()), 'slot-sum invariant failed'
    result = dict(quantum=quantum, fifo_peak=peak, pooled=stats([f-requests[t]['generation'] for t,f in finished.items()]),
                  per_source={h:stats([f-requests[t]['generation'] for t,f in finished.items() if requests[t]['source']==h]) for h in (1,2,3)})
    return result


def audit(run,output):
    summary = json.loads((run/'summary.json').read_text())
    assert summary['overall'] == 'PASS' and not summary['sim_build_relaxations']
    for step in summary['steps']:
        assert step['status'] == 'PASS'
        if 'exit_codes' in step:
            assert step['exit_codes'] and all(v == 0 for v in step['exit_codes'].values())
        if 'junit' in step:
            xml = ET.parse(run/step['junit'])
            cases = xml.findall('.//testcase')
            assert cases and not xml.findall('.//failure') and not xml.findall('.//error') and not xml.findall('.//skipped')
    assert json.loads((run/'source_hashes_before.json').read_text()) == json.loads((run/'source_hashes_after.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    results,inputs,paired,grants = [],[],{},{}
    for policy in range(3):
        files = list((run/'results').glob(f'cocotb_msq_p{policy}_w*_seed509__main_sq_diagnosis.json'))
        assert len(files) == 1
        path = files[0]
        diag = json.loads(path.read_text())
        metrics_path = path.with_name(path.name.replace('main_sq_diagnosis.json','hog_sparse_metrics.json'))
        metrics = json.loads(metrics_path.read_text())
        root = Path(__file__).resolve().parents[3]
        old_scope,old_id = ('HS-pilot','20261022T034155Z_369') if diag['window']==256 else ('HS-main','20261022T034507Z_311')
        original_path = root/'artifacts/implementation'/old_scope/old_id/'results'/f"cocotb_hs_p{policy}_w{diag['window']}_seed509__hog_sparse_metrics.json"
        packaged = run/'reference'/original_path.name
        if packaged.is_file():
            original_path = packaged
        if diag['window']==5_000_000:
            anchors = json.loads((root/'docs/performance/hog-sparse-audit.json').read_text())['inputs']
            anchor = next(r['sha256'] for r in anchors if Path(r['path']).name==original_path.name)
            assert hashlib.sha256(original_path.read_bytes()).hexdigest()==anchor, 'accepted reference hash changed'
        original = json.loads(original_path.read_text())
        volatile = ('active_wall_s','total_wall_s','peak_rss_kib')
        assert {k:v for k,v in metrics.items() if k not in volatile} == {k:v for k,v in original.items() if k not in volatile}
        assert diag['trace_sha256'] == metrics['trace_sha256']
        trace = path.with_name(path.name.replace('main_sq_diagnosis.json','main_sq_trace.jsonl.gz'))
        with gzip.open(trace,'rb') as f:
            raw = f.read()
        assert hashlib.sha256(raw).hexdigest() == diag['trace']['sha256_uncompressed']
        rows = [json.loads(line) for line in raw.splitlines()]
        grants[policy] = (diag['b_start'],[(r['src'],r['ctx'].get('charged')) for r in rows])
        assert len(rows) == diag['trace']['rows'] == diag['trace_end']-diag['b_start']
        assert [r['k'] for r in rows] == list(range(diag['b_start'],diag['trace_end']))
        req = observed(rows)
        paired[policy] = req
        bytag = {r['tag']:r for r in diag['per_request']}
        assert set(req) == set(bytag) and len(req) == 2400
        for t,r in req.items():
            native = bytag[t]
            assert all(r[k] == native[k] for k in ('source','generation','acceptance','fire'))
            assert r['head_low'] == native['head_fires_heavy']
            assert r['head_other'] == native['head_fires_other_sparse']
            assert r['nonhead_low'] == native['nonhead_fires_heavy']
            assert r['nonhead_other'] == native['nonhead_fires_other_sparse']
            assert r['predecessor_fires'] == native['nonhead_fires_same_source']
        quant = stats([r['g2f'] for r in req.values()])
        assert quant['p99'] == diag['direct_g2f_p99_nearest_rank']
        assert {int(k):v for k,v in diag['pooled']['generation_to_fire']['histogram'].items()} == quant['histogram']
        tail = [r for r in req.values() if r['g2f'] >= quant['p99']]
        result = dict(policy=diag['policy'],actual_rtl=dict(pooled=quant,per_source={h:stats([r['g2f'] for r in req.values() if r['source']==h]) for h in (1,2,3)}),
                      tail_requests=len(tail),tail_components={k:sum(r[k] for r in tail) for k in ('g2a','head_low','head_other','nonhead_low','nonhead_other','predecessor_fires','g2f')},
                      representative_tail=sorted(tail,key=lambda r:(-r['g2f'],r['tag']))[:8])
        result['actual_rtl']['stages'] = {
            key:dict(pooled=stats([r[key] for r in req.values()]),
                     per_source={h:stats([r[key] for r in req.values() if r['source']==h]) for h in (1,2,3)})
            for key in ('g2a','a2f','g2f')}
        if policy == 2:
            assert all(r['ctx']['classes'] == ['L','H','H','H'] for r in rows), 'fixed-class screen invalid'
            assert all(r['ctx']['charged'][0] == ('Low' if r['src'] == 0 else 'High') for r in rows)
            matched = 0
            for row in rows:
                if row['ctx']['charged'][0] == 'High':
                    oldest = min((req[t]['acceptance'],h,t) for h,t in enumerate(row['heads']) if h and t is not None)
                    assert (row['src'],row['tag']) == oldest[1:], 'oldest-head positive control failed'
                    matched += 1
            assert matched == len(req)
            result['oldest_head_positive_control_matches'] = matched
            visits,visit_sizes,events,limited = [],Counter(),Counter(),[]
            unused,max_run,run_length,last = 0,0,0,None
            for row in rows:
                cls,used = row['ctx']['charged']
                event = row['ctx']['visit_event']
                events[f'{cls}/{event}'] += 1
                multiple = sum(n>0 for n in row['occ'][1:])>=2
                if cls=='High':
                    assert used == len(visits), 'High visit context discontinuity'
                    visits.append(row['k'])
                    if multiple:
                        run_length = run_length+1 if last==(row['k']-1,row['src']) else 1
                        last = (row['k'],row['src'])
                        max_run = max(max_run,run_length)
                    else:
                        last = None
                    if event in ('expired','emptied'):
                        size = len(visits)
                        assert size==10 if event=='expired' else size<10
                        visit_sizes[size] += 1
                        unused += 10-size
                        post = sum(row['occ'][1:])+sum(h>0 for h,_ in row['acc'])-1
                        if event=='expired' and post>0:
                            limited.append(dict(end_cycle=row['k'],remaining_high=post))
                        visits = []
                else:
                    assert not visits, 'High visit left open across Low service'
                    last = None
            assert not visits and sum(n*c for n,c in visit_sizes.items())==len(req)
            result['class_visits'] = dict(events=dict(events),high_visit_sizes=dict(visit_sizes),unused_high_credit=unused,
                                          quota_exhaustions_with_high_pending=len(limited),examples=limited[:5],
                                          max_same_source_high_run_while_multiple_heads=max_run)
            result['software_fixed_slot_screen'] = [dict(initial_pointer=p,**shadow(rows,req,q,p)) for q in (1,2) for p in (1,2,3)]
        results.append(result)
        inputs.extend(dict(path=(p.relative_to(root) if p.is_absolute() else p).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (path,trace,metrics_path,original_path))
    comparisons = []
    for base in (0,1):
        assert paired[base].keys() == paired[2].keys()
        for t,r in paired[2].items():
            assert (r['generation'],r['acceptance']) == (paired[base][t]['generation'],paired[base][t]['acceptance'])
        differences = [r['g2f']-paired[base][t]['g2f'] for t,r in paired[2].items()]
        comparisons.append(dict(baseline=results[base]['policy'],same_request_count=len(differences),
                                main_lower=sum(d<0 for d in differences),main_equal=differences.count(0),
                                main_higher=sum(d>0 for d in differences),delta_main_minus_baseline=stats(differences)))
    examples = []
    for r in sorted(paired[2].values(),key=lambda r:(-r['g2f'],r['tag']))[:3]:
        policies = {}
        for p in (0,1,2):
            own = paired[p][r['tag']]
            start,slots = grants[p]
            sequence = slots[r['generation']-start:own['fire']-start+1]
            assert sequence[-1][0] == r['source']
            policies[results[p]['policy']] = dict(acceptance=own['acceptance'],fire=own['fire'],latency=own['g2f'],
                                                  sources=[s for s,_ in sequence],
                                                  main_charged_contexts=[c for _,c in sequence] if p==2 else None)
        examples.append(dict(tag=r['tag'],source=r['source'],generation=r['generation'],policies=policies))
    out = dict(status='PASS',scope=summary['scope'],window=diag['window'],run_id=summary['run_id'],inputs=inputs,results=results,paired_requests=comparisons,paired_tail_examples=examples,
               boundary='Actual RTL trace audit; SQ shadows are offline order-only design screens, NOT SQ RTL simulations.')
    (output/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',run_id=summary['run_id'],rtl_runs=len(results))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args = ap.parse_args()
    audit(args.run,args.output)
