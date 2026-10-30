# G0 · Khảo sát Core (CD-026 mục 2, CD-027, CD-030 mục 5) — 4 Codex chỉ đọc

## Phần chung (mọi lát)

- Bạn là worker Codex, sandbox **chỉ đọc**. **Làm ngay**, không hỏi lại.
- Đang **DỪNG LẬP TRÌNH** (CD-026): không sửa tệp nào. Câu trả lời cuối cùng của bạn **chính là tài liệu khảo sát**. Lead lưu nguyên văn vào `docs\47-core\g0\KS-<x>.md`.
- **Căn cứ phải đọc:**
  - `D:\Claude\Phan mem ho tro ke toan\54-ke-hoach-core-database-api-v1.md` (TL 54, §14 là quyết định của Anh và thắng các mục khác);
  - `D:\Claude\Phan mem ho tro ke toan\55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md` (TL 55);
  - `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục CD-026…CD-030.
- **Mã** = nhánh hợp nhất đang checkout ở thư mục này (`hop-nhat-20261023`). Mọi khẳng định về mã hiện có phải kèm **`tệp:dòng`**. Không suy đoán: chỗ không thấy thì ghi "không thấy" hoặc "chờ Anh".
- **Không đọc:**
  - `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`, `.env`;
  - tệp `*.local.json`, khóa/mật khẩu, dữ liệu thật.

  Không in DSN, số tài khoản, tên đối tác.
- **Định dạng:**
  - tiếng Việt, kết luận trước;
  - bảng ngắn;
  - tối đa khoảng **5 trang**;
  - cuối tài liệu có mục **"Chờ Anh"** và **"Gợi ý cho đặc tả G1"** (≤ 10 dòng).
- Tên đề xuất phải là tiếng Việt không dấu, dạng snake_case (TL 54 §14 #4). Tên trong TL 55 chỉ là nháp.

## KS-A · Xương sống hiện có ↔ 12 khối Core (TL 54 §9)

- Với **mỗi khối** của TL 54 §9 (Application Shell → Backup/Restore), cho biết đã có / một phần / chưa, kèm tệp:dòng, những gì dùng lại được và chỗ còn thiếu.
- Đối chiếu tối thiểu các phần sau:
  - **Xương sống:**
    - khung lưới icon TL 49 và khung khai báo (`giao_dien\khung_khai_bao.py`);
    - công tắc module (`k2\module.py`, `k2\sql_module.py`, `giao_dien\module_cong_tac.py`);
    - khai báo vùng dữ liệu XS-5a1 (`ha_tang\khai_bao_module.py`, `k2\vung_du_lieu.py`).
  - **Phân quyền và đường gọi chung:**
    - ma trận thẩm quyền (`k2\sql_mtq_*.py`, `k2\ma_tran_tham_quyen.py`);
    - bus sự kiện (`ha_tang\bus_su_kien.py`);
    - engine và cổng (`ha_tang\engine.py`, `danh_ba_engine.py`, `engine_cong.py`, `engine_hoa_don.py`).
  - **Việc nền và hạ tầng dữ liệu:**
    - hàng việc và worker (`k2\sql_hang_viec.py`, `ha_tang\hang_viec.py`, `ha_tang\chay_engine.py`);
    - kho file;
    - sao lưu mã hóa (`tools\sao_luu_ma_hoa.py`) và khóa cột (`ha_tang\ma_hoa_cot.py`);
    - cổng AI (TL 48), OCR-1, MASK-1/2.
- Ghi riêng mục **"Giao diện cần có"** (TL 54 §9 dòng cuối): những màn nào đã có.
- Phần mềm hiện chạy **một tiến trình**. Đánh giá điều đó so với **CD-028** (mỗi module/engine là tiến trình riêng, Core giữ cổng rồi nhả cổng). Ghi rõ chỗ nào trong `giao_dien\server.py` sẽ phải tách.

## KS-B · Cơ sở dữ liệu và 67 migration

- **Đầu vào số liệu** (lead đã lấy, chỉ catalog): `docs\47-core\g0\so-lieu-csdl-demo.json`.
  - Cụm DEMO PostgreSQL 16.
  - CSDL DEMO của Anh mới chạy 23 migration.
  - Còn 303 CSDL `kho_test_*` và 651 role `ktt_test_*` tồn đọng.
  - Thư mục `D:\DU-LIEU-KE-TOAN\postgresql` **rỗng**: CSDL thật chung chưa dựng.
- **Việc:**
  1. Lập bảng **67 migration** (`ha_tang\pg_migrations.py`, M0001…M0067), mỗi dòng gồm:
     - số và tên;
     - lát/ngày nếu có dấu;
     - schema và đối tượng tạo/sửa;
     - module chủ hiện tại;
     - **khối đích đề xuất** theo TL 55 §1 (`loi`, `loi_tai_lieu`, `danh_muc`, `mod_crm`, `mod_m2`, `mod_m4`, `cong_bo_*`). Phần không thuộc các khối này, như M3, M9, M1, lõi kho cũ, ghi khối riêng đề xuất.
     - Migration **chạm nhiều khối** (thay thân hàm của khối khác) → đánh dấu.
  2. **Schema/role/quyền hiện có**, theo migration và theo số liệu catalog:
     - schema `bao_mat`, `giao_tiep`, `kho`, `m4`, `master`, `nhat_ky`, `public`, `bus`, `viec`…;
     - role `app_web`, `app_doc`, `app_ke_toan`, `app_cong_ai`…;
     - RLS/policy;
     - quyền PUBLIC, `SECURITY DEFINER`, `search_path`.

     Nêu rủi ro: role chạy là chủ bảng, quyền PUBLIC thừa, hàm DEFINER thiếu `search_path`.
  3. Đặt tên đối tượng hiện có vào hai nhóm: đã đúng quy ước tiếng Việt không dấu, hoặc phải đổi (ví dụ `schema_migrations`). Nhóm phải đổi thì đề xuất tên mới.
  4. Phần lõi cũ chạy qua `search_path` và SQLite: phần nào còn dùng, phần nào chỉ còn tương thích.
  5. Đề xuất cách dọn CSDL/role test tồn đọng (QD-20261026-09 "ít tài nguyên"). **Chỉ đề xuất, không chạy.**

## KS-C · Route/API hiện có

1. Liệt kê **mọi route HTTP**, mỗi route gồm:
   - method và đường dẫn;
   - hàm xử lý (tệp:dòng);
   - module;
   - kiểm danh tính, quyền, pháp nhân ở đâu;
   - có ghi dữ liệu không;
   - có chạy lâu không (đồng bộ hay hàng việc).

   Nguồn: `giao_dien\server.py` và mọi tệp route (`crm_g.py`, `m4.py`, `module_cong_tac.py`, khung, M2, M3, M9, cổng AI, OCR, Mask…). Có thể gộp nhóm route cùng mẫu.
2. Quy ước hiện tại:
   - dạng lỗi;
   - mã HTTP;
   - chống lặp (idempotency, `expected_version`, CAS);
   - phân trang;
   - tải/xuống tệp;
   - phiên đăng nhập;
   - CSRF/Origin.
3. Bảng **ánh xạ route cũ → nhóm `/api/v1/`** theo TL 55 §2. Ví dụ: `/api/crm/...` → `/api/v1/module/crm/...`, `/api/cong-tac-module/...` → `/api/v1/quan-tri/module`.
4. Nêu route **vi phạm** nguyên tắc TL 54 §9:
   - frontend tự quyết quyền;
   - dùng phiên RAM toàn cục;
   - tải xuống không kiểm quyền.

## KS-D · Công cụ ngoài và engine

Với mỗi công cụ, ghi:
- thư mục;
- ngôn ngữ và phụ thuộc;
- cách khởi động (start.bat/cmd/script);
- cổng mặc định;
- API thực tế (endpoint, xác thực);
- readiness/health;
- dữ liệu lưu ở đâu (SQLite/tệp/RAM);
- phiên giao diện có gắn trạng thái không;
- giới hạn;
- **đường thay** cho engine G3 (`e_ocr`, `e_mask`, `e_trich_xuat`, `e_hoa_don`).

**Danh sách công cụ:**
- **Mask v2:** `D:\GPT\Phan mem Mask file\Mask file v2`. Adapter đã có trong repo là MASK-1/2.
- **Engine Studio:** `D:\GPT\Local AI\engine-console`. **OCR đối chiếu:** `D:\GPT\Local AI\ocr-dual-release`. Lead vừa tìm thấy hai thư mục này; ghi rõ "lead tìm thấy, chờ Anh xác nhận đúng bản".
- **OCR-1** (ABBYY Hot Folder) và cổng AI (TL 48) trong repo.
- **Bộ tải hóa đơn điện tử** (#7 / M2-00) và `nguon\hoa_don_xml.py`, manifest/hồi cứu. Tìm vị trí dự án "Tải hóa đơn điện tử" qua tài liệu TL 31 / `CLAUDE.md` thư mục cha; không thấy thì ghi "chờ Anh".
- **Engine #6, E1-MUA, AnDanh** (trích xuất tham số hợp đồng).
- **Phần mềm review hồ sơ xây dựng** `D:\Claude\Ho tro review ho so xay dung\review_xaydung`. Phần mềm này **đóng băng**: chỉ mô tả API/khởi động/dữ liệu, **không mở `co_so_du_lieu\*.db`**.
- **Phần mềm theo dõi khoản vay:** vị trí lấy từ tài liệu; không thấy thì ghi "chờ Anh".

**Cuối tài liệu:** trả lời các dòng **TL 54 §12** đã biết từ tài liệu (hạ tầng, PostgreSQL, quy mô, danh tính, kho file, dữ liệu nhạy cảm, khả năng engine, dữ liệu cũ, vận hành, module mẫu). Dòng chưa biết ghi "chờ Anh".
