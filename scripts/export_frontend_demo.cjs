/* Generate a standalone showcase from the canonical UI and synthetic fixtures.
   No dependencies, backend, external requests or private data directory reads. */
const {readFileSync, writeFileSync, mkdirSync, copyFileSync} = require('node:fs');
const {join, resolve} = require('node:path');
const root = resolve(__dirname, '..');
const source = join(root, 'src', 'job_agent', 'static');
const fixture = join(root, 'examples', 'frontend-demo');
const output = join(root, 'outputs', 'frontend-demo');
mkdirSync(output, {recursive: true});
const read = (directory, name) => readFileSync(join(directory, name), 'utf8');
const files = {};
for (const name of ['styles.css', 'commercial.css', 'app.js', 'recommendations.js', 'ui-icons.js', 'brand-icon.svg']) files[name] = read(source, name);
files['commercial.css'] = files['commercial.css'].replace('.header-actions { gap: 10px; }', '.header-actions { gap: 10px; flex-wrap: wrap; }');
files['app.js'] = files['app.js'].replace(/\blocalStorage\./g, 'window.DemoStorage.');
files['demo-data.js'] = read(fixture, 'demo-data.js');
files['demo-api.js'] = read(fixture, 'demo-api.js');
files['README.md'] = read(fixture, 'README.md');
let html = read(source, 'index.html')
  .replace(/\b(href|src)="\/([^"]+)"/g, '$1="./$2"')
  .replace('<title>职来 Agent</title>', '<title>职来求职助手 · 前端演示</title>')
  .replace('<span>求职工作台</span>', '<span>前端演示 · 合成数据</span>')
  .replace('<span id="last-refresh" class="muted"></span>', '<span id="last-refresh" class="muted"></span><button class="button ghost" id="reset-demo" type="button">重置演示</button>')
  .replace('  <script src="./app.js"></script>', '  <script src="./demo-data.js"></script>\n  <script src="./demo-api.js"></script>\n  <script src="./app.js"></script>');
files['index.html'] = html;
for (const [name, content] of Object.entries(files)) writeFileSync(join(output, name), content, 'utf8');
copyFileSync(join(root, 'LICENSE'), join(output, 'LICENSE'));
for (const name of ['styles.css', 'commercial.css']) {
  html = html.replace(`<link rel="stylesheet" href="./${name}">`, () => `<style data-source="${name}">\n${files[name]}\n</style>`);
}
for (const name of ['ui-icons.js', 'recommendations.js', 'demo-data.js', 'demo-api.js', 'app.js']) {
  // Callback replacement preserves literal $$ selectors in the source code.
  html = html.replace(`<script src="./${name}"></script>`, () => `<script data-source="${name}">\n${files[name].replace(/<\/script/gi, '<\\/script')}\n</script>`);
}
html = html.replaceAll('./brand-icon.svg', 'data:image/svg+xml,' + encodeURIComponent(files['brand-icon.svg']));
writeFileSync(join(root, 'outputs', 'JobAgent-frontend-demo.html'), html, 'utf8');
console.log('Frontend demo: outputs/frontend-demo/index.html');
console.log('Single file: outputs/JobAgent-frontend-demo.html');
