from datetime import date
from pathlib import Path
from bot.parser import normalize_name, ResultRow, ParsedTournament
from bot.parser import match_header
from bot.parser import parse_standings_line
from bot.parser import parse_message


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


def test_match_header_tolerates_extra_internal_whitespace():
    result = match_header("Monday  Standard   Showdown (06.07.2026) final standings:", ALLOWED)
    assert result == ("Monday  Standard   Showdown", date(2026, 7, 6))


def test_parse_row_with_deck():
    row = parse_standings_line("1    James Smith     9    3/0/0    44.3%    66.7%    45.9%     (Temur Harmonizer)")
    assert row == ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer")


def test_parse_row_without_deck():
    row = parse_standings_line("3    Artur Brown    6    2/1/0    59.3%    62.5%    62.7%     ")
    assert row == ResultRow(3, "Artur Brown", "artur brown", 6, 2, 1, 0, None)


def test_parse_row_single_word_name():
    row = parse_standings_line("5   Bob   4   1/1/1   50.0%   50.0%   50.0%")
    assert row == ResultRow(5, "Bob", "bob", 4, 1, 1, 1, None)


def test_parse_blank_or_header_returns_none():
    assert parse_standings_line("") is None
    assert parse_standings_line("Monday Standard Showdown (06.07.2026) final standings:") is None
    assert parse_standings_line("some random chatter") is None


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_message_full():
    content = (FIXTURES / "sample_message.txt").read_text(encoding="utf-8")
    t = parse_message(content, ALLOWED)
    assert t is not None
    assert t.name == "Monday Standard Showdown"
    assert t.event_date == date(2026, 7, 6)
    assert len(t.rows) == 3
    assert t.rows[0] == ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer")
    assert t.rows[2].deck is None


def test_parse_message_non_matching_header_returns_none():
    assert parse_message("just chatting here\n1 Bob 3 1/0/0", ALLOWED) is None


def test_parse_message_matching_header_no_rows_returns_none():
    content = "Monday Standard Showdown (06.07.2026) final standings:\n\n(no results yet)"
    assert parse_message(content, ALLOWED) is None
