from datetime import date
from bot.parser import normalize_name, ResultRow, ParsedTournament
from bot.parser import match_header


def test_normalize_lowercases_trims_collapses():
    assert normalize_name("  James   Smith ") == "james smith"


def test_normalize_idempotent():
    assert normalize_name(normalize_name("Nikita  Powers")) == "nikita powers"


def test_dataclasses_construct():
    row = ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer")
    assert row.points == 9
    t = ParsedTournament("Monday Standard Showdown", date(2026, 7, 6), [row])
    assert t.rows[0].deck == "Temur Harmonizer"


ALLOWED = ["Monday Standard Showdown", "Standard Store Championship"]


def test_match_header_allowed_name():
    result = match_header("Monday Standard Showdown (06.07.2026) final standings:", ALLOWED)
    assert result == ("Monday Standard Showdown", date(2026, 7, 6))


def test_match_header_case_insensitive_name_and_keyword():
    result = match_header("standard store championship (01.02.2026) Final Standings", ALLOWED)
    assert result == ("standard store championship", date(2026, 2, 1))


def test_match_header_rejects_unlisted_name():
    assert match_header("Legacy Brawl (06.07.2026) final standings:", ALLOWED) is None


def test_match_header_rejects_missing_keyword():
    assert match_header("Monday Standard Showdown (06.07.2026) results:", ALLOWED) is None


def test_match_header_rejects_no_date():
    assert match_header("Monday Standard Showdown final standings:", ALLOWED) is None
