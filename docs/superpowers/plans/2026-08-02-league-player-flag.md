# League Player Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-player `is_league` flag (new Supabase `players` table, approve-in default) that hides non-league players from the website and Discord leaderboards while keeping them in tournament detail.

**Architecture:** `players` table is the source of truth. Ingest upserts new players (default hidden). The Discord leaderboard filters by league keys; the export tags each JSON player with `is_league`; the web leaderboard filters on it. All logic lives in small, unit-tested functions.

**Tech Stack:** Python 3.11 + supabase-py + pytest; vanilla JS + `node --test`; Supabase Postgres; GitHub Actions (unchanged).

---

## File Structure

- `supabase/schema.sql` — add `players` table
- `bot/store.py` — `upsert_players`, `fetch_league_keys`
- `bot/ingest.py` — upsert players after insert
- `bot/leaderboard.py` — filter results by league keys in `run`
- `bot/export.py` — fetch players, tag `is_league` in `build_site_data`
- `web/lib/leaderboard.js` — `finalRecords` carries league flag; `quarterLeaderboard` skips non-league
- `web/data/tournaments.json` — add `is_league` to seed players (+ one non-league)
- Tests: `tests/test_store.py`, `tests/test_ingest.py`, `tests/test_leaderboard.py`, `tests/test_export.py`, `tests/web/leaderboard.test.mjs`, `tests/web/seed-data.test.mjs`
- Live Supabase: create + seed `players` (controller step, not a repo change)

**Environment for the executor:**
- Python: `.venv/Scripts/python.exe` (create it in Task 1).
- Node (for `node --test`): not on PATH; prepend in that Bash command:
  `export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`
- Git identity is configured. LF/CRLF warnings are harmless.

---

## Task 1: Environment setup

- [ ] **Step 1: venv + install**

Run: `python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"`
Expected: installs cleanly.

- [ ] **Step 2: baseline pytest**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all existing tests pass.

- [ ] **Step 3: baseline web tests**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/*.test.mjs
```
Expected: all pass.

- [ ] **Step 4: No commit** (`.venv/` is gitignored).

---

## Task 2: `players` table in schema

**Files:**
- Modify: `supabase/schema.sql`

- [ ] **Step 1: Append the `players` table to `supabase/schema.sql`**

Add at the end of the file:
```sql
-- League roster: which players appear on the leaderboards.
create table if not exists players (
  player_key   text primary key,
  display_name text,
  is_league    boolean not null default false,
  created_at   timestamptz not null default now()
);
```

- [ ] **Step 2: Verify the SQL is well-formed**

Run: `.venv/Scripts/python.exe -c "import pathlib; s=pathlib.Path('supabase/schema.sql').read_text(); assert 'create table if not exists players' in s; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat(db): add players table for league flag"
```

---

## Task 3: Store — `upsert_players` and `fetch_league_keys`

**Files:**
- Modify: `bot/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Extend the fakes and add failing tests in `tests/test_store.py`**

In `class FakeQuery`, add these methods (place them alongside the existing ones):
```python
    def upsert(self, payload, *, on_conflict=None, ignore_duplicates=False):
        self._is_upsert = True
        self.table.upserted.append(payload)
        return self

    def eq(self, col, value):
        self._filter = (col, {value})
        return self
```
In `class FakeQuery.__init__`, add `self._is_upsert = False`.
In `class FakeQuery.execute`, add this as the FIRST check inside the method:
```python
        if self._is_upsert:
            return Result([])
```
In `class FakeTable.__init__`, add `self.upserted = []`.

Then append these tests at the end of the file:
```python
def test_upsert_players_records_rows():
    players = FakeTable()
    store = Store(FakeSupabase({"players": players}))
    store.upsert_players([{"player_key": "ann", "display_name": "Ann"}])
    assert players.upserted[0][0]["player_key"] == "ann"
    assert players.upserted[0][0]["display_name"] == "Ann"


def test_upsert_players_empty_is_noop():
    players = FakeTable()
    store = Store(FakeSupabase({"players": players}))
    store.upsert_players([])
    assert players.upserted == []


def test_fetch_league_keys_returns_only_league():
    players = FakeTable(rows=[
        {"player_key": "ann", "is_league": True},
        {"player_key": "guest", "is_league": False},
    ])
    store = Store(FakeSupabase({"players": players}))
    assert store.fetch_league_keys() == {"ann"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -k "players or league" -v`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'upsert_players'`.

- [ ] **Step 3: Add the methods to `bot/store.py`** (inside `class Store`, after `existing_message_ids`):
```python
    def upsert_players(self, players: list[dict]) -> None:
        if not players:
            return
        self._db.table("players").upsert(
            players, on_conflict="player_key", ignore_duplicates=True
        ).execute()

    def fetch_league_keys(self) -> set[str]:
        resp = (
            self._db.table("players").select("player_key").eq("is_league", True).execute()
        )
        return {row["player_key"] for row in resp.data}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -v`
Expected: PASS (all store tests).

- [ ] **Step 5: Commit**

```bash
git add bot/store.py tests/test_store.py
git commit -m "feat(store): add upsert_players and fetch_league_keys"
```

---

## Task 4: Ingest — record players seen

**Files:**
- Modify: `bot/ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Extend the ingest FakeStore and add a failing assertion in `tests/test_ingest.py`**

In `class FakeStore.__init__`, add `self.upserted_players = []`.
Add this method to `class FakeStore`:
```python
    def upsert_players(self, players):
        self.upserted_players.append(players)
```
Append this test:
```python
def test_ingest_upserts_players_it_saw():
    msg = {"id": "m1", "content": SAMPLE, "timestamp": "2026-07-31T10:00:00+00:00"}
    store = FakeStore()
    run(FakeDiscord([msg]), store, channel_id="111", timezone="Europe/Riga")
    keys = {p["player_key"] for p in store.upserted_players[0]}
    assert keys == {"james doe", "alexey doe"}
    names = {p["player_key"]: p["display_name"] for p in store.upserted_players[0]}
    assert names["james doe"] == "James Doe"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ingest.py -k upserts_players -v`
Expected: FAIL — `AttributeError` on `upserted_players` or empty list (no upsert call yet).

- [ ] **Step 3: Update `bot/ingest.py`** — after the `store.insert_tournament(...)` line and before `log.info(...)`, add:
```python
        players = {}
        for r in rounds:
            players[r.player_key] = r.player_name
        store.upsert_players(
            [{"player_key": k, "display_name": v} for k, v in players.items()]
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ingest.py -v`
Expected: PASS (all ingest tests).

- [ ] **Step 5: Commit**

```bash
git add bot/ingest.py tests/test_ingest.py
git commit -m "feat(ingest): upsert seen players (default hidden)"
```

---

## Task 5: Discord leaderboard — filter non-league

**Files:**
- Modify: `bot/leaderboard.py`
- Test: `tests/test_leaderboard.py`

- [ ] **Step 1: Update the run-test fake and add a failing test in `tests/test_leaderboard.py`**

Add a `fetch_league_keys` method to the existing `class FakeStore2` (which currently has `fetch_results_in_window`):
```python
    def fetch_league_keys(self):
        return getattr(self, "league_keys", set())
```
Append this test:
```python
def test_leaderboard_run_excludes_non_league(monkeypatch):
    rows = [
        {"player_key": "ann", "player_name": "Ann", "points": 9},
        {"player_key": "guest", "player_name": "Guest", "points": 12},
    ]
    store = FakeStore2(rows)
    store.league_keys = {"ann"}
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15)
    posted = run(discord, store, channel_id="c", now=now)
    assert posted is True
    body = discord.posted_embeds
    text = " ".join(e["description"] for e in body)
    assert "Ann" in text
    assert "Guest" not in text
```
Note: adapt the names `FakeStore2`, `FakeDiscord2`, `run`, and the `discord.posted_embeds` accessor to match what the existing run tests already use in this file (look at `test_leaderboard_run_posts_embed`). If the fake discord records embeds under a different attribute, use that attribute in the assertion.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_leaderboard.py -k excludes_non_league -v`
Expected: FAIL — "Guest" still present (no filtering yet).

- [ ] **Step 3: Update `bot/leaderboard.py` `run`** — replace the body up to `aggregate_totals`:
```python
def run(discord, store, channel_id: str, now: datetime) -> bool:
    start, end = month_window(now)
    rows = store.fetch_results_in_window(start, end)
    league_keys = store.fetch_league_keys()
    rows = [r for r in rows if r["player_key"] in league_keys]
    totals = aggregate_totals(rows)
    if not totals:
        return False
    label = f"{_MONTHS[start.month - 1]} {start.year}"
    embeds = build_leaderboard_embeds(totals, label)
    discord.post_embeds(channel_id, embeds)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_leaderboard.py -v`
Expected: PASS. Note: the existing `test_leaderboard_run_posts_embed` will now need its `FakeStore2` to expose league keys — set `store.league_keys` in that test to the set of player_keys it expects on the board (so the filter keeps them). Update that test accordingly if it starts failing.

- [ ] **Step 5: Commit**

```bash
git add bot/leaderboard.py tests/test_leaderboard.py
git commit -m "feat(leaderboard): exclude non-league players from Discord post"
```

---

## Task 6: Export — tag each player with `is_league`

**Files:**
- Modify: `bot/export.py`
- Test: `tests/test_export.py`

- [ ] **Step 1: Add failing tests to `tests/test_export.py`**

Append:
```python
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
```

Also update `class _FakeClient` (used by the export_to_file tests) to serve a `players` table. Change its `__init__` and `table`:
```python
class _FakeClient:
    def __init__(self, tournaments, results, players=None):
        self._tables = {
            "tournaments": tournaments,
            "round_results": results,
            "players": players or [],
        }

    def table(self, name):
        return _FakeQuery(self._tables[name])
```
And append:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -k "is_league or players_flag or defaults_all_league" -v`
Expected: FAIL — `build_site_data() takes 2 positional arguments` / missing `is_league`.

- [ ] **Step 3: Update `bot/export.py`**

Change `_player_obj` to accept league keys:
```python
def _player_obj(row: dict, league_keys) -> dict:
    return {
        "name": row["player_name"],
        "game_wins": row["game_wins"],
        "record": {
            "wins": row["record_wins"],
            "draws": row["record_draws"],
            "losses": row["record_losses"],
        },
        "is_league": True if league_keys is None else row["player_key"] in league_keys,
    }
```

Change `build_site_data` signature and the two `_player_obj(...)` calls:
```python
def build_site_data(tournaments: list[dict], results: list[dict], league_keys=None) -> dict:
```
and inside the pairings loop:
```python
                pairings_out.append(
                    {
                        "pairing": pairing_no,
                        "player1": _player_obj(rows[0], league_keys),
                        "player2": _player_obj(rows[1], league_keys) if len(rows) > 1 else None,
                    }
                )
```

Add a players column constant near `_RESULT_COLS`:
```python
_PLAYER_COLS = "player_key, is_league"
```

Change `_fetch` to also load players and return league keys:
```python
def _fetch(client) -> tuple[list[dict], list[dict], set[str]]:
    tournaments = _fetch_all(client, "tournaments", _TOURNAMENT_COLS)
    results = _fetch_all(client, "round_results", _RESULT_COLS)
    players = _fetch_all(client, "players", _PLAYER_COLS)
    league_keys = {p["player_key"] for p in players if p["is_league"]}
    return tournaments, results, league_keys
```

Change `export_to_file`:
```python
def export_to_file(client, out_path: str) -> int:
    tournaments, results, league_keys = _fetch(client)
    data = build_site_data(tournaments, results, league_keys)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return len(data["tournaments"])
```

- [ ] **Step 4: Run the whole export test file**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: PASS. (The existing `test_export_to_file_writes_expected_json` and pagination test still pass — `_FakeClient` now serves an empty `players` table, and those tests don't assert `is_league`.)

- [ ] **Step 5: Commit**

```bash
git add bot/export.py tests/test_export.py
git commit -m "feat(export): tag each JSON player with is_league from players table"
```

---

## Task 7: Web leaderboard — filter non-league

**Files:**
- Modify: `web/lib/leaderboard.js`
- Test: `tests/web/leaderboard.test.mjs`

- [ ] **Step 1: Update the failing tests in `tests/web/leaderboard.test.mjs`**

The `finalRecords` contract changes to `{name: {record, isLeague}}`. Update the existing `finalRecords` test to:
```js
test('finalRecords keeps the last record per player and includes byes', () => {
  const f = finalRecords(t1);
  assert.deepEqual(f['Ann'].record, rec(2, 0, 0));
  assert.deepEqual(f['Bob'].record, rec(0, 0, 2));
  assert.deepEqual(f['Cara'].record, rec(1, 0, 0));
  assert.equal(f['Ann'].isLeague, true);
});
```
Append two new tests:
```js
test('quarterLeaderboard excludes non-league players', () => {
  const t = { id: 'x', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0), is_league: true },
        player2: { name: 'Guest', game_wins: 1, record: rec(0, 0, 1), is_league: false } },
    ] },
  ] };
  const board = quarterLeaderboard([t], '2026-Q3');
  assert.deepEqual(board.map(r => r.name), ['Ann']);
});

test('quarterLeaderboard treats a missing is_league as league', () => {
  const t = { id: 'x', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) },
        player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = quarterLeaderboard([t], '2026-Q3');
  assert.deepEqual(board.map(r => r.name).sort(), ['Ann', 'Bob']);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/leaderboard.test.mjs
```
Expected: FAIL (`f['Ann'].record` undefined; non-league still counted).

- [ ] **Step 3: Update `web/lib/leaderboard.js`**

Replace `finalRecords` and `quarterLeaderboard`:
```js
function playerEntry(player) {
  return { record: player.record, isLeague: player.is_league !== false };
}

export function finalRecords(tournament) {
  const last = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      last[pairing.player1.name] = playerEntry(pairing.player1);
      if (pairing.player2) {
        last[pairing.player2.name] = playerEntry(pairing.player2);
      }
    }
  }
  return last;
}

export function points(record) {
  return record.wins * 3 + record.draws;
}

export function quarterLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (quarterKey(tournament.date) !== key) continue;
    const finals = finalRecords(tournament);
    for (const [name, entry] of Object.entries(finals)) {
      if (!entry.isLeague) continue;
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += points(entry.record);
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
```
(Keep the `import { quarterKey } from './quarter.js';` line at the top.)

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/leaderboard.test.mjs
```
Expected: PASS (all leaderboard tests, including the updated one).

- [ ] **Step 5: Commit**

```bash
git add web/lib/leaderboard.js tests/web/leaderboard.test.mjs
git commit -m "feat(web): exclude non-league players from the quarterly leaderboard"
```

---

## Task 8: Seed data — add `is_league`

**Files:**
- Modify: `web/data/tournaments.json`
- Test: `tests/web/seed-data.test.mjs`

- [ ] **Step 1: Add `is_league` to the seed players**

In `web/data/tournaments.json`, add `"is_league": true` to **every** existing `player1`/`player2` object (they are league players). Then, to exercise the filter, change tournament `c`'s (`Spring Showdown`, `2026-04-12`) second pairing so `player2` (`Sergejs Ivanov`) is a non-league guest: set that player2 object's `"is_league": false` (leave its other fields).

Concretely, each player object goes from:
```json
{ "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }
```
to:
```json
{ "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 }, "is_league": true }
```
and the one non-league player (`Sergejs Ivanov` in tournament `c`) gets `"is_league": false`.

- [ ] **Step 2: Update `tests/web/seed-data.test.mjs`**

Append inside a new test (keep the existing test):
```js
test('seed players carry an is_league flag and include a non-league example', () => {
  const flags = [];
  for (const t of data.tournaments) {
    for (const r of t.rounds) {
      for (const p of r.pairings) {
        for (const player of [p.player1, p.player2]) {
          if (player) flags.push(player.is_league);
        }
      }
    }
  }
  assert.ok(flags.every(f => typeof f === 'boolean'));
  assert.ok(flags.includes(true));
  assert.ok(flags.includes(false));
});
```

- [ ] **Step 3: Validate JSON + run web tests**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
python -c "import json; json.load(open('web/data/tournaments.json', encoding='utf-8')); print('json ok')"
node --test tests/web/*.test.mjs
```
Expected: `json ok`; all web tests pass (Spring Showdown's Sergejs Ivanov now excluded from that quarter's board via the flag).

- [ ] **Step 4: Commit**

```bash
git add web/data/tournaments.json tests/web/seed-data.test.mjs
git commit -m "feat(web): add is_league to seed data with a non-league example"
```

---

## Task 9: Apply the players table + seed to the live database

**This is a controller step (uses the Supabase tooling), not a code change.** The executor should STOP and hand back to the controller for this task, or run the SQL if it has Supabase access.

- [ ] **Step 1: Create the table** (idempotent DDL) on project `shtatdxrwmiyzzvrfaai`:
```sql
create table if not exists players (
  player_key   text primary key,
  display_name text,
  is_league    boolean not null default false,
  created_at   timestamptz not null default now()
);
```

- [ ] **Step 2: Seed from existing round_results** (idempotent):
```sql
insert into players (player_key, display_name, is_league)
select distinct player_key, player_name,
       player_key not in ('aivars l','jevgenijs k','paul m','rolands s')
from round_results
on conflict (player_key) do nothing;
```

- [ ] **Step 3: Verify**
```sql
select is_league, count(*) from players group by is_league order by is_league;
```
Expected: `false → 4`, `true → 21`.

---

## Notes for delivery

- Delivered as a pull request from the `league-flag` branch.
- The `pages` deploy will hide the 4 non-league players once the live `players` table is seeded (Task 9) AND the branch merges. No workflow changes.

---

## Self-Review Notes

- **Spec coverage:** players table (Task 2, Task 9), approve-in default (Task 2 default false; ingest Task 4 adds hidden), Discord filter (Task 5), export tagging (Task 6), web filter incl. missing-flag=league back-compat (Task 7), seed data + non-league example (Task 8), live seed of 21/4 (Task 9), tests across store/ingest/leaderboard/export/web (Tasks 3–8). All spec sections map to tasks.
- **Placeholder scan:** none; all steps carry concrete code. Task 5 flags that fake attribute names must be matched to the existing file — this is guidance to reconcile with real code, not a placeholder for missing logic.
- **Type consistency:** `upsert_players(list[dict])` and `fetch_league_keys() -> set[str]` are defined in Task 3 and consumed in Tasks 4/5/6 identically. `build_site_data(tournaments, results, league_keys=None)` (Task 6) matches its Task 6 tests and the `export_to_file` caller. Web `finalRecords` now returns `{name: {record, isLeague}}` (Task 7) and its only consumer `quarterLeaderboard` is updated in the same task; the changed `finalRecords` test is updated in Task 7. `is_league` (JSON, snake_case) vs `isLeague` (internal JS entry) distinction is intentional and consistent.
