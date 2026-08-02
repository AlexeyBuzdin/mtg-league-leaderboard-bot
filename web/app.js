import { seasonKey, seasonLabel } from './lib/season.js';
import { seasonLeaderboard } from './lib/leaderboard.js';
import { renderLeaderboard } from './ui/leaderboard-view.js';
import { renderTournament } from './ui/tournament-view.js';

const state = { tournaments: [] };

async function boot() {
  try {
    const response = await fetch('data/tournaments.json');
    if (!response.ok) throw new Error('bad status');
    state.tournaments = (await response.json()).tournaments;
  } catch {
    const message = '<div class="empty">Couldn\'t load data.</div>';
    document.getElementById('lb-body').innerHTML = message;
    document.getElementById('td-body').innerHTML = message;
    return;
  }
  setupTabs();
  setupLeaderboard();
  setupTournaments();
}

function setupTabs() {
  const tabLb = document.getElementById('tab-lb');
  const tabTd = document.getElementById('tab-td');
  const viewLb = document.getElementById('view-lb');
  const viewTd = document.getElementById('view-td');
  function show(which) {
    const isLb = which === 'lb';
    viewLb.hidden = !isLb;
    viewTd.hidden = isLb;
    tabLb.setAttribute('aria-selected', String(isLb));
    tabTd.setAttribute('aria-selected', String(!isLb));
  }
  tabLb.addEventListener('click', () => show('lb'));
  tabTd.addEventListener('click', () => show('td'));
}

function setupLeaderboard() {
  const select = document.getElementById('q-sel');
  const byKey = new Map();
  for (const t of state.tournaments) byKey.set(seasonKey(t.date), seasonLabel(t.date));
  const keys = [...byKey.keys()].sort().reverse();
  select.innerHTML = keys
    .map(k => `<option value="${k}">${byKey.get(k)}</option>`)
    .join('');
  function render() {
    const key = select.value;
    const rows = seasonLeaderboard(state.tournaments, key);
    const count = state.tournaments.filter(t => seasonKey(t.date) === key).length;
    document.getElementById('q-meta').textContent =
      `${count} tournaments · ${rows.length} players`;
    document.getElementById('lb-body').innerHTML = renderLeaderboard(rows);
  }
  select.addEventListener('change', render);
  render();
}

function setupTournaments() {
  const select = document.getElementById('t-sel');
  const sorted = [...state.tournaments].sort((a, b) => b.date.localeCompare(a.date));
  select.innerHTML = sorted
    .map(t => `<option value="${t.id}">${t.date} — ${t.name}</option>`)
    .join('');
  function render() {
    const tournament = state.tournaments.find(t => t.id === select.value);
    document.getElementById('td-body').innerHTML = renderTournament(tournament);
  }
  select.addEventListener('change', render);
  render();
}

boot();
