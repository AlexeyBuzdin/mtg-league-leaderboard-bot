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
        `<div class="num strong">${row.points}<button class="why" data-index="${index}" aria-label="Points breakdown for ${row.name}">?</button></div>` +
        `</div>`
      );
    })
    .join('');
  return head + body;
}

export function renderBreakdown(row) {
  const sections = row.breakdown
    .map(t => {
      const items = t.items
        .map(it => `<div class="bd-item"><span>${it.label}</span><span>+${it.points}</span></div>`)
        .join('');
      return (
        `<div class="bd-tournament">${t.tournament} · ${t.date}</div>` +
        items +
        `<div class="bd-subtotal"><span>subtotal</span><span>${t.subtotal}</span></div>`
      );
    })
    .join('');
  return (
    `<div class="bd-head">${row.name} — ${row.points} pts</div>` +
    `<div class="bd-body">${sections}` +
    `<div class="bd-total"><span>Total</span><span>${row.points}</span></div></div>`
  );
}
