"""SCHEDULER_RTL fairness and finite-Heavy diagnosis through the native CGOF harness.

The per-cycle bookkeeping lives in ``cgof_diagnosis_accounting`` and is shared with the
model-only runner ``cgof_diagnosis_model``; this test answers each requested edge with
``Harness.cycle()`` (pin/model lockstep checks) and adds the DUT-only result fields.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import cocotb

from cgof_diagnosis_accounting import DiagnosisAccounting
from test_cgof_sched import Harness, P, POLICY_NAME


def _write_result(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@cocotb.test()
async def cgof_diagnosis_rtl(dut):
    job = json.loads(os.environ["CXL_DIAGNOSIS_JOB"])
    assert job["n_src"] == P["N_SRC"] and job["depth"] == P["DEPTH"]
    assert job["window"] == P["FAI_W"] and job["high_weight"] == P["HIGH_WEIGHT"]
    expected_ordering_code = {
        "oldest-first": 0,
        "eligible-round-robin": 1,
    }[job["ordering"]]
    assert P["ELIGIBLE_RR"] == expected_ordering_code, (
        "diagnosis job ordering does not match ELIGIBLE_RR"
    )

    harness = None
    account = DiagnosisAccounting(job, lambda: harness.model)
    harness = Harness(dut, f"diagnosis-{account.mode}-{account.lane}", job["seed"])

    try:
        await harness.start()
        steps = account.cycles()
        try:
            push, ready = next(steps)
            while True:
                sample = await harness.cycle(push, ready=ready)
                push, ready = steps.send(sample)
        except StopIteration:
            pass
        assert not any(harness.sb)

        result = {
            "schema": "cxl-cgof-diagnosis-rtl-v1",
            "evidence_kind": "SCHEDULER_RTL",
            **account.result(),
            "params": P,
            "policy": POLICY_NAME,
            "native_coverage": harness.cov,
            "native_cgof": harness.cgof,
            "input_hold_checks": account.input_hold_checks,
            "limitations": (
                "scheduler-boundary RTL only; fire/cycle is not memory bandwidth; "
                "generation-to-fire is not CXL response latency; no application slowdown"
            ),
        }
        _write_result(Path(os.environ.get("CXL_DIAGNOSIS_OUTPUT", "cgof_diagnosis.json")), result)
    except BaseException as exc:
        failure = dict(schema="cxl-cgof-diagnosis-rtl-v1", **account.failure(exc))
        _write_result(
            Path(os.environ.get("CXL_DIAGNOSIS_FAILURE", "cgof_diagnosis_failure.json")),
            failure,
        )
        raise
