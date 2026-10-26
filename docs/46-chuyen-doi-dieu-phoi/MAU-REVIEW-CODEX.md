# Mẫu review chéo cho Codex (theo bài review của Claude)

**Căn cứ:** Anh chốt 26/10/2026 ~16:00 (QD-20261026-04): hạn mức Claude gần đầy, nên giao Codex tự review chéo theo bài của Claude. Claude Code chỉ kiểm xác suất.

Bài gốc:
- `.claude/agents/kiem-nhanh.md` (soát nhanh);
- `.claude/agents/review-lat.md` (review kỹ);
- bài học từ các review Opus ngày 26/10 (mục C dưới).

## A. Cách lead giao

1. Worker Codex làm xong lát. Lead commit, chạy gate máy (diff đúng tệp, mã hóa, test thuần + PG so nền v4, số skip).
2. Lead giao **một Codex khác** review, chỉ đọc:
   - lệnh: `codex exec --sandbox read-only -c model_reasoning_effort=high -o <tệp review> - < <prompt>`;
   - prompt = phần B + C bên dưới, kèm: mã lát, nhánh/commit, tệp giao việc, tệp báo cáo worker, kết quả gate máy của lead.
3. Codex review trả **Đạt / Cần sửa**, mỗi điểm có tệp:dòng.
   - **Chặn** → vòng sửa giao lại worker.
   - Vòng review 2 chỉ xem các điểm Chặn của vòng 1.
   - Tối đa 2 vòng review; quá thì lead báo Anh.
4. **Claude kiểm xác suất:**
   - rút ngẫu nhiên khoảng **1/4** số lát đã Đạt review Codex (`python -c "import random;print(random.random()<0.25)"`);
   - lát rút trúng: lead tự đọc nhanh các điểm nóng của diff (mục C). **Không** gọi subagent Opus/Haiku;
   - ghi "kiểm xác suất: có/không" vào commit gộp.
5. Lead vẫn giữ gate máy cho **mọi** lát, vì chạy bằng script, không tốn hạn mức review.

## B. Phần cố định của prompt review

Bạn là reviewer Codex, **chỉ đọc**: không sửa tệp, không commit, không mở server/PostgreSQL, không đọc `var\`, `.env`, `cau_hinh.that.toml`, dữ liệu thật.

Đọc theo thứ tự:
1. tệp giao việc;
2. tài liệu nghiệp vụ được dẫn trong đó;
3. `git diff <nhánh gộp>...<nhánh lát>`;
4. báo cáo worker.

Kiểm 5 việc, mỗi việc một kết luận:
1. **Phạm vi** (kiểm nhanh): diff chỉ chạm tệp được giao; không dữ liệu thật trong test/fixture; báo cáo worker khớp diff (không tuyên bố việc chưa làm, số test/skip đúng).
2. **Đúng yêu cầu:** từng tiêu chí trong giao việc đã làm **đúng ý nghiệp vụ**, không chỉ "chạy được".
3. **Tiền, số liệu, quyền:** phép tính, làm tròn, đơn vị tiền, tổng khớp chi tiết; quyền kiểm ở máy chủ, không chỉ ẩn nút.
4. **Không phá phần cũ:** đường cũ giữ nguyên; không gọi thẳng `api.anthropic.com` / `api.openai.com` (chỉ qua cổng AI; M9 chỉ Local).
5. **Giao diện/câu cho người dùng:** tiếng Việt nghiệp vụ, không mã kỹ thuật, không "Cần Anh/lead"; ngày dd/mm/yyyy; tiền có đơn vị.

Trả ≤ 1 trang, ≤ 10 điểm, 3 mức **Chặn / Nên sửa / Để sau**; chỉ "Chặn" ngăn gộp. Không đề xuất mở rộng phạm vi.

## C. Điểm nóng phải soi (bài học review 26/10)

- **Quyền làm rộng hoặc fallback:**
  - resolver/cổng quyền nhận đối tượng ngoài module, ví dụ liên kết VAY/L11 lọt vào M1 (MTQ-4a3a);
  - khi đã bật ma trận thì không có đường quay về quyền cũ;
  - kiểm quyền mới không được chặn vai hợp lệ đang dùng, ví dụ DUYET/KE_TOAN bị 404 (DL5a).
- **Tiền/khối lượng:**
  - NULL ≠ 0;
  - `Decimal`, không float;
  - **không cộng khác đơn vị tính** (DL5b);
  - không cộng trùng hai nguồn;
  - mã trùng → cần xem lại.
- **Căn cứ/hash/bản ghi bất biến:**
  - basis, JSON kết luận/seal giữ nguyên byte khi không có dữ liệu mới;
  - câu ghi vào bản ghi bất biến phải trung tính.
- **Giao dịch:** không đổi cách mở/commit giao dịch dùng chung cho mọi luồng, vì có thể làm hỏng test fallback (DL5a: 8 mã lỗi mới).
- **SQL/migration:**
  - `SECURITY DEFINER` giữ `search_path`, ACL (`REVOKE PUBLIC`, `EXECUTE` chỉ `app_web`);
  - không SQL động;
  - migration mới không sửa hằng cũ;
  - test không ghim migration cuối hoặc hash byte tệp.
- **Test:**
  - test PG tự tạo `kho_test_*`, không đọc `KHO_PG_DEMO_*`;
  - không skip âm thầm;
  - dữ liệu giả đúng trigger/ràng buộc thật.
- **Tìm kiếm/AI (M9):**
  - thử câu hỏi tự nhiên và câu hỏi không có trong hợp đồng;
  - không trả lời bằng số khi trích dẫn không chứa số đó.
