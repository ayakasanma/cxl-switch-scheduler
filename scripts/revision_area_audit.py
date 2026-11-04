#!/usr/bin/env python3
"""Offline, provenance-checked area attribution for archived mapped netlists.

The audit uses only archived Design Compiler netlists and reports.  It expands
the mapped hierarchy to leaf-cell instances, assigns every leaf exactly once,
and reconciles Decimal areas against the archived report totals.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Iterable, Mapping, Sequence


AREA_TOLERANCE = Decimal("0.00001")
UNIT_AREA_TOLERANCE = Decimal("0.00001")
SCHEMA_VERSION = 1

POLICY_PREFIXES = (
    "cxl_fcfs_sel",
    "cxl_rr_sched",
    "cxl_fai_main_sched",
)
FIFO_PREFIX = "cxl_desc_fifo"
OUT_HOLD_PREFIX = "cxl_out_hold"
TOP_GLUE_PREFIXES = ("switch_top_DW",)

DECLARATION_KEYWORDS = {
    "assign",
    "genvar",
    "inout",
    "input",
    "integer",
    "localparam",
    "output",
    "parameter",
    "reg",
    "supply0",
    "supply1",
    "tri",
    "wire",
}


class AuditError(RuntimeError):
    """Raised when archived evidence is malformed or inconsistent."""


@dataclass(frozen=True)
class ReferenceRow:
    reference: str
    library: str | None
    reported_unit_area: Decimal
    count: int
    total_area: Decimal
    attributes: frozenset[str]
    line_number: int

    @property
    def implied_unit_area(self) -> Decimal:
        return self.total_area / Decimal(self.count)

    @property
    def hierarchical(self) -> bool:
        return "h" in self.attributes


@dataclass(frozen=True)
class ReferenceSection:
    name: str
    rows: tuple[ReferenceRow, ...]
    total_unique_references: int
    total_area: Decimal
    line_number: int


@dataclass(frozen=True)
class Instance:
    module_type: str
    instance_name: str
    line_number: int


@dataclass(frozen=True)
class Module:
    name: str
    instances: tuple[Instance, ...]
    line_number: int


@dataclass(frozen=True)
class Netlist:
    modules: Mapping[str, Module]
    top_module: str


@dataclass(frozen=True)
class Leaf:
    path: tuple[str, ...]
    module_type: str
    instance_name: str
    containing_module: str
    ancestor_module_types: tuple[str, ...]
    line_number: int

    @property
    def path_text(self) -> str:
        return "/".join(self.path)


@dataclass(frozen=True)
class AttributedLeaf:
    leaf: Leaf
    category: str
    reason: str
    area: Decimal


@dataclass(frozen=True)
class AreaSummary:
    values: Mapping[str, Decimal]
    source_path: Path


def _decimal(value: str | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _format_decimal(value: Decimal, places: int = 12) -> str:
    quantum = Decimal(1).scaleb(-places)
    with localcontext() as context:
        context.prec = 50
        return format(value.quantize(quantum), "f")


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _normalize_attributes(text: str | None) -> frozenset[str]:
    if not text:
        return frozenset()
    return frozenset(part for part in re.split(r"[,\s]+", text.strip()) if part)


def _strip_verilog_comments(text: str) -> str:
    text = re.sub(
        r"/\*.*?\*/", lambda match: re.sub(r"[^\n]", " ", match.group()),
        text, flags=re.DOTALL,
    )
    return re.sub(r"//[^\n]*", lambda match: " " * len(match.group()), text)


def parse_reference_report(path: Path) -> dict[str, ReferenceSection]:
    """Parse all per-module local report_reference sections."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditError(f"cannot read reference report {path}: {exc}") from exc

    lines = text.splitlines()
    heading_pattern = re.compile(r"^Design\s*:\s*(\S+)\s*$")
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = heading_pattern.match(line)
        if match:
            headings.append((index, match.group(1)))

    if not headings:
        raise AuditError(f"{path}: no 'Design :' report sections found")

    sections: dict[str, ReferenceSection] = {}
    row_pattern = re.compile(
        r"^\s*([0-9]+\.[0-9]+)\s+(\d+)\s+([0-9]+\.[0-9]+)"
        r"(?:\s+(.*?))?\s*$"
    )
    total_pattern = re.compile(r"^Total\s+(\d+)\s+references\s+([0-9]+\.[0-9]+)\s*$")
    separator_pattern = re.compile(r"^-{5,}\s*$")

    for position, (start, name) in enumerate(headings):
        if name in sections:
            raise AuditError(f"{path}:{start + 1}: duplicate Design section {name}")
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        block = lines[start:end]
        separator_index = next(
            (index for index, line in enumerate(block) if separator_pattern.match(line)),
            None,
        )
        if separator_index is None:
            raise AuditError(f"{path}:{start + 1}: section {name} has no row separator")

        rows: list[ReferenceRow] = []
        total_unique: int | None = None
        section_total: Decimal | None = None
        index = separator_index + 1
        while index < len(block):
            raw = block[index]
            stripped = raw.strip()
            total_match = total_pattern.match(stripped)
            if total_unique is not None:
                if not stripped or set(stripped) == {"*"} or stripped == "1":
                    index += 1
                    continue
                raise AuditError(
                    f"{path}:{start + index + 1}: unexpected content after Total"
                )
            if total_match:
                if total_unique is not None:
                    raise AuditError(f"{path}:{start + index + 1}: duplicate Total row")
                total_unique = int(total_match.group(1))
                section_total = _decimal(total_match.group(2))
                index += 1
                continue
            if not stripped or separator_pattern.match(stripped) or stripped.startswith("Reference"):
                index += 1
                continue
            if raw[:1].isspace():
                raise AuditError(
                    f"{path}:{start + index + 1}: orphan area row in section {name}"
                )

            parts = stripped.split()
            if len(parts) not in (1, 2):
                raise AuditError(f"{path}:{start + index + 1}: malformed reference name row")
            reference = parts[0]
            library = parts[1] if len(parts) > 1 else None
            area_index = index + 1
            while area_index < len(block) and not block[area_index].strip():
                area_index += 1
            if area_index >= len(block):
                raise AuditError(
                    f"{path}:{start + index + 1}: truncated row for {reference}"
                )
            area_match = row_pattern.match(block[area_index])
            if not area_match:
                raise AuditError(
                    f"{path}:{start + area_index + 1}: malformed area row for {reference}"
                )
            unit_area = _decimal(area_match.group(1))
            count = int(area_match.group(2))
            total_area = _decimal(area_match.group(3))
            attributes = _normalize_attributes(area_match.group(4))
            if count <= 0:
                raise AuditError(
                    f"{path}:{start + area_index + 1}: nonpositive count for {reference}"
                )
            implied = total_area / Decimal(count)
            if abs(implied - unit_area) > UNIT_AREA_TOLERANCE:
                raise AuditError(
                    f"{path}:{start + area_index + 1}: reported unit area for "
                    f"{reference} differs from total/count by {abs(implied - unit_area)}"
                )
            rows.append(
                ReferenceRow(
                    reference=reference,
                    library=library,
                    reported_unit_area=unit_area,
                    count=count,
                    total_area=total_area,
                    attributes=attributes,
                    line_number=start + area_index + 1,
                )
            )
            index = area_index + 1

        if total_unique is None or section_total is None:
            raise AuditError(f"{path}:{start + 1}: section {name} is missing Total row")
        if len(rows) != total_unique:
            raise AuditError(
                f"{path}:{start + 1}: section {name} has {len(rows)} rows but "
                f"Total says {total_unique} references"
            )
        references = [row.reference for row in rows]
        if len(set(references)) != len(references):
            raise AuditError(f"{path}:{start + 1}: duplicate reference row in {name}")
        summed_area = sum((row.total_area for row in rows), Decimal(0))
        if abs(summed_area - section_total) > AREA_TOLERANCE:
            raise AuditError(
                f"{path}:{start + 1}: section {name} rows sum to {summed_area}, "
                f"but Total is {section_total}"
            )
        sections[name] = ReferenceSection(
            name=name,
            rows=tuple(rows),
            total_unique_references=total_unique,
            total_area=section_total,
            line_number=start + 1,
        )

    return sections


def parse_netlist(path: Path) -> Netlist:
    """Parse a mapped structural Verilog netlist and its module definitions."""

    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditError(f"cannot read mapped netlist {path}: {exc}") from exc
    text = _strip_verilog_comments(original)
    text = re.sub(
        r"\(\*.*?\*\)", lambda match: re.sub(r"[^\n]", " ", match.group()),
        text, flags=re.DOTALL,
    )

    module_pattern = re.compile(
        r"\bmodule\s+([A-Za-z_$][A-Za-z0-9_$]*)"
        r"\s*(?:#\s*\(.*?\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
        re.DOTALL,
    )
    matches = list(module_pattern.finditer(text))
    if not matches:
        raise AuditError(f"{path}: no complete module definitions found")
    if (
        len(re.findall(r"\bmodule\b", text)) != len(matches)
        or len(re.findall(r"\bendmodule\b", text)) != len(matches)
        or module_pattern.sub("", text).strip()
    ):
        raise AuditError(f"{path}: malformed or truncated module definition")

    modules: dict[str, Module] = {}
    instance_pattern = re.compile(
        r"^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s+"
        r"([A-Za-z_$][A-Za-z0-9_$]*)\s*"
        r"\((.*)\)\s*$",
        re.DOTALL,
    )
    for match in matches:
        name = match.group(1)
        if name in modules:
            raise AuditError(f"{path}: duplicate module {name}")
        body = match.group(3)
        module_line = _line_of_offset(text, match.start())
        instances: list[Instance] = []
        local_names: set[str] = set()
        if body.rsplit(";", 1)[-1].strip():
            raise AuditError(f"{path}:{module_line}: unterminated statement in {name}")
        statement_line = _line_of_offset(text, match.start(3))
        for statement in body.split(";"):
            leading_space = statement[:len(statement) - len(statement.lstrip())]
            line_number = statement_line + leading_space.count("\n")
            statement_line += statement.count("\n")
            stripped = statement.strip()
            if not stripped:
                continue
            first_token = stripped.split(None, 1)[0]
            if first_token in DECLARATION_KEYWORDS:
                continue
            instance_match = instance_pattern.match(stripped)
            if not instance_match:
                excerpt = " ".join(stripped.split())[:100]
                raise AuditError(
                    f"{path}:{module_line}: unparsed statement in {name}: {excerpt}"
                )
            module_type = instance_match.group(1)
            instance_name = instance_match.group(2)
            depth = 0
            for character in instance_match.group(3):
                depth += (character == "(") - (character == ")")
                if depth < 0:
                    raise AuditError(f"{path}:{line_number}: unsupported multiple instances or unmatched parentheses")
            if depth:
                raise AuditError(f"{path}:{line_number}: unmatched instance parentheses")
            if instance_name in local_names:
                raise AuditError(
                    f"{path}:{module_line}: duplicate local instance "
                    f"{name}/{instance_name}"
                )
            local_names.add(instance_name)
            instances.append(
                Instance(
                    module_type=module_type,
                    instance_name=instance_name,
                    line_number=line_number,
                )
            )
        modules[name] = Module(name=name, instances=tuple(instances), line_number=module_line)

    return Netlist(modules=modules, top_module="")


def expand_leaf_instances(netlist: Netlist, top_module: str) -> tuple[tuple[Leaf, ...], dict[str, int]]:
    """Recursively expand hierarchy, rejecting cycles and duplicate full paths."""

    if top_module not in netlist.modules:
        raise AuditError(f"top module {top_module} not found in netlist")

    leaves: list[Leaf] = []
    seen_paths: set[tuple[str, ...]] = set()
    module_occurrences: Counter[str] = Counter()

    def walk(
        module_name: str,
        path: tuple[str, ...],
        ancestor_types: tuple[str, ...],
        stack: tuple[str, ...],
    ) -> None:
        if module_name in stack:
            cycle = " -> ".join((*stack, module_name))
            raise AuditError(f"hierarchical module cycle: {cycle}")
        module = netlist.modules[module_name]
        module_occurrences[module_name] += 1
        next_stack = (*stack, module_name)
        next_types = (*ancestor_types, module_name)
        for instance in module.instances:
            instance_path = (*path, instance.instance_name)
            if instance.module_type in netlist.modules:
                walk(
                    instance.module_type,
                    instance_path,
                    next_types,
                    next_stack,
                )
                continue
            if instance_path in seen_paths:
                raise AuditError(f"duplicate full leaf path: {'/'.join(instance_path)}")
            seen_paths.add(instance_path)
            leaves.append(
                Leaf(
                    path=instance_path,
                    module_type=instance.module_type,
                    instance_name=instance.instance_name,
                    containing_module=module_name,
                    ancestor_module_types=next_types,
                    line_number=instance.line_number,
                )
            )

    walk(top_module, (top_module,), (), ())
    unreachable = sorted(set(netlist.modules) - set(module_occurrences))
    if unreachable:
        raise AuditError(f"unreachable netlist modules: {', '.join(unreachable)}")
    return tuple(sorted(leaves, key=lambda leaf: leaf.path)), dict(module_occurrences)


def validate_reference_matches_netlist(
    netlist: Netlist,
    sections: Mapping[str, ReferenceSection],
) -> dict[str, object]:
    """Check module/leaf separation and local instance counts."""

    module_names = set(netlist.modules)
    report_names = set(sections)
    missing_sections = sorted(module_names - report_names)
    extra_sections = sorted(report_names - module_names)
    if missing_sections:
        raise AuditError(f"missing reference sections: {', '.join(missing_sections)}")
    if extra_sections:
        raise AuditError(f"reference sections without netlist modules: {', '.join(extra_sections)}")

    direct_instance_count = 0
    direct_leaf_count = 0
    for module_name, module in sorted(netlist.modules.items()):
        section = sections[module_name]
        netlist_counts = Counter(instance.module_type for instance in module.instances)
        report_counts = Counter()
        for row in section.rows:
            report_counts[row.reference] += row.count
            is_hierarchical = row.reference in module_names
            if is_hierarchical != row.hierarchical:
                kind = "hierarchical" if is_hierarchical else "leaf"
                raise AuditError(
                    f"reference row {module_name}/{row.reference} is {kind} in "
                    "netlist but its 'h' attribute disagrees"
                )
        if netlist_counts != report_counts:
            missing = sorted((netlist_counts - report_counts).items())
            extra = sorted((report_counts - netlist_counts).items())
            raise AuditError(
                f"reference/netlist local instance mismatch in {module_name}: "
                f"missing={missing}, extra={extra}"
            )
        direct_instance_count += sum(netlist_counts.values())
        direct_leaf_count += sum(
            count for module_type, count in netlist_counts.items() if module_type not in module_names
        )

    return {
        "direct_instance_count": direct_instance_count,
        "direct_leaf_count": direct_leaf_count,
        "section_count": len(sections),
    }


def classify_leaf(leaf: Leaf, top_module: str) -> tuple[str, str]:
    """Return one disjoint category and a short rationale."""

    ancestors = leaf.ancestor_module_types
    if any(name.startswith(POLICY_PREFIXES) for name in ancestors):
        return "policy", "leaf is under a scheduler policy module"

    if any(name.startswith(FIFO_PREFIX) for name in ancestors):
        if "desc_mem_q_reg" in leaf.instance_name:
            return "descriptor_storage", "FIFO descriptor storage register"
        if "gen_ts_ts_mem_q_reg" in leaf.instance_name:
            return "timestamp_storage", "FIFO timestamp storage register"
        return "common", "non-storage logic inside a descriptor FIFO"

    if any(name.startswith(OUT_HOLD_PREFIX) for name in ancestors):
        return "common", "output-hold common logic"
    if any(name.startswith(TOP_GLUE_PREFIXES) for name in ancestors):
        return "common", "top-level glue/arithmetic"
    if len(ancestors) == 1 and ancestors[0] == top_module:
        return "common", "direct top-level glue"

    return "unresolved", "leaf is under no recognized ownership module"


class CategoryLedger:
    """Append-only ledger that prevents duplicate or overlapping attribution."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, ...], AttributedLeaf] = {}

    def add(self, entry: AttributedLeaf) -> None:
        path = entry.leaf.path
        if path in self._entries:
            raise AuditError(f"leaf attributed more than once: {'/'.join(path)}")
        self._entries[path] = entry

    @property
    def entries(self) -> tuple[AttributedLeaf, ...]:
        return tuple(self._entries[path] for path in sorted(self._entries))

    def totals(self) -> dict[str, dict[str, object]]:
        area: defaultdict[str, Decimal] = defaultdict(lambda: Decimal(0))
        counts: Counter[str] = Counter()
        cell_types: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for entry in self.entries:
            area[entry.category] += entry.area
            counts[entry.category] += 1
            cell_types[entry.category][entry.leaf.module_type] += 1
        result: dict[str, dict[str, object]] = {}
        for category in ("descriptor_storage", "timestamp_storage", "policy", "common", "unresolved"):
            result[category] = {
                "leaf_count": counts[category],
                "area": _format_decimal(area[category]),
                "cell_types": [
                    {"type": cell_type, "count": count}
                    for cell_type, count in sorted(cell_types[category].items())
                ],
            }
        return result


def attribute_leaves(
    leaves: Sequence[Leaf],
    sections: Mapping[str, ReferenceSection],
    top_module: str,
) -> tuple[CategoryLedger, Decimal]:
    ledger = CategoryLedger()
    leaf_area = Decimal(0)
    row_maps = {
        name: {row.reference: row for row in section.rows}
        for name, section in sections.items()
    }
    for leaf in leaves:
        row = row_maps[leaf.containing_module].get(leaf.module_type)
        if row is None:
            raise AuditError(
                f"missing reference row for leaf {leaf.path_text} "
                f"({leaf.containing_module}/{leaf.module_type})"
            )
        # The archived totals are rounded. Keep a reproducible Decimal share;
        # the small residual against the original total remains explicit.
        area = row.implied_unit_area.quantize(Decimal("0.000000000001"))
        category, reason = classify_leaf(leaf, top_module)
        ledger.add(AttributedLeaf(leaf=leaf, category=category, reason=reason, area=area))
        leaf_area += area
    return ledger, leaf_area


def parse_area_summary(path: Path) -> AreaSummary:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AuditError(f"cannot read area summary {path}: {exc}") from exc
    values: dict[str, Decimal] = {}
    pattern = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$")
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            if match.group(1) in values:
                raise AuditError(f"{path}: duplicate area-summary field {match.group(1)}")
            values[match.group(1)] = _decimal(match.group(2))
    required = (
        "total_cell_area",
        "number_of_cells",
        "number_of_combinational_cells",
        "number_of_sequential_cells",
        "number_of_references",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise AuditError(f"{path}: missing area-summary fields: {', '.join(missing)}")
    if any(value != value.to_integral_value() for key, value in values.items() if key.startswith("number_of_")):
        raise AuditError(f"{path}: noninteger cell/count field")
    return AreaSummary(values=values, source_path=path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AuditError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def verify_result_checksums(archive: Path) -> tuple[dict[str, str], str]:
    sums_path = archive / "RESULT_SHA256SUMS"
    try:
        lines = sums_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AuditError(f"cannot read {sums_path}: {exc}") from exc
    entries: dict[str, str] = {}
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        match = re.match(r"^([0-9a-f]{64})\s+(.+?)\s*$", line)
        if not match:
            raise AuditError(f"{sums_path}:{index}: malformed checksum line")
        expected, relative = match.groups()
        candidate = (archive / relative).resolve()
        if not candidate.is_relative_to(archive.resolve()):
            raise AuditError(f"{sums_path}:{index}: checksum path escapes archive")
        if relative in entries:
            raise AuditError(f"{sums_path}:{index}: duplicate checksum path {relative}")
        entries[relative] = expected
    if not entries:
        raise AuditError(f"{sums_path}: no checksum entries")
    for relative, expected in sorted(entries.items()):
        candidate = archive / relative
        if not candidate.is_file():
            raise AuditError(f"checksummed file is missing: {candidate}")
        actual = sha256_file(candidate)
        if actual != expected:
            raise AuditError(
                f"checksum mismatch for {relative}: expected {expected}, got {actual}"
            )
    return entries, sha256_file(sums_path)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read JSON {path}: {exc}") from exc


def validate_manifest_and_parameters(
    archive: Path,
    parameters: Mapping[str, object],
    parameters_sha256: str,
) -> tuple[dict[str, object], str]:
    manifest_path = archive / "manifest.json"
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise AuditError(f"{manifest_path}: top-level JSON value is not an object")
    if manifest.get("parameters") != parameters:
        raise AuditError(f"{manifest_path}: parameters do not match parameters.json")
    file_hashes = manifest.get("file_sha256")
    if not isinstance(file_hashes, dict):
        raise AuditError(f"{manifest_path}: file_sha256 object is missing")
    expected = file_hashes.get("parameters.json")
    if expected != parameters_sha256:
        raise AuditError(
            f"{manifest_path}: file_sha256['parameters.json'] is {expected}, "
            f"actual is {parameters_sha256}"
        )
    return manifest, sha256_file(manifest_path)


def storage_observations(leaves: Iterable[Leaf]) -> dict[str, int]:
    descriptor = 0
    timestamp = 0
    arrival_counter = 0
    for leaf in leaves:
        if "desc_mem_q_reg" in leaf.instance_name:
            descriptor += 1
        if "gen_ts_ts_mem_q_reg" in leaf.instance_name:
            timestamp += 1
        if "gen_arrival_ts_arrival_cnt_q_reg" in leaf.instance_name:
            arrival_counter += 1
    return {
        "descriptor_storage_bits": descriptor,
        "timestamp_storage_bits": timestamp,
        "top_arrival_counter_bits": arrival_counter,
    }


def validate_storage(
    parameters: Mapping[str, object],
    leaves: Sequence[Leaf],
) -> dict[str, object]:
    n_src = int(parameters["N_SRC"])
    depth = int(parameters["D"])
    desc_width = int(parameters["DESC_W"])
    arrival_metadata = bool(parameters["arrival_metadata"])
    expected_descriptor = n_src * depth * desc_width
    expected_timestamp = n_src * depth * 32 if arrival_metadata else 0
    observed = storage_observations(leaves)

    expected_block = parameters.get("expected")
    if isinstance(expected_block, dict):
        if "descriptor_storage_bits" in expected_block:
            declared = int(expected_block["descriptor_storage_bits"])
            if declared != expected_descriptor:
                raise AuditError(
                    f"parameters expected descriptor bits {declared}, formula gives "
                    f"{expected_descriptor}"
                )
        if "timestamp_storage_bits" in expected_block:
            declared = int(expected_block["timestamp_storage_bits"])
            if declared != expected_timestamp:
                raise AuditError(
                    f"parameters expected timestamp bits {declared}, formula gives "
                    f"{expected_timestamp}"
                )

    if observed["descriptor_storage_bits"] != expected_descriptor:
        raise AuditError(
            f"observed descriptor storage {observed['descriptor_storage_bits']} bits, "
            f"expected {expected_descriptor}"
        )
    if observed["timestamp_storage_bits"] != expected_timestamp:
        raise AuditError(
            f"observed timestamp storage {observed['timestamp_storage_bits']} bits, "
            f"expected {expected_timestamp}"
        )
    policy_name = str(parameters.get("policy_name", ""))
    if policy_name == "rr" and (
        observed["timestamp_storage_bits"] != 0
        or observed["top_arrival_counter_bits"] != 0
        or arrival_metadata
    ):
        raise AuditError("RR archive contains timestamp/arrival storage")

    return {
        "expected_descriptor_storage_bits": expected_descriptor,
        "expected_timestamp_storage_bits": expected_timestamp,
        **observed,
        "descriptor_match": True,
        "timestamp_match": True,
        "rr_timestamp_zero": policy_name != "rr" or observed["timestamp_storage_bits"] == 0,
    }


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_leaf_inventory(
    path: Path,
    ledger: CategoryLedger,
    sections: Mapping[str, ReferenceSection],
) -> dict[str, object]:
    """Write a deterministic compressed inventory, never replacing evidence."""
    row_maps = {
        name: {row.reference: row for row in section.rows}
        for name, section in sections.items()
    }
    with path.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="ascii", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow((
                    "path", "cell_type", "category", "area", "containing_module",
                    "netlist_line", "reference_report_line", "reported_unit_area",
                    "reference_row_count", "reference_row_total_area", "reason",
                ))
                for entry in ledger.entries:
                    leaf = entry.leaf
                    row = row_maps[leaf.containing_module][leaf.module_type]
                    writer.writerow((
                        leaf.path_text, leaf.module_type, entry.category,
                        _format_decimal(entry.area), leaf.containing_module,
                        leaf.line_number, row.line_number,
                        str(row.reported_unit_area), row.count, str(row.total_area),
                        entry.reason,
                    ))
    return {"filename": path.name, "sha256": sha256_file(path), "leaf_count": len(ledger.entries)}


def audit_archive(
    archive: Path, case_id: str, repo_root: Path,
    inventory_dir: Path | None = None,
) -> dict[str, object]:
    archive = archive.resolve()
    netlist_path = archive / "output/switch_top.syn.v"
    reference_path = archive / "reports/reference.rpt"
    summary_path = archive / "reports/area_summary.rpt"
    parameters_path = archive / "parameters.json"
    manifest_path = archive / "manifest.json"
    sums_path = archive / "RESULT_SHA256SUMS"

    for required in (
        netlist_path,
        reference_path,
        summary_path,
        parameters_path,
        manifest_path,
        sums_path,
    ):
        if not required.is_file() or required.stat().st_size == 0:
            raise AuditError(f"required archived input is missing/empty: {required}")

    sums_entries, sums_sha256 = verify_result_checksums(archive)
    required_sum_paths = (
        "output/switch_top.syn.v",
        "reports/reference.rpt",
        "reports/area_summary.rpt",
    )
    for required in required_sum_paths:
        if required not in sums_entries:
            raise AuditError(f"{sums_path}: required path absent: {required}")

    parameters = _load_json(parameters_path)
    if not isinstance(parameters, dict):
        raise AuditError(f"{parameters_path}: top-level JSON value is not an object")
    parameters_sha256 = sha256_file(parameters_path)
    manifest, manifest_sha256 = validate_manifest_and_parameters(
        archive, parameters, parameters_sha256
    )

    parsed_netlist = parse_netlist(netlist_path)
    top_module = str(parameters["top_module"])
    if top_module not in parsed_netlist.modules:
        raise AuditError(f"{netlist_path}: configured top module {top_module} not found")
    netlist = Netlist(modules=parsed_netlist.modules, top_module=top_module)
    leaves, module_occurrences = expand_leaf_instances(netlist, top_module)

    sections = parse_reference_report(reference_path)
    if top_module not in sections:
        raise AuditError(f"{reference_path}: top section {top_module} is absent")
    local_checks = validate_reference_matches_netlist(netlist, sections)
    ledger, leaf_area = attribute_leaves(leaves, sections, top_module)
    summary = parse_area_summary(summary_path)
    total_cell_area = summary.values["total_cell_area"]
    reference_top_area = sections[top_module].total_area
    area_residual = leaf_area - total_cell_area
    # Each printed row total and the summary can differ by half a last digit.
    printed_rounding_bound = (
        sum(
            (Decimal(1).scaleb(row.total_area.as_tuple().exponent)
             * module_occurrences[name] / 2
             for name, section in sections.items()
             for row in section.rows if not row.hierarchical),
            Decimal(0),
        )
        + Decimal(1).scaleb(total_cell_area.as_tuple().exponent) / 2
    )
    allocation_rounding_bound = Decimal("0.0000000000005") * len(leaves)
    area_tolerance = max(
        AREA_TOLERANCE, printed_rounding_bound + allocation_rounding_bound
    )
    if abs(area_residual) > area_tolerance:
        raise AuditError(
            f"leaf area {leaf_area} differs from area summary total {total_cell_area} "
            f"by {area_residual}"
        )
    if abs(reference_top_area - total_cell_area) > AREA_TOLERANCE:
        raise AuditError(
            f"reference top area {reference_top_area} differs from summary "
            f"total {total_cell_area}"
        )

    category_totals = ledger.totals()
    category_area_sum = sum(
        (_decimal(item["area"]) for item in category_totals.values()),
        Decimal(0),
    )
    if category_area_sum != leaf_area:
        raise AuditError(
            f"category area sum {category_area_sum} differs from leaf area {leaf_area}"
        )

    leaf_count = len(leaves)
    combinational = int(summary.values["number_of_combinational_cells"])
    sequential = int(summary.values["number_of_sequential_cells"])
    comb_plus_seq = combinational + sequential
    reported_cells = int(summary.values["number_of_cells"])
    if comb_plus_seq != leaf_count:
        raise AuditError(
            f"combinational+sequential={comb_plus_seq}, expanded leaves={leaf_count}"
        )
    reference_expanded_leaf_count = sum(
        row.count * module_occurrences[name]
        for name, section in sections.items()
        for row in section.rows if not row.hierarchical
    )
    if reference_expanded_leaf_count != leaf_count:
        raise AuditError(
            f"reference leaf instances={reference_expanded_leaf_count}, "
            f"expanded leaves={leaf_count}"
        )
    top_rows = sections[top_module].total_unique_references
    if int(summary.values["number_of_references"]) != top_rows:
        raise AuditError(
            f"summary number_of_references={summary.values['number_of_references']} "
            f"but top report has {top_rows} rows"
        )

    nonleaf_count = sum(module_occurrences.values()) - 1  # Exclude the root design.
    expanded_instance_count = leaf_count + nonleaf_count
    if reported_cells == leaf_count:
        count_field_status = "CONSISTENT"
    elif reported_cells == expanded_instance_count:
        count_field_status = "CONSISTENT_INCLUDING_HIERARCHY"
    else:
        count_field_status = "UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH"
    warnings: list[str] = []
    if count_field_status == "UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH":
        warnings.append(
            "area_summary.rpt number_of_cells="
            f"{reported_cells}, combinational+sequential=expanded leaves={leaf_count}, "
            f"expanded nonleaf occurrences={nonleaf_count}; "
            f"unexplained delta after hierarchy={reported_cells - expanded_instance_count}"
        )
    unresolved_count = int(category_totals["unresolved"]["leaf_count"])
    if unresolved_count:
        warnings.append(f"{unresolved_count} leaves have unresolved ownership")

    storage = validate_storage(parameters, leaves)
    unresolved_examples = [
        {
            "path": entry.leaf.path_text,
            "cell_type": entry.leaf.module_type,
            "area": _format_decimal(entry.area),
            "reason": entry.reason,
        }
        for entry in ledger.entries
        if entry.category == "unresolved"
    ][:25]

    file_hashes = {
        "mapped_netlist": sha256_file(netlist_path),
        "reference_report": sha256_file(reference_path),
        "area_summary": sha256_file(summary_path),
        "parameters_json": parameters_sha256,
        "manifest_json": manifest_sha256,
        "result_sha256sums": sums_sha256,
    }
    source = manifest.get("source", {})
    source_head = source.get("head") if isinstance(source, dict) else None
    selected_parameters = {
        key: parameters.get(key)
        for key in (
            "top_module",
            "policy_name",
            "N_SRC",
            "D",
            "DESC_W",
            "arrival_metadata",
        )
    }
    reference_leaf_area = sum(
        (
            row.total_area * module_occurrences[name]
            for name, section in sections.items()
            for row in section.rows if not row.hierarchical
        ),
        Decimal(0),
    )
    inventory = None
    if inventory_dir is not None:
        inventory = write_leaf_inventory(
            inventory_dir / f"{case_id}-leaves.csv.gz", ledger, sections
        )

    return {
        "case_id": case_id,
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "archive": _relative_path(archive, repo_root),
        "inputs": {
            name: _relative_path(archive / relative, repo_root)
            for name, relative in (
                ("mapped_netlist", "output/switch_top.syn.v"),
                ("reference_report", "reports/reference.rpt"),
                ("area_summary", "reports/area_summary.rpt"),
                ("parameters_json", "parameters.json"),
                ("manifest_json", "manifest.json"),
                ("result_sha256sums", "RESULT_SHA256SUMS"),
            )
        },
        "provenance": {
            "sha256": file_hashes,
            "manifest_source_head": source_head,
            "manifest_parameters_sha256_match": True,
            "result_checksum_entries_verified": len(sums_entries),
            "all_result_checksums_verified": True,
        },
        "parameters": selected_parameters,
        "netlist": {
            "module_count": len(netlist.modules),
            "module_occurrences": dict(sorted(module_occurrences.items())),
            "leaf_instance_count": leaf_count,
            "reference_section_count": local_checks["section_count"],
            "reference_direct_instance_count": local_checks["direct_instance_count"],
            "reference_direct_leaf_count": local_checks["direct_leaf_count"],
            "reference_expanded_leaf_count": reference_expanded_leaf_count,
        },
        "area_reconciliation": {
            "leaf_area": _format_decimal(leaf_area),
            "reference_top_area": _format_decimal(reference_top_area),
            "area_summary_total_cell_area": _format_decimal(total_cell_area),
            "residual_vs_summary": _format_decimal(area_residual),
            "summary_minus_leaf_area": _format_decimal(-area_residual),
            "reference_leaf_row_total_area": _format_decimal(reference_leaf_area),
            "leaf_allocation_minus_reference_rows": _format_decimal(leaf_area - reference_leaf_area),
            "exact_category_plus_residual_equals_summary": category_area_sum - area_residual == total_cell_area,
            "printed_rounding_bound": _format_decimal(printed_rounding_bound),
            "allocation_rounding_bound": _format_decimal(allocation_rounding_bound),
            "tolerance": _format_decimal(area_tolerance),
            "reconciled": True,
        },
        "count_reconciliation": {
            "reported_number_of_cells": reported_cells,
            "number_of_combinational_cells": combinational,
            "number_of_sequential_cells": sequential,
            "combinational_plus_sequential": comb_plus_seq,
            "expanded_netlist_leaves": leaf_count,
            "expanded_nonleaf_instance_occurrences": nonleaf_count,
            "expanded_leaf_plus_nonleaf_instances": expanded_instance_count,
            "delta_reported_minus_leaf_count": reported_cells - leaf_count,
            "delta_reported_minus_leaf_plus_nonleaf_count": reported_cells - expanded_instance_count,
            "status": count_field_status,
            "number_of_references": int(summary.values["number_of_references"]),
            "top_reference_rows": top_rows,
        },
        "attribution": {
            "classification_policy": {
                "policy": "any ancestor module type starts with cxl_fcfs_sel, cxl_rr_sched, or cxl_fai_main_sched",
                "descriptor_storage": "cxl_desc_fifo ancestor and instance name contains desc_mem_q_reg",
                "timestamp_storage": "cxl_desc_fifo ancestor and instance name contains gen_ts_ts_mem_q_reg",
                "common": "other cxl_desc_fifo logic, cxl_out_hold, top glue, or direct top-level logic",
                "unresolved": "no recognized ownership ancestor",
            },
            "categories": category_totals,
            "category_area_sum": _format_decimal(category_area_sum),
            "unresolved_examples": unresolved_examples,
        },
        "storage": storage,
        "leaf_inventory": inventory,
        "warnings": warnings,
    }


def default_case_specs() -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for n_src in (4, 8, 16):
        for policy, suffix in (("fcfs", "fcfs"), ("rr", "rr"), ("fai-main", "fai-main")):
            specs.append(
                (
                    f"n{n_src}-{policy}",
                    f"primary-20261021-v2-{suffix}-n{n_src}",
                )
            )
    return specs


def run_audit(
    archive_root: Path,
    repo_root: Path,
    case_ids: Sequence[str] | None = None,
    inventory_dir: Path | None = None,
) -> dict[str, object]:
    specs = default_case_specs()
    known = {case_id for case_id, _ in specs}
    if case_ids:
        unknown = sorted(set(case_ids) - known)
        if unknown:
            raise AuditError(f"unknown case ids: {', '.join(unknown)}")
        selected = [(case_id, directory) for case_id, directory in specs if case_id in case_ids]
    else:
        selected = specs

    cases: list[dict[str, object]] = []
    for case_id, directory in selected:
        archive = archive_root / directory
        if not archive.is_dir():
            raise AuditError(f"archive directory is missing: {archive}")
        cases.append(audit_archive(archive, case_id, repo_root, inventory_dir))

    count_inconsistent = sum(
        1
        for case in cases
        if case["count_reconciliation"]["status"] == "UNEXPLAINED_NUMBER_OF_CELLS_MISMATCH"
    )
    unresolved_cases = sum(
        1
        for case in cases
        if int(case["attribution"]["categories"]["unresolved"]["leaf_count"]) > 0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_script_sha256": sha256_file(Path(__file__)),
        "scope": {
            "description": "Offline area attribution from archived mapped netlists and Design Compiler reports",
            "archive_root": _relative_path(archive_root, repo_root),
            "case_count": len(cases),
            "area_arithmetic": "Decimal",
            "area_source": "reference.rpt total_area/count per local cell row",
            "minimum_area_tolerance": _format_decimal(AREA_TOLERANCE),
            "area_tolerance_rule": "max(minimum, summed half-last-digit bounds of occurrence-weighted leaf row totals and summary, plus per-leaf 0.5e-12 allocation bound)",
            "new_ppa_runs": False,
            "remote_access": False,
            "proprietary_libraries_copied": False,
        },
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "all_result_checksums_verified": all(
                bool(case["provenance"]["all_result_checksums_verified"]) for case in cases
            ),
            "all_areas_reconciled": all(
                bool(case["area_reconciliation"]["reconciled"]) for case in cases
            ),
            "unexplained_number_of_cells_mismatch_cases": count_inconsistent,
            "unresolved_attribution_cases": unresolved_cases,
            "total_expanded_leaf_instances": sum(
                int(case["netlist"]["leaf_instance_count"]) for case in cases
            ),
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Audit archived mapped-netlist area attribution without rerunning PPA "
            "or accessing remote/proprietary files."
        )
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=repo_root / "artifacts/fastx",
        help="directory containing primary-20261021-v2-* archives",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "artifacts/implementation/revision-area"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") / "results.json",
        help="new JSON result path; existing outputs are refused (default: fresh timestamp directory)",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="case id to run (repeatable); default is all nine primary cases",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.output.exists():
            raise AuditError(f"refusing to overwrite existing output: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        inventory_dir = args.output.parent / (args.output.stem + "-leaves")
        inventory_dir.mkdir(exist_ok=False)
        result = run_audit(args.archive_root, repo_root, args.cases, inventory_dir)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    except (AuditError, OSError, KeyError, ValueError) as exc:
        print(f"AREA_AUDIT_ERROR: {exc}", file=sys.stderr)
        return 1

    for case in result["cases"]:
        categories = case["attribution"]["categories"]
        print(
            f"{case['case_id']}: {case['status']} "
            f"leaves={case['netlist']['leaf_instance_count']} "
            f"area={case['area_reconciliation']['leaf_area']} "
            f"unresolved={categories['unresolved']['leaf_count']} "
            f"count_field={case['count_reconciliation']['status']}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
