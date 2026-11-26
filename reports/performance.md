# Độ trễ và tài nguyên Backend — AFN-052

Đo ngày **26/11/2026, 09:49:55 Asia/Saigon** (JSON dùng UTC). Trạng thái:
**PASS kỹ thuật trên candidate thật; BLOCKED nghiệm thu frozen #49**.
Số đo gốc và hash từng tệp runtime/harness nằm trong
[performance-candidate.json](performance-candidate.json).

## Máy, artifact và phạm vi

- Máy checkout hiện tại: Windows 11 `10.0.26300`, CPU Intel64 Family 6 Model 126
  Stepping 5, 8 logical CPUs, RAM vật lý 12 GiB. Chưa có xác nhận đây là cấu hình
  máy bàn giao cuối cùng. Python 3.13.1, CPU, `torch.set_num_threads(4)`.
- Runtime: FastAPI 0.162.5, Uvicorn 0.54.0, torch 2.15.0, transformers 5.24.0,
  scikit-learn 1.9.1, NumPy 2.5.5, SciPy 1.18.1, Pillow 13.0.0. Không thêm dependency.
- Multimodal `multimodal-20261125-105d5f14e79a`, `is_fixture=false`,
  `status=candidate`; metadata SHA-256
  `a89325bcbb54f714c137c835253d741feef857b6d80d6550de70e9ad59869dd1`.
- CLIP `openai/clip-vit-base-patch32@3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`,
  cache offline. Worker ép `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.
- Một tiến trình Backend mới, `production` với candidate opt-in và metadata pin;
  bind loopback bằng socket do worker sở hữu. Supervisor dùng token ngẫu nhiên,
  không ghi token vào JSON. Không chạy pytest/parity đồng thời với lượt đo cuối.
- Chỉ dùng văn bản tiếng Anh và PNG RGB 160×120 tổng hợp cố định. Không đọc dữ liệu
  nghiên cứu Test; không dùng kết quả này để đánh giá chất lượng dự đoán.

## Lệnh đã chạy

Từ gốc repo, PowerShell:

```powershell
.\.venv\issue9\Scripts\python.exe scripts/benchmark_local.py --bundle backend/artifacts/multimodal --candidate --repeat 20 --threads 4 --out cache/afn-052/candidate-benchmark-final.json
```

Exit **0**. Sao chép JSON nguyên bản sang `reports/performance-candidate.json`.
Lượt đầu trong sandbox không khởi động được worker do hạn chế DLL; lượt đo này chạy
ngoài sandbox. Có một lượt thử trước khi bổ sung inventory/hash vào harness:
startup 18,440 s, server median 112 ms; không trộn số đo hai lượt.

## Kết quả

| Phạm vi | Số đo |
| --- | ---: |
| Tạo tiến trình → HTTP health ready, gồm import/load/warm-up và polling | 12.665 ms |
| Import runtime và cấu hình số thread | 3.635 ms |
| Loader tổng, gồm warm-up | 8.461 ms |
| Loader trừ warm-up, gồm kiểm metadata/identity và nạp bundle/encoder | 8.260 ms |
| Nạp bundle (thành phần của loader) | 1.955 ms |
| Nạp CLIP offline (thành phần của loader) | 6.283 ms |
| Warm-up startup | 201,04 ms |
| HTTP request đầu, sau warm-up: server / HTTP | 121 / 126,41 ms |
| 20 request sau: server min / median / p95 / max | 103 / 110 / 116 / 117 ms |
| 20 request sau: HTTP min / median / p95 / max | 107,61 / 118,79 / 132,99 / 135,62 ms |
| Working set baseline / sampled peak của worker | 29,06 / 767,09 MiB |
| CPU worker, user + system tích lũy | 21,375 CPU-seconds |
| Wall-time cửa sổ giám sát tài nguyên | 15,095 s |
| CPU trung bình, quy ước một logical CPU = 100% | 141,60% |

Trong bảng dùng dấu chấm phân cách hàng nghìn và dấu phẩy cho phần thập phân.
JSON giữ số thực nguyên bản. p95 dùng nearest-rank. **Mục tiêu median dưới 10 giây
sau load: PASS trên fixture này**. Startup vượt 10 giây nhưng không thuộc mục tiêu
request sau load; phần lớn thời gian nằm ở import và nạp CLIP.

`processing_time_ms` do API đo quanh lời gọi Predictor, loại trừ model load và
transport validation. HTTP đo từ gửi request tới đọc xong JSON, gồm validation và
truyền phản hồi; tạo fixture/multipart ở client nằm ngoài khoảng đo. Request đầu
được tách khỏi 20 request sau, nhưng vẫn diễn ra **sau startup warm-up**.
Các khoảng startup/loader/CLIP có phần bao nhau, không cộng tất cả các dòng.
OS file cache không bị xóa, nên đây không phải phép đo cold disk-cache.

Tài nguyên chỉ tính worker Backend, không cộng supervisor. RSS/working set được
lấy mẫu mỗi 50 ms (255 mẫu), có thể bỏ lỡ đỉnh ngắn hơn. CPU bao gồm import,
startup, suy luận, khoảng chờ và shutdown; vượt 100% là bình thường với nhiều core.
Worker thoát **0**, predictor được giải phóng và readiness trở về false. Không phát
hiện token, đường dẫn checkout/artifact hoặc traceback trong log lượt thành công.
Đây không phải bài kiểm tra rò bộ nhớ kéo dài hay kiểm thử tải đồng thời.

## Nghiệm thu và chạy lại

Harness dùng đúng serving loader, warm-up và API; các wrapper đo thời gian chỉ có
trong worker benchmark. Không đổi preprocessing, checkpoint, threshold hay pipeline.
Kết quả lặp lại nhất quán trên 21 request, đủ schema và đúng model ID/version.

Để đo bản cuối, ML/QA phải hoàn tất freeze và bàn giao bundle frozen cùng hồ sơ
signed khớp hash. Sau đó chạy **không có `--candidate`**:

```powershell
.\.venv\issue9\Scripts\python.exe scripts/benchmark_local.py --bundle backend/artifacts/multimodal --freeze release/model-freeze.json --repeat 20 --threads 4 --out cache/afn-052/frozen-benchmark.json
```

Lệnh này là hướng dẫn tương lai, **chưa chạy**. Harness gọi `ml.freeze.verify`
với yêu cầu signed; chỉ đổi metadata thành `frozen` không đủ vượt gate.
Hiện hồ sơ là draft, chưa có ML/QA signoff và còn hash mismatch (chi tiết tại
[backend-final-check.md](backend-final-check.md)). ML là reviewer của #52;
chưa có approval. Không chờ hay chạy #50/Test để đo benchmark.
