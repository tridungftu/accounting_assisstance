"""XS-2a / CD-017: một bảng ``viec.hang_viec`` chung, không chuyển queue cũ.

Chỉ giữ UUID tham chiếu; không lưu nội dung chứng từ, đường dẫn hay lỗi tự do.
``tao`` chạy trong giao dịch nghiệp vụ của caller, không tự commit. Dedupe theo
(pháp nhân, module, khóa), cùng khóa khác hợp đồng bị từ chối, kể cả việc đã đóng.
Loại việc + phiên bản là hợp đồng engine do bên tạo đăng ký, không tạo bảng riêng.

``nhan`` trả tối đa một việc, tăng số lần thử và cấp token UUID mới mỗi lượt.
Worker phải truyền worker ID + token, cùng danh tính phiên, khi gia hạn/tiến độ/
kết thúc/thử lại. Lease dùng clock_timestamp, không dùng thời điểm đầu transaction.
Module TẮT chặn tạo/nhận mới; worker đang giữ lease vẫn được kết thúc/dừng.
``thu_lai`` chỉ dùng khi worker biết chắc lần thử đã thất bại an toàn; tác động
ngoài chưa rõ phải kết thúc CHUA_RO. Hết lease có tác động ngoài luôn CHUA_RO.
Phục hồi/nhận giới hạn 100 việc hết lease mỗi lượt; caller poll tiếp nếu cần.

Hạn giữ khai báo bằng giu_ngay (NULL = chưa khai báo, phải giữ), tính từ
ket_thuc_luc của XONG/LOI/DA_DUNG. CHO/DANG_CHAY/CHUA_RO không có mốc dọn.
Chưa có quyền dọn: giữ ID/khóa dedupe, tham chiếu, FK và nhật ký kiểm toán;
chỉ có thể lưu trữ sau khi reader/replay/pin được đối soát ở lát sau. Không xóa.
"""

HANG_VIEC_SQL = (
    "CREATE SCHEMA viec",
    "REVOKE ALL ON SCHEMA viec FROM PUBLIC",
    """CREATE TABLE viec.hang_viec (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        module text NOT NULL REFERENCES master.module_danh_muc(ma),
        loai text NOT NULL CHECK (loai ~ '^[A-Z][A-Z0-9_-]{0,79}$'),
        phien_ban integer NOT NULL CHECK (phien_ban > 0),
        khoa_dedupe text NOT NULL CHECK (length(khoa_dedupe) BETWEEN 1 AND 200
            AND khoa_dedupe = btrim(khoa_dedupe)),
        tham_chieu_id uuid NOT NULL,
        co_tac_dong_ngoai boolean NOT NULL DEFAULT false,
        trang_thai text NOT NULL DEFAULT 'CHO'
            CHECK (trang_thai IN ('CHO','DANG_CHAY','XONG','LOI','DA_DUNG','CHUA_RO')),
        so_lan_thu integer NOT NULL DEFAULT 0,
        toi_da_lan_thu integer NOT NULL CHECK (toi_da_lan_thu BETWEEN 1 AND 100),
        thu_lai_giay integer NOT NULL CHECK (thu_lai_giay BETWEEN 1 AND 86400),
        thu_lai_sau timestamptz NOT NULL DEFAULT clock_timestamp(),
        lease_boi uuid,
        lease_danh_tinh text,
        lease_token uuid,
        lease_den timestamptz,
        tien_do integer NOT NULL DEFAULT 0 CHECK (tien_do BETWEEN 0 AND 100),
        yeu_cau_dung boolean NOT NULL DEFAULT false,
        ket_qua_id uuid,
        ma_loi text CHECK (ma_loi ~ '^[A-Z][A-Z0-9_]{0,79}$'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        ket_thuc_luc timestamptz,
        giu_ngay integer CHECK (giu_ngay BETWEEN 1 AND 36500),
        UNIQUE (phap_nhan_id, module, khoa_dedupe),
        CHECK (so_lan_thu BETWEEN 0 AND toi_da_lan_thu),
        CHECK ((trang_thai = 'DANG_CHAY' AND lease_boi IS NOT NULL
            AND lease_danh_tinh IS NOT NULL AND lease_token IS NOT NULL AND lease_den IS NOT NULL)
            OR (trang_thai <> 'DANG_CHAY' AND lease_boi IS NULL
            AND lease_danh_tinh IS NULL AND lease_token IS NULL AND lease_den IS NULL)),
        CHECK ((trang_thai IN ('XONG','LOI','DA_DUNG')) = (ket_thuc_luc IS NOT NULL)))""",
    """CREATE INDEX hang_viec_cho ON viec.hang_viec
        (phap_nhan_id, module, thu_lai_sau, tao_luc, id) WHERE trang_thai = 'CHO'""",
    """CREATE INDEX hang_viec_lease ON viec.hang_viec
        (phap_nhan_id, module, lease_den, id) WHERE trang_thai = 'DANG_CHAY'""",
    """CREATE INDEX hang_viec_han_giu ON viec.hang_viec (ket_thuc_luc)
        WHERE ket_thuc_luc IS NOT NULL AND giu_ngay IS NOT NULL""",
    "ALTER TABLE viec.hang_viec ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY hang_viec_pham_vi ON viec.hang_viec FOR SELECT
        USING (phap_nhan_id IN (SELECT master.ktt_pn_cho_phep())
            AND master.ktt_duoc(phap_nhan_id, module))""",
    """CREATE FUNCTION viec._kiem_quyen(p_pn uuid, p_module text) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn)
                OR NOT master.ktt_duoc(p_pn, p_module) THEN
                RAISE EXCEPTION 'VIEC_PHAM_VI: phiên không có quyền pháp nhân/module'
                    USING ERRCODE = '42501';
            END IF;
        END $$""",
    """CREATE FUNCTION viec._nhat_ky() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE cu jsonb;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                cu := jsonb_build_object('trang_thai', OLD.trang_thai,
                    'so_lan_thu', OLD.so_lan_thu, 'yeu_cau_dung', OLD.yeu_cau_dung);
                IF OLD.trang_thai = NEW.trang_thai
                    AND OLD.yeu_cau_dung = NEW.yeu_cau_dung THEN RETURN NEW; END IF;
            END IF;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang,
                doi_tuong_id, hanh_dong, truoc, sau)
                VALUES (NEW.phap_nhan_id, master.ktt_danh_tinh(), 'HE_THONG',
                    'viec.hang_viec', NEW.id, 'VIEC_' || NEW.trang_thai, cu,
                    jsonb_build_object('module', NEW.module, 'trang_thai', NEW.trang_thai,
                        'so_lan_thu', NEW.so_lan_thu, 'yeu_cau_dung', NEW.yeu_cau_dung,
                        'ma_loi', NEW.ma_loi));
            RETURN NEW;
        END $$""",
    """CREATE TRIGGER hang_viec_nhat_ky AFTER INSERT OR UPDATE ON viec.hang_viec
        FOR EACH ROW EXECUTE FUNCTION viec._nhat_ky()""",
    """CREATE FUNCTION viec.tao(p_pn uuid, p_module text, p_loai text,
        p_phien_ban integer, p_khoa text, p_tham_chieu uuid,
        p_ngoai boolean DEFAULT false, p_toi_da integer DEFAULT 3,
        p_cho_giay integer DEFAULT 60, p_giu_ngay integer DEFAULT NULL) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec; moi uuid;
        BEGIN
            PERFORM viec._kiem_quyen(p_pn, p_module);
            PERFORM pg_advisory_xact_lock_shared(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
            IF (master.module_trang_thai(p_module, p_pn)->'cho_ghi') IS DISTINCT FROM 'true'::jsonb THEN
                RAISE EXCEPTION 'VIEC_MODULE_TAT: không cho tạo việc mới' USING ERRCODE = '42501';
            END IF;
            INSERT INTO viec.hang_viec (phap_nhan_id, module, loai, phien_ban, khoa_dedupe,
                tham_chieu_id, co_tac_dong_ngoai, toi_da_lan_thu, thu_lai_giay, giu_ngay, tao_boi)
                VALUES (p_pn, p_module, p_loai, p_phien_ban, p_khoa, p_tham_chieu,
                    p_ngoai, p_toi_da, p_cho_giay, p_giu_ngay, master.ktt_danh_tinh())
                ON CONFLICT (phap_nhan_id, module, khoa_dedupe) DO NOTHING RETURNING id INTO moi;
            IF moi IS NOT NULL THEN RETURN moi; END IF;
            SELECT * INTO v FROM viec.hang_viec
                WHERE phap_nhan_id = p_pn AND module = p_module AND khoa_dedupe = p_khoa;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'VIEC_THU_LAI_GIAO_DICH' USING ERRCODE = '40001';
            END IF;
            IF v.loai IS DISTINCT FROM p_loai OR v.phien_ban IS DISTINCT FROM p_phien_ban
                OR v.tham_chieu_id IS DISTINCT FROM p_tham_chieu
                OR v.co_tac_dong_ngoai IS DISTINCT FROM p_ngoai
                OR v.toi_da_lan_thu IS DISTINCT FROM p_toi_da
                OR v.thu_lai_giay IS DISTINCT FROM p_cho_giay
                OR v.giu_ngay IS DISTINCT FROM p_giu_ngay THEN
                RAISE EXCEPTION 'VIEC_DEDUPE_XUNG_DOT' USING ERRCODE = '23505';
            END IF;
            RETURN v.id;
        END $$""",
    """CREATE FUNCTION viec.phuc_hoi(p_pn uuid, p_module text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec; tt text; n integer := 0;
        BEGIN
            PERFORM viec._kiem_quyen(p_pn, p_module);
            FOR v IN SELECT h.* FROM viec.hang_viec h
                WHERE h.phap_nhan_id = p_pn AND h.module = p_module
                    AND h.trang_thai = 'DANG_CHAY' AND h.lease_den <= clock_timestamp()
                ORDER BY h.lease_den, h.id LIMIT 100 FOR UPDATE SKIP LOCKED
            LOOP
                tt := CASE WHEN v.co_tac_dong_ngoai THEN 'CHUA_RO'
                    WHEN v.yeu_cau_dung THEN 'DA_DUNG'
                    WHEN v.so_lan_thu >= v.toi_da_lan_thu THEN 'LOI' ELSE 'CHO' END;
                UPDATE viec.hang_viec SET trang_thai = tt,
                    lease_boi = NULL, lease_danh_tinh = NULL, lease_token = NULL, lease_den = NULL,
                    ma_loi = 'LEASE_HET_HAN', cap_nhat_luc = clock_timestamp(),
                    thu_lai_sau = clock_timestamp() + make_interval(secs => v.thu_lai_giay),
                    ket_thuc_luc = CASE WHEN tt IN ('LOI','DA_DUNG') THEN clock_timestamp() END
                    WHERE id = v.id;
                n := n + 1;
            END LOOP;
            RETURN n;
        END $$""",
    """CREATE FUNCTION viec.nhan(p_pn uuid, p_module text, p_worker uuid,
        p_giay integer DEFAULT 120) RETURNS SETOF viec.hang_viec
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
        BEGIN
            PERFORM viec._kiem_quyen(p_pn, p_module);
            IF p_worker IS NULL OR p_giay IS NULL OR p_giay NOT BETWEEN 1 AND 3600 THEN
                RAISE EXCEPTION 'VIEC_LEASE_DAU_VAO' USING ERRCODE = '22023';
            END IF;
            -- Cùng khóa với module_kiem_admin/đổi công tắc, cả khi chưa có dòng override.
            PERFORM pg_advisory_xact_lock_shared(hashtextextended('module|' || p_module || '|' || p_pn::text, 0));
            IF (master.module_trang_thai(p_module, p_pn)->'cho_ghi') IS DISTINCT FROM 'true'::jsonb THEN
                RETURN;
            END IF;
            PERFORM viec.phuc_hoi(p_pn, p_module);
            SELECT * INTO v FROM viec.hang_viec h
                WHERE h.phap_nhan_id = p_pn AND h.module = p_module
                    AND h.trang_thai = 'CHO' AND NOT h.yeu_cau_dung
                    AND h.so_lan_thu < h.toi_da_lan_thu AND h.thu_lai_sau <= clock_timestamp()
                ORDER BY h.thu_lai_sau, h.tao_luc, h.id LIMIT 1 FOR UPDATE SKIP LOCKED;
            IF NOT FOUND THEN RETURN; END IF;
            UPDATE viec.hang_viec SET trang_thai = 'DANG_CHAY',
                so_lan_thu = so_lan_thu + 1, tien_do = 0,
                lease_boi = p_worker, lease_danh_tinh = master.ktt_danh_tinh(),
                lease_token = gen_random_uuid(), lease_den = clock_timestamp() + make_interval(secs => p_giay),
                cap_nhat_luc = clock_timestamp(), ma_loi = NULL
                WHERE id = v.id RETURNING * INTO v;
            RETURN NEXT v;
        END $$""",
    """CREATE FUNCTION viec._giu(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid)
        RETURNS viec.hang_viec LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn) THEN
                RAISE EXCEPTION 'VIEC_PHAM_VI' USING ERRCODE = '42501';
            END IF;
            SELECT * INTO v FROM viec.hang_viec WHERE id = p_id AND phap_nhan_id = p_pn FOR UPDATE;
            IF NOT FOUND THEN RETURN NULL; END IF;
            PERFORM viec._kiem_quyen(p_pn, v.module);
            IF v.trang_thai <> 'DANG_CHAY' OR v.lease_boi IS DISTINCT FROM p_worker
                OR v.lease_token IS DISTINCT FROM p_token
                OR v.lease_danh_tinh IS DISTINCT FROM master.ktt_danh_tinh()
                OR v.lease_den <= clock_timestamp() THEN RETURN NULL; END IF;
            RETURN v;
        END $$""",
    """CREATE FUNCTION viec.gia_han(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid,
        p_giay integer DEFAULT 120) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
        BEGIN
            v := viec._giu(p_pn, p_id, p_worker, p_token);
            IF v.id IS NULL THEN RETURN false; END IF;
            IF p_giay IS NULL OR p_giay NOT BETWEEN 1 AND 3600 THEN
                RAISE EXCEPTION 'VIEC_LEASE_DAU_VAO' USING ERRCODE = '22023';
            END IF;
            UPDATE viec.hang_viec SET lease_den = greatest(lease_den,
                clock_timestamp() + make_interval(secs => p_giay)), cap_nhat_luc = clock_timestamp()
                WHERE id = v.id AND lease_den > clock_timestamp();
            RETURN FOUND;
        END $$""",
    """CREATE FUNCTION viec.tien_do(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid,
        p_tien_do integer) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
        BEGIN
            v := viec._giu(p_pn, p_id, p_worker, p_token);
            IF v.id IS NULL THEN RETURN false; END IF;
            IF p_tien_do IS NULL OR p_tien_do NOT BETWEEN v.tien_do AND 100 THEN
                RAISE EXCEPTION 'VIEC_TIEN_DO' USING ERRCODE = '22023';
            END IF;
            UPDATE viec.hang_viec SET tien_do = p_tien_do, cap_nhat_luc = clock_timestamp()
                WHERE id = v.id AND lease_den > clock_timestamp();
            RETURN FOUND;
        END $$""",
    """CREATE FUNCTION viec.ket_thuc(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid,
        p_trang_thai text, p_ket_qua uuid DEFAULT NULL, p_ma_loi text DEFAULT NULL)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec; tt text := p_trang_thai;
        BEGIN
            v := viec._giu(p_pn, p_id, p_worker, p_token);
            IF v.id IS NULL THEN RETURN false; END IF;
            IF tt IS NULL OR tt NOT IN ('XONG','LOI','DA_DUNG','CHUA_RO','CHO')
                OR (tt = 'DA_DUNG' AND NOT v.yeu_cau_dung)
                OR (tt IN ('LOI','CHUA_RO','CHO') AND p_ma_loi IS NULL)
                OR (tt <> 'XONG' AND p_ket_qua IS NOT NULL) THEN
                RAISE EXCEPTION 'VIEC_KET_THUC_DAU_VAO' USING ERRCODE = '22023';
            END IF;
            IF tt = 'CHO' THEN
                tt := CASE WHEN v.yeu_cau_dung THEN 'DA_DUNG'
                    WHEN v.so_lan_thu >= v.toi_da_lan_thu THEN 'LOI' ELSE 'CHO' END;
            END IF;
            UPDATE viec.hang_viec SET trang_thai = tt, ket_qua_id = p_ket_qua, ma_loi = p_ma_loi,
                tien_do = CASE WHEN tt = 'XONG' THEN 100 ELSE tien_do END,
                thu_lai_sau = clock_timestamp() + make_interval(secs => v.thu_lai_giay),
                lease_boi = NULL, lease_danh_tinh = NULL, lease_token = NULL, lease_den = NULL,
                ket_thuc_luc = CASE WHEN tt IN ('XONG','LOI','DA_DUNG') THEN clock_timestamp() END,
                cap_nhat_luc = clock_timestamp() WHERE id = v.id AND lease_den > clock_timestamp();
            RETURN FOUND;
        END $$""",
    """CREATE FUNCTION viec.thu_lai(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid, p_ma_loi text)
        RETURNS boolean LANGUAGE sql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
            SELECT viec.ket_thuc(p_pn, p_id, p_worker, p_token, 'CHO', NULL, p_ma_loi)
        $$""",
    """CREATE FUNCTION viec.yeu_cau_dung(p_pn uuid, p_id uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn) THEN
                RAISE EXCEPTION 'VIEC_PHAM_VI' USING ERRCODE = '42501';
            END IF;
            SELECT * INTO v FROM viec.hang_viec WHERE id = p_id AND phap_nhan_id = p_pn FOR UPDATE;
            IF NOT FOUND THEN RETURN false; END IF;
            PERFORM viec._kiem_quyen(p_pn, v.module);
            IF v.trang_thai NOT IN ('CHO','DANG_CHAY') OR v.yeu_cau_dung THEN RETURN false; END IF;
            UPDATE viec.hang_viec SET yeu_cau_dung = true,
                trang_thai = CASE WHEN trang_thai = 'CHO' THEN 'DA_DUNG' ELSE trang_thai END,
                ket_thuc_luc = CASE WHEN trang_thai = 'CHO' THEN clock_timestamp() END,
                cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            RETURN true;
        END $$""",
    "REVOKE ALL ON ALL TABLES IN SCHEMA viec FROM PUBLIC",
    "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA viec FROM PUBLIC",
    """DO $$ DECLARE r text; BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON SCHEMA viec FROM %I', r);
                EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA viec FROM %I', r);
                EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA viec FROM %I', r);
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA viec TO app_web;
            GRANT SELECT ON viec.hang_viec TO app_web;
            GRANT EXECUTE ON FUNCTION
                viec.tao(uuid,text,text,integer,text,uuid,boolean,integer,integer,integer),
                viec.nhan(uuid,text,uuid,integer), viec.phuc_hoi(uuid,text),
                viec.gia_han(uuid,uuid,uuid,uuid,integer), viec.tien_do(uuid,uuid,uuid,uuid,integer),
                viec.ket_thuc(uuid,uuid,uuid,uuid,text,uuid,text),
                viec.thu_lai(uuid,uuid,uuid,uuid,text), viec.yeu_cau_dung(uuid,uuid) TO app_web;
        END IF;
        END $$""",
)


# XS-2a2 — CD-017: đọc lease không khóa/ghi; giữ nguyên hợp đồng M0060.
HANG_VIEC_B_SQL = (
    """CREATE FUNCTION viec.trang_thai_lease(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid)
        RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, viec, master, nhat_ky, pg_temp AS $$
        DECLARE v viec.hang_viec;
            khong_giu jsonb := jsonb_build_object('con_giu', false, 'yeu_cau_dung', NULL,
                'het_han_luc', NULL, 'trang_thai', NULL);
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.ktt_pn_cho_phep() pn WHERE pn = p_pn) THEN
                RAISE EXCEPTION 'VIEC_PHAM_VI' USING ERRCODE = '42501';
            END IF;
            SELECT * INTO v FROM viec.hang_viec WHERE id = p_id AND phap_nhan_id = p_pn;
            IF NOT FOUND THEN RETURN khong_giu; END IF;
            PERFORM viec._kiem_quyen(p_pn, v.module);
            IF v.trang_thai <> 'DANG_CHAY' OR v.lease_boi IS DISTINCT FROM p_worker
                OR v.lease_token IS DISTINCT FROM p_token
                OR v.lease_danh_tinh IS DISTINCT FROM master.ktt_danh_tinh()
                OR v.lease_den <= clock_timestamp() THEN RETURN khong_giu; END IF;
            RETURN jsonb_build_object('con_giu', true, 'yeu_cau_dung', v.yeu_cau_dung,
                'het_han_luc', v.lease_den, 'trang_thai', v.trang_thai);
        END $$""",
    "REVOKE ALL ON FUNCTION viec.trang_thai_lease(uuid,uuid,uuid,uuid) FROM PUBLIC",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION viec.trang_thai_lease(uuid,uuid,uuid,uuid) TO app_web;
        END IF;
        END $$""",
)
