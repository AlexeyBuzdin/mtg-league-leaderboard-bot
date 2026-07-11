from datetime import date
from bot.parser import normalize_name, ResultRow, ParsedTournament


def test_normalize_lowercases_trims_collapses():
    assert normalize_name("  James   Smith ") == "james smith"


def test_normalize_idempotent():
    assert normalize_name(normalize_name("Nikita  Powers")) == "nikita powers"


def test_dataclasses_construct():
    row = ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer")
    assert row.points == 9
    t = ParsedTournament("Monday Standard Showdown", date(2026, 7, 6), [row])
    assert t.rows[0].deck == "Temur Harmonizer"
