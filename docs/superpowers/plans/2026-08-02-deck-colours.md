# Deck Name & Colours Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store optional per-player deck name + colour identity in `round_results`, pass them through the export, and render them (mana-symbol icons then deck name) after each player's name in the tournament tab.

**Architecture:** Four nullable columns on `round_results` (filled manually in Supabase; bot untouched). `bot/export.py` selects the player-side columns and attaches `deck`/`deck_colours` to each JSON player. `web/ui/tournament-view.js` renders committed mana SVGs + the deck name in both render paths. Pure functions, unit-tested.

**Tech Stack:** Python 3.11 + supabase-py + pytest; vanilla JS + `node --test`; Supabase Postgres; committed SVG assets.

---

## File Structure

- `supabase/schema.sql` — add 4 columns to `round_results`
- `web/icons/mana/{W,U,B,R,G}.svg` — committed mana symbol assets
- `bot/export.py` — select + attach `deck`/`deck_colours`
- `tests/test_export.py` — deck passthrough tests (+ fix one exact-dict test)
- `web/ui/tournament-view.js` — `manaIcons`/`deckInfo` helpers, inserted after names
- `web/styles.css` — `.mana`, `.deck-name`
- `tests/web/tournament-view.test.mjs` — render tests
- `web/data/tournaments.json` — sample deck data
- Live Supabase: `alter table round_results …` (controller step)

**Environment for the executor:**
- Python: `.venv/Scripts/python.exe` (create in Task 1).
- Node (not on PATH): prepend in Bash node commands:
  `export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`
- Git identity configured. LF/CRLF warnings harmless.

---

## Task 1: Environment setup

- [ ] **Step 1:** `python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"` — installs cleanly.
- [ ] **Step 2:** `.venv/Scripts/python.exe -m pytest -q` — all existing tests pass (baseline).
- [ ] **Step 3:** Baseline web tests:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/*.test.mjs
```
All pass.
- [ ] **Step 4:** No commit (`.venv/` gitignored).

---

## Task 2: Schema columns

**Files:** Modify `supabase/schema.sql`

- [ ] **Step 1:** Append to the end of `supabase/schema.sql`:
```sql
-- Optional per-player deck info (filled manually in Supabase).
alter table round_results add column if not exists player_deck            text;
alter table round_results add column if not exists opponent_deck          text;
alter table round_results add column if not exists player_deck_colours     text;
alter table round_results add column if not exists opponent_deck_colours   text;
```

- [ ] **Step 2:** Verify: `.venv/Scripts/python.exe -c "import pathlib; s=pathlib.Path('supabase/schema.sql').read_text(); assert 'player_deck_colours' in s and 'opponent_deck' in s; print('ok')"` → `ok`.

- [ ] **Step 3:** Commit:
```bash
git add supabase/schema.sql
git commit -m "feat(db): add deck and deck_colours columns to round_results"
```

---

## Task 3: Commit the mana icon assets

**Files:** Create `web/icons/mana/{W,U,B,R,G}.svg`

- [ ] **Step 1: Download the raw SVGs** (Bash). These raw file URLs return `image/svg+xml` (the `/revision/latest/scale-to-width-down/15?cb=…` suffix must be omitted, or Fandom returns a webp):
```bash
mkdir -p web/icons/mana
curl -sS -o web/icons/mana/W.svg "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/8e/W.svg"
curl -sS -o web/icons/mana/U.svg "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/9/9f/U.svg"
curl -sS -o web/icons/mana/B.svg "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/2/2f/B.svg"
curl -sS -o web/icons/mana/R.svg "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/87/R.svg"
curl -sS -o web/icons/mana/G.svg "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/88/G.svg"
```

- [ ] **Step 2: Verify all five are real SVGs:**
```bash
for f in W U B R G; do
  head -c 5 "web/icons/mana/$f.svg" | grep -q "<svg" && echo "$f ok" || echo "$f BAD";
done
```
Expected: `W ok` … `G ok` (each file starts with `<svg`). If any is `BAD`, stop — the download returned non-SVG.

- [ ] **Step 3: Commit:**
```bash
git add web/icons/mana/W.svg web/icons/mana/U.svg web/icons/mana/B.svg web/icons/mana/R.svg web/icons/mana/G.svg
git commit -m "assets(web): add MTG mana symbol SVGs (W/U/B/R/G)"
```

---

## Task 4: Export — attach `deck` and `deck_colours`

**Files:** Modify `bot/export.py`; Test `tests/test_export.py`

- [ ] **Step 1: Add a failing test** — append to `tests/test_export.py`:
```python
def test_build_site_data_includes_deck_and_colours():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [
        {"tournament_id": 1, "round": 1, "pairing": 1, "player_name": "Ann", "player_key": "ann",
         "game_wins": 2, "record_wins": 1, "record_draws": 0, "record_losses": 0,
         "player_deck": "Izzet Prowess", "player_deck_colours": "UR"},
        {"tournament_id": 1, "round": 1, "pairing": 1, "player_name": "Bob", "player_key": "bob",
         "game_wins": 1, "record_wins": 0, "record_draws": 0, "record_losses": 1},
    ]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    by_name = {p["player1"]["name"]: p["player1"], p["player2"]["name"]: p["player2"]}
    assert by_name["Ann"]["deck"] == "Izzet Prowess"
    assert by_name["Ann"]["deck_colours"] == "UR"
    assert by_name["Bob"]["deck"] is None
    assert by_name["Bob"]["deck_colours"] is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -k deck_and_colours -v`
Expected: FAIL — `KeyError: 'deck'`.

- [ ] **Step 3: Update `bot/export.py`.**

Add the two columns to `_RESULT_COLS`:
```python
_RESULT_COLS = (
    "tournament_id, round, pairing, player_name, player_key, "
    "game_wins, record_wins, record_draws, record_losses, "
    "player_deck, player_deck_colours"
)
```

Add `deck`/`deck_colours` to `_player_obj` (use `.get` so rows without the keys → `None`):
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
        "deck": row.get("player_deck"),
        "deck_colours": row.get("player_deck_colours"),
    }
```

- [ ] **Step 4: Fix the exact-dict assertions in `test_full_pairing_two_rows`** (they now gain the two new keys). Replace the two assertion lines with:
```python
    assert p["player1"] == {"name": "Ann", "game_wins": 2, "record": {"wins": 1, "draws": 0, "losses": 0}, "is_league": True, "deck": None, "deck_colours": None}
    assert p["player2"] == {"name": "Bob", "game_wins": 1, "record": {"wins": 0, "draws": 0, "losses": 1}, "is_league": True, "deck": None, "deck_colours": None}
```

- [ ] **Step 5: Run the whole export file**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: PASS (new test + updated exact-dict test; others unchanged).

- [ ] **Step 6: Commit**

```bash
git add bot/export.py tests/test_export.py
git commit -m "feat(export): pass through deck and deck_colours to site JSON"
```

---

## Task 5: Web rendering — mana icons + deck name

**Files:** Modify `web/ui/tournament-view.js`, `web/styles.css`; Test `tests/web/tournament-view.test.mjs`

- [ ] **Step 1: Add failing tests** — append to `tests/web/tournament-view.test.mjs`:
```js
test('renders mana icons for deck colours in order, then the deck name', () => {
  const t = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0), deck_colours: 'WUR', deck: 'Jeskai Control' },
        player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(t);
  assert.ok(html.indexOf('icons/mana/W.svg') < html.indexOf('icons/mana/U.svg'));
  assert.ok(html.indexOf('icons/mana/U.svg') < html.indexOf('icons/mana/R.svg'));
  assert.equal((html.match(/class="mana"/g) || []).length, 3);
  assert.match(html, /Jeskai Control/);
  assert.ok(html.indexOf('icons/mana/R.svg') < html.indexOf('Jeskai Control'));
});

test('shows no deck info when deck and colours are empty', () => {
  const t = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(t);
  assert.ok(!html.includes('class="mana"'));
  assert.ok(!html.includes('deck-name'));
});

test('skips invalid colour characters (case-insensitive)', () => {
  const t = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0), deck_colours: 'WxG' }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(t);
  assert.equal((html.match(/class="mana"/g) || []).length, 2);
  assert.match(html, /icons\/mana\/W\.svg/);
  assert.match(html, /icons\/mana\/G\.svg/);
});

test('shows deck info in the standings-table view too', () => {
  const legacy = { name: 'Legacy', date: '2026-07-20', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Elliot N', game_wins: null, record: rec(3, 0, 0), deck_colours: 'B', deck: 'Mono Black' }, player2: null },
    ] },
  ] };
  const html = renderTournament(legacy);
  assert.match(html, /icons\/mana\/B\.svg/);
  assert.match(html, /Mono Black/);
});
```

- [ ] **Step 2: Run to verify they fail**

Run (after PATH export): `node --test tests/web/tournament-view.test.mjs`
Expected: FAIL (no `class="mana"`, deck name missing).

- [ ] **Step 3: Update `web/ui/tournament-view.js`.**

Add near the top (after the `MARK` constant):
```js
const MANA = new Set(['W', 'U', 'B', 'R', 'G']);

function manaIcons(colours) {
  if (!colours) return '';
  return [...colours.toUpperCase()]
    .filter(c => MANA.has(c))
    .map(c => `<img class="mana" src="icons/mana/${c}.svg" alt="${c}" />`)
    .join('');
}

function deckInfo(player) {
  const icons = manaIcons(player.deck_colours);
  const name = player.deck ? `<span class="deck-name">${player.deck}</span>` : '';
  return icons + name;
}
```

Insert `${deckInfo(pX)}` immediately after each player's `<span class="name">…</span>`:

In `pairingRow`, the bye branch:
```js
      `<div class="side win">${MARK}<span class="name">${p1.name}</span>${deckInfo(p1)}${recordChip(p1.record)}</div>` +
```
In `pairingRow`, the two-player branch:
```js
    `<div class="side ${p1Won ? 'win' : ''}">${p1Won ? MARK : ''}<span class="name">${p1.name}</span>${deckInfo(p1)}${recordChip(p1.record)}</div>` +
    `<div class="score">${p1.game_wins}-${p2.game_wins}</div>` +
    `<div class="side right ${p2Won ? 'win' : ''}">${recordChip(p2.record)}<span class="name">${p2.name}</span>${deckInfo(p2)}${p2Won ? MARK : ''}</div>` +
```
In `renderStandings`, the player cell:
```js
        `<div class="player">${player.name}${deckInfo(player)}</div>` +
```

- [ ] **Step 4: Add styles** — append to `web/styles.css`:
```css
.mana { height: 15px; width: 15px; vertical-align: -2px; margin: 0 1px; }
.deck-name { margin-left: 6px; font-size: 12px; color: var(--muted); }
```

- [ ] **Step 5: Run web tests**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/*.test.mjs
```
Expected: PASS (all web tests, including the 4 new ones).

- [ ] **Step 6: Commit**

```bash
git add web/ui/tournament-view.js web/styles.css tests/web/tournament-view.test.mjs
git commit -m "feat(web): render deck colour icons and deck name in tournament view"
```

---

## Task 6: Sample deck data in the seed

**Files:** Modify `web/data/tournaments.json`; Test `tests/web/seed-data.test.mjs`

- [ ] **Step 1:** In `web/data/tournaments.json`, add deck info to two players in tournament `a` (Standard Showdown):
  - `Raitis Ozols` (each of his player objects): add `"deck": "Izzet Prowess", "deck_colours": "UR"`.
  - `Mārtiņš Kalniņš` (each of his player objects): add `"deck_colours": "WUB"` (colours only, no deck name).

  It's sufficient to add these to their round-1 appearances (at minimum one appearance each) so the seed exercises the render; adding to all their appearances is fine too. Preserve UTF-8 diacritics.

- [ ] **Step 2:** Append to `tests/web/seed-data.test.mjs`:
```js
test('seed data includes at least one player with deck colours', () => {
  let found = false;
  for (const t of data.tournaments) {
    for (const r of t.rounds) {
      for (const p of r.pairings) {
        for (const player of [p.player1, p.player2]) {
          if (player && player.deck_colours) found = true;
        }
      }
    }
  }
  assert.ok(found);
});
```

- [ ] **Step 3: Validate + run web tests**
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
.venv/Scripts/python.exe -c "import json; json.load(open('web/data/tournaments.json', encoding='utf-8')); print('json ok')"
node --test tests/web/*.test.mjs
```
Expected: `json ok`; all web tests pass.

- [ ] **Step 4: Commit**
```bash
git add web/data/tournaments.json tests/web/seed-data.test.mjs
git commit -m "feat(web): add sample deck data to seed"
```

---

## Task 7: Apply the columns to the live database

**Controller step (Supabase tooling), not a code change.**

- [ ] **Step 1:** Apply to project `shtatdxrwmiyzzvrfaai` (idempotent):
```sql
alter table round_results add column if not exists player_deck            text;
alter table round_results add column if not exists opponent_deck          text;
alter table round_results add column if not exists player_deck_colours     text;
alter table round_results add column if not exists opponent_deck_colours   text;
```
- [ ] **Step 2:** Verify the columns exist (e.g. `select column_name from information_schema.columns where table_name='round_results' and column_name like '%deck%';` → 4 rows).

---

## Notes for delivery

- Delivered as a pull request from the `deck-colours` branch.
- After merge, deck data is entered manually in the Supabase `round_results` table (`player_deck`, `player_deck_colours` per row); the next export/deploy surfaces it on the site.

---

## Self-Review Notes

- **Spec coverage:** 4 columns (Task 2, Task 7), committed mana SVGs (Task 3), export passthrough (Task 4), web render of icons-then-deck-name in both views incl. invalid-char skipping (Task 5), styling (Task 5), sample seed (Task 6), live migration (Task 7). All spec sections map to tasks.
- **Placeholder scan:** none; every code step has full content. Task 6 Step 1 describes a JSON edit precisely (which players, which keys).
- **Type consistency:** JSON player keys `deck`/`deck_colours` are produced in `_player_obj` (Task 4) and consumed by `deckInfo` (Task 5) and asserted in the seed test (Task 6) identically. `_RESULT_COLS` gains exactly the two player-side columns the export reads. The exact-dict test update (Task 4 Step 4) keeps `test_full_pairing_two_rows` in sync with the new keys.
