from __future__ import annotations

import logging

from bot.parser import parse_message

log = logging.getLogger(__name__)


def run(discord, store, channel_id: str, allowed_names: list[str]) -> int:
    messages = discord.fetch_messages(channel_id, limit=100)
    already = store.existing_message_ids([m["id"] for m in messages])
    inserted = 0
    for message in messages:
        if message["id"] in already:
            continue
        tournament = parse_message(message.get("content", ""), allowed_names)
        if tournament is None:
            continue
        store.insert_tournament(message["id"], channel_id, tournament)
        log.info("Ingested %s (%s) with %d rows", tournament.name,
                 tournament.event_date, len(tournament.rows))
        inserted += 1
    return inserted
