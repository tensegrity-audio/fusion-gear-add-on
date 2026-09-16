/* Run with: node tests/test_ui.cjs
 * Requires Playwright and its Chromium browser for development only.
 * Exercises UI safety and editing behavior against a controlled Fusion bridge.
 */
'use strict';
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const ui = path.resolve(__dirname, '../GearStudio/ui');
const data = JSON.parse(fs.readFileSync(path.join(ui, 'demo-data.json'), 'utf8'));
const server = http.createServer((req, res) => {
  const pathname = req.url.split('?')[0];
  const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
  const file = path.resolve(ui, relative);
  if (!file.startsWith(ui + path.sep)) { res.writeHead(403); res.end(); return; }
  try {
    const type = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json' }[path.extname(file)] || 'application/octet-stream';
    const contents = fs.readFileSync(file);
    res.writeHead(200, { 'Content-Type': type }); res.end(contents);
  } catch (_) { res.writeHead(404); res.end(); }
});
let browser;
const clone = (value) => JSON.parse(JSON.stringify(value));

(async () => {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || chromium.executablePath() });
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() => {
    window.__requests = [];
    window.adsk = { fusionSendData(action, text) { window.__requests.push(Object.assign({ action }, JSON.parse(text))); return Promise.resolve('OK'); } };
  });
  await page.goto('http://127.0.0.1:' + server.address().port);
  await page.waitForFunction(() => window.__requests.some((request) => request.action === 'ready'));
  async function emit(action, payload) { await page.evaluate(({ action, payload }) => window.fusionJavaScriptHandler.handle(action, JSON.stringify(payload)), { action, payload }); }
  async function last(action) { return page.evaluate((action) => window.__requests.filter((request) => request.action === action).slice(-1)[0], action); }
  async function waitValidation(previous) { await page.waitForFunction((previous) => { const requests = window.__requests.filter((request) => request.action === 'validate'); return requests.length && requests[requests.length - 1].requestId !== previous; }, previous || ''); return last('validate'); }
  const initial = { catalog: data.catalog, spec: data.samples.spur.spec, presets: [], selection: null, mode: 'create', supportedKinds: data.supportedKinds, host: 'fusion' };
  await emit('state', initial);
  const first = await waitValidation();
  await emit('validation', Object.assign(clone(data.samples.spur.validation), { requestId: first.requestId }));
  assert.equal(await page.locator('#build-gear').isEnabled(), true, 'A checked configuration should be buildable in Fusion.');
  assert.equal(await page.locator('.preview-outline').count(), 1, 'Outline and bore must share an even-odd path.');
  assert.equal(await page.locator('.preview-outline').getAttribute('fill-rule'), 'evenodd');

  await page.locator('#field-module').fill('0 mm');
  assert.equal(await page.locator('#build-gear').isEnabled(), false, 'An edited input must immediately invalidate the build action.');
  const second = await waitValidation(first.requestId);
  await emit('validation', Object.assign(clone(data.samples.spur.validation), { requestId: first.requestId }));
  assert.equal(await page.locator('#build-gear').isEnabled(), false, 'A stale valid response must never enable a build.');
  await emit('validation', { requestId: second.requestId, valid: false, issues: [{ field: 'module', code: 'range', severity: 'error', message: 'Module must be greater than zero.' }], metrics: {}, cost: {} });
  assert.equal(await page.locator('#field-module').getAttribute('aria-invalid'), 'true');
  assert.match(await page.locator('#message-module').innerText(), /greater than zero/);
  assert.equal(await last('build'), undefined, 'Typing must not create geometry.');

  await page.locator('#field-module').fill('shaftModule * 2');
  await page.locator('#field-teeth').fill('31');
  await page.locator('[data-kind="helical"]').click();
  await page.locator('#field-teeth').fill('40');
  await page.locator('[data-kind="spur"]').click();
  assert.equal(await page.locator('#field-module').inputValue(), 'shaftModule * 2', 'Family drafts must retain expressions exactly.');
  assert.equal(await page.locator('#field-teeth').inputValue(), '31', 'Each family must retain its own draft.');
  await page.locator('[data-kind="helical"]').click();
  assert.equal(await page.locator('#field-teeth').inputValue(), '40');

  const editSpec = clone(data.samples.spur.spec); editSpec.id = 'managed-id'; editSpec.name = 'Editable drive gear'; editSpec.parameters.module = 'moduleMaster';
  const beforeEdit = (await last('validate')).requestId;
  await emit('state', Object.assign({}, initial, { spec: editSpec, selection: { id: 'managed-id', name: editSpec.name }, mode: 'edit' }));
  const editValidation = await waitValidation(beforeEdit);
  await emit('validation', Object.assign(clone(data.samples.spur.validation), { requestId: editValidation.requestId }));
  assert.equal(await page.locator('#build-label').innerText(), 'Update gear');
  assert.equal(await page.locator('#field-module').inputValue(), 'moduleMaster');
  await page.locator('#build-gear').click();
  const build = await last('build');
  assert.equal(build.spec.id, 'managed-id', 'An edit must preserve the original gear identity.');
  assert.equal(build.spec.parameters.module, 'moduleMaster', 'Building must preserve expression text.');
  assert.equal(await page.locator('#build-gear').isEnabled(), false, 'A build in progress must not be submitted twice.');
  assert.equal(await page.locator('#field-teeth').isEnabled(), false, 'Build inputs should be stable during a build.');
  await page.locator('#cancel-build').click();
  assert.equal((await last('cancel')).action, 'cancel');
  assert.equal(await page.locator('#cancel-build').isEnabled(), false);
  await emit('result', { ok: false, message: 'Build cancelled. Existing gear preserved.' });
  assert.equal(await page.locator('#gear-name').inputValue(), editSpec.name);
  assert.equal(await page.locator('#field-module').inputValue(), 'moduleMaster');
  assert.equal(await page.locator('#field-teeth').isEnabled(), true);

  await emit('state', Object.assign({}, initial, { host: 'preview' }));
  assert.equal(await page.locator('#host-label').innerText(), 'Autodesk Fusion', 'An unrelated preview message cannot change a native session.');
  assert.equal(await page.locator('#preview-notice').isVisible(), false);

  const origin = 'http://127.0.0.1:' + server.address().port;
  async function newPage() {
    const result = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
    result.on('pageerror', (error) => errors.push(error.message));
    return result;
  }
  async function installNativeBridge(target, dropFirstReady = false) {
    await target.evaluate(({ initial, validation, dropFirstReady }) => {
      window.__requests = [];
      let readyCount = 0;
      window.adsk = { fusionSendData(action, text) {
        const request = Object.assign({ action }, JSON.parse(text));
        window.__requests.push(request);
        if (action === 'ready' && !(dropFirstReady && ++readyCount === 1)) {
          window.fusionJavaScriptHandler.handle('state', JSON.stringify(Object.assign({}, initial, { requestId: request.requestId })));
        } else if (action === 'validate') {
          window.fusionJavaScriptHandler.handle('validation', JSON.stringify(Object.assign({}, validation, { requestId: request.requestId })));
        }
        return Promise.resolve('OK');
      } };
    }, { initial, validation: data.samples.spur.validation, dropFirstReady });
  }

  // Reproduce late Qt injection and a ready message sent before the Python
  // listener was available. Neither may enable preview or lose the handshake.
  const delayed = await newPage();
  let demoRequests = 0;
  delayed.on('request', (request) => { if (request.url().includes('demo-data.json')) demoRequests++; });
  await delayed.clock.install();
  await delayed.goto(origin + '/?host=fusion');
  await delayed.clock.runFor(1000);
  assert.equal(await delayed.evaluate(() => typeof window.adsk), 'undefined', 'Waiting must never replace the native adsk object.');
  assert.equal(await delayed.locator('#host-label').innerText(), 'Connecting to Fusion');
  assert.equal(await delayed.locator('#build-gear').isEnabled(), false);
  assert.equal(await delayed.locator('#preview-notice').isVisible(), false);
  await delayed.evaluate((initial) => window.fusionJavaScriptHandler.handle('state', JSON.stringify(initial)), initial);
  assert.equal(await delayed.locator('#host-label').innerText(), 'Connecting to Fusion', 'Receiving state alone does not establish a usable outgoing connection.');
  await installNativeBridge(delayed, true);
  await delayed.clock.runFor(1200);
  assert.equal(await delayed.locator('#build-gear').isEnabled(), true, 'The live handshake and validation enable Create gear.');
  assert.equal(await delayed.locator('#host-label').innerText(), 'Autodesk Fusion');
  assert.equal(demoRequests, 0, 'The native panel must not load sample preview data.');
  await delayed.locator('#build-gear').click();
  assert.equal(await delayed.evaluate(() => window.__requests.filter((r) => r.action === 'build').length), 1, 'A click reaches the native bridge exactly once.');
  assert.equal(await delayed.evaluate(() => window.__requests.find((r) => r.action === 'build').spec.kind), 'spur');
  // A previously sent ready reply must not clear the in-progress build.
  await delayed.evaluate((initial) => {
    const oldReady = window.__requests.find((r) => r.action === 'ready');
    window.fusionJavaScriptHandler.handle('state', JSON.stringify(Object.assign({}, initial, { requestId: oldReady.requestId })));
  }, initial);
  assert.equal(await delayed.locator('#field-teeth').isEnabled(), false);
  await delayed.clock.runFor(2000);
  assert.equal(await delayed.evaluate(() => window.__requests.filter((r) => r.action === 'build').length), 1, 'Only handshakes can be retried, never builds.');

  const disconnected = await newPage();
  await disconnected.clock.install();
  await disconnected.goto(origin + '/?host=fusion&preview=1');
  await disconnected.clock.runFor(15500);
  assert.equal(await disconnected.locator('#host-label').innerText(), 'Not connected');
  assert.equal(await disconnected.locator('#retry-connection').isVisible(), true);
  assert.equal(await disconnected.locator('#build-gear').isEnabled(), false);
  assert.equal(await disconnected.locator('#preview-notice').isVisible(), false, 'Explicit native mode takes precedence over the preview flag.');
  assert.equal(await disconnected.evaluate(() => typeof window.adsk), 'undefined');
  await installNativeBridge(disconnected);
  await disconnected.clock.runFor(1000);
  assert.equal(await disconnected.evaluate(() => window.__requests.length), 0, 'Polling stops at the connection deadline.');
  await disconnected.locator('#retry-connection').click();
  await disconnected.clock.runFor(10);
  assert.equal(await disconnected.locator('#build-gear').isEnabled(), true);
  assert.equal(await disconnected.locator('#retry-connection').isVisible(), false);

  const preview = await newPage();
  await preview.goto(origin + '/?preview=1');
  await preview.waitForFunction(() => document.getElementById('host-label').textContent === 'Interface preview');
  await preview.locator('#field-module').waitFor();
  assert.equal(await preview.locator('#build-gear').isEnabled(), false, 'An explicit browser preview cannot create a solid.');
  assert.equal(await preview.locator('#preview-notice').isVisible(), true);
  assert.equal(await preview.evaluate(() => typeof window.adsk), 'undefined', 'Preview uses its own transport, never a fake native object.');
  assert.deepEqual(errors, [], 'The page must not produce runtime errors.');
  console.log('PASS: validation, editing, cancellation, delayed native connection, lost handshake recovery, single build delivery, bounded retry, and isolated explicit preview.');
})().catch((error) => { console.error(error); process.exitCode = 1; }).finally(async () => { if (browser) await browser.close(); await new Promise((resolve) => server.close(resolve)); });
