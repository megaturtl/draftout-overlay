"""Always-on-top overlay showing the current opponent's competitive record.

Watches the Draftout Minecraft log, detects the opponent, fetches their
record, and shows it in a small draggable window.
"""

import argparse
import signal
import threading

import requests
from watchdog.observers import Observer

from . import api, cache, history, stats
from .config import CACHE_PATH, DEFAULT_DIR, DEFAULT_IGN
from .overlay import Overlay
from .stats import Record
from .watcher import OpponentWatcher


def lookup_async(overlay: Overlay, name: str) -> None:
    """Look up a player on a background thread.

    Show the headline record from one request first, then discover/cache the
    full match history and update with the stats that need every match.
    """

    def run() -> None:
        overlay.set_status(name, "looking up...")
        try:
            page1 = api.get_player_page(name)
        except (requests.RequestException, ValueError) as exc:
            overlay.set_status(name, "lookup failed")
            print(f"[lookup] {name}: {exc}")
            return

        rec = Record.from_api(name, page1)
        overlay.set_player(rec)

        uuid = (page1.get("player") or {}).get("uuid")
        if uuid is None:
            return
        # Best-effort enrichment: the headline record is already shown, so any
        # failure here (network, cache/DB locked, bad payload) just skips the
        # extra stats rather than killing the thread.
        try:
            conn = cache.connect(CACHE_PATH)
            try:
                summaries = history.discover(conn, name, uuid, first_page=page1)
            finally:
                conn.close()
            rec.avg_forfeit_ms = stats.avg_forfeit_ms(uuid, summaries)
            rec.avg_forfeit_deficit = stats.avg_forfeit_deficit(uuid, summaries)
            overlay.set_player(rec)
        except Exception as exc:
            print(f"[history] {name}: {exc}")

    threading.Thread(target=run, daemon=True).start()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Draftout opponent overlay")
    p.add_argument("--dir", default=DEFAULT_DIR)
    p.add_argument("--ign", default=DEFAULT_IGN)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    overlay = Overlay(
        on_submit=lambda name: lookup_async(overlay, name),
        on_refresh=lambda: refresh(),
    )

    watcher = OpponentWatcher(
        f"{args.dir}/logs/latest.log",
        args.ign,
        on_opponent=lambda name: lookup_async(overlay, name),
    )

    def refresh() -> None:
        if watcher.opponent:
            lookup_async(overlay, watcher.opponent)
        else:
            overlay.show_waiting()

    observer = Observer()
    observer.schedule(watcher, path=f"{args.dir}/logs", recursive=False)
    observer.start()

    signal.signal(signal.SIGINT, lambda *_: overlay.close())
    overlay.run()
    observer.stop()


if __name__ == "__main__":
    main()
