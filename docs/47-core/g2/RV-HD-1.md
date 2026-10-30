**Biên bản review chéo HD-1 — Kết luận: Cần sửa**

Nhánh `lat/g3-hd-1`, commit `8bcfe80`; đối chiếu `hop-nhat-20261023...HEAD`. Các vị trí dưới đây thuộc worktree `.claude/worktrees/lat-g3-hd-1`.

| Nội dung kiểm | Kết quả |
|---|---|
| Phạm vi, whitelist ≤3 tệp | **Đạt:** chỉ thêm `src/kho_tri_thuc/engines/e_hoa_don/doc.py` và `tests/test_g3_hd_1.py`. |
| Chuẩn và đặc tả | **Chưa đạt:** hai lỗi ánh xạ/phân loại trạng thái dưới đây. Tên trường contract giữ đúng schema. |
| An toàn | **Đạt qua kiểm tĩnh:** không SQL, DROP/xóa, mạng, COM, log/audit hoặc credential. Role/RLS/DEFINER/`search_path` và test login PostgreSQL **không áp dụng** cho lát thư viện thuần. |
| Dùng lại mã — CD-036 | **Đạt:** dùng nguyên parser/DTO; bọc `_trang_thai_xml` và bảng ngoại lệ cũ; viết mới phép chiếu contract. Parser, wrapper và hai module test gốc không có diff. |
| Test kiểm đúng điều tuyên bố | **Chưa đủ:** CRC được làm hỏng thật, entry trùng/partial dùng ZIP trong RAM; còn thiếu hai tổ hợp đã tái hiện dưới đây. |

| Phát hiện | Mức | `tệp:dòng` |
|---|---|---|
| **Chọn MST từ cấu trúc trùng khi tên entry chứa `#`.** ZIP có entry `DEMO#1.xml`, XML chứa `<NBan><MST>0000000001</MST></NBan><NBan/>`: phép chiếu trả `ma_so_thue_ban="0000000001"`, trong khi cùng XML ở entry `DEMO.xml` trả `null`. `split("#", 1)` cắt nhầm tại tên entry, khiến kiểm tra `STRUCTURE_DUPLICATE` không khớp. Vi phạm `CONTRACT-DU-LIEU.md` §10: đầu hóa đơn mơ hồ/trùng phải trả `null`, không chọn occurrence. | **Chặn** | [doc.py:104](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-hd-1/src/kho_tri_thuc/engines/e_hoa_don/doc.py:104>) |
| **Thiếu context che trạng thái lỗi context mâu thuẫn.** Với context vừa `source_profile_ref="DEMO_LA"` vừa `profile_document_sha256=None`, hàm trả `CHO / PROFILE_DOCUMENT_NOT_BOUND`; nhánh chuyển sang `LOI` chỉ chạy khi trạng thái cũ là `XONG`. Tương tự, sai raw hash đồng thời thiếu company trả `CHO / COMPANY_ABSENT`. Mã mâu thuẫn vẫn nằm trong payload nhưng trạng thái/mã chính bị phân loại sai. Ca test hiện chỉ thử từng lỗi riêng. Căn cứ: HD-1 yêu cầu profile lạ → lỗi có mã. | **Cần sửa** | [doc.py:206](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-hd-1/src/kho_tri_thuc/engines/e_hoa_don/doc.py:206>); [test_g3_hd_1.py:114](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-hd-1/tests/test_g3_hd_1.py:114>) |

**Bằng chứng kiểm:** `git diff --check` đạt; đã tái hiện trực tiếp cả hai tình huống bằng DEMO trong RAM, chạy Python với `-B`, không ghi tệp. Không chạy lại gate/regression toàn bộ. Theo thông tin lead: test thuần đạt, kiểm bằng runtime có `jsonschema` đang chạy; runtime reviewer thiếu `jsonschema`, nên chưa xác nhận kiểm schema đầy đủ.

**Hỏi Claude:** Xác nhận mức **Chặn** tại `doc.py:104` trước khi gộp: tên entry ZIP có `#` làm phần chiếu nhận MST từ cấu trúc trùng, trái quy tắc §10; tình huống đã tái hiện.