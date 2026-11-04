"""Standalone tests of the combinational FCFS selector cxl_fcfs_sel (spec 6), N_SRC = 4, 8, 16.

Run through scripts/run_verify.sh M3 (it builds the design and exports CXL_PARAM_*).

Oracle (written from spec 6, not from the RTL): every eligible head carries an ABSOLUTE arrival
time; all eligible absolute times lie inside one window narrower than 2^31 (the environment
assumption: every outstanding request is younger than 2^31 cycles). The DUT sees the times reduced
mod 2^32. Expected: o_valid = any eligible; o_source = eligible source with the minimum absolute
time, lowest source ID on equal times. Ineligible sources carry arbitrary (garbage, often "older")
timestamps and must never win. No modular comparison is used by the oracle.
"""

from __future__ import annotations

import os
import random

import cocotb
from cocotb.triggers import ReadOnly, Timer

MOD = 1 << 32
HALF = 1 << 31


def param(name: str) -> int:
    key = f"CXL_PARAM_{name}"
    if key not in os.environ:
        raise RuntimeError(f"{key} is not set: run through scripts/run_verify.sh")
    return int(os.environ[key], 0)


def run_seed() -> int:
    return int(os.environ["COCOTB_RANDOM_SEED"])


def oracle(elig: int, abs_t, n: int):
    cands = [(abs_t[h], h) for h in range(n) if (elig >> h) & 1]
    if not cands:
        return 0, None
    return 1, min(cands)[1]


class SelTb:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.n = param("N_SRC")
        self.ts_w = param("TS_W")
        self.vectors = 0
        self.straddles = 0  # eligible window straddles the 2^32 boundary
        self.wrap_discriminating = 0  # winner's stored value is numerically above another eligible one
        self.ties = 0
        self.garbage_older = 0  # an ineligible source stored a value an unsigned compare would prefer
        assert self.n in (4, 8, 16) and self.ts_w == 32

    def check_ports(self) -> None:
        d = self.dut
        assert len(d.i_eligible) == self.n and len(d.i_head_ts) == 32 * self.n
        assert len(d.o_valid) == 1 and len(d.o_source) == (self.n - 1).bit_length()

    async def apply(self, elig: int, abs_t, garbage=None, what: str = ""):
        """Drive one vector; absolute times of ineligible sources are replaced by ``garbage``."""
        n = self.n
        stored = []
        for h in range(n):
            if (elig >> h) & 1:
                stored.append(abs_t[h] % MOD)
            else:
                stored.append((garbage[h] if garbage is not None else abs_t[h]) % MOD)
        vec = 0
        for h, t in enumerate(stored):
            vec |= t << (32 * h)
        await Timer(1, unit="ns")
        self.dut.i_eligible.value = elig
        self.dut.i_head_ts.value = vec
        await Timer(1, unit="ns")
        await ReadOnly()
        got_v = int(self.dut.o_valid.value)
        got_s = int(self.dut.o_source.value)
        exp_v, exp_s = oracle(elig, abs_t, n)
        self.vectors += 1
        assert got_v == exp_v, f"{what}: o_valid={got_v}, expected {exp_v} (eligible {elig:#x})"
        if exp_v:
            el = [h for h in range(n) if (elig >> h) & 1]
            assert got_s == exp_s, (
                f"{what}: o_source={got_s}, expected {exp_s}; eligible {el}; "
                f"absolute {[abs_t[h] for h in el]}; stored {[hex(stored[h]) for h in el]}"
            )
            assert max(abs_t[h] for h in el) - min(abs_t[h] for h in el) < HALF, "vector outside the assumption"
            lo = min(abs_t[h] for h in el)
            self.straddles += int(lo % MOD + (max(abs_t[h] for h in el) - lo) >= MOD)
            self.wrap_discriminating += int(any(stored[h] < stored[exp_s] for h in el))
            self.ties += int(sum(1 for h in el if abs_t[h] == abs_t[exp_s]) > 1)
            self.garbage_older += int(any(stored[h] < stored[exp_s] for h in range(n) if not (elig >> h) & 1))
        return got_v, got_s


def rand_window(rng: random.Random, n: int, base: int, span: int):
    """Absolute times in [base, base+span], span < 2^31."""
    assert 0 <= span < HALF
    return [base + rng.randint(0, span) for _ in range(n)]


SPECIAL_BASES = [0, 1, HALF - 1, HALF, MOD - HALF, MOD - 1, MOD - 2, MOD - 1000, MOD - (HALF - 1)]


async def new_tb(dut) -> SelTb:
    tb = SelTb(dut)
    dut._log.info("run seed=%d N_SRC=%d TS_W=%d", run_seed(), tb.n, tb.ts_w)
    tb.check_ports()
    return tb


# Covers: SPEC §6 (no eligible head -> no candidate), §3 (widths)
@cocotb.test()
async def test_01_none_eligible(dut):
    tb = await new_tb(dut)
    rng = random.Random(f"{run_seed()}:sel01:{tb.n}")
    for _ in range(200):
        await tb.apply(0, [rng.getrandbits(32) for _ in range(tb.n)], what="none eligible")
    for t in (0, MOD - 1, HALF):
        await tb.apply(0, [t] * tb.n, what="none eligible const")
    assert tb.vectors == 203


# Covers: SPEC §6 (single eligible source wins whatever the other timestamps are)
@cocotb.test()
async def test_02_single_eligible(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel02:{n}")
    for s in range(n):
        for _ in range(40):
            t = rng.getrandbits(33)
            garbage = [rng.getrandbits(32) for _ in range(n)]
            garbage[(s + 1) % n] = (t - 5) % MOD  # an ineligible neighbour looks older
            await tb.apply(1 << s, [t] * n, garbage, what=f"single {s}")
        for t in SPECIAL_BASES:
            await tb.apply(1 << s, [t] * n, [(t - 1) % MOD] * n, what=f"single {s} t={t:#x}")
    assert tb.garbage_older > 0


# Covers: SPEC §6 (equal timestamps -> ascending source ID, incl. all eligible / subsets)
@cocotb.test()
async def test_03_ties_lowest_id(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel03:{n}")
    full = (1 << n) - 1
    for t in SPECIAL_BASES:
        await tb.apply(full, [t] * n, what=f"all equal t={t:#x}")
    for _ in range(600):
        elig = rng.randrange(1, full + 1)
        t = rng.getrandbits(33)
        abs_t = [t] * n
        # some eligible sources younger by a random amount, the rest tie at t
        for h in range(n):
            if rng.random() < 0.3:
                abs_t[h] = t + rng.randint(1, HALF - 1)
        await tb.apply(elig, abs_t, [rng.getrandbits(32) for _ in range(n)], what="tie subset")
    assert tb.ties > 100


# Covers: SPEC §6 (ineligible sources holding the oldest/garbage timestamps never win)
@cocotb.test()
async def test_04_ineligible_never_wins(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel04:{n}")
    full = (1 << n) - 1
    for _ in range(800):
        elig = rng.randrange(1, full)  # never all-eligible: at least one ineligible source
        base = rng.getrandbits(33)
        abs_t = rand_window(rng, n, base, rng.choice([0, 5, 1 << 20, HALF - 1]))
        oldest_el = min(abs_t[h] for h in range(n) if (elig >> h) & 1)
        garbage = []
        for h in range(n):
            r = rng.random()
            if r < 0.4:
                garbage.append((oldest_el - rng.randint(1, HALF - 1)) % MOD)  # older than every eligible
            elif r < 0.7:
                garbage.append(oldest_el % MOD)  # equal to the oldest eligible
            else:
                garbage.append(rng.getrandbits(32))
        await tb.apply(elig, abs_t, garbage, what="ineligible oldest")
    assert tb.garbage_older > 200


# Covers: SPEC §6 (random masks, absolute times inside a < 2^31 window, windows straddling the
#         2^32 wrap, gaps up to 2^31-1; reduced mod 2^32 for the DUT)
@cocotb.test()
async def test_05_random_windows(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel05:{n}")
    full = (1 << n) - 1
    for i in range(4000):
        elig = rng.randrange(0, full + 1)
        span = rng.choice([0, 1, 16, 1 << 10, 1 << 24, 1 << 30, HALF - 2, HALF - 1])
        if i % 3 == 0:  # centre the window on a 2^32 boundary
            base = MOD * rng.randint(1, 3) - rng.randint(span // 4, (3 * span) // 4)
        else:
            base = rng.getrandbits(34)
        abs_t = rand_window(rng, n, base, span)
        await tb.apply(elig, abs_t, [rng.getrandbits(32) for _ in range(n)], what=f"random #{i}")
    assert tb.straddles > 200 and tb.wrap_discriminating > 200, (tb.straddles, tb.wrap_discriminating)


# Covers: SPEC §6 (every ordered source pair: older / equal / younger at gaps 1 and 2^31-1, at bases
#         across the wrap; others ineligible with garbage)
@cocotb.test()
async def test_06_all_pairs_wrap_and_max_gap(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel06:{n}")
    bases = [0, HALF, MOD - 1, MOD - (1 << 30)]
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            for base in bases:
                for delta in (-(HALF - 1), -1, 0, 1, HALF - 1):
                    abs_t = [0] * n
                    abs_t[a] = base + (HALF - 1)  # keep both inside [base, base + 2^32)
                    abs_t[b] = abs_t[a] + delta
                    garbage = [rng.getrandbits(32) for _ in range(n)]
                    await tb.apply((1 << a) | (1 << b), abs_t, garbage, what=f"pair a={a} b={b} d={delta}")
    assert tb.vectors == n * (n - 1) * len(bases) * 5
    assert tb.wrap_discriminating > 0 and tb.straddles > 0


# Covers: SPEC §6 (three-source chains across the wrap: modular order is consistent/transitive
#         inside the half-range window)
@cocotb.test()
async def test_07_chains_across_wrap(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:sel07:{n}")
    for _ in range(1500):
        k = rng.randint(2, n)
        srcs = rng.sample(range(n), k)
        base = MOD - rng.randint(1, HALF - 1)
        gaps = sorted(rng.randint(0, HALF - 1) for _ in range(k))
        abs_t = [rng.getrandbits(32) for _ in range(n)]
        elig = 0
        for s, g in zip(srcs, gaps):
            abs_t[s] = base + g
            elig |= 1 << s
        await tb.apply(elig, abs_t, abs_t, what=f"chain {srcs}")
    assert tb.straddles > 400 and tb.wrap_discriminating > 400, (tb.straddles, tb.wrap_discriminating)
