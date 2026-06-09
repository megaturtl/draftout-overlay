"""SQLite cache of discovered matches.

A match is only cached once ended (terminal outcome + completedAt), which makes
it immutable, so a stored row is never refreshed. `matches` is keyed by the
global match id; `player_matches` records which matches we've already collected
per player, the signal that lets discovery stop paginating (see has_player_match).
"""

import json
import sqlite3
import time

_SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id    INTEGER PRIMARY KEY,
    summary     TEXT NOT NULL,
    detail      TEXT,
    fetched_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS player_matches (
    player_uuid TEXT NOT NULL,
    match_id    INTEGER NOT NULL,
    PRIMARY KEY (player_uuid, match_id)
);
"""


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def is_ended(summary):
    return bool(summary.get("outcome")) and summary.get("completedAt") is not None


def put_summary(conn, match_id, summary):
    """Store an ended match's summary (ignored if already present); no-op otherwise."""
    if not is_ended(summary):
        return False
    conn.execute(
        "INSERT OR IGNORE INTO matches (match_id, summary, fetched_at) "
        "VALUES (?, ?, ?)",
        (match_id, json.dumps(summary), int(time.time() * 1000)),
    )
    conn.commit()
    return True


def player_match_summaries(conn, player_uuid, match_type=None):
    """The player's cached match summaries (those recorded in player_matches)."""
    rows = conn.execute(
        "SELECT m.summary FROM matches m "
        "JOIN player_matches pm ON pm.match_id = m.match_id "
        "WHERE pm.player_uuid = ?",
        (player_uuid,),
    )
    out = []
    for (summary_text,) in rows:
        summary = json.loads(summary_text)
        if match_type is None or summary.get("matchType") == match_type:
            out.append(summary)
    return out


def has_player_match(conn, player_uuid, match_id):
    """Whether this match was collected for this player on an earlier walk.

    Not the global `matches` cache: a match cached from another player's
    perspective can sit mid-history here, and stopping on it would skip this
    player's older, never-walked matches.
    """
    row = conn.execute(
        "SELECT 1 FROM player_matches WHERE player_uuid = ? AND match_id = ?",
        (player_uuid, match_id),
    ).fetchone()
    return row is not None


def record_player_matches(conn, player_uuid, match_ids):
    conn.executemany(
        "INSERT OR IGNORE INTO player_matches (player_uuid, match_id) VALUES (?, ?)",
        [(player_uuid, mid) for mid in match_ids],
    )
    conn.commit()
