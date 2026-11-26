# Kết nối Extension với Backend cục bộ — AFN-027

Script đóng gói lấy `AFN_DEMO_TOKEN` và `AFN_PORT` từ môi trường hoặc `.env`.
Popup dùng địa chỉ loopback `http://127.0.0.1:8000` theo mặc định và chờ tối đa
30 giây cho phản hồi. Khi bấm **Phân tích**, tiện ích gửi token qua `X-Demo-Token`.
Đóng gói lại sau khi đổi cổng hoặc token Backend.

Popup lấy nội dung từ tab đang xem và dùng ảnh JPEG/PNG đầu tiên tải được từ bài.
Điểm `fake_score` được hiển thị theo phần trăm cùng nhãn dự đoán của Backend.
Nếu trang thiếu văn bản hoặc ảnh phù hợp, popup hiển thị thông báo tương ứng.

Để phát triển nội bộ, xem [cách bật mock](dev-mock.md). Backend mock được đánh dấu
trên giao diện. Từ hợp đồng v0.2.0, cả chế độ mock và real đều yêu cầu token
trùng với `AFN_DEMO_TOKEN` của Backend. Token thiếu hoặc sai trả 401. Chế độ real
trả 503 nếu token và dữ liệu hợp lệ nhưng model chưa sẵn sàng. Bàn giao model thật
theo #37/#38; giao diện kết quả
ở module result-view chỉ nhận dữ liệu đã qua kiểm tra request. Bàn giao nội dung và review UI cuối ở #40. Hợp đồng và form-state tiếp tục được đối chiếu ở #8/#12.
