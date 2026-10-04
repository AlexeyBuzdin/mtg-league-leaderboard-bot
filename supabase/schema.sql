-- One row per parsed tournament message
create table if not exists tournaments (
  id                  bigint generated always as identity primary key,
  discord_message_id  text not null unique,
  name                text,
  event_date          date not null,
  channel_id          text not null,
  ingested_at         timestamptz not null default now()
);

-- One row per player per pairing (two rows per full pairing, one per bye)
create table if not exists round_results (
  id                 bigint generated always as identity primary key,
  tournament_id      bigint not null references tournaments(id) on delete cascade,
  round              int  not null,
  pairing            int  not null,
  player_name        text not null,
  player_key         text not null,
  opponent_name      text,
  opponent_key       text,
  game_wins          int,
  opponent_game_wins int,
  record_wins        int  not null,
  record_draws       int  not null,
  record_losses      int  not null,
  unique (tournament_id, round, player_key)
);

create index if not exists round_results_player_key_idx on round_results (player_key);
create index if not exists round_results_tournament_idx on round_results (tournament_id, player_key);
create index if not exists tournaments_event_date_idx on tournaments (event_date);

-- League roster: which players appear on the leaderboards.
create table if not exists players (
  player_key   text primary key,
  display_name text,
  is_league    boolean not null default false,
  created_at   timestamptz not null default now()
);

-- Optional per-player deck info (filled manually in Supabase).
alter table round_results add column if not exists player_deck            text;
alter table round_results add column if not exists opponent_deck          text;
alter table round_results add column if not exists player_deck_colours     text;
alter table round_results add column if not exists opponent_deck_colours   text;
-- Official final standing (1 = winner) from an authoritative standings source;
-- null when placement should be computed from records.
alter table round_results add column if not exists final_rank             smallint;

-- Public read access for the browser (anon key). RLS is the security boundary;
-- these SELECT policies expose exactly the data already published in the static
-- site. The Discord bot/export uses service_role, which bypasses RLS. Writes
-- remain closed (no INSERT/UPDATE/DELETE policies) — added in a later phase.
alter table tournaments   enable row level security;
alter table round_results enable row level security;
alter table players       enable row level security;

drop policy if exists "public read tournaments"   on tournaments;
drop policy if exists "public read round_results"  on round_results;
drop policy if exists "public read players"        on players;

create policy "public read tournaments"  on tournaments
  for select to anon, authenticated using (true);
create policy "public read round_results" on round_results
  for select to anon, authenticated using (true);
create policy "public read players"       on players
  for select to anon, authenticated using (true);

-- Links a signed-in auth user to a league player. The admin sets player_key
-- manually in the Supabase dashboard (service_role bypasses RLS). Users may read
-- ONLY their own row; there are no user write policies.
create table if not exists profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  player_key text references players(player_key),
  created_at timestamptz not null default now()
);

alter table profiles enable row level security;
drop policy if exists "own profile read" on profiles;
create policy "own profile read" on profiles
  for select to authenticated using (auth.uid() = id);

-- Player achievements: short badge labels (emoji + text) shown on the profile.
-- Linked by player_key (no FK, so legacy players off the is_league roster qualify).
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
