# M2b — sửa vòng 2 (chỉ 2 điểm review vòng 1)

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8, không BOM. Worktree hiện tại, nhánh `lat/m2b` (commit `fffad5a` là bản của bạn ở vòng 1). Sandbox không ghi được `.git`: **không commit** — lead commit.

Review vòng 1 kết luận Đạt; lead quyết sửa đúng 2 điểm sau theo thiết kế đã chốt (`D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M2-00-NHAN-NGUON-TU-CONG-THUE.md` §6). **Không sửa gì khác.**

1. **`src/kho_tri_thuc/m2/tai_hoa_don/chinh_sach_tien_te.py` ~dòng 114–117:** điều kiện "MST bán và mua đều VN hợp lệ" CHỈ áp cho nhánh XML **không có** `DVTTe`. Khi XML có `DVTTe` = VND → kết quả theo XML (`THEO_XML`, VND, không cờ policy) dù một bên không có MST (ví dụ bán cho cá nhân) — nhưng vẫn giữ: `TGia` có mặt và ≠ 1 → "chưa rõ"; bảng kê ghi tiền tệ khác VND → "xung đột". Sửa test tương ứng (`tests/test_m2_00_tien_te_tinh.py` ~dòng 88) và thêm ca: `{"DVTTe": "VND", "mst_ban": <hợp lệ>, "mst_mua": None}` → THEO_XML.
2. **`src/kho_tri_thuc/m2/tai_hoa_don/manifest.py` ~dòng 210–214:** hóa đơn có `key_thieu` khác rỗng KHÔNG được làm từ chối cả manifest. Làm như `tools/source7_m2_patch/src/manifest.js` (~dòng 627): kiểm `key_thieu` khớp đúng danh sách phần khóa thực sự thiếu (lệch → lỗi như hiện nay), manifest vẫn hợp lệ; trả các hóa đơn đó trong một danh sách ngoại lệ riêng của kết quả đọc (ví dụ `hoa_don_thieu_khoa` với `key_raw` + phần thiếu) để lát M2c đưa vào danh sách việc — không vào đề xuất. Thêm test: manifest có 1 hóa đơn thiếu `shdon` → đọc được, hóa đơn đó nằm trong danh sách ngoại lệ, các hóa đơn khác bình thường; `key_thieu` khai sai → vẫn từ chối.

**Test phải đạt:** `python -X utf8 tools/chay_test_theo_module.py . --module test_m2_00_manifest_tinh --module test_m2_00_tien_te_tinh --module test_m2_00b_tien_trinh` — đạt hết.
**Báo cáo cuối (≤ ½ trang):** 2 điểm đã sửa (file:dòng) · test đạt/tổng · thông điệp commit đề xuất `[M2b] vòng 2: …`.
