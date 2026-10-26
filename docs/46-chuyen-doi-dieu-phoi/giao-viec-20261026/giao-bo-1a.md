# BO-1a · M4 · Nghiệm thu & chi phí dự án — BOQ: thêm "bỏ dòng" (BO) và cách đọc BOQ hiệu lực theo ngày (QD-20261026-09)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép** (`$$` PL/pgSQL bị mất).
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), dữ liệu giả đúng trigger/ràng buộc thật, chạy được dưới guard giữ tệp.
- Migration: chỉ thêm `M00xx_M4_BOQ_BO`, dấu `# BO-1a — QD-09:`. Không sửa migration cũ (tới M0057). Test không ghim migration cuối.

**Căn cứ:**
- `docs\QUYET-DINH.md` QD-20261026-09 (Anh: phụ lục đổi BOQ = thêm dòng hoặc hết hiệu lực dòng bị thay; không sửa đè/xóa);
- `docs\46-chuyen-doi-dieu-phoi\KK-DON-DEP.md` §2 "M4 · Nghiệm thu…" và §3 dòng BO-1;
- mã: `m4/sql_m17.py` (bảng `m4.boq`, `m4.boq_dong` CHECK `GOC/THEM/THAY`, writer ~dòng 995), `m4/sql_review_chep.py:127–143` (bản Review có `BO`), `m4/review_phu_luc_pg.py:144` (projection phía bản chép).

**Tệp (3):** `m4/sql_boq_bo.py` mới (hằng `M4_BOQ_BO_SQL`); `ha_tang/pg_migrations.py`; `tests/test_m4_boq_bo_pg.py` mới.

**Việc (lát này KHÔNG sửa writer `m4.ghi_boq` — để BO-1b, vì writer đã có guard ma trận M0055):**
1. Mở ràng buộc `m4.boq_dong.thao_tac` cho thêm `BO` (thay CHECK bằng migration mới; tên ràng buộc lấy từ catalog, không đoán).
   - Dòng `BO` chỉ hợp lệ trong một lần BOQ gắn phụ lục (`boq.phu_luc_id` không NULL) và phải trỏ tới `ma_hm` đang hiệu lực trước phụ lục đó. Kiểm bằng trigger hoặc trong hàm đọc — chọn cách không phá dữ liệu cũ, nêu trong báo cáo.
   - Không đổi dòng cũ, không xóa.
2. Hàm đọc `m4.boq_hieu_luc(p_hop_dong_id uuid, p_ngay date) RETURNS TABLE(...)`, `STABLE`, chỉ đọc:
   - Bắt đầu từ lần BOQ gốc.
   - Áp lần lượt các phụ lục `DA_KY`, không `DA_HUY`, có `ngay_hieu_luc <= p_ngay`, theo `ngay_hieu_luc` rồi `lan`.
   - Trong mỗi lần: `THEM` thêm hạng mục; `THAY` thay dòng cùng `ma_hm`; `BO` loại hạng mục khỏi tập hiệu lực.
   - Mỗi dòng trả về kèm nguồn (`boq_id`, `dong`, phụ lục) để truy vết.
   - Phụ lục bị hủy → không áp (BOQ trở lại đúng như trước phụ lục đó).
   - Quyền đọc: theo RLS/hàm đọc M4 hiện có. Không mở rộng quyền; `SECURITY INVOKER` trừ khi có lý do, nêu trong báo cáo.
3. Không đổi tiền/khối lượng/làm tròn. Các cột tiền hiện là `text`, trả nguyên, không ép kiểu.

**Test (PG):**
- BOQ gốc + phụ lục 1 (THEM, THAY) + phụ lục 2 (BO): đọc tại các ngày trước PL1, giữa PL1–PL2, sau PL2 → đúng tập dòng;
- hủy PL2 → hạng mục bị BO quay lại;
- BO trỏ hạng mục không tồn tại → bị chặn hoặc báo rõ (theo cách đã chọn);
- dòng cũ không đổi sau mọi thao tác;
- thứ tự ổn định;
- gọi được trong `READ ONLY`.

**Báo cáo (≤ ⅓ trang)**, "Cần lead", thông điệp commit `[BO-1a] …`.
