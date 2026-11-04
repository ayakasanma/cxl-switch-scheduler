from __future__ import annotations

import hashlib
import contextlib
import csv
import gzip
import io
import json
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import revision_area_audit as audit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_netlist(text: str) -> audit.Netlist:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "mapped.v"
        path.write_text(text, encoding="utf-8")
        return audit.parse_netlist(path)


def _parse_reference(text: str) -> dict[str, audit.ReferenceSection]:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "reference.rpt"
        path.write_text(text, encoding="utf-8")
        return audit.parse_reference_report(path)


def _reference_report(top_rows: list[tuple[str, str, str]], child_rows: list[tuple[str, str, str]]) -> str:
    def section(name: str, rows: list[tuple[str, str, str]], total: str) -> str:
        rendered = [
            "****************************************",
            f"Design : {name}" if name == "TOP" else f"Design: {name}",
            "****************************************",
            "Reference          Library       Unit Area   Count    Total Area   Attributes",
            "-----------------------------------------------------------------------------",
        ]
        for reference, count, total_area in rows:
            attrs = "h" if reference == "CHILD" else ""
            unit_area = Decimal(total_area) / int(count)
            rendered.extend(
                [
                    f"{reference}         fake_library",
                    f"                                  {unit_area:.6f}       {count}      {total_area}  {attrs}",
                ]
            )
        rendered.extend(
            [
                "-----------------------------------------------------------------------------",
                f"Total {len(rows)} references                                 {total}",
            ]
        )
        return "\n".join(rendered)

    return "\n\n".join(
        [
            section("TOP", top_rows, "5.000000"),
            section("CHILD", child_rows, "4.000000"),
        ]
    ) + "\n"


def _netlist() -> str:
    return """\
module TOP (a);
  input a;
  CHILD u_child ( .a(a) );
  LEAF u_leaf ( .a(a) );
endmodule

module CHILD (a);
  input a;
  LEAF u_leaf0 ( .a(a) );
  LEAF u_leaf1 ( .a(a) );
endmodule
"""


def _parameters(reported_cells: int = 9) -> dict[str, object]:
    return {
        "top_module": "TOP",
        "policy_name": "rr",
        "N_SRC": 0,
        "D": 0,
        "DESC_W": 0,
        "arrival_metadata": False,
        "expected": {
            "descriptor_storage_bits": 0,
            "timestamp_storage_bits": 0,
        },
        "_test_reported_cells": reported_cells,
    }


def _make_archive(
    root: Path,
    *,
    netlist: str | None = None,
    reference: str | None = None,
    reported_cells: int = 9,
) -> Path:
    archive = root / "case"
    (archive / "output").mkdir(parents=True)
    (archive / "reports").mkdir(parents=True)
    netlist_path = archive / "output/switch_top.syn.v"
    reference_path = archive / "reports/reference.rpt"
    summary_path = archive / "reports/area_summary.rpt"
    netlist_path.write_text(netlist if netlist is not None else _netlist(), encoding="utf-8")
    reference_path.write_text(
        reference
        if reference is not None
        else _reference_report(
            [("CHILD", "1", "4.000000"), ("LEAF", "1", "1.000000")],
            [("LEAF", "2", "4.000000")],
        ),
        encoding="utf-8",
    )
    summary_path.write_text(
        "\n".join(
            [
                "total_cell_area = 5.000000",
                f"number_of_cells = {reported_cells}",
                "number_of_combinational_cells = 3",
                "number_of_sequential_cells = 0",
                "number_of_references = 2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    parameters = _parameters(reported_cells)
    parameters_path = archive / "parameters.json"
    _write_json(parameters_path, parameters)
    manifest = {
        "parameters": parameters,
        "file_sha256": {"parameters.json": _sha256(parameters_path)},
        "source": {"head": "test"},
    }
    _write_json(archive / "manifest.json", manifest)

    checksum_targets = (
        "output/switch_top.syn.v",
        "reports/reference.rpt",
        "reports/area_summary.rpt",
    )
    sums = "".join(f"{_sha256(archive / item)}  {item}\n" for item in checksum_targets)
    (archive / "RESULT_SHA256SUMS").write_text(sums, encoding="utf-8")
    return archive


class AreaAuditTests(unittest.TestCase):
    def test_duplicate_leaf_paths_and_ledger_overlap_are_rejected(self) -> None:
        duplicate_netlist = _netlist().replace("LEAF u_leaf1", "LEAF u_leaf0")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dup.v"
            path.write_text(duplicate_netlist, encoding="utf-8")
            with self.assertRaisesRegex(audit.AuditError, "duplicate local instance"):
                audit.parse_netlist(path)

        leaf = audit.Leaf(
            path=("TOP", "u"),
            module_type="LEAF",
            instance_name="u",
            containing_module="TOP",
            ancestor_module_types=("TOP",),
            line_number=1,
        )
        ledger = audit.CategoryLedger()
        ledger.add(audit.AttributedLeaf(leaf, "common", "test", Decimal("1")))
        with self.assertRaisesRegex(audit.AuditError, "attributed more than once"):
            ledger.add(audit.AttributedLeaf(leaf, "policy", "overlap", Decimal("1")))

    def test_missing_reference_and_module_leaf_separation(self) -> None:
        netlist = _parse_netlist(_netlist())
        sections = _parse_reference(
            _reference_report(
                [("CHILD", "1", "4.000000"), ("LEAF", "1", "1.000000")],
                [("LEAF", "2", "4.000000")],
            )
        )
        top = sections["TOP"]
        sections["TOP"] = replace(
            top, rows=(top.rows[0],), total_area=Decimal("4"), total_unique_references=1
        )
        with self.assertRaisesRegex(audit.AuditError, "local instance mismatch"):
            audit.validate_reference_matches_netlist(netlist, sections)

        wrong_h = _reference_report(
            [("CHILD", "1", "4.000000"), ("LEAF", "1", "1.000000")],
            [("LEAF", "2", "4.000000")],
        ).replace("1.000000  \n", "1.000000  h\n")
        sections = _parse_reference(wrong_h)
        with self.assertRaisesRegex(audit.AuditError, "'h' attribute disagrees"):
            audit.validate_reference_matches_netlist(netlist, sections)

    def test_truncated_report_is_rejected(self) -> None:
        text = _reference_report(
            [("CHILD", "1", "4.000000"), ("LEAF", "1", "1.000000")],
            [("LEAF", "2", "4.000000")],
        )
        truncated = text.rsplit("Total", 1)[0]
        with self.assertRaisesRegex(audit.AuditError, "missing Total"):
            _parse_reference(truncated)

    def test_malformed_and_duplicate_netlist_modules_are_rejected(self) -> None:
        with self.assertRaises(audit.AuditError):
            _parse_netlist(_netlist().rsplit("endmodule", 1)[0])
        with self.assertRaisesRegex(audit.AuditError, "duplicate module"):
            _parse_netlist(_netlist() + _netlist())
        with self.assertRaisesRegex(audit.AuditError, "unterminated statement"):
            _parse_netlist(_netlist().replace("LEAF u_leaf1 ( .a(a) );", "LEAF u_leaf1 ( .a(a) )"))
        with self.assertRaisesRegex(audit.AuditError, "multiple instances|parentheses"):
            _parse_netlist(_netlist().replace("LEAF u_leaf0 ( .a(a) );", "LEAF u_leaf0 (.a(a)), u_other (.a(a));"))

    def test_recursion_reused_module_paths_and_cycles(self) -> None:
        netlist = _parse_netlist(_netlist().replace("CHILD u_child ( .a(a) );", "CHILD u_child ( .a(a) ); CHILD second (.a(a));"))
        leaves, occurrences = audit.expand_leaf_instances(netlist, "TOP")
        self.assertEqual(len(leaves), 5)
        self.assertEqual(len({leaf.path for leaf in leaves}), 5)
        self.assertEqual(occurrences["CHILD"], 2)
        with self.assertRaisesRegex(audit.AuditError, "cycle"):
            cycle = _parse_netlist(_netlist().replace("LEAF u_leaf0", "TOP u_leaf0"))
            audit.expand_leaf_instances(cycle, "TOP")

    def test_comma_separated_hierarchical_attributes(self) -> None:
        text = _reference_report(
            [("CHILD", "1", "4.000000"), ("LEAF", "1", "1.000000")],
            [("LEAF", "2", "4.000000")],
        ).replace("4.000000  h", "4.000000  h, n")
        sections = _parse_reference(text + "1\n")
        self.assertEqual(sections["TOP"].rows[0].attributes, frozenset({"h", "n"}))
        audit.validate_reference_matches_netlist(_parse_netlist(_netlist()), sections)

    def test_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            (archive / "output/switch_top.syn.v").write_text(
                _netlist() + "// corrupted\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(audit.AuditError, "checksum mismatch"):
                audit.verify_result_checksums(archive)

    def test_rr_timestamp_storage_is_zero(self) -> None:
        parameters = {
            "N_SRC": 1,
            "D": 1,
            "DESC_W": 4,
            "arrival_metadata": False,
            "policy_name": "rr",
            "expected": {
                "descriptor_storage_bits": 4,
                "timestamp_storage_bits": 0,
            },
        }
        leaves = [
            audit.Leaf(
                path=("TOP", f"desc{i}"),
                module_type="DFFX1_RVT",
                instance_name=f"desc_mem_q_reg_{i}",
                containing_module="cxl_desc_fifo_test",
                ancestor_module_types=("TOP", "cxl_desc_fifo_test"),
                line_number=1,
            )
            for i in range(4)
        ]
        observations = audit.validate_storage(parameters, leaves)
        self.assertTrue(observations["rr_timestamp_zero"])
        timestamp = replace(
            leaves[0], path=("TOP", "timestamp"), instance_name="gen_ts_ts_mem_q_reg_0"
        )
        with self.assertRaisesRegex(audit.AuditError, "timestamp storage"):
            audit.validate_storage(parameters, [*leaves, timestamp])
        arrival = replace(
            leaves[0], path=("TOP", "arrival"), instance_name="gen_arrival_ts_arrival_cnt_q_reg_0"
        )
        with self.assertRaisesRegex(audit.AuditError, "RR archive contains"):
            audit.validate_storage(parameters, [*leaves, arrival])

    def test_classification_and_exact_decimal_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            result = audit.audit_archive(archive, "test", root, root)
            categories = result["attribution"]["categories"]
            self.assertEqual(
                sum(Decimal(item["area"]) for item in categories.values()),
                Decimal(result["area_reconciliation"]["leaf_area"]),
            )
            with gzip.open(root / "test-leaves.csv.gz", "rt", encoding="ascii") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 3)
            self.assertEqual(len({row["path"] for row in rows}), 3)
            self.assertEqual(sum(Decimal(row["area"]) for row in rows), Decimal("5"))
            self.assertEqual(rows[0]["netlist_line"], "9")
            with self.assertRaises(FileExistsError):
                audit.audit_archive(archive, "test", root, root)

    def test_cli_refuses_existing_output_before_any_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "results.json"
            original = b'{"prior_evidence":true}\n'
            output.write_bytes(original)
            with patch.object(audit, "run_audit") as run, contextlib.redirect_stderr(io.StringIO()) as error:
                status = audit.main(["--output", str(output)])
            self.assertEqual(status, 1)
            self.assertIn("refusing to overwrite", error.getvalue())
            self.assertEqual(output.read_bytes(), original)
            run.assert_not_called()
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_manifest_parameter_corruption_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            path = archive / "parameters.json"
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["N_SRC"] = 16
            _write_json(path, changed)
            with self.assertRaisesRegex(audit.AuditError, "parameters do not match"):
                audit.audit_archive(archive, "test", root)

    def test_unresolved_and_unexplained_number_of_cells_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            result = audit.audit_archive(archive, "test", root)
            self.assertEqual(
                result["attribution"]["categories"]["unresolved"]["leaf_count"], 2
            )
            self.assertEqual(
                result["count_reconciliation"]["status"],
                "UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH",
            )
            self.assertEqual(result["count_reconciliation"]["delta_reported_minus_leaf_count"], 6)
            self.assertEqual(result["count_reconciliation"]["expanded_nonleaf_instance_occurrences"], 1)
            self.assertEqual(result["count_reconciliation"]["delta_reported_minus_leaf_plus_nonleaf_count"], 5)
            self.assertEqual(result["area_reconciliation"]["leaf_area"], "5.000000000000")
            self.assertEqual(result["area_reconciliation"]["residual_vs_summary"], "0.000000000000")

    def test_deterministic_totals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            first = json.dumps(audit.audit_archive(archive, "test", root), sort_keys=True)
            second = json.dumps(audit.audit_archive(archive, "test", root), sort_keys=True)
            self.assertEqual(first, second)

    def test_reused_module_area_and_counts_are_expanded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            netlist = archive / "output/switch_top.syn.v"
            netlist.write_text(
                _netlist().replace("CHILD u_child ( .a(a) );",
                                   "CHILD u_child (.a(a)); CHILD second (.a(a));"),
                encoding="utf-8",
            )
            reference = archive / "reports/reference.rpt"
            reference.write_text(
                _reference_report(
                    [("CHILD", "2", "8.000000"), ("LEAF", "1", "1.000000")],
                    [("LEAF", "2", "4.000000")],
                ).replace("5.000000", "9.000000"),
                encoding="utf-8",
            )
            summary = archive / "reports/area_summary.rpt"
            summary.write_text(
                summary.read_text(encoding="utf-8")
                .replace("5.000000", "9.000000")
                .replace("number_of_cells = 9", "number_of_cells = 5")
                .replace("number_of_combinational_cells = 3",
                         "number_of_combinational_cells = 5"),
                encoding="utf-8",
            )
            (archive / "RESULT_SHA256SUMS").write_text(
                "".join(f"{_sha256(path)}  {path.relative_to(archive).as_posix()}\n"
                        for path in (netlist, reference, summary)),
                encoding="utf-8",
            )
            result = audit.audit_archive(archive, "test", root)
            self.assertEqual(result["netlist"]["module_occurrences"]["CHILD"], 2)
            self.assertEqual(result["netlist"]["reference_direct_leaf_count"], 3)
            self.assertEqual(result["netlist"]["reference_expanded_leaf_count"], 5)
            self.assertEqual(result["area_reconciliation"]["leaf_area"], "9.000000000000")
            self.assertEqual(result["count_reconciliation"]["status"], "CONSISTENT")
            self.assertEqual(result["count_reconciliation"]["expanded_nonleaf_instance_occurrences"], 2)

    def test_leaf_and_hierarchy_inclusive_cell_counts_are_both_recognized(self) -> None:
        for reported, expected in (
            (3, "CONSISTENT"),
            (4, "CONSISTENT_INCLUDING_HIERARCHY"),
            (5, "UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH"),
        ):
            with self.subTest(reported=reported), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = _make_archive(root, reported_cells=reported)
                result = audit.audit_archive(archive, "test", root)
                count = result["count_reconciliation"]
                self.assertEqual(count["status"], expected)
                self.assertEqual(count["expanded_nonleaf_instance_occurrences"], 1)
                self.assertEqual(count["expanded_leaf_plus_nonleaf_instances"], 4)
                self.assertEqual(count["delta_reported_minus_leaf_plus_nonleaf_count"],
                                 reported - 4)
                count_warnings = [w for w in result["warnings"] if "number_of_cells=" in w]
                self.assertEqual(bool(count_warnings), reported == 5)

    def test_all_five_ownership_categories(self) -> None:
        leaf = audit.Leaf(
            path=("TOP", "u"), module_type="DFFX1_RVT", instance_name="u",
            containing_module="TOP", ancestor_module_types=("TOP",), line_number=1,
        )
        cases = (
            ("cxl_desc_fifo_test", "desc_mem_q_reg_0", "descriptor_storage"),
            ("cxl_desc_fifo_test", "gen_ts_ts_mem_q_reg_0", "timestamp_storage"),
            ("cxl_fai_main_sched_test", "u", "policy"),
            ("cxl_out_hold_test", "u", "common"),
            ("unknown", "u", "unresolved"),
        )
        for module, instance, expected in cases:
            with self.subTest(category=expected):
                candidate = replace(leaf, instance_name=instance,
                                    ancestor_module_types=("TOP", module))
                self.assertEqual(audit.classify_leaf(candidate, "TOP")[0], expected)

    def test_area_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = _make_archive(Path(temp))
            summary = audit.parse_area_summary(archive / "reports/area_summary.rpt")
            changed = replace(summary, values={**summary.values, "total_cell_area": Decimal("6")})
            with patch.object(audit, "parse_area_summary", return_value=changed):
                with self.assertRaisesRegex(audit.AuditError, "differs from area summary"):
                    audit.audit_archive(archive, "test", Path(temp))

    def test_printed_rounding_bound_is_derived_and_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = _make_archive(root)
            rows = tuple(
                audit.ReferenceRow(f"C{i}", "fake", Decimal("0.000001"), 1,
                                   Decimal("0.000001"), frozenset(), 1)
                for i in range(25)
            )
            sections = {"TOP": audit.ReferenceSection(
                "TOP", rows, 25, Decimal("0.000036"), 1
            )}
            netlist = _parse_netlist(
                "module TOP(a); input a;\n"
                + "\n".join(f"C{i} u{i}(.a(a));" for i in range(25))
                + "\nendmodule\n"
            )
            summary = audit.parse_area_summary(archive / "reports/area_summary.rpt")
            values = {**summary.values, "total_cell_area": Decimal("0.000036"),
                      "number_of_cells": Decimal(25),
                      "number_of_combinational_cells": Decimal(25),
                      "number_of_references": Decimal(25)}
            with patch.object(audit, "parse_netlist", return_value=netlist), \
                 patch.object(audit, "parse_reference_report", return_value=sections), \
                 patch.object(audit, "parse_area_summary",
                              return_value=replace(summary, values=values)):
                result = audit.audit_archive(archive, "test", root)
                area = result["area_reconciliation"]
                self.assertEqual(area["residual_vs_summary"], "-0.000011000000")
                self.assertEqual(area["printed_rounding_bound"], "0.000013000000")
                values["total_cell_area"] = Decimal("0.000039")
                with self.assertRaisesRegex(audit.AuditError, "differs from area summary"):
                    audit.audit_archive(archive, "test", root)


if __name__ == "__main__":
    unittest.main()
