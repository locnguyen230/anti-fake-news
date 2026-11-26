# AFN-031 · Audit chất lượng mẫu và nguồn trước khóa cuối

**Ngày audit:** 26/11/2026 (UTC+7)  
**Owner:** DATA `locnguyen230` · **Reviewer:** QA `dangnguyen0512`  
**Trạng thái:** PARTIAL / BLOCKED nghiệm thu dataset cuối.  
**Issue:** [#31](https://github.com/ngnsusinn/anti-fake-news/issues/31) · **Dependency:** [#18](https://github.com/ngnsusinn/anti-fake-news/issues/18).  
**Baseline:** `ngnsusinn/anti-fake-news`, `main` tại [`b9dbb7d5fdc46e659d8af3eb5a6e7ec1a0baa88d`](https://github.com/ngnsusinn/anti-fake-news/commit/b9dbb7d5fdc46e659d8af3eb5a6e7ec1a0baa88d).

## 1. Mục tiêu, phạm vi và phương pháp

Audit bắt đầu từ **352 bản ghi DATA gốc** đã merge qua PR #87, không lấy 218 mẫu ML làm mẫu số mặc định. Kiểm tra độ đầy đủ, ID, grouping, split, sự tồn tại và kích thước ảnh, ảnh trùng byte, trường provenance và nguyên tắc loại mẫu; đối chiếu với tiêu chí AFN-001 và bằng chứng ML/QA.

- **Trực tiếp:** lấy toàn bộ blob JSON bằng Git Blob API tại commit ghim; parse JSON, đếm ID, trường, độ dài và quan hệ trùng chính xác bằng chương trình; đối chiếu cây Git và SHA của ảnh; tính SHA-256 của nội dung JSON UTF-8 trả về. Số byte khớp kích thước blob. Không sử dụng bản preview hoặc phần text bị cắt.
- **Dẫn lại:** các kiểm tra decode/pHash, nguồn CSV, publisher, URL và đối chiếu bài/ảnh đã thực hiện bởi ML/QA được ghi riêng; không coi là kiểm tra độc lập mới của DATA.
- **Bảo vệ Test:** chỉ kiểm cấu trúc và thống kê tổng hợp tự động trên bản xuất DATA công khai cũ, gồm đếm độ dài và quan hệ trùng chính xác; không rà thủ công thân bài/ảnh Test, không truy xuất gói Test riêng `ml-v2`, không xem predictions, không chọn tham số hoặc thay split. Test cũ 53 và Test `ml-v2` 33 là hai phiên bản khác nhau, không được xem là cùng tập.
- Không sửa manifest/groups/split, không đổi nhãn, không tự loại mẫu, không huấn luyện, không tạo version mới khi chưa có quyết định DATA/QA. AFN-032 (profile phân bố) và AFN-029 (audit leakage độc lập) không thuộc phạm vi sửa file của lượt này.

## 2. Định danh baseline và đối soát số lượng

### 2.1. Dấu vân tay dữ liệu DATA

| File | Số bản ghi / key | SHA-256 |
| --- | ---: | --- |
| `data/processed/manifest.json` | 352 | `0d17dae8b2815985e5341f6a3f17afea22c96237c5f666e63ab824de64ca99ef` |
| `data/processed/groups.json` | 352 | `3bf9199395a5fb7ba0d063fdebeb40d440e648b379dd28ab8068bcd1474e28fe` |
| `data/split/train.json` | 247 | `cfb88a45316411431ce365e1372c2349aad53e5b02b466b4a9b4cb3d6ecf14d9` |
| `data/split/validation.json` | 52 | `1af2da1c02d24975c60253f2f4102e246ed67660876a8e02fb5b8fb3d423f720` |
| `data/split/test.json` | 53 | `aec6d2f56af24e7bea9f047cccf6727c657522812fe94ee4266b70ef07118310` |

Manifest có 1.941.904 byte; hash prefix `0d17dae8` và `3bf91993` khớp báo cáo AFN-034. Các hash này định danh bản xuất, **không phải** chữ ký nghiệm thu AFN-018. Dùng nguyên byte blob Git thay vì file checkout có thể bị đổi CRLF.

### 2.2. Cấu trúc và coverage

| Kiểm tra trực tiếp | Kết quả | Trạng thái |
| --- | --- | --- |
| Manifest là JSON array, parse thành công | 352 dòng, 352 ID duy nhất | PASS |
| Groups là mapping sample_id → group_id | 352 key, 342 group duy nhất | PASS |
| Coverage manifest → groups | 352/352, không thiếu ID | PASS |
| Coverage split → manifest | 352/352, không ID lạ/bỏ sót | PASS |
| ID giao giữa các split | 0 | PASS |
| Group ID khai báo giao giữa các split | 0 | PASS (chỉ xét mapping cũ) |
| Group ID trong split lệch mapping | 0 | PASS |
| Quan hệ ảnh trùng byte giao split | 4 cụm / 15 mẫu | FAIL |

| Split gốc | Mẫu | Group | Tỷ lệ |
| --- | ---: | ---: | ---: |
| Train | 247 | 240 | 70,17% |
| Validation | 52 | 51 | 14,77% |
| Test | 53 | 51 | 15,06% |
| Tổng | 352 | 342 | 100% |

**Kết luận:** cấu trúc split đủ mẫu và không giao group ID đã khai báo, nhưng mapping chưa bao phủ mọi quan hệ trùng ảnh. Không xác nhận split gốc đạt chống leakage.

## 3. Audit chất lượng baseline 352 mẫu

### 3.1. Độ đầy đủ của text và ảnh

| Loại | Mẫu | Tỷ lệ | Ý nghĩa |
| --- | ---: | ---: | --- |
| `full` | 274 | 77,84% | Có text không rỗng và đường dẫn ảnh |
| `noimg` | 66 | 18,75% | Có text, thiếu đường dẫn ảnh |
| `notext` | 12 | 3,41% | Có đường dẫn ảnh, thiếu text |
| Thiếu cả hai | 0 | 0% | Không phát hiện |
| Tổng | 352 | 100% | Baseline DATA |

`type` khớp trạng thái text/ảnh trên 352/352 dòng. Có 340 mẫu chứa text, 286 mẫu có đường dẫn ảnh. `full` chỉ là điều kiện hiện diện, chưa chứng minh đúng bài, đúng ngữ cảnh, ngôn ngữ hay quyền.

| Kiểm tra trực tiếp | Kết quả |
| --- | ---: |
| Text vượt 50.000 Unicode code points | 8 |
| Title vượt 500 Unicode code points | 0 |
| Đường dẫn ảnh có blob trong cây Git | 286/286 |
| Đường dẫn ảnh không tìm thấy | 0 |
| Đường dẫn ảnh phân biệt | 286 |
| File ảnh vượt 10 MiB | 0/286 |
| Đường dẫn ảnh không khớp thư mục source_label | 0/286 |

Chưa giải mã từng ảnh, chưa kiểm MIME/pixel/EXIF hoặc đối chiếu ảnh với bài. Không kết luận 286 ảnh đã PASS chất lượng. Giới hạn theo [data-contract.md](../docs/data-contract.md) và [API contract](../docs/api-contract.md): JPEG/PNG hợp lệ, tối đa 10 MiB và 20 megapixel; body tiếng Anh không rỗng, tối đa 50.000 ký tự, title tùy chọn tối đa 500 ký tự.

### 3.2. Ảnh lặp và bài lặp — phát hiện độc lập

Đối chiếu Git blob SHA của file ảnh được manifest tham chiếu. Blob SHA giống nhau trong cùng repo biểu thị cùng nội dung byte; không phải perceptual hash và không chứng minh cùng ngữ cảnh.

| Phép kiểm | Kết quả trực tiếp |
| --- | ---: |
| Cụm ảnh giống byte (ít nhất 2 mẫu/cụm) | 6 |
| Tổng mẫu trong 6 cụm | 21 |
| Cụm ảnh giống byte nằm ở nhiều group ID | 6/6 |
| Cụm ảnh giống byte nằm ở nhiều split | 4/6 |
| Mẫu thuộc 4 cụm giao split | 15 |
| Cụm body không rỗng giống chính xác sau trim | 4 |
| Mẫu thuộc 4 cụm body | 11 |
| Cụm body chính xác giao group/split | 0/4 |

Không công bố ID, đường dẫn hay nội dung Test trong báo cáo. Kiểm body ở đây chỉ so khớp chuỗi sau trim bằng chương trình; chưa kiểm chuẩn hóa NFKC/NFC, gần trùng, pHash hoặc quan hệ bắc cầu. QA cần đối chiếu bằng quy tắc AFN-017.

**Finding DQ-01 (P0):** 4 cụm ảnh giống byte giao split, 6 cụm chưa được gom chung. Không loại tự động 21 mẫu: ảnh dùng lại có thể đúng ngữ cảnh; cần rà ca được phép, gom quan hệ hợp lệ, cách ly xung đột với Test qua QA. Split DATA cũ không đủ điều kiện freeze. Không suy ra lỗi này vẫn tồn tại ở `ml-v2` nếu chưa kiểm lại đúng phiên bản.

### 3.3. Nhãn và provenance

| Nguồn | fake | real | Tổng |
| --- | ---: | ---: | ---: |
| GossipCop | 98 | 95 | 193 |
| PolitiFact | 89 | 70 | 159 |
| Tổng | 187 | 165 | 352 |

352 ID có prefix phù hợp trường source; các đường dẫn ảnh hiện diện đều phù hợp thư mục source_label. Đây là kiểm tra nhất quán nội bộ, **không** phải xác minh nhãn với CSV gốc hoặc xác nhận bài thu hồi chính là bài được gán nhãn.

Bản xuất có tám trường `sample_id`, `source`, `label`, `title`, `text`, `pathIMG`, `type`, `group_event` trên mỗi dòng. Cả 352 `group_event` đều null. Không có trường `publisher`, `source_url`, `retrieved_at`, `source_id` riêng, `rights`, `exclusion_reason`, `status` hoặc checksum ảnh theo schema. Không thể xác nhận provenance hay lý do loại trên toàn bộ inventory chỉ từ file này.

**Finding DQ-02 (P0):** thiếu publisher/event/URL và quyền trên baseline; phải khôi phục từ CSV nguồn, nhật ký recovery và bằng chứng bài/ảnh. Không tự gán event từ tên người hoặc hostname, không tự thay nhãn. Cần đối chiếu đúng đối tượng được fact-check, không dùng trang tham khảo/nguồn dẫn thay bài gốc.

## 4. Đối chiếu bước lọc của ML — 352 → 218

Nguồn: [ml/prepare_dataset.py](../ml/prepare_dataset.py), [ml-train-validation.md](ml-train-validation.md). Theo báo cáo AFN-034, ML chạy luật cố định và đếm mỗi mẫu theo lý do đầu tiên. Các số đếm theo quy tắc ảnh nhỏ, body ngắn và boilerplate bên dưới **là kết quả ML đã báo cáo**, không phải lượt chạy lại ở phiên audit này.

| Lý do | Số mẫu ML loại | Nhận định DATA |
| --- | ---: | --- |
| `missing_image` | 66 | Khớp kiểm tra trực tiếp; không đủ multimodal |
| `missing_body` | 12 | Khớp trực tiếp; không đủ multimodal |
| `image_too_small` | 36 | Cạnh ngắn <64 px là heuristic ML, cần kiểm logo/placeholder và thống nhất với DATA/QA |
| `body_too_short` | 14 | <50 từ là heuristic ML, cần phân biệt bài ngắn hợp lệ với menu/paywall |
| `body_too_long` | 3 | Giới hạn 50.000 ký tự thuộc contract; baseline có 8 dòng vượt giới hạn, khác số lý do đầu tiên |
| `boilerplate_body` | 3 | Body giống nhau, khác title là tín hiệu, cần rà trước khi loại |
| Tổng | 134 | 352 − 134 = 218 |

| Giai đoạn | Mẫu | Ý nghĩa |
| --- | ---: | --- |
| DATA gốc | 352 | Bản xuất đủ ID/split |
| Có cả text và đường dẫn ảnh | 274 | 352 − 66 − 12; chưa đảm bảo chất lượng |
| Loại bổ sung theo ML | 56 | 36 + 14 + 3 + 3, thuộc phép đếm lý do đầu tiên |
| ML candidate `ml-v2` | 218 | 153 Train, 32 Val, 33 Test khóa |

Không có bằng chứng về một dataset 204 mẫu trong nguồn đã đối chiếu. Không nhầm `218` mẫu với `208` group hoặc `185` Train+Validation. Tỷ lệ giữ theo ML là 218/352 = 61,93%.

Các luật giới hạn 500/50.000 ký tự và có text/ảnh có căn cứ contract. Các luật 50 từ, 64 px, tỷ lệ ký tự ASCII >=80% và cùng body khác title cần DATA/QA xác nhận; không tự nới ngưỡng chỉ để đạt số mẫu hoặc cải thiện kết quả mô hình. Giới hạn 1.500 từ là quy tắc tiền xử lý ML, khác giới hạn API 50.000 ký tự; không mặc nhiên xem body dài hơn 1.500 từ là bị loại. Đọc `qa-only/decisions.jsonl` qua QA (chỉ phần được phép) để giải thích mọi lý do, không suy đoán lý do của từng ID.

**Finding DQ-03 (P0):** bản xuất 352 chưa phải manifest đủ hai phương thức; `ml-v2` dùng luật bổ sung chưa được DATA/QA duyệt. Cần xác minh 56 loại bổ sung, ưu tiên những mẫu thuộc Train/Val được phép. Không phục hồi hàng loạt chỉ vì thiếu số lượng.

## 5. Bằng chứng ML/QA bổ trợ — không trộn phiên bản

### 5.1. ML candidate và QA leakage audit

[AFN-034](ml-train-validation.md) và [AFN-029](leakage-audit.md) ghi nhận `ml-v2` 218 mẫu, 208 group; QA đối chiếu 218/218 ID với bốn CSV nguồn FakeNewsNet ở commit `654361e1c8d5baa751baf1dac5032df621652280`. Có 218 hostname publisher đề xuất, 33 hostname ở nhiều group, 21 ở nhiều split; 13 cặp tiêu đề ứng viên event, 2 cặp giao split; chưa đủ căn cứ gán cùng event ID. 47 cạnh ảnh (9 giống byte, 38 gần trùng) nằm trong cùng group/split của `ml-v2`. Đây là số cạnh, không phải số mẫu hoặc cụm ảnh. 185/185 Train/Val có `rights: unverified`.

Candidate run `20261125T145232Z` (chỉ Validation) được định danh trong [selected-models.json](../configs/selected-models.json):

| Artifact | SHA-256 do ML công bố |
| --- | --- |
| Manifest Train/Val `ml-v2` | `a42af272426dc73019dd1f7b010de9feb1f3fb67f8b2740c672f6a34a237f44a` |
| Split CSV ẩn ID Test | `81058045c8397ed9cce8645267466e79a2fc346606865e05ade9b303b77b9c1f` |
| Experiment config | `11dab478d6838c5872a2446d01d950382a51c4265298319d03cdb472f3aa29a8` |

Chưa tính lại ba hash private. Audit #29 vẫn BLOCKED về provenance và thứ tự sign-off trước tuning, dù GitHub issue đã Closed. AFN-031 không cần chờ #29 để audit độc lập phần DATA; QA vẫn cần review trước freeze.

### 5.2. Rà soát chất lượng của QA ngày 26/11

Nguồn: [leakage-audit.md](leakage-audit.md), [afn-029-exploratory-review.json](afn-029-exploratory-review.json). Bản nháp 175 gồm 142 Train/Val và 33 Test khóa, chưa duyệt huấn luyện. Sau bước rà 134 Train/Val không xét quyền, QA báo:

| Kết quả | Mẫu |
| --- | ---: |
| Khớp bài và ảnh cùng pixel RGB | 38 |
| Khớp bài nhưng ảnh chưa xác minh | 13 |
| Cần rà lại nội dung | 8 |
| Không tải được trang | 4 |
| Cần rà nguồn thủ công | 71 |
| Tổng | 134 |

Trong 38 cặp khớp bài/ảnh, QA giữ 32 mẫu (Train 23, Val 9); còn 33 Test riêng. 113/134 tiêu đề khớp metadata là chỉ số riêng, không cộng vào bảng. Các mẫu giữ lại chưa được duyệt quyền, chưa huấn luyện trên tập con và không thay thế baseline 352. Không suy diễn 352 → 218 → 175 → 32 là cùng chuỗi lọc chính thức.

## 6. Quy trình xác minh và xử lý trước freeze

1. DATA nhận snapshot gốc, quyết định AFN-016, bốn CSV và hash nguồn; QA cung cấp manifest/split Train/Val được phép cùng hash đã duyệt. Đối chiếu coverage và version trước mọi bước rà nội dung.
2. Kiểm theo từng mẫu được phép: đúng ID/nhãn nguồn, đúng bài/URL, body tiếng Anh hợp lệ; ảnh liên quan, decode/MIME/byte/pixel/hash hợp lệ; publisher/event được xác nhận hoặc ghi thiếu rõ ràng; quyền theo từng bài và ảnh. URL 403/404/timeout không tự chứng minh snapshot cũ sai. Ghi quyết định `accepted/rejected/pending`, lý do/evidence, người review; lưu chi tiết theo ID trong kho riêng, không đưa payload lên repo.
3. Rà 56 mẫu bị ML loại bổ sung dựa trên tiêu chí dữ liệu độc lập, không predictions; tái sử dụng validator, grouping, split hiện có. Đối với quan hệ Test, QA xử lý riêng; DATA không đọc/đổi Test hoặc chuyển mẫu Test sang Train/Val.
4. Nếu thay mẫu, nhãn hợp lệ theo bằng chứng nguồn, metadata ảnh hưởng grouping hoặc split: tạo version mới do DATA/QA thống nhất, giữ nguyên bản cũ; chạy lại AFN-016 → AFN-017 → AFN-018 và audit AFN-029; kiểm checksum, số mẫu/lớp/nhóm, cập nhật AFN-032. Không sửa ngầm dataset cũ.
5. Thông báo ML/QA invalidation **trước lần tuning tiếp theo**: ghi version/hash cũ, version/hash mới, nguyên nhân và artifact bị ảnh hưởng; ML xác nhận cần chạy lại preprocessing/embedding cache phụ thuộc dữ liệu, cả ba pipeline Train/Val, selection, export, parity theo thay đổi. Freeze AFN-049 sau QA/ML sign-off; Test AFN-050 vẫn khóa tới đó.

### Bàn giao invalidation đề xuất (chưa gửi thông báo)

| Đối tượng | Yêu cầu |
| --- | --- |
| DATA `locnguyen230` | Đối chiếu DQ-01–03, bàn giao manifest/mapping/split hash mới nếu thay đổi, lưu bằng chứng nguồn và quyền |
| QA `dangnguyen0512` | Review quyết định, giữ Test, audit quan hệ và xác nhận version mới trước tuning |
| ML `0xDa1Vu` | Không xem candidate hiện tại là final; xác nhận invalidation và chạy lại các bước bị ảnh hưởng trên version đã duyệt |

Đây là cảnh báo cần review/invalidation trước freeze, chưa tuyên bố artifact hiện tại đã bị thay thế. Không có version mới, không có thông báo remote hoặc PR được tạo trong lượt này.

## 7. Kiểm chứng và tái lập

### 7.1. Kết quả đã chạy trực tiếp

- Git Blob API: `GET /repos/ngnsusinn/anti-fake-news/git/blobs/{sha}` cho toàn bộ năm JSON; `JSON.parse` thành công, số byte/hash và coverage tại §2.1–2.2. Manifest blob SHA-1 `0930cfe13215e3148cd5f624fd174052e70517e7`.
- Git Tree API: `GET /repos/ngnsusinn/anti-fake-news/git/trees/b9dbb7d5fdc46e659d8af3eb5a6e7ec1a0baa88d?recursive=1`; đối chiếu 286 đường dẫn, kích thước, blob SHA và các quan hệ ảnh ở §3.
- So sánh ID, group, field/type, độ dài, nguồn/nhãn nội bộ, chuỗi body chính xác và đối soát số lượng. Các phép integrity cấu trúc đạt; quan hệ ảnh giao split thất bại; metadata thiếu được ghi rõ.
- SHA-256 tính trên UTF-8 blob content; kiểm hàm hash với chuỗi `abc` cho digest chuẩn `ba7816bf...15ad`. Không chạy pytest, validator, pHash, decode ảnh hoặc truy vấn nguồn live độc lập trong lượt này. Không sử dụng mock làm bằng chứng dữ liệu thật.

### 7.2. Lệnh đối chiếu lại tại checkout local (chưa chạy trong lượt này)

Từ thư mục gốc repo, dùng Git lấy byte nguyên bản, không checkout đè thay đổi:

```powershell
git fetch origin
git cat-file -s 0930cfe13215e3148cd5f624fd174052e70517e7
```

Lệnh Python sau chỉ đọc Git blob và in thống kê cấu trúc; không in payload. Chạy bằng `python` từ root và truyền đoạn mã dưới dạng script tạm ngoài repo nếu cần. Đây là đoạn tái lập tham chiếu, không phải file mới bắt buộc của Issue.

```python
import hashlib
import json
import subprocess
from collections import Counter, defaultdict

commit = "b9dbb7d5fdc46e659d8af3eb5a6e7ec1a0baa88d"

def git(*args):
    return subprocess.check_output(["git", *args])

def read(path):
    raw = git("show", f"{commit}:{path}")
    print(path, len(raw), hashlib.sha256(raw).hexdigest())
    return json.loads(raw)

rows = read("data/processed/manifest.json")
groups = read("data/processed/groups.json")
parts = {name: read(f"data/split/{name}.json")
         for name in ("train", "validation", "test")}
ids = {r["sample_id"] for r in rows}
all_ids = [r["sample_id"] for part in parts.values() for r in part]
assert len(rows) == len(ids) == len(groups) == len(all_ids) == 352
assert ids == set(groups) == set(all_ids)
assert all(r["group_id"] == groups[r["sample_id"]]
           for part in parts.values() for r in part)
print("types", Counter(r["type"] for r in rows))
print("split counts", {k: len(v) for k, v in parts.items()})
print("groups", len(set(groups.values())))
print("missing event", sum(not r["group_event"] for r in rows))
print("body over limit", sum(len(r["text"] or "") > 50000 for r in rows))
print("title over limit", sum(len(r["title"] or "") > 500 for r in rows))

# Metadata Git, không tải hoặc giải mã ảnh.
images = {}
for entry in git("ls-tree", "-r", "-l", "-z", commit, "--", "data/images/").split(b"\0"):
    if not entry:
        continue
    meta, path = entry.split(b"\t", 1)
    _, kind, sha, size = meta.split()
    if kind == b"blob":
        images[path.decode("utf-8")] = (sha, int(size))

split_of = {r["sample_id"]: name for name, part in parts.items() for r in part}
by_blob = defaultdict(list)
missing = too_large = 0
for row in rows:
    if not row["pathIMG"]:
        continue
    path = row["pathIMG"].replace("\\", "/")
    path = path if path.startswith("data/") else "data/" + path
    if path not in images:
        missing += 1
        continue
    sha, size = images[path]
    too_large += size > 10 * 1024 * 1024
    by_blob[sha].append(row["sample_id"])
repeated = [members for members in by_blob.values() if len(members) > 1]
cross = [members for members in repeated if len({split_of[i] for i in members}) > 1]
print("missing image paths", missing, "oversize", too_large)
print("duplicate clusters/members", len(repeated), sum(map(len, repeated)))
print("cross-group clusters", sum(len({groups[i] for i in m}) > 1 for m in repeated))
print("cross-split clusters/members", len(cross), sum(map(len, cross)))
```

Kết quả tham chiếu mong đợi của snippet: 352 mẫu/342 group, 274 full/66 noimg/12 notext, event thiếu 352, body quá dài 8, title quá dài 0, ảnh thiếu/oversize 0, 6 cụm ảnh/21 mẫu, 6 cụm qua group, 4 cụm/15 mẫu qua split. Đây là phép audit không ghi file, không tuning. Kiểm pipeline private theo lệnh có sẵn tại [data-validation.md](data-validation.md), [grouping-audit.md](grouping-audit.md), [split-summary.md](split-summary.md), [rebuild-data.md](../docs/rebuild-data.md); QA cấp input được phép trước khi chạy.

## 8. Acceptance criteria, blocker và kết luận

| Tiêu chí AFN-031 | Trạng thái | Bằng chứng/việc còn thiếu |
| --- | --- | --- |
| Đối chiếu manifest với bài/ảnh và tiêu chí loại | PARTIAL | Đã đọc đủ 352 dòng, đối chiếu 286 ảnh về path/size; chưa xác minh từng bài/ảnh hoặc quyết định nguồn |
| Publisher/event thiếu, ảnh lặp, nhãn nguồn/provenance | PARTIAL | DQ-01/02 trực tiếp; CSV và nguồn live mới có bằng chứng QA trên phiên bản khác |
| Không loại mẫu vì model sai | PASS trong phạm vi audit | Không đọc predictions, không thay mẫu/nhãn/model |
| Không kiểm tra nội dung Test để tuning | PASS trong phạm vi audit | Chỉ đối soát tổng hợp baseline công khai; không mở Test riêng, không tuning |
| Dataset/split đổi phải version hóa và chạy lại pipeline | PASS về quy trình | §6; chưa có version mới để chạy kiểm chứng |
| Công khai giới hạn và metadata thiếu | PASS | §3, §5 và bảng blocker |
| Không chờ AFN-029 để làm phần độc lập | PASS | Kiểm trực tiếp baseline; không thay thế QA audit |
| Bàn giao invalidation cho ML/QA trước tuning | PARTIAL | Đã chuẩn bị nội dung §6; chưa gửi, chưa có xác nhận |
| Đầu ra `reports/data-quality-audit.md` | PASS về tài liệu | Báo cáo này |
| AFN-018 và QA review dataset thật | BLOCKED | #18 Closed/Not planned, chưa nghiệm thu mapping/hash; QA chưa review báo cáo này |

| Blocker / giới hạn | Owner | Điều kiện gỡ |
| --- | --- | --- |
| DQ-01: ảnh giống byte qua group/split gốc | DATA + QA | Rà quan hệ và bàn giao mapping/split version đã audit, giữ Test |
| DQ-02: thiếu provenance và quyền | DATA + QA | CSV/URL/snapshot, publisher/event, retrieved_at, bằng chứng quyền theo tài nguyên; ghi giới hạn không thể khôi phục |
| DQ-03: 56 mẫu lọc bổ sung chưa thống nhất | DATA + ML + QA | Rà lý do theo mẫu được phép, chốt tiêu chí lọc độc lập dự đoán |
| Thiếu gói private và hash độc lập đã duyệt | DATA + QA | Bàn giao AFN-018, đối chiếu đúng version; không lấy mock thay evidence |
| Chưa decode/pHash và rà nội dung độc lập trên bản cuối | DATA + QA | Chạy validator/shared preprocessing và audit quan hệ trên gói được phép |
| URL chết/paywall, event không có trong CSV, nhãn nguồn không chắc áp dụng đúng bài, ảnh bên thứ ba | DATA + QA | Lưu bằng chứng, giữ pending/loại có lý do; nếu không khắc phục được ghi hạn chế nghiên cứu |

**Kết luận:** baseline DATA 352 mẫu đã được đọc đầy đủ, không bị cắt bởi độ dài text. 274 mẫu có cả text và đường dẫn ảnh, 218 là candidate sau luật lọc ML. Audit phát hiện 4 cụm ảnh giống byte giao split gốc và 352/352 thiếu event; provenance chưa đạt contract. Báo cáo hoàn thành phần audit kỹ thuật độc lập trên baseline và tổng hợp bằng chứng liên quan. Chưa đủ cơ sở nghiệm thu AFN-031, chưa sửa dataset, chưa freeze, chưa chạy lại ML, chưa tạo commit/PR hoặc đóng Issue. QA cần đối chiếu và xác nhận trước Done.
