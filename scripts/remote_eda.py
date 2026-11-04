#!/usr/bin/env python3
"""Explicit, dry-run-first FastX preflight / synthesis / STA orchestration.

Python standard library and local OpenSSH only. No libraries/licenses are transferred.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
FIELDS = {
    "host", "user", "port", "identity_file", "remote_work_root", "module_name",
    "module_init", "target_library", "top_module", "rtl_files", "constraint_files",
    "sta_netlist_files", "sta_constraint_files",
}
FILE_TYPES = {
    "rtl_files": {".v", ".sv", ".vh", ".svh"},
    "constraint_files": {".sdc"},
    "sta_netlist_files": {".v"},
    "sta_constraint_files": {".sdc"},
}
FIXED_INPUTS = ("scripts/remote_entry.sh", "syn/dc.tcl", "sta/pt.tcl")


def fail(message: str) -> None:
    raise ValueError(message)


def portable_component(name: str) -> bool:
    """Use names that can be stored as ordinary files on Windows and Linux."""
    if not name or name.endswith((".", " ")) or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
        return False
    base = name.split(".", 1)[0].rstrip(" ").upper()
    if base in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}:
        return False
    return re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", base) is None


def clean_text(value: object, name: str, required: bool = True) -> str:
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        fail(f"{name} must be a string without control characters")
    if required and not value.strip():
        fail(f"Fill {name} in your local configuration")
    return value


def linux_path(value: object, name: str, required: bool = True) -> str:
    path = clean_text(value, name, required)
    if not path and not required:
        return path
    if not path.startswith("/") or ".." in PurePosixPath(path).parts:
        fail(f"{name} must be an absolute Linux path without '..'")
    return path


def repo_file(value: object, suffixes: set[str] | None = None) -> tuple[str, Path]:
    name = clean_text(value, "repository input")
    path = PurePosixPath(name)
    if path.is_absolute() or any(not portable_component(part) for part in name.split("/")):
        fail(f"Input must be a repository-relative path with forward slashes: {name}")
    # Do not permit symlinks, including intermediate directories, or paths outside ROOT.
    local = ROOT.joinpath(*path.parts)
    current = ROOT
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            fail(f"Symlink inputs are forbidden: {name}")
    if not local.resolve().is_relative_to(ROOT) or not local.is_file():
        fail(f"Input is not a regular file inside this repository: {name}")
    if suffixes is not None and path.suffix.lower() not in suffixes:
        fail(f"Forbidden input extension for {name}; allowed: {', '.join(sorted(suffixes))}")
    return str(path), local


def load_config(path: Path, mode: str) -> dict:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict) or set(config) - FIELDS:
        fail("Configuration must be an object containing only the fields from fastx.config.example.json")
    for key in ("host", "user", "module_name"):
        config[key] = clean_text(config.get(key, ""), key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", config["host"]):
        fail("host must be a DNS name or IPv4 address without SSH options")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", config["user"]):
        fail("user must be a plain SSH account name")
    port = config.get("port", 22)
    if type(port) is not int or not 1 <= port <= 65535:
        fail("port must be an integer from 1 to 65535")
    config["port"] = port
    config["target_library"] = linux_path(config.get("target_library", ""), "target_library")
    if not config["target_library"].endswith(".db"):
        fail("target_library must point to an existing university .db library")
    config["module_init"] = linux_path(config.get("module_init", ""), "module_init", required=False)
    config["identity_file"] = clean_text(config.get("identity_file", ""), "identity_file", required=False)
    if config["identity_file"]:
        identity = Path(config["identity_file"]).expanduser()
        if not identity.is_file():
            fail("identity_file does not exist locally")
        config["identity_file"] = str(identity.resolve())
    for field in FILE_TYPES:
        values = config.get(field, [])
        if not isinstance(values, list):
            fail(f"{field} must be an array of explicit repository-relative paths")
        config[field] = [clean_text(value, field) for value in values]
    if mode != "preflight":
        config["remote_work_root"] = linux_path(config.get("remote_work_root", ""), "remote_work_root").rstrip("/")
        if not config["remote_work_root"] or len(PurePosixPath(config["remote_work_root"]).parts) < 3:
            fail("remote_work_root must be a dedicated project directory below a parent directory")
        config["top_module"] = clean_text(config.get("top_module", ""), "top_module")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", config["top_module"]) or not portable_component(config["top_module"]):
            fail("top_module must be a Verilog identifier usable as an ordinary Windows filename")
        active_fields = ("rtl_files", "constraint_files") if mode == "syn" else ("sta_netlist_files", "sta_constraint_files")
        for field in active_fields:
            values = config.get(field, [])
            if not isinstance(values, list) or not values:
                fail(f"List explicit repository files in {field}")
            config[field] = [repo_file(value, FILE_TYPES[field])[0] for value in values]
    return config


def approved_architecture() -> tuple[str, Path]:
    name, path = repo_file("specs/APPROVAL.md")
    content = path.read_text(encoding="utf-8-sig")
    if not re.search(r"^Architecture status: APPROVED\s*$", content, re.M):
        fail("specs/APPROVAL.md must record 'Architecture status: APPROVED' after human specification approval")
    approver = re.search(r"^Approved by:[ \t]*(\S[^\r\n]*)$", content, re.M)
    date = re.search(r"^Approved on:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$", content, re.M)
    if not approver or not date or approver.group(1).strip().lower() in {"pending", "tbd", "unknown"}:
        fail("Architecture approval must include a named approver and 'Approved on: YYYY-MM-DD'")
    try:
        dt.date.fromisoformat(date.group(1))
    except ValueError:
        fail("Architecture approval date is invalid")
    specification = re.search(r"^Specification:[ \t]*(\S[^\r\n]*)$", content, re.M)
    reference = specification.group(1).strip() if specification else ""
    if (not reference or reference.lower() in {"pending", "tbd", "unknown", "todo", "n/a", "..."}
            or "<" in reference or ">" in reference):
        fail("Architecture approval must include a non-placeholder 'Specification: <exact approved revision or commit>' field")
    return name, path


def tcl_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ('"', "$", "[", "]"):
        escaped = escaped.replace(char, "\\" + char)
    return '"' + escaped + '"'


def tcl_config(config: dict) -> bytes:
    lines = ["# Generated for this isolated run; contains paths only, no library content."]
    for key, field in (("TOP_MODULE", "top_module"), ("TARGET_LIBRARY", "target_library")):
        lines.append(f"set {key} {tcl_string(config[field])}")
    for key, field in (("RTL_FILES", "rtl_files"), ("CONSTRAINT_FILES", "constraint_files"),
                       ("STA_NETLIST_FILES", "sta_netlist_files"), ("STA_CONSTRAINT_FILES", "sta_constraint_files")):
        values = config.get(field, [])
        lines.append(f"set {key} [list {' '.join(tcl_string(value) for value in values)}]")
    return ("\n".join(lines) + "\n").encode("utf-8")


def ssh_args(config: dict) -> list[str]:
    ssh = shutil.which("ssh")
    if not ssh:
        fail("OpenSSH ssh is unavailable locally; install it only with permission")
    args = [ssh, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=yes", "-p", str(config["port"])]
    if config["identity_file"]:
        args += ["-i", config["identity_file"]]
    return args + [f"{config['user']}@{config['host']}"]


def shell_environment(config: dict, job_dir: str = "") -> str:
    return "\n".join(f"export {key}={shlex.quote(value)}" for key, value in (
        ("EDA_MODULE", config["module_name"]), ("EDA_MODULE_INIT", config["module_init"]),
        ("EDA_TARGET_LIBRARY", config["target_library"]), ("EDA_JOB_DIR", job_dir),
        ("EDA_TOP_MODULE", config.get("top_module", "")),
    )) + "\n"


def run_ssh(config: dict, script: str, data: bytes | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    command = ssh_args(config) + ["bash -lc " + shlex.quote(script)]
    return subprocess.run(command, input=data, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, check=False)


def input_files(config: dict, mode: str) -> dict[str, bytes]:
    _, approved_path = approved_architecture()
    fields = ("rtl_files", "constraint_files") if mode == "syn" else ("sta_netlist_files", "sta_constraint_files")
    files = {name: repo_file(name)[1].read_bytes() for name in FIXED_INPUTS}
    for field in fields:
        for name in config[field]:
            files[name] = repo_file(name, FILE_TYPES[field])[1].read_bytes()
    files["ARCHITECTURE_APPROVAL.md"] = approved_path.read_bytes()
    files["run_config.tcl"] = tcl_config(config)
    return files


def upload_archive(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in files.items():
            item = tarfile.TarInfo(name)
            item.mode = 0o600
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
    return stream.getvalue()


def save_download(data: bytes, destination: Path) -> list[str]:
    if len(data) > MAX_DOWNLOAD_BYTES:
        fail("Downloaded archive exceeds 512 MiB")
    saved = []
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            allowed = (len(name.parts) == 2 and name.parts[0] in {"reports", "output"}
                       and ((name.parts[0] == "reports" and name.suffix in {".rpt", ".log"})
                            or (name.parts[0] == "output" and name.suffix in {".v", ".sdc"})))
            if (not member.isfile() or name.is_absolute() or ".." in name.parts or not allowed
                    or any(not portable_component(part) for part in member.name.split("/"))):
                fail(f"Refusing unexpected remote output: {member.name}")
            total += member.size
            if total > MAX_DOWNLOAD_BYTES:
                fail("Expanded remote outputs exceed 512 MiB")
            target = destination.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                fail(f"Cannot read remote output: {member.name}")
            with target.open("xb") as out:
                shutil.copyfileobj(source, out)
            saved.append(str(name))
    return saved


def git_state() -> dict:
    git = shutil.which("git")
    if not git:
        return {"revision": None, "worktree_status": None}
    revision = subprocess.run([git, "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    status = subprocess.run([git, "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, check=False)
    return {"revision": revision.stdout.strip() if not revision.returncode else None,
            "worktree_status": status.stdout.splitlines() if not status.returncode else None}


def execute_job(config: dict, mode: str, run_id: str, job_dir: str, files: dict[str, bytes]) -> int:
    destination = ROOT / "artifacts" / "fastx" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {
        "operation": mode, "host": config["host"], "remote_directory": job_dir,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "configuration": {key: value for key, value in config.items() if key != "identity_file"},
        "git": git_state(),
        "execution_status": "STARTED",
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # mkdir without -p for the final directory ensures an existing run is never overwritten.
    upload = ("set -euo pipefail\n"
              f"mkdir -p -- {shlex.quote(config['remote_work_root'] + '/runs')}\n"
              f"mkdir -- {shlex.quote(job_dir)}\n"
              f"tar -xf - -C {shlex.quote(job_dir)} --no-same-owner --no-same-permissions\n")
    uploaded = run_ssh(config, upload, upload_archive(files))
    if uploaded.returncode:
        manifest["execution_status"] = "UPLOAD_FAILED"
        manifest["upload_exit_code"] = uploaded.returncode
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return uploaded.returncode
    script = ("set -euo pipefail\n" + shell_environment(config, job_dir)
              + f"cd -- {shlex.quote(job_dir)}\nbash -- scripts/remote_entry.sh {shlex.quote(mode)}\n")
    executed = run_ssh(config, script)
    # Select only generated reports/netlists/SDC. Never archive host libraries or configs.
    download_script = ("set -euo pipefail\n" + f"cd -- {shlex.quote(job_dir)}\n"
                       + "shopt -s nullglob\nfiles=()\n"
                       + "for file in reports/*.rpt reports/*.log output/*.v output/*.sdc; do\n"
                       + '  [[ -f "$file" && ! -L "$file" ]] && files+=("$file")\n'
                       + "done\n"
                       + 'if ((${#files[@]})); then tar -czf - -- "${files[@]}"; '
                       + "else tar -czf - --files-from /dev/null; fi\n")
    downloaded = run_ssh(config, download_script, capture=True)
    manifest["tool_exit_code"] = executed.returncode
    manifest["download_exit_code"] = downloaded.returncode
    manifest["execution_status"] = "FAILED"
    try:
        if downloaded.returncode:
            print(downloaded.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        else:
            manifest["downloaded_files"] = save_download(downloaded.stdout, destination)
            if executed.returncode == 0:
                required = {"reports/run_status.rpt", "reports/dc.log" if mode == "syn" else "reports/pt.log"}
                if mode == "syn":
                    required |= {f"output/{config['top_module']}.syn.v", f"output/{config['top_module']}.syn.sdc"}
                if not required.issubset(manifest["downloaded_files"]):
                    fail("Remote command returned zero but required output files are missing")
                marker = (destination / "reports" / "run_status.rpt").read_text(encoding="utf-8")
                if f"STATUS: SUCCESS\nOPERATION: {mode}\n" != marker:
                    fail("Remote completion marker does not match the requested operation")
                manifest["execution_status"] = "TOOL_COMMANDS_COMPLETED"
    except (ValueError, tarfile.TarError, OSError):
        manifest["execution_status"] = "DOWNLOAD_REJECTED"
        raise
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated outputs and manifest: {destination}")
    return executed.returncode or downloaded.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preflight", "syn", "sta"))
    parser.add_argument("--config", type=Path, default=ROOT / "scripts" / "fastx.config.local.json")
    parser.add_argument("--execute", action="store_true", help="Make SSH calls; omission is always a dry run")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, args.operation)
        ssh = ssh_args(config)
        if args.operation == "preflight":
            entry = repo_file("scripts/remote_entry.sh")[1].read_text(encoding="utf-8")
            script = shell_environment(config) + "set -- preflight\n" + entry
            print(json.dumps({"operation": "preflight", "execute": args.execute, "ssh_target": ssh[-1],
                              "module": config["module_name"], "library_check": config["target_library"],
                              "uploads": [], "downloads": []}, indent=2))
            if not args.execute:
                print("DRY RUN: no SSH connection was attempted.")
                return 0
            return run_ssh(config, script).returncode
        files = input_files(config, args.operation)
        run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
        job_dir = config["remote_work_root"] + "/runs/" + run_id
        print(json.dumps({"operation": args.operation, "execute": args.execute, "ssh_target": ssh[-1],
                          "remote_directory": job_dir, "uploads": sorted(files),
                          "downloads": ["reports/*.rpt", "reports/*.log", "output/*.v", "output/*.sdc"]}, indent=2))
        if not args.execute:
            print("DRY RUN: no SSH connection was attempted and no artifacts were created.")
            return 0
        return execute_job(config, args.operation, run_id, job_dir, files)
    except (ValueError, OSError, json.JSONDecodeError, tarfile.TarError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
