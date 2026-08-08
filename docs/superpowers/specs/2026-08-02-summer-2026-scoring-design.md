# Summer 2026 Season Scoring Formula — Design

**Date:** 2026-08-02
**Status:** Approved (pending spec review)

## Summary

For the **Summer 2026** season, replace the leaderboard's `sum of (3·wins + draws)`
total with a special per-tournament formula that rewards placement, wins, ties,
and attendance. The rule attaches to the **tournament** (by its date's season),
so both the website season leaderboard and the Discord monthly post use it
automatically for Summer-2026 tournaments; every other tournament keeps the
current scoring.

## The scoring rule (per tournament, per player)

1. **Match points (for ranking only):** `mp = 3·wins + draws` from the player's
   final record.
2. **Rank all attendees** (league *and* non-league) within the tournament by
   `mp` desc, then **total game wins** desc (sum of `game_wins` across the
   player's pairings; null → 0), then name asc.
3. **Placement bonus:** rank 1 → **+3**, rank 2 → **+2**, rank 3 → **+1**,
   rank ≥ 4 → 0.
4. **Tournament score:**
   - **Summer 2026** tournament (`seasonKey(date) === "2026-2"`, i.e. Jun/Jul/Aug
     2026): `placementBonus + 2·wins + 1·draws + 1` (the `+1` is attendance).
   - otherwise: `3·wins + draws` (unchanged).

**Total** = Σ tournament score over the window's tournaments, per player. The
leaderboard shows only **league** players (non-league still count for placement
but are not displayed), sorted by total desc, name asc.

Worked check (Summer-2026 tournament, a league player goes 3-0 and finishes 1st
among all attendees): `+3 (1st) + 2·3 + 0 + 1 = 10`.

## Decisions (from brainstorming)

- **Placement source:** computed from match points, ties broken by total game
  wins, then name (exactly one player per rank).
- **Who is ranked:** all attendees (league + non-league); non-league count for
  placement but are excluded from the displayed board.
- **Scope:** website season leaderboard **and** Discord monthly post; the rule is
  keyed on the tournament's date season, so both apply it to Summer-2026
  tournaments only.

## Website (`web/lib/leaderboard.js`)

- **`playerTournamentStats(tournament)`** → `{ name: { record, gameWins, isLeague } }`
  — final record per player + summed `game_wins` (null → 0) + `is_league !== false`.
- **`tournamentScores(tournament)`** → `{ name: { score, isLeague } }` — ranks all
  attendees by `(mp desc, gameWins desc, name asc)`, assigns the placement bonus,
  and applies the rule (summer formula when `seasonKey(tournament.date) === "2026-2"`,
  else `3·wins + draws`).
- **`seasonLeaderboard(tournaments, key)`** — for each tournament in the season,
  add each league player's `score`, count events; sort by total desc, name asc.
- `points()` and `finalRecords()` are kept (still used/tested). Because the rule
  falls back to `3·wins + draws` for non-summer tournaments, other seasons'
  leaderboards are unchanged.

## Discord / store (Python)

- **`store.fetch_tournament_stats(start, end)`** (new) — selects `round_results`
  in the window joined to `tournaments.event_date`, and reduces per
  `(tournament_id, player_key)` to: final `record_wins`/`record_draws` (the
  max-round row), **summed** `game_wins` (null → 0), plus `player_name` and
  `event_date`. Returns all attendees.
- **`bot/leaderboard.py`** — a pure scorer mirroring the JS rule: group stats by
  tournament; rank each tournament's attendees by `(mp desc, game_wins desc,
  name asc)`; apply the placement bonus; score each player with the summer
  formula when `event_date` is in Summer 2026 (`year == 2026 and month in
  {6, 7, 8}`), else `3·wins + draws`; sum scores for league players
  (`fetch_league_keys()`), count events.
- `run()` swaps `fetch_results_in_window` + `aggregate_totals` for
  `fetch_tournament_stats` + the new scorer. `aggregate_totals` /
  `fetch_results_in_window` are removed if unused after the swap (the plan will
  verify no other caller), otherwise left in place.

## Seed data & testing

- **Seed:** no shape change — the exported JSON already carries `game_wins`,
  `record`, and `is_league` per player. Existing summer-dated seed tournaments
  now score under the new formula (numbers sanity-checked).
- **Web (`node --test`):** placement 1st/2nd/3rd with the game-win tiebreak;
  non-league counted for placement but excluded from the board; the attendance
  point; a non-summer season still uses `3·wins + draws`; the existing
  summer-dated `seasonLeaderboard` test updated to the new values.
- **Python (pytest):** the pure scorer (placement, tiebreak, attendance,
  summer-vs-not by `event_date`, league filtering) and `fetch_tournament_stats`
  reduction (final record + summed game wins) against a fake client.

## Edge cases

- Fewer than 3 attendees: only the available ranks get placement bonuses.
- Legacy standings-import tournaments (`game_wins` null): tiebreak by game wins
  degrades to name order; match points still rank them.
- Byes contribute the player's record but no opponent; `game_wins` may be null →
  counted as 0.

## Files changed

- `web/lib/leaderboard.js` — new helpers + rewritten `seasonLeaderboard`
- `tests/web/leaderboard.test.mjs` — updated + new tests
- `bot/store.py` — `fetch_tournament_stats`
- `bot/leaderboard.py` — pure seasonal scorer + `run()` swap
- `tests/test_store.py`, `tests/test_leaderboard.py` — new/updated tests

## Delivery

A pull request from the `summer-scoring` branch. No schema or live-DB change; no
workflow change.
