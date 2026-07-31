function recordChip(record) {
  return `<span class="chip">${record.wins}-${record.draws}-${record.losses}</span>`;
}

const MARK = '<span class="mark">✓</span>';

function pairingRow(pairing) {
  const p1 = pairing.player1;
  if (!pairing.player2) {
    return (
      `<div class="pairing bye">` +
      `<div class="side win">${MARK}<span class="name">${p1.name}</span>${recordChip(p1.record)}</div>` +
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
    `<div class="side ${p1Won ? 'win' : ''}">${p1Won ? MARK : ''}<span class="name">${p1.name}</span>${recordChip(p1.record)}</div>` +
    `<div class="score">${p1.game_wins}-${p2.game_wins}</div>` +
    `<div class="side right ${p2Won ? 'win' : ''}">${recordChip(p2.record)}<span class="name">${p2.name}</span>${p2Won ? MARK : ''}</div>` +
    `</div>`
  );
}

export function renderTournament(tournament) {
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
