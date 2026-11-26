# AFN-024 · Fixture vòng đời model

`tests/test_model_loader.py` tạo một bundle multimodal trong thư mục tạm bằng exporter AFN-035, dữ liệu tổng hợp và `FakeImageEncoder`. Bundle gồm metadata v1, từ vựng TF-IDF, IDF và hệ số classifier. Trọng số CLIP, dữ liệu nghiên cứu và file nhị phân sinh ra nằm ngoài fixture được theo dõi trong Git.

Test chạy qua FastAPI lifespan và `/health`, `/predict`. Bộ test kiểm tra warm-up, tái sử dụng encoder qua nhiều request, và trạng thái khi bundle bị thiếu, sai schema, sai kích thước, sai mapping, sai checksum hoặc lệch encoder.

```sh
python -m pytest -q tests/test_model_loader.py
```

Để thử với CLIP đã cache, dùng lệnh tạo bundle fixture trong [hướng dẫn bàn giao](../../../docs/model-bundle.md), rồi chạy Backend với `AFN_ENVIRONMENT=test`, `AFN_PREDICTOR_MODE=real` và đường dẫn đến thư mục `multimodal` do exporter tạo. `HF_HOME` trỏ đến thư mục cha của `hub` khi dùng cache ngoài repo.

Ngày 25/11/2026, Windows/Python 3.13, smoke với CLIP thật từ cache đã nạp
`multimodal-20261125-b696e27eac86-fixture`. Sau warm-up, `/health` báo `ready`
và một request multipart với PNG tổng hợp trả 200, đúng UUID và định danh fixture.
Lifespan chuyển về `not_loaded` khi shutdown.
