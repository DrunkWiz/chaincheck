# ChainCheck

Investment scam checker for Singapore. Paste or upload what an investment offer showed you, and
ChainCheck tells you which claims can't be verified, where you are in the scam playbook, and what
the scammer will ask for next.

*ScamShield protects the inbox. ChainCheck protects the wallet.* ChainCheck links to
[ScamShield](https://www.scamshield.gov.sg/); it does not send ScamShield any data.

Built for WarriorHacks 2.0. Full plan: [docs/BUILD_BRIEF.md](docs/BUILD_BRIEF.md).

## What's real, what's a snapshot, what's synthetic

| Part | Status |
|---|---|
| Checks, verdict, playbook stage, Reality Check | Real code, fixed rules, tested |
| MAS Financial Institutions Directory / Investor Alert List | **Demo data with invented firms** (`data/demo_mas_*.json`) until a real dated snapshot is added. The site shows a demo banner and every MAS flag says "DEMO data" |
| Community reports | **Synthetic**: 12 invented reports (`scripts/seed_reports.py`), labelled on screen |
| Example offers and mock chats | Invented, labelled MOCK |
| Domain age | Live RDAP lookup via rdap.org when deployed; fixtures in tests |
| Accuracy figure | Not yet measured on a real set: see [Accuracy](#accuracy) |

## How it works

**The model reads. Code decides.** The model (Gemini) only extracts entities into a fixed schema and
may add amber "concern" flags. Code also extracts the hard facts itself (links, phones, wallets,
returns, payment requests) and merges them in, so the model can only ever add. Every check, the
verdict, the stage and the next move are deterministic code. Any red or amber flag means **STOP**;
the best possible result is "No red flags found. Verify these yourself before you pay." The app never
says safe, verified or legit.

```
text / screenshots ─▶ model extraction ─┐
                   └▶ code extraction ──┴▶ merge ─▶ follow-up answers ─▶ checks ─▶ verdict ─▶ stage, chain map, Reality Check
```

| Check | Rule (thresholds in `backend/config.py`) |
|---|---|
| MAS licence | Not in FID snapshot: red. On Investor Alert List: red |
| Fuzzy name | ≥ 0.85 similar to a licensed name but not exact: red, looks like a copy |
| Copycat | Licensed name but website/email/phone not on its MAS record: red. No contact details: amber |
| Domain age | < 180 days red, < 365 days amber, lookup failed amber |
| Returns | Annualised `(1+p)^n − 1`: > 30%/yr red, 15–30% amber |
| Fees | Withdrawal "tax", unlock fee, % fee to withdraw: red |
| Payment | Cash handover, gold, crypto to a wallet given: red. Crypto otherwise: amber |
| App | Installed from a link, not an app store: red |
| Lockout | Withdrawal blocked, trading target to withdraw, account "frozen": red |
| Fund recovery | Offer to recover lost money: red |
| Claimed titles | Professor, analyst, fund manager: amber |
| Text aimed at AI | "Ignore your instructions…": red |
| Community network | Entity in approved reports: red. Licensed firms are never flagged from reports alone |
| AI concerns | Amber, labelled as AI, reason withheld if it tries to reassure |

## Run it locally

Needs Python 3.11+ and Node 20+.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
```

```bash
cd frontend && npm install && npm run build
```

```bash
.venv/Scripts/python -m scripts.seed_reports
```

```bash
.venv/Scripts/python -m backend.server
```

Open http://localhost:8000. For front-end work, also run `npm run dev` in `frontend/` (it proxies
`/api` to port 8000). On macOS/Linux use `.venv/bin/python`.

Without `GEMINI_API_KEY` the checker runs on code-side extraction only and says so on screen;
screenshot upload needs the key. Copy `.env.example` to `.env` (or export the variables) to configure.

## Tests

```bash
.venv/Scripts/python -m pytest -q
```

No network: a fake model gateway, fixture snapshots and fixture RDAP answers. Any attempt to open a
socket fails the test run. The injection fixture is run against an honest fake *and* a hijacked fake
that returns empty, hostile output; the verdict must not change.

## Accuracy

```bash
.venv/Scripts/python -m scripts.run_accuracy
```

`tests/fixtures/accuracy_set/` has 20 scam and 20 legitimate **invented** offers. Code-only mode
currently stops 19 of 20 scams with 4 false alarms on 20 legitimate offers. **Don't quote this
number**: the set was written by the same person as the rules. Before freeze, replace it with offers
written by someone else and modelled on real cases and real licensed-firm promotions, run it with
`--mode live`, and quote only that result with its size.

## Deploy (Vercel)

`vercel.json` builds the front end and routes `/api/*` to `api/index.py` (stdlib, no framework).
Set **every** variable from `.env.example` in the Vercel dashboard. Community reports need Turso
(`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`) because Vercel's filesystem doesn't keep writes; seed it
once by running `scripts.seed_reports` locally with those variables set. Checked against Vercel's docs (6 Oct): `api/index.py` exposes a `handler` class, which Vercel's
Python runtime supports; the rewrite passes the route as `__route` so routing works either way. Still
untested until the first deploy.

## Layout

```
backend/   api.py server.py pipeline.py extract.py code_extract.py schema.py prompt.py
           checks/ providers/ verdict.py playbook.py followups.py reality.py redact.py db.py community.py
api/       index.py (Vercel entry)
data/      demo MAS snapshots, benchmarks
frontend/  React + Vite
scripts/   seed_reports.py snapshot_mas.py run_accuracy.py
tests/     fixtures/offers, fixtures/model_outputs, fixtures/accuracy_set
```
