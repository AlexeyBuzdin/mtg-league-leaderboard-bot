# Player Achievements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `achievements` table (label linked to a `player_key`), read it live, and render an Achievements badge section on the player profile just before Placements.

**Architecture:** New Supabase table with a public-read RLS policy. A pure `achievementsByName` join in `site-data.js` turns achievements (by key) into a `name → [labels]` map; `loadSiteData` returns it; `app.js`/`account-view.js` pass the current player's labels into `renderProfile`, which renders a badge section before Placements.

**Tech Stack:** Vanilla ES modules, Node `node --test`, Supabase (Postgres + RLS).

---

## File Structure

- `supabase/schema.sql` — add the `achievements` table + RLS policy.
- `web/lib/site-data.js` — add pure `achievementsByName(achievements, results, players)`.
- `web/lib/supabase-data.js` — `loadSiteData` also fetches `achievements` and returns the `name → [labels]` map.
- `web/ui/profile-view.js` — render the Achievements section before Placements.
- `web/app.js` — thread `state.achievements` into `renderProfile` (profile + account paths).
- `web/ui/account-view.js` — pass achievements into the embedded profile's options.
- `web/styles.css` — `.achievements` / `.achievement` pill styles.
- Tests: `tests/web/site-data.test.mjs`, `tests/web/supabase-data.test.mjs`, `tests/web/profile-view.test.mjs`.

**Environment (executor):** Node is not on PATH; before any node command run:
`export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`.
Git identity is configured; LF/CRLF warnings are harmless; files are UTF-8 (emoji must be preserved). Applying the table to the live DB and seeding the row are controller actions, NOT part of this plan.

---

## Task 1: Schema

**Files:** Modify `supabase/schema.sql`

- [ ] **Step 1: Append the table** to the end of `supabase/schema.sql`:
```sql

-- Player achievements: short badge labels (emoji + text) shown on the profile.
-- Linked by player_key (no FK, so legacy players off the is_league roster qualify).
create table if not exists achievements (
  id         bigint generated always as identity primary key,
  player_key text not null,
  label      text not null,
  created_at timestamptz not null default now(),
  unique (player_key, label)
);
create index if not exists achievements_player_key_idx on achievements (player_key);

alter table achievements enable row level security;
drop policy if exists "public read achievements" on achievements;
create policy "public read achievements" on achievements
  for select to anon, authenticated using (true);
```

- [ ] **Step 2: Commit**
```bash
git add supabase/schema.sql
git commit -m "feat(db): add achievements table with public-read RLS"
```

---

## Task 2: `achievementsByName` pure helper

**Files:** Modify `web/lib/site-data.js`; Test `tests/web/site-data.test.mjs`

- [ ] **Step 1: Write the failing test (append to `tests/web/site-data.test.mjs`)**
```js
import { achievementsByName } from '../../web/lib/site-data.js';

test('achievementsByName maps labels onto every name sharing the key', () => {
  const achievements = [
    { player_key: 'marcis k', label: '🏆Summer 2026' },
    { player_key: 'marcis k', label: '🥈Spring 2026' },
  ];
  const results = [
    { player_name: 'Marcis K', player_key: 'marcis k' },
    { player_name: 'Other P', player_key: 'other p' },
  ];
  const players = [{ player_key: 'marcis k', display_name: 'Marcis K' }];
  const map = achievementsByName(achievements, results, players);
  assert.deepEqual(map.get('Marcis K'), ['🏆Summer 2026', '🥈Spring 2026']);
  assert.equal(map.has('Other P'), false);
});

test('achievementsByName ignores achievements whose key has no name', () => {
  const map = achievementsByName(
    [{ player_key: 'ghost', label: 'x' }], [], [],
  );
  assert.equal(map.size, 0);
});
```

- [ ] **Step 2: Run (red)** — `node --test tests/web/site-data.test.mjs` → FAIL (`achievementsByName` not exported).

- [ ] **Step 3: Implement — append to `web/lib/site-data.js`:**
```js
export function achievementsByName(achievements, results, players) {
  const byKey = new Map();
  for (const a of achievements) {
    if (!byKey.has(a.player_key)) byKey.set(a.player_key, []);
    byKey.get(a.player_key).push(a.label);
  }
  const byName = new Map();
  const attach = (name, key) => {
    if (name == null) return;
    const labels = byKey.get(key);
    if (labels) byName.set(name, labels);
  };
  for (const r of results) attach(r.player_name, r.player_key);
  for (const p of players) attach(p.display_name, p.player_key);
  return byName;
}
```

- [ ] **Step 4: Run (green)** — `node --test tests/web/site-data.test.mjs` → PASS.

- [ ] **Step 5: Commit**
```bash
git add web/lib/site-data.js tests/web/site-data.test.mjs
git commit -m "feat(web): add achievementsByName join helper"
```

---

## Task 3: Fetch achievements in `loadSiteData`

**Files:** Modify `web/lib/supabase-data.js`; Test `tests/web/supabase-data.test.mjs`

- [ ] **Step 1: Write the failing test (append to `tests/web/supabase-data.test.mjs`)**
```js
test('loadSiteData returns achievements mapped by name', async () => {
  const client = new FakeClient({
    tournaments: [{ id: 1, name: 'A', event_date: '2026-07-06' }],
    round_results: [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)],
    players: [{ player_key: 'ann', display_name: 'Ann', is_league: true }],
    achievements: [{ player_key: 'ann', label: '🏆Summer 2026' }],
  });
  const data = await loadSiteData(client);
  assert.deepEqual(data.achievements.get('Ann'), ['🏆Summer 2026']);
});
```

- [ ] **Step 2: Run (red)** — `node --test tests/web/supabase-data.test.mjs` → FAIL (`data.achievements` undefined → `.get` throws).

- [ ] **Step 3: Implement** in `web/lib/supabase-data.js`:
  - Update the import: `import { buildSiteData, achievementsByName } from './site-data.js';`
  - Add a columns constant near the others: `const ACHIEVEMENT_COLS = 'player_key, label';`
  - In `loadSiteData`, add the fourth fetch and return the map:
```js
export async function loadSiteData(client) {
  const [tournaments, results, players, achievements] = await Promise.all([
    fetchAll(client, 'tournaments', TOURNAMENT_COLS),
    fetchAll(client, 'round_results', RESULT_COLS),
    fetchAll(client, 'players', PLAYER_COLS),
    fetchAll(client, 'achievements', ACHIEVEMENT_COLS),
  ]);
  const leagueKeys = new Set(
    players.filter(p => p.is_league).map(p => p.player_key),
  );
  return {
    ...buildSiteData(tournaments, results, leagueKeys),
    players,
    achievements: achievementsByName(achievements, results, players),
  };
}
```
  (The existing tests build a `FakeClient` without an `achievements` table; `this.tables['achievements'] ?? []` returns `[]`, so `data.achievements` is an empty Map and those tests still pass.)

- [ ] **Step 4: Run (green)** — `node --test tests/web/supabase-data.test.mjs` → PASS (all, incl. existing).

- [ ] **Step 5: Commit**
```bash
git add web/lib/supabase-data.js tests/web/supabase-data.test.mjs
git commit -m "feat(web): load achievements in loadSiteData"
```

---

## Task 4: Render achievements before Placements

**Files:** Modify `web/ui/profile-view.js`; Test `tests/web/profile-view.test.mjs`

- [ ] **Step 1: Write the failing test (append to `tests/web/profile-view.test.mjs`)**
```js
test('renders achievements as badges before placements when present', () => {
  const html = renderProfile('Ann', profile, [], 'all', {
    achievements: ['🏆Summer 2026', '🥈Spring 2026'],
  });
  assert.match(html, /class="profile-section">Achievements</);
  assert.match(html, /class="achievement">🏆Summer 2026</);
  assert.ok(html.indexOf('Achievements') < html.indexOf('Placements'));
  assert.ok(html.indexOf('🏆Summer 2026') < html.indexOf('Placements'));
});

test('omits the achievements section when there are none', () => {
  const html = renderProfile('Ann', profile);
  assert.ok(!html.includes('Achievements'));
});
```

- [ ] **Step 2: Run (red)** — `node --test tests/web/profile-view.test.mjs` → FAIL (no Achievements section).

- [ ] **Step 3: Implement** in `web/ui/profile-view.js`:
  - Add `achievements = []` to the options destructure at the top of `renderProfile`:
    change `const { showBack = true } = options;` to
    `const { showBack = true, achievements = [] } = options;`
  - Build the section (place this next to where `placements` is built, before the `return`):
```js
  const achievementsSection = achievements.length
    ? '<h2 class="profile-section">Achievements</h2>' +
      '<div class="achievements">' +
      achievements.map(a => `<span class="achievement">${a}</span>`).join('') +
      '</div>'
    : '';
```
  - In the final `return`, insert `achievementsSection` immediately before `placements`:
    `return back + header + summary + achievementsSection + placements + decks + rivals + friends;`

- [ ] **Step 4: Run (green)** — `node --test tests/web/profile-view.test.mjs` → PASS.

- [ ] **Step 5: Commit**
```bash
git add web/ui/profile-view.js tests/web/profile-view.test.mjs
git commit -m "feat(web): show achievements section before placements"
```

---

## Task 5: Wire app.js + account-view + styles

**Files:** Modify `web/app.js`, `web/ui/account-view.js`, `web/styles.css`

- [ ] **Step 1: `web/app.js` — hold achievements in state and pass them through**
  - Initial state: change `const state = { tournaments: [] };` (the initial state object near the top) to include `achievements`: `const state = { tournaments: [], achievements: new Map() };` (keep any other existing fields — only add `achievements: new Map()`).
  - After BOTH `const data = await loadSiteData(client);` blocks (the boot path and the deck-save refresh), add alongside the existing assignments:
    `state.achievements = data.achievements;`
  - In `renderProfileFor(name, season)`, pass achievements as the 5th argument:
```js
    profileView.innerHTML = renderProfile(
      name, playerProfile(tournaments, name), seasonsForPlayer(name), season,
      { achievements: state.achievements.get(name) ?? [] },
    );
```
  - In `linkedFor(season)`, add `achievements` to the returned object:
```js
    return {
      name, profile: playerProfile(tournaments, name),
      seasons: seasonsForPlayer(name), selectedSeason: season,
      achievements: state.achievements.get(name) ?? [],
    };
```

- [ ] **Step 2: `web/ui/account-view.js` — pass achievements into the embedded profile**
  Change the embedded `renderProfile` call to include achievements in its options:
```js
      renderProfile(linked.name, linked.profile, linked.seasons, linked.selectedSeason,
        { showBack: false, achievements: linked.achievements ?? [] }) +
```

- [ ] **Step 3: `web/styles.css` — add pill styles** (append near the `.placements` rules):
```css
.achievements { display: flex; flex-wrap: wrap; gap: 8px; }
.achievement {
  font-size: 14px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  white-space: nowrap;
}
```
  (If `--surface` is not a defined token in this file, use the same background token the `.placement` rule uses — check lines ~276–286 — so the pill matches existing surfaces.)

- [ ] **Step 4: Verify**
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --check web/app.js && node --check web/ui/account-view.js
node --test tests/web/*.test.mjs
```
Expected: `node --check` clean; the full web suite passes (no regressions).

- [ ] **Step 5: Commit**
```bash
git add web/app.js web/ui/account-view.js web/styles.css
git commit -m "feat(web): thread achievements into profile and account views"
```

---

## Controller actions (outside this plan, approval-gated)

1. Apply the `achievements` table to the live Supabase DB (same SQL as Task 1).
2. Confirm Mārcis's exact `player_key`, then seed:
   `insert into achievements (player_key, label) values ('<key>', '🏆Summer 2026') on conflict (player_key, label) do nothing;`
3. Open the PR.

---

## Self-Review Notes

- **Spec coverage:** table + RLS (Task 1); live fetch + name join (Tasks 2–3); render before Placements, hidden when empty, badges (Task 4); profile + account wiring + CSS (Task 5); seed + live apply (Controller actions). All spec items map.
- **Placeholder scan:** none; full code in every step. The `<key>` in controller step 2 is a confirm-at-runtime value, intentionally not hardcoded.
- **Type consistency:** `achievementsByName(achievements, results, players) -> Map<name,[labels]>` is produced in Task 2, returned by `loadSiteData` (Task 3), stored as `state.achievements` and read via `.get(name) ?? []` (Task 5), and consumed as `options.achievements` (array) by `renderProfile` (Task 4). `renderProfile`'s existing signature and the `account-view` call site match.
- **Known limitation:** achievements are global (not season-filtered) but render in the main profile path, so a player viewed in a season with zero tournaments won't show them until the Overall view. Acceptable for this scope.
