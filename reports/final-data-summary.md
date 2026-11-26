# AFN-046 · Thống kê dataset/split cho báo cáo cuối

**Ngày đối chiếu:** 26/11/2026 (UTC+7).  
**Trạng thái:** DRAFT / BLOCKED nghiệm thu cuối — số liệu ứng viên, không phải dataset đã ký freeze.  
**Owner:** DATA `locnguyen230` · **Reviewer:** QA `dangnguyen0512` (chưa review).  
**Issue:** [#46](https://github.com/ngnsusinn/anti-fake-news/issues/46) · FR-08, T11.  
**Revision đối chiếu:** [`56e299e6630621aa3f60c3e2a190b625a7390767`](https://github.com/ngnsusinn/anti-fake-news/commit/56e299e6630621aa3f60c3e2a190b625a7390767).

## 1. Phạm vi và phiên bản

Báo cáo này hoàn thành phần độc lập của AFN-046 trước Test. Bản chính để mô tả dữ liệu **đã dùng cho lượt Train/Validation của mô hình ứng viên** là `ml-v2`, run `20261125T145232Z` (VALIDATION_ONLY). Bản DATA 352 mẫu chỉ là baseline thu hồi/tiền xử lý để đối soát mất mẫu; không gán thống kê của bản đó cho model. Chưa có phiên bản nghiên cứu cuối được ký.

| Giai đoạn | Số mẫu | Ý nghĩa / nguồn bằng chứng |
| --- | ---: | --- |
| Recovery AFN-003 | 400 | Có ít nhất thân bài hoặc ảnh; 286 có cả hai. [Recovery](recovery-summary.md) |
| DATA export PR #87 | 352 | 274 đủ hai đầu vào khai báo; chưa có quyết định accepted/rejected theo schema chính thức. Kiểm trực tiếp blob Git. |
| ML-v2 | 218 | 218/352 được giữ theo luật ML, chia lại nhóm; chưa duyệt cuối. [AFN-034](ml-train-validation.md) |
| Bản thăm dò QA | 175 | 116 Train, 26 Validation, 33 Test khóa; chưa được chấp thuận cho huấn luyện. [QA](afn-029-exploratory-review.json) |
| Tập con rà chất lượng | 32 Train/Val | 23 Train, 9 Validation; 33 Test riêng vẫn khóa; không phải model dataset hiện hành. [AFN-029](leakage-audit.md) |

Không suy diễn 400 → 352 là 48 mẫu loại nếu chưa có inventory/decision ledger nối hai batch. Tỷ lệ 218/352 chỉ áp dụng cho bản DATA đầu vào được ML công bố. Phạm vi thăm dò dưới 200 được QA ghi nhận ngày 25/11 theo quyết định chủ repo; không đồng nghĩa với việc chấp thuận một tập thăm dò làm dữ liệu cuối.

## 2. Bản DATA gốc — đối soát trực tiếp

Đọc đầy đủ JSON từ Git Blob API, không đếm preview. Manifest 1.941.904 byte, 352 ID duy nhất, 352 key mapping, 342 group; 352/352 ID được chia đúng một lần; không ID lạ, thiếu, lệch group hoặc group ID khai báo giao split. Không đọc nội dung bài/ảnh Test để tuning; phép kiểm chỉ dùng metadata của bản export cũ. Những số liệu dưới đây không đại diện cho Test khóa của `ml-v2`.

| Split | Mẫu | Tỷ lệ toàn bộ | Mục tiêu | Lệch (điểm %) | Group | Fake | Real |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 247 | 70.17% | 70% | +0.17 | 240 | 131 | 116 |
| Validation | 52 | 14.77% | 15% | -0.23 | 51 | 28 | 24 |
| Test gốc | 53 | 15.06% | 15% | +0.06 | 51 | 28 | 25 |
| Tổng | 352 | 100.00% | 100% | 0.00 | 342 | 187 | 165 |

| Nguồn × nhãn | Train | Validation | Test gốc | Tổng (% trên 352) |
| --- | ---: | ---: | ---: | ---: |
| GossipCop fake | 68 | 15 | 15 | 98 (27.84%) |
| GossipCop real | 67 | 14 | 14 | 95 (26.99%) |
| PolitiFact fake | 63 | 13 | 13 | 89 (25.28%) |
| PolitiFact real | 49 | 10 | 11 | 70 (19.89%) |
| Tổng | 247 | 52 | 53 | 352 (100.00%) |

GossipCop 193/352 (54.83%), PolitiFact 159/352 (45.17%); fake 187/352 (53.13% làm tròn half-up), real 165/352 (46.88%). Cả hai lớp và bốn tổ hợp nguồn × nhãn đều có mặt trong từng split gốc. Group histogram: 337 nhóm 1 mẫu, 2 nhóm 2 mẫu, 1 nhóm 3 mẫu, 2 nhóm 4 mẫu (342 nhóm, 352 mẫu); nhóm lớn nhất 4 mẫu. Các group khai báo không giao nhau nhưng không bảo đảm chống leakage: AFN-031 phát hiện 4 cụm ảnh giống byte qua split gốc (15 mẫu). Không dùng bản gốc làm split nghiên cứu đã duyệt.

| Split | Đủ hai đầu vào | Thiếu ảnh | Thiếu thân bài | Tổng |
| --- | ---: | ---: | ---: | ---: |
| Train | 189 (76.52%) | 48 (19.43%) | 10 (4.05%) | 247 |
| Validation | 41 (78.85%) | 11 (21.15%) | 0 (0.00%) | 52 |
| Test gốc | 44 (83.02%) | 7 (13.21%) | 2 (3.77%) | 53 |
| Tổng | 274 (77.84%) | 66 (18.75%) | 12 (3.41%) | 352 |

`full` chỉ có text và đường dẫn ảnh, không phải accepted. Thiếu publisher, URL nguồn và event trên 352/352 mẫu. Source là phân tập FakeNewsNet; publisher là nhà xuất bản bài gốc được đối soát; nhãn fake/real là nhãn nguồn, không phải sự thật do mô hình hoặc nhóm tự kiểm chứng. [Data card](../docs/data-card.md) · [Data contract](../docs/data-contract.md) · [AFN-031](https://github.com/ngnsusinn/anti-fake-news/issues/31) · [AFN-032](https://github.com/ngnsusinn/anti-fake-news/issues/32).

## 3. Bản ML-v2 — số liệu ứng viên khớp hồ sơ model

Các số đếm nguồn, nhóm và lý do loại trong mục này lấy từ [AFN-034](ml-train-validation.md) và [AFN-029](leakage-audit.md), không tái chạy ML hoặc truy cập gói QA riêng. Số lượng split, run ID, hash được đối chiếu trực tiếp với [selected models](../configs/selected-models.json) và [freeze nháp](../release/model-freeze.json).

| Lý do loại chính (mỗi mẫu một lý do) | Số mẫu | % trên 352 | % trên 134 bị loại |
| --- | ---: | ---: | ---: |
| `missing_image` | 66 | 18.75% | 49.25% |
| `missing_body` | 12 | 3.41% | 8.96% |
| `image_too_small` | 36 | 10.23% | 26.87% |
| `body_too_short` | 14 | 3.98% | 10.45% |
| `body_too_long` | 3 | 0.85% | 2.24% |
| `boilerplate_body` | 3 | 0.85% | 2.24% |
| Tổng loại | 134 | 38.07% | 100.00% |
| Giữ lại (ứng viên) | 218 | 61.93% | — |

78 mẫu thiếu phương thức, 56 mẫu bị loại theo các kiểm tra khác. Ngưỡng tối thiểu 64 px/50 từ và nhận diện boilerplate cần DATA/QA rà; không tự khôi phục hay loại thêm để đạt mục tiêu hoặc cải thiện điểm model. Các quyết định không dùng dự đoán. Mẫu số 352 không phải 400 của recovery.

| Split ML-v2 | Mẫu | Tỷ lệ trên 218 | Mục tiêu | Lệch (điểm %) | Group | Fake | Real |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 153 | 70.18% | 70% | +0.18 | 143 | 80 (52.29%) | 73 (47.71%) |
| Validation | 32 | 14.68% | 15% | -0.32 | 32 | 17 (53.13%) | 15 (46.88%) |
| Test khóa | 33 | 15.14% | 15% | +0.14 | 33 | Đủ lớp (QA) | Đủ lớp (QA) |
| Tổng | 218 | 100.00% | 100% | 0.00 | 208 | Chưa công bố | Chưa công bố |

Train + Validation = 185; 185 + 33 = 218. Số nhóm 143 + 32 + 33 = 208 theo QA. Histogram công bố: 205 nhóm 1 mẫu, 2 nhóm 2 mẫu, 1 nhóm 9 mẫu; 205 + 4 + 9 = 218. Nhóm lớn nhất 9/218 (4.13%). Quy mô danh nghĩa 218 trong khoảng mục tiêu 200–500 nhưng chưa xác nhận số mẫu đủ điều kiện cuối. Không coi nhóm khai báo là nhóm sự kiện đã xác minh.

| Nguồn × nhãn | Train (n=153) | Validation (n=32) | Train + Val (n=185) |
| --- | ---: | ---: | ---: |
| GossipCop fake | 50 (32.68%) | 11 (34.38%) | 61 (32.97%) |
| GossipCop real | 57 (37.25%) | 12 (37.50%) | 69 (37.30%) |
| PolitiFact fake | 30 (19.61%) | 6 (18.75%) | 36 (19.46%) |
| PolitiFact real | 16 (10.46%) | 3 (9.38%) | 19 (10.27%) |
| Tổng | 153 (100%) | 32 (100%) | 185 (100%) |

| Nguồn / nhãn | Train | Validation | Train + Validation |
| --- | ---: | ---: | ---: |
| GossipCop | 107 (69.93%) | 23 (71.88%) | 130 (70.27%) |
| PolitiFact | 46 (30.07%) | 9 (28.13%) | 55 (29.73%) |
| Fake | 80 (52.29%) | 17 (53.13%) | 97 (52.43%) |
| Real | 73 (47.71%) | 15 (46.88%) | 88 (47.57%) |

Không thiếu lớp hoặc tổ hợp nguồn × nhãn trong Train/Val. PolitiFact-real chỉ 3/32 (9.38%) Validation; GossipCop chi phối 130/185 (70.27%). QA ghi Test có hai nhãn theo thống kê tổng hợp nhưng không công bố số đếm từng lớp/nguồn trong bằng chứng hiện có. **Không suy diễn** số đếm Test hoặc toàn bộ 218 từ split gốc, không mở gói riêng, không ghi Test thiếu nguồn nếu chưa có bằng chứng. QA cần cung cấp bảng tổng hợp đã duyệt để hoàn tất số liệu toàn bộ.

## 4. Giới hạn dữ liệu và phương án thăm dò

- AFN-029 đối chiếu 218/218 ID với CSV nguồn, 218 hostname đề xuất; 33 hostname xuất hiện ở nhiều nhóm, 21 qua split; 13 cặp sự kiện ứng viên, 2 qua split. Publisher/event chưa xác nhận. 185/185 Train/Val ghi rights unverified; chưa đủ bằng chứng quyền và đúng đối tượng nhãn. Không công bố payload/ID Test.
- QA đã thử bản thăm dò 175 = 116 + 26 + 33, giữ Test khóa; 142 Train/Val đạt kiểm kỹ thuật nhưng 0 mẫu được phê duyệt huấn luyện theo lượt duyệt này. So với mốc ban đầu 200, thiếu 25 mẫu; tỷ lệ 66.29/14.86/18.86%, lệch -3.71/-0.14/+3.86 điểm %. QA ghi mốc 200 được nới cho nghiên cứu thăm dò; đây không phải split được model dùng.
- Tập con rà chất lượng 32 Train/Val (23/9; fake/real 11/12 và 2/7) cộng 33 Test giữ khóa là 65 dòng phân công nếu tính cả Test, không phải 65 mẫu hợp lệ; chưa train/evaluate. Không ghép số liệu với 218 hoặc 175. Cần phiên bản mới và xác nhận độc lập nếu chọn một tập thăm dò.
- Khả năng khôi phục URL/body/ảnh khác theo nguồn; có thể gây thiên lệch chọn mẫu. Không suy rộng kết quả ra mọi loại tin hoặc nhà xuất bản. Không kết luận chất lượng mô hình từ phân bố.
- [Data card](../docs/data-card.md), [quy trình tái tạo](../docs/rebuild-data.md), [audit chất lượng #31](https://github.com/ngnsusinn/anti-fake-news/issues/31), [audit leakage #29](leakage-audit.md) và [lý do loại #34](ml-train-validation.md#1-chuẩn-bị-dữ-liệu-mlprepare_dataset) là nguồn truy vết. Data card vẫn chờ số liệu cuối.

## 5. Checksum và đối chiếu AFN-049

### 5.1. Baseline DATA (SHA-256 tính lại trên blob UTF-8 nguyên byte)

| File | SHA-256 |
| --- | --- |
| `data/processed/manifest.json` | `0d17dae8b2815985e5341f6a3f17afea22c96237c5f666e63ab824de64ca99ef` |
| `data/processed/groups.json` | `3bf9199395a5fb7ba0d063fdebeb40d440e648b379dd28ab8068bcd1474e28fe` |
| `data/split/train.json` | `cfb88a45316411431ce365e1372c2349aad53e5b02b466b4a9b4cb3d6ecf14d9` |
| `data/split/validation.json` | `1af2da1c02d24975c60253f2f4102e246ed67660876a8e02fb5b8fb3d423f720` |
| `data/split/test.json` | `aec6d2f56af24e7bea9f047cccf6727c657522812fe94ee4266b70ef07118310` |

Các giá trị trên khớp AFN-032 đã bàn giao ngoài repo; file profile chưa xuất hiện trên main tại revision đối chiếu. Không dùng 5 hash legacy thay cho hash model.

### 5.2. Dữ liệu ứng viên và hồ sơ freeze nháp

| Đối tượng | SHA-256 | Cách xác nhận |
| --- | --- | --- |
| `ml-v2/train-validation/manifest.jsonl` | `a42af272426dc73019dd1f7b010de9feb1f3fb67f8b2740c672f6a34a237f44a` | Hai trường hash trong selected/freeze khớp; QA đã ghi tái dựng đúng byte. Chưa tính lại trên file private. |
| `ml-v2/train-validation/split.csv` (ẩn ID Test) | `81058045c8397ed9cce8645267466e79a2fc346606865e05ade9b303b77b9c1f` | Tương tự; không phải QA full split hash. |
| `configs/experiment.yaml` | `11dab478d6838c5872a2446d01d950382a51c4265298319d03cdb472f3aa29a8` | Tính trực tiếp; khớp selected/freeze; proposed. |
| `configs/selected-models.json` | `1ffa9d7cea176c75a8d7c27063cf7a781b701afea511fcefcca2879ad09d7ea0` | Tính trực tiếp; khớp freeze selection hash. |
| `release/model-freeze.json` | `e557c01fe22337d767ab1a8658f82ec27f1208febff2ae74721a1d73e894a92a` | Tính trực tiếp trên file draft; không phải record_sha256 có chữ ký. |

Run ID `20261125T145232Z`, seed 42, split unit `group_id`, ba cấu hình cùng 153 Train/32 Val, 33 Test khóa; run ID, số đếm và hash khai báo khớp. `selected-models.json`: candidate, `test_split.loaded=false`; freeze: draft, protocol proposed, signoffs ML/QA null. `refit_on_train_and_validation=false`. Model version trong freeze nháp: `text-only-20261125-275718e3163b`, `image-only-20261125-cd863cbaabf5`, `multimodal-20261125-105d5f14e79a`. Chưa kiểm byte của artifact, chưa xác nhận bản demo trỏ đúng model đã khóa. Freeze ghi các blocker: protocol proposed, snapshot code chưa sạch hoặc chưa biết, thiếu lệnh Test trong snapshot. Những blocker này thuộc hồ sơ đang ghim; ML cần collect lại trên commit được duyệt. [Biên bản AFN-049](pre-test-signoff.md).

## 6. Tái lập, kiểm chứng và bàn giao cuối

**Đã thực hiện trong lượt lập báo cáo:** lấy toàn bộ 5 blob legacy tại revision ghim, parse JSON, kiểm coverage ID/mapping/group, tính các bảng nguồn/nhãn/split và SHA-256; kiểm phép tính SHA-256 bằng vector `abc`; đọc selected/freeze/config và so run ID, manifest/split hash, selection/config hash và số mẫu của ba cấu hình. Đối chiếu hash với báo cáo AFN-032 đã bàn giao; kiểm lại tổng hàng và tỷ lệ. Không chạy validator/prepare_dataset/freeze verify trên gói private, không chạy Test hoặc mô hình. Không giả lập dữ liệu để tạo số nghiên cứu.

**Lệnh tái lập đề xuất, chưa chạy trên checkout thật trong lượt này:** tại repo, sau khi merge script AFN-032, ghim revision/hashes và dùng byte Git nguyên bản (lưu ý CRLF trên Windows):

```powershell
python -m scripts.profile_dataset --mode legacy --manifest data/processed/manifest.json --groups data/processed/groups.json --split-dir data/split --version data-export-pr87 --revision 56e299e6630621aa3f60c3e2a190b625a7390767 --out reports/data-profile.md --check
Get-FileHash configs/selected-models.json,configs/experiment.yaml,release/model-freeze.json -Algorithm SHA256
```

Khi có dataset cuối, QA cung cấp ledger quyết định, mapping và split đầy đủ trong vùng riêng; QA chạy `scripts.profile_dataset --mode decisions --qa-private` với các file được duyệt và ghi hash đầu vào. Không dùng CSV đã ẩn ID Test cho chế độ này; không đưa ledger/full split/payload Test cho ML hoặc commit vào Git. Dùng thống kê Test tổng hợp đã được QA phê duyệt để điền số đếm, nguồn, nhãn và nhóm còn thiếu. Đối chiếu đúng gói Train/Val (không phải full ledger) với freeze bằng lệnh ở [pre-test-signoff.md](pre-test-signoff.md); chỉ ML/QA ký và chạy verify khi đủ điều kiện. Không chạy `ml.evaluate_test` cho AFN-046.

### Checklist chốt cuối (chưa ký)

1. DATA/QA chốt version, manifest accepted/rejected/pending, mapping, split và checksum; xác minh nguồn/publisher/event, lớp/nhóm, lý do loại và phạm vi quyền.
2. Tái sinh profile AFN-032 trên đúng bản được duyệt. Ghi số đếm và tỷ lệ nguồn × nhãn, từng split và toàn bộ; thống kê Test do QA cung cấp. Đồng bộ data card AFN-033.
3. Nếu dữ liệu/split/protocol thay đổi trước freeze: tạo version/hash mới, ghi invalidation cho ML/QA, chạy lại validation/grouping/split/profile liên quan; ML đánh giá Train/Val, export, parity và collect freeze theo giao thức. Không thay Test để làm đẹp kết quả; không dùng dự đoán để loại mẫu.
4. Đối chiếu số đếm và hash gói thực tế với hồ sơ freeze có ML+QA ký; giữ riêng hash manifest đầy đủ, mapping, QA split, Train/Val manifest và split ẩn ID; không đánh đồng. Ghi record_sha256 đã ký và revision cuối. Chỉ khi QA review báo cáo và tất cả dependency đạt mới đổi DRAFT thành FINAL. Sau mở Test không thay split/lọc vì kết quả; lỗi kỹ thuật xử lý theo giao thức, ghi lý do và không âm thầm sửa.

| Blocker | Owner | Bằng chứng cần bổ sung |
| --- | --- | --- |
| AFN-018 chưa nghiệm thu batch thật (closed/not planned) | DATA + QA | Manifest/mapping/split được duyệt, hash và audit |
| AFN-032 open; profile chưa merge | DATA | PR/profile trên version cuối và QA xác nhận |
| AFN-033 closed/not planned | Integration `fulord26` + DATA | Data card/rebuild cập nhật số liệu cuối và giới hạn |
| AFN-029 audit blocked; provenance/rights | DATA + QA | Metadata/quan hệ đã đối soát; quyết định phạm vi |
| AFN-049 closed/not planned; freeze draft | ML `0xDa1Vu` + QA + Integration/Backend | Protocol locked, artifact/code khớp, chữ ký ML/QA và verify thành công |
| Phân bố Test và toàn bộ ML-v2 theo nguồn/nhãn chưa công bố | QA | Bảng aggregate đã duyệt, khớp đúng hash/split |

## 7. Acceptance criteria và trạng thái

| Tiêu chí AFN-046 | Kết quả | Trạng thái |
| --- | --- | --- |
| Tạo lại thống kê từ manifest/split đã khóa | Tính trực tiếp legacy; đối chiếu ứng viên, chưa có bản khóa | PARTIAL/BLOCKED |
| Bảng báo cáo và model cùng version/hash | Hash khai báo `ml-v2` khớp draft và selected; byte private/artifact, chữ ký chưa kiểm | PARTIAL |
| Đếm kèm tỷ lệ, giới hạn nguồn/nhãn/nhóm | Có đầy đủ baseline và Train/Val ứng viên; Test aggregate chi tiết chờ QA | PARTIAL |
| Liên kết data card, lý do loại, checksum | Đã liên kết, phân biệt mẫu số và phiên bản | PASS (phạm vi tài liệu) |
| Không đổi split/lọc vì kết quả cuối | Chỉ đọc metadata, không mở Test để tuning, không sửa dữ liệu | PASS (lượt này) |
| Đối chiếu freeze trước ký | Đã kiểm draft; chưa ký và chưa verify gói thực tế | BLOCKED |
| Output `reports/final-data-summary.md` | Báo cáo dự thảo này | PASS (phạm vi độc lập) |
| QA review và nghiệm thu cuối | Chưa có review | NOT RUN |

**Kết luận:** 352 là số mẫu bản DATA gốc, 218 là quy mô ứng viên model hiện tại; chưa có số mẫu nghiên cứu cuối được xác nhận. Báo cáo này không cấp phép mở Test, không chốt số liệu FINAL và không đóng Issue. Bàn giao dự thảo cho QA/ML/Integration đối chiếu; chưa commit/push/PR hoặc sửa bất kỳ file dataset/model nào.
