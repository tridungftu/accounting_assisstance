# XS-5a2 · Xương sống — nối khai báo bốn vùng dữ liệu vào khung module (CD-018)

- Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM, **bằng apply_patch**. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì ghi NOT_RUN; lead sẽ chạy test.

## Căn cứ

- `docs\46-chuyen-doi-dieu-phoi\KK-VUNG-DU-LIEU.md`: §2 (bốn vùng), §5 dòng **5a2** (và 5a1 để biết đã có gì).
- `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\tra-loi-lead-xs-5a1.md`.
- Mã 5a1 đã gộp: `src\kho_tri_thuc\ha_tang\khai_bao_module.py`, `src\kho_tri_thuc\k2\vung_du_lieu.py`, `tests\test_xs5_khai_bao.py`.
- Khung CRM hiện có: `src\kho_tri_thuc\giao_dien\khung_khai_bao.py` và test của nó.

## Tệp được sửa (2)

- `src\kho_tri_thuc\giao_dien\khung_khai_bao.py`
- `tests\test_xs5_khung.py` (mới)

## Việc

1. Khung module **lấy** khai báo vùng dữ liệu từ nguồn 5a1. Một nguồn — không chép danh sách bảng/hàm vào khung.
2. Mỗi phần/thẻ của khung chỉ đếm/đọc qua đối tượng nằm trong vùng đã khai báo của module đó:
   - V1 ghi riêng;
   - V3 danh mục chung;
   - V4 dữ liệu công bố.

   Thiếu khai báo hoặc khai báo không khớp → lỗi rõ lúc nạp khung (test đỏ), không im lặng.
3. **Bảo toàn từng bit** hành vi hiện có của khung CRM:
   - adapter;
   - số đếm;
   - quyền vai;
   - đường dẫn;
   - "không coi số bị giới hạn là tổng đầy đủ".
4. Không thêm quyền, không thêm SQL mới, không đổi `server.py`.

## Test

- Khung CRM hiện có cho đúng kết quả như trước. Test cũ của khung vẫn xanh.
- Khung có thẻ đọc đối tượng ngoài vùng khai báo → đỏ.
- Module thiếu khai báo → đỏ.

## Báo cáo

≤ ¼ trang, gồm "Cần lead". Thông điệp commit đề xuất `[XS-5a2] …`.
