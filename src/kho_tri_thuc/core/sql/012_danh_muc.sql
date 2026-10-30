-- G2-12: dinh nghia dich M0002/3/4/6/9/13_COMMON/15, khong replay lich su.
-- Lien ket chi co DDL, CHUA co cua ghi: G2-13 bo sung kiem tien/resolver.
-- Khong nhan ban ro nhom A hoac JSON nghiep vu module vao danh muc.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_danh_muc';
    chu_loi text := tt || 'vai_doi_cau_truc_loi';
    chu_tl text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
    chay text := tt || 'vai_chay_danh_muc';
    login text := tt || 'dang_nhap_loi';
    vai_cu text := current_setting('role');
    duong_cu text := current_setting('search_path');
    bang text; ham record;
BEGIN
    IF (tt<>'' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(chu_tl)>63 OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-12: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='danh_muc'
                  AND pg_get_userbyid(nspowner)=chu)
       OR to_regprocedure('loi_tai_lieu.bien_nhan_core_v2(text,text,uuid,text,text,text,jsonb,boolean,jsonb,jsonb,text,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-12: Can lead, ap G2-01..11 truoc';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I',chu_loi);
    EXECUTE format('GRANT USAGE ON SCHEMA loi TO %I',chu);
    EXECUTE format('GRANT REFERENCES ON loi.phap_nhan,loi.nguoi_dung,loi.module_danh_muc,loi.nguon_cai_dat TO %I',chu);
    FOR ham IN SELECT oid::regprocedure AS ck FROM pg_proc WHERE pronamespace='loi'::regnamespace
        AND proname IN ('mtq_phien_rls','chan_sua_kiem_toan') LOOP
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,chu);
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu_tl);
    EXECUTE format('GRANT USAGE ON SCHEMA loi_tai_lieu TO %I',chu);
    FOR ham IN SELECT oid::regprocedure AS ck FROM pg_proc WHERE pronamespace='loi_tai_lieu'::regnamespace
        AND proname IN ('ngu_canh','kiem_quyen','tra_bien_nhan_thao_tac_v2',
                         'ghi_bien_nhan_thao_tac_v2','bien_nhan_core_v2') LOOP
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,chu);
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);

    CREATE TABLE IF NOT EXISTS danh_muc.doi_tac (
        id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ten_phap_ly text NOT NULL CHECK(btrim(ten_phap_ly)<>''),
        ten_chuan_hoa text NOT NULL CHECK(btrim(ten_chuan_hoa)<>''),
        mst text, cccd_hash text, cccd_mh bytea,
        loai text NOT NULL CHECK(loai IN ('TC','CN','NHA_NUOC','NGAN_HANG','NOI_BO')),
        vai_tro text[] NOT NULL DEFAULT '{}',
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        CHECK(loai<>'CN' OR mst IS NULL), UNIQUE(id,phap_nhan_id)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS doi_tac_mst_uq ON danh_muc.doi_tac(phap_nhan_id,mst) WHERE mst IS NOT NULL AND hieu_luc_den IS NULL;
    CREATE UNIQUE INDEX IF NOT EXISTS doi_tac_cccd_uq ON danh_muc.doi_tac(phap_nhan_id,cccd_hash) WHERE cccd_hash IS NOT NULL AND hieu_luc_den IS NULL;
    CREATE TABLE IF NOT EXISTS danh_muc.du_an (
        id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ma_junsky text NOT NULL CHECK(btrim(ma_junsky)<>''), ten text NOT NULL CHECK(btrim(ten)<>''), cha_id uuid,
        giai_doan text, trang_thai text NOT NULL DEFAULT 'DAU_TU' CHECK(trang_thai IN ('DAU_TU','VAN_HANH','DONG')),
        ngay_chuyen_van_hanh date,
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        CHECK(cha_id IS DISTINCT FROM id), UNIQUE(id,phap_nhan_id), UNIQUE(phap_nhan_id,ma_junsky),
        FOREIGN KEY(cha_id,phap_nhan_id) REFERENCES danh_muc.du_an(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.tai_khoan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ma_junsky text NOT NULL, ten text NOT NULL, cap smallint,
        tk_cong_no boolean NOT NULL DEFAULT false, tk_tien boolean NOT NULL DEFAULT false,
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        UNIQUE(id,phap_nhan_id), UNIQUE(phap_nhan_id,ma_junsky)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.tai_khoan_ngan_hang (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ngan_hang text NOT NULL, chi_nhanh text, stk_mh bytea, stk_hash text,
        tk_ke_toan text NOT NULL, tien_te text NOT NULL DEFAULT 'VND' CHECK(tien_te ~ '^[A-Z]{3}$'),
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        UNIQUE(id,phap_nhan_id), UNIQUE(phap_nhan_id,tk_ke_toan)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.hop_dong (
        id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module_chu text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai text NOT NULL CHECK(loai IN ('XAY_DUNG','THUE_DAT','BAN_NHA','VAY','MUA','DICH_VU','KHAC')),
        ma_noi_bo text NOT NULL CHECK(btrim(ma_noi_bo)<>''), so_hop_dong text NOT NULL CHECK(btrim(so_hop_dong)<>''),
        doi_tac_id uuid, du_an_id uuid, ngay_ky date,
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        UNIQUE(id,phap_nhan_id), UNIQUE(id,du_an_id), UNIQUE(phap_nhan_id,loai,so_hop_dong), UNIQUE(phap_nhan_id,ma_noi_bo),
        FOREIGN KEY(doi_tac_id,phap_nhan_id) REFERENCES danh_muc.doi_tac(id,phap_nhan_id),
        FOREIGN KEY(du_an_id,phap_nhan_id) REFERENCES danh_muc.du_an(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.chung_tu (
        id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        module_nghiep_vu text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai text NOT NULL CHECK(btrim(loai)<>''),
        khoa_nguon text NOT NULL CHECK(btrim(khoa_nguon)<>''), ngay_nghiep_vu date NOT NULL CHECK(isfinite(ngay_nghiep_vu)),
        ky text NOT NULL CHECK(ky ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
        so_tien_minor numeric(38,0) CHECK(so_tien_minor>=0), tien_te text CHECK(tien_te ~ '^[A-Z]{3}$'),
        thang_tien smallint CHECK(thang_tien BETWEEN 0 AND 12), chieu text CHECK(chieu IN ('THU','CHI')),
        doi_tac_id uuid, du_an_id uuid, ma_bam text NOT NULL CHECK(ma_bam ~ '^[0-9a-f]{64}$'),
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(ky=to_char(ngay_nghiep_vu,'YYYY-MM')),
        CHECK(num_nonnulls(so_tien_minor,tien_te,thang_tien) IN (0,3)),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        UNIQUE(id,phap_nhan_id), UNIQUE(phap_nhan_id,id,module_nghiep_vu), UNIQUE(phap_nhan_id,loai,khoa_nguon),
        FOREIGN KEY(doi_tac_id,phap_nhan_id) REFERENCES danh_muc.doi_tac(id,phap_nhan_id),
        FOREIGN KEY(du_an_id,phap_nhan_id) REFERENCES danh_muc.du_an(id,phap_nhan_id)
    );
    -- Phan chu theo dinh nghia cuoi chung_tu_chu_so_huu_common.
    -- HD_MUA/M1 cu van hop le; projector M2 duoc ghi HD_MUA/M2.
    -- Khong FK module tuy chon chua cai; chung_tu van FK module_danh_muc.
    -- Them loai/module bang dong cau hinh, chi owner goi duoc sua.
    CREATE TABLE IF NOT EXISTS danh_muc.chung_tu_phan_chu (
        loai text NOT NULL CHECK(btrim(loai)<>''),
        module_chu text NOT NULL CHECK(module_chu ~ '^[a-z][a-z0-9_]{0,30}$'),
        loi_tien text, PRIMARY KEY(loai,module_chu)
    );
    IF (SELECT pg_get_userbyid(relowner)<>chu FROM pg_class WHERE oid='danh_muc.chung_tu_phan_chu'::regclass) THEN
        RAISE EXCEPTION 'G2-12: Can lead, sai owner phan chu';
    END IF;
    INSERT INTO danh_muc.chung_tu_phan_chu(loai,module_chu,loi_tien) VALUES
        ('PHIEU_KHO','m5','M5_CHI_SO_LUONG'), ('HOP_DONG_TEP','crm',NULL),
        ('HD_MUA','m1',NULL), ('HD_MUA','m2','M2_TIEN_CHUA_CAN_CU'),
        ('SAO_KE','m1',NULL), ('HD_BAN','m1',NULL), ('BANG_KE_THUE','m1',NULL),
        ('RQ','m1',NULL), ('NGHIEM_THU','m1',NULL), ('BANG_LUONG','m1',NULL),
        ('BANG_KHAU_HAO','m1',NULL), ('LENH_CHI','m1',NULL), ('SO_JUNSKY','m1',NULL),
        ('CONG_NO_MO','m1',NULL), ('BUT_TOAN_DIEU_CHINH','m1',NULL), ('KHAC','m1',NULL),
        ('HO_SO_VAY','m1',NULL)
        ON CONFLICT (loai,module_chu) DO NOTHING;
    IF NOT EXISTS(SELECT FROM pg_constraint WHERE conrelid='danh_muc.chung_tu'::regclass
                  AND conname='chung_tu_phan_chu_fk') THEN
        ALTER TABLE danh_muc.chung_tu ADD CONSTRAINT chung_tu_phan_chu_fk
            FOREIGN KEY(loai,module_nghiep_vu) REFERENCES danh_muc.chung_tu_phan_chu(loai,module_chu);
    END IF;
    ALTER TABLE danh_muc.chung_tu_phan_chu ENABLE ROW LEVEL SECURITY;
    ALTER TABLE danh_muc.chung_tu_phan_chu FORCE ROW LEVEL SECURITY;
    EXECUTE format('REVOKE ALL ON danh_muc.chung_tu_phan_chu FROM PUBLIC,%I,%I',chay,login);
    IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid='danh_muc.chung_tu_phan_chu'::regclass
                  AND polname='phan_chu_goi') THEN
        EXECUTE format('CREATE POLICY phan_chu_goi ON danh_muc.chung_tu_phan_chu TO %I
            USING (true) WITH CHECK (true)',chu);
    END IF;
    CREATE TABLE IF NOT EXISTS danh_muc.hoa_don_danh_tinh (
        id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        chieu text NOT NULL CHECK(chieu='MUA_VAO'), mst_ban text NOT NULL CHECK(mst_ban ~ '^[ -~]+$'),
        mau_so text NOT NULL CHECK(mau_so ~ '^[ -~]+$'), ky_hieu text NOT NULL CHECK(ky_hieu ~ '^[ -~]+$'),
        so_chuan text NOT NULL CHECK(so_chuan ~ '^(0|[1-9][0-9]*)$'),
        nguon_cai_dat_id text NOT NULL REFERENCES loi.nguon_cai_dat(id),
        hieu_luc_tu timestamptz NOT NULL DEFAULT clock_timestamp(), hieu_luc_den timestamptz,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(hieu_luc_den IS NULL OR (isfinite(hieu_luc_den) AND hieu_luc_den>=hieu_luc_tu)),
        UNIQUE(id,phap_nhan_id), UNIQUE(phap_nhan_id,chieu,mst_ban,mau_so,ky_hieu,so_chuan)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.khoa_ky (
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id), ky text NOT NULL CHECK(ky ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
        khoa_luc timestamptz NOT NULL DEFAULT clock_timestamp(), nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        PRIMARY KEY(phap_nhan_id,ky)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.lien_ket_chung_tu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        chung_tu_a_id uuid NOT NULL, chung_tu_b_id uuid,
        loai text NOT NULL, muc_dich_lien_ket text NOT NULL CHECK(muc_dich_lien_ket IN ('MONEY','EVIDENCE')),
        mo_hinh_phan_bo text CHECK(mo_hinh_phan_bo IN ('DIRECT','CHILD')),
        module_nghia_vu text, loai_nghia_vu text, nghia_vu_id uuid,
        phien_ban_can_cu_id uuid, ma_bam_phien_ban_can_cu text CHECK(ma_bam_phien_ban_can_cu ~ '^[0-9a-f]{64}$'),
        so_tien_khop_minor numeric(38,0) CHECK(so_tien_khop_minor>0),
        tien_te text CHECK(tien_te ~ '^[A-Z]{3}$'), thang_tien smallint CHECK(thang_tien BETWEEN 0 AND 12),
        trang_thai text NOT NULL DEFAULT 'CHO' CHECK(trang_thai IN ('CHO','DA_KHOP','HUY')),
        nguoi_duyet_id uuid REFERENCES loi.nguoi_dung(id), duyet_luc timestamptz,
        huy_boi uuid REFERENCES loi.nguoi_dung(id), huy_luc timestamptz, ly_do_huy text,
        muc_danh_muc text, tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(id,phap_nhan_id), CHECK(chung_tu_a_id IS DISTINCT FROM chung_tu_b_id),
        CHECK(trang_thai<>'HUY' OR (huy_boi IS NOT NULL AND huy_luc IS NOT NULL AND btrim(ly_do_huy)<>'' AND ly_do_huy IS NOT NULL)),
        CHECK(num_nonnulls(module_nghia_vu,loai_nghia_vu,nghia_vu_id) IN (0,3)),
        CHECK((muc_dich_lien_ket='MONEY' AND mo_hinh_phan_bo IS NOT NULL)
           OR (muc_dich_lien_ket='EVIDENCE' AND mo_hinh_phan_bo IS NULL AND so_tien_khop_minor IS NULL)),
        FOREIGN KEY(chung_tu_a_id,phap_nhan_id) REFERENCES danh_muc.chung_tu(id,phap_nhan_id),
        FOREIGN KEY(chung_tu_b_id,phap_nhan_id) REFERENCES danh_muc.chung_tu(id,phap_nhan_id)
    );
    CREATE TABLE IF NOT EXISTS danh_muc.lien_ket_phan_bo (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL, lien_ket_id uuid NOT NULL,
        dich_logic_id uuid NOT NULL, module_nghia_vu text NOT NULL, loai_nghia_vu text NOT NULL, nghia_vu_id uuid NOT NULL,
        cau_phan text NOT NULL CHECK(cau_phan IN ('GOC','LAI','PHI','GIAI_NGAN')),
        phien_ban_can_cu_id uuid NOT NULL, ma_bam_phien_ban_can_cu text NOT NULL CHECK(ma_bam_phien_ban_can_cu ~ '^[0-9a-f]{64}$'),
        so_tien_minor numeric(38,0) NOT NULL CHECK(so_tien_minor>0), tien_te text NOT NULL CHECK(tien_te ~ '^[A-Z]{3}$'),
        thang_tien smallint NOT NULL CHECK(thang_tien BETWEEN 0 AND 12),
        trang_thai text NOT NULL DEFAULT 'HIEU_LUC' CHECK(trang_thai IN ('HIEU_LUC','HUY')),
        huy_boi uuid REFERENCES loi.nguoi_dung(id), huy_luc timestamptz, ly_do_huy text,
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(trang_thai<>'HUY' OR (huy_boi IS NOT NULL AND huy_luc IS NOT NULL AND btrim(ly_do_huy)<>'' AND ly_do_huy IS NOT NULL)),
        UNIQUE(id,phap_nhan_id), FOREIGN KEY(lien_ket_id,phap_nhan_id) REFERENCES danh_muc.lien_ket_chung_tu(id,phap_nhan_id)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS lien_ket_phan_bo_dich_uq ON danh_muc.lien_ket_phan_bo(lien_ket_id,dich_logic_id) WHERE trang_thai='HIEU_LUC';

    CREATE OR REPLACE FUNCTION danh_muc.kiem_chu_chung_tu(p_loai text,p_module text) RETURNS text
    LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ma_loi text;
    BEGIN
        SELECT loi_tien INTO ma_loi FROM danh_muc.chung_tu_phan_chu
            WHERE loai=p_loai AND module_chu=p_module;
        IF NOT FOUND THEN RAISE EXCEPTION 'CHU_SO_HUU_SAI' USING ERRCODE='P0001'; END IF;
        RETURN ma_loi;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION danh_muc.chung_tu_chu_so_huu_common() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ma_loi text;
    BEGIN
        IF TG_OP='UPDATE' AND (NEW.module_nghiep_vu IS DISTINCT FROM OLD.module_nghiep_vu
                              OR NEW.loai IS DISTINCT FROM OLD.loai) THEN
            RAISE EXCEPTION 'CHU_SO_HUU_BAT_BIEN' USING ERRCODE='P0001';
        END IF;
        ma_loi := danh_muc.kiem_chu_chung_tu(NEW.loai,NEW.module_nghiep_vu);
        IF ma_loi IS NOT NULL THEN
            IF current_user::text<>(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=TG_RELID) THEN
                RAISE EXCEPTION 'CHUNG_TU_CHI_CHU' USING ERRCODE='42501';
            END IF;
            IF num_nonnulls(NEW.so_tien_minor,NEW.tien_te,NEW.thang_tien,NEW.chieu,NEW.doi_tac_id)>0 THEN
                RAISE EXCEPTION '%',ma_loi USING ERRCODE='P0001';
            END IF;
        END IF;
        -- Trang thai nghiep vu/journal khong nam trong dau chung tu Core.
        RETURN NEW;
    END;
    $ham$;
    IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid='danh_muc.chung_tu'::regclass
                  AND tgname='chung_tu_chu_so_huu_common') THEN
        CREATE TRIGGER chung_tu_chu_so_huu_common BEFORE INSERT OR UPDATE ON danh_muc.chung_tu
            FOR EACH ROW EXECUTE FUNCTION danh_muc.chung_tu_chu_so_huu_common();
    END IF;

    CREATE OR REPLACE FUNCTION danh_muc.chi_het_hieu_luc() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF TG_OP<>'UPDATE' THEN RAISE EXCEPTION 'DANH_MUC_BAT_BIEN' USING ERRCODE='42501'; END IF;
        IF OLD.hieu_luc_den IS NOT NULL OR NEW.hieu_luc_den IS NULL
           OR NEW.phien_ban_dong<>OLD.phien_ban_dong+1
           OR (to_jsonb(NEW)-ARRAY['hieu_luc_den','phien_ban_dong']) IS DISTINCT FROM
              (to_jsonb(OLD)-ARRAY['hieu_luc_den','phien_ban_dong']) THEN
            RAISE EXCEPTION 'DANH_MUC_BAT_BIEN' USING ERRCODE='42501';
        END IF;
        RETURN NEW;
    END;
    $ham$;
    FOREACH bang IN ARRAY ARRAY['doi_tac','du_an','tai_khoan','tai_khoan_ngan_hang','hop_dong',
        'chung_tu','hoa_don_danh_tinh','khoa_ky','lien_ket_chung_tu','lien_ket_phan_bo'] LOOP
        IF (SELECT pg_get_userbyid(relowner)<>chu FROM pg_class WHERE oid=format('danh_muc.%I',bang)::regclass) THEN
            RAISE EXCEPTION 'G2-12: Can lead, sai owner danh muc';
        END IF;
        EXECUTE format('ALTER TABLE danh_muc.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE danh_muc.%I FORCE ROW LEVEL SECURITY',bang);
        EXECUTE format('REVOKE ALL ON danh_muc.%I FROM PUBLIC,%I,%I',bang,chay,login);
        IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid=format('danh_muc.%I',bang)::regclass AND polname='danh_muc_phien') THEN
            EXECUTE format('CREATE POLICY danh_muc_phien ON danh_muc.%I TO %I
                USING (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))
                WITH CHECK (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))',bang,chu);
        END IF;
        IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid=format('danh_muc.%I',bang)::regclass AND tgname='danh_muc_khong_xoa') THEN
            EXECUTE format('CREATE TRIGGER danh_muc_khong_xoa BEFORE DELETE OR TRUNCATE ON danh_muc.%I
                FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
            IF bang IN ('khoa_ky','lien_ket_chung_tu','lien_ket_phan_bo') THEN
                EXECUTE format('CREATE TRIGGER danh_muc_khong_sua BEFORE UPDATE ON danh_muc.%I
                    FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
            ELSE
                EXECUTE format('CREATE TRIGGER danh_muc_khong_sua BEFORE UPDATE ON danh_muc.%I
                    FOR EACH ROW EXECUTE FUNCTION danh_muc.chi_het_hieu_luc()',bang);
            END IF;
        END IF;
    END LOOP;

    -- Cung namespace khoa cho kiem ky, ghi chung tu va khoa ky; giu den commit.
    CREATE OR REPLACE FUNCTION danh_muc.kiem_khoa_ky(p_pn uuid,p_ky text) RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF current_setting('transaction_isolation')<>'read committed' THEN
            RAISE EXCEPTION 'DANH_MUC_CAN_READ_COMMITTED' USING ERRCODE='25000';
        END IF;
        IF p_ky IS NULL OR p_ky !~ '^[0-9]{4}-(0[1-9]|1[0-2])$' THEN
            RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(hashtextextended(jsonb_build_array('khoa_ky',p_pn,p_ky)::text,12));
        IF EXISTS(SELECT FROM danh_muc.khoa_ky WHERE phap_nhan_id=p_pn AND ky=p_ky) THEN
            RAISE EXCEPTION 'KY_DA_KHOA' USING ERRCODE='P0001';
        END IF;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION danh_muc.ghi_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text,p_id uuid,p_khoa text,p_data jsonb,p_contract text DEFAULT '1',
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; doi jsonb; than jsonb; quyen jsonb; cu jsonb; kq jsonb; op text; hd_doc text;
        khoa text[]; ngay date; ky_ghi text; het boolean; n integer; ky_cu text; ban bigint;
    BEGIN
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF p_id IS NULL OR p_pn IS NULL OR jsonb_typeof(p_data) IS DISTINCT FROM 'object'
           OR coalesce(p_contract,'')='' THEN RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023'; END IF;
        het := p_data ? 'row_version';
        CASE p_loai
          WHEN 'doi_tac' THEN khoa := ARRAY['ten_phap_ly','ten_chuan_hoa','mst','loai','vai_tro'];
          WHEN 'du_an' THEN khoa := ARRAY['ma_junsky','ten','cha_id','giai_doan','trang_thai','ngay_chuyen_van_hanh'];
          WHEN 'hop_dong' THEN khoa := ARRAY['loai','ma_noi_bo','so_hop_dong','doi_tac_id','du_an_id','ngay_ky'];
          WHEN 'chung_tu' THEN khoa := ARRAY['loai','khoa_nguon','ngay_nghiep_vu','so_tien_minor','tien_te','thang_tien','chieu','doi_tac_id','du_an_id','ma_bam'];
          WHEN 'hoa_don_danh_tinh' THEN khoa := ARRAY['chieu','mst_ban','mau_so','ky_hieu','so_chuan','nguon_cai_dat_id'];
          WHEN 'khoa_ky' THEN khoa := ARRAY['ky'];
          ELSE RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
        END CASE;
        IF het THEN khoa := ARRAY['row_version']; END IF;
        IF EXISTS(SELECT FROM jsonb_object_keys(p_data) k WHERE NOT k=ANY(khoa))
           OR (het AND (p_loai='khoa_ky' OR coalesce(p_data->>'row_version','') !~ '^[1-9][0-9]{0,18}$'))
           OR split_part(p_hd,':',3) IS DISTINCT FROM (CASE WHEN het THEN 'SUA' WHEN p_loai='khoa_ky' THEN 'DUYET' ELSE 'LAP' END) THEN
            RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        doi := jsonb_build_object('bang','danh_muc.'||p_loai,'id',p_id);
        hd_doc := split_part(p_hd,':',1)||':'||split_part(p_hd,':',2)||':XEM';
        PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,doi,p_contract,'cho_ghi',p_viec,p_the_he);
        IF p_loai='chung_tu' AND NOT het THEN
            PERFORM danh_muc.kiem_chu_chung_tu(p_data->>'loai',p_module);
        END IF;
        op := 'danh_muc.'||p_loai||CASE WHEN het THEN '.het_hieu_luc' ELSE '.lap' END;
        than := jsonb_build_object('phap_nhan_id',p_pn,'doi_tuong',doi,'phien_ban_contract',p_contract,'noi_dung',p_data);
        quyen := jsonb_build_object('hanh_dong',hd_doc,'doi_tuong',doi,'phien_ban_contract',p_contract);
        -- Bien nhan Core 24h chi cho login Core; module dung bien nhan vinh vien.
        IF session_user::text=regexp_replace(current_user::text,'vai_doi_cau_truc_danh_muc$','dang_nhap_loi') THEN
            cu := loi_tai_lieu.bien_nhan_core_v2(p_ma,p_module,p_pn,p_hd,op,p_khoa,than,false,NULL,NULL,'HOAN_TAT',p_viec,p_the_he);
        ELSE
            cu := loi_tai_lieu.tra_bien_nhan_thao_tac_v2(p_ma,p_module,p_pn,p_hd,op,p_khoa,than,p_viec,p_the_he);
        END IF;
        IF cu IS NOT NULL THEN RETURN cu; END IF;
        IF het THEN
            ban := (p_data->>'row_version')::bigint;
            IF p_loai='hop_dong' AND NOT EXISTS(SELECT FROM danh_muc.hop_dong
                WHERE id=p_id AND phap_nhan_id=p_pn AND module_chu=p_module) THEN
                RAISE EXCEPTION 'DANH_MUC_KHONG_THAY' USING ERRCODE='P0002';
            END IF;
            IF p_loai='chung_tu' THEN
                SELECT ky INTO ky_cu FROM danh_muc.chung_tu WHERE id=p_id AND phap_nhan_id=p_pn AND module_nghiep_vu=p_module;
                IF ky_cu IS NULL THEN RAISE EXCEPTION 'DANH_MUC_KHONG_THAY' USING ERRCODE='P0002'; END IF;
                PERFORM danh_muc.kiem_khoa_ky(p_pn,ky_cu);
            END IF;
            EXECUTE format('UPDATE danh_muc.%I SET hieu_luc_den=clock_timestamp(),phien_ban_dong=phien_ban_dong+1
                WHERE id=$1 AND phap_nhan_id=$2 AND phien_ban_dong=$3 AND hieu_luc_den IS NULL',p_loai) USING p_id,p_pn,ban;
            GET DIAGNOSTICS n=ROW_COUNT;
            IF n<>1 THEN RAISE EXCEPTION 'DANH_MUC_XUNG_DOT' USING ERRCODE='P0001'; END IF;
        ELSIF p_loai='doi_tac' THEN
            -- Nhom A do G2-23 cap cong ma hoa; khong nhan CCCD/STK/MST ca nhan ban ro.
            IF p_data->>'loai'='CN' AND p_data->>'mst' IS NOT NULL THEN
                RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
            END IF;
            INSERT INTO danh_muc.doi_tac(id,phap_nhan_id,ten_phap_ly,ten_chuan_hoa,mst,loai,vai_tro,tao_boi)
                VALUES(p_id,p_pn,p_data->>'ten_phap_ly',p_data->>'ten_chuan_hoa',p_data->>'mst',p_data->>'loai',
                    ARRAY(SELECT jsonb_array_elements_text(coalesce(p_data->'vai_tro','[]'::jsonb))),ai);
        ELSIF p_loai='du_an' THEN
            INSERT INTO danh_muc.du_an(id,phap_nhan_id,ma_junsky,ten,cha_id,giai_doan,trang_thai,ngay_chuyen_van_hanh,tao_boi)
                VALUES(p_id,p_pn,p_data->>'ma_junsky',p_data->>'ten',(p_data->>'cha_id')::uuid,p_data->>'giai_doan',
                    coalesce(p_data->>'trang_thai','DAU_TU'),(p_data->>'ngay_chuyen_van_hanh')::date,ai);
        ELSIF p_loai='hop_dong' THEN
            INSERT INTO danh_muc.hop_dong(id,phap_nhan_id,module_chu,loai,ma_noi_bo,so_hop_dong,doi_tac_id,du_an_id,ngay_ky,tao_boi)
                VALUES(p_id,p_pn,p_module,p_data->>'loai',p_data->>'ma_noi_bo',p_data->>'so_hop_dong',
                    (p_data->>'doi_tac_id')::uuid,(p_data->>'du_an_id')::uuid,(p_data->>'ngay_ky')::date,ai);
        ELSIF p_loai='chung_tu' THEN
            ngay := (p_data->>'ngay_nghiep_vu')::date; ky_ghi := to_char(ngay,'YYYY-MM');
            PERFORM danh_muc.kiem_khoa_ky(p_pn,ky_ghi);
            IF p_data ? 'so_tien_minor' AND (jsonb_typeof(p_data->'so_tien_minor') IS DISTINCT FROM 'string'
               OR (p_data->>'so_tien_minor') !~ '^(0|[1-9][0-9]{0,37})$') THEN
                RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
            END IF;
            INSERT INTO danh_muc.chung_tu(id,phap_nhan_id,module_nghiep_vu,loai,khoa_nguon,ngay_nghiep_vu,ky,
                so_tien_minor,tien_te,thang_tien,chieu,doi_tac_id,du_an_id,ma_bam,tao_boi)
                VALUES(p_id,p_pn,p_module,p_data->>'loai',p_data->>'khoa_nguon',ngay,ky_ghi,
                    (p_data->>'so_tien_minor')::numeric,p_data->>'tien_te',(p_data->>'thang_tien')::smallint,p_data->>'chieu',
                    (p_data->>'doi_tac_id')::uuid,(p_data->>'du_an_id')::uuid,p_data->>'ma_bam',ai);
        ELSIF p_loai='hoa_don_danh_tinh' THEN
            INSERT INTO danh_muc.hoa_don_danh_tinh(id,phap_nhan_id,chieu,mst_ban,mau_so,ky_hieu,so_chuan,nguon_cai_dat_id,tao_boi)
                VALUES(p_id,p_pn,p_data->>'chieu',p_data->>'mst_ban',p_data->>'mau_so',p_data->>'ky_hieu',
                    p_data->>'so_chuan',p_data->>'nguon_cai_dat_id',ai);
        ELSE
            ky_ghi := p_data->>'ky';
            -- Lay doc quyen truoc: khong nang shared->exclusive giua hai yeu cau khoa.
            PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array('khoa_ky',p_pn,ky_ghi)::text,12));
            PERFORM danh_muc.kiem_khoa_ky(p_pn,ky_ghi);
            INSERT INTO danh_muc.khoa_ky(phap_nhan_id,ky,nguoi_dung_id) VALUES(p_pn,ky_ghi,ai);
        END IF;
        kq := jsonb_build_object('id',p_id,'phap_nhan_id',p_pn,'row_version',CASE WHEN het THEN (ban+1)::text ELSE '1' END);
        IF session_user::text=regexp_replace(current_user::text,'vai_doi_cau_truc_danh_muc$','dang_nhap_loi') THEN
            RETURN loi_tai_lieu.bien_nhan_core_v2(p_ma,p_module,p_pn,p_hd,op,p_khoa,than,true,kq,quyen,'HOAN_TAT',p_viec,p_the_he);
        END IF;
        RETURN loi_tai_lieu.ghi_bien_nhan_thao_tac_v2(p_ma,p_module,p_pn,p_hd,op,p_khoa,than,kq,quyen,p_viec,p_the_he);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION danh_muc.kiem_khoa_ky_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_chung_tu uuid,p_contract text DEFAULT '1',p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ky_ghi text;
    BEGIN
        PERFORM loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF split_part(p_hd,':',3) NOT IN ('LAP','SUA','DUYET') THEN
            RAISE EXCEPTION 'DANH_MUC_DAU_VAO' USING ERRCODE='22023';
        END IF;
        PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,
            jsonb_build_object('bang','danh_muc.chung_tu','id',p_chung_tu),p_contract,'cho_ghi',p_viec,p_the_he);
        SELECT ky INTO ky_ghi FROM danh_muc.chung_tu WHERE id=p_chung_tu AND phap_nhan_id=p_pn AND module_nghiep_vu=p_module;
        IF ky_ghi IS NULL THEN RAISE EXCEPTION 'DANH_MUC_KHONG_THAY' USING ERRCODE='P0002'; END IF;
        PERFORM danh_muc.kiem_khoa_ky(p_pn,ky_ghi);
    END;
    $ham$;
    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc WHERE pronamespace='danh_muc'::regnamespace
        AND proname IN ('kiem_chu_chung_tu','chung_tu_chu_so_huu_common',
                        'chi_het_hieu_luc','kiem_khoa_ky','ghi_v2','kiem_khoa_ky_v2') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I',ham.ck,chay,login);
        IF ham.proname IN ('ghi_v2','kiem_khoa_ky_v2') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        END IF;
    END LOOP;
    -- Module Manager chi cap dung chu ky V2 duoc duyet; khong GRANT bang/ham noi bo.
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
