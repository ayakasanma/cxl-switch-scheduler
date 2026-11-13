"""CGOF cohort bindings, independent replay and serialized corruption tests; no EDA."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import export_cgof_power_vectors as cgof


class CohortContracts(unittest.TestCase):
    def test_production_plans_preserve_separate_baseline_arms(self):
        for weight in (1, 2):
            for seed in (509, 510, 511):
                for arm, warmup, measured in (("A", 10000000, 100000),
                                               ("B", 10101024, 102400)):
                    metadata = cgof.plan(weight, seed, arm)
                    self.assertEqual((metadata["warmup_cycles"], metadata["measured_cycles"]),
                                     (warmup, measured))
                    self.assertEqual(metadata["policy_id"], weight + 2)
                    self.assertNotIn("rr_quantum", metadata)
                    self.assertTrue(metadata["production_evidence"])
                    cgof.check_contract(metadata)
        for args in ((1, 508, "A"), (1, 512, "A"), (3, 509, "A"),
                     (True, 509, "A"), (1, 509, "C"), (1, 509, "A", 256, 0),
                     (1, 509, "A", 5000000, 64)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                cgof.plan(*args)

    def test_historical_path_relocation_and_escape(self):
        root = Path("evidence")
        self.assertEqual(cgof.historical_path(root, str(cgof.RECORDED_ROOT / "data/file.json")),
                         root / "data/file.json")
        for name in ("C:/other/file", str(cgof.RECORDED_ROOT / "../secret")):
            with self.assertRaises(ValueError):
                cgof.historical_path(root, name)

    def test_line_endings_are_the_only_allowed_traffic_difference(self):
        archived = b"source" + bytes((13, 10))
        digest = hashlib.sha256(archived).hexdigest()
        result = cgof.traffic_binding(b"source" + bytes((10,)), archived, digest)
        self.assertEqual(result["comparison"], "CRLF_LF_ONLY")
        for current, expected in ((b"changed", digest), (archived, "0" * 64)):
            with self.assertRaises(ValueError):
                cgof.traffic_binding(current, archived, expected)

    def test_cgof_contract_rejects_weight_ordering_and_baseline_checker_aliases(self):
        original = cgof.plan(1, 509, "A", 256, 64)
        for key, value in (("high_weight", 2), ("eligible_rr", 1), ("ordering", "eligible-round-robin"),
                           ("policy_id", 0), ("mode_id", 12), ("production_evidence", True)):
            changed = dict(original, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                cgof.check_contract(changed)
        with self.assertRaises(ValueError):
            cgof.check_mode(original, allow_fixture=True)

    def test_output_boundary_is_fresh_and_worktree_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(cgof, "ROOT", root / "worktree"):
                out = root / "worktree/artifacts/new"
                cgof.output_dir(out, root / "evidence")
                for target in (out, root / "outside", root / "evidence/artifacts/new",
                               root / "worktree/artifacts"):
                    with self.subTest(target=target), self.assertRaises((ValueError, FileExistsError)):
                        cgof.output_dir(target, root / "evidence")

    def test_direct_and_recursive_semantic_hash_bindings(self):
        identity = dict(policy="fcfs", seed=509, arm="A")
        digest = "1" * 64
        leaf = dict(case=identity, decision="ADOPT_PRE_LAYOUT_TT25NS_MATCHED_POWER",
                    problems=[], bindings=dict(metadata=digest))
        cgof.metadata_binding(Path("unused"), leaf, digest, identity)
        with self.assertRaises(ValueError):
            cgof.metadata_binding(Path("unused"), leaf, "2" * 64, identity)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cgof.write_json(root / "leaf.json", leaf)
            parent = dict(actual_EDA_exit=0, semantic_receipt=str(cgof.RECORDED_ROOT / "leaf.json"),
                          semantic_sha256=cgof.sha(root / "leaf.json"))
            cgof.metadata_binding(root, parent, digest, identity)
            leaf["problems"] = ["unresolved"]
            cgof.write_json(root / "leaf.json", leaf)
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, parent, digest, identity)
            parent["semantic_sha256"] = cgof.sha(root / "leaf.json")
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, parent, digest, identity)

    def test_recovered_metadata_requires_pinned_plan_and_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            digest = "1" * 64
            plan = dict(expected_members={"metadata.json": digest})
            result = dict(actual_EDA_exit=0, payload_and_source_match=True)
            recovery = {}
            for name, value in (("plan", plan), ("result", result)):
                cgof.write_json(root / (name + ".json"), value)
                recovery[name] = dict(path=str(cgof.RECORDED_ROOT / (name + ".json")),
                                      sha256=cgof.sha(root / (name + ".json")))
            leaf = dict(status="ADOPTED_SINGLE_TRAINED_PRELAYOUT_CASE", blocking_issues=[],
                        source_before_after_identical=True,
                        recovery_result_sha256=recovery["result"]["sha256"])
            cgof.metadata_binding(root, leaf, digest, {}, recovery=recovery)
            for other in ("2" * 64,):
                with self.assertRaises(ValueError):
                    cgof.metadata_binding(root, leaf, other, {}, recovery=recovery)
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, leaf, digest, {})

    def test_detached_preparation_binding_requires_parent_adoption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            digest = "1" * 64
            prepared = dict(case_id="fcfs-A-s511",
                            local_export=dict(native_exit=0, files={"metadata.json": digest}),
                            member_sha256={"metadata.json": digest})
            cgof.write_json(root / "prepared.json", prepared)
            leaf = dict(status="REVIEWED_DETACHED_CASE_PARENT_ADOPTION_REQUIRED",
                        case_id=prepared["case_id"], blocking_issues=[], source_before_after_identical=True,
                        detached_transport=dict(raw_sha256={
                            str(cgof.RECORDED_ROOT / "prepared.json"): cgof.sha(root / "prepared.json")}))
            cgof.write_json(root / "leaf.json", leaf)
            parent = dict(status="PARENT_ACCEPTED_DETACHED_TRAINED_POWER_CASE",
                          actual_EDA_exit=0, case_id=prepared["case_id"],
                          semantic_receipt=str(cgof.RECORDED_ROOT / "leaf.json"),
                          semantic_sha256=cgof.sha(root / "leaf.json"))
            identity = dict(policy="fcfs", seed=511, arm="A")
            cgof.metadata_binding(root, parent, digest, identity)
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, leaf, digest, identity)
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, parent, "2" * 64, identity)
            prepared["local_export"]["native_exit"] = 1
            cgof.write_json(root / "prepared.json", prepared)
            with self.assertRaises(ValueError):
                cgof.metadata_binding(root, parent, digest, identity)


class ReplayContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {}
        for weight in (1, 2):
            for arm in ("A", "B"):
                metadata = cgof.plan(weight, 509, arm, 256, 64)
                stats = {}
                rows = list(cgof.replay(metadata, stats))
                metadata.update(stats)
                cls.cases[weight, arm] = metadata, rows

    def test_fixture_weights_share_exogenous_trace_and_conserve_requests(self):
        for arm in ("A", "B"):
            first, second = (self.cases[weight, arm][0] for weight in (1, 2))
            self.assertEqual(first["trace"], second["trace"])
            for metadata in (first, second):
                self.assertEqual(metadata["mode_id"], 9)
                self.assertFalse(metadata["production_evidence"])
                self.assertEqual(metadata["all"]["accepted"] - metadata["all"]["fires"],
                                 sum(metadata["state_at_end"]["occupancy"]))
                self.assertEqual(metadata["drain_cycles"], 0)
                self.assertGreater(metadata["credit_refills"]["warmup"], 0)
        self.assertEqual(self.cases[1, "B"][0]["warmup_cycles"], 101536)

    def test_every_pin_column_and_row_count_are_checked(self):
        metadata, rows = self.cases[2, "A"]
        for column in range(8):
            changed = list(rows)
            changed_row = list(changed[40])
            changed_row[column] ^= 1
            changed[40] = tuple(changed_row)
            with self.subTest(column=column), self.assertRaises(ValueError):
                list(cgof.replay(metadata, {}, changed))
        for changed in (rows[:-1], rows + [rows[-1]]):
            with self.assertRaises(ValueError):
                list(cgof.replay(metadata, {}, changed))

    def serialize(self, directory):
        metadata, rows = copy.deepcopy(self.cases[2, "A"])
        source_hashes = cgof.sources()
        directory.mkdir()
        entries = {name: (cgof.ROOT / name).read_bytes() for name in source_hashes}
        mapped = {name: b"synthetic input" for name in cgof.MAPPED_FILES}
        entries.update({"mapped/" + name: data for name, data in mapped.items()})
        entries["baseline-acceptance.json"] = b"synthetic index"
        pins = {name: hashlib.sha256(data).hexdigest() for name, data in mapped.items()}
        with zipfile.ZipFile(directory / "source-freeze.zip", "x") as archive:
            for name, data in sorted(entries.items()):
                archive.writestr(zipfile.ZipInfo(name), data)
        digest, count = cgof.trained.legacy._write_vectors(directory, cgof.trained.header(metadata), rows)
        metadata.update(source_sha256=source_hashes,
                        archive_files={name: hashlib.sha256(data).hexdigest() for name, data in entries.items()},
                        source_archive_sha256=cgof.sha(directory / "source-freeze.zip"),
                        vectors_text_sha256=digest, vectors_rows=count,
                        vectors_gzip_sha256=cgof.sha(directory / "vectors.txt.gz"),
                        mapping=dict(files=pins), library_sha256=cgof.DB_SHA,
                        profile_canonical_sha256=cgof.trained.legacy.PROFILE_SHA,
                        baseline_index_sha256=hashlib.sha256(entries["baseline-acceptance.json"]).hexdigest())
        cgof.write_json(directory / "metadata.json", metadata)
        return metadata, pins

    def test_serialized_audit_rejects_rehashed_statistics_and_archive_mutations(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "case"
            metadata, pins = self.serialize(directory)
            with patch.object(cgof, "MAPPING_PINS", {2: tuple(pins[name] for name in cgof.MAPPED_FILES[4:6])}), \
                    patch.object(cgof.inventory, "BASELINE_SHA", metadata["baseline_index_sha256"]):
                self.assertEqual(cgof.audit_export(directory)["power_status"], "NOT_RUN")
                for field in ("state_at_cut", "state_at_end", "closings", "credit_refills", "vectors_rows"):
                    changed = copy.deepcopy(metadata)
                    changed[field] = None
                    cgof.write_json(directory / "metadata.json", changed)
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        cgof.audit_export(directory)
                cgof.write_json(directory / "metadata.json", metadata)
                with zipfile.ZipFile(directory / "source-freeze.zip", "a") as archive:
                    archive.writestr("extra", b"unbound")
                metadata["source_archive_sha256"] = cgof.sha(directory / "source-freeze.zip")
                cgof.write_json(directory / "metadata.json", metadata)
                with self.assertRaises(ValueError):
                    cgof.audit_export(directory)


if __name__ == "__main__":
    unittest.main()
