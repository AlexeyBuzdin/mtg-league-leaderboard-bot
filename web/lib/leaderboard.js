import { quarterKey } from './quarter.js';

export function finalRecords(tournament) {
  const last = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      last[pairing.player1.name] = pairing.player1.record;
      if (pairing.player2) {
        last[pairing.player2.name] = pairing.player2.record;
      }
    }
  }
  return last;
}

export function points(record) {
  return record.wins * 3 + record.draws;
}

export function quarterLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (quarterKey(tournament.date) !== key) continue;
    const finals = finalRecords(tournament);
    for (const [name, record] of Object.entries(finals)) {
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += points(record);
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
