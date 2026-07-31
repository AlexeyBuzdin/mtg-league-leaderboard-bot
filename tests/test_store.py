from datetime import date
from bot.parser import PlayerRound
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

    def order(self, col, *, desc=False, foreign_table=None):
        self.table.calls.append(("order", col, desc, foreign_table))
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


def _pr(round, name, key, rw, rd, rl, opp=None, opp_key=None):
    return PlayerRound(
        round=round, pairing=1, player_name=name, player_key=key,
        game_wins=2, opponent_name=opp, opponent_key=opp_key, opponent_game_wins=0,
        record_wins=rw, record_draws=rd, record_losses=rl,
    )


def test_existing_message_ids_filters():
    tournaments = FakeTable(rows=[{"discord_message_id": "a"}, {"discord_message_id": "b"}])
    store = Store(FakeSupabase({"tournaments": tournaments}))
    assert store.existing_message_ids(["a", "c"]) == {"a"}


def test_insert_tournament_writes_tournament_then_round_results():
    tournaments = FakeTable(insert_returns=[{"id": 42}])
    round_results = FakeTable()
    store = Store(FakeSupabase({"tournaments": tournaments, "round_results": round_results}))
    rounds = [
        _pr(1, "James Doe", "james doe", 1, 0, 0, "Alexey Doe", "alexey doe"),
        _pr(1, "Alexey Doe", "alexey doe", 0, 1, 0, "James Doe", "james doe"),
    ]
    store.insert_tournament("msg1", "chan1", "2026-07-31", date(2026, 7, 31), rounds)
    assert tournaments.inserted[0]["discord_message_id"] == "msg1"
    assert tournaments.inserted[0]["event_date"] == "2026-07-31"
    assert tournaments.inserted[0]["name"] == "2026-07-31"
    assert tournaments.inserted[0]["channel_id"] == "chan1"
    written = round_results.inserted[0]
    assert written[0]["tournament_id"] == 42
    assert written[0]["player_key"] == "james doe"
    assert written[0]["round"] == 1
    assert written[0]["opponent_key"] == "alexey doe"


def test_fetch_results_in_window_derives_points_from_final_record():
    rows = [
        {"tournament_id": 7, "round": 1, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 1, "record_draws": 0},
        {"tournament_id": 7, "round": 2, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 2, "record_draws": 0},
        {"tournament_id": 7, "round": 1, "player_key": "alexey doe",
         "player_name": "Alexey Doe", "record_wins": 0, "record_draws": 0},
        {"tournament_id": 7, "round": 2, "player_key": "alexey doe",
         "player_name": "Alexey Doe", "record_wins": 0, "record_draws": 0},
    ]
    rr = FakeTable(rows=rows)
    store = Store(FakeSupabase({"round_results": rr}))
    out = store.fetch_results_in_window(date(2026, 7, 1), date(2026, 7, 31))
    by_key = {r["player_key"]: r for r in out}
    assert by_key["james doe"]["points"] == 6
    assert by_key["james doe"]["player_name"] == "James Doe"
    assert by_key["alexey doe"]["points"] == 0
    assert len(out) == 2
    assert ("gte", "tournaments.event_date", "2026-07-01") in rr.calls
    assert ("lte", "tournaments.event_date", "2026-07-31") in rr.calls


def test_fetch_results_separates_same_player_across_tournaments():
    rows = [
        {"tournament_id": 1, "round": 1, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 3, "record_draws": 0},
        {"tournament_id": 2, "round": 1, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 1, "record_draws": 0},
    ]
    rr = FakeTable(rows=rows)
    store = Store(FakeSupabase({"round_results": rr}))
    out = store.fetch_results_in_window(date(2026, 7, 1), date(2026, 7, 31))
    james_rows = [r for r in out if r["player_key"] == "james doe"]
    assert len(james_rows) == 2
    assert sorted(r["points"] for r in james_rows) == [3, 9]
