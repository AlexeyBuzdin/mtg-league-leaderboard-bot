# GitHub Pages UI Prototype — Design

**Date:** 2026-07-31
**Status:** Approved (pending spec review)

## Summary

A static, no-build GitHub Pages site that displays the league's tournament data
in the **new round-by-round structure**, using **mock data only** (no Supabase
integration yet). Two views: a **quarterly leaderboard** and a **tournament
detail** view showing rounds and pairings.

The mock data mirrors the shape of the planned `tournaments` + `round_results`
database so the prototype can later be pointed at real data with minimal change.

## Goals

- Show a **quarterly leaderboard**: players ranked by total points in a selected
  calendar quarter, with events played.
- Show **tournament detail**: rounds top-to-bottom, each pairing with both
  players' cumulative W–D–L, the game score, and the winner marked.
- Ship as a **vanilla static site** (HTML/CSS/JS, no build step) deployable to
  GitHub Pages.
- Keep the point/leaderboard logic in **pure, unit-tested functions**.

## Non-goals

- No Supabase or network integration (data is a local mock JSON file).
- No build tooling, framework, or bundler.
- No authentication, write actions, or admin UI.
- No player-profile or tournament-list views (explicitly out of scope for the
  prototype).

## Decisions (from brainstorming)

- **Views:** quarterly leaderboard + tournament detail.
- **Stack:** vanilla static (no build).
- **Navigation:** two-view nav; a **quarter selector** on the leaderboard and a
  **tournament selector** (by date) on the detail view.
- **Quarter:** calendar quarter (Q1 Jan–Mar, Q2 Apr–Jun, Q3 Jul–Sep, Q4 Oct–Dec).
- **Points:** `3·wins + 1·draws`, computed from each player's **final-round**
  cumulative record (matches the bot's scoring).
- **Tie-break:** points descending, then display name alphabetically.
- **Theme:** light/dark aware.

## Mock data shape

A single JSON file fetched at runtime, mirroring the new DB structure. A `null`
`player2` represents a **bye** (a pairing with one player).

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
            {
              "pairing": 1,
              "player1": { "name": "Raitis Ozols", "game_wins": 2,
                           "record": { "wins": 1, "draws": 0, "losses": 0 } },
              "player2": { "name": "Nikita Petrov", "game_wins": 1,
                           "record": { "wins": 0, "draws": 0, "losses": 1 } }
            },
            {
              "pairing": 2,
              "player1": { "name": "Mārtiņš Kalniņš", "game_wins": 2,
                           "record": { "wins": 1, "draws": 0, "losses": 0 } },
              "player2": null
            }
          ]
        }
      ]
    }
  ]
}
```

The mock file will contain at least **three tournaments across two quarters**
(so the quarter selector changes results), one tournament with **multiple
rounds**, and at least one **bye**, plus a name with **diacritics** (to exercise
Unicode handling in display).

## Derived logic (pure functions)

- **`finalRecords(tournament)`** → `{ [playerName]: record }`. Walks every round
  and pairing, keeping the last record seen per player (records are cumulative,
  so the last is the final). Byes (`player2 === null`) contribute only player1.
- **`points(record)`** → `record.wins * 3 + record.draws`.
- **`quarterOf(dateString)`** → `{ year, quarter }` from a `YYYY-MM-DD` string.
- **`quarterKey(dateString)`** → e.g. `"2026-Q3"`.
- **`quarterLeaderboard(tournaments, quarterKey)`** → array of
  `{ name, points, events }`, summing each player's per-tournament points over
  all tournaments in that quarter and counting tournaments as events, sorted by
  points desc then name asc.

These functions take plain data and return plain data — no DOM, no fetch — so
they are unit-tested directly.

## Views & components

**Leaderboard view (default):**
- Quarter `<select>` populated from the quarters present in the data (newest
  first); a small meta line (`N tournaments · M players`).
- A table: rank, player (initials avatar + name), events, points. Ranks 1–3 get
  a subtle tint.

**Tournament detail view:**
- Tournament `<select>` listing `date — name`, newest first.
- Header (name, date, round count), then each round as a labelled section; each
  pairing is a row: player1 (+W–D–L chip) · game score · player2 (+W–D–L chip),
  with a check on the winner. Byes render as a single-player row labelled "Bye".

**Shell:** a two-button nav (Leaderboard / Tournament) toggling the visible view.

## File structure

```
web/
├── index.html            # shell: header, nav, two view containers
├── styles.css            # theme-aware styles (light/dark via prefers-color-scheme)
├── app.js                # entry: fetch data, wire nav + selectors, render
├── lib/
│   ├── quarter.js        # quarterOf, quarterKey  (pure)
│   └── leaderboard.js    # finalRecords, points, quarterLeaderboard  (pure)
├── ui/
│   ├── leaderboard-view.js   # renders the leaderboard table from computed rows
│   └── tournament-view.js    # renders rounds/pairings for a tournament
└── data/
    └── mock-tournaments.json # the mock dataset
tests/
└── web/
    ├── quarter.test.js       # node:test unit tests for lib/quarter.js
    └── leaderboard.test.js   # node:test unit tests for lib/leaderboard.js
.github/workflows/
└── pages.yml             # build-free deploy of web/ to GitHub Pages
```

JS uses native ES modules (`<script type="module">`), so `lib/` and `ui/` import
cleanly in both the browser and Node's test runner. No transpilation.

## Data flow

1. `app.js` fetches `data/mock-tournaments.json`.
2. On load and on quarter change, it calls `quarterLeaderboard(...)` and hands
   the rows to `leaderboard-view` to render.
3. On tournament change, it passes the selected tournament to `tournament-view`.
4. Nav buttons toggle which container is visible. All rendering is client-side;
   there is no server.

## Error handling

Minimal, appropriate to a static prototype:
- If the data fetch fails, show a single inline message ("Couldn't load data").
- If a selected quarter has no players, the leaderboard shows an empty-state row.
- Pure functions assume well-formed mock data (the mock file is the contract);
  no defensive parsing of arbitrary input is needed.

## Testing

- **Unit (automated):** `node --test` over `tests/web/*.test.js` covering
  `quarter.js` (quarter boundaries, keys) and `leaderboard.js` (final-record
  extraction incl. byes, points formula, aggregation, tie-break ordering).
  No dependencies — Node's built-in test runner imports the ES modules directly.
- **Visual (manual):** open the deployed Pages URL (or `web/index.html` via a
  local static server) and exercise both selectors and the nav.

## Deployment

- `pages.yml` runs on push to `main` (and `workflow_dispatch`): uploads the
  `web/` directory with `actions/upload-pages-artifact` and publishes via
  `actions/deploy-pages`. No build step.
- One-time: enable GitHub Pages with **source = GitHub Actions** in repo
  settings.

## Delivery

Implemented on a dedicated worktree/branch and delivered as a **pull request**
(not merged directly), per the user's request.

## Future integration (noted, not built)

Swapping the mock for real data means replacing the single fetch of
`data/mock-tournaments.json` with a fetch of the same JSON shape from Supabase
(or a small API), plus using a **rolling/real** current quarter. The pure
`lib/` functions and the views remain unchanged.
