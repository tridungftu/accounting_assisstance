# Review Opus — bảng "dùng lại nguyên / bọc / sửa / viết mới" của 5 engine (CD-036), 30/10/2026

**Kết luận: chưa giao code — 3 Chặn** (1 trùng RV-ENGINE, thêm căn cứ; 2 mới) và **6 Cần sửa**.
- **Đúng hướng** ở cả 5 engine: ưu tiên bọc, viết mới chỉ adapter / khung chạy.
- **Chỗ sai:**
  - vài dòng xếp "dùng lại nguyên/bọc" thực ra phải đổi cách chạy nguồn;
  - "không giữ mật khẩu/khóa" không làm được với 3 engine.

E1 = `GIAO-ENGINE-1.md`, E2 = `GIAO-ENGINE-2.md`, RV = `RV-ENGINE.md`.

| Engine | Kết luận | Mục |
|---|---|---|
| `e_ocr` | **Chặn** | 2 |
| `e_mask` | Cần sửa | 4, 6 |
| `e_hoi_ai` | Cần sửa | 4, 7 |
| `e_trich_xuat` | **Chặn** | 3, 5, 8 |
| `e_hoa_don` | **Chặn** | 1, 9 |

## Chặn

1. **e_hoa_don** (gộp Chặn RV): phần tải không chạy được dưới tài khoản hạn chế headless.
   - `H\src\portal.js:29-30` dùng `launchPersistentContext` với `headless: false`: người dùng gõ CAPTCHA trên cửa sổ Chromium ở máy chủ, không có đường chuyển CAPTCHA về Core.
   - Engine nhận `TAX_PASSWORD` (`job.js` `opts.env`).
   - Vì vậy "dùng lại nguyên portal.js" và `waiting_input` mâu thuẫn với SDK §4.1 (headless) và §4.4.
   - **Sửa:** "Capability `hoa_don.tai_cong_thue@1` ở trạng thái CHỜ cho tới khi Anh chọn cách chạy phiên đăng nhập (Câu 2). Profile trình duyệt riêng theo pháp nhân trong kho tệp có ACL, xóa sau phiên. Mật khẩu chỉ nhận qua stdin/handle từ két Core."
2. **e_ocr**: "Dùng lại nguyên `app.py:25/:277`, giữ xử lý `:315`" là sai.
   - `O\ocr-abbyy-ai\ocr_web\app.py:27-29` import `hieu_dinh` (`D:\GPT\OCR\hieu-dinh-ocr`, ngoài 4 nguồn chính thức).
   - `:315` là `Corrector(...)` hiệu đính. `JobManager` luôn chạy hiệu đính, gọi thẳng `OllamaClient` (vượt cổng AI, trái TL 48) và ghi `ocr-abbyy-ai\ket-qua`.
   - Test gốc `ocr-abbyy-ai\tests\test_app.py:77` kiểm tệp `hieu_dinh`/`bao_cao`, nên muốn qua test thì buộc phải chạy hiệu đính.
   - **Sửa:** "Dùng lại nguyên chỉ `HotFolderClient.convert` (`O\abbyy-hotfolder\abbyy_hotfolder\client.py:113`) với `Config` do adapter dựng; không gọi `load_config` (thứ tự nạp `config.py:28` lấy `config.json` thật trong thư mục nguồn). `app.py` chỉ tham khảo, không chạy. `test_app.py` ngoài phạm vi engine; test gốc của engine là `abbyy-hotfolder\tests` và `O\tests\test_structured_docx.py`."
3. **e_trich_xuat**: "Bọc seam AI chuyển qua cổng AI" không làm được nếu không sửa nguồn.
   - X gọi Ollama `/api/chat` với `format: schema`, `num_ctx`, `think` và chặn khi câu hỏi bị cắt (`X\trich_xuat\ai_local.py:104-160`).
   - Cổng AI chỉ nói `/v1/chat/completions` kiểu OpenAI, không schema (`src\kho_tri_thuc\tri_thuc\ai_cuc_bo.py:213-241`). `CongAI.goi` còn ép prompt/định dạng riêng.
   - Test gốc `X\tests\test_trich_xuat.py:304,313` dùng `mock_ollama` `/api/chat`.
   - **Cần Anh chọn** (Câu 1).

## Cần sửa

4. **e_mask, e_hoi_ai — bí mật.**
   - Hiện trạng:
     - Mask giữ mật khẩu danh mục trong RAM (`M\privacy\server.py:236-238`);
     - khóa API ở `config\mask-api.key`, icacls cho tài khoản chạy Mask (`M\run_privacy.py`, `auto_api.py:43,118`);
     - `e_hoi_ai` đọc khóa Cloud từ biến môi trường (`cong_ai.py:1174`, SDK §4.1 cấm) và khóa Mask từ tệp (`:606`).
   - **Sửa:** "Engine chỉ giữ bí mật trong RAM, nhận qua stdin/handle từ két Core. `e_hoi_ai` tiêm qua seam `moi_truong` (`:988`) và đối tượng `mask`; không sửa nguồn. Không ghi đĩa, không log."
   - Dùng chung `ktt_module` thì module đọc được khóa Mask → đề xuất engine giữ bí mật có tài khoản riêng (Câu 3).
5. **e_trich_xuat — hai nhánh trái ràng buộc vẫn tự chạy.**
   - DOCX có Track Changes trên Windows tự gọi Word COM (`X\trich_xuat\doc_hop_dong.py:63,468-470`).
   - PDF chạy ABBYY riêng của X (`quy_trinh.py:292-293` → `ocr_abbyy.py`) = engine OCR thứ hai, sổ hạn mức thứ hai.
   - **Sửa:** "Adapter chỉ nhận DOCX (PDF phải qua `e_ocr`). Chặn `_word` bằng lớp bọc có test → nguồn rơi về nhánh Python chấp nhận sửa đổi trong XML (`:69-70`). `TrichXuat(cloud=None)`, `ai.la_cloud=False`. `out_dir` thư mục tạm theo việc, xóa sau khi bàn giao."
6. **e_mask:** "Dùng lại nguyên `auto_api.mask_text`" dễ dẫn tới viết lại logic an ninh.
   - Danh mục, mật khẩu, chờ duyệt, `TurnStore` nằm trong closure `create_app` (`server.py:1543-1598`); `mask_text` trả cả `mapping` (`auto_api.py:291`).
   - **Sửa:** "Bọc = chạy nguyên `run_privacy.py --port`, chỉ gọi HTTP `/api/v1/trang-thai`, `/che`, `/mo-che`. Adapter không import `mask_text`/`unmask_text`."
   - Mở khóa danh mục chỉ qua giao diện tại `127.0.0.1` (TrustedHost, Origin `server.py:240,263`). Core chuyển tiếp sẽ bị chặn; nới chặn trái quy tắc 3 trong `M\CLAUDE.md` (Câu 3).
7. **e_hoi_ai — thống kê bị mất.**
   - Engine không login CSDL nên loại `BoGhiPostgres`.
   - `BoGhiBoNho` mất thống kê mỗi lần tự dừng → tỷ lệ kiểm xác suất / độ chính xác Local về mặc định (`cong_ai.py:1002-1045`).
   - **Sửa:**
     - viết mới `BoGhiNhatKy` ghi qua bàn giao Core, đọc `thong_ke` qua Core;
     - cờ chỉ Local = instance theo request `cloud_bat=False` (`:1149`), không sửa nguồn;
     - thêm vào bảng "dùng lại nguyên": `ai_cuc_bo.ask_local` (`:243`), `MaskV2` (`:623`), `NhaCungCapAnthropic/OpenAI` (`:724`, `:761`).
8. **e_trich_xuat — xếp loại E1-MUA.** `tools\source6_g5_e5\trich_xuat\danh_muc.py` là bản chép đã vá của X (import tương đối `.cau_hinh`, dòng 25); danh mục MUA đặt cạnh `DANH_MUC_THAM_SO.xlsx` của X (`:291-305`).
   - Đây là "sửa / chép có vá", không phải "dùng lại".
   - **Sửa:** đổi nhãn, ghi SHA nguồn, giữ chờ Anh; gộp Cần sửa `trich.bang@1` của RV.
9. **e_hoa_don — contract/test** (gộp RV mục 4).
   - Đầu vào `tu_ngay/den_ngay` không khớp `job.js:55` (chỉ theo tháng/năm) → adapter chỉ nhận trọn tháng.
   - Nhóm truy vấn lỗi bị bỏ qua mà không báo (`portal.js:223-244`) → đánh dấu PARTIAL.
   - Nêu rõ Node là tiến trình con, đi theo đường `--port` có khoảng hở.
   - Tách lát 2 thành 2a tải giả lập (stub `portal`) và 2b bảng kê.

## Để sau / nên làm

- **e_ocr:** ghi vào bảng rằng repo đã có `src\kho_tri_thuc\ha_tang\cong_ocr.py` (OCR-1, cổng ABBYY dùng chung, đang dùng ở `m9\ocr_hot_folder.py`, `engine_cong.py`): một chủ điều phối, một sổ hạn mức (gộp RV mục 2).
- **e_ocr:** DOCX → bảng dùng `extract_docx` + `layout.word_layout(..., embedded_pages=[])`, không qua `structured._docx_result` (OCR ảnh nhúng bằng Tesseract/Paddle, `structured.py:349-352`).
- **e_ocr:** engine chết giữa `wait()` và lúc Core xác nhận thì mất kết quả mà hạn mức đã trừ (`client.py` xóa tệp sau khi đọc); không tự gửi lại.
- **Chung:** ghi thứ tự phụ thuộc e_mask → e_hoi_ai → e_trich_xuat.
- **e_mask:** cả 4 schema đang "chờ Anh", chỉ làm được lát 1. Lead soạn schema ánh xạ đúng trường MASK-1/2 để Anh duyệt.

Ý 3, 5 (bàn giao trước khi giải phóng RAM; "xong" ≠ "đã duyệt") ghi đúng ở cả 5 bản. Không che tiền/ngày; không gọi cổng thuế thật.

## Câu hỏi Anh trước khi mở lập trình

1. **AI của trích xuất hợp đồng:**
   - (A) mở rộng cổng AI thêm đường "Local có khuôn trả lời" — chỉ Local, giữ kiểm địa chỉ LAN/Tailscale (sửa `ai_cuc_bo`/`e_hoi_ai`). *Khuyến nghị.*
   - (B) trích xuất gọi thẳng máy AI như bản review cũ (ngoại lệ TL 48).
   - (C) đổi câu hỏi của bản review sang mẫu của cổng AI (đổi thuật toán, sửa test gốc).
2. **Tải hóa đơn cần người gõ CAPTCHA:**
   - (A) phần tải chạy trong một phiên Windows riêng có màn hình (ngoại lệ như ABBYY), mỗi pháp nhân một hồ sơ trình duyệt, xóa sau phiên. *Khuyến nghị.*
   - (B) sửa bộ tải sang chạy ẩn, chuyển ảnh CAPTCHA qua Core (sửa bản gốc).
   - (C) tạm chỉ làm phần đọc XML/ZIP.
3. **Mask và bí mật của engine:**
   - (A) Anh mở khóa danh mục Mask ngay tại máy chủ; Mask không tự dừng khi danh mục đang mở; engine giữ bí mật (Mask, Cloud AI, tải hóa đơn, ABBYY) mỗi engine một tài khoản máy riêng, khác tài khoản module. *Khuyến nghị.*
   - (B) Mask tự dừng như các engine khác; mỗi lần cần Cloud, Anh mở khóa lại.
