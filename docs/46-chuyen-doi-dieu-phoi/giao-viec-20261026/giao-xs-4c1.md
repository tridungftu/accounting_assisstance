# XS-4c1 · Dịch vụ công tắc module + hàm chặn dùng chung (CD-017, QD-20261026-11)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép.** Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), dữ liệu giả, chạy được dưới guard giữ tệp. Không kiểm CRLF/LF trên tệp nguồn (repo `core.autocrlf=true`).

**Căn cứ:**
- SQL đã có: **M0056** `k2/sql_module.py`. Hàm: `master.module_trang_thai(module, pn)` (cờ `che_do`, `hien_luoi`, `cho_xem`, `cho_ghi`, `cho_xuat_ngoai`, `cong_bo_chinh_thuc`, `dai_dang_thu`), `master.module_doi_che_do(...)`, cấp/thu hồi/xem người thử (chỉ Admin).
- Quyết định S1–S6: `docs\46-chuyen-doi-dieu-phoi\XS-4-CAN-CHOT.md`; QD-20261026-11.
- Mẫu dịch vụ: `k2/ma_tran_tham_quyen.py` (`MaTranThamQuyenK2`); mẫu HTTP: `giao_dien/ma_tran_tham_quyen.py` (lát sau XS-4c2 làm HTTP, không phải lát này).

**Tệp (2):** `k2/module.py` mới; `tests/test_xs4_dich_vu.py` mới. **Không sửa** `server.py`, `sql_module.py`, `pg_migrations.py`.

**Việc:**
1. **Lớp dịch vụ** `CongTacModuleK2` theo mẫu `MaTranThamQuyenK2`: dùng kết nối/danh tính phiên do bên gọi đưa vào; không tự mở kết nối, không nhận danh tính/PN từ body client. Phương thức:
   - `trang_thai(dang_nhap, module, phap_nhan_id)` → dict cờ (gọi `module_trang_thai`);
   - `doi_che_do(dang_nhap, payload)` (module, PN, chế độ, lý do, revision cũ);
   - `cap_nguoi_thu` / `thu_hoi_nguoi_thu` / `danh_sach_nguoi_thu` — gọi đúng hàm SQL M0056; chỉ Admin do SQL kiểm.
2. **Hàm chặn dùng chung** `kiem_module(conn, module, phap_nhan_id, *, can)` với `can` ∈ `{"xem", "ghi", "xuat_ngoai", "cong_bo"}`:
   - đọc cờ, không đạt → `DataError` có mã và câu tiếng Việt nghiệp vụ, không mã kỹ thuật trong câu. Ví dụ:
     - `MODULE_TAT`: "Chức năng này đang tạm tắt ở pháp nhân này.";
     - `MODULE_CHI_NGUOI_THU`: "Chức năng đang chạy thử, chỉ người được chọn thử dùng được.";
     - `MODULE_THU_KHONG_XUAT`: "Đang chạy thử nên chưa được xuất ra ngoài.";
   - `PN` phải do máy chủ xác định từ đối tượng nghiệp vụ hoặc phiên (ghi rõ docstring). Hàm không tự suy PN.
   - Đây là hàm mà các module sẽ gọi trước khi ghi / xuất ra ngoài / đẩy kết quả chính thức sang module khác (S1, S4).
3. **Chờ (S4):** hàm `trang_thai_cho(conn, module_nguon, phap_nhan_id)` → `None` nếu module nguồn đang cho xem dữ liệu công bố; ngược lại trả `{"ma": "CHO_MODULE", "ly_do": "Chờ <tên nghiệp vụ module>"}`. Tên lấy từ khai báo module XS-4a (`ha_tang/khai_bao_module.py`) nếu có; không có thì dùng tên trung tính. Module khác dùng để hiện "Chờ …" thay vì báo lỗi (pilot XS-T1 dùng sau).
4. Không log danh sách người thử. Không thêm thư viện.

**Test (PG):**
- ba chế độ × (Admin / người thử / người khác) qua `kiem_module` với từng `can` → đúng cho/chặn + mã + câu không chứa mã kỹ thuật;
- `trang_thai_cho` khi module nguồn TẮT/THỬ/VẬN HÀNH;
- `doi_che_do` không Admin → bị chặn; Admin đổi được, CAS sai revision bị chặn;
- PN B không bị ảnh hưởng khi đổi ở A.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[XS-4c1] …`.
