"""
test_filters.py

Manual test for Step 2: scrapes real listings, filters them against the
profiles in criteria.json, and prints what matched each profile - so we
can check the filtering logic against real data before wiring in dedup
and email.

Run with:
    python test_filters.py
"""

from scraper import scrape_all
from filters import load_criteria, filter_listings

listings = scrape_all()
print(f"Scraped {len(listings)} listing(s) total.\n")

profiles = load_criteria()
matches_by_profile = filter_listings(listings, profiles)

for name, matches in matches_by_profile.items():
    print(f"--- Profile '{name}': {len(matches)} match(es) ---")
    for listing in matches:
        print(f"  £{listing['price_pcm']} pcm | {listing['bedrooms']} bed | {listing['title']}")
    print()
