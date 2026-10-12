"""Load dated MAS snapshots (docs/BUILD_BRIEF.md §7).

Real snapshots are `mas_fid_YYYY-MM-DD.json` / `mas_ial_YYYY-MM-DD.json`.
Until one is committed, the invented `demo_mas_*` files are used and every
flag says so.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend import normalize

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATED = re.compile(r"(\d{4}-\d{2}-\d{2})\.json$")


@dataclass(frozen=True)
class Firm:
    name: str
    key: str               # normalised name
    licence: str
    websites: frozenset
    phones: frozenset
    email_domains: frozenset


@dataclass(frozen=True)
class Snapshot:
    kind: str              # "fid" or "ial"
    date: str
    source: str
    demo: bool
    firms: tuple

    @property
    def label(self):
        name = "MAS Financial Institutions Directory" if self.kind == "fid" else "MAS Investor Alert List"
        prefix = "DEMO data, invented firms, not " if self.demo else ""
        return f"{prefix}{name} snapshot, {self.date}"

    @property
    def invented(self):
        """The demo list of invented firms. Real firms aren't in it, so code mustn't say a firm
        missing from it is unlicensed. (Test fixtures behave like a real snapshot.)"""
        return self.source.upper().startswith("DEMO")


def parse(raw, kind, demo=False):
    records = raw.get("institutions") if kind == "fid" else raw.get("entries")
    firms = []
    for record in records or []:
        firms.append(Firm(
            name=record["name"],
            key=normalize.company(record["name"]),
            licence=record.get("licence", ""),
            websites=frozenset(normalize.domain(w) for w in record.get("websites", [])),
            phones=frozenset(normalize.phone(p) for p in record.get("phones", [])),
            email_domains=frozenset(normalize.domain(d) for d in record.get("email_domains", [])),
        ))
    return Snapshot(kind, raw["snapshot_date"], raw.get("source", ""), demo, tuple(firms))


def load_file(path, kind):
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    demo = path.name.startswith("demo_") or raw.get("source", "").upper().startswith(("FIXTURE", "DEMO"))
    return parse(raw, kind, demo)


def latest_path(kind, data_dir=DATA_DIR):
    """Newest real snapshot, else newest demo snapshot."""
    for prefix in (f"mas_{kind}_", f"demo_mas_{kind}_"):
        dated = sorted(
            (m.group(1), p) for p in Path(data_dir).glob(f"{prefix}*.json")
            if (m := _DATED.search(p.name)) and p.name.startswith(prefix)
        )
        if dated:
            return dated[-1][1]
    raise FileNotFoundError(f"no MAS {kind} snapshot in {data_dir}")


@lru_cache(maxsize=4)
def load_latest(kind, data_dir=DATA_DIR):
    return load_file(latest_path(kind, data_dir), kind)
