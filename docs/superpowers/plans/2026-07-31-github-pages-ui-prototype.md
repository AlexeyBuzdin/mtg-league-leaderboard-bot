# GitHub Pages UI Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a vanilla, no-build static GitHub Pages site that shows a quarterly leaderboard and a tournament detail view (rounds + pairings) from a local mock JSON file shaped like the planned `tournaments`/`round_results` data.

**Architecture:** Native ES modules split into pure logic (`web/lib/`), pure HTML-string renderers (`web/ui/`), a thin DOM wiring layer (`web/app.js`), a static `index.html`/`styles.css`, and a mock `data/*.json`. Pure modules are unit-tested with Node's built-in test runner (`node --test`, `.mjs` tests). Two GitHub Actions workflows: one runs the tests, one deploys `web/` to Pages. Delivered as a pull request from a dedicated worktree/branch.

**Tech Stack:** Vanilla HTML/CSS/JavaScript (ES modules), Node.js `node:test` (dev/CI only — no runtime deps, no bundler), GitHub Actions Pages.

---

## File Structure

- `web/package.json` — `{"type":"module"}` so Node treats `web/**/*.js` as ES modules
- `web/data/mock-tournaments.json` — mock dataset (new structure; multi-round, a bye, diacritics)
- `web/lib/quarter.js` — `quarterOf`, `quarterKey` (pure)
- `web/lib/leaderboard.js` — `finalRecords`, `points`, `quarterLeaderboard` (pure)
- `web/ui/leaderboard-view.js` — `renderLeaderboard(rows)` → HTML string (pure)
- `web/ui/tournament-view.js` — `renderTournament(tournament)` → HTML string (pure)
- `web/app.js` — fetch data, wire nav + selectors, inject rendered HTML (DOM; not unit-tested)
- `web/index.html` — shell: header, nav, two view sections, selectors
- `web/styles.css` — theme-aware styles (light/dark)
- `tests/web/quarter.test.mjs` — unit tests for `quarter.js`
- `tests/web/leaderboard.test.mjs` — unit tests for `leaderboard.js`
- `tests/web/leaderboard-view.test.mjs` — unit tests for the leaderboard renderer
- `tests/web/tournament-view.test.mjs` — unit tests for the tournament renderer
- `.github/workflows/web-ci.yml` — runs `node --test tests/web/`
- `.github/workflows/pages.yml` — deploys `web/` to GitHub Pages

Display separators use a plain hyphen `-` (e.g. records `1-0-0`, scores `2-1`) to avoid cross-file encoding pitfalls. Node is invoked as `node` (available on the runner and locally).

---

## Task 1: Scaffolding + mock dataset

**Files:**
- Create: `web/package.json`
- Create: `web/data/mock-tournaments.json`

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "type": "module",
  "private": true
}
```

- [ ] **Step 2: Create `web/data/mock-tournaments.json`**

Three tournaments across two quarters (Q2 and Q3 2026); tournament `b` includes byes (`player2: null`); names include Latvian diacritics. Records are cumulative W-D-L after each round.

```json
{
  "tournaments": [
    {
      "id": "a",
      "name": "Standard Showdown",
      "date": "2026-07-06",
      "rounds": [
        {
          "round": 1,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "Nikita Petrov", "game_wins": 1, "record": { "wins": 0, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "Mārtiņš Kalniņš", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "Artur Sokolov", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 1 } } },
            { "pairing": 3, "player1": { "name": "James Bond", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "Sergejs Ivanov", "game_wins": 1, "record": { "wins": 0, "draws": 0, "losses": 1 } } }
          ]
        },
        {
          "round": 2,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 2, "draws": 0, "losses": 0 } }, "player2": { "name": "Mārtiņš Kalniņš", "game_wins": 1, "record": { "wins": 1, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "James Bond", "game_wins": 2, "record": { "wins": 2, "draws": 0, "losses": 0 } }, "player2": { "name": "Nikita Petrov", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 2 } } },
            { "pairing": 3, "player1": { "name": "Artur Sokolov", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 1 } }, "player2": { "name": "Sergejs Ivanov", "game_wins": 1, "record": { "wins": 0, "draws": 0, "losses": 2 } } }
          ]
        },
        {
          "round": 3,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 3, "draws": 0, "losses": 0 } }, "player2": { "name": "James Bond", "game_wins": 1, "record": { "wins": 2, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "Mārtiņš Kalniņš", "game_wins": 2, "record": { "wins": 2, "draws": 0, "losses": 1 } }, "player2": { "name": "Artur Sokolov", "game_wins": 1, "record": { "wins": 1, "draws": 0, "losses": 2 } } },
            { "pairing": 3, "player1": { "name": "Nikita Petrov", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 2 } }, "player2": { "name": "Sergejs Ivanov", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 3 } } }
          ]
        }
      ]
    },
    {
      "id": "b",
      "name": "Store Championship",
      "date": "2026-08-17",
      "rounds": [
        {
          "round": 1,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "James Bond", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "Nikita Petrov", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "Toms Bērziņš", "game_wins": 1, "record": { "wins": 0, "draws": 0, "losses": 1 } } },
            { "pairing": 3, "player1": { "name": "Mārtiņš Kalniņš", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": null }
          ]
        },
        {
          "round": 2,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 2, "draws": 0, "losses": 0 } }, "player2": { "name": "Nikita Petrov", "game_wins": 1, "record": { "wins": 1, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "James Bond", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 1 } }, "player2": { "name": "Toms Bērziņš", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 2 } } },
            { "pairing": 3, "player1": { "name": "Mārtiņš Kalniņš", "game_wins": 2, "record": { "wins": 2, "draws": 0, "losses": 0 } }, "player2": null }
          ]
        }
      ]
    },
    {
      "id": "c",
      "name": "Spring Showdown",
      "date": "2026-04-12",
      "rounds": [
        {
          "round": 1,
          "pairings": [
            { "pairing": 1, "player1": { "name": "Raitis Ozols", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "James Bond", "game_wins": 1, "record": { "wins": 0, "draws": 0, "losses": 1 } } },
            { "pairing": 2, "player1": { "name": "Artur Sokolov", "game_wins": 2, "record": { "wins": 1, "draws": 0, "losses": 0 } }, "player2": { "name": "Sergejs Ivanov", "game_wins": 0, "record": { "wins": 0, "draws": 0, "losses": 1 } } }
          ]
        }
      ]
    }
  ]
}
```

- [ ] **Step 3: Validate the JSON parses**

Run: `node -e "JSON.parse(require('fs').readFileSync('web/data/mock-tournaments.json','utf8')); console.log('ok')"`
Expected: prints `ok`, exit 0.

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/data/mock-tournaments.json
git commit -m "feat(web): add package marker and mock tournament dataset"
```

---

## Task 2: `lib/quarter.js`

**Files:**
- Create: `web/lib/quarter.js`
- Test: `tests/web/quarter.test.mjs`

- [ ] **Step 1: Write the failing test**

`tests/web/quarter.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { quarterOf, quarterKey } from '../../web/lib/quarter.js';

test('quarterOf maps months to calendar quarters', () => {
  assert.deepEqual(quarterOf('2026-01-15'), { year: 2026, quarter: 1 });
  assert.deepEqual(quarterOf('2026-03-31'), { year: 2026, quarter: 1 });
  assert.deepEqual(quarterOf('2026-04-01'), { year: 2026, quarter: 2 });
  assert.deepEqual(quarterOf('2026-07-06'), { year: 2026, quarter: 3 });
  assert.deepEqual(quarterOf('2026-12-31'), { year: 2026, quarter: 4 });
});

test('quarterKey formats year and quarter', () => {
  assert.equal(quarterKey('2026-07-06'), '2026-Q3');
  assert.equal(quarterKey('2025-11-02'), '2025-Q4');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/web/quarter.test.mjs`
Expected: FAIL — cannot find module `web/lib/quarter.js`.

- [ ] **Step 3: Write minimal implementation**

`web/lib/quarter.js`:
```js
export function quarterOf(dateString) {
  const year = Number(dateString.slice(0, 4));
  const month = Number(dateString.slice(5, 7));
  const quarter = Math.floor((month - 1) / 3) + 1;
  return { year, quarter };
}

export function quarterKey(dateString) {
  const { year, quarter } = quarterOf(dateString);
  return `${year}-Q${quarter}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/web/quarter.test.mjs`
Expected: PASS (2 tests, 0 failures).

- [ ] **Step 5: Commit**

```bash
git add web/lib/quarter.js tests/web/quarter.test.mjs
git commit -m "feat(web): add quarter helpers"
```

---

## Task 3: `lib/leaderboard.js`

**Files:**
- Create: `web/lib/leaderboard.js`
- Test: `tests/web/leaderboard.test.mjs`

- [ ] **Step 1: Write the failing test**

`tests/web/leaderboard.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { finalRecords, points, quarterLeaderboard } from '../../web/lib/leaderboard.js';

const rec = (w, d, l) => ({ wins: w, draws: d, losses: l });

const t1 = {
  id: 'a', name: 'A', date: '2026-07-06',
  rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
    { round: 2, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(2, 0, 0) }, player2: { name: 'Bob', game_wins: 0, record: rec(0, 0, 2) } },
      { pairing: 2, player1: { name: 'Cara', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ],
};

test('finalRecords keeps the last record per player and includes byes', () => {
  const f = finalRecords(t1);
  assert.deepEqual(f['Ann'], rec(2, 0, 0));
  assert.deepEqual(f['Bob'], rec(0, 0, 2));
  assert.deepEqual(f['Cara'], rec(1, 0, 0));
});

test('points = 3*wins + draws', () => {
  assert.equal(points(rec(2, 1, 0)), 7);
  assert.equal(points(rec(0, 0, 3)), 0);
});

test('quarterLeaderboard sums points, counts events, filters by quarter, sorts', () => {
  const t2 = { id: 'b', name: 'B', date: '2026-08-01', rounds: [
    { round: 1, pairings: [ { pairing: 1, player1: { name: 'Bob', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Ann', game_wins: 0, record: rec(0, 0, 1) } } ] },
  ] };
  const q2Tournament = { id: 'c', name: 'C', date: '2026-04-01', rounds: [
    { round: 1, pairings: [ { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Zed', game_wins: 0, record: rec(0, 0, 1) } } ] },
  ] };
  const board = quarterLeaderboard([t1, t2, q2Tournament], '2026-Q3');
  assert.deepEqual(board.map(r => r.name), ['Ann', 'Bob', 'Cara']);
  assert.equal(board[0].points, 6);
  assert.equal(board[0].events, 2);
  assert.equal(board[1].name, 'Bob');
  assert.equal(board[1].points, 3);
  assert.equal(board[1].events, 2);
  assert.equal(board[2].name, 'Cara');
  assert.equal(board[2].events, 1);
  assert.ok(!board.find(r => r.name === 'Zed'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/web/leaderboard.test.mjs`
Expected: FAIL — cannot find module `web/lib/leaderboard.js`.

- [ ] **Step 3: Write minimal implementation**

`web/lib/leaderboard.js`:
```js
import { quarterKey } from './quarter.js';

export function finalRecords(tournament) {
  const last = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      last[pairing.player1.name] = pairing.player1.record;
      if (pairing.player2) {
        last[pairing.player2.name] = pairing.player2.record;
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
    for (const [name, record] of Object.entries(finals)) {
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += points(record);
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/web/leaderboard.test.mjs`
Expected: PASS (3 tests, 0 failures).

- [ ] **Step 5: Commit**

```bash
git add web/lib/leaderboard.js tests/web/leaderboard.test.mjs
git commit -m "feat(web): add leaderboard aggregation logic"
```

---

## Task 4: `ui/leaderboard-view.js`

**Files:**
- Create: `web/ui/leaderboard-view.js`
- Test: `tests/web/leaderboard-view.test.mjs`

- [ ] **Step 1: Write the failing test**

`tests/web/leaderboard-view.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderLeaderboard } from '../../web/ui/leaderboard-view.js';

test('renders ranked rows with names, initials, and preserves order', () => {
  const html = renderLeaderboard([
    { name: 'Ann Lee', points: 9, events: 3 },
    { name: 'Bob', points: 3, events: 1 },
  ]);
  assert.match(html, /Ann Lee/);
  assert.match(html, /AL/);
  assert.match(html, />1</);
  assert.ok(html.indexOf('Ann Lee') < html.indexOf('Bob'));
});

test('shows an empty state when there are no rows', () => {
  assert.match(renderLeaderboard([]), /No results/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/web/leaderboard-view.test.mjs`
Expected: FAIL — cannot find module `web/ui/leaderboard-view.js`.

- [ ] **Step 3: Write minimal implementation**

`web/ui/leaderboard-view.js`:
```js
function initials(name) {
  return name
    .split(/\s+/)
    .map(word => word[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export function renderLeaderboard(rows) {
  if (rows.length === 0) {
    return '<div class="empty">No results for this quarter.</div>';
  }
  const medal = ['#BA7517', '#888780', '#993C1D'];
  const head =
    '<div class="row head"><div>#</div><div>Player</div>' +
    '<div class="num">Events</div><div class="num">Points</div></div>';
  const body = rows
    .map((row, index) => {
      const rank = index + 1;
      const color = medal[index] || 'var(--muted)';
      return (
        `<div class="row">` +
        `<div class="rank" style="color:${color}">${rank}</div>` +
        `<div class="player"><span class="avatar">${initials(row.name)}</span>${row.name}</div>` +
        `<div class="num">${row.events}</div>` +
        `<div class="num strong">${row.points}</div>` +
        `</div>`
      );
    })
    .join('');
  return head + body;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/web/leaderboard-view.test.mjs`
Expected: PASS (2 tests, 0 failures).

- [ ] **Step 5: Commit**

```bash
git add web/ui/leaderboard-view.js tests/web/leaderboard-view.test.mjs
git commit -m "feat(web): add leaderboard renderer"
```

---

## Task 5: `ui/tournament-view.js`

**Files:**
- Create: `web/ui/tournament-view.js`
- Test: `tests/web/tournament-view.test.mjs`

- [ ] **Step 1: Write the failing test**

`tests/web/tournament-view.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderTournament } from '../../web/ui/tournament-view.js';

const rec = (w, d, l) => ({ wins: w, draws: d, losses: l });

test('marks the game-score winner and shows round labels and records', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.match(html, /Round 1/);
  assert.match(html, /1-0-0/);
  assert.match(html, /2-1/);
  const markIndex = html.indexOf('✓');
  const scoreIndex = html.indexOf('2-1');
  assert.ok(markIndex > -1 && markIndex < scoreIndex);
});

test('renders a bye as a single-player row', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Cara', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.match(html, /Bye/);
  assert.match(html, /Cara/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/web/tournament-view.test.mjs`
Expected: FAIL — cannot find module `web/ui/tournament-view.js`.

- [ ] **Step 3: Write minimal implementation**

`web/ui/tournament-view.js`. The winner is the side with more `game_wins`; the check mark (`✓`) is emitted before the score for a player-1 win and after the score for a player-2 win:
```js
function recordChip(record) {
  return `<span class="chip">${record.wins}-${record.draws}-${record.losses}</span>`;
}

const MARK = '<span class="mark">✓</span>';

function pairingRow(pairing) {
  const p1 = pairing.player1;
  if (!pairing.player2) {
    return (
      `<div class="pairing bye">` +
      `<div class="side win">${MARK}<span class="name">${p1.name}</span>${recordChip(p1.record)}</div>` +
      `<div class="score">Bye</div>` +
      `<div class="side right"></div>` +
      `</div>`
    );
  }
  const p2 = pairing.player2;
  const p1Won = p1.game_wins > p2.game_wins;
  return (
    `<div class="pairing">` +
    `<div class="side ${p1Won ? 'win' : ''}">${p1Won ? MARK : ''}<span class="name">${p1.name}</span>${recordChip(p1.record)}</div>` +
    `<div class="score">${p1.game_wins}-${p2.game_wins}</div>` +
    `<div class="side right ${p1Won ? '' : 'win'}">${recordChip(p2.record)}<span class="name">${p2.name}</span>${p1Won ? '' : MARK}</div>` +
    `</div>`
  );
}

export function renderTournament(tournament) {
  const header =
    `<div class="t-header"><div class="t-name">${tournament.name}</div>` +
    `<div class="t-meta">${tournament.date} · ${tournament.rounds.length} rounds</div></div>`;
  const rounds = tournament.rounds
    .map(round => {
      const pairings = round.pairings.map(pairingRow).join('');
      return `<div class="round-label">Round ${round.round}</div>${pairings}`;
    })
    .join('');
  return header + rounds;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/web/tournament-view.test.mjs`
Expected: PASS (2 tests, 0 failures).

- [ ] **Step 5: Run the whole web test suite**

Run: `node --test tests/web/`
Expected: PASS (all 9 tests across 4 files, 0 failures).

- [ ] **Step 6: Commit**

```bash
git add web/ui/tournament-view.js tests/web/tournament-view.test.mjs
git commit -m "feat(web): add tournament detail renderer"
```

---

## Task 6: Shell, styles, and wiring (`index.html`, `styles.css`, `app.js`)

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`

- [ ] **Step 1: Create `web/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MTG Latvia — Standard League</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header class="topbar">
      <div class="brand">MTG Latvia — Standard League</div>
      <nav class="tabs">
        <button id="tab-lb" class="tab" aria-selected="true">Leaderboard</button>
        <button id="tab-td" class="tab" aria-selected="false">Tournament</button>
      </nav>
    </header>
    <main>
      <section id="view-lb">
        <div class="controls">
          <label for="q-sel">Quarter</label>
          <select id="q-sel"></select>
          <span id="q-meta" class="meta"></span>
        </div>
        <div id="lb-body"></div>
      </section>
      <section id="view-td" hidden>
        <div class="controls">
          <label for="t-sel">Tournament</label>
          <select id="t-sel"></select>
        </div>
        <div id="td-body"></div>
      </section>
    </main>
    <script type="module" src="app.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Create `web/styles.css`**

```css
:root {
  --bg: #ffffff;
  --surface: #f7f6f2;
  --text: #1f1f1d;
  --muted: #6b6b66;
  --border: #e3e1d9;
  --accent-bg: #e6f1fb;
  --accent-text: #0c447c;
  --win: #0f6e56;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a18;
    --surface: #242422;
    --text: #eceae2;
    --muted: #a2a199;
    --border: #38372f;
    --accent-bg: #0c447c;
    --accent-text: #b5d4f4;
    --win: #5dcaa5;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.5;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.brand { font-weight: 500; font-size: 18px; }
.tabs { display: flex; gap: 8px; }
.tab {
  padding: 7px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font-size: 14px;
  cursor: pointer;
}
.tab[aria-selected="true"] {
  background: var(--accent-bg);
  color: var(--accent-text);
  border-color: var(--accent-bg);
}
main { max-width: 720px; margin: 0 auto; padding: 20px; }
.controls { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.controls label { font-size: 13px; color: var(--muted); }
select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
}
.meta { font-size: 13px; color: var(--muted); margin-left: auto; }
.row {
  display: grid;
  grid-template-columns: 40px 1fr 70px 70px;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.row.head { color: var(--muted); font-size: 12px; }
.rank { font-weight: 500; }
.num { text-align: right; }
.num.strong { font-weight: 500; }
.player { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--accent-bg);
  color: var(--accent-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
}
.empty { padding: 20px 12px; color: var(--muted); }
.t-header { margin-bottom: 12px; }
.t-name { font-size: 16px; font-weight: 500; }
.t-meta { font-size: 13px; color: var(--muted); }
.round-label { font-size: 13px; color: var(--muted); font-weight: 500; margin: 14px 0 6px; }
.pairing {
  display: grid;
  grid-template-columns: 1fr 66px 1fr;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  background: var(--surface);
}
.side { display: flex; align-items: center; gap: 8px; min-width: 0; }
.side.right { justify-content: flex-end; text-align: right; }
.side.win .name { font-weight: 500; }
.mark { color: var(--win); font-weight: 500; }
.chip {
  font-size: 12px;
  padding: 2px 7px;
  border-radius: 20px;
  border: 1px solid var(--border);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.score { text-align: center; font-size: 15px; font-variant-numeric: tabular-nums; }
```

- [ ] **Step 3: Create `web/app.js`**

```js
import { quarterKey } from './lib/quarter.js';
import { quarterLeaderboard } from './lib/leaderboard.js';
import { renderLeaderboard } from './ui/leaderboard-view.js';
import { renderTournament } from './ui/tournament-view.js';

const state = { tournaments: [] };

async function boot() {
  try {
    const response = await fetch('data/mock-tournaments.json');
    if (!response.ok) throw new Error('bad status');
    state.tournaments = (await response.json()).tournaments;
  } catch {
    document.getElementById('lb-body').innerHTML =
      '<div class="empty">Couldn\'t load data.</div>';
    return;
  }
  setupTabs();
  setupLeaderboard();
  setupTournaments();
}

function setupTabs() {
  const tabLb = document.getElementById('tab-lb');
  const tabTd = document.getElementById('tab-td');
  const viewLb = document.getElementById('view-lb');
  const viewTd = document.getElementById('view-td');
  function show(which) {
    const isLb = which === 'lb';
    viewLb.hidden = !isLb;
    viewTd.hidden = isLb;
    tabLb.setAttribute('aria-selected', String(isLb));
    tabTd.setAttribute('aria-selected', String(!isLb));
  }
  tabLb.addEventListener('click', () => show('lb'));
  tabTd.addEventListener('click', () => show('td'));
}

function setupLeaderboard() {
  const select = document.getElementById('q-sel');
  const quarters = [...new Set(state.tournaments.map(t => quarterKey(t.date)))]
    .sort()
    .reverse();
  select.innerHTML = quarters
    .map(q => `<option value="${q}">${q.replace('-', ' · ')}</option>`)
    .join('');
  function render() {
    const key = select.value;
    const rows = quarterLeaderboard(state.tournaments, key);
    const count = state.tournaments.filter(t => quarterKey(t.date) === key).length;
    document.getElementById('q-meta').textContent =
      `${count} tournaments · ${rows.length} players`;
    document.getElementById('lb-body').innerHTML = renderLeaderboard(rows);
  }
  select.addEventListener('change', render);
  render();
}

function setupTournaments() {
  const select = document.getElementById('t-sel');
  const sorted = [...state.tournaments].sort((a, b) => b.date.localeCompare(a.date));
  select.innerHTML = sorted
    .map(t => `<option value="${t.id}">${t.date} — ${t.name}</option>`)
    .join('');
  function render() {
    const tournament = state.tournaments.find(t => t.id === select.value);
    document.getElementById('td-body').innerHTML = renderTournament(tournament);
  }
  select.addEventListener('change', render);
  render();
}

boot();
```

- [ ] **Step 4: Manually verify in a browser**

Run a static server from the `web/` directory (Python is available):
```bash
cd web && python -m http.server 8000
```
Open `http://localhost:8000`. Verify:
- Leaderboard loads on Q3 2026: Raitis Ozols 15 (2 events) at rank 1, Mārtiņš Kalniņš 12, James Bond 9.
- Switching the quarter to Q2 2026 changes the table (Artur Sokolov and Raitis Ozols at 3).
- The Tournament tab shows rounds/pairings; the winner has a check; Store Championship (2026-08-17) shows a "Bye" row for Mārtiņš Kalniņš.
Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/styles.css web/app.js
git commit -m "feat(web): add shell, styles, and app wiring"
```

---

## Task 7: CI and Pages workflows

**Files:**
- Create: `.github/workflows/web-ci.yml`
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Create `.github/workflows/web-ci.yml`**

```yaml
name: web-ci
on:
  push:
    paths:
      - "web/**"
      - "tests/web/**"
      - ".github/workflows/web-ci.yml"
  pull_request:
    paths:
      - "web/**"
      - "tests/web/**"
      - ".github/workflows/web-ci.yml"
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: node --test tests/web/
```

- [ ] **Step 2: Create `.github/workflows/pages.yml`**

```yaml
name: pages
on:
  push:
    branches: [main]
    paths:
      - "web/**"
      - ".github/workflows/pages.yml"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Validate workflow YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/web-ci.yml')); yaml.safe_load(open('.github/workflows/pages.yml')); print('ok')"`
Expected: prints `ok`, exit 0.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/web-ci.yml .github/workflows/pages.yml
git commit -m "ci(web): add test and github pages deploy workflows"
```

---

## Notes for delivery

- This work is delivered as a **pull request** from a dedicated worktree/branch (do not merge to `main` directly).
- GitHub Pages requires a one-time manual setting: repo **Settings → Pages → Source = GitHub Actions**. Note this in the PR description; the `pages.yml` deploy will fail until it is set.

---

## Self-Review Notes

- **Spec coverage:** quarterly leaderboard view (Tasks 3,4,6), tournament detail with rounds/pairings/records/winner (Tasks 5,6), byes (Tasks 1,5), quarter selector + tournament selector + two-view nav (Task 6), vanilla no-build stack (all), mock JSON mirroring the new structure (Task 1), points = 3W+D from final record (Task 3), tie-break points desc then name asc (Task 3), calendar-quarter definition (Task 2), theme-aware styling (Task 6), unit tests via `node --test` for pure logic and renderers (Tasks 2–5), Pages deploy workflow (Task 7), PR delivery + one-time Pages setting (Notes). All spec sections map to tasks.
- **Placeholder scan:** no TBD/TODO; every code step contains full file content.
- **Type consistency:** `quarterKey`/`quarterOf` (Task 2) are consumed unchanged in Task 3; `quarterLeaderboard` returns `{name, points, events}` rows consumed by `renderLeaderboard` (Task 4) and `app.js` (Task 6); `renderTournament`/`renderLeaderboard` signatures match their `app.js` call sites; the mock JSON field names (`game_wins`, `record.{wins,draws,losses}`, `player2: null`) match what `finalRecords` and `pairingRow` read.
