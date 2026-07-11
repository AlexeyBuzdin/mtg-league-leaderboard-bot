from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

_PER_EMBED = 50


@dataclass
class PlayerTotal:
    player_key: str
    display_name: str
    points: int
    events: int


def month_window(now: datetime) -> tuple[date, date]:
    today = now.date()
    return today.replace(day=1), today


def aggregate_totals(rows: list[dict]) -> list[PlayerTotal]:
    acc: dict[str, PlayerTotal] = {}
    for row in rows:
        key = row["player_key"]
        current = acc.get(key)
        if current is None:
            acc[key] = PlayerTotal(key, row["player_name"], row["points"], 1)
        else:
            # rows arrive oldest-first, so overwrite display name with the latest
            acc[key] = PlayerTotal(
                key,
                row["player_name"],
                current.points + row["points"],
                current.events + 1,
            )
    return sorted(acc.values(), key=lambda t: (-t.points, t.display_name.lower()))


def _line(rank: int, t: PlayerTotal) -> str:
    unit = "event" if t.events == 1 else "events"
    return f"{rank}. {t.display_name} — {t.points} pts ({t.events} {unit})"


def build_leaderboard_embeds(totals: list[PlayerTotal], month_label: str) -> list[dict]:
    embeds: list[dict] = []
    for start in range(0, max(len(totals), 1), _PER_EMBED):
        chunk = totals[start : start + _PER_EMBED]
        lines = [_line(start + i + 1, t) for i, t in enumerate(chunk)]
        title = f"\U0001f3c6 Standard League — {month_label}"
        if start > 0:
            title += " (cont.)"
        embeds.append({"title": title, "description": "\n".join(lines)})
    return embeds


_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def run(discord, store, channel_id: str, now: datetime) -> bool:
    start, end = month_window(now)
    rows = store.fetch_results_in_window(start, end)
    totals = aggregate_totals(rows)
    if not totals:
        return False
    label = f"{_MONTHS[start.month - 1]} {start.year}"
    embeds = build_leaderboard_embeds(totals, label)
    discord.post_embeds(channel_id, embeds)
    return True
