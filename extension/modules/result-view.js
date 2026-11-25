export function createResultView(panel, detail, stale) {
  return {
    clear() {
      panel.hidden = true;
      stale.hidden = true;
      detail.textContent = '';
    },
    markStale() {
      if (!panel.hidden) stale.hidden = false;
    },
    render(data, mode) {
      const mock = mode === 'mock' || data.model_id === 'dev-mock-not-a-model';
      const fixture = data.model_id.endsWith('-fixture') && data.model_version.endsWith('-fixture');
      let explanation = 'Dự đoán của mô hình. Hãy đối chiếu nguồn.';
      if (mock) explanation = 'Giả lập dev/test. Không dùng làm kết quả nghiên cứu.';
      else if (fixture) explanation = 'Mô hình huấn luyện trên dữ liệu tổng hợp. Chỉ dùng để kiểm thử.';
      detail.textContent = [
        explanation,
        'Nhãn: ' + (data.label === 'fake' ? 'Nghi tin giả (fake)' : 'Nghi tin thật (real)'),
        'Điểm fake_score: ' + data.fake_score + ' (thang 0–1, chưa hiệu chuẩn thành xác suất).',
        'Mô hình: ' + data.model_id + ', phiên bản ' + data.model_version,
        'Thời gian xử lý: ' + data.processing_time_ms + ' ms.',
        data.text_truncated ? 'Mô hình đã cắt bớt văn bản.' : 'Văn bản không bị cắt.',
      ].join(' ');
      stale.hidden = true;
      panel.hidden = false;
      return mock;
    },
  };
}
