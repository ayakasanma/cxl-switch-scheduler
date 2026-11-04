"""Long-scope configuration and evidence gates, without running a simulator."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_verify as rv


def test_long_configs_and_main_defaults():
    assert rv._switch_fai_production_cocotb(4)["params"]["POLICY"] == 2
    assert rv._switch_fai_stress_cocotb(4, 64)["artifacts"][0]["file"] == "fai_stress_metrics.json"
    prod = rv.MILESTONES["M6-production"]
    cfg = prod["cocotb"][0]
    assert cfg["params"] == {"N_SRC": 4, "POLICY": 3}
    assert cfg["default_params"]["FAI_W"] == 5_000_000
    assert cfg["seeds"] == [509] and cfg["env"] == {"CXL_PRODUCTION_CYCLES": 20_000_000}
    assert prod["run_scope"]["min_windows"] >= 3
    stress = rv.MILESTONES["M6-stress"]
    assert [(c["params"]["FAI_W"], c["env"]["CXL_STRESS_CYCLES"]) for c in stress["cocotb"]] == [(64, 400000), (256, 800000)]
    assert all(c["params"]["N_SRC"] == 4 and c["params"]["POLICY"] == 3 and c["seeds"] == list(range(509, 514)) for c in stress["cocotb"])


@pytest.mark.parametrize("scope_name", ["M6-production", "M6-stress"])
@pytest.mark.parametrize("bad", [None, "missing", "short", "smoke", "override", "filter", "lint", "policy", "windows", "transitions", "extra", "empty"])
def test_full_scope_gate(tmp_path, scope_name, bad):
    scope = copy.deepcopy(rv.MILESTONES[scope_name]["run_scope"])
    run = object.__new__(rv.Run)
    run.args = SimpleNamespace(lint_only=bad == "lint")
    run.seeds_override = [509] if bad == "override" else None
    run.n_filter = [4] if bad == "filter" else None
    run.out = tmp_path
    run.steps = []
    run.rel = lambda p: p.name
    run.add_step = lambda step: run.steps.append(step)
    (tmp_path / "results").mkdir()
    for w in scope["fai_w"]:
        for seed in scope["seeds"]:
            name = f"test_w{w}_seed{seed}"
            run.steps.append({"kind": "cocotb", "name": "cocotb:" + name, "params": {"N_SRC": 4, "FAI_W": w}, "seed": seed, "status": "PASS"})
            cycles = scope["cycles_by_w"][w]
            data = dict(schema=scope["schema"], seed=seed, n_src=4, fai_w=w, requested_cycles=cycles,
                        measured_cycles=cycles, infra_smoke=False, outstanding_after_drain=0,
                        windows_closed_measurement=cycles // w, **scope["expect_fields"])
            data["transitions_reached"] = sorted(f"{s}/{e}" for s in scope.get("states", []) for e in ("UP", "DOWN", "KEEP", "S0"))
            if bad == "short": data["measured_cycles"] -= 1
            if bad == "smoke": data["infra_smoke"] = True
            if bad == "policy": data["policy"] = "FAI_MAIN"
            if bad == "windows": data["windows_closed_measurement"] = 0
            if bad == "transitions" and scope.get("require_all_transitions"): data["transitions_reached"].pop()
            (tmp_path / "results" / f"cocotb_{name}__{scope['metrics_file']}").write_text(json.dumps(data))
    if bad == "missing": run.steps.pop()
    if bad == "extra": run.steps.append({"kind": "cocotb", "name": "extra", "params": {"N_SRC": 8}, "seed": 509, "status": "PASS"})
    if bad == "empty": scope["n_src"] = []
    run.run_scope_step(1, scope)
    rejected = bad is not None and not (bad == "transitions" and scope_name == "M6-production")
    assert run.steps[-1]["status"] == ("FAIL" if rejected else "PASS")
