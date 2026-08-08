import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderLeaderboard, renderBreakdown } from '../../web/ui/leaderboard-view.js';

test('renders ranked rows with names, initials, and preserves order', () => {
  const html = renderLeaderboard([
    { name: 'Ann Lee', points: 9, events: 3 },
    { name: 'Bob', points: 3, events: 1 },
  ]);
  assert.match(html, /Ann Lee/);
  assert.match(html, /AL/);
  assert.match(html, />1</);
  assert.ok(html.indexOf('Ann Lee') < html.indexOf('Bob'));
});

test('shows an empty state when there are no rows', () => {
  assert.match(renderLeaderboard([]), /No results/);
});

test('renderLeaderboard adds one breakdown button per row', () => {
  const html = renderLeaderboard([
    { name: 'Ann Lee', points: 9, events: 1, breakdown: [] },
    { name: 'Bob', points: 3, events: 1, breakdown: [] },
  ]);
  assert.equal((html.match(/class="why"/g) || []).length, 2);
  assert.match(html, /data-index="0"/);
  assert.match(html, /data-index="1"/);
});

test('renderBreakdown lists tournaments, items, subtotals and total', () => {
  const row = { name: 'Ann', points: 9, events: 1, breakdown: [
    { tournament: 'Showdown', date: '2026-07-10', items: [
      { label: '1st place', points: 3 },
      { label: '2 wins (×2)', points: 4 },
      { label: 'attendance', points: 1 },
    ], subtotal: 8 },
    { tournament: 'Store', date: '2026-08-01', items: [{ label: 'attendance', points: 1 }], subtotal: 1 },
  ] };
  const html = renderBreakdown(row);
  assert.match(html, /Ann — 9 pts/);
  assert.match(html, /Showdown · 2026-07-10/);
  assert.match(html, /1st place/);
  assert.match(html, /\+4/);
  assert.match(html, /Store · 2026-08-01/);
  assert.match(html, /Total/);
});
