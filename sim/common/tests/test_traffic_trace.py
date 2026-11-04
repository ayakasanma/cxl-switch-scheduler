"""Pure-pytest tests of the policy-independent traffic/ready trace generator and of the TB-only
tagged response model (sim/common/traffic_trace.py, sim/common/tag_response.py).

They check: determinism and hash stability (pinned golden hashes, so a later RR/FAI run that
regenerates the same (seed, N, cycles, profile) is proven to replay the identical intended trace),
independence of the trace from DUT acceptance, unique tags, guaranteed overload/backpressure,
directed long stalls and resets, producer hold-until-push semantics, separate acceptance records,
the P99 estimator and exactly-once response matching.
"""

import random
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))  # sim/common
sys.path.insert(0, str(_HERE.parents[3] / "refc"))

import traffic_trace as tt  # noqa: E402
from cxl_model import FcfsSwitchModel  # noqa: E402
from tag_response import TagResponder  # noqa: E402

# Golden SHA-256 values of the canonical intended trace (generator cxl-traffic-trace-v2). A change
# here means every later policy run would replay DIFFERENT traffic: never update them silently.
GOLDEN = {
    (509, 4, 3000, "primary"): "e0be4985ea6dbb8ee362080eeea26478f4d9aed358ad454bbab8617e349eb9de",
    (528, 16, 3000, "primary"): "14f1ed2b87897d1a1b4b3f58ae93ebdd4fbf364781c4ff67a1e335c137bea0e4",
    (509, 8, 3000, "short"): "c875bd42286642988fb1588a92a0be8c9bd5e9a8435aa7f164dd350424f47530",
}


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_golden_hash_is_stable(key):
    assert tt.make_trace(*key).sha256 == GOLDEN[key]


def test_deterministic_and_hash_recomputes():
    a = tt.make_trace(509, 8, 5000, "primary")
    b = tt.make_trace(509, 8, 5000, "primary")
    assert a.sha256 == b.sha256 == tt.trace_sha256(a)
    assert a.gen == b.gen and a.ready == b.ready and a.reset == b.reset
    assert a.phases == b.phases and a.long_stalls == b.long_stalls


@pytest.mark.parametrize(
    "other", [(510, 8, 5000, "primary"), (509, 4, 5000, "primary"), (509, 8, 5001, "primary"), (509, 8, 5000, "short")]
)
def test_hash_depends_on_every_key_element(other):
    assert tt.make_trace(509, 8, 5000, "primary").sha256 != tt.make_trace(*other).sha256


def test_hash_covers_ready_reset_and_every_descriptor_bit():
    tr = tt.make_trace(511, 4, 2000, "short")
    ref = tr.sha256
    tr.ready[1234] ^= 1
    assert tt.trace_sha256(tr) != ref
    tr.ready[1234] ^= 1
    tr.reset[10] ^= 1
    assert tt.trace_sha256(tr) != ref
    tr.reset[10] ^= 1
    k = next(i for i, g in enumerate(tr.gen) if g)
    s, d = tr.gen[k][0]
    for bit in (0, 72, 73, 104):
        tr.gen[k][0] = (s, d ^ (1 << bit))
        assert tt.trace_sha256(tr) != ref
    tr.gen[k][0] = (s, d)
    assert tt.trace_sha256(tr) == ref


def test_tags_globally_unique_and_descriptors_105_bits():
    tr = tt.make_trace(512, 16, 20000, "primary")
    tags = [tt.tag_of(d) for g in tr.gen for _s, d in g]
    assert len(tags) == tr.generated > 10000
    assert len(set(tags)) == len(tags), "a tag was reused within the trace"
    assert all(0 <= d < (1 << 105) for g in tr.gen for _s, d in g)
    assert all(0 <= s < 16 for g in tr.gen for s, _d in g)
    # at most one generation per source per cycle
    assert all(len({s for s, _d in g}) == len(g) for g in tr.gen)


def test_every_phase_kind_and_overload_present():
    for n in (4, 8, 16):
        tr = tt.make_trace(513, n, 12000, "short")
        kinds = {kind for _s, _l, kind in tr.phases}
        assert kinds == set(tt.PROFILES["short"]["phases"])
        # offered load above one descriptor per cycle inside overload phases
        for start, length, kind in tr.phases:
            if kind in ("overload", "saturate") and length >= 200:
                offered = sum(len(tr.gen[k]) for k in range(start, start + length)) / length
                assert offered > 1.0, (n, kind, offered)


def test_directed_long_stalls_and_resets():
    tr = tt.make_trace(509, 4, 100000, "primary")
    directed = [(s, length) for s, length, why in tr.long_stalls if why == "directed"]
    assert directed == [(25000, 256), (50000, 1024), (75000, 512)]
    for s, length in directed:
        assert not any(tr.ready[s : s + length])
    assert sum(tr.reset) == 0
    assert any(why == "random" for _s, _l, why in tr.long_stalls)
    sh = tt.make_trace(509, 4, 12000, "short")
    assert all(sh.reset[6000:6002]) and sum(sh.reset) >= 2
    assert not any(sh.ready[3600:3900]) and not any(sh.ready[8400:8550])


def test_trace_is_independent_of_dut_acceptance():
    """Replaying with two different acceptance behaviours changes nothing in the trace, and the
    producers present exactly the generated descriptors in order, valid held until push."""
    n = 4
    tr = tt.make_trace(514, n, 4000, "short")
    ref = tr.sha256
    logs = []
    for accept_p in (1.0, 0.1):
        rng = random.Random(accept_p)
        prod = tt.Producers(n)
        presented_prev = {}
        for k in range(tr.cycles):
            prod.generate(k, tr.gen[k])
            offers = prod.offers()
            for h, off in presented_prev.items():
                # an offer not accepted last cycle is presented again, unchanged
                assert offers[h] == off
            presented_prev = {}
            for h, off in offers.items():
                if rng.random() < accept_p:
                    rec = prod.accept(h, k)
                    assert (rec.gen_cycle, rec.desc) == off and rec.push_cycle >= rec.gen_cycle
                else:
                    presented_prev[h] = off
        assert prod.generated == tr.generated == len(prod.accepted) + prod.backlog()
        logs.append([(r.source, r.desc) for r in prod.accepted])
        assert tt.trace_sha256(tr) == ref
    # same per-source order regardless of acceptance timing (prefix relation)
    for h in range(n):
        fast = [d for s, d in logs[0] if s == h]
        slow = [d for s, d in logs[1] if s == h]
        assert fast[: len(slow)] == slow
    with pytest.raises(AssertionError):
        tt.Producers(n).accept(0, 0)


def test_primary_trace_fills_fifos_and_backpressures():
    """Abstract replay on the independent FCFS model: FIFOs reach depth 16 and pushes are refused."""
    n = 4
    tr = tt.make_trace(515, n, 30000, "primary")
    m = FcfsSwitchModel(n)
    m.commit(rst_n=False)
    prod = tt.Producers(n)
    full_seen = refused = 0
    for k in range(tr.cycles):
        prod.generate(k, tr.gen[k])
        offers = prod.offers()
        v = m.view(bool(tr.ready[k]))
        full_seen += int(any(c == 16 for c in v.count))
        refused += sum(1 for h in offers if not v.in_ready[h])
        e = m.commit(bool(tr.ready[k]), [h in offers for h in range(n)], [offers[h][1] if h in offers else 0 for h in range(n)])
        for h in range(n):
            if e.pushed[h] is not None:
                prod.accept(h, k)
    assert full_seen > 100 and refused > 100
    assert max(r.push_cycle - r.gen_cycle for r in prod.accepted) > 16


def test_nearest_rank_p99_and_mean():
    assert tt.nearest_rank_p99([]) is None and tt.mean([]) is None
    assert tt.nearest_rank_p99([7]) == 7
    assert tt.nearest_rank_p99(list(range(1, 101))) == 99  # rank ceil(99) = 99
    assert tt.nearest_rank_p99(list(range(1, 102))) == 100  # rank ceil(99.99) = 100
    assert tt.nearest_rank_p99(list(range(1, 201))) == 198
    assert tt.mean([1, 2, 3, 4]) == 2.5


def test_invalid_arguments():
    with pytest.raises(ValueError):
        tt.make_trace(1, 4, 10, "nope")
    with pytest.raises(ValueError):
        tt.make_trace(1, 1, 10, "primary")
    with pytest.raises(ValueError):
        tt.make_trace(1, 4, 0, "primary")


def test_tag_responder_exactly_once_and_reordering():
    r = TagResponder(random.Random(5), (1, 30), unique_run=True)
    for i in range(200):
        r.issue(0, 0x1000 + i, i, i % 4, i)
        r.step(i, 0)
    for c in range(200, 240):
        r.step(c, 0)
    r.assert_all_complete()
    assert r.completed == r.issued == 200 and r.reordered > 0


def test_tag_responder_rejects_reuse_and_tracks_epochs():
    r = TagResponder(random.Random(1), (5, 5))
    r.issue(0, 0xAB, 10, 1, 0)
    with pytest.raises(AssertionError):
        r.issue(0, 0xAB, 11, 2, 0)  # outstanding tag reused
    r.issue(1, 0xAB, 12, 2, 0)  # new epoch: separate table
    assert [x.epoch for x in r.step(15, 1)] == [0]
    assert r.cross_epoch_completions == 1
    r.issue(1, 0xCD, 16, 0, 0)
    assert [x.tag for x in r.step(21, 1)] == [0xAB, 0xCD]
    r.issue(1, 0xAB, 22, 0, 0)  # reuse after its response is legal
    r.step(30, 1)
    r.assert_all_complete()
    u = TagResponder(random.Random(1), (1, 1), unique_run=True)
    u.issue(0, 7, 0, 0, 0)
    u.step(1, 0)
    with pytest.raises(AssertionError):
        u.issue(0, 7, 2, 0, 0)  # unique_run forbids any reuse
