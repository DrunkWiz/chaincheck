# Test fixtures — all invented

Every firm, person, phone number, wallet and domain in this folder is invented
for tests. Domains use the reserved `.example` TLD. The MAS files in `mas/` are
**not MAS data**; they imitate the snapshot format with fictional firms.
Don't reuse these phone numbers in public demo data without checking they're
unallocated.

- `offers/` — the four offer texts. Modelled on the CNA case patterns, not transcribed.
- `model_outputs/` — what an honest model should extract from each offer. The
  fake gateway replays these.
- `expected_verdicts.json` — the verdict each offer must get.
- `accuracy_set/` — 20 scam + 20 legitimate offers, filled in before freeze day.
