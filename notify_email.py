"""
notify_email.py

Sends one digest email covering every new matching listing, via Gmail
SMTP using an App Password. Credentials and recipients come from
environment variables - loaded from a local .env file when testing, or
from GitHub Actions secrets when running in the scheduled workflow.
Never hardcode these values.
"""

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
    recipients = [
        address.strip()
        for address in _require_env("ALERT_RECIPIENTS").split(",")
        if address.strip()
    ]

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
