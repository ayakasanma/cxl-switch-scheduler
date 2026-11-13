"""Real local simulator checks of the CGOF adapter in the common power testbench.

Local W256 fixture replays and header-only guards; no SAIF, gate netlist, PT or power evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_power_replay as checker
import export_cgof_power_vectors as cgof
import export_power_vectors as legacy
import export_revision_power_vectors as trained

TB = ROOT / "sim/power/tb_power.sv"
FILELIST = "rtl/experimental/filelist_cgof_unit.f"
BASELINE_TB_SHA = "9e9d5f18d0dc72074cf0532d6e1bcfc6f0dfb07ae9ab97ed0667b371ae7a5957"
IVL_ROOT = Path.home() / ".local/opt/cxl-scheduler/iverilog-12.0/usr"
WEIGHTS = (1, 2)
ARMS = ("A", "B")


def log_dir(fallback):
    path = Path(os.environ.get("CXL_CGOF_TB_LOG_DIR", fallback))
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_log(folder, name, command, result):
    (folder / f"{name}.txt").write_text(
        "command: " + " ".join(str(part) for part in command) + f"\nexit: {result.returncode}\n"
        + "--- stdout ---\n" + result.stdout + "--- stderr ---\n" + result.stderr)


def strip_cgof(text):
    """Remove every POWER_CGOF_WEIGHT branch and its wrapper, keeping only the baseline text."""
    kept, regions, depth = [], [], 0
    for line in text.splitlines(keepends=True):
        token = line.strip()
        directive = token.split()[0] if token.startswith("`") else ""
        if directive in ("`ifdef", "`ifndef"):
            depth += 1
            if token == "`ifdef POWER_CGOF_WEIGHT":
                regions.append([depth, True])
                continue
        elif directive == "`else" and regions and regions[-1][0] == depth:
            regions[-1][1] = False
            continue
        elif directive == "`endif":
            depth -= 1
            if regions and regions[-1][0] == depth + 1:
                regions.pop()
                continue
        if not any(skip for _, skip in regions):
            kept.append(line)
    if regions or depth:
        raise ValueError("unbalanced preprocessor regions")
    return "".join(kept)


def reference(weight, arm):
    """Reference rows from the CGOF exporter replay; result lines from the existing V2 helper."""
    metadata = cgof.plan(weight, 509, arm, 256, 64)
    stats = {}
    rows = [legacy._row_text(row) for row in cgof.replay(metadata, stats)]
    metadata.update(stats)
    content = trained.header(metadata) + "\n" + "\n".join(rows) + "\n"
    return metadata, content


class BaselineBranchPreserved(unittest.TestCase):
    def test_baseline_text_is_byte_identical_after_removing_cgof_branches(self):
        current = TB.read_bytes().decode("ascii")
        baseline = strip_cgof(current)
        self.assertEqual(hashlib.sha256(baseline.encode("ascii")).hexdigest(), BASELINE_TB_SHA)
        self.assertIn("      extra = line;\n", baseline)
        self.assertEqual(current.count("`POWER_FIXTURE_POLICY"), baseline.count("`POWER_FIXTURE_POLICY"))
        self.assertNotIn("cgof_unit_top", baseline)


@unittest.skipUnless(sys.platform == "linux" and shutil.which("verilator"), "WSL Verilator required")
class CgofVerilatorReplay(unittest.TestCase):
    """Actual CGOF RTL and the actual common TB; local fixtures only, never power evidence."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cxl-cgof-power-tb-")
        cls.root = Path(cls.tmp.name)
        cls.logs = log_dir(cls.root / "logs")
        cls.binaries = {}
        for weight in WEIGHTS:
            for kind in ("fixture", "production"):
                build = cls.root / f"build-{kind}-{weight}"
                command = ["verilator", "--binary", "--timing", "--timescale", "1ns/1ps",
                           "--top-module", "tb", "--Mdir", str(build), "-j", "1", "+define+POWER_NO_SAIF",
                           *(["+define+POWER_RTL_FIXTURE"] if kind == "fixture" else []),
                           f"+define+POWER_CGOF_WEIGHT={weight}", "-f", FILELIST, "sim/power/tb_power.sv"]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=1800)
                write_log(cls.logs, f"build-{kind}-w{weight}", command, result)
                if result.returncode:
                    raise AssertionError(f"strict Verilator build failed ({kind} w{weight}): {result.stderr}")
                cls.binaries[(kind, weight)] = build / "Vtb"
        cls.references = {}
        for weight in WEIGHTS:
            for arm in ARMS:
                metadata, content = reference(weight, arm)
                cls.references[(weight, arm)] = (metadata, content)
                summary = dict(metadata, vectors_text_sha256=hashlib.sha256(content.encode("ascii")).hexdigest(),
                               rows=metadata["total_cycles"], evidence="LOCAL_W256_FIXTURE_NOT_POWER")
                (cls.logs / f"reference-w{weight}-{arm}.json").write_text(
                    json.dumps(summary, indent=2, sort_keys=True) + "\n")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, binary, name, content, metadata=None, error=None):
        folder = self.root / "runs" / name
        folder.mkdir(parents=True)
        (folder / "vectors.txt").write_text(content)
        command = [str(self.binaries[binary]), f"+vectors={folder}/vectors.txt",
                   f"+result={folder}/result.txt", f"+saif={folder}/unused.saif"]
        result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=300)
        write_log(self.logs, f"run-{name}", command, result)
        output = result.stdout + result.stderr
        if error:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(error, output)
            self.assertFalse((folder / "result.txt").exists())
        else:
            self.assertEqual(result.returncode, 0, output)
            self.assertEqual((folder / "result.txt").read_text().splitlines(),
                             checker.expected_result_v2(metadata))
        return output

    def test_reference_pins_replay_both_weights_both_arms(self):
        for (weight, arm), (metadata, content) in self.references.items():
            with self.subTest(weight=weight, arm=arm):
                self.assertEqual((metadata["mode_id"], metadata["policy_id"], metadata["fai_window"],
                                  metadata["measured_cycles"], metadata["seed"]), (9, weight + 2, 256, 64, 509))
                self.assertEqual(metadata["warmup_cycles"], 512 if arm == "A" else 101_536)
                self.assertEqual(len(metadata["closings"]), metadata["total_cycles"] // 256)
                self.assertEqual(content.splitlines()[0],
                                 f"43585032 9 4 {metadata['total_cycles']} {metadata['warmup_cycles']} 64 509 "
                                 f"{weight + 2} 25000 3")
                output = self.run_case(("fixture", weight), f"good-w{weight}-{arm}", content, metadata)
                self.assertEqual([line for line in output.splitlines() if line.startswith("POWER_LOCAL_TOGGLE_")], [
                    f"POWER_LOCAL_TOGGLE_START checked_cycles={metadata['warmup_cycles']}",
                    f"POWER_LOCAL_TOGGLE_STOP checked_cycles={metadata['total_cycles']} measured_cycles=64"])
                other = 3 - weight
                self.run_case(("fixture", other), f"wrongweight-w{weight}-on-w{other}-{arm}", content,
                              error="invalid CGOF power configuration")

    def test_production_headers_reach_missing_row_zero(self):
        for kind in ("fixture", "production"):
            for weight in WEIGHTS:
                for seed in cgof.SEEDS:
                    for arm in ARMS:
                        header = trained.header(cgof.plan(weight, seed, arm))
                        self.assertEqual(header.split()[1], "12" if arm == "A" else "13")
                        self.run_case((kind, weight), f"prodheader-{kind}-w{weight}-{seed}-{arm}", header + "\n",
                                      error="missing vector row 0")

    def test_production_compile_refuses_local_fixture_mode(self):
        for weight in WEIGHTS:
            metadata, content = self.references[(weight, "A")]
            self.run_case(("production", weight), f"prod-refuses-mode9-w{weight}", content,
                          error="unsupported CGOF power mode (fixture refused by production)")

    def header_cases(self, weight, arm):
        header = trained.header(cgof.plan(weight, 509, arm)).split()
        policy = str(weight + 2)

        def mutate(**fields):
            bad = header.copy()
            for index, value in fields.items():
                bad[int(index[1:])] = value
            return bad
        trained_error = f"invalid CGOF trained {arm} header"
        cases = [("wrongweight", mutate(f7=str(5 - weight)), "invalid CGOF power configuration"),
                 ("v1", "43585031 4 100000 509 3 25000 3".split(), "CGOF requires the V2 power header"),
                 ("badmagic", mutate(f0="43585033"), "CGOF requires the V2 power header"),
                 ("overflowmagic", mutate(f0="143585032"), "noncanonical CGOF power header"),
                 ("short", header[:-1], "invalid CGOF power header"),
                 ("extra", header + ["extra"], "extra CGOF header fields"),
                 ("floatseed", mutate(f6="509.0"), "invalid CGOF power header"),
                 ("leadingzero", mutate(f6="0509"), "noncanonical CGOF power header"),
                 ("mode1", f"43585032 1 4 100000 0 100000 510 {policy} 25000 3".split(),
                  "unsupported CGOF power mode"),
                 ("mode2", f"43585032 2 4 10099500 9999500 100000 509 {policy} 25000 3".split(),
                  "unsupported CGOF power mode"),
                 ("mode0", mutate(f1="0"), "unsupported CGOF power mode"),
                 ("mode14", mutate(f1="14"), "unsupported CGOF power mode"),
                 ("otherarm", mutate(f1="13" if arm == "A" else "12"),
                  f"invalid CGOF trained {'B' if arm == 'A' else 'A'} header")]
        for baseline_policy in (0, 1, 2, 5):
            cases.append((f"policy{baseline_policy}", mutate(f7=str(baseline_policy)),
                          "invalid CGOF power configuration"))
        for seed in (508, 512, 513):
            cases.append((f"seed{seed}", mutate(f6=str(seed)), trained_error))
        for n in (8, 16):
            cases.append((f"n{n}", mutate(f2=str(n)), trained_error))
        for field in (2, 3, 4, 5, 8, 9):
            for delta in (-1, 1):
                error = ("invalid CGOF power header" if field in (3, 4, 5) else
                         trained_error if field == 2 else "invalid CGOF power configuration")
                cases.append((f"field{field}{delta:+d}", mutate(**{f"f{field}": str(int(header[field]) + delta)}),
                              error))
        for field in range(1, 10):
            cases.append((f"overflow{field}", mutate(**{f"f{field}": str(int(header[field]) + 2**32)}),
                          "noncanonical CGOF power header"))
        return cases

    def test_header_rejections_before_rows(self):
        for weight in WEIGHTS:
            for arm in ARMS:
                for name, fields, error in self.header_cases(weight, arm):
                    with self.subTest(weight=weight, arm=arm, case=name):
                        self.run_case(("fixture", weight), f"hdr-w{weight}-{arm}-{name}",
                                      " ".join(fields) + "\n", error=error)
            self.run_case(("fixture", weight), f"hdr-w{weight}-empty", "", error="missing power header")
            for name, kind in (("prod-overflow", "production"), ("prod-wrongweight", "production")):
                fields = trained.header(cgof.plan(weight, 509, "A")).split()
                if name == "prod-overflow":
                    fields[6] = str(509 + 2**32)
                    error = "noncanonical CGOF power header"
                else:
                    fields[7] = str(5 - weight)
                    error = "invalid CGOF power configuration"
                self.run_case((kind, weight), f"hdr-w{weight}-{name}", " ".join(fields) + "\n", error=error)

    def test_fixture_mode_bounds(self):
        for weight in WEIGHTS:
            def header(warmup, measured, seed=509, policy=weight + 2):
                return f"43585032 9 4 {warmup + measured} {warmup} {measured} {seed} {policy} 25000 3\n"
            for name, text, error in (
                    ("warmup102401", header(102_401, 64), "invalid CGOF local fixture header"),
                    ("warmupneg", header(-1, 64), "invalid CGOF local fixture header"),
                    ("measured0", header(512, 0), "invalid CGOF local fixture header"),
                    ("measured102401", header(0, 102_401), "invalid CGOF local fixture header"),
                    ("seed508", header(512, 64, 508), "invalid CGOF local fixture header"),
                    ("seed512", header(512, 64, 512), "invalid CGOF local fixture header"),
                    ("seed513", header(512, 64, 513), "invalid CGOF local fixture header"),
                    ("baselinepolicy", header(512, 64, 509, 1), "invalid CGOF power configuration"),
                    ("upperbound", header(102_400, 102_400), "missing vector row 0")):
                self.run_case(("fixture", weight), f"fixturebound-w{weight}-{name}", text, error=error)

    def test_row_and_pin_mutations_fail_without_result(self):
        for weight in WEIGHTS:
            metadata, content = self.references[(weight, "A")]
            lines = content.splitlines()
            last = len(lines) - 2
            cases = {"malformed": (lines[0] + "\n0 0\n" + "\n".join(lines[2:]) + "\n", "bad vector row 0"),
                     "rowindex": ("\n".join([lines[0], "7" + lines[1][1:], *lines[2:]]) + "\n", "bad vector row 0"),
                     "missing": ("\n".join(lines[:-1]) + "\n", f"missing vector row {last}"),
                     "extrarow": (content + lines[-1] + "\n", "extra vector rows/content"),
                     "extrafield": ("\n".join([lines[0], lines[1] + " extra", *lines[2:]]) + "\n",
                                    "extra fields in vector row 0")}
            row = next(i for i in range(1, len(lines)) if lines[i].split()[5] == "1")
            for field, label in ((4, "ready"), (5, "valid"), (6, "source"), (7, "desc")):
                mutated = lines.copy()
                parts = mutated[row].split()
                parts[field] = f"{int(parts[field], 16) ^ 1:x}"
                mutated[row] = " ".join(parts)
                cases[label] = ("\n".join(mutated) + "\n", f"cycle {row - 1} ")
            for name, (text, error) in cases.items():
                with self.subTest(weight=weight, case=name):
                    self.run_case(("fixture", weight), f"rows-w{weight}-{name}", text, error=error)
        metadata, content = self.references[(2, "B")]
        lines = content.splitlines()
        row = max(i for i in range(1, len(lines)) if lines[i].split()[5] == "1")
        parts = lines[row].split()
        parts[7] = f"{int(parts[7], 16) ^ (1 << 104):027x}"
        lines[row] = " ".join(parts)
        self.run_case(("fixture", 2), "rows-w2-B-late-desc", "\n".join(lines) + "\n",
                      error=f"cycle {row - 1} valid source/full105 mismatch")


STUB = '''`timescale 1ns/1ps
module cgof_unit_top #(parameter int unsigned N_SRC=4, DEPTH=16, FAI_W=5000000, HIGH_WEIGHT=2, ELIGIBLE_RR=0)(
  input clk, rst_n, input [N_SRC-1:0] i_in_valid, input [N_SRC*105-1:0] i_in_desc,
  input i_out_ready, output [N_SRC-1:0] o_in_ready, output o_out_valid,
  output [104:0] o_out_desc, output [$clog2(N_SRC)-1:0] o_out_source);
  integer kind;
  initial if (!$value$plusargs("xkind=%d", kind)) $fatal(1, "xkind missing");
  initial begin
    #1;
    if (kind==5) begin
      @(posedge rst_n);
      force tb.clk = 1'bx;
    end
  end
  assign o_in_ready = !rst_n ? '0 : kind==0 ? 'x : '1;
  assign o_out_valid = !rst_n ? 1'b0 : kind==1 ? 1'bx : 1'b1;
  assign o_out_source = kind==2 ? 'x : '0;
  assign o_out_desc = kind==3 ? 'x : '0;
endmodule
'''


@unittest.skipUnless(sys.platform == "linux" and (IVL_ROOT / "bin/iverilog").is_file(),
                     "user-local WSL Icarus required for true four-state checks")
class CgofFourStateRejection(unittest.TestCase):
    """Bounded pin-only stub (no scheduler) exercises only the common TB's four-state guards."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cxl-cgof-power-x-")
        cls.root = Path(cls.tmp.name)
        cls.logs = log_dir(cls.root / "logs")
        (cls.root / "pin_stub.sv").write_text(STUB)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def build(self, name, *defines):
        command = [str(IVL_ROOT / "bin/iverilog"), "-B", str(IVL_ROOT / "lib/x86_64-linux-gnu/ivl"),
                   "-g2012", "-s", "tb", *defines, "-o", str(self.root / f"{name}.vvp"),
                   str(TB), str(self.root / "pin_stub.sv")]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        write_log(self.logs, f"ivl-build-{name}", command, result)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / f"{name}.vvp"

    def run_vvp(self, image, name, content, kind=4, error=None):
        folder = self.root / name
        folder.mkdir()
        (folder / "vectors.txt").write_text(content)
        command = [str(IVL_ROOT / "bin/vvp"), "-M", str(IVL_ROOT / "lib/x86_64-linux-gnu/ivl"), str(image),
                   f"+xkind={kind}", f"+vectors={folder}/vectors.txt", f"+result={folder}/result.txt",
                   f"+saif={folder}/none.saif"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        write_log(self.logs, f"ivl-run-{name}", command, result)
        output = result.stdout + result.stderr
        if error:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(error, output)
            self.assertFalse((folder / "result.txt").exists())
        else:
            self.assertEqual(result.returncode, 0, output)
            return (folder / "result.txt").read_text().splitlines()

    @staticmethod
    def vectors(policy):
        return f"43585032 9 4 2 1 1 509 {policy} 25000 3\n0 0 0 1 f 1 0 0\n1 0 0 1 f 1 0 0\n"

    def test_common_tb_rejects_x_on_ready_valid_source_desc_and_clock(self):
        fixture = ("-DPOWER_NO_SAIF", "-DPOWER_RTL_FIXTURE")
        for weight in WEIGHTS:
            image = self.build(f"fixture-w{weight}", *fixture, f"-DPOWER_CGOF_WEIGHT={weight}")
            for kind, error in ((0, "ready/valid mismatch"), (1, "ready/valid mismatch"),
                                (2, "valid source/full105 mismatch"), (3, "valid source/full105 mismatch"),
                                (5, "invalid replay clock")):
                with self.subTest(weight=weight, kind=kind):
                    self.run_vvp(image, f"x-w{weight}-k{kind}", self.vectors(weight + 2), kind, error)
            xrow = self.vectors(weight + 2).replace("0 0 0 1 f 1 0 0", "0 x 0 1 f 1 0 0", 1)
            self.run_vvp(image, f"x-w{weight}-input", xrow, 4, "X/Z in vector row 0")
            lines = self.run_vvp(image, f"clean-w{weight}", self.vectors(weight + 2))
            self.assertEqual(lines[0], f"GATE_REPLAY_V2_COMPLETE mode=9 n=4 policy={weight + 2} seed=509 "
                                       "total_cycles=2 warmup_cycles=1 measured_cycles=1 duration_ns=25")

    def test_production_compile_refuses_local_mode9(self):
        for weight in WEIGHTS:
            image = self.build(f"production-w{weight}", "-DPOWER_NO_SAIF", f"-DPOWER_CGOF_WEIGHT={weight}")
            self.run_vvp(image, f"production-mode9-w{weight}", self.vectors(weight + 2),
                         error="unsupported CGOF power mode (fixture refused by production)")

    def test_unsupported_compile_configurations_refused(self):
        fixture = ("-DPOWER_NO_SAIF", "-DPOWER_RTL_FIXTURE")
        for name, defines, error in (
                ("weight0", ("-DPOWER_CGOF_WEIGHT=0",), "unsupported CGOF N/weight configuration"),
                ("weight3", ("-DPOWER_CGOF_WEIGHT=3",), "unsupported CGOF N/weight configuration"),
                ("n8", ("-DPOWER_CGOF_WEIGHT=1", "-DPOWER_N_SRC=8"), "unsupported CGOF N/weight configuration"),
                ("n16", ("-DPOWER_CGOF_WEIGHT=2", "-DPOWER_N_SRC=16"), "unsupported CGOF N/weight configuration"),
                ("baselinepolicy", ("-DPOWER_CGOF_WEIGHT=1", "-DPOWER_FIXTURE_POLICY=1"),
                 "baseline fixture policy define is invalid for CGOF")):
            with self.subTest(config=name):
                image = self.build(f"cfg-{name}", *fixture, *defines)
                self.run_vvp(image, f"cfg-{name}", self.vectors(3), error=error)


if __name__ == "__main__":
    unittest.main()
