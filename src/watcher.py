import re
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler

# Patterns for parsing the log file
CHAT_AUTHOR = re.compile(r"\[CHAT\] <([^>]+)>")
MATCH_FOUND = "[game, found]"


class OpponentWatcher(FileSystemEventHandler):
    def __init__(
        self, path: str, my_ign: str, on_opponent: Callable[[str], None]
    ) -> None:
        self._path = path
        self._my_ign = my_ign
        self._on_opponent = on_opponent
        self._opponent: str | None = None
        self._file = open(path, "r", encoding="utf-8", errors="replace")
        self._file.seek(0, 2)

    @property
    def opponent(self) -> str | None:
        return self._opponent

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.src_path != self._path:
            return
        for line in self._file:
            self._handle(line)

    def on_created(self, event: FileSystemEvent) -> None:  # log rotated out from under us
        if event.src_path == self._path:
            self._file.close()
            self._file = open(self._path, "r", encoding="utf-8", errors="replace")

    def _handle(self, line: str) -> None:
        if MATCH_FOUND in line:
            self._opponent = None
            return
        if self._opponent is not None:
            return
        m = CHAT_AUTHOR.search(line)
        if m and m.group(1) != self._my_ign:
            self._opponent = m.group(1)
            self._on_opponent(self._opponent)
