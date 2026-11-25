# AFN-034: Train/Validation trên dữ liệu thật (dataset ml-v2)

Ngày chạy: 25/11/2026, macOS M1, CPU, CLIP ViT-B/32 đã ghim. `evidence_kind: VALIDATION_ONLY`.
**Test chưa được nạp** (33 dòng bị khóa tới khi #49 ký freeze). Protocol `configs/experiment.yaml` vẫn ở trạng thái `proposed`.

## 1. Chuẩn bị dữ liệu (`ml.prepare_dataset`)

Đầu vào: bản xuất DATA đã merge ở PR #87 (`data/processed/manifest.json`, SHA-256 `0d17dae8…`;
`groups.json`, SHA-256 `3bf91993…`). Bản này không theo định dạng `afn-manifest-v1`, và split cũ
có các mẫu trùng ảnh/body nằm ở cả Train lẫn Val/Test, nên ML làm thêm một bước chuẩn bị:

1. **Lọc** theo luật cố định, không nhìn nhãn hay kết quả mô hình. Có test kiểm tra rằng đảo
   nhãn không làm đổi quyết định.

   | Lý do loại | Luật | Số mẫu |
   | --- | --- | ---: |
   | `missing_image` | không có ảnh | 66 |
   | `image_too_small` | cạnh ngắn < 64 px (favicon, placeholder) | 36 |
   | `body_too_short` | body < 50 từ (menu, chú thích, trang paywall) | 14 |
   | `missing_body` | body rỗng | 12 |
   | `body_too_long` | body > 50.000 ký tự (data contract) | 3 |
   | `boilerplate_body` | cùng body nhưng khác tiêu đề (footer trang) | 3 |

   Mỗi mẫu chỉ được tính theo lý do đầu tiên. Còn lại **218/352** mẫu.
2. **Gom nhóm lại** theo đúng luật AFN-017 (`scripts/group_samples.RULES`): trùng hash body/ảnh,
   văn bản gần trùng, cặp tiêu đề + nội dung, pHash ảnh ≤ 4. Các group gốc của DATA được giữ
   nguyên. Bản xuất không có URL/publisher/event nên không dùng được các khóa đó.
   Kết quả: 208 group (205 group 1 mẫu, 2 group 2 mẫu, 1 group 9 mẫu dùng chung ảnh).
3. **Chia lại** bằng `scripts/split_data.assign_groups` (seed 42, 70/15/15 theo group).

| Split | Mẫu | Group | gossipcop fake/real | politifact fake/real |
| --- | ---: | ---: | --- | --- |
| Train | 153 | 143 | 50 / 57 | 30 / 16 |
| Validation | 32 | 32 | 11 / 12 | 6 / 3 |
| Test (khóa) | 33 | 33 | (chỉ QA xem) | |

Kiểm tra sau khi chia: không có ảnh, body hay tiêu đề trùng nằm ở hai split khác nhau; không có group nào nằm ở nhiều split.
Gói cho ML (`data/private/ml-v2/train-validation/`, gitignored):
`manifest.jsonl` SHA-256 `a42af272…`, `split.csv` SHA-256 `81058045…`. Gói `qa-only/` chứa
payload Test, split đầy đủ, toàn bộ quyết định lọc và các cạnh gom nhóm để QA đối chiếu (#29).

## 2. #34: chọn C/ngưỡng trên Validation

Fit trên Train (153 mẫu), chọn trên Validation (32 mẫu) theo protocol AFN-004. Không refit trên Train+Val.

| Cấu hình | Số chiều | C | Ngưỡng | Macro-F1 Val |
| --- | ---: | ---: | ---: | ---: |
| Text-only | 5000 | 10 | 0,60 | **0,686** |
| Image-only | 512 | 10 | 0,30 | 0,536 |
| Multimodal | 5512 | 100 | 0,70 | 0,624 |

Macro-F1 tốt nhất theo từng C:
- Text: 0,683 / 0,648 / 0,683 / 0,686 / 0,683
- Image: 0,520 / 0,527 / 0,533 / 0,536 / 0,491
- Multimodal: 0,590 / 0,527 / 0,556 / 0,593 / 0,624

(C = 0,01 → 100). Không có cảnh báo không hội tụ.

**Đọc kết quả cho đúng:** Validation chỉ có 32 mẫu, mỗi mẫu đoán sai làm Macro-F1 đổi khoảng 3 điểm.
Chênh lệch giữa các C và giữa các cấu hình phần lớn nằm trong mức nhiễu này. Image-only gần mức
đoán ngẫu nhiên. Multimodal chưa vượt Text-only trên Validation. Theo protocol, điều này được báo
cáo đúng như số đo, không ép Multimodal phải thắng. Đây chưa phải kết quả cuối: kết quả cuối là Test (#50), chạy sau #49.

Run: `cache/runs/20261125T144056Z/results.json`.

## 3. Còn mở

- DATA/QA cần xác nhận các luật lọc và bản chia lại `ml-v2` (thay cho `data/split/*.json`), và đưa
  Test cùng payload gốc ra khỏi repo công khai.
- `rights` của các mẫu đang ghi `unverified`: bản xuất chưa có bằng chứng quyền theo publisher.
- PolitiFact-real chỉ còn 16 mẫu Train và 3 mẫu Val, nên số liệu theo nguồn rất không ổn định.
- Xuất gói ứng viên (#35) và kiểm tra parity (#36) nằm ở các PR riêng, xếp chồng lên PR này.
- #49 (freeze) và #50 (Test) chưa chạy. Thứ tự cần giữ: protocol được khóa, #49 ký, rồi #50 mới chấm Test một lần.

## Lệnh tái lập

```sh
.venv/bin/python -m ml.prepare_dataset --manifest data/processed/manifest.json \
    --groups data/processed/groups.json --image-root data --out data/private/ml-v2
H=data/private/ml-v2/train-validation
.venv/bin/python -m ml.run_experiments --manifest $H/manifest.jsonl --split $H/split.csv --image-root data --offline
```

`ml.prepare_dataset` import script của DATA nên cần `jsonschema` (chưa có trong requirements).
