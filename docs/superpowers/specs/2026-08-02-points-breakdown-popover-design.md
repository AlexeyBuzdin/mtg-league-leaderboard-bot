# Leaderboard Points Breakdown Popover — Design

**Date:** 2026-08-02
**Status:** Approved

## Summary

On the website leaderboard, add a "?" icon after each player's points. Clicking
it opens a small popover anchored to the icon showing the **full, per-tournament
itemized calculation** of that player's total. Website only (the Discord post is
static text).

## Decisions (from brainstorming)

- **Presentation:** a small popover anchored beside the clicked "?"; dismiss on
  click-outside, `Esc`, or clicking the same icon again.
- **Detail:** per-tournament, itemized (each component spelled out) with a
  subtotal per tournament and a grand total.
- **All seasons:** the popover works for every season; a non-summer season shows
  the `3·wins + draws` breakdown (no placement/attendance).

## Breakdown data

`seasonLeaderboard` gains a `breakdown` per player row: one entry per tournament
the player played that season.

- Row shape: `{ name, points, events, breakdown }`.
- `breakdown` entry: `{ tournament, date, items: [{ label, points }], subtotal }`.
- Items per tournament:
  - **Summer 2026** (`seasonKey(date) === "2026-2"`):
    - placement (only if the player finished top-3): `label` = `"1st place"` /
      `"2nd place"` / `"3rd place"`, `points` = 3 / 2 / 1.
    - wins (only if `> 0`): `label` = `"{n} win(s) (×2)"`, `points` = `2·wins`.
    - draws (only if `> 0`): `label` = `"{n} draw(s) (×1)"`, `points` = `draws`.
    - `label` = `"attendance"`, `points` = 1.
  - **Any other season:**
    - wins (only if `> 0`): `label` = `"{n} win(s) (×3)"`, `points` = `3·wins`.
    - draws (only if `> 0`): `label` = `"{n} draw(s) (×1)"`, `points` = `draws`.
- `subtotal` = sum of the entry's item points (equals the tournament score).
- The grand total equals `points` (already computed).

`tournamentScores(tournament)` is extended to return, per player,
`{ score, isLeague, breakdown }` where `breakdown` is that tournament's entry;
`seasonLeaderboard` accumulates the entries into the per-player array.

## Rendering (pure, `web/ui/leaderboard-view.js`)

- `renderLeaderboard(rows)` adds, after the points cell, a button:
  `<button class="why" data-index="${i}" aria-label="Points breakdown for ${row.name}">?</button>`.
- New pure `renderBreakdown(row)` → HTML string for the popover content:
  - header: `${row.name} — ${row.points} pts`;
  - a section per `breakdown` entry: a `${tournament} · ${date}` heading, one
    `label … +points` line per item, and a `subtotal … subtotal` line;
  - a final `Total … points` line.

Both are pure string functions, unit-tested.

## Interaction (`web/app.js` + popover element)

- `web/index.html` gains `<div id="breakdown-popover" class="breakdown-popover" hidden></div>`.
- `setupLeaderboard` keeps the current `rows` (updated each `render()`); a click
  handler delegated on `#lb-body` catches a `.why` click, fills the popover via
  `renderBreakdown(rows[index])`, positions it below-left of the clicked icon
  (`getBoundingClientRect` + scroll offsets, clamped to the viewport width), and
  shows it.
- Dismiss: click outside the popover (and not on a `.why`), `Esc`, or clicking
  the same "?" again; re-rendering the board (season change) also hides it.
- This DOM wiring lives in `app.js` alongside the existing tab/selector wiring
  and is verified manually, not unit-tested.

## Styling (`web/styles.css`)

- `.why` — small circular muted button (~16px) with a `?`, hover state, no
  layout shift in the points cell.
- `.breakdown-popover` — `position: absolute`, high `z-index`, card styling
  (surface bg, hairline border, shadow, `border-radius`, padding, `max-width`
  ~260px), theme-aware; hidden via the `hidden` attribute.
- `.bd-head`, `.bd-tournament`, `.bd-item` (flex row: label left, points right),
  `.bd-subtotal`, `.bd-total` for the content.

## Testing

- **Web (`node --test`):**
  - `seasonLeaderboard` rows carry a `breakdown` whose items match the formula —
    a Summer 2026 player (placement + `×2` wins + attendance) and a non-summer
    player (`×3` wins), with zero-value components omitted; `subtotal` equals the
    tournament score and the entries sum to `points`.
  - `renderLeaderboard` emits exactly one `.why` button per row with the correct
    `data-index`.
  - `renderBreakdown(row)` includes the tournament headings, item labels/points,
    subtotals, and the grand total.
- **Interaction** (open / position / dismiss) verified in the browser.

## Files changed

- `web/lib/leaderboard.js` — breakdown in `tournamentScores` + `seasonLeaderboard`
- `web/ui/leaderboard-view.js` — `.why` button + `renderBreakdown`
- `web/app.js` — popover wiring
- `web/index.html` — popover element
- `web/styles.css` — `.why`, `.breakdown-popover`, `.bd-*`
- `tests/web/leaderboard.test.mjs`, `tests/web/leaderboard-view.test.mjs`

## Delivery

A pull request from the `points-breakdown` branch. No backend/schema/workflow
change.
