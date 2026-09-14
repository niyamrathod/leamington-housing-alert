"""
scraper.py

Scrapes rental listings from independent Leamington Spa letting agents
(the ones that don't already offer their own automated search-alert
feature). Each source gets its own scrape_<name>() function that returns
a list of listing dictionaries, all using the same normalized shape:

    id         - unique string used for dedup (we use the URL slug)
    url        - full link to the listing
    source     - name of the agent, e.g. "Spa Estates"
    price_pcm  - monthly rent as an int (GBP), already normalized
    bedrooms   - int, or None if it couldn't be found
    area       - short area/postcode text
    title      - the listing's address/title text

scrape_all() runs every source and combines the results. To add a new
agent later (Tara & Co, Leamington Student Lets, ...), write a new
scrape_<name>() function with this same return shape and add it to
SOURCES below - nothing else in the pipeline needs to change.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

# Honest, identifying User-Agent so any site owner who checks their logs
# can see exactly what this is and how to reach us, per the project's
# scraping etiquette rules.
USER_AGENT = (
    "LeamingtonHousingAlertBot/1.0 "
    "(personal, non-commercial project; contact: rathodn209bx@gmail.com)"
)
HEADERS = {"User-Agent": USER_AGENT}

# Pause between requests to the same site so we're not hammering their
# server. 3 seconds is comfortably within the "2-3 seconds" politeness
# guideline for this project.
REQUEST_DELAY_SECONDS = 3


def _get_soup(url):
    """Fetch a URL and return a parsed BeautifulSoup document."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    if not response.ok:
        # Temporary diagnostics: a 401 from Spa Estates showed up only when
        # running in GitHub Actions, never locally, so we need to see what
        # the response actually says before deciding what's going on.
        print(f"  DEBUG: {response.status_code} response from {url}")
        print(f"  DEBUG: response headers: {dict(response.headers)}")
        print(f"  DEBUG: response body (first 500 chars): {response.text[:500]!r}")
    response.raise_for_status()  # raises on 4xx/5xx so failures aren't silent
    return BeautifulSoup(response.text, "html.parser")


def _parse_price_pcm(price_text):
    """
    Convert a price string like '£1,050 pcm' into a monthly integer.
    Spa Estates only ever shows 'pcm', but we handle 'pw' (per week) too
    in case that ever appears - (weekly * 52) / 12 is the standard
    weekly-to-monthly conversion used across UK letting sites.
    """
    digits_only = re.sub(r"[^\d.]", "", price_text)
    if not digits_only:
        return None
    amount = float(digits_only)
    if "pw" in price_text.lower():
        amount = amount * 52 / 12
    return round(amount)


def _parse_bedrooms(card):
    """Pull the bedroom count out of a Spa Estates property card."""
    bed_tag = card.select_one(".qt-property-thumb-style-7-info-bedrooms")
    if not bed_tag:
        return None
    match = re.search(r"\d+", bed_tag.get_text())
    return int(match.group()) if match else None


def scrape_spa_estates():
    """
    Scrape Spa Estates' residential lettings pages (spaestates.com).

    Checked 2026-09-14: robots.txt only blocks /wp-admin/, and there is
    no published Terms of Use restricting automated access, so this is
    a source we're clear to scrape (unlike the big portals, which we
    deliberately exclude).
    """
    listings = []
    page_url = "https://spaestates.com/properties/?department=residential-lettings"
    page_num = 1
    max_pages = 20  # safety cap - stops an infinite loop if pagination ever breaks

    while page_url and page_num <= max_pages:
        soup = _get_soup(page_url)
        cards = soup.select("li.qt-property-thumb-wrapper")

        for card in cards:
            availability = card.select_one(".qt-property-thumb-style-7-availability")
            # "Let Agreed" properties are no longer actually available -
            # skip them so we don't alert on a house that's already gone.
            if availability and "let agreed" in availability.get_text(strip=True).lower():
                continue

            link_tag = card.select_one(".qt-property-thumb-style-7-gallery-image-wrapper")
            price_tag = card.select_one(".qt-property-thumb-style-7-price")
            title_tag = card.select_one(".qt-property-thumb-style-7-info-title")
            location_tag = card.select_one(".qt-property-thumb-style-7-info-location")

            if not (link_tag and price_tag and title_tag):
                # Skip a malformed card rather than crashing the whole run -
                # one weird listing shouldn't take down the alert pipeline.
                continue

            url = link_tag["href"]
            # The URL slug (e.g. "high-street-cubbington-cv32-7lz") is
            # stable and unique per listing, so it doubles as our dedup ID.
            listing_id = url.rstrip("/").split("/")[-1]

            listings.append({
                "id": listing_id,
                "url": url,
                "source": "Spa Estates",
                "price_pcm": _parse_price_pcm(price_tag.get_text()),
                "bedrooms": _parse_bedrooms(card),
                "area": location_tag.get_text(strip=True) if location_tag else None,
                "title": title_tag.get_text(strip=True),
            })

        # Follow the "next page" link if there is one.
        next_link = soup.select_one("a.next.page-numbers")
        page_url = next_link["href"] if next_link else None
        page_num += 1

        if page_url:
            time.sleep(REQUEST_DELAY_SECONDS)

    return listings


# Every source scraper gets listed here. This is the one place to touch
# when adding a new agent - scrape_all() and everything downstream
# (filtering, dedup, email) doesn't need to change.
SOURCES = [
    scrape_spa_estates,
]


def scrape_all():
    """Run every source scraper and return one combined list of listings."""
    all_listings = []
    for scrape_source in SOURCES:
        all_listings.extend(scrape_source())
    return all_listings
