import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

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
    response.writeHead(200, { 'Content-Type': mediaType }).end(content);
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
          params: { expression: '(' + fn + ')()', returnByValue: true, awaitPromise: true },
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

async function checkPublisherExtraction(page) {
  const { extractArticle } = await import(pathToFileURL(join(extension, 'extract.js')).href);
  const structures = [
    ['www.reuters.com', '<div class="article-module__main__1N9VH">', '</div>'],
    ['www.reuters.com', '<div class="article-module__main__newHash">', '</div>'],
    ['edition.cnn.com', '<div class="article__content-container">', '</div>'],
    ['www.bbc.co.uk', '<main><article>', '</article></main>'],
    ['apnews.com', '<div class="RichTextStoryBody">', '</div>'],
    ['www.theguardian.com', '<div data-gu-name="body">', '</div>'],
    ['www.aljazeera.com', '<div class="wysiwyg">', '</div>'],
    ['abcnews.com', '<div data-testid="prism-article-body">', '</div>'],
  ];
  for (const [host, opening, closing] of structures) {
    const url = 'https://' + host + '/synthetic-check';
    await page.route(url, route => route.fulfill({
      contentType: 'text/html',
      body: `<article><p>${'Unrelated outside text. '.repeat(10)}</p></article>
        ${opening}<p>First article paragraph.</p><p>Second article paragraph.</p>
        <div class="related-content"><p>Related article excerpt.</p></div>${closing}`,
    }), { times: 1 });
    await page.goto(url);
    assert.equal((await page.evaluate(extractArticle)).text, 'First article paragraph.\n\nSecond article paragraph.', host);
  }

  const genericUrl = 'https://reuters.com.example.test/synthetic-check';
  await page.route(genericUrl, route => route.fulfill({
    contentType: 'text/html',
    body: `<meta property="og:image" content="/logo.png">
      <script type="application/ld+json">{ "broken": }</script>
      <script type="application/ld+json">
        {"@graph":[{"@type":"Organization","image":"/publisher.png"},
        {"@type":["NewsArticle"],"headline":"Main title","image":[{"contentUrl":"../cover.jpg"}]}]}
      </script>
      <main><div class="article-module__main__1N9VH"><p>Unrelated caption.</p></div>
      <section><p>First main paragraph with meaningful editorial text.</p>
      <p>Second main paragraph with enough editorial content.</p>
      <p><a href="/another">Entirely linked promotion</a></p>
      <figure><img alt="Lazy article image" data-srcset="/small.jpg 320w, /fallback.jpg 1200w"></figure>
      <aside><p>Outside text.</p></aside></section></main>`,
  }), { times: 1 });
  await page.route(url => url.hostname === 'reuters.com.example.test' && url.pathname !== '/synthetic-check',
    route => route.fulfill({ status: 404 }));
  await page.goto(genericUrl);
  const generic = await page.evaluate(extractArticle);
  assert.equal(generic.title, 'Main title');
  assert.equal(generic.text, 'First main paragraph with meaningful editorial text.\n\nSecond main paragraph with enough editorial content.');
  assert.deepEqual(generic.candidateImages.map(({ url }) => new URL(url).pathname), ['/cover.jpg', '/fallback.jpg']);
  console.log('PASS publisher selectors, generic paragraph fallback and cover image priorities');
}

let context;
try {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const origin = 'http://127.0.0.1:' + server.address().port;
  const manifest = JSON.parse(await readFile(join(extension, 'manifest.json'), 'utf8'));
  assert.equal(manifest.action.default_popup, 'popup.html');
  assert.deepEqual(manifest.permissions, ['activeTab', 'scripting']);
  assert.deepEqual(manifest.host_permissions, [
    'http://127.0.0.1/*',
    'https://www.reuters.com/*',
    'https://*.reutersmedia.net/*',
    'https://cloudfront-us-east-2.images.arcpublishing.com/*',
    'https://media.cnn.com/*',
    'https://ichef.bbci.co.uk/*',
    'https://dims.apnews.com/*',
    'https://i.guim.co.uk/*',
    'https://www.aljazeera.com/*',
    'https://i.abcnewsfe.com/*',
  ]);

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
    .filter(control => !control.closest('[hidden]'))
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
    assert.equal(await popup.evaluate(() => document.querySelector('#analysis-details').hidden), true);
  }
  if (!result.hidden) {
    assert.deepEqual(await popup.evaluate(() => {
      const details = document.querySelector('#analysis-details');
      return [details.hidden, details.open, details.querySelector('summary').textContent];
    }), [false, false, 'Xem chi tiết']);
    await popup.evaluate(() => document.querySelector('#analysis-details summary').click());
    const trace = await popup.evaluate(async () => {
      const get = id => document.getElementById(id).textContent;
      const image = document.querySelector('#detail-image');
      const bytes = await (await fetch(image.src)).arrayBuffer();
      return {
        open: document.querySelector('#analysis-details').open,
        title: get('detail-title'), text: get('detail-text'), imageSource: get('detail-image-source'),
        imageBytes: Array.from(new Uint8Array(bytes)), model: get('detail-model'),
        threshold: get('detail-threshold'), score: Number(get('detail-score')),
        pipeline: get('detail-pipeline-model'), request: get('detail-request'),
      };
    });
    assert.equal(trace.open, true);
    assert.equal(trace.title, 'Vườn cộng đồng mở buổi đổi hạt giống');
    assert.match(trace.text, /hạt giống đã ghi tên và trao đổi/u);
    assert.doesNotMatch(trace.text, /Quảng cáo|Nội dung ẩn|Menu/u);
    assert.equal(trace.imageSource, origin + '/synthetic.png');
    assert.deepEqual(Buffer.from(trace.imageBytes), await readFile(join(fixtures, 'synthetic.png')));
    assert.match(trace.request, /^[0-9a-f-]{36}$/u);
    if (outcome === 'mock') {
      assert.equal(trace.model, 'dev-mock-not-a-model');
      assert.equal(trace.threshold, 'Không áp dụng');
      assert.match(trace.pipeline, /giả lập.*cố định/u);
    } else {
      assert.match(trace.threshold, /^(?:0(?:\.\d+)?|1(?:\.0+)?)$/u);
      assert.equal(result.verdict, trace.score >= Number(trace.threshold) ? 'Fake' : 'Real');
      assert.match(trace.pipeline, /TF-IDF.*CLIP.*Hồi quy logistic/u);
    }
    assert.equal(await popup.evaluate(() => {
      document.querySelector('#predict').click();
      return document.querySelector('#analysis-details').hidden;
    }), true);
    await poll(() => popup.evaluate(() => !document.querySelector('#predict').disabled), 'repeat analysis', 50_000);
    assert.equal(await popup.evaluate(() => document.querySelector('#analysis-details').open), false);
    console.log('PASS analysis details match the submitted text and image, model pipeline and score');
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

    await source.goto('http://localhost:' + server.address().port + '/article.html');
    const genericPopup = await openPopup(cdp, id, source, manifest.action.default_popup);
    assert.equal((await analyze(genericPopup)).status, '');
    await genericPopup.close();

    await checkPublisherExtraction(source);
  }
} finally {
  await context?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  await rm(profile, { recursive: true, force: true });
}
