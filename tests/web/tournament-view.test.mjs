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

test('renders a bye as a single-player row within a pairing event', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 0, record: rec(0, 0, 1) } },
      { pairing: 2, player1: { name: 'Cara', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.match(html, /Bye/);
  assert.match(html, /Cara/);
});

test('marks player 2 as winner when they have more game wins', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 1, record: rec(0, 0, 1) }, player2: { name: 'Bob', game_wins: 2, record: rec(1, 0, 0) } },
    ] },
  ] };
  const html = renderTournament(tournament);
  const markIndex = html.indexOf('✓');
  const scoreIndex = html.indexOf('1-2');
  assert.ok(markIndex > scoreIndex);
});

test('marks neither side on a drawn game score', () => {
  const tournament = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 1, record: rec(0, 1, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 1, 0) } },
    ] },
  ] };
  const html = renderTournament(tournament);
  assert.ok(!html.includes('✓'));
  assert.ok(!html.includes('class="side win"'));
  assert.ok(!html.includes('class="side right win"'));
});

test('renders a standings-only event as a ranked table, not byes', () => {
  const legacy = { name: 'Monday Standard', date: '2026-07-20', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Elliot N', game_wins: null, record: rec(3, 0, 0) }, player2: null },
      { pairing: 3, player1: { name: 'Vlad K', game_wins: null, record: rec(2, 0, 1) }, player2: null },
      { pairing: 2, player1: { name: 'Toms L', game_wins: null, record: rec(3, 0, 0) }, player2: null },
    ] },
  ] };
  const html = renderTournament(legacy);
  assert.ok(!html.includes('Bye'));
  assert.ok(!html.includes('Round 1'));
  assert.ok(!html.includes('class="pairing'));
  assert.match(html, /Player/);
  assert.match(html, /Points/);
  assert.ok(html.indexOf('Elliot N') < html.indexOf('Toms L'));
  assert.ok(html.indexOf('Toms L') < html.indexOf('Vlad K'));
  assert.match(html, /3-0-0/);
  assert.match(html, /2-0-1/);
  assert.match(html, />9</);  // Elliot: 3*3+0
  assert.match(html, />6</);  // Vlad: 3*2+0
});

test('a normal pairing event still renders pairings (regression)', () => {
  const t = { name: 'A', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const html = renderTournament(t);
  assert.match(html, /Round 1/);
  assert.match(html, /2-1/);
  assert.match(html, /class="pairing/);
});
