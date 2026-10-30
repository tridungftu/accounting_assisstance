-- G2-13: tat ca thao tac cung ket noi/transaction READ COMMITTED.
-- ABI resolver_nghia_vu v1: (ma, module_caller, pn, hd, yeu_cau, viec, the_he)
-- -> {ket_luan: DAT|CHO, module_nghia_vu, loai_nghia_vu, nghia_vu_id,
--     phien_ban_can_cu_id, ma_bam_phien_ban_can_cu, tien_te, thang_tien}.
-- yeu_cau.giai_doan = KHOA|KIEM. KHOA phai khoa nghia vu va xac minh
-- ca bo ba + can cu; KIEM dung tong_nghia_vu_noi_bo de kiem suc chua.
-- Khong tra tong/suc chua ra runtime. Module Manager chi cap hai ham
-- tong_nghia_vu_noi_bo/khoa_lien_ket_noi_bo cho role kiem module da duyet.
-- Giam suc chua: khoa_lien_ket_noi_bo(pn) -> khoa nghia vu -> doi/kiem tong.
-- Khoa dieu phoi PN co y tuan tu hoa ghi tien, tranh bo sot chung tu moi
-- trong luc giam suc chua. Moi duong ghi phai di qua cung giao thuc nay.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt||'vai_doi_cau_truc_danh_muc';
    chu_loi text := tt||'vai_doi_cau_truc_loi';
    kiem text := tt||'vai_kiem_toan_ven_danh_muc';
    chay text := tt||'vai_chay_danh_muc';
    login text := tt||'dang_nhap_loi';
    vai_cu text := current_setting('role');
    duong_cu text := current_setting('search_path');
    bang text; ham record;
BEGIN
    IF (tt<>'' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tt||'vai_doi_cau_truc_loi_tai_lieu')>63
       OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-13: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF to_regclass('danh_muc.lien_ket_phan_bo') IS NULL
       OR NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='danh_muc' AND pg_get_userbyid(nspowner)=chu) THEN
        RAISE EXCEPTION 'G2-13: Can lead, ap 001..012 truoc';
    END IF;
    IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname=kiem) THEN
        EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION',kiem);
    END IF;
    IF EXISTS(SELECT FROM pg_roles WHERE rolname=kiem AND
        (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication))
       OR EXISTS(SELECT FROM pg_auth_members WHERE roleid=(SELECT oid FROM pg_roles WHERE rolname=kiem)
                  OR member=(SELECT oid FROM pg_roles WHERE rolname=kiem)) THEN
        RAISE EXCEPTION 'G2-13: Can lead, vai kiem sai thuoc tinh/membership';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I',chu_loi);
    EXECUTE format('GRANT USAGE ON SCHEMA loi TO %I',kiem);
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.mtq_phien_rls() TO %I',kiem);

    -- Dispatcher noi bo co quyen Core, registry G2-05 van la nguon binding.
    -- Khac phan_giai_ham_module: module dich co the khac module caller.
    CREATE OR REPLACE FUNCTION loi.goi_nghia_vu_noi_bo(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_dich jsonb,p_contract text,p_viec uuid,p_the_he bigint) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE h loi.dang_ky_ham_module; kq jsonb; cong_tac jsonb;
    BEGIN
        IF NOT EXISTS(SELECT FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he)) THEN
            RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
        END IF;
        SELECT d.* INTO h FROM loi.dang_ky_ham_module d
            JOIN loi.phien_ban_module m ON (m.module,m.so_phien_ban,m.ma_bam_goi)=
                (d.module,d.phien_ban_module,d.ma_bam_goi)
            JOIN loi.dang_ky_contract c ON (c.ma,c.phien_ban)=(d.ma_contract,d.phien_ban_contract)
            WHERE d.module=p_dich->>'module_nghia_vu' AND d.loai_ham='resolver_nghia_vu'
              AND d.phien_ban_contract=p_contract AND m.trang_thai='da_cai' AND c.trang_thai='dang_dung';
        IF NOT FOUND OR to_regprocedure(h.chu_ky) IS NULL THEN
            RETURN jsonb_build_object('ket_luan','CHO','ly_do','THIEU_MODULE_RESOLVER');
        END IF;
        cong_tac := loi.module_trang_thai(p_ma,h.module,p_pn,p_hd,p_module,p_viec,p_the_he);
        IF cong_tac->'cho_ghi' IS DISTINCT FROM 'true'::jsonb THEN
            RETURN jsonb_build_object('ket_luan','CHO','ly_do','MODULE_NGHIA_VU_KHONG_CHO_GHI');
        END IF;
        IF NOT loi.kiem_binding_ham(h) OR NOT EXISTS(SELECT FROM pg_proc
            WHERE oid=to_regprocedure(h.chu_ky) AND proargtypes='25 25 2950 25 3802 2950 20'::oidvector
              AND prorettype='jsonb'::regtype AND NOT proretset AND provolatile='v') THEN
            RAISE EXCEPTION 'LIEN_KET_RESOLVER' USING ERRCODE='42501';
        END IF;
        EXECUTE format('SELECT %I.%I($1,$2,$3,$4,$5,$6,$7)',h.ten_schema,h.ten_ham)
            INTO kq USING p_ma,p_module,p_pn,p_hd,p_dich,p_viec,p_the_he;
        IF kq IS NULL OR kq->>'ket_luan'='CHO' THEN
            RETURN jsonb_build_object('ket_luan','CHO','ly_do','THIEU_CAN_CU');
        END IF;
        IF kq->>'ket_luan' IS DISTINCT FROM 'DAT' OR EXISTS(
            SELECT FROM unnest(ARRAY['module_nghia_vu','loai_nghia_vu','nghia_vu_id',
                'phien_ban_can_cu_id','ma_bam_phien_ban_can_cu','tien_te','thang_tien']) k
            WHERE kq->k IS DISTINCT FROM p_dich->k) THEN
            RAISE EXCEPTION 'LIEN_KET_CAN_CU' USING ERRCODE='P0001';
        END IF;
        -- Chi chuyen ket luan, khong chuyen noi dung/tong tu module.
        RETURN jsonb_build_object('ket_luan','DAT');
    END;
    $ham$;
    REVOKE ALL ON FUNCTION loi.goi_nghia_vu_noi_bo(text,text,uuid,text,jsonb,text,uuid,bigint) FROM PUBLIC;
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.goi_nghia_vu_noi_bo(text,text,uuid,text,jsonb,text,uuid,bigint) TO %I',chu);

    EXECUTE format('SET LOCAL ROLE %I',chu);
    EXECUTE format('GRANT USAGE,CREATE ON SCHEMA danh_muc TO %I',kiem);
    FOREACH bang IN ARRAY ARRAY['chung_tu','lien_ket_chung_tu','lien_ket_phan_bo'] LOOP
        EXECUTE format('GRANT SELECT ON danh_muc.%I TO %I',bang,kiem);
        EXECUTE format('ALTER TABLE danh_muc.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE danh_muc.%I FORCE ROW LEVEL SECURITY',bang);
        -- Khong chap nhan restrictive policy co the lam thieu tong.
        IF EXISTS(SELECT FROM pg_policy WHERE polrelid=format('danh_muc.%I',bang)::regclass
                  AND NOT polpermissive) THEN
            RAISE EXCEPTION 'G2-13: Can lead, review restrictive policy';
        END IF;
        IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid=format('danh_muc.%I',bang)::regclass
                      AND polname='kiem_toan_ven_phap_nhan') THEN
            EXECUTE format('CREATE POLICY kiem_toan_ven_phap_nhan ON danh_muc.%I FOR SELECT TO %I
                USING (phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))',bang,kiem);
        END IF;
    END LOOP;
    CREATE INDEX IF NOT EXISTS lien_ket_nghia_vu ON danh_muc.lien_ket_chung_tu
        (phap_nhan_id,module_nghia_vu,loai_nghia_vu,nghia_vu_id) WHERE trang_thai<>'HUY';
    CREATE INDEX IF NOT EXISTS phan_bo_nghia_vu ON danh_muc.lien_ket_phan_bo
        (phap_nhan_id,module_nghia_vu,loai_nghia_vu,nghia_vu_id) WHERE trang_thai='HIEU_LUC';

    EXECUTE format('SET LOCAL ROLE %I',kiem);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);
    ALTER DEFAULT PRIVILEGES IN SCHEMA danh_muc REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    CREATE OR REPLACE FUNCTION danh_muc.khoa_lien_ket_noi_bo(p_pn uuid,p_ids uuid[] DEFAULT '{}') RETURNS void
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ct uuid;
    BEGIN
        IF current_setting('transaction_isolation')<>'read committed' THEN
            RAISE EXCEPTION 'LIEN_KET_CAN_READ_COMMITTED' USING ERRCODE='25000';
        END IF;
        IF NOT EXISTS(SELECT FROM loi.mtq_phien_rls() x WHERE x.phap_nhan_id=p_pn) THEN
            RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array('lien_ket_pn',p_pn)::text,13));
        -- Advisory thay FOR UPDATE: role kiem chi co SELECT, khong DML.
        FOR ct IN SELECT id FROM danh_muc.chung_tu WHERE phap_nhan_id=p_pn
            UNION SELECT id FROM unnest(p_ids) id WHERE id IS NOT NULL ORDER BY id LOOP
            PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array('lien_ket_ct',ct)::text,13));
        END LOOP;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION danh_muc.tong_nghia_vu_noi_bo(p_pn uuid,p_module text,p_loai text,p_id uuid)
    RETURNS numeric LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT coalesce(sum(tien),0) FROM (
            SELECT k.so_tien_khop_minor AS tien FROM danh_muc.lien_ket_chung_tu k
              WHERE k.phap_nhan_id=p_pn AND k.trang_thai<>'HUY' AND k.muc_dich_lien_ket='MONEY'
                AND k.mo_hinh_phan_bo='DIRECT'
                AND (k.module_nghia_vu,k.loai_nghia_vu,k.nghia_vu_id)=(p_module,p_loai,p_id)
            UNION ALL
            SELECT c.so_tien_minor FROM danh_muc.lien_ket_phan_bo c
              JOIN danh_muc.lien_ket_chung_tu k ON (k.id,k.phap_nhan_id)=(c.lien_ket_id,c.phap_nhan_id)
              WHERE c.phap_nhan_id=p_pn AND k.trang_thai<>'HUY' AND c.trang_thai='HIEU_LUC'
                AND k.muc_dich_lien_ket='MONEY' AND k.mo_hinh_phan_bo='CHILD'
                AND (c.module_nghia_vu,c.loai_nghia_vu,c.nghia_vu_id)=(p_module,p_loai,p_id)
        ) t
    $ham$;
    CREATE OR REPLACE FUNCTION danh_muc.kiem_tien_chung_tu_noi_bo(p_pn uuid,p_ids uuid[]) RETURNS boolean
    LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT NOT EXISTS(SELECT FROM danh_muc.chung_tu d WHERE d.phap_nhan_id=p_pn AND d.id=ANY(p_ids)
            AND EXISTS(SELECT FROM danh_muc.lien_ket_chung_tu k WHERE k.phap_nhan_id=p_pn
                AND k.chung_tu_a_id=d.id AND k.trang_thai<>'HUY' AND k.muc_dich_lien_ket='MONEY')
            AND (d.so_tien_minor IS NULL OR d.hieu_luc_den IS NOT NULL OR d.so_tien_minor < (
                SELECT coalesce(sum(tien),0) FROM (
                    -- Nguon tien la A; B la chung tu can cu, khong tru tien B lan hai.
                    SELECT k.so_tien_khop_minor AS tien FROM danh_muc.lien_ket_chung_tu k
                      WHERE k.phap_nhan_id=p_pn AND d.id=k.chung_tu_a_id
                        AND k.trang_thai<>'HUY' AND k.muc_dich_lien_ket='MONEY' AND k.mo_hinh_phan_bo='DIRECT'
                    UNION ALL
                    SELECT c.so_tien_minor FROM danh_muc.lien_ket_phan_bo c
                      JOIN danh_muc.lien_ket_chung_tu k ON (k.id,k.phap_nhan_id)=(c.lien_ket_id,c.phap_nhan_id)
                      WHERE k.phap_nhan_id=p_pn AND d.id=k.chung_tu_a_id
                        AND k.trang_thai<>'HUY' AND c.trang_thai='HIEU_LUC'
                        AND k.muc_dich_lien_ket='MONEY' AND k.mo_hinh_phan_bo='CHILD'
                ) t)))
    $ham$;
    FOR ham IN SELECT oid::regprocedure AS ck FROM pg_proc WHERE pronamespace='danh_muc'::regnamespace
        AND proname IN ('khoa_lien_ket_noi_bo','tong_nghia_vu_noi_bo','kiem_tien_chung_tu_noi_bo') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I',ham.ck,login,chay);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,chu);
    END LOOP;

    EXECUTE format('SET LOCAL ROLE %I',chu);
    EXECUTE format('REVOKE CREATE ON SCHEMA danh_muc FROM %I',kiem);
    -- Thay trigger 012 bang guard hep: SUA = HUY cu + INSERT moi.
    -- CREATE OR REPLACE TRIGGER khong xoa doi tuong/lich su.
    CREATE OR REPLACE FUNCTION danh_muc.lien_ket_chi_huy() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF OLD.trang_thai='HUY' OR NEW.trang_thai<>'HUY'
           OR (to_jsonb(NEW)-ARRAY['trang_thai','huy_boi','huy_luc','ly_do_huy']) IS DISTINCT FROM
              (to_jsonb(OLD)-ARRAY['trang_thai','huy_boi','huy_luc','ly_do_huy']) THEN
            RAISE EXCEPTION 'LIEN_KET_BAT_BIEN' USING ERRCODE='42501';
        END IF;
        RETURN NEW;
    END;
    $ham$;
    CREATE OR REPLACE TRIGGER danh_muc_khong_sua BEFORE UPDATE ON danh_muc.lien_ket_chung_tu
        FOR EACH ROW EXECUTE FUNCTION danh_muc.lien_ket_chi_huy();
    CREATE OR REPLACE TRIGGER danh_muc_khong_sua BEFORE UPDATE ON danh_muc.lien_ket_phan_bo
        FOR EACH ROW EXECUTE FUNCTION danh_muc.lien_ket_chi_huy();

    CREATE OR REPLACE FUNCTION danh_muc.lien_ket_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_lenh text,p_id uuid,p_data jsonb,p_contract text DEFAULT '1',p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE
        ai uuid; cu danh_muc.lien_ket_chung_tu; moi uuid; a uuid; b uuid;
        ids uuid[]; dich jsonb; tap jsonb := '[]'; x jsonb; kq jsonb;
        tt text; thang smallint; ky_ct text; n integer;
    BEGIN
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF p_id IS NULL OR p_contract IS NULL OR btrim(p_contract)=''
           OR p_lenh IS NULL OR p_lenh NOT IN ('LAP','SUA','HUY')
           OR split_part(p_hd,':',3) IS DISTINCT FROM p_lenh
           OR jsonb_typeof(p_data) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
        END IF;
        PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,
            jsonb_build_object('bang','danh_muc.lien_ket_chung_tu','id',p_id),p_contract,'cho_ghi',p_viec,p_the_he);
        PERFORM danh_muc.khoa_lien_ket_noi_bo(p_pn,ARRAY[
            (p_data->>'chung_tu_a_id')::uuid,(p_data->>'chung_tu_b_id')::uuid]);
        IF p_lenh<>'LAP' THEN
            SELECT * INTO cu FROM danh_muc.lien_ket_chung_tu WHERE id=p_id AND phap_nhan_id=p_pn;
            IF NOT FOUND OR cu.trang_thai='HUY' THEN
                RAISE EXCEPTION 'LIEN_KET_XUNG_DOT' USING ERRCODE='P0001';
            END IF;
            IF coalesce(btrim(p_data->>'ly_do_huy'),'')='' THEN
                RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
            END IF;
            ids := ARRAY[cu.chung_tu_a_id,cu.chung_tu_b_id];
            IF cu.mo_hinh_phan_bo='DIRECT' THEN
                tap := jsonb_build_array(to_jsonb(cu));
            ELSE
                SELECT coalesce(jsonb_agg(to_jsonb(c)),'[]') INTO tap FROM danh_muc.lien_ket_phan_bo c
                    WHERE c.lien_ket_id=p_id AND c.phap_nhan_id=p_pn AND c.trang_thai='HIEU_LUC';
            END IF;
        END IF;
        IF p_lenh='HUY' THEN
            IF EXISTS(SELECT FROM jsonb_object_keys(p_data) k WHERE k<>'ly_do_huy') THEN
                RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
            END IF;
        ELSE
            IF EXISTS(SELECT FROM jsonb_object_keys(p_data) k WHERE NOT k=ANY(ARRAY[
                'chung_tu_a_id','chung_tu_b_id','loai','mo_hinh_phan_bo','module_nghia_vu','loai_nghia_vu',
                'nghia_vu_id','phien_ban_can_cu_id','ma_bam_phien_ban_can_cu','so_tien_khop_minor',
                'tien_te','thang_tien','phan_bo','id_moi','ly_do_huy']))
               OR coalesce(btrim(p_data->>'loai'),'')=''
               OR coalesce(p_data->>'mo_hinh_phan_bo','') NOT IN ('DIRECT','CHILD')
               OR jsonb_typeof(p_data->'thang_tien') IS DISTINCT FROM 'number'
               OR coalesce(p_data->>'thang_tien','') !~ '^(0|[1-9]|1[0-2])$'
               OR coalesce(p_data->>'tien_te','') !~ '^[A-Z]{3}$' THEN
                RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
            END IF;
            a := (p_data->>'chung_tu_a_id')::uuid; b := (p_data->>'chung_tu_b_id')::uuid;
            IF a IS NULL OR a=b THEN RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023'; END IF;
            ids := coalesce(ids,'{}')||ARRAY[a,b];
            tt := p_data->>'tien_te'; thang := (p_data->>'thang_tien')::smallint;
            SELECT count(*) INTO n FROM danh_muc.chung_tu WHERE id=ANY(ARRAY[a,b]) AND phap_nhan_id=p_pn
                AND hieu_luc_den IS NULL AND ((id=a AND so_tien_minor IS NOT NULL AND tien_te=tt AND thang_tien=thang)
                    OR (id=b AND (so_tien_minor IS NULL OR (tien_te=tt AND thang_tien=thang))));
            IF n<>CASE WHEN b IS NULL THEN 1 ELSE 2 END THEN
                RAISE EXCEPTION 'LIEN_KET_PHAM_VI' USING ERRCODE='42501';
            END IF;
            moi := CASE WHEN p_lenh='LAP' THEN p_id ELSE (p_data->>'id_moi')::uuid END;
            IF moi IS NULL OR (p_lenh='SUA' AND moi=p_id) THEN
                RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
            END IF;
            IF p_data->>'mo_hinh_phan_bo'='DIRECT' THEN
                IF p_data ? 'phan_bo' THEN RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023'; END IF;
                dich := jsonb_build_array(p_data);
            ELSE
                IF jsonb_typeof(p_data->'phan_bo') IS DISTINCT FROM 'array'
                   OR jsonb_array_length(p_data->'phan_bo')=0
                   OR p_data ?| ARRAY['module_nghia_vu','loai_nghia_vu','nghia_vu_id',
                       'phien_ban_can_cu_id','ma_bam_phien_ban_can_cu','so_tien_khop_minor'] THEN
                    RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
                END IF;
                dich := p_data->'phan_bo';
            END IF;
            FOR x IN SELECT value FROM jsonb_array_elements(dich) LOOP
                IF coalesce(x->>'module_nghia_vu','') !~ '^[a-z][a-z0-9_]{0,30}$'
                   OR coalesce(btrim(x->>'loai_nghia_vu'),'')=''
                   OR nullif(x->>'nghia_vu_id','') IS NULL OR nullif(x->>'phien_ban_can_cu_id','') IS NULL
                   OR coalesce(x->>'ma_bam_phien_ban_can_cu','') !~ '^[0-9a-f]{64}$'
                   OR jsonb_typeof(x->CASE WHEN p_data->>'mo_hinh_phan_bo'='DIRECT' THEN 'so_tien_khop_minor' ELSE 'so_tien_minor' END) IS DISTINCT FROM 'string'
                   OR coalesce(x->>CASE WHEN p_data->>'mo_hinh_phan_bo'='DIRECT' THEN 'so_tien_khop_minor' ELSE 'so_tien_minor' END,'') !~ '^[1-9][0-9]{0,37}$' THEN
                    RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
                END IF;
                PERFORM (x->>'nghia_vu_id')::uuid,(x->>'phien_ban_can_cu_id')::uuid;
                IF p_data->>'mo_hinh_phan_bo'='CHILD' THEN
                    IF EXISTS(SELECT FROM jsonb_object_keys(x) k WHERE NOT k=ANY(ARRAY['dich_logic_id',
                        'module_nghia_vu','loai_nghia_vu','nghia_vu_id','cau_phan','phien_ban_can_cu_id',
                        'ma_bam_phien_ban_can_cu','so_tien_minor']))
                       OR nullif(x->>'dich_logic_id','') IS NULL
                       OR coalesce(x->>'cau_phan','') NOT IN ('GOC','LAI','PHI','GIAI_NGAN') THEN
                        RAISE EXCEPTION 'LIEN_KET_DAU_VAO' USING ERRCODE='22023';
                    END IF;
                    x := x||jsonb_build_object('tien_te',tt,'thang_tien',thang);
                END IF;
                tap := tap||jsonb_build_array(x);
            END LOOP;
        END IF;
        FOR ky_ct IN SELECT DISTINCT ky FROM danh_muc.chung_tu WHERE id=ANY(ids) AND phap_nhan_id=p_pn ORDER BY ky LOOP
            PERFORM danh_muc.kiem_khoa_ky(p_pn,ky_ct);
        END LOOP;
        -- Cung thu tu cho ca dich cu va moi. Khong tin bo ba caller truoc resolver.
        FOR x IN SELECT value FROM jsonb_array_elements(tap)
            ORDER BY value->>'module_nghia_vu',value->>'loai_nghia_vu',value->>'nghia_vu_id' LOOP
            kq := loi.goi_nghia_vu_noi_bo(p_ma,p_module,p_pn,p_hd,x||'{"giai_doan":"KHOA"}',p_contract,p_viec,p_the_he);
            IF kq->>'ket_luan'='CHO' THEN RETURN kq; END IF;
        END LOOP;
        -- Subtransaction: neu kiem cuoi CHO thi hoan tac ca HUY cu/INSERT moi.
        BEGIN
            IF p_lenh<>'LAP' THEN
                UPDATE danh_muc.lien_ket_chung_tu SET trang_thai='HUY',huy_boi=ai,huy_luc=clock_timestamp(),
                    ly_do_huy=p_data->>'ly_do_huy' WHERE id=p_id AND phap_nhan_id=p_pn;
                UPDATE danh_muc.lien_ket_phan_bo SET trang_thai='HUY',huy_boi=ai,huy_luc=clock_timestamp(),
                    ly_do_huy=p_data->>'ly_do_huy' WHERE lien_ket_id=p_id AND phap_nhan_id=p_pn AND trang_thai='HIEU_LUC';
            END IF;
            IF p_lenh<>'HUY' THEN
                INSERT INTO danh_muc.lien_ket_chung_tu(id,phap_nhan_id,chung_tu_a_id,chung_tu_b_id,loai,
                    muc_dich_lien_ket,mo_hinh_phan_bo,module_nghia_vu,loai_nghia_vu,nghia_vu_id,
                    phien_ban_can_cu_id,ma_bam_phien_ban_can_cu,so_tien_khop_minor,tien_te,thang_tien,trang_thai,tao_boi)
                VALUES(moi,p_pn,a,b,p_data->>'loai','MONEY',p_data->>'mo_hinh_phan_bo',
                    p_data->>'module_nghia_vu',p_data->>'loai_nghia_vu',(p_data->>'nghia_vu_id')::uuid,
                    (p_data->>'phien_ban_can_cu_id')::uuid,p_data->>'ma_bam_phien_ban_can_cu',
                    (p_data->>'so_tien_khop_minor')::numeric,tt,thang,'DA_KHOP',ai);
                IF p_data->>'mo_hinh_phan_bo'='CHILD' THEN
                    FOR x IN SELECT value FROM jsonb_array_elements(p_data->'phan_bo') LOOP
                        INSERT INTO danh_muc.lien_ket_phan_bo(phap_nhan_id,lien_ket_id,dich_logic_id,module_nghia_vu,
                            loai_nghia_vu,nghia_vu_id,cau_phan,phien_ban_can_cu_id,ma_bam_phien_ban_can_cu,
                            so_tien_minor,tien_te,thang_tien,tao_boi)
                        VALUES(p_pn,moi,(x->>'dich_logic_id')::uuid,x->>'module_nghia_vu',x->>'loai_nghia_vu',
                            (x->>'nghia_vu_id')::uuid,x->>'cau_phan',(x->>'phien_ban_can_cu_id')::uuid,
                            x->>'ma_bam_phien_ban_can_cu',(x->>'so_tien_minor')::numeric,tt,thang,ai);
                    END LOOP;
                END IF;
            END IF;
            IF NOT danh_muc.kiem_tien_chung_tu_noi_bo(p_pn,ids) THEN
                RAISE EXCEPTION 'LIEN_KET_VUOT_CHUNG_TU' USING ERRCODE='P0001';
            END IF;
            FOR x IN SELECT value FROM jsonb_array_elements(tap)
                ORDER BY value->>'module_nghia_vu',value->>'loai_nghia_vu',value->>'nghia_vu_id' LOOP
                kq := loi.goi_nghia_vu_noi_bo(p_ma,p_module,p_pn,p_hd,x||'{"giai_doan":"KIEM"}',p_contract,p_viec,p_the_he);
                IF kq->>'ket_luan'='CHO' THEN RAISE EXCEPTION 'CHO' USING ERRCODE='P0013'; END IF;
            END LOOP;
        EXCEPTION WHEN SQLSTATE 'P0013' THEN RETURN kq;
        END;
        RETURN jsonb_build_object('ket_luan','DAT','id',coalesce(moi,p_id));
    END;
    $ham$;
    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc WHERE pronamespace='danh_muc'::regnamespace
        AND proname IN ('lien_ket_v2','lien_ket_chi_huy') LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I',ham.ck,chay,login);
        IF ham.proname='lien_ket_v2' THEN EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login); END IF;
    END LOOP;
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
