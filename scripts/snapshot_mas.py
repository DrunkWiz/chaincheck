"""Turn a MAS list you downloaded yourself into a dated snapshot in data/.

Check MAS's website terms before downloading. This script never fetches
anything: it only converts a CSV you saved.

    python -m scripts.snapshot_mas fid path/to/fid_export.csv --date 2026-10-06
    python -m scripts.snapshot_mas ial path/to/alert_list.csv --date 2026-10-06

Columns are matched by name, case-insensitively; pass --name-col etc. if
MAS's headers differ.
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = {
    "fid": "MAS Financial Institutions Directory (https://eservices.mas.gov.sg/fid), downloaded by hand",
    "ial": "MAS Investor Alert List (https://www.mas.gov.sg/investor-alert-list), downloaded by hand",
}
GUESSES = {
    "name": ("organisation name", "name", "institution name", "entity name", "unregulated person"),
    "website": ("website", "websites", "web address", "url"),
    "phone": ("phone", "phone number", "telephone", "contact number"),
    "email": ("email", "email address"),
    "licence": ("licence type", "license type", "sector", "licence"),
}


def _column(headers, wanted, override):
    if override:
        return override
    lower = {h.lower().strip(): h for h in headers}
    for guess in GUESSES[wanted]:
        if guess in lower:
            return lower[guess]
    return None


def _split(value):
    return [v.strip() for v in re.split(r"[;,\n]| / ", value or "") if v.strip()]


def convert(kind, rows, headers, snapshot_date, cols):
    name_col = _column(headers, "name", cols.get("name"))
    if not name_col:
        raise SystemExit(f"Couldn't find a name column in {headers}. Use --name-col.")
    web, phone, email, licence = (_column(headers, k, cols.get(k)) for k in ("website", "phone", "email", "licence"))
    records = []
    for row in rows:
        name = (row.get(name_col) or "").strip()
        if not name:
            continue
        record = {"name": name, "websites": _split(row.get(web)) if web else []}
        if kind == "fid":
            record["licence"] = (row.get(licence) or "").strip() if licence else ""
            record["phones"] = _split(row.get(phone)) if phone else []
            record["email_domains"] = [e.split("@")[-1] for e in _split(row.get(email))] if email else []
        records.append(record)
    key = "institutions" if kind == "fid" else "entries"
    return {"snapshot_date": snapshot_date, "source": SOURCES[kind], key: records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=("fid", "ial"))
    parser.add_argument("csv_path")
    parser.add_argument("--date", default=date.today().isoformat(), help="date you downloaded it")
    for col in GUESSES:
        parser.add_argument(f"--{col}-col")
    args = parser.parse_args(argv)
    with open(args.csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        snapshot = convert(args.kind, list(reader), reader.fieldnames or [], args.date,
                           {c: getattr(args, f"{c}_col") for c in GUESSES})
    out = DATA / f"mas_{args.kind}_{args.date}.json"
    out.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8")
    count = len(snapshot.get("institutions") or snapshot.get("entries"))
    print(f"Wrote {count} records to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
