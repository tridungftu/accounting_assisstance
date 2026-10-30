**BIÊN BẢN REVIEW CHÉO 5 ENGINE — 30/10/2026**

**Kết luận: Cần sửa.** Cả 5 engine đúng định hướng dùng lại nguồn; chưa thấy yêu cầu viết lại nghiệp vụ/thuật toán. Còn **1 điểm Chặn, 3 điểm Cần sửa** trước khi giao triển khai.

Review tĩnh, chỉ đọc; không sửa tệp, chạy test/dịch vụ, gọi mạng hoặc mở dữ liệu/bí mật thuộc phạm vi cấm.

Quy ước đường dẫn:

- `E1`, `E2`: `docs\47-core\engine\GIAO-ENGINE-1.md`, `GIAO-ENGINE-2.md`.
- `O`: `D:\GPT\OCR`; `M`: `D:\GPT\Phan mem Mask file\Mask file v2`.
- `X`: `D:\Claude\Ho tro review ho so xay dung\review_xaydung`.
- `H`: `D:\Claude\Phan mem download hoa don`.
- `A`: `src\kho_tri_thuc\tri_thuc\cong_ai.py`; `P`: `src\kho_tri_thuc\nguon\hoa_don_xml.py`.
- `CD`, `SDK`, `CT`: lần lượt là `CHI-DAO-TU-ANH.md`, `DAC-TA-SDK.md`, `CONTRACT-DU-LIEU.md` trong các thư mục căn cứ Anh giao.

**Bảng dùng lại đã mở kiểm trực tiếp**

| # | Phần | Phân loại | Nguồn có thật và nội dung xác nhận |
|---|---|---|---|
| 1 | Tích hợp ABBYY | Dùng lại nguyên | `O\ocr-abbyy-ai\ocr_web\app.py:25`, `:277` — import bridge, nhận DOCX. |
| 2 | Bridge Hot Folder | Dùng lại nguyên | `O\abbyy-hotfolder\abbyy_hotfolder\client.py:113` — `convert`, hỗ trợ hủy. |
| 3 | Bảng/DOCX | Bọc | `O\mask_ocr\layout.py:28`, `:149` — bảng PDF, cấu trúc Word. |
| 4 | Pipeline OCR khác | Bọc, cần giới hạn | `O\mask_ocr\structured.py:244`, `:269` — nhánh Tesseract/Paddle; không phải ABBYY. |
| 5 | Gợi ý định danh | Dùng lại nguyên | `M\privacy\core.py:79` — `suggest`. |
| 6 | Che và kiểm | Dùng lại nguyên | `M\privacy\core.py:308`, `:325` — `replace`, `verify`. |
| 7 | Che/mở văn bản | Dùng lại nguyên | `M\privacy\auto_api.py:291`, `:362` — `mask_text`, `unmask_text`. |
| 8 | Mapping lượt | Dùng lại nguyên | `M\privacy\auto_api.py:172` — `TurnStore`, RAM, TTL/giới hạn lượt. |
| 9 | API/xuất tài liệu | Bọc | `M\privacy\server.py:1561`, `:1600`, `:982` — che/mở; xuất tài liệu phụ thuộc session, revision và duyệt. |
| 10 | Danh mục tham số | Dùng lại nguyên | `X\trich_xuat\danh_muc.py:149`, `:186` — đọc danh mục, nạp tham số. |
| 11 | Lõi trích xuất | Bọc | `X\trich_xuat\quy_trinh.py:91`, `:92`, `:272` — lớp trích, seam AI, xử lý hợp đồng. |
| 12 | Đọc hợp đồng | Dùng lại có giới hạn | `X\trich_xuat\doc_hop_dong.py:296`, `:453` — đọc DOCX/hợp đồng; phải chặn nhánh Word COM. |
| 13 | DTO AI | Dùng lại nguyên | `A:275`, `:296`, `:305` — yêu cầu, trường, kết quả. |
| 14 | Điều phối AI | Bọc | `A:988`, `:1149`, `:1236` — seam tiêm, kiểm Cloud, Local trước. |
| 15 | Job tải hóa đơn | Bọc | `H\src\job.js:75`, `:96` — khởi động/chạy job. |
| 16 | Phiên và tải thuế | Bọc, cần xử lý vận hành | `H\src\portal.js:27`, `:223`, `:251` — đăng nhập, lấy danh sách, xuất XML. |
| 17 | Bảng kê | Dùng lại nguyên | `H\src\build.js:18` — xuất Excel. |
| 18 | Parser XML/ZIP | Dùng lại nguyên, bọc contract | `P:618`, `:1183`, `:1191` — JSON exact decimal, đọc XML/ZIP. |
| — | Sửa bản gốc | Không giao sửa | `CD:429`; riêng Mask theo `M\CLAUDE.md:45`, `:51`; X tiếp tục đóng băng. |
| — | Viết mới | Chỉ adapter, khung chạy, vận hành Core | `CD:430`; `SDK:83`, `:90`, `:110`. Phải tái dùng cả nền bắt tay/Windows Job đã có. |

**Phát hiện và yêu cầu sửa**

| Phát hiện | Mức | Căn cứ và yêu cầu |
|---|---|---|
| Bộ tải dùng **browser profile bền, cố định trong thư mục nguồn**, chưa có ranh giới phiên theo pháp nhân và vòng đời bí mật. | **Chặn** | `E2:120`, `:125`; `H\src\portal.js:28`–`:29` dùng `.browser-profile` và `launchPersistentContext`. **Suy luận từ cơ chế:** có nguy cơ lưu/tái dùng phiên xác thực. Phải quy định profile, quyền truy cập, vòng đời credential và test không dùng chéo pháp nhân; không mở profile thật để kiểm. `CD:414`; `SDK:83`, `:122`. |
| Đường OCR chưa phân định rõ lõi ABBYY với pipeline dual; chưa đưa rủi ro hai sổ hạn mức vào nghiệm thu. | **Cần sửa** | `E1:22` dẫn `structured.py:244`, trong khi `CD:409` chọn ABBYY. Chỉ rõ đường ABBYY → DOCX → adapter; backend khác phải khai riêng. Bổ sung kiểm một chủ điều phối Hot Folder/hạn mức: `KS-E.md:66`, `:146`; `src\kho_tri_thuc\ha_tang\cong_ocr.py:8`. |
| `trich.bang@1` thiếu nguồn cụ thể bảo toàn cấu trúc bảng. | **Cần sửa** | `E2:27`, `:37`–`:41`. Bộ đọc được dẫn tại `X\trich_xuat\doc_hop_dong.py:341`–`:343` bỏ ô rỗng, ghép thành chuỗi; không đủ làm bằng chứng giữ cột/ô gộp/vị trí. Gắn nguồn đọc bảng thực có và test tương ứng, hoặc giữ capability ở trạng thái chưa hỗ trợ. Không viết lại thuật toán để lấp chỗ thiếu. |
| Test gốc hóa đơn chưa chứng minh luồng tải qua engine. | **Cần sửa** | `E2:153`; `H\test\test.js:4`, `:19`, `:24`, `:33` chỉ kiểm `build`/parse/PDF, không kiểm `job`/`portal`. Giữ test gốc và bổ sung ca giả qua engine cho tải, đăng nhập chờ, lỗi nhóm truy vấn, bàn giao và chống trùng; `CD:431`. |

Các ràng buộc còn lại được ghi đúng: chờ SDK/CD mở lại; không sửa nguồn khi chưa hỏi Anh; X đóng băng; Mask theo `CLAUDE.md`; Cloud qua `e_mask`; không che tiền/ngày; tài khoản hạn chế khác Core; ngoại lệ ABBYY hỏi Anh; lát ≤3 tệp gồm test và whitelist trước giao. Khi nghiệm thu tài khoản, phải dùng ca âm từ chính tiến trình engine theo `SDK:124`–`:126`.

**Tỉ lệ đúng:** 18/18 dòng nguồn đối chiếu trong bảng có thật (**100%**); 5/5 engine giới hạn phần viết mới đúng CD-036 (**100%**). Đây là tỷ lệ kiểm tài liệu/nguồn, **không phải tỷ lệ test hoặc nghiệm thu vận hành**; lượt này không chạy test.

**Kết luận cuối: Cần sửa bản giao việc theo bốn phát hiện trên trước khi giao code.**