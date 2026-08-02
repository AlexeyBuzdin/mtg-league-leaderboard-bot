from __future__ import annotations

from datetime import date

from bot.parser import PlayerRound


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

    def upsert_players(self, players: list[dict]) -> None:
        if not players:
            return
        self._db.table("players").upsert(
            players, on_conflict="player_key", ignore_duplicates=True
        ).execute()

    def fetch_league_keys(self) -> set[str]:
        resp = (
            self._db.table("players").select("player_key").eq("is_league", True).execute()
        )
        return {row["player_key"] for row in resp.data}

    def insert_tournament(
        self,
        message_id: str,
        channel_id: str,
        name: str,
        event_date: date,
        rounds: list[PlayerRound],
    ) -> None:
        resp = (
            self._db.table("tournaments")
            .insert(
                {
                    "discord_message_id": message_id,
                    "name": name,
                    "event_date": event_date.isoformat(),
                    "channel_id": channel_id,
                }
            )
            .execute()
        )
        tournament_id = resp.data[0]["id"]
        rows = [
            {
                "tournament_id": tournament_id,
                "round": r.round,
                "pairing": r.pairing,
                "player_name": r.player_name,
                "player_key": r.player_key,
                "opponent_name": r.opponent_name,
                "opponent_key": r.opponent_key,
                "game_wins": r.game_wins,
                "opponent_game_wins": r.opponent_game_wins,
                "record_wins": r.record_wins,
                "record_draws": r.record_draws,
                "record_losses": r.record_losses,
            }
            for r in rounds
        ]
        self._db.table("round_results").insert(rows).execute()

    def fetch_results_in_window(self, start: date, end: date) -> list[dict]:
        resp = (
            self._db.table("round_results")
            .select(
                "tournament_id, round, player_key, player_name, "
                "record_wins, record_draws, tournaments!inner(event_date)"
            )
            .gte("tournaments.event_date", start.isoformat())
            .lte("tournaments.event_date", end.isoformat())
            .order("event_date", desc=False, foreign_table="tournaments")
            .execute()
        )
        # Reduce to each player's final-round record per tournament, then points = 3W + D.
        finals: dict[tuple, dict] = {}
        for row in resp.data:
            key = (row["tournament_id"], row["player_key"])
            current = finals.get(key)
            if current is None or row["round"] > current["round"]:
                finals[key] = row
        return [
            {
                "player_key": row["player_key"],
                "player_name": row["player_name"],
                "points": 3 * row["record_wins"] + row["record_draws"],
            }
            for row in finals.values()
        ]
