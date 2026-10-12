const {chromium} = require('playwright');
const {mkdirSync, writeFileSync} = require('node:fs');
const {join, resolve} = require('node:path');
const out = resolve(__dirname, '..', 'work', 'commercial-references');
mkdirSync(out, {recursive: true});
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const context = await browser.newContext({viewport: {width: 1440, height: 1100}, reducedMotion: 'reduce'});
  const references = [
    ['wellfound', 'https://wellfound.com/jobs'],
    ['huntr', 'https://huntr.co/product/job-tracker'],
    ['simplify', 'https://simplify.jobs/'],
    ['welcome', 'https://www.welcometothejungle.com/en/jobs']
  ];
  const results = await Promise.all(references.map(async ([name, url]) => {
    const page = await context.newPage();
    try {
      await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 30000});
      await page.waitForTimeout(1500);
      const consent = page.getByRole('button', {name: /^(Accept all|Accept cookies|I agree|Accept)$/i}).first();
      if (await consent.isVisible().catch(() => false)) await consent.click();
      await page.screenshot({path: join(out, `${name}.png`), fullPage: false});
      return {name, url, title: await page.title(), text: (await page.locator('body').innerText()).slice(0, 4500)};
    } catch (error) {return {name, url, error: error.message};}
    finally {await page.close();}
  }));
  await browser.close();
  writeFileSync(join(out, 'references.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results.map(({text, ...item}) => item), null, 2));
})().catch(error => {console.error(error); process.exitCode = 1;});
