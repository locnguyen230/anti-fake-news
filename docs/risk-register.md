# Sổ theo dõi rủi ro — AFN-015

Cập nhật ngày 23/11/2026. “Chưa có bằng chứng” nghĩa là **chưa xác minh được trên nhánh mặc định và các issue tại thời điểm kiểm tra**, không khẳng định thành viên chưa làm ở máy/nhánh khác. Hạn xử lý phải được nhóm xác nhận.

| Mã | Rủi ro / khoảng trống đã nhận diện | Mức độ | Người gỡ / issue | Hướng xử lý | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| R01 | Chưa xác minh độc lập số bài khôi phục được, ảnh hợp lệ và quyền sử dụng; #3 đã tích checklist nhưng vẫn mở | Cao | DATA `locnguyen230`, #2/#3 | Nộp manifest, checksum, báo cáo số lượng và giấy phép để QA đối chiếu | Chờ evidence |
| R02 | Chưa xác nhận đủ nhóm độc lập và chia 70/15/15 | Cao | DATA `locnguyen230`, #3/#18 | Nộp group key, checksum split; kiểm tra rò rỉ trước khi Train/Test | Chặn nghiệm thu |
| R03 | Chưa thấy cấu hình/chính sách chọn mô hình đã duyệt trên nhánh mặc định | Cao | INTEGRATION `fulord26`, #4 | Chốt seed 42, C/ngưỡng bằng Validation, cấm xem Test trước khóa | Đang mở |
| R04 | Chưa có số đo CLIP CPU, revision/processor, số chiều embedding, thời gian và RAM | Cao | ML `0xDa1Vu`, #6 | Chạy smoke trên máy demo; lưu thông số thực và phiên bản | Đang mở |
| R05 | API/Predictor v0.1.1 còn nháp; chưa chốt ngôn ngữ, EXIF, size, timeout | Cao | BACKEND `Phuc1232` cùng ML/EXTENSION, #8 | Review liên vai trò; cập nhật schema/fixture có version | Chờ kiểm tra lại |
| R06 | `/predict` chế độ real mặc định chưa suy luận; mock chỉ tạo dữ liệu tổng hợp | Cao | BACKEND `Phuc1232`, #37/#38 | Giữ 503 trung thực đến khi tích hợp artifact; không dùng mock qua gate | Giới hạn đã biết |
| R07 | DOM/session của Extension có PR đang mở nhưng chưa xác minh sau merge trên main | Trung bình | EXTENSION `ngnsusinn`, #10/#11 | Review PR #65 và smoke trên fixture đã thống nhất | Đang mở |
| R08 | Issue nhắc T01–T12 nhưng `DESIGN.md` §1–4 chưa có đặc tả chi tiết | Trung bình | QA `dangnguyen0512`, #14 | DATA review ma trận QA và khóa phiên bản sau thống nhất | Đã có bản nháp |
| R09 | Chưa thống nhất giờ review, ngày khóa Test và phê duyệt CODEOWNERS cho QA | Trung bình | QA `dangnguyen0512`, owner `ngnsusinn`, #13 | Chốt hai giờ review/ngày, checkpoint và thời điểm khóa W4 | Chờ quyết định |
| R10 | DEFINE ghi tiếng Việt nhưng bản API nháp từng đề xuất đầu vào tiếng Anh | Cao | INTEGRATION `fulord26` cùng ML/EXTENSION, #4/#8 | Chốt một phạm vi ngôn ngữ trước khi nghiệm thu fixture/metrics | Chưa thống nhất |

Mỗi kỳ review cần bổ sung: URL bằng chứng, tác động đo được, quyết định, người duyệt và mốc xử lý tiếp. Ưu tiên blocker P0 trước khi dùng quỹ dự phòng; không đổi kiến trúc hoặc tự tạo số liệu chỉ để vượt checkpoint.
