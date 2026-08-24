/* Every element popup.js reaches for must exist in popup.html.
 *
 * Rewriting the config section left two `$('cGithub')` calls behind after the
 * field was removed. `node --check` passes that happily — the popup only dies
 * at runtime, on a line most people never look at. This catches it statically.
 *
 * Run: node tools/ai-log-extension/test/popup-dom.test.js
 */
const fs = require('fs');
const path = require('path');

const EXT = process.argv[2] || path.join(__dirname, '..');
const js = fs.readFileSync(path.join(EXT, 'popup.js'), 'utf8');
const html = fs.readFileSync(path.join(EXT, 'popup.html'), 'utf8');

let fail = 0;
function check(name, cond, extra) {
  if (cond) return console.log('  PASS  ' + name);
  fail++;
  console.log('  FAIL  ' + name + (extra !== undefined ? '  -> ' + JSON.stringify(extra) : ''));
}

const htmlIds = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]));
/* Not just $('x'): ids also travel as arguments — say('msgConfig', …) and the
   set('barBranch', …) helper — and those were invisible to the first version
   of this check, which is exactly the blind spot it exists to close. */
const usedIds = [
  ...[...js.matchAll(/\$\(\s*'([^']+)'\s*\)/g)].map((m) => m[1]),
  ...[...js.matchAll(/\bsay\(\s*'([^']+)'/g)].map((m) => m[1]),
  ...[...js.matchAll(/\bbusy\(\s*'([^']+)'/g)].map((m) => m[1]),
  ...[...js.matchAll(/\bset\(\s*'(bar[^']+)'/g)].map((m) => m[1]),
];
// Placeholders like msg<X> come from the doc comment, not from real calls.
const unique = [...new Set(usedIds)].filter((id) => !/[<>]/.test(id));

console.log('\n--- ids referenced by popup.js ---');
const missing = unique.filter((id) => !htmlIds.has(id));
check(`${unique.length} ids, tất cả tồn tại trong popup.html`, missing.length === 0, missing);

console.log('\n--- data-target của các mục gập ---');
const targets = [...html.matchAll(/data-target="([^"]+)"/g)].map((m) => m[1]);
const badTargets = targets.filter((t) => !htmlIds.has(t));
check(`${targets.length} mục, tất cả trỏ vào id có thật`, badTargets.length === 0, badTargets);

/* <use href="#i-x"> với tên sai không báo lỗi — nó chỉ đơn giản không vẽ gì.
   Đối chiếu mọi tên icon được dùng với các <symbol> có thật trong sprite. */
console.log('\n--- icon trong sprite ---');
const symbols = new Set([...html.matchAll(/<symbol id="([^"]+)"/g)].map((m) => m[1]));
const usedIcons = [
  ...[...html.matchAll(/<use href="#([^"]+)"/g)].map((m) => m[1]),
  ...[...js.matchAll(/svgIcon\(\s*'([^']+)'/g)].map((m) => m[1]),
  ...[...js.matchAll(/'(i-[a-z]+)'/g)].map((m) => m[1]),
];
const missingIcons = [...new Set(usedIcons)].filter((i) => !symbols.has(i));
check(`${symbols.size} symbol, ${new Set(usedIcons).size} tên được dùng đều có thật`,
  missingIcons.length === 0, missingIcons);

console.log('\n--- script popup.html nạp ---');
const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
const missingScripts = scripts.filter((s) => !fs.existsSync(path.join(EXT, s)));
check(`${scripts.length} script, tất cả có file`, missingScripts.length === 0, missingScripts);

console.log('\n--- file trong manifest ---');
const manifest = JSON.parse(fs.readFileSync(path.join(EXT, 'manifest.json'), 'utf8'));
const declared = [
  manifest.background.service_worker,
  manifest.action.default_popup,
  ...(manifest.content_scripts || []).flatMap((cs) => cs.js || []),
  ...Object.values(manifest.icons || {}),
];
const missingFiles = declared.filter((f) => !fs.existsSync(path.join(EXT, f)));
check(`${declared.length} file khai báo, tất cả tồn tại`, missingFiles.length === 0, missingFiles);

/* Files registered at runtime rather than in the manifest — a typo here is
   invisible until a site is enabled and nothing gets captured. */
console.log('\n--- file đăng ký lúc chạy trong background.js ---');
const bg = fs.readFileSync(path.join(EXT, 'background.js'), 'utf8');
const runtimeFiles = new Set([...bg.matchAll(/files:\s*\[([^\]]+)\]/g)]
  .flatMap((m) => [...m[1].matchAll(/'([^']+)'/g)].map((f) => f[1])));
const missingRuntime = [...runtimeFiles].filter((f) => !fs.existsSync(path.join(EXT, f)));
check(`${runtimeFiles.size} file, tất cả tồn tại`, missingRuntime.length === 0, missingRuntime);

/* Chrome logs "Unrecognized manifest key" for anything it does not know —
   including a comment field someone adds to explain a setting. There is no
   comment syntax in a manifest; notes belong in the README. */
console.log('\n--- key la trong manifest ---');
const KNOWN_KEYS = new Set([
  'manifest_version', 'name', 'version', 'description', 'minimum_chrome_version',
  'key', 'permissions', 'optional_permissions', 'host_permissions',
  'optional_host_permissions', 'background', 'action', 'icons', 'content_scripts',
  'web_accessible_resources', 'content_security_policy', 'options_page',
  'options_ui', 'commands', 'default_locale', 'devtools_page', 'homepage_url',
  'incognito', 'externally_connectable', 'declarative_net_request', 'omnibox',
  'side_panel', 'storage', 'update_url', 'author', 'short_name',
]);
const unknownKeys = Object.keys(manifest).filter((k) => !KNOWN_KEYS.has(k));
check('không có key lạ (Chrome sẽ cảnh báo)', unknownKeys.length === 0, unknownKeys);

/* A Windows path inside a JS string needs doubled backslashes. `tools\a...`
   silently becomes `toolsa...` because \a is not an escape — so the user is
   handed a command that cannot possibly work. */
console.log('\n--- duong dan Windows trong chuoi JS ---');
const jsSources = ['background.js', 'popup.js', 'content.js', 'adapters.js']
  .map((f) => [f, fs.readFileSync(path.join(EXT, f), 'utf8')]);
const badEscapes = [];
jsSources.forEach(([file, src]) => {
  src.split('\n').forEach((line, i) => {
    if (line.trim().startsWith('//') || line.trim().startsWith('*')) return;
    // Drop correctly-escaped pairs first, so only a lone backslash survives:
    //   "tools\\ai"  -> "toolsai"  (fine)
    //   "tools\ai"   -> "tools\ai" (bug)
    const stripped = line.replace(/\\\\/g, '');
    const m = stripped.match(/'[^']*\\[^nrt'][^']*'/);
    if (m && /tools|\.cmd|\.ps1/.test(m[0])) badEscapes.push(`${file}:${i + 1} ${m[0].trim()}`);
  });
});
check('không có backslash đơn trong đường dẫn', badEscapes.length === 0, badEscapes);

console.log('\n--- importScripts trong service worker ---');
const imported = [...bg.matchAll(/importScripts\(\s*'([^']+)'\s*\)/g)].map((m) => m[1]);
const missingImports = imported.filter((f) => !fs.existsSync(path.join(EXT, f)));
check(`${imported.length} import, tất cả tồn tại`, missingImports.length === 0, missingImports);

console.log(fail === 0 ? '\nALL PASS\n' : `\n${fail} FAILURE(S)\n`);
process.exit(fail ? 1 : 0);
