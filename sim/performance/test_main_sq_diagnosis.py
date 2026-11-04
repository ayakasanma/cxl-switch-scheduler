"""Passive Main-SQ diagnosis: the unchanged hog_sparse coroutine plus a recording Metrics.

Only two module globals of test_hog_sparse are substituted for the duration of this test:
Metrics (a subclass that additionally records) and write_json (writes the unchanged metrics
file, then the diagnosis). Traffic, TBs, models, pin checks and check_result are untouched.
The imported module object exposes no test of its own to cocotb discovery here.
"""
import os

import cocotb

import test_hog_sparse as base
from main_sq_diagnosis import DIAG_FILE, TRACE_FILE, Trace, diagnostic_metrics
from switch_fcfs_tb import param_from_env


@cocotb.test()
async def main_sq_diagnosis(dut):
    policy = param_from_env("POLICY")
    assert os.environ["CXL_MAIN_SQ_SCOPE"] == os.environ["CXL_HOG_SPARSE_SCOPE"]
    trace = Trace(TRACE_FILE)
    made, written = [], []
    saved = base.Metrics, base.write_json
    metrics_cls = diagnostic_metrics(saved[0], policy, trace)

    def make(window):
        assert not made, "one Metrics per run"
        made.append(metrics_cls(window))
        return made[0]

    def write(name, data):
        assert name == "hog_sparse_metrics.json" and made and not written
        path = saved[1](name, data)
        saved[1](DIAG_FILE, made[0].recorder.finalize(made[0], data))
        written.append(name)
        return path

    base.Metrics, base.write_json = make, write
    try:
        await base.hog_sparse.func(dut)
    finally:
        base.Metrics, base.write_json = saved
        trace.close()
    assert written == ["hog_sparse_metrics.json"], "diagnosis not written"
