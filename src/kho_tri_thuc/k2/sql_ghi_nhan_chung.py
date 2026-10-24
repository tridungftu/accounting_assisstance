"""M4-03B-01 — identity nguồn kinh tế dùng chung M2–M4 + đối chiếu căn cứ NT ↔ hóa đơn do KT xác nhận. CHỈ hằng SQL, export `M4_03B_COMMON_SQL`.

KHÔNG tự import/đăng ký/apply, KHÔNG đoán ordinal: Root integration owner append vào registry SAU mọi migration đã cấp ordinal (sau M4_03A/M26).
Không DROP/sửa bảng/hàm/dòng cũ; checksum 1–26 không đổi. Thay đổi trên đối tượng cũ CHỈ gồm (additive, đã Root duyệt):
- nới CHECK module của `kho.bien_nhan_thao_tac` thêm 'M4' (giữ CRM/M1/M2/M5) để dùng CÙNG biên nhận chung (không bảng biên nhận thứ hai);
- thêm trigger `bien_nhan_dc_chi_chu`: biên nhận module M4 hoặc operation DC_CAN_CU_* chỉ do hàm chủ bảng tạo (app không prefill/giả phát lại).

Ý nghĩa: `KT_XAC_NHAN_CAN_CU` = kế toán xác nhận QUAN HỆ CĂN CỨ (nguồn nghiệm thu đợt ↔ hóa đơn mua đã có), KHÔNG phải M2_MAP, KHÔNG
financial owner, KHÔNG công nợ/claim/proposal/AP/capacity/tài khoản/thuế. Mọi phiên bản ghi `ghi_nhan = CHO_CAN_CU_GHI_NHAN`,
`financial_owner IS NULL`; không bảng tiền/de_xuat/chung_tu/lien_ket_phan_bo nào bị chạm. Tiền M2 vẫn UNPROVEN_NO_MINOR — không đọc số tiền.

Quyền (server/DB quyết, không từ body):
- nguồn NT: m4.kt_kiem(cho,'XEM') (03A: ID+login hoạt động + module M4 + vai dự án KE_TOAN + vai trò toàn cục KE_TOAN/KE_TOAN_TRUONG). NT-only không
  cần M2.
- nguồn hóa đơn: M2_READ (module M2 trên PN + vai trò KE_TOAN/KE_TOAN_TRUONG/CFO/XEM) để xem; MỌI lệnh ghi còn bắt buộc vai trò toàn cục KE_TOAN hoặc
  KE_TOAN_TRUONG trên PN đó (không CFO/XEM ghi, không M2_MAP, không cấp vai).
- cross-source: đủ quyền trên TỪNG nguồn. Kiểm trước mọi lookup nội dung/biên nhận/lịch sử, lặp lại dưới khóa và ở trigger deferred lúc commit.

Hiện hành NT: Python dựng đồ thị bằng ĐÚNG producer 03A (`ke_toan_nghiem_thu._ghim_do_thi` sau `m4.kt_khoa`/`m4._kt_khoa_doc`) trong CÙNG giao
dịch chủ bảng, rồi `kho._dc_nt_ghi(cho)` ghi kết quả `m4._kt_hien_hanh` vào GUC cục bộ giao dịch `ktt.dc_nt_hien_hanh` (gắn pid+txid+actor). Đồ thị
đối chiếu chỉ coi NT hiện hành khi có mục hợp lệ của CHÍNH giao dịch này; thiếu/khác giao dịch → không hiện hành (không fallback).

Khóa: (Python) HĐ sorted → m4.kt_khoa từng gốc NT → ghim producer; (SQL) gốc hóa đơn sorted (advisory HOA_DON_ROOT| + closure
kho.l11_khoa_dong_nguon_noi_bo, thứ tự M16) → gốc đối chiếu → phiên bản mới nhất → biên nhận. Không khóa BANK, không gọi writer tiền/số lượng.

FIX01 (docs/GIAO-CODE-M4-03B-FIX01.md) — gốc ổn định khi đổi tập nguồn/phần:
- `doi_chieu_id` là identity xuyên revision. Thêm/bớt nguồn, đổi phần = revision mới (lý do + expected_revision + CAS đồ thị) của CÙNG gốc; không dựng
  gốc thay thế. `khoa_goc_sha256` của gốc = digest tập lúc TẠO, bất biến; mỗi revision mang `tap_sha256` (digest kind+occurrence+part, không phiên bản).
- Alias ghi thêm `kho.mua_doi_chieu_can_cu_tap` (PN, tap_sha256) → đúng MỘT gốc (metadata identity nội bộ, KHÔNG master/financial owner): tập đã từng
  thuộc gốc nào giải về gốc ấy (khóa mới/ABA không tạo gốc trùng); sửa sang tập của gốc khác → 409 DC_TAP_THUOC_GOC_KHAC, không merge/retag/dời lịch sử.
  Không UNIQUE theo nguồn đơn lẻ: một hóa đơn/NT tham gia nhiều đối chiếu với tập khác nhau.
- Namespace biên nhận bất biến theo gốc: `module_bien_nhan` ghi lúc tạo (M4 nếu tập tạo có NT, M2 nếu chỉ hóa đơn) — chỉ namespace biên nhận chung,
  không owner/quyền; đổi loại nguồn không đổi namespace (cùng khóa khác nội dung vẫn 409).
- Closure trước khóa: refs revision mới nhất ∪ refs yêu cầu (quyền đọc mọi revision trước) → quyền ghi hiện hành trên union → khóa hóa đơn union sorted →
  alias (advisory DC_TAP|) → gốc → revision mới nhất (phải đúng revision đã đọc trước khóa, lệch → DC_REVISION_CU rollback) → biên nhận → CAS.
  Python ghim producer 03A cho mọi NT của union (adapter không đổi). Revision/receipt/identity nguồn cũ giữ nguyên (append-only).

FIX02 (docs/GIAO-CODE-M4-03B-FIX02.md) — chỉ tên: native05 C01 dừng 42702 AmbiguousColumn `t` (dc_luu line22) vì alias `t` của `_REFS` trùng biến
jsonb `t` của dc_luu; `_HIEN_HANH` cũng dùng alias `x` trùng biến `x`. Sửa: `_REFS`/`_HIEN_HANH` dùng alias riêng + cột tường minh
(`AS dc_ref(value)` → `dc_ref.value`, `dc_hh`/`dc_ghim`), biến dc_luu `t`/`x` → `v_muc`/`v_cap`. Không `#variable_conflict`, không đổi GUC/cấu hình,
không đổi statement/guard/shape/thứ tự khóa/CAS/quyền. Quy tắc: trong mỗi hàm plpgsql không tên alias quan hệ/cột SQL nào trùng biến/tham số.
"""

from __future__ import annotations

_LOI = "USING ERRCODE = 'P0001'"
GUC_NT = "ktt.dc_nt_hien_hanh"
VAI_TRO_M2_DOC = ("KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM")
VAI_TRO_KT = ("KE_TOAN", "KE_TOAN_TRUONG")
LOAI_NGUON = ("NT", "HOA_DON")
LOAI_PHAN = ("TOAN_BO", "DONG_LOGIC")
PHAN = ("TOAN_PHAN", "MOT_PHAN")
TY_LE_TRANG_THAI = ("KHONG_AP_DUNG", "KHAI_BAO_THO_CHUA_SCALE", "THIEU")
LOAI = ("NHAP", "XAC_NHAN")
TT_NHAP = "NHAP_DOI_CHIEU"
TT_XAC_NHAN = "KT_XAC_NHAN_CAN_CU"
TT_CAN_KIEM_LAI = "CAN_KIEM_LAI"
GHI_NHAN_TT = "CHO_CAN_CU_GHI_NHAN"
OP_LUU, OP_XAC_NHAN = "DC_CAN_CU_LUU", "DC_CAN_CU_XAC_NHAN"
CONTRACT_DO_THI = "m4-03b-doi-chieu-can-cu/v1"
# mã thiếu (sắp collation "C" = sorted() ASCII của Python)
THIEU = ("BEN_BAN_HD_THIEU", "BEN_BAN_KHAC", "CHO_MAPPING_M2", "HOA_DON_CHUA_CO_PHIEN_BAN", "NT_CHUA_KT_XAC_NHAN", "NT_KHAC_HOP_DONG",
         "NT_KHONG_HIEN_HANH", "PHAN_KHAI_THIEU", "THIEU_HOA_DON", "THIEU_NT")
TOI_DA_THANH_PHAN = 50
TOI_DA_TEP = 20
BANG = ("mua_nguon_kinh_te", "mua_nguon_kinh_te_phien_ban", "mua_nguon_phan", "mua_doi_chieu_can_cu", "mua_doi_chieu_can_cu_phien_ban",
        "mua_doi_chieu_can_cu_thanh_phan", "mua_doi_chieu_can_cu_nhat_ky", "mua_doi_chieu_can_cu_tap")
MODULE_BIEN_NHAN = ("M4", "M2")
HAM_DOC = ("kho.dc_doc_hoa_don(uuid)",)
HAM_NOI_BO = ("kho._dc_m2_doc(uuid)", "kho._dc_kt_toan_cuc(uuid)", "kho._dc_quyen(jsonb, boolean)", "kho._dc_doc_duoc(jsonb)",
              "kho._dc_nt_ghi(uuid)", "kho._dc_nt_hien_hanh(uuid)", "kho._dc_thu_tu_nt(jsonb)", "kho._dc_do_thi(jsonb)",
              "kho._dc_thieu(jsonb, jsonb)", "kho._dc_khoa_hoa_don(jsonb)", "kho._dc_khoa_goc(jsonb)", "kho._dc_cap_nguon(jsonb, text, uuid)",
              "kho._dc_bn_tra(uuid, text, text, text, jsonb, text)", "kho._dc_nguon_cua(uuid, uuid)", "kho._dc_xem(jsonb)",
              "kho._dc_lich_su(uuid)", "kho._dc_tep(jsonb, jsonb)", "kho._dc_hop(jsonb, jsonb)")
HAM_LENH = ("kho.dc_luu(text, jsonb)", "kho.dc_xac_nhan(text, jsonb)")
HAM_TRIGGER = ("kho._dc_chi_ghi_them()", "kho._dc_nguon_kiem()", "kho._dc_nguon_phien_ban_kiem()", "kho._dc_phan_kiem()",
               "kho._dc_goc_kiem()", "kho._dc_phien_ban_kiem()", "kho._dc_phien_ban_hoan_tat()", "kho._dc_thanh_phan_kiem()",
               "kho.bien_nhan_dc_chi_chu()", "kho._dc_tap_kiem()")


def _tuple(xs) -> str:
    return "(" + ",".join(f"'{x}'" for x in xs) + ")"


def _mang(xs) -> str:
    return "ARRAY[" + ",".join(f"'{x}'" for x in xs) + "]"


_SHA = "encode(sha256(convert_to({x}::text, 'UTF8')), 'hex')"
_HEX = "~ '^[0-9a-f]{64}$'"
GHI_NHAN_SQL = ("jsonb_build_object('trang_thai', '" + GHI_NHAN_TT + "', 'financial_owner', NULL::text, 'claim', 0, 'proposal', 0, "
                "'source_use', 0, 'obligation', 0, 'ap', 0)")
REQUEST_SQL = "jsonb_build_object('trang_thai', 'CHUA_NOI_M4_04')"

_TIN_CAY = """
            IF NOT master.la_chu_bang('kho.mua_doi_chieu_can_cu'::regclass) OR NOT m4._kt_phien_chu() THEN
                RAISE EXCEPTION 'DC_CHI_MAY_CHU: chỉ đường tin cậy của máy chủ (phiên chủ bảng thật) ghi/đọc đối chiếu căn cứ' """ + _LOI + """;
            END IF;
            ai := master.ktt_danh_tinh();
            IF ai IS NULL THEN
                RAISE EXCEPTION 'DC_DANH_TINH: chưa có danh tính phiên hợp lệ (ID + login hoạt động)' """ + _LOI + """;
            END IF;
            aid := m4.ai_id();"""

# refs của một noi_dung/yêu cầu (mảng thanh_phan) → mảng nguon refs. FIX02: alias SQL có tên riêng + cột tường minh (dc_ref.value), không trùng
# biến PL/pgSQL của hàm nhúng (dc_luu từng khai biến `t` → 42702 AmbiguousColumn với alias `t`).
_REFS = ("(SELECT jsonb_agg(dc_ref.value->'nguon' ORDER BY dc_ref.value->'nguon'->>'kind', dc_ref.value->'nguon'->>'occurrence_id', "
         "coalesce(dc_ref.value->'nguon'->>'part_id', '')) FROM jsonb_array_elements({x}) AS dc_ref(value))")


def _kq(hanh: str, x: str, tt: str, trung: str) -> str:
    return (f"jsonb_build_object('hanh_dong', '{hanh}', 'doi_chieu_id', goc.id, 'phien_ban_id', {x}.id, 'revision', {x}.revision, "
            f"'loai', {x}.loai, 'nhap_id', {x}.nhap_id, 'trang_thai', '{tt}', 'thieu', {x}.thieu, 'graph_sha256', {x}.graph_sha256, "
            f"'noi_dung_sha256', {x}.noi_dung_sha256, 'tap_sha256', {x}.tap_sha256, 'trung_xac_nhan', {trung}, "
            f"'ghi_nhan', {GHI_NHAN_SQL}, 'request', {REQUEST_SQL})")


def _tra(lap_lai: str, kq: str, rid: str) -> str:
    return (f"jsonb_build_object('lap_lai', {lap_lai}, 'ket_qua', {kq}, 'receipt_id', {rid}, 'hien_tai', "
            f"jsonb_build_object('graph_sha256', r->>'graph_sha256', 'khop', (r->>'graph_sha256') IS NOT DISTINCT FROM ({kq}->>'graph_sha256')))")


# kiểm hiện hành từng mục đồ thị dưới khóa: NT toàn vẹn + hiện hành (chứng thực producer của giao dịch này); hóa đơn có phiên bản hiện hành;
# ref ghim đúng phiên bản hiện hành (CAS nguồn). {ma} = mã lỗi khi lệch.
# FIX02: alias tường minh dc_hh/dc_ghim(value) — trước dùng `x`, trùng biến jsonb `x` của dc_luu (cùng lớp lỗi 42702).
_HIEN_HANH = """
            FOR it IN SELECT dc_hh.value FROM jsonb_array_elements(r->'do_thi'->'nguon') AS dc_hh(value) LOOP
                SELECT dc_ghim.value INTO ref FROM jsonb_array_elements({refs}) AS dc_ghim(value)
                    WHERE dc_ghim.value->>'kind' = it->>'kind' AND dc_ghim.value->>'occurrence_id' = it->>'occurrence_id'
                      AND coalesce(dc_ghim.value->>'part_id', '') = coalesce(it->>'part_id', '');
                IF ref IS NULL OR (it->>'current') IS NULL OR (ref->>'source_version_id') IS DISTINCT FROM (it->>'current') THEN
                    RAISE EXCEPTION '{ma_cu}: nguồn đã có phiên bản/phong bì mới hơn phiên bản đang ghim — tải lại' """ + _LOI + """;
                END IF;
                IF it->>'kind' = 'NT' AND (NOT coalesce((it->>'toan_ven')::boolean, false) OR NOT coalesce((it->>'hien_hanh')::boolean, false)) THEN
                    RAISE EXCEPTION 'DC_CAN_KIEM_LAI: nguồn nghiệm thu không còn hiện hành toàn căn cứ (producer 03A) — chờ duyệt/seal lại' """ + _LOI + """;
                END IF;
            END LOOP;"""

_TRUONG_PB = ("doi_chieu_id, phap_nhan_id, revision, truoc_id, loai, nhap_id, noi_dung, noi_dung_sha256, do_thi, graph_sha256, thieu, "
              "tap_sha256, hop_dong_id, doi_tac_id, ly_do, tao_boi, tao_boi_id")


M4_03B_COMMON_SQL = (
    "SET LOCAL check_function_bodies = off",
    # ============================================================== biên nhận chung: thêm module M4 (không bảng thứ hai)
    """DO $$
    DECLARE r record;
    BEGIN
        FOR r IN SELECT c.conname FROM pg_catalog.pg_constraint c WHERE c.conrelid = 'kho.bien_nhan_thao_tac'::regclass AND c.contype = 'c'
                   AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%module%' AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%''M5''%' LOOP
            EXECUTE format('ALTER TABLE kho.bien_nhan_thao_tac DROP CONSTRAINT %I', r.conname);
        END LOOP;
    END $$""",
    "ALTER TABLE kho.bien_nhan_thao_tac ADD CONSTRAINT bien_nhan_thao_tac_module_m4_check CHECK (module IN ('CRM','M1','M2','M5','M4'))",
    f"""CREATE OR REPLACE FUNCTION kho.bien_nhan_dc_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE dc boolean := false;
        BEGIN
            IF TG_OP <> 'DELETE' THEN
                dc := NEW.module = 'M4' OR NEW.operation IN ('{OP_LUU}', '{OP_XAC_NHAN}');
            END IF;
            IF TG_OP <> 'INSERT' THEN
                dc := dc OR OLD.module = 'M4' OR OLD.operation IN ('{OP_LUU}', '{OP_XAC_NHAN}');
            END IF;
            IF dc AND NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'BIEN_NHAN_DC_CHI_CHU: biên nhận đối chiếu căn cứ chỉ do hàm chủ bảng tạo, không ghi trực tiếp' {_LOI};
            END IF;
            -- FIX01: biên nhận DC_* của một gốc chỉ trong namespace bất biến của gốc (module_bien_nhan) — đổi loại nguồn không né được 409
            IF TG_OP = 'INSERT' AND NEW.operation IN ('{OP_LUU}', '{OP_XAC_NHAN}') AND (NEW.result_json->>'doi_chieu_id') IS NOT NULL
               AND NEW.module IS DISTINCT FROM (SELECT g.module_bien_nhan FROM kho.mua_doi_chieu_can_cu g
                                               WHERE g.id::text = NEW.result_json->>'doi_chieu_id') THEN
                RAISE EXCEPTION 'BIEN_NHAN_DC_MODULE: biên nhận đối chiếu phải dùng namespace module gốc của đối chiếu' {_LOI};
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_dc_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.bien_nhan_thao_tac FOR EACH ROW EXECUTE FUNCTION kho.bien_nhan_dc_chi_chu()",
    # ============================================================== identity nguồn: gốc / phiên bản / phần (append-only, chỉ tham chiếu ID có thật)
    f"""CREATE TABLE kho.mua_nguon_kinh_te (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai IN {_tuple(LOAI_NGUON)}),
        occurrence_id uuid NOT NULL,
        cho_id uuid REFERENCES m4.duyet_kt_cho(id),
        hoa_don_id uuid,
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK ((loai = 'NT' AND cho_id IS NOT NULL AND hoa_don_id IS NULL AND occurrence_id = cho_id)
               OR (loai = 'HOA_DON' AND hoa_don_id IS NOT NULL AND cho_id IS NULL AND occurrence_id = hoa_don_id)),
        FOREIGN KEY (phap_nhan_id, hoa_don_id) REFERENCES kho.hoa_don_danh_tinh (phap_nhan_id, id),
        UNIQUE (phap_nhan_id, loai, occurrence_id),
        UNIQUE (id, phap_nhan_id),
        UNIQUE (id, phap_nhan_id, loai))""",
    f"""CREATE TABLE kho.mua_nguon_kinh_te_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguon_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN {_tuple(LOAI_NGUON)}),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        truoc_id uuid UNIQUE,
        cho_id uuid,
        phong_bi_id uuid,
        seal_id uuid REFERENCES m4.duyet_seal(id),
        kt_revision_id uuid,
        kt_xac_nhan_id uuid,
        hoa_don_id uuid,
        hoa_don_phien_ban_id uuid,
        quan_sat_id uuid,
        su_kien jsonb NOT NULL CHECK (jsonb_typeof(su_kien) = 'object'),
        semantic_sha256 text NOT NULL CHECK (semantic_sha256 {_HEX}),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK ((phien_ban = 1) = (truoc_id IS NULL)),
        CHECK ((loai = 'NT' AND cho_id IS NOT NULL AND phong_bi_id IS NOT NULL AND seal_id IS NOT NULL
                AND hoa_don_id IS NULL AND hoa_don_phien_ban_id IS NULL AND quan_sat_id IS NULL)
               OR (loai = 'HOA_DON' AND hoa_don_id IS NOT NULL AND hoa_don_phien_ban_id IS NOT NULL AND cho_id IS NULL AND phong_bi_id IS NULL
                   AND seal_id IS NULL AND kt_revision_id IS NULL AND kt_xac_nhan_id IS NULL)),
        FOREIGN KEY (nguon_id, phap_nhan_id, loai) REFERENCES kho.mua_nguon_kinh_te (id, phap_nhan_id, loai),
        FOREIGN KEY (phong_bi_id, cho_id) REFERENCES m4.duyet_kt_phong_bi (id, cho_id),
        FOREIGN KEY (kt_revision_id, cho_id) REFERENCES m4.kt_xac_nhan (id, cho_id),
        FOREIGN KEY (kt_xac_nhan_id, phong_bi_id) REFERENCES m4.kt_xac_nhan (id, phong_bi_id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id) REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, quan_sat_id) REFERENCES kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id),
        UNIQUE (nguon_id, phien_ban),
        UNIQUE (nguon_id, semantic_sha256),
        UNIQUE (id, nguon_id, phap_nhan_id))""",
    """ALTER TABLE kho.mua_nguon_kinh_te_phien_ban ADD CONSTRAINT mua_nguon_kinh_te_phien_ban_truoc_fk
        FOREIGN KEY (truoc_id, nguon_id, phap_nhan_id) REFERENCES kho.mua_nguon_kinh_te_phien_ban (id, nguon_id, phap_nhan_id)""",
    f"""CREATE TABLE kho.mua_nguon_phan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguon_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN {_tuple(LOAI_NGUON)}),
        loai_phan text NOT NULL CHECK (loai_phan IN {_tuple(LOAI_PHAN)}),
        hoa_don_id uuid,
        dong_danh_tinh_id uuid,
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK ((loai = 'HOA_DON') = (hoa_don_id IS NOT NULL)),
        CHECK ((loai_phan = 'TOAN_BO' AND dong_danh_tinh_id IS NULL)
               OR (loai_phan = 'DONG_LOGIC' AND loai = 'HOA_DON' AND dong_danh_tinh_id IS NOT NULL)),
        FOREIGN KEY (nguon_id, phap_nhan_id, loai) REFERENCES kho.mua_nguon_kinh_te (id, phap_nhan_id, loai),
        FOREIGN KEY (phap_nhan_id, dong_danh_tinh_id, hoa_don_id) REFERENCES kho.hoa_don_dong_danh_tinh (phap_nhan_id, id, hoa_don_id),
        UNIQUE (id, nguon_id, phap_nhan_id))""",
    "CREATE UNIQUE INDEX mua_nguon_phan_toan_bo_uq ON kho.mua_nguon_phan (nguon_id) WHERE loai_phan = 'TOAN_BO'",
    "CREATE UNIQUE INDEX mua_nguon_phan_dong_uq ON kho.mua_nguon_phan (nguon_id, dong_danh_tinh_id) WHERE loai_phan = 'DONG_LOGIC'",
    # ============================================================== đối chiếu căn cứ: gốc + phiên bản append-only + thành phần (FK tổ hợp) + nhật ký
    f"""CREATE TABLE kho.mua_doi_chieu_can_cu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        khoa_goc_sha256 text NOT NULL CHECK (khoa_goc_sha256 {_HEX}),
        module_bien_nhan text NOT NULL CHECK (module_bien_nhan IN {_tuple(MODULE_BIEN_NHAN)}),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, khoa_goc_sha256),
        UNIQUE (id, phap_nhan_id))""",
    f"""CREATE TABLE kho.mua_doi_chieu_can_cu_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        doi_chieu_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        truoc_id uuid UNIQUE,
        loai text NOT NULL CHECK (loai IN {_tuple(LOAI)}),
        nhap_id uuid UNIQUE,
        noi_dung jsonb NOT NULL CHECK (jsonb_typeof(noi_dung) = 'object'),
        noi_dung_sha256 text NOT NULL CHECK (noi_dung_sha256 {_HEX}),
        do_thi jsonb NOT NULL CHECK (jsonb_typeof(do_thi) = 'object'),
        graph_sha256 text NOT NULL CHECK (graph_sha256 {_HEX}),
        thieu jsonb NOT NULL CHECK (jsonb_typeof(thieu) = 'array'),
        tap_sha256 text NOT NULL CHECK (tap_sha256 {_HEX}),
        hop_dong_id uuid,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) >= 1 AND length(ly_do) <= 2000),
        ghi_nhan text NOT NULL DEFAULT '{GHI_NHAN_TT}' CHECK (ghi_nhan = '{GHI_NHAN_TT}'),
        financial_owner text CHECK (financial_owner IS NULL),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK ((revision = 1) = (truoc_id IS NULL)),
        CHECK ((loai = 'XAC_NHAN') = (nhap_id IS NOT NULL)),
        CHECK (loai = 'NHAP' OR thieu = '[]'::jsonb),
        FOREIGN KEY (doi_chieu_id, phap_nhan_id) REFERENCES kho.mua_doi_chieu_can_cu (id, phap_nhan_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        UNIQUE (doi_chieu_id, revision),
        UNIQUE (id, doi_chieu_id),
        UNIQUE (id, doi_chieu_id, phap_nhan_id))""",
    """ALTER TABLE kho.mua_doi_chieu_can_cu_phien_ban ADD CONSTRAINT mua_doi_chieu_can_cu_phien_ban_truoc_fk
        FOREIGN KEY (truoc_id, doi_chieu_id) REFERENCES kho.mua_doi_chieu_can_cu_phien_ban (id, doi_chieu_id)""",
    """ALTER TABLE kho.mua_doi_chieu_can_cu_phien_ban ADD CONSTRAINT mua_doi_chieu_can_cu_phien_ban_nhap_fk
        FOREIGN KEY (nhap_id, doi_chieu_id) REFERENCES kho.mua_doi_chieu_can_cu_phien_ban (id, doi_chieu_id)""",
    f"""CREATE TABLE kho.mua_doi_chieu_can_cu_thanh_phan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL,
        doi_chieu_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        nguon_id uuid NOT NULL,
        nguon_phien_ban_id uuid NOT NULL,
        phan_id uuid NOT NULL,
        phan text NOT NULL CHECK (phan IN {_tuple(PHAN)}),
        ty_le_khai text CHECK (ty_le_khai IS NULL OR (length(btrim(ty_le_khai)) >= 1 AND length(ty_le_khai) <= 100)),
        ty_le_trang_thai text NOT NULL CHECK (ty_le_trang_thai IN {_tuple(TY_LE_TRANG_THAI)}),
        CHECK ((phan = 'TOAN_PHAN' AND ty_le_khai IS NULL AND ty_le_trang_thai = 'KHONG_AP_DUNG')
               OR (phan = 'MOT_PHAN' AND ((ty_le_khai IS NULL AND ty_le_trang_thai = 'THIEU')
                                          OR (ty_le_khai IS NOT NULL AND ty_le_trang_thai = 'KHAI_BAO_THO_CHUA_SCALE')))),
        FOREIGN KEY (phien_ban_id, doi_chieu_id, phap_nhan_id) REFERENCES kho.mua_doi_chieu_can_cu_phien_ban (id, doi_chieu_id, phap_nhan_id),
        FOREIGN KEY (nguon_phien_ban_id, nguon_id, phap_nhan_id) REFERENCES kho.mua_nguon_kinh_te_phien_ban (id, nguon_id, phap_nhan_id),
        FOREIGN KEY (phan_id, nguon_id, phap_nhan_id) REFERENCES kho.mua_nguon_phan (id, nguon_id, phap_nhan_id),
        UNIQUE (phien_ban_id, phan_id))""",
    """CREATE TABLE kho.mua_doi_chieu_can_cu_nhat_ky (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        doi_chieu_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        hanh_dong text NOT NULL CHECK (hanh_dong IN ('LUU','XAC_NHAN')),
        boi text NOT NULL,
        boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        chi_tiet jsonb NOT NULL CHECK (jsonb_typeof(chi_tiet) = 'object'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phien_ban_id, doi_chieu_id, phap_nhan_id) REFERENCES kho.mua_doi_chieu_can_cu_phien_ban (id, doi_chieu_id, phap_nhan_id))""",
    # FIX01: alias tập nguồn chuẩn → gốc ổn định (ghi thêm; một tập thuộc đúng một gốc trong PN; không ràng buộc theo nguồn đơn lẻ → nhiều-nhiều)
    f"""CREATE TABLE kho.mua_doi_chieu_can_cu_tap (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        tap_sha256 text NOT NULL CHECK (tap_sha256 {_HEX}),
        doi_chieu_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (doi_chieu_id, phap_nhan_id) REFERENCES kho.mua_doi_chieu_can_cu (id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, doi_chieu_id, phap_nhan_id) REFERENCES kho.mua_doi_chieu_can_cu_phien_ban (id, doi_chieu_id, phap_nhan_id),
        UNIQUE (phap_nhan_id, tap_sha256))""",
    # ============================================================== trigger: chỉ chủ bảng, chỉ ghi thêm, định danh tổ hợp
    f"""CREATE OR REPLACE FUNCTION kho._dc_chi_ghi_them() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'DC_BAT_BIEN: % chỉ ghi thêm, không sửa/xóa', TG_TABLE_NAME {_LOI};
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'DC_CHI_CHU: % chỉ ghi qua hàm định nghĩa trên kết nối chủ bảng', TG_TABLE_NAME {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON kho.{t} FOR EACH ROW EXECUTE FUNCTION kho._dc_chi_ghi_them()"
      for t in BANG),
    f"""CREATE OR REPLACE FUNCTION kho._dc_nguon_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE v_pn uuid;
        BEGIN
            IF NEW.loai = 'NT' THEN
                SELECT c.phap_nhan_id INTO v_pn FROM m4.duyet_kt_cho c WHERE c.id = NEW.cho_id;
                IF v_pn IS DISTINCT FROM NEW.phap_nhan_id THEN
                    RAISE EXCEPTION 'DC_NGUON_SAI: gốc nguồn nghiệm thu không đúng pháp nhân của gốc KT' {_LOI};
                END IF;
            END IF;
            IF NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'DC_DANH_TINH: người tạo phải là phiên hiện tại' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_nguon_kinh_te_kiem BEFORE INSERT ON kho.mua_nguon_kinh_te FOR EACH ROW EXECUTE FUNCTION kho._dc_nguon_kiem()",
    f"""CREATE OR REPLACE FUNCTION kho._dc_nguon_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE g kho.mua_nguon_kinh_te%ROWTYPE; cuoi kho.mua_nguon_kinh_te_phien_ban%ROWTYPE; v_loai text;
        BEGIN
            SELECT * INTO g FROM kho.mua_nguon_kinh_te x WHERE x.id = NEW.nguon_id;
            IF g.id IS NULL OR NEW.cho_id IS DISTINCT FROM g.cho_id OR NEW.hoa_don_id IS DISTINCT FROM g.hoa_don_id THEN
                RAISE EXCEPTION 'DC_NGUON_SAI: phiên bản nguồn không thuộc đúng gốc nguồn' {_LOI};
            END IF;
            IF NEW.semantic_sha256 IS DISTINCT FROM {_SHA.format(x="NEW.su_kien")}
               OR (NEW.su_kien->>'current') IS DISTINCT FROM coalesce(NEW.phong_bi_id, NEW.hoa_don_phien_ban_id)::text THEN
                RAISE EXCEPTION 'DC_NGUON_SAI: dữ kiện ghim không khớp phiên bản nguồn' {_LOI};
            END IF;
            IF NEW.kt_xac_nhan_id IS NOT NULL THEN
                SELECT x.loai INTO v_loai FROM m4.kt_xac_nhan x WHERE x.id = NEW.kt_xac_nhan_id;
                IF v_loai IS DISTINCT FROM 'XAC_NHAN' THEN
                    RAISE EXCEPTION 'DC_NGUON_SAI: kt_xac_nhan_id phải là revision XAC_NHAN của phong bì' {_LOI};
                END IF;
            END IF;
            SELECT * INTO cuoi FROM kho.mua_nguon_kinh_te_phien_ban x WHERE x.nguon_id = NEW.nguon_id ORDER BY x.phien_ban DESC LIMIT 1;
            IF NEW.phien_ban IS DISTINCT FROM coalesce(cuoi.phien_ban, 0) + 1 OR NEW.truoc_id IS DISTINCT FROM cuoi.id THEN
                RAISE EXCEPTION 'DC_REVISION_CU: phiên bản nguồn phải nối tiếp phiên bản mới nhất' {_LOI};
            END IF;
            IF NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'DC_DANH_TINH: người tạo phải là phiên hiện tại' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_nguon_kinh_te_phien_ban_kiem BEFORE INSERT ON kho.mua_nguon_kinh_te_phien_ban FOR EACH ROW EXECUTE FUNCTION kho._dc_nguon_phien_ban_kiem()",
    f"""CREATE OR REPLACE FUNCTION kho._dc_phan_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE g kho.mua_nguon_kinh_te%ROWTYPE;
        BEGIN
            SELECT * INTO g FROM kho.mua_nguon_kinh_te x WHERE x.id = NEW.nguon_id;
            IF g.id IS NULL OR NEW.hoa_don_id IS DISTINCT FROM g.hoa_don_id THEN
                RAISE EXCEPTION 'DC_NGUON_SAI: phần nguồn không thuộc đúng gốc nguồn' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_nguon_phan_kiem BEFORE INSERT ON kho.mua_nguon_phan FOR EACH ROW EXECUTE FUNCTION kho._dc_phan_kiem()",
    f"""CREATE OR REPLACE FUNCTION kho._dc_goc_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'DC_DANH_TINH: người tạo phải là phiên hiện tại' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_doi_chieu_can_cu_kiem BEFORE INSERT ON kho.mua_doi_chieu_can_cu FOR EACH ROW EXECUTE FUNCTION kho._dc_goc_kiem()",
    # phiên bản đối chiếu: SHA nội dung/đồ thị tính lại; revision nối tiếp; HĐ/đối tác = đúng dữ kiện resolve trong đồ thị; XAC_NHAN = sao y nháp mới nhất
    f"""CREATE OR REPLACE FUNCTION kho._dc_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE cuoi kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; n kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; v_hd text; v_dt text;
        BEGIN
            IF NEW.noi_dung_sha256 IS DISTINCT FROM {_SHA.format(x="NEW.noi_dung")} OR NEW.graph_sha256 IS DISTINCT FROM {_SHA.format(x="NEW.do_thi")} THEN
                RAISE EXCEPTION 'DC_TOAN_VEN: SHA nội dung/đồ thị không khớp dữ liệu ghi' {_LOI};
            END IF;
            IF NEW.tap_sha256 IS DISTINCT FROM kho._dc_khoa_goc({_REFS.format(x="NEW.noi_dung->'thanh_phan'")}) THEN
                RAISE EXCEPTION 'DC_TOAN_VEN: tap_sha256 phải là digest chuẩn tập nguồn (kind, occurrence, part) của nội dung' {_LOI};
            END IF;
            IF NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'DC_DANH_TINH: người tạo phải là phiên hiện tại' {_LOI};
            END IF;
            SELECT * INTO cuoi FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.doi_chieu_id = NEW.doi_chieu_id ORDER BY x.revision DESC LIMIT 1;
            IF NEW.revision IS DISTINCT FROM coalesce(cuoi.revision, 0) + 1 OR NEW.truoc_id IS DISTINCT FROM cuoi.id THEN
                RAISE EXCEPTION 'DC_REVISION_CU: revision đối chiếu phải nối tiếp revision mới nhất' {_LOI};
            END IF;
            SELECT CASE WHEN count(DISTINCT i->>'hop_dong_id') = 1 THEN min(i->>'hop_dong_id') END,
                   CASE WHEN count(DISTINCT i->>'hop_dong_id') = 1 THEN min(i->>'doi_tac_id') END
                INTO v_hd, v_dt FROM jsonb_array_elements(NEW.do_thi->'nguon') i WHERE i->>'kind' = 'NT';
            IF NEW.hop_dong_id::text IS DISTINCT FROM v_hd OR NEW.doi_tac_id::text IS DISTINCT FROM v_dt THEN
                RAISE EXCEPTION 'DC_TOAN_VEN: HĐ/đối tác của phiên bản phải là dữ kiện master resolve từ nguồn nghiệm thu' {_LOI};
            END IF;
            IF NEW.loai = 'XAC_NHAN' THEN
                SELECT * INTO n FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.id = NEW.nhap_id;
                IF n.id IS NULL OR n.loai <> 'NHAP' OR n.id IS DISTINCT FROM cuoi.id OR NEW.thieu <> '[]'::jsonb
                   OR ROW(n.noi_dung, n.graph_sha256, n.do_thi, n.tap_sha256, n.hop_dong_id, n.doi_tac_id, n.ly_do)
                      IS DISTINCT FROM ROW(NEW.noi_dung, NEW.graph_sha256, NEW.do_thi, NEW.tap_sha256, NEW.hop_dong_id, NEW.doi_tac_id, NEW.ly_do) THEN
                    RAISE EXCEPTION 'DC_XAC_NHAN_KHAC_NHAP: xác nhận phải sao y đúng bản nháp mới nhất đã lưu, đủ điều kiện' {_LOI};
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_doi_chieu_can_cu_phien_ban_kiem BEFORE INSERT ON kho.mua_doi_chieu_can_cu_phien_ban FOR EACH ROW EXECUTE FUNCTION kho._dc_phien_ban_kiem()",
    # thành phần: chỉ thêm vào phiên bản tạo trong CHÍNH giao dịch này (không gắn thêm vào lịch sử)
    f"""CREATE OR REPLACE FUNCTION kho._dc_thanh_phan_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE v_xmin text;
        BEGIN
            SELECT x.xmin::text INTO v_xmin FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.id = NEW.phien_ban_id;
            IF v_xmin IS DISTINCT FROM (pg_catalog.txid_current() % 4294967296)::text THEN
                RAISE EXCEPTION 'DC_BAT_BIEN: thành phần chỉ ghi cùng giao dịch tạo phiên bản đối chiếu' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_doi_chieu_can_cu_thanh_phan_kiem BEFORE INSERT ON kho.mua_doi_chieu_can_cu_thanh_phan FOR EACH ROW EXECUTE FUNCTION kho._dc_thanh_phan_kiem()",
    # FIX01 alias: chỉ trỏ đúng phiên bản (cùng gốc, cùng tap_sha256) tạo trong CHÍNH giao dịch này; người tạo = phiên hiện tại
    f"""CREATE OR REPLACE FUNCTION kho._dc_tap_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE v kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; v_xmin text;
        BEGIN
            SELECT * INTO v FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.id = NEW.phien_ban_id;
            SELECT x.xmin::text INTO v_xmin FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.id = NEW.phien_ban_id;
            IF v.id IS NULL OR v.doi_chieu_id IS DISTINCT FROM NEW.doi_chieu_id OR v.tap_sha256 IS DISTINCT FROM NEW.tap_sha256
               OR v_xmin IS DISTINCT FROM (pg_catalog.txid_current() % 4294967296)::text THEN
                RAISE EXCEPTION 'DC_BAT_BIEN: alias tập nguồn chỉ ghi cùng giao dịch tạo revision mang đúng tập đó' {_LOI};
            END IF;
            IF NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'DC_DANH_TINH: người tạo phải là phiên hiện tại' {_LOI};
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_doi_chieu_can_cu_tap_kiem BEFORE INSERT ON kho.mua_doi_chieu_can_cu_tap FOR EACH ROW EXECUTE FUNCTION kho._dc_tap_kiem()",
    # ============================================================== quyền (không raise / raise) — kiểm TRƯỚC lookup nội dung
    f"""CREATE OR REPLACE FUNCTION kho._dc_m2_doc(p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT p_pn IS NOT NULL AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(p_pn, 'M2')
               AND master.ktt_co_vai(p_pn, {_mang(VAI_TRO_M2_DOC)}, NULL)
        $$""",
    f"""CREATE OR REPLACE FUNCTION kho._dc_kt_toan_cuc(p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT p_pn IS NOT NULL AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_co_vai(p_pn, {_mang(VAI_TRO_KT)}, NULL)
        $$""",
    """CREATE OR REPLACE FUNCTION kho.dc_doc_hoa_don(p_hoa_don uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM kho.hoa_don_danh_tinh d WHERE d.id = p_hoa_don AND kho._dc_m2_doc(d.phap_nhan_id))
        $$""",
    f"""CREATE OR REPLACE FUNCTION kho._dc_quyen(p_refs jsonb, p_ghi boolean) RETURNS void
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE e jsonb; v_pn uuid;
        BEGIN
            IF master.ktt_danh_tinh() IS NULL THEN
                RAISE EXCEPTION 'DC_DANH_TINH: chưa có danh tính phiên hợp lệ' {_LOI};
            END IF;
            IF p_refs IS NULL OR jsonb_typeof(p_refs) <> 'array' OR jsonb_array_length(p_refs) = 0 THEN
                RAISE EXCEPTION 'DC_THAM_SO_SAI: cần ít nhất một nguồn' {_LOI};
            END IF;
            FOR e IN SELECT x FROM jsonb_array_elements(p_refs) x LOOP
                IF e->>'kind' = 'NT' THEN
                    PERFORM m4.kt_kiem((e->>'occurrence_id')::uuid, 'XEM');
                ELSIF e->>'kind' = 'HOA_DON' THEN
                    v_pn := NULL;
                    SELECT d.phap_nhan_id INTO v_pn FROM kho.hoa_don_danh_tinh d WHERE d.id = (e->>'occurrence_id')::uuid;
                    IF v_pn IS NULL OR NOT master.ktt_duoc(v_pn, 'M2') THEN
                        RAISE EXCEPTION 'DC_KHONG_THAY: không thấy hóa đơn (hoặc ngoài phạm vi hiện hành)' {_LOI};
                    END IF;
                    IF NOT kho._dc_m2_doc(v_pn) THEN
                        RAISE EXCEPTION 'DC_PHAM_VI: cần quyền M2_READ hiện hành trên pháp nhân của hóa đơn' {_LOI};
                    END IF;
                    IF p_ghi AND NOT kho._dc_kt_toan_cuc(v_pn) THEN
                        RAISE EXCEPTION 'DC_PHAM_VI: lệnh ghi đối chiếu cần vai trò KE_TOAN/KE_TOAN_TRUONG hiện hành (CFO/XEM chỉ xem)' {_LOI};
                    END IF;
                ELSE
                    RAISE EXCEPTION 'DC_THAM_SO_SAI: loại nguồn không hợp lệ' {_LOI};
                END IF;
            END LOOP;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho._dc_doc_duoc(p_refs jsonb) RETURNS boolean
        LANGUAGE sql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        SELECT master.ktt_danh_tinh() IS NOT NULL AND p_refs IS NOT NULL AND jsonb_typeof(p_refs) = 'array'
               AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p_refs) e
                               WHERE NOT coalesce(CASE e->>'kind'
                                   WHEN 'NT' THEN m4.kt_doc_cho((e->>'occurrence_id')::uuid)
                                   WHEN 'HOA_DON' THEN (SELECT kho._dc_m2_doc(d.phap_nhan_id) FROM kho.hoa_don_danh_tinh d
                                                        WHERE d.id = (e->>'occurrence_id')::uuid)
                                   ELSE false END, false))
        $$""",
    # ============================================================== chứng thực hiện hành NT của giao dịch này (sau producer 03A)
    f"""CREATE OR REPLACE FUNCTION kho._dc_nt_ghi(p_cho uuid) RETURNS jsonb
        LANGUAGE plpgsql AS $$
        DECLARE h jsonb; m jsonb;
        BEGIN
            IF NOT m4._kt_phien_chu() THEN
                RAISE EXCEPTION 'DC_CHI_MAY_CHU: chứng thực hiện hành chỉ ghi trên phiên chủ bảng của máy chủ' {_LOI};
            END IF;
            PERFORM m4.kt_kiem(p_cho, 'XEM');
            h := m4._kt_hien_hanh(p_cho);
            IF h IS NULL THEN
                RAISE EXCEPTION 'DC_KHONG_THAY: không thấy gốc nguồn nghiệm thu' {_LOI};
            END IF;
            m := nullif(pg_catalog.current_setting('{GUC_NT}', true), '')::jsonb;
            IF m IS NULL OR (m->>'pid') IS DISTINCT FROM pg_catalog.pg_backend_pid()::text
               OR (m->>'txid') IS DISTINCT FROM pg_catalog.txid_current()::text
               OR (m->>'actor') IS DISTINCT FROM nullif(pg_catalog.current_setting('ktt.nguoi_dung_id', true), '') THEN
                m := pg_catalog.jsonb_build_object('pid', pg_catalog.pg_backend_pid()::text, 'txid', pg_catalog.txid_current()::text,
                                                   'actor', nullif(pg_catalog.current_setting('ktt.nguoi_dung_id', true), ''), 'cho', '{{}}'::jsonb);
            END IF;
            m := pg_catalog.jsonb_set(m, ARRAY['cho', p_cho::text],
                                      pg_catalog.jsonb_build_object('phong_bi_id', h->>'phong_bi_id',
                                                                    'hien_hanh', coalesce((h->>'hien_hanh')::boolean, false),
                                                                    'toan_ven', coalesce((h->>'toan_ven')::boolean, false),
                                                                    'ly_do', h->>'ly_do'));
            PERFORM pg_catalog.set_config('{GUC_NT}', m::text, true);
            RETURN h;
        END $$""",
    f"""CREATE OR REPLACE FUNCTION kho._dc_nt_hien_hanh(p_cho uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE m jsonb := nullif(current_setting('{GUC_NT}', true), '')::jsonb;
        BEGIN
            IF m IS NULL OR NOT m4._kt_phien_chu() OR (m->>'pid') IS DISTINCT FROM pg_backend_pid()::text
               OR (m->>'txid') IS DISTINCT FROM txid_current()::text
               OR (m->>'actor') IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '') THEN
                RETURN NULL;
            END IF;
            RETURN m->'cho'->(p_cho::text);
        END $$""",
    # thứ tự gốc NT cho Python khóa/ghim: quyền đọc TRƯỚC, rồi HĐ sorted → gốc sorted
    """CREATE OR REPLACE FUNCTION kho._dc_thu_tu_nt(p_refs jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        BEGIN
            PERFORM kho._dc_quyen(p_refs, false);
            RETURN (SELECT coalesce(jsonb_agg(c.id::text ORDER BY c.hop_dong_id, c.id), '[]'::jsonb) FROM m4.duyet_kt_cho c
                    WHERE c.id IN (SELECT DISTINCT (e->>'occurrence_id')::uuid FROM jsonb_array_elements(p_refs) e WHERE e->>'kind' = 'NT'));
        END $$""",
    # ============================================================== đồ thị hiện hành (dữ kiện thật của nguồn; KHÔNG gồm số tiền, KHÔNG gồm ghim của body)
    f"""CREATE OR REPLACE FUNCTION kho._dc_do_thi(p_refs jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE e jsonb; ds jsonb := '[]'::jsonb; it jsonb; g jsonb; c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE;
                s m4.duyet_seal%ROWTYPE; k m4.kt_xac_nhan%ROWTYPE; h jsonb; v_dt uuid; v_mst text; v_dtpb integer; v_xn uuid;
                d kho.hoa_don_danh_tinh%ROWTYPE; v_cur uuid; v_sem text; v_mb text; v_part uuid; v_key text; v_cau jsonb; n1 integer; n2 integer;
        BEGIN
            IF p_refs IS NULL OR jsonb_typeof(p_refs) <> 'array' OR jsonb_array_length(p_refs) = 0 OR jsonb_array_length(p_refs) > {TOI_DA_THANH_PHAN} THEN
                RAISE EXCEPTION 'DC_THAM_SO_SAI: cần 1..{TOI_DA_THANH_PHAN} nguồn' {_LOI};
            END IF;
            SELECT count(*), count(DISTINCT (x->>'kind') || '|' || (x->>'occurrence_id') || '|' || coalesce(x->>'part_id', '')) INTO n1, n2
                FROM jsonb_array_elements(p_refs) x;
            IF n1 <> n2 THEN
                RAISE EXCEPTION 'DC_THAM_SO_SAI: nguồn/phần bị lặp' {_LOI};
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_refs) x JOIN jsonb_array_elements(p_refs) y
                       ON x->>'kind' = 'HOA_DON' AND y->>'kind' = 'HOA_DON' AND x->>'occurrence_id' = y->>'occurrence_id'
                       WHERE x->>'part_id' IS NULL AND y->>'part_id' IS NOT NULL) THEN
                RAISE EXCEPTION 'DC_PHAN_SAI: không khai cả toàn bộ hóa đơn và dòng của chính hóa đơn đó' {_LOI};
            END IF;
            FOR e IN SELECT x FROM jsonb_array_elements(p_refs) x ORDER BY x->>'kind', x->>'occurrence_id', coalesce(x->>'part_id', '') LOOP
                IF e->>'kind' = 'NT' THEN
                    IF e->>'part_id' IS NOT NULL THEN
                        RAISE EXCEPTION 'DC_PHAN_SAI: nguồn nghiệm thu chỉ có phần TOAN_BO (không bịa dòng từ STT/PDF/hash)' {_LOI};
                    END IF;
                    SELECT * INTO c FROM m4.duyet_kt_cho x WHERE x.id = (e->>'occurrence_id')::uuid;
                    IF c.id IS NULL THEN
                        RAISE EXCEPTION 'DC_KHONG_THAY: không thấy gốc nguồn nghiệm thu' {_LOI};
                    END IF;
                    SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = c.id ORDER BY x.thu_tu DESC LIMIT 1;
                    SELECT * INTO s FROM m4.duyet_seal x WHERE x.id = b.seal_id;
                    v_dt := NULL; v_mst := NULL; v_dtpb := NULL; v_xn := NULL;
                    SELECT hd.doi_tac_id, nullif(btrim(t.mst), ''), t.phien_ban INTO v_dt, v_mst, v_dtpb
                        FROM master.hop_dong hd LEFT JOIN master.doi_tac t ON t.id = hd.doi_tac_id WHERE hd.id = c.hop_dong_id;
                    SELECT * INTO k FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id ORDER BY x.revision DESC LIMIT 1;
                    SELECT x.id INTO v_xn FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id AND x.loai = 'XAC_NHAN';
                    h := kho._dc_nt_hien_hanh(c.id);
                    it := jsonb_build_object('kind', 'NT', 'occurrence_id', c.id, 'part_id', NULL::uuid, 'part_kind', 'TOAN_BO', 'current', b.id,
                        'phap_nhan_id', c.phap_nhan_id, 'du_an_id', c.du_an_id, 'hop_dong_id', c.hop_dong_id, 'dot_id', c.dot_id,
                        'doi_tac_id', v_dt, 'doi_tac_mst', v_mst, 'doi_tac_phien_ban', v_dtpb,
                        'phong_bi_sha256', b.noi_dung_sha256, 'seal_id', s.id, 'version_id', s.phien_ban_id, 'ket_luan_id', s.ket_luan_id,
                        'pdf_id', s.pdf_id, 'pdf_sha256', s.pdf_sha256, 'graph_sha256', s.graph_sha256,
                        'toan_ven', b.id IS NOT NULL AND m4._kt_toan_ven(b.id),
                        'hien_hanh', coalesce((h->>'hien_hanh')::boolean, false) AND (h->>'phong_bi_id') IS NOT DISTINCT FROM b.id::text,
                        'ly_do_hold', CASE WHEN h IS NULL THEN 'CHUA_GHIM_CHUNG_THUC' ELSE h->>'ly_do' END,
                        'kt_revision_id', k.id, 'kt_revision', k.revision, 'kt_xac_nhan_id', v_xn);
                ELSIF e->>'kind' = 'HOA_DON' THEN
                    SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = (e->>'occurrence_id')::uuid;
                    IF d.id IS NULL THEN
                        RAISE EXCEPTION 'DC_KHONG_THAY: không thấy hóa đơn' {_LOI};
                    END IF;
                    v_cur := NULL; v_sem := NULL; v_mb := NULL; v_key := NULL; v_cau := '[]'::jsonb;
                    SELECT o.phien_ban_id INTO v_cur FROM kho.hoa_don_quan_sat o WHERE o.id = d.latest_observation_id;
                    SELECT v.semantic_sha256, v.money_basis_state INTO v_sem, v_mb FROM kho.hoa_don_phien_ban v WHERE v.id = v_cur;
                    v_part := nullif(e->>'part_id', '')::uuid;
                    IF v_part IS NOT NULL THEN
                        SELECT x.logical_line_key INTO v_key FROM kho.hoa_don_dong_danh_tinh x WHERE x.id = v_part AND x.hoa_don_id = d.id;
                        IF v_key IS NULL THEN
                            RAISE EXCEPTION 'DC_PHAN_SAI: dòng logic không thuộc hóa đơn (không dùng UUID giả)' {_LOI};
                        END IF;
                        SELECT coalesce(jsonb_agg(jsonb_build_object('id', x.id, 'source_dong_id', x.source_dong_id,
                                                                     'field_state_sha256', x.field_state_sha256) ORDER BY x.source_ordinal, x.id), '[]'::jsonb)
                            INTO v_cau FROM kho.hoa_don_dong_phien_ban x
                            WHERE x.hoa_don_id = d.id AND x.dong_danh_tinh_id = v_part AND x.hoa_don_phien_ban_id = v_cur;
                    END IF;
                    it := jsonb_build_object('kind', 'HOA_DON', 'occurrence_id', d.id, 'part_id', v_part,
                        'part_kind', CASE WHEN v_part IS NULL THEN 'TOAN_BO' ELSE 'DONG_LOGIC' END, 'current', v_cur,
                        'phap_nhan_id', d.phap_nhan_id, 'mst_ban', d.mst_ban, 'mau_so', d.mau_so, 'ky_hieu', d.ky_hieu, 'so_chuan', d.so_chuan,
                        'quan_sat_id', d.latest_observation_id, 'semantic_sha256', v_sem, 'eligible_content_id', d.eligible_content_id,
                        'op_graph_sha256', kho.m2_co_so(d.id)->>'graph_sha256', 'logical_line_key', v_key, 'cau_noi', v_cau,
                        'money_basis_state', v_mb);
                ELSE
                    RAISE EXCEPTION 'DC_THAM_SO_SAI: loại nguồn không hợp lệ' {_LOI};
                END IF;
                ds := ds || jsonb_build_array(it);
            END LOOP;
            g := jsonb_build_object('contract', '{CONTRACT_DO_THI}', 'nguon', ds);
            RETURN jsonb_build_object('do_thi', g, 'graph_sha256', {_SHA.format(x="g")});
        END $$""",
    # điều kiện căn cứ còn thiếu (gương Python ghi_nhan_chung.thieu) — dữ kiện master/nguồn thật, không lời khẳng định của body
    """CREATE OR REPLACE FUNCTION kho._dc_thieu(p_g jsonb, p_tp jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, pg_temp AS $$
        DECLARE x text[] := ARRAY[]::text[]; n_nt integer; n_hd integer; n_hdg integer; v_mst text;
        BEGIN
            SELECT count(*) FILTER (WHERE i->>'kind' = 'NT'), count(*) FILTER (WHERE i->>'kind' = 'HOA_DON'),
                   count(DISTINCT i->>'hop_dong_id') FILTER (WHERE i->>'kind' = 'NT')
                INTO n_nt, n_hd, n_hdg FROM jsonb_array_elements(p_g->'nguon') i;
            IF n_nt = 0 THEN
                x := array_append(x, 'THIEU_NT');
            END IF;
            IF n_hd = 0 THEN
                x := array_append(x, 'THIEU_HOA_DON');
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'NT'
                       AND (NOT coalesce((i->>'hien_hanh')::boolean, false) OR NOT coalesce((i->>'toan_ven')::boolean, false))) THEN
                x := array_append(x, 'NT_KHONG_HIEN_HANH');
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'NT' AND i->>'kt_xac_nhan_id' IS NULL) THEN
                x := array_append(x, 'NT_CHUA_KT_XAC_NHAN');
            END IF;
            IF n_hdg > 1 THEN
                x := array_append(x, 'NT_KHAC_HOP_DONG');
            ELSIF n_nt > 0 AND n_hd > 0 THEN
                SELECT i->>'doi_tac_mst' INTO v_mst FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'NT' LIMIT 1;
                IF v_mst IS NULL THEN
                    x := array_append(x, 'BEN_BAN_HD_THIEU');
                ELSIF EXISTS (SELECT 1 FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'HOA_DON'
                              AND (i->>'mst_ban') IS DISTINCT FROM v_mst) THEN
                    x := array_append(x, 'BEN_BAN_KHAC');
                END IF;
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'HOA_DON' AND i->>'current' IS NULL) THEN
                x := array_append(x, 'HOA_DON_CHUA_CO_PHIEN_BAN');
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_g->'nguon') i WHERE i->>'kind' = 'HOA_DON' AND i->>'part_kind' = 'DONG_LOGIC'
                       AND jsonb_array_length(coalesce(i->'cau_noi', '[]'::jsonb)) = 0) THEN
                x := array_append(x, 'CHO_MAPPING_M2');
            END IF;
            IF p_tp IS NOT NULL AND jsonb_typeof(p_tp) = 'array'
               AND EXISTS (SELECT 1 FROM jsonb_array_elements(p_tp) t WHERE t->>'phan' = 'MOT_PHAN' AND t->>'ty_le_khai' IS NULL) THEN
                x := array_append(x, 'PHAN_KHAI_THIEU');
            END IF;
            RETURN (SELECT coalesce(jsonb_agg(z.e ORDER BY z.e COLLATE "C"), '[]'::jsonb) FROM (SELECT DISTINCT unnest(x) AS e) z);
        END $$""",
    # khóa nguồn hóa đơn theo thứ tự M16: gốc advisory HOA_DON_ROOT| sorted → closure L11 (gốc/pool/child) → hàng danh tính FOR SHARE
    """CREATE OR REPLACE FUNCTION kho._dc_khoa_hoa_don(p_refs jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE ids uuid[]; i uuid;
        BEGIN
            SELECT coalesce(array_agg(DISTINCT (e->>'occurrence_id')::uuid ORDER BY (e->>'occurrence_id')::uuid), '{}') INTO ids
                FROM jsonb_array_elements(p_refs) e WHERE e->>'kind' = 'HOA_DON';
            IF cardinality(ids) = 0 THEN
                RETURN;
            END IF;
            FOREACH i IN ARRAY ids LOOP
                PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || i, 0));
            END LOOP;
            PERFORM kho.l11_khoa_dong_nguon_noi_bo(ids, NULL);
            PERFORM 1 FROM kho.hoa_don_danh_tinh d WHERE d.id = ANY (ids) ORDER BY d.id FOR SHARE;
        END $$""",
    # định danh ngữ nghĩa của TẬP nguồn (kind, occurrence, part) — không gồm phiên bản: PB mới/ABA/khóa mới không sinh gốc trùng
    f"""CREATE OR REPLACE FUNCTION kho._dc_khoa_goc(p_refs jsonb) RETURNS text
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT encode(sha256(convert_to((SELECT jsonb_agg(jsonb_build_object('kind', e->>'kind', 'occurrence_id', e->>'occurrence_id',
                                                                              'part_id', e->>'part_id')
                                                          ORDER BY e->>'kind', e->>'occurrence_id', coalesce(e->>'part_id', ''))
                                         FROM jsonb_array_elements(p_refs) e)::text, 'UTF8')), 'hex')
        $$""",
    # FIX01 closure: hợp refs (kind|occurrence|part), trùng khóa giữ mục của p_a (refs yêu cầu) — chỉ dùng cho quyền/khóa, không cho đồ thị
    """CREATE OR REPLACE FUNCTION kho._dc_hop(p_a jsonb, p_b jsonb) RETURNS jsonb
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT coalesce(jsonb_agg(z.e ORDER BY z.k), '[]'::jsonb)
        FROM (SELECT DISTINCT ON (w.k) w.e, w.k
              FROM (SELECT u.e, (u.e->>'kind') || '|' || (u.e->>'occurrence_id') || '|' || coalesce(u.e->>'part_id', '') AS k, u.n
                    FROM (SELECT x AS e, 0 AS n FROM jsonb_array_elements(coalesce(p_a, '[]'::jsonb)) x
                          UNION ALL SELECT y, 1 FROM jsonb_array_elements(coalesce(p_b, '[]'::jsonb)) y) u) w
              ORDER BY w.k, w.n) z
        $$""",
    # tìm-hoặc-tạo gốc/phiên bản/phần nguồn từ MỘT mục đồ thị hiện hành (không master mới, không đổi nguồn)
    """CREATE OR REPLACE FUNCTION kho._dc_cap_nguon(p_it jsonb, p_ai text, p_aid uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE g kho.mua_nguon_kinh_te%ROWTYPE; v kho.mua_nguon_kinh_te_phien_ban%ROWTYPE; cuoi kho.mua_nguon_kinh_te_phien_ban%ROWTYPE;
                f jsonb; sem text; ph uuid; kind text := p_it->>'kind'; occ uuid := (p_it->>'occurrence_id')::uuid;
                pn uuid := (p_it->>'phap_nhan_id')::uuid; part uuid := nullif(p_it->>'part_id', '')::uuid;
        BEGIN
            INSERT INTO kho.mua_nguon_kinh_te (phap_nhan_id, loai, occurrence_id, cho_id, hoa_don_id, tao_boi, tao_boi_id)
                VALUES (pn, kind, occ, CASE WHEN kind = 'NT' THEN occ END, CASE WHEN kind = 'HOA_DON' THEN occ END, p_ai, p_aid)
                ON CONFLICT (phap_nhan_id, loai, occurrence_id) DO NOTHING;
            SELECT * INTO g FROM kho.mua_nguon_kinh_te x WHERE x.phap_nhan_id = pn AND x.loai = kind AND x.occurrence_id = occ FOR UPDATE;
            f := p_it - 'part_id' - 'part_kind' - 'logical_line_key' - 'cau_noi' - 'hien_hanh' - 'ly_do_hold' - 'toan_ven';
            sem := encode(sha256(convert_to(f::text, 'UTF8')), 'hex');
            SELECT * INTO v FROM kho.mua_nguon_kinh_te_phien_ban x WHERE x.nguon_id = g.id AND x.semantic_sha256 = sem;
            IF v.id IS NULL THEN
                SELECT * INTO cuoi FROM kho.mua_nguon_kinh_te_phien_ban x WHERE x.nguon_id = g.id ORDER BY x.phien_ban DESC LIMIT 1;
                INSERT INTO kho.mua_nguon_kinh_te_phien_ban (nguon_id, phap_nhan_id, loai, phien_ban, truoc_id, cho_id, phong_bi_id, seal_id,
                                                             kt_revision_id, kt_xac_nhan_id, hoa_don_id, hoa_don_phien_ban_id, quan_sat_id,
                                                             su_kien, semantic_sha256, tao_boi, tao_boi_id)
                    VALUES (g.id, pn, kind, coalesce(cuoi.phien_ban, 0) + 1, cuoi.id,
                            CASE WHEN kind = 'NT' THEN occ END, CASE WHEN kind = 'NT' THEN (f->>'current')::uuid END,
                            CASE WHEN kind = 'NT' THEN (f->>'seal_id')::uuid END, CASE WHEN kind = 'NT' THEN (f->>'kt_revision_id')::uuid END,
                            CASE WHEN kind = 'NT' THEN (f->>'kt_xac_nhan_id')::uuid END,
                            CASE WHEN kind = 'HOA_DON' THEN occ END, CASE WHEN kind = 'HOA_DON' THEN (f->>'current')::uuid END,
                            CASE WHEN kind = 'HOA_DON' THEN (f->>'quan_sat_id')::uuid END, f, sem, p_ai, p_aid)
                    RETURNING * INTO v;
            END IF;
            INSERT INTO kho.mua_nguon_phan (nguon_id, phap_nhan_id, loai, loai_phan, hoa_don_id, dong_danh_tinh_id, tao_boi, tao_boi_id)
                VALUES (g.id, pn, kind, CASE WHEN part IS NULL THEN 'TOAN_BO' ELSE 'DONG_LOGIC' END, CASE WHEN kind = 'HOA_DON' THEN occ END,
                        part, p_ai, p_aid)
                ON CONFLICT DO NOTHING;
            SELECT x.id INTO ph FROM kho.mua_nguon_phan x WHERE x.nguon_id = g.id AND x.dong_danh_tinh_id IS NOT DISTINCT FROM part;
            RETURN jsonb_build_object('nguon_id', g.id, 'nguon_phien_ban_id', v.id, 'phan_id', ph);
        END $$""",
    # biên nhận chung: khóa tư vấn theo (PN, module, op, key) → tra; khác nội dung/khác actor → 409
    f"""CREATE OR REPLACE FUNCTION kho._dc_bn_tra(p_pn uuid, p_module text, p_op text, p_khoa text, p_yc jsonb, p_ai text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE b kho.bien_nhan_thao_tac%ROWTYPE;
        BEGIN
            IF p_khoa IS NULL OR p_khoa !~ '^[A-Za-z0-9_.:-]{{1,200}}$' THEN
                RAISE EXCEPTION 'DC_KHOA_THAO_TAC: thiếu hoặc sai khóa thao tác' {_LOI};
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('DC_BN|' || p_pn || '|' || p_module || '|' || p_op || '|' || p_khoa, 0));
            SELECT * INTO b FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = p_pn AND x.module = p_module AND x.operation = p_op AND x.client_key = p_khoa;
            IF b.id IS NULL THEN
                RETURN NULL;
            END IF;
            IF b.request_sha256 IS DISTINCT FROM {_SHA.format(x="p_yc")} OR b.actor IS DISTINCT FROM p_ai
               OR NOT EXISTS (SELECT 1 FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.id::text = b.result_json->>'phien_ban_id') THEN
                RAISE EXCEPTION 'DC_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác nội dung' {_LOI};
            END IF;
            RETURN jsonb_build_object('receipt_id', b.id, 'ket_qua', b.result_json);
        END $$""",
    # nguồn của một gốc (phiên bản chỉ định hoặc mới nhất) — quyền đọc trên MỌI nguồn của MỌI revision TRƯỚC khi trả (không lộ nguồn module khác)
    f"""CREATE OR REPLACE FUNCTION kho._dc_nguon_cua(p_goc uuid, p_phien_ban uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE tat_ca jsonb; ket jsonb; v_pb uuid;
        BEGIN
            SELECT jsonb_agg(DISTINCT jsonb_build_object('kind', t->'nguon'->>'kind', 'occurrence_id', t->'nguon'->>'occurrence_id')) INTO tat_ca
                FROM kho.mua_doi_chieu_can_cu_phien_ban v, jsonb_array_elements(v.noi_dung->'thanh_phan') t WHERE v.doi_chieu_id = p_goc;
            IF tat_ca IS NULL OR NOT kho._dc_doc_duoc(tat_ca) THEN
                RAISE EXCEPTION 'DC_KHONG_THAY: không thấy đối chiếu (hoặc ngoài phạm vi hiện hành của một nguồn)' {_LOI};
            END IF;
            v_pb := coalesce(p_phien_ban, (SELECT x.id FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.doi_chieu_id = p_goc
                                           ORDER BY x.revision DESC LIMIT 1));
            SELECT {_REFS.format(x="v.noi_dung->'thanh_phan'")} INTO ket
                FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.id = v_pb AND v.doi_chieu_id = p_goc;
            IF ket IS NULL THEN
                RAISE EXCEPTION 'DC_KHONG_THAY: không thấy phiên bản đối chiếu thuộc gốc' {_LOI};
            END IF;
            RETURN ket;
        END $$""",
    # tệp căn cứ: CHỈ m4.tep thuộc tập ứng viên 03A của phong bì hiện hành của một NT trong tập; SHA lấy từ CSDL
    f"""CREATE OR REPLACE FUNCTION kho._dc_tep(p_do_thi jsonb, p_ids jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE ket jsonb; n integer;
        BEGIN
            IF p_ids IS NULL OR jsonb_typeof(p_ids) <> 'array' OR jsonb_array_length(p_ids) > {TOI_DA_TEP} THEN
                RAISE EXCEPTION 'DC_CAN_CU_SAI: danh sách tệp căn cứ sai hình dạng' {_LOI};
            END IF;
            SELECT coalesce(jsonb_agg(jsonb_build_object('id', z.id, 'raw_sha256', z.raw_sha256) ORDER BY z.id), '[]'::jsonb), count(*) INTO ket, n
                FROM (SELECT DISTINCT t.id, t.raw_sha256 FROM jsonb_array_elements(p_do_thi->'nguon') i
                      CROSS JOIN LATERAL m4._kt_tep_can_cu((i->>'current')::uuid) t
                      WHERE i->>'kind' = 'NT' AND t.id::text IN (SELECT jsonb_array_elements_text(p_ids))) z;
            IF n <> (SELECT count(DISTINCT x) FROM jsonb_array_elements_text(p_ids) x) THEN
                RAISE EXCEPTION 'DC_CAN_CU_SAI: tệp căn cứ không thuộc hồ sơ/HĐ của nguồn nghiệm thu trong tập' {_LOI};
            END IF;
            RETURN ket;
        END $$""",
    # ============================================================== đọc (đường chủ bảng, sau quyền + khóa đọc + ghim producer của Python)
    f"""CREATE OR REPLACE FUNCTION kho._dc_xem(p_refs jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE r jsonb; lq jsonb; ghi boolean; gt uuid;
        BEGIN
            PERFORM kho._dc_quyen(p_refs, false);
            r := kho._dc_do_thi(p_refs);
            -- FIX01: gốc đang giữ tập chuẩn này (thứ tự refs không đổi identity); chỉ lộ khi đọc được mọi nguồn của gốc đó
            SELECT a.doi_chieu_id INTO gt FROM kho.mua_doi_chieu_can_cu_tap a
                WHERE a.tap_sha256 = kho._dc_khoa_goc(p_refs)
                  AND a.phap_nhan_id = (SELECT min(i->>'phap_nhan_id')::uuid FROM jsonb_array_elements(r->'do_thi'->'nguon') i)
                  AND kho._dc_doc_duoc((SELECT jsonb_agg(t2->'nguon') FROM kho.mua_doi_chieu_can_cu_phien_ban v2,
                                               jsonb_array_elements(v2.noi_dung->'thanh_phan') t2 WHERE v2.doi_chieu_id = a.doi_chieu_id));
            ghi := NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r->'do_thi'->'nguon') i
                               WHERE i->>'kind' = 'HOA_DON' AND NOT kho._dc_kt_toan_cuc((i->>'phap_nhan_id')::uuid));
            SELECT jsonb_agg(jsonb_build_object('doi_chieu_id', v.doi_chieu_id, 'phien_ban_id', v.id, 'revision', v.revision, 'loai', v.loai,
                                                'graph_sha256', v.graph_sha256) ORDER BY v.doi_chieu_id) INTO lq
                FROM kho.mua_doi_chieu_can_cu_phien_ban v
                WHERE v.revision = (SELECT max(y.revision) FROM kho.mua_doi_chieu_can_cu_phien_ban y WHERE y.doi_chieu_id = v.doi_chieu_id)
                  AND EXISTS (SELECT 1 FROM jsonb_array_elements(v.noi_dung->'thanh_phan') t, jsonb_array_elements(p_refs) e
                              WHERE t->'nguon'->>'kind' = e->>'kind' AND t->'nguon'->>'occurrence_id' = e->>'occurrence_id')
                  AND kho._dc_doc_duoc((SELECT jsonb_agg(t2->'nguon') FROM kho.mua_doi_chieu_can_cu_phien_ban v2,
                                               jsonb_array_elements(v2.noi_dung->'thanh_phan') t2 WHERE v2.doi_chieu_id = v.doi_chieu_id));
            RETURN jsonb_build_object('do_thi', r->'do_thi', 'graph_sha256', r->>'graph_sha256', 'thieu', kho._dc_thieu(r->'do_thi', NULL),
                                      'khoa_goc_sha256', kho._dc_khoa_goc(p_refs), 'goc_cua_tap', gt,
                                      'goc_lien_quan', coalesce(lq, '[]'::jsonb), 'duoc_ghi', ghi);
        END $$""",
    f"""CREATE OR REPLACE FUNCTION kho._dc_lich_su(p_goc uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE refs jsonb; r jsonb; ghi boolean; goc kho.mua_doi_chieu_can_cu%ROWTYPE;
        BEGIN
            refs := kho._dc_nguon_cua(p_goc, NULL);
            PERFORM kho._dc_quyen(refs, false);
            SELECT * INTO goc FROM kho.mua_doi_chieu_can_cu x WHERE x.id = p_goc;
            r := kho._dc_do_thi(refs);
            ghi := NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r->'do_thi'->'nguon') i
                               WHERE i->>'kind' = 'HOA_DON' AND NOT kho._dc_kt_toan_cuc((i->>'phap_nhan_id')::uuid));
            RETURN jsonb_build_object('doi_chieu_id', goc.id, 'phap_nhan_id', goc.phap_nhan_id, 'khoa_goc_sha256', goc.khoa_goc_sha256,
                'module_bien_nhan', goc.module_bien_nhan, 'do_thi', r->'do_thi', 'graph_sha256', r->>'graph_sha256', 'duoc_ghi', ghi,
                'bo_tap', (SELECT coalesce(jsonb_agg(jsonb_build_object('tap_sha256', a.tap_sha256, 'phien_ban_id', a.phien_ban_id)
                                                     ORDER BY a.tao_luc, a.id), '[]'::jsonb)
                           FROM kho.mua_doi_chieu_can_cu_tap a WHERE a.doi_chieu_id = p_goc),
                'phien_ban', (SELECT coalesce(jsonb_agg(jsonb_build_object('phien_ban_id', v.id, 'revision', v.revision, 'truoc_id', v.truoc_id,
                                  'loai', v.loai, 'nhap_id', v.nhap_id, 'noi_dung', v.noi_dung, 'noi_dung_sha256', v.noi_dung_sha256,
                                  'do_thi', v.do_thi, 'graph_sha256', v.graph_sha256, 'thieu', v.thieu, 'tap_sha256', v.tap_sha256,
                                  'hop_dong_id', v.hop_dong_id,
                                  'doi_tac_id', v.doi_tac_id, 'ly_do', v.ly_do, 'ghi_nhan', v.ghi_nhan, 'financial_owner', v.financial_owner,
                                  'tao_boi', v.tao_boi, 'tao_luc', v.tao_luc) ORDER BY v.revision), '[]'::jsonb)
                              FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.doi_chieu_id = p_goc));
        END $$""",
    # ============================================================== lệnh (SECURITY INVOKER, chỉ kết nối chủ bảng)
    # LƯU NHÁP (tạo gốc mới expected_revision=0, hoặc revision mới của gốc có lý do). Thiếu căn cứ được lưu (thieu ≠ []), không tự xác nhận.
    f"""CREATE OR REPLACE FUNCTION kho.dc_luu(p_khoa text, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE ai text; aid uuid; refs jsonb; r jsonb; it jsonb; ref jsonb; v_muc jsonb; v_cap jsonb; pn uuid; n_pn integer; module text; kg text;
                goc kho.mua_doi_chieu_can_cu%ROWTYPE; cuoi kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; moi kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE;
                cu jsonb; rid uuid; th jsonb; tep jsonb; nd jsonb; tp jsonb; hd uuid; dtac uuid; kq jsonb; erev integer; ma_goc uuid;
                hop jsonb; cu_refs jsonb; v_goc uuid; v_cuoi0 uuid;
        BEGIN""" + _TIN_CAY + f"""
            IF p_yc IS NULL OR jsonb_typeof(p_yc) <> 'object' OR jsonb_typeof(p_yc->'thanh_phan') IS DISTINCT FROM 'array'
               OR jsonb_array_length(p_yc->'thanh_phan') NOT BETWEEN 1 AND {TOI_DA_THANH_PHAN}
               OR jsonb_typeof(p_yc->'expected_revision') IS DISTINCT FROM 'number' OR length(btrim(coalesce(p_yc->>'ly_do', ''))) = 0 THEN
                RAISE EXCEPTION 'DC_THAM_SO_SAI: yêu cầu lưu đối chiếu không đúng hình dạng' {_LOI};
            END IF;
            tp := (SELECT jsonb_agg(z ORDER BY z->'nguon'->>'kind', z->'nguon'->>'occurrence_id', coalesce(z->'nguon'->>'part_id', ''))
                   FROM jsonb_array_elements(p_yc->'thanh_phan') z);
            refs := {_REFS.format(x="tp")};
            erev := (p_yc->>'expected_revision')::integer;
            v_goc := (p_yc->>'doi_chieu_id')::uuid;
            -- FIX01 closure TRƯỚC khóa: revision mới nhất đã đọc (v_cuoi0) + refs của nó ∪ refs yêu cầu (quyền đọc mọi revision trước khi trả)
            IF v_goc IS NOT NULL THEN
                SELECT x.id INTO v_cuoi0 FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.doi_chieu_id = v_goc ORDER BY x.revision DESC LIMIT 1;
                cu_refs := kho._dc_nguon_cua(v_goc, v_cuoi0);
                hop := kho._dc_hop(refs, cu_refs);
            ELSE
                hop := refs;
            END IF;
            PERFORM kho._dc_quyen(hop, true);
            PERFORM kho._dc_khoa_hoa_don(hop);
            r := kho._dc_do_thi(refs);
            SELECT count(DISTINCT i->>'phap_nhan_id'), min(i->>'phap_nhan_id')::uuid INTO n_pn, pn FROM jsonb_array_elements(r->'do_thi'->'nguon') i;
            IF n_pn <> 1 THEN
                RAISE EXCEPTION 'DC_KHAC_PN: mọi nguồn của một đối chiếu phải cùng pháp nhân' {_LOI};
            END IF;
            kg := kho._dc_khoa_goc(refs);
            -- alias tập (một khóa/giao dịch) → gốc → revision mới nhất → biên nhận
            PERFORM pg_advisory_xact_lock(hashtextextended('DC_TAP|' || pn || '|' || kg, 0));
            IF v_goc IS NOT NULL THEN
                SELECT * INTO goc FROM kho.mua_doi_chieu_can_cu x WHERE x.id = v_goc AND x.phap_nhan_id = pn FOR UPDATE;
                IF goc.id IS NULL THEN
                    RAISE EXCEPTION 'DC_KHONG_THAY: không thấy đối chiếu (hoặc khác pháp nhân của nguồn)' {_LOI};
                END IF;
                SELECT * INTO cuoi FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.doi_chieu_id = goc.id ORDER BY x.revision DESC LIMIT 1 FOR UPDATE;
                IF cuoi.id IS DISTINCT FROM v_cuoi0 THEN
                    RAISE EXCEPTION 'DC_REVISION_CU: đối chiếu đổi revision trong lúc khóa (closure nguồn đã đọc không còn đúng) — tải lại' {_LOI};
                END IF;
                PERFORM kho._dc_quyen(hop, true);
                module := goc.module_bien_nhan;
            ELSE
                module := CASE WHEN EXISTS (SELECT 1 FROM jsonb_array_elements(refs) e WHERE e->>'kind' = 'NT') THEN 'M4' ELSE 'M2' END;
            END IF;
            cu := kho._dc_bn_tra(pn, module, '{OP_LUU}', p_khoa, p_yc, ai);
            IF cu IS NOT NULL THEN
                SELECT * INTO goc FROM kho.mua_doi_chieu_can_cu x WHERE x.id = (cu->'ket_qua'->>'doi_chieu_id')::uuid;
                RETURN {_tra("true", "(cu->'ket_qua')", "(cu->>'receipt_id')::uuid")};
            END IF;""" + _HIEN_HANH.format(refs="refs", ma_cu="DC_NGUON_CU") + f"""
            IF (p_yc->>'expected_graph') IS DISTINCT FROM (r->>'graph_sha256') THEN
                RAISE EXCEPTION 'DC_DO_THI_DOI: đồ thị căn cứ hiện hành khác lúc xem — tải lại' {_LOI};
            END IF;
            SELECT a.doi_chieu_id INTO ma_goc FROM kho.mua_doi_chieu_can_cu_tap a WHERE a.phap_nhan_id = pn AND a.tap_sha256 = kg;
            IF goc.id IS NULL THEN
                IF erev <> 0 THEN
                    RAISE EXCEPTION 'DC_REVISION_CU: tạo đối chiếu mới cần expected_revision = 0' {_LOI};
                END IF;
                IF ma_goc IS NOT NULL THEN
                    RAISE EXCEPTION 'DC_DA_CO_GOC: tập nguồn này đã thuộc đối chiếu % — sửa bằng revision mới của gốc đó', ma_goc {_LOI};
                END IF;
                INSERT INTO kho.mua_doi_chieu_can_cu (phap_nhan_id, khoa_goc_sha256, module_bien_nhan, tao_boi, tao_boi_id)
                    VALUES (pn, kg, module, ai, aid) RETURNING * INTO goc;
            ELSIF erev IS DISTINCT FROM cuoi.revision THEN
                RAISE EXCEPTION 'DC_REVISION_CU: đối chiếu đã có revision mới (hiện tại %) — tải lại', cuoi.revision {_LOI};
            ELSIF ma_goc IS NOT NULL AND ma_goc IS DISTINCT FROM goc.id THEN
                RAISE EXCEPTION 'DC_TAP_THUOC_GOC_KHAC: tập nguồn này đã thuộc đối chiếu % — không tự gộp/chuyển lịch sử', ma_goc {_LOI};
            END IF;
            tep := kho._dc_tep(r->'do_thi', coalesce(p_yc->'can_cu_tep', '[]'::jsonb));
            nd := jsonb_build_object('thanh_phan', tp, 'can_cu_tep', tep, 'ly_do', p_yc->>'ly_do');
            th := kho._dc_thieu(r->'do_thi', tp);
            SELECT CASE WHEN count(DISTINCT i->>'hop_dong_id') = 1 THEN min(i->>'hop_dong_id')::uuid END,
                   CASE WHEN count(DISTINCT i->>'hop_dong_id') = 1 THEN min(i->>'doi_tac_id')::uuid END
                INTO hd, dtac FROM jsonb_array_elements(r->'do_thi'->'nguon') i WHERE i->>'kind' = 'NT';
            INSERT INTO kho.mua_doi_chieu_can_cu_phien_ban ({_TRUONG_PB})
                VALUES (goc.id, pn, coalesce(cuoi.revision, 0) + 1, cuoi.id, 'NHAP', NULL, nd, {_SHA.format(x="nd")}, r->'do_thi',
                        r->>'graph_sha256', th, kg, hd, dtac, p_yc->>'ly_do', ai, aid)
                RETURNING * INTO moi;
            FOR v_muc IN SELECT z FROM jsonb_array_elements(tp) z LOOP
                SELECT i INTO it FROM jsonb_array_elements(r->'do_thi'->'nguon') i
                    WHERE i->>'kind' = v_muc->'nguon'->>'kind' AND i->>'occurrence_id' = v_muc->'nguon'->>'occurrence_id'
                      AND coalesce(i->>'part_id', '') = coalesce(v_muc->'nguon'->>'part_id', '');
                v_cap := kho._dc_cap_nguon(it, ai, aid);
                INSERT INTO kho.mua_doi_chieu_can_cu_thanh_phan (phien_ban_id, doi_chieu_id, phap_nhan_id, nguon_id, nguon_phien_ban_id, phan_id,
                                                                  phan, ty_le_khai, ty_le_trang_thai)
                    VALUES (moi.id, goc.id, pn, (v_cap->>'nguon_id')::uuid, (v_cap->>'nguon_phien_ban_id')::uuid, (v_cap->>'phan_id')::uuid,
                            v_muc->>'phan', v_muc->>'ty_le_khai', CASE WHEN v_muc->>'phan' = 'TOAN_PHAN' THEN 'KHONG_AP_DUNG'
                                                                     WHEN v_muc->>'ty_le_khai' IS NULL THEN 'THIEU' ELSE 'KHAI_BAO_THO_CHUA_SCALE' END);
            END LOOP;
            IF ma_goc IS NULL THEN
                INSERT INTO kho.mua_doi_chieu_can_cu_tap (phap_nhan_id, tap_sha256, doi_chieu_id, phien_ban_id, tao_boi, tao_boi_id)
                    VALUES (pn, kg, goc.id, moi.id, ai, aid);
            END IF;
            INSERT INTO kho.mua_doi_chieu_can_cu_nhat_ky (phap_nhan_id, doi_chieu_id, phien_ban_id, hanh_dong, boi, boi_id, chi_tiet)
                VALUES (pn, goc.id, moi.id, 'LUU', ai, aid, jsonb_build_object('revision', moi.revision, 'so_thieu', jsonb_array_length(th),
                                                                               'so_thanh_phan', jsonb_array_length(tp), 'tap_sha256', kg,
                                                                               'doi_tap', cuoi.id IS NOT NULL AND cuoi.tap_sha256 IS DISTINCT FROM kg));
            kq := {_kq("LUU", "moi", TT_NHAP, "false")};
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                VALUES (pn, module, '{OP_LUU}', p_khoa, {_SHA.format(x="p_yc")}, kq, ai) RETURNING id INTO rid;
            RETURN {_tra("false", "kq", "rid")};
        END $$""",
    # XÁC NHẬN: đúng revision NHAP mới nhất đã lưu + đồ thị hiện hành = đồ thị đã lưu = expected_graph + đủ căn cứ → revision XAC_NHAN sao y.
    # Đã xác nhận từ CHÍNH nháp đó (khóa mới/đồng thời) → trả cùng xác nhận (trung_xac_nhan), khác → 409.
    f"""CREATE OR REPLACE FUNCTION kho.dc_xac_nhan(p_khoa text, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE ai text; aid uuid; refs jsonb; r jsonb; it jsonb; ref jsonb; module text; goc kho.mua_doi_chieu_can_cu%ROWTYPE;
                n kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; cuoi kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE;
                moi kho.mua_doi_chieu_can_cu_phien_ban%ROWTYPE; cu jsonb; rid uuid; th jsonb; kq jsonb; erev integer; hop jsonb;
        BEGIN""" + _TIN_CAY + f"""
            IF p_yc IS NULL OR jsonb_typeof(p_yc) <> 'object' OR jsonb_typeof(p_yc->'expected_revision') IS DISTINCT FROM 'number' THEN
                RAISE EXCEPTION 'DC_THAM_SO_SAI: yêu cầu xác nhận đối chiếu không đúng hình dạng' {_LOI};
            END IF;
            erev := (p_yc->>'expected_revision')::integer;
            SELECT * INTO goc FROM kho.mua_doi_chieu_can_cu x WHERE x.id = (p_yc->>'doi_chieu_id')::uuid;
            IF goc.id IS NULL THEN
                RAISE EXCEPTION 'DC_KHONG_THAY: không thấy đối chiếu (hoặc ngoài phạm vi hiện hành)' {_LOI};
            END IF;
            refs := kho._dc_nguon_cua(goc.id, (p_yc->>'phien_ban_id')::uuid);
            -- FIX01 closure: nháp chỉ định ∪ revision mới nhất (nháp không còn mới nhất → DC_REVISION_CU dưới khóa)
            hop := kho._dc_hop(refs, kho._dc_nguon_cua(goc.id, NULL));
            PERFORM kho._dc_quyen(hop, true);
            PERFORM kho._dc_khoa_hoa_don(hop);
            SELECT * INTO goc FROM kho.mua_doi_chieu_can_cu x WHERE x.id = goc.id FOR UPDATE;
            SELECT * INTO cuoi FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.doi_chieu_id = goc.id ORDER BY x.revision DESC LIMIT 1 FOR UPDATE;
            SELECT * INTO n FROM kho.mua_doi_chieu_can_cu_phien_ban x WHERE x.id = (p_yc->>'phien_ban_id')::uuid AND x.doi_chieu_id = goc.id;
            module := goc.module_bien_nhan;
            r := kho._dc_do_thi(refs);
            cu := kho._dc_bn_tra(goc.phap_nhan_id, module, '{OP_XAC_NHAN}', p_khoa, p_yc, ai);
            IF cu IS NOT NULL THEN
                RETURN {_tra("true", "(cu->'ket_qua')", "(cu->>'receipt_id')::uuid")};
            END IF;
            IF cuoi.loai = 'XAC_NHAN' AND cuoi.nhap_id IS NOT DISTINCT FROM n.id THEN
                IF erev IS DISTINCT FROM n.revision THEN
                    RAISE EXCEPTION 'DC_REVISION_CU: đối chiếu đã xác nhận từ revision khác — tải lại' {_LOI};
                END IF;
                moi := cuoi;
                kq := {_kq("XAC_NHAN", "moi", TT_XAC_NHAN, "true")};
            ELSE
                IF n.id IS NULL OR n.loai <> 'NHAP' OR n.id IS DISTINCT FROM cuoi.id OR erev IS DISTINCT FROM n.revision THEN
                    RAISE EXCEPTION 'DC_REVISION_CU: chỉ xác nhận đúng bản nháp mới nhất đã lưu (hiện tại %) — tải lại', cuoi.revision {_LOI};
                END IF;
                IF (p_yc->>'expected_graph') IS DISTINCT FROM n.graph_sha256 THEN
                    RAISE EXCEPTION 'DC_DO_THI_DOI: đồ thị gửi lên khác đồ thị của bản nháp đã lưu' {_LOI};
                END IF;
                IF (r->>'graph_sha256') IS DISTINCT FROM n.graph_sha256 THEN
                    RAISE EXCEPTION 'DC_CAN_KIEM_LAI: căn cứ nguồn đã đổi sau khi lưu nháp — lưu revision mới trước khi xác nhận' {_LOI};
                END IF;""" + _HIEN_HANH.format(refs="refs", ma_cu="DC_CAN_KIEM_LAI") + f"""
                th := kho._dc_thieu(r->'do_thi', n.noi_dung->'thanh_phan');
                IF jsonb_array_length(th) > 0 THEN
                    RAISE EXCEPTION 'DC_CHO_BO_SUNG: căn cứ chưa đủ để kế toán xác nhận (%)', th::text {_LOI};
                END IF;
                IF kho._dc_tep(r->'do_thi', (SELECT coalesce(jsonb_agg(z->>'id'), '[]'::jsonb) FROM jsonb_array_elements(n.noi_dung->'can_cu_tep') z))
                   IS DISTINCT FROM n.noi_dung->'can_cu_tep' THEN
                    RAISE EXCEPTION 'DC_CAN_CU_SAI: tệp căn cứ không còn thuộc phạm vi nguồn' {_LOI};
                END IF;
                INSERT INTO kho.mua_doi_chieu_can_cu_phien_ban ({_TRUONG_PB})
                    VALUES (goc.id, goc.phap_nhan_id, n.revision + 1, n.id, 'XAC_NHAN', n.id, n.noi_dung, n.noi_dung_sha256, n.do_thi,
                            n.graph_sha256, '[]'::jsonb, n.tap_sha256, n.hop_dong_id, n.doi_tac_id, n.ly_do, ai, aid)
                    RETURNING * INTO moi;
                INSERT INTO kho.mua_doi_chieu_can_cu_thanh_phan (phien_ban_id, doi_chieu_id, phap_nhan_id, nguon_id, nguon_phien_ban_id, phan_id,
                                                                  phan, ty_le_khai, ty_le_trang_thai)
                    SELECT moi.id, m.doi_chieu_id, m.phap_nhan_id, m.nguon_id, m.nguon_phien_ban_id, m.phan_id, m.phan, m.ty_le_khai, m.ty_le_trang_thai
                    FROM kho.mua_doi_chieu_can_cu_thanh_phan m WHERE m.phien_ban_id = n.id ORDER BY m.phan_id;
                INSERT INTO kho.mua_doi_chieu_can_cu_nhat_ky (phap_nhan_id, doi_chieu_id, phien_ban_id, hanh_dong, boi, boi_id, chi_tiet)
                    VALUES (goc.phap_nhan_id, goc.id, moi.id, 'XAC_NHAN', ai, aid, jsonb_build_object('revision', moi.revision, 'nhap_id', n.id));
                kq := {_kq("XAC_NHAN", "moi", TT_XAC_NHAN, "false")};
            END IF;
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                VALUES (goc.phap_nhan_id, module, '{OP_XAC_NHAN}', p_khoa, {_SHA.format(x="p_yc")}, kq, ai) RETURNING id INTO rid;
            RETURN {_tra("false", "kq", "rid")};
        END $$""",
    # ============================================================== guard deferred lúc commit: thành phần ↔ refs, quyền, đồ thị hiện hành, thiếu
    f"""CREATE OR REPLACE FUNCTION kho._dc_phien_ban_hoan_tat() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE refs jsonb; r jsonb; it jsonb; ref jsonb; n_tp integer; n_tv integer; bad integer;
        BEGIN
            refs := {_REFS.format(x="NEW.noi_dung->'thanh_phan'")};
            n_tp := coalesce(jsonb_array_length(NEW.noi_dung->'thanh_phan'), 0);
            SELECT count(*) INTO n_tv FROM kho.mua_doi_chieu_can_cu_thanh_phan m WHERE m.phien_ban_id = NEW.id;
            IF refs IS NULL OR n_tp = 0 OR n_tv <> n_tp THEN
                RAISE EXCEPTION 'DC_THANH_PHAN_SAI: thành phần đối chiếu không khớp nội dung đã ghi' {_LOI};
            END IF;
            SELECT count(*) INTO bad FROM jsonb_array_elements(NEW.noi_dung->'thanh_phan') t WHERE NOT EXISTS (
                SELECT 1 FROM kho.mua_doi_chieu_can_cu_thanh_phan m JOIN kho.mua_nguon_kinh_te g ON g.id = m.nguon_id
                     JOIN kho.mua_nguon_phan p ON p.id = m.phan_id JOIN kho.mua_nguon_kinh_te_phien_ban v ON v.id = m.nguon_phien_ban_id
                WHERE m.phien_ban_id = NEW.id AND g.loai = t->'nguon'->>'kind' AND g.occurrence_id::text = t->'nguon'->>'occurrence_id'
                  AND p.dong_danh_tinh_id IS NOT DISTINCT FROM nullif(t->'nguon'->>'part_id', '')::uuid
                  AND (v.su_kien->>'current') IS NOT DISTINCT FROM (t->'nguon'->>'source_version_id')
                  AND m.phan = t->>'phan' AND m.ty_le_khai IS NOT DISTINCT FROM (t->>'ty_le_khai'));
            IF bad > 0 THEN
                RAISE EXCEPTION 'DC_THANH_PHAN_SAI: thành phần không trỏ đúng gốc/phần/phiên bản nguồn của nội dung' {_LOI};
            END IF;
            -- FIX01: tập của revision phải có alias trỏ CHÍNH gốc này; revision 1 = tập tạo + namespace biên nhận đúng nguồn gốc
            IF NOT EXISTS (SELECT 1 FROM kho.mua_doi_chieu_can_cu_tap a WHERE a.phap_nhan_id = NEW.phap_nhan_id AND a.tap_sha256 = NEW.tap_sha256
                           AND a.doi_chieu_id = NEW.doi_chieu_id) THEN
                RAISE EXCEPTION 'DC_TAP_THUOC_GOC_KHAC: tập nguồn của revision không thuộc alias của chính đối chiếu' {_LOI};
            END IF;
            IF NEW.revision = 1 AND NOT EXISTS (
                   SELECT 1 FROM kho.mua_doi_chieu_can_cu g WHERE g.id = NEW.doi_chieu_id AND g.khoa_goc_sha256 = NEW.tap_sha256
                      AND g.module_bien_nhan = CASE WHEN EXISTS (SELECT 1 FROM jsonb_array_elements(refs) e WHERE e->>'kind' = 'NT')
                                                    THEN 'M4' ELSE 'M2' END) THEN
                RAISE EXCEPTION 'DC_TOAN_VEN: gốc phải mang digest + namespace biên nhận của tập tạo' {_LOI};
            END IF;
            PERFORM kho._dc_quyen(refs, true);
            r := kho._dc_do_thi(refs);
            IF (r->>'graph_sha256') IS DISTINCT FROM NEW.graph_sha256 OR (r->'do_thi') IS DISTINCT FROM NEW.do_thi THEN
                RAISE EXCEPTION 'DC_CAN_KIEM_LAI: đồ thị căn cứ hiện hành (producer + master) khác đồ thị đã ghi, hoặc thiếu chứng thực của giao dịch' {_LOI};
            END IF;""" + _HIEN_HANH.format(refs="refs", ma_cu="DC_CAN_KIEM_LAI") + f"""
            IF kho._dc_thieu(NEW.do_thi, NEW.noi_dung->'thanh_phan') IS DISTINCT FROM NEW.thieu THEN
                RAISE EXCEPTION 'DC_TOAN_VEN: danh sách thiếu đã ghi khác kiểm tra căn cứ' {_LOI};
            END IF;
            RETURN NULL;
        END $$""",
    """CREATE CONSTRAINT TRIGGER mua_doi_chieu_can_cu_phien_ban_hoan_tat AFTER INSERT ON kho.mua_doi_chieu_can_cu_phien_ban
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION kho._dc_phien_ban_hoan_tat()""",
    # ============================================================== quyền thực thi: lệnh/nội bộ/trigger KHÔNG cấp; app chỉ hàm đọc sớm
    "REVOKE EXECUTE ON FUNCTION " + ", ".join((*HAM_LENH, *HAM_NOI_BO, *HAM_DOC, *HAM_TRIGGER)) + " FROM PUBLIC",
    *(f"REVOKE ALL ON kho.{t} FROM PUBLIC" for t in BANG),
    *(f"ALTER TABLE kho.{t} ENABLE ROW LEVEL SECURITY" for t in BANG),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION """ + ", ".join(HAM_DOC) + """ TO app_web;
        END IF;
    END $$""",
)
