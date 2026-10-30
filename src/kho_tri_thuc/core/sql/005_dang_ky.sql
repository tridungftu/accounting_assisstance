-- G2-05: registry giao dien, khong phu thuoc DDL cua module tuy chon.
-- Ap qua doi_cau_truc.py sau 004; caller quan ly transaction. Khong DROP.
-- G2-24/25 kiem goi/manifest truoc khi goi cua cai dat nay.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    vai_chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    vai_chay constant text := tien_to || 'vai_chay_loi';
    login_loi constant text := tien_to || 'dang_nhap_loi';
    login_cai_dat constant text := tien_to || 'dang_nhap_cai_dat';
    vai_truoc constant text := current_setting('role');
    duong_tim_truoc constant text := current_setting('search_path');
    cac_bang constant text[] := ARRAY['module_danh_muc', 'phien_ban_module',
        'engine_dinh_nghia', 'dang_ky_ham_module', 'dang_ky_contract', 'module_dung_contract'];
    ten_bang text;
    ham record;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63
       OR (tien_to <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-05: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_namespace WHERE nspname = 'loi'
                   AND pg_catalog.pg_get_userbyid(nspowner) = vai_chu)
       OR pg_catalog.to_regclass('loi.nhat_ky_kiem_toan') IS NULL
       OR pg_catalog.to_regprocedure('loi.xac_minh_phien(text,text,uuid,text,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-05: Can lead, ap G2-01..04 truoc';
    END IF;
    FOREACH ten_bang IN ARRAY cac_bang LOOP
        IF EXISTS (SELECT FROM pg_catalog.pg_class
                   WHERE oid = pg_catalog.to_regclass('loi.' || ten_bang)
                     AND (pg_catalog.pg_get_userbyid(relowner) <> vai_chu OR relkind <> 'r')) THEN
            RAISE EXCEPTION 'G2-05: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);

    CREATE TABLE IF NOT EXISTS loi.module_danh_muc (
        ma text PRIMARY KEY CHECK (ma ~ '^[a-z][a-z0-9_]{0,30}$'),
        id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
        ten text NOT NULL CHECK (btrim(ten) <> ''),
        loai text NOT NULL CHECK (loai IN ('CORE', 'MODULE')),
        ten_schema text UNIQUE,
        vai_so_huu name,
        CHECK ((loai = 'CORE' AND ma = 'core' AND ten_schema IS NULL AND vai_so_huu IS NULL)
            OR (loai = 'MODULE' AND ma <> 'core' AND ten_schema = 'mod_' || ma
                AND vai_so_huu IS NOT NULL))
    );
    CREATE TABLE IF NOT EXISTS loi.phien_ban_module (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        so_phien_ban text NOT NULL CHECK (btrim(so_phien_ban) <> ''),
        ma_bam_goi text NOT NULL CHECK (ma_bam_goi ~ '^[0-9a-f]{64}$'),
        tuong_thich jsonb NOT NULL CHECK (jsonb_typeof(tuong_thich) = 'object'),
        trang_thai text NOT NULL DEFAULT 'chua_cai' CHECK (trang_thai IN ('chua_cai', 'da_cai')),
        UNIQUE (module, so_phien_ban),
        UNIQUE (module, so_phien_ban, ma_bam_goi)
    );
    CREATE TABLE IF NOT EXISTS loi.engine_dinh_nghia (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ma text NOT NULL CHECK (ma ~ '^[a-z][a-z0-9_]{0,30}$'),
        ten text NOT NULL CHECK (btrim(ten) <> ''),
        so_phien_ban text NOT NULL CHECK (btrim(so_phien_ban) <> ''),
        ma_bam_goi text NOT NULL CHECK (ma_bam_goi ~ '^[0-9a-f]{64}$'),
        ma_adapter text NOT NULL CHECK (btrim(ma_adapter) <> ''),
        phien_ban_adapter text NOT NULL CHECK (btrim(phien_ban_adapter) <> ''),
        nang_luc jsonb NOT NULL CHECK (jsonb_typeof(nang_luc) = 'array' AND jsonb_array_length(nang_luc) > 0),
        gioi_han jsonb NOT NULL CHECK (jsonb_typeof(gioi_han) = 'object'),
        UNIQUE (ma, so_phien_ban)
    );
    CREATE TABLE IF NOT EXISTS loi.dang_ky_contract (
        ma text NOT NULL CHECK (ma ~ '^[a-z][a-z0-9_.]{0,95}$'),
        phien_ban text NOT NULL CHECK (btrim(phien_ban) <> ''),
        id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
        module_so_huu text NOT NULL REFERENCES loi.module_danh_muc(ma),
        lop text NOT NULL CHECK (lop IN ('ky_thuat', 'nghiep_vu')),
        muc_dich text NOT NULL CHECK (btrim(muc_dich) <> ''),
        sieu_du_lieu jsonb NOT NULL CHECK (jsonb_typeof(sieu_du_lieu) = 'object'),
        luoc_do jsonb NOT NULL CHECK (jsonb_typeof(luoc_do) = 'object'),
        ma_bam text NOT NULL CHECK (ma_bam ~ '^[0-9a-f]{64}$'),
        trang_thai text NOT NULL DEFAULT 'nhap' CHECK (trang_thai IN ('nhap', 'anh_duyet', 'dang_dung', 'ngung')),
        bang_chung_duyet text,
        duyet_luc timestamptz,
        sap_ngung_luc timestamptz,
        PRIMARY KEY (ma, phien_ban),
        CHECK ((lop = 'ky_thuat' AND module_so_huu = 'core')
            OR (lop = 'nghiep_vu' AND module_so_huu <> 'core'))
    );
    -- Binding tach thanh dong co FK, giu ca ban module tam tat/ban viec con ghim.
    CREATE TABLE IF NOT EXISTS loi.module_dung_contract (
        id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
        ma_contract text NOT NULL,
        phien_ban_contract text NOT NULL,
        module text NOT NULL,
        phien_ban_module text NOT NULL,
        PRIMARY KEY (ma_contract, phien_ban_contract, module, phien_ban_module),
        FOREIGN KEY (ma_contract, phien_ban_contract) REFERENCES loi.dang_ky_contract(ma, phien_ban),
        FOREIGN KEY (module, phien_ban_module) REFERENCES loi.phien_ban_module(module, so_phien_ban)
    );
    CREATE TABLE IF NOT EXISTS loi.dang_ky_ham_module (
        id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai_ham text NOT NULL CHECK (loai_ham ~ '^[a-z][a-z0-9_]{0,62}$'),
        phien_ban_contract text NOT NULL,
        ma_contract text NOT NULL,
        phien_ban_module text NOT NULL,
        ten_schema text NOT NULL,
        ten_ham text NOT NULL CHECK (ten_ham ~ '^[a-z][a-z0-9_]{0,62}$'),
        chu_ky text NOT NULL,
        vai_so_huu name NOT NULL,
        ma_bam_goi text NOT NULL,
        PRIMARY KEY (module, loai_ham, phien_ban_contract),
        FOREIGN KEY (module, phien_ban_module, ma_bam_goi)
            REFERENCES loi.phien_ban_module(module, so_phien_ban, ma_bam_goi),
        FOREIGN KEY (ma_contract, phien_ban_contract) REFERENCES loi.dang_ky_contract(ma, phien_ban),
        CHECK (ten_schema = 'mod_' || module)
    );

    FOREACH ten_bang IN ARRAY cac_bang LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY', ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY', ten_bang);
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_policy
                       WHERE polrelid = format('loi.%I', ten_bang)::regclass AND polname = 'dang_ky_chu') THEN
            EXECUTE format('CREATE POLICY dang_ky_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',
                           ten_bang, vai_chu);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC, %I, %I, %I',
                       ten_bang, vai_chay, login_loi, login_cai_dat);
    END LOOP;

    -- Kiem binding o thoi diem doc de phat hien ham bi thay the/doi owner/ACL.
    -- Khong goi ham o day: ABI resolver do contract/G2-06 quy dinh, khong tu dat.
    CREATE OR REPLACE FUNCTION loi.kiem_binding_ham(p loi.dang_ky_ham_module)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
        SELECT EXISTS (
            SELECT FROM pg_catalog.pg_proc h
            JOIN pg_catalog.pg_namespace n ON n.oid = h.pronamespace
            JOIN pg_catalog.pg_roles r ON r.oid = h.proowner
            JOIN pg_catalog.pg_namespace l ON l.nspname = 'loi'
            WHERE h.oid = pg_catalog.to_regprocedure(p.chu_ky)
              AND n.nspname = p.ten_schema AND h.proname = p.ten_ham
              AND r.rolname = p.vai_so_huu AND NOT r.rolcanlogin
              AND NOT r.rolsuper AND NOT r.rolbypassrls AND h.prosecdef
              AND h.prokind = 'f'
              AND r.rolname IN (
                  regexp_replace(pg_get_userbyid(l.nspowner), 'vai_doi_cau_truc_loi$', 'vai_doi_cau_truc_mod_' || p.module),
                  regexp_replace(pg_get_userbyid(l.nspowner), 'vai_doi_cau_truc_loi$', 'vai_kiem_toan_ven_mod_' || p.module))
              AND h.proconfig @> ARRAY['search_path=pg_catalog, pg_temp']
              AND has_schema_privilege(l.nspowner, n.oid, 'USAGE')
              AND has_function_privilege(l.nspowner, h.oid, 'EXECUTE')
              AND NOT EXISTS (
                  SELECT FROM aclexplode(coalesce(h.proacl, acldefault('f', h.proowner))) a
                  WHERE a.privilege_type = 'EXECUTE' AND a.grantee NOT IN
                    (h.proowner, l.nspowner,
                     (SELECT oid FROM pg_roles WHERE rolname = regexp_replace(
                         pg_get_userbyid(l.nspowner), 'vai_doi_cau_truc_loi$', 'dang_nhap_loi'))))
        );
    $ham$;

    CREATE OR REPLACE FUNCTION loi.kiem_dang_ky()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        binding loi.dang_ky_ham_module;
        chu name;
        c loi.dang_ky_contract;
    BEGIN
        IF TG_OP = 'TRUNCATE' THEN
            RAISE EXCEPTION 'Khong duoc thu hoi lich su registry' USING ERRCODE = '55000';
        END IF;
        IF TG_OP = 'DELETE' AND TG_TABLE_NAME <> 'module_dung_contract' THEN
            RAISE EXCEPTION 'Khong duoc xoa phien ban registry' USING ERRCODE = '55000';
        END IF;
        IF TG_TABLE_NAME = 'dang_ky_contract' THEN
            IF TG_OP = 'INSERT' AND NEW.trang_thai <> 'nhap' THEN
                RAISE EXCEPTION 'Contract phai bat dau o nhap' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF NEW.ma <> OLD.ma OR NEW.phien_ban <> OLD.phien_ban OR NEW.id <> OLD.id
                   OR (OLD.trang_thai <> 'nhap' AND
                       (to_jsonb(NEW) - ARRAY['trang_thai','sap_ngung_luc']) IS DISTINCT FROM
                       (to_jsonb(OLD) - ARRAY['trang_thai','sap_ngung_luc'])) THEN
                    RAISE EXCEPTION 'Dinh nghia contract da duyet bat bien' USING ERRCODE = '23514';
                END IF;
                IF NEW.trang_thai <> OLD.trang_thai AND NOT (
                    (OLD.trang_thai = 'nhap' AND NEW.trang_thai = 'anh_duyet') OR
                    (OLD.trang_thai = 'anh_duyet' AND NEW.trang_thai = 'dang_dung') OR
                    (OLD.trang_thai = 'dang_dung' AND NEW.trang_thai = 'ngung')) THEN
                    RAISE EXCEPTION 'Chuyen trang thai contract khong hop le' USING ERRCODE = '23514';
                END IF;
                IF NEW.trang_thai = 'ngung' AND EXISTS (SELECT FROM loi.module_dung_contract b
                    WHERE b.ma_contract = OLD.ma AND b.phien_ban_contract = OLD.phien_ban) THEN
                    RAISE EXCEPTION 'Contract con module/viec dang dung' USING ERRCODE = '23503';
                END IF;
            END IF;
            IF NEW.trang_thai <> 'nhap' AND (NEW.bang_chung_duyet IS NULL
                OR btrim(NEW.bang_chung_duyet) = '' OR NEW.duyet_luc IS NULL) THEN
                RAISE EXCEPTION 'Thieu bang chung Anh duyet' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME = 'module_dung_contract' AND TG_OP <> 'DELETE' THEN
            -- Khoa cung dong voi chuyen ngung: tranh binding va ngung cung commit.
            SELECT * INTO c FROM loi.dang_ky_contract
                WHERE ma = NEW.ma_contract AND phien_ban = NEW.phien_ban_contract FOR UPDATE;
            IF NOT FOUND OR c.trang_thai <> 'dang_dung' THEN
                RAISE EXCEPTION 'Contract chua dang dung' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME = 'module_danh_muc' THEN
            SELECT pg_get_userbyid(nspowner) INTO chu FROM pg_namespace WHERE nspname = 'loi';
            IF NEW.loai = 'MODULE' AND NEW.vai_so_huu::text <>
                regexp_replace(chu, 'vai_doi_cau_truc_loi$', 'vai_doi_cau_truc_mod_' || NEW.ma) THEN
                RAISE EXCEPTION 'Owner module khong hop le' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW IS DISTINCT FROM OLD THEN
                RAISE EXCEPTION 'Dinh danh module bat bien' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME = 'dang_ky_ham_module' THEN
            binding := NEW;
            IF NOT loi.kiem_binding_ham(binding) THEN
                RAISE EXCEPTION 'Binding ham sai owner/chu ky/quyen' USING ERRCODE = '23514';
            END IF;
            IF NOT EXISTS (SELECT FROM loi.dang_ky_contract WHERE ma = NEW.ma_contract
                AND phien_ban = NEW.phien_ban_contract AND module_so_huu = NEW.module) THEN
                RAISE EXCEPTION 'Contract khong thuoc module' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME = 'engine_dinh_nghia' AND TG_OP = 'INSERT' THEN
            IF EXISTS (SELECT FROM jsonb_array_elements(NEW.nang_luc) n
                WHERE jsonb_typeof(n) <> 'object'
                   OR coalesce(n->>'ma', '') = ''
                   OR coalesce(n->>'dau_vao', '') = ''
                   OR coalesce(n->>'dau_ra', '') = '')
               OR (SELECT count(*) <> count(DISTINCT n->>'ma')
                   FROM jsonb_array_elements(NEW.nang_luc) n) THEN
                RAISE EXCEPTION 'Capability thieu ma/contract hoac trung ma' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME IN ('phien_ban_module', 'engine_dinh_nghia') AND TG_OP = 'UPDATE' THEN
            IF (to_jsonb(NEW) - 'trang_thai') IS DISTINCT FROM (to_jsonb(OLD) - 'trang_thai') THEN
                RAISE EXCEPTION 'Phien ban goi bat bien' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.kiem_toan_dang_ky()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        INSERT INTO loi.nhat_ky_kiem_toan(hanh_dong, doi_tuong, doi_tuong_id, ket_luan)
            VALUES ('DANG_KY_' || TG_OP, TG_TABLE_NAME,
                CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END, 'DAT');
        RETURN NULL;
    END;
    $ham$;
    FOREACH ten_bang IN ARRAY cac_bang LOOP
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid = format('loi.%I', ten_bang)::regclass
                       AND tgname = 'kiem_dang_ky') THEN
            EXECUTE format('CREATE TRIGGER kiem_dang_ky BEFORE INSERT OR UPDATE OR DELETE
                ON loi.%I FOR EACH ROW EXECUTE FUNCTION loi.kiem_dang_ky()', ten_bang);
            EXECUTE format('CREATE TRIGGER chan_truncate_dang_ky BEFORE TRUNCATE
                ON loi.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.kiem_dang_ky()', ten_bang);
            EXECUTE format('CREATE TRIGGER kiem_toan_dang_ky AFTER INSERT OR UPDATE OR DELETE
                ON loi.%I FOR EACH ROW EXECUTE FUNCTION loi.kiem_toan_dang_ky()', ten_bang);
        END IF;
    END LOOP;

    -- Ghi sau khi co trigger de bootstrap Core cung duoc audit.
    INSERT INTO loi.module_danh_muc(ma, ten, loai) VALUES ('core', 'Core', 'CORE')
        ON CONFLICT (ma) DO NOTHING;

    -- Cua noi bo cho goi da kiem: chi nhan du lieu, khong nhan SQL.
    CREATE OR REPLACE FUNCTION loi.ghi_dang_ky(p_loai text, p jsonb)
    RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        chu text;
        ket_qua uuid;
        c loi.dang_ky_contract;
    BEGIN
        SELECT pg_get_userbyid(nspowner) INTO chu FROM pg_namespace WHERE nspname = 'loi';
        IF session_user <> regexp_replace(chu, 'vai_doi_cau_truc_loi$', 'dang_nhap_cai_dat') THEN
            RAISE EXCEPTION 'Chi chuc trach cai dat duoc ghi registry' USING ERRCODE = '42501';
        END IF;
        IF p IS NULL OR jsonb_typeof(p) <> 'object' THEN
            RAISE EXCEPTION 'Du lieu registry khong hop le' USING ERRCODE = '22023';
        END IF;
        IF p_loai = 'module' THEN
            INSERT INTO loi.module_danh_muc(ma, ten, loai, ten_schema, vai_so_huu)
                VALUES (p->>'ma', p->>'ten', 'MODULE', 'mod_' || (p->>'ma'),
                    regexp_replace(chu, 'vai_doi_cau_truc_loi$', 'vai_doi_cau_truc_mod_' || (p->>'ma')))
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'phien_ban_module' THEN
            INSERT INTO loi.phien_ban_module(module, so_phien_ban, ma_bam_goi, tuong_thich)
                VALUES (p->>'module', p->>'so_phien_ban', p->>'ma_bam_goi', p->'tuong_thich')
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'trang_thai_module' THEN
            UPDATE loi.phien_ban_module SET trang_thai = p->>'trang_thai'
                WHERE module = p->>'module' AND so_phien_ban = p->>'so_phien_ban'
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'engine' THEN
            INSERT INTO loi.engine_dinh_nghia(ma, ten, so_phien_ban, ma_bam_goi,
                ma_adapter, phien_ban_adapter, nang_luc, gioi_han)
                VALUES (p->>'ma', p->>'ten', p->>'so_phien_ban', p->>'ma_bam_goi',
                    p->'adapter'->>'ma', p->'adapter'->>'phien_ban', p->'capability', p->'gioi_han')
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'contract' THEN
            INSERT INTO loi.dang_ky_contract(ma, phien_ban, module_so_huu, lop,
                muc_dich, sieu_du_lieu, luoc_do, ma_bam)
                VALUES (p->>'ma', p->>'phien_ban', p->>'module_so_huu', p->>'lop',
                    p->>'muc_dich', p->'sieu_du_lieu', p->'luoc_do', p->>'ma_bam')
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'trang_thai_contract' THEN
            SELECT * INTO c FROM loi.dang_ky_contract
                WHERE ma = p->>'ma' AND phien_ban = p->>'phien_ban' FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'Khong co contract' USING ERRCODE = '22023'; END IF;
            UPDATE loi.dang_ky_contract SET trang_thai = p->>'trang_thai',
                bang_chung_duyet = CASE WHEN c.trang_thai = 'nhap' THEN p->>'bang_chung_duyet'
                    ELSE c.bang_chung_duyet END,
                duyet_luc = CASE WHEN c.trang_thai = 'nhap' THEN statement_timestamp() ELSE c.duyet_luc END
                WHERE ma = c.ma AND phien_ban = c.phien_ban RETURNING id INTO ket_qua;
        ELSIF p_loai = 'sap_ngung_contract' THEN
            UPDATE loi.dang_ky_contract SET sap_ngung_luc = (p->>'sap_ngung_luc')::timestamptz
                WHERE ma = p->>'ma' AND phien_ban = p->>'phien_ban' RETURNING id INTO ket_qua;
        ELSIF p_loai = 'dung_contract' THEN
            INSERT INTO loi.module_dung_contract(ma_contract, phien_ban_contract, module, phien_ban_module)
                VALUES (p->>'ma_contract', p->>'phien_ban_contract', p->>'module', p->>'phien_ban_module')
                RETURNING id INTO ket_qua;
        ELSIF p_loai = 'thoi_dung_contract' THEN
            -- G2-25 chi goi sau khi kiem khong con module/viec ghim; khong tu thay ban.
            DELETE FROM loi.module_dung_contract WHERE ma_contract = p->>'ma_contract'
                AND phien_ban_contract = p->>'phien_ban_contract' AND module = p->>'module'
                AND phien_ban_module = p->>'phien_ban_module' RETURNING id INTO ket_qua;
        ELSIF p_loai = 'ham_module' THEN
            INSERT INTO loi.dang_ky_ham_module(module, loai_ham, phien_ban_contract,
                ma_contract, phien_ban_module, ten_schema, ten_ham, chu_ky, vai_so_huu, ma_bam_goi)
                VALUES (p->>'module', p->>'loai_ham', p->>'phien_ban_contract', p->>'ma_contract',
                    p->>'phien_ban_module', 'mod_' || (p->>'module'), p->>'ten_ham',
                    p->>'chu_ky', p->>'vai_so_huu', p->>'ma_bam_goi')
                ON CONFLICT (module, loai_ham, phien_ban_contract) DO UPDATE SET
                    ma_contract = EXCLUDED.ma_contract, phien_ban_module = EXCLUDED.phien_ban_module,
                    ten_schema = EXCLUDED.ten_schema, ten_ham = EXCLUDED.ten_ham,
                    chu_ky = EXCLUDED.chu_ky, vai_so_huu = EXCLUDED.vai_so_huu,
                    ma_bam_goi = EXCLUDED.ma_bam_goi RETURNING id INTO ket_qua;
        ELSE
            RAISE EXCEPTION 'Loai dang ky khong hop le' USING ERRCODE = '22023';
        END IF;
        IF ket_qua IS NULL THEN RAISE EXCEPTION 'Khong co muc dang ky' USING ERRCODE = '22023'; END IF;
        RETURN ket_qua;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.doc_dang_ky(p_loai text, p_ma text DEFAULT NULL)
    RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ket_qua jsonb;
    BEGIN
        CASE p_loai
        WHEN 'module' THEN SELECT jsonb_agg(to_jsonb(m) ORDER BY m.ma) INTO ket_qua
            FROM loi.module_danh_muc m WHERE p_ma IS NULL OR m.ma = p_ma;
        WHEN 'phien_ban_module' THEN SELECT jsonb_agg(to_jsonb(m) ORDER BY m.module, m.so_phien_ban) INTO ket_qua
            FROM loi.phien_ban_module m WHERE p_ma IS NULL OR m.module = p_ma;
        WHEN 'engine' THEN SELECT jsonb_agg(to_jsonb(e) ORDER BY e.ma, e.so_phien_ban) INTO ket_qua
            FROM loi.engine_dinh_nghia e WHERE p_ma IS NULL OR e.ma = p_ma;
        WHEN 'contract' THEN SELECT jsonb_agg(to_jsonb(c) || jsonb_build_object('module_dang_dung',
            coalesce((SELECT jsonb_agg(jsonb_build_object('module', b.module, 'phien_ban_module', b.phien_ban_module)
                ORDER BY b.module, b.phien_ban_module) FROM loi.module_dung_contract b
                WHERE b.ma_contract = c.ma AND b.phien_ban_contract = c.phien_ban), '[]'::jsonb))
            ORDER BY c.ma, c.phien_ban) INTO ket_qua
            FROM loi.dang_ky_contract c WHERE p_ma IS NULL OR c.ma = p_ma;
        WHEN 'ham_module' THEN SELECT jsonb_agg(to_jsonb(h) ORDER BY h.module, h.loai_ham, h.phien_ban_contract) INTO ket_qua
            FROM loi.dang_ky_ham_module h WHERE p_ma IS NULL OR h.module = p_ma;
        ELSE RAISE EXCEPTION 'Loai dang ky khong hop le' USING ERRCODE = '22023';
        END CASE;
        RETURN coalesce(ket_qua, '[]'::jsonb);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.phan_giai_ham_module(
        p_module text, p_loai_ham text, p_phien_ban_contract text,
        p_ma text, p_phap_nhan_id uuid, p_hanh_dong text,
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE h loi.dang_ky_ham_module;
    BEGIN
        IF NOT EXISTS (SELECT FROM loi.xac_minh_phien(
            p_ma, p_module, p_phap_nhan_id, p_hanh_dong, p_viec_id, p_the_he)) THEN
            RAISE EXCEPTION 'Phien khong hop le' USING ERRCODE = '42501';
        END IF;
        SELECT d.* INTO h FROM loi.dang_ky_ham_module d
            JOIN loi.phien_ban_module m ON m.module = d.module
                AND m.so_phien_ban = d.phien_ban_module AND m.ma_bam_goi = d.ma_bam_goi
            JOIN loi.dang_ky_contract c ON c.ma = d.ma_contract AND c.phien_ban = d.phien_ban_contract
            WHERE d.module = p_module AND d.loai_ham = p_loai_ham
                AND d.phien_ban_contract = p_phien_ban_contract
                AND m.trang_thai = 'da_cai' AND c.trang_thai = 'dang_dung';
        IF NOT FOUND THEN RETURN jsonb_build_object('ket_luan', 'CHO'); END IF;
        IF to_regprocedure(h.chu_ky) IS NULL THEN RETURN jsonb_build_object('ket_luan', 'CHO'); END IF;
        IF NOT loi.kiem_binding_ham(h) THEN
            RAISE EXCEPTION 'Binding ham khong con hop le' USING ERRCODE = '42501';
        END IF;
        RETURN jsonb_build_object('ket_luan', 'DAT', 'binding', to_jsonb(h));
    END;
    $ham$;

    -- Core-only resolver; module chi nhan ham doc registry theo quyen duoc cap.
    EXECUTE format('GRANT USAGE ON SCHEMA loi TO %I', login_cai_dat);
    FOR ham IN SELECT oid::regprocedure AS chu_ky, proname FROM pg_proc
        WHERE pronamespace = 'loi'::regnamespace AND proname IN ('kiem_binding_ham',
            'kiem_dang_ky', 'kiem_toan_dang_ky', 'ghi_dang_ky', 'doc_dang_ky', 'phan_giai_ham_module')
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I, %I',
                       ham.chu_ky, vai_chay, login_loi, login_cai_dat);
        IF ham.proname = 'ghi_dang_ky' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I', ham.chu_ky, login_cai_dat);
        ELSIF ham.proname = 'doc_dang_ky' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I, %I', ham.chu_ky, vai_chay, login_cai_dat);
        ELSIF ham.proname = 'phan_giai_ham_module' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I', ham.chu_ky, login_loi);
        END IF;
    END LOOP;
    PERFORM set_config('search_path', duong_tim_truoc, true);
    PERFORM set_config('role', vai_truoc, true);
END;
$$;
