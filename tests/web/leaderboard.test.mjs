import { test } from 'node:test';
import assert from 'node:assert/strict';
import { finalRecords, points, seasonLeaderboard } from '../../web/lib/leaderboard.js';

const rec = (w, d, l) => ({ wins: w, draws: d, losses: l });

const t1 = {
  id: 'a', name: 'A', date: '2026-07-06',
  rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
    { round: 2, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(2, 0, 0) }, player2: { name: 'Bob', game_wins: 0, record: rec(0, 0, 2) } },
      { pairing: 2, player1: { name: 'Cara', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ],
};

test('finalRecords keeps the last record per player and includes byes', () => {
  const f = finalRecords(t1);
  assert.deepEqual(f['Ann'].record, rec(2, 0, 0));
  assert.deepEqual(f['Bob'].record, rec(0, 0, 2));
  assert.deepEqual(f['Cara'].record, rec(1, 0, 0));
  assert.equal(f['Ann'].isLeague, true);
});

test('points = 3*wins + draws', () => {
  assert.equal(points(rec(2, 1, 0)), 7);
  assert.equal(points(rec(0, 0, 3)), 0);
});

test('seasonLeaderboard sums points, counts events, filters by season, sorts', () => {
  const t2 = { id: 'b', name: 'B', date: '2026-08-01', rounds: [
    { round: 1, pairings: [ { pairing: 1, player1: { name: 'Bob', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Ann', game_wins: 0, record: rec(0, 0, 1) } } ] },
  ] };
  const q2Tournament = { id: 'c', name: 'C', date: '2026-04-01', rounds: [
    { round: 1, pairings: [ { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Zed', game_wins: 0, record: rec(0, 0, 1) } } ] },
  ] };
  const board = seasonLeaderboard([t1, t2, q2Tournament], '2026-2');
  // Summer 2026 formula. t1: Ann 1st(8), Cara 2nd(5), Bob 3rd(2). t2: Bob 1st(6), Ann 2nd(3).
  // q2Tournament is spring (season 2026-1) -> excluded.
  assert.deepEqual(board.map(r => r.name), ['Ann', 'Bob', 'Cara']);
  assert.equal(board[0].points, 11); // Ann 8 + 3
  assert.equal(board[0].events, 2);
  assert.equal(board[1].name, 'Bob');
  assert.equal(board[1].points, 8);  // 2 + 6
  assert.equal(board[1].events, 2);
  assert.equal(board[2].name, 'Cara');
  assert.equal(board[2].points, 5);
  assert.equal(board[2].events, 1);
  assert.ok(!board.find(r => r.name === 'Zed'));
});

test('seasonLeaderboard excludes non-league players', () => {
  const t = { id: 'x', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0), is_league: true },
        player2: { name: 'Guest', game_wins: 1, record: rec(0, 0, 1), is_league: false } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  assert.deepEqual(board.map(r => r.name), ['Ann']);
});

test('seasonLeaderboard treats a missing is_league as league', () => {
  const t = { id: 'x', date: '2026-07-06', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) },
        player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  assert.deepEqual(board.map(r => r.name).sort(), ['Ann', 'Bob']);
});

test('summer placement ranks by match points then game wins', () => {
  const t = { id: 't', date: '2026-07-10', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 1, record: rec(1, 0, 0) }, player2: { name: 'Cara', game_wins: 2, record: rec(0, 0, 1) } },
      { pairing: 2, player1: { name: 'Bob', game_wins: 2, record: rec(1, 0, 0) }, player2: null },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  // Ann mp3 gw1; Bob mp3 gw2; Cara mp0 gw2 -> Bob 1st(6), Ann 2nd(5), Cara 3rd(2)
  assert.deepEqual(board.map(r => [r.name, r.points]), [['Bob', 6], ['Ann', 5], ['Cara', 2]]);
});

test('non-league players count for placement but are hidden', () => {
  const t = { id: 't', date: '2026-07-10', rounds: [
    { round: 1, pairings: [
      { pairing: 1,
        player1: { name: 'Guest', game_wins: 2, record: rec(1, 0, 0), is_league: false },
        player2: { name: 'Ann', game_wins: 1, record: rec(0, 0, 1), is_league: true } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-2');
  assert.deepEqual(board.map(r => r.name), ['Ann']);
  assert.equal(board[0].points, 3); // 2nd(2) + 0 + attendance 1
});

test('a non-summer season still uses 3*wins + draws', () => {
  const t = { id: 't', date: '2026-04-12', rounds: [
    { round: 1, pairings: [
      { pairing: 1, player1: { name: 'Ann', game_wins: 2, record: rec(1, 0, 0) }, player2: { name: 'Bob', game_wins: 1, record: rec(0, 0, 1) } },
    ] },
  ] };
  const board = seasonLeaderboard([t], '2026-1');
  assert.deepEqual(board.map(r => [r.name, r.points]), [['Ann', 3], ['Bob', 0]]);
});
