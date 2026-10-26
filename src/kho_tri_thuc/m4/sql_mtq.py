"""MTQ-4f1b: cổng nội bộ cho lệnh hồ sơ M17; không đổi API đọc/RLS.

Các bản sao tính căn cứ trong migration chỉ chạy sau guard lệnh, bằng chủ
bảng. Không cấp helper cho app_web và không sửa master.m4_duoc dùng chung.
"""

MTQ_M4_A_SQL = (
    """CREATE FUNCTION m4._mtq_ho_so_quyen(p_hanh_dong text, p_id uuid) RETURNS boolean
        LANGUAGE plpgsql SET search_path = pg_catalog, master, m4, pg_temp AS $$
        DECLARE bang text; lenh text; obj uuid := p_id; pn uuid; giai jsonb; q jsonb;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            CASE p_hanh_dong
                WHEN 'TAO_HOP_DONG', 'TAI_TEP' THEN
                    bang := 'master.du_an'; lenh := 'M4:HO_SO:LAP';
                WHEN 'GAN_TEP_HOP_DONG', 'TRICH', 'SUA_THAM_SO', 'KHAI_PHU_LUC' THEN
                    bang := 'master.hop_dong'; lenh := 'M4:HO_SO:SUA';
                WHEN 'XAC_NHAN_THAM_SO' THEN
                    bang := 'master.hop_dong'; lenh := 'M4:HO_SO:KIEM';
                WHEN 'THEM_PHU_LUC', 'NHAP_BOQ', 'TAO_DOT' THEN
                    bang := 'master.hop_dong'; lenh := 'M4:HO_SO:LAP';
                WHEN 'HUY_PHU_LUC' THEN
                    SELECT p.hop_dong_id INTO obj FROM m4.phu_luc p WHERE p.id = p_id;
                    bang := 'master.hop_dong'; lenh := 'M4:HO_SO:HUY';
                WHEN 'SUA_DOT', 'GAN_TEP_DOT', 'NOP' THEN
                    bang := 'm4.dot'; lenh := 'M4:HO_SO:SUA';
                ELSE
                    RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: Thao tác này trên hồ sơ hợp đồng chưa được hỗ trợ.' USING ERRCODE = 'P0001';
            END CASE;
            -- M0051 giữ nguyên resolver M0048: PN/HĐ/dự án từ FK thật,
            -- HĐ chỉ module_chu=M4. Không nhận PN hoặc phạm vi từ caller.
            giai := master.mtq_giai_doi_tuong(lenh, jsonb_build_object('bang', bang, 'id', obj));
            pn := (giai->>'pn')::uuid;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE bat AND (pn IS NULL OR phap_nhan_id = pn)) THEN
                RETURN false; -- CU: caller chạy nguyên guard cũ, kể cả mã lỗi.
            END IF;
            PERFORM 1 FROM master.nguoi_dung n WHERE n.id = m4.ai_id() FOR SHARE;
            q := master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', bang, 'id', obj), NULL);
            IF q->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
                RAISE EXCEPTION '%: Anh/chị chưa được giao quyền thực hiện thao tác này trên hồ sơ hợp đồng.', coalesce(q->>'ma', 'MTQ_TU_CHOI') USING ERRCODE = 'P0001';
            END IF;
            RETURN true;
        END $$""",
    "REVOKE ALL ON FUNCTION m4._mtq_ho_so_quyen(text, uuid) FROM PUBLIC",
    """CREATE FUNCTION m4._mtq_ho_so_replay(p_hanh_dong text, p_yc jsonb, p_du_an uuid) RETURNS boolean
        LANGUAGE plpgsql SET search_path = pg_catalog, master, m4, pg_temp AS $$
        DECLARE pn uuid; obj uuid;
        BEGIN
            PERFORM pg_advisory_xact_lock_shared(742601, 1);
            SELECT a.phap_nhan_id INTO pn FROM master.du_an a WHERE a.id = p_du_an;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE bat AND (pn IS NULL OR phap_nhan_id = pn)) THEN
                RETURN false;
            END IF;
            -- Chỉ đọc yêu cầu bất biến của receipt đúng actor lấy từ CSDL.
            CASE p_hanh_dong
                WHEN 'TAO_HOP_DONG', 'TAI_TEP' THEN obj := (p_yc->>'du_an_id')::uuid;
                WHEN 'GAN_TEP_HOP_DONG', 'TRICH', 'SUA_THAM_SO', 'XAC_NHAN_THAM_SO',
                     'KHAI_PHU_LUC', 'THEM_PHU_LUC', 'NHAP_BOQ', 'TAO_DOT' THEN obj := (p_yc->>'hop_dong_id')::uuid;
                WHEN 'HUY_PHU_LUC' THEN obj := (p_yc->>'phu_luc_id')::uuid;
                WHEN 'SUA_DOT', 'GAN_TEP_DOT', 'NOP' THEN obj := (p_yc->>'dot_id')::uuid;
                ELSE
                    -- Receipt 02A/02B/02C/master có cổng riêng, lát này không mở.
                    RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: Chưa hỗ trợ tra cứu lại biên nhận cho thao tác này.' USING ERRCODE = 'P0001';
            END CASE;
            IF m4._mtq_ho_so_quyen(p_hanh_dong, obj) IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: Không xác định được hồ sơ hợp đồng của biên nhận trong pháp nhân đã kích hoạt.' USING ERRCODE = 'P0001';
            END IF;
            RETURN true;
        END $$""",
    "REVOKE ALL ON FUNCTION m4._mtq_ho_so_replay(text, jsonb, uuid) FROM PUBLIC",
)
