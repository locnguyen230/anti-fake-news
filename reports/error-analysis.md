# AFN-047 · Phân loại lỗi và trường hợp hai cấu hình bất đồng

**26/11/2026 — BLOCKED / NOT RUN (Test cuối).** Báo cáo chuẩn bị cho RQ3, không phải kết quả đánh giá mô hình. Phạm vi độc lập đã triển khai và kiểm thử trên fixture; chưa mở Test, chưa phân tích dự đoán Test thật.

- DATA: `locnguyen230`; reviewer: QA `dangnguyen0512`; ưu tiên P0; hạn 14/12/2026.
- Issue: [AFN-047](https://github.com/ngnsusinn/anti-fake-news/issues/47); snapshot đọc: `b94deff881fa66842e32dbf03848cb0789a045f9`.
- Truy vết: RQ3, FR-08, DESIGN §10.4 theo issue; quy tắc thực tế tại [giao thức AFN-004](../docs/experiment-protocol.md#mở-test-và-phân-tích). Số mục DESIGN trong issue có thể khác bản tài liệu hiện hành.
- Nguồn: [AFN-050 evaluator](../ml/evaluate_test.py), [freeze](../release/model-freeze.json), [biên bản](pre-test-signoff.md), [data card](../docs/data-card.md), [kết quả mô hình](model-results.md).

## 1. Đầu vào và điều kiện hiện hành

| Đầu vào | Trạng thái tại snapshot | Owner / điều kiện |
|---|---|---|
| AFN-004 | Protocol `locked` | Đã merge [#111](https://github.com/ngnsusinn/anti-fake-news/pull/111) |
| AFN-046 | [Báo cáo ứng viên](final-data-summary.md) đã merge | DATA/QA duyệt số liệu và bàn giao hash báo cáo |
| AFN-049 | Freeze `draft`; ML `0xDa1Vu` đã ký run `20261126T024649Z` | QA xác minh gói bàn giao và ký cùng canonical record hash |
| AFN-050 | Closed – Not planned; code evaluator có, chưa có predictions/metrics Test | ML bàn giao kết quả thật sau freeze hợp lệ |
| Cờ chất lượng trước Test | Chưa có gói metadata đã duyệt được truy xuất | DATA/QA bàn giao cờ và hash độc lập |

Bản ứng viên `ml-v2` có 153 Train, 32 Validation và 33 dòng Test khóa, theo [AFN-034](ml-train-validation.md). Đây là số lượng dự kiến của phiên bản ứng viên, **không phải số mẫu Test đã đánh giá**. Bản DATA 352 mẫu không được dùng để thay thế dữ liệu ML. Các phương án QA thăm dò khác không phải dataset cuối.

Hash Train/Validation manifest khai báo: `a42af272426dc73019dd1f7b010de9feb1f3fb67f8b2740c672f6a34a237f44a`.
Hash split CSV ẩn ID Test khai báo: `81058045c8397ed9cce8645267466e79a2fc346606865e05ade9b303b77b9c1f`.
Hai hash trên nằm trong hồ sơ đã có chữ ký ML. Hồ sơ còn chờ QA xác minh gói bàn giao và ký. Không đọc payload Test hoặc chạy evaluator để tạo số liệu thay thế. Không dùng số liệu Validation làm kết quả Test.

## 2. Phương pháp (RQ3)

Input sau khi AFN-050 bàn giao: `test-predictions.jsonl` (mỗi dòng có `sample_id`, `group_id`, `source_label`, `text_truncated`, `predictions[text-only|multimodal]` gồm `fake_score`, `label`, `model_version`); `test-metrics.json` schema `afn-test-metrics-v1`; freeze đã ký; manifest Test và CSV QA; CSV đã khóa ẩn ID Test; báo cáo AFN-046 được QA duyệt và hash; tùy chọn bảng cờ chất lượng lập theo quy tắc trước Test.

Process: xác nhận freeze/status/signoffs, đối chiếu hash và model version, đọc ID/group từ split, xác nhận cùng Train/Validation assignments và đa tập group Test, join 1–1 predictions/manifest/split, kiểm nhãn nguồn và threshold, đối chiếu tổng, support và confusion matrix của hai mô hình. Không inner join làm mất mẫu; duplicate/missing/extra ID là lỗi dừng. Không fit, không gọi model, không sửa đầu vào.

| Kết quả | Điều kiện | Số đếm Test | Tỷ lệ |
|---|---|---:|---:|
| `both_correct` | Cả Text và MM đúng nhãn nguồn | Chưa đo | N/A |
| `both_wrong` | Cả hai sai nhãn nguồn | Chưa đo | N/A |
| `text_only_correct` | Text đúng, MM sai | Chưa đo | N/A |
| `multimodal_only_correct` | Text sai, MM đúng | Chưa đo | N/A |
| Tổng | Bốn nhóm rời nhau và phủ toàn bộ Test | Chưa đo | N/A |

Khi có dữ liệu: tổng bốn nhóm = n_test; số bất đồng = chỉ Text đúng + chỉ MM đúng (hai lớp); số đúng Text = cả hai đúng + chỉ Text đúng; số đúng MM = cả hai đúng + chỉ MM đúng. Tỷ lệ dùng mẫu số toàn Test hoặc đúng số mẫu trong phân tầng. Không suy diễn số cặp từ confusion matrix riêng lẻ.

## 3. Taxonomy đề xuất trước Test (chờ QA duyệt)

| Chiều | Giá trị / quy tắc | Giới hạn |
|---|---|---|
| Nhãn | `fake`, `real` từ manifest và predictions | Nhãn nguồn không đồng nghĩa fact-check độc lập |
| Source | `gossipcop`, `politifact`; thêm tổ hợp source × label | Không đồng nhất source với publisher |
| Publisher | Có metadata / unknown | Không tự suy diễn hostname là publisher đã xác minh |
| Event | `event_id` đã duyệt hoặc unknown | Không dùng group_id thay cho event_id |
| Group | Ghép theo `group_id` từ split khóa, báo cáo theo kích thước group | Các mẫu trong cùng group có thể phụ thuộc nhau |
| Text truncation | `text_truncated` true/false từ AFN-050 | Cờ theo preprocessing, không chứng minh lỗi do cắt văn bản |
| Text quality | `short_body`, `boilerplate`, `wrong_article`, `paywall`, `unsupported_language` | Chỉ lấy cờ theo metadata QA đã duyệt; không suy ra từ dự đoán |
| Image quality | `low_resolution`, `logo_or_placeholder`, `irrelevant_image`, `unverified_image` | Chỉ lấy cờ theo metadata QA đã duyệt; không tự phân tích ảnh Test |

Các cờ text/image có thể chồng lấp, vì vậy không cộng các hàng cờ thành N. `unknown` nghĩa là chưa có metadata; `none_recorded` nghĩa là có bản ghi cờ nhưng danh sách rỗng, không bảo đảm mẫu sạch. Không loại mẫu vì cờ lỗi. Bảng cờ được lập theo tiêu chí đã chốt trước khi xem dự đoán, lưu riêng tư; hash do QA bàn giao. Nếu cần rà định tính sau Test, dùng cùng rubric, ghi số ca rà được gồm cả ca đúng, không tuning hay loại mẫu; chỉ xuất mô tả tổng hợp được phép. Không xuất URL, text, ảnh, sample ID hoặc tên group/event gốc. Báo cáo nhóm theo kích thước và đếm có/thiếu metadata publisher hoặc event. QA rà nguy cơ tái định danh từ các ô nhỏ trước công bố. Không gọi kết quả là kiểm chứng ảnh–text, không quy mọi bất đồng cho ảnh: khác biệt đặc trưng, tham số và ngưỡng đều có thể góp phần.

## 4. Công cụ và cách tái lập

File hỗ trợ: `scripts/analyze_errors.py` (tái dùng kiểm tra split và freeze của ML; đọc metadata và dự đoán, xuất hai file trong thư mục mới); `tests/data/test_analyze_errors.py`. Không thay đổi interface ML. Schema đầu ra `afn-error-analysis-v1` là schema riêng của báo cáo DATA, không phải giao diện AFN-050.

Kiểm thử trên dữ liệu tổng hợp:

```sh
python -m py_compile scripts/analyze_errors.py
python -m pytest tests/data/test_analyze_errors.py -q
```

Kết quả: **14 passed**; fixture có đủ bốn nhóm, mỗi nhóm 1/4. Đây chỉ là bằng chứng kiểm thử logic, không đưa số fixture vào bảng Test hoặc JSON nghiên cứu. Các ca lỗi gồm draft freeze, fixture bị dùng như nghiên cứu, hash sai, signature hash sai, coverage/nhãn/group/threshold/model version sai, duplicate ID, matrix sai, cờ chất lượng, CLI không ghi đè.

Sau khi QA xác nhận AFN-046 và AFN-050, chạy trên môi trường có quyền đọc gói QA. Ví dụ PowerShell (đường dẫn `ml-v2` chỉ là ví dụ của candidate hiện tại, thay bằng phiên bản thực sự khóa; hash báo cáo nhận độc lập từ QA, không tự tạo phê duyệt):

```powershell
python -m scripts.analyze_errors `
  --freeze release/model-freeze.json `
  --metrics reports/test-metrics.json `
  --predictions reports/test-predictions.jsonl `
  --manifest data/private/ml-v2/qa-only/manifest-test.jsonl `
  --qa-split data/private/ml-v2/qa-only/split.csv `
  --locked-split data/private/ml-v2/train-validation/split.csv `
  --summary reports/final-data-summary.md `
  --summary-sha256 <SHA256_DA_DUYET_BOI_QA> `
  --out-dir data/private/afn-047-analysis-v1
```

Tùy chọn `--quality-flags <path>` và `--quality-sha256 <hash-tu-QA>` đi cùng nhau; mỗi dòng JSONL có `sample_id`, `text_flags`, `image_flags`. Mỗi ID xuất hiện tối đa một lần, chỉ từ Test đã bàn giao. Nếu chưa có cờ thì ghi unknown. Không dùng file flags tự tạo sau khi biết lỗi để thay thế metadata trước Test.

Script đối chiếu cấu trúc chữ ký/hash theo `ml.freeze.canonical_sha256`, không thay thế `ml.freeze verify` hoặc xác nhận danh tính người ký; QA phải xác nhận evaluator đã chạy hợp lệ và AFN-046 đã duyệt. Kiểm hash báo cáo AFN-046 và sự hiện diện hai hash dữ liệu trong nội dung không chứng minh tất cả số liệu của báo cáo là đúng: QA đối chiếu riêng. Kết quả thật xuất `PENDING_QA_REVIEW` cho đến khi review. Sau review, chỉ đưa hai file tổng hợp đã kiểm quyền vào `reports/`, không commit dữ liệu private. Giữ quy tắc không ghi đè thư mục kết quả để bảo toàn bằng chứng.

## 5. Nghiệm thu và bàn giao

| Tiêu chí | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| Ghép predictions theo ID và nhãn | PASS trên fixture | `scripts/analyze_errors.py` + pytest |
| Đếm đủ bốn nhóm | PASS trên fixture; Test NOT RUN | Kiểm phủ ID, support và confusion matrix |
| Taxonomy theo nhãn, nguồn/event, chất lượng | PARTIAL | Có rubric đề xuất, QA cần chốt cờ trước Test |
| Số đếm cộng đủ Test và truy nguồn | BLOCKED | Chờ #50 predictions/metrics thật và #46 đã duyệt |
| Không loại Test/chỉnh model sau xem lỗi | PASS phạm vi triển khai | Script chỉ đọc; không chạy inference/training |
| Không suy diễn ảnh hoặc kiểm chứng ảnh–text | PASS phạm vi tài liệu | Mục 3 và giới hạn báo cáo |
| Chỉ phân tích Test sau AFN-050 | PASS guard trên fixture; Test NOT RUN | Cổng freeze + evidence kind + hash |
| QA review, Done | BLOCKED | #46, #50, QA review và cờ chất lượng hợp lệ |

Đã kiểm thử công cụ bằng fixture tổng hợp. Kết quả Test vẫn ở trạng thái `NOT_RUN` cho đến khi đủ chữ ký, QA duyệt báo cáo AFN-046 và AFN-050 bàn giao đầu ra thật.
