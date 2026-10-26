# T-NODE: chẩn đoán 7 bộ test node đỏ sẵn trên hợp nhất (lấp chỗ trống theo CD-009). Chỉ chẩn đoán, sửa test khi lỗi thuần ở test.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- **Không sửa mã sản phẩm** (`src/`).
- Làm trong worktree hiện tại, nhánh `lat/t-node`, dựng từ hợp nhất.

**7 bộ đang đỏ, cả trên hợp nhất lẫn dòng giao diện:**
- `tests/crm_doi_chieu_async.cjs`
- `tests/m2_00a_source7_fix02.cjs`
- `tests/m2_00b_source7_rpc.cjs`
- `tests/m4_02c_dto_ui_async.cjs`
- `tests/m4_03a_async.cjs`
- `tests/m4_03a_gui_fix02_async.cjs`
- `tests/m4_04b_request_async.cjs`

**Việc:**
1. Chạy từng bộ: `node tests/<tệp>`, có giới hạn thời gian. Ghi **nguyên nhân gốc** của từng bộ, chọn một trong các loại:
   - (a) thiếu fixture hay tệp bị `.gitignore`;
   - (b) hash ghim lệch do kiểu xuống dòng CRLF/LF khi checkout;
   - (c) test cũ không theo kịp thay đổi giao diện đã duyệt;
   - (d) lỗi sản phẩm thật;
   - (e) môi trường (thiếu module node, đường dẫn…).

   Ghi kèm dòng lỗi đầu tiên và tệp:dòng.
2. Chỉ sửa **trong `tests/`** khi nguyên nhân là (b) hoặc (c) và cách sửa không nới kiểm:
   - (b): chuẩn hóa xuống dòng trước khi băm. Không đổi giá trị ghim nếu đã đúng trên LF.
   - (c): cập nhật kỳ vọng theo hành vi đã duyệt, nêu commit hay tài liệu căn cứ.

   Không tự đổi kỳ vọng nghiệp vụ khi chưa rõ căn cứ.
3. Loại (a), (d), (e): **không sửa**. Ghi vào báo cáo kèm đề xuất lát sửa (tệp, cách sửa).

**Chạy lại:** toàn bộ `tests/*.cjs`. Báo số bộ đạt trước và sau.

**Tệp:** chỉ các bộ test trong danh sách trên, tối đa 4 tệp.

**Báo cáo (≤ ⅓ trang):** bảng 7 bộ × nguyên nhân × đã sửa/đề xuất; thông điệp commit `[T-NODE] …`.
