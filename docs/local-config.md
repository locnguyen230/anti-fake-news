# Cấu hình chạy local, CORS, token và vòng đời sẵn sàng — AFN-038

Tài liệu mô tả cấu hình chạy local của dịch vụ Backend (`127.0.0.1:8000`), chính sách CORS
cho Chromium Extension, xác thực `X-Demo-Token`, vòng đời nạp/warm-up mô hình và nguyên tắc
bảo mật log/lỗi. Hợp đồng HTTP chi tiết xem tại [docs/api-contract.md](api-contract.md) và
định dạng gói mô hình tại [docs/model-bundle.md](model-bundle.md).

## 1. Biến môi trường (`backend/app/config.py`)

`Settings` đọc tệp `.env` ở thư mục gốc repo; biến môi trường của tiến trình luôn được ưu tiên
hơn `.env`. Mọi giá trị không hợp lệ đều chặn khởi động trước khi bind cổng.

| Biến | Mặc định | Ràng buộc và hành vi |
| --- | --- | --- |
| `AFN_HOST` | `127.0.0.1` | Chỉ cho phép loopback (`127.0.0.1`, `::1`, `localhost`). Từ chối `0.0.0.0` hoặc IP mạng LAN. |
| `AFN_PORT` | `8000` | Số nguyên `1..65535`. |
| `AFN_ENVIRONMENT` | `demo` | `production`, `demo`, `dev` hoặc `test`. Chỉ `dev` và `test` cho phép mock hoặc bundle fixture. |
| `AFN_PREDICTOR_MODE` | `real` | `real` hoặc `mock`. Chế độ `mock` yêu cầu đồng thời `AFN_ENVIRONMENT=dev` hoặc `test`. |
| `AFN_DEMO_TOKEN` | *(trống)* | Secret cục bộ (`SecretStr`, ẩn khỏi `repr`/JSON). Để trống sẽ từ chối mọi `POST /predict` với `401 invalid_token` (kể cả `mock`). |
| `AFN_EXTENSION_ORIGIN` | *(trống)* | Khớp chính xác `^chrome-extension://[a-p]{32}$` (không wildcard `*`, không `http`/`https`, không path). Để trống sẽ không cấp CORS cho bất kỳ origin nào. |
| `AFN_MODEL_ARTIFACT_PATH` | `artifacts/model` | Đường dẫn thư mục bundle Multimodal (tương đối theo gốc repo hoặc tuyệt đối), ẩn khỏi `repr`. Trỏ tới `backend/artifacts/multimodal` khi chạy candidate thật. |
| `AFN_MODEL_METADATA_SHA256` | *(trống)* | SHA-256 của `metadata.json` trong bundle được chọn. Bắt buộc ở `production` cùng với token. |
| `AFN_ALLOW_CANDIDATE_MODEL` | `false` | Cho phép bundle thật trạng thái `candidate` ở production khi đặt `true`. |
| `AFN_MAX_REQUEST_BYTES` | `12582912` (12 MiB) | Trần toàn bộ HTTP body (gồm overhead multipart), phải lớn hơn 10 MiB (`IMAGE_MAX_BYTES`). |
| `HF_HOME` | `cache/huggingface` | Biến môi trường Hugging Face (ngoài `AFN_`). Trỏ tới thư mục cha của `hub/` chứa cache CLIP đã ghim. |
| `HF_HUB_OFFLINE` | *(khuyến nghị `1` ở demo)* | `ClipImageEncoder` ở Backend luôn gọi `offline=True` (`local_files_only=True`); đặt `HF_HUB_OFFLINE=1` tăng cường bảo vệ không gọi mạng. |

## 2. Chính sách CORS và tách biệt với xác thực token

`LocalCORSMiddleware` (`backend/app/cors.py`) bọc ngoài `RequestLimitsMiddleware` để trình duyệt
của Extension được phép đọc cả phản hồi thành công lẫn JSON lỗi `400/401/413/503`.

- **Origin được phép:** chỉ đúng một chuỗi trong `AFN_EXTENSION_ORIGIN` (hoặc danh sách rỗng nếu chưa đặt).
- **Phương thức:** `GET`, `POST` (preflight `OPTIONS` được xử lý tự động bởi `CORSMiddleware`).
- **Header yêu cầu:** `X-Demo-Token`, `Content-Type` (cùng các CORS-safelisted headers).
- **Header công khai cho JS:** `X-AFN-Inference-Mode`, `X-AFN-Model-State`.
- **Credentials:** `allow_credentials=False`; `max_age=600` giây.
- **Origin khác:** không nhận header `Access-Control-Allow-Origin`; preflight `OPTIONS` bị từ chối với HTTP `400`.

> **Lưu ý bảo mật quan trọng:** CORS là chính sách do **trình duyệt** thực thi nhằm kiểm soát
> origin nào được gửi yêu cầu cross-origin và đọc phản hồi trong ngữ cảnh trình duyệt. CORS
> **không** chặn được các HTTP client ngoài trình duyệt (ví dụ `curl`, script Python hoặc tiến
> trình cục bộ khác có thể tự giả mạo hoặc bỏ qua header `Origin`). Do đó:
>
> 1. `POST /predict` **luôn** kiểm tra `X-Demo-Token` bằng `hmac.compare_digest` trước khi đọc body, kể cả khi `Origin` khớp `AFN_EXTENSION_ORIGIN`.
> 2. Preflight `OPTIONS` không mang token theo chuẩn trình duyệt, nhưng yêu cầu `POST /predict` thực tế ngay sau đó vẫn phải có `X-Demo-Token` hợp lệ.
> 3. Dịch vụ chỉ bind loopback (`127.0.0.1`) để hạn chế phạm vi tiếp cận mạng.

## 3. Vòng đời nạp mô hình, warm-up và readiness

Quá trình khởi động chạy qua FastAPI `lifespan` (`backend/app/main.py` → `app.inference_adapter.create_adapter` → `app.model_loader.load_predictor`):

1. **Không nạp khi import:** import `app.main` hoặc `app.model_loader` không đọc ổ đĩa, không nạp CLIP và không cấp phát mô hình.
2. **Xác thực bundle trước khi nạp encoder:**
   - Kiểm tra cấu hình `multimodal`, JSON Schema `backend/artifacts/metadata.schema.json`, checksum SHA-256 và kích thước từng tệp `.npy`/`.json` (nạp `allow_pickle=False`).
   - Kiểm tra `preprocess_version == afn-preprocess-v1`, `classes`, `label_map`, `threshold`, chiều TF-IDF/CLIP và thứ tự ghép `[text, image]`.
   - Từ chối bundle fixture (`is_fixture: true`) khi `AFN_ENVIRONMENT=demo`.
3. **Nạp CLIP offline và đối chiếu danh tính:** `ClipImageEncoder(offline=True)` nạp đúng `repo_id`, `revision` và `processor_config_sha256` đã ghim trong `configs/clip-reference.json` từ cache cục bộ; không gọi mạng, không fine-tune (`eval()`, `requires_grad_(False)`).
4. **Warm-up tổng hợp:** chạy một lượt `BundlePredictor.predict` với ảnh PNG tổng hợp 32×32 trước khi công bố sẵn sàng.
5. **Trạng thái `GET /health`:**
   - `not_loaded` (`model_ready: false`): chưa cấu hình `AFN_MODEL_ARTIFACT_PATH` và đường dẫn mặc định không tồn tại.
   - `ready` (`model_ready: true`): nạp, kiểm tra và warm-up hoàn tất.
   - `error` (`model_ready: false`): startup thất bại hoặc lỗi runtime trong lúc suy luận.
6. **Chống pipeline nạp dở và không fallback mock:**
   - Khi kiểm tra encoder hoặc warm-up thất bại, `load_predictor` đóng predictor vừa tạo. `InferenceAdapter` ghi nhận `ModelState.ERROR` và giữ chế độ suy luận đã cấu hình.
   - Mọi `POST /predict` hợp lệ khi adapter không ở trạng thái `ready` đều nhận `503 model_not_ready` (với `request_id` đã xác thực).
   - Ở `production`, adapter phải sẵn sàng thì dịch vụ mới khởi động thành công.
   - Khi shutdown, `lifespan` gọi `adapter.close()` trong threadpool để giải phóng tham chiếu `CLIPModel`/`CLIPImageProcessor` và bundle.
   - Các lời gọi CPU suy luận được tuần tự hóa qua `RLock` trong `InferenceAdapter`, tránh race giữa request đồng thời và đóng/báo lỗi.
   - Muốn phục hồi sau `error` phải khắc phục artifact/cache và khởi động lại dịch vụ.

## 4. Vệ sinh log và thông điệp lỗi

- Launcher `python -m app` (`backend/app/__main__.py`) chạy Uvicorn với `access_log=False`; khi cấu hình sai, chỉ in thông báo chung `"Invalid AFN configuration; check .env and environment values."` (ẩn giá trị đầu vào nhờ `hide_input_in_errors=True`).
- `SanitizedLifespanMiddleware` thay message lỗi startup/shutdown bằng thông báo cố định trước khi Uvicorn ghi log; startup lỗi vẫn không nhận request và launcher thoát thất bại. Không bật traceback để chẩn đoán artifact.
- `GET /health` và mọi phản hồi lỗi `400/401/413/503` chỉ trả schema cố định (`HealthResponse`, `ErrorResponse`) kèm header `Cache-Control: no-store`.
- Không ghi hoặc trả lại nội dung bài báo, byte ảnh, tên tệp upload, `AFN_DEMO_TOKEN`, đường dẫn máy cục bộ, thông điệp ngoại lệ nội bộ hay stack trace.
- Không đưa `.env`, artifact, cache hoặc dữ liệu private vào gói bàn giao. Kiểm tra danh sách tệp trước khi stage; checkout này bảo vệ dữ liệu/model qua Git local excludes.

## 5. Cách chạy cục bộ (Windows x64 / Python 3.13)

### 5.1. Cài đặt môi trường dùng chung (Backend + ML)

```powershell
# Tạo mới hoặc tái sử dụng venv Python 3.13 hiện có (trong checkout này: .venv\issue9)
.\.venv\issue9\Scripts\python.exe -m pip install -r backend/requirements.txt -r ml/requirements.txt
.\.venv\issue9\Scripts\python.exe -m pip check
```

### 5.2. Chuẩn bị cache CLIP cục bộ (một lần)

```powershell
# Tải đúng revision đã ghim vào cache/huggingface/hub và kiểm tra 16/16 check
.\.venv\issue9\Scripts\python.exe scripts/smoke_clip.py
# Xác nhận nạp lại hoàn toàn offline
.\.venv\issue9\Scripts\python.exe scripts/smoke_clip.py --offline
```

### 5.3. Cấu hình `.env` cho demo với candidate Multimodal thật

Sao chép `.env.example` sang `.env` (nếu chưa có) và đặt cục bộ (không commit `.env`):

```ini
AFN_HOST=127.0.0.1
AFN_PORT=8000
AFN_ENVIRONMENT=demo
AFN_PREDICTOR_MODE=real
AFN_DEMO_TOKEN=<secret-cuc-bo-cua-ban>
AFN_EXTENSION_ORIGIN=chrome-extension://<32-ky-tu-id-extension-that>
AFN_MODEL_ARTIFACT_PATH=backend/artifacts/multimodal
AFN_MAX_REQUEST_BYTES=12582912
```

### 5.4. Khởi động và kiểm tra nhanh

```powershell
$env:HF_HUB_OFFLINE = "1"
Push-Location backend
..\.venv\issue9\Scripts\python.exe -m app
Pop-Location
```

Kiểm tra health và preflight CORS (PowerShell):

```powershell
# Kiểm tra sẵn sàng
curl.exe -i http://127.0.0.1:8000/health

# Kiểm tra preflight từ origin Extension được cấu hình
curl.exe -i -X OPTIONS http://127.0.0.1:8000/predict `
  -H "Origin: chrome-extension://<32-ky-tu-id-extension-that>" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: X-Demo-Token"
```

Chạy kiểm thử tự động liên quan:

```powershell
# Unit + CORS + adapter tests
Push-Location backend
..\.venv\issue9\Scripts\python.exe -m pytest -q
Pop-Location

# Loader + bundle + parity + integration tests
.\.venv\issue9\Scripts\python.exe -m pytest -q tests/test_model_loader.py tests/test_model_bundle.py tests/test_inference_parity.py tests/integration/test_predict.py
```
