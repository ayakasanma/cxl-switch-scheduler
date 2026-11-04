"""Independent hand-derived controls for the offline trace audit/design screen."""
from collections import deque
from copy import deepcopy
import unittest

from analyze_trace import observed, shadow, stats


def simultaneous():
    queues = [deque() for _ in range(4)]
    pending = [deque() for _ in range(4)]
    rows = []
    sources = [0,1,2,3,1,2,3,1,2,3]
    for k,source in enumerate(sources):
        gen = [[h,10*h+i] for h in (1,2,3) for i in range(3)] if k==0 else []
        for h,t in gen:
            pending[h].append(t)
        acc = [[h,pending[h][0]] for h in (1,2,3) if pending[h]]
        row = dict(k=k,gen=gen,occ=[16 if k==0 else 15]+[len(queues[h]) for h in (1,2,3)],
                   pending=[1]+[len(pending[h]) for h in (1,2,3)],
                   heads=[999]+[queues[h][0] if queues[h] else None for h in (1,2,3)],
                   src=source,tag=queues[source][0] if source else 999,fire=1,acc=acc,in_ready=14,
                   ctx=dict(charged=['High',k-1] if source else ['Low',0]))
        rows.append(row)
        if source:
            queues[source].popleft()
        for h,t in acc:
            assert pending[h].popleft()==t
            queues[h].append(t)
    return rows


class TraceControls(unittest.TestCase):
    def test_simultaneous_generation_same_complete_histogram(self):
        rows = simultaneous()
        requests = observed(rows)
        self.assertEqual(stats([r['g2f'] for r in requests.values()]),stats(list(range(1,10))))
        for q in (1,2):
            for p in (1,2,3):
                with self.subTest(quantum=q,pointer=p):
                    result = shadow(rows,requests,q,p)
                    self.assertEqual(result['pooled'],stats(list(range(1,10))))
                    self.assertEqual([r['count'] for r in result['per_source'].values()],[3,3,3])

    def test_rejects_corrupt_heads_and_incomplete_population(self):
        for mutation in ('head','end'):
            with self.subTest(mutation=mutation):
                rows = deepcopy(simultaneous())
                if mutation=='head':
                    rows[1]['heads'][1]=999
                else:
                    rows.pop()
                with self.assertRaises(AssertionError):
                    observed(rows)

    def test_exact_nearest_rank(self):
        self.assertEqual(stats(list(range(100)))['p99'],98)
        self.assertEqual(stats([7])['p99'],7)

    def test_single_eligible_source_has_no_lost_slots(self):
        rows = [dict(k=k,acc=[[2,20+k]] if k<3 else [],ctx=dict(charged=['Low',0] if k==0 else ['High',k-1]),fire=1) for k in range(4)]
        req = {20+k:dict(source=2,generation=0,fire=k+1) for k in range(3)}
        for q in (1,2):
            for p in (1,2,3):
                with self.subTest(quantum=q,pointer=p):
                    result = shadow(rows,req,q,p)
                    self.assertEqual(result['pooled'],stats([1,2,3]))

    def test_partial_quota_carries_across_low_visit(self):
        rows = [dict(k=0,acc=[[1,10],[2,20]],ctx=dict(charged=['Low',0]),fire=1),
                dict(k=1,acc=[[1,11]],ctx=dict(charged=['High',0]),fire=1),
                dict(k=2,acc=[],ctx=dict(charged=['Low',0]),fire=1),
                dict(k=3,acc=[],ctx=dict(charged=['High',1]),fire=1),
                dict(k=4,acc=[],ctx=dict(charged=['High',2]),fire=1)]
        req = {10:dict(source=1,generation=0,fire=1),11:dict(source=1,generation=0,fire=4),20:dict(source=2,generation=0,fire=3)}
        self.assertEqual(shadow(rows,req,2,1)['per_source'][1]['mean'],2)
        self.assertEqual(shadow(rows,req,2,1)['per_source'][2]['mean'],4)
        self.assertEqual(shadow(rows,req,1,1)['per_source'][1]['mean'],2.5)

    def test_full_before_pop_invalidates_fixed_admissions(self):
        rows = [dict(k=k,acc=[[1,k]],ctx=dict(charged=['Low',0] if k<16 else ['High',0]),fire=1) for k in range(17)]
        req = {k:dict(source=1,generation=k,fire=17+k) for k in range(17)}
        with self.assertRaisesRegex(AssertionError,'shadow FIFO full'):
            shadow(rows,req,1,1)


if __name__=='__main__':
    unittest.main()
