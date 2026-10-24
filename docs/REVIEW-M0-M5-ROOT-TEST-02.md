# Kiểm chứng độc lập của root — candidate M0/M5 02

19/10/2026. **CHƯA NGHIỆM THU.** Claude68305 đã kết thúc exit0 (`5dc8f8`), root đóng băng210source (`2c578f`), manifest `3d5acde6e1327542aeca488c8d72599eef042c704dcf505b372165dead069906`. Có13source thay đổi, không thêm/mất/off-scope source, không drift fixture/contract/guard được bảo vệ. Bản đóng băng: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui02-handoff-20261019-165145-481-cec6fac8/`. Không chạy M9 hoặc sửa phần mềm nguồn.

## Kết quả thực chạy

- Root full-read ba file test mới (260/640/197dòng), report02 và handoff02 trước khi cấp các lần chạy hữu hạn. Không có coder đang sửa product trong các lần chạy.
- `90ee04`: hai lớp thuần `TinhLineage`/`ThuanM5`, **14/14 đạt**, không fail/error/skip, không PG/HTTP/GUI,0forbidden calls. Source210 giữ nguyên. Summary `var/codex-dieu-phoi/m0-m5-root-pure02-a9920de1cb69/summary.json`, SHA `63c2406b0bc474e2415abc16c4ca1c29599e7099893c3651a0fc34b7e4ed3ca2`.
- `ec2eb5` → terminal `5c6559`: `test_m0_m5_migrations.py`, **12/12 đạt** trên PostgreSQL16 cục bộ,0fail/error/skip,26.458giây; gồm6ca thuần và6ca PG. Nâng fresh/CRM12, từ chối lineage được liệt kê và core backfill chạy thật trên DB DEMO mới. Evidence `var/codex-dieu-phoi/pg-retained-20261019-165402-bacfa462/`. Không áp COMMON/M5 vào kho thật hoặc DB DEMO vận hành trước đó.
- `95b71f`: `test_m5_k2.py` dừng ở **setUpClass của M5K2Pg**, nên22ca PG của lớp này **CHƯA CHẠY**. Tám method thuần đều `ok`; có1class setup error. Trường `passed=7` của bridge là phép trừ errors khỏi testsRun, không phản ánh số method thuần đã đạt; lấy log unittest làm căn cứ, không dùng số7 để báo nghiệm thu. Evidence `var/codex-dieu-phoi/pg-retained-20261019-165513-d33fab73/tests.log`, SHA `371d207ede6b14581a5beedb5098deb9f20cdbd649b45e938f8d8282cc51def2`.
- Các tập thuần trên chồng lấn, **không cộng thành tổng ca độc lập**. Đây là test do coder viết do root thực chạy, không thay ma trận độc lập về quyền, race, file và UI. HTTP/browser chưa chạy; không lặp lại HTTP khi cùng bootstrap còn lỗi.

## P1 — bootstrap thực tế hỏng với dict_row

Final `crm_khoi_dong.py` SHA `f580d1bd2fa77b02524131a919d28317e9447493e0d3dc9b7fe1e69a6391d733`,152–156. SELECT trả current_user và ba biểu thức `pg_get_userbyid` không alias riêng. Với `psycopg.rows.dict_row`, ba cột cùng tên bị gom thành một key; `_dong` lấy values chỉ còn2phần tử. Dòng156 truy cập `row[2]` gây `IndexError: list index out of range`, dù kết nối là đúng owner và đúng DB.

Tái hiện thật: `test_m5_k2.M5K2Pg.setUpClass`235 gọi `kiem_ket_noi_chu(cls.chu, cls.app)`; các connection owner/app đều dùng dict_row. Migrate/seed đã chạy xong trên DB mới, nhưng suite chưa đến service intake hoặc business assertions. Không coi lỗi setup là chứng minh các ca quyền âm đã đạt.

Sửa tên cột duy nhất hoặc dùng row factory rõ ràng tại truy vấn, bảo toàn exact-current-user/table-owner/endpoint gate. Cần đúng-owner dương với cả tuple và dict_row, sai-owner âm. Không bỏ guard, ép mọi kết quả thành owner hợp lệ hoặc đổi test sang tuple để che lỗi đường production.

## Các điều kiện chưa được test hiện tại phủ đủ

Review final migration/service/HTTPUI02 vẫn là căn cứ sửa các blocker còn lại. Tests hiện chỉ race intake với barrier, chưa có observer nhân quả, FILE cùngkey/khácphiếu, MAP cùngkey đợi lock, stale whole-basis giữ ba pointers, hoặc UI response sau await refresh. Test replay capture chỉ so receiptID, chưa so immutable promote/resultrefs đầy đủ. K08/09/10 chưa có review-positive source accepted nhưng eligibleNULL. Không làm nhẹ oracle hoặc đổi frozen reader/fixtures để xanh.

Guard không xóa file hoạt động; giữ DB/role/temp/failed attempt. Không cleanup/DROP/reset. Quyền thu hồi chỉ nằm trong DB test mới. Source210 đã recheck sau các lần chạy; không có product edit của root. Tiếp tục sửa rồi freeze/review/test candidate mới; các kết quả này thuộc đúng candidate02.
