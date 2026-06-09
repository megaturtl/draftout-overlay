"""Always-on-top overlay showing the current opponent's competitive record.

Watches the Draftout Minecraft log, detects the opponent, fetches their
record, and shows it in a small draggable window.
"""

import argparse
import signal
import threading

import requests
from watchdog.observers import Observer

from .config import DEFAULT_DIR, DEFAULT_IGN
from .overlay import Overlay
from .stats import get_record
from .watcher import OpponentWatcher


def lookup_async(overlay: Overlay, name: str) -> None:
    """Fetch and display one player's record on a background thread."""

    def run() -> None:
        overlay.set_status(name, "looking up...")
        try:
            overlay.set_player(get_record(name))
        except (requests.RequestException, ValueError) as exc:
            overlay.set_status(name, "lookup failed")
            print(f"[lookup] {name}: {exc}")

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
