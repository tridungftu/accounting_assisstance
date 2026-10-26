# MTQ-4a3b: Ma trận thẩm quyền, nối Python 9 điểm CRM/M1 còn lại vào adapter (sau MTQ-4a3a, M0045). Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì **chặn** và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*`; không đọc `KHO_PG_DEMO_*`.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a3b`, dựng từ hợp nhất. Đã có:
  - **M0045**: cổng `master.mtq_quyet_dinh_phien` giải được `master.phap_nhan`, `kho.chung_tu` (hồ sơ CRM), `master.hop_dong` cho `M1:TIEN:SUA` / `CRM:FILE_SOAT:XEM`, `kho.lien_ket_chung_tu`, `kho.lo_xuat` (CRM);
  - adapter `k2/quyen.py:kiem_tham_quyen`;
  - các điểm đã nối ở MTQ-4a/4a2 (`git log --oneline -- src/kho_tri_thuc/k2/crm.py`).
- Không sửa SQL, migration hay `server.py`. Không bật ma trận.

**Căn cứ:**
- Bảng ánh xạ trong `giao-viec-20261026/giao-mtq-4a3a.md`.
- Báo cáo `bao-cao-mtq-4a2.md` (9 điểm bỏ) và `bao-cao-mtq-4a3a.md`.
- Thiết kế `THIET-KE-MA-TRAN-THAM-QUYEN.md` §5.1.

**Việc** (`k2/crm.py`, theo đúng mẫu `cap_nhat_mapping` / `_kiem_mtq_duyet`):

| Điểm | Khóa catalog | Đối tượng (dựng từ dòng thật đã đọc qua RLS, **không** từ body) | Lệnh cũ cho `kiem_cu` |
|---|---|---|---|
| `trich_tu_docx`, `nhan_ket_qua_6` | `CRM:TIEP_NHAN:LAP` | `{"bang":"master.phap_nhan","id":pn}` | `NOP_HOP_DONG` |
| `bo_sung_ho_so` | `CRM:TIEP_NHAN:SUA` | `{"bang":"kho.chung_tu","id":ct_id}` | `BO_SUNG_HO_SO` |
| `_trich_lai` | `CRM:TIEP_NHAN:KIEM` | `kho.chung_tu` | `DOI_CHIEU_TRICH_LAI` |
| `kiem_nhan_tien` | `M1:TIEN:LAP` | `master.phap_nhan` | `NHAN_TIEN` |
| `lien_ket` | `M1:TIEN:SUA` | `{"bang":"master.hop_dong","id":lich0["hop_dong_id"]}` | `LIEN_KET_TIEN` |
| `go_lien_ket` | `M1:TIEN:HUY` | `{"bang":"kho.lien_ket_chung_tu","id":lk_id}` | `LIEN_KET_TIEN` |
| `xuat_file_soat` | `CRM:FILE_SOAT:XEM` | `master.hop_dong` | `XUAT_FILE_SOAT` |
| `tep_file_soat` | `CRM:FILE_SOAT:XEM` | `{"bang":"kho.lo_xuat","id":lo_id}` | `XUAT_FILE_SOAT` |

1. **Nhánh CU** gọi đúng `quyen.kiem(...)` cũ, cùng tham số, kết quả **không đổi một bit** (cùng lỗi, cùng mã, cùng thứ tự kiểm so với side effect).
2. Cổng SQL đòi **giao dịch có GUC danh tính**.
   - `trich_tu_docx` và `kiem_nhan_tien` hiện kiểm ngoài giao dịch: bọc riêng lời gọi `kiem_tham_quyen` trong `with self._tx(dt):` (chỉ phần kiểm).
   - Giữ "kiểm **trước** mọi side effect / gọi engine".
   - **Không** đưa lời gọi engine #6 vào giao dịch.
3. Cả 8 khóa là `PHI_TIEN`: không truyền `so_tien_vnd`.
4. `khong_thay` đúng thông báo "không thấy … (hoặc ngoài quyền)" hiện có của từng điểm.
5. **Nên sửa trong `k2/quyen.py`** (review MTQ-4a/4a2):
   - Trong `hoi()` và bộ lấy tiền, nhánh `except Exception` ghi log máy chủ `exc_info=True` (logger module, như `crm.py:83`), không trả chi tiết cho client.
   - Đổi câu hiện cho người dùng có "Cần Anh …" thành câu trung tính, ví dụ "Không xác định được thẩm quyền; thao tác bị chặn. Báo quản trị." và "Chưa có tổng giá trị hợp đồng VND từ phiên bản đã khóa; chưa thể duyệt.". Giữ nguyên mã lỗi.
6. Nếu một route của các điểm trên chưa ghi nhật ký từ chối như `_crm_action` (bắt `TuChoiThamQuyen` → rollback → `ghi_tu_choi_tham_quyen` ở giao dịch riêng), **không** sửa `server.py`. Liệt kê route đó trong báo cáo, mục "Cần lead".

**Test** (`tests/test_mtq_crm.py`, thêm ca):
- **Hồi quy CU cho từng điểm mới:** so với oracle `quyen.kiem` thật, nhiều vai (có quyền / không quyền / sai PN). Mã lỗi và thứ tự so với side effect không đổi.
  - Riêng `trich_tu_docx`: không quyền thì engine **không** được gọi.
- **PG, PN bật MTQ:**
  - người có ô/phạm vi đúng thì qua;
  - không có thì `TuChoiThamQuyen` với mã cổng;
  - không fallback;
  - `kho.lo_xuat` của module khác bị chặn.
- **Câu người dùng:** không chứa "Cần Anh".
- **Log:** nhánh `except` có ghi log (dùng `assertLogs`).
- Số test CRM trước/sau (`tests/test_crm*.py`) không giảm, không mã lỗi mới.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_crm` và các test CRM liên quan, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `k2/crm.py`, `k2/quyen.py`, `tests/test_mtq_crm.py`.

**Báo cáo (≤ ⅓ trang):** điểm đã nối, route chưa ghi nhật ký từ chối, số test, thông điệp commit `[MTQ-4a3b] …`.
