Anh, đã hoàn tất đúng hai tệp:

- `m4_ke_toan.js:531,610,690,742`: dịch lỗi DC thành hướng dẫn tiếng Việt; tải lại khi xung đột; gợi ý định dạng và giữ nguyên số tiền nhập; lọc đợt cùng hợp đồng, nhãn theo dữ liệu; Việt hóa lỗi mạng.
- `tests/m4_03b_async.cjs:159`: thêm bốn ca hồi quy.

Test: **03B 16/16**, **01C 13/13**; không lỗi mới trong hai bộ. UTF-8 không BOM, diff sạch. Không commit.

Lưu ý: thiếu `review-m4-5b.md`; đã bám handoff. Lọc hợp đồng cần thêm lượt đọc chi tiết qua API sẵn có.

Thông điệp commit đề xuất: `[M4-5c] Việt hóa lỗi đối chiếu, hướng dẫn số tiền và lọc đợt cùng hợp đồng`