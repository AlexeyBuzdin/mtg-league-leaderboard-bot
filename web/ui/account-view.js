import { renderProfile } from './profile-view.js';

function initials(name) {
  return name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

// Account page. `user` is { name, email, avatarUrl } or null (signed out);
// `linked` is { name, profile, seasons, selectedSeason } or null (not linked).
// Pure HTML string; sign-in / sign-out / season controls are wired in app.js.
export function renderAccount(user, linked) {
  const back = '<a class="back-link" href="#">← Back</a>';
  if (!user) {
    return back +
      '<div class="account">' +
      '<h1 class="profile-name">Your account</h1>' +
      '<p class="profile-empty">Sign in to view your account.</p>' +
      '<div class="signin-options">' +
      '<button class="auth-signin" type="button" data-provider="discord">Sign in with Discord</button>' +
      '<button class="auth-signin" type="button" data-provider="google">Sign in with Google</button>' +
      '</div></div>';
  }
  const avatar = user.avatarUrl
    ? `<img class="account-avatar" src="${user.avatarUrl}" alt="" referrerpolicy="no-referrer" />`
    : `<span class="avatar">${initials(user.name)}</span>`;
  const head =
    '<div class="account">' +
    `<div class="account-head">${avatar}` +
    `<div><h1 class="profile-name">${user.name}</h1>` +
    `<div class="account-email">${user.email ?? ''}</div></div></div>` +
    '<button id="signout-btn" class="auth-signin" type="button">Sign out</button>' +
    '</div>';
  // Linked → embed the player's full profile (no duplicate back link); else the
  // admin-link prompt.
  const body = linked
    ? '<div class="account-profile">' +
      renderProfile(linked.name, linked.profile, linked.seasons, linked.selectedSeason,
        { showBack: false, achievements: linked.achievements ?? [] }) +
      '</div>'
    : '<p class="profile-empty">Not linked yet — ask an admin to link your account to a player.</p>';
  return back + head + body;
}
