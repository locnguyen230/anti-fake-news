# Kết nối Extension với Backend cục bộ — AFN-027

Script đóng gói lấy `AFN_DEMO_TOKEN` và `AFN_PORT` từ môi trường hoặc `.env`.
Popup dùng địa chỉ loopback `http://127.0.0.1:8000` theo mặc định và chờ tối đa
30 giây cho phản hồi. Khi bấm **Phân tích**, tiện ích gửi token qua `X-Demo-Token`.
Đóng gói lại sau khi đổi cổng hoặc token Backend.

Popup ưu tiên bố cục riêng của Reuters, CNN, BBC News, AP News, The Guardian,
Al Jazeera và ABC News. Với các trang khác, popup tìm vùng thân bài theo
markup HTML và các nhóm đoạn văn hiển thị, lọc menu và vùng liên kết phụ.
Với Reuters, bộ trích xuất đọc cả các đoạn được đánh dấu bằng
`data-testid="paragraph-…"` và dừng ở dòng ghi công. Trang chỉ hiện newsletter
hoặc tiểu sử tác giả sẽ báo thiếu nội dung.

Popup ưu tiên ảnh đại diện từ JSON-LD và Open Graph, rồi thử ảnh đầu bài
và ảnh trong thân bài, kể cả ảnh khai báo qua `srcset` hoặc tải trễ. Ảnh gửi
đi là ảnh JPEG/PNG hợp lệ đầu tiên tải được.
Điểm `fake_score` được hiển thị theo phần trăm cùng nhãn dự đoán của Backend.
Nếu trang thiếu văn bản hoặc ảnh phù hợp, popup hiển thị thông báo tương ứng.

Để phát triển nội bộ, xem [cách bật mock](dev-mock.md). Backend mock được đánh dấu
trên giao diện. Từ hợp đồng v0.2.0, cả chế độ mock và real đều yêu cầu token
trùng với `AFN_DEMO_TOKEN` của Backend. Token thiếu hoặc sai trả 401. Chế độ real
trả 503 nếu token và dữ liệu hợp lệ nhưng model chưa sẵn sàng. Bàn giao model thật
theo #37/#38; giao diện kết quả
ở module result-view chỉ nhận dữ liệu đã qua kiểm tra request. Bàn giao nội dung và review UI cuối ở #40. Hợp đồng và form-state tiếp tục được đối chiếu ở #8/#12.
