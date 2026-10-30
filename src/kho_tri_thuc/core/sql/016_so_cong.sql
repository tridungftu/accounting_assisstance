-- G2-16: so ben vung, KHONG bind/chuyen socket (G2-21).
-- Ke thua registry G2-05 va row lock/clock_timestamp/GREATEST cua lease XS-2.
-- So do chua thu thap la NULL; khong tu suy 0 hay tu doi chinh sach chay.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    chay constant text := tien_to || 'vai_chay_loi';
    login constant text := tien_to || 'dang_nhap_loi';
    cai_dat constant text := tien_to || 'dang_nhap_cai_dat';
    vai_cu constant text := current_setting('role');
    duong_cu constant text := current_setting('search_path');
    bang text;
    ham record;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63
       OR (tien_to <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-16: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR to_regclass('loi.engine_dinh_nghia') IS NULL
       OR to_regclass('loi.mtq_admin') IS NULL
       OR to_regclass('loi.ack_su_kien') IS NULL THEN
        RAISE EXCEPTION 'G2-16: Can lead, ap chuoi G2-01..15 truoc';
    END IF;
    FOREACH bang IN ARRAY ARRAY['engine_ho_so_chay','so_cong','engine_phien_chay',
        'module_phien_chay','so_do_phien_chay'] LOOP
        IF EXISTS (SELECT FROM pg_class WHERE oid=to_regclass('loi.'||bang)
            AND (relkind<>'r' OR pg_get_userbyid(relowner)<>chu)) THEN
            RAISE EXCEPTION 'G2-16: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);

    CREATE TABLE IF NOT EXISTS loi.engine_ho_so_chay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        engine_id uuid NOT NULL REFERENCES loi.engine_dinh_nghia(id),
        may_chu_id uuid NOT NULL,
        executable text NOT NULL CHECK (btrim(executable)<>''),
        doi_so jsonb NOT NULL CHECK (jsonb_typeof(doi_so)='array'),
        tham_chieu_bi_mat text,
        so_viec_dong_thoi integer NOT NULL CHECK (so_viec_dong_thoi BETWEEN 1 AND 1000),
        timeout_giay integer NOT NULL CHECK (timeout_giay BETWEEN 1 AND 86400),
        ranh_giay integer NOT NULL DEFAULT 300 CHECK (ranh_giay BETWEEN 1 AND 86400),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        het_hieu_luc_luc timestamptz
    );
    CREATE TABLE IF NOT EXISTS loi.so_cong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        may_chu_id uuid NOT NULL,
        dia_chi_nghe inet NOT NULL CHECK (dia_chi_nghe IN ('127.0.0.1'::inet,'::1'::inet)),
        cong integer NOT NULL CHECK (cong BETWEEN 1024 AND 65535),
        module text REFERENCES loi.module_danh_muc(ma),
        engine_ho_so_id uuid REFERENCES loi.engine_ho_so_chay(id),
        giu_boi uuid,
        the_he bigint NOT NULL DEFAULT 0 CHECK (the_he>=0),
        giu_den timestamptz,
        trang_thai text NOT NULL DEFAULT 'TRONG' CHECK (trang_thai IN
            ('TRONG','CORE_GIU','DANG_BAN_GIAO','CON_GIU','DANG_THU_HOI','LOI')),
        ma_loi text CHECK (ma_loi ~ '^[A-Z][A-Z0-9_]{0,79}$'),
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong>0),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        het_hieu_luc_luc timestamptz,
        CHECK (num_nonnulls(module,engine_ho_so_id)=1),
        CHECK ((giu_boi IS NULL)=(giu_den IS NULL)),
        CHECK ((trang_thai='LOI')=(ma_loi IS NOT NULL)),
        UNIQUE (may_chu_id,dia_chi_nghe,cong),
        UNIQUE (may_chu_id,module),
        UNIQUE (may_chu_id,engine_ho_so_id),
        UNIQUE (id,module,may_chu_id),
        UNIQUE (id,engine_ho_so_id)
    );
    CREATE TABLE IF NOT EXISTS loi.module_phien_chay (
        id uuid PRIMARY KEY,
        so_cong_id uuid NOT NULL,
        module text NOT NULL,
        may_chu_id uuid NOT NULL,
        phien_ban_module text NOT NULL,
        the_he bigint NOT NULL CHECK (the_he>0),
        pid integer NOT NULL CHECK (pid>0),
        dinh_danh_lan_tao text NOT NULL CHECK (length(btrim(dinh_danh_lan_tao)) BETWEEN 1 AND 200),
        nhan_yeu_cau_luc timestamptz NOT NULL,
        bat_dau_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        san_sang_luc timestamptz,
        bang_chung_san_sang_id uuid,
        heartbeat_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ket_thuc_luc timestamptz,
        ly_do_ket_thuc text,
        UNIQUE (so_cong_id,the_he),
        FOREIGN KEY (module,phien_ban_module) REFERENCES loi.phien_ban_module(module,so_phien_ban),
        FOREIGN KEY (so_cong_id,module,may_chu_id) REFERENCES loi.so_cong(id,module,may_chu_id)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS module_phien_chay_mot_chu
        ON loi.module_phien_chay(may_chu_id,module) WHERE ket_thuc_luc IS NULL;
    CREATE TABLE IF NOT EXISTS loi.engine_phien_chay (
        id uuid PRIMARY KEY,
        so_cong_id uuid NOT NULL,
        engine_ho_so_id uuid NOT NULL,
        phien_ban_thuc text NOT NULL CHECK (btrim(phien_ban_thuc)<>''),
        the_he bigint NOT NULL CHECK (the_he>0),
        pid integer NOT NULL CHECK (pid>0),
        dinh_danh_lan_tao text NOT NULL CHECK (length(btrim(dinh_danh_lan_tao)) BETWEEN 1 AND 200),
        nhan_yeu_cau_luc timestamptz NOT NULL,
        bat_dau_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        san_sang_luc timestamptz,
        bang_chung_san_sang_id uuid,
        heartbeat_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ket_thuc_luc timestamptz,
        ly_do_ket_thuc text,
        UNIQUE (so_cong_id,the_he),
        FOREIGN KEY (so_cong_id,engine_ho_so_id) REFERENCES loi.so_cong(id,engine_ho_so_id)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS engine_phien_chay_mot_chu
        ON loi.engine_phien_chay(so_cong_id) WHERE ket_thuc_luc IS NULL;
    CREATE TABLE IF NOT EXISTS loi.so_do_phien_chay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        engine_phien_id uuid REFERENCES loi.engine_phien_chay(id),
        module_phien_id uuid REFERENCES loi.module_phien_chay(id),
        nhan_yeu_cau_luc timestamptz,
        bat_dau_luc timestamptz,
        san_sang_luc timestamptz,
        that_bai_luc timestamptz,
        dong_luc timestamptz,
        chay_viec_ms numeric CHECK (chay_viec_ms>=0 AND chay_viec_ms<1e18),
        ranh_ms numeric CHECK (ranh_ms>=0 AND ranh_ms<1e18),
        ram_dinh_byte bigint CHECK (ram_dinh_byte>=0),
        ram_trung_binh_byte bigint CHECK (ram_trung_binh_byte>=0),
        cpu_ms numeric CHECK (cpu_ms>=0 AND cpu_ms<1e18),
        cua_so_tu timestamptz,
        cua_so_den timestamptz,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK (num_nonnulls(engine_phien_id,module_phien_id)=1),
        CHECK ((cua_so_tu IS NULL)=(cua_so_den IS NULL)),
        CHECK (cua_so_den>=cua_so_tu),
        CHECK (ram_trung_binh_byte<=ram_dinh_byte)
    );

    FOREACH bang IN ARRAY ARRAY['engine_ho_so_chay','so_cong','engine_phien_chay',
        'module_phien_chay','so_do_phien_chay'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY',bang);
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid=('loi.'||bang)::regclass
            AND polname='so_cong_chu') THEN
            EXECUTE format('CREATE POLICY so_cong_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',bang,chu);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC,%I,%I,%I',bang,chay,login,cai_dat);
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=('loi.'||bang)::regclass
            AND tgname='so_cong_khong_xoa') THEN
            EXECUTE format('CREATE TRIGGER so_cong_khong_xoa BEFORE DELETE OR TRUNCATE ON loi.%I
                FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
        END IF;
    END LOOP;
    IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='loi.so_do_phien_chay'::regclass
        AND tgname='so_do_bat_bien') THEN
        CREATE TRIGGER so_do_bat_bien BEFORE UPDATE ON loi.so_do_phien_chay
            FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan();
    END IF;

    CREATE OR REPLACE FUNCTION loi.so_cong_chi_core() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_loi') THEN
            RAISE EXCEPTION 'CONG_CHI_CORE' USING ERRCODE='42501';
        END IF;
    END;
    $ham$;
    -- Ho so chi den tu Module Manager da kiem; khong tao role/login engine.
    CREATE OR REPLACE FUNCTION loi.so_cong_tao_ho_so(p jsonb) RETURNS uuid
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE k uuid;
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_cai_dat') THEN
            RAISE EXCEPTION 'CONG_CHI_CAI_DAT' USING ERRCODE='42501';
        END IF;
        IF p IS NULL OR jsonb_typeof(p)<>'object' OR jsonb_typeof(p->'doi_so') IS DISTINCT FROM 'array'
            OR EXISTS (SELECT FROM jsonb_array_elements(p->'doi_so') x WHERE jsonb_typeof(x)<>'string')
            OR EXISTS (SELECT FROM jsonb_object_keys(p) x WHERE x NOT IN ('engine_id','may_chu_id',
                'executable','doi_so','tham_chieu_bi_mat','so_viec_dong_thoi','timeout_giay','ranh_giay')) THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        INSERT INTO loi.engine_ho_so_chay(engine_id,may_chu_id,executable,doi_so,tham_chieu_bi_mat,
            so_viec_dong_thoi,timeout_giay,ranh_giay) VALUES ((p->>'engine_id')::uuid,
            (p->>'may_chu_id')::uuid,p->>'executable',p->'doi_so',p->>'tham_chieu_bi_mat',
            (p->>'so_viec_dong_thoi')::integer,(p->>'timeout_giay')::integer,
            coalesce((p->>'ranh_giay')::integer,300)) RETURNING id INTO k;
        RETURN k;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_cap(p_may uuid,p_dia_chi inet,p_cong integer,
        p_module text,p_ho_so uuid) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        IF p_may IS NULL OR p_dia_chi IS NULL OR p_cong IS NULL
            OR p_dia_chi NOT IN ('127.0.0.1'::inet,'::1'::inet) OR p_cong NOT BETWEEN 1024 AND 65535
            OR num_nonnulls(p_module,p_ho_so)<>1 THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        IF p_module IS NOT NULL AND NOT EXISTS (SELECT FROM loi.module_danh_muc
            WHERE ma=p_module AND loai='MODULE') THEN
            RAISE EXCEPTION 'CONG_CHU' USING ERRCODE='22023';
        END IF;
        IF p_ho_so IS NOT NULL AND NOT EXISTS (SELECT FROM loi.engine_ho_so_chay
            WHERE id=p_ho_so AND may_chu_id=p_may AND het_hieu_luc_luc IS NULL) THEN
            RAISE EXCEPTION 'CONG_CHU' USING ERRCODE='22023';
        END IF;
        -- Khoa cung chu truoc INSERT; UNIQUE van chan hai chu xin cung cong.
        PERFORM pg_advisory_xact_lock(hashtextextended('cong|'||p_may::text||'|'||
            coalesce(p_module,p_ho_so::text),0));
        SELECT * INTO s FROM loi.so_cong WHERE may_chu_id=p_may
            AND (module=p_module OR engine_ho_so_id=p_ho_so) FOR UPDATE;
        IF FOUND THEN
            IF s.cong<>p_cong OR s.dia_chi_nghe<>p_dia_chi OR s.het_hieu_luc_luc IS NOT NULL THEN
                RAISE EXCEPTION 'CONG_CO_DINH' USING ERRCODE='40001';
            END IF;
            RETURN to_jsonb(s);
        END IF;
        INSERT INTO loi.so_cong(may_chu_id,dia_chi_nghe,cong,module,engine_ho_so_id)
            VALUES (p_may,p_dia_chi,p_cong,p_module,p_ho_so) RETURNING * INTO s;
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_doc(p_id uuid) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_dong_phien(s loi.so_cong,p_ly_do text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE da_dong boolean;
    BEGIN
        UPDATE loi.module_phien_chay SET ket_thuc_luc=clock_timestamp(),ly_do_ket_thuc=p_ly_do
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he AND ket_thuc_luc IS NULL;
        da_dong:=FOUND;
        UPDATE loi.engine_phien_chay SET ket_thuc_luc=clock_timestamp(),ly_do_ket_thuc=p_ly_do
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he AND ket_thuc_luc IS NULL;
        IF NOT (da_dong OR FOUND) THEN RETURN; END IF;
        INSERT INTO loi.so_do_phien_chay(engine_phien_id,module_phien_id,dong_luc,that_bai_luc)
            VALUES (CASE WHEN s.engine_ho_so_id IS NOT NULL THEN s.giu_boi END,
                CASE WHEN s.module IS NOT NULL THEN s.giu_boi END,clock_timestamp(),
                CASE WHEN p_ly_do='LOI' THEN clock_timestamp() END);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_nhan(p_id uuid,p_instance uuid,p_the_he bigint,
        p_lease integer,p_pid integer,p_lan_tao text,p_phien_ban text,p_yeu_cau timestamptz,
        p_bat_dau timestamptz,
        p_doi_chieu uuid DEFAULT NULL) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; e text;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        IF p_instance IS NULL OR p_the_he IS NULL OR p_the_he<0
            OR p_lease IS NULL OR p_lease NOT BETWEEN 1 AND 3600 OR p_pid IS NULL OR p_pid<1
            OR p_lan_tao IS NULL OR length(btrim(p_lan_tao)) NOT BETWEEN 1 AND 200
            OR p_phien_ban IS NULL OR btrim(p_phien_ban)='' OR p_yeu_cau IS NULL OR p_bat_dau IS NULL
            OR NOT isfinite(p_yeu_cau) OR NOT isfinite(p_bat_dau)
            OR p_yeu_cau>p_bat_dau OR p_bat_dau>clock_timestamp() THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        IF s.trang_thai='LOI' THEN RAISE EXCEPTION 'CONG_KHOA_LOI' USING ERRCODE='55000'; END IF;
        IF s.het_hieu_luc_luc IS NOT NULL OR s.the_he IS DISTINCT FROM p_the_he
            OR s.giu_den>clock_timestamp() THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        -- Instance khong tai su dung, ke ca doi tu module sang engine.
        PERFORM pg_advisory_xact_lock(hashtextextended('instance|'||p_instance::text,0));
        IF EXISTS (SELECT FROM loi.module_phien_chay WHERE id=p_instance)
            OR EXISTS (SELECT FROM loi.engine_phien_chay WHERE id=p_instance) THEN
            RAISE EXCEPTION 'CONG_CHU' USING ERRCODE='22023';
        END IF;
        IF s.engine_ho_so_id IS NOT NULL THEN
            SELECT d.so_phien_ban INTO e FROM loi.engine_ho_so_chay h
                JOIN loi.engine_dinh_nghia d ON d.id=h.engine_id
                WHERE h.id=s.engine_ho_so_id AND h.het_hieu_luc_luc IS NULL;
            IF e IS DISTINCT FROM p_phien_ban THEN
                RAISE EXCEPTION 'CONG_CHU' USING ERRCODE='22023';
            END IF;
        ELSIF NOT EXISTS (SELECT FROM loi.phien_ban_module WHERE module=s.module
            AND so_phien_ban=p_phien_ban AND trang_thai='da_cai') THEN
            RAISE EXCEPTION 'CONG_CHU' USING ERRCODE='22023';
        END IF;
        IF s.giu_boi IS NOT NULL THEN
            -- Lease het KHONG la bang chung tien trinh/socket da tat. G2-21 doi chieu
            -- OS truoc, truyen UUID bang chung; so nay chi luu vet, khong tu kiem OS.
            IF p_doi_chieu IS NULL THEN
                RAISE EXCEPTION 'CONG_CAN_DOI_CHIEU' USING ERRCODE='55000';
            END IF;
            PERFORM loi.so_cong_dong_phien(s,'GIAN_DOAN');
            PERFORM loi.ghi_kiem_toan('CORE:CONG:DOI_CHIEU','so_cong',s.id,'DAT',
                p_request_id=>p_doi_chieu);
        END IF;
        UPDATE loi.so_cong SET giu_boi=p_instance,the_he=the_he+1,
            giu_den=clock_timestamp()+make_interval(secs=>p_lease),trang_thai='CORE_GIU',
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        IF s.module IS NOT NULL THEN
            INSERT INTO loi.module_phien_chay(id,so_cong_id,module,may_chu_id,phien_ban_module,
                the_he,pid,dinh_danh_lan_tao,nhan_yeu_cau_luc,bat_dau_luc) VALUES
                (p_instance,s.id,s.module,s.may_chu_id,p_phien_ban,s.the_he,p_pid,p_lan_tao,p_yeu_cau,p_bat_dau);
        ELSE
            INSERT INTO loi.engine_phien_chay(id,so_cong_id,engine_ho_so_id,phien_ban_thuc,
                the_he,pid,dinh_danh_lan_tao,nhan_yeu_cau_luc,bat_dau_luc) VALUES
                (p_instance,s.id,s.engine_ho_so_id,p_phien_ban,s.the_he,p_pid,p_lan_tao,p_yeu_cau,p_bat_dau);
        END IF;
        INSERT INTO loi.so_do_phien_chay(engine_phien_id,module_phien_id,nhan_yeu_cau_luc,bat_dau_luc)
            VALUES (CASE WHEN s.module IS NULL THEN p_instance END,
                CASE WHEN s.module IS NOT NULL THEN p_instance END,p_yeu_cau,p_bat_dau);
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_giu(p_id uuid,p_instance uuid,p_the_he bigint)
    RETURNS loi.so_cong LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND OR s.giu_boi IS DISTINCT FROM p_instance OR p_instance IS NULL
            OR s.the_he IS DISTINCT FROM p_the_he OR s.giu_den IS NULL
            OR s.giu_den<=clock_timestamp() OR s.het_hieu_luc_luc IS NOT NULL
            OR s.trang_thai IN ('LOI','TRONG') THEN
            RAISE EXCEPTION 'CONG_MAT_LEASE' USING ERRCODE='40001';
        END IF;
        RETURN s;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_gia_han(p_id uuid,p_instance uuid,p_the_he bigint,p_lease integer)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p_lease IS NULL OR p_lease NOT BETWEEN 1 AND 3600 THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        UPDATE loi.so_cong SET giu_den=greatest(giu_den,clock_timestamp()+make_interval(secs=>p_lease)),
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        UPDATE loi.module_phien_chay SET heartbeat_luc=clock_timestamp()
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        UPDATE loi.engine_phien_chay SET heartbeat_luc=clock_timestamp()
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_san_sang(p_id uuid,p_instance uuid,p_the_he bigint,p_bang_chung uuid)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p_bang_chung IS NULL THEN RAISE EXCEPTION 'CONG_CAN_DOI_CHIEU' USING ERRCODE='22023'; END IF;
        -- Core chi goi sau kiem readiness/PID/lan tao/version/nonce/socket tai G2-21.
        UPDATE loi.module_phien_chay SET san_sang_luc=coalesce(san_sang_luc,clock_timestamp()),
            bang_chung_san_sang_id=coalesce(bang_chung_san_sang_id,p_bang_chung)
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        UPDATE loi.engine_phien_chay SET san_sang_luc=coalesce(san_sang_luc,clock_timestamp()),
            bang_chung_san_sang_id=coalesce(bang_chung_san_sang_id,p_bang_chung)
            WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        UPDATE loi.so_cong SET trang_thai='CON_GIU',phien_ban_dong=phien_ban_dong+1
            WHERE id=s.id RETURNING * INTO s;
        INSERT INTO loi.so_do_phien_chay(engine_phien_id,module_phien_id,san_sang_luc)
            VALUES (CASE WHEN s.module IS NULL THEN s.giu_boi END,
                CASE WHEN s.module IS NOT NULL THEN s.giu_boi END,clock_timestamp());
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_tra(p_id uuid,p_instance uuid,p_the_he bigint) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        -- G2-21 doi chieu/thu hoi socket xong moi tra; giu cong co dinh trong so.
        PERFORM loi.so_cong_dong_phien(s,'DA_DONG');
        UPDATE loi.so_cong SET giu_boi=NULL,giu_den=NULL,trang_thai='TRONG',
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id;
        RETURN true;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_loi_khoi_dong(p_id uuid,p_instance uuid,p_the_he bigint,p_ma_loi text)
    RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p_ma_loi IS NULL OR p_ma_loi !~ '^[A-Z][A-Z0-9_]{0,79}$' THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        PERFORM loi.so_cong_dong_phien(s,'LOI');
        -- Giu danh tinh cu de lan nhan sau mo khoa van can doi chieu OS.
        UPDATE loi.so_cong SET trang_thai='LOI',ma_loi=p_ma_loi,phien_ban_dong=phien_ban_dong+1 WHERE id=s.id;
        PERFORM loi.ghi_kiem_toan('CORE:CONG:LOI','so_cong',s.id,'LOI');
        RETURN true;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_mo_khoa(p_id uuid,p_phien_ban bigint,p_ma text,p_pn uuid,p_request uuid)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; ai uuid;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,'core',p_pn,'CORE:CONG:MO_KHOA',NULL,NULL);
        IF ai IS NULL OR NOT EXISTS (SELECT FROM loi.mtq_admin WHERE nguoi_dung_id=ai AND thu_hoi_luc IS NULL) THEN
            RAISE EXCEPTION 'CONG_CHI_ADMIN' USING ERRCODE='42501';
        END IF;
        IF p_request IS NULL THEN RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023'; END IF;
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        IF s.phien_ban_dong IS DISTINCT FROM p_phien_ban OR s.trang_thai<>'LOI' THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        PERFORM loi.ghi_kiem_toan('CORE:CONG:MO_KHOA','so_cong',s.id,'DAT',p_ma,'core',p_pn,p_request);
        UPDATE loi.so_cong SET trang_thai='TRONG',ma_loi=NULL,giu_den=clock_timestamp(),
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        RETURN to_jsonb(s);
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_het_hieu_luc(p_id uuid,p_phien_ban bigint) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND OR s.phien_ban_dong IS DISTINCT FROM p_phien_ban
            OR s.trang_thai<>'TRONG' OR s.giu_boi IS NOT NULL OR s.het_hieu_luc_luc IS NOT NULL THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        UPDATE loi.so_cong SET het_hieu_luc_luc=clock_timestamp(),phien_ban_dong=phien_ban_dong+1 WHERE id=s.id;
        RETURN true;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.so_cong_ghi_so_do(p_id uuid,p_instance uuid,p_the_he bigint,p jsonb)
    RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; k uuid;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p IS NULL OR jsonb_typeof(p)<>'object' OR p='{}'::jsonb
            OR EXISTS (SELECT FROM jsonb_object_keys(p) x WHERE x NOT IN
                ('chay_viec_ms','ranh_ms','ram_dinh_byte','ram_trung_binh_byte','cpu_ms','cua_so_tu','cua_so_den'))
            OR p->>'cua_so_tu' IS NULL OR p->>'cua_so_den' IS NULL
            OR NOT isfinite((p->>'cua_so_tu')::timestamptz)
            OR NOT isfinite((p->>'cua_so_den')::timestamptz)
            OR (p->>'cua_so_den')::timestamptz>clock_timestamp() THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        INSERT INTO loi.so_do_phien_chay(engine_phien_id,module_phien_id,chay_viec_ms,ranh_ms,
            ram_dinh_byte,ram_trung_binh_byte,cpu_ms,cua_so_tu,cua_so_den) VALUES
            (CASE WHEN s.module IS NULL THEN s.giu_boi END,CASE WHEN s.module IS NOT NULL THEN s.giu_boi END,
            (p->>'chay_viec_ms')::numeric,(p->>'ranh_ms')::numeric,(p->>'ram_dinh_byte')::bigint,
            (p->>'ram_trung_binh_byte')::bigint,(p->>'cpu_ms')::numeric,
            (p->>'cua_so_tu')::timestamptz,(p->>'cua_so_den')::timestamptz) RETURNING id INTO k;
        RETURN k;
    END;
    $ham$;

    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname LIKE 'so_cong\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I,%I',ham.ck,chay,login,cai_dat);
        IF ham.proname='so_cong_tao_ho_so' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,cai_dat);
        ELSIF ham.proname NOT IN ('so_cong_chi_core','so_cong_dong_phien','so_cong_giu') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
