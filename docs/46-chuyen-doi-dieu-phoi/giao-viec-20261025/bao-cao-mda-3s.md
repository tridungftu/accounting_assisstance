Đã hoàn tất MDA-3s, Anh.

- `src/kho_tri_thuc/k2/crm_giao_ket.py:814,1098,1350`: kiểm mốc đúng dự án trong giao dịch lưu; nạp tên mốc một lần khi in/DOCX, không in mã kỹ thuật.
- `tests/test_crm_moc_du_an_bao_gia.py:83`: thêm test giả lập và PostgreSQL.
- `tests/test_crm_ky_ket.py:43`: cập nhật `GK_SHA256` theo cách các lát trước; test ghim đạt.
- **Trước:** 74 đạt, 3 skip; thêm 1 lỗi import vì tệp mới chưa tồn tại. **Sau:** 81 đạt, 4 skip; không lỗi mới. PostgreSQL chờ lead chạy.
- Cả ba tệp UTF-8 không BOM; không commit.

Thông điệp commit đề xuất: `[MDA-3s] Kiểm mốc riêng đúng dự án và hiển thị tên mốc trên báo giá`