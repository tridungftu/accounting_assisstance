**Biên bản review chéo G2 đợt A — G2-00: Cần sửa; G2-33: Cần sửa.**

Review bằng `git show` tại `c83f04f` và `d175a3b`. Cả hai commit đều đổi đúng **3 tệp được giao**. Tôi không sửa tệp, không đọc kho thật/tệp bí mật, không gọi dịch vụ ngoài.

**G2-00 — `c83f04f`**

Đúng hướng dựng CSDL rỗng, kiểm tên, không DROP/xóa, chống ghi đè và tái sử dụng parser/loader/thay tên DSN từ `tao_ket_noi_demo_rieng.py` (`tools/tao_core_demo.py:28`). Không thấy in credential ra stdout/stderr.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Chưa chặn junction/symlink tại thư mục dữ liệu PostgreSQL.** `_kiem_cum` chỉ chuẩn hóa và so chuỗi `data_directory`; không kiểm đường dẫn vật lý như đối với kho tệp. Tình huống: đường dẫn cụm mặc định là junction tới `D:\DU-LIEU-KE-TOAN\...`, PostgreSQL báo đường dẫn alias đó, endpoint/tên CSDL nguồn khớp → guard chấp nhận và có thể `CREATE DATABASE` trên cụm thật. Vi phạm yêu cầu từ chối cụm thật, không vượt bằng symlink. | **Chặn** | `tools/tao_core_demo.py:114`, `:117`, `:162`, `:170` |
| **Có ghi DSN chứa mật khẩu dưới dạng rõ.** `moi` giữ nguyên credential nguồn rồi `json.dump` vào tệp kết nối; không có ACL/DPAPI tại bước ghi. Điều này không đáp ứng nguyên văn tiêu chí review “không in/ghi DSN, mật khẩu”; tuy nhiên đề lại yêu cầu tạo cấu hình kết nối, cần lead phân xử ngoại lệ này. | **Cần sửa** | `tools/tao_core_demo.py:157`, `:178` |
| Test từ chối chuyển hướng chỉ mock `Path.resolve` cho kho tệp; không bao phủ junction của `cum.data_dir`. Trong test sai cụm, `execute.side_effect` bị bỏ nên `so_tao == 0` không còn chứng minh rằng không phát lệnh CREATE. Cần kiểm SQL thực sự đã gọi và bổ sung ca alias cụm. | **Cần sửa** | `tests/test_g2_00.py:48`, `:176`, `:180` |

**Kết luận G2-00: Cần sửa.** Guard tên, đường dẫn kho và test credential/idempotence có kiểm tra hành vi cụ thể; chưa đủ bảo đảm ranh giới cụm PostgreSQL.

**G2-33 — `d175a3b`**

Mặc định chỉ preview; nhánh `-ApDung` kiểm quản trị rồi dừng vô điều kiện. Không có lệnh tạo/xóa tài khoản, ghi ACL hoặc sinh mật khẩu nên chưa phát sinh lộ mật khẩu. Mẫu ACL trong RAM được kiểm owner, DACL bảo vệ và đúng một ACE `ktt_core` (`tests/test_g2_33.py:139`).

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Chưa có đường áp dụng tài khoản/ACL/DPAPI.** Dù có `-ApDung` và quyền quản trị, script luôn ném `CAN_LEAD`. Đây là fallback an toàn được đề cho phép, nhưng chưa hoàn thành chức năng provisioning/chạy lại và chưa thể coi G2-33 là phụ thuộc đã sẵn sàng cho thử tiến trình thật. | **Cần sửa** | `tools/tao_tai_khoan_core.ps1:110`, `:157`, `:162` |

**Kết luận G2-33: Cần sửa.** Test thực sự chạy preview và dựng ACL trong RAM, không chỉ mock rỗng; kết quả ấy chưa chứng minh ACL trên đĩa, cách ly tài khoản hay DPAPI thực tế. Không phát hiện đường vượt sang đích thật trong phiên bản hiện tại vì mọi mutation đều bị chặn.

**Hỏi Claude theo mẫu review**

- Xác nhận xử lý điểm **Chặn** về junction cụm tại `tools/tao_core_demo.py:117`; tình huống trên được suy ra từ mã, chưa thử PostgreSQL thật.
- Tệp kết nối DEMO tại `tools/tao_core_demo.py:178` có được miễn tiêu chí “không ghi DSN/mật khẩu” không? Đề và tiêu chí review hiện khác nhau.
- G2-33 tại `tools/tao_tai_khoan_core.ps1:157` được nghiệm thu riêng phần preview hay phải hoàn tất provisioning trước khi đóng lát?

**Test:** Lead báo **16/16** và **12/12**. Reviewer **NOT_RUN**: không tìm thấy Python trong PATH; chưa xác minh độc lập regression so với nền.