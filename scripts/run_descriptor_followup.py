#!/usr/bin/env python3
"""Thin registry extension of run_verify; no alternate build/subprocess implementation.

Run in WSL after sourcing scripts/wsl_env.sh. Scopes: DF-pilot (21 jobs),
DF-controls (36), DF-finite (3), DF-trained (3 real W5M/10M-warmup jobs).
DF-placement (42 short-window sensitivity jobs), DF-placement-pilot (9).
"""
from pathlib import Path
import hashlib
import json
import sys
import time

import run_verify as rv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim" / "common"))
sys.path.insert(0, str(ROOT / "sim" / "performance"))
from followup import LOADS, LOW_SUBSETS, POLICIES, SCHEMA, Traffic, check_result


def config(case, policy, pilot=False, window=5_000_000, low_sources=(0,)):
    placement = case == "placement"
    if placement:
        window = 256
        assert tuple(low_sources) in LOW_SUBSETS
    warmup, measured = ((512,240) if placement else (2*window, 512 if pilot else 100_000) if case == "trained" else
                        (0,1024) if case == "finite" else (128,1024) if pilot else (10_000,100_000))
    params = dict(N_SRC=4, POLICY=policy)
    defaults = dict(rv._SWITCH_DEFAULTS, RR_QUANTUM=10)
    if window != 5_000_000:
        params["FAI_W"] = window
    else:
        defaults["FAI_W"] = window
    name = f"df_{case}_p{policy}_w{window}" + ("_low"+"".join(map(str,low_sources)) if placement else "")
    env = dict(CXL_FOLLOWUP_CASE=case, CXL_FOLLOWUP_WARMUP=warmup,
               CXL_FOLLOWUP_MEASURE=measured, CXL_FOLLOWUP_INFRA=int(pilot and not placement))
    if placement:
        env["CXL_FOLLOWUP_LOW_SOURCES"] = ",".join(map(str,low_sources))
    return dict(name=name, top="switch_top", filelist=rv._SWITCH_FILELIST,
                params=params, default_params=defaults, test_dir="sim/performance",
                test_module="test_descriptor_followup", seeds=[509] if pilot or case not in LOADS else [509,510,511],
                env=env,
                expect_tests=1, timeout_s=86_400 if case == "trained" and not pilot else 7200,
                artifacts=[dict(file="descriptor_followup_metrics.json", required=True)])


def register():
    pilot = [config(c,p,True) for c in LOADS for p in range(3)]
    pilot += [config("finite",p,True) for p in range(3)]
    pilot += [config("trained",p,True,w) for w in (64,256) for p in range(3)]
    scopes = {"DF-pilot":pilot,
              "DF-controls":[config(c,p) for c in LOADS for p in range(3)],
              "DF-finite":[config("finite",p) for p in range(3)],
              "DF-trained":[config("trained",p) for p in range(3)],
              "DF-placement":[config("placement",p,low_sources=low) for low in LOW_SUBSETS for p in range(3)],
              "DF-placement-pilot":[config("placement",p,low_sources=low)
                                    for low in ((2,), (0,3), (0,1,2)) for p in range(3)]}
    for name, cfgs in scopes.items():
        lint = {tuple(c["params"].items()):dict(name=c["name"], top=c["top"],
                                               filelist=c["filelist"], params=c["params"]) for c in cfgs}
        rv.MILESTONES[name] = dict(description="N4 descriptor follow-up" + (" INFRASTRUCTURE ONLY" if name == "DF-pilot" else ""),
                                  implemented=True, lint=list(lint.values()), cocotb=cfgs,
                                  pytest=[dict(name="descriptor_followup", target="sim/performance/tests", min_tests=1)],
                                  followup_scope=True)


def source_hashes():
    paths = [p for folder in ("rtl","refc","sim","scripts","specs") for p in (ROOT/folder).rglob("*")
             if p.suffix in (".py",".sv",".f",".md",".sh") and "__pycache__" not in p.parts]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def check_job_matrix(configs, steps):
    expected = [(c["name"],seed) for c in configs for seed in c["seeds"]]
    actual = [(s["name"].split(":",1)[1].rsplit("_seed",1)[0],s.get("seed"))
              for s in steps if s["kind"] == "cocotb"]
    assert expected and len(expected) == len(set(expected)), "invalid declared matrix"
    assert len(actual) == len(set(actual)) and set(actual) == set(expected), "executed matrix differs from declared matrix"
    for step in steps:
        if step["kind"] == "cocotb":
            assert step["status"] == "PASS", "missing/failed simulation"
            assert step["exit_codes"] and all(c == 0 for c in step["exit_codes"].values()), "nonzero process exit"


class FollowupRun(rv.Run):
    def write_summary(self, final):
        overall = super().write_summary(final)
        path = self.out/"summary.json"
        summary = json.loads(path.read_text())
        infra = self.milestone == "DF-pilot"
        sensitivity = self.milestone in ("DF-placement", "DF-placement-pilot")
        gate_pass = any(s["kind"] == "scope" and s["status"] == "PASS" for s in self.steps)
        summary.update(infrastructure_only=infra,
                       production_evidence=self.milestone == "DF-trained" and gate_pass and overall == "PASS",
                       milestone_acceptance_scope=self.acceptance_scope() and gate_pass and not infra and self.milestone != "DF-placement-pilot" and overall == "PASS",
                       declared_scope=dict(name=self.milestone, jobs=sum(len(c["seeds"]) for c in self.entry["cocotb"])))
        if sensitivity:
            summary.update(sensitivity_evidence=gate_pass and overall == "PASS", scope="short-window-sensitivity")
        if infra:
            summary["scope"] = "infrastructure-pilot"
            if overall in ("PASS", "FAIL"):
                overall = summary["overall"] = "INFRA_SMOKE_" + overall
        path.write_text(json.dumps(summary,indent=2)+"\n")
        return overall

    def execute(self):
        before = source_hashes()
        (self.out/"source_hashes.json").write_text(json.dumps(before,indent=2)+"\n")
        rc = super().execute()
        problems, accepted, hashes = [], [], {}
        if rc != 0:
            problems.append("strict runner failed; matrix cannot be accepted")
        if not self.acceptance_scope():
            problems.append("scope incomplete: override/filter/lint/smoke")
        expected_jobs = {(c["name"],s) for c in self.entry["cocotb"] for s in c["seeds"]}
        try:
            check_job_matrix(self.entry["cocotb"], self.steps)
        except (AssertionError,KeyError) as exc:
            problems.append(str(exc))
        for cfg in self.entry["cocotb"]:
            for seed in cfg["seeds"]:
                name = f"{cfg['name']}_seed{seed}"
                try:
                    step = next(s for s in self.steps if s["name"] == "cocotb:"+name)
                    assert step["status"] == "PASS"
                    assert all(code == 0 for code in step["exit_codes"].values())
                    p = {**cfg["default_params"], **cfg["params"]}
                    e = cfg["env"]
                    traffic = Traffic(e["CXL_FOLLOWUP_CASE"],seed,e["CXL_FOLLOWUP_WARMUP"],
                                      e["CXL_FOLLOWUP_MEASURE"],p["FAI_W"],
                                      tuple(map(int,e.get("CXL_FOLLOWUP_LOW_SOURCES","0").split(","))))
                    key = (traffic.case,seed,traffic.warmup,traffic.end,p["FAI_W"],traffic.low_sources)
                    if key not in hashes:
                        for k in range(traffic.end):
                            traffic.step(k)
                        hashes[key] = traffic.sha256
                    data = json.loads((self.out/"results"/f"cocotb_{name}__descriptor_followup_metrics.json").read_text())
                    expected = dict(case=traffic.case,seed=seed,n_src=4,policy=POLICIES[p["POLICY"]],
                                    policy_param=p["POLICY"],window=p["FAI_W"],warmup_cycles=traffic.warmup,
                                    measurement_cycles=traffic.end-traffic.warmup,
                                    infrastructure_only=bool(e["CXL_FOLLOWUP_INFRA"]),
                                    production_evidence=traffic.case == "trained" and not e["CXL_FOLLOWUP_INFRA"])
                    if traffic.case == "placement":
                        expected.update(low_sources=list(traffic.low_sources), sensitivity_evidence=True)
                    check_result(data,expected,hashes[key])
                    accepted.append(dict(name=name,trace_sha256=data["trace_sha256"]))
                except (AssertionError,OSError,ValueError,KeyError,StopIteration) as exc:
                    problems.append(f"{name}: {type(exc).__name__}: {exc}")
        if before != source_hashes():
            problems.append("source changed during run")
        gate = dict(declared_matrix_complete=not problems,
                    full_scope=not problems and self.milestone not in ("DF-pilot", "DF-placement-pilot"),
                    production_evidence=self.milestone == "DF-trained" and not problems,
                    infrastructure_only=self.milestone == "DF-pilot", problems=problems,
                    valid_runs=len(accepted), expected_runs=len(expected_jobs), runs=accepted)
        if self.milestone in ("DF-placement", "DF-placement-pilot"):
            gate["sensitivity_evidence"] = not problems
        (self.out/"followup_scope.json").write_text(json.dumps(gate,indent=2)+"\n")
        self.add_step(dict(order=len(self.steps)+1,kind="scope",name="scope:descriptor_followup",
                           status="FAIL" if problems else "PASS", reason="; ".join(problems),
                           log="followup_scope.json"))
        overall = self.write_summary(final=True)
        self.print_table(overall)
        return 0 if rc == 0 and not problems else 1


if __name__ == "__main__":
    register()
    rv.Run = FollowupRun
    sys.exit(rv.main())
