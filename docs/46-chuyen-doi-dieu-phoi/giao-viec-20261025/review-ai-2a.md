# review-lat AI-2a (vòng 1/2, CHỈ ĐỌC) — cổng AI dùng chung (đường duy nhất ra Cloud)

Lát Claude Opus: nhánh `lat/ai-2a`, commit `fe48744` (ai_cuc_bo: `ask_local`, `LocalAIUnavailable`) + `af31ef6` (`tri_thuc/cong_ai.py`, `tests/test_cong_ai.py`). Handoff `giao-viec-20261025/giao-ai-2a.md`; căn cứ TL 48 `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` §1, §4; hợp đồng API Mask v2 trong `D:\GPT\Phan mem Mask file\Mask file v2\README.md` (chỉ đọc; không đọc data\, *.key, *.maskvault, *.maskkeep, config\mask-api.key). Worker báo 78/78 (test_cong_ai 30, test_ai1_local_ai_lan 23, test_v11 25), Cloud mặc định TẮT.

Kiểm (tệp:dòng):
1. **Không có đường nào gửi văn bản chưa che ra Cloud**: công tắc tắt/khóa thiếu/Mask lỗi/422/423/`gui_duoc` false/`con_sot` khác rỗng/`danh_muc` khác `da_mo`/XML thô → không gọi nhà cung cấp; tự kiểm lại định danh đã khai sau che; chỉ dẫn/tên trường cũng qua Mask. Tìm mọi chuỗi đi vào thân yêu cầu nhà cung cấp và chứng minh đều là văn bản đã che (hoặc hằng số trong mã).
2. **Khóa**: khóa API (biến môi trường) và khóa Mask (tệp) không vào log, ngoại lệ, chuỗi ngoại lệ gốc, kết quả, nhật ký; không đọc `.env` trong mã? (TL 48 nói khóa trong `.env` — mã đọc biến môi trường là chấp nhận được, nêu nếu khác).
3. **Gọi nhà cung cấp đúng API thật**: đối chiếu định dạng gọi Anthropic (header `anthropic-version`, tên model `claude-opus-5-5`, tham số `fallbacks`, việc bỏ `temperature`) và OpenAI với tài liệu chính thức — dùng skill `claude-api` (gọi Skill tool tên `claude-api`) để kiểm phần Anthropic; tham số không có thật → Nên sửa/Chặn tùy hậu quả (gọi thật sẽ lỗi 400 khi mở Cloud ở AI-4).
4. **Mở che + kiểm trích dẫn** trên văn bản gốc; trích dẫn sai → loại trường; kết quả tối đa Vàng; `ket_thuc_luot` dọn RAM Mask khi bỏ lượt.
5. **Local luôn trước**, Cloud chỉ theo TL 48 §1.5 (a)(b); kiểm xác suất 0%; bảng loại việc hợp lý (CHON_UNG_VIEN không dùng Cloud).
6. **Không phá phần cũ**: `ai_cuc_bo.choose_counterparty` không đổi hành vi; test quét `src/` chỉ cho phép `cong_ai.py` (và `cloud.py` đã khóa) nhắc địa chỉ nhà cung cấp.
7. Nhật ký `BanGhiCongAI`: không chứa văn bản gốc/đã che; đủ trường cho AI-2b.
Kết luận Đạt / Không đạt; ≤ 10 điểm, Chặn / Nên sửa / Để sau, tiếng Việt, ≤ 1 trang.
