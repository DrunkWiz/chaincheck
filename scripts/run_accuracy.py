"""Run the accuracy set (docs/BUILD_BRIEF.md §12) and report hits and false alarms.

    python -m scripts.run_accuracy                # code-only extraction, offline
    python -m scripts.run_accuracy --mode live    # with the model (needs GEMINI_API_KEY)

Quote only the number from the mode you actually ship, with the set size.
Domain ages come from accuracy_set/rdap.json so runs are repeatable.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import pipeline, snapshots  # noqa: E402
from backend.verdict import STOP  # noqa: E402

SET_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "accuracy_set"


def load_set(set_dir=SET_DIR):
    offers = json.loads((set_dir / "offers.json").read_text(encoding="utf-8"))["offers"]
    rdap = {d: date.fromisoformat(v) for d, v in
            json.loads((set_dir / "rdap.json").read_text(encoding="utf-8")).items()}
    fid = snapshots.load_file(next(set_dir.glob("mas_fid_*.json")), "fid")
    ial = snapshots.load_file(next(set_dir.glob("mas_ial_*.json")), "ial")
    return offers, rdap, fid, ial


def run(provider=None, set_dir=SET_DIR, today=date(2026, 10, 12)):
    offers, rdap, fid, ial = load_set(set_dir)
    rows = []
    for offer in offers:
        ctx = pipeline.make_context(today=today, rdap=rdap.get, fid=fid, ial=ial, secret="accuracy")
        result = pipeline.analyze(offer["text"], provider, ctx)
        rows.append({
            "id": offer["id"], "label": offer["label"], "verdict": result.verdict,
            "rules": sorted({f.rule for f in result.flags}),
        })
    scams = [r for r in rows if r["label"] == "scam"]
    legit = [r for r in rows if r["label"] == "legit"]
    return {
        "hits": sum(r["verdict"] == STOP for r in scams), "scams": len(scams),
        "false_alarms": sum(r["verdict"] == STOP for r in legit), "legit": len(legit),
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("code-only", "live"), default="code-only")
    args = parser.parse_args(argv)
    provider = None
    if args.mode == "live":
        from backend.providers.gemini import default_chain
        provider = default_chain()
    report = run(provider)
    for row in report["rows"]:
        wrong = (row["label"] == "scam") != (row["verdict"] == STOP)
        print(f"{'MISS ' if wrong else '     '}{row['id']:<10} {row['label']:<6} {row['verdict']:<13} {', '.join(row['rules'])}")
    print()
    print(f"Mode: {args.mode}")
    print(f"Scams stopped: {report['hits']} of {report['scams']}")
    print(f"False alarms on legitimate offers: {report['false_alarms']} of {report['legit']}")


if __name__ == "__main__":
    main(sys.argv[1:])
