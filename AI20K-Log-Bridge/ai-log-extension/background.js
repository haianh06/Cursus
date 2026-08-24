/*
 * Service worker: the only component that touches the network.
 *
 * Why here and not in the page: the grading server answers every browser
 * origin with 400 "Disallowed CORS origin", so a fetch from a content script
 * or from a plain HTML file is blocked before it is ever sent. A service
 * worker with host_permissions is exempt, which is what makes this extension
 * work where scripts/log_web.html cannot.
 *
 * A captured prompt travels:
 *   capture -> pending (review mode only, waits for you)
 *           -> queue   (approved; retried until the server acknowledges)
 *           -> history
 * Nothing is deleted from a stage until the next stage has it.
 */
'use strict';

importScripts('giturl.js');

const DEFAULT_SERVER = 'https://ai-logs.note.transformerlabs.ai/api/ingest';
const RETRY_ALARM = 'ailog-retry';
const RETRY_PERIOD_MIN = 1;
const COMMIT_ALARM = 'ailog-commit';
const COMMIT_PERIOD_MIN = 30;
const HISTORY_CAP = 200;
const MAX_PROMPT_LEN = 1000;
const BATCH_LIMIT = 500;      // matches submit_log.py and the server's own cap
const DEDUPE_MS = 15000;      // one send can trip both composer triggers
const RECENT_CAP = 60;

const DEFAULT_CONFIG = {
  serverUrl: DEFAULT_SERVER,
  apiKey: '',
  repo: '',
  student: '',
  branch: 'main',
  commit: '',
  enabled: true,
  toast: true,
  mode: 'review', // 'review' holds prompts for approval; 'auto' sends at once
  githubRepo: '', // "owner/name" — fallback source for `commit`
  githubToken: '', // only needed for a private repo; scope repo:read
  repoPath: '', // local checkout, asked of the native host when present
  // 'auto' follows whatever branch the checkout is on, so switching branches
  // needs no config change; 'fixed' pins to config.branch.
  branchMode: 'auto',
};

/* Enabled out of the box so the common sites work on first install. */
const DEFAULT_SITES = [
  { host: 'chatgpt.com', tool: 'chatgpt' },
  { host: 'chat.openai.com', tool: 'chatgpt' },
  { host: 'claude.ai', tool: 'claude-web' },
  { host: 'gemini.google.com', tool: 'gemini-web' },
  { host: 'aistudio.google.com', tool: 'ai-studio' },
  { host: 'perplexity.ai', tool: 'perplexity' },
  { host: 'chat.deepseek.com', tool: 'deepseek' },
  { host: 'grok.com', tool: 'grok' },
];

/* ---------------- storage ---------------- */

function get(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function set(obj) {
  return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
}

async function getConfig() {
  const data = await get('config');
  return Object.assign({}, DEFAULT_CONFIG, data.config || {});
}

/* ---------------- entry construction ---------------- */

/* The Python side stamps VN time (+07:00). Match it so entries from the
   extension and from log_hook.py sort and bucket identically. */
function vnIso(date) {
  return new Date(date.getTime() + 7 * 3600 * 1000).toISOString().replace('Z', '+07:00');
}

function ymd(date) {
  return vnIso(date).slice(0, 10).replace(/-/g, '');
}

async function installId() {
  const data = await get('installId');
  if (data.installId) return data.installId;
  const id = Math.random().toString(36).slice(2, 10);
  await set({ installId: id });
  return id;
}

let idCounter = 0;
function newId() {
  idCounter = (idCounter + 1) % 100000;
  return Date.now().toString(36) + '-' + idCounter.toString(36);
}

/* Same 13 fields log_hook.py writes, in the same order. */
async function buildEntry(partial, event) {
  const cfg = await getConfig();
  const now = new Date();
  const iid = await installId();
  return {
    ts: vnIso(now),
    tool: partial.tool || 'unknown',
    event,
    session_id: `web-${partial.tool || 'unknown'}-${ymd(now)}-${iid}`,
    model: partial.model || '',
    repo: cfg.repo,
    branch: cfg.branch || 'main',
    commit: cfg.commit || '',
    student: cfg.student,
    prompt: String(partial.prompt || '').trim().slice(0, MAX_PROMPT_LEN),
    tool_name: '',
    tool_input: null,
    tool_response: '',
  };
}

/* ---------------- dedupe ---------------- */

function normalize(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 300);
}

/* One send can arrive twice — from the keydown handler and from the
   composer-cleared check — so collapse them here rather than in either path. */
async function seenRecently(prompt) {
  const key = normalize(prompt);
  if (!key) return false;
  const now = Date.now();
  const data = await get('recent');
  const fresh = (data.recent || []).filter((r) => now - r.at < DEDUPE_MS);
  const hit = fresh.some((r) => r.key === key);
  if (!hit) fresh.push({ key, at: now });
  await set({ recent: fresh.slice(-RECENT_CAP) });
  return hit;
}

/* When the same send arrives twice and only the later copy carries a model,
   let it fill that in on the copy already waiting rather than dropping it. */
async function enrichModel(prompt, model) {
  if (!model) return false;
  const key = normalize(prompt);
  const d = await get(['pending', 'queue']);
  let changed = false;

  const pending = (d.pending || []).map((p) => {
    if (p.entry && !p.entry.model && normalize(p.entry.prompt) === key) {
      changed = true;
      return Object.assign({}, p, { entry: Object.assign({}, p.entry, { model }) });
    }
    return p;
  });

  const queue = (d.queue || []).map((e) => {
    if (!e.model && normalize(e.prompt) === key) {
      changed = true;
      return Object.assign({}, e, { model });
    }
    return e;
  });

  if (changed) await set({ pending, queue });
  return changed;
}

/* ---------------- queues ---------------- */

async function holdForReview(entry, via) {
  const data = await get('pending');
  const pending = data.pending || [];
  pending.unshift({ id: newId(), entry, via: via || '', at: vnIso(new Date()) });
  await set({ pending: pending.slice(0, 500) });
  await updateBadge();
}

async function enqueue(entry) {
  const data = await get('queue');
  const queue = data.queue || [];
  queue.push(entry);
  await set({ queue });
  await updateBadge();
}

async function pushHistory(record) {
  const data = await get('history');
  const history = data.history || [];
  history.unshift(record);
  await set({ history: history.slice(0, HISTORY_CAP) });
}

async function setError(message) {
  await set({ lastError: message ? { message, at: vnIso(new Date()) } : null });
  await updateBadge();
}

async function updateBadge() {
  const d = await get(['queue', 'pending', 'rejected', 'config']);
  const cfg = Object.assign({}, DEFAULT_CONFIG, d.config || {});
  const rejected = (d.rejected || []).length;
  const pending = (d.pending || []).length;
  const queued = (d.queue || []).length;

  if (rejected > 0) {
    chrome.action.setBadgeText({ text: String(rejected) });
    chrome.action.setBadgeBackgroundColor({ color: '#c0392b' });
  } else if (pending > 0) {
    chrome.action.setBadgeText({ text: String(pending) });
    chrome.action.setBadgeBackgroundColor({ color: '#2563eb' });
  } else if (queued > 0) {
    chrome.action.setBadgeText({ text: String(queued) });
    chrome.action.setBadgeBackgroundColor({ color: '#b8860b' });
  } else if (cfg.enabled === false) {
    // Visible on purpose: logging silently off for a week is the same failure
    // as logging silently not submitting.
    chrome.action.setBadgeText({ text: 'off' });
    chrome.action.setBadgeBackgroundColor({ color: '#6b7280' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

function missingConfig(cfg) {
  const missing = [];
  if (!cfg.serverUrl) missing.push('Server URL');
  if (!cfg.apiKey) missing.push('API Key');
  if (!cfg.repo) missing.push('Repo');
  if (!cfg.student) missing.push('Email');
  return missing;
}

/* ---------------- network ---------------- */

async function postEntries(cfg, entries) {
  const resp = await fetch(cfg.serverUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + cfg.apiKey },
    body: JSON.stringify({ entries }),
  });
  let body = null;
  try {
    body = await resp.json();
  } catch (err) {
    body = null;
  }
  return { status: resp.status, ok: resp.ok, body };
}

let flushing = false;

async function flush() {
  if (flushing) return { ok: true, skipped: true };
  const cfg = await getConfig();

  const missing = missingConfig(cfg);
  if (missing.length) {
    await setError('Chưa cấu hình: ' + missing.join(', '));
    return { ok: false, error: 'missing-config' };
  }

  const data = await get('queue');
  const queue = data.queue || [];
  if (!queue.length) {
    await setError(null);
    return { ok: true, sent: 0 };
  }

  flushing = true;
  const batch = queue.slice(0, BATCH_LIMIT);
  try {
    const res = await postEntries(cfg, batch);

    if (!res.ok) {
      await setError(`Server trả HTTP ${res.status} — log vẫn giữ trong hàng đợi`);
      await scheduleRetry();
      return { ok: false, error: 'http-' + res.status };
    }

    const accepted = (res.body && res.body.accepted) || 0;
    const duplicates = (res.body && res.body.duplicates) || 0;
    const mismatched = (res.body && res.body.mismatched_repos) || 0;

    const rest = queue.slice(batch.length);
    await set({ queue: rest });

    if (mismatched > 0) {
      // Retrying against a wrong repo name would fail forever, so park these
      // where the user can fix the config and resend deliberately.
      const store = await get('rejected');
      await set({ rejected: (store.rejected || []).concat(batch) });
      await setError(
        `Server từ chối ${mismatched} entry: tên repo "${cfg.repo}" không khớp. ` +
        'Sửa Repo trong Cấu hình rồi bấm "Gửi lại".'
      );
    } else {
      await setError(null);
    }

    for (const entry of batch) {
      await pushHistory({
        ts: entry.ts,
        tool: entry.tool,
        prompt: entry.prompt,
        status: mismatched > 0 ? 'rejected' : 'sent',
      });
    }

    await updateBadge();
    if (rest.length) await scheduleRetry();
    else await chrome.alarms.clear(RETRY_ALARM);

    return { ok: true, accepted, duplicates, mismatched };
  } catch (err) {
    await setError('Không gửi được (mất mạng?) — log giữ trong hàng đợi: ' + err.message);
    await scheduleRetry();
    return { ok: false, error: String(err.message || err) };
  } finally {
    flushing = false;
  }
}

async function scheduleRetry() {
  const existing = await chrome.alarms.get(RETRY_ALARM);
  if (!existing) chrome.alarms.create(RETRY_ALARM, { periodInMinutes: RETRY_PERIOD_MIN });
}

/* ---------------- site registration ---------------- */

function matchPatterns(sites) {
  const out = [];
  sites.forEach((s) => {
    if (!s || !s.host) return;
    out.push(`*://${s.host}/*`);
    out.push(`*://*.${s.host}/*`);
  });
  return out;
}

/* Capture scripts are registered at runtime rather than declared in the
   manifest, so enabling a new site takes effect without reinstalling. The
   MAIN-world pair is what reads request bodies; it exists only for sites the
   user turned on. */
async function registerSiteScripts() {
  const data = await get('enabledSites');
  const sites = data.enabledSites || [];
  const ids = ['ailog-dom', 'ailog-net'];

  try {
    const existing = await chrome.scripting.getRegisteredContentScripts({ ids });
    if (existing.length) {
      await chrome.scripting.unregisterContentScripts({ ids: existing.map((s) => s.id) });
    }
  } catch (err) { /* none registered yet */ }

  const matches = matchPatterns(sites);
  if (!matches.length) return;

  try {
    await chrome.scripting.registerContentScripts([
      {
        id: 'ailog-dom',
        matches,
        js: ['adapters.js', 'composer.js', 'content.js'],
        runAt: 'document_idle',
        allFrames: true, // some chat UIs host the composer in an iframe
      },
    ]);
  } catch (err) {
    await setError('Không đăng ký được script cho site đã bật: ' + err.message);
  }
}

/* registerContentScripts only affects future navigations, so enabling a site
   while its tab is already open would otherwise do nothing until a reload.
   Inject into the open tabs directly. The __ailog* guards in the scripts make
   a double injection a no-op. */
async function injectIntoOpenTabs(host) {
  let tabs = [];
  try {
    tabs = await chrome.tabs.query({});
  } catch (err) {
    return;
  }

  for (const tab of tabs) {
    if (!tab.id || !tab.url) continue;
    let h;
    try {
      h = new URL(tab.url).hostname;
    } catch (err) {
      continue;
    }
    if (h !== host && !h.endsWith('.' + host)) continue;

    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        files: ['adapters.js', 'composer.js', 'content.js'],
      });
    } catch (err) {
      // chrome:// pages and the web store refuse injection; nothing to do.
    }
  }
}

/* ---------------- native host ---------------- */

const NATIVE_HOST = 'com.ai20k.gitinfo';

/* Reads git straight off the machine, so the commit matches what log_hook.py
   stamps — including work that has not been pushed. Absent unless the user ran
   the installer under native/, which is why every caller treats failure as
   "fall back", not "error". */
function nativeCall(message) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (v) => { if (!settled) { settled = true; resolve(v); } };
    try {
      chrome.runtime.sendNativeMessage(NATIVE_HOST, message, (res) => {
        if (chrome.runtime.lastError) {
          return done({ ok: false, error: chrome.runtime.lastError.message, absent: true });
        }
        done(res && res.ok ? res : { ok: false, error: (res && res.error) || 'no-reply' });
      });
    } catch (err) {
      done({ ok: false, error: String(err.message || err), absent: true });
    }
  });
}

/* branch: omit to follow HEAD, pass a name to read that branch's tip. */
function nativeRepoInfo(repoPath, branch) {
  const msg = { action: 'repoinfo' };
  if (repoPath) msg.repo = repoPath;
  if (branch) msg.branch = branch;
  return nativeCall(msg);
}

function nativeBranches(repoPath) {
  const msg = { action: 'branches' };
  if (repoPath) msg.repo = repoPath;
  return nativeCall(msg);
}

/* ---------------- branches ---------------- */

/* Branch names routinely contain slashes (feature/x, release/1.2). Those must
   stay literal slashes in the API path — encodeURIComponent turns them into
   %2F and GitHub answers 404, so the commit for any such branch would silently
   fall back to whatever was cached. Encode each segment instead. */
function encodeRef(ref) {
  return String(ref || '').split('/').map(encodeURIComponent).join('/');
}

async function githubApi(cfg, path) {
  const slug = String(cfg.githubRepo || '').trim()
    .replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, '');
  if (!slug || slug.split('/').length !== 2) return { ok: false, error: 'no-slug', slug: '' };

  const headers = { Accept: 'application/vnd.github+json' };
  if (cfg.githubToken) headers.Authorization = 'Bearer ' + cfg.githubToken;

  let resp;
  try {
    resp = await fetch(`https://api.github.com/repos/${slug}${path}`, { headers });
  } catch (err) {
    return { ok: false, error: 'Không gọi được GitHub: ' + err.message, slug };
  }
  if (!resp.ok) {
    const hint = resp.status === 404
      ? 'không thấy repo/branch — repo private thì cần GitHub token'
      : (resp.status === 401 || resp.status === 403) ? 'token sai hoặc hết quyền'
      : 'HTTP ' + resp.status;
    return { ok: false, error: 'GitHub: ' + hint, status: resp.status, slug };
  }
  try {
    return { ok: true, body: await resp.json(), slug };
  } catch (err) {
    return { ok: false, error: 'GitHub trả về dữ liệu lạ', slug };
  }
}

/* Real branch names from whichever source is available, so the popup can offer
   a list instead of a text box. A mistyped branch used to mean a silently wrong
   commit; picking from a list removes the whole failure mode. */
async function listBranches() {
  const cfg = await getConfig();

  const native = await nativeBranches(cfg.repoPath);
  if (native.ok && Array.isArray(native.branches)) {
    return {
      ok: true,
      source: 'native',
      current: native.current,
      branches: native.branches,
    };
  }

  const res = await githubApi(cfg, '/branches?per_page=100');
  if (!res.ok) {
    return {
      ok: false,
      error: res.error === 'no-slug'
        ? (native.absent
            ? 'Chưa cài native host và chưa điền GitHub repo.'
            : 'Native host lỗi: ' + native.error)
        : res.error,
    };
  }

  const branches = (res.body || []).map((b) => ({
    name: b.name,
    commit: String((b.commit && b.commit.sha) || '').slice(0, 7),
    full: (b.commit && b.commit.sha) || '',
    upstream: '',
    ahead: '',
    behind: '',
    message: '',
    current: false,
  }));
  return { ok: true, source: 'github', current: '', branches };
}

function slugFromOrigin(origin) {
  if (!origin) return '';
  const parsed = AILOG_GITURL.parseRepoUrl(origin);
  return parsed.ok ? parsed.slug : '';
}

/* Checks a link without changing anything. Separate from connectRepo because
   "did I paste the right thing?" and "commit to this repo" are different
   questions, and the first should never be able to break a working config. */
async function testRepoLink(url, token) {
  const parsed = AILOG_GITURL.parseRepoUrl(url);
  if (!parsed.ok) return { ok: false, error: parsed.error };

  const cfg = await getConfig();
  const probe = Object.assign({}, cfg, {
    githubRepo: parsed.slug,
    githubToken: typeof token === 'string' && token ? token : cfg.githubToken,
  });

  const meta = await githubApi(probe, '');
  if (!meta.ok) {
    return {
      ok: false,
      slug: parsed.slug,
      error: meta.status === 404
        ? `Không truy cập được ${parsed.slug}. Repo private thì cần GitHub token, hoặc link sai.`
        : meta.error,
    };
  }

  const info = meta.body || {};
  const list = await githubApi(probe, '/branches?per_page=100');
  const names = list.ok ? (list.body || []).map((b) => b.name) : [];
  const fromLink = AILOG_GITURL.resolveBranchHint(parsed.branchHint, names);

  return {
    ok: true,
    slug: parsed.slug,
    repo: info.name || parsed.name,
    defaultBranch: info.default_branch || '',
    private: !!info.private,
    branches: names,
    branchFromLink: fromLink,
    // Says out loud when a link pointed at a branch that no longer exists.
    danglingHint: !!(parsed.branchHint && !fromLink),
    matchesConfig: (info.name || parsed.name) === cfg.repo,
  };
}

/* One action instead of five fields. Paste the repo link and this derives the
   slug, the repo name the server expects, the branch list, the branch the link
   pointed at (if any), and the commit — then verifies all of it against the
   GitHub API rather than trusting what was typed. */
async function connectRepo(url, token) {
  const parsed = AILOG_GITURL.parseRepoUrl(url);
  if (!parsed.ok) return { ok: false, error: parsed.error };

  const cfg = await getConfig();
  const probe = Object.assign({}, cfg, {
    githubRepo: parsed.slug,
    githubToken: typeof token === 'string' && token ? token : cfg.githubToken,
  });

  const meta = await githubApi(probe, '');
  if (!meta.ok) {
    return {
      ok: false,
      error: meta.status === 404
        ? `Không truy cập được ${parsed.slug}. Repo private thì cần GitHub token, hoặc kiểm tra lại link.`
        : meta.error,
    };
  }

  const info = meta.body || {};
  const defaultBranch = info.default_branch || 'main';

  const list = await githubApi(probe, '/branches?per_page=100');
  const names = list.ok ? (list.body || []).map((b) => b.name) : [];

  // A link like /tree/feature/x/src carries the branch; settle it against the
  // real names so a path segment is not mistaken for part of the branch.
  const fromLink = AILOG_GITURL.resolveBranchHint(parsed.branchHint, names);
  const branch = fromLink || (names.indexOf(cfg.branch) !== -1 ? cfg.branch : defaultBranch);

  const next = Object.assign({}, probe, {
    // The server matches on the repo name it issued, which is the GitHub name.
    repo: info.name || parsed.name,
    branch,
    branchMode: fromLink ? 'fixed' : cfg.branchMode || 'auto',
  });
  await set({ config: next });
  await setError(null);

  const commit = await refreshCommit();

  return {
    ok: true,
    slug: parsed.slug,
    repo: next.repo,
    branch,
    branchFromLink: !!fromLink,
    defaultBranch,
    private: !!info.private,
    branches: names,
    commit: commit.ok ? commit.sha : '',
    commitSource: commit.ok ? commit.source : '',
    commitError: commit.ok ? '' : commit.error,
  };
}

/* ---------------- commit ---------------- */

/* Resolves the commit for the branch that entries should be stamped with.
 *
 * branchMode 'auto' asks the checkout what branch it is on, so switching
 * branches locally moves the logs with you and needs no config change.
 * branchMode 'fixed' pins to config.branch and reads that branch's tip even
 * when it is not the one checked out.
 *
 * Native is tried first: it is the only source that sees unpushed work, and it
 * costs one local process instead of a network round trip. GitHub is the
 * fallback and only ever knows the pushed tip.
 */
async function refreshCommit() {
  const cfg = await getConfig();
  const pinned = cfg.branchMode === 'fixed';
  const wanted = pinned ? (cfg.branch || 'main') : '';

  const native = await nativeRepoInfo(cfg.repoPath, wanted);
  if (native.ok && native.commit) {
    const next = Object.assign({}, cfg, { commit: native.commit });
    // In auto mode the checkout is the authority on which branch this is.
    if (!pinned && native.branch) next.branch = native.branch;
    await set({
      config: next,
      commitInfo: {
        sha: native.commit,
        full: native.full || '',
        branch: native.branch || cfg.branch || '',
        at: vnIso(new Date()),
        message: native.message || '',
        source: 'native',
        dirty: !!native.dirty,
        unpushed: native.unpushed || '',
        behind: native.behind || '',
        upstream: native.upstream || '',
        pinned,
      },
    });
    return {
      ok: true, sha: native.commit, branch: native.branch,
      source: 'native', dirty: !!native.dirty, unpushed: native.unpushed || '',
    };
  }

  // Native said the pinned branch does not exist — a real answer, not absence.
  if (!native.absent && native.error && /branch/i.test(native.error)) {
    return { ok: false, error: native.error };
  }

  const branch = cfg.branch || 'main';
  const res = await githubApi(cfg, '/commits/' + encodeRef(branch));
  if (!res.ok) {
    return {
      ok: false,
      error: res.error === 'no-slug'
        ? (native.absent
            ? 'Chưa điền GitHub repo dạng owner/name (và chưa cài native host)'
            : 'Native host lỗi: ' + native.error)
        : res.error,
    };
  }

  const body = res.body || {};
  const full = String(body.sha || '');
  if (!/^[0-9a-f]{7,40}$/i.test(full)) return { ok: false, error: 'Không đọc được SHA' };

  const short = full.slice(0, 7);
  await set({
    config: Object.assign({}, cfg, { commit: short }),
    commitInfo: {
      sha: short,
      full,
      branch,
      at: vnIso(new Date()),
      message: String((body.commit && body.commit.message) || '').split('\n')[0].slice(0, 120),
      source: 'github',
      pinned,
    },
  });
  return { ok: true, sha: short, branch, source: 'github' };
}

/* Fills repo / branch / student / commit in one go from the local checkout —
   the same four values log_hook.py derives, so the extension's entries and the
   Python pipeline's entries agree instead of diverging on a typo. */
async function adoptLocalRepo(repoPath) {
  const info = await nativeRepoInfo(repoPath);
  if (!info.ok) {
    return {
      ok: false,
      error: info.absent
        // Backslashes must be doubled — a single \a in a JS string is just "a",
        // and the user gets handed a path that does not exist.
        ? 'Chưa cài native host. Chạy một lệnh: tools\\ai-log-extension\\setup.cmd ' +
          '(macOS/Linux: bash tools/ai-log-extension/setup.sh), khởi động lại ' +
          'trình duyệt, rồi bấm "Kiểm tra tất cả". Xem mục "Bắt đầu" ở đầu popup.'
        : info.error,
    };
  }

  const cfg = await getConfig();
  const next = Object.assign({}, cfg);
  if (info.repo) next.repo = info.repo;
  if (info.branch) next.branch = info.branch;
  if (info.student) next.student = info.student;
  if (info.commit) next.commit = info.commit;
  if (repoPath) next.repoPath = repoPath;
  else if (info.root) next.repoPath = info.root;

  // The checkout already knows its GitHub URL — one less thing to paste, and
  // one less way to point the extension at the wrong repo.
  const fromOrigin = slugFromOrigin(info.origin);
  if (fromOrigin) next.githubRepo = fromOrigin;

  await set({
    config: next,
    commitInfo: {
      sha: info.commit || '',
      full: info.full || '',
      branch: info.branch || '',
      at: vnIso(new Date()),
      message: info.message || '',
      source: 'native',
      dirty: !!info.dirty,
      unpushed: info.unpushed || '',
    },
  });
  await setError(null);
  return { ok: true, info, config: next };
}

/* ---------------- messages ---------------- */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      switch (msg && msg.type) {
        case 'capture':
        case 'manual': {
          const cfg = await getConfig();
          const isAuto = msg.type === 'capture';
          if (isAuto && cfg.enabled === false) {
            return sendResponse({ ok: false, status: 'disabled', error: 'disabled' });
          }

          const entry = await buildEntry(msg.entry || {}, isAuto ? 'UserPromptSubmit' : 'ManualLog');
          if (!entry.prompt) return sendResponse({ ok: false, error: 'empty-prompt' });

          if (isAuto && (await seenRecently(entry.prompt))) {
            const enriched = await enrichModel(entry.prompt, entry.model);
            return sendResponse({ ok: true, status: 'duplicate', enriched });
          }

          // Manual entries are already a deliberate act, so they skip review.
          if (isAuto && cfg.mode === 'review') {
            await holdForReview(entry, (msg.entry && msg.entry.via) || '');
            return sendResponse({ ok: true, status: 'held' });
          }

          await enqueue(entry);
          const res = await flush();
          let status = 'sent';
          if (!res.ok) status = 'queued';
          else if (res.mismatched) status = 'rejected';
          return sendResponse({ ok: status !== 'rejected', status, detail: res });
        }

        case 'approvePending': {
          const ids = msg.ids || [];
          const d = await get(['pending', 'queue']);
          const pending = d.pending || [];
          const keep = [];
          const move = [];
          pending.forEach((p) => (ids.indexOf(p.id) === -1 ? keep.push(p) : move.push(p.entry)));
          if (!move.length) return sendResponse({ ok: true, moved: 0 });
          await set({ pending: keep, queue: (d.queue || []).concat(move) });
          await updateBadge();
          const res = await flush();
          return sendResponse(Object.assign({ moved: move.length }, res));
        }

        case 'deletePending': {
          const ids = msg.ids || [];
          const d = await get('pending');
          const keep = (d.pending || []).filter((p) => ids.indexOf(p.id) === -1);
          const removed = (d.pending || []).length - keep.length;
          await set({ pending: keep });
          await updateBadge();
          return sendResponse({ ok: true, removed });
        }

        case 'flush':
          return sendResponse(await flush());

        case 'getState': {
          const cfg = await getConfig();
          const d = await get([
            'queue', 'pending', 'history', 'rejected', 'lastError',
            'enabledSites', 'detected', 'commitInfo',
          ]);
          return sendResponse({
            ok: true,
            config: cfg,
            missing: missingConfig(cfg),
            queue: d.queue || [],
            pending: d.pending || [],
            history: d.history || [],
            rejected: d.rejected || [],
            lastError: d.lastError || null,
            enabledSites: d.enabledSites || [],
            detected: d.detected || {},
            commitInfo: d.commitInfo || null,
          });
        }

        case 'saveConfig': {
          const before = await getConfig();
          const cfg = Object.assign({}, before, msg.config || {});
          await set({ config: cfg });
          await setError(null);
          await updateBadge();
          // Re-read the commit when the thing it depends on changed.
          if (cfg.githubRepo &&
              (cfg.githubRepo !== before.githubRepo ||
               cfg.branch !== before.branch ||
               cfg.githubToken !== before.githubToken)) {
            await refreshCommit();
          }
          await flush();
          return sendResponse({ ok: true, config: await getConfig() });
        }

        /* Empty batch: proves URL + key + reachability without writing
           anything. The server answers 202 with all-zero counters. */
        case 'testConnection': {
          const cfg = await getConfig();
          const missing = missingConfig(cfg);
          if (missing.length) return sendResponse({ ok: false, error: 'Thiếu: ' + missing.join(', ') });
          try {
            const res = await postEntries(cfg, []);
            return sendResponse({ ok: res.ok, status: res.status, body: res.body, error: res.ok ? null : 'HTTP ' + res.status });
          } catch (err) {
            return sendResponse({ ok: false, error: String(err.message || err) });
          }
        }

        case 'requeueRejected': {
          const cfg = await getConfig();
          const d = await get(['rejected', 'queue']);
          const fixed = (d.rejected || []).map((e) =>
            Object.assign({}, e, { repo: cfg.repo, student: cfg.student })
          );
          await set({ queue: (d.queue || []).concat(fixed), rejected: [] });
          await updateBadge();
          return sendResponse(await flush());
        }

        case 'discardRejected':
          await set({ rejected: [] });
          await setError(null);
          return sendResponse({ ok: true });

        case 'clearHistory':
          await set({ history: [] });
          return sendResponse({ ok: true });

        case 'refreshCommit':
          return sendResponse(await refreshCommit());

        case 'adoptLocalRepo':
          return sendResponse(await adoptLocalRepo(msg.repoPath));

        case 'listBranches':
          return sendResponse(await listBranches());

        case 'connectRepo':
          return sendResponse(await connectRepo(msg.url, msg.token));

        case 'testRepoLink':
          return sendResponse(await testRepoLink(msg.url, msg.token));

        case 'autoDetect':
          return sendResponse(await autoDetect());

        case 'runDiagnostics':
          return sendResponse(await runDiagnostics(msg.host));

        case 'pingNative': {
          const info = await nativeRepoInfo((await getConfig()).repoPath);
          return sendResponse(info);
        }

        case 'detected': {
          if (!msg.host) return sendResponse({ ok: false });
          const d = await get(['detected', 'enabledSites']);
          const sites = d.enabledSites || [];
          const already = sites.some((s) => msg.host === s.host || msg.host.endsWith('.' + s.host));
          if (already) return sendResponse({ ok: true, enabled: true });
          const detected = d.detected || {};
          detected[msg.host] = { score: msg.score, signals: msg.signals || [], at: vnIso(new Date()) };
          await set({ detected });
          return sendResponse({ ok: true, enabled: false });
        }

        case 'enableSite': {
          const host = String(msg.host || '').replace(/^www\./, '');
          if (!host) return sendResponse({ ok: false, error: 'no-host' });
          const d = await get(['enabledSites', 'detected']);
          const sites = d.enabledSites || [];
          if (!sites.some((s) => s.host === host)) {
            sites.push({ host, tool: msg.tool || host });
          }
          const detected = d.detected || {};
          delete detected[host];
          delete detected['www.' + host];
          await set({ enabledSites: sites, detected });
          await registerSiteScripts();
          await injectIntoOpenTabs(host); // takes effect without a reload
          return sendResponse({ ok: true, enabledSites: sites });
        }

        case 'disableSite': {
          const d = await get('enabledSites');
          const sites = (d.enabledSites || []).filter((s) => s.host !== msg.host);
          await set({ enabledSites: sites });
          await registerSiteScripts();
          return sendResponse({ ok: true, enabledSites: sites });
        }

        case 'dismissDetected': {
          const d = await get('detected');
          const detected = d.detected || {};
          delete detected[msg.host];
          await set({ detected });
          return sendResponse({ ok: true });
        }

        default:
          return sendResponse({ ok: false, error: 'unknown-message' });
      }
    } catch (err) {
      return sendResponse({ ok: false, error: String(err.message || err) });
    }
  })();
  return true; // keep the channel open for the async work above
});

/* Runs on install and on every browser start. Anything the machine can answer
   for itself should not be a text box the user can mistype.
 *
 * Deliberately asymmetric about what it overwrites:
 *   - commit, and branch in auto mode, always track the checkout — that is the
 *     whole point, and they go stale by the minute.
 *   - repo, student, githubRepo, repoPath fill in only when empty, so a
 *     deliberate edit is never silently undone on the next restart.
 * Silent no-op when the native host is not installed. */
async function autoDetect() {
  const cfg = await getConfig();
  const info = await nativeRepoInfo(cfg.repoPath);
  if (!info.ok) return { ok: false, reason: info.absent ? 'no-host' : info.error };

  const next = Object.assign({}, cfg);
  if (!next.repo && info.repo) next.repo = info.repo;
  if (!next.student && info.student) next.student = info.student;
  if (!next.repoPath && info.root) next.repoPath = info.root;
  if (!next.githubRepo) {
    const slug = slugFromOrigin(info.origin);
    if (slug) next.githubRepo = slug;
  }
  await set({ config: next });

  const commit = await refreshCommit();
  return { ok: true, config: next, commit };
}

/* ---------------- diagnostics ---------------- */

/* The in-popup twin of native/doctor.py. Every step reports pass/fail plus
   what to do about it — a checklist beats a single "chưa cài native host",
   which tells you something is wrong but not which of six things. */
async function runDiagnostics(activeHost) {
  const cfg = await getConfig();
  const steps = [];
  const step = (key, title, ok, detail, fix, optional) =>
    steps.push({ key, title, ok, detail: detail || '', fix: fix || '', optional: !!optional });

  // 1. server credentials
  const missing = missingConfig(cfg);
  step('config', 'Server và API Key', missing.length === 0,
    missing.length ? 'Thiếu: ' + missing.join(', ') : cfg.serverUrl,
    'Mở mục Cấu hình, điền Server URL và API Key lấy từ file .env của repo.');

  // 2. server actually answers
  if (missing.length) {
    step('server', 'Gửi thử lên server', false, 'chưa kiểm tra được',
      'Điền Server URL và API Key trước đã.');
  } else {
    try {
      const res = await postEntries(cfg, []);
      step('server', 'Gửi thử lên server', res.ok,
        res.ok ? `HTTP ${res.status} — gửi batch rỗng, không ghi gì` : `HTTP ${res.status}`,
        res.status === 401 || res.status === 403
          ? 'API Key sai. Lấy lại từ .env (dòng AI_LOG_API_KEY).'
          : 'Kiểm tra Server URL, hoặc hỏi BTC endpoint đúng.');
    } catch (err) {
      step('server', 'Gửi thử lên server', false, String(err.message || err),
        'Mất mạng, hoặc Server URL sai.');
    }
  }

  // 3. repo identity
  const hasRepo = !!cfg.repo;
  step('repo', 'Repo và branch', hasRepo,
    hasRepo ? `${cfg.repo} · ${cfg.branch || 'main'} · ${cfg.commit || 'chưa có commit'}` : 'chưa có',
    'Dán link repo GitHub rồi bấm "Kết nối", hoặc cài native host để tự lấy.');

  // 4. native host — optional, but it is the only exact source for commit
  const native = await nativeRepoInfo(cfg.repoPath);
  step('native', 'Native host (tuỳ chọn)', native.ok,
    native.ok
      ? `${native.repo || '(không có origin)'} · ${native.branch} · ${native.commit}` +
        (native.dirty ? ' · có thay đổi chưa commit' : '')
      : (native.absent ? 'chưa cài' : native.error),
    'Một lệnh, vừa cài vừa kiểm tra, rồi KHỞI ĐỘNG LẠI trình duyệt:\n' +
    'tools\\ai-log-extension\\setup.cmd --server\n' +
    'macOS/Linux: bash tools/ai-log-extension/setup.sh --server',
    true);

  // 5. capture is actually armed somewhere
  const d = await get('enabledSites');
  const sites = d.enabledSites || [];
  step('sites', 'Site đang bật', sites.length > 0,
    sites.length ? `${sites.length} site` : 'chưa bật site nào',
    'Mở mục "Site đang bật" và thêm domain, hoặc mở một AI chat rồi bật ngay trên popup.');

  // 6. and specifically on the tab you are looking at
  if (activeHost) {
    const covered = sites.some((s) => activeHost === s.host || activeHost.endsWith('.' + s.host));
    step('tab', `Trang đang mở (${activeHost})`, covered,
      covered ? 'đang được ghi log' : 'không nằm trong danh sách',
      'Bật công tắc site ở đầu popup nếu đây là một AI chat.', true);
  }

  // 7. master switch — last, because it silences everything above
  step('enabled', 'Công tắc ghi log', cfg.enabled !== false,
    cfg.enabled === false ? 'ĐANG TẮT' : 'đang bật',
    'Gạt công tắc ở góc phải trên popup.');

  const required = steps.filter((s) => !s.optional);
  return {
    ok: true,
    steps,
    passed: required.filter((s) => s.ok).length,
    total: required.length,
    ready: required.every((s) => s.ok),
  };
}

/* ---------------- lifecycle ---------------- */

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RETRY_ALARM) flush();
  else if (alarm.name === COMMIT_ALARM) refreshCommit();
});

chrome.runtime.onInstalled.addListener(async () => {
  const d = await get(['config', 'enabledSites']);
  if (!d.config) await set({ config: DEFAULT_CONFIG });
  if (!d.enabledSites) await set({ enabledSites: DEFAULT_SITES });
  await registerSiteScripts();
  await updateBadge();
  chrome.alarms.create(COMMIT_ALARM, { periodInMinutes: COMMIT_PERIOD_MIN });
  await autoDetect();
});

chrome.runtime.onStartup.addListener(async () => {
  await registerSiteScripts();
  await updateBadge();
  chrome.alarms.create(COMMIT_ALARM, { periodInMinutes: COMMIT_PERIOD_MIN });
  await autoDetect();
  await flush();
});
