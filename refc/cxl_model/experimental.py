"""MODEL_ONLY closed-loop policy experiments; accepted models remain untouched.

Uses the accepted FIFO/hold controller and FAI-inspired classification arithmetic. All
selection uses beginning-cycle local heads, acceptance times and policy state.
Absolute acceptance edges order timestamps under the spec's half-range assumption.
"""
from collections import deque
from typing import NamedTuple

from .common_ctrl_model import Candidate, CommonCtrlModel, NO_CANDIDATE
from .fai_main_model import (
    EFFECTIVE_CLASS, FaiCtx, HIGH, MAIN_TRANSITIONS, ctx_to_hw,
    other_class, threshold_evidence, window_widths,
)
from .revision_baselines import MAIN_1W_TRANSITIONS


POLICIES = ("FAI-inspired", "RR10", "FCFS", "CGOF(2:1)", "CGOF(1:1)") + tuple(
    f"AGE_T{t}_K{k}" for t in (16, 32, 64) for k in (8, 16)
) + ("AGE_ONLY",)
CLASSIFIERS = ("live", "1w", "frozen")


class Choice(NamedTuple):
    source: int
    visit: FaiCtx
    rescue: bool = False
    credits: tuple = ()


class ExperimentalEdge(NamedTuple):
    reset: bool
    pushed: tuple
    fired: object
    rescue: bool
    closing: object


class ExperimentalSwitchModel:
    """Same view/commit convention as accepted switches; bounded policy history.

    AGE_ONLY is a negative control: age-only urgency, oldest urgent first,
    without the gap/budget guard. Under persistent urgency it can equal FCFS.
    """

    def __init__(self, n_src=4, policy="FAI-inspired", window=5_000_000, depth=16,
                 desc_width=105, ts_width=32, gap_max=65535,
                 high_weight=None, ordering="oldest-first", classifier="live"):
        if policy not in POLICIES and policy != "CGOF":
            raise ValueError(f"unsupported policy {policy!r}")
        configured_weight = {"CGOF(2:1)": 2, "CGOF(1:1)": 1}.get(policy)
        if high_weight is None:
            high_weight = configured_weight or 2
        if (type(high_weight) is not int or high_weight not in (1, 2)
                or configured_weight is not None and configured_weight != high_weight):
            raise ValueError("CGOF High:Low allocation must be 1:1 or 2:1 and match configuration")
        if classifier not in CLASSIFIERS:
            raise ValueError(f"unsupported classifier {classifier!r}")
        if ordering not in ("oldest-first", "eligible-round-robin"):
            raise ValueError("unsupported eligible-source ordering")
        if ordering != "oldest-first" and not policy.startswith("CGOF"):
            raise ValueError("eligible-round-robin is a credit-gated control")
        self.high_weight, self.ordering = high_weight, ordering
        policy = "CGOF" if policy.startswith("CGOF") else policy
        window_widths(window)
        if n_src < 2 or depth < 1 or desc_width < 1 or ts_width < 2:
            raise ValueError("invalid source count, depth or field width")
        self.threshold = int(policy.split("_")[1][1:]) if policy.startswith("AGE_T") else 16
        self.budget_limit = int(policy.split("_")[2][1:]) if policy.startswith("AGE_T") else 0
        if not isinstance(gap_max, int) or gap_max < self.threshold:
            raise ValueError("gap_max must cover the urgency threshold")
        self.n_src, self.policy, self.window, self.depth = n_src, policy, window, depth
        self.classifier = classifier
        self.ts_width, self.gap_max = ts_width, gap_max
        self.ctrl = CommonCtrlModel(n_src, depth, policy != "RR10", 5, desc_width, ts_width)
        self.arrivals = [deque() for _ in range(n_src)]
        self.state_known = False
        self.edge_index = 0
        self._reset_policy()

    def _reset_policy(self):
        self.cls = ["H"] * self.n_src
        self.visit = FaiCtx(HIGH, 0)
        self.poll = self.used = self.win_pos = self.s = self.windows_closed = 0
        self.b = [0] * self.n_src
        self.service = [0] * self.n_src
        self.credits = [0] * self.n_src
        self.gaps = [0] * self.n_src
        self.budget = self.rescues = 0
        self._held_choice = None
        self.time = self.counter_init = 0

    def occupancy(self, source):
        return self.ctrl.occupancy(source)

    def classes(self):
        return tuple(self.cls) if self.state_known else None

    def window_state(self):
        return (self.win_pos, tuple(self.b), self.s) if self.state_known else None

    def counter(self):
        return (self.counter_init + self.time) % (1 << self.ts_width)

    def deposit_counter(self, value):
        if (not self.state_known or self.time or any(self.arrivals)
                or not 0 <= value < (1 << self.ts_width)):
            raise ValueError("counter deposit requires empty first post-reset cycle and valid value")
        self.counter_init = value

    def _oldest(self, sources):
        return min(sources, key=lambda h: (self.arrivals[h][0], h))

    def _normal(self, active):
        turn = self.visit.cls
        eligible = [h for h in active if EFFECTIVE_CLASS[self.cls[h]] == turn]
        ctx = self.visit
        if not eligible:
            eligible = active
            ctx = FaiCtx(other_class(turn), 0)
        return Choice(self._oldest(eligible), ctx)

    def choice(self):
        active = [h for h in range(self.n_src) if self.arrivals[h]]
        if not self.state_known or not active:
            return None
        for h in active:
            if self.time - self.arrivals[h][0] >= 1 << (self.ts_width - 1):
                raise AssertionError("head exceeds timestamp half-range")
        if self._held_choice is not None:
            return self._held_choice
        if self.policy == "RR10":
            h = next((self.poll + k) % self.n_src for k in range(self.n_src)
                     if (self.poll + k) % self.n_src in active)
            return Choice(h, FaiCtx(HIGH, 0))
        if self.policy == "FCFS":
            return Choice(self._oldest(active), FaiCtx(HIGH, 0))
        if self.policy == "CGOF":
            credits = tuple(self.credits)
            eligible = [h for h in active if credits[h] > 0]
            if not eligible:
                credits = tuple(self.high_weight if EFFECTIVE_CLASS[c] == HIGH else 1
                                for c in self.cls)
                eligible = active
            source = (self._oldest(eligible) if self.ordering == "oldest-first" else
                      min(eligible, key=lambda h: (h - self.poll) % self.n_src))
            return Choice(source, self.visit, credits=credits)
        normal = self._normal(active)
        if self.policy.startswith("AGE"):
            urgent = [h for h in active if self.time - self.arrivals[h][0] >= self.threshold
                      and (self.policy == "AGE_ONLY" or self.gaps[h] >= self.threshold)]
            if urgent and (self.policy == "AGE_ONLY" or self.budget >= self.budget_limit):
                h = (self._oldest(urgent) if self.policy == "AGE_ONLY" else
                     min(urgent, key=lambda h: (-self.gaps[h], self.arrivals[h][0], h)))
                if h != normal.source:
                    return Choice(h, normal.visit, rescue=True)
        return normal

    def _candidate(self, choice):
        if choice is None:
            return NO_CANDIDATE
        ctx = ctx_to_hw(choice.visit) if self.policy == "FAI-inspired" else 0
        return Candidate(True, choice.source, ctx)

    def view(self, out_ready=False, rst_n=True):
        return self.ctrl.view(self._candidate(self.choice()), out_ready, rst_n)

    def commit(self, out_ready=False, in_valid=None, in_desc=None, rst_n=True):
        if rst_n and not self.state_known:
            raise AssertionError("reset required before use")
        choice = self.choice() if rst_n else None
        active = [bool(q) for q in self.arrivals]
        eff = [EFFECTIVE_CLASS[c] for c in self.cls]
        edge = self.ctrl.commit(self._candidate(choice), out_ready, in_valid, in_desc,
                                self.counter(), rst_n=rst_n)
        self.edge_index += 1
        if not rst_n:
            for q in self.arrivals:
                q.clear()
            self._reset_policy()
            self.state_known = True
            return ExperimentalEdge(True, edge.pushed, None, False, None)
        fired = edge.fired
        g = fired.source if fired else None
        if fired:
            assert choice.source == g
            self.arrivals[g].popleft()
            self.service[g] += 1
        for h, entry in enumerate(edge.pushed):
            if entry is not None:
                self.arrivals[h].append(self.time)
            assert len(self.arrivals[h]) == self.occupancy(h)
            self.gaps[h] = (0 if not active[h] or h == g or not self.arrivals[h] else
                            min(self.gap_max, self.gaps[h] + int(bool(out_ready))))
        rescue = bool(fired and choice.rescue)
        if fired:
            if self.policy == "CGOF":
                self.credits = list(choice.credits)
                assert self.credits[g] > 0
                self.credits[g] -= 1
                if self.ordering == "eligible-round-robin":
                    self.poll = (g + 1) % self.n_src
            elif self.policy == "RR10":
                self.used += 1
                if self.used == 10 or not self.arrivals[g]:
                    self.poll, self.used = (g + 1) % self.n_src, 0
                else:
                    self.poll = g
            elif self.policy != "FCFS":
                if rescue:
                    self.budget = 0
                    self.rescues += 1
                else:
                    self.budget = min(self.budget_limit, self.budget + 1)
                    ctx = choice.visit
                    live = any(self.arrivals[h] and eff[h] == ctx.cls for h in range(self.n_src))
                    self.visit = (FaiCtx(other_class(ctx.cls), 0) if ctx.fires + 1 == 10 or not live
                                  else FaiCtx(ctx.cls, ctx.fires + 1))
            self.b[g] += 1
            self.s += 1
        self._held_choice = choice if edge.latched or self.ctrl.held else None
        closing = None
        self.win_pos += 1
        if self.win_pos == self.window:
            evidence = tuple(threshold_evidence(self.n_src, b, self.s) for b in self.b)
            old = tuple(self.cls)
            if self.classifier == "live":
                self.cls = [MAIN_TRANSITIONS[c, e] for c, e in zip(old, evidence)]
            elif self.classifier == "1w":
                self.cls = [MAIN_1W_TRANSITIONS[c, e] for c, e in zip(old, evidence)]
            else:
                self.cls = ["H"] * self.n_src
            closing = dict(window=self.windows_closed, counts=tuple(self.b), total=self.s,
                           evidence=evidence, old_classes=old, classes=tuple(self.cls))
            self.windows_closed += 1
            self.win_pos = self.s = 0
            self.b = [0] * self.n_src
        self.time += 1
        return ExperimentalEdge(False, edge.pushed, fired, rescue, closing)
