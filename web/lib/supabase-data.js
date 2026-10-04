// Thin I/O wrapper: page the three tables through an injected Supabase client
// and build the site shape. The client is a parameter (never imported here) so
// the module carries no CDN dependency and is unit-testable in Node.
import { buildSiteData, achievementsByName } from './site-data.js';

const PAGE_SIZE = 1000;

const TOURNAMENT_COLS = 'id, name, event_date';
const RESULT_COLS =
  'tournament_id, round, pairing, final_rank, player_name, player_key, ' +
  'game_wins, record_wins, record_draws, record_losses, ' +
  'player_deck, player_deck_colours';
const PLAYER_COLS = 'player_key, display_name, is_league';
const ACHIEVEMENT_COLS = 'player_key, label';

export async function fetchAll(client, table, cols) {
  // PostgREST caps a single response (~1000 rows); page explicitly so a dropped
  // round_results row never renders as a false bye.
  const rows = [];
  let start = 0;
  for (;;) {
    const { data, error } = await client
      .from(table)
      .select(cols)
      .range(start, start + PAGE_SIZE - 1);
    if (error) throw error;
    rows.push(...data);
    if (data.length < PAGE_SIZE) break;
    start += PAGE_SIZE;
  }
  return rows;
}

export async function loadSiteData(client) {
  const [tournaments, results, players, achievements] = await Promise.all([
    fetchAll(client, 'tournaments', TOURNAMENT_COLS),
    fetchAll(client, 'round_results', RESULT_COLS),
    fetchAll(client, 'players', PLAYER_COLS),
    fetchAll(client, 'achievements', ACHIEVEMENT_COLS),
  ]);
  const leagueKeys = new Set(
    players.filter(p => p.is_league).map(p => p.player_key),
  );
  return {
    ...buildSiteData(tournaments, results, leagueKeys),
    players,
    achievements: achievementsByName(achievements, results, players),
  };
}
