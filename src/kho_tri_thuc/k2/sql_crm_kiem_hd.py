"""CRM-41-06A (G6A) — hợp đồ SQL: kế toán kiểm hợp đồng đã ký từ mẫu + kích hoạt HIEU_LUC có điều kiện, nguyên tử.

CHỈ HẰNG SỐ. Module này KHÔNG import/sửa ``ha_tang.pg_migrations`` và KHÔNG tự đăng ký migration: registry PG là bất biến với gói này.
Root integration owner import ``CRM_G6A_SQL`` và APPEND thành MỘT migration mới SAU M4M24 đã chốt (ordinal do owner cấp — gói này không
đoán ordinal, không tuyên bố đã cài). Trước khi append phải đối chiếu nguyên văn thân ``kho.viec_chu_so_huu`` hiện hành (M0021) với bản
sao ở dưới (chỉ thêm MỘT nhánh typed G6A); M4M24 có sửa thân hàm đó thì phải hợp nhất lại trước, không ghi đè mù.

Nội dung (mọi guard nằm ở CSDL — đường lệnh và SQL trực tiếp trên kết nối chủ bảng đi qua CÙNG bất biến, không chỉ HTTP):
  * phạm vi kiểm mỏng ``crm_kiem_pham_vi`` (phân công CRM_HD_KIEM hiện hành × đúng HĐ/bản ký/dự án; quản trị ghi, thu hồi một lần);
  * hồ sơ kiểm + revision KT (checklist 5 mục, mã Junsky CÓ SẴN, ngày hiệu lực + căn cứ), lần check (đồ thị không PII + sha256),
    xử lý lệch G5/G7 "theo bản ký", quyết định HIEU_LUC/BO_SUNG/TRA_LAI, dòng hoàn tất kích hoạt;
  * G5: chế độ VAN_HANH luôn HOLD (``UNREGISTERED_G5_PROOF``) — PENDING/NOT_SELECTED khởi tạo của G4 KHÔNG là bằng chứng; chế độ
    SYNTHETIC_FIXTURE chỉ cho fixture kiểm thử (GUC ``ktt.crm_kiem_g5`` do test đặt trong giao dịch; bảng nguồn ``phi_van_hanh``),
    không phải nghiệm thu, không producer/policy/chọn mẫu vận hành;
  * kích hoạt: master.hop_dong DA_KY→HIEU_LUC + kho.chung_tu HOP_DONG_TEP (bằng chứng bản ký) + hop_dong_phien_ban v1 GOC nguồn
    CRM_MAU DA_DUYET (KT kiểm) + hop_dong_tham_so + lich_thu — các bảng F6 (fact_hop_dong_m1) và F7 (lien_ket) đang đọc;
  * trả lại: chỉ ghi TRA_LAI_CHO_KY_LAI (chặn phụ thuộc) — KHÔNG mở khóa/sửa bản ký/PDF G4, không giả "về nháp".
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
_GK_KHAI = "ai text := master.ktt_danh_tinh(); d record; cu jsonb; kq jsonb;"
_GK_SHA = "encode(sha256(convert_to({x}::text, 'UTF8')), 'hex')"
_G_TYPED = "('master.crm_mau_phien_ban','master.crm_bo_chuan_phien_ban')"

_KIEM_TYPED = "('master.crm_kiem_ho_so','master.crm_kiem_hieu_luc')"
_KIEM_BANG_MOI = ("crm_kiem_pham_vi", "crm_kiem_ho_so", "crm_kiem_rev", "crm_kiem_check", "crm_kiem_g5_nguon", "crm_kiem_g5_chinh_sach",
                  "crm_kiem_g5_ket_qua", "crm_kiem_xu_ly_lech", "crm_kiem_quyet_dinh", "crm_kiem_hieu_luc")
_KIEM_RE_SO = "'^[0-9]{1,24}(\\.[0-9]{1,12})?$'"
_KIEM_CHECKLIST = "ARRAY['ban_ky_dung_ban_xuat','ben_ky_dung','dieu_khoan_dung','gia_tri_lich_dung','khach_dung']"
_KIEM_HIEN_THI = ("CASE {c} WHEN 'DANG_KIEM' THEN 'Đang kế toán kiểm' WHEN 'CHO_BO_SUNG' THEN 'Chờ bổ sung' "
                  "WHEN 'TRA_LAI_CHO_KY_LAI' THEN 'Trả lại — chờ quy trình ký lại (chưa mở lại G4)' WHEN 'HIEU_LUC' THEN 'Hiệu lực' "
                  "ELSE 'Đã ký — chờ kế toán kiểm' END")
# mở đầu chung của lệnh: máy chủ (chủ bảng) → ghim quyền + phạm vi (FOR SHARE) → đích/quyền hiện hành → khóa HĐ → (sau đó) biên nhận
_KIEM_MO = _G_CHU + """
            PERFORM master.crm_g_ghim_quyen((SELECT k0.phap_nhan_id FROM master.crm_hd_ky k0 WHERE k0.id = p_ky));
            PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = p_ky AND b.thu_hoi_luc IS NULL FOR SHARE;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, true);
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            SELECT * INTO h FROM master.hop_dong WHERE id = k.hop_dong_id FOR UPDATE;"""
_KIEM_HO_SO = """
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE ky_id = p_ky FOR UPDATE;
            IF ho.id IS NULL OR ho.trang_thai NOT IN {tt} THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: hồ sơ kiểm không ở trạng thái cho phép (hiện %)', coalesce(ho.trang_thai, 'CHUA_KIEM') """ + _G_LOI + """;
            END IF;
            IF p_expected IS NULL OR p_expected <> ho.revision THEN
                RAISE EXCEPTION 'CRM_KIEM_REVISION_CU: hồ sơ kiểm đã có revision mới — tải lại rồi thao tác' """ + _G_LOI + """;
            END IF;"""
_KIEM_LY_DO = """
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' OR length(p_ly_do) > 1000 OR p_ly_do ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: cần lý do (1–1000 ký tự)' """ + _G_LOI + """;
            END IF;"""
_KIEM_TXID = "(SELECT q0.id FROM master.crm_kiem_quyet_dinh q0 WHERE q0.hop_dong_id = {hd} AND q0.loai = {loai} AND q0.tao_txid = txid_current())"

CRM_G6A_SQL = (
    "SET LOCAL check_function_bodies = off",
    # ======================================================================= discriminator/nguồn: thêm giá trị (giá trị cũ giữ nguyên)
    "ALTER TABLE master.hop_dong DROP CONSTRAINT hop_dong_crm_giao_ket_check",
    """ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_crm_giao_ket_check
        CHECK (crm_giao_ket IS NULL OR crm_giao_ket IN ('SOAN_THAO','CHO_KY','DA_KY','HIEU_LUC'))""",
    "ALTER TABLE master.hop_dong_phien_ban DROP CONSTRAINT hop_dong_phien_ban_nguon_check",
    """ALTER TABLE master.hop_dong_phien_ban ADD CONSTRAINT hop_dong_phien_ban_nguon_check
        CHECK (nguon IN ('LLM','REVIEW_5','TRICH_6','SHEET','TAY','BAN_HANG','CRM_MAU'))""",
    # trigger cũ giữ NGUYÊN hàm; chỉ thêm WHEN loại trừ đúng đường G6A (đường G6A có guard riêng chặt hơn ở dưới)
    "DROP TRIGGER phien_ban_kiem_duyet ON master.hop_dong_phien_ban",
    """CREATE TRIGGER phien_ban_kiem_duyet BEFORE UPDATE ON master.hop_dong_phien_ban FOR EACH ROW
        WHEN (OLD.nguon IS DISTINCT FROM 'CRM_MAU' OR NEW.nguon IS DISTINCT FROM 'CRM_MAU') EXECUTE FUNCTION master.phien_ban_kiem_duyet()""",
    "DROP TRIGGER hop_dong_gk_kiem ON master.hop_dong",
    """CREATE TRIGGER hop_dong_gk_kiem BEFORE INSERT OR UPDATE ON master.hop_dong FOR EACH ROW
        WHEN (NEW.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC') EXECUTE FUNCTION master.hop_dong_gk_kiem()""",
    "DROP TRIGGER hop_dong_gk_ky_khoa ON master.hop_dong",
    """CREATE TRIGGER hop_dong_gk_ky_khoa BEFORE UPDATE ON master.hop_dong FOR EACH ROW
        WHEN (NOT (OLD.crm_giao_ket IS NOT DISTINCT FROM 'DA_KY' AND NEW.crm_giao_ket IS NOT DISTINCT FROM 'HIEU_LUC'))
        EXECUTE FUNCTION master.hop_dong_gk_ky_khoa()""",
    # ======================================================================= phạm vi kiểm (thin binding; không vai/IAM mới, không tự cấp)
    """CREATE TABLE master.crm_kiem_pham_vi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phan_cong_id uuid NOT NULL REFERENCES master.phan_cong_hanh_dong(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        hop_dong_id uuid NOT NULL,
        ky_id uuid NOT NULL,
        du_an_id uuid,
        cap_boi text NOT NULL,
        cap_luc timestamptz NOT NULL DEFAULT now(),
        thu_hoi_luc timestamptz,
        thu_hoi_boi text,
        thu_hoi_ly_do text,
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky (id, phap_nhan_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL) AND (thu_hoi_luc IS NULL) = (thu_hoi_ly_do IS NULL)))""",
    "CREATE UNIQUE INDEX crm_kiem_pham_vi_hien_hanh_uq ON master.crm_kiem_pham_vi (phan_cong_id, ky_id) WHERE thu_hoi_luc IS NULL",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_pham_vi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE a record; k record; s record; h record;
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_CHI_QUAN_TRI: phạm vi kiểm chỉ do quản trị (chủ CSDL) ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_BAT_BIEN: thu hồi bằng dấu thu hồi, không xóa' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.thu_hoi_luc IS NOT NULL OR NEW.thu_hoi_luc IS NULL OR coalesce(btrim(NEW.thu_hoi_ly_do), '') = ''
                   OR ROW(NEW.id, NEW.phan_cong_id, NEW.phap_nhan_id, NEW.hop_dong_id, NEW.ky_id, NEW.du_an_id, NEW.cap_boi, NEW.cap_luc)
                      IS DISTINCT FROM ROW(OLD.id, OLD.phan_cong_id, OLD.phap_nhan_id, OLD.hop_dong_id, OLD.ky_id, OLD.du_an_id, OLD.cap_boi, OLD.cap_luc) THEN
                    RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_BAT_BIEN: chỉ ghi dấu thu hồi một lần, không sửa phạm vi' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.thu_hoi_luc IS NOT NULL THEN
                RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_BAT_BIEN: không chèn phạm vi đã thu hồi' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO a FROM master.phan_cong_hanh_dong WHERE id = NEW.phan_cong_id;
            IF a.id IS NULL OR a.thu_hoi_luc IS NOT NULL OR a.phap_nhan_id <> NEW.phap_nhan_id OR a.module <> 'CRM' OR a.hanh_dong <> 'CRM_HD_KIEM' THEN
                RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_SAI: phạm vi phải gắn phân công CRM_HD_KIEM còn hiệu lực cùng pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = k.soan_id;
            SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF k.id IS NULL OR s.id IS NULL OR h.id IS NULL OR k.hop_dong_id <> NEW.hop_dong_id OR k.phap_nhan_id <> NEW.phap_nhan_id
               OR h.crm_giao_ket IS NULL OR (a.loai_hinh_id IS NOT NULL AND a.loai_hinh_id <> s.loai_hinh_id)
               OR NEW.du_an_id IS DISTINCT FROM h.du_an_id THEN
                RAISE EXCEPTION 'CRM_KIEM_PHAM_VI_SAI: phạm vi không khớp bản ký/HĐ/dự án hiện hành' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_pham_vi_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_pham_vi FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_pham_vi_kiem()",
    # ======================================================================= hồ sơ kiểm (một/bản ký) + revision KT + lần check
    """CREATE TABLE master.crm_kiem_ho_so (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        ky_id uuid NOT NULL UNIQUE,
        hop_dong_id uuid NOT NULL UNIQUE,
        trang_thai text NOT NULL CHECK (trang_thai IN ('DANG_KIEM','CHO_BO_SUNG','TRA_LAI_CHO_KY_LAI','HIEU_LUC')),
        revision integer NOT NULL CHECK (revision >= 0),
        viec_id uuid REFERENCES kho.viec_can_duyet(id),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky (id, phap_nhan_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        UNIQUE (id, ky_id),
        UNIQUE (id, phap_nhan_id))""",
    """CREATE TABLE master.crm_kiem_rev (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ho_so_id uuid NOT NULL,
        ky_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        checklist jsonb NOT NULL CHECK (jsonb_typeof(checklist) = 'object'),
        de_xuat_doi_tac_id uuid REFERENCES master.doi_tac(id),
        de_xuat_ma_junsky_id uuid REFERENCES master.doi_tac_ma_junsky(id),
        ngay_hieu_luc date,
        can_cu_ngay text CHECK (can_cu_ngay IS NULL OR can_cu_ngay IN ('DIEU_KHOAN_HD','TRUONG_HOP_DONG')),
        trich_dan_ngay text CHECK (trich_dan_ngay IS NULL OR (length(trich_dan_ngay) BETWEEN 1 AND 1000 AND btrim(trich_dan_ngay) <> ''
                                                              AND trich_dan_ngay !~ '[[:cntrl:]]')),
        ghi_chu text CHECK (ghi_chu IS NULL OR length(ghi_chu) <= 2000),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ho_so_id, ky_id) REFERENCES master.crm_kiem_ho_so (id, ky_id),
        UNIQUE (ho_so_id, revision),
        UNIQUE (id, ho_so_id),
        CHECK ((de_xuat_doi_tac_id IS NULL) = (de_xuat_ma_junsky_id IS NULL)),
        CHECK ((ngay_hieu_luc IS NULL) = (can_cu_ngay IS NULL) AND (ngay_hieu_luc IS NULL) = (trich_dan_ngay IS NULL)))""",
    "CREATE TRIGGER crm_kiem_rev_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_rev FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_rev_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ho record; j record; v_ky_dt text; v_hd_dt uuid;
        BEGIN
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            IF ho.id IS NULL OR ho.ky_id <> NEW.ky_id OR ho.phap_nhan_id <> NEW.phap_nhan_id OR ho.trang_thai NOT IN ('DANG_KIEM','CHO_BO_SUNG')
               OR NEW.revision <> ho.revision + 1 OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'CRM_KIEM_REV_SAI: revision kiểm phải nối tiếp hồ sơ đang kiểm/chờ bổ sung, do chính phiên ghi' USING ERRCODE = 'P0001';
            END IF;
            IF (SELECT array_agg(e ORDER BY e) FROM jsonb_object_keys(NEW.checklist) e) IS DISTINCT FROM """ + _KIEM_CHECKLIST + """
               OR EXISTS (SELECT 1 FROM jsonb_each(NEW.checklist) e
                          WHERE NOT (jsonb_typeof(e.value) = 'null' OR (jsonb_typeof(e.value) = 'string' AND e.value #>> '{}' IN ('XAC_NHAN','CO_VAN_DE')))) THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECKLIST_SAI: checklist phải đúng 5 mục, mỗi mục XAC_NHAN/CO_VAN_DE/null' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.de_xuat_ma_junsky_id IS NOT NULL THEN
                SELECT * INTO j FROM master.doi_tac_ma_junsky WHERE id = NEW.de_xuat_ma_junsky_id;
                IF j.id IS NULL OR j.doi_tac_id <> NEW.de_xuat_doi_tac_id OR j.phap_nhan_id <> NEW.phap_nhan_id OR j.valid_to IS NOT NULL OR j.dong THEN
                    RAISE EXCEPTION 'CRM_KIEM_JUNSKY_SAI: mã Junsky phải là mã CÓ SẴN, còn hiệu lực, đúng đối tác và pháp nhân (không tạo mã)' USING ERRCODE = 'P0001';
                END IF;
                -- P1-B: khách đã định danh (bản ký G4 hoặc HĐ master) KHÔNG bị thay; chỉ khách dự thảo (cả hai NULL) mới được KT chọn cặp có sẵn
                SELECT r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id', h.doi_tac_id INTO v_ky_dt, v_hd_dt
                    FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id JOIN master.hop_dong h ON h.id = k.hop_dong_id
                    WHERE k.id = NEW.ky_id;
                IF (v_ky_dt IS NOT NULL AND v_ky_dt <> NEW.de_xuat_doi_tac_id::text) OR (v_hd_dt IS NOT NULL AND v_hd_dt <> NEW.de_xuat_doi_tac_id) THEN
                    RAISE EXCEPTION 'CRM_KIEM_KHACH_DA_DINH: khách đã định danh trên bản ký/hợp đồng — không thay bằng đối tác khác' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_rev_kiem BEFORE INSERT ON master.crm_kiem_rev FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_rev_kiem()",
    """CREATE TABLE master.crm_kiem_check (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        ho_so_id uuid NOT NULL,
        ky_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        rev_id uuid NOT NULL,
        ho_so_revision integer NOT NULL CHECK (ho_so_revision >= 1),
        g5_che_do text NOT NULL CHECK (g5_che_do IN ('VAN_HANH','SYNTHETIC_FIXTURE')),
        do_thi jsonb NOT NULL CHECK (jsonb_typeof(do_thi) = 'object'),
        do_thi_sha256 text NOT NULL CHECK (do_thi_sha256 ~ '^[0-9a-f]{64}$'),
        chan jsonb NOT NULL,
        canh_bao jsonb NOT NULL CHECK (jsonb_typeof(canh_bao) = 'array'),
        ket_luan text NOT NULL CHECK (ket_luan IN ('DU_DIEU_KIEN','CHUA_DU_DIEU_KIEN')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ho_so_id, ky_id) REFERENCES master.crm_kiem_ho_so (id, ky_id),
        FOREIGN KEY (rev_id, ho_so_id) REFERENCES master.crm_kiem_rev (id, ho_so_id),
        UNIQUE (id, ky_id),
        CHECK (CASE WHEN jsonb_typeof(chan) = 'array' THEN (ket_luan = 'DU_DIEU_KIEN') = (jsonb_array_length(chan) = 0) ELSE false END))""",
    "CREATE TRIGGER crm_kiem_check_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_check FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # chèn lần check (kể cả SQL trực tiếp của chủ bảng): đánh giá lại TẠI CHỖ phải trùng từng byte đồ thị/chặn/kết luận đã ghi
    """CREATE OR REPLACE FUNCTION master.crm_kiem_check_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ho record; e jsonb;
        BEGIN
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            IF ho.id IS NULL OR ho.trang_thai <> 'DANG_KIEM' OR NEW.ho_so_revision <> ho.revision OR NEW.phap_nhan_id <> ho.phap_nhan_id
               OR NEW.rev_id IS DISTINCT FROM (SELECT r.id FROM master.crm_kiem_rev r WHERE r.ho_so_id = ho.id AND r.revision = ho.revision)
               OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECK_SAI: lần check phải gắn đúng revision hiện hành của hồ sơ đang kiểm' USING ERRCODE = 'P0001';
            END IF;
            e := master.crm_kiem_danh_gia(NEW.ky_id, NEW.g5_che_do);
            IF e ->> 'sha256' IS DISTINCT FROM NEW.do_thi_sha256 OR e -> 'do_thi' IS DISTINCT FROM NEW.do_thi OR e -> 'chan' IS DISTINCT FROM NEW.chan
               OR e -> 'canh_bao' IS DISTINCT FROM NEW.canh_bao OR e ->> 'ket_luan' IS DISTINCT FROM NEW.ket_luan THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECK_SAI: kết quả check không khớp đánh giá lại của máy chủ' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_check_kiem BEFORE INSERT ON master.crm_kiem_check FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_check_kiem()",
    # ======================================================================= G5 SYNTHETIC (chỉ fixture; KHÔNG producer/policy vận hành)
    """CREATE TABLE master.crm_kiem_g5_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ma text NOT NULL UNIQUE CHECK (ma ~ '^SYNTHETIC_[A-Z0-9_]{1,50}$'),
        loai text NOT NULL CHECK (loai = 'SYNTHETIC_FIXTURE'),
        phi_van_hanh boolean NOT NULL CHECK (phi_van_hanh),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE master.crm_kiem_g5_chinh_sach (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        nguon_id uuid NOT NULL REFERENCES master.crm_kiem_g5_nguon(id),
        loai text NOT NULL CHECK (loai = 'SYNTHETIC_FIXTURE'),
        mo_ta text NOT NULL CHECK (mo_ta LIKE 'SYNTHETIC%' AND length(mo_ta) <= 300),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE master.crm_kiem_g5_ket_qua (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thu_tu bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
        ky_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        nguon_id uuid NOT NULL REFERENCES master.crm_kiem_g5_nguon(id),
        ket_qua text NOT NULL CHECK (ket_qua IN ('KHOP','LECH','KHONG_CHON_MAU','CHUA_HOAN_TAT')),
        chinh_sach_id uuid REFERENCES master.crm_kiem_g5_chinh_sach(id),
        ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ '^[0-9a-f]{64}$'),
        g3_pdf_sha256 text NOT NULL CHECK (g3_pdf_sha256 ~ '^[0-9a-f]{64}$'),
        lech jsonb NOT NULL CHECK (jsonb_typeof(lech) = 'array'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky (id, phap_nhan_id),
        CHECK ((ket_qua = 'KHONG_CHON_MAU') = (chinh_sach_id IS NOT NULL)),
        CHECK ((ket_qua = 'LECH') = (jsonb_array_length(lech) > 0)))""",
    *(f"CREATE TRIGGER {t}_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.{t} FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()"
      for t in ("crm_kiem_g5_nguon", "crm_kiem_g5_chinh_sach", "crm_kiem_g5_ket_qua")),
    """CREATE OR REPLACE FUNCTION master.crm_kiem_g5_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE k record; c record;
        BEGIN
            IF current_setting('ktt.crm_kiem_g5', true) IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN
                RAISE EXCEPTION 'CRM_KIEM_G5_KHONG_PHAI_FIXTURE: bằng chứng G5 tổng hợp chỉ ghi trong giao dịch fixture kiểm thử (không phải vận hành)'
                    USING ERRCODE = 'P0001';
            END IF;
            IF TG_TABLE_NAME = 'crm_kiem_g5_ket_qua' THEN
                SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
                IF k.id IS NULL OR NEW.ky_pdf_sha256 <> k.ky_pdf_sha256 OR NEW.g3_pdf_sha256 <> k.g3_pdf_sha256 THEN
                    RAISE EXCEPTION 'CRM_KIEM_G5_SAI: kết quả G5 phải gắn đúng hash bản ký và bản xuất G3' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.ket_qua = 'KHONG_CHON_MAU' THEN
                    SELECT * INTO c FROM master.crm_kiem_g5_chinh_sach WHERE id = NEW.chinh_sach_id;
                    IF k.co_sua OR c.id IS NULL OR c.phap_nhan_id <> NEW.phap_nhan_id OR c.nguon_id <> NEW.nguon_id THEN
                        RAISE EXCEPTION 'CRM_KIEM_G5_SAI: không chọn mẫu chỉ khi khai Không sửa và có chính sách cùng pháp nhân/nguồn' USING ERRCODE = 'P0001';
                    END IF;
                END IF;
                IF EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.lech) e
                           WHERE jsonb_typeof(e) <> 'object' OR NOT coalesce((e ->> 'ma') ~ '^[A-Z0-9_]{1,60}$', false))
                   OR (SELECT count(DISTINCT e ->> 'ma') FROM jsonb_array_elements(NEW.lech) e) <> jsonb_array_length(NEW.lech) THEN
                    RAISE EXCEPTION 'CRM_KIEM_G5_SAI: mục lệch G5 phải có mã duy nhất hợp lệ' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    *(f"CREATE TRIGGER {t}_kiem BEFORE INSERT ON master.{t} FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_g5_kiem()"
      for t in ("crm_kiem_g5_nguon", "crm_kiem_g5_chinh_sach", "crm_kiem_g5_ket_qua")),
    # ======================================================================= xử lý lệch (KT quyết THEO BẢN KÝ — không sửa bản ký/G7)
    """CREATE TABLE master.crm_kiem_xu_ly_lech (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ky_id uuid NOT NULL,
        ho_so_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        ho_so_revision integer NOT NULL,
        loai text NOT NULL CHECK (loai IN ('G5_LECH','G7_LECH')),
        muc_tieu_id uuid NOT NULL,
        ma_lech text NOT NULL CHECK (ma_lech ~ '^[A-Z0-9_]{1,60}(:[0-9]{1,4})?$'),
        quyet_dinh text NOT NULL CHECK (quyet_dinh = 'THEO_BAN_KY'),
        ly_do text NOT NULL CHECK (length(ly_do) BETWEEN 1 AND 1000 AND btrim(ly_do) <> ''),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ho_so_id, ky_id) REFERENCES master.crm_kiem_ho_so (id, ky_id),
        UNIQUE (ky_id, loai, muc_tieu_id, ma_lech))""",
    "CREATE TRIGGER crm_kiem_xu_ly_lech_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_xu_ly_lech FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
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
                g := master.crm_kiem_g5_xet(NEW.ky_id, 'SYNTHETIC_FIXTURE');
                IF g ->> 'trang_thai' IS DISTINCT FROM 'LECH' OR g ->> 'ket_qua_id' IS DISTINCT FROM NEW.muc_tieu_id::text
                   OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(g -> 'lech') e WHERE e ->> 'khoa' = NEW.ma_lech) THEN
                    RAISE EXCEPTION 'CRM_KIEM_LECH_KHONG_CON: không có kết quả G5 LECH được đăng ký cho mục này' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_xu_ly_lech_kiem BEFORE INSERT ON master.crm_kiem_xu_ly_lech FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_xu_ly_lech_kiem()",
    # ======================================================================= quyết định KT (HIEU_LUC | BO_SUNG | TRA_LAI) + hoàn tất kích hoạt
    """CREATE TABLE master.crm_kiem_quyet_dinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ky_id uuid NOT NULL,
        ho_so_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN ('HIEU_LUC','BO_SUNG','TRA_LAI')),
        ho_so_revision integer NOT NULL CHECK (ho_so_revision >= 0),
        check_id uuid,
        rev_id uuid,
        g5_che_do text CHECK (g5_che_do IS NULL OR g5_che_do IN ('VAN_HANH','SYNTHETIC_FIXTURE')),
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        ma_junsky_id uuid REFERENCES master.doi_tac_ma_junsky(id),
        ngay_hieu_luc date,
        do_thi_sha256 text CHECK (do_thi_sha256 IS NULL OR do_thi_sha256 ~ '^[0-9a-f]{64}$'),
        ly_do text CHECK (ly_do IS NULL OR (length(ly_do) BETWEEN 1 AND 1000 AND btrim(ly_do) <> '')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        tao_txid bigint NOT NULL DEFAULT txid_current(),
        FOREIGN KEY (ho_so_id, ky_id) REFERENCES master.crm_kiem_ho_so (id, ky_id),
        FOREIGN KEY (check_id, ky_id) REFERENCES master.crm_kiem_check (id, ky_id),
        FOREIGN KEY (rev_id, ho_so_id) REFERENCES master.crm_kiem_rev (id, ho_so_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        CHECK (CASE WHEN loai = 'HIEU_LUC' THEN check_id IS NOT NULL AND rev_id IS NOT NULL AND g5_che_do IS NOT NULL AND doi_tac_id IS NOT NULL
                                               AND ma_junsky_id IS NOT NULL AND ngay_hieu_luc IS NOT NULL AND do_thi_sha256 IS NOT NULL AND ly_do IS NULL
                    ELSE ly_do IS NOT NULL AND check_id IS NULL AND g5_che_do IS NULL AND doi_tac_id IS NULL AND ma_junsky_id IS NULL
                         AND ngay_hieu_luc IS NULL AND do_thi_sha256 IS NULL END))""",
    "CREATE UNIQUE INDEX crm_kiem_quyet_dinh_hieu_luc_uq ON master.crm_kiem_quyet_dinh (ky_id) WHERE loai = 'HIEU_LUC'",
    "CREATE UNIQUE INDEX crm_kiem_quyet_dinh_tra_lai_uq ON master.crm_kiem_quyet_dinh (ky_id) WHERE loai = 'TRA_LAI'",
    "CREATE TRIGGER crm_kiem_quyet_dinh_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_quyet_dinh FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # chèn quyết định (kể cả SQL trực tiếp chủ bảng): quyền hiện hành + KHÁC người ký + trạng thái + (HIEU_LUC) check mới nhất đủ điều kiện và
    # đánh giá lại tại chỗ trùng sha đã duyệt — không có đường "quyết định trước, kiểm sau"
    """CREATE OR REPLACE FUNCTION master.crm_kiem_quyet_dinh_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ho record; c record; rv record; e jsonb;
        BEGIN
            PERFORM master.crm_kiem_dich(NEW.ky_id, true);
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            IF ho.id IS NULL OR ho.ky_id <> NEW.ky_id OR ho.hop_dong_id <> NEW.hop_dong_id OR ho.phap_nhan_id <> NEW.phap_nhan_id
               OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() OR NEW.tao_txid IS DISTINCT FROM txid_current()
               OR NEW.ho_so_revision <> ho.revision THEN
                RAISE EXCEPTION 'CRM_KIEM_QUYET_DINH_SAI: quyết định phải gắn đúng hồ sơ/revision hiện hành, do chính phiên ghi trong giao dịch này'
                    USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai = 'TRA_LAI' THEN
                IF ho.trang_thai NOT IN ('DANG_KIEM','CHO_BO_SUNG') THEN
                    RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chỉ trả lại hồ sơ đang kiểm/chờ bổ sung' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ho.trang_thai <> 'DANG_KIEM' THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chỉ quyết định khi hồ sơ đang kiểm' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai = 'BO_SUNG' THEN
                RETURN NEW;
            END IF;
            SELECT * INTO c FROM master.crm_kiem_check WHERE id = NEW.check_id;
            SELECT * INTO rv FROM master.crm_kiem_rev WHERE id = NEW.rev_id;
            IF c.id IS NULL OR c.ky_id <> NEW.ky_id OR c.ho_so_revision <> ho.revision OR c.rev_id <> NEW.rev_id OR c.ket_luan <> 'DU_DIEU_KIEN'
               OR c.do_thi_sha256 <> NEW.do_thi_sha256 OR c.g5_che_do <> NEW.g5_che_do
               OR EXISTS (SELECT 1 FROM master.crm_kiem_check c2 WHERE c2.ho_so_id = ho.id AND c2.thu_tu > c.thu_tu)
               OR rv.id IS NULL OR rv.revision <> ho.revision OR NEW.doi_tac_id IS DISTINCT FROM rv.de_xuat_doi_tac_id
               OR NEW.ma_junsky_id IS DISTINCT FROM rv.de_xuat_ma_junsky_id OR NEW.ngay_hieu_luc IS DISTINCT FROM rv.ngay_hieu_luc THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECK_CU: quyết định hiệu lực phải theo lần check mới nhất đủ điều kiện của revision hiện hành' USING ERRCODE = 'P0001';
            END IF;
            e := master.crm_kiem_danh_gia(NEW.ky_id, NEW.g5_che_do);
            IF e ->> 'ket_luan' IS DISTINCT FROM 'DU_DIEU_KIEN' OR e ->> 'sha256' IS DISTINCT FROM NEW.do_thi_sha256 THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECK_CU: căn cứ đã đổi sau lần check (đánh giá lại không còn trùng) — chạy check lại' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_quyet_dinh_kiem BEFORE INSERT ON master.crm_kiem_quyet_dinh FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_quyet_dinh_kiem()",
    """CREATE TABLE master.crm_kiem_hieu_luc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        quyet_dinh_id uuid NOT NULL UNIQUE REFERENCES master.crm_kiem_quyet_dinh(id),
        ky_id uuid NOT NULL UNIQUE,
        ho_so_id uuid NOT NULL UNIQUE,
        hop_dong_id uuid NOT NULL UNIQUE,
        phien_ban_id uuid NOT NULL UNIQUE REFERENCES master.hop_dong_phien_ban(id),
        chung_tu_id uuid NOT NULL UNIQUE REFERENCES kho.chung_tu(id),
        so_dong_lich integer NOT NULL CHECK (so_dong_lich >= 1),
        so_tham_so integer NOT NULL CHECK (so_tham_so >= 1),
        tong_minor bigint NOT NULL CHECK (tong_minor > 0),
        tien_te char(3) NOT NULL,
        g7_trang_thai text NOT NULL CHECK (g7_trang_thai IN ('KHONG_AP_DUNG','KHOP','LECH')),
        g5_che_do text NOT NULL CHECK (g5_che_do IN ('VAN_HANH','SYNTHETIC_FIXTURE')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ho_so_id, ky_id) REFERENCES master.crm_kiem_ho_so (id, ky_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id))""",
    "CREATE TRIGGER crm_kiem_hieu_luc_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_hieu_luc FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # dòng hoàn tất: kiểm lại TOÀN BỘ hồ sơ pháp lý đã ghi trong giao dịch (EXCEPT hai chiều lịch + tham số so với tính lại từ bản ký)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_hieu_luc_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE q record; k record; h record; p record; ct record; ho record; l jsonb; n integer;
        BEGIN
            SELECT * INTO q FROM master.crm_kiem_quyet_dinh WHERE id = NEW.quyet_dinh_id;
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
            SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            SELECT * INTO p FROM master.hop_dong_phien_ban WHERE id = NEW.phien_ban_id;
            SELECT * INTO ct FROM kho.chung_tu WHERE id = NEW.chung_tu_id;
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            l := master.crm_kiem_lich_ky(NEW.ky_id);
            IF q.id IS NULL OR q.loai <> 'HIEU_LUC' OR q.tao_txid <> txid_current() OR q.ky_id <> NEW.ky_id OR q.ho_so_id <> NEW.ho_so_id
               OR k.id IS NULL OR k.hop_dong_id <> NEW.hop_dong_id OR ho.trang_thai <> 'DANG_KIEM' OR NEW.tao_boi IS DISTINCT FROM q.tao_boi
               OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() OR NEW.g5_che_do <> q.g5_che_do
               OR h.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC' OR h.phien_ban_hien_hanh IS DISTINCT FROM p.id OR h.doi_tac_id IS DISTINCT FROM q.doi_tac_id
               OR h.ngay_ky IS DISTINCT FROM k.ngay_ky OR h.gia_tri_minor IS DISTINCT FROM NEW.tong_minor OR h.tien_te IS DISTINCT FROM NEW.tien_te
               OR p.hop_dong_id <> h.id OR p.nguon <> 'CRM_MAU' OR p.trang_thai <> 'DA_DUYET' OR p.phien_ban <> 1 OR p.loai <> 'GOC'
               OR p.chung_tu_id IS DISTINCT FROM ct.id OR p.ngay_hieu_luc IS DISTINCT FROM q.ngay_hieu_luc OR p.kiem_boi IS DISTINCT FROM q.tao_boi
               OR p.nguoi_duyet IS DISTINCT FROM q.tao_boi OR p.tham_so -> 'crm_g6a' ->> 'quyet_dinh_id' IS DISTINCT FROM q.id::text
               OR (SELECT count(*) FROM master.hop_dong_phien_ban p2 WHERE p2.hop_dong_id = h.id) <> 1
               OR ct.id IS NULL OR ct.phap_nhan_id <> NEW.phap_nhan_id OR ct.loai <> 'HOP_DONG_TEP' OR ct.khoa_nguon <> 'CRM_G6A:' || k.id::text
               OR ct.hash <> k.ky_pdf_sha256
               OR (l ->> 'tong_minor')::bigint IS DISTINCT FROM NEW.tong_minor OR l ->> 'tien_te' IS DISTINCT FROM NEW.tien_te::text
               OR master.crm_kiem_g7(NEW.ky_id) ->> 'trang_thai' IS DISTINCT FROM NEW.g7_trang_thai THEN
                RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: hồ sơ pháp lý kích hoạt không khớp quyết định/bản ký' USING ERRCODE = 'P0001';
            END IF;
            SELECT count(*) INTO n FROM (
                (SELECT x.dot, x.moc, x.ty_le, x.so_tien_minor, x.tien_te::text AS tt, x.han, x.loai, x.khoa_nghia_vu
                   FROM master.lich_thu x WHERE x.phien_ban_id = p.id
                 EXCEPT
                 SELECT (e ->> 'dot')::integer, e ->> 'moc', (e ->> 'ty_le')::numeric, (e ->> 'so_tien_minor')::bigint, l ->> 'tien_te',
                        (e ->> 'han')::date, 'DOT', 'CRM-DOT-' || (e ->> 'dot') FROM jsonb_array_elements(l -> 'dong') e)
                UNION ALL
                (SELECT (e ->> 'dot')::integer, e ->> 'moc', (e ->> 'ty_le')::numeric, (e ->> 'so_tien_minor')::bigint, l ->> 'tien_te',
                        (e ->> 'han')::date, 'DOT', 'CRM-DOT-' || (e ->> 'dot') FROM jsonb_array_elements(l -> 'dong') e
                 EXCEPT
                 SELECT x.dot, x.moc, x.ty_le, x.so_tien_minor, x.tien_te::text, x.han, x.loai, x.khoa_nghia_vu
                   FROM master.lich_thu x WHERE x.phien_ban_id = p.id)) z;
            IF n <> 0 OR NEW.so_dong_lich <> (SELECT count(*) FROM master.lich_thu x WHERE x.phien_ban_id = p.id)
               OR NEW.so_dong_lich <> jsonb_array_length(l -> 'dong')
               OR NEW.tong_minor <> (SELECT sum(x.so_tien_minor) FROM master.lich_thu x WHERE x.phien_ban_id = p.id) THEN
                RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: lịch thu không trùng lịch tính lại từ bản ký' USING ERRCODE = 'P0001';
            END IF;
            SELECT count(*) INTO n FROM (
                (SELECT t.ten, t.gia_tri, t.gia_tri_typed, t.trang_thai_can_cu, t.trich_dan, t.ma_nguon
                   FROM master.hop_dong_tham_so t WHERE t.phien_ban_id = p.id
                 EXCEPT
                 SELECT f.ten, f.gia_tri, f.gia_tri_typed, f.trang_thai_can_cu, f.trich_dan, f.ma_nguon FROM master.crm_kiem_tham_so_ky(NEW.ky_id, q.rev_id) f)
                UNION ALL
                (SELECT f.ten, f.gia_tri, f.gia_tri_typed, f.trang_thai_can_cu, f.trich_dan, f.ma_nguon FROM master.crm_kiem_tham_so_ky(NEW.ky_id, q.rev_id) f
                 EXCEPT
                 SELECT t.ten, t.gia_tri, t.gia_tri_typed, t.trang_thai_can_cu, t.trich_dan, t.ma_nguon
                   FROM master.hop_dong_tham_so t WHERE t.phien_ban_id = p.id)) z;
            IF n <> 0 OR NEW.so_tham_so <> (SELECT count(*) FROM master.hop_dong_tham_so t WHERE t.phien_ban_id = p.id) THEN
                RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: tham số không trùng tham số tính lại từ bản ký' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_hieu_luc_kiem BEFORE INSERT ON master.crm_kiem_hieu_luc FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_hieu_luc_kiem()",
    # cuối giao dịch: quyết định phải đi kèm đúng hệ quả (không quyết định "treo")
    """CREATE OR REPLACE FUNCTION master.crm_kiem_quyet_dinh_hoan_tat() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE ho record; x record; h record;
        BEGIN
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.ho_so_id;
            IF NEW.loai = 'HIEU_LUC' THEN
                SELECT * INTO x FROM master.crm_kiem_hieu_luc WHERE quyet_dinh_id = NEW.id;
                SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
                IF x.id IS NULL OR ho.trang_thai <> 'HIEU_LUC' OR h.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC' OR h.phien_ban_hien_hanh IS DISTINCT FROM x.phien_ban_id
                   OR (x.g7_trang_thai = 'LECH' AND NOT EXISTS (SELECT 1 FROM kho.viec_can_duyet v WHERE v.tham_chieu_bang = 'master.crm_kiem_hieu_luc'
                                                                AND v.tham_chieu_id = x.id AND v.loai = 'V8')) THEN
                    RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: quyết định hiệu lực thiếu hồ sơ pháp lý/trạng thái/việc CFO đi kèm' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.loai = 'BO_SUNG' AND ho.trang_thai NOT IN ('CHO_BO_SUNG','TRA_LAI_CHO_KY_LAI') THEN
                RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: yêu cầu bổ sung phải chuyển hồ sơ sang Chờ bổ sung' USING ERRCODE = 'P0001';
            ELSIF NEW.loai = 'TRA_LAI' AND ho.trang_thai <> 'TRA_LAI_CHO_KY_LAI' THEN
                RAISE EXCEPTION 'CRM_KIEM_HOAN_TAT_SAI: trả lại phải chuyển hồ sơ sang Trả lại — chờ ký lại' USING ERRCODE = 'P0001';
            END IF;
            RETURN NULL;
        END $$""",
    """CREATE CONSTRAINT TRIGGER crm_kiem_quyet_dinh_hoan_tat AFTER INSERT ON master.crm_kiem_quyet_dinh DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_quyet_dinh_hoan_tat()""",
    # hồ sơ kiểm: chủ bảng; không xóa; trạng thái chuyển chỉ khi có quyết định cùng giao dịch; cuối (HIEU_LUC/TRA_LAI) bất biến
    """CREATE OR REPLACE FUNCTION master.crm_kiem_ho_so_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE k record; h record;
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: hồ sơ kiểm chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_KIEM_BAT_BIEN: không xóa hồ sơ kiểm' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
                SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
                IF NEW.trang_thai <> 'DANG_KIEM' OR NEW.revision <> 0 OR NEW.viec_id IS NOT NULL OR k.id IS NULL OR k.hop_dong_id <> NEW.hop_dong_id
                   OR k.phap_nhan_id <> NEW.phap_nhan_id OR h.crm_giao_ket IS DISTINCT FROM 'DA_KY' OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() THEN
                    RAISE EXCEPTION 'CRM_KIEM_HO_SO_SAI: hồ sơ kiểm mở ở DANG_KIEM revision 0 cho đúng bản ký của HĐ đã ký' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.ky_id, NEW.hop_dong_id, NEW.tao_boi, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.ky_id, OLD.hop_dong_id, OLD.tao_boi, OLD.tao_luc)
               OR OLD.trang_thai IN ('HIEU_LUC','TRA_LAI_CHO_KY_LAI')
               OR (OLD.viec_id IS NOT NULL AND NEW.viec_id IS DISTINCT FROM OLD.viec_id) THEN
                RAISE EXCEPTION 'CRM_KIEM_BAT_BIEN: hồ sơ kiểm đã chốt hoặc đổi định danh' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.revision <> OLD.revision AND (NEW.revision <> OLD.revision + 1 OR NEW.trang_thai <> 'DANG_KIEM'
                   OR NOT EXISTS (SELECT 1 FROM master.crm_kiem_rev r WHERE r.ho_so_id = NEW.id AND r.revision = NEW.revision)) THEN
                RAISE EXCEPTION 'CRM_KIEM_HO_SO_SAI: revision chỉ tăng 1 khi đã ghi revision kiểm tương ứng' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.trang_thai IS DISTINCT FROM OLD.trang_thai AND NOT CASE NEW.trang_thai
                    WHEN 'CHO_BO_SUNG' THEN OLD.trang_thai = 'DANG_KIEM' AND NEW.revision = OLD.revision
                         AND """ + _KIEM_TXID.format(hd="NEW.hop_dong_id", loai="'BO_SUNG'") + """ IS NOT NULL
                    WHEN 'TRA_LAI_CHO_KY_LAI' THEN NEW.revision = OLD.revision
                         AND EXISTS (SELECT 1 FROM master.crm_kiem_quyet_dinh q0 WHERE q0.hop_dong_id = NEW.hop_dong_id AND q0.loai = 'TRA_LAI'
                                     AND q0.tao_txid = txid_current())
                    WHEN 'HIEU_LUC' THEN OLD.trang_thai = 'DANG_KIEM' AND NEW.revision = OLD.revision
                         AND EXISTS (SELECT 1 FROM master.crm_kiem_quyet_dinh q0 JOIN master.crm_kiem_hieu_luc x ON x.quyet_dinh_id = q0.id
                                     WHERE q0.hop_dong_id = NEW.hop_dong_id AND q0.loai = 'HIEU_LUC' AND q0.tao_txid = txid_current())
                    WHEN 'DANG_KIEM' THEN OLD.trang_thai = 'CHO_BO_SUNG' AND NEW.revision = OLD.revision + 1
                    ELSE false END THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chuyển trạng thái hồ sơ kiểm không hợp lệ (% → %)', OLD.trang_thai, NEW.trang_thai USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_ho_so_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_kiem_ho_so FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_ho_so_kiem()",
    # ======================================================================= guard bảng pháp lý (cùng bất biến cho mọi đường ghi)
    # HĐ: chèn HIEU_LUC cấm; DA_KY→HIEU_LUC chỉ theo quyết định cùng giao dịch (khách/ngày ký/giá trị từ bản ký, phần còn lại giữ nguyên);
    # HIEU_LUC: chỉ gắn con trỏ NULL → phiên bản CRM_MAU đã duyệt trước dòng hoàn tất; ngoài ra bất biến
    """CREATE OR REPLACE FUNCTION master.crm_kiem_hd_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE q record; k record; l jsonb;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.crm_giao_ket IS NOT DISTINCT FROM 'HIEU_LUC' THEN
                    RAISE EXCEPTION 'CRM_KIEM_HD_BAT_BIEN: không chèn hợp đồng ở HIEU_LUC' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC' AND NEW.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC' THEN
                RETURN NEW;
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: hợp đồng CRM hiệu lực chỉ ghi qua lệnh G6A trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.crm_giao_ket IS NOT DISTINCT FROM 'DA_KY' THEN
                SELECT * INTO q FROM master.crm_kiem_quyet_dinh WHERE hop_dong_id = NEW.id AND loai = 'HIEU_LUC' AND tao_txid = txid_current();
                SELECT * INTO k FROM master.crm_hd_ky WHERE hop_dong_id = NEW.id;
                l := master.crm_kiem_lich_ky(k.id);
                IF q.id IS NULL OR k.id IS NULL OR q.ky_id <> k.id OR NEW.trang_thai IS DISTINCT FROM 'HIEU_LUC'
                   OR NEW.doi_tac_id IS DISTINCT FROM q.doi_tac_id OR (OLD.doi_tac_id IS NOT NULL AND OLD.doi_tac_id <> q.doi_tac_id)
                   OR NEW.ngay_ky IS DISTINCT FROM k.ngay_ky OR NEW.gia_tri_minor IS DISTINCT FROM (l ->> 'tong_minor')::bigint
                   OR NEW.tien_te::text IS DISTINCT FROM l ->> 'tien_te' OR NEW.phien_ban_hien_hanh IS NOT NULL OR NEW.module_chu IS NOT NULL
                   OR (to_jsonb(NEW) - ARRAY['trang_thai','crm_giao_ket','doi_tac_id','ngay_ky','gia_tri_minor','tien_te'])
                      IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['trang_thai','crm_giao_ket','doi_tac_id','ngay_ky','gia_tri_minor','tien_te']) THEN
                    RAISE EXCEPTION 'CRM_KIEM_HD_KICH_HOAT_SAI: chỉ kích hoạt theo quyết định hiệu lực cùng giao dịch, đúng dữ liệu bản ký' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.crm_giao_ket IS NOT DISTINCT FROM 'HIEU_LUC' THEN
                IF NEW IS NOT DISTINCT FROM OLD THEN
                    RETURN NEW;
                END IF;
                IF NEW.crm_giao_ket IS NOT DISTINCT FROM 'HIEU_LUC' AND OLD.phien_ban_hien_hanh IS NULL AND NEW.phien_ban_hien_hanh IS NOT NULL
                   AND (to_jsonb(NEW) - 'phien_ban_hien_hanh') = (to_jsonb(OLD) - 'phien_ban_hien_hanh')
                   AND EXISTS (SELECT 1 FROM master.hop_dong_phien_ban p WHERE p.id = NEW.phien_ban_hien_hanh AND p.hop_dong_id = NEW.id
                               AND p.nguon = 'CRM_MAU' AND p.trang_thai = 'DA_DUYET')
                   AND """ + _KIEM_TXID.format(hd="NEW.id", loai="'HIEU_LUC'") + """ IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM master.crm_kiem_hieu_luc x WHERE x.hop_dong_id = NEW.id) THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'CRM_KIEM_HD_BAT_BIEN: hợp đồng CRM đã hiệu lực — không sửa/mở lại (phụ lục/thay thế chờ gói kế tiếp)' USING ERRCODE = 'P0001';
            END IF;
            RAISE EXCEPTION 'CRM_KIEM_HD_KICH_HOAT_SAI: chỉ chuyển HIEU_LUC từ DA_KY' USING ERRCODE = 'P0001';
        END $$""",
    "CREATE TRIGGER hop_dong_crm_kiem BEFORE INSERT OR UPDATE ON master.hop_dong FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_hd_kiem()",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_pb_chen() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE h record; q record;
        BEGIN
            SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF NEW.nguon IS DISTINCT FROM 'CRM_MAU' THEN
                IF h.crm_giao_ket IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_KIEM_PB_CHI_MAU: hợp đồng soạn từ mẫu chỉ nhận phiên bản CRM_MAU do G6A ghi' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT master.la_chu_bang('master.hop_dong'::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: phiên bản CRM_MAU chỉ ghi qua lệnh G6A trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO q FROM master.crm_kiem_quyet_dinh WHERE hop_dong_id = NEW.hop_dong_id AND loai = 'HIEU_LUC' AND tao_txid = txid_current();
            IF q.id IS NULL OR h.crm_giao_ket IS DISTINCT FROM 'HIEU_LUC' OR h.phien_ban_hien_hanh IS NOT NULL
               OR EXISTS (SELECT 1 FROM master.hop_dong_phien_ban p WHERE p.hop_dong_id = NEW.hop_dong_id)
               OR NEW.phien_ban <> 1 OR NEW.loai <> 'GOC' OR NEW.so_phu_luc IS NOT NULL OR NEW.thay_cho_id IS NOT NULL OR NEW.valid_to IS NOT NULL
               OR NEW.tao_boi IS DISTINCT FROM master.ktt_danh_tinh() OR NEW.tao_boi IS DISTINCT FROM q.tao_boi
               OR NEW.ngay_hieu_luc IS DISTINCT FROM q.ngay_hieu_luc OR NEW.valid_from IS DISTINCT FROM (q.ngay_hieu_luc::timestamp AT TIME ZONE 'UTC')
               OR NEW.loai_hinh_dt_id IS DISTINCT FROM h.loai_hinh_dt_id
               OR NEW.chung_tu_id IS NULL OR NEW.chung_tu_id IS DISTINCT FROM (SELECT c.id FROM kho.chung_tu c WHERE c.phap_nhan_id = h.phap_nhan_id
                                                                                AND c.loai = 'HOP_DONG_TEP' AND c.khoa_nguon = 'CRM_G6A:' || q.ky_id::text)
               OR NEW.tham_so -> 'crm_g6a' ->> 'quyet_dinh_id' IS DISTINCT FROM q.id::text THEN
                RAISE EXCEPTION 'CRM_KIEM_PB_SAI: phiên bản CRM_MAU chỉ là v1 GOC duy nhất theo quyết định hiệu lực cùng giao dịch' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_pb_chen BEFORE INSERT ON master.hop_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_pb_chen()",
    # duyệt phiên bản CRM_MAU: chỉ CHO_DUYET→DA_DUYET một lần, nội dung giữ nguyên, kiểm = duyệt = KT của quyết định (vai + action + phạm vi hiện hành),
    # vân tay khớp; sau đó bất biến (kể cả valid_to — thay thế/phụ lục là phụ thuộc gói kế tiếp)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_pb_sua() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE q record; pn uuid; ai text := master.ktt_danh_tinh();
        BEGIN
            IF NOT master.la_chu_bang('master.hop_dong'::regclass) OR OLD.nguon IS DISTINCT FROM 'CRM_MAU' OR NEW.nguon IS DISTINCT FROM 'CRM_MAU'
               OR OLD.trang_thai <> 'CHO_DUYET' OR NEW.trang_thai <> 'DA_DUYET'
               OR ROW(NEW.id, NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.so_phu_luc, NEW.ngay, NEW.tham_so, NEW.tep_goc_id, NEW.thay_cho_id,
                      NEW.ngay_hieu_luc, NEW.chung_tu_id, NEW.loai_hinh_dt_id, NEW.ly_do, NEW.tao_boi, NEW.tao_luc, NEW.valid_from, NEW.valid_to)
                  IS DISTINCT FROM ROW(OLD.id, OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.so_phu_luc, OLD.ngay, OLD.tham_so, OLD.tep_goc_id, OLD.thay_cho_id,
                      OLD.ngay_hieu_luc, OLD.chung_tu_id, OLD.loai_hinh_dt_id, OLD.ly_do, OLD.tao_boi, OLD.tao_luc, OLD.valid_from, OLD.valid_to) THEN
                RAISE EXCEPTION 'CRM_KIEM_PB_BAT_BIEN: phiên bản CRM_MAU chỉ duyệt một lần trong lệnh G6A, sau đó bất biến' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO q FROM master.crm_kiem_quyet_dinh WHERE hop_dong_id = NEW.hop_dong_id AND loai = 'HIEU_LUC' AND tao_txid = txid_current();
            SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF q.id IS NULL OR ai IS NULL OR ai IS DISTINCT FROM q.tao_boi OR NEW.kiem_boi IS DISTINCT FROM ai OR NEW.nguoi_duyet IS DISTINCT FROM ai
               OR NEW.kiem_luc IS DISTINCT FROM now() OR NEW.duyet_luc IS DISTINCT FROM now() OR NEW.valid_to IS NOT NULL
               OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id)
               OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
               OR NOT master.ktt_hanh_dong_duoc(pn, 'CRM', 'CRM_HD_KIEM', (SELECT s.loai_hinh_id FROM master.crm_hd_ky k JOIN master.crm_hd_soan s ON s.id = k.soan_id
                                                                         WHERE k.id = q.ky_id))
               OR NOT master.crm_kiem_pham_vi_duoc(q.ky_id)
               OR EXISTS (SELECT 1 FROM master.crm_kiem_hieu_luc x WHERE x.hop_dong_id = NEW.hop_dong_id) THEN
                RAISE EXCEPTION 'CRM_KIEM_PB_DUYET_SAI: kiểm/duyệt CRM_MAU phải là KT của quyết định, có quyền + phạm vi hiện hành, vân tay khớp'
                    USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE TRIGGER crm_kiem_pb_sua BEFORE UPDATE ON master.hop_dong_phien_ban FOR EACH ROW
        WHEN (OLD.nguon IS NOT DISTINCT FROM 'CRM_MAU' OR NEW.nguon IS NOT DISTINCT FROM 'CRM_MAU') EXECUTE FUNCTION master.crm_kiem_pb_sua()""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_tham_so_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE p record;
        BEGIN
            SELECT pb.nguon, pb.hop_dong_id INTO p FROM master.hop_dong_phien_ban pb WHERE pb.id = coalesce(NEW.phien_ban_id, OLD.phien_ban_id);
            IF p.nguon IS DISTINCT FROM 'CRM_MAU' AND (TG_OP <> 'UPDATE' OR NOT EXISTS (SELECT 1 FROM master.hop_dong_phien_ban pb
                                                                                        WHERE pb.id = OLD.phien_ban_id AND pb.nguon = 'CRM_MAU')) THEN
                RETURN coalesce(NEW, OLD);
            END IF;
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'CRM_KIEM_THAM_SO_BAT_BIEN: tham số CRM_MAU chỉ ghi một lần khi kích hoạt' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang('master.hop_dong'::regclass) OR NEW.nguon IS DISTINCT FROM 'CRM_MAU'
               OR """ + _KIEM_TXID.format(hd="p.hop_dong_id", loai="'HIEU_LUC'") + """ IS NULL
               OR EXISTS (SELECT 1 FROM master.crm_kiem_hieu_luc x WHERE x.hop_dong_id = p.hop_dong_id) THEN
                RAISE EXCEPTION 'CRM_KIEM_THAM_SO_SAI: tham số CRM_MAU chỉ ghi trong lệnh kích hoạt G6A' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_tham_so_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.hop_dong_tham_so FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_tham_so_kiem()",
    # lịch: chèn chỉ trong lệnh kích hoạt (guard cũ vẫn buộc DA_DUYET + duyet_luc = now()); cập nhật trạng thái thu (F7) giữ guard cũ
    """CREATE OR REPLACE FUNCTION master.crm_kiem_lich_thu_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE p record;
        BEGIN
            SELECT pb.nguon, pb.hop_dong_id INTO p FROM master.hop_dong_phien_ban pb WHERE pb.id = NEW.phien_ban_id;
            IF p.nguon IS DISTINCT FROM 'CRM_MAU' THEN
                RETURN NEW;
            END IF;
            IF NOT master.la_chu_bang('master.hop_dong'::regclass)
               OR """ + _KIEM_TXID.format(hd="p.hop_dong_id", loai="'HIEU_LUC'") + """ IS NULL
               OR EXISTS (SELECT 1 FROM master.crm_kiem_hieu_luc x WHERE x.hop_dong_id = p.hop_dong_id)
               OR NEW.loai <> 'DOT' OR NEW.thay_cho_id IS NOT NULL OR NEW.co_so IS DISTINCT FROM 'CRM_MAU:BAN_KY'
               OR NEW.khoa_nghia_vu IS DISTINCT FROM 'CRM-DOT-' || NEW.dot::text THEN
                RAISE EXCEPTION 'CRM_KIEM_LICH_SAI: lịch thu CRM_MAU chỉ sinh trong lệnh kích hoạt G6A' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_lich_thu_kiem BEFORE INSERT ON master.lich_thu FOR EACH ROW EXECUTE FUNCTION master.crm_kiem_lich_thu_kiem()",
    # ======================================================================= quyền hiện hành (không vai mới; không suy từ người tạo; không đọc rộng)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_pham_vi_duoc(p_ky uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (
            SELECT 1
            FROM master.crm_hd_ky k
            JOIN master.hop_dong h ON h.id = k.hop_dong_id AND h.phap_nhan_id = k.phap_nhan_id
            JOIN master.crm_hd_soan s ON s.id = k.soan_id
            JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id
            JOIN master.crm_kiem_pham_vi b ON b.ky_id = k.id AND b.hop_dong_id = h.id AND b.phap_nhan_id = k.phap_nhan_id AND b.thu_hoi_luc IS NULL
            JOIN master.phan_cong_hanh_dong a ON a.id = b.phan_cong_id AND a.thu_hoi_luc IS NULL AND a.phap_nhan_id = k.phap_nhan_id
                 AND a.module = 'CRM' AND a.hanh_dong = 'CRM_HD_KIEM' AND (a.loai_hinh_id IS NULL OR a.loai_hinh_id = s.loai_hinh_id)
            JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id AND n.trang_thai = 'HOAT_DONG'
            WHERE k.id = p_ky
              AND n.dang_nhap = master.ktt_danh_tinh()
              AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
              AND master.ktt_duoc(k.phap_nhan_id, 'CRM')
              AND master.ktt_co_vai(k.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
              AND b.du_an_id IS NOT DISTINCT FROM h.du_an_id
              AND b.du_an_id::text IS NOT DISTINCT FROM nullif(r.du_lieu -> 'bao_gia' ->> 'du_an_id', '')
              AND (h.doi_tac_id IS NULL
                   OR h.doi_tac_id::text IS NOT DISTINCT FROM (r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id')
                   OR EXISTS (SELECT 1 FROM master.crm_kiem_quyet_dinh q WHERE q.ky_id = k.id AND q.loai = 'HIEU_LUC' AND q.doi_tac_id = h.doi_tac_id)))
        $$""",
    # đích + quyền: ngoài PN/module/vai KT → 404 ẩn; thiếu action → 403; thiếu/cũ/thu hồi phạm vi → 403; lệnh do chính người ký → 403 (tách nhiệm)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_dich(p_ky uuid, p_lenh boolean, OUT pn uuid)
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE k record; lh uuid;
        BEGIN
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NULL OR NOT master.ktt_duoc(k.phap_nhan_id, 'CRM') OR NOT master.ktt_co_vai(k.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản ký (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            SELECT s.loai_hinh_id INTO lh FROM master.crm_hd_soan s WHERE s.id = k.soan_id;
            IF NOT master.ktt_hanh_dong_duoc(k.phap_nhan_id, 'CRM', 'CRM_HD_KIEM', lh) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền kiểm hợp đồng hiện hành (vai KT + phân công CRM_HD_KIEM)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_kiem_pham_vi_duoc(k.id) THEN
                RAISE EXCEPTION 'CRM_KIEM_CHUA_CO_PHAM_VI: chưa cấu hình phạm vi kiểm hiện hành cho hợp đồng/dự án/khách này' USING ERRCODE = 'P0001';
            END IF;
            IF p_lenh AND k.tao_boi IS NOT DISTINCT FROM master.ktt_danh_tinh() THEN
                RAISE EXCEPTION 'CRM_G_CUNG_NGUOI: người ghi nhận bản ký không được tự kiểm/kích hoạt' USING ERRCODE = 'P0001';
            END IF;
            pn := k.phap_nhan_id;
        END $$""",
    # ======================================================================= tính lại từ bản ký (chính xác; không float/làm tròn/residual)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(p_ky uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE v_bg jsonb; v_tt text; v_sc integer; v_m numeric; v_tong numeric; v_tich numeric; v_e jsonb; v_i integer := 0; v_tl numeric; v_n numeric;
                v_mi numeric; v_dl text[]; v_dong jsonb := '[]'::jsonb; v_loi jsonb := '[]'::jsonb; v_cb jsonb := '[]'::jsonb;
                v_pct numeric := 0; v_amt numeric := 0; v_tien numeric := 0; v_du boolean := true; v_moc text; v_han date; v_tl_suy text;
                v_max constant numeric := 9223372036854775807;
        BEGIN
            SELECT r.du_lieu -> 'bao_gia' INTO v_bg FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id WHERE k.id = p_ky;
            v_tt := v_bg -> 'gia' ->> 'tien_te';
            v_sc := CASE v_tt WHEN 'VND' THEN 0 WHEN 'USD' THEN 2 END;
            IF v_sc IS NULL THEN
                RETURN jsonb_build_object('tien_te', v_tt, 'scale', NULL, 'tong_minor', NULL, 'tong_dong_minor', NULL, 'dong', '[]'::jsonb,
                                          'loi', jsonb_build_array(jsonb_build_object('ma', 'THIEU_TIEN_TE')), 'canh_bao', '[]'::jsonb);
            END IF;
            v_m := CASE v_sc WHEN 0 THEN 1 ELSE 100 END;
            IF coalesce((v_bg -> 'gia' ->> 'tong') ~ """ + _KIEM_RE_SO + """, false) THEN
                v_tong := (v_bg -> 'gia' ->> 'tong')::numeric * v_m;
                IF v_tong <> trunc(v_tong) THEN
                    v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_KHONG_DUNG_SCALE'));
                    v_tong := NULL;
                END IF;
            END IF;
            IF coalesce((v_bg -> 'gia' ->> 'don_gia') ~ """ + _KIEM_RE_SO + """ AND (v_bg -> 'gia' ->> 'dien_tich') ~ """ + _KIEM_RE_SO + """, false) THEN
                v_tich := (v_bg -> 'gia' ->> 'don_gia')::numeric * (v_bg -> 'gia' ->> 'dien_tich')::numeric * v_m;
                IF v_tich <> trunc(v_tich) THEN
                    v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'DON_GIA_X_DIEN_TICH_KHONG_DUNG_SCALE'));
                    v_tich := NULL;
                END IF;
            END IF;
            IF v_tong IS NULL AND v_tich IS NOT NULL THEN
                v_tong := v_tich;
            ELSIF v_tong IS NOT NULL AND v_tich IS NOT NULL AND v_tong <> v_tich THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_LECH_DON_GIA_X_DIEN_TICH'));
            END IF;
            IF v_tong IS NULL THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'THIEU_TONG_GIA_TRI'));
            ELSIF v_tong <= 0 OR v_tong > v_max THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_NGOAI_MIEN'));
                v_tong := NULL;
            END IF;
            FOR v_e IN SELECT x FROM jsonb_array_elements(CASE WHEN jsonb_typeof(v_bg -> 'lich') = 'array' THEN v_bg -> 'lich' ELSE '[]'::jsonb END) x LOOP
                v_i := v_i + 1;
                v_dl := '{}';
                v_mi := NULL;
                v_tl := NULL;
                v_tl_suy := NULL;
                IF v_e ->> 'loai' = 'PERCENT' THEN
                    IF NOT coalesce((v_e ->> 'ty_le') ~ """ + _KIEM_RE_SO + """, false) THEN
                        v_dl := v_dl || 'CHUA_CO_TY_LE'::text;
                    ELSE
                        v_tl := (v_e ->> 'ty_le')::numeric;
                        v_pct := v_pct + v_tl;
                        IF v_tong IS NULL THEN
                            v_dl := v_dl || 'CHUA_CO_TONG'::text;
                        ELSE
                            v_n := v_tong * v_tl;
                            IF v_n <> trunc(v_n) OR mod(v_n, 100) <> 0 THEN
                                v_dl := v_dl || 'KHONG_BIEU_DIEN_DUNG_SCALE'::text;
                            ELSE
                                v_mi := v_n / 100;
                            END IF;
                        END IF;
                    END IF;
                ELSIF v_e ->> 'loai' = 'AMOUNT' THEN
                    IF (v_e ->> 'tien_te') IS NOT NULL AND (v_e ->> 'tien_te') <> v_tt THEN
                        v_dl := v_dl || 'KHAC_TIEN_TE'::text;
                    END IF;
                    IF (v_e ->> 'so_tien') IS NULL THEN
                        v_dl := v_dl || 'CHUA_CO_SO_TIEN'::text;
                    ELSIF NOT ((v_e ->> 'so_tien') ~ """ + _KIEM_RE_SO + """) OR (v_e ->> 'so_tien')::numeric * v_m <> trunc((v_e ->> 'so_tien')::numeric * v_m) THEN
                        v_dl := v_dl || 'KHONG_DUNG_SCALE_TIEN_TE'::text;
                    ELSE
                        v_mi := (v_e ->> 'so_tien')::numeric * v_m;
                        v_amt := v_amt + v_mi;
                        IF coalesce(v_tong, 0) > 0 THEN
                            IF mod(v_mi * 100 * 1000000000000, v_tong) <> 0 THEN
                                v_dl := v_dl || 'TY_LE_SUY_RA_KHONG_HUU_HAN'::text;
                            ELSE
                                v_tl_suy := trim_scale(v_mi * 100 / v_tong)::text;
                            END IF;
                        ELSE
                            v_dl := v_dl || 'CHUA_CO_TONG'::text;
                        END IF;
                    END IF;
                ELSE
                    v_dl := v_dl || 'CHUA_CO_GIA_TRI'::text;
                END IF;
                IF v_mi IS NOT NULL AND (v_mi <= 0 OR v_mi > v_max) THEN
                    v_dl := v_dl || 'SO_TIEN_KHONG_DUONG'::text;
                END IF;
                IF v_mi IS NOT NULL THEN
                    v_tien := v_tien + v_mi;
                END IF;
                v_moc := CASE WHEN v_e ->> 'moc_loai' = 'NGAY' AND (v_e ->> 'moc_ngay') IS NOT NULL THEN 'NGAY:' || (v_e ->> 'moc_ngay')
                              WHEN v_e ->> 'moc_loai' = 'SU_KIEN' AND (v_e ->> 'moc_su_kien') IS NOT NULL THEN 'SU_KIEN:' || (v_e ->> 'moc_su_kien') END;
                v_han := CASE WHEN v_e ->> 'moc_loai' = 'NGAY' AND coalesce((v_e ->> 'moc_ngay') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$', false)
                              THEN (v_e ->> 'moc_ngay')::date END;
                IF v_moc IS NULL THEN
                    v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'MOC_TRONG', 'dong', v_i));
                END IF;
                IF cardinality(v_dl) > 0 THEN
                    v_du := false;
                END IF;
                v_dong := v_dong || jsonb_build_array(jsonb_build_object(
                    'dot', v_i, 'lan', left(coalesce(v_e ->> 'lan', v_i::text), 40), 'loai', v_e ->> 'loai',
                    'ty_le', CASE WHEN v_e ->> 'loai' = 'PERCENT' AND v_tl IS NOT NULL THEN trim_scale(v_tl)::text END, 'ty_le_suy_ra', v_tl_suy,
                    'so_tien_minor', CASE WHEN cardinality(v_dl) = 0 THEN v_mi::bigint::text END, 'moc', v_moc, 'han', v_han, 'loi', to_jsonb(v_dl)));
            END LOOP;
            IF v_i = 0 THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'THIEU_LICH'));
            ELSIF NOT v_du THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'LICH_CHUA_TINH_DUOC'));
            ELSIF v_tong IS NOT NULL AND v_pct * v_tong + 100 * v_amt <> 100 * v_tong THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_TY_LE_KHAC_100'));
            ELSIF v_tong IS NOT NULL AND v_tien <> v_tong THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_TIEN_LECH'));
            END IF;
            RETURN jsonb_build_object('tien_te', v_tt, 'scale', v_sc, 'tong_minor', v_tong::bigint::text,
                                      'tong_dong_minor', CASE WHEN v_tien <= v_max THEN v_tien::bigint::text END,
                                      'dong', v_dong, 'loi', v_loi, 'canh_bao', v_cb);
        END $$""",
    # G7 theo NGÀY KÝ: bộ chuẩn HIỆU LỰC của (dự án, giai đoạn) của báo giá đã ký; thiếu → THIEU_G7 (không coi là khớp)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_g7(p_ky uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE k record; v_bg jsonb; v_l jsonb; pb record; a record; v_e jsonb; v_d jsonb; v_i integer := 0; v_lech jsonb := '[]'::jsonb;
                v_n integer; v_tong numeric; v_mi numeric;
        BEGIN
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            SELECT r.du_lieu -> 'bao_gia' INTO v_bg FROM master.crm_hd_soan_rev r WHERE r.id = k.soan_rev_id;
            IF coalesce(v_bg ->> 'nguon_lich', 'KHACH') <> 'DU_AN' THEN
                RETURN jsonb_build_object('trang_thai', 'KHONG_AP_DUNG', 'lech', '[]'::jsonb);
            END IF;
            SELECT v.* INTO pb FROM master.crm_bo_chuan b JOIN master.crm_bo_chuan_phien_ban v ON v.bo_chuan_id = b.id AND v.phap_nhan_id = b.phap_nhan_id
                WHERE b.phap_nhan_id = k.phap_nhan_id AND b.du_an_id::text = (v_bg ->> 'du_an_id') AND b.giai_doan = (v_bg ->> 'giai_doan_g7')
                  AND v.trang_thai = 'HIEU_LUC' AND v.valid_from <= k.ngay_ky AND (v.valid_to IS NULL OR v.valid_to > k.ngay_ky)
                ORDER BY v.valid_from DESC, v.phien_ban DESC LIMIT 1;
            IF pb.id IS NULL THEN
                RETURN jsonb_build_object('trang_thai', 'THIEU_G7', 'lech', '[]'::jsonb);
            END IF;
            v_l := master.crm_kiem_lich_ky(p_ky);
            v_tong := (v_l ->> 'tong_minor')::numeric;
            SELECT count(*) INTO v_n FROM master.crm_bo_chuan_dong WHERE phien_ban_id = pb.id;
            IF v_n <> jsonb_array_length(v_l -> 'dong') THEN
                v_lech := v_lech || jsonb_build_array(jsonb_build_object('ma', 'LECH_G7_SO_DONG', 'dong', 0, 'khoa', 'LECH_G7_SO_DONG:0'));
            END IF;
            FOR a IN SELECT * FROM master.crm_bo_chuan_dong WHERE phien_ban_id = pb.id ORDER BY thu_tu LOOP
                v_i := v_i + 1;
                v_e := v_bg -> 'lich' -> (v_i - 1);
                v_d := v_l -> 'dong' -> (v_i - 1);
                EXIT WHEN v_e IS NULL OR v_d IS NULL;
                v_mi := (v_d ->> 'so_tien_minor')::numeric;
                IF a.gia_tri_loai = 'PERCENT' AND (
                       (v_e ->> 'loai' = 'PERCENT' AND (v_d ->> 'ty_le' IS NULL OR (v_d ->> 'ty_le')::numeric <> a.gia_tri_thap_phan::numeric))
                    OR (v_e ->> 'loai' IS DISTINCT FROM 'PERCENT' AND (v_mi IS NULL OR coalesce(v_tong, 0) = 0
                                                                      OR v_mi * 100 <> a.gia_tri_thap_phan::numeric * v_tong))) THEN
                    v_lech := v_lech || jsonb_build_array(jsonb_build_object('ma', 'LECH_G7_TY_LE', 'dong', v_i, 'khoa', 'LECH_G7_TY_LE:' || v_i));
                ELSIF a.gia_tri_loai = 'AMOUNT' AND (a.tien_te::text IS DISTINCT FROM v_l ->> 'tien_te' OR v_mi IS DISTINCT FROM a.so_tien_minor::numeric) THEN
                    v_lech := v_lech || jsonb_build_array(jsonb_build_object('ma', 'LECH_G7_SO_TIEN', 'dong', v_i, 'khoa', 'LECH_G7_SO_TIEN:' || v_i));
                END IF;
                IF ROW(a.moc_loai, a.moc_ngay::text, a.moc_su_kien) IS DISTINCT FROM ROW(v_e ->> 'moc_loai', v_e ->> 'moc_ngay', v_e ->> 'moc_su_kien') THEN
                    v_lech := v_lech || jsonb_build_array(jsonb_build_object('ma', 'LECH_G7_MOC', 'dong', v_i, 'khoa', 'LECH_G7_MOC:' || v_i));
                END IF;
            END LOOP;
            RETURN jsonb_build_object('trang_thai', CASE WHEN jsonb_array_length(v_lech) = 0 THEN 'KHOP' ELSE 'LECH' END,
                                      'bo_chuan_pb_id', pb.id, 'bo_chuan_phien_ban', pb.phien_ban, 'lech', v_lech);
        END $$""",
    # G5: VAN_HANH luôn HOLD (chưa có producer/policy/kết quả tin cậy đăng ký) — PENDING/NOT_SELECTED khởi tạo KHÔNG là bằng chứng.
    # SYNTHETIC_FIXTURE: chỉ khi GUC fixture bật trong giao dịch; luôn mang nhãn phi vận hành.
    """CREATE OR REPLACE FUNCTION master.crm_kiem_g5_xet(p_ky uuid, p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE g record; q record; v_kt jsonb;
        BEGIN
            SELECT * INTO g FROM master.crm_hd_ky_g5 WHERE ky_id = p_ky;
            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);
            IF p_che_do IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN
                RETURN jsonb_build_object('che_do', 'VAN_HANH', 'trang_thai', 'HOLD', 'khoi_tao', v_kt, 'lech', '[]'::jsonb,
                                          'chan', jsonb_build_array(jsonb_build_object('ma', 'UNREGISTERED_G5_PROOF')));
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
    # tham số từ bản ký: mỗi trường danh mục đã ghim + giá trị revision đã xuất/ký + số vị trí ánh xạ; thêm crm.lich và crm.ngay_hieu_luc (KT)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_tham_so_ky(p_ky uuid, p_rev uuid)
        RETURNS TABLE (ten text, nhan text, gia_tri text, gia_tri_so numeric, gia_tri_typed jsonb, don_vi text, kieu text, nhom text, truong text,
                       ma_nguon text, vi_tri text, trich_dan text, kiem_tra_nguon text, trang_thai_can_cu text, bat_buoc boolean, pii boolean)
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        WITH kk AS (
            SELECT k.id, k.phap_nhan_id, k.danh_muc_ref, k.danh_muc_rev, k.mau_phien_ban_id, k.ky_pdf_sha256, s.loai_hinh_id, r.du_lieu,
                   m.ma_mau, pv.phien_ban AS mau_pb, ax.ban_do
            FROM master.crm_hd_ky k
            JOIN master.crm_hd_soan s ON s.id = k.soan_id
            JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id
            JOIN master.crm_mau_phien_ban pv ON pv.id = k.mau_phien_ban_id
            JOIN master.crm_mau m ON m.id = pv.mau_id
            JOIN master.crm_mau_anh_xa ax ON ax.id = k.anh_xa_id
            WHERE k.id = p_ky),
        ff AS (
            SELECT dm.khoa, dm.nhan, dm.kieu, dm.nhom, dm.pii, dm.bat_buoc, kk.mau_phien_ban_id, kk.ma_mau, kk.mau_pb, kk.ky_pdf_sha256,
                   CASE WHEN jsonb_typeof(kk.du_lieu -> 'gia_tri_truong' -> dm.khoa) IN ('string','number','object','array','boolean')
                        THEN kk.du_lieu -> 'gia_tri_truong' -> dm.khoa END AS v,
                   (SELECT count(*) FROM jsonb_array_elements(kk.ban_do) b WHERE b ->> 'truong' = dm.khoa) AS n
            FROM kk JOIN master.crm_danh_muc_truong dm ON dm.phap_nhan_id = kk.phap_nhan_id AND dm.loai_hinh_id = kk.loai_hinh_id
                 AND dm.danh_muc_ref = kk.danh_muc_ref AND dm.revision = kk.danh_muc_rev),
        ll AS (SELECT master.crm_kiem_lich_ky(p_ky) AS l)
        SELECT 'crm.' || ff.khoa, ff.nhan,
               CASE WHEN ff.v IS NULL THEN NULL
                    WHEN ff.kieu = 'tien' AND jsonb_typeof(ff.v) = 'object' THEN (ff.v ->> 'so_tien') || ' ' || (ff.v ->> 'tien_te')
                    WHEN jsonb_typeof(ff.v) = 'string' THEN ff.v #>> '{}'
                    ELSE ff.v::text END,
               CASE WHEN ff.kieu = 'so' AND jsonb_typeof(ff.v) = 'string' AND (ff.v #>> '{}') ~ """ + _KIEM_RE_SO + """ THEN (ff.v #>> '{}')::numeric
                    WHEN ff.kieu = 'tien' AND jsonb_typeof(ff.v) = 'object' AND (ff.v ->> 'so_tien') ~ """ + _KIEM_RE_SO + """ THEN (ff.v ->> 'so_tien')::numeric END,
               ff.v,
               CASE WHEN ff.kieu = 'tien' AND jsonb_typeof(ff.v) = 'object' THEN ff.v ->> 'tien_te' END,
               ff.kieu, ff.nhom, ff.khoa, 'CRM_MAU:' || ff.mau_phien_ban_id::text, ff.n::text || ' vị trí',
               'MẪU ' || ff.ma_mau || ' v' || ff.mau_pb::text || ' · trường ' || ff.khoa || ' · ' || ff.n::text || ' vị trí · bản ký ' || left(ff.ky_pdf_sha256, 12),
               'BAN_KY_SHA256:' || ff.ky_pdf_sha256,
               CASE WHEN ff.v IS NOT NULL AND ff.n > 0 THEN 'CO_CAN_CU' ELSE 'CHUA_DOI_CHIEU_NGUON' END,
               ff.bat_buoc, ff.pii
        FROM ff
        UNION ALL
        SELECT 'crm.lich', 'Lịch thu theo bản ký', (ll.l ->> 'tong_minor') || ' ' || (ll.l ->> 'tien_te'), (ll.l ->> 'tong_minor')::numeric,
               jsonb_build_object('tien_te', ll.l -> 'tien_te', 'scale', ll.l -> 'scale', 'tong_minor', ll.l -> 'tong_minor', 'dong', ll.l -> 'dong'),
               ll.l ->> 'tien_te', 'bang', 'LICH', 'lich', 'CRM_MAU:BAN_KY', jsonb_array_length(ll.l -> 'dong')::text || ' đợt',
               'BÁO GIÁ ĐÃ KÝ · lịch ' || jsonb_array_length(ll.l -> 'dong')::text || ' đợt · bản ký ' || left(kk.ky_pdf_sha256, 12),
               'BAN_KY_SHA256:' || kk.ky_pdf_sha256,
               CASE WHEN jsonb_array_length(ll.l -> 'loi') = 0 THEN 'CO_CAN_CU' ELSE 'CHUA_DOI_CHIEU_NGUON' END, true, false
        FROM kk, ll
        UNION ALL
        SELECT 'crm.ngay_hieu_luc', 'Ngày hiệu lực (kế toán xác định)', rv.ngay_hieu_luc::text, NULL::numeric,
               CASE WHEN rv.ngay_hieu_luc IS NOT NULL THEN to_jsonb(rv.ngay_hieu_luc::text) END, NULL, 'ngay', 'HIEU_LUC', 'ngay_hieu_luc',
               'CRM_G6A:' || coalesce(rv.can_cu_ngay, 'CHUA_CO'), NULL, rv.trich_dan_ngay, 'KT_KIEM_REV:' || rv.id::text,
               CASE WHEN rv.ngay_hieu_luc IS NOT NULL AND rv.trich_dan_ngay IS NOT NULL THEN 'CO_CAN_CU' ELSE 'CHUA_DOI_CHIEU_NGUON' END, true, false
        FROM master.crm_kiem_rev rv WHERE rv.id = p_rev AND rv.ky_id = p_ky
        $$""",
    # đánh giá đầy đủ (một hàm cho check, quyết định, hiển thị): đồ thị KHÔNG PII (giá trị tham số chỉ là sha256), sha256, chặn, cảnh báo
    """CREATE OR REPLACE FUNCTION master.crm_kiem_danh_gia(p_ky uuid, p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE k record; h record; s record; r record; ho record; rv record; j record; v_l jsonb; v_g7 jsonb; v_g5 jsonb; v_ts jsonb := '[]'::jsonb;
                v_xl jsonb; v_e jsonb; v_chan jsonb := '[]'::jsonb; v_cb jsonb := '[]'::jsonb; v_dt jsonb; v_muc text; v_ky_dt text;
        BEGIN
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NULL THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản ký' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM master.hop_dong WHERE id = k.hop_dong_id;
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = k.soan_id;
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE id = k.soan_rev_id;
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE ky_id = p_ky;
            SELECT * INTO rv FROM master.crm_kiem_rev WHERE ho_so_id = ho.id AND revision = ho.revision;
            SELECT * INTO j FROM master.doi_tac_ma_junsky WHERE id = rv.de_xuat_ma_junsky_id;
            IF ho.id IS NULL OR ho.trang_thai <> 'DANG_KIEM' THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'HO_SO_KHONG_DANG_KIEM'));
            END IF;
            IF rv.id IS NULL THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'CHUA_LUU_KIEM'));
            END IF;
            IF h.crm_giao_ket IS DISTINCT FROM 'DA_KY' OR s.trang_thai IS DISTINCT FROM 'DA_KY' OR h.phien_ban_hien_hanh IS NOT NULL
               OR EXISTS (SELECT 1 FROM master.hop_dong_phien_ban p WHERE p.hop_dong_id = h.id) THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'HOP_DONG_KHONG_O_DA_KY'));
            END IF;
            IF master.crm_g_danh_muc_digest(s.loai_hinh_id, k.danh_muc_ref, k.danh_muc_rev) IS DISTINCT FROM k.danh_muc_digest THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'DANH_MUC_LECH_GHIM'));
            END IF;
            IF rv.id IS NOT NULL THEN
                FOREACH v_muc IN ARRAY """ + _KIEM_CHECKLIST + """ LOOP
                    IF (rv.checklist ->> v_muc) IS DISTINCT FROM 'XAC_NHAN' THEN
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', CASE WHEN rv.checklist ->> v_muc = 'CO_VAN_DE' THEN 'CHECKLIST_CO_VAN_DE'
                                                                                          ELSE 'CHECKLIST_CHUA_XAC_NHAN' END, 'muc', v_muc));
                    END IF;
                END LOOP;
                v_ky_dt := r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id';
                IF rv.de_xuat_doi_tac_id IS NULL THEN
                    v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'THIEU_KHACH_JUNSKY'));
                ELSE
                    IF v_ky_dt IS NOT NULL AND v_ky_dt <> rv.de_xuat_doi_tac_id::text THEN
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'KHACH_KHAC_BAN_KY'));
                    END IF;
                    IF h.doi_tac_id IS NOT NULL AND h.doi_tac_id <> rv.de_xuat_doi_tac_id THEN
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'KHACH_KHAC_HOP_DONG'));
                    END IF;
                    IF j.id IS NULL OR j.doi_tac_id <> rv.de_xuat_doi_tac_id OR j.phap_nhan_id <> k.phap_nhan_id OR j.valid_to IS NOT NULL OR j.dong THEN
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'JUNSKY_KHONG_HIEU_LUC'));
                    END IF;
                    IF v_ky_dt IS NULL THEN
                        v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'KHACH_GAN_MA_KHI_KIEM'));
                    END IF;
                END IF;
                IF rv.ngay_hieu_luc IS NULL THEN
                    v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'THIEU_NGAY_HIEU_LUC'));
                ELSIF rv.ngay_hieu_luc < k.ngay_ky THEN
                    v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'NGAY_HIEU_LUC_TRUOC_NGAY_KY'));
                END IF;
            END IF;
            v_l := master.crm_kiem_lich_ky(p_ky);
            v_chan := v_chan || coalesce(v_l -> 'loi', '[]'::jsonb);
            IF v_l ->> 'tien_te' = 'USD' THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'USD_CHUA_HO_TRO_LIEN_KET_F7'));
            END IF;
            v_cb := v_cb || coalesce(v_l -> 'canh_bao', '[]'::jsonb);
            v_g7 := master.crm_kiem_g7(p_ky);
            IF v_g7 ->> 'trang_thai' = 'THIEU_G7' THEN
                v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'THIEU_G7'));
            ELSIF v_g7 ->> 'trang_thai' = 'LECH' THEN
                FOR v_e IN SELECT x FROM jsonb_array_elements(v_g7 -> 'lech') x LOOP
                    IF EXISTS (SELECT 1 FROM master.crm_kiem_xu_ly_lech y WHERE y.ky_id = p_ky AND y.loai = 'G7_LECH'
                               AND y.muc_tieu_id::text = v_g7 ->> 'bo_chuan_pb_id' AND y.ma_lech = v_e ->> 'khoa') THEN
                        v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'G7_LECH_THEO_BAN_KY', 'muc', v_e ->> 'khoa'));
                    ELSE
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'G7_LECH_CHUA_XU_LY', 'muc', v_e ->> 'khoa'));
                    END IF;
                END LOOP;
            END IF;
            v_g5 := master.crm_kiem_g5_xet(p_ky, p_che_do);
            v_chan := v_chan || coalesce(v_g5 -> 'chan', '[]'::jsonb);
            IF v_g5 ->> 'trang_thai' = 'LECH' THEN
                FOR v_e IN SELECT x FROM jsonb_array_elements(v_g5 -> 'lech') x LOOP
                    IF EXISTS (SELECT 1 FROM master.crm_kiem_xu_ly_lech y WHERE y.ky_id = p_ky AND y.loai = 'G5_LECH'
                               AND y.muc_tieu_id::text = v_g5 ->> 'ket_qua_id' AND y.ma_lech = v_e ->> 'khoa') THEN
                        v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'G5_LECH_THEO_BAN_KY', 'muc', v_e ->> 'khoa'));
                    ELSE
                        v_chan := v_chan || jsonb_build_array(jsonb_build_object('ma', 'G5_LECH_CHUA_XU_LY', 'muc', v_e ->> 'khoa'));
                    END IF;
                END LOOP;
            END IF;
            IF rv.id IS NOT NULL THEN
                SELECT coalesce(jsonb_agg(jsonb_build_object('ten', t.ten, 'kieu', t.kieu, 'nhom', t.nhom, 'bat_buoc', t.bat_buoc, 'pii', t.pii,
                                                             'vi_tri', t.vi_tri, 'trang_thai_can_cu', t.trang_thai_can_cu,
                                                             'gia_tri_sha256', CASE WHEN t.gia_tri_typed IS NOT NULL THEN """ + _GK_SHA.format(x="t.gia_tri_typed") + """ END)
                                          ORDER BY t.ten), '[]'::jsonb) INTO v_ts
                    FROM master.crm_kiem_tham_so_ky(p_ky, rv.id) t;
                SELECT v_chan || coalesce(jsonb_agg(jsonb_build_object('ma', 'THIEU_CAN_CU', 'muc', t.ten) ORDER BY t.ten), '[]'::jsonb) INTO v_chan
                    FROM master.crm_kiem_tham_so_ky(p_ky, rv.id) t WHERE t.bat_buoc AND t.trang_thai_can_cu <> 'CO_CAN_CU';
            END IF;
            SELECT coalesce(jsonb_agg(jsonb_build_object('id', y.id, 'loai', y.loai, 'muc_tieu_id', y.muc_tieu_id, 'ma_lech', y.ma_lech,
                                                         'quyet_dinh', y.quyet_dinh) ORDER BY y.loai, y.ma_lech, y.id), '[]'::jsonb) INTO v_xl
                FROM master.crm_kiem_xu_ly_lech y WHERE y.ky_id = p_ky;
            v_dt := jsonb_build_object(
                'phien_ban_do_thi', 1, 'ky_id', k.id, 'ky_pdf_sha256', k.ky_pdf_sha256, 'g3_pdf_sha256', k.g3_pdf_sha256, 'soan_rev_id', k.soan_rev_id,
                'du_lieu_sha256', k.du_lieu_sha256, 'danh_muc_digest', k.danh_muc_digest, 'ho_so_id', ho.id, 'ho_so_revision', ho.revision,
                'rev_id', rv.id, 'checklist', rv.checklist,
                'khach', jsonb_build_object('doi_tac_id', rv.de_xuat_doi_tac_id, 'ma_junsky_id', rv.de_xuat_ma_junsky_id),
                'ngay_hieu_luc', rv.ngay_hieu_luc, 'can_cu_ngay', rv.can_cu_ngay,
                'trich_dan_ngay_sha256', CASE WHEN rv.trich_dan_ngay IS NOT NULL THEN """ + _GK_SHA.format(x="rv.trich_dan_ngay") + """ END,
                'lich', v_l - 'canh_bao', 'g7', v_g7, 'g5', v_g5, 'tham_so', v_ts, 'xu_ly_lech', v_xl);
            RETURN jsonb_build_object('do_thi', v_dt, 'sha256', """ + _GK_SHA.format(x="v_dt") + """, 'chan', v_chan, 'canh_bao', v_cb,
                                      'ket_luan', CASE WHEN jsonb_array_length(v_chan) = 0 THEN 'DU_DIEU_KIEN' ELSE 'CHUA_DU_DIEU_KIEN' END);
        END $$""",
    # ======================================================================= hiển thị/đọc (PII che; quyền HIỆN HÀNH trước tra cứu; nhật ký truy cập)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_che(p text) RETURNS text
        LANGUAGE sql IMMUTABLE SET search_path = pg_temp AS $$
        SELECT CASE WHEN p IS NULL THEN NULL WHEN length(p) <= 4 THEN '****' ELSE repeat('*', least(length(p) - 4, 8)) || right(p, 4) END
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_kq(p_ho_so uuid) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT jsonb_build_object('ho_so_id', x.id, 'ky_id', x.ky_id, 'hop_dong_id', x.hop_dong_id, 'trang_thai', x.trang_thai,
                                  'hien_thi', """ + _KIEM_HIEN_THI.format(c="x.trang_thai") + """, 'revision', x.revision, 'viec_id', x.viec_id,
                                  'hieu_luc', (SELECT jsonb_build_object('phien_ban_id', z.phien_ban_id, 'chung_tu_id', z.chung_tu_id, 'so_dong_lich', z.so_dong_lich,
                                                                         'so_tham_so', z.so_tham_so, 'tong_minor', z.tong_minor::text, 'tien_te', z.tien_te,
                                                                         'g7_trang_thai', z.g7_trang_thai, 'g5_che_do', z.g5_che_do,
                                                                         'viec_cfo_id', (SELECT v.id FROM kho.viec_can_duyet v WHERE v.tham_chieu_bang = 'master.crm_kiem_hieu_luc'
                                                                                         AND v.tham_chieu_id = z.id))
                                               FROM master.crm_kiem_hieu_luc z WHERE z.ho_so_id = x.id),
                                  'phu_thuoc', CASE WHEN x.trang_thai = 'TRA_LAI_CHO_KY_LAI' THEN 'CRM_G6A_TRA_LAI_CHO_G4_KY_LAI' END)
        FROM master.crm_kiem_ho_so x WHERE x.id = p_ho_so
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_ds() RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        BEGIN""" + _G_CHU + """
            RETURN (SELECT coalesce(jsonb_agg(jsonb_build_object('ky_id', k.id, 'hop_dong_id', k.hop_dong_id, 'ma_noi_bo', h.ma_noi_bo, 'ngay_ky', k.ngay_ky,
                                                                 'trang_thai', coalesce(x.trang_thai, 'CHUA_KIEM'),
                                                                 'hien_thi', """ + _KIEM_HIEN_THI.format(c="x.trang_thai") + """,
                                                                 'revision', coalesce(x.revision, 0)) ORDER BY k.ngay_ky DESC, k.id), '[]'::jsonb)
                    FROM master.crm_hd_ky k JOIN master.hop_dong h ON h.id = k.hop_dong_id
                    JOIN master.crm_hd_soan s ON s.id = k.soan_id
                    LEFT JOIN master.crm_kiem_ho_so x ON x.ky_id = k.id
                    WHERE master.ktt_hanh_dong_duoc(k.phap_nhan_id, 'CRM', 'CRM_HD_KIEM', s.loai_hinh_id) AND master.crm_kiem_pham_vi_duoc(k.id));
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_doc(p_ky uuid, p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; k record; h record; r record; g record; ho record; rv record; j record; mv record; c record;
                v_kq jsonb;
        BEGIN""" + _G_CHU + """
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NOT NULL THEN  -- ghim quyền + phạm vi hiện hành tới hết giao dịch (thu hồi đồng thời không lọt giữa kiểm và nhật ký/đọc)
                PERFORM master.crm_g_ghim_quyen(k.phap_nhan_id);
                PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = k.id AND b.thu_hoi_luc IS NULL FOR SHARE;
            END IF;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, false);
            SELECT * INTO h FROM master.hop_dong WHERE id = k.hop_dong_id;
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE id = k.soan_rev_id;
            SELECT * INTO g FROM master.crm_hd_ky_g5 WHERE ky_id = k.id;
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE ky_id = k.id;
            SELECT * INTO rv FROM master.crm_kiem_rev WHERE ho_so_id = ho.id AND revision = ho.revision;
            SELECT * INTO j FROM master.doi_tac_ma_junsky WHERE id = rv.de_xuat_ma_junsky_id;
            SELECT pv.phien_ban, m.ma_mau INTO mv FROM master.crm_mau_phien_ban pv JOIN master.crm_mau m ON m.id = pv.mau_id WHERE pv.id = k.mau_phien_ban_id;
            SELECT * INTO c FROM master.crm_kiem_check WHERE ho_so_id = ho.id ORDER BY thu_tu DESC LIMIT 1;
            v_kq := jsonb_build_object(
                'ky', jsonb_build_object('ky_id', k.id, 'hop_dong_id', k.hop_dong_id, 'ma_noi_bo', h.ma_noi_bo, 'revision', k.revision, 'ngay_ky', k.ngay_ky,
                                         'nguoi_ky_khach', master.crm_kiem_che(k.nguoi_ky_khach), 'co_sua', k.co_sua, 'mo_ta_sua', k.mo_ta_sua,
                                         'ky_pdf_sha256', k.ky_pdf_sha256, 'ky_pdf_len', k.ky_pdf_len, 'ky_so_trang', k.ky_so_trang,
                                         'g3_pdf_sha256', k.g3_pdf_sha256, 'g3_pdf_len', k.g3_pdf_len, 'ma_mau', mv.ma_mau, 'phien_ban_mau', mv.phien_ban,
                                         'danh_muc_ref', k.danh_muc_ref, 'danh_muc_rev', k.danh_muc_rev, 'tao_boi', k.tao_boi,
                                         'g5_khoi_tao', jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false)),
                'quyen', jsonb_build_object('kiem', k.tao_boi IS DISTINCT FROM ai, 'ly_do', CASE WHEN k.tao_boi IS NOT DISTINCT FROM ai THEN 'CRM_G_CUNG_NGUOI' END),
                'hop_dong', jsonb_build_object('crm_giao_ket', h.crm_giao_ket, 'doi_tac_id', h.doi_tac_id),
                'khach_ban_ky', jsonb_build_object('doi_tac_id', r.du_lieu -> 'bao_gia' -> 'khach' -> 'doi_tac_id',
                                                   'du_thao_ten', master.crm_kiem_che(r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao' ->> 'ten'),
                                                   'du_thao_lien_he', master.crm_kiem_che(r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao' ->> 'lien_he')),
                'ma_junsky_ung_vien', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', y.id, 'doi_tac_id', y.doi_tac_id, 'tien_to', y.tien_to,
                                                                                    'object_id', master.crm_kiem_che(y.object_id_junsky),
                                                                                    'ten', master.crm_kiem_che(y.ten_junsky)) ORDER BY y.valid_from, y.id), '[]'::jsonb)
                                       FROM master.doi_tac_ma_junsky y WHERE y.phap_nhan_id = k.phap_nhan_id AND y.valid_to IS NULL AND NOT y.dong
                                         AND (y.doi_tac_id::text = coalesce(r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id', h.doi_tac_id::text)
                                              -- khách dự thảo (cả hai ID NULL): chỉ cặp KT đã CHỌN CÓ CHỦ Ý ở revision hiện hành; tìm thêm qua crm_kiem_tim_junsky
                                              OR (y.id = rv.de_xuat_ma_junsky_id AND y.doi_tac_id = rv.de_xuat_doi_tac_id))),
                'khach_du_thao', (r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id') IS NULL AND h.doi_tac_id IS NULL,
                'ho_so', CASE WHEN ho.id IS NOT NULL THEN master.crm_kiem_kq(ho.id) END,
                'rev', CASE WHEN rv.id IS NOT NULL THEN jsonb_build_object(
                           'rev_id', rv.id, 'revision', rv.revision, 'checklist', rv.checklist, 'de_xuat_doi_tac_id', rv.de_xuat_doi_tac_id,
                           'de_xuat_ma_junsky_id', rv.de_xuat_ma_junsky_id, 'ma_junsky', master.crm_kiem_che(j.object_id_junsky),
                           'ngay_hieu_luc', rv.ngay_hieu_luc, 'can_cu_ngay', rv.can_cu_ngay, 'trich_dan_ngay', rv.trich_dan_ngay, 'ghi_chu', rv.ghi_chu,
                           'tao_boi', rv.tao_boi, 'tao_luc', rv.tao_luc) END,
                'truong', (SELECT coalesce(jsonb_agg(jsonb_build_object('ten', t.ten, 'nhan', t.nhan, 'kieu', t.kieu, 'nhom', t.nhom, 'pii', t.pii,
                                                                       'bat_buoc', t.bat_buoc, 'gia_tri', CASE WHEN t.pii THEN master.crm_kiem_che(t.gia_tri) ELSE t.gia_tri END,
                                                                       'vi_tri', t.vi_tri, 'trang_thai_can_cu', t.trang_thai_can_cu)
                                                    ORDER BY t.ten), '[]'::jsonb)
                           FROM master.crm_kiem_tham_so_ky(k.id, rv.id) t WHERE t.ten NOT IN ('crm.lich')),
                'lich', master.crm_kiem_lich_ky(k.id),
                'g7', master.crm_kiem_g7(k.id),
                'g5', master.crm_kiem_g5_xet(k.id, p_che_do),
                'check', CASE WHEN c.id IS NOT NULL THEN jsonb_build_object('check_id', c.id, 'ho_so_revision', c.ho_so_revision, 'ket_luan', c.ket_luan,
                                                                             'chan', c.chan, 'canh_bao', c.canh_bao, 'do_thi_sha256', c.do_thi_sha256,
                                                                             'g5_che_do', c.g5_che_do, 'tao_luc', c.tao_luc) END,
                'xu_ly_lech', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', y.id, 'loai', y.loai, 'muc_tieu_id', y.muc_tieu_id, 'ma_lech', y.ma_lech,
                                                                            'ly_do', y.ly_do, 'tao_boi', y.tao_boi) ORDER BY y.tao_luc, y.id), '[]'::jsonb)
                               FROM master.crm_kiem_xu_ly_lech y WHERE y.ky_id = k.id),
                'lich_su', (SELECT coalesce(jsonb_agg(jsonb_build_object('luc', e.luc, 'nguoi', e.nguoi, 'hanh_dong', e.hanh_dong) ORDER BY e.id), '[]'::jsonb)
                            FROM nhat_ky.su_kien e WHERE (e.doi_tuong_bang = 'master.crm_kiem_ho_so' AND e.doi_tuong_id = ho.id)
                                                      OR (e.doi_tuong_bang = 'master.crm_hd_ky' AND e.doi_tuong_id = k.id)),
                '_bao_gia', r.du_lieu -> 'bao_gia');
            """ + _G_NK.format(pn="k.phap_nhan_id", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="'CRM_KIEM_XEM'",
                               sau="jsonb_build_object('muc_dich', 'XEM_KIEM', 'ky_pdf_sha256', k.ky_pdf_sha256)", ly="NULL") + """
            RETURN v_kq;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_tep(p_ky uuid, p_loai text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; k record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NOT NULL THEN
                PERFORM master.crm_g_ghim_quyen(k.phap_nhan_id);
                PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = k.id AND b.thu_hoi_luc IS NULL FOR SHARE;
            END IF;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, false);
            IF p_loai IS NULL OR p_loai NOT IN ('BAN_KY','G3_PDF') THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: loại tệp không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            """ + _G_NK.format(pn="k.phap_nhan_id", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="'CRM_KIEM_TAI'",
                               sau="jsonb_build_object('loai', p_loai, 'sha256', CASE p_loai WHEN 'BAN_KY' THEN k.ky_pdf_sha256 ELSE k.g3_pdf_sha256 END)",
                               ly="NULL") + """
            RETURN jsonb_build_object('ky_id', k.id, 'loai', p_loai, 'revision', k.revision,
                                      'sha256', CASE p_loai WHEN 'BAN_KY' THEN k.ky_pdf_sha256 ELSE k.g3_pdf_sha256 END,
                                      'len', CASE p_loai WHEN 'BAN_KY' THEN k.ky_pdf_len ELSE k.g3_pdf_len END,
                                      'ten', (SELECT h.ma_noi_bo FROM master.hop_dong h WHERE h.id = k.hop_dong_id));
        END $$""",
    # P1-B: tra mã Junsky CÓ SẴN cho khách DỰ THẢO (bản ký + HĐ đều chưa có đối tác). Quyền lệnh hiện hành (vai KT + CRM_HD_KIEM + phạm vi,
    # không phải người ghi bản ký) TRƯỚC tra cứu; chỉ PN của bản ký; từ khóa ≥ 3 ký tự; tối đa 10; che PII; nhật ký truy cập. Không tạo mã/đối tác.
    """CREATE OR REPLACE FUNCTION master.crm_kiem_tim_junsky(p_ky uuid, p_tu_khoa text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; k record; v_dt text; v_hd uuid; v_t text; v_kq jsonb;
        BEGIN""" + _G_CHU + """
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NOT NULL THEN
                PERFORM master.crm_g_ghim_quyen(k.phap_nhan_id);
                PERFORM 1 FROM master.crm_kiem_pham_vi b WHERE b.ky_id = k.id AND b.thu_hoi_luc IS NULL FOR SHARE;
            END IF;
            SELECT * INTO d FROM master.crm_kiem_dich(p_ky, true);
            IF p_tu_khoa IS NULL OR length(btrim(p_tu_khoa)) NOT BETWEEN 3 AND 60 OR p_tu_khoa ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: từ khóa tìm mã Junsky 3–60 ký tự' USING ERRCODE = 'P0001';
            END IF;
            SELECT r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id', h.doi_tac_id INTO v_dt, v_hd
                FROM master.crm_hd_soan_rev r, master.hop_dong h WHERE r.id = k.soan_rev_id AND h.id = k.hop_dong_id;
            IF v_dt IS NOT NULL OR v_hd IS NOT NULL THEN
                RAISE EXCEPTION 'CRM_KIEM_KHACH_DA_DINH: khách đã định danh trên bản ký/hợp đồng — không tra/thay mã khác' USING ERRCODE = 'P0001';
            END IF;
            v_t := btrim(p_tu_khoa);
            SELECT coalesce(jsonb_agg(x.o ORDER BY x.s), '[]'::jsonb) INTO v_kq FROM (
                SELECT y.object_id_junsky AS s,
                       jsonb_build_object('id', y.id, 'doi_tac_id', y.doi_tac_id, 'tien_to', y.tien_to,
                                          'object_id', CASE WHEN upper(y.object_id_junsky) = upper(v_t) THEN y.object_id_junsky
                                                            ELSE master.crm_kiem_che(y.object_id_junsky) END,
                                          'khop_ma', upper(y.object_id_junsky) = upper(v_t), 'ten', master.crm_kiem_che(y.ten_junsky)) AS o
                FROM master.doi_tac_ma_junsky y
                WHERE y.phap_nhan_id = d.pn AND y.valid_to IS NULL AND NOT y.dong
                  AND (upper(y.object_id_junsky) = upper(v_t)
                       OR y.ten_junsky ILIKE '%' || replace(replace(replace(v_t, '\\', '\\\\'), '%', '\\%'), '_', '\\_') || '%')
                ORDER BY y.object_id_junsky LIMIT 10) x;
            """ + _G_NK.format(pn="d.pn", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="'CRM_KIEM_TIM_JUNSKY'",
                               sau="jsonb_build_object('so_ket_qua', jsonb_array_length(v_kq), 'tu_khoa_sha256', " + _GK_SHA.format(x="v_t") + ")",
                               ly="NULL") + """
            RETURN jsonb_build_object('ky_id', k.id, 'ung_vien', v_kq, 'gioi_han', 10);
        END $$""",
    # ======================================================================= lệnh (READ COMMITTED; quyền → biên nhận → khóa hồ sơ → CAS)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_luu(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_checklist jsonb, p_doi_tac uuid,
                                                   p_ma_junsky uuid, p_ngay date, p_can_cu text, p_trich_dan text, p_ghi_chu text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record; v_cu text; v_vid uuid; v_rid uuid;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_LUU'") + """
            IF p_expected IS NULL OR p_expected < 0 OR p_checklist IS NULL OR jsonb_typeof(p_checklist) <> 'object' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: thiếu revision kỳ vọng/checklist' USING ERRCODE = 'P0001';
            END IF;
            IF h.crm_giao_ket IS DISTINCT FROM 'DA_KY' THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chỉ kiểm hợp đồng đã ký (hiện %)', h.crm_giao_ket USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE ky_id = p_ky FOR UPDATE;
            IF ho.id IS NULL THEN
                IF p_expected <> 0 THEN
                    RAISE EXCEPTION 'CRM_KIEM_REVISION_CU: hồ sơ kiểm chưa tồn tại — revision kỳ vọng phải là 0' USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO master.crm_kiem_ho_so (phap_nhan_id, ky_id, hop_dong_id, trang_thai, revision, tao_boi)
                    VALUES (d.pn, k.id, k.hop_dong_id, 'DANG_KIEM', 0, ai) RETURNING * INTO ho;
                INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, tham_chieu_bang, tham_chieu_id, muc, trang_thai, nguoi_duyet_vai_tro, tom_tat, module)
                    VALUES (d.pn, 'V3', 'CRM_G6A', 'master.crm_kiem_ho_so', ho.id, 'VANG', 'CHO_DUYET', 'KE_TOAN',
                            'Kế toán kiểm hợp đồng đã ký ' || h.ma_noi_bo, 'CRM') RETURNING id INTO v_vid;
                UPDATE master.crm_kiem_ho_so SET viec_id = v_vid WHERE id = ho.id;
                ho.viec_id := v_vid;
            ELSIF ho.trang_thai NOT IN ('DANG_KIEM','CHO_BO_SUNG') THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: hồ sơ kiểm đã chốt (%)', ho.trang_thai USING ERRCODE = 'P0001';
            ELSIF p_expected <> ho.revision THEN
                RAISE EXCEPTION 'CRM_KIEM_REVISION_CU: hồ sơ kiểm đã có revision mới — tải lại rồi lưu' USING ERRCODE = 'P0001';
            END IF;
            v_cu := ho.trang_thai;
            INSERT INTO master.crm_kiem_rev (ho_so_id, ky_id, phap_nhan_id, revision, checklist, de_xuat_doi_tac_id, de_xuat_ma_junsky_id, ngay_hieu_luc,
                                             can_cu_ngay, trich_dan_ngay, ghi_chu, tao_boi)
                VALUES (ho.id, k.id, d.pn, ho.revision + 1, p_checklist, p_doi_tac, p_ma_junsky, p_ngay, p_can_cu, p_trich_dan, p_ghi_chu, ai)
                RETURNING id INTO v_rid;
            UPDATE master.crm_kiem_ho_so SET revision = ho.revision + 1, trang_thai = 'DANG_KIEM', cap_nhat_luc = clock_timestamp() WHERE id = ho.id;
            IF v_cu = 'CHO_BO_SUNG' THEN
                UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_DUYET', ly_do_cho = '{}', cap_nhat_luc = now() WHERE id = ho.viec_id AND trang_thai = 'CHO_BO_SUNG';
            END IF;
            """ + _G_NK.format(pn="d.pn", loai="'HE_THONG'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_LUU'",
                               sau="jsonb_build_object('ky_id', k.id, 'revision', ho.revision + 1, 'rev_id', v_rid)", ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id);""" + _G_KET.format(a="'CRM_KIEM_LUU'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_chay_check(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record; v_e jsonb; v_cid uuid;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_CHECK'") + """
            IF p_che_do IS NULL OR p_che_do NOT IN ('VAN_HANH','SYNTHETIC_FIXTURE') THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: chế độ G5 không hợp lệ' USING ERRCODE = 'P0001';
            END IF;""" + _KIEM_HO_SO.format(tt="('DANG_KIEM')") + """
            v_e := master.crm_kiem_danh_gia(p_ky, p_che_do);
            INSERT INTO master.crm_kiem_check (ho_so_id, ky_id, phap_nhan_id, rev_id, ho_so_revision, g5_che_do, do_thi, do_thi_sha256, chan, canh_bao,
                                               ket_luan, tao_boi)
                VALUES (ho.id, k.id, d.pn, (SELECT r.id FROM master.crm_kiem_rev r WHERE r.ho_so_id = ho.id AND r.revision = ho.revision), ho.revision,
                        p_che_do, v_e -> 'do_thi', v_e ->> 'sha256', v_e -> 'chan', v_e -> 'canh_bao', v_e ->> 'ket_luan', ai) RETURNING id INTO v_cid;
            """ + _G_NK.format(pn="d.pn", loai="'HE_THONG'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_CHECK'",
                               sau="jsonb_build_object('check_id', v_cid, 'ket_luan', v_e ->> 'ket_luan', 'do_thi_sha256', v_e ->> 'sha256', 'g5_che_do', p_che_do)",
                               ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id) || jsonb_build_object('check', jsonb_build_object(
                'check_id', v_cid, 'ho_so_revision', ho.revision, 'ket_luan', v_e ->> 'ket_luan', 'chan', v_e -> 'chan', 'canh_bao', v_e -> 'canh_bao',
                'do_thi_sha256', v_e ->> 'sha256', 'g5_che_do', p_che_do));""" + _G_KET.format(a="'CRM_KIEM_CHECK'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_xu_ly_lech(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_loai text, p_muc_tieu uuid,
                                                          p_ma text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record; v_xid uuid;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_XU_LY_LECH'") + _KIEM_LY_DO + """
            IF p_loai IS NULL OR p_loai NOT IN ('G5_LECH','G7_LECH') OR p_muc_tieu IS NULL OR p_ma IS NULL THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: thiếu loại/mục tiêu/mã lệch' USING ERRCODE = 'P0001';
            END IF;""" + _KIEM_HO_SO.format(tt="('DANG_KIEM')") + """
            IF EXISTS (SELECT 1 FROM master.crm_kiem_xu_ly_lech y WHERE y.ky_id = p_ky AND y.loai = p_loai AND y.muc_tieu_id = p_muc_tieu AND y.ma_lech = p_ma) THEN
                RAISE EXCEPTION 'CRM_KIEM_DA_XU_LY: lệch này đã có quyết định xử lý' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_kiem_xu_ly_lech (ky_id, ho_so_id, phap_nhan_id, ho_so_revision, loai, muc_tieu_id, ma_lech, quyet_dinh, ly_do, tao_boi)
                VALUES (k.id, ho.id, d.pn, ho.revision, p_loai, p_muc_tieu, p_ma, 'THEO_BAN_KY', p_ly_do, ai) RETURNING id INTO v_xid;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_XU_LY_LECH'",
                               sau="jsonb_build_object('xu_ly_id', v_xid, 'loai', p_loai, 'muc_tieu_id', p_muc_tieu, 'ma_lech', p_ma)", ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id) || jsonb_build_object('xu_ly_id', v_xid);""" + _G_KET.format(a="'CRM_KIEM_XU_LY_LECH'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_kiem_bo_sung(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_BO_SUNG'") + _KIEM_LY_DO + _KIEM_HO_SO.format(tt="('DANG_KIEM')") + """
            INSERT INTO master.crm_kiem_quyet_dinh (ky_id, ho_so_id, hop_dong_id, phap_nhan_id, loai, ho_so_revision, ly_do, tao_boi)
                VALUES (k.id, ho.id, k.hop_dong_id, d.pn, 'BO_SUNG', ho.revision, p_ly_do, ai);
            UPDATE master.crm_kiem_ho_so SET trang_thai = 'CHO_BO_SUNG', cap_nhat_luc = clock_timestamp() WHERE id = ho.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_BO_SUNG', ly_do_cho = ARRAY['CRM_G6A_BO_SUNG'], cap_nhat_luc = now() WHERE id = ho.viec_id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_BO_SUNG'",
                               sau="jsonb_build_object('revision', ho.revision)", ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id);""" + _G_KET.format(a="'CRM_KIEM_BO_SUNG'") + """
        END $$""",
    # trả lại: KHÔNG mở khóa/sửa bản ký/PDF G4, không "về nháp" — chỉ chặn phụ thuộc (quy trình ký lại = gói kế tiếp)
    """CREATE OR REPLACE FUNCTION master.crm_kiem_tra_lai(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_TRA_LAI'") + _KIEM_LY_DO + _KIEM_HO_SO.format(tt="('DANG_KIEM','CHO_BO_SUNG')") + """
            INSERT INTO master.crm_kiem_quyet_dinh (ky_id, ho_so_id, hop_dong_id, phap_nhan_id, loai, ho_so_revision, ly_do, tao_boi)
                VALUES (k.id, ho.id, k.hop_dong_id, d.pn, 'TRA_LAI', ho.revision, p_ly_do, ai);
            UPDATE master.crm_kiem_ho_so SET trang_thai = 'TRA_LAI_CHO_KY_LAI', cap_nhat_luc = clock_timestamp() WHERE id = ho.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_BO_SUNG', ly_do_cho = ARRAY['CRM_G6A_TRA_LAI_CHO_G4_KY_LAI'], cap_nhat_luc = now()
                WHERE id = ho.viec_id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_TRA_LAI'",
                               sau="jsonb_build_object('revision', ho.revision, 'phu_thuoc', 'CRM_G6A_TRA_LAI_CHO_G4_KY_LAI')", ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id) || jsonb_build_object('ket_qua', 'CHAN_PHU_THUOC', 'phu_thuoc', 'CRM_G6A_TRA_LAI_CHO_G4_KY_LAI',
                                                                  'g4_trang_thai', h.crm_giao_ket);""" + _G_KET.format(a="'CRM_KIEM_TRA_LAI'") + """
        END $$""",
    # kích hoạt HIEU_LUC — MỘT giao dịch: quyết định (đánh giá lại) → HĐ → chứng từ bản ký → phiên bản v1 → tham số → duyệt → con trỏ → lịch →
    # hoàn tất (kiểm lại toàn bộ) → hồ sơ → K5 → (G7 lệch) việc V8 CFO → nhật ký → biên nhận. Cùng check đã kích hoạt → trả lại đúng kết quả cũ.
    """CREATE OR REPLACE FUNCTION master.crm_kiem_hieu_luc(p_khoa text, p_h text, p_ky uuid, p_expected integer, p_check uuid, p_sha text,
                                                        p_che_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ k record; h record; ho record; c record; rv record; q record; mv record; v_qid uuid; v_ctid uuid; v_pbid uuid;
                v_hlid uuid; v_l jsonb; v_g7 jsonb; v_e jsonb; v_pin jsonb; v_nts integer;
        BEGIN""" + _KIEM_MO + _G_REPLAY.format(a="'CRM_KIEM_HIEU_LUC'") + """
            IF p_che_do IS NULL OR p_che_do NOT IN ('VAN_HANH','SYNTHETIC_FIXTURE') OR p_expected IS NULL OR p_check IS NULL
               OR p_sha IS NULL OR p_sha !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: thiếu revision/check/sha256 đồ thị/chế độ G5' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE ky_id = p_ky FOR UPDATE;
            SELECT * INTO q FROM master.crm_kiem_quyet_dinh WHERE ky_id = p_ky AND loai = 'HIEU_LUC';
            IF q.id IS NOT NULL THEN
                IF q.check_id = p_check AND q.do_thi_sha256 = p_sha AND q.g5_che_do = p_che_do THEN
                    RETURN jsonb_build_object('lap_lai', true, 'ket_qua', master.crm_kiem_kq(ho.id));  -- cùng check, khóa mới: 0 hàng mới
                END IF;
                RAISE EXCEPTION 'CRM_KIEM_DA_HIEU_LUC: hợp đồng đã kích hoạt theo lần check khác' USING ERRCODE = 'P0001';
            END IF;
            IF ho.id IS NULL OR ho.trang_thai <> 'DANG_KIEM' THEN
                RAISE EXCEPTION 'CRM_KIEM_TRANG_THAI: chỉ kích hoạt hồ sơ đang kiểm (hiện %)', coalesce(ho.trang_thai, 'CHUA_KIEM') USING ERRCODE = 'P0001';
            END IF;
            IF p_expected <> ho.revision THEN
                RAISE EXCEPTION 'CRM_KIEM_REVISION_CU: hồ sơ kiểm đã có revision mới — check lại' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO c FROM master.crm_kiem_check WHERE id = p_check;
            IF c.id IS NULL OR c.ky_id <> p_ky OR c.ho_so_revision <> ho.revision OR c.do_thi_sha256 <> p_sha OR c.g5_che_do <> p_che_do
               OR EXISTS (SELECT 1 FROM master.crm_kiem_check c2 WHERE c2.ho_so_id = ho.id AND c2.thu_tu > c.thu_tu) THEN
                RAISE EXCEPTION 'CRM_KIEM_CHECK_CU: lần check không còn là lần mới nhất của revision hiện hành — check lại' USING ERRCODE = 'P0001';
            END IF;
            IF c.ket_luan <> 'DU_DIEU_KIEN' THEN
                RAISE EXCEPTION 'CRM_KIEM_CHUA_DU_DIEU_KIEN: lần check còn mục chặn — chưa kích hoạt được' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO rv FROM master.crm_kiem_rev WHERE id = c.rev_id;
            SELECT pv.phien_ban, m.ma_mau INTO mv FROM master.crm_mau_phien_ban pv JOIN master.crm_mau m ON m.id = pv.mau_id WHERE pv.id = k.mau_phien_ban_id;
            INSERT INTO master.crm_kiem_quyet_dinh (ky_id, ho_so_id, hop_dong_id, phap_nhan_id, loai, ho_so_revision, check_id, rev_id, g5_che_do,
                                                    doi_tac_id, ma_junsky_id, ngay_hieu_luc, do_thi_sha256, tao_boi)
                VALUES (k.id, ho.id, k.hop_dong_id, d.pn, 'HIEU_LUC', ho.revision, c.id, rv.id, p_che_do, rv.de_xuat_doi_tac_id, rv.de_xuat_ma_junsky_id,
                        rv.ngay_hieu_luc, p_sha, ai) RETURNING id INTO v_qid;
            v_l := master.crm_kiem_lich_ky(p_ky);
            v_g7 := master.crm_kiem_g7(p_ky);
            UPDATE master.hop_dong SET crm_giao_ket = 'HIEU_LUC', trang_thai = 'HIEU_LUC', doi_tac_id = rv.de_xuat_doi_tac_id, ngay_ky = k.ngay_ky,
                                       gia_tri_minor = (v_l ->> 'tong_minor')::bigint, tien_te = v_l ->> 'tien_te'
                WHERE id = k.hop_dong_id;
            INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, doi_tac_id, du_an_id, mo_ta, du_lieu, hash)
                VALUES (d.pn, 'HOP_DONG_TEP', 'CRM_G6A:' || k.id::text, k.ngay_ky, v_l ->> 'tien_te', (v_l ->> 'tong_minor')::bigint, rv.de_xuat_doi_tac_id,
                        h.du_an_id, 'Bản ký hợp đồng ' || h.ma_noi_bo,
                        jsonb_build_object('nguon', 'CRM_G6A', 'ky_id', k.id, 'quyet_dinh_id', v_qid, 'ky_pdf_sha256', k.ky_pdf_sha256,
                                           'g3_pdf_sha256', k.g3_pdf_sha256, 'ky_pdf_len', k.ky_pdf_len), k.ky_pdf_sha256)
                RETURNING id INTO v_ctid;
            v_pin := jsonb_build_object(
                'profile', jsonb_build_object('ma', 'CRM_MAU:' || mv.ma_mau, 'phien_ban', k.profile_phien_ban, 'hash', k.profile_sha256),
                'crm_g6a', jsonb_build_object('ky_id', k.id, 'quyet_dinh_id', v_qid, 'check_id', c.id, 'do_thi_sha256', p_sha,
                                              'ky_pdf_sha256', k.ky_pdf_sha256, 'g3_pdf_sha256', k.g3_pdf_sha256, 'mau_phien_ban_id', k.mau_phien_ban_id,
                                              'phien_ban_mau', mv.phien_ban, 'danh_muc_digest', k.danh_muc_digest, 'g5_che_do', p_che_do,
                                              'g7', v_g7 ->> 'trang_thai'));
            INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, loai, ngay, tham_so, nguon, trang_thai, valid_from, ngay_hieu_luc, chung_tu_id,
                                                   loai_hinh_dt_id, tao_boi)
                VALUES (k.hop_dong_id, 1, 'GOC', k.ngay_ky, v_pin, 'CRM_MAU', 'CHO_DUYET', rv.ngay_hieu_luc::timestamp AT TIME ZONE 'UTC', rv.ngay_hieu_luc,
                        v_ctid, h.loai_hinh_dt_id, ai) RETURNING id INTO v_pbid;
            INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, gia_tri_so, don_vi, trich_dan, do_tin_cay, nguon, ma_nguon, nhom, truong,
                                                 gia_tri_tho, kieu, gia_tri_typed, vi_tri, kiem_tra_nguon, trang_thai_can_cu, chung_tu_id)
                SELECT v_pbid, t.ten, t.gia_tri, t.gia_tri_so, t.don_vi, t.trich_dan, 'MAU_DA_KY', 'CRM_MAU', t.ma_nguon, t.nhom, t.truong, t.gia_tri, t.kieu,
                       t.gia_tri_typed, t.vi_tri, t.kiem_tra_nguon, t.trang_thai_can_cu, v_ctid
                FROM master.crm_kiem_tham_so_ky(p_ky, rv.id) t;
            GET DIAGNOSTICS v_nts = ROW_COUNT;
            UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', kiem_boi = ai, kiem_luc = now(), kiem_van_tay = master.van_tay_phien_ban(v_pbid),
                                                 nguoi_duyet = ai, duyet_luc = now()
                WHERE id = v_pbid;
            UPDATE master.hop_dong SET phien_ban_hien_hanh = v_pbid WHERE id = k.hop_dong_id;
            FOR v_e IN SELECT x FROM jsonb_array_elements(v_l -> 'dong') x LOOP
                INSERT INTO master.lich_thu (phien_ban_id, phap_nhan_id, dot, moc, ty_le, so_tien_minor, tien_te, han, loai, khoa_nghia_vu, nguon_tham_so,
                                             co_so, ghi_chu)
                    VALUES (v_pbid, d.pn, (v_e ->> 'dot')::integer, v_e ->> 'moc', (v_e ->> 'ty_le')::numeric, (v_e ->> 'so_tien_minor')::bigint,
                            v_l ->> 'tien_te', (v_e ->> 'han')::date, 'DOT', 'CRM-DOT-' || (v_e ->> 'dot'), ARRAY['crm.lich'], 'CRM_MAU:BAN_KY',
                            'Lần ' || (v_e ->> 'lan'));
            END LOOP;
            INSERT INTO master.crm_kiem_hieu_luc (phap_nhan_id, quyet_dinh_id, ky_id, ho_so_id, hop_dong_id, phien_ban_id, chung_tu_id, so_dong_lich,
                                                  so_tham_so, tong_minor, tien_te, g7_trang_thai, g5_che_do, tao_boi)
                VALUES (d.pn, v_qid, k.id, ho.id, k.hop_dong_id, v_pbid, v_ctid, jsonb_array_length(v_l -> 'dong'), v_nts,
                        (v_l ->> 'tong_minor')::bigint, v_l ->> 'tien_te', v_g7 ->> 'trang_thai', p_che_do, ai) RETURNING id INTO v_hlid;
            UPDATE master.crm_kiem_ho_so SET trang_thai = 'HIEU_LUC', cap_nhat_luc = clock_timestamp() WHERE id = ho.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET', kiem_boi = ai, kiem_luc = now(), duyet_boi = ai, duyet_luc = now(), ly_do_cho = '{}',
                                          cap_nhat_luc = now()
                WHERE id = ho.viec_id;
            IF v_g7 ->> 'trang_thai' = 'LECH' THEN
                INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, tham_chieu_bang, tham_chieu_id, muc, trang_thai, nguoi_duyet_vai_tro, tom_tat,
                                                so_tien_minor, tien_te, module)
                    VALUES (d.pn, 'V8', 'CRM_G6A_G7', 'master.crm_kiem_hieu_luc', v_hlid, 'DO', 'CHO_DUYET', 'CFO',
                            'Hợp đồng ' || h.ma_noi_bo || ' hiệu lực theo bản ký lệch bộ chuẩn G7 — CFO xem xét', (v_l ->> 'tong_minor')::bigint,
                            v_l ->> 'tien_te', 'CRM');
            END IF;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_kiem_ho_so'", id="ho.id", hd="'CRM_KIEM_HIEU_LUC'",
                               sau="jsonb_build_object('ky_id', k.id, 'hop_dong_id', k.hop_dong_id, 'phien_ban_id', v_pbid, 'chung_tu_id', v_ctid, "
                                   "'do_thi_sha256', p_sha, 'g5_che_do', p_che_do, 'g7', v_g7 ->> 'trang_thai')", ly="NULL") + """
            kq := master.crm_kiem_kq(ho.id);""" + _G_KET.format(a="'CRM_KIEM_HIEU_LUC'") + """
        END $$""",
    # ======================================================================= K5 typed cho hai chủ thể G6A
    """CREATE OR REPLACE FUNCTION kho.crm_kiem_chu_the(p_bang text, p_id uuid) RETURNS TABLE (phap_nhan_id uuid, module text)
        LANGUAGE sql STABLE SET search_path = master, kho, pg_temp AS $$
        SELECT x.phap_nhan_id, 'CRM'::text FROM master.crm_kiem_ho_so x WHERE p_bang = 'master.crm_kiem_ho_so' AND x.id = p_id
        UNION ALL
        SELECT z.phap_nhan_id, 'CRM'::text FROM master.crm_kiem_hieu_luc z WHERE p_bang = 'master.crm_kiem_hieu_luc' AND z.id = p_id
        $$""",
    """CREATE OR REPLACE FUNCTION kho.crm_kiem_viec_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE v_cu boolean := false; v_moi boolean := false; ho record; x record; ai text := master.ktt_danh_tinh();
        BEGIN
            IF TG_OP <> 'INSERT' THEN v_cu := OLD.tham_chieu_bang IN """ + _KIEM_TYPED + """; END IF;
            IF TG_OP <> 'DELETE' THEN v_moi := NEW.tham_chieu_bang IN """ + _KIEM_TYPED + """; END IF;
            IF NOT (v_cu OR v_moi) THEN
                RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END IF;
            IF NOT master.la_chu_bang('kho.viec_can_duyet'::regclass) THEN
                RAISE EXCEPTION 'CRM_KIEM_VIEC_CHI_CHU: việc kiểm/CFO của G6A chỉ do lệnh G6A trên kết nối chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_KIEM_VIEC_BAT_BIEN: không xóa việc G6A' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(OLD.tham_chieu_bang, OLD.tham_chieu_id, OLD.phap_nhan_id, OLD.module, OLD.loai, OLD.nguoi_duyet_vai_tro)
                   IS DISTINCT FROM ROW(NEW.tham_chieu_bang, NEW.tham_chieu_id, NEW.phap_nhan_id, NEW.module, NEW.loai, NEW.nguoi_duyet_vai_tro) THEN
                    RAISE EXCEPTION 'CRM_KIEM_VIEC_BAT_BIEN: không đổi đích/PN/module/loại/vai của việc G6A' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai IN ('DA_DUYET','BO_QUA','DONG') THEN
                    RAISE EXCEPTION 'CRM_KIEM_VIEC_BAT_BIEN: việc G6A đã đóng — không mở lại/sửa' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.module IS DISTINCT FROM 'CRM' THEN
                RAISE EXCEPTION 'CRM_KIEM_VIEC_SAI: việc G6A phải thuộc module CRM' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.tham_chieu_bang = 'master.crm_kiem_ho_so' THEN
                SELECT * INTO ho FROM master.crm_kiem_ho_so WHERE id = NEW.tham_chieu_id AND phap_nhan_id = NEW.phap_nhan_id;
                IF ho.id IS NULL OR NEW.loai <> 'V3' OR NEW.nguoi_duyet_vai_tro IS DISTINCT FROM 'KE_TOAN' THEN
                    RAISE EXCEPTION 'CRM_KIEM_VIEC_SAI: việc kiểm G6A là V3 kế toán của đúng hồ sơ cùng pháp nhân' USING ERRCODE = 'P0001';
                END IF;
                IF NOT CASE NEW.trang_thai WHEN 'CHO_DUYET' THEN ho.trang_thai = 'DANG_KIEM'
                                           WHEN 'CHO_BO_SUNG' THEN ho.trang_thai IN ('CHO_BO_SUNG','TRA_LAI_CHO_KY_LAI')
                                           WHEN 'DA_DUYET' THEN ho.trang_thai = 'HIEU_LUC' AND NEW.duyet_boi IS NOT DISTINCT FROM ai
                                           ELSE false END THEN
                    RAISE EXCEPTION 'CRM_KIEM_VIEC_TRANG_THAI: trạng thái việc phải theo hồ sơ kiểm (% / %)', NEW.trang_thai, ho.trang_thai USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            SELECT * INTO x FROM master.crm_kiem_hieu_luc WHERE id = NEW.tham_chieu_id AND phap_nhan_id = NEW.phap_nhan_id;
            IF x.id IS NULL OR NEW.loai <> 'V8' OR NEW.nguoi_duyet_vai_tro IS DISTINCT FROM 'CFO' OR x.g7_trang_thai <> 'LECH'
               OR (TG_OP = 'INSERT' AND NEW.trang_thai <> 'CHO_DUYET') THEN
                RAISE EXCEPTION 'CRM_KIEM_VIEC_SAI: việc CFO G6A là V8 mở cho đúng kích hoạt lệch G7' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.trang_thai = 'DA_DUYET' AND (ai IS NULL OR NEW.duyet_boi IS DISTINCT FROM ai OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['CFO'], 'V8')) THEN
                RAISE EXCEPTION 'CRM_KIEM_VIEC_QUYEN: chỉ CFO có quyền V8 của phiên hiện tại đóng việc này' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_kiem_viec_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.viec_can_duyet FOR EACH ROW EXECUTE FUNCTION kho.crm_kiem_viec_kiem()",
    # Guard chủ thể K5 chung: bản sao NGUYÊN VĂN thân hiện hành (M0021) + MỘT nhánh INSERT typed G6A ngay sau nhánh typed CRM-G.
    # Integrator: đối chiếu thân hiện hành sau M4M24 trước khi append; khác → hợp nhất, không ghi đè.
    """CREATE OR REPLACE FUNCTION kho.viec_chu_so_huu() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE chu record; n integer;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF (NEW.module, NEW.tham_chieu_bang, NEW.tham_chieu_id, NEW.phap_nhan_id, NEW.loai) IS DISTINCT FROM
                   (OLD.module, OLD.tham_chieu_bang, OLD.tham_chieu_id, OLD.phap_nhan_id, OLD.loai) THEN
                    RAISE EXCEPTION 'VIEC_CHU_THE_BAT_BIEN: không đổi chủ thể/module/loại việc' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.tham_chieu_bang IN """ + _G_TYPED + """ THEN
                SELECT count(*) INTO n FROM kho.crm_g_chu_the(NEW.tham_chieu_bang, NEW.tham_chieu_id);
                SELECT * INTO chu FROM kho.crm_g_chu_the(NEW.tham_chieu_bang, NEW.tham_chieu_id);
                IF n <> 1 OR chu.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR chu.module IS DISTINCT FROM NEW.module THEN
                    RAISE EXCEPTION 'VIEC_CHU_THE_SAI: việc phải cùng pháp nhân/module với chủ thể' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.tham_chieu_bang IN """ + _KIEM_TYPED + """ THEN
                SELECT count(*) INTO n FROM kho.crm_kiem_chu_the(NEW.tham_chieu_bang, NEW.tham_chieu_id);
                SELECT * INTO chu FROM kho.crm_kiem_chu_the(NEW.tham_chieu_bang, NEW.tham_chieu_id);
                IF n <> 1 OR chu.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR chu.module IS DISTINCT FROM NEW.module THEN
                    RAISE EXCEPTION 'VIEC_CHU_THE_SAI: việc phải cùng pháp nhân/module với chủ thể' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.tham_chieu_bang NOT IN ('master.hop_dong','master.hop_dong_phien_ban','kho.chung_tu','kho.de_xuat','master.anh_xa_nguon') THEN
                IF coalesce(NEW.module, 'M1') IN ('CRM','M9') THEN
                    RAISE EXCEPTION 'VIEC_CHU_THE_LA: loại chủ thể % không thuộc allowlist', NEW.tham_chieu_bang USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            SELECT count(*) INTO n FROM kho.kiem_chu_so_huu_noi_bo(NEW.tham_chieu_bang, NEW.tham_chieu_id);
            SELECT * INTO chu FROM kho.kiem_chu_so_huu_noi_bo(NEW.tham_chieu_bang, NEW.tham_chieu_id);
            IF n <> 1 OR chu.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR chu.module IS DISTINCT FROM coalesce(NEW.module, 'M1') THEN
                RAISE EXCEPTION 'VIEC_CHU_THE_SAI: việc phải cùng pháp nhân/module với chủ thể' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # đọc việc G6A: chỉ phiên có phạm vi kiểm hiện hành (hoặc CFO V8 với việc CFO) — áp mọi trạng thái
    """CREATE OR REPLACE FUNCTION master.crm_kiem_viec_doc_duoc(p_bang text, p_id uuid, p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT CASE WHEN p_bang = 'master.crm_kiem_ho_so' THEN
                        coalesce((SELECT master.crm_kiem_pham_vi_duoc(x.ky_id) FROM master.crm_kiem_ho_so x WHERE x.id = p_id AND x.phap_nhan_id = p_pn), false)
                    WHEN p_bang = 'master.crm_kiem_hieu_luc' THEN
                        coalesce((SELECT master.crm_kiem_pham_vi_duoc(z.ky_id)
                                         OR (master.ktt_duoc(p_pn, 'CRM') AND master.ktt_co_vai(p_pn, ARRAY['CFO'], 'V8'))
                                  FROM master.crm_kiem_hieu_luc z WHERE z.id = p_id AND z.phap_nhan_id = p_pn), false)
                    ELSE true END
        $$""",
    """CREATE POLICY viec_can_duyet_crm_kiem_doc ON kho.viec_can_duyet AS RESTRICTIVE FOR SELECT TO PUBLIC
        USING (tham_chieu_bang NOT IN """ + _KIEM_TYPED + """ OR master.crm_kiem_viec_doc_duoc(tham_chieu_bang, tham_chieu_id, phap_nhan_id))""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm không cấp PUBLIC
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _KIEM_BANG_MOI),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON """ + ", ".join(f"master.{t}" for t in _KIEM_BANG_MOI) + """ FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    "REVOKE ALL ON " + ", ".join(f"master.{t}" for t in _KIEM_BANG_MOI) + " FROM PUBLIC",
    """DO $$
    DECLARE f regprocedure;
    BEGIN
        FOR f IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname IN ('master','kho') AND p.proname LIKE 'crm\\_kiem\\_%' LOOP
            EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', f);
        END LOOP;
    END $$""",
    # P1-A: policy RESTRICTIVE trên kho.viec_can_duyet (TO PUBLIC) gọi helper đọc này bằng quyền của LOGIN ĐANG ĐỌC → vai ứng dụng CÓ SẴN phải có
    # EXECUTE riêng helper (chỉ trả boolean theo danh tính/PN/phạm vi hiện hành của chính phiên). KHÔNG cấp PUBLIC, không cấp hàm lệnh/ghi/kích hoạt,
    # không cấp bảng mới, không tạo vai; vai không tồn tại thì bỏ qua.
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('GRANT EXECUTE ON FUNCTION master.crm_kiem_viec_doc_duoc(text, uuid, uuid) TO %I', r);
            END IF;
        END LOOP;
    END $$""",
)
