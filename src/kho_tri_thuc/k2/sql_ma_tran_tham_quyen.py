"""MTQ-1: chỉ hằng SQL, chưa nối quyền cũ. Các hàm là SECURITY INVOKER.

Giống master CRM: thu hồi mọi quyền của app, dịch vụ dùng kết nối chủ bảng
và danh tính phiên đã xác thực. Không đưa các hàm này ra kết nối SQL của client.
MTQ-4 cung cấp resolver đối tượng/tiền và thay readiness sau khi đủ bao phủ.

Bootstrap chỉ khi mtq_admin chưa từng có dòng (kể cả dòng đã thu hồi vẫn chặn),
session_user phải thuộc vai chủ bảng; người được chỉ định phải đang hoạt động,
cap_boi = p_nguoi. Web dùng kết nối chủ bảng nên MTQ-2 không mở bootstrap qua
HTTP; chỉ công cụ lead tin cậy được gọi mtq_bootstrap_admin.
"""

_VAI = "('THUC_HIEN_1','THUC_HIEN_2','TRUONG_PHONG','CFO','NGUOI_XEM')"
_BANG = (
    "master.mtq_phong", "master.mtq_admin", "master.mtq_danh_muc_hanh_dong",
    "master.mtq_phien_ban", "master.mtq_dong", "master.mtq_o",
    "master.mtq_gan_vai", "master.mtq_pham_vi", "master.mtq_kich_hoat",
    "nhat_ky.mtq_thay_doi", "nhat_ky.mtq_tu_choi",
)
_HAM = (
    "master.mtq_la_admin()", "master.mtq_san_sang(uuid)",
    "master.mtq_bat_bien()", "master.mtq_kiem_ghi()", "master.mtq_ghi_vet()",
    "master.mtq_bootstrap_admin(uuid,uuid,text)",
    "master.mtq_cau_hinh_ghi(uuid,text,jsonb,bigint,text)",
    "master.mtq_quyet_dinh(uuid,uuid,text,text,text,text,text,numeric,uuid,uuid)",
)
# Whitelist nhóm màn hiện có (§4.1), không sinh sáu ô cho màn chưa hỗ trợ.
# Mã lệnh chuẩn MODULE:MAN:HANH_DONG là khóa cho adapter MTQ-4; adapter ánh
# xạ từng lệnh nghiệp vụ thực vào khóa này, không dùng tên route do client gửi.
_CATALOG = (
    ("CRM", "TIEP_NHAN", "XEM LAP SUA KIEM DUYET", "TONG_HOP_DONG"),
    ("CRM", "G1_MAU", "XEM LAP SUA KIEM DUYET", "PHI_TIEN"),
    ("CRM", "G7_CHUAN", "XEM LAP SUA DUYET", "PHI_TIEN"),
    ("CRM", "G2_BAO_GIA", "XEM LAP SUA HUY", "PHI_TIEN"),
    ("CRM", "G3_G4_SOAN_KY", "XEM LAP SUA", "PHI_TIEN"),
    ("CRM", "G5_G6_KIEM_KY", "XEM SUA KIEM DUYET", "TONG_HOP_DONG"),
    ("CRM", "DU_AN_BAN", "XEM LAP SUA", "PHI_TIEN"),
    ("CRM", "TY_GIA", "XEM SUA", "PHI_TIEN"),
    ("CRM", "FILE_SOAT", "XEM", "PHI_TIEN"),
    ("CRM", "BAN_KY", "XEM", "PHI_TIEN"),
    ("M1", "TIEN", "XEM LAP SUA HUY", "PHI_TIEN"),
    ("M1", "XEM_TIEN", "XEM", "PHI_TIEN"),
    ("M2", "HOA_DON", "XEM LAP DUYET HUY", "PHI_TIEN"),
    ("M2", "NGUON_THO", "XEM", "PHI_TIEN"),
    ("M5", "KHO", "XEM LAP DUYET", "PHI_TIEN"),
    ("M5", "NGUON_THO", "XEM", "PHI_TIEN"),
    ("M2", "L11", "XEM LAP DUYET HUY", "PHI_TIEN"),
    ("M5", "L11", "XEM LAP DUYET HUY", "PHI_TIEN"),
    ("M4", "HO_SO", "XEM LAP SUA KIEM HUY", "PHI_TIEN"),
    ("M4", "02A_REVIEW", "XEM SUA KIEM", "PHI_TIEN"),
    ("M4", "02B_CHUNG_TU", "XEM SUA KIEM", "PHI_TIEN"),
    ("M4", "02C_DUYET", "XEM LAP SUA KIEM DUYET", "XIN_THANH_TOAN"),
    ("M4", "PDF_DA_DUYET", "XEM", "PHI_TIEN"),
    ("M4", "03A_KE_TOAN", "XEM SUA KIEM", "PHI_TIEN"),
    ("M4", "03B_DOI_CHIEU", "XEM SUA KIEM", "PHI_TIEN"),
    ("M2", "03B_DOI_CHIEU", "XEM SUA KIEM", "PHI_TIEN"),
    ("M4", "04_REQUEST_NHAP", "XEM LAP KIEM", "PHI_TIEN"),
)

MA_TRAN_THAM_QUYEN_SQL = (
    """CREATE TABLE master.mtq_phong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ma text NOT NULL CHECK (length(btrim(ma)) > 0), ten text NOT NULL CHECK (length(btrim(ten)) > 0),
        hoat_dong boolean NOT NULL DEFAULT true, revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
        UNIQUE (phap_nhan_id, ma), UNIQUE (id, phap_nhan_id))""",
    """CREATE TABLE master.mtq_admin (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        cap_boi uuid NOT NULL REFERENCES master.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES master.nguoi_dung(id), ly_do text NOT NULL,
        revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)))""",
    "CREATE UNIQUE INDEX mtq_admin_hien_hanh ON master.mtq_admin (nguoi_dung_id) WHERE thu_hoi_luc IS NULL",
    """CREATE TABLE master.mtq_danh_muc_hanh_dong (
        catalog_version integer NOT NULL CHECK (catalog_version > 0),
        module text NOT NULL CHECK (module IN ('CRM','M1','M2','M4','M5')),
        man text NOT NULL, hanh_dong text NOT NULL CHECK (hanh_dong IN ('XEM','LAP','SUA','KIEM','DUYET','HUY')),
        lenh_ky_thuat text NOT NULL, loai_doi_tuong text NOT NULL,
        resolver text NOT NULL CHECK (resolver = 'MAY_CHU_MTQ4'),
        loai_tien text NOT NULL CHECK (loai_tien IN ('PHI_TIEN','TONG_HOP_DONG','XIN_THANH_TOAN')),
        PRIMARY KEY (catalog_version, module, man, hanh_dong),
        UNIQUE (catalog_version, lenh_ky_thuat, loai_doi_tuong))""",
    *("INSERT INTO master.mtq_danh_muc_hanh_dong VALUES (1, '%s', '%s', '%s', '%s:%s:%s', '%s', 'MAY_CHU_MTQ4', '%s')"
      % (module, man, action, module, man, action, man, money if action == "DUYET" else "PHI_TIEN")
      for module, man, actions, money in _CATALOG for action in actions.split()),
    """CREATE TABLE master.mtq_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        so_phien_ban integer NOT NULL CHECK (so_phien_ban > 0), revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
        duoc_tao_tu uuid, trang_thai text NOT NULL DEFAULT 'NHAP' CHECK (trang_thai IN ('NHAP','DA_CONG_BO')),
        catalog_version integer NOT NULL DEFAULT 1 CHECK (catalog_version = 1),
        tao_boi uuid NOT NULL REFERENCES master.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        cong_bo_boi uuid REFERENCES master.nguoi_dung(id), cong_bo_luc timestamptz, ly_do text NOT NULL,
        UNIQUE (phap_nhan_id, so_phien_ban), UNIQUE (id, phap_nhan_id), UNIQUE (id, catalog_version),
        FOREIGN KEY (duoc_tao_tu, phap_nhan_id) REFERENCES master.mtq_phien_ban(id, phap_nhan_id),
        CHECK ((trang_thai = 'DA_CONG_BO') = (cong_bo_boi IS NOT NULL AND cong_bo_luc IS NOT NULL)))""",
    """CREATE TABLE master.mtq_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL, phong_id uuid NOT NULL, vai text NOT NULL CHECK (vai IN """ + _VAI + """),
        gioi_han_vnd numeric(20,0) CHECK (gioi_han_vnd IS NULL OR (gioi_han_vnd >= 0 AND gioi_han_vnd < 'Infinity'::numeric)),
        catalog_version integer NOT NULL DEFAULT 1,
        UNIQUE (phien_ban_id, phong_id, vai), UNIQUE (id, catalog_version),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.mtq_phien_ban(id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, catalog_version) REFERENCES master.mtq_phien_ban(id, catalog_version),
        FOREIGN KEY (phong_id, phap_nhan_id) REFERENCES master.mtq_phong(id, phap_nhan_id))""",
    """CREATE TABLE master.mtq_o (
        dong_id uuid NOT NULL, catalog_version integer NOT NULL DEFAULT 1,
        module text NOT NULL, man text NOT NULL, hanh_dong text NOT NULL, cho_phep boolean NOT NULL DEFAULT false,
        PRIMARY KEY (dong_id, module, man, hanh_dong),
        FOREIGN KEY (dong_id, catalog_version) REFERENCES master.mtq_dong(id, catalog_version),
        FOREIGN KEY (catalog_version, module, man, hanh_dong)
            REFERENCES master.mtq_danh_muc_hanh_dong(catalog_version, module, man, hanh_dong))""",
    """CREATE TABLE master.mtq_gan_vai (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL, phong_id uuid NOT NULL, vai text NOT NULL CHECK (vai IN """ + _VAI + """),
        cap_boi uuid NOT NULL REFERENCES master.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES master.nguoi_dung(id), ly_do text NOT NULL,
        revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0), UNIQUE (id, phap_nhan_id),
        FOREIGN KEY (phong_id, phap_nhan_id) REFERENCES master.mtq_phong(id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)))""",
    "CREATE UNIQUE INDEX mtq_vai_hien_hanh ON master.mtq_gan_vai (nguoi_dung_id, phap_nhan_id, phong_id) WHERE thu_hoi_luc IS NULL",
    """CREATE TABLE master.mtq_pham_vi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), gan_vai_id uuid NOT NULL, phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN ('PHAP_NHAN','DU_AN','LOAI_HINH','HOP_DONG','KHACH','NGUON')),
        khoa text NOT NULL, quan_he jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(quan_he) = 'object'),
        cap_boi uuid NOT NULL REFERENCES master.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES master.nguoi_dung(id), ly_do text NOT NULL,
        revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
        FOREIGN KEY (gan_vai_id, phap_nhan_id) REFERENCES master.mtq_gan_vai(id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)))""",
    "CREATE UNIQUE INDEX mtq_pham_vi_hien_hanh ON master.mtq_pham_vi (gan_vai_id, loai, khoa) WHERE thu_hoi_luc IS NULL",
    """CREATE TABLE master.mtq_kich_hoat (
        phap_nhan_id uuid PRIMARY KEY REFERENCES master.phap_nhan(id), bat boolean NOT NULL DEFAULT false,
        phien_ban_id uuid, revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
        bat_boi uuid REFERENCES master.nguoi_dung(id), bat_luc timestamptz,
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.mtq_phien_ban(id, phap_nhan_id),
        CHECK (NOT bat OR (phien_ban_id IS NOT NULL AND bat_boi IS NOT NULL AND bat_luc IS NOT NULL)))""",
    """CREATE TABLE nhat_ky.mtq_thay_doi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL, phap_nhan_id uuid,
        doi_tuong_bang text NOT NULL, doi_tuong jsonb NOT NULL,
        phien_ban_id uuid, revision bigint, loai_su_kien text NOT NULL,
        truoc jsonb, sau jsonb, actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id), actor_login text NOT NULL,
        luc timestamptz NOT NULL DEFAULT clock_timestamp(), ly_do text NOT NULL, boi_csdl text NOT NULL DEFAULT session_user)""",
    """CREATE TABLE nhat_ky.mtq_tu_choi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL, actor_id uuid, actor_login text,
        phap_nhan_id uuid, phong_id uuid, vai text, phien_ban_id uuid, revision bigint,
        gan_vai_id uuid, gan_vai_revision bigint, pham_vi_id uuid, pham_vi_revision bigint,
        module text, man text, hanh_dong text, lenh_ky_thuat text, doi_tuong text,
        ma text NOT NULL, ly_do text NOT NULL, gioi_han_vnd numeric(20,0), so_tien_vnd numeric,
        luc timestamptz NOT NULL DEFAULT clock_timestamp())""",
    """CREATE FUNCTION master.mtq_la_admin() RETURNS boolean LANGUAGE sql STABLE
        SET search_path = pg_catalog, master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.mtq_admin a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
            WHERE a.thu_hoi_luc IS NULL AND n.dang_nhap = master.ktt_danh_tinh()) $$""",
    # Khóa cứng readiness trong MTQ-1. Không có tham số JSON/GUC để tự bật.
    """CREATE FUNCTION master.mtq_san_sang(p_pn uuid) RETURNS boolean LANGUAGE sql IMMUTABLE
        SET search_path = pg_catalog, master, pg_temp AS $$ SELECT false $$""",
    """CREATE FUNCTION master.mtq_bat_bien() RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, master, pg_temp AS $$
        BEGIN RAISE EXCEPTION 'MTQ_BAT_BIEN: không sửa/xóa/truncate lịch sử hoặc catalog'; END $$""",
    """CREATE FUNCTION master.mtq_kiem_ghi() RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, master, pg_temp AS $$
        DECLARE v jsonb; cu jsonb; pb uuid; g record; bootstrap boolean;
        BEGIN
            -- Khóa toàn cấu hình MTQ, không phụ thuộc thứ tự khóa PN/phòng.
            PERFORM pg_advisory_xact_lock(742601, 1);
            IF TG_OP IN ('DELETE','TRUNCATE') THEN
                RAISE EXCEPTION 'MTQ_BAT_BIEN: chỉ thêm/cập nhật có lịch sử';
            END IF;
            v := to_jsonb(NEW);
            IF TG_OP = 'UPDATE' THEN cu := to_jsonb(OLD); END IF;
            bootstrap := TG_TABLE_NAME = 'mtq_admin' AND TG_OP = 'INSERT'
                AND NOT EXISTS (SELECT 1 FROM master.mtq_admin)
                AND pg_has_role(session_user, (SELECT relowner FROM pg_class WHERE oid = TG_RELID), 'MEMBER');
            IF NOT bootstrap AND NOT master.mtq_la_admin() THEN
                RAISE EXCEPTION 'MTQ_CHI_ADMIN: chỉ Admin hoạt động được ghi cấu hình';
            END IF;
            IF nullif(btrim(current_setting('ktt.mtq_ly_do', true)), '') IS NULL
                OR nullif(current_setting('ktt.mtq_request', true), '') IS NULL THEN
                RAISE EXCEPTION 'MTQ_CAN_LY_DO: cần request ID và lý do';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF (v - ARRAY['revision','ten','hoat_dong','gioi_han_vnd','cho_phep','trang_thai',
                    'cong_bo_boi','cong_bo_luc','thu_hoi_luc','thu_hoi_boi','bat','phien_ban_id','bat_boi','bat_luc','ly_do'])
                    IS DISTINCT FROM
                   (cu - ARRAY['revision','ten','hoat_dong','gioi_han_vnd','cho_phep','trang_thai',
                    'cong_bo_boi','cong_bo_luc','thu_hoi_luc','thu_hoi_boi','bat','phien_ban_id','bat_boi','bat_luc','ly_do']) THEN
                    RAISE EXCEPTION 'MTQ_BAT_BIEN: không đổi khóa/phạm vi/danh tính đã cấp';
                END IF;
                IF TG_TABLE_NAME <> 'mtq_kich_hoat' AND
                    v->'phien_ban_id' IS DISTINCT FROM cu->'phien_ban_id' THEN
                    RAISE EXCEPTION 'MTQ_BAT_BIEN: không chuyển dòng sang snapshot khác';
                END IF;
                IF v ? 'revision' AND (v->>'revision')::bigint <> (cu->>'revision')::bigint + 1 THEN
                    RAISE EXCEPTION 'MTQ_REVISION: revision phải tăng một';
                END IF;
                IF TG_TABLE_NAME IN ('mtq_admin','mtq_gan_vai','mtq_pham_vi') AND
                    (cu->>'thu_hoi_luc' IS NOT NULL OR v->>'thu_hoi_luc' IS NULL) THEN
                    RAISE EXCEPTION 'MTQ_BAT_BIEN: chỉ thu hồi một lần, cấp lại bằng bản ghi mới';
                END IF;
            END IF;
            IF TG_TABLE_NAME = 'mtq_phien_ban' THEN
                IF TG_OP = 'UPDATE' AND OLD.trang_thai = 'DA_CONG_BO' THEN
                    RAISE EXCEPTION 'MTQ_BAT_BIEN: snapshot công bố';
                END IF;
                IF NEW.trang_thai = 'DA_CONG_BO' THEN
                    IF TG_OP <> 'UPDATE' OR EXISTS (
                        SELECT 1 FROM master.mtq_phong p WHERE p.phap_nhan_id = NEW.phap_nhan_id AND p.hoat_dong
                        AND (SELECT count(*) FROM master.mtq_dong d WHERE d.phien_ban_id = NEW.id AND d.phong_id = p.id) <> 5)
                        OR NOT EXISTS (SELECT 1 FROM master.mtq_phong p WHERE p.phap_nhan_id = NEW.phap_nhan_id AND p.hoat_dong) THEN
                        RAISE EXCEPTION 'MTQ_THIEU_DONG: mỗi phòng hoạt động cần đủ năm dòng';
                    END IF;
                END IF;
            ELSIF TG_TABLE_NAME IN ('mtq_dong','mtq_o') THEN
                IF TG_TABLE_NAME = 'mtq_o' THEN
                    SELECT phien_ban_id INTO pb FROM master.mtq_dong WHERE id = NEW.dong_id;
                ELSE pb := (v->>'phien_ban_id')::uuid; END IF;
                IF EXISTS (SELECT 1 FROM master.mtq_phien_ban WHERE id = pb AND trang_thai = 'DA_CONG_BO') THEN
                    RAISE EXCEPTION 'MTQ_BAT_BIEN: dòng/ô của snapshot công bố';
                END IF;
            ELSIF TG_TABLE_NAME = 'mtq_pham_vi' THEN
                SELECT * INTO g FROM master.mtq_gan_vai WHERE id = NEW.gan_vai_id;
                IF TG_OP = 'INSERT' AND (g.id IS NULL OR g.thu_hoi_luc IS NOT NULL) THEN
                    RAISE EXCEPTION 'MTQ_PHAM_VI: gán vai đã thu hồi/không tồn tại';
                END IF;
                IF NEW.loai = 'PHAP_NHAN' THEN
                    IF NEW.khoa <> NEW.phap_nhan_id::text THEN RAISE EXCEPTION 'MTQ_PHAM_VI: sai pháp nhân'; END IF;
                ELSIF NEW.loai = 'DU_AN' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.du_an WHERE id::text = NEW.khoa AND phap_nhan_id = NEW.phap_nhan_id) THEN
                        RAISE EXCEPTION 'MTQ_PHAM_VI: dự án khác pháp nhân';
                    END IF;
                ELSIF NEW.loai = 'LOAI_HINH' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.loai_hinh_doanh_thu WHERE id::text = NEW.khoa AND phap_nhan_id = NEW.phap_nhan_id) THEN
                        RAISE EXCEPTION 'MTQ_PHAM_VI: loại hình khác pháp nhân';
                    END IF;
                ELSIF NEW.loai = 'HOP_DONG' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.hop_dong WHERE id::text = NEW.khoa AND phap_nhan_id = NEW.phap_nhan_id) THEN
                        RAISE EXCEPTION 'MTQ_PHAM_VI: hợp đồng khác pháp nhân';
                    END IF;
                ELSIF NEW.loai = 'KHACH' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.doi_tac dt WHERE dt.id::text = NEW.khoa
                        AND (dt.phap_nhan_id = NEW.phap_nhan_id OR (dt.phap_nhan_id IS NULL AND EXISTS (
                            SELECT 1 FROM master.hop_dong hd WHERE hd.doi_tac_id = dt.id AND hd.phap_nhan_id = NEW.phap_nhan_id)))) THEN
                        RAISE EXCEPTION 'MTQ_PHAM_VI: khách chưa có quan hệ với pháp nhân';
                    END IF;
                ELSE
                    -- NGUON cần instance/profile SHA/công ty nguồn được resolver
                    -- MTQ-4i xác minh; tuyệt đối không kế thừa capability cũ.
                    RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: phạm vi nguồn chưa được hỗ trợ';
                END IF;
            ELSIF TG_TABLE_NAME = 'mtq_admin' AND TG_OP = 'UPDATE' THEN
                IF NOT EXISTS (SELECT 1 FROM master.mtq_admin a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
                    WHERE a.id <> NEW.id AND a.thu_hoi_luc IS NULL AND n.trang_thai = 'HOAT_DONG') THEN
                    RAISE EXCEPTION 'MTQ_ADMIN_CUOI: không được thu hồi Admin hoạt động cuối';
                END IF;
            ELSIF TG_TABLE_NAME = 'mtq_kich_hoat' THEN
                IF NEW.bat THEN
                    IF NOT master.mtq_san_sang(NEW.phap_nhan_id) THEN
                        RAISE EXCEPTION 'MTQ_CHUA_NOI_MTQ4: chưa đủ đường kiểm quyền để bật';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM master.mtq_phien_ban WHERE id = NEW.phien_ban_id
                        AND phap_nhan_id = NEW.phap_nhan_id AND trang_thai = 'DA_CONG_BO') THEN
                        RAISE EXCEPTION 'MTQ_CON_TRO_SAI: phải trỏ snapshot công bố đúng pháp nhân';
                    END IF;
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE FUNCTION master.mtq_ghi_vet() RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE moi jsonb := to_jsonb(NEW); cu jsonb; ai uuid; login text; pb uuid; pn uuid; rev bigint;
        BEGIN
            IF TG_OP = 'UPDATE' THEN cu := to_jsonb(OLD); END IF;
            login := master.ktt_danh_tinh();
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login;
            IF TG_TABLE_NAME = 'mtq_admin' AND ai IS NULL THEN
                ai := NEW.nguoi_dung_id;
                SELECT dang_nhap INTO login FROM master.nguoi_dung WHERE id = ai;
            END IF;
            pn := (moi->>'phap_nhan_id')::uuid;
            pb := (moi->>'phien_ban_id')::uuid;
            IF TG_TABLE_NAME = 'mtq_phien_ban' THEN pb := NEW.id; END IF;
            IF TG_TABLE_NAME = 'mtq_o' THEN
                SELECT d.phap_nhan_id, d.phien_ban_id INTO pn, pb FROM master.mtq_dong d WHERE d.id = NEW.dong_id;
            END IF;
            rev := (moi->>'revision')::bigint;
            IF pb IS NOT NULL THEN SELECT revision INTO rev FROM master.mtq_phien_ban WHERE id = pb; END IF;
            INSERT INTO nhat_ky.mtq_thay_doi (request_id, phap_nhan_id, doi_tuong_bang, doi_tuong,
                phien_ban_id, revision, loai_su_kien, truoc, sau, actor_id, actor_login, ly_do)
            VALUES (current_setting('ktt.mtq_request')::uuid, pn, TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                jsonb_strip_nulls(jsonb_build_object('id', moi->'id', 'dong_id', moi->'dong_id',
                    'module', moi->'module', 'man', moi->'man', 'hanh_dong', moi->'hanh_dong', 'phap_nhan_id', pn)),
                pb, rev, current_setting('ktt.mtq_lenh'), cu, moi, ai, login, current_setting('ktt.mtq_ly_do'));
            RETURN NEW;
        END $$""",
    *(f"CREATE TRIGGER mtq_kiem_ghi BEFORE INSERT OR UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION master.mtq_kiem_ghi()"
      for t in _BANG if t.startswith("master.") and t != "master.mtq_danh_muc_hanh_dong"),
    *(f"CREATE TRIGGER mtq_ghi_vet AFTER INSERT OR UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION master.mtq_ghi_vet()"
      for t in _BANG if t.startswith("master.") and t != "master.mtq_danh_muc_hanh_dong"),
    "CREATE TRIGGER mtq_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.mtq_danh_muc_hanh_dong FOR EACH ROW EXECUTE FUNCTION master.mtq_bat_bien()",
    *(f"CREATE TRIGGER mtq_bat_bien BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION master.mtq_bat_bien()"
      for t in ("nhat_ky.mtq_thay_doi", "nhat_ky.mtq_tu_choi")),
    *(f"CREATE TRIGGER mtq_chan_truncate BEFORE TRUNCATE ON {t} FOR EACH STATEMENT EXECUTE FUNCTION master.mtq_bat_bien()" for t in _BANG),
    """CREATE FUNCTION master.mtq_bootstrap_admin(p_nguoi uuid, p_request uuid, p_ly_do text) RETURNS uuid
        LANGUAGE plpgsql SET search_path = pg_catalog, master, pg_temp AS $$
        DECLARE k uuid;
        BEGIN
            PERFORM pg_advisory_xact_lock(742601, 1);
            IF NOT pg_has_role(session_user, (SELECT relowner FROM pg_class WHERE oid = 'master.mtq_admin'::regclass), 'MEMBER')
                OR EXISTS (SELECT 1 FROM master.mtq_admin) THEN
                RAISE EXCEPTION 'MTQ_BOOTSTRAP: chỉ chủ bảng tin cậy, duy nhất lần đầu';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE id = p_nguoi AND trang_thai = 'HOAT_DONG') THEN
                RAISE EXCEPTION 'MTQ_DANH_TINH: cần người dùng hoạt động chỉ định rõ';
            END IF;
            PERFORM set_config('ktt.mtq_request', p_request::text, true), set_config('ktt.mtq_ly_do', p_ly_do, true),
                set_config('ktt.mtq_lenh', 'BOOTSTRAP_ADMIN', true);
            INSERT INTO master.mtq_admin (nguoi_dung_id, cap_boi, ly_do) VALUES (p_nguoi, p_nguoi, p_ly_do) RETURNING id INTO k;
            RETURN k;
        END $$""",
    """CREATE FUNCTION master.mtq_cau_hinh_ghi(p_request uuid, p_lenh text, p_data jsonb, p_expected_revision bigint, p_ly_do text)
        RETURNS jsonb LANGUAGE plpgsql SET search_path = pg_catalog, master, pg_temp AS $$
        DECLARE ai uuid; k uuid := (p_data->>'id')::uuid; pn uuid := (p_data->>'phap_nhan_id')::uuid;
            pb uuid := (p_data->>'phien_ban_id')::uuid; v master.mtq_phien_ban; r jsonb; n bigint; d record;
        BEGIN
            PERFORM pg_advisory_xact_lock(742601, 1);
            IF NOT master.mtq_la_admin() THEN RAISE EXCEPTION 'MTQ_CHI_ADMIN: chỉ Admin hoạt động'; END IF;
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = master.ktt_danh_tinh();
            IF p_request IS NULL OR nullif(btrim(p_ly_do), '') IS NULL OR jsonb_typeof(p_data) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'MTQ_DAU_VAO: cần request, lý do và object cấu hình';
            END IF;
            PERFORM set_config('ktt.mtq_request', p_request::text, true), set_config('ktt.mtq_ly_do', p_ly_do, true),
                set_config('ktt.mtq_lenh', p_lenh, true);
            IF p_lenh = 'NHAP' THEN
                IF p_expected_revision IS DISTINCT FROM 0::bigint THEN RAISE EXCEPTION 'MTQ_REVISION: tạo mới cần revision 0'; END IF;
                IF pb IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.mtq_phien_ban WHERE id = pb AND phap_nhan_id = pn AND trang_thai = 'DA_CONG_BO') THEN
                    RAISE EXCEPTION 'MTQ_BAN_NGUON: chỉ sao chép snapshot công bố cùng pháp nhân';
                END IF;
                INSERT INTO master.mtq_phien_ban (phap_nhan_id, so_phien_ban, duoc_tao_tu, tao_boi, ly_do)
                    SELECT pn, coalesce(max(so_phien_ban), 0) + 1, pb, ai, p_ly_do FROM master.mtq_phien_ban WHERE phap_nhan_id = pn
                    RETURNING * INTO v;
                FOR d IN SELECT * FROM master.mtq_dong WHERE phien_ban_id = pb LOOP
                    INSERT INTO master.mtq_dong (phien_ban_id, phap_nhan_id, phong_id, vai, gioi_han_vnd)
                        VALUES (v.id, pn, d.phong_id, d.vai, d.gioi_han_vnd) RETURNING id INTO k;
                    INSERT INTO master.mtq_o SELECT k, catalog_version, module, man, hanh_dong, cho_phep FROM master.mtq_o WHERE dong_id = d.id;
                END LOOP;
                RETURN to_jsonb(v);
            ELSIF p_lenh IN ('DONG','O','CONG_BO') THEN
                SELECT * INTO v FROM master.mtq_phien_ban WHERE id = pb FOR UPDATE;
                IF v.id IS NULL OR v.trang_thai <> 'NHAP' OR v.revision IS DISTINCT FROM p_expected_revision THEN
                    RAISE EXCEPTION 'MTQ_REVISION: bản nháp không còn đúng revision';
                END IF;
                IF p_lenh <> 'CONG_BO' THEN
                    UPDATE master.mtq_phien_ban SET revision = revision + 1 WHERE id = pb RETURNING * INTO v;
                END IF;
                IF p_lenh = 'DONG' THEN
                    IF p_data->>'gioi_han_vnd' IS NOT NULL AND
                        (p_data->>'gioi_han_vnd') !~ '^[0-9]{1,20}$' THEN RAISE EXCEPTION 'MTQ_TIEN: VND phải nguyên không âm'; END IF;
                    INSERT INTO master.mtq_dong (phien_ban_id, phap_nhan_id, phong_id, vai, gioi_han_vnd)
                        VALUES (pb, v.phap_nhan_id, (p_data->>'phong_id')::uuid, p_data->>'vai', (p_data->>'gioi_han_vnd')::numeric)
                        ON CONFLICT (phien_ban_id, phong_id, vai) DO UPDATE SET gioi_han_vnd = EXCLUDED.gioi_han_vnd RETURNING to_jsonb(mtq_dong.*) INTO r;
                ELSIF p_lenh = 'O' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.mtq_dong WHERE id = (p_data->>'dong_id')::uuid AND phien_ban_id = pb)
                        OR jsonb_typeof(p_data->'cho_phep') IS DISTINCT FROM 'boolean' THEN RAISE EXCEPTION 'MTQ_O_SAI: ô phải thuộc bản nháp, giá trị boolean'; END IF;
                    INSERT INTO master.mtq_o (dong_id, module, man, hanh_dong, cho_phep)
                        VALUES ((p_data->>'dong_id')::uuid, p_data->>'module', p_data->>'man', p_data->>'hanh_dong', (p_data->>'cho_phep')::boolean)
                        ON CONFLICT (dong_id, module, man, hanh_dong) DO UPDATE SET cho_phep = EXCLUDED.cho_phep RETURNING to_jsonb(mtq_o.*) INTO r;
                ELSE
                    UPDATE master.mtq_phien_ban SET trang_thai = 'DA_CONG_BO', cong_bo_boi = ai, cong_bo_luc = clock_timestamp(),
                        revision = revision + 1 WHERE id = pb RETURNING * INTO v;
                    r := to_jsonb(v);
                END IF;
                RETURN jsonb_build_object('phien_ban', to_jsonb(v), 'doi_tuong', r);
            ELSIF p_lenh = 'PHONG' THEN
                IF k IS NULL THEN
                    IF p_expected_revision IS DISTINCT FROM 0::bigint THEN RAISE EXCEPTION 'MTQ_REVISION'; END IF;
                    INSERT INTO master.mtq_phong (phap_nhan_id, ma, ten) VALUES (pn, p_data->>'ma', p_data->>'ten') RETURNING to_jsonb(mtq_phong.*) INTO r;
                ELSE
                    UPDATE master.mtq_phong SET ten = coalesce(p_data->>'ten', ten), hoat_dong = coalesce((p_data->>'hoat_dong')::boolean, hoat_dong),
                        revision = revision + 1 WHERE id = k AND revision = p_expected_revision RETURNING to_jsonb(mtq_phong.*) INTO r;
                END IF;
            ELSIF p_lenh IN ('ADMIN','GAN_VAI','PHAM_VI') THEN
                IF p_expected_revision IS DISTINCT FROM 0::bigint THEN RAISE EXCEPTION 'MTQ_REVISION'; END IF;
                IF p_lenh = 'ADMIN' THEN
                    IF NOT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE id = (p_data->>'nguoi_dung_id')::uuid AND trang_thai = 'HOAT_DONG') THEN
                        RAISE EXCEPTION 'MTQ_DANH_TINH'; END IF;
                    INSERT INTO master.mtq_admin (nguoi_dung_id, cap_boi, ly_do)
                        VALUES ((p_data->>'nguoi_dung_id')::uuid, ai, p_ly_do) RETURNING to_jsonb(mtq_admin.*) INTO r;
                ELSIF p_lenh = 'GAN_VAI' THEN
                    INSERT INTO master.mtq_gan_vai (nguoi_dung_id, phap_nhan_id, phong_id, vai, cap_boi, ly_do)
                        VALUES ((p_data->>'nguoi_dung_id')::uuid, pn, (p_data->>'phong_id')::uuid, p_data->>'vai', ai, p_ly_do) RETURNING to_jsonb(mtq_gan_vai.*) INTO r;
                ELSE
                    INSERT INTO master.mtq_pham_vi (gan_vai_id, phap_nhan_id, loai, khoa, quan_he, cap_boi, ly_do)
                        VALUES ((p_data->>'gan_vai_id')::uuid, pn, p_data->>'loai', p_data->>'khoa', coalesce(p_data->'quan_he', '{}'::jsonb), ai, p_ly_do)
                        RETURNING to_jsonb(mtq_pham_vi.*) INTO r;
                END IF;
            ELSIF p_lenh IN ('THU_HOI_ADMIN','THU_HOI_VAI','THU_HOI_PHAM_VI') THEN
                IF p_lenh = 'THU_HOI_ADMIN' THEN
                    UPDATE master.mtq_admin SET thu_hoi_luc = clock_timestamp(), thu_hoi_boi = ai, ly_do = p_ly_do, revision = revision + 1
                        WHERE id = k AND revision = p_expected_revision AND thu_hoi_luc IS NULL RETURNING to_jsonb(mtq_admin.*) INTO r;
                ELSIF p_lenh = 'THU_HOI_VAI' THEN
                    UPDATE master.mtq_gan_vai SET thu_hoi_luc = clock_timestamp(), thu_hoi_boi = ai, ly_do = p_ly_do, revision = revision + 1
                        WHERE id = k AND revision = p_expected_revision AND thu_hoi_luc IS NULL RETURNING to_jsonb(mtq_gan_vai.*) INTO r;
                ELSE
                    UPDATE master.mtq_pham_vi SET thu_hoi_luc = clock_timestamp(), thu_hoi_boi = ai, ly_do = p_ly_do, revision = revision + 1
                        WHERE id = k AND revision = p_expected_revision AND thu_hoi_luc IS NULL RETURNING to_jsonb(mtq_pham_vi.*) INTO r;
                END IF;
            ELSIF p_lenh = 'KICH_HOAT' THEN
                IF jsonb_typeof(p_data->'bat') IS DISTINCT FROM 'boolean' THEN RAISE EXCEPTION 'MTQ_DAU_VAO: bat phải boolean'; END IF;
                SELECT revision INTO n FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn FOR UPDATE;
                IF coalesce(n, 0) IS DISTINCT FROM p_expected_revision THEN RAISE EXCEPTION 'MTQ_REVISION'; END IF;
                INSERT INTO master.mtq_kich_hoat (phap_nhan_id, bat, phien_ban_id, bat_boi, bat_luc)
                    VALUES (pn, (p_data->>'bat')::boolean, pb, ai, clock_timestamp())
                    ON CONFLICT (phap_nhan_id) DO UPDATE SET bat = EXCLUDED.bat, phien_ban_id = EXCLUDED.phien_ban_id,
                        bat_boi = ai, bat_luc = clock_timestamp(), revision = mtq_kich_hoat.revision + 1 RETURNING to_jsonb(mtq_kich_hoat.*) INTO r;
            ELSE RAISE EXCEPTION 'MTQ_LENH: lệnh cấu hình không được hỗ trợ'; END IF;
            IF r IS NULL THEN RAISE EXCEPTION 'MTQ_REVISION: đối tượng không tồn tại hoặc revision cũ'; END IF;
            RETURN r;
        END $$""",
    # p_pn/phong/loai/đối tượng/khóa phạm vi/tiền là kết quả resolver tin cậy tại máy
    # chủ, không truyền body client. Không có EXECUTE cho vai app/PUBLIC.
    # NULL cho_phep + nguon=CU nghĩa là KHÔNG CAN THIỆP, không phải cho phép.
    """CREATE FUNCTION master.mtq_quyet_dinh(p_pn uuid, p_phong uuid, p_lenh text, p_loai text,
        p_doi_tuong text, p_khoa text, p_scope_loai text, p_tien_vnd numeric, p_scope uuid, p_request uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; login text := master.ktt_danh_tinh(); kh master.mtq_kich_hoat; v master.mtq_phien_ban;
            g master.mtq_gan_vai; s master.mtq_pham_vi; d master.mtq_dong; c master.mtq_danh_muc_hanh_dong;
            ma text; ly_do text; kq jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login;
            SELECT * INTO kh FROM master.mtq_kich_hoat WHERE phap_nhan_id = p_pn;
            IF ai IS NULL THEN ma := 'MTQ_DANH_TINH'; ly_do := 'Danh tính phiên ID/login không khớp người hoạt động';
            ELSIF p_pn IS NULL OR NOT EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = p_pn) THEN
                ma := 'MTQ_PHAP_NHAN'; ly_do := 'Không xác định được pháp nhân';
            ELSIF NOT coalesce(kh.bat, false) THEN
                RETURN jsonb_build_object('nguon', 'CU', 'can_thiep', false, 'cho_phep', NULL, 'ma', 'MTQ_TAT', 'ly_do', 'Giữ đường kiểm quyền cũ');
            ELSE
                SELECT * INTO v FROM master.mtq_phien_ban WHERE id = kh.phien_ban_id AND phap_nhan_id = p_pn AND trang_thai = 'DA_CONG_BO';
                SELECT * INTO c FROM master.mtq_danh_muc_hanh_dong WHERE catalog_version = v.catalog_version AND lenh_ky_thuat = p_lenh AND loai_doi_tuong = p_loai;
                SELECT * INTO g FROM master.mtq_gan_vai WHERE nguoi_dung_id = ai AND phap_nhan_id = p_pn AND phong_id = p_phong AND thu_hoi_luc IS NULL;
                SELECT * INTO s FROM master.mtq_pham_vi WHERE id = p_scope AND gan_vai_id = g.id AND phap_nhan_id = p_pn AND thu_hoi_luc IS NULL;
                SELECT * INTO d FROM master.mtq_dong WHERE phien_ban_id = v.id AND phap_nhan_id = p_pn AND phong_id = p_phong AND vai = g.vai;
                IF v.id IS NULL THEN ma := 'MTQ_CON_TRO_SAI'; ly_do := 'Thiếu snapshot công bố hiệu lực';
                ELSIF c.module IS NULL THEN ma := 'MTQ_HANH_DONG'; ly_do := 'Hành động/đối tượng chưa có trong catalog';
                ELSIF g.id IS NULL OR NOT EXISTS (SELECT 1 FROM master.mtq_phong WHERE id = p_phong AND phap_nhan_id = p_pn AND hoat_dong) THEN
                    ma := 'MTQ_GAN_VAI'; ly_do := 'Chưa có vai tại đúng phòng/pháp nhân';
                ELSIF nullif(btrim(p_doi_tuong), '') IS NULL OR s.id IS NULL
                    OR s.loai IS DISTINCT FROM p_scope_loai OR s.khoa IS DISTINCT FROM p_khoa THEN
                    ma := 'MTQ_PHAM_VI'; ly_do := 'Đối tượng ngoài phạm vi được cấp';
                ELSIF d.id IS NULL OR NOT EXISTS (SELECT 1 FROM master.mtq_o WHERE dong_id = d.id AND module = c.module AND man = c.man AND hanh_dong = c.hanh_dong AND cho_phep) THEN
                    ma := 'MTQ_CHUA_TICK'; ly_do := 'Ô quyền chưa được tick';
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND
                    (p_tien_vnd IS NULL OR p_tien_vnd < 0 OR p_tien_vnd >= 'Infinity'::numeric OR p_tien_vnd <> trunc(p_tien_vnd)) THEN
                    ma := 'MTQ_THIEU_TIEN'; ly_do := 'Cần số tiền VND nguyên không âm từ hồ sơ/tỷ giá đã ghim';
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND d.gioi_han_vnd IS NOT NULL AND p_tien_vnd > d.gioi_han_vnd THEN
                    ma := 'MTQ_VUOT_HAN_MUC'; ly_do := 'Số tiền duyệt vượt giới hạn tiền VND của dòng';
                ELSE ma := 'MTQ_CHO_PHEP'; ly_do := 'Đúng ô tick, phòng, pháp nhân, phạm vi và hạn mức'; END IF;
            END IF;
            kq := jsonb_build_object('nguon', 'MA_TRAN', 'can_thiep', true, 'cho_phep', ma = 'MTQ_CHO_PHEP', 'ma', ma, 'ly_do', ly_do,
                'phien_ban_id', v.id, 'revision', v.revision, 'kich_hoat_revision', kh.revision,
                'gan_vai_id', g.id, 'gan_vai_revision', g.revision, 'pham_vi_id', s.id, 'pham_vi_revision', s.revision,
                'dong_id', d.id, 'module', c.module, 'man', c.man, 'hanh_dong', c.hanh_dong,
                'doi_tuong', p_doi_tuong, 'gioi_han_vnd', d.gioi_han_vnd, 'so_tien_vnd', p_tien_vnd);
            IF ma <> 'MTQ_CHO_PHEP' THEN
                INSERT INTO nhat_ky.mtq_tu_choi (request_id, actor_id, actor_login, phap_nhan_id, phong_id, vai, phien_ban_id, revision,
                    gan_vai_id, gan_vai_revision, pham_vi_id, pham_vi_revision, module, man, hanh_dong, lenh_ky_thuat, doi_tuong, ma, ly_do, gioi_han_vnd, so_tien_vnd)
                VALUES (coalesce(p_request, gen_random_uuid()), ai, login, p_pn, p_phong, g.vai, v.id, v.revision,
                    g.id, g.revision, s.id, s.revision, c.module, c.man, c.hanh_dong, p_lenh, p_doi_tuong, ma, ly_do, d.gioi_han_vnd, p_tien_vnd);
            END IF;
            -- Audit ở cùng giao dịch; MTQ-2 ghi bền từ chối sau rollback nghiệp vụ.
            RETURN kq;
        END $$""",
    *(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in _BANG),
    "REVOKE ALL ON " + ", ".join(_BANG) + " FROM PUBLIC",
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(_HAM) + " FROM PUBLIC",
    """DO $$ DECLARE r text;
        BEGIN
            FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE ALL ON """ + ", ".join(_BANG) + """ FROM %I', r);
                    EXECUTE format('REVOKE EXECUTE ON FUNCTION """ + ", ".join(_HAM) + """ FROM %I', r);
                END IF;
            END LOOP;
        END $$""",
)
