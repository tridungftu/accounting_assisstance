Anh, đã hoàn thành đúng 3 tệp, UTF-8 không BOM.

- **Đã thêm:** `money` dùng Decimal, `relations` đọc điều chỉnh/thay thế; thiếu hoặc mơ hồ → `HOLD` kèm lý do.
- **Thẻ:** `TgTCThue`, `TgTThue`, `TgTTTBSo`, `TGTKCThue`; `THTTLTSuat/LTSuat/{TSuat,ThTien,TThue}`; `TTHDLQuan/{TCHDon,LHDCLQuan,KHMSHDCLQuan,KHHDCLQuan,SHDCLQuan,NLHDCLQuan}`. Dùng lại `DVTTe`.
- **Test trước → sau:** 117/138 → **130/151 đạt**, cùng 21 skip PostgreSQL; không lỗi mới. 13 test mới đạt; toàn bộ trường cũ trên 32 kết quả fixture không đổi.
- **Cần Anh:** chốt cách thể hiện giá đất được trừ theo M3; reader chỉ đọc số khai báo.
- **Bàn giao:** fixture `tests/fixtures/m2_ban_ra.xml` bị `*.xml` ignore; lead cần `git add -f`.

Không commit. Thông điệp đề xuất: `[M2-BR4] Đọc tiền exact và quan hệ hóa đơn, bảo toàn contract cũ`.