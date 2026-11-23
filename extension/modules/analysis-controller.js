import { ApiError } from './api-client.js';
import { bindErrorRecovery } from './error-recovery.js';
import { createRequestLifecycle } from './request-lifecycle.js';

export function bindAnalysis({ form, configFields, client, status, result, resultDetail, retry }) {
  const lifecycle = createRequestLifecycle();
  const recovery = bindErrorRecovery(status, retry);
  const getConfig = () => ({
    endpoint: configFields.endpoint.value,
    demoToken: configFields.demoToken.value,
    timeoutMs: Number(configFields.timeout.value),
  });

  function clearDisplay() {
    recovery.clear();
    result.hidden = true;
    resultDetail.textContent = '';
    status.textContent = '';
  }

  function invalidate() {
    lifecycle.invalidate();
    clearDisplay();
  }

  form.addEventListener('afn:draft-change', invalidate);
  for (const field of Object.values(configFields)) field.addEventListener('input', invalidate);
  addEventListener('pagehide', invalidate);

  async function checkHealth() {
    clearDisplay();
    const request = lifecycle.begin();
    status.textContent = 'Đang kiểm tra kết nối…';
    try {
      const { data, mode } = await client.health(getConfig(), request.signal);
      if (!lifecycle.isCurrent(request)) return;
      status.textContent = mode === 'mock'
        ? 'Backend mock sẵn sàng cho dev/test.'
        : (data.model_ready ? 'Backend báo mô hình sẵn sàng.' : 'Backend phản hồi. Mô hình chưa sẵn sàng.');
    } catch (error) {
      if (lifecycle.isCurrent(request)) recovery.show(error, checkHealth);
    } finally {
      lifecycle.finish(request);
    }
  }

  form.addEventListener('afn:analyze', async ({ detail }) => {
    clearDisplay();
    const request = lifecycle.begin();
    status.textContent = 'Đang phân tích…';
    try {
      const { data, mode } = await client.predict(getConfig(), detail, request.id, request.signal);
      if (!lifecycle.isCurrent(request)) return;
      if (!lifecycle.accepts(request, data.request_id)) throw new ApiError('invalid-response');
      const mock = mode === 'mock' || data.model_id === 'dev-mock-not-a-model';
      status.textContent = mock ? 'Kết quả giả lập dev/test.' : 'Backend đã trả kết quả.';
      resultDetail.textContent = [
        mock ? 'Giả lập dev/test. Không dùng làm kết quả nghiên cứu.' : 'Dự đoán của mô hình. Hãy đối chiếu nguồn.',
        'Nhãn: ' + (data.label === 'fake' ? 'Nghi tin giả (fake)' : 'Nghi tin thật (real)'),
        'Điểm fake_score: ' + data.fake_score + ' (thang 0–1, chưa hiệu chuẩn thành xác suất).',
        'Mô hình: ' + data.model_id + ', phiên bản ' + data.model_version,
        'Thời gian xử lý: ' + data.processing_time_ms + ' ms.',
        data.text_truncated ? 'Mô hình đã cắt bớt văn bản.' : 'Văn bản không bị cắt.',
      ].join(' ');
      result.hidden = false;
    } catch (error) {
      if (!lifecycle.isCurrent(request)) return;
      if (error.kind === 'http' && error.requestId !== null && !lifecycle.accepts(request, error.requestId)) {
        error = new ApiError('invalid-response');
      }
      recovery.show(error, () => form.requestSubmit());
    } finally {
      lifecycle.finish(request);
    }
  });

  return { checkHealth };
}
