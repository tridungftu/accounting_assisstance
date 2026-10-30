# Review Opus G2-20 — Kết luận: Cần sửa, không Chặn (31/10 ~04:35)

Nhánh `lat/g2-20` (vòng 3 `910732e`). PG: test_g2_20 31/31; G2-04/06/09/10/11/14/15/19 đạt.

| Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|
| Cần sửa | Ca âm chỉ bắt `psycopg.Error` / `LoiGiaoDich`, không kiểm mã → xanh giả nếu GRANT thiếu ("permission denied"). Kiểm `SDK_MODULE`, `TAI_LIEU_PHIEN`, `SDK_NGUON_TU_KHAI`, `TAI_LIEU_KHONG_THAY`, `VIEC_MAT_LEASE`, `TAI_LIEU_REVISION`, `TAI_LIEU_NGUON`. | test:411-459 | v4 |
| Nên sửa | "Core gắn nguồn engine": `verify` trong test viết cứng `engine_id` (`demo_g214`), không lấy từ dòng việc của lease. Bộ xác minh `BanGiaoKetQua` + IPC Core thật chưa có trong `src` → nợ lát sau. | test:523-535 | v4 (test) + ghi nợ G2-21/22 |
| Nên sửa | Phụ thuộc ngược `loi` ↔ `loi_tai_lieu` (020 cấp USAGE `loi_tai_lieu` + EXECUTE cho `vai_doi_cau_truc_loi`). Có thể dùng `loi.xac_minh_phien` / `mtq_quyet_dinh_phien` / `module_trang_thai` để bỏ. | 020:23-26,83,87 | v4 |
| Nên sửa | Chú thích nói Module Manager cấp quyền V2 khi cài, nhưng chưa có mã. GRANT chỉ cho `vai_chay_mod_*` tồn tại lúc áp 020 → module cài sau không dùng được SDK V2. | 020:307-317 | Sửa chú thích + **nợ G2-25** |
| Nên sửa | Test ACL chưa kiểm đúng danh sách được EXECUTE (`vai_chay_mod_*` có; `dang_nhap_loi`, `dang_nhap_mod_m2`, owner không). | test:501-515 | v4 |
| Nên sửa | Engine nhận mọi đối tượng có `goi`; closure trong test với được tới kết nối CSDL. Chỉ nhận kiểu kênh Core cấp. | engine.py:24-27 | v4 |
| Để sau | Heartbeat so `moi.ma is not cu.ma` chỉ đúng khi cùng tiến trình. | engine.py:77 | Khi có IPC (G2-21/22) |
| Để sau | Audit nhận `doi_tuong` tự do (chỉ regex); `ket_qua.ghi` thiếu `khoa` chống trùng §3.3. | 020:74-92; dich_vu.py:90 | Ghi nợ |

**Đạt:**
- cửa V2 buộc `session_user` = `dang_nhap_mod_<module>`, không giả module / actor;
- nguồn chặn hai lớp;
- `ghi_metadata` chỉ khác 009 ở nhánh module;
- owner / `search_path` / REVOKE đúng, không cấp runtime;
- SDK không tự commit, không lộ bí mật;
- engine không có SQL / DSN;
- rollback cả nhóm thật trên PG.
