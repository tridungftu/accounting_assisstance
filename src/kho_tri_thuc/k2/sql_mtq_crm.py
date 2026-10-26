MTQ_CRM_A_SQL = (
    # G1/G7: đích và lệnh tường minh; không đòi thêm XEM khi ghi bằng MTQ.
    """CREATE OR REPLACE FUNCTION master.crm_g_dich(p_hanh_dong text, p_dich uuid, OUT pn uuid, OUT loai uuid)
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE bang text; lenh text; q jsonb;
        BEGIN
            -- Cùng khóa với công bố/bật/thu hồi MTQ; giữ đến hết giao dịch,
            -- kể cả khi caller gọi thẳng lệnh SQL mà không đi preflight.
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF p_hanh_dong = 'CRM_MAU_TAI' THEN
                bang := 'master.loai_hinh_doanh_thu'; lenh := 'CRM:G1_MAU:LAP';
                SELECT l.phap_nhan_id, l.id INTO pn, loai FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich;
            ELSIF p_hanh_dong IN ('CRM_MAU_MAP','CRM_MAU_GUI_KIEM','CRM_MAU_KIEM','CRM_MAU_TRA_LAI','CRM_MAU_DUYET_V4','CRM_MAU_TU_CHOI') THEN
                bang := 'master.crm_mau_phien_ban';
                lenh := CASE WHEN p_hanh_dong IN ('CRM_MAU_MAP','CRM_MAU_GUI_KIEM') THEN 'CRM:G1_MAU:SUA'
                             WHEN p_hanh_dong IN ('CRM_MAU_KIEM','CRM_MAU_TRA_LAI') THEN 'CRM:G1_MAU:KIEM'
                             ELSE 'CRM:G1_MAU:DUYET' END;
                SELECT v.phap_nhan_id, v.loai_hinh_id INTO pn, loai FROM master.crm_mau_phien_ban v WHERE v.id = p_dich;
            ELSIF p_hanh_dong = 'CRM_CHUAN_LAP' THEN
                bang := 'master.du_an'; lenh := 'CRM:G7_CHUAN:LAP';
                SELECT a.phap_nhan_id INTO pn FROM master.du_an a WHERE a.id = p_dich;
            ELSIF p_hanh_dong IN ('CRM_CHUAN_GUI_DUYET','CRM_CHUAN_DUYET_V4') THEN
                bang := 'master.crm_bo_chuan_phien_ban';
                lenh := CASE WHEN p_hanh_dong = 'CRM_CHUAN_GUI_DUYET' THEN 'CRM:G7_CHUAN:SUA' ELSE 'CRM:G7_CHUAN:DUYET' END;
                SELECT v.phap_nhan_id INTO pn FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_dich;
            ELSE
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF pn IS NULL THEN
                IF p_hanh_dong = 'CRM_MAU_TAI' THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy loại hình (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                ELSIF left(p_hanh_dong, 8) = 'CRM_MAU_' THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy phiên bản mẫu (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                ELSIF p_hanh_dong = 'CRM_CHUAN_LAP' THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                ELSE
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bộ chuẩn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                -- Khóa người dùng trước quyết định để việc vô hiệu danh tính
                -- đồng thời không lọt giữa kiểm và ghim.
                PERFORM 1 FROM master.nguoi_dung n WHERE n.id = master.crm_g_ai_id() FOR SHARE;
                q := master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', bang, 'id', p_dich), NULL);
                IF q->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
                    RAISE EXCEPTION '%: không có quyền hiện hành cho %', coalesce(q->>'ma', 'MTQ_TU_CHOI'), lenh USING ERRCODE = 'P0001';
                END IF;
                RETURN;
            END IF;
            -- CU: giữ đúng mức đọc và từng kiểm quyền cũ của M0018.
            IF p_hanh_dong = 'CRM_MAU_TAI' THEN
                IF NOT master.ktt_duoc(pn, 'CRM') THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy loại hình (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF left(p_hanh_dong, 8) = 'CRM_MAU_' THEN
                IF master.crm_g_mau_doc(pn, loai) IS DISTINCT FROM 'DAY_DU' THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy phiên bản mẫu (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF p_hanh_dong = 'CRM_CHUAN_LAP' THEN
                IF NOT master.ktt_duoc(pn, 'CRM') THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                IF NOT master.crm_g_chuan_doc_duoc(pn) THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bộ chuẩn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NOT master.crm_g_duoc(p_hanh_dong, pn, loai) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền hiện hành cho %', p_hanh_dong USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_tra(p_hanh_dong text, p_khoa text, p_dich uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE d record; cu jsonb; pn_tam uuid;
        BEGIN
            IF NOT master.la_chu_bang('master.crm_mau_phien_ban'::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_MAY_CHU: chỉ đường ghi tin cậy của máy chủ (chủ bảng) được thực hiện lệnh mẫu/bộ chuẩn' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            pn_tam := CASE WHEN p_hanh_dong = 'CRM_MAU_TAI' THEN (SELECT l.phap_nhan_id FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich)
                           WHEN left(p_hanh_dong, 8) = 'CRM_MAU_' THEN (SELECT v.phap_nhan_id FROM master.crm_mau_phien_ban v WHERE v.id = p_dich)
                           WHEN p_hanh_dong = 'CRM_CHUAN_LAP' THEN (SELECT a.phap_nhan_id FROM master.du_an a WHERE a.id = p_dich)
                           ELSE (SELECT v.phap_nhan_id FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_dich) END;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn_tam AND bat) THEN
                PERFORM master.crm_g_ghim_quyen(pn_tam);
            END IF;
            SELECT * INTO d FROM master.crm_g_dich(p_hanh_dong, p_dich);
            cu := master.crm_g_bn_tra(d.pn, p_hanh_dong, p_khoa, p_h);
            RETURN CASE WHEN cu IS NULL THEN NULL ELSE jsonb_build_object('lap_lai', true, 'ket_qua', cu) END;
        END $$""",
    # XEM G1 dùng LH thật (cùng phạm vi resolver M0047 của phiên bản mẫu).
    # Cần lead KK-MTQ4-CRM §5.2: chưa chốt nháp/lịch sử; XEM chỉ mở
    # đường hiệu lực đã có, không tự nâng thành DAY_DU/xem thử mẫu nháp.
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_doc(p_pn uuid, p_loai uuid) RETURNS text
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE pn uuid; q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            SELECT l.phap_nhan_id INTO pn FROM master.loai_hinh_doanh_thu l WHERE l.id = p_loai;
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE bat AND (
                (p_pn IS NULL AND pn IS NULL) OR phap_nhan_id = p_pn OR phap_nhan_id = pn)) THEN
                IF pn IS NULL OR pn IS DISTINCT FROM p_pn THEN RETURN NULL; END IF;
                q := master.mtq_quyet_dinh_phien('CRM:G1_MAU:XEM', jsonb_build_object('bang', 'master.loai_hinh_doanh_thu', 'id', p_loai), NULL);
                RETURN CASE WHEN q->>'nguon' = 'MA_TRAN' AND q->'cho_phep' = 'true'::jsonb THEN 'HIEU_LUC' ELSE NULL END;
            END IF;
            RETURN CASE WHEN NOT master.ktt_duoc(p_pn, 'CRM') THEN NULL
                        WHEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL)
                             OR master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai) THEN 'DAY_DU'
                        ELSE 'HIEU_LUC' END;
        END $$""",
    # Chữ ký cũ thiếu dự án/phiên bản: chặn khi bật; caller Python nối đích ở 4d1b.
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_doc_duoc(p_pn uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE bat AND (p_pn IS NULL OR phap_nhan_id = p_pn)) THEN RETURN false; END IF;
            RETURN master.ktt_duoc(p_pn, 'CRM') AND master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL);
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_duoc(p_hanh_dong text, p_pn uuid, p_loai uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE bat AND (p_pn IS NULL OR phap_nhan_id = p_pn)) THEN
                -- Chỉ tải mẫu có locator đầy đủ ở chữ ký cũ. Các cờ còn lại
                -- phải nối phiên bản/dự án ở 4d1b, không đoán từ PN/loại hình.
                IF p_hanh_dong IS DISTINCT FROM 'CRM_MAU_TAI' OR NOT EXISTS (
                    SELECT 1 FROM master.loai_hinh_doanh_thu WHERE id = p_loai AND phap_nhan_id = p_pn) THEN RETURN false; END IF;
                q := master.mtq_quyet_dinh_phien('CRM:G1_MAU:LAP', jsonb_build_object('bang', 'master.loai_hinh_doanh_thu', 'id', p_loai), NULL);
                RETURN coalesce(q->>'nguon' = 'MA_TRAN' AND q->'cho_phep' = 'true'::jsonb, false);
            END IF;
            RETURN master.ktt_duoc(p_pn, 'CRM') AND CASE
                WHEN p_hanh_dong = 'CRM_MAU_TAI' THEN master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai)
                WHEN p_hanh_dong IN ('CRM_MAU_MAP','CRM_MAU_GUI_KIEM') THEN master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai)
                     OR master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
                WHEN p_hanh_dong IN ('CRM_MAU_KIEM','CRM_MAU_TRA_LAI','CRM_CHUAN_LAP','CRM_CHUAN_GUI_DUYET')
                     THEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
                WHEN p_hanh_dong IN ('CRM_MAU_DUYET_V4','CRM_MAU_TU_CHOI','CRM_CHUAN_DUYET_V4') THEN master.ktt_co_vai(p_pn, ARRAY['CFO'], 'V4')
                ELSE false END;
        END $$""",
    # Cổng đọc có locator cho G7; không sửa RLS nền hay cấp quyền bảng.
    # Cần lead A3: cổng M0047 chưa dùng được cho mọi ca trong READ ONLY.
    """CREATE FUNCTION master.crm_g_chuan_xem(p_du_an uuid, p_day_du boolean) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE pn uuid; q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            SELECT a.phap_nhan_id INTO pn FROM master.du_an a WHERE a.id = p_du_an;
            IF pn IS NULL THEN RETURN false; END IF;
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                -- Cần lead §5.2: chưa chốt mức nháp/lịch sử G7.
                IF p_day_du IS DISTINCT FROM false THEN RETURN false; END IF;
                q := master.mtq_quyet_dinh_phien('CRM:G7_CHUAN:XEM', jsonb_build_object('bang', 'master.du_an', 'id', p_du_an), NULL);
                RETURN coalesce(q->>'nguon' = 'MA_TRAN' AND q->'cho_phep' = 'true'::jsonb, false);
            END IF;
            RETURN CASE WHEN p_day_du THEN master.crm_g_chuan_doc_duoc(pn) ELSE master.ktt_duoc(pn, 'CRM') END;
        END $$""",
    "REVOKE ALL ON FUNCTION master.crm_g_chuan_xem(uuid, boolean) FROM PUBLIC",
    # Chính policy typed G1/G7 đã gọi hàm này; giữ policy và mọi RLS nền.
    """CREATE OR REPLACE FUNCTION master.crm_g_viec_doc_duoc(p_bang text, p_id uuid, p_pn uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE pn uuid; loai uuid;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF p_bang = 'master.crm_mau_phien_ban' THEN
                SELECT v.phap_nhan_id, v.loai_hinh_id INTO pn, loai FROM master.crm_mau_phien_ban v WHERE v.id = p_id;
            ELSIF p_bang = 'master.crm_bo_chuan_phien_ban' THEN
                SELECT v.phap_nhan_id INTO pn FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_id;
            ELSE
                RETURN true;
            END IF;
            IF pn IS NULL OR pn IS DISTINCT FROM p_pn THEN RETURN false; END IF;
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                -- Policy typed vốn đòi DAY_DU ở mọi trạng thái. Cần lead
                -- §5.2 chốt mức đọc này; không suy DAY_DU chỉ từ tick XEM.
                RETURN false;
            END IF;
            RETURN CASE WHEN p_bang = 'master.crm_mau_phien_ban' THEN coalesce(master.crm_g_mau_doc(pn, loai) = 'DAY_DU', false)
                        ELSE master.crm_g_chuan_doc_duoc(pn) END;
        END $$""",
)


MTQ_CRM_B_SQL = (
    # Chỉ dùng nội bộ G2/G3; không thay helper nhóm mà G4/tỷ giá còn dùng.
    """CREATE FUNCTION master.crm_gk_ghim_quyen(p_pn uuid) RETURNS void
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = p_pn AND bat) THEN
                PERFORM 1 FROM master.nguoi_dung n WHERE n.id = master.crm_g_ai_id() FOR SHARE;
            ELSE
                PERFORM master.crm_g_ghim_quyen(p_pn);
            END IF;
        END $$""",
    "REVOKE ALL ON FUNCTION master.crm_gk_ghim_quyen(uuid) FROM PUBLIC",
    """CREATE OR REPLACE FUNCTION master.crm_gk_dich(p_hanh_dong text, p_dich uuid, OUT pn uuid, OUT loai uuid)
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE nhom text; bang text; lenh text; q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF p_hanh_dong = 'CRM_BAO_GIA_TAO' THEN
                SELECT l.phap_nhan_id, l.id INTO pn, loai FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich AND l.valid_to IS NULL;
                nhom := 'CRM_BAO_GIA'; bang := 'master.loai_hinh_doanh_thu'; lenh := 'CRM:G2_BAO_GIA:LAP';
            ELSIF p_hanh_dong IN ('CRM_BAO_GIA_LUU','CRM_BAO_GIA_HUY','CRM_BAO_GIA_IN','CRM_BAO_GIA_CHUYEN') THEN
                SELECT b.phap_nhan_id, b.loai_hinh_id INTO pn, loai FROM master.crm_bao_gia b WHERE b.id = p_dich;
                nhom := 'CRM_BAO_GIA'; bang := 'master.crm_bao_gia';
                lenh := CASE p_hanh_dong WHEN 'CRM_BAO_GIA_LUU' THEN 'CRM:G2_BAO_GIA:SUA'
                    WHEN 'CRM_BAO_GIA_HUY' THEN 'CRM:G2_BAO_GIA:HUY'
                    WHEN 'CRM_BAO_GIA_IN' THEN 'CRM:G2_BAO_GIA:XEM' ELSE 'CRM:G3_G4_SOAN_KY:LAP' END;
            ELSIF p_hanh_dong IN ('CRM_SOAN_LUU','CRM_SOAN_XUAT') THEN
                SELECT s.phap_nhan_id, s.loai_hinh_id INTO pn, loai FROM master.crm_hd_soan s WHERE s.id = p_dich;
                nhom := 'CRM_SOAN'; bang := 'master.crm_hd_soan';
                lenh := CASE p_hanh_dong WHEN 'CRM_SOAN_LUU' THEN 'CRM:G3_G4_SOAN_KY:SUA' ELSE 'CRM:G3_G4_SOAN_KY:XEM' END;
            ELSE
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF pn IS NOT NULL AND EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                PERFORM master.crm_gk_ghim_quyen(pn);
                q := master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', bang, 'id', p_dich), NULL);
                IF q->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
                    RAISE EXCEPTION '%: không có quyền hiện hành cho %', coalesce(q->>'ma', 'MTQ_TU_CHOI'), lenh USING ERRCODE = 'P0001';
                END IF;
                RETURN;
            END IF;
            -- CU: giữ cả thứ tự kiểm và mã lỗi M0021; không thêm XEM cho lệnh ghi.
            IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy đối tượng (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_gk_duoc(nhom, pn) OR (p_hanh_dong = 'CRM_BAO_GIA_CHUYEN' AND NOT master.crm_gk_duoc('CRM_SOAN', pn)) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền hiện hành cho %', p_hanh_dong USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    # Cờ/đọc có locator, chỉ gọi trên đường chủ bảng. Cổng boolean READ ONLY
    # của A3 thuộc MTQ-NEN; không gọi resolver nội bộ để tự dựng quyết định.
    """CREATE FUNCTION master.crm_gk_xem(p_bang text, p_id uuid, p_pn uuid) RETURNS boolean
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE pn uuid; loai uuid; nhom text; lenh text; q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            IF p_bang = 'master.crm_bao_gia' THEN
                SELECT b.phap_nhan_id INTO pn FROM master.crm_bao_gia b WHERE b.id = p_id;
                nhom := 'CRM_BAO_GIA'; lenh := 'CRM:G2_BAO_GIA:XEM';
            ELSIF p_bang = 'master.crm_hd_soan' THEN
                SELECT s.phap_nhan_id INTO pn FROM master.crm_hd_soan s WHERE s.id = p_id;
                nhom := 'CRM_SOAN'; lenh := 'CRM:G3_G4_SOAN_KY:XEM';
            ELSIF p_bang = 'master.crm_gk_xuat' THEN
                SELECT x.phap_nhan_id, CASE x.loai WHEN 'BAO_GIA' THEN 'CRM_BAO_GIA' WHEN 'HOP_DONG' THEN 'CRM_SOAN' END
                    INTO pn, nhom FROM master.crm_gk_xuat x WHERE x.id = p_id;
                lenh := CASE nhom WHEN 'CRM_BAO_GIA' THEN 'CRM:G2_BAO_GIA:XEM' WHEN 'CRM_SOAN' THEN 'CRM:G3_G4_SOAN_KY:XEM' END;
            ELSIF p_bang = 'master.loai_hinh_doanh_thu' THEN
                SELECT l.phap_nhan_id INTO pn FROM master.loai_hinh_doanh_thu l WHERE l.id = p_id;
                nhom := 'CRM_BAO_GIA'; lenh := 'CRM:G2_BAO_GIA:XEM';
            ELSIF p_bang = 'master.crm_mau_phien_ban' THEN
                SELECT v.phap_nhan_id, v.loai_hinh_id INTO pn, loai FROM master.crm_mau_phien_ban v WHERE v.id = p_id;
                lenh := 'CRM:G1_MAU:XEM';
            ELSE
                RETURN false;
            END IF;
            IF pn IS NULL OR pn IS DISTINCT FROM p_pn OR lenh IS NULL THEN RETURN false; END IF;
            IF EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN
                PERFORM master.crm_gk_ghim_quyen(pn);
                q := master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', p_bang, 'id', p_id), NULL);
                RETURN coalesce(q->>'nguon' = 'MA_TRAN' AND q->'cho_phep' = 'true'::jsonb, false);
            END IF;
            IF p_bang = 'master.crm_mau_phien_ban' THEN
                RETURN master.crm_g_mau_doc(pn, loai) IS NOT NULL;
            END IF;
            RETURN master.crm_gk_duoc(nhom, pn);
        END $$""",
    "REVOKE ALL ON FUNCTION master.crm_gk_xem(text, uuid, uuid) FROM PUBLIC",
)
