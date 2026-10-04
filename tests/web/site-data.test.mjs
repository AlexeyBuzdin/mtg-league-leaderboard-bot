import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildSiteData } from '../../web/lib/site-data.js';

function res(tid, rnd, pr, name, key, gw, w, d, l, extra = {}) {
  return {
    tournament_id: tid, round: rnd, pairing: pr,
    player_name: name, player_key: key, game_wins: gw,
    record_wins: w, record_draws: d, record_losses: l, ...extra,
  };
}

test('full pairing produces two players with records', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0),
                   res(1, 1, 1, 'Bob', 'bob', 1, 0, 0, 1)];
  const t = buildSiteData(tournaments, results).tournaments[0];
  assert.equal(t.id, '1');
  assert.equal(t.date, '2026-07-06');
  const p = t.rounds[0].pairings[0];
  assert.equal(p.pairing, 1);
  assert.deepEqual(p.player1, {
    name: 'Ann', game_wins: 2, record: { wins: 1, draws: 0, losses: 0 },
    is_league: true, deck: null, deck_colours: null, standing: null,
  });
  assert.deepEqual(p.player2, {
    name: 'Bob', game_wins: 1, record: { wins: 0, draws: 0, losses: 1 },
    is_league: true, deck: null, deck_colours: null, standing: null,
  });
});

test('a bye is a single-row pairing with player2 null', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Cara', 'cara', 2, 1, 0, 0)];
  const p = buildSiteData(tournaments, results).tournaments[0].rounds[0].pairings[0];
  assert.equal(p.player1.name, 'Cara');
  assert.equal(p.player2, null);
});

test('player1 is deterministic by player_key regardless of input order', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Bob', 'bob', 1, 0, 0, 1),
                   res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)];
  const p = buildSiteData(tournaments, results).tournaments[0].rounds[0].pairings[0];
  assert.equal(p.player1.name, 'Ann');
  assert.equal(p.player2.name, 'Bob');
});

test('tournaments sort by date; rounds sort numerically', () => {
  const tournaments = [{ id: 2, name: 'Later', event_date: '2026-08-01' },
                       { id: 1, name: 'Earlier', event_date: '2026-07-06' }];
  const results = [
    res(1, 2, 1, 'Ann', 'ann', 2, 2, 0, 0), res(1, 2, 1, 'Bob', 'bob', 1, 1, 0, 1),
    res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0), res(1, 1, 1, 'Bob', 'bob', 1, 0, 0, 1),
    res(2, 1, 1, 'Ann', 'ann', 2, 1, 0, 0), res(2, 1, 1, 'Zed', 'zed', 0, 0, 0, 1),
  ];
  const data = buildSiteData(tournaments, results);
  assert.deepEqual(data.tournaments.map(t => t.name), ['Earlier', 'Later']);
  assert.deepEqual(data.tournaments[0].rounds.map(r => r.round), [1, 2]);
});

test('null tournament name falls back to "Tournament"', () => {
  const tournaments = [{ id: 1, name: null, event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)];
  assert.equal(buildSiteData(tournaments, results).tournaments[0].name, 'Tournament');
});

test('is_league reflects the league key set', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0),
                   res(1, 1, 1, 'Guest', 'guest', 1, 0, 0, 1)];
  const p = buildSiteData(tournaments, results, new Set(['ann']))
    .tournaments[0].rounds[0].pairings[0];
  const byName = { [p.player1.name]: p.player1, [p.player2.name]: p.player2 };
  assert.equal(byName.Ann.is_league, true);
  assert.equal(byName.Guest.is_league, false);
});

test('is_league defaults to true when no league keys are given', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0)];
  const p = buildSiteData(tournaments, results).tournaments[0].rounds[0].pairings[0];
  assert.equal(p.player1.is_league, true);
});

test('deck, colours and standing are carried through', () => {
  const tournaments = [{ id: 1, name: 'A', event_date: '2026-07-06' }];
  const results = [
    res(1, 1, 1, 'Ann', 'ann', 2, 1, 0, 0,
        { player_deck: 'Izzet Prowess', player_deck_colours: 'UR', final_rank: 1 }),
    res(1, 1, 1, 'Bob', 'bob', 1, 0, 0, 1, { final_rank: 5 }),
  ];
  const p = buildSiteData(tournaments, results).tournaments[0].rounds[0].pairings[0];
  const byName = { [p.player1.name]: p.player1, [p.player2.name]: p.player2 };
  assert.equal(byName.Ann.deck, 'Izzet Prowess');
  assert.equal(byName.Ann.deck_colours, 'UR');
  assert.equal(byName.Ann.standing, 1);
  assert.equal(byName.Bob.deck, null);
  assert.equal(byName.Bob.deck_colours, null);
  assert.equal(byName.Bob.standing, 5);
});

import { achievementsByName } from '../../web/lib/site-data.js';

test('achievementsByName maps labels onto every name sharing the key', () => {
  const achievements = [
    { player_key: 'marcis k', label: '🏆Summer 2026' },
    { player_key: 'marcis k', label: '🥈Spring 2026' },
  ];
  const results = [
    { player_name: 'Marcis K', player_key: 'marcis k' },
    { player_name: 'Other P', player_key: 'other p' },
  ];
  const players = [{ player_key: 'marcis k', display_name: 'Marcis K' }];
  const map = achievementsByName(achievements, results, players);
  assert.deepEqual(map.get('Marcis K'), ['🏆Summer 2026', '🥈Spring 2026']);
  assert.equal(map.has('Other P'), false);
});

test('achievementsByName ignores achievements whose key has no name', () => {
  const map = achievementsByName(
    [{ player_key: 'ghost', label: 'x' }], [], [],
  );
  assert.equal(map.size, 0);
});
