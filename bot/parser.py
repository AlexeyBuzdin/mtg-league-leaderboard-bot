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


_ROW_RE = re.compile(
    r"^\s*(?P<standing>\d+)\s+(?P<name>.+?)\s+(?P<points>\d+)\s+"
    r"(?P<w>\d+)/(?P<d>\d+)/(?P<l>\d+)"
    r"(?:.*\((?P<deck>[^)]+)\))?.*$"
)


def parse_standings_line(line: str) -> ResultRow | None:
    m = _ROW_RE.match(line)
    if not m:
        return None
    name = m.group("name").strip()
    deck = m.group("deck")
    return ResultRow(
        standing=int(m.group("standing")),
        player_name=name,
        player_key=normalize_name(name),
        points=int(m.group("points")),
        wins=int(m.group("w")),
        draws=int(m.group("d")),
        losses=int(m.group("l")),
        deck=deck.strip() if deck else None,
    )


def parse_message(content: str, allowed_names: list[str]) -> ParsedTournament | None:
    lines = content.splitlines()
    if not lines:
        return None
    header = match_header(lines[0], allowed_names)
    if header is None:
        return None
    name, event_date = header
    rows = [r for r in (parse_standings_line(l) for l in lines[1:]) if r is not None]
    if not rows:
        return None
    return ParsedTournament(name=name, event_date=event_date, rows=rows)
