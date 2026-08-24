/* The "was that a send?" state machine.
   Run: node tools/ai-log-extension/test/composer.test.js */
const path = require('path');
const C = require(path.join(__dirname, '..', 'composer.js'));

let fail = 0;
function eq(name, got, want) {
  if (got === want) return console.log('  PASS  ' + name);
  fail++;
  console.log('  FAIL  ' + name + '\n        got : ' + JSON.stringify(got) + '\n        want: ' + JSON.stringify(want));
}

const T = (o) => C.createTracker(o);

console.log('\n--- the normal send ---');
{
  const t = T();
  t.onInput('Giải thích OAuth2 PKCE');
  t.onIntent(1000);                       // click the send button
  eq('fires when the box empties', t.onTick('', 1050, true), 'Giải thích OAuth2 PKCE');
  eq('does not fire twice', t.onTick('', 1100, true), '');
}

console.log('\n--- typing is not a send ---');
{
  const t = T();
  t.onInput('đang gõ');
  eq('still typing', t.onTick('đang gõ', 1000, true), '');
  t.onInput('đang gõ tiếp');
  eq('still typing, longer', t.onTick('đang gõ tiếp', 1100, true), '');
}

console.log('\n--- clearing by hand is not a send ---');
{
  const t = T();
  t.onInput('tôi đổi ý, xoá đi');
  eq('no intent -> nothing logged', t.onTick('', 5000, true), '');
}
{
  const t = T();
  t.onInput('gõ rồi bỏ đó rất lâu');
  t.onIntent(1000);                       // clicked something unrelated
  eq('intent too old -> nothing logged', t.onTick('', 1000 + 5000, true), '');
}

console.log('\n--- the intent window ---');
{
  const t = T();
  t.onInput('trong hạn');
  t.onIntent(1000);
  eq('inside 2s', t.onTick('', 2999, true), 'trong hạn');
}
{
  const t = T();
  t.onInput('ngoài hạn');
  t.onIntent(1000);
  eq('outside 2s', t.onTick('', 3001, true), '');
}
{
  const t = T({ intentMs: 500 });
  t.onInput('cửa sổ hẹp');
  t.onIntent(1000);
  eq('custom window respected', t.onTick('', 1400, true), 'cửa sổ hẹp');
}

console.log('\n--- editors that swap the node instead of clearing it ---');
{
  const t = T();
  t.onInput('ProseMirror thay node');
  t.onIntent(1000);
  eq('detached counts as cleared', t.onTick('bất kỳ', 1050, false), 'ProseMirror thay node');
}

console.log('\n--- interaction with the direct Enter path ---');
{
  const t = T();
  t.onInput('bắt bằng Enter');
  t.onIntent(1000);
  t.forget();                             // content.js captured it inline
  eq('no duplicate from the clear', t.onTick('', 1050, true), '');
}

console.log('\n--- guards ---');
{
  const t = T();
  eq('empty tracker', t.onTick('', 1000, true), '');
}
{
  const t = T();
  t.onInput('   ');
  t.onIntent(1000);
  eq('whitespace never tracked', t.onTick('', 1050, true), '');
}
{
  const t = T();
  t.onInput('a');
  t.onIntent(1000);
  eq('single char rejected', t.onTick('', 1050, true), '');
}
{
  const t = T();
  t.onInput('lần một');
  t.onIntent(1000);
  eq('first send', t.onTick('', 1050, true), 'lần một');
  t.onInput('lần hai');
  t.onIntent(2000);
  eq('tracker reusable', t.onTick('', 2050, true), 'lần hai');
}
{
  const t = T();
  t.onInput('giữ nguyên');
  eq('pending() exposes the draft', t.pending(), 'giữ nguyên');
}

console.log(fail === 0 ? '\nALL PASS\n' : `\n${fail} FAILURE(S)\n`);
process.exit(fail ? 1 : 0);
