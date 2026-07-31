from bot.parser import normalize_name, parse_record, PlayerRound


def test_normalize_casefolds_trims_collapses():
    assert normalize_name("  Artūrs   Smith ") == "artūrs smith"


def test_normalize_is_unicode_casefold():
    # casefold lowercases non-ASCII letters
    assert normalize_name("MĀRTIŅŠ Doe") == normalize_name("mārtiņš doe")


def test_parse_record_en_dash():
    assert parse_record("1–0–0") == (1, 0, 0)


def test_parse_record_hyphen_and_em_dash():
    assert parse_record("2-1-0") == (2, 1, 0)
    assert parse_record("0—3—0") == (0, 3, 0)


def test_parse_record_rejects_non_record():
    assert parse_record("James Doe") is None
    assert parse_record("5") is None


def test_player_round_dataclass():
    pr = PlayerRound(
        round=1, pairing=1,
        player_name="James Doe", player_key="james doe", game_wins=2,
        opponent_name="Alexey Doe", opponent_key="alexey doe", opponent_game_wins=0,
        record_wins=1, record_draws=0, record_losses=0,
    )
    assert pr.record_wins == 1
    assert pr.opponent_key == "alexey doe"


from pathlib import Path
from bot.parser import parse_tournament

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_tournament_rounds_and_pairings():
    content = (FIXTURES / "pairings_sample.txt").read_text(encoding="utf-8")
    rows = parse_tournament(content)
    assert rows is not None
    # 2 rounds * 2 pairings * 2 players = 8 rows
    assert len(rows) == 8
    first = rows[0]
    assert (first.round, first.pairing) == (1, 1)
    assert first.player_name == "James Doe"
    assert first.player_key == "james doe"
    assert first.game_wins == 2
    assert first.opponent_name == "Alexey Doe"
    assert first.opponent_game_wins == 0
    assert (first.record_wins, first.record_draws, first.record_losses) == (1, 0, 0)
    second = rows[1]
    assert second.player_name == "Alexey Doe"
    assert second.opponent_name == "James Doe"
    assert second.game_wins == 0
    assert (second.record_wins, second.record_draws, second.record_losses) == (0, 1, 0)


def test_parse_tournament_detects_second_round():
    content = (FIXTURES / "pairings_sample.txt").read_text(encoding="utf-8")
    rows = parse_tournament(content)
    round2 = [r for r in rows if r.round == 2]
    assert len(round2) == 4
    raitis_r2 = next(r for r in round2 if r.player_key == "raitis doe")
    assert (raitis_r2.record_wins, raitis_r2.record_draws, raitis_r2.record_losses) == (2, 0, 0)


def test_parse_tournament_returns_none_for_chatter():
    assert parse_tournament("just some chatter\nnothing here") is None
