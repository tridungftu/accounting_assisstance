**BIÊN BẢN REVIEW CHÉO TRICH-3a — ĐẠT**

Nhánh `lat/g3-trich-3a`, HEAD `a1047e0`, commit triển khai `8fab3ad`; đối chiếu `hop-nhat-20261023...HEAD`.

Quy ước: `E/` = `src/kho_tri_thuc/engines/e_trich_xuat/`; `T` = `tests/test_g3_trich_3a.py`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Không phát hiện lỗi thuộc mức Chặn / Cần sửa / Gợi ý trong phạm vi diff. | — | — |

1. **Phạm vi — Đạt.** Diff chỉ thêm đúng 3 tệp whitelist: `E/engine.json`, `E/chay.py`, `T`. Không có Excel trong diff; kiểm danh sách tệp Git cũng không thấy tệp Excel được theo dõi. `git diff --check` sạch.

2. **ACK và drain — Đạt.** Giữ cùng luồng kết quả, tua về đầu khi retry; chỉ ánh xạ sau ACK nguồn (`E/chay.py:47`, `:67`). Drain chờ worker hoàn tất, báo `drain_chua_xong` và tiếp tục chờ, không tự thoát (`:128`, `:148`). Test kiểm cả ACK nguồn và ACK tham số, cùng bytes/luồng qua retry, không chạy lại backend và không nhận việc mới khi drain (`T:178`, `:319`, `:353`, `:356`).

3. **Manifest/readiness — Đạt trong phạm vi giả lập.** Chỉ khai capability DOCX → `tham_so.v1`, có test ánh xạ đủ 37 mã và kiểm schema (`E/engine.json:9`; `T:138`, `:150`). Runtime báo `contracts=[]`; có ca từ chối khởi động khi Core đòi capability thật chưa đạt (`E/chay.py:143`; `T:250`, `:359`).

4. **Chuẩn và an toàn — Đạt.** Không thêm SQL, role, GRANT, DEFINER hoặc thay đổi RLS; kiểm login CSDL thật không áp dụng cho lát này. Không có lệnh xóa, ghi DSN/bí mật vào log/audit hoặc client gọi API AI trực tiếp. Test dùng DOCX DEMO/AI giả; có ca âm về loại hợp đồng, catalog/hash, PDF, Cloud, SDK sai, lease hết hạn và preflight (`T:212`, `:225`, `:236`).

5. **Dùng lại mã và chất lượng test — Đạt.** Dùng lại `docx.py`, `tham_so.py`, Bootstrap và SDKEngine; vòng đời bám mẫu `e_ocr/chay.py` (`E/chay.py:18`, `:42`). Các assertion kiểm hành vi bàn giao, giữ kết quả và readiness phù hợp tên test.

**Bằng chứng kiểm thử:** 11/11 theo thông tin lead cung cấp; lead đã chạy runtime. Reviewer chỉ đọc, không chạy lại test; không truy cập kho thật, tệp bí mật hoặc `*.local.json`.

**Kết luận: Đạt cho TRICH-3a giả lập; chưa xác nhận capability vận hành thật hoặc độ chính xác AI.**