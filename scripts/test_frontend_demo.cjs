/* Optional browser QA: export first; needs Node Playwright and a local browser. */
const {chromium} = require('playwright');
const {pathToFileURL} = require('node:url');
const {join, resolve} = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({channel: process.env.TEST_BROWSER_CHANNEL || 'msedge', headless: true});
  try {
    for (const file of ['outputs/frontend-demo/index.html', 'outputs/JobAgent-frontend-demo.html']) {
      const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
      const errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => { if (/^https?:/.test(request.url())) requests.push(request.url()); });
      await page.goto(pathToFileURL(join(root, file)).href);
      await page.locator('.job-decision-card').waitFor();
      assert((await page.locator('.job-decision-card h3').textContent()).includes('数据产品经理'));
      assert.equal(await page.locator('#recommendation-order').textContent(), '1 / 2');
      await page.locator('#recommendation-next').click();
      assert.equal(await page.locator('#recommendation-order').textContent(), '2 / 2');
      await page.locator('#recommendation-prev').click();
      await page.locator('.proof-link').first().click();
      assert(await page.locator('.decision-details').getAttribute('open') !== null);
      await page.setViewportSize({width: 390, height: 844});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.setViewportSize({width: 1440, height: 1000});
      const nav = name => page.locator('#nav').getByRole('button', {name, exact: true}).click();
      await nav('全部岗位');
      assert.equal(await page.locator('#jobs-body tr').count(), 4);
      await page.locator('#job-search').fill('示例云');
      assert.equal(await page.locator('#jobs-body tr').count(), 1);
      await nav('求职进度');
      await page.locator('#applications-body [data-edit-progress]').first().click();
      const note = '<img src=x onerror="window.__unsafe=true">本地备注';
      await page.locator('#progress-stage').selectOption('Offer');
      await page.locator('#progress-note').fill(note);
      await page.locator('#save-progress').click();
      await page.waitForFunction(() => !document.querySelector('#progress-dialog').open);
      assert.equal(await page.locator('#applications-body img').count(), 0);
      await page.reload();
      await page.locator('.job-decision-card').waitFor();
      await nav('求职进度');
      assert((await page.locator('#applications-body').textContent()).includes(note));
      await page.evaluate(async () => {
        const config = await (await fetch('/api/config')).json();
        config.candidate.profile_source = 'resume';
        await fetch('/api/config', {method: 'PUT', body: JSON.stringify(config)});
      });
      await page.locator('#refresh').click();
      await page.waitForTimeout(100);
      await nav('我的档案');
      await page.locator('#cfg-name').fill('未保存的档案');
      await nav('设置');
      await page.locator('#cfg-boss-keywords').fill('保存渠道');
      await page.locator('#save-settings-config').click();
      await page.waitForFunction(() => !document.querySelector('#save-settings-config').disabled);
      let config = await page.evaluate(async () => (await fetch('/api/config')).json());
      assert.equal(config.candidate.name, '演示候选人');
      assert.equal(config.candidate.profile_source, 'resume');
      await page.locator('#cfg-boss-keywords').fill('未保存的渠道');
      await nav('我的档案');
      await page.locator('#cfg-name').fill('已保存的档案');
      await page.locator('#save-basic-config').click();
      await page.waitForFunction(() => !document.querySelector('#save-basic-config').disabled);
      config = await page.evaluate(async () => (await fetch('/api/config')).json());
      assert.equal(config.candidate.name, '已保存的档案');
      assert.equal(config.candidate.profile_source, 'manual');
      assert.deepEqual(config.preferences.boss_keywords, ['保存渠道']);
      assert.equal(await page.evaluate(() => !!window.__unsafe), false);
      assert.deepEqual(errors, []);
      assert.deepEqual(requests, []);
      console.log(JSON.stringify({file, passed: true, httpRequests: requests.length}));
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
