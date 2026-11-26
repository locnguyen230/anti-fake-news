# Báo cáo kiểm thử hợp đồng API — AFN-028

**Nguồn kiểm tra lại:** `main` tại `180384b`.
**Người phụ trách:** `dangnguyen0512` (QA).
**Hợp đồng:** [API v0.2.0](../docs/api-contract.md).
**Môi trường:** Windows, Python 3.13.0, cấu hình kiểm thử độc lập với biến triển khai Backend.

## 1. Kết quả chạy thực tế

| Lệnh | Kết quả |
| --- | --- |
| `python -m unittest discover -s tests -p test_api_contract.py -v` | **13/13 PASS** với `main` tại `180384b` |
| `cd backend && python -m pytest -q` | 184/184 PASS trong lượt kiểm thử lịch sử trên Linux tại `976c912` |

Các bài test QA dùng ảnh/văn bản **tự tạo** và token **chỉ dùng trong kiểm thử**. Thành công 200 là **mock được bật tường minh** (`AFN_ENVIRONMENT=test`, `AFN_PREDICTOR_MODE=mock`), không phải suy luận mô hình thật.

## 2. Ma trận bằng chứng

| Nhóm | Ca kiểm tra QA | Kết quả |
| --- | --- | --- |
| Health/real-mode | Health 200, `model_ready=false`, contract 0.2.0, cache no-store | PASS |
| Mock hợp lệ | 200, UUID chuẩn, score hợp lệ, `model_id=dev-mock-not-a-model`, không có header ngưỡng model thật | PASS (mock) |
| Model chưa sẵn sàng | Real mode nhận input hợp lệ rồi trả 503, echo UUID | PASS |
| Xác thực | Thiếu/sai token trả 401 trước khi parse body; server chưa cấu hình token từ chối | PASS |
| UUID và trường bắt buộc | UUID sai/thiếu, text thiếu trả 400; giữ UUID nếu đã parse an toàn | PASS |
| Giới hạn văn bản | text rỗng, text 50.000/50.001, title 500/501 code points | PASS |
| Multipart | JSON body, multipart sai dạng, trường lạ hoặc trùng | PASS |
| Ảnh | Thiếu ảnh, ảnh hỏng, MIME không khớp, MIME text/plain | PASS |
| Giới hạn ảnh | File vượt 10 MiB trả 413 | PASS |
| EXIF | JPEG synthetic orientation=6 được parser chấp nhận ở mock | PASS (mock) |
| 401 so với 403 | Token sai trả 401; không đòi 403 khi chưa có policy | PASS |

Các ca giới hạn toàn body, thiếu/giả Content-Length, parser stream, pixel/bomb và cleanup spool còn được kiểm tra trong bộ regression Backend (`backend/tests/test_request_limits.py`, `backend/tests/test_image_validation.py`) đã chạy PASS; test QA mới không tuyên bố chạy lặp riêng từng biến thể đó.

## 3. Sai lệch và giới hạn

- **Không phát hiện lỗi trong các ca API v0.2.0 đã chạy.** Lần chạy đầu có 2 ca QA FAIL vì chính test chưa gắn token cho request JSON và giả định UUID vẫn được parse ở request thiếu ảnh nhưng gửi form-urlencoded. Đã điều chỉnh test cho đúng thứ tự xác thực/header, sau đó 13/13 PASS.
- **Suy luận thật:** bộ test contract kiểm tra 503 khi chạy chế độ real mà chưa nạp model. Nghiệm thu với bundle và cấu hình bàn giao vẫn cần lượt chạy riêng.
- **BLOCKED — xác nhận liên vai trò:** API v0.2.0 chưa có phê duyệt cuối của ML và Extension theo tài liệu; cần review trước nghiệm thu #28.
- **Máy demo:** kết quả Windows trên máy phát triển cần được đối chiếu trên cấu hình bàn giao.
- **Không có 403 bắt buộc**: hợp đồng hiện chưa thiết lập chính sách phân biệt bị cấm sau xác thực.

## 4. Bàn giao và bước tiếp theo

1. DATA (`locnguyen230`) review chuyên môn QA, CODEOWNER (`ngnsusinn`) duyệt PR.
2. Backend (`Phuc1232`) và Extension/ML xác nhận contract v0.2.0; nếu đổi phiên bản, cập nhật test/fixture và chạy lại.
3. Sau #22/#23 được nghiệm thu và thử nghiệm trên cấu hình nhóm, bổ sung URL/log evidence (đã loại bỏ bí mật), ghi PASS/BLOCKED cho từng điều kiện cuối.
4. Giữ Issue #28 **Open** đến khi đáp ứng các điều kiện nghiệm thu và được review, không tự đóng vì có 13 bài test PASS.

Các tệp bàn giao: `tests/test_api_contract.py`, `reports/api-contract-results.md`.
