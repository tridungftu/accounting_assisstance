# CLAUDE.md — Phần mềm hỗ trợ kế toán & Kho tri thức

Đọc trước: `D:\Claude\CACH-LAM-VIEC-CHUNG.md` (quy tắc chung, khi bản đó có hiệu lực), rồi file này (phần riêng). Quy ước chi tiết với anh Dũng ở Project claude.ai "phần mềm Hỗ trợ kế toán", tài liệu `claude/00`.
Mã nguồn nằm trong thư mục con `Phần mềm kho tri thức\` (repo git riêng tư `tridungftu/accounting_assisstance`). File này áp dụng cho cả thư mục cha lẫn thư mục con.

## Mục tiêu và phạm vi
- Biến chứng từ (sao kê ngân hàng, hóa đơn điện tử XML, đề nghị thanh toán Base, nghiệm thu xây dựng, bảng lương, hợp đồng vay…) thành **bút toán đề xuất**; kế toán duyệt; xuất **file Excel nạp vào Junsky ERP** (hai sheet `CB_tmpEntry1/2`).
- KHÔNG thay Junsky (sổ cái, BCTC, tờ khai chính thức ở Junsky). KHÔNG hạch toán hộ phòng ban khác. KHÔNG làm giá thành sản xuất, kho sản xuất, hợp nhất (anh bỏ 15/10/2026).
- Không xây lại nghiệp vụ mà dự án khác đang làm: nhận kết quả của **Review hồ sơ thanh toán xây dựng** (M4), **Theo dõi khoản vay** (M9, đọc Google Sheets API), **Tải hóa đơn điện tử** (M2/M3/M8), **Backup Base** (M2) dưới dạng file/API có cấu trúc.

## Trạng thái hiện tại
- Kho tri thức **V13 · 0.6.0** (18/10/2026, chờ anh bấm thử): xương sống K2 trên PostgreSQL (4 schema), lớp kết nối hai engine `[storage]` — **kho thật vẫn SQLite**; kho thử T8 PostgreSQL ở `var\plhn-thu-T8-postgres` (schema `v12_thu_t8`). Go-live sao kê một tài khoản (TK 112111). Hóa đơn XML: đề xuất theo tháng, chấm riêng mua vào/bán ra.
- Kiến trúc đa phòng ban (TL 40): phần mềm anh giữ mã nối CSDL qua schema `giao_tiep`; phần mềm khác không nối CSDL (nguyên tắc 11).
- **Mức 2 (file nhập Junsky) còn khóa** ở cả màn hình và máy chủ; mở sau khi nhập thử 1 → 5 chứng từ và chốt 3 câu với nhà cung cấp Junsky.
- Số đo mới nhất: xem `Phần mềm kho tri thức\CHANGELOG.md`.

## Nền tảng và lệnh
- Python ≥ 3.11 (chạy được 3.13), SQLite (`var\...\kho.sqlite`, schema có số phiên bản), phụ thuộc duy nhất `openpyxl` (+ `xlrd` tùy chọn cho `.xls`). Giao diện HTML cục bộ chỉ nghe `127.0.0.1` (cổng 8766 thật / 8767 thử). Không gọi API AI bên ngoài; LLM cục bộ chỉ ở tầng 4 của phễu.
- Mở phần mềm: nhấp đúp `Phần mềm kho tri thức\MỞ PHẦN MỀM.cmd` (kho thật) hoặc `MỞ PHẦN MỀM THỬ T8.cmd` (kho thử, học đến 30/06/2026).
- Chạy test (khối lệnh dán là chạy):
  ```powershell
  Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
  .\test.ps1
  ```
- Thêm thư viện ngoài: nêu lý do, hỏi anh một lần, ghi vào `pyproject.toml`.

## Quy tắc riêng của dự án
- Anh Dũng là người dùng cuối: **không bắt anh gõ lệnh**; **Claude Code lập trình và tự chạy thử** (anh đổi 18/10/2026, trước là Codex); bàn giao ở trạng thái bấm nút.
- Máy chỉ **đề xuất**; bút toán chỉ xuất khi đã "Đồng ý". Tự duyệt chỉ cho 4 loại anh chốt (phí ngân hàng, lãi tiền gửi, lương, bút toán định kỳ), chỉ khi mức 2 đã mở, qua đủ kiểm tra bước 4 và có nhật ký.
- **Thà bỏ sót còn hơn nhập sai**: dòng thiếu TK chi tiết hoặc thiếu mã đối tượng không được vào file nhập; không sửa tay file nhập Junsky.
- Dữ liệu thật chỉ trong `var\` (bị `.gitignore`); `tests\fixtures` dùng dữ liệu giả có chữ DEMO; chat, prompt, báo cáo chỉ nêu số đếm và số kiểm soát tổng, không in dòng giao dịch, số tài khoản, tên đối tác.
- Chấm điểm: học đến **30/06/2026**, chấm trên T7–T8 so với Sổ NKC; loại tri thức có `lan_dau ≥ 2026-08-01`. Báo cáo mỗi V phải có số trước/sau.
- Tri thức CFO ghi vào `TRI-THUC-CFO.json`, duyệt dưới actor `CFO_NTD`; actor shadow có tiền tố `MO_PHONG_`.
- Thư mục `var\sao-luu-truoc-Vxx\` là bản sao lưu: chỉ đọc. Trước khi thay mã trên máy anh: sao lưu, chép, kiểm hash.
- Thứ tự làm một module mới (tiêu chuẩn nội bộ): chốt yêu cầu → phản biện trường dữ liệu → **chốt màn hình rồi chốt schema** → ghi vào hàng đợi → chỉ code khi anh ra lệnh → test đi kèm → review độc lập cuối V → CHANGELOG + báo cáo.
- Khuyến nghị model: phễu, quy tắc định khoản, schema, review độc lập → mô hình mạnh nhất; giao diện, bộ đọc file, adapter (Zalo Bot, Sheets) → lớp Sonnet (Claude Code); script nhỏ → lớp Haiku; phân tích trả lời Zalo → LLM cục bộ.

## Tài liệu tham chiếu
- Project claude.ai: `01` bản đồ module · `08` file nhập Junsky · `23` phễu 6 bước · `28` sơ đồ phần hành · `29` kế hoạch 10 module · `30` khảo sát đầu vào · `31` tận dụng dự án hiện có.
- Trong thư mục con: `README.md`, `docs/QUYET-DINH.md` (nhật ký quyết định), `docs/BAO-CAO-Vxx.md`, `docs/HUONG-DAN-DINH-KHOAN.md`, `CHANGELOG.md`, `HANG-DOI-YEU-CAU.md`.
- Mẫu Junsky gốc của nhà cung cấp: không sửa.

## Điểm đang chờ anh Dũng chốt
- Hai câu bước 2 của phễu (tài liệu 23): đối tác hai vai trò; tiền khách về không khớp công nợ.
- Ba câu với nhà cung cấp Junsky + danh mục `BankID`, `CashflowID`, mẫu xuất sổ (tài liệu 08).
- Danh mục loại chi phí dùng chung với dự án "Phần mềm kiểm tra đề xuất Base" (ai là chủ, đã đặt tên chưa).
- Kết quả khảo sát đầu vào (tài liệu 30) để xếp thứ tự M5, M7, M8, M10.
