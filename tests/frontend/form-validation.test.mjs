import assert from 'node:assert/strict';
import test from 'node:test';
import { validateDraft } from '../../extension/modules/form-validation.js';

const image = { type: 'image/png' };

test('counts Unicode code points at both inclusive API boundaries', () => {
  assert.deepEqual(validateDraft({ title: '😀'.repeat(500), text: '😀'.repeat(50_000), image }), {});
  assert.ok(validateDraft({ title: '😀'.repeat(501), text: 'ok', image }).title);
  assert.ok(validateDraft({ title: '', text: ' ' + '😀'.repeat(50_000), image }).text);
});

test('requires nonblank text and one selected image', () => {
  const errors = validateDraft({ title: '', text: '\u00a0\n\t', image: null });
  assert.deepEqual(Object.keys(errors), ['text', 'image']);
});

test('allows an optional title and text longer than 1,500 words', () => {
  assert.deepEqual(validateDraft({ title: '', text: 'word '.repeat(1501), image }), {});
});
