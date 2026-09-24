const assert = require('node:assert/strict');
const helpers = require('./test-helper.js');

(async () => {
  let attempts = 0;
  assert.equal(await helpers.waitForCondition(() => ++attempts === 2, 100, 1), true);
  await assert.rejects(helpers.waitForCondition(() => false, 5, 1), /Condition not met/);

  let listener;
  const logs = helpers.captureConsoleLogs({ on: (event, callback) => {
    assert.equal(event, 'console');
    listener = callback;
  } });
  listener({ type: () => 'info', text: () => 'synthetic message' });
  assert.equal(logs[0].text, 'synthetic message');

  let options;
  const filename = await helpers.captureScreenshot({ screenshot: async value => {
    options = value;
  } }, 'synthetic');
  assert.equal(options.path, filename);
  assert.equal(options.fullPage, true);
  console.log('Web helper checks passed.');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
