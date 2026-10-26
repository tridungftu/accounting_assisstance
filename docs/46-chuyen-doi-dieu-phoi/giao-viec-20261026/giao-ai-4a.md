# AI-4a — Cổng AI: kiểm xác suất + đo độ chính xác Local theo loại việc (TL 48 §1.5 (c), §1.6) — Cloud vẫn TẮT mặc định

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại** (chưa rõ → chọn cách an toàn, ghi "Cần Anh"). Đọc `AGENTS.md`, `CLAUDE.md` §2 "Cổng AI". UTF-8 không BOM. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip). **Không gọi mạng thật** (Local AI, Mask, Cloud đều giả lập trong test). Không đọc `.env`. Không xóa file.

Worktree hiện tại, nhánh `lat/ai-4a` (hợp nhất, đã có AI-2a/2b/3). Căn cứ: TL 48 `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` **§1.5** (Cloud khi (a) Local không chạy, (b) Local không chắc, (c) **kiểm xác suất**), **§1.6** (đo độ chính xác Local theo loại việc; > 90% thì giảm dần tỷ lệ kiểm), §1.7; cổng `src/kho_tri_thuc/tri_thuc/cong_ai.py` (móc `kiem_xac_suat` hiện mặc định 0%), nhật ký `BoGhiPostgres` → `nhat_ky.cong_ai_goi` (M0034).

**Việc:**
1. `kiem_xac_suat`: tỷ lệ kiểm theo **loại việc** đọc từ cấu hình + thống kê; lượt được chọn kiểm → chạy cả Local và Cloud (qua Mask như mọi đường Cloud), so kết quả theo trường, ghi **đúng/sai của Local** vào nhật ký (không ghi văn bản). Công tắc Cloud **tắt** → không kiểm, không gọi Mask/Cloud (giữ nguyên hành vi hiện tại).
2. **Đo độ chính xác Local theo loại việc** từ nhật ký (cửa sổ N lượt kiểm gần nhất, mặc định cấu hình); quy tắc giảm tỷ lệ kiểm khi chính xác > 90% (bậc thang, có sàn tối thiểu, có tăng lại khi rơi dưới ngưỡng) — tham số một chỗ, giá trị mặc định ghi "Cần Anh".
3. Hàm/endpoint chỉ đọc trả bảng thống kê theo loại việc (số lượt, số kiểm, % chính xác, tỷ lệ kiểm hiện hành) — chưa làm màn hình.
4. Test (`tests/test_cong_ai.py` hoặc mới `tests/test_ai4a_kiem_xac_suat.py`): Cloud tắt → 0 kiểm; tỷ lệ 100% → luôn kiểm, ghi đúng/sai; giảm tỷ lệ khi > 90% qua N lượt, tăng lại khi tụt; không ghi văn bản; nhà cung cấp/Mask giả.
**Không làm:** bật Cloud mặc định, bí danh đối tác = mã Junsky (lát sau), màn hình.
**File (≤ 4, gồm test):** `tri_thuc/cong_ai.py`, (bảng thống kê nếu cần: migration nối cuối — tránh nếu tính được từ `nhat_ky.cong_ai_goi`), 1 test. **Báo cáo (≤ ⅓ trang)**, thông điệp commit `[AI-4a] …`.
