import { createResultView } from './result-view.js';
import { ApiError } from './api-client.js';
import { createRequestLifecycle } from './request-lifecycle.js';

export function bindAnalysis({ form, configFields, client, status, result, resultDetail }) {
  const lifecycle = createRequestLifecycle();
  const resultView = createResultView(result, resultDetail);
  const getConfig = () => ({
    endpoint: configFields.endpoint.value,
    demoToken: configFields.demoToken.value,
    timeoutMs: Number(configFields.timeout.value),
  });

  function clearDisplay() {
    resultView.clear();
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
      if (mode === 'mock') {
        status.textContent = data.model_ready
          ? 'Backend mock sẵn sàng cho dev/test.'
          : 'Backend mock phản hồi nhưng chưa sẵn sàng.';
      } else {
        status.textContent = data.model_ready ? 'Backend báo mô hình sẵn sàng.' : 'Backend phản hồi. Mô hình chưa sẵn sàng.';
      }
    } catch {
      if (lifecycle.isCurrent(request)) {
        status.textContent = 'Không kiểm tra được Backend. Hãy xác nhận địa chỉ và dịch vụ cục bộ.';
      }
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
      const mock = resultView.render(data, mode);
      status.textContent = mock ? 'Kết quả giả lập dev/test.' : 'Backend đã trả kết quả.';
    } catch (error) {
      if (!lifecycle.isCurrent(request)) return;
      if (error.kind === 'http' && error.requestId !== null && !lifecycle.accepts(request, error.requestId)) {
        error = new ApiError('invalid-response');
      }
      status.textContent = error.kind === 'timeout'
        ? 'Đã hết thời gian chờ của tiện ích. Bạn có thể thử lại.'
        : 'Yêu cầu không thành công. Hãy kiểm tra dữ liệu và Backend rồi thử lại.';
    } finally {
      lifecycle.finish(request);
    }
  });

  return { checkHealth };
}
