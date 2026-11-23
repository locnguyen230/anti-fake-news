import { bindFormValidation } from './modules/form-validation.js';
import { createImageSelection } from './modules/image-selection.js';
import { readSession } from './modules/session.js';

const get = id => document.getElementById(id);
const session = await readSession(location.search).catch(() => null);
const extractionMessages = {
  dom: 'Rà lại văn bản đã lấy từ trang. Bạn có thể chỉnh sửa bên dưới.',
  empty: 'Chưa tìm thấy nội dung bài viết. Bạn có thể nhập hoặc dán văn bản, hoặc mở lại tiện ích khi bài đã tải xong.',
  unavailable: 'Không đọc được tab nguồn. Bạn có thể nhập hoặc dán văn bản bên dưới.',
};

get('extraction').textContent = extractionMessages[session?.extraction]
  ?? 'Chưa có phiên nguồn. Bạn có thể nhập hoặc dán văn bản bên dưới.';

if (session?.url) {
  const source = get('source');
  source.textContent = 'Nguồn: ' + session.url;
  source.hidden = false;
}
get('title').value = session?.title ?? '';
get('text').value = session?.text ?? '';

const upload = get('image-upload');
const preview = get('image-preview');
const removeImage = get('remove-image');
const imageSelection = createImageSelection(({ file, preview: url, message }) => {
  get('image-status').textContent = message;
  preview.hidden = !file;
  removeImage.hidden = !file;
  if (url) preview.src = url;
  else preview.removeAttribute('src');
  formState.changed();
});

const formState = bindFormValidation(get('analysis-form'), {
  title: get('title'), text: get('text'), image: upload,
  getImage: () => imageSelection.file, feedback: get('form-status'),
});

upload.addEventListener('change', () => imageSelection.chooseFile(upload.files[0]));
removeImage.addEventListener('click', () => {
  upload.value = '';
  imageSelection.clear();
  upload.focus();
});
addEventListener('pagehide', () => {
  upload.value = '';
  imageSelection.clear();
});

const candidates = session?.candidateImages ?? [];
if (candidates.length) {
  const list = get('candidates');
  for (const { url, label } of candidates) {
    const item = document.createElement('li');
    const choose = document.createElement('button');
    choose.type = 'button';
    choose.textContent = label ? label + ' · ' + url : url;
    choose.addEventListener('click', () => {
      upload.value = '';
      imageSelection.chooseCandidate(url, session?.url);
    });
    item.append(choose);
    list.append(item);
  }
  get('image-candidates').hidden = false;
}
get('draft').disabled = false;
