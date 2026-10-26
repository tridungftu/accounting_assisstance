"""M0037 — CD-010: bằng chứng G5 kiểm tay riêng, không thay hợp đồng E5/PDF."""

from .sql_crm_doi_chieu import _G_KET, _G_REPLAY
from .sql_crm_kiem_hd import _KIEM_MO


G5_TAY_XET = """
            -- CD-010: chỉ bằng chứng kiểm tay của đúng revision đã ký mới qua G5.
            SELECT t.* INTO x FROM master.crm_g5_kiem_tay t
                JOIN master.crm_hd_ky kt ON kt.id = t.ky_id AND kt.phap_nhan_id = t.phap_nhan_id
                JOIN master.crm_hd_soan st ON st.id = kt.soan_id
                WHERE t.ky_id = p_ky AND t.soan_rev_id = kt.soan_rev_id AND st.revision_hien_hanh = kt.revision
                  AND t.ky_pdf_sha256 = kt.ky_pdf_sha256 AND t.g3_docx_sha256 = kt.g3_docx_sha256
                  AND kt.g3_pdf_sha256 IS NULL
                  AND NOT EXISTS (SELECT 1 FROM master.crm_g5_ket_qua q0 WHERE q0.ky_id = p_ky)
                  AND NOT EXISTS (SELECT 1 FROM master.crm_kiem_g5_ket_qua q0 WHERE q0.ky_id = p_ky);
            IF x.id IS NOT NULL THEN
                RETURN jsonb_build_object('che_do', CASE WHEN p_che_do = 'SYNTHETIC_FIXTURE' THEN 'SYNTHETIC_FIXTURE' ELSE 'VAN_HANH' END,
                    'trang_thai', 'KHOP', 'loai', 'KIEM_TAY', 'ket_qua_id', x.id, 'khoi_tao', v_kt,
                    'xac_nhan_boi', x.xac_nhan_boi, 'xac_nhan_luc', x.xac_nhan_luc, 'ly_do', x.ly_do,
                    'chan', '[]'::jsonb, 'lech', '[]'::jsonb);
            END IF;
"""

CRM_G5_TAY_SQL = (
    """CREATE TABLE master.crm_g5_kiem_tay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ky_id uuid NOT NULL UNIQUE,
        phap_nhan_id uuid NOT NULL,
        soan_rev_id uuid NOT NULL REFERENCES master.crm_hd_soan_rev(id),
        ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ '^[0-9a-f]{64}$'),
        g3_docx_sha256 text NOT NULL CHECK (g3_docx_sha256 ~ '^[0-9a-f]{64}$'),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) BETWEEN 10 AND 1000 AND ly_do !~ '[[:cntrl:]]'),
        xac_nhan_boi text NOT NULL,
        xac_nhan_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky(id, phap_nhan_id))""",
    "ALTER TABLE master.crm_g5_kiem_tay ENABLE ROW LEVEL SECURITY",
    "CREATE TRIGGER crm_g5_kiem_tay_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_kiem_tay FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_kiem_tay_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE p_ky uuid := NEW.ky_id; ai text := master.ktt_danh_tinh(); d record; k record; h record; s record; g jsonb;
        BEGIN""" + _KIEM_MO + """
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g5|' || p_ky::text, 0));
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = k.soan_id FOR UPDATE;
            PERFORM 1 FROM master.crm_hd_ky WHERE id = p_ky FOR UPDATE;
            g := master.crm_kiem_g5_xet(p_ky, 'VAN_HANH');
            IF h.crm_giao_ket IS DISTINCT FROM 'DA_KY' OR s.trang_thai IS DISTINCT FROM 'DA_KY'
               OR s.revision_hien_hanh IS DISTINCT FROM k.revision OR k.g3_pdf_sha256 IS NOT NULL
               OR g ->> 'trang_thai' IS DISTINCT FROM 'HOLD'
               OR g -> 'chan' IS DISTINCT FROM '[{"ma":"G5_BAN_SINH_CHI_DOCX"}]'::jsonb
               OR EXISTS (SELECT 1 FROM master.crm_g5_ket_qua WHERE ky_id = p_ky)
               OR EXISTS (SELECT 1 FROM master.crm_kiem_g5_ket_qua WHERE ky_id = p_ky)
               OR EXISTS (SELECT 1 FROM master.crm_g5_kiem_tay WHERE ky_id = p_ky)
               OR EXISTS (SELECT 1 FROM master.crm_kiem_ho_so WHERE ky_id = p_ky AND trang_thai NOT IN ('DANG_KIEM','CHO_BO_SUNG')) THEN
                RAISE EXCEPTION 'CRM_G5_TAY_TRANG_THAI: bản ký không còn HOLD vì bản sinh chỉ DOCX của revision hiện hành' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.phap_nhan_id IS DISTINCT FROM d.pn OR NEW.soan_rev_id IS DISTINCT FROM k.soan_rev_id
               OR NEW.ky_pdf_sha256 IS DISTINCT FROM k.ky_pdf_sha256 OR NEW.g3_docx_sha256 IS DISTINCT FROM k.g3_docx_sha256
               OR NEW.xac_nhan_boi IS DISTINCT FROM ai OR NEW.xac_nhan_luc IS DISTINCT FROM now() THEN
                RAISE EXCEPTION 'CRM_G5_TAY_TRANG_THAI: căn cứ hoặc người/lúc kiểm tay không khớp máy chủ' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.ly_do IS NULL OR length(btrim(NEW.ly_do)) NOT BETWEEN 10 AND 1000 OR NEW.ly_do ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'CRM_G5_TAY_LY_DO: lý do kiểm tay bắt buộc từ 10 đến 1000 ký tự, không có ký tự điều khiển' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_kiem_tay_kiem BEFORE INSERT ON master.crm_g5_kiem_tay FOR EACH ROW EXECUTE FUNCTION master.crm_g5_kiem_tay_kiem()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_kiem_tay_nhat_ky() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v record;
        BEGIN
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
                VALUES (NEW.phap_nhan_id, NEW.xac_nhan_boi, 'QUYET_DINH', 'master.crm_hd_ky', NEW.ky_id,
                        'CRM_G5_XAC_NHAN_TAY', to_jsonb(NEW) || jsonb_build_object('loai', 'KIEM_TAY'), NEW.ly_do);
            FOR v IN UPDATE master.crm_g5_viec SET trang_thai = 'XONG', ly_do = 'G5_DA_KIEM_TAY', ket_qua_id = NEW.id,
                         lease_boi = NULL, lease_den = NULL, cap_nhat_luc = now()
                     WHERE ky_id = NEW.ky_id AND trang_thai IN ('CHO','DANG_CHAY','CHUA_RO','CHO_CAU_HINH') RETURNING id LOOP
                PERFORM master.crm_g5_ghi_su_kien(v.id, 'XONG', 'NGUOI_DUNG', NEW.xac_nhan_boi,
                    jsonb_build_object('ket_qua_id', NEW.id, 'loai', 'KIEM_TAY', 'ly_do', NEW.ly_do));
            END LOOP;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_kiem_tay_nhat_ky AFTER INSERT ON master.crm_g5_kiem_tay FOR EACH ROW EXECUTE FUNCTION master.crm_g5_kiem_tay_nhat_ky()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_xac_nhan_tay(p_khoa text, p_h text, p_ky uuid, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; k record; h record; cu jsonb; kq jsonb; t record;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_G5_XAC_NHAN_TAY'") + """
            IF p_ly_do IS NULL OR length(btrim(p_ly_do)) NOT BETWEEN 10 AND 1000 OR p_ly_do ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'CRM_G5_TAY_LY_DO: lý do kiểm tay bắt buộc từ 10 đến 1000 ký tự, không có ký tự điều khiển' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_g5_kiem_tay (ky_id, phap_nhan_id, soan_rev_id, ky_pdf_sha256, g3_docx_sha256, ly_do, xac_nhan_boi)
                VALUES (p_ky, d.pn, k.soan_rev_id, k.ky_pdf_sha256, k.g3_docx_sha256, btrim(p_ly_do), ai) RETURNING * INTO t;
            kq := to_jsonb(t) || jsonb_build_object('loai', 'KIEM_TAY', 'trang_thai', 'KHOP', 'ket_qua_id', t.id);
            """ + _G_KET.format(a="'CRM_G5_XAC_NHAN_TAY'") + """
        END $$""",
    "REVOKE ALL ON master.crm_g5_kiem_tay FROM PUBLIC",
    """DO $$
        DECLARE r text;
        BEGIN
            FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE ALL ON master.crm_g5_kiem_tay FROM %I', r);
                END IF;
            END LOOP;
        END $$""",
    "REVOKE EXECUTE ON FUNCTION master.crm_g5_xac_nhan_tay(text, text, uuid, text), master.crm_g5_kiem_tay_kiem(), master.crm_g5_kiem_tay_nhat_ky() FROM PUBLIC",
)
