Anh, đã thêm khai báo CRM, route lọc quyền và test trong đúng **3 file**, giữ UTF-8; chưa commit.

[JSON đầy đủ từ test cho 4 vai](C:/Users/Admin/AppData/Local/Temp/ui-2-json-4-vai.json):

| Vai | Phần | Thẻ và số DEMO |
|---|---:|---|
| Bán hàng | 6 | Báo giá nháp: 1; HĐ có đợt đến hạn: 1 |
| Kế toán | 6 | HĐ chờ kiểm: 1; HĐ có đợt quá hạn: 1 |
| CFO | 6 | Mẫu chờ duyệt: 1; HĐ có đợt quá hạn: 1; HĐ hiệu lực: 1 |
| Người xem | 3 | HĐ hiệu lực: 1 |

Nguồn đếm: S1 dùng W2/W3 cho badge Hợp đồng, W5 cho đến hạn, `co=QUA_HAN` cho quá hạn, `trang_thai=HIEU_LUC` cho hiệu lực; G2 dùng `NHAP`; G1 dùng `CHO_KIEM`/`CHO_CFO`. Thẻ đến hạn đếm **hợp đồng**, khớp danh sách lọc.

Đã bỏ thẻ chờ ký quá hạn vì chưa có ngưỡng; tiền chưa nối vì chưa có nguồn; thẻ tiền của người xem theo quyền hiện hành. Các phần chưa có nguồn không trả số. Báo giá chạm giới hạn 200 dòng cũng không trả tổng bị cắt.

**Test mới: 16/16 đạt.** CRM: 358 đạt, 37 FAIL, 2 ERROR, 95 skip. So nền v4 có **2 mã lỗi thêm do thiếu `psycopg`** tại `test_crm_khoi_dong` và `test_crm_phan_tich`; runtime DEMO bị sandbox từ chối đọc, nên **chưa đạt cổng test nền**. [Kết quả test](C:/Users/Admin/AppData/Local/Temp/ui-2-final-tests.json).

File đổi: `khung_khai_bao.py`, `crm_g.py`, `test_khung_luoi_crm.py`.

Thông điệp commit đề xuất: `[UI-2] Thêm khung CRM lọc quyền và đếm việc chờ`.