// EduSync is always opened FROM Cursus in a new tab (Cursus's own Topbar
// link, target="_blank" -- see frontend/src/App.jsx), never navigated to
// directly in the same tab under normal use. That means the original Cursus
// tab, with whatever the user was doing there, is still open and untouched
// in the background -- following href={cursusUrl} in THIS tab would throw
// that state away and load a second, independent copy of Cursus instead of
// just returning to the one that's already there.
//
// window.opener is only set when this tab was itself opened by script from
// another same-origin-capable tab (exactly the target="_blank" case above),
// so closing it is the right move there. But window.close() is only
// GUARANTEED to work on a tab with no real navigation history -- and this
// app's own client-side router (App.tsx's `navigate()`) calls
// `history.pushState` on every internal click, so by the time a user has
// browsed a couple of screens before hitting "Back to Cursus", Chrome
// silently refuses to close the tab at all (no error, it just stays open).
// There's no synchronous way to know whether close() succeeded, so the
// fallback below checks `window.closed` on the next tick and only then
// falls back to a same-tab navigation -- that way a fresh tab (no
// navigation yet) closes cleanly, and a browsed-around tab still gets the
// user back to Cursus instead of leaving a dead click.
export function handleBackToCursusClick(e: React.MouseEvent<HTMLAnchorElement>, cursusUrl: string) {
  if (!window.opener) return;
  e.preventDefault();
  window.close();
  setTimeout(() => {
    if (!window.closed) window.location.href = cursusUrl;
  }, 250);
}
