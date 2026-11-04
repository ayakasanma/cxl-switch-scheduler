"""Six current-RTL/original-netlist Formality bridges; private inputs stay local."""

import argparse
import ast
import base64
import datetime
import hashlib
import hmac
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / ".setup-logs/implementation/revision-20261023/bridges"
HELPERS = ROOT / ".setup-logs/FastX-NN"
PRIMARY = "759f86b24f13ed5984c19034eeeea2ca43b0e971"
CURRENT = "c8e7ea8c0e4530572b3abf5b14ea9958e24f1789"
PROFILE = "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d"
LIBRARY = "844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094"
CASES = [(p, n) for n in (4, 8, 16) for p in ("fcfs", "rr")]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def linux(path):
    path = Path(path).resolve()
    require(path.drive.lower() == "c:", "WSL bridge requires the existing C: workspace")
    return "/mnt/c/" + path.as_posix()[3:]


def restore_pin(config, folder):
    require(config["host_key_state"] == "USER_CONFIRMED_AND_PINNED", "host key is not pinned")
    approved = set(re.findall(r"SHA256:[A-Za-z0-9+/]+", config["host_key_observed"]))
    require(len(approved) == 1, "ambiguous approved fingerprint")
    hosts = {config["host"], f"[{config['host']}]:{config['port']}"}
    matches = []
    for line in (HELPERS / "known_hosts").read_text().splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[1] != "ssh-ed25519":
            continue
        host, algorithm, key = fields[:3]
        key_bytes = base64.b64decode(key, validate=True)
        fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(key_bytes).digest()).decode().rstrip("=")
        host_match = any(name in hosts for name in host.split(","))
        if host.startswith("|1|"):
            _, _, salt, mac = host.split("|")
            host_match = any(hmac.compare_digest(
                hmac.new(base64.b64decode(salt), name.encode(), hashlib.sha1).digest(),
                base64.b64decode(mac)) for name in hosts)
        if fingerprint in approved and host_match:
            matches.append((line, fingerprint, algorithm))
    require(len(matches) == 1, "no unique archived approved host/key match")
    line, fingerprint, algorithm = matches[0]
    target = folder / "known_hosts"
    with target.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(line + "\n")
    write_json(folder / "trust-recovery.json", {
        "source": ".setup-logs/FastX-NN/known_hosts",
        "approved_state": config["host_key_state"], "approved_fingerprint": fingerprint,
        "algorithm": algorithm, "configured_host_match": True,
        "archived_line_preserved": target.read_text().rstrip("\n") == line,
        "source_file_sha256": digest((HELPERS / "known_hosts").read_bytes()),
        "task_local_file_sha256": digest(target.read_bytes()),
        "network_key_scan": False, "global_or_private_configuration_modified": False})
    return target


def pinned_ssh(config, folder):
    require(config["host_key_state"] == "USER_CONFIRMED_AND_PINNED", "host key is not pinned")
    # Reuse the exact reviewed SSH options without executing the helper's writes.
    tree = ast.parse((HELPERS / "remote.py").read_text(encoding="utf-8-sig"))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "ssh" for t in n.targets))
    ssh = eval(compile(ast.Expression(assignment.value), "<reviewed SSH options>", "eval"),
               {"__builtins__": {}, "config": config, "str": str})
    indices = [i for i, value in enumerate(ssh) if value.startswith("UserKnownHostsFile=")]
    require(len(indices) == 1 and "StrictHostKeyChecking=yes" in ssh, "reviewed SSH options changed")
    # OpenSSH parses -o values as config text, including paths containing spaces.
    known_hosts = linux(restore_pin(config, folder))
    require('"' not in known_hosts and "\n" not in known_hosts, "unsafe task-local trust path")
    ssh[indices[0]] = 'UserKnownHostsFile="' + known_hosts + '"'
    return ssh


def transport(folder, ssh, label, command, stdin=None, binary=False):
    request = folder / (label + ".request.json")
    source = None
    if stdin is not None:
        source = folder / (label + ".stdin")
        source.write_bytes(stdin)
    write_json(request, {"argv": ssh + [command], "stdin_path": linux(source) if source else None})
    stdout = folder / (label + (".tar" if binary else ".stdout.log"))
    stderr = folder / (label + ".stderr.log")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    argv = ["wsl.exe", "-d", "Ubuntu", "--exec", "python3",
            linux(HELPERS / "ssh_exec.py"), linux(request)]
    with stdout.open("wb") as out, stderr.open("wb") as err:
        code = subprocess.run(argv, stdout=out, stderr=err).returncode
    write_json(folder / (label + ".exit.json"), {
        "outer_exit": code, "started_utc": started,
        "ended_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return code, stdout


def connection_failure(folder, label):
    text = (folder / (label + ".stderr.log")).read_text(errors="replace")
    if "Host key verification failed" in text:
        return "strict pinned host-key verification failed"
    if "Permission denied" in text:
        return "pinned SSH authentication failed"
    return "SSH/WSL transport failed; inspect preserved private logs"


def template():
    source = ROOT / "artifacts/fastx/formality-current-main-bridge/reports/equiv.tcl"
    text = source.read_text()
    old = "$PARAM_N_SRC ni {8 16} || $PARAM_POLICY != 2"
    require(text.count(old) == 1, "audited bridge template changed")
    text = text.replace(old, "$PARAM_N_SRC != $::env(CXL_FM_N) || "
                        "$PARAM_POLICY != $::env(CXL_FM_POLICY)")
    marker = " redirect reports/unmatched.rpt {report_unmatched_points}"
    require(text.count(marker) == 1, "missing match diagnostic insertion point")
    return text.replace(marker, " redirect reports/undriven-after-match.rpt "
                        "{report_undriven_nets}\n" + marker)


CHECKER = """import hashlib,json,pathlib,sys
expected=json.loads(pathlib.Path(sys.argv[1]).read_text())
actual={}
for key,item in expected.items():
 p=pathlib.Path(item['path'])
 if not p.is_file(): raise RuntimeError('missing input: '+key)
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 if h!=item['sha256']: raise RuntimeError('input hash mismatch: '+key)
 actual[key]=h
print(json.dumps(actual,sort_keys=True,indent=2))
"""


def upload_text(path, data):
    encoded = base64.b64encode(data).decode("ascii")
    return ("mkdir -p -- " + shlex.quote(str(PurePosixPath(path).parent)) + "\n"
            "printf %s " + shlex.quote(encoded) + " | base64 -d > " + shlex.quote(path) + "\n")


def prepare(folder, config, run_id):
    formal = json.loads((ROOT / "docs/ppa/formality-20261021.json").read_text())
    supplement = json.loads((ROOT / "docs/ppa/algorithm2-n4-20261021.json").read_text())
    require(supplement["source_commit"] == CURRENT, "unexpected supplementary reference")
    reference = {name: (ROOT / name).read_bytes() for name in supplement["source_hashes"]}
    for name, data in reference.items():
        require(digest(data) == supplement["source_hashes"][name], "current RTL differs: " + name)
    remote_root = config["remote_work_root"].rstrip("/") + "/experiments/" + run_id
    require(".." not in PurePosixPath(remote_root).parts, "invalid scratch path")
    shell = "set -euo pipefail\numask 077\nmkdir -- " + shlex.quote(remote_root) + "\n"
    shell += "cd -- " + shlex.quote(remote_root) + "\nmkdir reports\n"
    for name, data in reference.items():
        shell += upload_text("reference/" + name, data)
    tcl = template().encode()
    shell += upload_text("equiv.tcl", tcl)
    shell += upload_text("source-check.py", CHECKER.encode())
    case_inputs = {}
    provenance = {
        "schema": "cxl-revision-bridges-v1", "reference_revision": CURRENT,
        "mapped_revision": PRIMARY, "profile_sha256": PROFILE, "library_sha256": LIBRARY,
        "reference_hashes": {n: digest(d) for n, d in reference.items()},
        "reference_git_blobs_verified": True, "template_sha256": digest(tcl),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "cases": {},
    }
    for name, data in reference.items():
        blob = subprocess.check_output(["git", "show", CURRENT + ":" + name], cwd=ROOT)
        require(data == blob, "reference differs from recorded Git revision: " + name)
    for policy, n in CASES:
        label = f"{policy}-n{n}"
        old = next(c for c in formal["cases"] if c["group"] == "primary9"
                   and c["policy"] == policy and c["n_src"] == n)
        accepted = ROOT / "artifacts/fastx" / ("primary-20261021-v2-" + label)
        manifest = json.loads((accepted / "manifest.json").read_text())
        require(manifest["source"]["head"] == PRIMARY and manifest["source"]["worktree_clean"],
                "unaccepted mapped source")
        before = ROOT / old["evidence_directory"] / "source-before.sha256"
        remote_hashes = dict(line.split("  ", 1) for line in before.read_text().splitlines())
        bases = [str(PurePosixPath(path).parent) for path in remote_hashes.values()
                 if path.endswith("/manifest.json")]
        require(len(bases) == 1, "ambiguous accepted remote case")
        base = bases[0]
        require(base.startswith(config["remote_work_root"].rstrip("/") + "/"),
                "accepted case outside configured work root")
        require(manifest["target_library"]["remote_path"] == config["target_library"],
                "configured library differs from accepted input")
        expected = {}
        prefix = f"primary-20261021-v2-{label}/{manifest['run_name']}/"
        for path, sha in old["source_sha256"].items():
            if path.startswith(prefix):
                rel = path[len(prefix):]
                expected["mapped/" + rel] = {"path": base + "/" + rel, "sha256": sha}
                local = accepted / rel
                if local.exists():
                    require(digest(local.read_bytes()) == sha, "local mapped input mismatch: " + rel)
        for rel, sha in manifest["file_sha256"].items():
            expected["mapped/" + rel] = {"path": base + "/" + rel, "sha256": sha}
        for rel, sha in old["reference_rtl_sha256"].items():
            require(digest(subprocess.check_output(["git", "show", PRIMARY + ":" + rel],
                                                   cwd=ROOT)) == sha, "old RTL Git mismatch")
        for name, data in reference.items():
            expected["reference/" + name] = {
                "path": remote_root + "/reference/" + name, "sha256": digest(data)}
        expected["library"] = {"path": config["target_library"], "sha256": LIBRARY}
        expected["tooling/equiv.tcl"] = {"path": remote_root + "/equiv.tcl", "sha256": digest(tcl)}
        expected["tooling/source-check.py"] = {
            "path": remote_root + "/source-check.py", "sha256": digest(CHECKER.encode())}
        case_inputs[label] = (base, expected)
        shell += upload_text(label + ".json", (json.dumps(expected) + "\n").encode())
        provenance["cases"][label] = {
            "policy": policy, "n_src": n, "expected_compare_points": old["passing_compare_points"],
            "expected_registers": old["passing_nonconstant_registers"]
            + old["constant_registers_not_compared"],
            "expected_hashes": {key: value["sha256"] for key, value in expected.items()},
            "mapped_netlist_sha256": expected["mapped/output/switch_top.syn.v"]["sha256"],
        }
    shell += "module load " + shlex.quote(config["module"]) + "\n"
    shell += "command -v fm_shell > reports/tool-path.txt\n"
    shell += "test -x /usr/bin/timeout\n"
    for label in case_inputs:
        shell += f"python3 source-check.py {label}.json > reports/preflight-{label}.json\n"
    license_tcl = ('read_db -i $::env(CXL_LIBRARY)\n'
                   'puts "CXL_LICENSE_PREFLIGHT_COMPLETED"\nexit 0\n')
    shell += upload_text("license.tcl", license_tcl.encode())
    shell += "export CXL_LIBRARY=" + shlex.quote(config["target_library"]) + "\n"
    shell += ("set +e\n/usr/bin/timeout 15m fm_shell -f license.tcl > reports/license.log 2>&1\n"
              "code=$?\nset -e\nprintf 'fm=%s\\n' \"$code\" > reports/license-exits.txt\n"
              "test \"$code\" -eq 0\n"
              "! grep -E '^[[:space:]]*(Error|Fatal):|CXL_FM_ERROR:' reports/license.log\n"
              "grep -q CXL_LICENSE_PREFLIGHT_COMPLETED reports/license.log\n"
              "date -u +%FT%TZ > reports/preflight-completed.txt\n")
    (folder / "preflight.sh").write_bytes(shell.encode())
    write_json(folder / "provenance.json", provenance)
    return remote_root, case_inputs, provenance


def case_shell(remote_root, label, base, policy, n, module):
    q = shlex.quote
    return ("set -euo pipefail\numask 077\nmodule load " + q(module) + "\n"
            "root=" + q(remote_root) + "\ncd \"$root\"\n"
            f"mkdir reports/{label}\nmkdir {label}\ncd {label}\nmkdir reports\n"
            f"trap 'wrapper=$?; printf \"outer=%s\\n\" \"$wrapper\" > reports/wrapper-exit.txt; "
            f"cp -a reports/. ../reports/{label}/; exit \"$wrapper\"' EXIT\n"
            "export CXL_FM_ACCEPTED=" + q(base) + "\n"
            "export CXL_FM_REFERENCE_ROOT=\"$root/reference\"\n"
            f"export CXL_FM_N={n} CXL_FM_POLICY={policy}\n"
            f"python3 ../source-check.py ../{label}.json > reports/source-before.json\n"
            "date -u +%FT%TZ > reports/start-utc.txt\nset +e\n"
            "/usr/bin/timeout 15m fm_shell -f ../equiv.tcl > reports/fm.log 2>&1\n"
            "code=$?\nset -e\nprintf 'fm=%s\\n' \"$code\" > reports/exits.txt\n"
            "date -u +%FT%TZ > reports/end-utc.txt\n"
            f"python3 ../source-check.py ../{label}.json > reports/source-after.json\n"
            "test \"$code\" -eq 0\n")


def extract_reports(archive, target):
    with tarfile.open(archive, "r:") as tar:
        members = tar.getmembers()
        require(sum(m.size for m in members) <= 128 * 1024 * 1024, "oversize report archive")
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts
                    and path.parts[0] == "reports", "unsafe report member")
            require(member.isdir() or member.isfile(), "report archive contains link/device")
            if member.isdir():
                continue
            require(path.suffix in {".json", ".rpt", ".log", ".txt"}, "unapproved report type")
            require(str(path) not in seen, "duplicate report member")
            seen.add(str(path))
            dest = target.joinpath(*path.parts)
            require(dest.resolve().is_relative_to(target.resolve()), "report escaped output")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(tar.extractfile(member).read())


def audit_case(reports, expected):
    read = lambda name: (reports / name).read_text(errors="strict")
    require(read("exits.txt").strip() == "fm=0", "nonzero Formality/timeout exit")
    require(json.loads(read("source-before.json")) == expected["expected_hashes"],
            "before hashes do not match reviewed inputs")
    require(read("source-before.json") == read("source-after.json"), "inputs changed during proof")
    require(read("result.txt").splitlines()
            == ["verify_return=1", "NO_USER_CONSTANTS_NO_COMPARE_POINT_EXCLUSIONS"],
            "verification did not return true")
    texts = "\n".join(p.read_text() for p in reports.iterdir()
                      if p.suffix in {".rpt", ".log"})
    require(not re.search(r"^\s*(?:Error|ERROR|Fatal|FATAL)\s*:|^CXL_FM_ERROR:", texts, re.M),
            "tool error in reports")
    require("CXL_FM_COMMANDS_COMPLETED_REVIEW_REQUIRED" in read("fm.log"), "missing completion marker")
    status = read("status.rpt")
    require("Verification SUCCEEDED" in status and "Verification SUCCEEDED" in read("verify.rpt"),
            "verification unsuccessful")
    row = re.search(r"^Passing \(equivalent\)\s+([\d\s]+)$", status, re.M)
    require(row is not None, "missing passing point accounting")
    counts = list(map(int, row[1].split()))
    require(len(counts) == 8, "unexpected passing point columns")
    bbpin, loop, bbnet, cut, ports, dff, latch, total = counts
    require(bbpin == loop == bbnet == cut == latch == 0, "nonstandard compare points")
    n = expected["n_src"]
    require(ports == n + 106 + n.bit_length() - 1 and total == ports + dff
            and total == expected["expected_compare_points"], "missing/extra compare points")
    row = re.search(r"^Failing \(not equivalent\)\s+([\d\s]+)$", status, re.M)
    require(row is not None and list(map(int, row[1].split())) == [0] * 8, "failing points")
    for name, marker in [("failing.rpt", "No failing compare points."),
                         ("aborted.rpt", "No aborted compare points."),
                         ("unverified.rpt", "No unverified compare points."),
                         ("unmatched.rpt", "No unmatched points.")]:
        require(marker in read(name), name + " is not empty")
    require("Don't verify points:   None" in read("dont-verify.rpt"), "excluded points")
    require(re.search(r"User Defined Constants:\s+None", read("constants.rpt")), "user constants")
    setup = read("setup.rpt")
    for setting, value in [("synopsys_auto_setup", "false"),
                           ("verification_set_undriven_signals", "binary:X"),
                           ("verification_verify_directly_undriven_output", "true")]:
        require(re.search(setting + r'\s*=\s*"' + re.escape(value) + '"', setup), "unsafe setup")
    stats = read("setup-status.rpt")
    for name in ["Black boxes", "Multiply-driven nets"]:
        require(re.search(re.escape(name) + r":\s+0\(0\)", stats), name)
    commands = re.findall(r"^\s*((?:set_|change_|create_|connect_|disconnect_|invert_|remove_|rewire_)\w+)"
                          r"\s*:\s+(\d+)\s+(\d+)\s*$", stats, re.M)
    required_commands = set("""set_black_box set_clock set_compare_rule set_constant
        set_constraint set_cutpoint set_dont_cut set_dont_match_points set_dont_verify_points
        set_factor_point set_input_value_range set_inv_push set_user_match set_verify_points
        change_link create_design create_cell create_net create_port create_primitive
        connect_net disconnect_net invert_pin remove_cell remove_net remove_port
        rewire_connection set_dont_reverse""".split())
    require({name for name, _, _ in commands} >= required_commands
            and all(a == b == "0" for _, a, b in commands),
            "user setup overrides or incomplete setup report")
    require("No 'black boxes' matched specified 'designID_list'" in read("black-boxes.rpt"),
            "active black boxes")
    require(re.search(r"^0 Undriven nets:$", read("undriven-after-match.rpt"), re.M),
            "postmatch undriven nets")
    regs = re.search(r"Registers:\s+(\d+)\((\d+)\)", stats)
    constant = re.search(r"Constant reg\s+(\d+)\s+0\s+\d+", status)
    constants = int(constant[1]) if constant else 0
    require(regs and int(regs[1]) == int(regs[2]) == dff + constants
            == expected["expected_registers"], "registers missing from comparison")
    policy = 0 if expected["policy"] == "fcfs" else 1
    require(f"r:/WORK/switch_top_N_SRC{n}_POLICY{policy}_RR_QUANTUM10_FAI_W5000000"
            in status, "wrong reference parameters")
    guidance = read("guidance.rpt")
    require("Guidance Summary" in guidance and "Total" in guidance, "missing SVF guidance report")
    return {"status": "PASS", "passing_compare_points": total, "passing_output_ports": ports,
            "passing_registers": dff, "constant_registers": constants,
            "postmatch_undriven_nets": 0,
            "report_sha256": {p.name: digest(p.read_bytes()) for p in sorted(reports.iterdir())
                              if p.is_file()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run pinned SSH preflight and six proofs")
    args = parser.parse_args()
    require(args.execute, "explicit --execute is required")
    run_id = "revision-bridges-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = LOGS / run_id
    folder.mkdir(parents=True, exist_ok=False)
    result = {"run_id": run_id, "status": "PREPARING", "cases": {}}
    target = ROOT / "artifacts/fastx" / run_id
    try:
        config = json.loads((HELPERS / "connection.local.json").read_text())
        ssh = pinned_ssh(config, folder)
        remote, cases, provenance = prepare(folder, config, run_id)
        # A failed connection ends execution immediately; there is no fallback or retry.
        code, _ = transport(folder, ssh, "preflight", "bash -l -s",
                            (folder / "preflight.sh").read_bytes())
        require(code == 0, f"preflight outer exit {code}: " + connection_failure(folder, "preflight"))
        result["preflight"] = "PASS"
        for policy, n in CASES:
            label = f"{policy}-n{n}"
            shell = case_shell(remote, label, cases[label][0], 0 if policy == "fcfs" else 1,
                               n, config["module"]).encode()
            code, _ = transport(folder, ssh, label, "bash -l -s", shell)
            result["cases"][label] = {"outer_exit": code, "status": "AWAITING_AUDIT"}
            write_json(folder / "result.json", result)
            require(code == 0, f"{label} outer exit {code}; remaining cases stopped")
            print(label + " tool wrapper completed", flush=True)
        result["status"] = "AWAITING_INDEPENDENT_AUDIT"
    except (ValueError, OSError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        result["status"] = "BLOCKED"
        result["blocker"] = str(error)
    # Fetch only after a successful preflight; never retry failed authentication.
    failed_connection = any(entry["outer_exit"] == 255 for entry in result["cases"].values())
    if result.get("preflight") == "PASS" and not failed_connection:
        hash_reports = ("import pathlib,hashlib,json; "
                        "b=pathlib.Path('reports'); "
                        "d={str(p.relative_to(b)):hashlib.sha256(p.read_bytes()).hexdigest() "
                        "for p in sorted(b.rglob('*')) if p.is_file() "
                        "and p.name!='report-hashes.json'}; "
                        "(b/'report-hashes.json').write_text(json.dumps(d,sort_keys=True))")
        command = ("cd " + shlex.quote(remote) + " && python3 -c " + shlex.quote(hash_reports)
                   + " && tar -cf - reports")
        code, archive = transport(folder, ssh, "fetch", command, binary=True)
        result["fetch_outer_exit"] = code
        if code == 0:
            try:
                target.mkdir(parents=True, exist_ok=False)
                extract_reports(archive, target)
                remote_hashes = json.loads((target / "reports/report-hashes.json").read_text())
                local_hashes = {str(p.relative_to(target / "reports")).replace("\\", "/"):
                                digest(p.read_bytes()) for p in (target / "reports").rglob("*")
                                if p.is_file() and p.name != "report-hashes.json"}
                require(local_hashes == remote_hashes, "transferred reports differ from remote hashes")
                for label, entry in result["cases"].items():
                    require(entry["outer_exit"] == 0, label + " outer exit not zero")
                    require((target / "reports" / label / "wrapper-exit.txt").read_text().strip()
                            == "outer=0", label + " remote wrapper exit not zero")
                    entry.update(audit_case(target / "reports" / label, provenance["cases"][label]))
                require(len(result["cases"]) == 6, "six proofs not completed")
                for name, sha in provenance["reference_hashes"].items():
                    require(digest((ROOT / name).read_bytes()) == sha, "local reference changed: " + name)
                require(result["status"] == "AWAITING_INDEPENDENT_AUDIT", "earlier execution failed")
                result["status"] = "PASS"
                write_json(target / "provenance.json", provenance)
            except (ValueError, OSError, tarfile.TarError) as error:
                result["status"] = "BLOCKED"
                result["blocker"] = str(error)
        else:
            result["status"] = "BLOCKED"
            result["blocker"] = "report fetch failed; inspect preserved private logs"
    write_json(folder / "result.json", result)
    if target.exists():
        write_json(target / "result.json", result)
    print(json.dumps({"status": result["status"], "run_id": run_id,
                      "evidence": str(folder.relative_to(ROOT)), "blocker": result.get("blocker")}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
