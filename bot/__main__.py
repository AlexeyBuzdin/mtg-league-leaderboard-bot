from __future__ import annotations

import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from bot.config import Config, load_config
from bot.discord_client import DiscordClient
from bot.ingest import run as ingest_run
from bot.leaderboard import run as leaderboard_run
from bot.store import Store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    sub.add_parser("leaderboard")
    return parser


def _make_clients(cfg: Config) -> tuple[DiscordClient, Store]:
    discord = DiscordClient(cfg.discord_bot_token)
    store = Store(create_client(cfg.supabase_url, cfg.supabase_key))
    return discord, store


def _run_ingest(cfg: Config) -> None:
    discord, store = _make_clients(cfg)
    count = ingest_run(discord, store, cfg.results_channel_id, cfg.tournament_names)
    logging.info("Ingest complete: %d new tournament(s)", count)


def _run_leaderboard(cfg: Config) -> None:
    discord, store = _make_clients(cfg)
    now = datetime.now(ZoneInfo(cfg.timezone))
    posted = leaderboard_run(discord, store, cfg.leaderboard_channel_id, now)
    logging.info("Leaderboard posted: %s", posted)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    cfg = load_config()
    if args.command == "ingest":
        _run_ingest(cfg)
    elif args.command == "leaderboard":
        _run_leaderboard(cfg)


if __name__ == "__main__":
    main()
