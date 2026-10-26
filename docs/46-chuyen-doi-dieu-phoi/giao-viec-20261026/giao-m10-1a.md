# M10-1a: M10 · Định kỳ & đóng sổ, engine lịch phân bổ A/B chỉ để kiểm chéo với Junsky (CD-013; thiết kế M3 v2 §7.4, §16 #2 và #9)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m10-1a`, dựng từ hợp nhất.
- Căn cứ: `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` §7.3, §7.4, §10 (quy tắc 7 và 10), §16 #2 và #9.

**Nguyên tắc (không được vi phạm):**
- Lịch tính **chỉ để kiểm chéo**: không là nguồn bút toán, không chuyển sang Junsky, không bên nào tự thắng khi lệch.
- Phần mềm **không phân bổ thay Junsky** (Anh, #9).
- Phương pháp (A/B), cơ sở kỳ (tháng), xử lý tháng lẻ đầu/cuối và quy tắc làm tròn là **tham số policy** truyền vào. **Không chọn mặc định A/B** (chờ hiệu chuẩn K0); thiếu tham số thì báo lỗi rõ.
- Tiền dùng `Decimal`, **không float**, không dung sai tự đặt; mọi chênh khác 0 là lệch.

**Việc: gói mới `src/kho_tri_thuc/m10/` (`__init__.py` rỗng) và tệp `src/kho_tri_thuc/m10/lich_phan_bo.py`, thuần Python, không đọc/ghi CSDL hay tệp.**

Đầu vào (dataclass bất biến):
- Hợp đồng/phiên bản: mã, phiên bản, **ngày bàn giao mặt bằng** (= ngày bắt đầu phân bổ cho mọi đợt), ngày kết thúc thuê, ngày chấm dứt (tùy chọn), currency.
- Các đợt thu: mã đợt, giá trị trước VAT, ngày ghi 3387.
- Policy: phương pháp `A` hoặc `B`; đơn vị kỳ `THANG`; quy tắc tháng lẻ đầu/cuối (`TRON_THANG` hoặc `THEO_NGAY`, chọn qua tham số); quy tắc làm tròn (số chữ số, kiểu làm tròn `ROUND_HALF_UP`/`ROUND_HALF_EVEN`, dồn phần lẻ vào kỳ cuối có hay không).

Đầu ra: lịch theo kỳ (năm-tháng) cho từng đợt và tổng theo hợp đồng.
- Mỗi dòng: doanh thu phân bổ kỳ, lũy kế, số dư 3387 cuối kỳ.
- Kèm phiên bản hợp đồng và mã hash ổn định của đầu vào, để biết lịch tính từ tham số nào.

Hai cách tính:
- **Cách A:** chia theo tổng số kỳ từ ngày bàn giao đến kết thúc thuê. Đợt ghi sau ngày bàn giao được **catch-up** trong tháng ghi.
- **Cách B:** chia theo số kỳ còn lại tính từ ngày ghi 3387, không catch-up.
- Đợt ghi **trước** ngày bàn giao: phân bổ không bắt đầu trước ngày bàn giao.
- Chấm dứt sớm: lịch dừng tại kỳ chấm dứt và trả số dư 3387 còn lại. Không tự quyết hoàn trả hay giữ lại.

**Test, tệp mới `tests/test_m10_lich_phan_bo.py`:**
- Ví dụ §7.4, số giả: thuê 600, 60 tháng, bàn giao tháng 1; đợt 1 = 300 thu tháng 1, đợt 2 = 300 thu tháng 7.
  - **Cách A: doanh thu năm 1 = 120.**
  - **Cách B: đợt 2 = 300/54 mỗi tháng → doanh thu năm 1 ≈ 93,3.** Khẳng định bằng Decimal theo quy tắc làm tròn trong test.
- Tổng phân bổ toàn kỳ = tổng giá trị đợt; số dư cuối = 0 (khi không chấm dứt).
- Đợt trước bàn giao không phân bổ trước ngày bàn giao.
- Chấm dứt sớm: dừng lịch, số dư 3387 còn lại đúng.
- Thiếu phương pháp hoặc quy tắc làm tròn thì báo lỗi, không mặc định.
- Đầu vào float bị từ chối.
- Cùng đầu vào thì cùng hash; đổi một tham số thì hash khác.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m10_lich_phan_bo`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `m10/__init__.py`, `m10/lich_phan_bo.py`, `tests/test_m10_lich_phan_bo.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[M10-1a] …`.
