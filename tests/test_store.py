from datetime import date
from bot.parser import ResultRow, ParsedTournament
from bot.store import Store


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table):
        self.table = table
        self._filter = None
        self._is_insert = False

    def select(self, *_cols):
        return self

    def in_(self, col, values):
        self._filter = (col, set(values))
        return self

    def gte(self, col, value):
        self.table.calls.append(("gte", col, value))
        return self

    def lte(self, col, value):
        self.table.calls.append(("lte", col, value))
        return self

    def insert(self, payload):
        self._is_insert = True
        self.table.inserted.append(payload)
        return self

    def execute(self):
        if self._is_insert:
            return Result(self.table.insert_returns)
        if self._filter:
            col, values = self._filter
            return Result([r for r in self.table.rows if r.get(col) in values])
        return Result(list(self.table.rows))


class FakeTable:
    def __init__(self, rows=None, insert_returns=None):
        self.rows = rows or []
        self.inserted = []
        self.calls = []
        self.insert_returns = insert_returns or []

    def query(self):
        return FakeQuery(self)


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return self._tables[name].query()


def test_existing_message_ids_filters():
    tournaments = FakeTable(rows=[{"discord_message_id": "a"}, {"discord_message_id": "b"}])
    store = Store(FakeSupabase({"tournaments": tournaments}))
    assert store.existing_message_ids(["a", "c"]) == {"a"}


def test_existing_message_ids_empty_input_returns_empty():
    tournaments = FakeTable(rows=[{"discord_message_id": "a"}])
    store = Store(FakeSupabase({"tournaments": tournaments}))
    assert store.existing_message_ids([]) == set()


def test_insert_tournament_writes_tournament_then_results():
    tournaments = FakeTable(insert_returns=[{"id": 42}])
    results = FakeTable()
    store = Store(FakeSupabase({"tournaments": tournaments, "results": results}))
    t = ParsedTournament("Monday Standard Showdown", date(2026, 7, 6), [
        ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer"),
    ])
    store.insert_tournament("msg1", "chan1", t)
    assert tournaments.inserted[0]["discord_message_id"] == "msg1"
    assert tournaments.inserted[0]["name"] == "Monday Standard Showdown"
    assert tournaments.inserted[0]["event_date"] == "2026-07-06"
    assert tournaments.inserted[0]["channel_id"] == "chan1"
    assert results.inserted[0][0]["tournament_id"] == 42
    assert results.inserted[0][0]["player_key"] == "james smith"
    assert results.inserted[0][0]["deck"] == "Temur Harmonizer"


def test_fetch_results_in_window_returns_rows_and_filters():
    joined = FakeTable(rows=[
        {"points": 9, "player_key": "james smith", "player_name": "James Smith"},
    ])
    store = Store(FakeSupabase({"results": joined}))
    rows = store.fetch_results_in_window(date(2026, 7, 1), date(2026, 7, 31))
    assert rows[0]["player_key"] == "james smith"
    assert ("gte", "tournaments.event_date", "2026-07-01") in joined.calls
    assert ("lte", "tournaments.event_date", "2026-07-31") in joined.calls
