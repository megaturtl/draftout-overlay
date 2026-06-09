from dataclasses import dataclass
from typing import Any, Self

import requests

from .config import USER_AGENT


@dataclass
class Record:
    name: str
    wins: int = 0
    draws: int = 0
    losses: int = 0
    elo: int | None = None
    forfeits: int = 0

    @classmethod
    def from_api(cls, name: str, data: dict[str, Any]) -> Self:
        rec = data.get("record", {})
        return cls(
            name=name,
            wins=rec.get("wins", 0),
            draws=rec.get("draws", 0),
            losses=rec.get("losses", 0),
            elo=data.get("player", {}).get("elo"),
            forfeits=data.get("aggregate", {}).get("forfeitCount", 0),
        )

    @property
    def forfeit_pct(self) -> int | None:
        return round(100 * self.forfeits / self.losses) if self.losses else None


def get_record(name: str) -> Record:
    """Fetch a player's Record, or raise requests.RequestException / ValueError."""
    response = requests.get(
        f"https://draftoutmc.com/api/stats/{name}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return Record.from_api(name, response.json())
