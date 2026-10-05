"""Vercel Python entry point: every /api/* request is routed here (vercel.json)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.server import Handler as handler  # noqa: E402,F401  (Vercel looks for `handler`)
