# Báo cáo bàn giao — bridge DEMO R_REV/M4 (kết quả #5 → hồ sơ nghiệm thu → file soát)

Ngày: 18/10/2026 (cập nhật sau review độc lập lần 1). Claude Code sửa chính, Codex kiểm độc lập. Theo `GIAO-VIEC-BRIDGE-REVIEW-XAY-DUNG-33.md`.
**Cập nhật Codex 19/10/2026: 5 nhóm lỗi đã qua review/probe độc lập lần 2 trong phạm vi DEMO; chưa phải toàn M4 hoàn thành hoặc nghiệm thu vận hành thật.** Production (`giao_tiep.v1_ghi_ket_qua_review`, vai trò `app_review`, TL40) chưa có và chưa được gọi. GUI nhận/xác nhận/duyệt/xuất đã kiểm sau sửa; xác nhận tệp tải qua browser sau sửa chưa kiểm chứng do công cụ browser bị ngắt.

## Luồng (cùng ứng dụng, cùng Store mô phỏng, cùng token/mutation lock)
JSON đúng shape `kiem_tra_dot` #5 → `Store.ingest` (raw bất biến/hash/staging/evidence) → hồ sơ `NGHIEM_THU` → xác nhận mapping (mã danh mục đúng hiệu lực ngày NT) + số kế toán → validator server → đề xuất bút toán nghiệm thu (không phát sinh thu/chi tiền) → Đồng ý → file soát xlsx. Mức 2 Junsky khóa; actor server cố định `MO_PHONG_KE_TOAN`; chỉ môi trường fixture.

## Sửa sau review lần 1
| Nhóm | Sửa |
|---|---|
| P1 sự kiện/bản thay | `de_xuat/nghiem_thu.py::_chan_su_kien` tính **động trong giao dịch** ở xác nhận/Đồng ý/xuất: bản khác đã xuất → chặn mọi bản khác (cần quy trình điều chỉnh, chưa có → chặn rõ `BAN_KHAC_DA_XUAT`/`NT_SU_KIEN_DA_XUAT`); bản khác Đã đồng ý → chặn; có bản mới hơn chưa Bỏ qua → bản cũ không Đồng ý/xuất (`BAN_MOI_HON`). `xuat` gọi lại toàn bộ validator nghiệp vụ, so bút toán đã duyệt với bút toán dựng lại, trước khi tạo file/đổi trạng thái (`NT_XUAT_CHAN`, `NT_BUT_TOAN_DOI`). Bỏ cờ chụp lúc đồng bộ. |
| P1 `da_nap` | `nguon/review_xay_dung.py::kiem_da_nap`: object; `luc` đọc được (có offset hoặc local → +07:00); `dot` khớp đợt; `so_hang_muc`/`khong_khop` int ≥ 0, `nap_lai` bool, `ghi_chu` chuỗi khi có. Hỏng/thiếu → hồ sơ + raw vẫn giữ, trạng thái `BANG_CHUNG_NAP_KHONG_HOP_LE`, chặn với lý do. |
| P1 NULL ≠ 0 | Giữ lại đợt và thu hồi tạm ứng phải xác nhận tường minh (0 hợp lệ); bỏ `or 0`; builder không dựng bút toán khi NULL. |
| P1 số chính xác | JSON đọc bằng `Decimal` (không qua float), vẫn chặn khóa lặp/NaN; số có phần lẻ → NULL, giữ chuỗi chính xác; staging/core serialize không mất nghĩa; hash nội dung phân biệt 1000000000000.00001 và 1000000000000.0. FixtureAdapter/bank parser không đổi. |
| P2 tiền lớn | API trả tiền dạng chuỗi; JS định dạng bằng chuỗi (không `Number`); XLSX ghi số ≥ 10^15 dạng chữ (cell `s`), số thường vẫn là số; formula safety giữ (`excel.table`). |
| UI | Nhãn `for` gắn mọi ô trong form xác nhận; tên hiển thị "Hỗ trợ kế toán" (title/brand/footer DEMO shell); bỏ "giao_tiep"/"PYTHON · SQLITE" khỏi giao diện; file soát ghi "Nghiệm thu — không phát sinh thu/chi tiền". |

## File đổi trong gói
`src/kho_tri_thuc/nguon/review_xay_dung.py`, `src/kho_tri_thuc/de_xuat/nghiem_thu.py`, `src/kho_tri_thuc/giao_dien/server.py`, `src/kho_tri_thuc/giao_dien/quick.py` (chặn run NGHIEM_THU), `src/kho_tri_thuc/giao_dien/assets/index.html`, `assets/app.js`, `src/kho_tri_thuc/kiem_chung/fixtures.py`, `tests/test_nghiem_thu_bridge.py`.

## Kiểm thử Claude tự chạy (chế độ giữ file do root bật; không dọn output)
| File | Kết quả |
|---|---|
| test_nghiem_thu_bridge.py | 21/21 pass (2 interleaving + ca đua lúc xuất, 5 ca `da_nap` hỏng + 3 dạng thời điểm hợp lệ, NULL/0, decimal/hash, int64 API + XLSX, HTTP token/actor/mức 2) |
| test_v9b.py | 19 pass |
| test_v11.py + test_v12.py | 34 pass |
| test_web.py | 22 pass, **1 fail do guard**: `test_scope_changes_receipt_not_raw_storage_size` đếm thư mục raw = 1 nhưng file tạm của `write_immutable` không được xóa (guard chặn unlink) → 5 |
| test_m1.py | 42 pass, **1 fail do guard**: `test_backup_does_not_succeed_without_referenced_raw` cố ý `raw.unlink()` để tạo thiếu raw; guard chặn xóa nên không có lỗi kỳ vọng |

Hai fail trên không thuộc file của gói (intake/store/backup không đổi) và là giới hạn của chế độ cấm xóa; **không tắt guard hoặc dọn file để làm xanh**. Codex chạy regression liên quan 167 test: 165 pass, 2 fail đúng hai ca này, 0 error/skip. Agent độc lập bổ sung 2 probe tương đương: một canonical artifact/4 receipt/unique bytes/restart/download/retry đúng; kho clone giữ hash đủ 50 bảng nhưng raw chưa từng tồn tại → backup từ chối, không publish, staging giữ lại; positive backup vẫn verified. Hai probe đạt không đổi kết quả suite gốc thành 167/167.

## Review độc lập sau sửa

- 27/27 probe đúng contract, 0 fail/error/skip; cả hai interleaving xuất trùng và 5 `da_nap` hỏng bị chặn; NULL khác 0; Decimal/hash chính xác; XML XLSX giữ nguyên `100000000000000001` dạng text, formula-safe, không ghi vế tiền. Evidence private `rrev-independent-review-b4293771b715.json` và thư mục run tương ứng.
- Root tự chạy `test_nghiem_thu_bridge.py`: 21 pass, 0 fail/error/skip trên Windows host với guard. Lần trong sandbox bị chặn hardlink os.link là lỗi môi trường setup, không dùng làm kết quả nghiệp vụ.
- Adapter SHA256 `a2c0577609e6b73f06931f20a9873c9212b9b96c1f545cee990d0dd7813debe4`; façade `301db1cabdfc0f83c1b940cf3f2049589fedf3aea2cbed3969ab514c06277128`.
- Regression evidence: `rrev-regression-retained-20261018-2240/summary.json`; probe tương đương `retained-equivalent-2bb4e4d9de4645e488f251a62916724e/summary.json` (SHA256 `4a536be4f9a88cdc29df0b51f360fc060599e9a079ed2a40f38f7817d8b331f3`). Mọi file/test DB được giữ.

## GUI
Root đã chạy lại trên kho DEMO riêng với guard: nhận danh mục/review, toàn bộ nhãn form dùng được, giữ nguyên số `100000000000000001` qua lưu/duyệt/hiển thị, giữ lại trống chặn Đồng ý, nhập 0 cho phép; xuất đúng 1 file soát. Ảnh `rrev-ui-after-repairs.png` đã xem trực quan. Nút Tải đã bấm nhưng chưa xác nhận được file lưu sau sửa; browser tool bị ngắt dù đã đặt timeout, không quy thành lỗi nghiệp vụ hay ghi bước tải đạt. Cách bấm: `MỞ BẢN DEMO.cmd` → **Hồ sơ nghiệm thu** → Nạp danh mục DEMO → Nhận review mẫu → Mở → điền mapping/số (giữ lại & thu hồi nhập rõ, kể cả 0), tích "số trước VAT" → Lưu xác nhận → Đồng ý → Xuất file soát → Tải.

## Giới hạn thật
Chưa có quy trình bút toán điều chỉnh sau xuất (đang chặn); mapping chưa là danh mục master có phiên bản; chính sách 241/154/VAT/tài khoản giữ lại thật do CFO chốt; production #5 → `giao_tiep` chưa làm; lỗi B1 đơn giá cố định thuộc engine #5. Converter/A5 (stt, FK tenant, hash 19 bảng) giữ riêng, không sửa lượt này.
