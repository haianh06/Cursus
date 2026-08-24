/* Runs every extension test. Usage: node tools/ai-log-extension/test/run.js */
const { execFileSync } = require('child_process');
const path = require('path');

const EXT = path.join(__dirname, '..');
const suites = [
  'giturl.test.js',
  'composer.test.js',
  'popup-dom.test.js',
  'background.test.js',
];

let failed = 0;
for (const suite of suites) {
  console.log('\n════ ' + suite + ' ════');
  try {
    execFileSync(process.execPath, [path.join(__dirname, suite), EXT], { stdio: 'inherit' });
  } catch (err) {
    failed++;
  }
}

console.log(failed ? `\n${failed} suite(s) failed\n` : '\nAll suites passed\n');
process.exit(failed ? 1 : 0);
