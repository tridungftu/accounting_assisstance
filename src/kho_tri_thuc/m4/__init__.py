"""M4 — Cổng hồ sơ xây dựng: adapter tái sử dụng lõi Review hồ sơ xây dựng (bản sao byte-for-byte đã pin trong `review_goc/`).

Gói M4-01 (docs/GIAO-CODE-M4-01-CONG-HO-SO-VA-TAI-SU-DUNG.md). Lõi nguồn được nạp bởi `tools/nap_nguon_review_m4.py` từ reference đã lọc
`docs/M4-REVIEW-REFERENCE-20261020/` (không đọc app nguồn ngoài workspace). Authority nghiệp vụ là K2 PostgreSQL (schema `m4`), không phải
CSDL SQLite/cấu hình/khóa của app nguồn.
"""
