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
  const stale = { hidden: true };
  const view = createResultView(panel, detail, stale);
  view.markStale();
  assert.equal(stale.hidden, true);
  assert.equal(view.render(fixture, 'real'), false);
  assert.equal(panel.hidden, false);
  assert.match(detail.textContent, /Hãy đối chiếu nguồn.*0\.73.*test-v1.*24 ms.*cắt bớt/u);
  view.markStale();
  assert.equal(stale.hidden, false);
  assert.match(detail.textContent, /test-v1/u);
  view.render(fixture, 'real');
  assert.equal(stale.hidden, true);
  view.clear();
  assert.equal(panel.hidden, true);
  assert.equal(detail.textContent, '');
});

test('the explicit mock identifier remains labelled even without a mode header', () => {
  const panel = { hidden: true };
  const detail = { textContent: '' };
  const view = createResultView(panel, detail, { hidden: true });
  assert.equal(view.render({ ...fixture, model_id: 'dev-mock-not-a-model' }, null), true);
  assert.match(detail.textContent, /Giả lập dev\/test/u);
});

test('a trained fixture is identified separately from the mock and research bundles', () => {
  const detail = { textContent: '' };
  const view = createResultView({ hidden: true }, detail, { hidden: true });
  const synthetic = { ...fixture, model_id: 'afn-multimodal-fixture', model_version: 'test-v1-fixture' };
  assert.equal(view.render(synthetic, 'real'), false);
  assert.match(detail.textContent, /huấn luyện trên dữ liệu tổng hợp/u);
});
