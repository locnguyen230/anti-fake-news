# Giao diện Predictor v0.1.1 — AFN-007 / AFN-008 / AFN-009

Trạng thái: **đề xuất (proposed)**, đang chờ ML và Extension review. Chưa có mô hình thật nào được triển khai.
AFN-009 bổ sung mock dev/test rõ ràng và adapter trạng thái suy luận.
`backend/app/predictor.py` vẫn là điểm nối định kiểu dùng chung (typed seam); chữ ký
input/output của nó không thay đổi. `backend/app/schemas.py` định nghĩa các ràng buộc dùng chung.

## Ranh giới Python đề xuất

```python
class PredictorInput(PredictFormFields):
    image_bytes: bytes

class Predictor(Protocol):
    def predict(self, inputs: PredictorInput) -> PredictionResult: ...
```

`PredictFormFields` chứa `request_id: UUID`, `title: str | None` (<=500 điểm mã Unicode
/ code points) và `text: str` (<=50.000 code points trước khi cắt khoảng trắng trim, không rỗng sau khi trim).
Tệp tải lên qua HTTP là một phần file multipart riêng biệt; không bao giờ là chuỗi byte JSON
hay URL hình ảnh. Tầng vận chuyển (transport) Backend thật sẽ xác thực dữ liệu vận chuyển, sau đó khởi tạo
`PredictorInput`. Trường bytes yêu cầu `bytes` không rỗng, nhưng chỉ riêng schema của nó thì
**không** xác thực MIME, giới hạn trần byte/pixel hay khả năng giải mã ảnh. Cầu nối mock (mock bridge)
kiểm tra các trường, sự hiện diện của tệp/bytes không rỗng và trần kích thước byte ảnh sau khi parse,
nhưng không giải mã hay xác thực ảnh. Đây không phải là bộ validator cho môi trường production.

**Đề xuất lựa chọn dạng ảnh: các byte JPEG/PNG đã mã hóa và được xác thực.** Điều này tránh phụ thuộc
Pillow, NumPy, Torch hay CLIP trong phần nền tảng (foundation). Backend #23 phải xác thực nội dung,
kích thước (<=20.000.000 pixel), dung lượng <=10 MiB, và định nghĩa cách xử lý EXIF/RGB.
ML chịu trách nhiệm về các biến đổi ảnh đặc thù của mô hình. Việc truyền các byte đã mã hóa hợp lệ có thể
yêu cầu ML phải giải mã lại; ML cần review xem liệu có nên thay thế ranh giới này bằng một đối tượng RGB đã giải mã hay không.
Trách nhiệm cụ thể về decode/hướng ảnh (orientation)/chuẩn hóa (normalization) phải được thống nhất
trước #23/#37. Việc thay đổi yêu cầu cập nhật phiên bản giao diện (versioned interface update), không phải
thay đổi ngầm định. Hiện tại chưa có mã giải mã nào được triển khai ở đây.

Truyền tiêu đề (title) tùy chọn và phần thân (body) đã trim riêng biệt. Backend chỉ xác thực độ dài/tính không rỗng
của tầng vận chuyển; không nối chuỗi (concatenate) hay cắt ngắn văn bản (truncate). ML chịu trách nhiệm
nối chuỗi nhất quán giữa huấn luyện/suy luận, tokenization, mức trần 1.500 từ được đề xuất và cách tính từ trong tiêu đề.
ML thiết lập `text_truncated` khi tiền xử lý thực hiện cắt ngắn văn bản.
Phạm vi đầu vào tiếng Anh và quy trình tiền xử lý chính xác đang chờ ML phê duyệt.
Không sử dụng request_id, URL, tên tệp hoặc nguồn gốc xuất xứ khác làm đặc trưng (features) cho mô hình.

## Đầu ra và xử lý lỗi

`PredictionResult` bao gồm:

| Trường | Kiểu dữ liệu / Trách nhiệm |
| --- | --- |
| `label` | Literal `fake` hoặc `real`, ngưỡng ML và ánh xạ phân lớp |
| `fake_score` | Số thực hữu hạn trong [0,1], không phải xác suất đã hiệu chuẩn (calibrated probability) |
| `model_version` | Chuỗi không rỗng từ metadata của mô hình tương thích thực tế |
| `model_id` | Chuỗi không rỗng định danh cấu hình mô hình thực tế |
| `text_truncated` | Kiểu bool nghiêm ngặt mô tả trạng thái tiền xử lý của ML |

Backend bổ sung UUID của request đã được parse an toàn và số nguyên không âm đơn điệu
`processing_time_ms` xung quanh lời gọi Predictor để xây dựng `PredictResponse`.
Thời gian xử lý bao gồm tiền xử lý của ML nhưng loại trừ việc tải artifact và vận chuyển HTTP.
Không cung cấp ID, thời gian hoặc kết quả tự bịa đặt khi chưa có mô hình nào được nạp.

`ModelNotReadyError` thể hiện mô hình/artifact bị thiếu, không khả dụng hoặc không tương thích.
Backend ánh xạ lỗi này thành mã 503 đã được làm sạch `model_not_ready`, tuyệt đối không trả về văn bản ngoại lệ gốc.
Adapter cũng đánh dấu provider của nó là `error` khi khởi tạo/gọi hàm/đầu ra không hợp lệ thất bại
và chỉ đưa ra `ModelNotReadyError`; không bao giờ tự động thử lại (retry) ngầm định
hay thay thế bằng đầu ra mock. Những lỗi này không được phân loại là đầu vào không hợp lệ (invalid input).
Chính sách xử lý lỗi cho mô hình thật vẫn cần ML review trước khi tích hợp. Không có thông điệp ngoại lệ
hay traceback nào được lưu giữ trong endpoint health công khai hoặc payload phản hồi.

## Vòng đời và tiêm phụ thuộc (Lifecycle & Dependency Injection)

`create_app(settings=None)` giải quyết cấu hình trong quá trình khởi động lifespan của ASGI
và tạo một `InferenceAdapter` cho mỗi lifespan tại `app.state.inference_adapter`.
Chế độ thực tế (real mode) mặc định sẽ để trạng thái là `not_loaded`, với `app.state.predictor = None`.
Mock dev/test tường minh sẽ khởi tạo `MockPredictor` và chỉ cài đặt adapter vào
`app.state.predictor` nếu ở trạng thái ready. Lỗi khởi động sẽ khiến dịch vụ vẫn chạy
nhưng trạng thái health báo lỗi (error-state) và `/predict` trả về 503. Quá trình tắt (shutdown) sẽ xóa các tham chiếu
provider và đặt lại về `not_loaded`; chưa có trình dọn dẹp tài nguyên/loader thực tế nào được triển khai.

`get_predictor(request)` giữ lại điểm hook DI hiện có. Endpoint health đọc adapter
thông qua `get_inference_adapter(request)`, ánh xạ tính sẵn sàng vào trường boolean JSON hiện có
và đưa mode/state vào header phản hồi. Gán trực tiếp vào vị trí `app.state.predictor` cũ
sẽ không làm thay đổi trạng thái health. Các bài kiểm thử có thể ghi đè (override) tường minh một trong hai
phụ thuộc. Chỉ các thành phần quản lý vòng đời mới được gọi `initialize(factory)`;
một factory thực tế trong tương lai phải kiểm tra tính tương thích/làm nóng (warm-up) trước khi trả về.

Các trạng thái gồm `not_loaded`, `ready`, `error`; xem [dev-mock.md](dev-mock.md) để biết
các chuyển thái (transitions). Endpoint `/predict` ở real-mode luôn trả về 503 trước khi đọc body,
kể cả khi đã override provider, cho đến khi công việc vận chuyển/tích hợp hoàn tất.
Cầu nối mock dev/test gọi Predictor đồng bộ tách khỏi vòng lặp sự kiện (event loop),
phản hồi lại UUID đã parse và đo thời gian xử lý. Kết quả cố định của nó có các ID
giả lập rõ ràng và không thực hiện tiền xử lý, kiểm tra ảnh hay đánh giá tính chân thật của bài báo.

Quy trình khởi động mô hình đề xuất trong tương lai: ML cung cấp package tương thích; Backend nạp
một lần, xác thực metadata và warm-up trước khi báo cáo trạng thái sẵn sàng (#37/#38).
Backend quản lý vòng đời tài nguyên/shutdown; ML định nghĩa các yêu cầu giải phóng tài nguyên và an toàn luồng (thread safety).
Predictor CPU đồng bộ phải chạy tách biệt khỏi event loop bất đồng bộ. Số lượng worker,
tuần tự hóa / an toàn luồng và hủy tác vụ (cancellation) cần ML review trước khi tích hợp;
nền tảng này khởi chạy một Uvicorn worker và không thực hiện suy luận thực tế.
Việc client hết thời gian chờ (timeout) không đảm bảo hủy bỏ được một tiến trình dự đoán đang chạy.

## Phân định trách nhiệm, phụ thuộc và quản lý phiên bản

- **Backend:** Phân tích cú pháp HTTP/form, token/chính sách, giới hạn luồng byte, xác thực
  ảnh theo #23, tương quan (correlation), đo thời gian, xử lý lỗi an toàn, DI và vòng đời dịch vụ.
- **ML:** Huấn luyện/artifacts, tiền xử lý và biến đổi mô hình, ánh xạ nhãn,
  ngưỡng, metadata kết quả, các phiên bản phụ thuộc ML tương thích.
- **Extension:** `analyze.js` tải lên, client ID/timeout, xử lý và hiển thị kết quả cũ/hết hạn;
  `service-worker.js` không gọi `/predict`.

Các yêu cầu ban đầu ghim các package backend và test đã được phân giải trên Python 3.10;
AFN-009 chỉ thêm `python-multipart==0.0.32` cho cầu nối mock. Các bài kiểm thử hiện tại
sử dụng Python 3.13.1 vì bản cài đặt cục bộ 3.10 trước đó không còn.
Không có bản kê khai phụ thuộc (dependency manifest) ML nào trong bản checkout này, do đó **tính
tương thích ML vẫn chưa được xác nhận**. Không thêm các bản ghim Torch/CLIP/scikit-learn
mang tính suy đoán hoặc thay đổi các tệp huấn luyện. ML phải cung cấp phiên bản Python và manifest
phụ thuộc của họ trước khi có thể kiểm thử môi trường kết hợp.

Hợp đồng v0.1.1 được chia sẻ với `docs/api-contract.md` và các fixture API đã được đánh phiên bản.
Bản vá bổ sung hành vi phát triển dạng opt-in cùng các header mode/state trong khi vẫn giữ nguyên
tập hợp các trường JSON và chữ ký Predictor. Điều này không ngụ ý sự phê duyệt từ phía consumer.
Những thay đổi đối với chữ ký, biểu diễn hình ảnh, các trường dữ liệu, ý nghĩa của tiền xử lý
hoặc các lỗi phát sinh đều yêu cầu cập nhật đồng bộ tài liệu/schema/fixture và thông báo cho
Backend, ML và Extension trước khi áp dụng. Các thay đổi phá vỡ tương thích (breaking changes)
sẽ tăng phiên bản minor khi ở giai đoạn pre-1.0; các điểm làm rõ tương thích sẽ tăng phiên bản patch.
Việc đánh phiên bản không ngụ ý bất kỳ sự phê duyệt nào.
