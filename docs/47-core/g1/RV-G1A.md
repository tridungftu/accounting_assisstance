**BIÊN BẢN REVIEW CHÉO G1a · CSDL — 30/10/2026**

**Kết luận: Cần sửa.** Hai tài liệu phủ đủ **9/9 mục G1a-1 và 3/3 mục G1a-2**. Bảng migration có đúng **67 số/tên, đúng thứ tự, không trùng, không thiếu**, khớp KS-B và chuỗi `PG_MIGRATIONS`. Tuy nhiên, bản đồ sở hữu còn mâu thuẫn và ánh xạ tên chưa hoàn chỉnh.

Review chỉ đọc tài liệu/mã; không sửa tệp, chạy test, kết nối CSDL hoặc đọc kho thật, tệp bí mật, `*.local.json`.

**Quy ước căn cứ:** `D`, `A` lần lượt là `docs/47-core/g1/DAC-TA-CSDL.md`, `ANH-XA-MIGRATION.md`; `B` = `docs/47-core/g0/KS-B.md`; `J` = `docs/47-core/g0/so-lieu-csdl-demo.json`. `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; `H/`, `K/`, `M/` lần lượt là các thư mục `ha_tang/`, `k2/`, `m4/` dưới `src/kho_tri_thuc/`. `C` = `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md`.

**Bảng phát hiện**

| Phát hiện và yêu cầu xử lý | Mức | Căn cứ |
|---|---|---|
| **`khoa_ky` có hai khối chủ.** Thân đặc tả đặt khóa kỳ tại `ke_toan_cu`; phụ lục chuyển `khoa_ky` vào `danh_muc`. Phải chọn một chủ, đồng bộ hai tài liệu và đường kiểm khóa kỳ của chứng từ. | **Chặn** | `D:55` ↔ `A:26`; bảng hiện có tại `P:494`, guard đọc tại `P:855`. |
| **Ranh giới tiếp nhận M0/Core chưa đủ rõ.** M0 được mô tả sở hữu lần tiếp nhận và vùng tạm trước định tuyến; phụ lục lại đưa metadata tiếp nhận vào `loi_tai_lieu`. Cần ghi rõ từng bảng Core giữ và phần nghiệp vụ riêng M0 còn giữ, nhất là `stage_tin_cay` và `lan_tiep_nhan_nguon`. Hiệu chỉnh KS-B đã được giải thích, nhưng chưa loại hết sự chồng lấn trong thân đặc tả. | **Cần sửa** | `D:49`, `D:261`; `A:33`, `A:135`; `P:3173`, `P:3208`. |
| **Ánh xạ tên tiếng Việt còn thiếu.** Các cột đã được KS-B chỉ ra như `latest_observation_id`, `source_instance_id`, `acct_id`, `base_deb/base_crd` chưa có tên đích rõ trong hai tài liệu. Cần bổ sung ánh xạ hoặc ghi rõ ngoại lệ chuyển tiếp và adapter; không để “Giữ” bị hiểu là giữ cả tên cột tiếng Anh. | **Cần sửa** | `B:147`, `B:148`; `D:99`, `D:105`; `A:26`, `A:35`; `P:5248`, `P:5249`, `P:859`, `P:868`. |
| Nên ghi thẳng invariant **mỗi module một tiến trình riêng**, cùng quy tắc chỉ một phiên hoạt động cho một module trên máy triển khai. Hiện đã có bảng phiên chạy và CAS chống khởi động trùng, nhưng ràng buộc này còn phân tán. | **Gợi ý** | `D:160`, `D:164`; quyết định bắt buộc tại `C:334`. |

**Kiểm mẫu 19 khẳng định**

“Lệch” dưới đây là bất nhất thiết kế giữa hai tài liệu; các khẳng định về mã hiện có trong mẫu đều khớp nguồn.

| # | Khẳng định được kiểm | Kết quả | Căn cứ đối chiếu |
|---:|---|---|---|
| 1 | Vị trí PostgreSQL, kho file, sao lưu đã chốt | Đúng | `D:13` ↔ `C:229` |
| 2 | Bộ kiểm vùng hiện kiểm bản khai, chưa trace SQL thực | Đúng | `D:70` ↔ `H/khai_bao_module.py:228` |
| 3 | `phan_quyen` có UUID PK và UNIQUE người–pháp nhân | Đúng | `D:127` ↔ `P:65` |
| 4 | Công tắc module có khóa module × pháp nhân | Đúng | `D:143` ↔ `K/sql_module.py:15` |
| 5 | Danh bạ engine hiện lưu trong RAM | Đúng | `D:172` ↔ `H/danh_ba_engine.py:14` |
| 6 | Hàng việc có lease, chống trùng và `CHUA_RO` | Đúng | `D:188` ↔ `K/sql_hang_viec.py:25` |
| 7 | Audit hiện dùng khóa `bigserial` | Đúng | `D:192` ↔ `P:414` |
| 8 | `tep_goc` có UUID, pháp nhân, hash, đường dẫn | Đúng | `D:206` ↔ `P:196` |
| 9 | Catalog: 128 bảng, 100 RLS, 0 FORCE, 120 DEFINER, 167 PUBLIC EXECUTE | Đúng | `D:239` ↔ `J:2663`, `J:2740` |
| 10 | CRM G hiện yêu cầu kết nối chủ bảng | Đúng | `D:241` ↔ `K/crm_mau.py:112` |
| 11 | Ngữ cảnh CRM đặt transaction-local | Đúng | `D:253` ↔ `K/crm_mau.py:141` |
| 12 | Catalog ghi 303 CSDL test, 651 role test | Đúng | `D:355` ↔ `J:26`, `J:1866` |
| 13 | M0001 chứa danh tính và cấu hình nguồn | Đúng | `A:21` ↔ `P:59`, `P:71` |
| 14 | Ordinal 13 dùng COMMON, không dùng full-M9 | Đúng | `A:33` ↔ `P:2994`, `P:9596` |
| 15 | M0022 có sáu nhóm bảng kiểm chứng từ | Đúng | `A:42` ↔ `M/sql_chung_tu.py:55` |
| 16 | M0042 đang dùng helper bất biến của CRM | Đúng | `A:62` ↔ `K/sql_m3.py:158` |
| 17 | M0052 tạo bus với RLS | Đúng | `A:72` ↔ `K/sql_bus_su_kien.py:76` |
| 18 | M0063 lấy writer hiện hành; M0067 dựng validator từ M0049 | Đúng | `A:83`, `A:87` ↔ `P:12490`, `K/sql_mtq_lien_module.py:117` |
| 19 | Chủ đích của `khoa_ky` nhất quán | **Lệch** | `D:55` ↔ `A:26`; nguồn `P:494` |

**Tỉ lệ đúng của mẫu: 18/19 = 94,7%** — 18 Đúng, 0 Sai, 1 Lệch. Đây là tỉ lệ kiểm mẫu, không phải tỉ lệ hoàn thiện toàn bộ thiết kế.

**An toàn và các quyết định của Anh**

Ở mức nguyên tắc, đặc tả đã bao phủ: runtime không sở hữu bảng/không BYPASSRLS (`D:220`); DEFINER có owner, `search_path` cố định, kiểm danh tính/pháp nhân và EXECUTE giới hạn (`D:233`); thu hồi PUBLIC/default privileges (`D:237`); ngữ cảnh theo transaction, chống giả GUC, kiểm cả worker và download (`D:249`, `D:255`, `D:263`, `D:265`); truy cập qua hàm Core/danh mục được cấp/`cong_bo_*` (`D:273`). Chưa thấy đề xuất mở rộng quyền so với hiện tại; chưa có bằng chứng runtime để xác nhận an toàn triển khai. Xung đột validator M0065/M0067 đã được nhận diện tại `A:111`, cần chốt hành vi cuối trước duyệt.

Đường dẫn CSDL và nguyên tắc thêm dòng, không tạo bảng/cột theo lần phát sinh phù hợp quyết định Anh (`D:13`, `D:343`). Quy ước tên cần hoàn thiện theo phát hiện trên.

**Năm câu tại `D:367`–`D:371` đều có phương án, đánh đổi và khuyến nghị; không vượt sáu câu.** Trong các quyết định đầu vào đã đối chiếu, chưa thấy câu nào hỏi lại nội dung Anh đã chốt.

**Kết luận cuối: Cần sửa**, ưu tiên thống nhất chủ `khoa_ky`, làm rõ M0/Core và hoàn thiện ánh xạ tên trước khi ghép phiếu duyệt CSDL.