/*
 * Per-site adapters.
 *
 * Every field except `hosts` and `tool` is optional — the generic fallbacks at
 * the bottom of each selector list carry sites we have no specific entry for.
 * That matters because these DOM selectors are the brittle part of the whole
 * extension: ChatGPT and Claude reship their composer regularly. When a
 * specific selector dies the generic one usually still catches the prompt, and
 * if even that misses, the popup is always there as a manual fallback.
 *
 * Loaded as a plain script in both the content script and the popup, so it
 * declares one global and guards against double injection.
 */
var AILOG = AILOG || (function () {
  'use strict';

  // Tried in order; first match that holds text wins.
  var GENERIC_COMPOSER = [
    'textarea',
    'div[contenteditable="true"]',
    'div[role="textbox"]',
  ];

  var GENERIC_SEND = [
    'button[type="submit"]',
    'button[aria-label*="Send" i]',
    'button[aria-label*="Submit" i]',
    'button[data-testid*="send" i]',
  ];

  var ADAPTERS = [
    {
      id: 'chatgpt',
      label: 'ChatGPT',
      tool: 'chatgpt',
      hosts: ['chatgpt.com', 'chat.openai.com'],
      composer: [
        '#prompt-textarea',
        'textarea[data-testid="prompt-textarea"]',
        'div[contenteditable="true"]',
      ],
      send: [
        'button[data-testid="send-button"]',
        'button[aria-label*="Send" i]',
      ],
      model: [
        '[data-testid="model-switcher-dropdown-button"]',
        'button[aria-label*="Model" i]',
      ],
    },
    {
      id: 'claude',
      label: 'Claude.ai',
      tool: 'claude-web',
      hosts: ['claude.ai'],
      composer: [
        'div[contenteditable="true"].ProseMirror',
        'div[contenteditable="true"]',
        'textarea',
      ],
      send: [
        'button[aria-label="Send message"]',
        'button[aria-label*="Send" i]',
      ],
      model: [
        'button[data-testid="model-selector-dropdown"]',
        'button[aria-label*="model" i]',
      ],
    },
    {
      id: 'gemini',
      label: 'Google Gemini',
      tool: 'gemini-web',
      hosts: ['gemini.google.com'],
      composer: [
        'rich-textarea div[contenteditable="true"]',
        '.ql-editor',
        'div[contenteditable="true"]',
      ],
      send: [
        'button.send-button',
        'button[aria-label*="Send" i]',
      ],
      model: ['.current-mode-title', 'button[class*="model" i]'],
    },
    {
      id: 'aistudio',
      label: 'Google AI Studio',
      tool: 'ai-studio',
      hosts: ['aistudio.google.com'],
      composer: [
        'ms-autosize-textarea textarea',
        'textarea[aria-label*="prompt" i]',
        'textarea',
      ],
      send: [
        'button[aria-label*="Run" i]',
        'run-button button',
      ],
      model: ['ms-model-selector', '[data-test-id="model-selector"]'],
    },
    {
      id: 'perplexity',
      label: 'Perplexity',
      tool: 'perplexity',
      hosts: ['perplexity.ai', 'www.perplexity.ai'],
      composer: [
        'textarea[placeholder*="Ask" i]',
        'div[contenteditable="true"]',
        'textarea',
      ],
      send: [
        'button[aria-label*="Submit" i]',
        'button[data-testid="submit-button"]',
      ],
      model: ['button[data-testid="model-selector"]'],
    },
    {
      id: 'deepseek',
      label: 'DeepSeek',
      tool: 'deepseek',
      hosts: ['chat.deepseek.com'],
      composer: ['textarea#chat-input', 'textarea'],
      send: ['div[role="button"][aria-disabled="false"]', 'button[type="submit"]'],
      model: [],
    },
    {
      id: 'grok',
      label: 'Grok',
      tool: 'grok',
      hosts: ['grok.com'],
      composer: ['textarea[aria-label*="Ask" i]', 'textarea', 'div[contenteditable="true"]'],
      send: ['button[type="submit"]', 'button[aria-label*="Submit" i]'],
      model: [],
    },
  ];

  /* A site the user added themselves in the popup. No hand-tuned selectors —
     it leans entirely on the generic ones. */
  function customAdapter(host, tool) {
    return {
      id: 'custom:' + host,
      label: host,
      tool: tool || host.replace(/^www\./, ''),
      hosts: [host],
      composer: [],
      send: [],
      model: [],
      custom: true,
    };
  }

  function hostMatches(hostname, host) {
    hostname = String(hostname || '').toLowerCase();
    host = String(host || '').toLowerCase();
    return hostname === host || hostname.endsWith('.' + host);
  }

  /* customSites: [{host, tool}] from storage — checked after the built-ins so a
     user entry can't shadow a hand-tuned adapter by accident. */
  function pickAdapter(hostname, customSites) {
    for (var i = 0; i < ADAPTERS.length; i++) {
      for (var j = 0; j < ADAPTERS[i].hosts.length; j++) {
        if (hostMatches(hostname, ADAPTERS[i].hosts[j])) return ADAPTERS[i];
      }
    }
    var list = customSites || [];
    for (var k = 0; k < list.length; k++) {
      if (list[k] && list[k].host && hostMatches(hostname, list[k].host)) {
        return customAdapter(list[k].host, list[k].tool);
      }
    }
    return null;
  }

  function selectorsFor(adapter, kind) {
    var own = (adapter && adapter[kind]) || [];
    var generic = kind === 'composer' ? GENERIC_COMPOSER
                : kind === 'send'     ? GENERIC_SEND
                : [];
    return own.concat(generic);
  }

  return {
    ADAPTERS: ADAPTERS,
    pickAdapter: pickAdapter,
    selectorsFor: selectorsFor,
    hostMatches: hostMatches,
  };
})();
