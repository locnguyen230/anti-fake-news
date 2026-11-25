import assert from 'node:assert/strict';
import test from 'node:test';
import { createResultView } from '../../extension/modules/result-view.js';

const fixture = {
  label: 'fake', fake_score: 0.73, model_id: 'fixture-real-model', model_version: 'test-v1',
  processing_time_ms: 24, text_truncated: true,
};

test('render keeps the limitations, version and truncation next to a real response', () => {
  const panel = { hidden: true };
  const detail = { textContent: '' };
  const warning = { textContent: '' };
  const stale = { hidden: true };
  const view = createResultView(panel, detail, warning, stale);
  view.markStale();
  assert.equal(stale.hidden, true);
  assert.equal(view.render(fixture, 'real'), false);
  assert.equal(panel.hidden, false);
  assert.match(warning.textContent, /dữ liệu huấn luyện.*đối chiếu nguồn.*xác minh sự thật/u);
  assert.match(detail.textContent, /fake.*0\.73.*chưa hiệu chuẩn.*fixture-real-model.*test-v1.*24 ms.*cắt bớt/su);
  view.markStale();
  assert.equal(stale.hidden, false);
  assert.match(detail.textContent, /test-v1/u);
  view.render({ ...fixture, label: 'real', text_truncated: false }, 'real');
  assert.match(detail.textContent, /Nghi tin thật.*toàn bộ văn bản/su);
  assert.equal(stale.hidden, true);
  view.clear();
  assert.equal(panel.hidden, true);
  assert.equal(detail.textContent, '');
  assert.equal(warning.textContent, '');
});

test('the explicit mock identifier remains labelled even without a mode header', () => {
  const warning = { textContent: '' };
  const view = createResultView({ hidden: true }, { textContent: '' }, warning, { hidden: true });
  assert.equal(view.render({ ...fixture, model_id: 'dev-mock-not-a-model' }, null), true);
  assert.match(warning.textContent, /Giả lập dev\/test/u);
});

test('a trained fixture is identified separately from the mock and research bundles', () => {
  const warning = { textContent: '' };
  const view = createResultView({ hidden: true }, { textContent: '' }, warning, { hidden: true });
  const synthetic = { ...fixture, model_id: 'afn-multimodal-fixture', model_version: 'test-v1-fixture' };
  assert.equal(view.render(synthetic, 'real'), false);
  assert.match(warning.textContent, /huấn luyện trên dữ liệu tổng hợp/u);
});
