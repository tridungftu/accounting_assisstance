Đã sửa duy nhất `tests/test_m3_sql.py`: bỏ `runner_cap`/`KHO_PG_DEMO_*`, tự tạo CSDL riêng, migrate và DROP qua cleanup; giữ nguyên ca kiểm, UTF-8 không BOM.
Test: 7/16 đạt, 9 PG skip đúng dự kiến; không lỗi, `git diff --check` đạt. Không mở PostgreSQL, không commit.
Thông điệp commit đề xuất: `[M3-1a] vòng 2: tự tạo CSDL PostgreSQL riêng cho test M3`.