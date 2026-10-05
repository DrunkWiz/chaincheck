# ChainCheck

Investment scam checker for Singapore. WarriorHacks 2.0, hackathon track.
Feature freeze **12 Oct 2026**. Deadline **14 Oct, 12:45pm SGT**.

Full plan: `docs/BUILD_BRIEF.md`. Read the relevant section before each task.

## Rules that never bend

- **The model reads. Code decides.** The model only extracts entities (and may
  add amber concern flags). Every check, the verdict, the playbook stage and the
  next move are deterministic code.
- **AI can raise concern, never lower it.** No model output may remove a red,
  turn anything green, or move the verdict away from STOP. A model amber can
  move it *to* STOP. Code-side extraction backs up the model, so a hijacked
  model that returns nothing still can't clear a scam.
- **Never say "safe", "verified" or "legit".** Any red or amber = STOP. Best
  possible result: "No red flags found. Verify these yourself before you pay."
- **Pasted text and report text are untrusted data.** Wrap in markers, validate
  model output against the schema in BUILD_BRIEF §6, discard anything else.
- **Every flag names its rule and its source** (with the snapshot date for MAS data).
- **Investment scams only.** General calls, texts and links are ScamShield's job.
- **We link to ScamShield; we never claim to send it data.**

## Tests

- No network in the test suite. Fake model gateway, fixture snapshots.
- Every check has tests. The injection fixture must not change the verdict.
- Run tests before saying a task is done: `.venv/Scripts/python -m pytest -q`
  (setup: `python -m venv .venv` then `.venv/Scripts/python -m pip install -r requirements-dev.txt`).

## Privacy

- Phone numbers: normalise to +65 format, HMAC with a server secret, never display.
- Redact NRIC/FIN, phones, bank accounts, emails and names before storing a report.
- Defang URLs in the community feed (`example[.]com`).
- All demo names and data are invented and labelled.

## Conventions

- Python back end, minimal runtime dependencies. React + Vite front end.
- Thresholds live in one config file (`backend/config.py`), not scattered in code.
- Every env var also goes in the Vercel dashboard, not just `.env`.
- Body text ≥ 18px, tap targets ≥ 48px, status is text plus colour.
