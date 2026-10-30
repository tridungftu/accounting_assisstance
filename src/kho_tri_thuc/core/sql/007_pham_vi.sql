-- G2-07: mot validator hop nhat M0065 (B3) va M0067 (NGUON).
-- Khong replay migration cu, khong tao/SQL bang rieng module.
-- ABI noi bo resolver_pham_vi: (ma, pn, hanh_dong, yeu_cau, viec, the_he)
-- -> jsonb. Cung chu ky/kiem owner/ACL nhu resolver_mtq G2-06.
-- yeu_cau: {loai,khoa,quan_he,doi_tuong}; doi_tuong null khi cap.
-- CRM tra {ket_luan,phap_nhan_id,quan_he}; khoa/doi tuong phai ton tai,
-- cung PN. HOP_DONG tu ghim ban soan hien hanh; DU_AN khi cap chi kiem
-- khach tuong minh, khong suy khach tu hop dong khac. Khi dung, tra quan he
-- cua doi tuong THUC TE (khong tra lai quan_he caller gui).
-- NGUON tra {ket_luan,ung_vien:[{ho_so_id,nguon_cai_dat,tham_chieu,ma_bam,
-- trang_thai}],anh_xa:[{id,nguon_cai_dat,tham_chieu,ma_bam,loai_chu_the,
-- khoa_chu_the,phap_nhan_id,trang_thai,hieu_luc_tu,hieu_luc_den}]}.
-- Resolver phai tra DU tap ung vien/anh xa, KHONG loc theo PN dich; khoa
-- hang ho so/instance va anh xa hien hanh theo ID (FOR SHARE), giu den het
-- transaction. Core kiem duy nhat truoc, khong chon dong dau theo PN.
-- Chi goi binding/contract da duoc provisioning duyet; khong tu kich hoat.
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai', true), '');
    vai_chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    vai_chay constant text := tien_to || 'vai_chay_loi';
    login_loi constant text := tien_to || 'dang_nhap_loi';
    vai_truoc constant text := current_setting('role');
    duong_tim_truoc constant text := current_setting('search_path');
    ham record;
BEGIN
    IF (tien_to <> '' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu') > 63
       OR (tien_to <> '' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'G2-07: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname = 'loi'
                   AND pg_get_userbyid(nspowner) = vai_chu)
       OR to_regprocedure('loi.mtq_quyet_dinh_phien(text,text,uuid,text,jsonb,text,text[],uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-07: Can lead, ap G2-01..06 truoc';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I', vai_chu);
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);

    CREATE OR REPLACE FUNCTION loi.mtq_kiem_pham_vi(
        p_ma text, p_module text, p_pn uuid, p_hanh_dong text,
        p_loai text, p_khoa text, p_quan_he jsonb, p_doi_tuong jsonb DEFAULT NULL,
        p_phien_ban_contract text DEFAULT '1', p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        binding jsonb; h loi.dang_ky_ham_module; kq jsonb; ghim jsonb;
        parts text[]; khoa text := p_khoa; loai_chu_the text; u jsonb; a jsonb;
        ho_so jsonb; n integer := 0; i integer; so_anh_xa integer := 0;
    BEGIN
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        IF NOT EXISTS (SELECT FROM loi.xac_minh_phien(
            p_ma,p_module,p_pn,p_hanh_dong,p_viec_id,p_the_he))
           OR split_part(p_hanh_dong,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'Phiên không hợp lệ' USING ERRCODE = '42501';
        END IF;
        IF p_loai IS NULL OR p_loai NOT IN ('PHAP_NHAN','NGUON','HOP_DONG','DU_AN','LOAI_HINH','KHACH')
           OR coalesce(btrim(p_khoa),'') = '' OR jsonb_typeof(p_quan_he) IS DISTINCT FROM 'object' THEN
            RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI');
        END IF;
        IF p_loai = 'PHAP_NHAN' THEN
            IF p_khoa IS DISTINCT FROM p_pn::text OR p_quan_he <> '{}'::jsonb THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI');
            END IF;
            RETURN jsonb_build_object('ket_luan','DAT','khoa',khoa,'quan_he',p_quan_he);
        ELSIF p_loai = 'NGUON' THEN
            parts := string_to_array(p_khoa, '|');
            IF cardinality(parts) <> 3 THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_KHOA');
            END IF;
            FOR i IN 1..3 LOOP
                parts[i] := upper(btrim(regexp_replace(parts[i], '[[:space:]]+', ' ', 'g')));
                IF parts[i] = '' THEN
                    RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_KHOA');
                END IF;
            END LOOP;
            loai_chu_the := CASE parts[1] WHEN 'INVOICE_SET' THEN 'COMPANY'
                WHEN 'KHO10_PHIEU' THEN 'WAREHOUSE' END;
            IF loai_chu_the IS NULL OR p_quan_he <> '{}'::jsonb THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_LOAI');
            END IF;
            khoa := array_to_string(parts, '|');
        END IF;
        -- Mot dinh nghia: khong co nhanh nao phu thuoc tick/cong tac MTQ.
        IF p_loai IN ('HOP_DONG','DU_AN') AND p_module <> 'crm' THEN
            RETURN jsonb_build_object('ket_luan','CHO','ma','MTQ_CAN_RESOLVER_MTQ4');
        END IF;
        binding := loi.phan_giai_ham_module(p_module,'resolver_pham_vi',p_phien_ban_contract,
            p_ma,p_pn,p_hanh_dong,p_viec_id,p_the_he);
        IF binding->>'ket_luan' IS DISTINCT FROM 'DAT' THEN
            RETURN jsonb_build_object('ket_luan','CHO','ma','MTQ_CAN_RESOLVER_MTQ4');
        END IF;
        h := jsonb_populate_record(NULL::loi.dang_ky_ham_module,binding->'binding');
        IF NOT EXISTS (SELECT FROM pg_proc WHERE oid = to_regprocedure(h.chu_ky)
            AND proargtypes = '25 2950 25 3802 2950 20'::oidvector
            AND prorettype = 'jsonb'::regtype AND NOT proretset AND provolatile = 'v') THEN
            -- Resolver khoa hang phai VOLATILE; STABLE khong duoc FOR SHARE.
            RAISE EXCEPTION 'Chữ ký resolver phạm vi không hợp lệ' USING ERRCODE = '42501';
        END IF;
        EXECUTE format('SELECT %I.%I($1,$2,$3,$4,$5,$6)',h.ten_schema,h.ten_ham)
            INTO kq USING p_ma,p_pn,p_hanh_dong,
                jsonb_build_object('loai',p_loai,'khoa',khoa,'quan_he',p_quan_he,'doi_tuong',p_doi_tuong),
                p_viec_id,p_the_he;
        IF kq IS NULL OR kq->>'ket_luan' = 'CHO' THEN
            RETURN jsonb_build_object('ket_luan','CHO','ma','MTQ_CAN_RESOLVER_MTQ4');
        END IF;
        IF kq->>'ket_luan' IS DISTINCT FROM 'DAT' THEN
            RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI_LECH');
        END IF;
        IF p_loai = 'NGUON' THEN
            IF jsonb_typeof(kq->'ung_vien') IS DISTINCT FROM 'array'
               OR jsonb_typeof(kq->'anh_xa') IS DISTINCT FROM 'array' THEN
                RETURN jsonb_build_object('ket_luan','CHO','ma','MTQ_CAN_RESOLVER_MTQ4');
            END IF;
            FOR u IN SELECT value FROM jsonb_array_elements(kq->'ung_vien') LOOP
                IF u->>'trang_thai' = 'HOAT_DONG' AND
                    (upper(u->>'ho_so_id') = parts[2] OR upper(u->>'nguon_cai_dat') = parts[2]) THEN
                    n := n + 1; ho_so := u;
                END IF;
            END LOOP;
            IF n <> 1 OR coalesce(ho_so->>'tham_chieu','') = ''
               OR coalesce(ho_so->>'ma_bam','') !~ '^[a-f0-9]{64}$'
               OR coalesce(ho_so->>'nguon_cai_dat','') = '' THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_PROFILE');
            END IF;
            FOR a IN SELECT value FROM jsonb_array_elements(kq->'anh_xa') LOOP
                IF a->>'nguon_cai_dat' = ho_so->>'nguon_cai_dat'
                   AND a->>'tham_chieu' = ho_so->>'tham_chieu' AND a->>'ma_bam' = ho_so->>'ma_bam'
                   AND a->>'loai_chu_the' = loai_chu_the
                   AND upper(btrim(regexp_replace(a->>'khoa_chu_the','[[:space:]]+',' ','g'))) = parts[3]
                   AND a->>'trang_thai' = 'DA_DUYET'
                   AND (a->>'hieu_luc_tu')::timestamptz <= now()
                   AND (a->>'hieu_luc_den' IS NULL OR (a->>'hieu_luc_den')::timestamptz > now()) THEN
                    so_anh_xa := so_anh_xa + 1;
                    -- Kiem MOI PN truoc dem duy nhat, khong LIMIT/theo PN dich.
                    IF a->>'phap_nhan_id' IS DISTINCT FROM p_pn::text THEN
                        RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_ANH_XA');
                    END IF;
                END IF;
            END LOOP;
            IF so_anh_xa <> 1 THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_NGUON_ANH_XA');
            END IF;
            ghim := '{}'::jsonb;
        ELSE
            ghim := kq->'quan_he';
            IF kq->>'phap_nhan_id' IS DISTINCT FROM p_pn::text
               OR jsonb_typeof(ghim) IS DISTINCT FROM 'object' THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI_LECH');
            END IF;
            IF p_loai = 'DU_AN' AND ghim <> '{}'::jsonb THEN
                IF NOT ((ghim ? 'doi_tac_id' AND ghim - 'doi_tac_id' = '{}'::jsonb
                        AND coalesce(ghim->>'doi_tac_id','') ~ '^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$')
                    OR (ghim ? 'khach_du_thao_sha256' AND ghim - 'khach_du_thao_sha256' = '{}'::jsonb
                        AND coalesce(ghim->>'khach_du_thao_sha256','') ~ '^[a-f0-9]{64}$')) THEN
                    RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI_LECH');
                END IF;
            END IF;
            -- Bao toan master.crm_ky_mtq (k2/sql_mtq_crm.py, M0065):
            -- DU_AN chua ghim khach duoc doc thuong; G3/BAN_KY luon can ghim khop.
            IF (p_doi_tuong IS NULL AND p_quan_he <> '{}'::jsonb AND p_quan_he IS DISTINCT FROM ghim)
               OR (p_doi_tuong IS NOT NULL AND p_quan_he IS DISTINCT FROM ghim
                   AND (p_loai <> 'DU_AN' OR p_quan_he <> '{}'::jsonb
                       OR p_hanh_dong ~ '^CRM:(G3_G4_SOAN_KY|BAN_KY):'))
               OR (p_doi_tuong IS NOT NULL AND p_hanh_dong ~ '^CRM:(G3_G4_SOAN_KY|BAN_KY):'
                   AND (p_loai NOT IN ('HOP_DONG','DU_AN') OR ghim = '{}'::jsonb)) THEN
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI_LECH');
            END IF;
            IF p_loai = 'DU_AN' AND p_doi_tuong IS NULL AND p_quan_he = '{}'::jsonb AND ghim <> '{}'::jsonb THEN
                -- Khong tu suy khach cua du an khi cap.
                RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI_LECH');
            END IF;
        END IF;
        RETURN jsonb_build_object('ket_luan','DAT','khoa',khoa,'quan_he',ghim);
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.mtq_cap_pham_vi_phien(
        p_ma text, p_module text, p_pn uuid, p_gan_vai uuid, p_loai text, p_khoa text,
        p_quan_he jsonb DEFAULT '{}', p_ly_do text DEFAULT 'Cấp phạm vi',
        p_phien_ban_contract text DEFAULT '1', p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE ai uuid; g loi.mtq_gan_vai; kq jsonb; ket_qua loi.mtq_pham_vi;
        hanh_dong text := upper(p_module) || ':MTQ:CAP_PHAM_VI';
    BEGIN
        PERFORM pg_advisory_xact_lock(742601, 1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(
            p_ma,p_module,p_pn,hanh_dong,p_viec_id,p_the_he);
        IF ai IS NULL OR NOT EXISTS (SELECT FROM loi.mtq_admin WHERE nguoi_dung_id=ai AND thu_hoi_luc IS NULL) THEN
            RAISE EXCEPTION 'Chỉ Admin đã xác minh được cấp phạm vi' USING ERRCODE = '42501';
        END IF;
        SELECT * INTO g FROM loi.mtq_gan_vai WHERE id=p_gan_vai FOR SHARE;
        IF g.id IS NULL OR g.phap_nhan_id IS DISTINCT FROM p_pn OR g.thu_hoi_luc IS NOT NULL
           OR NOT EXISTS (SELECT FROM loi.mtq_phong WHERE id=g.phong_id AND phap_nhan_id=p_pn)
           OR coalesce(btrim(p_ly_do),'') = '' THEN
            RETURN jsonb_build_object('ket_luan','TU_CHOI','ma','MTQ_PHAM_VI');
        END IF;
        kq := loi.mtq_kiem_pham_vi(p_ma,p_module,p_pn,hanh_dong,p_loai,p_khoa,p_quan_he,
            NULL,p_phien_ban_contract,p_viec_id,p_the_he);
        IF kq->>'ket_luan' IS DISTINCT FROM 'DAT' THEN RETURN kq; END IF;
        ket_qua.id := gen_random_uuid();
        -- Audit TRUOC INSERT: trigger G2-06 thu hoi phien khi doi cau hinh.
        -- Loi INSERT rollback luon audit; khong ghi ma/JSON quan he vao audit.
        PERFORM loi.ghi_kiem_toan(hanh_dong,'mtq_pham_vi',ket_qua.id,'DAT',
            p_ma,p_module,p_pn,NULL,p_viec_id,p_the_he);
        INSERT INTO loi.mtq_pham_vi(id,gan_vai_id,phap_nhan_id,loai,khoa,quan_he,cap_boi,ly_do)
            VALUES (ket_qua.id,p_gan_vai,p_pn,p_loai,kq->>'khoa',kq->'quan_he',ai,p_ly_do)
            RETURNING * INTO ket_qua;
        INSERT INTO loi.mtq_thay_doi(request_id,phap_nhan_id,doi_tuong_bang,doi_tuong,
            phien_ban_dong,loai_su_kien,sau,nguoi_dung_id,dang_nhap,ly_do)
            VALUES (gen_random_uuid(),p_pn,'mtq_pham_vi',jsonb_build_object('id',ket_qua.id),
                ket_qua.phien_ban_dong,'CAP_PHAM_VI',to_jsonb(ket_qua),ai,session_user,p_ly_do);
        RETURN jsonb_build_object('ket_luan','DAT','pham_vi',to_jsonb(ket_qua));
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.mtq_quyet_dinh_phien(
        p_ma text, p_module text, p_pn uuid, p_hanh_dong text, p_doi_tuong jsonb,
        p_phien_ban_contract text DEFAULT '1', p_cac_ma text[] DEFAULT '{}',
        p_viec_id uuid DEFAULT NULL, p_the_he bigint DEFAULT NULL
    ) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp AS $ham$
    DECLARE
        ai uuid; nguoi uuid; pn uuid; phong uuid; scope_id uuid;
        khoa text; scope_loai text; obj uuid; tap jsonb; giai jsonb;
        dau jsonb; kq jsonb; n bigint; so_pn bigint; so_bat bigint;
        ma text; ly_do text; tien numeric;
        pham_vi loi.mtq_pham_vi; kiem jsonb; ma_pn text;
    BEGIN
        -- Lay khoa truoc xac minh; VOLATILE doc snapshot moi sau khi cho cau hinh.
        -- xac_minh_phien van STABLE/tra bam co chi muc theo chuan G2-03.
        PERFORM pg_advisory_xact_lock_shared(742601, 1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(
            p_ma, p_module, p_pn, p_hanh_dong, p_viec_id, p_the_he);
        IF ai IS NULL THEN
            RAISE EXCEPTION 'Phiên không hợp lệ' USING ERRCODE = '42501';
        END IF;
        IF split_part(p_hanh_dong,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'Hành động không thuộc module của phiên' USING ERRCODE = '42501';
        END IF;
        IF jsonb_typeof(p_doi_tuong) IS DISTINCT FROM 'object'
           OR (p_doi_tuong - ARRAY['bang','id','phong_id']) <> '{}'::jsonb
           OR coalesce(p_doi_tuong->>'bang','') = '' THEN
            ma := 'MTQ_DOI_TUONG'; ly_do := 'Cần tham chiếu đối tượng máy chủ';
        ELSE
            BEGIN
                obj := (p_doi_tuong->>'id')::uuid;
                phong := (p_doi_tuong->>'phong_id')::uuid;
            EXCEPTION WHEN invalid_text_representation THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Tham chiếu đối tượng hoặc phòng không hợp lệ';
            END;
            IF obj IS NULL THEN ma := 'MTQ_DOI_TUONG'; ly_do := 'Thiếu mã đối tượng'; END IF;
        END IF;
        IF ma IS NULL THEN
            tap := loi.mtq_giai_doi_tuong_tap(p_ma, p_module, p_pn, p_hanh_dong,
                p_doi_tuong, p_phien_ban_contract, p_viec_id, p_the_he);
            IF tap IS NULL OR jsonb_typeof(tap) IS DISTINCT FROM 'array' THEN
                RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                    'ma','MTQ_CAN_RESOLVER_MTQ4','ly_do','Chưa có resolver hoặc căn cứ hợp lệ');
            END IF;
            SELECT count(*), count(DISTINCT value->>'pn'),
                count(*) FILTER (WHERE EXISTS (SELECT FROM loi.mtq_kich_hoat k
                    WHERE k.phap_nhan_id = (value->>'pn')::uuid AND k.bat))
                INTO so_pn, n, so_bat FROM jsonb_array_elements(tap);
            IF so_pn = 0 OR so_pn <> n OR NOT EXISTS
                (SELECT FROM jsonb_array_elements(tap) WHERE value->>'pn' = p_pn::text) THEN
                ma := 'MTQ_DOI_TUONG'; ly_do := 'Tập pháp nhân không hợp lệ';
            ELSE
                -- Moi PN can ma rieng, cung nguoi/module/hanh dong/uy nhiem viec.
                FOR giai IN SELECT value FROM jsonb_array_elements(tap) ORDER BY value->>'pn' LOOP
                    pn := (giai->>'pn')::uuid;
                    IF giai->'hop_le' = 'false'::jsonb THEN
                        ma := 'MTQ_DOI_TUONG';
                        ly_do := coalesce(giai->>'ly_do', 'Đối tượng không hợp lệ'); EXIT;
                    END IF;
                    IF giai->'hop_le' IS DISTINCT FROM 'true'::jsonb OR pn IS NULL THEN
                        RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                            'ma','MTQ_CAN_RESOLVER_MTQ4','ly_do','Chưa đủ căn cứ đối tượng');
                    END IF;
                    SELECT x.nguoi_dung_id INTO nguoi
                        FROM unnest(ARRAY[p_ma] || coalesce(p_cac_ma, '{}'::text[])) m
                        CROSS JOIN LATERAL loi.xac_minh_phien(m, p_module, pn, p_hanh_dong,
                            p_viec_id, p_the_he) x
                        WHERE x.nguoi_dung_id = ai LIMIT 1;
                    IF nguoi IS NULL THEN
                        ma := 'MTQ_PHAP_NHAN'; ly_do := 'Thiếu phiên hợp lệ ở một pháp nhân'; EXIT;
                    END IF;
                END LOOP;
                IF ma IS NULL THEN
                    -- QD-20261026-10: moi PN kiem cung tong tien, khong chia nho han muc.
                    tien := (tap->0->>'so_tien_vnd')::numeric;
                    IF EXISTS (SELECT FROM jsonb_array_elements(tap)
                        WHERE (value->>'so_tien_vnd')::numeric IS DISTINCT FROM tien) THEN
                        ma := 'MTQ_DOI_TUONG'; ly_do := 'Các pháp nhân phải dùng cùng số tiền';
                    END IF;
                END IF;
                IF ma IS NULL AND so_bat > 0 AND so_bat <> so_pn THEN
                    ma := 'MTQ_PN_HON_HOP'; ly_do := 'Đối tượng có pháp nhân chưa bật ma trận';
                ELSIF ma IS NULL AND so_bat = 0 THEN
                    -- Khong mo fallback CU cho module moi khong co khai bao chuyen tiep.
                    RETURN jsonb_build_object('ket_luan','CHO','cho_phep',false,
                        'ma','MTQ_TAT','ly_do','Ma trận chưa được bật cho đối tượng');
                ELSIF ma IS NULL AND so_pn > 1 AND p_doi_tuong->>'phong_id' IS NOT NULL THEN
                    ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Không hợp nhất phòng giữa các pháp nhân';
                END IF;
            END IF;
            IF ma IS NULL THEN
                FOR giai IN SELECT value FROM jsonb_array_elements(tap) ORDER BY value->>'pn' LOOP
                    pn := (giai->>'pn')::uuid;
                    phong := coalesce((giai->>'phong')::uuid, (p_doi_tuong->>'phong_id')::uuid);
                    scope_id := NULL; khoa := NULL; scope_loai := NULL;
                    SELECT count(*), (array_agg(g.phong_id))[1] INTO n, phong
                        FROM loi.mtq_gan_vai g JOIN loi.mtq_phong p
                            ON p.id = g.phong_id AND p.phap_nhan_id = g.phap_nhan_id AND p.hoat_dong
                        WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.thu_hoi_luc IS NULL
                            AND (phong IS NULL OR g.phong_id = phong);
                    IF n > 1 THEN
                        ma := 'MTQ_PHONG_MO_HO'; ly_do := 'Cần đúng một phòng, không hợp nhất quyền'; EXIT;
                    END IF;
                    SELECT s.id, s.khoa, s.loai INTO scope_id, khoa, scope_loai
                        FROM loi.mtq_pham_vi s JOIN loi.mtq_gan_vai g ON g.id = s.gan_vai_id
                        WHERE g.nguoi_dung_id = ai AND g.phap_nhan_id = pn AND g.phong_id = phong
                            AND g.thu_hoi_luc IS NULL AND s.phap_nhan_id = pn AND s.thu_hoi_luc IS NULL
                            AND ((s.loai = 'PHAP_NHAN' AND s.khoa = pn::text)
                                OR (s.loai = 'HOP_DONG' AND s.khoa = giai->>'hd')
                                OR (s.loai = 'DU_AN' AND s.khoa = giai->>'da')
                                OR (s.loai = 'LOAI_HINH' AND s.khoa = giai->>'lh')
                                OR (s.loai = 'KHACH' AND s.khoa = giai->>'khach')
                                OR (s.loai = 'NGUON' AND s.khoa = giai->>'nguon_khoa'))
                        ORDER BY CASE s.loai WHEN 'HOP_DONG' THEN 1 WHEN 'DU_AN' THEN 2
                            WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 WHEN 'NGUON' THEN 5 ELSE 6 END,
                            s.id LIMIT 1;
                    -- G2-07: kiem scope DA CHON, khong fallback khi ghim lech.
                    SELECT * INTO pham_vi FROM loi.mtq_pham_vi WHERE id=scope_id;
                    -- Guard ky doc lap voi NGUON va tick: nguon hop le khong thay HOP_DONG/DU_AN.
                    IF p_hanh_dong ~ '^CRM:(G3_G4_SOAN_KY|BAN_KY):'
                       AND (scope_id IS NULL OR pham_vi.loai NOT IN ('HOP_DONG','DU_AN')) THEN
                        RETURN jsonb_build_object('ket_luan','TU_CHOI','cho_phep',false,
                            'ma','MTQ_PHAM_VI','phap_nhan_id',pn);
                    END IF;
                    IF scope_id IS NOT NULL AND pham_vi.loai IN ('NGUON','HOP_DONG','DU_AN') THEN
                        SELECT m INTO ma_pn FROM unnest(ARRAY[p_ma] || coalesce(p_cac_ma,'{}'::text[])) m
                            CROSS JOIN LATERAL loi.xac_minh_phien(m,p_module,pn,p_hanh_dong,p_viec_id,p_the_he) x
                            WHERE x.nguoi_dung_id=ai LIMIT 1;
                        kiem := loi.mtq_kiem_pham_vi(ma_pn,p_module,pn,p_hanh_dong,
                            pham_vi.loai,pham_vi.khoa,pham_vi.quan_he,p_doi_tuong,
                            p_phien_ban_contract,p_viec_id,p_the_he);
                        IF kiem->>'ket_luan' IS DISTINCT FROM 'DAT' THEN
                            RETURN kiem || jsonb_build_object('cho_phep',false,'pham_vi_id',scope_id,
                                'phap_nhan_id',pn);
                        END IF;
                    END IF;
                    kq := loi.mtq_quyet_dinh(ai, pn, phong, p_hanh_dong, giai->>'loai',
                        obj::text, khoa, scope_loai, tien, scope_id, NULL);
                    kq := kq || jsonb_build_object('ket_luan', CASE WHEN kq->'cho_phep' = 'true'::jsonb
                        THEN 'DAT' ELSE 'TU_CHOI' END);
                    IF kq->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN RETURN kq; END IF;
                    IF dau IS NULL THEN dau := kq; END IF;
                END LOOP;
                RETURN dau;
            END IF;
        END IF;
        RETURN jsonb_build_object('nguon','MA_TRAN','can_thiep',true,'ket_luan','TU_CHOI',
            'cho_phep',false,'ma',ma,'ly_do',ly_do,'doi_tuong',obj);
    END;
    $ham$;

    -- CREATE OR REPLACE giu OID/owner/ACL cua cong G2-06.
    FOR ham IN SELECT oid::regprocedure AS chu_ky, proname FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname IN ('mtq_kiem_pham_vi','mtq_cap_pham_vi_phien') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, %I, %I',ham.chu_ky,vai_chay,login_loi);
        IF ham.proname='mtq_cap_pham_vi_phien' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.chu_ky,login_loi);
        END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_tim_truoc,true);
    PERFORM set_config('role',vai_truoc,true);
END;
$$;
