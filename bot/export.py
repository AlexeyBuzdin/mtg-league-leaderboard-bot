from __future__ import annotations

import argparse
import json
import os
import sys
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


_TOURNAMENT_COLS = "id, name, event_date"
_RESULT_COLS = (
    "tournament_id, round, pairing, player_name, player_key, "
    "game_wins, record_wins, record_draws, record_losses"
)


def _fetch(client) -> tuple[list[dict], list[dict]]:
    tournaments = client.table("tournaments").select(_TOURNAMENT_COLS).execute().data
    results = client.table("round_results").select(_RESULT_COLS).execute().data
    return tournaments, results


def export_to_file(client, out_path: str) -> int:
    tournaments, results = _fetch(client)
    data = build_site_data(tournaments, results)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return len(data["tournaments"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bot.export")
    parser.add_argument("--out", default="web/data/tournaments.json")
    args = parser.parse_args(argv)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_KEY must be set", file=sys.stderr)
        raise SystemExit(1)

    from supabase import create_client

    count = export_to_file(create_client(url, key), args.out)
    print(f"Wrote {count} tournaments to {args.out}")


if __name__ == "__main__":
    main()
