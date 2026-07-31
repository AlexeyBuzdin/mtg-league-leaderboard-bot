# MTG League Leaderboard Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python Discord bot (run as two GitHub Actions cron jobs) that ingests MTG tournament results from a Discord channel into Supabase and posts a weekly monthly-leaderboard embed.

**Architecture:** Two stateless CLI entry points (`ingest`, `leaderboard`) share a small package. `parser.py` holds pure string→data functions (the risky part, fully unit-tested); `discord_client.py` and `store.py` are thin I/O adapters; `ingest.py`/`leaderboard.py` orchestrate. Monthly aggregation is a pure Python function fed by a simple windowed DB fetch, so it is testable without a database.

**Tech Stack:** Python 3.11+, `httpx` (Discord REST), `supabase` (supabase-py), `pytest`, GitHub Actions.

---

## File Structure

- `bot/__init__.py` — package marker
- `bot/config.py` — `Config` dataclass + `load_config(env)`; env validation
- `bot/parser.py` — `ResultRow`, `ParsedTournament`, `normalize_name`, `match_header`, `parse_standings_line`, `parse_message` (pure)
- `bot/discord_client.py` — `DiscordClient.fetch_messages`, `.post_embeds` (httpx)
- `bot/store.py` — `Store.existing_message_ids`, `.insert_tournament`, `.fetch_results_in_window`
- `bot/leaderboard.py` — `PlayerTotal`, `month_window`, `aggregate_totals`, `build_leaderboard_embeds`, `run`
- `bot/ingest.py` — `run` (fetch→filter→parse→dedup→store)
- `bot/__main__.py` — CLI dispatch
- `tests/` — one test module per unit + `fixtures/`
- `supabase/schema.sql`
- `.github/workflows/ingest.yml`, `.github/workflows/leaderboard.yml`
- `pyproject.toml`, `.env.example`, `README.md`

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `bot/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "mtg-league-leaderboard-bot"
version = "0.1.0"
description = "Discord bot that ingests MTG tournament results and posts a monthly leaderboard"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "supabase>=2.4",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["bot*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty package markers**

`bot/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.env
.pytest_cache/
*.egg-info/
```

- [ ] **Step 4: Create venv and install**

Run:
```bash
python -m venv .venv && . .venv/Scripts/activate && pip install -e ".[dev]"
```
Expected: installs httpx, supabase, pytest with no errors.

- [ ] **Step 5: Verify pytest runs (no tests yet)**

Run: `pytest -q`
Expected: `no tests ran` (exit 5) — confirms discovery works.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml bot/__init__.py tests/__init__.py .gitignore
git commit -m "chore: scaffold python package and tooling"
```

---

## Task 2: Config loader

**Files:**
- Create: `bot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import pytest
from bot.config import load_config

BASE_ENV = {
    "DISCORD_BOT_TOKEN": "tok",
    "RESULTS_CHANNEL_ID": "111",
    "LEADERBOARD_CHANNEL_ID": "222",
    "SUPABASE_URL": "https://x.supabase.co",
    "SUPABASE_KEY": "key",
    "TOURNAMENT_NAMES": "Monday Standard Showdown, Standard Store Championship",
}


def test_load_config_parses_values():
    cfg = load_config(BASE_ENV)
    assert cfg.discord_bot_token == "tok"
    assert cfg.results_channel_id == "111"
    assert cfg.leaderboard_channel_id == "222"
    assert cfg.supabase_url == "https://x.supabase.co"
    assert cfg.supabase_key == "key"
    assert cfg.tournament_names == ["Monday Standard Showdown", "Standard Store Championship"]
    assert cfg.timezone == "Europe/Riga"  # default


def test_timezone_override():
    cfg = load_config({**BASE_ENV, "TIMEZONE": "UTC"})
    assert cfg.timezone == "UTC"


def test_missing_required_var_raises():
    broken = {k: v for k, v in BASE_ENV.items() if k != "SUPABASE_KEY"}
    with pytest.raises(ValueError) as exc:
        load_config(broken)
    assert "SUPABASE_KEY" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.config'`

- [ ] **Step 3: Write minimal implementation**

`bot/config.py`:
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
    "TOURNAMENT_NAMES",
]


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    results_channel_id: str
    leaderboard_channel_id: str
    supabase_url: str
    supabase_key: str
    tournament_names: list[str]
    timezone: str


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = env if env is not None else os.environ
    missing = [k for k in _REQUIRED if not env.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    names = [n.strip() for n in env["TOURNAMENT_NAMES"].split(",") if n.strip()]
    return Config(
        discord_bot_token=env["DISCORD_BOT_TOKEN"],
        results_channel_id=env["RESULTS_CHANNEL_ID"],
        leaderboard_channel_id=env["LEADERBOARD_CHANNEL_ID"],
        supabase_url=env["SUPABASE_URL"],
        supabase_key=env["SUPABASE_KEY"],
        tournament_names=names,
        timezone=env.get("TIMEZONE", "Europe/Riga"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/config.py tests/test_config.py
git commit -m "feat: add config loader with env validation"
```

---

## Task 3: Parser — data models and `normalize_name`

**Files:**
- Create: `bot/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

`tests/test_parser.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.parser'`

- [ ] **Step 3: Write minimal implementation**

`bot/parser.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ResultRow:
    standing: int
    player_name: str
    player_key: str
    points: int
    wins: int
    draws: int
    losses: int
    deck: str | None


@dataclass
class ParsedTournament:
    name: str
    event_date: date
    rows: list[ResultRow]


def normalize_name(name: str) -> str:
    return " ".join(name.split()).lower()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/parser.py tests/test_parser.py
git commit -m "feat: add parser data models and normalize_name"
```

---

## Task 4: Parser — `match_header`

**Files:**
- Modify: `bot/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_parser.py`)**

```python
from bot.parser import match_header

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py -k match_header -v`
Expected: FAIL — `ImportError: cannot import name 'match_header'`

- [ ] **Step 3: Write minimal implementation (append to `bot/parser.py`)**

```python
import re
from datetime import datetime

_HEADER_RE = re.compile(
    r"^(?P<name>.+?)\s*\((?P<date>\d{2}\.\d{2}\.\d{4})\)\s*final standings:?\s*$",
    re.IGNORECASE,
)


def match_header(line: str, allowed_names: list[str]) -> tuple[str, date] | None:
    m = _HEADER_RE.match(line.strip())
    if not m:
        return None
    name = m.group("name").strip()
    allowed = {n.strip().lower() for n in allowed_names}
    if name.lower() not in allowed:
        return None
    try:
        event_date = datetime.strptime(m.group("date"), "%d.%m.%Y").date()
    except ValueError:
        return None
    return name, event_date
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -k match_header -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/parser.py tests/test_parser.py
git commit -m "feat: add tournament header matching"
```

---

## Task 5: Parser — `parse_standings_line`

**Files:**
- Modify: `bot/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_parser.py`)**

```python
from bot.parser import parse_standings_line


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py -k standings -v`
Expected: FAIL — `ImportError: cannot import name 'parse_standings_line'`

- [ ] **Step 3: Write minimal implementation (append to `bot/parser.py`)**

Note: the `(?:.*\(...\))?` group is greedy so a present deck is captured at the end; when absent the whole optional group is skipped. The trailing `.*$` (not `\s*$`) is required so the ignored percentage columns between W/D/L and the deck are consumed when no deck is present.

```python
_ROW_RE = re.compile(
    r"^\s*(?P<standing>\d+)\s+(?P<name>.+?)\s+(?P<points>\d+)\s+"
    r"(?P<w>\d+)/(?P<d>\d+)/(?P<l>\d+)"
    r"(?:.*\((?P<deck>[^)]+)\))?.*$"
)


def parse_standings_line(line: str) -> ResultRow | None:
    m = _ROW_RE.match(line)
    if not m:
        return None
    name = m.group("name").strip()
    deck = m.group("deck")
    return ResultRow(
        standing=int(m.group("standing")),
        player_name=name,
        player_key=normalize_name(name),
        points=int(m.group("points")),
        wins=int(m.group("w")),
        draws=int(m.group("d")),
        losses=int(m.group("l")),
        deck=deck.strip() if deck else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -k standings -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/parser.py tests/test_parser.py
git commit -m "feat: add standings row parsing"
```

---

## Task 6: Parser — `parse_message`

**Files:**
- Modify: `bot/parser.py`
- Create: `tests/fixtures/sample_message.txt`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Create the fixture**

`tests/fixtures/sample_message.txt`:
```
Monday Standard Showdown (06.07.2026) final standings:

1    James Smith     9    3/0/0    44.3%    66.7%    45.9%     (Temur Harmonizer)
2    Nikita Powers    7    2/0/1    59.3%    71.4%    56.5%     (Jeskai Control)
3    Artur Brown    6    2/1/0    59.3%    62.5%    62.7%
```

- [ ] **Step 2: Write the failing test (append to `tests/test_parser.py`)**

```python
from pathlib import Path
from bot.parser import parse_message

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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_parser.py -k parse_message -v`
Expected: FAIL — `ImportError: cannot import name 'parse_message'`

- [ ] **Step 4: Write minimal implementation (append to `bot/parser.py`)**

```python
def parse_message(content: str, allowed_names: list[str]) -> ParsedTournament | None:
    lines = content.splitlines()
    if not lines:
        return None
    header = match_header(lines[0], allowed_names)
    if header is None:
        return None
    name, event_date = header
    rows = [r for r in (parse_standings_line(l) for l in lines[1:]) if r is not None]
    if not rows:
        return None
    return ParsedTournament(name=name, event_date=event_date, rows=rows)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_parser.py -v`
Expected: PASS (all parser tests)

- [ ] **Step 6: Commit**

```bash
git add bot/parser.py tests/test_parser.py tests/fixtures/sample_message.txt
git commit -m "feat: add whole-message parsing"
```

---

## Task 7: Discord REST client

**Files:**
- Create: `bot/discord_client.py`
- Test: `tests/test_discord_client.py`

- [ ] **Step 1: Write the failing test**

`tests/test_discord_client.py`:
```python
import httpx
from bot.discord_client import DiscordClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://discord.com/api/v10")
    return DiscordClient(token="tok", http=http)


def test_fetch_messages_returns_id_and_content():
    def handler(request):
        assert request.headers["Authorization"] == "Bot tok"
        assert request.url.path == "/api/v10/channels/111/messages"
        assert request.url.params["limit"] == "100"
        return httpx.Response(200, json=[
            {"id": "1", "content": "hello"},
            {"id": "2", "content": "world"},
        ])
    client = _client(handler)
    msgs = client.fetch_messages("111", limit=100)
    assert msgs == [{"id": "1", "content": "hello"}, {"id": "2", "content": "world"}]


def test_post_embeds_sends_payload():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["json"] = httpx.Response(200)._request  # placeholder, replaced below
        import json
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "9"})
    client = _client(handler)
    client.post_embeds("222", [{"title": "T"}])
    assert seen["path"] == "/api/v10/channels/222/messages"
    assert seen["body"] == {"embeds": [{"title": "T"}]}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_discord_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.discord_client'`

- [ ] **Step 3: Write minimal implementation**

`bot/discord_client.py`:
```python
from __future__ import annotations

import httpx

_API_BASE = "https://discord.com/api/v10"


class DiscordClient:
    def __init__(self, token: str, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(base_url=_API_BASE)
        self._headers = {"Authorization": f"Bot {token}"}

    def fetch_messages(self, channel_id: str, limit: int = 100) -> list[dict]:
        resp = self._http.get(
            f"/channels/{channel_id}/messages",
            params={"limit": limit},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    def post_embeds(self, channel_id: str, embeds: list[dict]) -> None:
        resp = self._http.post(
            f"/channels/{channel_id}/messages",
            json={"embeds": embeds},
            headers=self._headers,
        )
        resp.raise_for_status()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_discord_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/discord_client.py tests/test_discord_client.py
git commit -m "feat: add discord REST client"
```

---

## Task 8: Supabase store

**Files:**
- Create: `bot/store.py`
- Test: `tests/test_store.py`

The store depends only on the small slice of the supabase-py API it uses. Tests inject a hand-written fake implementing that chain.

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:
```python
from datetime import date
from bot.parser import ResultRow, ParsedTournament
from bot.store import Store


class FakeQuery:
    def __init__(self, table):
        self.table = table
        self._filter = None

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
        self.table.inserted.append(payload)
        return self

    def execute(self):
        if self._filter:
            col, values = self._filter
            rows = [r for r in self.table.rows if r.get(col) in values]
            return type("R", (), {"data": rows})
        return type("R", (), {"data": list(self.table.rows)})


class FakeTable:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.inserted = []
        self.calls = []

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


def test_insert_tournament_writes_tournament_then_results():
    tournaments = FakeTable(rows=[])
    # Simulate the tournaments insert returning the new id.
    def exec_with_id(self):
        tournaments.inserted_ok = True
        return type("R", (), {"data": [{"id": 42}]})
    FakeQuery.execute_insert = exec_with_id

    results = FakeTable(rows=[])
    tables = {"tournaments": tournaments, "results": results}
    store = Store(FakeSupabase(tables))

    t = ParsedTournament("Monday Standard Showdown", date(2026, 7, 6), [
        ResultRow(1, "James Smith", "james smith", 9, 3, 0, 0, "Temur Harmonizer"),
    ])
    store.insert_tournament("msg1", "chan1", t)

    assert tournaments.inserted[0]["discord_message_id"] == "msg1"
    assert tournaments.inserted[0]["name"] == "Monday Standard Showdown"
    assert tournaments.inserted[0]["event_date"] == "2026-07-06"
    assert results.inserted[0][0]["tournament_id"] == 42
    assert results.inserted[0][0]["player_key"] == "james smith"


def test_fetch_results_in_window_returns_rows():
    joined = FakeTable(rows=[
        {"points": 9, "player_key": "james smith", "player_name": "James Smith",
         "tournaments": {"event_date": "2026-07-06"}},
    ])
    store = Store(FakeSupabase({"results": joined}))
    rows = store.fetch_results_in_window(date(2026, 7, 1), date(2026, 7, 31))
    assert rows[0]["player_key"] == "james smith"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.store'`

- [ ] **Step 3: Write minimal implementation**

`bot/store.py`:
```python
from __future__ import annotations

from datetime import date

from bot.parser import ParsedTournament


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

    def insert_tournament(self, message_id: str, channel_id: str, t: ParsedTournament) -> None:
        resp = (
            self._db.table("tournaments")
            .insert(
                {
                    "discord_message_id": message_id,
                    "name": t.name,
                    "event_date": t.event_date.isoformat(),
                    "channel_id": channel_id,
                }
            )
            .execute()
        )
        tournament_id = resp.data[0]["id"]
        rows = [
            {
                "tournament_id": tournament_id,
                "standing": r.standing,
                "player_name": r.player_name,
                "player_key": r.player_key,
                "points": r.points,
                "wins": r.wins,
                "draws": r.draws,
                "losses": r.losses,
                "deck": r.deck,
            }
            for r in t.rows
        ]
        self._db.table("results").insert(rows).execute()

    def fetch_results_in_window(self, start: date, end: date) -> list[dict]:
        resp = (
            self._db.table("results")
            .select("points, player_key, player_name, tournaments!inner(event_date)")
            .gte("tournaments.event_date", start.isoformat())
            .lte("tournaments.event_date", end.isoformat())
            .execute()
        )
        return resp.data
```

Note: the FakeQuery in the test routes `.insert(...).execute()` through the same `execute` that returns `{"data": [{"id": 42}]}` via the `execute_insert` shim; keep the fake and implementation in sync if the insert return shape changes.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/store.py tests/test_store.py
git commit -m "feat: add supabase store adapter"
```

---

## Task 9: Leaderboard pure logic — window, aggregate, embeds

**Files:**
- Create: `bot/leaderboard.py`
- Test: `tests/test_leaderboard.py`

- [ ] **Step 1: Write the failing test**

`tests/test_leaderboard.py`:
```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from bot.leaderboard import month_window, aggregate_totals, build_leaderboard_embeds, PlayerTotal


def test_month_window_current_calendar_month():
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    start, end = month_window(now)
    assert start == date(2026, 7, 1)
    assert end == date(2026, 7, 15)


def test_aggregate_sums_and_sorts_desc():
    rows = [
        {"points": 9, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 6, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 7, "player_key": "nikita powers", "player_name": "Nikita Powers"},
    ]
    totals = aggregate_totals(rows)
    assert totals[0] == PlayerTotal("james smith", "James Smith", 15, 2)
    assert totals[1] == PlayerTotal("nikita powers", "Nikita Powers", 7, 1)


def test_aggregate_tie_broken_alphabetically():
    rows = [
        {"points": 5, "player_key": "bob", "player_name": "Bob"},
        {"points": 5, "player_key": "alice", "player_name": "Alice"},
    ]
    totals = aggregate_totals(rows)
    assert [t.display_name for t in totals] == ["Alice", "Bob"]


def test_aggregate_uses_latest_display_name():
    rows = [
        {"points": 3, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 3, "player_key": "james smith", "player_name": "james  smith"},
    ]
    # rows arrive oldest-first; latest spelling wins
    totals = aggregate_totals(rows)
    assert totals[0].display_name == "james  smith"


def test_build_embeds_single_when_small():
    totals = [PlayerTotal("a", "Alice", 10, 2), PlayerTotal("b", "Bob", 5, 1)]
    embeds = build_leaderboard_embeds(totals, "July 2026")
    assert len(embeds) == 1
    assert "July 2026" in embeds[0]["title"]
    assert "1. Alice — 10 pts (2 events)" in embeds[0]["description"]
    assert "2. Bob — 5 pts (1 event)" in embeds[0]["description"]


def test_build_embeds_chunks_when_large():
    totals = [PlayerTotal(f"p{i}", f"Player{i}", 100 - i, 1) for i in range(60)]
    embeds = build_leaderboard_embeds(totals, "July 2026")
    assert len(embeds) == 2  # 50 per embed
    assert "1. Player0" in embeds[0]["description"]
    assert "51. Player50" in embeds[1]["description"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_leaderboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.leaderboard'`

- [ ] **Step 3: Write minimal implementation**

`bot/leaderboard.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

_PER_EMBED = 50


@dataclass
class PlayerTotal:
    player_key: str
    display_name: str
    points: int
    events: int


def month_window(now: datetime) -> tuple[date, date]:
    today = now.date()
    return today.replace(day=1), today


def aggregate_totals(rows: list[dict]) -> list[PlayerTotal]:
    acc: dict[str, PlayerTotal] = {}
    for row in rows:
        key = row["player_key"]
        current = acc.get(key)
        if current is None:
            acc[key] = PlayerTotal(key, row["player_name"], row["points"], 1)
        else:
            # rows arrive oldest-first, so overwrite display name with the latest
            acc[key] = PlayerTotal(
                key,
                row["player_name"],
                current.points + row["points"],
                current.events + 1,
            )
    return sorted(acc.values(), key=lambda t: (-t.points, t.display_name.lower()))


def _line(rank: int, t: PlayerTotal) -> str:
    unit = "event" if t.events == 1 else "events"
    return f"{rank}. {t.display_name} — {t.points} pts ({t.events} {unit})"


def build_leaderboard_embeds(totals: list[PlayerTotal], month_label: str) -> list[dict]:
    embeds: list[dict] = []
    for start in range(0, max(len(totals), 1), _PER_EMBED):
        chunk = totals[start : start + _PER_EMBED]
        lines = [_line(start + i + 1, t) for i, t in enumerate(chunk)]
        title = f"🏆 Standard League — {month_label}"
        if start > 0:
            title += f" (cont.)"
        embeds.append({"title": title, "description": "\n".join(lines)})
    return embeds
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_leaderboard.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/leaderboard.py tests/test_leaderboard.py
git commit -m "feat: add leaderboard aggregation and embed building"
```

---

## Task 10: Ingest orchestration

**Files:**
- Create: `bot/ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ingest.py`:
```python
from datetime import date
from bot.ingest import run
from bot.parser import ParsedTournament


SAMPLE = (
    "Monday Standard Showdown (06.07.2026) final standings:\n\n"
    "1    James Smith     9    3/0/0    44.3%    66.7%    45.9%     (Temur Harmonizer)\n"
    "2    Nikita Powers    7    2/0/1    59.3%    71.4%    56.5%\n"
)
ALLOWED = ["Monday Standard Showdown", "Standard Store Championship"]


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
    def insert_tournament(self, message_id, channel_id, t):
        self.inserted.append((message_id, channel_id, t))


def test_ingest_inserts_new_tournament():
    discord = FakeDiscord([{"id": "m1", "content": SAMPLE}])
    store = FakeStore()
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 1
    message_id, channel_id, t = store.inserted[0]
    assert message_id == "m1"
    assert channel_id == "111"
    assert isinstance(t, ParsedTournament)
    assert t.event_date == date(2026, 7, 6)
    assert len(t.rows) == 2


def test_ingest_skips_already_processed():
    discord = FakeDiscord([{"id": "m1", "content": SAMPLE}])
    store = FakeStore(existing={"m1"})
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 0
    assert store.inserted == []


def test_ingest_skips_non_matching_messages():
    discord = FakeDiscord([{"id": "m2", "content": "just some chatter"}])
    store = FakeStore()
    count = run(discord, store, channel_id="111", allowed_names=ALLOWED)
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.ingest'`

- [ ] **Step 3: Write minimal implementation**

`bot/ingest.py`:
```python
from __future__ import annotations

import logging

from bot.parser import parse_message

log = logging.getLogger(__name__)


def run(discord, store, channel_id: str, allowed_names: list[str]) -> int:
    messages = discord.fetch_messages(channel_id, limit=100)
    already = store.existing_message_ids([m["id"] for m in messages])
    inserted = 0
    for message in messages:
        if message["id"] in already:
            continue
        tournament = parse_message(message.get("content", ""), allowed_names)
        if tournament is None:
            continue
        store.insert_tournament(message["id"], channel_id, tournament)
        log.info("Ingested %s (%s) with %d rows", tournament.name,
                 tournament.event_date, len(tournament.rows))
        inserted += 1
    return inserted
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/ingest.py tests/test_ingest.py
git commit -m "feat: add ingest orchestration"
```

---

## Task 11: Leaderboard orchestration (`run`)

**Files:**
- Modify: `bot/leaderboard.py`
- Test: `tests/test_leaderboard.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_leaderboard.py`)**

```python
from bot.leaderboard import run as leaderboard_run


class FakeStore2:
    def __init__(self, rows):
        self._rows = rows
        self.window = None
    def fetch_results_in_window(self, start, end):
        self.window = (start, end)
        return self._rows


class FakeDiscord2:
    def __init__(self):
        self.posted = None
    def post_embeds(self, channel_id, embeds):
        self.posted = (channel_id, embeds)


def test_leaderboard_run_posts_embed():
    rows = [
        {"points": 9, "player_key": "james smith", "player_name": "James Smith"},
        {"points": 7, "player_key": "nikita powers", "player_name": "Nikita Powers"},
    ]
    store = FakeStore2(rows)
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    posted = leaderboard_run(discord, store, channel_id="222", now=now)
    assert posted is True
    assert store.window == (date(2026, 7, 1), date(2026, 7, 15))
    channel_id, embeds = discord.posted
    assert channel_id == "222"
    assert "July 2026" in embeds[0]["title"]
    assert "1. James Smith — 9 pts" in embeds[0]["description"]


def test_leaderboard_run_skips_when_empty():
    store = FakeStore2([])
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    posted = leaderboard_run(discord, store, channel_id="222", now=now)
    assert posted is False
    assert discord.posted is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_leaderboard.py -k run -v`
Expected: FAIL — `ImportError: cannot import name 'run'`

- [ ] **Step 3: Write minimal implementation (append to `bot/leaderboard.py`)**

```python
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def run(discord, store, channel_id: str, now: datetime) -> bool:
    start, end = month_window(now)
    rows = store.fetch_results_in_window(start, end)
    totals = aggregate_totals(rows)
    if not totals:
        return False
    label = f"{_MONTHS[start.month - 1]} {start.year}"
    embeds = build_leaderboard_embeds(totals, label)
    discord.post_embeds(channel_id, embeds)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_leaderboard.py -v`
Expected: PASS (all leaderboard tests)

- [ ] **Step 5: Commit**

```bash
git add bot/leaderboard.py tests/test_leaderboard.py
git commit -m "feat: add leaderboard run orchestration"
```

---

## Task 12: CLI entry point

**Files:**
- Create: `bot/__main__.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import bot.__main__ as cli


def test_build_arg_parser_accepts_commands():
    parser = cli.build_parser()
    assert parser.parse_args(["ingest"]).command == "ingest"
    assert parser.parse_args(["leaderboard"]).command == "leaderboard"


def test_main_dispatches_ingest(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "_run_ingest", lambda cfg: called.setdefault("ingest", True))
    monkeypatch.setattr(cli, "load_config", lambda: object())
    cli.main(["ingest"])
    assert called == {"ingest": True}


def test_main_dispatches_leaderboard(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "_run_leaderboard", lambda cfg: called.setdefault("lb", True))
    monkeypatch.setattr(cli, "load_config", lambda: object())
    cli.main(["leaderboard"])
    assert called == {"lb": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'bot.__main__' has no attribute 'build_parser'`

- [ ] **Step 3: Write minimal implementation**

`bot/__main__.py`:
```python
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from bot.config import Config, load_config
from bot.discord_client import DiscordClient
from bot.ingest import run as ingest_run
from bot.leaderboard import run as leaderboard_run
from bot.store import Store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    sub.add_parser("leaderboard")
    return parser


def _make_clients(cfg: Config) -> tuple[DiscordClient, Store]:
    discord = DiscordClient(cfg.discord_bot_token)
    store = Store(create_client(cfg.supabase_url, cfg.supabase_key))
    return discord, store


def _run_ingest(cfg: Config) -> None:
    discord, store = _make_clients(cfg)
    count = ingest_run(discord, store, cfg.results_channel_id, cfg.tournament_names)
    logging.info("Ingest complete: %d new tournament(s)", count)


def _run_leaderboard(cfg: Config) -> None:
    discord, store = _make_clients(cfg)
    now = datetime.now(ZoneInfo(cfg.timezone))
    posted = leaderboard_run(discord, store, cfg.leaderboard_channel_id, now)
    logging.info("Leaderboard posted: %s", posted)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    cfg = load_config()
    if args.command == "ingest":
        _run_ingest(cfg)
    elif args.command == "leaderboard":
        _run_leaderboard(cfg)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 6: Commit**

```bash
git add bot/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point"
```

---

## Task 13: Supabase schema

**Files:**
- Create: `supabase/schema.sql`

- [ ] **Step 1: Write the schema**

`supabase/schema.sql`:
```sql
-- One row per parsed results message
create table if not exists tournaments (
  id                  bigint generated always as identity primary key,
  discord_message_id  text not null unique,
  name                text not null,
  event_date          date not null,
  channel_id          text not null,
  ingested_at         timestamptz not null default now()
);

-- One row per player line in a tournament
create table if not exists results (
  id              bigint generated always as identity primary key,
  tournament_id   bigint not null references tournaments(id) on delete cascade,
  standing        int  not null,
  player_name     text not null,
  player_key      text not null,
  points          int  not null,
  wins            int  not null,
  draws           int  not null,
  losses          int  not null,
  deck            text,
  unique (tournament_id, standing)
);

create index if not exists results_player_key_idx on results (player_key);
create index if not exists tournaments_event_date_idx on tournaments (event_date);
```

- [ ] **Step 2: Apply it (manual, documented)**

Apply via the Supabase SQL editor or CLI. Verify tables exist:
Run (Supabase SQL editor): `select count(*) from tournaments;`
Expected: returns `0` with no error.

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat: add supabase schema"
```

---

## Task 14: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/ingest.yml`
- Create: `.github/workflows/leaderboard.yml`

- [ ] **Step 1: Write the ingest workflow**

`.github/workflows/ingest.yml`:
```yaml
name: ingest
on:
  schedule:
    - cron: "0 21 * * *"   # ~00:00 Europe/Riga
  workflow_dispatch:

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: python -m bot ingest
        env:
          DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
          RESULTS_CHANNEL_ID: ${{ secrets.RESULTS_CHANNEL_ID }}
          LEADERBOARD_CHANNEL_ID: ${{ secrets.LEADERBOARD_CHANNEL_ID }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          TOURNAMENT_NAMES: ${{ secrets.TOURNAMENT_NAMES }}
          TIMEZONE: ${{ secrets.TIMEZONE }}
```

- [ ] **Step 2: Write the leaderboard workflow**

`.github/workflows/leaderboard.yml`:
```yaml
name: leaderboard
on:
  schedule:
    - cron: "0 7 * * 1"    # Mondays ~10:00 Europe/Riga
  workflow_dispatch:

jobs:
  leaderboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: python -m bot leaderboard
        env:
          DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
          RESULTS_CHANNEL_ID: ${{ secrets.RESULTS_CHANNEL_ID }}
          LEADERBOARD_CHANNEL_ID: ${{ secrets.LEADERBOARD_CHANNEL_ID }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          TOURNAMENT_NAMES: ${{ secrets.TOURNAMENT_NAMES }}
          TIMEZONE: ${{ secrets.TIMEZONE }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ingest.yml .github/workflows/leaderboard.yml
git commit -m "ci: add ingest and leaderboard scheduled workflows"
```

---

## Task 15: Docs — `.env.example` and README

**Files:**
- Create: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Write `.env.example`**

```dotenv
DISCORD_BOT_TOKEN=
RESULTS_CHANNEL_ID=
LEADERBOARD_CHANNEL_ID=
SUPABASE_URL=
SUPABASE_KEY=
TOURNAMENT_NAMES=Monday Standard Showdown,Standard Store Championship
TIMEZONE=Europe/Riga
```

- [ ] **Step 2: Write the README**

`README.md`:
````markdown
# mtg-league-leaderboard-bot

Discord bot for MTG Latvia that ingests MTG tournament results and posts a
monthly leaderboard. Runs as two GitHub Actions cron jobs.

## How it works

- **Daily `ingest`** polls the results channel (Discord REST), parses messages
  whose header matches `<Tournament Name> (dd.mm.yyyy) final standings:` for a
  configured tournament name, and stores standings in Supabase (deduplicated by
  Discord message ID).
- **Weekly `leaderboard`** sums points per attendee for the current calendar
  month and posts a rich embed to the leaderboard channel.

## Setup

### 1. Discord bot
1. Create an application + bot at the Discord Developer Portal.
2. Enable the **Message Content Intent** (Bot → Privileged Gateway Intents).
3. Invite the bot to the server with read access to the results channel and
   send access to the leaderboard channel.
4. Copy the bot token and the two channel IDs.

### 2. Supabase
1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL editor.
3. Copy the project URL and the service-role key.

### 3. GitHub secrets
Add these repository secrets (Settings → Secrets → Actions):
`DISCORD_BOT_TOKEN`, `RESULTS_CHANNEL_ID`, `LEADERBOARD_CHANNEL_ID`,
`SUPABASE_URL`, `SUPABASE_KEY`, `TOURNAMENT_NAMES`, `TIMEZONE`.

## Local development

```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -e ".[dev]"
pytest -q
```

Copy `.env.example` to `.env` and fill it in to run locally:

```bash
python -m bot ingest
python -m bot leaderboard
```

## Manual verification

Both workflows support `workflow_dispatch` — trigger them from the Actions tab
to run a real ingest or leaderboard post on demand.
````

- [ ] **Step 3: Commit**

```bash
git add .env.example README.md
git commit -m "docs: add setup readme and env example"
```

---

## Self-Review Notes

- **Spec coverage:** daily ingest (Tasks 7,8,10), message-ID dedup (Tasks 8,10), allow-list header match (Task 4), standings parse incl. optional deck (Tasks 5,6), normalized player key (Tasks 3,5), Supabase schema (Task 13), current-calendar-month window in configured TZ (Tasks 9,11), everyone-embed with chunking (Task 9), separate configurable leaderboard channel (Tasks 2,11,12), weekly/daily crons + workflow_dispatch (Task 14), config validation + secrets + README bot-intent note (Tasks 2,15). All spec sections map to tasks.
- **Refinement vs spec:** monthly totals are aggregated in pure Python (`aggregate_totals`) over a windowed fetch rather than SQL `GROUP BY`, for unit-testability. Data volume is small, so this is not a performance concern.
- **Type consistency:** `DiscordClient.fetch_messages/post_embeds`, `Store.existing_message_ids/insert_tournament/fetch_results_in_window`, `ParsedTournament`/`ResultRow`/`PlayerTotal`, and `run(...)` signatures are used identically across producing and consuming tasks.
- **Accepted limitation (from spec):** a corrected repost (new message ID) of the same tournament creates a second row; no secondary `(name, event_date)` guard for now.
