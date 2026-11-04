"""Hand-derived statistics checks; run alongside audit_followup before accepting evidence."""
from copy import deepcopy
import unittest

from audit_descriptor_followup import hist


class HistogramAuditTests(unittest.TestCase):
    def test_hand_computed_p99(self):
        h = dict(count=100, mean=10.98, p99_nearest_rank=2, min=2, max=900,
                 distinct_values=2, histogram={'2': 99, '900': 1})
        self.assertEqual(hist(h), (100, 1098))

    def test_empty_cohort_is_undefined(self):
        self.assertEqual(hist(dict(count=0, mean=None, p99_nearest_rank=None, min=None,
                                   max=None, distinct_values=0, histogram={})), (0, 0))

    def test_corrupt_summary_fields_rejected(self):
        h = dict(count=3, mean=4., p99_nearest_rank=8, min=2, max=8,
                 distinct_values=2, histogram={'2': 2, '8': 1})
        for field, bad in [('count', 4), ('mean', 5), ('p99_nearest_rank', 2),
                           ('min', 1), ('max', 9), ('distinct_values', 3)]:
            d = deepcopy(h)
            d[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                hist(d)


if __name__ == '__main__':
    unittest.main()
