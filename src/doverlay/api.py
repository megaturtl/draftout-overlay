"""HTTP access to the Draftout stats API.

Route A (`/api/stats/<name>`) returns a player's record plus a page of match
summaries; Route B (`/api/stats/<name>/<id>`) returns full per-match detail.
The site blocks automated user agents, so we send a browser-like one.
"""

import requests

from .config import USER_AGENT

BASE_URL = "https://draftoutmc.com"


def _get(path, params=None):
    resp = requests.get(
        f"{BASE_URL}{path}",
        params=params or None,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_player_page(name, page=None, filter=None):
    params = {}
    if page:
        params["page"] = page
    if filter:
        params["filter"] = filter
    return _get(f"/api/stats/{name}", params=params)


def get_match(name, match_id):
    """Route B detail. Unused for now; the hook for future goal-level stats."""
    return _get(f"/api/stats/{name}/{match_id}")


def iter_match_summaries(name, filter=None, first_page=None):
    """Yield every match summary across all Route A pages, newest first.

    `first_page` (an already-fetched payload) is reused as page 1 if given.
    """
    page = 1
    payload = first_page
    while True:
        if payload is None:
            payload = get_player_page(name, page=page, filter=filter)
        total_pages = payload.get("totalPages", 1) or 1
        yield from payload.get("matches", [])
        if page >= total_pages:
            return
        page += 1
        payload = None
