export function validateDraft({ title, text, image }) {
  const errors = {};
  if (Array.from(title).length > 500) errors.title = 'Tiêu đề được tối đa 500 ký tự.';
  if (!text.trim()) errors.text = 'Nhập nội dung bài viết.';
  else if (Array.from(text).length > 50_000) errors.text = 'Nội dung được tối đa 50.000 ký tự.';
  if (!image) errors.image = 'Chọn một ảnh JPEG hoặc PNG trước khi phân tích.';
  return errors;
}

export function bindFormValidation(form, { title, text, image, getImage, feedback }) {
  const fields = { title, text, image };
  let attempted = false;
  const get = () => ({ title: title.value, text: text.value, image: getImage() });

  function refresh() {
    const errors = attempted ? validateDraft(get()) : {};
    for (const [key, field] of Object.entries(fields)) {
      field.setAttribute('aria-invalid', String(Boolean(errors[key])));
    }
    feedback.textContent = Object.values(errors).join(' ');
    return errors;
  }

  function changed() {
    refresh();
    form.dispatchEvent(new Event('afn:draft-change'));
  }

  title.addEventListener('input', changed);
  text.addEventListener('input', changed);
  form.addEventListener('submit', event => {
    event.preventDefault();
    attempted = true;
    const errors = refresh();
    const first = Object.keys(errors)[0];
    if (first) {
      fields[first].focus();
      return;
    }
    form.dispatchEvent(new CustomEvent('afn:analyze', { detail: get() }));
  });
  return { get, changed };
}
