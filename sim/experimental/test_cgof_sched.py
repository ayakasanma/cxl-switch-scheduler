"""Cycle-exact cocotb checks of the EXPERIMENTAL CGOF (Credit-Gated Oldest-First) scheduler.

DUT: rtl/experimental/cgof_unit_top.sv (common FIFOs + unchanged cxl_out_hold + cxl_cgof_sched).
Oracle: the independent model refc/cxl_model/experimental.py
ExperimentalSwitchModel(policy="CGOF(<HIGH_WEIGHT>:1)", high_weight=HIGH_WEIGHT,
ordering="oldest-first" (ELIGIBLE_RR=0) or "eligible-round-robin" (ELIGIBLE_RR=1)).

Configuration identity = High:Low allocation x eligible-source ordering:
  CGOF(2:1) / CGOF(1:1)                       HIGH_WEIGHT = 2 / 1
  oldest-first / credit-gated eligible RR     ELIGIBLE_RR = 0 / 1

Parameters arrive as CXL_PARAM_<NAME> (scripts/run_revision_cgof.py) and are also passed to
Verilator with -G: N_SRC, DEPTH, FAI_W, HIGH_WEIGHT, ELIGIBLE_RR. Every cycle of every test goes
through ``Harness.cycle`` which

1. compares all output pins (o_in_ready, o_out_valid and, when valid, o_out_source plus all 105
   descriptor bits), the held flag and the stored head timestamps with the model view;
2. decodes the offered grant context {class snapshot, refill} into the credit snapshot it commits
   (refill ? weights(snapshot) : credit_q) and compares it with the model's Choice.credits, and the
   offered source with Choice.source;
3. compares every policy register (cls_q, idx_q, b_q, s_q, credit_q and, for eligible RR,
   rr_ptr_q) with the model state, pre-edge at the falling edge and again post-edge 1 ns after the
   closing rising edge;
4. applies model-free rules derived directly from the CGOF definition and the common framework:
   pin scoreboard (per-source FIFO order, exactly-once delivery, 105-bit integrity), readiness =
   occupancy < DEPTH (full before pop), no empty bypass, no avoidable bubble (any stored request
   => out_valid), reset suppression, held-grant stability (source, descriptor, context) until it
   fires; for every newly offered grant: refill bit == no active source with credit; offered
   source == oldest (absolute arrival edge, then lowest ID) of the pool (oldest-first), or the
   first pool source in circular order from an independently tracked pointer (eligible RR), where
   pool = active sources with credit, or all active sources on a refill; 2:1 class snapshot ==
   current effective classes; per edge: credit_q unchanged unless a fire, on a fire credit_q =
   snapshot - one-hot(grant), reset clears; RR pointer 0 after reset, (grant + 1) mod N after a
   fire, otherwise unchanged; window index advances by one per non-reset edge and wraps at W-1.

Directed tests add hand-derived literal expectations for each ordering (refill from empty,
exhaustion, inactive sources not blocking, overwrite, re-entry, held refill across a push of a
credited source, 2:1 / 1:1 shares at fixed classes, class change inside a round with a refill grant
held across the closing edge, long stalls across windows, timestamp wrap with ascending and
reversed rotation, RR pointer advance/hold/skip/wrap, W64/W256 threshold boundaries with the
closing fire included, W5M 32-bit threshold boundaries by state injection).

RTL-facing encodings (only facts the test uses):
  cls_q    : 2 bits per source, H=0, L=1, B_H=2, B_L=3 (bit0 = effective Low)
  credit_q : clog2(HIGH_WEIGHT+1) bits per source
  b_q, s_q : clog2(W+1) bits; idx_q : clog2(W) bits; rr_ptr_q : clog2(N) bits (ELIGIBLE_RR=1)
  grant ctx: bit0 refill; bits [N:1] effective-High class snapshot (HIGH_WEIGHT=2 only)
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import deque
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "refc"))
sys.path.insert(0, str(ROOT / "sim" / "common"))
from hier_util import hierarchy_paths  # noqa: E402
from cxl_model.experimental import ExperimentalSwitchModel  # noqa: E402
from cxl_model.fai_main_model import EFFECTIVE_CLASS, HIGH  # noqa: E402

DESC_W = 105
DESC_MASK = (1 << DESC_W) - 1
TS_W = 32
CLS_CODE = {"H": 0, "L": 1, "B_H": 2, "B_L": 3}
CODE_CLS = {v: k for k, v in CLS_CODE.items()}
RANDOM_CYCLES = int(os.environ.get("CXL_RANDOM_CYCLES", "20000"))
RESULT_FILE = "cgof_checks.json"


def param(name, default):
    return int(os.environ.get(f"CXL_PARAM_{name}", default))


P = dict(N_SRC=param("N_SRC", 4), DEPTH=param("DEPTH", 16), FAI_W=param("FAI_W", 5000000),
         HIGH_WEIGHT=param("HIGH_WEIGHT", 2), ELIGIBLE_RR=param("ELIGIBLE_RR", 0))
N, W, HW = P["N_SRC"], P["FAI_W"], P["HIGH_WEIGHT"]
RR = {0: False, 1: True}[P["ELIGIBLE_RR"]]
POLICY_NAME = {2: "CGOF(2:1)", 1: "CGOF(1:1)"}[HW]
ORDERING = "eligible-round-robin" if RR else "oldest-first"
IDENTITY = f"{POLICY_NAME}/{ORDERING}"
WEIGHTED = HW > 1
CRED_W = HW.bit_length()
BS_W = W.bit_length()
IDX_W = (W - 1).bit_length()
SRC_W = (N - 1).bit_length()
CTX_W = N + 1 if WEIGHTED else 1
SMALL_W = W <= 256
CONFIG_TAG = "n{N_SRC}_d{DEPTH}_w{FAI_W}_hw{HIGH_WEIGHT}_rr{ELIGIBLE_RR}".format(**P)


def field(value, i, width):
    return (value >> (i * width)) & ((1 << width) - 1)


def pack(values, width):
    return sum(v << (i * width) for i, v in enumerate(values))


def weight(high):
    return HW if high else 1


def class_high(cls_codes):
    """Effective-High bit per source from 2-bit RTL codes (bit0 = effective Low)."""
    return [int(not (c & 1)) for c in cls_codes]


def decode_ctx(ctx):
    """(refill, effective-High snapshot list or None) of a grant context."""
    refill = ctx & 1
    hi = [(ctx >> (1 + h)) & 1 for h in range(N)] if WEIGHTED else None
    return refill, hi


def snapshot(refill, hi, credits):
    """Credit vector a grant commits: the refill vector of its class snapshot, or credit_q."""
    if refill:
        return [weight(hi[h]) if WEIGHTED else 1 for h in range(N)]
    return list(credits)


def new_model(depth, policy=POLICY_NAME, high_weight=HW):
    return ExperimentalSwitchModel(N, policy, window=W, depth=depth, high_weight=high_weight,
                                   ordering=ORDERING)


class Harness:
    def __init__(self, dut, label, seed):
        self.dut, self.label = dut, label
        self.n, self.depth = N, P["DEPTH"]
        self.rng = random.Random(seed)
        self.model = new_model(self.depth)
        self.u = dut.u_cgof_sched
        self.sb = [deque() for _ in range(N)]  # pin scoreboard: (desc, absolute arrival edge)
        self.prev = None  # (stalled, source, desc, ctx) of the previous non-reset cycle
        self.edges = 0  # non-reset edges since the last reset edge
        self.abs_edge = 0  # every edge since start (arrival order key, immune to counter wrap)
        self.cycles = 0
        self.tag = 0
        self.rr_ptr = 0  # independent RR pointer: 0 after reset, (grant + 1) mod N after a fire
        self.left_with_credit = set()  # sources that went idle with credit left in this round
        self.cov = dict(cycles=0, resets=0, fires=0, stalls=0, held_cycles=0, full_refusals=0,
                        full_refused_while_popping=0, push_pop_same_source=0, max_occupancy=0,
                        policy_state_checks=0, offers_checked=0)  # fmt: skip
        self.cgof = dict(refill_offers=0, refill_fires=0, overwrite_fires=0, inactive_credit_refills=0,
                         reentry_fires=0, held_refill_cycles=0, held_refill_push_credited=0,
                         held_across_close=0, held_refill_class_change=0, windows=0, class_changes=0,
                         credit_blocked_older=0, offered_not_oldest=0, rr_wraps=0,
                         rr_skip_inactive=0, rr_skip_no_credit=0)  # fmt: skip

    def desc(self, h):
        self.tag += 1
        r = self.rng
        return ((self.tag & 0xFFFFFFFF) << 73) | (r.getrandbits(32) << 41) | (r.getrandbits(1) << 40) \
            | (r.getrandbits(8) << 32) | ((h * 0x01000193 + r.getrandbits(32)) & 0xFFFFFFFF)

    async def start(self):
        dut = self.dut
        dut.rst_n.value = 0
        dut.i_in_valid.value = 0
        dut.i_in_desc.value = 0
        dut.i_out_ready.value = 0
        cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
        await RisingEdge(dut.clk)
        self.model.commit(rst_n=False)
        self.abs_edge += 1
        await Timer(1, unit="ns")
        await self.reset(2)

    async def reset(self, k=1, busy=True):
        """Reset edges with every request input asserted (suppression is checked)."""
        for _ in range(k):
            push = {h: self.desc(h) for h in range(N)} if busy else {}
            await self.cycle(push, ready=1, rst_n=0)

    # ----- register access ----------------------------------------------------------------------

    def regs(self):
        u = self.u
        cls, b, cr = int(u.cls_q.value), int(u.b_q.value), int(u.credit_q.value)
        return dict(cls=[field(cls, h, 2) for h in range(N)], idx=int(u.idx_q.value),
                    b=[field(b, h, BS_W) for h in range(N)], s=int(u.s_q.value),
                    credit=[field(cr, h, CRED_W) for h in range(N)])  # fmt: skip

    def rr_value(self):
        """RTL eligible-RR pointer, None for oldest-first."""
        return int(self.u.gen_order_rr.rr_ptr_q.value) if RR else None

    def inject(self, cls=None, idx=None, b=None, s=None, credits=None):
        """Write policy state into the RTL registers AND the model (same values), at the settled
        point after an edge. Verified by the next pre-edge register comparison."""
        u, m = self.u, self.model
        if cls is not None:
            u.cls_q.value = pack([CLS_CODE[c] for c in cls], 2)
            m.cls = list(cls)
        if idx is not None:
            u.idx_q.value = idx
            m.win_pos = idx
        if b is not None:
            u.b_q.value = pack(b, BS_W)
            m.b = list(b)
        if s is not None:
            u.s_q.value = s
            m.s = s
        if credits is not None:
            u.credit_q.value = pack(credits, CRED_W)
            m.credits = list(credits)

    # ----- one cycle --------------------------------------------------------------------------

    async def cycle(self, push=None, ready=0, rst_n=1, deposit=None):
        """One clock cycle, entered and left at the settled point 1 ns after a rising edge. The
        returned sample ``o`` is the state BEFORE this cycle's closing edge; registers read by a
        test right after ``await tb.cycle(...)`` are the settled state AFTER it."""
        dut = self.dut
        push = push or {}
        valid = [h in push for h in range(N)]
        descs = [push.get(h, 0) for h in range(N)]
        dut.rst_n.value = rst_n
        dut.i_in_valid.value = sum(1 << h for h in push)
        dut.i_in_desc.value = sum(d << (DESC_W * h) for h, d in push.items())
        dut.i_out_ready.value = ready
        if deposit is not None:
            self.model.deposit_counter(deposit)
            dut.gen_arrival_ts.arrival_cnt_q.value = deposit
        await FallingEdge(dut.clk)
        await ReadOnly()
        o = self.sample(ready, rst_n)
        self.check(o, ready, rst_n)
        await RisingEdge(dut.clk)
        edge = self.model.commit(bool(ready), valid, descs, bool(rst_n))
        await Timer(1, unit="ns")  # nonblocking assignments of the closing edge have settled
        self.check_policy_state(f"[{self.label} cycle {self.cycles} post-edge]")
        self.after_edge(o, valid, descs, ready, rst_n, edge)
        return o

    def sample(self, ready, rst_n):
        dut = self.dut
        o = dict(in_ready=int(dut.o_in_ready.value), out_valid=int(dut.o_out_valid.value), ready=ready,
                 rst_n=rst_n, head_ts=int(dut.head_ts.value), grant_ctx=int(dut.grant_ctx.value),
                 held=int(dut.grant_held.value))  # fmt: skip
        o["out_source"] = int(dut.o_out_source.value) if o["out_valid"] else None
        o["out_desc"] = int(dut.o_out_desc.value) if o["out_valid"] else None
        o["fire"] = bool(o["out_valid"] and ready)
        o.update({f"r_{k}": v for k, v in self.regs().items()})
        o["r_ptr"] = self.rr_value()
        o["refill"], o["hi"] = decode_ctx(o["grant_ctx"])
        return o

    def oldest_of(self, sources):
        return min(sources, key=lambda h: (self.sb[h][0][1], h))

    def check(self, o, ready, rst_n):
        tag = f"[{self.label} cycle {self.cycles} edge {self.edges}]"
        m = self.model
        view = m.view(bool(ready), bool(rst_n))
        exp_ready = sum(int(b) << h for h, b in enumerate(view.in_ready))
        assert o["in_ready"] == exp_ready, f"{tag} o_in_ready {o['in_ready']:#x} != model {exp_ready:#x}"
        assert o["out_valid"] == int(view.out_valid), f"{tag} o_out_valid {o['out_valid']} != model"
        if o["out_valid"]:
            assert (o["out_source"], o["out_desc"]) == (view.out_source, view.out_desc), \
                f"{tag} grant {o['out_source']}/{o['out_desc']:#x} != model {view.out_source}/{view.out_desc}"
            assert o["held"] == int(view.held), f"{tag} grant_held {o['held']} != model {view.held}"
            choice = m.choice()
            assert choice is not None and choice.source == o["out_source"], f"{tag} model choice {choice}"
            snap = snapshot(o["refill"], o["hi"], o["r_credit"])
            assert tuple(snap) == tuple(choice.credits), \
                f"{tag} ctx refill={o['refill']} hi={o['hi']} -> credits {snap} != model {choice.credits}"
            self.cov["offers_checked"] += 1
        for h in range(N):
            if view.head_valid[h]:
                ts = field(o["head_ts"], h, TS_W)
                assert ts == view.head_ts[h], f"{tag} head_ts[{h}] {ts:#x} != model {view.head_ts[h]:#x}"
        self.check_policy_state(tag)
        if RR:
            assert o["r_ptr"] == self.rr_ptr, f"{tag} rr_ptr_q {o['r_ptr']} != independent {self.rr_ptr}"
        # ---- model-free pin and policy rules ----
        if not rst_n:
            assert o["in_ready"] == 0 and o["out_valid"] == 0, f"{tag} outputs not suppressed in reset"
            return
        active = [h for h in range(N) if self.sb[h]]
        for h in range(N):
            occ = len(self.sb[h])
            assert ((o["in_ready"] >> h) & 1) == int(occ < self.depth), \
                f"{tag} source {h} ready with scoreboard occupancy {occ} (DEPTH {self.depth})"
        assert o["out_valid"] == int(bool(active)), f"{tag} out_valid {o['out_valid']} with stored {active}"
        if o["out_valid"]:
            q = self.sb[o["out_source"]]
            assert q, f"{tag} output from source {o['out_source']} with nothing pushed (bypass?)"
            assert q[0][0] == o["out_desc"], f"{tag} out_desc is not the oldest descriptor of its source"
        if self.prev is not None and self.prev[0]:
            _, src, d, ctx = self.prev
            assert o["out_valid"] and (o["out_source"], o["out_desc"], o["grant_ctx"]) == (src, d, ctx), \
                f"{tag} stalled grant {src} was not held unchanged"
            assert o["held"], f"{tag} grant_held low on a held cycle"
            self.cov["held_cycles"] += 1
            if o["refill"]:
                self.cgof["held_refill_cycles"] += 1
                if any(o["r_credit"][h] > 0 for h in active):
                    self.cgof["held_refill_push_credited"] += 1
        else:
            assert not o["held"], f"{tag} grant_held without a previous stall"
        if o["out_valid"] and not o["held"]:
            credit = o["r_credit"]
            elig = [h for h in active if credit[h] > 0]
            assert o["refill"] == int(not elig), f"{tag} refill bit {o['refill']} with credited active {elig}"
            pool = elig or active
            if RR:
                ptr = self.rr_ptr
                exp = min(pool, key=lambda h: (h - ptr) % N)
                if ptr not in active:
                    self.cgof["rr_skip_inactive"] += 1
                elif ptr not in pool:
                    self.cgof["rr_skip_no_credit"] += 1
            else:
                exp = self.oldest_of(pool)
            assert o["out_source"] == exp, \
                f"{tag} offered {o['out_source']}, {ORDERING} choice is {exp} of {pool} (ptr {o['r_ptr']})"
            if WEIGHTED:
                assert o["hi"] == class_high(o["r_cls"]), f"{tag} class snapshot {o['hi']} != {o['r_cls']}"
            if o["refill"]:
                self.cgof["refill_offers"] += 1
                if any(credit[h] > 0 for h in range(N) if h not in active):
                    self.cgof["inactive_credit_refills"] += 1
            oldest = self.oldest_of(active)
            self.cgof["credit_blocked_older"] += int(oldest != self.oldest_of(pool))
            self.cgof["offered_not_oldest"] += int(oldest != exp)

    def check_policy_state(self, tag):
        m = self.model
        if not m.state_known:
            return
        r = self.regs()
        assert r["cls"] == [CLS_CODE[c] for c in m.classes()], f"{tag} cls_q {r['cls']} != {m.classes()}"
        pos, b, s = m.window_state()
        assert r["idx"] == pos, f"{tag} idx_q {r['idx']} != {pos}"
        assert r["b"] == list(b), f"{tag} b_q {r['b']} != {list(b)}"
        assert r["s"] == s, f"{tag} s_q {r['s']} != {s}"
        assert r["credit"] == list(m.credits), f"{tag} credit_q {r['credit']} != {m.credits}"
        assert all(0 <= c <= HW for c in r["credit"]), f"{tag} credit out of range {r['credit']}"
        if RR:
            assert self.rr_value() == m.poll, f"{tag} rr_ptr_q {self.rr_value()} != model {m.poll}"
        self.cov["policy_state_checks"] += 1

    def after_edge(self, o, valid, descs, ready, rst_n, edge):
        tag = f"[{self.label} cycle {self.cycles} after-edge]"
        self.cycles += 1
        self.cov["cycles"] += 1
        self.abs_edge += 1
        post = self.regs()
        if RR:
            if not rst_n:
                self.rr_ptr = 0
            elif o["fire"]:
                self.rr_ptr = (o["out_source"] + 1) % N
                self.cgof["rr_wraps"] += int(o["out_source"] == N - 1)
            assert self.rr_value() == self.rr_ptr, f"{tag} rr_ptr_q {self.rr_value()} != independent {self.rr_ptr}"
        if not rst_n:
            assert post == dict(cls=[0] * N, idx=0, b=[0] * N, s=0, credit=[0] * N), f"{tag} reset state {post}"
            self.sb = [deque() for _ in range(N)]
            self.prev = None
            self.edges = 0
            self.left_with_credit = set()
            self.cov["resets"] += 1
            return
        self.edges += 1
        # credit rule: only a fire changes credit_q; it commits the grant's snapshot minus one
        src = o["out_source"] if o["fire"] else None
        if src is not None:
            base = snapshot(o["refill"], o["hi"], o["r_credit"])
            assert base[src] >= 1, f"{tag} fired source {src} without credit in its snapshot {base}"
            base[src] -= 1
            assert post["credit"] == base, f"{tag} credit_q {post['credit']} != snapshot-1 {base}"
            self.cgof["refill_fires"] += o["refill"]
            self.cgof["overwrite_fires"] += int(bool(o["refill"] and any(o["r_credit"])))
            if o["refill"]:
                self.left_with_credit = set()
            elif src in self.left_with_credit:
                self.cgof["reentry_fires"] += 1
                self.left_with_credit.discard(src)
        else:
            assert post["credit"] == o["r_credit"], f"{tag} credit_q changed without a fire"
        closing = o["r_idx"] == W - 1
        assert post["idx"] == (0 if closing else o["r_idx"] + 1), f"{tag} idx_q {o['r_idx']} -> {post['idx']}"
        assert (edge.closing is not None) == closing, f"{tag} model/RTL closing edge disagree"
        stalled = bool(o["out_valid"] and not ready)
        if closing:
            self.cgof["windows"] += 1
            self.cgof["class_changes"] += int(post["cls"] != o["r_cls"])
            if stalled:
                self.cgof["held_across_close"] += 1
                if o["refill"] and WEIGHTED and o["hi"] != class_high(post["cls"]):
                    self.cgof["held_refill_class_change"] += 1
        # scoreboard
        if src is not None:
            d, _ = self.sb[src].popleft()
            assert d == o["out_desc"]
            self.cov["fires"] += 1
        for h in range(N):
            if valid[h]:
                if (o["in_ready"] >> h) & 1:
                    self.sb[h].append((descs[h], self.abs_edge))
                    self.cov["push_pop_same_source"] += int(h == src)
                else:
                    self.cov["full_refusals"] += 1
                    self.cov["full_refused_while_popping"] += int(h == src)
            self.cov["max_occupancy"] = max(self.cov["max_occupancy"], len(self.sb[h]))
            if not self.sb[h] and post["credit"][h] > 0:
                self.left_with_credit.add(h)
        self.cov["stalls"] += int(stalled)
        self.prev = (stalled, o["out_source"], o["out_desc"], o["grant_ctx"]) if stalled else None

    # ----- helpers ----------------------------------------------------------------------------

    def summary(self, name, extra=None):
        out = dict(config=CONFIG_TAG, params=P, identity=IDENTITY, policy=POLICY_NAME, ordering=ORDERING,
                   test=name, coverage=self.cov, cgof=self.cgof,
                   oracle="ExperimentalSwitchModel")  # fmt: skip
        out.update(extra or {})
        path = Path(RESULT_FILE)
        data = (json.loads(path.read_text()) if path.is_file()
                else dict(config=CONFIG_TAG, identity=IDENTITY, params=P, tests={}))
        data["tests"][name] = out
        path.write_text(json.dumps(data, indent=2) + "\n")
        self.dut._log.info("%s %s summary %s", CONFIG_TAG, name, json.dumps(out))
        return out


async def new_harness(dut, name):
    seed = (cocotb.RANDOM_SEED * 1_000_003 + sum(map(ord, name))) & 0xFFFFFFFF
    dut._log.info("test %s config %s identity %s cocotb seed %d harness seed %d", name, CONFIG_TAG,
                  IDENTITY, cocotb.RANDOM_SEED, seed)
    tb = Harness(dut, name, seed)
    await tb.start()
    return tb


async def run_cycles(tb, k, push_fn=None, ready_fn=None):
    for i in range(k):
        await tb.cycle(push_fn(i) if push_fn else {}, ready_fn(i) if ready_fn else 0)


def full(*pairs):
    """Credit vector of length N: listed (source, value) pairs, every other source HW."""
    v = [HW] * N
    for h, c in pairs:
        v[h] = c
    return v


def rr_rotation(order):
    """Hand rule for the drain of a pre-filled backlog with equal effective classes under eligible
    RR: the first pushed source (alone at the first offer) fires first, then circular ascending
    order over the sources that still hold descriptors (a credited source always comes next)."""
    queues = [deque(d for s, d in order if s == h) for h in range(N)]
    seq, h = [], order[0][0]
    while any(queues):
        while not queues[h]:
            h = (h + 1) % N
        seq.append((h, queues[h].popleft()))
        h = (h + 1) % N
    return seq


# ==================================================================================================
# Tests for every configuration
# ==================================================================================================


@cocotb.test()
async def test_structure_and_reset(dut):
    """Port widths, real policy-state widths, storage, context width, ordering structure, model
    configuration identity, reset values."""
    tb = await new_harness(dut, "structure")
    assert len(dut.i_in_valid) == N and len(dut.o_in_ready) == N
    assert len(dut.i_in_desc) == N * DESC_W and len(dut.o_out_desc) == DESC_W
    assert len(dut.o_out_source) == max(1, SRC_W)
    u = tb.u
    widths = dict(cls_q=len(u.cls_q.value), idx_q=len(u.idx_q.value), b_q=len(u.b_q.value),
                  s_q=len(u.s_q.value), credit_q=len(u.credit_q.value), grant_ctx=len(dut.grant_ctx.value),
                  held_ctx_q=len(dut.u_out_hold.held_ctx_q.value))  # fmt: skip
    expect = dict(cls_q=2 * N, idx_q=IDX_W, b_q=N * BS_W, s_q=BS_W, credit_q=N * CRED_W, grant_ctx=CTX_W,
                  held_ctx_q=CTX_W)  # fmt: skip
    if RR:
        widths["rr_ptr_q"] = len(u.gen_order_rr.rr_ptr_q.value)
        expect["rr_ptr_q"] = SRC_W
    assert widths == expect, f"state widths {widths} != {expect}"
    names = [p for p, _kind in hierarchy_paths(dut)]
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == N, "descriptor storage per source"
    assert len([p for p in names if "ts_mem_q" in p]) == N, "timestamp storage per source (both orderings)"
    assert [p for p in names if "arrival_cnt_q" in p] == [f"{dut._path}.gen_arrival_ts.arrival_cnt_q"]
    rr_paths = [p for p in names if "rr_ptr_q" in p]
    assert rr_paths == ([f"{dut._path}.u_cgof_sched.gen_order_rr.rr_ptr_q"] if RR else []), rr_paths
    for h in range(N):
        mem = dut.gen_fifo[h].u_fifo.gen_ts.ts_mem_q
        assert len(mem) == P["DEPTH"] and len(mem[0]) == TS_W
    # configuration identity: configured name == bare CGOF with explicit weight; mismatch rejected
    bare = new_model(P["DEPTH"], policy="CGOF")
    ident = lambda m: (m.policy, m.high_weight, m.ordering)  # noqa: E731
    assert ident(tb.model) == ident(bare) == ("CGOF", HW, ORDERING), (ident(tb.model), ident(bare))
    try:
        new_model(P["DEPTH"], high_weight=3 - HW)
    except ValueError:
        pass
    else:
        raise AssertionError(f"{POLICY_NAME} accepted high_weight={3 - HW}")
    assert tb.regs() == dict(cls=[0] * N, idx=0, b=[0] * N, s=0, credit=[0] * N), "state after reset edges"
    o = await tb.cycle()
    assert o["in_ready"] == (1 << N) - 1 and o["out_valid"] == 0
    assert o["r_credit"] == [0] * N and o["r_cls"] == [0] * N and o["r_idx"] == 0, "reset: credits 0, all H"
    if RR:
        assert o["r_ptr"] == 0, "reset: RR pointer 0"
    tb.summary("structure", dict(state_bits=expect))


@cocotb.test()
async def test_full_before_pop_no_bypass(dut):
    """Source 0 to DEPTH: ready drops exactly at DEPTH, a full FIFO refuses a push on the edge that
    pops it, a push into an empty FIFO is not output in its own cycle, 105-bit integrity."""
    tb = await new_harness(dut, "full_no_bypass")
    d = P["DEPTH"]
    o = await tb.cycle({0: tb.desc(0)}, ready=1)
    assert o["out_valid"] == 0, "push into an empty FIFO must not bypass to the output"
    for i in range(d - 1):
        o = await tb.cycle({0: tb.desc(0)}, ready=0)
        assert o["in_ready"] & 1, f"source 0 not ready at occupancy {i + 1}"
    o = await tb.cycle({0: tb.desc(0)}, ready=1)
    assert not (o["in_ready"] & 1) and o["fire"], "full FIFO must refuse the push on the popping edge"
    o = await tb.cycle({0: tb.desc(0)}, ready=0)
    assert o["in_ready"] & 1, "after the pop the FIFO has room again"
    hi = N - 1
    await tb.reset()
    pattern = (DESC_MASK, 0, 1 << 104, 0x15555555555555555555555555 & DESC_MASK)
    for dsc in pattern:
        await tb.cycle({hi: dsc}, ready=0)
    got = []
    for _ in range(4):
        o = await tb.cycle({}, ready=1)
        got.append(o["out_desc"])
    assert got == list(pattern)
    assert tb.cov["full_refused_while_popping"] >= 1
    tb.summary("full_no_bypass")


@cocotb.test()
async def test_refill_exhaust_inactive_overwrite(dut):
    """Hand-derived (all classes H after reset, refill vector = HW for every source):
    reset credits 0 -> the first offer is a refill (same selection, no bubble), latched by a stall
    and committed at its fire; exhausted credit blocks an older head; a refill happens as soon as no
    ACTIVE source has credit although inactive sources still hold credit, and it overwrites them.
      pushes: src0 @e1, src0 @e2, src0 @e3, src1 @e4 (ready 0, src0 refill offer held from cycle 2)
      2:1 oldest-first: 0 (refill) 0 1 0 (refill)
      2:1 eligible RR : 0 (refill) 1 0 0 (refill)    pointer after each fire 1 2 1 1
      1:1 both        : 0 (refill) 1 0 (refill) 0 (refill); RR pointer 1 2 1 1"""
    tb = await new_harness(dut, "refill_basics")
    for h in (0, 0, 0, 1):
        await tb.cycle({h: tb.desc(h)}, ready=0)
    seq, ptrs = [], []
    for _ in range(4):
        o = await tb.cycle({}, ready=1)
        assert o["fire"]
        seq.append((o["out_source"], o["refill"], tb.regs()["credit"]))
        ptrs.append(tb.rr_value())
    if WEIGHTED and RR:
        expect = [(0, 1, full((0, 1))), (1, 0, full((0, 1), (1, 1))), (0, 0, full((0, 0), (1, 1))),
                  (0, 1, full((0, 1)))]  # fmt: skip
    elif WEIGHTED:
        expect = [(0, 1, full((0, 1))), (0, 0, full((0, 0))), (1, 0, full((0, 0), (1, 1))),
                  (0, 1, full((0, 1)))]  # fmt: skip
    else:
        expect = [(0, 1, full((0, 0))), (1, 0, full((0, 0), (1, 0))), (0, 1, full((0, 0))),
                  (0, 1, full((0, 0)))]  # fmt: skip
    assert seq == expect, f"{seq} != {expect}"
    if RR:
        assert ptrs == [1, 2, 1, 1], f"RR pointer {ptrs}"
    assert tb.cgof["overwrite_fires"] >= 1 and tb.cgof["inactive_credit_refills"] >= 1
    idle = tb.regs()["credit"]
    for _ in range(5):  # idle cycles never change credits (nor the RR pointer: checked per cycle)
        o = await tb.cycle({}, ready=1)
        assert o["out_valid"] == 0 and tb.regs()["credit"] == idle
    # all sources active with every credit exhausted: one refill re-arms all of them
    for h in range(N):
        await tb.cycle({h: tb.desc(h)}, ready=0)
    while any(tb.sb):
        await tb.cycle({}, ready=1)
    assert tb.cov["fires"] == 4 + N
    tb.summary("refill_basics", dict(sequence=seq, rr_pointer=ptrs))


@cocotb.test()
async def test_reentry_and_held_refill_across_push(dut):
    """Hand-derived. (a) src1 fires the refill, empties (inactive, credit HW-1 kept), re-enters
    during the round and gets exactly its remaining credit, no extra credit (oldest-first serves the
    older src0 first, eligible RR serves src1 first from pointer 1). (b) a refill offer on src0 is
    stalled and held; meanwhile a credited source (src2) arrives, so the live candidate would no
    longer be a refill; the held grant still commits the refill snapshot at its fire. (c) src N-1,
    idle at that refill, re-enters and fires on its round credit (no refill; RR pointer wraps)."""
    tb = await new_harness(dut, "reentry_held_refill")
    await tb.cycle({1: tb.desc(1)}, ready=0)  # e1
    for _ in range(3):  # e2..e4: src0 x3; the src1 refill offer is latched at e2
        await tb.cycle({0: tb.desc(0)}, ready=0)
    seq = []
    o = await tb.cycle({}, ready=1)  # held refill of src1 fires
    seq.append((o["out_source"], o["refill"], o["held"], tb.regs()["credit"]))
    o = await tb.cycle({1: tb.desc(1)}, ready=1)  # src0 fires; src1 re-enters at this edge
    seq.append((o["out_source"], o["refill"], o["held"], tb.regs()["credit"]))
    for _ in range(2):
        o = await tb.cycle({}, ready=1)
        seq.append((o["out_source"], o["refill"], o["held"], tb.regs()["credit"]))
    if WEIGHTED and RR:
        expect = [(1, 1, 1, full((1, 1))), (0, 0, 0, full((0, 1), (1, 1))),
                  (1, 0, 0, full((0, 1), (1, 0))), (0, 0, 0, full((0, 0), (1, 0)))]  # fmt: skip
    elif WEIGHTED:
        expect = [(1, 1, 1, full((1, 1))), (0, 0, 0, full((0, 1), (1, 1))),
                  (0, 0, 0, full((0, 0), (1, 1))), (1, 0, 0, full((0, 0), (1, 0)))]  # fmt: skip
    elif RR:
        expect = [(1, 1, 1, full((1, 0))), (0, 0, 0, full((0, 0), (1, 0))),
                  (1, 1, 0, full((1, 0))), (0, 0, 0, full((0, 0), (1, 0)))]  # fmt: skip
    else:
        expect = [(1, 1, 1, full((1, 0))), (0, 0, 0, full((0, 0), (1, 0))),
                  (0, 1, 0, full((0, 0))), (1, 0, 0, full((0, 0), (1, 0)))]  # fmt: skip
    assert seq == expect, f"(a) {seq} != {expect}"
    if WEIGHTED:
        assert tb.cgof["reentry_fires"] >= 1, "(a) src1 re-entry on its remaining credit"
    # (b) src0 (credit 0) is the only active source: its refill offer is latched by a stall
    o = await tb.cycle({}, ready=0)
    assert o["out_source"] == 0 and o["refill"] == 1 and not o["held"]
    o = await tb.cycle({2: tb.desc(2)}, ready=0)  # credited src2 arrives while the grant is held
    assert o["held"]
    o = await tb.cycle({}, ready=0)
    assert o["held"] and o["refill"] == 1 and tb.regs()["credit"][2] == HW
    assert tb.cgof["held_refill_push_credited"] >= 1, "the held refill must have seen a credited arrival"
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == 0 and tb.regs()["credit"] == full((0, HW - 1))
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == 2 and o["refill"] == 0
    assert tb.regs()["credit"] == full((0, HW - 1), (2, HW - 1))
    # (c) src N-1 was idle at the src0 refill fire, so it holds credit HW of this round; it arrives
    # and fires on that credit without a new refill (both weights; the 1:1 only re-entry case)
    assert not any(tb.sb) and N - 1 in tb.left_with_credit
    reentry0 = tb.cgof["reentry_fires"]
    await tb.cycle({N - 1: tb.desc(N - 1)}, ready=1)
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == N - 1 and o["refill"] == 0
    assert tb.regs()["credit"] == full((0, HW - 1), (2, HW - 1), (N - 1, HW - 1))
    assert tb.cgof["reentry_fires"] == reentry0 + 1
    if RR:
        assert tb.rr_value() == 0 and tb.cgof["rr_wraps"] >= 1, "RR pointer wraps after src N-1"
    tb.summary("reentry_held_refill", dict(sequence=seq))


@cocotb.test()
async def test_shares_fixed_classes(dut):
    """Fixed classes by state injection right after reset: src0 Low, src1 High (others High,
    idle). Both backlogged inside one window: every complete round (refill fire to refill fire)
    has exactly HW fires of src1 and 1 of src0 (2:1 / 1:1), with and without stalls; the per-round
    counts are independent of the ordering. A second phase with src0 and src1 both High gives 1:1
    for both weights."""
    tb = await new_harness(dut, "shares")
    limit = min(W - 8, 900)
    results = {}
    for phase, cls in (("low_high", ["L"] + ["H"] * (N - 1)), ("high_high", ["H"] * N)):
        await tb.reset()
        tb.inject(cls=cls)
        rounds, cur = [], None
        while tb.edges < limit:
            o = await tb.cycle({0: tb.desc(0), 1: tb.desc(1)}, int(tb.edges % 7 != 6 or tb.edges < limit // 2))
            if o["fire"]:
                if o["refill"]:
                    if cur is not None:
                        rounds.append(cur)
                    cur = [0, 0]
                if cur is not None:
                    cur[o["out_source"]] += 1
        complete = rounds[1:]
        exp = [1, HW] if phase == "low_high" else [HW, HW]
        assert len(complete) >= 5, f"{phase}: too few rounds {rounds}"
        assert all(r == exp for r in complete), f"{phase}: rounds {complete} != {exp}"
        assert tb.regs()["cls"] == [CLS_CODE[c] for c in cls], "classes must stay fixed in the measured window"
        results[phase] = dict(rounds=len(complete), per_round=exp)
    tb.summary("shares", results)


@cocotb.test()
async def test_stall_hold_and_mid_traffic_reset(dut):
    """Contended traffic with stalls; a reset in the middle of a held grant drops everything and
    restores credits 0 / all H / empty window / RR pointer 0."""
    tb = await new_harness(dut, "stall_reset")
    r = tb.rng
    for rep in range(3):
        await run_cycles(tb, 60, lambda i: {h: tb.desc(h) for h in range(N) if r.random() < 0.5},
                         lambda i: int(i % 7 in (0, 3)))
        o = await tb.cycle({0: tb.desc(0)}, ready=0)
        assert o["out_valid"]
        o = await tb.cycle({}, ready=0)
        assert o["held"], "stalled grant must be held"
        await tb.reset(1 + rep)
        o = await tb.cycle({}, ready=1)
        assert o["out_valid"] == 0 and o["in_ready"] == (1 << N) - 1, "reset must empty every FIFO"
        assert o["r_credit"] == [0] * N and o["r_cls"] == [0] * N and o["r_s"] == 0
        if RR:
            assert o["r_ptr"] == 0, "reset must restore the RR pointer to 0"
    assert tb.cov["held_cycles"] > 20
    tb.summary("stall_reset")


@cocotb.test()
async def test_long_stall(dut):
    """A grant stalled for a long time (at W64/W256 across >= 2 closing edges with S == 0, which
    retain the classes) while every source keeps pushing: held unchanged, then everything drains
    in model order."""
    tb = await new_harness(dut, "long_stall")
    r = tb.rng
    await run_cycles(tb, 30, lambda i: {h: tb.desc(h) for h in range(N) if r.random() < 0.4}, lambda i: 1)
    length = 2 * W + 5 if SMALL_W else 600
    held0 = tb.cov["held_cycles"]
    ptr0 = tb.rr_value()
    await run_cycles(tb, length, lambda i: {h: tb.desc(h) for h in range(N) if r.random() < 0.3}, lambda i: 0)
    assert tb.cov["held_cycles"] - held0 == length - 1
    assert tb.rr_value() == ptr0, "a stall never moves the RR pointer"
    while any(tb.sb):
        await tb.cycle({}, ready=int(r.random() < 0.8))
    if SMALL_W:
        assert tb.cgof["held_across_close"] >= 2
    tb.summary("long_stall", dict(stall_cycles=length))


@cocotb.test()
async def test_timestamp_wrap(dut):
    """Arrival counter deposited just below 2**32. One push per cycle rotating sources in
    ascending order, then drain: with equal effective classes, oldest-first serves the oldest head
    (always credited) and eligible RR serves the ascending rotation, so both equal push order
    across the wrap; stored timestamps match the model."""
    tb = await new_harness(dut, "ts_wrap")
    await tb.cycle({}, ready=0, deposit=0xFFFFFFF8)
    order = []
    for i in range(3 * N + 5):
        d = tb.desc(i % N)
        order.append((i % N, d))
        await tb.cycle({i % N: d}, ready=0)
    got = []
    while len(got) < len(order):
        o = await tb.cycle({}, ready=1)
        assert o["fire"]
        got.append((o["out_source"], o["out_desc"]))
    effective = {EFFECTIVE_CLASS[c] for c in tb.model.classes()}
    assert effective == {HIGH}, "this test assumes no source became Low"
    assert got == order, "service order across the timestamp wrap is not arrival order"
    assert got == rr_rotation(order), "ascending rotation: both orderings coincide by construction"
    tb.summary("ts_wrap", dict(deposit=0xFFFFFFF8))


@cocotb.test()
async def test_reversed_rotation_order(dut):
    """Arrival counter deposited just below 2**32. One push per cycle rotating sources in
    DESCENDING order (N-1, N-2, ..., 0, N-1, ...), then drain. Oldest-first serves push order
    across the wrap; eligible RR ignores arrival time and serves the ascending rotation starting
    at the first pushed source, so the two orderings genuinely differ here."""
    tb = await new_harness(dut, "reversed_rotation")
    await tb.cycle({}, ready=0, deposit=0xFFFFFFF8)
    order = []
    for i in range(3 * N + 5):
        h = (N - 1 - i) % N
        d = tb.desc(h)
        order.append((h, d))
        await tb.cycle({h: d}, ready=0)
    got = []
    while len(got) < len(order):
        o = await tb.cycle({}, ready=1)
        assert o["fire"]
        got.append((o["out_source"], o["out_desc"]))
    effective = {EFFECTIVE_CLASS[c] for c in tb.model.classes()}
    assert effective == {HIGH}, "this test assumes no source became Low"
    rotation = rr_rotation(order)
    assert rotation != order, "test construction: the two orderings must differ"
    expect = rotation if RR else order
    assert got == expect, f"{ORDERING} service order {[s for s, _ in got]} != {[s for s, _ in expect]}"
    tb.summary("reversed_rotation", dict(deposit=0xFFFFFFF8, sources=[s for s, _ in got]))


@cocotb.test()
async def test_eligible_rr_pointer(dut):
    """Hand-derived selection sequences for both orderings (classes H, inside the first window).
    Step 1: src0 @e1 (refill offer held), src2 @e2, src1 @e3. After the src0 refill fire the RR
      pointer is 1: RR serves src1 (pointer source) before the older src2; oldest-first src2.
    Step 2: src0 and src N-1 on one edge, offer latched by a stall, src1 pushed while held: the RR
      pointer stays 3 while held; 2:1 RR picks N-1 (first credited from pointer 3), oldest-first
      the tie winner src0; 1:1 only N-1 has credit. N-1 fires -> pointer wraps to 0.
    Step 3: src N-1 alone fires on credit (pointer wraps to 0); then src0 (credit 0) and src2
      (credit 1): RR skips the pointer source src0 for lack of credit; then the src0 refill with
      RR skipping inactive sources from pointer 3."""
    tb = await new_harness(dut, "eligible_rr_pointer")
    last = N - 1
    seq, ptrs = [], []

    async def fire():
        o = await tb.cycle({}, ready=1)
        assert o["fire"]
        seq.append((o["out_source"], o["refill"]))
        ptrs.append(tb.rr_value())

    # step 1
    await tb.cycle({0: tb.desc(0)}, ready=0)
    await tb.cycle({2: tb.desc(2)}, ready=0)
    await tb.cycle({1: tb.desc(1)}, ready=0)
    for _ in range(3):
        await fire()
    s1 = [(0, 1), (1, 0), (2, 0)] if RR else [(0, 1), (2, 0), (1, 0)]
    assert seq == s1, f"step 1 {seq} != {s1}"
    assert tb.regs()["credit"] == full((0, HW - 1), (1, HW - 1), (2, HW - 1))
    steps = dict(step1=list(seq))
    # step 2
    seq.clear()
    await tb.cycle({0: tb.desc(0), last: tb.desc(last)}, ready=0)
    o = await tb.cycle({}, ready=0)
    assert o["out_valid"] and not o["held"]
    o = await tb.cycle({1: tb.desc(1)}, ready=0)
    assert o["held"]
    if RR:
        assert o["r_ptr"] == 3, "pointer must not move while the grant is held"
    for _ in range(3):
        await fire()
    if WEIGHTED:
        s2 = [(last, 0), (0, 0), (1, 0)] if RR else [(0, 0), (last, 0), (1, 0)]
    else:
        s2 = [(last, 0), (0, 1), (1, 0)]
    assert seq == s2, f"step 2 {seq} != {s2}"
    assert tb.regs()["credit"] == full((0, 0), (1, 0), (2, 1), (last, 1))
    steps["step2"] = list(seq)
    # step 3
    seq.clear()
    skip_credit0 = tb.cgof["rr_skip_no_credit"]
    skip_idle0 = tb.cgof["rr_skip_inactive"]
    await tb.cycle({last: tb.desc(last)}, ready=1)
    await fire()
    await tb.cycle({0: tb.desc(0), 2: tb.desc(2)}, ready=1)
    await fire()
    await fire()
    assert seq == [(last, 0), (2, 0), (0, 1)], f"step 3 {seq}"
    assert tb.regs()["credit"] == full((0, HW - 1))
    steps["step3"] = list(seq)
    if RR:
        assert ptrs == [1, 2, 3, 0, 1, 2, 0, 3, 1], f"RR pointer sequence {ptrs}"
        assert tb.cgof["rr_skip_no_credit"] > skip_credit0, "pointer source without credit not skipped"
        assert tb.cgof["rr_skip_inactive"] > skip_idle0, "inactive pointer source not skipped"
        assert tb.cgof["rr_wraps"] >= 2
    tb.summary("eligible_rr_pointer", dict(steps=steps, rr_pointer=ptrs))


@cocotb.test()
async def test_random(dut):
    """Seeded constrained-random traffic: uniform / hog / burst / sparse / saturate phases,
    Bernoulli and long-stall ready, sporadic resets (some while a grant is held)."""
    tb = await new_harness(dut, "random")
    r = tb.rng
    phases = ("uniform", "hog", "burst", "sparse", "saturate")
    random_resets = 0
    for k in range(RANDOM_CYCLES):
        phase = phases[(k // 1500) % len(phases)]
        hog = (k // 7500) % N
        if phase == "uniform":
            push = {h: tb.desc(h) for h in range(N) if r.random() < 0.6 / N * 2}
            ready = int(r.random() < 0.8)
        elif phase == "hog":
            push = {h: tb.desc(h) for h in range(N) if r.random() < (0.95 if h == hog else 0.05)}
            ready = int(r.random() < 0.9)
        elif phase == "burst":
            on = (k // 40) % 3 == 0
            push = {h: tb.desc(h) for h in range(N) if on and r.random() < 0.7}
            ready = int((k // 25) % 4 != 3)
        elif phase == "sparse":
            push = {h: tb.desc(h) for h in range(N) if r.random() < 0.03}
            ready = int(r.random() < 0.5)
        else:
            push = {h: tb.desc(h) for h in range(N)}
            ready = int(r.random() < 0.97)
        if r.random() < 0.0004:
            random_resets += 1
            await tb.reset(1 + r.randrange(2))
            continue
        await tb.cycle(push, ready)
    assert tb.cov["fires"] > RANDOM_CYCLES // 4, "random traffic delivered too little"
    assert random_resets >= 1 and tb.cov["stalls"] > 100 and tb.cov["full_refusals"] > 0
    d = tb.cgof
    assert d["refill_fires"] > 0 and d["overwrite_fires"] > 0 and d["inactive_credit_refills"] > 0
    assert d["held_refill_cycles"] > 0 and d["reentry_fires"] > 0 and d["credit_blocked_older"] > 0
    if RR:
        assert d["rr_wraps"] > 0 and d["rr_skip_inactive"] > 0 and d["offered_not_oldest"] > 0
    if SMALL_W:
        assert d["windows"] > 10 and d["class_changes"] > 0
    tb.summary("random", dict(random_resets=random_resets, cycles=RANDOM_CYCLES))


# ==================================================================================================
# Stress windows W64 / W256 only (real classification by traffic)
# ==================================================================================================

if SMALL_W:

    @cocotb.test()
    async def test_class_change_held_across_close(dut):
        """Hog src0 for two windows: H -B_H (edge W)- L (edge 2W). A refill offer of src0 is latched
        before closing edge 2W and held across it: its fire commits the OLD (High) weight even though
        src0 is Low from edge 2W on (2:1 credit HW-1 = 1); the round then continues with that
        credit; the next refill uses the new Low weight 1. Classes change inside a round only at
        the next refill. Single active source: identical for both orderings."""
        tb = await new_harness(dut, "class_change_held")
        await run_cycles(tb, W, lambda i: {0: tb.desc(0)}, lambda i: 1)
        assert tb.edges == W and tb.regs()["cls"][0] == CLS_CODE["B_H"]
        while tb.edges < 2 * W - 4:
            await tb.cycle({0: tb.desc(0)}, ready=1)
        while tb.regs()["credit"][0] != 0 and tb.edges < 2 * W - 2:
            await tb.cycle({0: tb.desc(0)}, ready=1)
        assert tb.regs()["credit"][0] == 0 and tb.edges <= 2 * W - 2
        o = await tb.cycle({}, ready=0)  # refill offer latched
        assert o["refill"] == 1 and o["out_source"] == 0 and not o["held"]
        if WEIGHTED:
            assert o["hi"][0] == 1, "snapshot must say High before the close"
        while tb.edges < 2 * W:
            await tb.cycle({}, ready=0)
        assert tb.regs()["cls"][0] == CLS_CODE["L"], "src0 must be Low after closing edge 2W"
        assert tb.cgof["held_across_close"] >= 1
        if WEIGHTED:
            assert tb.cgof["held_refill_class_change"] >= 1
        credits = []
        for _ in range(4):
            o = await tb.cycle({0: tb.desc(0)}, ready=1)
            assert o["fire"] and o["out_source"] == 0
            credits.append((o["held"], o["refill"], tb.regs()["credit"][0]))
        expect = ([(1, 1, 1), (0, 0, 0), (0, 1, 0), (0, 1, 0)] if WEIGHTED else
                  [(1, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0)])  # fmt: skip
        assert credits == expect, f"{credits} != {expect}"
        tb.summary("class_change_held", dict(sequence=credits))

    async def boundary_window(tb, src1_cls, k, s_total):
        """After a reset: inject src1's class, then in window 1 (edges 1..W) push src1 k descriptors
        (edges 1..k) and src0 on every edge; ready 0 until the last s_total edges of the window, so
        exactly s_total fires happen, the last one ON closing edge W (closing fire included).
        Both orderings serve all k src1 descriptors within the first few fires.
        Returns src1's class code after the closing edge."""
        await tb.reset()
        tb.inject(cls=["H", src1_cls] + ["H"] * (N - 2))
        fires0 = tb.cov["fires"]
        while tb.edges < W:
            e = tb.edges + 1  # edge closed by this cycle
            push = {0: tb.desc(0)}
            if e <= k:
                push[1] = tb.desc(1)
            o = await tb.cycle(push, int(e > W - s_total))
            if e > W - s_total:
                assert o["fire"], f"no fire on edge {e}: backlog lost"
        assert tb.cov["fires"] - fires0 == s_total
        assert not tb.sb[1], "every src1 descriptor must be served inside the window"
        return tb.regs()["cls"][1]

    @cocotb.test()
    async def test_window_threshold_boundaries(dut):
        """Hand-derived closing-edge evidence, closing fire included, B1 = k, S = s_total:
        DOWN iff N*B > S (from H: DOWN -> B_H, KEEP -> H): k=2, S=2N -> KEEP, S=2N-1 -> DOWN.
        UP iff 10*N*B < 3*S (from L: UP -> B_L, KEEP -> L): k=1, S=floor(10N/3)+1 -> UP, one less
        -> KEEP (N4: 14 / 13, N8: 27 / 26, N16: 54 / 53)."""
        tb = await new_harness(dut, "thresholds")
        s_up = (10 * N) // 3 + 1
        cases = [("H", 2, 2 * N, "H"), ("H", 2, 2 * N - 1, "B_H"), ("L", 1, s_up, "B_L"), ("L", 1, s_up - 1, "L")]
        seen = []
        for cls, k, s, exp in cases:
            got = await boundary_window(tb, cls, k, s)
            seen.append(dict(start=cls, b=k, s=s, expect=exp, got=CODE_CLS[got]))
            assert got == CLS_CODE[exp], f"src1 {cls} B={k} S={s}: got {CODE_CLS[got]}, expected {exp}"
        tb.summary("thresholds", dict(cases=seen))

# ==================================================================================================
# Production window W5M only: 32-bit threshold boundaries by state injection
# ==================================================================================================

if W == 5_000_000:

    @cocotb.test()
    async def test_w5m_threshold_injection(dut):
        """Inject idx = W-12, B, S and classes into the RTL and the model, then run the last 12
        edges of the window with exactly 5 src0 fires, the last on closing edge W-1 -> 0.
        Production-scale boundaries (closing totals S, B1 for src1):
          DOWN from H: N*B1 == S -> KEEP (H); S one less -> DOWN (B_H)
          UP from L: 10*N*B1 == 3*S -> KEEP (L); B1 one less -> UP (B_L)
          32-bit width: src1 H with B1 = 4,000,000 (10*N*B1 up to 640,000,000 needs 30 bits;
          truncated to the 23-bit count width it would read as UP and keep H): DOWN -> B_H."""
        tb = await new_harness(dut, "w5m_injection")
        f = 5
        b_down = {4: 1_000_000, 8: 600_000, 16: 300_000}[N]
        b_up = {4: 360_000, 8: 180_000, 16: 90_000}[N]
        cases = [("down_keep", "H", b_down, N * b_down, "H"), ("down", "H", b_down, N * b_down - 1, "B_H"),
                 ("up_keep", "L", b_up, 4_800_000, "L"), ("up", "L", b_up - 1, 4_800_000, "B_L"),
                 ("wide", "H", 4_000_000, 4_500_000, "B_H")]  # fmt: skip
        seen = []
        for name, cls, b1, s_final, exp in cases:
            await tb.reset()
            s0 = s_final - f
            b = [s0 - b1, b1] + [0] * (N - 2)
            assert b[0] >= 0
            tb.inject(cls=["H", cls] + ["H"] * (N - 2), idx=W - 12, b=b, s=s0)
            fires0 = tb.cov["fires"]
            for i in range(12):
                o = await tb.cycle({0: tb.desc(0)} if i < f else {}, int(i >= 12 - f))
                if i >= 12 - f:
                    assert o["fire"] and o["out_source"] == 0
            assert tb.cov["fires"] - fires0 == f and tb.regs()["idx"] == 0
            got = tb.regs()["cls"][1]
            seen.append(dict(case=name, start=cls, b1=b1, s=s_final, expect=exp, got=CODE_CLS[got]))
            assert got == CLS_CODE[exp], f"{name}: got {CODE_CLS[got]}, expected {exp}"
        tb.summary("w5m_injection", dict(cases=seen))
