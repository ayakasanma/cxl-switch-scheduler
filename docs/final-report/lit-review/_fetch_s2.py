import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
D = json.loads((BASE / "_fetch_meta.json").read_text(encoding="utf-8"))

out = {}
for doi in D:
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/DOI:"
        + urllib.parse.quote(doi, safe="")
        + "?fields=title,abstract,year,venue,authors,externalIds,openAccessPdf"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ECE509-lit-review/1.0"}
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            out[doi] = json.load(r)
    except Exception as e:
        out[doi] = {"error": str(e)}
    time.sleep(0.3)

(BASE / "_s2_meta.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
for doi, x in out.items():
    print(
        doi,
        "|",
        x.get("title"),
        "| abstract?",
        bool(x.get("abstract")),
        "| err",
        x.get("error", ""),
    )
    if x.get("abstract"):
        print("   ", x["abstract"][:500].replace("\n", " "))
