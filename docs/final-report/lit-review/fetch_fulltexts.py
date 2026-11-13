import json
import pathlib

import fitz
import requests


BASE = pathlib.Path(__file__).resolve().parent / "fulltexts"
BASE.mkdir(exist_ok=True)

URLS = {
    "ecrts2021.pdf": (
        "https://drops.dagstuhl.de/storage/00lipics/lipics-vol196-ecrts2021/"
        "LIPIcs.ECRTS.2021.2/LIPIcs.ECRTS.2021.2.pdf"
    ),
    "opendram.pdf": "https://dl.acm.org/doi/pdf/10.1145/3772724",
}


def main() -> None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0 Safari/537.36"
        ),
        "Accept": "application/pdf,text/html,*/*",
    }
    report = {}
    for name, url in URLS.items():
        response = requests.get(
            url, headers=headers, timeout=60, allow_redirects=True
        )
        record = {
            "url": url,
            "status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "final_url": response.url,
            "bytes": len(response.content),
        }
        path = BASE / name
        path.write_bytes(response.content)
        if response.content[:4] == b"%PDF":
            document = fitz.open(path)
            text = "\n".join(page.get_text() for page in document)
            (BASE / f"{path.stem}.txt").write_text(text, encoding="utf-8")
            record["pages"] = len(document)
            record["chars"] = len(text)
        report[name] = record
        print(json.dumps({name: record}, ensure_ascii=False))
    (BASE / "download_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
