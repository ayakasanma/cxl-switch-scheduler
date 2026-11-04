"""Pure-pytest tests of the spec 4 input (producer) hold checker (sim/common/input_hold.py).

They prove the checker the cocotb harness runs on every cycle accepts legal producer behaviour
(hold until push, release by reset, free after acceptance) and rejects the C1 failure modes
(valid withdrawn, descriptor changed while blocked).
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))  # sim/common

from input_hold import InputHoldChecker, InputHoldViolation  # noqa: E402

N = 4
D0, D1, D2 = 0x1_2345_6789, (1 << 104) | 0xABC, 0x7


def descs(**kw):
    out = [0] * N
    for k, v in kw.items():
        out[int(k[1:])] = v
    return out


def test_blocked_offer_held_until_push_passes():
    c = InputHoldChecker(N)
    c.step(0, 1, 0b0001, 0b1110, descs(s0=D0))  # refused
    assert c.obligations() == {0: D0}
    c.step(1, 1, 0b0001, 0b1110, descs(s0=D0))  # still refused, held
    c.step(2, 1, 0b0001, 0b1111, descs(s0=D0))  # pushed
    assert c.obligations() == {} and c.checked == 2
    c.step(3, 1, 0b0000, 0b1111, descs())  # free to drop after the push
    assert c.checked == 2


def test_withdrawn_valid_is_rejected():
    c = InputHoldChecker(N)
    c.step(0, 1, 0b1001, 0b0110, descs(s0=D0, s3=D1))
    with pytest.raises(InputHoldViolation, match="source 3 valid withdrawn"):
        c.step(1, 1, 0b0001, 0b0111, descs(s0=D0))


def test_changed_descriptor_is_rejected():
    c = InputHoldChecker(N)
    c.step(0, 1, 0b0100, 0b0000, descs(s2=D1))
    with pytest.raises(InputHoldViolation, match="source 2 descriptor changed"):
        c.step(1, 1, 0b0100, 0b0000, descs(s2=D1 ^ (1 << 104)))


def test_reset_releases_and_reset_cycles_create_no_obligation():
    c = InputHoldChecker(N)
    c.step(0, 1, 0b0001, 0b0000, descs(s0=D0))
    c.step(1, 0, 0b0000, 0b0000, descs())  # reset cycle: valid may drop
    c.step(2, 0, 0b0010, 0b0000, descs(s1=D2))  # offered during reset: in_ready 0 by reset
    assert c.obligations() == {}
    c.step(3, 1, 0b0000, 0b1111, descs())  # first non-reset cycle: nothing owed
    assert c.checked == 0


def test_accepted_offer_creates_no_obligation():
    c = InputHoldChecker(N)
    c.step(0, 1, 0b1111, 0b1111, descs(s0=D0, s1=D1, s2=D2, s3=D0))
    assert c.obligations() == {}
    c.step(1, 1, 0b0001, 0b1111, descs(s0=D1))  # new, different request: legal
    assert c.checked == 0
