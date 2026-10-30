-- G2-06: nang DDL/loi quyet dinh M0039, cong tap M0057, doc M0058.
-- Chi lay dinh nghia cuoi; resolver nghiep vu cua module goi dong qua G2-05.
-- Caller giu transaction; lead provisioning; khong commit/dich vu.
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
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63
       OR (tien_to <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-06: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname = 'loi'
                   AND pg_get_userbyid(nspowner) = vai_chu)
       OR to_regclass('loi.dang_ky_ham_module') IS NULL
       OR to_regprocedure('loi.xac_minh_phien(text,text,uuid,text,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-06: Can lead, ap G2-01..05 truoc';
    END IF;
    FOREACH ten_bang IN ARRAY ARRAY['mtq_phong','mtq_admin','mtq_danh_muc_hanh_dong','mtq_phien_ban','mtq_dong','mtq_o','mtq_gan_vai','mtq_pham_vi','mtq_kich_hoat','mtq_thay_doi','mtq_tu_choi'] LOOP
        IF EXISTS (SELECT FROM pg_class WHERE oid = to_regclass('loi.' || ten_bang)
                   AND (pg_get_userbyid(relowner) <> vai_chu OR relkind <> 'r')) THEN
            RAISE EXCEPTION 'G2-06: Can lead, bang MTQ sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);
CREATE TABLE IF NOT EXISTS loi.mtq_phong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ma text NOT NULL CHECK (length(btrim(ma)) > 0), ten text NOT NULL CHECK (length(btrim(ten)) > 0),
        hoat_dong boolean NOT NULL DEFAULT true, phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0),
        UNIQUE (phap_nhan_id, ma), UNIQUE (id, phap_nhan_id));

CREATE TABLE IF NOT EXISTS loi.mtq_admin (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        cap_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES loi.nguoi_dung(id), ly_do text NOT NULL,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)));

CREATE TABLE IF NOT EXISTS loi.mtq_danh_muc_hanh_dong (
        phien_ban_danh_muc integer NOT NULL CHECK (phien_ban_danh_muc > 0),
        module text NOT NULL CHECK (module ~ '^[A-Za-z][A-Za-z0-9_]*$'),
        man text NOT NULL, hanh_dong text NOT NULL CHECK (hanh_dong IN ('XEM','LAP','SUA','KIEM','DUYET','HUY')),
        lenh_ky_thuat text NOT NULL, loai_doi_tuong text NOT NULL,
        resolver text NOT NULL CHECK (resolver = 'MAY_CHU_MTQ4'),
        loai_tien text NOT NULL CHECK (loai_tien IN ('PHI_TIEN','TONG_HOP_DONG','XIN_THANH_TOAN')),
        PRIMARY KEY (phien_ban_danh_muc, module, man, hanh_dong),
        UNIQUE (phien_ban_danh_muc, lenh_ky_thuat, loai_doi_tuong));

CREATE TABLE IF NOT EXISTS loi.mtq_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        so_phien_ban integer NOT NULL CHECK (so_phien_ban > 0), phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0),
        duoc_tao_tu uuid, trang_thai text NOT NULL DEFAULT 'NHAP' CHECK (trang_thai IN ('NHAP','DA_CONG_BO')),
        phien_ban_danh_muc integer NOT NULL DEFAULT 1 CHECK (phien_ban_danh_muc = 1),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        cong_bo_boi uuid REFERENCES loi.nguoi_dung(id), cong_bo_luc timestamptz, ly_do text NOT NULL,
        UNIQUE (phap_nhan_id, so_phien_ban), UNIQUE (id, phap_nhan_id), UNIQUE (id, phien_ban_danh_muc),
        FOREIGN KEY (duoc_tao_tu, phap_nhan_id) REFERENCES loi.mtq_phien_ban(id, phap_nhan_id),
        CHECK ((trang_thai = 'DA_CONG_BO') = (cong_bo_boi IS NOT NULL AND cong_bo_luc IS NOT NULL)));

CREATE TABLE IF NOT EXISTS loi.mtq_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL, phong_id uuid NOT NULL, vai text NOT NULL CHECK (vai IN ('THUC_HIEN_1','THUC_HIEN_2','TRUONG_PHONG','CFO','NGUOI_XEM')),
        gioi_han_vnd numeric(20,0) CHECK (gioi_han_vnd IS NULL OR (gioi_han_vnd >= 0 AND gioi_han_vnd < 'Infinity'::numeric)),
        phien_ban_danh_muc integer NOT NULL DEFAULT 1,
        UNIQUE (phien_ban_id, phong_id, vai), UNIQUE (id, phien_ban_danh_muc),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES loi.mtq_phien_ban(id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, phien_ban_danh_muc) REFERENCES loi.mtq_phien_ban(id, phien_ban_danh_muc),
        FOREIGN KEY (phong_id, phap_nhan_id) REFERENCES loi.mtq_phong(id, phap_nhan_id));

CREATE TABLE IF NOT EXISTS loi.mtq_o (
        dong_id uuid NOT NULL, phien_ban_danh_muc integer NOT NULL DEFAULT 1,
        module text NOT NULL, man text NOT NULL, hanh_dong text NOT NULL, cho_phep boolean NOT NULL DEFAULT false,
        PRIMARY KEY (dong_id, module, man, hanh_dong),
        FOREIGN KEY (dong_id, phien_ban_danh_muc) REFERENCES loi.mtq_dong(id, phien_ban_danh_muc),
        FOREIGN KEY (phien_ban_danh_muc, module, man, hanh_dong)
            REFERENCES loi.mtq_danh_muc_hanh_dong(phien_ban_danh_muc, module, man, hanh_dong));

CREATE TABLE IF NOT EXISTS loi.mtq_gan_vai (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL, phong_id uuid NOT NULL, vai text NOT NULL CHECK (vai IN ('THUC_HIEN_1','THUC_HIEN_2','TRUONG_PHONG','CFO','NGUOI_XEM')),
        cap_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES loi.nguoi_dung(id), ly_do text NOT NULL,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0), UNIQUE (id, phap_nhan_id),
        FOREIGN KEY (phong_id, phap_nhan_id) REFERENCES loi.mtq_phong(id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)));

CREATE TABLE IF NOT EXISTS loi.mtq_pham_vi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), gan_vai_id uuid NOT NULL, phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN ('PHAP_NHAN','DU_AN','LOAI_HINH','HOP_DONG','KHACH','NGUON')),
        khoa text NOT NULL, quan_he jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(quan_he) = 'object'),
        cap_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id), cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        thu_hoi_luc timestamptz, thu_hoi_boi uuid REFERENCES loi.nguoi_dung(id), ly_do text NOT NULL,
        phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0),
        FOREIGN KEY (gan_vai_id, phap_nhan_id) REFERENCES loi.mtq_gan_vai(id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL)));

CREATE TABLE IF NOT EXISTS loi.mtq_kich_hoat (
        phap_nhan_id uuid PRIMARY KEY REFERENCES loi.phap_nhan(id), bat boolean NOT NULL DEFAULT false,
        phien_ban_id uuid, phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK (phien_ban_dong > 0),
        bat_boi uuid REFERENCES loi.nguoi_dung(id), bat_luc timestamptz,
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES loi.mtq_phien_ban(id, phap_nhan_id),
        CHECK (NOT bat OR (phien_ban_id IS NOT NULL AND bat_boi IS NOT NULL AND bat_luc IS NOT NULL)));

CREATE TABLE IF NOT EXISTS loi.mtq_thay_doi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL, phap_nhan_id uuid,
        doi_tuong_bang text NOT NULL, doi_tuong jsonb NOT NULL,
        phien_ban_id uuid, phien_ban_dong bigint, loai_su_kien text NOT NULL,
        truoc jsonb, sau jsonb, nguoi_dung_id uuid NOT NULL REFERENCES loi.nguoi_dung(id), dang_nhap text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(), ly_do text NOT NULL, dang_nhap_csdl text NOT NULL DEFAULT session_user);

CREATE TABLE IF NOT EXISTS loi.mtq_tu_choi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL, nguoi_dung_id uuid, dang_nhap text,
        phap_nhan_id uuid, phap_nhan_yeu_cau_id uuid NOT NULL,
        phong_id uuid, vai text, phien_ban_id uuid, phien_ban_dong bigint,
        gan_vai_id uuid, gan_vai_phien_ban_dong bigint, pham_vi_id uuid, pham_vi_phien_ban_dong bigint,
        module text, man text, hanh_dong text, lenh_ky_thuat text, doi_tuong text,
        ma text NOT NULL, ly_do text NOT NULL, gioi_han_vnd numeric(20,0), so_tien_vnd numeric,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp());
INSERT INTO loi.mtq_danh_muc_hanh_dong VALUES
(1,'CRM','TIEP_NHAN','XEM','CRM:TIEP_NHAN:XEM','TIEP_NHAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TIEP_NHAN','LAP','CRM:TIEP_NHAN:LAP','TIEP_NHAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TIEP_NHAN','SUA','CRM:TIEP_NHAN:SUA','TIEP_NHAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TIEP_NHAN','KIEM','CRM:TIEP_NHAN:KIEM','TIEP_NHAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TIEP_NHAN','DUYET','CRM:TIEP_NHAN:DUYET','TIEP_NHAN','MAY_CHU_MTQ4','TONG_HOP_DONG'),
(1,'CRM','G1_MAU','XEM','CRM:G1_MAU:XEM','G1_MAU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G1_MAU','LAP','CRM:G1_MAU:LAP','G1_MAU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G1_MAU','SUA','CRM:G1_MAU:SUA','G1_MAU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G1_MAU','KIEM','CRM:G1_MAU:KIEM','G1_MAU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G1_MAU','DUYET','CRM:G1_MAU:DUYET','G1_MAU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G7_CHUAN','XEM','CRM:G7_CHUAN:XEM','G7_CHUAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G7_CHUAN','LAP','CRM:G7_CHUAN:LAP','G7_CHUAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G7_CHUAN','SUA','CRM:G7_CHUAN:SUA','G7_CHUAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G7_CHUAN','DUYET','CRM:G7_CHUAN:DUYET','G7_CHUAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G2_BAO_GIA','XEM','CRM:G2_BAO_GIA:XEM','G2_BAO_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G2_BAO_GIA','LAP','CRM:G2_BAO_GIA:LAP','G2_BAO_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G2_BAO_GIA','SUA','CRM:G2_BAO_GIA:SUA','G2_BAO_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G2_BAO_GIA','HUY','CRM:G2_BAO_GIA:HUY','G2_BAO_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G3_G4_SOAN_KY','XEM','CRM:G3_G4_SOAN_KY:XEM','G3_G4_SOAN_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G3_G4_SOAN_KY','LAP','CRM:G3_G4_SOAN_KY:LAP','G3_G4_SOAN_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G3_G4_SOAN_KY','SUA','CRM:G3_G4_SOAN_KY:SUA','G3_G4_SOAN_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G5_G6_KIEM_KY','XEM','CRM:G5_G6_KIEM_KY:XEM','G5_G6_KIEM_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G5_G6_KIEM_KY','SUA','CRM:G5_G6_KIEM_KY:SUA','G5_G6_KIEM_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G5_G6_KIEM_KY','KIEM','CRM:G5_G6_KIEM_KY:KIEM','G5_G6_KIEM_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','G5_G6_KIEM_KY','DUYET','CRM:G5_G6_KIEM_KY:DUYET','G5_G6_KIEM_KY','MAY_CHU_MTQ4','TONG_HOP_DONG'),
(1,'CRM','DU_AN_BAN','XEM','CRM:DU_AN_BAN:XEM','DU_AN_BAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','DU_AN_BAN','LAP','CRM:DU_AN_BAN:LAP','DU_AN_BAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','DU_AN_BAN','SUA','CRM:DU_AN_BAN:SUA','DU_AN_BAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TY_GIA','XEM','CRM:TY_GIA:XEM','TY_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','TY_GIA','SUA','CRM:TY_GIA:SUA','TY_GIA','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','FILE_SOAT','XEM','CRM:FILE_SOAT:XEM','FILE_SOAT','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CRM','BAN_KY','XEM','CRM:BAN_KY:XEM','BAN_KY','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M1','TIEN','XEM','M1:TIEN:XEM','TIEN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M1','TIEN','LAP','M1:TIEN:LAP','TIEN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M1','TIEN','SUA','M1:TIEN:SUA','TIEN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M1','TIEN','HUY','M1:TIEN:HUY','TIEN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M1','XEM_TIEN','XEM','M1:XEM_TIEN:XEM','XEM_TIEN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','HOA_DON','XEM','M2:HOA_DON:XEM','HOA_DON','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','HOA_DON','LAP','M2:HOA_DON:LAP','HOA_DON','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','HOA_DON','DUYET','M2:HOA_DON:DUYET','HOA_DON','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','HOA_DON','HUY','M2:HOA_DON:HUY','HOA_DON','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','NGUON_THO','XEM','M2:NGUON_THO:XEM','NGUON_THO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','KHO','XEM','M5:KHO:XEM','KHO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','KHO','LAP','M5:KHO:LAP','KHO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','KHO','DUYET','M5:KHO:DUYET','KHO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','NGUON_THO','XEM','M5:NGUON_THO:XEM','NGUON_THO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','L11','XEM','M2:L11:XEM','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','L11','LAP','M2:L11:LAP','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','L11','DUYET','M2:L11:DUYET','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','L11','HUY','M2:L11:HUY','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','L11','XEM','M5:L11:XEM','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','L11','LAP','M5:L11:LAP','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','L11','DUYET','M5:L11:DUYET','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M5','L11','HUY','M5:L11:HUY','L11','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','HO_SO','XEM','M4:HO_SO:XEM','HO_SO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','HO_SO','LAP','M4:HO_SO:LAP','HO_SO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','HO_SO','SUA','M4:HO_SO:SUA','HO_SO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','HO_SO','KIEM','M4:HO_SO:KIEM','HO_SO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','HO_SO','HUY','M4:HO_SO:HUY','HO_SO','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02A_REVIEW','XEM','M4:02A_REVIEW:XEM','02A_REVIEW','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02A_REVIEW','SUA','M4:02A_REVIEW:SUA','02A_REVIEW','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02A_REVIEW','KIEM','M4:02A_REVIEW:KIEM','02A_REVIEW','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02B_CHUNG_TU','XEM','M4:02B_CHUNG_TU:XEM','02B_CHUNG_TU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02B_CHUNG_TU','SUA','M4:02B_CHUNG_TU:SUA','02B_CHUNG_TU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02B_CHUNG_TU','KIEM','M4:02B_CHUNG_TU:KIEM','02B_CHUNG_TU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02C_DUYET','XEM','M4:02C_DUYET:XEM','02C_DUYET','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02C_DUYET','LAP','M4:02C_DUYET:LAP','02C_DUYET','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02C_DUYET','SUA','M4:02C_DUYET:SUA','02C_DUYET','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02C_DUYET','KIEM','M4:02C_DUYET:KIEM','02C_DUYET','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','02C_DUYET','DUYET','M4:02C_DUYET:DUYET','02C_DUYET','MAY_CHU_MTQ4','XIN_THANH_TOAN'),
(1,'M4','PDF_DA_DUYET','XEM','M4:PDF_DA_DUYET:XEM','PDF_DA_DUYET','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03A_KE_TOAN','XEM','M4:03A_KE_TOAN:XEM','03A_KE_TOAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03A_KE_TOAN','SUA','M4:03A_KE_TOAN:SUA','03A_KE_TOAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03A_KE_TOAN','KIEM','M4:03A_KE_TOAN:KIEM','03A_KE_TOAN','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03B_DOI_CHIEU','XEM','M4:03B_DOI_CHIEU:XEM','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03B_DOI_CHIEU','SUA','M4:03B_DOI_CHIEU:SUA','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','03B_DOI_CHIEU','KIEM','M4:03B_DOI_CHIEU:KIEM','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','03B_DOI_CHIEU','XEM','M2:03B_DOI_CHIEU:XEM','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','03B_DOI_CHIEU','SUA','M2:03B_DOI_CHIEU:SUA','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M2','03B_DOI_CHIEU','KIEM','M2:03B_DOI_CHIEU:KIEM','03B_DOI_CHIEU','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','04_REQUEST_NHAP','XEM','M4:04_REQUEST_NHAP:XEM','04_REQUEST_NHAP','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','04_REQUEST_NHAP','LAP','M4:04_REQUEST_NHAP:LAP','04_REQUEST_NHAP','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'M4','04_REQUEST_NHAP','KIEM','M4:04_REQUEST_NHAP:KIEM','04_REQUEST_NHAP','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CORE','DANH_TINH','XEM','CORE:DANH_TINH:XEM','DANH_TINH','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CORE','DANH_TINH','LAP','CORE:DANH_TINH:LAP','DANH_TINH','MAY_CHU_MTQ4','PHI_TIEN'),
(1,'CORE','DANH_TINH','SUA','CORE:DANH_TINH:SUA','DANH_TINH','MAY_CHU_MTQ4','PHI_TIEN')
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION loi.mtq_quyet_dinh(p_ai uuid, p_pn uuid, p_phong uuid, p_lenh text, p_loai text,
        p_doi_tuong text, p_khoa text, p_scope_loai text, p_tien_vnd numeric, p_scope uuid, p_request uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $ham$
        DECLARE ai uuid := p_ai; kh loi.mtq_kich_hoat; v loi.mtq_phien_ban;
            g loi.mtq_gan_vai; s loi.mtq_pham_vi; d loi.mtq_dong; c loi.mtq_danh_muc_hanh_dong;
            ma text; ly_do text; kq jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            SELECT * INTO kh FROM loi.mtq_kich_hoat WHERE phap_nhan_id = p_pn;
            IF ai IS NULL THEN ma := 'MTQ_DANH_TINH'; ly_do := 'Danh tính phiên ID/login không khớp người hoạt động';
            ELSIF p_pn IS NULL OR NOT EXISTS (SELECT 1 FROM loi.phap_nhan WHERE id = p_pn) THEN
                ma := 'MTQ_PHAP_NHAN'; ly_do := 'Không xác định được pháp nhân';
            ELSIF NOT coalesce(kh.bat, false) THEN
                RETURN jsonb_build_object('nguon', 'CU', 'can_thiep', false, 'cho_phep', NULL, 'ma', 'MTQ_TAT', 'ly_do', 'Giữ đường kiểm quyền cũ');
            ELSE
                SELECT * INTO v FROM loi.mtq_phien_ban WHERE id = kh.phien_ban_id AND phap_nhan_id = p_pn AND trang_thai = 'DA_CONG_BO';
                SELECT * INTO c FROM loi.mtq_danh_muc_hanh_dong WHERE phien_ban_danh_muc = v.phien_ban_danh_muc AND lenh_ky_thuat = p_lenh AND loai_doi_tuong = p_loai;
                SELECT * INTO g FROM loi.mtq_gan_vai WHERE nguoi_dung_id = ai AND phap_nhan_id = p_pn AND phong_id = p_phong AND thu_hoi_luc IS NULL;
                SELECT * INTO s FROM loi.mtq_pham_vi WHERE id = p_scope AND gan_vai_id = g.id AND phap_nhan_id = p_pn AND thu_hoi_luc IS NULL;
                SELECT * INTO d FROM loi.mtq_dong WHERE phien_ban_id = v.id AND phap_nhan_id = p_pn AND phong_id = p_phong AND vai = g.vai;
                IF v.id IS NULL THEN ma := 'MTQ_CON_TRO_SAI'; ly_do := 'Thiếu snapshot công bố hiệu lực';
                ELSIF c.module IS NULL THEN ma := 'MTQ_HANH_DONG'; ly_do := 'Hành động/đối tượng chưa có trong catalog';
                ELSIF g.id IS NULL OR NOT EXISTS (SELECT 1 FROM loi.mtq_phong WHERE id = p_phong AND phap_nhan_id = p_pn AND hoat_dong) THEN
                    ma := 'MTQ_GAN_VAI'; ly_do := 'Chưa có vai tại đúng phòng/pháp nhân';
                ELSIF nullif(btrim(p_doi_tuong), '') IS NULL OR s.id IS NULL
                    OR s.loai IS DISTINCT FROM p_scope_loai OR s.khoa IS DISTINCT FROM p_khoa THEN
                    ma := 'MTQ_PHAM_VI'; ly_do := 'Đối tượng ngoài phạm vi được cấp';
                ELSIF d.id IS NULL OR NOT EXISTS (SELECT 1 FROM loi.mtq_o WHERE dong_id = d.id AND module = c.module AND man = c.man AND hanh_dong = c.hanh_dong AND cho_phep) THEN
                    ma := 'MTQ_CHUA_TICK'; ly_do := 'Ô quyền chưa được tick';
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND
                    (p_tien_vnd IS NULL OR p_tien_vnd < 0 OR p_tien_vnd >= 'Infinity'::numeric OR p_tien_vnd <> trunc(p_tien_vnd)) THEN
                    ma := 'MTQ_THIEU_TIEN'; ly_do := 'Cần số tiền VND nguyên không âm từ hồ sơ/tỷ giá đã ghim';
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND d.gioi_han_vnd IS NOT NULL AND p_tien_vnd > d.gioi_han_vnd THEN
                    ma := 'MTQ_VUOT_HAN_MUC'; ly_do := 'Số tiền duyệt vượt giới hạn tiền VND của dòng';
                ELSE ma := 'MTQ_CHO_PHEP'; ly_do := 'Đúng ô tick, phòng, pháp nhân, phạm vi và hạn mức'; END IF;
            END IF;
            kq := jsonb_build_object('nguon', 'MA_TRAN', 'can_thiep', true, 'cho_phep', ma = 'MTQ_CHO_PHEP', 'ma', ma, 'ly_do', ly_do,
                'phien_ban_id', v.id, 'phien_ban_dong', v.phien_ban_dong, 'kich_hoat_phien_ban_dong', kh.phien_ban_dong,
                'gan_vai_id', g.id, 'gan_vai_phien_ban_dong', g.phien_ban_dong,
                'pham_vi_id', s.id, 'pham_vi_phien_ban_dong', s.phien_ban_dong,
                'dong_id', d.id, 'module', c.module, 'man', c.man, 'hanh_dong', c.hanh_dong,
                'doi_tuong', p_doi_tuong, 'phap_nhan_id', p_pn,
                'gioi_han_vnd', d.gioi_han_vnd, 'so_tien_vnd', p_tien_vnd);
            RETURN kq;
        END $ham$;

CREATE UNIQUE INDEX IF NOT EXISTS mtq_admin_hien_hanh ON loi.mtq_admin (nguoi_dung_id) WHERE thu_hoi_luc IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS mtq_vai_hien_hanh ON loi.mtq_gan_vai (nguoi_dung_id, phap_nhan_id, phong_id) WHERE thu_hoi_luc IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS mtq_pham_vi_hien_hanh ON loi.mtq_pham_vi (gan_vai_id, loai, khoa) WHERE thu_hoi_luc IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS mtq_tu_choi_yeu_cau ON loi.mtq_tu_choi (request_id);

    -- ABI resolver_mtq v1: (ma, pn, hanh_dong, tham_chieu, viec, the_he)
    -- -> tap JSON M0057: [{pn, hop_le, loai, phong?, hd?, da?, lh?, khach?,
    -- nguon_khoa?, so_tien_vnd?, ly_do?}]. Tien/quan he chi lay tu resolver, khong tu client.
    -- Khong tu dang ky/kich hoat contract nghiep vu; thieu binding tra CHO.
    CREATE OR REPLACE FUNCTION loi.mtq_giai_doi_tuong_tap(
        p_ma text, p_module text, p_pn uuid, p_hanh_dong text, p_doi_tuong jsonb,
        p_phien_ban_contract text, p_viec_id uuid, p_the_he bigint
    ) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE binding jsonb; h loi.dang_ky_ham_module; tap jsonb; pn uuid;
    BEGIN
        IF NOT EXISTS (SELECT FROM loi.xac_minh_phien(
            p_ma, p_module, p_pn, p_hanh_dong, p_viec_id, p_the_he)) THEN
            RAISE EXCEPTION 'Phiên không hợp lệ' USING ERRCODE = '42501';
        END IF;
        -- Resolver danh tinh thuoc Core, khong cham bang rieng module.
        IF p_module = 'core' AND p_hanh_dong IN
            ('CORE:DANH_TINH:XEM','CORE:DANH_TINH:LAP','CORE:DANH_TINH:SUA')
           AND p_doi_tuong->>'bang' = 'loi.phap_nhan' THEN
            SELECT id INTO pn FROM loi.phap_nhan WHERE id = (p_doi_tuong->>'id')::uuid;
            IF pn IS DISTINCT FROM p_pn THEN RETURN NULL; END IF;
            RETURN jsonb_build_array(jsonb_build_object('pn', pn, 'hop_le', true, 'loai', 'DANH_TINH'));
        END IF;
        binding := loi.phan_giai_ham_module(p_module, 'resolver_mtq', p_phien_ban_contract,
            p_ma, p_pn, p_hanh_dong, p_viec_id, p_the_he);
        IF binding->>'ket_luan' = 'CHO' THEN RETURN NULL; END IF;
        h := jsonb_populate_record(NULL::loi.dang_ky_ham_module, binding->'binding');
        IF NOT EXISTS (SELECT FROM pg_proc WHERE oid = to_regprocedure(h.chu_ky)
            AND proargtypes = '25 2950 25 3802 2950 20'::oidvector
            AND prorettype = 'jsonb'::regtype AND NOT proretset) THEN
            RAISE EXCEPTION 'Chữ ký resolver không hợp lệ' USING ERRCODE = '42501';
        END IF;
        EXECUTE format('SELECT %I.%I($1,$2,$3,$4,$5,$6)', h.ten_schema, h.ten_ham)
            INTO tap USING p_ma, p_pn, p_hanh_dong, p_doi_tuong, p_viec_id, p_the_he;
        RETURN tap;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.mtq_quyet_dinh_phien(
        p_ma text, p_module text, p_pn uuid, p_hanh_dong text, p_doi_tuong jsonb,
        p_phien_ban_contract text DEFAULT '1', p_cac_ma text[] DEFAULT '{}',
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        ai uuid; nguoi uuid; pn uuid; phong uuid; scope_id uuid;
        khoa text; scope_loai text; obj uuid; tap jsonb; giai jsonb;
        dau jsonb; kq jsonb; n bigint; so_pn bigint; so_bat bigint;
        ma text; ly_do text; tien numeric;
    BEGIN
        -- Lay khoa truoc xac minh; VOLATILE doc snapshot moi sau khi cho cau hinh.
        -- xac_minh_phien van STABLE/tra bam co chi muc theo chuan G2-03.
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(
            p_ma, p_module, p_pn, p_hanh_dong, p_viec_id, p_the_he);
        IF ai IS NULL THEN
            RAISE EXCEPTION 'Phiên không hợp lệ' USING ERRCODE = '42501';
        END IF;
        IF split_part(p_hanh_dong,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'Hành động không thuộc module của phiên' USING ERRCODE = '42501';
        END IF;
        IF jsonb_typeof(p_doi_tuong) IS DISTINCT FROM 'object'
           OR (p_doi_tuong - ARRAY['bang','id','phong_id']) <> '{}'::jsonb
           OR coalesce(p_doi_tuong->>'bang','') = '' THEN
            ma := 'MTQ_DOI_TUONG'; ly_do := 'Cần tham chiếu đối tượng máy chủ';
        ELSE
            BEGIN
                obj := (p_doi_tuong->>'id')::uuid;
                phong := (p_doi_tuong->>'phong_id')::uuid;
            EXCEPTION WHEN invalid_text_representation THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Tham chiếu đối tượng hoặc phòng không hợp lệ';
            END;
            IF obj IS NULL THEN ma := 'MTQ_DOI_TUONG'; ly_do := 'Thiếu mã đối tượng'; END IF;
        END IF;
        IF ma IS NULL THEN
            tap := loi.mtq_giai_doi_tuong_tap(p_ma, p_module, p_pn, p_hanh_dong,
                p_doi_tuong, p_phien_ban_contract, p_viec_id, p_the_he);
            IF tap IS NULL OR jsonb_typeof(tap) IS DISTINCT FROM 'array' THEN
                RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                    'ma','MTQ_CAN_RESOLVER_MTQ4','ly_do','Chưa có resolver hoặc căn cứ hợp lệ');
            END IF;
            SELECT count(*), count(DISTINCT value->>'pn'),
                count(*) FILTER (WHERE EXISTS (SELECT FROM loi.mtq_kich_hoat k
                    WHERE k.phap_nhan_id = (value->>'pn')::uuid AND k.bat))
                INTO so_pn, n, so_bat FROM jsonb_array_elements(tap);
            IF so_pn = 0 OR so_pn <> n OR NOT EXISTS
                (SELECT FROM jsonb_array_elements(tap) WHERE value->>'pn' = p_pn::text) THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Tập pháp nhân không hợp lệ';
            ELSE
                -- Moi PN can ma rieng, cung nguoi/module/hanh dong/uy nhiem viec.
                FOR giai IN SELECT value FROM jsonb_array_elements(tap) ORDER BY value->>'pn' LOOP
                    pn := (giai->>'pn')::uuid;
                    IF giai->'hop_le' = 'false'::jsonb THEN
                        ma := 'MTQ_DOI_TUONG';
                        ly_do := coalesce(giai->>'ly_do', 'Đối tượng không hợp lệ'); EXIT;
                    END IF;
                    IF giai->'hop_le' IS DISTINCT FROM 'true'::jsonb OR pn IS NULL THEN
                        RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                            'ma','MTQ_CAN_RESOLVER_MTQ4','ly_do','Chưa đủ căn cứ đối tượng');
                    END IF;
                    SELECT x.nguoi_dung_id INTO nguoi
                        FROM unnest(ARRAY[p_ma] || coalesce(p_cac_ma, '{}'::text[])) m
                        CROSS JOIN LATERAL loi.xac_minh_phien(m, p_module, pn, p_hanh_dong,
                            p_viec_id, p_the_he) x
                        WHERE x.nguoi_dung_id = ai LIMIT 1;
                    IF nguoi IS NULL THEN
                        ma := 'MTQ_PHAP_NHAN'; ly_do := 'Thiếu phiên hợp lệ ở một pháp nhân'; EXIT;
                    END IF;
                END LOOP;
                IF ma IS NULL THEN
                    -- QD-20261026-10: moi PN kiem cung tong tien, khong chia nho han muc.
                    tien := (tap->0->>'so_tien_vnd')::numeric;
                    IF EXISTS (SELECT FROM jsonb_array_elements(tap)
                        WHERE (value->>'so_tien_vnd')::numeric IS DISTINCT FROM tien) THEN
                        ma := 'MTQ_DOI_TUONG'; ly_do := 'Các pháp nhân phải dùng cùng số tiền';
                    END IF;
                END IF;
                IF ma IS NULL AND so_bat > 0 AND so_bat <> so_pn THEN
                    ma := 'MTQ_PN_HON_HOP'; ly_do := 'Đối tượng có pháp nhân chưa bật ma trận';
                ELSIF ma IS NULL AND so_bat = 0 THEN
                    -- Khong mo fallback CU cho module moi khong co khai bao chuyen tiep.
                    RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                        'ma','MTQ_TAT','ly_do','Ma trận chưa được bật cho đối tượng');
                ELSIF ma IS NULL AND so_pn > 1 AND p_doi_tuong->>'phong_id' IS NOT NULL THEN
                    ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Không hợp nhất phòng giữa các pháp nhân';
                END IF;
            END IF;
            IF ma IS NULL THEN
                FOR giai IN SELECT value FROM jsonb_array_elements(tap) ORDER BY value->>'pn' LOOP
                    pn := (giai->>'pn')::uuid;
                    phong := coalesce((giai->>'phong')::uuid, (p_doi_tuong->>'phong_id')::uuid);
                    scope_id := NULL; khoa := NULL; scope_loai := NULL;
                    SELECT count(*), (array_agg(g.phong_id))[1] INTO n, phong
                        FROM loi.mtq_gan_vai g JOIN loi.mtq_phong p
                            ON p.id = g.phong_id AND p.phap_nhan_id = g.phap_nhan_id AND p.hoat_dong
                        WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.thu_hoi_luc IS NULL
                            AND (phong IS NULL OR g.phong_id = phong);
                    IF n > 1 THEN
                        ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Cần đúng một phòng, không hợp nhất quyền'; EXIT;
                    END IF;
                    SELECT s.id, s.khoa, s.loai INTO scope_id, khoa, scope_loai
                        FROM loi.mtq_pham_vi s JOIN loi.mtq_gan_vai g ON g.id = s.gan_vai_id
                        WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.phong_id = phong
                            AND g.thu_hoi_luc IS NULL AND s.phap_nhan_id = pn AND s.thu_hoi_luc IS NULL
                            AND ((s.loai = 'PHAP_NHAN' AND s.khoa = pn::text)
                                OR (s.loai = 'HOP_DONG' AND s.khoa = giai->>'hd')
                                OR (s.loai = 'DU_AN' AND s.khoa = giai->>'da')
                                OR (s.loai = 'LOAI_HINH' AND s.khoa = giai->>'lh')
                                OR (s.loai = 'KHACH' AND s.khoa = giai->>'khach')
                                OR (s.loai = 'NGUON' AND s.khoa = giai->>'nguon_khoa'))
                        ORDER BY CASE s.loai WHEN 'HOP_DONG' THEN 1 WHEN 'DU_AN' THEN 2
                            WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 WHEN 'NGUON' THEN 5 ELSE 6 END,
                            s.id LIMIT 1;
                    kq := loi.mtq_quyet_dinh(ai, pn, phong, p_hanh_dong, giai->>'loai',
                        obj::text, khoa, scope_loai, tien, scope_id, NULL);
                    kq := kq || jsonb_build_object('ket_luan', CASE WHEN kq->'cho_phep' = 'true'::jsonb
                        THEN 'DAT' ELSE 'TU_CHOI' END);
                    IF kq->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN RETURN kq; END IF;
                    IF dau IS NULL THEN dau := kq; END IF;
                END LOOP;
                RETURN dau;
            END IF;
        END IF;
        RETURN jsonb_build_object('nguon','MA_TRAN','can_thiep',true,'ket_luan','TU_CHOI',
            'cho_phep',false,'ma',ma,'ly_do',ly_do,'doi_tuong',obj);
    END;
    $ham$;

    -- Doc khong ghi audit tung dong; chi XEM, khong nhan so tien client.
    CREATE OR REPLACE FUNCTION loi.mtq_duoc_doc(
        p_ma text, p_module text, p_pn uuid, p_hanh_dong text, p_doi_tuong jsonb,
        p_phien_ban_contract text DEFAULT '1', p_cac_ma text[] DEFAULT '{}',
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS boolean LANGUAGE sql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
        SELECT CASE WHEN split_part(p_hanh_dong, ':', 3) = 'XEM' THEN coalesce(
            (loi.mtq_quyet_dinh_phien(p_ma,p_module,p_pn,p_hanh_dong,p_doi_tuong,
                p_phien_ban_contract,p_cac_ma,p_viec_id,p_the_he)->>'cho_phep')::boolean, false)
            ELSE false END
    $ham$;

    -- Sau rollback nghiep vu, caller mo transaction moi, goi cua nay va commit.
    -- Tinh lai ket luan hien hanh; khong nhan JSON quyet dinh tu client.
    CREATE OR REPLACE FUNCTION loi.mtq_ghi_tu_choi_phien(
        p_request uuid, p_ma text, p_module text, p_pn uuid, p_hanh_dong text,
        p_doi_tuong jsonb, p_phien_ban_contract text DEFAULT '1',
        p_cac_ma text[] DEFAULT '{}', p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ai uuid; kq jsonb; cu loi.mtq_tu_choi; ket_qua uuid; pn_tu_choi uuid; ma_audit text;
    BEGIN
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(
            p_ma,p_module,p_pn,p_hanh_dong,p_viec_id,p_the_he);
        IF ai IS NULL OR p_request IS NULL THEN
            RAISE EXCEPTION 'Không thể ghi từ chối' USING ERRCODE = '42501';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        PERFORM pg_advisory_xact_lock(hashtextextended(p_request::text, 6));
        SELECT * INTO cu FROM loi.mtq_tu_choi WHERE request_id = p_request;
        IF FOUND THEN
            IF cu.nguoi_dung_id IS DISTINCT FROM ai OR cu.dang_nhap IS DISTINCT FROM session_user::text
                OR cu.phap_nhan_yeu_cau_id IS DISTINCT FROM p_pn OR cu.module IS DISTINCT FROM p_module
                OR cu.lenh_ky_thuat IS DISTINCT FROM p_hanh_dong
                OR cu.doi_tuong IS DISTINCT FROM p_doi_tuong->>'id' THEN
                RAISE EXCEPTION 'Mã yêu cầu đã dùng cho thao tác khác' USING ERRCODE = '23505';
            END IF;
            RETURN cu.id;
        END IF;
        kq := loi.mtq_quyet_dinh_phien(p_ma,p_module,p_pn,p_hanh_dong,p_doi_tuong,
            p_phien_ban_contract,p_cac_ma,p_viec_id,p_the_he);
        IF kq->>'ket_luan' IS DISTINCT FROM 'TU_CHOI' OR kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb THEN
            RAISE EXCEPTION 'Chỉ ghi quyết định từ chối hiện hành' USING ERRCODE = '22023';
        END IF;
        pn_tu_choi := coalesce((kq->>'phap_nhan_id')::uuid,p_pn);
        SELECT m INTO ma_audit FROM unnest(ARRAY[p_ma] || coalesce(p_cac_ma,'{}'::text[])) m
            CROSS JOIN LATERAL loi.xac_minh_phien(m,p_module,pn_tu_choi,p_hanh_dong,p_viec_id,p_the_he) x
            WHERE x.nguoi_dung_id=ai LIMIT 1;
        IF ma_audit IS NULL THEN
            RAISE EXCEPTION 'Không thể xác minh pháp nhân ghi từ chối' USING ERRCODE='42501';
        END IF;
        INSERT INTO loi.mtq_tu_choi(request_id,nguoi_dung_id,dang_nhap,phap_nhan_id,phap_nhan_yeu_cau_id,
            module,lenh_ky_thuat,doi_tuong,ma,ly_do,phien_ban_id,phien_ban_dong,
            gan_vai_id,gan_vai_phien_ban_dong,pham_vi_id,pham_vi_phien_ban_dong,gioi_han_vnd,so_tien_vnd)
        VALUES (p_request,ai,session_user,pn_tu_choi,p_pn,p_module,p_hanh_dong,p_doi_tuong->>'id',
            kq->>'ma',kq->>'ly_do',(kq->>'phien_ban_id')::uuid,(kq->>'phien_ban_dong')::bigint,
            (kq->>'gan_vai_id')::uuid,(kq->>'gan_vai_phien_ban_dong')::bigint,
            (kq->>'pham_vi_id')::uuid,(kq->>'pham_vi_phien_ban_dong')::bigint,
            (kq->>'gioi_han_vnd')::numeric,(kq->>'so_tien_vnd')::numeric)
        RETURNING id INTO ket_qua;
        PERFORM loi.ghi_kiem_toan(p_hanh_dong,'mtq_tu_choi',ket_qua,'TU_CHOI',
            ma_audit,p_module,pn_tu_choi,p_request,p_viec_id,p_the_he);
        RETURN ket_qua;
    END;
    $ham$;

    -- GUC chi mang dau vao khong tin cay. Moi lan policy goi deu xac minh lai.
    -- Khong cache actor/quyen trong GUC hay bang tam. Loi ngu canh => khong dong.
    CREATE OR REPLACE FUNCTION loi.mtq_phien_rls()
    RETURNS TABLE(nguoi_dung_id uuid, phap_nhan_id uuid)
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        RETURN QUERY SELECT x.nguoi_dung_id, x.phap_nhan_id FROM loi.xac_minh_phien(
            current_setting('ktt.ma_phien',true), current_setting('ktt.module',true),
            nullif(current_setting('ktt.phap_nhan_id',true),'')::uuid,
            current_setting('ktt.hanh_dong',true),
            nullif(current_setting('ktt.viec_id',true),'')::uuid,
            nullif(current_setting('ktt.the_he',true),'')::bigint) x;
    EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
        RETURN;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.mtq_khong_chuyen_phap_nhan()
    RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $ham$
    BEGIN
        IF (to_jsonb(NEW)->'phap_nhan_id') IS DISTINCT FROM (to_jsonb(OLD)->'phap_nhan_id')
           OR (TG_TABLE_NAME = 'phap_nhan' AND NEW.id <> OLD.id) THEN
            RAISE EXCEPTION 'Không được chuyển hồ sơ sang pháp nhân khác' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END;
    $ham$;

    FOREACH ten_bang IN ARRAY ARRAY['nguoi_dung','phap_nhan','phan_quyen','phap_nhan_boi_canh'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY',ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY',ten_bang);
        -- Thu hoi ca GRANT theo cot cua 002, khong chi GRANT muc bang.
        EXECUTE format('REVOKE INSERT, UPDATE, DELETE ON loi.%I FROM %I, %I',ten_bang,vai_chay,login_loi);
        FOR ham IN SELECT attname FROM pg_attribute WHERE attrelid = format('loi.%I',ten_bang)::regclass
            AND attnum > 0 AND NOT attisdropped LOOP
            EXECUTE format('REVOKE INSERT (%I), UPDATE (%I) ON loi.%I FROM %I, %I',
                ham.attname,ham.attname,ten_bang,vai_chay,login_loi);
        END LOOP;
        IF ten_bang = 'nguoi_dung' THEN
            EXECUTE format('ALTER POLICY danh_tinh_cho_phien ON loi.nguoi_dung TO %I
                USING (id IN (SELECT nguoi_dung_id FROM loi.mtq_phien_rls())) WITH CHECK (false)',vai_chay);
        ELSIF ten_bang = 'phap_nhan' THEN
            EXECUTE format('ALTER POLICY danh_tinh_cho_phien ON loi.phap_nhan TO %I
                USING (id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls())) WITH CHECK (false)',vai_chay);
        ELSE
            EXECUTE format('ALTER POLICY danh_tinh_cho_phien ON loi.%I TO %I
                USING (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))
                WITH CHECK (false)',ten_bang,vai_chay);
        END IF;
        -- Danh tinh/xac thuc toan cuc: owner ham Core duoc ghi sau kiem MTQ.
        -- Runtime khong nhan policy/ACL nay; owner SELECT cua 003 giu nguyen.
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid = format('loi.%I',ten_bang)::regclass
                       AND polname = 'mtq_chu_them_danh_tinh') THEN
            EXECUTE format('CREATE POLICY mtq_chu_them_danh_tinh ON loi.%I FOR INSERT
                TO %I WITH CHECK (true)',ten_bang,vai_chu);
        END IF;
        IF ten_bang <> 'nguoi_dung' AND NOT EXISTS (SELECT FROM pg_trigger
            WHERE tgrelid = format('loi.%I',ten_bang)::regclass AND tgname = 'mtq_khong_chuyen_phap_nhan') THEN
            EXECUTE format('CREATE TRIGGER mtq_khong_chuyen_phap_nhan BEFORE UPDATE ON loi.%I
                FOR EACH ROW EXECUTE FUNCTION loi.mtq_khong_chuyen_phap_nhan()',ten_bang);
        END IF;
    END LOOP;

    -- Cua ghi thay GRANT INSERT cua G2-02. PN hien hanh la workspace quan tri.
    -- Tao workspace moi tao luon thanh vien cua nguoi da xac minh, khong nhan actor.
    CREATE OR REPLACE FUNCTION loi.mtq_tao_danh_tinh(
        p_ma text, p_pn uuid, p_loai text, p_du_lieu jsonb,
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE kq jsonb; ai uuid; ket_qua uuid; cac_module text[]; cac_loai text[];
    BEGIN
        kq := loi.mtq_quyet_dinh_phien(p_ma,'core',p_pn,'CORE:DANH_TINH:LAP',
            jsonb_build_object('bang','loi.phap_nhan','id',p_pn),'1','{}',p_viec_id,p_the_he);
        IF kq->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'Không có quyền tạo danh tính' USING ERRCODE = '42501';
        END IF;
        IF jsonb_typeof(p_du_lieu) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'Dữ liệu danh tính không hợp lệ' USING ERRCODE = '22023';
        END IF;
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(
            p_ma,'core',p_pn,'CORE:DANH_TINH:LAP',p_viec_id,p_the_he);
        ket_qua := gen_random_uuid();
        -- Audit cung transaction, truoc trigger thu hoi phien khi doi quyen.
        PERFORM loi.ghi_kiem_toan('CORE:DANH_TINH:LAP','danh_tinh',NULL,'DAT',
            p_ma,'core',p_pn,NULL,p_viec_id,p_the_he);
        CASE p_loai
        WHEN 'nguoi_dung' THEN
            IF p_du_lieu - ARRAY['dang_nhap','ten','vai_tro','mo_phong'] <> '{}'::jsonb
               OR coalesce(btrim(p_du_lieu->>'dang_nhap'),'') = ''
               OR coalesce(btrim(p_du_lieu->>'ten'),'') = '' THEN
                RAISE EXCEPTION 'Dữ liệu người dùng không hợp lệ' USING ERRCODE = '22023';
            END IF;
            INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro,mo_phong) VALUES
                (ket_qua,p_du_lieu->>'dang_nhap',p_du_lieu->>'ten',coalesce(p_du_lieu->>'vai_tro','XEM'),
                 coalesce((p_du_lieu->>'mo_phong')::boolean,false));
        WHEN 'phap_nhan' THEN
            IF p_du_lieu - ARRAY['ma','ten','mst'] <> '{}'::jsonb
               OR coalesce(btrim(p_du_lieu->>'ma'),'') = '' OR coalesce(btrim(p_du_lieu->>'ten'),'') = '' THEN
                RAISE EXCEPTION 'Dữ liệu pháp nhân không hợp lệ' USING ERRCODE = '22023';
            END IF;
            INSERT INTO loi.phap_nhan(id,ma,ten,mst)
                VALUES (ket_qua,p_du_lieu->>'ma',p_du_lieu->>'ten',p_du_lieu->>'mst');
            INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (ai,ket_qua,ARRAY['core']);
        WHEN 'thanh_vien' THEN
            IF p_du_lieu - ARRAY['nguoi_dung_id','module','duyet_loai_viec'] <> '{}'::jsonb
               OR jsonb_typeof(coalesce(p_du_lieu->'module','[]')) IS DISTINCT FROM 'array'
               OR jsonb_typeof(coalesce(p_du_lieu->'duyet_loai_viec','[]')) IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION 'Dữ liệu thành viên không hợp lệ' USING ERRCODE = '22023';
            END IF;
            IF EXISTS (SELECT FROM jsonb_array_elements(coalesce(p_du_lieu->'module','[]') ||
                coalesce(p_du_lieu->'duyet_loai_viec','[]')) e WHERE jsonb_typeof(e.value) <> 'string') THEN
                RAISE EXCEPTION 'Danh sách quyền phải gồm chuỗi' USING ERRCODE = '22023';
            END IF;
            SELECT coalesce(array_agg(value),'{}') INTO cac_module
                FROM jsonb_array_elements_text(coalesce(p_du_lieu->'module','[]'));
            SELECT coalesce(array_agg(value),'{}') INTO cac_loai
                FROM jsonb_array_elements_text(coalesce(p_du_lieu->'duyet_loai_viec','[]'));
            IF EXISTS (SELECT FROM unnest(cac_module || cac_loai) v WHERE v IS NULL OR btrim(v) = '') THEN
                RAISE EXCEPTION 'Danh sách quyền không hợp lệ' USING ERRCODE = '22023';
            END IF;
            INSERT INTO loi.phan_quyen(id,nguoi_dung_id,phap_nhan_id,module,duyet_loai_viec)
                VALUES (ket_qua,(p_du_lieu->>'nguoi_dung_id')::uuid,p_pn,cac_module,cac_loai);
        ELSE RAISE EXCEPTION 'Loại danh tính không hợp lệ' USING ERRCODE = '22023';
        END CASE;
        RETURN ket_qua;
    END;
    $ham$;

    -- Giu guard snapshot/thu hoi/cung PN cua MTQ-1, khong ke thua GUC admin.
    -- Cau hinh chua co ACL runtime; provisioning duy nhat duoi owner.
    -- Validator quan he NGUON/HOP_DONG/DU_AN duoc hop nhat o G2-07.
    CREATE OR REPLACE FUNCTION loi.mtq_kiem_bat_bien()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE moi jsonb; cu jsonb; pb uuid;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Cấu hình thẩm quyền phải giữ lịch sử' USING ERRCODE = '55000';
        END IF;
        moi := to_jsonb(NEW);
        IF TG_OP = 'UPDATE' THEN
            cu := to_jsonb(OLD);
            IF (moi - ARRAY['phien_ban_dong','ten','hoat_dong','gioi_han_vnd','cho_phep','trang_thai',
                'cong_bo_boi','cong_bo_luc','thu_hoi_luc','thu_hoi_boi','bat','phien_ban_id','bat_boi','bat_luc','ly_do'])
                IS DISTINCT FROM (cu - ARRAY['phien_ban_dong','ten','hoat_dong','gioi_han_vnd','cho_phep','trang_thai',
                'cong_bo_boi','cong_bo_luc','thu_hoi_luc','thu_hoi_boi','bat','phien_ban_id','bat_boi','bat_luc','ly_do'])
                OR (TG_TABLE_NAME <> 'mtq_kich_hoat' AND moi->'phien_ban_id' IS DISTINCT FROM cu->'phien_ban_id') THEN
                RAISE EXCEPTION 'Không đổi khóa hoặc phạm vi đã cấp' USING ERRCODE = '55000';
            END IF;
            IF moi ? 'phien_ban_dong' AND (moi->>'phien_ban_dong')::bigint <> (cu->>'phien_ban_dong')::bigint + 1 THEN
                RAISE EXCEPTION 'Phiên bản dòng phải tăng một' USING ERRCODE = '40001';
            END IF;
            IF TG_TABLE_NAME IN ('mtq_admin','mtq_gan_vai','mtq_pham_vi')
               AND (cu->>'thu_hoi_luc' IS NOT NULL OR moi->>'thu_hoi_luc' IS NULL) THEN
                RAISE EXCEPTION 'Chỉ thu hồi một lần, cấp lại bằng bản ghi mới' USING ERRCODE = '55000';
            END IF;
        END IF;
        IF TG_TABLE_NAME = 'mtq_phien_ban' THEN
            IF TG_OP = 'UPDATE' AND cu->>'trang_thai' = 'DA_CONG_BO' THEN
                RAISE EXCEPTION 'Bản công bố bất biến' USING ERRCODE = '55000';
            END IF;
            IF NEW.trang_thai = 'DA_CONG_BO' AND (TG_OP <> 'UPDATE'
                OR NOT EXISTS (SELECT FROM loi.mtq_phong p WHERE p.phap_nhan_id=NEW.phap_nhan_id AND p.hoat_dong)
                OR EXISTS (SELECT FROM loi.mtq_phong p WHERE p.phap_nhan_id=NEW.phap_nhan_id AND p.hoat_dong
                    AND (SELECT count(*) FROM loi.mtq_dong d WHERE d.phien_ban_id=NEW.id AND d.phong_id=p.id) <> 5)) THEN
                RAISE EXCEPTION 'Mỗi phòng hoạt động cần đủ năm vai trước công bố' USING ERRCODE = '23514';
            END IF;
        ELSIF TG_TABLE_NAME IN ('mtq_dong','mtq_o') THEN
            pb := (moi->>'phien_ban_id')::uuid;
            IF TG_TABLE_NAME = 'mtq_o' THEN
                SELECT phien_ban_id INTO pb FROM loi.mtq_dong WHERE id=NEW.dong_id;
            END IF;
            IF EXISTS (SELECT FROM loi.mtq_phien_ban WHERE id=pb AND trang_thai='DA_CONG_BO') THEN
                RAISE EXCEPTION 'Không sửa ô hoặc dòng của bản công bố' USING ERRCODE = '55000';
            END IF;
        ELSIF TG_TABLE_NAME = 'mtq_kich_hoat' THEN
            IF NEW.bat AND NOT EXISTS (SELECT FROM loi.mtq_phien_ban WHERE id=NEW.phien_ban_id
                AND phap_nhan_id=NEW.phap_nhan_id AND trang_thai='DA_CONG_BO') THEN
                RAISE EXCEPTION 'Chưa có bản công bố cùng pháp nhân' USING ERRCODE = '23514';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $ham$;

    -- Cau hinh phai dung cung khoa voi quyet dinh; thay quyen thu hoi ma cu.
    CREATE OR REPLACE FUNCTION loi.mtq_thu_hoi_khi_doi()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE nguoi uuid;
    BEGIN
        PERFORM pg_advisory_xact_lock(742601, 1);
        FOR nguoi IN SELECT DISTINCT nguoi_dung_id FROM loi.phien_xac_thuc ORDER BY nguoi_dung_id LOOP
            PERFORM loi.thu_hoi_phien_nguoi_dung(nguoi);
        END LOOP;
        RETURN NULL;
    END;
    $ham$;
    FOREACH ten_bang IN ARRAY ARRAY['mtq_phong','mtq_admin','mtq_danh_muc_hanh_dong','mtq_phien_ban',
        'mtq_dong','mtq_o','mtq_gan_vai','mtq_pham_vi','mtq_kich_hoat','mtq_thay_doi','mtq_tu_choi'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY',ten_bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY',ten_bang);
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC, %I, %I',ten_bang,vai_chay,login_loi);
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid = format('loi.%I',ten_bang)::regclass
                       AND polname = 'mtq_chu') THEN
            EXECUTE format('CREATE POLICY mtq_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',ten_bang,vai_chu);
        END IF;
        IF ten_bang IN ('mtq_thay_doi','mtq_tu_choi','mtq_danh_muc_hanh_dong') THEN
            IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid = format('loi.%I',ten_bang)::regclass
                           AND tgname = 'mtq_bat_bien') THEN
                EXECUTE format('CREATE TRIGGER mtq_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE ON loi.%I
                    FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',ten_bang);
            END IF;
        ELSIF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid = format('loi.%I',ten_bang)::regclass
                         AND tgname = 'mtq_doi_quyen') THEN
            EXECUTE format('CREATE TRIGGER mtq_doi_quyen BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE
                ON loi.%I FOR EACH STATEMENT EXECUTE FUNCTION loi.mtq_thu_hoi_khi_doi()',ten_bang);
        END IF;
        IF ten_bang NOT IN ('mtq_thay_doi','mtq_tu_choi','mtq_danh_muc_hanh_dong')
           AND NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=format('loi.%I',ten_bang)::regclass
                           AND tgname='mtq_kiem_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER mtq_kiem_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON loi.%I
                FOR EACH ROW EXECUTE FUNCTION loi.mtq_kiem_bat_bien()',ten_bang);
            EXECUTE format('CREATE TRIGGER mtq_chan_truncate BEFORE TRUNCATE ON loi.%I
                FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',ten_bang);
        END IF;
    END LOOP;
    -- Core owner la noi duy nhat goi loi quyet dinh/resolver noi bo.
    FOR ham IN SELECT oid::regprocedure AS chu_ky, proname FROM pg_proc
        WHERE pronamespace = 'loi'::regnamespace AND proname IN ('mtq_quyet_dinh',
            'mtq_giai_doi_tuong_tap','mtq_quyet_dinh_phien','mtq_duoc_doc','mtq_ghi_tu_choi_phien',
            'mtq_phien_rls','mtq_khong_chuyen_phap_nhan','mtq_tao_danh_tinh','mtq_thu_hoi_khi_doi',
            'mtq_kiem_bat_bien') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I',ham.chu_ky,vai_chay,login_loi);
        IF ham.proname IN ('mtq_quyet_dinh_phien','mtq_duoc_doc','mtq_phien_rls') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.chu_ky,vai_chay);
        ELSIF ham.proname IN ('mtq_ghi_tu_choi_phien','mtq_tao_danh_tinh') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.chu_ky,login_loi);
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_tim_truoc,true);
    PERFORM set_config('role',vai_truoc,true);
END;
$$;

