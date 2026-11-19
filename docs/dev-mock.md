# AFN-009 — Mock dev/test tường minh (hợp đồng v0.1.1)

Chế độ dịch vụ này trả về **nội dung giả lập cố định (synthetic fixed content)** phục vụ phát triển Extension.
Đây không phải là mô hình đã huấn luyện, không kiểm tra tính chân thật, không kiểm thử độ chính xác hay đánh giá hiệu năng suy luận thực tế.
Hành vi mặc định vẫn là real/demo khi không có mô hình nào được nạp và `/predict` trả về mã HTTP 503.
Ở đây chỉ triển khai Issue #9; báo cáo bàn giao của #7/#8 mang tính lịch sử.

## Chạy cục bộ

Làm theo [hướng dẫn thiết lập trong README](../README.md) sử dụng các gói phụ thuộc đã ghim. Từ thư mục `backend`,
trên PowerShell (thay thế trình thông dịch môi trường ảo bạn chọn nếu cần):

```powershell
$env:AFN_ENVIRONMENT = "dev"
$env:AFN_PREDICTOR_MODE = "mock"
..\.venv\Scripts\python.exe -m app
```

Cả hai giá trị đều bắt buộc. `AFN_ENVIRONMENT=test` cũng cho phép mock; `demo` kết hợp với
`mock` sẽ thất bại khi xác thực cấu hình lúc khởi động. Chỉ thiết lập dev/test sẽ không
kích hoạt mock. `.env.example` cố ý mặc định là `demo` / `real`.
Địa chỉ bind mặc định vẫn là `127.0.0.1:8000`. Dừng lại bằng phím Ctrl+C.

Chuyển lại về chế độ real/demo rõ ràng trước khi demo thực tế:

```powershell
$env:AFN_ENVIRONMENT = "demo"
$env:AFN_PREDICTOR_MODE = "real"
..\.venv\Scripts\python.exe -m app
```

Đối với POSIX shell, sử dụng lệnh trên một dòng từ thư mục `backend`:
`AFN_ENVIRONMENT=dev AFN_PREDICTOR_MODE=mock ../.venv/bin/python -m app`.
Biến môi trường của tiến trình (process environment) sẽ ghi đè `.env`. Thay đổi chế độ yêu cầu khởi động lại
dịch vụ; không có endpoint HTTP nào để thay đổi chế độ hoặc ép buộc trạng thái ready.

## Health, dự đoán và trạng thái (Health, Prediction và State)

Sử dụng `curl.exe -i http://127.0.0.1:8000/health` trên Windows (`curl` trên POSIX).
Các trường trong body phản hồi vẫn tương thích với hợp đồng hiện có. Body minh họa
của health ở chế độ mock:

```json
{"service_status":"ok","model_ready":true,"contract_version":"0.1.1"}
```

Các header phản hồi của health/predict/error bao gồm:

```text
X-AFN-Inference-Mode: mock
X-AFN-Model-State: ready
Cache-Control: no-store
```

`model_ready=true` trong chế độ mock nghĩa là **mock provider đã sẵn sàng**, tuyệt đối không phải tính sẵn sàng của mô hình thật.
Không loại bỏ header mode hoặc ID kết quả `dev-mock-not-a-model` khi hiển thị đầu ra mock.
Health không bao gồm token, đường dẫn mô hình, dữ liệu thô đầu vào hay chi tiết lỗi.

| Sự kiện | Trạng thái | Health model_ready | Hành vi của Predict |
| --- | --- | --- | --- |
| Khởi động chế độ real mặc định, có hoặc không có đường dẫn artifact | `not_loaded` | false | 503 trước khi đọc body |
| Khởi động mock dev/test tường minh thành công | `ready` | true | 200 giả lập cho form mock hợp lệ |
| Factory của provider thất bại hoặc trả về provider không hợp lệ | `error` | false | 503; không có cơ chế dự phòng fallback |
| Gọi provider hoặc kiểm tra đầu ra thất bại | `error` | false | 503 đã được làm sạch; không fallback/retry |
| Request mock không hợp lệ | không đổi | không đổi | 400 đã làm sạch hoặc 413 do byte ảnh sau khi parse |
| Tắt dịch vụ (Shutdown) | `not_loaded` | Không còn tiến trình phục vụ | Các tham chiếu provider được xóa sạch |

`InferenceAdapter.initialize(factory)` là một điểm nối vòng đời Python, không phải trình loader
hay một route công khai. Một factory thực tế trong tương lai phải kiểm tra tính tương thích của artifact và
warm-up trước khi trả về provider. Việc chỉ gán `app.state.predictor` hoặc
có đường dẫn artifact không cấu thành trạng thái ready. Quá trình phục hồi yêu cầu
khởi tạo tường minh hoặc khởi động lại dịch vụ; các request không tự kích hoạt phục hồi.
Suy luận HTTP ở chế độ real vẫn bị vô hiệu hóa ngay cả khi DI bị ghi đè.

Ví dụ request PowerShell minh họa sử dụng tệp kiểm thử nhỏ/giả lập cục bộ:

```powershell
curl.exe -i http://127.0.0.1:8000/predict `
  --form-string "request_id=550e8400-e29b-41d4-a716-446655440000" `
  --form-string "title=Tiêu đề kiểm thử giả lập" `
  --form-string "text=Bài báo tiếng Anh giả lập phục vụ kiểm thử giao diện UI." `
  --form "image=@./example.png;type=image/png"
```

Mock trả về các giá trị cố định: `label=real`, `fake_score=0.42`, `model_id=dev-mock-not-a-model`,
`model_version=mock-v0.1.1`, `text_truncated=false`. Nó bỏ qua nội dung, không thực hiện tiền xử lý
và không bao giờ áp dụng ngưỡng ML. UUID phản hồi là UUID client đã parse; `processing_time_ms` được đo
xung quanh lời gọi Predictor, loại trừ thời gian khởi động và tải lên. Điểm số là dữ liệu giả lập,
không phải xác suất đã hiệu chuẩn. Chế độ real luôn trả về 503 và `request_id=null` ngay cả với request này.

## Ranh giới của cầu nối mock (Mock bridge boundaries)

Đây là tầng vận chuyển tối thiểu phục vụ phát triển, không phải sự hoàn tất của #22/#23:

- Chỉ chấp nhận multipart, với UUID/title/text cộng thêm một phần file. Sử dụng các giới hạn trường Pydantic hiện có.
  Các trường bị thiếu/sai định dạng/rỗng trả về 400 đã được làm sạch, không bao giờ trả về lỗi 422 mặc định của FastAPI.
  Bảo toàn các UUID không nhập nhằng đã được parse an toàn khi có lỗi xảy ra.
- Từ chối các trường trùng lặp/chưa biết trong cầu nối mock này. Đây là lựa chọn mang tính tất định cho phát triển;
  chính sách xử lý các phần trùng lặp/chưa biết ở chế độ real vẫn đang chờ xử lý.
- Sử dụng các ràng buộc parser của Starlette: một file, ba trường text, 200.000 byte cho mỗi phần text.
  Tệp tải lên được sao chép với thao tác đọc 10 MiB + 1 byte và bị từ chối nếu vượt quá 10 MiB, **sau khi parse**.
  Điều này không thực thi tổng số byte luồng request và không ngăn việc spool dữ liệu tải lên.
  `AFN_MAX_REQUEST_BYTES` vẫn chưa được thực thi.
- Yêu cầu các byte tải lên không được rỗng, nhưng **không xác thực MIME, JPEG/PNG thực tế,
  kích thước pixel, EXIF hay RGB**. Cầu nối có thể chấp nhận các byte không thể giải mã; một request mock thành công
  không phải là bằng chứng về tính hợp lệ của ảnh hay việc endpoint thực tế sẽ chấp nhận.
- Không thực thi `X-Demo-Token` trong chế độ mock. Suy luận HTTP thực tế vẫn bị vô hiệu hóa.
  Chế độ opt-in này chỉ dành cho các đầu vào giả lập cục bộ đáng tin cậy. Xác thực token/request đầy đủ
  vẫn thuộc phạm vi #22; xác thực nội dung ảnh vẫn thuộc phạm vi #23.
- Chưa có middleware CORS, chính sách hiển thị origin/header, warm-up, loader mô hình hay tích hợp ML nào
  được triển khai. Các cuộc gọi cross-origin của tiện ích mở rộng trình duyệt (Browser Extension) và việc đọc
  các header phản hồi tùy chỉnh vẫn phụ thuộc vào #38. Các bài kiểm thử giao diện UI có thể sử dụng fixture
  độc lập; không có tệp Extension nào bị sửa đổi ở đây.

## Fixtures và kiểm thử

Body theo phiên bản và metadata trạng thái/header nằm tại
[`backend/tests/fixtures/api/v0.1.1`](../backend/tests/fixtures/api/v0.1.1/README.md).
Các fixture không chứa bài báo, hình ảnh, secret hay artifact mô hình thật nào. Thời gian cố định
trong một fixture JSON chỉ là phần giữ chỗ và khác với thời gian đo thực tế khi chạy.
Các bài kiểm thử xác thực schema của fixture và so sánh kết quả HTTP, bảo toàn sự phân biệt về thời gian đó.
Tập hợp trường đầu ra/đầu vào ban đầu và chữ ký Predictor được giữ nguyên; v0.1.1 bổ sung hành vi mock opt-in
và các header mode/state.

Từ thư mục `backend` với Python thuộc môi trường ảo đã chọn:

```powershell
python -m pytest -q
python -m pip check
python tests/smoke_local.py
python tests/smoke_local.py --mode mock
```

Các lệnh smoke giữ cổng 8000, buộc tiến trình con của chúng chạy theo chế độ đã chỉ định
bất kể thiết lập chế độ được kế thừa, kiểm tra HTTP thực tế và dừng server của chính chúng
trong khối `finally`. Không chạy chúng đồng thời. Lệnh smoke mock chỉ gửi văn bản giả lập được tạo
và các byte kiểm thử chưa giải mã. Nó không kiểm thử xác thực ảnh hay ML. TestClient cũng bao quát
các lỗi khởi động/tắt dịch vụ và lỗi provider.

## Yêu cầu, phân định trách nhiệm và trạng thái review (2026-11-19)

| Yêu cầu / Nguồn | Triển khai | Kiểm chứng (Verification) | Phụ trách / Trạng thái |
| --- | --- | --- | --- |
| #9: Predictor + not_loaded/ready/error | `inference_adapter.py`, Predictor protocol hiện có | Kiểm thử trạng thái/lỗi của Adapter | Backend đã triển khai; ML đang chờ review |
| #9: mock dev/test cố định | `dev/mock_predictor.py`, `dev/transport.py`, `main.py` | Kiểm thử mock HTTP, lỗi đầu vào, correlation, fixture | Backend; Extension đang chờ consumer review |
| #9: opt-in rõ ràng, không fallback thực tế | Settings/environment + factory vòng đời | Cấu hình, lỗi factory và kiểm thử hồi quy chế độ real | Backend đã triển khai |
| #9: health an toàn / real 503 khi chưa sẵn sàng | Health adapter DI + bộ xử lý lỗi | Kiểm thử quyền riêng tư, thiếu artifact, không đọc body và smoke test | Backend đã triển khai |
| #9: fixtures/docs có phiên bản; không sửa loader | `backend/tests/fixtures/api/v0.1.1`, tài liệu này | Xác thực fixture và rà soát diff có giới hạn | Backend sẵn sàng bàn giao cục bộ |
| Tiền đề đã hoàn thành: #7 + #8 / ML review | Nền tảng hiện có và hợp đồng đề xuất | Đã đọc các issue/comment hiện có; chưa có phê duyệt mới | MỘT PHẦN (PARTIAL): môi trường và review hợp đồng liên vai trò vẫn đang chờ |

Issue #9 trên GitHub hiện đang open và chưa có bình luận khi kiểm tra. Live #7/#8 được đánh dấu
`closed` với `state_reason=not_planned`, trong khi nội dung của chúng ghi cần mở tiếp
để chờ kiểm tra lại/review và hợp đồng v0.1.0 chỉ là bản thảo. Các bình luận của chúng chỉ ghi
"check my pull request". Không diễn giải trạng thái closed như là sự phê duyệt liên vai trò.
Nhánh cục bộ là `dev-be`, baseline `d134971`; ban đầu chỉ có `.agents/` là untracked.
Thư mục skill đó được giữ nguyên. `DIAGRAMS.md` không tồn tại; `DESIGN.md` vẫn chỉ có
các phần 1–4 mặc dù issue có tham chiếu đến §8.1–8.4. Các quyết định hiện có về ngôn ngữ,
bytes/RGB, timeout, tổng dung lượng và chính sách xác thực vẫn chưa được giải quyết.

ML review ngữ nghĩa/môi trường của Predictor; Extension review việc tiếp nhận health/kết quả
và dấu hiệu nhận biết mock; repo owner review toàn bộ tệp theo CODEOWNERS. **Chưa có phê duyệt nào
từ ML/Extension được xác nhận và không có yêu cầu review bên ngoài nào được gửi trong lần chạy này.**
Tài liệu này ghi nhận sự thay đổi hợp đồng để bàn giao; đây không phải biên bản phê duyệt. Không có thao tác
commit, push, PR hay biến đổi trạng thái issue nào được ủy quyền hoặc thực hiện cho #9.

## Bằng chứng thực thi (Execution evidence)

Môi trường kiểm thử hiện tại: Windows x64, Python **3.13.1** từ lệnh `python` có sẵn.
File `..\.venv\Scripts\python.exe` cũ không thể khởi động vì tệp thực thi Python 3.10 của nó
không còn tồn tại. Đã tạo `.venv/issue9` mà không xóa hay ghi đè môi trường cũ; nó vẫn được Git bỏ qua (ignored).

Trong bản checkout này, từ thư mục `backend`, hãy dùng
`..\.venv\issue9\Scripts\python.exe -m app` với các cờ nêu trên để chạy môi trường
đã cài đặt. Sử dụng chính trình thông dịch này cho pytest, pip check và các script smoke;
file `..\.venv\Scripts\python.exe` ban đầu vẫn không thể sử dụng.

Đã cài đặt các gói yêu cầu đã ghim sẵn có vào môi trường mới. Lần thử đầu tiên trong sandbox
thất bại với WinError 10013; lần thử lại sau khi cấp quyền đã thành công.
Tải `python-multipart` bằng lệnh `pip download --python-version 3.10
--only-binary=:all: --no-deps --dest .venv/issue9/wheels python-multipart` và cài đặt
wheel **0.0.32** đã phân giải với tùy chọn `--no-index`, sau đó thêm bản ghim chính xác đó.
Tất cả các bản ghim khác được giữ nguyên. Ràng buộc giải quyết này duy trì yêu cầu baseline cũ;
đây không phải là việc chạy lại trên Python 3.10 hay bằng chứng về tính tương thích với ML.

Lần chạy test ban đầu báo cáo 88 passed và 2 lỗi setup do ID tham số tự sinh quá dài;
sau khi gán các ID ngắn, kết quả thực tế của toàn bộ bộ test là **89 passed in 1.73s**.
Kết quả xác minh cuối cùng được ghi lại bên dưới.

Tất cả các lệnh dưới đây được chạy từ thư mục `backend` sử dụng `..\.venv\issue9\Scripts\python.exe`
trừ khi có ghi chú khác. Không có công cụ lint/type-check nào được cấu hình trong repo.

| Lệnh / Kiểm chứng | Kết quả thực tế cuối cùng |
| --- | --- |
| `python -m pytest -q` sau khi bổ sung bài test hồi quy lỗi khởi động | **90 passed in 2.52s**, exit 0 |
| `python -m pip check` | **No broken requirements found.**, exit 0 |
| `python tests/smoke_local.py` | Health 200, mode real, ready false; predict 503/null UUID; child process đã dừng; exit 0 |
| `python tests/smoke_local.py --mode mock` | Health 200, mode mock, ready true; predict 200/dev-mock ID/echoed UUID; child process đã dừng; exit 0 |
| `git diff --check` / `git -c core.safecrlf=false diff --check` từ thư mục gốc repo | Không có lỗi khoảng trắng; các lệnh Git thông thường chỉ phát cảnh báo chuyển đổi LF sang CRLF |
| Kiểm tra khoảng trắng Python + `ast.parse` trên các file mới/đổi, trừ `.agents/` có sẵn | **12 tệp sửa đổi + 17 tệp mới đều đạt chuẩn** |
| So sánh `importlib.metadata.version` với từng bản ghim trong requirements | Tất cả các phiên bản đã cài đặt khớp với 28 bản ghim |
| `git diff --cached --name-only` và diff có phạm vi các file gốc | Không có file staged; design/planning/CODEOWNERS/báo cáo lịch sử không đổi |
| Python 3.10, Linux/macOS, mô hình huấn luyện thực tế, tích hợp CORS trình duyệt | **CHƯA CHẠY**; nằm ngoài môi trường/phạm vi cục bộ này |

Các thay đổi mã nguồn gồm:

- Sửa đổi: `.env.example`, `README.md`, `backend/app/config.py`,
  `backend/app/main.py`, `backend/app/predictor.py` (chỉ docstring),
  `backend/app/schemas.py` (chỉ phiên bản hợp đồng), `backend/requirements.txt`,
  `backend/tests/smoke_local.py`, `backend/tests/test_app.py`,
  `backend/tests/test_config.py`, `docs/api-contract.md`, `docs/inference-interface.md`.
- Thêm mới: `backend/app/inference_adapter.py`, `backend/app/dev/__init__.py`,
  `backend/app/dev/mock_predictor.py`, `backend/app/dev/transport.py`,
  `backend/tests/test_inference_adapter.py`, `backend/tests/test_dev_mock.py`,
  tài liệu này, và mười tệp fixture/manifest/README trong thư mục
  `backend/tests/fixtures/api/v0.1.1/`.

| Tiêu chí nghiệm thu Live Issue #9 | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Mock chỉ khi có cờ dev/test tường minh; không fallback khi mô hình thật lỗi | **ĐẠT (PASS)** cục bộ | Cấu hình opt-in, factory thực, các bài test lỗi khởi tạo/gọi hàm |
| Health an toàn; chế độ real không có artifact không bao giờ ready | **ĐẠT (PASS)** cục bộ | Kiểm thử DI health/quyền riêng tư và smoke test HTTP thực tế |
| Chế độ real chưa sẵn sàng trả về 503 | **ĐẠT (PASS)** cục bộ | Kiểm thử hồi quy không đọc body/override hiện có và HTTP smoke |
| Bàn giao chỉ dành cho dev/test, fixtures có phiên bản, không sửa model_loader.py | **ĐẠT (PASS)** cục bộ | So sánh schema/HTTP của fixture có phiên bản và rà soát diff có phạm vi |
| Các điều kiện tiên quyết được chấp nhận và review ML bắt buộc | **MỘT PHẦN (PARTIAL)** | Các quyết định review của #7/#8 vẫn chưa được giải quyết; chưa có phê duyệt mới từ ML/Extension |

Triển khai đã hoàn thiện về mặt mã nguồn cho phạm vi cục bộ này. Trạng thái Done trên GitHub vẫn là
**MỘT PHẦN (PARTIAL)**, không phải là sự phê duyệt được suy đoán. Không có thao tác commit/push/PR hay biến đổi
trên GitHub nào được thực hiện. Các rủi ro còn lại là việc tích hợp mô hình thực/CORS/vận chuyển chưa hoàn thành
như đã ghi trong tài liệu và việc chờ review hợp đồng dùng chung, chứ không phải do cơ chế fallback ẩn của mock.
