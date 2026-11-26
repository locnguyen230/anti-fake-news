function sourceUrl(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    url.username = '';
    url.password = '';
    return url.href;
  } catch {
    return null;
  }
}

export async function readArticle(tab) {
  const url = sourceUrl(tab?.url);
  const unavailable = { url, title: '', text: '', candidateImages: [], extraction: 'unavailable' };
  if (!url || !Number.isInteger(tab.id)) return unavailable;

  try {
    const [injection] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractArticle,
    });
    const article = injection?.result;
    if (article && sourceUrl(article.url) === url) return { ...article, url };
  } catch {
    // Restricted pages and closed or navigated tabs use manual entry.
  }
  return unavailable;
}

// Chrome serializes this function into the tab's isolated world.
export function extractArticle() {
  const publishers = [
    [['reuters.com'], [
      '[data-testid="article-body"]',
      '[class*="article-body__content__"]',
      '[itemprop~="articleBody"]',
      '[data-testid="Body"]',
      '.article-module__main__1N9VH',
      '[class*="article-module__main__"]',
      'main article',
      'article',
      'main',
    ]],
    [['cnn.com'], ['.article__content-container', '.article__content']],
    [['bbc.com', 'bbc.co.uk'], ['main article', '#main-content article', '[data-testid="article"]']],
    [['apnews.com'], ['.RichTextStoryBody', '[data-testid="article-body-content"]']],
    [['theguardian.com'], ['[data-gu-name="body"]', '#maincontent [itemprop~="articleBody"]']],
    [['aljazeera.com'], ['.wysiwyg', '.article-p-wrapper']],
    [['abcnews.com', 'abcnews.go.com'], ['[data-testid="prism-article-body"]', '.Article__Content']],
  ];
  const hostname = location.hostname.toLowerCase().replace(/\.$/u, '');
  const publisher = publishers.find(([domains]) =>
    domains.some(domain => hostname === domain || hostname.endsWith('.' + domain)));
  const reuters = publisher?.[0][0] === 'reuters.com';
  const proseSelectors = ['p', 'blockquote', '[data-testid="paragraph"]', '[data-testid^="paragraph-"]'];
  const excludedSelectors = [
    'nav', 'aside', 'footer', 'script', 'style', 'template', 'noscript', 'figcaption',
    '[hidden]', '[aria-hidden="true"]', '[role="navigation"]', '[role="complementary"]',
    '.related-articles', '.related-content', '.related-links', '.read-more', '.advertisement',
    '.sidebar', '.newsletter', '.newsletter-signup', '.ad-slot', '.author-bio', '.byline',
    '[data-testid^="ad-"]', '[data-testid="related-topics"]', '[data-component="links-block"]',
  ];
  if (reuters) {
    proseSelectors.push('[class*="article-body__paragraph__"]');
    excludedSelectors.push(
      '[data-testid*="newsletter" i]', '[class*="newsletter-signup" i]',
      '[data-testid^="author-" i]', '[class*="author-bio" i]', '[class*="author-card" i]',
    );
  }
  const EXCLUDED = excludedSelectors.join(', ');
  const PROSE = proseSelectors.join(', ');
  const BLOCK = PROSE + ', h2, h3';
  const MAX_TEXT = 100_002;

  function visible(element) {
    if (element.closest(EXCLUDED) || !element.getClientRects().length
        || getComputedStyle(element).visibility !== 'visible') return false;
    for (let current = element; current; current = current.parentElement) {
      if (getComputedStyle(current).contentVisibility === 'hidden') return false;
    }
    return true;
  }

  function cleanText(element) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
          return getComputedStyle(node.parentElement).visibility === 'visible'
            ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
        const style = getComputedStyle(node);
        if (node.matches(EXCLUDED) || style.display === 'none' || style.contentVisibility === 'hidden') {
          return NodeFilter.FILTER_REJECT;
        }
        if (node.matches('br') && style.visibility === 'visible') return NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_SKIP;
      },
    });
    const text = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      text.push(node.nodeType === Node.TEXT_NODE ? node.data : ' ');
    }
    return text.join('').replace(/\s+/gu, ' ').trim();
  }

  const blockText = new WeakMap();
  function readBlock(block) {
    if (blockText.has(block)) return blockText.get(block);
    let text = '';
    if (visible(block) && !block.querySelector(BLOCK)) {
      text = cleanText(block);
      const linkedLength = [...block.querySelectorAll('a[href]')]
        .reduce((length, link) => length + cleanText(link).length, 0);
      if (linkedLength && linkedLength >= text.length * 0.65) text = '';
      if (reuters && /\bnewsletter\b/iu.test(text) && /\b(?:sign up|subscribe)(?: here| now)?\.?$/iu.test(text)) {
        text = '';
      }
    }
    blockText.set(block, text);
    return text;
  }

  function readContent(scope) {
    const paragraphs = [];
    let textLength = 0;
    let proseLength = 0;
    const blocks = scope.matches(BLOCK) ? [scope] : scope.querySelectorAll(BLOCK);
    for (const block of blocks) {
      const content = readBlock(block);
      if (!content) continue;
      if (reuters && /^(?:\(?(?:(?:additional )?reporting|writing|editing) by\b|Thomson Reuters\.?$|Our Standards:\s+The Thomson Reuters Trust Principles\b)/iu.test(content)) {
        break;
      }
      const part = content.slice(0, MAX_TEXT - textLength);
      paragraphs.push(part);
      if (block.matches(PROSE)) proseLength += part.length;
      textLength += part.length + 2;
      if (textLength >= MAX_TEXT) break;
    }
    return { scope, paragraphs, proseLength };
  }

  function bestContent(scopes) {
    let best;
    for (const scope of scopes) {
      if (!visible(scope)) continue;
      const result = readContent(scope);
      if (!result.proseLength) continue;
      if (!best || result.proseLength > best.proseLength
          || (result.proseLength === best.proseLength && best.scope.contains(scope))) best = result;
    }
    return best;
  }

  function findContent() {
    for (const selector of publisher?.[1] ?? []) {
      const result = bestContent(document.querySelectorAll(selector));
      if (result) return result;
    }
    // Reuters page furniture can be longer than the article. Avoid scoring its footer as a body.
    if (reuters) return undefined;
    const structured = bestContent(document.querySelectorAll('[itemprop~="articleBody"]'));
    if (structured) return structured;
    const marked = bestContent(document.querySelectorAll(
      '[data-testid="article-body"], .article-body, .article-content, .entry-content, .post-content',
    ));
    if (marked) return marked;
    const semantic = bestContent(document.querySelectorAll('article'));
    if (semantic) return semantic;

    const main = [...document.querySelectorAll('main, [role="main"]')].find(visible);
    const parent = main ?? document.body;
    const groups = new Set();
    for (const block of parent?.querySelectorAll(PROSE) ?? []) {
      if (!readBlock(block)) continue;
      const container = block.parentElement;
      if (container !== parent) groups.add(container);
      if (container.parentElement !== parent && container !== parent) groups.add(container.parentElement);
      if (groups.size >= 100) break;
    }
    return bestContent(groups) ?? (parent ? bestContent([parent]) : undefined);
  }

  // Article-specific metadata supplements the rendered body and excludes publisher logos.
  function articleMetadata() {
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      if (script.textContent.length > 1_000_000) continue;
      let data;
      try { data = JSON.parse(script.textContent); } catch { continue; }
      const entries = [data];
      for (let index = 0; index < entries.length && index < 100; index++) {
        const entry = entries[index];
        if (Array.isArray(entry)) {
          entries.push(...entry.slice(0, 100));
        } else if (entry && typeof entry === 'object') {
          if ([entry['@type']].flat().some(type =>
            typeof type === 'string' && /(?:Article|BlogPosting)$/u.test(type))) return entry;
          entries.push(entry['@graph'], entry.mainEntity);
        }
      }
    }
    return null;
  }

  const content = findContent();
  const scope = content?.scope;
  const article = scope?.closest('article');
  const meta = articleMetadata();
  const headings = (article ?? scope?.closest('main, [role="main"]') ?? scope)?.querySelectorAll('h1') ?? [];
  const heading = [...headings].find(visible);
  const metaTitle = document.querySelector('meta[property="og:title"]')?.content;
  const title = ((heading && cleanText(heading)) || (typeof meta?.headline === 'string' && meta.headline.trim())
    || metaTitle?.trim() || document.title.trim()).slice(0, 4096);
  const text = content?.paragraphs.join('\n\n') ?? '';
  const candidates = new Map();

  function addImage(value, label) {
    if (typeof value !== 'string' || !value.trim() || candidates.size >= 12) return;
    try {
      const url = new URL(value, document.baseURI);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return;
      if (/(?:^|[/_\-.])(?:logo|favicon|avatar|tracking|spacer|placeholder)(?:[/_\-.]|$)/iu.test(url.pathname)
          || /\.svg$/iu.test(url.pathname)) return;
      url.hash = '';
      if (url.href.length <= 2048 && !candidates.has(url.href)) {
        candidates.set(url.href, { url: url.href, label: label?.trim().slice(0, 160) || '' });
      }
    } catch {
      // Invalid URLs are ignored.
    }
  }

  function addSrcset(value, label) {
    if (!value) return;
    const entries = [...value.matchAll(/(?:^|,\s*)(\S+?)\s+(\d+(?:\.\d+)?)[wx](?=\s*,|\s*$)/gu)];
    if (!entries.length) {
      if (!/\s/u.test(value.trim())) addImage(value, label);
      return;
    }
    entries.sort((first, second) => Math.abs(Number(first[2]) - 1200) - Math.abs(Number(second[2]) - 1200));
    addImage(entries[0][1], label);
  }

  function addElementImage(image) {
    if (!visible(image)) return;
    const tooSmall = image.complete && image.naturalWidth > 0
      && Math.min(image.naturalWidth, image.naturalHeight) < 32;
    if (!tooSmall) addImage(image.currentSrc, image.alt);
    addImage(image.getAttribute('data-src'), image.alt);
    addImage(image.getAttribute('data-lazy-src'), image.alt);
    for (const source of image.closest('picture')?.querySelectorAll('source[type="image/jpeg"], source[type="image/png"]') ?? []) {
      addSrcset(source.getAttribute('srcset') ?? source.getAttribute('data-srcset'), image.alt);
    }
    addSrcset(image.getAttribute('data-srcset'), image.alt);
    addSrcset(image.getAttribute('srcset'), image.alt);
    if (!tooSmall) addImage(image.getAttribute('src'), image.alt);
  }

  const coverLabel = 'Ảnh đại diện bài viết';
  for (const image of [meta?.image].flat().slice(0, 3)) {
    if (typeof image === 'string') addImage(image, coverLabel);
    else {
      addImage(image?.contentUrl, coverLabel);
      addImage(image?.url, coverLabel);
    }
  }
  for (const selector of [
    'meta[property="og:image:secure_url"]', 'meta[property="og:image"]',
    'meta[name="twitter:image"], meta[name="twitter:image:src"]',
  ]) {
    for (const tag of [...document.querySelectorAll(selector)].slice(0, 2)) {
      addImage(tag.content, coverLabel);
    }
  }
  const images = article ?? scope;
  function addImages(container, selector) {
    for (const image of container?.querySelectorAll(selector) ?? []) {
      if (candidates.size === 12) break;
      addElementImage(image);
    }
  }
  addImages(images, '[itemprop~="image"] img, img[itemprop~="image"], header img');
  const wrapper = images?.parentElement;
  if (wrapper && !wrapper.matches('body, html')) {
    addImages(wrapper, ':scope > header img, :scope > figure img');
  }
  addImages(images, 'figure img');
  addImages(images, 'img');

  return {
    url: location.href,
    title,
    text,
    candidateImages: [...candidates.values()],
    extraction: text ? 'dom' : 'empty',
  };
}
