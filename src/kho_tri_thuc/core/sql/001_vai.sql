-- G2-01: bootstrap PostgreSQL 16+, do quan tri chay tren CSDL Core DEMO rieng.
-- Mot DO la mot lenh nguyen tu; caller quan ly transaction, khong tu commit.
-- Khong dat/doi mat khau: lead dat rieng qua cong cu dung, ngoai SQL nay.
-- DDL cac lat sau phai duoc tao boi dung vai_doi_cau_truc_<khoi>.
-- Mac dinh tien to rong; test dung set_config('kho_tri_thuc.tien_to_vai', ..., false).
-- Tien to la du lieu, moi dinh danh role deu quote bang format %I.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    login_loi constant text := tien_to || 'dang_nhap_loi';
    login_cai_dat constant text := tien_to || 'dang_nhap_cai_dat';
    cac_khoi constant text[] := ARRAY['loi', 'loi_tai_lieu', 'danh_muc'];
    cac_vai_chay text[] := ARRAY[]::text[];
    cac_vai text[] := ARRAY[login_loi, login_cai_dat];
    khoi text;
    ten_vai text;
    vai_chu text;
    vai_chay text;
    loai_doi_tuong text;
    doi_tuong record;
    la_login boolean;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63 THEN
        RAISE EXCEPTION 'G2-01: tien to role khong hop le';
    END IF;
    IF current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-01: can PostgreSQL 16 tro len';
    END IF;
    IF tien_to <> '' AND current_database() !~ '^kho_test_' THEN
        RAISE EXCEPTION 'G2-01: tien to role chi dung trong kho_test_*';
    END IF;
    IF current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$' THEN
        RAISE EXCEPTION 'G2-01: tu choi dich ngoai Core DEMO/test';
    END IF;
    IF NOT (SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = current_user) THEN
        RAISE EXCEPTION 'G2-01: can lead provisioning bang quan tri';
    END IF;

    FOREACH khoi IN ARRAY cac_khoi LOOP
        cac_vai_chay := cac_vai_chay || (tien_to || 'vai_chay_' || khoi);
        cac_vai := cac_vai || ARRAY[tien_to || 'vai_chay_' || khoi,
                                   tien_to || 'vai_doi_cau_truc_' || khoi];
    END LOOP;
    FOREACH ten_vai IN ARRAY cac_vai LOOP
        la_login := ten_vai IN (login_loi, login_cai_dat);
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = ten_vai) THEN
            EXECUTE format(
                'CREATE ROLE %I %s INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION',
                ten_vai, CASE WHEN la_login THEN 'LOGIN' ELSE 'NOLOGIN' END
            );
        END IF;
        -- Role la doi tuong toan cluster: khong sua ngam role co san sai chuan.
        IF EXISTS (
            SELECT FROM pg_catalog.pg_roles
            WHERE rolname = ten_vai AND (
                rolcanlogin <> la_login OR NOT rolinherit OR rolsuper OR rolbypassrls
                OR rolcreaterole OR rolcreatedb OR rolreplication
            )
        ) THEN
            RAISE EXCEPTION 'G2-01: Can lead, thuoc tinh role sai: %', ten_vai;
        END IF;
    END LOOP;

    -- Bat lech hai chieu, ke ca role ngoai bo nhan owner/runtime.
    IF EXISTS (
        SELECT FROM pg_catalog.pg_auth_members m
        JOIN pg_catalog.pg_roles thanh_vien ON thanh_vien.oid = m.member
        JOIN pg_catalog.pg_roles duoc_cap ON duoc_cap.oid = m.roleid
        WHERE (thanh_vien.rolname = ANY(cac_vai)
               OR duoc_cap.rolname = ANY(cac_vai))
          AND NOT (thanh_vien.rolname = login_loi
                   AND duoc_cap.rolname = ANY(cac_vai_chay))
    ) THEN
        RAISE EXCEPTION 'G2-01: Can lead, membership ngoai pham vi';
    END IF;
    -- Bat moi grantor: GRANT lai chi cap nhat membership cua grantor hien tai.
    IF EXISTS (
        SELECT FROM pg_catalog.pg_auth_members m
        JOIN pg_catalog.pg_roles thanh_vien ON thanh_vien.oid = m.member
        WHERE thanh_vien.rolname = login_loi
          AND (m.admin_option OR m.set_option OR NOT m.inherit_option)
    ) THEN
        RAISE EXCEPTION 'G2-01: Can lead, membership PG16 sai thuoc tinh';
    END IF;

    FOREACH vai_chay IN ARRAY cac_vai_chay LOOP
        EXECUTE format(
            'GRANT %I TO %I WITH INHERIT TRUE, SET FALSE, ADMIN FALSE',
            vai_chay, login_loi
        );
    END LOOP;
    -- Login cai dat khong nhan owner. G2-25 chi cap EXECUTE ham ap goi da kiem.

    -- TEMP/CREATE tu PUBLIC cung la duong DDL, chi thu hoi trong DB DEMO rieng.
    EXECUTE format(
        'REVOKE CREATE, TEMPORARY ON DATABASE %I FROM PUBLIC',
        current_database()
    );
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I, %I',
                   current_database(), login_loi, login_cai_dat);
    FOREACH ten_vai IN ARRAY cac_vai_chay || ARRAY[login_loi, login_cai_dat] LOOP
        EXECUTE format('REVOKE CREATE, TEMPORARY ON DATABASE %I FROM %I',
                       current_database(), ten_vai);
    END LOOP;

    FOREACH khoi IN ARRAY cac_khoi LOOP
        vai_chu := tien_to || 'vai_doi_cau_truc_' || khoi;
        vai_chay := tien_to || 'vai_chay_' || khoi;
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION %I', khoi, vai_chu);
        IF NOT EXISTS (
            SELECT FROM pg_catalog.pg_namespace n
            JOIN pg_catalog.pg_roles r ON r.oid = n.nspowner
            WHERE n.nspname = khoi AND r.rolname = vai_chu
        ) THEN
            RAISE EXCEPTION 'G2-01: Can lead, schema sai owner: %', khoi;
        END IF;
        EXECUTE format('REVOKE ALL ON SCHEMA %I FROM PUBLIC', khoi);
        FOREACH ten_vai IN ARRAY cac_vai_chay || ARRAY[login_loi, login_cai_dat] LOOP
            EXECUTE format('REVOKE CREATE ON SCHEMA %I FROM %I', khoi, ten_vai);
        END LOOP;
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', khoi, vai_chay);
        -- REVOKE dai tra bien ACL NULL thanh ACL owner, du PUBLIC khong co quyen.
        -- Chi cham doi tuong con quyen PUBLIC de giu nguyen anh ACL khi chay lai.
        FOR doi_tuong IN
            SELECT c.relname, c.relkind
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = khoi AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
              AND EXISTS (
                  SELECT FROM pg_catalog.aclexplode(coalesce(c.relacl,
                      pg_catalog.acldefault(
                          CASE WHEN c.relkind = 'S' THEN 'S' ELSE 'r' END::"char",
                          c.relowner))) a WHERE a.grantee = 0
              )
        LOOP
            EXECUTE format('REVOKE ALL ON %s %I.%I FROM PUBLIC',
                           CASE WHEN doi_tuong.relkind = 'S' THEN 'SEQUENCE' ELSE 'TABLE' END,
                           khoi, doi_tuong.relname);
        END LOOP;
        FOR doi_tuong IN
            SELECT p.proname, pg_catalog.pg_get_function_identity_arguments(p.oid) AS doi_so
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = khoi AND EXISTS (
                SELECT FROM pg_catalog.aclexplode(coalesce(p.proacl,
                    pg_catalog.acldefault('f', p.proowner))) a WHERE a.grantee = 0
            )
        LOOP
            EXECUTE format('REVOKE ALL ON ROUTINE %I.%I(%s) FROM PUBLIC',
                           khoi, doi_tuong.proname, doi_tuong.doi_so);
        END LOOP;
        -- Default EXECUTE/USAGE PUBLIC la GLOBAL; revoke chi IN SCHEMA khong du.
        -- Chi owner khong LOGIN tao doi tuong; khong cap DML/EXECUTE dai tra.
        FOREACH loai_doi_tuong IN ARRAY ARRAY['TABLES', 'SEQUENCES', 'FUNCTIONS', 'TYPES'] LOOP
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES FOR ROLE %I REVOKE ALL ON %s FROM PUBLIC',
                vai_chu, loai_doi_tuong
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I REVOKE ALL ON %s FROM PUBLIC',
                vai_chu, khoi, loai_doi_tuong
            );
        END LOOP;
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I REVOKE ALL ON SCHEMAS FROM PUBLIC', vai_chu
        );
    END LOOP;

    -- Khong tu doi owner/thu hoi quyen schema dung chung da co: bao lead neu sai.
    FOREACH ten_vai IN ARRAY cac_vai_chay || ARRAY[login_loi, login_cai_dat] LOOP
        IF EXISTS (
            SELECT FROM pg_catalog.pg_namespace n
            WHERE pg_catalog.has_schema_privilege(ten_vai, n.oid, 'CREATE')
        ) OR EXISTS (
            SELECT FROM pg_catalog.pg_shdepend d
            JOIN pg_catalog.pg_roles r ON r.oid = d.refobjid
            WHERE d.refclassid = 'pg_catalog.pg_authid'::regclass
              AND r.rolname = ten_vai AND d.deptype = 'o'
              AND d.dbid IN (0, (SELECT oid FROM pg_catalog.pg_database
                                 WHERE datname = current_database()))
        ) THEN
            RAISE EXCEPTION 'G2-01: Can lead, runtime/cai dat con owner hoac DDL: %', ten_vai;
        END IF;
    END LOOP;
END;
$$;
