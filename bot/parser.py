from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


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


_HEADER_RE = re.compile(
    r"^(?P<name>.+?)\s*\((?P<date>\d{2}\.\d{2}\.\d{4})\)\s*final standings:?\s*$",
    re.IGNORECASE,
)


def match_header(line: str, allowed_names: list[str]) -> tuple[str, date] | None:
    m = _HEADER_RE.match(line.strip())
    if not m:
        return None
    name = m.group("name").strip()
    allowed = {n.strip().lower() for n in allowed_names}
    if name.lower() not in allowed:
        return None
    try:
        event_date = datetime.strptime(m.group("date"), "%d.%m.%Y").date()
    except ValueError:
        return None
    return name, event_date
