-- G2-11. Nguon: M0013_COMMON/M0014/M0016 va K2 crm_mau._tra_trong.
-- Khong replay SQL cu. Caller giu cung transaction/ket noi: tra -> nghiep vu -> ghi.
-- Nang luc nguon la du lieu quan tri toan cuc, chi provisioning cap/thu hoi.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
    chu_loi text := tt || 'vai_doi_cau_truc_loi';
    login text := tt || 'dang_nhap_loi';
    chay text := tt || 'vai_chay_loi_tai_lieu';
    vai_cu text := current_setting('role');
    duong_cu text := current_setting('search_path');
    bang text; ham record;
BEGIN
    IF (tt <> '' AND tt !~ '^[a-z][a-z0-9_]*_$') OR octet_length(chu)>63
       OR (tt <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-11: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF to_regprocedure('loi_tai_lieu.doc_metadata(text,text,uuid,text,uuid,text,uuid,bigint)') IS NULL
       OR NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='loi_tai_lieu'
                     AND pg_get_userbyid(nspowner)=chu) THEN
        RAISE EXCEPTION 'G2-11: Can lead, ap G2-01..10 truoc';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I',chu_loi);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);
    -- Nang cap trigger cua 004 da phat hanh; giu nguyen checksum lich su.
    -- Ham duoc thay truoc khi runner ghi so 011, ke ca nen dung o 009.
    CREATE OR REPLACE FUNCTION loi.kiem_lich_su_doi_cau_truc()
    RETURNS trigger LANGUAGE plpgsql
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        bam_cu text;
        ban_cu integer;
    BEGIN
        PERFORM pg_advisory_xact_lock(hashtextextended('kho_core_migration:' || NEW.ma_goi, 4));
        SELECT ma_bam INTO bam_cu FROM loi.lich_su_doi_cau_truc
            WHERE ma_goi = NEW.ma_goi AND so_phien_ban = NEW.so_phien_ban;
        IF FOUND AND bam_cu <> NEW.ma_bam THEN
            RAISE EXCEPTION 'MIGRATION_CHANGED' USING ERRCODE = '23514';
        END IF;
        SELECT coalesce(max(so_phien_ban), 0) INTO ban_cu FROM loi.lich_su_doi_cau_truc
            WHERE ma_goi = NEW.ma_goi;
        IF NEW.so_phien_ban < ban_cu THEN
            RAISE EXCEPTION 'FUTURE_SCHEMA' USING ERRCODE = '23514';
        END IF;
        IF NEW.so_phien_ban <= ban_cu THEN
            RAISE EXCEPTION 'MIGRATION_ORDER' USING ERRCODE = '23514';
        END IF;
        NEW.nguoi_ap_dung := session_user;
        NEW.ap_dung_luc := statement_timestamp();
        RETURN NEW;
    END;
    $ham$;
    -- Ten dich theo DAC-TA-CSDL 3.5; giu khoa text/ref/hash cua K2.
    CREATE TABLE IF NOT EXISTS loi.nguon_cai_dat (
        id text PRIMARY KEY CHECK(id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG' CHECK(trang_thai IN ('HOAT_DONG','DUNG')),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE IF NOT EXISTS loi.ho_so_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguon_cai_dat text NOT NULL REFERENCES loi.nguon_cai_dat(id),
        tham_chieu text NOT NULL CHECK(length(tham_chieu) BETWEEN 1 AND 300),
        ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(nguon_cai_dat,tham_chieu), UNIQUE(nguon_cai_dat,tham_chieu,ma_bam)
    );
    CREATE TABLE IF NOT EXISTS loi.nang_luc_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        nguon_cai_dat text NOT NULL, tham_chieu text NOT NULL, ma_bam text NOT NULL,
        hanh_dong text NOT NULL CHECK(hanh_dong IN ('INTAKE','READ_SOURCE')),
        cap_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(), thu_hoi_luc timestamptz,
        FOREIGN KEY(nguon_cai_dat,tham_chieu,ma_bam)
            REFERENCES loi.ho_so_nguon(nguon_cai_dat,tham_chieu,ma_bam)
    );
    CREATE OR REPLACE FUNCTION loi.tiep_nhan_duoc_nguon(p_nguon text,p_ref text,p_bam text,p_hd text)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT EXISTS(SELECT FROM loi.nang_luc_nguon n
            JOIN loi.nguon_cai_dat g ON g.id=n.nguon_cai_dat
            JOIN loi.mtq_phien_rls() x ON x.nguoi_dung_id=n.nguoi_dung_id
            WHERE n.nguon_cai_dat=p_nguon AND n.tham_chieu=p_ref AND n.ma_bam=p_bam
                AND n.hanh_dong=p_hd AND n.thu_hoi_luc IS NULL AND g.trang_thai='HOAT_DONG')
    $ham$;
    FOREACH bang IN ARRAY ARRAY['nguon_cai_dat','ho_so_nguon','nang_luc_nguon'] LOOP
        IF (SELECT pg_get_userbyid(relowner)<>chu_loi FROM pg_class
            WHERE oid=format('loi.%I',bang)::regclass) THEN
            RAISE EXCEPTION 'G2-11: Can lead, sai owner nguon';
        END IF;
        EXECUTE format('REVOKE ALL ON loi.%I FROM PUBLIC, %I, %I',bang,tt||'vai_chay_loi',login);
    END LOOP;
    IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid='loi.ho_so_nguon'::regclass
                  AND tgname='ho_so_nguon_bat_bien') THEN
        CREATE TRIGGER ho_so_nguon_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE ON loi.ho_so_nguon
            FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan();
    END IF;
    REVOKE ALL ON FUNCTION loi.tiep_nhan_duoc_nguon(text,text,text,text) FROM PUBLIC;
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.tiep_nhan_duoc_nguon(text,text,text,text) TO %I',chu);
    EXECUTE format('GRANT REFERENCES ON loi.ho_so_nguon TO %I',chu);

    EXECUTE format('SET LOCAL ROLE %I',chu);
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.lan_tiep_nhan_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguon_cai_dat text NOT NULL, tham_chieu text NOT NULL, ma_bam_ho_so text NOT NULL,
        khong_gian text NOT NULL CHECK(length(khong_gian) BETWEEN 1 AND 120),
        khoa_chong_trung text NOT NULL CHECK(khoa_chong_trung ~ '^[A-Za-z0-9._:-]{16,128}$'),
        ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        phap_nhan_id uuid REFERENCES loi.phap_nhan(id),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        FOREIGN KEY(nguon_cai_dat,tham_chieu,ma_bam_ho_so)
            REFERENCES loi.ho_so_nguon(nguon_cai_dat,tham_chieu,ma_bam),
        UNIQUE(nguon_cai_dat,khong_gian,khoa_chong_trung),
        UNIQUE(id,nguon_cai_dat,tham_chieu,ma_bam_ho_so)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.vung_tam_tin_cay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), lan_tiep_nhan_id uuid NOT NULL UNIQUE,
        nguon_cai_dat text NOT NULL, tham_chieu text NOT NULL, ma_bam_ho_so text NOT NULL,
        phap_nhan_id uuid REFERENCES loi.phap_nhan(id),
        du_lieu jsonb NOT NULL CHECK(jsonb_typeof(du_lieu)='object'),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        FOREIGN KEY(lan_tiep_nhan_id,nguon_cai_dat,tham_chieu,ma_bam_ho_so)
            REFERENCES loi_tai_lieu.lan_tiep_nhan_nguon(id,nguon_cai_dat,tham_chieu,ma_bam_ho_so)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.bien_nhan_thao_tac (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        operation text NOT NULL CHECK(operation ~ '^[A-Za-z0-9._:-]{3,120}$'),
        khoa_chong_trung text NOT NULL CHECK(khoa_chong_trung ~ '^[A-Za-z0-9._:-]{16,128}$'),
        ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        ket_qua jsonb NOT NULL, quyen_doc jsonb NOT NULL CHECK(jsonb_typeof(quyen_doc)='object'),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(phap_nhan_id,module,operation,khoa_chong_trung)
    );
    CREATE TABLE IF NOT EXISTS loi_tai_lieu.bien_nhan_core (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module text NOT NULL REFERENCES loi.module_danh_muc(ma),
        operation text NOT NULL CHECK(operation ~ '^[A-Za-z0-9._:-]{3,120}$'),
        khoa_chong_trung text NOT NULL CHECK(khoa_chong_trung ~ '^[A-Za-z0-9._:-]{16,128}$'),
        ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        ket_qua jsonb NOT NULL, quyen_doc jsonb NOT NULL CHECK(jsonb_typeof(quyen_doc)='object'),
        trang_thai text NOT NULL CHECK(trang_thai IN ('DANG_XU_LY','CHUA_RO','HOAN_TAT')),
        ket_qua_cuoi_luc timestamptz,
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK((trang_thai='HOAN_TAT')=(ket_qua_cuoi_luc IS NOT NULL)),
        UNIQUE(tao_boi,phap_nhan_id,module,operation,khoa_chong_trung)
    );
    FOREACH bang IN ARRAY ARRAY['lan_tiep_nhan_nguon','vung_tam_tin_cay',
                                'bien_nhan_thao_tac','bien_nhan_core'] LOOP
        IF (SELECT pg_get_userbyid(relowner)<>chu FROM pg_class
            WHERE oid=format('loi_tai_lieu.%I',bang)::regclass) THEN
            RAISE EXCEPTION 'G2-11: Can lead, sai owner tiep nhan';
        END IF;
        EXECUTE format('ALTER TABLE loi_tai_lieu.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE loi_tai_lieu.%I FORCE ROW LEVEL SECURITY',bang);
        EXECUTE format('REVOKE ALL ON loi_tai_lieu.%I FROM PUBLIC, %I, %I',bang,chay,login);
        IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid=format('loi_tai_lieu.%I',bang)::regclass
                      AND polname='tiep_nhan_phien') THEN
            IF bang IN ('lan_tiep_nhan_nguon','vung_tam_tin_cay') THEN
                -- PrePN: quyen nguon, KHONG co nhanh phap_nhan_id IS NULL -> true.
                EXECUTE format('CREATE POLICY tiep_nhan_phien ON loi_tai_lieu.%I TO %I
                    USING (loi.tiep_nhan_duoc_nguon(nguon_cai_dat,tham_chieu,ma_bam_ho_so,''READ_SOURCE''))
                    WITH CHECK (loi.tiep_nhan_duoc_nguon(nguon_cai_dat,tham_chieu,ma_bam_ho_so,''INTAKE''))',bang,chu);
            ELSE
                EXECUTE format('CREATE POLICY tiep_nhan_phien ON loi_tai_lieu.%I TO %I
                    USING (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))
                    WITH CHECK (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))',bang,chu);
            END IF;
        END IF;
        IF bang<>'bien_nhan_core' AND NOT EXISTS(SELECT FROM pg_trigger
            WHERE tgrelid=format('loi_tai_lieu.%I',bang)::regclass AND tgname='tiep_nhan_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER tiep_nhan_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE
                ON loi_tai_lieu.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
        END IF;
    END LOOP;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.tiep_nhan_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_nguon text,p_ref text,p_bam_ho_so text,p_khong_gian text,p_khoa text,p_du_lieu jsonb)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; bam text; lan loi_tai_lieu.lan_tiep_nhan_nguon; tam uuid;
    BEGIN
        -- Runtime chi login Core; owner khong duoc dung lam runtime.
        IF session_user IS DISTINCT FROM regexp_replace(current_user,
            'vai_doi_cau_truc_loi_tai_lieu$','dang_nhap_loi') THEN
            RAISE EXCEPTION 'TIEP_NHAN_CHI_CORE' USING ERRCODE='42501';
        END IF;
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,NULL,NULL);
        IF split_part(p_hd,':',3) NOT IN ('LAP','SUA') OR p_khoa IS NULL
           OR p_khoa !~ '^[A-Za-z0-9._:-]{16,128}$' OR jsonb_typeof(p_du_lieu) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'TIEP_NHAN_DAU_VAO' USING ERRCODE='22023';
        END IF;
        IF NOT loi.tiep_nhan_duoc_nguon(p_nguon,p_ref,p_bam_ho_so,'INTAKE')
           OR NOT loi.tiep_nhan_duoc_nguon(p_nguon,p_ref,p_bam_ho_so,'READ_SOURCE') THEN
            RAISE EXCEPTION 'TIEP_NHAN_KHONG_THAY' USING ERRCODE='P0002';
        END IF;
        bam := encode(sha256(convert_to(jsonb_build_object('nguon',p_nguon,'ref',p_ref,
            'ma_bam_ho_so',p_bam_ho_so,'du_lieu',p_du_lieu)::text,'UTF8')),'hex');
        IF NOT pg_try_advisory_xact_lock(hashtextextended(
            jsonb_build_array('tiep_nhan',p_nguon,p_khong_gian,p_khoa)::text,11)) THEN
            RAISE EXCEPTION 'YEU_CAU_DANG_XU_LY' USING ERRCODE='P0001';
        END IF;
        SELECT * INTO lan FROM loi_tai_lieu.lan_tiep_nhan_nguon
            WHERE nguon_cai_dat=p_nguon AND khong_gian=p_khong_gian AND khoa_chong_trung=p_khoa;
        IF lan.id IS NOT NULL THEN
            IF lan.ma_bam<>bam THEN RAISE EXCEPTION 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG' USING ERRCODE='P0001'; END IF;
            RETURN jsonb_build_object('lan_tiep_nhan_id',lan.id,'vung_tam_id',
                (SELECT id FROM loi_tai_lieu.vung_tam_tin_cay WHERE lan_tiep_nhan_id=lan.id),'lap_lai',true);
        END IF;
        INSERT INTO loi_tai_lieu.lan_tiep_nhan_nguon(nguon_cai_dat,tham_chieu,ma_bam_ho_so,
            khong_gian,khoa_chong_trung,ma_bam,tao_boi)
            VALUES(p_nguon,p_ref,p_bam_ho_so,p_khong_gian,p_khoa,bam,ai) RETURNING * INTO lan;
        INSERT INTO loi_tai_lieu.vung_tam_tin_cay(lan_tiep_nhan_id,nguon_cai_dat,tham_chieu,
            ma_bam_ho_so,du_lieu,tao_boi) VALUES(lan.id,p_nguon,p_ref,p_bam_ho_so,p_du_lieu,ai) RETURNING id INTO tam;
        RETURN jsonb_build_object('lan_tiep_nhan_id',lan.id,'vung_tam_id',tam,'lap_lai',false);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.doc_vung_tam_v2(p_ma text,p_module text,p_pn uuid,p_hd text,p_lan uuid)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE kq jsonb;
    BEGIN
        PERFORM loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,NULL,NULL);
        IF split_part(p_hd,':',3) IS DISTINCT FROM 'XEM' THEN
            RAISE EXCEPTION 'TIEP_NHAN_KHONG_THAY' USING ERRCODE='P0002';
        END IF;
        SELECT jsonb_build_object('id',id,'lan_tiep_nhan_id',lan_tiep_nhan_id,
            'phap_nhan_id',phap_nhan_id,'du_lieu',du_lieu) INTO kq
            FROM loi_tai_lieu.vung_tam_tin_cay WHERE lan_tiep_nhan_id=p_lan;
        IF kq IS NULL THEN RAISE EXCEPTION 'TIEP_NHAN_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        RETURN kq;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.bien_nhan_kiem_doc(p_ma text,p_module text,p_pn uuid,
        p_quyen jsonb,p_viec uuid,p_the_he bigint) RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; tl jsonb;
    BEGIN
        IF jsonb_typeof(p_quyen) IS DISTINCT FROM 'object'
           OR split_part(p_quyen->>'hanh_dong',':',3) IS DISTINCT FROM 'XEM'
           OR jsonb_typeof(p_quyen->'doi_tuong') IS DISTINCT FROM 'object'
           OR coalesce(p_quyen->>'phien_ban_contract','')='' THEN
            RAISE EXCEPTION 'BIEN_NHAN_DAU_VAO' USING ERRCODE='22023';
        END IF;
        BEGIN
            ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_quyen->>'hanh_dong',p_viec,p_the_he);
            PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_quyen->>'hanh_dong',
                p_quyen->'doi_tuong',p_quyen->>'phien_ban_contract','cho_xem',p_viec,p_the_he);
            IF p_quyen ? 'tai_lieu_id' THEN
                tl := loi_tai_lieu.doc_metadata(p_ma,p_module,p_pn,p_quyen->>'hanh_dong',
                    (p_quyen->>'tai_lieu_id')::uuid,p_quyen->>'bien_the',p_viec,p_the_he);
            END IF;
            IF p_quyen ? 'ket_qua_id' AND NOT loi_tai_lieu.duoc_xem_ket_qua((p_quyen->>'ket_qua_id')::uuid,ai) THEN
                RAISE EXCEPTION 'BIEN_NHAN_KHONG_THAY' USING ERRCODE='P0002';
            END IF;
        EXCEPTION WHEN insufficient_privilege OR no_data_found THEN
            RAISE EXCEPTION 'BIEN_NHAN_KHONG_THAY' USING ERRCODE='P0002';
        END;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.bien_nhan_core_con_hieu_luc(p_trang_thai text,
        p_cuoi timestamptz,p_luc timestamptz) RETURNS boolean
    LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT CASE WHEN p_trang_thai IN ('DANG_XU_LY','CHUA_RO') THEN true
            WHEN p_trang_thai='HOAN_TAT' THEN p_cuoi IS NOT NULL AND p_luc<p_cuoi+interval '24 hours'
            ELSE false END
    $ham$;

    -- Noi bo: khong GRANT cho runtime. Hai cua module chi goi voi p_core=false.
    CREATE OR REPLACE FUNCTION loi_tai_lieu.bien_nhan_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_operation text,p_khoa text,p_than jsonb,p_ghi boolean,p_core boolean,p_ket_qua jsonb,
        p_quyen jsonb,p_trang_thai text,p_viec uuid,p_the_he bigint) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; bam text; kq jsonb; quyen jsonb; id_cu uuid; bam_cu text;
        cuoi timestamptz; trang_thai text; tao uuid; lap boolean := false;
    BEGIN
        IF p_core AND session_user IS DISTINCT FROM
            regexp_replace(current_user,'vai_doi_cau_truc_loi_tai_lieu$','dang_nhap_loi') THEN
            RAISE EXCEPTION 'TIEP_NHAN_CHI_CORE' USING ERRCODE='42501';
        END IF;
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF p_operation IS NULL OR p_operation !~ '^[A-Za-z0-9._:-]{3,120}$'
           OR p_khoa IS NULL OR p_khoa !~ '^[A-Za-z0-9._:-]{16,128}$'
           OR jsonb_typeof(p_than) IS DISTINCT FROM 'object'
           OR p_than->>'phap_nhan_id' IS DISTINCT FROM p_pn::text
           OR jsonb_typeof(p_than->'doi_tuong') IS DISTINCT FROM 'object'
           OR coalesce(p_than->>'phien_ban_contract','')=''
           OR split_part(p_hd,':',3) NOT IN ('LAP','SUA','DUYET','HUY') THEN
            RAISE EXCEPTION 'BIEN_NHAN_DAU_VAO' USING ERRCODE='22023';
        END IF;
        -- Bat buoc kiem HANH DONG truoc khi khoa/tra bien nhan.
        PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,p_than->'doi_tuong',
            p_than->>'phien_ban_contract','cho_ghi',p_viec,p_the_he);
        bam := encode(sha256(convert_to(jsonb_build_object('operation',p_operation,'body',p_than)::text,'UTF8')),'hex');
        IF NOT pg_try_advisory_xact_lock(hashtextextended(jsonb_build_array('bien_nhan',p_core,
            CASE WHEN p_core THEN ai END,p_pn,p_module,p_operation,p_khoa)::text,11)) THEN
            RAISE EXCEPTION 'YEU_CAU_DANG_XU_LY' USING ERRCODE='P0001';
        END IF;
        IF p_core THEN
            SELECT id,ma_bam,ket_qua,quyen_doc,ket_qua_cuoi_luc,b.trang_thai,tao_boi
                INTO id_cu,bam_cu,kq,quyen,cuoi,trang_thai,tao FROM loi_tai_lieu.bien_nhan_core b
                WHERE phap_nhan_id=p_pn AND module=p_module AND operation=p_operation
                    AND khoa_chong_trung=p_khoa AND tao_boi=ai;
        ELSE
            SELECT id,ma_bam,ket_qua,quyen_doc,tao_boi INTO id_cu,bam_cu,kq,quyen,tao
                FROM loi_tai_lieu.bien_nhan_thao_tac WHERE phap_nhan_id=p_pn AND module=p_module
                    AND operation=p_operation AND khoa_chong_trung=p_khoa;
        END IF;
        IF id_cu IS NOT NULL THEN
            PERFORM loi_tai_lieu.bien_nhan_kiem_doc(p_ma,p_module,p_pn,quyen,p_viec,p_the_he);
            IF bam_cu<>bam THEN RAISE EXCEPTION 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG' USING ERRCODE='P0001'; END IF;
            IF p_core AND NOT loi_tai_lieu.bien_nhan_core_con_hieu_luc(trang_thai,cuoi,clock_timestamp()) THEN
                -- G2-29 don payload khi du dieu kien; dau vet nay chan retry mu sau TTL.
                RAISE EXCEPTION 'BIEN_NHAN_CORE_HET_HAN' USING ERRCODE='P0001';
            END IF;
            -- Core chi hoan tat ket qua dang chay/chua ro; final khong doi/khong reset TTL.
            IF p_core AND p_ghi AND trang_thai<>'HOAN_TAT' THEN
                IF p_trang_thai IS NULL OR p_trang_thai NOT IN ('DANG_XU_LY','CHUA_RO','HOAN_TAT')
                   OR p_ket_qua IS NULL THEN RAISE EXCEPTION 'BIEN_NHAN_DAU_VAO' USING ERRCODE='22023'; END IF;
                PERFORM loi_tai_lieu.bien_nhan_kiem_doc(p_ma,p_module,p_pn,p_quyen,p_viec,p_the_he);
                -- Doc da dat GUC XEM; khoi phuc hanh dong ghi da xac minh.
                PERFORM loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
                UPDATE loi_tai_lieu.bien_nhan_core SET ket_qua=p_ket_qua,quyen_doc=p_quyen,
                    trang_thai=p_trang_thai,ket_qua_cuoi_luc=CASE WHEN p_trang_thai='HOAN_TAT' THEN clock_timestamp() END
                    WHERE id=id_cu;
                kq := p_ket_qua;
            ELSE lap := true;
            END IF;
        ELSIF NOT p_ghi THEN
            RETURN NULL;
        ELSE
            IF p_ket_qua IS NULL THEN RAISE EXCEPTION 'BIEN_NHAN_DAU_VAO' USING ERRCODE='22023'; END IF;
            PERFORM loi_tai_lieu.bien_nhan_kiem_doc(p_ma,p_module,p_pn,p_quyen,p_viec,p_the_he);
            PERFORM loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
            IF p_core THEN
                IF p_trang_thai IS NULL OR p_trang_thai NOT IN ('DANG_XU_LY','CHUA_RO','HOAN_TAT') THEN
                    RAISE EXCEPTION 'BIEN_NHAN_DAU_VAO' USING ERRCODE='22023';
                END IF;
                INSERT INTO loi_tai_lieu.bien_nhan_core(phap_nhan_id,module,operation,khoa_chong_trung,
                    ma_bam,ket_qua,quyen_doc,trang_thai,ket_qua_cuoi_luc,tao_boi)
                    VALUES(p_pn,p_module,p_operation,p_khoa,bam,p_ket_qua,p_quyen,p_trang_thai,
                        CASE WHEN p_trang_thai='HOAN_TAT' THEN clock_timestamp() END,ai) RETURNING id INTO id_cu;
            ELSE
                INSERT INTO loi_tai_lieu.bien_nhan_thao_tac(phap_nhan_id,module,operation,khoa_chong_trung,
                    ma_bam,ket_qua,quyen_doc,tao_boi)
                    VALUES(p_pn,p_module,p_operation,p_khoa,bam,p_ket_qua,p_quyen,ai) RETURNING id INTO id_cu;
            END IF;
            kq := p_ket_qua;
        END IF;
        PERFORM loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        RETURN jsonb_build_object('id',id_cu,'ket_qua',kq,'lap_lai',lap);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.tra_bien_nhan_thao_tac_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_operation text,p_khoa text,p_than jsonb,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT loi_tai_lieu.bien_nhan_v2(p_ma,p_module,p_pn,p_hd,p_operation,p_khoa,p_than,
            false,false,NULL,NULL,NULL,p_viec,p_the_he)
    $ham$;
    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_bien_nhan_thao_tac_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_operation text,p_khoa text,p_than jsonb,p_ket_qua jsonb,p_quyen jsonb,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT loi_tai_lieu.bien_nhan_v2(p_ma,p_module,p_pn,p_hd,p_operation,p_khoa,p_than,
            true,false,p_ket_qua,p_quyen,NULL,p_viec,p_the_he)
    $ham$;
    CREATE OR REPLACE FUNCTION loi_tai_lieu.bien_nhan_core_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_operation text,p_khoa text,p_than jsonb,p_ghi boolean DEFAULT false,p_ket_qua jsonb DEFAULT NULL,
        p_quyen jsonb DEFAULT NULL,p_trang_thai text DEFAULT 'HOAN_TAT',p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT loi_tai_lieu.bien_nhan_v2(p_ma,p_module,p_pn,p_hd,p_operation,p_khoa,p_than,
            p_ghi,true,p_ket_qua,p_quyen,p_trang_thai,p_viec,p_the_he)
    $ham$;
    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi_tai_lieu'::regnamespace AND proname IN
        ('tiep_nhan_v2','doc_vung_tam_v2','bien_nhan_kiem_doc','bien_nhan_v2','bien_nhan_core_con_hieu_luc',
         'tra_bien_nhan_thao_tac_v2','ghi_bien_nhan_thao_tac_v2','bien_nhan_core_v2') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I',ham.ck,chay,login);
        IF ham.proname NOT IN ('bien_nhan_v2','bien_nhan_kiem_doc') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        END IF;
        -- Module Manager cap dung chu ky tra/ghi/doc theo khai bao, khong cap ham noi bo/Core.
    END LOOP;
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
