# MTG League Leaderboard Bot — Design

**Date:** 2026-07-11
**Status:** Approved (pending spec review)

## Summary

A Discord bot for the MTG Latvia server that ingests Magic: The Gathering
tournament results posted in a Discord channel, stores them in Supabase, and
posts a monthly leaderboard (sum of points per attendee) on a weekly basis.

It runs as two stateless GitHub Actions cron jobs — nothing runs persistently.
Because a scheduled job cannot "subscribe" to a channel in real time, the daily
job **polls** the channel via the Discord REST API and processes anything new.

## Goals

1. Daily: read recent messages from the results channel, detect tournament
   results messages, parse the standings, and store them in Supabase.
2. Weekly: post a rich embed leaderboard summing points per attendee for the
   current calendar month, to a separate leaderboard channel.

## Non-goals

- Real-time/gateway bot behavior.
- Player identity resolution beyond normalized-name matching.
- Historical backfill tooling (recent-message polling self-heals missed runs
  within the fetch window).

## Decisions (from brainstorming)

- **Stack:** Python.
- **Discord access:** raw REST API (no `discord.py` gateway), one-shot CLI.
- **Player identity:** normalized name (lowercase + trim + collapse internal
  whitespace). Display name = spelling from the most recent tournament.
- **Dedup:** by Discord message ID (unique constraint on `tournaments`).
- **Header matching:** fixed allow-list of tournament names (case-insensitive),
  configured via env var.
- **Post target:** a separate, configurable leaderboard channel.
- **Month window:** current calendar month to date.
- **Leaderboard format:** rich Discord embed listing every attendee.
- **Timezone:** `Europe/Riga` (configurable) for month-boundary bucketing.

## Architecture

Two stateless entry points, run by two GitHub Actions cron workflows, sharing
one small Python package.

```
mtg-league-leaderboard-bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # CLI: `python -m bot ingest` / `python -m bot leaderboard`
│   ├── config.py            # loads/validates env vars; holds allow-list of tournament names
│   ├── discord_client.py    # thin REST wrapper: fetch channel messages, post message/embed
│   ├── parser.py            # PURE functions: header match + standings-row parsing (no I/O)
│   ├── store.py             # Supabase read/write (insert results, query monthly totals)
│   ├── ingest.py            # orchestrates: fetch → filter → parse → dedup → store
│   └── leaderboard.py       # orchestrates: query month totals → build embed → post
├── tests/
│   ├── test_parser.py       # bulk of tests — real message samples → expected rows
│   ├── test_leaderboard.py  # totals aggregation + embed formatting
│   └── fixtures/            # sample Discord message payloads
├── supabase/
│   └── schema.sql           # table definitions (also applied via Supabase)
├── .github/workflows/
│   ├── ingest.yml           # daily cron → `python -m bot ingest`
│   └── leaderboard.yml      # weekly cron → `python -m bot leaderboard`
├── pyproject.toml           # deps: httpx, supabase, (dev) pytest
├── .env.example
└── README.md
```

**Key boundary:** `parser.py` is pure (string in → structured data out, no
network/DB). That is where the parsing risk lives, so it is isolated and fully
unit-tested. `discord_client.py` and `store.py` are thin I/O adapters.
`ingest.py` / `leaderboard.py` wire them together.

## Data model (Supabase / Postgres)

```sql
-- One row per parsed results message
create table tournaments (
  id                  bigint generated always as identity primary key,
  discord_message_id  text not null unique,   -- idempotency key
  name                text not null,          -- e.g. "Monday Standard Showdown"
  event_date          date not null,          -- parsed from (dd.mm.yyyy)
  channel_id          text not null,
  ingested_at         timestamptz not null default now()
);

-- One row per player line in a tournament
create table results (
  id              bigint generated always as identity primary key,
  tournament_id   bigint not null references tournaments(id) on delete cascade,
  standing        int  not null,
  player_name     text not null,              -- as printed, e.g. "James Smith"
  player_key      text not null,              -- normalized: lower + trim + collapse spaces
  points          int  not null,
  wins            int  not null,
  draws           int  not null,
  losses          int  not null,
  deck            text,                        -- nullable (optional column)
  unique (tournament_id, standing)
);

create index results_player_key_idx on results (player_key);
create index tournaments_event_date_idx on tournaments (event_date);
```

- `discord_message_id unique` → re-running the daily ingest is a no-op for
  already-seen messages.
- `player_key` (normalized name) is what the monthly leaderboard groups by;
  `player_name` keeps the nicest-looking display version.
- W/D/L stored as three ints (parsed from `3/0/0`).
- Monthly leaderboard = `sum(points)` from `results` joined to `tournaments`
  where `event_date` is in the current calendar month, grouped by `player_key`.
- `event_date` uses the tournament's printed date (not ingest time), so month
  bucketing reflects when the tournament actually happened.

## Ingest flow (daily)

1. `discord_client.fetch_messages(channel_id, limit=100)` — most recent ~100
   messages in one REST call (covers far more than a day; missed runs self-heal).
2. For each message, `parser.match_header(first_line)`:
   - Requires the header to end with `(dd.mm.yyyy) final standings:` **and** the
     tournament name to be in the configured allow-list (case-insensitive).
   - Returns `(name, event_date)` or `None`.
3. Skip messages whose `discord_message_id` is already in `tournaments`
   (batch-checked up front).
4. `parser.parse_standings(body)` → list of row dicts.
5. Insert one `tournaments` row + its `results` rows in a transaction. If a
   matched header yields **zero** parsed rows, log a warning and skip (do not
   insert an empty tournament).

### Header regex

```
^(?P<name>.+?)\s*\((?P<date>\d{2}\.\d{2}\.\d{4})\)\s*final standings:?\s*$
```

The captured `name` is then validated (case-insensitively) against the
`TOURNAMENT_NAMES` allow-list.

### Standings-row regex

Anchored on the rigid `points` + `W/D/L` structure so the variable-width,
multi-word name is unambiguous:

```
^\s*(?P<standing>\d+)\s+(?P<name>.+?)\s+(?P<points>\d+)\s+(?P<w>\d+)/(?P<d>\d+)/(?P<l>\d+)\b.*?(?:\((?P<deck>[^)]+)\)\s*)?$
```

- `name` is non-greedy, bounded on the right by ` <points> <w>/<d>/<l>`, so a
  two-word name and a one-word name both parse.
- Everything between W/D/L and the optional trailing `(deck)` (the three %
  columns) is swallowed by `.*?` and ignored.
- Non-matching lines (blank lines, header, stray text) are skipped silently but
  counted, so format drift is observable in logs.

### Worked example

Input:
```
Monday Standard Showdown (06.07.2026) final standings:

1    James Smith     9    3/0/0    44.3%    66.7%    45.9%     (Temur Harmonizer)
2    Nikita Powers    7    2/0/1    59.3%    71.4%    56.5%     (Jeskai Control)
3    Artur Brown    6    2/1/0    59.3%    62.5%    62.7%
```

Parsed:
- header → `name="Monday Standard Showdown", event_date=2026-07-06`
- row 1 → `standing=1, name="James Smith", points=9, w/d/l=3/0/0, deck="Temur Harmonizer"`
- row 2 → `standing=2, name="Nikita Powers", points=7, w/d/l=2/0/1, deck="Jeskai Control"`
- row 3 → `standing=3, name="Artur Brown", points=6, w/d/l=2/1/0, deck=None`

These exact lines become test fixtures.

### Known edge cases (accepted for now)

- Decks containing `)`, or names ending in a stray token, are rare; the anchored
  regex handles normal cases and unmatched lines are logged.
- A corrected **repost** (new message) of the same tournament creates a second
  `tournaments` row, since dedup is by message ID only. Accepted for now; a
  secondary `(name, event_date)` guard can be added later if it becomes a
  problem.

## Leaderboard flow (weekly)

1. Compute current calendar-month window `[first-of-month, now]` in `TIMEZONE`.
2. `store.monthly_totals()` → SQL summing `points` grouped by `player_key`,
   joined to `tournaments` where `event_date` is in the window; also returns the
   latest display name per key and count of events played.
3. Sort by points desc, ties broken alphabetically by display name.
4. Build a Discord **embed** listing **every** attendee: title like
   `🏆 Standard League — July 2026`, rows `1. James Smith — 22 pts (3 events)`.
   If the content would exceed Discord embed limits (~4096 chars / 25 fields),
   spill into multiple embeds / a continuation message.
5. `discord_client.post_embed(LEADERBOARD_CHANNEL_ID, embed)`.
6. If there are zero results for the month, skip silently (default).

## Scheduling (GitHub Actions cron, UTC)

- `ingest.yml` — daily, e.g. `0 21 * * *` (~midnight Riga) + `workflow_dispatch`.
- `leaderboard.yml` — weekly, Mondays `0 7 * * 1` (morning Riga) +
  `workflow_dispatch`.

## Configuration (GitHub Actions secrets → env vars)

- `DISCORD_BOT_TOKEN` — bot present in the server; read perms on results channel,
  send perms on leaderboard channel; **Message Content Intent** enabled.
- `RESULTS_CHANNEL_ID`, `LEADERBOARD_CHANNEL_ID`
- `SUPABASE_URL`, `SUPABASE_KEY` (service role)
- `TOURNAMENT_NAMES` — comma-separated allow-list
  (e.g. `Monday Standard Showdown,Standard Store Championship`)
- `TIMEZONE` — default `Europe/Riga`

`.env.example` documents all of them; `config.py` validates presence and fails
fast with a clear error.

## Testing

- `test_parser.py` — core coverage: real message samples (the examples above +
  crafted edge cases: no deck, multi-word names, blank lines, non-matching
  headers) → asserted structured output. Pure, fast, no mocks.
- `test_leaderboard.py` — aggregation math (sums, tie-break ordering, month
  window) and embed formatting against fixture rows.
- I/O adapters (`discord_client`, `store`) kept thin so most logic is tested
  without network/DB.
- README documents a live dry-run via `workflow_dispatch` for manual
  verification.

## One-time manual setup (documented in README)

- Create the Discord application/bot, enable **Message Content Intent**, invite
  it to the server, grant read/send perms on the relevant channels.
- Create the Supabase project and apply `supabase/schema.sql`.
- Add all secrets to the GitHub repository.
