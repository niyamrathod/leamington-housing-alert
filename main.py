"""
main.py

Orchestrates one full run of the housing alert check:

    scrape -> filter -> dedupe -> email (if anything new) -> update seen.json

This is the single entry point the GitHub Actions workflow runs. Any
failure is logged clearly to stderr and the process exits with a
non-zero status, so a failed Actions run actually shows up as failed
in GitHub's UI rather than looking like it succeeded.

After a successful run, we also ping a healthchecks.io check-in URL.
That's the unattended-reliability safety net: if the scheduled run ever
stops happening (cron-job.org breaks, GitHub Actions has an outage, the
script starts erroring every time) healthchecks.io notices the ping
stopped arriving and emails us, instead of the failure going unnoticed.
"""

import os
import sys

import requests

from scraper import scrape_all
from filters import load_criteria, filter_listings, flatten_matches
from dedupe import load_seen, filter_new, mark_seen, save_seen
from notify_email import send_digest_email


def run():
    """Run one full check. Returns the number of new listings emailed."""
    print("Scraping listings...")
    listings = scrape_all()
    print(f"  scraped {len(listings)} listing(s) total")

    print("Filtering against criteria...")
    profiles = load_criteria()
    matches_by_profile = filter_listings(listings, profiles)
    all_matches = flatten_matches(matches_by_profile)
    print(f"  {len(all_matches)} listing(s) matched a profile")

    print("Checking for new listings...")
    seen = load_seen()
    new_listings = filter_new(all_matches, seen)
    print(f"  {len(new_listings)} of those are new")

    if new_listings:
        print("Sending digest email...")
        send_digest_email(new_listings)
        seen = mark_seen(seen, new_listings)
        save_seen(seen)
        print("  email sent and seen.json updated")
    else:
        print("Nothing new - no email sent, seen.json unchanged")

    return len(new_listings)


def ping_healthcheck():
    """
    Tell healthchecks.io this run completed successfully - "ran fine,
    nothing new" counts as success here, not just "found something".

    If HEALTHCHECK_URL isn't set, this quietly does nothing, which lets
    us run/test everything locally without needing a healthchecks.io
    account yet. If the ping itself fails (e.g. a network blip), we log
    a warning but don't fail the whole run over it - the actual work
    above already succeeded, and a single missed ping is exactly what
    healthchecks.io's own grace period exists to tolerate.
    """
    url = os.environ.get("HEALTHCHECK_URL")
    if not url:
        print("  HEALTHCHECK_URL not set - skipping heartbeat ping")
        return

    try:
        requests.get(url, timeout=10)
        print("  healthcheck ping sent")
    except requests.RequestException as error:
        print(f"  WARNING: healthcheck ping failed - {error}", file=sys.stderr)


if __name__ == "__main__":
    try:
        # Loads .env when running on your own machine; in GitHub Actions
        # there's no .env file, so this is a harmless no-op there and the
        # values come from the env vars the workflow sets from secrets.
        from dotenv import load_dotenv
        load_dotenv()

        new_count = run()
        print(f"Run complete. {new_count} new listing(s) found.")

        # Only reached if run() didn't raise - i.e. a genuine success,
        # whether or not anything new was found.
        ping_healthcheck()
    except Exception as error:
        print(f"ERROR: run failed - {error}", file=sys.stderr)
        sys.exit(1)
