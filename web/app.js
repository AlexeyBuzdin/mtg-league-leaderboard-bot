import { quarterKey } from './lib/quarter.js';
import { quarterLeaderboard } from './lib/leaderboard.js';
import { renderLeaderboard } from './ui/leaderboard-view.js';
import { renderTournament } from './ui/tournament-view.js';

const state = { tournaments: [] };

async function boot() {
  try {
    const response = await fetch('data/mock-tournaments.json');
    if (!response.ok) throw new Error('bad status');
    state.tournaments = (await response.json()).tournaments;
  } catch {
    document.getElementById('lb-body').innerHTML =
      '<div class="empty">Couldn\'t load data.</div>';
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
  const quarters = [...new Set(state.tournaments.map(t => quarterKey(t.date)))]
    .sort()
    .reverse();
  select.innerHTML = quarters
    .map(q => `<option value="${q}">${q.replace('-', ' · ')}</option>`)
    .join('');
  function render() {
    const key = select.value;
    const rows = quarterLeaderboard(state.tournaments, key);
    const count = state.tournaments.filter(t => quarterKey(t.date) === key).length;
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
