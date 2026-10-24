"""CRM G5-B — hằng SQL đối chiếu bản ký ↔ bản sinh (manual + khai Có bắt buộc) dùng chung MỘT engine Source6 (biến thể E5 ``doi_chieu_ban_ky``).

CHỈ HẰNG SỐ. Module này KHÔNG import/sửa ``ha_tang.pg_migrations``, không tự đăng ký/áp migration, không đoán ordinal. Root integration owner
import ``CRM_G5_SQL`` và APPEND thành MỘT migration mới SAU M25/M26 đã chốt (ordinal do owner cấp). Gói này không tuyên bố đã cài.

Nội dung (mọi guard ở CSDL — đường lệnh và SQL trực tiếp trên kết nối chủ bảng đi qua cùng bất biến):
  * đăng ký engine/catalog-binding BẤT BIẾN do chủ CSDL ghi (``crm_g5_dang_ky``): chỉ tham chiếu PN/loại hình/mẫu/danh mục ref-rev-digest/profile
    ĐÃ CÓ + catalog Source6 (id/sha) + implementation + mapping ``{ma, crm_truong, muc}`` tường minh; nhãn VAN_HANH | DEMO_KIEM_THU tách rõ.
    KHÔNG tự seed khi import/HTTP/khởi động; thu hồi bằng dòng ``crm_g5_thu_hoi``;
  * người chạy việc bắt buộc là CẤU HÌNH MÁY CHỦ tường minh (``crm_g5_nguoi_chay``) trỏ phân công CRM/CRM_HD_KIEM hiện hành có sẵn — không
    fallback người tạo/người ký/CFO/người đầu tiên, không tự cấp vai/phân công/phạm vi;
  * hàng đợi bền ``crm_g5_viec``: trigger AFTER INSERT trên ``crm_hd_ky`` (co_sua = true) ghi việc BAT_BUOC trong CHÍNH giao dịch ký (G4 ACK
    PENDING/NOT_SELECTED không đổi) + backfill idempotent; lease hữu hạn/CAS; ý định bất biến ``crm_g5_y_dinh`` (13 trường E5 + SHA);
    kết quả bất biến ``crm_g5_ket_qua``; sự kiện append-only ``crm_g5_su_kien`` (SYSTEM_JOB tách NGUOI_DUNG/HE_THONG);
  * việc hệ thống CHỈ tính/công bố bằng chứng G5 — không duyệt/kích hoạt/ghi sổ, không đánh dấu người chạy đã kiểm;
  * thay hẹp ``crm_kiem_g5_xet`` (nhánh VAN_HANH đọc kết quả hiện hành của đăng ký hiện hành; nhánh SYNTHETIC_FIXTURE giữ NGUYÊN VĂN) và trigger
    ``crm_kiem_xu_ly_lech_kiem`` (nhánh G5 theo chế độ giao dịch; nhánh G7/quyền/append giữ nguyên).
"""

_G_LOI = "USING ERRCODE = 'P0001'"
_G_CHU = """
            IF NOT master.la_chu_bang('master.crm_mau_phien_ban'::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_MAY_CHU: chỉ đường ghi tin cậy của máy chủ (chủ bảng) được thực hiện lệnh mẫu/bộ chuẩn' """ + _G_LOI + """;
            END IF;"""
_G_REPLAY = """
            cu := master.crm_g_bn_tra(d.pn, {a}, p_khoa, p_h);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;"""
_G_KET = """
            PERFORM master.crm_g_bn_ghi(d.pn, {a}, p_khoa, p_h, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);"""
_G_NK = "INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do) VALUES ({pn}, ai, {loai}, {bang}, {id}, {hd}, {sau}, {ly});"
_GK_SHA = "encode(sha256(convert_to({x}::text, 'UTF8')), 'hex')"
_HEX = "'^[0-9a-f]{64}$'"

_G5_BANG_MOI = ("crm_g5_dang_ky", "crm_g5_nguoi_chay", "crm_g5_thu_hoi", "crm_g5_viec", "crm_g5_y_dinh", "crm_g5_ket_qua", "crm_g5_su_kien")
_G5_MO = ("CHO", "DANG_CHAY", "CHUA_RO", "CHO_CAU_HINH")
_G5_MO_SQL = "('CHO','DANG_CHAY','CHUA_RO','CHO_CAU_HINH')"
# 13 khóa ngoài E5 (đã sắp xếp — so với array_agg ORDER BY)
_E5_KHOA = ("ARRAY['catalog_binding','catalog_binding_sha256','catalog_id','catalog_sha256','contract','expected','expected_sha256','loai_hop_dong',"
            "'mode','request_id','signed_pdf_sha256','source_sha256','tham_so']")
_G5_KHOA = ("ARRAY['catalog_binding_sha256','coverage','expected_sha256','g3_pdf_sha256','kieu','lech','signed_pdf_sha256','source_sha256',"
            "'thieu','trang_thai']")
_LECH_KHOA = "ARRAY['gia_tri_ban_ky','gia_tri_ky_vong','kieu','ma','muc','trich_dan','vi_tri_do_duoc']"
# lineage bản ký (đúng hàng crm_hd_ky đã ký; soan_rev_id bất biến) — dùng cho kiểm ý định và ngữ cảnh
_LINEAGE = ("jsonb_build_object('ky_id', k.id, 'hop_dong_id', k.hop_dong_id, 'soan_id', k.soan_id, 'soan_rev_id', k.soan_rev_id, 'xuat_id', k.xuat_id, "
            "'mau_phien_ban_id', k.mau_phien_ban_id, 'anh_xa_id', k.anh_xa_id, 'revision', k.revision, 'g3_input_sha256', k.g3_input_sha256, "
            "'g3_docx_sha256', k.g3_docx_sha256, 'g3_pdf_sha256', k.g3_pdf_sha256, 'ban_do_sha256', k.ban_do_sha256, 'danh_muc_ref', k.danh_muc_ref, "
            "'danh_muc_rev', k.danh_muc_rev, 'danh_muc_digest', k.danh_muc_digest, 'profile_sha256', k.profile_sha256, 'du_lieu_sha256', k.du_lieu_sha256)")
# mở đầu lệnh người dùng: máy chủ (chủ bảng) → ghim quyền + phạm vi → đích/quyền lệnh hiện hành (KT + CRM_HD_KIEM + phạm vi, không tự kiểm bản mình ghi)
_G5_MO_LENH = _G_CHU + """
            PERFORM master.crm_g_ghim_quyen((SELECT k0.phap_nhan_id FROM master.crm_hd_ky k0 WHERE k0.id = p_ky));
            PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = p_ky AND b.thu_hoi_luc IS NULL FOR SHARE;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, true);
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;"""
_G5_NK_LENH = _G_NK.format(pn="d.pn", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="{hd}",
                           sau="jsonb_build_object('viec_id', v.id, 'request_id', master.crm_g5_request_id(v.id, v.the_he))", ly="NULL")

CRM_G5_SQL = (
    "SET LOCAL check_function_bodies = off",
    # ======================================================================= đăng ký engine/catalog-binding (chủ CSDL ghi; bất biến; không master thứ hai)
    """CREATE TABLE master.crm_g5_dang_ky (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai_hinh_id uuid NOT NULL,
        mau_phien_ban_id uuid NOT NULL,
        danh_muc_ref text NOT NULL,
        danh_muc_rev integer NOT NULL CHECK (danh_muc_rev >= 1),
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ """ + _HEX + """),
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ """ + _HEX + """),
        loai_hop_dong text NOT NULL CHECK (loai_hop_dong ~ '^[A-Z0-9_]{1,40}$'),
        catalog_id text NOT NULL CHECK (catalog_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
        catalog_sha256 text NOT NULL CHECK (catalog_sha256 ~ """ + _HEX + """),
        implementation_sha256 text NOT NULL CHECK (implementation_sha256 ~ """ + _HEX + """),
        capability text NOT NULL CHECK (capability = 'doi_chieu_ban_ky'),
        mapping jsonb NOT NULL CHECK (jsonb_typeof(mapping) = 'array' AND jsonb_array_length(mapping) BETWEEN 1 AND 500),
        mapping_sha256 text NOT NULL CHECK (mapping_sha256 ~ """ + _HEX + """),
        nhan text NOT NULL CHECK (nhan IN ('VAN_HANH','DEMO_KIEM_THU')),
        ghi_chu text CHECK (ghi_chu IS NULL OR length(ghi_chu) <= 1000),
        tao_boi text NOT NULL DEFAULT current_user,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        FOREIGN KEY (mau_phien_ban_id, phap_nhan_id) REFERENCES master.crm_mau_phien_ban (id, phap_nhan_id))""",
    "CREATE TRIGGER crm_g5_dang_ky_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_dang_ky FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_dang_ky_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v_loai uuid; e jsonb; v_ma text[] := ARRAY[]::text[]; v_kieu text;
        BEGIN
            SELECT m.loai_hinh_id INTO v_loai FROM master.crm_mau_phien_ban pv JOIN master.crm_mau m ON m.id = pv.mau_id WHERE pv.id = NEW.mau_phien_ban_id;
            IF v_loai IS DISTINCT FROM NEW.loai_hinh_id THEN
                RAISE EXCEPTION 'CRM_G5_DANG_KY_SAI: mẫu không thuộc loại hình đăng ký' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = NEW.loai_hinh_id AND t.danh_muc_ref = NEW.danh_muc_ref
                           AND t.revision = NEW.danh_muc_rev)
               OR master.crm_g_danh_muc_digest(NEW.loai_hinh_id, NEW.danh_muc_ref, NEW.danh_muc_rev) IS DISTINCT FROM NEW.danh_muc_digest THEN
                RAISE EXCEPTION 'CRM_G5_DANG_KY_SAI: danh mục ref/rev/digest không khớp danh mục đã có' USING ERRCODE = 'P0001';
            END IF;
            IF """ + _GK_SHA.format(x="NEW.mapping") + """ <> NEW.mapping_sha256 THEN
                RAISE EXCEPTION 'CRM_G5_DANG_KY_SAI: mapping_sha256 không khớp mapping' USING ERRCODE = 'P0001';
            END IF;
            FOR e IN SELECT x FROM jsonb_array_elements(NEW.mapping) x LOOP
                IF jsonb_typeof(e) <> 'object' OR (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(e) z) IS DISTINCT FROM ARRAY['crm_truong','ma','muc']
                   OR jsonb_typeof(e -> 'ma') <> 'string' OR (e ->> 'ma') !~ '^[A-Z0-9_]{1,60}$' OR (e ->> 'ma') = ANY (v_ma)
                   OR jsonb_typeof(e -> 'muc') <> 'number' OR (e ->> 'muc') !~ '^[0-3]$'
                   OR jsonb_typeof(e -> 'crm_truong') <> 'string' THEN
                    RAISE EXCEPTION 'CRM_G5_DANG_KY_SAI: mapping phải là {ma, crm_truong, muc 0..3}, mã duy nhất' USING ERRCODE = 'P0001';
                END IF;
                IF e ->> 'crm_truong' <> 'crm.lich' THEN
                    SELECT t.kieu INTO v_kieu FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = NEW.loai_hinh_id AND t.danh_muc_ref = NEW.danh_muc_ref
                        AND t.revision = NEW.danh_muc_rev AND t.khoa = e ->> 'crm_truong';
                    IF v_kieu IS NULL OR v_kieu = 'bang' THEN
                        RAISE EXCEPTION 'CRM_G5_DANG_KY_SAI: trường CRM % không thuộc danh mục đã ghim (hoặc kiểu bảng chưa hỗ trợ ngoài crm.lich)', e ->> 'crm_truong' USING ERRCODE = 'P0001';
                    END IF;
                END IF;
                v_ma := v_ma || (e ->> 'ma');
            END LOOP;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_dang_ky_kiem BEFORE INSERT ON master.crm_g5_dang_ky FOR EACH ROW EXECUTE FUNCTION master.crm_g5_dang_ky_kiem()",
    # ======================================================================= người chạy việc bắt buộc (cấu hình máy chủ tường minh; không tự cấp)
    """CREATE TABLE master.crm_g5_nguoi_chay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        phan_cong_id uuid NOT NULL REFERENCES master.phan_cong_hanh_dong(id),
        nguoi_dung_id uuid NOT NULL,
        ghi_chu text CHECK (ghi_chu IS NULL OR length(ghi_chu) <= 1000),
        tao_boi text NOT NULL DEFAULT current_user,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE TRIGGER crm_g5_nguoi_chay_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_nguoi_chay FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_nguoi_chay_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.phan_cong_hanh_dong a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
                           WHERE a.id = NEW.phan_cong_id AND a.nguoi_dung_id = NEW.nguoi_dung_id AND a.phap_nhan_id = NEW.phap_nhan_id
                             AND a.module = 'CRM' AND a.hanh_dong = 'CRM_HD_KIEM' AND a.thu_hoi_luc IS NULL AND n.trang_thai = 'HOAT_DONG') THEN
                RAISE EXCEPTION 'CRM_G5_NGUOI_CHAY_SAI: phải trỏ phân công CRM_HD_KIEM hiện hành có sẵn của đúng người dùng/PN (không tự cấp)' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_nguoi_chay_kiem BEFORE INSERT ON master.crm_g5_nguoi_chay FOR EACH ROW EXECUTE FUNCTION master.crm_g5_nguoi_chay_kiem()",
    """CREATE TABLE master.crm_g5_thu_hoi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        loai text NOT NULL CHECK (loai IN ('DANG_KY','NGUOI_CHAY')),
        doi_tuong_id uuid NOT NULL,
        ly_do text NOT NULL CHECK (length(ly_do) BETWEEN 1 AND 1000 AND btrim(ly_do) <> ''),
        tao_boi text NOT NULL DEFAULT current_user,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (loai, doi_tuong_id))""",
    "CREATE TRIGGER crm_g5_thu_hoi_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_thu_hoi FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_thu_hoi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF (NEW.loai = 'DANG_KY' AND NOT EXISTS (SELECT 1 FROM master.crm_g5_dang_ky x WHERE x.id = NEW.doi_tuong_id))
               OR (NEW.loai = 'NGUOI_CHAY' AND NOT EXISTS (SELECT 1 FROM master.crm_g5_nguoi_chay x WHERE x.id = NEW.doi_tuong_id)) THEN
                RAISE EXCEPTION 'CRM_G5_THU_HOI_SAI: không có đối tượng để thu hồi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_thu_hoi_kiem BEFORE INSERT ON master.crm_g5_thu_hoi FOR EACH ROW EXECUTE FUNCTION master.crm_g5_thu_hoi_kiem()",
    # đăng ký hiện hành của một bản ký: đúng PN/loại hình/mẫu/danh mục ref-rev-digest/profile ĐÃ GHIM ở bản ký; mới nhất chưa thu hồi
    """CREATE OR REPLACE FUNCTION master.crm_g5_dang_ky_hien_hanh(p_ky uuid) RETURNS SETOF master.crm_g5_dang_ky
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT x.* FROM master.crm_hd_ky k JOIN master.crm_hd_soan s ON s.id = k.soan_id
        JOIN master.crm_g5_dang_ky x ON x.phap_nhan_id = k.phap_nhan_id AND x.loai_hinh_id = s.loai_hinh_id AND x.mau_phien_ban_id = k.mau_phien_ban_id
             AND x.danh_muc_ref = k.danh_muc_ref AND x.danh_muc_rev = k.danh_muc_rev AND x.danh_muc_digest = k.danh_muc_digest
             AND x.profile_sha256 = k.profile_sha256
        WHERE k.id = p_ky AND NOT EXISTS (SELECT 1 FROM master.crm_g5_thu_hoi t WHERE t.loai = 'DANG_KY' AND t.doi_tuong_id = x.id)
        ORDER BY x.thu_tu DESC LIMIT 1
        $$""",
    # người chạy hiện hành của PN: cấu hình mới nhất chưa thu hồi, phân công còn hiệu lực, người dùng hoạt động
    """CREATE OR REPLACE FUNCTION master.crm_g5_nguoi_chay_hien_hanh(p_pn uuid, OUT cau_hinh_id uuid, OUT nguoi_dung_id uuid, OUT dang_nhap text)
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT c.id, n.id, n.dang_nhap FROM master.crm_g5_nguoi_chay c
        JOIN master.phan_cong_hanh_dong a ON a.id = c.phan_cong_id AND a.thu_hoi_luc IS NULL AND a.nguoi_dung_id = c.nguoi_dung_id
        JOIN master.nguoi_dung n ON n.id = c.nguoi_dung_id AND n.trang_thai = 'HOAT_DONG'
        WHERE c.phap_nhan_id = p_pn AND NOT EXISTS (SELECT 1 FROM master.crm_g5_thu_hoi t WHERE t.loai = 'NGUOI_CHAY' AND t.doi_tuong_id = c.id)
        ORDER BY c.thu_tu DESC LIMIT 1
        $$""",
    # ======================================================================= hàng đợi bền + ý định + kết quả + sự kiện
    """CREATE TABLE master.crm_g5_viec (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        ky_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN ('BAT_BUOC','THU_CONG')),
        khoi_tao_loai text NOT NULL CHECK (khoi_tao_loai IN ('HE_THONG','NGUOI_DUNG')),
        khoi_tao_boi text NOT NULL CHECK (length(khoi_tao_boi) BETWEEN 1 AND 200),
        the_he integer NOT NULL DEFAULT 1 CHECK (the_he >= 1),
        trang_thai text NOT NULL CHECK (trang_thai IN ('CHO','DANG_CHAY','CHUA_RO','CHO_CAU_HINH','XONG','LOI')),
        ly_do text CHECK (ly_do IS NULL OR ly_do ~ '^[A-Z0-9_]{1,80}$'),
        lease_boi text CHECK (lease_boi IS NULL OR lease_boi ~ '^[A-Za-z0-9_.:-]{1,120}$'),
        lease_den timestamptz,
        thu_lai_sau timestamptz NOT NULL DEFAULT now(),
        so_lan integer NOT NULL DEFAULT 0 CHECK (so_lan >= 0),
        ket_qua_id uuid,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky (id, phap_nhan_id),
        CHECK ((trang_thai = 'DANG_CHAY') = (lease_boi IS NOT NULL AND lease_den IS NOT NULL)),
        CHECK ((loai = 'BAT_BUOC') = (khoi_tao_loai = 'HE_THONG')),
        CHECK (trang_thai <> 'LOI' OR loai = 'THU_CONG'))""",
    "CREATE UNIQUE INDEX crm_g5_viec_bat_buoc_uq ON master.crm_g5_viec (ky_id) WHERE loai = 'BAT_BUOC'",
    "CREATE UNIQUE INDEX crm_g5_viec_thu_cong_mo_uq ON master.crm_g5_viec (ky_id) WHERE loai = 'THU_CONG' AND trang_thai IN " + _G5_MO_SQL,
    "CREATE INDEX crm_g5_viec_den_han_ix ON master.crm_g5_viec (thu_lai_sau, thu_tu) WHERE trang_thai IN " + _G5_MO_SQL,
    "CREATE TRIGGER crm_g5_viec_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_viec FOR EACH ROW EXECUTE FUNCTION master.crm_g_chi_chu()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_viec_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'CHO' OR NEW.the_he <> 1 OR NEW.so_lan <> 0 OR NEW.ket_qua_id IS NOT NULL
                   OR (NEW.loai = 'BAT_BUOC' AND NOT (SELECT k.co_sua FROM master.crm_hd_ky k WHERE k.id = NEW.ky_id)) THEN
                    RAISE EXCEPTION 'CRM_G5_VIEC_SAI: việc mới phải CHO thế hệ 1; việc bắt buộc chỉ cho bản ký khai Có sửa' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.thu_tu, NEW.ky_id, NEW.phap_nhan_id, NEW.loai, NEW.khoi_tao_loai, NEW.khoi_tao_boi, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.thu_tu, OLD.ky_id, OLD.phap_nhan_id, OLD.loai, OLD.khoi_tao_loai, OLD.khoi_tao_boi, OLD.tao_luc)
               OR OLD.trang_thai IN ('XONG','LOI') OR NEW.the_he < OLD.the_he OR NEW.so_lan < OLD.so_lan
               OR (NEW.trang_thai = 'XONG') <> (NEW.ket_qua_id IS NOT NULL) THEN
                RAISE EXCEPTION 'CRM_G5_VIEC_BAT_BIEN: không sửa định danh việc, không mở lại việc đã đóng, thế hệ/số lần không lùi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_viec_kiem BEFORE INSERT OR UPDATE ON master.crm_g5_viec FOR EACH ROW EXECUTE FUNCTION master.crm_g5_viec_kiem()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_request_id(p_viec uuid, p_the_he integer) RETURNS text
        LANGUAGE sql IMMUTABLE SET search_path = pg_temp AS $$
        SELECT 'crm-g5-' || p_viec::text || '-' || p_the_he::text
        $$""",
    """CREATE TABLE master.crm_g5_y_dinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        viec_id uuid NOT NULL REFERENCES master.crm_g5_viec(id),
        the_he integer NOT NULL CHECK (the_he >= 1),
        ky_id uuid NOT NULL REFERENCES master.crm_hd_ky(id),
        dang_ky_id uuid NOT NULL REFERENCES master.crm_g5_dang_ky(id),
        request_id text NOT NULL UNIQUE,
        ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ """ + _HEX + """),
        g3_pdf_sha256 text NOT NULL CHECK (g3_pdf_sha256 ~ """ + _HEX + """),
        expected jsonb NOT NULL,
        expected_sha256 text NOT NULL CHECK (expected_sha256 ~ """ + _HEX + """),
        binding jsonb NOT NULL,
        binding_sha256 text NOT NULL CHECK (binding_sha256 ~ """ + _HEX + """),
        body jsonb NOT NULL,
        body_sha256 text NOT NULL CHECK (body_sha256 ~ """ + _HEX + """),
        tac_nhan_loai text NOT NULL CHECK (tac_nhan_loai IN ('SYSTEM_JOB','NGUOI_DUNG')),
        tac_nhan text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (viec_id, the_he))""",
    "CREATE TRIGGER crm_g5_y_dinh_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_y_dinh FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # ý định = ĐÚNG bản ký đã ghim (lineage/PDF) + đăng ký HIỆN HÀNH + body 13 khóa nhất quán; SHA canonical do máy chủ tính (Python) và ghi lại
    """CREATE OR REPLACE FUNCTION master.crm_g5_y_dinh_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v record; k record; dk record; v_ma jsonb; v_ts jsonb;
        BEGIN
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = NEW.viec_id;
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
            SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(NEW.ky_id);
            IF v.id IS NULL OR k.id IS NULL OR v.ky_id <> NEW.ky_id OR v.trang_thai <> 'DANG_CHAY' OR v.the_he <> NEW.the_he
               OR NEW.request_id <> master.crm_g5_request_id(v.id, v.the_he) OR dk.id IS DISTINCT FROM NEW.dang_ky_id
               OR NEW.ky_pdf_sha256 <> k.ky_pdf_sha256 OR NEW.g3_pdf_sha256 <> k.g3_pdf_sha256 THEN
                RAISE EXCEPTION 'CRM_G5_Y_DINH_SAI: ý định phải thuộc việc đang chạy, đúng bản ký và đăng ký hiện hành' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(jsonb_agg(e -> 'ma' ORDER BY o), '[]'::jsonb) INTO v_ma FROM jsonb_array_elements(dk.mapping) WITH ORDINALITY AS t(e, o);
            SELECT coalesce(jsonb_agg(e -> 'ma' ORDER BY o), '[]'::jsonb) INTO v_ts
                FROM jsonb_array_elements(CASE WHEN jsonb_typeof(NEW.expected -> 'tham_so') = 'array' THEN NEW.expected -> 'tham_so' ELSE '[]'::jsonb END)
                     WITH ORDINALITY AS t(e, o);
            IF jsonb_typeof(NEW.expected) <> 'object' OR (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(NEW.expected) z) IS DISTINCT FROM ARRAY['kieu','lineage','tham_so']
               OR NEW.expected ->> 'kieu' <> 'CRM_G5_EXPECTED_V1' OR NEW.expected -> 'lineage' <> """ + _LINEAGE + """
               OR v_ts <> v_ma
               OR EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.expected -> 'tham_so') e
                          WHERE jsonb_typeof(e) <> 'object' OR (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(e) z) IS DISTINCT FROM ARRAY['gia_tri','kieu','ma']
                             OR coalesce(e ->> 'kieu', '') NOT IN ('text','so','ngay','tien','bang')) THEN
                RAISE EXCEPTION 'CRM_G5_Y_DINH_SAI: expected phải là CRM_G5_EXPECTED_V1 của đúng bản ký đã ghim, mã theo đúng mapping đăng ký' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_typeof(NEW.binding) <> 'object'
               OR NEW.binding <> jsonb_build_object('kieu', 'CRM_G5_CATALOG_BINDING_V1', 'loai_hop_dong', dk.loai_hop_dong, 'catalog_id', dk.catalog_id,
                                                    'catalog_sha256', dk.catalog_sha256, 'danh_muc_ref', k.danh_muc_ref, 'danh_muc_rev', k.danh_muc_rev,
                                                    'danh_muc_digest', k.danh_muc_digest, 'mau_phien_ban_id', k.mau_phien_ban_id,
                                                    'profile_sha256', k.profile_sha256, 'mapping', dk.mapping) THEN
                RAISE EXCEPTION 'CRM_G5_Y_DINH_SAI: catalog_binding phải đúng đăng ký hiện hành + danh mục/mẫu/profile đã ghim' USING ERRCODE = 'P0001';
            END IF;
            IF (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(NEW.body) z) IS DISTINCT FROM """ + _E5_KHOA + """
               OR NEW.body <> jsonb_build_object('contract', 'trich-tham-so-common/v1', 'mode', 'doi_chieu_ban_ky', 'loai_hop_dong', dk.loai_hop_dong,
                                                 'catalog_id', dk.catalog_id, 'catalog_sha256', dk.catalog_sha256, 'source_sha256', k.ky_pdf_sha256,
                                                 'request_id', NEW.request_id, 'tham_so', v_ma, 'signed_pdf_sha256', k.ky_pdf_sha256,
                                                 'expected', NEW.expected, 'expected_sha256', NEW.expected_sha256,
                                                 'catalog_binding', NEW.binding, 'catalog_binding_sha256', NEW.binding_sha256) THEN
                RAISE EXCEPTION 'CRM_G5_Y_DINH_SAI: body E5 phải đúng 13 trường nhất quán với expected/binding/bản ký' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_y_dinh_kiem BEFORE INSERT ON master.crm_g5_y_dinh FOR EACH ROW EXECUTE FUNCTION master.crm_g5_y_dinh_kiem()",
    """CREATE TABLE master.crm_g5_ket_qua (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        ky_id uuid NOT NULL REFERENCES master.crm_hd_ky(id),
        phap_nhan_id uuid NOT NULL,
        viec_id uuid NOT NULL REFERENCES master.crm_g5_viec(id),
        y_dinh_id uuid NOT NULL UNIQUE REFERENCES master.crm_g5_y_dinh(id),
        dang_ky_id uuid NOT NULL REFERENCES master.crm_g5_dang_ky(id),
        request_id text NOT NULL,
        trang_thai text NOT NULL CHECK (trang_thai IN ('KHOP','LECH','CHUA_DOI_CHIEU_DUOC')),
        coverage jsonb NOT NULL CHECK (jsonb_typeof(coverage) = 'array'),
        lech jsonb NOT NULL CHECK (jsonb_typeof(lech) = 'array'),
        thieu jsonb NOT NULL CHECK (jsonb_typeof(thieu) = 'array'),
        g5 jsonb NOT NULL CHECK (jsonb_typeof(g5) = 'object'),
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ """ + _HEX + """),
        raw_len bigint NOT NULL CHECK (raw_len > 0),
        luot text NOT NULL CHECK (luot ~ '^[A-Za-z0-9_.:-]{1,120}$'),
        body_sha256 text NOT NULL CHECK (body_sha256 ~ """ + _HEX + """),
        expected_sha256 text NOT NULL CHECK (expected_sha256 ~ """ + _HEX + """),
        binding_sha256 text NOT NULL CHECK (binding_sha256 ~ """ + _HEX + """),
        implementation_sha256 text NOT NULL CHECK (implementation_sha256 ~ """ + _HEX + """),
        ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ """ + _HEX + """),
        g3_pdf_sha256 text NOT NULL CHECK (g3_pdf_sha256 ~ """ + _HEX + """),
        tac_nhan_loai text NOT NULL CHECK (tac_nhan_loai IN ('SYSTEM_JOB','NGUOI_DUNG')),
        tac_nhan text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE TRIGGER crm_g5_ket_qua_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_ket_qua FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # kết quả: đúng ý định của việc đang chạy + quy tắc cấu trúc KHOP/LECH/CHUA (Python đã kiểm envelope niêm phong; CSDL kiểm lại cấu trúc)
    """CREATE OR REPLACE FUNCTION master.crm_g5_ket_qua_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE y record; v record; dk record; e jsonb; x jsonb; v_ma text[]; v_cov text[]; v_th text[]; v_du boolean;
        BEGIN
            SELECT * INTO y FROM master.crm_g5_y_dinh WHERE id = NEW.y_dinh_id;
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = NEW.viec_id;
            SELECT * INTO dk FROM master.crm_g5_dang_ky WHERE id = NEW.dang_ky_id;
            IF y.id IS NULL OR v.id IS NULL OR y.viec_id <> v.id OR y.the_he <> v.the_he OR v.trang_thai <> 'DANG_CHAY'
               OR ROW(NEW.ky_id, NEW.phap_nhan_id, NEW.request_id, NEW.dang_ky_id, NEW.body_sha256, NEW.expected_sha256, NEW.binding_sha256,
                      NEW.ky_pdf_sha256, NEW.g3_pdf_sha256, NEW.implementation_sha256)
                  IS DISTINCT FROM ROW(y.ky_id, v.phap_nhan_id, y.request_id, y.dang_ky_id, y.body_sha256, y.expected_sha256, y.binding_sha256,
                                       y.ky_pdf_sha256, y.g3_pdf_sha256, dk.implementation_sha256) THEN
                RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: kết quả không thuộc đúng ý định/việc đang chạy/đăng ký' USING ERRCODE = 'P0001';
            END IF;
            IF (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(NEW.g5) z) IS DISTINCT FROM """ + _G5_KHOA + """
               OR NEW.g5 ->> 'kieu' <> 'CRM_G5_COMPARE_RESULT_V1' OR NEW.g5 ->> 'signed_pdf_sha256' <> y.ky_pdf_sha256
               OR NEW.g5 ->> 'source_sha256' <> y.ky_pdf_sha256 OR NEW.g5 ->> 'expected_sha256' <> y.expected_sha256
               OR NEW.g5 ->> 'catalog_binding_sha256' <> y.binding_sha256 OR NEW.g5 ->> 'g3_pdf_sha256' <> y.g3_pdf_sha256
               OR NEW.g5 ->> 'trang_thai' <> NEW.trang_thai OR NEW.g5 -> 'coverage' <> NEW.coverage OR NEW.g5 -> 'lech' <> NEW.lech
               OR NEW.g5 -> 'thieu' <> NEW.thieu THEN
                RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: g5 phải là CRM_G5_COMPARE_RESULT_V1 khớp SHA ý định và trường kết quả' USING ERRCODE = 'P0001';
            END IF;
            SELECT array_agg(t.e ->> 'ma' ORDER BY t.o) INTO v_ma FROM jsonb_array_elements(y.expected -> 'tham_so') WITH ORDINALITY AS t(e, o);
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.coverage) z WHERE jsonb_typeof(z) <> 'string' OR NOT (z #>> '{}') = ANY (v_ma))
               OR EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.thieu) z WHERE jsonb_typeof(z) <> 'string' OR NOT (z #>> '{}') = ANY (v_ma))
               OR (SELECT count(*) FROM jsonb_array_elements(NEW.coverage)) <> (SELECT count(DISTINCT z) FROM jsonb_array_elements(NEW.coverage) z)
               OR (SELECT count(*) FROM jsonb_array_elements(NEW.thieu)) <> (SELECT count(DISTINCT z) FROM jsonb_array_elements(NEW.thieu) z)
               OR EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.thieu) z WHERE z IN (SELECT w FROM jsonb_array_elements(NEW.coverage) w)) THEN
                RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: coverage/thieu phải là mã đã yêu cầu, không trùng, không giao nhau' USING ERRCODE = 'P0001';
            END IF;
            SELECT array_agg(z #>> '{}') INTO v_cov FROM jsonb_array_elements(NEW.coverage) z;
            SELECT array_agg(z #>> '{}') INTO v_th FROM jsonb_array_elements(NEW.thieu) z;
            FOR e IN SELECT z FROM jsonb_array_elements(NEW.lech) z LOOP
                SELECT t INTO x FROM jsonb_array_elements(y.expected -> 'tham_so') t WHERE t ->> 'ma' = e ->> 'ma';
                IF jsonb_typeof(e) <> 'object' OR (SELECT array_agg(z ORDER BY z) FROM jsonb_object_keys(e) z) IS DISTINCT FROM """ + _LECH_KHOA + """
                   OR x IS NULL OR NOT (e ->> 'ma') = ANY (coalesce(v_cov, ARRAY[]::text[]))
                   OR e -> 'muc' <> (SELECT m -> 'muc' FROM jsonb_array_elements(dk.mapping) m WHERE m ->> 'ma' = e ->> 'ma')
                   OR e ->> 'kieu' <> x ->> 'kieu' OR e -> 'gia_tri_ky_vong' <> x -> 'gia_tri'
                   OR (SELECT count(*) FROM jsonb_array_elements(NEW.lech) w WHERE w ->> 'ma' = e ->> 'ma') <> 1 THEN
                    RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: mỗi lệch phải đúng 7 khóa, mã đã phủ, mức theo catalog đã ghim, giá trị kỳ vọng đúng expected' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'LECH' AND (jsonb_typeof(e -> 'trich_dan') <> 'string' OR btrim(e ->> 'trich_dan') = ''
                                                 OR jsonb_typeof(e -> 'vi_tri_do_duoc') NOT IN ('string','object','array')
                                                 OR e -> 'vi_tri_do_duoc' IN ('""'::jsonb, '{}'::jsonb, '[]'::jsonb)) THEN
                    RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: LECH cần trích dẫn + vị trí đo được thật từ bản ký' USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
            v_du := coalesce(cardinality(v_cov), 0) = cardinality(v_ma) AND coalesce(cardinality(v_th), 0) = 0;
            IF (NEW.trang_thai = 'KHOP' AND NOT (v_du AND jsonb_array_length(NEW.lech) = 0))
               OR (NEW.trang_thai = 'LECH' AND NOT (v_du AND jsonb_array_length(NEW.lech) >= 1)) THEN
                RAISE EXCEPTION 'CRM_G5_KET_QUA_SAI: KHOP chỉ khi phủ đủ và 0 lệch; LECH chỉ khi phủ đủ và ≥1 lệch' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g5_ket_qua_kiem BEFORE INSERT ON master.crm_g5_ket_qua FOR EACH ROW EXECUTE FUNCTION master.crm_g5_ket_qua_kiem()",
    """CREATE TABLE master.crm_g5_su_kien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        viec_id uuid NOT NULL REFERENCES master.crm_g5_viec(id),
        ky_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai ~ '^[A-Z0-9_]{1,40}$'),
        tac_nhan_loai text NOT NULL CHECK (tac_nhan_loai IN ('SYSTEM_JOB','NGUOI_DUNG','HE_THONG')),
        tac_nhan text NOT NULL CHECK (length(tac_nhan) BETWEEN 1 AND 200),
        chi_tiet jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(chi_tiet) = 'object'),
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE TRIGGER crm_g5_su_kien_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g5_su_kien FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_g5_ghi_su_kien(p_viec uuid, p_loai text, p_tac_nhan_loai text, p_tac_nhan text, p_chi_tiet jsonb) RETURNS void
        LANGUAGE sql SET search_path = master, pg_temp AS $$
        INSERT INTO master.crm_g5_su_kien (viec_id, ky_id, phap_nhan_id, loai, tac_nhan_loai, tac_nhan, chi_tiet)
        SELECT v.id, v.ky_id, v.phap_nhan_id, p_loai, p_tac_nhan_loai, coalesce(p_tac_nhan, 'khong_ro'), coalesce(p_chi_tiet, '{}'::jsonb)
        FROM master.crm_g5_viec v WHERE v.id = p_viec
        $$""",
    # ======================================================================= việc bắt buộc trong CHÍNH giao dịch ký (G4 không đổi) + backfill
    """CREATE OR REPLACE FUNCTION master.crm_g5_tao_bat_buoc() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v_id uuid;
        BEGIN
            INSERT INTO master.crm_g5_viec (ky_id, phap_nhan_id, loai, khoi_tao_loai, khoi_tao_boi, trang_thai, ly_do)
                VALUES (NEW.id, NEW.phap_nhan_id, 'BAT_BUOC', 'HE_THONG', 'G4_KY_KHAI_CO', 'CHO', 'BAT_BUOC_KHAI_CO')
                ON CONFLICT DO NOTHING RETURNING id INTO v_id;
            IF v_id IS NOT NULL THEN
                PERFORM master.crm_g5_ghi_su_kien(v_id, 'TAO', 'HE_THONG', 'G4_KY_KHAI_CO', jsonb_build_object('ky_tao_boi', NEW.tao_boi));
            END IF;
            RETURN NULL;
        END $$""",
    """CREATE TRIGGER crm_g5_tao_bat_buoc AFTER INSERT ON master.crm_hd_ky FOR EACH ROW WHEN (NEW.co_sua)
        EXECUTE FUNCTION master.crm_g5_tao_bat_buoc()""",
    """WITH moi AS (
        INSERT INTO master.crm_g5_viec (ky_id, phap_nhan_id, loai, khoi_tao_loai, khoi_tao_boi, trang_thai, ly_do)
        SELECT k.id, k.phap_nhan_id, 'BAT_BUOC', 'HE_THONG', 'BACKFILL_G5B', 'CHO', 'BAT_BUOC_KHAI_CO' FROM master.crm_hd_ky k
        WHERE k.co_sua AND NOT EXISTS (SELECT 1 FROM master.crm_g5_viec v WHERE v.ky_id = k.id AND v.loai = 'BAT_BUOC')
        ON CONFLICT DO NOTHING
        RETURNING id, ky_id, phap_nhan_id)
    INSERT INTO master.crm_g5_su_kien (viec_id, ky_id, phap_nhan_id, loai, tac_nhan_loai, tac_nhan, chi_tiet)
        SELECT id, ky_id, phap_nhan_id, 'TAO', 'HE_THONG', 'BACKFILL_G5B', '{}'::jsonb FROM moi""",
    # ======================================================================= ngữ cảnh (CAS cho trình duyệt) + ACK
    """CREATE OR REPLACE FUNCTION master.crm_g5_ngu_canh(p_ky uuid) RETURNS text
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE k record; dk record; x record; v record;
        BEGIN
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(p_ky);
            SELECT * INTO x FROM master.crm_g5_ket_qua WHERE ky_id = p_ky ORDER BY thu_tu DESC LIMIT 1;
            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND trang_thai IN """ + _G5_MO_SQL + """ ORDER BY thu_tu DESC LIMIT 1;
            RETURN """ + _GK_SHA.format(x="""jsonb_build_object('kieu', 'CRM_G5_CONTEXT_V1', 'ky_id', k.id, 'ky_pdf_sha256', k.ky_pdf_sha256,
                                                  'g3_pdf_sha256', k.g3_pdf_sha256, 'soan_rev_id', k.soan_rev_id, 'dang_ky_id', dk.id,
                                                  'result_id', x.id, 'job_id', v.id, 'the_he', v.the_he)""") + """;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g5_ack(p_ky uuid, p_ctx text, p_viec uuid) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT jsonb_build_object('kieu', 'CRM_G5_ACK_V1', 'ky_id', p_ky, 'context_sha256', p_ctx, 'job_id', v.id,
                                  'request_id', master.crm_g5_request_id(v.id, v.the_he), 'state', v.trang_thai,
                                  'current_result_id', (SELECT x.id FROM master.crm_g5_ket_qua x WHERE x.ky_id = p_ky ORDER BY x.thu_tu DESC LIMIT 1))
        FROM master.crm_g5_viec v WHERE v.id = p_viec
        $$""",
    # ======================================================================= lệnh người dùng (quyền lệnh hiện hành; biên nhận; CAS ngữ cảnh)
    # Chạy thủ công: tạo việc THU_CONG (hoặc tham gia việc thủ công đang mở) — chạy dưới CHÍNH người đăng nhập; không gọi engine trong giao dịch
    """CREATE OR REPLACE FUNCTION master.crm_g5_chay(p_khoa text, p_h text, p_ky uuid, p_ctx text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; cu jsonb; kq jsonb; k record; v record; v_moi boolean := false;
        BEGIN""" + _G5_MO_LENH + _G_REPLAY.format(a="'CRM_G5_CHAY'") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g5|' || p_ky::text, 0));
            IF p_ctx IS NULL OR p_ctx IS DISTINCT FROM master.crm_g5_ngu_canh(p_ky) THEN
                RAISE EXCEPTION 'CRM_G5_NGU_CANH_CU: trạng thái đối chiếu đã đổi — tải lại rồi thao tác' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND loai = 'THU_CONG' AND trang_thai IN """ + _G5_MO_SQL + """ FOR UPDATE;
            IF v.id IS NULL THEN
                INSERT INTO master.crm_g5_viec (ky_id, phap_nhan_id, loai, khoi_tao_loai, khoi_tao_boi, trang_thai, ly_do)
                    VALUES (p_ky, d.pn, 'THU_CONG', 'NGUOI_DUNG', ai, 'CHO', 'THU_CONG') RETURNING * INTO v;
                v_moi := true;
                PERFORM master.crm_g5_ghi_su_kien(v.id, 'TAO', 'NGUOI_DUNG', ai, '{}'::jsonb);
            ELSE
                PERFORM master.crm_g5_ghi_su_kien(v.id, 'THAM_GIA', 'NGUOI_DUNG', ai, '{}'::jsonb);
            END IF;
            kq := master.crm_g5_ack(p_ky, p_ctx, v.id) || jsonb_build_object('tao_moi', v_moi);
            """ + _G5_NK_LENH.format(hd="'CRM_G5_CHAY'") + _G_KET.format(a="'CRM_G5_CHAY'") + """
        END $$""",
    # Đối soát: CHỈ việc đang mở (CHUA_RO/CHO_CAU_HINH/DANG_CHAY hết lease → CHO, CÙNG thế hệ/request_id); không có việc → 409, không tạo ý định mới
    """CREATE OR REPLACE FUNCTION master.crm_g5_doi_soat(p_khoa text, p_h text, p_ky uuid, p_ctx text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; cu jsonb; kq jsonb; k record; v record;
        BEGIN""" + _G5_MO_LENH + _G_REPLAY.format(a="'CRM_G5_DOI_SOAT'") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g5|' || p_ky::text, 0));
            IF p_ctx IS NULL OR p_ctx IS DISTINCT FROM master.crm_g5_ngu_canh(p_ky) THEN
                RAISE EXCEPTION 'CRM_G5_NGU_CANH_CU: trạng thái đối chiếu đã đổi — tải lại rồi thao tác' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND trang_thai IN """ + _G5_MO_SQL + """ ORDER BY thu_tu DESC LIMIT 1 FOR UPDATE;
            IF v.id IS NULL THEN
                RAISE EXCEPTION 'CRM_G5_CHUA_CO_VIEC: chưa có việc đối chiếu đang mở — dùng Chạy đối chiếu' USING ERRCODE = 'P0001';
            END IF;
            IF v.trang_thai IN ('CHUA_RO','CHO_CAU_HINH') OR (v.trang_thai = 'DANG_CHAY' AND v.lease_den <= now()) THEN
                UPDATE master.crm_g5_viec SET trang_thai = 'CHO', lease_boi = NULL, lease_den = NULL, thu_lai_sau = now(), cap_nhat_luc = now()
                    WHERE id = v.id RETURNING * INTO v;
            END IF;
            PERFORM master.crm_g5_ghi_su_kien(v.id, 'DOI_SOAT', 'NGUOI_DUNG', ai, jsonb_build_object('trang_thai', v.trang_thai));
            kq := master.crm_g5_ack(p_ky, p_ctx, v.id) || jsonb_build_object('tao_moi', false);
            """ + _G5_NK_LENH.format(hd="'CRM_G5_DOI_SOAT'") + _G_KET.format(a="'CRM_G5_DOI_SOAT'") + """
        END $$""",
    # ======================================================================= worker (chủ bảng; lệnh NGẮN; engine NGOÀI giao dịch)
    # việc đến hạn + người chạy: BAT_BUOC → cấu hình máy chủ hiện hành (thiếu → CHO_CAU_HINH, giữ việc); THU_CONG → chính người khởi tạo
    """CREATE OR REPLACE FUNCTION master.crm_g5_hang_doi(p_toi_da integer) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v record; nc record; kq jsonb := '[]'::jsonb;
        BEGIN""" + _G_CHU + """
            FOR v IN SELECT * FROM master.crm_g5_viec
                     WHERE (trang_thai IN ('CHO','CHUA_RO','CHO_CAU_HINH') AND thu_lai_sau <= now()) OR (trang_thai = 'DANG_CHAY' AND lease_den <= now())
                     ORDER BY thu_lai_sau, thu_tu LIMIT greatest(least(coalesce(p_toi_da, 1), 50), 1) FOR UPDATE SKIP LOCKED LOOP
                IF v.loai = 'BAT_BUOC' THEN
                    SELECT * INTO nc FROM master.crm_g5_nguoi_chay_hien_hanh(v.phap_nhan_id);
                    IF nc.dang_nhap IS NULL THEN
                        IF v.trang_thai <> 'CHO_CAU_HINH' OR v.ly_do IS DISTINCT FROM 'THIEU_NGUOI_CHAY' THEN
                            PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', 'SYSTEM_JOB', 'hang_doi', jsonb_build_object('ly_do', 'THIEU_NGUOI_CHAY'));
                        END IF;
                        UPDATE master.crm_g5_viec SET trang_thai = 'CHO_CAU_HINH', ly_do = 'THIEU_NGUOI_CHAY', lease_boi = NULL, lease_den = NULL,
                                                      thu_lai_sau = now() + interval '15 minutes', cap_nhat_luc = now() WHERE id = v.id;
                        CONTINUE;
                    END IF;
                    kq := kq || jsonb_build_array(jsonb_build_object('viec_id', v.id, 'ky_id', v.ky_id, 'loai', v.loai, 'nguoi_chay', nc.dang_nhap,
                                                                     'tac_nhan_loai', 'SYSTEM_JOB'));
                ELSE
                    kq := kq || jsonb_build_array(jsonb_build_object('viec_id', v.id, 'ky_id', v.ky_id, 'loai', v.loai, 'nguoi_chay', v.khoi_tao_boi,
                                                                     'tac_nhan_loai', 'NGUOI_DUNG'));
                END IF;
            END LOOP;
            RETURN kq;
        END $$""",
    # nhận việc dưới danh tính người chạy (GUC giao dịch): quyền + phạm vi HIỆN HÀNH trước mọi đọc; thiếu → CHO_CAU_HINH có lý do (giữ việc)
    """CREATE OR REPLACE FUNCTION master.crm_g5_nhan(p_viec uuid, p_lease_boi text, p_lease_giay integer) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v record; k record; r record; dk record; nc record; y record; x record; v_loi text; v_tn text;
                v_y_xong boolean := false;
        BEGIN""" + _G_CHU + """
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = p_viec FOR UPDATE;
            IF v.id IS NULL THEN
                RAISE EXCEPTION 'CRM_G5_CHUA_CO_VIEC: không có việc đối chiếu' USING ERRCODE = 'P0001';
            END IF;
            IF NOT ((v.trang_thai IN ('CHO','CHUA_RO','CHO_CAU_HINH') AND v.thu_lai_sau <= now()) OR (v.trang_thai = 'DANG_CHAY' AND v.lease_den <= now())) THEN
                RETURN jsonb_build_object('nhan', false, 'ly_do', 'KHONG_DEN_HAN', 'trang_thai', v.trang_thai);
            END IF;
            v_tn := CASE v.loai WHEN 'BAT_BUOC' THEN 'SYSTEM_JOB' ELSE 'NGUOI_DUNG' END;
            IF v.loai = 'BAT_BUOC' THEN
                SELECT * INTO nc FROM master.crm_g5_nguoi_chay_hien_hanh(v.phap_nhan_id);
                IF nc.dang_nhap IS NULL OR ai IS DISTINCT FROM nc.dang_nhap THEN
                    v_loi := 'THIEU_NGUOI_CHAY';
                END IF;
            ELSIF ai IS DISTINCT FROM v.khoi_tao_boi THEN
                v_loi := 'NGUOI_CHAY_KHAC';
            END IF;
            IF v_loi IS NULL THEN
                BEGIN
                    PERFORM master.crm_g_ghim_quyen(v.phap_nhan_id);
                    PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = v.ky_id AND b.thu_hoi_luc IS NULL FOR SHARE;
                    PERFORM master.crm_kiem_dich(v.ky_id, true);
                EXCEPTION WHEN raise_exception THEN
                    v_loi := left(split_part(SQLERRM, ':', 1), 80);
                    IF v_loi !~ '^[A-Z0-9_]{1,80}$' THEN v_loi := 'QUYEN_KHONG_DAT'; END IF;
                END;
            END IF;
            IF v_loi IS NULL THEN
                SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(v.ky_id);
                IF dk.id IS NULL THEN
                    v_loi := 'THIEU_DANG_KY';
                END IF;
            END IF;
            IF v_loi IS NOT NULL THEN
                IF v.trang_thai <> 'CHO_CAU_HINH' OR v.ly_do IS DISTINCT FROM v_loi THEN
                    PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', v_tn, coalesce(ai, 'khong_danh_tinh'), jsonb_build_object('ly_do', v_loi));
                END IF;
                -- việc DANG_CHAY hết lease giữ nguyên thế hệ/request_id (remote có thể đã nhận) — chỉ chờ cấu hình
                UPDATE master.crm_g5_viec SET trang_thai = 'CHO_CAU_HINH', ly_do = v_loi, lease_boi = NULL, lease_den = NULL,
                                              thu_lai_sau = now() + interval '15 minutes', cap_nhat_luc = now() WHERE id = v.id;
                RETURN jsonb_build_object('nhan', false, 'ly_do', v_loi, 'trang_thai', 'CHO_CAU_HINH');
            END IF;
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = v.ky_id;
            SELECT * INTO y FROM master.crm_g5_y_dinh WHERE viec_id = v.id AND the_he = v.the_he;
            -- ý định của thế hệ này đã có kết quả công bố (chỉ có thể là CHUA_DOI_CHIEU_DUOC với việc bắt buộc còn mở) → không POST lại cùng request_id
            v_y_xong := y.id IS NOT NULL AND EXISTS (SELECT 1 FROM master.crm_g5_ket_qua q WHERE q.y_dinh_id = y.id);
            -- việc bắt buộc: kết quả MỚI NHẤT của đăng ký hiện hành là kết quả HOÀN TẤT (KHOP/LECH — đã qua validator coverage) → đóng XONG,
            -- không gọi engine lần nữa. CHUA_DOI_CHIEU_DUOC không bao giờ hoàn tất nghĩa vụ (FIX01-D)
            IF v.loai = 'BAT_BUOC' AND (y.id IS NULL OR v_y_xong) THEN
                SELECT * INTO x FROM master.crm_g5_ket_qua WHERE ky_id = v.ky_id AND dang_ky_id = dk.id ORDER BY thu_tu DESC LIMIT 1;
                IF x.id IS NOT NULL AND x.trang_thai IN ('KHOP','LECH') THEN
                    UPDATE master.crm_g5_viec SET trang_thai = 'XONG', ly_do = 'DA_CO_KET_QUA_HIEN_HANH', ket_qua_id = x.id, lease_boi = NULL, lease_den = NULL,
                                                  cap_nhat_luc = now() WHERE id = v.id;
                    PERFORM master.crm_g5_ghi_su_kien(v.id, 'XONG', 'SYSTEM_JOB', ai, jsonb_build_object('ket_qua_id', x.id, 'ly_do', 'DA_CO_KET_QUA_HIEN_HANH'));
                    RETURN jsonb_build_object('nhan', false, 'ly_do', 'DA_CO_KET_QUA_HIEN_HANH', 'trang_thai', 'XONG');
                END IF;
            END IF;
            -- cùng đăng ký + ý định thế hệ này đã có kết quả CHUA: chờ có căn cứ (đăng ký/implementation/catalog mới → thế hệ mới; hoặc kết quả
            -- hoàn tất từ lượt thủ công có kiểm soát → shortcut ở trên). Không tạo ý định/request/engine call mới; nghĩa vụ vẫn mở
            IF v_y_xong AND y.dang_ky_id = dk.id THEN
                IF v.trang_thai <> 'CHO_CAU_HINH' OR v.ly_do IS DISTINCT FROM 'G5_CHUA_DOI_CHIEU_DUOC' THEN
                    PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', v_tn, ai, jsonb_build_object('ly_do', 'G5_CHUA_DOI_CHIEU_DUOC', 'the_he', v.the_he));
                END IF;
                UPDATE master.crm_g5_viec SET trang_thai = 'CHO_CAU_HINH', ly_do = 'G5_CHUA_DOI_CHIEU_DUOC', lease_boi = NULL, lease_den = NULL,
                                              thu_lai_sau = now() + interval '15 minutes', cap_nhat_luc = now() WHERE id = v.id;
                RETURN jsonb_build_object('nhan', false, 'ly_do', 'G5_CHUA_DOI_CHIEU_DUOC', 'trang_thai', 'CHO_CAU_HINH');
            END IF;
            IF y.id IS NOT NULL AND y.dang_ky_id <> dk.id THEN  -- đăng ký đổi: ý định cũ không dùng lại khóa; thế hệ mới, request_id mới
                UPDATE master.crm_g5_viec SET the_he = the_he + 1, cap_nhat_luc = now() WHERE id = v.id RETURNING * INTO v;
                PERFORM master.crm_g5_ghi_su_kien(v.id, 'THE_HE_MOI', v_tn, ai, jsonb_build_object('the_he', v.the_he, 'dang_ky_cu', y.dang_ky_id));
                SELECT * INTO y FROM master.crm_g5_y_dinh WHERE viec_id = v.id AND the_he = v.the_he;  -- thế hệ mới: chưa có ý định
            END IF;
            UPDATE master.crm_g5_viec SET trang_thai = 'DANG_CHAY', ly_do = NULL, lease_boi = p_lease_boi,
                                          lease_den = now() + make_interval(secs => greatest(least(coalesce(p_lease_giay, 600), 7200), 60)),
                                          so_lan = so_lan + 1, cap_nhat_luc = now() WHERE id = v.id RETURNING * INTO v;
            PERFORM master.crm_g5_ghi_su_kien(v.id, 'NHAN', v_tn, ai, jsonb_build_object('the_he', v.the_he, 'so_lan', v.so_lan, 'lease_boi', p_lease_boi));
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE id = k.soan_rev_id;
            RETURN jsonb_build_object(
                'nhan', true, 'viec_id', v.id, 'loai', v.loai, 'the_he', v.the_he, 'request_id', master.crm_g5_request_id(v.id, v.the_he),
                'tac_nhan_loai', v_tn, 'tac_nhan', ai,
                'ky', """ + _LINEAGE + """ || jsonb_build_object('ky_pdf_sha256', k.ky_pdf_sha256, 'ky_pdf_len', k.ky_pdf_len, 'ten_tep', k.ten_tep),
                'du_lieu', r.du_lieu,
                'danh_muc', (SELECT coalesce(jsonb_agg(jsonb_build_object('khoa', t.khoa, 'kieu', t.kieu, 'nhan', t.nhan, 'pii', t.pii, 'dinh_dang', t.dinh_dang)
                                                      ORDER BY t.khoa), '[]'::jsonb)
                             FROM master.crm_danh_muc_truong t JOIN master.crm_hd_soan s ON s.id = k.soan_id
                             WHERE t.loai_hinh_id = s.loai_hinh_id AND t.danh_muc_ref = k.danh_muc_ref AND t.revision = k.danh_muc_rev),
                'dang_ky', jsonb_build_object('id', dk.id, 'nhan', dk.nhan, 'loai_hop_dong', dk.loai_hop_dong, 'catalog_id', dk.catalog_id,
                                              'catalog_sha256', dk.catalog_sha256, 'implementation_sha256', dk.implementation_sha256,
                                              'capability', dk.capability, 'mapping', dk.mapping),
                'y_dinh', CASE WHEN y.id IS NULL THEN NULL ELSE jsonb_build_object('id', y.id, 'expected_sha256', y.expected_sha256,
                                                                                    'binding_sha256', y.binding_sha256, 'body_sha256', y.body_sha256) END);
        END $$""",
    # ghi ý định bất biến TRƯỚC khi gọi engine (cùng thế hệ: cùng SHA → dùng lại; khác → 409, không ghi đè)
    """CREATE OR REPLACE FUNCTION master.crm_g5_ghi_y_dinh(p_viec uuid, p_the_he integer, p_lease_boi text, p_expected jsonb, p_expected_sha text,
                                                         p_binding jsonb, p_binding_sha text, p_body jsonb, p_body_sha text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v record; y record; dk record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = p_viec FOR UPDATE;
            IF v.id IS NULL OR v.trang_thai <> 'DANG_CHAY' OR v.lease_boi IS DISTINCT FROM p_lease_boi OR v.lease_den IS NULL OR v.lease_den <= now()
               OR v.the_he <> p_the_he THEN
                RAISE EXCEPTION 'CRM_G5_LEASE_MAT: việc không còn do worker này giữ' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO y FROM master.crm_g5_y_dinh WHERE viec_id = v.id AND the_he = v.the_he;
            IF y.id IS NOT NULL THEN
                IF ROW(y.expected_sha256, y.binding_sha256, y.body_sha256) IS DISTINCT FROM ROW(p_expected_sha, p_binding_sha, p_body_sha) THEN
                    RAISE EXCEPTION 'CRM_G5_Y_DINH_KHAC: ý định đã ghi cho thế hệ này khác yêu cầu dựng lại — không dùng lại khóa' USING ERRCODE = 'P0001';
                END IF;
                RETURN jsonb_build_object('y_dinh_id', y.id, 'request_id', y.request_id, 'lap_lai', true);
            END IF;
            SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(v.ky_id);
            INSERT INTO master.crm_g5_y_dinh (viec_id, the_he, ky_id, dang_ky_id, request_id, ky_pdf_sha256, g3_pdf_sha256, expected, expected_sha256,
                                              binding, binding_sha256, body, body_sha256, tac_nhan_loai, tac_nhan)
                SELECT v.id, v.the_he, v.ky_id, dk.id, master.crm_g5_request_id(v.id, v.the_he), k.ky_pdf_sha256, k.g3_pdf_sha256, p_expected, p_expected_sha,
                       p_binding, p_binding_sha, p_body, p_body_sha, CASE v.loai WHEN 'BAT_BUOC' THEN 'SYSTEM_JOB' ELSE 'NGUOI_DUNG' END, coalesce(ai, 'khong_danh_tinh')
                FROM master.crm_hd_ky k WHERE k.id = v.ky_id
                RETURNING * INTO y;
            PERFORM master.crm_g5_ghi_su_kien(v.id, 'Y_DINH', CASE v.loai WHEN 'BAT_BUOC' THEN 'SYSTEM_JOB' ELSE 'NGUOI_DUNG' END, ai,
                                              jsonb_build_object('request_id', y.request_id, 'body_sha256', y.body_sha256));
            RETURN jsonb_build_object('y_dinh_id', y.id, 'request_id', y.request_id, 'lap_lai', false);
        END $$""",
    # công bố kết quả: lease + quyền/phạm vi/người chạy/đăng ký HIỆN HÀNH kiểm lại trong CHÍNH giao dịch ghi; không duyệt/kích hoạt/ghi sổ
    """CREATE OR REPLACE FUNCTION master.crm_g5_cong_bo(p_viec uuid, p_the_he integer, p_lease_boi text, p_trang_thai text, p_coverage jsonb, p_lech jsonb,
                                                      p_thieu jsonb, p_g5 jsonb, p_raw_sha text, p_raw_len bigint, p_luot text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v record; y record; dk record; nc record; x record; v_tn text;
        BEGIN""" + _G_CHU + """
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = p_viec FOR UPDATE;
            IF v.id IS NULL OR v.trang_thai <> 'DANG_CHAY' OR v.lease_boi IS DISTINCT FROM p_lease_boi OR v.lease_den IS NULL OR v.lease_den <= now()
               OR v.the_he <> p_the_he THEN
                RAISE EXCEPTION 'CRM_G5_LEASE_MAT: việc không còn do worker này giữ — không công bố' USING ERRCODE = 'P0001';
            END IF;
            v_tn := CASE v.loai WHEN 'BAT_BUOC' THEN 'SYSTEM_JOB' ELSE 'NGUOI_DUNG' END;
            IF v.loai = 'BAT_BUOC' THEN
                SELECT * INTO nc FROM master.crm_g5_nguoi_chay_hien_hanh(v.phap_nhan_id);
                IF nc.dang_nhap IS NULL OR ai IS DISTINCT FROM nc.dang_nhap THEN
                    RAISE EXCEPTION 'CRM_G5_NGUOI_CHAY_DOI: cấu hình người chạy đã đổi/thu hồi trước công bố' USING ERRCODE = 'P0001';
                END IF;
            ELSIF ai IS DISTINCT FROM v.khoi_tao_boi THEN
                RAISE EXCEPTION 'CRM_G5_NGUOI_CHAY_DOI: danh tính công bố khác người khởi tạo' USING ERRCODE = 'P0001';
            END IF;
            PERFORM master.crm_g_ghim_quyen(v.phap_nhan_id);
            PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = v.ky_id AND b.thu_hoi_luc IS NULL FOR SHARE;
            PERFORM master.crm_kiem_dich(v.ky_id, true);
            SELECT * INTO y FROM master.crm_g5_y_dinh WHERE viec_id = v.id AND the_he = v.the_he;
            SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(v.ky_id);
            IF y.id IS NULL OR dk.id IS DISTINCT FROM y.dang_ky_id THEN
                RAISE EXCEPTION 'CRM_G5_DANG_KY_DOI: đăng ký engine/catalog đã đổi/thu hồi trước công bố' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_g5_ket_qua (ky_id, phap_nhan_id, viec_id, y_dinh_id, dang_ky_id, request_id, trang_thai, coverage, lech, thieu, g5,
                                               raw_sha256, raw_len, luot, body_sha256, expected_sha256, binding_sha256, implementation_sha256,
                                               ky_pdf_sha256, g3_pdf_sha256, tac_nhan_loai, tac_nhan)
                VALUES (v.ky_id, v.phap_nhan_id, v.id, y.id, dk.id, y.request_id, p_trang_thai, p_coverage, p_lech, p_thieu, p_g5,
                        p_raw_sha, p_raw_len, p_luot, y.body_sha256, y.expected_sha256, y.binding_sha256, dk.implementation_sha256,
                        y.ky_pdf_sha256, y.g3_pdf_sha256, v_tn, ai)
                RETURNING * INTO x;
            PERFORM master.crm_g5_ghi_su_kien(v.id, 'KET_QUA', v_tn, ai, jsonb_build_object('ket_qua_id', x.id, 'trang_thai', x.trang_thai,
                                                                                         'raw_sha256', x.raw_sha256));
            -- CHUA_DOI_CHIEU_DUOC: kết quả/raw/ID vẫn công bố (lịch sử bất biến) nhưng nghĩa vụ BAT_BUOC KHÔNG đóng — chờ có lý do;
            -- crm_g5_nhan không POST lại cùng ý định/request_id (chỉ đăng ký mới hoặc kết quả hoàn tất mới đóng được). Việc thủ công đóng XONG.
            IF x.trang_thai = 'CHUA_DOI_CHIEU_DUOC' AND v.loai = 'BAT_BUOC' THEN
                UPDATE master.crm_g5_viec SET trang_thai = 'CHO_CAU_HINH', ly_do = 'G5_CHUA_DOI_CHIEU_DUOC', ket_qua_id = NULL, lease_boi = NULL,
                                              lease_den = NULL, thu_lai_sau = now() + interval '15 minutes', cap_nhat_luc = now()
                    WHERE id = v.id;
                PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', v_tn, ai, jsonb_build_object('ly_do', 'G5_CHUA_DOI_CHIEU_DUOC', 'ket_qua_id', x.id,
                                                                                                  'the_he', v.the_he));
                RETURN jsonb_build_object('ket_qua_id', x.id, 'trang_thai', x.trang_thai, 'viec_trang_thai', 'CHO_CAU_HINH');
            END IF;
            UPDATE master.crm_g5_viec SET trang_thai = 'XONG', ly_do = NULL, ket_qua_id = x.id, lease_boi = NULL, lease_den = NULL, cap_nhat_luc = now()
                WHERE id = v.id;
            RETURN jsonb_build_object('ket_qua_id', x.id, 'trang_thai', x.trang_thai, 'viec_trang_thai', 'XONG');
        END $$""",
    # kết thúc không có kết quả: CHUA_RO (giữ thế hệ/request_id) | CHO_CAU_HINH (lý do) | LOI (chỉ việc thủ công; bắt buộc → CHO_CAU_HINH) | CHO
    """CREATE OR REPLACE FUNCTION master.crm_g5_ket_thuc(p_viec uuid, p_the_he integer, p_lease_boi text, p_trang_thai text, p_ly_do text, p_cho_giay integer)
        RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v record; v_tt text := p_trang_thai; v_ly text := left(coalesce(p_ly_do, 'KHONG_RO'), 80);
        BEGIN""" + _G_CHU + """
            SELECT * INTO v FROM master.crm_g5_viec WHERE id = p_viec FOR UPDATE;
            -- lease thật: đúng chủ/thế hệ/trạng thái VÀ lease_den > now(); NULL hoặc đã hết hạn → không áp dụng, không lịch sử (kể cả chưa ai claim lại)
            IF v.id IS NULL OR v.trang_thai <> 'DANG_CHAY' OR v.lease_boi IS DISTINCT FROM p_lease_boi OR v.lease_den IS NULL OR v.lease_den <= now()
               OR v.the_he <> p_the_he THEN
                RETURN jsonb_build_object('ap_dung', false);  -- lease đã mất/hết hạn: worker khác/đối soát có thể giữ; không ghi đè
            END IF;
            IF v_tt NOT IN ('CHO','CHUA_RO','CHO_CAU_HINH','LOI') THEN
                RAISE EXCEPTION 'CRM_G5_VIEC_SAI: trạng thái kết thúc không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF v_ly !~ '^[A-Z0-9_]{1,80}$' THEN v_ly := 'KHONG_RO'; END IF;
            IF v_tt = 'LOI' AND v.loai = 'BAT_BUOC' THEN v_tt := 'CHO_CAU_HINH'; END IF;  -- nghĩa vụ bắt buộc không bị quên
            UPDATE master.crm_g5_viec SET trang_thai = v_tt, ly_do = v_ly, lease_boi = NULL, lease_den = NULL,
                                          thu_lai_sau = now() + make_interval(secs => greatest(least(coalesce(p_cho_giay, 120), 86400), 0)),
                                          cap_nhat_luc = now() WHERE id = v.id;
            PERFORM master.crm_g5_ghi_su_kien(v.id, v_tt, CASE v.loai WHEN 'BAT_BUOC' THEN 'SYSTEM_JOB' ELSE 'NGUOI_DUNG' END,
                                              coalesce(master.ktt_danh_tinh(), 'worker'), jsonb_build_object('ly_do', v_ly, 'the_he', v.the_he));
            RETURN jsonb_build_object('ap_dung', true, 'trang_thai', v_tt);
        END $$""",
    # ======================================================================= đọc CRM_G5_VIEW_V1 (quyền HIỆN HÀNH trước tra cứu; PII che; nhật ký truy cập)
    """CREATE OR REPLACE FUNCTION master.crm_g5_doc(p_ky uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; k record; g record; dk record; nc record; v record; x record; y record; v_chay boolean := true;
                v_ly jsonb := '[]'::jsonb; v_job jsonb; v_kq jsonb; v_ts jsonb; v_ctx text; v_pii text[];
        BEGIN""" + _G_CHU + """
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NOT NULL THEN
                PERFORM master.crm_g_ghim_quyen(k.phap_nhan_id);
                PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = k.id AND b.thu_hoi_luc IS NULL FOR SHARE;
            END IF;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, false);
            BEGIN
                PERFORM master.crm_kiem_dich(p_ky, true);
            EXCEPTION WHEN raise_exception THEN
                v_chay := false;
            END;
            SELECT * INTO g FROM master.crm_hd_ky_g5 WHERE ky_id = k.id;
            SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(p_ky);
            SELECT * INTO nc FROM master.crm_g5_nguoi_chay_hien_hanh(k.phap_nhan_id);
            IF dk.id IS NULL THEN v_ly := v_ly || jsonb_build_array('THIEU_DANG_KY'); END IF;
            IF dk.id IS NOT NULL AND dk.nhan <> 'VAN_HANH' THEN v_ly := v_ly || jsonb_build_array('DANG_KY_DEMO'); END IF;
            IF k.co_sua AND nc.dang_nhap IS NULL THEN v_ly := v_ly || jsonb_build_array('THIEU_NGUOI_CHAY'); END IF;
            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND trang_thai IN """ + _G5_MO_SQL + """ ORDER BY thu_tu DESC LIMIT 1;
            IF v.id IS NOT NULL THEN
                v_job := jsonb_build_object('job_id', v.id, 'loai', v.loai, 'trang_thai', v.trang_thai, 'ly_do', v.ly_do,
                                            'request_id', master.crm_g5_request_id(v.id, v.the_he), 'the_he', v.the_he, 'so_lan', v.so_lan,
                                            'khoi_tao_loai', v.khoi_tao_loai, 'cap_nhat_luc', v.cap_nhat_luc);
            END IF;
            SELECT * INTO x FROM master.crm_g5_ket_qua WHERE ky_id = p_ky ORDER BY thu_tu DESC LIMIT 1;
            IF x.id IS NOT NULL THEN
                SELECT * INTO y FROM master.crm_g5_y_dinh WHERE id = x.y_dinh_id;
                -- che PII theo mapping ĐÃ GHIM trong ý định của kết quả (không phụ thuộc đăng ký hiện hành còn hay đã thu hồi)
                SELECT array_agg(m ->> 'ma') INTO v_pii FROM jsonb_array_elements(y.binding -> 'mapping') m
                    JOIN master.crm_hd_soan s ON s.id = k.soan_id
                    JOIN master.crm_danh_muc_truong t ON t.khoa = m ->> 'crm_truong' AND t.loai_hinh_id = s.loai_hinh_id AND t.danh_muc_ref = k.danh_muc_ref
                         AND t.revision = k.danh_muc_rev AND t.pii;
                SELECT coalesce(jsonb_agg(jsonb_build_object(
                           'ma', t.e ->> 'ma',
                           'crm_truong', (SELECT m ->> 'crm_truong' FROM jsonb_array_elements(y.binding -> 'mapping') m WHERE m ->> 'ma' = t.e ->> 'ma'),
                           'muc', (SELECT (m ->> 'muc')::integer FROM jsonb_array_elements(y.binding -> 'mapping') m WHERE m ->> 'ma' = t.e ->> 'ma'),
                           'kieu', t.e ->> 'kieu',
                           'gia_tri_ky_vong', CASE WHEN (t.e ->> 'ma') = ANY (coalesce(v_pii, ARRAY[]::text[]))
                                                   THEN to_jsonb(master.crm_kiem_che(t.e -> 'gia_tri' #>> '{}')) ELSE t.e -> 'gia_tri' END,
                           'gia_tri_ban_ky', CASE WHEN l.e IS NULL THEN NULL WHEN (t.e ->> 'ma') = ANY (coalesce(v_pii, ARRAY[]::text[]))
                                                  THEN to_jsonb(master.crm_kiem_che(l.e -> 'gia_tri_ban_ky' #>> '{}')) ELSE l.e -> 'gia_tri_ban_ky' END,
                           'trich_dan', CASE WHEN l.e IS NULL THEN NULL WHEN (t.e ->> 'ma') = ANY (coalesce(v_pii, ARRAY[]::text[]))
                                             THEN master.crm_kiem_che(l.e ->> 'trich_dan') ELSE l.e ->> 'trich_dan' END,
                           'vi_tri_do_duoc', CASE WHEN l.e IS NULL THEN NULL ELSE l.e -> 'vi_tri_do_duoc' END,
                           'trang_thai', CASE WHEN l.e IS NOT NULL THEN 'LECH' WHEN x.thieu @> to_jsonb(t.e ->> 'ma') THEN 'THIEU'
                                              WHEN x.coverage @> to_jsonb(t.e ->> 'ma') THEN 'KHOP' ELSE 'CHUA_PHU' END) ORDER BY t.o), '[]'::jsonb)
                    INTO v_ts
                    FROM jsonb_array_elements(y.expected -> 'tham_so') WITH ORDINALITY AS t(e, o)
                    LEFT JOIN LATERAL (SELECT z AS e FROM jsonb_array_elements(x.lech) z WHERE z ->> 'ma' = t.e ->> 'ma') l ON true;
                v_kq := jsonb_build_object('result_id', x.id, 'trang_thai', x.trang_thai, 'hien_hanh', x.dang_ky_id IS NOT DISTINCT FROM dk.id,
                                           'nhan_dang_ky', (SELECT z.nhan FROM master.crm_g5_dang_ky z WHERE z.id = x.dang_ky_id),
                                           'tac_nhan_loai', x.tac_nhan_loai, 'so_phu', jsonb_array_length(x.coverage), 'so_ma', jsonb_array_length(y.expected -> 'tham_so'),
                                           'so_lech', jsonb_array_length(x.lech), 'so_thieu', jsonb_array_length(x.thieu), 'tham_so', v_ts, 'tao_luc', x.tao_luc);
            END IF;
            v_ctx := master.crm_g5_ngu_canh(p_ky);
            """ + _G_NK.format(pn="k.phap_nhan_id", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="'CRM_G5_XEM'",
                               sau="jsonb_build_object('muc_dich', 'XEM_DOI_CHIEU', 'ket_qua_id', x.id)", ly="NULL") + """
            RETURN jsonb_build_object(
                'kieu', 'CRM_G5_VIEW_V1', 'ky_id', k.id, 'context_sha256', v_ctx, 'bat_buoc', k.co_sua,
                'khoi_tao', jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false),
                'quyen', jsonb_build_object('chay', v_chay, 'doi_soat', v_chay AND v.id IS NOT NULL),
                'readiness', jsonb_build_object('san_sang', jsonb_array_length(v_ly) = 0, 'ly_do', v_ly),
                'current_job', v_job, 'current_result', v_kq,
                'history', (SELECT coalesce(jsonb_agg(jsonb_build_object('result_id', z.id, 'trang_thai', z.trang_thai, 'tac_nhan_loai', z.tac_nhan_loai,
                                                                          'hien_hanh', z.dang_ky_id IS NOT DISTINCT FROM dk.id, 'so_lech', jsonb_array_length(z.lech),
                                                                          'so_thieu', jsonb_array_length(z.thieu), 'tao_luc', z.tao_luc) ORDER BY z.thu_tu DESC), '[]'::jsonb)
                            FROM (SELECT * FROM master.crm_g5_ket_qua q WHERE q.ky_id = p_ky AND q.id IS DISTINCT FROM x.id ORDER BY q.thu_tu DESC LIMIT 50) z),
                'g6', master.crm_kiem_g5_xet(p_ky, 'VAN_HANH'));
        END $$""",
    # ======================================================================= G6: thay HẸP resolver G5 (VAN_HANH đọc bằng chứng thật; SYNTHETIC nguyên văn)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_g5_xet(p_ky uuid, p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE g record; q record; v_kt jsonb; k record; dk record; x record; v_ma text;
        BEGIN
            SELECT * INTO g FROM master.crm_hd_ky_g5 WHERE ky_id = p_ky;
            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);
            IF p_che_do IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN
                -- VAN_HANH: kết quả mới nhất của ĐĂNG KÝ HIỆN HÀNH (nhãn VAN_HANH) trên đúng PDF bản ký; PENDING/NOT_SELECTED không là bằng chứng
                SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
                SELECT * INTO dk FROM master.crm_g5_dang_ky_hien_hanh(p_ky);
                IF dk.id IS NULL THEN
                    RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', 'HOLD', 'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                              'chan', jsonb_build_array(jsonb_build_object('ma', 'UNREGISTERED_G5_PROOF')));
                END IF;
                SELECT * INTO x FROM master.crm_g5_ket_qua WHERE ky_id = p_ky AND dang_ky_id = dk.id AND ky_pdf_sha256 = k.ky_pdf_sha256
                    ORDER BY thu_tu DESC LIMIT 1;
                IF x.id IS NULL THEN
                    v_ma := CASE WHEN EXISTS (SELECT 1 FROM master.crm_g5_ket_qua z WHERE z.ky_id = p_ky) THEN 'G5_KET_QUA_CU'
                                 WHEN k.co_sua THEN 'G5_BAT_BUOC_CHUA_CO_KET_QUA' ELSE 'G5_CHUA_DOI_CHIEU' END;
                    RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', 'HOLD', 'dang_ky_id', dk.id, 'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                              'chan', jsonb_build_array(jsonb_build_object('ma', v_ma)));
                END IF;
                IF dk.nhan <> 'VAN_HANH' THEN
                    RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', 'HOLD', 'dang_ky_id', dk.id, 'ket_qua_id', x.id, 'ket_qua', x.trang_thai,
                                              'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                              'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_DANG_KY_DEMO')));
                END IF;
                IF x.trang_thai = 'CHUA_DOI_CHIEU_DUOC' THEN
                    RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', 'HOLD', 'dang_ky_id', dk.id, 'ket_qua_id', x.id, 'ket_qua', x.trang_thai,
                                              'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                              'lech_mot_phan', (SELECT coalesce(jsonb_agg(jsonb_build_object('ma', t.e ->> 'ma', 'muc', t.e -> 'muc') ORDER BY t.o), '[]'::jsonb)
                                                                FROM jsonb_array_elements(x.lech) WITH ORDINALITY AS t(e, o)),
                                              'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_CHUA_DOI_CHIEU_DUOC')));
                END IF;
                RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', x.trang_thai, 'dang_ky_id', dk.id, 'ket_qua_id', x.id, 'khoi_tao', v_kt,
                                          'chan', '[]'::jsonb,
                                          'lech', CASE WHEN x.trang_thai = 'LECH' THEN (SELECT jsonb_agg(jsonb_build_object('ma', t.e ->> 'ma', 'khoa', t.e ->> 'ma',
                                                                                                                       'muc', t.e -> 'muc') ORDER BY t.o)
                                                                                     FROM jsonb_array_elements(x.lech) WITH ORDINALITY AS t(e, o))
                                                       ELSE '[]'::jsonb END);
            END IF;
            IF current_setting('ktt.crm_kiem_g5', true) IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN
                RETURN jsonb_build_object('che_do', 'SYNTHETIC_FIXTURE', 'trang_thai', 'HOLD', 'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                          'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_SYNTHETIC_KHONG_DUOC_PHEP')));
            END IF;
            SELECT x.* INTO q FROM master.crm_kiem_g5_ket_qua x JOIN master.crm_kiem_g5_nguon n ON n.id = x.nguon_id AND n.phi_van_hanh
                WHERE x.ky_id = p_ky ORDER BY x.thu_tu DESC LIMIT 1;
            IF q.id IS NULL OR q.ket_qua = 'CHUA_HOAN_TAT' THEN
                RETURN jsonb_build_object('che_do', 'SYNTHETIC_FIXTURE', 'nhan', 'SYNTHETIC — không phải bằng chứng vận hành', 'trang_thai', 'HOLD',
                                          'khoi_tao', v_kt, 'lech', '[]'::jsonb, 'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_CHUA_HOAN_TAT')));
            END IF;
            RETURN jsonb_build_object('che_do', 'SYNTHETIC_FIXTURE', 'nhan', 'SYNTHETIC — không phải bằng chứng vận hành', 'trang_thai', q.ket_qua,
                                      'ket_qua_id', q.id, 'khoi_tao', v_kt, 'chan', '[]'::jsonb,
                                      'lech', CASE WHEN q.ket_qua = 'LECH' THEN (SELECT jsonb_agg(jsonb_build_object('ma', t.e ->> 'ma', 'khoa', t.e ->> 'ma') ORDER BY t.o)
                                                                                FROM jsonb_array_elements(q.lech) WITH ORDINALITY AS t(e, o))
                                                   ELSE '[]'::jsonb END);
        END $$""",
    # thay HẸP nhánh G5 của trigger xử lý lệch: chế độ theo giao dịch (GUC fixture chỉ do test đặt) — G7/quyền/hồ sơ/append giữ nguyên văn
    """CREATE OR REPLACE FUNCTION master.crm_kiem_xu_ly_lech_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ho record; g jsonb;
        BEGIN
            PERFORM master.crm_kiem_dich(NEW.ky_id, true);
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            IF ho.id IS NULL OR ho.ky_id <> NEW.ky_id OR ho.trang_thai <> 'DANG_KIEM' OR ho.revision <> NEW.ho_so_revision
               OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chỉ xử lý lệch khi hồ sơ đang kiểm (đúng revision)' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai = 'G7_LECH' THEN
                g := master.crm_kiem_g7(NEW.ky_id);
                IF g ->> 'trang_thai' IS DISTINCT FROM 'LECH' OR g ->> 'bo_chuan_pb_id' IS DISTINCT FROM NEW.muc_tieu_id::text
                   OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(g -> 'lech') e WHERE e ->> 'khoa' = NEW.ma_lech) THEN
                    RAISE EXCEPTION 'CRM_KIEM_LECH_KHONG_CON: lệch G7 không tồn tại ở bộ chuẩn hiệu lực theo ngày ký' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                g := master.crm_kiem_g5_xet(NEW.ky_id, CASE WHEN current_setting('ktt.crm_kiem_g5', true) = 'SYNTHETIC_FIXTURE' THEN 'SYNTHETIC_FIXTURE'
                                                            ELSE 'VAN_HANH' END);
                IF g ->> 'trang_thai' IS DISTINCT FROM 'LECH' OR g ->> 'ket_qua_id' IS DISTINCT FROM NEW.muc_tieu_id::text
                   OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(g -> 'lech') e WHERE e ->> 'khoa' = NEW.ma_lech) THEN
                    RAISE EXCEPTION 'CRM_KIEM_LECH_KHONG_CON: không có kết quả G5 LECH được đăng ký cho mục này' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm mới không cấp PUBLIC
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _G5_BANG_MOI),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON """ + ", ".join(f"master.{t}" for t in _G5_BANG_MOI) + """ FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    "REVOKE ALL ON " + ", ".join(f"master.{t}" for t in _G5_BANG_MOI) + " FROM PUBLIC",
    """DO $$
    DECLARE f regprocedure;
    BEGIN
        FOR f IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname = 'master' AND p.proname LIKE 'crm\\_g5\\_%' LOOP
            EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', f);
        END LOOP;
    END $$""",
)
