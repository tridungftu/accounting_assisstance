# L0-8e — Host engine #6 / tiến trình tính không khởi động dưới bộ chạy test (GUARD_KHONG_NAP)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2, §5). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/l0-8e` (từ `lat/l0-8d` = hop-nhat + họ bản sao 03a). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL/server DEMO. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`; sandbox chặn python → ghi "lead chạy test".

**Hiện tượng (lead đo 25/10):**
- `--pg-demo --module test_m4_03a_pg --module test_m4_03b_common_pg`: bản sao họ `03a` dựng được, nhưng `setUpClass` skip: "NOT_READY: host #6 không khởi động (GUARD_KHONG_NAP) — K2 dương không chạy". Vì vậy 31 ca PostgreSQL M4-03A/03B (gồm c11–c18 kiểm SQL M0033 đã gộp) **chưa chạy được**.
- Nền v4 (không PG) có sẵn 4 lỗi `test_trich6_host` (`HandlerSoHuuTests.test_cong_chan_truoc_handler_goc`, `VongDoiThatTests.test_06a_docx_that_all37_tap_con_seal_replay_va_tu_choi`, `…test_hai_instance_doc_lap_va_buoc_dung_central`, `…test_vong_doi_auth_common_only_va_dung`) — nghi cùng gốc.
- Mã lỗi: `src/kho_tri_thuc/k2/xay_dung.py:841-870` và `:1333-1360` (`MA_GUARD_KHONG_NAP` từ `m4/review_compute.py`): "chế độ giữ tệp bật nhưng hook giữ tệp thật không cài trong tiến trình tính". Bộ chạy test nạp bảo vệ `.pth` theo đường dẫn tuyệt đối (L0-8c, `tools/chay_test_theo_module.py` ~:680-700) cho tiến trình con; tiến trình tính/host #6 là **cháu** (có thể chạy `python -I`/môi trường sạch) nên có thể không nạp hook.

**Việc:**
1. Chẩn đoán đúng gốc: ai bật "chế độ giữ tệp", hook thật nằm ở đâu, vì sao không cài trong tiến trình tính/host #6 khi chạy dưới bộ chạy (so với khi máy chủ DEMO chạy thật). Tái hiện bằng `--module test_trich6_host` (thuần, không PG).
2. Sửa **để hook được cài đúng** trong tiến trình tính/host khi chạy dưới bộ chạy test (ưu tiên sửa ở bộ chạy hoặc cách truyền cấu hình hook cho tiến trình cháu). **Tuyệt đối không nới bảo vệ**: không tắt chế độ giữ tệp, không bỏ kiểm `MA_GUARD_KHONG_NAP`, không cho tiến trình tính chạy khi thiếu hook. Nếu gốc nằm ở mã sản phẩm và cần đổi hành vi bảo vệ → dừng, báo lead (không sửa).
3. Test: ca thuần chứng minh hook được cài ở tiến trình cháu dưới bộ chạy; ca âm: thiếu hook vẫn dừng `GUARD_KHONG_NAP`.

**File được sửa (≤ 3):** ưu tiên `tools/chay_test_theo_module.py`, `tests/test_chay_test_pg_demo.py`, và 1 tệp hỗ trợ nếu cần (ghi lý do). Không xóa file.
**Báo cáo cuối (≤ ½ trang):** gốc lỗi (tệp:dòng) · cách sửa · bằng chứng bảo vệ không bị nới · `test_trich6_host` trước/sau · thông điệp commit `[L0-8e] …`.
