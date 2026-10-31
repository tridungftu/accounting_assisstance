# G2 · giao G2-25 — áp gói đúng owner và kích hoạt nhất quán (lát cốt lõi, review Opus bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** `hop-nhat-20261023` (G2-00…G2-22a, G2-24 kiểm gói / staging `core\goi.py`, `core\cai_dat.py`; G2-33 tài khoản Core).

Quy ước như cũ:
- login thật + phiên xác minh; không DROP;
- **không sửa migration đã phát hành**; số 025 dành cho lát này;
- test tự áp chuỗi SQL theo số.

## Lát G2-25

**Tệp:**
- `src\kho_tri_thuc\core\sql\025_ap_goi.sql`
- `src\kho_tri_thuc\core\kich_hoat.py`
- `tests\test_g2_25.py`

**Căn cứ:**
- kế hoạch dòng G2-25;
- `CHUAN-CORE-SDK-v1.0.md` (v1.1) §3.8 `module.json`, §3.13 cài / nâng cấp / tắt / phục hồi;
- `CHUAN-CORE-CSDL-v1.0.md` (vai `vai_doi_cau_truc_<khoi>`, login `dang_nhap_cai_dat`);
- CD-043 mục 2: Core giải nén gói vào thư mục module đã cài do Core quản lý, không chạy thẳng từ thư mục nguồn;
- CD-045 (luồng Cài → Thử → Dùng, Nâng cấp giữ bản cũ).
- **Nợ phải trả trong lát này** (ghi ở `KE-HOACH-LAT-G2-G3.md`):
  - (a) cấp EXECUTE các cửa V2 module (`loi.ghi_ket_qua_v2`, `ghi_kiem_toan_v2`, cửa tạo việc G2-14, bus G2-15, danh mục G2-12 …) cho `vai_chay_mod_<ma>` **khi cài module mới**;
  - (b) wrapper kiểm tiền cố định module theo ABI 013, REVOKE EXECUTE PUBLIC / login; `vai_kiem_toan_ven_mod_<ma>` không có thành viên; cấp `USAGE loi` + EXECUTE `mtq_phien_rls()` cho role kiểm module;
  - (c) bảng của module mới phải gắn rào chắn DEMO của DM-1 nếu DM-1 đã gộp. Nếu chưa gộp, để móc gọi và ghi "Cần lead".
- **Dùng lại:**
  - `core\goi.py` / `cai_dat.py` (G2-24: kiểm gói, staging, không chạy mã khi đọc manifest, chặn traversal / symlink);
  - `core\doi_cau_truc.py` (áp migration theo gói);
  - `core\dang_ky.py` (registry G2-05).

**Việc:**
- **Login cài đặt chỉ EXECUTE gói đã kiểm:** không SQL tùy ý, không `SET ROLE`. Migration của gói chạy dưới `vai_doi_cau_truc_mod_<ma>` qua hàm Core.
- **Kích hoạt nhất quán:** migration + giải nén thư mục đã cài + đăng ký registry + cấp quyền (nợ a / b / c) + contract.
  - Lỗi ở bất kỳ bước nào → không kích hoạt một phần; trạng thái và tệp trở về trước khi cài.
  - Trạng thái sau cài là **Thử**; Admin chuyển **Dùng** qua CAS + audit.
- **Nâng cấp:** giữ bản cũ tới khi việc đang chạy xong; chuyển thế hệ có kiểm.
- **Tắt:** giữ dữ liệu.

**Test PG** (login thật; gói DEMO tối giản tạo trong test):
- cài đúng → Thử → Dùng;
- lỗi migration giữa chừng → không còn dấu vết kích hoạt;
- lỗi filesystem (giả lập) → như trên;
- login cài đặt không chạy được SQL tùy ý / `SET ROLE`;
- quyền V2 được cấp đúng cho vai module mới, không cấp thừa (PUBLIC / login khác không có);
- wrapper kiểm tiền module mới hoạt động; role kiểm không có thành viên;
- nâng cấp khi còn việc chạy → bản cũ giữ tới khi xong.

Báo cáo ≤ 3 dòng. Lead chạy PG và gọi review Opus.
