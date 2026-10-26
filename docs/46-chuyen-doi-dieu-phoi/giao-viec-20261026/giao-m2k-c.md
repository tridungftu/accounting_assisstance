# M2k-c: test M2k, ca "DTO sai" dùng đúng mã lỗi thật (nên sửa của review M2k-b)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m2k-c`, dựng từ hợp nhất (đã gộp M2k-b).

**Việc:**
- Trong `tests/test_m2k_khoi_dong_lai.py` (khoảng dòng 153–229), ca lỗi "DTO sai" đang dùng mã `DTO_SAI`, không có thật, nên ca này vẫn đạt trên mã cũ và không bảo vệ gì.
- Đổi sang mã thật **`KHACH_DTO_SAI`**. Xem mã lỗi khách trong `src/kho_tri_thuc/m2/tai_hoa_don/` hoặc `giao_dien/m2_tai_hoa_don.py`.
- Kiểm: ca đó đạt trên mã hiện tại, và **thất bại** nếu tạm coi `KHACH_DTO_SAI` là "treo". Chỉ thử trên bản sao trong thư mục tạm, không sửa `src/`.
- Không đổi ca nào khác. Không sửa `src/`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m2k_khoi_dong_lai` (PYTHONPATH=`src;.;tests`).

**Tệp (1):** `tests/test_m2k_khoi_dong_lai.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M2k-c] …`.
