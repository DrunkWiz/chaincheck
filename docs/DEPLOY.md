# Deploy runbook

From nothing to a live ChainCheck on Vercel with Turso. Takes about 30 minutes.
Commands are for PowerShell on Windows; bash equivalents are noted where they differ.

**Before you start you need:** a Vercel account, a Turso account, a Google AI Studio account with
billing enabled, and Node + Python installed (see the README).

---

## 1. Make the secrets

Generate two long random values. Keep them in a password manager, not in chat or git.

```powershell
.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run it twice:

- the first value is `PHONE_HMAC_SECRET`
- the second is `ADMIN_TOKEN`

> **`PHONE_HMAC_SECRET` must never change after you seed.** Phone numbers and bank accounts are
> stored only as HMACs made with it. A different secret means none of them match any more.

## 2. Gemini key (paid tier)

1. In Google AI Studio, create an API key.
2. Turn on billing for its project. Free-tier prompts may be used by Google to improve its products
   and read by human reviewers. Victims paste personal chats, so use the paid tier.
3. That value is `GEMINI_API_KEY`.

The model defaults are `gemini-3.5-flash`, with `gemini-3.5-flash-lite` as the fallback. Both were
checked against Google's model list on 6 Oct 2026.

## 3. Turso database

Install the Turso CLI (see docs.turso.tech/cli/installation), then:

```powershell
turso auth login
```

```powershell
turso db locations
```

Pick the location closest to Singapore from that list. If you're asked to create a group, create it
there.

```powershell
turso db create chaincheck --wait
```

```powershell
turso db show chaincheck --url
```

That URL (`libsql://chaincheck-<you>.turso.io`) is `TURSO_DATABASE_URL`.

```powershell
turso db tokens create chaincheck
```

That token is `TURSO_AUTH_TOKEN`. It doesn't expire by default. Use `--expiration 30d` if you'd
rather it lapsed after the hackathon.

The tables are created automatically on the first request, so there's no migration step.

## 4. Seed the synthetic reports into Turso

Do this from your machine, with **the same** `PHONE_HMAC_SECRET` you'll give Vercel.

```powershell
$env:TURSO_DATABASE_URL = "libsql://chaincheck-<you>.turso.io"
$env:TURSO_AUTH_TOKEN = "<token>"
$env:PHONE_HMAC_SECRET = "<secret from step 1>"
.venv\Scripts\python -m scripts.seed_reports
```

(bash: `TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... PHONE_HMAC_SECRET=... .venv/bin/python -m scripts.seed_reports`)

You should see `Seeded 12 SYNTHETIC reports.` Running it again is safe: it does nothing if synthetic
reports already exist.

Close the terminal afterwards so the token doesn't linger in your session.

## 5. Vercel project

### Option A: dashboard (simplest)

1. Go to **Add New → Project** and import `DrunkWiz/chaincheck`. The repo is private, so allow
   Vercel's GitHub app access to it.
2. **Framework preset: Other.** Leave **Root directory** as the repo root. Build and output settings
   come from `vercel.json`, so leave them empty.
3. Under **Environment Variables**, add every variable below for **Production** (and Preview if you
   use preview deploys).
4. Click **Deploy**.

### Option B: CLI

```powershell
npm install -g vercel
```

```powershell
vercel link
```

Then add each variable. The CLI prompts for the value, so it doesn't land in your shell history:

```powershell
vercel env add PHONE_HMAC_SECRET production
```

Repeat for each variable in the table, then:

```powershell
vercel --prod
```

### Environment variables (all of them, every time)

| Variable | Value |
|---|---|
| `PHONE_HMAC_SECRET` | from step 1, the same one used to seed |
| `ADMIN_TOKEN` | from step 1 |
| `GEMINI_API_KEY` | from step 2 |
| `GEMINI_MODEL` | `gemini-3.5-flash` |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |
| `TURSO_DATABASE_URL` | from step 3 |
| `TURSO_AUTH_TOKEN` | from step 3 |

`DATABASE_PATH` isn't needed on Vercel. Without the Turso variables, checks still work but the
community pages say they're unavailable. The app won't write reports to Vercel's temporary disk.

Changing a variable needs a redeploy before it takes effect.

## 6. Smoke test the live site

Replace `<site>` with your deployment URL.

```powershell
curl.exe https://<site>/api/meta
```

Expect JSON with `"demo": true` until a real MAS snapshot is committed.

```powershell
Invoke-RestMethod -Method Post -Uri https://<site>/api/analyze -ContentType "application/json" -Body '{"text": "Earn 3% per day. Our courier will collect cash."}' | Select-Object verdict, summary, degraded
```

Expect `"verdict": "STOP"` and `"degraded": false`. If `degraded` is `true`, Gemini isn't answering.
See the troubleshooting section.

Then in a browser:

- [ ] Home page loads with the demo banner. Run each of the three invented examples.
- [ ] The copycat example shows a "Seen in 1 scam report" flag. That proves Turso is connected and
      the HMAC secret matches the seed.
- [ ] Upload a screenshot of an invented offer. Text is read and checked.
- [ ] Community page shows 12 synthetic reports and a 9-report network alert.
- [ ] Share a test story. It shows up in `/#/admin` with your `ADMIN_TOKEN`. Reject it.
- [ ] Phone width (375px): no sideways scrolling on any page.

## 7. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/api/...` returns 404 or the HTML page | The rewrite didn't apply. Check `vercel.json` is at the repo root and the project's root directory is the repo root |
| Offers with a phone number get "ChainCheck isn't fully set up yet" (503); logs say `PHONE_HMAC_SECRET must be set` | Variable missing in Vercel. Offers without phone numbers still get checked. The app refuses to use the dev default on purpose |
| Results say "AI reader wasn't available" | `GEMINI_API_KEY` missing or wrong, billing off, or a model ID retired. Check the function logs: errors show as `HTTP 4xx` from `gemini:<model>` |
| "Community reports are unavailable right now" | Turso URL or token wrong, or the token expired. Checks still work without it |
| Copycat example doesn't show "Seen in 1 scam report" | The seed was run with a different `PHONE_HMAC_SECRET`. Empty the tables (below) and reseed with the production secret |
| Build fails at `npm ci` | `frontend/package-lock.json` missing or out of date. Run `npm install` in `frontend/` and commit the lock file |
| Vercel treats the repo as a Python framework app | It shouldn't, because there's no framework dependency. If it does, set the framework preset to **Other** |

To empty the community tables before reseeding (this deletes every report, including real ones,
so only do it before launch):

```powershell
turso db shell chaincheck "DELETE FROM clusters; DELETE FROM report_entities; DELETE FROM entities; DELETE FROM reports;"
```

Logs: in the Vercel dashboard, open **Project → Logs**, or run `vercel logs <deployment-url>`. The app
never logs request bodies.

## 8. Roll back

Promote a previous deployment from **Project → Deployments → … → Promote**, or run:

```powershell
vercel rollback
```

## 9. When real MAS snapshots arrive

1. Check MAS's site terms. Download the FID and Investor Alert List by hand.
2. Convert each one:

   ```powershell
   .venv\Scripts\python -m scripts.snapshot_mas fid <file>.csv --date <YYYY-MM-DD>
   ```

   Do the same for `ial`.
3. Commit the two `data/mas_*_YYYY-MM-DD.json` files and redeploy. Real snapshots automatically win
   over the demo ones, and the demo banner disappears.
4. The demo examples use invented firms, so they'll then show "not licensed". Update the README's
   "what's real" table before you submit.
