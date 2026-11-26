# Ma trận hồi quy T01–T12 · AFN-045

Bằng chứng tích hợp ngày 25/11/2026. Checkout nền `681de1c`, API v0.2.0,
Windows x64, Python 3.13.0, Node 26.13.1 và Chromium 159. Dùng định nghĩa
ca trong kế hoạch AFN-014. AFN-040 gọi phần hiển thị là T05 trong issue.
Trong ma trận QA, T05 là ảnh đầu vào và T07 là kết quả hiển thị.
[Kế hoạch QA](../docs/test-plan.md)

| Ca | Trạng thái | Bằng chứng và phạm vi còn thiếu |
| --- | --- | --- |
| T01 · Phiên theo tab | Đạt | Chromium unpacked kiểm chuyển tab, session độc lập, fallback khi trang hạn chế và dọn session. [Browser smoke](../tests/frontend/browser-smoke.mjs) |
| T02 · Trích xuất | Đạt trên fixture | Chromium kiểm bài tĩnh, DOM rỗng/động, ảnh tương đối và nhập thủ công. Còn bộ 10 trang nghiệm thu. [Browser smoke](../tests/frontend/browser-smoke.mjs) |
| T03 · Chọn đúng một ảnh | Đạt | Chromium kiểm chọn ảnh ứng viên, upload thủ công, preview và dọn file. Multipart mock xác nhận phần ảnh. [Browser smoke](../tests/frontend/browser-smoke.mjs) |
| T04 · Giới hạn text/title | Đạt ở luồng hiện tại | Chromium giữ draft và focus lỗi. Backend kiểm multipart và giới hạn byte với input tổng hợp. [Browser smoke](../tests/frontend/browser-smoke.mjs) · [Backend request limits](../backend/tests/test_request_limits.py) |
| T05 · Ảnh/EXIF | Đạt ở Backend | Các kiểm thử validation ảnh và request limits chạy trên mã thật, gồm MIME/giải mã, ngưỡng byte/pixel, JPEG EXIF và lỗi trước predictor. [Image validation](../backend/tests/test_image_validation.py) · [Backend request limits](../backend/tests/test_request_limits.py) |
| T06 · Tường minh và UUID | Đạt hợp đồng trên mock | Chromium gửi multipart vào FastAPI mock. Node kiểm UUID, các part và boundary. Còn xác nhận trên bản demo #43. [API client tests](../tests/frontend/api-client.test.mjs) · [Browser smoke](../tests/frontend/browser-smoke.mjs) |
| T07 · Kết quả UI từ model thật | Chờ #43 | View đã kiểm nhãn, score, version, thời gian, truncation và cảnh báo cạnh kết quả. Chromium nhận được kết quả từ CLIP và bundle huấn luyện trên fixture tổng hợp. Browser cũng kiểm phản hồi mock và bỏ UUID sai. Bằng chứng model nghiên cứu cần đúng bundle/hash. [Result-view tests](../tests/frontend/result-view.test.mjs) · [#43](https://github.com/ngnsusinn/anti-fake-news/issues/43) |
| T08 · Lỗi và thử lại | Một phần | Chromium kiểm giữ draft khi real-mode trả 503, sửa token rồi thử lại. Node kiểm timeout/lỗi mạng. Còn chạy trên cấu hình demo thật và rà CORS #44. [Browser smoke](../tests/frontend/browser-smoke.mjs) · [Recovery tests](../tests/frontend/error-recovery.test.mjs) · [#44](https://github.com/ngnsusinn/anti-fake-news/issues/44) |
| T09 · Race theo yêu cầu | Đạt | Chromium mô phỏng A trả sau B, sai UUID và reload. Node kiểm thế hệ request khi sửa input và phiên độc lập. [Browser smoke](../tests/frontend/browser-smoke.mjs) · [Lifecycle tests](../tests/frontend/request-lifecycle.test.mjs) |
| T10 · Split, nhóm và seed | Chờ audit #29 | Bộ kiểm thử pipeline DATA chạy trên fixture. ML đã ghi kiểm tra nhóm/hash và chia `ml-v2`; QA cần audit độc lập cùng phiên bản. [Train/Validation](ml-train-validation.md) · [Hash](../configs/selected-models.json) · [#29](https://github.com/ngnsusinn/anti-fake-news/issues/29) |
| T11 · Freeze và Test cuối | Chờ #49/#50 | ML ghi chọn C/ngưỡng chỉ trên Validation. Chờ QA/ML ký hash và biên bản freeze, ML xuất predictions/metrics rồi QA đối chiếu #58. [Giao thức](../docs/experiment-protocol.md) · [#49](https://github.com/ngnsusinn/anti-fake-news/issues/49) · [#50](https://github.com/ngnsusinn/anti-fake-news/issues/50) |
| T12 · Demo và hiệu năng | Chờ #43/#52 | Cần demo với model nghiên cứu, bộ 10 trang đã chọn trước, tỷ lệ trích xuất và trung vị qua ít nhất 20 lượt trên máy demo. [#43](https://github.com/ngnsusinn/anti-fake-news/issues/43) · [#52](https://github.com/ngnsusinn/anti-fake-news/issues/52) |

## Lệnh đã chạy

- `node --test tests/frontend/*.test.mjs` · 21 ca đạt.
- `python scripts/test_extension_smoke.py` · Chromium chạy với FastAPI mock
  và FastAPI real-mode thiếu artifact. Bộ trang, form và ảnh là fixture.
- Từ `backend/`: `python -m pytest -q tests/test_image_validation.py tests/test_request_limits.py tests/test_app.py`
  · 49 ca đạt.
- `python -m pytest -q tests/data/test_build_recovery_snapshots.py tests/data/test_recovery_snapshots.py tests/data/test_validate_manifest.py tests/data/test_group_samples.py tests/data/test_split_data.py tests/test_prepare_dataset.py tests/frontend/test_package_extension.py`
  · 9 ca đạt trên fixture và bao gói Extension.
- `python -m pytest -q tests/data/test_recover_data.py` · 4 ca recovery đạt trong môi trường có `requests`.

Khi có commit mới, ghi SHA, bản API, mode, model ID/version/hash, phiên bản
dataset và máy test trên từng kết quả mới. Chạy lại các ca bị ảnh hưởng và
ghép chứng cứ từ QA trước khi ký. [Checkpoint tuần 3](week-3-gate.md)

## Bằng chứng gói Backend · AFN-054

- Windows x64, AMD Ryzen 5 PRO 4650U, Python 3.13.0. Tạo ZIP 24 tệp
  theo danh sách cố định, kiểm nội dung và xác nhận token mẫu trống.
  Sau khi giải nén ZIP vào thư mục mới, cài hai bộ pins vào venv mới
  từ wheelhouse với `--no-index`, rồi chạy `pip check` thành công.
- Chạy `python tests/smoke_local.py` trên gói giải nén. Health 200,
  `model_ready=false`, request thiếu token 401, request hợp lệ 503
  `model_not_ready` cùng UUID. Smoke mock cũng nhận 200 với định danh mock.
- Khởi chạy process từ gói giải nén với `HF_HUB_OFFLINE=1`, checkpoint
  CLIP revision `3d74acf9` đã kiểm SHA-256, và bundle
  `multimodal-20261124-b696e27eac86-fixture` trong môi trường test.
  Health báo ready, predict trả 200 đúng UUID và model version.
  Chromium unpacked hiển thị kết quả. Smoke nghiệm thu từ chối bundle
  fixture khi truyền nó vào tùy chọn `--bundle`.
- Lượt preflight chạy trên cùng máy Windows. Còn cần kiểm trên máy
  bàn giao, bundle nghiên cứu đã freeze và kết quả #53.
  [Checklist](../release/backend-checklist.md)
