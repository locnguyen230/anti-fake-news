import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.AFN_PLAYWRIGHT_PATH || 'playwright');
const root = fileURLToPath(new URL('../../', import.meta.url));
const fixtures = join(root, 'tests', 'fixtures', 'pages');
const extension = process.env.AFN_EXTENSION_UNPACKED || join(root, 'release', 'extension');
const outcome = process.env.AFN_SMOKE_OUTCOME || 'mock';
const profile = await mkdtemp(join(tmpdir(), 'afn-browser-'));

const mediaTypes = new Map([
  ['/article.html', 'text/html; charset=UTF-8'],
  ['/dynamic.html', 'text/html; charset=UTF-8'],
  ['/dynamic.js', 'text/javascript'],
  ['/synthetic.png', 'image/png'],
]);
const server = createServer(async (request, response) => {
  const mediaType = mediaTypes.get(request.url);
  if (!mediaType) {
    response.writeHead(404).end();
    return;
  }
  try {
    const content = await readFile(join(fixtures, request.url.slice(1)));
    response.writeHead(200, { 'Content-Type': mediaType, 'Access-Control-Allow-Origin': '*' }).end(content);
  } catch {
    response.writeHead(500).end();
  }
});

async function poll(check, description, timeoutMs = 7000) {
  const deadline = Date.now() + timeoutMs;
  do {
    const result = await check();
    if (result) return result;
    await delay(50);
  } while (Date.now() < deadline);
  assert.fail('Timed out waiting for ' + description);
}

async function openPopup(cdp, extensionId, source, popupPath) {
  await source.bringToFront();
  const { targetInfos } = await cdp.send('Target.getTargets', {
    filter: [{ type: 'tab' }, { exclude: true }],
  });
  const tab = targetInfos.find(target => target.url === source.url());
  assert.ok(tab, 'Source tab target');
  await cdp.send('Extensions.triggerAction', { id: extensionId, targetId: tab.targetId });

  const popupUrl = 'chrome-extension://' + extensionId + '/' + popupPath;
  const popup = await poll(async () => {
    const { targetInfos } = await cdp.send('Target.getTargets', { filter: [{ type: 'page' }] });
    return targetInfos.find(target => target.url === popupUrl);
  }, 'toolbar popup');

  // Playwright does not expose the toolbar bubble through BrowserContext.pages().
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId: popup.targetId });
  let nextId = 0;
  async function evaluate(fn) {
    const id = ++nextId;
    const reply = await new Promise((resolve, reject) => {
      const eventName = 'Target.receivedMessageFromTarget';
      function finish(error, result) {
        clearTimeout(timer);
        cdp.off(eventName, receive);
        if (error) reject(error);
        else resolve(result);
      }
      function receive(event) {
        if (event.sessionId !== sessionId) return;
        const message = JSON.parse(event.message);
        if (message.id === id) finish(null, message);
      }
      const timer = setTimeout(() => finish(Error('Popup evaluation timed out')), 7000);
      cdp.on(eventName, receive);
      cdp.send('Target.sendMessageToTarget', {
        sessionId,
        message: JSON.stringify({
          id, method: 'Runtime.evaluate',
          params: { expression: '(' + fn + ')()', returnByValue: true },
        }),
      }).catch(finish);
    });
    assert.ok(!reply.error && !reply.result.exceptionDetails, 'Popup evaluation must succeed');
    return reply.result.result.value;
  }
  await poll(() => evaluate(() => document.querySelector('#predict')?.disabled === false), 'popup initialization');
  return { evaluate, close: () => cdp.send('Target.closeTarget', { targetId: popup.targetId }) };
}

async function analyze(popup) {
  await popup.evaluate(() => document.querySelector('#predict').click());
  await poll(() => popup.evaluate(() => !document.querySelector('#predict').disabled), 'analysis completion', 50_000);
  return popup.evaluate(() => ({
    hidden: document.querySelector('#prediction').hidden,
    score: document.querySelector('#score').innerText,
    verdict: document.querySelector('#verdict').innerText,
    context: document.querySelector('#context').innerText,
    status: document.querySelector('#status').innerText,
  }));
}

let context;
try {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const origin = 'http://127.0.0.1:' + server.address().port;
  const manifest = JSON.parse(await readFile(join(extension, 'manifest.json'), 'utf8'));
  assert.equal(manifest.action.default_popup, 'popup.html');
  assert.deepEqual(manifest.permissions, ['activeTab', 'scripting']);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1/*']);

  context = await chromium.launchPersistentContext(profile, {
    channel: 'chromium',
    ignoreDefaultArgs: ['--disable-extensions'],
    args: ['--enable-unsafe-extension-debugging'],
  });
  const cdp = await context.browser().newBrowserCDPSession();
  const { id } = await cdp.send('Extensions.loadUnpacked', { path: extension });
  const source = await context.newPage();
  await source.goto(origin + '/article.html');
  const popup = await openPopup(cdp, id, source, manifest.action.default_popup);

  assert.deepEqual(await popup.evaluate(() => [...document.querySelectorAll('button, input, summary, a')]
    .map(control => [control.tagName, control.textContent.trim()])), [['BUTTON', 'Phân tích']]);
  assert.equal(await popup.evaluate(() => document.querySelector('#prediction').hidden), true);

  const result = await analyze(popup);
  if (outcome === 'mock') {
    assert.deepEqual(result, { hidden: false, score: '42%', verdict: 'Real', context: 'Kết quả giả lập', status: '' });
  } else if (outcome === 'real') {
    assert.equal(result.hidden, false);
    assert.match(result.score, /^\d+(?:,\d+)?%$/u);
    assert.match(result.verdict, /^(Fake|Real)$/u);
    assert.equal(result.context, '');
  } else {
    assert.equal(result.hidden, true);
    assert.match(result.status, outcome === 'unauthorized' ? /từ chối xác thực/u : /chưa sẵn sàng/u);
  }
  console.log('PASS one-click native popup with embedded configuration (' + outcome + ')');
  await popup.close();

  if (outcome === 'mock') {
    await source.goto(origin + '/dynamic.html');
    const empty = await openPopup(cdp, id, source, manifest.action.default_popup);
    assert.match((await analyze(empty)).status, /Không đọc được nội dung/u);
    await empty.close();

    await source.locator('button').click();
    const noImage = await openPopup(cdp, id, source, manifest.action.default_popup);
    const unavailable = await analyze(noImage);
    assert.equal(unavailable.hidden, true);
    assert.match(unavailable.status, /cần có ảnh JPEG hoặc PNG/u);
    await noImage.close();
    console.log('PASS missing content and missing image report clear popup errors');
  }
} finally {
  await context?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  await rm(profile, { recursive: true, force: true });
}
