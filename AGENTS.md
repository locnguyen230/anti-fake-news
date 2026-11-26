# Hướng dẫn Codex

## Công cụ

- Không sử dụng skill `computer-use:computer-use` (Computer Use). Ưu tiên SSH, CLI, API hoặc công cụ tích hợp phù hợp.

## Quy trình Git

- Với mọi yêu cầu liên quan đến repository Git, kể cả chỉ hỏi thông tin, fetch remote, xác định nhánh đang làm việc hoặc nhánh đích và đối chiếu HEAD với upstream.
- Trước khi phân tích, sửa hoặc kiểm thử, đồng bộ upstream của nhánh bằng fast-forward nếu HEAD đi sau, rồi merge bản mới nhất của `origin/main` vào nhánh làm việc hiện tại. Kiểm tra lại remote trước khi hoàn tất nếu remote có thể đã thay đổi.
- Giữ nguyên thay đổi cục bộ và commit chưa push. Khi checkout hiện tại không thể đồng bộ an toàn, dùng checkout sạch từ bản mới nhất của nhánh đích hoặc `origin/main` và báo rõ tình trạng. Tránh reset, ghi đè thay đổi hoặc force-push để đồng bộ.
- Khi hoàn tất thay đổi, commit và push nhánh làm việc rồi tự động mở pull request vào `main`. Nếu nhánh đã có pull request mở vào `main`, cập nhật pull request đó.

## Kiểm thử và QA

- Chỉ kiểm thử dịch vụ, luồng và tính năng bị ảnh hưởng trực tiếp hoặc mới được thêm. Giới hạn kiểm thử hồi quy ở các điểm tích hợp liên quan, không chạy QA toàn hệ thống.
