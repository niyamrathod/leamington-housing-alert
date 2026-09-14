"""
dedupe.py

Tracks which listings we've already alerted on, so the same house doesn't
get emailed out again on every run. Backed by seen.json, a plain JSON
file mapping listing id -> the timestamp we first alerted on it.

This module only reads/writes the local seen.json file - it does NOT
commit or push anything to git. In this project's architecture, git is
the persistence layer: the GitHub Actions workflow commits the updated
seen.json back to the repo after a successful run. That commit step
belongs in the workflow YAML, not here.
"""

import json
import os
import tempfile
from datetime import datetime, timezone


def load_seen(path="seen.json"):
    """
    Load the seen-listings dict from disk. Returns an empty dict if the
    file doesn't exist yet - that's the normal state on the very first
    run, not an error.
    """
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def filter_new(listings, seen):
    """Return only the listings whose id isn't already a key in `seen`."""
    return [listing for listing in listings if listing["id"] not in seen]


def mark_seen(seen, listings):
    """
    Record each listing's id in `seen` with the current UTC timestamp.
    Mutates `seen` in place and also returns it, so it can be saved
    straight after with save_seen().
    """
    now = datetime.now(timezone.utc).isoformat()
    for listing in listings:
        seen[listing["id"]] = now
    return seen


def save_seen(seen, path="seen.json"):
    """
    Write `seen` to disk atomically.

    We write to a temporary file first and then rename it into place,
    instead of writing directly to seen.json. If the process got killed
    mid-write (e.g. a GitHub Actions runner timing out), a direct write
    could leave seen.json half-written and corrupt, which would break
    every future run. os.replace() is atomic on both Windows and Linux -
    the real file only ever changes in one instant, and only once fully
    written.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2)
        os.replace(temp_path, path)
    except Exception:
        # Clean up the temp file if something went wrong before the
        # rename landed, so stray .tmp files don't pile up.
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
