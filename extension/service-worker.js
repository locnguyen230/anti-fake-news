import { readArticle } from './extract.js';
import { SESSION_VERSION, sessionKey } from './modules/session.js';

async function openAnalysis(tab) {
  const id = crypto.randomUUID();
  const key = sessionKey(id);
  const session = {
    version: SESSION_VERSION,
    id,
    tabId: tab?.id ?? null,
    ...await readArticle(tab),
  };

  let stored = false;
  try {
    await chrome.storage.session.set({ [key]: session });
    stored = true;
  } catch {
    // The analysis page can continue with manual entry if storage is unavailable.
  }
  const page = new URL(chrome.runtime.getURL('analyze.html'));
  if (stored) page.searchParams.set('session', id);
  try {
    const analysisTab = await chrome.tabs.create({ url: page.href });
    if (!stored) return;
    if (!Number.isInteger(analysisTab.id)) {
      await chrome.storage.session.remove(key);
      return;
    }
    // Keep ownership in session storage so removal works after worker suspension.
    await chrome.storage.session.set({ ['analysis-tab:' + analysisTab.id]: key });
    try {
      await chrome.tabs.get(analysisTab.id);
    } catch {
      await removeAnalysis(analysisTab.id);
    }
  } catch {
    if (stored) await chrome.storage.session.remove(key);
    throw Error('Could not open the analysis tab');
  }
}

async function removeAnalysis(tabId) {
  const ownerKey = 'analysis-tab:' + tabId;
  const key = (await chrome.storage.session.get(ownerKey))[ownerKey];
  if (key) await chrome.storage.session.remove([ownerKey, key]);
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.url !== chrome.runtime.getURL('popup.html') || message?.type !== 'open-manual-analysis') return;

  const source = Number.isInteger(message.tabId)
    ? chrome.tabs.get(message.tabId).catch(() => null)
    : Promise.resolve(null);
  source.then(openAnalysis).then(() => respond(true), () => respond(false));
  return true;
});
chrome.tabs.onRemoved.addListener(tabId => removeAnalysis(tabId).catch(() => {}));
