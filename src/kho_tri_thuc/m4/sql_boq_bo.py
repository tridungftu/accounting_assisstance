"""BO-1a — QD-09: sự kiện bỏ dòng và BOQ hiệu lực, không sửa lịch sử.

Projection cùng quy tắc Review: dữ liệu nguồn sai trả cờ cần xem lại,
không trả tập dòng dở và không thêm trigger lên dữ liệu cũ.
BOQ gốc là lần DA_MAP mới nhất không gắn phụ lục, cùng quy ước writer M17.
"""

M4_BOQ_BO_SQL = (
    # Chỉ thay CHECK đơn cột thao_tac; giữ nguyên tên tìm được từ catalog.
    """DO $$
    DECLARE ten name;
    BEGIN
        SELECT c.conname INTO STRICT ten
        FROM pg_catalog.pg_constraint c
        JOIN pg_catalog.pg_attribute a
          ON a.attrelid = c.conrelid AND a.attname = 'thao_tac'
        WHERE c.conrelid = 'm4.boq_dong'::regclass AND c.contype = 'c'
          AND c.conkey = ARRAY[a.attnum]::smallint[];
        EXECUTE format('ALTER TABLE m4.boq_dong DROP CONSTRAINT %I', ten);
        EXECUTE format('ALTER TABLE m4.boq_dong ADD CONSTRAINT %I '
                       'CHECK (thao_tac IN (''GOC'',''THEM'',''THAY'',''BO''))', ten);
    END $$""",
    """CREATE FUNCTION m4.boq_hieu_luc(p_hop_dong_id uuid, p_ngay date)
    RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY INVOKER
    SET search_path = pg_catalog, m4, pg_temp AS $$
    DECLARE
        ban record;
        dong_doc record;
        dong_moi jsonb;
        cac_dong jsonb := '{}'::jsonb;
        da_gap jsonb := '{}'::jsonb;
        thu_tu text[] := ARRAY[]::text[];
        ly_do text[] := ARRAY[]::text[];
        ket_qua jsonb := '[]'::jsonb;
        loi text;
    BEGIN
        IF p_ngay IS NULL THEN
            RETURN jsonb_build_object('boq', NULL, 'can_xem_lai', true,
                'ly_do', jsonb_build_array('Cần ngày đọc BOQ.'));
        END IF;

        -- Mọi SELECT chịu RLS của caller; LEFT JOIN giữ dấu thiếu nguồn.
        FOR ban IN
            WITH goc AS (
                SELECT b.id FROM m4.boq b
                WHERE b.hop_dong_id = p_hop_dong_id
                  AND b.phu_luc_id IS NULL AND b.trang_thai = 'DA_MAP'
                ORDER BY b.lan DESC LIMIT 1
            )
            SELECT b.id, b.lan, b.phu_luc_id, p.id AS nguon_id, p.so_pl
            FROM m4.boq b LEFT JOIN m4.phu_luc p
              ON p.id = b.phu_luc_id AND p.hop_dong_id = b.hop_dong_id
            WHERE b.hop_dong_id = p_hop_dong_id AND b.trang_thai = 'DA_MAP'
              AND (b.id IN (SELECT id FROM goc)
                   OR (b.phu_luc_id IS NOT NULL AND
                       (p.id IS NULL OR
                        (p.trang_thai = 'DA_KY' AND p.ngay_hieu_luc <= p_ngay))))
            ORDER BY CASE WHEN b.phu_luc_id IS NULL THEN '-infinity'::date
                          ELSE p.ngay_hieu_luc END, b.lan
        LOOP
            FOR dong_doc IN
                SELECT d.boq_id, d.dong, d.ma_hm, d.thao_tac, d.stt,
                       d.nhom, d.ten, d.dvt, d.kl, d.don_gia,
                       d.thanh_tien, d.ma_rieng, d.o_goc
                FROM m4.boq_dong d WHERE d.boq_id = ban.id ORDER BY d.dong
            LOOP
                loi := NULL;
                dong_moi := to_jsonb(dong_doc) || jsonb_build_object(
                    'phu_luc_id', ban.phu_luc_id, 'lan', ban.lan,
                    'nguon', coalesce(ban.so_pl, 'HĐ gốc'));
                IF ban.phu_luc_id IS NULL THEN
                    IF dong_doc.thao_tac <> 'GOC' OR cac_dong ? dong_doc.ma_hm THEN
                        loi := 'BOQ gốc trùng mã hoặc sai thao tác.';
                    ELSE
                        cac_dong := cac_dong || jsonb_build_object(dong_doc.ma_hm, dong_moi);
                        thu_tu := array_append(thu_tu, dong_doc.ma_hm);
                    END IF;
                ELSIF ban.nguon_id IS NULL THEN
                    loi := 'BOQ thiếu phụ lục nguồn.';
                ELSIF coalesce(da_gap -> ban.phu_luc_id::text, '{}'::jsonb) ? dong_doc.ma_hm THEN
                    loi := format('Phụ lục %s: trùng mã hạng mục.', ban.so_pl);
                ELSE
                    -- Ghi nhớ theo phụ lục, kể cả khi có nhiều lần BOQ của cùng PL.
                    da_gap := da_gap || jsonb_build_object(ban.phu_luc_id::text,
                        coalesce(da_gap -> ban.phu_luc_id::text, '{}'::jsonb)
                        || jsonb_build_object(dong_doc.ma_hm, true));
                    IF dong_doc.thao_tac = 'THEM' AND NOT (cac_dong ? dong_doc.ma_hm) THEN
                        cac_dong := cac_dong || jsonb_build_object(dong_doc.ma_hm, dong_moi);
                        thu_tu := array_append(thu_tu, dong_doc.ma_hm);
                    ELSIF dong_doc.thao_tac = 'THAY' AND cac_dong ? dong_doc.ma_hm THEN
                        -- Đúng allowlist _THAY của Review; tiền/khối lượng giữ text.
                        SELECT coalesce(jsonb_object_agg(e.key, e.value), '{}'::jsonb)
                        INTO dong_moi
                        FROM jsonb_each(dong_moi) e
                        WHERE e.key IN ('stt', 'nhom', 'ten', 'dvt', 'kl', 'don_gia', 'thanh_tien')
                          AND e.value NOT IN ('null'::jsonb, '\"\"'::jsonb);
                        dong_moi := (cac_dong -> dong_doc.ma_hm) || dong_moi
                            || jsonb_build_object('boq_id', ban.id, 'dong', dong_doc.dong,
                                'phu_luc_id', ban.phu_luc_id, 'lan', ban.lan,
                                'thao_tac', dong_doc.thao_tac, 'o_goc', dong_doc.o_goc,
                                'nguon', ban.so_pl);
                        cac_dong := cac_dong || jsonb_build_object(dong_doc.ma_hm, dong_moi);
                    ELSIF dong_doc.thao_tac = 'BO' AND cac_dong ? dong_doc.ma_hm THEN
                        cac_dong := cac_dong - dong_doc.ma_hm;
                        thu_tu := array_remove(thu_tu, dong_doc.ma_hm);
                    ELSE
                        loi := format('Phụ lục %s: thao tác BOQ không khớp hạng mục đang hiệu lực.',
                                      ban.so_pl);
                    END IF;
                END IF;
                IF loi IS NOT NULL AND NOT (loi = ANY(ly_do)) THEN
                    ly_do := array_append(ly_do, loi);
                END IF;
            END LOOP;
        END LOOP;
        IF cardinality(ly_do) > 0 THEN
            RETURN jsonb_build_object('boq', NULL, 'can_xem_lai', true, 'ly_do', to_jsonb(ly_do));
        END IF;
        SELECT coalesce(jsonb_agg(cac_dong -> t.ma_hm ORDER BY t.vi_tri), '[]'::jsonb)
        INTO ket_qua FROM unnest(thu_tu) WITH ORDINALITY AS t(ma_hm, vi_tri);
        RETURN jsonb_build_object('boq', ket_qua, 'can_xem_lai', false, 'ly_do', '[]'::jsonb);
    END $$""",
    "REVOKE ALL ON FUNCTION m4.boq_hieu_luc(uuid, date) FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION m4.boq_hieu_luc(uuid, date) TO app_web;
        END IF;
    END $$""",
)
