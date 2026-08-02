function initials(name) {
  return name
    .split(/\s+/)
    .map(word => word[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export function renderLeaderboard(rows) {
  if (rows.length === 0) {
    return '<div class="empty">No results for this season.</div>';
  }
  const medal = ['#BA7517', '#888780', '#993C1D'];
  const head =
    '<div class="row head"><div>#</div><div>Player</div>' +
    '<div class="num">Events</div><div class="num">Points</div></div>';
  const body = rows
    .map((row, index) => {
      const rank = index + 1;
      const color = medal[index] || 'var(--muted)';
      return (
        `<div class="row">` +
        `<div class="rank" style="color:${color}">${rank}</div>` +
        `<div class="player"><span class="avatar">${initials(row.name)}</span>${row.name}</div>` +
        `<div class="num">${row.events}</div>` +
        `<div class="num strong">${row.points}</div>` +
        `</div>`
      );
    })
    .join('');
  return head + body;
}
