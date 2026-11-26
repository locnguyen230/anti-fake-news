import { readArticle } from './extract.js';
import { ApiError, createApiClient } from './modules/api-client.js';
import { describeApiError } from './modules/error-recovery.js';
import { createImageSelection } from './modules/image-selection.js';
import { createRequestLifecycle } from './modules/request-lifecycle.js';
import { predictionContext } from './modules/result-view.js';

const get = id => document.getElementById(id);
const predict = get('predict');
const status = get('status');
const prediction = get('prediction');
const context = get('context');
const client = createApiClient();
const lifecycle = createRequestLifecycle();
const images = createImageSelection(() => {});
const percentage = new Intl.NumberFormat('vi', { style: 'percent', maximumFractionDigits: 2 });

async function readConnection() {
  try {
    const response = await fetch(chrome.runtime.getURL('afn-runtime-config.json'));
    if (!response.ok) throw Error();
    const config = await response.json();
    if (typeof config?.endpoint !== 'string' || typeof config.demoToken !== 'string'
        || !config.demoToken.trim()) throw Error();
    return { endpoint: config.endpoint, demoToken: config.demoToken, timeoutMs: 30_000 };
  } catch {
    throw new ApiError('package-config');
  }
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

predict.addEventListener('click', async () => {
  if (predict.disabled) return;
  prediction.hidden = true;

  const request = lifecycle.begin();
  predict.disabled = true;
  status.textContent = 'Đang phân tích bài viết…';
  try {
    const [[tab], connection] = await Promise.all([
      chrome.tabs.query({ active: true, currentWindow: true }),
      readConnection(),
    ]);
    const article = await readArticle(tab);
    if (!lifecycle.isCurrent(request)) return;
    if (!article.text) {
      status.textContent = 'Không đọc được nội dung. Hãy mở một trang bài viết rồi thử lại.';
      return;
    }

    const image = await selectImage(article, request.signal);
    if (!lifecycle.isCurrent(request)) return;
    if (!image) {
      status.textContent = 'Bài viết cần có ảnh JPEG hoặc PNG để phân tích.';
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
    if (error.kind === 'package-config' || error.kind === 'config') {
      status.textContent = 'Thiếu cấu hình tích hợp. Hãy nạp bản tiện ích đã đóng gói.';
    } else if (error.status === 401 || error.status === 403) {
      status.textContent = 'Backend từ chối xác thực. Hãy dùng gói tiện ích được tạo từ cấu hình Backend hiện tại.';
    } else if (error.status === 400) {
      status.textContent = 'Backend không xử lý được nội dung hoặc ảnh của bài viết này.';
    } else {
      status.textContent = describeApiError(error);
    }
  } finally {
    if (lifecycle.isCurrent(request)) predict.disabled = false;
    lifecycle.finish(request);
  }
});

predict.disabled = false;
