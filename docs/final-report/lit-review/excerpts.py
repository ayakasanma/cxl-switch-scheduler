import pathlib


BASE = pathlib.Path(__file__).resolve().parent / "fulltexts"
WINDOWS = {
    "ecrts2021.txt": [(1, 35), (495, 540), (725, 755)],
    "qgwfqs.txt": [(1, 60), (585, 625), (745, 805), (865, 880)],
    "fsa.txt": [(1, 60), (555, 600), (700, 792), (843, 930)],
}


def main():
    for name, windows in WINDOWS.items():
        lines = (BASE / name).read_text(encoding="utf-8").splitlines()
        print(f"\n######## {name} ########")
        for start, end in windows:
            print(f"\n--- lines {start}-{end} ---")
            for number in range(start, min(end, len(lines)) + 1):
                print(f"{number}: {lines[number - 1].strip()[:240]}")


if __name__ == "__main__":
    main()
