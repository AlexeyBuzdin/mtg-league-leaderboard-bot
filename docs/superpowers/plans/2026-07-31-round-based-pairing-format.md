# Round-Based Pairing Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the bot from parsing final-standings tables to parsing round-by-round Swiss pairings, storing per-player round records, and deriving the monthly points leaderboard from each player's final-round record.

**Architecture:** `parser.py` is rewritten as a grammar-based state machine over blank-stripped tokens (pairing-start signature `INT → NAME → RECORD`, optional player 2, byes when player 2 is absent). Storage moves from a standings `results` table to a per-player-per-round `round_results` table. `store.fetch_results_in_window` reduces each player's final-round record to points (`3·W + 1·D`) and returns one row per (tournament, player), so `leaderboard.aggregate_totals` is unchanged. Tournament identity/date come from the Discord message (id + timestamp); the `TOURNAMENT_NAMES` allow-list is removed — the parser itself is the message filter.

**Tech Stack:** Python 3.11+, httpx, supabase, pytest, GitHub Actions. (No new dependencies.)

---

## Context for the implementer

This is a **change to an existing, working codebase** on branch `main`. The package `bot/` currently parses a *different*, now-obsolete input format. You will replace that logic. Read each "Modify" file before editing. Run Python via the project venv: `.venv/Scripts/python.exe` (Windows). Full suite: `.venv/Scripts/python.exe -m pytest -q`.

### The input format

One Discord message = one full tournament. Blank lines are separators only. After stripping blank lines, the tokens form repeating pairing blocks. A **full pairing** is 7 tokens:

```
1            pairing number   (a value of 1 opens a new round)
James Doe    player 1 name
1–0–0        player 1 cumulative W–D–L after this round   (en-dash U+2013)
2            player 1 game wins this match
0            player 2 game wins this match
Alexey Doe   player 2 name
0–1–0        player 2 cumulative W–D–L after this round
```

A **bye** is a pairing with only player 1 present (`pairing#, name, record`) and no player 2 block.

### Key rules (already agreed with the product owner)

- **Round detection:** a pairing number equal to `1` starts a new round (numbers reset each round).
- **Points:** MTG match points from each player's **final-round** cumulative record: `points = 3·record_wins + 1·record_draws`. (Verified: reproduces the old points exactly — 3–0–0 → 9, 2–1–0 → 7, 1–2–0 → 3, 0–3–0 → 0.)
- **Player identity:** normalized name via `str.casefold()` + whitespace collapse (Unicode-correct for names like `Artūrs`, `Mārtiņš`).
- **Tournament identity:** Discord `message["id"]` (dedup key, unchanged). **Date:** `message["timestamp"]` converted to a date in the configured timezone. **Name:** the ISO date string (there is no header in the message).
- **Byes / atypical structure:** if player 2's `INT, INT, NAME, RECORD` block is absent after player 1, emit player 1 as a bye (opponent `None`) and resync to the next pairing-start.
- The record separator may be en-dash `–` (U+2013), em-dash `—` (U+2014), or hyphen `-`.

---

## File Structure (after this change)

- `bot/parser.py` — **rewritten.** `PlayerRound` dataclass, `normalize_name`, `parse_record`, `parse_tournament`. Pure, no I/O. (Old `ResultRow`, `ParsedTournament`, `match_header`, `parse_standings_line`, `parse_message` are removed.)
- `bot/store.py` — **modified.** `existing_message_ids` (unchanged), `insert_tournament(message_id, channel_id, name, event_date, rounds)` writes `round_results`, `fetch_results_in_window(start, end)` returns one `{points, player_key, player_name}` per (tournament, player).
- `bot/ingest.py` — **modified.** `run(discord, store, channel_id, timezone)`: no allow-list; parse each message; `event_date` from timestamp; dedup by id.
- `bot/config.py` — **modified.** Remove `tournament_names` / `TOURNAMENT_NAMES`.
- `bot/__main__.py` — **modified.** `_run_ingest` passes `cfg.timezone` instead of `cfg.tournament_names`.
- `bot/leaderboard.py` — **unchanged** (aggregation + run stay as-is).
- `supabase/schema.sql` — **modified.** Drop `results`, add `round_results`, make `tournaments.name` nullable.
- `.env.example`, `.github/workflows/*.yml`, `README.md` — **modified.** Remove `TOURNAMENT_NAMES`.
- Tests: `tests/test_parser.py` rewritten; `tests/test_store.py`, `tests/test_ingest.py`, `tests/test_config.py` updated; `tests/fixtures/` gets a new sample; `tests/test_leaderboard.py` unchanged.

---

## Task 1: Rewrite parser data model, `normalize_name`, `parse_record`

**Files:**
- Modify (replace whole file): `bot/parser.py`
- Modify (replace whole file): `tests/test_parser.py`

- [ ] **Step 1: Replace `tests/test_parser.py` with the failing tests for this task**

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_record'` (or `PlayerRound`).

- [ ] **Step 3: Replace `bot/parser.py` with this minimal version**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

_RECORD_RE = re.compile(r"^(\d+)\s*[–—-]\s*(\d+)\s*[–—-]\s*(\d+)$")


@dataclass
class PlayerRound:
    round: int
    pairing: int
    player_name: str
    player_key: str
    game_wins: int | None
    opponent_name: str | None
    opponent_key: str | None
    opponent_game_wins: int | None
    record_wins: int
    record_draws: int
    record_losses: int


def normalize_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def parse_record(token: str) -> tuple[int, int, int] | None:
    m = _RECORD_RE.match(token.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/parser.py tests/test_parser.py
git commit -m "feat: parser model, casefold normalize, record parsing"
```

---

## Task 2: `parse_tournament` — full pairings and rounds

**Files:**
- Modify: `bot/parser.py`
- Modify: `tests/test_parser.py`
- Create: `tests/fixtures/pairings_sample.txt`

- [ ] **Step 1: Create the fixture** `tests/fixtures/pairings_sample.txt` (two rounds, two pairings each; uses en-dash `–`):

```
1

James Doe
1–0–0

2
0

Alexey Doe
0–1–0

2

Raitis Doe
1–0–0

2
1

Artur Doe
0–1–0
1

Raitis Doe
2–0–0

2
1

James Doe
1–1–0

2

Artur Doe
1–1–0

2
1

Alexey Doe
0–2–0
```

- [ ] **Step 2: Append failing tests to `tests/test_parser.py`**

```python
from pathlib import Path
from bot.parser import parse_tournament

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_tournament_rounds_and_pairings():
    content = (FIXTURES / "pairings_sample.txt").read_text(encoding="utf-8")
    rows = parse_tournament(content)
    assert rows is not None
    # 2 rounds * 2 pairings * 2 players = 8 rows
    assert len(rows) == 8
    # first row: round 1, pairing 1, James beat Alexey 2-0
    first = rows[0]
    assert (first.round, first.pairing) == (1, 1)
    assert first.player_name == "James Doe"
    assert first.player_key == "james doe"
    assert first.game_wins == 2
    assert first.opponent_name == "Alexey Doe"
    assert first.opponent_game_wins == 0
    assert (first.record_wins, first.record_draws, first.record_losses) == (1, 0, 0)
    # its mirror row is the opponent
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
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -k tournament -v`
Expected: FAIL — `ImportError: cannot import name 'parse_tournament'`.

- [ ] **Step 4: Append the implementation to `bot/parser.py`**

```python
def _is_record(token: str) -> bool:
    return _RECORD_RE.match(token.strip()) is not None


def _is_int(token: str) -> bool:
    return token.isdigit()


def _is_name(token: str) -> bool:
    return not _is_int(token) and not _is_record(token)


def parse_tournament(content: str) -> list[PlayerRound] | None:
    tokens = [ln.strip() for ln in content.splitlines() if ln.strip()]
    rows: list[PlayerRound] = []
    round_no = 0
    i = 0
    n = len(tokens)
    while i < n:
        # A pairing starts with: INT (pairing#), NAME (player1), RECORD (player1).
        if not (
            i + 2 < n
            and _is_int(tokens[i])
            and _is_name(tokens[i + 1])
            and _is_record(tokens[i + 2])
        ):
            i += 1  # resync: skip stray token
            continue
        pairing = int(tokens[i])
        p1_name = tokens[i + 1]
        p1_rec = parse_record(tokens[i + 2])
        i += 3
        if pairing == 1:
            round_no += 1
        # Player 2 present iff the next tokens are INT, INT, NAME, RECORD.
        has_p2 = (
            i + 3 < n
            and _is_int(tokens[i])
            and _is_int(tokens[i + 1])
            and _is_name(tokens[i + 2])
            and _is_record(tokens[i + 3])
        )
        if has_p2:
            w1 = int(tokens[i])
            w2 = int(tokens[i + 1])
            p2_name = tokens[i + 2]
            p2_rec = parse_record(tokens[i + 3])
            i += 4
            rows.append(_row(round_no, pairing, p1_name, w1, p2_name, w2, p1_rec))
            rows.append(_row(round_no, pairing, p2_name, w2, p1_name, w1, p2_rec))
        else:
            # Bye: player 1 only, no opponent.
            rows.append(_row(round_no, pairing, p1_name, None, None, None, p1_rec))
    return rows or None


def _row(round_no, pairing, name, game_wins, opp_name, opp_wins, record) -> PlayerRound:
    return PlayerRound(
        round=round_no,
        pairing=pairing,
        player_name=name,
        player_key=normalize_name(name),
        game_wins=game_wins,
        opponent_name=opp_name,
        opponent_key=normalize_name(opp_name) if opp_name else None,
        opponent_game_wins=opp_wins,
        record_wins=record[0],
        record_draws=record[1],
        record_losses=record[2],
    )
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -v`
Expected: PASS (all parser tests).

- [ ] **Step 6: Commit**

```bash
git add bot/parser.py tests/test_parser.py tests/fixtures/pairings_sample.txt
git commit -m "feat: parse round-based pairings into per-player rows"
```

---

## Task 3: `parse_tournament` — bye handling

**Files:**
- Modify: `tests/test_parser.py`

The bye logic is already implemented in Task 2 (the `has_p2` branch). This task adds explicit coverage.

- [ ] **Step 1: Append failing tests to `tests/test_parser.py`**

```python
def test_parse_tournament_handles_bye_minimal():
    # pairing 3 is a bye: player, record, no scores, no opponent
    content = (
        "1\nJames Doe\n1-0-0\n2\n0\nAlexey Doe\n0-1-0\n"
        "3\nRaitis Doe\n1-0-0\n"           # bye
        "1\nJames Doe\n2-0-0\n2\n1\nAlexey Doe\n0-2-0\n"  # round 2 opens (pairing==1)
    )
    rows = parse_tournament(content)
    byes = [r for r in rows if r.opponent_key is None]
    assert len(byes) == 1
    bye = byes[0]
    assert bye.player_key == "raitis doe"
    assert bye.round == 1
    assert bye.pairing == 3
    assert bye.game_wins is None
    assert (bye.record_wins, bye.record_draws, bye.record_losses) == (1, 0, 0)
    # round 2 was still detected after the bye
    assert any(r.round == 2 for r in rows)


def test_parse_tournament_bye_with_trailing_score_resyncs():
    # atypical: a stray score after a bye must not corrupt the next pairing
    content = (
        "3\nRaitis Doe\n1-0-0\n2\n0\n"     # bye-ish with stray scores, no opponent name/record
        "1\nJames Doe\n1-0-0\n2\n0\nAlexey Doe\n0-1-0\n"
    )
    rows = parse_tournament(content)
    # Raitis parsed as a bye (no opponent), James/Alexey parsed cleanly
    assert any(r.player_key == "raitis doe" and r.opponent_key is None for r in rows)
    james = next(r for r in rows if r.player_key == "james doe")
    assert james.opponent_key == "alexey doe"
    assert james.game_wins == 2
```

- [ ] **Step 2: Run to verify behavior**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -k bye -v`
Expected: PASS (2 tests) — the implementation from Task 2 already covers these.

If either FAILS, do not edit the tests: fix `parse_tournament` so byes emit a single opponent-less row and the parser resyncs to the next `INT, NAME, RECORD` pairing-start. Re-run until green.

- [ ] **Step 3: Commit**

```bash
git add tests/test_parser.py
git commit -m "test: cover bye and resync handling in parser"
```

---

## Task 4: Config — remove `TOURNAMENT_NAMES`

**Files:**
- Modify: `bot/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Replace `tests/test_config.py` with**

```python
import pytest
from bot.config import load_config

BASE_ENV = {
    "DISCORD_BOT_TOKEN": "tok",
    "RESULTS_CHANNEL_ID": "111",
    "LEADERBOARD_CHANNEL_ID": "222",
    "SUPABASE_URL": "https://x.supabase.co",
    "SUPABASE_KEY": "key",
}


def test_load_config_parses_values():
    cfg = load_config(BASE_ENV)
    assert cfg.discord_bot_token == "tok"
    assert cfg.results_channel_id == "111"
    assert cfg.leaderboard_channel_id == "222"
    assert cfg.supabase_url == "https://x.supabase.co"
    assert cfg.supabase_key == "key"
    assert cfg.timezone == "Europe/Riga"  # default


def test_timezone_override():
    cfg = load_config({**BASE_ENV, "TIMEZONE": "UTC"})
    assert cfg.timezone == "UTC"


def test_missing_required_var_raises():
    broken = {k: v for k, v in BASE_ENV.items() if k != "SUPABASE_KEY"}
    with pytest.raises(ValueError) as exc:
        load_config(broken)
    assert "SUPABASE_KEY" in str(exc.value)


def test_no_tournament_names_field():
    cfg = load_config(BASE_ENV)
    assert not hasattr(cfg, "tournament_names")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: FAIL — `test_no_tournament_names_field` fails (field still present) and/or `TOURNAMENT_NAMES` still required.

- [ ] **Step 3: Replace `bot/config.py` with**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

_REQUIRED = [
    "DISCORD_BOT_TOKEN",
    "RESULTS_CHANNEL_ID",
    "LEADERBOARD_CHANNEL_ID",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    results_channel_id: str
    leaderboard_channel_id: str
    supabase_url: str
    supabase_key: str
    timezone: str


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = env if env is not None else os.environ
    missing = [k for k in _REQUIRED if not env.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    return Config(
        discord_bot_token=env["DISCORD_BOT_TOKEN"],
        results_channel_id=env["RESULTS_CHANNEL_ID"],
        leaderboard_channel_id=env["LEADERBOARD_CHANNEL_ID"],
        supabase_url=env["SUPABASE_URL"],
        supabase_key=env["SUPABASE_KEY"],
        timezone=env.get("TIMEZONE", "Europe/Riga"),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/config.py tests/test_config.py
git commit -m "refactor: drop TOURNAMENT_NAMES from config"
```

---

## Task 5: Store — write `round_results`, derive points on read

**Files:**
- Modify: `bot/store.py`
- Modify: `tests/test_store.py`

- [ ] **Step 1: Replace `tests/test_store.py` with**

```python
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
    # James: round 1 record 1-0-0, round 2 record 2-0-0 (final) -> 6 pts, 1 event
    # Alexey: round 1 record 0-1-0, round 2 record 0-2-0 (final) -> 0 pts, 1 event
    rows = [
        {"tournament_id": 7, "round": 1, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 1, "record_draws": 0},
        {"tournament_id": 7, "round": 2, "player_key": "james doe",
         "player_name": "James Doe", "record_wins": 2, "record_draws": 0},
        {"tournament_id": 7, "round": 1, "player_key": "alexey doe",
         "player_name": "Alexey Doe", "record_wins": 0, "record_draws": 1},
        {"tournament_id": 7, "round": 2, "player_key": "alexey doe",
         "player_name": "Alexey Doe", "record_wins": 0, "record_draws": 2},
    ]
    rr = FakeTable(rows=rows)
    store = Store(FakeSupabase({"round_results": rr}))
    out = store.fetch_results_in_window(date(2026, 7, 1), date(2026, 7, 31))
    by_key = {r["player_key"]: r for r in out}
    assert by_key["james doe"]["points"] == 6
    assert by_key["james doe"]["player_name"] == "James Doe"
    assert by_key["alexey doe"]["points"] == 0
    assert len(out) == 2  # one row per (tournament, player)
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
    assert len(james_rows) == 2  # two tournaments -> two rows -> aggregate counts 2 events
    assert sorted(r["points"] for r in james_rows) == [3, 9]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -v`
Expected: FAIL — signature/shape mismatches (`insert_tournament` arity, `fetch_results_in_window` no longer returns raw rows).

- [ ] **Step 3: Replace `bot/store.py` with**

```python
from __future__ import annotations

from datetime import date

from bot.parser import PlayerRound


class Store:
    def __init__(self, supabase) -> None:
        self._db = supabase

    def existing_message_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        resp = (
            self._db.table("tournaments")
            .select("discord_message_id")
            .in_("discord_message_id", ids)
            .execute()
        )
        return {row["discord_message_id"] for row in resp.data}

    def insert_tournament(
        self,
        message_id: str,
        channel_id: str,
        name: str,
        event_date: date,
        rounds: list[PlayerRound],
    ) -> None:
        resp = (
            self._db.table("tournaments")
            .insert(
                {
                    "discord_message_id": message_id,
                    "name": name,
                    "event_date": event_date.isoformat(),
                    "channel_id": channel_id,
                }
            )
            .execute()
        )
        tournament_id = resp.data[0]["id"]
        rows = [
            {
                "tournament_id": tournament_id,
                "round": r.round,
                "pairing": r.pairing,
                "player_name": r.player_name,
                "player_key": r.player_key,
                "opponent_name": r.opponent_name,
                "opponent_key": r.opponent_key,
                "game_wins": r.game_wins,
                "opponent_game_wins": r.opponent_game_wins,
                "record_wins": r.record_wins,
                "record_draws": r.record_draws,
                "record_losses": r.record_losses,
            }
            for r in rounds
        ]
        self._db.table("round_results").insert(rows).execute()

    def fetch_results_in_window(self, start: date, end: date) -> list[dict]:
        resp = (
            self._db.table("round_results")
            .select(
                "tournament_id, round, player_key, player_name, "
                "record_wins, record_draws, tournaments!inner(event_date)"
            )
            .gte("tournaments.event_date", start.isoformat())
            .lte("tournaments.event_date", end.isoformat())
            .order("event_date", desc=False, foreign_table="tournaments")
            .execute()
        )
        # Reduce to each player's final-round record per tournament, then points = 3W + D.
        finals: dict[tuple, dict] = {}
        for row in resp.data:
            key = (row["tournament_id"], row["player_key"])
            current = finals.get(key)
            if current is None or row["round"] > current["round"]:
                finals[key] = row
        return [
            {
                "player_key": row["player_key"],
                "player_name": row["player_name"],
                "points": 3 * row["record_wins"] + row["record_draws"],
            }
            for row in finals.values()
        ]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/store.py tests/test_store.py
git commit -m "feat: store round_results and derive monthly points on read"
```

---

## Task 6: Ingest — parse-as-filter, date from message timestamp

**Files:**
- Modify: `bot/ingest.py`
- Modify: `tests/test_ingest.py`

- [ ] **Step 1: Replace `tests/test_ingest.py` with**

```python
from datetime import date
from bot.ingest import run


SAMPLE = (
    "1\nJames Doe\n1-0-0\n2\n0\nAlexey Doe\n0-1-0\n"
    "1\nJames Doe\n2-0-0\n2\n1\nAlexey Doe\n0-2-0\n"
)


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
    def insert_tournament(self, message_id, channel_id, name, event_date, rounds):
        self.inserted.append((message_id, channel_id, name, event_date, rounds))


def test_ingest_inserts_and_derives_date_from_timestamp():
    msg = {"id": "m1", "content": SAMPLE, "timestamp": "2026-07-31T21:30:00+00:00"}
    discord = FakeDiscord([msg])
    store = FakeStore()
    count = run(discord, store, channel_id="111", timezone="Europe/Riga")
    assert count == 1
    message_id, channel_id, name, event_date, rounds = store.inserted[0]
    assert message_id == "m1"
    assert channel_id == "111"
    # 21:30 UTC on 2026-07-31 is 00:30 next day in Riga (+03) -> 2026-08-01
    assert event_date == date(2026, 8, 1)
    assert name == "2026-08-01"
    assert len(rounds) == 4  # 2 rounds * 1 pairing * 2 players


def test_ingest_skips_already_processed():
    msg = {"id": "m1", "content": SAMPLE, "timestamp": "2026-07-31T10:00:00+00:00"}
    store = FakeStore(existing={"m1"})
    count = run(FakeDiscord([msg]), store, channel_id="111", timezone="Europe/Riga")
    assert count == 0
    assert store.inserted == []


def test_ingest_skips_unparseable_messages():
    msg = {"id": "m2", "content": "just chatter", "timestamp": "2026-07-31T10:00:00+00:00"}
    store = FakeStore()
    count = run(FakeDiscord([msg]), store, channel_id="111", timezone="Europe/Riga")
    assert count == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ingest.py -v`
Expected: FAIL — `run()` signature is `(discord, store, channel_id, allowed_names)` and calls `parse_message`.

- [ ] **Step 3: Replace `bot/ingest.py` with**

```python
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.parser import parse_tournament

log = logging.getLogger(__name__)


def run(discord, store, channel_id: str, timezone: str) -> int:
    tz = ZoneInfo(timezone)
    messages = discord.fetch_messages(channel_id, limit=100)
    already = store.existing_message_ids([m["id"] for m in messages])
    inserted = 0
    for message in messages:
        if message["id"] in already:
            continue
        rounds = parse_tournament(message.get("content", ""))
        if not rounds:
            continue
        event_date = datetime.fromisoformat(message["timestamp"]).astimezone(tz).date()
        name = event_date.isoformat()
        store.insert_tournament(message["id"], channel_id, name, event_date, rounds)
        log.info("Ingested tournament %s with %d player-rounds", name, len(rounds))
        inserted += 1
    return inserted
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ingest.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/ingest.py tests/test_ingest.py
git commit -m "feat: ingest round-based tournaments, date from message timestamp"
```

---

## Task 7: CLI — pass timezone to ingest

**Files:**
- Modify: `bot/__main__.py:_run_ingest`
- Test: existing `tests/test_cli.py` (monkeypatches `_run_ingest`) still passes; no change needed.

- [ ] **Step 1: Read `bot/__main__.py` and update `_run_ingest`**

Change the `_run_ingest` function body from passing `cfg.results_channel_id, cfg.tournament_names` to passing `cfg.results_channel_id, cfg.timezone`:

```python
def _run_ingest(cfg: Config) -> None:
    discord, store = _make_clients(cfg)
    count = ingest_run(discord, store, cfg.results_channel_id, cfg.timezone)
    logging.info("Ingest complete: %d new tournament(s)", count)
```

Leave the rest of the file unchanged.

- [ ] **Step 2: Run the CLI tests and full suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: PASS (all tests green — `test_cli.py` monkeypatches `_run_ingest`, so it is unaffected; `test_leaderboard.py` is unchanged and still passes).

- [ ] **Step 3: Commit**

```bash
git add bot/__main__.py
git commit -m "refactor: pass timezone (not allow-list) into ingest"
```

---

## Task 8: Schema — `round_results` replaces `results`

**Files:**
- Modify (replace whole file): `supabase/schema.sql`

- [ ] **Step 1: Replace `supabase/schema.sql` with**

```sql
-- One row per parsed tournament message
create table if not exists tournaments (
  id                  bigint generated always as identity primary key,
  discord_message_id  text not null unique,
  name                text,
  event_date          date not null,
  channel_id          text not null,
  ingested_at         timestamptz not null default now()
);

-- One row per player per pairing (two rows per full pairing, one per bye)
create table if not exists round_results (
  id                 bigint generated always as identity primary key,
  tournament_id      bigint not null references tournaments(id) on delete cascade,
  round              int  not null,
  pairing            int  not null,
  player_name        text not null,
  player_key         text not null,
  opponent_name      text,
  opponent_key       text,
  game_wins          int,
  opponent_game_wins int,
  record_wins        int  not null,
  record_draws       int  not null,
  record_losses      int  not null,
  unique (tournament_id, round, player_key)
);

create index if not exists round_results_player_key_idx on round_results (player_key);
create index if not exists round_results_tournament_idx on round_results (tournament_id, player_key);
create index if not exists tournaments_event_date_idx on tournaments (event_date);
```

- [ ] **Step 2: Note migration for the live database**

If the Supabase project already has the old `results` table, apply this manually in the SQL editor (there is no production data yet per the deployment status): `drop table if exists results;` then run the `create table round_results ...` statement above. Verify with `select count(*) from round_results;` → returns `0`.

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat: replace results table with round_results schema"
```

---

## Task 9: Docs & workflows — remove `TOURNAMENT_NAMES`

**Files:**
- Modify: `.env.example`
- Modify: `.github/workflows/ingest.yml`
- Modify: `.github/workflows/leaderboard.yml`
- Modify: `README.md`

- [ ] **Step 1: Replace `.env.example` with**

```dotenv
DISCORD_BOT_TOKEN=
RESULTS_CHANNEL_ID=
LEADERBOARD_CHANNEL_ID=
SUPABASE_URL=
SUPABASE_KEY=
TIMEZONE=Europe/Riga
```

- [ ] **Step 2: Edit both workflow files** — remove the `TOURNAMENT_NAMES: ${{ secrets.TOURNAMENT_NAMES }}` line from the `env:` block in `.github/workflows/ingest.yml` and `.github/workflows/leaderboard.yml`. Leave the other six env vars intact.

- [ ] **Step 3: Edit `README.md`** — in the "How it works" and "GitHub secrets" sections, remove the `TOURNAMENT_NAMES` reference and update the ingest description. Replace the `ingest` bullet under "How it works" with:

```markdown
- **Daily `ingest`** polls the results channel (Discord REST), parses messages
  containing round-by-round Swiss pairings, and stores per-player round records
  in Supabase (deduplicated by Discord message ID; tournament date taken from the
  message timestamp).
```

And in the GitHub secrets list, remove `TOURNAMENT_NAMES` so it reads:
`DISCORD_BOT_TOKEN`, `RESULTS_CHANNEL_ID`, `LEADERBOARD_CHANNEL_ID`, `SUPABASE_URL`, `SUPABASE_KEY`, `TIMEZONE`.

- [ ] **Step 4: Verify the full suite still passes**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add .env.example .github/workflows/ingest.yml .github/workflows/leaderboard.yml README.md
git commit -m "docs: drop TOURNAMENT_NAMES; document round-based ingest"
```

---

## Self-Review Notes

- **Coverage vs. confirmed design:** round-based parsing (Tasks 1–3), byes/atypical → single row + resync (Task 3), casefold Unicode identity (Task 1), points `3W+D` from final-round record (Task 5), one row per (tournament, player) so `aggregate_totals` is unchanged (Task 5), date from message timestamp in TZ (Task 6), parser-as-filter / no allow-list (Tasks 4, 6, 7, 9), schema swap (Task 8), docs/workflows cleanup (Task 9). `leaderboard.py` intentionally untouched.
- **Type consistency:** `PlayerRound` fields are used identically across parser → store → ingest. `insert_tournament(message_id, channel_id, name, event_date, rounds)` and `run(discord, store, channel_id, timezone)` signatures match every call site (store test, ingest test, `__main__`). `fetch_results_in_window` returns `{player_key, player_name, points}` — exactly what the unchanged `aggregate_totals` consumes.
- **Placeholders:** none — every code step is complete.
- **Known assumption to revisit:** the exact byte layout of a real bye is unconfirmed; the parser treats any non-two-player block as a single-player bye and resyncs on the `INT, NAME, RECORD` signature. If a real bye example differs, only `parse_tournament` needs adjusting.
- **Migration:** old standings `results` table and any prior rows are dropped (no production data yet). `TOURNAMENT_NAMES` secret becomes unused; it can be deleted from the GitHub repo settings but leaving it causes no harm.
