# M2-BR4: M2 · Hóa đơn, bộ đọc XML nhận thành phần tiền và quan hệ hóa đơn (phục vụ hóa đơn bán ra cho M3; `M2-BAN-RA-KIEM-KE.md` §4 dòng BR4)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì HOLD/PENDING và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Không gọi cổng thuế. **Chỉ dữ liệu giả có chữ DEMO.**
- Làm trong worktree hiện tại, nhánh `lat/m2-br4`, dựng từ hợp nhất.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M2-BAN-RA-KIEM-KE.md`: §1–§3, đặc biệt các dòng `XML:42,69` (allowlist strict reader), `XML:59–62,955,963`, phần tiền `SQL:5271–5282`, phần quan hệ `TTHDLQuan`/`NH:88–114`.
- Thiết kế M3 v2 §6, §9 (hóa đơn: net chịu thuế / phần không chịu thuế / VAT / tổng; quan hệ điều chỉnh/thay thế).

**Việc: chỉ trong `src/kho_tri_thuc/nguon/hoa_don_xml.py`**, giữ nguyên hợp đồng đầu ra cũ (mọi trường và giá trị đang có không đổi):
1. Thêm phần đọc **thành phần tiền** ở mức hóa đơn theo đúng thẻ XML hóa đơn điện tử: tổng tiền chưa thuế, tiền thuế theo từng thuế suất, phần không chịu thuế, tổng thanh toán, đơn vị tiền.
   - Giá trị **chính xác** (`Decimal` từ chuỗi), không float.
   - Thẻ thiếu hoặc mơ hồ (nhiều giá trị mâu thuẫn, định dạng lạ) → trạng thái `HOLD` kèm lý do. **Không** tự suy, **không** NULL thành 0.
2. Đọc **quan hệ hóa đơn liên quan** (`TTHDLQuan`): loại (thay thế/điều chỉnh), ký hiệu, số, ngày của hóa đơn gốc.
   - Thêm thẻ vào allowlist của strict reader **chỉ** cho các thẻ cần thiết.
   - Thiếu trường → HOLD.
3. Không phân biệt hay đổi chiều mua/bán ở lát này. Chỉ đọc; không đụng SQL, HTTP, UI.

**Test:**
- `tests/test_hoa_don_xml.py` hoặc bộ test của reader có sẵn.
- Fixture mới `tests/fixtures/m2_ban_ra.xml`, giả, có chữ DEMO, có:
  - nhiều thuế suất;
  - phần không chịu thuế (ví dụ giá đất được trừ);
  - một hóa đơn điều chỉnh tham chiếu hóa đơn gốc.
- Kiểm:
  - tiền đúng Decimal;
  - thẻ thiếu → HOLD;
  - hai giá trị mâu thuẫn → HOLD;
  - quan hệ đọc đúng;
  - **hợp đồng đầu ra cũ không đổi** trên các fixture mua vào có sẵn (so trước và sau).

**Chạy thuần:** test reader và các test M2 dùng reader (`python -X utf8 -m unittest tests.test_hoa_don_xml` và các module `tests/test_m2*` liên quan; PYTHONPATH=`src;.;tests`). Báo số trước/sau.

**Tệp (3):** `nguon/hoa_don_xml.py`, 1 test, 1 fixture.

**Báo cáo (≤ ¼ trang):** thẻ đã thêm, số test, phần "Cần Anh", thông điệp commit `[M2-BR4] …`.
