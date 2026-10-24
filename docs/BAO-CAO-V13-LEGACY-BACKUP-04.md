# BÁO CÁO V13 — legacy backup, 04 (residual biên nhận va chạm khi công bố)

Ngày 19/10/2026. Thực hiện `docs/GIAO-SUA-V13-LEGACY-BACKUP-04.md` (SHA `9f31050f…685b` theo lệnh root) theo `REVIEW-V13-BACKUP-CLI-03.md` (F1/P2) và `REVIEW-V13-BACKUP-TESTS-03.md` (P2 oracle con_lai). Báo cáo 01/02/03, reviews, core, PG test giữ nguyên. **Không tự nghiệm thu V13/33.** M9: không làm gì.

## 0. Kết quả tự kiểm

| Lệnh đã cấp | Kết quả |
|---|---|
| `python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py` | **18 test, 18 PASS**, 0 fail/error/skip (ResourceWarning do kết nối test giữ mở). 15 control cũ + 3 control mới. |

Không chạy PG/CLI độc lập/suite khác (đúng phạm vi vòng 04). Kết quả là Windows (Python hệ thống của phiên), unit trên thư mục tạm DEMO.

## 1. File thay đổi (3/3 được phép)

| File | Thay đổi |
|---|---|
| `tools/sao_luu_pg.py` | `_cong_bo`: bắt `FileExistsError` từ chính `os.rename` → `DESTINATION_EXISTS`, `final_ben_khac=True`, `da_cong_bo=False`; OSError khác giữ nguyên lỗi gốc, ghi trạng thái công bố `UNKNOWN`. Biên nhận thêm `trang_thai_cong_bo` (`CHUA_CONG_BO`/`VA_CHAM_BEN_KHAC`/`DA_CONG_BO`/`UNKNOWN`); khi `UNKNOWN`, final vào `khong_xac_dinh` và `kiem_ke=UNKNOWN`. |
| `tests/test_v13_backup_safety.py` | 3 unit mới trong `BienNhanCliTests`. |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-04.md` | Báo cáo này. |

Diff `_cong_bo` (logic): precheck `final.exists()` giữ nguyên → `try: os.rename(staging, final)`; `except FileExistsError` → đặt `final_ben_khac=True`, `trang_thai_cong_bo="VA_CHAM_BEN_KHAC"`, raise `DataError("DESTINATION_EXISTS")` (`from None`, không mang message gốc); `except OSError` → `trang_thai_cong_bo="UNKNOWN"`, `raise` (giữ loại lỗi gốc, `loi_sach` làm sạch ở biên CLI); chỉ sau rename thành công mới `da_cong_bo=True`, `"DA_CONG_BO"`. Không retry, không replace/ghi đè, không xóa/di chuyển staging, rival hay bản cũ. Bảo toàn lỗi gốc khi kiểm kê lỗi và logic UNKNOWN inventory của vòng 03 giữ nguyên; JSON lỗi CLI thêm trường `trang_thai_cong_bo`. Tương thích PG test frozen (không sửa): ca `loi_cong_bo` stub toàn `_cong_bo` → trạng thái vẫn `CHUA_CONG_BO`, `kiem_ke=DAY_DU`; ca bên khác tạo final trước precheck → `DESTINATION_EXISTS`/`final_ben_khac=True` như cũ.

## 2. Controls mới (operation thật vs. tiêm lỗi)

1. **`test_va_cham_muon_tai_rename_that` — operation thật.** Staging DEMO tạo độc quyền với DB và SHA không rỗng (bytes/hash biết trước). Bọc điểm gọi `os.rename` chỉ để phối hợp fixture: trong wrapper, xác nhận đích còn vắng (precheck của `_cong_bo` đã qua), tạo bundle bên khác (bytes khác), rồi gọi **`os.rename` thật** của Windows; ghi nhận nó ném `FileExistsError` (assert `goi == ["FileExistsError"]` chứng minh rename thật đã chạy và chính nó từ chối). Kết quả đòi: `DESTINATION_EXISTS`, `da_cong_bo=False`, `final_ben_khac=True`, `trang_thai_cong_bo=VA_CHAM_BEN_KHAC`; biên nhận `con_lai` **chính xác** `[partial/, partial/ban.sqlite, partial/ban.sqlite.sha256]` (không rỗng, không chứa tài sản bên khác — đóng P2 oracle của review tests 03 ở mức unit), `kiem_ke=DAY_DU`; hash DB+SHA staging và bytes bundle bên khác nguyên; `loi_sach` trả `ma=DESTINATION_EXISTS`.
2. **`test_loi_rename_khong_phai_va_cham_giu_loi_goc_unknown` — tiêm lỗi.** Thay rename bằng hàm ném `PermissionError` (không gọi rename thật). Đòi: lỗi gốc `PermissionError` (không thành `DESTINATION_EXISTS`), `da_cong_bo=False`, `final_ben_khac=False` (không khẳng định bên khác), `trang_thai_cong_bo=UNKNOWN`; biên nhận `kiem_ke=UNKNOWN`, `khong_xac_dinh=["ban/"]`, `con_lai` chính xác staging DB+SHA; `loi_sach` chỉ có kiểu lỗi, không message; DB nguyên, final không tạo.
3. **`test_cong_bo_that_khong_va_cham_db_sha` — operation thật, control dương.** Rename thật không va chạm: `da_cong_bo=True`, `DA_CONG_BO`, staging biến mất (đã đổi tên), DB+SHA đúng bytes trong final.

Giữ nguyên: va chạm thấy ngay ở precheck (`test_final_ben_khac_khong_nhan_so_huu`), công bố của chính mình (`test_cong_bo_cua_minh_moi_bao_da_cong_bo`), lỗi metadata UNKNOWN + lỗi kiểm kê không thay lỗi gốc, và các control 15 cũ.

## 3. Giới hạn

- Phân loại va chạm dựa trên Windows `os.rename` ném `FileExistsError` khi đích (thư mục) tồn tại — đã quan sát thật trong unit trên máy này; không cam kết portable (POSIX rename thư mục vào thư mục rỗng có thể thay thế) hay bền khi crash.
- PG test N08 (ngoài phạm vi sửa) vẫn chỉ tạo final trước precheck; ca va chạm muộn chỉ được kiểm ở unit. Không chạy PG, CLI tiến trình con, ordinary role, full V13/K2.

## 4. Tuân thủ

Chỉ sửa 3 file cho phép; không sửa core/PG test/báo cáo cũ/guard/runner/policy/probes/launcher. Không đọc var/.env/source app/secret, không dump env/rows/traceback. Không xóa/cleanup/di chuyển file/DB/role/attempt/backup/partial. Không PG/HTTP/host/Google/cloud/kho thật/duyệt thật/CFO_NTD/Git. Chỉ chạy một lệnh unit đã cấp.
