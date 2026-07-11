from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ResultRow:
    standing: int
    player_name: str
    player_key: str
    points: int
    wins: int
    draws: int
    losses: int
    deck: str | None


@dataclass
class ParsedTournament:
    name: str
    event_date: date
    rows: list[ResultRow]


def normalize_name(name: str) -> str:
    return " ".join(name.split()).lower()
