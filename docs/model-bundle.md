# Gói mô hình `afn-model-bundle-v1`: bàn giao cho Backend (#24, #37)

Loader AFN-024 dùng trực tiếp schema v1 của AFN-035. Gói fixture được huấn luyện trên
dữ liệu tổng hợp và dùng cho kiểm thử dev/test. AFN-035 đã xuất các ứng viên
Train/Validation từ dataset `ml-v2`. Xem [báo cáo xuất ứng viên](../reports/ml-candidates-v2.md).

## 1. Tạo gói trên máy bạn

Bundle sinh ra được Git bỏ qua. Schema dùng chung được theo dõi tại
[`backend/artifacts/metadata.schema.json`](../backend/artifacts/metadata.schema.json).
Để tự tạo bundle fixture, dùng cache CLIP từ AFN-006:

```sh
.venv/bin/python -m ml.export_artifacts --fixture --offline
.venv/bin/python scripts/smoke_bundle.py --bundle cache/ml-fixture-bundles/multimodal --offline
```

Kết quả:

```
cache/ml-fixture-bundles/
  label_map.json          {"0": "real", "1": "fake"}, positive_label fake
  export-report.json      parity khi xuất (Validation), model_version từng gói
  text_only/  image_only/  multimodal/
```

Chế độ xuất candidate thật mặc định ghi vào `backend/artifacts/` (`text_only/`, `image_only/`,
`multimodal/`, `label_map.json`, `export-report.json`; các file khác như `metadata.schema.json` được giữ).
Bộ xuất chỉ đưa cả ba gói vào sau khi kiểm tra parity xong. Nếu thư mục đã có gói thì phải thêm
`--replace`; khi thay bị lỗi, gói cũ được khôi phục. Gói fixture không bao giờ đè lên gói thật.
Thêm `--expect-selected configs/selected-models.json` để bắt buộc C/ngưỡng khớp với lựa chọn của #34.

Khi thử fixture, đặt `AFN_ENVIRONMENT=test`, `AFN_PREDICTOR_MODE=real` và
`AFN_MODEL_ARTIFACT_PATH=cache/ml-fixture-bundles/multimodal`. Với candidate thật,
trỏ cấu hình tới thư mục `multimodal` của lần xuất đã kiểm định.

## 2. Nội dung một gói

| File | Nội dung |
| --- | --- |
| `metadata.json` | Mọi thông tin bên dưới, kèm `files` (sha256 + bytes của từng file) |
| `classifier/coef.npy`, `classifier/intercept.npy` | Logistic Regression, float64, shape `(1, feature_dim)` và `(1,)` |
| `text/vocabulary.json`, `text/idf.npy` | TF-IDF đã fit trên Train (chỉ có ở text-only và multimodal) |

**Không dùng pickle/joblib.** Mảng được nạp bằng `allow_pickle=False`, nên nạp gói không bao giờ chạy code lạ.
**CLIP không được đóng gói** (`image.packaged: false`). Metadata ghim repo, revision, hash processor
và `preprocess_version`; service phải nạp đúng encoder đó từ cache Hugging Face.

Các trường chính của `metadata.json`:

| Trường | Ý nghĩa |
| --- | --- |
| `configuration` | `text-only` / `image-only` / `multimodal` |
| `model_id`, `model_version` | Trả thẳng trong `PredictResponse`. Version chứa hash nội dung; gói fixture có hậu tố `-fixture` |
| `status` | `candidate` cho tới khi #49 khóa (`frozen`) |
| `is_fixture`, `evidence_kind` | `true` và `FIXTURE_SMOKE_NOT_RESEARCH` với gói fixture |
| `classes`, `label_map`, `positive_label` | `[0, 1]`, `{"0": "real", "1": "fake"}`, `fake` |
| `threshold`, `threshold_comparison` | Ngưỡng chọn trên Validation; `fake` nếu `fake_score >= threshold` |
| `feature_dim`, `text.dim`, `image.dim`, `fusion` | Số chiều và thứ tự ghép `[text, image]`, float64 |
| `preprocess_version` | Phải bằng `PREPROCESS_VERSION` của service, nếu không thì từ chối |
| `training` | Seed, số mẫu, hash manifest/split/config, hash thứ tự Train |
| `test_predictions_included` | Luôn `false` |

## 3. Nạp và warm-up ở Backend

1. Cài `backend/requirements.txt` và `ml/requirements.txt` vào cùng môi trường Python.
2. Chuẩn bị cache CLIP theo [AFN-006](ml-environment.md). Nếu dùng cache ngoài repo,
   đặt `HF_HOME` tới thư mục cha của `hub`. Backend đọc cache ở chế độ offline.
3. Cấu hình thư mục bundle multimodal tin cậy và token demo. Khởi chạy
   `python -m app` từ `backend/`, kiểm tra `GET /health` rồi thử multipart mẫu trong
   [hợp đồng API](api-contract.md).

`app.model_loader.load_predictor` dùng reader và schema v1 để xác thực metadata,
checksum, chiều/kiểu mảng, classes, ánh xạ nhãn và ngưỡng. Encoder dùng chung ở
`backend/app/clip_encoder.py` đối chiếu checkpoint, hash processor và chiều/dtype với bundle.
Warm-up chạy một lần bằng PNG tổng hợp trước khi công bố `ready`. TF-IDF dùng từ vựng
và IDF đã xuất, classifier dùng các hệ số đã fit trên Train. Bundle chỉ lấy từ thư mục
do người vận hành cấu hình, còn multipart chỉ nhận nội dung bài và ảnh.

| Trạng thái hoặc lỗi | Phản hồi |
| --- | --- |
| Bundle thiếu hoặc không tương thích, CLIP thiếu cache hoặc warm-up thất bại | Health báo `error`, request hợp lệ nhận 503 `model_not_ready` |
| Nội dung rỗng sau chuẩn hóa hoặc ảnh không đọc được | 400 `invalid_input`, model giữ trạng thái hiện tại |
| Embedding sai dtype/chiều hoặc lỗi chấm điểm | 503 `model_not_ready`, adapter chuyển sang `error` |

HTTP trả mã lỗi chuẩn và UUID đã xác thực. Khởi động lại Backend để nạp lại bundle.

## 4. Đã kiểm tra

- **Parity khi xuất:** nạp lại gói từ đĩa, tính lại điểm Validation từ text thô và embedding, so với
  `predict_proba` của scikit-learn: sai lệch tối đa 0,0, nhãn trùng 100% cho cả 3 gói (ngưỡng cho phép 1e-9).
- `tests/test_model_bundle.py`: TF-IDF của gói khớp `TfidfVectorizer.transform` trên text chưa thấy;
  `text_truncated` đúng; gói bị sửa coef, nhét pickle, sai threshold/label_map/`preprocess_version`/thứ tự ghép,
  thiếu file, lệch encoder đều bị từ chối; thông điệp lỗi không lộ đường dẫn; export từ chối dữ liệu có Test.
  Kiểm thử hồi quy xác nhận metadata thiếu hoặc sai kiểu báo `BundleError` và lần xuất lỗi giữ nguyên bundle đã dùng.
- `tests/test_model_loader.py` chạy startup, hai request, shutdown và các ca lỗi trên
  bundle sinh bởi exporter. [Hướng dẫn fixture và smoke CLIP](../tests/fixtures/loader/README.md).
- `scripts/smoke_bundle.py` (macOS M1, CPU, CLIP thật, input tổng hợp, sau khi nạp model):

| Gói | Nạp gói + CLIP | 1 request (trung vị / max, 20 lượt) |
| --- | --- | --- |
| multimodal | ~4,0 s | 42,5 / 53,1 ms |
| text-only | ~0,7 s | 0,2 / 0,4 ms |

## 5. Còn mở

| Việc | Owner |
| --- | --- |
| Review lifecycle Backend và schema đã dùng | Backend (#24) |
| Audit độc lập split `ml-v2` trước khi khóa ứng viên | DATA/QA (#29, #49) |
| Parity và tích hợp ứng viên qua Predictor của dịch vụ | ML/Backend (#37–39) |
