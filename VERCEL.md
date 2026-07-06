# Deploy on Vercel

Flask works on Vercel, but **quotes must live in a cloud database** (local `data/quotes.db` does not persist on serverless). This project uses [Turso](https://turso.tech) (free tier, SQLite-compatible).

## Step 1 — Turso database (5 min)

1. Sign up at [turso.tech](https://turso.tech) (free).
2. Install the CLI (optional but easiest):

   ```bash
   brew install tursodatabase/tap/turso
   turso auth login
   ```

3. Create a database:

   ```bash
   turso db create toption-quotes
   turso db show toption-quotes --url
   turso db tokens create toption-quotes
   ```

   Save the **Database URL** (`libsql://...`) and **auth token**.

4. Initialize tables (one time):

   ```bash
   turso db shell toption-quotes
   ```

   Paste the SQL from `storage.py` (`CREATE TABLE quotes ...`) or run locally once with env vars set (see below).

## Step 2 — Deploy on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. **Import** your GitHub repo.
3. Framework Preset: **Flask** (or **Other** — Vercel reads `pyproject.toml` + `app.py`).
4. **Environment Variables** — add these for **Production** (required):

   | Name | Value |
   |------|--------|
   | `APP_PASSWORD` | `TopVN26` (or your password) |
   | `SECRET_KEY` | long random string, e.g. from `openssl rand -hex 32` |
   | `TURSO_DATABASE_URL` | `libsql://your-db-....turso.io` |
   | `TURSO_AUTH_TOKEN` | token from Turso |

   **All four are required.** Without Turso, the app crashes on Vercel (local `data/` does not work there).

5. Click **Deploy**.

6. Test: open `https://your-app.vercel.app/health` — should show `{"ok": true, "database": "turso"}`.

7. Open your `*.vercel.app` URL → sign in with `APP_PASSWORD`.

Share that URL and password with your coworker. Everyone sees the same quotes in Turso.

## Step 3 — Push config files (if you uploaded manually)

Make sure these files are in GitHub (re-upload or `git push`):

- `app.py` (entry point — not `api/index.py`)
- `pyproject.toml`
- `vercel.json`
- `db.py`
- updated `storage.py` and `requirements.txt`

Then **Redeploy** in the Vercel dashboard.

## Local dev with Turso (optional)

```bash
export TURSO_DATABASE_URL="libsql://..."
export TURSO_AUTH_TOKEN="..."
export APP_PASSWORD="TopVN26"
export SECRET_KEY="dev-secret"
python3 app.py
```

Without Turso env vars, the app still uses local `data/quotes.db` on your Mac.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Serverless function crashed** | Add `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` in Vercel env vars, then redeploy |
| Build fails on `libsql` | Ensure `requirements.txt` has `libsql-client` |
| `/health` shows `"ok": false` | Read the `error` field — usually missing Turso env vars |
| Login works but quotes don’t save | Check Turso token is valid; redeploy after env changes |
| PDF/Excel timeout | Hobby plan allows 10s; Pro allows 60s (`maxDuration` in `vercel.json`) |
| Missing logo on PDF | Upload `assets/logo.png` and `assets/signature.png` to the repo |

## Turso via Vercel Marketplace (alternative)

In the Vercel dashboard: **Storage** → **Create Database** → look for Turso integration, then map env vars automatically.
