import pytest
from bot.config import load_config

BASE_ENV = {
    "DISCORD_BOT_TOKEN": "tok",
    "RESULTS_CHANNEL_ID": "111",
    "LEADERBOARD_CHANNEL_ID": "222",
    "SUPABASE_URL": "https://x.supabase.co",
    "SUPABASE_KEY": "key",
    "TOURNAMENT_NAMES": "Monday Standard Showdown, Standard Store Championship",
}


def test_load_config_parses_values():
    cfg = load_config(BASE_ENV)
    assert cfg.discord_bot_token == "tok"
    assert cfg.results_channel_id == "111"
    assert cfg.leaderboard_channel_id == "222"
    assert cfg.supabase_url == "https://x.supabase.co"
    assert cfg.supabase_key == "key"
    assert cfg.tournament_names == ["Monday Standard Showdown", "Standard Store Championship"]
    assert cfg.timezone == "Europe/Riga"  # default


def test_timezone_override():
    cfg = load_config({**BASE_ENV, "TIMEZONE": "UTC"})
    assert cfg.timezone == "UTC"


def test_missing_required_var_raises():
    broken = {k: v for k, v in BASE_ENV.items() if k != "SUPABASE_KEY"}
    with pytest.raises(ValueError) as exc:
        load_config(broken)
    assert "SUPABASE_KEY" in str(exc.value)
