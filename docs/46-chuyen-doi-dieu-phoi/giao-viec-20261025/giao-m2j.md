# M2j — M2-00 · sau khi tải xong: danh sách hóa đơn với bộ lọc "mới từ lần tải này" + nút "Xem manifest"

Bạn là worker Codex, chạy không tương tác. Anh đã chốt thiết kế M2-00 (TL 43): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không khởi động PostgreSQL/server DEMO; không gọi cổng thuế thật). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/m2j` (từ hop-nhat, đã có M2e, M2h, M2h-c). Sandbox không ghi `.git`: **không commit**. Chạy: node test M2 hiện có; Python `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\43-M2-00-nhan-nguon-tu-cong-thue.md` dòng ~62: "Xong → M2 tự chạy bước nhận (mục 6) và chuyển sang danh sách hóa đơn của kỳ với bộ lọc **'mới từ lần tải này'**. Nút **'Mở thư mục'** và **'Xem manifest'**."
**Dùng lại:** route/giao diện tải (`giao_dien/m2_tai_hoa_don.py`, `assets/m2_tai_hoa_don.js`), bước nhận theo manifest (`m2/tai_hoa_don/nhan.py`, lát M2c — mỗi lần nhận gắn với lần tải/manifest), danh sách hóa đơn mua hiện có (tìm trang "Hóa đơn mua XML" trong `assets/app.js` và route đọc tương ứng). **Không** viết danh sách hóa đơn mới.

**Việc:**
1. Khi một lần tải kết thúc thành công: hiện nút **"Xem hóa đơn mới"** → mở danh sách hóa đơn của kỳ đó với bộ lọc **"Mới từ lần tải này"** (chỉ hóa đơn được nhận từ đúng lần tải/manifest đó; dùng định danh lần chạy đã có trong dữ liệu nhận — không suy theo thời gian). **Không tự chạy bước nhận** nếu luồng hiện tại chưa tự chạy (nếu đã có nút/route nhận thì giữ nguyên hành vi, chỉ nối bộ lọc).
2. Nút **"Xem manifest"**: hiện tóm tắt manifest của lần tải (số tệp, số hóa đơn, khoảng ngày, chiều mua/bán, lỗi nếu có) bằng tiếng Việt — không in đường dẫn tuyệt đối/MST đầy đủ ngoài phạm vi người xem có quyền. "Mở thư mục": chỉ khi đã có route mở thư mục an toàn sẵn; chưa có thì **bỏ qua**, ghi vào báo cáo.
3. Bộ lọc trong danh sách hóa đơn: thêm lựa chọn "Mới từ lần tải này" (khi có lần tải gần nhất); bỏ lọc trở về danh sách đầy đủ.
4. Test: Python (route đọc danh sách lọc theo lần tải, quyền) + node (nút sau khi tải xong, bộ lọc, xem manifest, chèn DOM an toàn).

**File được sửa/tạo (≤ 5):** `giao_dien/m2_tai_hoa_don.py`, `assets/m2_tai_hoa_don.js`, (nếu danh sách hóa đơn nằm ở đó) `assets/app.js` **chỉ khối danh sách hóa đơn** + route đọc tương ứng, 1–2 test mới. Cần thêm file/migration → **dừng**, ghi báo cáo.
**Không làm:** gọi cổng thật, đọc `.env`, migration, xóa file.
**Báo cáo cuối (≤ ½ trang):** nút/bộ lọc gồm gì · định danh lần tải dùng để lọc · test · file đã sửa · thông điệp commit `[M2j] …`.
