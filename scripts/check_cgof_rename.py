"""Compare current model pins/state against an immutable archived model."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "refc"))
from cxl_model.experimental import ExperimentalSwitchModel


def compare(archive_path, cycles=2048):
    if type(cycles) is not int or cycles < 1:
        raise ValueError("positive cycle count required")
    with tempfile.TemporaryDirectory(prefix="cgof-model-audit-") as folder:
        package = Path(folder) / "archived_model"
        package.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                path = Path(member)
                if path.parent.as_posix() == "refc/cxl_model" and path.suffix == ".py":
                    (package / path.name).write_bytes(archive.read(member))
        spec = importlib.util.spec_from_file_location(
            "archived_model", package / "__init__.py",
            submodule_search_locations=[str(package)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        from archived_model.experimental import ExperimentalSwitchModel as Archived
        checked = []
        # Archive identifiers are inputs to the comparison, never display labels.
        for n in (4, 8, 16):
            for window in (64, 256):
                for archived_policy, method, weight in (
                    ("DAC1", "CGOF", 1), ("DAC2", "CGOF", 2),
                    ("Main", "FAI-inspired", 2),
                ):
                    old = Archived(n, archived_policy, window)
                    new = ExperimentalSwitchModel(n, method, window, high_weight=weight)
                    for model in (old, new):
                        model.commit(rst_n=False)
                        model.deposit_counter((1 << 32) - 64)
                    rng = random.Random(f"cgof-rename:{n}:{window}:{method}:{weight}")
                    pending = [None] * n
                    for k in range(cycles):
                        for h in range(n):
                            if pending[h] is None and rng.random() < (.85 if h == 0 else .12):
                                pending[h] = rng.getrandbits(105)
                        ready = rng.random() > .2 and not window-3 <= k % (2*window) < window+9
                        left, right = old.view(ready), new.view(ready)
                        if left != right:
                            raise AssertionError((n, window, method, weight, k, "pin mismatch"))
                        valid = [x is not None for x in pending]
                        desc = [x or 0 for x in pending]
                        a, b = old.commit(ready, valid, desc), new.commit(ready, valid, desc)
                        if (a != b or old.cls != new.cls or old.credits != new.credits
                                or old.service != new.service or old.window_state() != new.window_state()):
                            raise AssertionError((n, window, method, weight, k, "state mismatch"))
                        for h in range(n):
                            if valid[h] and left.in_ready[h]:
                                pending[h] = None
                    checked.append(dict(n_src=n, window=window, method=method,
                                        high_low=f"{weight}:1" if method == "CGOF" else None,
                                        cycles=cycles, status="PASS"))
    return dict(status="PASS", evidence_kind="MODEL_DIFFERENTIAL",
                archive_sha256=hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
                current_source_sha256=hashlib.sha256(
                    (ROOT / "refc/cxl_model/experimental.py").read_bytes()).hexdigest(),
                configurations=checked, cycles=sum(r["cycles"] for r in checked),
                production_performance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=2048)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be fresh")
    result = compare(args.archive, args.cycles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        out.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status=result["status"], cycles=result["cycles"])))


if __name__ == "__main__":
    main()
