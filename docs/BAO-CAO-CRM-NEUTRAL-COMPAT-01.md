# BÁO CÁO CRM NEUTRAL COMPAT 01 (CODE_ONLY)

**Căn cứ:** `docs/GIAO-SUA-CRM-NEUTRAL-COMPAT-01.md` (task `CRM_NEUTRAL_COMPAT_CODE_ONLY01`, Root chọn OptionA — khôi phục compatibility CRM/M1 đã có).

**CODE_ONLY:** chỉ dùng file tools. Không chạy shell/Python/import/AST/test/SQL/HTTP/browser/process. Không đọc var/.env/.git/sourceapps/dữ liệu thật/credentials. Không xóa/di chuyển/đổi tên tệp.

**Self-tests: NOT_RUN.** Không nhận acceptance/runtime release. Không tuyên bố HTTP/GUI/PG đã chạy hay CRM/M1/M3/file33 hoàn tất.

Ba technical review CRM công khai (`REVIEW-CRM-HOST-06.md`, `REVIEW-CRM-HTTP-03.md`, `REVIEW-CRM-M1-03.md`) **không được đọc trong lượt này**. Hành vi lịch sử được đối chiếu qua handoff và `tests/test_crm_k2.py` (t08). Root có thể kiểm thêm.

## 1. Phạm vi 4 tệp

| Tệp | Loại | Thay đổi |
|---|---|---|
| `src/kho_tri_thuc/k2/crm.py` | sửa | Chỉ subquery `da_noi` trong `CrmK2.danh_sach` (R01) |
| `src/kho_tri_thuc/giao_dien/server.py` | sửa | Chỉ dòng `return` của `LocalApp.crm_m1_sao_ke` (R02) |
| `tests/test_crm_neutral_compat.py` | mới | Regression T01–T05 (NOT_RUN) |
| `docs/BAO-CAO-CRM-NEUTRAL-COMPAT-01.md` | mới | Báo cáo này |

Không chạm: `pg_migrations.py`, `m1_demo.py`, `lien_ket_chung.py`, M9, fixtures, config, source apps, tests cũ, reports/reviews/handoff cũ. Không thêm migration/schema/function/grant.

## 2. Hai diff chính xác

**R01 — `crm.py`, `danh_sach` (~dòng 771):**
```diff
-                    for r in self.conn.execute("""SELECT c.*, p.ma, (SELECT t.da_phan_bo_minor FROM kho.tien_con_lai(c.id) t) AS da_noi,""" + """
+                    for r in self.conn.execute("""SELECT c.*, p.ma, (SELECT coalesce(sum(k.so_tien_khop_minor), 0) FROM kho.lien_ket_chung_tu k
+                                                                     WHERE k.chung_tu_a_id = c.id AND k.trang_thai <> 'HUY') AS da_noi,""" + """
```

Những gì giữ nguyên:
- alias/shape `da_noi`;
- lọc `SAO_KE`/`THU`/pháp nhân (`pns_tien`), danh tính phiên/RLS, giao dịch đọc.

Cách tính mới:
- SUM mọi parent active (≠ HUY) có BANK là `chung_tu_a_id`;
- không lọc theo một hợp đồng, không cộng child quantity; `so_tien_khop_minor` NULL của parent evidence L11 không thành tiền.

Không gọi helper legacy, không catch `UndefinedFunction`, không fallback theo catalog.

**R02 — `server.py`, `crm_m1_sao_ke` (~dòng 330):**
```diff
-        return {"m1": {k: v for k, v in m1.items() if k != "sqlite"}, "chieu": chieu, "proof": self._ghi_proof_tien(admin, pn)}
+        return {"m1": {k: v for k, v in m1.items() if k != "sqlite"}, "chieu": chieu}
```

Những gì giữ nguyên:
- quyền trước ingest (`kiem_nhan_tien`), fact hợp đồng;
- `m1_demo.nhan_sao_ke` (Store.ingest + engine M1), converter `chieu_sang_k2`;
- kiểm `chieu["ok"]` (từ chối → `CRM_M1_CHIEU_LOI`).

Không trả proof/PROVEN giả. `_ghi_proof_tien` (định nghĩa) và caller M9 (`server.py` ~dòng 419, `"proof": self._ghi_proof_tien(admin, pn)`) giữ **byte-exact**. Edit được neo bằng ngữ cảnh duy nhất của hàm CRM để không chạm dòng M9 trùng chuỗi.

## 3. Hành vi sau sửa

- **GET CRM** (`danh_sach`) trên neutral16 không còn gọi `kho.tien_con_lai`. `da_noi` là SUM lịch sử của link CRM active theo BANK.
- **`m1-sao-ke`** trả API lịch sử `{m1, chieu}` và không gọi verifier proof tiền thuộc lineage legacy full-M13. Trước đây CRM route có thể lỗi sau khi projection đã commit; nay route trả đúng kết quả của pipeline đã chạy.
- **Giữ nguyên:**
  - `lien_ket` / `go_lien_ket`, quyền trước replay, lock HĐ→BANK→đợt, hiệu lực/phụ lục, PN/tiền tệ;
  - hai budget guard CRM (`VUOT_TIEN_KHA_DUNG`, `VUOT_NGHIA_VU` ở CSDL), HUY/idempotency hiện hành, audit.

**Giới hạn:** guard ngân sách BANK M11 hiện SUM link có `lich_thu_id`. Lượt này bảo toàn compatibility/conservation CRM đã có, không tạo all-module allocation ledger, không nghiệm thu G10/period/production.

## 4. Test mới `tests/test_crm_neutral_compat.py` — NOT_RUN

**Thiết lập:**
- Self-contained: không kế thừa/import class test cũ. Chỉ dùng `fixtures_crm`, `crm_demo`, `LocalApp`/`LocalServer` và pipeline M1 thật.
- Skip có khai báo khi thiếu `psycopg` hoặc `KHO_PG_DSN_TEST` (không tính đạt). Không đọc `.env`/credentials.
- DB mới `kho_test_crmn_*`, `pg.migrate` **mặc định** (assert 16), seed CRM DEMO.
- LOGIN app_web `NOSUPERUSER NOBYPASSRLS`; admin chỉ dùng cho setup/bộ chiếu M1/observer chỉ-đọc.
- Loopback, cổng ngẫu nhiên, token/cookie thật; mật khẩu chỉ trong bộ nhớ.
- Đóng đúng server/thread/kết nối sở hữu; giữ DB/role/thư mục. Không DELETE/DROP/TRUNCATE.

**Các ca:**

| Ca | Nội dung |
|---|---|
| T01 | Schema 16; `to_regprocedure`/`to_regclass` chứng minh `kho.tien_con_lai(uuid)`, `kho.ghi_proof_tien_noi_bo(...)`, `kho.chung_tu_tien_encoding` vắng. KT_A GET `/api/crm` 200, `tien=[]`. `MO_PHONG_KT_KHONG_CRM_A` nhận `khong_quyen` + 0 hồ sơ/HĐ/tiền |
| T02 | HTTP `m1-sao-ke` `PN_DEMO_A:truoc_hop_dong` (300m): 200; khóa đỉnh đúng `{m1, chieu}`; `chieu.ok`; 0 lệch; `moi=1`; một BANK logic mới; số đề xuất = engine; `da_noi="0"`; legacy vẫn vắng. Retry: `moi=0`; chung_tu/dòng/đề xuất/link toàn hàng giữ nguyên; snapshot PK/business/hash BANK bằng nhau. Khai báo: `su_kien` có thể tăng |
| T03 | `kcn_goc` qua HTTP (BAN_HANG) → KT kiểm → CFO duyệt (`so_dot=3`); lịch 300m/1.2b/1.5b. Nối 100m → `da_noi` 100m (khớp SUM độc lập); replay cùng ID; đổi body → `IDEMPOTENCY_KHAC`. Gỡ → `da_noi="0"`; khóa cũ trả `{id, lap_lai, HUY}`; vẫn đúng 1 link |
| T04 | Dương: nối đủ 300m vào cọc. M1 `sau_hop_dong` thật cho BANK còn tiền. Bốn ca âm, mỗi ca so ảnh chụp toàn hàng chung_tu/dòng/đề xuất/link/lịch + số `su_kien` + `pg_sequences` + danh sách tệp artifact trước/sau bằng nhau (0 delta): `VUOT_TIEN_KHA_DUNG` (BANK hết, DOT-1 đủ); `VUOT_NGHIA_VU` (COC-1 đã đủ, BANK2 còn); `LIEN_KET_THAM_CHIEU` (KT_B); `KHONG_CO_QUYEN_HANH_DONG` (CFO) |
| T05 | KT_B không thấy HĐ/tiền của A. Hai link active cùng BANK2 → `da_noi` = SUM đầy đủ (150m) và khớp SUM độc lập cho mọi BANK. Một ca từ chối giữa chừng; gỡ một link → 100m. Snapshot BANK/đề xuất/PK/hash giữ nguyên; positive đọc lại sau cùng |

**Giả định chưa xác minh bằng runtime:**
- Mã lỗi HTTP CRM là 400 với `error` = mã DataError (theo `server.py`).
- Ngày nghiệp vụ LocalApp cho phép nối vào phiên bản `kcn_goc` hiệu lực.
- Denial không làm tăng sequence. Nếu thực tế khác, đó là phát hiện cần báo, không phải nới assert.

## 5. Bảo toàn hash

Không đọc/tính hash (CODE_ONLY). Các tệp được bảo vệ theo handoff không bị mở để ghi: `pg_migrations.py`, `m1_demo.py`, `lien_ket_chung.py` và mọi tệp ngoài 4 tệp allowlist. Root xác minh SHA khi freeze.

## 6. Chưa chạy / ngoài phạm vi

- Toàn bộ T01–T05: **NOT_RUN**. Regression `tests/test_crm_k2.py` (vẫn kỳ vọng schema 13/legacy) **không sửa**; Root đánh giá riêng.
- Không mở lại M2–M5 deep Q09/shared pools, không đổi M9, không đổi yêu cầu báo cáo thiếu/thừa/trùng M2/M5.
