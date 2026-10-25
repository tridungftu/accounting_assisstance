# Review MASK-1 (chế độ API của Mask file v2) — vòng 1/2, CHỈ ĐỌC

Bạn là reviewer Claude của lead (lát rủi ro cao: đây là cổng duy nhất cho dữ liệu kế toán đi Cloud — TL 48 `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` §1, §4). **Chỉ đọc**: không sửa, không tạo tệp trong Mask v2, không khởi động server, không gọi mạng.

**Phạm vi:** `D:\GPT\Phan mem Mask file\Mask file v2\` — mới `privacy\auto_api.py`, `tests\test_auto_api.py`; sửa `privacy\server.py`, `run_privacy.py`, `privacy\__init__.py`, `.gitignore`, `CHANGELOG.md`, `README.md`, `docs\ARCHITECTURE.md`, `CLAUDE.md`. Bản gốc trước khi sửa (để so diff): `D:\Claude\Phan mem ho tro ke toan\LUU-TRU\mask1-sao-luu-mask-v2-20261025-183855\` (dùng `git diff --no-index` hoặc `diff -u`).
**Cấm đọc:** `data\`, `..\Mask file\data\`, `*.key`, `*.maskvault`, `*.maskkeep`, `.backups\`, `.venv*\`, `File ví dụ\`, `config\mask-api.key`. Đọc `CLAUDE.md` của Mask v2 trước.

**Kiểm (ghi tệp:dòng):**
1. Xác thực `/api/v1/*`: Bearer so hằng thời gian; kiểm ở `guard` **trước** khi đọc thân yêu cầu; Host đúng `127.0.0.1`; từ chối khi có `Origin`/`Sec-Fetch-Site`; khóa không in/ghi log/không trả trong lỗi; khóa API không mở được endpoint giao diện và cookie/CSRF giao diện không mở được `/api/v1`. Sinh tệp khóa: vị trí, quyền, độ dài/ngẫu nhiên (`secrets`), `.gitignore`.
2. Cổng "còn sót": khi còn sót → **không bao giờ** trả `van_ban_da_che` hay tạo lượt; mọi đường lỗi khác cũng không trả văn bản. `gui_duoc` chỉ true khi `con_sot` rỗng. Số tiền/ngày không bị che (Anh chốt). Định danh đã biết + bí danh: không va chạm, `trung_bi_danh`.
3. Mở che: chỉ thay bí danh của đúng lượt; bí danh lạ → `bi_danh_khong_ro`, không đoán; TTL 30 phút, tối đa 200 lượt, chỉ RAM; `ket_thuc_luot` xóa thật.
4. Danh mục: API chỉ dùng khi giao diện đang mở khóa, không gia hạn phiên; 423 khi khóa. Không đổi định dạng `.maskvault`/`.maskkeep`, không ghi cụm mới vào danh mục.
5. Không gọi mạng ra ngoài (audit hook còn hiệu lực với đường API); giới hạn kích thước; lỗi không phản chiếu đầu vào.
6. Test mới có kiểm đủ 1–5 không; ca nào thiếu.
7. Hai điểm worker ghi **CẦN ANH XÁC NHẬN** (lưu cụm mới "chờ duyệt"; API dùng danh mục khi phiên giao diện hết hạn): nêu rủi ro mỗi phương án, 2–3 dòng, để lead hỏi Anh.

**Kết luận:** Đạt / Không đạt; mỗi mục **Chặn / Nên sửa / Để sau**, ≤ 1 trang, tiếng Việt. Không in nội dung dữ liệu thật nào.
