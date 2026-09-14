"""
test_scraper.py

Manual test script for Step 1: runs the scraper and prints what it finds,
so we can check the results against the real Spa Estates website before
trusting this data in the rest of the pipeline.

Run with:
    python test_scraper.py
"""

from scraper import scrape_all

listings = scrape_all()

print(f"Found {len(listings)} listing(s):\n")

for listing in listings:
    price = f"£{listing['price_pcm']} pcm" if listing["price_pcm"] else "price unknown"
    bedrooms = listing["bedrooms"] if listing["bedrooms"] is not None else "unknown"

    print(f"[{listing['source']}] {listing['title']}")
    print(f"  Price: {price}")
    print(f"  Bedrooms: {bedrooms}")
    print(f"  Area: {listing['area']}")
    print(f"  URL: {listing['url']}")
    print(f"  Dedup ID: {listing['id']}")
    print()
