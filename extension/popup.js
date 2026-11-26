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
const details = get('analysis-details');
const detailImage = get('detail-image');
const client = createApiClient();
const lifecycle = createRequestLifecycle();
const images = createImageSelection(() => {});
const percentage = new Intl.NumberFormat('vi', { style: 'percent', maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('vi');
let detailImageUrl;

function clearDetails() {
  details.hidden = true;
  details.open = false;
  get('detail-text').textContent = '';
  if (detailImageUrl) URL.revokeObjectURL(detailImageUrl);
  detailImage.removeAttribute('src');
  detailImageUrl = undefined;
}

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
  clearDetails();
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
      if (images.file) return { file: images.file, url: candidate.url };
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

function showDetails({ data, mode, threshold }, article, draft, selectedImage, originalLengths) {
  const mock = predictionContext(data, mode) === 'mock';
  const titleLength = Array.from(draft.title).length;
  const textLength = Array.from(draft.text).length;
  const truncatedBeforeSend = titleLength < originalLengths.title || textLength < originalLengths.text;
  const clientTruncation = truncatedBeforeSend ? 'Popup đã rút gọn theo giới hạn gửi. ' : '';
  const modelTruncation = mock ? 'Không áp dụng cho giả lập.'
    : data.text_truncated ? 'Mô hình đã rút gọn thân bài khi tiền xử lý.' : 'Mô hình báo không cắt bớt thân bài.';
  const stages = mock
    ? 'Backend giả lập trả điểm và nhãn cố định sau khi kiểm tra đầu vào.'
    : mode === 'real'
      ? 'Backend chuẩn hóa tiêu đề và thân bài (tối đa 1.500 từ cho thân bài) để tạo đặc trưng TF-IDF. Ảnh được chuẩn hóa sang RGB và mã hóa bằng CLIP ViT-B/32 thành 512 đặc trưng. Hồi quy logistic kết hợp hai nhóm đặc trưng để tính điểm. Điểm từ ngưỡng trở lên cho nhãn Fake.'
      : 'Backend trả điểm và nhãn sau bước dự đoán.';
  const values = {
    'detail-page': article.url,
    'detail-title': draft.title || 'Không có tiêu đề',
    'detail-text-label': `Thân bài (${number.format(textLength)} ký tự)`,
    'detail-text': draft.text,
    'detail-image-info': `${draft.image.type} · ${number.format(draft.image.size)} byte`,
    'detail-image-source': selectedImage.url,
    'detail-pipeline-model': stages,
    'detail-model': data.model_id,
    'detail-version': data.model_version,
    'detail-score': String(data.fake_score),
    'detail-threshold': mock ? 'Không áp dụng' : threshold === null ? 'Backend chưa cung cấp' : String(threshold),
    'detail-time': `${number.format(data.processing_time_ms)} ms`,
    'detail-truncation': clientTruncation + modelTruncation,
    'detail-request': data.request_id,
  };
  for (const [id, value] of Object.entries(values)) get(id).textContent = value;
  detailImageUrl = URL.createObjectURL(draft.image);
  detailImage.src = detailImageUrl;
  details.hidden = false;
}

predict.addEventListener('click', async () => {
  if (predict.disabled) return;
  prediction.hidden = true;
  clearDetails();

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

    const selectedImage = await selectImage(article, request.signal);
    if (!lifecycle.isCurrent(request)) return;
    if (!selectedImage) {
      status.textContent = 'Bài viết cần có ảnh JPEG hoặc PNG để phân tích.';
      return;
    }
    const title = Array.from(article.title);
    const text = Array.from(article.text);
    const draft = {
      title: title.slice(0, 500).join(''),
      text: text.slice(0, 50_000).join(''),
      image: selectedImage.file,
    };
    const response = await client.predict(connection, draft, request.id, request.signal);
    if (!lifecycle.isCurrent(request)) return;
    const { data, mode } = response;
    if (!lifecycle.accepts(request, data.request_id)) throw new ApiError('invalid-response');
    showDetails(response, article, draft, selectedImage, { title: title.length, text: text.length });
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
