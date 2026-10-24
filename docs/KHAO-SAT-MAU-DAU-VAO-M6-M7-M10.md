# Khảo sát mẫu đầu vào M6, M7, M10 tại máy

**Ngày kiểm tra: 18/10/2026. Kết luận:** chưa xác định được mẫu đầu vào dùng được cho bảng lương đã tính/phân bổ, khấu hao/242/335/lịch doanh thu hoặc checklist đóng sổ trong phạm vi đã kiểm. Có schema nền và tài liệu HR để tiếp tục thiết kế adapter/DEMO. Chưa có bằng chứng cho phép chốt mapping mẫu thật hoặc tuyên bố nghiệp vụ đã được kiểm chứng. Kết quả này không có nghĩa toàn máy không có các mẫu đó.

## 1. Phạm vi và cách kiểm tra

Căn cứ: TL30 D1–D3, E1–E4; TL31; TL38; `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md`; `TAI-SU-DUNG-RQ-VA-NHAN-SU.md`; `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md`; `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md`. Đường dẫn nguồn được lấy từ các tài liệu này và cấu hình nguồn đã có; không quét toàn ổ đĩa. Tài liệu dùng sourceID giả danh; đường dẫn chính xác giữ trong manifest riêng tại máy dưới `var/codex-dieu-phoi`, không đưa lên Git.

| sourceID | Phạm vi kiểm | Kết quả metadata |
|---|---|---|
| S01 | Thư mục nhận mẫu được TL30 chỉ định | Chưa tồn tại tại thời điểm kiểm tra |
| S02 | Thư mục tài liệu HR Windows, gồm các file được quy tắc HR dẫn chiếu | 2 Markdown, 1 XLSX kỹ thuật |
| S03 | Cấp gốc dự án kế toán theo TL30; chỉ file trực tiếp, không duyệt sâu các thư mục khác | Không có XLSX/XLS trực tiếp |
| S04 | Cấp gốc repo kế toán; chỉ file trực tiếp | 2 XLSX |
| S10 | Thư mục sao kê được cấu hình nguồn chỉ định | 11 XLSX, 8 XLS, 24 PDF; PDF chỉ kiểm metadata |
| S11 | Thư mục danh mục Junsky được cấu hình chỉ định | 6 XLSX |
| S12 | Thư mục chứa đầu vào sổ Junsky được cấu hình chỉ định | 13 XLSX; có file trùng phạm vi S11, đã khử trùng theo đường dẫn |
| S13 | Thư mục chứa đầu vào sổ đối chiếu riêng được cấu hình chỉ định | 1 XLSX |

Hai bộ cấu hình kho thật/kho thử có các đường dẫn trùng nhau đã được khử trùng. Tổng cộng **35 workbook duy nhất**: **27 XLSX đọc được, 80 worksheet, không lỗi đọc**; **8 XLS chỉ kiểm metadata**, do Python đang dùng chưa có `xlrd`. Không cài thêm package hoặc gọi mạng.

XLSX được đọc bằng `openpyxl` với `read_only=True`, `data_only=False`, `keep_links=False`; không mở Excel/COM, không tính công thức hoặc thực thi macro. Chỉ so khớp nhãn với whitelist kỹ thuật do script định nghĩa, tối đa **80 dòng đầu × 160 cột mỗi sheet**. Script chỉ lưu canonical field, vị trí ô, số dòng/cột khai báo, số sheet, hash; không xuất giá trị ô, tên sheet, tên file nguồn hoặc thông tin nghiệp vụ thật. Số dòng là kích thước sheet khai báo, không phải số nhân viên/giao dịch đã xác minh.

Không chạy ứng dụng, test, dịch vụ hoặc truy cập mạng; không đọc `.env`/credentials; không sửa nguồn; không xóa file. Python chạy với `PYTHONUSERBASE` riêng và `CODEX_NO_DELETE_FILES=1`; đã kiểm guard giữ file được nạp. Giữ lại toàn bộ script và manifest riêng tại máy.

## 2. Kết quả schema đầu vào

| Đầu vào cần tìm | Điều kiện nhận diện cấu trúc tối thiểu trong khảo sát | Kết quả |
|---|---|---|
| M7: bảng lương đã tính và phân bổ | `employee_id` cùng ít nhất một nhãn `gross_salary`, `net_salary`, `insurance`, `personal_income_tax` trong cửa sổ header 3 dòng; tiếp tục xem `period`, `department`, `project` nếu có | Không có cửa sổ header đáp ứng |
| M6: khấu hao/242 | `asset_id` cùng `depreciation` hoặc `allocation` trong cửa sổ header 3 dòng; các nhãn hỗ trợ `period`, `account`, `amount`, `department`, `project` | Không có cửa sổ header đáp ứng |
| M10: checklist đóng sổ | Ít nhất 3/4 nhãn `task`, `deadline`, `owner`, `status` trong cửa sổ header 3 dòng | Không có cửa sổ header đáp ứng |
| M10: lịch 335/doanh thu | Kiểm metadata tên file theo nhóm từ khóa 335/phân bổ/doanh thu và các nhãn canonical được phép | Không có file được nhận diện bằng metadata; chưa xác minh được schema lịch tương ứng |

Các nhãn rời như mã nhân viên, bộ phận, tài khoản, số tiền và trạng thái xuất hiện trong một số workbook; chúng không tạo thành mẫu lương/lịch/checklist dùng được. Workbook kỹ thuật HR tại S02 có **6 sheet**, là từ điển/đặc tả theo tài liệu HR; không phải bằng chứng có bảng lương đã tính hoặc export payroll đang vận hành. Hash SHA-256 của workbook kỹ thuật này: `c8da398a1ad303420b65cb84358a3cb1d9cf206931fe6d7797bce49f50b64567`.

Giới hạn nhận diện: mẫu có header khác whitelist, nhiều tầng, nằm sau dòng 80/cột 160, XLS chưa đọc hoặc nằm ngoài các nguồn trên có thể chưa được tìm thấy. Vì vậy không dùng kết quả âm này để xác nhận không có dữ liệu, hoặc thay yêu cầu kiểm mẫu thật bằng mẫu tự dựng.

## 3. Phần đã có và phần thực sự chưa kiểm chứng

| Nhánh | Có thể dùng ngay làm căn cứ kỹ thuật | Khoảng trống còn lại |
|---|---|---|
| M6 / R_KH | TL38 định nghĩa `master.tai_san`; schema nguồn có bảng này và loại chứng từ `BANG_KHAU_HAO`. Hợp đồng tích hợp đã quy định bảng theo kỳ, phiên bản, kiểm tổng và lịch lưu cho M10 | Mẫu khấu hao/242 đang dùng; cột/định dạng cụ thể; cách biểu diễn tổng, kỳ, phân bổ bộ phận/dự án và trạng thái duyệt; mapping mã tài sản thực |
| M7 / R_BL | TL38 định nghĩa `master.nhan_vien`, `BANG_LUONG`; tài liệu HR Windows xác định nguồn tùy biến Frappe và từ điển dữ liệu kỹ thuật | Nguồn bảng lương đã tính hiện dùng; mẫu bảng lương và phân bổ; cấu trúc BH/TNCN cùng bảng hay riêng; mapping mã nhân viên/TTCP/dự án; provenance và phiên bản bảng đã duyệt |
| M10 / định kỳ | Hợp đồng C9a đã xác định đọc lịch lưu từ M3/M6/M9/335; schema nền có `khoa_ky`; cơ chế đóng kỳ legacy không tự chứng minh checklist nghiệp vụ mới | Mẫu lịch 335/doanh thu hiện dùng; cấu trúc lịch và kỳ hiệu lực; checklist hiện hành với việc/người/hạn/trạng thái; mapping nguồn lịch sang dòng đề xuất |

**Ranh giới HR:** quy tắc và kế hoạch giai đoạn 1 nêu rõ chấm công/ca/nghỉ, công tác/tạm ứng/quyết toán; cầu Excel hạch toán và tính lương/TNCN/BHXH nằm ngoài giai đoạn 1. Không suy từ việc dùng Frappe HR rằng đã có payroll export. Chưa có đường dẫn người dùng WSL cụ thể trong các tài liệu đã kiểm; không khởi động WSL/dịch vụ, không tìm rộng UNC để truy source.

**Công việc có thể giao tiếp:** thiết kế canonical contract/validator và ca DEMO cho R_KH, R_BL, lịch định kỳ/checklist dựa trên TL38/C6/C7/C9; đánh dấu rõ đây là contract kỹ thuật đề xuất. Mapping mẫu thật và kiểm tổng/nghiệp vụ phải chờ kiểm đúng mẫu đang dùng. Không hỏi lại kiến trúc K1–K5 hoặc yêu cầu Anh thiết kế lại HR.

## 4. Bằng chứng và mức kết luận

Script khảo sát và hai manifest (private path mapping; canonical findings) được giữ riêng trong `var/codex-dieu-phoi`; không chứa giá trị ô. Hash SHA-256 của canonical findings: `1b9a2f8052f10ea526223b2c351a34802d44301f1cf073fe0bbef96d1a77a706`.

Đã kiểm **sự hiện diện của file trong phạm vi và một phần cấu trúc nhãn**. Chưa kiểm số liệu, công thức, tổng, danh mục thật, tính đúng nghiệp vụ, quyền duyệt, triển khai/go-live hoặc tích hợp chạy thật. Có schema không đồng nghĩa M6/M7/M10 đã hoàn tất hoặc đã được nghiệm thu.
