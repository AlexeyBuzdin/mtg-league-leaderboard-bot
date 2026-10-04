import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fetchAll, loadSiteData } from '../../web/lib/supabase-data.js';

// Fake client mirroring the supabase-js query chain: from().select().range()
// resolves to { data, error }. range() slices to mimic PostgREST paging.
class FakeBuilder {
  constructor(rows) { this.rows = rows; }
  select() { return this; }
  async range(start, end) {
    return { data: this.rows.slice(start, end + 1), error: null };
  }
}
class FakeClient {
  constructor(tables) { this.tables = tables; }
  from(name) { return new FakeBuilder(this.tables[name] ?? []); }
}

function res(tid, rnd, pr, name, key, gw, w, d, l) {
  return {
    tournament_id: tid, round: rnd, pairing: pr, player_name: name,
    player_key: key, game_wins: gw, record_wins: w, record_draws: d, record_losses: l,
  };
}

test('fetchAll pages past the 1000-row cap', async () => {
  const rows = Array.from({ length: 2500 }, (_, i) => ({ n: i }));
  const client = new FakeClient({ big: rows });
  const got = await fetchAll(client, 'big', 'n');
  assert.equal(got.length, 2500);
  assert.equal(got[0].n, 0);
  assert.equal(got[2499].n, 2499);
});

test('fetchAll throws on a query error', async () => {
  const client = {
    from: () => ({ select: () => ({ range: async () => ({ data: null, error: new Error('boom') }) }) }),
  };
  await assert.rejects(() => fetchAll(client, 'x', 'c'), /boom/);
});

test('loadSiteData composes tables into the site shape with league flags', async () => {
  const client = new FakeClient({
    tournaments: [{ id: 1, name: 'A', event_date: '2026-07-06' }],
    round_results: [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0),
                    res(1, 1, 1, 'Guest', 'guest', 1, 0, 0, 1)],
    players: [{ player_key: 'ann', is_league: true },
              { player_key: 'guest', is_league: false }],
  });
  const data = await loadSiteData(client);
  const p = data.tournaments[0].rounds[0].pairings[0];
  const byName = { [p.player1.name]: p.player1, [p.player2.name]: p.player2 };
  assert.equal(byName.Ann.is_league, true);
  assert.equal(byName.Guest.is_league, false);
});

test('loadSiteData returns raw players including display_name', async () => {
  const client = new FakeClient({
    tournaments: [{ id: 1, name: 'A', event_date: '2026-07-06' }],
    round_results: [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)],
    players: [{ player_key: 'ann', display_name: 'Ann', is_league: true }],
  });
  const data = await loadSiteData(client);
  assert.deepEqual(data.players, [{ player_key: 'ann', display_name: 'Ann', is_league: true }]);
  assert.equal(data.tournaments[0].rounds[0].pairings[0].player1.name, 'Ann');
});

test('loadSiteData returns achievements mapped by name', async () => {
  const client = new FakeClient({
    tournaments: [{ id: 1, name: 'A', event_date: '2026-07-06' }],
    round_results: [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)],
    players: [{ player_key: 'ann', display_name: 'Ann', is_league: true }],
    achievements: [{ player_key: 'ann', label: '🏆Summer 2026' }],
  });
  const data = await loadSiteData(client);
  assert.deepEqual(data.achievements.get('Ann'), ['🏆Summer 2026']);
});
