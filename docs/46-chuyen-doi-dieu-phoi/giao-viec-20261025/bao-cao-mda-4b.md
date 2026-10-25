Đã hoàn tất, Anh.

- [khung_khai_bao.py:97](src/kho_tri_thuc/giao_dien/khung_khai_bao.py#L97): thêm `moc_cho` cho Bán hàng, dùng cache `dem`, ẩn số khi lỗi quyền.
- [test_khung_luoi_crm.py:121](tests/test_khung_luoi_crm.py#L121): kiểm tra tổng mốc, vai, lỗi quyền và cache.
- Test trước **21/21**, sau **26/26**; không lỗi mới. UTF-8 không BOM, `git diff --check` đạt.
- Không thêm thẻ vì hợp đồng hiện bắt buộc `loc` tới danh sách có bộ lọc.
- Không commit. Thông điệp đề xuất: `[MDA-4b] Đếm việc chờ mốc dự án trên icon CRM`.