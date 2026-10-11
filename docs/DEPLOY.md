# Deploy runbook

**Current deployment: Render**, service `chaincheck` in "My Workspace", Singapore region, free plan:
https://chaincheck-dxj5.onrender.com (dashboard: https://dashboard.render.com/web/srv-db5d4jflot8c73ehqrrg).
It auto-deploys every push to `master`. The Vercel route below still works as an alternative.

## Render (current)

One Python web service builds the front end and serves it with the API (`backend/server.py`).

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && cd frontend && npm ci && npm run build` |
| Start command | `python -m backend.server` (listens on `0.0.0.0:$PORT` when `RENDER` is set) |
| `SEED_DEMO_REPORTS` | `1` |
| `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash` / `gemini-3.5-flash-lite` |
| `PHONE_HMAC_SECRET` | add in **Environment**, use **Generate** |
| `ADMIN_TOKEN` | add in **Environment**, use **Generate**, keep a copy for `/#/admin` |
| `GEMINI_API_KEY` | add in **Environment**: your free Google AI Studio key |
| `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` | optional, keeps shared stories (below) |

### Keep shared stories: Turso in the browser, no CLI

1. Sign up at https://app.turso.tech (the free plan is enough; signing in with GitHub is quickest).
2. Create a database named `chaincheck`. Pick the location closest to Singapore that's offered.
3. On the database's page, copy its URL (it starts with `libsql://`). That's `TURSO_DATABASE_URL`.
4. On the same page, create a token with read and write access and no expiry. Copy it straight into
   Render; it's `TURSO_AUTH_TOKEN`. Don't paste it into chat or git.
5. Render → `chaincheck` → **Environment**: add both variables and save. Saving redeploys.

On the first start the app creates its tables and adds the 12 synthetic reports. After that,
stories survive sleeps and redeploys. Keep `PHONE_HMAC_SECRET` unchanged from then on.

### Reports are screened automatically

A shared story is published straight away when code finds no reason to hold it (instructions aimed
at AI, a MAS-licensed firm named, a repeat, more than 10 auto-published in the hour) **and** the
Gemini screen raises no concern. Otherwise it waits in `/#/admin`, with the reasons. Without
`GEMINI_API_KEY`, or when Gemini fails, every story waits. `/#/admin` also lists auto-published
stories so you can take one down.

Saving environment variables redeploys the service.

**Free-plan limits to know:**

- The service sleeps after 15 minutes without traffic and takes about a minute to wake. Open the
  site a minute before a demo or judging slot.
- The disk is temporary: the SQLite database is wiped when the service sleeps, restarts or
  redeploys. The 12 synthetic reports are re-added automatically on the next start, but **shared
  stories are lost**. For persistence, add Turso (`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`) and
  redeploy; the app uses it automatically.
- Without `PHONE_HMAC_SECRET`, offers containing phone numbers get "isn't fully set up yet" and the
  demo reports aren't seeded. The app never falls back to the dev secret on Render.

**Check it after a deploy:**

```bash
curl https://chaincheck-dxj5.onrender.com/api/meta
```

```bash
python -m scripts.run_accuracy --api https://chaincheck-dxj5.onrender.com
```

The second runs the 40 invented offers through the live site and reports how many were answered by
fixed rules only (Gemini unavailable). Render's **Logs** tab shows "AI reader unavailable" with the
error type, or "model output had N invalid part(s)" with field names. Message text is never logged.

---

## Vercel (alternative)

## 1. Make two secrets

You need two long random values. Keep them in a password manager, not in chat or git. Any one of
these works:

```bash
openssl rand -base64 32
```

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

(Windows: `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"`)

Run it twice:

- the first value is `PHONE_HMAC_SECRET`
- the second is `ADMIN_TOKEN`

> **Never change `PHONE_HMAC_SECRET` after the first deploy.** Phone numbers and bank accounts are
> stored only as HMACs made with it. A new secret means none of them match any more.

## 2. Gemini key (free tier)

1. In Google AI Studio, create an API key. No billing is needed.
2. That value is `GEMINI_API_KEY`.

On the free tier, Google uses what it receives to improve its products, and human reviewers may
read it. To limit that, ChainCheck removes phone numbers, emails, NRIC/FIN, account numbers and
"my name is …" from the text before sending it (`redact.for_model`). Code reads those details from
the original text itself. **Screenshots never reach Gemini or the server:** they're read in the
browser with Tesseract (OCR), and the text goes into the paste box for the user to review. The page
tells users their text (not their screenshots) goes to Google. If you later move to a paid key,
update that notice.

The OCR engine and English data (~15 MB) load from the jsDelivr CDN the first time someone adds a
screenshot, then stay cached in their browser. Only those static files are downloaded; images are
never uploaded.

Free-tier rate limits are low. If the model is rate-limited, checks fall back to fixed rules and
say so on screen. They don't fail.

The model defaults are `gemini-3.5-flash`, with `gemini-3.5-flash-lite` as the fallback. Both were
checked against Google's model list on 6 Oct 2026.

## 3. Create the Vercel project

1. In Vercel, go to **Add New → Project** and import `DrunkWiz/chaincheck`. The repo is private, so
   allow Vercel's GitHub app access to it.
2. Leave **Root directory** as the repo root and leave build and output settings empty.
   `vercel.json` defines two **Services**: `web` (the Vite front end) and `api` (the Python back end,
   `backend/wsgi.py`). If Vercel asks for a framework preset, pick **Services** if it's offered,
   otherwise **Other**.
3. Under **Environment Variables**, add these six for **Production**:

   | Variable | Value |
   |---|---|
   | `PHONE_HMAC_SECRET` | from step 1 |
   | `ADMIN_TOKEN` | from step 1 |
   | `GEMINI_API_KEY` | from step 2 |
   | `GEMINI_MODEL` | `gemini-3.5-flash` |
   | `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |
   | `SEED_DEMO_REPORTS` | `1` |

   `SEED_DEMO_REPORTS` adds the 12 labelled synthetic reports automatically the
   first time the app starts on an empty database.
4. Click **Deploy**. Checks work straight away. The community pages say "unavailable" until step 4
   is done.

## 4. Add the database from Vercel (Turso, no CLI)

1. In your new project, open the **Storage** tab and choose to create or connect a database.
2. Pick **Turso Cloud** from the Marketplace list and install it. Choose the **free plan**, and the
   region closest to Singapore if you're offered one.
3. Connect it to the `chaincheck` project. The integration adds `TURSO_DATABASE_URL` and
   `TURSO_AUTH_TOKEN` to the project's environment variables for you. Check they're there under
   **Settings → Environment Variables**.
4. **Redeploy** (**Deployments → … → Redeploy**), because new variables only apply to new deployments.

The tables are created and the synthetic reports added on the first request after that. There's no
migration or seeding step.

## 5. Smoke test the live site

Replace `<site>` with your deployment URL.

```bash
curl https://<site>/api/meta
```

Expect JSON with `"demo": true` until a real MAS snapshot is committed.

```bash
curl -s -X POST https://<site>/api/analyze -H "Content-Type: application/json" -d '{"text": "Earn 3% per day. Our courier will collect cash."}'
```

Expect `"verdict": "STOP"` and `"degraded": false`. If `degraded` is `true`, Gemini isn't answering.
See the troubleshooting section.

(Windows PowerShell: `Invoke-RestMethod -Method Post -Uri https://<site>/api/analyze -ContentType "application/json" -Body '{"text": "Earn 3% per day. Our courier will collect cash."}' | Select-Object verdict, summary, degraded`)

Then in a browser:

- [ ] Home page loads with the demo banner. Run each of the three invented examples.
- [ ] The copycat example shows a "Seen in 1 scam report" flag. That proves the database is
      connected and seeded.
- [ ] Add a screenshot of an invented offer. Its text appears in the box within a few seconds; check it.
- [ ] Community page shows 12 synthetic reports and a 9-report network alert.
- [ ] Share an invented test story. It's published, or held with a reason; either way it shows in
      `/#/admin` with your `ADMIN_TOKEN`. Take it down or reject it.
- [ ] Phone width (375px): no sideways scrolling on any page.

## 6. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Build fails with "pattern `api/index.py` doesn't match any Serverless Functions" | An old commit. Python files in `api/` aren't built for new Vercel projects; the app now deploys as Services. Redeploy the latest commit |
| `/api/...` returns 404 or the HTML page | The services rewrites didn't apply. Check `vercel.json` is at the repo root and the project's root directory is the repo root |
| Offers with a phone number get "ChainCheck isn't fully set up yet" (503); logs say `PHONE_HMAC_SECRET must be set` | Variable missing in Vercel. Offers without phone numbers still get checked. The app refuses to use the dev default on purpose |
| Results say "AI reader wasn't available" | `GEMINI_API_KEY` missing or wrong, free-tier rate limit hit, or a model ID retired. Check the function logs: errors show as `HTTP 4xx` from `gemini:<model>` |
| "Community reports are unavailable right now" | Turso variables missing (step 4), or you didn't redeploy after adding them |
| Community page is empty | `SEED_DEMO_REPORTS` isn't `1`, or wasn't set when the database was first used. Set it and redeploy: seeding runs whenever no synthetic reports exist |
| Copycat example doesn't show "Seen in 1 scam report" | `PHONE_HMAC_SECRET` was changed after the reports were seeded. Put the original value back, or ask me how to clear the tables and reseed |
| Build fails at `npm ci` | `frontend/package-lock.json` missing or out of date. Run `npm install` in `frontend/` and commit the lock file |

Logs: in the Vercel dashboard, open **Project → Logs**. The app never logs request bodies.

## 7. Roll back

Promote a previous deployment from **Project → Deployments → … → Promote**.

## 8. When real MAS snapshots arrive

1. Check MAS's site terms. Download the FID and Investor Alert List by hand.
2. Convert each one:

   ```bash
   .venv/bin/python -m scripts.snapshot_mas fid <file>.csv --date <YYYY-MM-DD>
   ```

   Do the same for `ial`.
3. Commit the two `data/mas_*_YYYY-MM-DD.json` files and push. Vercel redeploys on push. Real
   snapshots automatically win over the demo ones, and the demo banner disappears.
4. The demo examples use invented firms, so they'll then show "not licensed". Update the README's
   "what's real" table before you submit.

---

## Appendix: Turso without Vercel's Marketplace

If you'd rather manage Turso directly, the Turso CLI works too: `turso db create chaincheck`, then
`turso db show chaincheck --url` for `TURSO_DATABASE_URL` and `turso db tokens create chaincheck`
for `TURSO_AUTH_TOKEN`. Add both to Vercel yourself. Everything else is the same.
