# Báo cáo triển khai AFN-007 / AFN-008

Ngày thực hiện: **2026-11-18 (Asia/Saigon)**. Phạm vi chỉ #7 và #8.
Đây là bằng chứng triển khai local, không phải biên bản phê duyệt của reviewer.

## A — Kiểm tra ban đầu

- Đã đọc toàn bộ `PLANNING_ISSUES_7_8.md`, `DEFINE.md`, `DESIGN.md` và
  `.github/CODEOWNERS`. Không tìm thấy `AGENTS.md` áp dụng.
- `git status --short` ban đầu chỉ có `?? PLANNING_ISSUES_7_8.md`.
  `git diff` và `git diff --cached` trống. Tệp kế hoạch này được giữ nguyên.
- Repo chỉ có tài liệu, slides, PDF và CODEOWNERS; chưa có backend, README,
  tests, dependency manifest, ML/Extension source hay model artifacts.
- Đã đọc mô tả mới nhất qua GitHub connector của [#7](https://github.com/ngnsusinn/anti-fake-news/issues/7)
  và [#8](https://github.com/ngnsusinn/anti-fake-news/issues/8). Tại thời điểm đọc,
  cả hai `open`, assignee `Phuc1232`, không có comments. Đây không phải bằng chứng
  review. CODEOWNERS yêu cầu owner `@ngnsusinn` review tất cả tệp.
- `DESIGN.md` chỉ có §1–4; các tham chiếu §8–14 trong plan/issues không tồn tại
  ở checkout. `README`, `DIAGRAMS.md`, `PLANNING_ISSUES_7_8_EN.md` cũng không có.
  Dùng đúng tệp kế hoạch người dùng yêu cầu, không tạo tài liệu nguồn giả.
- `DEFINE.md` §3 ghi tiếng Việt nhưng cũng liệt kê tiếng Việt là hướng sau
  4 tuần; kế hoạch #7/#8 yêu cầu tiếng Anh. Contract nháp theo tiếng Anh và ghi
  xung đột để ML/Extension xác nhận; không sửa tài liệu nguồn.

Kế hoạch thay đổi: tạo mới foundation/config/DI/tests/README/env/gitignore cho
#7; schemas/API + inference docs cho #8; ghi bằng chứng và điểm chờ review.
Không chỉnh slides, PDF, CODEOWNERS, tài liệu nguồn hoặc kế hoạch chưa commit.

## B–C — Tệp thực tế được thêm

Tất cả tệp dưới đây là **tệp mới chưa commit**; không thay đổi tệp tracked có sẵn.

| Issue | Tệp | Nội dung |
| --- | --- | --- |
| #7 | `backend/app/__init__.py` | Package backend |
| #7 | `backend/app/main.py` | App factory, lifespan, health, skeleton predict 503, xử lý ModelNotReadyError |
| #7 | `backend/app/__main__.py` | Launcher dùng AFN_HOST/AFN_PORT, mặc định loopback, không access log |
| #7 | `backend/app/config.py` | Settings env/.env, SecretStr, origin/path/port và giới hạn request đề xuất |
| #7/#8 | `backend/app/predictor.py` | Protocol, input typed, provider DI và exception; không loader/mock/suy luận |
| #7 | `backend/requirements.txt` | 27 package runtime/test/transitive được pin chính xác |
| #7 | `.env.example`, `.gitignore` | Ví dụ không có secret; bỏ qua env/venv/cache/raw/private data/weights/artifacts |
| #7 | `README.md`, `backend/pytest.ini` | Setup/run/test local và cấu hình pytest |
| #7/#8 | `backend/tests/conftest.py` | Tách AFN environment khỏi test |
| #7 | `backend/tests/test_config.py` | Default, env precedence, path/origin/port, secret masking, launcher |
| #7/#8 | `backend/tests/test_app.py` | Lifespan, health, DI override, 503, không đọc body, lỗi không lộ chi tiết, OpenAPI |
| #8 | `backend/tests/test_schemas.py` | Giới hạn trường, UUID, enum, NaN/Infinity, timing, kiểu bool/bytes |
| #7 | `backend/tests/smoke_local.py` | Khởi động Uvicorn thật trên localhost, kiểm tra HTTP rồi dừng child process |
| #8 | `backend/app/schemas.py` | Form text fields, PredictionResult/PredictResponse/ErrorResponse/HealthResponse |
| #8 | `docs/api-contract.md` | Contract v0.1.0: multipart/token/limits/errors/correlation/timeout, cURL và FormData |
| #8 | `docs/inference-interface.md` | Predictor v0.1.0, byte input đề xuất, output, lifecycle và ranh giới ML/Backend |
| #7/#8 | `docs/implementation-issues-7-8.md` | Báo cáo này và yêu cầu review nháp |

Môi trường `.venv/` và `.venv/verify/` là thư mục sinh ra local, được ignore,
không phải deliverable mã nguồn. Không tạo `.env` chứa token.

`/predict` **luôn 503 trước khi đọc body**, kể cả khi override dependency.
`/health` **luôn model_ready=false**. Không có kết quả dự đoán thành công giả,
model loader, token auth đầy đủ, parser upload, decode ảnh, CORS, warm-up hay
readiness state machine. Các ví dụ kết quả/fixture đều được ghi là minh họa.

## D — Lệnh đã chạy và kết quả

Môi trường gốc: Windows x64, **Python 3.10.0**, pip 21.2.3. `py -0p` báo
không có Python được đăng ký với launcher; `python` vẫn chạy bình thường.
Lệnh Python dưới đây dùng interpreter của `.venv`, không cài vào Python global.

| Lệnh / kiểm tra | Kết quả thực tế |
| --- | --- |
| `Get-Location`, `rg --files`, `Get-ChildItem`, `Get-Content` các tài liệu/CODEOWNERS | Đã kiểm tra repo/tài liệu nêu ở A |
| `git ls-files`, `git remote -v`, `git status --short`, `git diff`, `git diff --cached` | Remote ngnsusinn/anti-fake-news; chỉ có kế hoạch untracked trước khi làm |
| `python --version`, `python -m pip --version`, `Get-Command python,uv,gh` | Python 3.10.0/pip 21.2.3; có uv; không dùng uv/gh để sửa repo |
| `python -m venv .venv` | Thành công |
| `.venv\Scripts\python.exe -m pip install fastapi uvicorn pydantic-settings pytest httpx` | Lần sandbox thất bại DNS `getaddrinfo failed`; chạy lại ngoài sandbox thành công |
| `python -m pip freeze` (trong venv) | Ghi các pin từ môi trường thực tế vào requirements; không dùng phiên bản suy đoán |
| `python -m pytest -q` lần đầu | Lỗi nội bộ pytest 9.2.0: `NodeId` thiếu `_str_cache`, chưa chạy test |
| `python -m pip install pytest==8.4.2` | Thành công; thay pin pytest bằng 8.4.2 |
| `python -m pytest -q` lần tiếp | Collection bị chặn bởi StarletteDeprecationWarning: TestClient cần httpx2; warnings được coi là lỗi |
| `python -m pip install httpx2` | Thành công; dùng httpx2 2.14.0 |
| `python -m pip show httpx httpcore certifi httpx2 httpcore2 truststore` | Kiểm tra phụ thuộc trước khi bỏ các package không còn dùng |
| `python -m pip uninstall -y httpx httpcore certifi` | Gỡ khỏi venv local; không cần cho TestClient mới |
| `python -m pytest -q` với dependency đã sửa, trong sandbox | Treo ở khởi tạo event loop; đã ngắt tiến trình, không tính là pass |
| `python -m pytest tests/test_config.py tests/test_schemas.py -q` | **49 passed in 1.03s**, exit 0 |
| `python -m pytest tests/test_app.py -vv -o faulthandler_timeout=10` | Trace chỉ ra treo tại Windows socketpair/accept; đã ngắt |
| `python -c "import asyncio; asyncio.run(asyncio.sleep(0)); print('asyncio ok')"` | Cũng treo trong sandbox; đã ngắt, xác nhận hạn chế môi trường |
| `python -m pytest -q` ngoài sandbox, cwd backend | **59 passed in 1.86s**, exit 0 |
| `python -m pip check` | **No broken requirements found.** |
| `python tests/smoke_local.py` ngoài sandbox, cwd backend | **GET /health 200/model_ready=false; POST /predict 503/model_not_ready/request_id=null**; startup complete; stopped process true; exit 0 |
| `git diff --check`, `git diff --exit-code`, `git diff --cached --exit-code` | Thành công; không có sửa đổi tracked/staged |
| `git check-ignore` với env/venv/cache/raw/private/artifact/weight/checkpoint mẫu | Các đường dẫn phải ignore được ignore |
| `git check-ignore .env.example` | Exit **1**, không output: đúng kỳ vọng, tệp ví dụ vẫn trackable |
| `python -m venv .venv/verify` | Tạo môi trường kiểm chứng sạch thành công |
| `.venv\verify\Scripts\python.exe -m pip install -r backend/requirements.txt` | Cài lại thành công cả 27 pins, exit 0 |
| `..\.venv\verify\Scripts\python.exe -m pytest -q` ngoài sandbox, cwd backend | **59 passed in 1.90s**, exit 0, từ môi trường cài sạch |
| `.venv\verify\Scripts\python.exe -m pip check` | **No broken requirements found.**, exit 0 |
| Python kiểm tra whitespace trên danh sách `git ls-files --others --exclude-standard` (trừ kế hoạch có sẵn) và `ast.parse` các tệp `.py` | **19 new files**, không trailing whitespace/thiếu newline; cú pháp Python hợp lệ |
| `Get-FileHash PLANNING_ISSUES_7_8.md,DEFINE.md,DESIGN.md -Algorithm SHA256` | Ghi nhận hash; trạng thái tracked vẫn nguyên vẹn qua `git diff --exit-code` |

Smoke chạy đúng command: `python -m uvicorn app.main:app --host 127.0.0.1
--port 8000 --no-access-log`, qua subprocess của script. Server đã dừng; test
lifespan kiểm tra cleanup bằng TestClient. Không tuyên bố forced termination của
smoke trên Windows là bằng chứng graceful shutdown.

`git diff --check` không bao gồm tệp mới untracked; đã kiểm tra riêng cả 19 tệp
mới bằng Python như ghi ở bảng. Bản cài sạch dùng đúng requirements.txt đã pass
toàn bộ 59 test; chưa kiểm tra cài đặt trên máy/OS khác.

Đã tra trang package chính thức trên [PyPI FastAPI](https://pypi.org/project/fastapi/),
[Pydantic Settings](https://pypi.org/project/pydantic-settings/),
[Pydantic](https://pypi.org/project/pydantic/), [Uvicorn](https://pypi.org/project/uvicorn/),
[pytest](https://pypi.org/project/pytest/) và [HTTPX](https://pypi.org/project/httpx/).
Phiên bản bàn giao lấy từ kết quả pip/resolver và test local, không coi thông tin
web hay `pip check` là bằng chứng tương thích ML hoặc audit bảo mật toàn diện.

## E — Trạng thái nghiệm thu và review

| Hạng mục | Trạng thái | Phần còn chờ |
| --- | --- | --- |
| A: inspect/preserve | done | Xung đột tài liệu được ghi, không tự sửa |
| B: #7 foundation local | done về triển khai local | ML thống nhất môi trường và reviewer phê duyệt trước Done issue |
| C: #8 schema/contracts | partial | Draft đã có; thông báo/review ML/Extension chưa hoàn tất |
| D: verification | done trên môi trường nêu trên | Không phải kiểm thử model, Linux/macOS hay máy demo khác |
| E: report/handoff | done | Báo cáo đúng bằng chứng; không đổi trạng thái GitHub |
| **Issue #7 DoD** | **partial** | Chưa được review và chưa xác nhận dependency ML |
| **Issue #8 DoD** | **partial** | Chưa có ML/Extension approval và các quyết định chung chưa chốt |

ML: **chưa có approval**. Extension: **chưa có approval**. Backend/owner:
**chưa có approval độc lập**. Không có PR/commit/review mới được tạo trong phiên
này. Nội dung yêu cầu review ở dưới chỉ là bản nháp local, **chưa gửi** ra GitHub
hoặc cho người khác. Không được xem các test tự động là review của ML/Extension.

| Quyết định còn mở | Owner cần xác nhận |
| --- | --- |
| Python/ML dependency manifest tương thích bộ pin backend | ML + Backend |
| Predictor nhận encoded bytes hay decoded RGB; EXIF/RGB/decode ownership | ML + Backend |
| Title/body concatenation và định nghĩa cắt 1,500 từ/text_truncated | ML |
| Xung đột tiếng Anh/tiếng Việt trong tài liệu nguồn | ML + Extension + owner |
| Whole-request 12 MiB đề xuất, overhead, duplicate/unknown parts | Backend + Extension |
| Timeout client cấu hình được, không mặc định bằng mục tiêu ~10 giây | Extension + ML |
| Health schema/status và quy tắc ready thật | Backend + ML + Extension |
| Token provisioning/rotation, error precedence, có cần phân biệt 403 không | Backend + Extension |

Các thiếu hụt trên chặn **nghiệm thu Done**, không ngăn chạy foundation local.
#9/#22/#23/#37/#38/#39 vẫn hoãn nguyên phạm vi. Không commit, không push, không
đóng issue hoặc sửa thông tin issue GitHub.

## Yêu cầu review bất đồng bộ — bản nháp chưa gửi

> Nhờ ML và Extension review contract/interface **v0.1.0** cho AFN-007/008.
> Bản thay đổi hiện chỉ ở workspace local, chưa commit/PR. Deliverables:
> `docs/api-contract.md`, `docs/inference-interface.md`, `backend/app/schemas.py`,
> DI seam và `backend/requirements.txt`. `/predict` hiện chỉ 503, health chưa ready;
> các ví dụ thành công là minh họa. Xin xác nhận các quyết định trong bảng trên,
> đặc biệt bytes/RGB, Python/ML pins, 12 MiB total multipart, timeout, health và
> token policy. Chưa có phê duyệt; chỉ đánh dấu Done sau khi review thực tế.
