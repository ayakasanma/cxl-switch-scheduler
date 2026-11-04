#!/usr/bin/env bash
# Reproduce the authorized lightweight WSL verification tool environment.
# Builds and binaries stay in Linux home; this creates no Git repository.
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
tool_home=${CXL_TOOL_HOME:-$HOME/.local/opt/cxl-scheduler}
cache_root=${CXL_CACHE_ROOT:-$HOME/.cache/cxl-scheduler}
venv=${CXL_VENV:-$HOME/.local/share/cxl-scheduler/venvs/py312-cocotb210}
verilator_version=5.052
verilator_sha=8c8d2e11e6ad32f641dd250742a94195ddecb912e2e2dabe2f42ddbbb99c1092
verible_tag=v0.0-4296-g0f262651
verible_sha=8569defb891d2316067613ea00442af28a7a09d405d95b54c0c91f9942d26635
apt_packages=(build-essential perl python3 python3-venv libpython3.12t64 autoconf flex bison
              help2man libfl-dev zlib1g-dev liblz4-dev curl ca-certificates jq)

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_wsl.sh [--apt-only | --check]
  --apt-only  Install the approved essential Ubuntu build prerequisites as root.
  --check     Read-only executable/version/dependency checks after setup.
  default     Verify prerequisites; install pinned user-local tools and venv.
No SystemC, CDC, formal, cloud, or proprietary software is installed.
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --apt-only)
    [[ $EUID -eq 0 ]] || { printf '%s\n' '--apt-only requires root (sudo or wsl.exe --user root).'; exit 2; }
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install --no-install-recommends -y "${apt_packages[@]}"
    exit 0 ;;
  --check)
    source "$project_root/scripts/wsl_env.sh"
    verilator --version | grep -E "^Verilator ${verilator_version//./\\.} "
    verible-verilog-lint --version 2>&1 | grep -F "$verible_tag"
    "$CXL_VENV/bin/python" - "$project_root/requirements-wsl.lock.txt" <<'PY'
import importlib.metadata
import os
from pathlib import Path
import sys
from find_libpython import find_libpython

if sys.version_info[:2] != (3, 12):
    raise SystemExit("Expected Python 3.12 for this lock")
if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != Path(os.environ["CXL_VENV"]).resolve():
    raise SystemExit("Python is not using the selected dedicated CXL virtual environment")
pins = [line.strip() for line in Path(sys.argv[1]).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")]
for pin in ["pip==24.0", *pins]:
    package, expected = pin.split("==", 1)
    actual = importlib.metadata.version(package)
    if actual != expected:
        raise SystemExit(f"Version mismatch: {package} expected {expected}, found {actual}")
    print(f"{package}=={actual}")
library = find_libpython()
if not library or not Path(library).is_file():
    raise SystemExit("A matching Python shared runtime is required for cocotb embedding")
print(f"Python {sys.version.split()[0]}; shared runtime: {library}")
PY
    "$CXL_VENV/bin/python" -m pip check
    exit 0 ;;
  '') ;;
  *) usage >&2; exit 2 ;;
esac

[[ $EUID -ne 0 ]] || { printf '%s\n' 'Run tool setup as the WSL project user; root is for --apt-only.' >&2; exit 2; }
[[ $(uname -m) == x86_64 ]] || { printf '%s\n' 'Pinned Verible binary requires x86_64.' >&2; exit 2; }
for executable in g++ make perl python3 autoconf flex bison help2man curl tar sha256sum jq; do
  command -v "$executable" >/dev/null || {
    printf 'Missing %s; first run the authorized --apt-only step.\n' "$executable" >&2
    exit 2
  }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Lock tested on Python 3.12")'
for package in libfl-dev zlib1g-dev liblz4-dev python3-venv libpython3.12t64; do
  [[ $(dpkg-query -W -f='${Status}' "$package" 2>/dev/null) == 'install ok installed' ]] || {
    printf 'Missing %s; first run --apt-only.\n' "$package" >&2
    exit 2
  }
done
mkdir -p "$cache_root/downloads" "$cache_root/src" "$cache_root/logs" "$tool_home"

download_verified() {
  local url=$1 archive=$2 digest=$3
  if [[ ! -f $archive ]]; then
    curl --fail --location --retry 3 "$url" --output "$archive.part"
    mv -- "$archive.part" "$archive"
  fi
  printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status || {
    printf 'SHA256 mismatch: %s; do not use this archive.\n' "$archive" >&2
    exit 3
  }
}

verilator_prefix="$tool_home/verilator-$verilator_version"
if [[ ! -x "$verilator_prefix/bin/verilator_bin" ]]; then
  archive="$cache_root/downloads/verilator-$verilator_version.tar.gz"
  download_verified "https://github.com/verilator/verilator/archive/refs/tags/v$verilator_version.tar.gz" "$archive" "$verilator_sha"
  source_dir="$cache_root/src/verilator-$verilator_version"
  [[ -d $source_dir ]] || tar -xzf "$archive" -C "$cache_root/src"
  (
    cd "$source_dir"
    unset VERILATOR_ROOT
    autoconf
    ./configure --prefix="$verilator_prefix" > "$cache_root/logs/verilator-configure.log" 2>&1
    # Cap build parallelism to avoid consuming the user's WSL memory.
    make -j2 > "$cache_root/logs/verilator-build.log" 2>&1
    make install > "$cache_root/logs/verilator-install.log" 2>&1
  )
fi
"$verilator_prefix/bin/verilator" --version | grep -F "Verilator $verilator_version "

verible_prefix="$tool_home/verible-$verible_tag"
if [[ ! -x "$verible_prefix/bin/verible-verilog-lint" ]]; then
  archive="$cache_root/downloads/verible-$verible_tag-linux-static-x86_64.tar.gz"
  download_verified "https://github.com/chipsalliance/verible/releases/download/$verible_tag/$(basename "$archive")" "$archive" "$verible_sha"
  tar -xzf "$archive" -C "$tool_home"
fi
"$verible_prefix/bin/verible-verilog-lint" --version

[[ -x "$venv/bin/python" ]] || python3 -m venv "$venv"
"$venv/bin/python" -m pip install 'pip==24.0'
"$venv/bin/python" -m pip install --requirement "$project_root/requirements-wsl.lock.txt"
"$venv/bin/python" -m pip check
printf '%s\n' 'Pinned tools installed. Source scripts/wsl_env.sh, then run scripts/smoke_wsl_toolchain.py.'
