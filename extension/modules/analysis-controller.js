import { createResultView } from './result-view.js';
import { ApiError } from './api-client.js';

export function bindAnalysis({ form, configFields, client, status, result, resultDetail }) {
  let activeRequest = null;
  const resultView = createResultView(result, resultDetail);
  const getConfig = () => ({
    endpoint: configFields.endpoint.value,
    demoToken: configFields.demoToken.value,
    timeoutMs: Number(configFields.timeout.value),
  });

  function invalidate() {
    activeRequest = null;
    resultView.clear();
    status.textContent = '';
  }

  form.addEventListener('afn:draft-change', invalidate);
  for (const field of Object.values(configFields)) field.addEventListener('input', invalidate);

  async function checkHealth() {
    try {
      const { data, mode } = await client.health(getConfig());
      if (mode === 'mock') {
        status.textContent = data.model_ready
          ? 'Backend mock sẵn sàng cho dev/test.'
          : 'Backend mock phản hồi nhưng chưa sẵn sàng.';
      } else {
        status.textContent = data.model_ready ? 'Backend báo mô hình sẵn sàng.' : 'Backend phản hồi. Mô hình chưa sẵn sàng.';
      }
    } catch {
      status.textContent = 'Không kiểm tra được Backend. Hãy xác nhận địa chỉ và dịch vụ cục bộ.';
    }
  }

  form.addEventListener('afn:analyze', async ({ detail }) => {
    invalidate();
    const id = crypto.randomUUID();
    activeRequest = id;
    status.textContent = 'Đang phân tích…';
    try {
      const { data, mode } = await client.predict(getConfig(), detail, id);
      if (id !== activeRequest) return;
      if (data.request_id !== id) throw new ApiError('invalid-response');
      const mock = resultView.render(data, mode);
      status.textContent = mock ? 'Kết quả giả lập dev/test.' : 'Backend đã trả kết quả.';
    } catch (error) {
      if (id !== activeRequest) return;
      status.textContent = error.kind === 'timeout'
        ? 'Đã hết thời gian chờ của tiện ích. Bạn có thể thử lại.'
        : 'Yêu cầu không thành công. Hãy kiểm tra dữ liệu và Backend rồi thử lại.';
    }
  });

  return { checkHealth };
}
