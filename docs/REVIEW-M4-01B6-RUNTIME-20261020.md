# M4-01B6 — Kết quả kiểm độc lập hữu hạn

Ngày 20/10/2026. Trạng thái: **đủ chuyển sang xây dựng Cổng hồ sơ M4-01C**. Đây không phải nghiệm thu toàn M4 hoặc toàn phần mềm.

| Phần kiểm | Kết quả thực tế |
|---|---|
| Native đọc tệp | 50/50, không bỏ qua |
| Nhóm độc lập đọc tệp | 4/4 |
| Native PostgreSQL | 10/10, không bỏ qua |
| Nhóm độc lập PostgreSQL | 8/8 |

Native PostgreSQL gồm replay cùng yêu cầu và thao tác đồng thời; kiểm độc lập gồm nâng cấp schema, nhận DOCX/XLSX thật, chống facts tự khai, đối chiếu BOQ vật lý, điều kiện nộp, căn cứ phiên bản sau và thu hồi quyền dự án. Các kết quả này chỉ chứng minh những ca đã kiểm. Chưa kiểm GUI Cổng, trích AI/OCR thực tế, đầy đủ Review xây dựng, Request hoặc nghiệm thu/công nợ.

B6 chỉ sửa xung đột tên tham số của helper trong bộ kiểm PostgreSQL và báo cáo. Product, pure test, vendor và reference được giữ nguyên so với B5; 411/413 file runtime byte-identical, hai file khác là test PostgreSQL và báo cáo. Vì vậy kết quả 50 + 4 và 8 nhóm độc lập được mang tiếp theo chứng cứ hash; 10 ca native PostgreSQL được chạy lại thực tế. Các lần kiểm chưa đạt trước đó được giữ để đối chiếu.

Bằng chứng retained: `var/codex-dieu-phoi/m4b6-pg-runtime-prep-20261020-m9-03/root-b-runtime-closed-008c60fc452d.json` (SHA256 `d58f47df994062061ff4847769cc0ef0349198d78107e9ede5bfaa5f2d6eed2f`). Native10: `actual-native10-8b1b1e5e6edd/parent-summary.json` trong cùng thư mục; owned handle 45412, terminal 8977eb, exit 0. Dừng tiến trình và post-hash nguồn đã được xác nhận.

Code/self-test của Claude vẫn là CODE_ONLY/NOT_RUN; kết quả runtime trên do Codex kiểm độc lập. Cổng GUI là gói đang viết tiếp, chưa báo sẵn sàng cho Anh xem. Không xóa file, không chạy M9 hoặc dữ liệu vận hành.
