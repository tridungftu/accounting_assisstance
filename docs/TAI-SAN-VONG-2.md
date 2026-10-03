# Kiểm kê tài sản vòng 2

Ngày 18/09/2026. Đọc tại chỗ, không chạy script nguồn và không ghi lại workbook. Kích thước là byte; ngày sửa hiển thị UTC+07, **không phải known_at/as_of**. Manifest đầy đủ từng file tại [KIEM-KE-FILE.json](../var/vong-2/V0/KIEM-KE-FILE.json); metadata/AST script tại [KIEM-KE-SCRIPT.json](../var/vong-2/V0/KIEM-KE-SCRIPT.json). Các thư mục có thể chứa bản sao của nhau, không cộng tổng thành số tài sản duy nhất.

## 1. Các thư mục thực đã kiểm kê

| Nhóm | Đường dẫn tuyệt đối | Số file | Phân loại |
|---|---|---:|---|
| original_trial | `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\thu-nghiem-claude-2026-09-18` | 2 | {'.md': 1, '.zip': 1} |
| rules | `D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\bo_quy_tac` | 96 | {'.py': 23, '.md': 13, '.bat': 1, '.xlsx': 48, '.zip': 2, '.xls': 8, '.txt': 1} |
| bank_sources | `D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\Ngân Hàng` | 35 | {'.pdf': 24, '.xlsx': 3, '.xls': 8} |
| catalogs | `D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\DANH MỤC` | 6 | {'.xlsx': 6} |
| invoice_csv | `D:\Claude\Claude outputs\hoa_don` | 3 | {'.csv': 3} |
| invoice_originals | `D:\Claude\Phan mem download hoa don\Download hoa don\PLHN` | 1986 | {'.xml': 1907, '.xlsx': 67, '.pdf': 12} |
| base_backup | `D:\Claude\Base back up module\backup\PLHN` | 7227 | {'.json': 2563, '.xlsx': 134, '.pdf': 3932, '.jpeg': 274, '.jpg': 253, '.png': 12, '.doc': 3, '.docx': 25, '.rar': 3, '.xls': 22, '.eml': 1, '.md': 4, '.py': 1} |
| loose_ledgers | `D:\Claude\Phan mem ho tro ke toan\Mang ngan hang` | 4 | 4 sổ rời được chỉ định |

## 2. Tất cả 23 script trong bo_quy_tac

Đã kiểm tra AST/I/O và lưu phần đầu/entry point. Năm script được chỉ định đã đọc sâu ở bảng sau. **Chưa chạy bất kỳ script khảo sát nào nên chưa chứng nhận tái sử dụng được.** Đường dẫn đầy đủ có trong liên kết tên file và manifest.

| Script | Byte | Sửa lúc (UTC+07) | Đầu vào đọc được từ code | Đầu ra ghi được từ code | Dependency trực tiếp ngoài stdlib |
|---|---:|---|---|---|---|
| [00_danh_muc.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/00_danh_muc.py>) | 8,453 | 04/09/2026 11:31:39 | Excel sáu danh mục trong nguon/danh_muc | du_lieu/dm_*.pkl; thống kê console | pandas |
| [01_doc_du_lieu.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/01_doc_du_lieu.py>) | 4,354 | 04/09/2026 07:04:18 | Excel sao kê và sổ trong nguon | sao_ke.pkl, nkc.pkl | pandas |
| [02_ghep_chuan.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/02_ghep_chuan.py>) | 7,708 | 04/09/2026 12:35:34 | sao_ke.pkl, nkc.pkl | chung_tu_dong.pkl, tap_chuan.pkl, can_xac_nhan.pkl | pandas |
| [03_khai_thac_quy_tac.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/03_khai_thac_quy_tac.py>) | 8,141 | 04/09/2026 12:35:34 | tap_chuan.pkl | quy_tac.pkl, doi_tac.pkl, tu_khoa.pkl, can_xem_lai.pkl | chung, pandas |
| [04_do_hieu_qua.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/04_do_hieu_qua.py>) | 10,203 | 04/09/2026 12:35:35 | tap_chuan.pkl | ket_qua_kiem.pkl, du_doan_sai.pkl | chung, pandas |
| [05_gop_excel.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/05_gop_excel.py>) | 13,712 | 04/09/2026 13:19:27 | các pickle kết quả trung gian | BO-QUY-TAC.xlsx, ghi lại workbook | chung, openpyxl, pandas |
| [06_khop_cong_no.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/06_khop_cong_no.py>) | 8,108 | 04/09/2026 12:35:36 | tap_chuan.pkl, dm_cong_no.pkl | anh_xa_stk.pkl, bac0.pkl | pandas |
| [07_phieu_coverage.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/07_phieu_coverage.py>) | 6,047 | 04/09/2026 13:13:08 | tap_chuan.pkl, dm_cong_no.pkl | phieu_coverage.pkl, thống kê | chung, pandas |
| [08_chan_doan.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/08_chan_doan.py>) | 11,446 | 04/09/2026 13:19:27 | tap_chuan.pkl, dm_cong_no.pkl, nkc.pkl | chan_doan.pkl, thống kê | chung, pandas |
| [11_loc_sao_ke.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/11_loc_sao_ke.py>) | 25,794 | 04/09/2026 13:51:34 | sao_ke.pkl, dm_doi_tuong.pkl, tap_chuan.pkl, dm_du_an.pkl nếu có | LOC-SAO-KE-T1-T6.xlsx và pickle lọc | chung, openpyxl, pandas |
| [12_loai_giao_dich.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/12_loai_giao_dich.py>) | 18,021 | 05/09/2026 06:04:31 | sao_ke.pkl, tap_chuan.pkl, dm_tai_khoan.pkl | LOAI-GIAO-DICH.xlsx, loai_giao_dich.pkl | chung, pandas |
| [13_but_toan_thang.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/13_but_toan_thang.py>) | 16,474 | 05/09/2026 06:27:27 | sao_ke, dm_doi_tuong, tap_chuan, loai_giao_dich, dm_tai_khoan dạng pickle | BUT-TOAN-T<tháng>.xlsx, but_toan_t<tháng>.pkl | chung, openpyxl, pandas |
| [14_xuat_junsky.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/14_xuat_junsky.py>) | 24,458 | 05/09/2026 14:12:15 | but_toan_t<tháng>.pkl, sao_ke.pkl, hai mẫu trong mau; --xuat đọc SỔ CHUNG | NHAP-JUNSKY-T<tháng>.xlsx, JUNSKY-CHI/THU-T<tháng>.xlsx; có ghi đè/xóa file đích rỗng | openpyxl, pandas |
| [15_doc_pdf_2nam.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/15_doc_pdf_2nam.py>) | 19,186 | 06/09/2026 20:26:17 | nguon/pdf_2nam/*.pdf, tùy chọn sao_ke.pkl đối chứng | SAO-KE-2-NAM.xlsx (7 sheet trong code), du_lieu/sao_ke_2nam.pkl | openpyxl, pandas, pdfplumber |
| [16_xuat_theo_thang.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/16_xuat_theo_thang.py>) | 11,862 | 06/09/2026 20:55:06 | bộ đọc PDF bước 15 | SAO-KE-THEO-THANG.xlsx, công thức kiểm soát theo tháng | openpyxl, pandas |
| [17_doi_chieu_2nam.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/17_doi_chieu_2nam.py>) | 13,865 | 06/09/2026 22:17:06 | sao_ke_2nam.pkl; nguon/so_nh_2nam.xlsx và so_nh_2nam_chi.xlsx | DOI-CHIEU-2-NAM.xlsx, doi_chieu_2nam.pkl, quy_tac_2nam.pkl | pandas |
| [18_de_xuat_loai.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/18_de_xuat_loai.py>) | 10,925 | 07/09/2026 15:36:00 | doi_chieu_2nam.pkl | DE-XUAT-LOAI-GIAO-DICH.xlsx | pandas |
| [19_hoc_kho.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/19_hoc_kho.py>) | 6,920 | 11/09/2026 20:36:59 | doi_chieu_2nam.pkl, Kho từ kho_tri_thuc.py | JSON kho/nhật ký và KHO-TRI-THUC.xlsx | kho_tri_thuc, pandas |
| [20_doc_hoa_don_xml.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/20_doc_hoa_don_xml.py>) | 12,330 | 11/09/2026 20:49:50 | XML/ZIP trong nguon/hoa_don | HOA-DON.xlsx, hoa_don.pkl, hoa_don_dong.pkl | pandas |
| [chung.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/chung.py>) | 5,136 | 04/09/2026 12:35:36 | chuỗi, bản ghi/DataFrame từ caller | giá trị chuẩn hóa, tín hiệu và khóa; không có main/I/O file | pandas |
| [quy_tac_nhom_nghiep_vu_v2.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/quy_tac_nhom_nghiep_vu_v2.py>) | 11,148 | 14/09/2026 06:58:36 | /tmp/base3.pkl ngay ở cấp module | /tmp/base9.pkl, /tmp/rules9.pkl; không import trực tiếp | pandas |
| [kho_tri_thuc.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/kho_tri_thuc.py>) | 12,672 | 11/09/2026 20:36:58 | thư mục JSON sáu bảng và meta; API Kho, không main CLI | JSON, luu_tru/vNNNN, nhat_ky.jsonl qua API ghi | stdlib |
| [ten_thuong_hieu.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ten_thuong_hieu.py>) | 6,992 | 05/09/2026 06:27:27 | danh mục/lịch sử/DataFrame từ caller | ứng viên đối tượng/TK; không main/I/O file | chung, pandas |

### Năm ứng viên được yêu cầu đọc sâu

| Script | Đánh giá tĩnh, chưa chạy |
|---|---|
| 15_doc_pdf_2nam.py | Đã đọc đầu và main 304–394, hàm đọc 202–275. Ứng viên tách parser PDF; phải cấp đường dẫn mới, thay float bằng tiền chính xác, kiểm thử hai layout và trang nối. Code hiện xuất 7 sheet nhưng workbook có 9: chưa xác nhận cùng phiên bản. |
| 17_doi_chieu_2nam.py | Đã đọc đầu và main 210–293. Tham khảo ghép ba bước; không bê ngưỡng lệch ngày/độ tin hoặc nhãn học cũ. Hai tên sổ theo đường dẫn cố định và pickle đầu vào không có trong bo_quy_tac đã cấp. |
| 14_xuat_junsky.py | Đã đọc đầu, xuat_file_nhap 422–441, main 444–475. Tham khảo tên/thứ tự cột và comments từ template; không chạy nguyên main vì ghi đè file, chưa chốt Entry2/EntryID/DebtID. Code còn tạo file nhập ở lượt dựng ban đầu trước duyệt tay. |
| kho_tri_thuc.py | Đã đọc phần đầu và API Kho 71–237. Không có main. Tham khảo chuẩn hóa/lưu vết; không mang DE_CU được dùng tự động và bộ đếm cộng dồn sang kho mới. Kho mới giữ quy trình nhãn đủ điều kiện và người duyệt. |
| 20_doc_hoa_don_xml.py | Đã đọc đầu và main 155–282. Ứng viên parser XML; hiện dùng float, có fallback suy MST phổ biến và cộng dòng chỉ theo ký hiệu+số thiếu MST/mẫu số. Phải sửa contract/khóa và kiểm thử trước dùng. |

Bộ đọc bảng kê/Base vẫn cần khảo sát riêng: không tìm thấy `doc_hd.py` trong các thư mục đã được chỉ định; `20_doc_hoa_don_xml.py` là ứng viên XML thực tìm thấy, không tự coi là cùng phiên bản với tên doc_hd.py trong kế hoạch cũ. Script phân nhóm Base đọc/ghi `/tmp/*.pkl` ngay khi import nên chưa thể dùng trực tiếp trên Windows. `bo_quy_tac` không có các pickle trung gian mà nhiều main cần.

Runtime kiểm tra: Python 3.12.14, openpyxl=3.1.5, pandas=3.0.1, xlrd=NOT_INSTALLED, pdfplumber=0.11.9, lxml=6.1.1. Chưa cài thêm dependency; pandas 3.0.1 hiện có chưa chứng minh tương thích script khảo sát cũ. `requirements.txt` cũ không khai pdfplumber dù script PDF import nó. Cần pin/thử và chuẩn bị gói offline ở V3.

## 3. Workbook thực mở được (57 đường dẫn)

Kiểm tra read-only bằng openpyxl, gồm cả workbook ở vị trí sao chép trong bo_quy_tac và DANH MỤC. Số sheet/kích thước hình học không tự xác nhận số bản ghi nghiệp vụ. Các hàng chú thích/tổng phải loại khi đếm.

| Workbook | Byte | Sửa lúc (UTC+07) | Số sheet |
|---|---:|---|---:|
| [BO-QUY-TAC.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/BO-QUY-TAC.xlsx>) | 429,074 | 04/09/2026 13:13:07 | 17 |
| [BUT-TOAN-T7.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/BUT-TOAN-T7.xlsx>) | 32,013 | 05/09/2026 06:04:30 | 7 |
| [DE-XUAT-LOAI-GIAO-DICH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/DE-XUAT-LOAI-GIAO-DICH.xlsx>) | 106,342 | 07/09/2026 15:36:00 | 4 |
| [DOI-CHIEU-2-NAM.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/DOI-CHIEU-2-NAM.xlsx>) | 540,000 | 06/09/2026 22:17:06 | 9 |
| [HOA-DON-CAY-PHAN-NHANH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/HOA-DON-CAY-PHAN-NHANH.xlsx>) | 41,625 | 17/09/2026 14:27:46 | 10 |
| [JUNSKY-CHI-T1.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T1.xlsx>) | 21,393 | 05/09/2026 14:11:23 | 2 |
| [JUNSKY-CHI-T2.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T2.xlsx>) | 16,423 | 05/09/2026 14:11:25 | 2 |
| [JUNSKY-CHI-T3.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T3.xlsx>) | 15,640 | 05/09/2026 14:11:27 | 2 |
| [JUNSKY-CHI-T4.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T4.xlsx>) | 16,916 | 05/09/2026 14:11:30 | 2 |
| [JUNSKY-CHI-T5.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T5.xlsx>) | 15,123 | 05/09/2026 14:11:31 | 2 |
| [JUNSKY-CHI-T6.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T6.xlsx>) | 17,109 | 05/09/2026 14:11:33 | 2 |
| [JUNSKY-CHI-T7.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T7.xlsx>) | 15,235 | 05/09/2026 14:11:18 | 2 |
| [JUNSKY-CHI-T8.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-CHI-T8.xlsx>) | 16,952 | 05/09/2026 14:11:35 | 2 |
| [JUNSKY-THU-T1.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T1.xlsx>) | 15,180 | 05/09/2026 14:11:23 | 2 |
| [JUNSKY-THU-T2.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T2.xlsx>) | 12,428 | 05/09/2026 14:11:25 | 2 |
| [JUNSKY-THU-T3.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T3.xlsx>) | 12,714 | 05/09/2026 14:11:27 | 2 |
| [JUNSKY-THU-T4.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T4.xlsx>) | 14,441 | 05/09/2026 14:11:29 | 2 |
| [JUNSKY-THU-T5.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T5.xlsx>) | 12,503 | 05/09/2026 14:11:31 | 2 |
| [JUNSKY-THU-T6.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T6.xlsx>) | 12,179 | 05/09/2026 14:11:33 | 2 |
| [JUNSKY-THU-T7.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T7.xlsx>) | 11,827 | 05/09/2026 14:11:18 | 2 |
| [JUNSKY-THU-T8.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/JUNSKY-THU-T8.xlsx>) | 11,823 | 05/09/2026 14:11:35 | 2 |
| [KHO-TRI-THUC.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/KHO-TRI-THUC.xlsx>) | 57,485 | 11/09/2026 20:36:59 | 6 |
| [LOAI-GIAO-DICH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/LOAI-GIAO-DICH.xlsx>) | 67,332 | 04/09/2026 22:02:57 | 5 |
| [LOC-SAO-KE-T1-T6.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/LOC-SAO-KE-T1-T6.xlsx>) | 103,049 | 04/09/2026 13:32:36 | 5 |
| [NHAP-JUNSKY-T1.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T1.xlsx>) | 88,145 | 05/09/2026 14:11:23 | 6 |
| [NHAP-JUNSKY-T2.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T2.xlsx>) | 59,283 | 05/09/2026 14:11:25 | 6 |
| [NHAP-JUNSKY-T3.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T3.xlsx>) | 63,915 | 05/09/2026 14:11:27 | 6 |
| [NHAP-JUNSKY-T4.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T4.xlsx>) | 79,052 | 05/09/2026 14:11:29 | 6 |
| [NHAP-JUNSKY-T5.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T5.xlsx>) | 59,916 | 05/09/2026 14:11:31 | 6 |
| [NHAP-JUNSKY-T6.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T6.xlsx>) | 68,043 | 05/09/2026 14:11:33 | 6 |
| [NHAP-JUNSKY-T7.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T7.xlsx>) | 48,874 | 05/09/2026 14:11:18 | 6 |
| [NHAP-JUNSKY-T8.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHAP-JUNSKY-T8.xlsx>) | 70,829 | 05/09/2026 14:11:35 | 6 |
| [NHOM-NGHIEP-VU-BASE-v2.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHOM-NGHIEP-VU-BASE-v2.xlsx>) | 120,685 | 14/09/2026 06:58:26 | 6 |
| [NHOM-NGHIEP-VU-BASE.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHOM-NGHIEP-VU-BASE.xlsx>) | 102,625 | 13/09/2026 22:52:14 | 4 |
| [SAO-KE-2-NAM.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/SAO-KE-2-NAM.xlsx>) | 751,667 | 06/09/2026 20:44:08 | 9 |
| [SAO-KE-THEO-THANG.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/SAO-KE-THEO-THANG.xlsx>) | 231,005 | 06/09/2026 20:55:06 | 19 |
| [TU-DIEN-NHOM-NGHIEP-VU.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/TU-DIEN-NHOM-NGHIEP-VU.xlsx>) | 59,770 | 14/09/2026 07:31:33 | 7 |
| [MAU-JUNSKY-PHIEU-CHI-NH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/mau/MAU-JUNSKY-PHIEU-CHI-NH.xlsx>) | 19,188 | 05/09/2026 07:04:30 | 2 |
| [MAU-JUNSKY-PHIEU-THU-NH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/mau/MAU-JUNSKY-PHIEU-THU-NH.xlsx>) | 19,188 | 05/09/2026 07:04:30 | 2 |
| [Bảng cân đối phát sinh.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Bảng cân đối phát sinh.xlsx>) | 12,910 | 04/09/2026 11:31:44 | 1 |
| [Danh mục khách hàng PLHN.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Danh mục khách hàng PLHN.xlsx>) | 398,779 | 04/09/2026 11:31:55 | 2 |
| [Danh sách chứng từ công nợ.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Danh sách chứng từ công nợ.xlsx>) | 196,555 | 04/09/2026 11:31:44 | 1 |
| [Khoản mục chi phí.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Khoản mục chi phí.xlsx>) | 8,976 | 04/09/2026 11:31:44 | 1 |
| [Mã dự án.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Mã dự án.xlsx>) | 10,442 | 04/09/2026 11:31:44 | 1 |
| [Trung tâm chi phí.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/danh_muc/Trung tâm chi phí.xlsx>) | 11,903 | 04/09/2026 11:31:44 | 1 |
| [Phiếu chi NH - UNC file mẫu junsix.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/Phiếu chi NH - UNC file mẫu junsix.xlsx>) | 19,188 | 04/09/2026 11:32:00 | 2 |
| [Phiếu thu NH - Báo có file mẫu junsix.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/Phiếu thu NH - Báo có file mẫu junsix.xlsx>) | 19,188 | 04/09/2026 11:32:00 | 2 |
| [Sổ NKC có đối ưng.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/nguon/Sổ NKC có đối ưng.xlsx>) | 399,664 | 04/09/2026 11:32:01 | 1 |
| [Bảng cân đối phát sinh.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Bảng cân đối phát sinh.xlsx>) | 12,910 | 04/09/2026 03:16:34 | 1 |
| [Danh mục khách hàng PLHN.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Danh mục khách hàng PLHN.xlsx>) | 398,779 | 04/09/2026 11:31:56 | 2 |
| [Danh sách chứng từ công nợ.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Danh sách chứng từ công nợ.xlsx>) | 196,555 | 04/09/2026 03:22:58 | 1 |
| [Khoản mục chi phí.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Khoản mục chi phí.xlsx>) | 8,976 | 04/09/2026 03:17:04 | 1 |
| [Mã dự án.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Mã dự án.xlsx>) | 10,442 | 04/09/2026 03:18:52 | 1 |
| [Trung tâm chi phí.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/DANH MỤC/Trung tâm chi phí.xlsx>) | 11,903 | 04/09/2026 03:22:10 | 1 |
| [dgbList.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/dgbList.xlsx>) | 731,228 | 11/09/2026 21:56:13 | 1 |
| [So ngan hang 9.2024-12.2025- Co 112.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/So ngan hang 9.2024-12.2025- Co 112.xlsx>) | 127,646 | 06/09/2026 22:14:19 | 1 |
| [So ngan hang 9.2024-12.2025.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/So ngan hang 9.2024-12.2025.xlsx>) | 89,203 | 06/09/2026 22:01:00 | 1 |

### Các lượng đã đếm từ nội dung

- BO-QUY-TAC: 809 quy tắc (182 DE_CU, 627 NHAP), 164 ánh xạ STK (35 CHAC_CHAN, 129 NHAP), 2.027 đối tượng, 768 dòng Tập chuẩn, 893 dòng Chứng từ · dòng. Đây là trạng thái của nguồn, chưa là quyền dùng trong sản phẩm.
- TU-DIEN: 7 sheet, 431 regex, 33 mã nhóm (có mã hậu tố A/B); không có 3B KHÓA CỨNG. Sheet NHÓM có thêm hàng ghi chú, không phải nhóm thứ 34.
- HOA-DON-CAY-PHAN-NHANH: 149 hàng nhà cung cấp, 28 mã khoản mục; loại hàng chú thích cuối sheet khỏi số đếm.
- SAO-KE-2-NAM: 9 sheet, 2.884 hàng trước khử, 2.648 sau khử, 236 nhóm trong sheet trùng; mới đọc workbook kết quả, chưa chạy lại parser PDF để xác nhận tổng.
- Mẫu Junsky có CB_tmpEntry1 17 cột (có ErrorText), CB_tmpEntry2 37 cột. File xuất T8 hiện có cùng số cột; chưa có bằng chứng nhập thành công chỉ từ tên file.
- CSV thực đếm: hoa_don.csv 1.907, dong_hang.csv 5.198, bang_ke.csv 2.716. Thư mục gốc có 1.907 XML, 67 Excel và 12 PDF. V0 chưa tái parse toàn bộ XML để đối chiếu tiền.
- Base: 2.563 JSON nằm trong 1.283 thư mục đề nghị và thêm 1 JSON cấu hình ở cấp khác; không nhầm 1.284 thư mục có JSON thành 1.284 đề nghị. Chỉ mục NHOM-NGHIEP-VU-BASE-v2 có 1.115 dòng. Chênh số lượng 168, chưa kết luận danh sách ID thiếu/dư cho đến V3.

## 4. Phần có thể tận dụng và phần phải chờ

Có thể dùng ngay làm bằng chứng thiết kế: cấu trúc file, template có chú thích, 13 JSON cùng runner đã cấp và workbook tri thức để lập danh sách chờ duyệt. Chỉ runner tái hiện đã chạy trên sản phẩm hiện có; việc đó không kiểm chứng các parser khảo sát.

Tái dùng có điều kiện: parser PDF/XML, kỹ thuật dựng template Junsky, chuẩn hóa và thuật toán ghép. Phải tách đọc/ghi, tham số hóa đường dẫn, giữ tiền/ID, bổ sung contract/known_at và smoke test trên bản sao. Chưa có script nào được chứng nhận giữ nguyên để đưa vào runtime.

Cần Anh/kế toán xác nhận metadata nguồn, quyền duyệt, chuẩn Entry2/EntryID/DebtID/EntryDM, bằng chứng nhập và tiêu chí pilot; không cần xin lại các file đã tìm thấy. Bốn tài liệu gốc và thư mục chạy thử nguyên bản được bảo vệ bằng SHA-256; nguồn ngoài dự án chỉ đọc, không tuyên bố đã kiểm hash toàn bộ hơn 4 GB Base.
