-- G2-09: metadata bat bien; bytes va xac minh instance/lease do cac lat sau noi.
-- Core la cua ghi duy nhat. Module chi gui tham chieu qua dich vu Core.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
    chu_loi text := tt || 'vai_doi_cau_truc_loi';
    chay text := tt || 'vai_chay_loi_tai_lieu';
    login text := tt || 'dang_nhap_loi';
    vai_cu text := current_setting('role');
    duong_cu text := current_setting('search_path');
    bang text;
    ham record;
BEGIN
    IF (tt <> '' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(chu) > 63 OR (tt <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-09: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname='loi_tai_lieu'
                   AND pg_get_userbyid(nspowner)=chu)
       OR to_regprocedure('loi.module_trang_thai(text,text,uuid,text,text,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-09: Can lead, ap G2-01..08 truoc';
    END IF;
    -- Quyen lien khoi chi cho owner cac cua hep, khong trao membership owner.
    EXECUTE format('SET LOCAL ROLE %I',chu_loi);
    EXECUTE format('GRANT USAGE ON SCHEMA loi TO %I',chu);
    EXECUTE format('GRANT REFERENCES ON loi.phap_nhan, loi.nguoi_dung, loi.phan_quyen,
        loi.module_danh_muc, loi.phien_ban_module, loi.engine_dinh_nghia,
        loi.dang_ky_contract TO %I',chu);
    FOR ham IN SELECT oid::regprocedure AS ck FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname IN
        ('xac_minh_phien','mtq_phien_rls','mtq_quyet_dinh_phien',
         'module_trang_thai','ghi_kiem_toan','chan_sua_kiem_toan') LOOP
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,chu);
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog, pg_temp',true);

    CREATE TABLE IF NOT EXISTS loi_tai_lieu.tai_lieu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai text NOT NULL CHECK (btrim(loai) <> ''),
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 255),
        bang_doi_tuong text NOT NULL CHECK (btrim(bang_doi_tuong) <> ''),
        doi_tuong_id uuid NOT NULL,
        phien_ban_contract text NOT NULL CHECK (btrim(phien_ban_contract) <> ''),
        trang_thai text NOT NULL DEFAULT 'NHAP' CHECK (trang_thai='NHAP'),
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong=1),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.tep_goc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        tai_lieu_id uuid NOT NULL,
        ten_tep text NOT NULL CHECK (length(ten_tep) BETWEEN 1 AND 255),
        ma_bam text NOT NULL CHECK (ma_bam ~ '^[0-9a-f]{64}$'),
        kich_thuoc bigint NOT NULL CHECK (kich_thuoc BETWEEN 0 AND 9007199254740991),
        mime text NOT NULL CHECK (mime ~ '^[A-Za-z0-9!#$&^_.+\-]+/[A-Za-z0-9!#$&^_.+\-]+$'),
        khoa_luu_tru text NOT NULL CHECK (khoa_luu_tru ~ '^[a-z0-9][a-z0-9_./-]*$'
            AND khoa_luu_tru !~ '(^|/)\.\.?(/|$)'),
        kiem_hash_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        het_han_luc timestamptz CHECK(het_han_luc IS NULL OR isfinite(het_han_luc)),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(id,phap_nhan_id), UNIQUE(id,tai_lieu_id,phap_nhan_id),
        FOREIGN KEY(tai_lieu_id,phap_nhan_id) REFERENCES loi_tai_lieu.tai_lieu(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.tai_lieu_tep (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL,
        tai_lieu_id uuid NOT NULL, tep_id uuid NOT NULL,
        bien_the text NOT NULL CHECK (bien_the IN ('goc','ocr','da_che','noi_dung','phan_hoi_nguon')),
        so_phien_ban bigint NOT NULL CHECK (so_phien_ban > 0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(tai_lieu_id,bien_the,so_phien_ban), UNIQUE(id,phap_nhan_id),
        FOREIGN KEY(tai_lieu_id,phap_nhan_id) REFERENCES loi_tai_lieu.tai_lieu(id,phap_nhan_id),
        FOREIGN KEY(tep_id,tai_lieu_id,phap_nhan_id)
            REFERENCES loi_tai_lieu.tep_goc(id,tai_lieu_id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.quyen_tai_lieu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL,
        tai_lieu_id uuid NOT NULL, nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        bien_the text NOT NULL CHECK (bien_the IN ('*','goc','ocr','da_che','noi_dung','phan_hoi_nguon')),
        hanh_dong text NOT NULL CHECK (hanh_dong='XEM'),
        so_phien_ban bigint NOT NULL CHECK (so_phien_ban > 0),
        cho_phep boolean NOT NULL, hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(),
        hieu_luc_den timestamptz,
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR hieu_luc_den > hieu_luc_tu),
        CHECK(hieu_luc_den IS NULL OR isfinite(hieu_luc_den)),
        UNIQUE(tai_lieu_id,nguoi_dung_id,bien_the,hanh_dong,so_phien_ban),
        FOREIGN KEY(tai_lieu_id,phap_nhan_id) REFERENCES loi_tai_lieu.tai_lieu(id,phap_nhan_id),
        FOREIGN KEY(nguoi_dung_id,phap_nhan_id) REFERENCES loi.phan_quyen(nguoi_dung_id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.ket_qua_xu_ly (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL,
        tai_lieu_id uuid NOT NULL, goc_id uuid NOT NULL, revision bigint NOT NULL CHECK(revision > 0),
        tep_id uuid, bien_the text NOT NULL CHECK (bien_the IN ('goc','ocr','da_che','noi_dung','phan_hoi_nguon')),
        ma_contract text NOT NULL, phien_ban_contract text NOT NULL,
        module text NOT NULL, phien_ban_module text NOT NULL,
        engine_id uuid REFERENCES loi.engine_dinh_nghia(id),
        ham text NOT NULL CHECK (btrim(ham) <> ''), phien_ban_ham text NOT NULL CHECK (btrim(phien_ban_ham) <> ''),
        viec_id uuid, buoc_id uuid, lan_thu_id uuid, the_he bigint,
        trang_thai text NOT NULL CHECK(trang_thai IN ('cho','dang_xu_ly','thanh_cong','loi')),
        ly_do text NOT NULL,
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK((viec_id IS NULL AND buoc_id IS NULL AND lan_thu_id IS NULL AND the_he IS NULL)
            OR (viec_id IS NOT NULL AND buoc_id IS NOT NULL AND lan_thu_id IS NOT NULL
                AND the_he IS NOT NULL AND the_he > 0)),
        UNIQUE(id,phap_nhan_id), UNIQUE(id,tai_lieu_id,phap_nhan_id), UNIQUE(goc_id,revision),
        FOREIGN KEY(tai_lieu_id,phap_nhan_id) REFERENCES loi_tai_lieu.tai_lieu(id,phap_nhan_id),
        FOREIGN KEY(goc_id,tai_lieu_id,phap_nhan_id)
            REFERENCES loi_tai_lieu.ket_qua_xu_ly(id,tai_lieu_id,phap_nhan_id),
        FOREIGN KEY(tep_id,tai_lieu_id,phap_nhan_id)
            REFERENCES loi_tai_lieu.tep_goc(id,tai_lieu_id,phap_nhan_id),
        FOREIGN KEY(ma_contract,phien_ban_contract) REFERENCES loi.dang_ky_contract(ma,phien_ban),
        FOREIGN KEY(module,phien_ban_module) REFERENCES loi.phien_ban_module(module,so_phien_ban)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.nguon_ket_qua (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL,
        ket_qua_id uuid NOT NULL, tep_id uuid, ket_qua_nguon_id uuid,
        ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        revision_nguon bigint CHECK(revision_nguon > 0),
        trang integer CHECK(trang > 0), dinh_vi text, trich_dan text,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(num_nonnulls(tep_id,ket_qua_nguon_id)=1),
        CHECK((ket_qua_nguon_id IS NULL) = (revision_nguon IS NULL)),
        CHECK(ket_qua_nguon_id IS DISTINCT FROM ket_qua_id),
        FOREIGN KEY(ket_qua_id,phap_nhan_id) REFERENCES loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id),
        FOREIGN KEY(tep_id,phap_nhan_id) REFERENCES loi_tai_lieu.tep_goc(id,phap_nhan_id),
        FOREIGN KEY(ket_qua_nguon_id,phap_nhan_id) REFERENCES loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id)
    );
    -- Duyet va cong bo la su kien rieng; khong sua ket qua/noi dung cu.
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.ket_qua_duyet (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL, ket_qua_id uuid NOT NULL,
        phien_ban_dong bigint NOT NULL CHECK(phien_ban_dong > 0),
        trang_thai_duyet text NOT NULL CHECK(trang_thai_duyet IN ('chua_duyet','da_duyet','tu_choi')),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(ket_qua_id,phien_ban_dong),
        FOREIGN KEY(ket_qua_id,phap_nhan_id) REFERENCES loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.ket_qua_cong_bo (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL, ket_qua_id uuid NOT NULL UNIQUE,
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        FOREIGN KEY(ket_qua_id,phap_nhan_id) REFERENCES loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id)
    );
    FOREACH bang IN ARRAY ARRAY['tai_lieu','tep_goc','tai_lieu_tep','quyen_tai_lieu',
        'ket_qua_xu_ly','nguon_ket_qua','ket_qua_duyet','ket_qua_cong_bo'] LOOP
        IF (SELECT pg_get_userbyid(relowner) <> chu FROM pg_class
            WHERE oid=format('loi_tai_lieu.%I',bang)::regclass) THEN
            RAISE EXCEPTION 'G2-09: Can lead, sai owner';
        END IF;
        EXECUTE format('ALTER TABLE loi_tai_lieu.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE loi_tai_lieu.%I FORCE ROW LEVEL SECURITY',bang);
        EXECUTE format('REVOKE ALL ON loi_tai_lieu.%I FROM PUBLIC, %I, %I',bang,chay,login);
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid=format('loi_tai_lieu.%I',bang)::regclass
                       AND polname='tai_lieu_phien') THEN
            EXECUTE format('CREATE POLICY tai_lieu_phien ON loi_tai_lieu.%I TO %I
                USING (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))
                WITH CHECK (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))',bang,chu);
        END IF;
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=format('loi_tai_lieu.%I',bang)::regclass
                       AND tgname='tai_lieu_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER tai_lieu_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE
                ON loi_tai_lieu.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
        END IF;
    END LOOP;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.ngu_canh(p_ma text,p_module text,p_pn uuid,
        p_hd text,p_viec uuid,p_the_he bigint) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid;
    BEGIN
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai IS NULL OR split_part(p_hd,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM set_config('ktt.ma_phien',p_ma,true), set_config('ktt.module',p_module,true),
            set_config('ktt.phap_nhan_id',p_pn::text,true), set_config('ktt.hanh_dong',p_hd,true),
            set_config('ktt.viec_id',coalesce(p_viec::text,''),true),
            set_config('ktt.the_he',coalesce(p_the_he::text,''),true);
        RETURN ai;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.kiem_quyen(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_doi_tuong jsonb,p_contract text,p_can text,p_viec uuid,p_the_he bigint) RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE q jsonb; co jsonb;
    BEGIN
        q := loi.mtq_quyet_dinh_phien(p_ma,p_module,p_pn,p_hd,p_doi_tuong,p_contract,'{}',p_viec,p_the_he);
        IF q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'TAI_LIEU_MTQ' USING ERRCODE='42501';
        END IF;
        co := loi.module_trang_thai(p_ma,p_module,p_pn,p_hd,p_module,p_viec,p_the_he);
        IF co->p_can IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'TAI_LIEU_CONG_TAC' USING ERRCODE='42501';
        END IF;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.duoc_xem_noi_dung(p_tai_lieu uuid,p_ai uuid,p_bien_the text)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT coalesce((SELECT q.cho_phep AND q.hieu_luc_tu<=statement_timestamp()
            AND (q.hieu_luc_den IS NULL OR q.hieu_luc_den>statement_timestamp())
            FROM loi_tai_lieu.quyen_tai_lieu q WHERE q.tai_lieu_id=p_tai_lieu AND q.nguoi_dung_id=p_ai
                AND q.bien_the IN ('*',p_bien_the) AND q.hanh_dong='XEM'
            ORDER BY (q.bien_the=p_bien_the) DESC,q.so_phien_ban DESC LIMIT 1),false)
    $ham$;

    -- Kiem quyen hien hanh ca ket qua va chuoi nguon, khong dung quyen luc tao.
    CREATE OR REPLACE FUNCTION loi_tai_lieu.duoc_xem_ket_qua(p_ket_qua uuid,p_ai uuid)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        WITH RECURSIVE tap AS (
            SELECT k.id,k.tai_lieu_id,k.bien_the FROM loi_tai_lieu.ket_qua_xu_ly k WHERE k.id=p_ket_qua
            UNION
            SELECT s.id,s.tai_lieu_id,s.bien_the FROM tap k
                JOIN loi_tai_lieu.nguon_ket_qua n ON n.ket_qua_id=k.id
                JOIN loi_tai_lieu.ket_qua_xu_ly s ON s.id=n.ket_qua_nguon_id
        )
        SELECT EXISTS(SELECT FROM tap WHERE id=p_ket_qua) AND NOT EXISTS(
            SELECT FROM tap k WHERE NOT loi_tai_lieu.duoc_xem_noi_dung(k.tai_lieu_id,p_ai,k.bien_the)
                OR EXISTS(SELECT FROM loi_tai_lieu.nguon_ket_qua n WHERE n.ket_qua_id=k.id
                    AND n.tep_id IS NOT NULL AND NOT EXISTS(
                        SELECT FROM loi_tai_lieu.tai_lieu_tep b WHERE b.tep_id=n.tep_id
                            AND loi_tai_lieu.duoc_xem_noi_dung(b.tai_lieu_id,p_ai,b.bien_the))))
    $ham$;

    -- Nguon/ham/engine chi den tu Core da xac minh; khong GRANT cua nay cho module.
    -- G2-10/14/16 noi doi chieu bytes va instance/lease truoc khi goi.
    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_metadata(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text,p_tai_lieu uuid,p_du_lieu jsonb,p_request uuid,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; tl loi_tai_lieu.tai_lieu; kq loi_tai_lieu.ket_qua_xu_ly;
        nguon jsonb; tep loi_tai_lieu.tep_goc; kq_nguon loi_tai_lieu.ket_qua_xu_ly;
        moi uuid := gen_random_uuid(); goc uuid; ban bigint; muc text; khoa text[];
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi_tai_lieu$','dang_nhap_loi') THEN
            RAISE EXCEPTION 'TAI_LIEU_CHI_CORE' USING ERRCODE='42501';
        END IF;
        muc := split_part(p_hd,':',3);
        IF p_request IS NULL OR p_module='core' OR p_tai_lieu IS NULL
           OR jsonb_typeof(p_du_lieu) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END IF;
        CASE p_loai
          WHEN 'tai_lieu' THEN khoa := ARRAY['loai','ten','doi_tuong','phien_ban_contract'];
          WHEN 'tep' THEN khoa := ARRAY['ten_tep','sha256','kich_thuoc','mime','khoa_luu_tru','het_han_luc'];
          WHEN 'bien_the' THEN khoa := ARRAY['tep_id','bien_the','revision_truoc'];
          WHEN 'quyen' THEN khoa := ARRAY['nguoi_dung_id','bien_the','cho_phep','hieu_luc_den','revision_truoc'];
          WHEN 'ket_qua' THEN khoa := ARRAY['tep_id','bien_the','ma_contract','phien_ban_contract',
              'phien_ban_module','engine_id','ham','phien_ban_ham','buoc_id','lan_thu_id',
              'trang_thai','ly_do','goc_id','revision_truoc','nguon'];
          WHEN 'duyet' THEN khoa := ARRAY['ket_qua_id','row_version','trang_thai_duyet'];
          WHEN 'cong_bo' THEN khoa := ARRAY['ket_qua_id'];
          ELSE RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END CASE;
        IF p_du_lieu - khoa <> '{}'::jsonb OR muc IS NULL OR
            (p_loai IN ('quyen','duyet','cong_bo') AND muc <> 'DUYET') OR
            (p_loai NOT IN ('quyen','duyet','cong_bo') AND muc NOT IN ('LAP','SUA')) THEN
            RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END IF;
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        PERFORM pg_advisory_xact_lock(hashtextextended('tai_lieu|' || p_tai_lieu::text,9));
        IF p_loai='tai_lieu' THEN
            PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,p_du_lieu->'doi_tuong',
                p_du_lieu->>'phien_ban_contract','cho_ghi',p_viec,p_the_he);
            moi := p_tai_lieu;
            INSERT INTO loi_tai_lieu.tai_lieu(id,phap_nhan_id,module,loai,ten,bang_doi_tuong,
                doi_tuong_id,phien_ban_contract,tao_boi) VALUES
                (moi,p_pn,p_module,p_du_lieu->>'loai',p_du_lieu->>'ten',p_du_lieu->'doi_tuong'->>'bang',
                 (p_du_lieu->'doi_tuong'->>'id')::uuid,p_du_lieu->>'phien_ban_contract',ai);
            INSERT INTO loi_tai_lieu.quyen_tai_lieu(phap_nhan_id,tai_lieu_id,nguoi_dung_id,
                bien_the,hanh_dong,so_phien_ban,cho_phep,tao_boi) VALUES(p_pn,moi,ai,'*','XEM',1,true,ai);
        ELSE
            SELECT * INTO tl FROM loi_tai_lieu.tai_lieu WHERE id=p_tai_lieu AND phap_nhan_id=p_pn;
            IF tl.id IS NULL OR tl.module <> p_module THEN
                RAISE EXCEPTION 'TAI_LIEU_KHONG_THAY' USING ERRCODE='42501';
            END IF;
            PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,
                jsonb_build_object('bang',tl.bang_doi_tuong,'id',tl.doi_tuong_id),tl.phien_ban_contract,
                CASE WHEN p_loai='cong_bo' THEN 'cong_bo_chinh_thuc' ELSE 'cho_ghi' END,p_viec,p_the_he);
            CASE p_loai
            WHEN 'tep' THEN
                INSERT INTO loi_tai_lieu.tep_goc(id,phap_nhan_id,tai_lieu_id,ten_tep,ma_bam,kich_thuoc,
                    mime,khoa_luu_tru,het_han_luc,tao_boi) VALUES(moi,p_pn,p_tai_lieu,
                    p_du_lieu->>'ten_tep',p_du_lieu->>'sha256',(p_du_lieu->>'kich_thuoc')::bigint,
                    p_du_lieu->>'mime',p_du_lieu->>'khoa_luu_tru',(p_du_lieu->>'het_han_luc')::timestamptz,ai);
            WHEN 'bien_the' THEN
                SELECT coalesce(max(so_phien_ban),0) INTO ban FROM loi_tai_lieu.tai_lieu_tep
                    WHERE tai_lieu_id=p_tai_lieu AND bien_the=p_du_lieu->>'bien_the';
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.tai_lieu_tep(id,phap_nhan_id,tai_lieu_id,tep_id,bien_the,so_phien_ban,tao_boi)
                    VALUES(moi,p_pn,p_tai_lieu,(p_du_lieu->>'tep_id')::uuid,p_du_lieu->>'bien_the',ban+1,ai);
            WHEN 'quyen' THEN
                SELECT coalesce(max(so_phien_ban),0) INTO ban FROM loi_tai_lieu.quyen_tai_lieu
                    WHERE tai_lieu_id=p_tai_lieu AND nguoi_dung_id=(p_du_lieu->>'nguoi_dung_id')::uuid
                        AND bien_the=p_du_lieu->>'bien_the' AND hanh_dong='XEM';
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.quyen_tai_lieu(id,phap_nhan_id,tai_lieu_id,nguoi_dung_id,bien_the,
                    hanh_dong,so_phien_ban,cho_phep,hieu_luc_den,tao_boi) VALUES(moi,p_pn,p_tai_lieu,
                    (p_du_lieu->>'nguoi_dung_id')::uuid,p_du_lieu->>'bien_the','XEM',ban+1,
                    (p_du_lieu->>'cho_phep')::boolean,(p_du_lieu->>'hieu_luc_den')::timestamptz,ai);
            WHEN 'ket_qua' THEN
                IF p_du_lieu->>'tep_id' IS NOT NULL AND NOT EXISTS (
                    SELECT FROM loi_tai_lieu.tai_lieu_tep WHERE tai_lieu_id=p_tai_lieu
                        AND tep_id=(p_du_lieu->>'tep_id')::uuid AND bien_the=p_du_lieu->>'bien_the') THEN
                    RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                END IF;
                goc := coalesce((p_du_lieu->>'goc_id')::uuid,moi);
                SELECT coalesce(max(revision),0) INTO ban FROM loi_tai_lieu.ket_qua_xu_ly
                    WHERE goc_id=goc AND tai_lieu_id=p_tai_lieu;
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint OR
                    (ban=0 AND goc<>moi) THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id,tai_lieu_id,goc_id,revision,
                    tep_id,bien_the,ma_contract,phien_ban_contract,module,phien_ban_module,engine_id,
                    ham,phien_ban_ham,viec_id,buoc_id,lan_thu_id,the_he,trang_thai,ly_do,tao_boi)
                VALUES(moi,p_pn,p_tai_lieu,goc,ban+1,(p_du_lieu->>'tep_id')::uuid,p_du_lieu->>'bien_the',
                    p_du_lieu->>'ma_contract',p_du_lieu->>'phien_ban_contract',p_module,
                    p_du_lieu->>'phien_ban_module',(p_du_lieu->>'engine_id')::uuid,
                    p_du_lieu->>'ham',p_du_lieu->>'phien_ban_ham',p_viec,(p_du_lieu->>'buoc_id')::uuid,
                    (p_du_lieu->>'lan_thu_id')::uuid,p_the_he,p_du_lieu->>'trang_thai',p_du_lieu->>'ly_do',ai);
                IF jsonb_typeof(p_du_lieu->'nguon') IS DISTINCT FROM 'array' THEN
                    RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                END IF;
                FOR nguon IN SELECT value FROM jsonb_array_elements(p_du_lieu->'nguon') LOOP
                    IF jsonb_typeof(nguon) IS DISTINCT FROM 'object' OR nguon - ARRAY[
                        'tep_id','ket_qua_id','revision','sha256','trang','dinh_vi','trich_dan'] <> '{}'::jsonb
                        OR num_nonnulls(nguon->>'tep_id',nguon->>'ket_qua_id') <> 1 THEN
                        RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                    END IF;
                    IF nguon->>'ket_qua_id' IS NOT NULL THEN
                        SELECT * INTO kq_nguon FROM loi_tai_lieu.ket_qua_xu_ly
                            WHERE id=(nguon->>'ket_qua_id')::uuid AND phap_nhan_id=p_pn;
                        IF kq_nguon.id IS NULL OR kq_nguon.id=moi OR kq_nguon.revision IS DISTINCT FROM
                            (nguon->>'revision')::bigint OR NOT loi_tai_lieu.duoc_xem_noi_dung(
                                p_tai_lieu,ai,kq_nguon.bien_the) THEN
                            RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                        END IF;
                        SELECT * INTO tep FROM loi_tai_lieu.tep_goc WHERE id=kq_nguon.tep_id;
                    ELSE
                        SELECT * INTO tep FROM loi_tai_lieu.tep_goc WHERE id=(nguon->>'tep_id')::uuid;
                        IF NOT EXISTS (SELECT FROM loi_tai_lieu.tai_lieu_tep b WHERE b.tep_id=tep.id
                            AND loi_tai_lieu.duoc_xem_noi_dung(p_tai_lieu,ai,b.bien_the)) THEN
                            RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
                        END IF;
                    END IF;
                    -- Nguon phai cung ho so; khong cho lay ID de vuot quyen noi dung.
                    IF tep.id IS NULL OR tep.tai_lieu_id<>p_tai_lieu OR tep.ma_bam IS DISTINCT FROM nguon->>'sha256'
                        OR (tep.het_han_luc IS NOT NULL AND tep.het_han_luc <= clock_timestamp()) THEN
                        RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                    END IF;
                    INSERT INTO loi_tai_lieu.nguon_ket_qua(phap_nhan_id,ket_qua_id,tep_id,ket_qua_nguon_id,
                        ma_bam,revision_nguon,trang,dinh_vi,trich_dan) VALUES(p_pn,moi,
                        (nguon->>'tep_id')::uuid,(nguon->>'ket_qua_id')::uuid,tep.ma_bam,
                        (nguon->>'revision')::bigint,(nguon->>'trang')::integer,nguon->>'dinh_vi',nguon->>'trich_dan');
                END LOOP;
                INSERT INTO loi_tai_lieu.ket_qua_duyet(phap_nhan_id,ket_qua_id,phien_ban_dong,trang_thai_duyet,tao_boi)
                    VALUES(p_pn,moi,1,'chua_duyet',ai);
            WHEN 'duyet','cong_bo' THEN
                SELECT * INTO kq FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=(p_du_lieu->>'ket_qua_id')::uuid
                    AND tai_lieu_id=p_tai_lieu AND phap_nhan_id=p_pn;
                IF kq.id IS NULL THEN RAISE EXCEPTION 'TAI_LIEU_KHONG_THAY' USING ERRCODE='42501'; END IF;
                IF p_loai='cong_bo' AND NOT loi_tai_lieu.duoc_xem_ket_qua(kq.id,ai) THEN
                    RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
                END IF;
                IF kq.trang_thai<>'thanh_cong' OR NOT EXISTS(SELECT FROM loi_tai_lieu.tep_goc
                    WHERE id=kq.tep_id AND ma_bam ~ '^[0-9a-f]{64}$'
                        AND (het_han_luc IS NULL OR het_han_luc>clock_timestamp()))
                    OR NOT EXISTS(SELECT FROM loi_tai_lieu.nguon_ket_qua WHERE ket_qua_id=kq.id) THEN
                    RAISE EXCEPTION 'TAI_LIEU_THIEU_TEP_HASH' USING ERRCODE='55000';
                END IF;
                IF EXISTS (SELECT FROM loi_tai_lieu.nguon_ket_qua n
                    LEFT JOIN loi_tai_lieu.ket_qua_xu_ly s ON s.id=n.ket_qua_nguon_id
                    LEFT JOIN loi_tai_lieu.tep_goc t ON t.id=coalesce(n.tep_id,s.tep_id)
                    WHERE n.ket_qua_id=kq.id AND (t.id IS NULL OR t.ma_bam IS DISTINCT FROM n.ma_bam
                        OR (t.het_han_luc IS NOT NULL AND t.het_han_luc<=clock_timestamp()))) THEN
                    RAISE EXCEPTION 'TAI_LIEU_THIEU_TEP_HASH' USING ERRCODE='55000';
                END IF;
                IF p_loai='duyet' THEN
                    SELECT max(phien_ban_dong) INTO ban FROM loi_tai_lieu.ket_qua_duyet WHERE ket_qua_id=kq.id;
                    IF ban IS DISTINCT FROM (p_du_lieu->>'row_version')::bigint THEN
                        RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                    END IF;
                    INSERT INTO loi_tai_lieu.ket_qua_duyet(id,phap_nhan_id,ket_qua_id,phien_ban_dong,trang_thai_duyet,tao_boi)
                        VALUES(moi,p_pn,kq.id,ban+1,p_du_lieu->>'trang_thai_duyet',ai);
                ELSE
                    INSERT INTO loi_tai_lieu.ket_qua_cong_bo(id,phap_nhan_id,ket_qua_id,tao_boi) VALUES(moi,p_pn,kq.id,ai);
                END IF;
            END CASE;
        END IF;
        PERFORM loi.ghi_kiem_toan(p_hd,'tai_lieu_' || p_loai,moi,'DAT',p_ma,p_module,p_pn,p_request,p_viec,p_the_he);
        RETURN moi;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.doc_metadata(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_tai_lieu uuid,p_bien_the text,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; tl loi_tai_lieu.tai_lieu;
    BEGIN
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF split_part(p_hd,':',3)<>'XEM' OR p_bien_the IS NULL OR p_bien_the NOT IN
            ('goc','ocr','da_che','noi_dung','phan_hoi_nguon') THEN
            RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END IF;
        SELECT * INTO tl FROM loi_tai_lieu.tai_lieu WHERE id=p_tai_lieu AND module=p_module AND phap_nhan_id=p_pn;
        IF tl.id IS NULL THEN RAISE EXCEPTION 'TAI_LIEU_KHONG_THAY' USING ERRCODE='42501'; END IF;
        PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,
            jsonb_build_object('bang',tl.bang_doi_tuong,'id',tl.doi_tuong_id),tl.phien_ban_contract,'cho_xem',p_viec,p_the_he);
        IF NOT loi_tai_lieu.duoc_xem_noi_dung(p_tai_lieu,ai,p_bien_the) THEN
            RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
        END IF;
        IF EXISTS(SELECT FROM loi_tai_lieu.ket_qua_xu_ly k
            WHERE k.tai_lieu_id=p_tai_lieu AND k.bien_the=p_bien_the
                AND NOT loi_tai_lieu.duoc_xem_ket_qua(k.id,ai)) THEN
            RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
        END IF;
        RETURN jsonb_build_object('id',tl.id,'phap_nhan_id',tl.phap_nhan_id,'module',tl.module,
            'loai',tl.loai,'ten',tl.ten,'row_version',tl.phien_ban_dong::text,
            'tep',coalesce((SELECT jsonb_agg(jsonb_build_object('bien_the',b.bien_the,
                'so_phien_ban',b.so_phien_ban,'tham_chieu',jsonb_build_object('contract','tham_chieu_tep.v1','phien_ban','1.0.0',
                'tep_id',t.id,'ten_tep',t.ten_tep,'mime',t.mime,'kich_thuoc',t.kich_thuoc,'sha256',t.ma_bam,
                'het_han_luc',CASE WHEN t.het_han_luc IS NULL THEN NULL ELSE
                    to_char(t.het_han_luc AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END)) ORDER BY b.so_phien_ban)
                FROM loi_tai_lieu.tai_lieu_tep b JOIN loi_tai_lieu.tep_goc t ON t.id=b.tep_id
                WHERE b.tai_lieu_id=p_tai_lieu AND b.bien_the=p_bien_the),'[]'::jsonb),
            'ket_qua',coalesce((SELECT jsonb_agg(jsonb_build_object('id',k.id,'goc_id',k.goc_id,'revision',k.revision,
                'tep_id',k.tep_id,'trang_thai',k.trang_thai,'trang_thai_duyet',d.trang_thai_duyet,
                'row_version',d.phien_ban_dong::text,'cong_bo',EXISTS(SELECT FROM loi_tai_lieu.ket_qua_cong_bo c
                    WHERE c.ket_qua_id=k.id)) ORDER BY k.goc_id,k.revision)
                FROM loi_tai_lieu.ket_qua_xu_ly k CROSS JOIN LATERAL(SELECT trang_thai_duyet,phien_ban_dong
                    FROM loi_tai_lieu.ket_qua_duyet WHERE ket_qua_id=k.id ORDER BY phien_ban_dong DESC LIMIT 1) d
                WHERE k.tai_lieu_id=p_tai_lieu AND k.bien_the=p_bien_the),'[]'::jsonb));
    END;
    $ham$;
    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi_tai_lieu'::regnamespace AND proname IN
        ('ngu_canh','kiem_quyen','duoc_xem_noi_dung','duoc_xem_ket_qua','ghi_metadata','doc_metadata') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I',ham.ck,chay,login);
        IF ham.proname IN ('ghi_metadata','doc_metadata') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
