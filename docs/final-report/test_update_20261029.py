"""Raw-result coverage guards and honest, reproducible Oct29 figure exports."""
import json
import unittest
import xml.etree.ElementTree as ET

import generate_update_20261029 as g


class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = g.collect()

    def test_recomputed_confirmation_and_paired_effect(self):
        groups = self.data["finite_groups"]
        self.assertEqual([x["sparse_p99"]["mean"] for x in groups], [3, 4])
        self.assertEqual([x["heavy_wall_gap_max"]["mean"] for x in groups], [9.45, 10.85])
        self.assertEqual([x["heavy_completion_delta_cycles"]["mean"] for x in groups], [3.05, 3])
        delta = next(x for x in self.data["quota_deltas"] if x["metric"] == "heavy_wall_gap_max")
        self.assertEqual(delta["percentile95"], [1.1, 1.75])
        self.assertEqual(delta["mean"], 1.4)
        self.assertEqual(self.data["coverage"]["finite_raw_jobs"], 80)
        self.assertEqual(len(self.data["finite_rows"]), 40)

    def test_duplicate_and_missing_pair_rejected(self):
        rows = self.data["finite_rows"]
        for bad in (rows[:-1], rows[:-1]+[rows[0]]):
            with self.assertRaisesRegex(ValueError, "40 unique"):
                g.check_grid(bad)

    def test_histogram_disagreement_rejected(self):
        with self.assertRaisesRegex(ValueError, "histogram count/P99"):
            g.check_histogram(dict(histogram={"3": 100}, count=100, p99=4))

    def test_exploration_has_no_interval_or_main_endpoint(self):
        groups = self.data["performance_cohorts"]
        self.assertEqual(len(groups), 6)
        for row in groups:
            confirm = row["ready"] == "always"
            self.assertEqual(row["n"], 20 if confirm else 5)
            self.assertEqual(row["sparse_p99"]["percentile95"] is not None, confirm)
        vals = {(r["cohort"], r["ready"]): r["sparse_p99"]["mean"] for r in groups}
        self.assertEqual([vals[("B", ready)] for ready in ("always", "bernoulli-0.75", "periodic-48/64")], [12.35, 20.4, 27])
        self.assertEqual(len(self.data["performance_rows"]), 60)

    def test_exports_hashes_editable_text_width_and_units(self):
        manifest = json.loads((g.HERE/"generated"/"update_20261029_manifest.json").read_text())
        self.assertEqual(manifest["generator_sha256"], g.sha(g.__file__))
        self.assertEqual(manifest["inputs"], self.data["inputs"])
        self.assertEqual(manifest["width_inches"], 7.1)
        self.assertEqual(manifest["png_dpi"], 300)
        for name, value in manifest["outputs"].items():
            self.assertEqual(g.sha(g.OUT/name), value)
        for name in ("finite-heavy-confirmation", "readiness-confirmation"):
            tree = ET.parse(g.OUT/(name+".svg"))
            self.assertEqual(tree.getroot().get("width"), "511.2pt")
            text = " ".join("".join(x.itertext()) for x in tree.findall(".//{http://www.w3.org/2000/svg}text"))
            self.assertGreater(len(text), 300)
            self.assertIn("cycles", text)
            self.assertTrue((g.OUT/(name+".pdf")).read_bytes().startswith(b"%PDF"))
        plotted = json.loads((g.OUT/"plot-data.json").read_text())
        self.assertEqual(plotted, self.data)
        self.assertEqual((g.HERE/"generated"/"update_20261029_results.tex").read_text(), g.tex_tables(self.data))


if __name__ == "__main__":
    unittest.main()
