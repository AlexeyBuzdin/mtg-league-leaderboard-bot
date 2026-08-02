# Non-League Tag in Tournament View — Design

**Date:** 2026-08-02
**Status:** Approved

## Summary

In the tournament-detail tab, show a small "Not from League" pill next to each
player who is not a league member, so non-league opponents are visually marked.
Purely a rendering change — the `is_league` flag is already on every player
object (from the league-flag feature).

## Behaviour

- Show the pill when `player.is_league === false`.
- A **missing** `is_league` (or `true`) shows **no** pill — consistent with the
  leaderboard's "missing flag = league" rule.
- Applies to **both** render paths in `web/ui/tournament-view.js`:
  - pairing rounds (`pairingRow`): player1, player2, and the bye's lone player;
  - the standings table (`renderStandings`): the player-name cell.
- Label: `Not from League`, rendered as a small styled **pill** (not literal
  brackets).

## Styling

A quiet annotation, not a loud badge: a small muted pill (`.non-league`) —
11px, muted text, hairline border, subtle surface background, rounded — placed
just after the player name.

## Files

- `web/ui/tournament-view.js` — a `leagueTag(player)` helper returning the pill
  HTML (or `''`), inserted after each player name in both paths.
- `web/styles.css` — `.non-league` pill style.
- `tests/web/tournament-view.test.mjs` — pill shows for a non-league player
  (pairings and standings), absent for league / missing-flag players.

No data, workflow, or backend changes.

## Delivery

A pull request from the `non-league-tag` branch.
