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


# BO-1b: các cặp thay SQL, áp dụng lên writer cuối trong registry (M0055),
# cùng cách _m36_thay/_m37_ham của MTQ-4f1b; không dựng lại guard/receipt.
M4_BOQ_BO_B_SQL = (
    ("b uuid; n integer; goc text[]; tt text;",
     """b uuid; n integer; goc text[]; tt text;
        tuong_minh boolean; so_co integer; dong_lon_nhat integer; nguon_bo jsonb := '{}'::jsonb;
        su_kien record; hien_tai jsonb;"""),
    ("            n := jsonb_array_length(p_dong);",
     """            n := jsonb_array_length(p_dong);
            SELECT count(*) FILTER (WHERE e.value ? 'thao_tac') INTO so_co
            FROM jsonb_array_elements(p_dong) e;
            tuong_minh := so_co > 0;
            IF tuong_minh AND so_co <> n THEN
                RAISE EXCEPTION 'M4_BOQ_LAN_THAO_TAC: mọi dòng phải cùng có hoặc cùng không có thao tác.' USING ERRCODE = 'P0001';
            END IF;
            IF tuong_minh AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(p_dong) e
                WHERE jsonb_typeof(e.value) IS DISTINCT FROM 'object'
                   OR jsonb_typeof(e.value->'thao_tac') IS DISTINCT FROM 'string'
                   OR (e.value->>'thao_tac') NOT IN ('GOC','THEM','THAY','BO')
                   OR (p_pl IS NULL AND e.value->>'thao_tac' <> 'GOC')
                   OR (p_pl IS NOT NULL AND e.value->>'thao_tac' = 'GOC')) THEN
                RAISE EXCEPTION 'M4_BOQ_THAO_TAC_SAI: BOQ gốc chỉ nhận hạng mục gốc; phụ lục nhận thêm hạng mục, thay hạng mục hoặc bỏ hạng mục.' USING ERRCODE = 'P0001';
            END IF;
            IF tuong_minh AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(p_dong) e
                WHERE e.value->>'thao_tac' = 'BO'
                  AND (jsonb_typeof(e.value->'ma_hm') IS DISTINCT FROM 'string'
                       OR coalesce(length(btrim(e.value->>'ma_hm')), 0) NOT BETWEEN 1 AND 500)) THEN
                RAISE EXCEPTION 'M4_BOQ_BO_THIEU_MA: bỏ hạng mục cần mã hạng mục hợp lệ.' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (
                SELECT 1 FROM jsonb_to_recordset(p_dong) AS x(dong integer)
                WHERE x.dong IS NOT NULL GROUP BY x.dong HAVING count(*) > 1) THEN
                RAISE EXCEPTION 'M4_BOQ_TRUNG_DONG: số dòng gửi tường minh bị trùng trong cùng lần ghi.' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(max(x.dong), 0) INTO dong_lon_nhat
            FROM jsonb_to_recordset(p_dong) AS x(dong integer);
            -- Dòng thiếu số nối sau số lớn nhất, theo thứ tự gửi; giữ số tường minh.
            SELECT coalesce(jsonb_agg(
                CASE WHEN e.dong IS NULL THEN e.value || jsonb_build_object(
                    'dong', dong_lon_nhat + e.so_thieu::integer) ELSE e.value END
                ORDER BY e.vi_tri), '[]'::jsonb) INTO p_dong
            FROM (
                SELECT a.value, a.vi_tri, x.dong,
                       count(*) FILTER (WHERE x.dong IS NULL) OVER (ORDER BY a.vi_tri) AS so_thieu
                FROM jsonb_array_elements(p_dong) WITH ORDINALITY AS a(value, vi_tri)
                CROSS JOIN LATERAL jsonb_to_record(a.value) AS x(dong integer)
            ) e;
            IF tuong_minh AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(p_dong) e WHERE e.value->>'thao_tac' = 'BO') THEN
                -- Chỉ projection các mã cần bỏ, trước PL này; cùng ngày theo lan.
                -- Loại toàn bộ PL đích và PL tương lai, kể cả khi đã nhập trước.
                FOR su_kien IN
                    WITH goc AS (
                        SELECT id FROM m4.boq WHERE hop_dong_id = p_hd
                          AND phu_luc_id IS NULL AND trang_thai = 'DA_MAP'
                        ORDER BY lan DESC LIMIT 1
                    )
                    SELECT d.ma_hm, d.thao_tac, d.ten, d.dvt
                    FROM m4.boq b0 JOIN m4.boq_dong d ON d.boq_id = b0.id
                    LEFT JOIN m4.phu_luc pl ON pl.id = b0.phu_luc_id AND pl.hop_dong_id = p_hd
                    WHERE b0.hop_dong_id = p_hd AND b0.trang_thai = 'DA_MAP'
                      AND (b0.id IN (SELECT id FROM goc)
                           OR (pl.id <> p_pl AND pl.trang_thai = 'DA_KY'
                               AND pl.ngay_hieu_luc <= (SELECT ngay_hieu_luc FROM m4.phu_luc WHERE id = p_pl)))
                      AND d.ma_hm IN (SELECT e.value->>'ma_hm' FROM jsonb_array_elements(p_dong) e
                                      WHERE e.value->>'thao_tac' = 'BO')
                    ORDER BY CASE WHEN b0.phu_luc_id IS NULL THEN '-infinity'::date
                                  ELSE pl.ngay_hieu_luc END, b0.lan, d.dong
                LOOP
                    hien_tai := nguon_bo -> su_kien.ma_hm;
                    IF su_kien.thao_tac IN ('GOC','THEM') AND hien_tai IS NULL THEN
                        nguon_bo := nguon_bo || jsonb_build_object(su_kien.ma_hm,
                            jsonb_build_object('ten', su_kien.ten, 'dvt', su_kien.dvt));
                    ELSIF su_kien.thao_tac = 'THAY' AND hien_tai IS NOT NULL THEN
                        nguon_bo := nguon_bo || jsonb_build_object(su_kien.ma_hm,
                            jsonb_build_object('ten', coalesce(nullif(su_kien.ten, ''), hien_tai->>'ten'),
                                               'dvt', coalesce(nullif(su_kien.dvt, ''), hien_tai->>'dvt')));
                    ELSIF su_kien.thao_tac = 'BO' THEN
                        nguon_bo := nguon_bo - su_kien.ma_hm;
                    END IF;
                END LOOP;
                IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_dong) e
                           WHERE e.value->>'thao_tac' = 'BO' AND NOT (nguon_bo ? (e.value->>'ma_hm'))) THEN
                    RAISE EXCEPTION 'M4_BOQ_BO_KHONG_HIEU_LUC: bỏ hạng mục cần mã có dòng hiệu lực trước phụ lục này.' USING ERRCODE = 'P0001';
                END IF;
            END IF;"""),
    ("            INSERT INTO m4.boq_dong (boq_id, du_an_id, dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng, o_goc)",
     """            IF tuong_minh THEN
                INSERT INTO m4.boq_dong (boq_id, du_an_id, dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng, o_goc)
                    SELECT b, h.du_an_id,
                           x.dong,
                           x.ma_hm, x.thao_tac, x.stt, x.nhom,
                           CASE WHEN x.thao_tac = 'BO' THEN coalesce(nullif(x.ten, ''), nguon_bo->x.ma_hm->>'ten') ELSE x.ten END,
                           CASE WHEN x.thao_tac = 'BO' THEN coalesce(nullif(x.dvt, ''), nguon_bo->x.ma_hm->>'dvt') ELSE x.dvt END,
                           x.kl, x.don_gia, x.thanh_tien, x.ma_rieng,
                           CASE WHEN x.thao_tac = 'BO' THEN coalesce(x.o_goc, '{}'::jsonb) ELSE x.o_goc END
                    FROM jsonb_array_elements(p_dong) WITH ORDINALITY AS e(value, vi_tri)
                    CROSS JOIN LATERAL jsonb_to_record(e.value) AS x(dong integer, ma_hm text, thao_tac text,
                        stt text, nhom text, ten text, dvt text, kl text, don_gia text, thanh_tien text, ma_rieng text, o_goc jsonb);
            ELSE
            INSERT INTO m4.boq_dong (boq_id, du_an_id, dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng, o_goc)"""),
    ("                                                     thanh_tien text, ma_rieng text, o_goc jsonb);",
     "                                                     thanh_tien text, ma_rieng text, o_goc jsonb);\n            END IF;"),
)
