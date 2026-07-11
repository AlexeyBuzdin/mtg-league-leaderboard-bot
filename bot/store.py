from __future__ import annotations

from datetime import date

from bot.parser import ParsedTournament


class Store:
    def __init__(self, supabase) -> None:
        self._db = supabase

    def existing_message_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        resp = (
            self._db.table("tournaments")
            .select("discord_message_id")
            .in_("discord_message_id", ids)
            .execute()
        )
        return {row["discord_message_id"] for row in resp.data}

    def insert_tournament(self, message_id: str, channel_id: str, t: ParsedTournament) -> None:
        resp = (
            self._db.table("tournaments")
            .insert(
                {
                    "discord_message_id": message_id,
                    "name": t.name,
                    "event_date": t.event_date.isoformat(),
                    "channel_id": channel_id,
                }
            )
            .execute()
        )
        tournament_id = resp.data[0]["id"]
        rows = [
            {
                "tournament_id": tournament_id,
                "standing": r.standing,
                "player_name": r.player_name,
                "player_key": r.player_key,
                "points": r.points,
                "wins": r.wins,
                "draws": r.draws,
                "losses": r.losses,
                "deck": r.deck,
            }
            for r in t.rows
        ]
        self._db.table("results").insert(rows).execute()

    def fetch_results_in_window(self, start: date, end: date) -> list[dict]:
        resp = (
            self._db.table("results")
            .select("points, player_key, player_name, tournaments!inner(event_date)")
            .gte("tournaments.event_date", start.isoformat())
            .lte("tournaments.event_date", end.isoformat())
            .execute()
        )
        return resp.data
