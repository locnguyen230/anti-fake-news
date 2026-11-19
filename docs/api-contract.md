# Hợp đồng API v0.1.1 — AFN-008 / AFN-009

Trạng thái: **bản thảo để Backend / ML / Extension review**, không phải biên bản phê duyệt.
URL cơ sở: `http://127.0.0.1:8000`. Các route hiện chưa đánh số phiên bản; phiên bản hợp đồng
được trả về qua endpoint health. Tất cả các ví dụ request/response bên dưới chỉ mang tính **minh họa**,
không phải bằng chứng về kết quả dự đoán hay hiệu năng.

## Bề mặt hiện thực hóa so với mục tiêu

| Endpoint | Hành vi thực tế/mặc định hiện tại | Mục tiêu sau các phần việc hoãn lại |
| --- | --- | --- |
| `GET /health` | 200, service ok, model_ready false | Trạng thái sẵn sàng an toàn của dịch vụ/mô hình |
| `POST /predict` | Luôn trả về 503, không đọc body request, không kiểm tra token, không suy luận | Đầu vào multipart đã xác thực và kết quả Predictor thật |

AFN-009 bổ sung một **chế độ mock dev/test tường minh**: yêu cầu đồng thời cả `AFN_ENVIRONMENT=dev|test`
và `AFN_PREDICTOR_MODE=mock`. Chế độ này parse các phần text/file của multipart và
trả về nội dung tổng hợp giả lập cố định với `model_id=dev-mock-not-a-model` và
`model_version=mock-v0.1.1`; nó không thực hiện suy luận ML hay xác thực nội dung ảnh/token.
Xem [dev-mock.md](dev-mock.md) để biết các giới hạn chi tiết và các fixture có phiên bản.
OpenAPI mô tả các phản hồi có điều kiện 200/400/413 cho mock và 503 cho thực/chưa sẵn sàng.
Body multipart chỉ bắt buộc ở chế độ mock. Không hỗ trợ body tải lên dạng JSON.
Trình parse mock thủ công ánh xạ các lỗi đầu vào dự kiến thành mã 400 đã được làm sạch, không qua lỗi validation 422 mặc định của FastAPI.
`python-multipart` chỉ được ghim phục vụ riêng cho cầu nối phát triển này.

Ngay cả khi một Predictor được tiêm vào, endpoint `/predict` ở **chế độ thực (real-mode)** vẫn chưa thể hoạt động
cho đến khi đường ống vận chuyển (transport pipeline) được hiện thực hóa. Do đó, việc thiếu/sai token,
form sai định dạng hoặc tải lên vượt dung lượng đều nhận về mã 503 với `request_id: null` ở chế độ thực.
Bảng lỗi mục tiêu dưới đây không phải là tuyên bố về khả năng thực thi hiện tại. Ứng dụng không đọc dữ liệu
tải lên ở chế độ thực; điều này không thay thế cho các giới hạn byte cấp luồng/server trong tương lai.

## Health

Không yêu cầu token cho endpoint health. Mã HTTP 200 có nghĩa là dịch vụ phản hồi, **không** đồng nghĩa
với việc hệ thống suy luận đã sẵn sàng. Các trường đề xuất (`HealthResponse`):

```json
{"service_status":"ok","model_ready":false,"contract_version":"0.1.1"}
```

Không trả về đường dẫn artifact, token, bài báo, nội dung ngoại lệ hay chi tiết hệ thống máy chủ.
Các trường JSON không thay đổi so với v0.1.0. `model_ready` phản ánh trạng thái của adapter DI:
chỉ nhận giá trị true khi ở trạng thái `ready` với một provider đã cài đặt. Trong chế độ mock, điều này có nghĩa là
**chỉ mock sẵn sàng**. Các header phản hồi mới trên health/predict/errors gồm:
`X-AFN-Inference-Mode: real|mock`, `X-AFN-Model-State: not_loaded|ready|error` và
`Cache-Control: no-store`. Chế độ thực mặc định vẫn là `not_loaded` bất kể đường dẫn artifact
có tồn tại hay không; chưa có loader thật nào được triển khai. Gán trực tiếp vào điểm nối
`app.state.predictor` cũ không chứng minh được tính sẵn sàng. Việc nạp mô hình thực tế,
tính tương thích và warm-up thuộc về #37/#38. Không có trường JSON mới nào được thêm vào health.
Schema và chính sách trạng thái khi health không khả dụng trong tương lai cần Extension/ML review.

## Mục tiêu POST /predict

Tệp **`analyze.js`** của Extension gửi request; `service-worker.js` không thực hiện việc này.
Sử dụng `multipart/form-data` với boundary tự sinh và header bắt buộc `X-Demo-Token`.
Không gửi body dạng JSON hoặc URL hình ảnh thay cho các byte được tải lên.

| Phần (Part) | Bắt buộc | Quy ước (Contract) |
| --- | --- | --- |
| `request_id` | Có | Chuỗi UUID do client tạo ra; được phản hồi lại sau khi parse an toàn |
| `title` | Không | Tối đa 500 điểm mã Unicode (code points); bỏ qua nghĩa là null, cho phép chuỗi rỗng |
| `text` | Có | Bài báo tiếng Anh; không rỗng sau khi trim; tối đa 50.000 điểm mã Unicode **trước** khi trim |
| `image` | Có | Một tệp JPEG/PNG được tải lên; tối đa 10 MiB (10.485.760 bytes); tối đa 20 MP (20.000.000 pixel giải mã) |

Các số lượng ký tự này tương ứng với chuỗi Python, không phải số byte UTF-8 hay đơn vị mã UTF-16 của JavaScript
(ở phía client có thể dùng `Array.from(value).length`).
Mức trần vận chuyển 50.000 ký tự độc lập với mức trần tiền xử lý ML đề xuất là **1.500 từ**.
Backend không thực hiện cắt từ, nhận diện ngôn ngữ, nối title/body hay chọn ngưỡng ML.
ML định nghĩa quy trình tiền xử lý và thiết lập `text_truncated`. Title và body đã trim đi qua ranh giới riêng biệt.

Đề xuất giới hạn toàn bộ body **có thể cấu hình**: **12 MiB (12.582.912 bytes)** thông qua
`AFN_MAX_REQUEST_BYTES`, đang chờ Backend/Extension thống nhất. Mức này vượt quá giới hạn
hình ảnh và cho phép lên tới 200.000 byte UTF-8 cho 50.000 code points, title, boundary
và chi phí overhead multipart thông thường. Tất cả các byte trong body đều được tính; một boundary/header/part bổ sung
quá lớn vẫn có thể vượt quá giới hạn. Giới hạn HTTP header là vấn đề riêng của server.
#22 phải thực thi việc kiểm tra số byte thực tế truyền qua luồng, không tin tưởng vào `Content-Length`;
không được tái sử dụng mức 10 MiB làm giới hạn cho toàn bộ request.
Cấu hình này đã có nhưng hiện chưa được kích hoạt thực thi.

Khai báo MIME và phần mở rộng tên tệp **không xác minh được nội dung hình ảnh**.
#23 chịu trách nhiệm xác thực định dạng/giải mã thực tế, kích thước, hướng EXIF và
chuẩn hóa RGB. Các loại media type mục tiêu được cho phép là `image/jpeg` và `image/png`.
Tệp không hợp lệ/bị thiếu và pixel sau giải mã sai quy chuẩn sẽ trả về 400; vượt quá kích thước byte trả về 413.

## Kết quả mục tiêu

HTTP 200 (`PredictResponse`), chỉ mang tính minh họa:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "label": "real",
  "fake_score": 0.42,
  "model_version": "illustrative-v1",
  "model_id": "illustrative-multimodal",
  "processing_time_ms": 250,
  "text_truncated": false
}
```

`label` chính xác là `fake` hoặc `real`. `fake_score` là một số hữu hạn trong [0,1]
và **không phải là xác suất đã hiệu chuẩn (calibrated probability)**. Không suy diễn ngưỡng cố định 0.5 cho mọi trường hợp.
ML quyết định ngưỡng và việc ánh xạ nhãn. `model_version` và `model_id` là
các chuỗi không rỗng do metadata của mô hình đã nạp cung cấp, không bao giờ do Backend
tự tạo ra ở chế độ thực. Các ID mock tường minh chỉ dùng để nhận diện nội dung giả lập.
`processing_time_ms` là số nguyên >=0, do Backend đo bằng đồng hồ đơn điệu (monotonic clock)
xung quanh lời gọi Predictor, bao gồm cả tiền xử lý của nó nhưng loại trừ việc nạp mô hình,
tải lên HTTP và truyền dữ liệu phản hồi. `text_truncated` là giá trị boolean từ tiền xử lý ML.
Các ID và con số ở trên chỉ là dữ liệu mẫu giữ chỗ.

## Lỗi và tương quan đối chiếu (Errors and Correlation)

Cấu trúc lỗi mục tiêu (`ErrorResponse`), chỉ mang tính minh họa:

```json
{"detail":"Invalid input","error_code":"invalid_input","request_id":null}
```

| HTTP | error_code | Nguyên nhân mục tiêu |
| --- | --- | --- |
| 400 | `invalid_input` | Thiếu/sai định dạng UUID, thiếu/trống/quá dài text, title >500, thiếu/hỏng ảnh, vi phạm MIME/pixel giải mã, multipart sai định dạng |
| 401 | `invalid_token` | Thiếu hoặc sai `X-Demo-Token` |
| 403 | `forbidden` | Chỉ khi chính sách phân biệt đã xác thực nhưng bị cấm; hiện chưa có chính sách này |
| 413 | `request_too_large` | Vượt quá mức trần dung lượng byte của ảnh hoặc toàn bộ request |
| 503 | `model_not_ready` | Thiếu, không khả dụng hoặc không tương thích mô hình/artifacts; route hiện đang bị vô hiệu hóa |

Chỉ phản hồi lại UUID đã được parse an toàn từ form, ngay cả khi trường khác gặp lỗi. UUID
được tuần tự hóa theo chuẩn chuẩn tắc (canonical). Sử dụng null khi ID bị thiếu, sai định dạng, chưa parse
hoặc không rõ ràng (ví dụ: trùng lặp các phần request_id); **tuyệt đối không tự tạo ID**
để thay thế cho một trường hợp parse thất bại. Các lỗi xác thực sớm/vượt giới hạn byte có thể trả về
null ngay cả khi body chưa đọc có chứa UUID hợp lệ. Mã 503 trong chế độ thực trả về null
vì nó không đọc body. Lỗi từ mock provider sau khi parse sẽ phản hồi lại UUID.
Client giữ lại ID tự sinh tại máy cục bộ để đối chiếu tương quan (correlation)
và bỏ qua các phản hồi thuộc về thao tác lựa chọn/request cũ đã hết hạn.

Trước khi bind form/tệp, #22/#23 phải bắt các lỗi `RequestValidationError` và lỗi parser
thuộc phạm vi hợp đồng và ánh xạ chúng thành `ErrorResponse` 400 đã được làm sạch,
thay vì trả về 422 mặc định. Chỉ bắt các lỗi đầu vào dự kiến; không chuyển đổi các lỗi lập trình
thành `invalid_input`. Chỉ khôi phục UUID từ metadata của form đã được parse rõ ràng, không nhập nhằng.
Không phản hồi lại nội dung đầu vào lỗi của Pydantic, thông điệp ngoại lệ của parser, stack trace,
đường dẫn, token, toàn bộ nội dung bài báo hay các byte hình ảnh.
Gỡ bỏ các phản hồi 422 tự động sinh trong OpenAPI khi ánh xạ đó được triển khai
và bổ sung các bài kiểm thử cấp endpoint khi đó. Cầu nối mock chỉ bắt các lỗi đầu vào
và lỗi parser dự kiến cho mã 400; lỗi adapter/provider sẽ chuyển thành 503 kèm trạng thái error.
Thứ tự ưu tiên xác thực/lỗi và cách xử lý các phần form trùng lặp/chưa biết đang chờ #22
và review; mã 503 ở chế độ thực được ưu tiên cao hơn mọi validation. Bản mock từ chối
các phần trùng lặp/chưa biết để đảm bảo tính tất định khi phát triển; điều này chưa chốt chính sách
cho API thật. Việc kiểm tra token được chủ động lược bỏ trong chế độ mock opt-in.

## Minh họa yêu cầu từ client (chế độ thực trả về 503; mock opt-in là dữ liệu giả lập)

POSIX shell; `AFN_DEMO_TOKEN` được cung cấp cục bộ, không phải là secret mẫu ghi cứng:

```sh
curl --request POST http://127.0.0.1:8000/predict \
  --header "X-Demo-Token: ${AFN_DEMO_TOKEN}" \
  --form-string 'request_id=550e8400-e29b-41d4-a716-446655440000' \
  --form-string 'title=Tiêu đề bài viết minh họa' \
  --form-string 'text=Nội dung bài viết tiếng Anh minh họa.' \
  --form 'image=@./example.png;type=image/png'
```

JavaScript cho việc tích hợp `analyze.js` trong tương lai; phía gọi cung cấp đối tượng `File`
đã chọn, token cấu hình cục bộ và thời gian chờ (timeout) có thể cấu hình:

```javascript
async function analyze({ title, text, imageFile, demoToken, timeoutMs }) {
  const requestId = crypto.randomUUID();
  const form = new FormData();
  form.append("request_id", requestId);
  if (title != null) form.append("title", title);
  form.append("text", text);
  form.append("image", imageFile);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch("http://127.0.0.1:8000/predict", {
      method: "POST",
      headers: { "X-Demo-Token": demoToken },
      body: form, // Trình duyệt tự thiết lập Content-Type và multipart boundary.
      signal: controller.signal
    });
    const payload = await response.json();
    return { requestId, ok: response.ok, status: response.status, payload };
  } finally {
    clearTimeout(timer);
  }
}
```

Lựa chọn `timeoutMs` thông qua cấu hình client, đang chờ Extension review.
Mục tiêu hiệu năng suy luận ~10 giây sau khi nạp mô hình **không phải là thời gian timeout bắt buộc**.
Việc abort, timeout hoặc lựa chọn cũ của client không đảm bảo việc hủy bỏ tiến trình ở phía server.
Cần bảo toàn dữ liệu nhập của người dùng; không thử lại mù quáng hoặc hiển thị các kết quả cũ.
Các cuộc gọi cross-origin hiện tại của Extension chưa cam kết hoạt động cho đến khi có #38.

## Bảo mật và phân định quyền sở hữu

Ràng buộc (bind) vào loopback. #22 chịu trách nhiệm xác thực token đầy đủ và thực thi giới hạn kích thước request;
#23 chịu trách nhiệm xác thực hình ảnh thực tế. #38 chịu trách nhiệm giới hạn origin CORS, warm-up
và gia cố bảo mật cục bộ. CORS không phải là cơ chế xác thực. Không hỗ trợ triển khai dịch vụ công khai ra ngoài.
Không đặt token trong URL, log, mã nguồn, ví dụ hoặc file cấu hình được commit. File `.env` ví dụ
không chứa secret. Ghi log truy cập của server bị vô hiệu hóa trong các lệnh được ghi nhận trong tài liệu.

Xung đột ngôn ngữ: `DEFINE.md` §3 ghi tiếng Việt (và sau đó hoãn tiếng Việt lại);
kế hoạch issue được cung cấp nêu rõ ràng là tiếng Anh. Bản thảo này tuân theo phạm vi đầu vào tiếng Anh
của kế hoạch, đang chờ ML/Extension xác nhận; các tài liệu thiết kế hiện có được giữ nguyên.
`DESIGN.md` hiện chỉ có §1–4, vì vậy các phần tham chiếu §8–14 không thể kiểm tra được tại máy cục bộ.

Khi thay đổi phiên bản, phải cập nhật đồng bộ các tài liệu này, schema, giao diện suy luận và các fixture liên quan.
Backend phải thông báo cho ML/Extension về các thay đổi phá vỡ tương thích liên quan đến trường dữ liệu/ngữ nghĩa
trước khi áp dụng. Xem báo cáo thực thi để biết trạng thái review thực tế.
