-- G2-22a: retry ben vung, danh tinh Job va doi chieu sau Core restart.
-- Khong sua 016; giu nguyen ACL, CAS va yeu cau bang chung OS cua 016.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_loi';
    vai_cu text := current_setting('role');
    duong_cu text := current_setting('search_path');
    bang text;
    ham record;
BEGIN
    IF (tt<>'' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tt||'vai_doi_cau_truc_loi_tai_lieu')>63
       OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-22: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR to_regprocedure('loi.so_cong_giu(uuid,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-22: Can lead, ap G2-16 dung owner truoc';
    END IF;
    FOREACH bang IN ARRAY ARRAY['so_cong','module_phien_chay','engine_phien_chay'] LOOP
        IF NOT EXISTS (SELECT FROM pg_class WHERE oid=to_regclass('loi.'||bang)
            AND relkind='r' AND pg_get_userbyid(relowner)=chu) THEN
            RAISE EXCEPTION 'G2-22: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);

    ALTER TABLE loi.so_cong
        ADD COLUMN IF NOT EXISTS so_loi_khoi_dong integer NOT NULL DEFAULT 0
            CHECK (so_loi_khoi_dong BETWEEN 0 AND 3),
        ADD COLUMN IF NOT EXISTS thu_lai_sau timestamptz,
        ADD COLUMN IF NOT EXISTS ma_loi_khoi_dong text
            CHECK (ma_loi_khoi_dong ~ '^[A-Z][A-Z0-9_]{0,79}$');
    ALTER TABLE loi.module_phien_chay ADD COLUMN IF NOT EXISTS ten_job text;
    ALTER TABLE loi.engine_phien_chay ADD COLUMN IF NOT EXISTS ten_job text;
    -- Khoa cu van doi Admin, khong tu mo khoa khi nang cap.
    UPDATE loi.so_cong SET so_loi_khoi_dong=3,ma_loi_khoi_dong=ma_loi
        WHERE trang_thai='LOI' AND so_loi_khoi_dong=0;

    CREATE OR REPLACE FUNCTION loi.so_cong_vong_doi() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        -- Chan ca caller goi truc tiep so_cong_nhan truoc han retry.
        IF NEW.giu_boi IS NOT NULL AND NEW.giu_boi IS DISTINCT FROM OLD.giu_boi
            AND OLD.thu_lai_sau>clock_timestamp() THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        IF (NEW.trang_thai='CON_GIU' AND OLD.trang_thai<>'CON_GIU')
            OR (OLD.trang_thai='LOI' AND NEW.trang_thai='TRONG') THEN
            NEW.so_loi_khoi_dong:=0;
            NEW.thu_lai_sau:=NULL;
            NEW.ma_loi_khoi_dong:=NULL;
        END IF;
        RETURN NEW;
    END;
    $ham$;
    CREATE OR REPLACE TRIGGER so_cong_vong_doi BEFORE UPDATE ON loi.so_cong
        FOR EACH ROW EXECUTE FUNCTION loi.so_cong_vong_doi();

    CREATE OR REPLACE FUNCTION loi.so_cong_loi_khoi_dong(p_id uuid,p_instance uuid,p_the_he bigint,p_ma_loi text)
    RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; n integer;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p_ma_loi IS NULL OR p_ma_loi !~ '^[A-Z][A-Z0-9_]{0,79}$' THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        -- Goi lai cung phien khong duoc tang so loi lan nua.
        IF EXISTS (SELECT FROM loi.module_phien_chay WHERE id=p_instance
                AND so_cong_id=p_id AND the_he=p_the_he AND ly_do_ket_thuc='LOI')
            OR EXISTS (SELECT FROM loi.engine_phien_chay WHERE id=p_instance
                AND so_cong_id=p_id AND the_he=p_the_he AND ly_do_ket_thuc='LOI') THEN
            RETURN true;
        END IF;
        PERFORM loi.so_cong_dong_phien(s,'LOI');
        n:=least(s.so_loi_khoi_dong+1,3);
        -- Giu danh tinh cu: cleanup/doi chieu OS xong moi bo giu_boi.
        UPDATE loi.so_cong SET so_loi_khoi_dong=n,ma_loi_khoi_dong=p_ma_loi,
            trang_thai=CASE WHEN n=3 THEN 'LOI' ELSE 'CORE_GIU' END,
            ma_loi=CASE WHEN n=3 THEN p_ma_loi END,
            thu_lai_sau=CASE WHEN n<3 THEN clock_timestamp()+make_interval(secs=>n*2) END,
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id;
        PERFORM loi.ghi_kiem_toan('CORE:CONG:LOI','so_cong',s.id,'LOI');
        RETURN true;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.so_cong_loi_chua_nhan(p_id uuid,p_the_he bigint,p_ma_loi text)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; n integer;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        IF p_ma_loi IS NULL OR p_ma_loi !~ '^[A-Z][A-Z0-9_]{0,79}$' THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        IF s.the_he IS DISTINCT FROM p_the_he OR s.giu_boi IS NOT NULL
            OR s.trang_thai='LOI' OR s.het_hieu_luc_luc IS NOT NULL
            OR s.thu_lai_sau>clock_timestamp() THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        n:=least(s.so_loi_khoi_dong+1,3);
        UPDATE loi.so_cong SET so_loi_khoi_dong=n,ma_loi_khoi_dong=p_ma_loi,
            trang_thai=CASE WHEN n=3 THEN 'LOI' ELSE 'TRONG' END,
            ma_loi=CASE WHEN n=3 THEN p_ma_loi END,
            thu_lai_sau=CASE WHEN n<3 THEN clock_timestamp()+make_interval(secs=>n*2) END,
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        PERFORM loi.ghi_kiem_toan('CORE:CONG:LOI','so_cong',s.id,'LOI');
        RETURN to_jsonb(s);
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
        UPDATE loi.so_cong SET trang_thai='TRONG',ma_loi=NULL,
            giu_den=CASE WHEN giu_boi IS NOT NULL THEN clock_timestamp() END,
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        RETURN to_jsonb(s);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.so_cong_ghi_job(p_id uuid,p_instance uuid,p_the_he bigint,p_ten text)
    RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        s:=loi.so_cong_giu(p_id,p_instance,p_the_he);
        IF p_ten IS DISTINCT FROM 'Global\ktt-'||p_id::text||'-'||p_instance::text THEN
            RAISE EXCEPTION 'CONG_DAU_VAO' USING ERRCODE='22023';
        END IF;
        UPDATE loi.module_phien_chay SET ten_job=p_ten
            WHERE id=p_instance AND so_cong_id=p_id AND the_he=p_the_he AND ten_job IS NULL;
        UPDATE loi.engine_phien_chay SET ten_job=p_ten
            WHERE id=p_instance AND so_cong_id=p_id AND the_he=p_the_he AND ten_job IS NULL;
        RETURN true;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.so_cong_doc_phien(p_id uuid) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong; p jsonb;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        IF s.module IS NOT NULL THEN
            SELECT jsonb_build_object('id',id,'the_he',the_he,'pid',pid,
                'dinh_danh_lan_tao',dinh_danh_lan_tao,'ten_job',ten_job) INTO p
                FROM loi.module_phien_chay WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        ELSE
            SELECT jsonb_build_object('id',id,'the_he',the_he,'pid',pid,
                'dinh_danh_lan_tao',dinh_danh_lan_tao,'ten_job',ten_job) INTO p
                FROM loi.engine_phien_chay WHERE id=s.giu_boi AND so_cong_id=s.id AND the_he=s.the_he;
        END IF;
        RETURN p;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.so_cong_doi_chieu(p_id uuid,p_instance uuid,p_the_he bigint,p_doi_chieu uuid)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE s loi.so_cong;
    BEGIN
        PERFORM loi.so_cong_chi_core();
        IF p_doi_chieu IS NULL THEN
            RAISE EXCEPTION 'CONG_CAN_DOI_CHIEU' USING ERRCODE='22023';
        END IF;
        SELECT * INTO s FROM loi.so_cong WHERE id=p_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'CONG_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        IF p_instance IS NULL OR s.giu_boi IS DISTINCT FROM p_instance
            OR s.the_he IS DISTINCT FROM p_the_he OR s.het_hieu_luc_luc IS NOT NULL THEN
            RAISE EXCEPTION 'CONG_CAS' USING ERRCODE='40001';
        END IF;
        -- Cung nghia UUID bang chung/audit nhu nhanh p_doi_chieu cua 016.
        -- Giu LOI cho den Admin; lease chua het van duoc thu neu OS/Job da xac nhan.
        PERFORM loi.so_cong_dong_phien(s,'GIAN_DOAN');
        PERFORM loi.ghi_kiem_toan('CORE:CONG:DOI_CHIEU','so_cong',s.id,'DAT',p_request_id=>p_doi_chieu);
        UPDATE loi.so_cong SET giu_boi=NULL,giu_den=NULL,
            trang_thai=CASE WHEN trang_thai='LOI' THEN 'LOI' ELSE 'TRONG' END,
            phien_ban_dong=phien_ban_dong+1 WHERE id=s.id RETURNING * INTO s;
        RETURN to_jsonb(s);
    END;
    $ham$;

    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname IN
            ('so_cong_vong_doi','so_cong_loi_khoi_dong','so_cong_loi_chua_nhan','so_cong_mo_khoa','so_cong_ghi_job',
             'so_cong_doc_phien','so_cong_doi_chieu') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I,%I',
            ham.ck,tt||'vai_chay_loi',tt||'dang_nhap_loi',tt||'dang_nhap_cai_dat');
        IF ham.proname<>'so_cong_vong_doi' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,tt||'dang_nhap_loi');
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
