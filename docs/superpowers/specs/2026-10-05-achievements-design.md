# Player Achievements — Design

**Date:** 2026-10-05
**Status:** Approved (design approved in chat)

## Summary

Add player **achievements** — short badge labels (e.g. `🏆Summer 2026`) earned by
a league player — stored in a new Supabase table, read live by the front-end, and
shown as a new section on the player profile **immediately before Placements**.
Seed one achievement (`🏆Summer 2026`) for the player `Mārcis K`.

## Goals

- A new `achievements` table linking a label to a player (`player_key`).
- Achievements rendered on the profile (and the embedded Account profile) as a
  row of pill badges, just above Placements; the section is omitted when a player
  has none.
- Seed `🏆Summer 2026` for `Mārcis K`.

## Non-goals

- No admin UI to add/edit achievements (inserted via Supabase, like decks).
- No per-achievement metadata beyond a single label (no icon/title split, no
  season linkage) — a single label string holds emoji + text.
- No awarding logic / automatic computation.

## Decisions (from brainstorming)

- **Storage:** a single `label` text column (emoji + text together).
- **Link:** `player_key` (plain text, same key used in `round_results`/`players`);
  **no hard FK to `players`**, so legacy players not on the `is_league` roster can
  still have achievements.
- **Rendering:** pill badges under an `Achievements` heading, before Placements;
  section hidden when empty.

## Data model

```sql
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
- `unique (player_key, label)` → the seed insert and any re-run are idempotent.
- Read-only public SELECT policy, matching `players`/`round_results`. No write
  policies (writes via service_role / Supabase dashboard).
- Added to `supabase/schema.sql` and applied to the live DB.

## Data access (`web/lib/supabase-data.js` + `web/lib/site-data.js`)

- `loadSiteData` additionally pages the `achievements` table (`player_key, label`)
  via the existing `fetchAll`.
- A **pure** helper (in `site-data.js`, unit-tested) joins achievements to
  display names:
  `achievementsByName(achievements, results, players) -> Map<name, string[]>` —
  for each achievement `player_key`, attach its labels to every `player_name`
  (from `round_results`) and `display_name` (from `players`) that shares that key.
  (The profile is keyed by display name, not `player_key`, so the join happens
  here.)
- `loadSiteData` returns the resulting `achievementsByName` map alongside the
  existing data.

## Profile rendering (`web/ui/profile-view.js`, `web/app.js`, `web/styles.css`)

- `renderProfile(name, profile, seasons, selectedSeason, options)` gains
  `options.achievements` (array of label strings, default `[]`).
- When non-empty, a section is rendered **before** the Placements section:
  ```html
  <h2 class="profile-section">Achievements</h2>
  <div class="achievements">
    <span class="achievement">🏆Summer 2026</span> …
  </div>
  ```
  When empty, nothing is emitted (no heading).
- `web/app.js`: `renderProfileFor` and the Account `linkedFor` path pass
  `{ achievements: achievementsByName.get(name) ?? [] }` through to
  `renderProfile` (so both the standalone profile and the embedded Account
  profile show them).
- `web/styles.css`: a small `.achievements` (flex row, wrap) + `.achievement`
  (pill: subtle background, radius, padding) style.

## Seed data

- Insert `('<mārcis-key>', '🏆Summer 2026')` into `achievements`, idempotent via
  `on conflict (player_key, label) do nothing`. Mārcis's exact `player_key` is
  confirmed by querying the live DB first; the write is approval-gated.

## Testing

- `site-data` test: `achievementsByName` attaches labels to the right names
  (incl. a key present under multiple name spellings; a key with no matching
  name is simply absent).
- `profile-view` test: the Achievements section renders badges **before**
  Placements when present, and is omitted when the achievements array is empty;
  existing sections unchanged.
- Live-DB verification: after the insert, query the achievement back and confirm
  it attaches to Mārcis's profile name.

## Delivery

- A PR (schema + data-access + UI + tests) from `feat/achievements`.
- The live table-create and the seed insert are separate, approval-gated DB
  actions (the site only shows the data once both are applied and the deploy
  reads live).
