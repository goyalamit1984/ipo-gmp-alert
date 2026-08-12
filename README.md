# IPO GMP Alert

Checks live IPO GMP data daily and creates a Google Calendar event when a rule
matches (e.g. "Mainboard IPO with GMP > 15%"). Runs on a GitHub Actions
schedule — no server of your own needed.

## How it's structured (built to add more alerts later)

```
rules.json           - alert definitions (data source + conditions + notifier)
fetchers/ipo_gmp.py   - scrapes investorgain.com's live IPO GMP table
conditions.py         - reusable comparison logic (>, <, ==, contains, ...)
notifiers/google_calendar.py - creates the calendar event
run.py                - loads rules.json, runs each fetcher, checks conditions, notifies
```

To add a new alert (a different data source, a different threshold, a
different notifier), you add a fetcher/notifier module if needed and a new
block in `rules.json` — `run.py` doesn't change.

## 1. One-time setup

### a) Get Google Calendar credentials

1. Go to https://console.cloud.google.com/ → create a project (or reuse one).
2. Enable the **Google Calendar API**.
3. Create an **OAuth client ID** (type: Desktop app). Download the client ID
   and client secret.
4. Run the helper script locally once to get a refresh token:

   ```bash
   pip install -r requirements.txt
   python get_refresh_token.py
   ```

   This opens a browser, asks you to log in with the Google account whose
   calendar you want events created on, and prints a `GOOGLE_REFRESH_TOKEN`.

### b) Add GitHub repo secrets

In your repo → Settings → Secrets and variables → Actions, add:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GOOGLE_CALENDAR_ID` (usually just `primary`)

### c) Push this folder to a GitHub repo

The workflow in `.github/workflows/ipo-gmp-alert.yml` runs daily at 9:00 AM
IST (03:30 UTC) — adjust the cron if you want a different time, and you can
trigger it manually from the Actions tab to test.

## 2. Test locally first

```bash
pip install -r requirements.txt
playwright install chromium
python run.py
```

This will print what it found and, if a rule matches, create the calendar
event. Do this once before trusting the GitHub Actions run — the scraper
depends on investorgain.com's page structure, which can change.

## Notes / limitations

- GMP is an unofficial, unregulated number scraped from a public webpage —
  not an official API. If investorgain.com changes their table layout, the
  scraper needs a small update to `fetchers/ipo_gmp.py`.
- The page is JavaScript-rendered, so the fetcher uses Playwright
  (a headless browser) rather than a plain HTTP request.
- Be a reasonable citizen: the script runs once (or a few times) a day, not
  in a tight loop, and identifies itself with a normal User-Agent.
