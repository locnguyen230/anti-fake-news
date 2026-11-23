# Kết nối Extension với Backend cục bộ — AFN-027

Trang phân tích có địa chỉ dịch vụ, token demo và thời gian chờ. Dùng
http://127.0.0.1:8000 hoặc đổi cổng theo Backend. Token nằm trong trường mật khẩu
của tab và được gửi bằng X-Demo-Token khi bấm **Phân tích**. Nút **Kiểm tra kết nối**
dùng GET /health và không gửi token. Thời gian chờ mặc định là 30 giây.

Mở hình ảnh hoặc tải tệp JPEG/PNG, nhập phần thân bài rồi bấm **Phân tích**. Trang
tạo UUID và gửi multipart để trình duyệt tự đặt boundary. Service worker không
gửi request. Tab giữ tệp trong bộ nhớ để thử lại.

Để phát triển nội bộ, xem [cách bật mock](dev-mock.md). Backend mock được đánh dấu
trên giao diện và có thể dùng token trống. Chế độ mặc định hiện trả 503 khi chưa
có model thật. Bàn giao từ v0.1.1 sang model thật theo #37/#38; giao diện kết quả
đầy đủ do #40 rà. Hợp đồng/tích hợp form-state tiếp tục theo #8/#12.
