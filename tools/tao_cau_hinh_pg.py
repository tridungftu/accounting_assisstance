"""V13 — tạo cau_hinh.thu-T8-postgres.toml từ cau_hinh.thu-T8.toml (giữ nguyên mọi khối, đổi data_dir, thêm [storage]).
Không ghi đè nếu file đích đã có. Không in nội dung cấu hình."""
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src, dst = root / "cau_hinh.thu-T8.toml", root / "cau_hinh.thu-T8-postgres.toml"
if dst.exists():
    print("Đã có cau_hinh.thu-T8-postgres.toml — giữ nguyên."); sys.exit(0)
text = src.read_text(encoding="utf-8-sig")
if "[storage]" in text:
    print("cau_hinh.thu-T8.toml đã có [storage] — dừng để anh kiểm."); sys.exit(2)
text, n = re.subn(r'(?m)^data_dir\s*=\s*"[^"]*"', 'data_dir = "var/plhn-thu-T8-postgres"', text, count=1)
if n != 1:
    print("Không tìm thấy data_dir trong cau_hinh.thu-T8.toml."); sys.exit(2)
text = text.rstrip() + '''

# V13 (phương án C, chốt 17/10/2026): kho thử T8 chạy trên PostgreSQL — bảng V12 nguyên trạng trong schema v12_thu_t8,
# nạp MỘT LẦN từ var/plhn-thu-T8 bằng «CHUYỂN DỮ LIỆU SANG POSTGRESQL (kho thử).cmd». Thư mục kho riêng (chỉ chứa raw/).
# Kho thật vẫn SQLite (không có [storage]). Đường lùi: bản sao lưu hằng đêm var/sao-luu-pg/v12_thu_t8-*.sqlite.
[storage]
engine = "postgres"
dsn_key = "KHO_PG_DSN"
schema = "v12_thu_t8"
'''
dst.write_text(text, encoding="utf-8")
print("Đã tạo cau_hinh.thu-T8-postgres.toml")
