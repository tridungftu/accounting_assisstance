"""M3-1a — CD-013: cơ sở hợp đồng, mapping M2 và policy doanh thu.

Chỉ hằng SQL. Không seed lựa chọn nghiệp vụ; thiếu căn cứ giữ NULL/PENDING.
M2 hiện chỉ promote mua vào: nguồn bán chưa promote chỉ là mapping PENDING.
Mỗi revision là một dòng bất biến; xác nhận cũng phải tạo revision mới.
"""

M3_CO_SO_SQL = (
    "CREATE SCHEMA m3",
    "REVOKE ALL ON SCHEMA m3 FROM PUBLIC",
    """CREATE TABLE m3.hop_dong_co_so (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        hop_dong_id uuid NOT NULL,
        hop_dong_phien_ban_id uuid NOT NULL,
        pham_vi text NOT NULL CHECK (length(btrim(pham_vi)) BETWEEN 1 AND 300),
        revision integer NOT NULL CHECK (revision >= 1),
        gia_tri_truoc_vat numeric CHECK (gia_tri_truoc_vat >= 0 AND gia_tri_truoc_vat::text NOT IN ('NaN','Infinity','-Infinity')),
        tong_gia_dat_duoc_tru numeric CHECK (tong_gia_dat_duoc_tru >= 0 AND tong_gia_dat_duoc_tru::text NOT IN ('NaN','Infinity','-Infinity')),
        phan_chiu_thue numeric CHECK (phan_chiu_thue >= 0 AND phan_chiu_thue::text NOT IN ('NaN','Infinity','-Infinity')),
        vat numeric CHECK (vat >= 0 AND vat::text NOT IN ('NaN','Infinity','-Infinity')),
        tong_thanh_toan numeric CHECK (tong_thanh_toan >= 0 AND tong_thanh_toan::text NOT IN ('NaN','Infinity','-Infinity')),
        currency text CHECK (currency ~ '^[A-Z]{3}$'),
        trang_thai text NOT NULL DEFAULT 'PENDING' CHECK (trang_thai IN ('PENDING','DA_XAC_NHAN')),
        ly_do_pending text,
        xac_nhan_boi text CHECK (length(btrim(xac_nhan_boi)) > 0),
        xac_nhan_luc timestamptz,
        ngay_nghiep_vu date,
        hieu_luc_tu date,
        nguon text NOT NULL CHECK (length(btrim(nguon)) > 0),
        nguon_sha256 text CHECK (nguon_sha256 ~ '^[0-9a-f]{64}$'),
        nguon_vi_tri text,
        tao_boi text NOT NULL CHECK (length(btrim(tao_boi)) > 0),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (hop_dong_phien_ban_id, hop_dong_id) REFERENCES master.hop_dong_phien_ban (id, hop_dong_id),
        UNIQUE (hop_dong_id, hop_dong_phien_ban_id, pham_vi, revision),
        UNIQUE (id, phap_nhan_id),
        CHECK (gia_tri_truoc_vat IS NULL OR tong_gia_dat_duoc_tru IS NULL OR
            (tong_gia_dat_duoc_tru <= gia_tri_truoc_vat AND
             phan_chiu_thue IS NOT DISTINCT FROM gia_tri_truoc_vat - tong_gia_dat_duoc_tru)),
        CHECK ((trang_thai = 'PENDING' AND xac_nhan_boi IS NULL AND xac_nhan_luc IS NULL) OR
            (trang_thai = 'DA_XAC_NHAN' AND xac_nhan_boi IS NOT NULL AND xac_nhan_luc IS NOT NULL
             AND gia_tri_truoc_vat IS NOT NULL AND tong_gia_dat_duoc_tru IS NOT NULL
             AND phan_chiu_thue IS NOT NULL AND vat IS NOT NULL AND tong_thanh_toan IS NOT NULL
             AND currency IS NOT NULL AND ngay_nghiep_vu IS NOT NULL AND hieu_luc_tu IS NOT NULL)))""",
    """CREATE FUNCTION m3.co_so_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = m3, pg_temp AS $$
        BEGIN
            IF NEW.trang_thai = 'DA_XAC_NHAN' AND NOT EXISTS (
                SELECT 1 FROM master.hop_dong_phien_ban p
                WHERE p.id = NEW.hop_dong_phien_ban_id AND p.hop_dong_id = NEW.hop_dong_id
                  AND p.trang_thai = 'DA_DUYET') THEN
                RAISE EXCEPTION 'M3_CO_SO_PENDING: phiên bản CRM chưa duyệt' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hop_dong_co_so_kiem BEFORE INSERT ON m3.hop_dong_co_so FOR EACH ROW EXECUTE FUNCTION m3.co_so_kiem()",
    """CREATE TABLE m3.hoa_don_hop_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        khoa_lien_ket uuid NOT NULL DEFAULT gen_random_uuid(),
        revision integer NOT NULL CHECK (revision >= 1),
        thay_cho_id uuid,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        co_so_id uuid NOT NULL,
        hoa_don_id uuid,
        hoa_don_phien_ban_id uuid,
        hoa_don_quan_sat_id uuid,
        nguon text NOT NULL CHECK (length(btrim(nguon)) > 0),
        nguon_ref text NOT NULL CHECK (length(btrim(nguon_ref)) > 0),
        nguon_sha256 text CHECK (nguon_sha256 ~ '^[0-9a-f]{64}$'),
        nguon_vi_tri text,
        can_cu text,
        trang_thai text NOT NULL DEFAULT 'PENDING' CHECK (trang_thai IN ('PENDING','DA_XAC_NHAN')),
        ly_do_pending text,
        xac_nhan_boi text CHECK (length(btrim(xac_nhan_boi)) > 0),
        xac_nhan_luc timestamptz,
        tao_boi text NOT NULL CHECK (length(btrim(tao_boi)) > 0),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (co_so_id, phap_nhan_id) REFERENCES m3.hop_dong_co_so (id, phap_nhan_id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id) REFERENCES kho.hoa_don_danh_tinh (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id)
            REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_quan_sat_id, hoa_don_phien_ban_id)
            REFERENCES kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id, phien_ban_id),
        UNIQUE (khoa_lien_ket, revision),
        UNIQUE (id, khoa_lien_ket, phap_nhan_id),
        UNIQUE (thay_cho_id),
        FOREIGN KEY (thay_cho_id, khoa_lien_ket, phap_nhan_id)
            REFERENCES m3.hoa_don_hop_dong (id, khoa_lien_ket, phap_nhan_id),
        CHECK ((revision = 1 AND thay_cho_id IS NULL) OR (revision > 1 AND thay_cho_id IS NOT NULL)),
        CHECK ((hoa_don_id IS NULL AND hoa_don_phien_ban_id IS NULL AND hoa_don_quan_sat_id IS NULL) OR
               (hoa_don_id IS NOT NULL AND hoa_don_phien_ban_id IS NOT NULL AND hoa_don_quan_sat_id IS NOT NULL)),
        CHECK ((trang_thai = 'PENDING' AND xac_nhan_boi IS NULL AND xac_nhan_luc IS NULL) OR
               (trang_thai = 'DA_XAC_NHAN' AND hoa_don_id IS NOT NULL AND xac_nhan_boi IS NOT NULL
                AND xac_nhan_luc IS NOT NULL AND can_cu IS NOT NULL AND length(btrim(can_cu)) > 0)))""",
    """CREATE FUNCTION m3.lien_ket_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = m3, pg_temp AS $$
        BEGIN
            IF NEW.thay_cho_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM m3.hoa_don_hop_dong c WHERE c.id = NEW.thay_cho_id AND c.revision + 1 = NEW.revision) THEN
                RAISE EXCEPTION 'M3_MAPPING_REVISION: phải nối tiếp bản cũ' USING ERRCODE = '23514';
            END IF;
            IF NEW.hoa_don_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM kho.hoa_don_danh_tinh h WHERE h.id = NEW.hoa_don_id AND h.chieu <> 'BAN_RA') THEN
                RAISE EXCEPTION 'M3_HOA_DON_CHIEU: chỉ liên kết hóa đơn bán' USING ERRCODE = '23514';
            END IF;
            IF NEW.trang_thai = 'DA_XAC_NHAN' AND NOT EXISTS (
                SELECT 1 FROM m3.hop_dong_co_so c JOIN kho.hoa_don_phien_ban p
                    ON p.id = NEW.hoa_don_phien_ban_id AND p.phap_nhan_id = c.phap_nhan_id
                JOIN kho.hoa_don_danh_tinh h ON h.id = p.hoa_don_id
                WHERE c.id = NEW.co_so_id AND c.trang_thai = 'DA_XAC_NHAN'
                  AND c.currency = p.tien_te AND h.chieu = 'BAN_RA') THEN
                RAISE EXCEPTION 'M3_MAPPING_PENDING: thiếu cơ sở xác nhận hoặc hóa đơn bán cùng currency' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hoa_don_hop_dong_kiem BEFORE INSERT ON m3.hoa_don_hop_dong FOR EACH ROW EXECUTE FUNCTION m3.lien_ket_kiem()",
    """CREATE TABLE m3.policy_hinh_thuc_doanh_thu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai_hinh_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        hinh_thuc text CHECK (hinh_thuc IN ('GHI_NHAN_LUON','PHAN_BO')),
        hieu_luc_tu date NOT NULL,
        trang_thai text NOT NULL DEFAULT 'PENDING' CHECK (trang_thai IN ('PENDING','DA_XAC_NHAN')),
        ly_do_pending text,
        xac_nhan_boi text CHECK (length(btrim(xac_nhan_boi)) > 0),
        xac_nhan_luc timestamptz,
        nguon text NOT NULL CHECK (length(btrim(nguon)) > 0),
        tao_boi text NOT NULL CHECK (length(btrim(tao_boi)) > 0),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (phap_nhan_id, loai_hinh_id, hieu_luc_tu, revision),
        CHECK ((trang_thai = 'PENDING' AND xac_nhan_boi IS NULL AND xac_nhan_luc IS NULL) OR
               (trang_thai = 'DA_XAC_NHAN' AND hinh_thuc IS NOT NULL AND xac_nhan_boi IS NOT NULL AND xac_nhan_luc IS NOT NULL)))""",
    # INVOKER: app_web đọc qua RLS, chủ bảng dùng cùng truy vấn. Bản PENDING
    # mới nhất che bản đã duyệt cũ, không tự quay về policy cũ khi thiếu căn cứ.
    """CREATE FUNCTION m3.policy_tai_ngay(p_pn uuid, p_loai uuid, p_ngay date)
        RETURNS SETOF m3.policy_hinh_thuc_doanh_thu
        LANGUAGE sql STABLE SET search_path = m3, pg_temp AS $$
        SELECT p.* FROM m3.policy_hinh_thuc_doanh_thu p
        WHERE p.phap_nhan_id = p_pn AND p.loai_hinh_id = p_loai AND p.hieu_luc_tu <= p_ngay
        ORDER BY p.hieu_luc_tu DESC, p.revision DESC LIMIT 1
        $$""",
    """CREATE FUNCTION m3.ghi_nhat_ky() RETURNS trigger
        LANGUAGE plpgsql SET search_path = m3, pg_temp AS $$
        BEGIN
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau)
                VALUES (NEW.phap_nhan_id, NEW.tao_boi, 'SUA_DANH_MUC', 'm3.' || TG_TABLE_NAME,
                        NEW.id, 'M3_THEM_REVISION', to_jsonb(NEW));
            RETURN NEW;
        END $$""",
    """DO $$
        DECLARE t text; r text;
        BEGIN
            FOREACH t IN ARRAY ARRAY['hop_dong_co_so','hoa_don_hop_dong','policy_hinh_thuc_doanh_thu'] LOOP
                EXECUTE format('CREATE TRIGGER %I BEFORE INSERT OR UPDATE OR DELETE ON m3.%I FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()', t || '_bat_bien', t);
                EXECUTE format('CREATE TRIGGER %I BEFORE TRUNCATE ON m3.%I FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chan_truncate()', t || '_chan_truncate', t);
                EXECUTE format('CREATE TRIGGER %I AFTER INSERT ON m3.%I FOR EACH ROW EXECUTE FUNCTION m3.ghi_nhat_ky()', t || '_nhat_ky', t);
                EXECUTE format('ALTER TABLE m3.%I ENABLE ROW LEVEL SECURITY', t);
                EXECUTE format('REVOKE ALL ON m3.%I FROM PUBLIC', t);
                FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                        EXECUTE format('REVOKE ALL ON m3.%I FROM %I', t, r);
                    END IF;
                END LOOP;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
                    EXECUTE format('GRANT SELECT ON m3.%I TO app_web', t);
                    EXECUTE format('CREATE POLICY %I ON m3.%I FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, %L))', t || '_web', t, 'M3');
                END IF;
            END LOOP;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
                GRANT USAGE ON SCHEMA m3 TO app_web;
            END IF;
        END $$""",
    "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA m3 FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION m3.policy_tai_ngay(uuid, uuid, date) TO app_web;
        END IF;
    END $$""",
)

# M3-1c — CD-013: chưa có quy tắc chia giá trị; chỉ một liên kết xác nhận/hóa đơn.
# Cần Anh: hóa đơn chung cho nhiều hợp đồng có cần chia giá trị không.
# Chỉ bản hiện hành giữ chỗ; revision cũ vẫn bất biến để truy vết.
M3_CO_SO_B_SQL = (
    """CREATE FUNCTION m3.lien_ket_mot_xac_nhan() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, m3, pg_temp AS $$
        BEGIN
            IF NEW.trang_thai = 'DA_XAC_NHAN' THEN
                PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(NEW.hoa_don_id::text, 0));
                IF EXISTS (
                    SELECT 1 FROM m3.hoa_don_hop_dong l
                    WHERE l.phap_nhan_id = NEW.phap_nhan_id AND l.hoa_don_id = NEW.hoa_don_id
                      AND l.trang_thai = 'DA_XAC_NHAN' AND l.khoa_lien_ket <> NEW.khoa_lien_ket
                      AND NOT EXISTS (
                          SELECT 1 FROM m3.hoa_don_hop_dong s WHERE s.thay_cho_id = l.id)) THEN
                    RAISE EXCEPTION 'Hóa đơn đã có liên kết hiện hành được xác nhận ở chuỗi khác'
                        USING ERRCODE = '23505';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE TRIGGER hoa_don_hop_dong_mot_xac_nhan BEFORE INSERT ON m3.hoa_don_hop_dong
        FOR EACH ROW EXECUTE FUNCTION m3.lien_ket_mot_xac_nhan()""",
)
