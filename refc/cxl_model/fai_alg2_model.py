"""Abstract cycle-level model of the complete switch under the supplementary FAI Algorithm-2
interpretation (POLICY=3).

Authority: specs/CXL_SPEC.md v1.0 section 8.6 (with 4, 5, 6, 8.1, 8.3-8.5 shared), D33, Option A
in specs/DECISIONS.md, and docs/phase-3-uarch/fai_alg2.md. The paper behavior is the owner's
supplied account of J. Li et al., FAI-CXL, ICPADS 2025, Algorithm 2; no IEEE PDF was inspected.
The single-output 10/10 alternation is the shared project reconstruction, not paper dispatch.

Authorship/independence: written from the spec text and the abstract Main model contract
(``fai_main_model``) before any FAI RTL body was read. It reuses the abstract FIFO/hold/FCFS/
visit/window mechanics of ``FaiMainSwitchModel`` unchanged and replaces only the interpretation
hook: state table, effective-class map and reset state. No RTL control code is copied.

Algorithm-2 states (deliberately distinct names from Main's previous-priority ``B_H``/``B_L``):

* ``STABLE_HIGH`` / ``STABLE_LOW``: stable effective High / Low;
* ``BUFFER_P_HIGH`` / ``BUFFER_P_LOW``: Buffer with stored target priority p. A Buffer request is
  serviced immediately in its target class p (it does NOT retain the previous effective class).

Spec 8.6 table: UP/DOWN from any Buffer settles stable High/Low; KEEP and the zero-service window
(evidence ``S0``) retain the current state, including a Buffer and its target - no cancellation.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .fai_main_model import EVIDENCES, HIGH, LOW, FaiMainSwitchModel

STABLE_HIGH = "STABLE_HIGH"
STABLE_LOW = "STABLE_LOW"
BUFFER_P_HIGH = "BUFFER_P_HIGH"
BUFFER_P_LOW = "BUFFER_P_LOW"
ALG2_STATES = (STABLE_HIGH, STABLE_LOW, BUFFER_P_HIGH, BUFFER_P_LOW)

# Effective class: stable states use their own class, Buffer uses its stored target p.
ALG2_EFFECTIVE_CLASS: Dict[str, str] = {
    STABLE_HIGH: HIGH,
    STABLE_LOW: LOW,
    BUFFER_P_HIGH: HIGH,
    BUFFER_P_LOW: LOW,
}

# Spec 8.6 table, copied literally: (current state, evidence) -> next state.
# "KEEP / zero-service window" is one column; S0 therefore maps exactly like KEEP.
ALG2_TRANSITIONS: Dict[Tuple[str, str], str] = {
    (STABLE_HIGH, "UP"): STABLE_HIGH,   (STABLE_HIGH, "DOWN"): BUFFER_P_LOW,
    (STABLE_HIGH, "KEEP"): STABLE_HIGH, (STABLE_HIGH, "S0"): STABLE_HIGH,
    (STABLE_LOW, "UP"): BUFFER_P_HIGH,  (STABLE_LOW, "DOWN"): STABLE_LOW,
    (STABLE_LOW, "KEEP"): STABLE_LOW,   (STABLE_LOW, "S0"): STABLE_LOW,
    (BUFFER_P_HIGH, "UP"): STABLE_HIGH, (BUFFER_P_HIGH, "DOWN"): STABLE_LOW,
    (BUFFER_P_HIGH, "KEEP"): BUFFER_P_HIGH, (BUFFER_P_HIGH, "S0"): BUFFER_P_HIGH,
    (BUFFER_P_LOW, "UP"): STABLE_HIGH,  (BUFFER_P_LOW, "DOWN"): STABLE_LOW,
    (BUFFER_P_LOW, "KEEP"): BUFFER_P_LOW, (BUFFER_P_LOW, "S0"): BUFFER_P_LOW,
}  # fmt: skip

assert set(ALG2_TRANSITIONS) == {(s, e) for s in ALG2_STATES for e in EVIDENCES}


class FaiAlg2SwitchModel(FaiMainSwitchModel):
    """Same switch/FIFO/hold/FCFS/visit/window model; Algorithm-2 state interpretation only.

    Reset (spec 5): every source stable High with no pending Buffer, visit (High, 0).
    """

    INTERPRETATION = "alg2"
    TRANSITIONS = ALG2_TRANSITIONS
    EFFECTIVE = ALG2_EFFECTIVE_CLASS
    RESET_STATE = STABLE_HIGH
