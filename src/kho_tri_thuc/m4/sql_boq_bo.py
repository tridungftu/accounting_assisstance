"""BO-1a — QD-09: sự kiện bỏ dòng và BOQ hiệu lực, không sửa lịch sử.

BO được kiểm lúc đọc, kể cả sau khi hủy phụ lục trước nó: báo lỗi thay vì
âm thầm bỏ mã không còn tồn tại. Không thêm trigger lên dữ liệu cũ.
BOQ gốc là lần DA_MAP mới nhất không gắn phụ lục, cùng quy ước writer M17.
"""

# Dùng chung cho kiểm BO và projection; mọi SELECT chạy dưới RLS của caller.
_SU_KIEN = """WITH goc AS (
    SELECT b.id, b.lan, b.phu_luc_id
    FROM m4.boq b
    WHERE b.hop_dong_id = p_hop_dong_id AND b.phu_luc_id IS NULL
      AND b.trang_thai = 'DA_MAP'
    ORDER BY b.lan DESC LIMIT 1
), lan_doc AS (
    SELECT g.id, g.lan, g.phu_luc_id, '-infinity'::date AS ngay_hieu_luc
    FROM goc g
    UNION ALL
    SELECT b.id, b.lan, b.phu_luc_id, p.ngay_hieu_luc
    FROM m4.boq b JOIN m4.phu_luc p
      ON p.id = b.phu_luc_id AND p.hop_dong_id = b.hop_dong_id
    WHERE b.hop_dong_id = p_hop_dong_id AND b.trang_thai = 'DA_MAP'
      AND p.trang_thai = 'DA_KY' AND p.ngay_hieu_luc <= p_ngay
      AND EXISTS (SELECT 1 FROM goc)
), su_kien AS (
    SELECT d.*, l.lan, l.phu_luc_id, l.ngay_hieu_luc,
           row_number() OVER (ORDER BY l.ngay_hieu_luc, l.lan, d.dong) AS vi_tri
    FROM lan_doc l JOIN m4.boq_dong d ON d.boq_id = l.id
) """

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
    RETURNS TABLE (
        boq_id uuid, dong integer, phu_luc_id uuid, lan integer,
        ma_hm text, thao_tac text, stt text, nhom text, ten text, dvt text,
        kl text, don_gia text, thanh_tien text, ma_rieng text, o_goc jsonb
    )
    LANGUAGE plpgsql STABLE SECURITY INVOKER
    SET search_path = pg_catalog, m4, pg_temp AS $$
    DECLARE sai record;
    BEGIN
        IF p_ngay IS NULL THEN
            RAISE EXCEPTION 'M4_BOQ_NGAY_THIEU: cần ngày đọc BOQ' USING ERRCODE = 'P0001';
        END IF;
        """ + _SU_KIEN + """
        SELECT s.boq_id, s.dong, s.ma_hm INTO sai
        FROM su_kien s
        WHERE s.thao_tac = 'BO' AND (
            s.phu_luc_id IS NULL OR NOT coalesce((
                SELECT t.thao_tac <> 'BO'
                FROM su_kien t
                WHERE t.ma_hm = s.ma_hm
                  AND t.phu_luc_id IS DISTINCT FROM s.phu_luc_id
                  AND (t.ngay_hieu_luc, t.lan) < (s.ngay_hieu_luc, s.lan)
                ORDER BY t.vi_tri DESC LIMIT 1
            ), false))
        ORDER BY s.vi_tri LIMIT 1;
        IF FOUND THEN
            RAISE EXCEPTION 'M4_BOQ_BO_KHONG_HOP_LE: BOQ %, dòng %, mã % phải có phụ lục và đang hiệu lực trước phụ lục',
                sai.boq_id, sai.dong, sai.ma_hm USING ERRCODE = 'P0001';
        END IF;

        RETURN QUERY
        """ + _SU_KIEN + """, cuoi AS (
            SELECT DISTINCT ON (s.ma_hm) s.*,
                   min(s.vi_tri) OVER (PARTITION BY s.ma_hm) AS vi_tri_dau
            FROM su_kien s ORDER BY s.ma_hm, s.vi_tri DESC
        )
        SELECT c.boq_id, c.dong, c.phu_luc_id, c.lan,
               c.ma_hm, c.thao_tac, c.stt, c.nhom, c.ten, c.dvt,
               c.kl, c.don_gia, c.thanh_tien, c.ma_rieng, c.o_goc
        FROM cuoi c WHERE c.thao_tac <> 'BO'
        ORDER BY c.vi_tri_dau, c.ma_hm;
    END $$""",
    "REVOKE ALL ON FUNCTION m4.boq_hieu_luc(uuid, date) FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION m4.boq_hieu_luc(uuid, date) TO app_web;
        END IF;
    END $$""",
)
