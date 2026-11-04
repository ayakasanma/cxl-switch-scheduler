#!/usr/bin/env python3
"""Verify tool integration with a temporary eight-bit wire, never scheduler RTL.

Run with scripts/wsl_env.sh sourced. Only installation evidence is generated.
The fixture and simulator build live under a Linux temporary directory. A log
may be redirected to ignored .setup-logs; no scheduler result is produced.
"""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def run(arguments: list[str], directory: Path) -> None:
    print("+", " ".join(arguments), flush=True)
    # Native child processes inherit the caller's PWD even after cwd changes.
    # Normalize it so make/cocotb cannot use the Windows-mounted project path.
    environment = dict(os.environ, PWD=str(directory),
                       CXL_EXPECTED_PY_VERSION=".".join(map(str, sys.version_info[:3])))
    subprocess.run(arguments, cwd=directory, env=environment, check=True)


def main() -> None:
    selected_venv = os.environ.get("CXL_VENV")
    if (not selected_venv or sys.prefix == sys.base_prefix
            or Path(sys.prefix).resolve() != Path(selected_venv).resolve()):
        raise RuntimeError("Source scripts/wsl_env.sh and use its dedicated Python environment")
    with tempfile.TemporaryDirectory(prefix="cxl-tools-only-") as temporary:
        directory = Path(temporary)
        source = directory / "toolchain_loopback.sv"
        source.write_text(
            "module toolchain_loopback (\n"
            "    input logic [7:0] data_i,\n"
            "    output logic [7:0] data_o\n"
            ");\n"
            "  assign data_o = data_i;\n"
            "endmodule : toolchain_loopback\n",
            encoding="utf-8",
        )
        (directory / "test_toolchain_loopback.py").write_text(
            "import os\nimport sys\nfrom pathlib import Path\nimport cocotb\n"
            "from cocotb.triggers import Timer\n\n"
            "@cocotb.test()\n"
            "async def wire_roundtrip(dut):\n"
            "    runtime_version = '.'.join(map(str, sys.version_info[:3]))\n"
            "    dut._log.info('Actual embedded Python runtime: %s; prefix: %s', runtime_version, sys.prefix)\n"
            "    if runtime_version != os.environ['CXL_EXPECTED_PY_VERSION']:\n"
            "        raise AssertionError('Embedded and launching Python versions differ')\n"
            "    if Path(sys.prefix).resolve() != Path(os.environ['CXL_VENV']).resolve():\n"
            "        raise AssertionError('Embedded Python escaped the selected venv')\n"
            "    for value in (0, 255, 165, 90, 1, 128):\n"
            "        dut.data_i.value = value\n"
            "        await Timer(2, unit='ns')\n"
            "        if int(dut.data_o.value) != value:\n"
            "            raise AssertionError('Wire roundtrip mismatch')\n",
            encoding="utf-8",
        )
        (directory / "Makefile").write_text(
            "SIM = verilator\n"
            "TOPLEVEL_LANG = verilog\n"
            "VERILOG_SOURCES = $(CURDIR)/toolchain_loopback.sv\n"
            "COCOTB_TOPLEVEL = toolchain_loopback\n"
            "COCOTB_TEST_MODULES = test_toolchain_loopback\n"
            "include $(shell cocotb-config --makefiles)/Makefile.sim\n",
            encoding="utf-8",
        )
        run(["verilator", "--version"], directory)
        run(["verible-verilog-lint", "--version"], directory)
        run([sys.executable, "-m", "pip", "check"], directory)
        run(["verilator", "--lint-only", "--Wall", "--sv", str(source)], directory)
        run(["verible-verilog-lint", str(source)], directory)
        run(["make", "SIM=verilator", "COCOTB_RANDOM_SEED=509"], directory)
        result = ET.parse(directory / "results.xml").getroot()
        tests = list(result.iter("testcase"))
        if len(tests) != 1 or any(list(result.iter(tag)) for tag in ("failure", "error", "skipped")):
            raise RuntimeError("Expected exactly one passing, unskipped cocotb testcase")
        print(f"INFRASTRUCTURE_SMOKE_PASS: {len(tests)} temporary wire test; no scheduler RTL or verification.", flush=True)


if __name__ == "__main__":
    main()
