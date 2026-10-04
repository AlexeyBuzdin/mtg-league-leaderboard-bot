import { seasonKey, seasonLabel, tournamentsForSeason } from './lib/season.js';
import { seasonLeaderboard, seasonLeaderboardBefore } from './lib/leaderboard.js';
import { renderLeaderboard, renderBreakdown, sortLeaderboard, computeMovements } from './ui/leaderboard-view.js';
import { renderTournament } from './ui/tournament-view.js';
import { renderRules } from './ui/rules.js';
import { renderLeagueRules } from './ui/league-rules.js';
import { renderProfile } from './ui/profile-view.js';
import { playerProfile, attendedDates } from './lib/player-stats.js';
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from './config.js';
import { loadSiteData } from './lib/supabase-data.js';
import { associatedName } from './lib/association.js';
import { renderAuthControl } from './ui/auth-control.js';
import { renderAccount } from './ui/account-view.js';
import { currentUser, onUserChange, signInWithProvider, signOut, associatedPlayerKey } from './lib/auth.js';
import { isWithinDays, normalizeColours } from './lib/deck.js';
import { saveDeck } from './lib/deck-edit.js';

const state = {
  tournaments: [], achievements: new Map(), players: [], user: null, associatedName: null,
  renderLeaderboard: null, showAccount: null, renderTournamentView: null,
};

const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const redirectTo = () => location.origin + location.pathname;

async function refreshViewer() {
  state.user = await currentUser(client);
  const key = state.user ? await associatedPlayerKey(client) : null;
  state.associatedName = associatedName(key ? { player_key: key } : null, state.players);
  document.getElementById('auth-control').innerHTML = renderAuthControl(state.user);
}

async function boot() {
  try {
    const data = await loadSiteData(client);
    state.tournaments = data.tournaments;
    state.players = data.players;
    state.achievements = data.achievements;
  } catch {
    const message = '<div class="empty">Couldn\'t load data.</div>';
    document.getElementById('lb-body').innerHTML = message;
    document.getElementById('td-body').innerHTML = message;
    return;
  }

  await refreshViewer();
  setupTabs();
  setupLeaderboard();
  setupTournaments();
  setupRules();
  document.getElementById('rules-view').innerHTML = renderLeagueRules();

  onUserChange(client, async () => {
    await refreshViewer();
    if (state.renderLeaderboard) state.renderLeaderboard();
    if (state.renderTournamentView) state.renderTournamentView();
    if (location.hash === '#account' && state.showAccount) state.showAccount();
  });
}

const SUMMER_2026 = '2026-2';

function setupRules() {
  const btn = document.getElementById('rules-btn');
  const modal = document.getElementById('rules-modal');
  const seasonSelect = document.getElementById('q-sel');
  document.getElementById('rules-content').innerHTML = renderRules();
  const open = () => { modal.hidden = false; };
  const close = () => { modal.hidden = true; };
  // The rules are Summer-2026 specific, so only show the button for that season.
  const syncVisibility = () => {
    const isSummer = seasonSelect.value === SUMMER_2026;
    btn.hidden = !isSummer;
    if (!isSummer) close();
  };
  btn.addEventListener('click', open);
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-close]')) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') close();
  });
  seasonSelect.addEventListener('change', syncVisibility);
  syncVisibility();
}

function setupTabs() {
  const tabs = [
    { btn: 'tab-lb', view: 'view-lb' },
    { btn: 'tab-td', view: 'view-td' },
    { btn: 'tab-rules', view: 'view-rules' },
  ].map(t => ({ btn: document.getElementById(t.btn), view: document.getElementById(t.view) }));
  const profileView = document.getElementById('view-profile');
  const accountView = document.getElementById('view-account');
  let active = tabs[0];
  let profileName = null;

  function showActiveTab() {
    profileView.hidden = true;
    accountView.hidden = true;
    for (const t of tabs) {
      const on = t === active;
      t.view.hidden = !on;
      t.btn.setAttribute('aria-selected', String(on));
    }
  }
  function seasonsForPlayer(name) {
    const byKey = new Map();
    for (const date of attendedDates(state.tournaments, name)) byKey.set(seasonKey(date), seasonLabel(date));
    return [...byKey.entries()]
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([key, label]) => ({ key, label }));
  }
  function renderProfileFor(name, season) {
    const tournaments = season === 'all'
      ? state.tournaments
      : state.tournaments.filter(t => seasonKey(t.date) === season);
    profileView.innerHTML = renderProfile(
      name, playerProfile(tournaments, name), seasonsForPlayer(name), season,
      { achievements: state.achievements.get(name) ?? [] },
    );
  }
  function showProfile(name) {
    profileName = name;
    for (const t of tabs) t.view.hidden = true;
    accountView.hidden = true;
    renderProfileFor(name, 'all');
    profileView.hidden = false;
    window.scrollTo(0, 0);
  }
  // The linked player's profile for the embedded Account view (season filtered).
  function linkedFor(season) {
    const name = state.associatedName;
    if (!name) return null;
    const tournaments = season === 'all'
      ? state.tournaments
      : state.tournaments.filter(t => seasonKey(t.date) === season);
    return {
      name, profile: playerProfile(tournaments, name),
      seasons: seasonsForPlayer(name), selectedSeason: season,
      achievements: state.achievements.get(name) ?? [],
    };
  }
  function showAccount() {
    for (const t of tabs) t.view.hidden = true;
    profileView.hidden = true;
    accountView.innerHTML = renderAccount(state.user, linkedFor('all'));
    accountView.hidden = false;
    window.scrollTo(0, 0);
  }
  state.showAccount = showAccount;
  accountView.addEventListener('change', event => {
    if (event.target.id === 'profile-season' && state.associatedName) {
      accountView.innerHTML = renderAccount(state.user, linkedFor(event.target.value));
    }
  });
  accountView.addEventListener('click', event => {
    const provider = event.target.closest('[data-provider]');
    if (provider) signInWithProvider(client, provider.dataset.provider, redirectTo());
    if (event.target.closest('#signout-btn')) signOut(client);
  });
  profileView.addEventListener('change', event => {
    if (event.target.id === 'profile-season' && profileName) {
      renderProfileFor(profileName, event.target.value);
    }
  });
  function route() {
    const match = location.hash.match(/^#player\/(.+)$/);
    if (match) showProfile(decodeURIComponent(match[1]));
    else if (location.hash === '#account') showAccount();
    else showActiveTab();
  }
  for (const t of tabs) {
    t.btn.addEventListener('click', () => {
      active = t;
      // Leaving a profile/account: clearing the hash re-routes to the active tab.
      if (location.hash.startsWith('#player/') || location.hash === '#account') location.hash = '';
      else showActiveTab();
    });
  }
  window.addEventListener('hashchange', route);
  route();
}

function setupLeaderboard() {
  const select = document.getElementById('q-sel');
  const body = document.getElementById('lb-body');
  const pop = document.getElementById('breakdown-popover');
  let currentRows = [];
  const sort = { col: 'points', dir: 'desc' };

  const byKey = new Map();
  for (const t of state.tournaments) byKey.set(seasonKey(t.date), seasonLabel(t.date));
  const keys = [...byKey.keys()].sort().reverse();
  select.innerHTML = keys
    .map(k => `<option value="${k}">${byKey.get(k)}</option>`)
    .join('');

  function hidePopover() {
    pop.hidden = true;
    delete pop.dataset.index;
  }

  function render() {
    const key = select.value;
    currentRows = sortLeaderboard(seasonLeaderboard(state.tournaments, key), sort);
    const before = seasonLeaderboardBefore(state.tournaments, key);
    const previousRows = sortLeaderboard(before.rows, sort);
    const moves = computeMovements(currentRows, previousRows, before.hasPrevious);
    const count = state.tournaments.filter(t => seasonKey(t.date) === key).length;
    document.getElementById('q-meta').textContent =
      `${count} tournaments · ${currentRows.length} players`;
    body.innerHTML = renderLeaderboard(currentRows, sort, moves, state.associatedName);
    hidePopover();
  }

  body.addEventListener('click', event => {
    const sortBtn = event.target.closest('.sort');
    if (sortBtn) {
      const col = sortBtn.dataset.sort;
      if (sort.col === col) sort.dir = sort.dir === 'desc' ? 'asc' : 'desc';
      else { sort.col = col; sort.dir = 'desc'; }
      render();
      return;
    }
    const btn = event.target.closest('.why');
    if (!btn) return;
    event.stopPropagation();
    if (!pop.hidden && pop.dataset.index === btn.dataset.index) {
      hidePopover();
      return;
    }
    pop.innerHTML = renderBreakdown(currentRows[Number(btn.dataset.index)]);
    pop.dataset.index = btn.dataset.index;
    pop.hidden = false;
    const rect = btn.getBoundingClientRect();
    pop.style.top = `${window.scrollY + rect.bottom + 6}px`;
    let left = window.scrollX + rect.left;
    const maxLeft = window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    pop.style.left = `${left}px`;
  });

  document.addEventListener('click', event => {
    if (pop.hidden) return;
    if (pop.contains(event.target) || event.target.closest('.why')) return;
    hidePopover();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') hidePopover();
  });

  select.addEventListener('change', render);
  state.renderLeaderboard = render;
  render();
}

function setupTournaments() {
  const seasonSelect = document.getElementById('td-season');
  const select = document.getElementById('t-sel');

  const byKey = new Map();
  for (const t of state.tournaments) byKey.set(seasonKey(t.date), seasonLabel(t.date));
  const keys = [...byKey.keys()].sort().reverse();
  seasonSelect.innerHTML = keys
    .map(k => `<option value="${k}">${byKey.get(k)}</option>`)
    .join('');

  function populateTournaments() {
    const list = tournamentsForSeason(state.tournaments, seasonSelect.value);
    select.innerHTML = list
      .map(t => `<option value="${t.id}">${t.date} — ${t.name}</option>`)
      .join('');
  }
  const body = document.getElementById('td-body');

  function viewerFor(tournament) {
    if (!state.user || !state.associatedName) return null;
    return {
      name: state.associatedName,
      editable: isWithinDays(tournament.date, new Date(), 7),
    };
  }
  function render() {
    const tournament = state.tournaments.find(t => t.id === select.value);
    body.innerHTML = tournament
      ? renderTournament(tournament, viewerFor(tournament))
      : '<div class="empty">No tournaments this season.</div>';
  }

  body.addEventListener('click', async event => {
    const pip = event.target.closest('.pip-toggle');
    if (pip) {
      const on = pip.classList.toggle('selected');
      pip.setAttribute('aria-pressed', String(on));
      return;
    }
    if (!event.target.closest('#deck-save')) return;
    const tournament = state.tournaments.find(t => t.id === select.value);
    if (!tournament) return;
    const colours = normalizeColours(
      [...body.querySelectorAll('.pip-toggle.selected')].map(p => p.dataset.pip),
    );
    const deckName = body.querySelector('#deck-name').value;
    const status = body.querySelector('#deck-status');
    const saveBtn = body.querySelector('#deck-save');
    status.textContent = 'Saving…';
    saveBtn.disabled = true;
    try {
      await saveDeck(client, { tournamentId: tournament.id, deckName, deckColours: colours });
      const data = await loadSiteData(client);
      state.tournaments = data.tournaments;
      state.players = data.players;
      state.achievements = data.achievements;
      render();
      if (state.renderLeaderboard) state.renderLeaderboard();
    } catch {
      status.textContent = "Couldn't save. Try again.";
      saveBtn.disabled = false;
    }
  });

  seasonSelect.addEventListener('change', () => { populateTournaments(); render(); });
  select.addEventListener('change', render);
  populateTournaments();
  state.renderTournamentView = render;
  render();
}

boot();
