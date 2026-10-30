-- G2-13b: resolver dang_dung cua module dich phai co dung mot binding.
-- 016 de danh cho G2-16; khong doi migration 013 da phat hanh.
DO $do$
DECLARE
    tt text := coalesce(current_setting('kho_tri_thuc.tien_to_vai',true),'');
    chu text := tt||'vai_doi_cau_truc_loi';
BEGIN
    IF (tt<>'' AND tt !~ '^[a-z][a-z0-9_]*_$')
       OR octet_length(tt||'vai_doi_cau_truc_loi_tai_lieu')>63
       OR (tt<>'' AND current_database() !~ '^kho_test_')
       OR current_database() !~ '^(kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+)$'
       OR current_setting('server_version_num')::integer<160000 THEN
        RAISE EXCEPTION 'G2-13b: tu choi dich ngoai Core DEMO/test PG16+';
    END IF;
    IF NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='loi' AND pg_get_userbyid(nspowner)=chu)
       OR NOT EXISTS(SELECT FROM pg_proc
            WHERE oid=to_regprocedure('loi.goi_nghia_vu_noi_bo(text,text,uuid,text,jsonb,text,uuid,bigint)')
              AND pg_get_userbyid(proowner)=chu) THEN
        RAISE EXCEPTION 'G2-13b: Can lead, ap 001..013 truoc';
    END IF;
    PERFORM set_config('kho_tri_thuc.g2_13b_vai_cu',current_setting('role'),true);
    PERFORM set_config('kho_tri_thuc.g2_13b_duong_cu',current_setting('search_path'),true);
    EXECUTE format('SET LOCAL ROLE %I',chu);
END;
$do$;

CREATE OR REPLACE FUNCTION loi.goi_nghia_vu_noi_bo(p_ma text,p_module text,p_pn uuid,p_hd text,
    p_dich jsonb,p_contract text,p_viec uuid,p_the_he bigint) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ham$
DECLARE h loi.dang_ky_ham_module; kq jsonb; cong_tac jsonb;
BEGIN
    IF NOT EXISTS(SELECT FROM loi.xac_minh_phien(p_ma,p_module,p_pn,p_hd,p_viec,p_the_he)) THEN
        RAISE EXCEPTION 'TAI_LIEU_PHIEN' USING ERRCODE='42501';
    END IF;
    BEGIN
        SELECT d.* INTO STRICT h FROM loi.dang_ky_ham_module d
            JOIN loi.phien_ban_module m ON (m.module,m.so_phien_ban,m.ma_bam_goi)=
                (d.module,d.phien_ban_module,d.ma_bam_goi)
            JOIN loi.dang_ky_contract c ON (c.ma,c.phien_ban)=(d.ma_contract,d.phien_ban_contract)
            WHERE d.module=p_dich->>'module_nghia_vu' AND d.loai_ham='resolver_nghia_vu'
              AND m.trang_thai='da_cai' AND c.trang_thai='dang_dung';
    EXCEPTION
        WHEN no_data_found THEN
            RETURN jsonb_build_object('ket_luan','CHO','ly_do','THIEU_MODULE_RESOLVER');
        WHEN too_many_rows THEN
            RAISE EXCEPTION 'LIEN_KET_RESOLVER' USING ERRCODE='42501';
    END;
    IF to_regprocedure(h.chu_ky) IS NULL THEN
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

DO $do$
BEGIN
    PERFORM set_config('search_path',current_setting('kho_tri_thuc.g2_13b_duong_cu'),true);
    PERFORM set_config('role',current_setting('kho_tri_thuc.g2_13b_vai_cu'),true);
END;
$do$;
