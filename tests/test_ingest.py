from datetime import date
from bot.ingest import run


SAMPLE = (
    "1\nJames Doe\n1-0-0\n2\n0\nAlexey Doe\n0-1-0\n"
    "1\nJames Doe\n2-0-0\n2\n1\nAlexey Doe\n0-2-0\n"
)


class FakeDiscord:
    def __init__(self, messages):
        self._messages = messages
    def fetch_messages(self, channel_id, limit=100):
        return self._messages


class FakeStore:
    def __init__(self, existing=None):
        self._existing = existing or set()
        self.inserted = []
    def existing_message_ids(self, ids):
        return {i for i in ids if i in self._existing}
    def insert_tournament(self, message_id, channel_id, name, event_date, rounds):
        self.inserted.append((message_id, channel_id, name, event_date, rounds))


def test_ingest_inserts_and_derives_date_from_timestamp():
    msg = {"id": "m1", "content": SAMPLE, "timestamp": "2026-07-31T21:30:00+00:00"}
    discord = FakeDiscord([msg])
    store = FakeStore()
    count = run(discord, store, channel_id="111", timezone="Europe/Riga")
    assert count == 1
    message_id, channel_id, name, event_date, rounds = store.inserted[0]
    assert message_id == "m1"
    assert channel_id == "111"
    # 21:30 UTC on 2026-07-31 is 00:30 next day in Riga (+03) -> 2026-08-01
    assert event_date == date(2026, 8, 1)
    assert name == "2026-08-01"
    assert len(rounds) == 4  # 2 rounds * 1 pairing * 2 players


def test_ingest_skips_already_processed():
    msg = {"id": "m1", "content": SAMPLE, "timestamp": "2026-07-31T10:00:00+00:00"}
    store = FakeStore(existing={"m1"})
    count = run(FakeDiscord([msg]), store, channel_id="111", timezone="Europe/Riga")
    assert count == 0
    assert store.inserted == []


def test_ingest_skips_unparseable_messages():
    msg = {"id": "m2", "content": "just chatter", "timestamp": "2026-07-31T10:00:00+00:00"}
    store = FakeStore()
    count = run(FakeDiscord([msg]), store, channel_id="111", timezone="Europe/Riga")
    assert count == 0
