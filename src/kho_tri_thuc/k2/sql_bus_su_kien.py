"""XS-1a / CD-017: bus PostgreSQL, tên tiếng Việt không dấu, snake_case.

Schema ``bus``: ``su_kien`` là outbox bất biến; ``inbox`` giữ CHO/DA_ACK
riêng theo (pháp nhân, bên nhận, sự kiện). Bên phát/nhận là mã module được
``master.ktt_duoc`` cho phép. Không thay các hàm danh tính/phân quyền cũ.

API SQL: phat(pn, ben_phat, loai, phien_ban, khoa_dedupe, payload) -> uuid;
nhan(pn, ben_nhan, loai=NULL, gioi_han=100) -> SETOF bus.su_kien;
ack(pn, ben_nhan, su_kien_id) -> boolean (true khi ACK đầu, false khi lặp).
Payload v1 là object không rỗng: tên *_id -> UUID, *_ids -> mảng UUID;
không nhận nội dung chứng từ, JSON lồng, đường dẫn hay văn bản tự do.
Hash SHA-256 của jsonb chuẩn hóa đi cùng phiên bản hợp đồng sự kiện.

Gọi phat trên CHÍNH kết nối/giao dịch nghiệp vụ; không commit trong hàm.
Nhận giữ khóa inbox tới cuối giao dịch. Bên nhận ghi kết quả và ACK trong
cùng giao dịch PG; rollback khôi phục cả hai. CHO được giao lại, DA_ACK
không giao lại cho cùng bên nhận; đây là giao ít nhất một lần, không hứa
exactly-once cho tác động ngoài PG. Chưa có subscription/lease/worker.
"""

BUS_SU_KIEN_SQL = (
    "CREATE SCHEMA bus",
    "REVOKE ALL ON SCHEMA bus FROM PUBLIC",
    """CREATE FUNCTION bus.payload_hop_le(p_payload jsonb) RETURNS boolean
        LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        DECLARE k text; v jsonb; item jsonb;
        BEGIN
            IF jsonb_typeof(p_payload) IS DISTINCT FROM 'object' OR p_payload = '{}'::jsonb THEN
                RETURN false;
            END IF;
            FOR k, v IN SELECT key, value FROM jsonb_each(p_payload) LOOP
                IF k ~ '^[a-z][a-z0-9_]*_id$' AND jsonb_typeof(v) = 'string' THEN
                    IF (v #>> '{}') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                        RETURN false;
                    END IF;
                ELSIF k ~ '^[a-z][a-z0-9_]*_ids$' AND jsonb_typeof(v) = 'array' THEN
                    FOR item IN SELECT value FROM jsonb_array_elements(v) LOOP
                        IF jsonb_typeof(item) <> 'string' OR
                            (item #>> '{}') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                            RETURN false;
                        END IF;
                    END LOOP;
                ELSE
                    RETURN false;
                END IF;
            END LOOP;
            RETURN true;
        END $$""",
    """CREATE TABLE bus.su_kien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ben_phat text NOT NULL CHECK (length(btrim(ben_phat)) > 0),
        loai_su_kien text NOT NULL CHECK (length(btrim(loai_su_kien)) > 0),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        khoa_dedupe text NOT NULL CHECK (length(btrim(khoa_dedupe)) > 0),
        payload jsonb NOT NULL CHECK (bus.payload_hop_le(payload)),
        payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
        trang_thai text NOT NULL DEFAULT 'DA_PHAT' CHECK (trang_thai = 'DA_PHAT'),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        tao_boi text NOT NULL,
        UNIQUE (phap_nhan_id, ben_phat, khoa_dedupe),
        UNIQUE (phap_nhan_id, id))""",
    "CREATE INDEX su_kien_doc ON bus.su_kien (phap_nhan_id, tao_luc, id)",
    """CREATE TABLE bus.inbox (
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ben_nhan text NOT NULL CHECK (length(btrim(ben_nhan)) > 0),
        su_kien_id uuid NOT NULL,
        trang_thai text NOT NULL DEFAULT 'CHO' CHECK (trang_thai IN ('CHO','DA_ACK')),
        nhan_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ack_luc timestamptz,
        ack_boi text,
        PRIMARY KEY (phap_nhan_id, ben_nhan, su_kien_id),
        FOREIGN KEY (phap_nhan_id, su_kien_id) REFERENCES bus.su_kien(phap_nhan_id, id),
        CHECK ((trang_thai = 'CHO' AND ack_luc IS NULL AND ack_boi IS NULL) OR
               (trang_thai = 'DA_ACK' AND ack_luc IS NOT NULL AND ack_boi IS NOT NULL)))""",
    "ALTER TABLE bus.su_kien ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE bus.inbox ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY su_kien_phap_nhan ON bus.su_kien
        USING (phap_nhan_id IN (SELECT master.ktt_pn_cho_phep()))
        WITH CHECK (phap_nhan_id IN (SELECT master.ktt_pn_cho_phep()))""",
    """CREATE POLICY inbox_phap_nhan ON bus.inbox
        USING (phap_nhan_id IN (SELECT master.ktt_pn_cho_phep()) AND master.ktt_duoc(phap_nhan_id, ben_nhan))
        WITH CHECK (phap_nhan_id IN (SELECT master.ktt_pn_cho_phep()) AND master.ktt_duoc(phap_nhan_id, ben_nhan))""",
    """CREATE FUNCTION bus.phat(p_pn uuid, p_ben_phat text, p_loai text,
        p_phien_ban integer, p_khoa_dedupe text, p_payload jsonb) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, bus, master, pg_temp AS $$
        DECLARE sk bus.su_kien; moi uuid;
        BEGIN
            -- Chủ hàm có thể bỏ qua RLS: luôn kiểm phiên tường minh trước khi đọc/ghi.
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn)
                OR NOT master.ktt_duoc(p_pn, p_ben_phat) THEN
                RAISE EXCEPTION 'BUS_PHAM_VI: phiên không có quyền phát trong pháp nhân/module' USING ERRCODE = '42501';
            END IF;
            IF p_loai IS NULL OR length(btrim(p_loai)) = 0 OR
                p_phien_ban IS NULL OR p_phien_ban < 1 OR
                p_khoa_dedupe IS NULL OR length(btrim(p_khoa_dedupe)) = 0 OR
                NOT bus.payload_hop_le(p_payload) THEN
                RAISE EXCEPTION 'BUS_DAU_VAO: cần loại, phiên bản, khóa dedupe và tham chiếu UUID' USING ERRCODE = '22023';
            END IF;
            INSERT INTO bus.su_kien (phap_nhan_id, ben_phat, loai_su_kien, phien_ban,
                    khoa_dedupe, payload, payload_sha256, tao_boi)
                VALUES (p_pn, p_ben_phat, p_loai, p_phien_ban, p_khoa_dedupe, p_payload,
                    encode(public.digest(p_payload::text, 'sha256'), 'hex'), master.ktt_danh_tinh())
                ON CONFLICT (phap_nhan_id, ben_phat, khoa_dedupe) DO NOTHING RETURNING id INTO moi;
            IF moi IS NOT NULL THEN RETURN moi; END IF;
            SELECT * INTO sk FROM bus.su_kien
                WHERE phap_nhan_id = p_pn AND ben_phat = p_ben_phat AND khoa_dedupe = p_khoa_dedupe;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'BUS_THU_LAI: cần thử lại toàn giao dịch' USING ERRCODE = '40001';
            END IF;
            IF sk.loai_su_kien IS DISTINCT FROM p_loai OR sk.phien_ban IS DISTINCT FROM p_phien_ban
                OR sk.payload IS DISTINCT FROM p_payload THEN
                RAISE EXCEPTION 'BUS_DEDUPE_XUNG_DOT: cùng khóa nhưng khác hợp đồng/nội dung' USING ERRCODE = '23505';
            END IF;
            RETURN sk.id;
        END $$""",
    """CREATE FUNCTION bus.nhan(p_pn uuid, p_ben_nhan text,
        p_loai text DEFAULT NULL, p_gioi_han integer DEFAULT 100) RETURNS SETOF bus.su_kien
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, bus, master, pg_temp AS $$
        DECLARE sk bus.su_kien;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn)
                OR NOT master.ktt_duoc(p_pn, p_ben_nhan) THEN
                RAISE EXCEPTION 'BUS_PHAM_VI: phiên không có quyền nhận trong pháp nhân/module' USING ERRCODE = '42501';
            END IF;
            IF p_gioi_han IS NULL OR p_gioi_han < 1 OR p_gioi_han > 1000 THEN
                RAISE EXCEPTION 'BUS_GIOI_HAN: số sự kiện phải từ 1 tới 1000' USING ERRCODE = '22023';
            END IF;
            FOR sk IN SELECT s.* FROM bus.su_kien s
                WHERE s.phap_nhan_id = p_pn AND (p_loai IS NULL OR s.loai_su_kien = p_loai)
                    AND NOT EXISTS (SELECT 1 FROM bus.inbox i WHERE i.phap_nhan_id = p_pn
                        AND i.ben_nhan = p_ben_nhan AND i.su_kien_id = s.id AND i.trang_thai = 'DA_ACK')
                ORDER BY s.tao_luc, s.id LIMIT p_gioi_han
            LOOP
                INSERT INTO bus.inbox (phap_nhan_id, ben_nhan, su_kien_id)
                    VALUES (p_pn, p_ben_nhan, sk.id) ON CONFLICT DO NOTHING;
                -- Khóa cùng inbox, kiểm lại sau khi chờ giao dịch nhận khác hoàn tất.
                PERFORM 1 FROM bus.inbox i WHERE i.phap_nhan_id = p_pn
                    AND i.ben_nhan = p_ben_nhan AND i.su_kien_id = sk.id AND i.trang_thai = 'CHO' FOR UPDATE;
                IF FOUND THEN RETURN NEXT sk; END IF;
            END LOOP;
            RETURN;
        END $$""",
    """CREATE FUNCTION bus.ack(p_pn uuid, p_ben_nhan text, p_su_kien uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, bus, master, pg_temp AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn)
                OR NOT master.ktt_duoc(p_pn, p_ben_nhan) THEN
                RAISE EXCEPTION 'BUS_PHAM_VI: phiên không có quyền ACK trong pháp nhân/module' USING ERRCODE = '42501';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM bus.inbox i WHERE i.phap_nhan_id = p_pn
                AND i.ben_nhan = p_ben_nhan AND i.su_kien_id = p_su_kien) THEN
                RAISE EXCEPTION 'BUS_CHUA_NHAN: không có sự kiện đã nhận trong pháp nhân này' USING ERRCODE = '42501';
            END IF;
            UPDATE bus.inbox SET trang_thai = 'DA_ACK', ack_luc = clock_timestamp(), ack_boi = master.ktt_danh_tinh()
                WHERE phap_nhan_id = p_pn AND ben_nhan = p_ben_nhan AND su_kien_id = p_su_kien AND trang_thai = 'CHO';
            RETURN FOUND;
        END $$""",
    "REVOKE ALL ON ALL TABLES IN SCHEMA bus FROM PUBLIC",
    "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA bus FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA bus TO app_web;
            REVOKE ALL ON ALL TABLES IN SCHEMA bus FROM app_web;
            GRANT SELECT ON bus.su_kien, bus.inbox TO app_web;
            GRANT EXECUTE ON FUNCTION bus.phat(uuid,text,text,integer,text,jsonb),
                bus.nhan(uuid,text,text,integer), bus.ack(uuid,text,uuid) TO app_web;
        END IF;
    END $$""",
)
