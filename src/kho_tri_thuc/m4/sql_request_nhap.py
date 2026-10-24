"""M4-04A — Request nháp từ hồ sơ đợt đã seal: intent bền vững + lịch sử/outbox + mapping nhân viên → Request. CHỈ hằng SQL, MỘT constant
`M4_REQUEST_NHAP`; KHÔNG ordinal, KHÔNG đăng ký vào registry migration (pg_migrations.py không đổi). Root review rồi apply riêng ở gói đăng ký.

- Mapping (m4.request_anh_xa): nhân viên KTT (master.nguoi_dung) + pháp nhân → tên đăng nhập Request đứng tên `nguoiTao`, có căn cứ và revision.
  Chỉ máy chủ/Root ghi qua hàm tin cậy; thay = thu hồi bản cũ (một lần) + revision mới; không xóa. Không suy từ email/tên giống nhau.
- Intent (m4.request_y_dinh): MỘT intent/nhánh trên một seal (UNIQUE(seal_id, nhanh)); canonical (nguồn seal + actor + mapping revision + cấu hình
  /nhóm/phiên bản quan sát + body POST) + SHA, idem key cố định `m4-request:<id>` tạo TRƯỚC HTTP. Cột nguồn/canonical/key bất biến; remote
  Request ID/tệp ID ghi một lần; không DELETE. Nhánh đính chính có cột lineage (parent_id) nhưng chưa có lệnh tạo ở gói này.
- Hai pha: m4.request_giu (giao dịch ngắn: quyền hiện hành → biên nhận → seal/canonical → intent → lease) → HTTP ngoài giao dịch → m4.request_ghi
  (CAS đúng lease + revision; quyền kiểm lại nhưng KHÔNG chặn ghi bằng chứng — trả quyen_con để máy chủ không lộ kết quả).
  Lease TAO/TAI hết hạn chưa ghi = có thể đã gửi → CHUA_RO_TAO/CHUA_RO_TAI (không tạo/tải lại mù). Gửi lại TAO cùng key/body chỉ trong 20 giờ kể
  từ lần gửi đầu (TTL idem nguồn 24 giờ); quá hạn → HOLD, không tạo lại.
- Số tiền = seal.so_lieu.so_xin_thanh_toan + tien_te ĐÚNG chuỗi (không gia_tri_nt, không trừ tạm ứng/thu hồi/giữ lại, không VAT/FX/AP).
- Bảng: chỉ chủ bảng ghi; RLS + GRANT SELECT kỹ thuật cho app_web hiện hữu (đọc theo m4.duyet_doc_dot / chính mình).
"""

from __future__ import annotations

_LOI = "USING ERRCODE = 'P0001'"
_HEX = "~ '^[0-9a-f]{64}$'"
_TIEN = r"~ '^(0|[1-9][0-9]{0,17})(\.[0-9]?[1-9])?$'"
TRANG_THAI = ("MOI", "CHUA_RO_TAO", "TU_CHOI_TAO", "DA_TAO", "DA_TAO_NHAP", "CHUA_RO_TAI", "CHO_QUET", "DA_DOI_SOAT", "HOLD")
BUOC = ("TAO", "DOC", "TAI", "DOI_SOAT")
HANH_DONG = ("REQUEST_TAO", "REQUEST_DOI_SOAT")
CUA_SO_GUI_LAI_GIO = 20  # < TTL idempotency nguồn 24h (ghi.ts:105–108): sau mốc này KHÔNG gửi lại POST, chuyển HOLD đối soát tay
_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.request_y_dinh'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường tin cậy của máy chủ ghi intent Request' """ + _LOI + """;
            END IF;"""


def _sql_tuple(xs) -> str:
    return "(" + ",".join(f"'{x}'" for x in xs) + ")"


# cột intent BẤT BIẾN sau INSERT (nguồn seal, actor, mapping, canonical, key, cấu hình, PDF)
COT_BAT_BIEN = ("id", "phap_nhan_id", "du_an_id", "hop_dong_id", "dot_id", "phien_ban_id", "seal_id", "nhanh", "parent_id", "actor_id", "actor",
                "anh_xa_id", "anh_xa_revision", "nguoi_tao", "canonical", "canonical_sha256", "idem_key", "cau_hinh_sha256", "khoa_ref", "nhom",
                "nhom_phien_ban", "so_tien", "tien_te", "pdf_id", "pdf_sha256", "pdf_byte_length", "tao_luc")
# cột ghi MỘT lần (NULL → giá trị; sau đó không đổi)
COT_MOT_LAN = ("remote_id", "remote_tep_id", "lan_tao_dau", "doi_soat_sha256", "doi_soat_byte_length")
HAM_LENH = ("m4.request_anh_xa_dat(uuid, uuid, text, text)", "m4.request_anh_xa_thu_hoi(uuid, text)",
            "m4.request_giu(text, text, jsonb, uuid, uuid, jsonb, text, text, integer)", "m4.request_ghi(uuid, uuid, integer, jsonb)",
            "m4._request_su_kien(uuid, text, text, text, jsonb, boolean)")
HAM_DOC = ("m4.request_quyen(uuid)", "m4.request_kiem(uuid)")
BANG = ("request_anh_xa", "request_y_dinh", "request_su_kien", "request_bien_nhan")

_CU = ", ".join(f"OLD.{c}" for c in COT_BAT_BIEN)
_MOI = ", ".join(f"NEW.{c}" for c in COT_BAT_BIEN)
_MOT_LAN = "\n".join(f"""            IF OLD.{c} IS NOT NULL AND NEW.{c} IS DISTINCT FROM OLD.{c} THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: {c} của intent Request chỉ ghi một lần' {_LOI};
            END IF;""" for c in COT_MOT_LAN)

M4_REQUEST_NHAP = (
    "SET LOCAL check_function_bodies = off",
    # --- mapping nhân viên → danh tính Request (người đứng tên nguoiTao; KHÁC chủ khóa API — máy chủ kiểm khác nhau theo cấu hình)
    """CREATE TABLE m4.request_anh_xa (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        request_dang_nhap text NOT NULL CHECK (length(request_dang_nhap) BETWEEN 1 AND 200 AND request_dang_nhap !~ '[[:cntrl:][:space:]]'),
        can_cu text NOT NULL CHECK (length(btrim(can_cu)) BETWEEN 1 AND 500 AND can_cu !~ '[[:cntrl:]]'),
        revision integer NOT NULL CHECK (revision >= 1),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        thu_hoi_luc timestamptz,
        thu_hoi_boi text,
        thu_hoi_ly_do text CHECK (thu_hoi_ly_do IS NULL OR length(btrim(thu_hoi_ly_do)) BETWEEN 1 AND 500),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL) AND (thu_hoi_luc IS NULL) = (thu_hoi_ly_do IS NULL)),
        UNIQUE (nguoi_dung_id, phap_nhan_id, revision))""",
    "CREATE UNIQUE INDEX request_anh_xa_hien_hanh ON m4.request_anh_xa (nguoi_dung_id, phap_nhan_id) WHERE thu_hoi_luc IS NULL",
    f"""CREATE OR REPLACE FUNCTION m4.request_anh_xa_bat_bien() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: % chỉ ghi qua hàm định nghĩa M4', TG_TABLE_NAME {_LOI};
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: mapping Request không xóa — thu hồi bằng hàm' {_LOI};
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.thu_hoi_luc IS NOT NULL OR NEW.thu_hoi_luc IS NULL
                   OR ROW(OLD.id, OLD.nguoi_dung_id, OLD.phap_nhan_id, OLD.request_dang_nhap, OLD.can_cu, OLD.revision, OLD.tao_boi, OLD.tao_boi_id, OLD.tao_luc)
                      IS DISTINCT FROM
                      ROW(NEW.id, NEW.nguoi_dung_id, NEW.phap_nhan_id, NEW.request_dang_nhap, NEW.can_cu, NEW.revision, NEW.tao_boi, NEW.tao_boi_id, NEW.tao_luc) THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: mapping Request chỉ được thu hồi một lần, không sửa nội dung' {_LOI};
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER request_anh_xa_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON m4.request_anh_xa FOR EACH ROW EXECUTE FUNCTION m4.request_anh_xa_bat_bien()",
    # --- intent bền vững: một nhánh / seal; canonical + idem key cố định trước HTTP; kết quả remote tách bước
    f"""CREATE TABLE m4.request_y_dinh (
        id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        seal_id uuid NOT NULL REFERENCES m4.duyet_seal(id),
        nhanh text NOT NULL CHECK (nhanh ~ '^[A-Z0-9_]{{1,40}}$'),
        parent_id uuid REFERENCES m4.request_y_dinh(id),
        actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        actor text NOT NULL,
        anh_xa_id uuid NOT NULL REFERENCES m4.request_anh_xa(id),
        anh_xa_revision integer NOT NULL CHECK (anh_xa_revision >= 1),
        nguoi_tao text NOT NULL,
        canonical jsonb NOT NULL CHECK (jsonb_typeof(canonical) = 'object' AND octet_length(canonical::text) <= 65536),
        canonical_sha256 text NOT NULL CHECK (canonical_sha256 {_HEX}),
        idem_key text NOT NULL UNIQUE,
        cau_hinh_sha256 text NOT NULL CHECK (cau_hinh_sha256 {_HEX}),
        khoa_ref text NOT NULL CHECK (khoa_ref ~ '^[A-Za-z0-9_.:-]{{1,100}}$'),
        nhom text NOT NULL CHECK (length(nhom) BETWEEN 1 AND 100),
        nhom_phien_ban integer NOT NULL CHECK (nhom_phien_ban >= 1),
        so_tien text NOT NULL CHECK (so_tien {_TIEN}),
        tien_te text NOT NULL CHECK (tien_te ~ '^[A-Z]{{3}}$'),
        pdf_id uuid NOT NULL REFERENCES m4.duyet_pdf(id),
        pdf_sha256 text NOT NULL CHECK (pdf_sha256 {_HEX}),
        pdf_byte_length bigint NOT NULL CHECK (pdf_byte_length > 0),
        trang_thai text NOT NULL CHECK (trang_thai IN {_sql_tuple(TRANG_THAI)}),
        hold_ma text CHECK (hold_ma IS NULL OR hold_ma ~ '^[A-Z0-9_]{{1,60}}$'),
        co_chua_ro boolean NOT NULL DEFAULT false,
        remote_id uuid,
        remote_ma text CHECK (remote_ma IS NULL OR length(remote_ma) BETWEEN 1 AND 100),
        remote_trang_thai text CHECK (remote_trang_thai IS NULL OR remote_trang_thai IN ('draft','in_review','returned','approved','rejected')),
        remote_tep_id uuid,
        tep_trang_thai_quet text CHECK (tep_trang_thai_quet IS NULL OR tep_trang_thai_quet IN ('pending','clean','infected','error')),
        doi_soat_sha256 text CHECK (doi_soat_sha256 IS NULL OR doi_soat_sha256 {_HEX}),
        doi_soat_byte_length bigint,
        lan_tao_dau timestamptz,
        so_lan_tao integer NOT NULL DEFAULT 0 CHECK (so_lan_tao >= 0),
        so_lan_tai integer NOT NULL DEFAULT 0 CHECK (so_lan_tai >= 0),
        lease_id uuid,
        lease_buoc text CHECK (lease_buoc IS NULL OR lease_buoc IN {_sql_tuple(BUOC)}),
        lease_het timestamptz,
        revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (idem_key = 'm4-request:' || id::text),
        CHECK ((nhanh = 'GOC') = (parent_id IS NULL)),
        CHECK ((lease_id IS NULL) = (lease_buoc IS NULL) AND (lease_id IS NULL) = (lease_het IS NULL)),
        CHECK ((trang_thai = 'HOLD') = (hold_ma IS NOT NULL)),
        CHECK (trang_thai NOT IN ('DA_TAO','DA_TAO_NHAP','CHUA_RO_TAI','CHO_QUET','DA_DOI_SOAT') OR remote_id IS NOT NULL),
        CHECK (trang_thai NOT IN ('CHO_QUET','DA_DOI_SOAT') OR remote_tep_id IS NOT NULL),
        CHECK (trang_thai <> 'DA_DOI_SOAT' OR (doi_soat_sha256 = pdf_sha256 AND doi_soat_byte_length = pdf_byte_length AND tep_trang_thai_quet = 'clean')),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        UNIQUE (seal_id, nhanh))""",
    "CREATE INDEX request_y_dinh_dot ON m4.request_y_dinh (dot_id)",
    f"""CREATE OR REPLACE FUNCTION m4.request_y_dinh_bat_bien() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: % chỉ ghi qua hàm định nghĩa M4', TG_TABLE_NAME {_LOI};
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: intent Request không xóa — giữ lịch sử/ID lâu dài' {_LOI};
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW({_CU}) IS DISTINCT FROM ROW({_MOI}) THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: nguồn/canonical/key/cấu hình của intent Request không đổi — nhánh mới mới có canonical khác' {_LOI};
                END IF;
{_MOT_LAN}
                IF OLD.trang_thai = 'DA_DOI_SOAT' AND NEW.trang_thai <> 'DA_DOI_SOAT' THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: intent đã đối soát xong' {_LOI};
                END IF;
                IF NEW.revision <> OLD.revision + 1 THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: revision intent Request tăng đúng 1 mỗi lần ghi' {_LOI};
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER request_y_dinh_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON m4.request_y_dinh FOR EACH ROW EXECUTE FUNCTION m4.request_y_dinh_bat_bien()",
    # --- lịch sử bước (append-only): giữ lại, gửi, kết quả HTTP đã chuẩn hóa (không raw remote error/bearer), quyền còn hay không sau I/O
    f"""CREATE TABLE m4.request_su_kien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        y_dinh_id uuid NOT NULL REFERENCES m4.request_y_dinh(id),
        thu_tu integer NOT NULL CHECK (thu_tu >= 1),
        buoc text NOT NULL CHECK (buoc ~ '^[A-Z_]{{1,40}}$'),
        tu_trang_thai text CHECK (tu_trang_thai IS NULL OR tu_trang_thai IN {_sql_tuple(TRANG_THAI)}),
        den_trang_thai text NOT NULL CHECK (den_trang_thai IN {_sql_tuple(TRANG_THAI)}),
        chi_tiet jsonb NOT NULL DEFAULT '{{}}'::jsonb CHECK (jsonb_typeof(chi_tiet) = 'object' AND octet_length(chi_tiet::text) <= 8000),
        quyen_con boolean NOT NULL,
        boi text NOT NULL,
        luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (y_dinh_id, thu_tu))""",
    # --- biên nhận thao tác của phiên (khóa người dùng): cùng khóa + đúng yêu cầu → cùng intent; khác → từ chối
    """CREATE TABLE m4.request_bien_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        hanh_dong text NOT NULL CHECK (hanh_dong IN """ + _sql_tuple(HANH_DONG) + """),
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        y_dinh_id uuid NOT NULL REFERENCES m4.request_y_dinh(id),
        luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (nguoi_dung_id, khoa))""",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in ("request_su_kien", "request_bien_nhan")),
    # --- quyền hiện hành (không raise, không lộ tồn tại): thấy đợt + tai_pdf (SOAN/DUYET trên đợt đã nộp) + mapping hiện hành của chính phiên
    """CREATE OR REPLACE FUNCTION m4.request_quyen(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE pn uuid; q jsonb; uid uuid; ax_id uuid; ax_rev integer; ax_dn text; tai boolean;
        BEGIN
            SELECT a.phap_nhan_id INTO pn FROM m4.dot x JOIN master.du_an a ON a.id = x.du_an_id WHERE x.id = p_dot;
            IF pn IS NULL OR NOT m4.duyet_doc_dot(p_dot) THEN
                RETURN jsonb_build_object('thay', false, 'tai_pdf', false, 'anh_xa', false, 'tao', false);
            END IF;
            q := m4.duyet_quyen(p_dot);
            tai := coalesce((q->>'tai_pdf')::boolean, false);
            SELECT n.id INTO uid FROM master.nguoi_dung n
                WHERE n.dang_nhap = master.ktt_danh_tinh() AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '');
            IF uid IS NOT NULL THEN
                SELECT m.id, m.revision, m.request_dang_nhap INTO ax_id, ax_rev, ax_dn FROM m4.request_anh_xa m
                    WHERE m.nguoi_dung_id = uid AND m.phap_nhan_id = pn AND m.thu_hoi_luc IS NULL;
            END IF;
            RETURN jsonb_build_object('thay', true, 'tai_pdf', tai, 'anh_xa', ax_id IS NOT NULL, 'tao', tai AND ax_id IS NOT NULL,
                                      'anh_xa_id', ax_id, 'anh_xa_revision', ax_rev, 'nguoi_tao', ax_dn, 'phap_nhan_id', pn);
        END $$""",
    # kiểm quyền cho lệnh (raise mã chính xác) — gọi TRƯỚC biên nhận/intent/ID/blob/mạng
    f"""CREATE OR REPLACE FUNCTION m4.request_kiem(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE q jsonb;
        BEGIN
            PERFORM m4.ai_id();
            q := m4.request_quyen(p_dot);
            IF NOT (q->>'thay')::boolean THEN
                RAISE EXCEPTION 'M4_REQUEST_KHONG_THAY: không thấy đợt (hoặc ngoài phạm vi hiện hành)' {_LOI};
            END IF;
            IF NOT (q->>'tai_pdf')::boolean THEN
                RAISE EXCEPTION 'M4_REQUEST_PHAM_VI: vai hiện hành không được tạo Request từ hồ sơ đã duyệt (cần soạn/duyệt trên đợt đã nộp)' {_LOI};
            END IF;
            IF NOT (q->>'anh_xa')::boolean THEN
                RAISE EXCEPTION 'M4_REQUEST_CHUA_ANH_XA: chưa có mapping nhân viên → Request hiện hành cho pháp nhân này' {_LOI};
            END IF;
            RETURN q;
        END $$""",
    # --- ghi mapping (máy chủ/Root qua kết nối chủ bảng, danh tính phiên hợp lệ): thay thế = thu hồi bản cũ + revision mới
    f"""CREATE OR REPLACE FUNCTION m4.request_anh_xa_dat(p_nguoi_dung uuid, p_phap_nhan uuid, p_dang_nhap text, p_can_cu text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); rv integer; moi uuid;
        BEGIN
            {_TIN_CAY.strip()}
            IF NOT EXISTS (SELECT 1 FROM master.nguoi_dung n WHERE n.id = p_nguoi_dung AND n.trang_thai = 'HOAT_DONG') THEN
                RAISE EXCEPTION 'M4_REQUEST_ANH_XA_SAI: nhân viên không tồn tại hoặc không hoạt động' {_LOI};
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:request_anh_xa:' || p_nguoi_dung::text || ':' || p_phap_nhan::text, 0));
            SELECT coalesce(max(m.revision), 0) + 1 INTO rv FROM m4.request_anh_xa m WHERE m.nguoi_dung_id = p_nguoi_dung AND m.phap_nhan_id = p_phap_nhan;
            UPDATE m4.request_anh_xa SET thu_hoi_luc = now(), thu_hoi_boi = ai, thu_hoi_ly_do = 'Thay bằng revision ' || rv
                WHERE nguoi_dung_id = p_nguoi_dung AND phap_nhan_id = p_phap_nhan AND thu_hoi_luc IS NULL;
            INSERT INTO m4.request_anh_xa (nguoi_dung_id, phap_nhan_id, request_dang_nhap, can_cu, revision, tao_boi, tao_boi_id)
                VALUES (p_nguoi_dung, p_phap_nhan, p_dang_nhap, p_can_cu, rv, ai, aid) RETURNING id INTO moi;
            RETURN jsonb_build_object('id', moi, 'revision', rv);
        END $$""",
    f"""CREATE OR REPLACE FUNCTION m4.request_anh_xa_thu_hoi(p_id uuid, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id();
        BEGIN
            {_TIN_CAY.strip()}
            UPDATE m4.request_anh_xa SET thu_hoi_luc = now(), thu_hoi_boi = ai, thu_hoi_ly_do = p_ly_do WHERE id = p_id AND thu_hoi_luc IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_REQUEST_ANH_XA_SAI: không thấy mapping đang hiệu lực' {_LOI};
            END IF;
            RETURN jsonb_build_object('id', p_id, 'thu_hoi_boi_id', aid);
        END $$""",
    # --- sự kiện nội bộ
    """CREATE OR REPLACE FUNCTION m4._request_su_kien(p_y uuid, p_buoc text, p_tu text, p_den text, p_ct jsonb, p_quyen boolean) RETURNS void
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            INSERT INTO m4.request_su_kien (y_dinh_id, thu_tu, buoc, tu_trang_thai, den_trang_thai, chi_tiet, quyen_con, boi)
                VALUES (p_y, (SELECT coalesce(max(s.thu_tu), 0) + 1 FROM m4.request_su_kien s WHERE s.y_dinh_id = p_y), p_buoc, p_tu, p_den,
                        coalesce(p_ct, '{}'::jsonb), p_quyen, coalesce(master.ktt_danh_tinh(), 'MAY_CHU'));
        END $$""",
    # --- PHA 1 (giao dịch ngắn): quyền → khóa seal → biên nhận → seal/canonical → intent (một/seal/nhánh) → chuyển lease hết hạn → nhận bước → lease
    f"""CREATE OR REPLACE FUNCTION m4.request_giu(p_khoa text, p_hanh text, p_yc jsonb, p_dot uuid, p_seal uuid, p_canonical jsonb, p_canonical_sha text,
                                                  p_buoc text, p_lease_giay integer) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); q jsonb; s record; pdf_len bigint; y m4.request_y_dinh%ROWTYPE;
                b record; lap boolean := false; chan text; lid uuid; nid uuid; tt text; nguon jsonb; ch jsonb; body jsonb; tien jsonb;
        BEGIN
            {_TIN_CAY.strip()}
            IF p_khoa IS NULL OR p_khoa !~ '^[A-Za-z0-9_.:-]{{1,200}}$' THEN
                RAISE EXCEPTION 'M4_KHOA_THAO_TAC: thiếu hoặc sai khóa thao tác' {_LOI};
            END IF;
            IF p_hanh IS NULL OR p_hanh NOT IN {_sql_tuple(HANH_DONG)} OR p_buoc IS NULL OR p_buoc NOT IN {_sql_tuple(BUOC)}
               OR p_lease_giay IS NULL OR p_lease_giay NOT BETWEEN 5 AND 900 OR jsonb_typeof(p_yc) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: tham số giữ intent Request không hợp lệ' {_LOI};
            END IF;
            q := m4.request_kiem(p_dot);
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:request:' || p_seal::text, 0));
            SELECT * INTO b FROM m4.request_bien_nhan x WHERE x.nguoi_dung_id = aid AND x.khoa = p_khoa;
            IF FOUND THEN
                IF b.hanh_dong <> p_hanh OR b.yeu_cau IS DISTINCT FROM p_yc THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' {_LOI};
                END IF;
                lap := true;
            END IF;
            SELECT x.* INTO s FROM m4.duyet_seal x WHERE x.id = p_seal AND x.dot_id = p_dot;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_REQUEST_KHONG_THAY: không thấy seal hồ sơ của đợt' {_LOI};
            END IF;
            SELECT p.byte_length INTO pdf_len FROM m4.duyet_pdf p WHERE p.id = s.pdf_id;
            SELECT * INTO y FROM m4.request_y_dinh x WHERE x.seal_id = p_seal AND x.nhanh = 'GOC' FOR UPDATE;
            IF NOT FOUND THEN
                IF p_hanh <> 'REQUEST_TAO' OR p_buoc <> 'TAO' THEN
                    RAISE EXCEPTION 'M4_REQUEST_CHUA_CO_Y_DINH: chưa có intent Request cho hồ sơ đã seal này' {_LOI};
                END IF;
                IF EXISTS (SELECT 1 FROM m4.duyet_phien_ban z WHERE z.parent_id = s.phien_ban_id) THEN
                    RAISE EXCEPTION 'M4_REQUEST_PHIEN_BAN_CU: phiên bản đã có bản kế tiếp — nhánh đính chính chưa triển khai ở gói này' {_LOI};
                END IF;
                IF s.so_lieu->>'so_xin_thanh_toan' IS NULL OR s.so_lieu->>'tien_te' IS NULL THEN
                    RAISE EXCEPTION 'M4_REQUEST_THIEU_SO_TIEN: seal không có số xin thanh toán/tiền tệ' {_LOI};
                END IF;
                IF jsonb_typeof(p_canonical) IS DISTINCT FROM 'object' OR p_canonical_sha IS NULL OR p_canonical_sha !~ '^[0-9a-f]{{64}}$' THEN
                    RAISE EXCEPTION 'M4_REQUEST_CANONICAL_SAI: canonical intent không hợp lệ' {_LOI};
                END IF;
                nguon := p_canonical->'nguon'; ch := p_canonical->'cau_hinh'; body := p_canonical->'body';
                IF nguon IS DISTINCT FROM jsonb_build_object(
                        'dot_id', s.dot_id, 'hop_dong_id', s.hop_dong_id, 'du_an_id', s.du_an_id, 'phap_nhan_id', s.phap_nhan_id,
                        'phien_ban_id', s.phien_ban_id, 'seal_id', s.id, 'quyet_dinh_id', s.quyet_dinh_id, 'ket_luan_id', s.ket_luan_id,
                        'graph_sha256', s.graph_sha256, 'so_lieu_sha256', s.so_lieu_sha256, 'so_tien', s.so_lieu->>'so_xin_thanh_toan',
                        'tien_te', s.so_lieu->>'tien_te', 'pdf_id', s.pdf_id, 'pdf_sha256', s.pdf_sha256, 'pdf_byte_length', pdf_len, 'nhanh', 'GOC') THEN
                    RAISE EXCEPTION 'M4_REQUEST_NGUON_LECH: canonical không khớp seal/PDF/số xin thanh toán đã chốt' {_LOI};
                END IF;
                IF p_canonical->'actor' IS DISTINCT FROM jsonb_build_object('id', aid, 'dang_nhap', ai)
                   OR p_canonical->'anh_xa' IS DISTINCT FROM jsonb_build_object('id', q->'anh_xa_id', 'revision', q->'anh_xa_revision', 'nguoi_tao', q->'nguoi_tao') THEN
                    RAISE EXCEPTION 'M4_REQUEST_NGUON_LECH: actor/mapping trong canonical khác phiên/mapping hiện hành' {_LOI};
                END IF;
                IF jsonb_typeof(ch) IS DISTINCT FROM 'object' OR coalesce(ch->>'sha256', '') !~ '^[0-9a-f]{{64}}$'
                   OR jsonb_typeof(ch->'phien_ban') IS DISTINCT FROM 'number' OR coalesce(ch->>'truong_tien', '') = ''
                   OR jsonb_typeof(body) IS DISTINCT FROM 'object' OR body->>'nhom' IS DISTINCT FROM ch->>'nhom' OR body->>'nguoiTao' IS DISTINCT FROM q->>'nguoi_tao' THEN
                    RAISE EXCEPTION 'M4_REQUEST_CANONICAL_SAI: cấu hình/body canonical thiếu hoặc lệch nhóm/người đứng tên' {_LOI};
                END IF;
                tien := jsonb_build_object('amount', s.so_lieu->>'so_xin_thanh_toan', 'currency', s.so_lieu->>'tien_te');
                IF body->'giaTri'->(ch->>'truong_tien') IS DISTINCT FROM tien THEN
                    RAISE EXCEPTION 'M4_REQUEST_NGUON_LECH: số tiền body khác số xin thanh toán + tiền tệ đã seal' {_LOI};
                END IF;
                nid := gen_random_uuid();
                INSERT INTO m4.request_y_dinh (id, phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, seal_id, nhanh, actor_id, actor, anh_xa_id,
                        anh_xa_revision, nguoi_tao, canonical, canonical_sha256, idem_key, cau_hinh_sha256, khoa_ref, nhom, nhom_phien_ban, so_tien,
                        tien_te, pdf_id, pdf_sha256, pdf_byte_length, trang_thai)
                    VALUES (nid, s.phap_nhan_id, s.du_an_id, s.hop_dong_id, s.dot_id, s.phien_ban_id, s.id, 'GOC', aid, ai, (q->>'anh_xa_id')::uuid,
                            (q->>'anh_xa_revision')::integer, q->>'nguoi_tao', p_canonical, p_canonical_sha, 'm4-request:' || nid::text, ch->>'sha256',
                            ch->>'khoa_ref', ch->>'nhom', (ch->>'phien_ban')::integer, s.so_lieu->>'so_xin_thanh_toan', s.so_lieu->>'tien_te', s.pdf_id,
                            s.pdf_sha256, pdf_len, 'MOI')
                    RETURNING * INTO y;
                PERFORM m4._request_su_kien(y.id, 'Y_DINH', NULL, 'MOI', jsonb_build_object('canonical_sha256', p_canonical_sha), true);
            ELSE
                IF y.actor_id <> aid THEN
                    RAISE EXCEPTION 'M4_REQUEST_NGUOI_KHAC: hồ sơ đã có intent Request của nhân viên khác — không tiếp quản' {_LOI};
                END IF;
                IF (q->>'anh_xa_id')::uuid IS DISTINCT FROM y.anh_xa_id THEN
                    chan := 'ANH_XA_DOI';
                ELSIF p_canonical_sha IS DISTINCT FROM y.canonical_sha256 THEN
                    chan := 'CAN_CU_DOI';
                END IF;
            END IF;
            IF NOT lap THEN
                INSERT INTO m4.request_bien_nhan (nguoi_dung_id, khoa, hanh_dong, yeu_cau, y_dinh_id) VALUES (aid, p_khoa, p_hanh, p_yc, y.id);
            END IF;
            IF chan IS NOT NULL THEN
                PERFORM m4._request_su_kien(y.id, 'CHAN', y.trang_thai, y.trang_thai, jsonb_build_object('chan', chan, 'buoc', p_buoc), true);
                RETURN jsonb_build_object('lap_lai', lap, 'chan', chan, 'lease_id', NULL, 'y_dinh', to_jsonb(y));
            END IF;
            IF y.lease_id IS NOT NULL AND y.lease_het > now() THEN
                RAISE EXCEPTION 'M4_REQUEST_DANG_XU_LY: intent đang có bước khác xử lý — chờ rồi xem lại trạng thái' {_LOI};
            END IF;
            IF y.lease_id IS NOT NULL THEN  -- lease hết hạn mà chưa ghi kết quả: bước có thể ĐÃ gửi → chưa rõ, không làm lại mù
                tt := y.trang_thai;
                UPDATE m4.request_y_dinh SET
                        trang_thai = CASE WHEN y.lease_buoc = 'TAO' THEN 'CHUA_RO_TAO' WHEN y.lease_buoc = 'TAI' THEN 'CHUA_RO_TAI' ELSE trang_thai END,
                        co_chua_ro = co_chua_ro OR y.lease_buoc = 'TAO', lease_id = NULL, lease_buoc = NULL, lease_het = NULL,
                        revision = revision + 1, cap_nhat_luc = now()
                    WHERE id = y.id RETURNING * INTO y;
                PERFORM m4._request_su_kien(y.id, 'LEASE_HET', tt, y.trang_thai, '{{}}'::jsonb, true);
            END IF;
            IF NOT ((p_buoc = 'TAO' AND y.trang_thai IN ('MOI','CHUA_RO_TAO','TU_CHOI_TAO'))
                    OR (p_buoc = 'DOC' AND y.remote_id IS NOT NULL)
                    OR (p_buoc = 'TAI' AND y.trang_thai = 'DA_TAO_NHAP')
                    OR (p_buoc = 'DOI_SOAT' AND y.trang_thai IN ('CHUA_RO_TAI','CHO_QUET'))) THEN
                RETURN jsonb_build_object('lap_lai', lap, 'chan', 'BUOC_KHONG_HOP', 'lease_id', NULL, 'y_dinh', to_jsonb(y));
            END IF;
            IF p_buoc = 'TAO' AND y.co_chua_ro AND y.lan_tao_dau <= now() - interval '{CUA_SO_GUI_LAI_GIO} hours' THEN
                tt := y.trang_thai;
                UPDATE m4.request_y_dinh SET trang_thai = 'HOLD', hold_ma = 'CHUA_RO_QUA_HAN_IDEM', revision = revision + 1, cap_nhat_luc = now()
                    WHERE id = y.id RETURNING * INTO y;
                PERFORM m4._request_su_kien(y.id, 'CHAN', tt, 'HOLD', jsonb_build_object('chan', 'CHUA_RO_QUA_HAN_IDEM'), true);
                RETURN jsonb_build_object('lap_lai', lap, 'chan', 'CHUA_RO_QUA_HAN_IDEM', 'lease_id', NULL, 'y_dinh', to_jsonb(y));
            END IF;
            lid := gen_random_uuid();
            UPDATE m4.request_y_dinh SET lease_id = lid, lease_buoc = p_buoc, lease_het = now() + make_interval(secs => p_lease_giay),
                    lan_tao_dau = CASE WHEN p_buoc = 'TAO' THEN coalesce(lan_tao_dau, now()) ELSE lan_tao_dau END,
                    so_lan_tao = so_lan_tao + (p_buoc = 'TAO')::integer, so_lan_tai = so_lan_tai + (p_buoc = 'TAI')::integer,
                    revision = revision + 1, cap_nhat_luc = now()
                WHERE id = y.id RETURNING * INTO y;
            PERFORM m4._request_su_kien(y.id, 'GIU_' || p_buoc, y.trang_thai, y.trang_thai, jsonb_build_object('lease_id', lid), true);
            RETURN jsonb_build_object('lap_lai', lap, 'chan', NULL, 'lease_id', lid, 'y_dinh', to_jsonb(y));
        END $$""",
    # --- PHA 2 (sau HTTP): CAS đúng lease + revision; chuyển hợp lệ theo bước; ghi bằng chứng KỂ CẢ khi quyền đã đổi (trả quyen_con)
    f"""CREATE OR REPLACE FUNCTION m4.request_ghi(p_y_dinh uuid, p_lease uuid, p_revision integer, p_kq jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE y m4.request_y_dinh%ROWTYPE; den text; tu text; bc text; q jsonb; ok boolean;
        BEGIN
            {_TIN_CAY.strip()}
            IF jsonb_typeof(p_kq) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: kết quả bước không hợp lệ' {_LOI};
            END IF;
            SELECT * INTO y FROM m4.request_y_dinh x WHERE x.id = p_y_dinh FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_REQUEST_KHONG_THAY: không thấy intent Request' {_LOI};
            END IF;
            IF y.lease_id IS DISTINCT FROM p_lease OR y.revision <> p_revision THEN
                RAISE EXCEPTION 'M4_REQUEST_LEASE_MAT: bước đã hết quyền ghi (lease/revision đổi) — xem lại trạng thái, không ghi đè' {_LOI};
            END IF;
            den := p_kq->>'den'; tu := y.trang_thai; bc := y.lease_buoc;
            IF den IS NULL OR NOT ((bc = 'TAO' AND den IN ('DA_TAO','CHUA_RO_TAO','TU_CHOI_TAO','HOLD'))
                    OR (bc = 'DOC' AND (den = tu OR (tu = 'DA_TAO' AND den IN ('DA_TAO_NHAP','HOLD'))))
                    OR (bc = 'TAI' AND den IN ('CHO_QUET','CHUA_RO_TAI','DA_TAO_NHAP','HOLD'))
                    OR (bc = 'DOI_SOAT' AND den IN ('DA_DOI_SOAT','CHO_QUET','CHUA_RO_TAI','HOLD'))) THEN
                RAISE EXCEPTION 'M4_REQUEST_CHUYEN_SAI: chuyển trạng thái không hợp lệ cho bước' {_LOI};
            END IF;
            IF (p_kq ? 'remote_id' AND y.remote_id IS NOT NULL AND p_kq->>'remote_id' IS DISTINCT FROM y.remote_id::text)
               OR (p_kq ? 'remote_tep_id' AND y.remote_tep_id IS NOT NULL AND p_kq->>'remote_tep_id' IS DISTINCT FROM y.remote_tep_id::text) THEN
                RAISE EXCEPTION 'M4_REQUEST_REMOTE_ID_KHAC: ID Request/tệp đã ghi khác kết quả mới — giữ ID cũ, đối soát tay' {_LOI};
            END IF;
            -- bằng chứng đối soát ghi MỘT lần: quan sát sau hoàn tất (thiếu proof) giữ bản đã lưu; proof mới KHÁC bản đã lưu → từ chối rõ
            IF (nullif(p_kq->>'doi_soat_sha256', '') IS NOT NULL AND y.doi_soat_sha256 IS NOT NULL
                    AND p_kq->>'doi_soat_sha256' IS DISTINCT FROM y.doi_soat_sha256)
               OR (nullif(p_kq->>'doi_soat_byte_length', '') IS NOT NULL AND y.doi_soat_byte_length IS NOT NULL
                    AND (p_kq->>'doi_soat_byte_length')::bigint IS DISTINCT FROM y.doi_soat_byte_length) THEN
                RAISE EXCEPTION 'M4_REQUEST_BANG_CHUNG_KHAC: bằng chứng đối soát mới khác bằng chứng đã lưu — giữ bản cũ, đối soát tay' {_LOI};
            END IF;
            IF den = 'HOLD' AND coalesce(p_kq->>'hold_ma', y.hold_ma, '') !~ '^[A-Z0-9_]{{1,60}}$' THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: HOLD cần mã lý do' {_LOI};
            END IF;
            q := m4.request_quyen(y.dot_id);
            ok := coalesce((q->>'tao')::boolean, false) AND (q->>'anh_xa_id')::uuid IS NOT DISTINCT FROM y.anh_xa_id;
            UPDATE m4.request_y_dinh SET
                    trang_thai = den,
                    hold_ma = CASE WHEN den = 'HOLD' THEN coalesce(p_kq->>'hold_ma', hold_ma) ELSE NULL END,
                    remote_id = coalesce(remote_id, nullif(p_kq->>'remote_id', '')::uuid),
                    remote_ma = coalesce(remote_ma, nullif(p_kq->>'remote_ma', '')),
                    remote_trang_thai = coalesce(nullif(p_kq->>'remote_trang_thai', ''), remote_trang_thai),
                    remote_tep_id = coalesce(remote_tep_id, nullif(p_kq->>'remote_tep_id', '')::uuid),
                    tep_trang_thai_quet = coalesce(nullif(p_kq->>'tep_trang_thai_quet', ''), tep_trang_thai_quet),
                    doi_soat_sha256 = CASE WHEN den = 'DA_DOI_SOAT' THEN coalesce(doi_soat_sha256, nullif(p_kq->>'doi_soat_sha256', ''))
                                           ELSE doi_soat_sha256 END,
                    doi_soat_byte_length = CASE WHEN den = 'DA_DOI_SOAT'
                                                THEN coalesce(doi_soat_byte_length, nullif(p_kq->>'doi_soat_byte_length', '')::bigint)
                                                ELSE doi_soat_byte_length END,
                    co_chua_ro = co_chua_ro OR den = 'CHUA_RO_TAO',
                    lease_id = NULL, lease_buoc = NULL, lease_het = NULL, revision = revision + 1, cap_nhat_luc = now()
                WHERE id = y.id RETURNING * INTO y;
            PERFORM m4._request_su_kien(y.id, 'GHI_' || bc, tu, den, coalesce(p_kq->'chi_tiet', '{{}}'::jsonb), ok);
            RETURN jsonb_build_object('quyen_con', ok, 'y_dinh', to_jsonb(y));
        END $$""",
    # --- quyền thực thi + RLS đọc
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_LENH) + " FROM PUBLIC",
    "REVOKE ALL ON " + ", ".join(f"m4.{t}" for t in BANG) + " FROM PUBLIC",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON """ + ", ".join(f"m4.{t}" for t in BANG) + """ TO app_web;
            CREATE POLICY request_y_dinh_web ON m4.request_y_dinh FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY request_su_kien_web ON m4.request_su_kien FOR SELECT TO app_web
                USING (EXISTS (SELECT 1 FROM m4.request_y_dinh y WHERE y.id = y_dinh_id AND m4.duyet_doc_dot(y.dot_id)));
            CREATE POLICY request_anh_xa_web ON m4.request_anh_xa FOR SELECT TO app_web
                USING (master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), ''));
            CREATE POLICY request_bien_nhan_web ON m4.request_bien_nhan FOR SELECT TO app_web
                USING (master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), ''));
        END IF;
    END $$""",
)
