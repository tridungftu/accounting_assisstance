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
7. **Gate máy chạy cả module test có gọi tới hàm/lớp bị sửa**, không chỉ test của lát: `grep -l "<tên hàm>" tests/*.py`. Mỗi đợt gộp nhiều lát chạy PG cả bộ trên hợp nhất. Bài học 26/10: PG cả bộ bắt 3 test cũ hỏng (`test_trich_chung_6` lớp giả thiếu `_tx`; `test_m4_dl5b_lich_su` vênh với DL5a; OCR test phụ thuộc tốc độ máy).
6. Worktree dựng trước khi lead commit tệp review/giao việc vòng sửa thì **không thấy** các tệp đó. Lead chép nguyên văn nội dung vào prompt, hoặc cho reviewer chạy ở repo chính và đọc mã bằng `git show`. Bài học 26/10: worker MTQ-4a3b/M9-3a vòng 2 dừng "Cần lead" vì thiếu tệp.

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

**Giữ đúng trọng tâm (Anh nhắc 26/10):**
- Trả lời **trước tiên** từng câu hỏi trọng tâm lead ghi ở mục D, mỗi câu: Đạt/Không + tệp:dòng.
- Chỉ xét **diff của lát** và đúng các tiêu chí trong giao việc + điểm nóng mục C. Không review lại mã cũ không bị diff chạm, không góp ý phong cách/đặt tên, không đề xuất tính năng hay thiết kế mới.
- Mỗi điểm **Chặn** phải có đủ 3 thứ:
  - tệp:dòng trong diff;
  - tiêu chí bị vi phạm (mục nào của giao việc, hoặc dòng nào của mục C);
  - **tình huống hỏng cụ thể** (dữ liệu vào → kết quả sai).

  Thiếu một trong ba thì ghi "Nên sửa", không ghi "Chặn".
- Phát hiện ngoài phạm vi lát (mã cũ, module khác): tối đa **2 dòng** ở "Để sau", không tính vào kết luận.
- Vòng review 2 **chỉ** xem các điểm Chặn của vòng 1 đã sửa đúng chưa và diff vòng sửa có phá gì không; không mở thêm hạng mục mới trừ lỗi Chặn do chính diff vòng sửa gây ra.

Trả ≤ 1 trang, ≤ 10 điểm, 3 mức **Chặn / Nên sửa / Để sau**; chỉ "Chặn" ngăn gộp. Không đề xuất mở rộng phạm vi.

**Hỏi Claude trước khi đi tiếp (Anh nhắc 26/10):**
- Mọi điểm Chặn có tình huống hỏng cụ thể, và mọi chỗ reviewer **không chắc** (thiếu căn cứ, nhiều cách hiểu, đụng nghiệp vụ/quyền/tiền chưa rõ), phải ghi riêng ở cuối review, mục **"Hỏi Claude"**.
- Mỗi dòng: câu hỏi + tệp:dòng + vì sao chưa rõ.
- Reviewer **không** tự kết luận Đạt cho lát còn mục "Hỏi Claude", và không tự đề xuất cách sửa ngoài phạm vi.

## E. Lead kiểm soát review của Codex (trước khi giao vòng sửa)

**Bắt buộc:** lát có điểm Chặn hoặc mục "Hỏi Claude" thì **dừng**. Lead (Claude) đọc, quyết từng điểm (Chặn thật / hạ mức / bỏ / hỏi Anh), rồi mới giao vòng sửa hoặc gộp. Worker Codex gặp chỗ chưa rõ trong khi làm cũng dừng và báo "Cần lead", không đoán.

Lead đọc review Codex và **lọc**:
- Điểm Chặn thiếu tệp:dòng, tiêu chí hoặc tình huống hỏng → hạ thành Nên sửa, hoặc bỏ.
- Điểm ngoài diff/ngoài giao việc → bỏ, hoặc ghi vào hàng đợi riêng nếu thật sự có rủi ro. Không đưa vào vòng sửa của lát.
- Review không trả lời các câu trọng tâm mục D → coi như chưa review, giao lại kèm nhắc.
- Review mâu thuẫn với kết quả gate máy (ví dụ nói test đạt khi PG có mã lỗi mới) → lấy gate máy.
- Vòng sửa chỉ gồm các điểm Chặn đã lọc, cộng Nên sửa rẻ và nằm trong cùng tệp.
- Ghi vào tệp `review-<mã>.md`: bản đã lọc, kèm dòng "lead lọc: bỏ N điểm ngoài phạm vi, hạ M điểm".

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
