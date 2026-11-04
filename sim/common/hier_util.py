"""Design-hierarchy inspection through the simulator's VPI view (cocotb handles)."""

from __future__ import annotations

from typing import List, Tuple

from cocotb.handle import HierarchyArrayObject, HierarchyObject


def hierarchy_paths(root) -> List[Tuple[str, str]]:
    """Every object the simulator exposes below ``root`` as (full path, handle class name).

    Scopes (modules, generate blocks) are descended into; signals and memories are listed but not
    expanded element by element.
    """
    found: List[Tuple[str, str]] = []

    def walk(handle) -> None:
        found.append((handle._path, type(handle).__name__))
        if isinstance(handle, (HierarchyObject, HierarchyArrayObject)):
            for child in handle:
                walk(child)

    walk(root)
    return found
