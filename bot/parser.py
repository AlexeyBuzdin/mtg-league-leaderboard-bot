from __future__ import annotations

import re
from dataclasses import dataclass

_RECORD_RE = re.compile(r"^(\d+)\s*[–—-]\s*(\d+)\s*[–—-]\s*(\d+)$")


@dataclass
class PlayerRound:
    round: int
    pairing: int
    player_name: str
    player_key: str
    game_wins: int | None
    opponent_name: str | None
    opponent_key: str | None
    opponent_game_wins: int | None
    record_wins: int
    record_draws: int
    record_losses: int


def normalize_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def parse_record(token: str) -> tuple[int, int, int] | None:
    m = _RECORD_RE.match(token.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))
