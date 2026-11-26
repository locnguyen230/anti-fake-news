# Extension tuần 1 · AFN-010 và AFN-011

## Chạy thử

Đóng gói, cài đặt và chạy popup hiện tại theo [hướng dẫn](extension-setup.md).
Mẫu bài và ảnh trong `tests/fixtures/pages` được tạo cho kiểm thử.

## Hợp đồng phiên của giao diện tuần 1

Trong giao diện tuần 1, thao tác bấm biểu tượng tiện ích kích hoạt worker tạo UUID
và truyền qua `analyze.html?session=<id>`. Trang đọc bản ghi `analysis:<id>` qua
`readSession(location.search)` trong `modules/session.js`. Schema v1 gồm các trường sau.

| Trường | Giá trị |
| --- | --- |
| `version`, `id`, `tabId` | Phiên bản DTO, UUID phiên và ID tab nguồn nếu có |
| `url` | URL HTTP(S) của tab nguồn, hoặc `null` |
| `title`, `text` | Tiêu đề và văn bản trích xuất |
| `candidateImages` | Tối đa 12 mục có `url` tuyệt đối và `label` |
| `extraction` | `dom` khi lấy được văn bản, `empty` khi không thấy thân bài, `unavailable` khi không đọc được tab |

Phiên được xóa khi đóng tab phân tích. Nội dung chỉnh sửa ở giao diện tuần 1 chỉ nằm trong trang đang mở. Nguồn và URL ứng viên được trình bày như văn bản. Bộ trích ưu tiên vùng bài, bỏ các khối điều hướng, quảng cáo đánh dấu bằng `aside`, chân trang và nội dung ẩn. Trang có cấu trúc khác có thể cần nhập tay.

## Bằng chứng cục bộ

| Issue | Kiểm thử đạt |
| --- | --- |
| [AFN-010](https://github.com/ngnsusinn/anti-fake-news/issues/10) | Mở từng phiên qua action, lặp lại trên cùng tab, tách phiên giữa các tab, từ chối DOM sau khi tab đổi URL, nhập tay trên tab bị giới hạn và xóa bản ghi khi đóng. |
| [AFN-011](https://github.com/ngnsusinn/anti-fake-news/issues/11) | Trích từ trang bài mẫu, lọc khối phụ, phân giải ảnh tương đối, xử lý trang rỗng và bắt được nội dung sau khi DOM động cập nhật. |

```powershell
node --test tests/frontend/session.test.mjs

$playwrightDir = Join-Path ([IO.Path]::GetTempPath()) 'afn-extension-playwright'
npm install --prefix $playwrightDir playwright --no-audit --no-fund
& (Join-Path $playwrightDir 'node_modules/.bin/playwright.cmd') install chromium
$env:AFN_PLAYWRIGHT_PATH = Join-Path $playwrightDir 'node_modules/playwright'
python scripts/test_extension_smoke.py
```

Browser smoke nạp gói tạm vào Chromium và dùng DevTools để kích hoạt popup.
[Tài liệu về thao tác kích hoạt action trong Chrome](https://chromedevtools.github.io/devtools-protocol/tot/Extensions/).

### Bàn giao phiên AFN-010

UI đọc DTO qua `readSession(location.search)`. Worker chỉ thu thập và giữ DTO theo UUID, còn file, token và request HTTP thuộc trang phân tích. Khi Chrome không tạo được tab hoặc tab đóng trước khi ghi xong ownership, worker dọn bản ghi. Các tab khác vẫn giữ phiên riêng.
