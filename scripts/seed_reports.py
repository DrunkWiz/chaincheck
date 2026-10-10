"""Seed the SYNTHETIC community reports into the configured database.

    python -m scripts.seed_reports

The deployed app does this itself when SEED_DEMO_REPORTS=1, so this is only
needed for local runs. The reports themselves live in backend/demo_seed.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db as database  # noqa: E402
from backend.demo_seed import SYNTHETIC_REPORTS, seed, seed_if_empty  # noqa: E402,F401


def main():
    added = seed_if_empty(database.from_env())
    print(f"Seeded {added} SYNTHETIC reports." if added else "Synthetic reports already present; nothing to do.")


if __name__ == "__main__":
    main()
