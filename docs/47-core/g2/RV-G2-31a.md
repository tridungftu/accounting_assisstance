**Biên bản review chéo G2-31a — Kết luận: Cần sửa**

Nhánh `lat/g2-31a`, HEAD `796e2f0`, commit triển khai `704e85d`; đối chiếu `hop-nhat-20261023...HEAD`.

**Kiểm trọng tâm**

| Nội dung | Kết quả và căn cứ |
|---|---|
| Whitelist ≤ 3 tệp | **Đạt:** diff chỉ thêm đúng SDK, Shell và test được giao. |
| Chỉ gọi `/api/v1/`, gắn CSRF | **Đạt phần giới hạn URL/CSRF:** `trinh_duyet.js:14`, `:105`, `:127`; ngoại lệ đăng xuất sai, xem phát hiện 2. |
| 202, polling, Retry-After | **Đạt:** `trinh_duyet.js:148`, `:159`; tiếp tục với `running`/`waiting_input`, dừng đúng trạng thái cuối. |
| 409 giữ nháp, CAS | **Đạt trong cùng context:** `trinh_duyet.js:94`, `:119`, `:141`; giữ nguyên `row_version` và `expected_revision`. |
| Đổi context bỏ response cũ | **Đạt với response/polling:** `trinh_duyet.js:48`, `:65`, `:134`; còn lỗi cách ly nháp bên dưới. |
| Không lưu bí mật localStorage | **Đạt:** SDK không sử dụng browser storage; dữ liệu giữ trong bộ nhớ tại `trinh_duyet.js:45`. |
| DEMO, tiếng Việt nghiệp vụ | **Đạt trong phạm vi mã:** `trinh_duyet.js:225`, `:321`; Shell `index.html:72`. Chưa kiểm trực quan trên trình duyệt. |

**Phát hiện**

Đường dẫn SDK: `src/kho_tri_thuc/sdk_core/trinh_duyet.js`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Nháp của người trước vẫn đọc được sau đổi danh tính/pháp nhân.** `doi_ngu_canh` không cách ly `yDinh`; `doc_nhap(khoa)` trả dữ liệu mà không kiểm người/context hiện tại. Đã tái hiện: A gửi nháp gặp 409 → chuyển B/PN-B → B đọc cùng khóa nhận nguyên nội dung của A. Vi phạm yêu cầu cách ly dữ liệu/quyền của review. Cần ràng buộc truy cập nháp theo chủ thể và context; bổ sung ca âm. | **Chặn** | `trinh_duyet.js:54`, `:187` |
| **SDK chặn đăng xuất hợp lệ.** Gọi `DELETE /api/v1/phien` với CSRF nhưng không có `khoa` bị `THIEU_KHOA` trước khi fetch, nên backend không thu hồi phiên. Chuẩn API §3.6 miễn khóa chống trùng cho cả đăng nhập và đăng xuất; mã chỉ miễn `POST /phien`. Đã tái hiện. | **Chặn** | `trinh_duyet.js:108` |
| **Chưa đáp ứng yêu cầu dùng lại khung UI-1/UI-2.** Shell khai CSS riêng, SDK dựng renderer mới; không nạp asset khung hiện có. Test “dùng lại khai báo UI-2” chỉ chứng minh nhận cấu trúc `module/phan/the`, chưa chứng minh tái dùng khung theo đề dòng 17. | **Cần sửa** | `core/ui/index.html:8`; `trinh_duyet.js:233`; `tests/g2_31a.cjs:284` |

**Test và an toàn**

Tôi chạy lại `node --test tests/g2_31a.cjs`: **28/28 đạt, 0 lỗi, 0 skip**; `git diff --check` đạt. Hai ca tái hiện bổ sung xác nhận hai lỗi Chặn; bộ test hiện chưa bao phủ chúng.

Không có SQL/migration hoặc thay đổi role/RLS/DEFINER/`search_path`; kiểm login PostgreSQL thật **không áp dụng** cho lát này. Không phát hiện lệnh xóa, gọi dịch vụ ngoài hay ghi DSN/bí mật vào log/audit trong diff. Không sửa tệp, không đọc kho thật/tệp bí mật.

**Hỏi Claude:** Đề nghị lead xác nhận xử lý hai điểm Chặn trên trước khi gộp; đồng thời xác nhận việc dựng lại renderer/CSS có được chấp thuận thay yêu cầu dùng lại khung hay không.