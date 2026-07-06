# Toption Quote Generator

Web tool to generate Toption (Asia) quotation sheets from factory inputs, with Excel and PDF export. Quotes are saved to a shared database so your team can search, edit, and export from any computer.

## Quick Start (Local)

```bash
pip3 install -r requirements.txt
python3 app.py
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) and sign in with the app password (default: `TopVN26`).

> **Note:** Port 5000 is used by macOS AirPlay Receiver and will show "access denied". This app uses port **8080** instead.

## Password Protection

The entire app is behind a sign-in screen. Set the password with an environment variable:

```bash
export APP_PASSWORD="TopVN26"
export SECRET_KEY="use-a-long-random-string-here"
python3 app.py
```

Share the password with coworkers who need access. Everyone sees the same saved quotes.

## Put It Online (Team Access)

### Option A — Docker on a server (recommended)

Works on any VPS (DigitalOcean, Linode, AWS EC2, etc.) or a Mac/PC that stays on.

```bash
cp .env.example .env
# Edit .env: set APP_PASSWORD and SECRET_KEY

docker compose up -d --build
```

Open `http://YOUR_SERVER_IP:8080` from any computer. Quotes persist in the Docker volume `quote_data`.

For HTTPS, put [Caddy](https://caddyserver.com/) or nginx in front of port 8080.

### Option B — Render (free tier)

1. Push this project to GitHub.
2. Create a [Render](https://render.com) account → **New Blueprint** → connect the repo.
3. Set `APP_PASSWORD` to `TopVN26` (or your chosen password) in the Render dashboard.
4. Render provisions a persistent disk at `/app/data` for the quote database.
5. Share the `*.onrender.com` URL with your coworker.

The included `render.yaml` configures this automatically.

### Option C — Quick tunnel (testing only)

If the app is running locally and you need temporary remote access:

```bash
# Install cloudflared, then:
cloudflared tunnel --url http://127.0.0.1:8080
```

Share the generated URL. **Not for production** — your laptop must stay on.

## Quote Storage

Every quote is automatically saved to SQLite (`data/quotes.db`) when you:
- Click **Save Quote**
- **Preview Calculations**
- **Generate Excel** or **Generate PDF**

Use the **Home** page search bar to find quotes by inquiry #, part number, drawing #, factory name, description, material, or notes.

## Features

- **Input fields:** Inquiry #, date, factory name, exchange rate, lead times, validity, custom fields
- **Line items:** P/N, cast/mach DWG #, description, material, qty, factory unit price (VND), weight, mold fee (VND), other/finish, pressure testing
- **Custom markups:** Global unit price % and mold fee %; optional per-line overrides
- **Export/inspection fee:** Flat USD amount (default $500), allocated per unit — **not marked up**
- **Preview:** Live calculation summary before export
- **Excel:** Two sheets — `Quotation` (customer-facing) + `Calculations` (full breakdown)
- **PDF:** Landscape quote with calculations summary; includes logo and signature

## Calculation Logic

| Step | Formula |
|------|---------|
| Factory unit (USD) | Factory unit (VND) ÷ exchange rate |
| Export fee per unit | Export fee ÷ # of parts ÷ qty |
| Quoted unit FOB (USD) | Factory unit (USD) × (1 + unit markup %) + export fee/unit |
| Quoted tooling (USD) | Factory mold (USD) × (1 + mold markup %) |
| Unit price profit | (Quoted FOB − factory unit USD) × qty |
| Mold fee profit | Quoted tooling − factory mold USD |
| Net profit | Σ line profits − export/inspection fee |

## Project Structure

```
app.py              Flask server
calculator.py       Calculation engine
excel_generator.py  Excel export
pdf_generator.py    PDF export
template.xlsx       Original reference template
assets/             Logo and signature images
static/             Web UI assets
templates/          HTML
```
