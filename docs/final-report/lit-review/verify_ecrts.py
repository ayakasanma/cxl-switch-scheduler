import json
import re

import requests


DOI = "10.4230/LIPIcs.ECRTS.2021.2"
LANDING = f"https://drops.dagstuhl.de/entities/document/{DOI}"


def meta_value(html, name):
    pattern = (
        rf'<meta\s+[^>]*name=["\']{re.escape(name)}["\'][^>]*'
        rf'content=["\']([^"\']*)["\']'
    )
    return re.findall(pattern, html, re.IGNORECASE)


def main():
    datacite = requests.get(f"https://api.datacite.org/dois/{DOI}", timeout=30)
    attributes = datacite.json()["data"]["attributes"]
    record = {
        "doi": DOI,
        "datacite_status": datacite.status_code,
        "datacite_url": f"https://api.datacite.org/dois/{DOI}",
        "title": attributes.get("titles", [{}])[0].get("title"),
        "creators": [
            creator.get("name") for creator in attributes.get("creators", [])
        ],
        "publisher": attributes.get("publisher"),
        "publication_year": attributes.get("publicationYear"),
        "types": attributes.get("types"),
        "url": attributes.get("url"),
        "container": attributes.get("container"),
        "dates": attributes.get("dates"),
    }
    html = requests.get(
        LANDING, headers={"User-Agent": "Mozilla/5.0"}, timeout=30
    ).text
    for name in [
        "citation_title",
        "citation_author",
        "citation_publication_date",
        "citation_firstpage",
        "citation_lastpage",
        "citation_doi",
        "citation_journal_title",
        "citation_volume",
        "citation_pdf_url",
        "citation_abstract",
    ]:
        record[name] = meta_value(html, name)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    output = (
        __import__("pathlib").Path(__file__).with_name("ecrts_metadata.json")
    )
    output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
