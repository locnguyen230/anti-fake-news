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

Đã rà sơ bộ tiêu đề nguồn của cả 13 cặp. Hai cặp qua split có tên người trùng nhưng tiêu đề mô tả tình huống khác nhau. Chưa có cặp nào đủ bằng chứng để gán cùng event ID. Nhận định theo cặp được lưu trong `event-review-draft.csv` của QA để DATA đối chiếu.

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

## Xác thực URL và thử tách publisher trước freeze

Ngày 25/11/2026. Gửi HEAD đến 218 URL nguồn, theo tối đa bốn chuyển hướng
trong mỗi lượt kiểm. Kiểm URL công khai và ghi hostname phản hồi. Không
tải thân bài, ảnh hoặc dự đoán Test. Điểm đo là trạng thái server tại thời
gian kiểm tra. HEAD 2xx chỉ xác nhận URL phản hồi, còn publisher của nội
dung đã thu hồi và quyền sử dụng cần bằng chứng riêng.

| Kết quả HEAD | Số mẫu |
| --- | ---: |
| 2xx cùng hostname đề xuất | 126 |
| 2xx trên hostname khác | 24 |
| 2xx tại trang gốc/landing page | 4 |
| 403 | 40 |
| 404 | 8 |
| HTTP khác | 7 |
| Timeout hoặc lỗi kết nối/URL | 9 |
| Tổng | 218 |

QA giữ bảng `publisher-review.csv` cùng URL nguồn và hostname cuối theo
ID để xác minh hai trường hợp chuyển hướng và website chặn HEAD. SHA-256
của bảng là `560815c314e6e43e08f0d73a881d90f74a796426c0553448c99578ae630fa36a`.
Manifest Train/Validation hiện có **185/185 dòng `rights: unverified`**.
Quyền sử dụng được quyết định theo điều khoản và bằng chứng từng tài nguyên.
[Hợp đồng dữ liệu](../docs/data-contract.md)

### Thử cách ly xung đột và giữ nguyên Test

Dùng các nhóm `ml-v2` làm nền, nối bắc cầu theo hostname đề xuất. Thử thêm
một phương án nhạy cảm coi cả 13 cặp tiêu đề là cạnh tiềm năng. Giữ đúng
33 ID Test. Cách ly dòng Train/Validation chung thành phần liên thông với
Test và chia phần còn lại theo nhóm. Chọn nhóm Validation gần 15% tổng số
mẫu giữ lại, cân đối nguồn × nhãn và ưu tiên ít đổi tập khi hòa. Kiểm lại
tập ID Test và xác nhận hostname xuất hiện ở đúng một split trong phần giữ lại.

| Kịch bản | Train | Validation | Test khóa | Cách ly | Mẫu giữ lại | Thiếu so với 200 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nối hostname | 118 | 27 | 33 | 40 | 178 | 22 |
| Nối hostname và 13 cặp ứng viên để thử độ nhạy | 104 | 24 | 33 | 57 | 161 | 39 |

Cả ba split đủ hai nhãn trong cả hai kịch bản. Phương án đầu có 79/18/30
nhóm. Phương án nhạy cảm có 74/18/29 nhóm. Chia tự do theo bộ phân bổ
hiện hành cho tỷ lệ gần 70/15/15 nhưng sẽ đưa 26 ID Test cũ vào
Train/Validation, nên phương án đó chỉ dùng làm đối chứng tính toán.
Nếu điều chỉnh bằng cách chuyển toàn bộ nhóm xung đột vào Test, Test tăng
từ 33 lên 73 mẫu trước khi xét cạnh sự kiện.

CSV hai bản nháp giữ riêng ở QA. SHA-256 lần lượt là
`156f17ea5b0d28ddb6317bd9bb3e4d3fb8a98bfe9722c5a26e2f1766cfed5d6c` và
`80b91f603daae6cf547e36a48e3b7b7ca06a3008275ffd66167961af21e9df98`.
Chưa dùng các bảng để huấn luyện, mở Test hoặc thay split chính thức.

DATA cần xác nhận publisher/event và quyền sử dụng, sau đó chọn tập nháp
để bổ sung mẫu hợp lệ từ nhóm độc lập với Test. Nếu mọi mẫu trong bản
nháp được chấp thuận, bản nối hostname cần tối thiểu 22 mẫu để đạt mục
tiêu 200. Nếu giữ quy mô dưới mục tiêu, DATA/ML/QA cần chốt phạm vi nghiên
cứu thăm dò theo thiết kế. QA ký split phiên bản mới trước lượt
Train/Validation làm bằng chứng nghiệm thu. Freeze #49 còn yêu cầu đúng
artifact, tham số và chữ ký ML/QA. [Thiết kế](../DESIGN.md) ·
[AFN-049](https://github.com/ngnsusinn/anti-fake-news/issues/49)

## Sàng lọc bổ sung và duyệt theo tài nguyên

Ngày 25/11/2026. Quét bốn CSV ghim SHA-256, loại ID đã có trong danh sách
218 mẫu rồi chuẩn hóa URL theo quy tắc AFN-017. Đối chiếu nhãn nguồn trên
toàn bộ CSV và so hostname với Test khóa. Có 22.647 dòng URL hợp lệ chưa
có trong danh sách 218, với quyết định sàng lọc dưới đây. Số đếm là số dòng
metadata, không phải số bài đủ điều kiện.

| Quyết định | Dòng |
| --- | ---: |
| Loại vì URL chuẩn hóa có cả hai nhãn nguồn | 308 |
| Cách ly vì hostname trùng Test khóa | 2.821 |
| Đã kiểm từng tài nguyên, cùng publisher với Test khóa | 1 |
| Đã kiểm từng tài nguyên, thân bài vượt giới hạn | 2 |
| Ưu tiên kiểm quyền từng bài và ảnh | 106 |
| Chờ xác định loại bài và quyền ảnh riêng | 656 |
| Chờ bằng chứng quyền từng tài nguyên | 18.753 |

Gói FakeNewsNet cung cấp URL, ID và metadata. Quyền dùng bài và ảnh
được đối chiếu theo từng tài nguyên. Nguồn cơ quan nhà nước được ưu
tiên tra cứu vì có thể tìm được thông tin quyền rõ ràng. Chỉ nhìn
hostname cơ quan chưa đủ để suy ra quyền của ảnh do bên thứ ba cung
cấp. [FakeNewsNet](https://github.com/KaiDMML/FakeNewsNet#overview) ·
[USAGov về nội dung cơ quan liên bang](https://www.usa.gov/government-copyright)

### Quyết định đã đối chiếu trực tiếp

- Ghép ba ID `politifact_real` chưa dùng với bài chính thức trong kho
  lưu trữ Nhà Trắng. Xác nhận publisher, ngày/sự kiện và chính sách quyền.
  Đối chiếu ảnh Pete Souza do Nhà Trắng công bố cùng sự kiện, sau đó
  kiểm giải mã JPEG và SHA-256. Hai bản ghi toàn văn dài 55.996 và
  58.310 ký tự vượt giới hạn 50.000. Bài Scranton dài 20.818 ký tự
  qua kiểm text/ảnh. Publisher này đã xuất hiện trong Test khóa nên
  cả ba nằm ngoài Train/Validation. Giữ nhãn nguồn và không đưa thêm
  ID vào Test. [Chính sách quyền](https://obamawhitehouse.archives.gov/copyright) ·
  [Bài Scranton](https://obamawhitehouse.archives.gov/the-press-office/2011/11/30/remarks-president-american-jobs-act-0) ·
  [Ảnh chính thức](https://obamawhitehouse.archives.gov/photos-and-video/photo/2011/11/20111130-potus-scranton)
- Rà bốn mẫu Train/Validation thuộc nguồn cơ quan trong bản nháp nối
  hostname. Loại trang hỏi đáp của National Archives và bảng chuỗi
  thống kê CES của BLS vì loại nội dung không đạt tiêu chí bài viết.
  Hai mẫu còn lại có hồ sơ chờ quyền ảnh. [National Archives](https://www.archives.gov/presidential-libraries/about/frequently-asked-questions) ·
  [BLS CES](https://www.bls.gov/ces/data/)

Sau khi loại thêm hai mẫu sai loại, đã cân bằng lại phần Train/Validation
ở hai kịch bản. Test giữ đúng tập 33 ID cũ. Các tập vẫn có hai lớp và giữ
nguyên thành phần nhóm ở mỗi split.

| Kịch bản | Train / Validation / Test khóa | Mẫu còn trong bản nháp | Thiếu để đạt 200 |
| --- | --- | ---: | ---: |
| Nối hostname | 117 / 26 / 33 | 176 | 24 |
| Thêm các cạnh sự kiện ứng viên để thử độ nhạy | 102 / 24 / 33 | 159 | 41 |

Các bảng sàng lọc và quyết định theo ID nằm trong thư mục
`data/private/afn-029-provenance/supplemental-review/`. Hai CSV split đã
rà nằm ở cùng vùng QA, có tên `qa-split-screened-*.csv`. SHA-256 của bản
nối hostname là `6cb2a123ffaf7680108f1e300ffb10fb2708028b184d17028fb0ca073d3f46ce`.
Chưa có mẫu bổ sung đủ điều kiện nhập split. Mốc thiếu 24 giả định tất cả
176 mẫu trong bản nháp sẽ được xác nhận quyền và metadata. Quy mô dưới
200 chỉ dùng cho hướng thăm dò theo điều kiện của nhóm. Không thay
manifest, nhãn hoặc split đã dùng ở #34. [Phạm vi dữ liệu](../DEFINE.md)

## Đối chiếu nhãn với đúng bài trước khi thay mẫu

Ngày 25/11/2026. So URL FakeNewsNet với đối tượng được chấm trong bài
fact-check. Một URL có quyền dùng vẫn bị loại nếu nhãn áp dụng cho một
bài hoặc phát ngôn khác.

| URL nguồn đối chiếu | Quyết định |
| --- | --- |
| Thông cáo DOJ về việc Jeff Sessions rút khỏi cuộc điều tra | Loại ứng viên. Thông cáo là nguồn dẫn; bài trên The Conservative Patriot mới là đối tượng được chấm. [Fact-check](https://politifact.com/factchecks/2018/may/23/blog-posting/false-claim-jeff-sessions-caught-collud/) |
| Thông cáo FDA về hiệu quả vaccine cúm | Loại ứng viên. Nhãn áp dụng cho tiêu đề Meddaily; FDA là nguồn dẫn. [Fact-check](https://politifact.com/factchecks/2018/mar/09/meddaily/no-flu-shot-was-not-designed-spread-cancer/) |
| Tuyên bố chung DHS/ODNI | Loại ứng viên. Bài fact-check chấm phát ngôn tranh luận; tuyên bố là bằng chứng được dẫn. [Fact-check](https://api.politifact.com/factchecks/2016/oct/20/hillary-clinton/hillary-clinton-blames-russia-putin-wikileaks-rele/) |
| Thông báo thu hồi sản phẩm CPSC năm 2017 | Loại khỏi bản nháp. Bài được chấm đăng năm 2018 đã dùng lại thông tin thu hồi cũ. [Thông báo CPSC](https://www.cpsc.gov/Recalls/2017/target-recalls-water-absorbing-toys) · [Fact-check](https://politifact.com/factchecks/2018/mar/06/blog-posting/website-recycles-2017-information-claim-target-rec/) |
| Bản ghi phỏng vấn Democracy Now! | Loại khỏi danh sách thay thế. Có quyền đăng lại transcript khi ghi công, nhưng PolitiFact chấm nhiều phát ngôn khác nhau trong cùng cuộc phỏng vấn. [Quyền transcript](https://www.democracynow.org/get_involved/spread_the_word/reprint_transcripts) · [Các phán quyết](https://politifact.com/article/2008/jun/30/nader-on-the-attack/) |
| Hai bài The Conversation | Chờ bằng chứng. Xác minh được tác giả và bài đăng lại. Bài gắn nhãn `fake` còn thiếu bằng chứng nhãn áp dụng đúng bài; bài còn lại dùng ảnh ghi công AP. Điều khoản đăng lại bài và quyền ảnh cần đối chiếu riêng. [Bài của Ronald Hall](https://atlantadailyworld.com/2018/02/05/black-americas-bleaching-syndrome/) · [Bài của Ashraf Rushdy](https://newsletter.blogs.wesleyan.edu/2018/02/13/ashraf-rushdy-in-the-conversation-the-art-of-the-public-apology/) · [Hướng dẫn đăng lại](https://theconversation.com/us/republishing-guidelines) |

Danh sách quyết định và nguồn theo ID được giữ ở vùng QA. Chạy lại bản
chia nháp sau khi bỏ thêm dòng CPSC. Kiểm đủ hai lớp ở mỗi split, hash
của cả hai CSV và giữ nguyên đúng 33 ID Test.

| Kịch bản | Train / Validation / Test | Tổng | Thiếu để đạt 200 |
| --- | --- | ---: | ---: |
| Nối hostname | 116 / 26 / 33 | 175 | 25 |
| Thêm các cạnh sự kiện ứng viên | 101 / 24 / 33 | 158 | 42 |

SHA-256 của bản nháp nối hostname là
`1f45fa9b6a98b54d835cc6556ba6d50f0675e0ce0ccb58e4cd70b84a9b9a171d`.
Chưa có mẫu mới vượt qua cả cổng nhãn, quyền bài/ảnh và quan hệ với Test.
Mốc thiếu 25 giả định cả 175 mẫu còn lại đều được duyệt. Giữ nguyên bản
chính thức và không dùng bản nháp để huấn luyện.

## Duyệt bản thăm dò 175 mẫu

Ngày 25/11/2026. Bỏ mục tiêu tối thiểu 200 theo quyết định của chủ repo.
Đối chiếu từng ID trong bản nháp `116/26/33` với nguồn và split gốc. Không
có nhóm hoặc hostname đề xuất giao giữa các split. 142 mẫu Train/Validation
đạt kiểm tra tiền xử lý văn bản, checksum và giải mã ảnh. Các phép kiểm
này xác nhận tính toàn vẹn kỹ thuật của tệp.

| Kết quả duyệt | Số mẫu |
| --- | ---: |
| Loại trang tham khảo bách khoa khỏi nhóm bài nghiên cứu | 8 |
| Chờ bằng chứng quyền từng bài/ảnh và đối chiếu đúng đối tượng nhãn | 132 |
| Chờ giấy phép riêng cho hai publisher có chính sách công bố quyền | 2 |
| Test giữ nguyên và chỉ kiểm metadata QA | 33 |
| Có đủ bằng chứng để phát hành công khai | 0 |

Hai mẫu chờ giấy phép riêng đến từ WBUR và Jamaica Information Service.
Bảng quyết định theo ID nằm trong `data/private/afn-029-provenance/review175/`.
Số liệu công khai và checksum của bản chia nằm trong
[bản tổng hợp QA](afn-029-exploratory-review.json).
[Chính sách WBUR](https://www.wbur.org/inside/licensing-wbur-content) ·
[Thông báo quyền JIS](https://jis.gov.jm/category/opm/page/70/?category=health)

Trạng thái nghiệm thu dữ liệu tiếp tục `BLOCKED`. Bỏ mốc số lượng cho
phép đánh giá thăm dò khi có tập đã được duyệt với hai lớp và nhóm độc
lập. 33 ID Test được giữ nguyên và payload vẫn khóa theo #49. Chưa chấp
thuận mẫu nào cho huấn luyện hoặc phát hành dựa trên lượt duyệt này.

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
