# Kết quả mô hình và giới hạn · AFN-051

**Chờ Test cuối và phân tích lỗi.** Phần phương pháp áp dụng cho ba cấu hình
ở giao thức AFN-004. Bản ứng viên `ml-v2` đã được chọn trên Validation, với
preprocessing `afn-preprocess-v1`. Kết quả Validation chỉ dùng để chọn cấu
hình và ngưỡng. [Giao thức](../docs/experiment-protocol.md) ·
[Lựa chọn ứng viên và hash](../configs/selected-models.json)

## RQ1 · Chất lượng của ba cấu hình trên cùng Test

So sánh Text-only (TF-IDF), Image-only (CLIP ViT-B/32) và Multimodal
(TF-IDF + CLIP). Dùng cùng ID và nhãn nguồn. Đọc C, ngưỡng và model version
từ phiên bản freeze AFN-049. Macro-F1 là trung bình F1 của hai lớp.

| Cấu hình | Macro-F1 | Accuracy | Precision / Recall / F1 / support `fake` | Precision / Recall / F1 / support `real` | Ma trận nhầm lẫn |
| --- | --- | --- | --- | --- | --- |
| Text-only | Chờ | Chờ | Chờ | Chờ | Chờ |
| Image-only | Chờ | Chờ | Chờ | Chờ | Chờ |
| Multimodal | Chờ | Chờ | Chờ | Chờ | Chờ |

Dùng thứ tự `fake, real` cho cả hàng nhãn nguồn và cột nhãn dự đoán.
Ma trận `[[a,b],[c,d]]` cho biết `a,d` dự đoán trùng nhãn và `b,c` nhầm
giữa hai lớp. Khi điền bảng, dẫn tới predictions theo ID, metrics và từng
ma trận, kèm phiên bản hoặc checksum đã bàn giao. Ghi dữ liệu ít hoặc thiếu
lớp nếu có.

## RQ2 · Thêm ảnh thay đổi kết quả bao nhiêu

Báo chênh lệch có dấu `Macro-F1(Multimodal) − Macro-F1(Text-only)` tính
trên thang 0–1, hoặc nhân 100 để báo theo điểm phần trăm. Chờ số liệu #50.
Kèm thay đổi số đếm nhầm lẫn theo lớp và đối chiếu Image-only để đặt kết
quả trong bối cảnh. Giữ kết luận giảm, bằng hoặc tăng theo số đo. Tập nhỏ
và các nhóm phụ thuộc nhau hạn chế độ chắc chắn của chênh lệch quan sát được.

## RQ3 · Hai cấu hình khác nhau ở những trường hợp nào

Ghép Text-only và Multimodal theo `sample_id` từ cùng Test. Với nhãn nguồn,
đếm cả hai đúng, chỉ Text-only đúng, chỉ Multimodal đúng và cả hai sai.
Tổng bốn nhóm phải khớp số ID Test. Trong hai nhóm bất đồng, so số đếm và
mẫu số theo nhãn, nguồn, nhóm sự kiện và cờ chất lượng xác định trước.
Ghi trường hợp metadata thiếu và số ca có thể rà, gồm ca dự đoán đúng.
Đối chiếu bằng báo cáo DATA #47 khi bàn giao và dẫn bằng chứng theo
quyền truy cập.

## Giới hạn diễn giải

`fake_score` là điểm của mô hình cho lớp `fake`, với nhãn dự đoán đặt theo
ngưỡng đã chọn trên Validation. Điểm chưa hiệu chuẩn thành xác suất. Phân
tích đo hiệu năng so với nhãn nguồn. Kiểm chứng sự thật cần bằng chứng độc
lập. Kết quả còn phụ thuộc độ phủ bài tiếng Anh, số mẫu/nhóm từng lớp,
khác biệt PolitiFact/GossipCop và thiên lệch khi URL, body hoặc ảnh không
khôi phục được. Phân tích Test phục vụ báo cáo theo giao thức đã khóa.
[Data card](../docs/data-card.md) · [Giao thức mở Test](../docs/experiment-protocol.md#mở-test-và-phân-tích)

## Cách đối chiếu số liệu khi bàn giao

Script đọc bản chuẩn hóa cho riêng báo cáo, schema `afn-report-metrics-v1`,
với ba ma trận đếm và thứ tự lớp tường minh. Script tính lại Macro-F1,
accuracy, metric từng lớp và Δ. Dùng fixture để kiểm tra đường đọc và trường
hợp Δ âm.

```sh
python scripts/summarize_model_results.py tests/fixtures/metrics/afn-report-metrics-v1.json
```

Khi #50 công bố schema, giữ nguyên các file gốc và chuyển ba ma trận đã xác
minh sang đầu vào chuẩn hóa với `evidence_kind: TEST_FINAL`. Đối chiếu
từng support, ma trận và Δ với số liệu chính thức. Đồng nhất support chỉ
là phép kiểm số đếm. Dùng predictions để kiểm tra đúng tập ID và hash.
Nhãn `FIXTURE_NOT_RESEARCH` đánh dấu dữ liệu tổng hợp dùng thử script.

| Đầu vào còn chờ | Owner | Phiên bản bằng chứng cần có |
| --- | --- | --- |
| #46 · quy mô và phân bố | DATA `locnguyen230` | Bản thống kê cuối cùng manifest/split đã khóa |
| #47 · lỗi và bất đồng | DATA `locnguyen230` | Phân tích ghép ID dựa trên predictions #50 |
| #49/#50 · freeze và kết quả | ML `0xDa1Vu` | Biên bản freeze và một lượt Test trên cùng bộ hash |

Review báo cáo sau khi #46, #47 và #50 bàn giao. [#46](https://github.com/ngnsusinn/anti-fake-news/issues/46) ·
[#47](https://github.com/ngnsusinn/anti-fake-news/issues/47) ·
[#49](https://github.com/ngnsusinn/anti-fake-news/issues/49) ·
[#50](https://github.com/ngnsusinn/anti-fake-news/issues/50)
