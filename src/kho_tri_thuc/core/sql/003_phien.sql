-- G2-03: lead ap sau 001/002, caller giu transaction; khong tu commit.
-- Lead phai tat log tham so tren moi login/ket noi:
-- log_parameter_max_length = 0; log_parameter_max_length_on_error = 0.
-- Registry module/FK (G2-05), MTQ (G2-06), lease (G2-14) noi qua cua Core.
-- Khong mo policy runtime cua G2-02 tai lat nay.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    vai_chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    vai_chay constant text := tien_to || 'vai_chay_loi';
    login_loi constant text := tien_to || 'dang_nhap_loi';
    vai_truoc constant text := current_setting('role');
    duong_tim_truoc constant text := current_setting('search_path');
    ten_bang text;
    ham record;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63 THEN
        RAISE EXCEPTION 'G2-03: tien to role khong hop le';
    END IF;
    IF tien_to <> '' AND current_database() !~ '^kho_test_' THEN
        RAISE EXCEPTION 'G2-03: tien to role chi dung trong kho_test_*';
    END IF;
    IF current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-03: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_namespace n
        WHERE n.nspname = 'loi' AND pg_catalog.pg_get_userbyid(n.nspowner) = vai_chu
    ) OR pg_catalog.to_regclass('loi.phan_quyen') IS NULL THEN
        RAISE EXCEPTION 'G2-03: Can lead, ap G2-01/02 dung owner truoc';
    END IF;
    IF EXISTS (
        SELECT FROM pg_catalog.pg_class c
        WHERE c.oid = pg_catalog.to_regclass('loi.phien_xac_thuc')
          AND (pg_catalog.pg_get_userbyid(c.relowner) <> vai_chu OR c.relkind <> 'r')
    ) THEN
        RAISE EXCEPTION 'G2-03: Can lead, bang phien sai owner/loai';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);

    -- Bang xac thuc toan cuc: owner co policy rieng, runtime khong co ACL.
    CREATE TABLE IF NOT EXISTS loi.phien_xac_thuc (
        id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
        ma_bam bytea NOT NULL UNIQUE CHECK (octet_length(ma_bam) = 32),
        nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        module text NOT NULL CHECK (btrim(module) <> ''),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        dang_nhap_csdl name NOT NULL,
        pham_vi_hanh_dong text[] NOT NULL CHECK (
            cardinality(pham_vi_hanh_dong) > 0
            AND array_position(pham_vi_hanh_dong, NULL) IS NULL
            AND NOT (pham_vi_hanh_dong && ARRAY['', '*']::text[])),
        loai text NOT NULL CHECK (loai IN ('NGUOI_DUNG', 'UY_NHIEM_PHIEN', 'UY_NHIEM_VIEC')),
        phien_goc_id uuid REFERENCES loi.phien_xac_thuc(id),
        viec_id uuid,
        the_he bigint,
        tao_luc timestamptz NOT NULL DEFAULT statement_timestamp(),
        hieu_luc_den timestamptz NOT NULL CHECK (isfinite(hieu_luc_den)),
        thu_hoi_luc timestamptz,
        CHECK (hieu_luc_den > tao_luc),
        CHECK ((loai = 'UY_NHIEM_VIEC' AND viec_id IS NOT NULL AND the_he IS NOT NULL AND the_he > 0)
            OR (loai <> 'UY_NHIEM_VIEC' AND viec_id IS NULL AND the_he IS NULL)),
        CHECK ((loai = 'NGUOI_DUNG' AND phien_goc_id IS NULL)
            OR (loai = 'UY_NHIEM_PHIEN' AND phien_goc_id IS NOT NULL)
            OR loai = 'UY_NHIEM_VIEC')
    );
    CREATE INDEX IF NOT EXISTS phien_xac_thuc_nguoi_dung
        ON loi.phien_xac_thuc (nguoi_dung_id, phap_nhan_id);
    CREATE INDEX IF NOT EXISTS phien_xac_thuc_phien_goc
        ON loi.phien_xac_thuc (phien_goc_id);
    CREATE INDEX IF NOT EXISTS phien_xac_thuc_viec_the_he
        ON loi.phien_xac_thuc (viec_id, the_he DESC) WHERE viec_id IS NOT NULL;
    ALTER TABLE loi.phien_xac_thuc ENABLE ROW LEVEL SECURITY;
    ALTER TABLE loi.phien_xac_thuc FORCE ROW LEVEL SECURITY;
    FOREACH ten_bang IN ARRAY ARRAY['phien_xac_thuc', 'nguoi_dung', 'phap_nhan', 'phan_quyen'] LOOP
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_policy
                       WHERE polrelid = format('loi.%I', ten_bang)::regclass
                         AND polname = 'phien_chu_xac_thuc') THEN
            -- Chi owner ham xac thuc, khong cap policy nay cho runtime.
            EXECUTE format('CREATE POLICY phien_chu_xac_thuc ON loi.%I
                TO %I USING (true) WITH CHECK (true)', ten_bang, vai_chu);
        END IF;
    END LOOP;
    REVOKE ALL ON TABLE loi.phien_xac_thuc FROM PUBLIC;
    EXECUTE format('REVOKE ALL ON TABLE loi.phien_xac_thuc FROM %I, %I', vai_chay, login_loi);

    CREATE OR REPLACE FUNCTION loi.cap_phien(
        p_ma text, p_nguoi_dung_id uuid, p_module text, p_phap_nhan_id uuid,
        p_dang_nhap_csdl text, p_pham_vi text[], p_hieu_luc_den timestamptz,
        p_loai text, p_ma_goc text DEFAULT NULL,
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        goc loi.phien_xac_thuc%ROWTYPE;
        ket_qua uuid;
    BEGIN
        -- Khoa cung thu hoi/thay doi quyen truoc khi doc danh tinh.
        PERFORM pg_advisory_xact_lock(hashtextextended(p_nguoi_dung_id::text, 3));
        IF p_ma IS NULL OR p_ma !~ '^[A-Za-z0-9_-]{43,128}$'
           OR p_hieu_luc_den IS NULL OR NOT isfinite(p_hieu_luc_den)
           OR p_hieu_luc_den <= statement_timestamp()
           OR p_module IS NULL OR btrim(p_module) = ''
           OR p_loai IS NULL OR p_loai NOT IN ('NGUOI_DUNG', 'UY_NHIEM_PHIEN', 'UY_NHIEM_VIEC')
           OR p_pham_vi IS NULL OR cardinality(p_pham_vi) = 0
           OR EXISTS (SELECT FROM unnest(p_pham_vi) h WHERE h IS NULL OR btrim(h) = '' OR h = '*')
           OR NOT EXISTS (SELECT FROM pg_catalog.pg_roles
                          WHERE rolname = p_dang_nhap_csdl AND rolcanlogin
                            AND NOT rolsuper AND NOT rolbypassrls)
           OR NOT EXISTS (SELECT FROM loi.nguoi_dung
                          WHERE id = p_nguoi_dung_id AND trang_thai = 'HOAT_DONG' AND NOT mo_phong)
           OR NOT EXISTS (SELECT FROM loi.phap_nhan
                          WHERE id = p_phap_nhan_id AND trang_thai = 'HOAT_DONG') THEN
            RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
        END IF;
        IF p_loai = 'NGUOI_DUNG' AND (p_ma_goc IS NOT NULL OR p_dang_nhap_csdl <> session_user) THEN
            RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
        END IF;
        IF p_ma_goc IS NOT NULL THEN
            SELECT * INTO goc FROM loi.phien_xac_thuc
            WHERE ma_bam = sha256(convert_to(p_ma_goc, 'UTF8'))
              AND loai = 'NGUOI_DUNG' AND dang_nhap_csdl = session_user
              AND nguoi_dung_id = p_nguoi_dung_id AND module = p_module
              AND phap_nhan_id = p_phap_nhan_id
              AND thu_hoi_luc IS NULL AND hieu_luc_den > statement_timestamp()
            FOR UPDATE;
            IF NOT FOUND OR p_hieu_luc_den > goc.hieu_luc_den
               OR NOT p_pham_vi <@ goc.pham_vi_hanh_dong THEN
                RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
            END IF;
        ELSIF p_loai = 'UY_NHIEM_PHIEN' THEN
            RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
        END IF;
        IF p_loai = 'UY_NHIEM_VIEC' THEN
            IF p_viec_id IS NULL OR p_the_he IS NULL OR p_the_he <= 0 THEN
                RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended(p_viec_id::text, 14));
            IF EXISTS (SELECT FROM loi.phien_xac_thuc
                       WHERE viec_id = p_viec_id AND the_he >= p_the_he) THEN
                RAISE EXCEPTION 'The he viec khong hop le' USING ERRCODE = '22023';
            END IF;
            UPDATE loi.phien_xac_thuc SET thu_hoi_luc = coalesce(thu_hoi_luc, statement_timestamp())
            WHERE viec_id = p_viec_id;
        ELSIF p_viec_id IS NOT NULL OR p_the_he IS NOT NULL THEN
            RAISE EXCEPTION 'Khong the cap phien' USING ERRCODE = '22023';
        END IF;
        INSERT INTO loi.phien_xac_thuc (ma_bam, nguoi_dung_id, module, phap_nhan_id,
            dang_nhap_csdl, pham_vi_hanh_dong, hieu_luc_den, loai, phien_goc_id, viec_id, the_he)
        VALUES (sha256(convert_to(p_ma, 'UTF8')), p_nguoi_dung_id, p_module, p_phap_nhan_id,
            p_dang_nhap_csdl, p_pham_vi, p_hieu_luc_den, p_loai, goc.id, p_viec_id, p_the_he)
        RETURNING id INTO ket_qua;
        RETURN ket_qua;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.xac_minh_phien(
        p_ma text, p_module text, p_phap_nhan_id uuid, p_hanh_dong text,
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS TABLE (phien_id uuid, nguoi_dung_id uuid, module text,
        phap_nhan_id uuid, hanh_dong text, viec_id uuid, the_he bigint, hieu_luc_den timestamptz)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
        SELECT p.id, p.nguoi_dung_id, p.module, p.phap_nhan_id, p_hanh_dong,
               p.viec_id, p.the_he, p.hieu_luc_den
        FROM loi.phien_xac_thuc p
        JOIN loi.nguoi_dung n ON n.id = p.nguoi_dung_id
        JOIN loi.phap_nhan pn ON pn.id = p.phap_nhan_id
        WHERE p.ma_bam = sha256(convert_to(p_ma, 'UTF8'))
          AND p.dang_nhap_csdl = session_user AND p.module = p_module
          AND p.phap_nhan_id = p_phap_nhan_id
          AND p_hanh_dong = ANY(p.pham_vi_hanh_dong)
          AND p.thu_hoi_luc IS NULL AND p.hieu_luc_den > statement_timestamp()
          AND n.trang_thai = 'HOAT_DONG' AND NOT n.mo_phong AND pn.trang_thai = 'HOAT_DONG'
          AND ((p.loai <> 'UY_NHIEM_VIEC' AND p_viec_id IS NULL AND p_the_he IS NULL)
            OR (p.loai = 'UY_NHIEM_VIEC' AND p.viec_id = p_viec_id AND p.the_he = p_the_he
                AND NOT EXISTS (SELECT FROM loi.phien_xac_thuc moi
                                WHERE moi.viec_id = p.viec_id AND moi.the_he > p.the_he)))
          AND (p.phien_goc_id IS NULL OR EXISTS (
              SELECT FROM loi.phien_xac_thuc g
              WHERE g.id = p.phien_goc_id AND g.loai = 'NGUOI_DUNG'
                AND g.nguoi_dung_id = p.nguoi_dung_id AND g.module = p.module
                AND g.phap_nhan_id = p.phap_nhan_id
                AND g.thu_hoi_luc IS NULL AND g.hieu_luc_den > statement_timestamp()
                AND p.hieu_luc_den <= g.hieu_luc_den
                AND p.pham_vi_hanh_dong <@ g.pham_vi_hanh_dong))
    $ham$;

    CREATE OR REPLACE FUNCTION loi.thu_hoi_phien(p_ma text)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE p loi.phien_xac_thuc%ROWTYPE;
    BEGIN
        SELECT * INTO p FROM loi.phien_xac_thuc WHERE ma_bam = sha256(convert_to(p_ma, 'UTF8'));
        IF FOUND THEN
            PERFORM pg_advisory_xact_lock(hashtextextended(p.nguoi_dung_id::text, 3));
            UPDATE loi.phien_xac_thuc SET thu_hoi_luc = coalesce(thu_hoi_luc, statement_timestamp())
            WHERE id = p.id OR phien_goc_id = p.id;
        END IF;
    END;
    $ham$;

    -- Cua nay phai duoc G2-06 goi cung transaction khi MTQ/quyen thay doi.
    CREATE OR REPLACE FUNCTION loi.thu_hoi_phien_nguoi_dung(p_nguoi_dung_id uuid)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        PERFORM pg_advisory_xact_lock(hashtextextended(p_nguoi_dung_id::text, 3));
        UPDATE loi.phien_xac_thuc SET thu_hoi_luc = coalesce(thu_hoi_luc, statement_timestamp())
        WHERE nguoi_dung_id = p_nguoi_dung_id;
    END;
    $ham$;

    -- G2-14 goi khi mat lease/crash, khong can khoi phuc ma bi mat da trao.
    CREATE OR REPLACE FUNCTION loi.thu_hoi_uy_nhiem_viec(p_viec_id uuid, p_the_he bigint)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        IF p_viec_id IS NULL OR p_the_he IS NULL OR p_the_he <= 0 THEN
            RAISE EXCEPTION 'The he viec khong hop le' USING ERRCODE = '22023';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(p_viec_id::text, 14));
        UPDATE loi.phien_xac_thuc SET thu_hoi_luc = coalesce(thu_hoi_luc, statement_timestamp())
        WHERE viec_id = p_viec_id AND the_he <= p_the_he;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.thu_hoi_phien_khi_doi_quyen()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE nguoi uuid;
    BEGIN
        IF TG_TABLE_NAME = 'nguoi_dung' THEN
            PERFORM loi.thu_hoi_phien_nguoi_dung(OLD.id);
        ELSIF TG_TABLE_NAME = 'phap_nhan' THEN
            FOR nguoi IN SELECT DISTINCT nguoi_dung_id FROM loi.phien_xac_thuc
                WHERE phap_nhan_id = OLD.id ORDER BY nguoi_dung_id
            LOOP
                PERFORM loi.thu_hoi_phien_nguoi_dung(nguoi);
            END LOOP;
        ELSIF TG_OP = 'INSERT' THEN
            PERFORM loi.thu_hoi_phien_nguoi_dung(NEW.nguoi_dung_id);
        ELSE
            PERFORM loi.thu_hoi_phien_nguoi_dung(OLD.nguoi_dung_id);
            IF TG_OP = 'UPDATE' AND NEW.nguoi_dung_id <> OLD.nguoi_dung_id THEN
                PERFORM loi.thu_hoi_phien_nguoi_dung(NEW.nguoi_dung_id);
            END IF;
        END IF;
        RETURN NULL;
    END;
    $ham$;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_trigger
                   WHERE tgrelid = 'loi.phan_quyen'::regclass AND tgname = 'phien_doi_quyen') THEN
        CREATE TRIGGER phien_doi_quyen AFTER INSERT OR UPDATE OR DELETE ON loi.phan_quyen
            FOR EACH ROW EXECUTE FUNCTION loi.thu_hoi_phien_khi_doi_quyen();
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_trigger
                   WHERE tgrelid = 'loi.phap_nhan'::regclass AND tgname = 'phien_doi_phap_nhan') THEN
        CREATE TRIGGER phien_doi_phap_nhan AFTER UPDATE OF trang_thai ON loi.phap_nhan
            FOR EACH ROW EXECUTE FUNCTION loi.thu_hoi_phien_khi_doi_quyen();
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_trigger
                   WHERE tgrelid = 'loi.nguoi_dung'::regclass AND tgname = 'phien_doi_tai_khoan') THEN
        CREATE TRIGGER phien_doi_tai_khoan AFTER UPDATE ON loi.nguoi_dung
            FOR EACH ROW EXECUTE FUNCTION loi.thu_hoi_phien_khi_doi_quyen();
    END IF;

    FOR ham IN SELECT p.oid::regprocedure AS chu_ky, p.proname
        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'loi' AND p.proname IN ('cap_phien', 'xac_minh_phien',
            'thu_hoi_phien', 'thu_hoi_phien_nguoi_dung', 'thu_hoi_uy_nhiem_viec',
            'thu_hoi_phien_khi_doi_quyen')
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I', ham.chu_ky, vai_chay, login_loi);
        IF ham.proname <> 'thu_hoi_phien_khi_doi_quyen' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I', ham.chu_ky, login_loi);
        END IF;
        IF ham.proname = 'xac_minh_phien' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I', ham.chu_ky, vai_chay);
        END IF;
    END LOOP;
    -- Module nhan EXECUTE xac_minh_phien rieng khi provisioning; khong nhan cap/thu hoi.
    PERFORM set_config('search_path', duong_tim_truoc, true);
    PERFORM set_config('role', vai_truoc, true);
END;
$$;
