-- G2-14: nang XS-2 (k2/sql_hang_viec.py, M0060/M0062), khong doi queue cu.
-- Giu dedupe, clock_timestamp, SKIP LOCKED, retry an toan va caller-owned tx.
-- hang_viec la con tro hien tai; buoc/lan_thu va cac dau trang thai chi them dong.
-- Engine dung kenh Core, khong nhan login CSDL. Core xac thuc instance truoc goi.
-- Khi ghi nghiep vu, ket_thuc phai o CUNG tx/ket noi; loi lease phai thoat tx.
-- Khong cam ket exactly-once cho tac dong ngoai CSDL.
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
        RAISE EXCEPTION 'G2-14: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR to_regclass('danh_muc.chung_tu') IS NULL
       OR to_regprocedure('loi.thu_hoi_uy_nhiem_viec(uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-14: Can lead, ap G2-01..12 truoc';
    END IF;
    FOREACH bang IN ARRAY ARRAY['hang_viec','buoc_viec','lan_thu','lan_thu_trang_thai'] LOOP
        IF EXISTS (SELECT FROM pg_class WHERE oid=to_regclass('loi.'||bang)
            AND (relkind<>'r' OR pg_get_userbyid(relowner)<>chu)) THEN
            RAISE EXCEPTION 'G2-14: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);

    CREATE TABLE IF NOT EXISTS loi.hang_viec (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai text NOT NULL CHECK (loai ~ '^[A-Z][A-Z0-9_-]{0,79}$'),
        phien_ban integer NOT NULL CHECK (phien_ban>0),
        phien_ban_contract text NOT NULL CHECK (btrim(phien_ban_contract)<>''),
        khoa_chong_trung text NOT NULL CHECK (length(khoa_chong_trung) BETWEEN 1 AND 200
            AND khoa_chong_trung=btrim(khoa_chong_trung)),
        bang_tham_chieu text NOT NULL CHECK (btrim(bang_tham_chieu)<>''),
        tham_chieu_id uuid NOT NULL,
        hanh_dong text NOT NULL,
        pham_vi_hanh_dong text[] NOT NULL,
        co_tac_dong_ngoai boolean NOT NULL,
        thu_lai_an_toan boolean NOT NULL,
        toi_da_lan_thu integer NOT NULL CHECK (toi_da_lan_thu BETWEEN 1 AND 100),
        thu_lai_giay integer NOT NULL CHECK (thu_lai_giay BETWEEN 1 AND 86400),
        giu_ngay integer CHECK (giu_ngay BETWEEN 1 AND 36500),
        trang_thai text NOT NULL DEFAULT 'CHO' CHECK (trang_thai IN
            ('CHO','DANG_CHAY','XONG','LOI','DA_DUNG','GIAN_DOAN','CHUA_RO')),
        so_lan_thu integer NOT NULL DEFAULT 0 CHECK (so_lan_thu BETWEEN 0 AND toi_da_lan_thu),
        the_he bigint NOT NULL DEFAULT 0 CHECK (the_he>=0),
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong>0),
        giu_boi uuid,
        giu_den timestamptz,
        giu_phien_id uuid REFERENCES loi.phien_xac_thuc(id),
        lan_thu_id uuid,
        thu_lai_sau timestamptz NOT NULL DEFAULT clock_timestamp(),
        yeu_cau_dung boolean NOT NULL DEFAULT false,
        ket_qua_id uuid,
        ma_loi text CHECK (ma_loi ~ '^[A-Z][A-Z0-9_]{0,79}$'),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ket_thuc_luc timestamptz,
        UNIQUE (phap_nhan_id,module,khoa_chong_trung),
        UNIQUE (id,phap_nhan_id,module),
        CHECK ((trang_thai='DANG_CHAY' AND giu_boi IS NOT NULL AND giu_den IS NOT NULL
                AND giu_phien_id IS NOT NULL AND lan_thu_id IS NOT NULL AND the_he>0)
            OR (trang_thai<>'DANG_CHAY' AND giu_boi IS NULL AND giu_den IS NULL AND giu_phien_id IS NULL)),
        CHECK ((trang_thai IN ('XONG','LOI','DA_DUNG'))=(ket_thuc_luc IS NOT NULL))
    );
    CREATE INDEX IF NOT EXISTS hang_viec_cho ON loi.hang_viec
        (phap_nhan_id,module,thu_lai_sau,tao_luc,id) WHERE trang_thai='CHO';
    CREATE INDEX IF NOT EXISTS hang_viec_giu ON loi.hang_viec(giu_den) WHERE trang_thai='DANG_CHAY';
    CREATE TABLE IF NOT EXISTS loi.buoc_viec (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        viec_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        module text NOT NULL,
        ma_buoc text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (viec_id,ma_buoc),
        UNIQUE (id,viec_id,phap_nhan_id,module),
        FOREIGN KEY (viec_id,phap_nhan_id,module) REFERENCES loi.hang_viec(id,phap_nhan_id,module)
    );
    CREATE TABLE IF NOT EXISTS loi.lan_thu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        buoc_viec_id uuid NOT NULL,
        viec_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        module text NOT NULL,
        so_lan integer NOT NULL CHECK (so_lan>0),
        the_he bigint NOT NULL CHECK (the_he>0),
        instance_id uuid NOT NULL,
        phien_id uuid NOT NULL REFERENCES loi.phien_xac_thuc(id),
        bat_dau_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (buoc_viec_id,so_lan),
        UNIQUE (viec_id,the_he),
        UNIQUE (id,viec_id,phap_nhan_id,module),
        FOREIGN KEY (buoc_viec_id,viec_id,phap_nhan_id,module)
            REFERENCES loi.buoc_viec(id,viec_id,phap_nhan_id,module)
    );
    -- Moi heartbeat/ket luan la mot dau moi; khong sua dong lan thu dang chay.
    CREATE TABLE IF NOT EXISTS loi.lan_thu_trang_thai (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        lan_thu_id uuid NOT NULL,
        viec_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        module text NOT NULL,
        phien_ban_dong bigint NOT NULL CHECK (phien_ban_dong>0),
        trang_thai text NOT NULL CHECK (trang_thai IN
            ('DANG_CHAY','XONG','LOI','DA_DUNG','GIAN_DOAN','CHUA_RO','CHO')),
        giu_den timestamptz,
        ket_qua_id uuid,
        ma_loi text CHECK (ma_loi ~ '^[A-Z][A-Z0-9_]{0,79}$'),
        ma_doi_chieu uuid,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (viec_id,phien_ban_dong),
        FOREIGN KEY (lan_thu_id,viec_id,phap_nhan_id,module)
            REFERENCES loi.lan_thu(id,viec_id,phap_nhan_id,module)
    );
    IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='loi.hang_viec'::regclass
        AND conname='hang_viec_lan_thu_fk') THEN
        ALTER TABLE loi.hang_viec ADD CONSTRAINT hang_viec_lan_thu_fk
            FOREIGN KEY (lan_thu_id,id,phap_nhan_id,module)
            REFERENCES loi.lan_thu(id,viec_id,phap_nhan_id,module);
    END IF;

    -- Thay dinh nghia tai migration MOI, khong sua checksum 003.
    -- Moi cua Core dang goi xac_minh_phien deu nhan hang rao lease nay.
    CREATE OR REPLACE FUNCTION loi.xac_minh_phien(
        p_ma text,p_module text,p_phap_nhan_id uuid,p_hanh_dong text,
        p_viec_id uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL
    ) RETURNS TABLE (phien_id uuid,nguoi_dung_id uuid,module text,
        phap_nhan_id uuid,hanh_dong text,viec_id uuid,the_he bigint,hieu_luc_den timestamptz)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT p.id,p.nguoi_dung_id,p.module,p.phap_nhan_id,p_hanh_dong,
            p.viec_id,p.the_he,p.hieu_luc_den
        FROM loi.phien_xac_thuc p
        JOIN loi.nguoi_dung n ON n.id=p.nguoi_dung_id
        JOIN loi.phap_nhan pn ON pn.id=p.phap_nhan_id
        WHERE p.ma_bam=sha256(convert_to(p_ma,'UTF8'))
            AND p.dang_nhap_csdl=session_user AND p.module=p_module AND p.phap_nhan_id=p_phap_nhan_id
            AND p_hanh_dong=ANY(p.pham_vi_hanh_dong)
            AND p.thu_hoi_luc IS NULL AND p.hieu_luc_den>clock_timestamp()
            AND n.trang_thai='HOAT_DONG' AND NOT n.mo_phong AND pn.trang_thai='HOAT_DONG'
            AND EXISTS (SELECT FROM loi.phan_quyen q WHERE q.nguoi_dung_id=p.nguoi_dung_id
                AND q.phap_nhan_id=p.phap_nhan_id AND p.module=ANY(q.module))
            AND ((p.loai<>'UY_NHIEM_VIEC' AND p_viec_id IS NULL AND p_the_he IS NULL)
                OR (p.loai='UY_NHIEM_VIEC' AND p.viec_id=p_viec_id AND p.the_he=p_the_he
                    AND NOT EXISTS (SELECT FROM loi.phien_xac_thuc moi
                        WHERE moi.viec_id=p.viec_id AND moi.the_he>p.the_he)
                    AND EXISTS (SELECT FROM loi.hang_viec v WHERE v.id=p.viec_id
                        AND v.phap_nhan_id=p.phap_nhan_id AND v.module=p.module
                        AND v.tao_boi=p.nguoi_dung_id AND v.the_he=p.the_he
                        AND v.trang_thai='DANG_CHAY' AND v.giu_den>clock_timestamp()
                        AND v.giu_phien_id=p.id)))
            AND (p.phien_goc_id IS NULL OR EXISTS (SELECT FROM loi.phien_xac_thuc g
                WHERE g.id=p.phien_goc_id AND g.loai='NGUOI_DUNG' AND g.nguoi_dung_id=p.nguoi_dung_id
                    AND g.module=p.module AND g.phap_nhan_id=p.phap_nhan_id
                    AND g.thu_hoi_luc IS NULL AND g.hieu_luc_den>clock_timestamp()
                    AND p.hieu_luc_den<=g.hieu_luc_den AND p.pham_vi_hanh_dong<@g.pham_vi_hanh_dong))
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_chi_core() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_loi') THEN
            RAISE EXCEPTION 'VIEC_CHI_CORE' USING ERRCODE='42501';
        END IF;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_ngu_canh(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid;
    BEGIN
        IF current_setting('transaction_isolation')<>'read committed' THEN
            RAISE EXCEPTION 'VIEC_CAN_READ_COMMITTED' USING ERRCODE='25000';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai IS NULL OR split_part(p_hd,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'VIEC_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM set_config('ktt.ma_phien',p_ma,true),set_config('ktt.module',p_module,true),
            set_config('ktt.phap_nhan_id',p_pn::text,true),set_config('ktt.hanh_dong',p_hd,true),
            set_config('ktt.viec_id',coalesce(p_viec::text,''),true),
            set_config('ktt.the_he',coalesce(p_the_he::text,''),true);
        RETURN ai;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_rls(p_pn uuid,p_module text,p_viec uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT coalesce(EXISTS (SELECT FROM loi.mtq_phien_rls() x
            WHERE x.phap_nhan_id=p_pn AND x.nguoi_dung_id=(SELECT tao_boi FROM loi.hang_viec WHERE id=p_viec)
                AND current_setting('ktt.module',true)=p_module
                AND (nullif(current_setting('ktt.viec_id',true),'') IS NULL
                    OR current_setting('ktt.viec_id',true)=p_viec::text)),false)
    $ham$;

    FOREACH bang IN ARRAY ARRAY['hang_viec','buoc_viec','lan_thu','lan_thu_trang_thai'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY',bang);
        -- Owner ham la trusted Core; runtime chi co policy doc theo phien da xac minh.
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid=format('loi.%I',bang)::regclass
            AND polname='viec_chu') THEN
            EXECUTE format('CREATE POLICY viec_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',bang,chu);
            EXECUTE format('CREATE POLICY viec_phien ON loi.%I FOR SELECT TO PUBLIC USING
                (loi.viec_rls(phap_nhan_id,module,%s))',bang,CASE WHEN bang='hang_viec' THEN 'id' ELSE 'viec_id' END);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC,%I,%I,%I',bang,chay,login,cai_dat);
        IF bang<>'hang_viec' AND NOT EXISTS (SELECT FROM pg_trigger
            WHERE tgrelid=format('loi.%I',bang)::regclass AND tgname='viec_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER viec_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE ON loi.%I
                FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
        END IF;
    END LOOP;

    CREATE OR REPLACE FUNCTION loi.viec_kiem_quyen(v loi.hang_viec,p_ma text,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL,p_moi boolean DEFAULT false) RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE q jsonb;
    BEGIN
        q:=loi.mtq_quyet_dinh_phien(p_ma,v.module,v.phap_nhan_id,v.hanh_dong,
            jsonb_build_object('bang',v.bang_tham_chieu,'id',v.tham_chieu_id),
            v.phien_ban_contract,'{}',p_viec,p_the_he);
        IF q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'VIEC_MTQ' USING ERRCODE='42501';
        END IF;
        IF p_moi THEN
            q:=loi.module_trang_thai(p_ma,v.module,v.phap_nhan_id,v.hanh_dong,v.module,p_viec,p_the_he);
            IF q->'cho_ghi' IS DISTINCT FROM 'true'::jsonb THEN
                RAISE EXCEPTION 'VIEC_CONG_TAC' USING ERRCODE='42501';
            END IF;
        END IF;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_dau(v loi.hang_viec,p_tt text,p_doi_chieu uuid DEFAULT NULL)
    RETURNS void LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        INSERT INTO loi.lan_thu_trang_thai(lan_thu_id,viec_id,phap_nhan_id,module,phien_ban_dong,
            trang_thai,giu_den,ket_qua_id,ma_loi,ma_doi_chieu)
        VALUES (v.lan_thu_id,v.id,v.phap_nhan_id,v.module,v.phien_ban_dong,
            p_tt,v.giu_den,v.ket_qua_id,v.ma_loi,p_doi_chieu)
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_tao(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text,p_phien_ban integer,p_khoa text,p_bang text,p_tham_chieu uuid,p_contract text,
        p_ngoai boolean DEFAULT false,p_an_toan boolean DEFAULT false,p_toi_da integer DEFAULT 3,
        p_thu_lai integer DEFAULT 60,p_giu_ngay integer DEFAULT NULL) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; cu loi.hang_viec; ai uuid; pham_vi text[];
    BEGIN
        PERFORM loi.viec_chi_core();
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd);
        IF p_loai IS NULL OR p_loai !~ '^[A-Z][A-Z0-9_-]{0,79}$' OR p_phien_ban IS NULL OR p_phien_ban<1
            OR p_khoa IS NULL OR length(p_khoa) NOT BETWEEN 1 AND 200 OR p_khoa<>btrim(p_khoa)
            OR p_bang IS NULL OR btrim(p_bang)='' OR p_tham_chieu IS NULL
            OR p_contract IS NULL OR btrim(p_contract)='' OR p_ngoai IS NULL OR p_an_toan IS NULL
            OR p_toi_da IS NULL OR p_toi_da NOT BETWEEN 1 AND 100
            OR p_thu_lai IS NULL OR p_thu_lai NOT BETWEEN 1 AND 86400
            OR (p_giu_ngay IS NOT NULL AND p_giu_ngay NOT BETWEEN 1 AND 36500)
            OR split_part(p_hd,':',3) NOT IN ('LAP','SUA','DUYET') THEN
            RAISE EXCEPTION 'VIEC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        v.module:=p_module; v.phap_nhan_id:=p_pn; v.hanh_dong:=p_hd;
        v.bang_tham_chieu:=p_bang; v.tham_chieu_id:=p_tham_chieu; v.phien_ban_contract:=p_contract;
        PERFORM loi.viec_kiem_quyen(v,p_ma,NULL,NULL,true);
        SELECT pham_vi_hanh_dong INTO pham_vi FROM loi.phien_xac_thuc
            WHERE ma_bam=sha256(convert_to(p_ma,'UTF8'));
        PERFORM pg_advisory_xact_lock(hashtextextended(p_pn::text||'|'||p_module||'|'||p_khoa,14));
        SELECT * INTO cu FROM loi.hang_viec
            WHERE phap_nhan_id=p_pn AND module=p_module AND khoa_chong_trung=p_khoa;
        IF FOUND THEN
            IF (cu.tao_boi,cu.loai,cu.phien_ban,cu.bang_tham_chieu,cu.tham_chieu_id,cu.hanh_dong,
                cu.phien_ban_contract,cu.co_tac_dong_ngoai,cu.thu_lai_an_toan,cu.toi_da_lan_thu,
                cu.thu_lai_giay,cu.giu_ngay) IS DISTINCT FROM
                (ai,p_loai,p_phien_ban,p_bang,p_tham_chieu,p_hd,p_contract,p_ngoai,p_an_toan,p_toi_da,
                p_thu_lai,p_giu_ngay) THEN
                RAISE EXCEPTION 'VIEC_KHOA_KHAC_NOI_DUNG' USING ERRCODE='23505';
            END IF;
            RETURN cu.id;
        END IF;
        INSERT INTO loi.hang_viec(phap_nhan_id,module,loai,phien_ban,khoa_chong_trung,bang_tham_chieu,
            tham_chieu_id,hanh_dong,phien_ban_contract,pham_vi_hanh_dong,co_tac_dong_ngoai,
            thu_lai_an_toan,toi_da_lan_thu,thu_lai_giay,giu_ngay,tao_boi)
        VALUES (p_pn,p_module,p_loai,p_phien_ban,p_khoa,p_bang,p_tham_chieu,p_hd,p_contract,pham_vi,
            p_ngoai,p_an_toan,p_toi_da,p_thu_lai,p_giu_ngay,ai) RETURNING * INTO v;
        -- Buoc XS-2 mac dinh; Workflow Runner G2-28 bo sung cac buoc/dependency.
        INSERT INTO loi.buoc_viec(viec_id,phap_nhan_id,module,ma_buoc)
            VALUES (v.id,p_pn,p_module,'THUC_HIEN');
        RETURN v.id;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_phuc_hoi(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_instance uuid DEFAULT NULL) RETURNS integer
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; ai uuid; n integer:=0;
    BEGIN
        PERFORM loi.viec_chi_core();
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd);
        FOR v IN SELECT * FROM loi.hang_viec WHERE phap_nhan_id=p_pn AND module=p_module
            AND tao_boi=ai AND hanh_dong=p_hd AND trang_thai='DANG_CHAY'
            AND ((p_instance IS NOT NULL AND giu_boi=p_instance)
                OR (p_instance IS NULL AND giu_den<=clock_timestamp()))
            ORDER BY giu_den,id LIMIT 100 FOR UPDATE SKIP LOCKED
        LOOP
            PERFORM loi.thu_hoi_uy_nhiem_viec(v.id,v.the_he);
            UPDATE loi.hang_viec SET trang_thai=CASE WHEN co_tac_dong_ngoai THEN 'CHUA_RO' ELSE 'GIAN_DOAN' END,
                giu_boi=NULL,giu_den=NULL,giu_phien_id=NULL,ma_loi='VIEC_GIAN_DOAN',
                phien_ban_dong=phien_ban_dong+1,cap_nhat_luc=clock_timestamp()
                WHERE id=v.id RETURNING * INTO v;
            PERFORM loi.viec_dau(v,'GIAN_DOAN');
            n:=n+1;
        END LOOP;
        RETURN n;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_nhan(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_instance uuid,p_ma_moi text,p_login text,p_giay integer DEFAULT 120) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; ai uuid; phien uuid; buoc uuid; lan uuid:=gen_random_uuid();
        den timestamptz; pham_vi text[];
    BEGIN
        PERFORM loi.viec_chi_core();
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd);
        IF p_instance IS NULL OR p_giay IS NULL OR p_giay NOT BETWEEN 1 AND 3600
            OR p_ma_moi IS NULL OR p_ma_moi !~ '^[A-Za-z0-9_-]{43,128}$'
            OR p_login IS NULL OR (p_login<>session_user::text AND p_login<>
                regexp_replace(current_user::text,'vai_doi_cau_truc_loi$','dang_nhap_mod_'||p_module)) THEN
            RAISE EXCEPTION 'VIEC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        PERFORM loi.viec_phuc_hoi(p_ma,p_module,p_pn,p_hd);
        SELECT * INTO v FROM loi.hang_viec WHERE phap_nhan_id=p_pn AND module=p_module
            AND tao_boi=ai AND hanh_dong=p_hd AND trang_thai='CHO' AND NOT yeu_cau_dung
            AND so_lan_thu<toi_da_lan_thu AND thu_lai_sau<=clock_timestamp()
            ORDER BY thu_lai_sau,tao_luc,id LIMIT 1 FOR UPDATE SKIP LOCKED;
        IF NOT FOUND THEN RETURN NULL; END IF;
        PERFORM loi.viec_kiem_quyen(v,p_ma,NULL,NULL,true);
        SELECT ARRAY(SELECT unnest(v.pham_vi_hanh_dong) INTERSECT SELECT unnest(p.pham_vi_hanh_dong))
            INTO pham_vi FROM loi.phien_xac_thuc p WHERE p.ma_bam=sha256(convert_to(p_ma,'UTF8'));
        den:=clock_timestamp()+make_interval(secs=>p_giay);
        phien:=loi.cap_phien(p_ma_moi,ai,p_module,p_pn,p_login,pham_vi,den,'UY_NHIEM_VIEC',NULL,v.id,v.the_he+1);
        SELECT id INTO STRICT buoc FROM loi.buoc_viec WHERE viec_id=v.id AND ma_buoc='THUC_HIEN';
        INSERT INTO loi.lan_thu(id,buoc_viec_id,viec_id,phap_nhan_id,module,so_lan,the_he,instance_id,phien_id)
            VALUES (lan,buoc,v.id,p_pn,p_module,v.so_lan_thu+1,v.the_he+1,p_instance,phien);
        UPDATE loi.hang_viec SET trang_thai='DANG_CHAY',so_lan_thu=so_lan_thu+1,the_he=the_he+1,
            giu_boi=p_instance,giu_den=den,giu_phien_id=phien,lan_thu_id=lan,ma_loi=NULL,
            phien_ban_dong=phien_ban_dong+1,cap_nhat_luc=clock_timestamp()
            WHERE id=v.id RETURNING * INTO v;
        PERFORM loi.viec_dau(v,'DANG_CHAY');
        RETURN jsonb_build_object('viec_id',v.id,'buoc_viec_id',buoc,'lan_thu_id',lan,
            'phap_nhan_id',p_pn,'module',p_module,'hanh_dong',p_hd,'instance_id',p_instance,
            'the_he',v.the_he,'giu_den',v.giu_den,'row_version',v.phien_ban_dong::text);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_giu(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_instance uuid,p_the_he bigint) RETURNS loi.hang_viec
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; ai uuid;
    BEGIN
        -- Khoa truoc doc lai quyen/lease, giu khoa den khi caller commit/rollback.
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT * INTO v FROM loi.hang_viec WHERE id=p_viec AND phap_nhan_id=p_pn AND module=p_module FOR UPDATE;
        IF NOT FOUND OR v.trang_thai<>'DANG_CHAY' OR v.the_he IS DISTINCT FROM p_the_he
            OR v.giu_boi IS DISTINCT FROM p_instance OR v.giu_den<=clock_timestamp()
            OR NOT EXISTS (SELECT FROM loi.phien_xac_thuc WHERE id=v.giu_phien_id
                AND ma_bam=sha256(convert_to(p_ma,'UTF8'))) THEN
            RAISE EXCEPTION 'VIEC_MAT_LEASE' USING ERRCODE='40001';
        END IF;
        -- Tuan tu hoa voi thu_hoi_phien: khong gia han lai ma vua bi thu hoi.
        PERFORM 1 FROM loi.phien_xac_thuc WHERE id=v.giu_phien_id FOR UPDATE;
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai<>v.tao_boi OR p_hd<>v.hanh_dong THEN
            RAISE EXCEPTION 'VIEC_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM loi.viec_kiem_quyen(v,p_ma,p_viec,p_the_he);
        IF v.giu_den<=clock_timestamp() THEN
            RAISE EXCEPTION 'VIEC_MAT_LEASE' USING ERRCODE='40001';
        END IF;
        RETURN v;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_gia_han(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_instance uuid,p_the_he bigint,p_giay integer DEFAULT 120) RETURNS timestamptz
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; den timestamptz;
    BEGIN
        IF p_giay IS NULL OR p_giay NOT BETWEEN 1 AND 3600 THEN
            RAISE EXCEPTION 'VIEC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        v:=loi.viec_giu(p_ma,p_module,p_pn,p_hd,p_viec,p_instance,p_the_he);
        den:=clock_timestamp()+make_interval(secs=>p_giay);
        UPDATE loi.phien_xac_thuc SET hieu_luc_den=den WHERE id=v.giu_phien_id;
        UPDATE loi.hang_viec SET giu_den=den,phien_ban_dong=phien_ban_dong+1,cap_nhat_luc=clock_timestamp()
            WHERE id=v.id AND giu_den>clock_timestamp() RETURNING * INTO v;
        IF NOT FOUND THEN RAISE EXCEPTION 'VIEC_MAT_LEASE' USING ERRCODE='40001'; END IF;
        PERFORM loi.viec_dau(v,'DANG_CHAY');
        RETURN den;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_ket_thuc(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_instance uuid,p_the_he bigint,p_tt text,p_ket_qua uuid DEFAULT NULL,
        p_ma_loi text DEFAULT NULL) RETURNS boolean
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; tt text:=p_tt;
    BEGIN
        v:=loi.viec_giu(p_ma,p_module,p_pn,p_hd,p_viec,p_instance,p_the_he);
        IF tt IS NULL OR tt NOT IN ('XONG','LOI','DA_DUNG','CHUA_RO','CHO')
            OR (tt='DA_DUNG' AND NOT v.yeu_cau_dung)
            OR (tt='CHO' AND NOT v.thu_lai_an_toan)
            OR (tt IN ('LOI','CHUA_RO','CHO') AND p_ma_loi IS NULL)
            OR (p_ma_loi IS NOT NULL AND p_ma_loi !~ '^[A-Z][A-Z0-9_]{0,79}$')
            OR (tt<>'XONG' AND p_ket_qua IS NOT NULL) THEN
            RAISE EXCEPTION 'VIEC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        IF tt='CHO' THEN
            tt:=CASE WHEN v.yeu_cau_dung THEN 'DA_DUNG'
                WHEN v.so_lan_thu>=v.toi_da_lan_thu THEN 'LOI' ELSE 'CHO' END;
        END IF;
        UPDATE loi.hang_viec SET trang_thai=tt,giu_boi=NULL,giu_den=NULL,giu_phien_id=NULL,
            ket_qua_id=p_ket_qua,ma_loi=p_ma_loi,phien_ban_dong=phien_ban_dong+1,
            thu_lai_sau=clock_timestamp()+make_interval(secs=>thu_lai_giay),cap_nhat_luc=clock_timestamp(),
            ket_thuc_luc=CASE WHEN tt IN ('XONG','LOI','DA_DUNG') THEN clock_timestamp() END
            WHERE id=v.id AND giu_den>clock_timestamp() RETURNING * INTO v;
        IF NOT FOUND THEN RAISE EXCEPTION 'VIEC_MAT_LEASE' USING ERRCODE='40001'; END IF;
        PERFORM loi.viec_dau(v,CASE WHEN p_tt='CHO' THEN 'LOI' ELSE tt END);
        PERFORM loi.thu_hoi_uy_nhiem_viec(v.id,v.the_he);
        RETURN true;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.viec_yeu_cau_dung(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_phien_ban bigint) RETURNS boolean
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; ai uuid;
    BEGIN
        PERFORM loi.viec_chi_core();
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd);
        SELECT * INTO v FROM loi.hang_viec WHERE id=p_viec AND phap_nhan_id=p_pn
            AND module=p_module AND tao_boi=ai AND hanh_dong=p_hd FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'VIEC_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        PERFORM loi.viec_kiem_quyen(v,p_ma);
        IF v.phien_ban_dong IS DISTINCT FROM p_phien_ban THEN
            RAISE EXCEPTION 'VIEC_CAS' USING ERRCODE='40001';
        END IF;
        IF v.trang_thai IN ('XONG','LOI','DA_DUNG') THEN RETURN false; END IF;
        -- CHUA_RO van cho doi chieu; huy khong xoa dau tac dong chua ro.
        UPDATE loi.hang_viec SET yeu_cau_dung=true,phien_ban_dong=phien_ban_dong+1,
            trang_thai=CASE WHEN trang_thai IN ('CHO','GIAN_DOAN') THEN 'DA_DUNG' ELSE trang_thai END,
            ket_thuc_luc=CASE WHEN trang_thai IN ('CHO','GIAN_DOAN') THEN clock_timestamp() END,
            cap_nhat_luc=clock_timestamp() WHERE id=v.id RETURNING * INTO v;
        IF v.lan_thu_id IS NOT NULL THEN PERFORM loi.viec_dau(v,v.trang_thai); END IF;
        RETURN true;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_xep_lai(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_phien_ban bigint,p_doi_chieu uuid) RETURNS boolean
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec; ai uuid;
    BEGIN
        -- Core chi goi sau doi chieu tac dong/bien nhan; UUID la tham chieu bang chung.
        PERFORM loi.viec_chi_core();
        ai:=loi.viec_ngu_canh(p_ma,p_module,p_pn,p_hd);
        SELECT * INTO v FROM loi.hang_viec WHERE id=p_viec AND phap_nhan_id=p_pn
            AND module=p_module AND tao_boi=ai AND hanh_dong=p_hd FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'VIEC_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        PERFORM loi.viec_kiem_quyen(v,p_ma,NULL,NULL,true);
        IF v.phien_ban_dong IS DISTINCT FROM p_phien_ban THEN
            RAISE EXCEPTION 'VIEC_CAS' USING ERRCODE='40001';
        END IF;
        IF p_doi_chieu IS NULL OR NOT v.thu_lai_an_toan OR v.yeu_cau_dung
            OR v.trang_thai NOT IN ('GIAN_DOAN','CHUA_RO') OR v.so_lan_thu>=v.toi_da_lan_thu THEN
            RAISE EXCEPTION 'VIEC_CAN_DOI_CHIEU' USING ERRCODE='22023';
        END IF;
        PERFORM loi.thu_hoi_uy_nhiem_viec(v.id,v.the_he);
        UPDATE loi.hang_viec SET trang_thai='CHO',phien_ban_dong=phien_ban_dong+1,
            thu_lai_sau=clock_timestamp()+make_interval(secs=>thu_lai_giay),cap_nhat_luc=clock_timestamp()
            WHERE id=v.id RETURNING * INTO v;
        PERFORM loi.viec_dau(v,'CHO',p_doi_chieu);
        RETURN true;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.viec_trang_thai_lease(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_instance uuid,p_the_he bigint) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE v loi.hang_viec;
    BEGIN
        v:=loi.viec_giu(p_ma,p_module,p_pn,p_hd,p_viec,p_instance,p_the_he);
        RETURN jsonb_build_object('con_giu',true,'yeu_cau_dung',v.yeu_cau_dung,'giu_den',v.giu_den,
            'row_version',v.phien_ban_dong::text,'buoc_viec_id',
            (SELECT buoc_viec_id FROM loi.lan_thu WHERE id=v.lan_thu_id),'lan_thu_id',v.lan_thu_id);
    END;
    $ham$;

    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname LIKE 'viec\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I,%I',ham.ck,chay,login,cai_dat);
        IF ham.proname IN ('viec_tao','viec_nhan','viec_gia_han','viec_ket_thuc','viec_phuc_hoi',
            'viec_yeu_cau_dung','viec_xep_lai','viec_trang_thai_lease','viec_rls') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        END IF;
        -- Policy doc can quyen goi, khong cap SELECT bang hoac quyen cac helper khac.
        IF ham.proname='viec_rls' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,chay);
        END IF;
    END LOOP;
    -- Module Manager chi cap EXECUTE heartbeat/ket_thuc/trang_thai_lease va viec_rls
    -- dung module, khong cap tao/nhan/phuc_hoi; engine di qua Core.
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
