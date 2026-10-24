"""M4-02A — M19 (append sau actual 1–18): bản ghi Review L1/L2 hữu hạn. CHỈ hằng SQL (không import ha_tang; pg_migrations.py import và append registry).

- m4.review_run: một lần chạy (PN/dự án/HĐ/đợt, tệp + raw SHA, mode L1|L1_L2, ô đích, basis JSON + SHA chụp từ PG, engine, yêu cầu gốc + khóa,
  quyền dùng SOAN|REVIEW, trạng thái PENDING/RUNNING/SUCCEEDED/PARTIAL/FAILED/STALE/CANCELLED, run cha khi Chạy lại). Định danh bất biến; chỉ một
  lần chuyển từ RUNNING sang trạng thái cuối.
- m4.review_result / m4.review_artifact / m4.review_manual_map: chỉ ghi thêm (owner admission, trigger m4.chi_ghi_them của M17).
- Quyền: SOAN đúng dự án (tệp hồ sơ đợt .xlsx của dự án; nếu có đợt thì tệp phải gắn đúng đợt) HOẶC REVIEW đúng dự án CHỈ trên tệp của đúng đợt đã NỘP.
  Không cấp SOAN cho reviewer, không mở vai/module mới, không owner-only theo người tạo khi đọc.
- Biên nhận: dùng lại m4.bien_nhan + m4._bn_tra/_bn_ghi (cùng ngữ nghĩa actor+khóa), nhưng TRA qua m4.review_tra kiểm quyền Review hiện hành + phạm vi
  đợt/tệp chính xác TRƯỚC (không dùng m4.tra_bien_nhan vốn đòi SOAN). FINAL chốt trong giao dịch công bố.
- FIX02 F4: m4.review_giu_khoa giữ chỗ (actor, khóa) của lệnh Review chạy/chạy lại, ghi + COMMIT trong giao dịch READ COMMITTED ngắn dưới khóa
  giao dịch biên nhận M17 TRƯỚC snapshot RR; trigger biên nhận chặn hành động/body khác dùng khóa đã giữ chỗ (cả khi commit sau snapshot RR).
- Không có bảng duyệt/AP/Request; không đụng định nghĩa/checksum 1–18.
"""

from __future__ import annotations

_LOI = "USING ERRCODE = 'P0001'"
_HEX = "~ '^[0-9a-f]{64}$'"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TRANG_THAI_RUN = ("PENDING", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "STALE", "CANCELLED")
LOAI_ARTIFACT = ("BASIS", "INPUT", "RESULT", "REPORT_L1", "REPORT_L2", "REPORT_L1_NGUON", "REPORT_L2_NGUON", "LOG")
HANH_DONG = ("REVIEW_CHAY", "REVIEW_CHAY_LAI", "REVIEW_GHEP")
_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.review_run'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường tin cậy của máy chủ ghi lần chạy/kết quả Review' """ + _LOI + """;
            END IF;"""
_KB = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); cu jsonb; kq jsonb;"
_TT_SQL = "(" + ",".join(f"'{t}'" for t in TRANG_THAI_RUN) + ")"
_ART_SQL = "(" + ",".join(f"'{t}'" for t in LOAI_ARTIFACT) + ")"
_HD_SQL = "(" + ",".join(f"'{t}'" for t in HANH_DONG) + ")"

HAM_LENH = ("m4.review_tra(text, text, uuid, uuid, uuid, jsonb)",
            "m4.review_giu(text, text, uuid, uuid, uuid, jsonb)",
            "m4.review_tao_run(text, text, jsonb, text, uuid, uuid, uuid, uuid, text, text, text, jsonb, text, text, text, uuid)",
            "m4.review_cong_bo(uuid, jsonb, text, jsonb, text, text, jsonb, text)",
            "m4.review_huy(uuid, text, jsonb, jsonb)",
            "m4.review_ghi_map(text, jsonb, uuid, text, uuid, integer, text, text, integer, text, text)",
            "m4.review_kiem(uuid, uuid, uuid)")
HAM_DOC = ("m4.review_quyen(uuid, uuid, uuid)", "m4.review_doc_duoc(uuid)")

M0019_M4_REVIEW = (
    "SET LOCAL check_function_bodies = off",
    f"""CREATE TABLE m4.review_run (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid,
        dot_id uuid REFERENCES m4.dot(id),
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        che_do text NOT NULL CHECK (che_do IN ('L1','L1_L2')),
        o_dich text CHECK (o_dich IS NULL OR length(o_dich) BETWEEN 3 AND 150),
        basis jsonb NOT NULL CHECK (jsonb_typeof(basis) = 'object'),
        basis_sha256 text NOT NULL CHECK (basis_sha256 {_HEX}),
        engine text NOT NULL CHECK (length(engine) BETWEEN 1 AND 300),
        engine_sha256 text NOT NULL CHECK (engine_sha256 {_HEX}),
        hanh_dong text NOT NULL CHECK (hanh_dong IN ('REVIEW_CHAY','REVIEW_CHAY_LAI')),
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        yeu_cau_sha256 text NOT NULL CHECK (yeu_cau_sha256 {_HEX}),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        quyen text NOT NULL CHECK (quyen IN ('SOAN','REVIEW')),
        trang_thai text NOT NULL DEFAULT 'RUNNING' CHECK (trang_thai IN {_TT_SQL}),
        parent_run_id uuid REFERENCES m4.review_run(id),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) <= 2000),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        xong_luc timestamptz,
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (tep_id, du_an_id, raw_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        CHECK (che_do = 'L1' OR (hop_dong_id IS NOT NULL AND dot_id IS NOT NULL)),
        CHECK (dot_id IS NULL OR hop_dong_id IS NOT NULL),
        CHECK ((trang_thai IN ('PENDING','RUNNING')) = (xong_luc IS NULL)),
        UNIQUE (tao_boi_id, khoa),
        UNIQUE (id, du_an_id))""",
    # định danh bất biến; chỉ chủ bảng; không xóa; chỉ MỘT lần từ PENDING/RUNNING sang trạng thái cuối
    """CREATE OR REPLACE FUNCTION m4.review_run_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: lần chạy Review chỉ ghi qua hàm định nghĩa trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không xóa lần chạy Review (giữ lịch sử/bằng chứng)' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai NOT IN ('PENDING','RUNNING') OR NEW.xong_luc IS NOT NULL THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: lần chạy mới phải ở PENDING/RUNNING' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.trang_thai NOT IN ('PENDING','RUNNING') THEN
                RAISE EXCEPTION 'M4_REVIEW_DA_CHOT: lần chạy đã ở trạng thái cuối %', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.du_an_id, NEW.hop_dong_id, NEW.dot_id, NEW.tep_id, NEW.raw_sha256, NEW.che_do, NEW.o_dich, NEW.basis,
                   NEW.basis_sha256, NEW.engine, NEW.engine_sha256, NEW.hanh_dong, NEW.yeu_cau, NEW.yeu_cau_sha256, NEW.khoa, NEW.quyen, NEW.parent_run_id,
                   NEW.tao_boi, NEW.tao_boi_id, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.du_an_id, OLD.hop_dong_id, OLD.dot_id, OLD.tep_id, OLD.raw_sha256, OLD.che_do, OLD.o_dich,
                   OLD.basis, OLD.basis_sha256, OLD.engine, OLD.engine_sha256, OLD.hanh_dong, OLD.yeu_cau, OLD.yeu_cau_sha256, OLD.khoa, OLD.quyen,
                   OLD.parent_run_id, OLD.tao_boi, OLD.tao_boi_id, OLD.tao_luc) THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không sửa định danh/căn cứ của lần chạy Review' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER review_run_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.review_run FOR EACH ROW EXECUTE FUNCTION m4.review_run_kiem()",
    f"""CREATE TABLE m4.review_result (
        run_id uuid PRIMARY KEY,
        du_an_id uuid NOT NULL,
        ket_qua jsonb NOT NULL CHECK (jsonb_typeof(ket_qua) = 'object'),
        ket_qua_sha256 text NOT NULL CHECK (ket_qua_sha256 {_HEX}),
        coverage jsonb NOT NULL CHECK (jsonb_typeof(coverage) = 'object'),
        cong_bo boolean NOT NULL,
        basis_cong_bo_sha256 text CHECK (basis_cong_bo_sha256 IS NULL OR basis_cong_bo_sha256 {_HEX}),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.review_run (id, du_an_id))""",
    f"""CREATE TABLE m4.review_artifact (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN {_ART_SQL}),
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 200 AND strpos(ten, '/') = 0 AND strpos(ten, chr(92)) = 0 AND ten !~ '[[:cntrl:]]'),
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        object_key text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'm4-review/' || raw_sha256),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.review_run (id, du_an_id),
        UNIQUE (run_id, loai))""",
    f"""CREATE TABLE m4.review_manual_map (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        khoa_hstt text NOT NULL CHECK (length(khoa_hstt) BETWEEN 1 AND 1000),
        revision integer NOT NULL CHECK (revision >= 1),
        boq_id uuid NOT NULL,
        boq_dong integer NOT NULL,
        ma_hm text NOT NULL CHECK (length(ma_hm) BETWEEN 1 AND 500),
        run_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        sheet text CHECK (sheet IS NULL OR length(sheet) <= 100),
        dong_hs integer,
        ten_hs text CHECK (ten_hs IS NULL OR length(ten_hs) <= 500),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) BETWEEN 1 AND 1000),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (boq_id, boq_dong) REFERENCES m4.boq_dong (boq_id, dong),
        FOREIGN KEY (run_id, du_an_id) REFERENCES m4.review_run (id, du_an_id),
        UNIQUE (hop_dong_id, khoa_hstt, revision))""",
    # FIX02 F4: giữ chỗ (actor, khóa) của lệnh Review — ghi trong giao dịch READ COMMITTED NGẮN, dưới khóa giao dịch biên nhận M17, và COMMIT
    # TRƯỚC khi mở snapshot REPEATABLE READ. Từ đó mọi biên nhận M17/Review cùng actor+khóa khác hành động/body bị trigger chặn (thấy hàng đã commit
    # dù đối phương mở snapshot sau), và Review thấy biên nhận M17 đã commit trước khi giữ chỗ. Chỉ ghi thêm; không giữ khóa biên nhận qua CPU.
    f"""CREATE TABLE m4.review_giu_khoa (
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        hanh_dong text NOT NULL CHECK (hanh_dong IN {_HD_SQL}),
        du_an_id uuid NOT NULL,
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (nguoi_dung_id, khoa))""",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in ("review_result", "review_artifact", "review_manual_map", "review_giu_khoa")),
    # --- quyền Review của phiên (không raise): SOAN đúng dự án hoặc REVIEW trên đúng tệp của đúng đợt đã nộp
    f"""CREATE OR REPLACE FUNCTION m4.review_quyen(p_du_an uuid, p_dot uuid, p_tep uuid) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE t record; d record;
        BEGIN
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            IF NOT FOUND OR t.du_an_id IS DISTINCT FROM p_du_an OR t.vai_tro_tai_lieu <> 'HO_SO_DOT' OR t.media_type <> '{_XLSX}' THEN
                RETURN NULL;
            END IF;
            IF p_dot IS NOT NULL THEN
                SELECT * INTO d FROM m4.dot WHERE id = p_dot;
                IF NOT FOUND OR d.du_an_id IS DISTINCT FROM p_du_an
                   OR NOT EXISTS (SELECT 1 FROM m4.dot_tep k WHERE k.dot_id = p_dot AND k.tep_id = p_tep) THEN
                    RETURN NULL;
                END IF;
            END IF;
            IF master.m4_duoc(p_du_an, 'SOAN') THEN
                RETURN 'SOAN';
            END IF;
            IF master.m4_duoc(p_du_an, 'REVIEW') AND p_dot IS NOT NULL AND d.trang_thai = 'DA_NOP' THEN
                RETURN 'REVIEW';
            END IF;
            RETURN NULL;
        END $$""",
    # có raise với mã chính xác — dùng trong mọi lệnh TRƯỚC tra biên nhận/đọc raw
    """CREATE OR REPLACE FUNCTION m4.review_kiem(p_du_an uuid, p_dot uuid, p_tep uuid) RETURNS text
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE q text;
        BEGIN
            q := m4.review_quyen(p_du_an, p_dot, p_tep);
            IF q IS NOT NULL THEN
                RETURN q;
            END IF;
            IF NOT (master.m4_duoc(p_du_an, 'SOAN') OR master.m4_duoc(p_du_an, 'REVIEW')) THEN
                RAISE EXCEPTION 'M4_KHONG_CO_QUYEN_DU_AN: cần quyền soạn hoặc review hiện hành đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            RAISE EXCEPTION 'M4_REVIEW_PHAM_VI: tệp/đợt ngoài phạm vi Review (tệp hồ sơ đợt .xlsx của dự án, gắn đúng đợt; người review chỉ chạy trên đợt đã nộp)'
                USING ERRCODE = 'P0001';
        END $$""",
    # đọc lần chạy: XEM dự án, hoặc REVIEW khi lần chạy gắn đúng tệp của đúng đợt đã nộp
    """CREATE OR REPLACE FUNCTION m4.review_doc_duoc(p_run uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.review_run r WHERE r.id = p_run AND (master.m4_duoc(r.du_an_id, 'XEM')
                       OR (master.m4_duoc(r.du_an_id, 'REVIEW') AND r.dot_id IS NOT NULL
                           AND EXISTS (SELECT 1 FROM m4.dot d WHERE d.id = r.dot_id AND d.trang_thai = 'DA_NOP')
                           AND EXISTS (SELECT 1 FROM m4.dot_tep k WHERE k.dot_id = r.dot_id AND k.tep_id = r.tep_id))))
        $$""",
    # tra biên nhận Review: quyền + phạm vi hiện hành TRƯỚC, rồi m4._bn_tra (cùng actor+khóa; khác yêu cầu → M4_IDEMPOTENCY_KHAC)
    """CREATE OR REPLACE FUNCTION m4.review_tra(p_khoa text, p_hanh text, p_du_an uuid, p_dot uuid, p_tep uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN""" + _TIN_CAY + f"""
            IF p_hanh NOT IN {_HD_SQL} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động Review không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.review_kiem(p_du_an, p_dot, p_tep);
            -- FIX01 R5/FIX02 F4: khóa đã được giữ chỗ cho lệnh Review (cùng actor) với hành động/body khác → xung đột chính xác TRƯỚC mọi hiệu lực
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || m4.ai_id()::text || ':' || p_khoa, 0));
            IF EXISTS (SELECT 1 FROM m4.review_giu_khoa g WHERE g.nguoi_dung_id = m4.ai_id() AND g.khoa = p_khoa
                       AND (g.hanh_dong <> p_hanh OR g.yeu_cau <> p_yc)) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu Review khác' {_LOI};
            END IF;
            RETURN m4._bn_tra(m4.ai_id(), p_khoa, p_hanh, p_du_an, p_yc);
        END $$""",
    # FIX02 F4: bước 1 của lệnh Review CHẠY/CHẠY LẠI — giao dịch READ COMMITTED ngắn: quyền + phạm vi hiện hành → khóa giao dịch biên nhận (cùng
    # namespace M17) → biên nhận cũ (đúng body → FINAL; khác → xung đột) → giữ chỗ (actor, khóa). Người gọi COMMIT trước khi mở snapshot RR.
    """CREATE OR REPLACE FUNCTION m4.review_giu(p_khoa text, p_hanh text, p_du_an uuid, p_dot uuid, p_tep uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE aid uuid; g record; cu jsonb;
        BEGIN""" + _TIN_CAY + f"""
            IF p_hanh NOT IN ('REVIEW_CHAY','REVIEW_CHAY_LAI') THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động giữ chỗ Review không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.review_kiem(p_du_an, p_dot, p_tep);
            aid := m4.ai_id();
            cu := m4._bn_tra(aid, p_khoa, p_hanh, p_du_an, p_yc);  -- khóa giao dịch m4:bien_nhan:(actor,khóa) giữ tới COMMIT của bước này
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            SELECT * INTO g FROM m4.review_giu_khoa WHERE nguoi_dung_id = aid AND khoa = p_khoa;
            IF FOUND THEN
                IF g.hanh_dong <> p_hanh OR g.yeu_cau <> p_yc OR g.du_an_id <> p_du_an THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' {_LOI};
                END IF;
            ELSE
                INSERT INTO m4.review_giu_khoa (nguoi_dung_id, khoa, hanh_dong, du_an_id, yeu_cau) VALUES (aid, p_khoa, p_hanh, p_du_an, p_yc);
            END IF;
            RETURN jsonb_build_object('lap_lai', false);
        END $$""",
    # FIX01 R5/FIX02 F4: mọi biên nhận (lệnh M17 thường hay ghép tay) cùng actor+khóa đã được giữ chỗ cho lệnh Review khác hành động/body → chặn
    # chính xác trong CÙNG giao dịch hiệu lực (rollback hiệu lực). Kiểm hàng giữ chỗ ĐÃ COMMIT (READ COMMITTED của lệnh M17). Không sửa M17.
    """CREATE OR REPLACE FUNCTION m4.review_bn_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM m4.review_giu_khoa g WHERE g.nguoi_dung_id = NEW.nguoi_dung_id AND g.khoa = NEW.khoa
                       AND (g.hanh_dong <> NEW.hanh_dong OR g.yeu_cau <> NEW.yeu_cau)) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho lệnh Review khác' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_review_khoa BEFORE INSERT ON m4.bien_nhan FOR EACH ROW EXECUTE FUNCTION m4.review_bn_khoa()",
    # tạo lần chạy RUNNING sau khi máy chủ chụp basis trong một snapshot REPEATABLE READ (cùng giao dịch với lệnh này)
    """CREATE OR REPLACE FUNCTION m4.review_tao_run(p_khoa text, p_hanh text, p_yc jsonb, p_yc_sha text, p_du_an uuid, p_hd uuid, p_dot uuid, p_tep uuid,
                                                    p_raw text, p_che_do text, p_o_dich text, p_basis jsonb, p_basis_sha text, p_engine text,
                                                    p_engine_sha text, p_parent uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ q text; r record; d record; p record; t record; moi uuid; pn uuid;
        BEGIN""" + _TIN_CAY + f"""
            q := m4.review_kiem(p_du_an, p_dot, p_tep);
            cu := m4._bn_tra(aid, p_khoa, p_hanh, p_du_an, p_yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            SELECT * INTO r FROM m4.review_run WHERE tao_boi_id = aid AND khoa = p_khoa;
            IF FOUND THEN
                IF r.hanh_dong <> p_hanh OR r.yeu_cau <> p_yc THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' {_LOI};
                END IF;
                RETURN jsonb_build_object('lap_lai', true, 'dang_chay', r.trang_thai IN ('PENDING','RUNNING'),
                                          'ket_qua', jsonb_build_object('run_id', r.id, 'trang_thai', r.trang_thai, 'basis_sha256', r.basis_sha256));
            END IF;
            IF p_che_do NOT IN ('L1','L1_L2') OR (p_che_do = 'L1_L2' AND p_dot IS NULL) THEN
                RAISE EXCEPTION 'M4_REVIEW_CAN_DOT: L1+L2 cần đợt (ngày nghiệm thu) của hợp đồng' {_LOI};
            END IF;
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            IF t.raw_sha256 <> p_raw THEN
                RAISE EXCEPTION 'M4_REVIEW_TEP_DOI: bytes tệp khác bản đã chụp' {_LOI};
            END IF;
            IF p_dot IS NOT NULL THEN
                SELECT * INTO d FROM m4.dot WHERE id = p_dot;
                IF d.hop_dong_id IS DISTINCT FROM p_hd THEN
                    RAISE EXCEPTION 'M4_REVIEW_PHAM_VI: đợt không thuộc hợp đồng đã chọn' {_LOI};
                END IF;
            ELSIF p_hd IS NOT NULL THEN
                RAISE EXCEPTION 'M4_REVIEW_PHAM_VI: chỉ gắn hợp đồng qua đợt của hợp đồng' {_LOI};
            END IF;
            IF p_parent IS NOT NULL THEN
                SELECT * INTO p FROM m4.review_run WHERE id = p_parent;
                IF NOT FOUND OR (p.du_an_id, p.tep_id, p.raw_sha256, p.che_do, p.dot_id, p.o_dich) IS DISTINCT FROM (p_du_an, p_tep, p_raw, p_che_do, p_dot, p_o_dich)
                   OR p.trang_thai IN ('PENDING','RUNNING') THEN
                    RAISE EXCEPTION 'M4_REVIEW_CHA_SAI: Chạy lại phải dùng đúng tệp/đợt/chế độ của lần chạy đã kết thúc' {_LOI};
                END IF;
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id = p_du_an;
            INSERT INTO m4.review_run (phap_nhan_id, du_an_id, hop_dong_id, dot_id, tep_id, raw_sha256, che_do, o_dich, basis, basis_sha256, engine,
                                       engine_sha256, hanh_dong, yeu_cau, yeu_cau_sha256, khoa, quyen, trang_thai, parent_run_id, tao_boi, tao_boi_id)
                VALUES (pn, p_du_an, p_hd, p_dot, p_tep, p_raw, p_che_do, p_o_dich, p_basis, p_basis_sha, p_engine, p_engine_sha, p_hanh, p_yc, p_yc_sha,
                        p_khoa, q, 'RUNNING', p_parent, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (p_du_an, p_hd, p_dot, p_hanh, ai, jsonb_build_object('run_id', moi, 'basis_sha256', p_basis_sha, 'quyen', q));
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', jsonb_build_object('run_id', moi, 'trang_thai', 'RUNNING', 'basis_sha256', p_basis_sha));
        END $$""",
    # công bố: quyền + phạm vi HIỆN HÀNH kiểm lại; so TOÀN basis token (máy chủ chụp lại ngay trong giao dịch này); đổi → STALE (giữ bằng chứng,
    # không gắn hiện hành); FINAL + biên nhận chốt cùng giao dịch
    """CREATE OR REPLACE FUNCTION m4.review_cong_bo(p_run uuid, p_kq jsonb, p_kq_sha text, p_coverage jsonb, p_trang_thai text, p_basis_hien_tai text,
                                                    p_artifacts jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; tt text; a jsonb;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.review_run WHERE id = p_run FOR UPDATE;
            IF NOT FOUND OR r.tao_boi_id <> aid THEN
                RAISE EXCEPTION 'M4_REVIEW_KHONG_THAY: không thấy lần chạy của phiên này' {_LOI};
            END IF;
            PERFORM m4.review_kiem(r.du_an_id, r.dot_id, r.tep_id);
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
            INSERT INTO m4.review_result (run_id, du_an_id, ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256)
                VALUES (r.id, r.du_an_id, p_kq, p_kq_sha, coalesce(p_coverage, '{{}}'::jsonb), tt IN ('SUCCEEDED','PARTIAL'), p_basis_hien_tai);
            FOR a IN SELECT * FROM jsonb_array_elements(coalesce(p_artifacts, '[]'::jsonb)) LOOP
                INSERT INTO m4.review_artifact (run_id, du_an_id, loai, ten, raw_sha256, byte_length, object_key)
                    VALUES (r.id, r.du_an_id, a->>'loai', a->>'ten', a->>'raw_sha256', (a->>'byte_length')::bigint, 'm4-review/' || (a->>'raw_sha256'));
            END LOOP;
            UPDATE m4.review_run SET trang_thai = tt, xong_luc = now(),
                   ly_do = coalesce(p_ly_do, CASE WHEN tt = 'STALE' THEN 'Căn cứ (nguồn/ánh xạ/phụ lục/xác nhận/đợt) đã đổi trong lúc tính — kết quả giữ làm bằng chứng, không gắn hiện hành' END)
                WHERE id = r.id;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'REVIEW_CONG_BO', ai, jsonb_build_object('run_id', r.id, 'trang_thai', tt));
            kq := jsonb_build_object('run_id', r.id, 'trang_thai', tt, 'basis_sha256', r.basis_sha256, 'basis_cong_bo_sha256', p_basis_hien_tai,
                                     'ket_qua_sha256', p_kq_sha, 'cong_bo', tt IN ('SUCCEEDED','PARTIAL'));
            PERFORM m4._bn_ghi(aid, r.khoa, r.hanh_dong, r.du_an_id, r.yeu_cau, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);
        END $$""",
    # người chạy mất quyền trước khi công bố: giữ bằng chứng (kết quả không công bố + artifact), đóng lần chạy CANCELLED; không biên nhận/FINAL nghiệp vụ
    """CREATE OR REPLACE FUNCTION m4.review_huy(p_run uuid, p_ly_do text, p_kq jsonb, p_artifacts jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; a jsonb;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.review_run WHERE id = p_run FOR UPDATE;
            IF NOT FOUND OR r.tao_boi_id <> aid THEN
                RAISE EXCEPTION 'M4_REVIEW_KHONG_THAY: không thấy lần chạy của phiên này' {_LOI};
            END IF;
            IF r.trang_thai NOT IN ('PENDING','RUNNING') THEN
                RETURN;
            END IF;
            IF p_kq IS NOT NULL AND jsonb_typeof(p_kq) = 'object' THEN
                INSERT INTO m4.review_result (run_id, du_an_id, ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256)
                    VALUES (r.id, r.du_an_id, p_kq, encode(sha256(convert_to(p_kq::text, 'UTF8')), 'hex'), coalesce(p_kq->'coverage', '{{}}'::jsonb), false, NULL);
            END IF;
            FOR a IN SELECT * FROM jsonb_array_elements(coalesce(p_artifacts, '[]'::jsonb)) LOOP
                INSERT INTO m4.review_artifact (run_id, du_an_id, loai, ten, raw_sha256, byte_length, object_key)
                    VALUES (r.id, r.du_an_id, a->>'loai', a->>'ten', a->>'raw_sha256', (a->>'byte_length')::bigint, 'm4-review/' || (a->>'raw_sha256'));
            END LOOP;
            UPDATE m4.review_run SET trang_thai = 'CANCELLED', xong_luc = now(), ly_do = left(coalesce(p_ly_do, 'Hủy'), 2000) WHERE id = r.id;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'REVIEW_HUY', ai, jsonb_build_object('run_id', r.id, 'ly_do', p_ly_do));
        END $$""",
    # ghép tay: giữ khoa_hstt gốc; đích BOQ typed hiện hành cùng HĐ, tồn tại đúng MỘT dòng; revision theo (HĐ, khóa dòng); không sửa kết quả lần chạy cũ
    """CREATE OR REPLACE FUNCTION m4.review_ghi_map(p_khoa text, p_yc jsonb, p_run uuid, p_khoa_dong text, p_boq uuid, p_boq_dong integer, p_ma_hm text,
                                                    p_ly_do text, p_dong_hs integer, p_ten_hs text, p_sheet text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ r record; h record; b record; bd record; d record; pb record; n integer; rev integer; moi uuid;
                pb_hl m4.phu_luc.ngay_hieu_luc%TYPE; pb_ky m4.phu_luc.ngay_ky%TYPE; pb_so m4.phu_luc.so_pl%TYPE;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO r FROM m4.review_run WHERE id = p_run;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_REVIEW_KHONG_THAY: không thấy lần chạy' {_LOI};
            END IF;
            PERFORM m4.review_kiem(r.du_an_id, r.dot_id, r.tep_id);
            IF r.hop_dong_id IS NULL OR r.che_do <> 'L1_L2' THEN
                RAISE EXCEPTION 'M4_REVIEW_CAN_L2: ghép tay chỉ cho lần chạy L1+L2 của hợp đồng' {_LOI};
            END IF;
            -- FIX01 R5: khóa HĐ TRƯỚC khóa biên nhận (cùng thứ tự lệnh M17) — không vòng khóa HĐ↔biên nhận
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.hop_dong_id FOR UPDATE;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || aid::text || ':' || p_khoa, 0));
            IF EXISTS (SELECT 1 FROM m4.review_giu_khoa g WHERE g.nguoi_dung_id = aid AND g.khoa = p_khoa) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã được giữ chỗ cho lệnh Review chạy/chạy lại' {_LOI};
            END IF;
            cu := m4._bn_tra(aid, p_khoa, 'REVIEW_GHEP', r.du_an_id, p_yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                RAISE EXCEPTION 'M4_THIEU_LY_DO: ghép tay cần lý do' {_LOI};
            END IF;
            IF NOT EXISTS (SELECT 1 FROM m4.review_result x, jsonb_array_elements(coalesce(x.ket_qua->'lop2'->'doi_chieu_hm', '[]'::jsonb)) e
                           WHERE x.run_id = r.id AND e->>'khoa' = p_khoa_dong) THEN
                RAISE EXCEPTION 'M4_REVIEW_DONG_KHONG_CO: lần chạy không có dòng hồ sơ với khóa này' {_LOI};
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
            -- FIX01 R6: đúng DÒNG nguồn mà engine dùng (máy chủ phân giải bằng phu_luc_ap_dung/boq_hieu_luc của nguồn trên cùng snapshot) và đúng
            -- hiệu lực tại ngày NT của đợt: PL đích phải ĐÃ KÝ + hiệu lực ≤ ngày NT; không bị PL hiệu lực SAU (thứ tự nguồn: ngày hiệu lực, ngày ký,
            -- số PL) thêm/thay cùng mã; dòng gốc không bị PL hiệu lực nào thêm/thay. Sai → từ chối trước map/nhật ký/biên nhận.
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
                pb_hl := pb.ngay_hieu_luc; pb_ky := pb.ngay_ky; pb_so := pb.so_pl;  -- biến thường: không tham chiếu record chưa gán khi đích là BOQ gốc
            END IF;
            IF EXISTS (SELECT 1 FROM m4.boq z JOIN m4.phu_luc p ON p.id = z.phu_luc_id JOIN m4.boq_dong zd ON zd.boq_id = z.id
                       WHERE z.hop_dong_id = r.hop_dong_id AND z.trang_thai = 'DA_MAP' AND z.id <> p_boq
                         AND z.lan = (SELECT max(y.lan) FROM m4.boq y WHERE y.hop_dong_id = z.hop_dong_id AND y.phu_luc_id = z.phu_luc_id)
                         AND p.trang_thai = 'DA_KY' AND p.ngay_hieu_luc <= d.ngay_nghiem_thu AND zd.ma_hm = p_ma_hm AND zd.thao_tac IN ('THEM','THAY')
                         AND (b.phu_luc_id IS NULL OR (p.ngay_hieu_luc, p.ngay_ky, p.so_pl) > (pb_hl, pb_ky, pb_so))) THEN
                RAISE EXCEPTION 'M4_REVIEW_DICH_KHONG_HIEU_LUC: mã % đã được phụ lục hiệu lực khác thêm/thay — đích không còn hiệu lực', p_ma_hm {_LOI};
            END IF;
            SELECT coalesce(max(revision), 0) + 1 INTO rev FROM m4.review_manual_map WHERE hop_dong_id = r.hop_dong_id AND khoa_hstt = p_khoa_dong;
            INSERT INTO m4.review_manual_map (phap_nhan_id, du_an_id, hop_dong_id, khoa_hstt, revision, boq_id, boq_dong, ma_hm, run_id, raw_sha256, sheet,
                                              dong_hs, ten_hs, ly_do, tao_boi, tao_boi_id)
                VALUES (r.phap_nhan_id, r.du_an_id, r.hop_dong_id, p_khoa_dong, rev, p_boq, bd.dong, p_ma_hm, r.id, r.raw_sha256, p_sheet, p_dong_hs,
                        left(p_ten_hs, 500), p_ly_do, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (r.du_an_id, r.hop_dong_id, r.dot_id, 'REVIEW_GHEP', ai,
                        jsonb_build_object('map_id', moi, 'khoa_hstt', p_khoa_dong, 'ma_hm', p_ma_hm, 'revision', rev, 'run_id', r.id));
            kq := jsonb_build_object('map_id', moi, 'revision', rev, 'khoa_hstt', p_khoa_dong, 'ma_hm', p_ma_hm, 'boq_id', p_boq, 'boq_dong', bd.dong,
                                     'pham_vi', 'Áp dụng cho dòng có cùng khóa trên CÙNG hợp đồng ở các lần chạy sau; không áp dụng hợp đồng khác');
            PERFORM m4._bn_ghi(aid, p_khoa, 'REVIEW_GHEP', r.du_an_id, p_yc, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);
        END $$""",
    # --- quyền thực thi + RLS đọc
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_LENH) + " FROM PUBLIC",
    "REVOKE ALL ON m4.review_run, m4.review_result, m4.review_artifact, m4.review_manual_map, m4.review_giu_khoa FROM PUBLIC",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in ("review_run", "review_result", "review_artifact", "review_manual_map", "review_giu_khoa")),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON m4.review_run, m4.review_result, m4.review_artifact, m4.review_manual_map TO app_web;
            CREATE POLICY review_run_web ON m4.review_run FOR SELECT TO app_web USING (m4.review_doc_duoc(id));
            CREATE POLICY review_result_web ON m4.review_result FOR SELECT TO app_web USING (m4.review_doc_duoc(run_id));
            CREATE POLICY review_artifact_web ON m4.review_artifact FOR SELECT TO app_web USING (m4.review_doc_duoc(run_id));
            -- correction: map chỉ thấy khi lần chạy gốc (tệp/raw/đợt) đang thấy được theo quyền hiện hành — reviewer KHÔNG thấy map tạo từ
            -- đợt nháp/chưa nộp/tệp không liên quan; XEM/SOAN của dự án giữ nguyên (review_doc_duoc gồm XEM)
            CREATE POLICY review_manual_map_web ON m4.review_manual_map FOR SELECT TO app_web USING (m4.review_doc_duoc(run_id));
        END IF;
    END $$""",
)


# ================================================================================================== M20 (FIX04) — corrective, append SAU M19 đã áp dụng
# M19 `m4.review_quyen` khai `d record` và chỉ SELECT INTO d khi p_dot khác NULL, nhưng biểu thức REVIEW sau đó tham chiếu `d.trang_thai`:
# PL/pgSQL dựng tham số cho CẢ biểu thức (không dựa thứ tự AND) → SQLSTATE 55000 "record d is not assigned yet" trên kết nối mới khi không có đợt
# (actor ngoài dự án, reviewer không đợt) → review_kiem không trả được mã domain. M19 GIỮ NGUYÊN (đã áp dụng, checksum bất biến); M20 chỉ
# CREATE OR REPLACE đúng hàm này với kiểu xác định (`%ROWTYPE`/`%TYPE`) và nhánh không đợt không tham chiếu dữ liệu đợt.
# Giữ nguyên ngữ nghĩa: SOAN đúng dự án; REVIEW chỉ trên tệp gắn đúng đợt DA_NOP; tệp phải là HO_SO_DOT .xlsx của đúng dự án. Giữ chữ ký, STABLE,
# SECURITY DEFINER, search_path; CREATE OR REPLACE giữ chủ sở hữu/ACL hiện có — KHÔNG GRANT/REVOKE mới, không đổi bảng/schema/hàm khác.
M0020_M4_REVIEW_QUYEN = (
    f"""CREATE OR REPLACE FUNCTION m4.review_quyen(p_du_an uuid, p_dot uuid, p_tep uuid) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE t m4.tep%ROWTYPE; d_du_an m4.dot.du_an_id%TYPE; d_trang_thai m4.dot.trang_thai%TYPE;
        BEGIN
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            IF NOT FOUND OR t.du_an_id IS DISTINCT FROM p_du_an OR t.vai_tro_tai_lieu <> 'HO_SO_DOT' OR t.media_type <> '{_XLSX}' THEN
                RETURN NULL;
            END IF;
            IF p_dot IS NOT NULL THEN
                SELECT x.du_an_id, x.trang_thai INTO d_du_an, d_trang_thai FROM m4.dot x WHERE x.id = p_dot;
                IF NOT FOUND OR d_du_an IS DISTINCT FROM p_du_an
                   OR NOT EXISTS (SELECT 1 FROM m4.dot_tep k WHERE k.dot_id = p_dot AND k.tep_id = p_tep) THEN
                    RETURN NULL;
                END IF;
            END IF;
            IF master.m4_duoc(p_du_an, 'SOAN') THEN
                RETURN 'SOAN';
            END IF;
            IF p_dot IS NULL THEN
                RETURN NULL;  -- REVIEW chỉ trên đợt đã nộp: không đợt → không quyền Review (review_kiem trả mã domain)
            END IF;
            IF d_trang_thai = 'DA_NOP' AND master.m4_duoc(p_du_an, 'REVIEW') THEN
                RETURN 'REVIEW';
            END IF;
            RETURN NULL;
        END $$""",
)
