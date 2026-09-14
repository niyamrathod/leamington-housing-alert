# Leamington Housing Alert

A small unattended tool that watches independent Leamington Spa letting
agents for new student houses, emails a digest the moment something
matches a saved search, and includes a standalone calculator for
splitting rent/bills by room size once a house is found.

It deliberately does **not** scrape Rightmove, Zoopla, SpareRoom, or
OnTheMarket — their terms of use prohibit automated scraping. Set up
their own native saved-search email alerts separately if you want that
coverage too; this tool only covers smaller independent agents that
don't offer their own alerts (currently: [Spa Estates](https://spaestates.com)).

A live project page (with an email sign-up form) and a browser version
of the bill-split calculator are hosted at
[niyamrathod.github.io/leamington-housing-alert.html](https://niyamrathod.github.io/leamington-housing-alert.html).

## How it works

There's no server and no database. GitHub Actions runs the check on a
schedule (triggered externally by [cron-job.org](https://cron-job.org),
since GitHub's own `schedule:` trigger is unreliable/delayed), and git
itself is the only persistence layer: `seen.json` records which
listings have already been alerted on, and the workflow commits it back
to the repo after every run that finds something new.

```
scraper.py       scrapes each source, returns normalized listings
filters.py       filters listings against criteria.json profiles
dedupe.py        compares against seen.json, returns only new listings
notify_email.py  sends one digest email for everything new
main.py           orchestrates the above + pings healthchecks.io
billsplit.py      standalone terminal bill-split calculator
```

## 1. Accounts you'll need

- **GitHub** — this repo already exists; you just need secrets set on it (below).
- **Gmail** — used to send the alert emails.
  1. Turn on **2-Step Verification**: https://myaccount.google.com/security
  2. Generate an **App Password**: https://myaccount.google.com/apppasswords
     (this is a 16-character code, separate from your normal password —
     copy it immediately, Google only shows it once)
- **healthchecks.io** — free account at https://healthchecks.io. Create a
  check named e.g. "Leamington Housing Alert" with a **Period** of 60
  minutes and a **Grace period** of 30 minutes (generous enough to
  absorb normal GitHub Actions runner startup delays). Copy its ping URL.
- **cron-job.org** — free account at https://cron-job.org, used to
  trigger the GitHub Actions workflow on a schedule (see section 4).

## 2. Running it locally

```
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
GMAIL_ADDRESS=youraddress@gmail.com
GMAIL_APP_PASSWORD=your16charapppassword
ALERT_RECIPIENTS=you@example.com,friend@example.com
HEALTHCHECK_URL=https://hc-ping.com/your-uuid-here
```

`.env` is gitignored and never committed — it's for local testing only.
In GitHub Actions, the same variable names come from repo secrets instead.

Useful test scripts, each runnable directly (`.venv\Scripts\python.exe <script>.py`):

| Script | What it checks |
|---|---|
| `test_scraper.py` | Prints everything the scraper currently finds |
| `test_filters.py` | Scrapes + filters against `criteria.json`, prints matches per profile |
| `test_dedupe.py` | Full scrape → filter → dedupe chain against the real `seen.json` |
| `test_email.py` | Sends a real digest email using fake listing data |
| `billsplit.py` | The terminal bill-split calculator |

Run the whole pipeline for real with `main.py` — this is exactly what
the scheduled workflow runs.

## 3. Repo secrets

Set these under **Settings → Secrets and variables → Actions → New
repository secret** — same names and values as your `.env`:

- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `ALERT_RECIPIENTS`
- `HEALTHCHECK_URL`

## 4. Wiring up the schedule

**Generate a GitHub PAT** so cron-job.org can trigger the workflow:
Settings (your profile) → **Developer settings → Personal access
tokens → Fine-grained tokens → Generate new token**
- Repository access: **Only select repositories** → this repo
- Permissions → Repository permissions → **Actions: Read and write**
- Generate, copy the token immediately (shown once)

**Create the cron-job.org job**:
- URL: `https://api.github.com/repos/<your-username>/leamington-housing-alert/actions/workflows/check_listings.yml/dispatches`
- Method: **POST**
- Headers:
  - `Authorization: Bearer <your PAT>`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- Body: `{"ref":"main"}`
- Schedule: every 30–60 minutes

A successful trigger returns **204 No Content**. Check the repo's
**Actions** tab to confirm runs are actually happening on schedule.

## 5. If `seen.json` needs to be reset

`seen.json` is a plain JSON dict of `{"listing-id": "timestamp"}`. To
make everything re-alert as if it were new (e.g. after changing
`criteria.json` significantly), edit it back to `{}`, commit, and push.
To forget one specific listing, just delete its key.

## 6. Adding another source

Each scraping source is one function in `scraper.py` (see
`scrape_spa_estates()`) returning a list of dicts with `id`, `url`,
`source`, `price_pcm`, `bedrooms`, `area`, and `title`. Add the new
function to the `SOURCES` list at the bottom of the file — nothing else
in the pipeline needs to change. Before adding a source, check its
robots.txt and terms of use for scraping restrictions first.
