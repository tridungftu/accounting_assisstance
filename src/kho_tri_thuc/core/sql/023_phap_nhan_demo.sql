-- DM-1 / CD-044. Caller giu transaction; chi provisioning DEMO/test PG16+.
-- Vai kiem chi doc de kiem toan ven, khong login/membership/BYPASSRLS.
-- Cac bang pham vi cai SAU 023 phai duoc Module Manager gan cung trigger
-- va ACL/policy kiem toan ven nay; khong tao FK phu thuoc module tuy chon.
DO $do$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt||'vai_doi_cau_truc_loi';
    kiem text := tt||'vai_kiem_demo';
    b record; cot text;
BEGIN
    IF (tt<>'' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tt||'vai_doi_cau_truc_loi_tai_lieu')>63
       OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'DM-1: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR to_regprocedure('loi_tai_lieu.ghi_ket_qua_v2(text,text,uuid,text,uuid,jsonb,uuid,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'DM-1: Can lead, ap chuoi SQL 001..020 truoc';
    END IF;
    PERFORM set_config('kho_tri_thuc.dm1_vai_cu',current_setting('role'),true);
    PERFORM set_config('kho_tri_thuc.dm1_duong_cu',current_setting('search_path'),true);
    IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname=kiem) THEN
        EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION',kiem);
    END IF;
    IF EXISTS(SELECT FROM pg_roles WHERE rolname=kiem AND
        (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication))
       OR EXISTS(SELECT FROM pg_auth_members WHERE roleid=(SELECT oid FROM pg_roles WHERE rolname=kiem)
                  OR member=(SELECT oid FROM pg_roles WHERE rolname=kiem)) THEN
        RAISE EXCEPTION 'DM-1: Can lead, vai kiem sai thuoc tinh/membership';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    ALTER TABLE loi.phap_nhan ADD COLUMN IF NOT EXISTS la_demo boolean NOT NULL DEFAULT false;
    ALTER TABLE loi.phap_nhan ADD COLUMN IF NOT EXISTS phien_ban_dong bigint NOT NULL DEFAULT 1 CHECK(phien_ban_dong>0);
    IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid='loi.phap_nhan'::regclass AND polname='demo_chu_doi_co') THEN
        EXECUTE format('CREATE POLICY demo_chu_doi_co ON loi.phap_nhan FOR UPDATE TO %I USING(true) WITH CHECK(true)',chu);
    END IF;
    EXECUTE format('GRANT USAGE,CREATE ON SCHEMA loi TO %I',kiem);
    -- Quay ve provisioning de cap SELECT/policy theo dung owner moi khoi.
    PERFORM set_config('role',current_setting('kho_tri_thuc.dm1_vai_cu'),true);
    FOR b IN SELECT c.oid,n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind IN ('r','p') AND (n.nspname IN ('loi','loi_tai_lieu','danh_muc')
            OR n.nspname ~ '^(mod_|cong_bo_)')
          AND (c.oid='loi.phap_nhan'::regclass OR EXISTS(SELECT FROM pg_attribute a
              WHERE a.attrelid=c.oid AND a.attname='phap_nhan_id' AND NOT a.attisdropped))
        ORDER BY c.oid LOOP
        IF EXISTS(SELECT FROM pg_policy WHERE polrelid=b.oid AND NOT polpermissive) THEN
            RAISE EXCEPTION 'DM-1: Can lead, review restrictive policy';
        END IF;
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I',b.nspname,kiem);
        SELECT string_agg(format('%I',attname),',' ORDER BY attnum) INTO cot
            FROM pg_attribute WHERE attrelid=b.oid AND attnum>0 AND NOT attisdropped
              AND (attname IN ('id','phap_nhan_id') OR (b.oid='loi.phap_nhan'::regclass AND attname='la_demo'));
        -- Chi ID/phap nhan/co, khong cap doc noi dung hay ma bam phien.
        EXECUTE format('GRANT SELECT (%s) ON %I.%I TO %I',cot,b.nspname,b.relname,kiem);
        IF NOT EXISTS(SELECT FROM pg_policy WHERE polrelid=b.oid AND polname='demo_kiem_noi_bo') THEN
            EXECUTE format('CREATE POLICY demo_kiem_noi_bo ON %I.%I FOR SELECT TO %I USING(true)',b.nspname,b.relname,kiem);
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',kiem);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);
END;
$do$;

-- Chi tra ma loi, khong tra cac dong ngoai pham vi caller. Khoa chia se
-- voi trigger ghi; doi co lay khoa doc quyen. READ COMMITTED doc moi sau cho.
CREATE OR REPLACE FUNCTION loi.demo_kiem_tap_noi_bo(p_ids uuid[]) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE pn uuid; co boolean; dau boolean;
BEGIN
    IF current_setting('transaction_isolation')<>'read committed' THEN
        RAISE EXCEPTION 'DEMO_CAN_READ_COMMITTED' USING ERRCODE='25000';
    END IF;
    FOR pn IN SELECT DISTINCT id FROM unnest(p_ids) id WHERE id IS NOT NULL ORDER BY id LOOP
        PERFORM pg_advisory_xact_lock_shared(hashtextextended('demo|'||pn::text,23));
        SELECT la_demo INTO co FROM loi.phap_nhan WHERE id=pn;
        IF NOT FOUND THEN RAISE EXCEPTION 'DEMO_PHAP_NHAN' USING ERRCODE='23503'; END IF;
        IF dau IS NOT NULL AND dau IS DISTINCT FROM co THEN
            RAISE EXCEPTION 'DEMO_LIEN_KET_CHEO' USING ERRCODE='23514';
        END IF;
        dau := co;
    END LOOP;
END;
$ham$;
REVOKE ALL ON FUNCTION loi.demo_kiem_tap_noi_bo(uuid[]) FROM PUBLIC;

-- Kiem FK cac dau lien ket bang ID truoc khi FK ghep tu choi khac PN.
-- Bao phu A/B lien ket tien, phan bo, nguon ket qua va cong bo. Khong doc
-- noi dung nghiep vu; khoa/ten cot chi lay tu catalog, khong tu client.
CREATE OR REPLACE FUNCTION loi.demo_kiem_lien_ket() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE f record; dich uuid; ids uuid[]; j jsonb := to_jsonb(NEW);
BEGIN
    ids := ARRAY[(j->>'phap_nhan_id')::uuid];
    IF TG_OP='UPDATE' THEN
        ids := array_append(ids,(to_jsonb(OLD)->>'phap_nhan_id')::uuid);
    END IF;
    FOR f IN SELECT n.nspname,c.relname,a.attname AS cot_nguon,r.attname AS cot_dich
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.confrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN LATERAL unnest(k.conkey,k.confkey) z(nguon,dich)
        JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=z.nguon
        JOIN pg_attribute r ON r.attrelid=k.confrelid AND r.attnum=z.dich
        WHERE k.contype='f' AND k.conrelid=TG_RELID AND r.attname='id'
          AND EXISTS(SELECT FROM pg_attribute x WHERE x.attrelid=k.confrelid
              AND x.attname='phap_nhan_id' AND NOT x.attisdropped)
        ORDER BY k.oid LOOP
        IF j->>f.cot_nguon IS NOT NULL THEN
            EXECUTE format('SELECT phap_nhan_id FROM %I.%I WHERE %I=$1',f.nspname,f.relname,f.cot_dich)
                INTO dich USING (j->>f.cot_nguon)::uuid;
            IF dich IS NOT NULL THEN ids := array_append(ids,dich); END IF;
        END IF;
    END LOOP;
    IF TG_TABLE_SCHEMA='loi' AND TG_TABLE_NAME='mtq_pham_vi' AND j->>'loai'='PHAP_NHAN' THEN
        ids := array_append(ids,(j->>'khoa')::uuid);
    END IF;
    PERFORM loi.demo_kiem_tap_noi_bo(ids);
    RETURN NEW;
END;
$ham$;
REVOKE ALL ON FUNCTION loi.demo_kiem_lien_ket() FROM PUBLIC;

CREATE OR REPLACE FUNCTION loi.demo_chan_doi_co() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE b record; co_du_lieu boolean;
BEGIN
    IF NEW.la_demo IS NOT DISTINCT FROM OLD.la_demo THEN RETURN NEW; END IF;
    IF current_setting('transaction_isolation')<>'read committed' THEN
        RAISE EXCEPTION 'DEMO_CAN_READ_COMMITTED' USING ERRCODE='25000';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('demo|'||OLD.id::text,23));
    -- Khong coi thanh vien, phien va audit la du lieu nghiep vu. Cau hinh MTQ,
    -- cong tac va du lieu da het hieu luc VAN khoa co, khong chi dong dang dung.
    FOR b IN SELECT c.oid,n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind IN ('r','p') AND (n.nspname IN ('loi','loi_tai_lieu','danh_muc')
            OR n.nspname ~ '^(mod_|cong_bo_)')
          AND EXISTS(SELECT FROM pg_attribute a WHERE a.attrelid=c.oid
              AND a.attname='phap_nhan_id' AND NOT a.attisdropped)
          AND NOT (n.nspname='loi' AND c.relname IN
              ('phan_quyen','phien_xac_thuc','nhat_ky_kiem_toan','mtq_thay_doi','mtq_tu_choi'))
        ORDER BY c.oid LOOP
        -- Bang moi chua gan trigger/ACL hoac policy co the che dong => fail closed.
        IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid=b.oid
            AND tgname='aaa_demo_lien_ket' AND tgenabled='O')
           OR EXISTS(SELECT FROM pg_policy WHERE polrelid=b.oid AND NOT polpermissive) THEN
            RAISE EXCEPTION 'DEMO_SCHEMA_CHUA_BAO_VE' USING ERRCODE='23514';
        END IF;
        EXECUTE format('SELECT EXISTS(SELECT FROM %I.%I WHERE phap_nhan_id=$1)',b.nspname,b.relname)
            INTO co_du_lieu USING OLD.id;
        IF co_du_lieu THEN RAISE EXCEPTION 'DEMO_DA_CO_DU_LIEU' USING ERRCODE='23514'; END IF;
    END LOOP;
    RETURN NEW;
END;
$ham$;
REVOKE ALL ON FUNCTION loi.demo_chan_doi_co() FROM PUBLIC;

DO $do$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt||'vai_doi_cau_truc_loi'; b record;
BEGIN
    PERFORM set_config('role',current_setting('kho_tri_thuc.dm1_vai_cu'),true);
    FOR b IN SELECT c.oid,n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind IN ('r','p') AND (n.nspname IN ('loi','loi_tai_lieu','danh_muc')
            OR n.nspname ~ '^(mod_|cong_bo_)')
          AND EXISTS(SELECT FROM pg_attribute a WHERE a.attrelid=c.oid
              AND a.attname='phap_nhan_id' AND NOT a.attisdropped)
          AND NOT (n.nspname='loi' AND c.relname IN
              ('phan_quyen','phien_xac_thuc','nhat_ky_kiem_toan','mtq_thay_doi','mtq_tu_choi'))
        ORDER BY c.oid LOOP
        EXECUTE format('CREATE OR REPLACE TRIGGER aaa_demo_lien_ket BEFORE INSERT OR UPDATE ON %I.%I
            FOR EACH ROW EXECUTE FUNCTION loi.demo_kiem_lien_ket()',b.nspname,b.relname);
    END LOOP;
    -- Trigger doi co chi UPDATE: INSERT khong co OLD.
    CREATE OR REPLACE TRIGGER aaa_demo_giu_pham_vi BEFORE UPDATE OF la_demo ON loi.phap_nhan
        FOR EACH ROW EXECUTE FUNCTION loi.demo_chan_doi_co();
    EXECUTE format('REVOKE CREATE ON SCHEMA loi FROM %I',tt||'vai_kiem_demo');
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.demo_kiem_tap_noi_bo(uuid[]) TO %I',chu);
    EXECUTE format('SET LOCAL ROLE %I',chu);
END;
$do$;

CREATE OR REPLACE FUNCTION loi.phap_nhan_dat_demo(p_ma text,p_pn uuid,p_la_demo boolean,
    p_phien_ban bigint,p_request uuid) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE ai uuid; moi loi.phap_nhan;
BEGIN
    PERFORM pg_advisory_xact_lock_shared(742601,1);
    SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,'core',p_pn,'CORE:DEMO:SUA',NULL,NULL);
    IF ai IS NULL OR NOT EXISTS(SELECT FROM loi.mtq_admin WHERE nguoi_dung_id=ai AND thu_hoi_luc IS NULL) THEN
        RAISE EXCEPTION 'DEMO_CHI_ADMIN' USING ERRCODE='42501';
    END IF;
    IF p_la_demo IS NULL OR p_phien_ban IS NULL OR p_phien_ban<1 OR p_request IS NULL THEN
        RAISE EXCEPTION 'DEMO_DAU_VAO' USING ERRCODE='22023';
    END IF;
    IF current_setting('transaction_isolation')<>'read committed' THEN
        RAISE EXCEPTION 'DEMO_CAN_READ_COMMITTED' USING ERRCODE='25000';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('demo|'||p_pn::text,23));
    UPDATE loi.phap_nhan SET la_demo=p_la_demo,phien_ban_dong=phien_ban_dong+1
        WHERE id=p_pn AND phien_ban_dong=p_phien_ban RETURNING * INTO moi;
    IF NOT FOUND THEN RAISE EXCEPTION 'DEMO_CAS' USING ERRCODE='40001'; END IF;
    PERFORM loi.ghi_kiem_toan('CORE:DEMO:SUA','phap_nhan_demo',p_pn,'DAT',p_ma,'core',p_pn,p_request);
    RETURN jsonb_build_object('id',moi.id,'la_demo',moi.la_demo,'row_version',moi.phien_ban_dong::text);
END;
$ham$;
REVOKE ALL ON FUNCTION loi.phap_nhan_dat_demo(text,uuid,boolean,bigint,uuid) FROM PUBLIC;

-- INVOKER: giu RLS xac minh phien, khong mo rong pham vi nguoi dang nhap.
CREATE OR REPLACE FUNCTION loi.phap_nhan_pham_vi(p_gom_demo boolean DEFAULT false)
RETURNS SETOF loi.phap_nhan LANGUAGE sql STABLE SECURITY INVOKER
SET search_path=pg_catalog,pg_temp AS $ham$
    SELECT p.* FROM loi.phap_nhan p WHERE NOT p.la_demo OR p_gom_demo IS TRUE
$ham$;
REVOKE ALL ON FUNCTION loi.phap_nhan_pham_vi(boolean) FROM PUBLIC;

-- Nang resolver Core G2-06, giu binding/ABI; kiem tap o CSDL truoc quyet dinh
-- MTQ, ke ca khi ma tran tat. Khong sua migration 006 da phat hanh.
CREATE OR REPLACE FUNCTION loi.mtq_giai_doi_tuong_tap(
    p_ma text,p_module text,p_pn uuid,p_hanh_dong text,p_doi_tuong jsonb,
    p_phien_ban_contract text,p_viec_id uuid,p_the_he bigint
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE binding jsonb; h loi.dang_ky_ham_module; tap jsonb; pn uuid;
BEGIN
    IF NOT EXISTS(SELECT FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hanh_dong,p_viec_id,p_the_he)) THEN
        RAISE EXCEPTION 'Phiên không hợp lệ' USING ERRCODE='42501';
    END IF;
    IF p_module='core' AND p_hanh_dong IN
        ('CORE:DANH_TINH:XEM','CORE:DANH_TINH:LAP','CORE:DANH_TINH:SUA')
       AND p_doi_tuong->>'bang'='loi.phap_nhan' THEN
        SELECT id INTO pn FROM loi.phap_nhan WHERE id=(p_doi_tuong->>'id')::uuid;
        IF pn IS DISTINCT FROM p_pn THEN RETURN NULL; END IF;
        RETURN jsonb_build_array(jsonb_build_object('pn',pn,'hop_le',true,'loai','DANH_TINH'));
    END IF;
    binding := loi.phan_giai_ham_module(p_module,'resolver_mtq',p_phien_ban_contract,
        p_ma,p_pn,p_hanh_dong,p_viec_id,p_the_he);
    IF binding->>'ket_luan'='CHO' THEN RETURN NULL; END IF;
    h := jsonb_populate_record(NULL::loi.dang_ky_ham_module,binding->'binding');
    IF NOT EXISTS(SELECT FROM pg_proc WHERE oid=to_regprocedure(h.chu_ky)
        AND proargtypes='25 2950 25 3802 2950 20'::oidvector
        AND prorettype='jsonb'::regtype AND NOT proretset) THEN
        RAISE EXCEPTION 'Chữ ký resolver không hợp lệ' USING ERRCODE='42501';
    END IF;
    EXECUTE format('SELECT %I.%I($1,$2,$3,$4,$5,$6)',h.ten_schema,h.ten_ham)
        INTO tap USING p_ma,p_pn,p_hanh_dong,p_doi_tuong,p_viec_id,p_the_he;
    IF jsonb_typeof(tap)='array' THEN
        -- MTQ chay truoc khoa_lien_ket_noi_bo trong cua V2. Giu ma guard
        -- G2-13 cho ghi lien ket / het hieu luc chung tu, truoc moi doc DEMO.
        IF current_setting('transaction_isolation')<>'read committed'
           AND ((p_doi_tuong->>'bang'='danh_muc.lien_ket_chung_tu'
                 AND split_part(p_hanh_dong,':',3) IN ('LAP','SUA','HUY'))
                OR (p_doi_tuong->>'bang'='danh_muc.chung_tu'
                    AND split_part(p_hanh_dong,':',3)='SUA')) THEN
            RAISE EXCEPTION 'LIEN_KET_CAN_READ_COMMITTED' USING ERRCODE='25000';
        END IF;
        PERFORM loi.demo_kiem_tap_noi_bo(ARRAY(SELECT (value->>'pn')::uuid FROM jsonb_array_elements(tap)));
    END IF;
    RETURN tap;
END;
$ham$;
REVOKE ALL ON FUNCTION loi.mtq_giai_doi_tuong_tap(text,text,uuid,text,jsonb,text,uuid,bigint) FROM PUBLIC;

DO $do$
DECLARE tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
BEGIN
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.phap_nhan_dat_demo(text,uuid,boolean,bigint,uuid),
        loi.phap_nhan_pham_vi(boolean) TO %I',tt||'vai_chay_loi');
    PERFORM set_config('search_path',current_setting('kho_tri_thuc.dm1_duong_cu'),true);
    PERFORM set_config('role',current_setting('kho_tri_thuc.dm1_vai_cu'),true);
END;
$do$;
