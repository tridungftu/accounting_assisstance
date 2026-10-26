"""mtq_duoc_doc dùng cho quyết định đọc/đếm/hiển thị với số tiền tùy chọn.

Thực hiện hành động vẫn phải qua cổng phiên.
"""

MTQ_NEN_A_SQL = (
    # Phần tính thuần M0039, chỉ nhận kết quả resolver tin cậy từ chủ bảng.
    # Không cấp hàm nội bộ này cho app_web; giữ nguyên mtq_quyet_dinh cũ.
    """CREATE FUNCTION master.mtq_tinh_doc(p_pn uuid, p_phong uuid, p_lenh text, p_loai text,
        p_doi_tuong text, p_khoa text, p_scope_loai text, p_tien_vnd numeric, p_scope uuid) RETURNS boolean
        LANGUAGE plpgsql STABLE
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE ai uuid; login text := master.ktt_danh_tinh(); kh master.mtq_kich_hoat; v master.mtq_phien_ban;
            g master.mtq_gan_vai; s master.mtq_pham_vi; d master.mtq_dong; c master.mtq_danh_muc_hanh_dong;
        BEGIN
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login;
            SELECT * INTO kh FROM master.mtq_kich_hoat WHERE phap_nhan_id = p_pn;
            IF ai IS NULL THEN RETURN false;
            ELSIF p_pn IS NULL OR NOT EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = p_pn) THEN
                RETURN false;
            ELSIF NOT coalesce(kh.bat, false) THEN RETURN NULL;
            ELSE
                SELECT * INTO v FROM master.mtq_phien_ban WHERE id = kh.phien_ban_id AND phap_nhan_id = p_pn AND trang_thai = 'DA_CONG_BO';
                SELECT * INTO c FROM master.mtq_danh_muc_hanh_dong WHERE catalog_version = v.catalog_version AND lenh_ky_thuat = p_lenh AND loai_doi_tuong = p_loai;
                SELECT * INTO g FROM master.mtq_gan_vai WHERE nguoi_dung_id = ai AND phap_nhan_id = p_pn AND phong_id = p_phong AND thu_hoi_luc IS NULL;
                SELECT * INTO s FROM master.mtq_pham_vi WHERE id = p_scope AND gan_vai_id = g.id AND phap_nhan_id = p_pn AND thu_hoi_luc IS NULL;
                SELECT * INTO d FROM master.mtq_dong WHERE phien_ban_id = v.id AND phap_nhan_id = p_pn AND phong_id = p_phong AND vai = g.vai;
                IF v.id IS NULL THEN RETURN false;
                ELSIF c.module IS NULL THEN RETURN false;
                ELSIF g.id IS NULL OR NOT EXISTS (SELECT 1 FROM master.mtq_phong WHERE id = p_phong AND phap_nhan_id = p_pn AND hoat_dong) THEN
                    RETURN false;
                ELSIF nullif(btrim(p_doi_tuong), '') IS NULL OR s.id IS NULL
                    OR s.loai IS DISTINCT FROM p_scope_loai OR s.khoa IS DISTINCT FROM p_khoa THEN
                    RETURN false;
                ELSIF d.id IS NULL OR NOT EXISTS (SELECT 1 FROM master.mtq_o WHERE dong_id = d.id AND module = c.module AND man = c.man AND hanh_dong = c.hanh_dong AND cho_phep) THEN
                    RETURN false;
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND
                    (p_tien_vnd IS NULL OR p_tien_vnd < 0 OR p_tien_vnd >= 'Infinity'::numeric OR p_tien_vnd <> trunc(p_tien_vnd)) THEN
                    RETURN false;
                ELSIF c.hanh_dong = 'DUYET' AND c.loai_tien <> 'PHI_TIEN' AND d.gioi_han_vnd IS NOT NULL AND p_tien_vnd > d.gioi_han_vnd THEN
                    RETURN false;
                ELSE RETURN true; END IF;
            END IF;
        END $$""",
    """CREATE FUNCTION master.mtq_duoc_doc(p_hanh_dong text, p_doi_tuong jsonb,
        p_so_tien numeric DEFAULT NULL) RETURNS boolean
        LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE
            login text := master.ktt_danh_tinh(); ai uuid; giai jsonb;
            pn uuid; phong uuid; hd uuid; da uuid; lh uuid; khach uuid;
            scope_id uuid; khoa text; scope_loai text; n bigint;
        BEGIN
            SELECT id INTO ai FROM master.nguoi_dung
                WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN RETURN false; END IF;
            giai := master.mtq_giai_doi_tuong(p_hanh_dong, p_doi_tuong);
            -- Đầu vào không hợp lệ/không giải được luôn chặn, kể cả khi tắt.
            IF (giai->>'hop_le')::boolean IS DISTINCT FROM true THEN RETURN false; END IF;
            pn := (giai->>'pn')::uuid; hd := (giai->>'hd')::uuid;
            da := (giai->>'da')::uuid; lh := (giai->>'lh')::uuid;
            khach := (giai->>'khach')::uuid; phong := (giai->>'phong')::uuid;
            IF pn IS NULL OR NOT EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = pn) THEN
                RETURN false;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                RETURN NULL;
            END IF;
            -- Cùng cách chọn đúng một phòng và phạm vi ưu tiên với cổng M0051.
            SELECT count(*), (array_agg(g.phong_id))[1] INTO n, phong
                FROM master.mtq_gan_vai g
                JOIN master.mtq_phong p ON p.id = g.phong_id AND p.phap_nhan_id = g.phap_nhan_id AND p.hoat_dong
                WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.thu_hoi_luc IS NULL
                    AND (phong IS NULL OR g.phong_id = phong);
            IF n > 1 THEN RETURN false; END IF;
            SELECT s.id, s.khoa, s.loai INTO scope_id, khoa, scope_loai
                FROM master.mtq_pham_vi s JOIN master.mtq_gan_vai g ON g.id = s.gan_vai_id
                WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.phong_id = phong
                    AND g.thu_hoi_luc IS NULL AND s.phap_nhan_id = pn AND s.thu_hoi_luc IS NULL
                    AND ((s.loai = 'PHAP_NHAN' AND s.khoa = pn::text)
                        OR (s.loai = 'HOP_DONG' AND s.khoa = hd::text)
                        OR (s.loai = 'DU_AN' AND s.khoa = da::text)
                        OR (s.loai = 'LOAI_HINH' AND s.khoa = lh::text)
                        OR (s.loai = 'KHACH' AND s.khoa = khach::text))
                ORDER BY CASE s.loai WHEN 'HOP_DONG' THEN 1 WHEN 'DU_AN' THEN 2
                    WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 ELSE 5 END, s.id LIMIT 1;
            -- Cùng số tiền cho cùng quyết định như cổng phiên; thiếu tiền vẫn chặn
            -- hành động cần tiền. Thực hiện hành động vẫn phải qua cổng phiên.
            -- STABLE dùng snapshot của câu lệnh, không lấy khóa/ghi rồi rollback.
            RETURN master.mtq_tinh_doc(pn, phong, p_hanh_dong, giai->>'loai',
                ((p_doi_tuong->>'id')::uuid)::text, khoa, scope_loai, p_so_tien, scope_id);
        END $$""",
    """REVOKE ALL ON FUNCTION master.mtq_tinh_doc(uuid,uuid,text,text,text,text,text,numeric,uuid),
        master.mtq_duoc_doc(text,jsonb,numeric) FROM PUBLIC""",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION master.mtq_duoc_doc(text,jsonb,numeric) TO app_web;
        END IF;
        END $$""",
)
