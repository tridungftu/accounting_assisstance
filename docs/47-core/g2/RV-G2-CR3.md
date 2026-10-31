**Biên bản review chéo G2-CR3 — Kết luận: Cần sửa (1 Chặn).**

Nhánh `lat/g2-cr3`, HEAD `b244bca`; đối chiếu `hop-nhat-20261023` tại `8116329`. Đã đọc đề, kế hoạch, chuẩn và bốn quyết định tại phụ lục `moc_da_xay_ra.v1`, CD-041 mục 2.

Quy ước **C** dưới đây: `src/kho_tri_thuc/modules/crm/contract/moc_da_xay_ra.schema.json`.

| Nội dung kiểm | Kết quả và căn cứ |
|---|---|
| Phạm vi | **Đạt:** diff chỉ thêm đúng 3 tệp whitelist; `git diff --check` không báo lỗi. |
| Bốn điểm Anh chốt | **Đạt về contract:** (a) ghim UUID lịch sử mới nhất: `C:45`; (b) điều kiện MTQ, ngày thực tế, căn cứ và nhật ký được mô tả: `C:5`; (c) CRM, M3, M10: `C:8`; (d) sự kiện điều chỉnh yêu cầu UUID lịch sử cũ, giữ sự kiện cũ và yêu cầu bên nhận tính lại: `C:6`, `C:53`. |
| Chuẩn và an toàn | **Đạt trong phạm vi diff:** trường nghiệp vụ không dấu; payload chỉ UUID, đóng trường ngoài. Không thêm SQL, role/RLS/DEFINER, quyền, thao tác xóa hoặc log bí mật/DSN. Test dưới login thật **không áp dụng** cho lát schema thuần này. |
| Dùng lại mã | **Đạt:** dùng bộ kiểm schema của G2-17 và wrapper bus hiện có: `tests/test_g2_cr3.py:18`, `tests/test_g2_cr3.py:189`. |
| Test kiểm đúng điều tuyên bố | Ca âm bao phủ trường ngoài, sai UUID, thiếu trường và điều chỉnh thiếu lịch sử cũ. Test bus dùng mock chỉ chứng minh tham số và việc không tự commit; chưa chứng minh quyền/giao dịch PostgreSQL. Có lỗi tích hợp dưới đây. |

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Test bên nhận chỉ cắt nội dung giữa §5.3 và §5.4 rồi tìm câu `(c) module nhận: CRM, M3, M10;`. Commit `d6ff24a` trên nhánh hợp nhất đã chuyển câu này xuống phụ lục cuối tài liệu. **Tình huống hỏng:** gộp CR3 với tài liệu hiện tại → `assertIn` thất bại dù schema khai đúng bên nhận. Vi phạm yêu cầu test bên nhận và không thêm lỗi so với nền. Cần sửa cách tìm khối quyết định trong chính tệp test được giao. | **Chặn** | `tests/test_g2_cr3.py:101` |

**Kiểm chứng:** đã tái hiện biểu thức tìm kiếm bằng Python chỉ đọc: worktree CR3 trả `True`, tài liệu trên nhánh hợp nhất hiện tại trả `False`. Không chạy lại toàn suite; số CR3 11/11, CR1 21/21, CR2 23/23, G2-17 28/28 là kết quả Anh cung cấp.

**Hỏi Claude:** CR3 11/11 đã được đo với tài liệu sau commit `d6ff24a` chưa? Kết quả đó hiện chưa chứng minh ca tích hợp nêu trên.

Không sửa tệp, không mở dịch vụ, không đọc kho thật, tệp bí mật hoặc `*.local.json`.