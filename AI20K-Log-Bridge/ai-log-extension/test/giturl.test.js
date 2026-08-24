/* Parsing whatever the user pastes.
   Run: node tools/ai-log-extension/test/giturl.test.js */
const path = require('path');
const G = require(path.join(__dirname, '..', 'giturl.js'));

let fail = 0;
function eq(name, got, want) {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g === w) return console.log('  PASS  ' + name);
  fail++;
  console.log('  FAIL  ' + name + '\n        got : ' + g + '\n        want: ' + w);
}

const slug = (s) => { const r = G.parseRepoUrl(s); return r.ok ? r.slug : 'ERR:' + r.error; };
const hint = (s) => { const r = G.parseRepoUrl(s); return r.ok ? r.branchHint : 'ERR'; };

const REPO = 'AI20K-Build-Cohort-2/P-093';

console.log('\n--- the forms people actually paste ---');
eq('https url', slug('https://github.com/AI20K-Build-Cohort-2/P-093'), REPO);
eq('with .git', slug('https://github.com/AI20K-Build-Cohort-2/P-093.git'), REPO);
eq('trailing slash', slug('https://github.com/AI20K-Build-Cohort-2/P-093/'), REPO);
eq('no scheme', slug('github.com/AI20K-Build-Cohort-2/P-093'), REPO);
eq('www', slug('https://www.github.com/AI20K-Build-Cohort-2/P-093'), REPO);
eq('bare slug', slug('AI20K-Build-Cohort-2/P-093'), REPO);
eq('ssh scp form', slug('git@github.com:AI20K-Build-Cohort-2/P-093.git'), REPO);
eq('ssh url form', slug('ssh://git@github.com/AI20K-Build-Cohort-2/P-093.git'), REPO);
eq('surrounding spaces', slug('  https://github.com/AI20K-Build-Cohort-2/P-093  '), REPO);
eq('query string dropped', slug('https://github.com/AI20K-Build-Cohort-2/P-093?tab=readme'), REPO);
eq('fragment dropped', slug('https://github.com/AI20K-Build-Cohort-2/P-093#readme'), REPO);

console.log('\n--- links that carry a branch ---');
eq('tree/main', hint('https://github.com/o/r/tree/main'), 'main');
eq('blob path', hint('https://github.com/o/r/blob/develop/README.md'), 'develop/README.md');
eq('slashed branch + path', hint('https://github.com/o/r/tree/feature/x/src/app.js'), 'feature/x/src/app.js');
eq('commits view', hint('https://github.com/o/r/commits/release-1.2'), 'release-1.2');
eq('no branch in url', hint('https://github.com/o/r'), '');
eq('slug survives a tree url', slug('https://github.com/o/r/tree/main'), 'o/r');

console.log('\n--- the hint is settled against real branches ---');
const NAMES = ['main', 'develop', 'feature', 'feature/x', 'release-1.2'];
eq('exact', G.resolveBranchHint('main', NAMES), 'main');
eq('strips the file path', G.resolveBranchHint('develop/README.md', NAMES), 'develop');
// "feature" and "feature/x" both prefix the hint; the longer one is the branch.
eq('longest match wins', G.resolveBranchHint('feature/x/src/app.js', NAMES), 'feature/x');
eq('plain feature', G.resolveBranchHint('feature/README.md', NAMES), 'feature');
eq('unknown branch', G.resolveBranchHint('khong-co', NAMES), '');
eq('empty hint', G.resolveBranchHint('', NAMES), '');
eq('no branch list yet', G.resolveBranchHint('main', []), '');
// A branch whose name merely starts the same must not match.
eq('not a prefix match on partial segment', G.resolveBranchHint('mainline/x', NAMES), '');

console.log('\n--- refuses rather than guesses ---');
eq('empty', slug(''), 'ERR:Chưa nhập link repo.');
eq('owner only', slug('https://github.com/AI20K-Build-Cohort-2'), 'ERR:Thiếu tên repo. Dạng đúng: owner/repo.');
eq('gitlab', slug('https://gitlab.com/owner/repo'), 'ERR:Chỉ hỗ trợ github.com (link này thuộc host khác).');
eq('bitbucket', slug('https://bitbucket.org/owner/repo'), 'ERR:Chỉ hỗ trợ github.com (link này thuộc host khác).');
eq('bad characters', slug('https://github.com/own er/re po'), 'ERR:Owner hoặc tên repo không hợp lệ.');

console.log(fail === 0 ? '\nALL PASS\n' : `\n${fail} FAILURE(S)\n`);
process.exit(fail ? 1 : 0);
