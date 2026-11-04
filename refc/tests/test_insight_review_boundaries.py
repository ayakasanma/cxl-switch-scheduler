"""Independent directed checks; do not change the sealed screening sources."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cxl_model.experimental import ExperimentalSwitchModel


class InsightBoundaryTests(unittest.TestCase):
    def waiting_source(self):
        model = ExperimentalSwitchModel(policy="AGE_T16_K8", window=64)
        model.commit(rst_n=False)
        # Align the last normal fire just after a close, then hold the rescue.
        for _ in range(96):
            model.commit(out_ready=True)
        for k in range(16):
            model.commit(in_valid=[True, True, False, False],
                         in_desc=[100 + k, 200 + k, 0, 0])
        model.commit(in_valid=[False, False, True, False], in_desc=[0, 0, 300, 0])
        for _ in range(15):
            edge = model.commit(out_ready=True)
            self.assertFalse(edge.rescue)
            self.assertIn(edge.fired.source, (0, 1))
        return model

    def test_first_selection_at_ready_gap_threshold(self):
        model = self.waiting_source()
        self.assertEqual(model.gaps[2], 15)
        self.assertGreaterEqual(model.time - model.arrivals[2][0], 16)
        self.assertFalse(model.choice().rescue)
        model.commit(out_ready=True)
        self.assertEqual(model.gaps[2], 16)
        self.assertEqual((model.choice().source, model.choice().rescue), (2, True))
        edge = model.commit(out_ready=True)
        self.assertEqual((edge.fired.source, edge.rescue), (2, True))
        self.assertEqual((model.gaps[2], model.budget), (0, 0))

    def test_held_rescue_across_real_window_close(self):
        model = self.waiting_source()
        model.commit(out_ready=True)
        visit, budget = model.visit, model.budget
        selected = model.choice()
        self.assertEqual((selected.source, selected.rescue), (2, True))
        before = model.view(out_ready=False)
        model.commit(out_ready=False)
        previous_windows = model.windows_closed
        previous_classes = model.classes()
        closing = None
        while model.windows_closed == previous_windows:
            held = model.view(out_ready=False)
            self.assertTrue(held.held)
            self.assertEqual((held.out_source, held.out_desc),
                             (before.out_source, before.out_desc))
            self.assertEqual(model.choice(), selected)
            edge = model.commit(out_ready=False)
            closing = edge.closing or closing
            self.assertEqual((model.visit, model.budget), (visit, budget))
        self.assertIsNotNone(closing)
        self.assertNotEqual(previous_classes, model.classes())
        self.assertIn("L", model.classes())
        edge = model.commit(out_ready=True)
        self.assertEqual((edge.fired.source, edge.rescue), (2, True))
        self.assertEqual(model.visit, visit)
        self.assertEqual(model.budget, 0)
        self.assertEqual(model.occupancy(2), 0)
        normal = model.choice()
        self.assertFalse(normal.rescue)
        self.assertIn(normal.source, (0, 1))
        self.assertIn(model.classes()[normal.source], ("H", "B_H"))
        edge = model.commit(out_ready=True)
        self.assertEqual(edge.fired.source, normal.source)
        self.assertFalse(edge.rescue)
        self.assertEqual(model.budget, 1)


if __name__ == "__main__":
    unittest.main()
