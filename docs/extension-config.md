# Kết nối Extension với Backend cục bộ — AFN-027

Mở **Kết nối Backend** trong popup để nhập địa chỉ dịch vụ, token demo và thời gian
chờ. Dùng `http://127.0.0.1:8000` hoặc đổi cổng theo Backend. Khi bấm **Phân tích**,
tiện ích lưu cấu hình trong phiên trình duyệt và gửi token qua `X-Demo-Token`.
Thời gian chờ mặc định là 30 giây.

Popup lấy nội dung từ tab đang xem và dùng ảnh JPEG/PNG đầu tiên tải được từ bài.
Điểm `fake_score` được hiển thị theo phần trăm cùng nhãn dự đoán của Backend.
Dùng **Phân tích thủ công** để sửa nội dung, tải ảnh lên hoặc gọi `GET /health`
qua nút **Kiểm tra kết nối**. Trang thủ công giữ tệp trong bộ nhớ để thử lại.

Để phát triển nội bộ, xem [cách bật mock](dev-mock.md). Backend mock được đánh dấu
trên giao diện. Từ hợp đồng v0.2.0, cả chế độ mock và real đều yêu cầu nhập token
trùng với `AFN_DEMO_TOKEN` của Backend. Token thiếu hoặc sai trả 401. Chế độ real
trả 503 nếu token và dữ liệu hợp lệ nhưng model chưa sẵn sàng. Bàn giao model thật
theo #37/#38; giao diện kết quả
ở module result-view chỉ nhận dữ liệu đã qua kiểm tra request. Bàn giao nội dung và review UI cuối ở #40. Hợp đồng và form-state tiếp tục được đối chiếu ở #8/#12.
