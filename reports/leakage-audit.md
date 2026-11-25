# AFN-029 · Audit độc lập split và giao thức Train/Validation

**25/11/2026 · BLOCKED cho nghiệm thu.** Đã tái dựng và đối chiếu đúng phiên bản
`ml-v2` dùng cho lượt Validation `20261125T145232Z`. Các phép kiểm có đầu vào
đều đạt. Bản xuất thiếu metadata publisher và event ID nên chưa đủ bằng
chứng để kết luận về rò rỉ theo các quan hệ đó. Audit này diễn ra sau lượt
#34 đã công bố và không thể thay cho sign-off trước tuning.
[Báo cáo ML](ml-train-validation.md) · [Mốc T10](regression-matrix.md#ma-trận-hồi-quy-t01t12--afn-045)

## Đối chiếu dữ liệu thật

Hai lần tái dựng từ bản xuất DATA ở commit `6602529`, seed 42, cho byte
giống nhau ở manifest và split Train/Validation, CSV QA, cạnh gom nhóm và
báo cáo chuẩn bị. Chạy trên Windows x64 với Python 3.13 và hai lockfile của
repo. Dùng blob Git nguyên byte để tránh thay SHA-256 do CRLF.

| Tệp đối chiếu | SHA-256 | Kết quả |
| --- | --- | --- |
| Manifest Train/Validation | `a42af272426dc73019dd1f7b010de9feb1f3fb67f8b2740c672f6a34a237f44a` | Khớp #34 |
| Split CSV đã ẩn Test ID | `81058045c8397ed9cce8645267466e79a2fc346606865e05ade9b303b77b9c1f` | Khớp #34 |
| Cấu hình thực nghiệm v1 | `11dab478d6838c5872a2446d01d950382a51c4265298319d03cdb472f3aa29a8` | Khớp #34, trạng thái `proposed` |

[Hash đã công bố](../configs/selected-models.json)

| Split | Mẫu | Nhóm | Tỷ lệ thực | Hai nhãn |
| --- | ---: | ---: | ---: | --- |
| Train | 153 | 143 | 70,18% | Đủ |
| Validation | 32 | 32 | 14,68% | Đủ |
| Test khóa | 33 | 33 | 15,14% | Đủ theo thống kê tổng hợp lúc chia |

- CSV QA có 218 ID duy nhất, 208 nhóm và không có nhóm qua nhiều split.
  Các phân công Train/Validation và đa tập group ID Test khớp CSV đã ẩn ID.
- 47 cạnh trong ledger đều nằm trong cùng nhóm và cùng split, gồm 9 cạnh
  ảnh giống byte và 38 cạnh ảnh gần trùng. Điều này kiểm được cả các
  quan hệ bắc cầu có trong ledger. Kiểm độc lập SHA-256 ảnh và trùng
  body/tiêu đề chuẩn hóa giữa Train và Validation không phát hiện giao nhau.
- Số đếm nguồn × nhãn của Train/Validation khớp manifest. PolitiFact-real
  chỉ có 3 mẫu Validation. Dùng số đếm Test tổng hợp để xác nhận đủ nhãn,
  giữ manifest Test riêng và không đọc nội dung Test phục vụ audit.

## Giao thức và lựa chọn Validation

Hồ sơ #34 ghi fit trên Train, chọn trên Validation, không refit Train+Val
và `test_split.loaded: false`. Hai hồ sơ khớp cùng run ID, hash đầu vào, số
mẫu và hash thứ tự Train/Validation cho cả ba cấu hình. Đã xếp lại độc lập
75 điểm trong lưới theo Macro-F1 và luật hòa AFN-004. C và ngưỡng cùng khớp
hai hồ sơ với cả ba cấu hình.

| Cấu hình | C | Ngưỡng | Macro-F1 Validation |
| --- | ---: | ---: | ---: |
| Text-only | 10 | 0,60 | 0,6863 |
| Image-only | 10 | 0,30 | 0,5362 |
| Multimodal | 100 | 0,70 | 0,6235 |

[Hồ sơ Validation](validation-search.json) · [Giao thức AFN-004](../docs/experiment-protocol.md)

24 ca pytest đạt. Các kiểm thử fixture ghi nhận Logistic Regression chỉ
fit hàng Train, TF-IDF từ chối Validation khi fit, runner từ chối tập có
Test, và audit phát hiện quan hệ vắt qua split, metadata thiếu hoặc checksum bị sửa. Hai
phép thử âm trên bản sao trong bộ nhớ cũng từ chối C bị thay và cờ Test
đã load. Lượt audit này không huấn luyện lại.

## Chạy lại

PowerShell từ thư mục gốc repo. Các thư mục đầu ra nên là thư mục mới trong
vùng riêng. Chạy lệnh chuẩn bị hai lần với hai giá trị `--out` khác nhau
để đối chiếu khả năng tái lập.

```powershell
New-Item -ItemType Directory -Force cache | Out-Null
git -c core.autocrlf=false archive --format=zip --output=cache/afn-029-data.zip 6602529 data/processed/manifest.json data/processed/groups.json data/images
git -c core.autocrlf=false archive --format=zip --output=cache/afn-029-config.zip c3c6ebd configs/experiment.yaml
Expand-Archive cache/afn-029-data.zip cache/afn-029-input
Expand-Archive cache/afn-029-config.zip cache/afn-029-input
python -m ml.prepare_dataset --manifest cache/afn-029-input/data/processed/manifest.json --groups cache/afn-029-input/data/processed/groups.json --image-root cache/afn-029-input/data --out data/private/afn-029-a
python -m scripts.audit_split --ml-v2 --release data/private/afn-029-a --image-root cache/afn-029-input/data --experiment-config cache/afn-029-input/configs/experiment.yaml
python -m pytest -q tests/test_split_integrity.py tests/data/test_split_data.py tests/test_prepare_dataset.py tests/test_fusion.py tests/test_selection_outputs.py
```

Chế độ `--ml-v2` trả mã 1 với `BLOCKED` vì thiếu provenance dù các phép
kiểm của ứng viên đạt. Chế độ AFN-018 dùng bộ bàn giao DATA và hai hash độc
lập do QA nhận từ AFN-017/018.

```text
python -m scripts.audit_split --release <private-release> --grouping <private-grouping> --summary-sha256 <sha256-tu-AFN-018> --audit-sha256 <sha256-tu-AFN-017>
```

## Khôi phục metadata nguồn

Đối chiếu cả bốn CSV FakeNewsNet tại commit
`654361e1c8d5baa751baf1dac5032df621652280` với CSV split QA. Khớp đúng một
bản ghi cho cả **218/218 ID**. Lấy hostname từ URL gốc, chuẩn hóa `www.`
và tách URL gốc từ đường dẫn Wayback khi có. Đã điền **218/218 hostname
publisher dạng đề xuất**. Việc xác nhận nhà xuất bản thật và quyền sử dụng
vẫn cần DATA đối chiếu bản thu hồi.
[CSV nguồn FakeNewsNet](https://github.com/KaiDMML/FakeNewsNet/tree/654361e1c8d5baa751baf1dac5032df621652280/dataset)

Bản xuất DATA có trường `group_event` nhưng không có giá trị đã gán. CSV
nguồn cũng không cấp event ID. `event_id` được để trống và bảng review có
**13 cặp** từ độ giống tiêu đề nguồn với ngưỡng ứng viên AFN-017, trong đó
**2 cặp qua split**. Đây là danh sách để DATA xem cùng bằng chứng sự kiện.
Không có cặp trùng URL bài sau chuẩn hóa trong tập đối chiếu.

Khi dùng hostname đề xuất để rà split hiện hành, **33 hostname** có mặt ở
nhiều nhóm, trong đó **21 hostname** xuất hiện ở nhiều split. Kết quả
audit vẫn `BLOCKED`. DATA cần xác nhận hostname, xử lý hai cặp ứng viên
qua split và bàn giao checksum; nếu quan hệ được xác nhận, gộp nhóm và
chia lại theo giao thức trước khi chạy lại Train/Validation.

```powershell
python -m scripts.recover_split_provenance --source-dir data/private/afn-029-provenance/source --qa-split data/private/afn-029-a/qa-only/split.csv --out data/private/afn-029-provenance/draft
```

Script ghim SHA-256 của bốn CSV nguồn, ghi `provenance-draft.csv`,
`source-evidence.csv`, `event-candidates.csv` và `summary.json` vào thư mục
riêng. Hai lượt chạy cho cùng checksum các tệp. SHA-256 của CSV metadata
nháp là `d6e830893641ae922f0aad02e180361a29100b39b98ad4286b688c526b950305`.
Bảng dùng ID trong CSV QA và metadata nguồn; không đọc thân bài, ảnh hoặc
dự đoán Test. Giữ tệp theo ID trong kho QA. Chỉ dữ liệu tổng hợp xuất hiện
trong báo cáo này.

## Điều kiện bỏ chặn

DATA `locnguyen230` cần bàn giao metadata publisher/event theo ID hoặc bản
audit quan hệ đã duyệt với checksum và phiên bản. QA `dangnguyen0512` đối
chiếu trên cùng snapshot và ghi kết quả review. Nếu bổ sung quan hệ làm
thay đổi nhóm hoặc split, QA/DATA ghi phiên bản mới và ML đánh giá lại
Train/Validation theo giao thức trước freeze. Điều kiện mở Test thuộc #49.
[#18](https://github.com/ngnsusinn/anti-fake-news/issues/18) ·
[#29](https://github.com/ngnsusinn/anti-fake-news/issues/29) ·
[#49](https://github.com/ngnsusinn/anti-fake-news/issues/49)


Khi DATA cung cấp metadata đã review cho đúng snapshot, QA nhận CSV riêng
có đúng ba cột `sample_id,publisher,event_id` và SHA-256 do DATA thông báo
qua kênh bàn giao. CSV chỉ chứa khóa đã chuẩn hóa để nối quan hệ. Mỗi ID
trong split QA cần có đúng một dòng. Giữ tệp trong vùng riêng của QA.

```powershell
python -m scripts.audit_split --ml-v2 --release data/private/afn-029-a --image-root cache/afn-029-input/data --experiment-config cache/afn-029-input/configs/experiment.yaml --provenance-csv <csv-da-review> --provenance-sha256 <sha256-tu-DATA>
```

Lệnh đối chiếu độ phủ ID, checksum và đếm khóa trùng qua nhóm hoặc split
mà không in ID hay khóa. Với CSV này, khóa thiếu hoặc qua nhóm khiến phép
audit báo `BLOCKED`. Nếu DATA bàn giao bộ AFN-017/018 đã duyệt với giới
hạn metadata được giải trình, dùng chế độ AFN-018 và đối chiếu phiên bản
với lượt Train/Validation liên quan.

`PASS` từ script chỉ xác nhận các phép kiểm dữ liệu. QA và DATA xác nhận
audit trước lượt Train/Validation làm bằng chứng nghiệm thu. Lượt #34
đã công bố diễn ra trước audit này, nên cần một lượt Train/Validation được
ML xác nhận sau sign-off để đáp ứng trình tự của #29. Nếu nhóm hoặc split
thay đổi, ghi phiên bản và checksum mới trước khi chạy. Test vẫn khóa
theo #49.
