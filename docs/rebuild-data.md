# Tái tạo dữ liệu FakeNewsNet · AFN-033

Chạy lệnh từ thư mục gốc repo. Ghi commit của mã, commit FakeNewsNet và SHA-256
của bốn CSV, phiên bản Python, môi trường phụ thuộc và phiên bản tập dữ liệu
trước khi bắt đầu. Dùng thư mục `data/private/` hoặc một kho riêng được DATA
phê duyệt. Các đường dẫn trong lệnh dưới đây là ví dụ.

## 1. Lấy lại snapshot hoặc thu hồi nguồn

**Đối chiếu một phiên bản đã bàn giao.** Lấy bản snapshot và `SHA256SUMS` từ
DATA qua kho được cấp quyền. Lấy hash của snapshot chốt từ biên bản DATA
độc lập với gói, rồi đối chiếu cả bốn mốc.

```text
python scripts/verify_recovery_snapshots.py --checksums data/private/recovery/SHA256SUMS --final data/private/recovery/valid-400.jsonl --expected-final-sha256 <sha256-snapshot-tu-DATA> data/private/recovery/snapshot-228.jsonl data/private/recovery/snapshot-300.jsonl data/private/recovery/snapshot-350.jsonl data/private/recovery/snapshot-400.jsonl
```

Nếu còn snapshot cuối và thứ tự hoàn thành gốc, có thể dựng lại các mốc bằng
`scripts/build_recovery_snapshots.py`. Với cùng file và mã, có thể đối chiếu
byte, ID, quyết định lọc và split. [Bàn giao recovery và cách tái dựng](../reports/data-validation.md#tạo-lại-gói-snapshot-khi-đủ-bằng-chứng-gốc)

**Thu hồi mới từ URL.** Dùng bốn CSV của commit FakeNewsNet đã ghi. Trong một
venv riêng cho recovery, cài `requests`, chuẩn bị checkout upstream có
`code/main.py` và file cấu hình credential cục bộ theo yêu cầu của script
upstream. Script dự án chọn `news_articles`; giữ credential ngoài repo này.

```text
python scripts/recover_data.py --repo <checkout-FakeNewsNet> --dataset-dir <thu-muc-bon-CSV>
```

Kết quả tại `fakenewsnet_raw_output/<checksum-CSV>/` và
`validation_reports/` của checkout FakeNewsNet. Từ lượt mới, DATA đối chiếu
URL, nội dung, ảnh, quyền sử dụng và tạo snapshot/quyết định mới. URL và nội
dung có thể thay đổi hoặc biến mất, nên lượt thu hồi mới không bảo đảm tái tạo
đúng bộ byte cũ. [Báo cáo thu hồi](../reports/recovery-summary.md)

## 2. Xác thực, gom nhóm và chia tập theo v1

Dùng venv chung Python 3.13 với `backend/requirements.txt` và
`ml/requirements.txt`. Cung cấp một dòng quyết định JSONL cho mỗi ID trong
snapshot và thư mục ảnh có SHA-256 khớp manifest. Kiểm tra quyền và lý do loại
theo [schema v1](../data/manifest.schema.json). Tạo các thư mục đầu ra mới.

```text
python -m scripts.validate_manifest --decisions data/private/recovery/decisions.jsonl --snapshot data/private/recovery/valid-400.jsonl --snapshot-sha256 <sha256-snapshot-tu-DATA> --image-root <thu-muc-anh> --out data/private/validated-v1
python -m scripts.group_samples --manifest data/private/validated-v1/manifest.jsonl --manifest-sha256 <sha256-manifest-tu-validation.json> --image-root <thu-muc-anh> --out data/private/grouped-v1
python -m scripts.split_data --manifest data/private/validated-v1/manifest.jsonl --groups data/private/grouped-v1/groups.json --groups-sha256 <sha256-groups-da-duyet> --audit data/private/grouped-v1/grouping-audit.json --image-root <thu-muc-anh> --out data/private/dataset-v1 --version v1
```

QA duyệt `grouping-audit.json` và hash của `groups.json` trước lệnh chia.
Sau đó đối chiếu `validation.json` và `qa-only/split-summary.json`. Ghi
checksum, quy tắc nhóm, seed 42, số nhóm/nhãn/nguồn, tỷ lệ thực tế và lý do
lọc. Bàn giao riêng `train-validation/` cho ML. `qa-only/` chứa payload
đầy đủ và chỉ được cung cấp cho người được phân quyền. [Audit gom nhóm](../reports/grouping-audit.md) ·
[Chia nhóm](../reports/split-summary.md)

Bản Train/Validation `ml-v2` đã công bố được tạo từ bản xuất DATA khác schema
bằng `ml.prepare_dataset`. Khi cần tái tạo đúng bản đó, dùng đầu vào và lệnh
đã ghi trong báo cáo AFN-034, rồi đối chiếu hash đầu ra với
`configs/selected-models.json`. Chạy qua QA để bảo vệ payload Test.
[Bản ml-v2](../reports/ml-train-validation.md) ·
[Hash Train/Validation](../configs/selected-models.json)

## 3. Bàn giao metadata

Lưu trong kho riêng bảng ánh xạ phiên bản, commit, vị trí gói được phân quyền
và SHA-256. Bản chia sẻ do DATA duyệt có thể dùng cột
`sample_id,source,source_id,label,group_id,split` cho các ID được phép công bố.
Trước freeze, chỉ chia sẻ thống kê Test được QA cho phép. Dùng checksum đối
chiếu độc lập với bản tải về, ví dụ `Get-FileHash <file> -Algorithm SHA256`
trên PowerShell hoặc `sha256sum <file>` trên Linux. Khi dữ liệu hoặc quyết định
thay đổi, tạo phiên bản mới và giữ bản cũ để truy vết.

Tài liệu chờ DATA `locnguyen230` bàn giao counts và checksum bản audit cuối.
[#31](https://github.com/ngnsusinn/anti-fake-news/issues/31) ·
[#32](https://github.com/ngnsusinn/anti-fake-news/issues/32)
