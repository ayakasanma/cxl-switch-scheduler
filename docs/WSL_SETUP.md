# WSL verification tool environment

The project owner authorized Verilator, cocotb, and necessary open-source verification dependencies in WSL on 2026-10-13. This authorization covers environment setup. Scheduler RTL, reference models, scheduler verification, and the nine synthesis/PPA experiments remain unimplemented and unrun.

## Selected runtime and pins

| Component | Selection | Scope |
| --- | --- | --- |
| Distro | Ubuntu 24.04.4 LTS, WSL2, x86_64 | Existing local WSL distro |
| Python | Ubuntu Python 3.12.3 | Existing runtime |
| Verilator | 5.052, upstream release 2026-09-05 | Source tarball, user-local prefix |
| cocotb | 2.1.0 | Project-dedicated Python virtual environment |
| pytest | 9.1.1 | Same virtual environment |
| Verible | v0.0-4296-g0f262651, static Linux x86_64 | Official release binary, user-local prefix |
| jq | 1.7.1 | Ubuntu dependency for plugin shell hooks |

Ubuntu's observed `apt` Verilator candidate is 5.020. The selected [cocotb 2.1.0 simulator support](https://docs.cocotb.org/en/v2.1.0/simulator_support.html) requires Verilator 5.036 or newer, so the project uses an upstream versioned source build. The build follows [Verilator's official installation instructions](https://verilator.org/guide/latest/install.html), uses `--prefix` under the WSL user's home, and caps compilation at two jobs. The [Verible release](https://github.com/chipsalliance/verible/releases/tag/v0.0-4296-g0f262651) provides a small standalone static lint/format bundle.

All Python package versions are recorded in `requirements-wsl.lock.txt`. Pip itself is pinned to 24.0 by the setup script. Linux tools, source archives, and builds live on the WSL filesystem, avoiding Windows-mounted virtual-environment and build-directory overhead. Their versioned directories are dedicated to this project; they are not a second project checkout or Git repository. No `.bashrc` modification is required.

## Reproduce installation

From PowerShell, in the existing `cxl-scheduler` directory:

```powershell
# Explicit approved prerequisite step, limited to the existing Ubuntu distro:
wsl.exe --distribution Ubuntu --user root -- bash -lc 'cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler" && bash scripts/setup_wsl.sh --apt-only'
# Source build / Python packages run as the ordinary WSL user:
wsl.exe --distribution Ubuntu -- bash -lc 'cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler" && bash scripts/setup_wsl.sh'
```

Alternatively, inside Ubuntu, `sudo bash scripts/setup_wsl.sh --apt-only` installs the same prerequisites and `bash scripts/setup_wsl.sh` installs the user-local pinned tools. The default invocation does not attempt privilege elevation and reports any missing prerequisite.

The WSL user's noninteractive `sudo` check required a password. The authorized installation therefore used `wsl.exe --distribution Ubuntu --user root` for the prerequisite step only. No password, user identity, broad directory ownership, Windows software, or default distro setting was changed.

Essential apt packages are `build-essential`, `perl`, `python3`, `python3-venv`, `libpython3.12t64`, `autoconf`, `flex`, `bison`, `help2man`, `libfl-dev`, `zlib1g-dev`, `liblz4-dev`, `curl`, `ca-certificates`, and `jq`. The shared Python runtime was already present on this machine, but is explicitly required for reproducing cocotb embedding on a fresh distro; `python3-venv` alone does not provide it. See [cocotb's prerequisites](https://docs.cocotb.org/en/v2.1.0/install.html). Ubuntu package dependencies may be updated as required by this install; this is not an `apt upgrade` of the distro. Exact package revisions can change with Ubuntu security updates, while Verilator/Verible source or binary digests and Python package versions are pinned.

## Activate and check

Within WSL, from the repository root:

```bash
source scripts/wsl_env.sh
bash scripts/setup_wsl.sh --check
python scripts/smoke_wsl_toolchain.py
```

`wsl_env.sh` sets this shell's tool paths, `SIM=verilator`, and isolated Python import behavior; it clears an inherited `VERILATOR_ROOT` so the installed prefix locates its matching runtime. To select a custom Linux tool location, set `CXL_TOOL_HOME`, `CXL_VENV`, and optionally `CXL_CACHE_ROOT` consistently for both setup and activation. Absolute local paths and credentials are not stored in tracked configuration.

`--check` is read-only and rejects version drift: it verifies the pinned Verilator/Verible releases, Python 3.12 in the selected dedicated venv, every locked Python distribution and pip, the shared-runtime path, and `pip check`. For a current inventory, run `python scripts/check_environment.py --json` inside this activated WSL shell. The native Windows audit's optional `--wsl` probe does not activate this profile automatically and may therefore report user-local tools as absent from its default PATH.

`smoke_wsl_toolchain.py` creates a temporary eight-bit combinational wire under Linux's temporary directory, checks Verilator lint and Verible lint, and runs six data values through cocotb's Verilator VPI integration. It removes the fixture/build automatically. This is installation/infrastructure verification only; it does not create scheduler RTL, a scheduler reference model, or project functional evidence. The result must include actual simulator execution and a passing JUnit testcase; an installed package alone does not constitute a smoke-test pass.

## Download integrity

| Artifact | SHA256 | Provenance |
| --- | --- | --- |
| `verilator-5.052.tar.gz` | `8c8d2e11e6ad32f641dd250742a94195ddecb912e2e2dabe2f42ddbbb99c1092` | Observed digest of the official GitHub `v5.052` tag archive downloaded over HTTPS; not an upstream signed checksum. |
| `verible-v0.0-4296-g0f262651-linux-static-x86_64.tar.gz` | `8569defb891d2316067613ea00442af28a7a09d405d95b54c0c91f9942d26635` | Publisher digest from the official GitHub release asset metadata, verified after download. |

Archive downloads are checked before extraction; a changed archive fails setup rather than silently accepting a different build. Python packages use exact version pins from PyPI, without claiming cryptographic lockfile coverage.

## Observed checks and limits

**Selected lightweight WSL profile: READY_FOR_ENVIRONMENT_USE.** Installation and the final integration check succeeded on 2026-10-13. This status covers tool operation only; the tool smoke does not authorize architecture by itself. Subsequent owner approval opens the controlled implementation gate; see specs/APPROVAL.md.

| Check | Observed result |
| --- | --- |
| Pinned version / dedicated venv / shared runtime checks | PASS; Verilator5.052, Verible v0.0-4296-g0f262651, Python3.12.3, cocotb2.1.0, pytest9.1.1, remaining lock pins matched. |
| Python dependency health | `pip check`: no broken requirements. |
| Setup/activation syntax | Bash syntax PASS; smoke Python syntax PASS. |
| Verilator lint + Verible lint | PASS for the temporary generic eight-bit wire. |
| Verilator compile/link and cocotb VPI execution | PASS; exactly one testcase, six data patterns, 12ns simulated time, seed509. |
| JUnit guard | Exactly one testcase, no failure/error/skipped element; `TESTS=1 PASS=1 FAIL=0 SKIP=0`. |
| Actual embedded Python / venv | Test measured Python3.12.3 and the selected dedicated venv; matches the launching interpreter. |

The first temporary-fixture attempt failed because an inherited `PWD` pointed to the Windows-mounted project path with spaces. The fixture was corrected to use Make's `CURDIR` and a normalized child `PWD`; the final check above passed. No scheduler issue or result is inferred. The fixture is removed automatically, while invocation logs remain ignored in `.setup-logs/wsl-final-validation-with-runtime.log` and the earlier attempt logs. The activated audit snapshot is `.setup-logs/wsl-activated-environment.json`.

The cocotb wheel prints a `Using Python 3.12.12` startup banner from the compile-time `PY_VERSION` macro ([upstream source](https://raw.githubusercontent.com/cocotb/cocotb/v2.1.0/src/cocotb/share/lib/pygpi/embed.cpp)); it does not report the loaded runtime patch version. The fixture explicitly measured3.12.3 inside the simulator. No distro Python update was needed to address that banner.

SystemC, CDC tooling, cloud dependencies, waveform GUIs, and formal toolchains are not installed by this profile. The full generic RTL Agent Team environment may list them as missing; they are not prerequisites for this project's selected lightweight Verilator/cocotb lint/simulation setup. Formal and CDC scope remain architecture review decisions. Claude Code's plugin is installed on Windows; sourcing this WSL profile does not install a separate WSL Claude CLI or imply a new `rat-setup` invocation.

Commercial synthesis/STA still uses UIUC FastX, with Design Compiler/PrimeTime and SAED32 libraries remaining on the university host. This local installation does not establish FastX connectivity, licensing, remote script execution, or scheduler PPA results. See `FASTX.md` for the separate remote prerequisites and access status.

## Four-state replay checks —2026-10-21 supplement

The power testbench's X-rejection checks additionally use user-local Icarus12.0 on Ubuntu24.04
amd64. This is separate from the original Verilator/cocotb profile and implements no scheduler
in the Icarus fixture. The existing owner authorization covers this small necessary open-source
verification dependency. No system package installation or global PATH change was performed.

Observed package: `iverilog_12.0-2build2_amd64.deb`, SHA-256
`f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667`.
The package was downloaded from Ubuntu noble/universe and unpacked under
`~/.local/opt/cxl-scheduler/iverilog-12.0`. To reproduce that exact user-local installation on
the same distribution/architecture, with the version still available in its configured archive:

```bash
cxl_ivl_cache="$HOME/.cache/cxl-scheduler/iverilog-12.0"
mkdir -p "$cxl_ivl_cache"
(cd "$cxl_ivl_cache" && apt-get download iverilog=12.0-2build2)
(cd "$cxl_ivl_cache" && printf '%s  %s\n' \
  f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667 \
  iverilog_12.0-2build2_amd64.deb | sha256sum -c -)
dpkg-deb -x "$cxl_ivl_cache/iverilog_12.0-2build2_amd64.deb" \
  "$HOME/.local/opt/cxl-scheduler/iverilog-12.0"
```

The test supplies `iverilog -B .../usr/lib/x86_64-linux-gnu/ivl` and `vvp -M` for the relocated
runtime; invoking its binary without those paths initially failed to locate helpers. The
package hash is the observed frozen download, not a claim of a publisher signature.
From the repository root, run:

```bash
source scripts/wsl_env.sh
python -m unittest discover -s scripts -p 'test_power*.py' -v
```

The exporter tests also require the preserved accepted primary-v2 own-design artifacts under
`artifacts/fastx/primary-20261021-v2-{policy}-n{N}/`: manifest, run configuration, mapped netlist
and SDC. They are present in this workspace and retained on FastX; a fresh clone must restore
those accepted artifacts before this power-specific suite. They must not be replaced with
fabricated measurement files. No proprietary cell library/model belongs in that directory.

Independent final local runs used the pending tooling changes on base `4007f99`; their five
code-file hashes match the subsequently committed `43bf975`. WSL22PASS/1explicit Tkinter-Tcl skip;
Windows18PASS/5explicit Linux-simulator skips. The same suite on Windows covers the Tcl-stub
check; WSL covers the actual Verilator and Icarus cases. All23 test cases therefore have an
executed passing platform; the two run totals are not46 unique tests. Test logs and actual
commands remain under `.setup-logs/implementation/power-extension-sol-20261021/`.
These checks validate replay infrastructure, with separate actual commercial gate/power
execution documented in [STATUS](STATUS.md). They do not create a new architecture approval.
