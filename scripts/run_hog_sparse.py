#!/usr/bin/env python3
"""HS-pilot/HS-main registry extension; all tools run through the existing strict engine."""
import json
from pathlib import Path
import sys

import run_verify as rv
from run_descriptor_followup import check_job_matrix, source_hashes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"sim"/"performance"))
from hog_sparse import POLICIES, Traffic, check_result


def config(policy,pilot):
    window = 256 if pilot else 5_000_000
    params = dict(N_SRC=4,POLICY=policy)
    defaults = dict(rv._SWITCH_DEFAULTS,RR_QUANTUM=10)
    (params if pilot else defaults)["FAI_W"] = window
    return dict(name=f"hs_p{policy}_w{window}",top="switch_top",filelist=rv._SWITCH_FILELIST,
                params=params,default_params=defaults,test_dir="sim/performance",test_module="test_hog_sparse",
                seeds=[509] if pilot else list(range(509,514)),env=dict(CXL_HOG_SPARSE_SCOPE="pilot" if pilot else "main"),
                expect_tests=1,timeout_s=86400,artifacts=[dict(file="hog_sparse_metrics.json",required=True)])


def register():
    for name,pilot in (("HS-pilot",True),("HS-main",False)):
        configs = [config(p,pilot) for p in range(3)]
        rv.MILESTONES[name] = dict(description="Heavy host plus sparse hosts"+(" W256 sensitivity pilot" if pilot else " production W5M"),
                                  implemented=True,cocotb=configs,
                                  lint=[{k:c[k] for k in ("name","top","filelist","params")} for c in configs],
                                  pytest=[dict(name="hog_sparse",target="sim/performance/tests/test_hog_sparse.py",min_tests=1)])


def check_matrix(configs,steps):
    check_job_matrix(configs,steps)
    assert all(s["status"] == "PASS" for s in steps), "failed/missing/skipped strict step"
    assert sum(s["kind"] == "lint" for s in steps) == 3
    assert sum(s["kind"] == "pytest" for s in steps) == 1
    for step in steps:
        if step["kind"] in ("pytest","cocotb"):
            assert step["tests"] > 0 and all(step.get(k,0) == 0 for k in ("failures","errors","skipped"))
    for c in configs:
        assert c == config(c["params"]["POLICY"],c["env"]["CXL_HOG_SPARSE_SCOPE"] == "pilot"), "changed job specification"


class HogRun(rv.Run):
    def write_summary(self,final):
        overall = super().write_summary(final)
        path = self.out/"summary.json"
        summary = json.loads(path.read_text())
        accepted = overall == "PASS" and any(s["kind"] == "scope" and s["status"] == "PASS" for s in self.steps)
        pilot = self.milestone == "HS-pilot"
        summary.update(scope="short-window-sensitivity-pilot" if pilot else "production-heavy-sparse",
                       infrastructure_only=False,sensitivity_evidence=pilot and accepted,
                       production_evidence=not pilot and accepted,
                       milestone_acceptance_scope=not pilot and accepted and self.acceptance_scope(),
                       declared_scope=dict(name=self.milestone,jobs=3 if pilot else 15))
        path.write_text(json.dumps(summary,indent=2)+"\n")
        return overall

    def execute(self):
        before = source_hashes()
        (self.out/"source_hashes_before.json").write_text(json.dumps(before,indent=2)+"\n")
        rc = super().execute()
        problems, accepted, hashes, groups = [], [], {}, {}
        if rc != 0:
            problems.append("strict runner failed")
        if not self.acceptance_scope():
            problems.append("scope override/filter/lint/smoke")
        try:
            check_matrix(self.entry["cocotb"],self.steps)
        except (AssertionError,KeyError) as exc:
            problems.append(str(exc))
        pilot = self.milestone == "HS-pilot"
        for cfg in self.entry["cocotb"]:
            for seed in cfg["seeds"]:
                name = f"{cfg['name']}_seed{seed}"
                try:
                    step = next(s for s in self.steps if s["name"] == "cocotb:"+name)
                    assert step["status"] == "PASS" and all(v == 0 for v in step["exit_codes"].values())
                    p = {**cfg["default_params"],**cfg["params"]}
                    key = (seed,p["FAI_W"])
                    traffic = Traffic(*key)
                    if key not in hashes:
                        for k in range(traffic.end):
                            traffic.step(k)
                        hashes[key] = traffic.sha256
                    data = json.loads((self.out/"results"/f"cocotb_{name}__hog_sparse_metrics.json").read_text())
                    check_result(data,dict(seed=seed,policy_param=p["POLICY"],policy=POLICIES[p["POLICY"]],
                                           window=p["FAI_W"],production_evidence=not pilot,sensitivity_evidence=pilot),hashes[key])
                    groups.setdefault(seed,{})[p["POLICY"]] = data
                    accepted.append(dict(name=name,seed=seed,policy_param=p["POLICY"],trace_sha256=data["trace_sha256"],
                                         metrics_json=f"results/cocotb_{name}__hog_sparse_metrics.json"))
                except (AssertionError,KeyError,OSError,ValueError,StopIteration) as exc:
                    problems.append(f"{name}: {type(exc).__name__}: {exc}")
        try:
            assert set(groups) == ({509} if pilot else set(range(509,514))), "missing seed groups"
            for seed,rows in groups.items():
                assert set(rows) == {0,1,2}, f"incomplete policy triplet seed{seed}"
                assert len({d["trace_sha256"] for d in rows.values()}) == 1, "unpaired trace"
                assert rows[0]["cold_pin_sha256"] == rows[2]["cold_pin_sha256"], "FCFS/Main cold actual pins differ"
        except AssertionError as exc:
            problems.append(str(exc))
        after = source_hashes()
        (self.out/"source_hashes_after.json").write_text(json.dumps(after,indent=2)+"\n")
        if before != after:
            problems.append("frozen sources changed during execution")
        gate = dict(schema="cxl-hog-sparse-scope-v1",declared_matrix_complete=not problems,
                    full_scope=not pilot and not problems,production_evidence=not pilot and not problems,
                    sensitivity_evidence=pilot and not problems,infrastructure_only=False,
                    valid_runs=len(accepted),expected_runs=3 if pilot else 15,paired_trace_groups=len(groups),
                    problems=problems,runs=accepted)
        (self.out/"hog_sparse_scope.json").write_text(json.dumps(gate,indent=2)+"\n")
        self.add_step(dict(order=len(self.steps)+1,kind="scope",name="scope:hog_sparse",
                           status="FAIL" if problems else "PASS",reason="; ".join(problems),log="hog_sparse_scope.json"))
        overall = self.write_summary(final=True)
        self.print_table(overall)
        return 0 if rc == 0 and not problems else 1


if __name__ == "__main__":
    register()
    rv.MILESTONES = {k:v for k,v in rv.MILESTONES.items() if k in ("HS-pilot","HS-main")}
    rv.Run = HogRun
    sys.exit(rv.main())
