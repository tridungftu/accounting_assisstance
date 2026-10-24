# Review độc lập CRM — nguồn và parser lần 03

19/10/2026. **27/27 criterion đạt; 0 lỗi setup.** Đã giữ nguyên input/expected của 25 criterion lượt02 và bổ sung hai ca đối chứng currency gắn đúng số tiền. 18 source-format được đọc riêng, chỉ chứng minh định dạng được tiếp nhận, không cộng thành ca nghiệp vụ đạt.

Chạy sau CLI89659 kết thúc exit0, trên manifest121 file SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`. Hash toàn bộ bản mã trước/sau giữ nguyên; baseline187 file không đổi. Guard không xóa và `PYTHONDONTWRITEBYTECODE=1` bật. Chỉ fixture DEMO, không API xác nhận thủ công, audit/repository hoặc dữ liệu thật.

Hai lỗi chặn lượt02 đã đạt: token40 không được lấy từ140; giá trị VND không được xác minh bằng câu trích dẫn USD, kể cả có nhãn xác nhận thủ công. Ca mới có hai số tiền trong cùng câu kiểm đúng liên kết số–currency: `40.000.000 USD; …60.000.000 đồng` chặn40mVND, còn `40.000.000 đồng; …60.000.000 USD` vẫn nhận40mVND. Positive controls VND/alias đồng giữ nguyên, tránh kết luận xanh bằng cách từ chối mọi input.

Các control còn lại kiểm đủ căn cứ/vị trí điều khoản, lịch suy ra, tham số optional rỗng, integer lớn, tiền lẻ VND không làm tròn, USD locale, source identity, mốc sự kiện chưa có ngày và phụ lục làm thay đổi nghĩa vụ đã thu. Không dùng source `checkOK` làm duyệt kế toán. Flat text vẫn cần review vị trí; đây không phải bằng chứng độ đúng của mọi tài liệu nguồn.

Evidence: `var/codex-dieu-phoi/crm-parser-recheck03/runtime-20261019T004834895146Z/result.json`, SHA256 `2020b1666218042019de4281ab3430d6da7e403a7f7930e775c6b5026fa03fb4`.

Probe `var/codex-dieu-phoi/crm-parser-recheck03/recheck03.py`, SHA256 `9a5d18ff6f03ad9e9bd9f83a3a0fb0800b4d4164ee95822845e44527f63df243`; plan SHA256 `ba24bff7252b9ec82df3ac8d4f95df892a851bea1fc3e3cd3a7381139064c1d0`. Exit0; trạng thái `PARSER_SOURCE_ONLY_NOT_CRM_ACCEPTANCE`. Không nghiệm thu toàn CRM/M1/GUI/toàn cây33 từ kết quả này.
