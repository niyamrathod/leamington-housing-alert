"""
notify_email.py

Sends one digest email covering every new matching listing, via Gmail
SMTP using an App Password. Credentials and recipients come from
environment variables - loaded from a local .env file when testing, or
from GitHub Actions secrets when running in the scheduled workflow.
Never hardcode these values.
"""

import json
import os
import smtplib
from email.mime.text import MIMEText


def _require_env(name):
    """Fetch a required environment variable, with a clear error if missing."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Check your .env file (local) or repo secrets (GitHub Actions)."
        )
    return value


def _load_signup_recipients(path="recipients.json"):
    """
    Load email addresses that signed up through the website's form.

    A Cloudflare Worker commits new addresses into this file automatically
    when someone submits the sign-up form - see the project README for how
    that's wired up. Returns an empty list if the file doesn't exist yet,
    since that's a normal state (nobody has signed up through the site
    yet, or this is a local test run without the file present).
    """
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_recipients():
    """
    Combine the fixed ALERT_RECIPIENTS secret (your own/close friends'
    addresses, set by hand) with the dynamic list of website sign-ups in
    recipients.json. Keeping ALERT_RECIPIENTS as a base list means alerts
    still reach you even if recipients.json is ever empty or missing.
    """
    fixed = [
        address.strip()
        for address in os.environ.get("ALERT_RECIPIENTS", "").split(",")
        if address.strip()
    ]
    signups = [address.strip() for address in _load_signup_recipients() if address.strip()]

    # Dedupe while preserving order, so the same address listed in both
    # places (or submitted twice) only gets one copy of the email.
    seen = set()
    combined = []
    for address in fixed + signups:
        if address.lower() not in seen:
            seen.add(address.lower())
            combined.append(address)

    if not combined:
        raise RuntimeError(
            "No alert recipients found - set ALERT_RECIPIENTS and/or "
            "make sure recipients.json has at least one address."
        )
    return combined


def _build_email_body(listings):
    """Build the plain-text digest body listing every new match."""
    lines = [f"{len(listings)} new listing(s) matching your criteria:\n"]
    for listing in listings:
        price = f"£{listing['price_pcm']} pcm" if listing.get("price_pcm") else "price unknown"
        bedrooms = listing.get("bedrooms")
        bedrooms_text = f"{bedrooms} bed" if bedrooms is not None else "bedrooms unknown"
        area = listing.get("area") or "area unknown"

        lines.append(
            f"- {listing['title']}\n"
            f"  {price} | {bedrooms_text} | {area}\n"
            f"  {listing['url']}\n"
        )
    return "\n".join(lines)


def send_digest_email(listings):
    """
    Send a single digest email listing every new match.

    Returns True if an email was sent, False if there was nothing to
    send (an empty listings list). Callers should generally check for
    new listings themselves before calling this, but it's a safe no-op
    either way.
    """
    if not listings:
        return False

    sender = _require_env("GMAIL_ADDRESS")
    app_password = _require_env("GMAIL_APP_PASSWORD")
    recipients = _get_recipients()

    message = MIMEText(_build_email_body(listings), "plain", "utf-8")
    message["Subject"] = f"{len(listings)} new Leamington housing match(es)"
    message["From"] = sender
    message["To"] = ", ".join(recipients)

    # Gmail's SMTP-over-SSL endpoint - App Passwords only work here, not
    # with your normal Google account password.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipients, message.as_string())

    return True
