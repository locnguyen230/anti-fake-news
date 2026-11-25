# AFN-030 · Checkpoint tích hợp tuần 2

Ngày 25/11/2026. **Mock Extension đạt. Gate chờ review #28 và audit độc lập #29.**
AFN-008 và AFN-014 đã đóng. Bằng chứng dùng hợp đồng API v0.2.0 và ma trận
T01–T06/T10. [Ma trận QA](../docs/test-plan.md)

## Extension và API

| Đầu vào | Kết quả | Review |
| --- | --- | --- |
| AFN-027 · mock UI | Đã đóng. Chromium unpacked đạt các ca đúng tab, nhập tay, sửa text, ảnh, multipart và giữ input khi lỗi. [Kết quả chạy](extension-mock-results.md) | QA `dangnguyen0512` |
| AFN-028 · hợp đồng API | Còn mở. PR #94 báo 13/13 ca API contract đạt trên Linux, gồm auth, giới hạn, correlation và readiness. [Báo cáo tại commit e2b4f20](https://github.com/ngnsusinn/anti-fake-news/blob/e2b4f206d909a8454ef37dbbd14b12c7fe44f9d7/reports/api-contract-results.md) | QA `dangnguyen0512`, DATA `locnguyen230` |

## Dữ liệu và ML

- **Fixture tổng hợp.** Chạy `python -m ml.export_artifacts --fixture --offline`
  trên Windows với CLIP ViT-B/32 ghim tại revision `3d74acf9`. Ba pipeline
  Text-only, Image-only và Multimodal xuất gói 391, 512 và 903 chiều. Sai lệch
  điểm Validation khi đọc lại bundle là 0 và nhãn trùng ở cả ba cấu hình.
  Kết quả mang nhãn `FIXTURE_SMOKE_NOT_RESEARCH`.
- **Loader AFN-024.** Backend warm-up bundle `multimodal-20261125-b696e27eac86-fixture`
  với CLIP ghim từ cache. Health 200 và `ready`. Multipart có token và UUID
  nhận HTTP 200, giữ UUID và trả hậu tố `-fixture`. 79 ca pytest tập trung
  vào loader, bundle và lifecycle đạt. [Fixture và cách chạy](../tests/fixtures/loader/README.md)
- **Ứng viên nghiên cứu.** AFN-034 đã chạy Train/Validation trên `ml-v2`
  (153 Train, 32 Validation, 33 Test khóa), seed 42, manifest `a42af272…` và
  split `81058045…`. Báo cáo #35 ghi ba bundle `candidate` và #36 ghi parity
  trên 32 mẫu Validation với predictor tham chiếu. Bằng chứng mang nhãn
  `VALIDATION_ONLY`. [Train/Validation](ml-train-validation.md) ·
  [Hash đầy đủ](../configs/selected-models.json) · [Export](ml-candidates-v2.md) ·
  [Parity](inference-parity.md)
- **T10 và Test.** Split DATA trước bước chuẩn bị `ml-v2` có mẫu trùng ảnh
  hoặc body ở nhiều tập. ML đã lọc, gom nhóm lại và công bố split mới.
  QA cần đối chiếu độc lập hash manifest/split và nhóm trên gói `ml-v2` trước
  khi ký gate. Giữ Test khóa tới khi #49 ký freeze, sau đó #50 mới đánh giá.
  [Bằng chứng chuẩn bị dữ liệu](ml-train-validation.md#1-chuẩn-bị-dữ-liệu-mlprepare_dataset) ·
  [Audit #29](https://github.com/ngnsusinn/anti-fake-news/issues/29)

## Sai lệch và việc chờ nghiệm thu

| Mức độ | Sai lệch hoặc việc còn chờ | Owner và bằng chứng |
| --- | --- | --- |
| P1 · Đã sửa | Sửa input từng làm biến mất kết quả thành công. Bây giờ giữ kết quả và báo kết quả cũ cho đến lần phân tích tiếp theo. | INTEGRATION `fulord26`. T04 trong [kết quả Chromium](extension-mock-results.md). |
| P0 · Chặn gate | QA cần xác minh split `ml-v2`, gồm version/hash và nhóm trùng. | QA `dangnguyen0512`, DATA `locnguyen230`, ML `0xDa1Vu`. [#29](https://github.com/ngnsusinn/anti-fake-news/issues/29) |
| P0 · Chờ review gate | Hoàn tất review bộ kiểm tra API v0.2.0. | QA `dangnguyen0512`, DATA `locnguyen230`. [#28](https://github.com/ngnsusinn/anti-fake-news/issues/28) · [PR #94](https://github.com/ngnsusinn/anti-fake-news/pull/94) |
| Tuần 3 | Kiểm candidate qua predictor của dịch vụ, kết nối và error recovery bằng môi trường demo, rồi chạy checklist trang nghiên cứu. | BACKEND `Phuc1232`, EXTENSION `ngnsusinn`, QA `dangnguyen0512`. [#39](https://github.com/ngnsusinn/anti-fake-news/issues/39) · [#43](https://github.com/ngnsusinn/anti-fake-news/issues/43) · [#45](https://github.com/ngnsusinn/anti-fake-news/issues/45) |

Ký checkpoint sau khi QA review bằng chứng mock và xác nhận #27, #28, #29 đạt.
