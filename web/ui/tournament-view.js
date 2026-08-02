function recordChip(record) {
  return `<span class="chip">${record.wins}-${record.draws}-${record.losses}</span>`;
}

const MARK = '<span class="mark">✓</span>';

const MANA = new Set(['W', 'U', 'B', 'R', 'G']);

function manaIcons(colours) {
  if (!colours) return '';
  return [...colours.toUpperCase()]
    .filter(c => MANA.has(c))
    .map(c => `<img class="mana" src="icons/mana/${c}.svg" alt="${c}" />`)
    .join('');
}

function deckInfo(player) {
  const icons = manaIcons(player.deck_colours);
  const name = player.deck ? `<span class="deck-name">${player.deck}</span>` : '';
  return icons + name;
}

function leagueTag(player) {
  return player.is_league === false
    ? '<span class="non-league">Not from League</span>'
    : '';
}

function pairingRow(pairing) {
  const p1 = pairing.player1;
  if (!pairing.player2) {
    return (
      `<div class="pairing bye">` +
      `<div class="side win">${MARK}<span class="name">${p1.name}</span>${deckInfo(p1)}${leagueTag(p1)}${recordChip(p1.record)}</div>` +
      `<div class="score">Bye</div>` +
      `<div class="side right"></div>` +
      `</div>`
    );
  }
  const p2 = pairing.player2;
  const p1Won = p1.game_wins > p2.game_wins;
  const p2Won = p2.game_wins > p1.game_wins;
  return (
    `<div class="pairing">` +
    `<div class="side ${p1Won ? 'win' : ''}">${p1Won ? MARK : ''}<span class="name">${p1.name}</span>${deckInfo(p1)}${leagueTag(p1)}${recordChip(p1.record)}</div>` +
    `<div class="score">${p1.game_wins}-${p2.game_wins}</div>` +
    `<div class="side right ${p2Won ? 'win' : ''}">${recordChip(p2.record)}<span class="name">${p2.name}</span>${deckInfo(p2)}${leagueTag(p2)}${p2Won ? MARK : ''}</div>` +
    `</div>`
  );
}

function isStandingsEvent(tournament) {
  const pairings = tournament.rounds.flatMap(round => round.pairings);
  return pairings.length > 0 && pairings.every(pairing => pairing.player2 === null);
}

function renderStandings(tournament) {
  const players = tournament.rounds
    .flatMap(round => round.pairings)
    .map(pairing => ({ rank: pairing.pairing, player: pairing.player1 }))
    .sort((a, b) => a.rank - b.rank);
  const header =
    `<div class="t-header"><div class="t-name">${tournament.name}</div>` +
    `<div class="t-meta">${tournament.date} · ${players.length} players</div></div>`;
  const head =
    '<div class="row head"><div>#</div><div>Player</div>' +
    '<div class="num">Record</div><div class="num">Points</div></div>';
  const body = players
    .map(({ rank, player }) => {
      const r = player.record;
      const points = r.wins * 3 + r.draws;
      return (
        `<div class="row">` +
        `<div class="rank">${rank}</div>` +
        `<div class="player">${player.name}${deckInfo(player)}${leagueTag(player)}</div>` +
        `<div class="num">${r.wins}-${r.draws}-${r.losses}</div>` +
        `<div class="num strong">${points}</div>` +
        `</div>`
      );
    })
    .join('');
  return header + head + body;
}

export function renderTournament(tournament) {
  if (isStandingsEvent(tournament)) return renderStandings(tournament);
  const header =
    `<div class="t-header"><div class="t-name">${tournament.name}</div>` +
    `<div class="t-meta">${tournament.date} · ${tournament.rounds.length} rounds</div></div>`;
  const rounds = tournament.rounds
    .map(round => {
      const pairings = round.pairings.map(pairingRow).join('');
      return `<div class="round-label">Round ${round.round}</div>${pairings}`;
    })
    .join('');
  return header + rounds;
}
