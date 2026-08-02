# Legacy Standings Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render legacy standings-only events (every pairing is a single-player "bye") as a ranked standings table in the tournament-detail view, instead of a list of byes.

**Architecture:** One localized change to `web/ui/tournament-view.js`: detect a standings event (all pairings have `player2 === null`) and render a table (rank · player · record · points); real pairing events keep the existing rendering. The leaderboard and `app.js` are untouched.

**Tech Stack:** Vanilla ES modules, Node's built-in test runner (`node --test`).

---

## File Structure

- `web/ui/tournament-view.js` — add `isStandingsEvent()` and `renderStandings()`, and a guard at the top of `renderTournament()`. Existing `pairingRow()` / pairing rendering unchanged.
- `tests/web/tournament-view.test.mjs` — add tests for the standings path and a regression test for the pairing path.

**Environment note (executor):** Node is not on PATH; for node commands, first run
`export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`.
Git identity is configured; LF/CRLF warnings are harmless. No CSS changes are needed — the standings table reuses existing classes (`.t-header`, `.t-name`, `.t-meta`, `.row`, `.row.head`, `.rank`, `.player`, `.num`, `.num.strong`).

---

## Task 1: Render standings-only events as a table

**Files:**
- Modify: `web/ui/tournament-view.js`
- Test: `tests/web/tournament-view.test.mjs`

- [ ] **Step 1: Write the failing tests (append to `tests/web/tournament-view.test.mjs`)**

```js
test('renders a standings-only event as a ranked table, not byes', () => {
  const legacy = { name: 'Monday Standard', date: '2026-07-20', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Elliot N', game_wins: null, record: rec(3, 0, 0) }, player2: null },
      { pairing: 3, player1: { name: 'Vlad K', game_wins: null, record: rec(2, 0, 1) }, player2: null },
      { pairing: 2, player1: { name: 'Toms L', game_wins: null, record: rec(3, 0, 0) }, player2: null },
    ] },
  ] };
  const html = renderTournament(legacy);
  // No pairing/bye/round chrome
  assert.ok(!html.includes('Bye'));
  assert.ok(!html.includes('Round 1'));
  assert.ok(!html.includes('class="pairing'));
  // Table header present
  assert.match(html, /Player/);
  assert.match(html, /Points/);
  // Players present, sorted by rank (1,2,3)
  assert.ok(html.indexOf('Elliot N') < html.indexOf('Toms L'));
  assert.ok(html.indexOf('Toms L') < html.indexOf('Vlad K'));
  // Record shown W-D-L and points = 3*wins + draws
  assert.match(html, /3-0-0/);
  assert.match(html, /2-0-1/);
  assert.match(html, />9</);  // Elliot: 3*3+0
  assert.match(html, />6</);  // Vlad: 3*2+0
});

test('a normal pairing event still renders pairings (regression)', () => {
  const t = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(t);
  assert.match(html, /Round 1/);
  assert.match(html, /2-1/);          // game score
  assert.match(html, /class="pairing/);
});
```

Note: the `rec(w, d, l)` helper already exists at the top of this test file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/web/tournament-view.test.mjs`
Expected: FAIL — the standings test fails (a legacy event currently renders as byes: `Bye`/`Round 1` present). The regression test passes.

- [ ] **Step 3: Implement**

In `web/ui/tournament-view.js`, add these two functions **above** `renderTournament`:

```js
function isStandingsEvent(tournament) {
  const pairings = tournament.rounds.flatMap(round => round.pairings);
  return pairings.length > 0 && pairings.every(pairing => pairing.player2 === null);
}

function renderStandings(tournament) {
  const players = tournament.rounds
    .flatMap(round => round.pairings)
    .map(pairing => ({ rank: pairing.pairing, player: pairing.player1 }))
    .sort((a, b) => a.rank - b.rank);
  const header =
    `<div class="t-header"><div class="t-name">${tournament.name}</div>` +
    `<div class="t-meta">${tournament.date} · ${players.length} players</div></div>`;
  const head =
    '<div class="row head"><div>#</div><div>Player</div>' +
    '<div class="num">Record</div><div class="num">Points</div></div>';
  const body = players
    .map(({ rank, player }) => {
      const r = player.record;
      const points = r.wins * 3 + r.draws;
      return (
        `<div class="row">` +
        `<div class="rank">${rank}</div>` +
        `<div class="player">${player.name}</div>` +
        `<div class="num">${r.wins}-${r.draws}-${r.losses}</div>` +
        `<div class="num strong">${points}</div>` +
        `</div>`
      );
    })
    .join('');
  return header + head + body;
}
```

Then add a guard as the **first line** of `renderTournament`'s body:

```js
export function renderTournament(tournament) {
  if (isStandingsEvent(tournament)) return renderStandings(tournament);
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

(Only the guard line is new; the rest of `renderTournament` is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/web/tournament-view.test.mjs`
Expected: PASS (all tournament-view tests, including the two new ones).

- [ ] **Step 5: Run the whole web suite**

Run: `node --test tests/web/*.test.mjs`
Expected: PASS (no regressions across all web tests).

- [ ] **Step 6: Commit**

```bash
git add web/ui/tournament-view.js tests/web/tournament-view.test.mjs
git commit -m "feat(web): render legacy standings-only events as a table"
```

---

## Manual verification (optional, after the SUPABASE_URL secret is fixed)

Serve the site (`python -m http.server` in `web/`) against exported real data, open the Tournament tab, and select a legacy event (e.g. `2026-07-20 — Monday Standard`): it should show a ranked standings table (rank · player · record · points), while a new-format event still shows rounds/pairings.

---

## Self-Review Notes

- **Spec coverage:** standings detection via all-`player2`-null (Step 3 `isStandingsEvent`); standings table rank·player·record·points sorted by rank with `points = 3·wins + draws` and `W-D-L` record (Step 3 `renderStandings` + Step 1 assertions); real pairing events unchanged (regression test); leaderboard/`app.js` untouched (not modified). All spec front-end requirements map to Task 1.
- **Placeholder scan:** none; full code shown for every change.
- **Type consistency:** `renderStandings` reads `pairing.pairing`, `pairing.player1.{name,record.{wins,draws,losses}}` — matching the shape `build_site_data` emits and the test fixtures. Reused CSS classes all exist in `web/styles.css`.
