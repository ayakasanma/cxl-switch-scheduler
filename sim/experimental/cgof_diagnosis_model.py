"""MODEL_ONLY runner for the scheduler-boundary diagnosis jobs of ``test_cgof_diagnosis``.

The bookkeeping is ``cgof_diagnosis_accounting`` (the same code the cocotb test runs). Each
requested edge is answered by the reference model instead of the DUT: the pre-edge sample is
``model.view(ready)`` (the view ``Harness.check()`` asserts the pins against), then the edge is
``model.commit(ready, valid, descs)``. The reset sequence mirrors ``Harness.start()``: one reset
edge with idle inputs followed by ``reset(2)`` edges with every source pushing a descriptor and
``ready=1``. Policies: ``CGOF(1:1)``, ``CGOF(2:1)`` and Main as ``FAI-inspired``.

The output keeps the RTL result schema except the DUT-only fields ``native_coverage``,
``native_cgof`` and ``input_hold_checks``; it is labelled ``MODEL_ONLY``, never SCHEDULER_RTL.

Usage: python cgof_diagnosis_model.py --job JOB.json --output RESULT.json [--policy NAME]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cgof_diagnosis_accounting import DiagnosisAccounting  # noqa: E402
from cxl_model.experimental import ExperimentalSwitchModel  # noqa: E402

SCHEMA = "cxl-cgof-diagnosis-model-v1"
RESET_BUSY_EDGES = 2
ORDERING_CODE = {"oldest-first": 0, "eligible-round-robin": 1}


def job_policy(job: dict) -> str:
    """Policy implied by a CGOF diagnosis job (``high_weight``); Main must be named explicitly."""
    if job.get("policy") == "FAI-inspired":
        return "FAI-inspired"
    return {2: "CGOF(2:1)", 1: "CGOF(1:1)"}[job["high_weight"]]


def job_params(job: dict) -> dict:
    """Same build-parameter record the RTL result carries (``run_rtl_diagnosis.params``)."""
    if job.get("policy") == "FAI-inspired":
        return dict(N_SRC=job["n_src"], POLICY=2, DEPTH=job["depth"],
                    RR_QUANTUM=10, FAI_W=job["window"], HIGH_QUOTA=10, MAIN_1W=0)
    return dict(N_SRC=job["n_src"], DEPTH=job["depth"], FAI_W=job["window"],
                HIGH_WEIGHT=job["high_weight"],
                ELIGIBLE_RR=ORDERING_CODE[job.get("ordering", "oldest-first")])


def new_model(job: dict, policy: str) -> ExperimentalSwitchModel:
    high_weight = job["high_weight"] if policy.startswith("CGOF") else None
    return ExperimentalSwitchModel(job["n_src"], policy, window=job["window"], depth=job["depth"],
                                   high_weight=high_weight,
                                   ordering=job.get("ordering", "oldest-first"))


def reset(model: ExperimentalSwitchModel, n: int, seed: int) -> None:
    """``Harness.start()``: one idle reset edge, then ``reset(2)`` busy reset edges.

    The busy descriptors follow ``Harness.desc`` (harness RNG seeded with the job seed); the
    reset discards them, so they do not reach the traffic or the accounting.
    """
    model.commit(rst_n=False)
    rng, tag = random.Random(seed), 0
    for _ in range(RESET_BUSY_EDGES):
        descs = []
        for h in range(n):
            tag += 1
            descs.append(((tag & 0xFFFFFFFF) << 73) | (rng.getrandbits(32) << 41)
                         | (rng.getrandbits(1) << 40) | (rng.getrandbits(8) << 32)
                         | ((h * 0x01000193 + rng.getrandbits(32)) & 0xFFFFFFFF))
        model.commit(True, [True] * n, descs, False)


def sample(model: ExperimentalSwitchModel, ready: int) -> dict:
    view = model.view(bool(ready), True)
    valid = int(view.out_valid)
    return dict(in_ready=sum(int(b) << h for h, b in enumerate(view.in_ready)),
                out_valid=valid,
                out_source=view.out_source if valid else None,
                out_desc=view.out_desc if valid else None,
                fire=bool(valid and ready))


def run(job: dict, policy: str | None = None) -> dict:
    policy = policy or job_policy(job)
    model = new_model(job, policy)
    account = DiagnosisAccounting(job, lambda: model)
    n = job["n_src"]
    try:
        reset(model, n, job["seed"])
        steps = account.cycles()
        try:
            push, ready = next(steps)
            while True:
                o = sample(model, ready)
                model.commit(bool(ready), [h in push for h in range(n)],
                             [push.get(h, 0) for h in range(n)], True)
                push, ready = steps.send(o)
        except StopIteration:
            pass
        assert not any(model.occupancy(h) for h in range(n)), "model FIFOs not empty after drain"
        return {
            "schema": SCHEMA,
            "evidence_kind": "MODEL_ONLY",
            **account.result(),
            "params": job_params(job),
            "policy": policy,
            "limitations": (
                "MODEL_ONLY reference-model replay of the scheduler-boundary diagnosis; RTL "
                "equivalence holds only where a matching RTL anchor was compared; fire/cycle is not "
                "memory bandwidth; generation-to-fire is not CXL response latency"
            ),
        }
    except BaseException as exc:
        return dict(schema=SCHEMA, evidence_kind="MODEL_ONLY", policy=policy,
                    **account.failure(exc))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--job", required=True, type=Path, help="diagnosis job JSON file")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy", choices=("CGOF(1:1)", "CGOF(2:1)", "FAI-inspired"),
                        help="default: the CGOF weight of the job's high_weight")
    args = parser.parse_args(argv)
    job = json.loads(args.job.read_text(encoding="utf-8"))
    result = run(job, args.policy)
    with open(args.output, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result.get(k) for k in ("status", "policy", "active_cycles",
                                                  "drain_cycles", "wall_s", "error")}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
