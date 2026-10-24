# BÁO CÁO CRM NEUTRAL COMPAT 02 — sửa test tối thiểu (CODE_ONLY)

**Căn cứ:** `docs/GIAO-SUA-CRM-FEEDBACK-TEST-02.md`.

**CODE_ONLY:** không chạy lệnh/SQL/import/test/network/browser; không đọc var/.env/.git/sourceapps/dữ liệu thật; không xóa/đổi tên/di chuyển tệp.

**Self-tests: NOT_RUN.** Root chạy kiểm độc lập.

## 1. Tệp

| Tệp | Thao tác |
|---|---|
| `tests/test_crm_neutral_compat.py` | sửa — chỉ tệp này |
| `docs/BAO-CAO-CRM-NEUTRAL-COMPAT-02.md` | tạo mới |

Không chạm production (gồm hai hunk CRM/server đã review), migrations, guard, M9, `app.js`, tests khác, báo cáo 01.

## 2. Thay đổi

### 2.1. T05 — không vi phạm guard cũ

BANK2 trước nối hai lần vào DOT-1. Guard lịch sử đúng là cấm hai link active cùng BANK/đợt (`LIEN_KET_DA_CO`).

Nay nối:
- 100m vào **DOT-1** (khóa `crmn-d1-a`);
- 50m vào **DOT-2** (khóa `crmn-d2-b`).

Vẫn kiểm:
- `da_noi` = 150m = SUM độc lập mọi link CRM active của BANK2;
- mọi BANK khớp SUM;
- gỡ link 50m → còn 100m;
- snapshot BANK/đề xuất/PK/hash giữ nguyên.

Không nới guard, không sửa sản phẩm.

### 2.2. setUpClass — cấu hình fixture tối thiểu

Bỏ đọc `ROOT/cau_hinh.toml` (không nằm trong source frozen). Hằng `CAU_HINH_FIXTURE` được ghi thành `cau_hinh_fixture.toml` trong **chính thư mục temp được giữ lại** của test. `LocalApp(cls.cau_hinh, tam / "web")` dùng tệp này.

Nội dung (đúng các trường `Config.load` cần):

| Bảng | Giá trị |
|---|---|
| `[app]` | `entity_id = "PLHN_FIXTURE"`, `environment = "fixture"`, `data_dir = "data"` |
| `[money]` | `currency = "VND"`, `scale = 0` |
| `[operation]` | `junsky_export_enabled = false`, `junsky_import_enabled = false` |
| `[storage]` | `engine = "sqlite"` |

Không đọc cấu hình thật, `.env` hay `var`.

### 2.3. Mô tả snapshot trung thực

Docstring `anh_chup`, comment ca âm T04 và docstring module nay ghi đúng phạm vi so sánh:

| Đối tượng | Cách so |
|---|---|
| Bảng nghiệp vụ được chọn (`chung_tu`, `chung_tu_dong`, `de_xuat`, `de_xuat_dong`, `lien_ket_chung_tu`, `lich_thu`) | toàn hàng (`to_jsonb`) |
| Audit `nhat_ky.su_kien` | chỉ số lượng |
| Sequence | chỉ `last_value` |
| Tệp | chỉ đường dẫn + kích thước |

Không tuyên bố so toàn byte tệp, toàn hàng audit hay mọi trường sequence. Không thêm framework snapshot.

## 3. Chưa chạy

- T01–T05: **NOT_RUN** (CODE_ONLY).
- Giả định còn mở như báo cáo 01: mã lỗi HTTP CRM 400 + `error`; ngày nghiệp vụ LocalApp cho phép nối; denial không tăng sequence.
- Thêm một giả định mới: TOML tối thiểu đủ để `LocalApp` dựng CRM DEMO (DSN lấy từ biến môi trường `LocalApp.CRM_ENV*`). Nếu LocalApp cần trường cấu hình khác, đó là phát hiện cần báo Root.
