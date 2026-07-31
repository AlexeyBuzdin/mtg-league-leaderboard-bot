from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

_REQUIRED = [
    "DISCORD_BOT_TOKEN",
    "RESULTS_CHANNEL_ID",
    "LEADERBOARD_CHANNEL_ID",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    results_channel_id: str
    leaderboard_channel_id: str
    supabase_url: str
    supabase_key: str
    timezone: str


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = env if env is not None else os.environ
    missing = [k for k in _REQUIRED if not env.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    return Config(
        discord_bot_token=env["DISCORD_BOT_TOKEN"],
        results_channel_id=env["RESULTS_CHANNEL_ID"],
        leaderboard_channel_id=env["LEADERBOARD_CHANNEL_ID"],
        supabase_url=env["SUPABASE_URL"],
        supabase_key=env["SUPABASE_KEY"],
        timezone=env.get("TIMEZONE", "Europe/Riga"),
    )
