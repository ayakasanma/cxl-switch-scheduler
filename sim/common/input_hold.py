"""Spec 4 input (producer) hold checker, evaluated from OBSERVED DUT input pins.

Spec 4: "An input producer retains its valid descriptor until push." A request that is offered
(in_valid[h]=1) in a non-reset cycle and not accepted (in_ready[h]=0) creates an obligation: in the
next cycle source h must still drive in_valid[h]=1 with the identical full 105-bit descriptor,
unless that next cycle is a reset cycle (rst_n=0; the reset edge ends the epoch and releases every
producer). The obligation repeats every cycle until the request is pushed (in_valid & in_ready in
a non-reset cycle) or a reset cycle occurs. Reset cycles never create an obligation.

The checker is pure Python (no cocotb), is stepped once per clock cycle by the harness with the
pin values sampled in that cycle, and has no enable/disable switch: it is active on every
non-reset clock transition of every test, including measurement -> drain entry, the drain itself
and drain completion. ``obligations()`` tells a well-behaved producer (the drain phase of the
harness) exactly which already-offered descriptors it must keep driving.
"""

from __future__ import annotations

from typing import Dict, List


class InputHoldViolation(AssertionError):
    """An offered, refused input request was withdrawn or changed before push/reset."""


class InputHoldChecker:
    def __init__(self, n_src: int) -> None:
        self.n = n_src
        self.pending: Dict[int, int] = {}  # source -> descriptor offered and refused last non-reset cycle
        self.checked = 0  # source-cycles whose hold obligation was verified
        self.cycles = 0  # cycles stepped

    def obligations(self) -> Dict[int, int]:
        """source -> descriptor that must be driven (valid=1, same bits) in the next cycle unless
        that cycle is a reset cycle."""
        return dict(self.pending)

    def step(self, cycle: int, rst_n: int, in_valid: int, in_ready: int, in_desc: List[int]) -> None:
        """Check this cycle's observed inputs against the previous cycle's obligations, then derive
        the obligations for the next cycle. Raises ``InputHoldViolation`` on a violation."""
        self.cycles += 1
        if not rst_n:
            self.pending = {}  # a reset cycle releases every producer and creates no obligation
            return
        for h, desc in sorted(self.pending.items()):
            if not (in_valid >> h) & 1:
                raise InputHoldViolation(
                    f"SPEC4 input hold violation at cycle {cycle}: source {h} valid withdrawn before push/reset"
                )
            if in_desc[h] != desc:
                raise InputHoldViolation(
                    f"SPEC4 input hold violation at cycle {cycle}: source {h} descriptor changed while "
                    f"valid and not accepted, diff {in_desc[h] ^ desc:#029x}"
                )
            self.checked += 1
        self.pending = {
            h: in_desc[h] for h in range(self.n) if (in_valid >> h) & 1 and not (in_ready >> h) & 1
        }
