# G2-31a — SDK JS và Shell theo khai báo đã lọc quyền

**Phần chung:** như `GIAO-G2-DOT-A.md`. **Nền:** hợp nhất (G2-18 HTTP / dispatcher, G2-19 / 20 SDK).

**Tệp:**
- `src\kho_tri_thuc\sdk_core\trinh_duyet.js`
- `src\kho_tri_thuc\core\ui\index.html`
- `tests\g2_31a.cjs` (chạy bằng node)

**Căn cứ:**
- kế hoạch dòng G2-31a;
- `CHUAN-CORE-SDK-v1.0.md` (v1.1) §3.5 SDK JavaScript;
- `CHUAN-CORE-API-v1.0.md` §3.2 (Origin / CSRF), §3.7 (CAS / phân trang), §3.8 (202 / polling / Retry-After);
- CD-043 mục 3 (Core giữ khung giao diện chung, module chỉ cung cấp nội dung trang);
- CD-044 (nhãn "DEMO" khi ở pháp nhân DEMO);
- quy ước giao diện trong `CLAUDE.md` (tiếng Việt nghiệp vụ, không mã kỹ thuật, ngày dd/mm/yyyy, tiền có đơn vị).
- Dùng lại khung lưới icon UI-1 / UI-2 hiện có: `giao_dien\assets\` — **chỉ đọc**, không sửa tệp dùng chung.

**Việc:**
- **SDK JS:**
  - chỉ gọi Core `/api/v1/`;
  - gắn CSRF, xử lý 202 + polling theo `Retry-After`;
  - CAS / 409 giữ nháp;
  - đổi pháp nhân / context thì bỏ response cũ;
  - không lưu bí mật trong `localStorage`.
- **Shell `index.html`:**
  - khung chung (lưới icon theo khai báo module đã lọc quyền từ Core);
  - vùng nội dung trang module;
  - nhãn **DEMO** rõ khi pháp nhân `la_demo`.

**Test node:**
- polling / Retry-After;
- 409 giữ nháp;
- đổi context bỏ response cũ;
- không gọi URL ngoài `/api/v1/`;
- nhãn DEMO hiện đúng.

Báo cáo ≤ 3 dòng.
