# League Player Flag — Design

**Date:** 2026-08-02
**Status:** Approved (pending spec review)

## Summary

Add a per-player **`is_league`** flag so non-league players (guests, drop-ins)
are hidden from the leaderboards — on both the GitHub Pages website and the
Discord monthly post — while remaining visible in the tournament-detail view
(they were real opponents). The flag is stored in a new Supabase `players`
table, defaults to **hidden** (approve-in), and is maintained by an admin
editing the table.

## Goals

- Hide non-league players from the **quarterly website leaderboard** and the
  **Discord monthly leaderboard**.
- Keep non-league players in the **tournament-detail** view (pairings stay
  intact).
- Make the roster editable without a code change or redeploy.
- Seed the current 25 known players (21 league, 4 non-league) so the effect is
  immediate.

## Non-goals

- No admin UI (the Supabase table editor is the admin surface).
- No removal of non-league players from `round_results` (their match rows stay).
- No changes to how tournaments/results are ingested or parsed, beyond
  recording players.

## Decisions (from brainstorming)

- **Storage:** a new `players` table.
- **Default:** `is_league=false` (approve-in — new players are hidden until
  promoted).
- **Hide scope:** leaderboards only; tournament detail shows everyone.
- **Surfaces:** both website and Discord.
- **Web mechanism:** each player object in the exported JSON carries `is_league`;
  the web leaderboard filters on it (tournament detail ignores it).

## Data model

```sql
create table players (
  player_key   text primary key,                -- normalized name; matches round_results.player_key
  display_name text,                              -- admin readability
  is_league    boolean not null default false,   -- approve-in: hidden until promoted
  created_at   timestamptz not null default now()
);
```

Added to `supabase/schema.sql`. `player_key` is the same normalized key used in
`round_results` (lowercased, collapsed whitespace).

## Data flow

```
ingest ──upsert new player_keys (default is_league=false)──► players
                                                                │
Discord leaderboard (bot) ──filter results to is_league=true───┘
                                                                │
export ──read league keys, tag each JSON player is_league──► web/data/tournaments.json
                                                                │
web leaderboard ──skip is_league=false──►  (tournament detail shows everyone)
```

## Backend (`bot`)

- **`store.upsert_players(players)`** — inserts `{player_key, display_name}` rows
  via supabase-py `upsert(rows, on_conflict="player_key", ignore_duplicates=True)`
  (i.e. `INSERT … ON CONFLICT (player_key) DO NOTHING`), so re-seeing a player
  never overwrites an admin's `is_league` decision.
- **`store.fetch_league_keys()`** — `select player_key from players where
  is_league = true` → `set[str]`. Shared by the Discord leaderboard and the
  export.
- **`ingest.run(...)`** — after `insert_tournament`, collect the distinct
  `(player_key, player_name)` from the parsed rounds (covers opponents too, since
  each player has their own row) and call `store.upsert_players(...)`. New faces
  land as `is_league=false`.
- **`leaderboard.run(...)`** (Discord) — fetch `league_keys` and drop rows whose
  `player_key` is not in the set before aggregating. `store.fetch_results_in_window`
  is unchanged; the filter is one explicit, unit-testable line in `leaderboard.run`.

## Export (`bot/export.py`)

- **`_fetch`** also reads `players` (`player_key, is_league`) and returns
  `league_keys = {p.player_key for p in players if p.is_league}`.
- **`build_site_data(tournaments, results, league_keys)`** — `_player_obj` gains
  `"is_league": row["player_key"] in league_keys`. Every `player1`/`player2`
  object in the JSON carries the flag; a player absent from `players` → `false`.
- `build_site_data` stays pure (three plain inputs), still unit-tested without a
  DB.

## Front-end (`web/lib/leaderboard.js` + seed)

- **`quarterLeaderboard`** skips player objects whose `is_league` is `false` when
  building the ranking. `finalRecords` carries `is_league` alongside the record.
- **Backward-safe:** a **missing** `is_league` is treated as `true` in the web
  filter, so the committed seed `tournaments.json` and any legacy data still show
  everyone rather than emptying the board. The live export always sets the flag.
- **Tournament detail is unchanged** — it renders all players regardless of the
  flag.
- **Seed data:** add `"is_league": true` to the sample player objects plus one
  sample non-league player (`is_league: false`) so the seed exercises the filter.

## Seeding the live database

Apply the `players` table to the live Supabase project and seed from existing
data (idempotent):

```sql
insert into players (player_key, display_name, is_league)
select distinct player_key, player_name,
       player_key not in ('aivars l','jevgenijs k','paul m','rolands s')
from round_results
on conflict (player_key) do nothing;
```

This inserts the 25 current players with the 4 non-league ones flagged `false`,
making them drop off the leaderboard on the next export/deploy. Applied via the
Supabase tooling during implementation; flags are trivially editable afterward.

## Testing

- **Python (pytest):**
  - `upsert_players` uses ignore-duplicates (existing rows untouched).
  - `fetch_league_keys` returns only league keys.
  - `leaderboard.run` excludes non-league players from the Discord aggregation.
  - `build_site_data` attaches `is_league` per player (true for league keys,
    false otherwise).
  - `ingest.run` upserts the players it saw.
- **Web (`node --test`):**
  - `quarterLeaderboard` drops non-league players from the ranking.
  - a missing `is_league` is treated as league (seed/back-compat).
  - tournament-detail rendering is unaffected by the flag.

## Deployment

No workflow changes. `pages.yml` already runs the export; the ingest/leaderboard
crons already exist. Once the table is seeded and the branch merges:
- the next export/deploy hides the 4 non-league players on the website;
- the next monthly Discord post excludes them.

## Files changed

- `supabase/schema.sql` — add `players` table.
- `bot/store.py` — `upsert_players`, `fetch_league_keys`.
- `bot/ingest.py` — upsert players after insert.
- `bot/leaderboard.py` — filter results by league keys.
- `bot/export.py` — fetch players, tag `is_league` in `build_site_data`.
- `web/lib/leaderboard.js` — filter non-league from the ranking.
- `web/data/tournaments.json` — add `is_league` to seed players (+ one non-league).
- Tests: `tests/test_store.py`, `tests/test_leaderboard.py`, `tests/test_export.py`,
  `tests/test_ingest.py`, `tests/web/leaderboard.test.mjs`, seed-shape test.
- Live Supabase: create + seed `players` (applied via tooling, not a repo change).

## Delivery

A pull request from the `league-flag` worktree/branch.
