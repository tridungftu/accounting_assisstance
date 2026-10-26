# M9-2a vòng 3: tiêu đề Điều không là kết quả riêng; ngưỡng khớp chặt hơn

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi UTF-8 không BOM. **Không commit**. Không mạng, không AI, không thư viện ngoài.
- Làm trong worktree hiện tại, nhánh `lat/m9-2a`. Mã vòng 2 chưa commit. Giao việc gốc: `giao-m9-2a.md` và `giao-m9-2a-v2.md` (cùng thư mục `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\`).

**Lead chạy test (sandbox không chạy được Python): 24 ca, 2 hỏng.**
- `test_cau_hoi_tu_nhien_co_va_khong_dau`, câu hỏi "cho hỏi lãi suất là bao nhiêu" (có dấu và không dấu): kết quả đầu có `khoan = None`, mong `'1'`.
- Nguyên nhân: tiêu đề Điều ("Lãi suất") thành một câu tìm kiếm riêng; câu ngắn nên BM25 xếp cao hơn câu nội dung.

**Lead thử thêm:** "lãi suất quá hạn là bao nhiêu" trả về khoản lãi suất **trong hạn** (khớp 2/4 từ nội dung, đúng ngưỡng 50%). Bên soạn câu trả lời (M9-2b) có thể đưa ra "8,5%" cho câu hỏi lãi quá hạn: **sai bằng số**.

**Việc** (`m9/chi_muc_vay.py`):
1. Câu chỉ là tiêu đề Điều/Chương (trùng phần tiêu đề sau nhãn) **không** là đơn vị kết quả.
   - Từ của tiêu đề dùng làm **ngữ cảnh** cho mọi câu trong Điều đó, trọng số nhỏ hơn từ của chính câu.
   - Câu trả về vẫn là câu nội dung nguyên văn.
2. Ngưỡng khớp: số từ nội dung của câu hỏi khớp phải **lớn hơn một nửa** (không phải ≥). Tính trên câu cộng ngữ cảnh tiêu đề.
3. Từ phân biệt nghĩa đi theo cặp **không** được coi là hư từ (quá hạn, trước hạn, trong hạn, cố định, thả nổi, ân hạn); "hạn" và "quá" phải giữ.

**Test** (thêm/sửa trong `tests/test_m9_chi_muc_vay.py`):
- 2 ca hỏng phải đạt; kết quả đầu là câu nội dung có `khoan`.
- "lãi suất quá hạn là bao nhiêu" khi hợp đồng **không có** câu về lãi quá hạn → `[]`. Khi **có** câu "Lãi suất quá hạn bằng 150% lãi suất trong hạn." → trúng câu đó, không phải câu lãi trong hạn.
- Không có kết quả nào là câu chỉ gồm tiêu đề.
- Ca vòng 1 và vòng 2 vẫn đạt.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_chi_muc_vay tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests`. Nếu sandbox chặn Python thì ghi rõ.

**Tệp (2):** `m9/chi_muc_vay.py`, `tests/test_m9_chi_muc_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-2a] …`.
