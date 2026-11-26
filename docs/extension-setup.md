# Cài Extension unpacked — AFN-057

## Đóng gói và cài đặt

1. Từ gốc repo, chạy `python scripts/package_extension.py`. Gói được tạo ở
   `release/extension`. Sau khi cập nhật mã, có thể dùng
   `python scripts/package_extension.py --output release/extension-next`.
2. Mở `chrome://extensions`, bật **Developer mode**, chọn **Load unpacked**,
   rồi chọn thư mục đã tạo. Ghi lại ID hiển thị bên dưới tiện ích.
3. Origin của gói là `chrome-extension://<ID>`. Dùng giá trị này cho
   `AFN_EXTENSION_ORIGIN` trong cấu hình Backend khi hỗ trợ CORS của #38 đã có.
   Khởi động Backend tại `127.0.0.1`.
4. Mở một bài viết, bấm biểu tượng **Anti Fake News**, rồi mở **Kết nối Backend**
   để nhập địa chỉ và token demo. Bấm **Phân tích** để xem điểm `fake_score`
   theo phần trăm và nhãn **Fake** hoặc **Real**.
5. Dùng **Phân tích thủ công** để chỉnh văn bản, chọn ảnh hoặc **Kiểm tra kết nối**.
   Chỉ demo suy luận thật khi
   Backend chạy mode real, đã nạp artifact đã khóa và trả `model_ready=true`.

Gói chỉ lấy mã MV3 và tệp giao diện trong danh sách runtime của script đóng gói.
Xem [kết nối API](extension-config.md) và
[kịch bản demo](demo-script.md). Phát hành theo mô hình unpacked của dự án.

## Kiểm tra trên máy khác

Sau khi cài dependencies Backend và Playwright theo
[hướng dẫn Chromium](extension-w1.md), có thể kiểm tra gói vừa đóng:

```powershell
$env:AFN_EXTENSION_UNPACKED = (Resolve-Path release/extension).Path
python scripts/test_extension_smoke.py
```

Lệnh trên kiểm tra Chromium, FastAPI mock và luồng real-mode 503 với token
thử nghiệm do runner tạo. Rehearsal
với mô hình đã khóa dùng gói Backend #54 và lệnh ở
[biên bản hồi quy](../reports/extension-final-check.md).
