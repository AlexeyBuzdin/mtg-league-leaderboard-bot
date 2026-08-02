from __future__ import annotations

from collections import defaultdict


def _player_obj(row: dict) -> dict:
    return {
        "name": row["player_name"],
        "game_wins": row["game_wins"],
        "record": {
            "wins": row["record_wins"],
            "draws": row["record_draws"],
            "losses": row["record_losses"],
        },
    }


def build_site_data(tournaments: list[dict], results: list[dict]) -> dict:
    grouped: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for row in results:
        grouped[row["tournament_id"]][row["round"]][row["pairing"]].append(row)

    out_tournaments = []
    for t in sorted(tournaments, key=lambda t: t["event_date"]):
        rounds_map = grouped.get(t["id"], {})
        rounds_out = []
        for round_no in sorted(rounds_map):
            pairings_out = []
            for pairing_no in sorted(rounds_map[round_no]):
                rows = sorted(
                    rounds_map[round_no][pairing_no],
                    key=lambda r: r["player_key"],
                )
                pairings_out.append(
                    {
                        "pairing": pairing_no,
                        "player1": _player_obj(rows[0]),
                        "player2": _player_obj(rows[1]) if len(rows) > 1 else None,
                    }
                )
            rounds_out.append({"round": round_no, "pairings": pairings_out})
        out_tournaments.append(
            {
                "id": str(t["id"]),
                "name": t["name"] or "Tournament",
                "date": t["event_date"],
                "rounds": rounds_out,
            }
        )
    return {"tournaments": out_tournaments}
