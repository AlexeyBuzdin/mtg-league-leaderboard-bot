# Summer 2026 Season Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score Summer-2026 tournaments with `placement + 2·wins + 1·draws + 1(attendance)` (placement ranked among all attendees by match points then game wins), on both the website season leaderboard and the Discord monthly post; all other tournaments keep `3·wins + draws`.

**Architecture:** The scoring rule is a pure per-tournament function keyed on the tournament's date season, so any leaderboard summing a Summer-2026 tournament uses it automatically. Web implements it in `web/lib/leaderboard.js`; Discord in `bot/leaderboard.py` fed by a new richer store query. Both are unit-tested.

**Tech Stack:** Vanilla JS + `node --test`; Python 3.11 + supabase-py + pytest.

---

## File Structure

- `web/lib/leaderboard.js` — `playerTournamentStats`, `tournamentScores`, rewritten `seasonLeaderboard` (keeps `points`, `finalRecords`)
- `tests/web/leaderboard.test.mjs` — updated existing + new summer-formula tests
- `bot/store.py` — new `fetch_tournament_stats`
- `bot/leaderboard.py` — `_is_summer_2026`, `_tournament_scores`, `season_totals`; `run()` swap
- `tests/test_store.py` — `fetch_tournament_stats` reduction test
- `tests/test_leaderboard.py` — scorer tests + updated `run` tests

**Environment for the executor:**
- Python: `.venv/Scripts/python.exe` (create in Task 1).
- Node (not on PATH): prepend in Bash node commands:
  `export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`
- Git identity configured. LF/CRLF warnings harmless.

---

## Task 1: Environment setup

- [ ] **Step 1:** `python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"` — installs cleanly.
- [ ] **Step 2:** `.venv/Scripts/python.exe -m pytest -q` — baseline all pass.
- [ ] **Step 3:** Baseline web tests:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/*.test.mjs
```
All pass.
- [ ] **Step 4:** No commit.

---

## Task 2: Website scoring (`web/lib/leaderboard.js`)

**Files:** Modify `web/lib/leaderboard.js`; Test `tests/web/leaderboard.test.mjs`

- [ ] **Step 1: Update the existing test and add new ones in `tests/web/leaderboard.test.mjs`.**

The existing `seasonLeaderboard sums points, counts events, filters by season, sorts` test uses **summer-dated** fixtures, so its numbers change. Replace that test's final block (the `const board = seasonLeaderboard(...)` and its assertions) with:
```js
  const board = seasonLeaderboard([t1, t2, q2Tournament], '2026-2');
  // Summer 2026 formula. t1: Ann 1st(8), Cara 2nd(5), Bob 3rd(2). t2: Bob 1st(6), Ann 2nd(3).
  // q2Tournament is spring (season 2026-1) -> excluded.
  assert.deepEqual(board.map(r => r.name), ['Ann', 'Bob', 'Cara']);
  assert.equal(board[0].points, 11); // Ann 8 + 3
  assert.equal(board[0].events, 2);
  assert.equal(board[1].name, 'Bob');
  assert.equal(board[1].points, 8);  // 2 + 6
  assert.equal(board[1].events, 2);
  assert.equal(board[2].name, 'Cara');
  assert.equal(board[2].points, 5);
  assert.equal(board[2].events, 1);
  assert.ok(!board.find(r => r.name === 'Zed'));
```

Append these new tests:
```js
test('summer placement ranks by match points then game wins', () => {
  const t = { id: 't', date: '2026-07-10', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 1, record: rec(1, 0, 0) }, player2: { name: 'Cara', game_wins: 2, record: rec(0, 0, 1) } },
      { pairing: 2, player1: { name: 'Bob', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  // Ann mp3 gw1; Bob mp3 gw2; Cara mp0 gw2 -> Bob 1st(6), Ann 2nd(5), Cara 3rd(2)
  assert.deepEqual(board.map(r => [r.name, r.points]), [['Bob', 6], ['Ann', 5], ['Cara', 2]]);
});

test('non-league players count for placement but are hidden', () => {
  const t = { id: 't', date: '2026-07-10', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Guest', game_wins: 2, record: rec(1, 0, 0), is_league: false },
        player2: { name: 'Ann', game_wins: 1, record: rec(0, 0, 1), is_league: true } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  // Guest 1st (hidden); Ann 2nd -> 2 + 0 + 0 + 1 = 3
  assert.deepEqual(board.map(r => r.name), ['Ann']);
  assert.equal(board[0].points, 3);
});

test('a non-summer season still uses 3*wins + draws', () => {
  const t = { id: 't', date: '2026-04-12', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-1');
  assert.deepEqual(board.map(r => [r.name, r.points]), [['Ann', 3], ['Bob', 0]]);
});
```

- [ ] **Step 2: Run to verify failure**

Run (after PATH export): `node --test tests/web/leaderboard.test.mjs`
Expected: FAIL (old formula numbers; new tests fail).

- [ ] **Step 3: Rewrite `web/lib/leaderboard.js`** to:
```js
import { seasonKey } from './season.js';

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

function accumulate(stats, player) {
  const s = stats[player.name] || { record: null, gameWins: 0, isLeague: true };
  s.record = player.record; // rounds are in order, so this ends as the final record
  s.gameWins += player.game_wins || 0;
  s.isLeague = player.is_league !== false;
  stats[player.name] = s;
}

export function playerTournamentStats(tournament) {
  const stats = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      accumulate(stats, pairing.player1);
      if (pairing.player2) accumulate(stats, pairing.player2);
    }
  }
  return stats;
}

export function tournamentScores(tournament) {
  const stats = playerTournamentStats(tournament);
  const summer = seasonKey(tournament.date) === '2026-2';
  const ranked = Object.entries(stats)
    .map(([name, s]) => ({ name, ...s, mp: points(s.record) }))
    .sort((a, b) => b.mp - a.mp || b.gameWins - a.gameWins || a.name.localeCompare(b.name));
  const bonus = [3, 2, 1];
  const scores = {};
  ranked.forEach((p, i) => {
    if (summer) {
      const placement = i < 3 ? bonus[i] : 0;
      scores[p.name] = { score: placement + 2 * p.record.wins + p.record.draws + 1, isLeague: p.isLeague };
    } else {
      scores[p.name] = { score: points(p.record), isLeague: p.isLeague };
    }
  });
  return scores;
}

export function seasonLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (seasonKey(tournament.date) !== key) continue;
    const scored = tournamentScores(tournament);
    for (const [name, { score, isLeague }] of Object.entries(scored)) {
      if (!isLeague) continue;
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += score;
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
```

- [ ] **Step 4: Run all web tests**

Run (after PATH export): `node --test tests/web/*.test.mjs`
Expected: PASS (including the `finalRecords` test, which is unchanged, and all leaderboard tests).

- [ ] **Step 5: Commit**

```bash
git add web/lib/leaderboard.js tests/web/leaderboard.test.mjs
git commit -m "feat(web): apply Summer 2026 placement/attendance scoring to the season leaderboard"
```

---

## Task 3: Store — `fetch_tournament_stats`

**Files:** Modify `bot/store.py`; Test `tests/test_store.py`

- [ ] **Step 1: Add a failing test** — append to `tests/test_store.py`:
```python
def test_fetch_tournament_stats_reduces_final_record_and_sums_game_wins():
    rows = [
        {"tournament_id": 7, "round": 1, "player_key": "ann", "player_name": "Ann",
         "game_wins": 2, "record_wins": 1, "record_draws": 0, "tournaments": {"event_date": "2026-07-06"}},
        {"tournament_id": 7, "round": 2, "player_key": "ann", "player_name": "Ann",
         "game_wins": 1, "record_wins": 2, "record_draws": 0, "tournaments": {"event_date": "2026-07-06"}},
        {"tournament_id": 7, "round": 1, "player_key": "bob", "player_name": "Bob",
         "game_wins": 1, "record_wins": 0, "record_draws": 0, "tournaments": {"event_date": "2026-07-06"}},
    ]
    rr = FakeTable(rows=rows)
    store = Store(FakeSupabase({"round_results": rr}))
    out = store.fetch_tournament_stats(date(2026, 7, 1), date(2026, 7, 31))
    by_key = {r["player_key"]: r for r in out}
    assert by_key["ann"]["record_wins"] == 2       # final round
    assert by_key["ann"]["record_draws"] == 0
    assert by_key["ann"]["game_wins"] == 3         # 2 + 1 summed
    assert by_key["ann"]["event_date"] == "2026-07-06"
    assert by_key["ann"]["tournament_id"] == 7
    assert by_key["bob"]["game_wins"] == 1
    assert ("gte", "tournaments.event_date", "2026-07-01") in rr.calls
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -k tournament_stats -v`
Expected: FAIL — `Store` has no attribute `fetch_tournament_stats`.

- [ ] **Step 3: Add the method to `bot/store.py`** (inside `class Store`, after `fetch_results_in_window`):
```python
    def fetch_tournament_stats(self, start: date, end: date) -> list[dict]:
        resp = (
            self._db.table("round_results")
            .select(
                "tournament_id, round, player_key, player_name, game_wins, "
                "record_wins, record_draws, tournaments!inner(event_date)"
            )
            .gte("tournaments.event_date", start.isoformat())
            .lte("tournaments.event_date", end.isoformat())
            .order("event_date", desc=False, foreign_table="tournaments")
            .execute()
        )
        reduced: dict[tuple, dict] = {}
        for row in resp.data:
            key = (row["tournament_id"], row["player_key"])
            cur = reduced.get(key)
            if cur is None:
                reduced[key] = {
                    "tournament_id": row["tournament_id"],
                    "event_date": row["tournaments"]["event_date"],
                    "player_key": row["player_key"],
                    "player_name": row["player_name"],
                    "record_wins": row["record_wins"],
                    "record_draws": row["record_draws"],
                    "game_wins": row["game_wins"] or 0,
                    "_round": row["round"],
                }
            else:
                cur["game_wins"] += row["game_wins"] or 0
                if row["round"] > cur["_round"]:
                    cur["_round"] = row["round"]
                    cur["record_wins"] = row["record_wins"]
                    cur["record_draws"] = row["record_draws"]
                    cur["player_name"] = row["player_name"]
        return [{k: v for k, v in r.items() if k != "_round"} for r in reduced.values()]
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bot/store.py tests/test_store.py
git commit -m "feat(store): add fetch_tournament_stats (all attendees, summed game wins)"
```

---

## Task 4: Discord scorer + run swap (`bot/leaderboard.py`)

**Files:** Modify `bot/leaderboard.py`; Test `tests/test_leaderboard.py`

- [ ] **Step 1: Add failing scorer tests** — append to `tests/test_leaderboard.py`:
```python
from bot.leaderboard import season_totals


def _stat(tid, key, name, w, d, gw, date_="2026-07-06"):
    return {"tournament_id": tid, "player_key": key, "player_name": name,
            "record_wins": w, "record_draws": d, "game_wins": gw, "event_date": date_}


def test_season_totals_summer_placement_and_attendance():
    stats = [
        _stat(1, "ann", "Ann", 2, 0, 4),
        _stat(1, "bob", "Bob", 0, 0, 1),
        _stat(1, "cara", "Cara", 1, 0, 2),
    ]
    totals = season_totals(stats, {"ann", "bob", "cara"})
    by = {t.player_key: t for t in totals}
    assert by["ann"].points == 8   # 1st(3) + 2*2 + 0 + 1
    assert by["cara"].points == 5  # 2nd(2) + 2*1 + 0 + 1
    assert by["bob"].points == 2   # 3rd(1) + 0 + 0 + 1
    assert [t.player_key for t in totals] == ["ann", "cara", "bob"]


def test_season_totals_excludes_non_league_but_ranks_them():
    stats = [_stat(1, "guest", "Guest", 1, 0, 2), _stat(1, "ann", "Ann", 0, 0, 1)]
    totals = season_totals(stats, {"ann"})
    assert [t.player_key for t in totals] == ["ann"]
    assert totals[0].points == 3   # 2nd(2) + 0 + attendance 1


def test_season_totals_non_summer_uses_standard():
    stats = [_stat(1, "ann", "Ann", 1, 0, 2, date_="2026-04-12")]
    totals = season_totals(stats, {"ann"})
    assert totals[0].points == 3   # 3*1 + 0, no placement/attendance
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python.exe -m pytest tests/test_leaderboard.py -k season_totals -v`
Expected: FAIL — cannot import `season_totals`.

- [ ] **Step 3: Update `bot/leaderboard.py`.**

Add near the top, after the existing imports, `from collections import defaultdict`. Then add these functions (place them above `run`):
```python
def _is_summer_2026(event_date) -> bool:
    if isinstance(event_date, str):
        year, month = int(event_date[:4]), int(event_date[5:7])
    else:
        year, month = event_date.year, event_date.month
    return year == 2026 and month in (6, 7, 8)


def _tournament_scores(rows: list[dict]) -> dict:
    summer = _is_summer_2026(rows[0]["event_date"])
    ranked = sorted(
        rows,
        key=lambda r: (
            -(3 * r["record_wins"] + r["record_draws"]),
            -(r["game_wins"] or 0),
            r["player_name"].lower(),
        ),
    )
    bonus = [3, 2, 1]
    out: dict = {}
    for i, r in enumerate(ranked):
        if summer:
            placement = bonus[i] if i < 3 else 0
            score = placement + 2 * r["record_wins"] + r["record_draws"] + 1
        else:
            score = 3 * r["record_wins"] + r["record_draws"]
        out[r["player_key"]] = {"player_name": r["player_name"], "score": score}
    return out


def season_totals(stats: list[dict], league_keys: set[str]) -> list[PlayerTotal]:
    by_tournament: dict = defaultdict(list)
    for row in stats:
        by_tournament[row["tournament_id"]].append(row)
    acc: dict[str, PlayerTotal] = {}
    for rows in by_tournament.values():
        for key, s in _tournament_scores(rows).items():
            if key not in league_keys:
                continue
            cur = acc.get(key)
            if cur is None:
                acc[key] = PlayerTotal(key, s["player_name"], s["score"], 1)
            else:
                acc[key] = PlayerTotal(
                    key, s["player_name"], cur.points + s["score"], cur.events + 1
                )
    return sorted(acc.values(), key=lambda t: (-t.points, t.display_name.lower()))
```

Replace the body of `run` (from `rows = store.fetch_results_in_window(...)` through `totals = aggregate_totals(rows)`) with:
```python
def run(discord, store, channel_id: str, now: datetime) -> bool:
    start, end = month_window(now)
    stats = store.fetch_tournament_stats(start, end)
    league_keys = store.fetch_league_keys()
    totals = season_totals(stats, league_keys)
    if not totals:
        return False
    label = f"{_MONTHS[start.month - 1]} {start.year}"
    embeds = build_leaderboard_embeds(totals, label)
    discord.post_embeds(channel_id, embeds)
    return True
```
(`aggregate_totals` and `store.fetch_results_in_window` are no longer used by `run` but are left in place with their existing tests.)

- [ ] **Step 4: Update the `run` tests in `tests/test_leaderboard.py`.**

Replace `class FakeStore2` with:
```python
class FakeStore2:
    def __init__(self, stats):
        self._stats = stats
        self.window = None
    def fetch_tournament_stats(self, start, end):
        self.window = (start, end)
        return self._stats
    def fetch_league_keys(self):
        return getattr(self, "league_keys", set())
```

Replace `test_leaderboard_run_posts_embed` with:
```python
def test_leaderboard_run_posts_embed():
    stats = [
        {"tournament_id": 1, "player_key": "james smith", "player_name": "James Smith",
         "record_wins": 3, "record_draws": 0, "game_wins": 6, "event_date": "2026-07-05"},
        {"tournament_id": 1, "player_key": "nikita powers", "player_name": "Nikita Powers",
         "record_wins": 2, "record_draws": 0, "game_wins": 4, "event_date": "2026-07-05"},
    ]
    store = FakeStore2(stats)
    store.league_keys = {"james smith", "nikita powers"}
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    posted = leaderboard_run(discord, store, channel_id="222", now=now)
    assert posted is True
    assert store.window == (date(2026, 7, 1), date(2026, 7, 15))
    channel_id, embeds = discord.posted
    assert channel_id == "222"
    assert "July 2026" in embeds[0]["title"]
    # July 2026 is summer: James 1st = 3 + 2*3 + 0 + 1 = 10
    assert "1. James Smith — 10 pts" in embeds[0]["description"]
```

If a `test_leaderboard_run_excludes_non_league` test exists, replace its store setup to use the new stats shape and keep asserting the non-league name is absent:
```python
def test_leaderboard_run_excludes_non_league():
    stats = [
        {"tournament_id": 1, "player_key": "ann", "player_name": "Ann",
         "record_wins": 1, "record_draws": 0, "game_wins": 2, "event_date": "2026-07-05"},
        {"tournament_id": 1, "player_key": "guest", "player_name": "Guest",
         "record_wins": 2, "record_draws": 0, "game_wins": 4, "event_date": "2026-07-05"},
    ]
    store = FakeStore2(stats)
    store.league_keys = {"ann"}
    discord = FakeDiscord2()
    now = datetime(2026, 7, 15, 9, 0, tzinfo=ZoneInfo("Europe/Riga"))
    assert leaderboard_run(discord, store, channel_id="c", now=now) is True
    text = " ".join(e["description"] for e in discord.posted[1])
    assert "Ann" in text
    assert "Guest" not in text
```
(`test_leaderboard_run_skips_when_empty` needs no change — `FakeStore2([])` returns `[]` → `season_totals([], …)` → `[]` → returns False.)

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_leaderboard.py -v` then the full suite `.venv/Scripts/python.exe -m pytest -q`.
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bot/leaderboard.py tests/test_leaderboard.py
git commit -m "feat(leaderboard): score Summer 2026 tournaments with placement/attendance on Discord"
```

---

## Task 5: Full verification

- [ ] **Step 1: Full suites**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
.venv/Scripts/python.exe -m pytest -q
node --test tests/web/*.test.mjs
```
Expected: all pass.

- [ ] **Step 2: Sanity-check the website Summer 2026 board**

Serve `web/` (`python -m http.server 8200 --directory web`), open the leaderboard, select the Summer 2026 season, and confirm the totals reflect placement + wins + attendance (they should be higher than the old sum-of-points) and non-league players are still absent. Stop the server.

- [ ] **Step 3: No commit** (verification only).

---

## Notes for delivery

- Delivered as a pull request from the `summer-scoring` branch. No schema, live-DB, or workflow change.
- The Summer-2026 rule is keyed on `seasonKey === "2026-2"` (web) / `year==2026 and month in {6,7,8}` (Python). To change which season is special, update those two checks.

---

## Self-Review Notes

- **Spec coverage:** scoring rule (Tasks 2,4), placement by match points + game-win tiebreak among all attendees (Tasks 2,4), summer-only via tournament date (Tasks 2,4), attendance point (Tasks 2,4), league-only display (Tasks 2,4), richer store fetch (Task 3), web + Discord surfaces (Tasks 2,4), tests incl. non-summer unchanged (Tasks 2,4), full verification + visual (Task 5). All spec sections map to tasks.
- **Placeholder scan:** none; all code and expected numbers are concrete (worked examples computed).
- **Type consistency:** `playerTournamentStats`→`tournamentScores`→`seasonLeaderboard` shapes line up (`{record, gameWins, isLeague}`, `{score, isLeague}`). Python `fetch_tournament_stats` rows (`tournament_id, event_date, player_key, player_name, record_wins, record_draws, game_wins`) match what `_tournament_scores`/`season_totals` read, and `season_totals` returns `PlayerTotal(player_key, display_name, points, events)` consumed by `build_leaderboard_embeds`. Summer detection is consistent (`2026-2` / `year 2026 & month 6-8`).
