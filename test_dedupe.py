"""
test_dedupe.py

Manual test for Step 3: runs the full scrape -> filter -> dedupe chain
against real data, then updates and saves seen.json.

Run this TWICE in a row to see dedup actually working:
  - 1st run: today's matches (if any) show up as NEW, and get saved
    into seen.json.
  - 2nd run: those same listings should now show up as "already seen"
    instead of NEW, since their ids are in seen.json.

Run with:
    python test_dedupe.py
"""

from scraper import scrape_all
from filters import load_criteria, filter_listings, flatten_matches
from dedupe import load_seen, filter_new, mark_seen, save_seen

listings = scrape_all()
profiles = load_criteria()
matches_by_profile = filter_listings(listings, profiles)
all_matches = flatten_matches(matches_by_profile)

print(f"{len(all_matches)} listing(s) matched a profile this run.\n")

seen = load_seen()
new_listings = filter_new(all_matches, seen)
already_seen = [listing for listing in all_matches if listing["id"] in seen]

for listing in new_listings:
    print(f"  NEW:          {listing['title']}")
for listing in already_seen:
    print(f"  already seen: {listing['title']}")

if new_listings:
    seen = mark_seen(seen, new_listings)
    save_seen(seen)
    print(f"\nUpdated seen.json with {len(new_listings)} new id(s).")
else:
    print("\nNo new listings this run - seen.json left unchanged.")
