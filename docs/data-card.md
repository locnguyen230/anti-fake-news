# Data card · AFN-033

## Nguồn và đơn vị phân tích

Dự án nghiên cứu bài viết tiếng Anh kèm một ảnh đại diện. FakeNewsNet cung cấp
bốn nhóm metadata từ PolitiFact và GossipCop, mỗi nguồn có nhóm `fake` và
`real`. Khóa mẫu là `source:label:source_id`. Nhãn kế thừa từ nhóm CSV của
nguồn. Nhóm dự án kiểm tra bản ghi, đúng bài và ngữ cảnh ảnh khi thu hồi.
Nhãn biểu thị phân loại của nguồn. [FakeNewsNet](https://github.com/KaiDMML/FakeNewsNet#overview) ·
[Hợp đồng manifest v1](data-contract.md)

## Thu hồi, lọc và chia tập

- Giữ bài khớp với URL và tiêu đề gốc, có thân bài tiếng Anh và một ảnh liên quan.
  Loại nội dung chuyển hướng sai bài, trang lỗi, logo, quảng cáo và ảnh hỏng.
  Kiểm tra quyền đối với cả bài và ảnh trước khi đánh dấu `accepted`. Ghi lý do
  loại và thời điểm thu hồi UTC theo manifest.
- Validator kiểm tra body tối đa 50.000 ký tự, ảnh JPEG/PNG giải mã được,
  tối đa 10 MiB và 20 megapixel, cùng SHA-256 của ảnh. Trước khi chia, audit
  các liên kết trùng hoặc gần trùng, sự kiện và nhà xuất bản khi có metadata.
- Chia nhóm nguyên vẹn theo mục tiêu 70/15/15 với seed 42. Dùng cùng bộ ID và
  cùng split cho ba cấu hình. QA giữ payload Test riêng đến khi ký freeze.
  Ghi tỷ lệ thực tế và số mẫu, lớp, nguồn, nhóm. Nếu thiếu lớp hoặc nhóm
  độc lập, ghi blocker trước khi đánh giá. [Quy trình tái tạo](rebuild-data.md) ·
  [Giao thức thực nghiệm](experiment-protocol.md)

## Bằng chứng theo giai đoạn

| Giai đoạn | Số liệu đã công bố | Bằng chứng |
| --- | --- | --- |
| Thu hồi | 400 bản ghi có body hoặc ảnh, 286 có cả hai | [Báo cáo thu hồi](../reports/recovery-summary.md) |
| Chuẩn bị Train/Validation `ml-v2` | Giữ 218/352 bản ghi trong bản xuất DATA, chia 153 Train, 32 Validation, 33 Test khóa. Bản xuất thiếu metadata URL, publisher và sự kiện. | [Chuẩn bị ml-v2](../reports/ml-train-validation.md#1-chuẩn-bị-dữ-liệu-mlprepare_dataset) · [Hash Train/Validation](../configs/selected-models.json) |
| Bản DATA cuối | Đang chờ số mẫu hợp lệ, tỷ lệ loại theo nguồn/lớp, phân bố split/group, phiên bản và checksum đã audit. Mốc mục tiêu là 200–500 bài đủ hai đầu vào. | DATA `locnguyen230` · [#31](https://github.com/ngnsusinn/anti-fake-news/issues/31) · [#32](https://github.com/ngnsusinn/anti-fake-news/issues/32) |

Các giai đoạn dùng tiêu chí và bản đầu vào khác nhau. Dùng đúng mẫu số của
từng báo cáo khi phân tích mất dữ liệu. Với bản DATA cuối, ghi rõ nếu dưới
200 mẫu hoặc thiếu lớp/nhóm, và chỉ diễn giải theo phạm vi mà QA chấp nhận.

## Giới hạn và chia sẻ

URL chết, paywall, chuyển hướng và CDN có thể gây mất dữ liệu khác nhau theo
nguồn, thời điểm và nhãn. Hai phân tập cũng khác chủ đề. Mẫu phục hồi được,
đặc biệt các bài có đủ ảnh và text, có thể lệch so với quần thể nguồn. Phân
tích lỗi cần giữ số đếm theo nguồn/lớp và lưu ý các nhóm nhỏ. Phạm vi nghiên
cứu là tập con tiếng Anh này.

DATA duyệt trước khi chia sẻ từng trường metadata. Bản giao mặc định gồm mã
mẫu nguồn đã duyệt, phân công split được phép thấy, quy tắc xử lý, checksum
và thống kê tổng hợp. Body, ảnh, thông tin cá nhân, tweet IDs và bằng chứng
quyền được giữ trong kho giới hạn truy cập. Tuân theo quyền theo từng tài
nguyên khi bàn giao sang môi trường khác.
