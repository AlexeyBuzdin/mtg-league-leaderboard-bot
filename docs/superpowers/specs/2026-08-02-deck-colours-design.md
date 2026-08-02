# Deck Name & Colours in Tournament View — Design

**Date:** 2026-08-02
**Status:** Approved (pending spec review)

## Summary

Store an optional deck name and colour identity per player-row in
`round_results`, and show them in the tournament tab: after each player's name,
render the colour identity as MTG mana-symbol icons, then the deck name. Deck
data is entered **manually in Supabase** for now (the bot does not parse it).

## Decisions (from brainstorming)

- **Data source:** manual in Supabase. Columns are nullable; the bot/parser/store
  are unchanged and leave them `NULL`.
- **Display order after the name:** colour icons, then deck name.
- **All four columns** are added (`player_*` and `opponent_*`), but only the
  player-side columns are used by the export/display (each row self-describes its
  own player).
- **Colour format:** a string of up to 5 characters from `W U B R G`.
- **Icons:** the 5 mana SVGs are committed to the repo and referenced locally.

## Schema

```sql
alter table round_results
  add column if not exists player_deck            text,
  add column if not exists opponent_deck          text,
  add column if not exists player_deck_colours    text,
  add column if not exists opponent_deck_colours  text;
```

Added to `supabase/schema.sql` and applied to the live project via a migration.
All nullable — existing rows and bot inserts are unaffected.

## Icons (committed assets)

Download the 5 raw mana SVGs (the actual `image/svg+xml` files — strip Fandom's
`/revision/latest/scale-to-width-down/15?cb=…` thumbnail suffix) into
`web/icons/mana/`:

| File | Source (raw `.svg`) |
|------|---------------------|
| `web/icons/mana/W.svg` | `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/8e/W.svg` |
| `web/icons/mana/U.svg` | `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/9/9f/U.svg` |
| `web/icons/mana/B.svg` | `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/2/2f/B.svg` |
| `web/icons/mana/R.svg` | `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/87/R.svg` |
| `web/icons/mana/G.svg` | `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/8/88/G.svg` |

Referenced as `icons/mana/W.svg` (relative to `web/`), so the deployed site makes
no external requests.

## Export (`bot/export.py`)

- Add `player_deck, player_deck_colours` to `_RESULT_COLS`.
- `_player_obj(row, league_keys)` also sets:
  - `"deck": row.get("player_deck")`
  - `"deck_colours": row.get("player_deck_colours")`
- These pass straight through to each JSON player object (null when unset).

## Web rendering (`web/ui/tournament-view.js`)

A pure helper renders the deck annotation after a player's name, in **both** the
pairing rounds and the standings-table view:

```js
const MANA = new Set(['W', 'U', 'B', 'R', 'G']);

function manaIcons(colours) {
  if (!colours) return '';
  return [...colours.toUpperCase()]
    .filter(c => MANA.has(c))
    .map(c => `<img class="mana" src="icons/mana/${c}.svg" alt="${c}" />`)
    .join('');
}

function deckInfo(player) {
  const icons = manaIcons(player.deck_colours);
  const name = player.deck ? `<span class="deck-name">${player.deck}</span>` : '';
  return icons + name;
}
```

- Inserted immediately after `<span class="name">…</span>` for player1, player2,
  the bye's lone player, and the standings player cell.
- Colour icons first, then the deck name (muted, small).
- Each shown only when its value is non-empty; invalid colour characters are
  skipped.

## Styling (`web/styles.css`)

- `.mana` — `height: 15px; width: 15px; vertical-align: -2px; margin: 0 1px;`
- `.deck-name` — `margin-left: 6px; font-size: 12px; color: var(--muted);`

## Seed data

Add `deck` and `deck_colours` to a couple of seed players in
`web/data/tournaments.json` (e.g. one with both, one with colours only) so local
dev and the shape test exercise the feature; leave others without (null).

## Testing

- **Web (`node --test`):**
  - `manaIcons`/render: a player with `deck_colours: "WUR"` renders 3 `<img>`
    tags for `W.svg`, `U.svg`, `R.svg` in order; deck name shown when present;
    nothing rendered when both are empty; invalid chars skipped.
  - Applies in both pairing and standings views.
- **Python (pytest):** `build_site_data`/`export_to_file` attach `deck` and
  `deck_colours` from the row (present and null cases).

## Live database

Apply the `alter table` (idempotent `add column if not exists`) to project
`shtatdxrwmiyzzvrfaai` via the Supabase tooling. No seed needed — columns start
`NULL` and are filled manually.

## Files changed

- `supabase/schema.sql` — add 4 columns
- `bot/export.py` — select + attach `deck`/`deck_colours`
- `tests/test_export.py` — deck passthrough tests
- `web/icons/mana/{W,U,B,R,G}.svg` — committed icon assets
- `web/ui/tournament-view.js` — render mana icons + deck name
- `web/styles.css` — `.mana`, `.deck-name`
- `web/data/tournaments.json` — sample deck data
- `tests/web/tournament-view.test.mjs` — render tests
- Live Supabase: `alter table round_results …` (via tooling)

## Delivery

A pull request from the `deck-colours` branch.
