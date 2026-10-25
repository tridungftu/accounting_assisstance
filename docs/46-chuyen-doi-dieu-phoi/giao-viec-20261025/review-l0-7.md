# REVIEW L0-7 · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Python hệ thống không dùng được trong sandbox; nếu cần chạy thử dùng `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"` (có thể thiếu openpyxl — khi đó chỉ đọc mã).

**Đối tượng:** nhánh `lat/l0-7` (worktree hiện tại), 3 commit trên `1d1c12f`: `2072eed` (trich6_host nạp sẵn numpy/openpyxl/docx ở luồng chính), `f222a79` (`.gitattributes` cho `src/kho_tri_thuc/m4/review_goc/`), `e041224` (`tools/chuan_bi_crm_demo.py` seed duyệt viên M4). Diff: `git diff 1d1c12f..lat/l0-7`.
**Bối cảnh:** engine trích #6 (tiến trình con `python -m kho_tri_thuc.nguon.trich6_host --child`) treo ở lệnh trích đầu vì `openpyxl` tự import `numpy` lần đầu trong luồng worker khi tiến trình con đang `serve_forever` → kẹt. Sửa: nạp sẵn ở luồng chính trước khi phục vụ. Worker báo đối chứng A/B: có sửa 3 lần trích 1,8 s; gỡ dòng nạp sẵn → treo/503.

**Kiểm 4 việc, Đạt/Không:**
1. **Đúng & an toàn của (a):** `nap_san_thu_vien()` gọi ở luồng chính, SAU guard (A517) và TRƯỚC `serve_forever`; mô-đun thiếu/lỗi chỉ ghi log và đi tiếp (không làm chết tiến trình con, không nuốt lỗi khác); không đổi giao thức/hành vi; log không in dữ liệu. Có tác dụng phụ nào với kho thật (`MỞ PHẦN MỀM.cmd`) — ví dụ nạp `docx` khi không cài?
2. **(d) `.gitattributes`:** quy tắc `review_goc/** text eol=lf`, 2 file `eol=crlf`, `*.woff2 -text` — có làm đổi byte của file KHÔNG bị ghim theo cách gây hại (vd file nhị phân khác trong `review_goc` bị coi là text)? Liệt kê đuôi file trong `review_goc` và kiểm mỗi loại có đúng thuộc tính.
3. **(e) seed duyệt viên:** chỉ chạy ở DEMO (không bao giờ ở kho thật), kiểm DSN loopback + tiền tố CSDL DEMO trước khi kết nối, idempotent, lỗi không chặn mở DEMO, không in bí mật.
4. **Phạm vi/ràng buộc:** 5 file (`trich6_host.py`, `.gitattributes`, `chuan_bi_crm_demo.py`, `tests/test_trich6_host.py`, `tests/test_crm_khoi_dong.py`); không dữ liệu thật; không xóa file.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW L0-7 · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi có thể làm hỏng/treo phần mềm thật, chạy seed ngoài DEMO, lộ bí mật, hoặc vi phạm ràng buộc cứng.
