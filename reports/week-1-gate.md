# Báo cáo kiểm tra điều kiện cuối tuần 1 — AFN-015

**Thời điểm:** 23/11/2026, giờ Việt Nam.

**Quyết định sơ bộ: TIẾP TỤC CÓ ĐIỀU KIỆN — CHƯA KÝ NGHIỆM THU.** Các việc tuần 2 không bị phụ thuộc có thể bắt đầu; chưa đủ căn cứ đánh dấu checkpoint tuần 1 Done.

## 1. Kiểm tra đầu vào

| Điều kiện kiểm tra | Bằng chứng/trạng thái quan sát | Nhận định |
| --- | --- | --- |
| Pilot ≥30 URL và tỷ lệ khôi phục cả bài lẫn ảnh | #2/#3 theo dõi; báo cáo này chưa kiểm chứng số liệu cụ thể | Chờ DATA cung cấp log và kết quả, không tự đặt số mẫu |
| Mục tiêu 200–500 mẫu hợp lệ; nhãn/nhóm, lý do ảnh thiếu | DEFINE nêu mục tiêu; #3 vẫn mở dù checklist đã tích | Chờ manifest, checksum và đối chiếu số lượng |
| Ba cấu hình, quy tắc chọn bằng Validation | DESIGN §4 có ba cấu hình; #4 vẫn mở | Chờ giao thức được phê duyệt |
| CLIP ViT-B/32 chạy CPU, RAM, số chiều | #6 còn mở | Chờ đo thật trên máy demo |
| Hợp đồng API và Extension | `api-contract.md` / `inference-interface.md` v0.1.1 là bản đề xuất; #8 cảnh báo kiểm tra lại | Chờ Backend/ML/Extension đồng ý |
| Backend scaffold | README mô tả FastAPI local; health chưa sẵn sàng, real `/predict` trả 503; mock phải bật rõ ràng | Đã có khung, **không** chứng minh suy luận thật |
| Extension smoke | #10/#11 vẫn mở; PR #65 đang mở tại thời điểm rà soát | Cần review và chạy browser smoke thực |
| Quy trình/ma trận QA | Đã soạn `docs/working-agreement.md`, `docs/test-plan.md`, `tests/fixtures/README.md` | Chờ DATA review và CODEOWNER duyệt |

## 2. Các bước xác minh cần thực hiện tiếp

1. Trên checkout đã cài dependency: vào `backend`, chạy `python -m pytest -q`, ghi **đúng số bài pass/fail**, phiên bản Python và commit SHA.
2. Từ thư mục `backend`, chạy `python tests/smoke_local.py` với môi trường riêng; chỉ dùng chế độ mock tường minh để phát triển hợp đồng. Ghi chính xác `/health` 200 và `/predict` real-mode 503 với ý nghĩa thật của chúng.
3. Sau khi review PR #65, chạy smoke Extension trên phiên bản commit được chọn: kiểm tra phiên theo tab, ảnh tương đối và nhập thủ công.
4. DATA bàn giao số đầu vào, hợp lệ, loại, chờ xử lý, lý do thiếu, nguồn/quyền và checksum manifest. Kiểm tra `tổng đầu vào = hợp lệ + bị loại + chờ xử lý`.
5. ML bàn giao checkpoint/revision và đo CLIP frozen trên CPU: số chiều embedding, thời gian nạp, mức RAM và phiên bản môi trường.

**Các lệnh trên là việc cần chạy trong bước nghiệm thu, không phải lời khẳng định đã chạy ở báo cáo này.** Chưa có số liệu đo thực tế nào được tự điền.

## 3. Quyết định checkpoint

- **No Go đối với nghiệm thu hoàn tất tuần 1 hoặc demo mô hình thật**: chưa đủ bằng chứng đáng tin cậy để kết luận đạt 30 URL, 200 mẫu, CLIP CPU hoặc API đã ký duyệt.
- **Conditional Go cho các việc độc lập tuần 2**: tiếp tục kiểm tra schema/fixture, test hợp đồng tổng hợp, UX Extension và validator chia tập. Không tự mở Test hoặc thay đổi contract chưa duyệt.
- **Blocker cần xử lý:** DATA `locnguyen230` (#2/#3), INTEGRATION `fulord26` (#4), ML `0xDa1Vu` (#6), BACKEND `Phuc1232` phối hợp ML/EXTENSION (#8), EXTENSION `ngnsusinn` (#10/#11), QA `dangnguyen0512` và owner (#13). Xem [sổ rủi ro](../docs/risk-register.md).
- **Phê duyệt bắt buộc:** reviewer DATA và CODEOWNER `@ngnsusinn`. Chỉ ký checkpoint và đánh dấu #15 Done khi có URL bằng chứng thực, quyết định, ngày giờ và những giới hạn còn lại.

Nguồn đối chiếu: [DEFINE](../DEFINE.md), [DESIGN](../DESIGN.md), [hợp đồng API](../docs/api-contract.md), [Issue #15](https://github.com/ngnsusinn/anti-fake-news/issues/15).
