# AFN-032 · Thống kê phân bố và phân tích theo nguồn

- Phiên bản công cụ: `afn-profile-v1`; dataset: `data-export-pr87`; commit nguồn: `56e299e6630621aa3f60c3e2a190b625a7390767`.
- Chế độ: `legacy`; fixture: `None`.
- Trạng thái: **EXPLORATORY — chưa nghiệm thu dataset cuối**.
- Chỉ thống kê metadata; không đọc ảnh, đánh giá dự đoán hoặc dùng nội dung Test để tuning.
- Test chỉ hiển thị số liệu tổng hợp. Với gói riêng, QA quyết định phạm vi chia sẻ.

## 1. Định danh và checksum SHA-256

| Đầu vào | SHA-256 |
| --- | --- |
| `manifest` | `0d17dae8b2815985e5341f6a3f17afea22c96237c5f666e63ab824de64ca99ef` |
| `groups` | `3bf9199395a5fb7ba0d063fdebeb40d440e648b379dd28ab8068bcd1474e28fe` |
| `train` | `cfb88a45316411431ce365e1372c2349aad53e5b02b466b4a9b4cb3d6ecf14d9` |
| `validation` | `1af2da1c02d24975c60253f2f4102e246ed67660876a8e02fb5b8fb3d423f720` |
| `test` | `aec6d2f56af24e7bea9f047cccf6727c657522812fe94ee4266b70ef07118310` |

Hash tính trên byte file đầu vào, không phải JSON đã serialize lại. Khi hash thay đổi, sinh lại báo cáo; không tái dùng thống kê cũ.

## 2. Inventory và tình trạng mẫu

| Phạm vi | Số mẫu | Đủ hai đầu vào (khai báo) | Thiếu ảnh | Thiếu text | Chưa xác nhận accepted/rejected |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 352 | 274 (77.84%) | 66 (18.75%) | 12 (3.41%) | 352 (100.00%) |
| train | 247 | 189 (76.52%) | 48 (19.43%) | 10 (4.05%) | 247 (100.00%) |
| validation | 52 | 41 (78.85%) | 11 (21.15%) | 0 (0.00%) | 52 (100.00%) |
| test | 53 | 44 (83.02%) | 7 (13.21%) | 2 (3.77%) | 53 (100.00%) |
| unsplit | 0 | 0 (—) | 0 (—) | 0 (—) | 0 (—) |

Legacy `type=full/noimg/notext` là khai báo mức đầy đủ, không phải quyết định accepted/rejected theo schema. Mẫu thiếu phương thức không đủ đầu vào Multimodal; chưa loại khỏi split bằng công cụ này.

### Lý do thiếu/loại theo phạm vi

| Phạm vi | Lý do | Số mẫu / tỷ lệ trên phạm vi |
| --- | --- | ---: |
| all | `missing_body` | 12 (3.41%) |
| all | `missing_image` | 66 (18.75%) |
| train | `missing_body` | 10 (4.05%) |
| train | `missing_image` | 48 (19.43%) |
| validation | `missing_image` | 11 (21.15%) |
| test | `missing_body` | 2 (3.77%) |
| test | `missing_image` | 7 (13.21%) |
| unsplit | Không có lý do ghi nhận | 0 (—) |

## 3. Nguồn và nhãn

Source là phân tập FakeNewsNet (`gossipcop`/`politifact`); publisher là nhà xuất bản bài gốc đã đối soát, không đồng nghĩa với source. Nhãn là nhãn nguồn, không phải kết luận độc lập của dự án.

| Phạm vi | GossipCop | PolitiFact | Fake | Real |
| --- | ---: | ---: | ---: | ---: |
| all | 193 (54.83%) | 159 (45.17%) | 187 (53.12%) | 165 (46.88%) |
| train | 135 (54.66%) | 112 (45.34%) | 131 (53.04%) | 116 (46.96%) |
| validation | 29 (55.77%) | 23 (44.23%) | 28 (53.85%) | 24 (46.15%) |
| test | 29 (54.72%) | 24 (45.28%) | 28 (52.83%) | 25 (47.17%) |
| unsplit | 0 (—) | 0 (—) | 0 (—) | 0 (—) |

| Phạm vi | GossipCop fake | GossipCop real | PolitiFact fake | PolitiFact real |
| --- | ---: | ---: | ---: | ---: |
| all | 98 (27.84%) | 95 (26.99%) | 89 (25.28%) | 70 (19.89%) |
| train | 68 (27.53%) | 67 (27.13%) | 63 (25.51%) | 49 (19.84%) |
| validation | 15 (28.85%) | 14 (26.92%) | 13 (25.00%) | 10 (19.23%) |
| test | 15 (28.30%) | 14 (26.42%) | 13 (24.53%) | 11 (20.75%) |
| unsplit | 0 (—) | 0 (—) | 0 (—) | 0 (—) |

### Tình trạng mẫu theo nguồn × nhãn

Tỷ lệ tính trên số mẫu của từng tổ hợp nguồn × nhãn trong từng phạm vi; không dùng mẫu số toàn tập.

| Phạm vi | Nguồn × nhãn | Tổng | Đủ hai đầu vào | Thiếu ảnh | Thiếu text |
| --- | --- | ---: | ---: | ---: | ---: |
| all | gossipcop:fake | 98 | 83 (84.69%) | 14 (14.29%) | 1 (1.02%) |
| all | gossipcop:real | 95 | 89 (93.68%) | 5 (5.26%) | 1 (1.05%) |
| all | politifact:fake | 89 | 53 (59.55%) | 32 (35.96%) | 4 (4.49%) |
| all | politifact:real | 70 | 49 (70.00%) | 15 (21.43%) | 6 (8.57%) |
| train | gossipcop:fake | 68 | 58 (85.29%) | 10 (14.71%) | 0 (0.00%) |
| train | gossipcop:real | 67 | 63 (94.03%) | 3 (4.48%) | 1 (1.49%) |
| train | politifact:fake | 63 | 35 (55.56%) | 24 (38.10%) | 4 (6.35%) |
| train | politifact:real | 49 | 33 (67.35%) | 11 (22.45%) | 5 (10.20%) |
| validation | gossipcop:fake | 15 | 11 (73.33%) | 4 (26.67%) | 0 (0.00%) |
| validation | gossipcop:real | 14 | 14 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| validation | politifact:fake | 13 | 9 (69.23%) | 4 (30.77%) | 0 (0.00%) |
| validation | politifact:real | 10 | 7 (70.00%) | 3 (30.00%) | 0 (0.00%) |
| test | gossipcop:fake | 15 | 14 (93.33%) | 0 (0.00%) | 1 (6.67%) |
| test | gossipcop:real | 14 | 12 (85.71%) | 2 (14.29%) | 0 (0.00%) |
| test | politifact:fake | 13 | 9 (69.23%) | 4 (30.77%) | 0 (0.00%) |
| test | politifact:real | 11 | 9 (81.82%) | 1 (9.09%) | 1 (9.09%) |
| unsplit | gossipcop:fake | 0 | 0 (—) | 0 (—) | 0 (—) |
| unsplit | gossipcop:real | 0 | 0 (—) | 0 (—) | 0 (—) |
| unsplit | politifact:fake | 0 | 0 (—) | 0 (—) | 0 (—) |
| unsplit | politifact:real | 0 | 0 (—) | 0 (—) | 0 (—) |

### Biểu đồ phân bố nguồn (mỗi khối xấp xỉ 5% của phạm vi)

```text
all        gossipcop  ███████████          193 (54.83%)
all        politifact █████████            159 (45.17%)
train      gossipcop  ███████████          135 (54.66%)
train      politifact █████████            112 (45.34%)
validation gossipcop  ███████████          29 (55.77%)
validation politifact █████████            23 (44.23%)
test       gossipcop  ███████████          29 (54.72%)
test       politifact █████████            24 (45.28%)
```

## 4. Split, group và lớp thiếu

Tỷ lệ split dùng mẫu số là tổng mẫu được phân tập; tỷ lệ nguồn/nhãn dùng mẫu số từng hàng. Độ lệch tính theo điểm phần trăm.

| Split | Số mẫu | Tỷ lệ thực | Mục tiêu | Độ lệch (pp) | Group | Lớp thiếu | Nguồn × nhãn thiếu |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | 247 | 70.17% | 70% | +0.17 | 240 | Không | Không |
| validation | 52 | 14.77% | 15% | -0.23 | 51 | Không | Không |
| test | 53 | 15.06% | 15% | +0.06 | 51 | Không | Không |

| Phạm vi | Số group | Nhóm lớn nhất (mẫu) | Histogram kích thước: số group | Nguồn chi phối |
| --- | ---: | ---: | --- | --- |
| all | 342 | 4 | 1: 337, 2: 2, 3: 1, 4: 2 | gossipcop (193 (54.83%)) |
| train | 240 | 4 | 1: 237, 2: 1, 4: 2 | gossipcop (135 (54.66%)) |
| validation | 51 | 2 | 1: 50, 2: 1 | gossipcop (29 (55.77%)) |
| test | 51 | 3 | 1: 50, 3: 1 | gossipcop (29 (54.72%)) |

Đối soát: 352 = 352 đã chia + 0 chưa chia. Không trùng ID, không thiếu ID được yêu cầu chia, không giao group đã khai báo giữa split; đây không phải chứng nhận chống leakage theo nội dung.

## 5. Metadata nguồn và giới hạn

| Phạm vi | Thiếu publisher | Publisher phân biệt (khai báo) | Publisher lớn nhất (mẫu) | Thiếu event | Thiếu URL |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 352 (100.00%) | 0 | 0 | 352 (100.00%) | 352 (100.00%) |
| train | 247 (100.00%) | 0 | 0 | 247 (100.00%) | 247 (100.00%) |
| validation | 52 (100.00%) | 0 | 0 | 52 (100.00%) | 52 (100.00%) |
| test | 53 (100.00%) | 0 | 0 | 53 (100.00%) | 53 (100.00%) |
| unsplit | 0 (—) | 0 | 0 | 0 (—) | 0 (—) |

Publisher chỉ chuẩn hóa khoảng trắng và chữ hoa/thường để đếm metadata hiện có; không suy đoán từ source. Không công bố ID, URL, tên publisher riêng lẻ hoặc nội dung bài/ảnh. Không đánh giá chất lượng model từ phân bố này.

## 6. Bàn giao và tái lập

- DATA: `locnguyen230`; QA: `dangnguyen0512`. AFN-018 vẫn chờ nghiệm thu batch thật; AFN-031/029 cần xử lý chất lượng và leakage. Không dùng profile để quyết định tuning hoặc thay split.
- Bản `ml-v2` là ứng viên khác sau lọc/gom nhóm/chia lại; số liệu tham chiếu ở [AFN-034](ml-train-validation.md). Không suy diễn thống kê của ứng viên từ split gốc. Gói quyết định đầy đủ do QA quản lý; chạy chế độ `decisions` khi được bàn giao.
- Khi DATA/QA cập nhật manifest, nhóm hoặc split: tạo version mới, chạy lại công cụ với hash đã bàn giao; soát số đếm, ghi nhận invalidation cho ML/QA trước sử dụng.

Chạy từ thư mục gốc repo (Python 3.10+, standard library):

```sh
python -m scripts.profile_dataset --mode legacy --manifest data/processed/manifest.json --groups data/processed/groups.json --split-dir data/split --version data-export-pr87 --revision 56e299e6630621aa3f60c3e2a190b625a7390767 --out reports/data-profile.md
python -m scripts.profile_dataset --mode legacy --manifest data/processed/manifest.json --groups data/processed/groups.json --split-dir data/split --version data-export-pr87 --revision 56e299e6630621aa3f60c3e2a190b625a7390767 --out reports/data-profile.md --check
```

`--check` đối chiếu toàn bộ báo cáo sinh lại (bao gồm checksum); trả mã khác 0 khi dữ liệu hoặc báo cáo không còn khớp. `--expect-sha256 KEY=HASH` có thể lặp để ghim hash bàn giao độc lập. Trên Windows, kiểm tra CRLF do Git checkout; không chuẩn hóa byte trước khi tính hash. Dùng bản file nguyên byte đã bàn giao. Kiểm thử mục tiêu: `python -m pytest -q tests/data/test_profile_dataset.py`.
