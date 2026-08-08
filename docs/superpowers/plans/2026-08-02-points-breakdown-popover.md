# Leaderboard Points Breakdown Popover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "?" icon after each leaderboard player's points that opens a popover showing the full per-tournament, itemized points calculation.

**Architecture:** `seasonLeaderboard` gains a per-player `breakdown` array (built in `tournamentScores`); pure renderers add a `.why` button and a `renderBreakdown` string; `app.js` wires a single anchored popover element with dismissal. Website only.

**Tech Stack:** Vanilla JS + `node --test`; CSS.

---

## File Structure

- `web/lib/leaderboard.js` — itemized `breakdown` in `tournamentScores` + `seasonLeaderboard`
- `web/ui/leaderboard-view.js` — `.why` button in `renderLeaderboard`; new `renderBreakdown`
- `web/app.js` — popover open/position/dismiss wiring
- `web/index.html` — `#breakdown-popover` element
- `web/styles.css` — `.why`, `.breakdown-popover`, `.bd-*`
- `tests/web/leaderboard.test.mjs`, `tests/web/leaderboard-view.test.mjs` — tests

**Environment:** Node not on PATH; prepend in Bash node commands:
`export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`. Git identity configured; LF/CRLF warnings harmless.

---

## Task 1: Baseline

- [ ] **Step 1:** Run web tests:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --test tests/web/*.test.mjs
```
Expected: all pass.

---

## Task 2: Breakdown data (`web/lib/leaderboard.js`)

**Files:** Modify `web/lib/leaderboard.js`; Test `tests/web/leaderboard.test.mjs`

- [ ] **Step 1: Add failing tests** — append to `tests/web/leaderboard.test.mjs`:
```js
test('seasonLeaderboard attaches an itemized breakdown (summer)', () => {
  const t = { id: 't', name: 'Showdown', date: '2026-07-10', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(2, 1, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  const ann = board.find(r => r.name === 'Ann');
  assert.equal(ann.breakdown.length, 1);
  const e = ann.breakdown[0];
  assert.equal(e.tournament, 'Showdown');
  assert.equal(e.date, '2026-07-10');
  assert.deepEqual(e.items, [
    { label: '1st place', points: 3 },
    { label: '2 wins (×2)', points: 4 },
    { label: '1 draw (×1)', points: 1 },
    { label: 'attendance', points: 1 },
  ]);
  assert.equal(e.subtotal, 9);
  assert.equal(ann.points, 9);
});

test('breakdown omits zero components and uses ×3 off-summer', () => {
  const t = { id: 't', name: 'Spring', date: '2026-04-12', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(2, 0, 0) }, player2: { name: 'Bob', game_wins: 0, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-1');
  const ann = board.find(r => r.name === 'Ann');
  assert.deepEqual(ann.breakdown[0].items, [{ label: '2 wins (×3)', points: 6 }]);
  assert.equal(ann.breakdown[0].subtotal, 6);
  const bob = board.find(r => r.name === 'Bob');
  assert.deepEqual(bob.breakdown[0].items, []); // 0 wins, 0 draws off-summer
  assert.equal(bob.points, 0);
});
```

- [ ] **Step 2: Run to verify failure**

Run (after PATH export): `node --test tests/web/leaderboard.test.mjs`
Expected: FAIL (`breakdown` undefined).

- [ ] **Step 3: Update `web/lib/leaderboard.js`.** Add a `plural` helper and an `ORD` constant, and rewrite `tournamentScores` and `seasonLeaderboard`:
```js
const ORD = ['1st', '2nd', '3rd'];

function plural(n, word) {
  return `${n} ${n === 1 ? word : word + 's'}`;
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
    const items = [];
    if (summer) {
      if (i < 3) items.push({ label: `${ORD[i]} place`, points: bonus[i] });
      if (p.record.wins > 0) items.push({ label: `${plural(p.record.wins, 'win')} (×2)`, points: 2 * p.record.wins });
      if (p.record.draws > 0) items.push({ label: `${plural(p.record.draws, 'draw')} (×1)`, points: p.record.draws });
      items.push({ label: 'attendance', points: 1 });
    } else {
      if (p.record.wins > 0) items.push({ label: `${plural(p.record.wins, 'win')} (×3)`, points: 3 * p.record.wins });
      if (p.record.draws > 0) items.push({ label: `${plural(p.record.draws, 'draw')} (×1)`, points: p.record.draws });
    }
    const subtotal = items.reduce((sum, it) => sum + it.points, 0);
    scores[p.name] = {
      score: subtotal,
      isLeague: p.isLeague,
      breakdown: { tournament: tournament.name, date: tournament.date, items, subtotal },
    };
  });
  return scores;
}

export function seasonLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (seasonKey(tournament.date) !== key) continue;
    const scored = tournamentScores(tournament);
    for (const [name, { score, isLeague, breakdown }] of Object.entries(scored)) {
      if (!isLeague) continue;
      if (!agg[name]) agg[name] = { name, points: 0, events: 0, breakdown: [] };
      agg[name].points += score;
      agg[name].events += 1;
      agg[name].breakdown.push(breakdown);
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
```
(Note: `score` now equals the item sum, which equals the previous formula — so existing point-value tests still pass.)

- [ ] **Step 4: Run all web tests**

Run (after PATH export): `node --test tests/web/*.test.mjs`
Expected: PASS (existing summer/season tests unchanged; new breakdown tests pass).

- [ ] **Step 5: Commit**

```bash
git add web/lib/leaderboard.js tests/web/leaderboard.test.mjs
git commit -m "feat(web): add per-tournament points breakdown to leaderboard rows"
```

---

## Task 3: Renderers (`web/ui/leaderboard-view.js`)

**Files:** Modify `web/ui/leaderboard-view.js`; Test `tests/web/leaderboard-view.test.mjs`

- [ ] **Step 1: Add failing tests** — append to `tests/web/leaderboard-view.test.mjs`:
```js
import { renderBreakdown } from '../../web/ui/leaderboard-view.js';

test('renderLeaderboard adds one breakdown button per row', () => {
  const html = renderLeaderboard([
    { name: 'Ann Lee', points: 9, events: 1, breakdown: [] },
    { name: 'Bob', points: 3, events: 1, breakdown: [] },
  ]);
  assert.equal((html.match(/class="why"/g) || []).length, 2);
  assert.match(html, /data-index="0"/);
  assert.match(html, /data-index="1"/);
});

test('renderBreakdown lists tournaments, items, subtotals and total', () => {
  const row = { name: 'Ann', points: 9, events: 1, breakdown: [
    { tournament: 'Showdown', date: '2026-07-10', items: [
      { label: '1st place', points: 3 },
      { label: '2 wins (×2)', points: 4 },
      { label: 'attendance', points: 1 },
    ], subtotal: 8 },
    { tournament: 'Store', date: '2026-08-01', items: [{ label: 'attendance', points: 1 }], subtotal: 1 },
  ] };
  const html = renderBreakdown(row);
  assert.match(html, /Ann — 9 pts/);
  assert.match(html, /Showdown · 2026-07-10/);
  assert.match(html, /1st place/);
  assert.match(html, /\+4/);
  assert.match(html, /Store · 2026-08-01/);
  assert.match(html, /Total/);
});
```

- [ ] **Step 2: Run to verify failure**

Run (after PATH export): `node --test tests/web/leaderboard-view.test.mjs`
Expected: FAIL (`renderBreakdown` not exported; no `.why`).

- [ ] **Step 3: Update `web/ui/leaderboard-view.js`.** In `renderLeaderboard`, change the points cell to include the button; add `renderBreakdown`. Replace the points-cell line inside the `.map`:
```js
        `<div class="num strong">${row.points}<button class="why" data-index="${index}" aria-label="Points breakdown for ${row.name}">?</button></div>` +
```
Append:
```js
export function renderBreakdown(row) {
  const sections = row.breakdown
    .map(t => {
      const items = t.items
        .map(it => `<div class="bd-item"><span>${it.label}</span><span>+${it.points}</span></div>`)
        .join('');
      return (
        `<div class="bd-tournament">${t.tournament} · ${t.date}</div>` +
        items +
        `<div class="bd-subtotal"><span>subtotal</span><span>${t.subtotal}</span></div>`
      );
    })
    .join('');
  return (
    `<div class="bd-head">${row.name} — ${row.points} pts</div>` +
    `<div class="bd-body">${sections}` +
    `<div class="bd-total"><span>Total</span><span>${row.points}</span></div></div>`
  );
}
```

- [ ] **Step 4: Run all web tests**

Run (after PATH export): `node --test tests/web/*.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/ui/leaderboard-view.js tests/web/leaderboard-view.test.mjs
git commit -m "feat(web): add breakdown button and renderBreakdown to the leaderboard view"
```

---

## Task 4: Popover wiring + styles (`web/app.js`, `web/index.html`, `web/styles.css`)

**Files:** Modify `web/app.js`, `web/index.html`, `web/styles.css`

- [ ] **Step 1: Add the popover element to `web/index.html`** — just before the closing `</body>` (or after `<main>`), add:
```html
    <div id="breakdown-popover" class="breakdown-popover" hidden></div>
```

- [ ] **Step 2: Import `renderBreakdown` in `web/app.js`** — update the import line:
```js
import { renderLeaderboard, renderBreakdown } from './ui/leaderboard-view.js';
```

- [ ] **Step 3: Rewrite `setupLeaderboard` in `web/app.js`** to keep `currentRows` and wire the popover:
```js
function setupLeaderboard() {
  const select = document.getElementById('q-sel');
  const body = document.getElementById('lb-body');
  const pop = document.getElementById('breakdown-popover');
  let currentRows = [];

  const byKey = new Map();
  for (const t of state.tournaments) byKey.set(seasonKey(t.date), seasonLabel(t.date));
  const keys = [...byKey.keys()].sort().reverse();
  select.innerHTML = keys.map(k => `<option value="${k}">${byKey.get(k)}</option>`).join('');

  function hidePopover() {
    pop.hidden = true;
    delete pop.dataset.index;
  }

  function render() {
    const key = select.value;
    currentRows = seasonLeaderboard(state.tournaments, key);
    const count = state.tournaments.filter(t => seasonKey(t.date) === key).length;
    document.getElementById('q-meta').textContent = `${count} tournaments · ${currentRows.length} players`;
    body.innerHTML = renderLeaderboard(currentRows);
    hidePopover();
  }

  body.addEventListener('click', event => {
    const btn = event.target.closest('.why');
    if (!btn) return;
    event.stopPropagation();
    if (!pop.hidden && pop.dataset.index === btn.dataset.index) {
      hidePopover();
      return;
    }
    pop.innerHTML = renderBreakdown(currentRows[Number(btn.dataset.index)]);
    pop.dataset.index = btn.dataset.index;
    pop.hidden = false;
    const rect = btn.getBoundingClientRect();
    pop.style.top = `${window.scrollY + rect.bottom + 6}px`;
    let left = window.scrollX + rect.left;
    const maxLeft = window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    pop.style.left = `${left}px`;
  });

  document.addEventListener('click', event => {
    if (pop.hidden) return;
    if (pop.contains(event.target) || event.target.closest('.why')) return;
    hidePopover();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') hidePopover();
  });

  select.addEventListener('change', render);
  render();
}
```

- [ ] **Step 4: Add styles to `web/styles.css`** (append):
```css
.why {
  margin-left: 6px;
  width: 16px;
  height: 16px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  vertical-align: 1px;
}
.why:hover { border-color: var(--accent-text); color: var(--accent-text); }
.breakdown-popover {
  position: absolute;
  z-index: 20;
  max-width: 260px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
  padding: 12px 14px;
  font-size: 13px;
  color: var(--text);
}
.bd-head { font-weight: 500; margin-bottom: 8px; }
.bd-tournament { color: var(--muted); font-size: 12px; margin: 8px 0 4px; }
.bd-item, .bd-subtotal, .bd-total { display: flex; justify-content: space-between; gap: 16px; }
.bd-subtotal { border-top: 1px solid var(--border); margin-top: 4px; padding-top: 3px; color: var(--muted); }
.bd-total { margin-top: 8px; padding-top: 6px; border-top: 1px solid var(--border); font-weight: 500; }
```

- [ ] **Step 5: Manual browser verification.** Serve `web/` (`python -m http.server 8201 --directory web`), open the leaderboard, click a "?" — confirm the popover shows the itemized breakdown next to the icon, that click-outside / Esc / re-click close it, and that switching seasons hides it. Also `node --check web/app.js`.

- [ ] **Step 6: Commit**

```bash
git add web/app.js web/index.html web/styles.css
git commit -m "feat(web): open a points-breakdown popover from the leaderboard '?' button"
```

---

## Task 5: Full verification

- [ ] **Step 1:** `node --test tests/web/*.test.mjs` → all pass.
- [ ] **Step 2:** No commit (verification).

---

## Notes for delivery

- Delivered as a pull request from the `points-breakdown` branch. No backend/schema/workflow change.

## Self-Review Notes

- **Spec coverage:** breakdown data with itemized components incl. omission of zero + off-summer ×3 (Task 2), `.why` button + `renderBreakdown` (Task 3), anchored popover with dismissal (Task 4), styling (Task 4), tests (Tasks 2,3) + manual interaction check (Task 4). All spec sections map to tasks.
- **Placeholder scan:** none; full code and concrete expected values throughout.
- **Type consistency:** `tournamentScores` returns `{score, isLeague, breakdown:{tournament,date,items,subtotal}}`; `seasonLeaderboard` rows are `{name, points, events, breakdown:[…]}`; `renderLeaderboard` reads `row.points`/`index`; `renderBreakdown` reads `row.{name,points,breakdown[].{tournament,date,items[].{label,points},subtotal}}` — all consistent. `score` still equals the item sum so existing point-value tests are unaffected.
