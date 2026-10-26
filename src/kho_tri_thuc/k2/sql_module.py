"""XS-4b / CD-017: công tắc module × pháp nhân, không thay quyền MTQ.

Revision 0 là chế độ mặc định chưa có dòng ghi đè. S5 chỉ cho khôi phục
module cũ/đã vận hành; bảng điều kiện go-live thuộc XS-4b2.
"""

MODULE_CONG_TAC_SQL = (
    """CREATE TABLE master.module_danh_muc (
        ma text PRIMARY KEY CHECK (ma = btrim(ma) AND ma <> ''),
        che_do_mac_dinh text NOT NULL DEFAULT 'TAT'
            CHECK (che_do_mac_dinh IN ('TAT','THU','VAN_HANH')))""",
    """INSERT INTO master.module_danh_muc (ma, che_do_mac_dinh) VALUES
        ('CRM','VAN_HANH'), ('M2','VAN_HANH'), ('M4','VAN_HANH'), ('M0','VAN_HANH'),
        ('M3','TAT'), ('M9','TAT'), ('M10','TAT')""",
    """CREATE TABLE master.module_cong_tac (
        module text NOT NULL REFERENCES master.module_danh_muc(ma),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        che_do text NOT NULL CHECK (che_do IN ('TAT','THU','VAN_HANH')),
        revision bigint NOT NULL CHECK (revision > 0),
        da_van_hanh boolean NOT NULL DEFAULT false,
        ly_do text NOT NULL CHECK (btrim(ly_do) <> ''),
        doi_boi uuid NOT NULL REFERENCES master.nguoi_dung(id),
        doi_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY (module, phap_nhan_id),
        CHECK (che_do <> 'VAN_HANH' OR da_van_hanh))""",
    """CREATE TABLE master.module_nguoi_thu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        module text NOT NULL REFERENCES master.module_danh_muc(ma),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        cap_boi uuid NOT NULL REFERENCES master.nguoi_dung(id),
        cap_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ly_do_cap text NOT NULL CHECK (btrim(ly_do_cap) <> ''),
        thu_hoi_boi uuid REFERENCES master.nguoi_dung(id),
        thu_hoi_luc timestamptz,
        ly_do_thu_hoi text,
        CHECK ((thu_hoi_boi IS NULL AND thu_hoi_luc IS NULL AND ly_do_thu_hoi IS NULL)
            OR (thu_hoi_boi IS NOT NULL AND thu_hoi_luc IS NOT NULL
                AND ly_do_thu_hoi IS NOT NULL AND btrim(ly_do_thu_hoi) <> '')),
        CHECK (thu_hoi_luc IS NULL OR thu_hoi_luc >= cap_luc))""",
    """CREATE UNIQUE INDEX module_nguoi_thu_hien_hanh
        ON master.module_nguoi_thu (module, phap_nhan_id, nguoi_dung_id)
        WHERE thu_hoi_luc IS NULL""",
    "ALTER TABLE master.module_danh_muc ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.module_cong_tac ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.module_nguoi_thu ENABLE ROW LEVEL SECURITY",
    """CREATE TRIGGER module_khong_xoa BEFORE DELETE ON master.module_cong_tac
        FOR EACH ROW EXECUTE FUNCTION nhat_ky.chi_ghi_them()""",
    """CREATE TRIGGER module_khong_xoa BEFORE DELETE ON master.module_nguoi_thu
        FOR EACH ROW EXECUTE FUNCTION nhat_ky.chi_ghi_them()""",
    """CREATE TRIGGER module_khong_truncate BEFORE TRUNCATE ON master.module_cong_tac
        FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chi_ghi_them()""",
    """CREATE TRIGGER module_khong_truncate BEFORE TRUNCATE ON master.module_nguoi_thu
        FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chi_ghi_them()""",
    """CREATE FUNCTION master.module_trang_thai(p_module text, p_pn uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; cd text; rev bigint; duoc_thu boolean := false; hop_le boolean;
        BEGIN
            SELECT id INTO ai FROM master.nguoi_dung
                WHERE dang_nhap = master.ktt_danh_tinh() AND trang_thai = 'HOAT_DONG';
            hop_le := ai IS NOT NULL AND EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = p_pn);
            SELECT coalesce(c.che_do, d.che_do_mac_dinh), coalesce(c.revision, 0) INTO cd, rev
                FROM master.module_danh_muc d LEFT JOIN master.module_cong_tac c
                ON c.module = d.ma AND c.phap_nhan_id = p_pn WHERE d.ma = p_module;
            cd := coalesce(cd, 'TAT');
            IF hop_le AND cd = 'THU' THEN
                duoc_thu := master.mtq_la_admin() OR EXISTS (
                    SELECT 1 FROM master.module_nguoi_thu t WHERE t.module = p_module
                    AND t.phap_nhan_id = p_pn AND t.nguoi_dung_id = ai AND t.thu_hoi_luc IS NULL);
            END IF;
            RETURN jsonb_build_object('che_do', cd, 'revision', coalesce(rev, 0),
                'hien_luoi', hop_le AND (cd = 'VAN_HANH' OR duoc_thu),
                'cho_xem', hop_le AND (cd IN ('VAN_HANH','TAT') OR duoc_thu),
                'cho_ghi', hop_le AND (cd = 'VAN_HANH' OR duoc_thu),
                'cho_xuat_ngoai', hop_le AND cd = 'VAN_HANH',
                'cong_bo_chinh_thuc', hop_le AND cd = 'VAN_HANH',
                -- Handoff XS-4b quy định VAN_HANH: mọi cờ true, kể cả cờ này.
                'dai_dang_thu', hop_le AND (cd = 'VAN_HANH' OR duoc_thu));
        END $$""",
    # Helper chỉ dành cho các hàm cùng owner; không cấp EXECUTE cho ứng dụng.
    """CREATE FUNCTION master.module_kiem_admin(p_module text, p_pn uuid, p_ly_do text)
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid;
        BEGIN
            -- MTQ cấu hình dùng khóa độc quyền cùng khóa này: không đua với thu hồi Admin.
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF NOT master.mtq_la_admin() THEN
                RAISE EXCEPTION 'MODULE_CHI_ADMIN: chỉ Admin MTQ hiện hành';
            END IF;
            SELECT id INTO ai FROM master.nguoi_dung
                WHERE dang_nhap = master.ktt_danh_tinh() AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN RAISE EXCEPTION 'MODULE_CHI_ADMIN: danh tính không hợp lệ'; END IF;
            IF nullif(btrim(p_ly_do), '') IS NULL THEN
                RAISE EXCEPTION 'MODULE_CAN_LY_DO: bắt buộc lý do';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.module_danh_muc WHERE ma = p_module)
                OR NOT EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = p_pn) THEN
                RAISE EXCEPTION 'MODULE_DAU_VAO: module hoặc pháp nhân chưa khai báo';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
            RETURN ai;
        END $$""",
    """CREATE FUNCTION master.module_danh_sach_nguoi_thu(p_module text, p_pn uuid)
        RETURNS SETOF master.module_nguoi_thu LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        BEGIN
            PERFORM master.module_kiem_admin(p_module, p_pn, 'Xem danh sách người thử');
            -- Admin xem cả lịch sử cấp/thu hồi, chỉ trong đúng module × pháp nhân.
            RETURN QUERY SELECT t.* FROM master.module_nguoi_thu t
                WHERE t.module = p_module AND t.phap_nhan_id = p_pn
                ORDER BY t.cap_luc, t.id;
        END $$""",
    """CREATE FUNCTION master.module_doi_che_do(p_module text, p_pn uuid, p_che_do text,
        p_ly_do text, p_revision_cu bigint) RETURNS bigint
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; cu master.module_cong_tac%ROWTYPE; mac_dinh text;
            cd_cu text; rev bigint; da_chay boolean; moi master.module_cong_tac%ROWTYPE;
        BEGIN
            ai := master.module_kiem_admin(p_module, p_pn, p_ly_do);
            IF p_che_do IS NULL OR p_che_do NOT IN ('TAT','THU','VAN_HANH') THEN
                RAISE EXCEPTION 'MODULE_CHE_DO: chế độ không hợp lệ';
            END IF;
            SELECT che_do_mac_dinh INTO mac_dinh FROM master.module_danh_muc WHERE ma = p_module;
            SELECT * INTO cu FROM master.module_cong_tac
                WHERE module = p_module AND phap_nhan_id = p_pn FOR UPDATE;
            cd_cu := coalesce(cu.che_do, mac_dinh);
            rev := coalesce(cu.revision, 0);
            IF p_revision_cu IS DISTINCT FROM rev THEN
                RAISE EXCEPTION 'MODULE_REVISION: công tắc đã đổi, cần đọc lại';
            END IF;
            da_chay := coalesce(cu.da_van_hanh, false) OR cd_cu = 'VAN_HANH';
            -- Chủ bảng/DBA là bên tin cậy; DML qua migration có review, vai ứng dụng đã khóa.
            IF p_che_do = 'VAN_HANH' AND mac_dinh <> 'VAN_HANH' AND NOT da_chay THEN
                RAISE EXCEPTION 'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE: chờ bảng điều kiện go-live';
            END IF;
            INSERT INTO master.module_cong_tac (module, phap_nhan_id, che_do, revision,
                da_van_hanh, ly_do, doi_boi, doi_luc)
                VALUES (p_module, p_pn, p_che_do, rev + 1, da_chay OR p_che_do = 'VAN_HANH',
                    btrim(p_ly_do), ai, clock_timestamp())
                ON CONFLICT (module, phap_nhan_id) DO UPDATE SET che_do = EXCLUDED.che_do,
                    revision = EXCLUDED.revision, da_van_hanh = EXCLUDED.da_van_hanh,
                    ly_do = EXCLUDED.ly_do, doi_boi = EXCLUDED.doi_boi, doi_luc = EXCLUDED.doi_luc
                RETURNING * INTO moi;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang,
                hanh_dong, truoc, sau, ly_do)
                VALUES (p_pn, moi.doi_luc, ai::text, 'SUA_DANH_MUC', 'master.module_cong_tac',
                    'MODULE_DOI_CHE_DO', jsonb_build_object('module', p_module, 'phap_nhan_id', p_pn,
                        'che_do', cd_cu, 'revision', rev), to_jsonb(moi), btrim(p_ly_do));
            RETURN moi.revision;
        END $$""",
    """CREATE FUNCTION master.module_cap_nguoi_thu(p_module text, p_pn uuid, p_nguoi uuid,
        p_ly_do text) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; moi master.module_nguoi_thu%ROWTYPE;
        BEGIN
            ai := master.module_kiem_admin(p_module, p_pn, p_ly_do);
            IF NOT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE id = p_nguoi AND trang_thai = 'HOAT_DONG') THEN
                RAISE EXCEPTION 'MODULE_NGUOI_THU: cần người dùng hoạt động';
            END IF;
            IF EXISTS (SELECT 1 FROM master.module_nguoi_thu WHERE module = p_module
                AND phap_nhan_id = p_pn AND nguoi_dung_id = p_nguoi AND thu_hoi_luc IS NULL) THEN
                RAISE EXCEPTION 'MODULE_DA_CAP: người dùng đang được thử';
            END IF;
            INSERT INTO master.module_nguoi_thu (module, phap_nhan_id, nguoi_dung_id, cap_boi, ly_do_cap)
                VALUES (p_module, p_pn, p_nguoi, ai, btrim(p_ly_do)) RETURNING * INTO moi;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang,
                doi_tuong_id, hanh_dong, sau, ly_do)
                VALUES (p_pn, moi.cap_luc, ai::text, 'SUA_DANH_MUC', 'master.module_nguoi_thu',
                    moi.id, 'MODULE_CAP_NGUOI_THU', jsonb_build_object('id', moi.id,
                        'module', p_module, 'phap_nhan_id', p_pn, 'hanh_dong', 'CAP',
                        'ly_do', btrim(p_ly_do), 'nguoi_thuc_hien', ai), btrim(p_ly_do));
            RETURN moi.id;
        END $$""",
    """CREATE FUNCTION master.module_thu_hoi_nguoi_thu(p_module text, p_pn uuid, p_nguoi uuid,
        p_ly_do text) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; cu master.module_nguoi_thu%ROWTYPE; moi master.module_nguoi_thu%ROWTYPE;
        BEGIN
            ai := master.module_kiem_admin(p_module, p_pn, p_ly_do);
            SELECT * INTO cu FROM master.module_nguoi_thu WHERE module = p_module
                AND phap_nhan_id = p_pn AND nguoi_dung_id = p_nguoi AND thu_hoi_luc IS NULL FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'MODULE_CHUA_CAP: không có lượt thử hiện hành'; END IF;
            UPDATE master.module_nguoi_thu SET thu_hoi_boi = ai, thu_hoi_luc = clock_timestamp(),
                ly_do_thu_hoi = btrim(p_ly_do) WHERE id = cu.id RETURNING * INTO moi;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang,
                doi_tuong_id, hanh_dong, sau, ly_do)
                VALUES (p_pn, moi.thu_hoi_luc, ai::text, 'SUA_DANH_MUC', 'master.module_nguoi_thu',
                    moi.id, 'MODULE_THU_HOI_NGUOI_THU', jsonb_build_object('id', moi.id,
                        'module', p_module, 'phap_nhan_id', p_pn, 'hanh_dong', 'THU_HOI',
                        'ly_do', btrim(p_ly_do), 'nguoi_thuc_hien', ai), btrim(p_ly_do));
            RETURN moi.id;
        END $$""",
    """REVOKE ALL ON master.module_danh_muc, master.module_cong_tac, master.module_nguoi_thu FROM PUBLIC""",
    """REVOKE ALL ON FUNCTION master.module_trang_thai(text,uuid),
        master.module_danh_sach_nguoi_thu(text,uuid),
        master.module_kiem_admin(text,uuid,text), master.module_doi_che_do(text,uuid,text,text,bigint),
        master.module_cap_nguoi_thu(text,uuid,uuid,text), master.module_thu_hoi_nguoi_thu(text,uuid,uuid,text)
        FROM PUBLIC""",
    """DO $$ DECLARE r text; BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON master.module_danh_muc, master.module_cong_tac,
                    master.module_nguoi_thu FROM %I', r);
                EXECUTE format('REVOKE ALL ON FUNCTION master.module_trang_thai(text,uuid),
                    master.module_danh_sach_nguoi_thu(text,uuid),
                    master.module_kiem_admin(text,uuid,text), master.module_doi_che_do(text,uuid,text,text,bigint),
                    master.module_cap_nguoi_thu(text,uuid,uuid,text),
                    master.module_thu_hoi_nguoi_thu(text,uuid,uuid,text) FROM %I', r);
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION master.module_trang_thai(text,uuid),
                master.module_danh_sach_nguoi_thu(text,uuid),
                master.module_doi_che_do(text,uuid,text,text,bigint),
                master.module_cap_nguoi_thu(text,uuid,uuid,text),
                master.module_thu_hoi_nguoi_thu(text,uuid,uuid,text) TO app_web;
        END IF;
        END $$""",
)
