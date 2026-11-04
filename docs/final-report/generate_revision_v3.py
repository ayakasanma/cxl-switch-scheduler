"""Generate v3-only table fragments from hash-pinned accepted evidence (stdlib only)."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import platform
import re
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parents[2]
E = ".setup-logs/implementation/revision-20261024/"
FINAL = E + "power-index/final498-20261027/"
N60 = E + "n-expansion-analysis-20261027/full60-output/analysis.json"
POWER = E + "trained-power-results-20261026/analysis-output/analysis.json"
PPA = "artifacts/fastx/revision-dac-ppa-20261023T190649Z/"
SUPPLEMENT = ".setup-logs/implementation/manuscript-revision-20261027/data/domain-repair/existing-records.json"
INPUT_PINS = {'.setup-logs/implementation/revision-20261024/n-expansion-analysis-20261027/full60-output/analysis.json': 'c196865abf056e552a380bcfd461bd8acec421f8e177c8c6644e7d5718639786',
 '.setup-logs/implementation/revision-20261024/n-expansion-analysis-20261027/full60-release.json': 'c6255e142c21750d2ed6c4c19ad3b561ff342116f38666772c260c984a5689e7',
 '.setup-logs/implementation/revision-20261024/parent-continuation-20261026T0906/index-final18-adoption.json': '78aaef88589fd9ee785740de3d11441a389f0a7ba317d8b0190f417517a3db53',
 '.setup-logs/implementation/revision-20261024/parent-continuation-20261026T1518/robustness-index-adoption.json': '7ebbb680a326901c4bff09f8409f71ecefd73ba660c154137b5d560104c608f2',
 '.setup-logs/implementation/revision-20261024/parent-continuation-20261027T0325/final498-adoption.json': '16445cbcbcc10be603e619405fd7c170605c3c0694398a88bb30b2b387f430c4',
 '.setup-logs/implementation/revision-20261024/parent-continuation-20261027T0325/n60-report-adoption.json': '54ab9d38df70a6efdb22cccfc5c14781c8e4751f46109af31130e40e1d05a33f',
 '.setup-logs/implementation/revision-20261024/power-index/final498-20261027/release.json': '75399940a90fa0973552e78ee1c64341b47b6b0873fa96dc3e29ac4bfa113771',
 '.setup-logs/implementation/revision-20261024/power-index/final498-20261027/snapshot/analysis/analysis.json': '89170cfbe0bb449c25ebbe782203b1695550b7b6bb9e467bae8d6bb00b483061',
 '.setup-logs/implementation/revision-20261024/power-index/final498-20261027/snapshot/index/matrix-coverage.json': '1defb1bbebe31948b5a2834e3510bfcda660190a8630732593bb2169c462f668',
 '.setup-logs/implementation/revision-20261024/power-index/robustness-sealed-20261026t1518/release.json': '1fea76a9c574f2b47a3c6b94299f62748db0ad3d19cf80d341af13f082397af2',
 '.setup-logs/implementation/revision-20261024/power-parent-review-20261024T0904/sources.json': 'd29d645b6a67d9f3f146447f0f6c29cbbbe0e50d3925c9da2b4e251b25ff061a',
 '.setup-logs/implementation/revision-20261024/trained-power-results-20261026/analysis-output/analysis.json': '8c3fac19a7c59e44da32d059f44f7e4418efe6ea689e3c05a549200f587709df',
 '.setup-logs/implementation/revision-20261024/trained-power-results-20261026/release.json': 'de013ee77aad3ede0fa2505c32d554d38cd6b158249c401c7525cfe635913b0e',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/DOWNLOAD_SHA256.json': '1775de8637b0153c951a10ffd507975ad2afdd9838e873b8475d566bd0fe49f4',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/formal/reports/verify.rpt': '6a8ddbc84c0908f116243e5d8ab739ad9e7ad5b362b0348a9ede212dc8cbc305',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/reports/area_summary.rpt': '4812d5be69c4155e9205a8ae1dde2ba94b71f2677aa6a12766e9dfd7b2e43c0d',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/reports/pt_coverage_summary.rpt': '47b4aadb8df25a5cb8c8941492b16c38a4086e0c72a4b47b0557f945d8d40796',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/reports/pt_timing_max.rpt': 'd52f6c16a30b4f075a5d6c47715449cb2c663063947074fefc6025986ba82de7',
 'artifacts/fastx/revision-dac-ppa-20261023T190649Z/reports/pt_timing_min.rpt': '89a59c4b59af422352d5c9fbfb61735a7654826e829d539ceccc8897d51ec2f7',
 'docs/experiments/revision-20261023/ADAPTATION_RESULTS.md': '13e4b7a0235b21b26101f719fe05f99ed2e8056fa749cd743882e3e2640dacb3',
 'docs/experiments/revision-20261023/BASELINES.md': '214104ea52ec3b60f12ab2892f3e2cccbaf5fcd7cdb0fb937b6a83854974245b',
 'docs/experiments/revision-20261023/CONFIRMATION_RESULTS.md': '9d30335e303110c44c52363d974c183c21ba1a97b945cc4fe9ba1dc09655fd5b',
 'docs/experiments/revision-20261023/DAC_PPA_RESULTS.md': 'a5128c7e7cbbd00a3f3a732452f0fd070d1e11573746dde6dcffc6b66c260980',
 'docs/experiments/revision-20261023/DEPTH_RESULTS.md': '9cdc1c35c8fa51a1485029e40d489daf1cc9999ab20e3edc30602a1e21ae21f0',
 'docs/experiments/revision-20261023/METHOD_DIFFERENCES.md': '167915c983da04d628c6485b8fad8864b547abefbb11e800851a93fa5f554c62',
 'docs/experiments/revision-20261023/N_EXPANSION_RESULTS.md': 'e64149b686c8b326f6baa4881108c2d9abff59ddc8e8c07bf74f03c383dc0e7c',
 'docs/experiments/revision-20261023/ROBUSTNESS_RESULTS.md': '9493e7c765f94fb078ce1a1013077f4c93a3c669ea45189f2b53d7982c0d8a48',
 'docs/experiments/revision-20261023/SENSITIVITY_RESULTS.md': '8913bbdf268d12a356435508a71057c0f0446fca9423f32d239600345dd5d6ed',
 'docs/experiments/revision-20261023/TRAINED_POWER_RESULTS.md': 'd1fa1aa3f624b22cc5d04f32c09988e29129cb8ac1c38575bfaf9c4de0311aad',
 'docs/final-report/generate_results.py': 'e6a7fcd2add1597bc2cca0952fe1719a03c798d20584cbe59664557e4bf2d9fb',
 'docs/final-report/generated/evidence_manifest.json': '723bdbec5a6803e6322fcd886822b961e0929ec41479bc4aa5b35b076c1fb184',
 'docs/final-report/generated/results.tex': 'c1ae15bb7b7a2c5084b46a2eef043f2e0af1d46fe36fb712ecf489f2526a94db',
 'docs/ppa/algorithm2-n4-20261021.json': '0421ad3803d436c345cc4d6aa965c9f2e146dd9a427bb185587be32d1be47642',
 'docs/ppa/formality-20261021.json': '3100ee92c9e6cad14aeaabc4275680c282e726e6e6adc5a676d14077a4863dbc',
 'docs/ppa/power-20261021.json': '30b4621c0827daf5c210a6a6e7d65c4e6a049cef531cc433dd864ec540ed70db',
 'docs/ppa/power-supplement-20261021.json': 'b9facc797d4b280cc32b2186a1a063339b7ad42b4fee013b9c865aef5a84ad30',
 'docs/ppa/primary-20261021-v2.json': '168e4bd6f44c3e850948ff1f4942d571a46e91a9272c940170c99e988b892a1d',
 'syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json': 'b6cc33219d1fe240a81d653e7dd3848e784586b5e4e885886e9f407d19619f8c'}
POLICIES = ("FCFS", "RR1", "RR10", "MAIN", "ALG2", "BLISS", "DAC2")
INPUT_PINS[SUPPLEMENT] = "674e9b1f9780de87a1c4347aa167771131bbfa710b54a6e402aac16c0e8c5fa9"
LABELS = dict(MAIN="FAI-inspired", ALG2="Algorithm-2", BLISS="BLISS-inspired",
              DAC1="CGOF (1:1)", DAC2="CGOF (2:1)")
HIGH_LOW = dict(DAC1="1:1", DAC2="2:1")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bound_bytes(root, pins):
    """Check all top-level bytes before interpreting any JSON/report content."""
    result = {}
    for name, expected in pins.items():
        raw = (root / name).read_bytes()
        require(digest(raw) == expected, "input hash mismatch: " + name)
        result[name] = raw
    return result


def cohort(rows, seeds):
    require(sorted(r["seed"] for r in rows) == list(seeds), "incomplete/duplicate seed cohort")
    for r in rows:
        hist = {int(k): v for k, v in r["histogram"].items()}
        require(all(k >= 0 and type(v) is int and v > 0 for k, v in hist.items()), "histogram domain")
        n = sum(hist.values())
        require(n == r["count"] and n > 0, "histogram count")
        rank, count = (99*n+99)//100, 0
        for value in sorted(hist):
            count += hist[value]
            if count >= rank:
                require(value == r["p99"], "histogram P99")
                break
    return dict(n=len(rows), p99=mean(r["p99"] for r in rows), wait=mean(r["mean"] for r in rows))


def number(value, places=2):
    return f"{Decimal(str(value)):.{places}f}"


def table(name, columns, header, rows):
    def escape(value):
        return str(value).replace("_", r"\_").replace("%", r"\%")
    content = ["\\newcommand{\\" + name + r"}{%", r"\begin{tabular}{" + columns + "}", r"\hline",
               " & ".join(header) + r" \\", r"\hline"]
    content.extend(" & ".join(escape(x) for x in row) + r" \\" for row in rows)
    content.extend([r"\hline", r"\end{tabular}%", "}"])
    return "\n".join(content)


def disjoint_area_rows(audit):
    """Keep the accepted audit's four bins and signed printed-report residual."""
    cases = audit["cases"]
    require(len(cases) == 9 and {c["case_id"] for c in cases} ==
            {f"n{n}-{p}" for n in (4,8,16) for p in ("fcfs","rr","fai-main")}, "area nine identities")
    require(audit["summary"]["total_expanded_leaf_instances"] == 540590, "area leaf coverage")
    result = []
    for c in cases:
        cats = c["attribution"]["categories"]
        require(set(cats) == {"descriptor_storage","timestamp_storage","policy","common","unresolved"}, "area category bins")
        values = [Decimal(cats[k]["area"]) for k in ("descriptor_storage","timestamp_storage","policy","common")]
        rec = c["area_reconciliation"]
        total, residual = Decimal(rec["area_summary_total_cell_area"]), Decimal(rec["summary_minus_leaf_area"])
        require(Decimal(cats["unresolved"]["area"]) == 0 and rec["reconciled"] is True
                and sum(values) == Decimal(c["attribution"]["category_area_sum"])
                and sum(values)+residual == total and abs(residual) <= Decimal(rec["tolerance"]), "area reconciliation")
        if c["parameters"]["N_SRC"] == 4:
            result.append(dict(case_id=c["case_id"],policy=c["parameters"]["policy_name"],
                               categories={k:v["area"] for k,v in cats.items()},
                               whole_cell_area=str(total),summary_minus_leaf_area=str(residual)))
    return result


def existing_records(root, raw):
    """Verify the finite existing-record closure; do not replay or re-audit it."""
    supplement = json.loads(raw[SUPPLEMENT])
    pins = supplement["record_hashes"]
    for name, expected in pins.items():
        with (root/name).open("rb") as stream:
            actual = hashlib.file_digest(stream,"sha256").hexdigest()
        require(actual == expected, "existing record hash mismatch: " + name)
    def load(name):
        require(name in pins, "unbound existing record: " + name)
        return json.loads((root/name).read_bytes())
    bridge = supplement["formal_bridges"]
    b,p,a = (load(bridge[k]) for k in ("result","provenance","acceptance"))
    require(b["status"] == "PASS" and a["acceptance"] == "SIX_SOURCE_BRIDGES_PASS"
            and a["provenance_sha256"] == pins[bridge["provenance"]]
            and set(b["cases"]) == {f"{p}-n{n}" for p in ("fcfs","rr") for n in (4,8,16)}, "six bridge acceptance")
    for name,c in b["cases"].items():
        require(c["status"] == "PASS" and c["outer_exit"] == 0 and c["report_sha256"] == a["cases"][name]["report_sha256"], "bridge reports/acceptance")
        prefix = str(Path(bridge["result"]).parent.as_posix())+"/reports/"+name+"/"
        for report,h in c["report_sha256"].items():
            require(pins.get(prefix+report) == h, "bridge report binding")
        require(load(prefix+"source-before.json") == load(prefix+"source-after.json") == p["cases"][name]["expected_hashes"], "bridge source chain")
    area = supplement["primary_disjoint_area"]
    audit, verification = load(area["results"]), load(area["verification"])
    require(verification["tests_returncode"] == 0 and verification["tests_passed"] == 18
            and all(c["area_attribution_provenance_and_inventory_unchanged"] for c in verification["cases"]), "area accepted receipt")
    n4 = disjoint_area_rows(audit)
    for c in audit["cases"]:
        for key,path in c["inputs"].items():
            require(pins.get(path) == c["provenance"]["sha256"][key], "area source/report binding")
    sq = supplement["main_sq"]
    replay, closeout = load(sq["audit"]), load(sq["acceptance"])
    require(replay["status"] == closeout["status"] == "PASS"
            and closeout["archive_sha256"] == pins[sq["portable_bundle"]], "SQ accepted closure")
    for ref in replay["inputs"]:
        require(pins.get(ref["path"]) == ref["sha256"], "SQ raw binding")
    main = next(r for r in replay["results"] if r["policy"] == "FAI_MAIN")
    diagnosis = load(next(r["path"] for r in replay["inputs"] if "p2_" in r["path"] and r["path"].endswith("__main_sq_diagnosis.json")))
    sq["claim_locators"] = dict(trace_rows=diagnosis["trace"]["rows"],requests=main["actual_rtl"]["pooled"]["count"],
        quota_expiries=main["class_visits"]["quota_exhaustions_with_high_pending"],
        target=next(r for r in replay["paired_tail_examples"] if r["tag"] == 10410514),
        main_pooled=main["actual_rtl"]["pooled"],main_source2=main["actual_rtl"]["per_source"]["2"],
        fixed_slot_screens=main["software_fixed_slot_screen"])
    screen = supplement["insight_screen"]
    completed, evaluated, accepted = (load(screen[k]) for k in ("completed","gate","acceptance"))
    require(len(completed["jobs"]) == 68 and Counter(j["kind"] for j in completed["jobs"]) == {"hog":60,"feedback":8}
            and all(j["exit_code"] == 0 for j in completed["jobs"]) and completed["sources_unchanged"]
            and completed["exit_code"] == completed["evaluation_exit_code"] == 0
            and accepted["status"] == "PASS" and accepted["fresh_gate_matches_saved"]
            and evaluated["gate"] == accepted["gate"] and accepted["gate"]["frozen_candidate"] == "DAC2", "sealed68 model gate")
    screen["gate_result"] = accepted["gate"]
    area["n4_subset"] = n4
    area["full9_summary"] = audit["summary"]
    area["table_note"] = "N4 subset, square micrometres; four disjoint bins plus signed summary-minus-leaf rounding residual = whole total_cell_area. Display rounds to 6 decimals (residual 9); exact decimals retained here. Unresolved bin zero in all nine; cell-count semantic residuals remain warnings."
    return supplement, n4


def render(root=ROOT):
    raw = bound_bytes(root, INPUT_PINS)
    supplement, n4_area = existing_records(root, raw)
    load = lambda name: json.loads(raw[name])
    index, analysis = (load(FINAL + "snapshot/" + p) for p in ("index/matrix-coverage.json", "analysis/analysis.json"))
    release = load(FINAL + "release.json")
    adoption = load(E + "parent-continuation-20261027T0325/final498-adoption.json")
    require(adoption["writer_release"]["sha256"] == digest(raw[FINAL + "release.json"])
            and adoption["index"]["sha256"] == digest(raw[FINAL+"snapshot/index/matrix-coverage.json"]), "final adoption/release binding")
    for name in ("snapshot/index/matrix-coverage.json", "snapshot/analysis/analysis.json"):
        require(release["artifacts"][name]["sha256"] == digest(raw[FINAL+name]), "final release input binding")
    rows = index["matrix"]["rows"]
    require(len(rows) == len({r["id"] for r in rows.values()}) == 498
            and all(r["status"] == "PASS" for r in rows.values()), "exact498 accepted identities")
    require(index["matrix"]["completion"]["complete"] is True, "incomplete matrix")
    require(index["matched_power"]["accepted_rows"] == 9, "power ninepairs")
    require(analysis["core_trained_jobs"]["accepted"] == 120
            and analysis["conditional_dac"]["confirmation"]["accepted"] == 20, "confirmation run coverage")
    endpoints = analysis["endpoints"] + analysis["conditional_dac"]["endpoints"]
    confirmation = {}
    for policy in POLICIES:
        for arm in ("A", "B"):
            selected = [r for r in endpoints if r["policy"] == policy and r["profile"] == "trained-"+arm
                        and r["configuration"]["group"] in ("n4-confirmation", "insight-confirmation")]
            confirmation[policy, arm] = cohort(selected, range(529,549))
    require(confirmation["MAIN","A"]["p99"] == 10 and confirmation["MAIN","B"]["p99"] == 21.05
            and confirmation["DAC2","A"]["p99"] == 1.1 and confirmation["DAC2","B"]["p99"] == 12.35,
            "accepted confirmation key-value sanity check")
    fragments = ["% v3 only; generated from pinned accepted evidence. Do not edit.",
                 r"\newcommand{\RevisionMatrixPassed}{"+str(index["matrix"]["completion"]["pass"])+"}",
                 r"\newcommand{\RevisionMatrixPlanned}{"+str(len(rows))+"}"]
    fragments.append(table("RevisionConfirmationTable", "llrrrr", ["Policy", "High:Low", "A P99", "B P99", "A mean", "B mean"],
        [[LABELS.get(p,p), HIGH_LOW.get(p,"--"), number(confirmation[p,"A"]["p99"]), number(confirmation[p,"B"]["p99"]),
          number(confirmation[p,"A"]["wait"],3), number(confirmation[p,"B"]["wait"],3)] for p in POLICIES]))
    for arm in ("A","B"):
        coordinates=" ".join(f"({i},{number(confirmation[p,arm]['p99'])})" for i,p in enumerate(POLICIES,1))
        fragments.append("\\newcommand{\\RevisionPninetyNine"+arm+"}{"+coordinates+"}")
    selected_pairs = [p for p in analysis["comparisons"] + analysis["conditional_dac"]["comparisons"]
                      if p.get("confirmation") is True and p["candidate_configuration"]["group"] in ("n4-confirmation","insight-confirmation")]
    require(len(selected_pairs) == 6, "six selected confirmation comparisons")
    pair_rows = []
    for p in selected_pairs:
        require(p["status"] == "COMPLETE" and p["n"] == 20 and p["seeds"] == list(range(529,549))
                and p["paired_bootstrap"]["replicates"] == 10000 and p["paired_bootstrap"]["rng_seed"] == 20261023,
                "paired confirmation/bootstrap contract")
        lo, hi = p["paired_bootstrap"]["percentile95"]
        pair_rows.append([LABELS.get(p["candidate"],p["candidate"])+" / "+LABELS.get(p["baseline"],p["baseline"]),
                          HIGH_LOW.get(p["candidate"],HIGH_LOW.get(p["baseline"],"--")),
                          p["profile"][-1],number(p["mean_p99_delta_cycles"]),f"[{number(lo)}, {number(hi)}]"])
    fragments.append(table("RevisionPairedCITable","lllrr",["Candidate / baseline","High:Low","Arm",r"$\Delta$ P99",r"95\% CI"],pair_rows))
    ndata = load(N60)
    require(ndata["run_count"] == 60 and ndata["endpoint_count"] == 120 and len(ndata["summaries"]) == 24,
            "full60 report coverage")
    ns = {}
    for n in (8,16):
        for policy in POLICIES[:-1]:
            for arm in ("A","B"):
                chosen=[r for r in endpoints if r["policy"] == policy and r["profile"] == "trained-"+arm
                        and r["configuration"]["group"] == "n-expansion" and r["configuration"]["n_src"] == n]
                stat=cohort(chosen,range(509,514));ns[n,policy,arm]=stat
                report=next(s for s in ndata["summaries"] if (s["n_src"],s["policy"],s["profile"]) == (n,policy,"trained-"+arm))
                require(report["n"] == 5 and report["stages"]["generation_to_fire"]["p99"] == stat["p99"], "full60/index P99 disagreement")
    fragments.append(table("RevisionNExpansionTable","rlrrrr",["N","Policy","A P99","B P99","A mean","B mean"],
        [[n,LABELS.get(p,p),number(ns[n,p,"A"]["p99"]),number(ns[n,p,"B"]["p99"]),
          number(ns[n,p,"A"]["wait"],3),number(ns[n,p,"B"]["wait"],3)] for n in (8,16) for p in POLICIES[:-1]]))
    power = load(POWER)
    cases = power["cases"]
    require(len(cases) == 18 and {(c["policy"],c["seed"],c["arm"]) for c in cases}
            == {(p,s,a) for p in ("fcfs","rr","fai-main") for s in (509,510,511) for a in ("A","B")}, "power18 identities")
    transitive = {}
    def bound_ref(ref):
        path=Path(ref["path"]);path=path if path.is_absolute() else root/path
        blob=path.read_bytes();require(digest(blob)==ref["sha256"],"power raw reference changed")
        transitive[path.relative_to(root).as_posix()] = ref["sha256"]
        return blob
    tokens = dict(internal="Cell Internal",switching="Net Switching",leakage="Cell Leakage",total="Total")
    power_sources = None
    for c in cases:
        metadata=json.loads(bound_ref(c["provenance"]["metadata"]))
        source_map=metadata["source_sha256"]
        require(digest(json.dumps(source_map,sort_keys=True,separators=(",",":")).encode()) == c["source_sha256"], "power source closure binding")
        require(power_sources is None or power_sources == source_map, "power common source closure changed")
        power_sources=source_map
        text=bound_ref(c["provenance"]["power_report"]).decode()
        for component,label in tokens.items():
            match=re.search(re.escape(label)+r"\s+Power\s*=\s*([\d.eE+-]+)",text)
            require(match and match[1]==c["printed_W"][component],"printed raw power token")
        require(c["training_cycles"] == 10000000 and c["measured_cycles"] == (100000 if c["arm"]=="A" else 102400), "power actual windows")
    power_rows=[]
    for policy,label in (("fcfs","FCFS"),("rr","RR10"),("fai-main","FAI-inspired")):
        for arm in ("A","B"):
            chosen=[c for c in cases if (c["policy"],c["arm"]) == (policy,arm)]
            require(sorted(c["seed"] for c in chosen)==[509,510,511],"power3 seeds")
            values=[sum(Decimal(c["printed_W"][k]) for c in chosen)/3*1000 for k in tokens]
            power_rows.append([label,arm,*[number(v,6) for v in values]])
    fragments.append(table("RevisionPowerTable","llrrrr",["Policy","Arm","Internal","Switching","Leakage","Total"],power_rows))
    area = {k:Decimal(v) for k,v in re.findall(r"^(\w+)\s*=\s*([\d.]+)$",raw[PPA+"reports/area_summary.rpt"].decode(),re.M)}
    coverage={k:int(v) for k,v in re.findall(r"^(\w+)\s*=\s*(\d+)$",raw[PPA+"reports/pt_coverage_summary.rpt"].decode(),re.M)}
    slack=lambda name: Decimal(re.search(r"slack \(MET\)\s+([\d.]+)",raw[PPA+"reports/"+name].decode())[1])
    setup,hold=slack("pt_timing_max.rpt"),slack("pt_timing_min.rpt")
    passing=int(re.search(r"(\d+) Passing compare points",raw[PPA+"formal/reports/verify.rpt"].decode())[1])
    require(area["total_cell_area"]==area["combinational_area"]+area["noncombinational_area"] and area["number_of_sequential_cells"]==9014
            and coverage["violated"]==0 and coverage["untested"]==68 and passing==9126 and setup>0 and hold>0,"DAC PPA facts")
    fragments.append(table("RevisionCgofPpaTable","lrrrrrr",["High:Low","Cell area","Registers","Setup ns","Hold ns","Untested","Formal points"],
        [["2:1",number(area["total_cell_area"],6),int(area["number_of_sequential_cells"]),number(setup,6),number(hold,6),coverage["untested"],passing]]))
    fragments.append("% N4 subset of the full nine-case disjoint leaf audit; square micrometres; printed rounding applies.\n"+
        table("RevisionPrimaryAreaTable","lrrrrrr",["N4 policy","Descriptor","Timestamp","Policy logic","Common","Residual","Whole area"],
        [[{"fcfs":"FCFS","rr":"RR10","fai-main":"FAI-inspired"}[c["policy"]],
          *[number(c["categories"][k],6) for k in ("descriptor_storage","timestamp_storage","policy","common")],
          number(c["summary_minus_leaf_area"],9),number(c["whole_cell_area"],6)] for c in n4_area]))
    primary=load("docs/ppa/primary-20261021-v2.json")["cases"]
    over=[];below=[]
    for n in (4,8,16):
        main=Decimal(str(next(c["cell_area"] for c in primary if c["N"]==n and c["policy"]=="fai-main")))
        rr=Decimal(str(next(c["cell_area"] for c in primary if c["N"]==n and c["policy"]=="rr")))
        over.append((main-rr)/rr*100);below.append((main-rr)/main*100)
    for name,value in [("RevisionFaiOverRRMin",min(over)),("RevisionFaiOverRRMax",max(over)),("RevisionRRBelowFaiMin",min(below)),("RevisionRRBelowFaiMax",max(below))]:
        fragments.append("\\newcommand{\\"+name+"}{"+number(value)+"}")
    tex="\n\n".join(fragments)+"\n"
    frozen_power=load(E+"power-parent-review-20261024T0904/sources.json")
    require(len(analysis["endpoints"][0]["source_hashes"])==39
            and len(analysis["conditional_dac"]["endpoints"][0]["source_hashes"])==53
            and len(power_sources)==32 and len(frozen_power)==33
            and all(frozen_power.get(p)==h for p,h in power_sources.items()), "exact source closure sizes/projection")
    anchors=[]
    for path,blob in raw.items():
        if path.endswith(".md"):
            lines=blob.decode().splitlines()
            anchors.append(dict(path=path,sha256=INPUT_PINS[path],headings=[dict(line=i+1,text=s) for i,s in enumerate(lines) if s.startswith('#')],
                                scope='Textual report anchor only; historical pendingapproval wording is superseded by actual user-approvedv3scope, not rewritten here.'))
    manifest=dict(schema="cxl-manuscript-revision-v3-evidence-v1",inputs=INPUT_PINS,existing_record_supplement=supplement,transitive_power_report_hashes=transitive,
        generator=dict(path="docs/final-report/generate_revision_v3.py",sha256=digest(Path(__file__).read_bytes()),python=platform.python_version(),
                       executable=Path(sys.executable).name,dependencies="Python standard library only",runtime_model="Not introspected; no model provenance inferred from comments."),
        output_tex_sha256=digest(tex.encode()),source_closures=dict(core=next(b["core_source_sha256"] for b in index["performance"]["bundles"] if b.get("core_source_sha256")),
        core39=analysis["endpoints"][0]["source_hashes"],dac53=analysis["conditional_dac"]["endpoints"][0]["source_hashes"],
        power_export32=power_sources,power_frozen33=frozen_power,
        hardware_source_revision=load("docs/ppa/primary-20261021-v2.json")["source_commit"]),
        matrix=index["matrix"]["completion"],cohorts=dict(confirmation7policies=14,N_expansion60runs=24,power18captures=6,selected_confirmation_pairs=6),
        historical_results=dict(path="docs/final-report/generated/results.tex",sha256=INPUT_PINS["docs/final-report/generated/results.tex"],
            six_source_anchors={p:INPUT_PINS[p] for p in ("docs/ppa/primary-20261021-v2.json","docs/ppa/algorithm2-n4-20261021.json",
                "docs/ppa/power-20261021.json","docs/ppa/power-supplement-20261021.json","docs/ppa/formality-20261021.json",
                "syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json")}),
        table_contract=dict(RevisionConfirmationTable="7rows; policy, High:Low allocation where applicable, A/B meanrunP99 and mean generation-to-fire cycles;20confirmation seeds529..548",
            RevisionPninetyNineA="PGF coordinates x1..7=FCFS,RR1,RR10,FAI-inspired,Alg2,BLISS,CGOF (2:1); same cohort values as confirmation table",
            RevisionPninetyNineB="Same ordered x1..7; trainedB meanrunP99",
            RevisionPairedCITable="6rows; candidate/baseline, High:Low allocation where applicable, arm and delta;95% pairedseedbootstrap10000 RNG20261023;20seeds",
            RevisionNExpansionTable="12rows; N8/N16 sixpolicies; A/B meanrunP99 and meanwait cycles;5exploration seeds509..513, noCI",
            RevisionPowerTable="6rows; separate A/B arithmeticmean3seeds509..511 in mW, printedPTtokens; noCI",
            RevisionPrimaryAreaTable="3rows N4 subset FCFS/RR10/FAI-inspired; four disjoint bins, signed rounding residual and whole cell area in square micrometres; full9 bound",
            RevisionCgofPpaTable="1row; CGOF (2:1) with High:Low=2:1; N4 prelayoutTT25ns cellarea/registers/setup/hold/untested/own-netlistformalpoints"),
        textual_claim_anchors=anchors,limits=["No policy overallwinner or crossNfixed-demand causality.","Power qualifiedwarnings and prelayout/noSDF scope retained by bound report.","No physicalsignoff or new experiments.","Historical generator/results/manifest are not modified."])
    return tex,manifest


IMPROVEMENT_HANDOFF = "docs/final-report/improvement-20261028/agent-handoff.json"
IMPROVEMENT_HANDOFF_SHA = "95507756077e841330763a4065ffeb19f54a84faa99289f46f2b1aff3177cf18"
MODEL_RAW_DIGESTS = {
    "fixed-class": "ec576b38a2bcc53c2d5337dc24a972938352cd38478ddc90daea9d4ca130af55",
    "finite-heavy": "ba5ed6aae3fdd567f07332909a59a8d129fc1a20720d1a9a2d62232ea0a57a69",
}
IMPROVEMENT_POLICIES = ("FAI-inspired", "CGOF_w1_oldest-first", "CGOF_w2_oldest-first",
                        "WRR_weights2-1-1-1", "IWRR_weights2-1-1-1")
IMPROVEMENT_LABELS = dict(zip(IMPROVEMENT_POLICIES,
    ("FAI-inspired", "CGOF (1:1)", "CGOF (2:1)", "WRR (2:1)", "IWRR (2:1)")))


def canonical_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def effective_classes(states):
    require(all(s in ("H", "B_H", "L", "B_L") for s in states), "unknown Main class")
    return ["High" if s in ("H", "B_H") else "Low" for s in states]


def histogram_p99(histogram):
    hist = {int(k): v for k, v in histogram.items()}
    require(hist and all(k >= 0 and type(v) is int and v > 0 for k, v in hist.items()), "P99 histogram domain")
    rank, cumulative = (99 * sum(hist.values()) + 99) // 100, 0
    for value in sorted(hist):
        cumulative += hist[value]
        if cumulative >= rank:
            return value


def improvement_data(root=ROOT):
    """Read completed evidence only; freeze raw report/job bytes before aggregation."""
    handoff_raw = bound_bytes(root, {IMPROVEMENT_HANDOFF: IMPROVEMENT_HANDOFF_SHA})
    h = json.loads(handoff_raw[IMPROVEMENT_HANDOFF])
    # Manuscript sources are edited concurrently; only evidence and the fixed plan are inputs here.
    pins = {r["path"]: r["sha256"] for r in h["source_files"]
            if r["path"].startswith(("artifacts/", "specs/", "scripts/", "docs/experiments/",
                                   "docs/final-report/improvement-", "docs/final-report/lit-review/"))}
    raw = bound_bytes(root, pins)
    pins[IMPROVEMENT_HANDOFF] = IMPROVEMENT_HANDOFF_SHA
    def read_extra(path):
        blob = (root / path).read_bytes()
        pins[path] = digest(blob)
        return blob
    hardware, extra_ppa = [], {}
    for c in h["evidence"]["cgof_area_sta"]:
        base = c["report_root"] + "/"
        extra = {}
        for name in ("area.rpt", "pt_coverage_summary.rpt", "profile_applied.rpt", "power_status.rpt"):
            extra[name] = read_extra(base + name).decode()
            extra_ppa[base + name] = pins[base + name]
        area = Decimal(re.search(r"^Total cell area:\s*([\d.]+)", extra["area.rpt"], re.M)[1])
        summary_area = Decimal(re.search(r"^total_cell_area\s*=\s*([\d.]+)", raw[base + "area_summary.rpt"].decode(), re.M)[1])
        slacks = [min(Decimal(v) for v in re.findall(r"slack \((?:MET|VIOLATED)\)\s+(-?[\d.]+)",
                   raw[base + name].decode())) for name in ("pt_timing_max.rpt", "pt_timing_min.rpt")]
        require(area == summary_area == Decimal(str(c["area"]))
                and slacks == [Decimal(str(c[k])) for k in ("setup_slack_ns", "hold_slack_ns")], "raw area/STA mismatch")
        require(re.search(r"^violated\s*=\s*0$", extra["pt_coverage_summary.rpt"], re.M)
                and "CLOCK_PERIOD = 25.0 (1ns)" in extra["profile_applied.rpt"]
                and "operating_conditions = tt0p78v25c" in extra["profile_applied.rpt"]
                and "POWER_STATUS: NOT_RUN" in extra["power_status.rpt"], "hardware conditions/coverage")
        hardware.append(dict(c, area=str(area), setup_slack_ns=str(slacks[0]), hold_slack_ns=str(slacks[1]),
            untested_checks=int(re.search(r"^untested\s*=\s*(\d+)", extra["pt_coverage_summary.rpt"], re.M)[1])))
    require(canonical_digest(extra_ppa) == "91cc80fc442626e4271f0027b958ead8efed37baa9e38f4a034cae8e3b012e72", "raw hardware binding")
    model, fixed, finite, source_closures = {}, [], [], {}
    for c in h["evidence"]["model_cohorts"]:
        s = json.loads(raw[c["summary"]])
        base = Path(c["summary"]).parent
        m = json.loads(raw[(base / "manifest.json").as_posix()])
        require(s["manifest_sha256"] == m["manifest_sha256"] == c["manifest_digest"]
                and canonical_digest({k:v for k,v in m.items() if k != "manifest_sha256"}) == m["manifest_sha256"], "model manifest binding")
        require(s["overall_status"] == "PASS" and s["scope"] == "MODEL_ONLY" and s["source_stable"]
                and s["jobs_completed"] == s["jobs_expected"] == c["jobs"]
                and s["seeds"] == c["seeds"] == list(range(6201, 6221)), "model cohort completeness")
        model[c["id"]] = dict(summary=c["summary"], settings=s["settings"], profiles=s["profiles"], jobs=c["jobs"], seeds=c["seeds"])
        source_closures[c["id"]] = m["source_hashes"]
        if c["id"] == "equal-demand":
            continue
        raw_pins = {}
        for p in sorted((root / base / "jobs").glob("*/result.json")):
            with p.open("rb") as stream:
                value = hashlib.file_digest(stream, "sha256").hexdigest()
            raw_pins[p.relative_to(root / base).as_posix()] = value
            pins[p.relative_to(root).as_posix()] = value
        require(len(raw_pins) == c["jobs"] and canonical_digest(raw_pins) == MODEL_RAW_DIGESTS[c["id"]], "raw model job binding")
        for policy in IMPROVEMENT_POLICIES[:3] if c["id"] == "fixed-class" else IMPROVEMENT_POLICIES:
            selected = [r for r in s["runs"] if r["config_id"] == policy and r["profile"] == ("equal" if c["id"] == "fixed-class" else "over")]
            require(sorted(r["seed"] for r in selected) == c["seeds"], "selected model seeds")
            shares, values = [], []
            for row in selected:
                job = next(j for j in m["jobs"] if j["id"] == row["id"])
                path = next(p for p in raw_pins if p.endswith("-" + row["id"] + "/result.json"))
                payload = json.loads((root / base / path).read_bytes())
                result = payload["result"]
                require(payload["job"] == job and payload["status"] == result["status"] == row["status"] == "PASS"
                        and payload["endpoint_metrics"] == row["endpoints"] and result["scope"] == "MODEL_ONLY", "model identity/endpoint binding")
                mix, iso = result["mixed"], result["isolated"]
                require(all(lane["conservation"]["final_generated_eq_accepted_eq_fired"] for lane in (mix, iso)), "model conservation")
                require(mix["active_cycles"] < s["settings"]["window"] and not mix["classifier_trajectory"], "model pre-boundary scope")
                if c["id"] == "fixed-class":
                    require(result["initial_classes"] == ["L", "H", "H", "H"] and mix["active_cycles"] == 20000, "fixed-class horizon")
                    counts = mix["phase_metrics"]["active"]["fired"]
                    share = [v / sum(counts) for v in counts]
                    require(share == [mix["active_service_shares"][str(i)] for i in range(4)], "measurement service shares")
                    shares.append(share)
                else:
                    if policy in IMPROVEMENT_POLICIES[:3]:
                        require(mix["class_changes"] == [{"classes": ["H"] * 4, "cycle": 0}], "model initial all-High scope")
                    histogram = Counter()
                    for cohort_row in mix["cohorts"].values():
                        for source in cohort_row["stages_by_source"][1:]:
                            histogram.update(source["generation_to_fire"]["histogram"])
                    endpoints = row["endpoints"]
                    p99 = histogram_p99(histogram)
                    gap = mix["heavy"]["gaps"]["samples"]["inter_service"]["wall_cycles"]["max"]
                    ratio = (mix["cut_cycle"] + 1) / (iso["cut_cycle"] + 1)
                    require(p99 == endpoints["sparse_completed_generation_to_fire_p99"]
                            and gap == endpoints["heavy_max_service_gap"]
                            and ratio == endpoints["heavy_completion_ratio_mixed_over_isolated"], "raw model metric mismatch")
                    values.append(dict(seed=row["seed"], sparse_p99=p99, heavy_max_gap=gap, completion_ratio=ratio,
                        active_cycles=mix["active_cycles"], classifier_boundaries=len(mix["classifier_trajectory"]),
                        sparse_censored_at_cut=endpoints["sparse_censored_at_cut"], job_id=row["id"]))
            if shares:
                require(all(v == shares[0] for v in shares), "fixed-class deterministic shares")
                fixed.append(dict(config_id=policy, policy=IMPROVEMENT_LABELS[policy], shares=shares[0], n=20,
                                  config=job["config"], measurement_cycles=20000))
            else:
                finite.append(dict(config_id=policy, policy=IMPROVEMENT_LABELS[policy], config=job["config"], n=20,
                    **{k:mean(v[k] for v in values) for k in ("sparse_p99", "heavy_max_gap", "completion_ratio")}, runs=values))
        if c["id"] == "finite-heavy":
            metrics = ("sparse_completed_generation_to_fire_p99", "heavy_max_service_gap", "heavy_completion_ratio_mixed_over_isolated")
            model[c["id"]]["overload_paired_contrasts"] = [dict(r, metrics={k:v for k,v in r["metrics"].items() if k in metrics})
                                                          for r in s["comparisons"] if r["profile"] == "over"]
    rtl, common = [], []
    for group in h["evidence"]["production_rtl"]:
        require(json.loads(raw[group["summary"]])["overall"] == "PASS", "RTL summary failed")
        records = [json.loads(raw[p]) for p in group["result_files"]]
        for p, r in zip(group["result_files"], records):
            job = r["job"]
            require(r["evidence_kind"] == "SCHEDULER_RTL" and job["seed"] == 6201
                    and (job["n_src"], job["depth"], job["window"]) == (4, 16, 5000000)
                    and sum(r["generated"]) == r["accepted"] == r["fired"], "RTL scope/conservation")
            mode = job["mode"]
            cohort_row = r["metrics"]["cohorts"][mode]
            if mode == "common-demand":
                states = [b["classes"] for b in r["classifier"]]
                require(states == [["B_H", "B_H", "B_H", "H"], ["H"] * 4, ["H"] * 4], "common-demand boundary trace")
                common.append(dict(policy=f"CGOF ({job['high_weight']}:1)", encoded_boundaries=states,
                    effective_boundaries=[effective_classes(s) for s in states],
                    measurement_fires=cohort_row["completed_by_phase"]["measurement"],
                    producer_backlog_limit=r["trace_config"]["producer_backlog_limit"], generated=sum(r["generated"]),
                    per_source_gf_p99=[x["generation_to_fire"]["p99"] for x in cohort_row["per_source"]], source=p))
            elif job["lane"] == "mixed":
                states = [b["classes"] for b in r["classifier"]]
                require(states == [["B_H", "H", "H", "H"]], "finite RTL boundary scope")
                isolated = next(x for x in records if x["job"]["high_weight"] == job["high_weight"] and x["job"]["lane"] == "isolated")
                sparse = cohort_row["pooled_sparse"]["generation_to_fire"]
                require(histogram_p99(sparse["histogram"]) == sparse["p99"], "RTL Sparse P99")
                rtl.append(dict(policy=f"CGOF ({job['high_weight']}:1)", sparse_p99=sparse["p99"],
                    heavy_max_gap=r["heavy"]["max_wall_gap"], isolated_heavy_max_gap=isolated["heavy"]["max_wall_gap"],
                    mixed_active_cycles=r["active_cycles"], isolated_active_cycles=isolated["active_cycles"],
                    encoded_boundaries=states, effective_boundaries=[effective_classes(s) for s in states],
                    completion_ratio=r["active_cycles"] / isolated["active_cycles"], job=job, source=p))
    return dict(hardware=hardware, fixed_class=fixed, finite_heavy=finite, production_rtl=rtl,
                common_demand_rtl=common, model_cohorts=model, inputs=pins, source_closures=source_closures)


def render_improvement(root=ROOT):
    d = improvement_data(root)
    fragments = ["% Generated from completed, hash-bound October 28 evidence; no new experiment.",
        "% MODEL_ONLY P99 is mean per-run pooled-Sparse G-to-F P99, including completed cleanup requests.",
        "% MODEL_ONLY Heavy gap is mean per-run maximum uncensored FIFO-nonempty inter-service wall-cycle gap.",
        "% W5M is configured; the short model controls end BEFORE the first classification boundary.",
        table("ImprovementCgofHardwareTable", "lrrrr", ["Policy", "N", "Cell area", "Setup (ns)", "Hold (ns)"],
            [[r["policy"], r["n"], number(r["area"], 6), number(r["setup_slack_ns"], 6), number(r["hold_slack_ns"], 6)] for r in d["hardware"]]),
        table("ImprovementFixedClassTable", "lrrrr", ["Policy", r"Low 0 (\%)", r"High 1 (\%)", r"High 2 (\%)", r"High 3 (\%)"],
            [[r["policy"], *[number(100 * v, 4) for v in r["shares"]]] for r in d["fixed_class"]]),
        table("ImprovementFiniteHeavyModelTable", "lrrr", ["Policy", "Sparse P99", "Heavy max gap", "Completion ratio"],
            [[r["policy"], number(r["sparse_p99"]), number(r["heavy_max_gap"]), number(r["completion_ratio"], 7)] for r in d["finite_heavy"]]),
        "% Production RTL: near profile, seed 6201, Heavy work 5,000,000; one B_H/H/H/H boundary, all effective High.",
        table("ImprovementProductionRtlTable", "lrrr", ["Policy", "Sparse P99", "Heavy max gap", "Completion ratio"],
            [[r["policy"], r["sparse_p99"], r["heavy_max_gap"], number(r["completion_ratio"], 8)] for r in d["production_rtl"]])]
    tex = "\n\n".join(fragments) + "\n"
    manifest = dict(schema="cxl-improvement-evidence-v1", **d, output_tex_sha256=digest(tex.encode()),
        generator=dict(path="docs/final-report/generate_revision_v3.py", sha256=digest(Path(__file__).read_bytes())),
        limits=["MODEL_ONLY fixed-class uses 20,000-cycle measurement counts, excludes drain.",
                "Fixed L/H/H/H map is initialized and observed before any W5M classification boundary.",
                "MODEL_ONLY overload: Heavy work 20,000; N4/D16/W5M; 20 seeds 6201..6220.",
                "W5M is the configured threshold, not elapsed training. Class-aware finite models remain initial all High.",
                "Sparse P99 pools sources 1..3 within a run, includes completed cleanup requests, then averages run P99s.",
                "Heavy gap is active FIFO-nonempty inter-service wall cycles: excludes initial, empty-terminated and censored gaps; includes sink stalls.",
                "Heavy gap aggregation is mean of per-run maxima, unlike old RTL reanalysis maximum of run maxima.",
                "Completion ratio uses inclusive active duration (mixed cut+1)/(isolated cut+1), not application slowdown.",
                "Production RTL finite Heavy: near profile, work 5,000,000; one seed 6201.",
                "Finite RTL has one B_H/H/H/H boundary, still all effective High; its workload differs from the overload model.",
                "Common-demand B_H preserves effective High; no effective demotion at recorded boundaries.",
                "Common-demand RTL uses bounded producers (256/source): generated demand is acceptance-throttled, not unbounded offered traffic.",
                "Fixed-horizon endpoint active-rate fields mix drain numerators with active denominators and are excluded.",
                "Hardware is pre-layout cell area and STA at TT/25ns; power NOT_RUN; untested timing checks retained.",
                "H1-H5 remain future experiments; no new simulations or EDA executed."])
    return tex, manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir",type=Path,default=Path(__file__).parent/"generated")
    parser.add_argument("--improvement-only", action="store_true", help="Write October 28 additions without regenerating historical outputs")
    args=parser.parse_args(argv)
    tex,manifest=render_improvement() if args.improvement_only else render()
    prefix = "improvement" if args.improvement_only else "revision_v3"
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/(prefix+"_results.tex")).write_text(tex,encoding="utf-8",newline="\n")
    (args.out_dir/(prefix+"_evidence_manifest.json")).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(dict(output=str(args.out_dir),tex_sha256=digest(tex.encode()),input_count=len(manifest["inputs"]))))


if __name__=="__main__":main()
