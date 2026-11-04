"""Small independent hand-computed pooled-tail checks; no simulator imports."""
from copy import deepcopy
import unittest

from audit_hog_sparse import pooled


def example():
    return dict(count=100,mean=10.98,min=2,max=900,p99_nearest_rank=2,
                distinct_values=2,histogram={'2':99,'900':1})


class PooledAuditTests(unittest.TestCase):
    def test_pool_recomputes_tail_from_counts(self):
        h=example()
        singleton=dict(count=1,mean=900,min=900,max=900,p99_nearest_rank=900,
                       distinct_values=1,histogram={'900':1})
        result=pooled([h,singleton])
        self.assertEqual(result['count'],101)
        self.assertEqual(result['p99_nearest_rank'],900)
        self.assertEqual(result['mean'],1998/101)

    def test_empty_population_has_no_latency(self):
        self.assertIsNone(pooled([])['p99_nearest_rank'])
        self.assertIsNone(pooled([])['mean'])

    def test_corrupt_input_rejected(self):
        h=deepcopy(example())
        h['p99_nearest_rank']=900
        with self.assertRaises(ValueError):pooled([h])


if __name__ == '__main__':
    unittest.main()
