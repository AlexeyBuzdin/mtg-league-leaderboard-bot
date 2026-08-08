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

function accumulate(stats, player) {
  const s = stats[player.name] || { record: null, gameWins: 0, isLeague: true };
  s.record = player.record; // rounds are in order, so this ends as the final record
  s.gameWins += player.game_wins || 0;
  s.isLeague = player.is_league !== false;
  stats[player.name] = s;
}

export function playerTournamentStats(tournament) {
  const stats = {};
  for (const round of tournament.rounds) {
    for (const pairing of round.pairings) {
      accumulate(stats, pairing.player1);
      if (pairing.player2) accumulate(stats, pairing.player2);
    }
  }
  return stats;
}

export function tournamentScores(tournament) {
  const stats = playerTournamentStats(tournament);
  const summer = seasonKey(tournament.date) === '2026-2';
  const ranked = Object.entries(stats)
    .map(([name, s]) => ({ name, ...s, mp: points(s.record) }))
    .sort((a, b) => b.mp - a.mp || b.gameWins - a.gameWins || a.name.localeCompare(b.name));
  const bonus = [3, 2, 1];
  const scores = {};
  ranked.forEach((p, i) => {
    if (summer) {
      const placement = i < 3 ? bonus[i] : 0;
      scores[p.name] = { score: placement + 2 * p.record.wins + p.record.draws + 1, isLeague: p.isLeague };
    } else {
      scores[p.name] = { score: points(p.record), isLeague: p.isLeague };
    }
  });
  return scores;
}

export function seasonLeaderboard(tournaments, key) {
  const agg = {};
  for (const tournament of tournaments) {
    if (seasonKey(tournament.date) !== key) continue;
    const scored = tournamentScores(tournament);
    for (const [name, { score, isLeague }] of Object.entries(scored)) {
      if (!isLeague) continue;
      if (!agg[name]) agg[name] = { name, points: 0, events: 0 };
      agg[name].points += score;
      agg[name].events += 1;
    }
  }
  return Object.values(agg).sort(
    (a, b) => b.points - a.points || a.name.localeCompare(b.name),
  );
}
