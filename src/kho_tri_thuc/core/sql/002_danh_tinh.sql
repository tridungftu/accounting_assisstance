-- G2-02: dinh nghia cuoi M0001 + mo rong danh tinh M0010, khong chay chuoi cu.
-- Lead provisioning sau 001_vai.sql; caller quan ly transaction.
-- CHUA_KIEM/CAN LEAD: G2-03 phai them policy dua tren phien da xac minh va
-- chuc trach quan tri. Cho den do, RLS dong mac dinh (ke ca owner), khong
-- suy quyen tu session_user, GUC actor/phap nhan, vai_tro hay danh muc vai.
-- Khong tao ham/phien gia de mo quyen tam. Khong nap nhan su that/DEMO.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    vai_chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    vai_chay constant text := tien_to || 'vai_chay_loi';
    vai_truoc constant text := current_setting('role');
    duong_tim_truoc constant text := current_setting('search_path');
    ten_bang text;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63 THEN
        RAISE EXCEPTION 'G2-02: tien to role khong hop le';
    END IF;
    IF tien_to <> '' AND current_database() !~ '^kho_test_' THEN
        RAISE EXCEPTION 'G2-02: tien to role chi dung trong kho_test_*';
    END IF;
    IF current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$' THEN
        RAISE EXCEPTION 'G2-02: tu choi dich ngoai Core DEMO/test';
    END IF;
    IF current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-02: can PostgreSQL 16 tro len';
    END IF;
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_namespace n
        JOIN pg_catalog.pg_roles r ON r.oid = n.nspowner
        WHERE n.nspname = 'loi' AND r.rolname = vai_chu
    ) OR NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = vai_chay
            AND NOT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls
            AND NOT rolcreaterole AND NOT rolcreatedb
    ) THEN
        RAISE EXCEPTION 'G2-02: Can lead, phai ap G2-01 dung owner/role truoc';
    END IF;
    -- Khong doi owner ngam cua doi tuong da ton tai.
    IF EXISTS (
        SELECT FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'loi'
          AND c.relname IN ('nguoi_dung', 'phap_nhan', 'phap_nhan_boi_canh',
                            'phan_quyen', 'vai_nghiep_vu', 'thanh_vien')
          AND (pg_catalog.pg_get_userbyid(c.relowner) <> vai_chu
               OR c.relkind <> CASE WHEN c.relname = 'thanh_vien'
                                    THEN 'v'::"char" ELSE 'r'::"char" END)
    ) THEN
        RAISE EXCEPTION 'G2-02: Can lead, doi tuong danh tinh sai owner/loai';
    END IF;

    -- Provisioning tao truc tiep duoi owner; login runtime/cai dat khong SET ROLE.
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);
    CREATE TABLE IF NOT EXISTS loi.vai_nghiep_vu (
        ma text PRIMARY KEY,
        ten text NOT NULL
    );
    -- Day la danh muc, khong phai ma tran cap quyen.
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_policy
                   WHERE polrelid = 'loi.vai_nghiep_vu'::regclass
                     AND polname = 'vai_nghiep_vu_chu') THEN
        EXECUTE format('CREATE POLICY vai_nghiep_vu_chu ON loi.vai_nghiep_vu
            TO %I USING (true) WITH CHECK (true)', vai_chu);
    END IF;
    INSERT INTO loi.vai_nghiep_vu (ma, ten) VALUES
        ('KE_TOAN', 'Ke toan'), ('KE_TOAN_TRUONG', 'Ke toan truong'),
        ('CFO', 'CFO'), ('NHAP_JUNSKY', 'Nhap Junsky'), ('XEM', 'Xem'),
        ('BAN_HANG', 'Ban hang'), ('DU_AN', 'Du an')
    ON CONFLICT (ma) DO NOTHING;

    CREATE TABLE IF NOT EXISTS loi.nguoi_dung (
        id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
        ten text NOT NULL,
        dang_nhap text NOT NULL UNIQUE,
        vai_tro text NOT NULL REFERENCES loi.vai_nghiep_vu(ma)
            CHECK (vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG','CFO','NHAP_JUNSKY',
                               'XEM','BAN_HANG','DU_AN')),
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG',
        mo_phong boolean NOT NULL DEFAULT false,
        CONSTRAINT nguoi_dung_mo_phong_ten
            CHECK (NOT mo_phong OR left(dang_nhap, 9) = 'MO_PHONG_')
    );
    CREATE TABLE IF NOT EXISTS loi.phap_nhan (
        id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
        ma text NOT NULL UNIQUE,
        ten text NOT NULL,
        mst text,
        ma_don_vi_junsky text UNIQUE,
        che_do_ke_toan text NOT NULL DEFAULT 'TT200',
        nam_tai_chinh text NOT NULL DEFAULT 'DUONG_LICH',
        tien_te char(3) NOT NULL DEFAULT 'VND',
        bi_danh_ai text,
        moc_hoc date,
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG',
        tao_luc timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS loi.phap_nhan_boi_canh (
        id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        muc smallint NOT NULL CHECK (muc BETWEEN 0 AND 13),
        tieu_de text,
        noi_dung text,
        noi_dung_json jsonb,
        gui_ai boolean NOT NULL DEFAULT true,
        nguon text,
        nguoi_duyet text,
        duyet_luc timestamptz,
        hieu_luc_tu timestamptz NOT NULL DEFAULT now(),
        hieu_luc_den timestamptz,
        UNIQUE (phap_nhan_id, muc, phien_ban)
    );
    CREATE TABLE IF NOT EXISTS loi.phan_quyen (
        id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        duyet_loai_viec text[] NOT NULL DEFAULT '{}',
        module text[] NOT NULL DEFAULT '{}',
        UNIQUE (nguoi_dung_id, phap_nhan_id)
    );
    -- View dung quyen caller/RLS bang goc, khong luu ban sao thanh vien.
    CREATE OR REPLACE VIEW loi.thanh_vien WITH (security_invoker = true) AS
        SELECT id, nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module
        FROM loi.phan_quyen;

    FOREACH ten_bang IN ARRAY ARRAY['nguoi_dung', 'phap_nhan',
                                   'phap_nhan_boi_canh', 'phan_quyen', 'vai_nghiep_vu'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY', ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY', ten_bang);
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC', ten_bang);
        -- Chi pham vi tao/tra. Khong UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER.
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM %I', ten_bang, vai_chay);
        EXECUTE format('GRANT SELECT ON TABLE loi.%I TO %I', ten_bang, vai_chay);
        IF ten_bang <> 'vai_nghiep_vu' AND NOT EXISTS (
            SELECT FROM pg_catalog.pg_policy p
            JOIN pg_catalog.pg_class c ON c.oid = p.polrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'loi' AND c.relname = ten_bang
              AND p.polname = 'danh_tinh_cho_phien'
        ) THEN
            EXECUTE format('CREATE POLICY danh_tinh_cho_phien ON loi.%I
                TO %I USING (false) WITH CHECK (false)', ten_bang, vai_chay);
        END IF;
    END LOOP;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_policy
                   WHERE polrelid = 'loi.vai_nghiep_vu'::regclass
                     AND polname = 'vai_nghiep_vu_doc') THEN
        EXECUTE format('CREATE POLICY vai_nghiep_vu_doc ON loi.vai_nghiep_vu
            FOR SELECT TO %I USING (true)', vai_chay);
    END IF;
    EXECUTE format('GRANT INSERT (dang_nhap, ten, vai_tro, mo_phong)
                   ON loi.nguoi_dung TO %I', vai_chay);
    EXECUTE format('GRANT INSERT (ma, ten, mst) ON loi.phap_nhan TO %I', vai_chay);
    EXECUTE format('GRANT INSERT (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                   ON loi.phan_quyen TO %I', vai_chay);
    REVOKE ALL ON TABLE loi.thanh_vien FROM PUBLIC;
    EXECUTE format('REVOKE ALL ON TABLE loi.thanh_vien FROM %I', vai_chay);
    EXECUTE format('GRANT SELECT ON TABLE loi.thanh_vien TO %I', vai_chay);
    PERFORM set_config('search_path', duong_tim_truoc, true);
    PERFORM set_config('role', vai_truoc, true);
END;
$$;
