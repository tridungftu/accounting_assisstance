-- G2-04: lead ap sau 001/002/003, caller quan ly transaction.
-- G2-25 se cung cap cua ap goi da kiem cho login cai dat; khong cap DDL o day.
-- Lich su Core moi KHONG xac nhan 67 migration cu da chay.
-- Nguon doi chieu: M0013_COMMON (khong full-M9), M0017 SQL import hien hanh.
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
        RAISE EXCEPTION 'G2-04: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_namespace
                   WHERE nspname = 'loi' AND pg_catalog.pg_get_userbyid(nspowner) = vai_chu)
       OR pg_catalog.to_regprocedure('loi.xac_minh_phien(text,text,uuid,text,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-04: Can lead, ap G2-01/02/03 dung owner truoc';
    END IF;
    FOREACH ten_bang IN ARRAY ARRAY['nhat_ky_kiem_toan', 'lich_su_doi_cau_truc'] LOOP
        IF EXISTS (SELECT FROM pg_catalog.pg_class
                   WHERE oid = pg_catalog.to_regclass('loi.' || ten_bang)
                     AND (pg_catalog.pg_get_userbyid(relowner) <> vai_chu OR relkind <> 'r')) THEN
            RAISE EXCEPTION 'G2-04: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);

    CREATE TABLE IF NOT EXISTS loi.nhat_ky_kiem_toan (
        id bigserial PRIMARY KEY,
        tao_luc timestamptz NOT NULL DEFAULT statement_timestamp(),
        dang_nhap_csdl name NOT NULL DEFAULT session_user,
        nguoi_dung_id uuid REFERENCES loi.nguoi_dung(id),
        phap_nhan_id uuid REFERENCES loi.phap_nhan(id),
        module text,
        hanh_dong text NOT NULL CHECK (hanh_dong ~ '^[A-Za-z][A-Za-z0-9_.:-]{0,95}$'),
        doi_tuong text NOT NULL CHECK (doi_tuong ~ '^[A-Za-z][A-Za-z0-9_.:-]{0,95}$'),
        doi_tuong_id uuid,
        ket_luan text NOT NULL CHECK (ket_luan IN ('DAT', 'KHONG_DAT', 'TU_CHOI', 'LOI', 'CHO')),
        request_id uuid,
        viec_id uuid,
        buoc_id uuid,
        lan_thu_id uuid,
        CHECK ((nguoi_dung_id IS NULL AND phap_nhan_id IS NULL AND module IS NULL)
            OR (nguoi_dung_id IS NOT NULL AND phap_nhan_id IS NOT NULL AND module IS NOT NULL))
    );
    CREATE INDEX IF NOT EXISTS nhat_ky_kiem_toan_phap_nhan_luc
        ON loi.nhat_ky_kiem_toan (phap_nhan_id, tao_luc, id);
    CREATE TABLE IF NOT EXISTS loi.lich_su_doi_cau_truc (
        ma_goi text NOT NULL CHECK (ma_goi ~ '^[a-z][a-z0-9_]{0,62}$'),
        so_phien_ban integer NOT NULL CHECK (so_phien_ban > 0),
        ma_bam text NOT NULL CHECK (ma_bam ~ '^[0-9a-f]{64}$'),
        ap_dung_luc timestamptz NOT NULL DEFAULT statement_timestamp(),
        nguoi_ap_dung name NOT NULL DEFAULT session_user,
        nguon_lich_su jsonb NOT NULL CHECK (jsonb_typeof(nguon_lich_su) = 'object'),
        PRIMARY KEY (ma_goi, so_phien_ban)
    );
    FOREACH ten_bang IN ARRAY ARRAY['nhat_ky_kiem_toan', 'lich_su_doi_cau_truc'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY', ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY', ten_bang);
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_policy
                       WHERE polrelid = format('loi.%I', ten_bang)::regclass
                         AND polname = 'kiem_toan_chu') THEN
            EXECUTE format('CREATE POLICY kiem_toan_chu ON loi.%I TO %I
                USING (true) WITH CHECK (true)', ten_bang, vai_chu);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC, %I, %I, %I',
                       ten_bang, vai_chay, login_loi, login_cai_dat);
    END LOOP;
    REVOKE ALL ON SEQUENCE loi.nhat_ky_kiem_toan_id_seq FROM PUBLIC;
    EXECUTE format('REVOKE ALL ON SEQUENCE loi.nhat_ky_kiem_toan_id_seq FROM %I, %I, %I',
                   vai_chay, login_loi, login_cai_dat);

    CREATE OR REPLACE FUNCTION loi.chan_sua_kiem_toan()
    RETURNS trigger LANGUAGE plpgsql
    SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        RAISE EXCEPTION 'Nhat ky va lich su doi cau truc chi duoc ghi them'
            USING ERRCODE = '55000';
    END;
    $ham$;
    FOREACH ten_bang IN ARRAY ARRAY['nhat_ky_kiem_toan', 'lich_su_doi_cau_truc'] LOOP
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_trigger
                       WHERE tgrelid = format('loi.%I', ten_bang)::regclass
                         AND tgname = 'chan_sua_kiem_toan') THEN
            EXECUTE format('CREATE TRIGGER chan_sua_kiem_toan BEFORE UPDATE OR DELETE OR TRUNCATE
                ON loi.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()', ten_bang);
        END IF;
    END LOOP;

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
        IF NEW.so_phien_ban <> ban_cu + 1 THEN
            RAISE EXCEPTION 'MIGRATION_ORDER' USING ERRCODE = '23514';
        END IF;
        NEW.nguoi_ap_dung := session_user;
        NEW.ap_dung_luc := statement_timestamp();
        RETURN NEW;
    END;
    $ham$;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_trigger
                   WHERE tgrelid = 'loi.lich_su_doi_cau_truc'::regclass
                     AND tgname = 'kiem_lich_su_doi_cau_truc') THEN
        CREATE TRIGGER kiem_lich_su_doi_cau_truc BEFORE INSERT ON loi.lich_su_doi_cau_truc
            FOR EACH ROW EXECUTE FUNCTION loi.kiem_lich_su_doi_cau_truc();
    END IF;

    -- Chi nhan ma hanh dong/loai doi tuong va UUID, khong nhan JSON hay van ban tu do.
    -- Ma phien chi la tham so xac minh, khong luu phien_id/ma/bam ma vao audit.
    CREATE OR REPLACE FUNCTION loi.ghi_kiem_toan(
        p_hanh_dong text, p_doi_tuong text, p_doi_tuong_id uuid, p_ket_luan text,
        p_ma text DEFAULT NULL, p_module text DEFAULT NULL, p_phap_nhan_id uuid DEFAULT NULL,
        p_request_id uuid DEFAULT NULL, p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL,
        p_buoc_id uuid DEFAULT NULL, p_lan_thu_id uuid DEFAULT NULL
    ) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        danh_tinh record;
        nguoi uuid;
        phap_nhan uuid;
        module_da_kiem text;
        ket_qua bigint;
    BEGIN
        -- Tu choi truoc INSERT de loi CHECK khong dua gia tri vao DETAIL cua log.
        IF p_hanh_dong IS NULL OR p_hanh_dong !~ '^[A-Za-z][A-Za-z0-9_.:-]{0,95}$'
           OR p_doi_tuong IS NULL OR p_doi_tuong !~ '^[A-Za-z][A-Za-z0-9_.:-]{0,95}$'
           OR p_ket_luan IS NULL OR p_ket_luan NOT IN ('DAT', 'KHONG_DAT', 'TU_CHOI', 'LOI', 'CHO')
           OR (p_ma IS NOT NULL AND p_ma <> ''
               AND (strpos(p_hanh_dong, p_ma) > 0 OR strpos(p_doi_tuong, p_ma) > 0)) THEN
            RAISE EXCEPTION 'Metadata kiem toan khong hop le' USING ERRCODE = '23514';
        END IF;
        IF p_ma IS NOT NULL OR p_module IS NOT NULL OR p_phap_nhan_id IS NOT NULL THEN
            SELECT * INTO danh_tinh FROM loi.xac_minh_phien(
                p_ma, p_module, p_phap_nhan_id, p_hanh_dong, p_viec_id, p_the_he);
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Khong the ghi kiem toan' USING ERRCODE = '42501';
            END IF;
            nguoi := danh_tinh.nguoi_dung_id;
            phap_nhan := danh_tinh.phap_nhan_id;
            module_da_kiem := danh_tinh.module;
        ELSIF session_user <> regexp_replace(current_user, 'vai_doi_cau_truc_loi$', 'dang_nhap_loi')
              OR p_viec_id IS NOT NULL OR p_the_he IS NOT NULL
              OR p_buoc_id IS NOT NULL OR p_lan_thu_id IS NOT NULL THEN
            RAISE EXCEPTION 'Khong the ghi kiem toan' USING ERRCODE = '42501';
        END IF;
        INSERT INTO loi.nhat_ky_kiem_toan (nguoi_dung_id, phap_nhan_id, module,
            hanh_dong, doi_tuong, doi_tuong_id, ket_luan, request_id, viec_id, buoc_id, lan_thu_id)
        VALUES (nguoi, phap_nhan, module_da_kiem, p_hanh_dong, p_doi_tuong,
            p_doi_tuong_id, p_ket_luan, p_request_id, p_viec_id, p_buoc_id, p_lan_thu_id)
        RETURNING id INTO ket_qua;
        RETURN ket_qua;
    END;
    $ham$;
    FOR ham IN SELECT p.oid::regprocedure AS chu_ky, p.proname
        FROM pg_catalog.pg_proc p WHERE p.pronamespace = 'loi'::regnamespace
          AND p.proname IN ('chan_sua_kiem_toan', 'kiem_lich_su_doi_cau_truc', 'ghi_kiem_toan')
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I, %I',
                       ham.chu_ky, vai_chay, login_loi, login_cai_dat);
        IF ham.proname = 'ghi_kiem_toan' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I', ham.chu_ky, login_loi);
        END IF;
    END LOOP;
    PERFORM set_config('search_path', duong_tim_truoc, true);
    PERFORM set_config('role', vai_truoc, true);
END;
$$;
