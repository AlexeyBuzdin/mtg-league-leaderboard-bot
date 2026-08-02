import { seasonKey } from './season.js';

function playerEntry(player) {
  return { record: player.record, isLeague: player.is_league !== false };
}

export function finalRecords(tournament) {
  const last = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      last[pairing.player1.name] = playerEntry(pairing.player1);
      if (pairing.player2) {
        last[pairing.player2.name] = playerEntry(pairing.player2);
      }
    }
  }
  return last;
}

export function points(record) {
  return record.wins * 3 + record.draws;
}

export function seasonLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (seasonKey(tournament.date) !== key) continue;
    const finals = finalRecords(tournament);
    for (const [name, entry] of Object.entries(finals)) {
      if (!entry.isLeague) continue;
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += points(entry.record);
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
