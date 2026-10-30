# Review Opus G2-21 — Kết luận: Cần sửa, không Chặn (31/10 ~05:15)

Nhánh `lat/g2-21` (lát `a6bc937`). PG / tiến trình Windows thật: test_g2_21 23/23.

| Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|
| Cần sửa | Mất lease → controller kẹt vĩnh viễn. Lease 240 giây, chưa tự `gia_han`; module rảnh 300 giây; drain quá hạn lease `timeout+30`. Con chết → `so_cong.tra` báo `CONG_MAT_LEASE`, ngoại lệ thoát trước khi dọn: `_proc` còn, `chu_accept='con'`, mọi lệnh báo `TIEN_TRINH_DANG_DUNG`. Khi đã xác minh con chết + Job rỗng → thu hồi accept trong máy trước; lỗi sổ để đối chiếu. | tien_trinh.py:166-169, 234-248, 268-269 | **v2** |
| Cần sửa | stdout của con là kênh bootstrap nhưng Core không đọc sau readiness → con in khoảng 4 KB là treo vì pipe đầy. Bootstrap tách `sys.stdout` khỏi kênh, hoặc Core xả liên tục. | bootstrap.py:70-72, 119-122, 143; tien_trinh.py:161 | **v2** |
| Cần sửa | Chưa có đường đối chiếu (`doi_chieu_id`). Sau `loi_khoi_dong`, `giu_boi` còn giữ kể cả sau Admin `mo_khoa`; Core restart → dòng sổ vẫn `CON_GIU` → `CONG_CAN_DOI_CHIEU` mãi. | tien_trinh.py:143-144; 016:296-301, 405 | **Nợ đích danh G2-22** |
| Nên sửa | `thu_hoi` giữ `self.khoa` suốt drain (tới 300 giây) → dispatch không trả ngay `503` + `Retry-After: 2`, vượt hạn 30 giây (§3.10a/b). | tien_trinh.py:259-277 | G2-22 |
| Nên sửa | Lỗi khởi động khóa `LOI` ngay lần đầu, lệch §3.10b (giãn 2 giây / 4 giây, lần 3 mới khóa) — an toàn nhưng chặt hơn. | tien_trinh.py:211-215 | G2-22 |
| Nên sửa | `_don_loi` lỗi → `_proc` còn nhưng handle Job đã đóng → `kiem_con` ném `LoiHost('JOB_TRUY_VAN_LOI')`, controller kẹt. | tien_trinh.py:217-221, 234-236 | **v2** |
| Để sau | `bang_chung_id=uuid4()` không gắn bằng chứng (nên là hash thông điệp sẵn sàng). | tien_trinh.py:200 | Ghi nợ |
| Để sau | Chặn accept phía con chỉ là quy ước (`Bootstrap.socket` công khai); `KeyboardInterrupt` bỏ qua dọn. | bootstrap.py:96,128-131; tien_trinh.py:204 | Ghi nợ |

**Đạt:**
- share / fromshare đúng, một bên accept;
- blob `share(pid)`;
- `close_fds`, Job `KILL_ON_JOB_CLOSE`;
- readiness PID + thời điểm tạo + nonce `compare_digest` + phiên bản + thế hệ;
- thông số chỉ qua stdin;
- cổng bị chiếm không dò / không diệt tiến trình lạ (có test tiến trình lạ thật);
- bootstrap không ghi đĩa / log;
- không tạo tài khoản / đổi quyền;
- không có test xanh giả.
