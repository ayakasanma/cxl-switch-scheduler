"""Main diagnosis on the existing common FIFO/hold experimental top."""
import json
import os
from pathlib import Path

import cocotb

from cgof_diagnosis_accounting import DiagnosisAccounting
from cxl_model.experimental import ExperimentalSwitchModel
from test_experiment_top import Harness, P, CLS_CODE


class MainHarness(Harness):
    """Retain the accepted independent Main oracle and compare policy registers."""

    def check_policy_state(self, tag):
        super().check_policy_state(tag)
        m = self.model
        if not m.state_known:
            return
        f = self.fai
        cls = int(f.cls_q.value)
        assert [(cls >> (2*h)) & 3 for h in range(self.n)] == [CLS_CODE[c] for c in m.classes()], tag
        pos, b, s = m.window_state()
        assert int(f.idx_q.value) == pos, (tag, "idx_q")
        bw, bq = m.count_bits, int(f.b_q.value)
        assert [(bq >> (bw*h)) & ((1 << bw)-1) for h in range(self.n)] == list(b), (tag, "b_q")
        assert int(f.s_q.value) == s, (tag, "s_q")
        visit = m.visit_state()
        assert int(f.turn_q.value) == int(visit.cls == "Low"), (tag, "turn_q")
        assert int(f.used_q.value) == visit.fires, (tag, "used_q")
        self.cov["policy_state_checks"] += 1


@cocotb.test()
async def main_diagnosis_rtl(dut):
    job = json.loads(os.environ["CXL_DIAGNOSIS_JOB"])
    assert job["policy"] == "FAI-inspired"
    assert P["POLICY"] == 2 and P["HIGH_QUOTA"] == 10 and P["MAIN_1W"] == 0
    assert (job["n_src"], job["depth"], job["window"]) == (P["N_SRC"], P["DEPTH"], P["FAI_W"])
    harness = MainHarness(dut, "main-diagnosis", job["seed"])
    mirror = ExperimentalSwitchModel(job["n_src"], "FAI-inspired",
                                     window=job["window"], depth=job["depth"])
    harness.mirrors.append(mirror)
    account = DiagnosisAccounting(job, lambda: mirror)
    try:
        await harness.start()
        steps = account.cycles()
        try:
            push, ready = next(steps)
            while True:
                sample = await harness.cycle(push, ready=ready)
                assert mirror.classes() == harness.model.classes(), "Main mirror classes"
                assert mirror.window_state() == harness.model.window_state(), "Main mirror window"
                assert mirror.visit == harness.model.visit_state(), "Main mirror class quota"
                push, ready = steps.send(sample)
        except StopIteration:
            pass
        assert not any(harness.sb)
        result = dict(schema="cxl-main-diagnosis-rtl-v1", evidence_kind="SCHEDULER_RTL",
                      **account.result(), params=P, policy="FAI-inspired",
                      native_coverage=harness.cov, native_main=harness.fai_cov,
                      input_hold_checks=account.input_hold_checks,
                      limitations="scheduler-boundary RTL; not CXL response latency or application slowdown")
    except BaseException as exc:
        result = dict(schema="cxl-main-diagnosis-rtl-v1", **account.failure(exc))
        Path(os.environ["CXL_DIAGNOSIS_FAILURE"]).write_text(json.dumps(result, indent=2)+"\n")
        raise
    Path(os.environ["CXL_DIAGNOSIS_OUTPUT"]).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")


@cocotb.test()
async def main_hold_crosses_class_close(dut):
    """A High-context offer survives its source's High-to-Low closing edge."""
    harness = MainHarness(dut, "held-close", 7301)
    await harness.start()
    for _ in range(2*P["FAI_W"]-1):
        await harness.cycle({0: harness.desc(0)}, ready=1)
    assert harness.model.classes()[0] == "B_H"
    before_visit = harness.model.visit_state()
    service = list(harness.model.service)
    offered = await harness.cycle({1: harness.desc(1)}, ready=0)
    held = tuple(offered[key] for key in ("out_source", "out_desc", "grant_ctx"))
    assert harness.model.classes()[0] == "L", "closing edge must change the effective class"
    for _ in range(3):
        sample = await harness.cycle(ready=0)
        assert tuple(sample[key] for key in ("out_source", "out_desc", "grant_ctx")) == held
        assert harness.model.visit_state() == before_visit, "stall must not consume quota"
        assert harness.model.service == service, "stall must not count as service"
    sample = await harness.cycle(ready=1)
    assert tuple(sample[key] for key in ("out_source", "out_desc", "grant_ctx")) == held
    assert sum(harness.model.service) == sum(service)+1
    Path("main_held_close.json").write_text(json.dumps(dict(
        status="PASS", params=P, coverage=harness.cov,
        changed_class="B_H to L", held_context=list(held),
    ), indent=2)+"\n")
