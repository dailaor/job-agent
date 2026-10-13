const {spawn} = require('node:child_process');
const {copyFileSync, mkdirSync, existsSync} = require('node:fs');
const {resolve, dirname, join} = require('node:path');
const assert = require('node:assert/strict');
const net = require('node:net');
const {chromium} = require('playwright');
const sleep = ms => new Promise(done => setTimeout(done, ms));
const exe = resolve(process.argv[2]);
const root = resolve(__dirname, '..');
const dataDir = join(dirname(exe), 'data');

async function unusedPort() {
  for (let port = 8765; port < 8775; port++) {
    const free = await new Promise(done => {
      const probe = net.createServer();
      probe.once('error', () => done(false));
      probe.listen(port, '127.0.0.1', () => probe.close(() => done(true)));
    });
    if (free) return port;
  }
  throw new Error('No free launcher port for isolated package test');
}

async function launchAndCheck(withFixtures) {
  const port = await unusedPort();
  const child = spawn(exe, [], {windowsHide: true, env: {...process.env, JOB_AGENT_NO_BROWSER: '1', PATH: 'C:\\Windows\\System32'}});
  let logs = '';
  child.stdout.on('data', data => { logs += data; });
  child.stderr.on('data', data => { logs += data; });
  const address = `http://127.0.0.1:${port}`;
  let browser;
  try {
    let response;
    for (let index = 0; index < 100; index++) {
      try {response = await fetch(`${address}/api/recommendations`); if (response.ok) break;} catch (_) { /* boot */ }
      if (child.exitCode !== null) throw new Error(`Packaged launcher exited: ${logs}`);
      await sleep(100);
    }
    assert(response?.ok, `Packaged server unavailable: ${logs}`);
    const payload = await response.json();
    assert.equal(payload.items.length, withFixtures ? 4 : 0);
    if (withFixtures) assert.equal(payload.items.filter(item => item.decision.status === 'recommend').length, 2);
    const markup = await (await fetch(address)).text();
    assert(markup.includes('view-recommendations'));
    assert(markup.includes('recommendation-carousel'));
    assert(markup.includes('progress-dialog'));
    const script = await (await fetch(`${address}/recommendations.js`)).text();
    assert(script.includes('window.Recommendations'));
    const theme = await (await fetch(`${address}/commercial.css`)).text();
    assert(theme.includes('--primary: #233b62'));
    assert(theme.includes('--paper: #f5f7fa'));
    const icons = await (await fetch(`${address}/ui-icons.js`)).text();
    assert(icons.includes('window.JobIcons'));
    assert(existsSync(join(dataDir, 'config.json')), 'Fresh package must create its config');
    browser = await chromium.launch({channel: 'msedge', headless: true});
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(address, {waitUntil: 'networkidle'});
    assert.equal(await page.locator('#page-title').textContent(), '智能推荐');
    assert.equal(await page.locator('.sidebar').evaluate(element => getComputedStyle(element).backgroundColor), 'rgb(240, 243, 248)');
    if (withFixtures) {
      assert.equal(await page.locator('.job-decision-card').count(), 1);
      assert.equal(await page.locator('#recommendation-order').textContent(), '1 / 2');
      await page.locator('#recommendation-next').click();
      assert.equal(await page.locator('#recommendation-order').textContent(), '2 / 2');
      assert(await page.locator('#recommendation-next').isDisabled());
      await page.locator('#recommendation-prev').click();
      await page.locator('.proof-link').first().click();
      assert((await page.evaluate(() => document.activeElement.id)).startsWith('proof-'));
    } else {
      assert((await page.locator('#recommendation-results').textContent()).includes('暂无高推荐岗位'));
      assert(await page.locator('#recommendation-prev').isDisabled());
      assert(await page.locator('#recommendation-next').isDisabled());
    }
    await page.locator('#nav').getByRole('button', {name: '全部岗位', exact: true}).click();
    assert(await page.locator('#jobs-one-click-apply').isDisabled());
    assert.deepEqual(errors, []);
    return {phase: withFixtures ? 'synthetic cards and evidence' : 'fresh launch and empty state', passed: true, port};
  } finally {
    if (browser) await browser.close();
    child.kill();
    await sleep(300);
  }
}

(async () => {
  assert(!existsSync(dataDir), 'Use a newly built package without user data');
  const results = [await launchAndCheck(false)];
  mkdirSync(dataDir, {recursive: true});
  const fixtureRoot = join(root, 'work', 'recommendation-preview');
  copyFileSync(join(fixtureRoot, 'config.json'), join(dataDir, 'config.json'));
  copyFileSync(join(fixtureRoot, 'preview.sqlite3'), join(dataDir, 'job-agent.sqlite3'));
  results.push(await launchAndCheck(true));
  console.log(JSON.stringify({passed: true, globalPythonNotOnPath: true, results}, null, 2));
})().catch(error => {console.error(error); process.exitCode = 1;});
