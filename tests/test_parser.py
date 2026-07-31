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
