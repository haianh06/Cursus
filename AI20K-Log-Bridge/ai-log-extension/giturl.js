/*
 * Turns whatever the user pastes into owner/name (and a branch, when the link
 * carries one).
 *
 * The config used to ask for the pieces separately — owner/name here, branch
 * there — which is both more typing and more ways to be silently wrong. People
 * have the URL in their address bar; take that instead.
 *
 * Loaded in the service worker (importScripts), the popup, and the node tests.
 */
var AILOG_GITURL = AILOG_GITURL || (function () {
  'use strict';

  // GitHub allows letters, digits, dot, dash, underscore in owner and name.
  var SEGMENT = /^[A-Za-z0-9._-]+$/;

  function clean(s) {
    return String(s == null ? '' : s).trim();
  }

  /* Accepts:
       https://github.com/owner/repo
       https://github.com/owner/repo.git
       https://github.com/owner/repo/tree/main
       https://github.com/owner/repo/tree/feature/x/src   (branch + path)
       https://github.com/owner/repo/blob/main/README.md
       git@github.com:owner/repo.git
       ssh://git@github.com/owner/repo.git
       github.com/owner/repo
       owner/repo
     Returns { ok, slug, owner, name, branchHint }.
     branchHint may include trailing path segments — GitHub URLs give no way to
     tell "feature/x" from "feature" + "/x" — so resolveBranchHint() settles it
     against the real branch list later. */
  function parseRepoUrl(input) {
    var raw = clean(input);
    if (!raw) return { ok: false, error: 'Chưa nhập link repo.' };

    // Strip query and fragment before anything else.
    raw = raw.split('#')[0].split('?')[0];

    var rest = raw;

    // scp-like: git@github.com:owner/repo.git
    var scp = /^(?:ssh:\/\/)?(?:[^@\s]+@)?github\.com[:/](.+)$/i.exec(rest);
    if (scp) {
      rest = scp[1];
    } else {
      rest = rest.replace(/^[a-z+]+:\/\//i, '');            // scheme
      rest = rest.replace(/^[^@/\s]+@/, '');                // user@
      var host = /^(?:www\.)?github\.com\/(.+)$/i.exec(rest);
      if (host) {
        rest = host[1];
      } else if (/^[a-z0-9.-]+\.[a-z]{2,}\//i.test(rest)) {
        // Some other host — the GitHub API cannot answer for it, and guessing
        // would produce a confidently wrong repo.
        return { ok: false, error: 'Chỉ hỗ trợ github.com (link này thuộc host khác).' };
      }
    }

    rest = rest.replace(/^\/+/, '').replace(/\/+$/, '');
    if (!rest) return { ok: false, error: 'Link không có owner/repo.' };

    var parts = rest.split('/');
    if (parts.length < 2) {
      return { ok: false, error: 'Thiếu tên repo. Dạng đúng: owner/repo.' };
    }

    var owner = parts[0];
    var name = parts[1].replace(/\.git$/i, '');
    if (!SEGMENT.test(owner) || !SEGMENT.test(name)) {
      return { ok: false, error: 'Owner hoặc tên repo không hợp lệ.' };
    }

    var branchHint = '';
    if (parts.length > 3 && /^(tree|blob|commits)$/i.test(parts[2])) {
      branchHint = parts.slice(3).join('/');
    }

    return {
      ok: true,
      slug: owner + '/' + name,
      owner: owner,
      name: name,
      branchHint: branchHint,
    };
  }

  /* A hint like "feature/x/src/app.js" could be branch "feature" or
     "feature/x". Longest real branch that the hint starts with wins. */
  function resolveBranchHint(hint, names) {
    hint = clean(hint);
    if (!hint || !names || !names.length) return '';
    var best = '';
    for (var i = 0; i < names.length; i++) {
      var n = names[i];
      if (!n) continue;
      if (hint === n || hint.indexOf(n + '/') === 0) {
        if (n.length > best.length) best = n;
      }
    }
    return best;
  }

  return { parseRepoUrl: parseRepoUrl, resolveBranchHint: resolveBranchHint };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = AILOG_GITURL;
