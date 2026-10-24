"""M4 — nhận hợp đồng master dùng chung, chọn đối tác và căn cứ master/mapping (docs/GIAO-CODE-M4-MASTER-REUSE-02.md).

CHỈ hằng SQL + danh sách ACL: module này không import hạ tầng, không tự đăng ký/áp dụng. Root cấp ordinal/registry riêng (không hardcode số
migration); thứ tự áp dụng: SAU M17 (m4 lõi) và M24 (m4.duyet_phien_ban), trên đúng kết nối chủ bảng m4/master.

- Chỉ THÊM: 2 bảng ghi-thêm (m4.master_can_cu, m4.master_can_cu_phien_ban), hàm, trigger quan sát và MỘT policy SELECT hẹp trên master.hop_dong.
  Không sửa/drop trigger/policy hiện hữu (hop_dong_kiem, hop_dong_m4_chi_chu, hop_dong_m4_rang_buoc, gk/crm_kiem, m4.chi_chu/chi_ghi_them...),
  không đổi discriminator module_chu/crm_giao_ket hay hàng CRM, không SET GUC, không mượn quyền SOAN/chủ bảng cho phiên người dùng.
- Căn cứ (canonical meta) = master ID/PN/dự án/loại/số/mã/trạng thái/crm_giao_ket/module_chu/đối tác/con trỏ phiên bản + các mapping
  doi_tac_ma_junsky đang mở (valid_to IS NULL) của đúng đối tác+PN; sha256 trên jsonb::text (jsonb tự chuẩn hóa thứ tự khóa), mốc thời gian UTC.
  Không phụ thuộc now() → hash chỉ đổi khi nguồn thật đổi.

Giao thức khóa (không có cặp khóa ngược master↔dossier, mapping không bao giờ bị khóa bởi M4):
- Lệnh nhận/gắn: master FOR UPDATE → hồ sơ FOR UPDATE → đọc MVCC mới (hàm VOLATILE, READ COMMITTED: mỗi câu lệnh một snapshot) master/mapping,
  kiểm CAS/trạng thái dưới khóa. Không khóa hàng mapping.
- Observer mapping (chạy trong chính giao dịch nguồn, đã giữ khóa hàng mapping): khóa FOR SHARE các master tiềm năng cùng PN (có hồ sơ M4 hoặc
  đúng đối tác cũ/mới) theo id tăng dần, mỗi master rồi đến hồ sơ của nó FOR UPDATE; sau khóa đọc lại master/mapping thật rồi mới quyết định.
- Observer master (AFTER UPDATE master.hop_dong, giao dịch nguồn đã giữ khóa hàng master): khóa hồ sơ → tính lại → ghi thêm nếu đổi.
- Thứ tự toàn cục: mapping → master(id↑) → hồ sơ. Lệnh M4 chỉ đi master → hồ sơ; nộp/duyệt chỉ giữ hồ sơ (→ đợt → phiên bản), đọc master/mapping
  không khóa. Hai thứ tự thắng attach↔đóng mapping:
    (1) attach thắng khóa master: đóng mapping chờ ở master; attach đọc mapping (chưa commit đóng) → gắn, commit; observer mapping lấy khóa,
        đọc lại thấy HĐ vừa gắn + mapping đã đóng (chính giao dịch nó) → ghi thêm căn cứ, tăng revision + rev_tham_so đúng 1 → nộp/duyệt cũ
        CAN_KIEM_LAI qua cổng revision hiện có.
    (2) đóng mapping thắng khóa master: attach chờ master tới khi nguồn commit; đọc mapping mới → sha mapping khác expected_mapping
        → M4_MAPPING_DA_DOI (expected_mapping đúng bản mới nhưng valid_to đã đặt → M4_MAPPING_KHONG_HIEN_HANH), 0 thay đổi.
"""

HAM_LENH = ("m4.nhan_master_hop_dong(text, uuid, uuid, text, text)",
            "m4.gan_doi_tac_hop_dong(text, uuid, uuid, uuid, integer, text, text, text)")
HAM_DOC = ("m4.master_hop_dong_ds(uuid, text, integer)", "m4.master_doi_tac_ds(uuid, text, integer)", "m4.master_can_cu_doc(uuid)",
           "m4.mc_co_ho_so(uuid, uuid)")
HAM_NOI_BO = ("m4._mc_sha(jsonb)", "m4._mc_meta(uuid, uuid, boolean)", "m4._mc_mapping_sha(uuid)",
              "m4._mc_ghi(uuid, jsonb, text, text, uuid, boolean)")
HAM_TRIGGER = ("m4._mc_ho_so_moi()", "m4._mc_quan_sat_hop_dong()", "m4._mc_quan_sat_mapping()", "m4._mc_chup_phien_ban()")
BANG = ("master_can_cu", "master_can_cu_phien_ban")
TRANG_THAI_NHAN = ("SOAN_THAO", "CHO_KY", "DA_KY", "HIEU_LUC")  # master state nhận được như nháp M4; HUY/khác → fail closed
NGUON = ("TAO_HO_SO_M4", "NHAN_MASTER_CO_SAN", "GAN_DOI_TAC", "QUAN_SAT_NGUON_HOP_DONG", "QUAN_SAT_NGUON_MAPPING",
         "BASELINE_BIET_TAI_NHAN", "BASELINE_BIET_TAI_NOP")
THIEU_NGUOI = "NGUON_KHONG_CO_DANH_TINH_PHIEN"  # nguồn không có danh tính phiên chứng minh được → actor NULL + lý do (không bịa)

_LOI = "USING ERRCODE = 'P0001'"
_HEX = "~ '^[0-9a-f]{64}$'"
_TT = "(" + ", ".join(f"'{t}'" for t in TRANG_THAI_NHAN) + ")"
_NG = "(" + ", ".join(f"'{t}'" for t in NGUON) + ")"


def _ts(c: str) -> str:
    """Mốc thời gian dạng chuẩn UTC (không phụ thuộc TimeZone phiên)."""
    return f"""to_char({c} AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')"""


_SOAN = """
            IF NOT master.m4_duoc({d}, 'SOAN') THEN
                RAISE EXCEPTION 'M4_KHONG_CO_QUYEN_DU_AN: cần quyền soạn hồ sơ hiện hành (phòng dự án phụ trách) đúng dự án' """ + _LOI + """;
            END IF;"""
_REPLAY = """
            cu := m4._bn_tra(aid, p_khoa, '{a}', {d}, yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;"""
_KET = """
            PERFORM m4._bn_ghi(aid, p_khoa, '{a}', {d}, yc, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);"""
_KHAI_BAO = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); yc jsonb; cu jsonb; kq jsonb;"
_Q = """
            IF p_q IS NULL OR length(p_q) > 100 OR p_q ~ '[[:cntrl:]]' OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 50 THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: q tối đa 100 ký tự, limit 1–50' """ + _LOI + """;
            END IF;"""
_NGUON_TRIGGER = """
            IF TG_RELID <> '{bang}'::regclass::oid OR TG_OP NOT IN ({op}) OR TG_WHEN <> 'AFTER' OR TG_LEVEL <> 'ROW' THEN
                RAISE EXCEPTION 'M4_CHI_CHU: hàm quan sát chỉ chạy từ đúng trigger nguồn đã khai báo' """ + _LOI + """;
            END IF;"""

M4_MASTER_DUNG_CHUNG_SQL = (
    "SET LOCAL check_function_bodies = off",
    # chủ sở hữu: trigger-function definer phải thuộc ĐÚNG chủ bảng nguồn/đích (guard cũ la_chu_bang/chi_chu cho phép, không nới guard)
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c WHERE c.oid IN ('m4.ho_so_hop_dong'::regclass, 'master.hop_dong'::regclass,
                       'master.doi_tac_ma_junsky'::regclass, 'm4.duyet_phien_ban'::regclass, 'm4.nhat_ky'::regclass)
                   AND c.relowner <> (SELECT r.oid FROM pg_catalog.pg_roles r WHERE r.rolname = current_user)) THEN
            RAISE EXCEPTION 'M4_CHI_CHU: gói master dùng chung phải áp dụng trên kết nối chủ bảng m4/master' USING ERRCODE = 'P0001';
        END IF;
    END $$""",
    # --- căn cứ master/mapping: ghi thêm, bất biến; record mới thay record trước (thay_cho), không sửa record cũ
    f"""CREATE TABLE m4.master_can_cu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        so integer NOT NULL CHECK (so >= 1),
        thay_cho uuid,
        revision_ho_so integer NOT NULL CHECK (revision_ho_so >= 1),
        meta jsonb NOT NULL CHECK (jsonb_typeof(meta) = 'object'),
        sha256 text NOT NULL CHECK (sha256 {_HEX}),
        mapping_id uuid REFERENCES master.doi_tac_ma_junsky(id),
        nguon text NOT NULL CHECK (nguon IN {_NG}),
        ly_do text CHECK (ly_do IS NULL OR length(btrim(ly_do)) BETWEEN 1 AND 1000),
        boi text,
        boi_id uuid REFERENCES master.nguoi_dung(id),
        thieu_nguoi text CHECK (thieu_nguoi IS NULL OR thieu_nguoi = '{THIEU_NGUOI}'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (hop_dong_id, so),
        UNIQUE (thay_cho),
        UNIQUE (id, hop_dong_id),
        UNIQUE (id, sha256),
        CHECK ((so = 1) = (thay_cho IS NULL)),
        CHECK ((boi IS NULL) = (boi_id IS NULL)),
        CHECK ((boi IS NULL) = (thieu_nguoi IS NOT NULL)),
        CHECK (nguon <> 'GAN_DOI_TAC' OR (ly_do IS NOT NULL AND boi IS NOT NULL AND mapping_id IS NOT NULL)))""",
    "ALTER TABLE m4.master_can_cu ADD CONSTRAINT master_can_cu_thay_cho_fk FOREIGN KEY (thay_cho, hop_dong_id) REFERENCES m4.master_can_cu (id, hop_dong_id)",
    "CREATE TRIGGER master_can_cu_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.master_can_cu FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()",
    # --- liên kết bất biến phiên bản đã nộp → căn cứ đúng giao dịch nộp (metadata FK-linked, KHÔNG nằm trong snapshot/digest JSON cũ)
    f"""CREATE TABLE m4.master_can_cu_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL UNIQUE,
        nop_id uuid REFERENCES m4.nop(id),
        can_cu_id uuid NOT NULL,
        can_cu_sha256 text NOT NULL CHECK (can_cu_sha256 {_HEX}),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phien_ban_id, du_an_id) REFERENCES m4.duyet_phien_ban (id, du_an_id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (can_cu_id, hop_dong_id) REFERENCES m4.master_can_cu (id, hop_dong_id),
        FOREIGN KEY (can_cu_id, can_cu_sha256) REFERENCES m4.master_can_cu (id, sha256))""",
    "CREATE TRIGGER master_can_cu_phien_ban_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.master_can_cu_phien_ban FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()",
    # ======================================================================= nội bộ (REVOKE PUBLIC/app_web; INVOKER — chỉ chạy dưới hàm định nghĩa)
    """CREATE OR REPLACE FUNCTION m4._mc_sha(p jsonb) RETURNS text
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT encode(sha256(convert_to(p::text, 'UTF8')), 'hex')
        $$""",
    # canonical meta: đọc master/mapping THẬT bằng snapshot mới của câu lệnh (VOLATILE); p_thay → tính trước cho đối tác sẽ gắn (cùng một công thức
    # với observer nên sau UPDATE master observer thấy cùng hash → no-op, không tăng revision lần hai)
    f"""CREATE OR REPLACE FUNCTION m4._mc_meta(p_hd uuid, p_doi_tac uuid, p_thay boolean) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SET search_path = master, m4, pg_temp AS $$
        DECLARE h record; dt uuid; refs jsonb; n_mo bigint; n_ok bigint; ok uuid; tt text;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.du_an_id, x.loai, x.so_hop_dong, x.ma_noi_bo, x.trang_thai, x.crm_giao_ket, x.module_chu, x.doi_tac_id,
                   x.phien_ban_hien_hanh INTO h FROM master.hop_dong x WHERE x.id = p_hd;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            dt := CASE WHEN p_thay THEN p_doi_tac ELSE h.doi_tac_id END;
            SELECT coalesce(jsonb_agg(jsonb_build_object('id', m.id, 'object_id_junsky', m.object_id_junsky, 'khoa', m.khoa, 'dong', m.dong,
                                                         'valid_from', {_ts('m.valid_from')}) ORDER BY m.id), '[]'::jsonb),
                   count(*), count(*) FILTER (WHERE NOT m.khoa AND NOT m.dong),
                   (array_agg(m.id ORDER BY m.id) FILTER (WHERE NOT m.khoa AND NOT m.dong))[1]
              INTO refs, n_mo, n_ok, ok
              FROM master.doi_tac_ma_junsky m
             WHERE dt IS NOT NULL AND m.doi_tac_id = dt AND m.phap_nhan_id = h.phap_nhan_id AND m.valid_to IS NULL;
            tt := CASE WHEN dt IS NULL THEN 'KHONG_DOI_TAC' WHEN n_ok = 1 THEN 'OK' WHEN n_ok > 1 THEN 'MO_HO' WHEN n_mo > 0 THEN 'KHOA_DONG' ELSE 'THIEU' END;
            RETURN jsonb_build_object('hop_dong_id', h.id, 'phap_nhan_id', h.phap_nhan_id, 'du_an_id', h.du_an_id, 'loai', h.loai,
                                      'so_hop_dong', h.so_hop_dong, 'ma_noi_bo', h.ma_noi_bo, 'trang_thai', h.trang_thai, 'crm_giao_ket', h.crm_giao_ket,
                                      'module_chu', h.module_chu, 'doi_tac_id', dt, 'phien_ban_hien_hanh', h.phien_ban_hien_hanh,
                                      'mapping', refs, 'mapping_trang_thai', tt, 'mapping_hien_hanh', CASE WHEN tt = 'OK' THEN ok END);
        END $$""",
    f"""CREATE OR REPLACE FUNCTION m4._mc_mapping_sha(p uuid) RETURNS text
        LANGUAGE sql VOLATILE SET search_path = master, m4, pg_temp AS $$
        SELECT m4._mc_sha(jsonb_build_object('id', m.id, 'doi_tac_id', m.doi_tac_id, 'phap_nhan_id', m.phap_nhan_id, 'object_id_junsky', m.object_id_junsky,
                                             'khoa', m.khoa, 'dong', m.dong, 'valid_from', {_ts('m.valid_from')},
                                             'valid_to', CASE WHEN m.valid_to IS NOT NULL THEN {_ts('m.valid_to')} END))
        FROM master.doi_tac_ma_junsky m WHERE m.id = p
        $$""",
    # ghi thêm căn cứ dưới khóa hồ sơ: cùng hash với record mới nhất → no-op; khác → record mới (thay_cho record trước) và, nếu p_tang và đã có
    # record trước, tăng revision + rev_tham_so ĐÚNG 1 (cổng m4.thieu/DuyetDot hiện có tự chặn/CAN_KIEM_LAI). Record đầu tiên = baseline, không tăng.
    # Actor: danh tính phiên đã chứng minh (ID+login) hoặc NULL + lý do thiếu — không bịa, không SET GUC.
    f"""CREATE OR REPLACE FUNCTION m4._mc_ghi(p_hd uuid, p_meta jsonb, p_nguon text, p_ly_do text, p_mapping uuid, p_tang boolean) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SET search_path = master, m4, pg_temp AS $$
        DECLARE h record; c record; v_sha text; v_ai text := master.ktt_danh_tinh(); v_aid uuid; v_rev integer; v_id uuid; v_so integer;
        BEGIN
            IF p_meta IS NULL THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hợp đồng master của hồ sơ' {_LOI};
            END IF;
            v_sha := m4._mc_sha(p_meta);
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hồ sơ hợp đồng M4' {_LOI};
            END IF;
            SELECT * INTO c FROM m4.master_can_cu WHERE hop_dong_id = p_hd ORDER BY so DESC LIMIT 1;
            IF c.id IS NOT NULL AND c.sha256 = v_sha THEN
                RETURN jsonb_build_object('id', c.id, 'sha256', c.sha256, 'so', c.so, 'moi', false, 'revision', h.revision);
            END IF;
            v_rev := h.revision;
            IF c.id IS NOT NULL AND p_tang THEN
                UPDATE m4.ho_so_hop_dong SET revision = revision + 1, rev_tham_so = rev_tham_so + 1, cap_nhat_luc = now() WHERE hop_dong_id = p_hd
                    RETURNING revision INTO v_rev;
            END IF;
            IF v_ai IS NOT NULL THEN
                SELECT n.id INTO v_aid FROM master.nguoi_dung n
                 WHERE n.dang_nhap = v_ai AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '');
            END IF;
            IF v_aid IS NULL THEN
                v_ai := NULL;
            END IF;
            INSERT INTO m4.master_can_cu (phap_nhan_id, du_an_id, hop_dong_id, so, thay_cho, revision_ho_so, meta, sha256, mapping_id, nguon, ly_do,
                                          boi, boi_id, thieu_nguoi)
                VALUES (h.phap_nhan_id, h.du_an_id, p_hd, coalesce(c.so, 0) + 1, c.id, v_rev, p_meta, v_sha, p_mapping, p_nguon, p_ly_do,
                        v_ai, v_aid, CASE WHEN v_aid IS NULL THEN '{THIEU_NGUOI}' END)
                RETURNING id, so INTO v_id, v_so;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (h.du_an_id, p_hd, NULL, 'MASTER_CAN_CU', coalesce(v_ai, 'HE_THONG:' || p_nguon),
                        jsonb_build_object('can_cu_id', v_id, 'so', v_so, 'nguon', p_nguon, 'sha256', v_sha, 'revision', v_rev,
                                           'tang_revision', v_rev <> h.revision, 'thieu_nguoi', CASE WHEN v_aid IS NULL THEN '{THIEU_NGUOI}' END));
            RETURN jsonb_build_object('id', v_id, 'sha256', v_sha, 'so', v_so, 'moi', true, 'revision', v_rev);
        END $$""",
    # ======================================================================= trigger quan sát (INTERNAL SECURITY DEFINER của chủ bảng)
    # hook tạo hồ sơ (tao_hop_dong M17 hoặc nhận master): baseline căn cứ hiện tại, không tăng revision, không viết lịch sử cũ
    """CREATE OR REPLACE FUNCTION m4._mc_ho_so_moi() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE m jsonb;
        BEGIN""" + _NGUON_TRIGGER.format(bang="m4.ho_so_hop_dong", op="'INSERT'") + """
            m := m4._mc_meta(NEW.hop_dong_id, NULL, false);
            PERFORM m4._mc_ghi(NEW.hop_dong_id, m, CASE WHEN m->>'module_chu' = 'M4' THEN 'TAO_HO_SO_M4' ELSE 'NHAN_MASTER_CO_SAN' END, NULL,
                               (m->>'mapping_hien_hanh')::uuid, false);
            RETURN NULL;
        END $$""",
    # nguồn master đổi (CRM G6A/lệnh hợp lệ khác, hoặc chính lệnh gắn đối tác): giao dịch nguồn đã giữ khóa hàng master → khóa hồ sơ → tính lại
    """CREATE OR REPLACE FUNCTION m4._mc_quan_sat_hop_dong() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE m jsonb;
        BEGIN""" + _NGUON_TRIGGER.format(bang="master.hop_dong", op="'UPDATE'") + """
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = NEW.id FOR UPDATE;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            m := m4._mc_meta(NEW.id, NULL, false);
            PERFORM m4._mc_ghi(NEW.id, m, 'QUAN_SAT_NGUON_HOP_DONG', NULL, (m->>'mapping_hien_hanh')::uuid, true);
            RETURN NULL;
        END $$""",
    # nguồn mapping thêm/đóng/khóa/đổi: khóa master tiềm năng cùng PN theo id↑ (FOR SHARE) rồi hồ sơ; đọc lại thật SAU khóa (bắt cả HĐ vừa gắn
    # đối tác song song). Không cập nhật mapping/master; chỉ ghi thêm căn cứ + tăng revision hồ sơ bị ảnh hưởng.
    """CREATE OR REPLACE FUNCTION m4._mc_quan_sat_mapping() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE pn uuid[]; dt uuid[]; r record; m jsonb;
        BEGIN""" + _NGUON_TRIGGER.format(bang="master.doi_tac_ma_junsky", op="'INSERT', 'UPDATE', 'DELETE'") + """
            IF TG_OP = 'INSERT' THEN
                pn := ARRAY[NEW.phap_nhan_id]; dt := ARRAY[NEW.doi_tac_id];
            ELSIF TG_OP = 'DELETE' THEN
                pn := ARRAY[OLD.phap_nhan_id]; dt := ARRAY[OLD.doi_tac_id];
            ELSE
                IF (OLD.doi_tac_id, OLD.phap_nhan_id, OLD.object_id_junsky, OLD.khoa, OLD.dong, OLD.valid_from, OLD.valid_to)
                   IS NOT DISTINCT FROM (NEW.doi_tac_id, NEW.phap_nhan_id, NEW.object_id_junsky, NEW.khoa, NEW.dong, NEW.valid_from, NEW.valid_to) THEN
                    RETURN NULL;
                END IF;
                pn := ARRAY[OLD.phap_nhan_id, NEW.phap_nhan_id]; dt := ARRAY[OLD.doi_tac_id, NEW.doi_tac_id];
            END IF;
            FOR r IN SELECT h.id FROM master.hop_dong h
                      WHERE h.phap_nhan_id = ANY (pn) AND h.loai = 'XAY_DUNG'
                        AND (h.doi_tac_id = ANY (dt) OR EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = h.id))
                      ORDER BY h.id FOR SHARE OF h LOOP
                PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.id FOR UPDATE;
                IF FOUND THEN
                    m := m4._mc_meta(r.id, NULL, false);
                    PERFORM m4._mc_ghi(r.id, m, 'QUAN_SAT_NGUON_MAPPING', NULL, (m->>'mapping_hien_hanh')::uuid, true);
                END IF;
            END LOOP;
            RETURN NULL;
        END $$""",
    # chụp căn cứ đúng giao dịch nộp: bản 1 (m4.nop → duyet_phien_ban_tu_nop) và bản kế NHAP→DA_NOP. Không đổi snapshot/digest của nop/phiên bản.
    # Hồ sơ chưa có record (không có baseline di trú) → baseline 'biết tại thời điểm nộp'; căn cứ hiện hành lệch nguồn thật → chặn (không lặng lẽ nộp).
    """CREATE OR REPLACE FUNCTION m4._mc_chup_phien_ban() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE c record; m jsonb; k jsonb;
        BEGIN""" + _NGUON_TRIGGER.format(bang="m4.duyet_phien_ban", op="'INSERT', 'UPDATE'") + """
            IF NEW.trang_thai <> 'DA_NOP' THEN
                RETURN NULL;
            END IF;
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = NEW.hop_dong_id FOR UPDATE;
            m := m4._mc_meta(NEW.hop_dong_id, NULL, false);
            SELECT * INTO c FROM m4.master_can_cu WHERE hop_dong_id = NEW.hop_dong_id ORDER BY so DESC LIMIT 1;
            IF c.id IS NULL THEN
                k := m4._mc_ghi(NEW.hop_dong_id, m, 'BASELINE_BIET_TAI_NOP', NULL, (m->>'mapping_hien_hanh')::uuid, false);
            ELSIF c.sha256 IS DISTINCT FROM m4._mc_sha(m) THEN
                RAISE EXCEPTION 'M4_MASTER_CAN_CU_DOI: căn cứ master/mapping nguồn khác căn cứ hiện hành của hồ sơ — tải lại, soát lại rồi nộp' """ + _LOI + """;
            ELSE
                k := jsonb_build_object('id', c.id, 'sha256', c.sha256);
            END IF;
            INSERT INTO m4.master_can_cu_phien_ban (phap_nhan_id, du_an_id, hop_dong_id, phien_ban_id, nop_id, can_cu_id, can_cu_sha256)
                VALUES (NEW.phap_nhan_id, NEW.du_an_id, NEW.hop_dong_id, NEW.id, NEW.nop_id, (k->>'id')::uuid, k->>'sha256');
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER ho_so_hop_dong_master_can_cu AFTER INSERT ON m4.ho_so_hop_dong FOR EACH ROW EXECUTE FUNCTION m4._mc_ho_so_moi()",
    """CREATE TRIGGER hop_dong_m4_master_can_cu AFTER UPDATE ON master.hop_dong FOR EACH ROW
        WHEN ((OLD.doi_tac_id, OLD.du_an_id, OLD.loai, OLD.trang_thai, OLD.crm_giao_ket, OLD.module_chu, OLD.phien_ban_hien_hanh)
              IS DISTINCT FROM (NEW.doi_tac_id, NEW.du_an_id, NEW.loai, NEW.trang_thai, NEW.crm_giao_ket, NEW.module_chu, NEW.phien_ban_hien_hanh))
        EXECUTE FUNCTION m4._mc_quan_sat_hop_dong()""",
    "CREATE TRIGGER doi_tac_ma_junsky_m4_can_cu AFTER INSERT OR UPDATE OR DELETE ON master.doi_tac_ma_junsky FOR EACH ROW EXECUTE FUNCTION m4._mc_quan_sat_mapping()",
    """CREATE TRIGGER duyet_phien_ban_master_can_cu_chen AFTER INSERT ON m4.duyet_phien_ban FOR EACH ROW WHEN (NEW.trang_thai = 'DA_NOP')
        EXECUTE FUNCTION m4._mc_chup_phien_ban()""",
    """CREATE TRIGGER duyet_phien_ban_master_can_cu_nop AFTER UPDATE ON m4.duyet_phien_ban FOR EACH ROW
        WHEN (OLD.trang_thai = 'NHAP' AND NEW.trang_thai = 'DA_NOP') EXECUTE FUNCTION m4._mc_chup_phien_ban()""",
    # ======================================================================= đọc (app_web; SOAN/XEM/REVIEW hiện hành kiểm trong hàm)
    # policy đọc master.hop_dong hẹp: chỉ HĐ có hồ sơ M4 thật đúng dự án + quyền XEM/REVIEW hiện hành (không cấp CRM, không master khác)
    """CREATE OR REPLACE FUNCTION m4.mc_co_ho_so(p_hd uuid, p_du_an uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT p_hd IS NOT NULL AND p_du_an IS NOT NULL
               AND EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = p_hd AND s.du_an_id = p_du_an)
               AND (master.m4_duoc(p_du_an, 'XEM') OR master.m4_duoc(p_du_an, 'REVIEW'))
        $$""",
    # ứng viên master cho bộ chọn: SOAN hiện hành đúng dự án; PN suy từ master.du_an; chỉ XAY_DUNG đúng PN/dự án + trạng thái đã chốt; giới hạn
    f"""CREATE OR REPLACE FUNCTION m4.master_hop_dong_ds(p_du_an uuid, p_q text, p_limit integer) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d record; ds jsonb;
        BEGIN""" + _SOAN.format(d="p_du_an") + _Q + f"""
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            SELECT coalesce(jsonb_agg(x.o ORDER BY x.so_hop_dong, x.id), '[]'::jsonb) INTO ds FROM (
                SELECT h.so_hop_dong, h.id,
                       jsonb_build_object('hop_dong_id', h.id, 'so_hop_dong', h.so_hop_dong, 'ma_noi_bo', h.ma_noi_bo, 'trang_thai_master', h.trang_thai,
                                          'module_chu', h.module_chu, 'doi_tac_id', h.doi_tac_id, 'doi_tac_ten', t.ten_phap_ly,
                                          'da_co_ho_so_m4', s.hop_dong_id IS NOT NULL, 'revision_ho_so', s.revision,
                                          'expected_master', m4._mc_sha(m4._mc_meta(h.id, NULL, false))) AS o
                  FROM master.hop_dong h
                  LEFT JOIN master.doi_tac t ON t.id = h.doi_tac_id
                  LEFT JOIN m4.ho_so_hop_dong s ON s.hop_dong_id = h.id
                 WHERE h.phap_nhan_id = d.phap_nhan_id AND h.du_an_id = p_du_an AND h.loai = 'XAY_DUNG'
                   AND h.trang_thai IN {_TT} AND (h.crm_giao_ket IS NULL OR h.crm_giao_ket = h.trang_thai)
                   AND (p_q = '' OR strpos(lower(h.so_hop_dong), lower(p_q)) > 0 OR strpos(lower(h.ma_noi_bo), lower(p_q)) > 0)
                 ORDER BY h.so_hop_dong, h.id
                 LIMIT p_limit) x;
            RETURN jsonb_build_object('du_an_id', p_du_an, 'items', ds, 'limit', p_limit);
        END $$""",
    # đối tác hiện hành cùng PN: master.doi_tac + doi_tac_ma_junsky đang mở (valid_to IS NULL); đúng MỘT mapping dùng được mới có mapping_id,
    # còn lại trả mã HOLD (mơ hồ/chưa hiệu lực/khóa-đóng) — không đoán theo MST/tên/hóa đơn
    f"""CREATE OR REPLACE FUNCTION m4.master_doi_tac_ds(p_du_an uuid, p_q text, p_limit integer) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d record; ds jsonb;
        BEGIN""" + _SOAN.format(d="p_du_an") + _Q + """
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            SELECT coalesce(jsonb_agg(x.o ORDER BY x.ten, x.id), '[]'::jsonb) INTO ds FROM (
                SELECT t.ten_phap_ly AS ten, t.id,
                       jsonb_build_object('doi_tac_id', t.id, 'ten', t.ten_phap_ly,
                                          'ma_junsky', CASE WHEN g.n_ok = 1 THEN g.ma END,
                                          'mapping_id', CASE WHEN g.n_ok = 1 THEN g.mid END,
                                          'expected_mapping', CASE WHEN g.n_ok = 1 THEN m4._mc_mapping_sha(g.mid) END,
                                          'ma_hold', CASE WHEN g.n_ok = 1 THEN NULL WHEN g.n_ok > 1 THEN 'M4_MAPPING_MO_HO'
                                                          WHEN g.n_cho > 0 THEN 'M4_MAPPING_CHUA_HIEU_LUC' ELSE 'M4_MAPPING_KHOA_DONG' END) AS o
                  FROM master.doi_tac t
                 CROSS JOIN LATERAL (
                       SELECT count(*) AS n,
                              count(*) FILTER (WHERE NOT m.khoa AND NOT m.dong AND m.valid_from <= now()) AS n_ok,
                              count(*) FILTER (WHERE NOT m.khoa AND NOT m.dong AND m.valid_from > now()) AS n_cho,
                              (array_agg(m.id ORDER BY m.id) FILTER (WHERE NOT m.khoa AND NOT m.dong AND m.valid_from <= now()))[1] AS mid,
                              (array_agg(m.object_id_junsky ORDER BY m.id) FILTER (WHERE NOT m.khoa AND NOT m.dong AND m.valid_from <= now()))[1] AS ma,
                              string_agg(lower(m.object_id_junsky), ' ') AS ma_tim
                         FROM master.doi_tac_ma_junsky m
                        WHERE m.doi_tac_id = t.id AND m.phap_nhan_id = d.phap_nhan_id AND m.valid_to IS NULL) g
                 WHERE g.n > 0 AND t.trang_thai = 'HOAT_DONG' AND (t.phap_nhan_id IS NULL OR t.phap_nhan_id = d.phap_nhan_id)
                   AND (p_q = '' OR strpos(lower(t.ten_phap_ly), lower(p_q)) > 0 OR strpos(g.ma_tim, lower(p_q)) > 0)
                 ORDER BY t.ten_phap_ly, t.id
                 LIMIT p_limit) x;
            RETURN jsonb_build_object('du_an_id', p_du_an, 'items', ds, 'limit', p_limit);
        END $$""",
    # căn cứ của MỘT hồ sơ (gắn vào chi_tiet): XEM/REVIEW hiện hành; ngoài phạm vi → NULL (không lộ tồn tại)
    """CREATE OR REPLACE FUNCTION m4.master_can_cu_doc(p_hd uuid) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE h record; hm record; c record; m jsonb; v_sha text; n_chua bigint; v_ma text; hold jsonb := '[]'::jsonb; ten_dt text; ma_dt text;
        BEGIN
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd;
            IF NOT FOUND OR NOT (master.m4_duoc(h.du_an_id, 'XEM') OR master.m4_duoc(h.du_an_id, 'REVIEW')) THEN
                RETURN NULL;
            END IF;
            SELECT x.module_chu, x.crm_giao_ket, x.phien_ban_hien_hanh INTO hm FROM master.hop_dong x WHERE x.id = p_hd;
            m := m4._mc_meta(p_hd, NULL, false);
            v_sha := m4._mc_sha(m);
            SELECT * INTO c FROM m4.master_can_cu WHERE hop_dong_id = p_hd ORDER BY so DESC LIMIT 1;
            SELECT count(*) INTO n_chua FROM m4.duyet_phien_ban v
             WHERE v.hop_dong_id = p_hd AND v.trang_thai = 'DA_NOP'
               AND NOT EXISTS (SELECT 1 FROM m4.master_can_cu_phien_ban l WHERE l.phien_ban_id = v.id);
            SELECT t.ten_phap_ly INTO ten_dt FROM master.doi_tac t WHERE t.id = (m->>'doi_tac_id')::uuid;
            SELECT j.object_id_junsky INTO ma_dt FROM master.doi_tac_ma_junsky j WHERE j.id = (m->>'mapping_hien_hanh')::uuid;
            v_ma := CASE WHEN NOT master.m4_duoc(h.du_an_id, 'SOAN') THEN 'M4_KHONG_CO_QUYEN_DU_AN'
                         WHEN hm.module_chu IS DISTINCT FROM 'M4' OR hm.crm_giao_ket IS NOT NULL OR hm.phien_ban_hien_hanh IS NOT NULL
                              THEN 'M4_MASTER_CAN_SUA_TAI_NGUON'
                         WHEN EXISTS (SELECT 1 FROM m4.nop n WHERE n.hop_dong_id = p_hd)
                              OR EXISTS (SELECT 1 FROM m4.duyet_phien_ban v WHERE v.hop_dong_id = p_hd) THEN 'M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH' END;
            IF m->>'mapping_trang_thai' <> 'OK' THEN
                hold := hold || to_jsonb('MAPPING_' || (m->>'mapping_trang_thai'));
            END IF;
            IF c.id IS NULL OR c.sha256 <> v_sha THEN
                hold := hold || to_jsonb('CAN_CU_CHUA_DONG_BO'::text);
            END IF;
            IF c.thieu_nguoi IS NOT NULL THEN
                hold := hold || to_jsonb('CAN_CU_CHUA_CO_NGUOI_XAC_NHAN'::text);
            END IF;
            IF n_chua > 0 THEN
                hold := hold || to_jsonb('LICH_SU_NOP_CHUA_CHUNG_MINH'::text);
            END IF;
            RETURN jsonb_build_object(
                'hop_dong_id', p_hd, 'revision', h.revision, 'expected_master', v_sha,
                'master', jsonb_build_object('module_chu', m->'module_chu', 'trang_thai_master', m->'trang_thai', 'crm_giao_ket', m->'crm_giao_ket',
                                             'doi_tac_id', m->'doi_tac_id', 'doi_tac_ten', ten_dt, 'ma_junsky', ma_dt,
                                             'mapping_trang_thai', m->'mapping_trang_thai', 'mapping_hien_hanh', m->'mapping_hien_hanh'),
                'can_cu', CASE WHEN c.id IS NULL THEN NULL ELSE jsonb_build_object('id', c.id, 'so', c.so, 'sha256', c.sha256, 'nguon', c.nguon,
                                             'mapping_id', c.mapping_id, 'revision_ho_so', c.revision_ho_so, 'ly_do', c.ly_do, 'boi', c.boi,
                                             'thieu_nguoi', c.thieu_nguoi, 'tao_luc', c.tao_luc) END,
                'dong_bo', c.id IS NOT NULL AND c.sha256 = v_sha,
                'phien_ban_chua_chung_minh', n_chua,
                'gan_doi_tac', jsonb_build_object('duoc', v_ma IS NULL, 'ma', v_ma),
                'hold', hold);
        END $$""",
    # ======================================================================= lệnh (app_web; SOAN hiện hành TRƯỚC replay; biên nhận m4.bien_nhan)
    # nhận master có sẵn thành hồ sơ M4 nháp: khóa master → hồ sơ; chỉ INSERT hồ sơ + nhật ký + biên nhận (hook ghi baseline). Không ghi master/CRM.
    f"""CREATE OR REPLACE FUNCTION m4.nhan_master_hop_dong(p_khoa text, p_du_an uuid, p_hd uuid, p_ten text, p_expected_master text) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + f""" d record; hm record; h record; c record; m jsonb; v_sha text; v_co boolean;
        BEGIN
            yc := jsonb_build_object('du_an_id', p_du_an, 'hop_dong_id', p_hd, 'ten', p_ten, 'expected_master', p_expected_master);""" + _SOAN.format(d="p_du_an")
    + _REPLAY.format(a="NHAN_MASTER_HOP_DONG", d="p_du_an") + f"""
            IF p_ten IS NULL OR length(p_ten) NOT BETWEEN 1 AND 300 OR p_expected_master IS NULL OR p_expected_master !{_HEX} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: cần tên hồ sơ (1–300 ký tự) và expected_master hợp lệ' {_LOI};
            END IF;
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            SELECT x.id, x.trang_thai, x.crm_giao_ket, x.module_chu, x.so_hop_dong INTO hm FROM master.hop_dong x
             WHERE x.id = p_hd AND x.phap_nhan_id = d.phap_nhan_id AND x.du_an_id = p_du_an AND x.loai = 'XAY_DUNG' FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_MASTER_KHONG_THAY: không thấy hợp đồng xây dựng phù hợp trong dự án' {_LOI};
            END IF;
            IF hm.trang_thai NOT IN {_TT} OR (hm.crm_giao_ket IS NOT NULL AND hm.crm_giao_ket <> hm.trang_thai) THEN
                RAISE EXCEPTION 'M4_MASTER_TRANG_THAI_KHONG_NHAN: trạng thái hợp đồng nguồn không nhận được thành hồ sơ M4' {_LOI};
            END IF;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd FOR UPDATE;
            v_co := FOUND;
            m := m4._mc_meta(p_hd, NULL, false);
            v_sha := m4._mc_sha(m);
            IF v_sha IS DISTINCT FROM p_expected_master THEN
                RAISE EXCEPTION 'M4_MASTER_DA_DOI: hợp đồng nguồn/đối tác/mapping đã đổi — tải lại danh sách rồi chọn lại' {_LOI};
            END IF;
            IF NOT v_co THEN
                INSERT INTO m4.ho_so_hop_dong (hop_dong_id, phap_nhan_id, du_an_id, ten, tao_boi) VALUES (p_hd, d.phap_nhan_id, p_du_an, p_ten, ai);
                SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd;
            END IF;
            SELECT * INTO c FROM m4.master_can_cu WHERE hop_dong_id = p_hd ORDER BY so DESC LIMIT 1;
            IF NOT v_co THEN
                INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet) VALUES (p_du_an, p_hd, NULL, 'NHAN_MASTER_HOP_DONG', ai,
                    jsonb_build_object('so_hop_dong', hm.so_hop_dong, 'module_chu', hm.module_chu, 'trang_thai_master', hm.trang_thai,
                                       'master_can_cu_id', c.id, 'master_can_cu_sha256', c.sha256));
            END IF;
            kq := jsonb_build_object('hop_dong_id', p_hd, 'revision', h.revision, 'expected_master', v_sha, 'master_can_cu_id', c.id,
                                     'master_can_cu_sha256', c.sha256, 'da_co_san', v_co);""" + _KET.format(a="NHAN_MASTER_HOP_DONG", d="p_du_an") + """
        END $$""",
    # gắn/sửa đối tác trên nháp DO M4 SỞ HỮU, trước mọi lần nộp: khóa master → hồ sơ; đọc mapping MVCC mới (không khóa mapping); căn cứ ghi TRƯỚC
    # (ly_do + actor + bump 1), rồi UPDATE master.doi_tac_id qua guard hiện hữu → observer master thấy cùng hash → no-op.
    f"""CREATE OR REPLACE FUNCTION m4.gan_doi_tac_hop_dong(p_khoa text, p_hd uuid, p_doi_tac uuid, p_mapping uuid, p_rev integer,
                                                        p_expected_master text, p_expected_mapping text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + f""" v_du_an uuid; hm record; h record; mp record; t record; m jsonb; g jsonb; k jsonb;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'doi_tac_id', p_doi_tac, 'mapping_id', p_mapping, 'revision', p_rev,
                                     'expected_master', p_expected_master, 'expected_mapping', p_expected_mapping, 'ly_do', p_ly_do);
            SELECT s.du_an_id INTO v_du_an FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = p_hd;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hồ sơ hợp đồng M4' {_LOI};
            END IF;""" + _SOAN.format(d="v_du_an") + _REPLAY.format(a="GAN_DOI_TAC_HOP_DONG", d="v_du_an") + f"""
            IF p_doi_tac IS NULL OR p_mapping IS NULL THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: cần đối tác và mapping cụ thể' {_LOI};
            END IF;
            -- thứ tự khóa: (khóa tư vấn biên nhận) → master → hồ sơ, như lệnh nhận; quyền hiện hành kiểm lại dưới khóa
            SELECT x.id, x.phap_nhan_id, x.du_an_id, x.module_chu, x.crm_giao_ket, x.phien_ban_hien_hanh, x.doi_tac_id INTO hm
              FROM master.hop_dong x WHERE x.id = p_hd FOR UPDATE;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd FOR UPDATE;""" + _SOAN.format(d="h.du_an_id") + f"""
            IF hm.module_chu IS DISTINCT FROM 'M4' OR hm.crm_giao_ket IS NOT NULL OR hm.phien_ban_hien_hanh IS NOT NULL THEN
                RAISE EXCEPTION 'M4_MASTER_CAN_SUA_TAI_NGUON: hợp đồng do nguồn khác quản lý/đã khóa — chọn/sửa đối tác theo authority nguồn (CRM/master)' {_LOI};
            END IF;
            IF EXISTS (SELECT 1 FROM m4.nop n WHERE n.hop_dong_id = p_hd) OR EXISTS (SELECT 1 FROM m4.duyet_phien_ban v WHERE v.hop_dong_id = p_hd) THEN
                RAISE EXCEPTION 'M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH: hồ sơ đã nộp — đổi đối tác cần căn cứ/quyết định phiên bản điều chỉnh (chưa triển khai)' {_LOI};
            END IF;
            IF p_rev IS NULL OR h.revision <> p_rev THEN
                RAISE EXCEPTION 'M4_REVISION_CU: hồ sơ đã đổi (revision hiện tại %) — tải lại rồi thao tác', h.revision {_LOI};
            END IF;
            IF p_ly_do IS NULL OR length(btrim(p_ly_do)) NOT BETWEEN 1 AND 1000 OR p_ly_do ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'M4_LY_DO_BAT_BUOC: cần lý do gắn/sửa đối tác (1–1000 ký tự)' {_LOI};
            END IF;
            m := m4._mc_meta(p_hd, NULL, false);
            IF p_expected_master IS NULL OR m4._mc_sha(m) IS DISTINCT FROM p_expected_master THEN
                RAISE EXCEPTION 'M4_MASTER_DA_DOI: hợp đồng nguồn/đối tác/mapping đã đổi — tải lại rồi chọn lại' {_LOI};
            END IF;
            IF hm.doi_tac_id IS NOT DISTINCT FROM p_doi_tac THEN
                RAISE EXCEPTION 'M4_KHONG_DOI: đối tác này đang là đối tác hiện hành của hợp đồng' {_LOI};
            END IF;
            -- mapping: đọc MVCC mới SAU khóa master/hồ sơ, không khóa hàng mapping (nguồn đóng mapping song song → observer mapping xử lý, xem docstring)
            SELECT * INTO mp FROM master.doi_tac_ma_junsky WHERE id = p_mapping;
            IF NOT FOUND OR mp.doi_tac_id <> p_doi_tac OR mp.phap_nhan_id <> hm.phap_nhan_id THEN
                RAISE EXCEPTION 'M4_MAPPING_KHONG_THAY: không thấy mapping đối tác đúng pháp nhân' {_LOI};
            END IF;
            SELECT * INTO t FROM master.doi_tac WHERE id = p_doi_tac;
            IF t.trang_thai IS DISTINCT FROM 'HOAT_DONG' OR (t.phap_nhan_id IS NOT NULL AND t.phap_nhan_id <> hm.phap_nhan_id) THEN
                RAISE EXCEPTION 'M4_DOI_TAC_KHONG_HOP_LE: đối tác không hoạt động hoặc khác pháp nhân' {_LOI};
            END IF;
            IF p_expected_mapping IS NULL OR m4._mc_mapping_sha(p_mapping) IS DISTINCT FROM p_expected_mapping THEN
                RAISE EXCEPTION 'M4_MAPPING_DA_DOI: mapping đối tác đã đổi — tải lại danh sách đối tác' {_LOI};
            END IF;
            IF mp.valid_to IS NOT NULL OR mp.khoa OR mp.dong OR mp.valid_from > now() THEN
                RAISE EXCEPTION 'M4_MAPPING_KHONG_HIEN_HANH: mapping đã đóng/khóa hoặc chưa hiệu lực' {_LOI};
            END IF;
            g := m4._mc_meta(p_hd, p_doi_tac, true);
            IF g->>'mapping_trang_thai' <> 'OK' OR (g->>'mapping_hien_hanh')::uuid IS DISTINCT FROM p_mapping THEN
                RAISE EXCEPTION 'M4_MAPPING_MO_HO: đối tác có nhiều mapping mở cùng pháp nhân — chờ nguồn master làm rõ (HOLD)' {_LOI};
            END IF;
            IF NOT EXISTS (SELECT 1 FROM m4.master_can_cu WHERE hop_dong_id = p_hd) THEN
                PERFORM m4._mc_ghi(p_hd, m, 'BASELINE_BIET_TAI_NHAN', NULL, (m->>'mapping_hien_hanh')::uuid, false);
            END IF;
            k := m4._mc_ghi(p_hd, g, 'GAN_DOI_TAC', btrim(p_ly_do), p_mapping, true);
            UPDATE master.hop_dong SET doi_tac_id = p_doi_tac WHERE id = p_hd;
            IF m4._mc_sha(m4._mc_meta(p_hd, NULL, false)) IS DISTINCT FROM k->>'sha256' THEN
                RAISE EXCEPTION 'M4_MASTER_DA_DOI: căn cứ sau gắn không khớp nguồn — không ghi' {_LOI};
            END IF;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet) VALUES (h.du_an_id, p_hd, NULL, 'GAN_DOI_TAC_HOP_DONG', ai,
                jsonb_build_object('doi_tac_cu', hm.doi_tac_id, 'doi_tac_moi', p_doi_tac, 'mapping_id', p_mapping, 'master_can_cu_id', k->>'id',
                                   'revision', (k->>'revision')::integer, 'ly_do', btrim(p_ly_do)));
            kq := jsonb_build_object('hop_dong_id', p_hd, 'revision', (k->>'revision')::integer, 'expected_master', k->>'sha256',
                                     'master_can_cu_id', k->>'id', 'master_can_cu_sha256', k->>'sha256');""" + _KET.format(a="GAN_DOI_TAC_HOP_DONG", d="h.du_an_id") + """
        END $$""",
    # --- baseline cho hồ sơ đã có: căn cứ HIỆN TẠI 'biết tại thời điểm nhận' (không backfill facts lúc nộp lịch sử; bản đã nộp không có liên kết
    # → master_can_cu_doc báo LICH_SU_NOP_CHUA_CHUNG_MINH → HOLD khi dùng tài chính). Actor NULL + lý do thiếu (di trú không có danh tính phiên).
    """DO $$
    DECLARE r record; m jsonb;
    BEGIN
        FOR r IN SELECT s.hop_dong_id FROM m4.ho_so_hop_dong s ORDER BY s.hop_dong_id LOOP
            m := m4._mc_meta(r.hop_dong_id, NULL, false);
            PERFORM m4._mc_ghi(r.hop_dong_id, m, 'BASELINE_BIET_TAI_NHAN', NULL, (m->>'mapping_hien_hanh')::uuid, false);
        END LOOP;
    END $$""",
    # ======================================================================= quyền
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_LENH + HAM_DOC + HAM_NOI_BO + HAM_TRIGGER) + " FROM PUBLIC",
    "REVOKE ALL ON " + ", ".join(f"m4.{t}" for t in BANG) + " FROM PUBLIC",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            REVOKE EXECUTE ON FUNCTION """ + ", ".join(HAM_NOI_BO + HAM_TRIGGER) + """ FROM app_web;
            GRANT SELECT ON m4.master_can_cu, m4.master_can_cu_phien_ban TO app_web;
            CREATE POLICY master_can_cu_web ON m4.master_can_cu FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY master_can_cu_phien_ban_web ON m4.master_can_cu_phien_ban FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY hop_dong_m4_ho_so ON master.hop_dong FOR SELECT TO app_web USING (m4.mc_co_ho_so(id, du_an_id));
            GRANT EXECUTE ON FUNCTION """ + ", ".join(HAM_LENH + HAM_DOC) + """ TO app_web;
        END IF;
    END $$""",
)
