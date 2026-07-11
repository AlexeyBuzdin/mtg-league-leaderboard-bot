from datetime import date, datetime
from zoneinfo import ZoneInfo
from bot.leaderboard import month_window, aggregate_totals, build_leaderboard_embeds, PlayerTotal


def test_month_window_current_calendar_month():
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    start, end = month_window(now)
    assert start == date(2026, 7, 1)
    assert end == date(2026, 7, 15)


def test_aggregate_sums_and_sorts_desc():
    rows = [
        {"points": 9, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 6, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 7, "player_key": "nikita powers", "player_name": "Nikita Powers"},
    ]
    totals = aggregate_totals(rows)
    assert totals[0] == PlayerTotal("james smith", "James Smith", 15, 2)
    assert totals[1] == PlayerTotal("nikita powers", "Nikita Powers", 7, 1)


def test_aggregate_tie_broken_alphabetically():
    rows = [
        {"points": 5, "player_key": "bob", "player_name": "Bob"},
        {"points": 5, "player_key": "alice", "player_name": "Alice"},
    ]
    totals = aggregate_totals(rows)
    assert [t.display_name for t in totals] == ["Alice", "Bob"]


def test_aggregate_uses_latest_display_name():
    rows = [
        {"points": 3, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 3, "player_key": "james smith", "player_name": "james  smith"},
    ]
    # rows arrive oldest-first; latest spelling wins
    totals = aggregate_totals(rows)
    assert totals[0].display_name == "james  smith"


def test_build_embeds_single_when_small():
    totals = [PlayerTotal("a", "Alice", 10, 2), PlayerTotal("b", "Bob", 5, 1)]
    embeds = build_leaderboard_embeds(totals, "July 2026")
    assert len(embeds) == 1
    assert "July 2026" in embeds[0]["title"]
    assert "1. Alice — 10 pts (2 events)" in embeds[0]["description"]
    assert "2. Bob — 5 pts (1 event)" in embeds[0]["description"]


def test_build_embeds_chunks_when_large():
    totals = [PlayerTotal(f"p{i}", f"Player{i}", 100 - i, 1) for i in range(60)]
    embeds = build_leaderboard_embeds(totals, "July 2026")
    assert len(embeds) == 2  # 50 per embed
    assert "1. Player0" in embeds[0]["description"]
    assert "51. Player50" in embeds[1]["description"]


from bot.leaderboard import run as leaderboard_run


class FakeStore2:
    def __init__(self, rows):
        self._rows = rows
        self.window = None
    def fetch_results_in_window(self, start, end):
        self.window = (start, end)
        return self._rows


class FakeDiscord2:
    def __init__(self):
        self.posted = None
    def post_embeds(self, channel_id, embeds):
        self.posted = (channel_id, embeds)


def test_leaderboard_run_posts_embed():
    rows = [
        {"points": 9, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 7, "player_key": "nikita powers", "player_name": "Nikita Powers"},
    ]
    store = FakeStore2(rows)
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    posted = leaderboard_run(discord, store, channel_id="222", now=now)
    assert posted is True
    assert store.window == (date(2026, 7, 1), date(2026, 7, 15))
    channel_id, embeds = discord.posted
    assert channel_id == "222"
    assert "July 2026" in embeds[0]["title"]
    assert "1. James Smith — 9 pts" in embeds[0]["description"]


def test_leaderboard_run_skips_when_empty():
    store = FakeStore2([])
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    posted = leaderboard_run(discord, store, channel_id="222", now=now)
    assert posted is False
    assert discord.posted is None
