/* Run with the available Playwright package on NODE_PATH; no user data or external actions. */
const {spawn} = require('node:child_process');
const {mkdirSync, writeFileSync} = require('node:fs');
const {join, resolve} = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

const root = resolve(__dirname, '..');
const evidenceDir = join(root, 'work', 'recommendation-review');
mkdirSync(evidenceDir, {recursive: true});
const server = spawn(process.env.TEST_PYTHON || join(root, '.venv', 'Scripts', 'python.exe'),
  ['scripts/preview_recommendations.py', '--port', '9876'],
  {cwd: root, env: {...process.env, PYTHONPATH: join(root, 'src')}, windowsHide: true});
let serverLog = '';
server.stdout.on('data', data => { serverLog += data; });
server.stderr.on('data', data => { serverLog += data; });
const sleep = ms => new Promise(resolveDelay => setTimeout(resolveDelay, ms));
async function capture(page, name, fullPage = true) {
  await page.evaluate(() => window.scrollTo({top: 0, left: 0, behavior: 'instant'}));
  await page.waitForTimeout(80);
  await page.screenshot({path: join(evidenceDir, name), fullPage});
}

(async () => {
  let browser;
  const checks = [];
  try {
    let response;
    for (let index = 0; index < 60; index++) {
      try { response = await fetch('http://127.0.0.1:9876/api/recommendations'); if (response.ok) break; } catch (_) { /* server boot */ }
      await sleep(250);
    }
    assert(response?.ok, 'preview server did not start');
    const payload = await response.json();
    assert.equal(payload.items.length, 3);
    assert(payload.items.some(item => item.default_visible === false));
    browser = await chromium.launch({channel: 'msedge', headless: true});
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const mutations = [];
    page.on('request', request => { if (request.method() !== 'GET') mutations.push(request.url()); });
    await page.goto('http://127.0.0.1:9876', {waitUntil: 'networkidle'});
    await page.locator('.job-decision-card').first().waitFor();
    assert.equal(await page.locator('.job-decision-card').count(), 2, 'blocked jobs stay in pool');
    assert.equal(await page.locator('#page-title').textContent(), '智能推荐');
    assert.equal(await page.locator('#recommendation-order').getAttribute('role'), 'status');
    assert.equal(await page.locator('#recommendation-order').getAttribute('aria-live'), 'polite');
    assert.equal(await page.locator('.experience-preview').first().locator('dl > div').count(), 6);
    assert((await page.locator('.job-decision-card').first().textContent()).includes('演示'));
    checks.push('Default recommendations show reasons, risks, six experience dimensions and explicit demo labels; blocked jobs excluded.');
    await capture(page, 'desktop.png');
    await page.setViewportSize({width: 1448, height: 1086});
    await capture(page, 'hero-repro.png', false);
    await page.setViewportSize({width: 1440, height: 1000});
    await page.locator('#recommendation-search').focus();
    const focusStyle = await page.locator('#recommendation-search').evaluate(element => ({color: getComputedStyle(element).outlineColor, style: getComputedStyle(element).outlineStyle}));
    assert.deepEqual(focusStyle, {color: 'rgb(38, 118, 90)', style: 'solid'});
    await capture(page, 'keyboard-focus.png');
    await page.locator('.proof-link').first().click();
    assert(await page.locator('.decision-details').first().getAttribute('open') !== null);
    assert((await page.evaluate(() => document.activeElement.id)).startsWith('proof-'));
    assert((await page.locator('.evidence-entry').first().textContent()).includes('原始来源'));
    await capture(page, 'evidence.png');
    checks.push('Inline evidence opens the containing disclosure, focuses the correct source and keeps origin/scope/date readable.');
    const multiProof = page.locator('.proof-link[data-proof-ids*=","]').first();
    if (await multiProof.count()) {
      const sourceCount = (await multiProof.getAttribute('data-proof-ids')).split(',').length;
      await multiProof.click();
      assert.equal(await multiProof.evaluate(button => button.closest('.job-decision-card').querySelectorAll('.evidence-entry.is-linked').length), sourceCount);
      checks.push('Grouped evidence preserves all linked sources and highlights every source rather than duplicating buttons.');
    }
    await page.locator('#recommendation-search').fill('示例云');
    assert.equal(await page.locator('.job-decision-card').count(), 1);
    assert((await page.locator('#recommendation-order').textContent()).includes('显示 1 个候选'));
    await page.locator('#recommendation-evidence-only').check();
    assert.equal(await page.locator('.job-decision-card').count(), 0);
    assert((await page.locator('#recommendation-order').textContent()).includes('显示 0 个候选'));
    await page.locator('[data-recommendation-clear]').click();
    assert.equal(await page.locator('.job-decision-card').count(), 2);
    await page.locator('#recommendation-status').selectOption('verify');
    assert(await page.locator('.job-decision-card').count() >= 1);
    await page.locator('#recommendation-reset').click();
    checks.push('Search, decision status, direct-experience filter and reset work; no-match state offers recovery.');
    checks.push('Keyboard focus uses solid incumbent green and polite result status reports actual 2 → 1 → 0 candidate counts.');
    await page.locator('#recommendation-overview [data-recommendation-pool]').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'page-title');
    assert(await page.locator('#jobs-one-click-apply').isDisabled());
    assert.equal(await page.locator('#jobs-body tr').count(), 3);
    assert((await page.locator('#jobs-one-click-note').textContent()).includes('确认'));
    await capture(page, 'job-pool.png');
    checks.push('Job pool remains available with all jobs and an explicitly disabled one-click-apply entry.');
    await page.getByRole('button', {name: '智能推荐', exact: true}).click();
    await page.getByRole('button', {name: '总览', exact: true}).click();
    assert(await page.locator('#view-overview').isVisible());
    await capture(page, 'overview.png');
    await page.getByRole('button', {name: '配置', exact: true}).click();
    assert(await page.locator('#save-basic-config').isVisible());
    await capture(page, 'settings.png');
    await page.getByRole('button', {name: '智能推荐', exact: true}).click();
    await page.setViewportSize({width: 390, height: 844});
    await capture(page, 'mobile.png');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile horizontal overflow');
    await page.setViewportSize({width: 1280, height: 900});
    await capture(page, 'desktop-1280.png');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'desktop horizontal overflow');
    checks.push('390px and 1280px layouts have no page overflow.');
    await page.route('**/api/recommendations', route => route.fulfill({status: 500, contentType: 'application/json', body: JSON.stringify({message: '受控测试：本地推荐暂不可用'})}));
    await page.locator('#refresh').click();
    await page.locator('[data-recommendation-retry]').waitFor();
    assert((await page.locator('#recommendation-results').textContent()).includes('本地推荐暂不可用'));
    await page.unroute('**/api/recommendations');
    await page.locator('[data-recommendation-retry]').click();
    await page.locator('.job-decision-card').first().waitFor();
    checks.push('Recommendation API error is visible and retry restores cards without blocking other views.');
    const malicious = structuredClone(payload);
    malicious.items[0].title = '<img src=x onerror="window.__unsafe=true">';
    malicious.items[0].apply_url = 'javascript:window.__unsafe=true';
    malicious.items[0].experience[0].facts = [{text: '<p>岗位职责</p><p>负责真实产品需求与数据分析</p><img src=x onerror="window.__unsafe=true"><script>window.__unsafe=true</script>', evidence_ids: [malicious.items[0].evidence[0].id]}];
    await page.route('**/api/recommendations', route => route.fulfill({contentType: 'application/json', body: JSON.stringify(malicious)}));
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('.job-decision-card h3')?.textContent.includes('<img'));
    assert.equal(await page.locator('.job-decision-card img').count(), 0);
    assert.equal(await page.locator('a[href^="javascript:"]').count(), 0);
    assert.equal(await page.evaluate(() => !!window.__unsafe), false);
    const experienceCopy = await page.locator('.experience-preview').first().textContent();
    assert(experienceCopy.includes('岗位职责 负责真实产品需求与数据分析'));
    assert(!experienceCopy.includes('<p>') && !experienceCopy.includes('__unsafe'));
    checks.push('HTML-formatted source excerpts become readable text; scripts/resources stay inert and do not run.');
    await page.unroute('**/api/recommendations');
    await page.locator('#refresh').click();
    await page.locator('.job-decision-card').first().waitFor();
    assert.equal(mutations.length, 0, 'browsing recommendation/pool must not send writes');
    assert.deepEqual(errors, []);
    checks.push('Untrusted text/URLs cannot execute; viewing/filtering/pool produced zero non-GET requests and zero page errors.');
    writeFileSync(join(evidenceDir, 'ui-results.json'), JSON.stringify({passed: true, checks}, null, 2));
    console.log(JSON.stringify({passed: true, checks}, null, 2));
  } finally {
    if (browser) await browser.close();
    server.kill();
    writeFileSync(join(evidenceDir, 'preview-server.log'), serverLog);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
