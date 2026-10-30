-- G2-15: nang XS-1/M0052 (k2/sql_bus_su_kien.py, ha_tang/bus_su_kien.py).
-- Giu outbox, dedupe, khoa inbox va ACK cung tx; khong migrate bus cu.
-- ACK la dong rieng bat bien. G2-29 don theo policy 30 ngay va giu dau replay.
-- Khong kich hoat contract nghiep vu con cho Anh (ke ca moc_da_xay_ra).
DO $$
DECLARE
    tien_to constant text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu constant text := tien_to || 'vai_doi_cau_truc_loi';
    chay constant text := tien_to || 'vai_chay_loi';
    login constant text := tien_to || 'dang_nhap_loi';
    cai_dat constant text := tien_to || 'dang_nhap_cai_dat';
    vai_cu constant text := current_setting('role');
    duong_cu constant text := current_setting('search_path');
    bang text;
    ham record;
BEGIN
    IF (tien_to<>'' AND tien_to !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tien_to || 'vai_doi_cau_truc_loi_tai_lieu')>63
       OR (tien_to<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-15: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR to_regclass('loi.hang_viec') IS NULL THEN
        RAISE EXCEPTION 'G2-15: Can lead, ap G2-01..14 truoc';
    END IF;
    FOREACH bang IN ARRAY ARRAY['su_kien','hop_nhan_su_kien','ack_su_kien','dang_ky_nhan_su_kien'] LOOP
        IF EXISTS (SELECT FROM pg_class WHERE oid=to_regclass('loi.'||bang)
            AND (relkind<>'r' OR pg_get_userbyid(relowner)<>chu)) THEN
            RAISE EXCEPTION 'G2-15: Can lead, bang sai owner/loai';
        END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);

    -- Subscription rieng: binding dung contract khong tu dong cap quyen doc bus.
    -- G2-25 goi cua cai dat sau khi kiem manifest.su_kien_nhan.
    CREATE TABLE IF NOT EXISTS loi.dang_ky_nhan_su_kien (
        module text NOT NULL,
        phien_ban_module text NOT NULL,
        loai text NOT NULL,
        phien_ban text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY (module,phien_ban_module,loai,phien_ban),
        FOREIGN KEY (loai,phien_ban,module,phien_ban_module)
            REFERENCES loi.module_dung_contract(ma_contract,phien_ban_contract,module,phien_ban_module)
    );
    CREATE TABLE IF NOT EXISTS loi.su_kien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES loi.phap_nhan(id),
        ben_phat text NOT NULL REFERENCES loi.module_danh_muc(ma),
        loai_su_kien text NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban>0),
        phien_ban_contract text NOT NULL CHECK (phien_ban_contract=phien_ban::text),
        khoa_chong_trung text NOT NULL CHECK (length(khoa_chong_trung) BETWEEN 1 AND 200
            AND khoa_chong_trung=btrim(khoa_chong_trung)),
        noi_dung_su_kien jsonb NOT NULL,
        ma_bam text NOT NULL CHECK (ma_bam ~ '^[0-9a-f]{64}$'),
        tao_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (phap_nhan_id,ben_phat,khoa_chong_trung),
        UNIQUE (phap_nhan_id,id),
        FOREIGN KEY (loai_su_kien,phien_ban_contract) REFERENCES loi.dang_ky_contract(ma,phien_ban)
    );
    CREATE INDEX IF NOT EXISTS su_kien_doc ON loi.su_kien(phap_nhan_id,tao_luc,id);
    CREATE TABLE IF NOT EXISTS loi.hop_nhan_su_kien (
        phap_nhan_id uuid NOT NULL,
        ben_nhan text NOT NULL REFERENCES loi.module_danh_muc(ma),
        su_kien_id uuid NOT NULL,
        nhan_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY (phap_nhan_id,ben_nhan,su_kien_id),
        FOREIGN KEY (phap_nhan_id,su_kien_id) REFERENCES loi.su_kien(phap_nhan_id,id)
    );
    CREATE TABLE IF NOT EXISTS loi.ack_su_kien (
        phap_nhan_id uuid NOT NULL,
        ben_nhan text NOT NULL,
        su_kien_id uuid NOT NULL,
        ack_boi uuid NOT NULL REFERENCES loi.nguoi_dung(id),
        ack_luc timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY (phap_nhan_id,ben_nhan,su_kien_id),
        FOREIGN KEY (phap_nhan_id,ben_nhan,su_kien_id)
            REFERENCES loi.hop_nhan_su_kien(phap_nhan_id,ben_nhan,su_kien_id)
    );
    FOREACH bang IN ARRAY ARRAY['su_kien','hop_nhan_su_kien','ack_su_kien','dang_ky_nhan_su_kien'] LOOP
        EXECUTE format('ALTER TABLE loi.%I ENABLE ROW LEVEL SECURITY',bang);
        EXECUTE format('ALTER TABLE loi.%I FORCE ROW LEVEL SECURITY',bang);
        IF NOT EXISTS (SELECT FROM pg_policy WHERE polrelid=format('loi.%I',bang)::regclass
            AND polname='su_kien_chu') THEN
            EXECUTE format('CREATE POLICY su_kien_chu ON loi.%I TO %I USING (true) WITH CHECK (true)',bang,chu);
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE loi.%I FROM PUBLIC,%I,%I,%I',bang,chay,login,cai_dat);
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=format('loi.%I',bang)::regclass
            AND tgname='su_kien_bat_bien') THEN
            EXECUTE format('CREATE TRIGGER su_kien_bat_bien BEFORE UPDATE OR DELETE OR TRUNCATE ON loi.%I
                FOR EACH STATEMENT EXECUTE FUNCTION loi.chan_sua_kiem_toan()',bang);
        END IF;
    END LOOP;

    -- Schema tham chieu dong: object dong, UUID don/mang; keyword chua ho tro
    -- bi tu choi (khong bo qua rang buoc JSON Schema va khong tai $ref ngoai).
    CREATE OR REPLACE FUNCTION loi.su_kien_payload(p jsonb,s jsonb) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE k text; v jsonb; d jsonb; item jsonb;
        mau constant text := '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
    BEGIN
        IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR p='{}'::jsonb
           OR s->>'type' IS DISTINCT FROM 'object' OR s->'additionalProperties' IS DISTINCT FROM 'false'::jsonb
           OR jsonb_typeof(s->'properties') IS DISTINCT FROM 'object'
           OR jsonb_typeof(s->'required') IS DISTINCT FROM 'array'
           OR (s-ARRAY['type','properties','required','additionalProperties','$schema','$id','title','description','examples'])<>'{}'::jsonb THEN
            RETURN false;
        END IF;
        FOR item IN SELECT value FROM jsonb_array_elements(s->'required') LOOP
            IF jsonb_typeof(item)<>'string' OR NOT (s->'properties' ? (item#>>'{}'))
                OR NOT (p ? (item#>>'{}')) THEN RETURN false; END IF;
        END LOOP;
        FOR k,d IN SELECT key,value FROM jsonb_each(s->'properties') LOOP
            IF jsonb_typeof(d)<>'object' THEN RETURN false; END IF;
            IF k ~ '^[a-z][a-z0-9_]*_id$' AND d->>'type'='string' AND d->>'format'='uuid'
               AND (d-ARRAY['type','format','title','description','examples'])='{}'::jsonb THEN
                NULL;
            ELSIF k ~ '^[a-z][a-z0-9_]*_ids$' AND d->>'type'='array'
               AND d->'items'='{"type":"string","format":"uuid"}'::jsonb
               AND (d-ARRAY['type','items','title','description','examples'])='{}'::jsonb THEN
                NULL;
            ELSE RETURN false;
            END IF;
        END LOOP;
        FOR k,v IN SELECT key,value FROM jsonb_each(p) LOOP
            d:=s->'properties'->k;
            IF d IS NULL THEN RETURN false; END IF;
            IF d->>'type'='string' THEN
                IF jsonb_typeof(v)<>'string' OR (v#>>'{}') !~* mau THEN RETURN false; END IF;
            ELSE
                IF jsonb_typeof(v)<>'array' THEN RETURN false; END IF;
                FOR item IN SELECT value FROM jsonb_array_elements(v) LOOP
                    IF jsonb_typeof(item)<>'string' OR (item#>>'{}') !~* mau THEN RETURN false; END IF;
                END LOOP;
            END IF;
        END LOOP;
        RETURN true;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.su_kien_dang_ky_nhan(p_module text,p_ban text,p_loai text,p_pb text)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_cai_dat') THEN
            RAISE EXCEPTION 'BUS_DANG_KY' USING ERRCODE='42501';
        END IF;
        IF NOT EXISTS (SELECT FROM loi.module_dung_contract b JOIN loi.dang_ky_contract c
            ON (c.ma,c.phien_ban)=(b.ma_contract,b.phien_ban_contract)
            WHERE (b.module,b.phien_ban_module,b.ma_contract,b.phien_ban_contract)=(p_module,p_ban,p_loai,p_pb)
                AND b.ket_thuc_luc IS NULL AND c.trang_thai='dang_dung') THEN
            RAISE EXCEPTION 'BUS_CONTRACT' USING ERRCODE='22023';
        END IF;
        INSERT INTO loi.dang_ky_nhan_su_kien(module,phien_ban_module,loai,phien_ban)
            VALUES (p_module,p_ban,p_loai,p_pb) ON CONFLICT DO NOTHING;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.su_kien_duoc_nhan(p_module text,p_loai text,p_pb text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
        SELECT EXISTS (SELECT FROM loi.dang_ky_nhan_su_kien n JOIN loi.module_dung_contract b
            ON (b.module,b.phien_ban_module,b.ma_contract,b.phien_ban_contract)=
               (n.module,n.phien_ban_module,n.loai,n.phien_ban)
            JOIN loi.phien_ban_module m ON (m.module,m.so_phien_ban)=(b.module,b.phien_ban_module)
            JOIN loi.dang_ky_contract c ON (c.ma,c.phien_ban)=(n.loai,n.phien_ban)
            WHERE n.module=p_module AND n.loai=p_loai AND n.phien_ban=p_pb
                AND b.ket_thuc_luc IS NULL AND m.trang_thai='da_cai' AND c.trang_thai='dang_dung')
    $ham$;
    CREATE OR REPLACE FUNCTION loi.su_kien_ngu_canh(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid,p_the_he bigint) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; q jsonb;
    BEGIN
        IF current_setting('transaction_isolation')<>'read committed' THEN
            RAISE EXCEPTION 'BUS_CAN_READ_COMMITTED' USING ERRCODE='25000';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai IS NULL OR split_part(p_hd,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'BUS_PHIEN' USING ERRCODE='42501';
        END IF;
        q:=loi.module_trang_thai(p_ma,p_module,p_pn,p_hd,p_module,p_viec,p_the_he);
        IF q->'cho_ghi' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'BUS_CONG_TAC' USING ERRCODE='42501';
        END IF;
        RETURN ai;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi.su_kien_phat(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text,p_pb integer,p_khoa text,p_noi_dung jsonb,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; c loi.dang_ky_contract; sk loi.su_kien; moi uuid;
    BEGIN
        ai:=loi.su_kien_ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF p_pb IS NULL OR p_pb<1 OR p_loai IS NULL OR p_khoa IS NULL
            OR length(p_khoa) NOT BETWEEN 1 AND 200 OR p_khoa<>btrim(p_khoa)
            OR split_part(p_hd,':',3) NOT IN ('LAP','SUA','DUYET') THEN
            RAISE EXCEPTION 'BUS_DAU_VAO' USING ERRCODE='22023';
        END IF;
        SELECT * INTO c FROM loi.dang_ky_contract WHERE ma=p_loai AND phien_ban=p_pb::text FOR SHARE;
        IF NOT FOUND OR c.trang_thai<>'dang_dung' OR c.module_so_huu<>p_module
            OR NOT EXISTS (SELECT FROM loi.phien_ban_module WHERE module=p_module AND trang_thai='da_cai') THEN
            RAISE EXCEPTION 'BUS_CONTRACT' USING ERRCODE='22023';
        END IF;
        IF NOT loi.su_kien_payload(p_noi_dung,c.luoc_do) THEN
            RAISE EXCEPTION 'BUS_PAYLOAD' USING ERRCODE='22023';
        END IF;
        INSERT INTO loi.su_kien(phap_nhan_id,ben_phat,loai_su_kien,phien_ban,phien_ban_contract,
            khoa_chong_trung,noi_dung_su_kien,ma_bam,tao_boi)
        VALUES (p_pn,p_module,p_loai,p_pb,p_pb::text,p_khoa,p_noi_dung,
            encode(sha256(convert_to(p_noi_dung::text,'UTF8')),'hex'),ai)
        ON CONFLICT (phap_nhan_id,ben_phat,khoa_chong_trung) DO NOTHING RETURNING id INTO moi;
        IF moi IS NOT NULL THEN RETURN moi; END IF;
        SELECT * INTO sk FROM loi.su_kien WHERE phap_nhan_id=p_pn AND ben_phat=p_module AND khoa_chong_trung=p_khoa;
        IF (sk.loai_su_kien,sk.phien_ban,sk.noi_dung_su_kien) IS DISTINCT FROM (p_loai,p_pb,p_noi_dung) THEN
            RAISE EXCEPTION 'BUS_DEDUPE_XUNG_DOT' USING ERRCODE='23505';
        END IF;
        RETURN sk.id;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.su_kien_nhan(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text DEFAULT NULL,p_gioi_han integer DEFAULT 100,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE sk loi.su_kien; ket_qua jsonb := '[]'::jsonb;
    BEGIN
        PERFORM loi.su_kien_ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF p_gioi_han IS NULL OR p_gioi_han NOT BETWEEN 1 AND 1000 THEN
            RAISE EXCEPTION 'BUS_DAU_VAO' USING ERRCODE='22023';
        END IF;
        FOR sk IN SELECT s.* FROM loi.su_kien s WHERE s.phap_nhan_id=p_pn
            AND (p_loai IS NULL OR s.loai_su_kien=p_loai)
            AND loi.su_kien_duoc_nhan(p_module,s.loai_su_kien,s.phien_ban_contract)
            AND NOT EXISTS (SELECT FROM loi.ack_su_kien a WHERE a.phap_nhan_id=p_pn
                AND a.ben_nhan=p_module AND a.su_kien_id=s.id)
            ORDER BY s.tao_luc,s.id LIMIT p_gioi_han
        LOOP
            INSERT INTO loi.hop_nhan_su_kien(phap_nhan_id,ben_nhan,su_kien_id)
                VALUES (p_pn,p_module,sk.id) ON CONFLICT DO NOTHING;
            PERFORM 1 FROM loi.hop_nhan_su_kien WHERE phap_nhan_id=p_pn
                AND ben_nhan=p_module AND su_kien_id=sk.id FOR UPDATE;
            -- Snapshot moi SAU khi cho khoa: worker truoc co the vua ACK.
            IF NOT EXISTS (SELECT FROM loi.ack_su_kien WHERE phap_nhan_id=p_pn
                AND ben_nhan=p_module AND su_kien_id=sk.id) THEN
                ket_qua:=ket_qua || jsonb_build_array(to_jsonb(sk));
            END IF;
        END LOOP;
        RETURN ket_qua;
    END;
    $ham$;
    CREATE OR REPLACE FUNCTION loi.su_kien_ack(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_su_kien uuid,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS boolean
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; sk loi.su_kien;
    BEGIN
        ai:=loi.su_kien_ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        SELECT * INTO sk FROM loi.su_kien WHERE phap_nhan_id=p_pn AND id=p_su_kien;
        IF NOT FOUND OR NOT loi.su_kien_duoc_nhan(p_module,sk.loai_su_kien,sk.phien_ban_contract) THEN
            RAISE EXCEPTION 'BUS_DANG_KY' USING ERRCODE='42501';
        END IF;
        PERFORM 1 FROM loi.hop_nhan_su_kien WHERE phap_nhan_id=p_pn
            AND ben_nhan=p_module AND su_kien_id=p_su_kien FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'BUS_CHUA_NHAN' USING ERRCODE='23505'; END IF;
        INSERT INTO loi.ack_su_kien(phap_nhan_id,ben_nhan,su_kien_id,ack_boi)
            VALUES (p_pn,p_module,p_su_kien,ai) ON CONFLICT DO NOTHING;
        RETURN FOUND;
    END;
    $ham$;

    FOR ham IN SELECT oid::regprocedure AS ck,proname FROM pg_proc
        WHERE pronamespace='loi'::regnamespace AND proname LIKE 'su_kien\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,%I,%I,%I',ham.ck,chay,login,cai_dat);
        IF ham.proname IN ('su_kien_phat','su_kien_nhan','su_kien_ack') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,login);
        ELSIF ham.proname='su_kien_dang_ky_nhan' THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',ham.ck,cai_dat);
        END IF;
    END LOOP;
    -- Module Manager cap dung ba cua phat/nhan/ack cho login module; khong cap bang/helper.
    PERFORM set_config('search_path',duong_cu,true);
    PERFORM set_config('role',vai_cu,true);
END;
$$;
