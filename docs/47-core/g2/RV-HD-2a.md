**BIÊN BẢN REVIEW CHÉO HD-2a — Kết luận: Đạt**

Nhánh `lat/g3-hd-2a`, HEAD `f41f155`, commit triển khai `750c5ca`; đối chiếu `hop-nhat-20261023...HEAD`.

Quy ước: **T** = `src/kho_tri_thuc/engines/e_hoa_don/tai.py`; **K** = `tests/test_g3_hd_2a.py`.

| Nội dung kiểm tra | Kết quả · căn cứ |
|---|---|
| Đúng đề và whitelist | **Đạt.** Chỉ thêm T và K, đúng 2 tệp được giao; không sửa chức năng cũ. |
| Portal giả, chờ đăng nhập | **Đạt.** Chưa đăng nhập trả `waiting_input`, chưa tải; test kiểm số lời gọi portal. `T:161`, `K:161`. |
| PARTIAL/coverage | **Đạt.** Phân biệt nhóm lỗi, tải dở và nhóm rỗng; giữ tệp đã nhận, coverage từng tháng/nhóm. `T:174`, `K:189`, `K:204`, `K:230`. |
| Bàn giao/dedupe | **Đạt.** Giữ kết quả chờ ACK; retry không tải lại; ACK coverage riêng; không gộp XML khác nội dung hoặc khác phiên. `T:202`, `K:251`, `K:268`, `K:332`, `K:382`. |
| Kỳ trọn tháng | **Đạt.** Từ chối kỳ lẻ/đảo ngược; kiểm năm nhuận 2000/2100, đổi năm và tháng cuối năm 9999. `T:44`, `K:121`, `K:129`, `K:137`. |
| Dùng lại mã, bảo toàn dữ liệu | **Đạt.** Gọi `doc.doc_xml` HD-1; test kiểm decimal, số 0 đầu, hash và tham chiếu nguồn riêng. `T:221`, `K:295`. |
| Chuẩn và an toàn | **Đạt trong phạm vi giả lập.** Không SQL, thay role/RLS/DEFINER/`search_path`, mở quyền hay thao tác xóa. Không có backend Chromium/thuế thật; lỗi nhóm không phản chiếu thông điệp nguồn. `T:100`, `T:175`, `K:448`. Kiểm login CSDL thực **không áp dụng** cho lát này. |

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Không phát hiện lỗi cần sửa trong diff HD-2a. | — | — |

**Xác minh:** `git diff --check` đạt. Lead báo **117/117**; reviewer chỉ đọc, không chạy lại test, nên chưa xác nhận độc lập kết quả runtime hoặc lỗi mới so với nền.

**Giới hạn nghiệm thu:** kết luận áp dụng cho HD-2a giả lập; profile/ACL, credential, tiến trình và tải thật thuộc các lát tiếp theo. Không đọc kho thật, tệp bí mật hoặc `*.local.json`; không sửa tệp.