"""DA-1 — CRM · Dự án đang bán (QD-20261025-05…09): migration 31. CHỈ hằng SQL, export `CRM_DU_AN_BAN_SQL` (đăng ký ở ha_tang/pg_migrations.py).

Dùng lại, không viết lại:
  - `master.du_an` (danh mục dự án kế toán, khóa (id, phap_nhan_id)): dự án đang bán GẮN vào đây (QD-06), không có danh mục dự án thứ hai.
  - Bộ chuẩn G7 `master.crm_bo_chuan` / `_phien_ban` / `_dong` làm tiến độ thanh toán tiêu chuẩn; `master.crm_g_chuan_doc` là hàm đọc duy nhất.
  - Bất biến `master.crm_g_bat_bien()`, biên nhận idempotent `master.crm_g_bn_tra/bn_ghi`, ghim quyền `master.crm_g_ghim_quyen` (M0018).
  - Loại hình `master.loai_hinh_doanh_thu.cau_hinh` (tiền tệ hợp lệ của profile); mẫu số `_RE_SO` của M0030 (chỉ chữ số ASCII).

Mới:
  - `crm_da_ban` (gốc, một dòng/dự án) + `crm_da_ban_phien_ban` (thông tin bán hàng CÓ PHIÊN BẢN: cờ đang bán, vị trí, mô tả, đơn giá niêm yết +
    tiền tệ, loại hình + thuế mặc định, giai đoạn tiến độ) + `crm_da_ban_phi` (phí tiêu chuẩn theo phiên bản) + `crm_da_ban_lo` / `_lo_ls` (lô/căn,
    đổi = dòng lịch sử) + `crm_bo_chuan_ap_dung` (bằng chứng G7 áp dụng ngay, căn cứ QD-20261025-07).
  - Phiên bản và dòng lịch sử đã tạo bất biến; chỉ được ĐÓNG hiệu lực một lần (`hieu_luc_den`). Sửa = đóng dòng cũ + thêm dòng mới + nhật ký
    `nhat_ky.su_kien`, cùng giao dịch, hiệu lực ngay từ ngày máy chủ (`master.ktt_ngay()`). Sửa nhiều lần trong ngày: dòng cũ cùng ngày đóng
    thành khoảng rỗng [ngày, ngày) — không bao giờ được chọn ở bất kỳ ngày nào.
  - G7 áp dụng ngay (bỏ CFO, QD-07): `crm_g_chuan_ap_dung` tạo phiên bản G7 rồi chuyển HIEU_LUC ngay từ hôm nay, đóng phiên bản đang hiệu lực
    tại hôm nay. Phiên bản G7 đã duyệt cũ GIỮ NGUYÊN nghĩa (trạng thái, ngày hiệu lực, người duyệt); luồng KT lập → CFO duyệt cũ không đổi.
    CHECK `valid_to > valid_from` của `crm_bo_chuan_phien_ban` nới thành `>=` để đóng phiên bản cùng ngày thành khoảng rỗng (luồng CFO cũ luôn
    tạo ngày hiệu lực sau phiên bản trước nên không bao giờ sinh khoảng rỗng). Mọi chỗ đọc "bộ chuẩn hiệu lực" (crm_g_chuan_doc, crm_kiem_g7,
    lệnh lưu báo giá) đọc theo `trang_thai = 'HIEU_LUC'` + khoảng ngày → đọc được phiên bản áp dụng ngay, không cần sửa.
  - Ảnh chụp mặc định `master.crm_da_anh_chup(du_an, ngày)` cho báo giá (DA-3), có `anh_chup_sha256` để so lại trong lệnh lưu.
Quyền: đọc = phiên có module CRM trên pháp nhân; ghi = bán hàng/kế toán/kế toán trưởng có module CRM (hoặc phân công CRM_DU_AN_BAN). Mọi lệnh
ghi là hàm INVOKER chỉ chạy trên kết nối CHỦ BẢNG của máy chủ, kiểm quyền HIỆN HÀNH của phiên (GUC) TRƯỚC tra biên nhận.
"""

from .sql_crm_bg1c import _RE_SO  # literal M0030 '^[0-9]{1,24}(\.[0-9]{1,12})?$' — một nguồn cho số chính xác (Python lấy cùng literal)

CAN_CU_G7 = "QD-20261025-07"
_UUID_RE = "'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'"
_GD_RE = "'^[A-Za-z0-9_.-]{1,80}$'"
_LOI = "USING ERRCODE = 'P0001'"
_CHU = """
            IF NOT master.la_chu_bang('master.crm_da_ban'::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_MAY_CHU: chỉ đường ghi/đọc tin cậy của máy chủ (chủ bảng) được dùng dự án đang bán' """ + _LOI + """;
            END IF;"""
_REPLAY = """
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;"""
_KET = """
            PERFORM master.crm_g_bn_ghi({pn}, {a}, p_khoa, p_h, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);"""
_TT_KHOA = "ARRAY['vi_tri','mo_ta','don_gia_niem_yet','tien_te','loai_hinh_id','co_so_thue','vat_phan_tram','giai_doan_g7']"
_PHI_KHOA = "ARRAY['ten','loai','muc','don_vi_tinh','tien_te','co_so_tinh']"
_LO_KHOA = "ARRAY['ma','dien_tich','trang_thai','ghi_chu','expected_lan']"
_BANG = ("crm_da_ban", "crm_da_ban_phien_ban", "crm_da_ban_phi", "crm_da_ban_lo", "crm_da_ban_lo_ls", "crm_bo_chuan_ap_dung")
_BANG_DS = ", ".join("master." + t for t in _BANG)
_HAM = ("master.crm_da_duoc_doc(uuid)", "master.crm_da_duoc_ghi(uuid)", "master.crm_da_vao(text, uuid, text, text)",
        "master.crm_da_tt_chuan(jsonb)", "master.crm_da_noi_dung_tu(boolean, jsonb, jsonb)", "master.crm_da_noi_dung(uuid)",
        "master.crm_da_kiem(uuid, jsonb, jsonb)", "master.crm_da_ghi_phien_ban(uuid, uuid, integer, date, boolean, jsonb, jsonb, text, text, boolean)",
        "master.crm_da_bat_ban(text, text, uuid, jsonb, jsonb, text)",
        "master.crm_da_cap_nhat(text, text, text, uuid, integer, jsonb, jsonb, text)",
        "master.crm_da_doi_trang_thai(text, text, uuid, integer, boolean, text)", "master.crm_da_lo_ghi(text, text, uuid, jsonb, text)",
        "master.crm_da_anh_chup_pb(uuid, date)", "master.crm_da_anh_chup(uuid, date)",
        "master.crm_g_chuan_ap_dung(text, text, uuid, text, jsonb)")

CRM_DU_AN_BAN_SQL = (
    # ======================================================================= bảng: gốc + phiên bản + phí + lô/căn + lịch sử lô + bằng chứng G7
    """CREATE TABLE master.crm_da_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (du_an_id),
        UNIQUE (id, phap_nhan_id))""",
    "CREATE TRIGGER crm_da_ban_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_ban FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # đóng hiệu lực MỘT lần: mọi cột khác giữ nguyên byte; không xóa; dòng mới phải đang hiệu lực
    """CREATE OR REPLACE FUNCTION master.crm_da_dong_mot_lan() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: % chỉ ghi qua hàm lệnh trên kết nối chủ bảng', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa % (giữ lịch sử)', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.hieu_luc_den IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: dòng mới của % phải đang hiệu lực', TG_TABLE_NAME USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.hieu_luc_den IS NOT NULL OR NEW.hieu_luc_den IS NULL
               OR (to_jsonb(NEW) - 'hieu_luc_den') IS DISTINCT FROM (to_jsonb(OLD) - 'hieu_luc_den') THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: % đã tạo là bất biến — chỉ đóng hiệu lực một lần (sửa = phiên bản/dòng mới)', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE TABLE master.crm_da_ban_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        da_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        hieu_luc_tu date NOT NULL,
        hieu_luc_den date,
        dang_ban boolean NOT NULL,
        vi_tri text CHECK (vi_tri IS NULL OR length(vi_tri) BETWEEN 1 AND 500),
        mo_ta text CHECK (mo_ta IS NULL OR length(mo_ta) BETWEEN 1 AND 4000),
        don_gia_niem_yet text CHECK (don_gia_niem_yet IS NULL OR don_gia_niem_yet ~ """ + _RE_SO + """),
        tien_te text NOT NULL CHECK (tien_te IN ('VND','USD')),
        loai_hinh_id uuid NOT NULL,
        co_so_thue text CHECK (co_so_thue IN ('NET','GROSS')),
        vat_phan_tram text CHECK (vat_phan_tram IS NULL OR CASE WHEN vat_phan_tram ~ """ + _RE_SO + """ THEN vat_phan_tram::numeric <= 100 ELSE false END),
        giai_doan_g7 text CHECK (giai_doan_g7 IS NULL OR giai_doan_g7 ~ """ + _GD_RE + """),
        so_phi integer NOT NULL CHECK (so_phi BETWEEN 0 AND 50),
        noi_dung_sha256 text NOT NULL CHECK (noi_dung_sha256 ~ '^[0-9a-f]{64}$'),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) BETWEEN 1 AND 1000),
        lap_boi text NOT NULL,
        lap_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (da_ban_id, phap_nhan_id) REFERENCES master.crm_da_ban (id, phap_nhan_id),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (da_ban_id, phien_ban),
        UNIQUE (id, phap_nhan_id),
        CHECK (hieu_luc_den IS NULL OR hieu_luc_den >= hieu_luc_tu))""",
    "CREATE UNIQUE INDEX crm_da_ban_phien_ban_mo_uq ON master.crm_da_ban_phien_ban (da_ban_id) WHERE hieu_luc_den IS NULL",
    "CREATE TRIGGER crm_da_ban_phien_ban_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_ban_phien_ban FOR EACH ROW EXECUTE FUNCTION master.crm_da_dong_mot_lan()",
    """CREATE TABLE master.crm_da_ban_phi (
        phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu BETWEEN 1 AND 50),
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 200),
        loai text NOT NULL CHECK (loai IN ('BAO_TRI','SU_DUNG','KHAC')),
        muc text NOT NULL CHECK (muc ~ """ + _RE_SO + """),
        don_vi_tinh text NOT NULL CHECK (don_vi_tinh IN ('M2_THANG','M2_NAM','LAN')),
        tien_te text NOT NULL CHECK (tien_te IN ('VND','USD')),
        co_so_tinh text CHECK (co_so_tinh IS NULL OR length(co_so_tinh) BETWEEN 1 AND 300),
        PRIMARY KEY (phien_ban_id, thu_tu),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.crm_da_ban_phien_ban (id, phap_nhan_id))""",
    "CREATE UNIQUE INDEX crm_da_ban_phi_ten_uq ON master.crm_da_ban_phi (phien_ban_id, lower(ten))",
    "CREATE TRIGGER crm_da_ban_phi_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_ban_phi FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_da_ban_lo (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        da_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        ma text NOT NULL CHECK (length(ma) BETWEEN 1 AND 80 AND ma = btrim(ma) AND ma !~ '[[:cntrl:]{}]'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (da_ban_id, phap_nhan_id) REFERENCES master.crm_da_ban (id, phap_nhan_id),
        UNIQUE (id, phap_nhan_id))""",
    "CREATE UNIQUE INDEX crm_da_ban_lo_ma_uq ON master.crm_da_ban_lo (da_ban_id, upper(ma))",
    "CREATE TRIGGER crm_da_ban_lo_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_ban_lo FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_da_ban_lo_ls (
        lo_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        hieu_luc_tu date NOT NULL,
        hieu_luc_den date,
        dien_tich text NOT NULL CHECK (CASE WHEN dien_tich ~ """ + _RE_SO + """ THEN dien_tich::numeric > 0 ELSE false END),
        trang_thai text NOT NULL CHECK (trang_thai IN ('CON_TRONG','GIU_CHO','DA_BAN','KHONG_BAN')),
        ghi_chu text CHECK (ghi_chu IS NULL OR length(ghi_chu) BETWEEN 1 AND 1000),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (lo_id, lan),
        FOREIGN KEY (lo_id, phap_nhan_id) REFERENCES master.crm_da_ban_lo (id, phap_nhan_id),
        CHECK (hieu_luc_den IS NULL OR hieu_luc_den >= hieu_luc_tu))""",
    "CREATE UNIQUE INDEX crm_da_ban_lo_ls_mo_uq ON master.crm_da_ban_lo_ls (lo_id) WHERE hieu_luc_den IS NULL",
    "CREATE TRIGGER crm_da_ban_lo_ls_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_da_ban_lo_ls FOR EACH ROW EXECUTE FUNCTION master.crm_da_dong_mot_lan()",
    """CREATE TABLE master.crm_bo_chuan_ap_dung (
        phien_ban_id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        da_ban_id uuid NOT NULL,
        can_cu text NOT NULL CHECK (can_cu = '""" + CAN_CU_G7 + """'),
        hieu_luc_tu date NOT NULL,
        dong_phien_ban_truoc uuid,
        ap_dung_boi text NOT NULL,
        ap_dung_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.crm_bo_chuan_phien_ban (id, phap_nhan_id),
        FOREIGN KEY (da_ban_id, phap_nhan_id) REFERENCES master.crm_da_ban (id, phap_nhan_id))""",
    "CREATE TRIGGER crm_bo_chuan_ap_dung_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bo_chuan_ap_dung FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # G7 áp dụng ngay nhiều lần trong ngày: nới đúng MỘT CHECK `valid_to > valid_from` thành `>=` (khoảng rỗng = phiên bản bị thay cùng ngày)
    """DO $$
    DECLARE r record; n integer := 0;
    BEGIN
        FOR r IN SELECT c.conname FROM pg_constraint c WHERE c.conrelid = 'master.crm_bo_chuan_phien_ban'::regclass AND c.contype = 'c'
                   AND pg_get_constraintdef(c.oid) LIKE '%valid_to > valid_from%' LOOP
            EXECUTE format('ALTER TABLE master.crm_bo_chuan_phien_ban DROP CONSTRAINT %I', r.conname);
            n := n + 1;
        END LOOP;
        IF n <> 1 THEN
            RAISE EXCEPTION 'M0031: không thấy đúng một CHECK valid_to > valid_from của crm_bo_chuan_phien_ban (thấy %)', n;
        END IF;
    END $$""",
    """ALTER TABLE master.crm_bo_chuan_phien_ban ADD CONSTRAINT crm_bo_chuan_phien_ban_valid_to_check
        CHECK (valid_to IS NULL OR (valid_from IS NOT NULL AND valid_to >= valid_from))""",
    # ======================================================================= quyền HIỆN HÀNH của phiên (không vai mới, không IAM thứ hai)
    """CREATE OR REPLACE FUNCTION master.crm_da_duoc_doc(p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT p_pn IS NOT NULL AND master.ktt_duoc(p_pn, 'CRM')
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_da_duoc_ghi(p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT p_pn IS NOT NULL AND master.ktt_duoc(p_pn, 'CRM')
               AND (master.ktt_co_vai(p_pn, ARRAY['BAN_HANG','KE_TOAN','KE_TOAN_TRUONG'], NULL)
                    OR master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_DU_AN_BAN', NULL))
        $$""",
    # preflight mọi lệnh ghi: chủ bảng → ghim dòng quyền → đọc được → ghi được → biên nhận (cùng H → FINAL cũ; khác H → CRM_G_IDEMPOTENCY_KHAC)
    """CREATE OR REPLACE FUNCTION master.crm_da_vao(p_hanh text, p_pn uuid, p_khoa text, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN""" + _CHU + """
            PERFORM master.crm_g_ghim_quyen(p_pn);
            IF NOT master.crm_da_duoc_doc(p_pn) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_da_duoc_ghi(p_pn) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: chỉ bán hàng/kế toán có module CRM được sửa dự án đang bán' USING ERRCODE = 'P0001';
            END IF;
            RETURN master.crm_g_bn_tra(p_pn, p_hanh, p_khoa, p_h);
        END $$""",
    # ======================================================================= nội dung chuẩn hóa của một phiên bản (so "không đổi" + sha)
    """CREATE OR REPLACE FUNCTION master.crm_da_tt_chuan(p_tt jsonb) RETURNS jsonb
        LANGUAGE sql IMMUTABLE SET search_path = master, pg_temp AS $$
        SELECT CASE WHEN coalesce(p_tt ->> 'loai_hinh_id', '') ~ """ + _UUID_RE + """
                    THEN p_tt || jsonb_build_object('loai_hinh_id', (p_tt ->> 'loai_hinh_id')::uuid::text) ELSE p_tt END
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_da_noi_dung_tu(p_dang_ban boolean, p_tt jsonb, p_phi jsonb) RETURNS jsonb
        LANGUAGE sql IMMUTABLE SET search_path = master, pg_temp AS $$
        SELECT jsonb_build_object('dang_ban', p_dang_ban,
            'thong_tin', jsonb_build_object('vi_tri', p_tt ->> 'vi_tri', 'mo_ta', p_tt ->> 'mo_ta', 'don_gia_niem_yet', p_tt ->> 'don_gia_niem_yet',
                                            'tien_te', p_tt ->> 'tien_te', 'loai_hinh_id', p_tt ->> 'loai_hinh_id', 'co_so_thue', p_tt ->> 'co_so_thue',
                                            'vat_phan_tram', p_tt ->> 'vat_phan_tram', 'giai_doan_g7', p_tt ->> 'giai_doan_g7'),
            'phi', coalesce((SELECT jsonb_agg(jsonb_build_object('ten', e ->> 'ten', 'loai', e ->> 'loai', 'muc', e ->> 'muc',
                                                                 'don_vi_tinh', e ->> 'don_vi_tinh', 'tien_te', e ->> 'tien_te',
                                                                 'co_so_tinh', e ->> 'co_so_tinh') ORDER BY o)
                             FROM jsonb_array_elements(coalesce(p_phi, '[]'::jsonb)) WITH ORDINALITY AS x(e, o)), '[]'::jsonb))
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_da_noi_dung(p_pb uuid) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT master.crm_da_noi_dung_tu(v.dang_ban,
            jsonb_build_object('vi_tri', v.vi_tri, 'mo_ta', v.mo_ta, 'don_gia_niem_yet', v.don_gia_niem_yet, 'tien_te', v.tien_te,
                               'loai_hinh_id', v.loai_hinh_id::text, 'co_so_thue', v.co_so_thue, 'vat_phan_tram', v.vat_phan_tram,
                               'giai_doan_g7', v.giai_doan_g7),
            (SELECT coalesce(jsonb_agg(jsonb_build_object('ten', f.ten, 'loai', f.loai, 'muc', f.muc, 'don_vi_tinh', f.don_vi_tinh,
                                                          'tien_te', f.tien_te, 'co_so_tinh', f.co_so_tinh) ORDER BY f.thu_tu), '[]'::jsonb)
             FROM master.crm_da_ban_phi f WHERE f.phien_ban_id = v.id))
        FROM master.crm_da_ban_phien_ban v WHERE v.id = p_pb
        $$""",
    # kiểm nội dung (fail-closed, cùng miền với CHECK bảng + bộ kiểm Python): khóa, kiểu chuỗi, loại hình cùng PN + hiện hành, tiền tệ của profile
    """CREATE OR REPLACE FUNCTION master.crm_da_kiem(p_pn uuid, p_tt jsonb, p_phi jsonb) RETURNS void
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE lh record; v_tt text; r record; ds jsonb;
        BEGIN
            IF p_tt IS NULL OR jsonb_typeof(p_tt) <> 'object'
               OR EXISTS (SELECT 1 FROM jsonb_each(p_tt) e WHERE e.key <> ALL (""" + _TT_KHOA + """) OR jsonb_typeof(e.value) NOT IN ('string','null')) THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: thông tin dự án chỉ gồm vị trí, mô tả, đơn giá, tiền tệ, loại hình, thuế, giai đoạn tiến độ (chuỗi)' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p_tt ->> 'loai_hinh_id', '') !~ """ + _UUID_RE + """ THEN
                RAISE EXCEPTION 'CRM_DA_THIEU_LOAI_HINH: cần chọn loại hình của dự án' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO lh FROM master.loai_hinh_doanh_thu l WHERE l.id = (p_tt ->> 'loai_hinh_id')::uuid AND l.phap_nhan_id = p_pn AND l.valid_to IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'CRM_DA_LOAI_HINH_SAI: loại hình không thuộc pháp nhân của dự án hoặc đã có phiên bản mới — chọn loại hình hiện hành' USING ERRCODE = 'P0001';
            END IF;
            ds := CASE WHEN jsonb_typeof(lh.cau_hinh -> 'tien_te_hop_le') = 'array' THEN lh.cau_hinh -> 'tien_te_hop_le' ELSE '["VND","USD"]'::jsonb END;
            v_tt := p_tt ->> 'tien_te';
            IF v_tt IS NULL OR v_tt NOT IN ('VND','USD') OR NOT (ds ? v_tt) THEN
                RAISE EXCEPTION 'CRM_DA_TIEN_TE_SAI: tiền tệ của dự án không hợp lệ với loại hình (nhận %)', ds USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p_tt ->> 'don_gia_niem_yet', '0') !~ """ + _RE_SO + """ OR coalesce(p_tt ->> 'vat_phan_tram', '0') !~ """ + _RE_SO + """ THEN
                RAISE EXCEPTION 'CRM_DA_SO_SAI: đơn giá/thuế phải là số thập phân không âm (chữ số 0–9, dấu chấm thập phân)' USING ERRCODE = 'P0001';
            END IF;
            IF (p_tt ->> 'vat_phan_tram') IS NOT NULL AND (p_tt ->> 'vat_phan_tram')::numeric > 100 THEN
                RAISE EXCEPTION 'CRM_DA_SO_SAI: thuế VAT tối đa 100%%' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p_tt ->> 'giai_doan_g7', 'X') !~ """ + _GD_RE + """ THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: giai đoạn tiến độ chỉ gồm chữ/số/_ . - (1–80)' USING ERRCODE = 'P0001';
            END IF;
            IF p_phi IS NULL OR jsonb_typeof(p_phi) <> 'array' OR jsonb_array_length(p_phi) > 50 THEN
                RAISE EXCEPTION 'CRM_DA_PHI_SAI: danh sách phí tối đa 50 dòng' USING ERRCODE = 'P0001';
            END IF;
            FOR r IN SELECT e, o FROM jsonb_array_elements(p_phi) WITH ORDINALITY AS x(e, o) LOOP
                IF jsonb_typeof(r.e) <> 'object'
                   OR EXISTS (SELECT 1 FROM jsonb_each(r.e) k WHERE k.key <> ALL (""" + _PHI_KHOA + """) OR jsonb_typeof(k.value) NOT IN ('string','null')) THEN
                    RAISE EXCEPTION 'CRM_DA_PHI_SAI: phí dòng % chỉ gồm tên, loại, mức, đơn vị tính, tiền tệ, cơ sở tính (chuỗi)', r.o USING ERRCODE = 'P0001';
                END IF;
                IF coalesce(r.e ->> 'muc', '') !~ """ + _RE_SO + """ THEN
                    RAISE EXCEPTION 'CRM_DA_SO_SAI: mức phí dòng % phải là số thập phân không âm', r.o USING ERRCODE = 'P0001';
                END IF;
                IF (r.e ->> 'tien_te') IS NULL OR NOT (ds ? (r.e ->> 'tien_te')) THEN
                    RAISE EXCEPTION 'CRM_DA_TIEN_TE_SAI: tiền tệ phí dòng % không hợp lệ với loại hình (nhận %)', r.o, ds USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
        END $$""",
    # ghi MỘT phiên bản mới (gọi sau khi đã đóng phiên bản đang hiệu lực); p_kiem = false chỉ khi chép nguyên nội dung đã lưu (ngừng bán)
    """CREATE OR REPLACE FUNCTION master.crm_da_ghi_phien_ban(p_da uuid, p_pn uuid, p_n integer, p_ngay date, p_dang_ban boolean, p_tt jsonb,
                                                           p_phi jsonb, p_ly_do text, p_ai text, p_kiem boolean) RETURNS uuid
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE tt jsonb := master.crm_da_tt_chuan(p_tt); nd jsonb; pb uuid; r record;
        BEGIN
            IF p_kiem THEN
                PERFORM master.crm_da_kiem(p_pn, tt, p_phi);
            END IF;
            nd := master.crm_da_noi_dung_tu(p_dang_ban, tt, p_phi);
            INSERT INTO master.crm_da_ban_phien_ban (da_ban_id, phap_nhan_id, phien_ban, hieu_luc_tu, dang_ban, vi_tri, mo_ta, don_gia_niem_yet, tien_te,
                                                     loai_hinh_id, co_so_thue, vat_phan_tram, giai_doan_g7, so_phi, noi_dung_sha256, ly_do, lap_boi)
                VALUES (p_da, p_pn, p_n, p_ngay, p_dang_ban, tt ->> 'vi_tri', tt ->> 'mo_ta', tt ->> 'don_gia_niem_yet', tt ->> 'tien_te',
                        (tt ->> 'loai_hinh_id')::uuid, tt ->> 'co_so_thue', tt ->> 'vat_phan_tram', tt ->> 'giai_doan_g7', jsonb_array_length(p_phi),
                        encode(sha256(convert_to(nd::text, 'UTF8')), 'hex'), nullif(btrim(p_ly_do), ''), p_ai)
                RETURNING id INTO pb;
            FOR r IN SELECT e, o FROM jsonb_array_elements(p_phi) WITH ORDINALITY AS x(e, o) LOOP
                INSERT INTO master.crm_da_ban_phi (phien_ban_id, phap_nhan_id, thu_tu, ten, loai, muc, don_vi_tinh, tien_te, co_so_tinh)
                    VALUES (pb, p_pn, r.o, r.e ->> 'ten', r.e ->> 'loai', r.e ->> 'muc', r.e ->> 'don_vi_tinh', r.e ->> 'tien_te', r.e ->> 'co_so_tinh');
            END LOOP;
            RETURN pb;
        END $$""",
    # ======================================================================= lệnh: bật bán từ danh mục dự án kế toán
    """CREATE OR REPLACE FUNCTION master.crm_da_bat_ban(p_khoa text, p_h text, p_du_an uuid, p_tt jsonb, p_phi jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); a record; cu jsonb; kq jsonb; da uuid; pb uuid; ngay date := master.ktt_ngay();
        BEGIN
            SELECT * INTO a FROM master.du_an WHERE id = p_du_an;
            cu := master.crm_da_vao('CRM_DA_BAT_BAN', a.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            IF a.trang_thai = 'DONG' OR a.valid_to IS NOT NULL THEN
                RAISE EXCEPTION 'CRM_DA_DU_AN_DONG: dự án đã đóng trong danh mục dự án kế toán' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_da|' || p_du_an::text, 0));
            IF EXISTS (SELECT 1 FROM master.crm_da_ban WHERE du_an_id = p_du_an) THEN
                RAISE EXCEPTION 'CRM_DA_DA_CO: dự án đã có trong danh mục dự án đang bán — dùng Sửa hoặc Mở bán lại' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_da_ban (phap_nhan_id, du_an_id, tao_boi) VALUES (a.phap_nhan_id, p_du_an, ai) RETURNING id INTO da;
            pb := master.crm_da_ghi_phien_ban(da, a.phap_nhan_id, 1, ngay, true, p_tt, p_phi, p_ly_do, ai, true);
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
                VALUES (a.phap_nhan_id, ai, 'SUA_DANH_MUC', 'master.crm_da_ban', da, 'CRM_DA_BAT_BAN',
                        jsonb_build_object('phien_ban', 1, 'phien_ban_id', pb, 'hieu_luc_tu', ngay, 'du_an_id', p_du_an,
                                           'noi_dung', master.crm_da_noi_dung(pb)), nullif(btrim(p_ly_do), ''));
            kq := jsonb_build_object('da_ban_id', da, 'du_an_id', p_du_an, 'phien_ban_id', pb, 'phien_ban', 1, 'hieu_luc_tu', ngay, 'dang_ban', true,
                                     'khong_doi', false);""" + _KET.format(pn="a.phap_nhan_id", a="'CRM_DA_BAT_BAN'") + """
        END $$""",
    # ======================================================================= lệnh: sửa thông tin / sửa phí → phiên bản mới (CAS phiên bản đang dùng)
    """CREATE OR REPLACE FUNCTION master.crm_da_cap_nhat(p_khoa text, p_h text, p_hanh text, p_da uuid, p_expected integer, p_tt jsonb, p_phi jsonb,
                                                      p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; v record; cu jsonb; kq jsonb; pb uuid; ngay date := master.ktt_ngay();
                nd_cu jsonb; nd_moi jsonb; v_tt jsonb; v_phi jsonb; khac jsonb;
        BEGIN
            IF p_hanh IS NULL OR p_hanh NOT IN ('CRM_DA_CAP_NHAT','CRM_DA_PHI') THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: thao tác sửa dự án đang bán không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.crm_da_ban WHERE id = p_da;
            cu := master.crm_da_vao(p_hanh, d.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            PERFORM 1 FROM master.crm_da_ban WHERE id = p_da FOR UPDATE;
            SELECT * INTO v FROM master.crm_da_ban_phien_ban WHERE da_ban_id = p_da AND hieu_luc_den IS NULL FOR UPDATE;
            IF p_expected IS NULL OR v.phien_ban IS DISTINCT FROM p_expected THEN
                RAISE EXCEPTION 'CRM_DA_PHIEN_BAN_CU: thông tin dự án đang ở phiên bản % — tải lại rồi sửa', v.phien_ban USING ERRCODE = 'P0001';
            END IF;
            IF ngay < v.hieu_luc_tu THEN
                RAISE EXCEPTION 'CRM_DA_NGAY_LUI: ngày hiện hành % trước ngày hiệu lực % của phiên bản đang dùng', ngay, v.hieu_luc_tu USING ERRCODE = 'P0001';
            END IF;
            nd_cu := master.crm_da_noi_dung(v.id);
            v_tt := CASE WHEN p_hanh = 'CRM_DA_PHI' THEN nd_cu -> 'thong_tin' ELSE master.crm_da_tt_chuan(p_tt) END;
            v_phi := CASE WHEN p_hanh = 'CRM_DA_CAP_NHAT' THEN coalesce(p_phi, nd_cu -> 'phi') ELSE p_phi END;
            IF v_tt IS NULL OR v_phi IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: thiếu thông tin dự án hoặc danh sách phí' USING ERRCODE = 'P0001';
            END IF;
            PERFORM master.crm_da_kiem(d.phap_nhan_id, v_tt, v_phi);
            nd_moi := master.crm_da_noi_dung_tu(v.dang_ban, v_tt, v_phi);
            IF nd_moi = nd_cu THEN
                kq := jsonb_build_object('da_ban_id', p_da, 'du_an_id', d.du_an_id, 'phien_ban_id', v.id, 'phien_ban', v.phien_ban,
                                         'hieu_luc_tu', v.hieu_luc_tu, 'dang_ban', v.dang_ban, 'khong_doi', true, 'khac', '[]'::jsonb);
            ELSE
                UPDATE master.crm_da_ban_phien_ban SET hieu_luc_den = ngay WHERE id = v.id;
                pb := master.crm_da_ghi_phien_ban(p_da, d.phap_nhan_id, v.phien_ban + 1, ngay, v.dang_ban, v_tt, v_phi, p_ly_do, ai, true);
                SELECT coalesce(jsonb_agg(x.k ORDER BY x.k), '[]'::jsonb) INTO khac FROM (
                    SELECT t.k FROM jsonb_object_keys(nd_moi -> 'thong_tin') AS t(k)
                     WHERE (nd_moi -> 'thong_tin' -> t.k) IS DISTINCT FROM (nd_cu -> 'thong_tin' -> t.k)
                    UNION ALL SELECT 'phi'::text WHERE (nd_moi -> 'phi') IS DISTINCT FROM (nd_cu -> 'phi')) AS x(k);
                INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do)
                    VALUES (d.phap_nhan_id, ai, 'SUA_DANH_MUC', 'master.crm_da_ban', p_da, p_hanh,
                            jsonb_build_object('phien_ban', v.phien_ban, 'phien_ban_id', v.id, 'noi_dung', nd_cu),
                            jsonb_build_object('phien_ban', v.phien_ban + 1, 'phien_ban_id', pb, 'hieu_luc_tu', ngay, 'khac', khac,
                                               'noi_dung', master.crm_da_noi_dung(pb)), nullif(btrim(p_ly_do), ''));
                kq := jsonb_build_object('da_ban_id', p_da, 'du_an_id', d.du_an_id, 'phien_ban_id', pb, 'phien_ban', v.phien_ban + 1,
                                         'hieu_luc_tu', ngay, 'dang_ban', v.dang_ban, 'khong_doi', false, 'khac', khac, 'dong_phien_ban_truoc', v.id);
            END IF;""" + _KET.format(pn="d.phap_nhan_id", a="p_hanh") + """
        END $$""",
    # ======================================================================= lệnh: ngừng bán / mở bán lại = phiên bản mới + sự kiện QUYET_DINH
    """CREATE OR REPLACE FUNCTION master.crm_da_doi_trang_thai(p_khoa text, p_h text, p_da uuid, p_expected integer, p_dang_ban boolean, p_ly_do text)
        RETURNS jsonb LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; v record; cu jsonb; kq jsonb; pb uuid; ngay date := master.ktt_ngay(); nd_cu jsonb;
                hanh text := CASE WHEN p_dang_ban THEN 'CRM_DA_MO_BAN_LAI' ELSE 'CRM_DA_NGUNG_BAN' END;
        BEGIN
            IF p_dang_ban IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: thiếu trạng thái bán' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.crm_da_ban WHERE id = p_da;
            cu := master.crm_da_vao(hanh, d.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            IF NOT p_dang_ban AND coalesce(btrim(p_ly_do), '') = '' THEN
                RAISE EXCEPTION 'CRM_DA_THIEU_LY_DO: ngừng bán cần lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM 1 FROM master.crm_da_ban WHERE id = p_da FOR UPDATE;
            SELECT * INTO v FROM master.crm_da_ban_phien_ban WHERE da_ban_id = p_da AND hieu_luc_den IS NULL FOR UPDATE;
            IF p_expected IS NULL OR v.phien_ban IS DISTINCT FROM p_expected THEN
                RAISE EXCEPTION 'CRM_DA_PHIEN_BAN_CU: thông tin dự án đang ở phiên bản % — tải lại rồi thao tác', v.phien_ban USING ERRCODE = 'P0001';
            END IF;
            IF v.dang_ban = p_dang_ban THEN
                RAISE EXCEPTION 'CRM_DA_TRANG_THAI: dự án đã ở trạng thái %', CASE WHEN v.dang_ban THEN 'đang bán' ELSE 'ngừng bán' END USING ERRCODE = 'P0001';
            END IF;
            IF ngay < v.hieu_luc_tu THEN
                RAISE EXCEPTION 'CRM_DA_NGAY_LUI: ngày hiện hành % trước ngày hiệu lực % của phiên bản đang dùng', ngay, v.hieu_luc_tu USING ERRCODE = 'P0001';
            END IF;
            nd_cu := master.crm_da_noi_dung(v.id);
            UPDATE master.crm_da_ban_phien_ban SET hieu_luc_den = ngay WHERE id = v.id;
            -- ngừng bán chép nguyên nội dung đã lưu (luôn làm được); mở bán lại kiểm lại loại hình/tiền tệ hiện hành
            pb := master.crm_da_ghi_phien_ban(p_da, d.phap_nhan_id, v.phien_ban + 1, ngay, p_dang_ban, nd_cu -> 'thong_tin', nd_cu -> 'phi', p_ly_do, ai,
                                              p_dang_ban);
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do)
                VALUES (d.phap_nhan_id, ai, 'QUYET_DINH', 'master.crm_da_ban', p_da, hanh,
                        jsonb_build_object('phien_ban', v.phien_ban, 'phien_ban_id', v.id, 'dang_ban', v.dang_ban),
                        jsonb_build_object('phien_ban', v.phien_ban + 1, 'phien_ban_id', pb, 'hieu_luc_tu', ngay, 'dang_ban', p_dang_ban),
                        nullif(btrim(p_ly_do), ''));
            kq := jsonb_build_object('da_ban_id', p_da, 'du_an_id', d.du_an_id, 'phien_ban_id', pb, 'phien_ban', v.phien_ban + 1, 'hieu_luc_tu', ngay,
                                     'dang_ban', p_dang_ban, 'khong_doi', false, 'dong_phien_ban_truoc', v.id);""" + _KET.format(pn="d.phap_nhan_id", a="hanh") + """
        END $$""",
    # ======================================================================= lệnh: lô/căn (thêm mới; đổi = đóng dòng lịch sử + dòng mới; CAS theo lần)
    """CREATE OR REPLACE FUNCTION master.crm_da_lo_ghi(p_khoa text, p_h text, p_da uuid, p_lo jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; cu jsonb; kq jsonb; ngay date := master.ktt_ngay(); r record; o record; s record;
                v_ma text; v_tt text; moi jsonb := '[]'::jsonb; doi jsonb := '[]'::jsonb; giu integer := 0; ra jsonb := '[]'::jsonb; lo uuid;
        BEGIN
            SELECT * INTO d FROM master.crm_da_ban WHERE id = p_da;
            cu := master.crm_da_vao('CRM_DA_LO', d.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            IF p_lo IS NULL OR jsonb_typeof(p_lo) <> 'array' OR jsonb_array_length(p_lo) = 0 OR jsonb_array_length(p_lo) > 500 THEN
                RAISE EXCEPTION 'CRM_DA_LO_SAI: danh sách lô/căn cần 1–500 dòng' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_lo) e WHERE jsonb_typeof(e) <> 'object' OR jsonb_typeof(e -> 'ma') IS DISTINCT FROM 'string')
               OR (SELECT count(DISTINCT upper(e ->> 'ma')) FROM jsonb_array_elements(p_lo) e) <> jsonb_array_length(p_lo) THEN
                RAISE EXCEPTION 'CRM_DA_LO_SAI: mỗi dòng lô/căn cần mã (chuỗi), không trùng mã trong danh sách' USING ERRCODE = 'P0001';
            END IF;
            PERFORM 1 FROM master.crm_da_ban WHERE id = p_da FOR UPDATE;
            FOR r IN SELECT e, i FROM jsonb_array_elements(p_lo) WITH ORDINALITY AS x(e, i) LOOP
                IF EXISTS (SELECT 1 FROM jsonb_each(r.e) k WHERE k.key <> ALL (""" + _LO_KHOA + """)
                               OR (k.key <> 'expected_lan' AND jsonb_typeof(k.value) NOT IN ('string','null'))
                               OR (k.key = 'expected_lan' AND jsonb_typeof(k.value) NOT IN ('number','null'))) THEN
                    RAISE EXCEPTION 'CRM_DA_LO_SAI: lô/căn dòng % chỉ gồm mã, diện tích, trạng thái, ghi chú, lần mong đợi', r.i USING ERRCODE = 'P0001';
                END IF;
                v_ma := r.e ->> 'ma';
                IF coalesce(r.e ->> 'dien_tich', '') !~ """ + _RE_SO + """ THEN
                    RAISE EXCEPTION 'CRM_DA_SO_SAI: diện tích lô/căn % phải là số dương (chữ số 0–9, dấu chấm thập phân)', v_ma USING ERRCODE = 'P0001';
                END IF;
                IF (r.e ->> 'dien_tich')::numeric <= 0 THEN
                    RAISE EXCEPTION 'CRM_DA_SO_SAI: diện tích lô/căn % phải lớn hơn 0', v_ma USING ERRCODE = 'P0001';
                END IF;
                IF (r.e ->> 'expected_lan') IS NOT NULL AND (r.e ->> 'expected_lan') !~ '^[0-9]{1,9}$' THEN
                    RAISE EXCEPTION 'CRM_DA_LO_SAI: lần mong đợi của lô/căn % phải là số nguyên', v_ma USING ERRCODE = 'P0001';
                END IF;
                SELECT * INTO o FROM master.crm_da_ban_lo WHERE da_ban_id = p_da AND upper(ma) = upper(v_ma);
                IF o.id IS NULL THEN
                    IF (r.e ->> 'expected_lan') IS NOT NULL THEN
                        RAISE EXCEPTION 'CRM_DA_LO_LAN_CU: lô/căn % chưa có trong danh mục — bỏ lần mong đợi để thêm mới', v_ma USING ERRCODE = 'P0001';
                    END IF;
                    INSERT INTO master.crm_da_ban_lo (da_ban_id, phap_nhan_id, ma, tao_boi) VALUES (p_da, d.phap_nhan_id, v_ma, ai) RETURNING id INTO lo;
                    INSERT INTO master.crm_da_ban_lo_ls (lo_id, phap_nhan_id, lan, hieu_luc_tu, dien_tich, trang_thai, ghi_chu, tao_boi)
                        VALUES (lo, d.phap_nhan_id, 1, ngay, r.e ->> 'dien_tich', coalesce(r.e ->> 'trang_thai', 'CON_TRONG'), r.e ->> 'ghi_chu', ai);
                    moi := moi || to_jsonb(v_ma);
                    ra := ra || jsonb_build_array(jsonb_build_object('ma', v_ma, 'lo_id', lo, 'lan', 1, 'doi', true));
                ELSE
                    SELECT * INTO s FROM master.crm_da_ban_lo_ls WHERE lo_id = o.id AND hieu_luc_den IS NULL FOR UPDATE;
                    IF (r.e ->> 'expected_lan') IS NULL OR (r.e ->> 'expected_lan')::integer IS DISTINCT FROM s.lan THEN
                        RAISE EXCEPTION 'CRM_DA_LO_LAN_CU: lô/căn % đã đổi (lần %) — tải lại rồi sửa', o.ma, s.lan USING ERRCODE = 'P0001';
                    END IF;
                    IF ngay < s.hieu_luc_tu THEN
                        RAISE EXCEPTION 'CRM_DA_NGAY_LUI: ngày hiện hành % trước ngày hiệu lực % của lô/căn %', ngay, s.hieu_luc_tu, o.ma USING ERRCODE = 'P0001';
                    END IF;
                    v_tt := coalesce(r.e ->> 'trang_thai', s.trang_thai);
                    IF (r.e ->> 'dien_tich')::numeric = s.dien_tich::numeric AND v_tt = s.trang_thai AND (r.e ->> 'ghi_chu') IS NOT DISTINCT FROM s.ghi_chu THEN
                        giu := giu + 1;
                        ra := ra || jsonb_build_array(jsonb_build_object('ma', o.ma, 'lo_id', o.id, 'lan', s.lan, 'doi', false));
                    ELSE
                        UPDATE master.crm_da_ban_lo_ls SET hieu_luc_den = ngay WHERE lo_id = o.id AND lan = s.lan;
                        INSERT INTO master.crm_da_ban_lo_ls (lo_id, phap_nhan_id, lan, hieu_luc_tu, dien_tich, trang_thai, ghi_chu, tao_boi)
                            VALUES (o.id, d.phap_nhan_id, s.lan + 1, ngay, r.e ->> 'dien_tich', v_tt, r.e ->> 'ghi_chu', ai);
                        doi := doi || to_jsonb(o.ma);
                        ra := ra || jsonb_build_array(jsonb_build_object('ma', o.ma, 'lo_id', o.id, 'lan', s.lan + 1, 'doi', true));
                    END IF;
                END IF;
            END LOOP;
            IF jsonb_array_length(moi) + jsonb_array_length(doi) > 0 THEN
                INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
                    VALUES (d.phap_nhan_id, ai, 'SUA_DANH_MUC', 'master.crm_da_ban', p_da, 'CRM_DA_LO',
                            jsonb_build_object('moi', moi, 'doi', doi, 'giu', giu, 'hieu_luc_tu', ngay), nullif(btrim(p_ly_do), ''));
            END IF;
            kq := jsonb_build_object('da_ban_id', p_da, 'du_an_id', d.du_an_id, 'moi', jsonb_array_length(moi), 'doi', jsonb_array_length(doi),
                                     'giu', giu, 'hieu_luc_tu', ngay, 'lo', ra);""" + _KET.format(pn="d.phap_nhan_id", a="'CRM_DA_LO'") + """
        END $$""",
    # ======================================================================= G7 áp dụng ngay (QD-20261025-07: bỏ bước CFO duyệt)
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_ap_dung(p_khoa text, p_h text, p_du_an uuid, p_giai_doan text, p_dong jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); a record; d record; cu jsonb; kq jsonb; b record; mo record; pb uuid; n integer; r record;
                so integer; ngay date := master.ktt_ngay(); cuoi date; gd text; sha text;
        BEGIN
            SELECT * INTO a FROM master.du_an WHERE id = p_du_an;
            cu := master.crm_da_vao('CRM_CHUAN_AP_DUNG', a.phap_nhan_id, p_khoa, p_h);""" + _REPLAY + """
            SELECT * INTO d FROM master.crm_da_ban WHERE du_an_id = p_du_an;
            IF d.id IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_CHUA_BAT_BAN: dự án chưa có trong danh mục dự án đang bán — bật bán trước khi khai tiến độ tiêu chuẩn' USING ERRCODE = 'P0001';
            END IF;
            gd := nullif(p_giai_doan, '');
            IF gd IS NULL THEN
                SELECT v.giai_doan_g7 INTO gd FROM master.crm_da_ban_phien_ban v WHERE v.da_ban_id = d.id AND v.hieu_luc_den IS NULL;
            END IF;
            IF gd IS NULL OR gd !~ """ + _GD_RE + """ THEN
                RAISE EXCEPTION 'CRM_DA_THIEU_GIAI_DOAN: cần giai đoạn tiến độ (chữ/số/_ . -, 1–80) — khai ở thông tin dự án hoặc gửi kèm' USING ERRCODE = 'P0001';
            END IF;
            IF p_dong IS NULL OR jsonb_typeof(p_dong) <> 'array' OR jsonb_array_length(p_dong) = 0 OR jsonb_array_length(p_dong) > 200 THEN
                RAISE EXCEPTION 'CRM_G_CHUAN_SAI: bộ chuẩn cần 1–200 dòng' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g_chuan|' || p_du_an::text || '|' || gd, 0));
            SELECT * INTO b FROM master.crm_bo_chuan WHERE phap_nhan_id = a.phap_nhan_id AND du_an_id = p_du_an AND giai_doan = gd FOR UPDATE;
            IF NOT FOUND THEN
                INSERT INTO master.crm_bo_chuan (phap_nhan_id, du_an_id, giai_doan, tao_boi) VALUES (a.phap_nhan_id, p_du_an, gd, ai) RETURNING * INTO b;
            END IF;
            SELECT max(valid_from) INTO cuoi FROM master.crm_bo_chuan_phien_ban WHERE bo_chuan_id = b.id AND trang_thai = 'HIEU_LUC';
            IF cuoi IS NOT NULL AND cuoi > ngay THEN
                RAISE EXCEPTION 'CRM_G_HIEU_LUC_CHONG: đã có tiến độ tiêu chuẩn duyệt hiệu lực từ % (sau hôm nay) — không áp dụng chồng', cuoi USING ERRCODE = 'P0001';
            END IF;
            sha := encode(sha256(convert_to(p_dong::text, 'UTF8')), 'hex');
            SELECT * INTO mo FROM master.crm_bo_chuan_phien_ban WHERE bo_chuan_id = b.id AND trang_thai = 'HIEU_LUC' AND valid_to IS NULL FOR UPDATE;
            IF mo.id IS NOT NULL AND mo.dong_sha256 = sha THEN
                kq := jsonb_build_object('bo_chuan_id', b.id, 'du_an_id', p_du_an, 'giai_doan', gd, 'phien_ban_id', mo.id, 'phien_ban', mo.phien_ban,
                                         'trang_thai', 'HIEU_LUC', 'valid_from', mo.valid_from, 'so_dong', mo.so_dong, 'khong_doi', true,
                                         'can_cu', '""" + CAN_CU_G7 + """');
            ELSE
                SELECT coalesce(max(phien_ban), 0) + 1 INTO n FROM master.crm_bo_chuan_phien_ban WHERE bo_chuan_id = b.id;
                so := jsonb_array_length(p_dong);
                INSERT INTO master.crm_bo_chuan_phien_ban (bo_chuan_id, phap_nhan_id, phien_ban, trang_thai, so_dong, dong_sha256, lap_boi)
                    VALUES (b.id, a.phap_nhan_id, n, 'DRAFT', so, sha, ai) RETURNING id INTO pb;
                FOR r IN SELECT e, ord FROM jsonb_array_elements(p_dong) WITH ORDINALITY AS x(e, ord) LOOP
                    IF jsonb_typeof(r.e) <> 'object' THEN
                        RAISE EXCEPTION 'CRM_G_CHUAN_SAI: mỗi dòng là object' USING ERRCODE = 'P0001';
                    END IF;
                    INSERT INTO master.crm_bo_chuan_dong (phien_ban_id, phap_nhan_id, thu_tu, lan, gia_tri_loai, gia_tri_thap_phan, so_tien_minor, tien_te,
                                                          moc_loai, moc_ngay, moc_su_kien, ghi_chu)
                        VALUES (pb, a.phap_nhan_id, r.ord, r.e ->> 'lan', r.e ->> 'gia_tri_loai', r.e ->> 'gia_tri_thap_phan', r.e ->> 'so_tien_minor',
                                r.e ->> 'tien_te', r.e ->> 'moc_loai', (r.e ->> 'moc_ngay')::date, r.e ->> 'moc_su_kien', r.e ->> 'ghi_chu');
                END LOOP;
                IF mo.id IS NOT NULL THEN  -- đóng phiên bản đang hiệu lực tại hôm nay (cùng ngày → khoảng rỗng, không còn được chọn)
                    UPDATE master.crm_bo_chuan_phien_ban SET valid_to = ngay, cap_nhat_luc = clock_timestamp() WHERE id = mo.id;
                END IF;
                UPDATE master.crm_bo_chuan_phien_ban SET trang_thai = 'HIEU_LUC', valid_from = ngay, cap_nhat_luc = clock_timestamp() WHERE id = pb;
                INSERT INTO master.crm_bo_chuan_ap_dung (phien_ban_id, phap_nhan_id, da_ban_id, can_cu, hieu_luc_tu, dong_phien_ban_truoc, ap_dung_boi)
                    VALUES (pb, a.phap_nhan_id, d.id, '""" + CAN_CU_G7 + """', ngay, mo.id, ai);
                INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do, can_cu)
                    VALUES (a.phap_nhan_id, ai, 'QUYET_DINH', 'master.crm_bo_chuan_phien_ban', pb, 'CRM_CHUAN_AP_DUNG',
                            jsonb_build_object('giai_doan', gd, 'phien_ban', n, 'so_dong', so, 'valid_from', ngay, 'dong_phien_ban_truoc', mo.id,
                                               'da_ban_id', d.id),
                            'Bán hàng áp dụng ngay tiến độ thanh toán tiêu chuẩn — bỏ bước CFO duyệt (""" + CAN_CU_G7 + """)',
                            jsonb_build_object('quyet_dinh', '""" + CAN_CU_G7 + """'));
                kq := jsonb_build_object('bo_chuan_id', b.id, 'du_an_id', p_du_an, 'giai_doan', gd, 'phien_ban_id', pb, 'phien_ban', n,
                                         'trang_thai', 'HIEU_LUC', 'valid_from', ngay, 'so_dong', so, 'khong_doi', false, 'dong_phien_ban_truoc', mo.id,
                                         'can_cu', '""" + CAN_CU_G7 + """');
            END IF;""" + _KET.format(pn="a.phap_nhan_id", a="'CRM_CHUAN_AP_DUNG'") + """
        END $$""",
    # ======================================================================= ảnh chụp mặc định (DA-3 báo giá nạp mặc định; DA-2 chi tiết)
    """CREATE OR REPLACE FUNCTION master.crm_da_anh_chup_pb(p_pb uuid, p_ngay date) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE v record; d record; a record; l record; kq jsonb; bc jsonb; bc_pb uuid;
        BEGIN""" + _CHU + """
            SELECT * INTO v FROM master.crm_da_ban_phien_ban WHERE id = p_pb;
            IF v.id IS NULL OR NOT master.crm_da_duoc_doc(v.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy phiên bản dự án đang bán (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF p_ngay IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: cần ngày ảnh chụp' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.crm_da_ban WHERE id = v.da_ban_id;
            SELECT * INTO a FROM master.du_an WHERE id = d.du_an_id;
            SELECT * INTO l FROM master.loai_hinh_doanh_thu WHERE id = v.loai_hinh_id;
            IF v.giai_doan_g7 IS NOT NULL THEN
                bc := master.crm_g_chuan_doc(d.du_an_id, v.giai_doan_g7, p_ngay);
                bc_pb := (bc -> 'version' ->> 'id')::uuid;
                bc := bc || jsonb_build_object('giai_doan', v.giai_doan_g7,
                    'nguon', CASE WHEN bc_pb IS NULL THEN NULL
                                  WHEN EXISTS (SELECT 1 FROM master.crm_bo_chuan_ap_dung x WHERE x.phien_ban_id = bc_pb) THEN 'AP_DUNG_NGAY'
                                  ELSE 'CFO_DUYET' END);
            END IF;
            kq := jsonb_build_object(
                'kieu', 'CRM_DA_ANH_CHUP_V1',
                'trang_thai', CASE WHEN v.dang_ban THEN 'DANG_BAN' ELSE 'NGUNG_BAN' END,
                'du_an_id', d.du_an_id, 'da_ban_id', d.id, 'phap_nhan_id', d.phap_nhan_id,
                'du_an', jsonb_build_object('ma', a.ma_junsky, 'ten', a.ten),
                'phien_ban', jsonb_build_object('id', v.id, 'so', v.phien_ban, 'hieu_luc_tu', v.hieu_luc_tu, 'hieu_luc_den', v.hieu_luc_den,
                                                'dang_ban', v.dang_ban, 'lap_boi', v.lap_boi, 'noi_dung_sha256', v.noi_dung_sha256),
                'thong_tin', jsonb_build_object('vi_tri', v.vi_tri, 'mo_ta', v.mo_ta),
                'don_gia', v.don_gia_niem_yet, 'tien_te', v.tien_te,
                'loai_hinh', jsonb_build_object('id', l.id, 'ma', l.ma, 'ten', l.ten, 'phien_ban', l.phien_ban, 'con_hieu_luc', l.valid_to IS NULL),
                'thue', jsonb_build_object('co_so_thue', v.co_so_thue, 'vat_phan_tram', v.vat_phan_tram),
                'giai_doan_g7', v.giai_doan_g7,
                'phi', (SELECT coalesce(jsonb_agg(jsonb_build_object('thu_tu', f.thu_tu, 'ten', f.ten, 'loai', f.loai, 'muc', f.muc,
                                                                     'don_vi_tinh', f.don_vi_tinh, 'tien_te', f.tien_te, 'co_so_tinh', f.co_so_tinh)
                                                  ORDER BY f.thu_tu), '[]'::jsonb)
                        FROM master.crm_da_ban_phi f WHERE f.phien_ban_id = v.id),
                'lo', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'ma', o.ma, 'dien_tich', s.dien_tich, 'trang_thai', s.trang_thai,
                                                                    'ghi_chu', s.ghi_chu, 'lan', s.lan, 'hieu_luc_tu', s.hieu_luc_tu)
                                                 ORDER BY upper(o.ma), o.ma), '[]'::jsonb)
                       FROM master.crm_da_ban_lo o JOIN master.crm_da_ban_lo_ls s ON s.lo_id = o.id
                       WHERE o.da_ban_id = d.id AND s.hieu_luc_tu <= p_ngay AND (s.hieu_luc_den IS NULL OR p_ngay < s.hieu_luc_den)),
                'bo_chuan', bc,
                'giai_doan_co_chuan', (SELECT coalesce(jsonb_agg(DISTINCT b.giai_doan ORDER BY b.giai_doan), '[]'::jsonb)
                                       FROM master.crm_bo_chuan b JOIN master.crm_bo_chuan_phien_ban p ON p.bo_chuan_id = b.id
                                       WHERE b.du_an_id = d.du_an_id AND b.phap_nhan_id = d.phap_nhan_id AND p.trang_thai = 'HIEU_LUC'
                                         AND p.valid_from <= p_ngay AND (p.valid_to IS NULL OR p_ngay < p.valid_to)));
            -- sha của NỘI DUNG (không gồm ngày đọc): cùng tiêu chuẩn → cùng sha bất kể ngày nạp; DA-3 so lại trong lệnh lưu báo giá
            RETURN kq || jsonb_build_object('ngay', p_ngay, 'anh_chup_sha256', encode(sha256(convert_to(kq::text, 'UTF8')), 'hex'));
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_da_anh_chup(p_du_an uuid, p_ngay date) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE a record; d record; pb uuid;
        BEGIN""" + _CHU + """
            SELECT * INTO a FROM master.du_an WHERE id = p_du_an;
            IF a.id IS NULL OR NOT master.crm_da_duoc_doc(a.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF p_ngay IS NULL THEN
                RAISE EXCEPTION 'CRM_DA_YEU_CAU_SAI: cần ngày ảnh chụp' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.crm_da_ban WHERE du_an_id = p_du_an;
            IF d.id IS NOT NULL THEN
                SELECT v.id INTO pb FROM master.crm_da_ban_phien_ban v
                    WHERE v.da_ban_id = d.id AND v.hieu_luc_tu <= p_ngay AND (v.hieu_luc_den IS NULL OR p_ngay < v.hieu_luc_den);
            END IF;
            IF pb IS NULL THEN
                RETURN jsonb_build_object('kieu', 'CRM_DA_ANH_CHUP_V1', 'trang_thai', CASE WHEN d.id IS NULL THEN 'CHUA_BAT_BAN' ELSE 'CHUA_CO_PHIEN_BAN' END,
                                          'du_an_id', p_du_an, 'da_ban_id', d.id, 'phap_nhan_id', a.phap_nhan_id, 'ngay', p_ngay, 'phien_ban', NULL);
            END IF;
            RETURN master.crm_da_anh_chup_pb(pb, p_ngay);
        END $$""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm không cấp PUBLIC
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
    "REVOKE EXECUTE ON FUNCTION master.crm_da_dong_mot_lan(), " + ", ".join(_HAM) + " FROM PUBLIC",
)
