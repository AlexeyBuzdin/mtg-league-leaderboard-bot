import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderProfile } from '../../web/ui/profile-view.js';
import { playerLink } from '../../web/ui/player-link.js';

test('playerLink encodes the name in the href and shows it as text', () => {
  const html = playerLink('Sergey P');
  assert.match(html, /href="#player\/Sergey%20P"/);
  assert.match(html, />Sergey P<\/a>/);
  assert.match(html, /class="player-link"/);
});

test('playerLink adds an extra class when given', () => {
  assert.match(playerLink('Ann', 'pname'), /class="player-link pname"/);
});

const profile = {
  tournaments: 3,
  record: { wins: 6, draws: 1, losses: 2 },
  placements: { first: 2, second: 1, third: 0 },
  colours: { top: ['W', 'U'], pct: 60 },
  decks: [{ deck: 'Azorius Flash', colours: 'WU', tournaments: 2 }, { deck: 'Mono Red', colours: 'R', tournaments: 1 }],
  rivals: [{ name: 'Bob', losses: 3 }, { name: 'Cara', losses: 1 }],
  friends: [{ name: 'Bob', games: 5 }, { name: 'Dan', games: 2 }],
};

test('renders header, placements, decks, rivals and friends', () => {
  const html = renderProfile('Ann', profile);
  assert.match(html, /Ann/);
  assert.match(html, /3 tournaments/);
  assert.match(html, /6.1.2/); // 6-1-2 record
  assert.match(html, /Azorius Flash/);
  assert.match(html, /2 tournaments/);
  // deck colours render as mana pips after the deck name (W then U)
  const deckPos = html.indexOf('Azorius Flash');
  const wAfter = html.indexOf('icons/mana/W.svg', deckPos);
  const uAfter = html.indexOf('icons/mana/U.svg', deckPos);
  assert.ok(wAfter > deckPos && wAfter < uAfter);
  assert.match(html, /Bob/);
  assert.match(html, /3 losses/);
  assert.match(html, /5 games/);
  // placement counts present
  assert.match(html, />2</);
  assert.match(html, />1</);
  // most-played colours shown in the placements section with a whole-percent share
  assert.match(html, /class="placement fav-colours"/);
  assert.match(html, /60%/);
});

test('renders a season picker with Overall plus the player seasons', () => {
  const seasons = [{ key: '2026-2', label: 'Summer 2026' }, { key: '2026-1', label: 'Spring 2026' }];
  const html = renderProfile('Ann', profile, seasons, '2026-2');
  assert.match(html, /id="profile-season"/);
  assert.match(html, /<option value="all">Overall<\/option>/);
  assert.match(html, /<option value="2026-2" selected>Summer 2026<\/option>/);
  assert.match(html, /Spring 2026/);
});

test('no season picker when the player has no seasons', () => {
  assert.ok(!renderProfile('Ann', profile).includes('profile-season'));
});

test('shows empty states for decks and head-to-head', () => {
  const html = renderProfile('New', {
    tournaments: 1, record: { wins: 0, draws: 0, losses: 3 },
    placements: { first: 0, second: 0, third: 0 }, decks: [], rivals: [], friends: [],
  });
  assert.match(html, /No decks recorded/);
  assert.match(html, /No head-to-head data/);
});

test('unknown player (no tournaments) shows a friendly message', () => {
  const html = renderProfile('Ghost', {
    tournaments: 0, record: { wins: 0, draws: 0, losses: 0 },
    placements: { first: 0, second: 0, third: 0 }, decks: [], rivals: [], friends: [],
  });
  assert.match(html, /No data for this player/);
});

test('renderProfile omits the back link when showBack is false (embedded)', () => {
  const profile = {
    tournaments: 2, record: { wins: 3, draws: 0, losses: 1 },
    placements: { first: 1, second: 0, third: 0 }, colours: { top: [], pct: 0 },
    decks: [], rivals: [], friends: [],
  };
  const withBack = renderProfile('Ann', profile, [], 'all');
  const embedded = renderProfile('Ann', profile, [], 'all', { showBack: false });
  assert.ok(withBack.includes('class="back-link"'));
  assert.ok(!embedded.includes('class="back-link"'));
  assert.ok(embedded.includes('Placements')); // body still rendered
});

test('renders achievements as badges before placements when present', () => {
  const html = renderProfile('Ann', profile, [], 'all', {
    achievements: ['🏆Summer 2026', '🥈Spring 2026'],
  });
  assert.match(html, /class="profile-section">Achievements</);
  assert.match(html, /class="achievement">🏆Summer 2026</);
  assert.ok(html.indexOf('Achievements') < html.indexOf('Placements'));
  assert.ok(html.indexOf('🏆Summer 2026') < html.indexOf('Placements'));
});

test('omits the achievements section when there are none', () => {
  const html = renderProfile('Ann', profile);
  assert.ok(!html.includes('Achievements'));
});
