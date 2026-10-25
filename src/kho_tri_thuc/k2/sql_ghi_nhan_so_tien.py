"""03B: khai một phần bằng số tiền, dữ liệu đọc cho màn kế toán (QD-20261025-13).

Chỉ hằng SQL; dùng lại nguyên thân các hàm M0029 và thay đúng các đoạn tiền.
Không đổi quyền, closure, CAS, biên nhận, đồ thị nguồn hoặc dữ liệu lịch sử.
Mỗi phép thay có kiểm số lần để không âm thầm mất guard khi nguồn thay đổi.
"""

from .sql_ghi_nhan_chung import M4_03B_COMMON_SQL


def _ham(ten):
    return next(s for s in M4_03B_COMMON_SQL if s.startswith(f"CREATE OR REPLACE FUNCTION {ten}("))


def _doi(sql, cu, moi):
    if sql.count(cu) != 1:
        raise ValueError(f"03B số tiền: đoạn SQL gốc không duy nhất: {cu[:80]}")
    return sql.replace(cu, moi)


_LUU = _doi(_ham("kho.dc_luu"), "            tp := (SELECT", "            PERFORM kho._dc_kiem_tien_tp(p_yc->'thanh_phan');\n            tp := (SELECT")
_LUU = _doi(_LUU, "phan, ty_le_khai, ty_le_trang_thai)", "phan, ty_le_khai, ty_le_trang_thai, so_tien_khai, tien_te)")
_LUU = _doi(_LUU,
    """v_muc->>'phan', v_muc->>'ty_le_khai', CASE WHEN v_muc->>'phan' = 'TOAN_PHAN' THEN 'KHONG_AP_DUNG'
                                                                     WHEN v_muc->>'ty_le_khai' IS NULL THEN 'THIEU' ELSE 'KHAI_BAO_THO_CHUA_SCALE' END)""",
    """v_muc->>'phan', NULL, CASE WHEN v_muc->>'phan' = 'TOAN_PHAN' THEN 'KHONG_AP_DUNG'
                            WHEN v_muc->>'so_tien_khai' IS NULL OR v_muc->>'tien_te' IS NULL THEN 'THIEU' ELSE 'KHAI_SO_TIEN' END,
                            (v_muc->>'so_tien_khai')::numeric, v_muc->>'tien_te')""")

_XAC_NHAN = _doi(_ham("kho.dc_xac_nhan"), "phan, ty_le_khai, ty_le_trang_thai)", "phan, ty_le_khai, ty_le_trang_thai, so_tien_khai, tien_te)")
_XAC_NHAN = _doi(_XAC_NHAN, "m.phan, m.ty_le_khai, m.ty_le_trang_thai\n", "m.phan, m.ty_le_khai, m.ty_le_trang_thai, m.so_tien_khai, m.tien_te\n")

_HOAN_TAT = _doi(_ham("kho._dc_phien_ban_hoan_tat"),
    "AND m.phan = t->>'phan' AND m.ty_le_khai IS NOT DISTINCT FROM (t->>'ty_le_khai'))",
    """AND m.phan = t->>'phan' AND m.ty_le_khai IS NOT DISTINCT FROM (t->>'ty_le_khai')
                  AND m.so_tien_khai IS NOT DISTINCT FROM (t->>'so_tien_khai')::numeric
                  AND m.tien_te IS NOT DISTINCT FROM (t->>'tien_te'))""")
_THIEU = _doi(_ham("kho._dc_thieu"), "t->>'phan' = 'MOT_PHAN' AND t->>'ty_le_khai' IS NULL",
    "t->>'phan' = 'MOT_PHAN' AND t->>'ty_le_khai' IS NULL AND (t->>'so_tien_khai' IS NULL OR t->>'tien_te' IS NULL)")

M4_03B_SO_TIEN_SQL = (
    "SET LOCAL check_function_bodies = off",
    """ALTER TABLE kho.mua_doi_chieu_can_cu_thanh_phan
        ADD COLUMN so_tien_khai numeric,
        ADD COLUMN tien_te text CHECK (tien_te IN ('VND','USD'))""",
    # Hai CHECK cũ chứa cột trạng thái (tên do PG cấp); giữ CHECK tỷ lệ thô và mọi FK cũ.
    """DO $$ DECLARE dc_ck record;
        BEGIN
            FOR dc_ck IN SELECT c.conname FROM pg_constraint c
                WHERE c.conrelid = 'kho.mua_doi_chieu_can_cu_thanh_phan'::regclass AND c.contype = 'c'
                  AND (SELECT a.attnum FROM pg_attribute a WHERE a.attrelid = c.conrelid AND a.attname = 'ty_le_trang_thai') = ANY(c.conkey)
            LOOP
                EXECUTE format('ALTER TABLE kho.mua_doi_chieu_can_cu_thanh_phan DROP CONSTRAINT %I', dc_ck.conname);
            END LOOP;
        END $$""",
    """ALTER TABLE kho.mua_doi_chieu_can_cu_thanh_phan
        ADD CONSTRAINT dc_so_tien_mien CHECK (so_tien_khai IS NULL OR
            (so_tien_khai > 0 AND so_tien_khai < 1000000000000000000
             AND so_tien_khai::text ~ '^[0-9]+([.][0-9]{1,2})?$'
             AND (tien_te IS DISTINCT FROM 'VND' OR scale(so_tien_khai) = 0))),
        ADD CONSTRAINT dc_phan_khai_trang_thai CHECK (
            (phan = 'TOAN_PHAN' AND ty_le_khai IS NULL AND so_tien_khai IS NULL AND tien_te IS NULL AND ty_le_trang_thai = 'KHONG_AP_DUNG')
            OR (phan = 'MOT_PHAN' AND (
                (ty_le_khai IS NOT NULL AND so_tien_khai IS NULL AND tien_te IS NULL AND ty_le_trang_thai = 'KHAI_BAO_THO_CHUA_SCALE')
                OR (ty_le_khai IS NULL AND (so_tien_khai IS NULL OR tien_te IS NULL) AND ty_le_trang_thai = 'THIEU')
                OR (ty_le_khai IS NULL AND so_tien_khai IS NOT NULL AND tien_te IS NOT NULL AND ty_le_trang_thai = 'KHAI_SO_TIEN'))))""",
    """CREATE OR REPLACE FUNCTION kho._dc_so_tien_hop_le(p_so text, p_tt text) RETURNS boolean
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT CASE WHEN p_so IS NULL OR p_so !~ '^(0|[1-9][0-9]{0,17})([.][0-9]{1,2})?$'
                     OR (p_tt IS NOT NULL AND p_tt NOT IN ('VND','USD'))
                     OR (p_tt = 'VND' AND position('.' IN p_so) > 0) THEN false
                    ELSE p_so::numeric > 0 AND p_so::numeric < 1000000000000000000 END
        $$""",
    """CREATE OR REPLACE FUNCTION kho._dc_kiem_tien_tp(p_tp jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = kho, pg_temp AS $$
        DECLARE dc_tp jsonb;
        BEGIN
            FOR dc_tp IN SELECT value FROM jsonb_array_elements(p_tp) LOOP
                IF jsonb_typeof(dc_tp) IS DISTINCT FROM 'object' THEN
                    RAISE EXCEPTION 'DC_PHAN_SAI: thành phần phải là object' USING ERRCODE = 'P0001';
                END IF;
                IF dc_tp ? 'ty_le_khai' AND (dc_tp->>'ty_le_khai' IS NOT NULL OR dc_tp->>'phan' = 'MOT_PHAN') THEN
                    RAISE EXCEPTION 'DC_PHAN_SAI: ty_le_khai không nhận cho bản mới; dùng so_tien_khai và tien_te' USING ERRCODE = 'P0001';
                END IF;
                IF dc_tp->>'phan' IS NULL OR dc_tp->>'phan' NOT IN ('TOAN_PHAN','MOT_PHAN')
                   OR (dc_tp->>'tien_te' IS NOT NULL AND dc_tp->>'tien_te' NOT IN ('VND','USD')) THEN
                    RAISE EXCEPTION 'DC_PHAN_SAI: phan/tien_te không hợp lệ' USING ERRCODE = 'P0001';
                END IF;
                IF dc_tp->>'so_tien_khai' IS NOT NULL AND
                   (jsonb_typeof(dc_tp->'so_tien_khai') IS DISTINCT FROM 'string'
                    OR NOT kho._dc_so_tien_hop_le(dc_tp->>'so_tien_khai', dc_tp->>'tien_te')) THEN
                    RAISE EXCEPTION 'DC_PHAN_SAI: so_tien_khai phải là chuỗi số ASCII dương, dưới 10^18; VND nguyên, USD tối đa 2 số lẻ' USING ERRCODE = 'P0001';
                END IF;
                IF dc_tp->>'phan' = 'TOAN_PHAN' AND (dc_tp->>'so_tien_khai' IS NOT NULL OR dc_tp->>'tien_te' IS NOT NULL) THEN
                    RAISE EXCEPTION 'DC_PHAN_SAI: TOAN_PHAN không kèm so_tien_khai/tien_te' USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
        END $$""",
    _LUU, _XAC_NHAN, _HOAN_TAT, _THIEU,
    # Chỉ đọc trên kết nối chủ bảng của service; quyền KT kiểm trước trả ngữ cảnh đợt.
    """CREATE OR REPLACE FUNCTION kho._dc_dot_goi_y(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE dc_cho m4.duyet_kt_cho%ROWTYPE; dc_kq jsonb;
        BEGIN
            SELECT * INTO dc_cho FROM m4.duyet_kt_cho c WHERE c.dot_id = p_dot;
            PERFORM m4.kt_kiem(dc_cho.id, 'XEM');
            SELECT jsonb_build_object('dot_id', d.id, 'cho_id', dc_cho.id, 'phap_nhan_id', dc_cho.phap_nhan_id,
                'doi_tac_mst', nullif(btrim(t.mst), ''), 'ngay_nghiem_thu', d.ngay_nghiem_thu,
                'gia_tri', k.gia_tri_nt_xac_nhan, 'tien_te', k.tien_te) INTO dc_kq
              FROM m4.dot d JOIN master.hop_dong h ON h.id = d.hop_dong_id
              LEFT JOIN master.doi_tac t ON t.id = h.doi_tac_id
              LEFT JOIN LATERAL (SELECT b.id FROM m4.duyet_kt_phong_bi b WHERE b.cho_id = dc_cho.id ORDER BY b.thu_tu DESC LIMIT 1) pb ON true
              LEFT JOIN m4.kt_xac_nhan k ON k.phong_bi_id = pb.id AND k.loai = 'XAC_NHAN'
              WHERE d.id = p_dot;
            RETURN dc_kq;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho._dc_goi_y_hoa_don(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, kho, m4, pg_temp AS $$
        DECLARE dc_dot jsonb; dc_ds jsonb;
        BEGIN
            dc_dot := kho._dc_dot_goi_y(p_dot);
            IF NOT coalesce(kho._dc_m2_doc((dc_dot->>'phap_nhan_id')::uuid), false) THEN
                RETURN jsonb_build_object('khong_quyen', true, 'hoa_don', '[]'::jsonb);
            END IF;
            SELECT coalesce(jsonb_agg(jsonb_build_object(
                'nguon', jsonb_build_object('kind','HOA_DON','occurrence_id',d.id,'source_version_id',v.id,'part_id',NULL),
                'phap_nhan_id',d.phap_nhan_id,'mst_ban',d.mst_ban,'mau_so',d.mau_so,'ky_hieu',d.ky_hieu,'so_chuan',d.so_chuan,
                'ngay_lap',v.ngay_lap,'tien_te',v.tien_te,'raw_header_states',v.raw_header_states,
                'da_gan_o', (SELECT coalesce(jsonb_agg(jsonb_build_object('doi_chieu_id',CASE WHEN z.doc_duoc THEN z.doi_chieu_id END,
                    'nhan',CASE WHEN z.doc_duoc THEN 'đã gắn ở ' || z.doi_chieu_id::text ELSE 'đã gắn ở đối chiếu ngoài phạm vi' END)
                    ORDER BY z.doi_chieu_id), '[]'::jsonb)
                    FROM (SELECT DISTINCT p.doi_chieu_id,
                          kho._dc_doc_duoc((SELECT jsonb_agg(tp2->'nguon')
                              FROM kho.mua_doi_chieu_can_cu_phien_ban allp, jsonb_array_elements(allp.noi_dung->'thanh_phan') tp2
                              WHERE allp.doi_chieu_id = p.doi_chieu_id)) AS doc_duoc
                        FROM kho.mua_doi_chieu_can_cu_phien_ban p
                        JOIN kho.mua_doi_chieu_can_cu_thanh_phan m ON m.phien_ban_id = p.id
                        JOIN kho.mua_nguon_kinh_te n ON n.id = m.nguon_id
                        WHERE n.hoa_don_id = d.id
                          AND NOT EXISTS (SELECT 1 FROM kho.mua_doi_chieu_can_cu_phien_ban p2 WHERE p2.doi_chieu_id = p.doi_chieu_id AND p2.revision > p.revision)
                          AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p.noi_dung->'thanh_phan') tp
                              WHERE tp->'nguon'->>'kind' = 'NT' AND tp->'nguon'->>'occurrence_id' = dc_dot->>'cho_id')) z)
                ) ORDER BY d.id), '[]'::jsonb) INTO dc_ds
              FROM kho.hoa_don_danh_tinh d
              JOIN kho.hoa_don_quan_sat o ON o.id = d.latest_observation_id
              JOIN kho.hoa_don_phien_ban v ON v.id = o.phien_ban_id
              WHERE d.phap_nhan_id = (dc_dot->>'phap_nhan_id')::uuid AND d.mst_ban = dc_dot->>'doi_tac_mst' AND d.chieu = 'MUA_VAO';
            RETURN jsonb_build_object('khong_quyen', false, 'dot', dc_dot, 'hoa_don', dc_ds);
        END $$""",
    "REVOKE EXECUTE ON FUNCTION kho._dc_so_tien_hop_le(text,text), kho._dc_kiem_tien_tp(jsonb), kho._dc_dot_goi_y(uuid), kho._dc_goi_y_hoa_don(uuid) FROM PUBLIC",
)
