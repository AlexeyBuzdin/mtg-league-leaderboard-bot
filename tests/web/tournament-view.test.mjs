import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderTournament } from '../../web/ui/tournament-view.js';

const rec = (w, d, l) => ({ wins: w, draws: d, losses: l });

test('marks the game-score winner and shows round labels and records', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.match(html, /Round 1/);
  assert.match(html, /1-0-0/);
  assert.match(html, /2-1/);
  const markIndex = html.indexOf('✓');
  const scoreIndex = html.indexOf('2-1');
  assert.ok(markIndex > -1 && markIndex < scoreIndex);
});

test('renders a bye as a single-player row', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Cara', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.match(html, /Bye/);
  assert.match(html, /Cara/);
});
