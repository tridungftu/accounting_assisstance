# M9-2a vòng 4: một ca hỏng — hư từ không dấu nuốt mất từ phân biệt nghĩa

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Ghi UTF-8 không BOM. **Không commit**. Không mạng/AI/thư viện ngoài. Worktree hiện tại, nhánh `lat/m9-2a` (mã vòng 3 chưa commit; giao việc trước: `giao-m9-2a-v3.md`).

**Lead chạy test: 1 hỏng** — `test_giu_ca_hai_tu_phan_biet_nghia (cum='cố định', hoi='co dinh')`: chỉ mục chỉ còn câu "định." mà vẫn trả kết quả. Nguyên nhân khả dĩ: câu hỏi **không dấu** "co" bị coi là hư từ "có", nên từ nội dung chỉ còn "dinh" → khớp 1/1. Với câu hỏi có dấu "cố định" thì đúng (`[]`).

**Việc** (`m9/chi_muc_vay.py`): với từ **không dấu** trong câu hỏi, chỉ bỏ như hư từ khi dạng không dấu đó **không trùng** dạng bỏ dấu của một từ trong danh sách cặp phân biệt nghĩa/từ nghiệp vụ cần giữ (cố định, quá hạn, trước hạn, trong hạn, thả nổi, ân hạn, …) **khi từ kế bên trong câu hỏi tạo thành cặp đó** (ví dụ "co dinh" → giữ "co"). Không làm hỏng các ca hư từ đã đạt ("cho hoi lai suat la bao nhieu").

**Test:** ca hỏng phải đạt; toàn bộ `tests.test_m9_chi_muc_vay` và `tests.test_m9_tai_lieu_vay` đạt. **Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_chi_muc_vay tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests` (nếu sandbox chặn Python thì ghi rõ). **Tệp (≤2):** `m9/chi_muc_vay.py`, `tests/test_m9_chi_muc_vay.py`. **Báo cáo (≤ 5 dòng)**, thông điệp `[M9-2a] …`.
