#!/usr/bin/env python3
"""MSQ-pilot/MSQ-main passive diagnosis registry; all tools run through the existing strict engine.

Jobs equal run_hog_sparse.config except the cocotb module (which wraps the unchanged
hog_sparse coroutine), job name, scope env and extra required artifacts. The scope gate
regenerates the Traffic hash, applies the existing check_result, requires the metrics to
equal the accepted HS run exactly (wall/RSS excluded), and replays every per-request join
from the per-cycle trace. MSQ-main is seed509 only (representative) and is not launched here.
Reference override: CXL_MSQ_REFERENCE=<accepted HS run directory>.
"""
import json
import os
from pathlib import Path
import sys

import run_verify as rv
import run_hog_sparse as hs
from run_descriptor_followup import check_job_matrix, source_hashes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"sim"/"performance"))
from hog_sparse import POLICIES, Traffic, check_result
from main_sq_diagnosis import DIAG_FILE, TRACE_FILE, VOLATILE, check_diagnosis

METRICS = "hog_sparse_metrics.json"
SCOPES = {"MSQ-pilot": True, "MSQ-main": False}


def config(policy, pilot):
    base = hs.config(policy, pilot)
    window = 256 if pilot else 5_000_000
    scope = "pilot" if pilot else "main"
    return dict(base, name=f"msq_p{policy}_w{window}", test_module="test_main_sq_diagnosis", seeds=[509],
                env=dict(base["env"], CXL_MAIN_SQ_SCOPE=scope),
                artifacts=[dict(file=f, required=True) for f in (METRICS, DIAG_FILE, TRACE_FILE)])


def register():
    for name, pilot in SCOPES.items():
        configs = [config(p, pilot) for p in range(3)]
        rv.MILESTONES[name] = dict(description="Passive Main-SQ baseline diagnosis"+(" W256 INFRASTRUCTURE pilot" if pilot else " W5M seed509"),
                                  implemented=True, cocotb=configs,
                                  lint=[{k: c[k] for k in ("name", "top", "filelist", "params")} for c in configs],
                                  pytest=[dict(name="main_sq_diagnosis", target="sim/performance/tests/test_main_sq_diagnosis.py", min_tests=1),
                                          dict(name="hog_sparse", target="sim/performance/tests/test_hog_sparse.py", min_tests=1)])


def reference_dir(pilot):
    if os.environ.get("CXL_MSQ_REFERENCE"):
        return Path(os.environ["CXL_MSQ_REFERENCE"])
    folder = ROOT/"artifacts"/"implementation"/("HS-pilot" if pilot else "HS-main")
    return folder/(folder/"latest.txt").read_text().strip()


def stable(data):
    return {k: v for k, v in data.items() if k not in VOLATILE}


class DiagnosisRun(rv.Run):
    def write_summary(self, final):
        overall = super().write_summary(final)
        path = self.out/"summary.json"
        summary = json.loads(path.read_text())
        pilot = SCOPES[self.milestone]
        summary.update(scope="infrastructure-pilot" if pilot else "representative-diagnosis",
                       infrastructure_only=pilot, production_evidence=False, sensitivity_evidence=False,
                       milestone_acceptance_scope=False, declared_scope=dict(name=self.milestone, jobs=3))
        path.write_text(json.dumps(summary, indent=2)+"\n")
        return overall

    def execute(self):
        before = source_hashes()
        (self.out/"source_hashes_before.json").write_text(json.dumps(before, indent=2)+"\n")
        rc = super().execute()
        pilot = SCOPES[self.milestone]
        problems, runs, hashes, groups = [], [], {}, {}
        if rc != 0:
            problems.append(f"strict runner exit {rc}")
        if not self.acceptance_scope():
            problems.append("scope override/filter/lint/smoke")
        try:
            check_job_matrix(self.entry["cocotb"], self.steps)
            assert all(s["status"] == "PASS" for s in self.steps), "failed/missing/skipped strict step"
            for c in self.entry["cocotb"]:
                assert c == config(c["params"]["POLICY"], pilot), "changed job specification"
        except (AssertionError, KeyError) as exc:
            problems.append(str(exc))
        try:
            ref = reference_dir(pilot)
        except OSError as exc:
            ref = None
            problems.append(f"reference: {exc}")
        for cfg in self.entry["cocotb"]:
            name = f"{cfg['name']}_seed509"
            try:
                step = next(s for s in self.steps if s["name"] == "cocotb:"+name)
                assert step["status"] == "PASS" and all(v == 0 for v in step["exit_codes"].values())
                p = {**cfg["default_params"], **cfg["params"]}
                key = (509, p["FAI_W"])
                if key not in hashes:
                    traffic = Traffic(*key)
                    for k in range(traffic.end):
                        traffic.step(k)
                    hashes[key] = traffic.sha256
                res = self.out/"results"
                data = json.loads((res/f"cocotb_{name}__{METRICS}").read_text())
                check_result(data, dict(seed=509, policy_param=p["POLICY"], policy=POLICIES[p["POLICY"]],
                                        window=p["FAI_W"], production_evidence=not pilot,
                                        sensitivity_evidence=pilot), hashes[key])
                old_name = f"cocotb_hs_p{p['POLICY']}_w{p['FAI_W']}_seed509__{METRICS}"
                old = json.loads((ref/"results"/old_name).read_text())
                assert stable(data) == stable(old), "metrics differ from accepted HS run"
                diag = json.loads((res/f"cocotb_{name}__{DIAG_FILE}").read_text())
                check_diagnosis(diag, data, res/f"cocotb_{name}__{TRACE_FILE}")
                groups[p["POLICY"]] = data
                runs.append(dict(name=name, policy=POLICIES[p["POLICY"]], exit_codes=step["exit_codes"],
                                 trace_sha256=data["trace_sha256"], reference=f"{ref.name}/{old_name}",
                                 direct_g2f_p99=diag["direct_g2f_p99_nearest_rank"], requests=diag["requests"],
                                 tail_requests=diag["tail_requests"], totals=diag["totals"],
                                 tail_totals=diag["tail_totals"], trace=diag["trace"]))
            except (AssertionError, KeyError, OSError, ValueError, StopIteration, TypeError) as exc:
                problems.append(f"{name}: {type(exc).__name__}: {exc}")
        try:
            assert set(groups) == {0, 1, 2}, "incomplete policy triplet"
            assert len({d["trace_sha256"] for d in groups.values()}) == 1, "unpaired trace"
            assert groups[0]["cold_pin_sha256"] == groups[2]["cold_pin_sha256"], "FCFS/Main cold actual pins differ"
        except AssertionError as exc:
            problems.append(str(exc))
        after = source_hashes()
        (self.out/"source_hashes_after.json").write_text(json.dumps(after, indent=2)+"\n")
        if before != after:
            problems.append("frozen sources changed during execution")
        gate = dict(schema="cxl-main-sq-diagnosis-scope-v1", scope=self.milestone, infrastructure_only=pilot,
                    production_evidence=False, passed=not problems, problems=problems,
                    reference_run=str(ref.relative_to(ROOT)) if ref and ref.is_relative_to(ROOT) else str(ref), runs=runs)
        (self.out/"main_sq_diagnosis_scope.json").write_text(json.dumps(gate, indent=2)+"\n")
        self.add_step(dict(order=len(self.steps)+1, kind="scope", name="scope:main_sq_diagnosis",
                           status="FAIL" if problems else "PASS", reason="; ".join(problems),
                           log="main_sq_diagnosis_scope.json"))
        overall = self.write_summary(final=True)
        self.print_table(overall)
        return 0 if rc == 0 and not problems else 1


if __name__ == "__main__":
    register()
    rv.MILESTONES = {k: v for k, v in rv.MILESTONES.items() if k in SCOPES}
    rv.Run = DiagnosisRun
    sys.exit(rv.main())
