"""
test_email.py

Manual test for Step 4: sends a real test digest email using fake
listing data (no scraping involved - this step only tests the email
sending itself, separately from the scraper/filter/dedup chain).

Before running this:
  1. Turn on 2-Step Verification on your Google account, if you haven't.
  2. Generate a Gmail App Password: https://myaccount.google.com/apppasswords
  3. Copy .env.example to .env and fill in GMAIL_ADDRESS, GMAIL_APP_PASSWORD,
     and ALERT_RECIPIENTS (your own address is fine for this test).

Run with:
    python test_email.py
"""

from dotenv import load_dotenv

from notify_email import send_digest_email

load_dotenv()  # reads .env into the environment for this local test run

fake_listings = [
    {
        "title": "Test House, CV32 4AB",
        "price_pcm": 650,
        "bedrooms": 4,
        "area": "Leamington Spa",
        "url": "https://spaestates.com/property/example/",
    },
    {
        "title": "Another Test House, CV31 1AA",
        "price_pcm": 700,
        "bedrooms": 3,
        "area": "Leamington Spa",
        "url": "https://spaestates.com/property/example-2/",
    },
]

sent = send_digest_email(fake_listings)
print("Email sent! Check your inbox." if sent else "No email sent (empty listing list).")
