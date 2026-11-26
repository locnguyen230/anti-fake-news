# Checkpoint tích hợp tuần 3 · AFN-045

**Gate bị chặn. Test nghiên cứu vẫn khóa.** Các luồng API/Extension có thể
kiểm trên phiên bản hiện tại đã có bằng chứng ở ma trận. Chờ demo với model
nghiên cứu và các kiểm tra phát hành trước khi ký. [Ma trận T01–T12](regression-matrix.md)

## Phiên bản và bằng chứng hiện có

| Đầu vào | Phiên bản kiểm được | Điều kiện ký |
| --- | --- | --- |
| API, Extension | API v0.2.0. AFN-027 và AFN-030 đã đóng. Chromium chạy mock, 503 thật khi thiếu artifact, và race/UUID. Preflight với CLIP cache và bundle huấn luyện trên fixture cũng chạy qua Chromium. | QA đối chiếu bộ kiểm API #28, E2E #43 và quyền/CORS/privacy #44. [Gate tuần 2](week-2-gate.md) |
| Mô hình | Ba bundle `candidate` từ `ml-v2`. Multimodal báo cáo version `multimodal-20261125-105d5f14e79a`. Parity #36 dùng 32 mẫu Validation với predictor tham chiếu. | Backend/QA cần cùng bundle qua Predictor dịch vụ, warm-up, health và Extension trước khi quyết định freeze. [Bundle](ml-candidates-v2.md) · [Parity](inference-parity.md) |
| Dữ liệu | `ml-v2`, seed 42, 153 Train / 32 Validation / 33 Test khóa, hash lưu trong hồ sơ lựa chọn. QA giữ payload Test. | Đối chiếu độc lập hash, nhóm/lớp và nguồn đủ cho phạm vi phân tích. [Bản lựa chọn](../configs/selected-models.json) · [#29](https://github.com/ngnsusinn/anti-fake-news/issues/29) |

## Lỗi chặn và việc theo dõi

| Mức độ | Việc còn chờ | Owner và bằng chứng |
| --- | --- | --- |
| P0 · Chặn gate | Xác minh gói Multimodal nghiên cứu qua Backend và Chromium với model ID/version/hash, dùng đầu vào demo được phép. | BACKEND `Phuc1232`, QA `dangnguyen0512`. [#37](https://github.com/ngnsusinn/anti-fake-news/issues/37) · [#39](https://github.com/ngnsusinn/anti-fake-news/issues/39) · [#43](https://github.com/ngnsusinn/anti-fake-news/issues/43) |
| P0 · Chặn gate | Xác nhận quyền Extension, CORS, token và dữ liệu riêng trên commit demo. | QA `dangnguyen0512`, BACKEND `Phuc1232`. [#44](https://github.com/ngnsusinn/anti-fake-news/issues/44) · [#38](https://github.com/ngnsusinn/anti-fake-news/issues/38) |
| P0 · Chặn mở Test | QA kiểm `ml-v2` đủ lớp/nhóm và hash. QA/ML ký manifest, split, mã, preprocessing, artifact, C/ngưỡng và mapping trước khi ML mở Test. | QA `dangnguyen0512`, DATA `locnguyen230`, ML `0xDa1Vu`. [#29](https://github.com/ngnsusinn/anti-fake-news/issues/29) · [#49](https://github.com/ngnsusinn/anti-fake-news/issues/49) |
| Tuần 4 · Nghiệm thu | T11 chờ predictions/metrics sau freeze. T12 chờ kết quả bộ 10 trang và đo sau warm-up trên máy demo. | ML `0xDa1Vu`, QA `dangnguyen0512`, BACKEND `Phuc1232`. [#50](https://github.com/ngnsusinn/anti-fake-news/issues/50) · [#52](https://github.com/ngnsusinn/anti-fake-news/issues/52) |
| P2 · Tài liệu | Issue #40 gọi phần kết quả T05, kế hoạch QA dùng T07. Dùng mã trong kế hoạch để ghi chứng cứ tuần 3. | Integration `fulord26`, QA `dangnguyen0512`. [Kế hoạch QA](../docs/test-plan.md) |

Integration `fulord26` cập nhật các ca bị ảnh hưởng khi #43 và #44 bàn
giao. QA `dangnguyen0512` review checkpoint sau khi xác nhận bằng chứng
trên cùng bản tích hợp. Nếu audit phát hiện thiếu lớp/nhóm hoặc lỗi nghiêm
trọng, giữ gate blocked và chuyển xử lý cho owner tương ứng.
