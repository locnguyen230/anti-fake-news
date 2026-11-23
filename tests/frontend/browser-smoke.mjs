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
const extension = join(root, 'extension');
const profile = await mkdtemp(join(tmpdir(), 'afn-w1-browser-'));

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
let context;

try {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const origin = 'http://127.0.0.1:' + server.address().port;
  const manifest = JSON.parse(await readFile(join(extension, 'manifest.json'), 'utf8'));
  assert.deepEqual(manifest.permissions, ['activeTab', 'scripting', 'storage']);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1/*']);
  context = await chromium.launchPersistentContext(profile, {
    channel: 'chromium',
    args: [
      '--enable-unsafe-extension-debugging',
      '--disable-extensions-except=' + extension,
      '--load-extension=' + extension,
    ],
  });
  context.setDefaultTimeout(7000);
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  const extensionId = new URL(worker.url()).hostname;
  const browserSession = await context.browser().newBrowserCDPSession();

  async function openAnalysis(source) {
    await source.bringToFront();
    const { targetInfos } = await browserSession.send('Target.getTargets', {
      filter: [{ type: 'tab' }, { exclude: true }],
    });
    const tab = targetInfos.find(target => target.url === source.url());
    assert.ok(tab, 'Chrome tab target for ' + source.url());
    const [page] = await Promise.all([
      context.waitForEvent('page'),
      browserSession.send('Extensions.triggerAction', { id: extensionId, targetId: tab.targetId }),
    ]);
    await page.waitForFunction(() => document.querySelector('#draft')?.disabled === false);
    return page;
  }

  function sessionId(page) {
    return new URL(page.url()).searchParams.get('session');
  }

  const article = await context.newPage();
  await article.goto(origin + '/article.html');
  const analysis = await openAnalysis(article);
  assert.match(await analysis.locator('#title').inputValue(), /Vườn cộng đồng/u);
  const input = await analysis.locator('#text').inputValue();
  assert.match(input, /hạt giống/u);
  assert.match(input, /mang hạt giống đã ghi tên và trao đổi/u);
  assert.doesNotMatch(input, /Menu|Quảng cáo|Nội dung ẩn|chân trang|Đoạn ẩn bằng CSS|Chữ ẩn theo visibility|Không được chọn bài ẩn/u);
  assert.match(await analysis.locator('#source').innerText(), /article\.html/u);
  assert.equal(await analysis.locator('#candidates li').count(), 2);
  assert.match(await analysis.locator('#candidates li').first().innerText(), /\/synthetic\.png/u);
  console.log('PASS article DOM, relative images, filtering and activeTab permission');
  await analysis.locator('#candidates button').first().click();
  await analysis.waitForFunction(() => document.querySelector('#image-preview').naturalWidth > 0
    && !document.querySelector('#image-preview').hidden);
  assert.match(await analysis.locator('#image-status').innerText(), /Đã chọn ảnh/u);
  await analysis.locator('#candidates button').last().click();
  await analysis.waitForFunction(() => document.querySelector('#image-status').textContent.includes('Không tải'));
  assert.equal(await analysis.locator('#image-preview').isHidden(), true);
  await analysis.locator('#image-upload').setInputFiles(join(fixtures, 'synthetic.png'));
  await analysis.waitForFunction(() => !document.querySelector('#image-preview').hidden);
  await analysis.locator('#remove-image').click();
  assert.equal(await analysis.locator('#image-preview').isHidden(), true);
  console.log('PASS candidate bytes, manual upload and preview cleanup');
  await analysis.locator('#analyze').click();
  assert.match(await analysis.locator('#form-status').innerText(), /Chọn một ảnh/u);
  assert.equal(await analysis.locator('#text').inputValue(), input);
  assert.ok(await analysis.locator('#image-upload').evaluate(node => node === document.activeElement));
  console.log('PASS validation preserves draft and focuses the invalid field');
  await analysis.setViewportSize({ width: 360, height: 720 });
  await analysis.locator('#title').focus();
  await analysis.keyboard.press('Tab');
  assert.ok(await analysis.locator('#text').evaluate(node => node === document.activeElement));
  assert.ok(await analysis.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  console.log('PASS keyboard focus and narrow viewport layout');
  if (process.env.AFN_MOCK_TEST_URL) {
    await analysis.locator('#endpoint').fill(process.env.AFN_MOCK_TEST_URL);
    await analysis.locator('#check-health').click();
    await analysis.waitForFunction(() => document.querySelector('#analysis-status').textContent.includes('mock'));
    await analysis.locator('#image-upload').setInputFiles(join(fixtures, 'synthetic.png'));
    await analysis.waitForFunction(() => !document.querySelector('#image-preview').hidden);
    await analysis.locator('#analyze').click();
    await analysis.waitForFunction(() => !document.querySelector('#result').hidden);
    assert.match(await analysis.locator('#result-detail').innerText(), /Giả lập.*dev-mock-not-a-model/u);
    await analysis.locator('#text').fill(input + ' Changed.');
    assert.equal(await analysis.locator('#result').isHidden(), true);
    await analysis.locator('#text').fill(input);
    console.log('PASS browser multipart upload reaches FastAPI mock and labels the result');
    const predictUrl = process.env.AFN_MOCK_TEST_URL + '/predict';
    await analysis.route(predictUrl, async route => {
      await route.fulfill({ status: 503, json: { error_code: 'model_not_ready', request_id: null } });
    }, { times: 1 });
    const beforeRetry = await analysis.locator('#text').inputValue();
    await analysis.locator('#analyze').click();
    await analysis.locator('#retry').waitFor({ state: 'visible' });
    assert.match(await analysis.locator('#analysis-status').innerText(), /chưa sẵn sàng/u);
    assert.equal(await analysis.locator('#text').inputValue(), beforeRetry);
    assert.equal(await analysis.locator('#image-preview').isVisible(), true);
    assert.equal(await analysis.locator('#result').isHidden(), true);
    await analysis.locator('#retry').click();
    await analysis.locator('#result').waitFor({ state: 'visible' });
    console.log('PASS 503 preserves the draft and manual retry reaches the mock');
  }

  const dynamic = await context.newPage();
  await dynamic.goto(origin + '/dynamic.html');
  const empty = await openAnalysis(dynamic);
  assert.match(await empty.locator('#extraction').innerText(), /Chưa tìm thấy/u);
  assert.equal(await empty.locator('#text').inputValue(), '');
  await empty.locator('#text').fill('Bản nháp nhập tay.');
  await dynamic.locator('button').click();
  const loaded = await openAnalysis(dynamic);
  assert.notEqual(sessionId(empty), sessionId(loaded));
  assert.match(await loaded.locator('#text').inputValue(), /xuất hiện sau/u);
  assert.equal(await empty.locator('#text').inputValue(), 'Bản nháp nhập tay.');
  assert.equal(await analysis.locator('#text').inputValue(), input);
  console.log('PASS empty/dynamic DOM, manual entry and isolated sessions');

  const restricted = await context.newPage();
  await restricted.goto('chrome://version/');
  const manual = await openAnalysis(restricted);
  assert.match(await manual.locator('#extraction').innerText(), /Không đọc được tab nguồn/u);
  await manual.locator('#text').fill('Nội dung khi không có quyền đọc tab.');
  assert.equal(await manual.locator('#text').inputValue(), 'Nội dung khi không có quyền đọc tab.');

  const key = 'analysis:' + sessionId(analysis);
  await analysis.close();
  let stored = true;
  for (let attempt = 0; stored && attempt < 20; attempt++) {
    stored = await worker.evaluate(async id => Boolean((await chrome.storage.session.get(id))[id]), key);
    if (stored) await delay(50);
  }
  assert.equal(stored, false);
  assert.match(await loaded.locator('#text').inputValue(), /xuất hiện sau/u);
  console.log('PASS restricted tab fallback and session cleanup');
} finally {
  await context?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  await rm(profile, { recursive: true, force: true });
}
