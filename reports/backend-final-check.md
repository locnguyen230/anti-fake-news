# Kiểm tra bàn giao Backend — AFN-053

**26/11/2026 · kỹ thuật trên candidate PASS; nghiệm thu frozen BLOCKED bởi #49.**
Không còn hai lỗi đã tái hiện trong lượt review Backend trước. Không tuyên bố
nghiệm thu toàn hệ thống hoặc approval ML/Extension.

## Nền mã và thay đổi thực tế

HEAD trước và sau công việc vẫn là `79e3a7e85e72d6a778954b8ef42667f3190258d2`.
Đã fetch và merge `origin/main` tại `56e299e` bằng `--no-commit --no-ff`.
Xung đột duy nhất ở `docs/local-config.md` đã giải quyết theo cấu hình candidate
opt-in upstream. Merge đang chờ commit theo yêu cầu người dùng, không còn conflict.

Các tệp triển khai #52/#53 (ngoài nội dung merge):

| Tệp | Thay đổi |
| --- | --- |
| `backend/app/lifespan.py`, `backend/app/main.py` | Middleware làm sạch message `lifespan.startup.failed`/`shutdown.failed` trước khi Uvicorn log; vẫn truyền trạng thái thất bại, giữ startup fail-closed |
| `backend/app/predictor.py` | Factory `load_for_parity(bundle_dir)` gọi serving loader thật, schema/checksum/identity/warm-up đầy đủ; dùng test environment tường minh, không đọc `.env`/các biến deployment `AFN_*`; caller chịu trách nhiệm `close()` |
| `scripts/package_backend.py` | Đưa module lifespan mới vào ZIP; giữ sửa CORS của upstream |
| `backend/tests/test_lifespan_logging.py` | Regression startup subprocess thiếu model: nonzero exit, không traceback/token/path; kiểm message startup và shutdown |
| `tests/test_model_loader.py` | Kiểm hook parity, không bị deployment settings làm lệch; phục hồi sau lỗi inference bằng lifecycle mới và không dùng lại provider đã đóng |
| `scripts/benchmark_local.py`, `tests/test_benchmark_local.py` | Benchmark HTTP/resource, candidate/freeze gate, kiểm thống kê và package import độc lập |
| `reports/performance.md`, `reports/performance-candidate.json` | Phương pháp, số đo thật, raw evidence và hash mã nguồn |
| `reports/backend-validation-parity.json`, báo cáo này | Bằng chứng parity Validation, lệnh kiểm tra, ranh giới và blocker |
| `reports/backend-integration.md`, `reports/predict-smoke.md`, `docs/local-config.md` | Liên kết kết quả mới và cập nhật trạng thái handoff/logging |

Các thay đổi `.env.example`, config/loader candidate opt-in, smoke candidate,
README/deployment docs, `ml/freeze.py`, `ml/evaluate_test.py`, tests freeze/evaluate,
freeze draft và sửa `.gitignore` là **nội dung upstream**, không phải triển khai mới
#52/#53. Không chạy lệnh đánh giá Test. Không sửa byte artifact, checkpoint,
threshold, preprocessing, data manifest hoặc split.

Upstream bỏ các ignore cho dữ liệu/model. Đã thêm **local-only** exclusions vào
`.git/info/exclude` cho `data/private`, `data/raw`, ba thư mục bundle và gói release;
không stage chúng. Không chỉnh `.env`, không cài dependency, không tạo venv mới.

## Lỗi và kết quả sửa

| Vấn đề | Bằng chứng sau sửa | Trạng thái |
| --- | --- | --- |
| Production startup ném RuntimeError làm Uvicorn in traceback/path | `test_real_launcher_missing_production_model_exits_without_traceback`: tiến trình thật vẫn thất bại, log chỉ thông báo cố định, không token/path/traceback | PASS |
| Báo cáo gọi hook `load_for_parity` không tồn tại | CLI thật dùng hook chạy 32 mẫu Validation với candidate + CLIP offline; max score diff `1.2477080180151034e-07 <= 1e-6`, label/truncation/identity đều khớp, 0 lỗi | PASS |
| Restart/cleanup sau inference failure | Ca fixture gây lỗi runtime → 503/not-ready → provider cũ bỏ bundle/encoder → lifespan mới nạp provider mới và trả 200 | PASS fixture, không tính là chất lượng model |
| Gói ZIP thiếu dependency module nội bộ | Tạo ZIP, giải nén vào thư mục tạm, import `app.main` bằng subprocess từ gói đó; có CORS và lifespan, không data/`.env` | PASS |
| Demo thật sau tích hợp | Benchmark hai tiến trình mới độc lập thành công; lượt cuối 21/21 request, identity/score ổn định, health giữ ready, shutdown graceful và bỏ provider | PASS candidate, ngoài Test |

Factory bổ sung không sửa API v0.2.0 hay chữ ký `predict`. Không dùng
`ReferenceBundlePredictor` làm bằng chứng cho Backend. Factory là công cụ parity;
nó không chứng nhận freeze hoặc cho phép sử dụng bundle fixture trong production.

## Lệnh đã chạy và kết quả

Interpreter dùng chung: `.venv\issue9\Scripts\python.exe` (Python 3.13.1).

```powershell
# Trong backend/
..\.venv\issue9\Scripts\python.exe -m pytest -q -p no:cacheprovider
# 204 passed in 4.91s

# Từ gốc repo, ngoài sandbox do sandbox chặn DLL SciPy/scikit-learn/PyTorch
$env:HF_HUB_OFFLINE='1'
$env:AFN_CLIP_TESTS='1'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
.\.venv\issue9\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_model_loader.py tests/test_model_bundle.py tests/test_inference_parity.py tests/integration/test_predict.py tests/test_benchmark_local.py
# 95 passed in 95.26s; không skip

# Ca restart được bổ sung sau khi suite trên đã collect, nên chạy riêng:
.\.venv\issue9\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_model_loader.py::test_restart_recovers_from_inference_failure_without_reusing_closed_provider
# 1 passed in 4.34s

.\.venv\issue9\Scripts\python.exe -m ml.inference_parity --bundle-root backend/artifacts --manifest data/private/ml-v2/train-validation/manifest.jsonl --split data/private/ml-v2/train-validation/split.csv --image-root data --configurations multimodal --predictor app.predictor:load_for_parity --offline --out cache/afn-053/validation-parity.json
# Exit 0: n=32, max|diff|=1.25e-07, errors=0, PASS [VALIDATION_ONLY]

.\.venv\issue9\Scripts\python.exe -m pip check
# No broken requirements found
git -c core.safecrlf=false diff --check
git -c core.safecrlf=false diff --cached --check
# Không lỗi whitespace
```

Các lượt test tập trung trước đó: 49 lifecycle/config/CORS/adapter và 11 benchmark/
package đều PASS (trùng phạm vi suite trên, không cộng thành test mới).
Lần chạy root suite trong sandbox bị 3 lỗi collection do DLL `Access is denied`;
chạy lại ngoài sandbox đạt 95 test. Đây là hạn chế môi trường, không bỏ qua test.
Benchmark và phiên bản harness cuối: xem [performance.md](performance.md).

Raw parity được sao chép nguyên bản sang
[backend-validation-parity.json](backend-validation-parity.json).
153 Train/32 Validation và các hash dữ liệu đã khớp artifact; không nạp payload
`qa-only`. Parity xác nhận tính nhất quán triển khai, không phải accuracy/F1.

## Blocker còn lại, owner và trạng thái review

Đã chạy chỉ đọc:

```powershell
.\.venv\issue9\Scripts\python.exe -m ml.freeze verify --bundle-root backend/artifacts --manifest data/private/ml-v2/train-validation/manifest.jsonl --split data/private/ml-v2/train-validation/split.csv
```

Exit **1**: thiếu chữ ký ML/QA, trạng thái draft, record còn blocker, config/selection
và một số code hash không khớp. Chẩn đoán byte chỉ đọc cho thấy config, selection,
model_bundle, clip-reference và phần lớn mã ML khớp hash khi chuyển **CRLF → LF**
trong bộ nhớ. Git xác nhận index LF/worktree CRLF. `ml/freeze.py` đã khác snapshot
nháp và `ml/evaluate_test.py` trước đó chưa có hash. Không tự sửa file hay đổi
protocol để làm gate xanh.

| Điều kiện còn mở | Owner | Hành động cần thiết |
| --- | --- | --- |
| Freeze draft chưa signed, protocol còn proposed/audit chưa chốt | ML `0xDa1Vu`, QA `dangnguyen0512`, Integration/DATA theo #49 | Hoàn tất gate, thống nhất chính sách hash/line endings, collect snapshot đúng, ký cùng record, bàn giao bundle frozen |
| Benchmark và regression trên đúng artifact frozen | Backend + ML reviewer | Chạy lại sau #49; số đo candidate hiện tại không thay nghiệm thu cuối |
| ML approval cho #52/#53 | ML | Review code, parity và số đo; hiện chưa có approval được xác minh |
| Extension E2E và approval liên quan | Extension/QA | Ngoài lượt Backend này; không tuyên bố đã chạy browser E2E |
| `ml.inference_parity --fixture` gán `experiment_config_sha256="fixture"` sai schema | ML/#36 | Lỗi đã ghi nhận từ trước, chưa sửa ML-owned harness; đường `--bundle-root` thật vừa kiểm chứng PASS |

Không có commit/push/PR mới hoặc thay đổi trạng thái issue trong lượt này. Không ký
thay ML/QA, không mở Test và không đưa hai issue sang Done khi gate cuối còn thiếu.
