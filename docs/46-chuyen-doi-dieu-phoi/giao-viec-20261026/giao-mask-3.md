# MASK-3 — Mask file v2: cụm định danh mới ở chế độ API lưu "chờ Anh duyệt" vào tệp riêng mã hóa + màn hình duyệt (QD-20261025-23)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại** (chưa rõ → chọn cách an toàn, ghi "Cần Anh"). Thư mục làm việc: `D:\GPT\Phan mem Mask file\Mask file v2` (dự án riêng, **không có git** — không chạy lệnh git ở đây). Đọc `README.md`, `CHANGELOG.md`, tài liệu API trong dự án.

**Ràng buộc cứng (Mask v2):** **không đọc, không sửa**: `data\`, mọi `*.key`, `*.maskvault`, `*.maskkeep`, `config\mask-api.key`, `.backups\`, `.venv*\`, `File ví dụ\`. Không xóa tệp (cần bỏ → để nguyên, ghi báo cáo). Ghi **CHANGELOG** (mục mới, ngày 26/10/2026). **Số test và benchmark không được giảm** (chạy bộ test + benchmark có sẵn trước và sau, ghi số). Không gọi mạng ngoài `127.0.0.1`. UTF-8 không BOM.

**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\docs\QUYET-DINH.md` **QD-20261025-23** (cụm định danh **mới** gặp trong lượt tự động (chế độ API) được lưu "chờ Anh duyệt" vào **tệp riêng mã hóa** (như `.maskkeep`) kèm **màn hình duyệt**; **không đổi định dạng** danh mục `.maskvault`; trước đó cụm mới chỉ giữ trong RAM của lượt — `cum_moi`), **QD-20261025-24** (danh mục đã mở khóa dùng cho API đến khi tắt Mask; mật khẩu chỉ trong RAM).

**Việc:**
1. Chế độ API: khi lượt `/che` phát hiện cụm định danh mới (`cum_moi`), ghi vào **tệp chờ duyệt mã hóa riêng** (cùng cơ chế mã hóa/khóa như tệp giữ `.maskkeep` hiện có; không lưu mật khẩu ra đĩa; không ghi văn bản gốc ngoài cụm định danh cần duyệt + ngữ cảnh tối thiểu đã che; chống trùng; giới hạn kích thước).
2. **Màn hình duyệt** trong giao diện Mask v2 (khi danh mục đã mở khóa): danh sách cụm chờ duyệt → Anh chọn **Thêm vào danh mục** (nhóm định danh) / **Bỏ qua** / **Đánh dấu không phải định danh**; thao tác ghi vào danh mục theo đường ghi danh mục hiện có; nhật ký thao tác.
3. Test (bộ test của dự án): cụm mới → vào tệp chờ (mã hóa, không đọc được khi khóa); duyệt Thêm → vào danh mục, lượt sau được che; Bỏ qua → không vào; định dạng `.maskvault` không đổi; benchmark không giảm.
**Báo cáo (≤ ⅓ trang):** tệp đã sửa/thêm, cơ chế mã hóa dùng lại, test/benchmark trước → sau, mục CHANGELOG, Cần Anh.
