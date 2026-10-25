# REVIEW DA-1 vòng 2/2 (CRM · Dự án đang bán — máy chủ + M0031) · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho phần sửa do Codex viết. **Chỉ đọc**: không sửa tệp, không commit, không nối CSDL. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-da-1`, nhánh `lat/da-1`. Vòng 2 = hai commit `f31e012` (sửa 3 điểm review vòng 1) và `9e0378c` (thuế theo QD-20261025-20): `git -C <worktree> diff b9adfe7 9e0378c`. Toàn lát: `git -C <worktree> diff hop-nhat-20261023...lat/da-1`. Lead đã chạy: test thuần 35/35, **PostgreSQL thật 15/15** trên CSDL DEMO mới (schema 31), nhóm CRM 0 mã lỗi mới.

**Review vòng 1 (Codex):** (1) **Chặn** — nhánh `OR … CRM_DU_AN_BAN` cho người XEM có phân công được ghi; (2) cập nhật G7 không có CAS → hai người cùng sửa từ bản cũ, người sau đè không báo; (3) `_chi_query` chỉ kiểm tên khóa: `?dang_ban=1&dang_ban=` → 200, `phien_ban` 1.000 số 0 qua kiểm độ dài.
**Quyết định Anh:** QD-20261025-07 (ghi chỉ BAN_HANG/KE_TOAN/KE_TOAN_TRUONG có CRM, hiệu lực ngay, nhật ký); QD-20261025-20 (giá luôn chưa gồm VAT; thuế suất danh mục 10/8/5/0/KCT/KKKNT mặc định 10; `gia_dat_tru` ≥ 0, ≤ đơn giá, không tính VAT).

**Kiểm, Đạt/Không:**
1. Ba điểm vòng 1 hết thật (đọc đường thực thi SQL + Python, không tin chú thích): không còn đường nào để vai khác ghi; CAS G7 kiểm **sau** khi khóa bộ chuẩn và trả 409; query thô chặn lặp/rỗng/quá dài cho mọi route DA.
2. Thuế: CHECK SQL và kiểm Python cùng miền (danh mục, `gia_dat_tru` so với đơn giá cùng tiền tệ, chữ số ASCII, không float); trường cũ `co_so_thue`/`vat_phan_tram` bị từ chối; ảnh chụp có `thue{thue_suat, nhan, gia_chua_gom_vat}` và `gia_dat_tru`; `anh_chup_sha256` không phụ thuộc ngày gọi.
3. M0031 vẫn chỉ APPEND (M0001–M0030 trùng byte hop-nhat) và không đổi nghĩa bộ chuẩn G7 cũ.
4. Test mới (XEM có phân công bị từ chối, hai người cùng sửa G7 → 409, query biên, thuế) có nghĩa.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW DA-1 · vòng 2/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Vòng cuối: chỉ "Chặn" khi còn đường ghi trái quyền, tiền/thuế sai, hoặc M0031 phá migration cũ.
