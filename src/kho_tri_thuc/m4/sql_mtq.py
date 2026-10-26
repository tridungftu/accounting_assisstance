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


def _mtq_m4_b_policy(bang: str, doi_tuong: str, obj: str, cu: str) -> str:
    """COALESCE chỉ chạy CU khi đúng PN chưa bật; false không fallback."""
    moi = f"m4.mtq_ho_so_doc('{doi_tuong}', {obj}, 'XEM')"
    if bang == 'nhat_ky':
        # Tải tệp có nhật ký dự án chưa gắn HĐ. Không làm mất dòng CU đó.
        moi = "m4.mtq_ho_so_doc(CASE WHEN hop_dong_id IS NULL THEN 'master.du_an' ELSE 'master.hop_dong' END, coalesce(hop_dong_id, du_an_id), 'XEM')"
    return f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            DROP POLICY IF EXISTS {bang}_web ON m4.{bang};
            CREATE POLICY {bang}_web ON m4.{bang} FOR SELECT TO app_web
                USING (coalesce({moi}, ({cu})));
        END IF;
    END $$"""


_M4_B_X = "master.m4_duoc(du_an_id, 'XEM')"
_M4_B_XR = _M4_B_X + " OR master.m4_duoc(du_an_id, 'REVIEW')"

# MTQ-4f1c — CD-012: chỉ đọc, không khóa/ghi, không đổi nguồn quyền CU.
MTQ_M4_B_SQL = (
    """CREATE FUNCTION m4.mtq_ho_so_doc(p_bang text, p_id uuid, p_hanh text) RETURNS boolean
        LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, master, m4, pg_temp AS $$
        DECLARE pn uuid;
        BEGIN
            IF p_id IS NULL OR p_hanh IS NULL OR p_hanh NOT IN ('XEM','LAP','SUA') THEN RETURN false; END IF;
            -- Suy PN từ dòng thật trước khi chọn CU. Resolver có thể từ chối
            -- HĐ mượn CRM; không dùng kết quả đó để làm đổi CU của PN tắt.
            CASE p_bang
                WHEN 'master.du_an' THEN SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id = p_id;
                WHEN 'master.hop_dong' THEN SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = p_id;
                WHEN 'm4.tep' THEN SELECT phap_nhan_id INTO pn FROM m4.tep WHERE id = p_id;
                WHEN 'm4.dot' THEN
                    SELECT a.phap_nhan_id INTO pn FROM m4.dot d JOIN master.du_an a ON a.id = d.du_an_id WHERE d.id = p_id;
                ELSE RETURN false;
            END CASE;
            IF pn IS NULL OR NOT EXISTS (SELECT 1 FROM master.phap_nhan WHERE id = pn) THEN RETURN false; END IF;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) THEN RETURN NULL; END IF;
            RETURN master.mtq_duoc_doc('M4:HO_SO:' || p_hanh, jsonb_build_object('bang', p_bang, 'id', p_id)) IS TRUE;
        END $$""",
    """CREATE FUNCTION m4.mau_duoc(p_du_an uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, master, m4, pg_temp AS $$
        SELECT coalesce(m4.mtq_ho_so_doc('master.du_an', p_du_an, 'LAP'), master.m4_duoc(p_du_an, 'SOAN'))
        $$""",
    "REVOKE ALL ON FUNCTION m4.mtq_ho_so_doc(text, uuid, text), m4.mau_duoc(uuid) FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION m4.mtq_ho_so_doc(text, uuid, text), m4.mau_duoc(uuid) TO app_web;
        END IF;
    END $$""",
    *(_mtq_m4_b_policy(t, 'master.hop_dong', 'hop_dong_id', _M4_B_XR) for t in (
        'ho_so_hop_dong', 'trich_xuat', 'tham_so', 'tham_so_lich_su', 'xac_nhan_tham_so',
        'phu_luc', 'boq', 'nop', 'master_can_cu', 'master_can_cu_phien_ban')),
    _mtq_m4_b_policy('boq_dong', 'master.hop_dong',
                     '(SELECT b.hop_dong_id FROM m4.boq b WHERE b.id = boq_id)', _M4_B_XR),
    _mtq_m4_b_policy('nhat_ky', 'master.hop_dong', 'hop_dong_id', _M4_B_X),
    # Biên nhận vẫn đúng actor; replay dùng guard lệnh gốc M0055, không dùng Xem.
    _mtq_m4_b_policy('bien_nhan', 'master.du_an', 'du_an_id',
                     "master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '') AND " + _M4_B_X)
        .replace("USING (coalesce(", "USING (nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '') AND coalesce("),
    _mtq_m4_b_policy('dot', 'm4.dot', 'id',
                     _M4_B_X + " OR (master.m4_duoc(du_an_id, 'REVIEW') AND trang_thai = 'DA_NOP')"),
    _mtq_m4_b_policy('dot_tep', 'm4.dot', 'dot_id',
                     _M4_B_X + " OR (master.m4_duoc(du_an_id, 'REVIEW') AND EXISTS (SELECT 1 FROM m4.dot d WHERE d.id = dot_id AND d.trang_thai = 'DA_NOP'))"),
    _mtq_m4_b_policy('tep', 'm4.tep', 'id',
                     _M4_B_X + " OR (master.m4_duoc(du_an_id, 'REVIEW') AND (vai_tro_tai_lieu <> 'HO_SO_DOT' OR m4.tep_da_nop(id)))"),
    *(_mtq_m4_b_policy(t, 'master.hop_dong', 'hop_dong_id', cu) for t, cu in (
        ('review_chep_hop_dong', _M4_B_XR), ('review_chep_tham_so', _M4_B_XR),
        ('review_chep_phu_luc', _M4_B_XR), ('review_chep_boq_dong', _M4_B_XR),
        ('review_chep_tham_so_nguon', _M4_B_XR), ('review_chep_dot_thanh_toan', _M4_B_X),
        ('review_chep_khop_hang_muc', _M4_B_X), ('review_chep_canh_bao', _M4_B_X), ('review_chep_nhat_ky', _M4_B_X))),
    _mtq_m4_b_policy('review_chep_thay_doi_tham_so', 'master.hop_dong',
                     '(SELECT p.hop_dong_id FROM m4.review_chep_phu_luc p WHERE p.nguon_id = review_chep_thay_doi_tham_so.nguon_id AND p.id = pl_id)', _M4_B_XR),
    _mtq_m4_b_policy('review_chep_kl_thanh_toan', 'master.hop_dong',
                     '(SELECT d.hop_dong_id FROM m4.review_chep_dot_thanh_toan d WHERE d.nguon_id = review_chep_kl_thanh_toan.nguon_id AND d.ma_hd = review_chep_kl_thanh_toan.ma_hd AND d.dot = review_chep_kl_thanh_toan.dot)', _M4_B_X),
    # Chỉ policy do M4 sở hữu; không đổi RLS nền master hay nhánh HĐ CRM.
    "DROP POLICY hop_dong_m4_rang_buoc ON master.hop_dong",
    """CREATE POLICY hop_dong_m4_rang_buoc ON master.hop_dong AS RESTRICTIVE TO PUBLIC
        USING (module_chu IS DISTINCT FROM 'M4' OR coalesce(m4.mtq_ho_so_doc('master.hop_dong', id, 'XEM'),
            (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'))))
        WITH CHECK (module_chu IS DISTINCT FROM 'M4')""",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            DROP POLICY hop_dong_m4_du_an ON master.hop_dong;
            CREATE POLICY hop_dong_m4_du_an ON master.hop_dong FOR SELECT TO app_web
                USING (module_chu = 'M4' AND coalesce(m4.mtq_ho_so_doc('master.hop_dong', id, 'XEM'),
                    (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'))));
        END IF;
    END $$""",
)
