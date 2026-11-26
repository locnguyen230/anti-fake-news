# Checklist bàn giao Backend · AFN-054

Bản đóng gói nguồn theo API v0.2.0 và `afn-model-bundle-v1`.
Owner Integration `fulord26`. Reviewer Backend `Phuc1232`.
[Hướng dẫn cài đặt](../docs/backend-setup.md)

## Gói cài và môi trường

- [ ] Ghi commit Backend, phiên bản gói ZIP, vị trí kho bàn giao và SHA-256.
- [ ] Kiểm danh sách ZIP. Chỉ có code phục vụ, pins, `.env.example`,
  schema, cấu hình CLIP và tài liệu. Kiểm `.env.example` để
  bảo đảm token trống. Bàn giao cache và bundle qua kho riêng.
- [ ] Từ ZIP mới giải nén, dựng venv, cài hai lockfile, chạy `pip check`.
  Ghi OS, CPU, Python và nguồn wheelhouse.
- [ ] Kiểm bundle Multimodal thật có `status: frozen`, `is_fixture: false`;
  ghi model ID/version và checksum metadata từ AFN-049. Kiểm SHA-256
  weights CLIP theo revision ghi trong hướng dẫn.
- [ ] Khởi động `python -m app` trên loopback bằng cấu hình production và
  kiểm HTTP 200 `model_ready: true`, mode real, state ready.
- [ ] Chạy script smoke từ checkout mã nguồn cùng commit, trong một process
  mới khi offline và giữ loopback. Ghi
  health, 401 thiếu token, 200 predict và UUID cùng model ID/version
  khớp cấu hình. Dùng đầu vào smoke tổng hợp.
- [ ] Thiếu bundle khi chạy production phải khiến Backend dừng khởi động.
- [ ] Backend review bằng chứng máy đích và biên bản #53. Ghi cụ thể
  lỗi, giới hạn hoặc phiên bản còn chờ.

## Đầu vào nghiệm thu còn chờ

| Đầu vào | Owner | Phiên bản cần có |
| --- | --- | --- |
| #49 · Freeze | ML `0xDa1Vu`, QA `dangnguyen0512` | Bundle thật, SHA-256 metadata chốt và thông tin model đã ký |
| #53 · Regression bàn giao | BACKEND `Phuc1232` | Kết quả cuối cùng trên commit chứa fixes hoặc biên bản xác nhận không có lỗi chặn |
| Máy đích | BACKEND `Phuc1232`, Integration `fulord26` | Kết quả cài từ ZIP và restart offline trên môi trường bàn giao |

Hiệu năng AFN-052 được ghi riêng ở báo cáo nghiệm thu. Có thể tạo
ZIP nguồn trong lúc chờ những đầu vào trên.
[#49](https://github.com/ngnsusinn/anti-fake-news/issues/49) ·
[#52](https://github.com/ngnsusinn/anti-fake-news/issues/52) ·
[#53](https://github.com/ngnsusinn/anti-fake-news/issues/53)
