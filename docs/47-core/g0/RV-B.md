**BIÊN BẢN REVIEW CHÉO G0 — KS-B: ĐẠT**

Đối tượng: `docs/47-core/g0/KS-B.md`. Đối chiếu phần chung và KS-B trong `GIAO-G0.md`, TL 54, TL 55, chỉ đạo CD-026…CD-030 và catalog `docs/47-core/g0/so-lieu-csdl-demo.json`. Đường dẫn catalog trong yêu cầu có lỗi gõ; đã dùng đường dẫn đúng theo đề gốc.

Chỉ đọc; không sửa tệp, kết nối CSDL, chạy migration hoặc công cụ dọn. Không đọc các đường dẫn bị cấm.

Quy ước dưới đây: `B` = KS-B; `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; `H`, `K`, `M` = các thư mục `ha_tang`, `k2`, `m4` dưới `src/kho_tri_thuc`; `J` = catalog nói trên. Mức “—” nghĩa là không có phát hiện cần xử lý.

| Phát hiện / khẳng định được kiểm | Mức | Căn cứ đã mở trực tiếp |
|---|---|---|
| **Đúng:** ordinal 13 dùng COMMON; full-M9 là lineage lịch sử ngoài chuỗi mặc định. | — | `B:20`; `P:2994`, `P:9596` |
| **Đúng:** ordinal 17 import bản M4 hiện hành, bản partial chỉ giữ đối chiếu. | — | `B:20`; `P:8748`, `P:9594` |
| **Đúng:** M0001 tạo bốn schema và các đối tượng nền được nêu. | — | `B:24`; `P:13`, `P:21`, `P:49`, `P:59`, `P:71` |
| **Đúng:** M0008 cấp quyền có điều kiện theo sự tồn tại của role. | — | `B:31`; `P:783`, `P:786`, `P:794`, `P:801` |
| **Đúng:** M0020 chỉ thay hàm `m4.review_quyen`. | — | `B:43`; `P:10582` |
| **Đúng:** M0038 bổ sung 13 bảng `review_chep_*`. | — | `B:61`; `M/sql_review_chep.py:48`, `:53`, `:71` |
| **Đúng:** M0052 tạo `bus`, bảng `su_kien` và `inbox`. | — | `B:75`; `K/sql_bus_su_kien.py:22`, `:49`, `:64` |
| **Đúng:** M0060 tạo schema `viec` và bảng `hang_viec`. | — | `B:83`; `K/sql_hang_viec.py:22`, `:25` |
| **Đúng:** M0064 công bố bằng hàm trong `master`, chưa tạo schema/view công bố. | — | `B:87`; `K/sql_cong_bo_hoa_don.py:14`, `:15` |
| **Đúng:** M0063 lấy writer hiện hành qua `_m37_ham`; phép thay kiểm đúng một vị trí. | — | `B:92`; `P:11974`, `P:12088`, `P:12490` |
| **Đúng:** catalog ghi PostgreSQL 16.15 và trường migration `"23 23"`. | — | `B:100`; `J:2`, `J:2764` |
| **Đúng:** tổng 128 bảng, 100 bật RLS, 0 FORCE, 120 hàm DEFINER; 68 policy. Đã cộng lại số liệu. | — | `B:112`; `J:2663`, `:2674`, `:2685`, `:2696`, `:2707`, `:2718`, `:2729`, `:2742` |
| **Đúng:** bốn role ứng dụng đều NOLOGIN và không có các đặc quyền được nêu; riêng `app_web` NOINHERIT. | — | `B:120`; `J:28` |
| **Đúng:** catalog ghi 167 hàm EXECUTE mặc định PUBLIC và default privileges rỗng. | — | `B:125`; `J:2740`, `J:2741` |
| **Đúng:** CRM G nhận kết nối chủ bảng; thiếu thì từ chối; writer có guard chủ bảng. | — | `B:124`; `K/crm_mau.py:111`, `:126`; `P:9620` |
| **Đúng:** CLI vẫn có đường vào Store, rồi chọn SQLite qua factory kết nối. | — | `B:158`; `src/kho_tri_thuc/cli.py:148`; `H/store.py:89`; `H/ket_noi.py:480` |
| **Đúng:** V12 PostgreSQL dùng migration dịch riêng, đặt `search_path`, mặc định schema `v12`. | — | `B:159`; `H/ket_noi.py:184`, `:279`, `:473` |
| **Đúng:** M4 vẫn dùng SQLite trong RAM làm projection và bật `query_only` sau khi nạp. | — | `B:161`; `M/nguon_review.py:533`, `:706`, `:724`, `:771` |
| **Đúng:** M0040 chặn nâng cấp khi bảng nguồn đã có dòng, không tự suy thời điểm chụp. | — | `B:167`; `M/sql_review_chep.py:239`, `:242`, `:247` |
| **Đúng:** có 303 CSDL test, 651 role test; công cụ dọn hiện kiểm tên/phiên và xử lý tuần tự. | — | `B:171`, `B:181`; `J:26`, `J:1866`; `tools/don_csdl_test_cu.py:24`, `:41`, `:74`, `:82` |
| Dẫn chiếu hai đối tượng ở dòng 142 đang đảo thứ tự: `he_thong` nằm dòng 238, `migration_tuong_thich` nằm dòng 244. Cả hai dòng đều đã được dẫn nên vẫn truy được căn cứ. | Gợi ý | `B:142`; `H/postgres.py:238`, `:244` |
| Nên ghi rõ tên đối tượng chung trong dòng M0016 để thuận tiện tách gói: `master.nguon_pham_vi`, `giao_tiep.stage_tin_cay`, `kho.lien_ket_chung_tu`. Hiện tài liệu đã mô tả bằng nhóm “scope/stage” và đánh dấu nhiều khối. | Gợi ý | `B:39`; `P:8232`, `P:8240`, `P:8244` |

**Tỷ lệ kiểm mẫu:** 20/20 khẳng định đúng (**100%**); 0 Sai, 0 Lệch dòng làm mất căn cứ. Đây là tỷ lệ trên mẫu, không phải xác nhận toàn bộ tài liệu.

**Sót phạm vi:** bảng có đủ 67 dòng migration, số 0001–0067 không thiếu hoặc trùng. Đủ năm nhóm việc KS-B: ánh xạ migration, schema/role/quyền, quy ước tên, lõi cũ/SQLite và đề xuất dọn test. Không phát hiện bỏ sót hạng mục bắt buộc; route và công cụ ngoài thuộc KS-C/KS-D.

**Kết luận quá tay và dữ liệu cấm:** không phát hiện trong phạm vi kiểm tra. Tài liệu phân biệt rõ mã nguồn với catalog triển khai, khối đích đề xuất với schema hiện có, và giới hạn bằng chứng về owner/ACL/search_path. Không thấy DSN, khóa, dữ liệu nghiệp vụ thật hoặc tên đối tác trong KS-B.

**Kết luận: Đạt; hai góp ý trên không chặn nghiệm thu khảo sát.**