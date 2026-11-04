#!/usr/bin/env python3
"""Read-only environment inventory; missing tools are findings, not successful checks.

Uses only Python's standard library. No installs, authentication inspection,
proprietary tool execution, remote connections, or project implementation occur.
WSL is launched only when --wsl is explicitly requested on Windows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


BASIC_VERSIONS = {
    "git": ["--version"],
    "node": ["--version"],
    "npm": ["--version"],
    "claude": ["--version"],
    "ssh": ["-V"],
}
EXECUTABLE_GROUPS = {
    "build": ["python", "python3", "gcc", "g++", "make", "cmake", "pkg-config", "bash"],
    "simulation": ["verilator", "iverilog", "vvp", "cocotb-config", "gtkwave"],
    "lint": ["verible-verilog-lint", "verible-verilog-format", "slang", "slang-server"],
    "formal_synthesis_cdc": ["yosys", "sby", "sv2v", "svlens"],
    "optional": ["jq", "docker", "d2", "pytest"],
    "commercial_eda": [
        "vcs", "xrun", "vsim", "dc_shell", "pt_shell", "genus", "sg_shell",
        "vc_cdc", "questa_cdc", "fm_shell", "lec", "verdi", "simvision",
    ],
}
PYTHON_PACKAGES = {
    "cocotb": "cocotb",
    "cocotb_bus": "cocotb-bus",
    "pytest": "pytest",
    "numpy": "numpy",
    "hjson": "hjson",
}


def run(command: list[str], timeout: int = 15, source: str | None = None) -> dict:
    """Execute an explicit argument array, retaining bounded diagnostic output."""
    try:
        result = subprocess.run(
            command,
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip()[:4096],
            "stderr": result.stderr.strip()[:4096],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "error": f"Timed out after {timeout} seconds"}
    except OSError as exc:
        return {"exit_code": None, "error": str(exc)}


def shell_context() -> dict:
    """Report shell evidence without assuming COMSPEC is the active shell."""
    parent = None
    if os.name == "nt":
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            command = f"(Get-Process -Id {os.getppid()} -ErrorAction Stop).ProcessName"
            result = run([powershell, "-NoProfile", "-NonInteractive", "-Command", command], 5)
            if result.get("exit_code") == 0:
                parent = result["stdout"]
    else:
        try:
            parent = Path(f"/proc/{os.getppid()}/comm").read_text().strip()
        except OSError:
            pass
    return {
        "parent_process_name": parent,
        "configured_shell": os.environ.get("SHELL"),
        "windows_command_processor": os.environ.get("COMSPEC"),
        "msystem": os.environ.get("MSYSTEM"),
        "note": "Parent process and configured shell are evidence; Python may be launched by a wrapper.",
    }


def host_context() -> dict:
    release = platform.release()
    in_wsl = platform.system() == "Linux" and (
        "microsoft" in release.lower() or bool(os.environ.get("WSL_DISTRO_NAME"))
    )
    if in_wsl:
        context = "WSL"
    elif platform.system() == "Windows":
        context = "NATIVE_WINDOWS"
    else:
        context = "NATIVE_OR_REMOTE_NON_WSL"
    return {
        "system": platform.system(),
        "release": release,
        "architecture": platform.machine(),
        "execution_context": context,
        "wsl_distribution": os.environ.get("WSL_DISTRO_NAME") if in_wsl else None,
        "shell": shell_context(),
        "fastx_access": "NOT_TESTED",
        "note": "This audit does not contact FastX or infer university tool access from local findings.",
    }


def package_context() -> dict:
    packages = {}
    for module, distribution in PYTHON_PACKAGES.items():
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[module] = {"module_found": found, "distribution_version": version}
    return {
        "executable": sys.executable,
        "version": platform.python_version(),
        "packages": packages,
        "note": "Module discovery and package metadata are checked; packages are not imported or exercised.",
    }


def git_context(repository: Path) -> dict:
    git = shutil.which("git")
    result = {"requested_path": str(repository), "exists": repository.is_dir()}
    if not git:
        result["status"] = "GIT_NOT_FOUND"
        return result
    if not repository.is_dir():
        result["status"] = "REPOSITORY_DIRECTORY_NOT_FOUND"
        return result
    prefix = [git, "--no-optional-locks", "-C", str(repository)]
    root = run([*prefix, "rev-parse", "--show-toplevel"])
    result["root_probe"] = root
    if root.get("exit_code") != 0:
        result["status"] = "NOT_A_GIT_WORKTREE"
        return result
    result["status"] = "GIT_WORKTREE_FOUND"
    result["working_tree"] = run([*prefix, "status", "--short", "--branch"])
    result["head"] = run([*prefix, "rev-parse", "--verify", "HEAD"])
    return result


def systemc_context() -> dict:
    candidates = []
    if os.name != "nt":
        candidates.extend([Path("/usr/include/systemc"), Path("/usr/local/include/systemc")])
    for name in ("SYSTEMC_HOME", "SYSTEMC"):
        value = os.environ.get(name)
        if value:
            candidates.append(Path(value) / "include" / "systemc")
    found = [str(path) for path in candidates if path.is_file()]
    return {
        "headers_found": found,
        "status": "HEADER_FOUND_NOT_LINK_TESTED" if found else "NOT_FOUND_IN_CHECKED_LOCATIONS",
        "note": "Only conventional/configured header locations are checked; no installation or compile/link test.",
    }


def audit(repository: Path) -> dict:
    basic = {}
    for name, arguments in BASIC_VERSIONS.items():
        path = shutil.which(name)
        basic[name] = {"found": path is not None, "path": path}
        if path:
            basic[name]["version_probe"] = run([path, *arguments])
    groups = {}
    for group, commands in EXECUTABLE_GROUPS.items():
        groups[group] = {}
        for command in commands:
            path = shutil.which(command)
            groups[group][command] = {"found": path is not None, "path": path}
    return {
        "schema_version": 1,
        "observed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": host_context(),
        "repository": git_context(repository),
        "python": package_context(),
        "basic_tools": basic,
        "executables": groups,
        "systemc": systemc_context(),
        "scope": "Read-only inventory. Executable presence does not prove EDA operation, licensing, or pipeline readiness.",
    }


def wsl_repository_path(repository: Path) -> str:
    if not repository.drive or len(repository.drive) != 2 or repository.drive[1] != ":":
        raise ValueError("WSL audit requires a repository on a Windows drive (UNC paths are unsupported).")
    return f"/mnt/{repository.drive[0].lower()}/" + "/".join(repository.parts[1:])


def probe_wsl(repository: Path) -> dict:
    if os.name != "nt":
        return {"status": "NOT_APPLICABLE", "reason": "--wsl launches Ubuntu only from Windows."}
    executable = shutil.which("wsl")
    if not executable:
        return {"status": "WSL_NOT_FOUND"}
    try:
        translated = wsl_repository_path(repository)
        source = Path(__file__).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return {"status": "PROBE_UNAVAILABLE", "error": str(exc)}
    command = [executable, "--distribution", "Ubuntu", "--exec", "python3", "-", "--json", "--repo", translated]
    # WSL child emits a full inventory, so allow more output than a single version probe.
    try:
        completed = subprocess.run(
            command, input=source, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=55, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "PROBE_FAILED", "error": str(exc)}
    if completed.returncode != 0:
        return {"status": "PROBE_FAILED", "exit_code": completed.returncode, "stderr": completed.stderr.strip()[:4096]}
    try:
        return {"status": "PROBED", "distribution": "Ubuntu", "audit": json.loads(completed.stdout)}
    except json.JSONDecodeError:
        return {"status": "PROBE_FAILED", "error": "Ubuntu did not return valid audit JSON.", "stderr": completed.stderr.strip()[:4096]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable inventory.")
    parser.add_argument("--repo", type=Path, default=None, help="Repository directory (default: this script's project).")
    parser.add_argument("--wsl", action="store_true", help="Also audit Ubuntu through WSL; never launched by default.")
    args = parser.parse_args()
    repository = (args.repo or Path(__file__).resolve().parents[1]).resolve()
    inventory = audit(repository)
    inventory["wsl_probe"] = probe_wsl(repository) if args.wsl else {"status": "NOT_REQUESTED"}
    if args.json:
        print(json.dumps(inventory, indent=2, ensure_ascii=False))
    else:
        print(f"Host: {inventory['host']['system']} / {inventory['host']['execution_context']}")
        print(f"Repository: {repository} ({inventory['repository'].get('status')})")
        print(f"Python: {inventory['python']['version']} ({sys.executable})")
        for name, tool in inventory["basic_tools"].items():
            probe = tool.get("version_probe", {})
            version = probe.get("stdout") or probe.get("stderr") or probe.get("error")
            print(f"{name}: {version if tool['found'] else 'NOT_FOUND'}")
        for group, tools in inventory["executables"].items():
            found = ", ".join(name for name, tool in tools.items() if tool["found"]) or "none"
            missing = ", ".join(name for name, tool in tools.items() if not tool["found"]) or "none"
            print(f"{group}: found [{found}]; missing [{missing}]")
        packages = inventory["python"]["packages"]
        print("Python packages: " + ", ".join(f"{name}={'FOUND' if info['module_found'] else 'NOT_FOUND'}" for name, info in packages.items()))
        print(f"SystemC: {inventory['systemc']['status']}")
        print(f"WSL probe: {inventory['wsl_probe']['status']}; FastX access: NOT_TESTED")
        print(inventory["scope"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
