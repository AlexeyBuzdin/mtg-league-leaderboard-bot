from __future__ import annotations

from collections import defaultdict
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


def _is_summer_2026(event_date) -> bool:
    if isinstance(event_date, str):
        year, month = int(event_date[:4]), int(event_date[5:7])
    else:
        year, month = event_date.year, event_date.month
    return year == 2026 and month in (6, 7, 8)


def _tournament_scores(rows: list[dict]) -> dict:
    summer = _is_summer_2026(rows[0]["event_date"])
    ranked = sorted(
        rows,
        key=lambda r: (
            -(3 * r["record_wins"] + r["record_draws"]),
            -(r["game_wins"] or 0),
            r["player_name"].lower(),
        ),
    )
    bonus = [3, 2, 1]
    out: dict = {}
    for i, r in enumerate(ranked):
        if summer:
            placement = bonus[i] if i < 3 else 0
            score = placement + 2 * r["record_wins"] + r["record_draws"] + 1
        else:
            score = 3 * r["record_wins"] + r["record_draws"]
        out[r["player_key"]] = {"player_name": r["player_name"], "score": score}
    return out


def season_totals(stats: list[dict], league_keys: set[str]) -> list[PlayerTotal]:
    by_tournament: dict = defaultdict(list)
    for row in stats:
        by_tournament[row["tournament_id"]].append(row)
    acc: dict[str, PlayerTotal] = {}
    for rows in by_tournament.values():
        for key, s in _tournament_scores(rows).items():
            if key not in league_keys:
                continue
            cur = acc.get(key)
            if cur is None:
                acc[key] = PlayerTotal(key, s["player_name"], s["score"], 1)
            else:
                acc[key] = PlayerTotal(
                    key, s["player_name"], cur.points + s["score"], cur.events + 1
                )
    return sorted(acc.values(), key=lambda t: (-t.points, t.display_name.lower()))


def run(discord, store, channel_id: str, now: datetime) -> bool:
    start, end = month_window(now)
    stats = store.fetch_tournament_stats(start, end)
    league_keys = store.fetch_league_keys()
    totals = season_totals(stats, league_keys)
    if not totals:
        return False
    label = f"{_MONTHS[start.month - 1]} {start.year}"
    embeds = build_leaderboard_embeds(totals, label)
    discord.post_embeds(channel_id, embeds)
    return True
