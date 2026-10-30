-- G2-20: cua V2 SDK cho login module; giu nguyen cac migration da phat hanh.
-- Dung lai ghi_metadata G2-09: chi them nhanh module/ket_qua, Core nhu cu.
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_loi';
    chu_tl text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
BEGIN
    IF (tt <> '' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(chu_tl)>63 OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-20: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='loi_tai_lieu' AND pg_get_userbyid(nspowner)=chu_tl)
       OR to_regprocedure('loi.viec_giu(text,text,uuid,text,uuid,uuid,bigint)') IS NULL THEN
        RAISE EXCEPTION 'G2-20: Can lead, ap G2-01..19 dung owner truoc';
    END IF;
    PERFORM set_config('kho_tri_thuc.g2_20_vai_cu',current_setting('role'),true);
    PERFORM set_config('kho_tri_thuc.g2_20_duong_cu',current_setting('search_path'),true);
    EXECUTE format('SET LOCAL ROLE %I',chu);
    PERFORM set_config('search_path','pg_catalog,pg_temp',true);
END;
$$;

    -- DDL ngoai DO: tao ham duoi role da chon, nhu 013/017.
    -- Ham noi bo, khong cap cho runtime. Fail closed neu chua cai/nhieu ban da_cai.
    CREATE OR REPLACE FUNCTION loi.sdk_nguon_module(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS jsonb
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; pb text; so_ban integer; v loi.hang_viec; buoc uuid;
    BEGIN
        IF p_module IS NULL OR session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_mod_'||p_module) THEN
            RAISE EXCEPTION 'SDK_MODULE' USING ERRCODE='42501';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai IS NULL OR split_part(p_hd,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM set_config('ktt.ma_phien',p_ma,true), set_config('ktt.module',p_module,true),
            set_config('ktt.phap_nhan_id',p_pn::text,true), set_config('ktt.hanh_dong',p_hd,true),
            set_config('ktt.viec_id',coalesce(p_viec::text,''),true),
            set_config('ktt.the_he',coalesce(p_the_he::text,''),true);
        SELECT count(*),min(so_phien_ban) INTO so_ban,pb FROM (
            SELECT so_phien_ban FROM loi.phien_ban_module
            WHERE module=p_module AND trang_thai='da_cai' FOR SHARE
        ) b;
        IF so_ban<>1 THEN RAISE EXCEPTION 'SDK_PHIEN_BAN' USING ERRCODE='42501'; END IF;
        IF p_viec IS NOT NULL THEN
            SELECT * INTO v FROM loi.hang_viec WHERE id=p_viec AND module=p_module
                AND phap_nhan_id=p_pn FOR UPDATE;
            IF v.id IS NULL OR v.tao_boi IS DISTINCT FROM ai OR v.the_he IS DISTINCT FROM p_the_he
               OR v.engine_id IS NOT NULL OR v.trang_thai IS DISTINCT FROM 'DANG_CHAY'
               OR v.giu_den IS NULL OR v.giu_den<=clock_timestamp() THEN
                RAISE EXCEPTION 'VIEC_MAT_LEASE' USING ERRCODE='40001';
            END IF;
            SELECT buoc_viec_id INTO STRICT buoc FROM loi.lan_thu
                WHERE id=v.lan_thu_id AND viec_id=v.id AND the_he=p_the_he;
        END IF;
        RETURN jsonb_build_object('phien_ban_module',pb,'engine_id',NULL,
            'ham',p_hd,'phien_ban_ham',pb,'buoc_id',buoc,'lan_thu_id',v.lan_thu_id);
    END;
    $ham$;
    REVOKE ALL ON FUNCTION loi.sdk_nguon_module(text,text,uuid,text,uuid,bigint) FROM PUBLIC;
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu_tl text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
BEGIN
    EXECUTE format('GRANT EXECUTE ON FUNCTION loi.sdk_nguon_module(text,text,uuid,text,uuid,bigint) TO %I',chu_tl);
END;
$$;

    CREATE OR REPLACE FUNCTION loi.ghi_kiem_toan_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_doi_tuong text,p_doi_tuong_id uuid,p_ket_luan text,p_request uuid,
        p_contract text DEFAULT '1',p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS bigint
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; q jsonb; co jsonb; can text;
    BEGIN
        IF p_module IS NULL OR session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi$','dang_nhap_mod_'||p_module) THEN
            RAISE EXCEPTION 'SDK_MODULE' USING ERRCODE='42501';
        END IF;
        PERFORM pg_advisory_xact_lock_shared(742601,1);
        SELECT nguoi_dung_id INTO ai FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        IF ai IS NULL OR split_part(p_hd,':',1) IS DISTINCT FROM upper(p_module) THEN
            RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
        END IF;
        PERFORM set_config('ktt.ma_phien',p_ma,true), set_config('ktt.module',p_module,true),
            set_config('ktt.phap_nhan_id',p_pn::text,true), set_config('ktt.hanh_dong',p_hd,true),
            set_config('ktt.viec_id',coalesce(p_viec::text,''),true),
            set_config('ktt.the_he',coalesce(p_the_he::text,''),true);
        IF p_request IS NULL OR p_doi_tuong_id IS NULL THEN
            RAISE EXCEPTION 'SDK_DAU_VAO' USING ERRCODE='22023';
        END IF;
        q := loi.mtq_quyet_dinh_phien(p_ma,p_module,p_pn,p_hd,
            jsonb_build_object('bang',p_doi_tuong,'id',p_doi_tuong_id),p_contract,'{}',p_viec,p_the_he);
        IF q->'cho_phep' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'TAI_LIEU_MTQ' USING ERRCODE='42501';
        END IF;
        co := loi.module_trang_thai(p_ma,p_module,p_pn,p_hd,p_module,p_viec,p_the_he);
        can := CASE WHEN split_part(p_hd,':',3)='XEM' THEN 'cho_xem' ELSE 'cho_ghi' END;
        IF co->can IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'TAI_LIEU_CONG_TAC' USING ERRCODE='42501';
        END IF;
        RETURN loi.ghi_kiem_toan(p_hd,p_doi_tuong,p_doi_tuong_id,p_ket_luan,
            p_ma,p_module,p_pn,p_request,p_viec,p_the_he);
    END;
    $ham$;
    REVOKE ALL ON FUNCTION loi.ghi_kiem_toan_v2(text,text,uuid,text,text,uuid,text,uuid,text,uuid,bigint) FROM PUBLIC;
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu_tl text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
BEGIN
    EXECUTE format('SET LOCAL ROLE %I',chu_tl);
END;
$$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_metadata(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_loai text,p_tai_lieu uuid,p_du_lieu jsonb,p_request uuid,
        p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL) RETURNS uuid
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    DECLARE ai uuid; tl loi_tai_lieu.tai_lieu; kq loi_tai_lieu.ket_qua_xu_ly;
        nguon jsonb; tep loi_tai_lieu.tep_goc; kq_nguon loi_tai_lieu.ket_qua_xu_ly;
        moi uuid := gen_random_uuid(); goc uuid; ban bigint; muc text; khoa text[];
    BEGIN
        IF session_user::text IS DISTINCT FROM regexp_replace(current_user::text,
            'vai_doi_cau_truc_loi_tai_lieu$','dang_nhap_loi') THEN
            IF p_loai IS DISTINCT FROM 'ket_qua' THEN
                RAISE EXCEPTION 'TAI_LIEU_CHI_CORE' USING ERRCODE='42501';
            END IF;
            -- Chi cua V2 duoc cap EXECUTE cho module. Danh tinh nguon duoc
            -- Core tinh lai, ke ca neu cua noi bo nhan cac truong gia mao.
            p_du_lieu := p_du_lieu || loi.sdk_nguon_module(
                p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        END IF;
        muc := split_part(p_hd,':',3);
        IF p_request IS NULL OR p_module='core' OR p_tai_lieu IS NULL
           OR jsonb_typeof(p_du_lieu) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END IF;
        CASE p_loai
          WHEN 'tai_lieu' THEN khoa := ARRAY['loai','ten','doi_tuong','phien_ban_contract'];
          WHEN 'tep' THEN khoa := ARRAY['ten_tep','sha256','kich_thuoc','mime','khoa_luu_tru','het_han_luc'];
          WHEN 'bien_the' THEN khoa := ARRAY['tep_id','bien_the','revision_truoc'];
          WHEN 'quyen' THEN khoa := ARRAY['nguoi_dung_id','bien_the','cho_phep','hieu_luc_den','revision_truoc'];
          WHEN 'ket_qua' THEN khoa := ARRAY['tep_id','bien_the','ma_contract','phien_ban_contract',
              'phien_ban_module','engine_id','ham','phien_ban_ham','buoc_id','lan_thu_id',
              'trang_thai','ly_do','goc_id','revision_truoc','nguon'];
          WHEN 'duyet' THEN khoa := ARRAY['ket_qua_id','row_version','trang_thai_duyet'];
          WHEN 'cong_bo' THEN khoa := ARRAY['ket_qua_id'];
          ELSE RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END CASE;
        IF p_du_lieu - khoa <> '{}'::jsonb OR muc IS NULL OR
            (p_loai IN ('quyen','duyet','cong_bo') AND muc <> 'DUYET') OR
            (p_loai NOT IN ('quyen','duyet','cong_bo') AND muc NOT IN ('LAP','SUA')) THEN
            RAISE EXCEPTION 'TAI_LIEU_DAU_VAO' USING ERRCODE='22023';
        END IF;
        ai := loi_tai_lieu.ngu_canh(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he);
        PERFORM pg_advisory_xact_lock(hashtextextended('tai_lieu|' || p_tai_lieu::text,9));
        IF p_loai='tai_lieu' THEN
            PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,p_du_lieu->'doi_tuong',
                p_du_lieu->>'phien_ban_contract','cho_ghi',p_viec,p_the_he);
            moi := p_tai_lieu;
            INSERT INTO loi_tai_lieu.tai_lieu(id,phap_nhan_id,module,loai,ten,bang_doi_tuong,
                doi_tuong_id,phien_ban_contract,tao_boi) VALUES
                (moi,p_pn,p_module,p_du_lieu->>'loai',p_du_lieu->>'ten',p_du_lieu->'doi_tuong'->>'bang',
                 (p_du_lieu->'doi_tuong'->>'id')::uuid,p_du_lieu->>'phien_ban_contract',ai);
            INSERT INTO loi_tai_lieu.quyen_tai_lieu(phap_nhan_id,tai_lieu_id,nguoi_dung_id,
                bien_the,hanh_dong,so_phien_ban,cho_phep,tao_boi) VALUES(p_pn,moi,ai,'*','XEM',1,true,ai);
        ELSE
            SELECT * INTO tl FROM loi_tai_lieu.tai_lieu WHERE id=p_tai_lieu AND phap_nhan_id=p_pn;
            IF tl.id IS NULL OR tl.module <> p_module THEN
                RAISE EXCEPTION 'TAI_LIEU_KHONG_THAY' USING ERRCODE='42501';
            END IF;
            PERFORM loi_tai_lieu.kiem_quyen(p_ma,p_module,p_pn,p_hd,
                jsonb_build_object('bang',tl.bang_doi_tuong,'id',tl.doi_tuong_id),tl.phien_ban_contract,
                CASE WHEN p_loai='cong_bo' THEN 'cong_bo_chinh_thuc' ELSE 'cho_ghi' END,p_viec,p_the_he);
            CASE p_loai
            WHEN 'tep' THEN
                INSERT INTO loi_tai_lieu.tep_goc(id,phap_nhan_id,tai_lieu_id,ten_tep,ma_bam,kich_thuoc,
                    mime,khoa_luu_tru,het_han_luc,tao_boi) VALUES(moi,p_pn,p_tai_lieu,
                    p_du_lieu->>'ten_tep',p_du_lieu->>'sha256',(p_du_lieu->>'kich_thuoc')::bigint,
                    p_du_lieu->>'mime',p_du_lieu->>'khoa_luu_tru',(p_du_lieu->>'het_han_luc')::timestamptz,ai);
            WHEN 'bien_the' THEN
                SELECT coalesce(max(so_phien_ban),0) INTO ban FROM loi_tai_lieu.tai_lieu_tep
                    WHERE tai_lieu_id=p_tai_lieu AND bien_the=p_du_lieu->>'bien_the';
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.tai_lieu_tep(id,phap_nhan_id,tai_lieu_id,tep_id,bien_the,so_phien_ban,tao_boi)
                    VALUES(moi,p_pn,p_tai_lieu,(p_du_lieu->>'tep_id')::uuid,p_du_lieu->>'bien_the',ban+1,ai);
            WHEN 'quyen' THEN
                SELECT coalesce(max(so_phien_ban),0) INTO ban FROM loi_tai_lieu.quyen_tai_lieu
                    WHERE tai_lieu_id=p_tai_lieu AND nguoi_dung_id=(p_du_lieu->>'nguoi_dung_id')::uuid
                        AND bien_the=p_du_lieu->>'bien_the' AND hanh_dong='XEM';
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.quyen_tai_lieu(id,phap_nhan_id,tai_lieu_id,nguoi_dung_id,bien_the,
                    hanh_dong,so_phien_ban,cho_phep,hieu_luc_den,tao_boi) VALUES(moi,p_pn,p_tai_lieu,
                    (p_du_lieu->>'nguoi_dung_id')::uuid,p_du_lieu->>'bien_the','XEM',ban+1,
                    (p_du_lieu->>'cho_phep')::boolean,(p_du_lieu->>'hieu_luc_den')::timestamptz,ai);
            WHEN 'ket_qua' THEN
                IF p_du_lieu->>'tep_id' IS NOT NULL AND NOT EXISTS (
                    SELECT FROM loi_tai_lieu.tai_lieu_tep WHERE tai_lieu_id=p_tai_lieu
                        AND tep_id=(p_du_lieu->>'tep_id')::uuid AND bien_the=p_du_lieu->>'bien_the') THEN
                    RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                END IF;
                goc := coalesce((p_du_lieu->>'goc_id')::uuid,moi);
                SELECT coalesce(max(revision),0) INTO ban FROM loi_tai_lieu.ket_qua_xu_ly
                    WHERE goc_id=goc AND tai_lieu_id=p_tai_lieu;
                IF ban IS DISTINCT FROM (p_du_lieu->>'revision_truoc')::bigint OR
                    (ban=0 AND goc<>moi) THEN
                    RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                END IF;
                INSERT INTO loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id,tai_lieu_id,goc_id,revision,
                    tep_id,bien_the,ma_contract,phien_ban_contract,module,phien_ban_module,engine_id,
                    ham,phien_ban_ham,viec_id,buoc_id,lan_thu_id,the_he,trang_thai,ly_do,tao_boi)
                VALUES(moi,p_pn,p_tai_lieu,goc,ban+1,(p_du_lieu->>'tep_id')::uuid,p_du_lieu->>'bien_the',
                    p_du_lieu->>'ma_contract',p_du_lieu->>'phien_ban_contract',p_module,
                    p_du_lieu->>'phien_ban_module',(p_du_lieu->>'engine_id')::uuid,
                    p_du_lieu->>'ham',p_du_lieu->>'phien_ban_ham',p_viec,(p_du_lieu->>'buoc_id')::uuid,
                    (p_du_lieu->>'lan_thu_id')::uuid,p_the_he,p_du_lieu->>'trang_thai',p_du_lieu->>'ly_do',ai);
                IF jsonb_typeof(p_du_lieu->'nguon') IS DISTINCT FROM 'array' THEN
                    RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                END IF;
                FOR nguon IN SELECT value FROM jsonb_array_elements(p_du_lieu->'nguon') LOOP
                    IF jsonb_typeof(nguon) IS DISTINCT FROM 'object' OR nguon - ARRAY[
                        'tep_id','ket_qua_id','revision','sha256','trang','dinh_vi','trich_dan'] <> '{}'::jsonb
                        OR num_nonnulls(nguon->>'tep_id',nguon->>'ket_qua_id') <> 1 THEN
                        RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                    END IF;
                    IF nguon->>'ket_qua_id' IS NOT NULL THEN
                        SELECT * INTO kq_nguon FROM loi_tai_lieu.ket_qua_xu_ly
                            WHERE id=(nguon->>'ket_qua_id')::uuid AND phap_nhan_id=p_pn;
                        IF kq_nguon.id IS NULL OR kq_nguon.id=moi OR kq_nguon.revision IS DISTINCT FROM
                            (nguon->>'revision')::bigint OR NOT loi_tai_lieu.duoc_xem_noi_dung(
                                p_tai_lieu,ai,kq_nguon.bien_the) THEN
                            RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                        END IF;
                        SELECT * INTO tep FROM loi_tai_lieu.tep_goc WHERE id=kq_nguon.tep_id;
                    ELSE
                        SELECT * INTO tep FROM loi_tai_lieu.tep_goc WHERE id=(nguon->>'tep_id')::uuid;
                        IF NOT EXISTS (SELECT FROM loi_tai_lieu.tai_lieu_tep b WHERE b.tep_id=tep.id
                            AND loi_tai_lieu.duoc_xem_noi_dung(p_tai_lieu,ai,b.bien_the)) THEN
                            RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
                        END IF;
                    END IF;
                    -- Nguon phai cung ho so; khong cho lay ID de vuot quyen noi dung.
                    IF tep.id IS NULL OR tep.tai_lieu_id<>p_tai_lieu OR tep.ma_bam IS DISTINCT FROM nguon->>'sha256'
                        OR (tep.het_han_luc IS NOT NULL AND tep.het_han_luc <= clock_timestamp()) THEN
                        RAISE EXCEPTION 'TAI_LIEU_NGUON' USING ERRCODE='22023';
                    END IF;
                    INSERT INTO loi_tai_lieu.nguon_ket_qua(phap_nhan_id,ket_qua_id,tep_id,ket_qua_nguon_id,
                        ma_bam,revision_nguon,trang,dinh_vi,trich_dan) VALUES(p_pn,moi,
                        (nguon->>'tep_id')::uuid,(nguon->>'ket_qua_id')::uuid,tep.ma_bam,
                        (nguon->>'revision')::bigint,(nguon->>'trang')::integer,nguon->>'dinh_vi',nguon->>'trich_dan');
                END LOOP;
                INSERT INTO loi_tai_lieu.ket_qua_duyet(phap_nhan_id,ket_qua_id,phien_ban_dong,trang_thai_duyet,tao_boi)
                    VALUES(p_pn,moi,1,'chua_duyet',ai);
            WHEN 'duyet','cong_bo' THEN
                SELECT * INTO kq FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=(p_du_lieu->>'ket_qua_id')::uuid
                    AND tai_lieu_id=p_tai_lieu AND phap_nhan_id=p_pn;
                IF kq.id IS NULL THEN RAISE EXCEPTION 'TAI_LIEU_KHONG_THAY' USING ERRCODE='42501'; END IF;
                IF p_loai='cong_bo' AND NOT loi_tai_lieu.duoc_xem_ket_qua(kq.id,ai) THEN
                    RAISE EXCEPTION 'TAI_LIEU_NOI_DUNG' USING ERRCODE='42501';
                END IF;
                IF kq.trang_thai<>'thanh_cong' OR NOT EXISTS(SELECT FROM loi_tai_lieu.tep_goc
                    WHERE id=kq.tep_id AND ma_bam ~ '^[0-9a-f]{64}$'
                        AND (het_han_luc IS NULL OR het_han_luc>clock_timestamp()))
                    OR NOT EXISTS(SELECT FROM loi_tai_lieu.nguon_ket_qua WHERE ket_qua_id=kq.id) THEN
                    RAISE EXCEPTION 'TAI_LIEU_THIEU_TEP_HASH' USING ERRCODE='55000';
                END IF;
                IF EXISTS (SELECT FROM loi_tai_lieu.nguon_ket_qua n
                    LEFT JOIN loi_tai_lieu.ket_qua_xu_ly s ON s.id=n.ket_qua_nguon_id
                    LEFT JOIN loi_tai_lieu.tep_goc t ON t.id=coalesce(n.tep_id,s.tep_id)
                    WHERE n.ket_qua_id=kq.id AND (t.id IS NULL OR t.ma_bam IS DISTINCT FROM n.ma_bam
                        OR (t.het_han_luc IS NOT NULL AND t.het_han_luc<=clock_timestamp()))) THEN
                    RAISE EXCEPTION 'TAI_LIEU_THIEU_TEP_HASH' USING ERRCODE='55000';
                END IF;
                IF p_loai='duyet' THEN
                    SELECT max(phien_ban_dong) INTO ban FROM loi_tai_lieu.ket_qua_duyet WHERE ket_qua_id=kq.id;
                    IF ban IS DISTINCT FROM (p_du_lieu->>'row_version')::bigint THEN
                        RAISE EXCEPTION 'TAI_LIEU_REVISION' USING ERRCODE='40001';
                    END IF;
                    INSERT INTO loi_tai_lieu.ket_qua_duyet(id,phap_nhan_id,ket_qua_id,phien_ban_dong,trang_thai_duyet,tao_boi)
                        VALUES(moi,p_pn,kq.id,ban+1,p_du_lieu->>'trang_thai_duyet',ai);
                ELSE
                    INSERT INTO loi_tai_lieu.ket_qua_cong_bo(id,phap_nhan_id,ket_qua_id,tao_boi) VALUES(moi,p_pn,kq.id,ai);
                END IF;
            END CASE;
        END IF;
        PERFORM loi.ghi_kiem_toan(p_hd,'tai_lieu_' || p_loai,moi,'DAT',p_ma,p_module,p_pn,p_request,p_viec,p_the_he);
        RETURN moi;
    END;
    $ham$;

    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_ket_qua_v2(p_ma text,p_module text,p_pn uuid,p_hd text,
        p_tai_lieu uuid,p_du_lieu jsonb,p_request uuid,p_viec uuid DEFAULT NULL,p_the_he bigint DEFAULT NULL)
    RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
    BEGIN
        IF jsonb_typeof(p_du_lieu) IS DISTINCT FROM 'object'
           OR p_du_lieu-ARRAY['tep_id','bien_the','ma_contract','phien_ban_contract',
               'trang_thai','ly_do','goc_id','revision_truoc','nguon']<>'{}'::jsonb THEN
            RAISE EXCEPTION 'SDK_NGUON_TU_KHAI' USING ERRCODE='22023';
        END IF;
        -- ghi_metadata kiem module/login, phien/MTQ/phap nhan, nguon va revision;
        -- khong cap duyet/cong bo, khong cap metadata tep chua duoc Core kiem hash.
        RETURN loi_tai_lieu.ghi_metadata(p_ma,p_module,p_pn,p_hd,'ket_qua',
            p_tai_lieu,p_du_lieu,p_request,p_viec,p_the_he);
    END;
    $ham$;
    REVOKE ALL ON FUNCTION loi_tai_lieu.ghi_ket_qua_v2(text,text,uuid,text,uuid,jsonb,uuid,uuid,bigint) FROM PUBLIC;
DO $$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt || 'vai_doi_cau_truc_loi';
    chu_tl text := tt || 'vai_doi_cau_truc_loi_tai_lieu';
    vai record;
BEGIN
    -- Giu ACL cua ghi_metadata: module KHONG duoc goi cua noi bo G2-09.
    -- 020 chi cap hai chu ky V2 cho vai_chay_mod_* ton tai luc ap migration.
    -- Module cai sau 020 can G2-25 cap quyen: no da ghi trong ke hoach,
    -- Module Manager hien chua co ma cap bo sung; khong cap owner/login bang chung.
    EXECUTE format('REVOKE ALL ON FUNCTION loi_tai_lieu.ghi_ket_qua_v2(text,text,uuid,text,uuid,jsonb,uuid,uuid,bigint) FROM %I',chu_tl);
    EXECUTE format('SET LOCAL ROLE %I',chu);
    EXECUTE format('REVOKE ALL ON FUNCTION loi.ghi_kiem_toan_v2(text,text,uuid,text,text,uuid,text,uuid,text,uuid,bigint) FROM %I',chu);
    EXECUTE format('SET LOCAL ROLE %I',chu_tl);
    FOR vai IN SELECT rolname FROM pg_roles
        WHERE left(rolname,length(tt||'vai_chay_mod_'))=tt||'vai_chay_mod_'
          AND NOT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls LOOP
        EXECUTE format('GRANT EXECUTE ON FUNCTION loi_tai_lieu.ghi_ket_qua_v2(text,text,uuid,text,uuid,jsonb,uuid,uuid,bigint) TO %I',vai.rolname);
        EXECUTE format('SET LOCAL ROLE %I',chu);
        EXECUTE format('GRANT EXECUTE ON FUNCTION loi.ghi_kiem_toan_v2(text,text,uuid,text,text,uuid,text,uuid,text,uuid,bigint) TO %I',vai.rolname);
        EXECUTE format('SET LOCAL ROLE %I',chu_tl);
    END LOOP;
    PERFORM set_config('search_path',current_setting('kho_tri_thuc.g2_20_duong_cu'),true);
    PERFORM set_config('role',current_setting('kho_tri_thuc.g2_20_vai_cu'),true);
END;
$$;

