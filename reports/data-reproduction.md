# AFN-048 · Kiểm tra tái tạo manifest/split và đóng gói metadata

**26/11/2026 · PARTIAL / BLOCKED cho nghiệm thu cuối.** Bản chỉ mục là bản nháp metadata tổng hợp; không cấp phép phát hành dữ liệu, không mở Test, không thay đổi dataset. DATA: `locnguyen230`; QA: `dangnguyen0512`. [Issue #48](https://github.com/ngnsusinn/anti-fake-news/issues/48) · [Commit khảo sát](https://github.com/ngnsusinn/anti-fake-news/commit/819e2fa42a44f2906d0e9e08bf884c53cdbe8f25). Truy vết: DEFINE §9.5; DESIGN §11; T10/T11 (theo Issue).

## 1. Phạm vi và phiên bản

| Giai đoạn | Số mẫu | Vai trò | Bằng chứng |
|---|---:|---|---|
| Recovery | 400 | 286 đủ text/ảnh; 99 chỉ text; 15 chỉ ảnh | [Recovery summary](recovery-summary.md), báo cáo kế thừa |
| DATA export PR #87 | 352 | 274 full, 66 noimg, 12 notext; chưa phải accepted theo v1 | Kiểm trực tiếp blob, [AFN-032](data-profile.md) |
| ML-v2 | 218 | 153 Train, 32 Validation, 33 Test khóa | [AFN-034](ml-train-validation.md), [AFN-029](leakage-audit.md) |

Ngày 26/11 nhóm chọn `ml-v2`. Protocol đã `locked`, run `20261126T024649Z`; freeze còn `draft`, ML đã ký, QA chưa ký. Không dùng snapshot 352 hoặc tập con thăm dò QA thay thế 218. Không cần đợi AFN-046: số liệu lấy từ manifest/split và hồ sơ ML. AFN-018 và AFN-033 closed `not_planned`, không đồng nghĩa nghiệm thu. Data card hiện chưa chốt; bàn giao bổ sung cho Integration.

## 2. Kiểm trực tiếp snapshot Git

Hai lượt đọc độc lập cùng năm blob dữ liệu và ba hồ sơ cấu hình tại commit ghim; tính SHA-256 trên UTF-8 nguyên bản trả về, không serialize JSON trước khi hash. Tất cả độ dài byte khớp kích thước trong cây Git; kiểm thử SHA-256 với chuỗi `abc` khớp vector chuẩn. Hai lượt đọc cho dữ liệu giống hệt và phép đếm metadata giống nhau. Đây là **khôi phục đúng snapshot đã version hóa**, không phải chạy lại recovery hoặc chia lại từ đầu.

| File | Byte | SHA-256 | Hai lượt đọc |
|---|---:|---|---|
| `data/processed/manifest.json` | 1,941,904 | `0d17dae8b2815985e5341f6a3f17afea22c96237c5f666e63ab824de64ca99ef` | MATCH |
| `data/processed/groups.json` | 12,818 | `3bf9199395a5fb7ba0d063fdebeb40d440e648b379dd28ab8068bcd1474e28fe` | MATCH |
| `data/split/train.json` | 18,622 | `cfb88a45316411431ce365e1372c2349aad53e5b02b466b4a9b4cb3d6ecf14d9` | MATCH |
| `data/split/validation.json` | 3,927 | `1af2da1c02d24975c60253f2f4102e246ed67660876a8e02fb5b8fb3d423f720` | MATCH |
| `data/split/test.json` | 4,003 | `aec6d2f56af24e7bea9f047cccf6727c657522812fe94ee4266b70ef07118310` | MATCH |
| `configs/experiment.yaml` | 1,381 | `dd4da7bde49905e06d6e89dc9e1a7ff3518bc2cabde424d798bb85d19e805298` | MATCH |
| `configs/selected-models.json` | 1,866 | `ced48940b30aab32e48625743f4697f92b3728f1f94947c7c1b9db83f5167030` | MATCH |
| `release/model-freeze.json` | 6,768 | `9b7d3d1ed529bb9510f3ad9df839e967661e0bb712a5ecaee42359e53206bd5f` | MATCH |

| Split DATA gốc | Mẫu | Nhóm | Tỷ lệ |
|---|---:|---:|---:|
| Train | 247 | 240 | 70,17% |
| Validation | 52 | 51 | 14,77% |
| Test | 53 | 51 | 15,06% |
| Tổng | 352 | 342 | 100% |

352 sample ID duy nhất; 352 khóa mapping; mỗi ID xuất hiện đúng một lần trong split, group_id khớp mapping, không group ID giao split. Nguồn × nhãn: GossipCop fake 98, real 95; PolitiFact fake 89, real 70. Không đọc nội dung Test để lựa chọn hay điều chỉnh; phép kiểm chỉ dùng định danh và metadata. Không xuất danh sách ID. **Giới hạn:** AFN-031 phát hiện 4 cụm ảnh trùng byte qua split gốc; không thể gọi đây là split chống leakage hoàn chỉnh. [AFN-031](data-quality-audit.md).

## 3. Đối chiếu ML-v2 và hồ sơ freeze

QA báo cáo hai lần tái dựng từ DATA commit `6602529` cho byte giống nhau ở manifest, split Train/Validation, CSV QA, cạnh gom nhóm và báo cáo chuẩn bị. Đây là bằng chứng QA kế thừa, không phải lượt chạy Python mới của AFN-048. Hash QA công bố đối chiếu trực tiếp với `configs/selected-models.json` và `release/model-freeze.json` hiện hành:

| Đối tượng | SHA-256 | Phạm vi |
|---|---|---|
| Manifest Train/Validation | `a42af272426dc73019dd1f7b010de9feb1f3fb67f8b2740c672f6a34a237f44a` | 185 dòng, không chứa Test |
| Split CSV ẩn ID Test | `81058045c8397ed9cce8645267466e79a2fc346606865e05ade9b303b77b9c1f` | 218 phân công, 33 dòng Test đã ẩn ID |
| Config hiện hành | `dd4da7bde49905e06d6e89dc9e1a7ff3518bc2cabde424d798bb85d19e805298` | locked, hash tính lại trực tiếp |
| Selected models | `ced48940b30aab32e48625743f4697f92b3728f1f94947c7c1b9db83f5167030` | run 20261126T024649Z, hash tính lại trực tiếp |

Manifest/split hash, protocol hash, selection hash, run ID và counts khớp giữa các hồ sơ. Không nhầm hash file freeze với `record_sha256` dùng ký nội dung canonical. Hash canonical được ML ghi `7afd69ded04c225beb6537295555178d901383983a19b552d6e27c10aac983f8`; chưa chạy `ml.freeze verify` với file và bundle thật.

| Split ML-v2 | Mẫu | Nhóm | Tỷ lệ | Lệch mục tiêu (điểm %) |
|---|---:|---:|---:|---:|
| Train | 153 | 143 | 70,18% | +0,18 |
| Validation | 32 | 32 | 14,68% | -0,32 |
| Test khóa | 33 | 33 | 15,14% | +0,14 |
| Tổng | 218 | 208 | 100% | 0 |

134/352 mẫu bị loại ở bước chuẩn bị ML (66 thiếu ảnh, 36 ảnh quá nhỏ, 14 body ngắn, 12 thiếu body, 3 body dài, 3 boilerplate; tính lý do đầu tiên). Chỉ 185 mẫu Train/Validation được phép dùng để mô tả chi tiết nguồn/nhãn: GossipCop fake 61, real 69; PolitiFact fake 36, real 19; riêng PolitiFact-real Validation có 3. Chi tiết Test để QA giữ. 21 hostname đề xuất giao split và event ID chưa gán; rights ghi `unverified`. Không xem lựa chọn ml-v2 là xác minh quyền hoặc hết nguy cơ leakage. [Biên bản freeze](pre-test-signoff.md).

## 4. Provenance và điều kiện khôi phục nguồn

FakeNewsNet commit `654361e1c8d5baa751baf1dac5032df621652280`. Bốn hash dưới đây được ghim trong [`scripts/recover_split_provenance.py`](../scripts/recover_split_provenance.py) và dẫn chứng AFN-029; **chưa tải và băm lại bốn CSV trong lượt này**.

| CSV | SHA-256 ghim |
|---|---|
| `gossipcop_fake.csv` | `c6932bffadb1230bc61c66bb2ca298f4ef28ce849d268313ad2eed41d18d4c99` |
| `gossipcop_real.csv` | `d721e9a8b7e660da05c089691743c33fecb25367074e936b5fab3d85cdcbe79f` |
| `politifact_fake.csv` | `abe7fe7aad801b1e2ab5fc963cbd0881d9670190262ae3df85e91c3380bd004c` |
| `politifact_real.csv` | `2500f86a7addca0f59fe8cf089c0f802d3eca6980f53538992b3b0e9687dbae0` |

`source` là phân tập GossipCop/PolitiFact; `publisher` là nhà xuất bản gốc đã đối soát, không đồng nhất với source. Nhãn là nhãn nguồn. AFN-029 đối chiếu 218/218 ID với CSV và tạo hostname đề xuất, chưa hoàn tất xác minh publisher/event/quyền. Legacy thiếu publisher và event ở 352/352 mẫu. Snapshot recovery 400 và hash do DATA bàn giao độc lập chưa truy cập được; không suy diễn 48 chênh lệch 400→352 là một lý do loại cụ thể nếu không có ledger ID.

## 5. Hướng dẫn tái lập và đối chiếu

### A. Khôi phục snapshot Git không đổi byte

Dùng checkout sạch từ commit ghim; không reset nhánh người dùng. Đoạn Python sau chạy ở thư mục gốc repository và chỉ đọc blob Git. Dùng `subprocess.check_output` thay cho chuyển hướng PowerShell có thể đổi encoding/newline. So hash với bảng mục 2 và chỉ mục JSON. Không in nội dung bài, ảnh hay ID Test.

```python
import hashlib, json, subprocess
from pathlib import Path

index = json.loads(Path("release/data-manifest-index.json").read_text(encoding="utf-8"))
revision = index["code_revision"]
for path, meta in index["legacy_data_export"]["files"].items():
    blob = subprocess.check_output(["git", "show", f"{revision}:{path}"])
    actual = hashlib.sha256(blob).hexdigest()
    if actual != meta["sha256"] or len(blob) != meta["bytes"]:
        raise SystemExit(f"MISMATCH: {path}")
    print("MATCH", path, actual)
```

Lệnh này là hướng dẫn chạy tại checkout người nhận; trong lượt hiện tại đã thực hiện phép đối chiếu tương đương qua GitHub API, không chạy đoạn git show ở container vì không có checkout upstream.

### B. Tái dựng ML-v2 (QA quản lý; không mở Test cho ML)

Dùng Python 3.13 và các requirements của repo, thêm `jsonschema` theo AFN-034; khôi phục đúng manifest/groups và ảnh từ snapshot được phép, giữ môi trường/commit ghi trong QA log. Chọn hai thư mục private mới, đã bảo vệ quyền đọc và không nằm trong vùng commit. Thực hiện bởi QA trước mở Test; nếu Test đã mở thì chỉ tái lập kiểm toán trong vùng riêng, tuyệt đối không thay split, model, ngưỡng hoặc dataset đã khóa.

```powershell
python -m ml.prepare_dataset --manifest data/processed/manifest.json --groups data/processed/groups.json --image-root data --out data/private/afn-048-rebuild-a
python -m ml.prepare_dataset --manifest data/processed/manifest.json --groups data/processed/groups.json --image-root data --out data/private/afn-048-rebuild-b
```

```powershell
Get-FileHash data/private/afn-048-rebuild-a/train-validation/manifest.jsonl -Algorithm SHA256
Get-FileHash data/private/afn-048-rebuild-b/train-validation/manifest.jsonl -Algorithm SHA256
Get-FileHash data/private/afn-048-rebuild-a/train-validation/split.csv -Algorithm SHA256
Get-FileHash data/private/afn-048-rebuild-b/train-validation/split.csv -Algorithm SHA256
```

QA đối chiếu cả A/B với hash mục 3 và bản chính thức, so chính xác danh sách `(sample_id, split, group_id)` trong CSV QA, kể cả thứ tự nếu yêu cầu đồng nhất byte, so group ledger và thống kê; không đưa ID Test ra khỏi kho QA. Nếu hash khác, kiểm tra CRLF, phiên bản mã, ảnh, rule, seed, dependency và thứ tự; không tự sửa hash kỳ vọng. Ghi diff và nguyên nhân; nếu dữ liệu thay đổi thực sự, thông báo invalidation DATA/ML/QA, phiên bản mới trước freeze. Sau mở Test chỉ ghi lỗi/giới hạn và theo quy trình đã duyệt.

### C. Manifest v1 và recovery 400

Không chạy validator v1 trực tiếp trên legacy JSON array. Theo [rebuild-data](../docs/rebuild-data.md) và [data contract](../docs/data-contract.md), cần snapshot 400, checksum do DATA cung cấp độc lập, nhật ký completion-order, quyết định từng ID và ảnh được phép. Dùng `scripts.verify_recovery_snapshots` để đối chiếu mốc 228/300/350/400, sau đó `scripts.validate_manifest`, `scripts.group_samples`, `scripts.split_data` với checksum nhóm được QA duyệt. Không đánh đồng đầu ra v1 với ml-v2. **NOT RUN** trong lượt này do thiếu snapshot/private input.

## 6. Metadata bàn giao và kiểm tra quyền

Đầu ra [`release/data-manifest-index.json`](../release/data-manifest-index.json) dùng schema đề xuất `afn-data-manifest-index-v1`, không thay đổi schema manifest v1. SHA-256 file index (UTF-8, LF): `48faee9b2be8438a31657275f5c6141f613a5fe44fabd205db55c7f3961b541e`. Đây là chỉ mục tổng hợp, không phải manifest huấn luyện hoặc gói dữ liệu được cấp phép công khai. Không có bản ghi từng ID vì DATA/QA chưa duyệt danh sách chia sẻ; nếu cần bản row-level, DATA xuất riêng danh sách trường `sample_id,source,source_id,label,group_id,split` đã duyệt, chỉ cho người được cấp quyền và loại ID Test trước freeze.

| Được đưa vào chỉ mục | Không được đưa vào |
|---|---|
| Version, commit, hash, counts, seed, split ratios | Body, title gốc, ảnh, tweet IDs, credential |
| Nguồn, nhãn tổng hợp, trạng thái provenance | URL từng bài, publisher evidence chi tiết, đường dẫn cá nhân |
| Link tài liệu tái lập, trạng thái QA | ID từng mẫu, ID Test, nội dung Test, prediction |

Gói AFN-048 chỉ gồm hai file yêu cầu. Kiểm tra schema JSON, allowlist khóa cấu trúc, số học, SHA-256 dạng 64 hex, trường trạng thái và danh sách file ZIP; không đóng gói nguyên cây `data/`. Cây repo khảo sát vẫn chứa legacy manifest có text và 286 file ảnh: việc loại khỏi gói mới **không đồng nghĩa repo/history đã được làm sạch hoặc quyền đã xác minh**. DATA/QA cần rà riêng quyền và phạm vi chia sẻ, không tự xóa hay viết lại lịch sử Git trong issue này. Lưu bản private ngoài Git hoặc kiểm `git check-ignore` và `git status` trước add; `.gitignore` gốc không tự chứng minh mọi thư mục private bị bỏ qua.

## 7. Giới hạn tái tạo Internet

URL có thể chết, redirect sang bài khác, paywall, CDN đổi ảnh, nội dung được cập nhật hoặc quyền truy cập thay đổi. Tải lại được URL không chứng minh byte và ngữ cảnh giống snapshot. Chỉ khôi phục bản byte cũ nếu snapshot hợp lệ còn lưu và có quyền; nếu không, đánh dấu không tái tạo được và giữ metadata được phép. Lượt thu hồi mới là phiên bản khác, không thay thế mẫu sau freeze hoặc sau khi xem Test. Không hứa URL tương lai còn hoạt động. [Recovery summary](recovery-summary.md) · [Data card](../docs/data-card.md).

## 8. Bằng chứng nghiệm thu và bàn giao

| Tiêu chí | Kết quả | Bằng chứng / điều kiện |
|---|---|---|
| Danh sách split tái tạo trùng | PARTIAL | Hai lượt lấy lại Git giống byte; QA đã báo tái dựng ml-v2 hai lần; AFN-048 chưa tái chạy full pipeline private |
| Provenance, version, hướng dẫn | PASS trong phạm vi chỉ mục | Commit, nguồn/hash ghim, phiên bản, hướng dẫn và thiếu metadata được ghi rõ |
| Không raw content trong gói | PASS phạm vi hai output | Allowlist file và trường; không phải kiểm toàn repo |
| Không hứa khôi phục Internet | PASS | Mục 7 |
| Đối chiếu với AFN-033 | PARTIAL | Liên kết data card/rebuild-data; Integration cần duyệt bổ sung counts/hash |
| Đối chiếu Test gate | BLOCKED | ML đã ký, QA chưa ký; private byte verify chưa chạy |
| QA review | NOT RUN | QA `dangnguyen0512`, CODEOWNER `ngnsusinn` theo working agreement |

**Việc còn lại:** DATA cung cấp snapshot/hash và xác nhận metadata được chia sẻ; QA chạy B/C và lưu exact assignment/hash, đối chiếu freeze, duyệt hai output; Integration cập nhật data card AFN-033. Nếu hash dataset đổi, thông báo ML/QA, tái sinh AFN-032/046/048 từ version mới và không sử dụng stats cũ. Không chờ AFN-046 để làm phần độc lập. Không chỉnh code ML, manifest, split, freeze hoặc data card của Integration. Chưa commit, push, mở PR hoặc đóng Issue trong lượt này. Không công bố kết quả Test hay đánh giá chất lượng model.
