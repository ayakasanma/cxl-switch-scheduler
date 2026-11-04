"""Hand examples for the independent quota audit; real-evidence mutations are separate."""
import unittest

from audit_descriptor_placement import SUBSETS, mechanism


class PlacementAuditTests(unittest.TestCase):
    def test_subsets_and_half_class_allocation(self):
        self.assertEqual(len(SUBSETS), 14)
        self.assertEqual(mechanism([960,320,320,320], (0,)), [960,960])
        self.assertEqual(mechanism([480]*4, (1,3)), [960,960])
        self.assertEqual(mechanism([320,960,320,320], (0,2,3)), [960,960])

    def test_partial_visits_are_allowed(self):
        self.assertEqual(mechanism([950,323,324,323], (0,)), [950,970])

    def test_wrong_placement_or_allocation_rejected(self):
        for counts, low in (([960,320,320,320], (1,)), ([960,320,320,320], ()),
                            ([480]*4, (0,0)), ([960,300,340,320], (0,)),
                            ([949,324,324,323], (0,))):
            with self.subTest(counts=counts, low=low), self.assertRaises(ValueError):
                mechanism(counts, low)


if __name__ == '__main__':
    unittest.main()
