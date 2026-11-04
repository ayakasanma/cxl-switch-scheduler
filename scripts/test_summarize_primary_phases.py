"""Independent rejection controls for phase result ingestion."""
from copy import deepcopy
import unittest

from test_primary_phase_metrics import hand_trace, legacy
from summarize_primary_phases import validate_bucket, validate_metrics


class PhaseAuditTests(unittest.TestCase):
    def fixture(self):
        return hand_trace().result(legacy(6, 4, 3, [1, 1, 2, 2], [0, 0, 1, 2]))["by_kind"]["A"]

    def test_hand_computed_bucket(self):
        validate_bucket(self.fixture(), 2)

    def test_bad_histogram_cohort_partition_and_depth_rejected(self):
        mutations = [
            lambda b: b["acceptance_to_fire_completed"].update(count=999),
            lambda b: b.update(accepted=5, accepted_per_source=[3, 2]),
            lambda b: b.update(stall_cycles=99),
            lambda b: b["fifo_occupancy_pre_edge"]["max_per_source"].__setitem__(0, 17),
            lambda b: b["producer_backlog_post_edge"].update(sum_total=999),
        ]
        for mutation in mutations:
            b = deepcopy(self.fixture())
            mutation(b)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_bucket(b, 2)

    def test_changed_legacy_rejected_before_acceptance(self):
        with self.assertRaisesRegex(ValueError, "legacy field changed"):
            validate_metrics({"fires_measurement": 2}, {"fires_measurement": 1})


if __name__ == "__main__":
    unittest.main()
