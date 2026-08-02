from bot.export import build_site_data


def res(tid, rnd, pr, name, key, gw, w, d, l):
    return {
        "tournament_id": tid, "round": rnd, "pairing": pr,
        "player_name": name, "player_key": key, "game_wins": gw,
        "record_wins": w, "record_draws": d, "record_losses": l,
    }


def test_full_pairing_two_rows():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1)]
    data = build_site_data(tournaments, results)
    t = data["tournaments"][0]
    assert t["id"] == "1"
    assert t["date"] == "2026-07-06"
    p = t["rounds"][0]["pairings"][0]
    assert p["pairing"] == 1
    assert p["player1"] == {"name": "Ann", "game_wins": 2, "record": {"wins": 1, "draws": 0, "losses": 0}, "is_league": True, "deck": None, "deck_colours": None}
    assert p["player2"] == {"name": "Bob", "game_wins": 1, "record": {"wins": 0, "draws": 0, "losses": 1}, "is_league": True, "deck": None, "deck_colours": None}


def test_bye_single_row():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Cara", "cara", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    assert p["player1"]["name"] == "Cara"
    assert p["player2"] is None


def test_deterministic_player1_by_key():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1),
               res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    assert p["player1"]["name"] == "Ann"
    assert p["player2"]["name"] == "Bob"


def test_ordering_and_grouping():
    tournaments = [{"id": 2, "name": "Later", "event_date": "2026-08-01"},
                   {"id": 1, "name": "Earlier", "event_date": "2026-07-06"}]
    results = [
        res(1, 2, 1, "Ann", "ann", 2, 2, 0, 0), res(1, 2, 1, "Bob", "bob", 1, 1, 0, 1),
        res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0), res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1),
        res(2, 1, 1, "Ann", "ann", 2, 1, 0, 0), res(2, 1, 1, "Zed", "zed", 0, 0, 0, 1),
    ]
    data = build_site_data(tournaments, results)
    assert [t["name"] for t in data["tournaments"]] == ["Earlier", "Later"]
    assert [r["round"] for r in data["tournaments"][0]["rounds"]] == [1, 2]


def test_null_name_fallback():
    tournaments = [{"id": 1, "name": None, "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    assert data["tournaments"][0]["name"] == "Tournament"


def test_build_site_data_tags_is_league():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Guest", "guest", 1, 0, 0, 1)]
    data = build_site_data(tournaments, results, {"ann"})
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    by_name = {p["player1"]["name"]: p["player1"], p["player2"]["name"]: p["player2"]}
    assert by_name["Ann"]["is_league"] is True
    assert by_name["Guest"]["is_league"] is False


def test_build_site_data_defaults_all_league_when_keys_none():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    assert data["tournaments"][0]["rounds"][0]["pairings"][0]["player1"]["is_league"] is True


import json
import pytest
from bot.export import export_to_file, main


_POSTGREST_CAP = 1000


class _FakeQuery:
    def __init__(self, data):
        self._data = data
        self._range = None

    def select(self, *_cols):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        if self._range is None:
            # Mimic PostgREST: an un-ranged read is capped server-side.
            data = self._data[:_POSTGREST_CAP]
        else:
            start, end = self._range
            data = self._data[start : end + 1]
        return type("R", (), {"data": data})


class _FakeClient:
    def __init__(self, tournaments, results, players=None):
        self._tables = {
            "tournaments": tournaments,
            "round_results": results,
            "players": players or [],
        }

    def table(self, name):
        return _FakeQuery(self._tables[name])


def test_export_to_file_writes_expected_json(tmp_path):
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1)]
    out = tmp_path / "tournaments.json"
    count = export_to_file(_FakeClient(tournaments, results), str(out))
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["tournaments"][0]["rounds"][0]["pairings"][0]["player1"]["name"] == "Ann"


def test_export_to_file_preserves_unicode(tmp_path):
    tournaments = [{"id": 1, "name": None, "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Mārtiņš", "mārtiņš", 2, 1, 0, 0)]
    out = tmp_path / "t.json"
    export_to_file(_FakeClient(tournaments, results), str(out))
    assert "Mārtiņš" in out.read_text(encoding="utf-8")


def test_main_requires_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path / "x.json")])


def test_normalize_url_strips_trailing_slash():
    from bot.export import _normalize_url

    assert _normalize_url("https://x.supabase.co/") == "https://x.supabase.co"
    assert _normalize_url("https://x.supabase.co") == "https://x.supabase.co"
    assert _normalize_url("https://x.supabase.co//") == "https://x.supabase.co"


def test_export_fetches_all_rows_beyond_page_cap(tmp_path):
    # 1500 pairings -> 3000 round_results rows, past the 1000-row cap.
    # An un-paginated fetch would truncate and render dropped rows as false byes.
    tournaments = [{"id": 1, "name": "Big", "event_date": "2026-07-06"}]
    results = []
    for i in range(1500):
        results.append(res(1, 1, i + 1, f"A{i}", f"a{i:05d}", 2, 1, 0, 0))
        results.append(res(1, 1, i + 1, f"B{i}", f"b{i:05d}", 1, 0, 0, 1))
    out = tmp_path / "t.json"
    export_to_file(_FakeClient(tournaments, results), str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    pairings = data["tournaments"][0]["rounds"][0]["pairings"]
    assert len(pairings) == 1500
    assert all(p["player2"] is not None for p in pairings)


def test_export_to_file_uses_players_flag(tmp_path):
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Guest", "guest", 1, 0, 0, 1)]
    players = [{"player_key": "ann", "is_league": True},
               {"player_key": "guest", "is_league": False}]
    out = tmp_path / "t.json"
    export_to_file(_FakeClient(tournaments, results, players), str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    flags = {p["player1"]["name"]: p["player1"]["is_league"],
             p["player2"]["name"]: p["player2"]["is_league"]}
    assert flags == {"Ann": True, "Guest": False}


def test_build_site_data_includes_deck_and_colours():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [
        {"tournament_id": 1, "round": 1, "pairing": 1, "player_name": "Ann", "player_key": "ann",
         "game_wins": 2, "record_wins": 1, "record_draws": 0, "record_losses": 0,
         "player_deck": "Izzet Prowess", "player_deck_colours": "UR"},
        {"tournament_id": 1, "round": 1, "pairing": 1, "player_name": "Bob", "player_key": "bob",
         "game_wins": 1, "record_wins": 0, "record_draws": 0, "record_losses": 1},
    ]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    by_name = {p["player1"]["name"]: p["player1"], p["player2"]["name"]: p["player2"]}
    assert by_name["Ann"]["deck"] == "Izzet Prowess"
    assert by_name["Ann"]["deck_colours"] == "UR"
    assert by_name["Bob"]["deck"] is None
    assert by_name["Bob"]["deck_colours"] is None
