# Legacy Standings Import & Rendering — Design

**Date:** 2026-08-02
**Status:** Approved (pending spec review)

## Summary

Populate the Supabase database with **legacy tournament results** (the old
standings-only format), and render those events in the front-end as a **flat
standings table** (the legacy data has no pairing/round detail to show).

Two parts:
1. A **one-off data load** of the pasted legacy dump into `tournaments` +
   `round_results`, via the Supabase API.
2. A small **front-end change** so a legacy (standings-only) event renders as a
   ranked standings table instead of pairing rows. The quarterly leaderboard
   needs no change — it already counts these players.

## Goals

- Get real June/July 2026 results into the DB so the quarterly leaderboard shows
  real players and points.
- Render legacy events with a sensible detail view (standings table).
- No schema change; reuse the existing `round_results` table.

## Non-goals

- No reusable importer command (this is a one-off load).
- No deck storage (the schema has no deck column; legacy decks are dropped).
- No change to the ingest bot or the new-format pipeline.

## Decisions (from brainstorming)

- **Legacy detail view:** flat standings list (rank · player · record · points).
- **Load mechanism:** one-off SQL via the Supabase API (not a committed
  importer).
- **Representation:** legacy rows live in `round_results` with null opponents;
  that null-opponent state marks a standings-only event.
- **Record order:** legacy record column is **W/L/D** (wins/losses/draws).

## Data representation & mapping

**Per legacy event → one `tournaments` row:**
- `name`: header name, whitespace-collapsed (e.g. `Monday Standard Showdown`).
- `event_date`: parsed from the header, normalizing `dd.mm.yyyy`, `dd.mm.yy`
  (`13.07.26` → `2026-07-13`), and `d.mm.yyyy` (`8.06.2026` → `2026-06-08`).
- `discord_message_id`: synthetic `legacy-<event_date>` (e.g.
  `legacy-2026-06-01`) — satisfies NOT NULL / UNIQUE and makes re-loading
  idempotent (`ON CONFLICT (discord_message_id) DO NOTHING`).
- `channel_id`: `"legacy"`.

**Per standings row → one `round_results` row:**
- `round = 1`, `pairing = <standing>` (rank preserved in `pairing`).
- `player_name` as printed; `player_key = " ".join(name.split()).casefold()`
  (the bot's `normalize_name`, so legacy and future players merge).
- `opponent_name = opponent_key = game_wins = opponent_game_wins = NULL` — the
  **null-opponent marker** identifying a standings-only event.
- **Record mapping (W/L/D):** `record_wins = col1`, `record_losses = col2`,
  `record_draws = col3`. Reproduces points exactly (`3·wins + draws`):
  `3/0/0 → 9`, `2/0/1 → 7`, `2/1/0 → 6`, `1/1/1 → 4`, `0/2/1 → 1`.

Dropped: deck names (no column; not shown in the standings view). Possible
future work.

## The one-off load

1. **Parse** the 8 events with old-standings-format logic: header →
   `(name, date)`; each row → `standing, name, points, W/L/D` (deck ignored).
   Non-matching lines are skipped and reported (nothing silently dropped).
2. **Generate SQL**: per event, a CTE that inserts the `tournaments` row
   `RETURNING id` and inserts its `round_results` rows referencing that id, all
   in one transaction.
3. **Idempotent**: `INSERT INTO tournaments … ON CONFLICT (discord_message_id)
   DO NOTHING`; only insert `round_results` for events that were actually
   inserted — re-running is safe.
4. **Approval gate**: show the parsed summary (event count, per-event player
   counts, a couple of computed-points spot-checks) and the exact SQL; run
   against the live `league-binder` DB only on an explicit go.
5. **Verify**: re-query row counts (8 tournaments, total players) and one
   event's standings after the load.

## Front-end standings rendering

Only `web/ui/tournament-view.js` changes; `app.js` and the leaderboard logic are
untouched.

- **Detect a standings event:** every pairing across all rounds has
  `player2 === null`. A real pairing event always has at least one two-player
  pairing, so this is unambiguous.
- **Render a standings table:** columns **rank · player · record · points**,
  sorted by rank (`pairing`); `record` shown `W-D-L` from `player1.record`;
  `points = 3·wins + draws`.
- Real (pairing) events render exactly as before (unchanged path).

**Why the leaderboard is unaffected:** the export emits each legacy player as a
single-player ("bye") pairing, and the existing `finalRecords` counts a bye's
player — so legacy players already contribute correct points to
`quarterLeaderboard`.

## Testing & verification

- **Front-end (`node --test`):** the new renderer — a standings event renders a
  table with correct ranks, records, and derived points; a normal pairing event
  still renders pairings; standings sorted by rank.
- **Load verification:** post-load Supabase queries for counts and one event's
  standings, spot-checking computed points against the source dump.
- **End-to-end:** after the `SUPABASE_URL` secret is corrected and the site
  redeploys, the quarterly leaderboard shows real June/July players and a legacy
  event opens as a standings table.

## Files changed / delivery

- **Data load:** executed via the Supabase API (no committed code) — a separate,
  approval-gated action.
- **Front-end:** `web/ui/tournament-view.js` + `tests/web/tournament-view.test.mjs`
  (and any small helper), delivered as a **PR** from the `legacy-standings`
  branch.

## Dependency / note

- The site will only display this data once the separate `SUPABASE_URL` secret
  issue is fixed (the deploy currently fails on a malformed URL secret). The data
  load itself is independent of that.
