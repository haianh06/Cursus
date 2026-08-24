/* Exercises background.js against a stubbed chrome + fetch.
   Covers the review queue, the send path, model enrichment, and every way a
   log could go missing. Run: node test/background.test.js <extDir> */
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const EXT = process.argv[2] || path.join(__dirname, '..');

const ok202 = (body) => ({ ok: true, status: 202, json: async () => body });
const SENT_OK = { accepted: 1, duplicates: 0, mismatched_repos: 0 };

let fetchCalls = [];
let fetchImpl = async () => ok202(SENT_OK);
let githubImpl = async () => ({ ok: false, status: 404, json: async () => ({}) });

const store = {};
let messageListener = null;
const badge = { text: '', color: '' };
const registered = [];
const injected = [];
const nativeCalls = [];
/* null means "host not installed" — the default, since most machines will not
   have run the installer. */
let nativeImpl = () => null;

/* One tab open on a subdomain of live.example, to prove enabling a site
   reaches tabs that are already loaded. */
const TABS = [
  { id: 42, url: 'https://app.live.example/chat' },
  { id: 43, url: 'https://unrelated.test/' },
  { id: 44, url: 'chrome://extensions' },
];

const chrome = {
  storage: {
    local: {
      get(keys, cb) {
        const k = keys == null ? Object.keys(store) : (Array.isArray(keys) ? keys : [keys]);
        const out = {};
        k.forEach((key) => { if (key in store) out[key] = store[key]; });
        cb(out);
      },
      set(obj, cb) { Object.assign(store, obj); cb && cb(); },
    },
    onChanged: { addListener() {} },
  },
  runtime: {
    onMessage: { addListener: (fn) => { messageListener = fn; } },
    onInstalled: { addListener() {} },
    onStartup: { addListener() {} },
    lastError: undefined,
    sendNativeMessage: (host, msg, cb) => {
      nativeCalls.push([host, msg]);
      const res = nativeImpl(msg);
      // Chrome signals "host not installed" through lastError, not an argument.
      chrome.runtime.lastError = res === null ? { message: 'Specified native messaging host not found.' } : undefined;
      cb(res === null ? undefined : res);
      chrome.runtime.lastError = undefined;
    },
  },
  action: {
    setBadgeText: ({ text }) => { badge.text = text; },
    setBadgeBackgroundColor: ({ color }) => { badge.color = color; },
  },
  alarms: {
    onAlarm: { addListener() {} },
    get: async () => null,
    create: () => {},
    clear: async () => {},
  },
  scripting: {
    getRegisteredContentScripts: async () => registered.slice(),
    unregisterContentScripts: async () => { registered.length = 0; },
    registerContentScripts: async (list) => { registered.push(...list); },
    executeScript: async (opts) => { injected.push(opts); return []; },
  },
  tabs: { query: async () => TABS.slice() },
  permissions: { contains: async () => true },
};

/* Route by host so the GitHub lookup and the log submit can be stubbed
   independently; only log-server calls land in fetchCalls. */
function routedFetch(url, opts) {
  if (String(url).indexOf('api.github.com') !== -1) return githubImpl(url, opts);
  fetchCalls.push([url, opts]);
  return fetchImpl(url, opts);
}

const ctx = vm.createContext({
  chrome,
  fetch: routedFetch,
  URL,
  // Same effect as the service worker's: evaluate the file in this scope.
  importScripts: (...files) => files.forEach((f) =>
    vm.runInContext(fs.readFileSync(path.join(EXT, f), 'utf8'), ctx, { filename: f })),
  console, setTimeout, clearTimeout, Date, Math, JSON, Promise, Object, Array, String, Number, Error,
});
vm.runInContext(fs.readFileSync(path.join(EXT, 'background.js'), 'utf8'), ctx, { filename: 'background.js' });

const send = (msg) => new Promise((res) => messageListener(msg, {}, res));
const bodyOf = (call) => JSON.parse(call[1].body);

let failures = 0;
function check(name, cond, extra) {
  if (cond) return console.log('  PASS  ' + name);
  failures++;
  console.log('  FAIL  ' + name + (extra !== undefined ? '  -> ' + JSON.stringify(extra) : ''));
}

const CONFIG = {
  serverUrl: 'https://example.test/api/ingest', apiKey: 'k-123',
  repo: 'P-093', student: 'binhnthe182340@fpt.edu.vn', branch: 'main', commit: 'abc1234',
};

(async () => {
  console.log('\n--- 1. review mode holds instead of sending ---');
  await send({ type: 'saveConfig', config: Object.assign({ mode: 'review' }, CONFIG) });
  fetchCalls = [];
  let res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'Câu hỏi riêng tư không muốn gửi' } });
  check('status=held', res.status === 'held', res);
  check('nothing POSTed', fetchCalls.length === 0, fetchCalls.length);
  check('sits in pending', (store.pending || []).length === 1, store.pending);
  check('queue untouched', (store.queue || []).length === 0, store.queue);
  check('badge blue', badge.color === '#2563eb', badge);

  console.log('\n--- 2. deleting a held prompt never reaches the server ---');
  fetchCalls = [];
  res = await send({ type: 'deletePending', ids: [store.pending[0].id] });
  check('removed 1', res.removed === 1, res);
  check('pending empty', (store.pending || []).length === 0, store.pending);
  check('still no POST', fetchCalls.length === 0, fetchCalls.length);
  check('badge cleared', badge.text === '', badge);

  console.log('\n--- 3. approve only what was ticked ---');
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'giữ lại cái này' } });
  await send({ type: 'capture', entry: { tool: 'claude-web', prompt: 'gửi cái này' } });
  check('two held', (store.pending || []).length === 2, store.pending);

  const wanted = store.pending.find((p) => p.entry.prompt === 'gửi cái này').id;
  fetchCalls = [];
  res = await send({ type: 'approvePending', ids: [wanted] });
  check('moved 1', res.moved === 1, res);
  check('one POST', fetchCalls.length === 1, fetchCalls.length);
  check('batch holds only the chosen one', bodyOf(fetchCalls[0]).entries.length === 1);
  check('and it is the right one', bodyOf(fetchCalls[0]).entries[0].prompt === 'gửi cái này');
  check('the other stays held', (store.pending || []).length === 1 &&
    store.pending[0].entry.prompt === 'giữ lại cái này', store.pending);
  await send({ type: 'deletePending', ids: [store.pending[0].id] });

  console.log('\n--- 4. entry schema matches log_hook.py ---');
  await send({ type: 'saveConfig', config: { mode: 'auto' } });
  fetchCalls = [];
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', model: 'gpt-5.4', prompt: 'Xin chào, giải thích OAuth2 PKCE' } });
  check('status=sent', res.status === 'sent', res);
  const e = bodyOf(fetchCalls[0]).entries[0];
  const FIELDS = ['ts','tool','event','session_id','model','repo','branch','commit','student','prompt','tool_name','tool_input','tool_response'];
  check('13 fields, same order', JSON.stringify(Object.keys(e)) === JSON.stringify(FIELDS), Object.keys(e));
  check('event=UserPromptSubmit', e.event === 'UserPromptSubmit', e.event);
  check('ts is VN +07:00', /\+07:00$/.test(e.ts), e.ts);
  check('model carried through', e.model === 'gpt-5.4', e.model);
  check('Bearer header', fetchCalls[0][1].headers.Authorization === 'Bearer k-123');
  check('Vietnamese intact', e.prompt === 'Xin chào, giải thích OAuth2 PKCE', e.prompt);

  console.log('\n--- 5. one send seen twice logs once ---');
  fetchCalls = [];
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'trùng nhau', via: 'dom:enter' } });
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'trùng  nhau ', via: 'net:fetch' } });
  check('second is a duplicate', res.status === 'duplicate', res);
  check('only one POST', fetchCalls.length === 1, fetchCalls.length);

  console.log('\n--- 6. the duplicate backfills the model it knows ---');
  await send({ type: 'saveConfig', config: { mode: 'review' } });
  // DOM fires first and has no model; the network copy arrives with one.
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'model đến sau', model: '', via: 'dom:enter' } });
  check('held without a model', store.pending[0].entry.model === '', store.pending[0].entry);
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'model đến sau', model: 'claude-opus-5', via: 'dom:sent' } });
  check('reported as duplicate', res.status === 'duplicate', res);
  check('enriched flag set', res.enriched === true, res);
  check('held entry now names the model', store.pending[0].entry.model === 'claude-opus-5', store.pending[0].entry);
  check('still only one held', (store.pending || []).length === 1, store.pending);
  await send({ type: 'deletePending', ids: [store.pending[0].id] });

  console.log('\n--- 7. manual entry bypasses review ---');
  fetchCalls = [];
  res = await send({ type: 'manual', entry: { tool: 'claude-web', prompt: 'Ghi tay' } });
  check('sent immediately', res.status === 'sent', res);
  check('event=ManualLog', bodyOf(fetchCalls[0]).entries[0].event === 'ManualLog');
  check('not parked in pending', (store.pending || []).length === 0, store.pending);

  console.log('\n--- 8. network failure keeps the entry ---');
  await send({ type: 'saveConfig', config: { mode: 'auto' } });
  fetchImpl = async () => { throw new Error('net::ERR_INTERNET_DISCONNECTED'); };
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'khi mất mạng' } });
  check('status=queued', res.status === 'queued', res);
  check('retained in queue', (store.queue || []).length === 1, store.queue);
  check('badge amber', badge.color === '#b8860b', badge);
  check('error recorded', !!store.lastError, store.lastError);

  console.log('\n--- 9. recovers on the next flush ---');
  fetchImpl = async () => ok202(SENT_OK);
  res = await send({ type: 'flush' });
  check('flush ok', res.ok === true, res);
  check('queue drained', (store.queue || []).length === 0, store.queue);
  check('badge cleared', badge.text === '', badge);

  console.log('\n--- 10. wrong repo parks entries instead of losing them ---');
  fetchImpl = async () => ok202({ accepted: 0, duplicates: 0, mismatched_repos: 1 });
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'sai repo' } });
  check('status=rejected', res.status === 'rejected', res);
  check('parked in rejected', (store.rejected || []).length === 1, store.rejected);
  check('not left in queue', (store.queue || []).length === 0, store.queue);
  check('error names the repo', /repo/i.test((store.lastError || {}).message || ''), store.lastError);
  check('badge red', badge.color === '#c0392b', badge);

  console.log('\n--- 11. fix the repo and resend ---');
  fetchImpl = async () => ok202(SENT_OK);
  await send({ type: 'saveConfig', config: { repo: 'P-093-correct' } });
  fetchCalls = [];
  res = await send({ type: 'requeueRejected' });
  check('requeue ok', res.ok === true, res);
  check('rejected drained', (store.rejected || []).length === 0, store.rejected);
  check('resent with the new repo', bodyOf(fetchCalls[0]).entries[0].repo === 'P-093-correct');

  console.log('\n--- 12. missing config blocks the send but keeps the entry ---');
  await send({ type: 'saveConfig', config: { apiKey: '' } });
  fetchCalls = [];
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'chưa cấu hình' } });
  check('no POST attempted', fetchCalls.length === 0, fetchCalls.length);
  check('entry still queued', (store.queue || []).length === 1, store.queue);
  check('status=queued', res.status === 'queued', res);
  await send({ type: 'saveConfig', config: { apiKey: 'k-123' } });
  await send({ type: 'flush' });

  console.log('\n--- 13. site enable / disable ---');
  await send({ type: 'enableSite', host: 'www.chat.mistral.ai', tool: 'mistral' });
  check('www stripped', store.enabledSites.some((s) => s.host === 'chat.mistral.ai'), store.enabledSites);
  check('DOM script registered', registered.some((r) => r.id === 'ailog-dom'), registered.map((r) => r.id));
  // The MAIN-world request sniffer was removed: it could not tell a prompt
  // from the site's own traffic and logged things like "Turn exchange
  // complete". Nothing may read page requests any more.
  check('no MAIN-world script', registered.every((r) => r.world !== 'MAIN'), registered);
  await send({ type: 'disableSite', host: 'chat.mistral.ai' });
  check('site removed', !store.enabledSites.some((s) => s.host === 'chat.mistral.ai'), store.enabledSites);

  console.log('\n--- 14. detection only suggests, never acts ---');
  fetchCalls = [];
  await send({ type: 'detected', host: 'newchat.example', score: 7, signals: ['composer', 'send-button'] });
  check('recorded as a suggestion', !!(store.detected || {})['newchat.example'], store.detected);
  check('does not auto-enable', !(store.enabledSites || []).some((s) => s.host === 'newchat.example'));
  check('sends nothing', fetchCalls.length === 0, fetchCalls.length);
  await send({ type: 'enableSite', host: 'newchat.example', tool: 'newchat' });
  check('enabling clears the suggestion', !(store.detected || {})['newchat.example'], store.detected);

  console.log('\n--- 15. master switch ---');
  await send({ type: 'saveConfig', config: { enabled: false } });
  fetchCalls = [];
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'khi đã tắt' } });
  check('capture refused', res.status === 'disabled', res);
  check('nothing POSTed', fetchCalls.length === 0, fetchCalls.length);
  check('badge shows off', badge.text === 'off', badge);
  res = await send({ type: 'manual', entry: { tool: 'chatgpt', prompt: 'nhập tay vẫn được' } });
  check('manual still works while off', res.status === 'sent', res);
  await send({ type: 'saveConfig', config: { enabled: true } });
  check('badge clears on re-enable', badge.text === '', badge);

  console.log('\n--- 16. enabling a site reaches tabs already open ---');
  injected.length = 0;
  await send({ type: 'enableSite', host: 'live.example', tool: 'live' });
  check('injected into the open tab', injected.length === 1, injected);
  check('nothing injected into MAIN world', injected.every((i) => i.world !== 'MAIN'), injected);
  check('composer.js included', injected.some((i) => (i.files || []).includes('composer.js')), injected);
  check('subdomain tab matched', injected.every((i) => i.target.tabId === 42), injected);
  injected.length = 0;
  await send({ type: 'enableSite', host: 'notopen.example', tool: 'x' });
  check('no matching tab -> no injection', injected.length === 0, injected);

  console.log('\n--- 17. commit auto-fetch ---');
  res = await send({ type: 'refreshCommit' });
  check('needs a github repo first', res.ok === false && /owner\/name/.test(res.error), res);

  githubImpl = async () => ({
    ok: true, status: 200,
    json: async () => ({ sha: '9f2c1ab7de45', commit: { message: 'feat: thêm extension\n\nchi tiết' } }),
  });
  await send({ type: 'saveConfig', config: { githubRepo: 'AI20K-Build-Cohort-2/P-093', branch: 'main' } });
  check('config carries the short sha', (await send({ type: 'getState' })).config.commit === '9f2c1ab', store.config);
  check('commitInfo recorded', store.commitInfo.full === '9f2c1ab7de45', store.commitInfo);
  check('first line of the message only', store.commitInfo.message === 'feat: thêm extension', store.commitInfo);

  fetchCalls = [];
  await send({ type: 'saveConfig', config: { mode: 'auto' } });
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'entry sau khi có commit' } });
  check('entry stamped with the fetched commit',
    bodyOf(fetchCalls[fetchCalls.length - 1]).entries[0].commit === '9f2c1ab',
    bodyOf(fetchCalls[fetchCalls.length - 1]).entries[0]);

  githubImpl = async () => ({ ok: false, status: 404, json: async () => ({}) });
  res = await send({ type: 'refreshCommit' });
  check('404 explains private repos', res.ok === false && /private/.test(res.error), res);
  check('commit kept on failure', (await send({ type: 'getState' })).config.commit === '9f2c1ab', store.config);

  githubImpl = async () => ({ ok: true, status: 200, json: async () => ({ sha: 'not-a-sha' }) });
  res = await send({ type: 'refreshCommit' });
  check('rejects a bogus sha', res.ok === false, res);

  console.log('\n--- 18. native host is preferred over GitHub ---');
  nativeImpl = () => ({
    ok: true, root: 'D:\\Lab Vin AI\\team-T093', repo: 'P-093', branch: 'main',
    commit: '2b5a5d8', full: '2b5a5d8ffffffffffffffffffffffffffffffff',
    message: 'feat: khoi tao du an', student: 'binhnthe182340@fpt.edu.vn',
    dirty: true, upstream: '', unpushed: '',
  });
  githubImpl = async () => ok202({ sha: 'aaaaaaaaaaaa' }); // must NOT be used
  nativeCalls.length = 0;
  res = await send({ type: 'refreshCommit' });
  check('answered from native', res.source === 'native', res);
  check('local commit wins', res.sha === '2b5a5d8', res);
  check('dirty surfaced', res.dirty === true, res);
  check('github not consulted', (await send({ type: 'getState' })).commitInfo.source === 'native');

  console.log('\n--- 19. falls back to GitHub when the host is absent ---');
  nativeImpl = () => null;
  githubImpl = async () => ({ ok: true, status: 200, json: async () => ({ sha: 'bbbbbbbcccc', commit: { message: 'tu github' } }) });
  res = await send({ type: 'refreshCommit' });
  check('answered from github', res.source === 'github', res);
  check('short sha', res.sha === 'bbbbbbb', res);

  console.log('\n--- 20. neither source available ---');
  githubImpl = async () => ({ ok: false, status: 404, json: async () => ({}) });
  await send({ type: 'saveConfig', config: { githubRepo: '' } });
  res = await send({ type: 'refreshCommit' });
  check('error names both options', res.ok === false && /native host/.test(res.error), res);

  console.log('\n--- 21. adopt the local repo fills four fields at once ---');
  await send({ type: 'saveConfig', config: { repo: 'SAI', branch: 'sai', student: 'sai@x.com' } });
  nativeImpl = () => ({
    ok: true, root: 'D:\\Lab Vin AI\\team-T093', repo: 'P-093', branch: 'main',
    commit: '2b5a5d8', full: '2b5a5d8fff', message: 'feat: khoi tao',
    student: 'binhnthe182340@fpt.edu.vn', dirty: false, upstream: '', unpushed: '',
  });
  res = await send({ type: 'adoptLocalRepo' });
  check('adopt ok', res.ok === true, res);
  let cfgNow = (await send({ type: 'getState' })).config;
  check('repo filled', cfgNow.repo === 'P-093', cfgNow.repo);
  check('branch filled', cfgNow.branch === 'main', cfgNow.branch);
  check('student filled', cfgNow.student === 'binhnthe182340@fpt.edu.vn', cfgNow.student);
  check('commit filled', cfgNow.commit === '2b5a5d8', cfgNow.commit);
  check('repoPath remembered', cfgNow.repoPath === 'D:\\Lab Vin AI\\team-T093', cfgNow.repoPath);

  fetchCalls = [];
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'sau khi adopt' } });
  const stamped = bodyOf(fetchCalls[fetchCalls.length - 1]).entries[0];
  check('entries use the adopted values',
    stamped.repo === 'P-093' && stamped.commit === '2b5a5d8' && stamped.branch === 'main', stamped);

  console.log('\n--- 22. adopt without the host explains how to install ---');
  nativeImpl = () => null;
  res = await send({ type: 'adoptLocalRepo' });
  check('points at the one setup command', res.ok === false && /setup\.cmd/.test(res.error), res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('config untouched on failure', cfgNow.repo === 'P-093', cfgNow.repo);

  console.log('\n--- 23. branch list comes from real refs ---');
  const LOCAL_BRANCHES = {
    ok: true, current: 'feature/x',
    branches: [
      { name: 'main', commit: '2b5a5d8', upstream: 'origin/main', ahead: '0', behind: '0', current: false },
      { name: 'feature/x', commit: 'aa11bb2', upstream: '', ahead: '', behind: '', current: true },
    ],
  };
  nativeImpl = (m) => (m.action === 'branches' ? LOCAL_BRANCHES : null);
  res = await send({ type: 'listBranches' });
  check('from native', res.source === 'native', res);
  check('two branches', res.branches.length === 2, res.branches);
  check('current flagged', res.current === 'feature/x', res);

  console.log('\n--- 24. branch list falls back to GitHub ---');
  nativeImpl = () => null;
  githubImpl = async () => ({
    ok: true, status: 200,
    json: async () => ([
      { name: 'main', commit: { sha: '1111111aaaa' } },
      { name: 'dev', commit: { sha: '2222222bbbb' } },
    ]),
  });
  await send({ type: 'saveConfig', config: { githubRepo: 'AI20K-Build-Cohort-2/P-093' } });
  res = await send({ type: 'listBranches' });
  check('from github', res.source === 'github', res);
  check('sha shortened', res.branches[0].commit === '1111111', res.branches[0]);

  console.log('\n--- 25. auto mode follows the checked-out branch ---');
  // Assert on the recorded calls, not inside the stub: saveConfig itself can
  // trigger a refresh, so a check() living in a stub outlives its section.
  nativeImpl = (m) => (m.action === 'repoinfo'
    ? { ok: true, branch: 'feature/x', commit: 'aa11bb2', full: 'aa11bb2ff', message: 'wip', dirty: false }
    : null);
  await send({ type: 'saveConfig', config: { branchMode: 'auto', branch: 'main' } });
  nativeCalls.length = 0;
  res = await send({ type: 'refreshCommit' });
  check('auto sends no branch', nativeCalls[0][1].branch === undefined, nativeCalls[0][1]);
  check('reports the checked-out branch', res.branch === 'feature/x', res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('config branch followed', cfgNow.branch === 'feature/x', cfgNow.branch);

  fetchCalls = [];
  await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: 'tren branch moi' } });
  const onBranch = bodyOf(fetchCalls[fetchCalls.length - 1]).entries[0];
  check('entry carries that branch', onBranch.branch === 'feature/x', onBranch);
  check('entry carries that commit', onBranch.commit === 'aa11bb2', onBranch);

  console.log('\n--- 26. fixed mode pins a branch ---');
  nativeImpl = (m) => (m.action === 'repoinfo'
    ? { ok: true, branch: 'main', commit: '2b5a5d8', full: '2b5a5d8ff', message: 'khoi tao', dirty: false }
    : null);
  await send({ type: 'saveConfig', config: { branchMode: 'fixed', branch: 'main' } });
  nativeCalls.length = 0;
  res = await send({ type: 'refreshCommit' });
  check('fixed sends the branch', nativeCalls[0][1].branch === 'main', nativeCalls[0][1]);
  check('pinned branch reported', res.branch === 'main', res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('does not drift to the checkout', cfgNow.branch === 'main', cfgNow.branch);

  console.log('\n--- 27. a branch that does not exist fails loudly ---');
  nativeImpl = (m) => (m.action === 'repoinfo'
    ? { ok: false, error: "Không có branch 'sai-ten' trong repo." }
    : null);
  githubImpl = async () => ({ ok: true, status: 200, json: async () => ({ sha: 'ffffffffff' }) });
  await send({ type: 'saveConfig', config: { branch: 'sai-ten' } });
  res = await send({ type: 'refreshCommit' });
  check('surfaces the native error', res.ok === false && /sai-ten/.test(res.error), res);
  check('does not silently use GitHub instead',
    (await send({ type: 'getState' })).config.commit !== 'fffffff',
    (await send({ type: 'getState' })).config.commit);

  console.log('\n--- 28. connect by pasting the repo link ---');
  nativeImpl = () => null; // GitHub-only path
  const GH = {
    '': { name: 'P-093', default_branch: 'main', private: true },
    '/branches?per_page=100': [
      { name: 'main', commit: { sha: '1111111aaaa' } },
      { name: 'feature', commit: { sha: '2222222bbbb' } },
      { name: 'feature/x', commit: { sha: '3333333cccc' } },
    ],
    '/commits/main': { sha: '1111111aaaa', commit: { message: 'khoi tao' } },
    '/commits/feature/x': { sha: '3333333cccc', commit: { message: 'wip' } },
  };
  githubImpl = async (url) => {
    const suffix = String(url).replace('https://api.github.com/repos/AI20K-Build-Cohort-2/P-093', '');
    const body = GH[suffix];
    if (!body) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => body };
  };

  await send({ type: 'saveConfig', config: { branchMode: 'auto', branch: 'main', repo: '', githubRepo: '' } });
  res = await send({ type: 'connectRepo', url: 'https://github.com/AI20K-Build-Cohort-2/P-093' });
  check('connected', res.ok === true, res);
  check('repo name from GitHub', res.repo === 'P-093', res);
  check('default branch used', res.branch === 'main', res);
  check('branch list returned', res.branches.length === 3, res.branches);
  check('private flagged', res.private === true, res);
  check('commit resolved in the same step', res.commit === '1111111', res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('slug stored', cfgNow.githubRepo === 'AI20K-Build-Cohort-2/P-093', cfgNow.githubRepo);
  check('repo stored for the server', cfgNow.repo === 'P-093', cfgNow.repo);

  console.log('\n--- 29. a /tree/ link pins the branch it points at ---');
  res = await send({
    type: 'connectRepo',
    url: 'https://github.com/AI20K-Build-Cohort-2/P-093/tree/feature/x/src/app.js',
  });
  check('branch taken from the link', res.branch === 'feature/x', res);
  check('flagged as from the link', res.branchFromLink === true, res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('switched to fixed mode', cfgNow.branchMode === 'fixed', cfgNow.branchMode);
  check('commit is that branch tip', cfgNow.commit === '3333333', cfgNow.commit);

  console.log('\n--- 30. bad links are refused, config untouched ---');
  const before = (await send({ type: 'getState' })).config;
  res = await send({ type: 'connectRepo', url: 'https://gitlab.com/owner/repo' });
  check('non-github refused', res.ok === false && /github\.com/.test(res.error), res);
  res = await send({ type: 'connectRepo', url: 'khong-phai-link' });
  check('garbage refused', res.ok === false, res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('config unchanged', cfgNow.githubRepo === before.githubRepo && cfgNow.repo === before.repo, cfgNow);

  console.log('\n--- 31. private repo without a token says so ---');
  githubImpl = async () => ({ ok: false, status: 404, json: async () => ({}) });
  res = await send({ type: 'connectRepo', url: 'https://github.com/AI20K-Build-Cohort-2/P-999' });
  check('explains the token', res.ok === false && /token/.test(res.error), res);

  console.log('\n--- 32. testRepoLink only reports, never writes ---');
  githubImpl = async (url) => {
    const suffix = String(url).replace('https://api.github.com/repos/AI20K-Build-Cohort-2/P-093', '');
    const body = GH[suffix];
    if (!body) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => body };
  };
  await send({ type: 'saveConfig', config: { repo: 'GIU-NGUYEN', branch: 'main', branchMode: 'auto' } });
  const untouched = (await send({ type: 'getState' })).config;

  res = await send({ type: 'testRepoLink', url: 'https://github.com/AI20K-Build-Cohort-2/P-093' });
  check('reports the repo', res.ok === true && res.repo === 'P-093', res);
  check('reports branch count', res.branches.length === 3, res.branches);
  check('reports private', res.private === true, res);
  check('flags mismatch with saved repo', res.matchesConfig === false, res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('config not written', cfgNow.repo === untouched.repo && cfgNow.branch === untouched.branch, cfgNow);

  res = await send({ type: 'testRepoLink', url: 'https://github.com/AI20K-Build-Cohort-2/P-093/tree/main' });
  check('resolves a branch from the link', res.branchFromLink === 'main', res);
  res = await send({ type: 'testRepoLink', url: 'https://github.com/AI20K-Build-Cohort-2/P-093/tree/da-xoa' });
  check('flags a branch that no longer exists', res.danglingHint === true, res);

  console.log('\n--- 33. auto-detect fills what the machine knows ---');
  nativeImpl = (m) => (m.action === 'repoinfo' ? {
    ok: true, root: 'D:\\Lab Vin AI\\team-T093', repo: 'P-093', branch: 'main',
    origin: 'https://github.com/AI20K-Build-Cohort-2/P-093.git',
    commit: '2b5a5d8', full: '2b5a5d8ff', message: 'khoi tao',
    student: 'binhnthe182340@fpt.edu.vn', dirty: false,
  } : null);

  // Empty fields get filled...
  await send({ type: 'saveConfig', config: { repo: '', student: '', repoPath: '', githubRepo: '' } });
  res = await send({ type: 'autoDetect' });
  check('detected', res.ok === true, res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('repo filled', cfgNow.repo === 'P-093', cfgNow.repo);
  check('student filled', cfgNow.student === 'binhnthe182340@fpt.edu.vn', cfgNow.student);
  check('repo path filled', cfgNow.repoPath === 'D:\\Lab Vin AI\\team-T093', cfgNow.repoPath);
  check('github slug derived from origin', cfgNow.githubRepo === 'AI20K-Build-Cohort-2/P-093', cfgNow.githubRepo);
  check('commit refreshed', cfgNow.commit === '2b5a5d8', cfgNow.commit);

  // ...but a deliberate edit is never undone on the next restart.
  await send({ type: 'saveConfig', config: { repo: 'TU-SUA', student: 'toi@tu.sua' } });
  await send({ type: 'autoDetect' });
  cfgNow = (await send({ type: 'getState' })).config;
  check('does not clobber an edited repo', cfgNow.repo === 'TU-SUA', cfgNow.repo);
  check('does not clobber an edited email', cfgNow.student === 'toi@tu.sua', cfgNow.student);
  check('but commit still tracks', cfgNow.commit === '2b5a5d8', cfgNow.commit);

  console.log('\n--- 34. auto-detect is a silent no-op without the host ---');
  nativeImpl = () => null;
  const beforeAuto = (await send({ type: 'getState' })).config;
  res = await send({ type: 'autoDetect' });
  check('reports no host', res.ok === false && res.reason === 'no-host', res);
  cfgNow = (await send({ type: 'getState' })).config;
  check('config untouched', JSON.stringify(cfgNow) === JSON.stringify(beforeAuto), cfgNow);

  console.log('\n--- 35. diagnostics name what is wrong ---');
  await send({ type: 'saveConfig', config: Object.assign({ enabled: true }, CONFIG) });
  await send({ type: 'enableSite', host: 'chatgpt.com', tool: 'chatgpt' });
  fetchImpl = async () => ok202(SENT_OK);
  nativeImpl = () => null;

  res = await send({ type: 'runDiagnostics', host: 'chatgpt.com' });
  const byKey = Object.fromEntries(res.steps.map((s) => [s.key, s]));
  check('config step passes', byKey.config.ok === true, byKey.config);
  check('server step passes', byKey.server.ok === true, byKey.server);
  check('native step fails but is optional',
    byKey.native.ok === false && byKey.native.optional === true, byKey.native);
  check('native fix names the setup command', /setup\.cmd/.test(byKey.native.fix), byKey.native.fix);
  check('native fix covers macOS/Linux too', /setup\.sh/.test(byKey.native.fix), byKey.native.fix);
  check('native fix says to restart the browser', /KH.I ..NG L.I/i.test(byKey.native.fix), byKey.native.fix);
  check('active tab is covered', byKey.tab.ok === true, byKey.tab);
  check('optional misses do not block ready', res.ready === true, res);

  console.log('\n--- 36. every failure carries a fix ---');
  await send({ type: 'saveConfig', config: { apiKey: '', repo: '', enabled: false } });
  res = await send({ type: 'runDiagnostics', host: 'khong-bat.example' });
  const failed = res.steps.filter((s) => !s.ok);
  check('several steps fail', failed.length >= 4, failed.map((s) => s.key));
  check('all of them explain how to fix', failed.every((s) => s.fix.length > 10),
    failed.filter((s) => s.fix.length <= 10).map((s) => s.key));
  check('not ready', res.ready === false, res);

  const d2 = Object.fromEntries(res.steps.map((s) => [s.key, s]));
  check('missing key reported', /API Key/.test(d2.config.detail), d2.config);
  check('server skipped rather than guessed', d2.server.ok === false, d2.server);
  check('master switch off is reported', d2.enabled.ok === false, d2.enabled);
  check('uncovered tab flagged as optional', d2.tab.optional === true, d2.tab);
  await send({ type: 'saveConfig', config: Object.assign({ enabled: true }, CONFIG) });

  console.log('\n--- 37. junk input ---');
  res = await send({ type: 'capture', entry: { tool: 'chatgpt', prompt: '   ' } });
  check('whitespace-only rejected', res.error === 'empty-prompt', res);
  res = await send({ type: 'nonsense' });
  check('unknown message handled', res.error === 'unknown-message', res);

  console.log(failures === 0 ? '\nALL PASS\n' : `\n${failures} FAILURE(S)\n`);
  process.exit(failures ? 1 : 0);
})();
