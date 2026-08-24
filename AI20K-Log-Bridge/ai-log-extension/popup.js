/* Popup: hàng đợi duyệt, cấu hình, nhập tay, quản lý site.
 *
 * Quy tắc đặt thông báo — mỗi thông báo nằm cạnh thứ đã tạo ra nó:
 *
 *   #state<X>     điều kiện thường trực của mục X (chưa cấu hình, N chờ gửi).
 *                 Vẽ lại mỗi lần render nên luôn phản ánh đúng hiện trạng.
 *   say('msg<X>') kết quả của nút bạn vừa bấm trong nhóm X.
 *
 * Hai loại là hai phần tử khác nhau, vì một lần render không được phép xoá mất
 * thông báo bạn chưa kịp đọc.
 *
 * Mục Cấu hình có ba nhóm nút rời nhau nên có ba ô riêng — msgServer, msgRepo,
 * msgBranch — thay vì một ô chung ở đáy: bấm nút ở đầu mục mà chữ hiện tận
 * cuối thì coi như không thấy.
 */
'use strict';

const $ = (id) => document.getElementById(id);

function send(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, (res) => {
      if (chrome.runtime.lastError) return resolve({ ok: false, error: chrome.runtime.lastError.message });
      resolve(res || { ok: false, error: 'no-response' });
    });
  });
}

let state = null;
let currentHost = '';
/* Danh sách branch lấy theo yêu cầu, không lấy mỗi lần render — nó tốn một lần
   gọi native host hoặc một vòng mạng tới GitHub. */
let branchList = null;
let diag = null;

/* ---------- icon ---------- */

const ICON = { ok: 'i-check', err: 'i-alert', warn: 'i-bang', info: 'i-info' };

function svgIcon(name, cls) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'ic ' + (cls || 'ic-sm'));
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#' + name);
  svg.appendChild(use);
  return svg;
}

/* ---------- thông báo ---------- */

function paint(el, text, kind, actions) {
  if (!el) return;
  el.innerHTML = '';
  if (!text) return;

  const box = document.createElement('div');
  box.className = 'note ' + (kind || 'warn');
  box.appendChild(svgIcon(ICON[kind] || ICON.warn));

  const body = document.createElement('span');
  body.className = 'txt2';
  body.textContent = text;

  if (actions && actions.length) {
    const row = document.createElement('span');
    row.className = 'btn-row';
    actions.forEach((a) => {
      const b = document.createElement('button');
      b.textContent = a.label;
      b.className = (a.ghost ? 'ghost ' : '') + 'sm';
      b.addEventListener('click', a.onClick);
      row.appendChild(b);
    });
    body.appendChild(row);
  }

  box.appendChild(body);
  el.appendChild(box);
}

const sayTimers = {};

/* Báo thành công thì tự tắt; báo lỗi thì ở lại tới thao tác kế — một lỗi bạn
   chưa kịp đọc là một lỗi bạn sẽ gặp lại. */
function say(slot, text, kind, actions) {
  const el = $(slot);
  if (!el) return;
  clearTimeout(sayTimers[slot]);
  paint(el, text, kind, actions);
  if (kind === 'ok') sayTimers[slot] = setTimeout(() => paint(el, ''), 6000);
}

const busy = (slot, text) => say(slot, text, 'warn');

/* ---------- đóng mở mục ---------- */

function openSection(id) {
  const sec = $(id);
  if (!sec) return;
  sec.classList.add('open');
  sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.querySelectorAll('.sec .head').forEach((h) => {
  h.addEventListener('click', () => $(h.dataset.target).classList.toggle('open'));
});

document.querySelectorAll('[data-jump]').forEach((el) => {
  el.addEventListener('click', () => openSection(el.dataset.jump));
});

/* ---------- thanh repo ---------- */

/* Đáng có một hàng riêng: gửi entry dưới repo hoặc branch sai thì server lặng
   lẽ bỏ qua, nên phải thấy được mà không cần mở gì. */
function renderRepoBar() {
  const cfg = state.config || {};
  const ci = state.commitInfo;

  const chip = (id, icon, value) => {
    const el = $(id);
    el.classList.toggle('none', !value);
    el.innerHTML = '';
    el.appendChild(svgIcon(icon));
    const b = document.createElement('b');
    b.textContent = value || 'chưa có';
    el.appendChild(b);
  };

  chip('barRepo', 'i-folder', cfg.repo);
  chip('barBranch', 'i-branch', cfg.branch);
  chip('barCommit', 'i-commit', cfg.commit);

  const flag = $('barFlag');
  let note = '';
  if (cfg.branchMode === 'fixed') note = 'branch đã ghim';
  if (ci && ci.unpushed && ci.unpushed !== '0') note = `${ci.unpushed} commit chưa push`;
  if (ci && ci.dirty) note = 'có thay đổi chưa commit';
  flag.style.display = note ? '' : 'none';
  if (note) {
    flag.innerHTML = '';
    flag.appendChild(svgIcon('i-alert'));
    const b = document.createElement('b');
    b.textContent = note;
    flag.appendChild(b);
  }

  const src = ci ? (ci.source === 'native' ? 'đọc từ repo trên máy' : 'lấy từ GitHub') : 'chưa lấy commit';
  $('repoBar').title =
    `${cfg.repo || 'chưa có repo'} · ${cfg.branch || 'chưa có branch'} · ${cfg.commit || 'chưa có commit'}\n${src}` +
    (cfg.branchMode === 'fixed' ? '\nĐang ghim branch.' : '\nTheo branch repo đang checkout.') +
    '\n\nBấm để mở phần Cấu hình.';
}

/* ---------- trang hiện tại ---------- */

function siteEntry() {
  if (!currentHost) return null;
  return (state.enabledSites || []).find(
    (s) => currentHost === s.host || currentHost.endsWith('.' + s.host)
  ) || null;
}

function renderSiteCard() {
  const card = $('siteCard');
  if (!currentHost) {
    card.style.display = 'none';
    return;
  }
  card.style.display = '';

  const on = !!siteEntry();
  const masterOff = state.config.enabled === false;

  $('siteHost').firstChild.nodeValue = currentHost;
  $('siteState').textContent = masterOff
    ? 'toàn bộ đang tắt'
    : on ? 'đang ghi log trang này' : 'không ghi log trang này';
  $('siteToggle').classList.toggle('on', on && !masterOff);
  $('siteToggle').disabled = masterOff;

  // Gợi ý bật cho site lạ — thuộc về đúng thẻ này, không phải đầu popup.
  const detected = state.detected || {};
  const hit = Object.keys(detected).find(
    (h) => h === currentHost || currentHost.endsWith('.' + h) || h.endsWith('.' + currentHost)
  );

  if (masterOff) {
    paint($('stateSite'), 'Ghi log đang TẮT trên mọi trang.', 'warn',
      [{ label: 'Bật lại', onClick: () => setEnabled(true) }]);
  } else if (hit && !on) {
    paint($('stateSite'), `Trang này trông giống một AI chat. Bật log cho ${hit}?`, 'info', [
      { label: 'Bật log', onClick: async () => { await send({ type: 'enableSite', host: hit }); await refresh(); } },
      { label: 'Bỏ qua', ghost: true, onClick: async () => { await send({ type: 'dismissDetected', host: hit }); await refresh(); } },
    ]);
  } else {
    paint($('stateSite'), '');
  }
}

/* ---------- hàng đợi ---------- */

function renderQueueCard() {
  const cfg = state.config || {};
  const pending = (state.pending || []).length;
  const queued = (state.queue || []).length;
  const rejected = (state.rejected || []).length;

  const review = cfg.mode !== 'auto';
  $('modeReview').classList.toggle('on', review);
  $('modeAuto').classList.toggle('on', !review);
  // Hai chữ trên nút không nói ra rằng một trong hai gửi đi mà không hỏi lại.
  $('modeHint').textContent = review
    ? 'Prompt bắt được sẽ đợi bạn duyệt, không tự gửi đi đâu.'
    : 'Prompt bắt được sẽ gửi thẳng lên server, không hỏi lại.';

  $('statPending').textContent = pending;
  $('statQueue').textContent = queued;
  $('statSent').textContent = (state.history || []).filter((h) => h.status === 'sent').length;
  $('statRejected').textContent = rejected;
  $('statRejectedBox').classList.toggle('hot', rejected > 0);
  $('rejectedActions').style.display = rejected ? 'flex' : 'none';

  if (rejected) {
    paint($('stateQueue'),
      state.lastError ? state.lastError.message : `${rejected} entry bị server từ chối.`, 'err');
  } else if (state.lastError) {
    paint($('stateQueue'), state.lastError.message, 'err');
  } else if (queued) {
    paint($('stateQueue'), `${queued} entry đang chờ gửi — tự thử lại mỗi phút.`, 'warn');
  } else {
    paint($('stateQueue'), '');
  }
}

/* ---------- checklist cài đặt ---------- */

function renderSetup() {
  const ol = $('setupSteps');
  if (!diag) {
    ol.innerHTML = '<li class="empty">Bấm "Kiểm tra tất cả" để soi từng bước.</li>';
    $('setupCount').textContent = '—';
    return;
  }
  ol.innerHTML = '';
  diag.steps.forEach((s) => {
    const li = document.createElement('li');
    li.className = s.ok ? 'ok' : (s.optional ? 'opt' : 'bad');

    const mark = document.createElement('span');
    mark.className = 'mark';
    mark.appendChild(svgIcon(s.ok ? 'i-check' : (s.optional ? 'i-bang' : 'i-x')));

    const what = document.createElement('span');
    what.className = 'what';
    const title = document.createElement('b');
    title.textContent = s.title;
    const detail = document.createElement('span');
    detail.textContent = s.detail;
    what.append(title, detail);
    if (!s.ok && s.fix) {
      const fix = document.createElement('span');
      fix.className = 'fix';
      fix.textContent = s.fix;
      what.appendChild(fix);
    }

    li.append(mark, what);
    ol.appendChild(li);
  });
  $('setupCount').textContent = `${diag.passed}/${diag.total}`;
}

/* ---------- danh sách ---------- */

/* Một hàng dùng chung cho cả hai danh sách. Bấm vào là mở toàn văn — danh sách
   cắt còn hai dòng để prompt dài không đẩy mọi thứ khác ra khỏi màn hình, mà
   bạn vẫn phải đọc hết trước khi quyết định gửi. */
function entryRow({ id, prompt, tag, tagClass, meta, fields, checkable }) {
  const li = document.createElement('li');
  li.className = 'entry';

  if (checkable) {
    const wrap = document.createElement('label');
    wrap.className = 'pickwrap';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.id = id;
    wrap.addEventListener('click', (e) => e.stopPropagation()); // tick ≠ mở
    wrap.appendChild(cb);
    li.appendChild(wrap);
  } else if (tag) {
    const t = document.createElement('span');
    t.className = 'tag ' + (tagClass || '');
    t.textContent = tag;
    li.appendChild(t);
  }

  const txt = document.createElement('span');
  txt.className = 'txt';

  const line = document.createElement('span');
  line.className = 'line';
  line.textContent = prompt;

  const metaEl = document.createElement('span');
  metaEl.className = 'meta';
  metaEl.textContent = meta;

  const detail = document.createElement('div');
  detail.className = 'detail';
  const pre = document.createElement('pre');
  pre.textContent = prompt;
  detail.appendChild(pre);

  const dl = document.createElement('dl');
  dl.className = 'kv';
  fields.filter(([, v]) => v).forEach(([k, v]) => {
    const dt = document.createElement('dt');
    dt.textContent = k;
    const dd = document.createElement('dd');
    dd.textContent = v;
    dl.append(dt, dd);
  });
  detail.appendChild(dl);

  const row = document.createElement('div');
  row.className = 'btn-row tight';
  const copy = document.createElement('button');
  copy.className = 'ghost sm';
  copy.appendChild(svgIcon('i-copy'));
  copy.append('Chép prompt');
  copy.addEventListener('click', async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(prompt);
      copy.lastChild.textContent = 'Đã chép';
      setTimeout(() => { copy.lastChild.textContent = 'Chép prompt'; }, 1500);
    } catch (err) {
      copy.lastChild.textContent = 'Không chép được';
    }
  });
  row.appendChild(copy);
  detail.appendChild(row);

  txt.append(line, metaEl, detail);
  li.append(txt, svgIcon('i-chev', 'caret'));
  li.title = 'Bấm để xem toàn bộ prompt';
  li.addEventListener('click', () => li.classList.toggle('open'));
  return li;
}

function renderPending() {
  const ul = $('pendingList');
  ul.innerHTML = '';
  const items = state.pending || [];
  $('pendingCount').textContent = items.length;

  paint($('statePending'), items.length
    ? `${items.length} prompt đang chờ bạn duyệt — chưa có gì được gửi đi.`
    : '', 'info');

  if (!items.length) {
    ul.innerHTML = '<li class="empty">Chưa có prompt nào chờ duyệt.</li>';
    return;
  }
  items.forEach((p) => {
    const e = p.entry;
    ul.appendChild(entryRow({
      id: p.id,
      prompt: e.prompt,
      meta: `${e.tool} · ${String(p.at || '').slice(11, 16)}` +
        (e.model ? ` · ${e.model}` : '') + (p.via ? ` · ${p.via}` : ''),
      // Hiện ra vì đây là thứ entry sẽ được ghi kèm, và sai repo thì server bỏ.
      fields: [
        ['Thời gian', String(e.ts || p.at || '').slice(0, 19).replace('T', ' ')],
        ['Tool', e.tool],
        ['Model', e.model],
        ['Bắt bằng', p.via],
        ['Repo', e.repo],
        ['Branch', e.branch],
        ['Commit', e.commit],
        ['Độ dài', e.prompt ? e.prompt.length + ' ký tự' : ''],
      ],
      checkable: true,
    }));
  });
}

function renderHistory() {
  const ul = $('historyList');
  ul.innerHTML = '';
  const items = state.history || [];
  $('historyCount').textContent = items.length;
  if (!items.length) {
    ul.innerHTML = '<li class="empty">Chưa gửi log nào.</li>';
    return;
  }
  items.forEach((h) => {
    ul.appendChild(entryRow({
      prompt: h.prompt,
      tag: h.tool,
      tagClass: h.status,
      meta: String(h.ts || '').slice(0, 16).replace('T', ' ') +
        (h.status === 'rejected' ? ' · bị từ chối' : ' · đã gửi'),
      fields: [
        ['Thời gian', String(h.ts || '').slice(0, 19).replace('T', ' ')],
        ['Tool', h.tool],
        ['Trạng thái', h.status === 'rejected' ? 'server từ chối' : 'server đã nhận'],
        ['Độ dài', h.prompt ? h.prompt.length + ' ký tự' : ''],
      ],
      checkable: false,
    }));
  });
}

function renderSites() {
  const ul = $('sitesList');
  ul.innerHTML = '';
  const sites = state.enabledSites || [];
  $('sitesCount').textContent = sites.length;
  if (!sites.length) {
    ul.innerHTML = '<li class="empty">Chưa bật site nào.</li>';
    return;
  }
  sites.forEach((s) => {
    const li = document.createElement('li');
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = s.tool;
    const txt = document.createElement('span');
    txt.className = 'txt';
    txt.textContent = s.host;
    const del = document.createElement('button');
    del.className = 'ghost sm';
    del.textContent = 'Tắt';
    del.addEventListener('click', async () => {
      await send({ type: 'disableSite', host: s.host });
      await refresh();
      say('msgSites', `Đã tắt log cho ${s.host} — có hiệu lực ngay.`, 'ok');
    });
    li.append(tag, txt, del);
    ul.appendChild(li);
  });
}

function renderTools() {
  const sel = $('mTool');
  const want = AILOG.ADAPTERS.map((a) => ({ value: a.tool, label: a.label }))
    .concat((state.enabledSites || []).map((s) => ({ value: s.tool, label: s.host })));
  const seen = new Set();
  const opts = want.filter((o) => (seen.has(o.value) ? false : seen.add(o.value)));
  opts.push({ value: 'other', label: 'Khác…' });

  const prev = sel.value;
  sel.innerHTML = '';
  opts.forEach((o) => {
    const opt = document.createElement('option');
    opt.value = o.value;
    opt.textContent = o.label;
    sel.appendChild(opt);
  });
  if (prev) sel.value = prev;
}

function renderBranches() {
  const cfg = state.config || {};
  const pinned = cfg.branchMode === 'fixed';
  $('branchAuto').classList.toggle('on', !pinned);
  $('branchFixed').classList.toggle('on', pinned);

  const sel = $('cBranch');
  sel.disabled = !pinned;
  sel.innerHTML = '';

  const names = branchList && branchList.ok ? branchList.branches.map((b) => b.name) : [];
  // Giữ branch đang cấu hình luôn chọn được, kể cả khi chưa nạp danh sách —
  // một lần render không được phép đổi branch mà entry sẽ mang.
  if (cfg.branch && names.indexOf(cfg.branch) === -1) names.unshift(cfg.branch);
  if (!names.length) names.push(cfg.branch || 'main');

  names.forEach((n) => {
    const o = document.createElement('option');
    o.value = n;
    const b = branchList && branchList.ok && branchList.branches.find((x) => x.name === n);
    o.textContent = n + (b && b.commit ? `  (${b.commit})` : '') + (b && b.current ? '  •' : '');
    sel.appendChild(o);
  });
  sel.value = cfg.branch || names[0];

  const info = $('branchInfo');
  if (!branchList) {
    info.textContent = pinned
      ? 'Bấm nút làm mới để lấy danh sách branch thật.'
      : 'Branch lấy tự động từ repo trên máy — đổi branch là log đi theo.';
  } else if (!branchList.ok) {
    info.textContent = branchList.error || 'Không nạp được branch';
  } else {
    const b = branchList.branches.find((x) => x.name === sel.value);
    const bits = [`${branchList.branches.length} branch · từ ${branchList.source === 'native' ? 'máy' : 'GitHub'}`];
    if (b) {
      if (!b.upstream && branchList.source === 'native') bits.push('chưa có upstream');
      if (b.ahead && b.ahead !== '0') bits.push(`${b.ahead} commit chưa push`);
      if (b.behind && b.behind !== '0') bits.push(`sau remote ${b.behind}`);
    }
    info.textContent = bits.join(' · ');
  }

  const ci = state.commitInfo;
  if (!ci) {
    $('commitInfo').textContent = 'Dán link repo rồi bấm "Kết nối", hoặc "Lấy từ repo trên máy".';
  } else {
    const flags = [];
    if (ci.dirty) flags.push('có thay đổi chưa commit');
    if (ci.unpushed && ci.unpushed !== '0') flags.push(`${ci.unpushed} commit chưa push`);
    $('commitInfo').textContent =
      `${ci.sha} · ${ci.branch} · ${ci.source === 'native' ? 'từ máy' : 'từ GitHub'} ` +
      `lúc ${String(ci.at).slice(11, 16)}` + (ci.message ? ` · ${ci.message}` : '') +
      (flags.length ? ` — ${flags.join(', ')}` : '');
  }
}

/* ---------- render ---------- */

function render() {
  const cfg = state.config || {};
  $('cServer').value = cfg.serverUrl || '';
  $('cKey').value = cfg.apiKey || '';
  $('cRepo').value = cfg.repo || '';
  $('cStudent').value = cfg.student || '';
  $('cCommit').value = cfg.commit || '';
  $('cToken').value = cfg.githubToken || '';
  $('cRepoPath').value = cfg.repoPath || '';
  if (!$('cUrl').value) {
    $('cUrl').value = cfg.githubRepo ? 'https://github.com/' + cfg.githubRepo : '';
  }

  const on = cfg.enabled !== false;
  $('masterToggle').classList.toggle('on', on);
  $('masterToggle').setAttribute('aria-checked', String(on));
  $('masterLabel').textContent = on ? 'Đang ghi' : 'Đã tắt';
  document.body.classList.toggle('off', !on);

  // Một dòng tóm tắt ở header, thay cho dải thông báo cũ chiếm chỗ trên cùng.
  const pending = (state.pending || []).length;
  const queued = (state.queue || []).length;
  const rejected = (state.rejected || []).length;
  $('statusLine').textContent =
    !on ? 'đã tắt ghi log'
    : state.missing.length ? 'chưa cấu hình xong'
    : rejected ? `${rejected} entry bị từ chối`
    : pending ? `${pending} chờ duyệt`
    : queued ? `${queued} chờ gửi`
    : 'sẵn sàng';

  if (state.missing.length) {
    paint($('stateConfig'),
      'Chưa cấu hình: ' + state.missing.join(', ') + '. Điền vào các ô bên dưới rồi bấm "Lưu cấu hình".', 'err');
    $('secConfig').classList.add('open');
    $('secSetup').classList.add('open');
  } else {
    paint($('stateConfig'), '');
  }

  renderRepoBar();
  renderSiteCard();
  renderQueueCard();
  renderSetup();
  renderPending();
  renderHistory();
  renderSites();
  renderTools();
  renderBranches();
}

async function refresh() {
  state = await send({ type: 'getState' });
  if (!state || !state.ok) {
    $('statusLine').textContent = 'không kết nối được service worker';
    return;
  }
  render();
}

async function setEnabled(on) {
  await send({ type: 'saveConfig', config: { enabled: on } });
  await refresh();
}

function selectedIds() {
  return [...document.querySelectorAll('#pendingList input[type=checkbox]:checked')]
    .map((cb) => cb.dataset.id);
}

async function loadBranches() {
  branchList = await send({ type: 'listBranches' });
  return branchList;
}

/* ---------- header ---------- */

$('masterToggle').addEventListener('click', () => setEnabled(state.config.enabled === false));
$('repoBar').addEventListener('click', () => openSection('secConfig'));

/* ---------- trang hiện tại ---------- */

/* Một cú bấm để ngừng ghi trang đang mở, không đụng gì khác — trường hợp hay
   gặp là "riêng cuộc này là chuyện riêng". */
$('siteToggle').addEventListener('click', async () => {
  if (state.config.enabled === false) return;
  const entry = siteEntry();
  if (entry) await send({ type: 'disableSite', host: entry.host });
  else await send({ type: 'enableSite', host: currentHost, tool: currentHost.replace(/^www\./, '') });
  await refresh();
  say('msgSite', siteEntry()
    ? `Đang ghi log cho ${currentHost} — có hiệu lực ngay.`
    : `Đã tắt log cho ${currentHost} — có hiệu lực ngay.`, 'ok');
});

/* ---------- hàng đợi ---------- */

$('modeReview').addEventListener('click', async () => {
  await send({ type: 'saveConfig', config: { mode: 'review' } });
  await refresh();
});
$('modeAuto').addEventListener('click', async () => {
  await send({ type: 'saveConfig', config: { mode: 'auto' } });
  await refresh();
});

$('flushBtn').addEventListener('click', async () => {
  $('flushBtn').disabled = true;
  busy('msgQueue', 'Đang gửi…');
  const res = await send({ type: 'flush' });
  $('flushBtn').disabled = false;
  await refresh();
  say('msgQueue', res.ok
    ? `Gửi xong: ${res.accepted || 0} nhận, ${res.duplicates || 0} trùng.`
    : 'Chưa gửi được: ' + (res.error || 'unknown'), res.ok ? 'ok' : 'err');
});

$('testBtn').addEventListener('click', async () => {
  $('testBtn').disabled = true;
  busy('msgQueue', 'Đang test…');
  const res = await send({ type: 'testConnection' });
  $('testBtn').disabled = false;
  say('msgQueue', res.ok
    ? `Kết nối OK — server trả HTTP ${res.status}.`
    : 'Test thất bại: ' + (res.error || 'unknown'), res.ok ? 'ok' : 'err');
});

$('requeueBtn').addEventListener('click', async () => {
  const res = await send({ type: 'requeueRejected' });
  await refresh();
  say('msgQueue', res.ok ? `Đã gửi lại — server nhận ${res.accepted || 0}.` : 'Vẫn chưa gửi được.',
    res.ok ? 'ok' : 'err');
});

$('discardBtn').addEventListener('click', async () => {
  await send({ type: 'discardRejected' });
  await refresh();
  say('msgQueue', 'Đã xoá các entry bị từ chối.', 'ok');
});

/* ---------- chờ duyệt ---------- */

$('selAll').addEventListener('click', () => {
  document.querySelectorAll('#pendingList input[type=checkbox]').forEach((cb) => (cb.checked = true));
});
$('selNone').addEventListener('click', () => {
  document.querySelectorAll('#pendingList input[type=checkbox]').forEach((cb) => (cb.checked = false));
});

$('approveBtn').addEventListener('click', async () => {
  const ids = selectedIds();
  if (!ids.length) return say('msgPending', 'Chưa chọn mục nào.', 'warn');
  $('approveBtn').disabled = true;
  busy('msgPending', 'Đang gửi…');
  const res = await send({ type: 'approvePending', ids });
  $('approveBtn').disabled = false;
  await refresh();
  say('msgPending', res.ok
    ? `Đã gửi ${res.moved} mục — server nhận ${res.accepted || 0}.`
    : `Đã duyệt nhưng chưa gửi được (${res.error || '?'}) — vẫn nằm trong hàng đợi.`,
    res.ok ? 'ok' : 'warn');
});

$('dropBtn').addEventListener('click', async () => {
  const ids = selectedIds();
  if (!ids.length) return say('msgPending', 'Chưa chọn mục nào.', 'warn');
  const res = await send({ type: 'deletePending', ids });
  await refresh();
  say('msgPending', `Đã xoá ${res.removed} mục, không gửi lên server.`, 'ok');
});

/* ---------- bắt đầu ---------- */

$('diagBtn').addEventListener('click', async () => {
  $('diagBtn').disabled = true;
  busy('msgSetup', 'Đang kiểm tra…');
  diag = await send({ type: 'runDiagnostics', host: currentHost });
  $('diagBtn').disabled = false;
  await refresh();
  if (!diag || !diag.ok) return say('msgSetup', 'Không chạy được kiểm tra.', 'err');
  const opt = diag.steps.filter((s) => s.optional && !s.ok).length;
  say('msgSetup', diag.ready
    ? `Đủ điều kiện chạy (${diag.passed}/${diag.total})` + (opt ? ` — còn ${opt} mục tuỳ chọn.` : '. Xong.')
    : `Còn ${diag.total - diag.passed} mục bắt buộc chưa đạt.`,
    diag.ready ? 'ok' : 'err');
});

/* Lệnh dài, gõ lại là một nguồn sai khác. */
document.querySelectorAll('[data-copy]').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const src = $(btn.dataset.copy);
    if (!src) return;
    try {
      await navigator.clipboard.writeText(src.textContent.trim());
      say('msgSetup', 'Đã chép lệnh vào clipboard.', 'ok');
    } catch (err) {
      say('msgSetup', 'Không chép được — bôi đen dòng lệnh rồi Ctrl+C.', 'warn');
    }
  });
});

/* ---------- nhập tay ---------- */

$('sendBtn').addEventListener('click', async () => {
  const prompt = $('mPrompt').value.trim();
  if (!prompt) return say('msgManual', 'Nhập mô tả trước khi gửi.', 'warn');
  $('sendBtn').disabled = true;
  busy('msgManual', 'Đang gửi…');
  const res = await send({
    type: 'manual',
    entry: { tool: $('mTool').value, model: $('mModel').value.trim(), prompt },
  });
  $('sendBtn').disabled = false;
  if (res.status === 'sent') { $('mPrompt').value = ''; say('msgManual', 'Đã gửi lên server.', 'ok'); }
  else if (res.status === 'queued') { $('mPrompt').value = ''; say('msgManual', 'Đã xếp hàng — sẽ tự gửi lại.', 'warn'); }
  else if (res.status === 'rejected') say('msgManual', 'Server từ chối: tên repo không khớp.', 'err');
  else say('msgManual', 'Lỗi: ' + (res.error || 'unknown'), 'err');
  await refresh();
});

/* ---------- site ---------- */

$('addSiteBtn').addEventListener('click', async () => {
  const host = $('sHost').value.trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '').replace(/^www\./, '');
  if (!host) return say('msgSites', 'Nhập domain, vd: chat.mistral.ai', 'warn');
  await send({ type: 'enableSite', host, tool: $('sTool').value.trim() || host });
  $('sHost').value = '';
  $('sTool').value = '';
  await refresh();
  say('msgSites', `Đã bật ${host} — tab đang mở của site đó cũng nhận ngay.`, 'ok');
});

/* ---------- cấu hình: server ---------- */

$('saveBtn').addEventListener('click', async () => {
  $('saveBtn').disabled = true;
  const res = await send({
    type: 'saveConfig',
    config: {
      serverUrl: $('cServer').value.trim(),
      apiKey: $('cKey').value.trim(),
      student: $('cStudent').value.trim(),
      repo: $('cRepo').value.trim(),
      commit: $('cCommit').value.trim(),
      githubToken: $('cToken').value.trim(),
      repoPath: $('cRepoPath').value.trim(),
    },
  });
  $('saveBtn').disabled = false;
  await refresh();
  say('msgServer', res.ok ? 'Đã lưu cấu hình.' : (res.error || 'Lưu thất bại'), res.ok ? 'ok' : 'err');
});

/* ---------- cấu hình: repo ---------- */

$('testLinkBtn').addEventListener('click', async () => {
  $('testLinkBtn').disabled = true;
  busy('msgRepo', 'Đang kiểm tra link…');
  const res = await send({ type: 'testRepoLink', url: $('cUrl').value, token: $('cToken').value.trim() });
  $('testLinkBtn').disabled = false;
  if (!res.ok) return say('msgRepo', res.error || 'Link không dùng được', 'err');

  const bits = [`${res.slug}${res.private ? ' (private)' : ''}`,
    `${res.branches.length} branch`, `mặc định ${res.defaultBranch}`];
  if (res.branchFromLink) bits.push(`link trỏ branch ${res.branchFromLink}`);
  if (res.danglingHint) bits.push('link trỏ branch không còn tồn tại');
  if (!res.matchesConfig) bits.push(`repo hiện lưu là "${state.config.repo || '(trống)'}"`);
  say('msgRepo', 'Link dùng được — ' + bits.join(' · ') + '. Bấm "Kết nối" để áp dụng.',
    res.danglingHint ? 'warn' : 'ok');
});

$('connectBtn').addEventListener('click', async () => {
  $('connectBtn').disabled = true;
  busy('msgRepo', 'Đang kết nối GitHub…');
  const res = await send({ type: 'connectRepo', url: $('cUrl').value, token: $('cToken').value.trim() });
  $('connectBtn').disabled = false;

  if (!res.ok) {
    await refresh();
    return say('msgRepo', res.error || 'Không kết nối được', 'err');
  }
  // Dùng lại danh sách branch vừa lấy, khỏi bắt bấm nút làm mới thêm lần nữa.
  branchList = {
    ok: true, source: 'github', current: '',
    branches: res.branches.map((n) => ({
      name: n, commit: '', upstream: '', ahead: '', behind: '', current: false,
    })),
  };
  await refresh();

  const bits = [`repo ${res.repo}`, `branch ${res.branch}`];
  if (res.branchFromLink) bits.push('(ghim theo link)');
  if (res.commit) bits.push(`commit ${res.commit}`);
  say('msgRepo', `Đã kết nối ${res.slug} — ${bits.join(' · ')}.` +
    (res.commitError ? ` Chưa lấy được commit: ${res.commitError}` : ''),
    res.commitError ? 'warn' : 'ok');
});

$('cUrl').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('connectBtn').click(); });

$('adoptBtn').addEventListener('click', async () => {
  $('adoptBtn').disabled = true;
  busy('msgRepo', 'Đang hỏi native host…');
  const res = await send({ type: 'adoptLocalRepo', repoPath: $('cRepoPath').value.trim() });
  $('adoptBtn').disabled = false;
  branchList = null; // repo trên máy có danh sách branch riêng
  await refresh();
  if (!res.ok) return say('msgRepo', res.error || 'Không lấy được', 'err');
  const i = res.info;
  say('msgRepo', `Đã lấy từ ${i.root}: repo ${i.repo || '(không có origin)'}, branch ${i.branch}, commit ${i.commit}.` +
    (i.dirty ? ' Repo đang có thay đổi chưa commit.' : ''), 'ok');
});

/* ---------- cấu hình: branch và commit ---------- */

$('branchAuto').addEventListener('click', async () => {
  await send({ type: 'saveConfig', config: { branchMode: 'auto' } });
  const res = await send({ type: 'refreshCommit' });
  await refresh();
  say('msgBranch', res.ok ? `Theo branch đang dùng: ${res.branch} · ${res.sha}.`
    : (res.error || 'Chưa lấy được commit'), res.ok ? 'ok' : 'err');
});

$('branchFixed').addEventListener('click', async () => {
  await send({ type: 'saveConfig', config: { branchMode: 'fixed' } });
  if (!branchList) await loadBranches();
  await refresh();
  say('msgBranch', `Đã ghim branch ${state.config.branch}.`, 'ok');
});

$('branchesBtn').addEventListener('click', async () => {
  $('branchesBtn').disabled = true;
  busy('msgBranch', 'Đang nạp danh sách branch…');
  await loadBranches();
  $('branchesBtn').disabled = false;
  await refresh();
  say('msgBranch', branchList.ok
    ? `Nạp ${branchList.branches.length} branch từ ${branchList.source === 'native' ? 'repo trên máy' : 'GitHub'}.`
    : (branchList.error || 'Không nạp được branch'), branchList.ok ? 'ok' : 'err');
});

$('cBranch').addEventListener('change', async () => {
  await send({ type: 'saveConfig', config: { branch: $('cBranch').value } });
  const res = await send({ type: 'refreshCommit' });
  await refresh();
  say('msgBranch', res.ok ? `Branch ${res.branch} → commit ${res.sha}.`
    : (res.error || 'Không lấy được commit cho branch này'), res.ok ? 'ok' : 'err');
});

$('commitBtn').addEventListener('click', async () => {
  $('commitBtn').disabled = true;
  busy('msgBranch', 'Đang lấy commit…');
  await send({
    type: 'saveConfig',
    config: { githubToken: $('cToken').value.trim(), branch: $('cBranch').value || 'main' },
  });
  const res = await send({ type: 'refreshCommit' });
  $('commitBtn').disabled = false;
  await refresh();
  say('msgBranch', res.ok
    ? `Commit ${res.sha} (${res.branch}) — ${res.source === 'native' ? 'từ máy' : 'từ GitHub'}.`
    : (res.error || 'Không lấy được commit'), res.ok ? 'ok' : 'err');
});

/* ---------- lịch sử ---------- */

$('clearHistBtn').addEventListener('click', async () => {
  await send({ type: 'clearHistory' });
  await refresh();
  say('msgHistory', 'Đã xoá danh sách hiển thị. Log đã gửi vẫn nằm trên server.', 'ok');
});

/* ---------- khởi động ---------- */

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  try {
    if (tabs && tabs[0] && tabs[0].url) currentHost = new URL(tabs[0].url).hostname;
  } catch (err) { /* trang chrome:// không có host dùng được */ }
  refresh();
});
