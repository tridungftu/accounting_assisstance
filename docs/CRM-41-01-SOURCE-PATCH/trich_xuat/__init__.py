# -*- coding: utf-8 -*-
"""
trich_xuat — Trích tham số hợp đồng xây dựng bằng Local AI (phương pháp v3, RUNPOD_TRICH_XUAT_HOP_DONG.md mục 6).

Luồng một hợp đồng (quy_trinh.TrichXuat.xu_ly):
  1. Đọc .docx/.doc; còn Track Changes → Accept All trên BẢN SAO (Word; không có Word thì Python), file gốc không đổi.
  2. Tách Điều/Khoản, dựng lại số tự động.
  3. Dò vị trí tham số theo từ khoá; không khớp → Local AI tìm qua mục lục.
  4. Hỏi Local AI theo nhóm (≤ 8 tham số, ≤ 14.000 ký tự, chỉ các Khoản liên quan).
  5. Python tự kiểm: trích dẫn nguyên văn, số liệu nằm trong trích dẫn, Điều/Khoản suy lại từ trích dẫn.
  6. (Tuỳ chọn) Rà lại toàn hợp đồng cho ô vàng.
  7. Kiểm tra logic L1–L5 (luôn chạy).
  8. (Tuỳ chọn, mặc định tắt) Kiểm tra chéo trên cloud — đã che thông tin định danh, có nhật ký gửi ra ngoài.
  9. Xuất Excel/JSON từng HĐ, TONG_HOP, và cập nhật DANH_MUC_HD\\DANH_MUC_HOP_DONG.xlsx.
Chỉ dùng thư viện chuẩn Python, trừ bước ghi DANH_MUC_HOP_DONG.xlsx (openpyxl — đã dùng cho csdl_hop_dong.py).
"""
PHIEN_BAN = "2026-10-15a"
