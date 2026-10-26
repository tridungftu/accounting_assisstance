"""M4-DL1 — bổ sung chứng cứ nguồn Review SQLite (CD-011). Chỉ hằng SQL.

Ánh xạ: master.hop_dong + m4.ho_so_hop_dong giữ hồ sơ vận hành;
review_chep_hop_dong giữ bản nguồn riêng, không thêm review_* vào hồ sơ.
11 bảng còn lại là phần bổ sung lịch sử chưa có ngữ nghĩa tương đương đầy đủ:
tham_so không đòi trich_xuat/catalog; phu_luc không đoán ngày/actor hủy;
boq_dong không tạo lần nhập/tệp giả; dot_thanh_toan không tạo seal/DA_NOP;
khop_hang_muc/canh_bao không tạo review_run; nhat_ky không đoán timezone/JSON.
Các con trỏ m4_* tái dùng bản ghi vận hành nếu đã có, FK kiểm đúng HĐ/dự án.
Không lập master HĐ/BOQ/run/log vận hành thứ hai để chứa dữ liệu nguồn.

Mỗi nguon_id là MỘT lần chụp đầy đủ (một lần chạy công cụ), không phải mã kho
SQLite cố định; lần chạy sau dùng nguon_id mới. Khóa mọi bảng chép là
(nguon_id, PK SQLite); dòng sửa/xóa/id dùng lại ở lần sau không đè lần trước.
Replay cùng lần chụp chỉ ON CONFLICT DO NOTHING sau khi đối chiếu dong_sha256;
không dùng SHA file DB làm khóa, không ON CONFLICT DO UPDATE.
Công cụ nạp toàn bộ lần chụp trong một transaction; nguon.chup_luc là thời
điểm chụp tệp nguồn do công cụ nạp truyền vào, bắt buộc và không có DEFAULT.
nguon.nhap_luc chỉ là thời điểm nạp, có thể khác thứ tự khi nạp bù bản cũ.
Mỗi lần chụp là bản sao đủ của CÙNG MỘT CSDL Review. Bản hiện hành của HĐ:
m4.review_chep_hien_hanh(:hop_dong_id) chọn lần chụp mới nhất TOÀN BỘ trước
(ORDER BY n.chup_luc DESC, n.id DESC LIMIT 1), rồi kiểm HĐ trong lần chụp đó.
HĐ vắng mặt trả NULL (đã xóa ở nguồn), không lùi về lần chụp cũ hơn có HĐ.
Sau đó lấy bảng con với nguon_id đó và khóa HĐ tương ứng (qua PL/đợt nếu cần);
không chọn dòng mới nhất riêng từng khóa. Hàm đọc theo quyền/RLS của bên gọi;
bảng nguồn vẫn chỉ chủ bảng đọc, không mở thêm quyền cho app_web.
Cần Anh: nếu có nhiều CSDL Review (ví dụ mỗi pháp nhân một tệp), cần chốt
cột phân biệt nguồn trước khi dùng quy tắc mới nhất toàn bộ; chưa tự thêm.
DL2: DTO chỉ xuất định danh tệp được quản lý, không lộ file_nguon/đường dẫn.
Điều kiện trước khi nạp: người chốt bảng ánh xạ ma_hd → master.hop_dong /
pháp nhân / dự án; không suy từ chuỗi nguồn. Không chép che_do.sua thành quyền.
REAL -> numeric: công cụ nạp truyền Decimal(repr(x)), giữ NULL; không truyền
float trực tiếp hoặc ép tiền VND sang BIGINT minor. INTEGER -> bigint;
ngày/JSON nguồn vẫn TEXT, giữ NULL/rỗng/âm.
Các FK nguồn có thật được giữ; cảnh báo/nhật ký/ghép nguồn không có FK ma_hd
thì không tự thêm, tránh mất log orphan. Dòng không rõ dự án chỉ chủ bảng đọc.
"""

BANG_NGUON = (
    "che_do", "hop_dong", "tham_so", "phu_luc", "thay_doi_tham_so",
    "boq_dong", "dot_thanh_toan", "kl_thanh_toan", "khop_hang_muc",
    "canh_bao", "nhat_ky", "tham_so_nguon",
)
BANG_BO_SUNG = ("review_chep_nguon", *("review_chep_" + t for t in BANG_NGUON))
_BANG_REVIEW = (
    "review_chep_hop_dong", "review_chep_tham_so", "review_chep_phu_luc",
    "review_chep_thay_doi_tham_so", "review_chep_boq_dong", "review_chep_tham_so_nguon",
)
_HASH = "text NOT NULL CHECK (dong_sha256 ~ '^[0-9a-f]{64}$')"
# HĐ/PN/dự án được chỉ định rõ qua hồ sơ đang có; không suy từ chuỗi nguồn.
_HD = """nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        ma_hd text NOT NULL,
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,"""
_FK_HD = """FOREIGN KEY (nguon_id, ma_hd, hop_dong_id, du_an_id)
        REFERENCES m4.review_chep_hop_dong (nguon_id, ma_hd, hop_dong_id, du_an_id)"""
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
    f"""CREATE TABLE m4.review_chep_hop_dong (
        {_HD}
        so_hd text NOT NULL, phan_loai text, loai_gia text, ngay_ky text,
        goi_thau text, gia_tri_hd numeric, gom_vat text, vat numeric,
        file_nguon text, ngay_nap text,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd),
        UNIQUE (nguon_id, so_hd),
        UNIQUE (nguon_id, ma_hd, hop_dong_id, du_an_id),
        FOREIGN KEY (hop_dong_id, du_an_id)
            REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id))""",
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
        gt_truoc_vat numeric, gt_sau_vat numeric, gt_hd_sau_pl numeric,
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
        kl numeric, don_gia numeric, thanh_tien_ghi numeric,
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
        gt_ky numeric, gt_luy_ke numeric, giu_lai numeric,
        thu_hoi_tu numeric, gt_tt_ky numeric, file_nguon text, ngay_nap text,
        m4_dot_id uuid,
        {_CHUNG}
        PRIMARY KEY (nguon_id, ma_hd, dot),
        UNIQUE (nguon_id, ma_hd, dot, du_an_id), {_FK_HD},
        FOREIGN KEY (m4_dot_id, hop_dong_id, du_an_id) REFERENCES m4.dot (id, hop_dong_id, du_an_id))""",
    f"""CREATE TABLE m4.review_chep_kl_thanh_toan (
        nguon_id text NOT NULL REFERENCES m4.review_chep_nguon(id),
        ma_hd text NOT NULL, dot bigint NOT NULL, ma_hm text NOT NULL,
        du_an_id uuid NOT NULL,
        kl_ky numeric, kl_luy_ke numeric, don_gia_tt numeric, vi_tri_nguon text,
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
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in BANG_BO_SUNG),
    *(f"CREATE TRIGGER {t}_chan_truncate BEFORE TRUNCATE ON m4.{t} FOR EACH STATEMENT EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in BANG_BO_SUNG),
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG_BO_SUNG),
    "REVOKE ALL ON " + ", ".join("m4." + t for t in BANG_BO_SUNG) + " FROM PUBLIC",
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            REVOKE ALL ON """ + ", ".join("m4." + t for t in BANG_BO_SUNG) + """ FROM app_web;
        END IF;
    END $$""",
    # Nguồn/cờ sửa không có phạm vi dự án: owner-only. Lịch sử đợt chưa nộp
    # chỉ XEM, không cho REVIEW đọc như đợt đã nộp. Thu hồi quyền có hiệu lực ngay.
    # HĐ/tham số/phụ lục/BOQ theo mẫu XEM OR REVIEW của M4; bảng khác chỉ XEM.
    *(f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON m4.{t} TO app_web;
            CREATE POLICY {t}_web ON m4.{t} FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM'){" OR master.m4_duoc(du_an_id, 'REVIEW')" if t in _BANG_REVIEW else ''});
        END IF;
    END $$""" for t in BANG_BO_SUNG if t not in ("review_chep_nguon", "review_chep_che_do")),
)

# M4-DL1b — CD-011: chỉ bổ sung, giữ nguyên toàn bộ SQL M0038 bên trên.
M4_REVIEW_CHEP_B_SQL = (
    # Giữ khóa tới hết transaction migration, không cho INSERT chen giữa kiểm
    # rỗng và ADD NOT NULL; tuyệt đối không suy thời điểm chụp từ nhap_luc.
    """DO $$
    BEGIN
        LOCK TABLE m4.review_chep_nguon IN ACCESS EXCLUSIVE MODE;
        IF EXISTS (SELECT 1 FROM m4.review_chep_nguon) THEN
            RAISE EXCEPTION 'M4_REVIEW_CHEP_B_NGUON_DA_CO_DONG: bảng nguồn đã có dòng; cần chốt chup_luc của tệp nguồn trước khi nâng lược đồ, không tự điền thời điểm chụp';
        END IF;
    END $$""",
    "ALTER TABLE m4.review_chep_hop_dong ADD CONSTRAINT review_chep_hop_dong_nguon_hd_uq UNIQUE (nguon_id, hop_dong_id)",
    "ALTER TABLE m4.review_chep_nguon ADD COLUMN chup_luc timestamptz NOT NULL",
    "CREATE INDEX review_chep_nguon_chup_idx ON m4.review_chep_nguon (chup_luc DESC, id DESC)",
    """CREATE FUNCTION m4.review_chep_hien_hanh(p_hop_dong_id uuid)
    RETURNS text
    LANGUAGE sql STABLE SECURITY INVOKER
    AS $$
        SELECT n.id FROM (
            SELECT n.id FROM m4.review_chep_nguon n
            ORDER BY n.chup_luc DESC, n.id DESC LIMIT 1
        ) n
        WHERE EXISTS (
            SELECT 1 FROM m4.review_chep_hop_dong h
            WHERE h.nguon_id = n.id AND h.hop_dong_id = p_hop_dong_id
        )
    $$""",
)
