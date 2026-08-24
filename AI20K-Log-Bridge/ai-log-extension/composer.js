/*
 * Decides when what you typed counts as "sent".
 *
 * Watching for Enter, or for a click on a known send button, only works on
 * sites we already have selectors for. This works anywhere, because every chat
 * UI does the same two things: it clears the composer after a send, and the
 * send was triggered by a key or a click.
 *
 *   you type          -> remember the text
 *   key / click       -> note the intent
 *   composer empties  -> if that happened right after an intent, it was a send
 *
 * The intent window is what keeps a manual select-all-delete from being logged
 * as a prompt: clearing the box by hand has no key-or-click intent in front of
 * it, so it produces nothing.
 *
 * Pure state machine with no DOM access so it can be tested directly; the
 * caller feeds it text and timestamps.
 */
var AILOG_COMPOSER = AILOG_COMPOSER || (function () {
  'use strict';

  var DEFAULT_INTENT_MS = 2000;
  var MIN_LEN = 2;

  function createTracker(opts) {
    opts = opts || {};
    var intentMs = opts.intentMs || DEFAULT_INTENT_MS;
    var state = { text: '', intentAt: 0 };

    return {
      /* Called on every input event while you type. */
      onInput: function (text) {
        if (text && text.trim()) state.text = text;
      },

      /* Called on Enter, on any button click, and on form submit. Cheap on
         purpose — it only arms the window, it never captures by itself. */
      onIntent: function (now) {
        state.intentAt = now;
      },

      /* Poll while there is text pending. Returns the prompt to log, or ''.
         connected=false means the site replaced the composer node outright,
         which some editors do instead of clearing it. */
      onTick: function (currentText, now, connected) {
        if (!state.text) return '';

        var gone = connected === false;
        var empty = !currentText || !currentText.trim();
        if (!gone && !empty) {
          state.text = currentText; // still typing
          return '';
        }

        var captured = state.text;
        var confirmed = state.intentAt > 0 && (now - state.intentAt) <= intentMs;
        state.text = '';
        state.intentAt = 0;

        if (!confirmed) return '';                    // cleared by hand
        if (captured.trim().length < MIN_LEN) return '';
        return captured;
      },

      /* After a direct capture (Enter handled inline) so the clear that
         follows does not produce a second one. */
      forget: function () {
        state.text = '';
        state.intentAt = 0;
      },

      pending: function () {
        return state.text;
      },
    };
  }

  return { createTracker: createTracker };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = AILOG_COMPOSER;
