import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const data = JSON.parse(
  readFileSync(new URL('../../web/data/tournaments.json', import.meta.url), 'utf-8'),
);

test('committed seed data matches the front-end shape', () => {
  assert.ok(Array.isArray(data.tournaments) && data.tournaments.length > 0);
  const t = data.tournaments[0];
  for (const key of ['id', 'name', 'date', 'rounds']) {
    assert.ok(key in t, `tournament missing ${key}`);
  }
  const pairing = t.rounds[0].pairings[0];
  assert.ok('pairing' in pairing && 'player1' in pairing && 'player2' in pairing);
  const p1 = pairing.player1;
  assert.ok('name' in p1 && 'game_wins' in p1 && 'record' in p1);
});

test('seed players carry an is_league flag and include a non-league example', () => {
  const flags = [];
  for (const t of data.tournaments) {
    for (const r of t.rounds) {
      for (const p of r.pairings) {
        for (const player of [p.player1, p.player2]) {
          if (player) flags.push(player.is_league);
        }
      }
    }
  }
  assert.ok(flags.every(f => typeof f === 'boolean'));
  assert.ok(flags.includes(true));
  assert.ok(flags.includes(false));
});

test('seed data includes at least one player with deck colours', () => {
  let found = false;
  for (const t of data.tournaments) {
    for (const r of t.rounds) {
      for (const p of r.pairings) {
        for (const player of [p.player1, p.player2]) {
          if (player && player.deck_colours) found = true;
        }
      }
    }
  }
  assert.ok(found);
});
