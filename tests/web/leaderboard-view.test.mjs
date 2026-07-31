import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderLeaderboard } from '../../web/ui/leaderboard-view.js';

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
