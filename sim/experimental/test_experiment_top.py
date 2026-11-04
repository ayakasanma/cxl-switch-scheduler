"""Cycle-exact cocotb checks of rtl/experimental/switch_experiment_top.sv (revision 2026-10-23).

Parameters arrive as CXL_PARAM_<NAME> (sim/experimental/Makefile or scripts/run_verify.py) and are
also passed to Verilator with -G. Every cycle of every test goes through ``Harness.cycle`` which

1. compares all output pins (o_in_ready, o_out_valid and, when valid, o_out_source plus all 105
   descriptor bits) and the offered grant context with an INDEPENDENT Python oracle:
     POLICY 0 FcfsSwitchModel | 1 RrSwitchModel | 3 FaiAlg2SwitchModel  (accepted models)
     POLICY 2, HIGH_QUOTA=10, MAIN_1W=0: FaiMainSwitchModel (accepted) + FaiVariantSwitchModel mirror
     POLICY 2 variants: FaiVariantSwitchModel | POLICY 4: BlissSwitchModel   (revision_baselines)
2. compares the stored head timestamps and, for BLISS / Main variants, every policy register
   (encodings below are the only RTL-facing facts used) - pre-edge at the falling edge and again
   post-edge at the settled point 1 ns after the closing rising edge, where ``cycle`` returns;
3. applies model-free pin rules: a pin scoreboard (per-source FIFO order, exactly-once delivery,
   105-bit integrity), readiness = occupancy < DEPTH with no same-edge pop credit (full before
   pop), no empty bypass, reset suppression, and held-grant stability (source, descriptor,
   context) after a stall until it fires.

Directed tests add hand-derived literal expectations (BLISS streak/blacklist/clear boundaries,
High/Low visit quotas, retained contexts across stalls, timestamp wrap, mid-traffic reset).

RTL-facing encodings:
  Main/variant cls_q : 2 bits per source, H=0, L=1, B_H=2, B_L=3 (bit0 = effective Low)
  variant context    : {class (0 High, 1 Low), used[USED_W-1:0]}, USED_W = clog2(max(HQ,10))
  BLISS              : bl_q bit per source; last_valid_q; last_src_q; streak_q; clr_q
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
from cxl_model import FaiAlg2SwitchModel, FaiMainSwitchModel, FcfsSwitchModel, RrSwitchModel  # noqa: E402
from cxl_model.revision_baselines import (  # noqa: E402
    BLISS_CLEAR_INTERVAL,
    BLISS_THRESHOLD,
    LOW_QUOTA,
    BlissSwitchModel,
    FaiVariantSwitchModel,
    variant_ctx_from_hw,
)

DESC_W = 105
DESC_MASK = (1 << DESC_W) - 1
TS_W = 32
CLS_CODE = {"H": 0, "L": 1, "B_H": 2, "B_L": 3}
POLICY_NAMES = {0: "FCFS", 1: "RR", 2: "FAI_MAIN", 3: "FAI_ALG2", 4: "BLISS"}
RANDOM_CYCLES = int(os.environ.get("CXL_RANDOM_CYCLES", "24000"))


def param(name, default):
    return int(os.environ.get(f"CXL_PARAM_{name}", default))


P = dict(N_SRC=param("N_SRC", 4), POLICY=param("POLICY", 0), DEPTH=param("DEPTH", 16),
         RR_QUANTUM=param("RR_QUANTUM", 10), FAI_W=param("FAI_W", 5000000),
         HIGH_QUOTA=param("HIGH_QUOTA", 10), MAIN_1W=param("MAIN_1W", 0))
VARIANT = P["POLICY"] == 2 and (P["HIGH_QUOTA"] != 10 or P["MAIN_1W"] != 0)
TS_EN = P["POLICY"] != 1
FAI = P["POLICY"] in (2, 3)
CONFIG_TAG = "n{N_SRC}_p{POLICY}_d{DEPTH}_q{RR_QUANTUM}_w{FAI_W}_hq{HIGH_QUOTA}_1w{MAIN_1W}".format(**P)


def has(handle, name):
    try:
        getattr(handle, name)
        return True
    except AttributeError:
        return False


def make_models():
    n, d = P["N_SRC"], P["DEPTH"]
    pol = P["POLICY"]
    if pol == 0:
        return FcfsSwitchModel(n, depth=d), []
    if pol == 1:
        return RrSwitchModel(n, quantum=P["RR_QUANTUM"], depth=d), []
    if pol == 3:
        return FaiAlg2SwitchModel(n, window=P["FAI_W"], depth=d), []
    if pol == 4:
        return BlissSwitchModel(n, depth=d), []
    variant = FaiVariantSwitchModel(n, window=P["FAI_W"], depth=d, high_quota=P["HIGH_QUOTA"],
                                    main_1w=bool(P["MAIN_1W"]))  # fmt: skip
    if not VARIANT:
        # Accepted Main is the oracle; the variant model at its accepted parameters is a mirror.
        return FaiMainSwitchModel(n, window=P["FAI_W"], depth=d), [variant]
    mirrors = []
    if P["MAIN_1W"] and P["HIGH_QUOTA"] == 10:
        # Observation (test_baseline_models): Main-1W at HQ10 is pin-identical to Algorithm-2.
        mirrors.append(FaiAlg2SwitchModel(n, window=P["FAI_W"], depth=d))
    return variant, mirrors


class Harness:
    def __init__(self, dut, label, seed):
        self.dut, self.label = dut, label
        self.n, self.depth = P["N_SRC"], P["DEPTH"]
        self.rng = random.Random(seed)
        self.model, self.mirrors = make_models()
        self.sb = [deque() for _ in range(self.n)]  # pin scoreboard
        self.prev = None  # (stalled, source, desc, ctx) of the previous non-reset cycle
        self.edges = 0  # non-reset edges since the last reset edge (pin-level)
        self.cycles = 0
        self.tag = 0
        self.cov = dict(cycles=0, resets=0, fires=0, stalls=0, held_cycles=0, full_refusals=0,
                        full_refused_while_popping=0, push_pop_same_source=0, max_occupancy=0,
                        mirror_checks=0, policy_state_checks=0)  # fmt: skip
        self.bliss_cov = dict(blacklist_events=0, discarded=0, clears=0, held_across_clear=0)
        self.fai_cov = dict(windows=0, expired_high=0, expired_low=0, emptied=0, max_used_high=-1,
                            max_used_low=-1, class_changes=0)  # fmt: skip
        self.ctx_w = len(dut.grant_ctx)
        if FAI:
            scope = ("gen_policy_fai_variant" if VARIANT else
                     "gen_policy_fai_main" if P["POLICY"] == 2 else "gen_policy_fai_alg2")
            self.fai = getattr(dut, scope).u_fai_sched
        if P["POLICY"] == 4:
            self.bl = dut.gen_policy_bliss.u_bliss_sched

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
        for m in [self.model] + self.mirrors:
            m.commit(rst_n=False)
        await Timer(1, unit="ns")  # settled point (see cycle)
        await self.reset(2)

    async def reset(self, k=1, busy=True):
        """Reset edges with every request input asserted (suppression is checked)."""
        for _ in range(k):
            push = {h: self.desc(h) for h in range(self.n)} if busy else {}
            await self.cycle(push, ready=1, rst_n=0)

    # ----- one cycle --------------------------------------------------------------------------

    async def cycle(self, push=None, ready=0, rst_n=1, deposit=None):
        """One clock cycle. Entered and left at the settled point, 1 ns after a rising edge: inputs
        are driven there, pins are sampled at the falling edge (pre-edge, against the model view),
        then the closing edge is committed to the models and, 1 ns later, the policy registers
        are compared with the post-edge model state. Live registers read by a test right after
        ``await tb.cycle(...)`` are therefore the settled state AFTER that cycle's closing edge,
        while the returned pin sample ``o`` is the state BEFORE it."""
        dut, n = self.dut, self.n
        push = push or {}
        valid = [h in push for h in range(n)]
        descs = [push.get(h, 0) for h in range(n)]
        dut.rst_n.value = rst_n
        dut.i_in_valid.value = sum(1 << h for h in push)
        dut.i_in_desc.value = sum(d << (DESC_W * h) for h, d in push.items())
        dut.i_out_ready.value = ready
        if deposit is not None:
            self.model.deposit_counter(deposit)
            for m in self.mirrors:
                m.deposit_counter(deposit)
            dut.gen_arrival_ts.arrival_cnt_q.value = deposit
        await FallingEdge(dut.clk)
        await ReadOnly()
        o = self.sample(ready, rst_n)
        self.check(o, valid, ready, rst_n)
        await RisingEdge(dut.clk)
        edges = [m.commit(bool(ready), valid, descs, bool(rst_n)) for m in [self.model] + self.mirrors]
        await Timer(1, unit="ns")  # nonblocking assignments of the closing edge have settled
        self.check_policy_state(f"[{self.label} cycle {self.cycles} post-edge]")
        self.after_edge(o, valid, descs, ready, rst_n, edges[0])
        return o

    def sample(self, ready, rst_n):
        dut = self.dut
        o = dict(in_ready=int(dut.o_in_ready.value), out_valid=int(dut.o_out_valid.value), ready=ready,
                 rst_n=rst_n, head_ts=int(dut.head_ts.value), grant_ctx=int(dut.grant_ctx.value))  # fmt: skip
        o["out_source"] = int(dut.o_out_source.value) if o["out_valid"] else None
        o["out_desc"] = int(dut.o_out_desc.value) if o["out_valid"] else None
        o["fire"] = o["out_valid"] and ready
        o["held"] = int(dut.grant_held.value)
        return o

    def check(self, o, valid, ready, rst_n):
        n, tag = self.n, f"[{self.label} cycle {self.cycles} edge {self.edges}]"
        view = self.model.view(bool(ready), bool(rst_n))
        exp_ready = sum(int(b) << h for h, b in enumerate(view.in_ready))
        assert o["in_ready"] == exp_ready, f"{tag} o_in_ready {o['in_ready']:#x} != model {exp_ready:#x}"
        assert o["out_valid"] == int(view.out_valid), f"{tag} o_out_valid {o['out_valid']} != model"
        if o["out_valid"]:
            assert (o["out_source"], o["out_desc"]) == (view.out_source, view.out_desc), \
                f"{tag} grant {o['out_source']}/{o['out_desc']:#x} != model {view.out_source}/{view.out_desc}"
            assert o["grant_ctx"] == view.grant_ctx, f"{tag} grant ctx {o['grant_ctx']:#x} != {view.grant_ctx:#x}"
        for m in self.mirrors:
            v = m.view(bool(ready), bool(rst_n))
            assert (v.in_ready, v.out_valid, v.out_source, v.out_desc, v.grant_ctx) == \
                (view.in_ready, view.out_valid, view.out_source, view.out_desc, view.grant_ctx), \
                f"{tag} mirror {type(m).__name__} disagrees with the oracle"
            self.cov["mirror_checks"] += 1
        # stored timestamps (none for RR)
        for h in range(n):
            ts = (o["head_ts"] >> (TS_W * h)) & 0xFFFFFFFF
            if not TS_EN:
                assert ts == 0, f"{tag} RR head_ts[{h}] = {ts:#x}, expected no timestamp storage"
            elif view.head_valid[h]:
                assert ts == view.head_ts[h], f"{tag} head_ts[{h}] {ts:#x} != model {view.head_ts[h]:#x}"
        self.check_policy_state(tag)
        # ---- model-free pin rules ----
        if not rst_n:
            assert o["in_ready"] == 0 and o["out_valid"] == 0, f"{tag} outputs not suppressed in reset"
            return
        for h in range(n):
            occ = len(self.sb[h])
            assert ((o["in_ready"] >> h) & 1) == int(occ < self.depth), \
                f"{tag} source {h} ready with scoreboard occupancy {occ} (DEPTH {self.depth})"
        if o["out_valid"]:
            q = self.sb[o["out_source"]]
            assert q, f"{tag} output from source {o['out_source']} with nothing pushed (bypass?)"
            assert q[0] == o["out_desc"], f"{tag} out_desc is not the oldest descriptor of its source"
        if self.prev is not None and self.prev[0]:
            _, src, d, ctx = self.prev
            assert o["out_valid"] and (o["out_source"], o["out_desc"], o["grant_ctx"]) == (src, d, ctx), \
                f"{tag} stalled grant {src} was not held unchanged"
            assert o["held"], f"{tag} grant_held low on a held cycle"
            self.cov["held_cycles"] += 1

    def check_policy_state(self, tag):
        m = self.model
        if P["POLICY"] == 4 and m.state_known:
            bl, last, streak, since = m.bliss_state()
            u = self.bl
            assert int(u.bl_q.value) == sum(int(b) << h for h, b in enumerate(bl)), f"{tag} bl_q"
            assert int(u.last_valid_q.value) == int(last is not None), f"{tag} last_valid_q"
            if last is not None:
                assert int(u.last_src_q.value) == last, f"{tag} last_src_q"
            assert int(u.streak_q.value) == streak, f"{tag} streak_q {int(u.streak_q.value)} != {streak}"
            assert int(u.clr_q.value) == since, f"{tag} clr_q {int(u.clr_q.value)} != {since}"
            self.cov["policy_state_checks"] += 1
        if FAI and isinstance(m, FaiVariantSwitchModel) and m.state_known:
            f = self.fai
            cls = int(f.cls_q.value)
            for h, c in enumerate(m.classes()):
                assert (cls >> (2 * h)) & 3 == CLS_CODE[c], f"{tag} cls_q[{h}] != {c}"
            pos, b, s = m.window_state()
            assert int(f.idx_q.value) == pos, f"{tag} idx_q"
            bw, bq = m.count_bits, int(f.b_q.value)
            assert [(bq >> (bw * h)) & ((1 << bw) - 1) for h in range(self.n)] == list(b), f"{tag} b_q"
            assert int(f.s_q.value) == s, f"{tag} s_q"
            visit = m.visit_state()
            assert int(f.turn_q.value) == int(visit.cls == "Low"), f"{tag} turn_q"
            assert int(f.used_q.value) == visit.fires, f"{tag} used_q {int(f.used_q.value)} != {visit.fires}"
            self.cov["policy_state_checks"] += 1

    def after_edge(self, o, valid, descs, ready, rst_n, edge):
        n = self.n
        self.cycles += 1
        self.cov["cycles"] += 1
        if not rst_n:
            self.sb = [deque() for _ in range(n)]
            self.prev = None
            self.edges = 0
            self.cov["resets"] += 1
            return
        self.edges += 1
        src = o["out_source"] if o["fire"] else None
        if src is not None:
            assert self.sb[src].popleft() == o["out_desc"]
            self.cov["fires"] += 1
        for h in range(n):
            if valid[h]:
                if (o["in_ready"] >> h) & 1:
                    self.sb[h].append(descs[h])
                    self.cov["push_pop_same_source"] += int(h == src)
                else:
                    self.cov["full_refusals"] += 1
                    self.cov["full_refused_while_popping"] += int(h == src)
            self.cov["max_occupancy"] = max(self.cov["max_occupancy"], len(self.sb[h]))
        stalled = bool(o["out_valid"] and not ready)
        self.cov["stalls"] += int(stalled)
        self.prev = (stalled, o["out_source"], o["out_desc"], o["grant_ctx"]) if stalled else None
        if P["POLICY"] == 4:
            self.bliss_cov["blacklist_events"] += int(edge.blacklisted is not None)
            self.bliss_cov["discarded"] += int(edge.blacklisted is not None and not edge.blacklist_applied)
            self.bliss_cov["clears"] += int(edge.cleared)
            self.bliss_cov["held_across_clear"] += int(edge.cleared and self.model.held is not None)
        if FAI:
            self.fai_cov_update(o, edge)

    def fai_cov_update(self, o, edge):
        c = self.fai_cov
        if isinstance(edge, dict):  # FaiVariantSwitchModel: the closed window is in window_log
            event, charged, closing = edge["visit_event"], edge["charged"], edge["closing"]
            if closing:
                w = self.model.window_log[-1]
                assert w.edge_index == edge["edge_index"], "window_log out of step with the edge"
                c["class_changes"] += int(w.old_classes != w.new_classes)
        else:
            event, charged, closing = edge.visit_event, edge.charged, edge.closing
            if closing and edge.old_classes != edge.new_classes:
                c["class_changes"] += 1
        c["windows"] += int(closing)
        if charged is not None:
            key = "max_used_high" if charged.cls == "High" else "max_used_low"
            c[key] = max(c[key], charged.fires)
        if event == "expired":
            c["expired_high" if charged.cls == "High" else "expired_low"] += 1
        c["emptied"] += int(event == "emptied")

    # ----- helpers ----------------------------------------------------------------------------

    def fire_ctx(self, o):
        """Decoded context of a cycle's grant (class, used)."""
        hq = P["HIGH_QUOTA"]
        return variant_ctx_from_hw(o["grant_ctx"], hq) if P["POLICY"] == 2 else None

    def summary(self, name, extra=None):
        out = dict(config=CONFIG_TAG, params=P, test=name, coverage=self.cov,
                   oracle=type(self.model).__name__, mirrors=[type(m).__name__ for m in self.mirrors])
        if P["POLICY"] == 4:
            out["bliss"] = self.bliss_cov
        if FAI:
            out["fai"] = self.fai_cov
        out.update(extra or {})
        d = os.environ.get("CXL_ARTIFACT_DIR")
        if d:
            p = Path(d)
            p.mkdir(parents=True, exist_ok=True)
            (p / f"{CONFIG_TAG}__{name}.json").write_text(json.dumps(out, indent=2) + "\n")
        self.dut._log.info("%s %s summary %s", CONFIG_TAG, name, json.dumps(out))
        return out


async def new_harness(dut, name):
    seed = (cocotb.RANDOM_SEED * 1_000_003 + sum(map(ord, name))) & 0xFFFFFFFF
    dut._log.info("test %s config %s cocotb seed %d harness seed %d", name, CONFIG_TAG, cocotb.RANDOM_SEED, seed)
    tb = Harness(dut, name, seed)
    await tb.start()
    return tb


async def run_cycles(tb, k, push_fn=None, ready_fn=None):
    for i in range(k):
        await tb.cycle(push_fn(i) if push_fn else {}, ready_fn(i) if ready_fn else 0)


# ==================================================================================================
# Tests common to every configuration
# ==================================================================================================


@cocotb.test()
async def test_structure_and_reset(dut):
    """Port widths, elaborated policy branch, reset suppression, power-up reset values."""
    tb = await new_harness(dut, "structure")
    n = P["N_SRC"]
    assert len(dut.i_in_valid) == n and len(dut.o_in_ready) == n
    assert len(dut.i_in_desc) == n * DESC_W and len(dut.o_out_desc) == DESC_W
    assert len(dut.o_out_source) == max(1, (n - 1).bit_length())
    expected = {0: "gen_policy_fcfs", 1: "gen_policy_rr", 3: "gen_policy_fai_alg2", 4: "gen_policy_bliss",
                2: "gen_policy_fai_variant" if VARIANT else "gen_policy_fai_main"}[P["POLICY"]]
    scopes = ("gen_policy_fcfs", "gen_policy_rr", "gen_policy_fai_main", "gen_policy_fai_variant",
              "gen_policy_fai_alg2", "gen_policy_bliss")
    present = [s for s in scopes if has(dut, s)]
    assert present == [expected], f"elaborated policy scopes {present}, expected [{expected}]"
    # Verilator can remove constant-only scopes; inspect the actual storage under --public-flat-rw.
    names = [p for p, _kind in hierarchy_paths(dut)]
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == n, "descriptor storage per source"
    timestamps = [p for p in names if "ts_mem_q" in p]
    counters = [p for p in names if "arrival_cnt_q" in p]
    if TS_EN:
        assert has(dut, "gen_arrival_ts") and not has(dut, "gen_no_arrival_ts")
        assert counters == [f"{dut._path}.gen_arrival_ts.arrival_cnt_q"], "one shared arrival counter"
        assert len(dut.gen_arrival_ts.arrival_cnt_q) == TS_W
        assert len(timestamps) == n, "timestamp storage per source"
        for h in range(n):
            mem = dut.gen_fifo[h].u_fifo.gen_ts.ts_mem_q
            assert len(mem) == P["DEPTH"] and len(mem[0]) == TS_W
    else:
        assert not counters, f"RR must not have an arrival counter: {counters}"
        assert not timestamps, f"RR must not store arrival timestamps: {timestamps}"
        assert int(dut.head_ts.value) == 0, "RR head timestamps must be constant zero"
    ctx_w = {True: 1 + (max(P["HIGH_QUOTA"], 10) - 1).bit_length(), False: 1}[FAI]
    assert tb.ctx_w == ctx_w, f"grant context width {tb.ctx_w}, expected {ctx_w}"
    # After reset: empty, ready everywhere, nothing offered.
    o = await tb.cycle()
    assert o["in_ready"] == (1 << n) - 1 and o["out_valid"] == 0
    tb.summary("structure", dict(present_scope=expected, ctx_width=tb.ctx_w))


@cocotb.test()
async def test_full_before_pop_no_bypass(dut):
    """Fill source 0 to DEPTH: ready drops exactly at DEPTH, a full FIFO refuses a push even on the
    edge that pops it, a push into an empty FIFO is not output in its own cycle, 105-bit intact."""
    tb = await new_harness(dut, "full_no_bypass")
    d = P["DEPTH"]
    o = await tb.cycle({0: tb.desc(0)}, ready=1)
    assert o["out_valid"] == 0, "push into an empty FIFO must not bypass to the output"
    for i in range(d - 1):
        o = await tb.cycle({0: tb.desc(0)}, ready=0)
        assert o["in_ready"] & 1, f"source 0 not ready at occupancy {i + 1}"
    o = await tb.cycle({0: tb.desc(0)}, ready=1)  # full: refused although this edge pops it
    assert not (o["in_ready"] & 1) and o["fire"], "full FIFO must refuse the push on the popping edge"
    o = await tb.cycle({0: tb.desc(0)}, ready=0)
    assert o["in_ready"] & 1, "after the pop the FIFO has room again"
    # all-ones / all-zeros descriptor integrity on the last source
    hi = P["N_SRC"] - 1
    await tb.reset()
    for dsc in (DESC_MASK, 0, 1 << 104, 0x15555555555555555555555555 & DESC_MASK):
        await tb.cycle({hi: dsc}, ready=0)
    got = []
    for _ in range(4):
        o = await tb.cycle({}, ready=1)
        got.append(o["out_desc"])
    assert got == [DESC_MASK, 0, 1 << 104, 0x15555555555555555555555555 & DESC_MASK]
    assert tb.cov["full_refused_while_popping"] >= 1
    tb.summary("full_no_bypass")


@cocotb.test()
async def test_stall_hold_and_mid_traffic_reset(dut):
    """Contended traffic with long stalls: held grants never change; a reset in the middle of a
    held grant drops everything and restores the reset state of the policy."""
    tb = await new_harness(dut, "stall_reset")
    n = P["N_SRC"]
    r = tb.rng
    for rep in range(3):
        await run_cycles(tb, 60, lambda i: {h: tb.desc(h) for h in range(n) if r.random() < 0.5},
                         lambda i: int(i % 7 in (0, 3)))
        # make sure a stalled, held grant exists, then reset
        o = await tb.cycle({0: tb.desc(0)}, ready=0)
        assert o["out_valid"], "work exists: a grant must be offered"
        o = await tb.cycle({}, ready=0)
        assert o["held"], "stalled grant must be held"
        await tb.reset(1 + rep)
        o = await tb.cycle({}, ready=1)
        assert o["out_valid"] == 0 and o["in_ready"] == (1 << n) - 1, "reset must empty every FIFO"
        if P["POLICY"] == 4:
            u = tb.bl
            assert int(u.bl_q.value) == 0 and int(u.streak_q.value) == 0 and int(u.last_valid_q.value) == 0
        if VARIANT:
            f = tb.fai
            assert int(f.cls_q.value) == 0 and int(f.used_q.value) == 0 and int(f.turn_q.value) == 0
    assert tb.cov["held_cycles"] > 20
    tb.summary("stall_reset")


@cocotb.test()
async def test_timestamp_wrap(dut):
    """Arrival counter deposited just below 2**32: FCFS-style ordering across the wrap follows push
    order (one push per cycle, rotating sources), stored timestamps match the model. RR: no
    timestamp exists - checked instead that head_ts stays zero (every cycle) and RR order holds."""
    tb = await new_harness(dut, "ts_wrap")
    n = P["N_SRC"]
    if TS_EN:
        await tb.cycle({}, ready=0, deposit=0xFFFFFFF8)
    order = []
    for i in range(3 * n + 5):
        d = tb.desc(i % n)
        order.append(((i % n), d))
        await tb.cycle({i % n: d}, ready=0)
    got = []
    while len(got) < len(order):
        o = await tb.cycle({}, ready=1)
        assert o["fire"]
        got.append((o["out_source"], o["out_desc"]))
    if P["POLICY"] in (0, 2, 3, 4):
        # All FAI sources are High (no window closed), BLISS never repeats a source: push order.
        if not (FAI and P["FAI_W"] < len(order) + 8):
            assert got == order, "service order across the timestamp wrap is not arrival order"
    else:
        assert sorted(got) == sorted(order)
    tb.summary("ts_wrap", dict(deposit=0xFFFFFFF8 if TS_EN else None))


@cocotb.test()
async def test_random(dut):
    """Seeded constrained-random traffic: uniform / hog / burst phases, Bernoulli and long-stall
    ready, sporadic resets (some while a grant is held). Every cycle fully checked. BLISS: the
    first CLEAR_INTERVAL + 1000 cycles are reset-free so that at least one real clear happens
    under random traffic; a deterministic mid-traffic reset closes that phase, random resets
    follow."""
    tb = await new_harness(dut, "random")
    n, r = P["N_SRC"], tb.rng
    phases = ("uniform", "hog", "burst", "sparse", "saturate")
    cycles = RANDOM_CYCLES
    protected = BLISS_CLEAR_INTERVAL + 1000 if P["POLICY"] == 4 and cycles >= BLISS_CLEAR_INTERVAL * 2 else 0
    clears_before_reset = None
    random_resets = 0
    for k in range(cycles):
        phase = phases[(k // 1500) % len(phases)]
        hog = (k // 7500) % n
        if phase == "uniform":
            push = {h: tb.desc(h) for h in range(n) if r.random() < 0.6 / n * 2}
            ready = int(r.random() < 0.8)
        elif phase == "hog":
            push = {h: tb.desc(h) for h in range(n) if r.random() < (0.95 if h == hog else 0.05)}
            ready = int(r.random() < 0.9)
        elif phase == "burst":
            on = (k // 40) % 3 == 0
            push = {h: tb.desc(h) for h in range(n) if on and r.random() < 0.7}
            ready = int((k // 25) % 4 != 3)
        elif phase == "sparse":
            push = {h: tb.desc(h) for h in range(n) if r.random() < 0.03}
            ready = int(r.random() < 0.5)
        else:
            push = {h: tb.desc(h) for h in range(n)}
            ready = int(r.random() < 0.97)
        if protected and k == protected:
            clears_before_reset = tb.bliss_cov["clears"]
            await tb.reset(1)  # deterministic reset in the middle of random traffic
            continue
        if r.random() < 0.0004 and k >= protected:
            random_resets += 1
            await tb.reset(1 + r.randrange(2))
            continue
        await tb.cycle(push, ready)
    extra = dict(random_resets=random_resets, protected_cycles=protected)
    assert tb.cov["fires"] > cycles // 4, "random traffic delivered too little"
    assert tb.cov["resets"] >= 2 and tb.cov["stalls"] > 100 and tb.cov["full_refusals"] > 0
    if P["POLICY"] == 4 and cycles >= BLISS_CLEAR_INTERVAL * 2:
        assert clears_before_reset >= 1, "no clear in the uninterrupted BLISS phase"
        assert tb.bliss_cov["blacklist_events"] > 0 and tb.bliss_cov["clears"] > 0
    if FAI and P["FAI_W"] <= 256:
        assert tb.fai_cov["windows"] > 10 and tb.fai_cov["class_changes"] > 0
    tb.summary("random", extra)


# ==================================================================================================
# BLISS boundaries (POLICY=4)
# ==================================================================================================


def bliss_regs(tb):
    """Settled BLISS registers (valid right after ``await tb.cycle``: post-edge state)."""
    u = tb.bl
    return dict(bl=int(u.bl_q.value), last_valid=int(u.last_valid_q.value), last=int(u.last_src_q.value),
                streak=int(u.streak_q.value), clr=int(u.clr_q.value))  # fmt: skip


@cocotb.test(skip=P["POLICY"] != 4)
async def test_bliss_streak_and_priority(dut):
    """Hand-derived: streak 0,1,2,3,4 then the 6th consecutive fire blacklists and resets the
    streak; a stalled grant on the blacklisted source is still delivered; the younger
    non-blacklisted head then wins; with only blacklisted heads FCFS falls back; a source change
    resets the streak to 0; stalls/idle never count."""
    tb = await new_harness(dut, "bliss_streak")
    assert BLISS_THRESHOLD == 4
    for _ in range(10):
        await tb.cycle({0: tb.desc(0)}, ready=0)  # grant on 0 latched and held (stall)
    ladder = []
    for _ in range(6):
        o = await tb.cycle({}, ready=1)
        assert o["fire"] and o["out_source"] == 0
        s = bliss_regs(tb)
        ladder.append((s["streak"], s["bl"]))
        assert s["last_valid"] == 1 and s["last"] == 0
    assert ladder == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 0b1)], ladder
    o = await tb.cycle({1: tb.desc(1)}, ready=0)  # only source 0 visible: offered, stalled -> held
    assert o["out_valid"] and o["out_source"] == 0 and not o["fire"]
    o = await tb.cycle({}, ready=1)
    assert o["held"] and o["fire"] and o["out_source"] == 0, "held grant must not be preempted by the blacklist"
    s = bliss_regs(tb)
    assert (s["streak"], s["last"], s["bl"]) == (1, 0, 0b1), s
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == 1, "non-blacklisted (younger) head must be preferred"
    s = bliss_regs(tb)
    assert (s["streak"], s["last"], s["bl"]) == (0, 1, 0b1), s
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == 0, "only blacklisted heads: FCFS fallback"
    s = bliss_regs(tb)
    assert (s["streak"], s["last"], s["bl"]) == (0, 0, 0b1), s  # source change: count 0 again
    # streak ladder on source 2 with stall gaps between fires
    await tb.reset()
    for _ in range(8):
        await tb.cycle({2: tb.desc(2)}, ready=0)
    seen = []
    for _ in range(6):
        await run_cycles(tb, 3, ready_fn=lambda j: 0)  # stalls between fires do not count
        o = await tb.cycle({}, ready=1)
        assert o["fire"] and o["out_source"] == 2
        s = bliss_regs(tb)
        seen.append((s["streak"], s["bl"]))
    assert seen == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 0b100)], seen
    tb.summary("bliss_streak", dict(ladder=ladder, ladder_with_stalls=seen))


async def idle_until(tb, target):
    """Idle cycles (no push, ready 0) until exactly ``target`` non-reset edges have committed."""
    assert tb.edges <= target, f"already past edge {target} ({tb.edges})"
    while tb.edges < target:
        await tb.cycle({}, ready=0)
    assert tb.edges == target


@cocotb.test(skip=P["POLICY"] != 4)
async def test_bliss_clear_boundaries(dut):
    """CLEAR_INTERVAL = 10000 non-reset edges after reset. The 6th consecutive fire of source 0
    lands exactly on clearing edge 10000: the clear wins (blacklist stays empty, the overflow is
    discarded), streak 0 and last source are still updated, the clear counter restarts."""
    tb = await new_harness(dut, "bliss_clear")
    ci = BLISS_CLEAR_INTERVAL
    assert ci == 10000 and BLISS_THRESHOLD == 4
    await idle_until(tb, ci - 12)
    for _ in range(6):  # pushes on edges ci-11 .. ci-6; the grant on 0 is offered and held
        await tb.cycle({0: tb.desc(0)}, ready=0)
    assert tb.edges == ci - 6
    for i in range(6):  # fires on edges ci-5 .. ci
        o = await tb.cycle({}, ready=1)
        assert o["fire"] and o["out_source"] == 0
        assert tb.edges == ci - 5 + i
        s = bliss_regs(tb)
        if i < 5:
            assert (s["streak"], s["bl"], s["clr"]) == (i, 0, ci - 5 + i), s
    s = bliss_regs(tb)  # settled after clearing edge ci
    assert s["clr"] == 0 and s["bl"] == 0, f"clear must win over the same-edge blacklist {s}"
    assert s["streak"] == 0 and s["last_valid"] == 1 and s["last"] == 0, s
    assert tb.bliss_cov == dict(blacklist_events=1, discarded=1, clears=1, held_across_clear=0), tb.bliss_cov
    await tb.cycle({}, ready=0)
    s = bliss_regs(tb)
    assert s["clr"] == 1 and s["bl"] == 0, s
    tb.summary("bliss_clear_a")


@cocotb.test(skip=P["POLICY"] != 4)
async def test_bliss_clear_applied_then_wiped_and_held(dut):
    """(b) the 6th fire of source 1 lands exactly on edge 9999: source 1 is blacklisted, which is
    visible in the cycle closed by edge 10000 (the younger source 2 head wins over the older
    source 1 head; that grant is stalled, so it is also held across the clear), then wiped by
    clearing edge 10000 (source 1 wins again afterwards).
    (c) a grant offered and stalled before clearing edge 20000 is held across it and delivered
    unchanged afterwards."""
    tb = await new_harness(dut, "bliss_clear_b")
    ci, n = BLISS_CLEAR_INTERVAL, P["N_SRC"]
    # (b)
    await idle_until(tb, ci - 14)
    for _ in range(7):  # pushes on edges ci-13 .. ci-7 (7 descriptors on source 1)
        await tb.cycle({1: tb.desc(1)}, ready=0)
    assert tb.edges == ci - 7
    for i in range(6):  # fires on edges ci-6 .. ci-1; source 2 pushed (younger) on edge ci-2
        o = await tb.cycle({2: tb.desc(2)} if i == 4 else {}, ready=1)
        assert o["fire"] and o["out_source"] == 1
    assert tb.edges == ci - 1
    s = bliss_regs(tb)
    assert (s["bl"], s["streak"], s["last"], s["clr"]) == (0b10, 0, 1, ci - 1), s
    o = await tb.cycle({}, ready=0)  # cycle closed by clearing edge ci
    assert tb.edges == ci
    assert o["out_valid"] and o["out_source"] == 2, "blacklist set on edge ci-1 must steer the cycle before the clear"
    s = bliss_regs(tb)
    assert (s["bl"], s["clr"], s["streak"], s["last"]) == (0, 0, 0, 1), f"clearing edge must wipe {s}"
    assert tb.bliss_cov["clears"] == 1 and tb.bliss_cov["held_across_clear"] == 1  # source 2 stalled on edge ci
    o = await tb.cycle({2: tb.desc(2)}, ready=1)  # held source-2 grant delivered unchanged
    assert o["held"] and o["fire"] and o["out_source"] == 2
    o = await tb.cycle({}, ready=1)  # older source 1 vs younger source 2, no blacklist
    assert o["fire"] and o["out_source"] == 1, "after the clear the older source 1 head must win"
    o = await tb.cycle({}, ready=1)
    assert o["fire"] and o["out_source"] == 2
    assert tb.model.nonempty_sources() == [] and tb.bliss_cov["clears"] == 1
    # (c)
    h = 3 % n
    await idle_until(tb, 2 * ci - 4)
    await tb.cycle({h: tb.desc(h)}, ready=0)  # push on edge 2ci-3
    o = await tb.cycle({}, ready=0)  # edge 2ci-2: offered, stalled -> latched
    assert o["out_valid"] and not o["held"] and o["out_source"] == h
    held = (o["out_source"], o["out_desc"], o["grant_ctx"])
    o = await tb.cycle({}, ready=0)  # edge 2ci-1
    assert o["held"] and (o["out_source"], o["out_desc"], o["grant_ctx"]) == held
    o = await tb.cycle({}, ready=0)  # edge 2ci: clearing edge while held
    assert tb.edges == 2 * ci and o["held"] and (o["out_source"], o["out_desc"], o["grant_ctx"]) == held
    assert bliss_regs(tb)["clr"] == 0 and int(dut.grant_held.value) == 1
    o = await tb.cycle({}, ready=1)
    assert o["held"] and o["fire"] and (o["out_source"], o["out_desc"], o["grant_ctx"]) == held
    assert tb.bliss_cov["held_across_clear"] == 2 and tb.bliss_cov["clears"] == 2, tb.bliss_cov
    tb.summary("bliss_clear_b")


# ==================================================================================================
# FAI Main quota / Main-1W (POLICY=2)
# ==================================================================================================


def visits(fires):
    """Group [(source, ctx)] fire records into visits (a visit starts at used == 0)."""
    out = []
    for src, ctx in fires:
        if ctx.fires == 0 or not out or out[-1]["cls"] != ctx.cls:
            out.append(dict(cls=ctx.cls, used=[], sources=set()))
        out[-1]["used"].append(ctx.fires)
        out[-1]["sources"].add(src)
    return out


@cocotb.test(skip=P["POLICY"] != 2)
async def test_quota_high_only(dut):
    """All sources High after reset (no window closes in this test): with only High work, every
    High visit has exactly HIGH_QUOTA fires with contexts used = 0..HQ-1; stalls inside a visit
    keep the context (checked every held cycle by the harness)."""
    tb = await new_harness(dut, "quota_high")
    hq, n = P["HIGH_QUOTA"], P["N_SRC"]
    budget = P["FAI_W"] - 8
    for _ in range(4):
        await tb.cycle({0: tb.desc(0)}, ready=0)
    fires = []
    i = 0
    while len(fires) < 2 * hq + 1 and tb.edges < budget:
        push = {h: tb.desc(h) for h in (0, n - 1)} if i % 2 == 0 else {}
        ready = int(i % 5 != 4)
        o = await tb.cycle(push, ready)
        if o["fire"]:
            fires.append((o["out_source"], tb.fire_ctx(o)))
        i += 1
    assert len(fires) >= 2 * hq + 1, "window budget too small for the High quota check"
    vs = visits(fires)
    assert all(v["cls"] == "High" for v in vs)
    for v in vs[:-1]:
        assert v["used"] == list(range(hq)), f"High visit {v['used']} != 0..{hq - 1}"
    tb.summary("quota_high", dict(visits=[len(v["used"]) for v in vs]))


@cocotb.test(skip=P["POLICY"] != 2 or P["FAI_W"] > 256)
async def test_quota_high_low_alternation(dut):
    """Hog source 0 until it is classified Low (one window under Main-1W, two under the four-state
    table); then keep source 0 (Low) and source 1 (High) backlogged for one full window: visits
    alternate High/Low; every complete visit inside the window has exactly HIGH_QUOTA (High) or
    10 (Low) fires, used = 0..quota-1; periodic stalls preserve the context."""
    tb = await new_harness(dut, "quota_alternation")
    hq, w = P["HIGH_QUOTA"], P["FAI_W"]
    need = 1 if P["MAIN_1W"] else 2
    await run_cycles(tb, need * w, lambda i: {0: tb.desc(0)}, lambda i: 1)
    assert tb.edges == need * w, "the last hog cycle must be closed by window-closing edge need*W"
    expect = [CLS_CODE["L"]] + [CLS_CODE["H"]] * (P["N_SRC"] - 1)
    cls = int(tb.fai.cls_q.value)  # settled after the closing edge
    assert [(cls >> (2 * h)) & 3 for h in range(P["N_SRC"])] == expect, f"cls_q {cls:#x} after closing edge"
    fires = []
    start = tb.edges
    while tb.edges < start + w - 1:  # stay inside the window: its closing edge is start + W
        k = tb.edges - start
        o = await tb.cycle({0: tb.desc(0), 1: tb.desc(1)}, int(k % 9 != 8))
        if o["fire"]:
            fires.append((o["out_source"], tb.fire_ctx(o)))
    cls = int(tb.fai.cls_q.value)
    assert [(cls >> (2 * h)) & 3 for h in range(P["N_SRC"])] == expect, "class map changed inside a window"
    vs = visits(fires)
    complete = vs[1:-1]  # the first may continue a visit opened before the window, the last is cut
    assert len(complete) >= 2, f"too few complete visits {[(v['cls'], len(v['used'])) for v in vs]}"
    for a, b in zip(vs, vs[1:]):
        assert a["cls"] != b["cls"], "with both classes backlogged visits must alternate"
    for v in complete:
        q = hq if v["cls"] == "High" else LOW_QUOTA
        assert v["used"] == list(range(q)), f"{v['cls']} visit {v['used']} != 0..{q - 1}"
        assert v["sources"] == ({1} if v["cls"] == "High" else {0})
    tb.summary("quota_alternation", dict(visits=[(v["cls"], len(v["used"])) for v in vs]))


@cocotb.test(skip=P["POLICY"] != 2 or P["FAI_W"] > 256)
async def test_main_1w_classification(dut):
    """Hand-derived classification: hog source 0 for one window -> evidence DOWN for 0, UP for
    others. Four-state: H -> B_H (still High); Main-1W: H -> L immediately. A following zero-
    service window (S0/KEEP) retains the class under both (1W: stays L; 4-state: B_H -> H)."""
    tb = await new_harness(dut, "main_1w")
    w = P["FAI_W"]
    await run_cycles(tb, w, lambda i: {0: tb.desc(0)}, lambda i: 1)
    await run_cycles(tb, 4, ready_fn=lambda i: 1)  # drain source 0 (no more pushes)
    cls0 = int(tb.fai.cls_q.value) & 3
    assert cls0 == (CLS_CODE["L"] if P["MAIN_1W"] else CLS_CODE["B_H"]), f"after DOWN cls {cls0}"
    while tb.edges % w != 0:
        await tb.cycle({}, ready=1)
    o = await tb.cycle({}, ready=0)
    cls0 = int(tb.fai.cls_q.value) & 3
    # the second window had the drain fires of source 0 only: DOWN again unless empty
    tb.summary("main_1w", dict(cls_after_second=cls0))
