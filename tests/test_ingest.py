from datetime import date
from bot.ingest import run
from bot.parser import ParsedTournament


SAMPLE = (
    "Monday Standard Showdown (06.07.2026) final standings:\n\n"
    "1    James Smith     9    3/0/0    44.3%    66.7%    45.9%     (Temur Harmonizer)\n"
    "2    Nikita Powers    7    2/0/1    59.3%    71.4%    56.5%\n"
)
ALLOWED = ["Monday Standard Showdown", "Standard Store Championship"]


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
    def insert_tournament(self, message_id, channel_id, t):
        self.inserted.append((message_id, channel_id, t))


def test_ingest_inserts_new_tournament():
    discord = FakeDiscord([{"id": "m1", "content": SAMPLE}])
    store = FakeStore()
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 1
    message_id, channel_id, t = store.inserted[0]
    assert message_id == "m1"
    assert channel_id == "111"
    assert isinstance(t, ParsedTournament)
    assert t.event_date == date(2026, 7, 6)
    assert len(t.rows) == 2


def test_ingest_skips_already_processed():
    discord = FakeDiscord([{"id": "m1", "content": SAMPLE}])
    store = FakeStore(existing={"m1"})
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 0
    assert store.inserted == []


def test_ingest_skips_non_matching_messages():
    discord = FakeDiscord([{"id": "m2", "content": "just some chatter"}])
    store = FakeStore()
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 0
