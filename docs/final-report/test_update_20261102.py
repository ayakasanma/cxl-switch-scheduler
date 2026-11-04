"""Verification tests for the November 2, 2026 evidence-review follow-up generator."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import generate_update_20261102 as g


class Update20261102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = g.collect()

    def test_w5m_and_w256_ordering_numbers_from_frozen_manifests(self):
        w5m = self.data["w5m_ordering"]
        self.assertEqual(w5m["status"], "COMPLETE_DESCRIPTIVE_EXPLORATION")
        self.assertEqual(len(w5m["seeds"]), 5)
        for row in w5m["seeds"]:
            self.assertEqual(
                (row["S_Q1_OF"], row["S_Q1_RR"], row["S_Q2_OF"], row["S_Q2_RR"]),
                (11, 11, 12, 11),
            )
            self.assertEqual((row["d1"], row["d2"], row["I"]), (0, -1, -1))
            self.assertEqual((row["A_delta_Q1"], row["A_delta_Q2"]), (0, 0))
        self.assertEqual([r["A_cycles"] for r in w5m["seeds"]], [3, 0, 7, 1, 8])
        self.assertEqual(w5m["summaries"]["Hmax_deltas"]["Q1"]["mean"], 1.6)
        self.assertEqual(w5m["summaries"]["Hmax_deltas"]["Q2"]["mean"], -0.2)

        w256 = self.data["w256_ordering"]
        self.assertEqual(w256["verdict"], "NOT_CONFIRMED")
        self.assertEqual(w256["counts"]["jobs"], 160)
        self.assertEqual(w256["counts"]["mixed_isolated_pairs"], 80)
        self.assertEqual(w256["primary"]["d1"]["zero"], 20)
        self.assertEqual(w256["primary"]["d2"]["negative"], 7)
        self.assertEqual(w256["primary"]["d2"]["zero"], 13)
        self.assertEqual(w256["primary"]["d2"]["mean"], -0.35)
        self.assertEqual(w256["primary"]["interaction"]["mean"], -0.35)

    def test_arrival_phase_slack_and_lag_recovery(self):
        arr_w5m = {(r["profile"], r["policy"]): r for r in self.data["arrival_w5m_confirmation"]}
        self.assertEqual(arr_w5m[("under", "CGOF (1:1)")]["delta_mean"], 0.0)
        self.assertEqual(arr_w5m[("under", "CGOF (2:1)")]["delta_ci95"], [0.0, 0.0])
        self.assertEqual(arr_w5m[("over", "CGOF (2:1)")]["delta_mean"], 834.25)
        self.assertEqual(arr_w5m[("over", "CGOF (2:1)")]["delta_ci95"], [820.4, 849.3])

        arr_p0 = {(r["profile"], r["policy"]): r for r in self.data["arrival_p0_w256"]}
        self.assertEqual(arr_p0[("near", "CGOF (1:1)")]["max_lag_mean"], 5.0)
        self.assertEqual(arr_p0[("near", "CGOF (2:1)")]["max_lag_mean"], 4.95)
        self.assertEqual(arr_p0[("near", "CGOF (1:1)")]["recovered"], 20)
        self.assertEqual(arr_p0[("near", "CGOF (2:1)")]["recovered"], 20)
        self.assertEqual(arr_p0[("over", "CGOF (2:1)")]["delta_mean"], 85.2)

    def test_refill_buffer_and_dynamic_single_seed_probe(self):
        refill = self.data["refill_trace"]
        self.assertEqual(refill["divergent_shifts"], [2, 4, 6])
        self.assertEqual(refill["cause_counts"], {"eligibility": 1, "refill": 2})

        cl = self.data["buffer_closed_loop"]
        self.assertEqual(cl["summary"]["run_count"], 720)
        self.assertEqual(cl["summary"]["scenario_count"], 120)
        self.assertEqual(cl["negative_control_groups"], 120)
        self.assertEqual(cl["negative_control_status"], "PASS")

        dyn = {(r["case"], r["policy"]): r for r in self.data["dynamic_rtl_probe"]}
        self.assertEqual(dyn[("role-switch", "CGOF (2:1)")]["effective_transitions"], 3)
        self.assertEqual(dyn[("ready-spread", "CGOF (2:1)")]["sparse_gf_p99"], 3)
        self.assertEqual(dyn[("ready-bursty", "CGOF (2:1)")]["sparse_gf_p99"], 11)
        self.assertEqual(
            (
                dyn[("ready-bursty", "CGOF (2:1)")]["heavy_ga_p99"],
                dyn[("ready-bursty", "CGOF (2:1)")]["heavy_af_p99"],
                dyn[("ready-bursty", "CGOF (2:1)")]["heavy_gf_p99"],
            ),
            (2, 18, 20),
        )
        self.assertEqual(
            (
                dyn[("depth8-bursty", "CGOF (2:1)")]["heavy_ga_p99"],
                dyn[("depth8-bursty", "CGOF (2:1)")]["heavy_af_p99"],
                dyn[("depth8-bursty", "CGOF (2:1)")]["heavy_gf_p99"],
            ),
            (11, 16, 20),
        )

    def test_claim_matrix_tiers_and_bound_outputs(self):
        tiers = {c["id"]: c["tier"] for c in self.data["claim_matrix"]}
        self.assertEqual(
            tiers,
            {
                "C1": "CONFIRMED",
                "C2": "CONFIRMED",
                "C3": "CONFIRMED",
                "C4": "DESCRIPTIVE",
                "C5": "MODEL_ONLY",
                "C6": "MODEL_ONLY",
                "C7": "SINGLE_SEED",
                "C8": "NOT_RUN",
            },
        )
        manifest = json.loads((g.OUT_GEN / "update_20261102_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["inputs"]), 24)
        c_hashes = {c["id"]: c["sha256"] for c in self.data["claim_matrix"]}
        self.assertEqual(
            c_hashes["C1"],
            "da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097",
        )
        self.assertEqual(
            c_hashes["C2"],
            "0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d",
        )
        self.assertNotEqual(c_hashes["C1"], c_hashes["C2"])
        self.assertEqual(manifest["generator_sha256"], g.sha(g.__file__))
        self.assertEqual(manifest["tex_sha256"], g.sha(g.OUT_GEN / "update_20261102_results.tex"))
        for name, expected in manifest["figure_exports"].items():
            self.assertEqual(g.sha(g.OUT_FIG / name), expected)
        svg = ET.parse(g.OUT_FIG / "followup-synthesis-20261102.svg")
        text = " ".join("".join(x.itertext()) for x in svg.findall(".//{http://www.w3.org/2000/svg}text"))
        self.assertIn("W5M ordering", text)
        self.assertIn("seed 7291", text)


if __name__ == "__main__":
    unittest.main()
