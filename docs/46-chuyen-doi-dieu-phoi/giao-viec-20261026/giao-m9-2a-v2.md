# M9-2a vòng 2: chỉ mục từ khóa, sửa lỗi bỏ sót với câu hỏi tự nhiên

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi UTF-8 không BOM. **Không commit**. Không mạng, không AI, không thư viện ngoài.
- Làm trong worktree hiện tại, nhánh `lat/m9-2a`. Mã vòng 1 chưa commit: `src/kho_tri_thuc/m9/chi_muc_vay.py`, `tests/test_m9_chi_muc_vay.py`. Giao việc gốc: `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\giao-m9-2a.md`.

**Lead thử (kết quả thật):** chỉ mục có câu "Phí trả nợ trước hạn là 1% trên số tiền trả trước." (khoản 7.2).
- Hỏi "Hỏi: phí trả nợ trước hạn bao nhiêu phần trăm vậy?" → `[]`. **Sai: bỏ sót.**
- Nguyên nhân 1: điều kiện "khớp ít nhất nửa số từ của câu hỏi" (dòng ~88) tính cả hư từ của câu hỏi ("hỏi", "bao", "nhiêu", "phần", "trăm", "vậy").
- Nguyên nhân 2: "vậy" bỏ dấu thành "vay", trùng nghĩa với "vay" (khoản vay).
- "ngân hàng có được đơn phương tăng lãi không" → `[]` là **đúng**, vì không có câu nào nói về việc này. Phải giữ.

**Việc** (`m9/chi_muc_vay.py`):
1. Danh sách hư từ tiếng Việt cho **câu hỏi**, so ở dạng **có dấu**, trước khi bỏ dấu, để "vậy" không thành "vay".
   - Gồm ít nhất: hỏi, cho hỏi, là, gì, nào, bao nhiêu, bao lâu, mấy, có, không, được, chưa, vậy, thì, của, theo, như thế nào, thế nào, khi nào, ở đâu, ai, tôi, mình, ạ, nhé, à, hả, phần trăm (ghi chú: "%" trong câu vẫn là token số).
   - Không bỏ từ nghiệp vụ: lãi, suất, phí, trả, nợ, hạn, vay, gốc, kỳ, điều chỉnh, bảo đảm, tài sản, biên độ.
2. Điều kiện nhận:
   - tính tỷ lệ khớp trên **từ nội dung** của câu hỏi (sau khi bỏ hư từ);
   - giữ ngưỡng điểm BM25;
   - câu hỏi chỉ toàn hư từ → `[]`.
3. Chỉ mục (phía văn bản hợp đồng) **giữ nguyên**, không bỏ từ, để câu trích không đổi.

**Test** (thêm vào `tests/test_m9_chi_muc_vay.py`):
- Ít nhất 6 câu hỏi tự nhiên có/không dấu, trúng đúng khoản. Ví dụ: "phí trả nợ trước hạn bao nhiêu phần trăm vậy?", "cho hỏi lãi suất là bao nhiêu", "bao lâu thì điều chỉnh lãi một lần", "tai san bao dam la gi".
- Ít nhất 3 câu hỏi về chủ đề không có → `[]`. Ví dụ: "ngân hàng có được đơn phương tăng lãi không", "phạt chậm nộp báo cáo tài chính".
- "vậy" không khớp "vay".
- Các ca vòng 1 vẫn đạt.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_chi_muc_vay tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests`. Nếu sandbox chặn Python thì ghi rõ.

**Tệp (2):** `m9/chi_muc_vay.py`, `tests/test_m9_chi_muc_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-2a] …`.
