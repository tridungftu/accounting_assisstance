Anh, kết quả Node: **14/21 → 16/21 bộ đạt**, không thêm lỗi. Chỉ sửa 2 tệp test, UTF-8 không BOM; không commit.

Đường dẫn dưới đây thuộc `tests/`; dòng lỗi tính trước sửa.

| Bộ test:dòng | Nguyên nhân / lỗi đầu | Đã sửa hoặc đề xuất |
|---|---|---|
| `crm_doi_chieu_async.cjs:173` | **(c)** `TypeError: Cannot read properties of null (reading 'click')` | Đã dùng “Làm mới” cho dòng “Đang mở”, theo `bd2824b`; đạt. |
| `m2_00a_source7_fix02.cjs:25` | **(e)** `Error: M2_00A_VIEW_ROOT phai la duong dan tuyet doi toi view da materialize (khong fallback).` | Giữ nguyên; lát M2-env cấp VIEW_ROOT/DEMO_OUT theo đầu tệp. |
| `m2_00b_source7_rpc.cjs:23` | **(e)** `Error: M2_00B_VIEW_ROOT phai la duong dan tuyet doi toi view da materialize (khong fallback).` | Giữ nguyên; lát M2-env cấp VIEW_ROOT/DEMO_OUT. |
| `m4_02c_dto_ui_async.cjs:32` | **(a)** `SETUP_FIXTURE: ENOENT: no such file or directory, open ''` | Giữ nguyên; runner lấy fixture từ `test_m4_02c_dto_ui.py`, truyền `argv[2]`. |
| `m4_03a_async.cjs:379` | **(c)** AssertionError: nhãn AP cũ; thêm lỗi mock `title` tại `:386` | Giữ bản gốc ghim; đề xuất runner dùng FIX02 đã sửa. |
| `m4_03a_gui_fix02_async.cjs:147` | **(b)** `SETUP FIX02_GOC_SAI_HASH`; sau đó lộ **(c)** nhãn AP cũ | Đã chuẩn hóa LF, giữ pin; cập nhật nhãn theo `6d4d4a6`; **48/48 ca đạt**. |
| `m4_04b_request_async.cjs:33` | **(a)** `SETUP_FIXTURE: ENOENT: no such file or directory, open ''` | Giữ nguyên; runner lấy fixture từ `test_m4_04b_request_wiring_http.py`, truyền `argv[2]`. |

Đã chạy toàn bộ với timeout tối đa 180 giây/bộ; `git diff --check` đạt. Integration producer vẫn **NOT_VERIFIED** do thiếu bundle.

Thông điệp commit đề xuất: `[T-NODE] Chẩn đoán 7 bộ Node đỏ, sửa thao tác CRM và harness FIX02`