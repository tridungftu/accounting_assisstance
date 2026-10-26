"""XS-T1a / CD-017: phép chiếu đầu hóa đơn M2, chỉ đọc, không cấp quyền bảng.

Đầu vào là PN và tập ID danh tính như occurrence_id của đối chiếu hiện hữu.
Giữ quyền đọc M2 của đối chiếu; công tắc không thay quyền người dùng.
Envelope v1: CO_DU_LIEU chỉ nói có nguồn, không xác nhận đủ căn cứ ghi nhận.
CHO luôn có hoa_don=[]; sai quyền là lỗi 42501, không giả thành CHO.
Phiên bản hiện hành theo latest_observation_id (không theo max phiên bản hay
eligible_content_id). semantic_sha256 là hash nội dung M2 đã lưu, không băm lại
phép chiếu. tong_tien giữ JSON field state/lexeme nếu nguồn có trường này;
thiếu thì NULL. total_minor giữ bigint NULL khi UNPROVEN_NO_MINOR.
Không trả raw_header_states, raw_components, dòng/tệp.
"""

CONG_BO_HOA_DON_SQL = (
    """CREATE FUNCTION master.hoa_don_cong_bo(p_pn uuid, p_hoa_don_ids uuid[])
        RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, master, kho, giao_tiep, pg_temp AS $$
        DECLARE ds jsonb; cong_tac jsonb;
        BEGIN
            -- Kiểm quyền trước công tắc/lookup: không lộ chế độ hay ID ngoài PN.
            IF p_pn IS NULL OR master.ktt_danh_tinh() IS NULL
                OR NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() AS pv(phap_nhan_id)
                    WHERE pv.phap_nhan_id = p_pn)
                OR NOT coalesce(kho._dc_m2_doc(p_pn), false) THEN
                RAISE EXCEPTION 'HOA_DON_CONG_BO_PHAM_VI: không có quyền đọc hóa đơn ở pháp nhân này'
                    USING ERRCODE = '42501';
            END IF;
            cong_tac := master.module_trang_thai('M2', p_pn);
            IF (cong_tac->>'cong_bo_chinh_thuc')::boolean IS DISTINCT FROM true THEN
                RETURN jsonb_build_object('contract', 'm2-hoa-don-cong-bo/v1',
                    'phap_nhan_id', p_pn, 'trang_thai', 'CHO',
                    'ly_do', 'Chờ hóa đơn mua vào', 'hoa_don', '[]'::jsonb);
            END IF;
            IF p_hoa_don_ids IS NULL OR array_position(p_hoa_don_ids, NULL) IS NOT NULL THEN
                RAISE EXCEPTION 'HOA_DON_CONG_BO_THAM_SO: cần tập ID hóa đơn không chứa NULL'
                    USING ERRCODE = '22023';
            END IF;
            SELECT coalesce(jsonb_agg(jsonb_build_object(
                'hoa_don_id', d.id, 'phap_nhan_id', d.phap_nhan_id,
                'phien_ban_id', v.id, 'phien_ban', v.phien_ban,
                'semantic_contract', v.semantic_contract, 'semantic_sha256', v.semantic_sha256,
                'so_chuan', d.so_chuan, 'so_hoa_don', v.raw_header_states->'SHDon',
                'mau_so', d.mau_so, 'ky_hieu', d.ky_hieu, 'ngay_lap', v.ngay_lap,
                'mst_ban', d.mst_ban, 'mst_mua', v.raw_header_states->'NMua/MST'->>'lexeme',
                'tien_te', v.tien_te, 'tong_tien', v.raw_header_states->'TgTTTBSo',
                'total_minor', v.total_minor, 'money_basis_state', v.money_basis_state,
                'trang_thai_nguon', jsonb_build_object(
                    'quan_sat_id', o.id, 'classification', o.classification,
                    'native_fiscal_status', o.native_fiscal_status,
                    'raw_status_namespace', o.raw_status_namespace, 'raw_status', o.raw_status,
                    'accepted_source_observation_id', d.accepted_source_observation_id,
                    'eligible_content_id', d.eligible_content_id),
                'coverage', l.coverage, 'coverage_hieu_luc', l.coverage_hieu_luc,
                'period_completeness', coalesce(l.ket_qua->>'period_completeness', 'UNKNOWN')
            ) ORDER BY d.id), '[]'::jsonb) INTO ds
            FROM kho.hoa_don_danh_tinh d
            JOIN kho.hoa_don_quan_sat o ON o.id = d.latest_observation_id
                AND o.hoa_don_id = d.id AND o.phap_nhan_id = d.phap_nhan_id
            JOIN kho.hoa_don_phien_ban v ON v.id = o.phien_ban_id
                AND v.hoa_don_id = d.id AND v.phap_nhan_id = d.phap_nhan_id
            JOIN giao_tiep.lan_tiep_nhan_nguon l ON l.id = o.lan_tiep_nhan_id
                AND l.source_instance_id = o.source_instance_id AND l.snapshot_id = o.snapshot_id
            WHERE d.phap_nhan_id = p_pn AND d.chieu = 'MUA_VAO' AND d.id = ANY(p_hoa_don_ids);
            RETURN jsonb_build_object('contract', 'm2-hoa-don-cong-bo/v1',
                'phap_nhan_id', p_pn,
                'trang_thai', CASE WHEN ds = '[]'::jsonb THEN 'CHO' ELSE 'CO_DU_LIEU' END,
                'ly_do', CASE WHEN ds = '[]'::jsonb THEN 'Chờ hóa đơn mua vào' ELSE NULL END,
                'hoa_don', ds);
        END $$""",
    "REVOKE ALL ON FUNCTION master.hoa_don_cong_bo(uuid,uuid[]) FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION master.hoa_don_cong_bo(uuid,uuid[]) TO app_web;
        END IF;
    END $$""",
)
