# Review hồ sơ thanh toán khối lượng xây dựng

Phần mềm hỗ trợ review hồ sơ thanh toán khối lượng xây dựng theo cách của auditor: đi từ số đề nghị thanh toán ngược về
dữ liệu gốc (hợp đồng, BOQ, phụ lục, đợt trước, biên bản nghiệm thu). Phương pháp đầy đủ:
[`quy-trinh-review-ttkl.md`](quy-trinh-review-ttkl.md).

## Mở phần mềm

Nhấp đúp **`CHAY_PHAN_MEM.bat`** → trình duyệt mở `http://localhost:8600` — giao diện **"Bàn kiểm soát"**
(thiết kế Claude Design, chạy trên dữ liệu thật). Giữ cửa sổ đen mở trong lúc dùng. Các màn hình:

| Màn hình | Làm gì |
|---|---|
| Tổng quan | Việc gần đây, việc đang chạy, "Cần Anh xem xét" (phát hiện mức cao, cờ đỏ phụ lục, tham số chưa xác nhận) |
| Trích tham số | Thả Word/PDF → 9 bước Local AI → bảng 37 tham số có trích dẫn → sửa / xác nhận → Nạp CSDL (kèm nguồn gốc từng giá trị) |
| Danh mục hợp đồng | Tham số hiệu lực theo ngày, phụ lục, BOQ, đợt, cảnh báo; mở "Nguồn" từng tham số để xem trích dẫn, model, file, lịch sử và xác nhận |
| Phụ lục | Nạp file phụ lục Word / PDF (nhiều file) → quy tắc + Local AI trích thay đổi → duyệt, xác nhận → kiểm tra P01–P18 → nạp; cách cũ: phiếu Excel; huỷ kèm lý do |
| BOQ | BOQ hiệu lực tại ngày; Import BOQ gốc: chọn sheet, ánh xạ cột (kể cả cột "Mã HM" phòng Dự án đặt, nếu có), Σ round(KL×ĐG)×(1+VAT) so giá trị HĐ → ghi; nạp cả loạt nhiều file: tự nhận hợp đồng theo số HĐ trong file / tên file, bảng số liệu ĐẠT/LỆCH để xác nhận, chỉ ĐẠT được chọn sẵn; nhận cả BOQ Word / PDF scan (OCR) |
| File Excel 97-2003 (.xls) | Mọi chỗ nạp Excel (kiểm tra đợt, toàn vẹn, Import BOQ, phiếu phụ lục, chứng từ) nhận cả `.xls`: máy tự chuyển sang `.xlsx` bằng **Microsoft Excel** trên máy (giữ công thức, liên kết, sheet ẩn; tắt macro, không cập nhật liên kết), không có Excel thì **LibreOffice**; file gốc `.xls` giữ cạnh file chuyển. Không có cả hai: Import BOQ / phiếu / chứng từ vẫn đọc giá trị bằng thư viện `xlrd`; kiểm tra đợt / toàn vẹn thì báo lỗi (cần công thức gốc) và hướng dẫn Save As `.xlsx` |
| Kiểm tra đợt | Hai lớp: toàn vẹn Excel (K1–K8) + đối chiếu HĐ/PL/BOQ tại ngày nghiệm thu (B1–B6), hằng số gõ cứng và khấu trừ so tham số HĐ (B7–B8); bảng các bước Lớp 2 hiện cả bước đạt (GT HĐ so với giá trị thực hiện / thanh toán, tỷ lệ thanh toán TT-20, giữ lại TT-21, đơn giá và KL từng hạng mục BOQ so với hồ sơ); bằng chứng từng ô, cây truy vết số đề nghị; ghép hạng mục khi thiết bị cùng tên lặp ở nhiều bể (theo nhóm, thứ tự dòng, đơn giá + KL, mã HM), dòng chưa chắc → **Ghép tay** trên bảng từng hạng mục rồi Chạy lại (máy nhớ cho các đợt sau); nạp đợt đã duyệt |
| Kiểm tra đợt · chế độ "Chỉ toàn vẹn file" | Cùng mục Kiểm tra đợt trên menu, chọn khi hợp đồng **chưa có trong CSDL**: chỉ Lớp 1 (K1–K8, truy vết số đề nghị); không đối chiếu HĐ / BOQ, không nạp đợt |
| Chứng từ | Lớp 3: BB nghiệm thu KL, BB giao nhận, packing list, CO, CQ, BB lắp đặt / chạy thử (PDF scan tự OCR) → ghép với hạng mục, đối chiếu số lượng với KL kỳ này / lũy kế, chéo giữa chứng từ (model, số lô), ngày tháng (C01–C09); ma trận hạng mục × chứng từ |
| Cài đặt | Máy AI LAN, kiểm tra chéo Claude (mặc định tắt), API key, sao lưu / xuất CSDL |

API cho giao diện: [`API.md`](API.md). Font Be Vietnam Pro trong `giao_dien/fonts/` (giấy phép OFL, xem `OFL.txt`).

## Thành phần

| Thư mục / file | Dùng để |
|---|---|
| `trich_xuat/` | **Trích 37 tham số hợp đồng bằng Local AI** theo phương pháp v3: Accept All Track Changes trên bản sao → tách Điều/Khoản → dò vị trí theo từ khoá (AI tìm qua mục lục nếu không khớp) → hỏi AI theo nhóm ≤ 8 tham số chỉ với các Khoản liên quan → Python tự kiểm trích dẫn nguyên văn và số liệu → rà lại toàn HĐ cho ô vàng → kiểm tra logic L1–L5 → (tuỳ chọn) kiểm tra chéo cloud đã che thông tin định danh → Excel/JSON, TONG_HOP, `DANH_MUC_HOP_DONG.xlsx`. Danh mục tham số: `trich_xuat/DANH_MUC_THAM_SO.xlsx` (mức quan trọng 0–3, từ khoá L4) |
| `trich_xuat/ai_cloud.py` | Nguồn AI dự phòng: Claude qua API thay máy Local AI khi máy AI không bật (chọn trong Cài đặt → Nguồn AI). Cùng giao diện với Local AI; che định danh trước khi gửi (câu còn sót định danh thì không gửi), mở che kết quả trên máy, ghi `GUI_RA_NGOAI_*.txt`. Trích HĐ: thông tin chung đọc bằng quy tắc, không gửi Phần mở đầu, không rà lại toàn HĐ |
| `trich_xuat/ocr_abbyy.py` | OCR PDF scan bằng ABBYY FineReader Hot Folder trên máy: phần mềm có thư mục `ocr\in` / `ocr\out` riêng (không lên Git) cho một task Hot Folder; hợp đồng / phụ lục PDF scan → DOCX → đọc như Word; BOQ PDF → bảng → Excel. Kết quả lưu đệm theo SHA-1 trong `ket_qua_AI\ocr_abbyy\`. Task ABBYY phải: lưu **Microsoft Word (.docx)** vào `ocr\out`, **mỗi file một tài liệu riêng** (tên giống file nguồn), nhận dạng bảng (mặc định), ngôn ngữ Tiếng Việt + Tiếng Anh. Bảng KL / đơn giá trong Word của ABBYY được đọc lại thành dòng BOQ (tiêu đề cột chịu lỗi OCR như "Nội duug", "Đơn qia") |
| `may_chu/phu_luc_ai.py` | Trích nội dung thay đổi từ file phụ lục Word / PDF: quy tắc (HĐ, số PL, ngày, bảng KL/đơn giá, THAY/THEM/BO) + Local AI (tham số bị sửa, thay đổi khác) → kiểm tra P01–P18 → anh duyệt → nạp CSDL |
| `may_chu/chung_tu.py` | Lớp 3: đọc và đối chiếu chứng từ của đợt (C01–C09) |
| `may_chu/` | Máy chủ web cục bộ + API JSON + việc chạy nền (tiến độ, nhật ký, Dừng); `nghiep_vu.py`: import BOQ, kiểm tra đợt hai lớp, toàn vẹn |
| `giao_dien/` | Giao diện "Bàn kiểm soát": `index.html`, `app.js` (khung, Tổng quan, Cài đặt), `extraction.js`, `contracts.js` (danh mục, phụ lục, BOQ), `checks.js` (kiểm tra đợt, toàn vẹn), `chung_tu.js` (chứng từ), `phu_luc_ai.js` (phụ lục Word / PDF), `api.js`, `ui.js`, `styles.css` |
| `chay.py`, `CHAY_PHAN_MEM.bat` | Mở phần mềm |
| `csdl_hop_dong.py` | CSDL SQLite hợp đồng – phụ lục – BOQ – đợt thanh toán (giao diện gọi qua API; vẫn chạy được bằng dòng lệnh) |
| `toan_ven.py` | Lớp 1: tính toàn vẹn file Excel hồ sơ thanh toán (K1–K8) |
| `master_hd.py`, `hardcode_audit.py` | Trích tham số bằng quy tắc / phân rã công thức (công cụ phụ) |
| `tests/` | `python -m unittest discover -s tests -v` — kiểm thử không cần GPU (AI và cloud giả lập, hợp đồng giả lập) |

Dòng lệnh dự phòng: `python -m trich_xuat <file hoặc thư mục> [--model gpt-oss:20b] [--may-ai 192.168.5.67]`.

## Cài đặt

Python 3.9+ và `pip install openpyxl` (bat tự cài nếu thiếu). File `.doc` và hợp đồng còn Track Changes dùng
Microsoft Word có sẵn trên máy để chuyển/Accept All trên bản sao (không có Word thì Python tự xử lý `.docx`).
Địa chỉ máy AI, model, cloud: trang **Cài đặt** (lưu ở `cau_hinh_may_ai.json`). API key cloud lưu ở
`%USERPROFILE%\.trich_xuat_hd\khoa_api.json` (hoặc biến môi trường `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`), không bao giờ
nằm trong thư mục dự án.

## Dữ liệu

Kho này **chỉ chứa mã nguồn và tài liệu chung**. `.gitignore` liệt kê đích danh file được phép đẩy lên (whitelist), nên
hợp đồng, hồ sơ, master, CSDL (`co_so_du_lieu/`), kết quả (`ket_qua_AI/`), `cau_hinh_may_ai.json`, `File mẫu/`,
`tai_lieu_noi_bo/`, `du_lieu_mau/` không bao giờ lên kho.
