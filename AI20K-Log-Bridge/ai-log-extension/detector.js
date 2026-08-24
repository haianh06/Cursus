/*
 * Runs on every page. Answers one question — "does this look like an AI chat?"
 * — and nothing else.
 *
 * It reads STRUCTURE only: how many editable boxes exist, whether a send
 * control is present, how many repeated turn blocks there are, and the
 * hostname. It never reads what you typed, never touches request bodies, and
 * never sends page text anywhere. Capture only starts after you enable a site
 * from the popup, and that is a different script entirely.
 */
(function () {
  'use strict';

  if (window.__ailogDetector) return;
  window.__ailogDetector = true;

  var THRESHOLD = 5;
  var HOST_HINT = /(chat|ai|gpt|claude|gemini|copilot|perplexity|mistral|deepseek|grok|llm|assistant)/i;

  function visible(el) {
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function scan() {
    var score = 0;
    var signals = [];

    var editors = [];
    var all = document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]');
    for (var i = 0; i < all.length && i < 200; i++) {
      if (!visible(all[i])) continue;
      var r = all[i].getBoundingClientRect();
      if (r.width >= 180 && r.height >= 20) editors.push(all[i]);
    }
    if (editors.length) {
      score += 3;
      signals.push('composer');
    }

    if (document.querySelector(
      'button[aria-label*="send" i], button[data-testid*="send" i], ' +
      'button[aria-label*="submit" i], button[type="submit"], ' +
      'button[aria-label*="gửi" i]'
    )) {
      score += 2;
      signals.push('send-button');
    }

    var turns = document.querySelectorAll(
      '[data-message-author-role], [data-testid*="conversation-turn" i], ' +
      '[data-testid*="message" i], article'
    );
    if (turns.length >= 2) {
      score += 2;
      signals.push('turns');
    }

    if (HOST_HINT.test(location.hostname)) {
      score += 2;
      signals.push('hostname');
    }

    return { score: score, signals: signals };
  }

  function report() {
    var res = scan();
    if (res.score < THRESHOLD) return;
    try {
      chrome.runtime.sendMessage({
        type: 'detected',
        host: location.hostname,
        score: res.score,
        signals: res.signals,
      }, function () { void chrome.runtime.lastError; });
    } catch (err) { /* extension reloaded — the next page load re-reports */ }
  }

  // Chat UIs mount late and re-route without a reload, so sample a few times.
  report();
  setTimeout(report, 2500);
  setTimeout(report, 7000);

  var lastUrl = location.href;
  setInterval(function () {
    if (location.href === lastUrl) return;
    lastUrl = location.href;
    setTimeout(report, 1500);
  }, 2000);
})();
