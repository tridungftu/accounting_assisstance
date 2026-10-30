-- G2-08: nang cong tac M0056, giu co doc M0056/kiem_module/trang_thai_cho.
-- QD-09: moi lan doi la snapshot moi; khong UPDATE/DELETE lich su/nguoi thu.
-- Default TAT, phien_ban_dong 1; lan ghi dau luu ca snapshot TAT ban dau.
-- Caller giu transaction. Chi Core DEMO/test PG16+, lead ap dung theo thu tu.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    vai_chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    vai_chay constant text := tien_to || 'vai_chay_loi';
    login_loi constant text := tien_to || 'dang_nhap_loi';
    login_cai_dat constant text := tien_to || 'dang_nhap_cai_dat';
    vai_truoc constant text := current_setting('role');
    duong_tim_truoc constant text := current_setting('search_path');
    ten_bang text;
    ham record;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63
       OR (tien_to <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-08: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname = 'loi' AND pg_get_userbyid(nspowner) = vai_chu)
       OR to_regclass('loi.mtq_admin') IS NULL
       OR to_regclass('loi.module_danh_muc') IS NULL
       OR to_regprocedure('loi.chan_sua_kiem_toan()') IS NULL THEN
        RAISE EXCEPTION 'G2-08: Can lead, ap G2-01..06 truoc';
    END IF;
    FOREACH ten_bang IN ARRAY ARRAY['module_cong_tac', 'module_nguoi_thu'] LOOP
        IF EXISTS (SELECT FROM pg_class WHERE oid = to_regclass('loi.' || ten_bang)
                   AND (pg_get_userbyid(relowner) <> vai_chu OR relkind <> 'r')) THEN
            RAISE EXCEPTION 'G2-08: Can lead, cong tac sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);

    CREATE TABLE IF NOT EXISTS loi.module_cong_tac (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        phien_ban_dong bigint NOT NULL CHECK (phien_ban_dong > 0),
        che_do text NOT NULL CHECK (che_do IN ('TAT','THU','VAN_HANH')),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (module, phap_nhan_id, phien_ban_dong),
        UNIQUE (id, phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi.module_nguoi_thu (
        cong_tac_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        PRIMARY KEY (cong_tac_id, nguoi_dung_id),
        FOREIGN KEY (cong_tac_id, phap_nhan_id) REFERENCES loi.module_cong_tac(id, phap_nhan_id)
    );
    FOREACH ten_bang IN ARRAY ARRAY['module_cong_tac', 'module_nguoi_thu'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY', ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY', ten_bang);
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid = format('loi.%I', ten_bang)::regclass
                       AND polname = 'cong_tac_chu') THEN
            EXECUTE format('CREATE POLICY cong_tac_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',
                           ten_bang, vai_chu);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC, %I, %I, %I',
                       ten_bang, vai_chay, login_loi, login_cai_dat);
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid = format('loi.%I', ten_bang)::regclass
                       AND tgname = 'cong_tac_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER cong_tac_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE
                ON loi.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()', ten_bang);
        END IF;
    END LOOP;

    -- G2-06 chua co cua Admin cong khai: dung NGUYEN nguon Admin MTQ, khong
    -- tao vai/Admin rieng, khong fallback vai_tro CFO hoac MTQ dang tat.
    CREATE OR REPLACE FUNCTION loi.module_kiem_admin(p_ma text, p_module text, p_pn uuid, p_hanh_dong text)
    RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ai uuid;
    BEGIN
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,'core',p_pn,p_hanh_dong,NULL,NULL);
        IF ai IS NULL OR NOT EXISTS (SELECT FROM loi.mtq_admin
            WHERE nguoi_dung_id = ai AND thu_hoi_luc IS NULL) THEN
            RAISE EXCEPTION 'MODULE_CHI_ADMIN' USING ERRCODE = '42501';
        END IF;
        IF NOT EXISTS (SELECT FROM loi.module_danh_muc WHERE ma = p_module AND loai = 'MODULE') THEN
            RAISE EXCEPTION 'MODULE_DAU_VAO' USING ERRCODE = '22023';
        END IF;
        RETURN ai;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.module_che_do(p_ma text, p_module text, p_pn uuid)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE cu loi.module_cong_tac;
    BEGIN
        PERFORM loi.module_kiem_admin(p_ma,p_module,p_pn,'CORE:MODULE:XEM');
        PERFORM pg_advisory_xact_lock_shared(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
        SELECT * INTO cu FROM loi.module_cong_tac WHERE module = p_module AND phap_nhan_id = p_pn
            ORDER BY phien_ban_dong DESC LIMIT 1;
        RETURN jsonb_build_object('row_version',coalesce(cu.phien_ban_dong,1)::text,
            'che_do',coalesce(cu.che_do,'TAT'), 'nguoi_thu_ids',coalesce((
                SELECT jsonb_agg(nguoi_dung_id ORDER BY nguoi_dung_id) FROM loi.module_nguoi_thu
                WHERE cong_tac_id = cu.id AND phap_nhan_id = p_pn),'[]'::jsonb));
    END;
    $ham$;

    -- Nguoi thu gan voi snapshot; doi danh sach cung CAS/transaction voi che do.
    CREATE OR REPLACE FUNCTION loi.module_doi_che_do(p_ma text, p_module text, p_pn uuid,
        p_che_do text, p_phien_ban_cu bigint, p_nguoi_thu uuid[], p_request uuid)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ai uuid; cu loi.module_cong_tac; moi uuid; ban_cu bigint;
    BEGIN
        -- Khoa doi cong tac truoc khi xac minh: snapshot moi sau khi cho CAS.
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        IF p_module IS NULL OR p_pn IS NULL THEN
            RAISE EXCEPTION 'MODULE_DAU_VAO' USING ERRCODE = '22023';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
        ai := loi.module_kiem_admin(p_ma,p_module,p_pn,'CORE:MODULE:SUA');
        IF p_che_do IS NULL OR p_che_do NOT IN ('TAT','THU','VAN_HANH')
           OR p_phien_ban_cu IS NULL OR p_phien_ban_cu < 1 OR p_request IS NULL
           OR p_nguoi_thu IS NULL OR cardinality(p_nguoi_thu) > 1000
           OR array_position(p_nguoi_thu,NULL) IS NOT NULL
           OR cardinality(p_nguoi_thu) <> (SELECT count(DISTINCT n) FROM unnest(p_nguoi_thu) n) THEN
            RAISE EXCEPTION 'MODULE_DAU_VAO' USING ERRCODE = '22023';
        END IF;
        IF EXISTS (SELECT FROM unnest(p_nguoi_thu) n WHERE NOT EXISTS (
            SELECT FROM loi.nguoi_dung d JOIN loi.phan_quyen q ON q.nguoi_dung_id = d.id
            WHERE d.id = n AND d.trang_thai = 'HOAT_DONG' AND q.phap_nhan_id = p_pn
                AND p_module = ANY(q.module))) THEN
            RAISE EXCEPTION 'MODULE_NGUOI_THU' USING ERRCODE = '22023';
        END IF;
        -- Nang guard go-live M0056: registry thay danh muc mac dinh cu.
        -- Dang ky khong dong nghia da cai; khong cho cong bo module chua cai.
        IF p_che_do = 'VAN_HANH' AND NOT EXISTS (SELECT FROM loi.phien_ban_module
            WHERE module = p_module AND trang_thai = 'da_cai') THEN
            RAISE EXCEPTION 'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE' USING ERRCODE = '55000';
        END IF;
        SELECT * INTO cu FROM loi.module_cong_tac WHERE module = p_module AND phap_nhan_id = p_pn
            ORDER BY phien_ban_dong DESC LIMIT 1;
        ban_cu := coalesce(cu.phien_ban_dong,1);
        IF p_phien_ban_cu <> ban_cu OR ban_cu = 9223372036854775807 THEN
            RAISE EXCEPTION 'MODULE_REVISION' USING ERRCODE = '40001';
        END IF;
        IF cu.id IS NULL THEN
            INSERT INTO loi.module_cong_tac(module,phap_nhan_id,phien_ban_dong,che_do,tao_boi)
                VALUES (p_module,p_pn,1,'TAT',ai);
        END IF;
        INSERT INTO loi.module_cong_tac(module,phap_nhan_id,phien_ban_dong,che_do,tao_boi)
            VALUES (p_module,p_pn,ban_cu+1,p_che_do,ai) RETURNING id INTO moi;
        INSERT INTO loi.module_nguoi_thu(cong_tac_id,phap_nhan_id,nguoi_dung_id)
            SELECT moi,p_pn,n FROM unnest(p_nguoi_thu) n;
        PERFORM loi.ghi_kiem_toan('CORE:MODULE:SUA','module_cong_tac',moi,'DAT',
            p_ma,'core',p_pn,p_request);
        RETURN jsonb_build_object('row_version',(ban_cu+1)::text,'che_do',p_che_do,
            'nguoi_thu_ids',to_jsonb(p_nguoi_thu));
    END;
    $ham$;

    -- Cong tac khong thay MTQ: caller van kiem hanh dong/pham vi/hang muc.
    -- TAT cho xem lich su noi bo; khong nhan/ghi/xuat/cong bo viec moi.
    CREATE OR REPLACE FUNCTION loi.module_trang_thai(p_ma text, p_module text, p_pn uuid,
        p_hanh_dong text, p_module_phien text DEFAULT NULL,
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ai uuid; cu loi.module_cong_tac; cd text; duoc_thu boolean := false; mp text;
    BEGIN
        mp := coalesce(p_module_phien,p_module);
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        IF p_module IS NULL OR p_pn IS NULL
           OR NOT EXISTS (SELECT FROM loi.module_danh_muc WHERE ma = mp)
           OR split_part(p_hanh_dong,':',1) IS DISTINCT FROM upper(mp) THEN
            RAISE EXCEPTION 'MODULE_DAU_VAO' USING ERRCODE = '22023';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,mp,p_pn,p_hanh_dong,p_viec_id,p_the_he);
        IF ai IS NULL THEN RAISE EXCEPTION 'MODULE_PHIEN' USING ERRCODE = '42501'; END IF;
        IF NOT EXISTS (SELECT FROM loi.module_danh_muc WHERE ma = p_module AND loai = 'MODULE') THEN
            RAISE EXCEPTION 'MODULE_DAU_VAO' USING ERRCODE = '22023';
        END IF;
        SELECT * INTO cu FROM loi.module_cong_tac WHERE module = p_module AND phap_nhan_id = p_pn
            ORDER BY phien_ban_dong DESC LIMIT 1;
        cd := coalesce(cu.che_do,'TAT');
        IF cd = 'THU' THEN
            duoc_thu := EXISTS (SELECT FROM loi.module_nguoi_thu t JOIN loi.phan_quyen q
                ON q.nguoi_dung_id = t.nguoi_dung_id AND q.phap_nhan_id = t.phap_nhan_id
                WHERE t.cong_tac_id = cu.id AND t.phap_nhan_id = p_pn AND t.nguoi_dung_id = ai
                    AND p_module = ANY(q.module));
        END IF;
        RETURN jsonb_build_object('che_do',cd,'row_version',coalesce(cu.phien_ban_dong,1)::text,
            'hien_luoi',cd = 'VAN_HANH' OR duoc_thu,
            'cho_xem',cd IN ('VAN_HANH','TAT') OR duoc_thu,
            'cho_ghi',cd = 'VAN_HANH' OR duoc_thu,
            'cho_xuat_ngoai',cd = 'VAN_HANH','cong_bo_chinh_thuc',cd = 'VAN_HANH',
            'dai_dang_thu',cd = 'THU' AND duoc_thu);
    END;
    $ham$;

    FOR ham IN SELECT p.oid::regprocedure AS chu_ky,p.proname FROM pg_proc p
        WHERE p.pronamespace = 'loi'::regnamespace
          AND p.proname IN ('module_kiem_admin','module_che_do','module_doi_che_do','module_trang_thai')
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I, %I',
                       ham.chu_ky,vai_chay,login_loi,login_cai_dat);
        IF ham.proname = 'module_trang_thai' THEN
            -- Module nhan EXECUTE V2 cu the qua provisioning, khong GRANT PUBLIC.
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.chu_ky,vai_chay);
        ELSIF ham.proname IN ('module_che_do','module_doi_che_do') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.chu_ky,login_loi);
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_tim_truoc,true);
    PERFORM set_config('role',vai_truoc,true);
END;
$$;
