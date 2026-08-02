from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.parser import parse_tournament

log = logging.getLogger(__name__)


def run(discord, store, channel_id: str, timezone: str) -> int:
    tz = ZoneInfo(timezone)
    messages = discord.fetch_messages(channel_id, limit=100)
    already = store.existing_message_ids([m["id"] for m in messages])
    inserted = 0
    for message in messages:
        if message["id"] in already:
            continue
        rounds = parse_tournament(message.get("content", ""))
        if not rounds:
            continue
        event_date = datetime.fromisoformat(message["timestamp"]).astimezone(tz).date()
        name = event_date.isoformat()
        store.insert_tournament(message["id"], channel_id, name, event_date, rounds)
        players = {}
        for r in rounds:
            players[r.player_key] = r.player_name
        store.upsert_players(
            [{"player_key": k, "display_name": v} for k, v in players.items()]
        )
        log.info("Ingested tournament %s with %d player-rounds", name, len(rounds))
        inserted += 1
    return inserted
