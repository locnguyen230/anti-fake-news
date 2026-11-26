import assert from 'node:assert/strict';
import test from 'node:test';
import { readSession, sessionKey } from '../../extension/modules/session.js';

const sessions = new Map();
const tabs = new Map();
const injections = [];
let nextTabId = 100;
let onMessage;
let closed;
let extracted;
globalThis.chrome = {
  scripting: {
    async executeScript(details) {
      injections.push(details);
      if (extracted instanceof Error) throw extracted;
      return [{ result: extracted }];
    },
  },
  runtime: {
    getURL: page => 'chrome-extension://afn-test/' + page,
    onMessage: { addListener: handler => { onMessage = handler; } },
  },
  storage: {
    session: {
      async get(key) { return { [key]: sessions.get(key) }; },
      async set(values) { for (const [key, value] of Object.entries(values)) sessions.set(key, value); },
      async remove(keys) { for (const key of [keys].flat()) sessions.delete(key); },
    },
  },
  tabs: {
    onRemoved: { addListener: handler => { closed = handler; } },
    async create(tab) {
      const id = nextTabId++;
      tabs.set(id, tab);
      return { id, ...tab };
    },
    async get(id) {
      const tab = tabs.get(id);
      if (!tab) throw Error('Tab closed');
      return tab;
    },
  },
};

await import('../../extension/service-worker.js');

function article(url, text) {
  return { url, text, title: 'Fixture', candidateImages: [], extraction: 'dom' };
}

async function open(tab) {
  const analysisId = nextTabId;
  assert.equal(await requestManualAnalysis(tab), true);
  const { search } = new URL(tabs.get(analysisId).url);
  return { analysisId, session: await readSession(search) };
}

function requestManualAnalysis(tab) {
  tabs.set(tab.id, tab);
  return new Promise(resolve => {
    const sender = { url: chrome.runtime.getURL('popup.html') };
    assert.equal(onMessage({ type: 'open-manual-analysis', tabId: tab.id }, sender, resolve), true);
  });
}

test('the popup manual action injects into the source tab and owns each analysis session', async () => {
  const firstUrl = 'https://one.example/first';
  const secondUrl = 'https://two.example/second';
  extracted = article(firstUrl, 'First session');
  const first = await open({ id: 1, url: firstUrl });
  extracted = article(secondUrl, 'Second session');
  const second = await open({ id: 2, url: secondUrl });
  const reopened = await open({ id: 2, url: secondUrl });

  assert.deepEqual(injections.map(({ target }) => target.tabId), [1, 2, 2]);
  assert.equal(first.session.text, 'First session');
  assert.equal(second.session.text, 'Second session');
  assert.notEqual(second.session.id, reopened.session.id);
  assert.deepEqual(Object.keys(first.session).sort(), [
    'candidateImages', 'extraction', 'id', 'tabId', 'text', 'title', 'url', 'version',
  ]);

  await closed(first.analysisId);
  assert.equal(sessions.has(sessionKey(first.session.id)), false);
  assert.equal(sessions.has(sessionKey(second.session.id)), true);
});

test('missing permissions and navigation during extraction switch to manual input', async () => {
  const count = injections.length;
  const restricted = await open({ id: 3, url: 'chrome://extensions/' });
  assert.equal(injections.length, count);
  assert.equal(restricted.session.extraction, 'unavailable');

  const url = 'https://page.example/original';
  extracted = article('https://page.example/after-navigation', 'Must not use this DOM');
  assert.equal((await open({ id: 4, url })).session.text, '');

  extracted = new Error('No host permission');
  const denied = await open({ id: 4, url });
  assert.equal(denied.session.extraction, 'unavailable');
  assert.equal(denied.session.text, '');
  assert.equal(await readSession('?session=invalid'), null);
});


test('failed or untrackable analysis tab creation leaves no orphan session', async () => {
  const original = chrome.tabs.create;
  const before = [...sessions.keys()].sort();
  try {
    chrome.tabs.create = async () => { throw Error('Cannot create analysis tab'); };
    assert.equal(await requestManualAnalysis({ id: 7, url: 'chrome://version/' }), false);
    assert.deepEqual([...sessions.keys()].sort(), before);

    chrome.tabs.create = async () => ({});
    await requestManualAnalysis({ id: 7, url: 'chrome://version/' });
    assert.deepEqual([...sessions.keys()].sort(), before);

    chrome.tabs.create = async tab => ({ ...tab, id: 999 });
    await requestManualAnalysis({ id: 7, url: 'chrome://version/' });
    assert.deepEqual([...sessions.keys()].sort(), before);
  } finally {
    chrome.tabs.create = original;
  }
});
