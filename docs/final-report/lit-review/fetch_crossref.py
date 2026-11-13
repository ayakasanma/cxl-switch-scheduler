import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


DOIS = [
    "10.1109/isca66397.2026.00060",
    "10.1145/3713082.3730393",
    "10.1109/tpds.2025.3598190",
    "10.1145/3695794.3695809",
    "10.1109/fccm57271.2023.00017",
    "10.1109/pact65351.2025.00018",
    "10.1109/lca.2026.3673181",
    "10.1016/j.future.2020.01.047",
    "10.1145/3605181.3626287",
    "10.1145/3764862.3768173",
    "10.1109/lca.2025.3621612",
    "10.1145/3723851.3723858",
    "10.1109/tcad.2025.3607145",
]

OUT = Path(__file__).with_name("candidates_crossref.json")
HEADERS = {"User-Agent": "CXL-lit-verifier/1.0 (mailto:USER@illinois.edu)"}


def author_name(author):
    name = " ".join(
        part for part in [author.get("given"), author.get("family")] if part
    )
    return name or author.get("name", "")


def main():
    out = {}
    for doi in DOIS:
        url = (
            "https://api.crossref.org/works/"
            + urllib.parse.quote(doi, safe="/")
            + "?mailto=USER@illinois.edu"
        )
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)["message"]
            record = {
                "doi": data.get("DOI"),
                "title": (data.get("title") or [""])[0],
                "authors": [author_name(a) for a in data.get("author", [])],
                "container": (data.get("container-title") or [""])[0],
                "publisher": data.get("publisher"),
                "type": data.get("type"),
                "volume": data.get("volume"),
                "issue": data.get("issue"),
                "page": data.get("page"),
                "published": data.get("published", {}).get("date-parts"),
                "issued": data.get("issued", {}).get("date-parts"),
                "URL": data.get("URL"),
                "abstract": data.get("abstract"),
                "event": data.get("event"),
            }
            out[doi] = record
            print(f"\n=== {doi} ===")
            print(json.dumps(record, ensure_ascii=False, indent=1)[:7000])
        except Exception as exc:  # noqa: BLE001
            print(f"\n=== {doi} ERROR {exc!r} ===")
            out[doi] = {"error": str(exc)}
        time.sleep(0.8)

    with OUT.open("w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(out)} records to {OUT}")


if __name__ == "__main__":
    main()
