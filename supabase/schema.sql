-- One row per parsed results message
create table if not exists tournaments (
  id                  bigint generated always as identity primary key,
  discord_message_id  text not null unique,
  name                text not null,
  event_date          date not null,
  channel_id          text not null,
  ingested_at         timestamptz not null default now()
);

-- One row per player line in a tournament
create table if not exists results (
  id              bigint generated always as identity primary key,
  tournament_id   bigint not null references tournaments(id) on delete cascade,
  standing        int  not null,
  player_name     text not null,
  player_key      text not null,
  points          int  not null,
  wins            int  not null,
  draws           int  not null,
  losses          int  not null,
  deck            text,
  unique (tournament_id, standing)
);

create index if not exists results_player_key_idx on results (player_key);
create index if not exists tournaments_event_date_idx on tournaments (event_date);
