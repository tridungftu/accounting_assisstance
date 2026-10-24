# Kiểm tra độc lập mốc học V13 — 18/10/2026

**Kết luận: `NOT_VERIFIED` cho backtest không dùng thông tin tương lai.** Mốc học sổ 30/06/2026 đang được giữ trên snapshot được kiểm tra; bộ lọc POLICY loại đúng 59 phiên bản có `lan_dau >= 01/08/2026` và 26 phiên bản tháng 7 trong các ngày sao kê thực tế. Tuy nhiên, một POLICY không có ngày lần đầu vẫn lọt qua và được chọn cho **3/105 dòng T8**. Các thống kê quy tắc và ảnh chụp công nợ sau mốc vẫn tham gia đề xuất; chưa đủ chứng cứ để nghiệm thu cột backtest sạch.

Đây là kiểm tra chỉ đọc của Codex, không sửa source/test/tool, không gọi Claude hoặc dịch vụ mạng. Audit chính dùng đúng `snapshot-that/kho.sqlite` bên dưới thư mục ghi trong `var/codex-dieu-phoi/evidence-current.txt`, mở SQLite bằng `mode=ro`, `PRAGMA query_only=ON`. Tìm nguồn bổ sung bằng sáu backup cũ và metadata file trong workspace như phần cuối báo cáo. SHA-256 các bản gốc trước và sau bằng nhau. Chỉ công bố số tổng hợp tại [evidence/cutoff-audit.json](../evidence/cutoff-audit.json); bản forensic có dữ liệu nằm trong `var/`, không thuộc tài liệu công bố. Kết quả gắn với các source hash trong JSON; sau sửa code phải kiểm tra lại.

## Căn cứ và ý nghĩa trường thời gian

- Objective yêu cầu học đến 30/06/2026, chấm T7–T8 và không dùng dữ liệu tương lai.
- `docs/HOP-DONG-DU-LIEU.md:340` quy định cột nghiệm thu T8 chỉ nhận POLICY có first_seen trước 01/08/2026, **loại cả ngày thiếu**; cũng ghi rõ thống kê/lần cuối và snapshot kế thừa là giới hạn của cột này, không đủ gọi là backtest độc lập sạch.
- `tri_thuc/human_workbook.py:165` lấy ngày hiệu lực POLICY từ `source_row.lan_dau`. `:132–136` giữ `known_at=at` của lần nhập. Vì vậy `known_at` sau mốc không tự chứng minh một quy tắc được phát sinh sau mốc. Audit dùng `lan_dau` cho lần đầu, `lan_cuoi` cho khoảng thống kê, `business_date` cho ngày chứng từ/snapshot; không gán ngày nhập thành ngày nghiệp vụ.
- `tri_thuc/service.py:110–140` kiểm ngày hiệu lực, `known_at`, approval/revoke/supersession. QuickPosting dùng `include_pending=True`; đó là cơ chế đề xuất có căn cứ chờ duyệt, không phải chứng nhận tri thức đã có ở ngày nghiệp vụ quá khứ.

## Kết quả trên snapshot hiện tại

Runtime là `learning_cutoff=2026-06-30`, `scoring_mode=true`. Có 105 BANK của 20 ngày từ 03/08 đến 31/08/2026, không có BANK T7 hoặc BANK trước mốc trong snapshot này. Do đó audit này chưa kiểm chứng kết quả T7.

| Nhóm | Số lượng và kiểm tra |
|---|---:|
| POLICY toàn kho | 810 |
| `lan_dau <= 30/06` | 724 |
| `lan_dau` T7 | 26 |
| `lan_dau >= 01/08` | 59 |
| Thiếu/không đọc được `lan_dau` | 1 |
| POLICY union được `Knowledge.query` trả về trên 20 ngày BANK | 327 |
| POLICY union còn sau `Engine._query` | 242 = 241 trước mốc + 1 thiếu ngày |
| POLICY bị bộ lọc loại trên 20 ngày BANK | 85 = 26 T7 + 59 từ T8 |
| JOURNAL | 4.222; từ 01/09/2024 đến đúng 30/06/2026 |
| OPEN_ITEM | 1.581; tất cả thuộc snapshot 12/10/2026 |
| `quick_condition_learning` | 0 |

Số union không phải số quy tắc đồng thời có hiệu lực ở một ngày: `valid_to` vẫn được áp dụng theo từng ngày BANK. 29 RULE hiện có là JOURNAL_PATTERN được sinh từ chứng từ cũ, không mang `lan_dau`; không thể coi thiếu trường này ở RULE tự sinh là chứng minh rò rỉ. CATEGORY khác đi qua đường thời gian riêng, không được bộ lọc `lan_dau` của POLICY/RULE tự bảo đảm.

## Phát hiện cần xử lý

**F1 — POLICY thiếu ngày được dùng trong cột nghiệm thu.** `de_xuat/engine.py:200–213` trả chuỗi rỗng khi không đọc được `lan_dau`; `:220` so trực tiếp `'' <= limit`, nên cho qua. POLICY thiếu ngày có `valid_from` trước mốc và đã APPROVE, nhưng không có `first_seen` thay thế hoặc `lan_dau` trong `source_row`. Nó được chọn ở 3/105 proposal, góp 6 field confidence `APPROVED_TEMPLATE`. Đây là vi phạm cụ thể của cổng loại ngày thiếu tại hợp đồng dữ liệu:340. Không dùng ngày approval/import để suy đoán ngày lần đầu rồi chữa metadata hồi cứu.

Hướng sửa để Claude thực hiện: trong chế độ đánh giá có mốc học, POLICY phải có ngày lần đầu hợp lệ và nằm trong giới hạn, hoặc được báo `NOT_VERIFIED`/loại khỏi cột nghiệm thu. Cần test DEMO thiếu ngày, ngày từ T8, ngày trước mốc; giữ hành vi production theo quyết định vận hành hiện có. Audit này không tự thay business policy.

**F2 — Thống kê quy tắc chưa được khóa theo mốc học.** Trong 242 POLICY eligible, 117 có `lan_cuoi > 30/06`; 87 trong số đó có `lan_cuoi >= 01/08`. Cả 117 mang `so_lan_gap`, `so_lan_dung`, `do_on_dinh`. `engine.py:116–118` dùng số gặp/đúng để nâng confidence STRONG; `:302–315` dùng độ ổn định/số gặp/trạng thái để quyết định quy tắc có nhường chứng cứ từ sổ hay không. Vì vậy thống kê này tác động kết quả, không chỉ được hiển thị trong giải thích.

Trong 105 proposal đã lưu, 44 dòng dùng POLICY có `lan_cuoi > 30/06`, gồm 42 dòng dùng POLICY có `lan_cuoi >= 01/08`. Những POLICY đó góp 62 field confidence: 36 debit account, 4 credit account, 22 project; 52 mức `PENDING_RULE_STRONG` và 10 `PENDING_RULE_WEAK`. Các field counterparty/account/project trong payload không có lịch sử version để xác lập giá trị tại 30/06. Điều này **không chứng minh mỗi giá trị đã bị sửa sau mốc**, nhưng không đủ chứng cứ rằng chúng chỉ phản ánh thông tin trước mốc.

**F3 — Công nợ hiện tại được dùng khi chấm tháng 8.** `QuickPosting._bundle`, `giao_dien/quick.py:105–108` đưa toàn bộ OPEN_ITEM có bằng chứng trước ngày chạy vào bundle. `engine.py:359–361` chọn item theo đối tượng/chiều/tiền, không lọc ngày snapshot theo ngày BANK hoặc mốc học. Trong proposal đã lưu, 31/105 dòng dùng 17 OPEN_ITEM làm confidence; toàn bộ các item này thuộc snapshot 12/10, sau ngày BANK. Ngày `business_date` ở đây là `metadata.as_of` của snapshot (`nguon/that.py:647`), không phải ngày hóa đơn. Không thể biến snapshot này thành số dư tháng 6/tháng 8 chỉ bằng cách lọc ngày hóa đơn. V11 đã ghi hạn chế này ở `docs/BAO-CAO-V11.md:76`; việc đã ghi hạn chế không tạo bằng chứng đạt mục tiêu backtest không dùng tương lai.

## Khả năng dựng bộ đánh giá sạch

4.222 JOURNAL trước mốc đủ làm đầu vào cho nhánh học pattern từ sổ hiện có; `engine.py:568–575` và `giao_dien/v9b.py:350` khóa ngày học. Trên proposal đã lưu, 25 dòng dùng 261 JOURNAL làm confidence và không có JOURNAL sau mốc.

Tuy nhiên chưa đủ nguồn để tái dựng chính xác toàn bộ thống kê quy tắc nhập sẵn. Trong 117 POLICY có lần cuối sau mốc, 100 trigger đòi BANK_ACCOUNT/COUNTERPARTY_NAME, 17 chỉ dùng regex. Snapshot không có BANK trước mốc; JOURNAL không thay thế nguyên trạng sao kê về các trường trigger và outcome cần chấm. Cả 117 POLICY không tham chiếu evidence bằng document ID của từng lần gặp, và không có `supersedes_id` cho lịch sử payload. Với regex-only có thể nghiên cứu một phương pháp dựng lại từ sổ, nhưng chưa được chứng minh tương đương với tập lần gặp/đáp án nguồn, không nên tự coi đó là cùng luật đã chốt.

Đề xuất để nghiệm thu mà không sửa hành vi production:

1. Sửa F1 và chạy lại số trước/sau trên hai engine; số 62/33/10 hiện tại chỉ là kết quả trên snapshot hiện tại, chưa được chứng nhận sạch và không quy kết nguyên nhân tăng so với mốc lịch sử.
2. Trong `scoring_mode`, khai trạng thái `NOT_VERIFIED` khi thiếu snapshot tri thức, thống kê và công nợ có provenance theo mốc. Có thể vẫn chạy để kiểm hồi quy kỹ thuật nhưng phải tách cột hồi cứu khỏi cột có đủ bằng chứng thời gian.
3. Muốn chứng nhận backtest không dùng tương lai cần snapshot tri thức/statistics/open-item có thời điểm xác lập, hoặc dựng lại từ nguyên liệu huấn luyện trước mốc và đối chiếu bằng chứng từng quy tắc. Thiếu nguồn không tự lùi ngày, suy mốc từ mtime hoặc loại một vài trường rồi gọi kết quả là sạch.

## Tìm nguồn sạch có sẵn

Đã kiểm tra sáu backup tiêu biểu được giao: trước V10, trước V11, trước V11.1, trước V12, trước V13 và trước khi xóa T7–T8. Bốn ZIP được trích xuất **nguyên bytes** vào bản forensic mới, kèm sidecar nếu có, rồi mở bản sao `mode=ro`; hai SQLite nguyên mở `mode=ro`. Hash nội dung DB trích xuất khớp member ZIP, hash bản sao không đổi sau đọc, hash mọi backup gốc không đổi, `integrity_check=ok` cho cả sáu. Các ZIP không chứa WAL/SHM. Kết quả thử RAM có chuẩn hóa journal header ban đầu đã bị loại khỏi bằng chứng; số trong JSON là từ lần đọc SQLite nguyên bytes.

| Nhóm backup | OPEN_ITEM | POLICY |
|---|---|---|
| Trước V10/V11/V11.1 và trước xóa T7–T8 | Mỗi bản 1.581 item, snapshot 26/09/2026 | 809; `lan_cuoi`: 607 trước/đúng 30/06, 56 T7, 146 từ T8 |
| Trước V12/V13 | Mỗi bản 1.581 item, snapshot 12/10/2026 | 810; cùng 809 POLICY trên và 1 thiếu ngày |

Không có snapshot công nợ trước/đúng ngày BANK hoặc rulebook freeze toàn bộ tại 30/06 trong **sáu bản đã đọc**. Không đánh đồng tên backup V cũ với thời điểm sạch của dữ liệu bên trong. Đây là kiểm chứng nội dung có sẵn, chưa phải xác nhận tính đầy đủ lịch sử của backup khi không có WAL nguồn.

Tìm metadata trong cây workspace phát hiện 7 file ứng viên DGBList/NKC, 4 file công nợ, 7 ứng viên rulebook/từ điển. Chưa đọc nội dung các workbook này trong nhiệm vụ; tên/ngày file và mtime không chứng minh kỳ số dư hoặc thời điểm freeze. Vì vậy nguồn sạch từ các file này vẫn **chưa kiểm chứng**, không khẳng định toàn máy không có dữ liệu phù hợp. Danh sách metadata trong JSON không chứa tên đối tác, STK hay dòng dữ liệu.

Chốt nhiệm vụ temporal ở trạng thái `NOT_VERIFIED`; không mở thêm nghiên cứu backend. Chưa sửa source, chưa chạy lại proposal sau sửa, chưa dựng lại tri thức theo mốc, chưa kiểm chứng T7. Đây là trạng thái kiểm chứng, không phải thay đổi kiến trúc hoặc tự phê duyệt vận hành thật.
