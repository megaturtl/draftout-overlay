"""Player record model and aggregation over match summaries."""

from dataclasses import dataclass
from typing import Any, Self


@dataclass
class Record:
    name: str
    wins: int = 0
    draws: int = 0
    losses: int = 0
    elo: int | None = None
    forfeits: int = 0
    # filled in after history discovery
    avg_forfeit_ms: float | None = None
    avg_forfeit_deficit: float | None = None  # mean goals behind when forfeiting

    @classmethod
    def from_api(cls, name: str, data: dict[str, Any]) -> Self:
        # `or {}` guards against the API returning these keys explicitly null
        # (e.g. an unknown player), which the {} default does not.
        rec = data.get("record") or {}
        return cls(
            name=name,
            wins=rec.get("wins", 0),
            draws=rec.get("draws", 0),
            losses=rec.get("losses", 0),
            elo=(data.get("player") or {}).get("elo"),
            forfeits=(data.get("aggregate") or {}).get("forfeitCount", 0),
        )

    @property
    def forfeit_pct(self) -> int | None:
        return round(100 * self.forfeits / self.losses) if self.losses else None

    @property
    def avg_forfeit_str(self) -> str | None:
        if self.avg_forfeit_ms is None:
            return None
        total = round(self.avg_forfeit_ms / 1000)
        return f"{total // 60}:{total % 60:02d}"


def _forfeited_by_player(player_uuid, summaries):
    """Yield (summary, me, opponent) for matches this player forfeited.

    The forfeiter is the loser of a forfeited match.
    """
    for s in summaries:
        if s.get("outcome") != "forfeited":
            continue
        parts = s.get("participants") or []
        me = next((p for p in parts if p.get("uuid") == player_uuid), None)
        opp = next((p for p in parts if p.get("uuid") != player_uuid), None)
        if me is not None and opp is not None and me.get("won") is False:
            yield s, me, opp


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def avg_forfeit_ms(player_uuid: str, summaries: list[dict[str, Any]]) -> float | None:
    """Mean duration of matches this player forfeited (how long until they quit)."""
    return _mean(
        [
            s["durationMs"]
            for s, _, _ in _forfeited_by_player(player_uuid, summaries)
            if s.get("durationMs") is not None
        ]
    )


def avg_forfeit_deficit(
    player_uuid: str, summaries: list[dict[str, Any]]
) -> float | None:
    """Mean goals behind (opponent score - player score) when this player forfeits."""
    return _mean(
        [
            opp["score"] - me["score"]
            for _, me, opp in _forfeited_by_player(player_uuid, summaries)
            if me.get("score") is not None and opp.get("score") is not None
        ]
    )
