"""MDA-1a — Mốc thanh toán riêng của dự án (CD-006, CD-007), chỉ hằng SQL.

Tái sử dụng preflight/biên nhận và bất biến của M0031. Ghi bằng kết nối chủ
bảng, kiểm quyền phiên trước replay; mỗi thay đổi là một lần + một sự kiện.
"""

from .sql_crm_du_an_ban import _CHU, _KET, _REPLAY, _UUID_RE

_BANG = ("crm_da_moc", "crm_da_moc_ls")
_BANG_DS = ", ".join("master." + t for t in _BANG)
_HAM = (
    "master.crm_da_moc_ten_chuan(text)", "master.crm_da_moc_kiem_trung()",
    "master.crm_da_moc_ghi(text, text, uuid, jsonb, text)",
    "master.crm_da_moc_doc(uuid, date)", "master.crm_da_moc_ls_doc(uuid)",
)

CRM_DU_AN_MOC_SQL = (
    """CREATE TABLE master.crm_da_moc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        da_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        ma text NOT NULL UNIQUE CHECK (ma = 'DAM-' || id::text),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (da_ban_id, phap_nhan_id) REFERENCES master.crm_da_ban (id, phap_nhan_id),
        UNIQUE (id, phap_nhan_id))""",
    "CREATE INDEX crm_da_moc_du_an ON master.crm_da_moc (da_ban_id)",
    "CREATE TRIGGER crm_da_moc_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_moc FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_da_moc_ls (
        moc_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        hieu_luc_tu date NOT NULL,
        hieu_luc_den date,
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 120 AND ten = btrim(ten) AND ten !~ '[[:cntrl:]{}]'),
        ten_tat text CHECK (ten_tat IS NULL OR (length(ten_tat) BETWEEN 1 AND 20 AND ten_tat = btrim(ten_tat) AND ten_tat !~ '[[:cntrl:]{}]')),
        ngay_du_kien date NOT NULL,
        ngay_thuc_te date,
        dang_dung boolean NOT NULL DEFAULT true,
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) BETWEEN 1 AND 1000),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (moc_id, lan),
        FOREIGN KEY (moc_id, phap_nhan_id) REFERENCES master.crm_da_moc (id, phap_nhan_id),
        CHECK (hieu_luc_den IS NULL OR hieu_luc_den >= hieu_luc_tu))""",
    "CREATE UNIQUE INDEX crm_da_moc_ls_mo_uq ON master.crm_da_moc_ls (moc_id) WHERE hieu_luc_den IS NULL",
    "CREATE TRIGGER crm_da_moc_ls_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_moc_ls FOR EACH ROW EXECUTE FUNCTION master.crm_da_dong_mot_lan()",
    # Ánh xạ đủ hoa/thường sang ASCII trước upper: không phụ thuộc locale C.
    # Bỏ dấu tổ hợp (NFD), sau đó gộp và cắt khoảng trắng, không extension.
    """CREATE FUNCTION master.crm_da_moc_ten_chuan(p_ten text) RETURNS text
        LANGUAGE sql IMMUTABLE STRICT SET search_path = master, pg_temp AS $$
        SELECT btrim(regexp_replace(upper(regexp_replace(translate(p_ten,
            U&'aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵAÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬEÈÉẺẼẸÊỀẾỂỄỆIÌÍỈĨỊOÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢUÙÚỦŨỤƯỪỨỬỮỰYỲÝỶỸỴđĐ',
            'AAAAAAAAAAAAAAAAAAEEEEEEEEEEEEIIIIIIOOOOOOOOOOOOOOOOOOUUUUUUUUUUUUYYYYYYAAAAAAAAAAAAAAAAAAEEEEEEEEEEEEIIIIIIOOOOOOOOOOOOOOOOOOUUUUUUUUUUUUYYYYYYDD'),
            U&'[\\0300\\0301\\0303\\0309\\0323\\0306\\0302\\031B]', '', 'g')),
            '[[:space:]]+', ' ', 'g'))
        $$""",
    # Khóa cùng dòng dự án như lệnh ghi: serialize các mốc khác nhau cùng dự án.
    # Trigger giữ ràng buộc cả khi chủ bảng INSERT trực tiếp, không chỉ qua lệnh.
    """CREATE FUNCTION master.crm_da_moc_kiem_trung() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE da uuid;
        BEGIN
            SELECT da_ban_id INTO da FROM master.crm_da_moc WHERE id = NEW.moc_id;
            PERFORM 1 FROM master.crm_da_ban WHERE id = da FOR UPDATE;
            IF NEW.dang_dung AND NEW.hieu_luc_den IS NULL AND EXISTS (
                SELECT 1 FROM master.crm_da_moc m JOIN master.crm_da_moc_ls s ON s.moc_id = m.id
                WHERE m.da_ban_id = da AND m.id <> NEW.moc_id AND s.hieu_luc_den IS NULL AND s.dang_dung
                  AND master.crm_da_moc_ten_chuan(s.ten) = master.crm_da_moc_ten_chuan(NEW.ten)) THEN
                RAISE EXCEPTION 'CRM_DA_MOC_TRUNG: tên mốc đang dùng đã có trong dự án' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_da_moc_ls_trung BEFORE INSERT ON master.crm_da_moc_ls FOR EACH ROW EXECUTE FUNCTION master.crm_da_moc_kiem_trung()",
    """CREATE FUNCTION master.crm_da_moc_ghi(p_khoa text, p_h text, p_da uuid, p_moc jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); ngay date := master.ktt_ngay(); d record;
                o master.crm_da_moc%ROWTYPE; s master.crm_da_moc_ls%ROWTYPE;
                cu jsonb; kq jsonb; truoc jsonb; sau jsonb; v jsonb; mid uuid;
                n integer := 1; doi boolean := true; hanh text := 'CRM_DA_MOC_KHAI';
                dk date; tt date; ld text := nullif(btrim(p_ly_do), ''); r record;
        BEGIN
            SELECT * INTO d FROM master.crm_da_ban WHERE id = p_da;
            cu := master.crm_da_vao('CRM_DA_MOC', d.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            IF p_moc IS NULL OR jsonb_typeof(p_moc) <> 'object' THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: cần một object mốc' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_each(p_moc) k
                WHERE k.key <> ALL (ARRAY['moc_id','expected_lan','ten','ten_tat','ngay_du_kien','ngay_thuc_te','dang_dung'])
                   OR (k.key IN ('moc_id','ten','ten_tat','ngay_du_kien','ngay_thuc_te') AND jsonb_typeof(k.value) NOT IN ('string','null'))
                   OR (k.key = 'expected_lan' AND jsonb_typeof(k.value) NOT IN ('number','null'))
                   OR (k.key = 'dang_dung' AND jsonb_typeof(k.value) <> 'boolean')) THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: khóa hoặc kiểu trường mốc không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF ld IS NOT NULL AND length(ld) > 1000 THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: lý do tối đa 1000 ký tự' USING ERRCODE = 'P0001';
            END IF;
            IF p_moc ->> 'expected_lan' IS NOT NULL AND (p_moc ->> 'expected_lan') !~ '^[0-9]{1,9}$' THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: lần mong đợi phải là số nguyên' USING ERRCODE = 'P0001';
            END IF;
            PERFORM 1 FROM master.crm_da_ban WHERE id = p_da FOR UPDATE;
            IF p_moc ->> 'moc_id' IS NULL THEN
                IF p_moc ->> 'expected_lan' IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_LAN_CU: mốc mới chưa có lần hiện hành' USING ERRCODE = 'P0001';
                END IF;
                mid := gen_random_uuid();
                v := jsonb_build_object('ten_tat', NULL, 'ngay_thuc_te', NULL, 'dang_dung', true) || p_moc;
            ELSE
                IF (p_moc ->> 'moc_id') !~ """ + _UUID_RE + """ THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_SAI: mã mốc không hợp lệ' USING ERRCODE = 'P0001';
                END IF;
                mid := (p_moc ->> 'moc_id')::uuid;
                SELECT * INTO o FROM master.crm_da_moc WHERE id = mid AND da_ban_id = p_da;
                IF o.id IS NULL THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_SAI: mốc không thuộc dự án' USING ERRCODE = 'P0001';
                END IF;
                SELECT * INTO s FROM master.crm_da_moc_ls WHERE moc_id = mid AND hieu_luc_den IS NULL FOR UPDATE;
                IF p_moc ->> 'expected_lan' IS NULL OR (p_moc ->> 'expected_lan')::integer IS DISTINCT FROM s.lan THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_LAN_CU: mốc đã đổi (lần %) — tải lại rồi sửa', s.lan USING ERRCODE = 'P0001';
                END IF;
                IF ngay < s.hieu_luc_tu THEN
                    RAISE EXCEPTION 'CRM_DA_NGAY_LUI: ngày hiện hành trước ngày hiệu lực mốc' USING ERRCODE = 'P0001';
                END IF;
                truoc := jsonb_build_object('ten', s.ten, 'ten_tat', s.ten_tat, 'ngay_du_kien', s.ngay_du_kien,
                                           'ngay_thuc_te', s.ngay_thuc_te, 'dang_dung', s.dang_dung);
                v := truoc || p_moc;
                n := s.lan;
            END IF;
            IF coalesce(length(v ->> 'ten'), 0) NOT BETWEEN 1 AND 120 OR (v ->> 'ten') <> btrim(v ->> 'ten')
               OR (v ->> 'ten') ~ '[[:cntrl:]{}]'
               OR (v ->> 'ten_tat' IS NOT NULL AND (length(v ->> 'ten_tat') NOT BETWEEN 1 AND 20
                   OR (v ->> 'ten_tat') <> btrim(v ->> 'ten_tat') OR (v ->> 'ten_tat') ~ '[[:cntrl:]{}]')) THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: tên cần 1–120 ký tự, tên tắt 1–20, không khoảng trắng thừa/ký tự cấm' USING ERRCODE = 'P0001';
            END IF;
            IF v ->> 'ngay_du_kien' IS NULL THEN
                IF o.id IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_SAI: Ngày dự kiến không được để trống' USING ERRCODE = 'P0001';
                END IF;
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: cần ngày dự kiến khi khai mốc' USING ERRCODE = 'P0001';
            END IF;
            FOR r IN SELECT k.key, k.value FROM jsonb_each_text(v) k WHERE k.key IN ('ngay_du_kien','ngay_thuc_te') LOOP
                IF r.value IS NOT NULL THEN
                    IF r.value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
                        RAISE EXCEPTION 'CRM_DA_MOC_NGAY_SAI: ngày cần dạng YYYY-MM-DD' USING ERRCODE = 'P0001';
                    END IF;
                    BEGIN
                        PERFORM r.value::date;
                    EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN
                        RAISE EXCEPTION 'CRM_DA_MOC_NGAY_SAI: ngày không tồn tại' USING ERRCODE = 'P0001';
                    END;
                END IF;
            END LOOP;
            dk := (v ->> 'ngay_du_kien')::date;
            tt := (v ->> 'ngay_thuc_te')::date;
            IF tt > ngay THEN
                RAISE EXCEPTION 'CRM_DA_MOC_NGAY_SAI: không ghi ngày thực tế tương lai' USING ERRCODE = 'P0001';
            END IF;
            sau := jsonb_build_object('ten', v ->> 'ten', 'ten_tat', v ->> 'ten_tat', 'ngay_du_kien', dk,
                                     'ngay_thuc_te', tt, 'dang_dung', (v ->> 'dang_dung')::boolean);
            IF o.id IS NOT NULL THEN
                doi := truoc IS DISTINCT FROM sau;
                IF (dk IS DISTINCT FROM s.ngay_du_kien OR (s.ngay_thuc_te IS NOT NULL AND tt IS DISTINCT FROM s.ngay_thuc_te)) AND ld IS NULL THEN
                    RAISE EXCEPTION 'CRM_DA_MOC_CAN_LY_DO: chỉnh ngày dự kiến hoặc ngày thực tế đã ghi cần lý do' USING ERRCODE = 'P0001';
                END IF;
                IF doi THEN
                    hanh := CASE WHEN tt IS DISTINCT FROM s.ngay_thuc_te THEN 'CRM_DA_MOC_THUC_TE'
                                 WHEN dk IS DISTINCT FROM s.ngay_du_kien THEN 'CRM_DA_MOC_CHINH_DU_KIEN' ELSE 'CRM_DA_MOC_SUA' END;
                    UPDATE master.crm_da_moc_ls SET hieu_luc_den = ngay WHERE moc_id = mid AND lan = s.lan;
                    n := s.lan + 1;
                END IF;
            ELSE
                INSERT INTO master.crm_da_moc (id, da_ban_id, phap_nhan_id, ma, tao_boi)
                    VALUES (mid, p_da, d.phap_nhan_id, 'DAM-' || mid::text, ai);
            END IF;
            IF doi THEN
                INSERT INTO master.crm_da_moc_ls (moc_id, phap_nhan_id, lan, hieu_luc_tu, ten, ten_tat, ngay_du_kien, ngay_thuc_te, dang_dung, ly_do, tao_boi)
                    VALUES (mid, d.phap_nhan_id, n, ngay, v ->> 'ten', v ->> 'ten_tat', dk, tt, (v ->> 'dang_dung')::boolean, ld, ai);
                INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do)
                    VALUES (d.phap_nhan_id, ai, 'SUA_DANH_MUC', 'master.crm_da_moc', mid, hanh, truoc, sau, ld);
            END IF;
            kq := jsonb_build_object('da_ban_id', p_da, 'du_an_id', d.du_an_id, 'moc_id', mid, 'ma', 'DAM-' || mid::text, 'lan', n, 'doi', doi);""" + _KET.format(pn="d.phap_nhan_id", a="'CRM_DA_MOC'") + """
        END $$""",
    """CREATE FUNCTION master.crm_da_moc_doc(p_du_an uuid, p_ngay date) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE a record; kq jsonb;
        BEGIN""" + _CHU + """
            SELECT * INTO a FROM master.du_an WHERE id = p_du_an;
            IF a.id IS NULL OR NOT master.crm_da_duoc_doc(a.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF p_ngay IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_MOC_SAI: cần ngày đọc mốc' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(jsonb_agg(jsonb_build_object('moc_id', m.id, 'ma', m.ma, 'lan', s.lan, 'ten', s.ten, 'ten_tat', s.ten_tat,
                'ngay_du_kien', s.ngay_du_kien, 'ngay_thuc_te', s.ngay_thuc_te,
                'du_an_dang_ban', coalesce((SELECT v.dang_ban FROM master.crm_da_ban_phien_ban v
                    WHERE v.da_ban_id = d.id AND v.hieu_luc_tu <= p_ngay
                      AND (v.hieu_luc_den IS NULL OR p_ngay < v.hieu_luc_den)), false),
                'trang_thai', CASE WHEN s.ngay_thuc_te IS NOT NULL THEN 'DA_XONG'
                                   WHEN s.ngay_du_kien >= p_ngay THEN 'CHUA_DEN' ELSE 'QUA_DU_KIEN' END)
                ORDER BY s.ngay_du_kien, s.ten), '[]'::jsonb) INTO kq
            FROM master.crm_da_ban d JOIN master.crm_da_moc m ON m.da_ban_id = d.id
                JOIN master.crm_da_moc_ls s ON s.moc_id = m.id
            WHERE d.du_an_id = p_du_an AND s.dang_dung AND s.hieu_luc_tu <= p_ngay AND (s.hieu_luc_den IS NULL OR p_ngay < s.hieu_luc_den);
            RETURN kq;
        END $$""",
    """CREATE FUNCTION master.crm_da_moc_ls_doc(p_moc uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE m record;
        BEGIN""" + _CHU + """
            SELECT o.*, d.du_an_id INTO m FROM master.crm_da_moc o JOIN master.crm_da_ban d ON d.id = o.da_ban_id WHERE o.id = p_moc;
            IF m.id IS NULL OR NOT master.crm_da_duoc_doc(m.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy mốc (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            RETURN jsonb_build_object('moc_id', m.id, 'ma', m.ma, 'da_ban_id', m.da_ban_id, 'du_an_id', m.du_an_id,
                'lich_su', (SELECT coalesce(jsonb_agg(to_jsonb(s) ORDER BY s.lan), '[]'::jsonb) FROM master.crm_da_moc_ls s WHERE s.moc_id = p_moc),
                'nhat_ky', (SELECT coalesce(jsonb_agg(to_jsonb(k) ORDER BY k.id), '[]'::jsonb) FROM nhat_ky.su_kien k
                           WHERE k.doi_tuong_bang = 'master.crm_da_moc' AND k.doi_tuong_id = p_moc AND k.phap_nhan_id = m.phap_nhan_id));
        END $$""",
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _BANG),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON """ + _BANG_DS + """ FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    "REVOKE ALL ON " + _BANG_DS + " FROM PUBLIC",
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(_HAM) + " FROM PUBLIC",
)
