"""M4-DL1 — bổ sung chứng cứ nguồn Review SQLite (CD-011). Chỉ hằng SQL.

Ánh xạ: hop_dong dùng NGUYÊN master.hop_dong + m4.ho_so_hop_dong; các cột
review_* của hồ sơ giữ bản nguồn, không thay tiền minor/ngày chuẩn hóa của master.
11 bảng còn lại là phần bổ sung lịch sử chưa có ngữ nghĩa tương đương đầy đủ:
tham_so không đòi trich_xuat/catalog; phu_luc không đoán ngày/actor hủy;
boq_dong không tạo lần nhập/tệp giả; dot_thanh_toan không tạo seal/DA_NOP;
khop_hang_muc/canh_bao không tạo review_run; nhat_ky không đoán timezone/JSON.
Các con trỏ m4_* tái dùng bản ghi vận hành nếu đã có, FK kiểm đúng HĐ/dự án.
Không lập master HĐ/BOQ/run/log vận hành thứ hai để chứa dữ liệu nguồn.

Khóa nguồn = nguon_id ổn định do người nhập khai + PK SQLite, KHÔNG dùng SHA
file DB (thay đổi sau mỗi lần cập nhật). dong_sha256 là hash từng dòng cho DL2/
công cụ import so sánh; bản nguồn bất biến, dòng đổi cần lịch sử/audit ở lát sau,
không ON CONFLICT DO UPDATE. Không chép che_do.sua thành quyền ứng dụng.
REAL -> double precision (binary64 như SQLite); INTEGER -> bigint; ngày/JSON
nguồn vẫn TEXT, giữ NULL/rỗng/âm. Không ép tiền VND sang BIGINT minor.
Các FK nguồn có thật được giữ; cảnh báo/nhật ký/ghép nguồn không có FK ma_hd
thì không tự thêm, tránh mất log orphan. Dòng không rõ dự án chỉ chủ bảng đọc.
"""

BANG_NGUON = (
    "che_do", "hop_dong", "tham_so", "phu_luc", "thay_doi_tham_so",
    "boq_dong", "dot_thanh_toan", "kl_thanh_toan", "khop_hang_muc",
    "canh_bao", "nhat_ky", "tham_so_nguon",
)
BANG_BO_SUNG = ("review_chep_nguon", *("review_chep_" + t for t in BANG_NGUON if t != "hop_dong"))
_HASH = "text NOT NULL CHECK (dong_sha256 ~ '^[0-9a-f]{64}$')"
# HĐ/PN/dự án được chỉ định rõ qua hồ sơ đang có; không suy từ chuỗi nguồn.
_HD = """nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        ma_hd text NOT NULL,
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,"""
_FK_HD = """FOREIGN KEY (nguon_id, ma_hd, hop_dong_id, du_an_id)
        REFERENCES m4.ho_so_hop_dong (review_nguon_id, review_ma_hd, hop_dong_id, du_an_id)"""
_CHUNG = f"""chep_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
        dong_sha256 {_HASH},
        nhap_boi text NOT NULL,
        nhap_luc timestamptz NOT NULL DEFAULT now(),"""

M4_REVIEW_CHEP_SQL = (
    """CREATE TABLE m4.review_chep_nguon (
        id text PRIMARY KEY CHECK (length(btrim(id)) > 0),
        mo_ta text,
        nhap_boi text NOT NULL,
        nhap_luc timestamptz NOT NULL DEFAULT now())""",
    # Không đổi định nghĩa/constraint cũ: phần typed nguyên bản gắn hồ sơ có sẵn.
    """ALTER TABLE m4.ho_so_hop_dong
        ADD COLUMN review_nguon_id text REFERENCES m4.review_chep_nguon(id),
        ADD COLUMN review_ma_hd text,
        ADD COLUMN review_so_hd text,
        ADD COLUMN review_phan_loai text,
        ADD COLUMN review_loai_gia text,
        ADD COLUMN review_ngay_ky text,
        ADD COLUMN review_goi_thau text,
        ADD COLUMN review_gia_tri_hd double precision,
        ADD COLUMN review_gom_vat text,
        ADD COLUMN review_vat double precision,
        ADD COLUMN review_file_nguon text,
        ADD COLUMN review_ngay_nap text,
        ADD COLUMN review_dong_sha256 text,
        ADD COLUMN review_nhap_boi text,
        ADD COLUMN review_nhap_luc timestamptz,
        ADD CONSTRAINT ho_so_review_nguon_ck CHECK (
            (review_nguon_id IS NOT NULL AND review_ma_hd IS NOT NULL AND review_so_hd IS NOT NULL
             AND review_dong_sha256 IS NOT NULL AND review_dong_sha256 ~ '^[0-9a-f]{64}$'
             AND review_nhap_boi IS NOT NULL AND review_nhap_luc IS NOT NULL)
            OR (review_nguon_id IS NULL AND review_ma_hd IS NULL AND review_so_hd IS NULL
                AND review_phan_loai IS NULL AND review_loai_gia IS NULL AND review_ngay_ky IS NULL
                AND review_goi_thau IS NULL AND review_gia_tri_hd IS NULL AND review_gom_vat IS NULL
                AND review_vat IS NULL AND review_file_nguon IS NULL AND review_ngay_nap IS NULL
                AND review_dong_sha256 IS NULL AND review_nhap_boi IS NULL AND review_nhap_luc IS NULL)),
        ADD CONSTRAINT ho_so_review_ma_uq UNIQUE (review_nguon_id, review_ma_hd),
        ADD CONSTRAINT ho_so_review_so_uq UNIQUE (review_nguon_id, review_so_hd),
        ADD CONSTRAINT ho_so_review_pham_vi_uq UNIQUE (review_nguon_id, review_ma_hd, hop_dong_id, du_an_id)""",
    """CREATE FUNCTION m4.review_chep_hd_bat_bien() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
        BEGIN
            IF OLD.review_nguon_id IS NOT NULL AND
               (SELECT jsonb_object_agg(key, value) FROM jsonb_each(to_jsonb(OLD)) WHERE left(key, 7) = 'review_')
               IS DISTINCT FROM
               (SELECT jsonb_object_agg(key, value) FROM jsonb_each(to_jsonb(NEW)) WHERE left(key, 7) = 'review_') THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không sửa bản nguồn hợp đồng Review' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER ho_so_review_bat_bien BEFORE UPDATE ON m4.ho_so_hop_dong FOR EACH ROW EXECUTE FUNCTION m4.review_chep_hd_bat_bien()",
    f"""CREATE TABLE m4.review_chep_che_do (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        id bigint NOT NULL CHECK (id = 1), sua bigint NOT NULL DEFAULT 0,
        {_CHUNG}
        PRIMARY KEY (nguon_id, id))""",
    f"""CREATE TABLE m4.review_chep_tham_so (
        {_HD}
        ma_ts text NOT NULL, ten text, gia_tri text, don_vi text,
        dieu_khoan text, trich_dan text, trang_thai text,
        m4_ma text CHECK (m4_ma = ma_ts),
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, ma_ts), {_FK_HD},
        FOREIGN KEY (hop_dong_id, m4_ma) REFERENCES m4.tham_so (hop_dong_id, ma))""",
    f"""CREATE TABLE m4.review_chep_phu_luc (
        {_HD}
        id bigint NOT NULL, so_pl text NOT NULL,
        ngay_ky text NOT NULL, ngay_hieu_luc text NOT NULL,
        loai text, doi_boq bigint NOT NULL,
        gt_truoc_vat double precision, gt_sau_vat double precision, gt_hd_sau_pl double precision,
        noi_dung text, can_cu text, file_nguon text, phieu text,
        trang_thai text NOT NULL, nguoi_nhap text, ngay_nap text, ly_do_huy text,
        m4_phu_luc_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, id),
        UNIQUE (nguon_id, id, du_an_id),
        UNIQUE (nguon_id, id, ma_hd, hop_dong_id, du_an_id), {_FK_HD},
        FOREIGN KEY (m4_phu_luc_id, hop_dong_id) REFERENCES m4.phu_luc (id, hop_dong_id))""",
    "CREATE UNIQUE INDEX review_chep_phu_luc_so_uq ON m4.review_chep_phu_luc (nguon_id, ma_hd, so_pl) WHERE trang_thai <> 'Đã hủy'",
    f"""CREATE TABLE m4.review_chep_thay_doi_tham_so (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        pl_id bigint NOT NULL,
        du_an_id uuid NOT NULL,
        ma_ts text NOT NULL, gia_tri_cu text, gia_tri_moi text, trich_dan text,
        {_CHUNG}
        PRIMARY KEY (nguon_id, pl_id, ma_ts),
        FOREIGN KEY (nguon_id, pl_id, du_an_id) REFERENCES m4.review_chep_phu_luc (nguon_id, id, du_an_id))""",
    # Các UNIQUE bổ sung chỉ là khóa đích cho FK, không thay khóa/ngữ nghĩa cũ.
    "ALTER TABLE m4.boq ADD CONSTRAINT boq_review_hd_uq UNIQUE (id, hop_dong_id)",
    "ALTER TABLE m4.boq_dong ADD CONSTRAINT boq_dong_review_du_an_uq UNIQUE (boq_id, dong, du_an_id)",
    f"""CREATE TABLE m4.review_chep_boq_dong (
        {_HD}
        id bigint NOT NULL, pl_id bigint,
        thao_tac text NOT NULL CHECK (thao_tac IN ('GOC','THAY','THEM','BO')),
        ma_hm text NOT NULL, stt text, nhom text, ten text, dvt text,
        kl double precision, don_gia double precision, thanh_tien_ghi double precision,
        khoa text, vi_tri_nguon text, ghi_chu text, ma_rieng text,
        m4_boq_id uuid, m4_dong integer,
        {_CHUNG}
        PRIMARY KEY (nguon_id, id), {_FK_HD},
        FOREIGN KEY (nguon_id, pl_id, ma_hd, hop_dong_id, du_an_id)
            REFERENCES m4.review_chep_phu_luc (nguon_id, id, ma_hd, hop_dong_id, du_an_id),
        CHECK ((m4_boq_id IS NULL) = (m4_dong IS NULL)),
        FOREIGN KEY (m4_boq_id, hop_dong_id) REFERENCES m4.boq (id, hop_dong_id),
        FOREIGN KEY (m4_boq_id, m4_dong, du_an_id) REFERENCES m4.boq_dong (boq_id, dong, du_an_id))""",
    # Giữ cả va chạm pl_id=0 với NULL của IFNULL SQLite; không chỉ UQ có NULL.
    "CREATE UNIQUE INDEX review_chep_boq_hm_uq ON m4.review_chep_boq_dong (nguon_id, ma_hd, coalesce(pl_id, 0), ma_hm)",
    "ALTER TABLE m4.dot ADD CONSTRAINT dot_review_hd_du_an_uq UNIQUE (id, hop_dong_id, du_an_id)",
    f"""CREATE TABLE m4.review_chep_dot_thanh_toan (
        {_HD}
        dot bigint NOT NULL, ngay_nghiem_thu text, ngay_nhan_hs text,
        gt_ky double precision, gt_luy_ke double precision, giu_lai double precision,
        thu_hoi_tu double precision, gt_tt_ky double precision, file_nguon text, ngay_nap text,
        m4_dot_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, dot),
        UNIQUE (nguon_id, ma_hd, dot, du_an_id), {_FK_HD},
        FOREIGN KEY (m4_dot_id, hop_dong_id, du_an_id) REFERENCES m4.dot (id, hop_dong_id, du_an_id))""",
    f"""CREATE TABLE m4.review_chep_kl_thanh_toan (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        ma_hd text NOT NULL, dot bigint NOT NULL, ma_hm text NOT NULL,
        du_an_id uuid NOT NULL,
        kl_ky double precision, kl_luy_ke double precision, don_gia_tt double precision, vi_tri_nguon text,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, dot, ma_hm),
        FOREIGN KEY (nguon_id, ma_hd, dot, du_an_id)
            REFERENCES m4.review_chep_dot_thanh_toan (nguon_id, ma_hd, dot, du_an_id))""",
    "ALTER TABLE m4.review_manual_map ADD CONSTRAINT review_map_chep_hd_du_an_uq UNIQUE (id, hop_dong_id, du_an_id)",
    f"""CREATE TABLE m4.review_chep_khop_hang_muc (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        ma_hd text NOT NULL, khoa_hstt text NOT NULL, ma_hm text NOT NULL,
        cach_khop text, nguoi_xac_nhan text, ngay text,
        hop_dong_id uuid, du_an_id uuid, m4_map_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, khoa_hstt),
        {_FK_HD},
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id) MATCH FULL,
        CHECK (m4_map_id IS NULL OR hop_dong_id IS NOT NULL),
        FOREIGN KEY (m4_map_id, hop_dong_id, du_an_id) REFERENCES m4.review_manual_map (id, hop_dong_id, du_an_id))""",
    "ALTER TABLE m4.review_run ADD CONSTRAINT review_run_chep_hd_du_an_uq UNIQUE (id, hop_dong_id, du_an_id)",
    f"""CREATE TABLE m4.review_chep_canh_bao (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        id bigint NOT NULL, ma_hd text, pl_id bigint, dot bigint,
        ma_kt text, muc_do text, noi_dung text, thoi_diem text,
        hop_dong_id uuid, du_an_id uuid, m4_run_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, id),
        {_FK_HD},
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id) MATCH FULL,
        CHECK (hop_dong_id IS NULL OR ma_hd IS NOT NULL),
        CHECK (m4_run_id IS NULL OR hop_dong_id IS NOT NULL),
        FOREIGN KEY (m4_run_id, hop_dong_id, du_an_id) REFERENCES m4.review_run (id, hop_dong_id, du_an_id))""",
    "ALTER TABLE m4.nhat_ky ADD CONSTRAINT nhat_ky_review_du_an_uq UNIQUE (id, du_an_id)",
    f"""CREATE TABLE m4.review_chep_nhat_ky (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        id bigint NOT NULL, thoi_diem text, nguoi text, thao_tac text, ma_hd text, chi_tiet text,
        hop_dong_id uuid, du_an_id uuid, m4_nhat_ky_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, id),
        {_FK_HD},
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id) MATCH FULL,
        CHECK (hop_dong_id IS NULL OR ma_hd IS NOT NULL),
        CHECK (m4_nhat_ky_id IS NULL OR du_an_id IS NOT NULL),
        FOREIGN KEY (m4_nhat_ky_id, du_an_id) REFERENCES m4.nhat_ky (id, du_an_id))""",
    f"""CREATE TABLE m4.review_chep_tham_so_nguon (
        {_HD}
        ma_ts text NOT NULL, gia_tri_ai text, gia_tri text, kiem_tra text, muc bigint, nguon text,
        da_xac_nhan bigint NOT NULL DEFAULT 0, da_sua_tay bigint NOT NULL DEFAULT 0,
        nguoi_xac_nhan text, luc_xac_nhan text, ghi_chu_soat text, lich_su text,
        model text, may_ai text, luot text, file_hop_dong text, sha1_file text, luc_trich text, luc_nap text,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, ma_ts), {_FK_HD})""",
    # Không grant ghi, không SECURITY DEFINER cho import. Chỉ kết nối chủ bảng
    # tin cậy ghi được; không nhận cờ sửa/GUC làm đường vượt quyền.
    "REVOKE EXECUTE ON FUNCTION m4.review_chep_hd_bat_bien() FROM PUBLIC",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in BANG_BO_SUNG),
    *(f"CREATE TRIGGER {t}_chan_truncate BEFORE TRUNCATE ON m4.{t} FOR EACH STATEMENT EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in BANG_BO_SUNG),
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG_BO_SUNG),
    "REVOKE ALL ON " + ", ".join("m4." + t for t in BANG_BO_SUNG) + " FROM PUBLIC",
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            REVOKE EXECUTE ON FUNCTION m4.review_chep_hd_bat_bien() FROM app_web;
            REVOKE ALL ON """ + ", ".join("m4." + t for t in BANG_BO_SUNG) + """ FROM app_web;
        END IF;
    END $$""",
    # Nguồn/cờ sửa không có phạm vi dự án: owner-only. Lịch sử đợt chưa nộp
    # chỉ XEM, không cho REVIEW đọc như đợt đã nộp. Thu hồi quyền có hiệu lực ngay.
    *(f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON m4.{t} TO app_web;
            CREATE POLICY {t}_web ON m4.{t} FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM'));
        END IF;
    END $$""" for t in BANG_BO_SUNG if t not in ("review_chep_nguon", "review_chep_che_do")),
)
