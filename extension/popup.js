import { readArticle } from './extract.js';
import { ApiError, createApiClient, validateConnection } from './modules/api-client.js';
import { describeApiError } from './modules/error-recovery.js';
import { createImageSelection } from './modules/image-selection.js';
import { createRequestLifecycle } from './modules/request-lifecycle.js';
import { predictionContext } from './modules/result-view.js';
import { CONNECTION_KEY, readConnection } from './modules/session.js';

const get = id => document.getElementById(id);
const form = get('connection');
const settings = get('settings');
const endpoint = get('endpoint');
const token = get('demo-token');
const timeout = get('timeout');
const predict = get('predict');
const manual = get('manual');
const status = get('status');
const prediction = get('prediction');
const context = get('context');
const client = createApiClient();
const lifecycle = createRequestLifecycle();
const images = createImageSelection(() => {});
const percentage = new Intl.NumberFormat('vi', { style: 'percent', maximumFractionDigits: 2 });

const [[tab], config] = await Promise.all([
  chrome.tabs.query({ active: true, currentWindow: true }).catch(() => []),
  readConnection().catch(() => null),
]);
if (config) {
  endpoint.value = config.endpoint;
  token.value = config.demoToken;
  timeout.value = config.timeoutMs;
}

addEventListener('pagehide', () => {
  lifecycle.invalidate();
  images.clear();
});

async function selectImage(article, signal) {
  let expired = false;
  const timer = setTimeout(() => {
    expired = true;
    images.clear();
  }, 15_000);
  try {
    for (const candidate of article.candidateImages) {
      if (expired || signal.aborted) break;
      await images.chooseCandidate(candidate.url, article.url);
      if (images.file) return images.file;
    }
    return null;
  } finally {
    clearTimeout(timer);
    images.clear();
  }
}

function showPrediction(data, mode) {
  prediction.dataset.label = data.label;
  get('score').textContent = percentage.format(data.fake_score);
  get('verdict').textContent = data.label === 'fake' ? 'Fake' : 'Real';
  const source = predictionContext(data, mode);
  context.textContent = { mock: 'Kết quả giả lập', fixture: 'Kết quả từ mô hình kiểm thử' }[source] ?? '';
  context.hidden = !source;
  status.textContent = '';
  prediction.hidden = false;
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (predict.disabled) return;
  prediction.hidden = true;
  const connection = { endpoint: endpoint.value, demoToken: token.value.trim(), timeoutMs: timeout.valueAsNumber };
  if (!connection.demoToken) {
    settings.open = true;
    status.textContent = describeApiError(new ApiError('http', { status: 401 }));
    token.focus();
    return;
  }

  const request = lifecycle.begin();
  predict.disabled = true;
  status.textContent = 'Đang phân tích bài viết…';
  try {
    validateConnection(connection);
    await chrome.storage.session.set({ [CONNECTION_KEY]: connection });
    settings.open = false;
    const article = await readArticle(tab);
    if (!lifecycle.isCurrent(request)) return;
    if (!article.text) {
      status.textContent = 'Không đọc được nội dung bài viết. Bạn có thể nhập nội dung thủ công.';
      return;
    }

    const image = await selectImage(article, request.signal);
    if (!lifecycle.isCurrent(request)) return;
    if (!image) {
      status.textContent = 'Không tải được ảnh JPEG hoặc PNG từ bài viết. Hãy chọn ảnh thủ công.';
      return;
    }
    const { data, mode } = await client.predict(connection, {
      title: Array.from(article.title).slice(0, 500).join(''),
      text: Array.from(article.text).slice(0, 50_000).join(''),
      image,
    }, request.id, request.signal);
    if (!lifecycle.isCurrent(request)) return;
    if (!lifecycle.accepts(request, data.request_id)) throw new ApiError('invalid-response');
    showPrediction(data, mode);
  } catch (error) {
    if (!lifecycle.isCurrent(request)) return;
    status.textContent = describeApiError(error);
    if (error.kind === 'config' || error.status === 401) settings.open = true;
  } finally {
    if (lifecycle.isCurrent(request)) predict.disabled = false;
    lifecycle.finish(request);
  }
});

manual.addEventListener('click', async () => {
  manual.disabled = true;
  const opened = await chrome.runtime.sendMessage({ type: 'open-manual-analysis', tabId: tab?.id }).catch(() => false);
  if (!opened) {
    status.textContent = 'Không mở được trang phân tích thủ công. Hãy thử lại.';
    manual.disabled = false;
  }
});

predict.disabled = false;
manual.disabled = false;
