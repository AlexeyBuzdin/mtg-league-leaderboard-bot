# Connect Front-End and Back-End — Design

**Date:** 2026-08-02
**Status:** Approved (pending spec review)

## Summary

Wire the static GitHub Pages site to the Supabase back-end via a **build-time
export**. A GitHub Action fetches tournament data from Supabase, reshapes it into
the front-end's JSON shape, and deploys it with the site — no client-side
Supabase access and no generated data committed to git.

## Goals

- Serve **real tournament data** on the Pages site instead of mock data.
- Keep all Supabase access **server-side** (in a GitHub Action), not in the
  browser.
- Reshape the player-centric `round_results` rows into the front-end's
  pairing-centric JSON in a **pure, unit-tested** function.
- Refresh the site automatically after new results are ingested.

## Non-goals

- No client-side/browser Supabase queries.
- No changes to the front-end rendering/logic (only its data source path).
- No new Supabase auth setup (reuse the bot's existing service_role secret).
- No committing of generated data to the repository.

## Decisions (from brainstorming)

- **Data → site:** generated at deploy time inside the Pages workflow; never
  committed.
- **Trigger:** `workflow_run` after the `ingest` workflow succeeds, plus
  `workflow_dispatch` and push to `web/**`.
- **Supabase auth:** reuse the existing `SUPABASE_URL` / `SUPABASE_KEY`
  (service_role) secrets.
- **Export logic:** a Python script (`bot/export.py`) reusing `supabase-py`,
  with a pure transform function.

## Architecture & data flow

```
 Discord ──► [ingest workflow] ──writes──► Supabase (tournaments, round_results)
                     │ on success (workflow_run)
                     ▼
        ┌──────────────────────────────────────────────┐
        │  pages workflow (also: workflow_dispatch,      │
        │                  push to web/**)               │
        │                                                │
        │  1. checkout                                   │
        │  2. setup Python + pip install -e .            │
        │  3. python -m bot.export --out \               │
        │        web/data/tournaments.json               │
        │       (env: SUPABASE_URL, SUPABASE_KEY)        │
        │  4. upload web/ artifact  →  5. deploy-pages   │
        └──────────────────────────────────────────────┘
                     ▼
        https://alexeybuzdin.github.io/…/  (real data)
```

- The export **overwrites `web/data/tournaments.json` in the build only**; it is
  never committed. A committed **seed** copy (the current sample data) keeps
  local dev and pre-data deploys working.
- The front-end changes exactly one thing: it fetches `data/tournaments.json`
  instead of `data/mock-tournaments.json`.

## Back-end shape (input)

- `tournaments`: `id` (bigint), `name` (nullable text), `event_date` (date),
  plus `discord_message_id`, `channel_id`, `ingested_at` (unused by the site).
- `round_results`: `tournament_id`, `round`, `pairing`, `player_name`,
  `player_key`, `opponent_name`, `opponent_key`, `game_wins`,
  `opponent_game_wins`, `record_wins`, `record_draws`, `record_losses`. One row
  per player per pairing (two rows per full pairing; one row for a bye, with
  `opponent_name` null).

## Front-end shape (output)

```json
{
  "tournaments": [
    {
      "id": "1",
      "name": "Standard Showdown",
      "date": "2026-07-06",
      "rounds": [
        {
          "round": 1,
          "pairings": [
            {
              "pairing": 1,
              "player1": { "name": "…", "game_wins": 2,
                           "record": { "wins": 1, "draws": 0, "losses": 0 } },
              "player2": { "name": "…", "game_wins": 1,
                           "record": { "wins": 0, "draws": 0, "losses": 1 } }
            }
          ]
        }
      ]
    }
  ]
}
```

## Export script (`bot/export.py`)

```
bot/export.py
├── build_site_data(tournaments, results) -> dict   # PURE — the tested core
└── main(argv)                                        # I/O: connect, fetch, write file
```

**`main(argv)`:**
- Reads `SUPABASE_URL` / `SUPABASE_KEY` **directly from the environment** (not
  the bot's `load_config`, which also requires Discord vars the export does not
  need). Exits non-zero with a clear message if either is missing.
- Two `supabase-py` queries: all rows from `tournaments`, all rows from
  `round_results`.
- Calls `build_site_data(...)`, writes JSON to `--out`
  (default `web/data/tournaments.json`), UTF-8, `ensure_ascii=False`.

**`build_site_data(tournaments, results)` — the reshape (pure):**
1. Group `results` by `tournament_id`, then `round`, then `pairing`.
2. For each pairing group (1 or 2 rows), each row self-describes its own player
   (so `opponent_*` fields are ignored):
   - `player = {name: r.player_name, game_wins: r.game_wins,
      record: {wins: r.record_wins, draws: r.record_draws, losses: r.record_losses}}`
   - **1 row → bye:** `player1 = player`, `player2 = null`.
   - **2 rows → full pairing:** sort the two by `player_key` for a deterministic
     `player1`/`player2` (the front-end derives the winner from `game_wins`, so
     the side assignment is cosmetic).
3. Assemble each tournament:
   `{id: str(id), name: name or "Tournament", date: event_date,
     rounds: [...]}`, rounds ascending by `round`, pairings ascending by
   `pairing`.
4. Return `{"tournaments": [...]}`, tournaments ordered by `date`.

This never trusts cross-row consistency, tolerates a bye as a single row, and
produces exactly the shape the front-end already consumes and tests.

## Workflow changes (`.github/workflows/pages.yml`)

```yaml
on:
  workflow_run:
    workflows: ["ingest"]
    types: [completed]
  workflow_dispatch:
  push:
    branches: [main]
    paths: ["web/**", "bot/export.py", ".github/workflows/pages.yml"]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency: { group: pages, cancel-in-progress: true }

jobs:
  deploy:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .
      - run: python -m bot.export --out web/data/tournaments.json
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: web }
      - id: deployment
        uses: actions/deploy-pages@v4
```

- Reuses existing `SUPABASE_URL` / `SUPABASE_KEY` secrets — no new secrets.
- If `bot.export` fails, the job fails and **nothing deploys** (last good site
  stays live).
- Empty Supabase is **not** a failure: export writes `{"tournaments": []}` and
  the site shows its empty state.

## Front-end change & local dev

- `web/app.js`: change the one fetch from `data/mock-tournaments.json` →
  `data/tournaments.json`. Nothing else changes.
- Rename `web/data/mock-tournaments.json` → `web/data/tournaments.json`
  (committed **seed** sample data). The Action overwrites it in the build with
  live data; locally, `python -m http.server` in `web/` serves the seed, so the
  site works with zero Supabase setup.
- No `mock-tournaments.json` left behind (avoids two sample files drifting).

## Testing

- `tests/test_export.py` (pytest, reusing the bot's venv) covering the pure
  `build_site_data`:
  - full pairing (2 rows) → correct `player1`/`player2`, each with its own
    `game_wins` and record;
  - a **bye** (1 row) → `player2: null`;
  - multiple rounds and tournaments → correct grouping, ascending round/pairing
    order, tournaments ordered by date;
  - null tournament `name` → `"Tournament"` fallback;
  - `id` stringified.
- CI runs `pytest` for the export test (extend the existing `web-ci.yml` with a
  Python test job, or add a small `bot-ci.yml`). The front-end `node --test`
  suite is unchanged.
- A sanity check that the committed seed `tournaments.json` parses and has the
  expected top-level shape.

## Error handling

- Missing `SUPABASE_URL`/`SUPABASE_KEY` → non-zero exit with a clear message →
  workflow fails, no deploy.
- Supabase query error → propagates, job fails, no deploy.
- Empty result set → valid `{"tournaments": []}`, site renders empty state.

## Files changed

- Create: `bot/export.py`
- Create: `tests/test_export.py`
- Modify: `web/app.js` (data source path)
- Rename: `web/data/mock-tournaments.json` → `web/data/tournaments.json`
- Modify: `.github/workflows/pages.yml` (triggers + Python export step)
- CI: run `pytest` for the export (extend `web-ci.yml` or add `bot-ci.yml`)

## Future work (noted, not built)

- If the served data grows large, scope the export to recent quarters.
- If least-privilege becomes a priority, switch from service_role to an anon key
  with read-only RLS policies.
