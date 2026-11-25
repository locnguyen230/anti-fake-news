# AFN-030 · Kết quả Extension với mock

Ngày 25/11/2026, Windows x64, Chromium unpacked (`Chrome/159.0.8154.6`),
Node.js 26.13.1, Python 3.13, API v0.2.0. Chạy trên bản thay đổi AFN-012/024/030
từ `main@976c912`. Browser smoke dùng trang/ảnh tổng hợp, hai API loopback
và token tạm cho phiên chạy.

| Ca | Kết quả và bằng chứng |
| --- | --- |
| T01 · Đúng tab | PASS. Mở từ action trên nhiều tab và xác nhận session riêng. Đóng trang phân tích dọn đúng session. |
| T02 · Trích xuất và nhập tay | PASS. Trang tĩnh và động, bỏ DOM ẩn, ảnh đường dẫn tương đối. DOM rỗng và tab bị giới hạn vẫn nhập được. |
| T03 · Chọn ảnh | PASS. Chọn từ trang, lỗi tải ảnh, upload PNG, preview và bỏ ảnh. Snapshot `storage.session` không đổi sau khi chọn tệp và chỉnh bản nhập. |
| T04 · Sửa bản nhập | PASS. Validation giữ bản nhập và chuyển focus tới trường lỗi. Sửa nội dung sau HTTP 200 giữ bản nhập/ảnh và hiển thị cảnh báo kết quả cũ. Kết quả mới bỏ cảnh báo. |
| T05 · Giới hạn ảnh tại Extension | PASS. Từ chối ảnh vượt trần byte hoặc pixel. Giới hạn transport và ảnh tại Backend có bằng chứng ở [PR #94](https://github.com/ngnsusinn/anti-fake-news/pull/94). |
| T06 · Multipart | PASS. FastAPI mock nhận request, trả HTTP 200 với đúng UUID và UI gắn nhãn giả lập. Test API client kiểm tra tên các part và boundary do trình duyệt tạo. |
| Lỗi và thử lại | PASS. 401 khi thiếu token, 503 khi provider chưa sẵn sàng, giữ text/ảnh, thử lại sau khi sửa token. Phản hồi trễ hoặc sai UUID không ghi đè kết quả hợp lệ. |

```sh
node --test tests/frontend/form-validation.test.mjs tests/frontend/session.test.mjs tests/frontend/image-selection.test.mjs tests/frontend/result-view.test.mjs tests/frontend/request-lifecycle.test.mjs tests/frontend/error-recovery.test.mjs tests/frontend/api-client.test.mjs
python scripts/test_extension_smoke.py
```

Kết quả ngày 25/11 là **20/20 test JavaScript và 13 ca browser smoke đạt**.
Cách thiết lập runner ở [Extension tuần 1](../docs/extension-w1.md).
Các việc chuyển sang tuần 3 ở [checkpoint](week-2-gate.md).
