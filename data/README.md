# data/

- `mas_fid_YYYY-MM-DD.json`, `mas_ial_YYYY-MM-DD.json`: real MAS snapshots, made with
  `scripts/snapshot_mas.py` from files you download yourself (check MAS's site terms first).
  **None are committed yet.**
- `demo_mas_*.json`: invented firms used until a real snapshot exists. Every flag based on
  them says "DEMO data, invented firms", and the UI shows a demo banner.
- `benchmarks.json`: comparison figures for the Reality Check chart, each with its source.

The newest real snapshot always wins over a demo one. Snapshots are never presented as live.
