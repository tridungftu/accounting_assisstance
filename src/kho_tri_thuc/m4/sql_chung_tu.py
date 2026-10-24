"""M4-02B — M22 (append sau actual 1–21): bản ghi Chứng từ L3 hữu hạn. CHỈ hằng SQL (không import ha_tang; pg_migrations.py import và append registry).

- Phạm vi bộ chứng từ = ĐỢT (m4.dot) + các tệp đã gắn đợt (m4.dot_tep) — không master bộ hồ sơ mới.
- m4.chung_tu_revision: revision metadata L3 của đợt (loại/số/ngày/bỏ khỏi bộ theo tệp) — chỉ ghi thêm, mỗi revision chứa bản HIỆU LỰC tích lũy + phần
  thay đổi + actor/lý do/lần chạy gốc; không sửa raw/kết quả trích cũ.
- m4.chung_tu_manual_map: ghép tay dòng chứng từ (row_id ổn định do máy chủ cấp từ raw SHA-256 + vị trí) → dòng BOQ typed hiệu lực tại ngày NT.
- m4.chung_tu_run / _result / _artifact: lần chạy L3 (PN/dự án/HĐ/đợt, revision metadata dùng, basis + SHA, engine + pin, yêu cầu gốc + khóa,
  quyền SOAN|REVIEW, trạng thái như M19, run cha khi Chạy lại); kết quả tách finding nguồn khỏi coverage; artifact BASIS/INPUT/RESULT/REPORT_L3/LOG.
- m4.chung_tu_giu_khoa: giữ chỗ (actor, khóa) cho lệnh chạy/chạy lại — COMMIT trước snapshot RR (cùng mẫu M19 FIX02 F4).
- Quyền: SOAN đúng dự án (mọi đợt của dự án) HOẶC REVIEW đúng dự án CHỈ trên đợt DA_NOP; XEM chỉ đọc. Phân tích/metadata/ghép tay KHÔNG phải duyệt.
- Biên nhận: dùng lại m4.bien_nhan + m4._bn_tra/_bn_ghi (namespace actor+khóa chung với M17/M19). Khóa đã giữ chỗ cho L3 chặn biên nhận/giữ chỗ
  Review khác hành động/body và ngược lại (trigger mới trên bien_nhan và review_giu_khoa — không sửa định nghĩa M17/M19/M20/M21).
- Không DROP/DELETE; không đổi bảng/hàm/checksum 1–21; không tạo role/quyền nghiệp vụ mới.
"""

from __future__ import annotations

_LOI = "USING ERRCODE = 'P0001'"
_HEX = "~ '^[0-9a-f]{64}$'"
LOAI_TAI_LIEU = ("BB_NT", "BB_GN", "PL", "CO", "CQ", "BB_LD", "KHAC")
TRANG_THAI_RUN = ("PENDING", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "STALE", "CANCELLED")
LOAI_ARTIFACT = ("BASIS", "INPUT", "RESULT", "REPORT_L3", "LOG")
HANH_DONG_CHAY = ("CHUNG_TU_CHAY", "CHUNG_TU_CHAY_LAI")
HANH_DONG = HANH_DONG_CHAY + ("CHUNG_TU_SUA", "CHUNG_TU_GHEP")
_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.chung_tu_run'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường tin cậy của máy chủ ghi chứng từ L3' """ + _LOI + """;
            END IF;"""
_KB = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); cu jsonb; kq jsonb;"


def _sql_tuple(xs) -> str:
    return "(" + ",".join(f"'{x}'" for x in xs) + ")"


_TT_SQL, _ART_SQL, _HDC_SQL, _HD_SQL, _LOAI_SQL = (_sql_tuple(TRANG_THAI_RUN), _sql_tuple(LOAI_ARTIFACT), _sql_tuple(HANH_DONG_CHAY), _sql_tuple(HANH_DONG),
                                                   _sql_tuple(LOAI_TAI_LIEU))
# xung đột khóa đã giữ chỗ (L3 hoặc Review) cùng actor với hành động/body khác — kiểm dưới khóa giao dịch biên nhận, TRƯỚC mọi hiệu lực
_XUNG_DOT_GIU = """
            IF EXISTS (SELECT 1 FROM m4.chung_tu_giu_khoa g WHERE g.nguoi_dung_id = aid AND g.khoa = p_khoa
                       AND (g.hanh_dong <> {hanh} OR g.yeu_cau <> p_yc))
               OR EXISTS (SELECT 1 FROM m4.review_giu_khoa g WHERE g.nguoi_dung_id = aid AND g.khoa = p_khoa) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho yêu cầu khác' """ + _LOI + """;
            END IF;"""

HAM_LENH = ("m4.chung_tu_tra(text, text, uuid, jsonb)",
            "m4.chung_tu_giu(text, text, uuid, jsonb)",
            "m4.chung_tu_tao_run(text, text, jsonb, text, uuid, integer, jsonb, text, text, text, uuid)",
            "m4.chung_tu_cong_bo(uuid, jsonb, text, jsonb, text, text, jsonb, text)",
            "m4.chung_tu_huy(uuid, text, jsonb, jsonb)",
            "m4.chung_tu_ghi_revision(text, jsonb, uuid, integer, jsonb, text)",
            "m4.chung_tu_ghi_map(text, jsonb, uuid, text, uuid, integer, text, integer, text, uuid, jsonb, text)",
            "m4.chung_tu_kiem(uuid)")
HAM_DOC = ("m4.chung_tu_quyen(uuid)", "m4.chung_tu_doc_dot(uuid)", "m4.chung_tu_doc_duoc(uuid)")
BANG = ("chung_tu_run", "chung_tu_result", "chung_tu_artifact", "chung_tu_revision", "chung_tu_manual_map", "chung_tu_giu_khoa")

M0022_M4_CHUNG_TU = (
    "SET LOCAL check_function_bodies = off",
    f"""CREATE TABLE m4.chung_tu_run (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL REFERENCES m4.dot(id),
        revision integer NOT NULL CHECK (revision >= 0),
        basis jsonb NOT NULL CHECK (jsonb_typeof(basis) = 'object'),
        basis_sha256 text NOT NULL CHECK (basis_sha256 {_HEX}),
        engine text NOT NULL CHECK (length(engine) BETWEEN 1 AND 400),
        engine_sha256 text NOT NULL CHECK (engine_sha256 {_HEX}),
        hanh_dong text NOT NULL CHECK (hanh_dong IN {_HDC_SQL}),
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        yeu_cau_sha256 text NOT NULL CHECK (yeu_cau_sha256 {_HEX}),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        quyen text NOT NULL CHECK (quyen IN ('SOAN','REVIEW')),
        trang_thai text NOT NULL DEFAULT 'RUNNING' CHECK (trang_thai IN {_TT_SQL}),
        parent_run_id uuid REFERENCES m4.chung_tu_run(id),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) <= 2000),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        xong_luc timestamptz,
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        CHECK ((trang_thai IN ('PENDING','RUNNING')) = (xong_luc IS NULL)),
        UNIQUE (tao_boi_id, khoa),
        UNIQUE (id, du_an_id))""",
    # định danh bất biến; chỉ chủ bảng; không xóa; chỉ MỘT lần từ PENDING/RUNNING sang trạng thái cuối (cùng mẫu m4.review_run_kiem)
    """CREATE OR REPLACE FUNCTION m4.chung_tu_run_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: lần chạy chứng từ L3 chỉ ghi qua hàm định nghĩa trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không xóa lần chạy chứng từ L3 (giữ lịch sử/bằng chứng)' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai NOT IN ('PENDING','RUNNING') OR NEW.xong_luc IS NOT NULL THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: lần chạy mới phải ở PENDING/RUNNING' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.trang_thai NOT IN ('PENDING','RUNNING') THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_DA_CHOT: lần chạy đã ở trạng thái cuối %', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.du_an_id, NEW.hop_dong_id, NEW.dot_id, NEW.revision, NEW.basis, NEW.basis_sha256, NEW.engine,
                   NEW.engine_sha256, NEW.hanh_dong, NEW.yeu_cau, NEW.yeu_cau_sha256, NEW.khoa, NEW.quyen, NEW.parent_run_id, NEW.tao_boi, NEW.tao_boi_id,
                   NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.du_an_id, OLD.hop_dong_id, OLD.dot_id, OLD.revision, OLD.basis, OLD.basis_sha256,
                   OLD.engine, OLD.engine_sha256, OLD.hanh_dong, OLD.yeu_cau, OLD.yeu_cau_sha256, OLD.khoa, OLD.quyen, OLD.parent_run_id, OLD.tao_boi,
                   OLD.tao_boi_id, OLD.tao_luc) THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không sửa định danh/căn cứ của lần chạy chứng từ L3' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_run_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.chung_tu_run FOR EACH ROW EXECUTE FUNCTION m4.chung_tu_run_kiem()",
    f"""CREATE TABLE m4.chung_tu_result (
        run_id uuid PRIMARY KEY,
        du_an_id uuid NOT NULL,
        ket_qua jsonb NOT NULL CHECK (jsonb_typeof(ket_qua) = 'object'),
        ket_qua_sha256 text NOT NULL CHECK (ket_qua_sha256 {_HEX}),
        coverage jsonb NOT NULL CHECK (jsonb_typeof(coverage) = 'object'),
        cong_bo boolean NOT NULL,
        basis_cong_bo_sha256 text CHECK (basis_cong_bo_sha256 IS NULL OR basis_cong_bo_sha256 {_HEX}),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.chung_tu_run (id, du_an_id))""",
    f"""CREATE TABLE m4.chung_tu_artifact (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN {_ART_SQL}),
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 200 AND strpos(ten, '/') = 0 AND strpos(ten, chr(92)) = 0 AND ten !~ '[[:cntrl:]]'),
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        object_key text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'm4-chung-tu/' || raw_sha256),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.chung_tu_run (id, du_an_id),
        UNIQUE (run_id, loai))""",
    """CREATE TABLE m4.chung_tu_revision (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL REFERENCES m4.dot(id),
        revision integer NOT NULL CHECK (revision >= 1),
        parent_revision integer NOT NULL CHECK (parent_revision >= 0),
        run_id uuid NOT NULL,
        tai_lieu jsonb NOT NULL CHECK (jsonb_typeof(tai_lieu) = 'object'),
        thay_doi jsonb NOT NULL CHECK (jsonb_typeof(thay_doi) = 'array'),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) BETWEEN 1 AND 1000),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.chung_tu_run (id, du_an_id),
        CHECK (parent_revision = revision - 1),
        UNIQUE (dot_id, revision))""",
    f"""CREATE TABLE m4.chung_tu_manual_map (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL REFERENCES m4.dot(id),
        row_id text NOT NULL CHECK (row_id {_HEX}),
        revision integer NOT NULL CHECK (revision >= 1),
        boq_id uuid NOT NULL,
        boq_dong integer NOT NULL,
        ma_hm text NOT NULL CHECK (length(ma_hm) BETWEEN 1 AND 500),
        run_id uuid NOT NULL,
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        locator jsonb NOT NULL CHECK (jsonb_typeof(locator) = 'object'),
        ten_dong text CHECK (ten_dong IS NULL OR length(ten_dong) <= 500),
        revision_chung_tu integer NOT NULL CHECK (revision_chung_tu >= 0),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) BETWEEN 1 AND 1000),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (boq_id, boq_dong) REFERENCES m4.boq_dong (boq_id, dong),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.chung_tu_run (id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id, raw_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
        UNIQUE (dot_id, row_id, revision))""",
    f"""CREATE TABLE m4.chung_tu_giu_khoa (
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        hanh_dong text NOT NULL CHECK (hanh_dong IN {_HDC_SQL}),
        du_an_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (nguoi_dung_id, khoa))""",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in ("chung_tu_result", "chung_tu_artifact", "chung_tu_revision", "chung_tu_manual_map", "chung_tu_giu_khoa")),
    # --- quyền L3 của phiên trên MỘT đợt (không raise): SOAN đúng dự án, hoặc REVIEW đúng dự án khi đợt DA_NOP. Biến %TYPE (không record chưa gán).
    """CREATE OR REPLACE FUNCTION m4.chung_tu_quyen(p_dot uuid) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d_du_an m4.dot.du_an_id%TYPE; d_tt m4.dot.trang_thai%TYPE;
        BEGIN
            SELECT x.du_an_id, x.trang_thai INTO d_du_an, d_tt FROM m4.dot x WHERE x.id = p_dot;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            IF master.m4_duoc(d_du_an, 'SOAN') THEN
                RETURN 'SOAN';
            END IF;
            IF d_tt = 'DA_NOP' AND master.m4_duoc(d_du_an, 'REVIEW') THEN
                RETURN 'REVIEW';
            END IF;
            RETURN NULL;
        END $$""",
    # đọc bộ chứng từ của đợt: XEM dự án (gồm phụ trách), hoặc REVIEW khi đợt DA_NOP
    """CREATE OR REPLACE FUNCTION m4.chung_tu_doc_dot(p_dot uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.dot d WHERE d.id = p_dot AND (master.m4_duoc(d.du_an_id, 'XEM')
                       OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')))
        $$""",
    """CREATE OR REPLACE FUNCTION m4.chung_tu_doc_duoc(p_run uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.chung_tu_run r WHERE r.id = p_run AND m4.chung_tu_doc_dot(r.dot_id))
        $$""",
    # có raise với mã chính xác — mọi lệnh gọi TRƯỚC tra biên nhận/đọc raw. Không lộ tồn tại đợt cho phiên không có quyền gì trên dự án (404).
    """CREATE OR REPLACE FUNCTION m4.chung_tu_kiem(p_dot uuid) RETURNS text
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE q text; d_du_an m4.dot.du_an_id%TYPE;
        BEGIN
            q := m4.chung_tu_quyen(p_dot);
            IF q IS NOT NULL THEN
                RETURN q;
            END IF;
            SELECT x.du_an_id INTO d_du_an FROM m4.dot x WHERE x.id = p_dot;
            IF NOT FOUND OR NOT (master.m4_duoc(d_du_an, 'XEM') OR master.m4_duoc(d_du_an, 'REVIEW')) THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_KHONG_THAY: không thấy đợt (hoặc ngoài phạm vi hiện hành)' USING ERRCODE = 'P0001';
            END IF;
            RAISE EXCEPTION 'M4_CHUNG_TU_PHAM_VI: chạy/sửa chứng từ L3 cần quyền soạn đúng dự án, hoặc review trên đợt đã nộp' USING ERRCODE = 'P0001';
        END $$""",
    # tra biên nhận L3 (sửa/ghép, hoặc chạy khi đã có FINAL): quyền + phạm vi hiện hành TRƯỚC, rồi khóa giao dịch biên nhận + xung đột giữ chỗ + _bn_tra
    """CREATE OR REPLACE FUNCTION m4.chung_tu_tra(p_khoa text, p_hanh text, p_dot uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE aid uuid; d_du_an m4.dot.du_an_id%TYPE;
        BEGIN""" + _TIN_CAY + f"""
            IF p_hanh NOT IN {_HD_SQL} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động chứng từ L3 không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.chung_tu_kiem(p_dot);
            aid := m4.ai_id();
            SELECT x.du_an_id INTO d_du_an FROM m4.dot x WHERE x.id = p_dot;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || aid::text || ':' || p_khoa, 0));""" + _XUNG_DOT_GIU.format(hanh="p_hanh") + """
            RETURN m4._bn_tra(aid, p_khoa, p_hanh, d_du_an, p_yc);
        END $$""",
    # bước 1 của lệnh CHẠY/CHẠY LẠI — giao dịch READ COMMITTED ngắn: quyền → khóa biên nhận → FINAL cũ hoặc xung đột → giữ chỗ (actor, khóa).
    # Người gọi COMMIT trước khi mở snapshot RR. Khóa đã giữ chỗ cho Review cùng actor → xung đột (không dùng chung khóa giữa L3 và Review).
    """CREATE OR REPLACE FUNCTION m4.chung_tu_giu(p_khoa text, p_hanh text, p_dot uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE aid uuid; g record; cu jsonb; d_du_an m4.dot.du_an_id%TYPE;
        BEGIN""" + _TIN_CAY + f"""
            IF p_hanh NOT IN {_HDC_SQL} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động giữ chỗ chứng từ L3 không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.chung_tu_kiem(p_dot);
            aid := m4.ai_id();
            SELECT x.du_an_id INTO d_du_an FROM m4.dot x WHERE x.id = p_dot;
            cu := m4._bn_tra(aid, p_khoa, p_hanh, d_du_an, p_yc);  -- khóa giao dịch m4:bien_nhan:(actor,khóa) giữ tới COMMIT của bước này
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            IF EXISTS (SELECT 1 FROM m4.review_giu_khoa r WHERE r.nguoi_dung_id = aid AND r.khoa = p_khoa) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho lệnh Review' {_LOI};
            END IF;
            SELECT * INTO g FROM m4.chung_tu_giu_khoa WHERE nguoi_dung_id = aid AND khoa = p_khoa;
            IF FOUND THEN
                IF g.hanh_dong <> p_hanh OR g.yeu_cau <> p_yc OR g.dot_id <> p_dot THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' {_LOI};
                END IF;
            ELSE
                INSERT INTO m4.chung_tu_giu_khoa (nguoi_dung_id, khoa, hanh_dong, du_an_id, dot_id, yeu_cau) VALUES (aid, p_khoa, p_hanh, d_du_an, p_dot, p_yc);
            END IF;
            RETURN jsonb_build_object('lap_lai', false);
        END $$""",
    # biên nhận M17/M19 (và L3 sửa/ghép) cùng actor+khóa đã giữ chỗ cho lệnh L3 khác hành động/body → chặn trong CÙNG giao dịch hiệu lực
    """CREATE OR REPLACE FUNCTION m4.chung_tu_bn_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM m4.chung_tu_giu_khoa g WHERE g.nguoi_dung_id = NEW.nguoi_dung_id AND g.khoa = NEW.khoa
                       AND (g.hanh_dong <> NEW.hanh_dong OR g.yeu_cau <> NEW.yeu_cau)) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho lệnh chứng từ L3 khác' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_chung_tu_khoa BEFORE INSERT ON m4.bien_nhan FOR EACH ROW EXECUTE FUNCTION m4.chung_tu_bn_khoa()",
    # Review giữ chỗ (actor, khóa) đã giữ cho L3 → chặn TRƯỚC khi Review tạo lần chạy (không đổi hàm M19; trigger mới trên bảng M19)
    """CREATE OR REPLACE FUNCTION m4.chung_tu_review_giu_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM m4.chung_tu_giu_khoa g WHERE g.nguoi_dung_id = NEW.nguoi_dung_id AND g.khoa = NEW.khoa) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho lệnh chứng từ L3' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER review_giu_khoa_chung_tu BEFORE INSERT ON m4.review_giu_khoa FOR EACH ROW EXECUTE FUNCTION m4.chung_tu_review_giu_khoa()",
    # tạo lần chạy RUNNING sau khi máy chủ chụp basis trong một snapshot REPEATABLE READ (cùng giao dịch); revision metadata L3 kiểm CAS hiện hành
    """CREATE OR REPLACE FUNCTION m4.chung_tu_tao_run(p_khoa text, p_hanh text, p_yc jsonb, p_yc_sha text, p_dot uuid, p_revision integer, p_basis jsonb,
                                                      p_basis_sha text, p_engine text, p_engine_sha text, p_parent uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ q text; r record; d record; p record; moi uuid; pn uuid; rv integer;
        BEGIN""" + _TIN_CAY + f"""
            q := m4.chung_tu_kiem(p_dot);
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            cu := m4._bn_tra(aid, p_khoa, p_hanh, d.du_an_id, p_yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            SELECT * INTO r FROM m4.chung_tu_run WHERE tao_boi_id = aid AND khoa = p_khoa;
            IF FOUND THEN
                IF r.hanh_dong <> p_hanh OR r.yeu_cau <> p_yc THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' {_LOI};
                END IF;
                RETURN jsonb_build_object('lap_lai', true, 'dang_chay', r.trang_thai IN ('PENDING','RUNNING'),
                                          'ket_qua', jsonb_build_object('run_id', r.id, 'trang_thai', r.trang_thai, 'basis_sha256', r.basis_sha256));
            END IF;
            IF p_hanh NOT IN {_HDC_SQL} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động chạy chứng từ L3 không hợp lệ' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.chung_tu_revision x WHERE x.dot_id = p_dot;
            IF p_revision IS NULL OR rv <> p_revision THEN
                RAISE EXCEPTION 'M4_REVISION_CU: metadata chứng từ của đợt đã có revision mới (hiện tại %) — tải lại rồi chạy', rv {_LOI};
            END IF;
            IF p_parent IS NOT NULL THEN
                SELECT * INTO p FROM m4.chung_tu_run WHERE id = p_parent;
                IF NOT FOUND OR p.dot_id <> p_dot OR p.trang_thai IN ('PENDING','RUNNING') THEN
                    RAISE EXCEPTION 'M4_CHUNG_TU_CHA_SAI: Chạy lại phải dùng đúng đợt của lần chạy đã kết thúc' {_LOI};
                END IF;
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id = d.du_an_id;
            INSERT INTO m4.chung_tu_run (phap_nhan_id, du_an_id, hop_dong_id, dot_id, revision, basis, basis_sha256, engine, engine_sha256, hanh_dong, yeu_cau,
                                         yeu_cau_sha256, khoa, quyen, trang_thai, parent_run_id, tao_boi, tao_boi_id)
                VALUES (pn, d.du_an_id, d.hop_dong_id, p_dot, p_revision, p_basis, p_basis_sha, p_engine, p_engine_sha, p_hanh, p_yc, p_yc_sha, p_khoa, q,
                        'RUNNING', p_parent, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (d.du_an_id, d.hop_dong_id, p_dot, p_hanh, ai, jsonb_build_object('run_id', moi, 'basis_sha256', p_basis_sha, 'quyen', q, 'revision', p_revision));
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', jsonb_build_object('run_id', moi, 'trang_thai', 'RUNNING', 'basis_sha256', p_basis_sha));
        END $$""",
    # công bố: quyền + phạm vi HIỆN HÀNH kiểm lại; so TOÀN basis token (máy chủ chụp lại ngay trong giao dịch); đổi → STALE; FINAL + biên nhận cùng giao dịch
    """CREATE OR REPLACE FUNCTION m4.chung_tu_cong_bo(p_run uuid, p_kq jsonb, p_kq_sha text, p_coverage jsonb, p_trang_thai text, p_basis_hien_tai text,
                                                      p_artifacts jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; tt text; a jsonb;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.chung_tu_run WHERE id = p_run FOR UPDATE;
            IF NOT FOUND OR r.tao_boi_id <> aid THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_KHONG_THAY: không thấy lần chạy của phiên này' {_LOI};
            END IF;
            PERFORM m4.chung_tu_kiem(r.dot_id);
            IF r.trang_thai NOT IN ('PENDING','RUNNING') THEN
                cu := m4._bn_tra(aid, r.khoa, r.hanh_dong, r.du_an_id, r.yeu_cau);
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', coalesce(cu, jsonb_build_object('run_id', r.id, 'trang_thai', r.trang_thai)));
            END IF;
            IF p_trang_thai NOT IN ('SUCCEEDED','PARTIAL','FAILED') THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: trạng thái công bố không hợp lệ' {_LOI};
            END IF;
            IF p_kq IS NULL OR jsonb_typeof(p_kq) <> 'object' OR p_kq_sha IS NULL OR p_kq_sha !{_HEX} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: kết quả tính phải là object kèm SHA' {_LOI};
            END IF;
            tt := CASE WHEN p_trang_thai <> 'FAILED' AND p_basis_hien_tai IS DISTINCT FROM r.basis_sha256 THEN 'STALE' ELSE p_trang_thai END;
            INSERT INTO m4.chung_tu_result (run_id, du_an_id, ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256)
                VALUES (r.id, r.du_an_id, p_kq, p_kq_sha, coalesce(p_coverage, '{{}}'::jsonb), tt IN ('SUCCEEDED','PARTIAL'), p_basis_hien_tai);
            FOR a IN SELECT * FROM jsonb_array_elements(coalesce(p_artifacts, '[]'::jsonb)) LOOP
                INSERT INTO m4.chung_tu_artifact (run_id, du_an_id, loai, ten, raw_sha256, byte_length, object_key)
                    VALUES (r.id, r.du_an_id, a->>'loai', a->>'ten', a->>'raw_sha256', (a->>'byte_length')::bigint, 'm4-chung-tu/' || (a->>'raw_sha256'));
            END LOOP;
            UPDATE m4.chung_tu_run SET trang_thai = tt, xong_luc = now(),
                   ly_do = coalesce(p_ly_do, CASE WHEN tt = 'STALE' THEN 'Căn cứ (tệp/metadata/ghép tay/HĐ/BOQ/L2) đã đổi trong lúc tính — kết quả giữ làm bằng chứng, không gắn hiện hành' END)
                WHERE id = r.id;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'CHUNG_TU_CONG_BO', ai, jsonb_build_object('run_id', r.id, 'trang_thai', tt));
            kq := jsonb_build_object('run_id', r.id, 'trang_thai', tt, 'basis_sha256', r.basis_sha256, 'basis_cong_bo_sha256', p_basis_hien_tai,
                                     'ket_qua_sha256', p_kq_sha, 'cong_bo', tt IN ('SUCCEEDED','PARTIAL'), 'revision', r.revision);
            PERFORM m4._bn_ghi(aid, r.khoa, r.hanh_dong, r.du_an_id, r.yeu_cau, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);
        END $$""",
    # người chạy mất quyền trước khi công bố: giữ bằng chứng (kết quả không công bố + artifact), CANCELLED; không biên nhận/FINAL nghiệp vụ
    """CREATE OR REPLACE FUNCTION m4.chung_tu_huy(p_run uuid, p_ly_do text, p_kq jsonb, p_artifacts jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; a jsonb;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.chung_tu_run WHERE id = p_run FOR UPDATE;
            IF NOT FOUND OR r.tao_boi_id <> aid THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_KHONG_THAY: không thấy lần chạy của phiên này' {_LOI};
            END IF;
            IF r.trang_thai NOT IN ('PENDING','RUNNING') THEN
                RETURN;
            END IF;
            IF p_kq IS NOT NULL AND jsonb_typeof(p_kq) = 'object' THEN
                INSERT INTO m4.chung_tu_result (run_id, du_an_id, ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256)
                    VALUES (r.id, r.du_an_id, p_kq, encode(sha256(convert_to(p_kq::text, 'UTF8')), 'hex'), coalesce(p_kq->'coverage', '{{}}'::jsonb), false, NULL);
            END IF;
            FOR a IN SELECT * FROM jsonb_array_elements(coalesce(p_artifacts, '[]'::jsonb)) LOOP
                INSERT INTO m4.chung_tu_artifact (run_id, du_an_id, loai, ten, raw_sha256, byte_length, object_key)
                    VALUES (r.id, r.du_an_id, a->>'loai', a->>'ten', a->>'raw_sha256', (a->>'byte_length')::bigint, 'm4-chung-tu/' || (a->>'raw_sha256'));
            END LOOP;
            UPDATE m4.chung_tu_run SET trang_thai = 'CANCELLED', xong_luc = now(), ly_do = left(coalesce(p_ly_do, 'Hủy'), 2000) WHERE id = r.id;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'CHUNG_TU_HUY', ai, jsonb_build_object('run_id', r.id, 'ly_do', p_ly_do));
        END $$""",
    # sửa metadata (loại/số/ngày/bỏ-khôi phục) → revision MỚI của đợt (bản hiệu lực tích lũy + phần thay đổi); không sửa raw/kết quả trích/lần chạy cũ.
    # Khóa HĐ TRƯỚC khóa biên nhận (thứ tự M17/M19). Tệp phải gắn đúng đợt VÀ có trong basis của lần chạy được sửa.
    """CREATE OR REPLACE FUNCTION m4.chung_tu_ghi_revision(p_khoa text, p_yc jsonb, p_run uuid, p_revision integer, p_tai_lieu jsonb, p_ly_do text)
        RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; rv integer; cu_tl jsonb; moi_tl jsonb; e jsonb; t text; moi uuid;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.chung_tu_run WHERE id = p_run;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_KHONG_THAY: không thấy lần chạy' {_LOI};
            END IF;
            PERFORM m4.chung_tu_kiem(r.dot_id);
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.hop_dong_id FOR UPDATE;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || aid::text || ':' || p_khoa, 0));""" + _XUNG_DOT_GIU.format(hanh="'CHUNG_TU_SUA'") + f"""
            cu := m4._bn_tra(aid, p_khoa, 'CHUNG_TU_SUA', r.du_an_id, p_yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                RAISE EXCEPTION 'M4_THIEU_LY_DO: sửa metadata chứng từ cần lý do' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.chung_tu_revision x WHERE x.dot_id = r.dot_id;
            IF p_revision IS NULL OR rv <> p_revision THEN
                RAISE EXCEPTION 'M4_REVISION_CU: metadata chứng từ của đợt đã có revision mới (hiện tại %)', rv {_LOI};
            END IF;
            IF p_tai_lieu IS NULL OR jsonb_typeof(p_tai_lieu) <> 'array' OR jsonb_array_length(p_tai_lieu) NOT BETWEEN 1 AND 500 THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: danh sách sửa phải là mảng 1–500 mục' {_LOI};
            END IF;
            SELECT coalesce((SELECT x.tai_lieu FROM m4.chung_tu_revision x WHERE x.dot_id = r.dot_id AND x.revision = rv), '{{}}'::jsonb) INTO cu_tl;
            moi_tl := cu_tl;
            FOR e IN SELECT * FROM jsonb_array_elements(p_tai_lieu) LOOP
                IF jsonb_typeof(e) <> 'object' OR NOT (e ? 'tep_id')
                   OR EXISTS (SELECT 1 FROM jsonb_object_keys(e) k WHERE k NOT IN ('tep_id','loai','so','ngay','bo'))
                   OR (e ? 'loai' AND jsonb_typeof(e->'loai') <> 'null' AND (e->>'loai') NOT IN {_LOAI_SQL})
                   OR (e ? 'so' AND jsonb_typeof(e->'so') NOT IN ('null','string'))
                   OR (e ? 'so' AND length(coalesce(e->>'so', '')) > 100)
                   OR (e ? 'ngay' AND jsonb_typeof(e->'ngay') <> 'null' AND (e->>'ngay') !~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$')
                   OR (e ? 'bo' AND jsonb_typeof(e->'bo') NOT IN ('null','boolean')) THEN
                    RAISE EXCEPTION 'M4_THAM_SO_SAI: mục sửa chứng từ không hợp lệ' {_LOI};
                END IF;
                t := e->>'tep_id';
                IF NOT EXISTS (SELECT 1 FROM m4.dot_tep k WHERE k.dot_id = r.dot_id AND k.tep_id::text = t)
                   OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(coalesce(r.basis->'tai_lieu', '[]'::jsonb)) b WHERE b->>'tep_id' = t) THEN
                    RAISE EXCEPTION 'M4_CHUNG_TU_TEP_KHONG_THUOC: tệp không thuộc bộ chứng từ của đợt/lần chạy này' {_LOI};
                END IF;
                moi_tl := jsonb_set(moi_tl, ARRAY[t], coalesce(moi_tl->t, '{{}}'::jsonb) || (e - 'tep_id'), true);
            END LOOP;
            INSERT INTO m4.chung_tu_revision (phap_nhan_id, du_an_id, hop_dong_id, dot_id, revision, parent_revision, run_id, tai_lieu, thay_doi, ly_do,
                                              tao_boi, tao_boi_id)
                VALUES (r.phap_nhan_id, r.du_an_id, r.hop_dong_id, r.dot_id, rv + 1, rv, r.id, moi_tl, p_tai_lieu, p_ly_do, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'CHUNG_TU_SUA', ai, jsonb_build_object('revision_id', moi, 'revision', rv + 1, 'run_id', r.id));
            kq := jsonb_build_object('revision_id', moi, 'revision', rv + 1, 'dot_id', r.dot_id, 'so_muc', jsonb_array_length(p_tai_lieu),
                                     'ghi_chu', 'Revision metadata mới — bấm Chạy lại để đối chiếu; raw/kết quả cũ giữ nguyên');
            PERFORM m4._bn_ghi(aid, p_khoa, 'CHUNG_TU_SUA', r.du_an_id, p_yc, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);
        END $$""",
    # ghép tay dòng chứng từ → đúng MỘT dòng BOQ typed hiện hành cùng HĐ và hiệu lực tại ngày NT (cùng kiểm của m4.review_ghi_map); revision theo (đợt, row)
    """CREATE OR REPLACE FUNCTION m4.chung_tu_ghi_map(p_khoa text, p_yc jsonb, p_run uuid, p_row_id text, p_boq uuid, p_boq_dong integer, p_ma_hm text,
                                                      p_revision integer, p_ly_do text, p_tep uuid, p_locator jsonb, p_ten text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; b record; bd record; d record; pb record; t record; n integer; rv integer; mrev integer; moi uuid;
                pb_hl m4.phu_luc.ngay_hieu_luc%TYPE; pb_ky m4.phu_luc.ngay_ky%TYPE; pb_so m4.phu_luc.so_pl%TYPE;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.chung_tu_run WHERE id = p_run;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_KHONG_THAY: không thấy lần chạy' {_LOI};
            END IF;
            PERFORM m4.chung_tu_kiem(r.dot_id);
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.hop_dong_id FOR UPDATE;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || aid::text || ':' || p_khoa, 0));""" + _XUNG_DOT_GIU.format(hanh="'CHUNG_TU_GHEP'") + f"""
            cu := m4._bn_tra(aid, p_khoa, 'CHUNG_TU_GHEP', r.du_an_id, p_yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                RAISE EXCEPTION 'M4_THIEU_LY_DO: ghép tay cần lý do' {_LOI};
            END IF;
            IF p_row_id IS NULL OR p_row_id !{_HEX} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: mã dòng chứng từ không hợp lệ' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.chung_tu_revision x WHERE x.dot_id = r.dot_id;
            IF p_revision IS NULL OR rv <> p_revision THEN
                RAISE EXCEPTION 'M4_REVISION_CU: metadata chứng từ của đợt đã có revision mới (hiện tại %)', rv {_LOI};
            END IF;
            IF NOT EXISTS (SELECT 1 FROM m4.chung_tu_result x, jsonb_array_elements(coalesce(x.ket_qua->'tai_lieu', '[]'::jsonb)) dd,
                                         jsonb_array_elements(coalesce(dd->'dong', '[]'::jsonb)) l
                           WHERE x.run_id = r.id AND dd->>'tep_id' = p_tep::text AND l->>'row_id' = p_row_id) THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_DONG_KHONG_CO: lần chạy không có dòng chứng từ với mã này' {_LOI};
            END IF;
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM m4.dot_tep k WHERE k.dot_id = r.dot_id AND k.tep_id = p_tep) THEN
                RAISE EXCEPTION 'M4_CHUNG_TU_TEP_KHONG_THUOC: tệp không thuộc bộ chứng từ của đợt' {_LOI};
            END IF;
            SELECT * INTO b FROM m4.boq WHERE id = p_boq AND hop_dong_id = r.hop_dong_id AND trang_thai = 'DA_MAP'
                AND lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = r.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM m4.boq.phu_luc_id);
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_REVIEW_BOQ_KHONG_HIEN_HANH: BOQ đích không phải bản hiện hành hợp lệ của đúng hợp đồng' {_LOI};
            END IF;
            SELECT count(*) INTO n FROM m4.boq_dong WHERE boq_id = p_boq AND ma_hm = p_ma_hm;
            IF n <> 1 THEN
                RAISE EXCEPTION 'M4_REVIEW_DICH_MO_HO: mã hạng mục đích không tồn tại hoặc không duy nhất trong BOQ (% dòng)', n {_LOI};
            END IF;
            SELECT * INTO bd FROM m4.boq_dong WHERE boq_id = p_boq AND ma_hm = p_ma_hm;
            IF p_boq_dong IS NULL OR bd.dong <> p_boq_dong THEN
                RAISE EXCEPTION 'M4_REVIEW_DICH_KHONG_HIEU_LUC: dòng BOQ đích khác dòng nguồn đang hiệu lực' {_LOI};
            END IF;
            SELECT * INTO d FROM m4.dot WHERE id = r.dot_id;
            IF d.ngay_nghiem_thu IS NULL THEN
                RAISE EXCEPTION 'M4_REVIEW_DICH_KHONG_HIEU_LUC: đợt chưa có ngày nghiệm thu — không xác định được BOQ hiệu lực' {_LOI};
            END IF;
            IF b.phu_luc_id IS NOT NULL THEN
                SELECT * INTO pb FROM m4.phu_luc WHERE id = b.phu_luc_id AND hop_dong_id = r.hop_dong_id;
                IF NOT FOUND OR pb.trang_thai <> 'DA_KY' OR pb.ngay_hieu_luc > d.ngay_nghiem_thu THEN
                    RAISE EXCEPTION 'M4_REVIEW_DICH_KHONG_HIEU_LUC: phụ lục của BOQ đích chưa ký/chưa hiệu lực tại ngày NT/đã hủy' {_LOI};
                END IF;
                pb_hl := pb.ngay_hieu_luc; pb_ky := pb.ngay_ky; pb_so := pb.so_pl;
            END IF;
            IF EXISTS (SELECT 1 FROM m4.boq z JOIN m4.phu_luc p ON p.id = z.phu_luc_id JOIN m4.boq_dong zd ON zd.boq_id = z.id
                       WHERE z.hop_dong_id = r.hop_dong_id AND z.trang_thai = 'DA_MAP' AND z.id <> p_boq
                         AND z.lan = (SELECT max(y.lan) FROM m4.boq y WHERE y.hop_dong_id = z.hop_dong_id AND y.phu_luc_id = z.phu_luc_id)
                         AND p.trang_thai = 'DA_KY' AND p.ngay_hieu_luc <= d.ngay_nghiem_thu AND zd.ma_hm = p_ma_hm AND zd.thao_tac IN ('THEM','THAY')
                         AND (b.phu_luc_id IS NULL OR (p.ngay_hieu_luc, p.ngay_ky, p.so_pl) > (pb_hl, pb_ky, pb_so))) THEN
                RAISE EXCEPTION 'M4_REVIEW_DICH_KHONG_HIEU_LUC: mã % đã được phụ lục hiệu lực khác thêm/thay — đích không còn hiệu lực', p_ma_hm {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) + 1 INTO mrev FROM m4.chung_tu_manual_map x WHERE x.dot_id = r.dot_id AND x.row_id = p_row_id;
            INSERT INTO m4.chung_tu_manual_map (phap_nhan_id, du_an_id, hop_dong_id, dot_id, row_id, revision, boq_id, boq_dong, ma_hm, run_id, tep_id,
                                                raw_sha256, locator, ten_dong, revision_chung_tu, ly_do, tao_boi, tao_boi_id)
                VALUES (r.phap_nhan_id, r.du_an_id, r.hop_dong_id, r.dot_id, p_row_id, mrev, p_boq, bd.dong, p_ma_hm, r.id, p_tep, t.raw_sha256,
                        coalesce(p_locator, '{{}}'::jsonb), left(p_ten, 500), rv, p_ly_do, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'CHUNG_TU_GHEP', ai,
                        jsonb_build_object('map_id', moi, 'row_id', p_row_id, 'ma_hm', p_ma_hm, 'revision', mrev, 'run_id', r.id));
            kq := jsonb_build_object('map_id', moi, 'revision', mrev, 'row_id', p_row_id, 'ma_hm', p_ma_hm, 'boq_id', p_boq, 'boq_dong', bd.dong,
                                     'pham_vi', 'Áp dụng cho dòng cùng mã (cùng raw + vị trí) ở các lần chạy sau của CÙNG đợt; không áp đợt/HĐ khác');
            PERFORM m4._bn_ghi(aid, p_khoa, 'CHUNG_TU_GHEP', r.du_an_id, p_yc, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);
        END $$""",
    # --- quyền thực thi + RLS đọc (không role/quyền nghiệp vụ mới; GRANT SELECT kỹ thuật cho app_web hiện hữu, luôn qua RLS)
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_LENH) + " FROM PUBLIC",
    "REVOKE ALL ON " + ", ".join(f"m4.{t}" for t in BANG) + " FROM PUBLIC",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON m4.chung_tu_run, m4.chung_tu_result, m4.chung_tu_artifact, m4.chung_tu_revision, m4.chung_tu_manual_map TO app_web;
            CREATE POLICY chung_tu_run_web ON m4.chung_tu_run FOR SELECT TO app_web USING (m4.chung_tu_doc_duoc(id));
            CREATE POLICY chung_tu_result_web ON m4.chung_tu_result FOR SELECT TO app_web USING (m4.chung_tu_doc_duoc(run_id));
            CREATE POLICY chung_tu_artifact_web ON m4.chung_tu_artifact FOR SELECT TO app_web USING (m4.chung_tu_doc_duoc(run_id));
            CREATE POLICY chung_tu_revision_web ON m4.chung_tu_revision FOR SELECT TO app_web USING (m4.chung_tu_doc_dot(dot_id));
            CREATE POLICY chung_tu_manual_map_web ON m4.chung_tu_manual_map FOR SELECT TO app_web USING (m4.chung_tu_doc_dot(dot_id));
        END IF;
    END $$""",
)
