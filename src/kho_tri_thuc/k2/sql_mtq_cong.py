MTQ_CONG_SQL = (
    """CREATE FUNCTION master.mtq_quyet_dinh_phien(
        p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE
            login text := master.ktt_danh_tinh(); ai uuid;
            pn uuid; phong uuid; scope_id uuid; khoa text; scope_loai text;
            obj uuid; hd uuid; da uuid; lh uuid; khach uuid;
            loai text; man_hinh text; module_hd text; hd_ho_tro boolean;
            n bigint; kq jsonb; ma text; ly_do text;
        BEGIN
            -- JSON là tham chiếu đối tượng, không phải danh tính/quyền client.
            -- Hợp đồng: {bang, id, phong_id?}. Pháp nhân, vai, phạm vi lấy từ DB.
            -- Resolver chưa có: chỉ chặn khi MTQ đã bật, không đoán pháp nhân.
            SELECT id INTO ai FROM master.nguoi_dung
                WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN
                ma := 'MTQ_DANH_TINH'; ly_do := 'Danh tính phiên ID/login không hợp lệ';
            ELSIF jsonb_typeof(p_doi_tuong) IS DISTINCT FROM 'object' THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Cần tham chiếu đối tượng máy chủ';
            ELSIF (p_doi_tuong - ARRAY['bang','id','phong_id']) <> '{}'::jsonb THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Không nhận danh tính, pháp nhân, vai hay quyết định từ tham số';
            ELSE
                BEGIN
                    obj := (p_doi_tuong->>'id')::uuid;
                    phong := (p_doi_tuong->>'phong_id')::uuid;
                EXCEPTION WHEN invalid_text_representation THEN
                    ma := 'MTQ_DOI_TUONG'; ly_do := 'Tham chiếu đối tượng/phòng không hợp lệ';
                END;
                IF ma IS NULL THEN
                    PERFORM pg_advisory_xact_lock_shared(742601, 1);
                    -- Không SQL động, không để client chọn bảng tùy ý.
                    IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN
                        SELECT h.phap_nhan_id, h.id, h.du_an_id, h.loai_hinh_dt_id, h.doi_tac_id,
                                h.module_chu IS NULL AND h.crm_giao_ket IS NULL
                            INTO pn, hd, da, lh, khach, hd_ho_tro FROM master.hop_dong h
                            WHERE h.id = obj;
                    ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN
                        SELECT d.phap_nhan_id, d.id INTO pn, da FROM master.du_an d WHERE d.id = obj;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat
                            WHERE bat AND (pn IS NULL OR phap_nhan_id = pn)) THEN
                        -- Cùng hợp đồng CU của lõi; không xét quyền cũ ở đây.
                        RETURN jsonb_build_object('nguon', 'CU', 'can_thiep', false, 'cho_phep', NULL,
                            'ma', 'MTQ_TAT', 'ly_do', 'Giữ đường kiểm quyền cũ');
                    ELSIF pn IS NULL THEN
                        ma := 'MTQ_CAN_RESOLVER_MTQ4'; ly_do := 'Chưa xác định được đối tượng/pháp nhân từ CSDL';
                    ELSE
                        SELECT c.loai_doi_tuong, c.man, c.module
                            INTO loai, man_hinh, module_hd
                            FROM master.mtq_danh_muc_hanh_dong c
                            WHERE c.catalog_version = 1 AND c.lenh_ky_thuat = p_hanh_dong;
                        -- Không suy HĐ M4/bản soạn G3 thành tiếp nhận luồng B.
                        IF module_hd IS DISTINCT FROM 'CRM' OR NOT coalesce((
                            (p_doi_tuong->>'bang' = 'master.hop_dong' AND hd_ho_tro AND man_hinh = 'TIEP_NHAN') OR
                            (p_doi_tuong->>'bang' = 'master.du_an' AND man_hinh = 'DU_AN_BAN')), false) THEN
                            ma := 'MTQ_CAN_RESOLVER_MTQ4'; ly_do := 'Chưa có resolver cho hành động trên loại đối tượng này';
                        ELSE
                            SELECT count(*), (array_agg(g.phong_id))[1] INTO n, phong
                                FROM master.mtq_gan_vai g
                                JOIN master.mtq_phong p ON p.id = g.phong_id AND p.phap_nhan_id = g.phap_nhan_id AND p.hoat_dong
                                WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.thu_hoi_luc IS NULL
                                    AND (phong IS NULL OR g.phong_id = phong);
                            IF n > 1 THEN
                                ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Cần xác định đúng một phòng, không hợp nhất quyền';
                            ELSE
                                SELECT s.id, s.khoa, s.loai INTO scope_id, khoa, scope_loai
                                    FROM master.mtq_pham_vi s JOIN master.mtq_gan_vai g ON g.id = s.gan_vai_id
                                    WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.phong_id = phong
                                        AND g.thu_hoi_luc IS NULL AND s.phap_nhan_id = pn AND s.thu_hoi_luc IS NULL
                                        AND ((s.loai = 'PHAP_NHAN' AND s.khoa = pn::text)
                                            OR (s.loai = 'HOP_DONG' AND s.khoa = hd::text)
                                            OR (s.loai = 'DU_AN' AND s.khoa = da::text)
                                            OR (s.loai = 'LOAI_HINH' AND s.khoa = lh::text)
                                            OR (s.loai = 'KHACH' AND s.khoa = khach::text))
                                    ORDER BY CASE s.loai WHEN 'HOP_DONG' THEN 1 WHEN 'DU_AN' THEN 2
                                        WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 ELSE 5 END, s.id LIMIT 1;
                            END IF;
                        END IF;
                    END IF;
                END IF;
            END IF;
            IF ma IS NOT NULL THEN
                RETURN jsonb_build_object('nguon','MA_TRAN','can_thiep',true,'cho_phep',false,
                    'ma',ma,'ly_do',ly_do,'revision',NULL,'gioi_han_vnd',NULL,
                    'doi_tuong',obj,'so_tien_vnd',p_so_tien);
            END IF;
            -- M0039 INSERT audit trong lõi. Rollback riêng INSERT đó để hàm hỏi
            -- không ghi trùng/ghi từng hàng RLS; biến PL/pgSQL giữ nguyên kq.
            -- Như hợp đồng lõi M0039, p_so_tien do resolver máy chủ lấy từ phiên
            -- bản nghiệp vụ đã khóa/tỷ giá ghim; adapter không chuyển số client.
            BEGIN
                kq := master.mtq_quyet_dinh(pn, phong, p_hanh_dong, loai, obj::text,
                    khoa, scope_loai, p_so_tien, scope_id, NULL);
                RAISE SQLSTATE 'ZMT01' USING MESSAGE = 'MTQ_CONG_HOI_KHONG_GHI';
            EXCEPTION WHEN SQLSTATE 'ZMT01' THEN NULL;
            END;
            IF kq IS NULL THEN RAISE EXCEPTION 'MTQ_LOI_QUYET_DINH: lõi không trả quyết định'; END IF;
            RETURN kq;
        END $$""",
    """CREATE FUNCTION master.mtq_ghi_tu_choi_phien(
        p_request uuid, p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE login text := master.ktt_danh_tinh(); ai uuid; kq jsonb; k uuid;
            pn uuid; phong uuid; vai_hd text;
        BEGIN
            -- Caller rollback nghiệp vụ, mở giao dịch khác, đặt lại GUC ID/login,
            -- gọi hàm này rồi commit. Hàm không tự commit, không tin JSON quyết định.
            IF p_request IS NULL THEN RAISE EXCEPTION 'MTQ_REQUEST: cần request ID'; END IF;
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN RAISE EXCEPTION 'MTQ_DANH_TINH: cần danh tính phiên hợp lệ để ghi'; END IF;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_danh_muc_hanh_dong
                    WHERE catalog_version = 1 AND lenh_ky_thuat = p_hanh_dong) THEN
                RAISE EXCEPTION 'MTQ_HANH_DONG: hành động chưa có trong catalog';
            END IF;
            -- Khóa theo request trước khi đọc/ghi để các lần gọi đồng thời
            -- không cùng thấy thiếu dòng; không cần đổi bảng M0039.
            PERFORM pg_advisory_xact_lock(hashtextextended(p_request::text, 0));
            SELECT id INTO k FROM nhat_ky.mtq_tu_choi
                WHERE request_id = p_request ORDER BY luc, id LIMIT 1;
            IF k IS NOT NULL THEN RETURN k; END IF;
            kq := master.mtq_quyet_dinh_phien(p_hanh_dong, p_doi_tuong, p_so_tien);
            -- Quyền đổi thành CU/cho phép sau rollback: báo lỗi, không giả mạo
            -- quyết định cũ và không chuyển lần thử nghiệp vụ thành thành công.
            IF kq->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb THEN
                RAISE EXCEPTION 'MTQ_KHONG_PHAI_TU_CHOI: chỉ ghi quyết định từ chối hiện hành';
            END IF;
            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN
                SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN
                SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id::text = kq->>'doi_tuong';
            END IF;
            SELECT g.phong_id, g.vai INTO phong, vai_hd FROM master.mtq_gan_vai g
                WHERE g.id = (kq->>'gan_vai_id')::uuid AND g.nguoi_dung_id = ai;
            INSERT INTO nhat_ky.mtq_tu_choi
                (request_id, actor_id, actor_login, phap_nhan_id, phong_id, vai, phien_ban_id, revision,
                 gan_vai_id, gan_vai_revision, pham_vi_id, pham_vi_revision, module, man, hanh_dong,
                 lenh_ky_thuat, doi_tuong, ma, ly_do, gioi_han_vnd, so_tien_vnd)
                VALUES (p_request, ai, login, pn, phong, vai_hd, (kq->>'phien_ban_id')::uuid,
                    (kq->>'revision')::bigint, (kq->>'gan_vai_id')::uuid, (kq->>'gan_vai_revision')::bigint,
                    (kq->>'pham_vi_id')::uuid, (kq->>'pham_vi_revision')::bigint,
                    kq->>'module', kq->>'man', kq->>'hanh_dong', p_hanh_dong,
                    kq->>'doi_tuong', kq->>'ma', kq->>'ly_do', (kq->>'gioi_han_vnd')::numeric,
                    (kq->>'so_tien_vnd')::numeric) RETURNING id INTO k;
            -- Không bắt/nuốt lỗi INSERT: audit lỗi phải trả lỗi hệ thống, không cho phép.
            RETURN k;
        END $$""",
    """REVOKE ALL ON FUNCTION master.mtq_quyet_dinh_phien(text,jsonb,numeric),
        master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric) FROM PUBLIC""",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION master.mtq_quyet_dinh_phien(text,jsonb,numeric),
                master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric) TO app_web;
        END IF;
        END $$""",
)


# MTQ-4a0b: bổ sung sau M0041; CREATE OR REPLACE giữ nguyên ACL của hàm.
MTQ_CONG_B_SQL = (
    """CREATE INDEX IF NOT EXISTS mtq_tu_choi_request_id_idx
        ON nhat_ky.mtq_tu_choi (request_id)""",
    """CREATE OR REPLACE FUNCTION master.mtq_ghi_tu_choi_phien(
        p_request uuid, p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE login text := master.ktt_danh_tinh(); ai uuid; kq jsonb; k uuid;
            pn uuid; phong uuid; vai_hd text; cu nhat_ky.mtq_tu_choi%ROWTYPE;
        BEGIN
            -- Caller rollback nghiệp vụ, mở giao dịch khác, đặt lại GUC ID/login,
            -- gọi hàm này rồi commit. Hàm không tự commit, không tin JSON quyết định.
            IF p_request IS NULL THEN RAISE EXCEPTION 'MTQ_REQUEST: cần request ID'; END IF;
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN RAISE EXCEPTION 'MTQ_DANH_TINH: cần danh tính phiên hợp lệ để ghi'; END IF;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_danh_muc_hanh_dong
                    WHERE catalog_version = 1 AND lenh_ky_thuat = p_hanh_dong) THEN
                RAISE EXCEPTION 'MTQ_HANH_DONG: hành động chưa có trong catalog';
            END IF;
            -- Khóa theo request trước khi đọc/ghi để các lần gọi đồng thời
            -- không cùng thấy thiếu dòng; không cần đổi bảng M0039.
            PERFORM pg_advisory_xact_lock(hashtextextended(p_request::text, 0));
            SELECT * INTO cu FROM nhat_ky.mtq_tu_choi
                WHERE request_id = p_request ORDER BY luc, id LIMIT 1;
            IF FOUND THEN
                -- Request chỉ idempotent khi cùng người, lệnh và ID đối tượng.
                IF cu.actor_id IS DISTINCT FROM ai
                        OR cu.actor_login IS DISTINCT FROM login
                        OR cu.lenh_ky_thuat IS DISTINCT FROM p_hanh_dong
                        OR cu.doi_tuong IS DISTINCT FROM (p_doi_tuong->>'id') THEN
                    RAISE EXCEPTION 'MTQ_REQUEST_TRUNG: request ID đã dùng cho người, hành động hoặc đối tượng khác';
                END IF;
                RETURN cu.id;
            END IF;
            kq := master.mtq_quyet_dinh_phien(p_hanh_dong, p_doi_tuong, p_so_tien);
            -- Quyền đổi thành CU/cho phép sau rollback: báo lỗi, không giả mạo
            -- quyết định cũ và không chuyển lần thử nghiệp vụ thành thành công.
            IF kq->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb THEN
                RAISE EXCEPTION 'MTQ_KHONG_PHAI_TU_CHOI: chỉ ghi quyết định từ chối hiện hành';
            END IF;
            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN
                SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN
                SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id::text = kq->>'doi_tuong';
            END IF;
            SELECT g.phong_id, g.vai INTO phong, vai_hd FROM master.mtq_gan_vai g
                WHERE g.id = (kq->>'gan_vai_id')::uuid AND g.nguoi_dung_id = ai;
            INSERT INTO nhat_ky.mtq_tu_choi
                (request_id, actor_id, actor_login, phap_nhan_id, phong_id, vai, phien_ban_id, revision,
                 gan_vai_id, gan_vai_revision, pham_vi_id, pham_vi_revision, module, man, hanh_dong,
                 lenh_ky_thuat, doi_tuong, ma, ly_do, gioi_han_vnd, so_tien_vnd)
                VALUES (p_request, ai, login, pn, phong, vai_hd, (kq->>'phien_ban_id')::uuid,
                    (kq->>'revision')::bigint, (kq->>'gan_vai_id')::uuid, (kq->>'gan_vai_revision')::bigint,
                    (kq->>'pham_vi_id')::uuid, (kq->>'pham_vi_revision')::bigint,
                    kq->>'module', kq->>'man', kq->>'hanh_dong', p_hanh_dong,
                    kq->>'doi_tuong', kq->>'ma', kq->>'ly_do', (kq->>'gioi_han_vnd')::numeric,
                    (kq->>'so_tien_vnd')::numeric) RETURNING id INTO k;
            -- Không bắt/nuốt lỗi INSERT: audit lỗi phải trả lỗi hệ thống, không cho phép.
            RETURN k;
        END $$""",
)


# MTQ-4a3a: resolver CRM luồng B/M1/file soát; giữ các hằng đã phát hành.
MTQ_CONG_C_SQL = (
    """CREATE OR REPLACE FUNCTION master.mtq_quyet_dinh_phien(
        p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE
            login text := master.ktt_danh_tinh(); ai uuid;
            pn uuid; phong uuid; scope_id uuid; khoa text; scope_loai text;
            obj uuid; hd uuid; da uuid; lh uuid; khach uuid;
            loai text; man_hinh text; module_hd text; hd_ho_tro boolean; hd_crm boolean; doi_tuong_ho_tro boolean := false;
            hd_text text;
            n bigint; kq jsonb; ma text; ly_do text;
        BEGIN
            -- JSON là tham chiếu đối tượng, không phải danh tính/quyền client.
            -- Hợp đồng: {bang, id, phong_id?}. Pháp nhân, vai, phạm vi lấy từ DB.
            -- Resolver chưa có: chỉ chặn khi MTQ đã bật, không đoán pháp nhân.
            SELECT id INTO ai FROM master.nguoi_dung
                WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN
                ma := 'MTQ_DANH_TINH'; ly_do := 'Danh tính phiên ID/login không hợp lệ';
            ELSIF jsonb_typeof(p_doi_tuong) IS DISTINCT FROM 'object' THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Cần tham chiếu đối tượng máy chủ';
            ELSIF (p_doi_tuong - ARRAY['bang','id','phong_id']) <> '{}'::jsonb THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Không nhận danh tính, pháp nhân, vai hay quyết định từ tham số';
            ELSE
                BEGIN
                    obj := (p_doi_tuong->>'id')::uuid;
                    phong := (p_doi_tuong->>'phong_id')::uuid;
                EXCEPTION WHEN invalid_text_representation THEN
                    ma := 'MTQ_DOI_TUONG'; ly_do := 'Tham chiếu đối tượng/phòng không hợp lệ';
                END;
                IF ma IS NULL THEN
                    PERFORM pg_advisory_xact_lock_shared(742601, 1);
                    -- Không SQL động, không để client chọn bảng tùy ý.
                    IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN
                        SELECT h.phap_nhan_id, h.id, h.du_an_id, h.loai_hinh_dt_id, h.doi_tac_id,
                                h.module_chu IS NULL AND h.crm_giao_ket IS NULL,
                                h.module_chu IS NULL AND h.loai NOT IN ('VAY','MUA')
                            INTO pn, hd, da, lh, khach, hd_ho_tro, hd_crm FROM master.hop_dong h
                            WHERE h.id = obj;
                    ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN
                        SELECT d.phap_nhan_id, d.id INTO pn, da FROM master.du_an d WHERE d.id = obj;
                    ELSIF p_doi_tuong->>'bang' = 'master.phap_nhan' THEN
                        SELECT p.id INTO pn FROM master.phap_nhan p WHERE p.id = obj;
                        doi_tuong_ho_tro := FOUND;
                    ELSIF p_doi_tuong->>'bang' = 'kho.chung_tu' THEN
                        -- KIND trong nguon/trich_hop_dong_6.py, được crm.py dùng.
                        -- Vẫn suy PN của dòng sai loại để PN tắt giữ nguyên CU.
                        SELECT c.phap_nhan_id, c.loai = 'HOP_DONG_TEP'
                            INTO pn, doi_tuong_ho_tro FROM kho.chung_tu c WHERE c.id = obj;
                        IF doi_tuong_ho_tro THEN
                            SELECT count(DISTINCT v.hop_dong_id), (array_agg(DISTINCT v.hop_dong_id))[1]
                                INTO n, hd FROM master.hop_dong_phien_ban v WHERE v.chung_tu_id = obj;
                            IF n = 1 THEN
                                SELECT h.du_an_id, h.loai_hinh_dt_id, h.doi_tac_id
                                    INTO da, lh, khach FROM master.hop_dong h
                                    WHERE h.id = hd AND h.phap_nhan_id = pn
                                        AND h.module_chu IS NULL AND h.crm_giao_ket IS NULL;
                                doi_tuong_ho_tro := FOUND;
                            ELSIF n > 1 THEN
                                -- Cần Anh/lead: không tự chọn một HĐ trong hồ sơ mơ hồ.
                                doi_tuong_ho_tro := false;
                            END IF;
                        END IF;
                    ELSIF p_doi_tuong->>'bang' = 'kho.lien_ket_chung_tu' THEN
                        -- Giữ PN cả dòng ngoài CRM để PN tắt vẫn đi CU.
                        SELECT l.phap_nhan_id, l.hop_dong_id,
                                l.loai = 'HOP_DONG_DOT_TIEN' AND l.chu_so_huu_module IS NULL
                            INTO pn, hd, doi_tuong_ho_tro FROM kho.lien_ket_chung_tu l WHERE l.id = obj;
                        IF doi_tuong_ho_tro AND hd IS NOT NULL THEN
                            SELECT h.du_an_id, h.loai_hinh_dt_id, h.doi_tac_id
                                INTO da, lh, khach FROM master.hop_dong h
                                WHERE h.id = hd AND h.phap_nhan_id = pn
                                    AND h.module_chu IS NULL AND h.loai NOT IN ('VAY','MUA');
                            doi_tuong_ho_tro := FOUND;
                        END IF;
                    ELSIF p_doi_tuong->>'bang' = 'kho.lo_xuat' THEN
                        SELECT l.phap_nhan_id, l.loai = 'FILE_SOAT' AND l.du_lieu->>'module' = 'CRM',
                                l.du_lieu->>'hop_dong_id'
                            INTO pn, doi_tuong_ho_tro, hd_text FROM kho.lo_xuat l WHERE l.id = obj;
                        IF doi_tuong_ho_tro THEN
                            -- Ép UUID riêng: chuỗi sai dạng chỉ còn phạm vi PN.
                            BEGIN
                                hd := hd_text::uuid;
                            EXCEPTION WHEN invalid_text_representation THEN
                                hd := NULL;
                            END;
                            IF hd IS NOT NULL THEN
                                SELECT h.du_an_id, h.loai_hinh_dt_id, h.doi_tac_id
                                    INTO da, lh, khach FROM master.hop_dong h
                                    WHERE h.id = hd AND h.phap_nhan_id = pn
                                        AND h.module_chu IS NULL AND h.loai NOT IN ('VAY','MUA');
                                doi_tuong_ho_tro := FOUND;
                            END IF;
                        END IF;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat
                            WHERE bat AND (pn IS NULL OR phap_nhan_id = pn)) THEN
                        -- Cùng hợp đồng CU của lõi; không xét quyền cũ ở đây.
                        RETURN jsonb_build_object('nguon', 'CU', 'can_thiep', false, 'cho_phep', NULL,
                            'ma', 'MTQ_TAT', 'ly_do', 'Giữ đường kiểm quyền cũ');
                    ELSIF pn IS NULL THEN
                        ma := 'MTQ_CAN_RESOLVER_MTQ4'; ly_do := 'Chưa xác định được đối tượng/pháp nhân từ CSDL';
                    ELSE
                        SELECT c.loai_doi_tuong, c.man, c.module
                            INTO loai, man_hinh, module_hd
                            FROM master.mtq_danh_muc_hanh_dong c
                            WHERE c.catalog_version = 1 AND c.lenh_ky_thuat = p_hanh_dong;
                        -- Không suy HĐ M4/bản soạn G3 thành tiếp nhận luồng B.
                        -- Whitelist cặp bảng/lệnh; không suy quyền từ loại đối tượng catalog.
                        -- HĐ thuộc CRM = module_chu IS NULL AND loai NOT IN ('VAY','MUA') (crm_s1.py:93), hẹp hơn RLS (an toàn).
                        IF NOT coalesce((
                            (p_doi_tuong->>'bang' = 'master.hop_dong' AND (
                                (module_hd = 'CRM' AND hd_ho_tro AND man_hinh = 'TIEP_NHAN') OR
                                (hd_crm AND p_hanh_dong IN ('M1:TIEN:SUA','CRM:FILE_SOAT:XEM')))) OR
                            (p_doi_tuong->>'bang' = 'master.du_an' AND module_hd = 'CRM' AND man_hinh = 'DU_AN_BAN') OR
                            (p_doi_tuong->>'bang' = 'master.phap_nhan' AND doi_tuong_ho_tro
                                AND p_hanh_dong IN ('CRM:TIEP_NHAN:LAP','M1:TIEN:LAP')) OR
                            (p_doi_tuong->>'bang' = 'kho.chung_tu' AND doi_tuong_ho_tro
                                AND p_hanh_dong IN ('CRM:TIEP_NHAN:SUA','CRM:TIEP_NHAN:KIEM')) OR
                            (p_doi_tuong->>'bang' = 'kho.lien_ket_chung_tu' AND doi_tuong_ho_tro
                                AND p_hanh_dong = 'M1:TIEN:HUY') OR
                            (p_doi_tuong->>'bang' = 'kho.lo_xuat' AND doi_tuong_ho_tro
                                AND p_hanh_dong = 'CRM:FILE_SOAT:XEM')), false) THEN
                            ma := 'MTQ_CAN_RESOLVER_MTQ4'; ly_do := 'Chưa có resolver cho hành động trên loại đối tượng này';
                        ELSE
                            SELECT count(*), (array_agg(g.phong_id))[1] INTO n, phong
                                FROM master.mtq_gan_vai g
                                JOIN master.mtq_phong p ON p.id = g.phong_id AND p.phap_nhan_id = g.phap_nhan_id AND p.hoat_dong
                                WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.thu_hoi_luc IS NULL
                                    AND (phong IS NULL OR g.phong_id = phong);
                            IF n > 1 THEN
                                ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Cần xác định đúng một phòng, không hợp nhất quyền';
                            ELSE
                                SELECT s.id, s.khoa, s.loai INTO scope_id, khoa, scope_loai
                                    FROM master.mtq_pham_vi s JOIN master.mtq_gan_vai g ON g.id = s.gan_vai_id
                                    WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.phong_id = phong
                                        AND g.thu_hoi_luc IS NULL AND s.phap_nhan_id = pn AND s.thu_hoi_luc IS NULL
                                        AND ((s.loai = 'PHAP_NHAN' AND s.khoa = pn::text)
                                            OR (s.loai = 'HOP_DONG' AND s.khoa = hd::text)
                                            OR (s.loai = 'DU_AN' AND s.khoa = da::text)
                                            OR (s.loai = 'LOAI_HINH' AND s.khoa = lh::text)
                                            OR (s.loai = 'KHACH' AND s.khoa = khach::text))
                                    ORDER BY CASE s.loai WHEN 'HOP_DONG' THEN 1 WHEN 'DU_AN' THEN 2
                                        WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 ELSE 5 END, s.id LIMIT 1;
                            END IF;
                        END IF;
                    END IF;
                END IF;
            END IF;
            IF ma IS NOT NULL THEN
                RETURN jsonb_build_object('nguon','MA_TRAN','can_thiep',true,'cho_phep',false,
                    'ma',ma,'ly_do',ly_do,'revision',NULL,'gioi_han_vnd',NULL,
                    'doi_tuong',obj,'so_tien_vnd',p_so_tien);
            END IF;
            -- M0039 INSERT audit trong lõi. Rollback riêng INSERT đó để hàm hỏi
            -- không ghi trùng/ghi từng hàng RLS; biến PL/pgSQL giữ nguyên kq.
            -- Như hợp đồng lõi M0039, p_so_tien do resolver máy chủ lấy từ phiên
            -- bản nghiệp vụ đã khóa/tỷ giá ghim; adapter không chuyển số client.
            BEGIN
                kq := master.mtq_quyet_dinh(pn, phong, p_hanh_dong, loai, obj::text,
                    khoa, scope_loai, p_so_tien, scope_id, NULL);
                RAISE SQLSTATE 'ZMT01' USING MESSAGE = 'MTQ_CONG_HOI_KHONG_GHI';
            EXCEPTION WHEN SQLSTATE 'ZMT01' THEN NULL;
            END;
            IF kq IS NULL THEN RAISE EXCEPTION 'MTQ_LOI_QUYET_DINH: lõi không trả quyết định'; END IF;
            RETURN kq;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.mtq_ghi_tu_choi_phien(
        p_request uuid, p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$
        DECLARE login text := master.ktt_danh_tinh(); ai uuid; kq jsonb; k uuid;
            pn uuid; phong uuid; vai_hd text; cu nhat_ky.mtq_tu_choi%ROWTYPE;
        BEGIN
            -- Caller rollback nghiệp vụ, mở giao dịch khác, đặt lại GUC ID/login,
            -- gọi hàm này rồi commit. Hàm không tự commit, không tin JSON quyết định.
            IF p_request IS NULL THEN RAISE EXCEPTION 'MTQ_REQUEST: cần request ID'; END IF;
            SELECT id INTO ai FROM master.nguoi_dung WHERE dang_nhap = login AND trang_thai = 'HOAT_DONG';
            IF ai IS NULL THEN RAISE EXCEPTION 'MTQ_DANH_TINH: cần danh tính phiên hợp lệ để ghi'; END IF;
            IF NOT EXISTS (SELECT 1 FROM master.mtq_danh_muc_hanh_dong
                    WHERE catalog_version = 1 AND lenh_ky_thuat = p_hanh_dong) THEN
                RAISE EXCEPTION 'MTQ_HANH_DONG: hành động chưa có trong catalog';
            END IF;
            -- Khóa theo request trước khi đọc/ghi để các lần gọi đồng thời
            -- không cùng thấy thiếu dòng; không cần đổi bảng M0039.
            PERFORM pg_advisory_xact_lock(hashtextextended(p_request::text, 0));
            SELECT * INTO cu FROM nhat_ky.mtq_tu_choi
                WHERE request_id = p_request ORDER BY luc, id LIMIT 1;
            IF FOUND THEN
                -- Request chỉ idempotent khi cùng người, lệnh và ID đối tượng.
                IF cu.actor_id IS DISTINCT FROM ai
                        OR cu.actor_login IS DISTINCT FROM login
                        OR cu.lenh_ky_thuat IS DISTINCT FROM p_hanh_dong
                        OR cu.doi_tuong IS DISTINCT FROM (p_doi_tuong->>'id') THEN
                    RAISE EXCEPTION 'MTQ_REQUEST_TRUNG: request ID đã dùng cho người, hành động hoặc đối tượng khác';
                END IF;
                RETURN cu.id;
            END IF;
            kq := master.mtq_quyet_dinh_phien(p_hanh_dong, p_doi_tuong, p_so_tien);
            -- Quyền đổi thành CU/cho phép sau rollback: báo lỗi, không giả mạo
            -- quyết định cũ và không chuyển lần thử nghiệp vụ thành thành công.
            IF kq->>'nguon' IS DISTINCT FROM 'MA_TRAN' OR kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb THEN
                RAISE EXCEPTION 'MTQ_KHONG_PHAI_TU_CHOI: chỉ ghi quyết định từ chối hiện hành';
            END IF;
            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN
                SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN
                SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'master.phap_nhan' THEN
                SELECT id INTO pn FROM master.phap_nhan WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'kho.chung_tu' THEN
                SELECT phap_nhan_id INTO pn FROM kho.chung_tu WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'kho.lien_ket_chung_tu' THEN
                -- kq đã qua resolver CRM ở mtq_quyet_dinh_phien; giữ PN cả khi chặn VAY/L11/HĐ ngoài CRM.
                SELECT phap_nhan_id INTO pn FROM kho.lien_ket_chung_tu WHERE id::text = kq->>'doi_tuong';
            ELSIF p_doi_tuong->>'bang' = 'kho.lo_xuat' THEN
                -- Cùng quyết định đã kiểm HĐ/UUID; audit vẫn ghi PN của lô bị từ chối.
                SELECT phap_nhan_id INTO pn FROM kho.lo_xuat WHERE id::text = kq->>'doi_tuong';
            END IF;
            SELECT g.phong_id, g.vai INTO phong, vai_hd FROM master.mtq_gan_vai g
                WHERE g.id = (kq->>'gan_vai_id')::uuid AND g.nguoi_dung_id = ai;
            INSERT INTO nhat_ky.mtq_tu_choi
                (request_id, actor_id, actor_login, phap_nhan_id, phong_id, vai, phien_ban_id, revision,
                 gan_vai_id, gan_vai_revision, pham_vi_id, pham_vi_revision, module, man, hanh_dong,
                 lenh_ky_thuat, doi_tuong, ma, ly_do, gioi_han_vnd, so_tien_vnd)
                VALUES (p_request, ai, login, pn, phong, vai_hd, (kq->>'phien_ban_id')::uuid,
                    (kq->>'revision')::bigint, (kq->>'gan_vai_id')::uuid, (kq->>'gan_vai_revision')::bigint,
                    (kq->>'pham_vi_id')::uuid, (kq->>'pham_vi_revision')::bigint,
                    kq->>'module', kq->>'man', kq->>'hanh_dong', p_hanh_dong,
                    kq->>'doi_tuong', kq->>'ma', kq->>'ly_do', (kq->>'gioi_han_vnd')::numeric,
                    (kq->>'so_tien_vnd')::numeric) RETURNING id INTO k;
            -- Không bắt/nuốt lỗi INSERT: audit lỗi phải trả lỗi hệ thống, không cho phép.
            RETURN k;
        END $$""",
    """REVOKE ALL ON FUNCTION master.mtq_quyet_dinh_phien(text,jsonb,numeric),
        master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric) FROM PUBLIC""",
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT EXECUTE ON FUNCTION master.mtq_quyet_dinh_phien(text,jsonb,numeric),
                master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric) TO app_web;
        END IF;
        END $$""",
)
