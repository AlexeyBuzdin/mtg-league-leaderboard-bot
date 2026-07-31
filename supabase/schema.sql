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
