"""
filters.py

Filters scraped listings against the search-criteria profiles defined in
criteria.json. Each profile can set:

    name           - whose profile this is (used later in the email/logs)
    max_price      - highest monthly rent (pcm) to accept
    min_bedrooms   - fewest bedrooms to accept
    max_bedrooms   - most bedrooms to accept
    area_keywords  - list of strings; a listing must contain at least one
                      of these (case-insensitive) somewhere in its area
                      or title text

Any of these fields can simply be left out of a profile to skip that
particular check for that person.
"""

import json


def load_criteria(path="criteria.json"):
    """Load the list of search-criteria profiles from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _matches_profile(listing, profile):
    """Check whether a single listing satisfies a single criteria profile."""
    price = listing.get("price_pcm")
    if "max_price" in profile:
        # A listing with an unparsed/unknown price can't be confirmed to
        # be within budget, so treat it as a non-match rather than guessing.
        if price is None or price > profile["max_price"]:
            return False

    bedrooms = listing.get("bedrooms")
    if "min_bedrooms" in profile:
        if bedrooms is None or bedrooms < profile["min_bedrooms"]:
            return False
    if "max_bedrooms" in profile:
        if bedrooms is None or bedrooms > profile["max_bedrooms"]:
            return False

    if "area_keywords" in profile:
        # Check both area and title, since the area field is often just
        # "Leamington Spa" while the postcode (e.g. CV32) only shows up
        # in the title text.
        haystack = f"{listing.get('area', '')} {listing.get('title', '')}".lower()
        if not any(keyword.lower() in haystack for keyword in profile["area_keywords"]):
            return False

    return True


def filter_listings(listings, profiles):
    """
    Filter listings against every profile in criteria.json.

    Returns a dict mapping each profile's name to the list of listings
    that matched it, e.g. {"niyam": [listing1, listing2]}. A listing that
    matches more than one person's profile will appear under each of them.
    """
    matches_by_profile = {}
    for profile in profiles:
        matches_by_profile[profile["name"]] = [
            listing for listing in listings if _matches_profile(listing, profile)
        ]
    return matches_by_profile


def flatten_matches(matches_by_profile):
    """
    Combine every profile's matches into one list of unique listings,
    ready to hand to dedupe.py and then the alert email. A listing that
    matched more than one person's profile only appears once here - we
    only ever want to alert on it once, not once per matching profile.
    """
    unique_by_id = {}
    for matches in matches_by_profile.values():
        for listing in matches:
            unique_by_id[listing["id"]] = listing
    return list(unique_by_id.values())
