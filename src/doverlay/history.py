from . import api, cache


def discover(conn, name, player_uuid, first_page=None, filter=None):
    """Cache any new ended matches, then return all of the player's cached summaries.

    The list is newest-first and ended matches are immutable, so once we reach
    one already collected for this player everything older was too and we stop.
    Each call thus picks up only matches played since the last lookup.
    """
    # put_summary returns True only for ended (cached) matches; those become the
    # per-player stop points, so in-progress matches are re-walked until they end.
    collected = []
    for summary in api.iter_match_summaries(name, filter=filter, first_page=first_page):
        match_id = summary["id"]
        if cache.has_player_match(conn, player_uuid, match_id):
            break
        if cache.put_summary(conn, match_id, summary):
            collected.append(match_id)
    cache.record_player_matches(conn, player_uuid, collected)

    return cache.player_match_summaries(conn, player_uuid, match_type=filter)
