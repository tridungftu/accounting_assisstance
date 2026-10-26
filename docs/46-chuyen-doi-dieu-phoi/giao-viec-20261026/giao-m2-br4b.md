# M2-BR4b: bộ đọc XML, đối chiếu tổng tiền với chi tiết trước khi cho EXACT; nhiều quan hệ → HOLD (nên sửa bắt buộc của review M2-BR4)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- **Chỉ dữ liệu giả DEMO.**
- Làm trong worktree hiện tại, nhánh `lat/m2-br4b`, dựng từ hợp nhất (đã gộp M2-BR4).

**Việc trong `src/kho_tri_thuc/nguon/hoa_don_xml.py`** (phần `money`/`relations` do BR4 thêm). **Không** đổi hợp đồng đầu ra cũ và **không** đổi bước quét strict V1.
1. **Đối chiếu tổng với chi tiết.** Chỉ đối chiếu, **không thay số** (thiết kế M3 §6: không tính lại). Lệch → `state = HOLD`, lý do `MONEY_TOTAL_CONFLICT`, kèm tên phép đối chiếu.
   - Σ `ThTien` các dòng thuế suất = `TgTCThue`;
   - Σ `TThue` = `TgTThue`;
   - `TgTCThue + TgTThue` = `TgTTTBSo`.

   Khi thiếu số để đối chiếu, giữ trạng thái hiện có (ABSENT/HOLD theo quy tắc BR4), không kết luận khớp.
2. **Nhiều thẻ `TTHDLQuan`** trong một hóa đơn → HOLD (`RELATION_MULTIPLE`).
3. Docstring ghi rõ:
   - `net_amount` = `TgTCThue` gồm cả phần không chịu thuế; lát nối sang M3 **không được** gán thẳng vào "net chịu thuế".
   - Hóa đơn có `TTHDLQuan`/`TToan` vẫn nằm ngoài envelope V1; lát đưa hóa đơn bán ra vào K2 phải chốt envelope V2.

**Test `tests/test_hoa_don_xml.py`:**
- Sửa ca `test_am_ngoai_te_va_decimal_khong_mat_chinh_xac` (đang ghim việc tổng lệch vẫn ra EXACT).
- Thêm ca:
  - mỗi phép đối chiếu lệch → HOLD đúng lý do;
  - khớp → EXACT;
  - 2 `TTHDLQuan` → HOLD;
  - hợp đồng đầu ra cũ không đổi.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_hoa_don_xml` cùng các test M2 dùng reader (PYTHONPATH=`src;.;tests`). Báo số trước/sau.

**Tệp (2):** `nguon/hoa_don_xml.py`, `tests/test_hoa_don_xml.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M2-BR4b] …`.
