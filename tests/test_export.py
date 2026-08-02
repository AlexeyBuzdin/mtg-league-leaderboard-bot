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
    assert p["player1"] == {"name": "Ann", "game_wins": 2, "record": {"wins": 1, "draws": 0, "losses": 0}}
    assert p["player2"] == {"name": "Bob", "game_wins": 1, "record": {"wins": 0, "draws": 0, "losses": 1}}


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


import json
import pytest
from bot.export import export_to_file, main


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_cols):
        return self

    def execute(self):
        return type("R", (), {"data": self._data})


class _FakeClient:
    def __init__(self, tournaments, results):
        self._tables = {"tournaments": tournaments, "round_results": results}

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
