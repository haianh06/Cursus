/*
 * Isolated-world script for sites you enabled. Two jobs:
 *   1. Composer capture — watch the box you type in and log what you send.
 *   2. Toast — tell you whether that got logged.
 *
 * It reads ONE thing: the composer you typed in. There used to be a second
 * path that sniffed outgoing requests, and it was removed because it could not
 * tell your prompt from the site's own traffic — it logged "Turn exchange
 * complete" and "Failed to fetch persisted textdocs" alongside real prompts.
 * Reading the composer cannot produce anything you did not type.
 *
 * Two triggers, because one is fast and one is general:
 *   - Enter on the composer fires immediately (instant feedback)
 *   - the composer emptying right after a key or click confirms a send on ANY
 *     site, whatever its send button looks like
 * Both funnel through capture(), and the service worker collapses the overlap.
 *
 * It must NOT post to the server directly: this code runs under the page's
 * origin and the grading server answers every browser origin with
 * "Disallowed CORS origin". Only the service worker is exempt.
 */
(function () {
  'use strict';

  if (window.__ailogBridgeLoaded) return;
  window.__ailogBridgeLoaded = true;

  var MIN_PROMPT_LEN = 2;
  var MAX_PROMPT_LEN = 1000;
  var LOCAL_DEDUPE_MS = 5000;
  var POLL_MS = 250;

  // siteOn is re-read from storage rather than baked in at injection time, so
  // turning a site off takes effect in tabs that are already open.
  var state = { enabled: true, toast: true, tool: null, siteOn: true };
  var adapter = null;
  var last = { text: '', at: 0 };

  var tracker = AILOG_COMPOSER.createTracker();
  var watched = null;   // the composer element currently holding a draft
  var timer = null;

  /* ---------- state ---------- */

  function loadState(done) {
    try {
      chrome.storage.local.get(['config', 'enabledSites'], function (data) {
        if (chrome.runtime.lastError) return done();
        var cfg = data.config || {};
        state.enabled = cfg.enabled !== false;
        state.toast = cfg.toast !== false;

        applySites(data.enabledSites || []);
        done();
      });
    } catch (err) {
      done();
    }
  }

  function applySites(sites) {
    state.siteOn = false;
    for (var i = 0; i < sites.length; i++) {
      if (AILOG.hostMatches(location.hostname, sites[i].host)) {
        state.tool = sites[i].tool;
        state.siteOn = true;
        return;
      }
    }
  }

  function active() {
    return state.enabled && state.siteOn;
  }

  function toolName() {
    return state.tool || (adapter && adapter.tool) || location.hostname.replace(/^www\./, '');
  }

  /* ---------- DOM helpers ---------- */

  function readComposer(el) {
    if (!el) return '';
    if (typeof el.value === 'string') return el.value;
    return el.innerText || el.textContent || '';
  }

  function composerFrom(node) {
    if (!node || !node.closest) return null;
    return node.closest(
      'textarea, input[type="text"], input[type="search"], ' +
      '[contenteditable="true"], [contenteditable=""], [role="textbox"]'
    );
  }

  function detectModel() {
    var sels = (adapter && adapter.model) || [];
    for (var i = 0; i < sels.length; i++) {
      var el;
      try {
        el = document.querySelector(sels[i]);
      } catch (err) {
        continue;
      }
      if (el) {
        var txt = (el.innerText || el.textContent || '').trim();
        if (txt && txt.length < 60) return txt.replace(/\s+/g, ' ');
      }
    }
    return '';
  }

  /* ---------- capture ---------- */

  function capture(text, via) {
    if (!active()) return;
    text = (text || '').trim();
    if (text.length < MIN_PROMPT_LEN) return;

    var now = Date.now();
    // Enter and the composer-cleared check both fire for one send; collapse
    // them here so the service worker never sees the pair.
    if (text === last.text && now - last.at < LOCAL_DEDUPE_MS) return;
    last = { text: text, at: now };

    try {
      chrome.runtime.sendMessage({
        type: 'capture',
        entry: {
          tool: toolName(),
          model: detectModel(),
          prompt: text.slice(0, MAX_PROMPT_LEN),
          via: via,
        },
      }, function (res) {
        if (chrome.runtime.lastError) return;
        if (!res) return;
        if (res.status === 'held') showToast('Chờ bạn duyệt', false);
        else if (res.status === 'sent') showToast('Đã ghi log', true);
        else if (res.status === 'queued') showToast('Đã xếp hàng — chờ gửi lại', false);
        else if (res.status === 'rejected') showToast('Server từ chối — kiểm tra tên repo', false, true);
        else if (res.status === 'duplicate') { /* silent by design */ }
        else if (res.error && res.error !== 'disabled') showToast('Log lỗi: ' + res.error, false, true);
      });
    } catch (err) {
      showToast('Extension vừa reload — tải lại trang để tiếp tục log', false, true);
    }
  }

  /* ---------- composer tracking ---------- */

  function startPolling() {
    if (timer) return;
    timer = setInterval(poll, POLL_MS);
  }

  function stopPolling() {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  }

  function poll() {
    if (!watched || !tracker.pending()) {
      stopPolling();
      return;
    }
    // Some editors replace the composer node on send rather than emptying it.
    var connected = watched.isConnected !== false;
    var text = connected ? readComposer(watched) : '';
    var got = tracker.onTick(text, Date.now(), connected);
    if (got) {
      capture(got, 'dom:sent');
      watched = null;
      stopPolling();
    } else if (!tracker.pending()) {
      watched = null;
      stopPolling();
    }
  }

  function onInput(e) {
    if (!active()) return;
    var el = composerFrom(e.target);
    if (!el) return;
    watched = el;
    tracker.onInput(readComposer(el));
    if (tracker.pending()) startPolling();
  }

  /* ---------- events ---------- */

  function onKeydown(e) {
    if (e.key !== 'Enter') return;
    // Vietnamese IME: Enter mid-composition commits the word, it does not send.
    if (e.isComposing || e.keyCode === 229) return;

    // Any Enter is a plausible send — Shift+Enter is a newline everywhere, but
    // Ctrl/Cmd+Enter is the send shortcut on several sites.
    if (!e.shiftKey && !e.altKey) tracker.onIntent(Date.now());

    if (e.shiftKey || e.altKey) return;
    var el = composerFrom(e.target);
    if (!el) return;
    var text = readComposer(el);
    if (!text.trim()) return;
    capture(text, 'dom:enter');
    tracker.forget(); // the clear that follows must not fire a second time
    watched = null;
    stopPolling();
  }

  /* Any click may be a send. This only arms the window — the composer going
     empty is what confirms it — so there is no need to know what the site's
     send button looks like. */
  function onClick(e) {
    var node = e.target;
    if (!node || !node.closest) return;
    if (!node.closest('button, div[role="button"], span[role="button"], a[role="button"], [type="submit"]')) return;
    tracker.onIntent(Date.now());
  }

  function onSubmit() {
    tracker.onIntent(Date.now());
  }

  /* ---------- toast ---------- */

  var toastEl = null;
  var toastTimer = null;

  function showToast(msg, success, isError) {
    if (!state.toast) return;
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.style.cssText = [
        'position:fixed', 'z-index:2147483647', 'bottom:20px', 'right:20px',
        'padding:9px 14px', 'border-radius:8px', 'font:500 13px/1.4 system-ui,sans-serif',
        'color:#fff', 'pointer-events:none', 'opacity:0',
        'transition:opacity .18s ease', 'box-shadow:0 4px 14px rgba(0,0,0,.28)',
      ].join(';');
      document.documentElement.appendChild(toastEl);
    }
    toastEl.textContent = 'AI20K · ' + msg;
    toastEl.style.background = isError ? '#c0392b' : (success ? '#1e8e4f' : '#b8860b');
    toastEl.style.opacity = '1';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.style.opacity = '0'; }, 2200);
  }

  /* ---------- boot ---------- */

  loadState(function () {
    // Known sites get hand-tuned selectors for the model readout; the capture
    // itself needs none, which is what lets a brand-new AI chat work unmodified.
    adapter = AILOG.pickAdapter(location.hostname, []) || null;
    document.addEventListener('input', onInput, true);
    document.addEventListener('keydown', onKeydown, true);
    document.addEventListener('click', onClick, true);
    document.addEventListener('submit', onSubmit, true);
  });

  /* Live re-read: flipping either switch in the popup takes effect in tabs
     that are already open, with no reload. */
  chrome.storage.onChanged.addListener(function (changes, area) {
    if (area !== 'local') return;
    if (changes.config) {
      var cfg = changes.config.newValue || {};
      state.enabled = cfg.enabled !== false;
      state.toast = cfg.toast !== false;
    }
    if (changes.enabledSites) applySites(changes.enabledSites.newValue || []);
    if (!active()) {
      // Drop any half-typed draft so it cannot surface after being turned off.
      tracker.forget();
      watched = null;
      stopPolling();
    }
  });
})();
