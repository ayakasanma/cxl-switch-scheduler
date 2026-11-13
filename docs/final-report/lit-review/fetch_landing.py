import json
import re
import sys
import time
from pathlib import Path

import requests


DOIS = sys.argv[1:] or [
    "10.1109/isca66397.2026.00060",
    "10.1145/3713082.3730393",
    "10.1109/tpds.2025.3598190",
    "10.1145/3695794.3695809",
    "10.1109/fccm57271.2023.00017",
    "10.1109/pact65351.2025.00018",
    "10.1109/lca.2026.3673181",
    "10.1145/3772724",
    "10.3390/mi14112100",
    "10.1145/3544216.3544223",
    "10.14778/3748191.3748225",
    "10.1109/tcad.2025.3607145",
]

OUT = Path(__file__).with_name("landing_pages.json")
META_RE = re.compile(
    r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\']([^"\']+)["\'][^>]*?'
    r'content\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE | re.DOTALL,
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def main():
    out = {}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    for doi in DOIS:
        url = f"https://doi.org/{doi}"
        record = {"doi": doi, "requested_url": url}
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=45,
                allow_redirects=True,
            )
            text = response.text
            metas = {}
            for name, content in META_RE.findall(text):
                metas.setdefault(name.lower(), []).append(clean(content))
            title = TITLE_RE.search(text)
            record.update(
                {
                    "status": response.status_code,
                    "final_url": response.url,
                    "title_tag": clean(title.group(1)) if title else None,
                    "meta": metas,
                }
            )
            interesting = {
                k: v
                for k, v in metas.items()
                if k.startswith("citation_")
                or k
                in {
                    "description",
                    "og:title",
                    "og:description",
                    "dc.title",
                    "dc.description",
                }
            }
            print(f"\n=== {doi} -> {response.status_code} {response.url} ===")
            print(json.dumps(interesting, ensure_ascii=False, indent=1)[:9000])
        except Exception as exc:  # noqa: BLE001
            record["error"] = repr(exc)
            print(f"\n=== {doi} ERROR {exc!r} ===")
        out[doi] = record
        time.sleep(1.0)

    with OUT.open("w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
