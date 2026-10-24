# L0-2i — File chưa vào git

Đối chiếu 36 nhánh (`hop-nhat-20261023`, `chinh`, toàn bộ `luu/*`): **A = 27 đường dẫn; B = 26 đường dẫn (204 cặp file–gói).** Đã quét 131 bản chụp (105 frozen + 26 workspace), 43195 lượt file/403 đường dẫn; B chỉ xét 36 Frozen head trong `TAN-DUNG-CODE.md`.

Mốc đầu nhánh git: 2026-10-24T02:58:43+00:00 (UTC); đọc blob theo commit đã ghim, không chạy theo cập nhật nhánh sau mốc này.

Có **8 file A có import xác định được** trên hop-nhat; bảng hiển thị tối đa 10 file, ưu tiên số file gọi. CSV lưu mọi bản chụp chứa file, số phiên bản, import/tham chiếu và đề xuất cho từng file A.

| File nhóm A đang được import | File trên hop-nhat import nó | Đề xuất nhánh (suy luận) |
|---|---|---|
| `src/kho_tri_thuc/m4/request_api.py` | src/kho_tri_thuc/giao_dien/m4_request.py (+4, xem CSV) | `luu/m4-04a-request-backend-20261023-01` |
| `src/kho_tri_thuc/k2/sql_crm_kiem_hd.py` | src/kho_tri_thuc/ha_tang/pg_migrations.py (+2, xem CSV) | `luu/crm-g6a-20261022-01 (đề xuất mới)` |
| `src/kho_tri_thuc/m4/sql_request_nhap.py` | src/kho_tri_thuc/m4/request_nhap.py (+1, xem CSV) | `luu/m4-04a-request-backend-20261023-01` |
| `tests/test_m4_03a_pg.py` | tests/test_m4_03a_full_basis_pg.py (+1, xem CSV) | `luu/m4-03a-kt-backend-20261023-01` |
| `tools/source7_m2_patch/config.js` | tools/source7_m2_patch/src/job.js (+1, xem CSV) | `luu/m2-00b-owned-rpc-20261023-01` |
| `src/kho_tri_thuc/k2/crm_kiem_hd.py` | tests/test_crm_g6a_m25_integration.py | `luu/crm-g6a-20261022-01 (đề xuất mới)` |
| `tests/test_crm_kiem_hd.py` | tests/test_crm_g6a_m25_integration.py | `luu/crm-g6a-20261022-01 (đề xuất mới)` |
| `tests/test_m4_02c_dto_ui.py` | tests/test_m4_04b_request_wiring_http.py | `luu/m4-02c-integration-repair-20261023-01` |

Đề xuất: lead khôi phục trước các dependency trong bảng vào nhánh gói sở hữu, rồi review các A còn lại theo CSV; B cần review delta từng gói trước khi hợp nhất. Tên nhánh suy từ tên file và gói mang bản chụp, cần lead xác nhận; bản chụp có thể chứa code kế thừa.

Phương pháp/giới hạn: so SHA1 blob sau khi bỏ mọi byte CR ở cả git và bản chụp; A xét đường dẫn, B xét tập blob toàn bộ cây cho phép trên các nhánh, kể cả blob ở tên khác (0 cặp file–gói đã khớp dưới tên khác). Không xét lịch sử commit, nhánh ngoài danh sách, file ngoài allowlist, symlink/junction hoặc dữ liệu thật. Mtime mới nhất = max metadata thư mục snapshot/files (hoặc job/workspace), thư mục và file hợp lệ trong src/tests/tools; không phải thứ tự tạo/phiên bản ngữ nghĩa. Import phân giải AST Python và literal tương đối JS/HTML; tham chiếu grep tên module có thể trùng tên hoặc nằm trong comment; không bảo đảm tìm được dynamic import. Kiểm kê chi tiết mtime xuất JSON ra stdout khi chạy script.

Chạy lại: `python -X utf8 tools/do_file_chua_vao_git.py <REPO>`; kiểm thử trong bộ nhớ: thêm `--self-test` (không cần REPO). Không chạy suite ứng dụng hay dịch vụ ngoài.

Bàn giao: CSV có sẵn trên đĩa nhưng bị `.gitignore:13` (`*.csv`) bỏ qua; lead cần đưa đích danh CSV vào commit. Worker không add/commit.
