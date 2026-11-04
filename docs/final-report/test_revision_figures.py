"""Checks that visualized values preserve accepted cohorts and contrast meaning."""
import unittest
import json
import xml.etree.ElementTree as ET
import generate_revision_figures as f


class FigureDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = f.data()

    def test_confirmation_and_contrast_direction(self):
        self.assertEqual(self.d["confirmation"]["B"], [33.45,16.65,17.7,21.05,21.35,33,12.35])
        for p in self.d["contrasts"]:
            a=self.d["confirmation"][p["arm"]]
            expected=a[f.g.POLICIES.index(p["candidate"])]-a[f.g.POLICIES.index(p["baseline"])]
            self.assertAlmostEqual(p["value"],expected)
            self.assertLessEqual(p["low"],p["value"])
            self.assertGreaterEqual(p["high"],p["value"])

    def test_public_figure_labels(self):
        self.assertEqual(f.LABELS[3].replace("\n", ""), "FAI-inspired")
        self.assertEqual(f.LABELS[6], "CGOF\n(2:1)")
        self.assertFalse(any("CGOF-" in label for label in f.LABELS))

    def test_exploration_coverage_and_no_unmeasured_dac(self):
        self.assertEqual(len(self.d["robustness"]),6)
        self.assertTrue(all(len(r["values"])==6 and "DAC2" not in r["values"] for r in self.d["robustness"]))
        for a in ("A","B"):
            self.assertEqual(set(self.d["n_expansion"][a]),{"8","16"})
            self.assertTrue(all(len(v)==6 for v in self.d["n_expansion"][a].values()))
            self.assertEqual(len(self.d["power_mW"][a]),3)
        self.assertEqual([round(r["dac"]-r["main"],1) for r in self.d["dac_backpressure"]],[-12.2,-12.2,-9,-7])
        self.assertEqual(len(self.d["primary_area"]),3)
        self.assertAlmostEqual(self.d["dac_area"],109794.784709)
        self.assertEqual([len(self.d["sensitivity"][g]) for g in ("rr-quantum","high-quota","depth")],[2,2,6])
        depth_main_b=next(s for s in self.d["sensitivity"]["depth"] if (s["policy"],s["arm"])==("MAIN","B"))
        self.assertEqual(depth_main_b["points"],[[8,20.6],[16,20.8],[32,20.8]])


class ImprovementFigureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = f.improvement_data()
        cls.out = f.OUT/'improvement'

    def test_figure_data_share_table_evidence(self):
        plotted = json.loads((self.out/'plot-data.json').read_text())
        for key in plotted:
            self.assertEqual(plotted[key], self.d[key])
        manifest = json.loads((self.out/'figure-manifest.json').read_text())
        self.assertEqual(manifest['table_manifest_sha256'], self.d['table_manifest_sha256'])
        self.assertEqual(manifest['generator_sha256'], f.g.digest(f.Path(f.__file__).read_bytes()))
        self.assertEqual(manifest['png_dpi'], 300)
        for name, expected in manifest['outputs'].items():
            self.assertEqual(f.g.digest((self.out/name).read_bytes()), expected)

    def test_five_vector_exports_and_explicit_evidence_labels(self):
        ns = {'s': 'http://www.w3.org/2000/svg'}
        names = ('pooling-path', 'buffer-transition', 'allocation-shares', 'heavy-sparse-tradeoff', 'cgof-hardware')
        text = {}
        for name in names:
            tree = ET.parse(self.out/(name+'.svg'))
            text[name] = ' '.join(''.join(e.itertext()) for e in tree.findall('.//s:text', ns))
            self.assertGreater(len(text[name]), 100)  # SVG text remains editable.
            self.assertTrue((self.out/(name+'.pdf')).read_bytes().startswith(b'%PDF'))
            self.assertTrue((self.out/(name+'.png')).read_bytes().startswith(b'\x89PNG'))
        self.assertIn('MODEL_ONLY', text['allocation-shares'])
        self.assertIn('MODEL_ONLY', text['heavy-sparse-tradeoff'])
        self.assertNotIn('SCHEDULER_RTL', text['heavy-sparse-tradeoff'])
        self.assertIn('PRE-LAYOUT', text['cgof-hardware'])
        self.assertIn('effective High', text['buffer-transition'])
        self.assertIn('in_ready', text['pooling-path'])
        self.assertIn('out_ready', text['pooling-path'])
        self.assertNotIn('ready / eligibility', text['pooling-path'])


if __name__ == "__main__":
    unittest.main()
