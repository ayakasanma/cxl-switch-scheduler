import json
import pathlib
import re
import time

import requests


DOIS = [
    "10.1109/isca66397.2026.00060",
    "10.1145/3605181.3626287",
    "10.1109/ipdps64566.2025.00097",
    "10.14778/3746405.3746432",
    "10.3390/mi14112100",
    "10.3390/app122312458",
    "10.1145/3772724",
    "10.4230/LIPIcs.ECRTS.2021.2",
    "10.1109/tcad.2025.3607145",
    "10.1109/lca.2026.3673181",
]

OUT = pathlib.Path(__file__).with_name("selected_crossref.json")


def clean_markup(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def main():
    records = {}
    for doi in DOIS:
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "CXL-report-bibliography/1.0 (mailto:research@example.com)"},
            timeout=30,
        )
        record = {
            "doi": doi,
            "crossref_status": response.status_code,
            "crossref_url": f"https://api.crossref.org/works/{doi}",
        }
        if response.ok:
            message = response.json()["message"]
            record.update(
                {
                    "title": (message.get("title") or [""])[0],
                    "authors": [
                        f"{author.get('given', '')} {author.get('family', '')}".strip()
                        for author in message.get("author", [])
                    ],
                    "container": (message.get("container-title") or [""])[0],
                    "publisher": message.get("publisher"),
                    "type": message.get("type"),
                    "volume": message.get("volume"),
                    "issue": message.get("issue"),
                    "page": message.get("page"),
                    "issued": message.get("issued", {}).get("date-parts"),
                    "doi_url": message.get("URL"),
                    "publisher_url": (message.get("resource") or {})
                    .get("primary", {})
                    .get("URL"),
                    "abstract": clean_markup(message.get("abstract")),
                }
            )
        else:
            record["error"] = response.text[:500]
        records[doi] = record
        print(json.dumps({doi: record}, ensure_ascii=False, indent=1)[:5000])
        time.sleep(0.4)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
