"""Migration PostgreSQL cho lớp dữ liệu V13 — theo tài liệu 38 (schema master · kho · nhat_ky · bao_mat).

Quy ước: mỗi phần tử của PG_MIGRATIONS là một nhóm câu lệnh chạy trong một giao dịch,
có checksum ghi vào master.schema_migrations (như database.py với SQLite). Không ORM.
Tên bảng/trường tiếng Việt không dấu, snake_case. Tiền: *_minor BIGINT + tien_te.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 0001 — schema, mở rộng, pháp nhân, bảng hệ thống
# ---------------------------------------------------------------------------
M0001 = (
    "CREATE SCHEMA IF NOT EXISTS master",
    "CREATE SCHEMA IF NOT EXISTS kho",
    "CREATE SCHEMA IF NOT EXISTS nhat_ky",
    "CREATE SCHEMA IF NOT EXISTS bao_mat",
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    """CREATE TABLE master.phap_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ma text NOT NULL UNIQUE,
        ten text NOT NULL,
        mst text,
        ma_don_vi_junsky text UNIQUE,
        che_do_ke_toan text NOT NULL DEFAULT 'TT200',
        nam_tai_chinh text NOT NULL DEFAULT 'DUONG_LICH',
        tien_te char(3) NOT NULL DEFAULT 'VND',
        bi_danh_ai text,
        moc_hoc date,
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG',
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE master.phap_nhan_boi_canh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        muc smallint NOT NULL CHECK (muc BETWEEN 0 AND 13),
        tieu_de text,
        noi_dung text,
        noi_dung_json jsonb,
        gui_ai boolean NOT NULL DEFAULT true,
        nguon text,
        nguoi_duyet text,
        duyet_luc timestamptz,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, muc, phien_ban))""",
    """CREATE TABLE master.cau_hinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        khoa text NOT NULL,
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        gia_tri jsonb NOT NULL,
        mo_ta text,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        nguoi_duyet text,
        UNIQUE NULLS NOT DISTINCT (khoa, phap_nhan_id, valid_from))""",
    """CREATE TABLE master.nguoi_dung (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ten text NOT NULL,
        dang_nhap text NOT NULL UNIQUE,
        vai_tro text NOT NULL CHECK (vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG','CFO','NHAP_JUNSKY','XEM')),
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG')""",
    """CREATE TABLE master.phan_quyen (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        duyet_loai_viec text[] NOT NULL DEFAULT '{}',
        UNIQUE (nguoi_dung_id, phap_nhan_id))""",
    """CREATE TABLE master.nguon_tu_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai IN ('HOA_DON_7','BASE_8','REVIEW_5','SHEET_VAY_9','THU_MUC_SAO_KE')),
        cau_hinh jsonb NOT NULL DEFAULT '{}'::jsonb,
        lich text,
        lan_cuoi timestamptz,
        so_moi integer NOT NULL DEFAULT 0,
        trang_thai text NOT NULL DEFAULT 'TAT',
        UNIQUE (phap_nhan_id, loai))""",
)

# ---------------------------------------------------------------------------
# 0002 — đối tác, định danh, tài khoản ngân hàng, danh mục Junsky
# ---------------------------------------------------------------------------
M0002 = (
    """CREATE TABLE master.doi_tac (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ten_phap_ly text NOT NULL,
        ten_chuan_hoa text NOT NULL,
        mst text,
        cccd_hash text,
        cccd_mh bytea,
        loai text NOT NULL DEFAULT 'TC' CHECK (loai IN ('TC','CN','NHA_NUOC','NGAN_HANG','NOI_BO')),
        vai_tro text[] NOT NULL DEFAULT '{}',
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG',
        phien_ban integer NOT NULL DEFAULT 1,
        ghi_chu text,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE UNIQUE INDEX doi_tac_mst_uq ON master.doi_tac (mst) WHERE mst IS NOT NULL",
    "CREATE UNIQUE INDEX doi_tac_cccd_uq ON master.doi_tac (cccd_hash) WHERE cccd_hash IS NOT NULL",
    "CREATE INDEX doi_tac_ten_trgm ON master.doi_tac USING gin (ten_chuan_hoa gin_trgm_ops)",
    """CREATE TABLE master.doi_tac_ma_junsky (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        doi_tac_id uuid NOT NULL REFERENCES master.doi_tac(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        object_id_junsky text NOT NULL,
        tien_to text,
        ten_junsky text,
        khoa boolean NOT NULL DEFAULT false,
        dong boolean NOT NULL DEFAULT false,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, object_id_junsky))""",
    "CREATE INDEX doi_tac_ma_junsky_doi_tac ON master.doi_tac_ma_junsky (doi_tac_id)",
    """CREATE TABLE master.doi_tac_dinh_danh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        doi_tac_id uuid NOT NULL REFERENCES master.doi_tac(id),
        loai text NOT NULL CHECK (loai IN ('STK','MST','CCCD','BIEN_SO','TEN_BI_DANH','SO_HD','TEN_CHU_TK')),
        gia_tri text,
        gia_tri_mh bytea,
        gia_tri_hash text NOT NULL,
        nguon text NOT NULL,
        do_tin_cay text NOT NULL DEFAULT 'THAP' CHECK (do_tin_cay IN ('CAO','TB','THAP')),
        lan_gap integer NOT NULL DEFAULT 1,
        xung_dot boolean NOT NULL DEFAULT false,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        nguoi_duyet text,
        CHECK ((loai IN ('STK','CCCD') AND gia_tri IS NULL AND gia_tri_mh IS NOT NULL)
            OR (loai NOT IN ('STK','CCCD') AND gia_tri IS NOT NULL)))""",
    "CREATE UNIQUE INDEX doi_tac_dinh_danh_uq ON master.doi_tac_dinh_danh (loai, gia_tri_hash) WHERE valid_to IS NULL",
    """CREATE TABLE master.tai_khoan_ngan_hang (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ngan_hang text NOT NULL,
        chi_nhanh text,
        stk_mh bytea,
        stk_hash text,
        tk_ke_toan text NOT NULL,
        bank_id_junsky text,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        co_sao_ke boolean NOT NULL DEFAULT false,
        nguon_sao_ke text,
        UNIQUE (phap_nhan_id, tk_ke_toan))""",
    """CREATE TABLE master.du_an (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        cha_id uuid REFERENCES master.du_an(id),
        giai_doan text,
        trang_thai text NOT NULL DEFAULT 'DAU_TU' CHECK (trang_thai IN ('DAU_TU','VAN_HANH','DONG')),
        ngay_chuyen_van_hanh date,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, ma_junsky))""",
    """CREATE TABLE master.ttcp (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        nhom text,
        du_an_id uuid REFERENCES master.du_an(id),
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE NULLS NOT DISTINCT (phap_nhan_id, ma_junsky))""",
    """CREATE TABLE master.khoan_muc_phi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        nhom_g text,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE NULLS NOT DISTINCT (phap_nhan_id, ma_junsky))""",
    """CREATE TABLE master.tai_khoan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        cap smallint,
        tk_cong_no boolean NOT NULL DEFAULT false,
        tk_tien boolean NOT NULL DEFAULT false,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE NULLS NOT DISTINCT (phap_nhan_id, ma_junsky))""",
)

# ---------------------------------------------------------------------------
# 0003 — tệp gốc, chứng từ, dòng chứng từ, công nợ mở (kho)
# ---------------------------------------------------------------------------
M0003 = (
    """CREATE TABLE kho.tep_goc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai_nguon text NOT NULL,
        duong_dan text NOT NULL,
        hash text NOT NULL UNIQUE CHECK (length(hash) = 64),
        kich_thuoc bigint NOT NULL DEFAULT 0 CHECK (kich_thuoc >= 0),
        nhan_luc timestamptz NOT NULL DEFAULT now(),
        nguon text NOT NULL DEFAULT 'TAY',
        nguon_tu_dong_id uuid REFERENCES master.nguon_tu_dong(id),
        nguoi text)""",
    """CREATE TABLE kho.chung_tu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai IN ('SAO_KE','HD_MUA','HD_BAN','BANG_KE_THUE','RQ','NGHIEM_THU',
            'HOP_DONG_TEP','BANG_LUONG','BANG_KHAU_HAO','PHIEU_KHO','LENH_CHI','SO_JUNSKY','CONG_NO_MO',
            'BUT_TOAN_DIEU_CHINH','KHAC')),
        khoa_nguon text NOT NULL,
        ngay_nghiep_vu date NOT NULL,
        nhan_luc timestamptz NOT NULL DEFAULT now(),
        tien_te char(3),
        so_tien_minor bigint,
        chieu text CHECK (chieu IN ('THU','CHI')),
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        doi_tac_tho text,
        du_an_id uuid REFERENCES master.du_an(id),
        mo_ta text,
        du_lieu jsonb NOT NULL DEFAULT '{}'::jsonb,
        hash text NOT NULL,
        tep_goc_id uuid REFERENCES kho.tep_goc(id),
        ky text,
        trang_thai text NOT NULL DEFAULT 'DANG_XU_LY' CHECK (trang_thai IN ('DANG_XU_LY','CHO_DUYET','DANG_HOI',
            'CHO_BO_SUNG','DA_DUYET','DA_XUAT','DA_NAP','DA_DOI_CHIEU','BO_QUA','DA_CO_JUNSKY')),
        voucher_type text,
        so_chung_tu_junsky text,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, loai, khoa_nguon))""",
    "CREATE INDEX chung_tu_ngay ON kho.chung_tu (phap_nhan_id, loai, ngay_nghiep_vu)",
    "CREATE INDEX chung_tu_trang_thai ON kho.chung_tu (phap_nhan_id, trang_thai)",
    "CREATE INDEX chung_tu_doi_tac ON kho.chung_tu (doi_tac_id)",
    "CREATE INDEX chung_tu_so_junsky ON kho.chung_tu (phap_nhan_id, so_chung_tu_junsky) WHERE so_chung_tu_junsky IS NOT NULL",
    """CREATE TABLE kho.chung_tu_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        chung_tu_id uuid NOT NULL REFERENCES kho.chung_tu(id) ON DELETE CASCADE,
        stt integer NOT NULL,
        mo_ta text,
        so_luong numeric,
        don_gia_minor bigint,
        tien_truoc_thue_minor bigint,
        thue_suat numeric,
        tien_thue_minor bigint,
        tai_khoan text,
        no_minor bigint NOT NULL DEFAULT 0,
        co_minor bigint NOT NULL DEFAULT 0,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        doi_tac_junsky text,
        du_an_id uuid REFERENCES master.du_an(id),
        du_an_junsky text,
        ttcp text,
        khoan_muc text,
        dich text CHECK (dich IS NULL OR dich IN ('CHI_PHI','XDCB_241','TAI_SAN','KHO')),
        du_lieu jsonb NOT NULL DEFAULT '{}'::jsonb,
        UNIQUE (chung_tu_id, stt))""",
    "CREATE INDEX chung_tu_dong_tai_khoan ON kho.chung_tu_dong (tai_khoan)",
    """CREATE TABLE kho.cong_no_mo (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ngay_chup date NOT NULL,
        tai_khoan text NOT NULL,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        doi_tac_junsky text,
        item_key text NOT NULL,
        loai text NOT NULL CHECK (loai IN ('UNBILLED','INVOICE','KHAC')),
        so_tien_minor bigint NOT NULL,
        con_lai_minor bigint,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        hoa_don_ref text,
        du_an_id uuid REFERENCES master.du_an(id),
        du_an_junsky text,
        ngay_chung_tu date,
        ngay_hoa_don date,
        du_lieu jsonb NOT NULL DEFAULT '{}'::jsonb,
        UNIQUE (phap_nhan_id, ngay_chup, item_key))""",
    "CREATE INDEX cong_no_mo_doi_tac ON kho.cong_no_mo (phap_nhan_id, ngay_chup, tai_khoan, doi_tac_junsky)",
)

# ---------------------------------------------------------------------------
# 0004 — hợp đồng, tham số, lịch thu/trả nợ, tài sản, nhân viên, loại hình doanh thu (master)
# ---------------------------------------------------------------------------
M0004 = (
    """CREATE TABLE master.loai_hinh_doanh_thu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ma text NOT NULL,
        ten text NOT NULL,
        cau_hinh jsonb NOT NULL DEFAULT '{}'::jsonb,
        tk_cong_no text,
        tk_dt_chua_th text,
        tk_doanh_thu text,
        tk_gia_von text,
        phien_ban integer NOT NULL DEFAULT 1,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, ma, phien_ban))""",
    """CREATE TABLE master.hop_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai IN ('XAY_DUNG','THUE_DAT','BAN_NHA','VAY','MUA','DICH_VU','KHAC')),
        ma_noi_bo text NOT NULL,
        so_hop_dong text NOT NULL,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        du_an_id uuid REFERENCES master.du_an(id),
        loai_hinh_dt_id uuid REFERENCES master.loai_hinh_doanh_thu(id),
        ngay_ky date,
        gia_tri_minor bigint,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        trang_thai text NOT NULL DEFAULT 'HIEU_LUC',
        phien_ban_hien_hanh uuid,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, loai, so_hop_dong),
        UNIQUE (phap_nhan_id, ma_noi_bo))""",
    """CREATE TABLE master.hop_dong_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL REFERENCES master.hop_dong(id),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        loai text NOT NULL DEFAULT 'GOC' CHECK (loai IN ('GOC','PHU_LUC')),
        so_phu_luc text,
        ngay date,
        tham_so jsonb NOT NULL DEFAULT '{}'::jsonb,
        tep_goc_id uuid REFERENCES kho.tep_goc(id),
        nguon text NOT NULL CHECK (nguon IN ('LLM','REVIEW_5','TRICH_6','SHEET','TAY')),
        trang_thai text NOT NULL DEFAULT 'CHO_DUYET' CHECK (trang_thai IN ('CHO_DUYET','DA_DUYET','TU_CHOI')),
        nguoi_duyet text,
        duyet_luc timestamptz,
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (hop_dong_id, phien_ban))""",
    """ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_phien_ban_hien_hanh_fk
        FOREIGN KEY (phien_ban_hien_hanh) REFERENCES master.hop_dong_phien_ban(id) DEFERRABLE INITIALLY DEFERRED""",
    """CREATE TABLE master.hop_dong_tham_so (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL REFERENCES master.hop_dong_phien_ban(id) ON DELETE CASCADE,
        ten text NOT NULL,
        gia_tri text,
        gia_tri_so numeric,
        don_vi text,
        trich_dan text,
        trang integer,
        do_tin_cay text,
        nguon text NOT NULL DEFAULT 'TAY',
        UNIQUE (phien_ban_id, ten),
        CHECK (nguon <> 'LLM' OR trich_dan IS NOT NULL OR gia_tri IS NULL))""",
    """CREATE TABLE master.lich_thu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL REFERENCES master.hop_dong_phien_ban(id) ON DELETE CASCADE,
        dot integer NOT NULL,
        moc text,
        ty_le numeric,
        so_tien_minor bigint,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        han date,
        loai text NOT NULL DEFAULT 'DOT' CHECK (loai IN ('COC','DOT','PHI_KY')),
        trang_thai text NOT NULL DEFAULT 'CHUA_THU' CHECK (trang_thai IN ('CHUA_THU','MOT_PHAN','DA_THU','QUA_HAN','HUY')),
        da_thu_minor bigint NOT NULL DEFAULT 0,
        UNIQUE (phien_ban_id, loai, dot))""",
    """CREATE TABLE master.lich_tra_no (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL REFERENCES master.hop_dong_phien_ban(id) ON DELETE CASCADE,
        ky integer NOT NULL,
        ngay date,
        goc_minor bigint NOT NULL DEFAULT 0,
        lai_minor bigint NOT NULL DEFAULT 0,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        so_khe_uoc text,
        trang_thai text NOT NULL DEFAULT 'CHUA_TRA' CHECK (trang_thai IN ('CHUA_TRA','MOT_PHAN','DA_TRA','QUA_HAN')),
        da_tra_minor bigint NOT NULL DEFAULT 0,
        UNIQUE (phien_ban_id, ky))""",
    """CREATE TABLE master.tai_san (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        loai text NOT NULL CHECK (loai IN ('TSCD','CCDC','BDSDT')),
        nguyen_gia_minor bigint,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        ngay_su_dung date,
        bo_phan text,
        du_an_id uuid REFERENCES master.du_an(id),
        nguon_241_chung_tu_id uuid REFERENCES kho.chung_tu(id),
        trang_thai text NOT NULL DEFAULT 'DANG_DUNG',
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, ma_junsky))""",
    """CREATE TABLE master.nhan_vien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ma_junsky text NOT NULL,
        ten text NOT NULL,
        bo_phan text,
        zalo_id text,
        da_quet_qr boolean NOT NULL DEFAULT false,
        vai_tro_tra_loi text[] NOT NULL DEFAULT '{}',
        stk_mh bytea,
        stk_hash text,
        cccd_mh bytea,
        cccd_hash text,
        trang_thai text NOT NULL DEFAULT 'DANG_LAM',
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        UNIQUE (phap_nhan_id, ma_junsky))""",
)

# ---------------------------------------------------------------------------
# 0005 — nhật ký (chỉ INSERT) và bảo mật
# ---------------------------------------------------------------------------
M0005 = (
    """CREATE TABLE nhat_ky.su_kien (
        id bigserial PRIMARY KEY,
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        luc timestamptz NOT NULL DEFAULT now(),
        nguoi text NOT NULL,
        phien_id uuid,
        loai text NOT NULL CHECK (loai IN ('QUYET_DINH','SUA_DANH_MUC','PHU_LUC','TRI_THUC','LO','DIEU_CHINH',
            'HE_THONG','NGUON_TU_DONG','GHI_CHU_AI','CHUYEN_DOI')),
        doi_tuong_bang text NOT NULL,
        doi_tuong_id uuid,
        hanh_dong text NOT NULL,
        truoc jsonb,
        sau jsonb,
        ly_do text,
        can_cu jsonb,
        ghi_nho boolean NOT NULL DEFAULT false)""",
    "CREATE INDEX su_kien_doi_tuong ON nhat_ky.su_kien (doi_tuong_bang, doi_tuong_id)",
    "CREATE INDEX su_kien_luc ON nhat_ky.su_kien (phap_nhan_id, luc)",
    """CREATE TABLE nhat_ky.cong_ai_goi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        luc timestamptz NOT NULL DEFAULT now(),
        loai_viec text NOT NULL,
        model text NOT NULL,
        nha_cung_cap text NOT NULL,
        cloud boolean NOT NULL,
        dau_vao_mask_hash text,
        token_vao integer,
        token_ra integer,
        chi_phi_uoc numeric,
        ket_qua_tom_tat text,
        trich_dan_hop_le boolean,
        viec_id uuid,
        de_xuat_id uuid,
        thoi_gian_ms integer,
        loi text)""",
    """CREATE TABLE nhat_ky.tin_zalo (
        id bigserial PRIMARY KEY,
        luc timestamptz NOT NULL DEFAULT now(),
        chieu text NOT NULL CHECK (chieu IN ('GUI','NHAN')),
        zalo_id text NOT NULL,
        noi_dung text NOT NULL,
        cau_hoi_id uuid,
        trang_thai_gui text)""",
    # Nhật ký chỉ ghi thêm: trigger từ chối UPDATE/DELETE với mọi vai trò (kể cả chủ CSDL)
    """CREATE OR REPLACE FUNCTION nhat_ky.chi_ghi_them() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'NHAT_KY_CHI_GHI_THEM: không được sửa hoặc xóa nhật ký (%).', TG_TABLE_NAME
                USING ERRCODE = 'P0001';
        END $$""",
    "CREATE TRIGGER su_kien_chi_ghi_them BEFORE UPDATE OR DELETE ON nhat_ky.su_kien FOR EACH ROW EXECUTE FUNCTION nhat_ky.chi_ghi_them()",
    "CREATE TRIGGER cong_ai_goi_chi_ghi_them BEFORE UPDATE OR DELETE ON nhat_ky.cong_ai_goi FOR EACH ROW EXECUTE FUNCTION nhat_ky.chi_ghi_them()",
    "CREATE TRIGGER tin_zalo_chi_ghi_them BEFORE UPDATE OR DELETE ON nhat_ky.tin_zalo FOR EACH ROW EXECUTE FUNCTION nhat_ky.chi_ghi_them()",
    """CREATE TABLE bao_mat.mask_bi_danh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai IN ('TEN_PHAP_NHAN','TEN_KHU','MST','DIA_CHI','STK','CCCD','SO_HD','TIEN')),
        gia_tri_that_mh bytea NOT NULL,
        gia_tri_hash text NOT NULL,
        bi_danh text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        dung_lan_cuoi timestamptz,
        UNIQUE (loai, gia_tri_hash),
        UNIQUE (loai, bi_danh))""",
)

# ---------------------------------------------------------------------------
# 0006 — đề xuất, liên kết, việc cần duyệt, câu hỏi, tri thức, nhãn học, lô, khóa kỳ, phiên, cảnh báo (kho)
# ---------------------------------------------------------------------------
M0006 = (
    """CREATE TABLE kho.phien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        mode text NOT NULL CHECK (mode IN ('THAT','THU','CHAM_DIEM')),
        cutoff date,
        snapshot_cong_no_ngay date,
        opened_at timestamptz NOT NULL DEFAULT now(),
        closed_at timestamptz,
        actor text NOT NULL,
        reason text)""",
    """CREATE TABLE kho.khoa_ky (
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ky text NOT NULL,
        khoa_luc timestamptz NOT NULL DEFAULT now(),
        nguoi text NOT NULL,
        bang_chung jsonb,
        PRIMARY KEY (phap_nhan_id, ky))""",
    """CREATE TABLE kho.de_xuat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        chung_tu_id uuid NOT NULL REFERENCES kho.chung_tu(id) ON DELETE CASCADE,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        hien_hanh boolean NOT NULL DEFAULT true,
        chu_trinh text CHECK (chu_trinh IS NULL OR chu_trinh ~ '^M(10|[1-9])$'),
        nhan_nghiep_vu text,
        dich text,
        muc text NOT NULL CHECK (muc IN ('XANH','VANG','DO')),
        vi_sao text,
        so_do jsonb,
        can_cu jsonb,
        phuong_an jsonb,
        nguon_suy_luan text NOT NULL DEFAULT 'NGUOI' CHECK (nguon_suy_luan IN ('KHOA_CUNG','TU_KHOA','LICH_SU','CONG_NO','CFO','LLM','NGUOI','JUNSKY')),
        cong_ai_goi_id uuid,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        tao_boi text NOT NULL DEFAULT 'MAY',
        UNIQUE (chung_tu_id, phien_ban),
        CHECK (nguon_suy_luan <> 'LLM' OR muc <> 'XANH'))""",
    "CREATE UNIQUE INDEX de_xuat_hien_hanh_uq ON kho.de_xuat (chung_tu_id) WHERE hien_hanh",
    """CREATE TABLE kho.de_xuat_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        de_xuat_id uuid NOT NULL REFERENCES kho.de_xuat(id) ON DELETE CASCADE,
        "offset" integer NOT NULL,
        no_co char(1) NOT NULL CHECK (no_co IN ('N','C')),
        acct_id text NOT NULL,
        bank_id text,
        orgl_id char(3) NOT NULL DEFAULT 'VND',
        orgl_rate numeric NOT NULL DEFAULT 1,
        orgl_deb numeric NOT NULL DEFAULT 0,
        orgl_crd numeric NOT NULL DEFAULT 0,
        base_deb bigint NOT NULL DEFAULT 0 CHECK (base_deb >= 0),
        base_crd bigint NOT NULL DEFAULT 0 CHECK (base_crd >= 0),
        object_id_junsky text,
        entry_dm text,
        cashflow_id text,
        precost_id text,
        project_id text,
        center_id text,
        cost_id text,
        remark text,
        vat_id text,
        vat_acct_id text,
        base_bef_vat bigint,
        base_amt_vat bigint,
        inv_name text, inv_addr text, inv_code text, inv_form text, inv_seri text,
        inv_no text, inv_date date, inv_mode text, inv_text text, inv_look text,
        UNIQUE (de_xuat_id, "offset"),
        CHECK ((no_co = 'N' AND base_crd = 0) OR (no_co = 'C' AND base_deb = 0)))""",
    """CREATE TABLE kho.lien_ket_chung_tu (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        chung_tu_a_id uuid NOT NULL REFERENCES kho.chung_tu(id),
        chung_tu_b_id uuid NOT NULL REFERENCES kho.chung_tu(id),
        loai text NOT NULL CHECK (loai IN ('TIEN_CONG_NO','HD_NGHIEM_THU','HOP_DONG_DOT_TIEN','HD_TAI_SAN',
            'XDCB_TAI_SAN','NHIEU_LAN_CHUYEN','HD_RQ','HD_PHIEU_KHO','DIEU_CHINH','KHAC')),
        so_tien_khop_minor bigint,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        trang_thai text NOT NULL DEFAULT 'CHO' CHECK (trang_thai IN ('CHO','DA_KHOP','HUY')),
        nguon_suy_luan text NOT NULL DEFAULT 'MAY',
        do_tin_cay text,
        nguoi_duyet text,
        duyet_luc timestamptz,
        entry_dm text,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (chung_tu_a_id, chung_tu_b_id, loai),
        CHECK (chung_tu_a_id <> chung_tu_b_id))""",
    "CREATE INDEX lien_ket_b ON kho.lien_ket_chung_tu (chung_tu_b_id)",
    """CREATE TABLE kho.viec_can_duyet (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        loai text NOT NULL CHECK (loai ~ '^V[1-8]$'),
        chu_trinh text,
        tham_chieu_bang text NOT NULL,
        tham_chieu_id uuid NOT NULL,
        muc text CHECK (muc IS NULL OR muc IN ('XANH','VANG','DO')),
        trang_thai text NOT NULL DEFAULT 'CHO_DUYET' CHECK (trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG','DA_DUYET','BO_QUA','DONG')),
        nguoi_phu_trach_id uuid REFERENCES master.nhan_vien(id),
        nguoi_duyet_vai_tro text,
        han date,
        ngay_ton integer NOT NULL DEFAULT 0,
        uu_tien integer NOT NULL DEFAULT 0,
        tom_tat text,
        so_tien_minor bigint,
        tien_te char(3),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE UNIQUE INDEX viec_can_duyet_mo_uq ON kho.viec_can_duyet (tham_chieu_bang, tham_chieu_id) WHERE trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')",
    "CREATE INDEX viec_can_duyet_loc ON kho.viec_can_duyet (phap_nhan_id, trang_thai, loai, muc)",
    """CREATE TABLE kho.cau_hoi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        viec_id uuid NOT NULL REFERENCES kho.viec_can_duyet(id),
        kenh text NOT NULL DEFAULT 'ZALO',
        nguoi_nhan_id uuid REFERENCES master.nhan_vien(id),
        noi_dung text NOT NULL,
        phuong_an jsonb NOT NULL DEFAULT '[]'::jsonb,
        gui_luc timestamptz,
        han date,
        tu_dong boolean NOT NULL DEFAULT false,
        loai_tu_dong text,
        trang_thai text NOT NULL DEFAULT 'SOAN' CHECK (trang_thai IN ('SOAN','DA_GUI','DA_TRA_LOI','QUA_HAN','NHAC_LAI','TU_QUYET')),
        tra_loi_tho text,
        phuong_an_chon integer,
        tra_loi_luc timestamptz,
        cong_ai_goi_id uuid)""",
    """CREATE TABLE kho.tri_thuc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        nhom text NOT NULL,
        khoa_logic text NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        noi_dung jsonb NOT NULL,
        bang_chung jsonb,
        so_do jsonb,
        trang_thai text NOT NULL DEFAULT 'NHAP' CHECK (trang_thai IN ('NHAP','CHO_DUYET','DA_DUYET','THU_HOI')),
        actor text NOT NULL,
        valid_from timestamptz,
        valid_to timestamptz,
        known_at timestamptz,
        supersedes_id uuid REFERENCES kho.tri_thuc(id),
        content_hash text,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE NULLS NOT DISTINCT (phap_nhan_id, nhom, khoa_logic, phien_ban))""",
    "CREATE INDEX tri_thuc_nhom ON kho.tri_thuc (nhom, trang_thai)",
    """CREATE TABLE kho.nhan_hoc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        chung_tu_id uuid NOT NULL REFERENCES kho.chung_tu(id),
        de_xuat_id uuid REFERENCES kho.de_xuat(id),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DU_DIEU_KIEN','NGOAI_LE','BI_THAY_THE')),
        ly_do text,
        business_date date NOT NULL,
        known_at timestamptz NOT NULL,
        eligible_at timestamptz,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    "CREATE UNIQUE INDEX nhan_hoc_hieu_luc_uq ON kho.nhan_hoc (chung_tu_id) WHERE trang_thai = 'DU_DIEU_KIEN'",
    """CREATE TABLE kho.lo_xuat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ky text NOT NULL,
        ma_lo text NOT NULL UNIQUE,
        loai text NOT NULL CHECK (loai IN ('FILE_SOAT','JUNSKY_THU','JUNSKY_CHI','JUNSKY')),
        duong_dan text,
        hash text,
        so_dong integer NOT NULL DEFAULT 0,
        tong_no_minor bigint NOT NULL DEFAULT 0,
        tong_co_minor bigint NOT NULL DEFAULT 0,
        tien_te char(3) NOT NULL DEFAULT 'VND',
        trang_thai text NOT NULL DEFAULT 'DA_XUAT' CHECK (trang_thai IN ('CHUAN_BI','DA_XUAT','DA_NAP','DA_DOI_CHIEU','HUY')),
        nguoi text NOT NULL,
        xuat_luc timestamptz,
        nap_luc timestamptz,
        nguoi_nap text,
        du_lieu jsonb)""",
    """CREATE TABLE kho.lo_xuat_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        lo_id uuid NOT NULL REFERENCES kho.lo_xuat(id),
        loai_lo text NOT NULL,
        de_xuat_id uuid NOT NULL REFERENCES kho.de_xuat(id),
        entry_id_junsky text,
        doi_chieu text CHECK (doi_chieu IS NULL OR doi_chieu IN ('KHOP','LECH_GIA_TRI','THIEU_JUNSKY','THUA_JUNSKY')),
        chenh_minor bigint,
        ghi_chu text,
        UNIQUE (lo_id, de_xuat_id))""",
    "CREATE UNIQUE INDEX lo_xuat_dong_junsky_uq ON kho.lo_xuat_dong (de_xuat_id) WHERE loai_lo <> 'FILE_SOAT'",
    """CREATE TABLE kho.canh_bao (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ma text NOT NULL,
        muc text NOT NULL DEFAULT 'CANH_BAO' CHECK (muc IN ('THONG_TIN','CANH_BAO','CHAN')),
        thong_diep text NOT NULL,
        viec_can_lam text,
        man_hinh_xu_ly text,
        trang_thai text NOT NULL DEFAULT 'MO' CHECK (trang_thai IN ('MO','DA_XU_LY','BO_QUA')),
        tao_luc timestamptz NOT NULL DEFAULT now())""",
)

# ---------------------------------------------------------------------------
# 0007 — ràng buộc nghiệp vụ mức CSDL: máy trạng thái chứng từ, điều kiện Đồng ý, khóa kỳ
# ---------------------------------------------------------------------------
M0007 = (
    # Máy trạng thái chứng từ (TL 37 §5.2)
    """CREATE OR REPLACE FUNCTION kho.chuyen_trang_thai_hop_le(tu text, den text) RETURNS boolean
        LANGUAGE sql IMMUTABLE AS $$
        SELECT tu = den OR (tu, den) IN (
            ('DANG_XU_LY','CHO_DUYET'), ('DANG_XU_LY','DA_CO_JUNSKY'), ('DANG_XU_LY','BO_QUA'),
            ('CHO_DUYET','DANG_HOI'), ('CHO_DUYET','CHO_BO_SUNG'), ('CHO_DUYET','DA_DUYET'),
            ('CHO_DUYET','BO_QUA'), ('CHO_DUYET','DA_CO_JUNSKY'),
            ('DANG_HOI','CHO_DUYET'), ('DANG_HOI','BO_QUA'),
            ('CHO_BO_SUNG','CHO_DUYET'), ('CHO_BO_SUNG','BO_QUA'),
            ('DA_DUYET','CHO_DUYET'), ('DA_DUYET','DA_XUAT'),
            ('BO_QUA','CHO_DUYET'),
            ('DA_XUAT','DA_NAP'),
            ('DA_NAP','DA_DOI_CHIEU'),
            ('DA_CO_JUNSKY','CHO_DUYET'))
        $$""",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_kiem_trang_thai() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            tong_no bigint; tong_co bigint; thieu_dt integer; thieu_tk integer; da_khoa integer;
        BEGIN
            IF NOT kho.chuyen_trang_thai_hop_le(OLD.trang_thai, NEW.trang_thai) THEN
                RAISE EXCEPTION 'TRANG_THAI_KHONG_HOP_LE: % -> %', OLD.trang_thai, NEW.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF NEW.trang_thai = 'DA_DUYET' AND OLD.trang_thai <> 'DA_DUYET' THEN
                -- kỳ chưa khóa
                SELECT count(*) INTO da_khoa FROM kho.khoa_ky k WHERE k.phap_nhan_id = NEW.phap_nhan_id AND k.ky = NEW.ky;
                IF da_khoa > 0 THEN
                    RAISE EXCEPTION 'KY_DA_KHOA: kỳ % đã khóa', NEW.ky USING ERRCODE = 'P0001';
                END IF;
                -- đề xuất hiện hành: Nợ = Có > 0
                SELECT coalesce(sum(d.base_deb),0), coalesce(sum(d.base_crd),0) INTO tong_no, tong_co
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh;
                IF tong_no <> tong_co OR tong_no = 0 THEN
                    RAISE EXCEPTION 'NO_KHONG_BANG_CO: Nợ % <> Có % hoặc bằng 0', tong_no, tong_co USING ERRCODE = 'P0001';
                END IF;
                -- TK công nợ phải có mã đối tượng Junsky; mọi dòng phải dùng TK chi tiết (có trong danh mục, không có TK con)
                SELECT count(*) INTO thieu_dt
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                JOIN master.tai_khoan t ON t.ma_junsky = d.acct_id AND t.valid_to IS NULL
                    AND (t.phap_nhan_id = NEW.phap_nhan_id OR t.phap_nhan_id IS NULL)
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh AND t.tk_cong_no AND (d.object_id_junsky IS NULL OR d.object_id_junsky = '');
                IF thieu_dt > 0 THEN
                    RAISE EXCEPTION 'THIEU_DOI_TUONG: % dòng TK công nợ chưa có mã đối tượng', thieu_dt USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO thieu_tk
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh AND EXISTS (
                    SELECT 1 FROM master.tai_khoan c WHERE c.valid_to IS NULL
                        AND (c.phap_nhan_id = NEW.phap_nhan_id OR c.phap_nhan_id IS NULL)
                        AND c.ma_junsky <> d.acct_id AND c.ma_junsky LIKE d.acct_id || '%');
                IF thieu_tk > 0 THEN
                    RAISE EXCEPTION 'TK_CHUA_CHI_TIET: % dòng dùng TK tổng hợp', thieu_tk USING ERRCODE = 'P0001';
                END IF;
            END IF;
            NEW.cap_nhat_luc := now();
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_trang_thai BEFORE UPDATE OF trang_thai ON kho.chung_tu FOR EACH ROW EXECUTE FUNCTION kho.chung_tu_kiem_trang_thai()",
    # Sau khi đã xuất, không cho sửa dòng đề xuất hiện hành (sửa = bút toán điều chỉnh)
    """CREATE OR REPLACE FUNCTION kho.de_xuat_dong_khoa_sau_xuat() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE tt text;
        BEGIN
            SELECT c.trang_thai INTO tt FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id
            WHERE x.id = coalesce(NEW.de_xuat_id, OLD.de_xuat_id);
            IF tt IN ('DA_XUAT','DA_NAP','DA_DOI_CHIEU') THEN
                RAISE EXCEPTION 'DA_XUAT_KHONG_SUA: chứng từ đã xuất lô; sửa bằng bút toán điều chỉnh' USING ERRCODE = 'P0001';
            END IF;
            RETURN coalesce(NEW, OLD);
        END $$""",
    "CREATE TRIGGER de_xuat_dong_khoa BEFORE INSERT OR UPDATE OR DELETE ON kho.de_xuat_dong FOR EACH ROW EXECUTE FUNCTION kho.de_xuat_dong_khoa_sau_xuat()",
    # Nhãn học chỉ khi đã đối chiếu khớp
    """CREATE OR REPLACE FUNCTION kho.nhan_hoc_kiem() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE tt text; khop integer;
        BEGIN
            IF NEW.trang_thai = 'DU_DIEU_KIEN' THEN
                SELECT trang_thai INTO tt FROM kho.chung_tu WHERE id = NEW.chung_tu_id;
                IF tt <> 'DA_DOI_CHIEU' THEN
                    RAISE EXCEPTION 'CHUA_DOI_CHIEU: chứng từ ở trạng thái %, không được học', tt USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO khop FROM kho.lo_xuat_dong l JOIN kho.de_xuat x ON x.id = l.de_xuat_id
                WHERE x.chung_tu_id = NEW.chung_tu_id AND l.doi_chieu = 'KHOP';
                IF khop = 0 THEN
                    RAISE EXCEPTION 'CHUA_KHOP_JUNSKY: chưa có dòng lô đối chiếu KHOP' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER nhan_hoc_kiem BEFORE INSERT ON kho.nhan_hoc FOR EACH ROW EXECUTE FUNCTION kho.nhan_hoc_kiem()",
    # Hàm tiện ích: chuẩn hóa tên (bỏ dấu, viết hoa, bỏ viết tắt phổ biến) dùng chung hai engine qua ứng dụng; bản SQL để truy vấn nhanh
    """CREATE OR REPLACE FUNCTION master.chuan_hoa_ten(v text) RETURNS text
        LANGUAGE sql IMMUTABLE AS $$
        SELECT regexp_replace(upper(unaccent(replace(replace(coalesce(v,''), 'Đ', 'D'), 'đ', 'd'))), '\\s+', ' ', 'g')
        $$""",
)

# ---------------------------------------------------------------------------
# 0008 — quyền cho vai trò ứng dụng (chỉ khi vai trò tồn tại)
# ---------------------------------------------------------------------------
M0008 = (
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            GRANT USAGE ON SCHEMA master, kho, nhat_ky TO app_ke_toan;
            GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA master, kho TO app_ke_toan;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA master, kho, nhat_ky TO app_ke_toan;
            GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA nhat_ky TO app_ke_toan;
            REVOKE UPDATE, DELETE ON ALL TABLES IN SCHEMA nhat_ky FROM app_ke_toan;
            REVOKE ALL ON SCHEMA bao_mat FROM app_ke_toan;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            GRANT USAGE ON SCHEMA master, kho, nhat_ky, bao_mat TO app_cong_ai;
            GRANT SELECT ON ALL TABLES IN SCHEMA master, kho TO app_cong_ai;
            GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA nhat_ky TO app_cong_ai;
            GRANT SELECT, INSERT, UPDATE ON bao_mat.mask_bi_danh TO app_cong_ai;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA nhat_ky TO app_cong_ai;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            GRANT USAGE ON SCHEMA master, kho, nhat_ky TO app_doc;
            GRANT SELECT ON ALL TABLES IN SCHEMA master, kho, nhat_ky TO app_doc;
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0009 — theo review độc lập 16/10: nhật ký chặn TRUNCATE; quyền mặc định cho bảng mới; TK phải có trong danh mục;
#        đường HUY lô (DA_XUAT → DA_DUYET); nhóm tri thức có CHECK
# ---------------------------------------------------------------------------
M0009 = (
    """CREATE OR REPLACE FUNCTION nhat_ky.chan_truncate() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'NHAT_KY_CHI_GHI_THEM: không được TRUNCATE nhật ký (%).', TG_TABLE_NAME USING ERRCODE = 'P0001';
        END $$""",
    "CREATE TRIGGER su_kien_chan_truncate BEFORE TRUNCATE ON nhat_ky.su_kien FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chan_truncate()",
    "CREATE TRIGGER cong_ai_goi_chan_truncate BEFORE TRUNCATE ON nhat_ky.cong_ai_goi FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chan_truncate()",
    "CREATE TRIGGER tin_zalo_chan_truncate BEFORE TRUNCATE ON nhat_ky.tin_zalo FOR EACH STATEMENT EXECUTE FUNCTION nhat_ky.chan_truncate()",
    # Máy trạng thái: thêm đường hủy lô (DA_XUAT → DA_DUYET) — chỉ dùng khi lô bị HUY, ứng dụng kiểm tra lô
    """CREATE OR REPLACE FUNCTION kho.chuyen_trang_thai_hop_le(tu text, den text) RETURNS boolean
        LANGUAGE sql IMMUTABLE AS $$
        SELECT tu = den OR (tu, den) IN (
            ('DANG_XU_LY','CHO_DUYET'), ('DANG_XU_LY','DA_CO_JUNSKY'), ('DANG_XU_LY','BO_QUA'),
            ('CHO_DUYET','DANG_HOI'), ('CHO_DUYET','CHO_BO_SUNG'), ('CHO_DUYET','DA_DUYET'),
            ('CHO_DUYET','BO_QUA'), ('CHO_DUYET','DA_CO_JUNSKY'),
            ('DANG_HOI','CHO_DUYET'), ('DANG_HOI','BO_QUA'),
            ('CHO_BO_SUNG','CHO_DUYET'), ('CHO_BO_SUNG','BO_QUA'),
            ('DA_DUYET','CHO_DUYET'), ('DA_DUYET','DA_XUAT'),
            ('BO_QUA','CHO_DUYET'),
            ('DA_XUAT','DA_NAP'), ('DA_XUAT','DA_DUYET'),
            ('DA_NAP','DA_DOI_CHIEU'),
            ('DA_CO_JUNSKY','CHO_DUYET'))
        $$""",
    # Điều kiện Đồng ý: TK phải CÓ trong danh mục (không chỉ "không có TK con"); so tiền tố không dùng LIKE
    """CREATE OR REPLACE FUNCTION kho.chung_tu_kiem_trang_thai() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            tong_no bigint; tong_co bigint; thieu_dt integer; thieu_tk integer; khong_co integer; da_khoa integer; huy_lo integer;
        BEGIN
            IF NOT kho.chuyen_trang_thai_hop_le(OLD.trang_thai, NEW.trang_thai) THEN
                RAISE EXCEPTION 'TRANG_THAI_KHONG_HOP_LE: % -> %', OLD.trang_thai, NEW.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'DA_XUAT' AND NEW.trang_thai = 'DA_DUYET' THEN
                -- chỉ khi mọi lô chứa đề xuất của chứng từ này đã HUY
                SELECT count(*) INTO huy_lo FROM kho.lo_xuat_dong ld JOIN kho.lo_xuat l ON l.id = ld.lo_id
                    JOIN kho.de_xuat x ON x.id = ld.de_xuat_id
                WHERE x.chung_tu_id = NEW.id AND ld.loai_lo <> 'FILE_SOAT' AND l.trang_thai <> 'HUY';
                IF huy_lo > 0 THEN
                    RAISE EXCEPTION 'LO_CHUA_HUY: chứng từ còn nằm trong lô chưa hủy' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.trang_thai = 'DA_DUYET' AND OLD.trang_thai NOT IN ('DA_DUYET','DA_XUAT') THEN
                SELECT count(*) INTO da_khoa FROM kho.khoa_ky k WHERE k.phap_nhan_id = NEW.phap_nhan_id AND k.ky = NEW.ky;
                IF da_khoa > 0 THEN
                    RAISE EXCEPTION 'KY_DA_KHOA: kỳ % đã khóa', NEW.ky USING ERRCODE = 'P0001';
                END IF;
                SELECT coalesce(sum(d.base_deb),0), coalesce(sum(d.base_crd),0) INTO tong_no, tong_co
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh;
                IF tong_no <> tong_co OR tong_no = 0 THEN
                    RAISE EXCEPTION 'NO_KHONG_BANG_CO: Nợ % <> Có % hoặc bằng 0', tong_no, tong_co USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO khong_co
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh AND NOT EXISTS (
                    SELECT 1 FROM master.tai_khoan t WHERE t.ma_junsky = d.acct_id AND t.valid_to IS NULL
                        AND (t.phap_nhan_id = NEW.phap_nhan_id OR t.phap_nhan_id IS NULL));
                IF khong_co > 0 THEN
                    RAISE EXCEPTION 'TK_KHONG_CO_TRONG_DANH_MUC: % dòng dùng TK ngoài danh mục', khong_co USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO thieu_dt
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                JOIN master.tai_khoan t ON t.ma_junsky = d.acct_id AND t.valid_to IS NULL
                    AND (t.phap_nhan_id = NEW.phap_nhan_id OR t.phap_nhan_id IS NULL)
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh AND t.tk_cong_no AND (d.object_id_junsky IS NULL OR d.object_id_junsky = '');
                IF thieu_dt > 0 THEN
                    RAISE EXCEPTION 'THIEU_DOI_TUONG: % dòng TK công nợ chưa có mã đối tượng', thieu_dt USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO thieu_tk
                FROM kho.de_xuat x JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id
                WHERE x.chung_tu_id = NEW.id AND x.hien_hanh AND EXISTS (
                    SELECT 1 FROM master.tai_khoan c WHERE c.valid_to IS NULL
                        AND (c.phap_nhan_id = NEW.phap_nhan_id OR c.phap_nhan_id IS NULL)
                        AND c.ma_junsky <> d.acct_id AND left(c.ma_junsky, length(d.acct_id)) = d.acct_id);
                IF thieu_tk > 0 THEN
                    RAISE EXCEPTION 'TK_CHUA_CHI_TIET: % dòng dùng TK tổng hợp', thieu_tk USING ERRCODE = 'P0001';
                END IF;
            END IF;
            NEW.cap_nhat_luc := now();
            RETURN NEW;
        END $$""",
    "ALTER TABLE kho.de_xuat_dong ADD CONSTRAINT de_xuat_dong_acct_id_khong_rong CHECK (acct_id <> '')",
    """ALTER TABLE kho.tri_thuc ADD CONSTRAINT tri_thuc_nhom_check CHECK (nhom IN ('DANH_MUC','DINH_DANH','TU_KHOA','KHOA_CUNG','MAU_LICH_SU',
        'CFO','DAP_AN_MAU','ANH_XA_NHOM_G','NHOM_G','CAY_HOA_DON','QUY_TAC','NGOAI_LE','LOAI_HINH_DT','BOI_CANH'))""",
    # Quyền: thu hồi TRUNCATE; quyền mặc định cho bảng tạo ở migration sau (áp cho vai trò đang chạy migration)
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            REVOKE TRUNCATE ON ALL TABLES IN SCHEMA master, kho, nhat_ky FROM app_ke_toan;
            ALTER DEFAULT PRIVILEGES IN SCHEMA master, kho GRANT SELECT, INSERT, UPDATE ON TABLES TO app_ke_toan;
            ALTER DEFAULT PRIVILEGES IN SCHEMA nhat_ky GRANT SELECT, INSERT ON TABLES TO app_ke_toan;
            ALTER DEFAULT PRIVILEGES IN SCHEMA master, kho, nhat_ky GRANT USAGE, SELECT ON SEQUENCES TO app_ke_toan;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            ALTER DEFAULT PRIVILEGES IN SCHEMA master, kho GRANT SELECT ON TABLES TO app_cong_ai;
            ALTER DEFAULT PRIVILEGES IN SCHEMA nhat_ky GRANT SELECT, INSERT ON TABLES TO app_cong_ai;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            ALTER DEFAULT PRIVILEGES IN SCHEMA master, kho, nhat_ky GRANT SELECT ON TABLES TO app_doc;
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0010 — CRM-01 (V14 typed K2): vai trò TL40, phân quyền module, provenance tham số/phiên bản, lịch thu có khóa nghĩa vụ,
#        liên kết/phân bổ chung trỏ đợt thu, việc V3/V4 hai bước, RLS theo pháp nhân cho vai trò web app_web.
#        Vai trò cũ (app_ke_toan/app_doc/app_cong_ai) giữ phạm vi như trước bằng policy riêng — không đổi legacy/option C.
# ---------------------------------------------------------------------------
_RLS_BANG = (
    # (bảng, biểu thức pháp nhân của dòng)
    ("master.hop_dong", "phap_nhan_id"),
    ("master.hop_dong_phien_ban", "(SELECT h.phap_nhan_id FROM master.hop_dong h WHERE h.id = hop_dong_id)"),
    ("master.hop_dong_tham_so", "(SELECT h.phap_nhan_id FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = phien_ban_id)"),
    ("master.lich_thu", "phap_nhan_id"),
    ("master.loai_hinh_doanh_thu", "phap_nhan_id"),
    ("master.doi_tac_ma_junsky", "phap_nhan_id"),
    ("master.du_an", "phap_nhan_id"),
    ("kho.tep_goc", "phap_nhan_id"),
    ("kho.chung_tu", "phap_nhan_id"),
    ("kho.de_xuat", "(SELECT c.phap_nhan_id FROM kho.chung_tu c WHERE c.id = chung_tu_id)"),
    ("kho.lien_ket_chung_tu", "phap_nhan_id"),
    ("kho.viec_can_duyet", "phap_nhan_id"),
)


def _rls_statements() -> tuple[str, ...]:
    out = []
    for table, expr in _RLS_BANG:
        name = table.split(".")[1]
        out.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        out.append(f"""DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
                EXECUTE 'CREATE POLICY {name}_pham_vi_web ON {table} TO app_web USING ({expr.replace("'", "''")} IN (SELECT master.ktt_pn_cho_phep())) WITH CHECK ({expr.replace("'", "''")} IN (SELECT master.ktt_pn_cho_phep()))';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
                EXECUTE 'CREATE POLICY {name}_ung_dung_cu ON {table} TO app_ke_toan USING (true) WITH CHECK (true)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
                EXECUTE 'CREATE POLICY {name}_chi_doc ON {table} FOR SELECT TO app_doc USING (true)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
                EXECUTE 'CREATE POLICY {name}_cong_ai ON {table} FOR SELECT TO app_cong_ai USING (true)';
            END IF;
        END $$""")
    return tuple(out)


# M0010 BẢN BÀN GIAO ĐẦU (19/10/2026, chưa nghiệm thu) — GIỮ NGUYÊN TỪNG KÝ TỰ để nhận diện chính xác checksum của các DB thử
# đã áp nó. Bản này chặn upgrade DB v9 có link HUY cũ (CHECK lien_ket_huy_co_vet, lỗi 23514), nên M0010 hiện hành = bản này bỏ
# đúng câu CHECK đó; M0011 thêm lại ràng buộc có phân biệt lịch sử trước v10, đưa cả hai đường về cùng schema.
M0010_V1_BAN_GIAO_DAU = (
    # Vai trò TL40 + đánh dấu danh tính mô phỏng; phân quyền theo module
    "ALTER TABLE master.nguoi_dung DROP CONSTRAINT nguoi_dung_vai_tro_check",
    """ALTER TABLE master.nguoi_dung ADD CONSTRAINT nguoi_dung_vai_tro_check
        CHECK (vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG','CFO','NHAP_JUNSKY','XEM','BAN_HANG','DU_AN'))""",
    "ALTER TABLE master.nguoi_dung ADD COLUMN mo_phong boolean NOT NULL DEFAULT false",
    "ALTER TABLE master.nguoi_dung ADD CONSTRAINT nguoi_dung_mo_phong_ten CHECK (NOT mo_phong OR left(dang_nhap, 9) = 'MO_PHONG_')",
    "ALTER TABLE master.phan_quyen ADD COLUMN module text[] NOT NULL DEFAULT '{}'",
    # Phiên bản hợp đồng: nguồn BAN_HANG (TL40 §7), quan hệ phụ lục, hiệu lực, căn cứ, bước kiểm/duyệt
    "ALTER TABLE master.hop_dong_phien_ban DROP CONSTRAINT hop_dong_phien_ban_nguon_check",
    "ALTER TABLE master.hop_dong_phien_ban ADD CONSTRAINT hop_dong_phien_ban_nguon_check CHECK (nguon IN ('LLM','REVIEW_5','TRICH_6','SHEET','TAY','BAN_HANG'))",
    """ALTER TABLE master.hop_dong_phien_ban
        ADD COLUMN thay_cho_id uuid REFERENCES master.hop_dong_phien_ban(id),
        ADD COLUMN ngay_hieu_luc date,
        ADD COLUMN chung_tu_id uuid REFERENCES kho.chung_tu(id),
        ADD COLUMN loai_hinh_dt_id uuid REFERENCES master.loai_hinh_doanh_thu(id),
        ADD COLUMN kiem_boi text,
        ADD COLUMN kiem_luc timestamptz,
        ADD COLUMN ly_do text,
        ADD COLUMN tao_boi text,
        ADD COLUMN tao_luc timestamptz NOT NULL DEFAULT now()""",
    # Tham số: giữ nguyên nội dung nguồn #6 và trạng thái căn cứ; giá trị hiệu lực NULL khi không có căn cứ
    """ALTER TABLE master.hop_dong_tham_so
        ADD COLUMN ma_nguon text,
        ADD COLUMN nhom text,
        ADD COLUMN truong text,
        ADD COLUMN gia_tri_tho text,
        ADD COLUMN kieu text,
        ADD COLUMN gia_tri_typed jsonb,
        ADD COLUMN dieu_khoan text,
        ADD COLUMN vi_tri text,
        ADD COLUMN kiem_tra_nguon text,
        ADD COLUMN ghi_chu_nguon text,
        ADD COLUMN trang_thai_can_cu text CHECK (trang_thai_can_cu IN ('CO_CAN_CU','KHONG_QUY_DINH','CAN_CU_KHONG_KHOP','CHUA_DOI_CHIEU_NGUON')),
        ADD COLUMN loi text[] NOT NULL DEFAULT '{}',
        ADD COLUMN chung_tu_id uuid REFERENCES kho.chung_tu(id),
        ADD COLUMN ke_thua_tu uuid REFERENCES master.hop_dong_tham_so(id)""",
    "ALTER TABLE master.hop_dong_tham_so ADD CONSTRAINT tham_so_can_cu_co_trich_dan CHECK (trang_thai_can_cu IS DISTINCT FROM 'CO_CAN_CU' OR trich_dan IS NOT NULL)",
    "ALTER TABLE master.hop_dong_tham_so ADD CONSTRAINT tham_so_khong_quy_dinh_null CHECK (trang_thai_can_cu IS DISTINCT FROM 'KHONG_QUY_DINH' OR gia_tri IS NULL)",
    # Lịch thu: pháp nhân, khóa nghĩa vụ nối giữa phiên bản, provenance tham số, cơ sở số tiền
    """ALTER TABLE master.lich_thu
        ADD COLUMN phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ADD COLUMN khoa_nghia_vu text,
        ADD COLUMN thay_cho_id uuid REFERENCES master.lich_thu(id),
        ADD COLUMN nguon_tham_so text[] NOT NULL DEFAULT '{}',
        ADD COLUMN co_so text,
        ADD COLUMN ghi_chu text""",
    """UPDATE master.lich_thu l SET phap_nhan_id = h.phap_nhan_id, khoa_nghia_vu = coalesce(l.khoa_nghia_vu, l.loai || '-' || l.dot)
        FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = l.phien_ban_id""",
    "ALTER TABLE master.lich_thu ALTER COLUMN phap_nhan_id SET NOT NULL",
    "ALTER TABLE master.lich_thu ALTER COLUMN khoa_nghia_vu SET NOT NULL",
    "CREATE UNIQUE INDEX lich_thu_khoa_uq ON master.lich_thu (phien_ban_id, khoa_nghia_vu)",
    "ALTER TABLE master.lich_thu ADD CONSTRAINT lich_thu_so_tien_duong CHECK (so_tien_minor IS NULL OR so_tien_minor > 0)",
    # Liên kết/phân bổ chung: trỏ được đợt thu (không biến đợt thành chứng từ giả), nhiều đợt/nhiều lần, idempotency, hủy có vết
    """ALTER TABLE kho.lien_ket_chung_tu
        ADD COLUMN lich_thu_id uuid REFERENCES master.lich_thu(id),
        ADD COLUMN hop_dong_id uuid REFERENCES master.hop_dong(id),
        ADD COLUMN khoa_idempotency text,
        ADD COLUMN tao_boi text,
        ADD COLUMN huy_luc timestamptz,
        ADD COLUMN huy_boi text,
        ADD COLUMN ly_do_huy text,
        ADD COLUMN can_cu jsonb""",
    "ALTER TABLE kho.lien_ket_chung_tu DROP CONSTRAINT lien_ket_chung_tu_chung_tu_a_id_chung_tu_b_id_loai_key",
    "CREATE UNIQUE INDEX lien_ket_cap_uq ON kho.lien_ket_chung_tu (chung_tu_a_id, chung_tu_b_id, loai) WHERE lich_thu_id IS NULL AND trang_thai <> 'HUY'",
    "CREATE UNIQUE INDEX lien_ket_lich_uq ON kho.lien_ket_chung_tu (chung_tu_a_id, lich_thu_id) WHERE lich_thu_id IS NOT NULL AND trang_thai <> 'HUY'",
    "CREATE UNIQUE INDEX lien_ket_idempotency_uq ON kho.lien_ket_chung_tu (khoa_idempotency) WHERE khoa_idempotency IS NOT NULL",
    "CREATE INDEX lien_ket_lich ON kho.lien_ket_chung_tu (lich_thu_id) WHERE lich_thu_id IS NOT NULL",
    """ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_huy_co_vet
        CHECK (trang_thai <> 'HUY' OR (huy_luc IS NOT NULL AND huy_boi IS NOT NULL AND ly_do_huy IS NOT NULL))""",
    """CREATE OR REPLACE FUNCTION kho.lien_ket_kiem() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            a record; b record; l record; tong_a bigint; tong_l bigint; hd uuid;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF OLD.trang_thai = 'HUY' AND NEW.trang_thai <> 'HUY' THEN
                    RAISE EXCEPTION 'LIEN_KET_DA_HUY: liên kết đã hủy không mở lại; tạo liên kết mới' USING ERRCODE = 'P0001';
                END IF;
                IF (NEW.chung_tu_a_id, NEW.chung_tu_b_id, NEW.lich_thu_id, NEW.so_tien_khop_minor, NEW.tien_te, NEW.phap_nhan_id)
                   IS DISTINCT FROM (OLD.chung_tu_a_id, OLD.chung_tu_b_id, OLD.lich_thu_id, OLD.so_tien_khop_minor, OLD.tien_te, OLD.phap_nhan_id) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA: chỉ đổi trạng thái; sửa = hủy + tạo mới' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            SELECT * INTO a FROM kho.chung_tu WHERE id = NEW.chung_tu_a_id FOR UPDATE;
            SELECT * INTO b FROM kho.chung_tu WHERE id = NEW.chung_tu_b_id;
            IF a.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR b.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.lich_thu_id IS NULL THEN
                RETURN NEW;
            END IF;
            SELECT lt.*, p.hop_dong_id AS hd, p.chung_tu_id AS ct_phien_ban, p.trang_thai AS pb_trang_thai
                INTO l FROM master.lich_thu lt JOIN master.hop_dong_phien_ban p ON p.id = lt.phien_ban_id WHERE lt.id = NEW.lich_thu_id FOR UPDATE OF lt;
            IF l.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF l.pb_trang_thai IS DISTINCT FROM 'DA_DUYET' THEN
                RAISE EXCEPTION 'LICH_CHUA_HIEU_LUC: đợt thuộc phiên bản chưa duyệt' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai <> 'HOP_DONG_DOT_TIEN' OR a.loai <> 'SAO_KE' OR a.chieu IS DISTINCT FROM 'THU' OR NEW.chung_tu_b_id IS DISTINCT FROM l.ct_phien_ban THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_THAM_CHIEU: tiền thu ↔ đợt phải nối với chứng từ của đúng phiên bản' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.hop_dong_id IS DISTINCT FROM l.hd THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_HOP_DONG' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.so_tien_khop_minor IS NULL OR NEW.so_tien_khop_minor <= 0 OR l.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_SO_TIEN: cần số tiền dương và đợt có số tiền' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.tien_te IS DISTINCT FROM a.tien_te OR NEW.tien_te IS DISTINCT FROM l.tien_te OR a.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_TIEN_TE: không bù trừ khác loại tiền' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(sum(so_tien_khop_minor), 0) INTO tong_a FROM kho.lien_ket_chung_tu
                WHERE chung_tu_a_id = NEW.chung_tu_a_id AND trang_thai <> 'HUY' AND lich_thu_id IS NOT NULL;
            IF tong_a + NEW.so_tien_khop_minor > a.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_TIEN_KHA_DUNG: % + % > %', tong_a, NEW.so_tien_khop_minor, a.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(sum(k.so_tien_khop_minor), 0) INTO tong_l FROM kho.lien_ket_chung_tu k
                JOIN master.lich_thu x ON x.id = k.lich_thu_id JOIN master.hop_dong_phien_ban px ON px.id = x.phien_ban_id
                WHERE k.trang_thai <> 'HUY' AND px.hop_dong_id = l.hd AND x.khoa_nghia_vu = l.khoa_nghia_vu;
            IF tong_l + NEW.so_tien_khop_minor > l.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_NGHIA_VU: % + % > %', tong_l, NEW.so_tien_khop_minor, l.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lien_ket_kiem BEFORE INSERT OR UPDATE ON kho.lien_ket_chung_tu FOR EACH ROW EXECUTE FUNCTION kho.lien_ket_kiem()",
    # Việc cần duyệt: bước kế toán kiểm trước, CFO duyệt; lý do chờ
    """ALTER TABLE kho.viec_can_duyet
        ADD COLUMN module text,
        ADD COLUMN kiem_boi text,
        ADD COLUMN kiem_luc timestamptz,
        ADD COLUMN duyet_boi text,
        ADD COLUMN duyet_luc timestamptz,
        ADD COLUMN ly_do_cho text[] NOT NULL DEFAULT '{}'""",
    # Phạm vi pháp nhân của phiên làm việc: ứng dụng (máy chủ) đặt ktt.nguoi_dung_id cho từng giao dịch
    """CREATE OR REPLACE FUNCTION master.ktt_pn_cho_phep() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT q.phap_nhan_id FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
        WHERE n.trang_thai = 'HOAT_DONG'
          AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
        $$""",
    # Duyệt phiên bản: kế toán kiểm trước, CFO có quyền V3 trên pháp nhân duyệt, khác người kiểm, trùng danh tính phiên
    """CREATE OR REPLACE FUNCTION master.phien_ban_kiem_duyet() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pn uuid; ok integer; phien text;
        BEGIN
            IF NEW.trang_thai = OLD.trang_thai AND NEW.kiem_boi IS NOT DISTINCT FROM OLD.kiem_boi THEN
                RETURN NEW;
            END IF;
            IF OLD.trang_thai <> 'CHO_DUYET' THEN
                RAISE EXCEPTION 'PHIEN_BAN_DA_CHOT: phiên bản % không còn chờ duyệt', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            phien := nullif(current_setting('ktt.nguoi_dung_dang_nhap', true), '');
            IF NEW.kiem_boi IS DISTINCT FROM OLD.kiem_boi THEN
                SELECT count(*) INTO ok FROM master.nguoi_dung n JOIN master.phan_quyen q ON q.nguoi_dung_id = n.id
                    WHERE n.dang_nhap = NEW.kiem_boi AND n.trang_thai = 'HOAT_DONG' AND n.vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG') AND q.phap_nhan_id = pn;
                IF ok = 0 OR (phien IS NOT NULL AND phien <> NEW.kiem_boi) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_KIEM: % không phải kế toán có quyền trên pháp nhân', NEW.kiem_boi USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.trang_thai IN ('DA_DUYET','TU_CHOI') THEN
                IF NEW.trang_thai = 'DA_DUYET' AND NEW.kiem_luc IS NULL THEN
                    RAISE EXCEPTION 'CHUA_KIEM_TRUOC: kế toán chưa kiểm trước' USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO ok FROM master.nguoi_dung n JOIN master.phan_quyen q ON q.nguoi_dung_id = n.id
                    WHERE n.dang_nhap = NEW.nguoi_duyet AND n.trang_thai = 'HOAT_DONG' AND n.vai_tro = 'CFO' AND q.phap_nhan_id = pn
                      AND 'V3' = ANY (q.duyet_loai_viec);
                IF ok = 0 OR NEW.nguoi_duyet IS NOT DISTINCT FROM NEW.kiem_boi OR (phien IS NOT NULL AND phien <> NEW.nguoi_duyet) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_DUYET: % không phải CFO có quyền V3 trên pháp nhân', NEW.nguoi_duyet USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER phien_ban_kiem_duyet BEFORE UPDATE ON master.hop_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION master.phien_ban_kiem_duyet()",
    # Vai trò web đa người dùng (TL40 V14): tạo nếu có quyền; quyền hẹp; bao_mat không có
    """DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            BEGIN
                CREATE ROLE app_web NOLOGIN NOINHERIT;
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Không đủ quyền tạo vai trò app_web — chủ CSDL tạo sau rồi chạy lại cấp quyền.';
            END;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA master, kho, nhat_ky TO app_web;
            GRANT SELECT ON ALL TABLES IN SCHEMA master TO app_web;
            GRANT SELECT, INSERT, UPDATE ON master.hop_dong, master.hop_dong_phien_ban, master.hop_dong_tham_so, master.lich_thu TO app_web;
            GRANT SELECT, INSERT, UPDATE ON kho.tep_goc, kho.chung_tu, kho.de_xuat, kho.lien_ket_chung_tu, kho.viec_can_duyet TO app_web;
            GRANT SELECT ON kho.chung_tu_dong, kho.de_xuat_dong TO app_web;
            GRANT SELECT, INSERT ON nhat_ky.su_kien TO app_web;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA nhat_ky TO app_web;
            GRANT EXECUTE ON FUNCTION master.ktt_pn_cho_phep() TO app_web;
            REVOKE ALL ON SCHEMA bao_mat FROM app_web;
            REVOKE TRUNCATE, DELETE ON ALL TABLES IN SCHEMA master, kho, nhat_ky FROM app_web;
        END IF;
    END $$""",
) + _rls_statements()

M0010 = tuple(s for s in M0010_V1_BAN_GIAO_DAU if "lien_ket_huy_co_vet" not in s)

# ---------------------------------------------------------------------------
# 0011 — CRM-01 sửa sau review độc lập 02: danh tính phiên fail-closed (ID + login khớp), RLS theo pháp nhân + module, bảng con,
#        bất biến bản/tham số/lịch đã duyệt, chặn chèn bản đã duyệt, FK cùng pháp nhân/cùng hợp đồng, vân tay lần kiểm, V3/V4,
#        hiệu lực theo ngày, khóa hợp đồng trước khi nối tiền, link HUY lịch sử trước v10, đăng ký file soát CRM.
# ---------------------------------------------------------------------------
_RLS_V11 = (
    ("master.hop_dong", "master.ktt_duoc(phap_nhan_id, 'CRM')"),
    ("master.hop_dong_phien_ban", "master.ktt_duoc((SELECT h.phap_nhan_id FROM master.hop_dong h WHERE h.id = hop_dong_id), 'CRM')"),
    ("master.hop_dong_tham_so", "master.ktt_duoc((SELECT h.phap_nhan_id FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = phien_ban_id), 'CRM')"),
    ("master.lich_thu", "master.ktt_duoc(phap_nhan_id, 'CRM')"),
    ("master.loai_hinh_doanh_thu", "master.ktt_duoc(phap_nhan_id, 'CRM')"),
    ("master.doi_tac_ma_junsky", "phap_nhan_id IN (SELECT master.ktt_pn_cho_phep())"),
    ("master.du_an", "phap_nhan_id IN (SELECT master.ktt_pn_cho_phep())"),
    ("master.nhan_vien", "master.ktt_duoc(phap_nhan_id, 'M7')"),
    ("kho.tep_goc", "phap_nhan_id IN (SELECT master.ktt_pn_cho_phep())"),
    ("kho.chung_tu", "master.ktt_duoc(phap_nhan_id, CASE WHEN loai = 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END)"),
    ("kho.chung_tu_dong", "(SELECT master.ktt_duoc(c.phap_nhan_id, CASE WHEN c.loai = 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END) FROM kho.chung_tu c WHERE c.id = chung_tu_id)"),
    ("kho.de_xuat", "master.ktt_duoc((SELECT c.phap_nhan_id FROM kho.chung_tu c WHERE c.id = chung_tu_id), 'M1')"),
    ("kho.de_xuat_dong", "master.ktt_duoc((SELECT c.phap_nhan_id FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id WHERE x.id = de_xuat_id), 'M1')"),
    ("kho.lien_ket_chung_tu", "master.ktt_duoc(phap_nhan_id, 'M1')"),
    ("kho.viec_can_duyet", "master.ktt_duoc(phap_nhan_id, coalesce(module, 'M1'))"),
    ("kho.lo_xuat", "master.ktt_duoc(phap_nhan_id, coalesce(du_lieu->>'module', 'M1'))"),
)
_RLS_MOI_V11 = ("master.nhan_vien", "kho.chung_tu_dong", "kho.de_xuat_dong", "kho.lo_xuat")


def _rls_v11() -> tuple[str, ...]:
    out = []
    for table, expr in _RLS_V11:
        name = table.split(".")[1]
        e = expr.replace("'", "''")
        if table in _RLS_MOI_V11:
            out.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        out.append(f"""DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_pham_vi_web ON {table}';
                EXECUTE 'CREATE POLICY {name}_pham_vi_web ON {table} TO app_web USING ({e}) WITH CHECK ({e})';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_ung_dung_cu ON {table}';
                EXECUTE 'CREATE POLICY {name}_ung_dung_cu ON {table} TO app_ke_toan USING (true) WITH CHECK (true)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_chi_doc ON {table}';
                EXECUTE 'CREATE POLICY {name}_chi_doc ON {table} FOR SELECT TO app_doc USING (true)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_cong_ai ON {table}';
                EXECUTE 'CREATE POLICY {name}_cong_ai ON {table} FOR SELECT TO app_cong_ai USING (true)';
            END IF;
        END $$""")
    return tuple(out)


M0011 = (
    # --- danh tính phiên: ID và login phải cùng có và cùng một người dùng hoạt động (fail-closed)
    """CREATE OR REPLACE FUNCTION master.ktt_danh_tinh() RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT n.dang_nhap FROM master.nguoi_dung n
        WHERE n.trang_thai = 'HOAT_DONG'
          AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
          AND n.dang_nhap = nullif(current_setting('ktt.nguoi_dung_dang_nhap', true), '')
        $$""",
    """CREATE OR REPLACE FUNCTION master.ktt_pn_cho_phep() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT q.phap_nhan_id FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
        WHERE n.dang_nhap = master.ktt_danh_tinh()
        $$""",
    """CREATE OR REPLACE FUNCTION master.ktt_duoc(pn uuid, p_module text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.dang_nhap = master.ktt_danh_tinh() AND q.phap_nhan_id = pn AND p_module = ANY (q.module))
        $$""",
    """CREATE OR REPLACE FUNCTION master.ktt_co_vai(pn uuid, vai text[], loai_viec text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.dang_nhap = master.ktt_danh_tinh() AND q.phap_nhan_id = pn AND n.vai_tro = ANY (vai)
                         AND (loai_viec IS NULL OR loai_viec = ANY (q.duyet_loai_viec)))
        $$""",
    """CREATE OR REPLACE FUNCTION master.ktt_ngay() RETURNS date
        LANGUAGE sql STABLE AS $$ SELECT coalesce(nullif(current_setting('ktt.ngay_hieu_luc', true), '')::date, current_date) $$""",
    """CREATE OR REPLACE FUNCTION master.ktt_la_chu(bang regclass) RETURNS boolean
        LANGUAGE sql STABLE AS $$ SELECT pg_has_role(current_user, (SELECT relowner FROM pg_class WHERE oid = bang), 'MEMBER') $$""",
    # --- trạng thái mới THAY_THE (bản trích lại thay bản chờ, có vết) + vân tay lần kiểm
    "ALTER TABLE master.hop_dong_phien_ban DROP CONSTRAINT hop_dong_phien_ban_trang_thai_check",
    "ALTER TABLE master.hop_dong_phien_ban ADD CONSTRAINT hop_dong_phien_ban_trang_thai_check CHECK (trang_thai IN ('CHO_DUYET','DA_DUYET','TU_CHOI','THAY_THE'))",
    "ALTER TABLE master.hop_dong_phien_ban ADD COLUMN kiem_van_tay text",
    # --- tham số: trạng thái căn cứ đầy đủ + xác nhận thủ công từng tham số có vết
    "ALTER TABLE master.hop_dong_tham_so DROP CONSTRAINT hop_dong_tham_so_trang_thai_can_cu_check",
    """ALTER TABLE master.hop_dong_tham_so ADD CONSTRAINT hop_dong_tham_so_trang_thai_can_cu_check CHECK (trang_thai_can_cu IN
        ('CO_CAN_CU','KHONG_QUY_DINH','CAN_CU_KHONG_KHOP','CHUA_DOI_CHIEU_NGUON','CHUA_DOI_CHIEU_VI_TRI','VI_TRI_KHONG_KHOP',
         'GIA_TRI_KHONG_KHOP_TRICH_DAN','SUY_RA'))""",
    "ALTER TABLE master.hop_dong_tham_so ADD COLUMN xac_nhan_thu_cong jsonb",
    # --- FK cùng pháp nhân / cùng hợp đồng
    "ALTER TABLE master.loai_hinh_doanh_thu ADD CONSTRAINT loai_hinh_id_pn_uq UNIQUE (id, phap_nhan_id)",
    "ALTER TABLE master.du_an ADD CONSTRAINT du_an_id_pn_uq UNIQUE (id, phap_nhan_id)",
    "ALTER TABLE master.hop_dong_phien_ban ADD CONSTRAINT phien_ban_id_hd_uq UNIQUE (id, hop_dong_id)",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_loai_hinh_cung_pn FOREIGN KEY (loai_hinh_dt_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id)",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_du_an_cung_pn FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id)",
    """ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_hien_hanh_cung_hd FOREIGN KEY (phien_ban_hien_hanh, id)
        REFERENCES master.hop_dong_phien_ban (id, hop_dong_id) DEFERRABLE INITIALLY DEFERRED""",
    "ALTER TABLE master.hop_dong_phien_ban ADD CONSTRAINT phien_ban_thay_cho_cung_hd FOREIGN KEY (thay_cho_id, hop_dong_id) REFERENCES master.hop_dong_phien_ban (id, hop_dong_id)",
    # --- phần nghĩa vụ đã có tiền nối (bỏ qua RLS để mọi người tính cùng một số), phiên bản hiệu lực theo ngày
    """CREATE OR REPLACE FUNCTION master.da_lien_ket(hd uuid, khoa text) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(sum(k.so_tien_khop_minor), 0)::bigint FROM kho.lien_ket_chung_tu k JOIN master.lich_thu x ON x.id = k.lich_thu_id
        JOIN master.hop_dong_phien_ban px ON px.id = x.phien_ban_id WHERE k.trang_thai <> 'HUY' AND px.hop_dong_id = hd AND x.khoa_nghia_vu = khoa
        $$""",
    """CREATE OR REPLACE FUNCTION master.da_lien_ket_dong(lich uuid) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(sum(k.so_tien_khop_minor), 0)::bigint FROM kho.lien_ket_chung_tu k WHERE k.trang_thai <> 'HUY' AND k.lich_thu_id = lich
        $$""",
    """CREATE OR REPLACE FUNCTION master.phien_ban_hieu_luc(hd uuid, d date) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT id FROM master.hop_dong_phien_ban WHERE hop_dong_id = hd AND trang_thai = 'DA_DUYET'
          AND (valid_from AT TIME ZONE 'UTC')::date <= d AND (valid_to IS NULL OR d < (valid_to AT TIME ZONE 'UTC')::date)
        ORDER BY phien_ban DESC LIMIT 1
        $$""",
    """CREATE OR REPLACE FUNCTION master.van_tay_phien_ban(pb uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT md5(concat_ws('|', p.loai, p.so_phu_luc, p.ngay::text, p.ngay_hieu_luc::text, p.thay_cho_id::text, p.chung_tu_id::text,
                   p.loai_hinh_dt_id::text, p.tham_so::text, h.doi_tac_id::text, h.du_an_id::text, h.loai_hinh_dt_id::text, h.ma_noi_bo, h.so_hop_dong,
                   (SELECT string_agg(concat_ws('~', t.ten, t.ma_nguon, t.gia_tri, t.gia_tri_tho, t.don_vi, t.trich_dan, t.dieu_khoan, t.trang_thai_can_cu,
                           t.gia_tri_typed::text, t.loi::text, t.xac_nhan_thu_cong::text, t.ke_thua_tu::text), '#' ORDER BY t.ten)
                    FROM master.hop_dong_tham_so t WHERE t.phien_ban_id = p.id)))
        FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = pb
        $$""",
    # --- hợp đồng: mapping đối tác theo pháp nhân, khóa định danh, con trỏ bản duyệt, đổi mapping chỉ trước khi có bản duyệt
    """CREATE OR REPLACE FUNCTION master.hop_dong_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE cu uuid;
        BEGIN
            IF NEW.doi_tac_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.doi_tac_ma_junsky m WHERE m.doi_tac_id = NEW.doi_tac_id
                    AND m.phap_nhan_id = NEW.phap_nhan_id AND m.valid_to IS NULL) THEN
                RAISE EXCEPTION 'DOI_TAC_KHONG_THUOC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                cu := OLD.phien_ban_hien_hanh;
                IF (NEW.phap_nhan_id, NEW.loai, NEW.ma_noi_bo, NEW.so_hop_dong) IS DISTINCT FROM (OLD.phap_nhan_id, OLD.loai, OLD.ma_noi_bo, OLD.so_hop_dong) THEN
                    RAISE EXCEPTION 'HOP_DONG_KHONG_DOI_DINH_DANH' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.phien_ban_hien_hanh IS NOT NULL AND (NEW.doi_tac_id, NEW.du_an_id, NEW.loai_hinh_dt_id) IS DISTINCT FROM (OLD.doi_tac_id, OLD.du_an_id, OLD.loai_hinh_dt_id) THEN
                    RAISE EXCEPTION 'HOP_DONG_DA_DUYET_KHONG_DOI_MAPPING' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.phien_ban_hien_hanh IS DISTINCT FROM cu AND NEW.phien_ban_hien_hanh IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM master.hop_dong_phien_ban p WHERE p.id = NEW.phien_ban_hien_hanh AND p.hop_dong_id = NEW.id AND p.trang_thai = 'DA_DUYET') THEN
                RAISE EXCEPTION 'CON_TRO_PHIEN_BAN_SAI' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hop_dong_kiem BEFORE INSERT OR UPDATE ON master.hop_dong FOR EACH ROW EXECUTE FUNCTION master.hop_dong_kiem()",
    # --- phiên bản: chỉ chèn ở CHO_DUYET; bất biến khi đã chốt; kiểm/duyệt fail-closed theo danh tính phiên + vân tay
    """CREATE OR REPLACE FUNCTION master.phien_ban_chen() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pn uuid;
        BEGIN
            IF NEW.trang_thai <> 'CHO_DUYET' OR NEW.kiem_boi IS NOT NULL OR NEW.kiem_luc IS NOT NULL OR NEW.kiem_van_tay IS NOT NULL
               OR NEW.nguoi_duyet IS NOT NULL OR NEW.duyet_luc IS NOT NULL THEN
                RAISE EXCEPTION 'PHIEN_BAN_MOI_PHAI_CHO_DUYET' USING ERRCODE = 'P0001';
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF NEW.loai_hinh_dt_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.loai_hinh_doanh_thu WHERE id = NEW.loai_hinh_dt_id AND phap_nhan_id = pn) THEN
                RAISE EXCEPTION 'PROFILE_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.chung_tu_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kho.chung_tu WHERE id = NEW.chung_tu_id AND phap_nhan_id = pn AND loai = 'HOP_DONG_TEP') THEN
                RAISE EXCEPTION 'CHUNG_TU_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER phien_ban_chen BEFORE INSERT ON master.hop_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION master.phien_ban_chen()",
    """CREATE OR REPLACE FUNCTION master.phien_ban_kiem_duyet() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pn uuid; ai text := master.ktt_danh_tinh();
        BEGIN
            IF OLD.trang_thai IN ('TU_CHOI','THAY_THE') THEN
                RAISE EXCEPTION 'PHIEN_BAN_DA_CHOT: phiên bản % không sửa được', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'DA_DUYET' THEN
                IF ROW(NEW.id, NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.so_phu_luc, NEW.ngay, NEW.tham_so, NEW.tep_goc_id, NEW.nguon, NEW.trang_thai,
                       NEW.nguoi_duyet, NEW.duyet_luc, NEW.valid_from, NEW.thay_cho_id, NEW.ngay_hieu_luc, NEW.chung_tu_id, NEW.loai_hinh_dt_id, NEW.kiem_boi,
                       NEW.kiem_luc, NEW.ly_do, NEW.tao_boi, NEW.tao_luc, NEW.kiem_van_tay)
                   IS DISTINCT FROM ROW(OLD.id, OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.so_phu_luc, OLD.ngay, OLD.tham_so, OLD.tep_goc_id, OLD.nguon, OLD.trang_thai,
                       OLD.nguoi_duyet, OLD.duyet_luc, OLD.valid_from, OLD.thay_cho_id, OLD.ngay_hieu_luc, OLD.chung_tu_id, OLD.loai_hinh_dt_id, OLD.kiem_boi,
                       OLD.kiem_luc, OLD.ly_do, OLD.tao_boi, OLD.tao_luc, OLD.kiem_van_tay) THEN
                    RAISE EXCEPTION 'PHIEN_BAN_DA_DUYET_BAT_BIEN: chỉ đóng hiệu lực (valid_to) khi có bản thay' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF (NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.nguon, NEW.tao_boi, NEW.tao_luc) IS DISTINCT FROM (OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.nguon, OLD.tao_boi, OLD.tao_luc) THEN
                RAISE EXCEPTION 'PHIEN_BAN_KHONG_DOI_DINH_DANH' USING ERRCODE = 'P0001';
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF (NEW.kiem_boi, NEW.kiem_luc, NEW.kiem_van_tay) IS DISTINCT FROM (OLD.kiem_boi, OLD.kiem_luc, OLD.kiem_van_tay) THEN
                IF NEW.kiem_boi IS NULL THEN
                    IF NEW.kiem_luc IS NOT NULL OR NEW.kiem_van_tay IS NOT NULL THEN
                        RAISE EXCEPTION 'KIEM_KHONG_HOP_LE' USING ERRCODE = 'P0001';
                    END IF;
                ELSIF ai IS NULL OR ai <> NEW.kiem_boi OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
                      OR NEW.kiem_luc IS NULL OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_KIEM: % không phải kế toán của phiên hiện tại trên pháp nhân', NEW.kiem_boi USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.trang_thai IN ('DA_DUYET','TU_CHOI') THEN
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.nguoi_duyet OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NEW.duyet_luc IS NULL THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_DUYET: % không phải CFO có quyền V3 của phiên hiện tại', NEW.nguoi_duyet USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'DA_DUYET' AND (NEW.kiem_luc IS NULL OR NEW.kiem_boi IS NOT DISTINCT FROM NEW.nguoi_duyet
                                                    OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id)) THEN
                    RAISE EXCEPTION 'KIEM_DA_HET_HIEU_LUC: chưa kiểm trước hoặc nội dung/mapping đã đổi sau lần kiểm' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai = 'THAY_THE' THEN
                IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_THAY_THE' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai <> 'CHO_DUYET' THEN
                RAISE EXCEPTION 'TRANG_THAI_PHIEN_BAN_SAI' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- tham số và lịch: chỉ ghi khi phiên bản cho phép; lịch chỉ sinh trong giao dịch duyệt; lịch chỉ đổi trạng thái thu
    """CREATE OR REPLACE FUNCTION master.tham_so_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE tt text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.phien_ban_id IS DISTINCT FROM OLD.phien_ban_id THEN
                RAISE EXCEPTION 'THAM_SO_KHONG_DOI_PHIEN_BAN' USING ERRCODE = 'P0001';
            END IF;
            SELECT trang_thai INTO tt FROM master.hop_dong_phien_ban WHERE id = coalesce(NEW.phien_ban_id, OLD.phien_ban_id);
            IF tt IS DISTINCT FROM 'CHO_DUYET' THEN
                RAISE EXCEPTION 'THAM_SO_BAT_BIEN: phiên bản % không còn chờ duyệt', tt USING ERRCODE = 'P0001';
            END IF;
            RETURN coalesce(NEW, OLD);
        END $$""",
    "CREATE TRIGGER tham_so_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.hop_dong_tham_so FOR EACH ROW EXECUTE FUNCTION master.tham_so_kiem()",
    """CREATE OR REPLACE FUNCTION master.lich_thu_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE p record; t record;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'LICH_BAT_BIEN: không xóa lịch nghĩa vụ' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(NEW.id, NEW.phien_ban_id, NEW.dot, NEW.moc, NEW.ty_le, NEW.so_tien_minor, NEW.tien_te, NEW.han, NEW.loai, NEW.phap_nhan_id,
                       NEW.khoa_nghia_vu, NEW.thay_cho_id, NEW.nguon_tham_so, NEW.co_so, NEW.ghi_chu)
                   IS DISTINCT FROM ROW(OLD.id, OLD.phien_ban_id, OLD.dot, OLD.moc, OLD.ty_le, OLD.so_tien_minor, OLD.tien_te, OLD.han, OLD.loai, OLD.phap_nhan_id,
                       OLD.khoa_nghia_vu, OLD.thay_cho_id, OLD.nguon_tham_so, OLD.co_so, OLD.ghi_chu) THEN
                    RAISE EXCEPTION 'LICH_BAT_BIEN: chỉ cập nhật trạng thái thu' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            SELECT pb.trang_thai, pb.duyet_luc, pb.hop_dong_id, h.phap_nhan_id INTO p FROM master.hop_dong_phien_ban pb JOIN master.hop_dong h ON h.id = pb.hop_dong_id WHERE pb.id = NEW.phien_ban_id;
            IF p.trang_thai IS DISTINCT FROM 'DA_DUYET' OR p.duyet_luc IS DISTINCT FROM now() THEN
                RAISE EXCEPTION 'LICH_CHI_SINH_KHI_DUYET' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.phap_nhan_id IS DISTINCT FROM p.phap_nhan_id THEN
                RAISE EXCEPTION 'LICH_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.thay_cho_id IS NOT NULL THEN
                SELECT x.khoa_nghia_vu, xp.hop_dong_id INTO t FROM master.lich_thu x JOIN master.hop_dong_phien_ban xp ON xp.id = x.phien_ban_id WHERE x.id = NEW.thay_cho_id;
                IF t.hop_dong_id IS DISTINCT FROM p.hop_dong_id OR t.khoa_nghia_vu IS DISTINCT FROM NEW.khoa_nghia_vu THEN
                    RAISE EXCEPTION 'LICH_THAY_CHO_SAI_NGHIA_VU' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lich_thu_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.lich_thu FOR EACH ROW EXECUTE FUNCTION master.lich_thu_kiem()",
    # --- việc V3/V4: hoàn tất (DA_DUYET) chỉ bởi đúng người của phiên có quyền loại việc trên pháp nhân (vai trò ứng dụng).
    #     KHÔNG SECURITY DEFINER: ktt_la_chu phải thấy vai trò thật của phiên (definer sẽ luôn là chủ bảng).
    """CREATE OR REPLACE FUNCTION kho.viec_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NEW.trang_thai = 'DA_DUYET' AND OLD.trang_thai <> 'DA_DUYET' AND NOT master.ktt_la_chu('kho.viec_can_duyet'::regclass) THEN
                IF master.ktt_danh_tinh() IS NULL OR master.ktt_danh_tinh() IS DISTINCT FROM NEW.duyet_boi
                   OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['CFO','KE_TOAN','KE_TOAN_TRUONG'], NEW.loai) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_LOAI_VIEC: % không có quyền %', NEW.duyet_boi, NEW.loai USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER viec_kiem BEFORE UPDATE ON kho.viec_can_duyet FOR EACH ROW EXECUTE FUNCTION kho.viec_kiem()",
    # --- link: dòng HUY lịch sử trước v10 (không có người/thời điểm hủy) được đánh dấu, không bịa; dòng mới phải đủ vết
    "ALTER TABLE kho.lien_ket_chung_tu ADD COLUMN IF NOT EXISTS huy_khong_vet_truoc_v10 boolean NOT NULL DEFAULT false",
    "UPDATE kho.lien_ket_chung_tu SET huy_khong_vet_truoc_v10 = true WHERE trang_thai = 'HUY' AND (huy_luc IS NULL OR huy_boi IS NULL OR ly_do_huy IS NULL)",
    "ALTER TABLE kho.lien_ket_chung_tu DROP CONSTRAINT IF EXISTS lien_ket_huy_co_vet",
    """ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_huy_co_vet
        CHECK (trang_thai <> 'HUY' OR huy_khong_vet_truoc_v10 OR (huy_luc IS NOT NULL AND huy_boi IS NOT NULL AND ly_do_huy IS NOT NULL))""",
    """CREATE OR REPLACE FUNCTION kho.lien_ket_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE
            a record; b record; l record; hd uuid; tong_a bigint; d date := master.ktt_ngay();
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.huy_khong_vet_truoc_v10 IS DISTINCT FROM OLD.huy_khong_vet_truoc_v10 THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai = 'HUY' AND NEW.trang_thai <> 'HUY' THEN
                    RAISE EXCEPTION 'LIEN_KET_DA_HUY: liên kết đã hủy không mở lại; tạo liên kết mới' USING ERRCODE = 'P0001';
                END IF;
                IF ROW(NEW.id, NEW.phap_nhan_id, NEW.chung_tu_a_id, NEW.chung_tu_b_id, NEW.loai, NEW.so_tien_khop_minor, NEW.tien_te, NEW.nguon_suy_luan,
                       NEW.do_tin_cay, NEW.nguoi_duyet, NEW.duyet_luc, NEW.entry_dm, NEW.tao_luc, NEW.lich_thu_id, NEW.hop_dong_id, NEW.khoa_idempotency,
                       NEW.tao_boi, NEW.can_cu)
                   IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.chung_tu_a_id, OLD.chung_tu_b_id, OLD.loai, OLD.so_tien_khop_minor, OLD.tien_te, OLD.nguon_suy_luan,
                       OLD.do_tin_cay, OLD.nguoi_duyet, OLD.duyet_luc, OLD.entry_dm, OLD.tao_luc, OLD.lich_thu_id, OLD.hop_dong_id, OLD.khoa_idempotency,
                       OLD.tao_boi, OLD.can_cu) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA: chỉ đổi trạng thái/hủy; sửa = hủy + tạo mới' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai = 'HUY' AND (NEW.huy_luc, NEW.huy_boi, NEW.ly_do_huy) IS DISTINCT FROM (OLD.huy_luc, OLD.huy_boi, OLD.ly_do_huy) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.huy_khong_vet_truoc_v10 OR NEW.trang_thai = 'HUY' THEN
                RAISE EXCEPTION 'LIEN_KET_MOI_KHONG_HOP_LE' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.lich_thu_id IS NOT NULL THEN  -- khóa hợp đồng TRƯỚC (cùng thứ tự với duyệt phụ lục), rồi khoản tiền, rồi đợt
                SELECT p.hop_dong_id INTO hd FROM master.lich_thu x JOIN master.hop_dong_phien_ban p ON p.id = x.phien_ban_id WHERE x.id = NEW.lich_thu_id;
                PERFORM 1 FROM master.hop_dong WHERE id = hd FOR UPDATE;
            END IF;
            SELECT * INTO a FROM kho.chung_tu WHERE id = NEW.chung_tu_a_id FOR UPDATE;
            SELECT * INTO b FROM kho.chung_tu WHERE id = NEW.chung_tu_b_id;
            IF a.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR b.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.lich_thu_id IS NULL THEN
                RETURN NEW;
            END IF;
            SELECT lt.*, p.hop_dong_id AS hd, p.chung_tu_id AS ct_phien_ban, p.trang_thai AS pb_trang_thai, p.phien_ban AS so_pb
                INTO l FROM master.lich_thu lt JOIN master.hop_dong_phien_ban p ON p.id = lt.phien_ban_id WHERE lt.id = NEW.lich_thu_id FOR UPDATE OF lt;
            IF l.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF l.pb_trang_thai IS DISTINCT FROM 'DA_DUYET' OR l.phien_ban_id IS DISTINCT FROM master.phien_ban_hieu_luc(l.hd, d) THEN
                RAISE EXCEPTION 'LICH_KHONG_HIEU_LUC: đợt không thuộc phiên bản hiệu lực ngày %', d USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM master.hop_dong_phien_ban v WHERE v.hop_dong_id = l.hd AND v.trang_thai = 'DA_DUYET' AND v.phien_ban > l.so_pb
                       AND NOT EXISTS (SELECT 1 FROM master.lich_thu y WHERE y.phien_ban_id = v.id AND y.khoa_nghia_vu = l.khoa_nghia_vu
                                       AND (y.so_tien_minor, y.tien_te, y.han, y.moc, y.loai, y.dot, y.co_so) IS NOT DISTINCT FROM (l.so_tien_minor, l.tien_te, l.han, l.moc, l.loai, l.dot, l.co_so))) THEN
                RAISE EXCEPTION 'NGHIA_VU_SAP_THAY_DOI: phụ lục đã duyệt sẽ đổi/bỏ đợt này — xử lý theo phụ lục' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai <> 'HOP_DONG_DOT_TIEN' OR a.loai <> 'SAO_KE' OR a.chieu IS DISTINCT FROM 'THU' OR NEW.chung_tu_b_id IS DISTINCT FROM l.ct_phien_ban THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_THAM_CHIEU: tiền thu ↔ đợt phải nối với chứng từ của đúng phiên bản' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.hop_dong_id IS DISTINCT FROM l.hd THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_HOP_DONG' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.so_tien_khop_minor IS NULL OR NEW.so_tien_khop_minor <= 0 OR l.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_SO_TIEN: cần số tiền dương và đợt có số tiền' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.tien_te IS DISTINCT FROM a.tien_te OR NEW.tien_te IS DISTINCT FROM l.tien_te OR a.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_TIEN_TE: không bù trừ khác loại tiền' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(sum(so_tien_khop_minor), 0) INTO tong_a FROM kho.lien_ket_chung_tu
                WHERE chung_tu_a_id = NEW.chung_tu_a_id AND trang_thai <> 'HUY' AND lich_thu_id IS NOT NULL;
            IF tong_a + NEW.so_tien_khop_minor > a.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_TIEN_KHA_DUNG: % + % > %', tong_a, NEW.so_tien_khop_minor, a.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            IF master.da_lien_ket(l.hd, l.khoa_nghia_vu) + NEW.so_tien_khop_minor > l.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_NGHIA_VU: đã nối % + % > %', master.da_lien_ket(l.hd, l.khoa_nghia_vu), NEW.so_tien_khop_minor, l.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- quyền vai trò web bổ sung: đăng ký file soát CRM, hàm mới; bảo mật không đổi
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT, INSERT ON kho.lo_xuat TO app_web;
            GRANT EXECUTE ON FUNCTION master.ktt_danh_tinh(), master.ktt_duoc(uuid, text), master.ktt_co_vai(uuid, text[], text), master.ktt_ngay(),
                master.da_lien_ket(uuid, text), master.da_lien_ket_dong(uuid), master.phien_ban_hieu_luc(uuid, date), master.van_tay_phien_ban(uuid) TO app_web;
        END IF;
    END $$""",
) + _rls_v11()

# ---------------------------------------------------------------------------
# 0012 — CRM-01 sửa sau review 03 (M0011 đã có trong DB giữ lại: không sửa, chỉ thêm):
#   (1) biên hiệu lực bản đã duyệt: valid_to chỉ được đóng MỘT lần, bởi CFO có V3 của phiên, đúng bằng valid_from của bản thay
#       đã duyệt trong cùng giao dịch, cùng hợp đồng, thay_cho = bản này; không mở lại, không đóng lại về mốc khác;
#   (2) bốn hàm SECURITY DEFINER thành hàm nội bộ (chỉ trigger của chủ CSDL gọi; thu hồi PUBLIC và app_web); ứng dụng dùng hàm
#       master.crm_* kiểm danh tính phiên + pháp nhân + module CRM trên chính ID tham số, ngoài phạm vi trả NULL (không lộ tồn tại).
# ---------------------------------------------------------------------------
M0012 = (
    """CREATE OR REPLACE FUNCTION master.phien_ban_kiem_duyet() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pn uuid; ai text := master.ktt_danh_tinh();
        BEGIN
            IF OLD.trang_thai IN ('TU_CHOI','THAY_THE') THEN
                RAISE EXCEPTION 'PHIEN_BAN_DA_CHOT: phiên bản % không sửa được', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.hop_dong WHERE id = OLD.hop_dong_id;
            IF OLD.trang_thai = 'DA_DUYET' THEN
                IF ROW(NEW.id, NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.so_phu_luc, NEW.ngay, NEW.tham_so, NEW.tep_goc_id, NEW.nguon, NEW.trang_thai,
                       NEW.nguoi_duyet, NEW.duyet_luc, NEW.valid_from, NEW.thay_cho_id, NEW.ngay_hieu_luc, NEW.chung_tu_id, NEW.loai_hinh_dt_id, NEW.kiem_boi,
                       NEW.kiem_luc, NEW.ly_do, NEW.tao_boi, NEW.tao_luc, NEW.kiem_van_tay)
                   IS DISTINCT FROM ROW(OLD.id, OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.so_phu_luc, OLD.ngay, OLD.tham_so, OLD.tep_goc_id, OLD.nguon, OLD.trang_thai,
                       OLD.nguoi_duyet, OLD.duyet_luc, OLD.valid_from, OLD.thay_cho_id, OLD.ngay_hieu_luc, OLD.chung_tu_id, OLD.loai_hinh_dt_id, OLD.kiem_boi,
                       OLD.kiem_luc, OLD.ly_do, OLD.tao_boi, OLD.tao_luc, OLD.kiem_van_tay) THEN
                    RAISE EXCEPTION 'PHIEN_BAN_DA_DUYET_BAT_BIEN: chỉ đóng hiệu lực (valid_to) khi có bản thay' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.valid_to IS NOT DISTINCT FROM OLD.valid_to THEN
                    RETURN NEW;
                END IF;
                IF OLD.valid_to IS NOT NULL OR NEW.valid_to IS NULL THEN
                    RAISE EXCEPTION 'HIEU_LUC_DA_DONG: biên hiệu lực bản đã duyệt không mở lại hay đổi mốc' USING ERRCODE = 'P0001';
                END IF;
                IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NOT EXISTS (
                        SELECT 1 FROM master.hop_dong_phien_ban r WHERE r.hop_dong_id = OLD.hop_dong_id AND r.thay_cho_id = OLD.id AND r.id <> OLD.id
                          AND r.trang_thai = 'DA_DUYET' AND r.nguoi_duyet = ai AND r.duyet_luc = now() AND r.valid_from = NEW.valid_to) THEN
                    RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: chỉ CFO có V3 đóng bản cũ đúng mốc của bản thay vừa duyệt' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF (NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.nguon, NEW.tao_boi, NEW.tao_luc) IS DISTINCT FROM (OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.nguon, OLD.tao_boi, OLD.tao_luc) THEN
                RAISE EXCEPTION 'PHIEN_BAN_KHONG_DOI_DINH_DANH' USING ERRCODE = 'P0001';
            END IF;
            IF (NEW.valid_from, NEW.valid_to) IS DISTINCT FROM (OLD.valid_from, OLD.valid_to) AND NEW.trang_thai <> 'DA_DUYET' THEN
                RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: biên hiệu lực chỉ đặt khi duyệt' USING ERRCODE = 'P0001';
            END IF;
            IF (NEW.kiem_boi, NEW.kiem_luc, NEW.kiem_van_tay) IS DISTINCT FROM (OLD.kiem_boi, OLD.kiem_luc, OLD.kiem_van_tay) THEN
                IF NEW.kiem_boi IS NULL THEN
                    IF NEW.kiem_luc IS NOT NULL OR NEW.kiem_van_tay IS NOT NULL THEN
                        RAISE EXCEPTION 'KIEM_KHONG_HOP_LE' USING ERRCODE = 'P0001';
                    END IF;
                ELSIF ai IS NULL OR ai <> NEW.kiem_boi OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
                      OR NEW.kiem_luc IS NULL OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_KIEM: % không phải kế toán của phiên hiện tại trên pháp nhân', NEW.kiem_boi USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.trang_thai IN ('DA_DUYET','TU_CHOI') THEN
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.nguoi_duyet OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NEW.duyet_luc IS NULL THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_DUYET: % không phải CFO có quyền V3 của phiên hiện tại', NEW.nguoi_duyet USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'DA_DUYET' AND (NEW.kiem_luc IS NULL OR NEW.kiem_boi IS NOT DISTINCT FROM NEW.nguoi_duyet
                                                    OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id)) THEN
                    RAISE EXCEPTION 'KIEM_DA_HET_HIEU_LUC: chưa kiểm trước hoặc nội dung/mapping đã đổi sau lần kiểm' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'DA_DUYET' AND (NEW.valid_to IS NOT NULL OR NEW.duyet_luc IS DISTINCT FROM now()) THEN
                    RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: bản vừa duyệt chưa có mốc kết thúc' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai = 'THAY_THE' THEN
                IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_THAY_THE' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai <> 'CHO_DUYET' THEN
                RAISE EXCEPTION 'TRANG_THAI_PHIEN_BAN_SAI' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- hàm đọc cho ứng dụng: kiểm phạm vi trên chính ID tham số; ngoài phạm vi / không tồn tại đều NULL
    """CREATE OR REPLACE FUNCTION master.crm_da_lien_ket(hd uuid, khoa text) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT master.da_lien_ket(h.id, khoa) FROM master.hop_dong h
        WHERE h.id = hd AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_da_lien_ket_dong(lich uuid) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT master.da_lien_ket_dong(l.id) FROM master.lich_thu l
        WHERE l.id = lich AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(l.phap_nhan_id, 'CRM')
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_phien_ban_hieu_luc(hd uuid, d date) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.phien_ban_hieu_luc(h.id, d) FROM master.hop_dong h
        WHERE h.id = hd AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_van_tay_phien_ban(pb uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.van_tay_phien_ban(p.id) FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
        WHERE p.id = pb AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
        $$""",
    """REVOKE EXECUTE ON FUNCTION master.da_lien_ket(uuid, text), master.da_lien_ket_dong(uuid), master.phien_ban_hieu_luc(uuid, date),
        master.van_tay_phien_ban(uuid), master.crm_da_lien_ket(uuid, text), master.crm_da_lien_ket_dong(uuid),
        master.crm_phien_ban_hieu_luc(uuid, date), master.crm_van_tay_phien_ban(uuid) FROM PUBLIC""",
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            REVOKE EXECUTE ON FUNCTION master.da_lien_ket(uuid, text), master.da_lien_ket_dong(uuid), master.phien_ban_hieu_luc(uuid, date),
                master.van_tay_phien_ban(uuid) FROM app_web;
            GRANT EXECUTE ON FUNCTION master.crm_da_lien_ket(uuid, text), master.crm_da_lien_ket_dong(uuid), master.crm_phien_ban_hieu_luc(uuid, date),
                master.crm_van_tay_phien_ban(uuid) TO app_web;
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0013 — M9 typed + common M0/K1, K5 owner/action, money L8 (binding 28af9c1, proposal e3e9704f, R1–R4):
#   common: giao_tiep (intake metadata integration-only), snapshot/row/mapping/derivative, registry tiền tệ, identity khóa công ty nguồn;
#   R1 discriminator chủ sở hữu bất biến (chung_tu.module_nghiep_vu, việc, lô, link_purpose/allocation_model);
#   typed M9: alias/vay_phien_ban/khế ước + revision/lãi suất/sự kiện + mở rộng lich_tra_no (LEGACY | M9_TYPED);
#   R2 validator đồ thị + manifest canonical + dispatch kiểm/duyệt theo HĐ.loai; ghi typed chỉ INSERT có trigger (UPDATE/DELETE 42501);
#   R3 đích logic ổn định + tiêu thụ xuyên revision; R4 proof encoding tiền của chính BANK; child allocation + biên nhận + ngân sách chung
#   (CRM DIRECT cùng trừ một ngân sách với M9 CHILD).
# ---------------------------------------------------------------------------
_RLS_V13 = (
    ("master.hop_dong", "master.ktt_duoc(phap_nhan_id, CASE WHEN loai = 'VAY' THEN 'M9' ELSE 'CRM' END)"),
    ("master.hop_dong_phien_ban", "(SELECT master.ktt_duoc(h.phap_nhan_id, CASE WHEN h.loai = 'VAY' THEN 'M9' ELSE 'CRM' END) FROM master.hop_dong h WHERE h.id = hop_dong_id)"),
    ("master.hop_dong_tham_so", "(SELECT master.ktt_duoc(h.phap_nhan_id, CASE WHEN h.loai = 'VAY' THEN 'M9' ELSE 'CRM' END) FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = phien_ban_id)"),
    ("kho.chung_tu", "master.ktt_duoc(phap_nhan_id, module_nghiep_vu)"),
    ("kho.chung_tu_dong", "(SELECT master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id)"),
    ("master.lich_tra_no", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.anh_xa_nguon", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.ban_ghi_nguon", "phap_nhan_id IS NOT NULL AND master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.anh_chup_nguon", "EXISTS (SELECT 1 FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = anh_chup_nguon.id AND b.phap_nhan_id IS NOT NULL AND master.ktt_duoc(b.phap_nhan_id, 'M9')) OR nguoi = master.ktt_danh_tinh()"),
    ("giao_tiep.tep_tach_phap_nhan", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.vay_dinh_danh_nguon", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.vay_phien_ban", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.khe_uoc_vay", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.khe_uoc_vay_phien_ban", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("master.lai_suat_vay", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.su_kien_vay", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.su_kien_vay_phan", "master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.dich_phan_bo_tien", "master.ktt_duoc(phap_nhan_id, module_nghiep_vu)"),
    ("kho.lien_ket_phan_bo", "master.ktt_duoc(phap_nhan_id, 'M1') AND master.ktt_duoc(phap_nhan_id, 'M9')"),
    ("kho.bien_nhan_thao_tac", "master.ktt_duoc(phap_nhan_id, module)"),
)
_RLS_MOI_V13 = ("master.lich_tra_no", "master.anh_xa_nguon", "kho.ban_ghi_nguon", "kho.anh_chup_nguon", "giao_tiep.tep_tach_phap_nhan",
                "master.vay_dinh_danh_nguon", "master.vay_phien_ban", "master.khe_uoc_vay", "master.khe_uoc_vay_phien_ban", "master.lai_suat_vay",
                "kho.su_kien_vay", "kho.su_kien_vay_phan", "kho.dich_phan_bo_tien", "kho.lien_ket_phan_bo", "kho.bien_nhan_thao_tac")


def _rls_v13() -> tuple[str, ...]:
    """Cùng mẫu policy với v11 (app_web theo PN + module; vai trò cũ giữ phạm vi cũ). Hàm v11 giữ nguyên để không đổi checksum M0011."""
    out = []
    for table, expr in _RLS_V13:
        name = table.split(".")[1]
        e = expr.replace("'", "''")
        if table in _RLS_MOI_V13:
            out.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        out.append(f"""DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_pham_vi_web ON {table}';
                EXECUTE 'CREATE POLICY {name}_pham_vi_web ON {table} TO app_web USING ({e}) WITH CHECK ({e})';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_ung_dung_cu ON {table}';
                EXECUTE 'CREATE POLICY {name}_ung_dung_cu ON {table} TO app_ke_toan USING (true) WITH CHECK (true)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
                EXECUTE 'DROP POLICY IF EXISTS {name}_chi_doc ON {table}';
                EXECUTE 'CREATE POLICY {name}_chi_doc ON {table} FOR SELECT TO app_doc USING (true)';
            END IF;
        END $$""")
    return tuple(out)


_M9_KIEM_GHI = """
            -- ghi bản nháp typed M9: đúng PN của HĐ VAY, PB còn CHO_DUYET, kế toán có module M9 của phiên; khóa HĐ trước (thứ tự HĐ → con)
            SELECT h.phap_nhan_id, h.loai INTO hd FROM master.hop_dong h WHERE h.id = v_hd FOR UPDATE;
            IF hd.loai IS DISTINCT FROM 'VAY' OR hd.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'M9_SAI_HOP_DONG: dòng typed phải thuộc HĐ VAY cùng pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            IF master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M9')
               OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                RAISE EXCEPTION 'M9_KHONG_CO_QUYEN_GHI: cần kế toán có module M9 của phiên' USING ERRCODE = 'P0001';
            END IF;
"""

M0013 = (
    "SET LOCAL check_function_bodies = off",  # hàm SQL tham chiếu bảng tạo sau trong cùng migration; thân hàm vẫn được kiểm khi gọi
    "CREATE SCHEMA IF NOT EXISTS giao_tiep",
    # --- registry tiền tệ chung (M0): mô tả đơn vị; KHÔNG chứng minh encoding của một BANK cụ thể (R4)
    """CREATE TABLE master.don_vi_tien (
        ma char(3) NOT NULL CHECK (ma ~ '^[A-Z]{3}$'),
        scale smallint NOT NULL CHECK (scale BETWEEN 0 AND 6),
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        can_cu text NOT NULL,
        noi_dung_sha256 text NOT NULL CHECK (noi_dung_sha256 ~ '^[0-9a-f]{64}$'),
        ghi_nhan_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (ma, phien_ban))""",
    """INSERT INTO master.don_vi_tien (ma, scale, phien_ban, can_cu, noi_dung_sha256)
       SELECT v.ma, v.scale, 1, v.can_cu, encode(sha256(convert_to(v.ma || '|' || v.scale || '|1|' || v.can_cu, 'UTF8')), 'hex')
       FROM (VALUES ('VND', 0, 'DEMO_FIXTURE_CONTRACT: minor = đồng (Config V12 currency VND scale 0); không phải chính sách FX'),
                    ('USD', 2, 'DEMO_FIXTURE_CONTRACT: minor = cent; không phải chính sách FX')) AS v(ma, scale, can_cu)""",
    # --- khóa composite cùng PN cho tham chiếu mới
    "ALTER TABLE kho.tep_goc ADD CONSTRAINT tep_goc_pn_id_uq UNIQUE (phap_nhan_id, id)",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_pn_id_uq UNIQUE (phap_nhan_id, id)",
    "ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_pn_id_uq UNIQUE (phap_nhan_id, id)",
    "ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_pn_id_uq UNIQUE (phap_nhan_id, id)",
    # --- R1: chủ sở hữu chứng từ là discriminator do DB đặt/kiểm, bất biến (SAO_KE luôn M1; HO_SO_VAY → M9 của HĐ VAY cùng PN)
    "ALTER TABLE kho.chung_tu DROP CONSTRAINT chung_tu_loai_check",
    """ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_loai_check CHECK (loai IN ('SAO_KE','HD_MUA','HD_BAN','BANG_KE_THUE','RQ','NGHIEM_THU',
        'HOP_DONG_TEP','BANG_LUONG','BANG_KHAU_HAO','PHIEU_KHO','LENH_CHI','SO_JUNSKY','CONG_NO_MO','BUT_TOAN_DIEU_CHINH','KHAC','HO_SO_VAY'))""",
    "ALTER TABLE kho.chung_tu ADD COLUMN module_nghiep_vu text",
    "UPDATE kho.chung_tu SET module_nghiep_vu = CASE WHEN loai = 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END",
    "ALTER TABLE kho.chung_tu ALTER COLUMN module_nghiep_vu SET NOT NULL",
    "ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_module_check CHECK (module_nghiep_vu IN ('CRM','M1','M9'))",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_chu_so_huu() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE mong text;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF (NEW.module_nghiep_vu, NEW.loai, NEW.phap_nhan_id) IS DISTINCT FROM (OLD.module_nghiep_vu, OLD.loai, OLD.phap_nhan_id) THEN
                    RAISE EXCEPTION 'CHU_SO_HUU_BAT_BIEN: không đổi module/loại/pháp nhân của chứng từ' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.loai = 'HO_SO_VAY' AND NEW.du_lieu->>'hop_dong_id' IS DISTINCT FROM OLD.du_lieu->>'hop_dong_id' THEN
                    RAISE EXCEPTION 'CHU_SO_HUU_BAT_BIEN: không đổi chủ thể của hồ sơ vay' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            mong := CASE NEW.loai WHEN 'HOP_DONG_TEP' THEN 'CRM' WHEN 'HO_SO_VAY' THEN 'M9' ELSE 'M1' END;
            IF NEW.module_nghiep_vu IS NULL THEN
                NEW.module_nghiep_vu := mong;
            ELSIF NEW.module_nghiep_vu <> mong THEN
                RAISE EXCEPTION 'CHU_SO_HUU_SAI: chứng từ % thuộc module %', NEW.loai, mong USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai = 'HO_SO_VAY' AND NOT EXISTS (SELECT 1 FROM master.hop_dong h WHERE h.id::text = NEW.du_lieu->>'hop_dong_id'
                                                       AND h.loai = 'VAY' AND h.phap_nhan_id = NEW.phap_nhan_id) THEN
                RAISE EXCEPTION 'CHU_SO_HUU_SAI: hồ sơ vay phải trỏ HĐ VAY cùng pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_chu_so_huu BEFORE INSERT OR UPDATE ON kho.chung_tu FOR EACH ROW EXECUTE FUNCTION kho.chung_tu_chu_so_huu()",
    # --- R1: việc K5 resolve chủ thể theo allowlist typed; module việc phải là module chủ thể; chủ thể/module bất biến
    """CREATE OR REPLACE FUNCTION kho.kiem_chu_so_huu_noi_bo(loai_chu text, chu_id uuid) RETURNS TABLE (phap_nhan_id uuid, module text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT h.phap_nhan_id, CASE WHEN h.loai = 'VAY' THEN 'M9' ELSE 'CRM' END FROM master.hop_dong h WHERE loai_chu = 'master.hop_dong' AND h.id = chu_id
        UNION ALL
        SELECT h.phap_nhan_id, CASE WHEN h.loai = 'VAY' THEN 'M9' ELSE 'CRM' END FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
            WHERE loai_chu = 'master.hop_dong_phien_ban' AND p.id = chu_id
        UNION ALL
        SELECT c.phap_nhan_id, c.module_nghiep_vu FROM kho.chung_tu c WHERE loai_chu = 'kho.chung_tu' AND c.id = chu_id
        UNION ALL
        SELECT c.phap_nhan_id, 'M1' FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id WHERE loai_chu = 'kho.de_xuat' AND x.id = chu_id
        UNION ALL
        SELECT m.phap_nhan_id, 'M9' FROM master.anh_xa_nguon m WHERE loai_chu = 'master.anh_xa_nguon' AND m.id = chu_id
        $$""",
    "REVOKE EXECUTE ON FUNCTION kho.kiem_chu_so_huu_noi_bo(text, uuid) FROM PUBLIC",
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
    "CREATE TRIGGER viec_chu_so_huu BEFORE INSERT OR UPDATE ON kho.viec_can_duyet FOR EACH ROW EXECUTE FUNCTION kho.viec_chu_so_huu()",
    # --- R1: lô FILE_SOAT có chủ thể HĐ → module lô phải là module HĐ, cùng PN
    """CREATE OR REPLACE FUNCTION kho.lo_xuat_chu_so_huu() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE chu record;
        BEGIN
            IF TG_OP = 'UPDATE' AND (NEW.du_lieu->>'module', NEW.du_lieu->>'hop_dong_id', NEW.phap_nhan_id, NEW.loai)
                                    IS DISTINCT FROM (OLD.du_lieu->>'module', OLD.du_lieu->>'hop_dong_id', OLD.phap_nhan_id, OLD.loai) THEN
                RAISE EXCEPTION 'LO_CHU_THE_BAT_BIEN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.du_lieu ? 'hop_dong_id' THEN
                SELECT * INTO chu FROM kho.kiem_chu_so_huu_noi_bo('master.hop_dong', (NEW.du_lieu->>'hop_dong_id')::uuid);
                IF chu.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR chu.module IS DISTINCT FROM coalesce(NEW.du_lieu->>'module', 'M1') THEN
                    RAISE EXCEPTION 'LO_CHU_THE_SAI: lô phải cùng pháp nhân/module với HĐ chủ thể' USING ERRCODE = 'P0001';
                END IF;
            ELSIF coalesce(NEW.du_lieu->>'module', 'M1') IN ('CRM','M9') THEN
                RAISE EXCEPTION 'LO_CHU_THE_SAI: lô CRM/M9 phải có HĐ chủ thể' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lo_xuat_chu_so_huu BEFORE INSERT OR UPDATE ON kho.lo_xuat FOR EACH ROW EXECUTE FUNCTION kho.lo_xuat_chu_so_huu()",
    # --- M0/K1 intake: metadata raw toàn phần chỉ integration (không cấp app_web); snapshot/row/derivative/mapping
    """CREATE TABLE giao_tiep.tep_tiep_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        object_key text NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 0),
        media_type text NOT NULL,
        received_at_server timestamptz NOT NULL DEFAULT now(),
        access_domain text NOT NULL DEFAULT 'INTEGRATION_ONLY' CHECK (access_domain = 'INTEGRATION_ONLY'),
        nguoi text NOT NULL,
        UNIQUE (source_instance_id, raw_sha256))""",
    """CREATE TABLE kho.anh_chup_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        profile_code text NOT NULL,
        profile_version text NOT NULL,
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ '^[0-9a-f]{64}$'),
        source_code_sha256 text,
        ui_sha256 text,
        header_set_sha256 text,
        transport text NOT NULL,
        tep_tiep_nhan_id uuid NOT NULL REFERENCES giao_tiep.tep_tiep_nhan(id),
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        typed_sha256 text,
        received_started_at timestamptz NOT NULL,
        received_finished_at timestamptz NOT NULL,
        exported_at_source text,
        known_at_server timestamptz NOT NULL DEFAULT now(),
        coverage_kind text NOT NULL CHECK (coverage_kind IN ('FULL_SHAPE','PARTIAL','NONE')),
        coverage_manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
        state text NOT NULL CHECK (state IN ('VALIDATED','PARTIAL','INCONSISTENT','REJECTED')),
        error_code text,
        loi jsonb NOT NULL DEFAULT '[]'::jsonb,
        nguoi text NOT NULL,
        CHECK (received_finished_at >= received_started_at),
        UNIQUE (source_instance_id, profile_sha256, raw_sha256))""",
    """CREATE TABLE kho.ban_ghi_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        snapshot_id uuid NOT NULL REFERENCES kho.anh_chup_nguon(id),
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        section text NOT NULL,
        locator text NOT NULL,
        source_company_key text,
        source_key text,
        row_raw jsonb NOT NULL,
        row_raw_sha256 text NOT NULL CHECK (row_raw_sha256 ~ '^[0-9a-f]{64}$'),
        typed_sha256 text,
        validation_state text NOT NULL CHECK (validation_state IN ('HOP_LE','LOI','XUNG_DOT','MO_HO')),
        error_code text,
        mapping_revision_id uuid,
        UNIQUE (snapshot_id, section, locator),
        UNIQUE (phap_nhan_id, id))""",
    """CREATE TABLE master.dinh_danh_cong_ty_nguon (
        source_instance_id text NOT NULL,
        source_company_key text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (source_instance_id, source_company_key))""",
    """CREATE TABLE master.anh_xa_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        source_company_key text NOT NULL,
        kind text NOT NULL CHECK (kind IN ('COMPANY','BANK','PROJECT')),
        source_value text NOT NULL,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        du_an_id uuid,
        revision integer NOT NULL CHECK (revision >= 1),
        valid_from timestamptz NOT NULL DEFAULT now(),
        valid_to timestamptz,
        known_at_server timestamptz NOT NULL DEFAULT now(),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        state text NOT NULL DEFAULT 'DA_DUYET' CHECK (state IN ('DA_DUYET','DONG')),
        duyet_boi text NOT NULL,
        ly_do text,
        CHECK (kind <> 'COMPANY' OR (source_value = source_company_key AND doi_tac_id IS NULL AND du_an_id IS NULL)),
        CHECK (kind <> 'BANK' OR (doi_tac_id IS NOT NULL AND du_an_id IS NULL)),
        CHECK (kind <> 'PROJECT' OR (du_an_id IS NOT NULL AND doi_tac_id IS NULL)),
        CHECK (valid_to IS NULL OR valid_to > valid_from),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (source_instance_id, source_company_key, kind, source_value, revision))""",
    """CREATE OR REPLACE FUNCTION master.anh_xa_nguon_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh();
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF ROW(NEW.id, NEW.source_instance_id, NEW.source_company_key, NEW.kind, NEW.source_value, NEW.phap_nhan_id, NEW.doi_tac_id, NEW.du_an_id,
                       NEW.revision, NEW.valid_from, NEW.known_at_server, NEW.recorded_at, NEW.duyet_boi)
                   IS DISTINCT FROM ROW(OLD.id, OLD.source_instance_id, OLD.source_company_key, OLD.kind, OLD.source_value, OLD.phap_nhan_id, OLD.doi_tac_id,
                       OLD.du_an_id, OLD.revision, OLD.valid_from, OLD.known_at_server, OLD.recorded_at, OLD.duyet_boi)
                   OR OLD.state = 'DONG' OR NEW.state <> 'DONG' OR NEW.valid_to IS NULL THEN
                    RAISE EXCEPTION 'ANH_XA_BAT_BIEN: chỉ đóng hiệu lực mapping, không sửa/mở lại' USING ERRCODE = 'P0001';
                END IF;
                IF ai IS NULL OR NOT master.ktt_co_vai(OLD.phap_nhan_id, ARRAY['CFO'], 'V4') OR NOT master.ktt_duoc(OLD.phap_nhan_id, 'M9') THEN
                    RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: cần CFO có V4 + M9' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ai IS NULL OR ai IS DISTINCT FROM NEW.duyet_boi OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['CFO'], 'V4') OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M9') THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping nguồn cần CFO có V4 + M9 của phiên (người duyệt = phiên)' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.state <> 'DA_DUYET' OR NEW.valid_to IS NOT NULL THEN
                RAISE EXCEPTION 'ANH_XA_MOI_PHAI_DANG_HIEU_LUC' USING ERRCODE = 'P0001';
            END IF;
            -- khóa identity bền của công ty nguồn TRƯỚC khi kiểm chồng lấn (hai duyệt A/B đồng thời không cùng thành công)
            INSERT INTO master.dinh_danh_cong_ty_nguon (source_instance_id, source_company_key) VALUES (NEW.source_instance_id, NEW.source_company_key)
                ON CONFLICT DO NOTHING;
            PERFORM 1 FROM master.dinh_danh_cong_ty_nguon WHERE source_instance_id = NEW.source_instance_id AND source_company_key = NEW.source_company_key FOR UPDATE;
            IF EXISTS (SELECT 1 FROM master.anh_xa_nguon m WHERE m.source_instance_id = NEW.source_instance_id AND m.source_company_key = NEW.source_company_key
                       AND m.kind = NEW.kind AND m.source_value = NEW.source_value AND m.state = 'DA_DUYET'
                       AND (m.valid_to IS NULL OR m.valid_to > NEW.valid_from)) THEN
                RAISE EXCEPTION 'ANH_XA_CHONG_LAN: đã có mapping đang hiệu lực cho khóa nguồn này' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.kind <> 'COMPANY' AND NOT EXISTS (SELECT 1 FROM master.anh_xa_nguon c WHERE c.source_instance_id = NEW.source_instance_id
                       AND c.source_company_key = NEW.source_company_key AND c.kind = 'COMPANY' AND c.state = 'DA_DUYET' AND c.valid_to IS NULL
                       AND c.phap_nhan_id = NEW.phap_nhan_id) THEN
                RAISE EXCEPTION 'ANH_XA_THIEU_CONG_TY: mapping ngân hàng/dự án cần công ty nguồn đã map đúng pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.kind = 'BANK' AND NOT EXISTS (SELECT 1 FROM master.doi_tac_ma_junsky d WHERE d.doi_tac_id = NEW.doi_tac_id
                       AND d.phap_nhan_id = NEW.phap_nhan_id AND d.valid_to IS NULL) THEN
                RAISE EXCEPTION 'ANH_XA_DOI_TAC_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER anh_xa_nguon_kiem BEFORE INSERT OR UPDATE ON master.anh_xa_nguon FOR EACH ROW EXECUTE FUNCTION master.anh_xa_nguon_kiem()",
    """CREATE TABLE giao_tiep.tep_tach_phap_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        tep_tiep_nhan_id uuid NOT NULL REFERENCES giao_tiep.tep_tiep_nhan(id),
        snapshot_id uuid NOT NULL REFERENCES kho.anh_chup_nguon(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        tep_goc_id uuid NOT NULL,
        profile_sha256 text NOT NULL,
        mapping_revision_sha256 text NOT NULL,
        selected_rows_sha256 text NOT NULL,
        transformation_profile text NOT NULL,
        created_at_server timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, tep_goc_id) REFERENCES kho.tep_goc (phap_nhan_id, id),
        UNIQUE (tep_tiep_nhan_id, phap_nhan_id, profile_sha256, mapping_revision_sha256, selected_rows_sha256))""",
    # intake: một hàm integration ghi metadata raw + snapshot + rows nguyên tử; PN của row do mapping COMPANY đã duyệt quyết, không do client
    """CREATE OR REPLACE FUNCTION giao_tiep.ghi_anh_chup(p jsonb) RETURNS TABLE (snapshot_id uuid, moi boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); tep uuid; snap uuid; r jsonb; pn uuid; ma uuid;
        BEGIN
            IF ai IS NULL OR NOT EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                                         WHERE n.dang_nhap = ai AND 'M9' = ANY (q.module) AND n.vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG')) THEN
                RAISE EXCEPTION 'M9_KHONG_CO_QUYEN_NHAN: cần kế toán có module M9' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO giao_tiep.tep_tiep_nhan (source_instance_id, object_key, raw_sha256, byte_length, media_type, nguoi)
                VALUES (p->>'source_instance_id', p->>'object_key', p->>'raw_sha256', (p->>'byte_length')::bigint, p->>'media_type', ai)
                ON CONFLICT (source_instance_id, raw_sha256) DO NOTHING RETURNING id INTO tep;
            IF tep IS NULL THEN
                SELECT t.id INTO tep FROM giao_tiep.tep_tiep_nhan t WHERE t.source_instance_id = p->>'source_instance_id' AND t.raw_sha256 = p->>'raw_sha256';
            END IF;
            SELECT s.id INTO snap FROM kho.anh_chup_nguon s WHERE s.source_instance_id = p->>'source_instance_id'
                AND s.profile_sha256 = p->>'profile_sha256' AND s.raw_sha256 = p->>'raw_sha256';
            IF snap IS NOT NULL THEN
                RETURN QUERY SELECT snap, false;
                RETURN;
            END IF;
            INSERT INTO kho.anh_chup_nguon (source_instance_id, profile_code, profile_version, profile_sha256, source_code_sha256, ui_sha256, header_set_sha256,
                transport, tep_tiep_nhan_id, raw_sha256, typed_sha256, received_started_at, received_finished_at, exported_at_source, coverage_kind,
                coverage_manifest, state, error_code, loi, nguoi)
            VALUES (p->>'source_instance_id', p->>'profile_code', p->>'profile_version', p->>'profile_sha256', p->>'source_code_sha256', p->>'ui_sha256',
                p->>'header_set_sha256', p->>'transport', tep, p->>'raw_sha256', p->>'typed_sha256', (p->>'received_started_at')::timestamptz,
                (p->>'received_finished_at')::timestamptz, p->>'exported_at_source', p->>'coverage_kind', coalesce(p->'coverage_manifest', '{}'::jsonb),
                p->>'state', p->>'error_code', coalesce(p->'loi', '[]'::jsonb), ai)
            RETURNING id INTO snap;
            FOR r IN SELECT * FROM jsonb_array_elements(coalesce(p->'rows', '[]'::jsonb)) LOOP
                pn := NULL; ma := NULL;
                SELECT m.phap_nhan_id, m.id INTO pn, ma FROM master.anh_xa_nguon m WHERE m.source_instance_id = p->>'source_instance_id'
                    AND m.kind = 'COMPANY' AND m.source_company_key = r->>'source_company_key' AND m.state = 'DA_DUYET' AND m.valid_to IS NULL;
                INSERT INTO kho.ban_ghi_nguon (snapshot_id, phap_nhan_id, section, locator, source_company_key, source_key, row_raw, row_raw_sha256,
                    typed_sha256, validation_state, error_code, mapping_revision_id)
                VALUES (snap, pn, r->>'section', r->>'locator', r->>'source_company_key', r->>'source_key', r->'row_raw', r->>'row_raw_sha256',
                    r->>'typed_sha256', r->>'validation_state', r->>'error_code', ma);
            END LOOP;
            RETURN QUERY SELECT snap, true;
        END $$""",
    """CREATE OR REPLACE FUNCTION giao_tiep.gan_phap_nhan_theo_anh_xa(snap uuid) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); n integer;
        BEGIN
            IF ai IS NULL OR NOT EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n2 ON n2.id = q.nguoi_dung_id
                                         WHERE n2.dang_nhap = ai AND 'M9' = ANY (q.module)) THEN
                RAISE EXCEPTION 'M9_KHONG_CO_QUYEN' USING ERRCODE = 'P0001';
            END IF;
            UPDATE kho.ban_ghi_nguon b SET phap_nhan_id = m.phap_nhan_id, mapping_revision_id = m.id
            FROM kho.anh_chup_nguon s, master.anh_xa_nguon m
            WHERE b.snapshot_id = snap AND s.id = b.snapshot_id AND b.phap_nhan_id IS NULL AND m.source_instance_id = s.source_instance_id
              AND m.kind = 'COMPANY' AND m.source_company_key = b.source_company_key AND m.state = 'DA_DUYET' AND m.valid_to IS NULL;
            GET DIAGNOSTICS n = ROW_COUNT;
            RETURN n;
        END $$""",
    # ứng viên mapping công ty: chỉ khóa công ty nguồn + số dòng chờ (không raw/không PN) cho người có M9 (KT nhận hoặc CFO duyệt mapping)
    """CREATE OR REPLACE FUNCTION giao_tiep.cong_ty_chua_map() RETURNS TABLE (source_instance_id text, source_company_key text, so_dong bigint,
                                                                          snapshot_ids uuid[])
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh();
        BEGIN
            IF ai IS NULL OR NOT EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                                         WHERE n.dang_nhap = ai AND 'M9' = ANY (q.module) AND n.vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG','CFO')) THEN
                RETURN;
            END IF;
            RETURN QUERY SELECT s.source_instance_id, b.source_company_key, count(*), array_agg(DISTINCT s.id)
                FROM kho.ban_ghi_nguon b JOIN kho.anh_chup_nguon s ON s.id = b.snapshot_id
                WHERE b.phap_nhan_id IS NULL AND b.source_company_key IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.ban_ghi_nguon_bat_bien() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(NEW.id, NEW.snapshot_id, NEW.section, NEW.locator, NEW.source_company_key, NEW.source_key, NEW.row_raw, NEW.row_raw_sha256,
                   NEW.typed_sha256, NEW.validation_state, NEW.error_code)
               IS DISTINCT FROM ROW(OLD.id, OLD.snapshot_id, OLD.section, OLD.locator, OLD.source_company_key, OLD.source_key, OLD.row_raw,
                   OLD.row_raw_sha256, OLD.typed_sha256, OLD.validation_state, OLD.error_code)
               OR OLD.phap_nhan_id IS NOT NULL THEN
                RAISE EXCEPTION 'BAN_GHI_NGUON_BAT_BIEN: chỉ gán pháp nhân một lần theo mapping đã duyệt' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER ban_ghi_nguon_bat_bien BEFORE UPDATE ON kho.ban_ghi_nguon FOR EACH ROW EXECUTE FUNCTION kho.ban_ghi_nguon_bat_bien()",
    # --- typed M9: alias ổn định (không chứa financial kind/target PN), revision 1:1 PB, khế ước identity + revision, lãi suất, sự kiện
    """CREATE TABLE master.vay_dinh_danh_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        source_section text NOT NULL CHECK (source_section IN ('DaiHan','VayNganHan')),
        source_company_key text NOT NULL,
        source_key text NOT NULL,
        hop_dong_id uuid NOT NULL UNIQUE,
        first_known_at timestamptz NOT NULL,
        tao_boi text NOT NULL,
        UNIQUE (source_instance_id, source_section, source_company_key, source_key),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id))""",
    """CREATE TABLE master.vay_phien_ban (
        phien_ban_id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        source_alias_id uuid NOT NULL,
        snapshot_id uuid NOT NULL REFERENCES kho.anh_chup_nguon(id),
        source_row_id uuid NOT NULL,
        source_revision_sha256 text NOT NULL CHECK (source_revision_sha256 ~ '^[0-9a-f]{64}$'),
        financing_kind text NOT NULL CHECK (financing_kind IN ('LONG_TERM','SHORT_TERM','LC','GUARANTEE')),
        currency_code char(3),
        currency_scale smallint,
        han_muc_minor bigint,
        du_no_nguon_minor bigint,
        ngay_du_no_nguon date,
        ky_han_nguon text,
        an_han_nguon text,
        quy_uoc_lai_nguon text,
        source_status text,
        so_hop_dong_nguon text,
        so_nhan_no text,
        so_lc text,
        ngay_mo_lc date,
        ngay_nhan_no date,
        ngay_den_han date,
        ngay_tra_no_thuc_te date,
        so_vay_vnd_minor bigint,
        so_da_tra_vnd_minor bigint,
        so_nguyen_te_minor bigint,
        nguyen_te_code char(3),
        nguyen_te_scale smallint,
        source_fx_rate numeric,
        source_fx_basis text,
        ma_lien_ket_nguon text,
        chi_tiet_raw jsonb,
        precision_contract_id text NOT NULL,
        precision_contract_version text NOT NULL,
        precision_status text NOT NULL CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST')),
        precision_fields jsonb NOT NULL DEFAULT '{}'::jsonb,
        blockers text[] NOT NULL DEFAULT '{}',
        mapping_pin jsonb NOT NULL DEFAULT '{}'::jsonb,
        known_at_server timestamptz NOT NULL,
        recorded_at timestamptz NOT NULL DEFAULT now(),
        CHECK ((currency_code IS NULL) = (currency_scale IS NULL)),
        CHECK (so_nguyen_te_minor IS NULL OR (nguyen_te_code IS NOT NULL AND nguyen_te_scale IS NOT NULL)),
        CHECK (source_fx_rate IS NULL OR source_fx_rate > 0),
        UNIQUE (phap_nhan_id, phien_ban_id),
        FOREIGN KEY (phien_ban_id, hop_dong_id) REFERENCES master.hop_dong_phien_ban (id, hop_dong_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_alias_id) REFERENCES master.vay_dinh_danh_nguon (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_row_id) REFERENCES kho.ban_ghi_nguon (phap_nhan_id, id))""",
    """CREATE TABLE master.khe_uoc_vay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        source_alias_id uuid NOT NULL,
        ma_khe_uoc_nguon text NOT NULL,
        first_known_at timestamptz NOT NULL,
        tao_boi text NOT NULL,
        UNIQUE (source_alias_id, ma_khe_uoc_nguon),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_alias_id) REFERENCES master.vay_dinh_danh_nguon (phap_nhan_id, id))""",
    # đích logic ổn định (R3): khóa từ alias/draw/nghĩa vụ — KHÔNG gồm PB/rate/basis revision, amount hay lần fetch
    """CREATE TABLE kho.dich_phan_bo_tien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        module_nghiep_vu text NOT NULL CHECK (module_nghiep_vu IN ('M9')),
        target_kind text NOT NULL CHECK (target_kind IN ('NGHIA_VU','GIAI_NGAN')),
        hop_dong_id uuid NOT NULL,
        khe_uoc_id uuid,
        nghia_vu_key text,
        cau_phan text NOT NULL CHECK (cau_phan IN ('GOC','LAI','PHI','GIAI_NGAN')),
        logical_key text NOT NULL,
        first_known_at timestamptz NOT NULL DEFAULT now(),
        CHECK (target_kind <> 'GIAI_NGAN' OR (khe_uoc_id IS NOT NULL AND cau_phan = 'GIAI_NGAN' AND nghia_vu_key IS NULL)),
        CHECK (target_kind <> 'NGHIA_VU' OR (nghia_vu_key IS NOT NULL AND cau_phan <> 'GIAI_NGAN')),
        UNIQUE (phap_nhan_id, module_nghiep_vu, logical_key),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, khe_uoc_id) REFERENCES master.khe_uoc_vay (phap_nhan_id, id))""",
    """CREATE TABLE master.khe_uoc_vay_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        khe_uoc_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        hop_dong_phien_ban_id uuid NOT NULL,
        source_row_id uuid NOT NULL,
        ngay_giai_ngan_nguon date,
        so_tien_minor bigint,
        currency_code char(3),
        currency_scale smallint,
        revision_sha256 text NOT NULL CHECK (revision_sha256 ~ '^[0-9a-f]{64}$'),
        precision_status text NOT NULL CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST')),
        dich_phan_bo_id uuid NOT NULL,
        known_at_server timestamptz NOT NULL,
        recorded_at timestamptz NOT NULL DEFAULT now(),
        CHECK ((currency_code IS NULL) = (currency_scale IS NULL)),
        CHECK (so_tien_minor IS NULL OR so_tien_minor >= 0),
        UNIQUE (khe_uoc_id, hop_dong_phien_ban_id),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, khe_uoc_id) REFERENCES master.khe_uoc_vay (phap_nhan_id, id),
        FOREIGN KEY (hop_dong_phien_ban_id, hop_dong_id) REFERENCES master.hop_dong_phien_ban (id, hop_dong_id),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_row_id) REFERENCES kho.ban_ghi_nguon (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, dich_phan_bo_id) REFERENCES kho.dich_phan_bo_tien (phap_nhan_id, id))""",
    """CREATE TABLE master.lai_suat_vay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        khe_uoc_phien_ban_id uuid NOT NULL,
        hop_dong_phien_ban_id uuid NOT NULL,
        source_row_id uuid NOT NULL,
        ap_dung_tu date NOT NULL,
        lai_suat_pct_nam numeric NOT NULL CHECK (lai_suat_pct_nam >= 0 AND lai_suat_pct_nam < 1000),
        source_unit text NOT NULL DEFAULT 'PCT_NAM',
        quy_uoc_nguon text,
        precision_status text NOT NULL CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST')),
        revision_sha256 text NOT NULL,
        known_at_server timestamptz NOT NULL,
        recorded_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (khe_uoc_phien_ban_id, ap_dung_tu),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, khe_uoc_phien_ban_id) REFERENCES master.khe_uoc_vay_phien_ban (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_row_id) REFERENCES kho.ban_ghi_nguon (phap_nhan_id, id))""",
    """CREATE TABLE kho.su_kien_vay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        source_alias_id uuid NOT NULL,
        hop_dong_phien_ban_id uuid NOT NULL,
        khe_uoc_id uuid,
        source_event_key text NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        source_row_id uuid NOT NULL,
        loai_su_kien text NOT NULL CHECK (loai_su_kien IN ('PHAT_SINH')),
        ngay_nguon date,
        so_chung_tu_nguon text,
        payload_sha256 text NOT NULL,
        supersedes_id uuid REFERENCES kho.su_kien_vay(id),
        trang_thai text NOT NULL DEFAULT 'BANG_CHUNG' CHECK (trang_thai IN ('BANG_CHUNG','XUNG_DOT')),
        known_at_server timestamptz NOT NULL,
        recorded_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (source_alias_id, source_event_key, revision),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_alias_id) REFERENCES master.vay_dinh_danh_nguon (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, khe_uoc_id) REFERENCES master.khe_uoc_vay (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, source_row_id) REFERENCES kho.ban_ghi_nguon (phap_nhan_id, id))""",
    """CREATE TABLE kho.su_kien_vay_phan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        su_kien_id uuid NOT NULL,
        cau_phan text NOT NULL CHECK (cau_phan IN ('GOC','LAI','PHI')),
        amount_minor bigint,
        currency_code char(3),
        currency_scale smallint,
        precision_status text NOT NULL CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST')),
        CHECK ((currency_code IS NULL) = (currency_scale IS NULL)),
        UNIQUE (su_kien_id, cau_phan),
        UNIQUE (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, su_kien_id) REFERENCES kho.su_kien_vay (phap_nhan_id, id))""",
    # --- mở rộng lịch trả nợ hiện có (không lịch song song): LEGACY giữ nguyên dữ liệu/cách đọc, M9_TYPED một nghĩa vụ/một cấu phần
    """ALTER TABLE master.lich_tra_no
        ADD COLUMN model_version text NOT NULL DEFAULT 'LEGACY' CHECK (model_version IN ('LEGACY','M9_TYPED')),
        ADD COLUMN phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        ADD COLUMN hop_dong_id uuid,
        ADD COLUMN pham_vi text CHECK (pham_vi IN ('LOAN','DRAW')),
        ADD COLUMN khe_uoc_id uuid,
        ADD COLUMN cau_phan text CHECK (cau_phan IN ('GOC','LAI','PHI','KY_QUY','LC_THANH_TOAN','BAO_LANH_PHI','GIAI_TOA')),
        ADD COLUMN nghia_vu_key text,
        ADD COLUMN ky_nguon integer CHECK (ky_nguon > 0),
        ADD COLUMN period_from date,
        ADD COLUMN period_to date,
        ADD COLUMN ngay_den_han date,
        ADD COLUMN amount_minor bigint CHECK (amount_minor >= 0),
        ADD COLUMN currency_code char(3),
        ADD COLUMN currency_scale smallint,
        ADD COLUMN amount_kind text CHECK (amount_kind IN ('SOURCE_SCHEDULE','CONFIRMED_ACCOUNTING_RESULT','ESTIMATE')),
        ADD COLUMN precision_status text CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST')),
        ADD COLUMN source_row_id uuid,
        ADD COLUMN basis_revision_sha256 text,
        ADD COLUMN known_at_server timestamptz,
        ADD COLUMN recorded_at timestamptz,
        ADD COLUMN thay_cho_id uuid REFERENCES master.lich_tra_no(id),
        ADD COLUMN dich_phan_bo_id uuid""",
    """UPDATE master.lich_tra_no l SET phap_nhan_id = h.phap_nhan_id, hop_dong_id = h.id
       FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = l.phien_ban_id""",
    "ALTER TABLE master.lich_tra_no ALTER COLUMN ky DROP NOT NULL",
    "ALTER TABLE master.lich_tra_no ALTER COLUMN goc_minor DROP NOT NULL",
    "ALTER TABLE master.lich_tra_no ALTER COLUMN goc_minor DROP DEFAULT",
    "ALTER TABLE master.lich_tra_no ALTER COLUMN lai_minor DROP NOT NULL",
    "ALTER TABLE master.lich_tra_no ALTER COLUMN lai_minor DROP DEFAULT",
    "ALTER TABLE master.lich_tra_no DROP CONSTRAINT lich_tra_no_phien_ban_id_ky_key",
    "CREATE UNIQUE INDEX lich_tra_no_legacy_ky_uq ON master.lich_tra_no (phien_ban_id, ky) WHERE model_version = 'LEGACY'",
    "CREATE UNIQUE INDEX lich_tra_no_m9_khoa_uq ON master.lich_tra_no (phien_ban_id, nghia_vu_key) WHERE model_version = 'M9_TYPED'",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_pn_id_uq UNIQUE (phap_nhan_id, id)",
    """ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_legacy_du CHECK (model_version <> 'LEGACY' OR (ky IS NOT NULL AND goc_minor IS NOT NULL
        AND lai_minor IS NOT NULL AND cau_phan IS NULL AND amount_minor IS NULL))""",
    """ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_m9_du CHECK (model_version <> 'M9_TYPED' OR (goc_minor IS NULL AND lai_minor IS NULL
        AND phap_nhan_id IS NOT NULL AND hop_dong_id IS NOT NULL AND pham_vi IS NOT NULL AND cau_phan IS NOT NULL AND nghia_vu_key IS NOT NULL
        AND source_row_id IS NOT NULL AND precision_status IS NOT NULL AND known_at_server IS NOT NULL AND dich_phan_bo_id IS NOT NULL AND amount_kind IS NOT NULL))""",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_pham_vi CHECK ((pham_vi IS DISTINCT FROM 'LOAN' OR khe_uoc_id IS NULL) AND (pham_vi IS DISTINCT FROM 'DRAW' OR khe_uoc_id IS NOT NULL))",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_ky_ngay CHECK (period_to IS NULL OR period_from IS NULL OR period_to > period_from)",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_tien_te CHECK (amount_minor IS NULL OR (currency_code IS NOT NULL AND currency_scale IS NOT NULL))",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_pb_hd FOREIGN KEY (phien_ban_id, hop_dong_id) REFERENCES master.hop_dong_phien_ban (id, hop_dong_id)",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_khe_uoc FOREIGN KEY (phap_nhan_id, khe_uoc_id) REFERENCES master.khe_uoc_vay (phap_nhan_id, id)",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_nguon FOREIGN KEY (phap_nhan_id, source_row_id) REFERENCES kho.ban_ghi_nguon (phap_nhan_id, id)",
    "ALTER TABLE master.lich_tra_no ADD CONSTRAINT lich_tra_no_dich FOREIGN KEY (phap_nhan_id, dich_phan_bo_id) REFERENCES kho.dich_phan_bo_tien (phap_nhan_id, id)",
    # lịch sử phiên bản không xóa (FK cũ PB→lịch ON DELETE CASCADE không còn đường kích hoạt)
    """CREATE OR REPLACE FUNCTION master.phien_ban_cam_xoa() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'PHIEN_BAN_KHONG_XOA: lịch sử phiên bản hợp đồng không xóa' USING ERRCODE = 'P0001'; END $$""",
    "CREATE TRIGGER phien_ban_cam_xoa BEFORE DELETE ON master.hop_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION master.phien_ban_cam_xoa()",
    # --- trigger ghi typed M9 (R2): chỉ INSERT vào bản nháp, khóa HĐ trước; không UPDATE/DELETE (không cấp quyền + trigger chặn)
    """CREATE OR REPLACE FUNCTION master.m9_ghi_nhap_noi_bo() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE hd record; v_hd uuid; v_pb uuid; tt text; x record;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'M9_BAT_BIEN: dòng typed M9 không sửa/xóa — thay bằng phiên bản mới' USING ERRCODE = 'P0001';
            END IF;
            -- mỗi nhánh chỉ tham chiếu cột có thật của bảng đó (plpgsql phân giải NEW.<cột> khi chạy câu lệnh)
            IF TG_TABLE_NAME = 'lich_tra_no' THEN
                IF NEW.model_version <> 'M9_TYPED' THEN
                    RAISE EXCEPTION 'M9_LICH_LEGACY_KHONG_GHI_MOI' USING ERRCODE = 'P0001';
                END IF;
                v_hd := NEW.hop_dong_id; v_pb := NEW.phien_ban_id;
            ELSIF TG_TABLE_NAME IN ('vay_dinh_danh_nguon', 'khe_uoc_vay', 'dich_phan_bo_tien') THEN
                v_hd := NEW.hop_dong_id;
            ELSIF TG_TABLE_NAME = 'vay_phien_ban' THEN
                v_hd := NEW.hop_dong_id; v_pb := NEW.phien_ban_id;
            ELSIF TG_TABLE_NAME = 'khe_uoc_vay_phien_ban' THEN
                v_hd := NEW.hop_dong_id; v_pb := NEW.hop_dong_phien_ban_id;
            ELSIF TG_TABLE_NAME = 'lai_suat_vay' THEN
                SELECT k.hop_dong_id, k.hop_dong_phien_ban_id INTO v_hd, v_pb FROM master.khe_uoc_vay_phien_ban k WHERE k.id = NEW.khe_uoc_phien_ban_id;
                IF v_pb IS DISTINCT FROM NEW.hop_dong_phien_ban_id THEN RAISE EXCEPTION 'M9_SAI_CHA: lãi suất phải cùng PB với khế ước' USING ERRCODE = 'P0001'; END IF;
            ELSIF TG_TABLE_NAME = 'su_kien_vay' THEN
                SELECT a.hop_dong_id INTO v_hd FROM master.vay_dinh_danh_nguon a WHERE a.id = NEW.source_alias_id;
                v_pb := NEW.hop_dong_phien_ban_id;
            ELSIF TG_TABLE_NAME = 'su_kien_vay_phan' THEN
                SELECT a.hop_dong_id, e.hop_dong_phien_ban_id INTO v_hd, v_pb FROM kho.su_kien_vay e JOIN master.vay_dinh_danh_nguon a ON a.id = e.source_alias_id
                    WHERE e.id = NEW.su_kien_id;
            END IF;
            """ + _M9_KIEM_GHI + """
            IF v_pb IS NOT NULL THEN
                SELECT p.trang_thai INTO tt FROM master.hop_dong_phien_ban p WHERE p.id = v_pb AND p.hop_dong_id = v_hd;
                IF tt IS DISTINCT FROM 'CHO_DUYET' THEN
                    RAISE EXCEPTION 'M9_PHIEN_BAN_DA_CHOT: chỉ ghi vào phiên bản đang chờ duyệt' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF TG_TABLE_NAME = 'vay_phien_ban' THEN
                IF NOT EXISTS (SELECT 1 FROM master.vay_dinh_danh_nguon a WHERE a.id = NEW.source_alias_id AND a.hop_dong_id = NEW.hop_dong_id) THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: alias không trỏ đúng HĐ' USING ERRCODE = 'P0001';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM kho.ban_ghi_nguon b WHERE b.id = NEW.source_row_id AND b.snapshot_id = NEW.snapshot_id) THEN
                    RAISE EXCEPTION 'M9_SAI_NGUON: dòng nguồn không thuộc snapshot' USING ERRCODE = 'P0001';
                END IF;
            ELSIF TG_TABLE_NAME = 'khe_uoc_vay' THEN
                IF NOT EXISTS (SELECT 1 FROM master.vay_dinh_danh_nguon a WHERE a.id = NEW.source_alias_id AND a.hop_dong_id = NEW.hop_dong_id) THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: alias không trỏ đúng HĐ' USING ERRCODE = 'P0001';
                END IF;
            ELSIF TG_TABLE_NAME = 'khe_uoc_vay_phien_ban' THEN
                SELECT * INTO x FROM kho.dich_phan_bo_tien d WHERE d.id = NEW.dich_phan_bo_id;
                IF NOT EXISTS (SELECT 1 FROM master.khe_uoc_vay k WHERE k.id = NEW.khe_uoc_id AND k.hop_dong_id = NEW.hop_dong_id)
                   OR x.target_kind IS DISTINCT FROM 'GIAI_NGAN' OR x.khe_uoc_id IS DISTINCT FROM NEW.khe_uoc_id THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: khế ước/đích giải ngân không khớp' USING ERRCODE = 'P0001';
                END IF;
            ELSIF TG_TABLE_NAME = 'lich_tra_no' THEN
                SELECT * INTO x FROM kho.dich_phan_bo_tien d WHERE d.id = NEW.dich_phan_bo_id;
                IF x.target_kind IS DISTINCT FROM 'NGHIA_VU' OR x.hop_dong_id IS DISTINCT FROM NEW.hop_dong_id OR x.nghia_vu_key IS DISTINCT FROM NEW.nghia_vu_key
                   OR x.cau_phan IS DISTINCT FROM NEW.cau_phan THEN
                    RAISE EXCEPTION 'M9_SAI_DICH: nghĩa vụ phải trỏ đúng đích logic (HĐ/khóa/cấu phần)' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.khe_uoc_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.khe_uoc_vay k WHERE k.id = NEW.khe_uoc_id AND k.hop_dong_id = NEW.hop_dong_id) THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: khế ước không thuộc HĐ' USING ERRCODE = 'P0001';
                END IF;
            ELSIF TG_TABLE_NAME = 'su_kien_vay' THEN
                IF NEW.khe_uoc_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.khe_uoc_vay k WHERE k.id = NEW.khe_uoc_id AND k.source_alias_id = NEW.source_alias_id) THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: khế ước của sự kiện không thuộc alias' USING ERRCODE = 'P0001';
                END IF;
            ELSIF TG_TABLE_NAME = 'dich_phan_bo_tien' THEN
                IF NEW.khe_uoc_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.khe_uoc_vay k WHERE k.id = NEW.khe_uoc_id AND k.hop_dong_id = NEW.hop_dong_id) THEN
                    RAISE EXCEPTION 'M9_SAI_CHA: khế ước của đích không thuộc HĐ' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    *(f"CREATE TRIGGER m9_ghi_nhap BEFORE INSERT OR UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION master.m9_ghi_nhap_noi_bo()"
      for t in ("master.vay_dinh_danh_nguon", "master.vay_phien_ban", "master.khe_uoc_vay", "master.khe_uoc_vay_phien_ban", "master.lai_suat_vay",
                "kho.su_kien_vay", "kho.su_kien_vay_phan", "kho.dich_phan_bo_tien")),
    # lịch: INSERT qua cùng kiểm ghi nháp (LEGACY không ghi mới); dòng M9_TYPED không sửa/xóa; dòng LEGACY giữ nguyên hành vi cũ
    "CREATE TRIGGER m9_ghi_nhap BEFORE INSERT ON master.lich_tra_no FOR EACH ROW EXECUTE FUNCTION master.m9_ghi_nhap_noi_bo()",
    """CREATE TRIGGER m9_ghi_nhap_bat_bien BEFORE UPDATE OR DELETE ON master.lich_tra_no FOR EACH ROW WHEN (OLD.model_version = 'M9_TYPED')
        EXECUTE FUNCTION master.m9_ghi_nhap_noi_bo()""",
    # --- R2: manifest canonical + validator đồ thị (owner-only, không bị RLS che); phân biệt NULL/0, sort theo khóa ổn định
    """CREATE OR REPLACE FUNCTION master.m9_manifest_phien_ban_noi_bo(pb uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT jsonb_build_object(
            'v', 'M9_MANIFEST_V1',
            'pb', jsonb_build_object('id', p.id::text, 'hop_dong_id', p.hop_dong_id::text, 'phien_ban', p.phien_ban, 'loai', p.loai, 'nguon', p.nguon,
                   'thay_cho_id', p.thay_cho_id::text, 'ngay_hieu_luc', p.ngay_hieu_luc::text, 'tham_so', p.tham_so),
            'hop_dong', jsonb_build_object('phap_nhan_id', h.phap_nhan_id::text, 'loai', h.loai, 'ma_noi_bo', h.ma_noi_bo, 'so_hop_dong', h.so_hop_dong,
                   'doi_tac_id', h.doi_tac_id::text, 'du_an_id', h.du_an_id::text, 'tien_te', h.tien_te),
            'vay', (SELECT to_jsonb(v) - 'recorded_at' FROM master.vay_phien_ban v WHERE v.phien_ban_id = p.id),
            'alias', (SELECT to_jsonb(a) - 'tao_boi' FROM master.vay_dinh_danh_nguon a WHERE a.hop_dong_id = h.id),
            'draws', coalesce((SELECT jsonb_agg(jsonb_build_object('ma', k.ma_khe_uoc_nguon, 'identity', k.id::text, 'rev', to_jsonb(r) - 'recorded_at')
                               ORDER BY k.ma_khe_uoc_nguon) FROM master.khe_uoc_vay_phien_ban r JOIN master.khe_uoc_vay k ON k.id = r.khe_uoc_id
                               WHERE r.hop_dong_phien_ban_id = p.id), '[]'::jsonb),
            'rates', coalesce((SELECT jsonb_agg(to_jsonb(l) - 'recorded_at' || jsonb_build_object('pct', l.lai_suat_pct_nam::text, 'ma', k.ma_khe_uoc_nguon)
                               ORDER BY k.ma_khe_uoc_nguon, l.ap_dung_tu) FROM master.lai_suat_vay l JOIN master.khe_uoc_vay_phien_ban r ON r.id = l.khe_uoc_phien_ban_id
                               JOIN master.khe_uoc_vay k ON k.id = r.khe_uoc_id WHERE l.hop_dong_phien_ban_id = p.id), '[]'::jsonb),
            'lich', coalesce((SELECT jsonb_agg(to_jsonb(t) - 'recorded_at' - 'trang_thai' - 'da_tra_minor' || jsonb_build_object('amount', t.amount_minor::text)
                              ORDER BY t.nghia_vu_key) FROM master.lich_tra_no t WHERE t.phien_ban_id = p.id), '[]'::jsonb),
            'events', coalesce((SELECT jsonb_agg(to_jsonb(e) - 'recorded_at' || jsonb_build_object('parts', coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.cau_phan)
                                FROM kho.su_kien_vay_phan x WHERE x.su_kien_id = e.id), '[]'::jsonb)) ORDER BY e.source_event_key, e.revision)
                                FROM kho.su_kien_vay e WHERE e.hop_dong_phien_ban_id = p.id), '[]'::jsonb),
            'source_rows', coalesce((SELECT jsonb_agg(DISTINCT b.row_raw_sha256 ORDER BY b.row_raw_sha256) FROM kho.ban_ghi_nguon b WHERE b.id IN (
                                SELECT v.source_row_id FROM master.vay_phien_ban v WHERE v.phien_ban_id = p.id
                                UNION SELECT r.source_row_id FROM master.khe_uoc_vay_phien_ban r WHERE r.hop_dong_phien_ban_id = p.id
                                UNION SELECT l.source_row_id FROM master.lai_suat_vay l WHERE l.hop_dong_phien_ban_id = p.id
                                UNION SELECT t.source_row_id FROM master.lich_tra_no t WHERE t.phien_ban_id = p.id
                                UNION SELECT e.source_row_id FROM kho.su_kien_vay e WHERE e.hop_dong_phien_ban_id = p.id)), '[]'::jsonb))
        FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id WHERE p.id = pb
        $$""",
    """CREATE OR REPLACE FUNCTION master.m9_van_tay_noi_bo(pb uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT encode(sha256(convert_to(master.m9_manifest_phien_ban_noi_bo(pb)::text, 'UTF8')), 'hex')
        $$""",
    """CREATE OR REPLACE FUNCTION master.m9_kiem_do_thi_noi_bo(pb uuid, transition text) RETURNS text[]
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE b text[] := '{}'; v record; h record; n integer;
        BEGIN
            SELECT * INTO h FROM master.hop_dong WHERE id = (SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = pb);
            SELECT count(*) INTO n FROM master.vay_phien_ban WHERE phien_ban_id = pb;
            IF h.loai IS DISTINCT FROM 'VAY' THEN RETURN ARRAY['KHONG_PHAI_HOP_DONG_VAY']; END IF;
            IF n <> 1 THEN RETURN ARRAY['THIEU_GOC_TYPED_VAY']; END IF;
            SELECT * INTO v FROM master.vay_phien_ban WHERE phien_ban_id = pb;
            IF v.hop_dong_id <> h.id OR v.phap_nhan_id <> h.phap_nhan_id THEN b := b || text 'GOC_TYPED_SAI_CHA'; END IF;
            b := b || v.blockers;
            IF v.precision_status <> 'PROVEN' THEN b := b || text 'PRECISION_CHUA_CHUNG_MINH'; END IF;
            IF v.financing_kind = 'LONG_TERM' AND v.currency_code IS NULL THEN b := b || text 'THIEU_TIEN_TE'; END IF;
            IF h.doi_tac_id IS NULL THEN b := b || text 'MAPPING_NGAN_HANG'; END IF;
            IF EXISTS (SELECT 1 FROM kho.ban_ghi_nguon r WHERE r.validation_state <> 'HOP_LE' AND r.id IN (
                   SELECT source_row_id FROM master.khe_uoc_vay_phien_ban WHERE hop_dong_phien_ban_id = pb UNION SELECT source_row_id FROM master.lich_tra_no WHERE phien_ban_id = pb
                   UNION SELECT source_row_id FROM master.lai_suat_vay WHERE hop_dong_phien_ban_id = pb UNION SELECT v.source_row_id)) THEN
                b := b || text 'NGUON_LOI';
            END IF;
            IF EXISTS (SELECT 1 FROM master.khe_uoc_vay_phien_ban r WHERE r.hop_dong_phien_ban_id = pb AND (r.so_tien_minor IS NULL OR r.ngay_giai_ngan_nguon IS NULL)) THEN
                b := b || text 'KHE_UOC_THIEU_SO_LIEU';
            END IF;
            IF EXISTS (SELECT 1 FROM master.khe_uoc_vay_phien_ban r WHERE r.hop_dong_phien_ban_id = pb AND r.precision_status <> 'PROVEN')
               OR EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND t.precision_status <> 'PROVEN')
               OR EXISTS (SELECT 1 FROM master.lai_suat_vay l WHERE l.hop_dong_phien_ban_id = pb AND l.precision_status <> 'PROVEN') THEN
                b := b || text 'PRECISION_CHUA_CHUNG_MINH';
            END IF;
            IF EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND t.amount_minor IS NULL) THEN b := b || text 'LICH_THIEU_SO_TIEN'; END IF;
            IF EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND t.amount_kind = 'ESTIMATE') THEN b := b || text 'LICH_UOC_TINH'; END IF;
            IF EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND (t.currency_code, t.currency_scale) IS DISTINCT FROM (v.currency_code, v.currency_scale))
               OR EXISTS (SELECT 1 FROM master.khe_uoc_vay_phien_ban r WHERE r.hop_dong_phien_ban_id = pb AND (r.currency_code, r.currency_scale) IS DISTINCT FROM (v.currency_code, v.currency_scale)) THEN
                b := b || text 'KHAC_TIEN_TE_HOP_DONG';
            END IF;
            IF EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND t.pham_vi = 'LOAN' AND t.cau_phan = 'GOC')
               AND EXISTS (SELECT 1 FROM master.lich_tra_no t WHERE t.phien_ban_id = pb AND t.pham_vi = 'DRAW' AND t.cau_phan = 'GOC') THEN
                b := b || text 'CHO_XAC_NHAN_PHAM_VI_LICH';
            END IF;
            IF EXISTS (SELECT 1 FROM kho.su_kien_vay e WHERE e.hop_dong_phien_ban_id = pb AND e.trang_thai = 'XUNG_DOT') THEN b := b || text 'PHAT_SINH_XUNG_DOT'; END IF;
            IF transition = 'APPROVE' AND EXISTS (SELECT 1 FROM kho.viec_can_duyet w WHERE w.tham_chieu_bang = 'master.hop_dong' AND w.tham_chieu_id = h.id
                                                   AND w.loai = 'V4' AND w.trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')) THEN
                b := b || text 'V4_CHUA_XONG';
            END IF;
            RETURN (SELECT coalesce(array_agg(DISTINCT x ORDER BY x), '{}') FROM unnest(b) x);
        END $$""",
    # wrapper đọc cho app (phạm vi M9 của chính PB), như mẫu crm_*: ngoài phạm vi trả NULL
    """CREATE OR REPLACE FUNCTION master.m9_van_tay(pb uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT master.m9_van_tay_noi_bo(p.id) FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
        WHERE p.id = pb AND h.loai = 'VAY' AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'M9')
        $$""",
    """CREATE OR REPLACE FUNCTION master.m9_chan(pb uuid, transition text) RETURNS text[]
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT master.m9_kiem_do_thi_noi_bo(p.id, transition) FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
        WHERE p.id = pb AND h.loai = 'VAY' AND transition IN ('CHECK','APPROVE') AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'M9')
        $$""",
    """CREATE OR REPLACE FUNCTION master.m9_phien_ban_hieu_luc(hd uuid, d date) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.phien_ban_hieu_luc(h.id, d) FROM master.hop_dong h
        WHERE h.id = hd AND h.loai = 'VAY' AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'M9')
        $$""",
    # wrapper CRM chỉ cho HĐ không phải VAY (domain dispatch): người chỉ có CRM không đọc hiệu lực/vân tay HĐ vay qua đường CRM
    """CREATE OR REPLACE FUNCTION master.crm_phien_ban_hieu_luc(hd uuid, d date) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.phien_ban_hieu_luc(h.id, d) FROM master.hop_dong h
        WHERE h.id = hd AND h.loai <> 'VAY' AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_van_tay_phien_ban(pb uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.van_tay_phien_ban(p.id) FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
        WHERE p.id = pb AND h.loai <> 'VAY' AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
        $$""",
    # kiểm/duyệt dispatch theo HĐ.loai bất biến: VAY → validator + manifest M9 + quyền M9; còn lại giữ nguyên logic M0012 (CRM)
    """CREATE OR REPLACE FUNCTION master.phien_ban_kiem_duyet() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pn uuid; loai_hd text; ai text := master.ktt_danh_tinh(); van_tay text; chan text[];
        BEGIN
            IF OLD.trang_thai IN ('TU_CHOI','THAY_THE') THEN
                RAISE EXCEPTION 'PHIEN_BAN_DA_CHOT: phiên bản % không sửa được', OLD.trang_thai USING ERRCODE = 'P0001';
            END IF;
            SELECT phap_nhan_id, loai INTO pn, loai_hd FROM master.hop_dong WHERE id = OLD.hop_dong_id;
            IF OLD.trang_thai = 'DA_DUYET' THEN
                IF ROW(NEW.id, NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.so_phu_luc, NEW.ngay, NEW.tham_so, NEW.tep_goc_id, NEW.nguon, NEW.trang_thai,
                       NEW.nguoi_duyet, NEW.duyet_luc, NEW.valid_from, NEW.thay_cho_id, NEW.ngay_hieu_luc, NEW.chung_tu_id, NEW.loai_hinh_dt_id, NEW.kiem_boi,
                       NEW.kiem_luc, NEW.ly_do, NEW.tao_boi, NEW.tao_luc, NEW.kiem_van_tay)
                   IS DISTINCT FROM ROW(OLD.id, OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.so_phu_luc, OLD.ngay, OLD.tham_so, OLD.tep_goc_id, OLD.nguon, OLD.trang_thai,
                       OLD.nguoi_duyet, OLD.duyet_luc, OLD.valid_from, OLD.thay_cho_id, OLD.ngay_hieu_luc, OLD.chung_tu_id, OLD.loai_hinh_dt_id, OLD.kiem_boi,
                       OLD.kiem_luc, OLD.ly_do, OLD.tao_boi, OLD.tao_luc, OLD.kiem_van_tay) THEN
                    RAISE EXCEPTION 'PHIEN_BAN_DA_DUYET_BAT_BIEN: chỉ đóng hiệu lực (valid_to) khi có bản thay' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.valid_to IS NOT DISTINCT FROM OLD.valid_to THEN
                    RETURN NEW;
                END IF;
                IF OLD.valid_to IS NOT NULL OR NEW.valid_to IS NULL THEN
                    RAISE EXCEPTION 'HIEU_LUC_DA_DONG: biên hiệu lực bản đã duyệt không mở lại hay đổi mốc' USING ERRCODE = 'P0001';
                END IF;
                IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NOT EXISTS (
                        SELECT 1 FROM master.hop_dong_phien_ban r WHERE r.hop_dong_id = OLD.hop_dong_id AND r.thay_cho_id = OLD.id AND r.id <> OLD.id
                          AND r.trang_thai = 'DA_DUYET' AND r.nguoi_duyet = ai AND r.duyet_luc = now() AND r.valid_from = NEW.valid_to) THEN
                    RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: chỉ CFO có V3 đóng bản cũ đúng mốc của bản thay vừa duyệt' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF (NEW.hop_dong_id, NEW.phien_ban, NEW.loai, NEW.nguon, NEW.tao_boi, NEW.tao_luc) IS DISTINCT FROM (OLD.hop_dong_id, OLD.phien_ban, OLD.loai, OLD.nguon, OLD.tao_boi, OLD.tao_luc) THEN
                RAISE EXCEPTION 'PHIEN_BAN_KHONG_DOI_DINH_DANH' USING ERRCODE = 'P0001';
            END IF;
            IF (NEW.valid_from, NEW.valid_to) IS DISTINCT FROM (OLD.valid_from, OLD.valid_to) AND NEW.trang_thai <> 'DA_DUYET' THEN
                RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: biên hiệu lực chỉ đặt khi duyệt' USING ERRCODE = 'P0001';
            END IF;
            IF loai_hd = 'VAY' THEN
                van_tay := master.m9_van_tay_noi_bo(NEW.id);
                IF (NEW.kiem_boi, NEW.kiem_luc, NEW.kiem_van_tay) IS DISTINCT FROM (OLD.kiem_boi, OLD.kiem_luc, OLD.kiem_van_tay) AND NEW.kiem_boi IS NOT NULL THEN
                    IF ai IS NULL OR ai <> NEW.kiem_boi OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) OR NOT master.ktt_duoc(pn, 'M9')
                       OR NEW.kiem_luc IS NULL OR NEW.kiem_van_tay IS DISTINCT FROM van_tay THEN
                        RAISE EXCEPTION 'KHONG_CO_QUYEN_KIEM: % không phải kế toán M9 của phiên hoặc vân tay không khớp đồ thị hiện tại', NEW.kiem_boi USING ERRCODE = 'P0001';
                    END IF;
                    chan := master.m9_kiem_do_thi_noi_bo(NEW.id, 'CHECK');
                    IF cardinality(chan) > 0 THEN
                        RAISE EXCEPTION 'M9_CHUA_DU_DIEU_KIEN: %', array_to_string(chan, ',') USING ERRCODE = 'P0001';
                    END IF;
                ELSIF (NEW.kiem_boi, NEW.kiem_luc, NEW.kiem_van_tay) IS DISTINCT FROM (OLD.kiem_boi, OLD.kiem_luc, OLD.kiem_van_tay)
                      AND (NEW.kiem_luc IS NOT NULL OR NEW.kiem_van_tay IS NOT NULL) THEN
                    RAISE EXCEPTION 'KIEM_KHONG_HOP_LE' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai IN ('DA_DUYET','TU_CHOI') THEN
                    IF ai IS NULL OR ai IS DISTINCT FROM NEW.nguoi_duyet OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NOT master.ktt_duoc(pn, 'M9') OR NEW.duyet_luc IS NULL THEN
                        RAISE EXCEPTION 'KHONG_CO_QUYEN_DUYET: % không phải CFO có V3 + M9 của phiên', NEW.nguoi_duyet USING ERRCODE = 'P0001';
                    END IF;
                    IF NEW.trang_thai = 'DA_DUYET' THEN
                        IF NEW.kiem_luc IS NULL OR NEW.kiem_boi IS NOT DISTINCT FROM NEW.nguoi_duyet OR NEW.kiem_van_tay IS DISTINCT FROM van_tay THEN
                            RAISE EXCEPTION 'KIEM_DA_HET_HIEU_LUC: chưa kiểm hoặc đồ thị M9 đã đổi sau lần kiểm' USING ERRCODE = 'P0001';
                        END IF;
                        chan := master.m9_kiem_do_thi_noi_bo(NEW.id, 'APPROVE');  -- đọc lại khi duyệt, không tin lần kiểm
                        IF cardinality(chan) > 0 THEN
                            RAISE EXCEPTION 'M9_CHUA_DU_DIEU_KIEN: %', array_to_string(chan, ',') USING ERRCODE = 'P0001';
                        END IF;
                        IF NEW.valid_to IS NOT NULL OR NEW.duyet_luc IS DISTINCT FROM now() THEN
                            RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: bản vừa duyệt chưa có mốc kết thúc' USING ERRCODE = 'P0001';
                        END IF;
                    END IF;
                ELSIF NEW.trang_thai = 'THAY_THE' THEN
                    IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) OR NOT master.ktt_duoc(pn, 'M9') THEN
                        RAISE EXCEPTION 'KHONG_CO_QUYEN_THAY_THE' USING ERRCODE = 'P0001';
                    END IF;
                ELSIF NEW.trang_thai <> 'CHO_DUYET' THEN
                    RAISE EXCEPTION 'TRANG_THAI_PHIEN_BAN_SAI' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF (NEW.kiem_boi, NEW.kiem_luc, NEW.kiem_van_tay) IS DISTINCT FROM (OLD.kiem_boi, OLD.kiem_luc, OLD.kiem_van_tay) THEN
                IF NEW.kiem_boi IS NULL THEN
                    IF NEW.kiem_luc IS NOT NULL OR NEW.kiem_van_tay IS NOT NULL THEN
                        RAISE EXCEPTION 'KIEM_KHONG_HOP_LE' USING ERRCODE = 'P0001';
                    END IF;
                ELSIF ai IS NULL OR ai <> NEW.kiem_boi OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
                      OR NEW.kiem_luc IS NULL OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_KIEM: % không phải kế toán của phiên hiện tại trên pháp nhân', NEW.kiem_boi USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.trang_thai IN ('DA_DUYET','TU_CHOI') THEN
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.nguoi_duyet OR NOT master.ktt_co_vai(pn, ARRAY['CFO'], 'V3') OR NEW.duyet_luc IS NULL THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_DUYET: % không phải CFO có quyền V3 của phiên hiện tại', NEW.nguoi_duyet USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'DA_DUYET' AND (NEW.kiem_luc IS NULL OR NEW.kiem_boi IS NOT DISTINCT FROM NEW.nguoi_duyet
                                                    OR NEW.kiem_van_tay IS DISTINCT FROM master.van_tay_phien_ban(NEW.id)) THEN
                    RAISE EXCEPTION 'KIEM_DA_HET_HIEU_LUC: chưa kiểm trước hoặc nội dung/mapping đã đổi sau lần kiểm' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai = 'DA_DUYET' AND (NEW.valid_to IS NOT NULL OR NEW.duyet_luc IS DISTINCT FROM now()) THEN
                    RAISE EXCEPTION 'HIEU_LUC_KHONG_HOP_LE: bản vừa duyệt chưa có mốc kết thúc' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai = 'THAY_THE' THEN
                IF ai IS NULL OR NOT master.ktt_co_vai(pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                    RAISE EXCEPTION 'KHONG_CO_QUYEN_THAY_THE' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.trang_thai <> 'CHO_DUYET' THEN
                RAISE EXCEPTION 'TRANG_THAI_PHIEN_BAN_SAI' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- R4: proof encoding tiền của chính BANK — bất biến, chỉ chủ CSDL (verifier) ghi; app không sửa/khai PROVEN
    """CREATE TABLE kho.chung_tu_tien_encoding (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        chung_tu_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        encoding_kind text NOT NULL CHECK (encoding_kind = 'MINOR_INT64'),
        currency_code char(3) NOT NULL,
        currency_scale smallint NOT NULL,
        precision_status text NOT NULL CHECK (precision_status IN ('PROVEN','UNPROVEN','LOST','UNKNOWN')),
        contract_id text NOT NULL,
        contract_version text NOT NULL,
        contract_sha256 text NOT NULL CHECK (contract_sha256 ~ '^[0-9a-f]{64}$'),
        artifact_ref text NOT NULL,
        field_locator text NOT NULL,
        money_digest text NOT NULL CHECK (money_digest ~ '^[0-9a-f]{64}$'),
        known_at timestamptz NOT NULL DEFAULT now(),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        state text NOT NULL CHECK (state IN ('HIEU_LUC','BANG_CHUNG_BO_SUNG')),
        UNIQUE (chung_tu_id, revision),
        FOREIGN KEY (phap_nhan_id, chung_tu_id) REFERENCES kho.chung_tu (phap_nhan_id, id))""",
    "CREATE UNIQUE INDEX chung_tu_tien_encoding_hieu_luc_uq ON kho.chung_tu_tien_encoding (chung_tu_id) WHERE state = 'HIEU_LUC'",
    """CREATE OR REPLACE FUNCTION kho.tien_digest_noi_bo(bank uuid, scale smallint) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT encode(sha256(convert_to('MINOR_INT64|' || c.id::text || '|' || coalesce(c.so_tien_minor::text, 'NULL') || '|' || coalesce(rtrim(c.tien_te), 'NULL')
                                        || '|' || coalesce(scale::text, 'NULL') || '|' || coalesce(c.chieu, 'NULL'), 'UTF8')), 'hex')
        FROM kho.chung_tu c WHERE c.id = bank
        $$""",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_tien_encoding_kiem() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE c record;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'PROOF_TIEN_BAT_BIEN: proof encoding không sửa/xóa — bổ sung bằng revision bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO c FROM kho.chung_tu WHERE id = NEW.chung_tu_id;
            IF c.loai <> 'SAO_KE' OR c.so_tien_minor IS NULL OR rtrim(c.tien_te) IS DISTINCT FROM rtrim(NEW.currency_code) THEN
                RAISE EXCEPTION 'PROOF_TIEN_SAI: proof chỉ cho BANK có số/loại tiền khớp' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.don_vi_tien d WHERE d.ma = NEW.currency_code AND d.scale = NEW.currency_scale) THEN
                RAISE EXCEPTION 'PROOF_TIEN_SAI: đơn vị/scale không có trong registry' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.state = 'BANG_CHUNG_BO_SUNG' AND NOT EXISTS (SELECT 1 FROM kho.chung_tu_tien_encoding e WHERE e.chung_tu_id = NEW.chung_tu_id
                   AND e.state = 'HIEU_LUC' AND e.currency_code = NEW.currency_code AND e.currency_scale = NEW.currency_scale AND e.money_digest = NEW.money_digest) THEN
                RAISE EXCEPTION 'PROOF_TIEN_SAI: bằng chứng bổ sung phải giữ nguyên số/loại tiền/scale đã pin' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_tien_encoding_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.chung_tu_tien_encoding FOR EACH ROW EXECUTE FUNCTION kho.chung_tu_tien_encoding_kiem()",
    # verifier (chủ CSDL, không PUBLIC/app): gắn proof lần đầu cho BANK có contract encoding đã pin; đã pin rồi thì chỉ bổ sung bằng chứng cùng số
    """CREATE OR REPLACE FUNCTION kho.ghi_proof_tien_noi_bo(bank uuid, p_scale smallint, p_contract_id text, p_contract_version text, p_contract_sha256 text,
                                                           p_artifact_ref text, p_field_locator text, p_precision text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE c record; da uuid; rev integer; nid uuid;
        BEGIN
            SELECT * INTO c FROM kho.chung_tu WHERE id = bank FOR UPDATE;
            SELECT id INTO da FROM kho.chung_tu_tien_encoding WHERE chung_tu_id = bank AND state = 'HIEU_LUC';
            SELECT coalesce(max(revision), 0) + 1 INTO rev FROM kho.chung_tu_tien_encoding WHERE chung_tu_id = bank;
            INSERT INTO kho.chung_tu_tien_encoding (phap_nhan_id, chung_tu_id, revision, encoding_kind, currency_code, currency_scale, precision_status, contract_id,
                contract_version, contract_sha256, artifact_ref, field_locator, money_digest, state)
            VALUES (c.phap_nhan_id, bank, rev, 'MINOR_INT64', rtrim(c.tien_te), p_scale, p_precision, p_contract_id, p_contract_version, p_contract_sha256,
                p_artifact_ref, p_field_locator, kho.tien_digest_noi_bo(bank, p_scale), CASE WHEN da IS NULL THEN 'HIEU_LUC' ELSE 'BANG_CHUNG_BO_SUNG' END)
            RETURNING id INTO nid;
            RETURN nid;
        END $$""",
    "REVOKE EXECUTE ON FUNCTION kho.ghi_proof_tien_noi_bo(uuid, smallint, text, text, text, text, text, text) FROM PUBLIC",
    # --- link chung: phân loại mục đích/mô hình (R1), loại VAY_TIEN, child allocation, biên nhận
    "ALTER TABLE kho.lien_ket_chung_tu ADD COLUMN link_purpose text, ADD COLUMN allocation_model text, ADD COLUMN bien_nhan_id uuid",
    """UPDATE kho.lien_ket_chung_tu SET link_purpose = CASE WHEN lich_thu_id IS NOT NULL THEN 'MONEY' WHEN so_tien_khop_minor IS NULL THEN 'EVIDENCE'
                                                            ELSE 'LEGACY_UNCLASSIFIED' END,
                                        allocation_model = CASE WHEN lich_thu_id IS NOT NULL THEN 'DIRECT' END""",
    "ALTER TABLE kho.lien_ket_chung_tu ALTER COLUMN link_purpose SET NOT NULL",
    "ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_purpose_check CHECK (link_purpose IN ('MONEY','EVIDENCE','LEGACY_UNCLASSIFIED'))",
    "ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_model_check CHECK (allocation_model IN ('DIRECT','CHILD') AND link_purpose = 'MONEY' OR allocation_model IS NULL AND link_purpose <> 'MONEY')",
    "ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_evidence_khong_tien CHECK (link_purpose <> 'EVIDENCE' OR so_tien_khop_minor IS NULL)",
    "ALTER TABLE kho.lien_ket_chung_tu DROP CONSTRAINT lien_ket_chung_tu_loai_check",
    """ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_chung_tu_loai_check CHECK (loai IN ('TIEN_CONG_NO','HD_NGHIEM_THU','HOP_DONG_DOT_TIEN','HD_TAI_SAN',
        'XDCB_TAI_SAN','NHIEU_LAN_CHUYEN','HD_RQ','HD_PHIEU_KHO','DIEU_CHINH','KHAC','VAY_TIEN'))""",
    """CREATE TABLE kho.bien_nhan_thao_tac (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        module text NOT NULL CHECK (module IN ('M9','CRM','M1','M2')),
        operation text NOT NULL CHECK (operation ~ '^[A-Z_]{3,40}$'),
        client_key text NOT NULL CHECK (length(client_key) BETWEEN 1 AND 200),
        request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
        result_json jsonb NOT NULL,
        actor text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, module, operation, client_key),
        UNIQUE (phap_nhan_id, id))""",
    """CREATE OR REPLACE FUNCTION kho.bien_nhan_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'BIEN_NHAN_BAT_BIEN' USING ERRCODE = 'P0001';
            END IF;
            IF master.ktt_danh_tinh() IS NULL OR master.ktt_danh_tinh() IS DISTINCT FROM NEW.actor OR NOT master.ktt_duoc(NEW.phap_nhan_id, NEW.module) THEN
                RAISE EXCEPTION 'BIEN_NHAN_KHONG_CO_QUYEN: actor biên nhận phải là phiên hiện tại có module' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.bien_nhan_thao_tac FOR EACH ROW EXECUTE FUNCTION kho.bien_nhan_kiem()",
    """CREATE TABLE kho.lien_ket_phan_bo (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        lien_ket_id uuid NOT NULL,
        cau_phan text NOT NULL CHECK (cau_phan IN ('GOC','LAI','PHI','GIAI_NGAN')),
        logical_target_id uuid NOT NULL,
        lich_tra_no_id uuid,
        khe_uoc_phien_ban_id uuid,
        su_kien_vay_phan_id uuid,
        amount_minor bigint NOT NULL CHECK (amount_minor > 0),
        currency_code char(3) NOT NULL,
        currency_scale smallint NOT NULL,
        trang_thai text NOT NULL DEFAULT 'HIEU_LUC' CHECK (trang_thai IN ('HIEU_LUC','HUY')),
        huy_boi text,
        huy_luc timestamptz,
        ly_do_huy text,
        basis_revision_sha256 text NOT NULL,
        bien_nhan_id uuid,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (num_nonnulls(lich_tra_no_id, khe_uoc_phien_ban_id) = 1),
        CHECK ((cau_phan = 'GIAI_NGAN') = (khe_uoc_phien_ban_id IS NOT NULL)),
        CHECK (trang_thai <> 'HUY' OR (huy_boi IS NOT NULL AND huy_luc IS NOT NULL AND ly_do_huy IS NOT NULL)),
        FOREIGN KEY (phap_nhan_id, lien_ket_id) REFERENCES kho.lien_ket_chung_tu (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, logical_target_id) REFERENCES kho.dich_phan_bo_tien (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, lich_tra_no_id) REFERENCES master.lich_tra_no (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, khe_uoc_phien_ban_id) REFERENCES master.khe_uoc_vay_phien_ban (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, su_kien_vay_phan_id) REFERENCES kho.su_kien_vay_phan (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id))""",
    "CREATE UNIQUE INDEX lien_ket_phan_bo_dich_uq ON kho.lien_ket_phan_bo (lien_ket_id, logical_target_id) WHERE trang_thai = 'HIEU_LUC'",
    "CREATE INDEX lien_ket_phan_bo_dich ON kho.lien_ket_phan_bo (logical_target_id) WHERE trang_thai = 'HIEU_LUC'",
    # ngân sách chung (internal owner-only): DIRECT góp parent một lần, CHILD góp child hiệu lực của parent hiệu lực; mỗi amount một lần
    """CREATE OR REPLACE FUNCTION kho.tien_da_phan_bo_noi_bo(bank uuid) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT (SELECT coalesce(sum(k.so_tien_khop_minor), 0) FROM kho.lien_ket_chung_tu k WHERE k.chung_tu_a_id = bank AND k.trang_thai <> 'HUY'
                  AND k.link_purpose = 'MONEY' AND k.allocation_model = 'DIRECT')
             + (SELECT coalesce(sum(c.amount_minor), 0) FROM kho.lien_ket_phan_bo c JOIN kho.lien_ket_chung_tu k ON k.id = c.lien_ket_id
                  WHERE k.chung_tu_a_id = bank AND k.trang_thai <> 'HUY' AND k.allocation_model = 'CHILD' AND c.trang_thai = 'HIEU_LUC')
        $$""",
    """CREATE OR REPLACE FUNCTION kho.dich_da_phan_bo_noi_bo(dich uuid) RETURNS bigint
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(sum(c.amount_minor), 0) FROM kho.lien_ket_phan_bo c JOIN kho.lien_ket_chung_tu k ON k.id = c.lien_ket_id
        WHERE c.logical_target_id = dich AND c.trang_thai = 'HIEU_LUC' AND k.trang_thai <> 'HUY'
        $$""",
    # sức chứa của đích = số của revision đang hiệu lực (ngày nghiệp vụ phiên) — tiêu thụ cũ vẫn trừ xuyên revision
    """CREATE OR REPLACE FUNCTION kho.dich_suc_chua_noi_bo(dich uuid, d date) RETURNS TABLE (amount_minor bigint, currency_code text, currency_scale smallint,
                                                                                            revision_id uuid, precision_status text, basis text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT t.amount_minor, rtrim(t.currency_code), t.currency_scale, t.id, t.precision_status, t.basis_revision_sha256
        FROM kho.dich_phan_bo_tien x JOIN master.lich_tra_no t ON t.dich_phan_bo_id = x.id AND t.model_version = 'M9_TYPED'
        WHERE x.id = dich AND x.target_kind = 'NGHIA_VU' AND t.phien_ban_id = master.phien_ban_hieu_luc(x.hop_dong_id, d)
        UNION ALL
        SELECT r.so_tien_minor, rtrim(r.currency_code), r.currency_scale, r.id, r.precision_status, r.revision_sha256
        FROM kho.dich_phan_bo_tien x JOIN master.khe_uoc_vay_phien_ban r ON r.dich_phan_bo_id = x.id
        WHERE x.id = dich AND x.target_kind = 'GIAI_NGAN' AND r.hop_dong_phien_ban_id = master.phien_ban_hieu_luc(x.hop_dong_id, d)
        $$""",
    # wrapper app: BANK (cần M1 + PN) — remaining chỉ khi proof encoding còn khớp và không có link tiền chưa phân loại
    """CREATE OR REPLACE FUNCTION kho.tien_con_lai(bank uuid) RETURNS TABLE (so_tien_minor bigint, da_phan_bo_minor bigint, con_lai_minor bigint, currency_code text,
                                                                          currency_scale smallint, chieu text, blocked_reason text, version_digest text)
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE c record; e record; da bigint; ly text;
        BEGIN
            SELECT * INTO c FROM kho.chung_tu WHERE id = bank AND loai = 'SAO_KE';
            IF c.id IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(c.phap_nhan_id, 'M1') THEN
                RETURN;
            END IF;
            SELECT * INTO e FROM kho.chung_tu_tien_encoding WHERE chung_tu_id = bank AND state = 'HIEU_LUC';
            da := kho.tien_da_phan_bo_noi_bo(bank);
            ly := CASE WHEN e.id IS NULL THEN 'KHONG_CO_PROOF_TIEN'
                       WHEN e.precision_status <> 'PROVEN' THEN 'PROOF_TIEN_CHUA_CHUNG_MINH'
                       WHEN e.money_digest <> kho.tien_digest_noi_bo(bank, e.currency_scale) THEN 'PROOF_TIEN_LECH'
                       WHEN EXISTS (SELECT 1 FROM kho.lien_ket_chung_tu k WHERE k.chung_tu_a_id = bank AND k.trang_thai <> 'HUY' AND k.link_purpose = 'LEGACY_UNCLASSIFIED')
                            THEN 'LINK_TIEN_CHUA_PHAN_LOAI'
                       END;
            RETURN QUERY SELECT c.so_tien_minor, da, CASE WHEN ly IS NULL THEN c.so_tien_minor - da END, rtrim(c.tien_te), e.currency_scale, c.chieu, ly,
                                kho.tien_digest_noi_bo(bank, e.currency_scale);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.dich_tien_con_lai(dich uuid, valid_on date DEFAULT NULL) RETURNS TABLE (suc_chua_minor bigint, da_phan_bo_minor bigint,
                                                     con_lai_minor bigint, currency_code text, currency_scale smallint, revision_id uuid, basis text, blocked_reason text)
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE x record; s record; da bigint;
        BEGIN
            SELECT * INTO x FROM kho.dich_phan_bo_tien WHERE id = dich;
            IF x.id IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(x.phap_nhan_id, x.module_nghiep_vu) THEN
                RETURN;
            END IF;
            SELECT * INTO s FROM kho.dich_suc_chua_noi_bo(dich, coalesce(valid_on, master.ktt_ngay()));
            da := kho.dich_da_phan_bo_noi_bo(dich);
            RETURN QUERY SELECT s.amount_minor, da,
                CASE WHEN s.revision_id IS NOT NULL AND s.amount_minor IS NOT NULL AND s.precision_status = 'PROVEN' AND s.amount_minor >= da THEN s.amount_minor - da END,
                s.currency_code, s.currency_scale, s.revision_id, s.basis,
                CASE WHEN s.revision_id IS NULL THEN 'DICH_CHUA_HIEU_LUC' WHEN s.amount_minor IS NULL THEN 'DICH_THIEU_SO_TIEN'
                     WHEN s.precision_status <> 'PROVEN' THEN 'DICH_PRECISION_CHUA_CHUNG_MINH' WHEN s.amount_minor < da THEN 'DICH_SUC_CHUA_DUOI_DA_TIEU' END;
        END $$""",
    # tổng parent/child + ngân sách BANK + đích, kiểm cuối giao dịch (deferred) — không dựa thứ tự câu lệnh của app
    """CREATE OR REPLACE FUNCTION kho.kiem_tong_lien_ket_noi_bo(lk uuid) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE k record; a record; tong bigint; n integer; t record; s record;
        BEGIN
            SELECT * INTO k FROM kho.lien_ket_chung_tu WHERE id = lk;
            IF k.id IS NULL OR k.link_purpose <> 'MONEY' THEN RETURN; END IF;
            IF k.allocation_model = 'CHILD' THEN
                SELECT coalesce(sum(amount_minor), 0), count(*) INTO tong, n FROM kho.lien_ket_phan_bo WHERE lien_ket_id = lk AND trang_thai = 'HIEU_LUC';
                IF k.trang_thai <> 'HUY' AND (n = 0 OR tong <> k.so_tien_khop_minor) THEN
                    RAISE EXCEPTION 'LIEN_KET_TONG_LECH: parent % ≠ tổng child hiệu lực %', k.so_tien_khop_minor, tong USING ERRCODE = 'P0001';
                END IF;
                IF k.trang_thai = 'HUY' AND n > 0 THEN
                    RAISE EXCEPTION 'LIEN_KET_HUY_CON_CHILD: hủy parent phải hủy mọi child' USING ERRCODE = 'P0001';
                END IF;
                FOR t IN SELECT DISTINCT logical_target_id FROM kho.lien_ket_phan_bo WHERE lien_ket_id = lk AND trang_thai = 'HIEU_LUC' LOOP
                    SELECT * INTO s FROM kho.dich_suc_chua_noi_bo(t.logical_target_id, master.ktt_ngay());
                    IF s.revision_id IS NULL OR s.amount_minor IS NULL OR kho.dich_da_phan_bo_noi_bo(t.logical_target_id) > s.amount_minor THEN
                        RAISE EXCEPTION 'VUOT_NGHIA_VU: đích logic vượt sức chứa (tiêu thụ xuyên revision)' USING ERRCODE = 'P0001';
                    END IF;
                END LOOP;
            END IF;
            SELECT * INTO a FROM kho.chung_tu WHERE id = k.chung_tu_a_id;
            IF kho.tien_da_phan_bo_noi_bo(a.id) > a.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_TIEN_KHA_DUNG: tổng phân bổ mọi module vượt số tiền BANK' USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.kiem_tong_lien_ket_trg() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_TABLE_NAME = 'lien_ket_phan_bo' THEN
                PERFORM kho.kiem_tong_lien_ket_noi_bo(NEW.lien_ket_id);
            ELSE
                PERFORM kho.kiem_tong_lien_ket_noi_bo(NEW.id);
            END IF;
            RETURN NULL;
        END $$""",
    """CREATE CONSTRAINT TRIGGER lien_ket_phan_bo_tong AFTER INSERT OR UPDATE ON kho.lien_ket_phan_bo DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION kho.kiem_tong_lien_ket_trg()""",
    """CREATE CONSTRAINT TRIGGER lien_ket_chung_tu_tong AFTER INSERT OR UPDATE ON kho.lien_ket_chung_tu DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION kho.kiem_tong_lien_ket_trg()""",
    # child: chỉ INSERT vào parent CHILD vừa tạo cùng giao dịch, đích/revision/cấu phần/đồng tiền/chiều tiền/proof khớp; UPDATE chỉ HIEU_LUC→HUY
    """CREATE OR REPLACE FUNCTION kho.lien_ket_phan_bo_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE k record; a record; x record; e record; ai text := master.ktt_danh_tinh(); rv record;
        BEGIN
            IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'PHAN_BO_KHONG_XOA' USING ERRCODE = 'P0001'; END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(NEW.id, NEW.phap_nhan_id, NEW.lien_ket_id, NEW.cau_phan, NEW.logical_target_id, NEW.lich_tra_no_id, NEW.khe_uoc_phien_ban_id, NEW.su_kien_vay_phan_id,
                       NEW.amount_minor, NEW.currency_code, NEW.currency_scale, NEW.basis_revision_sha256, NEW.bien_nhan_id, NEW.tao_boi, NEW.tao_luc)
                   IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.lien_ket_id, OLD.cau_phan, OLD.logical_target_id, OLD.lich_tra_no_id, OLD.khe_uoc_phien_ban_id,
                       OLD.su_kien_vay_phan_id, OLD.amount_minor, OLD.currency_code, OLD.currency_scale, OLD.basis_revision_sha256, OLD.bien_nhan_id, OLD.tao_boi, OLD.tao_luc)
                   OR OLD.trang_thai = 'HUY' OR NEW.trang_thai <> 'HUY' THEN
                    RAISE EXCEPTION 'PHAN_BO_BAT_BIEN: chỉ hủy (giữ lịch sử), không sửa/reparent/mở lại' USING ERRCODE = 'P0001';
                END IF;
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.huy_boi OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M9') OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M1')
                   OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                    RAISE EXCEPTION 'PHAN_BO_KHONG_CO_QUYEN' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            SELECT * INTO k FROM kho.lien_ket_chung_tu WHERE id = NEW.lien_ket_id;
            PERFORM 1 FROM master.hop_dong WHERE id = k.hop_dong_id FOR UPDATE;  -- thứ tự HĐ → BANK → đích
            SELECT * INTO a FROM kho.chung_tu WHERE id = k.chung_tu_a_id FOR UPDATE;
            SELECT * INTO x FROM kho.dich_phan_bo_tien WHERE id = NEW.logical_target_id FOR UPDATE;
            IF ai IS NULL OR ai IS DISTINCT FROM NEW.tao_boi OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M9') OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M1')
               OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL) THEN
                RAISE EXCEPTION 'PHAN_BO_KHONG_CO_QUYEN: nối tiền M9 cần kế toán có M1 + M9 của phiên' USING ERRCODE = 'P0001';
            END IF;
            IF k.allocation_model IS DISTINCT FROM 'CHILD' OR k.trang_thai = 'HUY' OR k.tao_luc <> now() OR k.phap_nhan_id <> NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'PHAN_BO_SAI_PARENT: child chỉ vào parent CHILD hiệu lực tạo cùng giao dịch, cùng pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            IF x.hop_dong_id IS DISTINCT FROM k.hop_dong_id OR x.cau_phan IS DISTINCT FROM NEW.cau_phan THEN
                RAISE EXCEPTION 'PHAN_BO_SAI_DICH: đích phải cùng HĐ của parent và đúng cấu phần' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.lich_tra_no_id IS NOT NULL THEN
                SELECT t.id, t.dich_phan_bo_id AS dich, p.trang_thai, t.currency_code, t.currency_scale INTO rv FROM master.lich_tra_no t
                    JOIN master.hop_dong_phien_ban p ON p.id = t.phien_ban_id WHERE t.id = NEW.lich_tra_no_id;
            ELSE
                SELECT r.id, r.dich_phan_bo_id AS dich, p.trang_thai, r.currency_code, r.currency_scale INTO rv FROM master.khe_uoc_vay_phien_ban r
                    JOIN master.hop_dong_phien_ban p ON p.id = r.hop_dong_phien_ban_id WHERE r.id = NEW.khe_uoc_phien_ban_id;
            END IF;
            IF rv.dich IS DISTINCT FROM NEW.logical_target_id OR rv.trang_thai IS DISTINCT FROM 'DA_DUYET' THEN
                RAISE EXCEPTION 'PHAN_BO_SAI_REVISION: revision phải thuộc đúng đích logic và phiên bản đã duyệt' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO e FROM kho.chung_tu_tien_encoding WHERE chung_tu_id = a.id AND state = 'HIEU_LUC';
            IF e.id IS NULL OR e.precision_status <> 'PROVEN' OR e.money_digest <> kho.tien_digest_noi_bo(a.id, e.currency_scale) THEN
                RAISE EXCEPTION 'PROOF_TIEN_CHUA_DU: BANK chưa có proof encoding còn khớp' USING ERRCODE = 'P0001';
            END IF;
            IF rtrim(NEW.currency_code) IS DISTINCT FROM rtrim(e.currency_code) OR NEW.currency_scale IS DISTINCT FROM e.currency_scale
               OR rtrim(NEW.currency_code) IS DISTINCT FROM rtrim(rv.currency_code) OR NEW.currency_scale IS DISTINCT FROM rv.currency_scale THEN
                RAISE EXCEPTION 'PHAN_BO_KHAC_TIEN_TE: child phải cùng loại tiền + scale với proof BANK và đích' USING ERRCODE = 'P0001';
            END IF;
            IF (NEW.cau_phan = 'GIAI_NGAN' AND a.chieu IS DISTINCT FROM 'THU') OR (NEW.cau_phan <> 'GIAI_NGAN' AND a.chieu IS DISTINCT FROM 'CHI') THEN
                RAISE EXCEPTION 'PHAN_BO_SAI_CHIEU_TIEN: giải ngân là tiền về, trả gốc/lãi/phí là tiền đi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lien_ket_phan_bo_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.lien_ket_phan_bo FOR EACH ROW EXECUTE FUNCTION kho.lien_ket_phan_bo_kiem()",
    # parent link chung: thay lien_ket_kiem M0011 — giữ nguyên nhánh CRM, ngân sách BANK dùng tổng chung (gồm child M9), discriminator do DB
    """CREATE OR REPLACE FUNCTION kho.lien_ket_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE
            a record; b record; l record; hd uuid; d date := master.ktt_ngay(); purpose text; model text;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.huy_khong_vet_truoc_v10 IS DISTINCT FROM OLD.huy_khong_vet_truoc_v10
                   OR (NEW.link_purpose, NEW.allocation_model, NEW.bien_nhan_id) IS DISTINCT FROM (OLD.link_purpose, OLD.allocation_model, OLD.bien_nhan_id) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA: không đổi mục đích/mô hình/biên nhận của liên kết' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai = 'HUY' AND NEW.trang_thai <> 'HUY' THEN
                    RAISE EXCEPTION 'LIEN_KET_DA_HUY: liên kết đã hủy không mở lại; tạo liên kết mới' USING ERRCODE = 'P0001';
                END IF;
                IF ROW(NEW.id, NEW.phap_nhan_id, NEW.chung_tu_a_id, NEW.chung_tu_b_id, NEW.loai, NEW.so_tien_khop_minor, NEW.tien_te, NEW.nguon_suy_luan,
                       NEW.do_tin_cay, NEW.nguoi_duyet, NEW.duyet_luc, NEW.entry_dm, NEW.tao_luc, NEW.lich_thu_id, NEW.hop_dong_id, NEW.khoa_idempotency,
                       NEW.tao_boi, NEW.can_cu)
                   IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.chung_tu_a_id, OLD.chung_tu_b_id, OLD.loai, OLD.so_tien_khop_minor, OLD.tien_te, OLD.nguon_suy_luan,
                       OLD.do_tin_cay, OLD.nguoi_duyet, OLD.duyet_luc, OLD.entry_dm, OLD.tao_luc, OLD.lich_thu_id, OLD.hop_dong_id, OLD.khoa_idempotency,
                       OLD.tao_boi, OLD.can_cu) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA: chỉ đổi trạng thái/hủy; sửa = hủy + tạo mới' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai = 'HUY' AND (NEW.huy_luc, NEW.huy_boi, NEW.ly_do_huy) IS DISTINCT FROM (OLD.huy_luc, OLD.huy_boi, OLD.ly_do_huy) THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_SUA' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.huy_khong_vet_truoc_v10 OR NEW.trang_thai = 'HUY' THEN
                RAISE EXCEPTION 'LIEN_KET_MOI_KHONG_HOP_LE' USING ERRCODE = 'P0001';
            END IF;
            -- R1: mục đích/mô hình do DB suy từ loại + đích, client không tự chọn
            purpose := CASE WHEN NEW.lich_thu_id IS NOT NULL OR NEW.loai = 'VAY_TIEN' THEN 'MONEY' WHEN NEW.so_tien_khop_minor IS NULL THEN 'EVIDENCE' ELSE 'LEGACY_UNCLASSIFIED' END;
            model := CASE WHEN NEW.lich_thu_id IS NOT NULL THEN 'DIRECT' WHEN NEW.loai = 'VAY_TIEN' THEN 'CHILD' END;
            IF (NEW.link_purpose IS NOT NULL AND NEW.link_purpose <> purpose) OR (NEW.allocation_model IS NOT NULL AND NEW.allocation_model IS DISTINCT FROM model) THEN
                RAISE EXCEPTION 'LIEN_KET_PHAN_LOAI_SAI: mục đích/mô hình liên kết do CSDL xác định' USING ERRCODE = 'P0001';
            END IF;
            NEW.link_purpose := purpose;
            NEW.allocation_model := model;
            IF NEW.lich_thu_id IS NOT NULL OR NEW.loai = 'VAY_TIEN' THEN  -- khóa hợp đồng TRƯỚC, rồi khoản tiền, rồi đợt/đích
                IF NEW.lich_thu_id IS NOT NULL THEN
                    SELECT p.hop_dong_id INTO hd FROM master.lich_thu x JOIN master.hop_dong_phien_ban p ON p.id = x.phien_ban_id WHERE x.id = NEW.lich_thu_id;
                ELSE
                    hd := NEW.hop_dong_id;
                END IF;
                PERFORM 1 FROM master.hop_dong WHERE id = hd FOR UPDATE;
            END IF;
            SELECT * INTO a FROM kho.chung_tu WHERE id = NEW.chung_tu_a_id FOR UPDATE;
            SELECT * INTO b FROM kho.chung_tu WHERE id = NEW.chung_tu_b_id;
            IF a.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR b.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai = 'VAY_TIEN' THEN
                IF a.loai <> 'SAO_KE' OR b.loai <> 'HO_SO_VAY' OR b.du_lieu->>'hop_dong_id' IS DISTINCT FROM NEW.hop_dong_id::text
                   OR NOT EXISTS (SELECT 1 FROM master.hop_dong h WHERE h.id = NEW.hop_dong_id AND h.loai = 'VAY' AND h.phap_nhan_id = NEW.phap_nhan_id) THEN
                    RAISE EXCEPTION 'LIEN_KET_SAI_THAM_CHIEU: tiền vay nối BANK M1 với hồ sơ vay của đúng HĐ VAY' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.so_tien_khop_minor IS NULL OR NEW.so_tien_khop_minor <= 0 OR NEW.tien_te IS DISTINCT FROM a.tien_te THEN
                    RAISE EXCEPTION 'LIEN_KET_SO_TIEN: parent tiền vay cần số dương cùng loại tiền BANK' USING ERRCODE = 'P0001';
                END IF;
                IF master.ktt_danh_tinh() IS NULL OR master.ktt_danh_tinh() IS DISTINCT FROM NEW.tao_boi
                   OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M9') OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M1') THEN
                    RAISE EXCEPTION 'LIEN_KET_KHONG_CO_QUYEN: nối tiền vay cần phiên có M1 + M9' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.lich_thu_id IS NULL THEN
                RETURN NEW;
            END IF;
            SELECT lt.*, p.hop_dong_id AS hd, p.chung_tu_id AS ct_phien_ban, p.trang_thai AS pb_trang_thai, p.phien_ban AS so_pb
                INTO l FROM master.lich_thu lt JOIN master.hop_dong_phien_ban p ON p.id = lt.phien_ban_id WHERE lt.id = NEW.lich_thu_id FOR UPDATE OF lt;
            IF l.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_PHAP_NHAN' USING ERRCODE = 'P0001';
            END IF;
            IF l.pb_trang_thai IS DISTINCT FROM 'DA_DUYET' OR l.phien_ban_id IS DISTINCT FROM master.phien_ban_hieu_luc(l.hd, d) THEN
                RAISE EXCEPTION 'LICH_KHONG_HIEU_LUC: đợt không thuộc phiên bản hiệu lực ngày %', d USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM master.hop_dong_phien_ban v WHERE v.hop_dong_id = l.hd AND v.trang_thai = 'DA_DUYET' AND v.phien_ban > l.so_pb
                       AND NOT EXISTS (SELECT 1 FROM master.lich_thu y WHERE y.phien_ban_id = v.id AND y.khoa_nghia_vu = l.khoa_nghia_vu
                                       AND (y.so_tien_minor, y.tien_te, y.han, y.moc, y.loai, y.dot, y.co_so) IS NOT DISTINCT FROM (l.so_tien_minor, l.tien_te, l.han, l.moc, l.loai, l.dot, l.co_so))) THEN
                RAISE EXCEPTION 'NGHIA_VU_SAP_THAY_DOI: phụ lục đã duyệt sẽ đổi/bỏ đợt này — xử lý theo phụ lục' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai <> 'HOP_DONG_DOT_TIEN' OR a.loai <> 'SAO_KE' OR a.chieu IS DISTINCT FROM 'THU' OR NEW.chung_tu_b_id IS DISTINCT FROM l.ct_phien_ban THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_THAM_CHIEU: tiền thu ↔ đợt phải nối với chứng từ của đúng phiên bản' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.hop_dong_id IS DISTINCT FROM l.hd THEN
                RAISE EXCEPTION 'LIEN_KET_SAI_HOP_DONG' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.so_tien_khop_minor IS NULL OR NEW.so_tien_khop_minor <= 0 OR l.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_SO_TIEN: cần số tiền dương và đợt có số tiền' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.tien_te IS DISTINCT FROM a.tien_te OR NEW.tien_te IS DISTINCT FROM l.tien_te OR a.so_tien_minor IS NULL THEN
                RAISE EXCEPTION 'LIEN_KET_KHAC_TIEN_TE: không bù trừ khác loại tiền' USING ERRCODE = 'P0001';
            END IF;
            IF kho.tien_da_phan_bo_noi_bo(a.id) + NEW.so_tien_khop_minor > a.so_tien_minor THEN  -- ngân sách chung: gồm child M9 hiệu lực
                RAISE EXCEPTION 'VUOT_TIEN_KHA_DUNG: % + % > %', kho.tien_da_phan_bo_noi_bo(a.id), NEW.so_tien_khop_minor, a.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            IF master.da_lien_ket(l.hd, l.khoa_nghia_vu) + NEW.so_tien_khop_minor > l.so_tien_minor THEN
                RAISE EXCEPTION 'VUOT_NGHIA_VU: đã nối % + % > %', master.da_lien_ket(l.hd, l.khoa_nghia_vu), NEW.so_tien_khop_minor, l.so_tien_minor USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- quyền vai trò web: đọc/INSERT typed qua RLS + trigger; KHÔNG UPDATE/DELETE typed; raw toàn phần chỉ qua hàm integration
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA giao_tiep TO app_web;
            GRANT SELECT ON master.don_vi_tien, kho.anh_chup_nguon, kho.ban_ghi_nguon TO app_web;
            GRANT SELECT, INSERT ON giao_tiep.tep_tach_phap_nhan TO app_web;
            GRANT SELECT, INSERT, UPDATE ON master.anh_xa_nguon TO app_web;
            GRANT SELECT, INSERT ON master.vay_dinh_danh_nguon, master.vay_phien_ban, master.khe_uoc_vay, master.khe_uoc_vay_phien_ban, master.lai_suat_vay,
                kho.su_kien_vay, kho.su_kien_vay_phan, kho.dich_phan_bo_tien, master.lich_tra_no, kho.bien_nhan_thao_tac TO app_web;
            GRANT SELECT, INSERT, UPDATE ON kho.lien_ket_phan_bo TO app_web;
            REVOKE ALL ON giao_tiep.tep_tiep_nhan, kho.chung_tu_tien_encoding, master.dinh_danh_cong_ty_nguon FROM app_web;
            GRANT EXECUTE ON FUNCTION giao_tiep.ghi_anh_chup(jsonb), giao_tiep.gan_phap_nhan_theo_anh_xa(uuid), giao_tiep.cong_ty_chua_map(), kho.tien_con_lai(uuid),
                kho.dich_tien_con_lai(uuid, date), master.m9_van_tay(uuid), master.m9_chan(uuid, text), master.m9_phien_ban_hieu_luc(uuid, date) TO app_web;
        END IF;
    END $$""",
    """REVOKE EXECUTE ON FUNCTION giao_tiep.ghi_anh_chup(jsonb), giao_tiep.gan_phap_nhan_theo_anh_xa(uuid), giao_tiep.cong_ty_chua_map(), kho.tien_con_lai(uuid),
        kho.dich_tien_con_lai(uuid, date),
        master.m9_van_tay(uuid), master.m9_chan(uuid, text), master.m9_phien_ban_hieu_luc(uuid, date), master.m9_van_tay_noi_bo(uuid), master.m9_manifest_phien_ban_noi_bo(uuid),
        master.m9_kiem_do_thi_noi_bo(uuid, text), kho.tien_da_phan_bo_noi_bo(uuid), kho.dich_da_phan_bo_noi_bo(uuid), kho.dich_suc_chua_noi_bo(uuid, date),
        kho.tien_digest_noi_bo(uuid, smallint), kho.kiem_tong_lien_ket_noi_bo(uuid) FROM PUBLIC""",
) + _rls_v13()

# Chuỗi lịch sử full-M9 (M0001–M0012 + M0013 ở trên): CHỈ là định nghĩa lịch sử/lineage, KHÔNG nằm trong chuỗi mặc định và không được
# execute bởi migrate(). DB đã ghi đúng checksum M0013 này bị từ chối sạch (LEGACY_FULL_M9_LINEAGE), không alias/rewrite/skip.
PG_MIGRATIONS_LICH_SU_FULL_M9: tuple[tuple[str, ...], ...] = (M0001, M0002, M0003, M0004, M0005, M0006, M0007, M0008, M0009, M0010, M0011,
                                                              M0012, M0013)
LEGACY_FULL_M9_M0013_SHA256 = "2a2acb81bc85f57a5643a4736528d120f9f48ee1d005ad8bec0a178ba1926d40"  # root pin lineage-pins.json (155 câu)


# ---------------------------------------------------------------------------
# 0013 COMMON (M0–M5 gói 01, contract M0-M5-SQL-VA-FIXTURE-01 §4): nguồn/profile/năng lực nguồn trước PN, raw + bundle vai trò artifact,
#   biên nhận capture prePN `m0-capture/v1` (namespace (instance, CAPTURE, client_key)), dòng nguồn, mapping WAREHOUSE trung tính
#   (instance/profile/MaKho → PN, revision + hiệu lực + chống chồng lấn/retarget), derivative theo PN, biên nhận nghiệp vụ (PN, module,
#   operation, key). Không loan/money/M9 grants, không _rls_v13, không UNIQUE raw/profile nuốt lần fetch. Quyền nguồn lưu/ép tại DB.
#   Sửa 02 (GIAO-SUA-M0-M5-INTAKE-UI-02): stage tin cậy bất biến chỉ chủ bảng ghi + consumer stageID/expectedH (không writer free-JSON);
#   biên nhận/lô M5 chỉ qua đường định nghĩa; discriminator chủ sở hữu trung tính kho.chung_tu (CRM/M1/M5) + core PHIEU_KHO quantity-only;
#   metadata nguồn theo năng lực nguồn; thu hồi ACL kế thừa của vai trò cũ trên object mới; mapping chỉ qua hàm định nghĩa (helper chạy quyền chủ).
# ---------------------------------------------------------------------------
_KIEM_NGUON = """
            IF master.ktt_danh_tinh() IS NULL OR NOT master.ktt_nguon_duoc({i}, {r}, {s}, {a}, {p}) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: cần năng lực nguồn % của phiên trên đúng instance/profile', {a} USING ERRCODE = 'P0001';
            END IF;
"""


def _chi_ghi_them(bang: str, ten: str) -> str:
    return f"CREATE TRIGGER {ten} BEFORE UPDATE OR DELETE ON {bang} FOR EACH ROW EXECUTE FUNCTION giao_tiep.chi_ghi_them()"


M0013_COMMON = (
    "SET LOCAL check_function_bodies = off",
    "CREATE SCHEMA IF NOT EXISTS giao_tiep",
    """CREATE OR REPLACE FUNCTION giao_tiep.chi_ghi_them() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'BAN_GHI_BAT_BIEN: % chỉ ghi thêm, không sửa/xóa', TG_TABLE_NAME USING ERRCODE = 'P0001';
        END $$""",
    # current_user ĐÚNG là chủ (relowner) của bảng — INVOKER, không membership/superuser/GUC. Trong hàm definer của chủ, current_user = chủ.
    """CREATE OR REPLACE FUNCTION master.la_chu_bang(p regclass) RETURNS boolean
        LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT coalesce((SELECT c.relowner = (SELECT r.oid FROM pg_catalog.pg_roles r WHERE r.rolname = current_user)
                         FROM pg_catalog.pg_class c WHERE c.oid = p), false)
        $$""",
    # --- registry nguồn (seed bởi chủ CSDL; app không INSERT/UPDATE)
    """CREATE TABLE master.nguon_instance (
        source_instance_id text PRIMARY KEY CHECK (source_instance_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
        trang_thai text NOT NULL DEFAULT 'HOAT_DONG' CHECK (trang_thai IN ('HOAT_DONG','DUNG')),
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE master.nguon_profile (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        profile_ref text NOT NULL CHECK (length(profile_ref) BETWEEN 1 AND 300),
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ '^[0-9a-f]{64}$'),
        payload jsonb NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (source_instance_id, profile_ref),
        UNIQUE (source_instance_id, profile_ref, profile_sha256))""",
    _chi_ghi_them("master.nguon_profile", "nguon_profile_bat_bien"),
    """CREATE TABLE master.nguon_pham_vi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        scope_ref text NOT NULL CHECK (length(scope_ref) BETWEEN 1 AND 300),
        ma_kho text NOT NULL,
        so_phieu text NOT NULL,
        sections text[] NOT NULL CHECK (cardinality(sections) >= 1),
        coverage_binding text NOT NULL,
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE (source_instance_id, scope_ref))""",
    _chi_ghi_them("master.nguon_pham_vi", "nguon_pham_vi_bat_bien"),
    """CREATE TABLE master.nang_luc_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        hanh_dong text NOT NULL CHECK (hanh_dong IN ('INTAKE','READ_SOURCE','SOURCE_MAP')),
        target_phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK ((hanh_dong = 'SOURCE_MAP') = (target_phap_nhan_id IS NOT NULL)),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE NULLS NOT DISTINCT (nguoi_dung_id, source_instance_id, profile_ref, profile_sha256, hanh_dong, target_phap_nhan_id))""",
    # năng lực chỉ thêm hoặc thu hồi (DELETE bởi chủ CSDL); không sửa tại chỗ
    """CREATE OR REPLACE FUNCTION master.nang_luc_nguon_khong_sua() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'NANG_LUC_BAT_BIEN: chỉ thêm hoặc thu hồi năng lực nguồn, không sửa' USING ERRCODE = 'P0001';
        END $$""",
    "CREATE TRIGGER nang_luc_nguon_khong_sua BEFORE UPDATE ON master.nang_luc_nguon FOR EACH ROW EXECUTE FUNCTION master.nang_luc_nguon_khong_sua()",
    """CREATE TABLE master.nguon_master_noi_dung (
        reference_id text PRIMARY KEY CHECK (length(reference_id) BETWEEN 1 AND 300),
        raw_sha256 text NOT NULL UNIQUE CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 0),
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    _chi_ghi_them("master.nguon_master_noi_dung", "nguon_master_noi_dung_bat_bien"),
    """CREATE TABLE master.nguon_su_kien_do_luong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        declaration_ref text NOT NULL,
        payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
        payload jsonb NOT NULL,
        dieu_kien jsonb NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE (source_instance_id, profile_ref, profile_sha256, declaration_ref, payload_sha256))""",
    _chi_ghi_them("master.nguon_su_kien_do_luong", "nguon_su_kien_do_luong_bat_bien"),
    # --- năng lực nguồn của phiên: ID + login hoạt động (ktt_danh_tinh), instance đang hoạt động, đúng profile ref+SHA, action, PN đích
    """CREATE OR REPLACE FUNCTION master.ktt_nguon_duoc(p_instance text, p_ref text, p_sha text, p_hanh_dong text, p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.nang_luc_nguon c
                       JOIN master.nguoi_dung n ON n.id = c.nguoi_dung_id
                       JOIN master.nguon_instance i ON i.source_instance_id = c.source_instance_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND i.trang_thai = 'HOAT_DONG' AND c.source_instance_id = p_instance AND c.profile_ref = p_ref
                         AND c.profile_sha256 = p_sha AND c.hanh_dong = p_hanh_dong AND c.target_phap_nhan_id IS NOT DISTINCT FROM p_pn)
        $$""",
    # metadata nguồn chỉ hiện với phiên có ÍT NHẤT một năng lực nguồn hiện hành trên đúng instance (và đúng profile ref+SHA nếu truyền)
    """CREATE OR REPLACE FUNCTION master.ktt_nguon_co_nang_luc(p_instance text, p_ref text, p_sha text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.nang_luc_nguon c
                       JOIN master.nguoi_dung n ON n.id = c.nguoi_dung_id
                       JOIN master.nguon_instance i ON i.source_instance_id = c.source_instance_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND i.trang_thai = 'HOAT_DONG' AND c.source_instance_id = p_instance
                         AND (p_ref IS NULL OR (c.profile_ref = p_ref AND c.profile_sha256 = p_sha)))
        $$""",
    # --- raw: metadata toàn phần chỉ integration (không cấp app_web); object key content-addressed do máy chủ ghi
    """CREATE TABLE giao_tiep.tep_tiep_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        object_key text NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 0),
        media_type text NOT NULL CHECK (length(media_type) BETWEEN 1 AND 100),
        received_at_server timestamptz NOT NULL DEFAULT now(),
        access_domain text NOT NULL DEFAULT 'INTEGRATION_ONLY' CHECK (access_domain = 'INTEGRATION_ONLY'),
        nguoi text NOT NULL,
        CHECK (object_key = 'm0-raw/' || raw_sha256),
        UNIQUE (source_instance_id, raw_sha256),
        UNIQUE (id, source_instance_id, raw_sha256, byte_length, media_type))""",
    _chi_ghi_them("giao_tiep.tep_tiep_nhan", "tep_tiep_nhan_bat_bien"),
    # --- nội dung = bundle vai trò artifact (instance/profile/SHA + digest bộ vai trò); không dùng nativeSHA-only khi master đổi
    """CREATE TABLE kho.anh_chup_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        bundle_sha256 text NOT NULL CHECK (bundle_sha256 ~ '^[0-9a-f]{64}$'),
        state text NOT NULL CHECK (state IN ('DU_VAI_TRO','THIEU_VAI_TRO')),
        so_dong integer NOT NULL DEFAULT 0 CHECK (so_dong >= 0),
        known_at_server timestamptz NOT NULL DEFAULT now(),
        nguoi text NOT NULL,
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE (source_instance_id, profile_ref, profile_sha256, bundle_sha256),
        UNIQUE (id, source_instance_id))""",
    _chi_ghi_them("kho.anh_chup_nguon", "anh_chup_nguon_bat_bien"),
    """CREATE TABLE kho.anh_chup_nguon_vai_tro (
        snapshot_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        vai_tro text NOT NULL CHECK (vai_tro ~ '^[A-Z_]{1,40}$'),
        co_mat boolean NOT NULL,
        tep_tiep_nhan_id uuid,
        raw_sha256 text,
        byte_length bigint,
        media_type text,
        ly_do_vang text,
        PRIMARY KEY (snapshot_id, vai_tro),
        FOREIGN KEY (snapshot_id, source_instance_id) REFERENCES kho.anh_chup_nguon (id, source_instance_id),
        FOREIGN KEY (tep_tiep_nhan_id, source_instance_id, raw_sha256, byte_length, media_type)
            REFERENCES giao_tiep.tep_tiep_nhan (id, source_instance_id, raw_sha256, byte_length, media_type),
        CHECK (co_mat = (tep_tiep_nhan_id IS NOT NULL AND raw_sha256 IS NOT NULL AND byte_length IS NOT NULL AND media_type IS NOT NULL)),
        CHECK (co_mat OR (tep_tiep_nhan_id IS NULL AND raw_sha256 IS NULL AND byte_length IS NULL AND media_type IS NULL AND ly_do_vang IS NOT NULL)))""",
    _chi_ghi_them("kho.anh_chup_nguon_vai_tro", "anh_chup_nguon_vai_tro_bat_bien"),
    # --- stage tin cậy BẤT BIẾN (S01/S02/SR1): chỉ máy chủ cấu hình (đúng CHỦ BẢNG, không membership/GUC) ghi, trong giao dịch có danh tính phiên;
    #     pin mục đích/khóa/H, instance/profile/scope, claim gốc, vai trò thực, dòng nguồn, kết quả reader, kế hoạch promote/file + expected refs.
    #     Consumer chỉ nhận stage ID + expected H; ID không là bearer capability (consumer kiểm lại actor + quyền hiện hành).
    """CREATE TABLE giao_tiep.stage_tin_cay (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        muc_dich text NOT NULL CHECK (muc_dich IN ('CAPTURE','FILE_SOAT')),
        client_key text NOT NULL CHECK (length(client_key) BETWEEN 1 AND 200),
        h text NOT NULL CHECK (h ~ '^[0-9a-f]{64}$'),
        actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        actor text NOT NULL,
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        phap_nhan_id uuid REFERENCES master.phap_nhan(id),
        du_lieu jsonb NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        CHECK (muc_dich <> 'FILE_SOAT' OR phap_nhan_id IS NOT NULL),
        UNIQUE (id, muc_dich))""",
    # INVOKER: current_user phải ĐÚNG chủ bảng (không pg_has_role/superuser/GUC); actor = phiên hiện tại; chỉ INSERT
    """CREATE OR REPLACE FUNCTION giao_tiep.stage_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, giao_tiep, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'STAGE_BAT_BIEN: stage chỉ ghi thêm' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'STAGE_CHI_MAY_CHU: chỉ máy chủ cấu hình (chủ bảng) ghi stage' USING ERRCODE = 'P0001';
            END IF;
            IF master.ktt_danh_tinh() IS NULL OR NEW.actor IS DISTINCT FROM master.ktt_danh_tinh()
               OR NEW.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '') THEN
                RAISE EXCEPTION 'STAGE_ACTOR_SAI: stage phải mang đúng danh tính phiên' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER stage_kiem BEFORE INSERT OR UPDATE OR DELETE ON giao_tiep.stage_tin_cay FOR EACH ROW EXECUTE FUNCTION giao_tiep.stage_kiem()",
    # --- biên nhận capture prePN + occurrence mỏng (một hàng giữ cả hai invariant): fresh key cùng bundle → occurrence mới tái dùng blob/nội dung
    #     coverage = claim nguồn báo (vào H); coverage_hieu_luc = kết quả máy chủ đã kiểm (thiếu vai trò bắt buộc/graph partial → PARTIAL)
    """CREATE TABLE giao_tiep.lan_tiep_nhan_nguon (
        id uuid PRIMARY KEY,
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        khong_gian text NOT NULL DEFAULT 'CAPTURE' CHECK (khong_gian = 'CAPTURE'),
        client_key text NOT NULL CHECK (length(client_key) BETWEEN 1 AND 200),
        capture_contract text NOT NULL CHECK (capture_contract = 'm0-capture/v1'),
        capture_sha256 text NOT NULL CHECK (capture_sha256 ~ '^[0-9a-f]{64}$'),
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        scope_ref text NOT NULL,
        source_scope jsonb NOT NULL,
        coverage text NOT NULL,
        coverage_hieu_luc text NOT NULL,
        reported_errors text[] NOT NULL DEFAULT '{}',
        snapshot_id uuid NOT NULL,
        envelope jsonb NOT NULL,
        ket_qua jsonb NOT NULL,
        stage_id uuid NOT NULL UNIQUE REFERENCES giao_tiep.stage_tin_cay(id),
        actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        actor text NOT NULL,
        nhan_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (snapshot_id, source_instance_id) REFERENCES kho.anh_chup_nguon (id, source_instance_id),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE (source_instance_id, khong_gian, client_key),
        UNIQUE (id, source_instance_id, snapshot_id))""",
    _chi_ghi_them("giao_tiep.lan_tiep_nhan_nguon", "lan_tiep_nhan_nguon_bat_bien"),
    # --- SR02-1 (repair03): KẾT QUẢ CUỐI bất biến của một lần nhận (sau typed/hold trong CÙNG giao dịch): promote/HOLD + stage + snapshot_moi.
    #     Một hàng cho mỗi biên nhận capture; chỉ chủ bảng (máy chủ cấu hình) ghi qua giao_tiep.nguon_chot_ket_qua (INVOKER, không cấp app);
    #     replay cùng key/H đọc lại đúng hàng này (không tính lại reader/promote). Không UPDATE stage/biên nhận.
    """CREATE TABLE giao_tiep.ket_qua_cuoi_tiep_nhan (
        lan_tiep_nhan_id uuid PRIMARY KEY REFERENCES giao_tiep.lan_tiep_nhan_nguon(id),
        stage_id uuid NOT NULL UNIQUE REFERENCES giao_tiep.stage_tin_cay(id),
        capture_sha256 text NOT NULL CHECK (capture_sha256 ~ '^[0-9a-f]{64}$'),
        snapshot_moi boolean NOT NULL,
        promote jsonb NOT NULL CHECK (jsonb_typeof(promote) = 'object'),
        actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        actor text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now())""",
    """CREATE OR REPLACE FUNCTION giao_tiep.ket_qua_cuoi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, giao_tiep, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'BAN_GHI_BAT_BIEN: kết quả cuối lần nhận chỉ ghi một lần' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_CHI_CHU: chỉ máy chủ cấu hình (chủ bảng) chốt kết quả lần nhận' USING ERRCODE = 'P0001';
            END IF;
            IF master.ktt_danh_tinh() IS NULL OR NEW.actor IS DISTINCT FROM master.ktt_danh_tinh()
               OR NEW.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT EXISTS (SELECT 1 FROM giao_tiep.lan_tiep_nhan_nguon l WHERE l.id = NEW.lan_tiep_nhan_id AND l.stage_id = NEW.stage_id
                                AND l.capture_sha256 = NEW.capture_sha256 AND l.actor_id = NEW.actor_id) THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: phải đúng biên nhận/stage/H/actor của phiên' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER ket_qua_cuoi_kiem BEFORE INSERT OR UPDATE OR DELETE ON giao_tiep.ket_qua_cuoi_tiep_nhan FOR EACH ROW EXECUTE FUNCTION giao_tiep.ket_qua_cuoi_kiem()",
    # --- dòng nguồn theo snapshot (trước PN): exact row/locator/thứ tự; số lượng giữ token lexical + loại JSON, không thay bằng JSONB
    """CREATE TABLE kho.ban_ghi_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        snapshot_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        vai_tro text NOT NULL,
        section text NOT NULL,
        locator text NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu >= 0),
        source_key text,
        row_raw jsonb NOT NULL,
        row_raw_sha256 text NOT NULL CHECK (row_raw_sha256 ~ '^[0-9a-f]{64}$'),
        quantity_json_kind text CHECK (quantity_json_kind IN ('STRING','NUMBER','NULL','INVALID')),
        quantity_text text,
        validation_state text NOT NULL CHECK (validation_state IN ('HOP_LE','LOI','XUNG_DOT','MO_HO')),
        error_codes text[] NOT NULL DEFAULT '{}',
        FOREIGN KEY (snapshot_id, source_instance_id) REFERENCES kho.anh_chup_nguon (id, source_instance_id),
        FOREIGN KEY (snapshot_id, vai_tro) REFERENCES kho.anh_chup_nguon_vai_tro (snapshot_id, vai_tro),
        CHECK (quantity_text IS NULL OR quantity_json_kind IN ('STRING','NUMBER')),
        UNIQUE (snapshot_id, section, locator),
        UNIQUE (id, snapshot_id))""",
    _chi_ghi_them("kho.ban_ghi_nguon", "ban_ghi_nguon_bat_bien"),
    # --- mapping trung tính WAREHOUSE: instance/profile/MaKho → PN, revision bất biến, chỉ đóng hiệu lực; chống chồng lấn dưới khóa subject
    """CREATE TABLE master.anh_xa_nguon (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        reference_id text NOT NULL CHECK (length(reference_id) BETWEEN 1 AND 200),
        revision integer NOT NULL CHECK (revision >= 1),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        subject_kind text NOT NULL CHECK (subject_kind = 'WAREHOUSE'),
        subject_key text NOT NULL CHECK (length(subject_key) BETWEEN 1 AND 200),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        valid_from timestamptz NOT NULL,
        valid_to timestamptz,
        state text NOT NULL DEFAULT 'DA_DUYET' CHECK (state IN ('DA_DUYET','DONG')),
        thay_cho_id uuid REFERENCES master.anh_xa_nguon(id),
        nguon_quyet_dinh text NOT NULL CHECK (nguon_quyet_dinh IN ('ROOT_SEED_DEMO','CFO_V4')),
        duyet_boi text NOT NULL,
        ly_do text,
        known_at_server timestamptz NOT NULL DEFAULT now(),
        CHECK (valid_to IS NULL OR valid_to > valid_from),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        UNIQUE (reference_id, revision),
        UNIQUE (source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, revision),
        UNIQUE (id, phap_nhan_id))""",
    """CREATE OR REPLACE FUNCTION master.anh_xa_nguon_noi_bo(p_instance text, p_ref text, p_sha text, p_kind text, p_key text, p_tai timestamptz)
        RETURNS TABLE (so_hieu_luc bigint, revision_max integer)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT count(*) FILTER (WHERE m.state = 'DA_DUYET' AND (m.valid_to IS NULL OR m.valid_to > p_tai)), coalesce(max(m.revision), 0)
        FROM master.anh_xa_nguon m WHERE m.source_instance_id = p_instance AND m.profile_ref = p_ref AND m.profile_sha256 = p_sha
          AND m.subject_kind = p_kind AND m.subject_key = p_key
        $$""",
    # trigger INVOKER (S07): mọi ghi mapping chỉ qua chủ bảng — seed DEMO (ROOT_SEED_DEMO) hoặc hàm định nghĩa kho.m5_anh_xa_v4 (CFO_V4, vẫn kiểm
    # actor hiện hành: SOURCE_MAP đúng PN đích + CFO V4 + M5). App thường không có INSERT/UPDATE; helper nội bộ chạy với quyền chủ trong chính đường đó.
    """CREATE OR REPLACE FUNCTION master.anh_xa_nguon_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); chu boolean := master.la_chu_bang(TG_RELID::regclass); k record;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'ANH_XA_BAT_BIEN: không xóa mapping' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(NEW.id, NEW.reference_id, NEW.revision, NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, NEW.subject_kind, NEW.subject_key,
                       NEW.phap_nhan_id, NEW.valid_from, NEW.thay_cho_id, NEW.nguon_quyet_dinh, NEW.duyet_boi, NEW.ly_do, NEW.known_at_server)
                   IS DISTINCT FROM ROW(OLD.id, OLD.reference_id, OLD.revision, OLD.source_instance_id, OLD.profile_ref, OLD.profile_sha256, OLD.subject_kind,
                       OLD.subject_key, OLD.phap_nhan_id, OLD.valid_from, OLD.thay_cho_id, OLD.nguon_quyet_dinh, OLD.duyet_boi, OLD.ly_do, OLD.known_at_server)
                   OR OLD.state <> 'DA_DUYET' OR NEW.state <> 'DONG' OR NEW.valid_to IS NULL OR OLD.valid_to IS NOT NULL THEN
                    RAISE EXCEPTION 'ANH_XA_BAT_BIEN: chỉ đóng hiệu lực mapping một lần, không sửa/mở lại' USING ERRCODE = 'P0001';
                END IF;
                IF NOT chu OR ai IS NULL OR NOT master.ktt_duoc(OLD.phap_nhan_id, 'M5') OR NOT master.ktt_co_vai(OLD.phap_nhan_id, ARRAY['CFO'], 'V4')
                   OR NOT master.ktt_nguon_duoc(OLD.source_instance_id, OLD.profile_ref, OLD.profile_sha256, 'SOURCE_MAP', OLD.phap_nhan_id) THEN
                    RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: đóng mapping chỉ qua hàm định nghĩa, cần SOURCE_MAP đúng PN + CFO V4 + M5 của phiên' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT chu THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping chỉ ghi qua đường định nghĩa của chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.nguon_quyet_dinh = 'CFO_V4' THEN
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.duyet_boi OR NOT master.ktt_duoc(NEW.phap_nhan_id, 'M5')
                   OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['CFO'], 'V4')
                   OR NOT master.ktt_nguon_duoc(NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, 'SOURCE_MAP', NEW.phap_nhan_id) THEN
                    RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping cần đồng thời SOURCE_MAP (instance/profile → PN đích) và CFO V4 + M5 của phiên' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.nguon_quyet_dinh <> 'ROOT_SEED_DEMO' OR NEW.duyet_boi <> 'ROOT_SEED_DEMO' THEN
                RAISE EXCEPTION 'ANH_XA_SEED_SAI' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.state <> 'DA_DUYET' OR NEW.valid_to IS NOT NULL THEN
                RAISE EXCEPTION 'ANH_XA_MOI_PHAI_DANG_HIEU_LUC' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('ANH_XA|' || NEW.source_instance_id || '|' || NEW.profile_ref || '|' || NEW.profile_sha256 || '|'
                                                           || NEW.subject_kind || '|' || NEW.subject_key, 0));
            SELECT * INTO k FROM master.anh_xa_nguon_noi_bo(NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, NEW.subject_kind, NEW.subject_key,
                                                            NEW.valid_from);
            IF k.so_hieu_luc > 0 THEN
                RAISE EXCEPTION 'ANH_XA_CHONG_LAN: subject đã có mapping đang hiệu lực — đóng bản cũ (retarget có impact) trước' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.revision <> k.revision_max + 1 THEN
                RAISE EXCEPTION 'ANH_XA_REVISION_SAI: revision phải là % (expected revision đã đổi?)', k.revision_max + 1 USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER anh_xa_nguon_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.anh_xa_nguon FOR EACH ROW EXECUTE FUNCTION master.anh_xa_nguon_kiem()",
    # --- derivative theo PN/module (chỉ hàm định nghĩa ghi), không raw toàn phần
    """CREATE TABLE giao_tiep.tep_tach_phap_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        snapshot_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        module text NOT NULL CHECK (module IN ('M5')),
        mapping_revision_id uuid NOT NULL,
        selected_rows_sha256 text NOT NULL CHECK (selected_rows_sha256 ~ '^[0-9a-f]{64}$'),
        transformation_profile text NOT NULL,
        created_at_server timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (snapshot_id, source_instance_id) REFERENCES kho.anh_chup_nguon (id, source_instance_id),
        FOREIGN KEY (mapping_revision_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (snapshot_id, phap_nhan_id, module, mapping_revision_id, selected_rows_sha256),
        UNIQUE (id, phap_nhan_id))""",
    _chi_ghi_them("giao_tiep.tep_tach_phap_nhan", "tep_tach_phap_nhan_bat_bien"),
    # --- biên nhận nghiệp vụ (PN, module, operation, key) — tách khỏi capture; actor = phiên có module
    """CREATE TABLE kho.bien_nhan_thao_tac (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        module text NOT NULL CHECK (module IN ('CRM','M1','M2','M5')),
        operation text NOT NULL CHECK (operation ~ '^[A-Z_0-9]{3,40}$'),
        client_key text NOT NULL CHECK (length(client_key) BETWEEN 1 AND 200),
        request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
        result_json jsonb NOT NULL,
        actor text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, module, operation, client_key),
        UNIQUE (phap_nhan_id, id))""",
    """CREATE OR REPLACE FUNCTION kho.bien_nhan_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'BIEN_NHAN_BAT_BIEN' USING ERRCODE = 'P0001';
            END IF;
            IF master.ktt_danh_tinh() IS NULL OR master.ktt_danh_tinh() IS DISTINCT FROM NEW.actor OR NOT master.ktt_duoc(NEW.phap_nhan_id, NEW.module) THEN
                RAISE EXCEPTION 'BIEN_NHAN_KHONG_CO_QUYEN: actor biên nhận phải là phiên hiện tại có module' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.bien_nhan_thao_tac FOR EACH ROW EXECUTE FUNCTION kho.bien_nhan_kiem()",
    # biên nhận M5 chỉ do consumer/hàm định nghĩa của chủ bảng tạo trong cùng giao dịch (không app INSERT/prefill/retag); CRM/M1 giữ hành vi cũ
    """CREATE OR REPLACE FUNCTION kho.bien_nhan_m5_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE m5 boolean := false;
        BEGIN
            IF TG_OP <> 'DELETE' THEN
                m5 := NEW.module = 'M5';
            END IF;
            IF TG_OP <> 'INSERT' THEN
                m5 := m5 OR OLD.module = 'M5';
            END IF;
            IF m5 AND NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'BIEN_NHAN_M5_CHI_CHU: biên nhận M5 chỉ do đường định nghĩa tạo, không ghi trực tiếp' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bien_nhan_m5_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.bien_nhan_thao_tac FOR EACH ROW EXECUTE FUNCTION kho.bien_nhan_m5_chi_chu()",
    # --- core: discriminator chủ sở hữu TRUNG TÍNH trên kho.chung_tu (không dùng DDL/helper M9 lịch sử). Backfill TRƯỚC guard: HOP_DONG_TEP → CRM,
    #     MỌI hàng cũ khác → M1 (kể cả PHIEU_KHO cũ); ID/giá trị cũ giữ nguyên. Hàng mới: DB suy chủ (PHIEU_KHO → M5, HOP_DONG_TEP → CRM, còn lại M1).
    "ALTER TABLE kho.chung_tu ADD COLUMN module_nghiep_vu text",
    "UPDATE kho.chung_tu SET module_nghiep_vu = CASE WHEN loai = 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END",
    "ALTER TABLE kho.chung_tu ALTER COLUMN module_nghiep_vu SET NOT NULL",
    "ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_module_common_check CHECK (module_nghiep_vu IN ('CRM','M1','M5'))",
    "ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_pn_id_module_common_uq UNIQUE (phap_nhan_id, id, module_nghiep_vu)",
    "ALTER TABLE kho.chung_tu_dong ADD CONSTRAINT chung_tu_dong_ct_id_stt_common_uq UNIQUE (chung_tu_id, id, stt)",
    # quantity-only cho M5: bỏ NOT NULL nhưng GIỮ DEFAULT 0 cho caller cũ; guard cha-con giữ nguyên invariant no/co NOT NULL cho dòng không phải M5
    "ALTER TABLE kho.chung_tu_dong ALTER COLUMN no_minor DROP NOT NULL",
    "ALTER TABLE kho.chung_tu_dong ALTER COLUMN co_minor DROP NOT NULL",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_chu_so_huu_common() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE mong text;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                mong := CASE NEW.loai WHEN 'PHIEU_KHO' THEN 'M5' WHEN 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END;
                IF NEW.module_nghiep_vu IS NULL THEN
                    NEW.module_nghiep_vu := mong;
                ELSIF NEW.module_nghiep_vu <> mong THEN
                    RAISE EXCEPTION 'CHU_SO_HUU_SAI: chứng từ % thuộc module %, không nhận module do caller khai', NEW.loai, mong USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.module_nghiep_vu IS DISTINCT FROM OLD.module_nghiep_vu
                  OR (NEW.loai IS DISTINCT FROM OLD.loai AND (OLD.module_nghiep_vu = 'M5' OR NEW.loai = 'PHIEU_KHO' OR OLD.loai = 'HOP_DONG_TEP'
                                                               OR NEW.loai = 'HOP_DONG_TEP')) THEN
                RAISE EXCEPTION 'CHU_SO_HUU_BAT_BIEN: không đổi module/loại quyết định chủ sở hữu' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.module_nghiep_vu = 'M5' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M5_CHI_CHU: chứng từ PHIEU_KHO M5 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.so_tien_minor IS NOT NULL OR NEW.tien_te IS NOT NULL OR NEW.chieu IS NOT NULL OR NEW.doi_tac_id IS NOT NULL THEN
                    RAISE EXCEPTION 'M5_CHI_SO_LUONG: phiếu kho M5 không mang tiền/tiền tệ/chiều/đối tác hạch toán' USING ERRCODE = 'P0001';
                END IF;
                IF TG_OP = 'INSERT' AND NEW.trang_thai <> 'DANG_XU_LY' THEN
                    RAISE EXCEPTION 'M5_KHONG_DUYET_JOURNAL: phiếu kho M5 vào core ở DANG_XU_LY, không DA_DUYET/V1' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_chu_so_huu_common BEFORE INSERT OR UPDATE ON kho.chung_tu FOR EACH ROW EXECUTE FUNCTION kho.chung_tu_chu_so_huu_common()",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_dong_kiem_common() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE m text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.chung_tu_id IS DISTINCT FROM OLD.chung_tu_id THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_DOI_CHA: không chuyển dòng sang chứng từ khác' USING ERRCODE = 'P0001';
            END IF;
            SELECT c.module_nghiep_vu INTO m FROM kho.chung_tu c WHERE c.id = NEW.chung_tu_id;
            IF m IS NULL THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_CHA_KHONG_THAY: không thấy chứng từ cha trong phạm vi' USING ERRCODE = 'P0001';
            END IF;
            IF m = 'M5' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M5_CHI_CHU: dòng PHIEU_KHO M5 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.no_minor IS NOT NULL OR NEW.co_minor IS NOT NULL OR NEW.don_gia_minor IS NOT NULL OR NEW.tien_truoc_thue_minor IS NOT NULL
                   OR NEW.thue_suat IS NOT NULL OR NEW.tien_thue_minor IS NOT NULL OR NEW.tai_khoan IS NOT NULL THEN
                    RAISE EXCEPTION 'M5_CHI_SO_LUONG: dòng phiếu kho M5 không mang Nợ/Có/đơn giá/thuế/tài khoản (NULL, không 0)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.no_minor IS NULL OR NEW.co_minor IS NULL THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_NO_CO_NULL: dòng chứng từ không phải M5 phải có no_minor/co_minor' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER chung_tu_dong_kiem_common BEFORE INSERT OR UPDATE ON kho.chung_tu_dong FOR EACH ROW EXECUTE FUNCTION kho.chung_tu_dong_kiem_common()",
    # registry lô: lô module M5 chỉ do consumer FILE_SOAT của chủ bảng ghi, đúng đường dẫn m5-xuat/<sha>.xlsx + stage; bất biến. CRM/M1 giữ hành vi cũ.
    """CREATE OR REPLACE FUNCTION kho.lo_xuat_m5_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE moi boolean := false; cu boolean := false;
        BEGIN
            IF TG_OP <> 'DELETE' THEN
                moi := coalesce(NEW.du_lieu->>'module', '') = 'M5';
            END IF;
            IF TG_OP <> 'INSERT' THEN
                cu := coalesce(OLD.du_lieu->>'module', '') = 'M5';
            END IF;
            IF NOT (moi OR cu) THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END IF;
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'LO_M5_BAT_BIEN: lô file soát M5 không sửa/xóa/đổi module' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'LO_M5_CHI_CHU: lô M5 chỉ do consumer FILE_SOAT ghi' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.loai <> 'FILE_SOAT' OR NEW.hash IS NULL OR NEW.duong_dan IS DISTINCT FROM 'm5-xuat/' || NEW.hash || '.xlsx'
               OR NEW.duong_dan !~ '^m5-xuat/[0-9a-f]{64}\\.xlsx$' OR NOT (NEW.du_lieu ? 'stage_id') OR NEW.du_lieu->>'muc_dich' IS DISTINCT FROM 'FILE_SOAT' THEN
                RAISE EXCEPTION 'LO_M5_SAI_MUC_DICH: lô M5 phải là FILE_SOAT, đường dẫn m5-xuat/<sha>.xlsx và gắn stage' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lo_xuat_m5_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.lo_xuat FOR EACH ROW EXECUTE FUNCTION kho.lo_xuat_m5_chi_chu()",
    # RLS core: thay policy app_web theo PN + chủ sở hữu do DB suy (hàng cũ giữ đúng phạm vi CRM/M1 như trước); policy vai trò cũ loại trừ M5
    # trừ khi phiên có quyền M5 hiện hành; dòng xét theo chứng từ cha (không chỉ header). Không OR giữ policy M1 cũ.
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            DROP POLICY IF EXISTS chung_tu_pham_vi_web ON kho.chung_tu;
            CREATE POLICY chung_tu_pham_vi_web ON kho.chung_tu TO app_web
                USING (master.ktt_duoc(phap_nhan_id, module_nghiep_vu)) WITH CHECK (master.ktt_duoc(phap_nhan_id, module_nghiep_vu));
            DROP POLICY IF EXISTS chung_tu_dong_pham_vi_web ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_pham_vi_web ON kho.chung_tu_dong TO app_web
                USING ((SELECT master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id))
                WITH CHECK ((SELECT master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            DROP POLICY IF EXISTS chung_tu_ung_dung_cu ON kho.chung_tu;
            CREATE POLICY chung_tu_ung_dung_cu ON kho.chung_tu TO app_ke_toan
                USING (module_nghiep_vu <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'))
                WITH CHECK (module_nghiep_vu <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS chung_tu_dong_ung_dung_cu ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_ung_dung_cu ON kho.chung_tu_dong TO app_ke_toan
                USING ((SELECT c.module_nghiep_vu <> 'M5' OR master.ktt_duoc(c.phap_nhan_id, 'M5') FROM kho.chung_tu c WHERE c.id = chung_tu_id))
                WITH CHECK ((SELECT c.module_nghiep_vu <> 'M5' OR master.ktt_duoc(c.phap_nhan_id, 'M5') FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            DROP POLICY IF EXISTS chung_tu_chi_doc ON kho.chung_tu;
            CREATE POLICY chung_tu_chi_doc ON kho.chung_tu FOR SELECT TO app_doc USING (module_nghiep_vu <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS chung_tu_dong_chi_doc ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_chi_doc ON kho.chung_tu_dong FOR SELECT TO app_doc
                USING ((SELECT c.module_nghiep_vu <> 'M5' OR master.ktt_duoc(c.phap_nhan_id, 'M5') FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
        -- registry lô/việc dùng chung: hàng M5 mới cũng bị loại khỏi policy USING true của vai trò cũ (hàng cũ giữ nguyên phạm vi)
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            DROP POLICY IF EXISTS lo_xuat_ung_dung_cu ON kho.lo_xuat;
            CREATE POLICY lo_xuat_ung_dung_cu ON kho.lo_xuat TO app_ke_toan
                USING (coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'))
                WITH CHECK (coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS viec_can_duyet_ung_dung_cu ON kho.viec_can_duyet;
            CREATE POLICY viec_can_duyet_ung_dung_cu ON kho.viec_can_duyet TO app_ke_toan
                USING (coalesce(module, 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'))
                WITH CHECK (coalesce(module, 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            DROP POLICY IF EXISTS lo_xuat_chi_doc ON kho.lo_xuat;
            CREATE POLICY lo_xuat_chi_doc ON kho.lo_xuat FOR SELECT TO app_doc
                USING (coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS viec_can_duyet_chi_doc ON kho.viec_can_duyet;
            CREATE POLICY viec_can_duyet_chi_doc ON kho.viec_can_duyet FOR SELECT TO app_doc
                USING (coalesce(module, 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            DROP POLICY IF EXISTS lo_xuat_cong_ai ON kho.lo_xuat;
            CREATE POLICY lo_xuat_cong_ai ON kho.lo_xuat FOR SELECT TO app_cong_ai
                USING (coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS viec_can_duyet_cong_ai ON kho.viec_can_duyet;
            CREATE POLICY viec_can_duyet_cong_ai ON kho.viec_can_duyet FOR SELECT TO app_cong_ai
                USING (coalesce(module, 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            DROP POLICY IF EXISTS chung_tu_cong_ai ON kho.chung_tu;
            CREATE POLICY chung_tu_cong_ai ON kho.chung_tu FOR SELECT TO app_cong_ai USING (module_nghiep_vu <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5'));
            DROP POLICY IF EXISTS chung_tu_dong_cong_ai ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_cong_ai ON kho.chung_tu_dong FOR SELECT TO app_cong_ai
                USING ((SELECT c.module_nghiep_vu <> 'M5' OR master.ktt_duoc(c.phap_nhan_id, 'M5') FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
    END $$""",
    # --- hàm integration (SECURITY DEFINER, search_path cố định): quyền nguồn TRƯỚC khóa/tra biên nhận/artifact
    # replay trả thêm kết quả cuối bất biến (SR02-1): stage/snapshot_moi/promote đã chốt cùng giao dịch lần đầu
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_tim_lan_nhan(p_instance text, p_ref text, p_sha text, p_key text)
        RETURNS TABLE (id uuid, capture_sha256 text, snapshot_id uuid, ket_qua jsonb, nhan_luc timestamptz, ket_qua_cuoi jsonb)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        BEGIN""" + _KIEM_NGUON.format(i="p_instance", r="p_ref", s="p_sha", a="'INTAKE'", p="NULL") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('CAPTURE|' || p_instance || '|' || p_key, 0));
            RETURN QUERY SELECT l.id, l.capture_sha256, l.snapshot_id, l.ket_qua, l.nhan_luc,
                    (SELECT jsonb_build_object('stage_id', k.stage_id, 'snapshot_moi', k.snapshot_moi, 'promote', k.promote)
                     FROM giao_tiep.ket_qua_cuoi_tiep_nhan k WHERE k.lan_tiep_nhan_id = l.id)
                FROM giao_tiep.lan_tiep_nhan_nguon l
                WHERE l.source_instance_id = p_instance AND l.khong_gian = 'CAPTURE' AND l.client_key = p_key;
        END $$""",
    # Consumer capture DUY NHẤT (thay hàm free-JSON cũ): chỉ nhận stage ID + expected H; mọi facts (H/envelope/roles/bundle/rows/kết quả) đọc từ stage
    # bất biến do máy chủ (chủ bảng) ghi; kiểm lại actor/quyền INTAKE hiện hành, khóa namespace, biên nhận cũ, đồng nhất bundle đã có.
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_tieu_thu_capture(p_stage uuid, p_h text)
        RETURNS TABLE (receipt_id uuid, snapshot_id uuid, moi boolean, snapshot_moi boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE
            ai text := master.ktt_danh_tinh(); s record; p jsonb; v_inst text; v_ref text; v_sha text; v_key text; cu record; snap uuid;
            moi_snap boolean := false; a jsonb; r jsonb; t uuid; tt record; prof jsonb; vai jsonb; thieu integer := 0; vr record;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage capture không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            IF ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '') THEN
                RAISE EXCEPTION 'STAGE_ACTOR_SAI: stage không thuộc danh tính phiên hiện tại' USING ERRCODE = 'P0001';
            END IF;
            v_inst := s.source_instance_id; v_ref := s.profile_ref; v_sha := s.profile_sha256; v_key := s.client_key; p := s.du_lieu;""" \
        + _KIEM_NGUON.format(i="v_inst", r="v_ref", s="v_sha", a="'INTAKE'", p="NULL") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('CAPTURE|' || v_inst || '|' || v_key, 0));
            SELECT l.id, l.capture_sha256, l.snapshot_id INTO cu FROM giao_tiep.lan_tiep_nhan_nguon l
                WHERE l.source_instance_id = v_inst AND l.khong_gian = 'CAPTURE' AND l.client_key = v_key;
            IF FOUND THEN
                IF cu.capture_sha256 IS DISTINCT FROM s.h THEN
                    RAISE EXCEPTION 'CAPTURE_KHAC_NOI_DUNG: khóa capture đã dùng cho nội dung/profile/scope/coverage/lỗi khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN QUERY SELECT cu.id, cu.snapshot_id, false, false;
                RETURN;
            END IF;
            -- stage tự nhất quán: envelope ↔ cột stage, artifacts envelope ↔ vai trò có mặt (hash/độ dài/media)
            IF p->'envelope'->>'contract' IS DISTINCT FROM 'm0-capture/v1' OR p->'envelope'->>'source_instance' IS DISTINCT FROM v_inst
               OR p->'envelope'->'source_profile'->>'reference_id' IS DISTINCT FROM v_ref OR p->'envelope'->'source_profile'->>'sha256' IS DISTINCT FROM v_sha
               OR p->'envelope'->'source_scope'->>'scope_ref' IS DISTINCT FROM p->>'scope_ref' OR p->'envelope'->>'coverage' IS DISTINCT FROM p->>'coverage'
               OR (SELECT coalesce(jsonb_agg(jsonb_build_object('role', f->>'role', 'raw_sha256', f->>'raw_sha256', 'byte_length', (f->>'byte_length')::bigint,
                                                                'media_type', f->>'media_type') ORDER BY f->>'role'), '[]'::jsonb)
                   FROM jsonb_array_elements(p->'roles') AS u(f) WHERE (f->>'co_mat')::boolean)
                  IS DISTINCT FROM
                  (SELECT coalesce(jsonb_agg(jsonb_build_object('role', e->>'role', 'raw_sha256', e->>'raw_sha256', 'byte_length', (e->>'byte_length')::bigint,
                                                                'media_type', e->>'media_type') ORDER BY e->>'role'), '[]'::jsonb)
                   FROM jsonb_array_elements(p->'envelope'->'artifacts') AS t(e)) THEN
                RAISE EXCEPTION 'STAGE_KHONG_NHAT_QUAN: envelope/vai trò của stage không khớp nhau' USING ERRCODE = 'P0001';
            END IF;
            SELECT np.payload INTO prof FROM master.nguon_profile np WHERE np.source_instance_id = v_inst AND np.profile_ref = v_ref AND np.profile_sha256 = v_sha;
            IF prof IS NULL THEN
                RAISE EXCEPTION 'NGUON_PROFILE_LA' USING ERRCODE = 'P0001';
            END IF;
            IF NOT (prof->'coverage_values') ? (p->>'coverage') OR NOT (prof->'coverage_values') ? (p->>'coverage_hieu_luc') THEN
                RAISE EXCEPTION 'NGUON_COVERAGE_LA: coverage ngoài profile' USING ERRCODE = 'P0001';
            END IF;
            -- mỗi vai trò khai báo đúng profile (media), không vai trò lạ; vai trò bắt buộc vắng phải ghi lý do vắng
            FOR a IN SELECT * FROM jsonb_array_elements(p->'roles') LOOP
                SELECT e INTO vai FROM jsonb_array_elements(prof->'artifact_roles') AS t(e) WHERE e->>'role' = a->>'role';
                IF vai IS NULL THEN
                    RAISE EXCEPTION 'NGUON_VAI_TRO_LA: %', a->>'role' USING ERRCODE = 'P0001';
                END IF;
                IF (a->>'co_mat')::boolean AND a->>'media_type' IS DISTINCT FROM vai->>'media_type' THEN
                    RAISE EXCEPTION 'NGUON_MEDIA_SAI: %', a->>'role' USING ERRCODE = 'P0001';
                END IF;
                IF NOT (a->>'co_mat')::boolean THEN
                    thieu := thieu + 1;
                END IF;
            END LOOP;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(prof->'artifact_roles') AS t(e) WHERE NOT EXISTS (
                           SELECT 1 FROM jsonb_array_elements(p->'roles') AS u(f) WHERE f->>'role' = e->>'role'))
               OR (SELECT count(*) FROM jsonb_array_elements(p->'roles') AS u(f)) <> (SELECT count(DISTINCT f->>'role') FROM jsonb_array_elements(p->'roles') AS u(f)) THEN
                RAISE EXCEPTION 'NGUON_VAI_TRO_THIEU_KHAI_BAO: mọi vai trò profile phải có mặt hoặc ghi vắng' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.id INTO snap FROM kho.anh_chup_nguon x WHERE x.source_instance_id = v_inst AND x.profile_ref = v_ref AND x.profile_sha256 = v_sha
                AND x.bundle_sha256 = p->>'bundle_sha256';
            IF snap IS NOT NULL THEN
                -- bundle đã có: vai trò đã lưu phải đúng y vai trò thực của stage (không gắn lại master/native cũ qua bundle SHA trùng)
                FOR vr IN SELECT v.vai_tro, v.co_mat, v.raw_sha256, v.byte_length, v.media_type FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = snap LOOP
                    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p->'roles') AS u(f) WHERE f->>'role' = vr.vai_tro AND (f->>'co_mat')::boolean = vr.co_mat
                                   AND (f->>'raw_sha256') IS NOT DISTINCT FROM vr.raw_sha256 AND (f->>'byte_length')::bigint IS NOT DISTINCT FROM vr.byte_length
                                   AND (f->>'media_type') IS NOT DISTINCT FROM CASE WHEN vr.co_mat THEN vr.media_type END) THEN
                        RAISE EXCEPTION 'BUNDLE_XUNG_DOT: bundle đã lưu khác vai trò thực của lần nhận' USING ERRCODE = 'P0001';
                    END IF;
                END LOOP;
                IF (SELECT count(*) FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = snap) <> jsonb_array_length(p->'roles') THEN
                    RAISE EXCEPTION 'BUNDLE_XUNG_DOT: số vai trò khác' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                moi_snap := true;
                INSERT INTO kho.anh_chup_nguon (source_instance_id, profile_ref, profile_sha256, bundle_sha256, state, so_dong, nguoi)
                VALUES (v_inst, v_ref, v_sha, p->>'bundle_sha256', CASE WHEN thieu > 0 THEN 'THIEU_VAI_TRO' ELSE 'DU_VAI_TRO' END,
                        jsonb_array_length(coalesce(p->'rows', '[]'::jsonb)), ai)
                RETURNING id INTO snap;
                FOR a IN SELECT * FROM jsonb_array_elements(p->'roles') LOOP
                    t := NULL;
                    IF (a->>'co_mat')::boolean THEN
                        INSERT INTO giao_tiep.tep_tiep_nhan (source_instance_id, object_key, raw_sha256, byte_length, media_type, nguoi)
                        VALUES (v_inst, 'm0-raw/' || (a->>'raw_sha256'), a->>'raw_sha256', (a->>'byte_length')::bigint, a->>'media_type', ai)
                        ON CONFLICT (source_instance_id, raw_sha256) DO NOTHING RETURNING id INTO t;
                        IF t IS NULL THEN
                            SELECT x.id, x.byte_length, x.media_type INTO tt FROM giao_tiep.tep_tiep_nhan x
                                WHERE x.source_instance_id = v_inst AND x.raw_sha256 = a->>'raw_sha256';
                            IF tt.byte_length IS DISTINCT FROM (a->>'byte_length')::bigint OR tt.media_type IS DISTINCT FROM a->>'media_type' THEN
                                RAISE EXCEPTION 'RAW_METADATA_XUNG_DOT: cùng SHA khác độ dài/media' USING ERRCODE = 'P0001';
                            END IF;
                            t := tt.id;
                        END IF;
                    END IF;
                    INSERT INTO kho.anh_chup_nguon_vai_tro (snapshot_id, source_instance_id, vai_tro, co_mat, tep_tiep_nhan_id, raw_sha256, byte_length, media_type, ly_do_vang)
                    VALUES (snap, v_inst, a->>'role', (a->>'co_mat')::boolean, t,
                            CASE WHEN (a->>'co_mat')::boolean THEN a->>'raw_sha256' END,
                            CASE WHEN (a->>'co_mat')::boolean THEN (a->>'byte_length')::bigint END,
                            CASE WHEN (a->>'co_mat')::boolean THEN a->>'media_type' END, a->>'ly_do_vang');
                END LOOP;
                FOR r IN SELECT * FROM jsonb_array_elements(coalesce(p->'rows', '[]'::jsonb)) LOOP
                    INSERT INTO kho.ban_ghi_nguon (snapshot_id, source_instance_id, vai_tro, section, locator, thu_tu, source_key, row_raw, row_raw_sha256,
                        quantity_json_kind, quantity_text, validation_state, error_codes)
                    VALUES (snap, v_inst, r->>'vai_tro', r->>'section', r->>'locator', (r->>'thu_tu')::integer, r->>'source_key', r->'row_raw',
                        r->>'row_raw_sha256', r->>'quantity_json_kind', r->>'quantity_text', r->>'validation_state',
                        coalesce(ARRAY(SELECT jsonb_array_elements_text(r->'error_codes')), '{}'));
                END LOOP;
            END IF;
            INSERT INTO giao_tiep.lan_tiep_nhan_nguon (id, source_instance_id, client_key, capture_contract, capture_sha256, profile_ref, profile_sha256,
                scope_ref, source_scope, coverage, coverage_hieu_luc, reported_errors, snapshot_id, envelope, ket_qua, stage_id, actor_id, actor)
            VALUES ((p->>'receipt_id')::uuid, v_inst, v_key, 'm0-capture/v1', s.h, v_ref, v_sha, p->>'scope_ref', p->'envelope'->'source_scope',
                p->>'coverage', p->>'coverage_hieu_luc', coalesce(ARRAY(SELECT jsonb_array_elements_text(p->'envelope'->'reported_errors')), '{}'), snap,
                p->'envelope', p->'ket_qua', s.id, s.actor_id, ai);
            RETURN QUERY SELECT (p->>'receipt_id')::uuid, snap, true, moi_snap;
        END $$""",
    # mapping hiện hành cho người có INTAKE/SOURCE_MAP của đúng instance/profile (không cần quyền PN): PN do mapping quyết, không do client.
    # I-S01 (repair03): nhánh SOURCE_MAP dùng CÙNG predicate nguồn hiện hành (người dùng HOAT_DONG + ID phiên + instance HOAT_DONG) qua
    # master.ktt_nguon_duoc với ĐÚNG PN đích của từng mapping; instance DUNG / năng lực bị thu hồi → không qua. Không cần cấp INTAKE/READ_SOURCE.
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_anh_xa_hien_hanh(p_instance text, p_ref text, p_sha text, p_kind text, p_key text)
        RETURNS TABLE (id uuid, reference_id text, revision integer, phap_nhan_id uuid, phap_nhan_ma text)
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, giao_tiep, pg_temp AS $$
        DECLARE v_intake boolean;
        BEGIN
            IF master.ktt_danh_tinh() IS NULL THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: cần INTAKE hoặc SOURCE_MAP của đúng instance/profile' USING ERRCODE = 'P0001';
            END IF;
            v_intake := master.ktt_nguon_duoc(p_instance, p_ref, p_sha, 'INTAKE', NULL);
            IF NOT v_intake AND NOT EXISTS (SELECT 1 FROM master.nang_luc_nguon c WHERE c.source_instance_id = p_instance AND c.profile_ref = p_ref
                                               AND c.profile_sha256 = p_sha AND c.hanh_dong = 'SOURCE_MAP'
                                               AND master.ktt_nguon_duoc(p_instance, p_ref, p_sha, 'SOURCE_MAP', c.target_phap_nhan_id)) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: cần INTAKE hoặc SOURCE_MAP của đúng instance/profile' USING ERRCODE = 'P0001';
            END IF;
            RETURN QUERY SELECT m.id, m.reference_id, m.revision, m.phap_nhan_id, pn.ma FROM master.anh_xa_nguon m JOIN master.phap_nhan pn ON pn.id = m.phap_nhan_id
                WHERE m.source_instance_id = p_instance AND m.profile_ref = p_ref AND m.profile_sha256 = p_sha AND m.subject_kind = p_kind
                  AND m.subject_key = p_key AND m.state = 'DA_DUYET' AND m.valid_from <= now() AND (m.valid_to IS NULL OR m.valid_to > now())
                  AND (v_intake OR master.ktt_nguon_duoc(p_instance, p_ref, p_sha, 'SOURCE_MAP', m.phap_nhan_id));
        END $$""",
    # đọc raw/rows chỉ với READ_SOURCE hiện hành của đúng instance/profile (không qua quyền PN/M5)
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_doc_lan_nhan(p_receipt uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE l record;
        BEGIN
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = p_receipt;
            IF NOT FOUND OR master.ktt_danh_tinh() IS NULL
               OR NOT master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'READ_SOURCE', NULL) THEN
                RETURN NULL;
            END IF;
            RETURN jsonb_build_object(
                'id', l.id, 'source_instance_id', l.source_instance_id, 'client_key', l.client_key, 'capture_sha256', l.capture_sha256,
                'profile_ref', l.profile_ref, 'profile_sha256', l.profile_sha256, 'scope_ref', l.scope_ref, 'source_scope', l.source_scope,
                'coverage', l.coverage, 'coverage_hieu_luc', l.coverage_hieu_luc, 'reported_errors', to_jsonb(l.reported_errors), 'snapshot_id', l.snapshot_id,
                'envelope', l.envelope,
                'ket_qua', l.ket_qua, 'actor', l.actor, 'nhan_luc', l.nhan_luc,
                'vai_tro', (SELECT coalesce(jsonb_agg(jsonb_build_object('vai_tro', v.vai_tro, 'co_mat', v.co_mat, 'tep_id', v.tep_tiep_nhan_id,
                                    'raw_sha256', v.raw_sha256, 'byte_length', v.byte_length, 'media_type', v.media_type, 'ly_do_vang', v.ly_do_vang)
                                    ORDER BY v.vai_tro), '[]'::jsonb) FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = l.snapshot_id),
                'dong', (SELECT coalesce(jsonb_agg(jsonb_build_object('section', b.section, 'locator', b.locator, 'thu_tu', b.thu_tu, 'source_key', b.source_key,
                                    'row_raw', b.row_raw, 'quantity_json_kind', b.quantity_json_kind, 'quantity_text', b.quantity_text,
                                    'validation_state', b.validation_state, 'error_codes', to_jsonb(b.error_codes))
                                    ORDER BY b.vai_tro, b.section, b.thu_tu), '[]'::jsonb) FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = l.snapshot_id));
        END $$""",
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_danh_sach_lan_nhan() RETURNS SETOF jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        SELECT jsonb_build_object('id', l.id, 'source_instance_id', l.source_instance_id, 'client_key', l.client_key, 'capture_sha256', l.capture_sha256,
                                  'scope_ref', l.scope_ref, 'coverage', l.coverage, 'coverage_hieu_luc', l.coverage_hieu_luc,
                                  'reported_errors', to_jsonb(l.reported_errors), 'snapshot_id', l.snapshot_id,
                                  'ket_qua', l.ket_qua, 'actor', l.actor, 'nhan_luc', l.nhan_luc,
                                  'doc_raw', master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'READ_SOURCE', NULL))
        FROM giao_tiep.lan_tiep_nhan_nguon l
        WHERE master.ktt_danh_tinh() IS NOT NULL
          AND (master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'READ_SOURCE', NULL)
               OR master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'INTAKE', NULL))
        ORDER BY l.nhan_luc DESC, l.id
        $$""",
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_doc_tep(p_receipt uuid, p_vai_tro text)
        RETURNS TABLE (object_key text, raw_sha256 text, byte_length bigint, media_type text)
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE l record;
        BEGIN
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = p_receipt;
            IF NOT FOUND OR master.ktt_danh_tinh() IS NULL
               OR NOT master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'READ_SOURCE', NULL) THEN
                RETURN;
            END IF;
            RETURN QUERY SELECT t.object_key, t.raw_sha256, t.byte_length, t.media_type FROM kho.anh_chup_nguon_vai_tro v
                JOIN giao_tiep.tep_tiep_nhan t ON t.id = v.tep_tiep_nhan_id WHERE v.snapshot_id = l.snapshot_id AND v.vai_tro = p_vai_tro AND v.co_mat;
        END $$""",
    """REVOKE EXECUTE ON FUNCTION master.ktt_nguon_duoc(text, text, text, text, uuid), master.ktt_nguon_co_nang_luc(text, text, text),
        master.anh_xa_nguon_noi_bo(text, text, text, text, text, timestamptz),
        giao_tiep.nguon_tim_lan_nhan(text, text, text, text), giao_tiep.nguon_tieu_thu_capture(uuid, text),
        giao_tiep.nguon_anh_xa_hien_hanh(text, text, text, text, text), giao_tiep.nguon_doc_lan_nhan(uuid), giao_tiep.nguon_danh_sach_lan_nhan(),
        giao_tiep.nguon_doc_tep(uuid, text) FROM PUBLIC""",
    # --- RLS + quyền: chỉ trên object COMMON thực có; raw/capture/rows/stage/master catalog/facts không cấp trực tiếp cho app_web
    "ALTER TABLE master.nguon_instance ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.nguon_profile ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.nguon_pham_vi ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.nguon_master_noi_dung ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.nguon_su_kien_do_luong ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.nang_luc_nguon ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.anh_xa_nguon ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE giao_tiep.stage_tin_cay ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE giao_tiep.tep_tach_phap_nhan ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.bien_nhan_thao_tac ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE giao_tiep.tep_tiep_nhan ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE giao_tiep.lan_tiep_nhan_nguon ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE giao_tiep.ket_qua_cuoi_tiep_nhan ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.anh_chup_nguon ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.anh_chup_nguon_vai_tro ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.ban_ghi_nguon ENABLE ROW LEVEL SECURITY",
    # S08: ACL mặc định kế thừa từ prefix (app_ke_toan/app_cong_ai/app_doc trong master/kho) bị thu hồi trên CHÍNH object mới; không đổi quyền object cũ
    """DO $$
    DECLARE r text; t text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_ke_toan','app_cong_ai','app_doc','app_web'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                FOREACH t IN ARRAY ARRAY['master.nguon_instance','master.nguon_profile','master.nguon_pham_vi','master.nang_luc_nguon','master.nguon_master_noi_dung',
                                         'master.nguon_su_kien_do_luong','master.anh_xa_nguon','giao_tiep.stage_tin_cay','giao_tiep.tep_tiep_nhan',
                                         'giao_tiep.lan_tiep_nhan_nguon','kho.anh_chup_nguon','kho.anh_chup_nguon_vai_tro','kho.ban_ghi_nguon',
                                         'giao_tiep.tep_tach_phap_nhan','kho.bien_nhan_thao_tac','giao_tiep.ket_qua_cuoi_tiep_nhan'] LOOP
                    EXECUTE format('REVOKE ALL ON %s FROM %I', t, r);
                END LOOP;
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA giao_tiep TO app_web;
            -- metadata nguồn: chỉ phiên có năng lực nguồn hiện hành trên đúng instance/profile; master catalog/facts đo lường: chỉ máy chủ
            GRANT SELECT ON master.nguon_instance, master.nguon_profile, master.nguon_pham_vi TO app_web;
            DROP POLICY IF EXISTS nguon_instance_theo_nang_luc ON master.nguon_instance;
            CREATE POLICY nguon_instance_theo_nang_luc ON master.nguon_instance FOR SELECT TO app_web
                USING (master.ktt_nguon_co_nang_luc(source_instance_id, NULL, NULL));
            DROP POLICY IF EXISTS nguon_profile_theo_nang_luc ON master.nguon_profile;
            CREATE POLICY nguon_profile_theo_nang_luc ON master.nguon_profile FOR SELECT TO app_web
                USING (master.ktt_nguon_co_nang_luc(source_instance_id, profile_ref, profile_sha256));
            DROP POLICY IF EXISTS nguon_pham_vi_theo_nang_luc ON master.nguon_pham_vi;
            CREATE POLICY nguon_pham_vi_theo_nang_luc ON master.nguon_pham_vi FOR SELECT TO app_web
                USING (master.ktt_nguon_co_nang_luc(source_instance_id, profile_ref, profile_sha256));
            GRANT SELECT ON master.nang_luc_nguon TO app_web;
            DROP POLICY IF EXISTS nang_luc_nguon_cua_phien ON master.nang_luc_nguon;
            CREATE POLICY nang_luc_nguon_cua_phien ON master.nang_luc_nguon FOR SELECT TO app_web
                USING (nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '') AND master.ktt_danh_tinh() IS NOT NULL);
            -- mapping: app chỉ ĐỌC (theo M5 của PN hoặc SOURCE_MAP đúng PN); ghi chỉ qua kho.m5_anh_xa_v4 (S07)
            GRANT SELECT ON master.anh_xa_nguon TO app_web;
            DROP POLICY IF EXISTS anh_xa_nguon_pham_vi_web ON master.anh_xa_nguon;
            CREATE POLICY anh_xa_nguon_pham_vi_web ON master.anh_xa_nguon FOR SELECT TO app_web
                USING (master.ktt_duoc(phap_nhan_id, 'M5') OR master.ktt_nguon_duoc(source_instance_id, profile_ref, profile_sha256, 'SOURCE_MAP', phap_nhan_id));
            GRANT SELECT ON giao_tiep.tep_tach_phap_nhan TO app_web;
            DROP POLICY IF EXISTS tep_tach_phap_nhan_pham_vi_web ON giao_tiep.tep_tach_phap_nhan;
            CREATE POLICY tep_tach_phap_nhan_pham_vi_web ON giao_tiep.tep_tach_phap_nhan FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, module));
            -- biên nhận: CRM/M1/M2 giữ INSERT của app như trước; M5 bị trigger chủ-bảng chặn (BIEN_NHAN_M5_CHI_CHU)
            GRANT SELECT, INSERT ON kho.bien_nhan_thao_tac TO app_web;
            DROP POLICY IF EXISTS bien_nhan_thao_tac_pham_vi_web ON kho.bien_nhan_thao_tac;
            CREATE POLICY bien_nhan_thao_tac_pham_vi_web ON kho.bien_nhan_thao_tac TO app_web
                USING (master.ktt_duoc(phap_nhan_id, module)) WITH CHECK (master.ktt_duoc(phap_nhan_id, module));
            GRANT EXECUTE ON FUNCTION master.ktt_nguon_duoc(text, text, text, text, uuid), master.ktt_nguon_co_nang_luc(text, text, text),
                giao_tiep.nguon_tim_lan_nhan(text, text, text, text), giao_tiep.nguon_tieu_thu_capture(uuid, text),
                giao_tiep.nguon_anh_xa_hien_hanh(text, text, text, text, text), giao_tiep.nguon_doc_lan_nhan(uuid),
                giao_tiep.nguon_danh_sach_lan_nhan(), giao_tiep.nguon_doc_tep(uuid, text) TO app_web;
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0014 M5 (binding M5 §2–§3, contract §5): năm bảng typed phiếu kho — danh tính / phiên bản nội dung / quan sát / dòng danh tính / dòng phiên bản.
#   Chỉ hàm định nghĩa ghi (PN từ mapping đã duyệt, quyền nguồn của phiên, khóa danh tính); con trỏ latest/accepted/eligible có FK cùng PN/phiếu
#   và trigger bất biến; review V8 (CFO + M5) với expected pointers; kỳ khóa chặn nghiệp vụ, không chặn capture. Không journal/valuation/L11.
# ---------------------------------------------------------------------------
# chấp nhận nguồn (accepted) bị chặn khi quan sát có các lý do này; nguồn Đã đảo VẪN chấp nhận được (accepted = B) nhưng eligible luôn NULL
_M5_CHAN_CHAP_NHAN = ("REAPPEARANCE_HOLD", "KHO_RECEIPT_CONFLICT", "HISTORY_UNAVAILABLE", "HISTORY_UNBOUND", "HISTORY_MISMATCH", "KHO_SOURCE_PARTIAL",
                      "KHO_CONTEXT_UNRESOLVED", "KHO_CONTEXT_SCOPE_MISMATCH", "KHO_CONTEXT_PROOF_MISMATCH")
_M5_CHAN_SQL = "ARRAY[" + ",".join(f"'{c}'" for c in _M5_CHAN_CHAP_NHAN) + "]"

M0014_M5 = (
    "SET LOCAL check_function_bodies = off",
    """CREATE TABLE kho.phieu_kho_danh_tinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        so_phieu_raw text NOT NULL,
        so_phieu_key text NOT NULL CHECK (length(so_phieu_key) BETWEEN 1 AND 200),
        ma_kho text NOT NULL,
        mapping_revision_id uuid NOT NULL,
        latest_observation_id uuid,
        accepted_source_observation_id uuid,
        eligible_content_id uuid,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        tao_boi text NOT NULL,
        FOREIGN KEY (mapping_revision_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (source_instance_id, so_phieu_key),
        UNIQUE (phap_nhan_id, id))""",
    """CREATE TABLE kho.phieu_kho_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        phieu_id uuid NOT NULL,
        version integer NOT NULL CHECK (version >= 1),
        semantic_contract text NOT NULL CHECK (semantic_contract = 'kho10-content/v1'),
        semantic_sha256 text NOT NULL CHECK (semantic_sha256 ~ '^[0-9a-f]{64}$'),
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        mapping_revision_id uuid NOT NULL,
        first_snapshot_id uuid NOT NULL,
        header_row_id uuid NOT NULL,
        native_header jsonb NOT NULL,
        loai_phieu_raw text NOT NULL,
        trang_thai_raw text NOT NULL,
        trang_thai_nguon text NOT NULL CHECK (trang_thai_nguon IN ('NHAP','DA_DUYET','DA_DAO','CHUA_MAP')),
        ngay_chung_tu date NOT NULL,
        ma_kho text NOT NULL,
        ma_doi_tac text,
        nguoi_duyet_nguon text,
        thoi_diem_duyet_nguon text,
        master_raw_sha256 text CHECK (master_raw_sha256 ~ '^[0-9a-f]{64}$'),
        master_reference_id text,
        related_master_facts jsonb NOT NULL,
        khoa_nguon_chieu text NOT NULL CHECK (khoa_nguon_chieu ~ '^KHO10_PHIEU:v1:[0-9a-f]{64}$'),
        chung_tu_id uuid NOT NULL UNIQUE,
        chung_tu_module text NOT NULL DEFAULT 'M5' CHECK (chung_tu_module = 'M5'),
        first_known_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_danh_tinh (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, chung_tu_id, chung_tu_module) REFERENCES kho.chung_tu (phap_nhan_id, id, module_nghiep_vu),
        UNIQUE (phap_nhan_id, phieu_id, id, chung_tu_id),
        FOREIGN KEY (header_row_id, first_snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        FOREIGN KEY (mapping_revision_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (phieu_id, version),
        UNIQUE (phieu_id, semantic_sha256),
        UNIQUE (khoa_nguon_chieu),
        UNIQUE (phap_nhan_id, phieu_id, id),
        UNIQUE (phap_nhan_id, phieu_id, id, first_snapshot_id))""",
    """CREATE TABLE kho.phieu_kho_dong_danh_tinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        phieu_id uuid NOT NULL,
        id_dong_nguon text NOT NULL CHECK (length(id_dong_nguon) BETWEEN 1 AND 200),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_danh_tinh (phap_nhan_id, id),
        UNIQUE (phieu_id, id_dong_nguon),
        UNIQUE (id, phap_nhan_id, phieu_id))""",
    """CREATE TABLE kho.phieu_kho_dong_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        phieu_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        dong_id uuid NOT NULL,
        snapshot_id uuid NOT NULL,
        source_row_id uuid NOT NULL,
        stt integer NOT NULL CHECK (stt >= 1),
        source_ordinal integer NOT NULL CHECK (source_ordinal >= 0),
        ma_hang_raw text,
        native_values jsonb NOT NULL,
        quantity_json_kind text NOT NULL CHECK (quantity_json_kind IN ('STRING','NUMBER','NULL','INVALID')),
        so_luong_raw text,
        so_luong numeric(38,12),
        precision_state text NOT NULL CHECK (precision_state IN ('EXACT_SYNTHETIC_DEMO','UNPROVEN','UNKNOWN','OUT_OF_DOMAIN')),
        dvt_raw text,
        unit_definition_ref text,
        chung_tu_id uuid NOT NULL,
        chung_tu_dong_id uuid NOT NULL UNIQUE,
        FOREIGN KEY (phap_nhan_id, phieu_id, phien_ban_id, snapshot_id) REFERENCES kho.phieu_kho_phien_ban (phap_nhan_id, phieu_id, id, first_snapshot_id),
        FOREIGN KEY (phap_nhan_id, phieu_id, phien_ban_id, chung_tu_id) REFERENCES kho.phieu_kho_phien_ban (phap_nhan_id, phieu_id, id, chung_tu_id),
        FOREIGN KEY (chung_tu_id, chung_tu_dong_id, stt) REFERENCES kho.chung_tu_dong (chung_tu_id, id, stt),
        FOREIGN KEY (dong_id, phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_dong_danh_tinh (id, phap_nhan_id, phieu_id),
        FOREIGN KEY (source_row_id, snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        CHECK (so_luong IS NULL OR (precision_state = 'EXACT_SYNTHETIC_DEMO' AND quantity_json_kind = 'STRING' AND so_luong = so_luong_raw::numeric)),
        CHECK (precision_state <> 'EXACT_SYNTHETIC_DEMO' OR so_luong IS NOT NULL),
        UNIQUE (phien_ban_id, dong_id),
        UNIQUE (phien_ban_id, stt))""",
    """CREATE TABLE kho.phieu_kho_quan_sat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        phieu_id uuid NOT NULL,
        content_id uuid NOT NULL,
        lan_tiep_nhan_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        snapshot_id uuid NOT NULL,
        observation_key text NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu >= 1),
        predecessor_observation_id uuid,
        trang_thai_nguon text NOT NULL CHECK (trang_thai_nguon IN ('NHAP','DA_DUYET','DA_DAO','CHUA_MAP')),
        request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
        phan_loai text[] NOT NULL,
        history_state text NOT NULL CHECK (history_state IN ('KNOWN','UNKNOWN','MISSING')),
        can_xem_xet boolean NOT NULL,
        mapping_revision_id uuid NOT NULL,
        scope_ref text NOT NULL,
        known_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, phieu_id, content_id) REFERENCES kho.phieu_kho_phien_ban (phap_nhan_id, phieu_id, id),
        FOREIGN KEY (lan_tiep_nhan_id, source_instance_id, snapshot_id) REFERENCES giao_tiep.lan_tiep_nhan_nguon (id, source_instance_id, snapshot_id),
        FOREIGN KEY (phap_nhan_id, phieu_id, predecessor_observation_id) REFERENCES kho.phieu_kho_quan_sat (phap_nhan_id, phieu_id, id),
        FOREIGN KEY (mapping_revision_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (phap_nhan_id, phieu_id, lan_tiep_nhan_id, observation_key),
        UNIQUE (lan_tiep_nhan_id, observation_key),
        UNIQUE (phieu_id, thu_tu),
        UNIQUE (phap_nhan_id, phieu_id, id))""",
    """ALTER TABLE kho.phieu_kho_danh_tinh
        ADD CONSTRAINT phieu_kho_latest_cung_phieu FOREIGN KEY (phap_nhan_id, id, latest_observation_id)
            REFERENCES kho.phieu_kho_quan_sat (phap_nhan_id, phieu_id, id) DEFERRABLE INITIALLY DEFERRED,
        ADD CONSTRAINT phieu_kho_accepted_cung_phieu FOREIGN KEY (phap_nhan_id, id, accepted_source_observation_id)
            REFERENCES kho.phieu_kho_quan_sat (phap_nhan_id, phieu_id, id) DEFERRABLE INITIALLY DEFERRED,
        ADD CONSTRAINT phieu_kho_eligible_cung_phieu FOREIGN KEY (phap_nhan_id, id, eligible_content_id)
            REFERENCES kho.phieu_kho_phien_ban (phap_nhan_id, phieu_id, id) DEFERRABLE INITIALLY DEFERRED""",
    _chi_ghi_them("kho.phieu_kho_phien_ban", "phieu_kho_phien_ban_bat_bien"),
    _chi_ghi_them("kho.phieu_kho_dong_danh_tinh", "phieu_kho_dong_danh_tinh_bat_bien"),
    _chi_ghi_them("kho.phieu_kho_dong_phien_ban", "phieu_kho_dong_phien_ban_bat_bien"),
    _chi_ghi_them("kho.phieu_kho_quan_sat", "phieu_kho_quan_sat_bat_bien"),
    # I-M05 (repair03): accepted (nguồn) ≠ eligible (số lượng). Quan sát đã chấp nhận chỉ cho eligible khi graph tin cậy đã đóng chứng minh đủ:
    # nguồn Đã duyệt + lịch sử KNOWN + phân loại chỉ mang mã thông tin (không HOLD đo lường/UOM/precision/continuity/context/partial/đảo) +
    # capture không PARTIAL (claim = hiệu lực) + master đã pin + mọi dòng nguồn snapshot HOP_LE + ≥1 dòng và MỌI dòng content là STRING exact
    # đã chuẩn hóa có đơn vị định nghĩa. Facts đọc từ bảng typed/capture bất biến, không boolean của caller. Không phải L11/proof tiền.
    """CREATE OR REPLACE FUNCTION kho.m5_quan_sat_du_dieu_kien(p_obs uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        SELECT coalesce((
            SELECT o.trang_thai_nguon = 'DA_DUYET' AND o.history_state = 'KNOWN'
               AND o.phan_loai <@ ARRAY['FIRST_OBSERVATION_CANDIDATE','REPLAY','SAME_CONTENT_FRESH_OBSERVATION']::text[]
               AND l.coverage_hieu_luc = l.coverage AND l.coverage_hieu_luc <> 'PARTIAL'
               AND v.master_raw_sha256 IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = o.snapshot_id AND b.validation_state <> 'HOP_LE')
               AND EXISTS (SELECT 1 FROM kho.phieu_kho_dong_phien_ban lw WHERE lw.phien_ban_id = v.id)
               AND NOT EXISTS (SELECT 1 FROM kho.phieu_kho_dong_phien_ban lw WHERE lw.phien_ban_id = v.id
                               AND NOT (lw.precision_state = 'EXACT_SYNTHETIC_DEMO' AND lw.quantity_json_kind = 'STRING'
                                        AND lw.so_luong IS NOT NULL AND lw.so_luong_raw IS NOT NULL AND lw.unit_definition_ref IS NOT NULL))
            FROM kho.phieu_kho_quan_sat o
            JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id AND v.phieu_id = o.phieu_id
            JOIN giao_tiep.lan_tiep_nhan_nguon l ON l.id = o.lan_tiep_nhan_id
            WHERE o.id = p_obs), false)
        $$""",
    # con trỏ: danh tính/PN/khóa nguồn bất biến; latest chỉ tiến; accepted chỉ tới quan sát đã có; eligible chỉ là content của accepted
    # DA_DUYET VÀ quan sát accepted qua cổng số lượng m5_quan_sat_du_dieu_kien (đóng cả đường ghi trực tiếp của chủ bảng)
    """CREATE OR REPLACE FUNCTION kho.phieu_kho_con_tro_kiem() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE cu integer; moi integer; acc record;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'PHIEU_KHO_BAT_BIEN: không xóa danh tính phiếu' USING ERRCODE = 'P0001';
            END IF;
            IF (NEW.id, NEW.phap_nhan_id, NEW.source_instance_id, NEW.so_phieu_raw, NEW.so_phieu_key, NEW.ma_kho, NEW.mapping_revision_id, NEW.tao_luc, NEW.tao_boi)
               IS DISTINCT FROM (OLD.id, OLD.phap_nhan_id, OLD.source_instance_id, OLD.so_phieu_raw, OLD.so_phieu_key, OLD.ma_kho, OLD.mapping_revision_id,
                                 OLD.tao_luc, OLD.tao_boi) THEN
                RAISE EXCEPTION 'PHIEU_KHO_BAT_BIEN: không đổi PN/khóa nguồn/mapping của danh tính đã promote' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.latest_observation_id IS DISTINCT FROM OLD.latest_observation_id THEN
                SELECT thu_tu INTO cu FROM kho.phieu_kho_quan_sat WHERE id = OLD.latest_observation_id;
                SELECT thu_tu INTO moi FROM kho.phieu_kho_quan_sat WHERE id = NEW.latest_observation_id AND phieu_id = NEW.id;
                IF moi IS NULL OR (cu IS NOT NULL AND moi <= cu) THEN
                    RAISE EXCEPTION 'CON_TRO_LATEST_SAI: latest chỉ tiến theo thứ tự nhận' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.accepted_source_observation_id IS NOT NULL THEN
                SELECT o.trang_thai_nguon, o.content_id INTO acc FROM kho.phieu_kho_quan_sat o
                    WHERE o.id = NEW.accepted_source_observation_id AND o.phieu_id = NEW.id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'CON_TRO_ACCEPTED_SAI' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.eligible_content_id IS NOT NULL AND (acc.trang_thai_nguon <> 'DA_DUYET' OR acc.content_id IS DISTINCT FROM NEW.eligible_content_id
                                                            OR NOT kho.m5_quan_sat_du_dieu_kien(NEW.accepted_source_observation_id)) THEN
                    RAISE EXCEPTION 'CON_TRO_ELIGIBLE_SAI: eligible chỉ là nội dung của nguồn đã chấp nhận Đã duyệt và đủ căn cứ số lượng' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.eligible_content_id IS NOT NULL THEN
                RAISE EXCEPTION 'CON_TRO_ELIGIBLE_SAI: chưa có nguồn được chấp nhận' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER phieu_kho_con_tro_kiem BEFORE UPDATE OR DELETE ON kho.phieu_kho_danh_tinh FOR EACH ROW EXECUTE FUNCTION kho.phieu_kho_con_tro_kiem()",
    # --- khóa danh tính + đọc lịch sử repository (dưới khóa) cho người nhận nguồn, TRƯỚC khi ghi stage: PN chỉ từ mapping hiện hành đúng
    #     instance/profile/MaKho. Thứ tự khóa chung: (namespace capture) → hàng mapping FOR SHARE → advisory logic phiếu → hàng danh tính FOR UPDATE.
    """CREATE OR REPLACE FUNCTION kho.m5_khoa_phieu(p_instance text, p_ref text, p_sha text, p_scope_ref text, p_so_phieu text, p_ma_kho text, p_mapping uuid)
        RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); l record; m record; d record; acc record; sc text; pr text;
        BEGIN
            IF ai IS NULL OR NOT master.ktt_nguon_duoc(p_instance, p_ref, p_sha, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: promote cần INTAKE hiện hành của phiên trên đúng instance/profile' USING ERRCODE = 'P0001';
            END IF;
            SELECT p_instance AS source_instance_id, p_ref AS profile_ref, p_sha AS profile_sha256, p_scope_ref AS scope_ref INTO l;
            SELECT * INTO m FROM master.anh_xa_nguon x WHERE x.id = p_mapping AND x.source_instance_id = l.source_instance_id AND x.profile_ref = l.profile_ref
                AND x.profile_sha256 = l.profile_sha256 AND x.subject_kind = 'WAREHOUSE' AND x.subject_key = p_ma_kho AND x.state = 'DA_DUYET'
                AND x.valid_from <= now() AND (x.valid_to IS NULL OR x.valid_to > now()) FOR SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: mapping hiện hành đã đổi so với lúc đọc' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || p_so_phieu, 0));
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.source_instance_id = l.source_instance_id AND x.so_phieu_key = p_so_phieu FOR UPDATE;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('phieu_id', NULL, 'phap_nhan_id', m.phap_nhan_id, 'hold', NULL, 'latest_observation_id', NULL,
                    'summary', jsonb_build_object('summary_kind', 'EXPLICIT_EMPTY', 'authority_ref', 'urn:ktt:m5:repository',
                        'logical_source_identity', jsonb_build_object('source_instance', l.source_instance_id, 'SoPhieu', p_so_phieu),
                        'scope_ref', l.scope_ref, 'profile_ref', l.profile_ref, 'receipts_seen', '[]'::jsonb, 'seen_content_references', '[]'::jsonb,
                        'seen_content_digests', '[]'::jsonb, 'accepted_source', NULL, 'old_line_unit_basis_refs', '[]'::jsonb,
                        'digest_binding_state', 'REPOSITORY_BOUND', 'actual_repository_state', 'REPOSITORY_POSTGRES_DEMO'));
            END IF;
            IF d.phap_nhan_id IS DISTINCT FROM m.phap_nhan_id THEN
                RETURN jsonb_build_object('phieu_id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'hold', 'KHO_RETARGET_IMPACT', 'summary', NULL);
            END IF;
            IF d.ma_kho IS DISTINCT FROM p_ma_kho THEN
                RETURN jsonb_build_object('phieu_id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'hold', 'KHO_IDENTITY_CONFLICT', 'summary', NULL);
            END IF;
            SELECT c.scope_ref, c.profile_ref INTO sc, pr FROM kho.phieu_kho_quan_sat o JOIN giao_tiep.lan_tiep_nhan_nguon c ON c.id = o.lan_tiep_nhan_id
                WHERE o.id = d.latest_observation_id;
            SELECT o.id, o.trang_thai_nguon, v.semantic_sha256, v.id AS content_id INTO acc FROM kho.phieu_kho_quan_sat o
                JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.id = d.accepted_source_observation_id;
            RETURN jsonb_build_object('phieu_id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'hold', NULL, 'latest_observation_id', d.latest_observation_id,
                'summary', jsonb_build_object(
                    'summary_kind', CASE WHEN d.latest_observation_id IS NULL THEN 'EXPLICIT_EMPTY' ELSE 'REPOSITORY_PRIOR_STATE' END,
                    'authority_ref', 'urn:ktt:m5:repository',
                    'logical_source_identity', jsonb_build_object('source_instance', d.source_instance_id, 'SoPhieu', d.so_phieu_key),
                    'scope_ref', coalesce(sc, l.scope_ref), 'profile_ref', coalesce(pr, l.profile_ref),
                    'receipts_seen', (SELECT coalesce(jsonb_agg(jsonb_build_object('receipt_id', o.lan_tiep_nhan_id::text, 'request_digest', o.request_sha256,
                                            'content_digest', v.semantic_sha256, 'content_reference_id', 'urn:ktt:m5:content:' || v.id,
                                            'request_reference_id', NULL, 'binding_state', 'REPOSITORY_BOUND') ORDER BY o.thu_tu), '[]'::jsonb)
                                      FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.phieu_id = d.id),
                    'seen_content_references', (SELECT coalesce(jsonb_agg(jsonb_build_object('reference_id', 'urn:ktt:m5:content:' || v.id,
                                            'logical_source_identity', jsonb_build_object('source_instance', d.source_instance_id, 'SoPhieu', d.so_phieu_key),
                                            'native_raw_sha256', (SELECT r.raw_sha256 FROM kho.anh_chup_nguon_vai_tro r WHERE r.snapshot_id = v.first_snapshot_id
                                                                   AND r.vai_tro = 'NATIVE_DETAIL'),
                                            'master_raw_subtree_sha256', v.master_raw_sha256, 'semantic_digest', v.semantic_sha256,
                                            'binding_state', 'REPOSITORY_BOUND') ORDER BY v.version), '[]'::jsonb)
                                      FROM kho.phieu_kho_phien_ban v WHERE v.phieu_id = d.id),
                    'seen_content_digests', (SELECT coalesce(jsonb_agg(v.semantic_sha256 ORDER BY v.version), '[]'::jsonb) FROM kho.phieu_kho_phien_ban v
                                             WHERE v.phieu_id = d.id),
                    'accepted_source', CASE WHEN acc.id IS NULL THEN NULL ELSE jsonb_build_object('content_digest', acc.semantic_sha256,
                                            'observation_ref', 'urn:ktt:m5:observation:' || acc.id, 'source_state', acc.trang_thai_nguon,
                                            'content_reference_id', 'urn:ktt:m5:content:' || acc.content_id,
                                            'actual_event_history_verification', 'REPOSITORY_REVIEW_V8') END,
                    'old_line_unit_basis_refs', CASE WHEN acc.id IS NULL THEN '[]'::jsonb ELSE (
                        SELECT coalesce(jsonb_agg(jsonb_build_object('native_line_id', dd.id_dong_nguon, 'unit_definition_ref', lv.unit_definition_ref,
                                            'basis_ref', 'urn:ktt:m5:line-version:' || lv.id, 'proof_ref', 'urn:ktt:m5:content:' || acc.content_id,
                                            'proof_authority', 'REPOSITORY_ACCEPTED_SOURCE_LINE', 'actual_source_proof_verification', 'NOT_VERIFIED')
                                            ORDER BY lv.stt), '[]'::jsonb)
                        FROM kho.phieu_kho_dong_phien_ban lv JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lv.dong_id
                        WHERE lv.phien_ban_id = acc.content_id AND lv.unit_definition_ref IS NOT NULL) END,
                    'digest_binding_state', 'REPOSITORY_BOUND', 'actual_repository_state', 'REPOSITORY_POSTGRES_DEMO'));
        END $$""",
    # --- consumer typed + core PHIEU_KHO (S02/SR6): chỉ nhận stage ID + expected H; facts typed/native/status/quantity/precision/classification
    #     đều đọc từ stage bất biến do máy chủ ghi (không caller override). Kiểm lại actor/INTAKE/biên nhận capture của chính stage/mapping hiện hành/
    #     expected latest dưới cùng thứ tự khóa; kỳ khóa → GIU_CHO với 0 typed/core/pointer delta. Core: header PHIEU_KHO owner M5 (DB suy), ngày thật,
    #     DANG_XU_LY, tiền/tiền tệ/chiều NULL; dòng chỉ số lượng exact/proven, Nợ/Có/đơn giá/thuế/TK NULL. Một bộ core cho mỗi content mới (R3 key).
    """CREATE OR REPLACE FUNCTION kho.m5_tieu_thu_quan_sat(p_stage uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE
            ai text := master.ktt_danh_tinh(); s record; p jsonb; l record; m record; d record; v_content uuid; v_moi_content boolean := false; v_obs uuid;
            v_hdr uuid; dl jsonb; v_dong uuid; v_row uuid; v_ver integer; v_thu_tu integer; v_ky text; v_ngay date; v_so text; v_eligible uuid;
            v_ct uuid; v_ctd uuid; cu record;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage capture không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            IF ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: promote cần INTAKE hiện hành của đúng phiên đã tạo stage' USING ERRCODE = 'P0001';
            END IF;
            p := s.du_lieu->'promote';
            IF p IS NULL OR jsonb_typeof(p) <> 'object' THEN
                RAISE EXCEPTION 'STAGE_KHONG_CO_PROMOTE: lần nhận này không đủ căn cứ promote (giữ ứng viên)' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.stage_id = s.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'STAGE_CHUA_CAPTURE: phải tiêu thụ capture của chính stage trước' USING ERRCODE = 'P0001';
            END IF;
            SELECT o.id, o.phieu_id, o.content_id, o.thu_tu INTO cu FROM kho.phieu_kho_quan_sat o WHERE o.lan_tiep_nhan_id = l.id;
            IF FOUND THEN
                RETURN jsonb_build_object('trang_thai', 'DA_GHI_QUAN_SAT', 'lap_lai', true, 'phieu_id', cu.phieu_id, 'content_id', cu.content_id,
                                          'observation_id', cu.id, 'thu_tu', cu.thu_tu);
            END IF;
            v_ngay := (p->>'ngay_chung_tu')::date; v_so := p->>'so_phieu';
            -- thứ tự khóa chung: hàng mapping FOR SHARE → advisory logic → hàng danh tính
            SELECT * INTO m FROM master.anh_xa_nguon x WHERE x.id = (p->>'mapping_revision_id')::uuid AND x.source_instance_id = l.source_instance_id
                AND x.profile_ref = l.profile_ref AND x.profile_sha256 = l.profile_sha256 AND x.subject_kind = 'WAREHOUSE' AND x.subject_key = p->>'ma_kho'
                AND x.state = 'DA_DUYET' AND x.valid_from <= now() AND (x.valid_to IS NULL OR x.valid_to > now()) FOR SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: mapping hiện hành đã đổi' USING ERRCODE = 'P0001';
            END IF;
            v_ky := to_char(v_ngay, 'YYYY-MM');
            IF EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = m.phap_nhan_id AND k.ky = v_ky) THEN
                RETURN jsonb_build_object('trang_thai', 'GIU_CHO', 'ly_do', 'KY_DA_KHOA', 'ky', v_ky);
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || v_so, 0));
            INSERT INTO kho.phieu_kho_danh_tinh (phap_nhan_id, source_instance_id, so_phieu_raw, so_phieu_key, ma_kho, mapping_revision_id, tao_boi)
            VALUES (m.phap_nhan_id, l.source_instance_id, v_so, v_so, p->>'ma_kho', m.id, ai)
            ON CONFLICT (source_instance_id, so_phieu_key) DO NOTHING;
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.source_instance_id = l.source_instance_id AND x.so_phieu_key = v_so FOR UPDATE;
            IF d.phap_nhan_id IS DISTINCT FROM m.phap_nhan_id OR d.ma_kho IS DISTINCT FROM p->>'ma_kho' THEN
                RAISE EXCEPTION 'KHO_RETARGET_IMPACT: danh tính đã promote vào PN/kho khác — giữ impact, không chuyển' USING ERRCODE = 'P0001';
            END IF;
            IF (d.latest_observation_id IS NULL AND p->>'summary_kind' IS DISTINCT FROM 'EXPLICIT_EMPTY')
               OR (d.latest_observation_id IS NOT NULL AND (p->>'latest_truoc') IS DISTINCT FROM d.latest_observation_id::text) THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: lịch sử đã đổi sau lúc phân loại' USING ERRCODE = 'P0001';
            END IF;
            SELECT v.id INTO v_content FROM kho.phieu_kho_phien_ban v WHERE v.phieu_id = d.id AND v.semantic_sha256 = p->>'semantic_sha256';
            IF v_content IS NULL THEN
                v_moi_content := true;
                SELECT b.id INTO v_hdr FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = l.snapshot_id AND b.section = 'GD_Phieu' AND b.locator = '/phieu';
                IF v_hdr IS NULL THEN
                    RAISE EXCEPTION 'M5_THIEU_DONG_NGUON: header' USING ERRCODE = 'P0001';
                END IF;
                SELECT coalesce(max(v.version), 0) + 1 INTO v_ver FROM kho.phieu_kho_phien_ban v WHERE v.phieu_id = d.id;
                -- core header quantity-only: chủ M5 do DB suy từ PHIEU_KHO (trigger chỉ cho chủ bảng ghi), khóa R3 sau dedup content, ngày nguồn thật
                INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, mo_ta, du_lieu, hash, ky, trang_thai)
                VALUES (d.phap_nhan_id, 'PHIEU_KHO', p->>'khoa_nguon_chieu', v_ngay, 'Phiếu kho nguồn #10 — chỉ số lượng (M5), không hạch toán',
                        jsonb_build_object('m5_phieu_id', d.id, 'm5_content_id', p->>'content_id_moi', 'so_phieu', v_so, 'semantic_sha256', p->>'semantic_sha256',
                                           'trang_thai_nguon', p->>'trang_thai_nguon', 'khoa_nguon_chieu', p->>'khoa_nguon_chieu'),
                        p->>'semantic_sha256', v_ky, 'DANG_XU_LY')
                RETURNING id INTO v_ct;
                -- id nội dung do máy chủ đề xuất trước để khóa chiếu R3 (canonical JSON phía máy chủ) gắn đúng content_id; chỉ dùng khi nội dung mới
                INSERT INTO kho.phieu_kho_phien_ban (id, phap_nhan_id, phieu_id, version, semantic_contract, semantic_sha256, profile_ref, profile_sha256,
                    mapping_revision_id, first_snapshot_id, header_row_id, native_header, loai_phieu_raw, trang_thai_raw, trang_thai_nguon, ngay_chung_tu, ma_kho,
                    ma_doi_tac, nguoi_duyet_nguon, thoi_diem_duyet_nguon, master_raw_sha256, master_reference_id, related_master_facts, khoa_nguon_chieu, chung_tu_id)
                VALUES ((p->>'content_id_moi')::uuid, d.phap_nhan_id, d.id, v_ver, 'kho10-content/v1', p->>'semantic_sha256', l.profile_ref, l.profile_sha256, m.id,
                    l.snapshot_id, v_hdr,
                    p->'native_header', p->>'loai_phieu_raw', p->>'trang_thai_raw', p->>'trang_thai_nguon', v_ngay, p->>'ma_kho', p->>'ma_doi_tac',
                    p->>'nguoi_duyet_nguon', p->>'thoi_diem_duyet_nguon', p->>'master_raw_sha256', p->>'master_reference_id', p->'related_master_facts',
                    p->>'khoa_nguon_chieu', v_ct)
                RETURNING id INTO v_content;
                FOR dl IN SELECT * FROM jsonb_array_elements(p->'lines') LOOP
                    INSERT INTO kho.phieu_kho_dong_danh_tinh (phap_nhan_id, phieu_id, id_dong_nguon) VALUES (d.phap_nhan_id, d.id, dl->>'id_dong')
                        ON CONFLICT (phieu_id, id_dong_nguon) DO NOTHING;
                    SELECT x.id INTO v_dong FROM kho.phieu_kho_dong_danh_tinh x WHERE x.phieu_id = d.id AND x.id_dong_nguon = dl->>'id_dong';
                    SELECT b.id INTO v_row FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = l.snapshot_id AND b.section = 'GD_Dong' AND b.locator = dl->>'locator';
                    IF v_row IS NULL THEN
                        RAISE EXCEPTION 'M5_THIEU_DONG_NGUON: %', dl->>'locator' USING ERRCODE = 'P0001';
                    END IF;
                    -- core line: STT = vị trí nguồn; số lượng chỉ khi exact/proven, ngược lại NULL; Nợ/Có/đơn giá/thuế/TK NULL (không fake 0)
                    INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, so_luong, no_minor, co_minor, du_lieu)
                    VALUES (v_ct, (dl->>'stt')::integer, dl->>'ma_hang', (dl->>'so_luong')::numeric(38,12), NULL, NULL,
                            jsonb_build_object('id_dong_nguon', dl->>'id_dong', 'so_luong_nguon', dl->>'so_luong_raw', 'loai_so_luong', dl->>'quantity_json_kind',
                                               'do_chinh_xac', dl->>'precision_state', 'don_vi', dl->>'unit_definition_ref', 'dvt_nguon', dl->>'dvt_raw'))
                    RETURNING id INTO v_ctd;
                    INSERT INTO kho.phieu_kho_dong_phien_ban (phap_nhan_id, phieu_id, phien_ban_id, dong_id, snapshot_id, source_row_id, stt, source_ordinal, ma_hang_raw,
                        native_values, quantity_json_kind, so_luong_raw, so_luong, precision_state, dvt_raw, unit_definition_ref, chung_tu_id, chung_tu_dong_id)
                    VALUES (d.phap_nhan_id, d.id, v_content, v_dong, l.snapshot_id, v_row, (dl->>'stt')::integer, (dl->>'source_ordinal')::integer, dl->>'ma_hang',
                        dl->'native_values', dl->>'quantity_json_kind', dl->>'so_luong_raw', (dl->>'so_luong')::numeric(38,12), dl->>'precision_state',
                        dl->>'dvt_raw', dl->>'unit_definition_ref', v_ct, v_ctd);
                END LOOP;
            END IF;
            SELECT coalesce(max(o.thu_tu), 0) + 1 INTO v_thu_tu FROM kho.phieu_kho_quan_sat o WHERE o.phieu_id = d.id;
            INSERT INTO kho.phieu_kho_quan_sat (phap_nhan_id, phieu_id, content_id, lan_tiep_nhan_id, source_instance_id, snapshot_id, observation_key, thu_tu,
                predecessor_observation_id, trang_thai_nguon, request_sha256, phan_loai, history_state, can_xem_xet, mapping_revision_id, scope_ref)
            VALUES (d.phap_nhan_id, d.id, v_content, l.id, l.source_instance_id, l.snapshot_id, 'HEADER:/phieu', v_thu_tu, d.latest_observation_id,
                p->>'trang_thai_nguon', p->>'request_sha256', ARRAY(SELECT jsonb_array_elements_text(p->'phan_loai')), p->>'history_state',
                (p->>'can_xem_xet')::boolean, m.id, l.scope_ref)
            RETURNING id INTO v_obs;
            -- nguồn đảo chặn eligible ngay dưới cùng khóa (không bịa phiếu âm); accepted chỉ đổi bằng review V8
            v_eligible := CASE WHEN p->>'trang_thai_nguon' = 'DA_DAO' THEN NULL ELSE d.eligible_content_id END;
            UPDATE kho.phieu_kho_danh_tinh SET latest_observation_id = v_obs, eligible_content_id = v_eligible WHERE id = d.id;
            INSERT INTO giao_tiep.tep_tach_phap_nhan (snapshot_id, source_instance_id, phap_nhan_id, module, mapping_revision_id, selected_rows_sha256, transformation_profile)
            VALUES (l.snapshot_id, l.source_instance_id, d.phap_nhan_id, 'M5', m.id, p->>'selected_rows_sha256', 'kho10-m5-promote/v1')
            ON CONFLICT DO NOTHING;
            IF (p->>'can_xem_xet')::boolean THEN
                IF NOT EXISTS (SELECT 1 FROM kho.viec_can_duyet x WHERE x.tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND x.tham_chieu_id = d.id
                               AND x.trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')) THEN
                    INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                    VALUES (d.phap_nhan_id, 'V8', 'M5', 'M5', 'kho.phieu_kho_danh_tinh', d.id, 'CFO', 'Soát nguồn phiếu kho ' || v_so,
                            ARRAY(SELECT jsonb_array_elements_text(p->'phan_loai')));
                ELSE
                    UPDATE kho.viec_can_duyet SET ly_do_cho = ARRAY(SELECT jsonb_array_elements_text(p->'phan_loai')), cap_nhat_luc = now()
                    WHERE tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND tham_chieu_id = d.id AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG');
                END IF;
            END IF;
            RETURN jsonb_build_object('trang_thai', 'DA_GHI_QUAN_SAT', 'phieu_id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'content_id', v_content,
                                      'content_moi', v_moi_content, 'observation_id', v_obs, 'thu_tu', v_thu_tu, 'eligible_content_id', v_eligible);
        END $$""",
    # --- impact retarget/identity conflict: việc V4 trong PN cũ, không chuyển danh tính/nội dung; chỉ từ stage capture đã tiêu thụ của phiên
    """CREATE OR REPLACE FUNCTION kho.m5_giu_cho_anh_huong(p_stage uuid, p_h text, p_ly_do text) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE s record; l record; d record; v_so text;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h OR master.ktt_danh_tinh() IS NULL OR s.actor IS DISTINCT FROM master.ktt_danh_tinh()
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.stage_id = s.id;
            v_so := s.du_lieu->'promote'->>'so_phieu';
            IF NOT FOUND OR v_so IS NULL OR p_ly_do NOT IN ('KHO_RETARGET_IMPACT','KHO_IDENTITY_CONFLICT') THEN
                RAISE EXCEPTION 'M5_GIU_CHO_SAI' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || s.source_instance_id || '|' || v_so, 0));
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.source_instance_id = s.source_instance_id AND x.so_phieu_key = v_so FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M5_GIU_CHO_SAI' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM kho.viec_can_duyet x WHERE x.tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND x.tham_chieu_id = d.id
                           AND x.trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')) THEN
                INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                VALUES (d.phap_nhan_id, 'V4', 'M5', 'M5', 'kho.phieu_kho_danh_tinh', d.id, 'CFO', 'Ảnh hưởng mapping/khóa nguồn phiếu ' || d.so_phieu_key,
                        ARRAY[p_ly_do]);
            ELSE
                UPDATE kho.viec_can_duyet SET ly_do_cho = (SELECT array_agg(DISTINCT u) FROM unnest(ly_do_cho || ARRAY[p_ly_do]) u), cap_nhat_luc = now()
                WHERE tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND tham_chieu_id = d.id AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG');
            END IF;
        END $$""",
    # --- SR02-1 (repair03): chốt KẾT QUẢ CUỐI của lần nhận trong CÙNG giao dịch chủ, SAU consumer typed/hold. INVOKER + không cấp app_web: chỉ
    #     máy chủ cấu hình (chủ bảng) gọi được; trạng thái/refs đối chiếu facts CSDL (quan sát của chính biên nhận, HOLD của stage, kỳ khóa thật,
    #     snapshot mới/cũ) — không nhận refs tùy ý. Ghi một lần (PK biên nhận), bất biến; replay đọc lại qua nguon_tim_lan_nhan.
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_chot_ket_qua(p_stage uuid, p_h text, p_snapshot_moi boolean, p_promote jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE s record; l record; o record; t text; sp jsonb; v_pn uuid; v_khac boolean;
        BEGIN
            IF NOT master.la_chu_bang('giao_tiep.ket_qua_cuoi_tiep_nhan'::regclass) THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_CHI_CHU: chỉ máy chủ cấu hình (chủ bảng) chốt kết quả lần nhận' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h OR master.ktt_danh_tinh() IS NULL OR s.actor IS DISTINCT FROM master.ktt_danh_tinh()
               OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: chốt kết quả cần INTAKE hiện hành của đúng phiên đã tạo stage' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.stage_id = s.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'STAGE_CHUA_CAPTURE: phải tiêu thụ capture của chính stage trước' USING ERRCODE = 'P0001';
            END IF;
            IF p_snapshot_moi IS NULL OR jsonb_typeof(p_promote) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: thiếu snapshot_moi/promote' USING ERRCODE = 'P0001';
            END IF;
            v_khac := EXISTS (SELECT 1 FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.snapshot_id = l.snapshot_id AND x.id <> l.id);
            IF p_snapshot_moi = v_khac THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: snapshot_moi không khớp lịch sử bundle' USING ERRCODE = 'P0001';
            END IF;
            t := p_promote->>'trang_thai';
            sp := s.du_lieu->'promote';
            IF sp IS NOT NULL AND jsonb_typeof(sp) <> 'object' THEN
                sp := NULL;
            END IF;
            SELECT q.id, q.phieu_id, q.content_id INTO o FROM kho.phieu_kho_quan_sat q WHERE q.lan_tiep_nhan_id = l.id;
            IF FOUND THEN
                IF t IS DISTINCT FROM 'DA_GHI_QUAN_SAT' OR p_promote->>'phieu_id' IS DISTINCT FROM o.phieu_id::text
                   OR p_promote->>'content_id' IS DISTINCT FROM o.content_id::text OR p_promote->>'observation_id' IS DISTINCT FROM o.id::text THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: refs quan sát không khớp CSDL' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO_UNG_VIEN' THEN
                IF sp IS NOT NULL THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: stage có kế hoạch promote, không phải ứng viên giữ chờ' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO_ANH_HUONG' THEN
                IF sp IS NULL OR sp->>'hold' IS NULL OR p_promote->'ly_do'->>0 IS DISTINCT FROM sp->>'hold' THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: HOLD ảnh hưởng không khớp stage' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO' THEN
                SELECT m.phap_nhan_id INTO v_pn FROM master.anh_xa_nguon m WHERE m.id = (sp->>'mapping_revision_id')::uuid;
                IF sp IS NULL OR p_promote->>'ly_do' IS DISTINCT FROM 'KY_DA_KHOA'
                   OR NOT EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = v_pn AND k.ky = to_char((sp->>'ngay_chung_tu')::date, 'YYYY-MM')) THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: HOLD kỳ khóa không khớp kỳ thật' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: trạng thái kết quả lạ' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO giao_tiep.ket_qua_cuoi_tiep_nhan (lan_tiep_nhan_id, stage_id, capture_sha256, snapshot_moi, promote, actor_id, actor)
            VALUES (l.id, s.id, l.capture_sha256, p_snapshot_moi, p_promote, s.actor_id, s.actor);
            RETURN jsonb_build_object('stage_id', s.id, 'snapshot_moi', p_snapshot_moi, 'promote', p_promote);
        END $$""",
    # --- review nguồn V8 (S03/S04/SR4): quyền CFO + M5 + V8 hiện hành TRƯỚC tra biên nhận/replay; thứ tự khóa chung advisory logic → hàng danh tính
    #     (cùng intake/file); hash yêu cầu do DB tính; CHẤP NHẬN chỉ cho quan sát MỚI NHẤT (không chọn lại quan sát A cũ để vượt B), không mang lý do chặn,
    #     lịch sử KNOWN; nguồn Đã đảo vẫn được chấp nhận (accepted = B) nhưng eligible NULL. Biên nhận/kết quả do chính hàm dẫn xuất trong cùng giao dịch.
    """CREATE OR REPLACE FUNCTION kho.m5_xem_xet_nguon(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d0 record; d record; o record; v_eligible uuid; v_bn uuid; v_ket jsonb; v_req jsonb; v_h text; cu record;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.source_instance_id, x.so_phieu_key INTO d0 FROM kho.phieu_kho_danh_tinh x WHERE x.id = (p->>'phieu_id')::uuid;
            IF NOT FOUND OR ai IS NULL OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M5') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['CFO'], 'V8') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_SOURCE_REVIEW: cần CFO có V8 + M5 của phiên trên PN của phiếu' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(length(p->>'client_key'), 0) NOT BETWEEN 1 AND 200 OR coalesce(btrim(p->>'ly_do'), '') = ''
               OR p->>'quyet_dinh' IS NULL OR p->>'quyet_dinh' NOT IN ('CHAP_NHAN_NGUON','GIU_CHO') THEN
                RAISE EXCEPTION 'M5_YEU_CAU_SAI: cần khóa, lý do và quyết định CHAP_NHAN_NGUON/GIU_CHO' USING ERRCODE = 'P0001';
            END IF;
            -- thứ tự khóa chung: namespace biên nhận (PN, M5, operation, key) → advisory logic phiếu → hàng danh tính; tra biên nhận SAU các khóa
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M5|SOURCE_REVIEW_V8|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || d0.source_instance_id || '|' || d0.so_phieu_key, 0));
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            v_req := jsonb_build_object('operation', 'SOURCE_REVIEW_V8', 'phieu_id', p->'phieu_id', 'observation_id', p->'observation_id',
                                        'quyet_dinh', p->'quyet_dinh', 'accepted_truoc', p->'accepted_truoc', 'eligible_truoc', p->'eligible_truoc',
                                        'latest_truoc', p->'latest_truoc', 'ly_do', p->'ly_do');
            v_h := encode(sha256(convert_to(v_req::text, 'UTF8')), 'hex');
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = d.phap_nhan_id AND b.module = 'M5' AND b.operation = 'SOURCE_REVIEW_V8' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa review đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            IF (p->>'accepted_truoc') IS DISTINCT FROM d.accepted_source_observation_id::text OR (p->>'eligible_truoc') IS DISTINCT FROM d.eligible_content_id::text
               OR (p->>'latest_truoc') IS DISTINCT FROM d.latest_observation_id::text THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: con trỏ nguồn đã đổi so với expected' USING ERRCODE = 'P0001';
            END IF;
            SELECT q.*, v.ngay_chung_tu INTO o FROM kho.phieu_kho_quan_sat q JOIN kho.phieu_kho_phien_ban v ON v.id = q.content_id
                WHERE q.id = (p->>'observation_id')::uuid AND q.phieu_id = d.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M5_QUAN_SAT_KHONG_THUOC_PHIEU' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = d.phap_nhan_id AND k.ky = to_char(o.ngay_chung_tu, 'YYYY-MM')) THEN
                RAISE EXCEPTION 'KY_DA_KHOA: kỳ % đã khóa', to_char(o.ngay_chung_tu, 'YYYY-MM') USING ERRCODE = 'P0001';
            END IF;
            IF p->>'quyet_dinh' = 'CHAP_NHAN_NGUON' THEN
                IF o.id IS DISTINCT FROM d.latest_observation_id THEN
                    RAISE EXCEPTION 'KHO_SOURCE_REAPPROVAL_REVIEW: chỉ chấp nhận quan sát mới nhất; quan sát cũ không thay bằng chứng nguồn mới' USING ERRCODE = 'P0001';
                END IF;
                IF o.phan_loai && """ + _M5_CHAN_SQL + """ OR o.history_state <> 'KNOWN' THEN
                    RAISE EXCEPTION 'KHO_SOURCE_REAPPROVAL_REVIEW: quan sát mang lý do chặn/lịch sử chưa rõ — cần bằng chứng sự kiện nguồn, không chấp nhận tự động'
                        USING ERRCODE = 'P0001';
                END IF;
                -- accepted = quan sát nguồn mới nhất; eligible CHỈ khi cổng số lượng trên graph tin cậy đạt (K08/09/10: accepted, eligible NULL)
                v_eligible := CASE WHEN o.trang_thai_nguon = 'DA_DUYET' AND kho.m5_quan_sat_du_dieu_kien(o.id) THEN o.content_id END;
                UPDATE kho.phieu_kho_danh_tinh SET accepted_source_observation_id = o.id, eligible_content_id = v_eligible WHERE id = d.id;
            ELSE
                v_eligible := d.eligible_content_id;
            END IF;
            v_ket := jsonb_build_object('phieu_id', d.id, 'quyet_dinh', p->>'quyet_dinh', 'observation_id', o.id,
                                        'accepted_source_observation_id', CASE WHEN p->>'quyet_dinh' = 'CHAP_NHAN_NGUON' THEN o.id ELSE d.accepted_source_observation_id END,
                                        'eligible_content_id', v_eligible);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (d.phap_nhan_id, 'M5', 'SOURCE_REVIEW_V8', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            IF p->>'quyet_dinh' = 'CHAP_NHAN_NGUON' THEN
                UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET', duyet_boi = ai, duyet_luc = now(), cap_nhat_luc = now()
                WHERE tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND tham_chieu_id = d.id AND loai = 'V8' AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG');
            END IF;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (d.phap_nhan_id, ai, 'HE_THONG', 'kho.phieu_kho_danh_tinh', d.id, 'M5_SOURCE_REVIEW_V8', v_ket, p->>'ly_do');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # --- mapping V4 (S07): chỉ đường định nghĩa này ghi master.anh_xa_nguon cho CFO; kiểm ĐỒNG THỜI SOURCE_MAP đúng PN đích + CFO V4 + M5 trước
    #     replay; khóa subject → hàng mapping hiện hành → (retarget) khóa logic từng phiếu bị ảnh hưởng; retarget giữ PN cũ, mở việc V4, không chuyển.
    """CREATE OR REPLACE FUNCTION kho.m5_anh_xa_v4(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v_pn uuid; pr record; n integer; v_req jsonb; v_h text; cu record; hien record; v_rev integer;
            v_moi uuid; v_ref text; ph record; anh_huong jsonb := '[]'::jsonb; v_ket jsonb; v_bn uuid; v_inst text := p->>'source_instance'; v_kho text := p->>'ma_kho';
        BEGIN
            SELECT id INTO v_pn FROM master.phap_nhan WHERE ma = p->>'phap_nhan';
            SELECT count(*) INTO n FROM master.nguon_profile WHERE source_instance_id = v_inst;
            SELECT profile_ref, profile_sha256 INTO pr FROM master.nguon_profile WHERE source_instance_id = v_inst;
            IF ai IS NULL OR v_pn IS NULL OR n <> 1 OR NOT master.ktt_duoc(v_pn, 'M5') OR NOT master.ktt_co_vai(v_pn, ARRAY['CFO'], 'V4')
               OR NOT master.ktt_nguon_duoc(v_inst, pr.profile_ref, pr.profile_sha256, 'SOURCE_MAP', v_pn) THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping cần đồng thời SOURCE_MAP (instance/profile → PN đích) và CFO V4 + M5 của phiên' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(length(p->>'client_key'), 0) NOT BETWEEN 1 AND 200 OR coalesce(btrim(p->>'ly_do'), '') = '' OR coalesce(v_kho, '') = ''
               OR jsonb_typeof(p->'revision_hien_tai') IS DISTINCT FROM 'number' THEN
                RAISE EXCEPTION 'M5_YEU_CAU_SAI: cần khóa, kho nguồn, revision mong đợi và lý do' USING ERRCODE = 'P0001';
            END IF;
            v_rev := (p->>'revision_hien_tai')::integer;
            v_req := jsonb_build_object('operation', 'MAP_V4', 'source_instance', v_inst, 'ma_kho', v_kho, 'phap_nhan', p->'phap_nhan',
                                        'revision_hien_tai', v_rev, 'ly_do', p->'ly_do');
            v_h := encode(sha256(convert_to(v_req::text, 'UTF8')), 'hex');
            -- thứ tự khóa chung: namespace biên nhận (PN, M5, MAP_V4, key) → subject mapping → hàng mapping → advisory logic phiếu → hàng danh tính.
            -- Tra biên nhận SAU khóa: hai yêu cầu cùng key/cùng payload đồng thời → kẻ đến sau chờ, thấy biên nhận của người thắng và REPLAY
            -- (không rơi xuống ANH_XA_DA_CO); cùng key khác payload → 409 trước mọi ghi.
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || v_pn || '|M5|MAP_V4|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('ANH_XA|' || v_inst || '|' || pr.profile_ref || '|' || pr.profile_sha256 || '|WAREHOUSE|' || v_kho, 0));
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = v_pn AND b.module = 'M5' AND b.operation = 'MAP_V4' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa mapping đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            SELECT * INTO hien FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.profile_ref = pr.profile_ref AND m.profile_sha256 = pr.profile_sha256
                AND m.subject_kind = 'WAREHOUSE' AND m.subject_key = v_kho AND m.state = 'DA_DUYET' AND (m.valid_to IS NULL OR m.valid_to > now()) FOR UPDATE;
            IF FOUND THEN
                IF hien.phap_nhan_id = v_pn THEN
                    RAISE EXCEPTION 'ANH_XA_DA_CO: kho nguồn đã map đúng pháp nhân này' USING ERRCODE = 'P0001';
                END IF;
                IF hien.revision <> v_rev THEN
                    RAISE EXCEPTION 'KHO_VERSION_CHANGED: revision mapping hiện tại khác expected' USING ERRCODE = 'P0001';
                END IF;
                v_ref := hien.reference_id;
                -- đóng bản cũ: trigger INVOKER kiểm quyền trên PN CŨ của chính phiên (SOURCE_MAP + CFO V4 + M5)
                UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = hien.id;
                FOR ph IN SELECT x.id, x.phap_nhan_id, x.source_instance_id, x.so_phieu_key FROM kho.phieu_kho_danh_tinh x
                          WHERE x.source_instance_id = v_inst AND x.ma_kho = v_kho ORDER BY x.source_instance_id, x.so_phieu_key LOOP
                    PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || ph.source_instance_id || '|' || ph.so_phieu_key, 0));
                    PERFORM 1 FROM kho.phieu_kho_danh_tinh x WHERE x.id = ph.id FOR UPDATE;
                    IF NOT EXISTS (SELECT 1 FROM kho.viec_can_duyet x WHERE x.tham_chieu_bang = 'kho.phieu_kho_danh_tinh' AND x.tham_chieu_id = ph.id
                                   AND x.trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')) THEN
                        INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                        VALUES (ph.phap_nhan_id, 'V4', 'M5', 'M5', 'kho.phieu_kho_danh_tinh', ph.id, 'CFO',
                                'Mapping kho nguồn đã đổi đích — phiếu giữ PN cũ, chờ xử lý ' || ph.so_phieu_key, ARRAY['KHO_RETARGET_IMPACT']);
                    END IF;
                    anh_huong := anh_huong || to_jsonb(ph.id::text);
                END LOOP;
            ELSE
                SELECT coalesce(max(m.revision), 0) INTO n FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.profile_ref = pr.profile_ref
                    AND m.profile_sha256 = pr.profile_sha256 AND m.subject_kind = 'WAREHOUSE' AND m.subject_key = v_kho;
                IF n <> v_rev THEN
                    RAISE EXCEPTION 'KHO_VERSION_CHANGED: revision cuối của kho nguồn khác expected' USING ERRCODE = 'P0001';
                END IF;
                SELECT m.reference_id INTO v_ref FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.subject_kind = 'WAREHOUSE'
                    AND m.subject_key = v_kho ORDER BY m.revision DESC LIMIT 1;
                v_ref := coalesce(v_ref, 'M5_MAP:' || v_inst || ':' || v_kho);
            END IF;
            INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, phap_nhan_id,
                valid_from, thay_cho_id, nguon_quyet_dinh, duyet_boi, ly_do)
            VALUES (v_ref, v_rev + 1, v_inst, pr.profile_ref, pr.profile_sha256, 'WAREHOUSE', v_kho, v_pn, now(), hien.id, 'CFO_V4', ai, p->>'ly_do')
            RETURNING id INTO v_moi;
            v_ket := jsonb_build_object('mapping_id', v_moi, 'reference_id', v_ref, 'revision', v_rev + 1, 'phap_nhan', p->>'phap_nhan',
                                        'dong_mapping_id', hien.id, 'anh_huong_phieu', anh_huong);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (v_pn, 'M5', 'MAP_V4', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (v_pn, ai, 'HE_THONG', 'master.anh_xa_nguon', v_moi, 'M5_MAP_V4', v_ket, p->>'ly_do');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # --- FILE expected basis (repair03 §4): graph nhất quán đang xem của phiếu, DB dẫn xuất, thứ tự/khóa xác định, không timestamp biến động:
    #     phiếu + ba con trỏ + mapping của danh tính và mapping hiện hành của subject + nội dung/quan sát được chọn (latest) + capture/bundle/vai trò/
    #     profile + master catalog + facts đo lường của profile + dòng nội dung (raw/chuẩn hóa/precision/đơn vị) + dòng nguồn (validation/lỗi) +
    #     cổng eligible + kỳ (và trạng thái khóa) + chuỗi quan sát. Token = SHA-256(jsonb::text) — cùng graph ⇒ cùng token.
    """CREATE OR REPLACE FUNCTION kho.m5_co_so_file_noi_bo(p_phieu uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        SELECT jsonb_build_object(
            'contract', 'm5-file-basis/v1',
            'phieu', jsonb_build_object('id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'source_instance_id', d.source_instance_id,
                                        'so_phieu', d.so_phieu_key, 'ma_kho', d.ma_kho),
            'con_tro', jsonb_build_object('latest', d.latest_observation_id, 'accepted', d.accepted_source_observation_id, 'eligible', d.eligible_content_id),
            'mapping', (SELECT jsonb_build_object('id', m.id, 'reference_id', m.reference_id, 'revision', m.revision, 'state', m.state,
                                                  'dong', m.valid_to IS NOT NULL, 'phap_nhan_id', m.phap_nhan_id, 'nguon_quyet_dinh', m.nguon_quyet_dinh)
                        FROM master.anh_xa_nguon m WHERE m.id = d.mapping_revision_id),
            'mapping_hien_hanh', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', m.id, 'revision', m.revision, 'phap_nhan_id', m.phap_nhan_id)
                                                            ORDER BY m.revision, m.id), '[]'::jsonb)
                                  FROM master.anh_xa_nguon m JOIN master.anh_xa_nguon g ON g.id = d.mapping_revision_id
                                  WHERE m.source_instance_id = g.source_instance_id AND m.profile_ref = g.profile_ref AND m.profile_sha256 = g.profile_sha256
                                    AND m.subject_kind = g.subject_kind AND m.subject_key = g.subject_key AND m.state = 'DA_DUYET' AND m.valid_to IS NULL),
            'quan_sat_chon', (SELECT jsonb_build_object('id', o.id, 'thu_tu', o.thu_tu, 'content_id', o.content_id, 'lan_tiep_nhan_id', o.lan_tiep_nhan_id,
                                                        'snapshot_id', o.snapshot_id, 'trang_thai_nguon', o.trang_thai_nguon, 'request_sha256', o.request_sha256,
                                                        'phan_loai', to_jsonb(o.phan_loai), 'history_state', o.history_state, 'can_xem_xet', o.can_xem_xet,
                                                        'mapping_revision_id', o.mapping_revision_id, 'scope_ref', o.scope_ref)
                              FROM kho.phieu_kho_quan_sat o WHERE o.id = d.latest_observation_id),
            'noi_dung_chon', (SELECT jsonb_build_object('id', v.id, 'version', v.version, 'semantic_sha256', v.semantic_sha256, 'profile_ref', v.profile_ref,
                                                        'profile_sha256', v.profile_sha256, 'mapping_revision_id', v.mapping_revision_id,
                                                        'first_snapshot_id', v.first_snapshot_id, 'master_raw_sha256', v.master_raw_sha256,
                                                        'master_reference_id', v.master_reference_id, 'khoa_nguon_chieu', v.khoa_nguon_chieu,
                                                        'chung_tu_id', v.chung_tu_id, 'ngay_chung_tu', v.ngay_chung_tu, 'trang_thai_raw', v.trang_thai_raw,
                                                        'trang_thai_nguon', v.trang_thai_nguon)
                              FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.id = d.latest_observation_id),
            'capture', (SELECT jsonb_build_object('id', l.id, 'capture_sha256', l.capture_sha256, 'scope_ref', l.scope_ref, 'profile_ref', l.profile_ref,
                                                  'profile_sha256', l.profile_sha256, 'coverage', l.coverage, 'coverage_hieu_luc', l.coverage_hieu_luc,
                                                  'reported_errors', to_jsonb(l.reported_errors), 'snapshot_id', l.snapshot_id,
                                                  'bundle_sha256', a.bundle_sha256, 'bundle_state', a.state,
                                                  'vai_tro', (SELECT coalesce(jsonb_agg(jsonb_build_object('vai_tro', r.vai_tro, 'co_mat', r.co_mat,
                                                                  'raw_sha256', r.raw_sha256, 'byte_length', r.byte_length, 'media_type', r.media_type,
                                                                  'ly_do_vang', r.ly_do_vang) ORDER BY r.vai_tro), '[]'::jsonb)
                                                              FROM kho.anh_chup_nguon_vai_tro r WHERE r.snapshot_id = l.snapshot_id))
                        FROM kho.phieu_kho_quan_sat o JOIN giao_tiep.lan_tiep_nhan_nguon l ON l.id = o.lan_tiep_nhan_id
                        JOIN kho.anh_chup_nguon a ON a.id = l.snapshot_id WHERE o.id = d.latest_observation_id),
            'master', (SELECT jsonb_build_object('reference_id', mn.reference_id, 'raw_sha256', mn.raw_sha256, 'byte_length', mn.byte_length)
                       FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id
                       JOIN master.nguon_master_noi_dung mn ON mn.raw_sha256 = v.master_raw_sha256 WHERE o.id = d.latest_observation_id),
            'do_luong', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', f.id, 'declaration_ref', f.declaration_ref, 'payload_sha256', f.payload_sha256)
                                                   ORDER BY f.declaration_ref, f.payload_sha256), '[]'::jsonb)
                         FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id
                         JOIN master.nguon_su_kien_do_luong f ON f.source_instance_id = d.source_instance_id AND f.profile_ref = v.profile_ref
                                                             AND f.profile_sha256 = v.profile_sha256
                         WHERE o.id = d.latest_observation_id),
            'dong', (SELECT coalesce(jsonb_agg(jsonb_build_object('stt', lw.stt, 'id_dong', dd.id_dong_nguon, 'source_ordinal', lw.source_ordinal,
                                                   'ma_hang', lw.ma_hang_raw, 'loai_so_luong', lw.quantity_json_kind, 'so_luong_nguon', lw.so_luong_raw,
                                                   'so_luong_chuan_hoa', CASE WHEN lw.so_luong IS NULL THEN NULL ELSE lw.so_luong_raw END,
                                                   'do_chinh_xac', lw.precision_state, 'dvt_nguon', lw.dvt_raw, 'don_vi', lw.unit_definition_ref,
                                                   'source_row_id', lw.source_row_id, 'chung_tu_dong_id', lw.chung_tu_dong_id) ORDER BY lw.stt), '[]'::jsonb)
                     FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_dong_phien_ban lw ON lw.phien_ban_id = o.content_id
                     JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lw.dong_id WHERE o.id = d.latest_observation_id),
            'dong_nguon', (SELECT coalesce(jsonb_agg(jsonb_build_object('vai_tro', b.vai_tro, 'section', b.section, 'locator', b.locator, 'thu_tu', b.thu_tu,
                                                         'row_raw_sha256', b.row_raw_sha256, 'quantity_json_kind', b.quantity_json_kind,
                                                         'quantity_text', b.quantity_text, 'validation_state', b.validation_state,
                                                         'error_codes', to_jsonb(b.error_codes)) ORDER BY b.vai_tro, b.section, b.thu_tu, b.locator), '[]'::jsonb)
                           FROM kho.phieu_kho_quan_sat o JOIN kho.ban_ghi_nguon b ON b.snapshot_id = o.snapshot_id WHERE o.id = d.latest_observation_id),
            'du_dieu_kien_so_luong', CASE WHEN d.accepted_source_observation_id IS NULL THEN NULL
                                          ELSE kho.m5_quan_sat_du_dieu_kien(d.accepted_source_observation_id) END,
            'ky', (SELECT jsonb_build_object('ky', to_char(v.ngay_chung_tu, 'YYYY-MM'),
                                             'da_khoa', EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = d.phap_nhan_id
                                                                AND k.ky = to_char(v.ngay_chung_tu, 'YYYY-MM')))
                   FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.id = d.latest_observation_id),
            'lich_su', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'thu_tu', o.thu_tu, 'content_id', o.content_id,
                                                                     'trang_thai_nguon', o.trang_thai_nguon) ORDER BY o.thu_tu), '[]'::jsonb)
                        FROM kho.phieu_kho_quan_sat o WHERE o.phieu_id = d.id))
        FROM kho.phieu_kho_danh_tinh d WHERE d.id = p_phieu
        $$""",
    # đọc token basis cho chi tiết/UI (app thường, M5 của PN): chỉ token + kỳ, không lộ raw/capture metadata ngoài quyền
    """CREATE OR REPLACE FUNCTION kho.m5_co_so_file(p_phieu uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_pn uuid; b jsonb;
        BEGIN
            SELECT x.phap_nhan_id INTO v_pn FROM kho.phieu_kho_danh_tinh x WHERE x.id = p_phieu;
            IF v_pn IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(v_pn, 'M5') THEN
                RETURN NULL;
            END IF;
            b := kho.m5_co_so_file_noi_bo(p_phieu);
            RETURN jsonb_build_object('co_so_sha256', encode(sha256(convert_to(b::text, 'UTF8')), 'hex'), 'ky', b->'ky'->>'ky',
                                      'ky_da_khoa', (b->'ky'->>'da_khoa')::boolean);
        END $$""",
    # --- FILE_SOAT pha 1 (SR2/SR3/I4 + repair03): quyền FILE hiện hành → namespace biên nhận (PN, M5, FILE_SOAT, key) → hàng mapping FOR SHARE →
    #     khóa logic → hàng danh tính; kỳ hiện hành + expected ba con trỏ + expected TOKEN basis toàn graph kiểm TRƯỚC tra biên nhận/replay (retry cũ
    #     sau đổi basis/khóa kỳ bị từ chối, không trả cached success); H gồm token. Trả MỘT snapshot nhất quán dưới khóa. Không ghi gì.
    """CREATE OR REPLACE FUNCTION kho.m5_file_bat_dau(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d0 record; d record; v_req jsonb; v_h text; cu record; lv record; v_snap jsonb; v_co_so jsonb; v_tok text;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.source_instance_id, x.so_phieu_key, x.mapping_revision_id INTO d0 FROM kho.phieu_kho_danh_tinh x
                WHERE x.id = (p->>'phieu_id')::uuid;
            IF NOT FOUND OR ai IS NULL OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M5') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL) THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_FILE_SOAT: cần quyền xuất file soát M5 của phiên trên PN của phiếu' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(length(p->>'client_key'), 0) NOT BETWEEN 1 AND 200 OR coalesce(p->>'co_so_truoc', '') !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'M5_YEU_CAU_SAI: cần khóa thao tác và token basis đang xem (co_so_truoc)' USING ERRCODE = 'P0001';
            END IF;
            -- thứ tự khóa chung: namespace biên nhận → hàng mapping (khóa chia sẻ) → advisory logic phiếu → hàng danh tính (giữ tới consumer cùng giao dịch)
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M5|FILE_SOAT|' || (p->>'client_key'), 0));
            PERFORM 1 FROM master.anh_xa_nguon m WHERE m.id = d0.mapping_revision_id FOR SHARE;
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || d0.source_instance_id || '|' || d0.so_phieu_key, 0));
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            SELECT v.* INTO lv FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.id = d.latest_observation_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'PHIEU_KHO: phiếu chưa có quan sát/nội dung đã promote' USING ERRCODE = 'P0001';
            END IF;
            -- guard HIỆN HÀNH trước mọi cached result: kỳ → expected con trỏ → expected token basis toàn graph
            IF EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = d.phap_nhan_id AND k.ky = to_char(lv.ngay_chung_tu, 'YYYY-MM')) THEN
                RAISE EXCEPTION 'KY_DA_KHOA: kỳ % đã khóa', to_char(lv.ngay_chung_tu, 'YYYY-MM') USING ERRCODE = 'P0001';
            END IF;
            IF (p->>'accepted_truoc') IS DISTINCT FROM d.accepted_source_observation_id::text OR (p->>'eligible_truoc') IS DISTINCT FROM d.eligible_content_id::text
               OR (p->>'latest_truoc') IS DISTINCT FROM d.latest_observation_id::text THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: con trỏ nguồn đã đổi so với expected' USING ERRCODE = 'P0001';
            END IF;
            v_co_so := kho.m5_co_so_file_noi_bo(d.id);
            v_tok := encode(sha256(convert_to(v_co_so::text, 'UTF8')), 'hex');
            IF (p->>'co_so_truoc') IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: basis file soát (nội dung/capture/mapping/master/đo lường/kỳ) đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            v_req := jsonb_build_object('operation', 'FILE_SOAT', 'phieu_id', p->'phieu_id', 'latest_truoc', p->'latest_truoc',
                                        'accepted_truoc', p->'accepted_truoc', 'eligible_truoc', p->'eligible_truoc', 'co_so_truoc', p->'co_so_truoc');
            v_h := encode(sha256(convert_to(v_req::text, 'UTF8')), 'hex');
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = d.phap_nhan_id AND b.module = 'M5' AND b.operation = 'FILE_SOAT' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa file soát đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN jsonb_build_object('lap_lai', true, 'h', v_h, 'ket_qua', cu.result_json || jsonb_build_object('bien_nhan_id', cu.id));
            END IF;
            v_snap := jsonb_build_object(
                'phieu_id', d.id, 'phap_nhan_id', d.phap_nhan_id, 'phap_nhan', (SELECT ma FROM master.phap_nhan WHERE id = d.phap_nhan_id),
                'source_instance_id', d.source_instance_id, 'so_phieu', d.so_phieu_key, 'ma_kho', d.ma_kho, 'mapping_revision_id', d.mapping_revision_id,
                'latest_observation_id', d.latest_observation_id, 'accepted_source_observation_id', d.accepted_source_observation_id,
                'eligible_content_id', d.eligible_content_id, 'ky', to_char(lv.ngay_chung_tu, 'YYYY-MM'),
                'profile_ref', lv.profile_ref, 'profile_sha256', lv.profile_sha256,
                'noi_dung', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', v.id, 'version', v.version, 'semantic_sha256', v.semantic_sha256,
                                    'ngay_chung_tu', v.ngay_chung_tu, 'trang_thai_raw', v.trang_thai_raw, 'trang_thai_nguon', v.trang_thai_nguon,
                                    'khoa_nguon_chieu', v.khoa_nguon_chieu, 'chung_tu_id', v.chung_tu_id, 'master_raw_sha256', v.master_raw_sha256,
                                    'first_snapshot_id', v.first_snapshot_id, 'mapping_revision_id', v.mapping_revision_id,
                                    'dong', (SELECT coalesce(jsonb_agg(jsonb_build_object('stt', lw.stt, 'id_dong', dd.id_dong_nguon, 'source_ordinal', lw.source_ordinal,
                                                 'ma_hang', lw.ma_hang_raw, 'loai_so_luong', lw.quantity_json_kind, 'so_luong_nguon', lw.so_luong_raw,
                                                 'co_chuan_hoa', lw.so_luong IS NOT NULL, 'do_chinh_xac', lw.precision_state, 'dvt_nguon', lw.dvt_raw,
                                                 'don_vi', lw.unit_definition_ref, 'chung_tu_dong_id', lw.chung_tu_dong_id) ORDER BY lw.stt), '[]'::jsonb)
                                             FROM kho.phieu_kho_dong_phien_ban lw JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lw.dong_id
                                             WHERE lw.phien_ban_id = v.id)) ORDER BY v.version), '[]'::jsonb)
                             FROM kho.phieu_kho_phien_ban v WHERE v.phieu_id = d.id),
                'quan_sat', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'thu_tu', o.thu_tu, 'lan_tiep_nhan_id', o.lan_tiep_nhan_id,
                                    'content_id', o.content_id, 'trang_thai_nguon', o.trang_thai_nguon, 'request_sha256', o.request_sha256,
                                    'phan_loai', to_jsonb(o.phan_loai), 'history_state', o.history_state, 'can_xem_xet', o.can_xem_xet, 'known_at', o.known_at)
                                    ORDER BY o.thu_tu), '[]'::jsonb) FROM kho.phieu_kho_quan_sat o WHERE o.phieu_id = d.id),
                'co_so', v_co_so, 'co_so_sha256', v_tok);
            RETURN jsonb_build_object('lap_lai', false, 'h', v_h, 'snapshot', v_snap);
        END $$""",
    # --- FILE_SOAT pha 2: chỉ nhận stage FILE_SOAT + expected H; kiểm lại actor/quyền/khóa/biên nhận/expected/kỳ; registry lô + biên nhận dẫn xuất từ
    #     chính stage (đường dẫn m5-xuat/<sha>.xlsx, SHA/độ dài của bytes máy chủ đã ghi và kiểm). Không ghi gì nếu stale/revoke/khóa kỳ.
    """CREATE OR REPLACE FUNCTION kho.m5_file_tieu_thu(p_stage uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); s record; q jsonb; d0 record; d record; cu record; v_lo uuid; v_bn uuid; v_ket jsonb; lv record;
            v_co_so jsonb; v_tok text;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'FILE_SOAT';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage file soát không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            q := s.du_lieu;
            SELECT x.id, x.phap_nhan_id, x.source_instance_id, x.so_phieu_key, x.mapping_revision_id INTO d0 FROM kho.phieu_kho_danh_tinh x
                WHERE x.id = (q->>'phieu_id')::uuid AND x.phap_nhan_id = s.phap_nhan_id;
            IF NOT FOUND OR ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M5') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL) THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_FILE_SOAT: stage/quyền xuất file soát không còn hợp lệ cho phiên' USING ERRCODE = 'P0001';
            END IF;
            -- cùng thứ tự khóa với pha 1 (khóa giao dịch tái nhập trong cùng giao dịch chủ)
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M5|FILE_SOAT|' || s.client_key, 0));
            PERFORM 1 FROM master.anh_xa_nguon m WHERE m.id = d0.mapping_revision_id FOR SHARE;
            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || d0.source_instance_id || '|' || d0.so_phieu_key, 0));
            SELECT * INTO d FROM kho.phieu_kho_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            -- guard hiện hành (kỳ → con trỏ → token basis) TRƯỚC tra biên nhận
            SELECT v.ngay_chung_tu INTO lv FROM kho.phieu_kho_quan_sat o JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id WHERE o.id = d.latest_observation_id;
            IF to_char(lv.ngay_chung_tu, 'YYYY-MM') IS DISTINCT FROM q->>'ky'
               OR EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = d.phap_nhan_id AND k.ky = q->>'ky') THEN
                RAISE EXCEPTION 'KY_DA_KHOA: kỳ % đã khóa hoặc khác snapshot', q->>'ky' USING ERRCODE = 'P0001';
            END IF;
            IF (q->>'accepted_truoc') IS DISTINCT FROM d.accepted_source_observation_id::text OR (q->>'eligible_truoc') IS DISTINCT FROM d.eligible_content_id::text
               OR (q->>'latest_truoc') IS DISTINCT FROM d.latest_observation_id::text THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: con trỏ nguồn đã đổi so với snapshot của file' USING ERRCODE = 'P0001';
            END IF;
            v_co_so := kho.m5_co_so_file_noi_bo(d.id);
            v_tok := encode(sha256(convert_to(v_co_so::text, 'UTF8')), 'hex');
            IF (q->>'co_so_sha256') IS DISTINCT FROM v_tok OR (q->>'co_so_truoc') IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'KHO_VERSION_CHANGED: basis file soát đã đổi so với snapshot của file' USING ERRCODE = 'P0001';
            END IF;
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = d.phap_nhan_id AND b.module = 'M5' AND b.operation = 'FILE_SOAT' AND b.client_key = s.client_key;
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM s.h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa file soát đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            IF q->>'artifact_sha256' !~ '^[0-9a-f]{64}$' OR (q->>'byte_length')::bigint <= 0 THEN
                RAISE EXCEPTION 'LO_M5_SAI_MUC_DICH: artifact file soát không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, duong_dan, hash, so_dong, nguoi, xuat_luc, trang_thai, du_lieu)
            VALUES (d.phap_nhan_id, q->>'ky', 'M5-' || s.id, 'FILE_SOAT', 'm5-xuat/' || (q->>'artifact_sha256') || '.xlsx', q->>'artifact_sha256',
                    (q->>'so_dong')::integer, ai, now(), 'DA_XUAT',
                    jsonb_build_object('module', 'M5', 'muc_dich', 'FILE_SOAT', 'loai', 'PHIEU_KHO_SOAT', 'stage_id', s.id, 'phieu_id', d.id, 'ten', q->>'ten',
                                       'byte_length', (q->>'byte_length')::bigint, 'snapshot_sha256', q->>'snapshot_sha256',
                                       'latest_observation_id', d.latest_observation_id, 'accepted_source_observation_id', d.accepted_source_observation_id,
                                       'eligible_content_id', d.eligible_content_id, 'co_so_sha256', v_tok,
                                       'mapping_revision_id', v_co_so->'mapping'->>'id', 'noi_dung_chon_id', v_co_so->'noi_dung_chon'->>'id',
                                       'lan_tiep_nhan_id', v_co_so->'capture'->>'id', 'capture_sha256', v_co_so->'capture'->>'capture_sha256',
                                       'bundle_sha256', v_co_so->'capture'->>'bundle_sha256', 'master_raw_sha256', v_co_so->'master'->>'raw_sha256'))
            RETURNING id INTO v_lo;
            v_ket := jsonb_build_object('id', v_lo, 'ten', q->>'ten', 'sha256', q->>'artifact_sha256', 'byte_length', (q->>'byte_length')::bigint,
                                        'phieu_id', d.id, 'snapshot_sha256', q->>'snapshot_sha256', 'co_so_sha256', v_tok);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (d.phap_nhan_id, 'M5', 'FILE_SOAT', s.client_key, s.h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau)
            VALUES (d.phap_nhan_id, ai, 'LO', 'kho.lo_xuat', v_lo, 'XUAT_FILE_SOAT_M5', v_ket);
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    """REVOKE EXECUTE ON FUNCTION kho.m5_khoa_phieu(text, text, text, text, text, text, uuid), kho.m5_tieu_thu_quan_sat(uuid, text),
        kho.m5_giu_cho_anh_huong(uuid, text, text), kho.m5_xem_xet_nguon(jsonb), kho.m5_anh_xa_v4(jsonb), kho.m5_file_bat_dau(jsonb),
        kho.m5_file_tieu_thu(uuid, text), kho.m5_quan_sat_du_dieu_kien(uuid), kho.m5_co_so_file_noi_bo(uuid), kho.m5_co_so_file(uuid),
        giao_tiep.nguon_chot_ket_qua(uuid, text, boolean, jsonb) FROM PUBLIC""",
    "ALTER TABLE kho.phieu_kho_danh_tinh ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.phieu_kho_phien_ban ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.phieu_kho_quan_sat ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.phieu_kho_dong_danh_tinh ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE kho.phieu_kho_dong_phien_ban ENABLE ROW LEVEL SECURITY",
    """DO $$
    DECLARE t text; r text;
    BEGIN
        -- S08: thu hồi ACL mặc định kế thừa của vai trò cũ trên CHÍNH 5 bảng mới (RLS không có policy cho họ ⇒ không thấy)
        FOREACH r IN ARRAY ARRAY['app_ke_toan','app_cong_ai','app_doc'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                FOREACH t IN ARRAY ARRAY['phieu_kho_danh_tinh','phieu_kho_phien_ban','phieu_kho_quan_sat','phieu_kho_dong_danh_tinh','phieu_kho_dong_phien_ban'] LOOP
                    EXECUTE format('REVOKE ALL ON kho.%I FROM %I', t, r);
                END LOOP;
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            FOREACH t IN ARRAY ARRAY['phieu_kho_danh_tinh','phieu_kho_phien_ban','phieu_kho_quan_sat','phieu_kho_dong_danh_tinh','phieu_kho_dong_phien_ban'] LOOP
                EXECUTE format('REVOKE ALL ON kho.%I FROM app_web', t);
                EXECUTE format('GRANT SELECT ON kho.%I TO app_web', t);
                EXECUTE format('DROP POLICY IF EXISTS %I ON kho.%I', t || '_pham_vi_web', t);
                EXECUTE format('CREATE POLICY %I ON kho.%I FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, %L))', t || '_pham_vi_web', t, 'M5');
            END LOOP;
            -- consumer/hàm guarded: gọi được bởi app thường (kiểm actor/quyền hiện hành bên trong); không có writer free-JSON
            GRANT EXECUTE ON FUNCTION kho.m5_khoa_phieu(text, text, text, text, text, text, uuid), kho.m5_tieu_thu_quan_sat(uuid, text),
                kho.m5_giu_cho_anh_huong(uuid, text, text), kho.m5_xem_xet_nguon(jsonb), kho.m5_anh_xa_v4(jsonb), kho.m5_file_bat_dau(jsonb),
                kho.m5_file_tieu_thu(uuid, text), kho.m5_co_so_file(uuid) TO app_web;
            -- KHÔNG cấp app_web: kho.m5_quan_sat_du_dieu_kien / kho.m5_co_so_file_noi_bo (nội bộ, gọi trong definer) và
            -- giao_tiep.nguon_chot_ket_qua (chỉ máy chủ cấu hình — chủ bảng — trong giao dịch nhận)
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0015 M2 BRIDGE (R15, docs/GIAO-CODE-M2-BRIDGE-01.md): APPEND ONLY — không sửa/alias 1–14. Nối nguồn XML/ZIP hóa đơn mua (pure reader
#   `nguon/hoa_don_xml.py`) vào M2: 1 bảng MASTER định nghĩa đơn vị dùng chung + 6 bảng M2 (danh tính / phiên bản nội dung / quan sát /
#   dòng logic / cầu nối dòng-phiên bản / tuyến dòng mua) + view tuyến hiện hành; thích ứng COMMON có cộng thêm (scope INVOICE_SET, mapping
#   COMPANY/INVOICE_LINE, dòng nguồn dẫn xuất không byte-span, stage có module, consumer capture nhận nhiều media/vai trò, finalizer theo
#   module, core HD_MUA owner M2 NULL tiền/Nợ/Có, biên nhận M2 owner-only). Không pool/child số lượng/L11/journal/M9 (R16 và sau).
# ---------------------------------------------------------------------------
_M2_BANG = ("kho.hoa_don_danh_tinh", "kho.hoa_don_phien_ban", "kho.hoa_don_quan_sat", "kho.hoa_don_dong_danh_tinh", "kho.hoa_don_dong_phien_ban",
            "kho.mua_dich_dong")
_M2_TOKEN = "encode(sha256(convert_to({x}::text, 'UTF8')), 'hex')"

M0015_M2_BRIDGE = (
    "SET LOCAL check_function_bodies = off",
    # ---- MASTER (R4 repair03): tài liệu khai báo đơn vị = BYTES THÔ bất biến đã admit, gắn với catalog nội dung nguồn dùng chung
    #      master.nguon_master_noi_dung (reference + raw SHA + độ dài). raw document SHA ≠ canonical payload SHA. Căn cứ nguồn (source_basis_ref)
    #      là chuỗi mờ (opaque, có thể URN) gắn ĐÚNG MỘT tài liệu (UNIQUE) — không suy authority từ cú pháp chuỗi.
    "ALTER TABLE master.nguon_master_noi_dung ADD CONSTRAINT nguon_master_noi_dung_ref_sha_len_m2_uq UNIQUE (reference_id, raw_sha256, byte_length)",
    """CREATE TABLE master.tai_lieu_khai_bao_don_vi (
        reference_id text PRIMARY KEY CHECK (length(reference_id) BETWEEN 1 AND 300),
        raw_sha256 text NOT NULL UNIQUE CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 1),
        noi_dung bytea NOT NULL,
        source_basis_ref text NOT NULL UNIQUE CHECK (length(source_basis_ref) BETWEEN 1 AND 300),
        known_at_server timestamptz NOT NULL DEFAULT now(),
        CHECK (octet_length(noi_dung) = byte_length AND encode(sha256(noi_dung), 'hex') = raw_sha256),
        FOREIGN KEY (reference_id, raw_sha256, byte_length) REFERENCES master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length),
        UNIQUE (reference_id, raw_sha256))""",
    """CREATE OR REPLACE FUNCTION master.tai_lieu_khai_bao_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE v jsonb;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_BAT_BIEN: tài liệu khai báo đơn vị chỉ thêm, không sửa/xóa' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_CHI_CHU: tài liệu khai báo chỉ do cấu hình của chủ CSDL admit' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM master.nguon_master_noi_dung m WHERE m.reference_id = NEW.reference_id AND m.raw_sha256 = NEW.raw_sha256
                           AND m.byte_length = NEW.byte_length) THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_KHONG_CO_CATALOG: tài liệu chưa có trong catalog nội dung nguồn với đúng reference/SHA/độ dài'
                    USING ERRCODE = 'P0001';
            END IF;
            IF octet_length(NEW.noi_dung) <> NEW.byte_length OR encode(sha256(NEW.noi_dung), 'hex') <> NEW.raw_sha256 THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_SAI_HASH: bytes tài liệu không khớp SHA/độ dài khai' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM master.tai_lieu_khai_bao_don_vi x WHERE x.source_basis_ref = NEW.source_basis_ref
                       AND (x.reference_id, x.raw_sha256) IS DISTINCT FROM (NEW.reference_id, NEW.raw_sha256)) THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_CAN_CU_DA_DUNG: căn cứ nguồn đã gắn với tài liệu khác — không tái dùng căn cứ cũ cho bytes mới'
                    USING ERRCODE = 'P0001';
            END IF;
            -- căn cứ nhắc tới một SHA256 khác SHA thật của tài liệu → mâu thuẫn, từ chối (căn cứ mờ không chứa SHA vẫn hợp lệ, gắn qua UNIQUE)
            IF NEW.source_basis_ref ~ '[0-9a-f]{64}' AND position(NEW.raw_sha256 IN NEW.source_basis_ref) = 0 THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_CAN_CU_SAI: căn cứ nguồn nêu SHA khác tài liệu thật' USING ERRCODE = 'P0001';
            END IF;
            BEGIN
                v := convert_from(NEW.noi_dung, 'UTF8')::jsonb;
            EXCEPTION WHEN others THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_KHONG_DOC_DUOC: tài liệu khai báo phải là JSON UTF-8 hợp lệ' USING ERRCODE = 'P0001';
            END;
            IF jsonb_typeof(v) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'DON_VI_TAI_LIEU_KHONG_DOC_DUOC: tài liệu khai báo phải là một JSON object' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER tai_lieu_khai_bao_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.tai_lieu_khai_bao_don_vi FOR EACH ROW EXECUTE FUNCTION master.tai_lieu_khai_bao_kiem()",
    # ---- MASTER: định nghĩa đơn vị lượng dùng chung (R15 seed đúng 1 định nghĩa CAI phía hóa đơn; R16 bind proof vào CÙNG bảng này).
    #      Repair03: mỗi hàng mang tuple khai báo chính xác — tài liệu (ref + raw SHA) + locator JSON pointer của payload + căn cứ nguyên văn +
    #      ngữ cảnh hỗ trợ (instance/profile; tùy chọn raw native/master SHA + locator) — và chỉ được admit khi CSDL tự đối chiếu với bytes tài liệu.
    """CREATE TABLE master.dinh_nghia_don_vi_luong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        reference_id text NOT NULL UNIQUE CHECK (length(reference_id) BETWEEN 1 AND 200),
        definition_sha256 text NOT NULL CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
        payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
        source_basis_ref text NOT NULL CHECK (length(source_basis_ref) BETWEEN 1 AND 300),
        declared_scope text NOT NULL,
        declaration_ref text NOT NULL,
        declaration_raw_sha256 text NOT NULL,
        declaration_locator text NOT NULL CHECK (declaration_locator ~ '^(/[A-Za-z0-9_]+)+$'),
        support_source_instance_id text NOT NULL,
        support_profile_ref text NOT NULL,
        support_profile_sha256 text NOT NULL,
        support_raw_sha256 text,
        support_locator text,
        known_at_server timestamptz NOT NULL DEFAULT now(),
        created_by uuid REFERENCES master.nguoi_dung(id),
        CHECK (payload->>'reference_id' = reference_id AND payload->>'scope' = declared_scope),
        CHECK (coalesce((support_raw_sha256 IS NULL AND support_locator IS NULL)
                        OR (support_raw_sha256 IS NOT NULL AND support_locator IS NOT NULL AND support_raw_sha256 ~ '^[0-9a-f]{64}$'
                            AND support_locator <> ''), false)),
        FOREIGN KEY (declaration_ref, declaration_raw_sha256) REFERENCES master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256),
        FOREIGN KEY (support_source_instance_id, support_profile_ref, support_profile_sha256)
            REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        FOREIGN KEY (support_raw_sha256) REFERENCES master.nguon_master_noi_dung (raw_sha256),
        UNIQUE (declaration_ref, declaration_locator),
        UNIQUE (id, definition_sha256))""",
    # canonical JSON đúng hợp đồng payload digest (khóa sắp theo code point đệ quy, compact ',' ':', UTF-8 không escape ASCII, giữ thứ tự mảng,
    # không BOM/newline) — KHÔNG dùng jsonb::text (khóa theo độ dài + ", "/": "). Số chỉ nhận số nguyên (fail closed, không tự đổi dạng số).
    """CREATE OR REPLACE FUNCTION master.json_chuan(v jsonb) RETURNS text
        LANGUAGE plpgsql IMMUTABLE STRICT SET search_path = pg_catalog, pg_temp AS $$
        DECLARE t text := jsonb_typeof(v); r text;
        BEGIN
            IF t = 'object' THEN
                SELECT '{' || coalesce(string_agg(to_jsonb(e.key)::text || ':' || master.json_chuan(e.value), ',' ORDER BY e.key COLLATE "C"), '') || '}'
                    INTO r FROM jsonb_each(v) e;
                RETURN r;
            ELSIF t = 'array' THEN
                SELECT '[' || coalesce(string_agg(master.json_chuan(e.value), ',' ORDER BY e.ord), '') || ']'
                    INTO r FROM jsonb_array_elements(v) WITH ORDINALITY AS e(value, ord);
                RETURN r;
            ELSIF t = 'number' AND v::text !~ '^-?(0|[1-9][0-9]*)$' THEN
                RAISE EXCEPTION 'JSON_CHUAN_SO: payload chuẩn hóa chỉ nhận số nguyên' USING ERRCODE = 'P0001';
            END IF;
            RETURN v::text;
        END $$""",
    # R4 repair03: MỘT quy tắc đối chiếu đơn vị ↔ tuple khai báo đã admit, dùng cho cả admission (trigger) lẫn consumer (trước khi gắn vào cầu
    # nối). Giá trị kỳ vọng lấy ĐỘC LẬP từ bytes tài liệu: payload tại locator (so canonical), payload SHA tài liệu khai ở khóa anh em
    # `definition_payload_sha256` (bắt buộc) và = canonical tự tính, reference/scope, căn cứ nguyên văn (khai trong tài liệu nếu có, ngược lại
    # căn cứ đã gắn với tài liệu), instance/profile hỗ trợ khi tài liệu khai. Trả NULL khi khớp, ngược lại mã từ chối cụ thể.
    """CREATE OR REPLACE FUNCTION master.don_vi_khop_khai_bao(p_payload jsonb, p_sha text, p_ref text, p_scope text, p_decl_ref text, p_decl_sha text,
            p_locator text, p_basis text, p_inst text, p_pref text, p_psha text) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        DECLARE t record; doc jsonb; sub jsonb; cha jsonb; v_path text[]; v_h text;
        BEGIN
            SELECT * INTO t FROM master.tai_lieu_khai_bao_don_vi x WHERE x.reference_id = p_decl_ref;
            IF t.reference_id IS NULL THEN
                RETURN 'DON_VI_TAI_LIEU_KHONG_CO';
            END IF;
            IF t.raw_sha256 IS DISTINCT FROM p_decl_sha OR octet_length(t.noi_dung) <> t.byte_length OR encode(sha256(t.noi_dung), 'hex') <> t.raw_sha256 THEN
                RETURN 'DON_VI_TAI_LIEU_SAI_HASH';
            END IF;
            BEGIN
                doc := convert_from(t.noi_dung, 'UTF8')::jsonb;
            EXCEPTION WHEN others THEN
                RETURN 'DON_VI_TAI_LIEU_KHONG_DOC_DUOC';
            END;
            IF p_locator IS NULL OR p_locator !~ '^(/[A-Za-z0-9_]+)+$' THEN
                RETURN 'DON_VI_VI_TRI_KHONG_CO';
            END IF;
            v_path := string_to_array(substr(p_locator, 2), '/');
            sub := doc #> v_path;
            IF sub IS NULL OR jsonb_typeof(sub) IS DISTINCT FROM 'object' THEN
                RETURN 'DON_VI_VI_TRI_KHONG_CO';
            END IF;
            cha := CASE WHEN cardinality(v_path) = 1 THEN doc ELSE doc #> v_path[1:cardinality(v_path) - 1] END;
            IF p_payload IS NULL OR master.json_chuan(sub) IS DISTINCT FROM master.json_chuan(p_payload) THEN
                RETURN 'DON_VI_KHONG_KHOP_TAI_LIEU';
            END IF;
            v_h := encode(sha256(convert_to(master.json_chuan(sub), 'UTF8')), 'hex');
            IF jsonb_typeof(cha->'definition_payload_sha256') IS DISTINCT FROM 'string' OR cha->>'definition_payload_sha256' IS DISTINCT FROM v_h
               OR p_sha IS DISTINCT FROM v_h THEN
                RETURN 'DON_VI_DIGEST_SAI';
            END IF;
            IF p_ref IS DISTINCT FROM sub->>'reference_id' OR (cha ? 'reference_id' AND cha->>'reference_id' IS DISTINCT FROM p_ref)
               OR p_scope IS DISTINCT FROM sub->>'scope' THEN
                RETURN 'DON_VI_KHONG_KHOP_TAI_LIEU';
            END IF;
            IF cha ? 'source_basis_ref' THEN
                IF jsonb_typeof(cha->'source_basis_ref') IS DISTINCT FROM 'string' OR p_basis IS DISTINCT FROM cha->>'source_basis_ref' THEN
                    RETURN 'DON_VI_CAN_CU_SAI';
                END IF;
            ELSIF p_basis IS DISTINCT FROM t.source_basis_ref THEN
                RETURN 'DON_VI_CAN_CU_SAI';
            END IF;
            IF (doc ? 'source_instance' AND doc->>'source_instance' IS DISTINCT FROM p_inst) OR (doc ? 'profile_ref' AND doc->>'profile_ref' IS DISTINCT FROM p_pref)
               OR (doc ? 'profile_payload_sha256' AND doc->>'profile_payload_sha256' IS DISTINCT FROM p_psha) THEN
                RETURN 'DON_VI_PHAM_VI_SAI';
            END IF;
            RETURN NULL;
        END $$""",
    # R4: định nghĩa đơn vị chỉ là authority khi digest khai = digest canonical của CHÍNH payload, đủ trường nghĩa, VÀ khớp đúng tuple tài liệu
    # khai báo đã admit (master.don_vi_khop_khai_bao). Không hệ số mặc định, không hardcode đơn vị; định nghĩa đơn vị không phải proof quy đổi.
    """CREATE OR REPLACE FUNCTION master.dinh_nghia_don_vi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE k text; v_loi text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'DON_VI_BAT_BIEN: định nghĩa đơn vị chỉ thêm, không sửa/xóa' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'DON_VI_CHI_CHU: định nghĩa đơn vị chỉ do chủ CSDL ghi' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.definition_sha256 IS DISTINCT FROM encode(sha256(convert_to(master.json_chuan(NEW.payload), 'UTF8')), 'hex') THEN
                RAISE EXCEPTION 'DON_VI_DIGEST_SAI: definition_sha256 khác digest canonical của payload' USING ERRCODE = 'P0001';
            END IF;
            FOREACH k IN ARRAY ARRAY['reference_id','scope','native_unit_code','definition_kind','meaning','label','authority'] LOOP
                IF jsonb_typeof(NEW.payload->k) IS DISTINCT FROM 'string' OR coalesce(NEW.payload->>k, '') = '' THEN
                    RAISE EXCEPTION 'DON_VI_NGHIA_THIEU: payload đơn vị thiếu trường nghĩa %', k USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
            IF jsonb_typeof(NEW.payload->'version') IS DISTINCT FROM 'number' OR NEW.payload->>'reference_id' IS DISTINCT FROM NEW.reference_id
               OR NEW.payload->>'scope' IS DISTINCT FROM NEW.declared_scope THEN
                RAISE EXCEPTION 'DON_VI_NGHIA_THIEU: reference/scope/version không khớp payload' USING ERRCODE = 'P0001';
            END IF;
            v_loi := master.don_vi_khop_khai_bao(NEW.payload, NEW.definition_sha256, NEW.reference_id, NEW.declared_scope, NEW.declaration_ref,
                                                 NEW.declaration_raw_sha256, NEW.declaration_locator, NEW.source_basis_ref, NEW.support_source_instance_id,
                                                 NEW.support_profile_ref, NEW.support_profile_sha256);
            IF v_loi IS NOT NULL THEN
                RAISE EXCEPTION '%: định nghĩa đơn vị không khớp tuple tài liệu khai báo đã admit', v_loi USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER dinh_nghia_don_vi_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.dinh_nghia_don_vi_luong FOR EACH ROW EXECUTE FUNCTION master.dinh_nghia_don_vi_kiem()",
    # ---- COMMON: scope có kiểu; INVOICE_SET dùng tập company key, MaKho/SoPhieu NULL (không giả kho/phiếu); hàng cũ mặc định KHO10_PHIEU
    "ALTER TABLE master.nguon_pham_vi ADD COLUMN scope_kind text NOT NULL DEFAULT 'KHO10_PHIEU'",
    "ALTER TABLE master.nguon_pham_vi ADD COLUMN company_keys text[]",
    "ALTER TABLE master.nguon_pham_vi ALTER COLUMN ma_kho DROP NOT NULL",
    "ALTER TABLE master.nguon_pham_vi ALTER COLUMN so_phieu DROP NOT NULL",
    """ALTER TABLE master.nguon_pham_vi ADD CONSTRAINT nguon_pham_vi_kind_m2_check CHECK (
        (scope_kind = 'KHO10_PHIEU' AND ma_kho IS NOT NULL AND so_phieu IS NOT NULL AND company_keys IS NULL)
        OR (scope_kind = 'INVOICE_SET' AND ma_kho IS NULL AND so_phieu IS NULL AND company_keys IS NOT NULL AND cardinality(company_keys) >= 1))""",
    "ALTER TABLE master.nguon_profile ADD CONSTRAINT nguon_profile_id_sha_m2_uq UNIQUE (id, profile_sha256)",
    # ---- COMMON: stage cùng đường đóng owner-only, thêm module để phân biệt CAPTURE M2/M5 (M5 cũ NULL)
    "ALTER TABLE giao_tiep.stage_tin_cay ADD COLUMN module text CHECK (module IS NULL OR module IN ('M5','M2'))",
    # ---- MASTER (R2 repair02): ứng viên bằng chứng literal dòng hóa đơn — CHỈ là raw candidate evidence đã admit từ cấu hình đã pin, KHÔNG phải
    #      registry duyệt: không tạo mapping/dòng logic, không cấp quyền. Chủ bảng ghi, chỉ thêm; digest canonical CSDL tính lại; cột dẫn xuất từ
    #      payload (không nhận cột do caller khai); hình dạng NULL tường minh (XML: bộ ZIP all NULL; ZIP: all present).
    """CREATE TABLE master.m2_ung_vien_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
        fact_sha256 text NOT NULL CHECK (fact_sha256 ~ '^[0-9a-f]{64}$'),
        source_document_ref text NOT NULL CHECK (length(source_document_ref) BETWEEN 1 AND 300),
        source_document_sha256 text NOT NULL CHECK (source_document_sha256 ~ '^[0-9a-f]{64}$'),
        mapping_ref text NOT NULL CHECK (mapping_ref ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        revision integer NOT NULL CHECK (revision >= 1),
        authority text NOT NULL CHECK (authority = 'RAW_DEMO_EVIDENCE_REQUIRES_ACTUAL_CFO_MAPPING'),
        source_instance_id text NOT NULL,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        scope_ref text NOT NULL,
        company_key text NOT NULL CHECK (company_key <> ''),
        phap_nhan_ma text NOT NULL REFERENCES master.phap_nhan(ma),
        native_xml_sha256 text NOT NULL CHECK (native_xml_sha256 ~ '^[0-9a-f]{64}$'),
        native_byte_length bigint NOT NULL CHECK (native_byte_length >= 1),
        container_sha256 text,
        container_byte_length bigint,
        entry_ordinal integer,
        entry_name text,
        identity_tuple text[] NOT NULL,
        source_locator text NOT NULL CHECK (source_locator <> ''),
        source_ordinal integer NOT NULL CHECK (source_ordinal >= 1),
        logical_line_key text NOT NULL CHECK (logical_line_key ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        known_at_server timestamptz NOT NULL DEFAULT now(),
        CHECK (coalesce((container_sha256 IS NULL AND container_byte_length IS NULL AND entry_ordinal IS NULL AND entry_name IS NULL)
                        OR (container_sha256 IS NOT NULL AND container_byte_length IS NOT NULL AND entry_ordinal IS NOT NULL AND entry_name IS NOT NULL
                            AND container_sha256 ~ '^[0-9a-f]{64}$' AND container_byte_length >= 1 AND entry_ordinal >= 1 AND entry_name <> ''), false)),
        CHECK (coalesce(cardinality(identity_tuple) = 6 AND array_position(identity_tuple, NULL) IS NULL AND NOT ('' = ANY (identity_tuple)), false)),
        FOREIGN KEY (source_instance_id, profile_ref, profile_sha256) REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256),
        FOREIGN KEY (source_instance_id, scope_ref) REFERENCES master.nguon_pham_vi (source_instance_id, scope_ref),
        UNIQUE (mapping_ref, revision))""",
    """CREATE OR REPLACE FUNCTION master.m2_ung_vien_dong_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE p jsonb; s record;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_BAT_BIEN: ứng viên literal chỉ thêm, không sửa/xóa' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_CHI_CHU: ứng viên literal chỉ do cấu hình của chủ CSDL admit' USING ERRCODE = 'P0001';
            END IF;
            p := NEW.payload;
            IF NEW.fact_sha256 IS DISTINCT FROM encode(sha256(convert_to(master.json_chuan(p), 'UTF8')), 'hex') THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_DIGEST: fact_sha256 khác digest canonical của payload' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_typeof(p->'identity_tuple') IS DISTINCT FROM 'array' OR jsonb_typeof(p->'revision') IS DISTINCT FROM 'number'
               OR jsonb_typeof(p->'source_ordinal') IS DISTINCT FROM 'number' OR jsonb_typeof(p->'native_byte_length') IS DISTINCT FROM 'number'
               OR p->'row_raw_sha256' IS DISTINCT FROM 'null'::jsonb OR p->'row_byte_span' IS DISTINCT FROM 'null'::jsonb THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_HINH_DANG: payload literal thiếu/sai kiểu trường bắt buộc' USING ERRCODE = 'P0001';
            END IF;
            NEW.mapping_ref := p->>'mapping_ref';
            NEW.revision := (p->>'revision')::integer;
            NEW.authority := p->>'authority';
            NEW.source_instance_id := p->>'source_instance';
            NEW.profile_ref := p->>'profile_ref';
            NEW.profile_sha256 := p->>'profile_payload_sha256';
            NEW.scope_ref := p->>'scope_ref';
            NEW.company_key := p->>'company_key';
            NEW.phap_nhan_ma := p->>'existing_phap_nhan_ma';
            NEW.native_xml_sha256 := p->>'native_xml_sha256';
            NEW.native_byte_length := (p->>'native_byte_length')::bigint;
            NEW.container_sha256 := p->>'container_sha256';
            NEW.container_byte_length := (p->>'container_byte_length')::bigint;
            NEW.entry_ordinal := (p->>'entry_ordinal')::integer;
            NEW.entry_name := p->>'entry_name';
            NEW.identity_tuple := ARRAY(SELECT jsonb_array_elements_text(p->'identity_tuple'));
            NEW.source_locator := p->>'source_locator';
            NEW.source_ordinal := (p->>'source_ordinal')::integer;
            NEW.logical_line_key := p->>'logical_line_key';
            SELECT x.company_keys INTO s FROM master.nguon_pham_vi x WHERE x.source_instance_id = NEW.source_instance_id AND x.scope_ref = NEW.scope_ref
                AND x.profile_ref = NEW.profile_ref AND x.profile_sha256 = NEW.profile_sha256 AND x.scope_kind = 'INVOICE_SET';
            IF NOT FOUND OR NOT (NEW.company_key = ANY (s.company_keys)) THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_HINH_DANG: scope/company key của ứng viên không thuộc phạm vi INVOICE_SET cấu hình' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.identity_tuple[1] IS DISTINCT FROM NEW.phap_nhan_ma OR NEW.identity_tuple[2] IS DISTINCT FROM 'MUA_VAO' THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_HINH_DANG: định danh literal phải là MUA_VAO của đúng PN khai' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER m2_ung_vien_dong_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.m2_ung_vien_dong FOR EACH ROW EXECUTE FUNCTION master.m2_ung_vien_dong_kiem()",
    # ---- COMMON: dòng nguồn dẫn xuất M2 không có byte span → row_raw_sha256 NULL CHỈ khi có hash_basis tường minh + digest bản ghi dẫn xuất (DB tính)
    "ALTER TABLE kho.ban_ghi_nguon ALTER COLUMN row_raw_sha256 DROP NOT NULL",
    """ALTER TABLE kho.ban_ghi_nguon ADD COLUMN hash_basis text
        CHECK (hash_basis IS NULL OR hash_basis IN ('XML_DECODED_FIELD_STATES','ZIP_ENTRY_INVENTORY','CROSSWALK_METADATA'))""",
    "ALTER TABLE kho.ban_ghi_nguon ADD COLUMN derived_record_sha256 text CHECK (derived_record_sha256 IS NULL OR derived_record_sha256 ~ '^[0-9a-f]{64}$')",
    """ALTER TABLE kho.ban_ghi_nguon ADD CONSTRAINT ban_ghi_nguon_basis_m2_check CHECK (
        (row_raw_sha256 IS NOT NULL AND hash_basis IS NULL AND derived_record_sha256 IS NULL)
        OR (row_raw_sha256 IS NULL AND hash_basis IS NOT NULL AND derived_record_sha256 IS NOT NULL))""",
    # INVOKER: dòng basis M2 chỉ chủ bảng ghi, chỉ cho profile module M2, section ↔ basis đúng loại, bind đúng artifact thực của snapshot/vai trò;
    # digest bản ghi dẫn xuất do CSDL tự tính (không nhận từ caller). Profile M2 không được dùng dòng kiểu M5 (row_raw_sha256) và ngược lại.
    """CREATE OR REPLACE FUNCTION kho.ban_ghi_nguon_m2_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE v_mod text;
        BEGIN
            SELECT p.payload->>'module' INTO v_mod FROM kho.anh_chup_nguon a
                JOIN master.nguon_profile p ON p.source_instance_id = a.source_instance_id AND p.profile_ref = a.profile_ref AND p.profile_sha256 = a.profile_sha256
                WHERE a.id = NEW.snapshot_id;
            IF NEW.hash_basis IS NULL THEN
                IF v_mod = 'M2' THEN
                    RAISE EXCEPTION 'M2_DONG_NGUON_BASIS: dòng nguồn M2 phải có hash_basis dẫn xuất tường minh' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) OR v_mod IS DISTINCT FROM 'M2' THEN
                RAISE EXCEPTION 'M2_DONG_NGUON_BASIS: dòng dẫn xuất chỉ do chủ bảng ghi cho profile M2' USING ERRCODE = 'P0001';
            END IF;
            IF NOT ((NEW.section IN ('XML_HEADER','XML_LINE') AND NEW.hash_basis = 'XML_DECODED_FIELD_STATES')
                    OR (NEW.section = 'ZIP_ENTRY' AND NEW.hash_basis = 'ZIP_ENTRY_INVENTORY')
                    OR (NEW.section = 'CROSSWALK' AND NEW.hash_basis = 'CROSSWALK_METADATA')) THEN
                RAISE EXCEPTION 'M2_DONG_NGUON_BASIS: section % không khớp hash_basis %', NEW.section, NEW.hash_basis USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = NEW.snapshot_id AND v.vai_tro = NEW.vai_tro AND v.co_mat
                           AND v.raw_sha256 = NEW.row_raw->>'artifact_sha256') THEN
                RAISE EXCEPTION 'M2_DONG_NGUON_ARTIFACT: dòng dẫn xuất không bind đúng artifact thực của snapshot' USING ERRCODE = 'P0001';
            END IF;
            NEW.row_raw_sha256 := NULL;
            NEW.derived_record_sha256 := encode(sha256(convert_to(NEW.row_raw::text, 'UTF8')), 'hex');
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER ban_ghi_nguon_m2_kiem BEFORE INSERT ON kho.ban_ghi_nguon FOR EACH ROW EXECUTE FUNCTION kho.ban_ghi_nguon_m2_kiem()",
    # ---- COMMON: derivative M2; biên nhận M2 owner-only; core module M2
    "ALTER TABLE giao_tiep.tep_tach_phap_nhan DROP CONSTRAINT tep_tach_phap_nhan_module_check",
    "ALTER TABLE giao_tiep.tep_tach_phap_nhan ADD CONSTRAINT tep_tach_phap_nhan_module_m2_check CHECK (module IN ('M5','M2'))",
    """CREATE OR REPLACE FUNCTION kho.bien_nhan_m5_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE m text;
        BEGIN
            IF TG_OP <> 'DELETE' AND NEW.module IN ('M5','M2') THEN
                m := NEW.module;
            END IF;
            IF TG_OP <> 'INSERT' AND OLD.module IN ('M5','M2') THEN
                m := OLD.module;
            END IF;
            IF m IS NOT NULL AND NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'BIEN_NHAN_%_CHI_CHU: biên nhận % chỉ do đường định nghĩa tạo, không ghi trực tiếp', m, m USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END $$""",
    "ALTER TABLE kho.chung_tu DROP CONSTRAINT chung_tu_module_common_check",
    "ALTER TABLE kho.chung_tu ADD CONSTRAINT chung_tu_module_m2_check CHECK (module_nghiep_vu IN ('CRM','M1','M5','M2'))",
    # owner do DB suy: PHIEU_KHO → M5, HOP_DONG_TEP → CRM; HD_MUA chỉ thành M2 khi projector chủ bảng khai M2 (caller cũ không khai → M1 như trước,
    # hàng HD_MUA/M1 cũ giữ nguyên). M2: chủ bảng, tiền/tiền tệ/chiều/đối tác NULL (chưa có căn cứ precision), DANG_XU_LY, không DA_DUYET/V1.
    """CREATE OR REPLACE FUNCTION kho.chung_tu_chu_so_huu_common() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE mong text;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                mong := CASE WHEN NEW.loai = 'PHIEU_KHO' THEN 'M5' WHEN NEW.loai = 'HOP_DONG_TEP' THEN 'CRM'
                             WHEN NEW.loai = 'HD_MUA' AND NEW.module_nghiep_vu = 'M2' THEN 'M2' ELSE 'M1' END;
                IF NEW.module_nghiep_vu IS NULL THEN
                    NEW.module_nghiep_vu := mong;
                ELSIF NEW.module_nghiep_vu <> mong THEN
                    RAISE EXCEPTION 'CHU_SO_HUU_SAI: chứng từ % thuộc module %, không nhận module do caller khai', NEW.loai, mong USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.module_nghiep_vu IS DISTINCT FROM OLD.module_nghiep_vu
                  OR (NEW.loai IS DISTINCT FROM OLD.loai AND (OLD.module_nghiep_vu IN ('M5','M2') OR NEW.loai = 'PHIEU_KHO' OR OLD.loai = 'HOP_DONG_TEP'
                                                               OR NEW.loai = 'HOP_DONG_TEP')) THEN
                RAISE EXCEPTION 'CHU_SO_HUU_BAT_BIEN: không đổi module/loại quyết định chủ sở hữu' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.module_nghiep_vu = 'M5' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M5_CHI_CHU: chứng từ PHIEU_KHO M5 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.so_tien_minor IS NOT NULL OR NEW.tien_te IS NOT NULL OR NEW.chieu IS NOT NULL OR NEW.doi_tac_id IS NOT NULL THEN
                    RAISE EXCEPTION 'M5_CHI_SO_LUONG: phiếu kho M5 không mang tiền/tiền tệ/chiều/đối tác hạch toán' USING ERRCODE = 'P0001';
                END IF;
                IF TG_OP = 'INSERT' AND NEW.trang_thai <> 'DANG_XU_LY' THEN
                    RAISE EXCEPTION 'M5_KHONG_DUYET_JOURNAL: phiếu kho M5 vào core ở DANG_XU_LY, không DA_DUYET/V1' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.module_nghiep_vu = 'M2' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M2_CHI_CHU: chứng từ HD_MUA M2 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.so_tien_minor IS NOT NULL OR NEW.tien_te IS NOT NULL OR NEW.chieu IS NOT NULL OR NEW.doi_tac_id IS NOT NULL THEN
                    RAISE EXCEPTION 'M2_TIEN_CHUA_CAN_CU: hóa đơn M2 R15 chưa mang tiền/tiền tệ/chiều/đối tác (NULL, không 0)' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.trang_thai <> 'DANG_XU_LY' THEN
                    RAISE EXCEPTION 'M2_KHONG_DUYET_JOURNAL: hóa đơn M2 nguồn ở DANG_XU_LY, không DA_DUYET/V1' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.chung_tu_dong_kiem_common() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE m text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.chung_tu_id IS DISTINCT FROM OLD.chung_tu_id THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_DOI_CHA: không chuyển dòng sang chứng từ khác' USING ERRCODE = 'P0001';
            END IF;
            SELECT c.module_nghiep_vu INTO m FROM kho.chung_tu c WHERE c.id = NEW.chung_tu_id;
            IF m IS NULL THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_CHA_KHONG_THAY: không thấy chứng từ cha trong phạm vi' USING ERRCODE = 'P0001';
            END IF;
            IF m = 'M5' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M5_CHI_CHU: dòng PHIEU_KHO M5 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.no_minor IS NOT NULL OR NEW.co_minor IS NOT NULL OR NEW.don_gia_minor IS NOT NULL OR NEW.tien_truoc_thue_minor IS NOT NULL
                   OR NEW.thue_suat IS NOT NULL OR NEW.tien_thue_minor IS NOT NULL OR NEW.tai_khoan IS NOT NULL THEN
                    RAISE EXCEPTION 'M5_CHI_SO_LUONG: dòng phiếu kho M5 không mang Nợ/Có/đơn giá/thuế/tài khoản (NULL, không 0)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF m = 'M2' THEN
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'CHUNG_TU_M2_CHI_CHU: dòng HD_MUA M2 chỉ do projector của chủ bảng ghi' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.no_minor IS NOT NULL OR NEW.co_minor IS NOT NULL OR NEW.don_gia_minor IS NOT NULL OR NEW.tien_truoc_thue_minor IS NOT NULL
                   OR NEW.thue_suat IS NOT NULL OR NEW.tien_thue_minor IS NOT NULL OR NEW.tai_khoan IS NOT NULL OR NEW.dich IS NOT NULL THEN
                    RAISE EXCEPTION 'M2_TIEN_CHUA_CAN_CU: dòng M2 R15 không mang Nợ/Có/đơn giá/thuế/TK/đích (NULL, không 0; tuyến ở kho.mua_dich_dong)'
                        USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.no_minor IS NULL OR NEW.co_minor IS NULL THEN
                RAISE EXCEPTION 'CHUNG_TU_DONG_NO_CO_NULL: dòng chứng từ không phải M5/M2 phải có no_minor/co_minor' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # ---- R3 (repair02): core HD_MUA M2 là MIRROR nguồn bất biến sau promote — mọi UPDATE thay đổi giá trị và mọi DELETE header/dòng M2 bị từ chối,
    #      kể cả chủ bảng đã cấu hình (không có ngoại lệ owner); tuyến đổi CHỈ qua successor typed kho.mua_dich_dong. Điều kiện theo module M2 của
    #      chứng từ (cũ), không đổi nghĩa M1/M5/CRM; UPDATE không đổi giá trị (no-op) vẫn qua.
    """CREATE OR REPLACE FUNCTION kho.m2_core_nguon_bat_bien() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE m text;
        BEGIN
            IF TG_TABLE_NAME = 'chung_tu' THEN
                m := OLD.module_nghiep_vu;
            ELSE
                SELECT c.module_nghiep_vu INTO m FROM kho.chung_tu c WHERE c.id = OLD.chung_tu_id;
            END IF;
            IF m IS DISTINCT FROM 'M2' THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M2_NGUON_BAT_BIEN: không xóa % của hóa đơn M2 (mirror nguồn bất biến)', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF NEW IS DISTINCT FROM OLD THEN
                RAISE EXCEPTION 'M2_NGUON_BAT_BIEN: không sửa % của hóa đơn M2 (nguồn/số lượng/ngày/hash/payload bất biến; tuyến qua successor typed)',
                    TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # tên "…_zz_m2…" để chạy SAU CÙNG trong các trigger BEFORE (PostgreSQL gọi theo thứ tự tên): so NEW cuối cùng (kể cả cột do trigger khác tự
    # gán như cap_nhat_luc) với OLD → không có "no-op" nào lọt qua làm đổi hàng M2; guard khác có thể từ chối sớm hơn bằng mã riêng (vẫn là từ chối)
    "CREATE TRIGGER chung_tu_zz_m2_nguon_bat_bien BEFORE UPDATE OR DELETE ON kho.chung_tu FOR EACH ROW EXECUTE FUNCTION kho.m2_core_nguon_bat_bien()",
    "CREATE TRIGGER chung_tu_dong_zz_m2_nguon_bat_bien BEFORE UPDATE OR DELETE ON kho.chung_tu_dong FOR EACH ROW EXECUTE FUNCTION kho.m2_core_nguon_bat_bien()",
    # ---- 6 bảng M2
    """CREATE TABLE kho.hoa_don_danh_tinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        chieu text NOT NULL CHECK (chieu = 'MUA_VAO'),
        mst_ban text NOT NULL CHECK (mst_ban ~ '^[ -~]+$'),
        mau_so text NOT NULL CHECK (mau_so ~ '^[ -~]+$'),
        ky_hieu text NOT NULL CHECK (ky_hieu ~ '^[ -~]+$'),
        so_chuan text NOT NULL CHECK (so_chuan ~ '^(0|[1-9][0-9]*)$'),
        source_instance_id text NOT NULL REFERENCES master.nguon_instance(source_instance_id),
        latest_observation_id uuid,
        accepted_source_observation_id uuid,
        eligible_content_id uuid,
        created_at timestamptz NOT NULL DEFAULT now(),
        created_by text NOT NULL,
        UNIQUE (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan),
        UNIQUE (phap_nhan_id, id))""",
    """CREATE TABLE kho.hoa_don_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        semantic_contract text NOT NULL CHECK (semantic_contract = 'M2_XML_CONTENT_V1'),
        semantic_sha256 text NOT NULL CHECK (semantic_sha256 ~ '^[0-9a-f]{64}$'),
        profile_id uuid NOT NULL,
        profile_sha256 text NOT NULL,
        company_mapping_id uuid NOT NULL,
        snapshot_id uuid NOT NULL,
        header_source_row_id uuid NOT NULL,
        raw_header_states jsonb NOT NULL,
        ngay_lap date NOT NULL,
        tien_te text NOT NULL CHECK (length(tien_te) BETWEEN 1 AND 20),
        net_minor bigint,
        tax_minor bigint,
        total_minor bigint,
        other_minor bigint,
        non_taxable_minor bigint,
        raw_components jsonb NOT NULL,
        money_basis_state text NOT NULL CHECK (money_basis_state = 'UNPROVEN_NO_MINOR'),
        chung_tu_id uuid NOT NULL UNIQUE,
        owner_module text NOT NULL DEFAULT 'M2' CHECK (owner_module = 'M2'),
        supersedes_id uuid,
        first_known_at_server timestamptz NOT NULL DEFAULT now(),
        CHECK (net_minor IS NULL AND tax_minor IS NULL AND total_minor IS NULL AND other_minor IS NULL AND non_taxable_minor IS NULL),
        FOREIGN KEY (phap_nhan_id, hoa_don_id) REFERENCES kho.hoa_don_danh_tinh (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, chung_tu_id, owner_module) REFERENCES kho.chung_tu (phap_nhan_id, id, module_nghiep_vu),
        FOREIGN KEY (header_source_row_id, snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        FOREIGN KEY (profile_id, profile_sha256) REFERENCES master.nguon_profile (id, profile_sha256),
        FOREIGN KEY (company_mapping_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (hoa_don_id, phien_ban),
        UNIQUE (hoa_don_id, semantic_sha256),
        UNIQUE (phap_nhan_id, hoa_don_id, id),
        UNIQUE (phap_nhan_id, hoa_don_id, id, chung_tu_id))""",
    """ALTER TABLE kho.hoa_don_phien_ban ADD CONSTRAINT hoa_don_phien_ban_supersedes_fk
        FOREIGN KEY (phap_nhan_id, hoa_don_id, supersedes_id) REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id)""",
    """CREATE TABLE kho.hoa_don_quan_sat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        lan_tiep_nhan_id uuid NOT NULL,
        source_instance_id text NOT NULL,
        snapshot_id uuid NOT NULL,
        source_row_id uuid NOT NULL,
        native_xml_sha256 text NOT NULL CHECK (native_xml_sha256 ~ '^[0-9a-f]{64}$'),
        container_sha256 text,
        entry_ordinal integer,
        entry_name text,
        locator text NOT NULL,
        observation_key text NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu >= 1),
        predecessor_observation_id uuid,
        classification text[] NOT NULL,
        raw_status_namespace text,
        raw_status text,
        native_fiscal_status text NOT NULL DEFAULT 'UNKNOWN' CHECK (native_fiscal_status = 'UNKNOWN'),
        company_mapping_id uuid NOT NULL,
        known_at_server timestamptz NOT NULL DEFAULT now(),
        CHECK (coalesce((container_sha256 IS NULL AND entry_ordinal IS NULL AND entry_name IS NULL)
               OR (container_sha256 IS NOT NULL AND entry_ordinal IS NOT NULL AND entry_name IS NOT NULL
                   AND container_sha256 ~ '^[0-9a-f]{64}$' AND entry_ordinal >= 1 AND entry_name <> ''), false)),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, phien_ban_id) REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id),
        FOREIGN KEY (lan_tiep_nhan_id, source_instance_id, snapshot_id) REFERENCES giao_tiep.lan_tiep_nhan_nguon (id, source_instance_id, snapshot_id),
        FOREIGN KEY (source_row_id, snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        FOREIGN KEY (company_mapping_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (lan_tiep_nhan_id, observation_key),
        UNIQUE (hoa_don_id, thu_tu),
        UNIQUE (phap_nhan_id, hoa_don_id, id),
        UNIQUE (phap_nhan_id, hoa_don_id, id, phien_ban_id))""",
    """ALTER TABLE kho.hoa_don_quan_sat ADD CONSTRAINT hoa_don_quan_sat_predecessor_fk
        FOREIGN KEY (phap_nhan_id, hoa_don_id, predecessor_observation_id) REFERENCES kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id)""",
    """ALTER TABLE kho.hoa_don_danh_tinh
        ADD CONSTRAINT hoa_don_latest_cung_hd FOREIGN KEY (phap_nhan_id, id, latest_observation_id)
            REFERENCES kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id) DEFERRABLE INITIALLY DEFERRED,
        ADD CONSTRAINT hoa_don_accepted_cung_hd FOREIGN KEY (phap_nhan_id, id, accepted_source_observation_id)
            REFERENCES kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id) DEFERRABLE INITIALLY DEFERRED,
        ADD CONSTRAINT hoa_don_eligible_cung_hd FOREIGN KEY (phap_nhan_id, id, eligible_content_id)
            REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id) DEFERRABLE INITIALLY DEFERRED""",
    """CREATE TABLE kho.hoa_don_dong_danh_tinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        logical_line_key text NOT NULL CHECK (logical_line_key ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        identity_evidence_id uuid NOT NULL REFERENCES kho.ban_ghi_nguon(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        created_by text NOT NULL,
        FOREIGN KEY (phap_nhan_id, hoa_don_id) REFERENCES kho.hoa_don_danh_tinh (phap_nhan_id, id),
        UNIQUE (phap_nhan_id, id, hoa_don_id),
        UNIQUE (phap_nhan_id, hoa_don_id, logical_line_key))""",
    # mapping COMPANY / INVOICE_LINE trên bảng mapping trung tính (WAREHOUSE giữ nguyên): target typed đúng một loại + FK cùng PN
    "ALTER TABLE master.anh_xa_nguon DROP CONSTRAINT anh_xa_nguon_subject_kind_check",
    "ALTER TABLE master.anh_xa_nguon ADD CONSTRAINT anh_xa_nguon_subject_kind_m2_check CHECK (subject_kind IN ('WAREHOUSE','COMPANY','INVOICE_LINE'))",
    """ALTER TABLE master.anh_xa_nguon
        ADD COLUMN target_hoa_don_id uuid,
        ADD COLUMN target_dong_danh_tinh_id uuid,
        ADD COLUMN line_phien_ban_id uuid,
        ADD COLUMN line_source_row_id uuid,
        ADD COLUMN line_native_xml_sha256 text,
        ADD COLUMN line_container_sha256 text,
        ADD COLUMN line_entry_ordinal integer,
        ADD COLUMN line_entry_name text,
        ADD COLUMN line_source_locator text,
        ADD COLUMN line_source_ordinal integer,
        ADD COLUMN line_identity_binding text[],
        ADD COLUMN line_ung_vien_id uuid REFERENCES master.m2_ung_vien_dong(id)""",
    # S1: hình dạng hai trị tường minh (IS NOT NULL từng cột + coalesce(...,false)) — không để UNKNOWN thỏa CHECK; XML: bộ ZIP all NULL, ZIP: all present
    """ALTER TABLE master.anh_xa_nguon ADD CONSTRAINT anh_xa_nguon_target_m2_check CHECK (coalesce(
        (subject_kind = 'INVOICE_LINE' AND target_hoa_don_id IS NOT NULL AND target_dong_danh_tinh_id IS NOT NULL AND line_phien_ban_id IS NOT NULL
             AND line_source_row_id IS NOT NULL AND line_native_xml_sha256 IS NOT NULL AND line_native_xml_sha256 ~ '^[0-9a-f]{64}$'
             AND line_source_locator IS NOT NULL AND line_source_locator <> '' AND line_source_ordinal IS NOT NULL AND line_source_ordinal >= 1
             AND line_ung_vien_id IS NOT NULL
             AND line_identity_binding IS NOT NULL AND cardinality(line_identity_binding) = 6 AND array_position(line_identity_binding, NULL) IS NULL
             AND NOT ('' = ANY (line_identity_binding))
             AND ((line_container_sha256 IS NULL AND line_entry_ordinal IS NULL AND line_entry_name IS NULL)
                  OR (line_container_sha256 IS NOT NULL AND line_entry_ordinal IS NOT NULL AND line_entry_name IS NOT NULL
                      AND line_container_sha256 ~ '^[0-9a-f]{64}$' AND line_entry_ordinal >= 1 AND line_entry_name <> '')))
        OR (subject_kind <> 'INVOICE_LINE' AND target_hoa_don_id IS NULL AND target_dong_danh_tinh_id IS NULL AND line_phien_ban_id IS NULL
             AND line_source_row_id IS NULL AND line_native_xml_sha256 IS NULL AND line_container_sha256 IS NULL AND line_entry_ordinal IS NULL
             AND line_entry_name IS NULL AND line_source_locator IS NULL AND line_source_ordinal IS NULL AND line_identity_binding IS NULL
             AND line_ung_vien_id IS NULL), false))""",
    """ALTER TABLE master.anh_xa_nguon
        ADD CONSTRAINT anh_xa_nguon_target_dong_m2_fk FOREIGN KEY (phap_nhan_id, target_dong_danh_tinh_id, target_hoa_don_id)
            REFERENCES kho.hoa_don_dong_danh_tinh (phap_nhan_id, id, hoa_don_id),
        ADD CONSTRAINT anh_xa_nguon_target_pb_m2_fk FOREIGN KEY (phap_nhan_id, target_hoa_don_id, line_phien_ban_id)
            REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id),
        ADD CONSTRAINT anh_xa_nguon_line_row_m2_fk FOREIGN KEY (line_source_row_id) REFERENCES kho.ban_ghi_nguon (id)""",
    # trigger mapping (thay thế, cùng tên): module theo loại subject — WAREHOUSE → M5 (giữ nguyên nghĩa cũ), COMPANY/INVOICE_LINE → M2; target bất biến
    """CREATE OR REPLACE FUNCTION master.anh_xa_nguon_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); chu boolean := master.la_chu_bang(TG_RELID::regclass); k record; v_mod text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'ANH_XA_BAT_BIEN: không xóa mapping' USING ERRCODE = 'P0001';
            END IF;
            v_mod := CASE WHEN NEW.subject_kind = 'WAREHOUSE' THEN 'M5' ELSE 'M2' END;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(NEW.id, NEW.reference_id, NEW.revision, NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, NEW.subject_kind, NEW.subject_key,
                       NEW.phap_nhan_id, NEW.valid_from, NEW.thay_cho_id, NEW.nguon_quyet_dinh, NEW.duyet_boi, NEW.ly_do, NEW.known_at_server,
                       NEW.target_hoa_don_id, NEW.target_dong_danh_tinh_id, NEW.line_phien_ban_id, NEW.line_source_row_id, NEW.line_native_xml_sha256,
                       NEW.line_container_sha256, NEW.line_entry_ordinal, NEW.line_entry_name, NEW.line_source_locator, NEW.line_source_ordinal,
                       NEW.line_identity_binding, NEW.line_ung_vien_id)
                   IS DISTINCT FROM ROW(OLD.id, OLD.reference_id, OLD.revision, OLD.source_instance_id, OLD.profile_ref, OLD.profile_sha256, OLD.subject_kind,
                       OLD.subject_key, OLD.phap_nhan_id, OLD.valid_from, OLD.thay_cho_id, OLD.nguon_quyet_dinh, OLD.duyet_boi, OLD.ly_do, OLD.known_at_server,
                       OLD.target_hoa_don_id, OLD.target_dong_danh_tinh_id, OLD.line_phien_ban_id, OLD.line_source_row_id, OLD.line_native_xml_sha256,
                       OLD.line_container_sha256, OLD.line_entry_ordinal, OLD.line_entry_name, OLD.line_source_locator, OLD.line_source_ordinal,
                       OLD.line_identity_binding, OLD.line_ung_vien_id)
                   OR OLD.state <> 'DA_DUYET' OR NEW.state <> 'DONG' OR NEW.valid_to IS NULL OR OLD.valid_to IS NOT NULL THEN
                    RAISE EXCEPTION 'ANH_XA_BAT_BIEN: chỉ đóng hiệu lực mapping một lần, không sửa/mở lại' USING ERRCODE = 'P0001';
                END IF;
                IF NOT chu OR ai IS NULL OR NOT master.ktt_duoc(OLD.phap_nhan_id, v_mod) OR NOT master.ktt_co_vai(OLD.phap_nhan_id, ARRAY['CFO'], 'V4')
                   OR NOT master.ktt_nguon_duoc(OLD.source_instance_id, OLD.profile_ref, OLD.profile_sha256, 'SOURCE_MAP', OLD.phap_nhan_id) THEN
                    RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: đóng mapping chỉ qua hàm định nghĩa, cần SOURCE_MAP đúng PN + CFO V4 + % của phiên', v_mod
                        USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT chu THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping chỉ ghi qua đường định nghĩa của chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.nguon_quyet_dinh = 'CFO_V4' THEN
                IF ai IS NULL OR ai IS DISTINCT FROM NEW.duyet_boi OR NOT master.ktt_duoc(NEW.phap_nhan_id, v_mod)
                   OR NOT master.ktt_co_vai(NEW.phap_nhan_id, ARRAY['CFO'], 'V4')
                   OR NOT master.ktt_nguon_duoc(NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, 'SOURCE_MAP', NEW.phap_nhan_id) THEN
                    RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping cần đồng thời SOURCE_MAP (instance/profile → PN đích) và CFO V4 + % của phiên', v_mod
                        USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.nguon_quyet_dinh <> 'ROOT_SEED_DEMO' OR NEW.duyet_boi <> 'ROOT_SEED_DEMO' OR NEW.subject_kind = 'INVOICE_LINE' THEN
                RAISE EXCEPTION 'ANH_XA_SEED_SAI: INVOICE_LINE chỉ do CFO duyệt trong workflow mapping dòng, không seed' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.state <> 'DA_DUYET' OR NEW.valid_to IS NOT NULL THEN
                RAISE EXCEPTION 'ANH_XA_MOI_PHAI_DANG_HIEU_LUC' USING ERRCODE = 'P0001';
            END IF;
            -- R2: mapping dòng phải bind ứng viên literal đã admit khớp đúng artifact/locator/ordinal/định danh/dòng logic đích (lớp phòng thủ thứ hai)
            IF NEW.subject_kind = 'INVOICE_LINE' AND NOT EXISTS (
                   SELECT 1 FROM master.m2_ung_vien_dong f JOIN kho.hoa_don_dong_danh_tinh x ON x.id = NEW.target_dong_danh_tinh_id
                   WHERE f.id = NEW.line_ung_vien_id AND f.source_instance_id = NEW.source_instance_id AND f.profile_ref = NEW.profile_ref
                     AND f.profile_sha256 = NEW.profile_sha256 AND f.native_xml_sha256 = NEW.line_native_xml_sha256
                     AND f.container_sha256 IS NOT DISTINCT FROM NEW.line_container_sha256 AND f.entry_ordinal IS NOT DISTINCT FROM NEW.line_entry_ordinal
                     AND f.entry_name IS NOT DISTINCT FROM NEW.line_entry_name AND f.source_ordinal = NEW.line_source_ordinal
                     AND f.identity_tuple = NEW.line_identity_binding AND f.logical_line_key = x.logical_line_key) THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_KHONG_KHOP: mapping dòng không khớp ứng viên literal đã admit' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('ANH_XA|' || NEW.source_instance_id || '|' || NEW.profile_ref || '|' || NEW.profile_sha256 || '|'
                                                           || NEW.subject_kind || '|' || NEW.subject_key, 0));
            SELECT * INTO k FROM master.anh_xa_nguon_noi_bo(NEW.source_instance_id, NEW.profile_ref, NEW.profile_sha256, NEW.subject_kind, NEW.subject_key,
                                                            NEW.valid_from);
            IF k.so_hieu_luc > 0 THEN
                RAISE EXCEPTION 'ANH_XA_CHONG_LAN: subject đã có mapping đang hiệu lực — đóng bản cũ (retarget có impact) trước' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.revision <> k.revision_max + 1 THEN
                RAISE EXCEPTION 'ANH_XA_REVISION_SAI: revision phải là % (expected revision đã đổi?)', k.revision_max + 1 USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE TABLE kho.hoa_don_dong_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        hoa_don_phien_ban_id uuid NOT NULL,
        dong_danh_tinh_id uuid NOT NULL,
        chung_tu_id uuid NOT NULL,
        source_dong_id uuid NOT NULL,
        source_row_id uuid NOT NULL,
        snapshot_id uuid NOT NULL,
        source_ordinal integer NOT NULL CHECK (source_ordinal >= 1),
        line_identity_mapping_id uuid NOT NULL,
        field_states jsonb NOT NULL,
        quantity_raw text,
        unit_raw text,
        unitprice_raw text,
        amount_raw text,
        quantity_exact numeric(38,12),
        unitprice_exact numeric(38,12),
        precision_state text NOT NULL CHECK (precision_state IN ('EXACT_21_6','INVALID','ABSENT','EMPTY','OVER_DOMAIN')),
        unit_definition_id uuid,
        unit_basis_sha256 text,
        nature_raw text,
        nature text NOT NULL CHECK (nature IN ('GOODS','PROMOTION','DISCOUNT','NOTE','SPECIAL_GOODS','UNKNOWN')),
        row_raw_sha256 text CHECK (row_raw_sha256 IS NULL),
        field_state_sha256 text NOT NULL CHECK (field_state_sha256 ~ '^[0-9a-f]{64}$'),
        created_at timestamptz NOT NULL DEFAULT now(),
        created_by text NOT NULL,
        CHECK (quantity_exact IS NULL OR precision_state = 'EXACT_21_6'),
        CHECK ((unit_definition_id IS NULL) = (unit_basis_sha256 IS NULL)),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, chung_tu_id) REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id, chung_tu_id),
        FOREIGN KEY (phap_nhan_id, dong_danh_tinh_id, hoa_don_id) REFERENCES kho.hoa_don_dong_danh_tinh (phap_nhan_id, id, hoa_don_id),
        FOREIGN KEY (chung_tu_id, source_dong_id, source_ordinal) REFERENCES kho.chung_tu_dong (chung_tu_id, id, stt),
        FOREIGN KEY (source_row_id, snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        FOREIGN KEY (line_identity_mapping_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        FOREIGN KEY (unit_definition_id, unit_basis_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        UNIQUE (phap_nhan_id, hoa_don_phien_ban_id, source_dong_id),
        UNIQUE (phap_nhan_id, hoa_don_phien_ban_id, dong_danh_tinh_id),
        UNIQUE (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, source_dong_id, dong_danh_tinh_id))""",
    """CREATE TABLE kho.mua_dich_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        hoa_don_phien_ban_id uuid NOT NULL,
        source_dong_id uuid NOT NULL,
        dong_danh_tinh_id uuid NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        dich text NOT NULL CHECK (dich IN ('CHI_PHI','XDCB_241','TAI_SAN','KHO')),
        hien_hanh boolean NOT NULL,
        trang_thai text NOT NULL CHECK (trang_thai IN ('NHAP','CHO_DUYET','DA_DUYET','THAY_THE','BO_QUA')),
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ '^[0-9a-f]{64}$'),
        crosswalk_mapping_id uuid NOT NULL,
        source_graph_sha256 text NOT NULL CHECK (source_graph_sha256 ~ '^[0-9a-f]{64}$'),
        predecessor_route_id uuid,
        actor_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        reason text NOT NULL CHECK (length(btrim(reason)) >= 1),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, source_dong_id, dong_danh_tinh_id)
            REFERENCES kho.hoa_don_dong_phien_ban (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, source_dong_id, dong_danh_tinh_id),
        FOREIGN KEY (crosswalk_mapping_id, phap_nhan_id) REFERENCES master.anh_xa_nguon (id, phap_nhan_id),
        UNIQUE (source_dong_id, phien_ban),
        UNIQUE (id, source_dong_id))""",
    """ALTER TABLE kho.mua_dich_dong ADD CONSTRAINT mua_dich_dong_predecessor_fk
        FOREIGN KEY (predecessor_route_id, source_dong_id) REFERENCES kho.mua_dich_dong (id, source_dong_id)""",
    "CREATE UNIQUE INDEX mua_dich_dong_hien_hanh_uq ON kho.mua_dich_dong (source_dong_id) WHERE hien_hanh",
    """CREATE VIEW kho.mua_dong_hien_hanh WITH (security_invoker = true) AS
        SELECT b.phap_nhan_id, b.hoa_don_id, b.hoa_don_phien_ban_id, b.source_dong_id, b.dong_danh_tinh_id, b.source_ordinal, b.field_states,
               b.quantity_raw, b.unit_raw, b.nature, r.id AS route_id, r.dich AS effective_dich, r.trang_thai AS route_state, r.phien_ban AS route_phien_ban
        FROM kho.hoa_don_dong_phien_ban b LEFT JOIN kho.mua_dich_dong r ON r.source_dong_id = b.source_dong_id AND r.hien_hanh""",
    # ---- guards M2: owner-only, chỉ thêm (trừ con trỏ danh tính và chuyển hien_hanh của tuyến); đồ thị cầu nối kiểm đủ trước khi ghi
    """CREATE OR REPLACE FUNCTION kho.m2_chi_chu_ghi_them() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'M2_BAT_BIEN: % chỉ ghi thêm', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M2_CHI_CHU: % chỉ do hàm định nghĩa của chủ bảng ghi', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hoa_don_phien_ban_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.hoa_don_phien_ban FOR EACH ROW EXECUTE FUNCTION kho.m2_chi_chu_ghi_them()",
    "CREATE TRIGGER hoa_don_quan_sat_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.hoa_don_quan_sat FOR EACH ROW EXECUTE FUNCTION kho.m2_chi_chu_ghi_them()",
    "CREATE TRIGGER hoa_don_dong_danh_tinh_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.hoa_don_dong_danh_tinh FOR EACH ROW EXECUTE FUNCTION kho.m2_chi_chu_ghi_them()",
    "CREATE TRIGGER hoa_don_dong_phien_ban_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.hoa_don_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION kho.m2_chi_chu_ghi_them()",
    """CREATE OR REPLACE FUNCTION kho.hoa_don_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE v int;
        BEGIN
            IF NEW.supersedes_id IS NOT NULL THEN
                SELECT phien_ban INTO v FROM kho.hoa_don_phien_ban WHERE id = NEW.supersedes_id AND hoa_don_id = NEW.hoa_don_id;
                IF v IS NULL OR v >= NEW.phien_ban THEN
                    RAISE EXCEPTION 'M2_PHIEN_BAN_VONG: supersedes phải là phiên bản trước của cùng hóa đơn' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hoa_don_phien_ban_kiem BEFORE INSERT ON kho.hoa_don_phien_ban FOR EACH ROW EXECUTE FUNCTION kho.hoa_don_phien_ban_kiem()",
    """CREATE OR REPLACE FUNCTION kho.hoa_don_con_tro_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE cu integer; moi integer; acc record;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M2_BAT_BIEN: không xóa danh tính hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M2_CHI_CHU: danh tính hóa đơn chỉ do hàm định nghĩa của chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.latest_observation_id IS NOT NULL OR NEW.accepted_source_observation_id IS NOT NULL OR NEW.eligible_content_id IS NOT NULL THEN
                    RAISE EXCEPTION 'M2_CON_TRO_SAI: danh tính mới chưa có con trỏ' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF (NEW.id, NEW.phap_nhan_id, NEW.chieu, NEW.mst_ban, NEW.mau_so, NEW.ky_hieu, NEW.so_chuan, NEW.source_instance_id, NEW.created_at, NEW.created_by)
               IS DISTINCT FROM (OLD.id, OLD.phap_nhan_id, OLD.chieu, OLD.mst_ban, OLD.mau_so, OLD.ky_hieu, OLD.so_chuan, OLD.source_instance_id, OLD.created_at,
                                 OLD.created_by) THEN
                RAISE EXCEPTION 'M2_BAT_BIEN: không đổi PN/chiều/định danh hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.latest_observation_id IS DISTINCT FROM OLD.latest_observation_id THEN
                SELECT thu_tu INTO cu FROM kho.hoa_don_quan_sat WHERE id = OLD.latest_observation_id;
                SELECT thu_tu INTO moi FROM kho.hoa_don_quan_sat WHERE id = NEW.latest_observation_id AND hoa_don_id = NEW.id;
                IF moi IS NULL OR (cu IS NOT NULL AND moi <= cu) THEN
                    RAISE EXCEPTION 'M2_CON_TRO_SAI: latest chỉ tiến theo thứ tự nhận' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.accepted_source_observation_id IS NOT NULL THEN
                SELECT o.phien_ban_id INTO acc FROM kho.hoa_don_quan_sat o WHERE o.id = NEW.accepted_source_observation_id AND o.hoa_don_id = NEW.id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'M2_CON_TRO_SAI: accepted phải là quan sát của chính hóa đơn' USING ERRCODE = 'P0001';
                END IF;
                IF NEW.eligible_content_id IS NOT NULL AND NEW.eligible_content_id IS DISTINCT FROM acc.phien_ban_id THEN
                    RAISE EXCEPTION 'M2_CON_TRO_SAI: eligible chỉ là nội dung của quan sát đã chấp nhận' USING ERRCODE = 'P0001';
                END IF;
            ELSIF NEW.eligible_content_id IS NOT NULL THEN
                RAISE EXCEPTION 'M2_CON_TRO_SAI: chưa có nguồn được chấp nhận' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hoa_don_con_tro_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.hoa_don_danh_tinh FOR EACH ROW EXECUTE FUNCTION kho.hoa_don_con_tro_kiem()",
    # đồ thị cầu nối: mapping INVOICE_LINE hiện hành đúng PN/hóa đơn/dòng logic/phiên bản/dòng nguồn/ordinal; dòng nguồn XML_LINE đúng snapshot/ordinal
    """CREATE OR REPLACE FUNCTION kho.hoa_don_dong_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM master.anh_xa_nguon m WHERE m.id = NEW.line_identity_mapping_id AND m.subject_kind = 'INVOICE_LINE'
                           AND m.state = 'DA_DUYET' AND m.valid_to IS NULL AND m.phap_nhan_id = NEW.phap_nhan_id AND m.target_hoa_don_id = NEW.hoa_don_id
                           AND m.target_dong_danh_tinh_id = NEW.dong_danh_tinh_id AND m.line_phien_ban_id = NEW.hoa_don_phien_ban_id
                           AND m.line_source_row_id = NEW.source_row_id AND m.line_source_ordinal = NEW.source_ordinal) THEN
                RAISE EXCEPTION 'M2_CAU_NOI_DO_THI: cần mapping INVOICE_LINE đã duyệt khớp đúng đồ thị' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM kho.ban_ghi_nguon b WHERE b.id = NEW.source_row_id AND b.snapshot_id = NEW.snapshot_id AND b.section = 'XML_LINE'
                           AND b.hash_basis = 'XML_DECODED_FIELD_STATES' AND (b.row_raw->>'source_ordinal')::integer = NEW.source_ordinal
                           AND b.derived_record_sha256 = NEW.field_state_sha256) THEN
                RAISE EXCEPTION 'M2_CAU_NOI_DO_THI: dòng nguồn XML_LINE không khớp snapshot/ordinal/digest' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hoa_don_dong_phien_ban_kiem BEFORE INSERT ON kho.hoa_don_dong_phien_ban FOR EACH ROW EXECUTE FUNCTION kho.hoa_don_dong_phien_ban_kiem()",
    """CREATE OR REPLACE FUNCTION kho.mua_dich_dong_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M2_BAT_BIEN: không xóa tuyến dòng' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M2_CHI_CHU: tuyến dòng chỉ do hàm định nghĩa của chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NOT NEW.hien_hanh OR NEW.trang_thai <> 'DA_DUYET' THEN
                    RAISE EXCEPTION 'M2_TUYEN_SAI: R15 chỉ ghi tuyến CFO tạo+duyệt hiện hành' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.hoa_don_id, NEW.hoa_don_phien_ban_id, NEW.source_dong_id, NEW.dong_danh_tinh_id, NEW.phien_ban, NEW.dich,
                   NEW.profile_sha256, NEW.crosswalk_mapping_id, NEW.source_graph_sha256, NEW.predecessor_route_id, NEW.actor_id, NEW.reason, NEW.recorded_at)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.hoa_don_id, OLD.hoa_don_phien_ban_id, OLD.source_dong_id, OLD.dong_danh_tinh_id,
                   OLD.phien_ban, OLD.dich, OLD.profile_sha256, OLD.crosswalk_mapping_id, OLD.source_graph_sha256, OLD.predecessor_route_id, OLD.actor_id,
                   OLD.reason, OLD.recorded_at)
               OR NOT (OLD.hien_hanh AND NOT NEW.hien_hanh AND OLD.trang_thai = 'DA_DUYET' AND NEW.trang_thai = 'THAY_THE') THEN
                RAISE EXCEPTION 'M2_BAT_BIEN: tuyến đã xác nhận chỉ chuyển hien_hanh→THAY_THE qua successor' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER mua_dich_dong_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.mua_dich_dong FOR EACH ROW EXECUTE FUNCTION kho.mua_dich_dong_kiem()",
    # ---- consumer capture COMMON (thay thế, cùng chữ ký): giữ nguyên mọi kiểm cũ; thêm (1) vai trò profile có allowed_media_types (M2: NATIVE
    #      xml|zip, CROSSWALK json) bên cạnh media_type đơn (M5 giữ nguyên quy tắc 1 media), (2) dòng dẫn xuất M2 mang hash_basis (digest do trigger tính).
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_tieu_thu_capture(p_stage uuid, p_h text)
        RETURNS TABLE (receipt_id uuid, snapshot_id uuid, moi boolean, snapshot_moi boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE
            ai text := master.ktt_danh_tinh(); s record; p jsonb; v_inst text; v_ref text; v_sha text; v_key text; cu record; snap uuid;
            moi_snap boolean := false; a jsonb; r jsonb; t uuid; tt record; prof jsonb; vai jsonb; thieu integer := 0; vr record;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage capture không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            IF ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '') THEN
                RAISE EXCEPTION 'STAGE_ACTOR_SAI: stage không thuộc danh tính phiên hiện tại' USING ERRCODE = 'P0001';
            END IF;
            v_inst := s.source_instance_id; v_ref := s.profile_ref; v_sha := s.profile_sha256; v_key := s.client_key; p := s.du_lieu;""" \
        + _KIEM_NGUON.format(i="v_inst", r="v_ref", s="v_sha", a="'INTAKE'", p="NULL") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('CAPTURE|' || v_inst || '|' || v_key, 0));
            SELECT l.id, l.capture_sha256, l.snapshot_id INTO cu FROM giao_tiep.lan_tiep_nhan_nguon l
                WHERE l.source_instance_id = v_inst AND l.khong_gian = 'CAPTURE' AND l.client_key = v_key;
            IF FOUND THEN
                IF cu.capture_sha256 IS DISTINCT FROM s.h THEN
                    RAISE EXCEPTION 'CAPTURE_KHAC_NOI_DUNG: khóa capture đã dùng cho nội dung/profile/scope/coverage/lỗi khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN QUERY SELECT cu.id, cu.snapshot_id, false, false;
                RETURN;
            END IF;
            IF p->'envelope'->>'contract' IS DISTINCT FROM 'm0-capture/v1' OR p->'envelope'->>'source_instance' IS DISTINCT FROM v_inst
               OR p->'envelope'->'source_profile'->>'reference_id' IS DISTINCT FROM v_ref OR p->'envelope'->'source_profile'->>'sha256' IS DISTINCT FROM v_sha
               OR p->'envelope'->'source_scope'->>'scope_ref' IS DISTINCT FROM p->>'scope_ref' OR p->'envelope'->>'coverage' IS DISTINCT FROM p->>'coverage'
               OR (SELECT coalesce(jsonb_agg(jsonb_build_object('role', f->>'role', 'raw_sha256', f->>'raw_sha256', 'byte_length', (f->>'byte_length')::bigint,
                                                                'media_type', f->>'media_type') ORDER BY f->>'role'), '[]'::jsonb)
                   FROM jsonb_array_elements(p->'roles') AS u(f) WHERE (f->>'co_mat')::boolean)
                  IS DISTINCT FROM
                  (SELECT coalesce(jsonb_agg(jsonb_build_object('role', e->>'role', 'raw_sha256', e->>'raw_sha256', 'byte_length', (e->>'byte_length')::bigint,
                                                                'media_type', e->>'media_type') ORDER BY e->>'role'), '[]'::jsonb)
                   FROM jsonb_array_elements(p->'envelope'->'artifacts') AS t(e)) THEN
                RAISE EXCEPTION 'STAGE_KHONG_NHAT_QUAN: envelope/vai trò của stage không khớp nhau' USING ERRCODE = 'P0001';
            END IF;
            SELECT np.payload INTO prof FROM master.nguon_profile np WHERE np.source_instance_id = v_inst AND np.profile_ref = v_ref AND np.profile_sha256 = v_sha;
            IF prof IS NULL THEN
                RAISE EXCEPTION 'NGUON_PROFILE_LA' USING ERRCODE = 'P0001';
            END IF;
            IF NOT (prof->'coverage_values') ? (p->>'coverage') OR NOT (prof->'coverage_values') ? (p->>'coverage_hieu_luc') THEN
                RAISE EXCEPTION 'NGUON_COVERAGE_LA: coverage ngoài profile' USING ERRCODE = 'P0001';
            END IF;
            IF (prof->>'module') IS DISTINCT FROM s.module AND NOT ((prof->>'module') IS NULL AND s.module IS NULL) THEN
                RAISE EXCEPTION 'STAGE_MODULE_SAI: module stage khác module profile' USING ERRCODE = 'P0001';
            END IF;
            FOR a IN SELECT * FROM jsonb_array_elements(p->'roles') LOOP
                SELECT e INTO vai FROM jsonb_array_elements(prof->'artifact_roles') AS t(e) WHERE e->>'role' = a->>'role';
                IF vai IS NULL THEN
                    RAISE EXCEPTION 'NGUON_VAI_TRO_LA: %', a->>'role' USING ERRCODE = 'P0001';
                END IF;
                IF (a->>'co_mat')::boolean AND NOT (
                       (vai ? 'allowed_media_types' AND jsonb_typeof(vai->'allowed_media_types') = 'array' AND (vai->'allowed_media_types') ? (a->>'media_type'))
                       OR (NOT vai ? 'allowed_media_types' AND a->>'media_type' IS NOT DISTINCT FROM vai->>'media_type')) THEN
                    RAISE EXCEPTION 'NGUON_MEDIA_SAI: %', a->>'role' USING ERRCODE = 'P0001';
                END IF;
                IF NOT (a->>'co_mat')::boolean THEN
                    thieu := thieu + 1;
                END IF;
            END LOOP;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(prof->'artifact_roles') AS t(e) WHERE NOT EXISTS (
                           SELECT 1 FROM jsonb_array_elements(p->'roles') AS u(f) WHERE f->>'role' = e->>'role'))
               OR (SELECT count(*) FROM jsonb_array_elements(p->'roles') AS u(f)) <> (SELECT count(DISTINCT f->>'role') FROM jsonb_array_elements(p->'roles') AS u(f)) THEN
                RAISE EXCEPTION 'NGUON_VAI_TRO_THIEU_KHAI_BAO: mọi vai trò profile phải có mặt hoặc ghi vắng' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.id INTO snap FROM kho.anh_chup_nguon x WHERE x.source_instance_id = v_inst AND x.profile_ref = v_ref AND x.profile_sha256 = v_sha
                AND x.bundle_sha256 = p->>'bundle_sha256';
            IF snap IS NOT NULL THEN
                FOR vr IN SELECT v.vai_tro, v.co_mat, v.raw_sha256, v.byte_length, v.media_type FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = snap LOOP
                    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p->'roles') AS u(f) WHERE f->>'role' = vr.vai_tro AND (f->>'co_mat')::boolean = vr.co_mat
                                   AND (f->>'raw_sha256') IS NOT DISTINCT FROM vr.raw_sha256 AND (f->>'byte_length')::bigint IS NOT DISTINCT FROM vr.byte_length
                                   AND (f->>'media_type') IS NOT DISTINCT FROM CASE WHEN vr.co_mat THEN vr.media_type END) THEN
                        RAISE EXCEPTION 'BUNDLE_XUNG_DOT: bundle đã lưu khác vai trò thực của lần nhận' USING ERRCODE = 'P0001';
                    END IF;
                END LOOP;
                IF (SELECT count(*) FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = snap) <> jsonb_array_length(p->'roles') THEN
                    RAISE EXCEPTION 'BUNDLE_XUNG_DOT: số vai trò khác' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                moi_snap := true;
                INSERT INTO kho.anh_chup_nguon (source_instance_id, profile_ref, profile_sha256, bundle_sha256, state, so_dong, nguoi)
                VALUES (v_inst, v_ref, v_sha, p->>'bundle_sha256', CASE WHEN thieu > 0 THEN 'THIEU_VAI_TRO' ELSE 'DU_VAI_TRO' END,
                        jsonb_array_length(coalesce(p->'rows', '[]'::jsonb)), ai)
                RETURNING id INTO snap;
                FOR a IN SELECT * FROM jsonb_array_elements(p->'roles') LOOP
                    t := NULL;
                    IF (a->>'co_mat')::boolean THEN
                        INSERT INTO giao_tiep.tep_tiep_nhan (source_instance_id, object_key, raw_sha256, byte_length, media_type, nguoi)
                        VALUES (v_inst, 'm0-raw/' || (a->>'raw_sha256'), a->>'raw_sha256', (a->>'byte_length')::bigint, a->>'media_type', ai)
                        ON CONFLICT (source_instance_id, raw_sha256) DO NOTHING RETURNING id INTO t;
                        IF t IS NULL THEN
                            SELECT x.id, x.byte_length, x.media_type INTO tt FROM giao_tiep.tep_tiep_nhan x
                                WHERE x.source_instance_id = v_inst AND x.raw_sha256 = a->>'raw_sha256';
                            IF tt.byte_length IS DISTINCT FROM (a->>'byte_length')::bigint OR tt.media_type IS DISTINCT FROM a->>'media_type' THEN
                                RAISE EXCEPTION 'RAW_METADATA_XUNG_DOT: cùng SHA khác độ dài/media' USING ERRCODE = 'P0001';
                            END IF;
                            t := tt.id;
                        END IF;
                    END IF;
                    INSERT INTO kho.anh_chup_nguon_vai_tro (snapshot_id, source_instance_id, vai_tro, co_mat, tep_tiep_nhan_id, raw_sha256, byte_length, media_type, ly_do_vang)
                    VALUES (snap, v_inst, a->>'role', (a->>'co_mat')::boolean, t,
                            CASE WHEN (a->>'co_mat')::boolean THEN a->>'raw_sha256' END,
                            CASE WHEN (a->>'co_mat')::boolean THEN (a->>'byte_length')::bigint END,
                            CASE WHEN (a->>'co_mat')::boolean THEN a->>'media_type' END, a->>'ly_do_vang');
                END LOOP;
                FOR r IN SELECT * FROM jsonb_array_elements(coalesce(p->'rows', '[]'::jsonb)) LOOP
                    INSERT INTO kho.ban_ghi_nguon (snapshot_id, source_instance_id, vai_tro, section, locator, thu_tu, source_key, row_raw, row_raw_sha256,
                        quantity_json_kind, quantity_text, validation_state, error_codes, hash_basis)
                    VALUES (snap, v_inst, r->>'vai_tro', r->>'section', r->>'locator', (r->>'thu_tu')::integer, r->>'source_key', r->'row_raw',
                        CASE WHEN r ? 'hash_basis' THEN NULL ELSE r->>'row_raw_sha256' END, r->>'quantity_json_kind', r->>'quantity_text', r->>'validation_state',
                        coalesce(ARRAY(SELECT jsonb_array_elements_text(r->'error_codes')), '{}'), r->>'hash_basis');
                END LOOP;
            END IF;
            INSERT INTO giao_tiep.lan_tiep_nhan_nguon (id, source_instance_id, client_key, capture_contract, capture_sha256, profile_ref, profile_sha256,
                scope_ref, source_scope, coverage, coverage_hieu_luc, reported_errors, snapshot_id, envelope, ket_qua, stage_id, actor_id, actor)
            VALUES ((p->>'receipt_id')::uuid, v_inst, v_key, 'm0-capture/v1', s.h, v_ref, v_sha, p->>'scope_ref', p->'envelope'->'source_scope',
                p->>'coverage', p->>'coverage_hieu_luc', coalesce(ARRAY(SELECT jsonb_array_elements_text(p->'envelope'->'reported_errors')), '{}'), snap,
                p->'envelope', p->'ket_qua', s.id, s.actor_id, ai);
            RETURN QUERY SELECT (p->>'receipt_id')::uuid, snap, true, moi_snap;
        END $$""",
    # ---- OP graph token (CAS, gồm quan sát/delivery hiện hành) và basis ngữ nghĩa của tuyến (KHÔNG gồm delivery-only)
    """CREATE OR REPLACE FUNCTION kho.m2_co_so_noi_bo(p_hoa_don uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        SELECT jsonb_build_object(
            'contract', 'm2-op-graph/v1',
            'hoa_don', jsonb_build_object('id', d.id, 'phap_nhan_id', d.phap_nhan_id,
                                          'identity', jsonb_build_array(d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan)),
            'con_tro', jsonb_build_object('latest', d.latest_observation_id, 'accepted', d.accepted_source_observation_id, 'eligible', d.eligible_content_id),
            'quan_sat', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'thu_tu', o.thu_tu, 'phien_ban_id', o.phien_ban_id, 'snapshot_id', o.snapshot_id,
                                     'native', o.native_xml_sha256, 'container', o.container_sha256, 'entry_ordinal', o.entry_ordinal,
                                     'classification', to_jsonb(o.classification), 'company_mapping_id', o.company_mapping_id) ORDER BY o.thu_tu), '[]'::jsonb)
                         FROM kho.hoa_don_quan_sat o WHERE o.hoa_don_id = d.id),
            'phien_ban', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', v.id, 'phien_ban', v.phien_ban, 'semantic', v.semantic_sha256,
                                      'chung_tu_id', v.chung_tu_id, 'profile_sha256', v.profile_sha256) ORDER BY v.phien_ban), '[]'::jsonb)
                          FROM kho.hoa_don_phien_ban v WHERE v.hoa_don_id = d.id),
            'anh_xa_dong', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', m.id, 'revision', m.revision, 'state', m.state, 'mo', m.valid_to IS NULL,
                                        'dong', m.target_dong_danh_tinh_id, 'phien_ban', m.line_phien_ban_id, 'ordinal', m.line_source_ordinal)
                                        ORDER BY m.subject_key, m.revision), '[]'::jsonb)
                            FROM master.anh_xa_nguon m WHERE m.target_hoa_don_id = d.id),
            'dong_logic', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', x.id, 'key', x.logical_line_key) ORDER BY x.logical_line_key), '[]'::jsonb)
                           FROM kho.hoa_don_dong_danh_tinh x WHERE x.hoa_don_id = d.id),
            'cau_noi', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', b.id, 'phien_ban', b.hoa_don_phien_ban_id, 'dong', b.source_dong_id,
                                    'logic', b.dong_danh_tinh_id, 'fs', b.field_state_sha256) ORDER BY b.hoa_don_phien_ban_id, b.source_ordinal), '[]'::jsonb)
                        FROM kho.hoa_don_dong_phien_ban b WHERE b.hoa_don_id = d.id),
            'tuyen', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', r.id, 'dong', r.source_dong_id, 'phien_ban', r.phien_ban, 'dich', r.dich,
                                  'trang_thai', r.trang_thai, 'hien_hanh', r.hien_hanh) ORDER BY r.source_dong_id, r.phien_ban), '[]'::jsonb)
                      FROM kho.mua_dich_dong r WHERE r.hoa_don_id = d.id),
            'cong_ty', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', m.id, 'revision', m.revision, 'state', m.state, 'mo', m.valid_to IS NULL,
                                    'pn', m.phap_nhan_id) ORDER BY m.id), '[]'::jsonb)
                        FROM master.anh_xa_nguon m WHERE m.id IN (SELECT o.company_mapping_id FROM kho.hoa_don_quan_sat o WHERE o.hoa_don_id = d.id)))
        FROM kho.hoa_don_danh_tinh d WHERE d.id = p_hoa_don
        $$""",
    """CREATE OR REPLACE FUNCTION kho.m2_co_so(p_hoa_don uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_pn uuid; b jsonb;
        BEGIN
            SELECT x.phap_nhan_id INTO v_pn FROM kho.hoa_don_danh_tinh x WHERE x.id = p_hoa_don;
            IF v_pn IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(v_pn, 'M2') THEN
                RETURN NULL;
            END IF;
            b := kho.m2_co_so_noi_bo(p_hoa_don);
            RETURN jsonb_build_object('graph_sha256', """ + _M2_TOKEN.format(x="b") + """);
        END $$""",
    # dòng XML_LINE (field states đã decode) của quan sát MỚI NHẤT — derivative theo PN + M2 cho bước mapping dòng; không cấp raw bytes/metadata nguồn
    """CREATE OR REPLACE FUNCTION kho.m2_dong_nguon(p_hoa_don uuid) RETURNS SETOF jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE d record; o record;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.latest_observation_id INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = p_hoa_don;
            IF d.id IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(d.phap_nhan_id, 'M2') THEN
                RETURN;
            END IF;
            SELECT q.* INTO o FROM kho.hoa_don_quan_sat q WHERE q.id = d.latest_observation_id;
            RETURN QUERY SELECT jsonb_build_object('source_row_id', b.id, 'locator', b.locator, 'source_ordinal', (b.row_raw->>'source_ordinal')::integer,
                                                   'fields', b.row_raw->'fields', 'quantity', b.row_raw->'quantity', 'nature', b.row_raw->>'nature',
                                                   'normalized_quantity_text', b.row_raw->>'normalized_quantity_text',
                                                   'unit_definition_ref', b.row_raw->>'unit_definition_ref', 'issues', b.row_raw->'issues',
                                                   'derived_record_sha256', b.derived_record_sha256, 'hash_basis', b.hash_basis, 'row_raw_sha256', b.row_raw_sha256)
                FROM kho.ban_ghi_nguon b
                WHERE b.snapshot_id = o.snapshot_id AND b.section = 'XML_LINE' AND b.row_raw->>'header_locator' = o.locator
                  AND b.row_raw->>'native_xml_sha256' = o.native_xml_sha256
                ORDER BY (b.row_raw->>'source_ordinal')::integer;
        END $$""",
    # R2: MỘT quy tắc đối chiếu ứng viên literal ↔ dòng/quan sát THỰC (dùng cho cả consumer mapping và danh sách ứng viên của chi tiết):
    #     instance/profile payload SHA/scope của lần nhận; company key → PN theo mapping công ty của quan sát; native SHA + độ dài thực; bộ ZIP
    #     (container SHA + độ dài vai trò NATIVE của snapshot, entry ordinal/name) hoặc all NULL; định danh 6 phần tự dẫn xuất; locator/ordinal.
    #     Trả NULL khi khớp, ngược lại mã từ chối cụ thể. Khóa dòng logic do caller so riêng. Nội bộ: không grant cho ứng dụng.
    """CREATE OR REPLACE FUNCTION kho.m2_ung_vien_khop_noi_bo(p_fact uuid, p_row uuid, p_obs uuid) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE f record; r record; o record; d record; l record; a record; m record; v_pn_ma text; v_len bigint;
        BEGIN
            SELECT * INTO f FROM master.m2_ung_vien_dong x WHERE x.id = p_fact;
            IF f.id IS NULL THEN
                RETURN 'M2_UNG_VIEN_KHONG_CO';
            END IF;
            SELECT * INTO r FROM kho.ban_ghi_nguon x WHERE x.id = p_row;
            SELECT * INTO o FROM kho.hoa_don_quan_sat x WHERE x.id = p_obs;
            IF r.id IS NULL OR o.id IS NULL OR r.snapshot_id IS DISTINCT FROM o.snapshot_id THEN
                RETURN 'M2_DONG_NGUON_KHONG_HIEN_HANH';
            END IF;
            SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = o.hoa_don_id;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = o.lan_tiep_nhan_id;
            SELECT * INTO a FROM kho.anh_chup_nguon x WHERE x.id = o.snapshot_id;
            SELECT * INTO m FROM master.anh_xa_nguon x WHERE x.id = o.company_mapping_id;
            SELECT x.ma INTO v_pn_ma FROM master.phap_nhan x WHERE x.id = d.phap_nhan_id;
            IF f.source_instance_id IS DISTINCT FROM a.source_instance_id OR f.profile_ref IS DISTINCT FROM a.profile_ref
               OR f.profile_sha256 IS DISTINCT FROM a.profile_sha256 OR f.scope_ref IS DISTINCT FROM l.scope_ref THEN
                RETURN 'M2_UNG_VIEN_SAI_NGUON';
            END IF;
            IF f.company_key IS DISTINCT FROM m.subject_key OR m.phap_nhan_id IS DISTINCT FROM d.phap_nhan_id OR f.phap_nhan_ma IS DISTINCT FROM v_pn_ma THEN
                RETURN 'M2_UNG_VIEN_SAI_PHAP_NHAN';
            END IF;
            IF f.native_xml_sha256 IS DISTINCT FROM o.native_xml_sha256 OR f.native_xml_sha256 IS DISTINCT FROM r.row_raw->>'native_xml_sha256'
               OR f.native_byte_length IS DISTINCT FROM (r.row_raw->>'byte_length')::bigint
               OR f.container_sha256 IS DISTINCT FROM o.container_sha256 OR f.entry_ordinal IS DISTINCT FROM o.entry_ordinal
               OR f.entry_name IS DISTINCT FROM o.entry_name THEN
                RETURN 'M2_UNG_VIEN_SAI_ARTIFACT';
            END IF;
            IF f.container_sha256 IS NOT NULL THEN
                SELECT v.byte_length INTO v_len FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = o.snapshot_id AND v.vai_tro = 'NATIVE' AND v.co_mat
                    AND v.raw_sha256 = f.container_sha256;
                IF v_len IS DISTINCT FROM f.container_byte_length THEN
                    RETURN 'M2_UNG_VIEN_SAI_ARTIFACT';
                END IF;
            END IF;
            IF f.identity_tuple IS DISTINCT FROM ARRAY[v_pn_ma, d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan] THEN
                RETURN 'M2_UNG_VIEN_SAI_DINH_DANH';
            END IF;
            IF f.source_locator IS DISTINCT FROM r.row_raw->>'source_locator' OR f.source_ordinal IS DISTINCT FROM (r.row_raw->>'source_ordinal')::integer THEN
                RETURN 'M2_UNG_VIEN_SAI_VI_TRI';
            END IF;
            RETURN NULL;
        END $$""",
    # danh sách ứng viên khớp dòng XML_LINE hiện hành của hóa đơn (quyền M2 hiện hành trên PN): chỉ ref/revision/dòng logic đích — không raw bundle
    """CREATE OR REPLACE FUNCTION kho.m2_ung_vien_hien_hanh(p_hoa_don uuid) RETURNS SETOF jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE d record; o record;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.latest_observation_id INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = p_hoa_don;
            IF d.id IS NULL OR master.ktt_danh_tinh() IS NULL OR NOT master.ktt_duoc(d.phap_nhan_id, 'M2') THEN
                RETURN;
            END IF;
            SELECT q.* INTO o FROM kho.hoa_don_quan_sat q WHERE q.id = d.latest_observation_id;
            IF o.id IS NULL THEN
                RETURN;
            END IF;
            RETURN QUERY SELECT jsonb_build_object('source_row_id', b.id, 'evidence_ref', f.mapping_ref, 'evidence_revision', f.revision,
                                                   'logical_line_key', f.logical_line_key, 'authority', 'CANDIDATE_EVIDENCE_NOT_APPROVAL')
                FROM kho.ban_ghi_nguon b JOIN master.m2_ung_vien_dong f ON f.native_xml_sha256 = o.native_xml_sha256
                WHERE b.snapshot_id = o.snapshot_id AND b.section = 'XML_LINE' AND b.row_raw->>'header_locator' = o.locator
                  AND b.row_raw->>'native_xml_sha256' = o.native_xml_sha256 AND kho.m2_ung_vien_khop_noi_bo(f.id, b.id, o.id) IS NULL
                ORDER BY (b.row_raw->>'source_ordinal')::integer, f.mapping_ref, f.revision;
        END $$""",
    # basis ngữ nghĩa tuyến: nội dung/định danh/dòng logic/facts dòng nguồn/mapping dòng đã duyệt/đơn vị/profile — không gồm quan sát delivery
    """CREATE OR REPLACE FUNCTION kho.m2_basis_tuyen_noi_bo(p_cau_noi uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT """ + _M2_TOKEN.format(x="""jsonb_build_object('contract', 'm2-route-basis/v1', 'semantic', v.semantic_sha256, 'phien_ban_id', v.id,
                   'profile_sha256', v.profile_sha256, 'identity', jsonb_build_array(d.phap_nhan_id, d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan),
                   'logic', jsonb_build_object('id', x.id, 'key', x.logical_line_key), 'dong_nguon', b.source_dong_id, 'ordinal', b.source_ordinal,
                   'field_state_sha256', b.field_state_sha256, 'quantity_raw', b.quantity_raw, 'unit_raw', b.unit_raw, 'nature', b.nature,
                   'unit_definition', jsonb_build_object('id', b.unit_definition_id, 'sha', b.unit_basis_sha256),
                   'mapping', jsonb_build_object('id', m.id, 'revision', m.revision, 'state', m.state, 'mo', m.valid_to IS NULL))""") + """
        FROM kho.hoa_don_dong_phien_ban b
        JOIN kho.hoa_don_phien_ban v ON v.id = b.hoa_don_phien_ban_id
        JOIN kho.hoa_don_danh_tinh d ON d.id = b.hoa_don_id
        JOIN kho.hoa_don_dong_danh_tinh x ON x.id = b.dong_danh_tinh_id
        JOIN master.anh_xa_nguon m ON m.id = b.line_identity_mapping_id
        WHERE b.id = p_cau_noi
        $$""",
    # ---- consumer typed M2: chỉ stage ID + H của stage module M2 do chủ bảng ghi; facts đọc từ stage; kiểm actor/INTAKE/biên nhận/mapping công ty
    #      hiện hành; khóa danh tính; dedup nội dung theo semantic; core HD_MUA M2 + dòng NULL tiền; quan sát mỗi delivery; con trỏ theo lifecycle.
    """CREATE OR REPLACE FUNCTION kho.m2_tieu_thu_quan_sat(p_stage uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE
            ai text := master.ktt_danh_tinh(); s record; l record; it jsonb; m record; v_pn_ma text; d record; v_pb uuid; v_moi boolean; v_hdr uuid;
            v_ct uuid; dl jsonb; v_obs uuid; v_thu_tu integer; v_prof uuid; latest record; v_ver integer; v_cls text; v_acc_pb uuid; out jsonb := '[]'::jsonb;
            v_ngay date; v_sup uuid;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h OR s.module IS DISTINCT FROM 'M2' THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage capture M2 không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            IF ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: promote cần INTAKE hiện hành của đúng phiên đã tạo stage' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.stage_id = s.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'STAGE_CHUA_CAPTURE: phải tiêu thụ capture của chính stage trước' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM kho.hoa_don_quan_sat o WHERE o.lan_tiep_nhan_id = l.id) THEN
                RETURN jsonb_build_object('lap_lai', true);
            END IF;
            SELECT np.id INTO v_prof FROM master.nguon_profile np WHERE np.source_instance_id = l.source_instance_id AND np.profile_ref = l.profile_ref
                AND np.profile_sha256 = l.profile_sha256;
            FOR it IN SELECT * FROM jsonb_array_elements(coalesce(s.du_lieu->'promote_m2', '[]'::jsonb)) LOOP
                SELECT * INTO m FROM master.anh_xa_nguon x WHERE x.id = (it->>'company_mapping_id')::uuid AND x.subject_kind = 'COMPANY'
                    AND x.subject_key = it->>'company_key' AND x.source_instance_id = l.source_instance_id AND x.profile_ref = l.profile_ref
                    AND x.profile_sha256 = l.profile_sha256 AND x.state = 'DA_DUYET' AND x.valid_from <= now() AND (x.valid_to IS NULL OR x.valid_to > now())
                    FOR SHARE;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'M2_MAPPING_CONG_TY_DOI: mapping công ty hiện hành đã đổi' USING ERRCODE = 'P0001';
                END IF;
                SELECT ma INTO v_pn_ma FROM master.phap_nhan WHERE id = m.phap_nhan_id;
                IF it->>'direction' IS DISTINCT FROM 'MUA_VAO' OR it->'identity'->>0 IS DISTINCT FROM v_pn_ma OR it->'identity'->>1 IS DISTINCT FROM 'MUA_VAO'
                   OR jsonb_array_length(it->'identity') <> 6 THEN
                    RAISE EXCEPTION 'M2_KE_HOACH_SAI: chỉ MUA_VAO của đúng PN mapping công ty vào M2' USING ERRCODE = 'P0001';
                END IF;
                SELECT b.id INTO v_hdr FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = l.snapshot_id AND b.section = 'XML_HEADER' AND b.locator = it->>'header_locator'
                    AND b.hash_basis = 'XML_DECODED_FIELD_STATES' AND b.row_raw->>'native_xml_sha256' = it->>'native_xml_sha256';
                IF v_hdr IS NULL THEN
                    RAISE EXCEPTION 'M2_THIEU_DONG_NGUON: header' USING ERRCODE = 'P0001';
                END IF;
                v_ngay := (it->>'ngay_lap')::date;
                PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON|' || m.phap_nhan_id || '|' || (it->'identity')::text, 0));
                INSERT INTO kho.hoa_don_danh_tinh (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan, source_instance_id, created_by)
                VALUES (m.phap_nhan_id, 'MUA_VAO', it->'identity'->>2, it->'identity'->>3, it->'identity'->>4, it->'identity'->>5, l.source_instance_id, ai)
                ON CONFLICT (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan) DO NOTHING;
                SELECT x.id INTO d FROM kho.hoa_don_danh_tinh x WHERE x.phap_nhan_id = m.phap_nhan_id AND x.chieu = 'MUA_VAO' AND x.mst_ban = it->'identity'->>2
                    AND x.mau_so = it->'identity'->>3 AND x.ky_hieu = it->'identity'->>4 AND x.so_chuan = it->'identity'->>5;
                -- cùng thứ tự với thao tác nghiệp vụ: advisory gốc hóa đơn → hàng danh tính
                PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || d.id, 0));
                SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = d.id FOR UPDATE;
                SELECT o.id, o.phien_ban_id INTO latest FROM kho.hoa_don_quan_sat o WHERE o.id = d.latest_observation_id;
                SELECT v.id INTO v_pb FROM kho.hoa_don_phien_ban v WHERE v.hoa_don_id = d.id AND v.semantic_sha256 = it->>'semantic_sha256';
                v_moi := v_pb IS NULL;
                IF v_moi THEN
                    SELECT coalesce(max(v.phien_ban), 0) + 1 INTO v_ver FROM kho.hoa_don_phien_ban v WHERE v.hoa_don_id = d.id;
                    v_sup := latest.phien_ban_id;
                    INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, mo_ta, du_lieu, hash, ky, trang_thai, module_nghiep_vu)
                    VALUES (d.phap_nhan_id, 'HD_MUA', 'M2:' || d.id || ':' || (it->>'semantic_sha256'), v_ngay,
                            'Hóa đơn mua XML (M2) — nguồn, chưa hạch toán/tiền chưa có căn cứ',
                            jsonb_build_object('m2_hoa_don_id', d.id, 'semantic_sha256', it->>'semantic_sha256', 'tien_te_nguon', it->>'tien_te',
                                               'identity', it->'identity'),
                            it->>'semantic_sha256', to_char(v_ngay, 'YYYY-MM'), 'DANG_XU_LY', 'M2')
                    RETURNING id INTO v_ct;
                    INSERT INTO kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, phien_ban, semantic_contract, semantic_sha256, profile_id, profile_sha256,
                        company_mapping_id, snapshot_id, header_source_row_id, raw_header_states, ngay_lap, tien_te, raw_components, money_basis_state,
                        chung_tu_id, supersedes_id)
                    VALUES (d.phap_nhan_id, d.id, v_ver, 'M2_XML_CONTENT_V1', it->>'semantic_sha256', v_prof, l.profile_sha256, m.id, l.snapshot_id, v_hdr,
                            it->'raw_header_states', v_ngay, it->>'tien_te', coalesce(it->'raw_components', '{}'::jsonb), 'UNPROVEN_NO_MINOR', v_ct, v_sup)
                    RETURNING id INTO v_pb;
                    FOR dl IN SELECT * FROM jsonb_array_elements(coalesce(it->'lines', '[]'::jsonb)) LOOP
                        INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, so_luong, no_minor, co_minor, du_lieu)
                        VALUES (v_ct, (dl->>'source_ordinal')::integer, dl->>'mo_ta', (dl->>'so_luong_chuan_hoa')::numeric(38,12), NULL, NULL,
                                jsonb_build_object('locator', dl->>'locator', 'so_luong_nguon', dl->>'quantity_raw', 'dvt_nguon', dl->>'unit_raw',
                                                   'tinh_chat', dl->>'nature', 'm2_phien_ban_id', v_pb));
                    END LOOP;
                END IF;
                IF d.latest_observation_id IS NULL THEN
                    v_cls := 'FIRST_OBSERVATION';
                ELSIF latest.phien_ban_id = v_pb THEN
                    v_cls := 'SAME_CONTENT_REPEAT';
                ELSIF EXISTS (SELECT 1 FROM kho.hoa_don_quan_sat o WHERE o.hoa_don_id = d.id AND o.phien_ban_id = v_pb) THEN
                    v_cls := 'ANCESTOR_REAPPEARANCE_HOLD';
                ELSE
                    v_cls := 'CHANGED_CONTENT_HOLD';
                END IF;
                SELECT coalesce(max(o.thu_tu), 0) + 1 INTO v_thu_tu FROM kho.hoa_don_quan_sat o WHERE o.hoa_don_id = d.id;
                INSERT INTO kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, phien_ban_id, lan_tiep_nhan_id, source_instance_id, snapshot_id, source_row_id,
                    native_xml_sha256, container_sha256, entry_ordinal, entry_name, locator, observation_key, thu_tu, predecessor_observation_id,
                    classification, company_mapping_id)
                VALUES (d.phap_nhan_id, d.id, v_pb, l.id, l.source_instance_id, l.snapshot_id, v_hdr, it->>'native_xml_sha256', it->>'container_sha256',
                        (it->>'entry_ordinal')::integer, it->>'entry_name', it->>'header_locator', it->>'delivery_key', v_thu_tu, d.latest_observation_id,
                        ARRAY[v_cls] || coalesce(ARRAY(SELECT jsonb_array_elements_text(it->'issue_codes')), '{}'), m.id)
                RETURNING id INTO v_obs;
                SELECT o.phien_ban_id INTO v_acc_pb FROM kho.hoa_don_quan_sat o WHERE o.id = d.accepted_source_observation_id;
                IF v_cls = 'FIRST_OBSERVATION' THEN
                    UPDATE kho.hoa_don_danh_tinh SET latest_observation_id = v_obs, accepted_source_observation_id = v_obs, eligible_content_id = v_pb WHERE id = d.id;
                ELSIF v_cls = 'SAME_CONTENT_REPEAT' THEN
                    UPDATE kho.hoa_don_danh_tinh SET latest_observation_id = v_obs,
                        accepted_source_observation_id = CASE WHEN v_acc_pb = v_pb THEN v_obs ELSE accepted_source_observation_id END WHERE id = d.id;
                ELSE
                    UPDATE kho.hoa_don_danh_tinh SET latest_observation_id = v_obs, eligible_content_id = NULL WHERE id = d.id;
                END IF;
                INSERT INTO giao_tiep.tep_tach_phap_nhan (snapshot_id, source_instance_id, phap_nhan_id, module, mapping_revision_id, selected_rows_sha256,
                    transformation_profile)
                VALUES (l.snapshot_id, l.source_instance_id, d.phap_nhan_id, 'M2', m.id,
                        (SELECT encode(sha256(convert_to(string_agg(b.derived_record_sha256, ',' ORDER BY b.thu_tu), 'UTF8')), 'hex') FROM kho.ban_ghi_nguon b
                         WHERE b.snapshot_id = l.snapshot_id AND (b.id = v_hdr OR b.locator IN (SELECT jsonb_array_elements_text(it->'line_locators')))),
                        'm2-xml-promote/v1')
                ON CONFLICT DO NOTHING;
                out := out || jsonb_build_object('delivery_key', it->>'delivery_key', 'observation_id', v_obs, 'hoa_don_id', d.id, 'phien_ban_id', v_pb,
                                                 'phap_nhan_id', d.phap_nhan_id, 'phien_ban_moi', v_moi, 'classification', v_cls);
            END LOOP;
            RETURN jsonb_build_object('lap_lai', false, 'items', out);
        END $$""",
    # ---- finalizer capture (thay thế, cùng chữ ký): giữ nguyên nhánh M5; nhánh M2 TỰ dẫn xuất danh sách kết quả từ CSDL cùng giao dịch (không nhận refs)
    """CREATE OR REPLACE FUNCTION giao_tiep.nguon_chot_ket_qua(p_stage uuid, p_h text, p_snapshot_moi boolean, p_promote jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE s record; l record; o record; t text; sp jsonb; v_pn uuid; v_khac boolean; v_kq jsonb;
        BEGIN
            IF NOT master.la_chu_bang('giao_tiep.ket_qua_cuoi_tiep_nhan'::regclass) THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_CHI_CHU: chỉ máy chủ cấu hình (chủ bảng) chốt kết quả lần nhận' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'CAPTURE';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h OR master.ktt_danh_tinh() IS NULL OR s.actor IS DISTINCT FROM master.ktt_danh_tinh()
               OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: chốt kết quả cần INTAKE hiện hành của đúng phiên đã tạo stage' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.stage_id = s.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'STAGE_CHUA_CAPTURE: phải tiêu thụ capture của chính stage trước' USING ERRCODE = 'P0001';
            END IF;
            IF p_snapshot_moi IS NULL OR jsonb_typeof(p_promote) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: thiếu snapshot_moi/promote' USING ERRCODE = 'P0001';
            END IF;
            v_khac := EXISTS (SELECT 1 FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.snapshot_id = l.snapshot_id AND x.id <> l.id);
            IF p_snapshot_moi = v_khac THEN
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: snapshot_moi không khớp lịch sử bundle' USING ERRCODE = 'P0001';
            END IF;
            IF s.module = 'M2' THEN
                IF p_promote <> jsonb_build_object('module', 'M2') THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: kết quả M2 do CSDL dẫn xuất, không nhận refs từ caller' USING ERRCODE = 'P0001';
                END IF;
                v_kq := jsonb_build_object('module', 'M2', 'trang_thai', 'M2_DA_GHI',
                    'items', (SELECT coalesce(jsonb_agg(jsonb_build_object('observation_id', q.id, 'hoa_don_id', q.hoa_don_id, 'phien_ban_id', q.phien_ban_id,
                                                  'phap_nhan_id', q.phap_nhan_id, 'delivery_key', q.observation_key, 'classification', to_jsonb(q.classification))
                                                  ORDER BY q.observation_key), '[]'::jsonb)
                              FROM kho.hoa_don_quan_sat q WHERE q.lan_tiep_nhan_id = l.id),
                    'candidates', coalesce(s.du_lieu->'candidates_m2', '[]'::jsonb));
                INSERT INTO giao_tiep.ket_qua_cuoi_tiep_nhan (lan_tiep_nhan_id, stage_id, capture_sha256, snapshot_moi, promote, actor_id, actor)
                VALUES (l.id, s.id, l.capture_sha256, p_snapshot_moi, v_kq, s.actor_id, s.actor);
                RETURN jsonb_build_object('stage_id', s.id, 'snapshot_moi', p_snapshot_moi, 'promote', v_kq);
            END IF;
            t := p_promote->>'trang_thai';
            sp := s.du_lieu->'promote';
            IF sp IS NOT NULL AND jsonb_typeof(sp) <> 'object' THEN
                sp := NULL;
            END IF;
            SELECT q.id, q.phieu_id, q.content_id INTO o FROM kho.phieu_kho_quan_sat q WHERE q.lan_tiep_nhan_id = l.id;
            IF FOUND THEN
                IF t IS DISTINCT FROM 'DA_GHI_QUAN_SAT' OR p_promote->>'phieu_id' IS DISTINCT FROM o.phieu_id::text
                   OR p_promote->>'content_id' IS DISTINCT FROM o.content_id::text OR p_promote->>'observation_id' IS DISTINCT FROM o.id::text THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: refs quan sát không khớp CSDL' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO_UNG_VIEN' THEN
                IF sp IS NOT NULL THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: stage có kế hoạch promote, không phải ứng viên giữ chờ' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO_ANH_HUONG' THEN
                IF sp IS NULL OR sp->>'hold' IS NULL OR p_promote->'ly_do'->>0 IS DISTINCT FROM sp->>'hold' THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: HOLD ảnh hưởng không khớp stage' USING ERRCODE = 'P0001';
                END IF;
            ELSIF t = 'GIU_CHO' THEN
                SELECT m.phap_nhan_id INTO v_pn FROM master.anh_xa_nguon m WHERE m.id = (sp->>'mapping_revision_id')::uuid;
                IF sp IS NULL OR p_promote->>'ly_do' IS DISTINCT FROM 'KY_DA_KHOA'
                   OR NOT EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = v_pn AND k.ky = to_char((sp->>'ngay_chung_tu')::date, 'YYYY-MM')) THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: HOLD kỳ khóa không khớp kỳ thật' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                RAISE EXCEPTION 'KET_QUA_CUOI_SAI: trạng thái kết quả lạ' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO giao_tiep.ket_qua_cuoi_tiep_nhan (lan_tiep_nhan_id, stage_id, capture_sha256, snapshot_moi, promote, actor_id, actor)
            VALUES (l.id, s.id, l.capture_sha256, p_snapshot_moi, p_promote, s.actor_id, s.actor);
            RETURN jsonb_build_object('stage_id', s.id, 'snapshot_moi', p_snapshot_moi, 'promote', p_promote);
        END $$""",
    # ---- thao tác nghiệp vụ M2 (CFO, V4): quyền hiện hành TRƯỚC tra biên nhận; khóa namespace → gốc hóa đơn → hàng; token OP graph; biên nhận do DB dẫn xuất
    """CREATE OR REPLACE FUNCTION kho.m2_xem_xet_nguon(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d0 record; d record; o record; v_tok text; v_req jsonb; v_h text; cu record; v_ket jsonb; v_bn uuid;
        BEGIN
            SELECT x.id, x.phap_nhan_id INTO d0 FROM kho.hoa_don_danh_tinh x WHERE x.id = (p->>'hoa_don_id')::uuid;
            IF NOT FOUND OR ai IS NULL OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M2') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['CFO'], 'V4') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_M2_SOURCE_REVIEW: cần CFO có V4 + M2 của phiên trên PN của hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ '^[A-Za-z0-9_.:-]{1,200}$' OR coalesce(btrim(p->>'reason'), '') = '' THEN
                RAISE EXCEPTION 'M2_YEU_CAU_SAI: cần khóa và lý do' USING ERRCODE = 'P0001';
            END IF;
            -- R1: quyền HIỆN HÀNH (trên) → khóa namespace/gốc → biên nhận cùng khóa: cùng H của body gốc → trả nguyên kết quả (kể cả khi đồ thị đã
            --     đổi do chính lần đầu); khác H → IDEMPOTENCY_KHAC; chưa có biên nhận → yêu cầu MỚI mới CAS token đồ thị dưới khóa hóa đơn.
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M2|M2_SOURCE_REVIEW|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || d0.id, 0));
            SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            v_req := jsonb_build_object('operation', 'M2_SOURCE_REVIEW', 'hoa_don_id', p->'hoa_don_id', 'observation_id', p->'observation_id',
                                        'expected_graph', p->'expected_graph', 'reason', p->'reason');
            v_h := """ + _M2_TOKEN.format(x="v_req") + """;
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = d.phap_nhan_id AND b.module = 'M2' AND b.operation = 'M2_SOURCE_REVIEW' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            v_tok := """ + _M2_TOKEN.format(x="kho.m2_co_so_noi_bo(d.id)") + """;
            IF (p->>'expected_graph') IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'M2_VERSION_CHANGED: đồ thị nguồn/hóa đơn đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO o FROM kho.hoa_don_quan_sat q WHERE q.id = (p->>'observation_id')::uuid AND q.hoa_don_id = d.id;
            IF NOT FOUND OR o.id IS DISTINCT FROM d.latest_observation_id THEN
                RAISE EXCEPTION 'M2_CHI_QUAN_SAT_MOI_NHAT: chỉ chọn quan sát mới nhất; không tự khôi phục nội dung cũ' USING ERRCODE = 'P0001';
            END IF;
            UPDATE kho.hoa_don_danh_tinh SET accepted_source_observation_id = o.id, eligible_content_id = o.phien_ban_id WHERE id = d.id;
            v_ket := jsonb_build_object('hoa_don_id', d.id, 'accepted_source_observation_id', o.id, 'eligible_content_id', o.phien_ban_id,
                                        'native_fiscal_status', 'UNKNOWN');
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (d.phap_nhan_id, 'M2', 'M2_SOURCE_REVIEW', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (d.phap_nhan_id, ai, 'HE_THONG', 'kho.hoa_don_danh_tinh', d.id, 'M2_SOURCE_REVIEW', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # mapping dòng (CFO, M2_MAP + V4 + SOURCE_MAP PN đích): dòng nguồn XML_LINE hiện hành của quan sát mới nhất → gốc dòng logic (tạo/dùng lại) →
    # mapping INVOICE_LINE đã duyệt (bind artifact/locator/ordinal/định danh tự dẫn xuất) → cầu nối dòng core có sẵn; một giao dịch, biên nhận DB.
    """CREATE OR REPLACE FUNCTION kho.m2_mapping_dong(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d0 record; d record; r record; a record; o record; pb record; v_tok text; v_req jsonb; v_h text;
            cu record; v_dong uuid; v_root uuid; v_map uuid; v_bridge uuid; ex record; v_ket jsonb; v_bn uuid; v_ord integer; v_q text; v_qx numeric;
            v_ps text; v_up text; v_upx numeric; un record; v_pn_ma text; v_rev integer; v_subj text; fv record; v_loi text;
        BEGIN
            SELECT x.id, x.phap_nhan_id INTO d0 FROM kho.hoa_don_danh_tinh x WHERE x.id = (p->>'hoa_don_id')::uuid;
            IF NOT FOUND OR ai IS NULL OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M2') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['CFO'], 'V4') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_M2_MAP: cần CFO có V4 + M2 của phiên trên PN của hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            SELECT b.* INTO r FROM kho.ban_ghi_nguon b WHERE b.id = (p->>'source_row_id')::uuid;
            SELECT x.* INTO a FROM kho.anh_chup_nguon x WHERE x.id = r.snapshot_id;
            IF a.id IS NULL OR NOT master.ktt_nguon_duoc(a.source_instance_id, a.profile_ref, a.profile_sha256, 'SOURCE_MAP', d0.phap_nhan_id) THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping dòng cần SOURCE_MAP hiện hành đúng instance/profile → PN của hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ '^[A-Za-z0-9_.:-]{1,200}$' OR coalesce(p->>'logical_line_key', '') !~ '^[A-Za-z0-9_.:-]{1,200}$'
               OR coalesce(btrim(p->>'reason'), '') = '' OR coalesce(p->>'evidence_ref', '') = ''
               OR jsonb_typeof(p->'evidence_revision') IS DISTINCT FROM 'number' OR coalesce(p->>'evidence_revision', '') !~ '^[1-9][0-9]{0,8}$' THEN
                RAISE EXCEPTION 'M2_YEU_CAU_SAI: cần khóa, khóa dòng logic, bằng chứng literal + revision và lý do' USING ERRCODE = 'P0001';
            END IF;
            -- R1: quyền hiện hành (trên) → khóa → biên nhận cùng khóa (cùng H body gốc → kết quả cũ; khác H → 409) → yêu cầu mới mới CAS đồ thị
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M2|M2_MAP_LINE|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || d0.id, 0));
            SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            v_req := jsonb_build_object('operation', 'M2_MAP_LINE', 'hoa_don_id', p->'hoa_don_id', 'source_row_id', p->'source_row_id',
                                        'logical_line_key', p->'logical_line_key', 'expected_graph', p->'expected_graph', 'evidence_ref', p->'evidence_ref',
                                        'evidence_revision', p->'evidence_revision', 'reason', p->'reason');
            v_h := """ + _M2_TOKEN.format(x="v_req") + """;
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = d.phap_nhan_id AND b.module = 'M2' AND b.operation = 'M2_MAP_LINE' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            v_tok := """ + _M2_TOKEN.format(x="kho.m2_co_so_noi_bo(d.id)") + """;
            IF (p->>'expected_graph') IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'M2_VERSION_CHANGED: đồ thị nguồn/hóa đơn đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            -- dòng nguồn phải là XML_LINE hiện hành của quan sát MỚI NHẤT (đúng snapshot + artifact + delivery), không theo STT/MaHang
            SELECT q.* INTO o FROM kho.hoa_don_quan_sat q WHERE q.id = d.latest_observation_id;
            IF o.id IS NULL OR r.id IS NULL OR r.section <> 'XML_LINE' OR r.hash_basis IS DISTINCT FROM 'XML_DECODED_FIELD_STATES' OR r.snapshot_id <> o.snapshot_id
               OR r.row_raw->>'native_xml_sha256' IS DISTINCT FROM o.native_xml_sha256 OR r.row_raw->>'container_sha256' IS DISTINCT FROM o.container_sha256
               OR (r.row_raw->>'entry_ordinal')::integer IS DISTINCT FROM o.entry_ordinal OR r.row_raw->>'entry_name' IS DISTINCT FROM o.entry_name
               OR r.row_raw->>'header_locator' IS DISTINCT FROM o.locator THEN
                RAISE EXCEPTION 'M2_DONG_NGUON_KHONG_HIEN_HANH: dòng nguồn không thuộc quan sát mới nhất của hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            -- R2: resolve ĐÚNG ứng viên literal (ref + revision) rồi đối chiếu với dòng/quan sát/định danh THỰC đã capture (không tin tuple từ trình
            --     duyệt) và đúng khóa dòng logic — sai/không có → từ chối cụ thể TRƯỚC mọi gốc/mapping/cầu nối/biên nhận/audit.
            SELECT f.id, f.logical_line_key INTO fv FROM master.m2_ung_vien_dong f WHERE f.mapping_ref = p->>'evidence_ref'
                AND f.revision = (p->>'evidence_revision')::integer;
            IF fv.id IS NULL THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_KHONG_CO: không có ứng viên literal đã admit với ref/revision này' USING ERRCODE = 'P0001';
            END IF;
            v_loi := kho.m2_ung_vien_khop_noi_bo(fv.id, r.id, o.id);
            IF v_loi IS NOT NULL THEN
                RAISE EXCEPTION '%: ứng viên literal không khớp dòng/artifact/định danh thực', v_loi USING ERRCODE = 'P0001';
            END IF;
            IF fv.logical_line_key IS DISTINCT FROM p->>'logical_line_key' THEN
                RAISE EXCEPTION 'M2_UNG_VIEN_SAI_DONG_LOGIC: khóa dòng logic khác đích của ứng viên literal' USING ERRCODE = 'P0001';
            END IF;
            -- R4 repair03 (consumer độc lập): đơn vị dòng nguồn chỉ làm căn cứ khi khớp lại ĐÚNG tuple tài liệu khai báo đã admit (bytes tài liệu,
            -- locator, payload SHA tài liệu khai, căn cứ nguyên văn) VÀ ngữ cảnh hỗ trợ = instance/profile của snapshot — kiểm TRƯỚC mọi ghi.
            SELECT u.* INTO un FROM master.dinh_nghia_don_vi_luong u WHERE u.reference_id = r.row_raw->>'unit_definition_ref';
            IF un.id IS NOT NULL THEN
                v_loi := master.don_vi_khop_khai_bao(un.payload, un.definition_sha256, un.reference_id, un.declared_scope, un.declaration_ref,
                                                     un.declaration_raw_sha256, un.declaration_locator, un.source_basis_ref, un.support_source_instance_id,
                                                     un.support_profile_ref, un.support_profile_sha256);
                IF v_loi IS NULL AND (un.support_source_instance_id, un.support_profile_ref, un.support_profile_sha256)
                                     IS DISTINCT FROM (a.source_instance_id, a.profile_ref, a.profile_sha256) THEN
                    v_loi := 'DON_VI_NGOAI_PHAM_VI';
                END IF;
                IF v_loi IS NOT NULL THEN
                    RAISE EXCEPTION '%: định nghĩa đơn vị không khớp tuple khai báo đã admit — không dùng làm căn cứ', v_loi USING ERRCODE = 'P0001';
                END IF;
            END IF;
            SELECT v.* INTO pb FROM kho.hoa_don_phien_ban v WHERE v.id = o.phien_ban_id;
            v_ord := (r.row_raw->>'source_ordinal')::integer;
            SELECT x.id INTO v_dong FROM kho.chung_tu_dong x WHERE x.chung_tu_id = pb.chung_tu_id AND x.stt = v_ord;
            IF v_dong IS NULL THEN
                RAISE EXCEPTION 'M2_THIEU_DONG_CORE: không thấy dòng core cùng phiên bản/ordinal' USING ERRCODE = 'P0001';
            END IF;
            SELECT b.*, x.logical_line_key INTO ex FROM kho.hoa_don_dong_phien_ban b JOIN kho.hoa_don_dong_danh_tinh x ON x.id = b.dong_danh_tinh_id
                WHERE b.hoa_don_phien_ban_id = pb.id AND b.source_dong_id = v_dong;
            IF FOUND THEN
                IF ex.logical_line_key IS DISTINCT FROM p->>'logical_line_key' THEN
                    RAISE EXCEPTION 'M2_DONG_DA_MAP: dòng đã nối với dòng logic khác — không retarget âm thầm' USING ERRCODE = 'P0001';
                END IF;
                v_root := ex.dong_danh_tinh_id; v_map := ex.line_identity_mapping_id; v_bridge := ex.id;
            ELSE
                INSERT INTO kho.hoa_don_dong_danh_tinh (phap_nhan_id, hoa_don_id, logical_line_key, identity_evidence_id, created_by)
                VALUES (d.phap_nhan_id, d.id, p->>'logical_line_key', r.id, ai)
                ON CONFLICT (phap_nhan_id, hoa_don_id, logical_line_key) DO NOTHING;
                SELECT x.id INTO v_root FROM kho.hoa_don_dong_danh_tinh x WHERE x.hoa_don_id = d.id AND x.logical_line_key = p->>'logical_line_key';
                IF EXISTS (SELECT 1 FROM kho.hoa_don_dong_phien_ban b WHERE b.hoa_don_phien_ban_id = pb.id AND b.dong_danh_tinh_id = v_root) THEN
                    RAISE EXCEPTION 'M2_LOGIC_DA_DUNG: dòng logic đã nối dòng khác trong cùng phiên bản' USING ERRCODE = 'P0001';
                END IF;
                SELECT ma INTO v_pn_ma FROM master.phap_nhan WHERE id = d.phap_nhan_id;
                v_subj := pb.id || '|' || v_ord;
                SELECT coalesce(max(m.revision), 0) + 1 INTO v_rev FROM master.anh_xa_nguon m WHERE m.source_instance_id = a.source_instance_id
                    AND m.profile_ref = a.profile_ref AND m.profile_sha256 = a.profile_sha256 AND m.subject_kind = 'INVOICE_LINE' AND m.subject_key = v_subj;
                INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, phap_nhan_id,
                    valid_from, nguon_quyet_dinh, duyet_boi, ly_do, target_hoa_don_id, target_dong_danh_tinh_id, line_phien_ban_id, line_source_row_id,
                    line_native_xml_sha256, line_container_sha256, line_entry_ordinal, line_entry_name, line_source_locator, line_source_ordinal,
                    line_identity_binding, line_ung_vien_id)
                VALUES ('M2_LINE:' || v_subj, v_rev, a.source_instance_id, a.profile_ref, a.profile_sha256, 'INVOICE_LINE', v_subj, d.phap_nhan_id, now(),
                        'CFO_V4', ai, p->>'reason', d.id, v_root, pb.id, r.id, o.native_xml_sha256, o.container_sha256, o.entry_ordinal, o.entry_name,
                        r.locator, v_ord, ARRAY[v_pn_ma, d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan], fv.id)
                RETURNING id INTO v_map;
                v_q := r.row_raw->'quantity'->>'exact_text';
                v_ps := CASE r.row_raw->'quantity'->>'state' WHEN 'EXACT' THEN 'EXACT_21_6' WHEN 'ABSENT' THEN 'ABSENT' WHEN 'EMPTY' THEN 'EMPTY'
                             WHEN 'OVER_DOMAIN' THEN 'OVER_DOMAIN' ELSE 'INVALID' END;
                v_qx := CASE WHEN v_ps = 'EXACT_21_6' AND v_q ~ '^-?[0-9]+(\\.[0-9]+)?$' AND length(regexp_replace(v_q, '[^0-9]', '', 'g')) <= 21
                                  AND length(split_part(v_q, '.', 2)) <= 6 THEN v_q::numeric END;
                IF v_ps = 'EXACT_21_6' AND v_qx IS NULL THEN
                    v_ps := 'INVALID';
                END IF;
                v_up := r.row_raw->'unit_price'->>'exact_text';
                v_upx := CASE WHEN r.row_raw->'unit_price'->>'state' = 'EXACT' AND v_up ~ '^-?[0-9]+(\\.[0-9]+)?$'
                                   AND length(regexp_replace(v_up, '[^0-9]', '', 'g')) <= 21 AND length(split_part(v_up, '.', 2)) <= 6 THEN v_up::numeric END;
                -- `un` đã được đối chiếu tuple khai báo ở trên (trước mọi ghi)
                INSERT INTO kho.hoa_don_dong_phien_ban (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, dong_danh_tinh_id, chung_tu_id, source_dong_id,
                    source_row_id, snapshot_id, source_ordinal, line_identity_mapping_id, field_states, quantity_raw, unit_raw, unitprice_raw, amount_raw,
                    quantity_exact, unitprice_exact, precision_state, unit_definition_id, unit_basis_sha256, nature_raw, nature, field_state_sha256, created_by)
                VALUES (d.phap_nhan_id, d.id, pb.id, v_root, pb.chung_tu_id, v_dong, r.id, r.snapshot_id, v_ord, v_map, r.row_raw->'fields',
                        r.row_raw->>'quantity_raw', r.row_raw->>'unit_raw', r.row_raw->>'unitprice_raw', r.row_raw->>'amount_raw', v_qx, v_upx, v_ps,
                        un.id, un.definition_sha256, r.row_raw->>'nature_raw', coalesce(r.row_raw->>'nature', 'UNKNOWN'), r.derived_record_sha256, ai)
                RETURNING id INTO v_bridge;
            END IF;
            v_ket := jsonb_build_object('hoa_don_id', d.id, 'phien_ban_id', pb.id, 'source_dong_id', v_dong, 'dong_danh_tinh_id', v_root,
                                        'mapping_id', v_map, 'cau_noi_id', v_bridge, 'logical_line_key', p->>'logical_line_key',
                                        'evidence_ref', p->>'evidence_ref', 'evidence_revision', (p->>'evidence_revision')::integer, 'ung_vien_id', fv.id,
                                        'evidence_ref_authority', 'EVIDENCE_ONLY_NOT_APPROVAL');
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (d.phap_nhan_id, 'M2', 'M2_MAP_LINE', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (d.phap_nhan_id, ai, 'HE_THONG', 'kho.hoa_don_dong_phien_ban', v_bridge, 'M2_MAP_LINE', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # tuyến dòng: MỘT thao tác CFO tạo+duyệt (M2_ROUTE + V4); cần cầu nối dòng đã duyệt của phiên bản hiện hành; tuyến cũ chỉ chuyển THAY_THE qua successor
    """CREATE OR REPLACE FUNCTION kho.m2_route(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d0 record; d record; b record; m record; o record; pb record; cur record; v_tok text; v_req jsonb;
            v_h text; cu record; v_basis text; v_route uuid; v_ket jsonb; v_bn uuid; v_actor uuid;
        BEGIN
            SELECT x.id, x.phap_nhan_id INTO d0 FROM kho.hoa_don_danh_tinh x WHERE x.id = (p->>'hoa_don_id')::uuid;
            IF NOT FOUND OR ai IS NULL OR NOT master.ktt_duoc(d0.phap_nhan_id, 'M2') OR NOT master.ktt_co_vai(d0.phap_nhan_id, ARRAY['CFO'], 'V4') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_M2_ROUTE: cần CFO có V4 + M2 của phiên trên PN của hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ '^[A-Za-z0-9_.:-]{1,200}$' OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'dich', '') NOT IN ('CHI_PHI','XDCB_241','TAI_SAN','KHO') THEN
                RAISE EXCEPTION 'M2_YEU_CAU_SAI: cần khóa, đích hợp lệ và lý do' USING ERRCODE = 'P0001';
            END IF;
            -- R1: quyền hiện hành (trên) → khóa → biên nhận cùng khóa (cùng H body gốc → kết quả cũ; khác H → 409) → yêu cầu mới mới CAS đồ thị
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || d0.phap_nhan_id || '|M2|M2_ROUTE|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || d0.id, 0));
            SELECT * INTO d FROM kho.hoa_don_danh_tinh x WHERE x.id = d0.id FOR UPDATE;
            v_req := jsonb_build_object('operation', 'M2_ROUTE', 'hoa_don_id', p->'hoa_don_id', 'cau_noi_id', p->'cau_noi_id', 'dich', p->'dich',
                                        'expected_route_id', p->'expected_route_id', 'expected_graph', p->'expected_graph', 'reason', p->'reason');
            v_h := """ + _M2_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = d.phap_nhan_id AND x.module = 'M2' AND x.operation = 'M2_ROUTE' AND x.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            v_tok := """ + _M2_TOKEN.format(x="kho.m2_co_so_noi_bo(d.id)") + """;
            IF (p->>'expected_graph') IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'M2_VERSION_CHANGED: đồ thị nguồn/hóa đơn đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO b FROM kho.hoa_don_dong_phien_ban x WHERE x.id = (p->>'cau_noi_id')::uuid AND x.hoa_don_id = d.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M2_ROUTE_CHUA_CO_CAU_NOI: tuyến cần cầu nối dòng đã duyệt thật' USING ERRCODE = 'P0001';
            END IF;
            SELECT q.* INTO o FROM kho.hoa_don_quan_sat q WHERE q.id = d.latest_observation_id;
            IF o.phien_ban_id IS DISTINCT FROM b.hoa_don_phien_ban_id THEN
                RAISE EXCEPTION 'M2_VERSION_CHANGED: cầu nối không thuộc nội dung của quan sát mới nhất' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO m FROM master.anh_xa_nguon x WHERE x.id = b.line_identity_mapping_id AND x.state = 'DA_DUYET' AND x.valid_to IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M2_MAPPING_KHONG_HIEN_HANH: mapping dòng không còn hiện hành' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO cur FROM kho.mua_dich_dong x WHERE x.source_dong_id = b.source_dong_id AND x.hien_hanh FOR UPDATE;
            IF cur.id::text IS DISTINCT FROM p->>'expected_route_id' THEN
                RAISE EXCEPTION 'M2_ROUTE_STALE: tuyến hiện hành khác expected' USING ERRCODE = 'P0001';
            END IF;
            IF cur.id IS NOT NULL AND cur.dich = p->>'dich' THEN
                RAISE EXCEPTION 'M2_ROUTE_KHONG_DOI: tuyến hiện hành đã là đích này' USING ERRCODE = 'P0001';
            END IF;
            SELECT pb2.* INTO pb FROM kho.hoa_don_phien_ban pb2 WHERE pb2.id = b.hoa_don_phien_ban_id;
            v_basis := kho.m2_basis_tuyen_noi_bo(b.id);
            v_actor := nullif(current_setting('ktt.nguoi_dung_id', true), '')::uuid;
            IF cur.id IS NOT NULL THEN
                UPDATE kho.mua_dich_dong SET hien_hanh = false, trang_thai = 'THAY_THE' WHERE id = cur.id;
            END IF;
            INSERT INTO kho.mua_dich_dong (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, source_dong_id, dong_danh_tinh_id, phien_ban, dich, hien_hanh,
                trang_thai, profile_sha256, crosswalk_mapping_id, source_graph_sha256, predecessor_route_id, actor_id, reason)
            VALUES (d.phap_nhan_id, d.id, b.hoa_don_phien_ban_id, b.source_dong_id, b.dong_danh_tinh_id, coalesce(cur.phien_ban, 0) + 1, p->>'dich', true,
                    'DA_DUYET', pb.profile_sha256, m.id, v_basis, cur.id, v_actor, p->>'reason')
            RETURNING id INTO v_route;
            v_ket := jsonb_build_object('route_id', v_route, 'hoa_don_id', d.id, 'source_dong_id', b.source_dong_id, 'dich', p->>'dich',
                                        'phien_ban', coalesce(cur.phien_ban, 0) + 1, 'predecessor_route_id', cur.id, 'source_graph_sha256', v_basis,
                                        'financial_or_inventory_approval', false);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (d.phap_nhan_id, 'M2', 'M2_ROUTE', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (d.phap_nhan_id, ai, 'HE_THONG', 'kho.mua_dich_dong', v_route, 'M2_ROUTE', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # mapping công ty → PN (CFO, SOURCE_MAP PN đích + M2 + V4); retarget đóng bản cũ với quyền trên PN cũ; hóa đơn đã promote giữ PN cũ
    """CREATE OR REPLACE FUNCTION kho.m2_mapping_cong_ty(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v_pn uuid; pr record; n integer; v_req jsonb; v_h text; cu record; hien record; v_rev integer;
            v_moi uuid; v_ref text; v_ket jsonb; v_bn uuid; v_inst text := p->>'source_instance'; v_key text := p->>'company_key';
        BEGIN
            SELECT id INTO v_pn FROM master.phap_nhan WHERE ma = p->>'phap_nhan';
            SELECT count(*) INTO n FROM master.nguon_profile WHERE source_instance_id = v_inst;
            SELECT profile_ref, profile_sha256 INTO pr FROM master.nguon_profile WHERE source_instance_id = v_inst;
            IF ai IS NULL OR v_pn IS NULL OR n <> 1 OR NOT master.ktt_duoc(v_pn, 'M2') OR NOT master.ktt_co_vai(v_pn, ARRAY['CFO'], 'V4')
               OR NOT master.ktt_nguon_duoc(v_inst, pr.profile_ref, pr.profile_sha256, 'SOURCE_MAP', v_pn) THEN
                RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: mapping công ty cần SOURCE_MAP (→ PN đích) và CFO V4 + M2 của phiên' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ '^[A-Za-z0-9_.:-]{1,200}$' OR coalesce(btrim(p->>'reason'), '') = '' OR coalesce(v_key, '') = ''
               OR jsonb_typeof(p->'revision_hien_tai') IS DISTINCT FROM 'number'
               OR NOT EXISTS (SELECT 1 FROM master.nguon_pham_vi s WHERE s.source_instance_id = v_inst AND s.profile_ref = pr.profile_ref
                              AND s.profile_sha256 = pr.profile_sha256 AND s.scope_kind = 'INVOICE_SET' AND v_key = ANY (s.company_keys)) THEN
                RAISE EXCEPTION 'M2_YEU_CAU_SAI: cần khóa, company key thuộc scope cấu hình, revision mong đợi và lý do' USING ERRCODE = 'P0001';
            END IF;
            v_rev := (p->>'revision_hien_tai')::integer;
            v_req := jsonb_build_object('operation', 'M2_MAP_COMPANY', 'source_instance', v_inst, 'company_key', v_key, 'phap_nhan', p->'phap_nhan',
                                        'revision_hien_tai', v_rev, 'reason', p->'reason');
            v_h := """ + _M2_TOKEN.format(x="v_req") + """;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || v_pn || '|M2|M2_MAP_COMPANY|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('ANH_XA|' || v_inst || '|' || pr.profile_ref || '|' || pr.profile_sha256 || '|COMPANY|' || v_key, 0));
            SELECT b.id, b.request_sha256, b.result_json INTO cu FROM kho.bien_nhan_thao_tac b
                WHERE b.phap_nhan_id = v_pn AND b.module = 'M2' AND b.operation = 'M2_MAP_COMPANY' AND b.client_key = p->>'client_key';
            IF FOUND THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                -- R1: replay retarget vẫn cần quyền HIỆN HÀNH trên PN cũ đã đóng (không dùng quyền lịch sử ghi trong biên nhận)
                IF cu.result_json->>'dong_mapping_id' IS NOT NULL THEN
                    SELECT m.* INTO hien FROM master.anh_xa_nguon m WHERE m.id = (cu.result_json->>'dong_mapping_id')::uuid;
                    IF NOT master.ktt_duoc(hien.phap_nhan_id, 'M2') OR NOT master.ktt_co_vai(hien.phap_nhan_id, ARRAY['CFO'], 'V4')
                       OR NOT master.ktt_nguon_duoc(v_inst, pr.profile_ref, pr.profile_sha256, 'SOURCE_MAP', hien.phap_nhan_id) THEN
                        RAISE EXCEPTION 'ANH_XA_KHONG_CO_QUYEN: replay đổi mapping cần quyền hiện hành trên pháp nhân cũ' USING ERRCODE = 'P0001';
                    END IF;
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            SELECT * INTO hien FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.profile_ref = pr.profile_ref
                AND m.profile_sha256 = pr.profile_sha256 AND m.subject_kind = 'COMPANY' AND m.subject_key = v_key AND m.state = 'DA_DUYET'
                AND (m.valid_to IS NULL OR m.valid_to > now()) FOR UPDATE;
            IF FOUND THEN
                IF hien.phap_nhan_id = v_pn THEN
                    RAISE EXCEPTION 'ANH_XA_DA_CO: company key đã map đúng pháp nhân này' USING ERRCODE = 'P0001';
                END IF;
                IF hien.revision <> v_rev THEN
                    RAISE EXCEPTION 'M2_VERSION_CHANGED: revision mapping công ty khác expected' USING ERRCODE = 'P0001';
                END IF;
                v_ref := hien.reference_id;
                UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = hien.id;
            ELSE
                SELECT coalesce(max(m.revision), 0) INTO n FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.profile_ref = pr.profile_ref
                    AND m.profile_sha256 = pr.profile_sha256 AND m.subject_kind = 'COMPANY' AND m.subject_key = v_key;
                IF n <> v_rev THEN
                    RAISE EXCEPTION 'M2_VERSION_CHANGED: revision cuối của company key khác expected' USING ERRCODE = 'P0001';
                END IF;
                SELECT m.reference_id INTO v_ref FROM master.anh_xa_nguon m WHERE m.source_instance_id = v_inst AND m.subject_kind = 'COMPANY'
                    AND m.subject_key = v_key ORDER BY m.revision DESC LIMIT 1;
                v_ref := coalesce(v_ref, 'M2_COMPANY:' || v_inst || ':' || v_key);
            END IF;
            INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, phap_nhan_id,
                valid_from, thay_cho_id, nguon_quyet_dinh, duyet_boi, ly_do)
            VALUES (v_ref, v_rev + 1, v_inst, pr.profile_ref, pr.profile_sha256, 'COMPANY', v_key, v_pn, now(), hien.id, 'CFO_V4', ai, p->>'reason')
            RETURNING id INTO v_moi;
            v_ket := jsonb_build_object('mapping_id', v_moi, 'reference_id', v_ref, 'revision', v_rev + 1, 'phap_nhan', p->>'phap_nhan',
                                        'dong_mapping_id', hien.id, 'hoa_don_da_promote_giu_pn_cu', true);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (v_pn, 'M2', 'M2_MAP_COMPANY', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (v_pn, ai, 'HE_THONG', 'master.anh_xa_nguon', v_moi, 'M2_MAP_COMPANY', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    """REVOKE EXECUTE ON FUNCTION kho.m2_co_so_noi_bo(uuid), kho.m2_co_so(uuid), kho.m2_dong_nguon(uuid), kho.m2_basis_tuyen_noi_bo(uuid),
        kho.m2_tieu_thu_quan_sat(uuid, text),
        kho.m2_xem_xet_nguon(jsonb), kho.m2_mapping_dong(jsonb), kho.m2_route(jsonb), kho.m2_mapping_cong_ty(jsonb),
        kho.m2_ung_vien_khop_noi_bo(uuid, uuid, uuid), kho.m2_ung_vien_hien_hanh(uuid),
        master.don_vi_khop_khai_bao(jsonb, text, text, text, text, text, text, text, text, text, text)
        FROM PUBLIC""",
    "ALTER TABLE master.dinh_nghia_don_vi_luong ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE master.tai_lieu_khai_bao_don_vi ENABLE ROW LEVEL SECURITY",  # không policy cho ứng dụng: bytes tài liệu chỉ chủ CSDL đọc
    "ALTER TABLE master.m2_ung_vien_dong ENABLE ROW LEVEL SECURITY",  # không policy cho ứng dụng: chỉ đọc qua hàm lọc theo hóa đơn/PN
    *(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in _M2_BANG),
    # ---- ACL: thu hồi ACL kế thừa/legacy trên object mới; app_web đọc theo PN + M2; thay policy legacy rộng của core để loại M2 (không OR policy cũ)
    """DO $$
    DECLARE t text; r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_ke_toan','app_cong_ai','app_doc','app_web'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                FOREACH t IN ARRAY ARRAY['master.dinh_nghia_don_vi_luong','master.tai_lieu_khai_bao_don_vi','master.m2_ung_vien_dong','kho.hoa_don_danh_tinh','kho.hoa_don_phien_ban','kho.hoa_don_quan_sat',
                                         'kho.hoa_don_dong_danh_tinh','kho.hoa_don_dong_phien_ban','kho.mua_dich_dong','kho.mua_dong_hien_hanh'] LOOP
                    EXECUTE format('REVOKE ALL ON %s FROM %I', t, r);
                END LOOP;
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            FOREACH t IN ARRAY ARRAY['hoa_don_danh_tinh','hoa_don_phien_ban','hoa_don_quan_sat','hoa_don_dong_danh_tinh','hoa_don_dong_phien_ban',
                                     'mua_dich_dong'] LOOP
                EXECUTE format('GRANT SELECT ON kho.%I TO app_web', t);
                EXECUTE format('DROP POLICY IF EXISTS %I ON kho.%I', t || '_pham_vi_web', t);
                EXECUTE format('CREATE POLICY %I ON kho.%I FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, %L))', t || '_pham_vi_web', t, 'M2');
            END LOOP;
            GRANT SELECT ON kho.mua_dong_hien_hanh TO app_web;
            GRANT SELECT ON master.dinh_nghia_don_vi_luong TO app_web;
            DROP POLICY IF EXISTS dinh_nghia_don_vi_luong_doc ON master.dinh_nghia_don_vi_luong;
            CREATE POLICY dinh_nghia_don_vi_luong_doc ON master.dinh_nghia_don_vi_luong FOR SELECT TO app_web USING (master.ktt_danh_tinh() IS NOT NULL);
            DROP POLICY IF EXISTS anh_xa_nguon_pham_vi_web ON master.anh_xa_nguon;
            CREATE POLICY anh_xa_nguon_pham_vi_web ON master.anh_xa_nguon FOR SELECT TO app_web
                USING (master.ktt_duoc(phap_nhan_id, CASE WHEN subject_kind = 'WAREHOUSE' THEN 'M5' ELSE 'M2' END)
                       OR master.ktt_nguon_duoc(source_instance_id, profile_ref, profile_sha256, 'SOURCE_MAP', phap_nhan_id));
            GRANT EXECUTE ON FUNCTION kho.m2_co_so(uuid), kho.m2_dong_nguon(uuid), kho.m2_tieu_thu_quan_sat(uuid, text), kho.m2_xem_xet_nguon(jsonb), kho.m2_mapping_dong(jsonb),
                kho.m2_route(jsonb), kho.m2_mapping_cong_ty(jsonb), kho.m2_ung_vien_hien_hanh(uuid) TO app_web;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            DROP POLICY IF EXISTS chung_tu_ung_dung_cu ON kho.chung_tu;
            CREATE POLICY chung_tu_ung_dung_cu ON kho.chung_tu TO app_ke_toan
                USING (module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(phap_nhan_id, module_nghiep_vu))
                WITH CHECK (module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(phap_nhan_id, module_nghiep_vu));
            DROP POLICY IF EXISTS chung_tu_dong_ung_dung_cu ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_ung_dung_cu ON kho.chung_tu_dong TO app_ke_toan
                USING ((SELECT c.module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id))
                WITH CHECK ((SELECT c.module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            DROP POLICY IF EXISTS chung_tu_chi_doc ON kho.chung_tu;
            CREATE POLICY chung_tu_chi_doc ON kho.chung_tu FOR SELECT TO app_doc
                USING (module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(phap_nhan_id, module_nghiep_vu));
            DROP POLICY IF EXISTS chung_tu_dong_chi_doc ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_chi_doc ON kho.chung_tu_dong FOR SELECT TO app_doc
                USING ((SELECT c.module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            DROP POLICY IF EXISTS chung_tu_cong_ai ON kho.chung_tu;
            CREATE POLICY chung_tu_cong_ai ON kho.chung_tu FOR SELECT TO app_cong_ai
                USING (module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(phap_nhan_id, module_nghiep_vu));
            DROP POLICY IF EXISTS chung_tu_dong_cong_ai ON kho.chung_tu_dong;
            CREATE POLICY chung_tu_dong_cong_ai ON kho.chung_tu_dong FOR SELECT TO app_cong_ai
                USING ((SELECT c.module_nghiep_vu NOT IN ('M5','M2') OR master.ktt_duoc(c.phap_nhan_id, c.module_nghiep_vu) FROM kho.chung_tu c WHERE c.id = chung_tu_id));
        END IF;
    END $$""",
)

# ---------------------------------------------------------------------------
# 0016 L11 QUANTITY (R16, docs/GIAO-CODE-L11-QUANTITY-01.md): APPEND ONLY — literal/generated 1–15 giữ nguyên; mọi hàm cũ cần đổi chỉ
#   CREATE OR REPLACE TRONG 16. Hai lượng native, hai quantity pool ổn định theo gốc logic (hóa đơn M2 / phiếu M5), mã hóa native→pool bất biến,
#   bằng chứng hàng/tỷ lệ/mã hóa = raw candidate (COMMON capture + stage L11_PROOF) rồi CFO BOTH V4 xác nhận; child HOA_DON_PHIEU_KHO bất biến
#   dưới parent HD_PHIEU_KHO/EVIDENCE/M5 (không tiền). Một biên nhận xác nhận = một child. used = confirmed (DA_KHOP+CO_HIEU_LUC) + held
#   (DA_KHOP+CAN_SOAT); HUY = 0. Không bảng/cache còn lại; không tiền/331/BANK/stock engine/M9.
# ---------------------------------------------------------------------------
_L11_BANG = ("kho.bang_chung_ung_vien", "kho.bang_chung_quy_doi_luong", "kho.dich_so_luong", "kho.ma_hoa_luong_nguon", "kho.lien_ket_dong")
_L11_TOKEN = _M2_TOKEN
_CHOT_M15 = next(s for s in M0015_M2_BRIDGE if s.startswith("CREATE OR REPLACE FUNCTION giao_tiep.nguon_chot_ket_qua"))
_CHOT_NHANH_L11 = """            IF s.du_lieu ? 'l11_proof' THEN
                IF p_promote <> jsonb_build_object('module', 'L11') THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: kết quả L11 do CSDL dẫn xuất, không nhận refs từ caller' USING ERRCODE = 'P0001';
                END IF;
                SELECT jsonb_build_object('module', 'L11', 'trang_thai', 'L11_BANG_CHUNG_DA_GHI', 'ung_vien_id', u.id, 'trang_thai_ung_vien', u.trang_thai,
                                          'reference_id', u.reference_id, 'evidence_revision', u.evidence_revision, 'kind', u.kind,
                                          'issues', to_jsonb(u.issues))
                    INTO v_kq FROM kho.bang_chung_ung_vien u WHERE u.lan_tiep_nhan_id = l.id;
                IF v_kq IS NULL THEN
                    RAISE EXCEPTION 'KET_QUA_CUOI_SAI: lần nhận L11 chưa có ứng viên bằng chứng do consumer ghi' USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO giao_tiep.ket_qua_cuoi_tiep_nhan (lan_tiep_nhan_id, stage_id, capture_sha256, snapshot_moi, promote, actor_id, actor)
                VALUES (l.id, s.id, l.capture_sha256, p_snapshot_moi, v_kq, s.actor_id, s.actor);
                RETURN jsonb_build_object('stage_id', s.id, 'snapshot_moi', p_snapshot_moi, 'promote', v_kq);
            END IF;
"""
_CHOT_NEO = "            IF s.module = 'M2' THEN\n"
assert _CHOT_M15.count(_CHOT_NEO) == 1
_CHOT_M16 = _CHOT_M15.replace(_CHOT_NEO, _CHOT_NHANH_L11 + _CHOT_NEO, 1)

# khóa gốc dùng CHUNG với các entrypoint M2/M5 hiện có (cùng tên advisory) theo thứ tự chuẩn: mọi hóa đơn (UUID sorted) → mọi phiếu (khóa text
# sorted) → pool (UUID sorted). Đường nghiệp vụ một phía cũ chỉ giữ gốc của phía mình nên không tạo vòng với L11.
_L11_KHOA_GOC = """CREATE OR REPLACE FUNCTION kho.l11_khoa_goc_noi_bo(p_hoa_don uuid[], p_phieu uuid[]) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE k text;
        BEGIN
            FOR k IN SELECT DISTINCT 'HOA_DON_ROOT|' || x FROM unnest(coalesce(p_hoa_don, '{}')) AS x WHERE x IS NOT NULL ORDER BY 1 LOOP
                PERFORM pg_advisory_xact_lock(hashtextextended(k, 0));
            END LOOP;
            FOR k IN SELECT DISTINCT 'PHIEU_KHO|' || d.source_instance_id || '|' || d.so_phieu_key FROM kho.phieu_kho_danh_tinh d
                     WHERE d.id = ANY (coalesce(p_phieu, '{}')) ORDER BY 1 LOOP
                PERFORM pg_advisory_xact_lock(hashtextextended(k, 0));
            END LOOP;
        END $$"""

_L11_HEX = "'^[0-9a-f]{64}$'"
_L11_KHOA_RE = "'^[A-Za-z0-9_.:-]{1,200}$'"

# ---------------------------------------------------------------------------------------------------------------------------------------------
# R1 repair02 — giao thức khóa/ảnh hưởng toàn batch DÙNG CHUNG cho 11 đường nguồn cũ + mọi thao tác L11:
#   (quyền hiện hành) → namespace/khóa thao tác → PRECOLLECT toàn batch gốc nguồn của thao tác + mọi child sống chạm các gốc đó → gốc ngang hàng
#   CẢ HAI PHÍA → khóa gốc chuẩn (mọi HOA_DON_ROOT sorted → mọi PHIEU_KHO sorted) → pool sorted FOR UPDATE → hàng child FOR UPDATE → ĐỌC LẠI
#   closure dưới khóa (phát sinh child chạm gốc batch với gốc ngang hàng chưa khóa → L11_CLOSURE_MO_RONG, hủy toàn thao tác TRƯỚC mọi hiệu lực).
#   Hiệu lực (CAN_SOAT đồng bộ) do trigger CSDL ghi trong cùng giao dịch; trigger KHÔNG xin khóa muộn mà KIỂM khóa gốc hai phía của mọi child
#   bị ảnh hưởng đã do chính backend giữ (pg_locks) — thiếu → L11_KHOA_GOC_THIEU (đường ghi trực tiếp/bỏ giao thức bị từ chối, không suy giảm).
#   Hàng mapping (MASTER cố định) giữ thứ tự R14/R15 sẵn có: subject/hàng mapping trước gốc — không đường L11 nào khóa hàng mapping nên không
#   tạo vòng; đổi thứ tự này trong đường M5/M2 cũ sẽ tạo vòng với intake/file soát cũ (xem báo cáo 02 §3).
# ---------------------------------------------------------------------------------------------------------------------------------------------
_L11_R1_HAM = (
    """CREATE OR REPLACE FUNCTION kho.l11_giu_khoa_noi_bo(p_k text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_locks l, (SELECT hashtextextended(p_k, 0) AS h) z
                       WHERE l.locktype = 'advisory' AND l.pid = pg_backend_pid() AND l.granted AND l.objsubid = 1
                         AND l.database = (SELECT d.oid FROM pg_catalog.pg_database d WHERE d.datname = current_database())
                         AND l.classid = ((z.h >> 32) & 4294967295)::oid AND l.objid = (z.h & 4294967295)::oid)
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_kiem_khoa_dong_noi_bo(p_dong uuid[]) RETURNS void
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE r record;
        BEGIN
            FOR r IN SELECT c.id, c.hoa_don_id, d.source_instance_id, d.so_phieu_key FROM kho.lien_ket_dong c JOIN kho.phieu_kho_danh_tinh d ON d.id = c.phieu_id
                     WHERE c.id = ANY (coalesce(p_dong, '{}')) AND c.trang_thai = 'DA_KHOP' ORDER BY c.id LOOP
                IF NOT kho.l11_giu_khoa_noi_bo('HOA_DON_ROOT|' || r.hoa_don_id)
                   OR NOT kho.l11_giu_khoa_noi_bo('PHIEU_KHO|' || r.source_instance_id || '|' || r.so_phieu_key) THEN
                    RAISE EXCEPTION 'L11_KHOA_GOC_THIEU: thay đổi nguồn/mapping/tuyến/bằng chứng ảnh hưởng child % mà chưa giữ khóa gốc hai phía theo giao thức chung', r.id
                        USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_khoa_dong_nguon_noi_bo(p_hoa_don uuid[], p_phieu uuid[]) RETURNS uuid[]
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_dong uuid[]; v_dong2 uuid[]; v_hd uuid[]; v_pk uuid[]; v_pool uuid[];
        BEGIN
            -- precollect toàn batch (không phụ thuộc thứ tự XML/ZIP/vòng lặp): child sống chạm bất kỳ gốc batch → gốc ngang hàng cả hai phía + pool
            SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') INTO v_dong FROM kho.lien_ket_dong c
                WHERE c.trang_thai = 'DA_KHOP' AND (c.hoa_don_id = ANY (coalesce(p_hoa_don, '{}')) OR c.phieu_id = ANY (coalesce(p_phieu, '{}')));
            SELECT coalesce(array_agg(DISTINCT z.x ORDER BY z.x), '{}') INTO v_hd
                FROM (SELECT unnest(coalesce(p_hoa_don, '{}')) AS x UNION SELECT c.hoa_don_id FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong)) z
                WHERE z.x IS NOT NULL;
            SELECT coalesce(array_agg(DISTINCT z.x ORDER BY z.x), '{}') INTO v_pk
                FROM (SELECT unnest(coalesce(p_phieu, '{}')) AS x UNION SELECT c.phieu_id FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong)) z
                WHERE z.x IS NOT NULL;
            -- pool + child của closure được BIND ngay lúc precollect (không truy vấn pool mới sau khi chờ gốc)
            SELECT coalesce(array_agg(DISTINCT z.x ORDER BY z.x), '{}') INTO v_pool
                FROM (SELECT c.pool_hoa_don_id AS x FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong)
                      UNION SELECT c.pool_phieu_id FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong)) z;
            PERFORM kho.l11_khoa_goc_noi_bo(v_hd, v_pk);
            -- repair03 (R1-L02): đọc lại NGAY sau khi giữ gốc, TRƯỚC pool/hàng — tập child (do đó pool LINE + gốc ngang hàng) phải TRÙNG KHÍT
            -- tập đã precollect; khác (child mới cùng cặp chứng từ nhưng LINE/pool mới, child đã HUY, gốc mới) → hủy toàn thao tác, 0 hiệu lực,
            -- không xin thêm pool/hàng theo thứ tự thấp hơn khi đang giữ gốc
            SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') INTO v_dong2 FROM kho.lien_ket_dong c
                WHERE c.trang_thai = 'DA_KHOP' AND (c.hoa_don_id = ANY (coalesce(p_hoa_don, '{}')) OR c.phieu_id = ANY (coalesce(p_phieu, '{}')));
            IF v_dong2 IS DISTINCT FROM v_dong THEN
                RAISE EXCEPTION 'L11_CLOSURE_MO_RONG: tập child/pool/gốc của closure đã đổi trong lúc chờ khóa gốc — thử lại toàn thao tác (0 hiệu lực)'
                    USING ERRCODE = 'P0001';
            END IF;
            PERFORM kho.l11_khoa_pool_noi_bo(v_pool);
            PERFORM 1 FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong) ORDER BY c.id FOR UPDATE;
            RETURN v_dong;
        END $$""",
    # R3 repair02 — admission cặp TRƯỚC mọi projection: PN chung của dòng hóa đơn + dòng phiếu, và mọi mã hóa/bằng chứng được tham chiếu (nếu có)
    # cùng PN đó; bất kỳ endpoint vắng/khác PN → NULL (người gọi từ chối, không nạp/serialize facts PN khác)
    """CREATE OR REPLACE FUNCTION kho.l11_trang_thai_cap_noi_bo(p jsonb) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT b.phap_nhan_id FROM kho.hoa_don_dong_phien_ban b JOIN kho.phieu_kho_dong_phien_ban lw ON lw.phap_nhan_id = b.phap_nhan_id
        WHERE b.id = kho.l11_uuid(p->>'cau_noi_id') AND lw.id = kho.l11_uuid(p->>'dong_phien_ban_id')
          AND NOT EXISTS (SELECT 1 FROM unnest(ARRAY[p->>'ma_hoa_hoa_don_id', p->>'ma_hoa_phieu_id']) AS t(k)
                          WHERE t.k IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kho.ma_hoa_luong_nguon e WHERE e.id = kho.l11_uuid(t.k)
                                                                AND e.phap_nhan_id = b.phap_nhan_id))
          AND NOT EXISTS (SELECT 1 FROM unnest(ARRAY[p->>'bang_chung_hang_id', p->>'bang_chung_ty_le_id']) AS t(k)
                          WHERE t.k IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kho.bang_chung_quy_doi_luong q WHERE q.id = kho.l11_uuid(t.k)
                                                                AND q.phap_nhan_id = b.phap_nhan_id))
        $$""",
    # child sống bị ảnh hưởng khi ĐÓNG một mapping (dòng INVOICE_LINE / công ty / WAREHOUSE) — dùng chung cho kiểm khóa trước tuple và giữ soát
    """CREATE OR REPLACE FUNCTION kho.l11_dong_anh_xa_noi_bo(p_map uuid) RETURNS uuid[]
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') FROM kho.lien_ket_dong c WHERE c.trang_thai = 'DA_KHOP' AND (
            EXISTS (SELECT 1 FROM kho.hoa_don_dong_phien_ban b WHERE b.id = c.cau_noi_id AND b.line_identity_mapping_id = p_map)
            OR EXISTS (SELECT 1 FROM kho.hoa_don_phien_ban v WHERE v.id = c.hoa_don_phien_ban_id AND v.company_mapping_id = p_map)
            OR EXISTS (SELECT 1 FROM kho.phieu_kho_danh_tinh d WHERE d.id = c.phieu_id AND d.mapping_revision_id = p_map))
        $$""",
    # khai báo đo lường HIỆN HÀNH của một dòng phiếu: đúng một fact của instance/profile của phiên bản, điều kiện master SHA thật của nội dung,
    # đúng định nghĩa đơn vị của dòng và payload SHA canonical tự tính — không chọn theo nhãn, không ép mọi delivery về một raw SHA
    """CREATE OR REPLACE FUNCTION kho.l11_do_luong_dong_noi_bo(p_lw uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT CASE WHEN count(*) = 1 THEN min(f.payload_sha256) END
        FROM kho.phieu_kho_dong_phien_ban lw JOIN kho.phieu_kho_phien_ban v ON v.id = lw.phien_ban_id
        JOIN kho.phieu_kho_danh_tinh d ON d.id = lw.phieu_id
        JOIN master.nguon_su_kien_do_luong f ON f.source_instance_id = d.source_instance_id AND f.profile_ref = v.profile_ref
             AND f.profile_sha256 = v.profile_sha256 AND f.dieu_kien->'resolution_preconditions'->>'actual_master_sha256' = v.master_raw_sha256
             AND f.payload->'unit_definition'->>'reference_id' = lw.unit_definition_ref
             AND f.payload_sha256 = encode(sha256(convert_to(master.json_chuan(f.payload), 'UTF8')), 'hex')
        WHERE lw.id = p_lw
        $$""",
    # định nghĩa đơn vị đã xác minh qua MASTER chung (tuple tài liệu khai báo R15) — NULL = đạt
    """CREATE OR REPLACE FUNCTION kho.l11_don_vi_xac_minh_noi_bo(p_dv uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT CASE WHEN u.id IS NULL THEN 'L11_DON_VI_KHONG_CO'
                    ELSE master.don_vi_khop_khai_bao(u.payload, u.definition_sha256, u.reference_id, u.declared_scope, u.declaration_ref,
                                                     u.declaration_raw_sha256, u.declaration_locator, u.source_basis_ref, u.support_source_instance_id,
                                                     u.support_profile_ref, u.support_profile_sha256) END
        FROM (SELECT p_dv AS k) z LEFT JOIN master.dinh_nghia_don_vi_luong u ON u.id = z.k
        $$""",
    # R3 repair02 — hỗ trợ nguồn thật của định nghĩa đơn vị: artifact hỗ trợ (raw SHA + độ dài catalog) ĐÃ capture trong đúng ngữ cảnh
    # instance/profile hỗ trợ, và TRƯỜNG đơn vị (+ mã hàng khi có) tại đúng locator khai báo trích bởi reader thật = mã đơn vị của định nghĩa.
    # Không coi FK catalog/self-H của tài liệu khai báo hay cùng nhãn CAI là bằng chứng trường nguồn.
    """CREATE OR REPLACE FUNCTION kho.l11_ho_tro_don_vi_noi_bo(p_dv uuid, p_item text) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE u record; v_loi text; v_loc text; v_fld text; v_len bigint;
        BEGIN
            v_loi := kho.l11_don_vi_xac_minh_noi_bo(p_dv);
            IF v_loi IS NOT NULL THEN
                RETURN v_loi;
            END IF;
            SELECT x.* INTO u FROM master.dinh_nghia_don_vi_luong x WHERE x.id = p_dv;
            IF u.support_raw_sha256 IS NULL OR u.support_locator IS NULL OR u.support_locator !~ '^/.+/[^/]+$' THEN
                RETURN 'L11_HO_TRO_DON_VI_THIEU';
            END IF;
            SELECT c.byte_length INTO v_len FROM master.nguon_master_noi_dung c WHERE c.raw_sha256 = u.support_raw_sha256;
            v_loc := regexp_replace(u.support_locator, '/[^/]+$', '');
            v_fld := substring(u.support_locator from '[^/]+$');
            IF v_len IS NULL OR NOT EXISTS (
                   SELECT 1 FROM kho.ban_ghi_nguon r JOIN kho.anh_chup_nguon a ON a.id = r.snapshot_id
                   JOIN kho.anh_chup_nguon_vai_tro v ON v.snapshot_id = r.snapshot_id AND v.vai_tro = r.vai_tro AND v.co_mat
                   WHERE a.source_instance_id = u.support_source_instance_id AND a.profile_ref = u.support_profile_ref
                     AND a.profile_sha256 = u.support_profile_sha256
                     AND ((r.section = 'XML_LINE' AND r.row_raw->>'native_xml_sha256' = u.support_raw_sha256
                           AND (r.row_raw->>'byte_length')::bigint = v_len AND r.row_raw->>'source_locator' = v_loc
                           AND CASE v_fld WHEN 'DVTinh' THEN r.row_raw->>'unit_raw' ELSE r.row_raw->'fields'->v_fld->0->>'lexeme' END
                               = u.payload->>'native_unit_code'
                           AND (p_item IS NULL OR r.row_raw->'fields'->'MHHDVu'->0->>'lexeme' = p_item))
                          OR (r.section <> 'XML_LINE' AND v.raw_sha256 = u.support_raw_sha256 AND v.byte_length = v_len AND r.locator = v_loc
                              AND r.row_raw->>v_fld = u.payload->>'native_unit_code'
                              AND (p_item IS NULL OR r.row_raw->>'MaHang' = p_item)))) THEN
                RETURN 'L11_HO_TRO_DON_VI_KHONG_KHOP';
            END IF;
            RETURN NULL;
        END $$""",
)

M0016_L11_HAM = _L11_R1_HAM + (
    # ---- quyền hiện hành L11 (một chỗ): BOTH M2+M5 của phiên trên PN + vai/loại việc theo thao tác; không GUC/owner bypass
    """CREATE OR REPLACE FUNCTION kho.l11_quyen_noi_bo(p_pn uuid, p_loai text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(master.ktt_danh_tinh() IS NOT NULL AND p_pn IS NOT NULL AND master.ktt_duoc(p_pn, 'M2') AND master.ktt_duoc(p_pn, 'M5')
               AND CASE p_loai WHEN 'READ' THEN true
                               WHEN 'LINK' THEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], 'V2')
                               WHEN 'CFO' THEN master.ktt_co_vai(p_pn, ARRAY['CFO'], 'V4')
                               WHEN 'FILE' THEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL)
                               ELSE false END, false)
        $$""",
    # ---- bốn primitive số lượng: chuỗi native exact 38,12 dương; tỷ lệ = CHUỖI số nguyên dương ≤38 chữ số (không Number/1.5/0); quy đổi exact
    #      (biểu diễn được trong 38,12, không làm tròn); ngân sách đã dùng (confirmed + held, mỗi child một lần mỗi pool)
    """CREATE OR REPLACE FUNCTION kho.l11_uuid(t text) RETURNS uuid
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT CASE WHEN t ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN t::uuid END
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_so_nguon(t text) RETURNS numeric
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT CASE WHEN t ~ '^(0|[1-9][0-9]{0,25})(\\.[0-9]{1,12})?$' THEN CASE WHEN t::numeric > 0 THEN t::numeric(38,12) END END
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_so_ty_le(v jsonb) RETURNS numeric
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT CASE WHEN jsonb_typeof(v) = 'string' THEN CASE WHEN (v #>> '{}') ~ '^[1-9][0-9]{0,37}$' THEN (v #>> '{}')::numeric(38,0) END END
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_quy_doi(x numeric, tu numeric, mau numeric) RETURNS numeric
        LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        DECLARE q numeric;
        BEGIN
            IF x IS NULL OR tu IS NULL OR mau IS NULL OR x <= 0 OR tu <= 0 OR mau <= 0 THEN
                RETURN NULL;
            END IF;
            q := round((x * tu) / mau, 12);
            IF q <= 0 OR q >= 1e26 OR q * mau <> x * tu THEN
                RETURN NULL;  -- không biểu diễn chính xác trong 38,12 (vd 1/12): không làm tròn, không clamp
            END IF;
            RETURN q::numeric(38,12);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_text(n numeric) RETURNS text
        LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT CASE WHEN n IS NULL THEN NULL WHEN n::text LIKE '%.%' THEN rtrim(rtrim(n::text, '0'), '.') ELSE n::text END
        $$""",
    _L11_KHOA_GOC,
    """CREATE OR REPLACE FUNCTION kho.l11_khoa_pool_noi_bo(p_pools uuid[]) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE k uuid;
        BEGIN
            FOR k IN SELECT DISTINCT x FROM unnest(coalesce(p_pools, '{}')) AS x WHERE x IS NOT NULL ORDER BY 1 LOOP
                PERFORM pg_advisory_xact_lock(hashtextextended('L11_POOL|' || k, 0));
                PERFORM 1 FROM kho.dich_so_luong d WHERE d.id = k FOR UPDATE;
            END LOOP;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.luong_da_khop_noi_bo(p_pool uuid) RETURNS TABLE (da_xac_nhan numeric, dang_giu numeric)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce(sum(CASE WHEN c.hieu_luc = 'CO_HIEU_LUC' THEN CASE WHEN c.pool_hoa_don_id = p_pool THEN c.so_luong_pool_hoa_don
                                                                          ELSE c.so_luong_pool_phieu END END), 0),
               coalesce(sum(CASE WHEN c.hieu_luc = 'CAN_SOAT' THEN CASE WHEN c.pool_hoa_don_id = p_pool THEN c.so_luong_pool_hoa_don
                                                                       ELSE c.so_luong_pool_phieu END END), 0)
        FROM kho.lien_ket_dong c WHERE c.trang_thai = 'DA_KHOP' AND (c.pool_hoa_don_id = p_pool OR c.pool_phieu_id = p_pool)
        $$""",
    # sức chứa hiện hành = mã hóa revision mới nhất của PB-line thuộc NỘI DUNG ELIGIBLE hiện hành của gốc (+ tuyến KHO/mapping/bằng chứng còn hiệu lực);
    # thiếu bất kỳ căn cứ → sức chứa NULL, còn lại NULL (bị chặn), held/confirmed vẫn tính; không clamp 0, không giải phóng, không retarget
    """CREATE OR REPLACE FUNCTION kho.l11_ngan_sach_noi_bo(p_pool uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE pl record; d_hd record; d_pk record; b record; lw record; u record; dung record;
            v_ly_do text[] := '{}'; v_e_id uuid; v_e_cap numeric; v_e_proof uuid; v_cap numeric; v_con numeric;
        BEGIN
            SELECT x.* INTO pl FROM kho.dich_so_luong x WHERE x.id = p_pool;
            IF pl.id IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT * INTO dung FROM kho.luong_da_khop_noi_bo(p_pool);
            SELECT x.reference_id, x.payload->>'native_unit_code' AS ma INTO u FROM master.dinh_nghia_don_vi_luong x WHERE x.id = pl.don_vi_id;
            IF pl.owner_module = 'M2' THEN
                SELECT x.* INTO d_hd FROM kho.hoa_don_danh_tinh x WHERE x.id = pl.hoa_don_id;
                SELECT x.* INTO b FROM kho.hoa_don_dong_phien_ban x WHERE x.hoa_don_id = pl.hoa_don_id AND x.hoa_don_phien_ban_id = d_hd.eligible_content_id
                    AND x.dong_danh_tinh_id = pl.hoa_don_dong_id;
                IF d_hd.eligible_content_id IS NULL THEN
                    v_ly_do := v_ly_do || 'L11_NGUON_KHONG_DU_DIEU_KIEN'::text;
                ELSIF b.id IS NULL THEN
                    v_ly_do := v_ly_do || 'L11_DONG_KHONG_CO_TRONG_NOI_DUNG_HIEN_HANH'::text;
                ELSE
                    SELECT x.id, x.suc_chua, x.bang_chung_ma_hoa_id INTO v_e_id, v_e_cap, v_e_proof FROM kho.ma_hoa_luong_nguon x
                        WHERE x.cau_noi_id = b.id AND x.pool_id = pl.id ORDER BY x.basis_revision DESC LIMIT 1;
                    IF NOT EXISTS (SELECT 1 FROM kho.mua_dich_dong r WHERE r.source_dong_id = b.source_dong_id AND r.hien_hanh AND r.dich = 'KHO'
                                   AND r.trang_thai = 'DA_DUYET') THEN
                        v_ly_do := v_ly_do || 'L11_TUYEN_KHONG_PHAI_KHO'::text;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM master.anh_xa_nguon m WHERE m.id = b.line_identity_mapping_id AND m.state = 'DA_DUYET' AND m.valid_to IS NULL) THEN
                        v_ly_do := v_ly_do || 'L11_MAPPING_KHONG_HIEN_HANH'::text;
                    END IF;
                END IF;
            ELSE
                SELECT x.* INTO d_pk FROM kho.phieu_kho_danh_tinh x WHERE x.id = pl.phieu_id;
                SELECT x.* INTO lw FROM kho.phieu_kho_dong_phien_ban x WHERE x.phien_ban_id = d_pk.eligible_content_id AND x.dong_id = pl.phieu_dong_id;
                IF d_pk.eligible_content_id IS NULL THEN
                    v_ly_do := v_ly_do || 'L11_NGUON_KHONG_DU_DIEU_KIEN'::text;
                ELSIF lw.id IS NULL THEN
                    v_ly_do := v_ly_do || 'L11_DONG_KHONG_CO_TRONG_NOI_DUNG_HIEN_HANH'::text;
                ELSE
                    SELECT x.id, x.suc_chua, x.bang_chung_ma_hoa_id INTO v_e_id, v_e_cap, v_e_proof FROM kho.ma_hoa_luong_nguon x
                        WHERE x.phieu_dong_phien_ban_id = lw.id AND x.pool_id = pl.id ORDER BY x.basis_revision DESC LIMIT 1;
                    IF NOT EXISTS (SELECT 1 FROM master.anh_xa_nguon m WHERE m.id = d_pk.mapping_revision_id AND m.state = 'DA_DUYET' AND m.valid_to IS NULL) THEN
                        v_ly_do := v_ly_do || 'L11_MAPPING_KHONG_HIEN_HANH'::text;
                    END IF;
                    IF v_e_id IS NOT NULL AND (SELECT x.do_luong_sha256 FROM kho.ma_hoa_luong_nguon x WHERE x.id = v_e_id)
                                              IS DISTINCT FROM kho.l11_do_luong_dong_noi_bo(lw.id) THEN
                        v_ly_do := v_ly_do || 'L11_DO_LUONG_KHONG_HIEN_HANH'::text;  -- R3: khai báo đo lường đổi → sức chứa bị chặn (held giữ nguyên)
                    END IF;
                END IF;
            END IF;
            IF v_e_id IS NULL AND cardinality(v_ly_do) = 0 THEN
                v_ly_do := v_ly_do || 'L11_MA_HOA_THIEU'::text;
            END IF;
            IF v_e_proof IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kho.bang_chung_quy_doi_luong q WHERE q.id = v_e_proof AND q.trang_thai = 'DA_XAC_NHAN') THEN
                v_ly_do := v_ly_do || 'L11_BANG_CHUNG_MA_HOA_THU_HOI'::text;
            END IF;
            v_cap := CASE WHEN cardinality(v_ly_do) = 0 THEN v_e_cap END;
            IF v_cap IS NOT NULL AND v_cap < dung.da_xac_nhan + dung.dang_giu THEN
                v_ly_do := v_ly_do || 'L11_SUC_CHUA_NHO_HON_DA_DUNG'::text;
            END IF;
            v_con := CASE WHEN cardinality(v_ly_do) = 0 THEN v_cap - dung.da_xac_nhan - dung.dang_giu END;
            RETURN jsonb_build_object('pool_id', pl.id, 'owner_module', pl.owner_module, 'don_vi_id', pl.don_vi_id, 'don_vi', u.reference_id,
                                      'don_vi_ma', u.ma, 'suc_chua', kho.l11_text(v_cap), 'da_xac_nhan', kho.l11_text(dung.da_xac_nhan),
                                      'dang_giu', kho.l11_text(dung.dang_giu), 'da_dung', kho.l11_text(dung.da_xac_nhan + dung.dang_giu),
                                      'con_lai', kho.l11_text(v_con), 'ma_hoa_id', v_e_id, 'bang_chung_ma_hoa_id', v_e_proof, 'ly_do_chan', to_jsonb(v_ly_do));
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.luong_con_lai(p_pool uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_pn uuid;
        BEGIN
            SELECT x.phap_nhan_id INTO v_pn FROM kho.dich_so_luong x WHERE x.id = p_pool;
            IF v_pn IS NULL OR NOT kho.l11_quyen_noi_bo(v_pn, 'READ') THEN
                RETURN NULL;  -- ngoài quyền BOTH READ hiện hành: không lộ tồn tại
            END IF;
            RETURN kho.l11_ngan_sach_noi_bo(p_pool);
        END $$""",
    # ---- consumer stage L11_PROOF: chỉ nhận stage ID + H do chủ bảng ghi cùng giao dịch với capture COMMON; facts đối chiếu từ CSDL (vai trò NATIVE
    #      thật của snapshot, dòng JSON đã capture, binding cấu hình của profile) — kind/ref/revision do cấu hình suy, không từ trình duyệt; sai → HOLD
    """CREATE OR REPLACE FUNCTION kho.l11_tieu_thu_bang_chung(p_stage uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); s record; q jsonb; l record; sc record; prof jsonb; cfg jsonb; v_raw text; v_len bigint;
            b record; cu record; v_issues text[] := '{}'; v_ref text; v_rev integer; v_kind text; v_id uuid; v_payload text; v_pn_ma text;
        BEGIN
            SELECT * INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'L11_PROOF';
            IF NOT FOUND OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage L11_PROOF không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            IF ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL) THEN
                RAISE EXCEPTION 'NGUON_KHONG_CO_QUYEN: nhận bằng chứng cần INTAKE hiện hành của đúng phiên đã tạo stage' USING ERRCODE = 'P0001';
            END IF;
            q := s.du_lieu;
            SELECT x.* INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = kho.l11_uuid(q->>'receipt_id') AND x.source_instance_id = s.source_instance_id
                AND x.profile_ref = s.profile_ref AND x.profile_sha256 = s.profile_sha256 AND x.actor_id = s.actor_id;
            IF l.id IS NULL THEN
                RAISE EXCEPTION 'STAGE_CHUA_CAPTURE: phải tiêu thụ capture COMMON của chính lần nhận trước' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.id, x.trang_thai INTO cu FROM kho.bang_chung_ung_vien x WHERE x.lan_tiep_nhan_id = l.id;
            IF cu.id IS NOT NULL THEN
                RETURN jsonb_build_object('ung_vien_id', cu.id, 'trang_thai', cu.trang_thai, 'lap_lai', true);
            END IF;
            SELECT x.* INTO sc FROM master.nguon_pham_vi x WHERE x.source_instance_id = l.source_instance_id AND x.scope_ref = l.scope_ref
                AND x.profile_ref = l.profile_ref AND x.profile_sha256 = l.profile_sha256 AND x.scope_kind = 'L11_EVIDENCE_SET';
            IF sc.id IS NULL OR sc.phap_nhan_id IS DISTINCT FROM s.phap_nhan_id THEN
                RAISE EXCEPTION 'L11_PHAM_VI_SAI: lần nhận không thuộc phạm vi bằng chứng L11 của đúng PN' USING ERRCODE = 'P0001';
            END IF;
            SELECT np.payload INTO prof FROM master.nguon_profile np WHERE np.source_instance_id = l.source_instance_id AND np.profile_ref = l.profile_ref
                AND np.profile_sha256 = l.profile_sha256;
            IF prof->>'purpose' IS DISTINCT FROM 'L11_PROOF' OR jsonb_typeof(prof->'proof_references') IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION 'L11_PROFILE_SAI: profile không phải profile bằng chứng L11' USING ERRCODE = 'P0001';
            END IF;
            SELECT v.raw_sha256, v.byte_length INTO v_raw, v_len FROM kho.anh_chup_nguon_vai_tro v WHERE v.snapshot_id = l.snapshot_id AND v.vai_tro = 'NATIVE' AND v.co_mat;
            IF v_raw IS NULL THEN
                v_issues := v_issues || 'L11_THIEU_NATIVE'::text;
            END IF;
            SELECT e INTO cfg FROM jsonb_array_elements(prof->'proof_references') AS t(e) WHERE e->>'raw_sha256' = v_raw;
            IF cfg IS NULL THEN
                v_issues := v_issues || 'L11_BANG_CHUNG_KHONG_CAU_HINH'::text;
            ELSE
                IF (cfg->>'byte_length')::bigint IS DISTINCT FROM v_len THEN
                    v_issues := v_issues || 'L11_DO_DAI_SAI'::text;
                END IF;
                v_ref := cfg->>'reference_id'; v_rev := (cfg->>'evidence_revision')::integer;
                v_kind := CASE cfg->>'kind' WHEN 'GOODS_EQUIVALENCE' THEN 'GOODS_EQUIVALENCE' WHEN 'CROSS_NATIVE_RATIO' THEN 'CROSS_NATIVE_RATIO'
                                            WHEN 'NATIVE_ENCODING' THEN 'NATIVE_ENCODING' END;
                IF v_kind IS NULL THEN
                    v_issues := v_issues || 'L11_LOAI_BANG_CHUNG_LA'::text;
                END IF;
            END IF;
            SELECT x.* INTO b FROM kho.ban_ghi_nguon x WHERE x.snapshot_id = l.snapshot_id AND x.section = 'L11_PROOF_JSON' ORDER BY x.thu_tu LIMIT 1;
            IF b.id IS NULL THEN
                v_issues := v_issues || 'L11_JSON_KHONG_DOC_DUOC'::text;
            ELSE
                BEGIN
                    v_payload := encode(sha256(convert_to(master.json_chuan(b.row_raw), 'UTF8')), 'hex');
                EXCEPTION WHEN others THEN
                    v_payload := NULL;
                END;
                IF v_payload IS NULL OR v_payload IS DISTINCT FROM b.row_raw_sha256 THEN
                    v_issues := v_issues || 'L11_JSON_KHONG_DOC_DUOC'::text;
                END IF;
                IF cfg IS NOT NULL AND (b.row_raw->>'reference_id' IS DISTINCT FROM v_ref OR jsonb_typeof(b.row_raw->'evidence_revision') IS DISTINCT FROM 'number'
                                        OR (b.row_raw->>'evidence_revision')::numeric IS DISTINCT FROM v_rev) THEN
                    v_issues := v_issues || 'L11_THAM_CHIEU_MAU_THUAN'::text;
                END IF;
                SELECT p.ma INTO v_pn_ma FROM master.phap_nhan p WHERE p.id = sc.phap_nhan_id;
                IF b.row_raw->>'pn_ma' IS DISTINCT FROM v_pn_ma THEN
                    v_issues := v_issues || 'L11_PHAP_NHAN_KHAC'::text;
                END IF;
            END IF;
            -- R3 repair02: claim gốc của lần nhận (coverage/lỗi báo — đã nằm trong H/biên nhận COMMON) quyết định khả năng duyệt: chỉ COMPLETE_INPUT
            -- (một bằng chứng đầy đủ) + coverage hiệu lực COMPLETE + không lỗi báo mới là ứng viên; còn lại HOLD (giữ raw, không tự coi là đầy đủ)
            IF l.coverage IS DISTINCT FROM 'COMPLETE_INPUT' THEN
                v_issues := v_issues || ('L11_COVERAGE_' || coalesce(l.coverage, 'NULL'))::text;
            END IF;
            IF l.coverage_hieu_luc IS DISTINCT FROM 'COMPLETE_INPUT' THEN
                v_issues := v_issues || 'L11_COVERAGE_HIEU_LUC_CHUA_DU'::text;
            END IF;
            IF cardinality(l.reported_errors) > 0 THEN
                v_issues := v_issues || 'L11_LOI_BAO_CAO_NGUON'::text;
            END IF;
            -- facts trong stage do máy chủ ghi phải trùng facts CSDL tự dẫn xuất (không cho máy chủ tự khai kind/ref khác bytes)
            IF q->>'raw_sha256' IS DISTINCT FROM v_raw OR (q->>'reference_id') IS DISTINCT FROM v_ref THEN
                RAISE EXCEPTION 'STAGE_KHONG_NHAT_QUAN: stage L11 khác facts CSDL của lần nhận' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO kho.bang_chung_ung_vien (phap_nhan_id, lan_tiep_nhan_id, source_instance_id, snapshot_id, source_row_id, stage_id, reference_id,
                evidence_revision, kind, raw_sha256, byte_length, payload_sha256, trang_thai, issues, coverage, coverage_hieu_luc, reported_errors, tao_boi)
            VALUES (sc.phap_nhan_id, l.id, l.source_instance_id, l.snapshot_id, b.id, s.id, v_ref, v_rev, v_kind, v_raw, v_len, v_payload,
                    CASE WHEN cardinality(v_issues) = 0 THEN 'UNG_VIEN' ELSE 'HOLD' END, v_issues, l.coverage, l.coverage_hieu_luc, l.reported_errors, ai)
            RETURNING id INTO v_id;
            RETURN jsonb_build_object('ung_vien_id', v_id, 'trang_thai', CASE WHEN cardinality(v_issues) = 0 THEN 'UNG_VIEN' ELSE 'HOLD' END,
                                      'issues', to_jsonb(v_issues), 'lap_lai', false);
        END $$""",
    _CHOT_M16,
    # ---- token đồ thị bằng chứng (CAS cho xác nhận/thu hồi) + danh sách theo quyền hiện hành (raw candidate chỉ với READ_SOURCE nguồn bằng chứng)
    """CREATE OR REPLACE FUNCTION kho.l11_co_so_bang_chung_noi_bo(p_pn uuid, p_ung_vien uuid, p_bang_chung uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT jsonb_build_object('contract', 'l11-proof-graph/v1', 'pn', p_pn,
            'ung_vien', (SELECT jsonb_build_object('id', u.id, 'trang_thai', u.trang_thai, 'ref', u.reference_id, 'rev', u.evidence_revision, 'kind', u.kind,
                                                   'raw', u.raw_sha256, 'payload', u.payload_sha256, 'issues', to_jsonb(u.issues))
                         FROM kho.bang_chung_ung_vien u WHERE u.id = p_ung_vien),
            'bang_chung', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'ref', q.reference_id, 'rev', q.evidence_revision, 'kind', q.kind,
                                                                        'trang_thai', q.trang_thai, 'ung_vien', q.ung_vien_id) ORDER BY q.id), '[]'::jsonb)
                           FROM kho.bang_chung_quy_doi_luong q WHERE q.phap_nhan_id = p_pn),
            'chon', p_bang_chung,
            'dong_lien_quan', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', c.id, 'tt', c.trang_thai, 'hl', c.hieu_luc) ORDER BY c.id), '[]'::jsonb)
                               FROM kho.lien_ket_dong c WHERE p_bang_chung IS NOT NULL AND c.phap_nhan_id = p_pn
                                 AND (c.bang_chung_hang_id = p_bang_chung OR c.bang_chung_ty_le_id = p_bang_chung)))
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_danh_sach_bang_chung() RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        BEGIN
            RETURN jsonb_build_object(
                'ung_vien', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', u.id, 'phap_nhan_id', u.phap_nhan_id, 'reference_id', u.reference_id,
                                     'evidence_revision', u.evidence_revision, 'kind', u.kind, 'raw_sha256', u.raw_sha256, 'byte_length', u.byte_length,
                                     'trang_thai', u.trang_thai, 'issues', to_jsonb(u.issues), 'lan_tiep_nhan_id', u.lan_tiep_nhan_id, 'tao_luc', u.tao_luc,
                                     'coverage', u.coverage, 'coverage_hieu_luc', u.coverage_hieu_luc, 'reported_errors', to_jsonb(u.reported_errors),
                                     'expected_graph', """ + _L11_TOKEN.format(x="kho.l11_co_so_bang_chung_noi_bo(u.phap_nhan_id, u.id, NULL)") + """,
                                     'facts', (SELECT r.row_raw FROM kho.ban_ghi_nguon r WHERE r.id = u.source_row_id),
                                     'bang_chung_id', (SELECT q.id FROM kho.bang_chung_quy_doi_luong q WHERE q.ung_vien_id = u.id))
                                     ORDER BY u.tao_luc, u.id), '[]'::jsonb)
                             FROM kho.bang_chung_ung_vien u JOIN giao_tiep.lan_tiep_nhan_nguon l ON l.id = u.lan_tiep_nhan_id
                             WHERE kho.l11_quyen_noi_bo(u.phap_nhan_id, 'READ')
                               AND master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'READ_SOURCE', NULL)),
                'bang_chung', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'phap_nhan_id', q.phap_nhan_id, 'reference_id', q.reference_id,
                                     'evidence_revision', q.evidence_revision, 'kind', q.kind, 'trang_thai', q.trang_thai, 'raw_sha256', q.raw_sha256,
                                     'hang_hoa_hoa_don', q.hang_hoa_hoa_don, 'hang_hoa_kho', q.hang_hoa_kho,
                                     'tu_don_vi', (SELECT x.reference_id FROM master.dinh_nghia_don_vi_luong x WHERE x.id = q.tu_don_vi_id),
                                     'den_don_vi', (SELECT x.reference_id FROM master.dinh_nghia_don_vi_luong x WHERE x.id = q.den_don_vi_id),
                                     'don_vi', (SELECT x.reference_id FROM master.dinh_nghia_don_vi_luong x WHERE x.id = q.don_vi_id),
                                     'tu_so', q.tu_so::text, 'mau_so', q.mau_so::text, 'native_xml_sha256', q.native_xml_sha256,
                                     'native_byte_length', q.native_byte_length,
                                     'unit_lexeme', q.unit_lexeme, 'mien', q.mien, 'xac_nhan_boi', q.xac_nhan_boi, 'xac_nhan_luc', q.xac_nhan_luc,
                                     'thu_hoi_boi', q.thu_hoi_boi, 'thu_hoi_luc', q.thu_hoi_luc, 'thu_hoi_ly_do', q.thu_hoi_ly_do,
                                     'expected_graph', """ + _L11_TOKEN.format(x="kho.l11_co_so_bang_chung_noi_bo(q.phap_nhan_id, q.ung_vien_id, q.id)") + """)
                                     ORDER BY q.kind, q.reference_id), '[]'::jsonb)
                               FROM kho.bang_chung_quy_doi_luong q WHERE kho.l11_quyen_noi_bo(q.phap_nhan_id, 'READ')));
        END $$""",
    # ---- CFO BOTH V4 + SOURCE_MAP nguồn bằng chứng → PN: xác nhận facts dẫn xuất từ raw đã capture (không factor/kind/PROVEN từ trình duyệt)
    """CREATE OR REPLACE FUNCTION kho.l11_xac_nhan_bang_chung(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); u record; l record; r jsonb; v_req jsonb; v_h text; cu record; v_tok text; v_pn_ma text;
            v_g uuid; v_fu record; v_tu_dv record; v_dv record; v_tu numeric; v_mau numeric; v_id uuid; v_bn uuid; v_ket jsonb; v_cur record;
            v_len bigint; v_row record; v_gq record; v_loi text;
        BEGIN
            SELECT x.* INTO u FROM kho.bang_chung_ung_vien x WHERE x.id = kho.l11_uuid(p->>'candidate_id');
            IF u.id IS NULL OR NOT kho.l11_quyen_noi_bo(u.phap_nhan_id, 'CFO') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_BANG_CHUNG: cần CFO có V4 + M2 + M5 hiện hành trên PN của bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = u.lan_tiep_nhan_id;
            IF NOT master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'SOURCE_MAP', u.phap_nhan_id) THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_BANG_CHUNG: cần SOURCE_MAP hiện hành của nguồn bằng chứng → PN' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'expected_graph', '') !~ """ + _L11_HEX + """ THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần ứng viên, token đồ thị đang xem, khóa và lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || u.phap_nhan_id || '|M5|L11_PROOF_CONFIRM|' || (p->>'client_key'), 0));
            PERFORM pg_advisory_xact_lock(hashtextextended('L11_BANG_CHUNG|' || u.phap_nhan_id, 0));
            v_req := jsonb_build_object('operation', 'L11_PROOF_CONFIRM', 'candidate_id', p->'candidate_id', 'expected_graph', p->'expected_graph',
                                        'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = u.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_PROOF_CONFIRM' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                SELECT q.id, q.trang_thai INTO v_cur FROM kho.bang_chung_quy_doi_luong q WHERE q.ung_vien_id = u.id;
                RETURN cu.result_json || jsonb_build_object('trang_thai', v_cur.trang_thai, 'bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            v_tok := """ + _L11_TOKEN.format(x="kho.l11_co_so_bang_chung_noi_bo(u.phap_nhan_id, u.id, NULL)") + """;
            IF p->>'expected_graph' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: đồ thị bằng chứng đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            IF u.trang_thai <> 'UNG_VIEN' THEN
                RAISE EXCEPTION 'L11_BANG_CHUNG_HOLD: ứng viên đang HOLD (%) — không xác nhận', array_to_string(u.issues, ',') USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM kho.bang_chung_quy_doi_luong q WHERE q.ung_vien_id = u.id OR (q.phap_nhan_id = u.phap_nhan_id
                       AND q.reference_id = u.reference_id AND q.evidence_revision = u.evidence_revision)) THEN
                RAISE EXCEPTION 'L11_BANG_CHUNG_DA_XAC_NHAN: tham chiếu/revision này đã có bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.row_raw INTO r FROM kho.ban_ghi_nguon x WHERE x.id = u.source_row_id;
            SELECT ma INTO v_pn_ma FROM master.phap_nhan WHERE id = u.phap_nhan_id;
            IF r->>'pn_ma' IS DISTINCT FROM v_pn_ma THEN
                RAISE EXCEPTION 'L11_PHAP_NHAN_KHAC: bằng chứng khai PN khác' USING ERRCODE = 'P0001';
            END IF;
            v_id := gen_random_uuid();
            v_ket := jsonb_build_object('bang_chung_id', v_id, 'candidate_id', u.id, 'reference_id', u.reference_id, 'evidence_revision', u.evidence_revision,
                                        'kind', u.kind, 'trang_thai', 'DA_XAC_NHAN');
            IF u.kind = 'GOODS_EQUIVALENCE' THEN
                -- R3/R4 repair02: miền khai báo TƯỜNG MINH (instance/profile/company/kho/mapping/mã hàng) được lưu và đối chiếu ngữ cảnh nguồn thật
                -- của từng cặp khi đánh giá — không chỉ tuple native hỗ trợ
                IF coalesce(r#>>'{domain,invoice,item_code}', '') = '' OR coalesce(r#>>'{domain,warehouse,item_code}', '') = ''
                   OR coalesce(r#>>'{domain,invoice,source_instance}', '') = '' OR coalesce(r#>>'{domain,invoice,profile_ref}', '') = ''
                   OR coalesce(r#>>'{domain,invoice,profile_payload_sha256}', '') !~ """ + _L11_HEX + """
                   OR coalesce(r#>>'{domain,invoice,company_key}', '') = '' OR coalesce(r#>>'{domain,invoice,company_mapping_ref}', '') = ''
                   OR coalesce(r#>>'{domain,warehouse,source_instance}', '') = '' OR coalesce(r#>>'{domain,warehouse,profile_ref}', '') = ''
                   OR coalesce(r#>>'{domain,warehouse,profile_payload_sha256}', '') !~ """ + _L11_HEX + """
                   OR coalesce(r#>>'{domain,warehouse,MaKho}', '') = '' OR coalesce(r#>>'{domain,warehouse,warehouse_mapping_ref}', '') = ''
                   OR jsonb_typeof(r->'supporting_native_bindings') IS DISTINCT FROM 'array' OR jsonb_array_length(r->'supporting_native_bindings') = 0 THEN
                    RAISE EXCEPTION 'L11_BANG_CHUNG_HINH_DANG: bằng chứng hàng thiếu miền/binding tường minh' USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                VALUES (u.phap_nhan_id, 'M5', 'L11_PROOF_CONFIRM', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
                INSERT INTO kho.bang_chung_quy_doi_luong (id, phap_nhan_id, ung_vien_id, reference_id, evidence_revision, kind, raw_sha256, byte_length,
                    payload_sha256, hang_hoa_hoa_don, hang_hoa_kho, rang_buoc, mien, trang_thai, xac_nhan_boi, xac_nhan_bien_nhan_id)
                VALUES (v_id, u.phap_nhan_id, u.id, u.reference_id, u.evidence_revision, u.kind, u.raw_sha256, u.byte_length, u.payload_sha256,
                        r#>>'{domain,invoice,item_code}', r#>>'{domain,warehouse,item_code}', r->'supporting_native_bindings',
                        jsonb_build_object(
                            'invoice', jsonb_build_object('source_instance', r#>>'{domain,invoice,source_instance}', 'profile_ref', r#>>'{domain,invoice,profile_ref}',
                                                          'profile_payload_sha256', r#>>'{domain,invoice,profile_payload_sha256}',
                                                          'company_key', r#>>'{domain,invoice,company_key}',
                                                          'company_mapping_ref', r#>>'{domain,invoice,company_mapping_ref}', 'item_code', r#>>'{domain,invoice,item_code}'),
                            'warehouse', jsonb_build_object('source_instance', r#>>'{domain,warehouse,source_instance}', 'profile_ref', r#>>'{domain,warehouse,profile_ref}',
                                                            'profile_payload_sha256', r#>>'{domain,warehouse,profile_payload_sha256}', 'MaKho', r#>>'{domain,warehouse,MaKho}',
                                                            'warehouse_mapping_ref', r#>>'{domain,warehouse,warehouse_mapping_ref}',
                                                            'item_code', r#>>'{domain,warehouse,item_code}')),
                        'DA_XAC_NHAN', ai, v_bn);
            ELSIF u.kind = 'CROSS_NATIVE_RATIO' THEN
                SELECT x.id, x.definition_sha256 INTO v_fu FROM master.dinh_nghia_don_vi_luong x
                    WHERE x.reference_id = r->>'from_definition_ref' AND x.definition_sha256 = r->>'from_definition_payload_sha256';
                SELECT x.id, x.definition_sha256 INTO v_tu_dv FROM master.dinh_nghia_don_vi_luong x
                    WHERE x.reference_id = r->>'to_definition_ref' AND x.definition_sha256 = r->>'to_definition_payload_sha256';
                IF v_fu.id IS NULL OR v_tu_dv.id IS NULL THEN
                    RAISE EXCEPTION 'L11_DON_VI_CHUA_DANG_KY: định nghĩa đơn vị nguồn/đích chưa có trong registry với đúng digest' USING ERRCODE = 'P0001';
                END IF;
                IF v_fu.id = v_tu_dv.id THEN
                    RAISE EXCEPTION 'L11_TY_LE_CUNG_DON_VI: tỷ lệ cross-native cần hai định nghĩa khác nhau' USING ERRCODE = 'P0001';
                END IF;
                -- R2: hai định nghĩa NATIVE phải đã xác minh qua MASTER chung (tuple tài liệu khai báo), không chỉ khớp ref + digest
                IF kho.l11_don_vi_xac_minh_noi_bo(v_fu.id) IS NOT NULL OR kho.l11_don_vi_xac_minh_noi_bo(v_tu_dv.id) IS NOT NULL THEN
                    RAISE EXCEPTION 'L11_DON_VI_CHUA_XAC_MINH: định nghĩa đơn vị native của tỷ lệ chưa xác minh qua tài liệu khai báo' USING ERRCODE = 'P0001';
                END IF;
                v_tu := kho.l11_so_ty_le(r->'numerator_text'); v_mau := kho.l11_so_ty_le(r->'denominator_text');
                IF v_tu IS NULL OR v_mau IS NULL THEN
                    RAISE EXCEPTION 'L11_TY_LE_SAI: tỷ lệ phải là CHUỖI số nguyên dương ≤38 chữ số (không Number/thập phân/0)' USING ERRCODE = 'P0001';
                END IF;
                IF gcd(v_tu, v_mau) <> 1 THEN
                    RAISE EXCEPTION 'L11_TY_LE_CHUA_TOI_GIAN: tỷ lệ phải tối giản (không tự rút gọn)' USING ERRCODE = 'P0001';
                END IF;
                SELECT q.id INTO v_g FROM kho.bang_chung_quy_doi_luong q WHERE q.phap_nhan_id = u.phap_nhan_id AND q.kind = 'GOODS_EQUIVALENCE'
                    AND q.reference_id = r->>'goods_equivalence_ref' AND q.raw_sha256 = r->>'goods_evidence_sha256' AND q.trang_thai = 'DA_XAC_NHAN' FOR SHARE;
                IF v_g IS NULL THEN
                    RAISE EXCEPTION 'L11_THIEU_BANG_CHUNG_HANG: cần bằng chứng hàng hóa đã xác nhận đúng ref/raw SHA' USING ERRCODE = 'P0001';
                END IF;
                IF EXISTS (SELECT 1 FROM kho.bang_chung_quy_doi_luong q WHERE q.phap_nhan_id = u.phap_nhan_id AND q.kind = 'CROSS_NATIVE_RATIO'
                           AND q.trang_thai = 'DA_XAC_NHAN' AND q.hang_hoa_bang_chung_id = v_g
                           AND ((q.tu_don_vi_id = v_fu.id AND q.den_don_vi_id = v_tu_dv.id AND q.tu_so * v_mau <> q.mau_so * v_tu)
                                OR (q.tu_don_vi_id = v_tu_dv.id AND q.den_don_vi_id = v_fu.id AND q.tu_so * v_tu <> q.mau_so * v_mau))) THEN
                    RAISE EXCEPTION 'L11_TY_LE_XUNG_DOT: đã có tỷ lệ hiệu lực khác cho cùng định nghĩa/hàng hóa — HOLD' USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                VALUES (u.phap_nhan_id, 'M5', 'L11_PROOF_CONFIRM', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
                INSERT INTO kho.bang_chung_quy_doi_luong (id, phap_nhan_id, ung_vien_id, reference_id, evidence_revision, kind, raw_sha256, byte_length,
                    payload_sha256, hang_hoa_bang_chung_id, tu_don_vi_id, tu_don_vi_sha256, den_don_vi_id, den_don_vi_sha256, tu_so, mau_so, rang_buoc,
                    trang_thai, xac_nhan_boi, xac_nhan_bien_nhan_id)
                VALUES (v_id, u.phap_nhan_id, u.id, u.reference_id, u.evidence_revision, u.kind, u.raw_sha256, u.byte_length, u.payload_sha256, v_g,
                        v_fu.id, v_fu.definition_sha256, v_tu_dv.id, v_tu_dv.definition_sha256, v_tu, v_mau,
                        CASE WHEN jsonb_typeof(r->'supported_warehouse_bindings') = 'array' THEN r->'supported_warehouse_bindings' ELSE '[]'::jsonb END,
                        'DA_XAC_NHAN', ai, v_bn);
            ELSIF u.kind = 'NATIVE_ENCODING' THEN
                -- R2 repair02: HAI tuple riêng — đơn vị NATIVE của dòng (unit_definition: ref + digest) và đơn vị OWN-POOL (pool_unit_definition_ref
                -- [+ digest khi khai]) — cả hai đã xác minh qua MASTER chung; tỷ lệ native→pool khai báo độc lập, không ép pool = native
                SELECT x.* INTO v_dv FROM master.dinh_nghia_don_vi_luong x
                    WHERE x.reference_id = r#>>'{unit_definition,reference_id}' AND x.definition_sha256 = r#>>'{unit_definition,definition_sha256}';
                SELECT x.* INTO v_fu FROM master.dinh_nghia_don_vi_luong x WHERE x.reference_id = r->>'pool_unit_definition_ref'
                    AND (NOT (r ? 'pool_unit_definition_sha256') OR x.definition_sha256 = r->>'pool_unit_definition_sha256');
                IF v_dv.id IS NULL OR v_fu.id IS NULL THEN
                    RAISE EXCEPTION 'L11_DON_VI_CHUA_DANG_KY: định nghĩa đơn vị native/pool của mã hóa chưa có đúng digest' USING ERRCODE = 'P0001';
                END IF;
                IF kho.l11_don_vi_xac_minh_noi_bo(v_dv.id) IS NOT NULL OR kho.l11_don_vi_xac_minh_noi_bo(v_fu.id) IS NOT NULL THEN
                    RAISE EXCEPTION 'L11_DON_VI_CHUA_XAC_MINH: định nghĩa native/pool của mã hóa chưa xác minh qua tài liệu khai báo' USING ERRCODE = 'P0001';
                END IF;
                IF coalesce((r#>>'{native_to_pool_ratio,same_definition_required}')::boolean, false) AND v_dv.id <> v_fu.id THEN
                    RAISE EXCEPTION 'L11_DON_VI_POOL_KHAC: mã hóa khai báo yêu cầu cùng định nghĩa native/pool' USING ERRCODE = 'P0001';
                END IF;
                -- hỗ trợ khai báo của định nghĩa native phải trỏ ĐÚNG artifact/locator/lexeme của mã hóa (trường thật kiểm lại khi mã hóa dòng)
                IF v_dv.support_raw_sha256 IS DISTINCT FROM r->>'native_xml_sha256' OR v_dv.support_locator IS DISTINCT FROM r->>'unit_field_locator'
                   OR v_dv.payload->>'native_unit_code' IS DISTINCT FROM r->>'unit_decoded_lexeme'
                   OR (r ? 'profile_ref_unchanged' AND r->>'profile_ref_unchanged' IS DISTINCT FROM v_dv.support_profile_ref) THEN
                    RAISE EXCEPTION 'L11_BANG_CHUNG_MA_HOA_KHONG_KHOP: định nghĩa native không hỗ trợ đúng artifact/locator/lexeme/profile của mã hóa'
                        USING ERRCODE = 'P0001';
                END IF;
                v_tu := kho.l11_so_ty_le(r#>'{native_to_pool_ratio,numerator_text}'); v_mau := kho.l11_so_ty_le(r#>'{native_to_pool_ratio,denominator_text}');
                IF v_tu IS NULL OR v_mau IS NULL THEN
                    RAISE EXCEPTION 'L11_TY_LE_SAI: tỷ lệ native→pool phải là CHUỖI số nguyên dương' USING ERRCODE = 'P0001';
                END IF;
                IF gcd(v_tu, v_mau) <> 1 THEN
                    RAISE EXCEPTION 'L11_TY_LE_CHUA_TOI_GIAN: tỷ lệ native→pool phải tối giản' USING ERRCODE = 'P0001';
                END IF;
                IF v_dv.id = v_fu.id AND (v_tu <> 1 OR v_mau <> 1) THEN
                    RAISE EXCEPTION 'L11_TY_LE_SAI: cùng định nghĩa native/pool chỉ có tỷ lệ 1/1' USING ERRCODE = 'P0001';
                END IF;
                IF coalesce(r->>'native_xml_sha256', '') !~ """ + _L11_HEX + """ OR coalesce(r->>'quantity_field_locator', '') = ''
                   OR coalesce(r->>'unit_field_locator', '') = '' OR coalesce(r->>'unit_decoded_lexeme', '') = '' THEN
                    RAISE EXCEPTION 'L11_BANG_CHUNG_HINH_DANG: mã hóa native thiếu artifact/locator/lexeme' USING ERRCODE = 'P0001';
                END IF;
                SELECT q.id INTO v_g FROM kho.bang_chung_quy_doi_luong q WHERE q.phap_nhan_id = u.phap_nhan_id AND q.kind = 'GOODS_EQUIVALENCE'
                    AND q.raw_sha256 = r->>'goods_domain_evidence_sha256' AND q.trang_thai = 'DA_XAC_NHAN' FOR SHARE;
                IF v_g IS NULL THEN
                    RAISE EXCEPTION 'L11_THIEU_BANG_CHUNG_HANG: mã hóa cần bằng chứng hàng hóa đã xác nhận đúng raw SHA' USING ERRCODE = 'P0001';
                END IF;
                -- repair03 (C): TRƯỚC khi ghi bằng chứng đã duyệt — claim độ dài native là SỐ NGUYÊN DƯƠNG chính xác (JSON number, không chuỗi/
                -- thập phân/0/âm), và nguồn THẬT đã capture qua COMMON + reader (dòng XML_LINE) trong đúng ngữ cảnh instance/profile hỗ trợ của định
                -- nghĩa native: đúng artifact SHA + độ dài thật (dòng reader + catalog), locator, lexeme đơn vị/số lượng, mã hàng của miền hàng; rồi trường
                -- hỗ trợ khai báo của định nghĩa (l11_ho_tro_don_vi_noi_bo). Không coi self-H tài liệu/FK catalog/H proof đã đăng ký là kiểm claim.
                IF jsonb_typeof(r->'native_byte_length') IS DISTINCT FROM 'number' OR coalesce(r->>'native_byte_length', '') !~ '^[1-9][0-9]{0,17}$' THEN
                    RAISE EXCEPTION 'L11_DO_DAI_NATIVE_SAI: native_byte_length phải là số nguyên dương chính xác' USING ERRCODE = 'P0001';
                END IF;
                v_len := (r->>'native_byte_length')::bigint;
                SELECT g.* INTO v_gq FROM kho.bang_chung_quy_doi_luong g WHERE g.id = v_g;
                IF v_gq.mien->'invoice'->>'source_instance' IS DISTINCT FROM v_dv.support_source_instance_id
                   OR v_gq.mien->'invoice'->>'profile_ref' IS DISTINCT FROM v_dv.support_profile_ref
                   OR v_gq.mien->'invoice'->>'profile_payload_sha256' IS DISTINCT FROM v_dv.support_profile_sha256 THEN
                    RAISE EXCEPTION 'L11_BANG_CHUNG_MA_HOA_KHONG_KHOP: ngữ cảnh hỗ trợ của định nghĩa native khác miền hóa đơn của bằng chứng hàng' USING ERRCODE = 'P0001';
                END IF;
                SELECT r0.* INTO v_row FROM kho.ban_ghi_nguon r0 JOIN kho.anh_chup_nguon a0 ON a0.id = r0.snapshot_id
                    WHERE r0.section = 'XML_LINE' AND r0.row_raw->>'native_xml_sha256' = r->>'native_xml_sha256'
                      AND a0.source_instance_id = v_dv.support_source_instance_id AND a0.profile_ref = v_dv.support_profile_ref
                      AND a0.profile_sha256 = v_dv.support_profile_sha256 AND (r0.row_raw->>'source_locator') || '/DVTinh' = r->>'unit_field_locator'
                    ORDER BY r0.id LIMIT 1;
                IF v_row.id IS NULL THEN
                    RAISE EXCEPTION 'L11_HO_TRO_CHUA_CAPTURE: chưa có nguồn thật đã capture đúng artifact/locator/ngữ cảnh của mã hóa — giữ raw, chưa duyệt'
                        USING ERRCODE = 'P0001';
                END IF;
                IF (v_row.row_raw->>'byte_length')::bigint IS DISTINCT FROM v_len
                   OR (SELECT DISTINCT c.byte_length FROM master.nguon_master_noi_dung c WHERE c.raw_sha256 = r->>'native_xml_sha256') IS DISTINCT FROM v_len THEN
                    RAISE EXCEPTION 'L11_DO_DAI_NATIVE_SAI: độ dài native khai báo khác độ dài thật của artifact đã capture' USING ERRCODE = 'P0001';
                END IF;
                IF v_row.row_raw->>'unit_raw' IS DISTINCT FROM r->>'unit_decoded_lexeme'
                   OR (r ? 'quantity_decoded_lexeme' AND v_row.row_raw->>'quantity_raw' IS DISTINCT FROM r->>'quantity_decoded_lexeme')
                   OR (v_row.row_raw->>'source_locator') || '/SLuong' IS DISTINCT FROM r->>'quantity_field_locator'
                   OR v_row.row_raw->'fields'->'MHHDVu'->0->>'lexeme' IS DISTINCT FROM v_gq.hang_hoa_hoa_don THEN
                    RAISE EXCEPTION 'L11_HO_TRO_DON_VI_KHONG_KHOP: trường đơn vị/số lượng/mã hàng thật đã capture khác claim của mã hóa' USING ERRCODE = 'P0001';
                END IF;
                v_loi := kho.l11_ho_tro_don_vi_noi_bo(v_dv.id, v_gq.hang_hoa_hoa_don);
                IF v_loi IS NOT NULL THEN
                    RAISE EXCEPTION '%: hỗ trợ khai báo của định nghĩa native chưa có trường thật đã capture', v_loi USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                VALUES (u.phap_nhan_id, 'M5', 'L11_PROOF_CONFIRM', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
                INSERT INTO kho.bang_chung_quy_doi_luong (id, phap_nhan_id, ung_vien_id, reference_id, evidence_revision, kind, raw_sha256, byte_length,
                    payload_sha256, hang_hoa_bang_chung_id, tu_don_vi_id, tu_don_vi_sha256, den_don_vi_id, den_don_vi_sha256, tu_so, mau_so,
                    native_xml_sha256, native_byte_length, quantity_locator, unit_locator, unit_lexeme, quantity_lexeme, rang_buoc, mien, trang_thai,
                    xac_nhan_boi, xac_nhan_bien_nhan_id)
                VALUES (v_id, u.phap_nhan_id, u.id, u.reference_id, u.evidence_revision, u.kind, u.raw_sha256, u.byte_length, u.payload_sha256, v_g,
                        v_dv.id, v_dv.definition_sha256, v_fu.id, v_fu.definition_sha256, v_tu, v_mau, r->>'native_xml_sha256', v_len,
                        r->>'quantity_field_locator', r->>'unit_field_locator', r->>'unit_decoded_lexeme', r->>'quantity_decoded_lexeme', '[]'::jsonb,
                        jsonb_build_object('source_instance', v_dv.support_source_instance_id, 'profile_ref', v_dv.support_profile_ref,
                                           'profile_sha256', v_dv.support_profile_sha256),
                        'DA_XAC_NHAN', ai, v_bn);
            ELSE
                RAISE EXCEPTION 'L11_LOAI_BANG_CHUNG_LA' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (u.phap_nhan_id, ai, 'HE_THONG', 'kho.bang_chung_quy_doi_luong', v_id, 'L11_PROOF_CONFIRM', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # thu hồi: quyền hiện hành → namespace/H/replay → closure child sống (trực tiếp + qua bằng chứng phụ thuộc) → khóa gốc theo thứ tự chuẩn →
    # khóa bằng chứng (FOR UPDATE, chờ confirm đang giữ FOR SHARE) → đọc lại closure; mở rộng ⇒ rollback/thử lại; rồi CAN_SOAT đồng bộ (giữ lượng cũ)
    """CREATE OR REPLACE FUNCTION kho.l11_huy_bang_chung(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); q record; u record; l record; v_req jsonb; v_h text; cu record; v_tok text; v_hd uuid[]; v_pk uuid[];
            v_dong0 uuid[]; v_pool uuid[]; v_dong uuid[]; v_bn uuid; v_ket jsonb; v_n integer;
        BEGIN
            SELECT x.* INTO q FROM kho.bang_chung_quy_doi_luong x WHERE x.id = kho.l11_uuid(p->>'proof_id');
            IF q.id IS NULL OR NOT kho.l11_quyen_noi_bo(q.phap_nhan_id, 'CFO') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_BANG_CHUNG: cần CFO có V4 + M2 + M5 hiện hành trên PN của bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO u FROM kho.bang_chung_ung_vien x WHERE x.id = q.ung_vien_id;
            SELECT x.* INTO l FROM giao_tiep.lan_tiep_nhan_nguon x WHERE x.id = u.lan_tiep_nhan_id;
            IF NOT master.ktt_nguon_duoc(l.source_instance_id, l.profile_ref, l.profile_sha256, 'SOURCE_MAP', q.phap_nhan_id) THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_BANG_CHUNG: cần SOURCE_MAP hiện hành của nguồn bằng chứng → PN' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'expected_graph', '') !~ """ + _L11_HEX + """ THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần bằng chứng, token đồ thị đang xem, khóa và lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || q.phap_nhan_id || '|M5|L11_PROOF_REVOKE|' || (p->>'client_key'), 0));
            v_req := jsonb_build_object('operation', 'L11_PROOF_REVOKE', 'proof_id', p->'proof_id', 'expected_graph', p->'expected_graph', 'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = q.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_PROOF_REVOKE' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('trang_thai', (SELECT x.trang_thai FROM kho.bang_chung_quy_doi_luong x WHERE x.id = q.id),
                                                            'bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            -- repair03 (R1-L02): precollect MỘT lần child + gốc + pool của closure; giữ gốc; đọc lại tập child TRÙNG KHÍT trước khi xin pool/hàng;
            -- giữ pool đã bind → hàng child → hàng bằng chứng; đọc lại lần nữa (confirm gốc khác đã commit trong lúc chờ hàng bằng chứng) → khác ⇒ hủy
            SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') INTO v_dong0
                FROM kho.lien_ket_dong c WHERE c.trang_thai = 'DA_KHOP' AND kho.l11_dong_dung_bang_chung_noi_bo(c.id, q.id);
            SELECT array_agg(DISTINCT c.hoa_don_id ORDER BY c.hoa_don_id), array_agg(DISTINCT c.phieu_id ORDER BY c.phieu_id) INTO v_hd, v_pk
                FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong0);
            SELECT coalesce(array_agg(DISTINCT z.x ORDER BY z.x), '{}') INTO v_pool FROM (
                SELECT c.pool_hoa_don_id AS x FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong0)
                UNION SELECT c.pool_phieu_id FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong0)) z;
            PERFORM kho.l11_khoa_goc_noi_bo(v_hd, v_pk);
            SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') INTO v_dong
                FROM kho.lien_ket_dong c WHERE c.trang_thai = 'DA_KHOP' AND kho.l11_dong_dung_bang_chung_noi_bo(c.id, q.id);
            IF v_dong IS DISTINCT FROM v_dong0 THEN
                RAISE EXCEPTION 'L11_CLOSURE_MO_RONG: tập liên kết dùng bằng chứng đã đổi trong lúc chờ khóa gốc — thử lại toàn thao tác (0 hiệu lực)'
                    USING ERRCODE = 'P0001';
            END IF;
            PERFORM kho.l11_khoa_pool_noi_bo(v_pool);
            PERFORM 1 FROM kho.lien_ket_dong c WHERE c.id = ANY (v_dong0) ORDER BY c.id FOR UPDATE;
            SELECT x.* INTO q FROM kho.bang_chung_quy_doi_luong x WHERE x.id = q.id FOR UPDATE;
            SELECT coalesce(array_agg(c.id ORDER BY c.id), '{}') INTO v_dong
                FROM kho.lien_ket_dong c WHERE c.trang_thai = 'DA_KHOP' AND kho.l11_dong_dung_bang_chung_noi_bo(c.id, q.id);
            IF v_dong IS DISTINCT FROM v_dong0 THEN
                RAISE EXCEPTION 'L11_CLOSURE_MO_RONG: có liên kết mới dùng bằng chứng trong lúc chờ khóa — thử lại toàn thao tác (0 hiệu lực)' USING ERRCODE = 'P0001';
            END IF;
            v_tok := """ + _L11_TOKEN.format(x="kho.l11_co_so_bang_chung_noi_bo(q.phap_nhan_id, q.ung_vien_id, q.id)") + """;
            IF p->>'expected_graph' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: đồ thị bằng chứng đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            IF q.trang_thai <> 'DA_XAC_NHAN' THEN
                RAISE EXCEPTION 'L11_BANG_CHUNG_DA_THU_HOI: bằng chứng đã thu hồi' USING ERRCODE = 'P0001';
            END IF;
            v_ket := jsonb_build_object('bang_chung_id', q.id, 'reference_id', q.reference_id, 'trang_thai', 'DA_THU_HOI');
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (q.phap_nhan_id, 'M5', 'L11_PROOF_REVOKE', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            UPDATE kho.bang_chung_quy_doi_luong SET trang_thai = 'DA_THU_HOI', thu_hoi_boi = ai, thu_hoi_luc = now(), thu_hoi_bien_nhan_id = v_bn,
                thu_hoi_ly_do = p->>'reason' WHERE id = q.id;
            v_n := kho.l11_can_soat_noi_bo(v_dong, 'BANG_CHUNG_THU_HOI');
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (q.phap_nhan_id, ai, 'HE_THONG', 'kho.bang_chung_quy_doi_luong', q.id, 'L11_PROOF_REVOKE', v_ket || jsonb_build_object('can_soat', v_n),
                    p->>'reason');
            RETURN v_ket || jsonb_build_object('so_dong_can_soat', v_n, 'bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_dong_dung_bang_chung_noi_bo(p_dong uuid, p_bang_chung uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM kho.lien_ket_dong c WHERE c.id = p_dong AND (
                   c.bang_chung_hang_id = p_bang_chung OR c.bang_chung_ty_le_id = p_bang_chung
                   OR EXISTS (SELECT 1 FROM kho.ma_hoa_luong_nguon e WHERE e.id IN (c.ma_hoa_hoa_don_id, c.ma_hoa_phieu_id) AND e.bang_chung_ma_hoa_id = p_bang_chung)
                   OR EXISTS (SELECT 1 FROM kho.bang_chung_quy_doi_luong d WHERE d.hang_hoa_bang_chung_id = p_bang_chung AND (d.id = c.bang_chung_ty_le_id
                              OR EXISTS (SELECT 1 FROM kho.ma_hoa_luong_nguon e WHERE e.id IN (c.ma_hoa_hoa_don_id, c.ma_hoa_phieu_id)
                                         AND e.bang_chung_ma_hoa_id = d.id)))))
        $$""",
    # ---- mã hóa nguồn (CFO BOTH V4): PB-line typed hiện hành → pool ổn định theo gốc logic + mã hóa bất biến. CAI: định nghĩa đã xác minh cùng
    #      ngữ cảnh (không theo nhãn); THUNG: bằng chứng NATIVE_ENCODING đã xác nhận khớp artifact/locator/lexeme thật. Không pool theo key/PB.
    """CREATE OR REPLACE FUNCTION kho.l11_co_so_ma_hoa_noi_bo(p_side text, p_id uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF p_side = 'M2' THEN
                RETURN (SELECT jsonb_build_object('contract', 'l11-encoding-graph/v1', 'side', 'M2', 'cau_noi', b.id, 'pb', b.hoa_don_phien_ban_id,
                            'dong', b.dong_danh_tinh_id, 'fs', b.field_state_sha256, 'q', b.quantity_raw, 'u', b.unit_raw, 'unit_def', b.unit_definition_id,
                            'eligible', d.eligible_content_id, 'accepted', d.accepted_source_observation_id,
                            'pool', (SELECT jsonb_build_object('id', x.id, 'don_vi', x.don_vi_id) FROM kho.dich_so_luong x WHERE x.phap_nhan_id = b.phap_nhan_id
                                     AND x.pool_kind = 'L11' AND x.hoa_don_dong_id = b.dong_danh_tinh_id),
                            'ma_hoa', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', e.id, 'rev', e.basis_revision) ORDER BY e.basis_revision), '[]'::jsonb)
                                       FROM kho.ma_hoa_luong_nguon e WHERE e.cau_noi_id = b.id),
                            'bang_chung', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'tt', q.trang_thai) ORDER BY q.id), '[]'::jsonb)
                                           FROM kho.bang_chung_quy_doi_luong q WHERE q.phap_nhan_id = b.phap_nhan_id AND q.kind = 'NATIVE_ENCODING'))
                        FROM kho.hoa_don_dong_phien_ban b JOIN kho.hoa_don_danh_tinh d ON d.id = b.hoa_don_id WHERE b.id = p_id);
            END IF;
            RETURN (SELECT jsonb_build_object('contract', 'l11-encoding-graph/v1', 'side', 'M5', 'dong_pb', lw.id, 'pb', lw.phien_ban_id, 'dong', lw.dong_id,
                        'q', lw.so_luong_raw, 'qn', lw.so_luong, 'u', lw.dvt_raw, 'unit_ref', lw.unit_definition_ref, 'eligible', d.eligible_content_id,
                        'accepted', d.accepted_source_observation_id, 'map', d.mapping_revision_id, 'do_luong', kho.l11_do_luong_dong_noi_bo(lw.id),
                        'pool', (SELECT jsonb_build_object('id', x.id, 'don_vi', x.don_vi_id) FROM kho.dich_so_luong x WHERE x.phap_nhan_id = lw.phap_nhan_id
                                 AND x.pool_kind = 'L11' AND x.phieu_dong_id = lw.dong_id),
                        'ma_hoa', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', e.id, 'rev', e.basis_revision) ORDER BY e.basis_revision), '[]'::jsonb)
                                   FROM kho.ma_hoa_luong_nguon e WHERE e.phieu_dong_phien_ban_id = lw.id))
                    FROM kho.phieu_kho_dong_phien_ban lw JOIN kho.phieu_kho_danh_tinh d ON d.id = lw.phieu_id WHERE lw.id = p_id);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_co_so_ma_hoa(p_side text, p_id uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_pn uuid; v jsonb;
        BEGIN
            IF p_side = 'M2' THEN
                SELECT x.phap_nhan_id INTO v_pn FROM kho.hoa_don_dong_phien_ban x WHERE x.id = p_id;
            ELSE
                SELECT x.phap_nhan_id INTO v_pn FROM kho.phieu_kho_dong_phien_ban x WHERE x.id = p_id;
            END IF;
            IF v_pn IS NULL OR NOT kho.l11_quyen_noi_bo(v_pn, 'READ') THEN
                RETURN NULL;
            END IF;
            v := kho.l11_co_so_ma_hoa_noi_bo(p_side, p_id);
            RETURN v || jsonb_build_object('expected_graph', """ + _L11_TOKEN.format(x="v") + """);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_ma_hoa(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); v_side text := p->>'side'; v_id uuid := kho.l11_uuid(p->>'line_id'); v_pn uuid; b record; lw record;
            d_hd record; d_pk record; ppb record; rw jsonb; q record; dv record; v_req jsonb; v_h text; cu record; v_tok text; v_native numeric;
            v_unit uuid; v_unit_sha text; v_tu numeric := 1; v_mau numeric := 1; v_can_cu text; v_proof uuid; v_cap numeric; v_pool record; v_pool_id uuid;
            v_rev integer; v_eid uuid; v_bn uuid; v_ket jsonb; v_prof_ref text; v_prof_sha text; v_qtext text; v_utext text; v_loi text; v_item text;
            v_nat uuid; v_nat_sha text; v_do_luong text; v_inst text; v_g record; v_cty record;
        BEGIN
            IF v_side = 'M2' THEN
                SELECT x.* INTO b FROM kho.hoa_don_dong_phien_ban x WHERE x.id = v_id;
                v_pn := b.phap_nhan_id;
            ELSIF v_side = 'M5' THEN
                SELECT x.* INTO lw FROM kho.phieu_kho_dong_phien_ban x WHERE x.id = v_id;
                v_pn := lw.phap_nhan_id;
            END IF;
            IF v_pn IS NULL OR NOT kho.l11_quyen_noi_bo(v_pn, 'CFO') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_MA_HOA: cần CFO có V4 + M2 + M5 hiện hành trên PN của dòng' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'expected_graph', '') !~ """ + _L11_HEX + """ OR (p ? 'proof_id' AND p->'proof_id' <> 'null'::jsonb AND kho.l11_uuid(p->>'proof_id') IS NULL) THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần dòng typed, token đồ thị, khóa, lý do (bằng chứng mã hóa nếu có)' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || v_pn || '|M5|L11_ENCODE|' || (p->>'client_key'), 0));
            v_req := jsonb_build_object('operation', 'L11_ENCODE', 'side', v_side, 'line_id', p->'line_id', 'proof_id', p->'proof_id',
                                        'expected_graph', p->'expected_graph', 'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = v_pn AND x.module = 'M5' AND x.operation = 'L11_ENCODE' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            -- R1: giao thức chung gốc → pool (đã có) → hàng danh tính/bằng chứng
            IF v_side = 'M2' THEN
                PERFORM kho.l11_khoa_goc_noi_bo(ARRAY[b.hoa_don_id], NULL);
                PERFORM kho.l11_khoa_pool_noi_bo(ARRAY(SELECT x.id FROM kho.dich_so_luong x WHERE x.phap_nhan_id = v_pn AND x.pool_kind = 'L11'
                                                         AND x.hoa_don_dong_id = b.dong_danh_tinh_id));
                SELECT x.* INTO d_hd FROM kho.hoa_don_danh_tinh x WHERE x.id = b.hoa_don_id FOR SHARE;
            ELSE
                PERFORM kho.l11_khoa_goc_noi_bo(NULL, ARRAY[lw.phieu_id]);
                PERFORM kho.l11_khoa_pool_noi_bo(ARRAY(SELECT x.id FROM kho.dich_so_luong x WHERE x.phap_nhan_id = v_pn AND x.pool_kind = 'L11'
                                                         AND x.phieu_dong_id = lw.dong_id));
                SELECT x.* INTO d_pk FROM kho.phieu_kho_danh_tinh x WHERE x.id = lw.phieu_id FOR SHARE;
            END IF;
            SELECT x.* INTO q FROM kho.bang_chung_quy_doi_luong x WHERE x.id = kho.l11_uuid(p->>'proof_id') FOR SHARE;  -- luôn gán (không có → NULL)
            v_tok := """ + _L11_TOKEN.format(x="kho.l11_co_so_ma_hoa_noi_bo(v_side, v_id)") + """;
            IF p->>'expected_graph' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: dòng/nguồn/pool/bằng chứng đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            IF v_side = 'M2' THEN
                IF d_hd.eligible_content_id IS DISTINCT FROM b.hoa_don_phien_ban_id THEN
                    RAISE EXCEPTION 'L11_HOA_DON_KHONG_DU_DIEU_KIEN: dòng không thuộc nội dung eligible hiện hành' USING ERRCODE = 'P0001';
                END IF;
                v_qtext := b.quantity_raw; v_utext := b.unit_raw;
                v_native := kho.l11_so_nguon(b.quantity_raw);
                IF v_native IS NULL OR b.precision_state IS DISTINCT FROM 'EXACT_21_6' OR b.quantity_exact IS DISTINCT FROM v_native THEN
                    RAISE EXCEPTION 'L11_SO_LUONG_NGUON_SAI: số lượng nguồn không exact dương trong miền' USING ERRCODE = 'P0001';
                END IF;
                SELECT x.source_instance_id, x.profile_ref, x.profile_sha256 INTO v_inst, v_prof_ref, v_prof_sha FROM kho.anh_chup_nguon x WHERE x.id = b.snapshot_id;
                rw := (SELECT r.row_raw FROM kho.ban_ghi_nguon r WHERE r.id = b.source_row_id);
                v_item := CASE WHEN jsonb_array_length(coalesce(b.field_states->'MHHDVu', '[]'::jsonb)) = 1 THEN b.field_states->'MHHDVu'->0->>'lexeme' END;
                IF b.unit_definition_id IS NOT NULL THEN
                    IF q.id IS NOT NULL THEN
                        RAISE EXCEPTION 'L11_MA_HOA_KHONG_CAN_BANG_CHUNG: dòng đã có đơn vị định nghĩa xác minh — không gắn bằng chứng mã hóa' USING ERRCODE = 'P0001';
                    END IF;
                    SELECT x.* INTO dv FROM master.dinh_nghia_don_vi_luong x WHERE x.id = b.unit_definition_id;
                    v_loi := kho.l11_don_vi_xac_minh_noi_bo(dv.id);
                    IF v_loi IS NOT NULL OR dv.support_profile_ref IS DISTINCT FROM v_prof_ref OR dv.support_profile_sha256 IS DISTINCT FROM v_prof_sha
                       OR dv.support_source_instance_id IS DISTINCT FROM v_inst OR b.unit_basis_sha256 IS DISTINCT FROM dv.definition_sha256
                       OR dv.payload->>'native_unit_code' IS DISTINCT FROM b.unit_raw THEN
                        RAISE EXCEPTION 'L11_DON_VI_CHUA_XAC_MINH: định nghĩa đơn vị dòng không khớp tuple khai báo/ngữ cảnh hiện hành' USING ERRCODE = 'P0001';
                    END IF;
                    -- R3: định nghĩa có khai báo artifact hỗ trợ → kiểm trường thật tại locator đó; định nghĩa R15 không khai hỗ trợ (support NULL,
                    -- seed ngoài phạm vi sửa) → bằng chứng trường thật là CHÍNH dòng đã capture: reader thật resolve đúng định nghĩa này trong cùng
                    -- ngữ cảnh (row_raw.unit_definition_ref) và DVTinh giải mã = mã đơn vị — không dùng nhãn/FK catalog thay trường nguồn
                    IF dv.support_raw_sha256 IS NULL AND dv.support_locator IS NULL THEN
                        v_loi := CASE WHEN rw->>'unit_definition_ref' IS DISTINCT FROM dv.reference_id OR rw->>'unit_raw' IS DISTINCT FROM b.unit_raw
                                      THEN 'L11_HO_TRO_DON_VI_KHONG_KHOP' END;
                    ELSE
                        v_loi := kho.l11_ho_tro_don_vi_noi_bo(dv.id, v_item);
                    END IF;
                    IF v_loi IS NOT NULL THEN
                        RAISE EXCEPTION '%: trường đơn vị/mã hàng thật tại locator hỗ trợ khai báo không khớp định nghĩa', v_loi USING ERRCODE = 'P0001';
                    END IF;
                    v_unit := dv.id; v_unit_sha := dv.definition_sha256; v_nat := dv.id; v_nat_sha := dv.definition_sha256;
                    v_can_cu := 'SAME_VERIFIED_DEFINITION';
                ELSE
                    IF q.id IS NULL OR q.kind <> 'NATIVE_ENCODING' OR q.trang_thai <> 'DA_XAC_NHAN' OR q.phap_nhan_id <> v_pn THEN
                        RAISE EXCEPTION 'L11_THIEU_BANG_CHUNG_MA_HOA: dòng chưa có đơn vị xác minh — cần bằng chứng mã hóa native đã xác nhận' USING ERRCODE = 'P0001';
                    END IF;
                    SELECT g.* INTO v_g FROM kho.bang_chung_quy_doi_luong g WHERE g.id = q.hang_hoa_bang_chung_id AND g.trang_thai = 'DA_XAC_NHAN';
                    SELECT m.subject_key, m.reference_id INTO v_cty FROM master.anh_xa_nguon m
                        WHERE m.id = (SELECT v.company_mapping_id FROM kho.hoa_don_phien_ban v WHERE v.id = b.hoa_don_phien_ban_id);
                    SELECT x.* INTO dv FROM master.dinh_nghia_don_vi_luong x WHERE x.id = q.tu_don_vi_id;
                    -- R2/R3/R4: artifact/locator/lexeme/hàng thật của dòng + ngữ cảnh instance/profile của mã hóa và miền hàng (company/mapping) +
                    --   định nghĩa NATIVE của mã hóa đúng trường đơn vị thật (hỗ trợ đã capture); pool = tuple own-pool riêng của bằng chứng
                    IF q.native_xml_sha256 IS DISTINCT FROM rw->>'native_xml_sha256' OR q.unit_lexeme IS DISTINCT FROM b.unit_raw
                       OR q.native_byte_length IS DISTINCT FROM (rw->>'byte_length')::bigint  -- repair03: tuple độ dài bất biến đối chiếu dòng hiện hành
                       OR (q.quantity_lexeme IS NOT NULL AND q.quantity_lexeme IS DISTINCT FROM b.quantity_raw)
                       OR q.quantity_locator IS DISTINCT FROM (rw->>'source_locator') || '/SLuong' OR q.unit_locator IS DISTINCT FROM (rw->>'source_locator') || '/DVTinh'
                       OR v_g.id IS NULL OR v_g.hang_hoa_hoa_don IS DISTINCT FROM v_item
                       OR q.mien->>'source_instance' IS DISTINCT FROM v_inst OR q.mien->>'profile_ref' IS DISTINCT FROM v_prof_ref
                       OR q.mien->>'profile_sha256' IS DISTINCT FROM v_prof_sha
                       OR v_g.mien->'invoice'->>'source_instance' IS DISTINCT FROM v_inst OR v_g.mien->'invoice'->>'profile_ref' IS DISTINCT FROM v_prof_ref
                       OR v_g.mien->'invoice'->>'profile_payload_sha256' IS DISTINCT FROM v_prof_sha
                       OR v_g.mien->'invoice'->>'company_key' IS DISTINCT FROM v_cty.subject_key
                       OR v_g.mien->'invoice'->>'company_mapping_ref' IS DISTINCT FROM v_cty.reference_id
                       OR dv.payload->>'native_unit_code' IS DISTINCT FROM b.unit_raw THEN
                        RAISE EXCEPTION 'L11_BANG_CHUNG_MA_HOA_KHONG_KHOP: bằng chứng mã hóa không khớp artifact/locator/lexeme/hàng/ngữ cảnh của dòng thật' USING ERRCODE = 'P0001';
                    END IF;
                    v_loi := kho.l11_ho_tro_don_vi_noi_bo(q.tu_don_vi_id, v_item);
                    IF v_loi IS NOT NULL THEN
                        RAISE EXCEPTION '%: trường đơn vị/mã hàng thật tại locator hỗ trợ khai báo không khớp định nghĩa native của mã hóa', v_loi USING ERRCODE = 'P0001';
                    END IF;
                    v_nat := q.tu_don_vi_id; v_nat_sha := q.tu_don_vi_sha256; v_unit := q.den_don_vi_id; v_unit_sha := q.den_don_vi_sha256;
                    v_tu := q.tu_so; v_mau := q.mau_so; v_can_cu := 'APPROVED_NATIVE_ENCODING'; v_proof := q.id;
                END IF;
                SELECT x.* INTO v_pool FROM kho.dich_so_luong x WHERE x.phap_nhan_id = v_pn AND x.pool_kind = 'L11' AND x.hoa_don_dong_id = b.dong_danh_tinh_id;
            ELSE
                IF d_pk.eligible_content_id IS DISTINCT FROM lw.phien_ban_id THEN
                    RAISE EXCEPTION 'L11_PHIEU_KHONG_DU_DIEU_KIEN: dòng không thuộc nội dung eligible hiện hành' USING ERRCODE = 'P0001';
                END IF;
                IF q.id IS NOT NULL THEN
                    RAISE EXCEPTION 'L11_MA_HOA_KHONG_CAN_BANG_CHUNG: dòng phiếu dùng định nghĩa đơn vị đã xác minh' USING ERRCODE = 'P0001';
                END IF;
                v_qtext := lw.so_luong_raw; v_utext := lw.dvt_raw;
                v_native := kho.l11_so_nguon(lw.so_luong_raw);
                IF v_native IS NULL OR lw.quantity_json_kind <> 'STRING' OR lw.precision_state <> 'EXACT_SYNTHETIC_DEMO' OR lw.so_luong IS DISTINCT FROM v_native THEN
                    RAISE EXCEPTION 'L11_SO_LUONG_NGUON_SAI: số lượng phiếu không exact dương trong miền' USING ERRCODE = 'P0001';
                END IF;
                SELECT x.* INTO ppb FROM kho.phieu_kho_phien_ban x WHERE x.id = lw.phien_ban_id;
                v_prof_ref := ppb.profile_ref; v_prof_sha := ppb.profile_sha256;
                SELECT x.* INTO dv FROM master.dinh_nghia_don_vi_luong x WHERE x.reference_id = lw.unit_definition_ref;
                v_loi := CASE WHEN dv.id IS NULL THEN 'L11_DON_VI_KHONG_CO' ELSE kho.l11_don_vi_xac_minh_noi_bo(dv.id) END;
                IF v_loi IS NOT NULL OR dv.support_source_instance_id IS DISTINCT FROM d_pk.source_instance_id
                   OR dv.support_profile_ref IS DISTINCT FROM ppb.profile_ref OR dv.support_profile_sha256 IS DISTINCT FROM ppb.profile_sha256
                   OR dv.payload->>'native_unit_code' IS DISTINCT FROM lw.dvt_raw THEN
                    RAISE EXCEPTION 'L11_DON_VI_CHUA_XAC_MINH: đơn vị dòng phiếu chưa có định nghĩa khai báo cùng ngữ cảnh (không suy theo nhãn)' USING ERRCODE = 'P0001';
                END IF;
                -- R3: hỗ trợ trường thật (master DVT_Goc + MaHang tại locator khai báo của artifact hỗ trợ đã capture) + khai báo đo lường hiện hành
                v_loi := kho.l11_ho_tro_don_vi_noi_bo(dv.id, lw.ma_hang_raw);
                IF v_loi IS NOT NULL THEN
                    RAISE EXCEPTION '%: trường đơn vị/mã hàng thật tại locator hỗ trợ khai báo không khớp định nghĩa', v_loi USING ERRCODE = 'P0001';
                END IF;
                v_do_luong := kho.l11_do_luong_dong_noi_bo(lw.id);
                IF v_do_luong IS NULL THEN
                    RAISE EXCEPTION 'L11_DO_LUONG_KHONG_HIEN_HANH: dòng phiếu không có đúng một khai báo đo lường hiện hành khớp master/đơn vị' USING ERRCODE = 'P0001';
                END IF;
                v_unit := dv.id; v_unit_sha := dv.definition_sha256; v_nat := dv.id; v_nat_sha := dv.definition_sha256; v_can_cu := 'SAME_VERIFIED_DEFINITION';
                SELECT x.* INTO v_pool FROM kho.dich_so_luong x WHERE x.phap_nhan_id = v_pn AND x.pool_kind = 'L11' AND x.phieu_dong_id = lw.dong_id;
            END IF;
            v_cap := kho.l11_quy_doi(v_native, v_tu, v_mau);
            IF v_cap IS NULL THEN
                RAISE EXCEPTION 'L11_KHONG_BIEU_DIEN_DUOC: sức chứa không biểu diễn chính xác trong 38,12' USING ERRCODE = 'P0001';
            END IF;
            IF v_pool.id IS NOT NULL THEN
                PERFORM kho.l11_khoa_pool_noi_bo(ARRAY[v_pool.id]);
                IF v_pool.don_vi_id IS DISTINCT FROM v_unit THEN
                    RAISE EXCEPTION 'L11_DON_VI_POOL_KHAC: pool của gốc đã cố định đơn vị khác — HOLD, không tạo pool mới' USING ERRCODE = 'P0001';
                END IF;
                v_pool_id := v_pool.id;
            ELSE
                IF v_side = 'M2' THEN
                    INSERT INTO kho.dich_so_luong (phap_nhan_id, owner_module, pool_kind, hoa_don_id, hoa_don_dong_id, don_vi_id, don_vi_sha256, tao_boi)
                    VALUES (v_pn, 'M2', 'L11', b.hoa_don_id, b.dong_danh_tinh_id, v_unit, v_unit_sha, ai) RETURNING id INTO v_pool_id;
                ELSE
                    INSERT INTO kho.dich_so_luong (phap_nhan_id, owner_module, pool_kind, phieu_id, phieu_dong_id, don_vi_id, don_vi_sha256, tao_boi)
                    VALUES (v_pn, 'M5', 'L11', lw.phieu_id, lw.dong_id, v_unit, v_unit_sha, ai) RETURNING id INTO v_pool_id;
                END IF;
                PERFORM kho.l11_khoa_pool_noi_bo(ARRAY[v_pool_id]);
            END IF;
            IF EXISTS (SELECT 1 FROM kho.ma_hoa_luong_nguon e WHERE e.phap_nhan_id = v_pn AND e.pool_id = v_pool_id
                       AND (e.cau_noi_id = v_id OR e.phieu_dong_phien_ban_id = v_id) AND e.don_vi_pool_id = v_unit AND e.tu_so = v_tu AND e.mau_so = v_mau
                       AND e.bang_chung_ma_hoa_id IS NOT DISTINCT FROM v_proof AND e.so_luong_nguon = v_native AND e.don_vi_nguon_id = v_nat
                       AND e.do_luong_sha256 IS NOT DISTINCT FROM v_do_luong) THEN
                RAISE EXCEPTION 'L11_MA_HOA_DA_CO: dòng đã có mã hóa cùng căn cứ' USING ERRCODE = 'P0001';
            END IF;
            SELECT coalesce(max(e.basis_revision), 0) + 1 INTO v_rev FROM kho.ma_hoa_luong_nguon e WHERE e.cau_noi_id = v_id OR e.phieu_dong_phien_ban_id = v_id;
            v_eid := gen_random_uuid();
            v_ket := jsonb_build_object('ma_hoa_id', v_eid, 'pool_id', v_pool_id, 'side', v_side, 'line_id', v_id, 'so_luong_nguon', kho.l11_text(v_native),
                                        'don_vi_nguon', v_utext, 'don_vi_pool', (SELECT x.reference_id FROM master.dinh_nghia_don_vi_luong x WHERE x.id = v_unit),
                                        'dinh_nghia_nguon', (SELECT x.reference_id FROM master.dinh_nghia_don_vi_luong x WHERE x.id = v_nat),
                                        'do_luong_sha256', v_do_luong,
                                        'tu_so', v_tu::text, 'mau_so', v_mau::text, 'suc_chua', kho.l11_text(v_cap), 'can_cu', v_can_cu, 'basis_revision', v_rev);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (v_pn, 'M5', 'L11_ENCODE', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            IF v_side = 'M2' THEN
                INSERT INTO kho.ma_hoa_luong_nguon (id, phap_nhan_id, owner_module, pool_id, cau_noi_id, hoa_don_id, hoa_don_phien_ban_id, hoa_don_dong_id,
                    so_luong_nguon_text, so_luong_nguon, don_vi_nguon_text, don_vi_nguon_id, don_vi_nguon_sha256, do_luong_sha256, don_vi_pool_id,
                    don_vi_pool_sha256, tu_so, mau_so, suc_chua, can_cu, bang_chung_ma_hoa_id, profile_ref, profile_sha256, basis_revision, bien_nhan_id, tao_boi)
                VALUES (v_eid, v_pn, 'M2', v_pool_id, b.id, b.hoa_don_id, b.hoa_don_phien_ban_id, b.dong_danh_tinh_id, v_qtext, v_native, v_utext, v_nat,
                        v_nat_sha, NULL, v_unit, v_unit_sha, v_tu, v_mau, v_cap, v_can_cu, v_proof, v_prof_ref, v_prof_sha, v_rev, v_bn, ai);
            ELSE
                INSERT INTO kho.ma_hoa_luong_nguon (id, phap_nhan_id, owner_module, pool_id, phieu_dong_phien_ban_id, phieu_id, phieu_phien_ban_id, phieu_dong_id,
                    so_luong_nguon_text, so_luong_nguon, don_vi_nguon_text, don_vi_nguon_id, don_vi_nguon_sha256, do_luong_sha256, don_vi_pool_id,
                    don_vi_pool_sha256, tu_so, mau_so, suc_chua, can_cu, bang_chung_ma_hoa_id, profile_ref, profile_sha256, basis_revision, bien_nhan_id, tao_boi)
                VALUES (v_eid, v_pn, 'M5', v_pool_id, lw.id, lw.phieu_id, lw.phien_ban_id, lw.dong_id, v_qtext, v_native, v_utext, v_nat, v_nat_sha,
                        v_do_luong, v_unit, v_unit_sha, v_tu, v_mau, v_cap, v_can_cu, NULL, v_prof_ref, v_prof_sha, v_rev, v_bn, ai);
            END IF;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (v_pn, ai, 'HE_THONG', 'kho.ma_hoa_luong_nguon', v_eid, 'L11_ENCODE', v_ket, p->>'reason');
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
)

M0016_L11_HAM = M0016_L11_HAM + (
    # ---- đánh giá cặp (preview + cổng xác nhận dùng CHUNG một hàm): đồ thị typed hiện hành, bằng chứng, mã hóa, ngân sách hai pool, số học exact
    """CREATE OR REPLACE FUNCTION kho.l11_danh_gia_noi_bo(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE b record; lw record; hd record; pb record; pd record; ppb record; rt record; ei record; ew record; g record; x record;
            rw jsonb; bl text[] := '{}'; v_item_hd text; v_item_kho text; v_pn_ma text; v_id_dong text; v_wh_native text; v_a numeric; v_b numeric;
            v_pa numeric; v_pb numeric; nsh jsonb; nsp jsonb; v_graph jsonb; v_map_hd text; v_map_pk text; v_wh_len bigint; v_do_luong text;
            v_ctx_hd record; v_cty record; v_map_kho record;
        BEGIN
            -- R3 repair02: chỉ đánh giá khi CẢ HAI endpoint typed + mọi mã hóa/bằng chứng tham chiếu cùng PN (l11_trang_thai_cap_noi_bo);
            -- không nạp/serialize facts của PN khác rồi mới gắn blocker
            IF kho.l11_trang_thai_cap_noi_bo(p) IS NULL THEN
                RETURN jsonb_build_object('blockers', jsonb_build_array('L11_CAP_KHONG_TON_TAI'), 'graph', NULL, 'expected_graph', NULL);
            END IF;
            SELECT y.* INTO b FROM kho.hoa_don_dong_phien_ban y WHERE y.id = kho.l11_uuid(p->>'cau_noi_id');
            SELECT y.* INTO lw FROM kho.phieu_kho_dong_phien_ban y WHERE y.id = kho.l11_uuid(p->>'dong_phien_ban_id');
            SELECT y.* INTO hd FROM kho.hoa_don_danh_tinh y WHERE y.id = b.hoa_don_id;
            SELECT y.* INTO pb FROM kho.hoa_don_phien_ban y WHERE y.id = b.hoa_don_phien_ban_id;
            SELECT y.* INTO pd FROM kho.phieu_kho_danh_tinh y WHERE y.id = lw.phieu_id;
            SELECT y.* INTO ppb FROM kho.phieu_kho_phien_ban y WHERE y.id = lw.phien_ban_id;
            SELECT y.* INTO rt FROM kho.mua_dich_dong y WHERE y.source_dong_id = b.source_dong_id AND y.hien_hanh;
            SELECT y.* INTO ei FROM kho.ma_hoa_luong_nguon y WHERE y.id = kho.l11_uuid(p->>'ma_hoa_hoa_don_id') AND y.phap_nhan_id = b.phap_nhan_id;
            SELECT y.* INTO ew FROM kho.ma_hoa_luong_nguon y WHERE y.id = kho.l11_uuid(p->>'ma_hoa_phieu_id') AND y.phap_nhan_id = b.phap_nhan_id;
            SELECT y.* INTO g FROM kho.bang_chung_quy_doi_luong y WHERE y.id = kho.l11_uuid(p->>'bang_chung_hang_id') AND y.phap_nhan_id = b.phap_nhan_id;
            SELECT y.* INTO x FROM kho.bang_chung_quy_doi_luong y WHERE y.id = kho.l11_uuid(p->>'bang_chung_ty_le_id') AND y.phap_nhan_id = b.phap_nhan_id;
            SELECT y.ma INTO v_pn_ma FROM master.phap_nhan y WHERE y.id = b.phap_nhan_id;
            SELECT y.id_dong_nguon INTO v_id_dong FROM kho.phieu_kho_dong_danh_tinh y WHERE y.id = lw.dong_id;
            SELECT y.raw_sha256, y.byte_length INTO v_wh_native, v_wh_len FROM kho.anh_chup_nguon_vai_tro y
                WHERE y.snapshot_id = ppb.first_snapshot_id AND y.vai_tro = 'NATIVE_DETAIL';
            v_do_luong := kho.l11_do_luong_dong_noi_bo(lw.id);
            -- ngữ cảnh nguồn thật của hai phía (instance/profile của snapshot/phiên bản, company/kho + mapping hiện hành) cho miền bằng chứng hàng
            SELECT a.source_instance_id, a.profile_ref, a.profile_sha256 INTO v_ctx_hd FROM kho.anh_chup_nguon a WHERE a.id = b.snapshot_id;
            SELECT m.subject_key, m.reference_id INTO v_cty FROM master.anh_xa_nguon m WHERE m.id = pb.company_mapping_id;
            SELECT m.subject_key, m.reference_id INTO v_map_kho FROM master.anh_xa_nguon m WHERE m.id = pd.mapping_revision_id;
            SELECT m.state || '|' || coalesce(m.valid_to::text, '') INTO v_map_hd FROM master.anh_xa_nguon m WHERE m.id = b.line_identity_mapping_id;
            SELECT m.state || '|' || coalesce(m.valid_to::text, '') INTO v_map_pk FROM master.anh_xa_nguon m WHERE m.id = pd.mapping_revision_id;
            rw := (SELECT r.row_raw FROM kho.ban_ghi_nguon r WHERE r.id = b.source_row_id);
            v_item_hd := CASE WHEN jsonb_array_length(coalesce(b.field_states->'MHHDVu', '[]'::jsonb)) = 1 THEN b.field_states->'MHHDVu'->0->>'lexeme' END;
            v_item_kho := lw.ma_hang_raw;
            IF lw.phap_nhan_id IS DISTINCT FROM b.phap_nhan_id THEN
                bl := bl || 'L11_CAP_KHAC_PHAP_NHAN'::text;
            END IF;
            IF hd.chieu IS DISTINCT FROM 'MUA_VAO' OR hd.accepted_source_observation_id IS NULL OR hd.eligible_content_id IS DISTINCT FROM b.hoa_don_phien_ban_id THEN
                bl := bl || 'L11_HOA_DON_KHONG_DU_DIEU_KIEN'::text;
            END IF;
            IF rt.id IS NULL OR rt.dich IS DISTINCT FROM 'KHO' OR rt.trang_thai IS DISTINCT FROM 'DA_DUYET' THEN
                bl := bl || 'L11_TUYEN_KHONG_PHAI_KHO'::text;
            END IF;
            IF v_map_hd IS DISTINCT FROM 'DA_DUYET|' OR v_map_pk IS DISTINCT FROM 'DA_DUYET|' THEN
                bl := bl || 'L11_MAPPING_KHONG_HIEN_HANH'::text;
            END IF;
            IF pd.eligible_content_id IS DISTINCT FROM lw.phien_ban_id OR pd.accepted_source_observation_id IS NULL THEN
                bl := bl || 'L11_PHIEU_KHONG_DU_DIEU_KIEN'::text;
            END IF;
            IF ei.id IS NULL OR ei.cau_noi_id IS DISTINCT FROM b.id
               OR ei.basis_revision IS DISTINCT FROM (SELECT max(e.basis_revision) FROM kho.ma_hoa_luong_nguon e WHERE e.cau_noi_id = b.id) THEN
                bl := bl || 'L11_MA_HOA_HOA_DON_KHONG_HIEN_HANH'::text;
            END IF;
            IF ew.id IS NULL OR ew.phieu_dong_phien_ban_id IS DISTINCT FROM lw.id
               OR ew.basis_revision IS DISTINCT FROM (SELECT max(e.basis_revision) FROM kho.ma_hoa_luong_nguon e WHERE e.phieu_dong_phien_ban_id = lw.id) THEN
                bl := bl || 'L11_MA_HOA_PHIEU_KHONG_HIEN_HANH'::text;
            ELSIF v_do_luong IS NULL OR ew.do_luong_sha256 IS DISTINCT FROM v_do_luong THEN
                bl := bl || 'L11_DO_LUONG_KHONG_HIEN_HANH'::text;  -- R3: mã hóa M5 gắn khai báo đo lường hiện hành của nội dung
            END IF;
            -- R3 repair02: binding phía kho = native NATIVE_DETAIL thật (SHA + độ dài) + SoPhieu + ID_Dong + source_ordinal GỐC của reader (vị trí mảng
            --   /lines/{i}; binding khai báo đếm từ 1 nên so với i + 1, KHÔNG dùng STT hiển thị) + master SHA thật + khai báo đo lường hiện hành + mã hàng
            IF g.id IS NULL OR g.kind IS DISTINCT FROM 'GOODS_EQUIVALENCE' OR g.trang_thai IS DISTINCT FROM 'DA_XAC_NHAN' THEN
                bl := bl || 'L11_BANG_CHUNG_HANG_THIEU'::text;
            ELSIF g.mien->'invoice'->>'source_instance' IS DISTINCT FROM v_ctx_hd.source_instance_id
               OR g.mien->'invoice'->>'profile_ref' IS DISTINCT FROM v_ctx_hd.profile_ref
               OR g.mien->'invoice'->>'profile_payload_sha256' IS DISTINCT FROM v_ctx_hd.profile_sha256
               OR g.mien->'invoice'->>'company_key' IS DISTINCT FROM v_cty.subject_key
               OR g.mien->'invoice'->>'company_mapping_ref' IS DISTINCT FROM v_cty.reference_id
               OR g.mien->'warehouse'->>'source_instance' IS DISTINCT FROM pd.source_instance_id
               OR g.mien->'warehouse'->>'profile_ref' IS DISTINCT FROM ppb.profile_ref
               OR g.mien->'warehouse'->>'profile_payload_sha256' IS DISTINCT FROM ppb.profile_sha256
               OR g.mien->'warehouse'->>'MaKho' IS DISTINCT FROM pd.ma_kho
               OR g.mien->'warehouse'->>'warehouse_mapping_ref' IS DISTINCT FROM v_map_kho.reference_id THEN
                bl := bl || 'L11_BANG_CHUNG_HANG_NGOAI_MIEN'::text;  -- R3/R4: miền khai báo của bằng chứng hàng ≠ ngữ cảnh nguồn thật của cặp
            ELSIF g.hang_hoa_hoa_don IS DISTINCT FROM v_item_hd OR g.hang_hoa_kho IS DISTINCT FROM v_item_kho
               OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(g.rang_buoc) AS t(e) WHERE e->>'side' = 'INVOICE'
                              AND e->>'native_sha256' IS NOT DISTINCT FROM rw->>'native_xml_sha256'
                              AND e->>'byte_length' IS NOT DISTINCT FROM rw->>'byte_length' AND e->>'locator' IS NOT DISTINCT FROM rw->>'source_locator'
                              AND e->'identity_tuple' = to_jsonb(ARRAY[v_pn_ma, hd.chieu, hd.mst_ban, hd.mau_so, hd.ky_hieu, hd.so_chuan])
                              AND e->>'item_code' IS NOT DISTINCT FROM v_item_hd)
               OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(g.rang_buoc) AS t(e) WHERE e->>'side' = 'WAREHOUSE'
                              AND e->>'native_sha256' IS NOT DISTINCT FROM v_wh_native AND e->>'byte_length' IS NOT DISTINCT FROM v_wh_len::text
                              AND e->>'SoPhieu' IS NOT DISTINCT FROM pd.so_phieu_key AND e->>'ID_Dong' IS NOT DISTINCT FROM v_id_dong
                              AND e->>'source_ordinal' IS NOT DISTINCT FROM (lw.source_ordinal + 1)::text
                              AND e->>'master_sha256' IS NOT DISTINCT FROM ppb.master_raw_sha256
                              AND e->>'measurement_payload_sha256' IS NOT DISTINCT FROM v_do_luong
                              AND e->>'item_code' IS NOT DISTINCT FROM v_item_kho) THEN
                bl := bl || 'L11_BANG_CHUNG_HANG_KHONG_PHU'::text;
            END IF;
            -- R2 repair02: tỷ lệ cross-native áp lên định nghĩa đơn vị NATIVE của hai dòng (từ mã hóa), không lên đơn vị pool
            IF x.id IS NULL OR x.kind IS DISTINCT FROM 'CROSS_NATIVE_RATIO' OR x.trang_thai IS DISTINCT FROM 'DA_XAC_NHAN' THEN
                bl := bl || 'L11_BANG_CHUNG_TY_LE_THIEU'::text;
            ELSIF x.hang_hoa_bang_chung_id IS DISTINCT FROM g.id THEN
                bl := bl || 'L11_BANG_CHUNG_TY_LE_KHAC_HANG'::text;
            ELSIF x.tu_don_vi_id IS DISTINCT FROM ei.don_vi_nguon_id OR x.den_don_vi_id IS DISTINCT FROM ew.don_vi_nguon_id THEN
                bl := bl || 'L11_TY_LE_DON_VI_KHAC'::text;
            ELSIF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(x.rang_buoc) AS t(e) WHERE e->>'side' = 'WAREHOUSE'
                              AND e->>'native_sha256' IS NOT DISTINCT FROM v_wh_native AND e->>'byte_length' IS NOT DISTINCT FROM v_wh_len::text
                              AND e->>'SoPhieu' IS NOT DISTINCT FROM pd.so_phieu_key AND e->>'ID_Dong' IS NOT DISTINCT FROM v_id_dong
                              AND e->>'source_ordinal' IS NOT DISTINCT FROM (lw.source_ordinal + 1)::text
                              AND e->>'master_sha256' IS NOT DISTINCT FROM ppb.master_raw_sha256
                              AND e->>'measurement_payload_sha256' IS NOT DISTINCT FROM v_do_luong
                              AND e->>'item_code' IS NOT DISTINCT FROM v_item_kho) THEN
                bl := bl || 'L11_BANG_CHUNG_TY_LE_KHONG_PHU'::text;
            END IF;
            nsh := CASE WHEN ei.pool_id IS NOT NULL THEN kho.l11_ngan_sach_noi_bo(ei.pool_id) END;
            nsp := CASE WHEN ew.pool_id IS NOT NULL THEN kho.l11_ngan_sach_noi_bo(ew.pool_id) END;
            IF nsh IS NULL OR nsh->>'con_lai' IS NULL OR nsh->>'ma_hoa_id' IS DISTINCT FROM ei.id::text THEN
                bl := bl || 'L11_POOL_HOA_DON_BI_CHAN'::text;
            END IF;
            IF nsp IS NULL OR nsp->>'con_lai' IS NULL OR nsp->>'ma_hoa_id' IS DISTINCT FROM ew.id::text THEN
                bl := bl || 'L11_POOL_PHIEU_BI_CHAN'::text;
            END IF;
            IF EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = b.phap_nhan_id
                       AND k.ky IN (to_char(pb.ngay_lap, 'YYYY-MM'), to_char(ppb.ngay_chung_tu, 'YYYY-MM'))) THEN
                bl := bl || 'KY_DA_KHOA'::text;
            END IF;
            IF p ? 'so_luong_hoa_don' OR p ? 'so_luong_phieu' THEN
                IF jsonb_typeof(p->'so_luong_hoa_don') IS DISTINCT FROM 'string' OR jsonb_typeof(p->'so_luong_phieu') IS DISTINCT FROM 'string' THEN
                    bl := bl || 'L11_SO_LUONG_SAI'::text;
                ELSE
                    v_a := kho.l11_so_nguon(p->>'so_luong_hoa_don'); v_b := kho.l11_so_nguon(p->>'so_luong_phieu');
                    IF v_a IS NULL OR v_b IS NULL THEN
                        bl := bl || 'L11_SO_LUONG_SAI'::text;
                    ELSIF ei.id IS NOT NULL AND ew.id IS NOT NULL THEN
                        v_pa := kho.l11_quy_doi(v_a, ei.tu_so, ei.mau_so); v_pb := kho.l11_quy_doi(v_b, ew.tu_so, ew.mau_so);
                        IF v_pa IS NULL OR v_pb IS NULL THEN
                            bl := bl || 'L11_KHONG_BIEU_DIEN_DUOC'::text;
                        ELSE
                            -- R2: native A × tử = native B × mẫu (đơn vị native); hai lượng pool dẫn xuất ĐỘC LẬP qua mã hóa own-pool từng phía
                            IF x.id IS NOT NULL AND v_a * x.tu_so <> v_b * x.mau_so THEN
                                bl := bl || 'L11_SAI_PHEP_NHAN'::text;
                            END IF;
                            IF nsh->>'con_lai' IS NOT NULL AND v_pa > (nsh->>'con_lai')::numeric THEN
                                bl := bl || 'L11_VUOT_SO_LUONG_HOA_DON'::text;
                            END IF;
                            IF nsp->>'con_lai' IS NOT NULL AND v_pb > (nsp->>'con_lai')::numeric THEN
                                bl := bl || 'L11_VUOT_SO_LUONG_PHIEU'::text;
                            END IF;
                        END IF;
                    END IF;
                END IF;
            END IF;
            v_graph := jsonb_build_object('contract', 'l11-link-graph/v1', 'pn', b.phap_nhan_id,
                'hoa_don', jsonb_build_object('id', hd.id, 'latest', hd.latest_observation_id, 'accepted', hd.accepted_source_observation_id,
                                              'eligible', hd.eligible_content_id),
                'cau_noi', jsonb_build_object('id', b.id, 'pb', b.hoa_don_phien_ban_id, 'map', b.line_identity_mapping_id, 'map_tt', v_map_hd,
                                              'fs', b.field_state_sha256),
                'tuyen', jsonb_build_object('id', rt.id, 'dich', rt.dich, 'phien_ban', rt.phien_ban),
                'phieu', jsonb_build_object('id', pd.id, 'latest', pd.latest_observation_id, 'accepted', pd.accepted_source_observation_id,
                                            'eligible', pd.eligible_content_id, 'map', pd.mapping_revision_id, 'map_tt', v_map_pk),
                'dong_phieu', jsonb_build_object('id', lw.id, 'pb', lw.phien_ban_id, 'q', lw.so_luong_raw, 'do_luong', v_do_luong),
                'ma_hoa', jsonb_build_array(ei.id, ew.id),
                'bang_chung', jsonb_build_object('hang', g.id, 'hang_tt', g.trang_thai, 'ty_le', x.id, 'ty_le_tt', x.trang_thai),
                'ngan_sach', jsonb_build_array(nsh, nsp));
            RETURN jsonb_build_object('phap_nhan_id', b.phap_nhan_id, 'blockers', to_jsonb(bl), 'graph', v_graph,
                'expected_graph', """ + _L11_TOKEN.format(x="v_graph") + """,
                'so_luong', jsonb_build_object('hoa_don_nguon', kho.l11_text(v_a), 'phieu_nguon', kho.l11_text(v_b), 'pool_hoa_don', kho.l11_text(v_pa),
                                               'pool_phieu', kho.l11_text(v_pb)),
                'don_vi', jsonb_build_object('hoa_don_nguon', b.unit_raw, 'phieu_nguon', lw.dvt_raw, 'pool_hoa_don', nsh->>'don_vi', 'pool_phieu', nsp->>'don_vi',
                                             'dinh_nghia_nguon_hoa_don', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u WHERE u.id = ei.don_vi_nguon_id),
                                             'dinh_nghia_nguon_phieu', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u WHERE u.id = ew.don_vi_nguon_id)),
                'ngan_sach', jsonb_build_object('hoa_don', nsh, 'phieu', nsp),
                'ty_le', CASE WHEN x.id IS NOT NULL THEN jsonb_build_object('tu_so', x.tu_so::text, 'mau_so', x.mau_so::text, 'ap_tren', 'NATIVE') END,
                'ma_hoa_ty_le', jsonb_build_object('hoa_don', CASE WHEN ei.id IS NOT NULL THEN jsonb_build_object('tu_so', ei.tu_so::text, 'mau_so', ei.mau_so::text) END,
                                                   'phieu', CASE WHEN ew.id IS NOT NULL THEN jsonb_build_object('tu_so', ew.tu_so::text, 'mau_so', ew.mau_so::text) END),
                'refs', jsonb_build_object('hoa_don_id', hd.id, 'hoa_don_phien_ban_id', pb.id, 'hoa_don_chung_tu_id', pb.chung_tu_id,
                                           'hoa_don_chung_tu_dong_id', b.source_dong_id, 'hoa_don_dong_id', b.dong_danh_tinh_id, 'phieu_id', pd.id,
                                           'phieu_phien_ban_id', ppb.id, 'phieu_chung_tu_id', ppb.chung_tu_id, 'phieu_chung_tu_dong_id', lw.chung_tu_dong_id,
                                           'phieu_dong_id', lw.dong_id, 'pool_hoa_don_id', ei.pool_id, 'pool_phieu_id', ew.pool_id,
                                           'don_vi_hoa_don_id', ei.don_vi_pool_id, 'don_vi_phieu_id', ew.don_vi_pool_id, 'tuyen_id', rt.id),
                'so', jsonb_build_object('a', v_a, 'b', v_b, 'pa', v_pa, 'pb', v_pb));
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_xem_truoc(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE v_pn uuid; v jsonb;
        BEGIN
            -- R3 repair02: resolve CẢ HAI endpoint typed (+ mọi mã hóa/bằng chứng tham chiếu) cùng PN và BOTH READ hiện hành TRƯỚC mọi projection
            -- chủ bảng/ngân sách/refs ngang hàng: sai PN/không tồn tại/không quyền đều cùng một từ chối, 0 dữ liệu PN khác
            v_pn := kho.l11_trang_thai_cap_noi_bo(p);
            IF v_pn IS NULL OR NOT kho.l11_quyen_noi_bo(v_pn, 'READ') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_XEM: cần cặp typed cùng PN và M2_READ + M5_READ hiện hành trên PN đó' USING ERRCODE = 'P0001';
            END IF;
            v := kho.l11_danh_gia_noi_bo(p);
            RETURN (v - 'so') || jsonb_build_object('duoc_xac_nhan', kho.l11_quyen_noi_bo(v_pn, 'LINK'), 'ghi', 0);
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_ket_qua_dong_noi_bo(p_dong uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        SELECT coalesce((SELECT jsonb_build_object('child_id', c.id, 'lien_ket_id', c.lien_ket_id, 'trang_thai', c.trang_thai, 'hieu_luc', c.hieu_luc,
                    'can_soat_ly_do', to_jsonb(c.can_soat_ly_do), 'so_luong', jsonb_build_object('hoa_don_nguon', kho.l11_text(c.so_luong_hoa_don_nguon),
                    'phieu_nguon', kho.l11_text(c.so_luong_phieu_nguon), 'pool_hoa_don', kho.l11_text(c.so_luong_pool_hoa_don),
                    'pool_phieu', kho.l11_text(c.so_luong_pool_phieu)),
                    'don_vi', jsonb_build_object('pool_hoa_don', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u WHERE u.id = c.don_vi_hoa_don_id),
                                                 'pool_phieu', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u WHERE u.id = c.don_vi_phieu_id),
                                                 'hoa_don_nguon', (SELECT e.don_vi_nguon_text FROM kho.ma_hoa_luong_nguon e WHERE e.id = c.ma_hoa_hoa_don_id),
                                                 'phieu_nguon', (SELECT e.don_vi_nguon_text FROM kho.ma_hoa_luong_nguon e WHERE e.id = c.ma_hoa_phieu_id),
                                                 'dinh_nghia_nguon_hoa_don', (SELECT u.reference_id FROM kho.ma_hoa_luong_nguon e
                                                     JOIN master.dinh_nghia_don_vi_luong u ON u.id = e.don_vi_nguon_id WHERE e.id = c.ma_hoa_hoa_don_id),
                                                 'dinh_nghia_nguon_phieu', (SELECT u.reference_id FROM kho.ma_hoa_luong_nguon e
                                                     JOIN master.dinh_nghia_don_vi_luong u ON u.id = e.don_vi_nguon_id WHERE e.id = c.ma_hoa_phieu_id)),
                    'pool_hoa_don_id', c.pool_hoa_don_id, 'pool_phieu_id', c.pool_phieu_id, 'ma_hoa_hoa_don_id', c.ma_hoa_hoa_don_id,
                    'ma_hoa_phieu_id', c.ma_hoa_phieu_id, 'bang_chung_hang_id', c.bang_chung_hang_id, 'bang_chung_ty_le_id', c.bang_chung_ty_le_id,
                    'cau_noi_id', c.cau_noi_id, 'hoa_don_id', c.hoa_don_id, 'hoa_don_phien_ban_id', c.hoa_don_phien_ban_id, 'phieu_id', c.phieu_id,
                    'phieu_phien_ban_id', c.phieu_phien_ban_id, 'dong_phien_ban_id', c.phieu_dong_phien_ban_id, 'tuyen_id', c.tuyen_id,
                    'tao_boi', c.tao_boi, 'tao_luc', c.tao_luc, 'ly_do', c.ly_do, 'huy_boi', c.huy_boi, 'huy_luc', c.huy_luc, 'huy_ly_do', c.huy_ly_do)
                 FROM kho.lien_ket_dong c WHERE c.id = p_dong), '{}'::jsonb)
        $$""",
    # xác nhận: quyền hiện hành BOTH V2 → namespace/H/replay (trả TRẠNG THÁI HIỆN HÀNH của child, không DA_KHOP lịch sử) → khóa gốc chuẩn →
    # khóa pool sorted → khóa chia sẻ bằng chứng/tuyến/con trỏ → đánh giá lại dưới khóa (CAS token + mọi blocker) → parent dùng lại/tạo → biên nhận → child
    """CREATE OR REPLACE FUNCTION kho.l11_xac_nhan(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); b0 record; lw0 record; v_req jsonb; v_h text; cu record; v_dg jsonb; r jsonb; pk record; v_parent uuid;
            v_child uuid; v_bn uuid; v_ket jsonb; v_actor uuid;
        BEGIN
            SELECT x.id, x.phap_nhan_id, x.hoa_don_id, x.source_dong_id INTO b0 FROM kho.hoa_don_dong_phien_ban x WHERE x.id = kho.l11_uuid(p->>'cau_noi_id');
            SELECT x.id, x.phap_nhan_id, x.phieu_id INTO lw0 FROM kho.phieu_kho_dong_phien_ban x WHERE x.id = kho.l11_uuid(p->>'dong_phien_ban_id');
            IF b0.id IS NULL OR NOT kho.l11_quyen_noi_bo(b0.phap_nhan_id, 'LINK') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_LIEN_KET: cần M2+M5 và V2 hiện hành trên PN của cặp' USING ERRCODE = 'P0001';
            END IF;
            IF lw0.id IS NULL OR kho.l11_trang_thai_cap_noi_bo(p) IS DISTINCT FROM b0.phap_nhan_id THEN
                RAISE EXCEPTION 'L11_CAP_KHAC_PHAP_NHAN: dòng phiếu/mã hóa/bằng chứng không cùng PN với dòng hóa đơn' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'expected_graph', '') !~ """ + _L11_HEX + """
               OR jsonb_typeof(p->'so_luong_hoa_don') IS DISTINCT FROM 'string' OR jsonb_typeof(p->'so_luong_phieu') IS DISTINCT FROM 'string' THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần cặp typed, mã hóa, bằng chứng, hai số lượng native dạng chuỗi, token, khóa, lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || b0.phap_nhan_id || '|M5|L11_CONFIRM|' || (p->>'client_key'), 0));
            v_req := jsonb_build_object('operation', 'L11_CONFIRM', 'cau_noi_id', p->'cau_noi_id', 'dong_phien_ban_id', p->'dong_phien_ban_id',
                                        'ma_hoa_hoa_don_id', p->'ma_hoa_hoa_don_id', 'ma_hoa_phieu_id', p->'ma_hoa_phieu_id',
                                        'bang_chung_hang_id', p->'bang_chung_hang_id', 'bang_chung_ty_le_id', p->'bang_chung_ty_le_id',
                                        'so_luong_hoa_don', p->'so_luong_hoa_don', 'so_luong_phieu', p->'so_luong_phieu', 'expected_graph', p->'expected_graph',
                                        'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256 INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = b0.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_CONFIRM' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN kho.l11_ket_qua_dong_noi_bo((SELECT c.id FROM kho.lien_ket_dong c WHERE c.phap_nhan_id = b0.phap_nhan_id
                                                    AND c.xac_nhan_bien_nhan_id = cu.id)) || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            -- R1: cùng giao thức chung gốc → pool → hàng (danh tính/bằng chứng/tuyến)
            PERFORM kho.l11_khoa_goc_noi_bo(ARRAY[b0.hoa_don_id], ARRAY[lw0.phieu_id]);
            PERFORM kho.l11_khoa_pool_noi_bo(ARRAY(SELECT e.pool_id FROM kho.ma_hoa_luong_nguon e
                                                    WHERE e.id IN (kho.l11_uuid(p->>'ma_hoa_hoa_don_id'), kho.l11_uuid(p->>'ma_hoa_phieu_id'))));
            PERFORM 1 FROM kho.hoa_don_danh_tinh x WHERE x.id = b0.hoa_don_id FOR SHARE;
            PERFORM 1 FROM kho.phieu_kho_danh_tinh x WHERE x.id = lw0.phieu_id FOR SHARE;
            PERFORM 1 FROM kho.bang_chung_quy_doi_luong q
                WHERE q.id IN (kho.l11_uuid(p->>'bang_chung_hang_id'), kho.l11_uuid(p->>'bang_chung_ty_le_id'))
                   OR q.id IN (SELECT e.bang_chung_ma_hoa_id FROM kho.ma_hoa_luong_nguon e
                               WHERE e.id IN (kho.l11_uuid(p->>'ma_hoa_hoa_don_id'), kho.l11_uuid(p->>'ma_hoa_phieu_id')))
                ORDER BY q.id FOR SHARE;
            PERFORM 1 FROM kho.mua_dich_dong r0 WHERE r0.source_dong_id = b0.source_dong_id AND r0.hien_hanh FOR SHARE;
            v_dg := kho.l11_danh_gia_noi_bo(p);
            IF p->>'expected_graph' IS DISTINCT FROM v_dg->>'expected_graph' THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: đồ thị/ngân sách đã đổi so với lúc xem trước' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_array_length(v_dg->'blockers') > 0 THEN
                RAISE EXCEPTION '%: liên kết số lượng bị chặn (%)', v_dg->'blockers'->>0, v_dg->>'blockers' USING ERRCODE = 'P0001';
            END IF;
            r := v_dg->'refs';
            SELECT k.id, k.chu_so_huu_module INTO pk FROM kho.lien_ket_chung_tu k
                WHERE k.chung_tu_a_id = (r->>'hoa_don_chung_tu_id')::uuid AND k.chung_tu_b_id = (r->>'phieu_chung_tu_id')::uuid AND k.loai = 'HD_PHIEU_KHO'
                  AND k.lich_thu_id IS NULL AND k.trang_thai <> 'HUY' FOR UPDATE;
            IF pk.id IS NOT NULL AND pk.chu_so_huu_module IS DISTINCT FROM 'M5' THEN
                RAISE EXCEPTION 'L11_CHA_KHONG_PHAI_L11: cặp chứng từ đã có liên kết chung không thuộc nhánh L11' USING ERRCODE = 'P0001';
            END IF;
            v_parent := pk.id;
            IF v_parent IS NULL THEN
                INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, so_tien_khop_minor, trang_thai, nguon_suy_luan, nguoi_duyet,
                    duyet_luc, tao_boi, can_cu, chu_so_huu_module, muc_dich_lien_ket, hoa_don_id, phieu_id)
                VALUES (b0.phap_nhan_id, (r->>'hoa_don_chung_tu_id')::uuid, (r->>'phieu_chung_tu_id')::uuid, 'HD_PHIEU_KHO', NULL, 'DA_KHOP', 'NGUOI_L11', ai,
                        now(), ai, jsonb_build_object('contract', 'l11-parent/v1'), 'M5', 'EVIDENCE', (r->>'hoa_don_id')::uuid, (r->>'phieu_id')::uuid)
                RETURNING id INTO v_parent;
            END IF;
            v_child := gen_random_uuid();
            v_actor := nullif(current_setting('ktt.nguoi_dung_id', true), '')::uuid;
            v_ket := jsonb_build_object('child_id', v_child, 'lien_ket_id', v_parent, 'trang_thai_khi_xac_nhan', 'DA_KHOP', 'so_luong', v_dg->'so_luong',
                                        'don_vi', v_dg->'don_vi');
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (b0.phap_nhan_id, 'M5', 'L11_CONFIRM', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO kho.lien_ket_dong (id, phap_nhan_id, lien_ket_id, xac_nhan_bien_nhan_id, hoa_don_id, hoa_don_phien_ban_id, hoa_don_chung_tu_id, cau_noi_id,
                hoa_don_chung_tu_dong_id, hoa_don_dong_id, ma_hoa_hoa_don_id, pool_hoa_don_id, don_vi_hoa_don_id, phieu_id, phieu_phien_ban_id,
                phieu_chung_tu_id, phieu_dong_phien_ban_id, phieu_chung_tu_dong_id, phieu_dong_id, ma_hoa_phieu_id, pool_phieu_id, don_vi_phieu_id,
                tuyen_id, bang_chung_hang_id, bang_chung_ty_le_id, so_luong_hoa_don_nguon, so_luong_phieu_nguon, so_luong_pool_hoa_don,
                so_luong_pool_phieu, trang_thai, hieu_luc, ly_do, tao_boi, tao_boi_id)
            VALUES (v_child, b0.phap_nhan_id, v_parent, v_bn, (r->>'hoa_don_id')::uuid, (r->>'hoa_don_phien_ban_id')::uuid, (r->>'hoa_don_chung_tu_id')::uuid,
                    b0.id, (r->>'hoa_don_chung_tu_dong_id')::uuid, (r->>'hoa_don_dong_id')::uuid, kho.l11_uuid(p->>'ma_hoa_hoa_don_id'),
                    (r->>'pool_hoa_don_id')::uuid, (r->>'don_vi_hoa_don_id')::uuid, (r->>'phieu_id')::uuid, (r->>'phieu_phien_ban_id')::uuid,
                    (r->>'phieu_chung_tu_id')::uuid, lw0.id, (r->>'phieu_chung_tu_dong_id')::uuid, (r->>'phieu_dong_id')::uuid,
                    kho.l11_uuid(p->>'ma_hoa_phieu_id'), (r->>'pool_phieu_id')::uuid, (r->>'don_vi_phieu_id')::uuid, (r->>'tuyen_id')::uuid,
                    kho.l11_uuid(p->>'bang_chung_hang_id'), kho.l11_uuid(p->>'bang_chung_ty_le_id'), (v_dg->'so'->>'a')::numeric,
                    (v_dg->'so'->>'b')::numeric, (v_dg->'so'->>'pa')::numeric, (v_dg->'so'->>'pb')::numeric, 'DA_KHOP', 'CO_HIEU_LUC', p->>'reason', ai, v_actor);
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (b0.phap_nhan_id, ai, 'HE_THONG', 'kho.lien_ket_dong', v_child, 'L11_CONFIRM', v_ket, p->>'reason');
            RETURN kho.l11_ket_qua_dong_noi_bo(v_child) || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # undo: quyền BOTH V2 hiện hành → namespace/H/replay (trạng thái hiện hành) → khóa gốc/pool → child FOR UPDATE → CAS → kỳ → HUY + tombstone +
    # audit; giải phóng ĐÚNG lượng pool đã lưu của child (đọc từ SUM), không đòi eligibility/sức chứa/bằng chứng hiện hành; held/ineligible vẫn undo được
    """CREATE OR REPLACE FUNCTION kho.l11_huy(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); c record; v_req jsonb; v_h text; cu record; v_tok text; v_bn uuid; v_ket jsonb; v_ky text[];
        BEGIN
            SELECT x.* INTO c FROM kho.lien_ket_dong x WHERE x.id = kho.l11_uuid(p->>'child_id');
            IF c.id IS NULL OR NOT kho.l11_quyen_noi_bo(c.phap_nhan_id, 'LINK') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_LIEN_KET: cần M2+M5 và V2 hiện hành trên PN của child' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(btrim(p->>'reason'), '') = ''
               OR coalesce(p->>'expected_graph', '') !~ """ + _L11_HEX + """ THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần child, token trạng thái đang xem, khóa và lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || c.phap_nhan_id || '|M5|L11_UNDO|' || (p->>'client_key'), 0));
            v_req := jsonb_build_object('operation', 'L11_UNDO', 'child_id', p->'child_id', 'expected_graph', p->'expected_graph', 'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256 INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = c.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_UNDO' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN kho.l11_ket_qua_dong_noi_bo(c.id) || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            PERFORM kho.l11_khoa_goc_noi_bo(ARRAY[c.hoa_don_id], ARRAY[c.phieu_id]);
            PERFORM kho.l11_khoa_pool_noi_bo(ARRAY[c.pool_hoa_don_id, c.pool_phieu_id]);
            SELECT x.* INTO c FROM kho.lien_ket_dong x WHERE x.id = c.id FOR UPDATE;
            v_tok := """ + _L11_TOKEN.format(x="kho.l11_ket_qua_dong_noi_bo(c.id)") + """;
            IF p->>'expected_graph' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: trạng thái child đã đổi so với lúc xem' USING ERRCODE = 'P0001';
            END IF;
            IF c.trang_thai <> 'DA_KHOP' THEN
                RAISE EXCEPTION 'L11_DA_HUY: child không còn DA_KHOP' USING ERRCODE = 'P0001';
            END IF;
            SELECT ARRAY[to_char(v.ngay_lap, 'YYYY-MM'), to_char(w.ngay_chung_tu, 'YYYY-MM')] INTO v_ky
                FROM kho.hoa_don_phien_ban v, kho.phieu_kho_phien_ban w WHERE v.id = c.hoa_don_phien_ban_id AND w.id = c.phieu_phien_ban_id;
            IF EXISTS (SELECT 1 FROM kho.khoa_ky k WHERE k.phap_nhan_id = c.phap_nhan_id AND k.ky = ANY (v_ky)) THEN
                RAISE EXCEPTION 'KY_DA_KHOA: kỳ của cặp chứng từ đã khóa' USING ERRCODE = 'P0001';
            END IF;
            v_ket := jsonb_build_object('child_id', c.id, 'trang_thai', 'HUY', 'giai_phong', jsonb_build_object(
                         'pool_hoa_don', kho.l11_text(c.so_luong_pool_hoa_don), 'pool_phieu', kho.l11_text(c.so_luong_pool_phieu)));
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (c.phap_nhan_id, 'M5', 'L11_UNDO', p->>'client_key', v_h, v_ket, ai) RETURNING id INTO v_bn;
            UPDATE kho.lien_ket_dong SET trang_thai = 'HUY', huy_bien_nhan_id = v_bn, huy_boi = ai, huy_luc = now(), huy_ly_do = p->>'reason' WHERE id = c.id;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do)
            VALUES (c.phap_nhan_id, ai, 'HE_THONG', 'kho.lien_ket_dong', c.id, 'L11_UNDO', v_ket, p->>'reason');
            RETURN kho.l11_ket_qua_dong_noi_bo(c.id) || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # ---- giữ soát ĐỒNG BỘ (cùng giao dịch chuyển trạng thái nguồn/tuyến/mapping/bằng chứng): DA_KHOP+CO_HIEU_LUC → CAN_SOAT, giữ nguyên lượng/ID;
    #      chạy trong giao dịch của người nhận/duyệt nguồn bằng chính quyền của thao tác đó (không đòi BOTH V2), không lộ child cho actor nguồn
    """CREATE OR REPLACE FUNCTION kho.l11_can_soat_noi_bo(p_dong uuid[], p_ly_do text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE n integer := 0; k uuid;
        BEGIN
            -- R1 repair02: hiệu lực CAN_SOAT chỉ ghi khi giao dịch đang giữ khóa gốc hai phía của MỌI child bị ảnh hưởng (giao thức chung)
            PERFORM kho.l11_kiem_khoa_dong_noi_bo(p_dong);
            FOR k IN SELECT DISTINCT x FROM unnest(coalesce(p_dong, '{}')) AS x WHERE x IS NOT NULL ORDER BY 1 LOOP
                UPDATE kho.lien_ket_dong c SET hieu_luc = 'CAN_SOAT', can_soat_luc = coalesce(c.can_soat_luc, now()),
                    can_soat_ly_do = CASE WHEN p_ly_do = ANY (c.can_soat_ly_do) THEN c.can_soat_ly_do ELSE c.can_soat_ly_do || p_ly_do END
                    WHERE c.id = k AND c.trang_thai = 'DA_KHOP' AND NOT (p_ly_do = ANY (c.can_soat_ly_do));
                IF FOUND THEN
                    n := n + 1;
                END IF;
            END LOOP;
            RETURN n;
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_hoa_don_doi() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NEW.eligible_content_id IS DISTINCT FROM OLD.eligible_content_id OR NEW.accepted_source_observation_id IS DISTINCT FROM OLD.accepted_source_observation_id THEN
                PERFORM kho.l11_can_soat_noi_bo(ARRAY(SELECT c.id FROM kho.lien_ket_dong c WHERE c.hoa_don_id = NEW.id AND c.trang_thai = 'DA_KHOP'
                                                       AND c.hoa_don_phien_ban_id IS DISTINCT FROM NEW.eligible_content_id), 'NGUON_HOA_DON_DOI');
            END IF;
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER hoa_don_l11_can_soat AFTER UPDATE ON kho.hoa_don_danh_tinh FOR EACH ROW EXECUTE FUNCTION kho.l11_hoa_don_doi()",
    """CREATE OR REPLACE FUNCTION kho.l11_phieu_doi() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NEW.eligible_content_id IS DISTINCT FROM OLD.eligible_content_id OR NEW.accepted_source_observation_id IS DISTINCT FROM OLD.accepted_source_observation_id THEN
                PERFORM kho.l11_can_soat_noi_bo(ARRAY(SELECT c.id FROM kho.lien_ket_dong c WHERE c.phieu_id = NEW.id AND c.trang_thai = 'DA_KHOP'
                                                       AND c.phieu_phien_ban_id IS DISTINCT FROM NEW.eligible_content_id), 'NGUON_PHIEU_DOI');
            END IF;
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER phieu_kho_l11_can_soat AFTER UPDATE ON kho.phieu_kho_danh_tinh FOR EACH ROW EXECUTE FUNCTION kho.l11_phieu_doi()",
    """CREATE OR REPLACE FUNCTION kho.l11_tuyen_doi() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF NEW.predecessor_route_id IS NOT NULL AND NEW.dich <> 'KHO' THEN
                PERFORM kho.l11_can_soat_noi_bo(ARRAY(SELECT c.id FROM kho.lien_ket_dong c WHERE c.tuyen_id = NEW.predecessor_route_id
                                                       AND c.trang_thai = 'DA_KHOP'), 'TUYEN_DOI_KHOI_KHO');
            END IF;
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER mua_dich_dong_l11_can_soat AFTER INSERT ON kho.mua_dich_dong FOR EACH ROW EXECUTE FUNCTION kho.l11_tuyen_doi()",
    """CREATE OR REPLACE FUNCTION kho.l11_anh_xa_doi() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF OLD.state = 'DA_DUYET' AND (NEW.state IS DISTINCT FROM 'DA_DUYET' OR (OLD.valid_to IS NULL AND NEW.valid_to IS NOT NULL)) THEN
                PERFORM kho.l11_can_soat_noi_bo(kho.l11_dong_anh_xa_noi_bo(NEW.id), 'MAPPING_DOI');
            END IF;
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER anh_xa_nguon_l11_can_soat AFTER UPDATE ON master.anh_xa_nguon FOR EACH ROW EXECUTE FUNCTION kho.l11_anh_xa_doi()",
    # ---- FILE chế độ L11_QUANTITY (riêng, owner-derived, bất biến): BOTH READ + quyền file M5 TRƯỚC tra cứu/replay; token toàn đồ thị số lượng
    """CREATE OR REPLACE FUNCTION kho.l11_co_so_file_noi_bo(p_lien_ket uuid) RETURNS jsonb
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        SELECT jsonb_build_object('contract', 'l11-file/v1',
            'lien_ket', jsonb_build_object('id', k.id, 'phap_nhan_id', k.phap_nhan_id, 'hoa_don_id', k.hoa_don_id, 'phieu_id', k.phieu_id,
                                           'chung_tu_a', k.chung_tu_a_id, 'chung_tu_b', k.chung_tu_b_id, 'trang_thai', k.trang_thai),
            'hoa_don', (SELECT jsonb_build_object('id', d.id, 'dinh_danh', jsonb_build_array(d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan),
                                                  'latest', d.latest_observation_id, 'accepted', d.accepted_source_observation_id, 'eligible', d.eligible_content_id)
                        FROM kho.hoa_don_danh_tinh d WHERE d.id = k.hoa_don_id),
            'phieu', (SELECT jsonb_build_object('id', d.id, 'nguon', d.source_instance_id, 'so_phieu', d.so_phieu_key, 'ma_kho', d.ma_kho,
                                                'latest', d.latest_observation_id, 'accepted', d.accepted_source_observation_id, 'eligible', d.eligible_content_id)
                      FROM kho.phieu_kho_danh_tinh d WHERE d.id = k.phieu_id),
            'dong', (SELECT coalesce(jsonb_agg(kho.l11_ket_qua_dong_noi_bo(c.id) || jsonb_build_object(
                         'tuyen', (SELECT jsonb_build_object('id', r.id, 'dich', r.dich, 'hien_hanh', r.hien_hanh, 'trang_thai', r.trang_thai)
                                   FROM kho.mua_dich_dong r WHERE r.id = c.tuyen_id),
                         'bang_chung', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'ref', q.reference_id, 'rev', q.evidence_revision,
                                                                                     'kind', q.kind, 'trang_thai', q.trang_thai,
                                                                                     'native_xml_sha256', q.native_xml_sha256,
                                                                                     'native_byte_length', q.native_byte_length) ORDER BY q.kind), '[]'::jsonb)
                                        FROM kho.bang_chung_quy_doi_luong q WHERE q.id IN (c.bang_chung_hang_id, c.bang_chung_ty_le_id)
                                           OR q.id IN (SELECT e.bang_chung_ma_hoa_id FROM kho.ma_hoa_luong_nguon e WHERE e.id IN (c.ma_hoa_hoa_don_id, c.ma_hoa_phieu_id))),
                         'ma_hoa', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', e.id, 'side', e.owner_module, 'so_luong_nguon', e.so_luong_nguon_text,
                                                                                 'don_vi_nguon', e.don_vi_nguon_text, 'tu_so', e.tu_so::text, 'mau_so', e.mau_so::text,
                                                                                 'suc_chua', kho.l11_text(e.suc_chua), 'can_cu', e.can_cu,
                                                                                 'dinh_nghia_nguon', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u
                                                                                                      WHERE u.id = e.don_vi_nguon_id),
                                                                                 'dinh_nghia_pool', (SELECT u.reference_id FROM master.dinh_nghia_don_vi_luong u
                                                                                                     WHERE u.id = e.don_vi_pool_id),
                                                                                 'do_luong_sha256', e.do_luong_sha256) ORDER BY e.owner_module), '[]'::jsonb)
                                    FROM kho.ma_hoa_luong_nguon e WHERE e.id IN (c.ma_hoa_hoa_don_id, c.ma_hoa_phieu_id)))
                         ORDER BY c.tao_luc, c.id), '[]'::jsonb) FROM kho.lien_ket_dong c WHERE c.lien_ket_id = k.id),
            'ngan_sach', (SELECT coalesce(jsonb_agg(kho.l11_ngan_sach_noi_bo(z.pid) ORDER BY z.pid), '[]'::jsonb)
                          FROM (SELECT DISTINCT c.pool_hoa_don_id AS pid FROM kho.lien_ket_dong c WHERE c.lien_ket_id = k.id
                                UNION SELECT DISTINCT c.pool_phieu_id FROM kho.lien_ket_dong c WHERE c.lien_ket_id = k.id) z))
        FROM kho.lien_ket_chung_tu k WHERE k.id = p_lien_ket AND k.chu_so_huu_module = 'M5'
        $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_co_so_file(p_lien_ket uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE v_pn uuid; v jsonb;
        BEGIN
            SELECT k.phap_nhan_id INTO v_pn FROM kho.lien_ket_chung_tu k WHERE k.id = p_lien_ket AND k.chu_so_huu_module = 'M5';
            IF v_pn IS NULL OR NOT kho.l11_quyen_noi_bo(v_pn, 'READ') THEN
                RETURN NULL;
            END IF;
            v := kho.l11_co_so_file_noi_bo(p_lien_ket);
            RETURN v || jsonb_build_object('co_so_sha256', """ + _L11_TOKEN.format(x="v") + """,
                                           'duoc_file', kho.l11_quyen_noi_bo(v_pn, 'FILE'), 'duoc_lien_ket', kho.l11_quyen_noi_bo(v_pn, 'LINK'),
                                           'token_dong', (SELECT coalesce(jsonb_object_agg(c.id::text, """
                                           + _L11_TOKEN.format(x="kho.l11_ket_qua_dong_noi_bo(c.id)") + """), '{}'::jsonb)
                                                          FROM kho.lien_ket_dong c WHERE c.lien_ket_id = p_lien_ket));
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_file_bat_dau(p jsonb) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, pg_temp AS $$
        DECLARE k record; v_req jsonb; v_h text; cu record; v_co_so jsonb; v_tok text; v_pb record;
        BEGIN
            SELECT x.* INTO k FROM kho.lien_ket_chung_tu x WHERE x.id = kho.l11_uuid(p->>'lien_ket_id') AND x.chu_so_huu_module = 'M5';
            IF k.id IS NULL OR NOT kho.l11_quyen_noi_bo(k.phap_nhan_id, 'FILE') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_FILE: file số lượng chéo cần M2_READ + M5_READ + quyền file soát M5 hiện hành' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(p->>'client_key', '') !~ """ + _L11_KHOA_RE + """ OR coalesce(p->>'co_so_truoc', '') !~ """ + _L11_HEX + """
               OR coalesce(btrim(p->>'reason'), '') = '' THEN
                RAISE EXCEPTION 'L11_YEU_CAU_SAI: cần liên kết, token đồ thị số lượng đang xem, khóa và lý do' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || k.phap_nhan_id || '|M5|L11_FILE|' || (p->>'client_key'), 0));
            v_req := jsonb_build_object('operation', 'L11_FILE', 'che_do', 'L11_QUANTITY', 'lien_ket_id', p->'lien_ket_id', 'co_so_truoc', p->'co_so_truoc',
                                        'reason', p->'reason');
            v_h := """ + _L11_TOKEN.format(x="v_req") + """;
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = k.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_FILE' AND x.client_key = p->>'client_key';
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM v_h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa file đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN jsonb_build_object('lap_lai', true, 'h', v_h, 'ket_qua', cu.result_json || jsonb_build_object('bien_nhan_id', cu.id));
            END IF;
            PERFORM kho.l11_khoa_goc_noi_bo(ARRAY[k.hoa_don_id], ARRAY[k.phieu_id]);
            v_co_so := kho.l11_co_so_file_noi_bo(k.id);
            v_tok := """ + _L11_TOKEN.format(x="v_co_so") + """;
            IF p->>'co_so_truoc' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: đồ thị số lượng đã đổi so với lúc xem — 0 file mới' USING ERRCODE = 'P0001';
            END IF;
            SELECT w.profile_ref, w.profile_sha256, d.source_instance_id, to_char(w.ngay_chung_tu, 'YYYY-MM') AS ky INTO v_pb
                FROM kho.phieu_kho_danh_tinh d JOIN kho.phieu_kho_phien_ban w ON w.chung_tu_id = k.chung_tu_b_id WHERE d.id = k.phieu_id;
            RETURN jsonb_build_object('lap_lai', false, 'h', v_h, 'snapshot', v_co_so || jsonb_build_object('co_so_sha256', v_tok,
                'phap_nhan', (SELECT ma FROM master.phap_nhan WHERE id = k.phap_nhan_id), 'source_instance_id', v_pb.source_instance_id,
                'profile_ref', v_pb.profile_ref, 'profile_sha256', v_pb.profile_sha256, 'ky', v_pb.ky));
        END $$""",
    """CREATE OR REPLACE FUNCTION kho.l11_file_tieu_thu(p_stage uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, kho, giao_tiep, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); s record; q jsonb; k record; cu record; v_tok text; v_lo uuid; v_bn uuid; v_ket jsonb;
        BEGIN
            SELECT x.* INTO s FROM giao_tiep.stage_tin_cay x WHERE x.id = p_stage AND x.muc_dich = 'L11_FILE';
            IF s.id IS NULL OR s.h IS DISTINCT FROM p_h THEN
                RAISE EXCEPTION 'STAGE_KHONG_HOP_LE: stage file L11 không tồn tại hoặc H không khớp' USING ERRCODE = 'P0001';
            END IF;
            q := s.du_lieu;
            SELECT x.* INTO k FROM kho.lien_ket_chung_tu x WHERE x.id = kho.l11_uuid(q->>'lien_ket_id') AND x.chu_so_huu_module = 'M5'
                AND x.phap_nhan_id = s.phap_nhan_id;
            IF k.id IS NULL OR ai IS NULL OR s.actor IS DISTINCT FROM ai OR s.actor_id::text IS DISTINCT FROM nullif(current_setting('ktt.nguoi_dung_id', true), '')
               OR NOT kho.l11_quyen_noi_bo(k.phap_nhan_id, 'FILE') THEN
                RAISE EXCEPTION 'KHONG_CO_QUYEN_L11_FILE: stage/quyền file số lượng không còn hợp lệ cho phiên' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('BIEN_NHAN|' || k.phap_nhan_id || '|M5|L11_FILE|' || s.client_key, 0));
            SELECT x.id, x.request_sha256, x.result_json INTO cu FROM kho.bien_nhan_thao_tac x
                WHERE x.phap_nhan_id = k.phap_nhan_id AND x.module = 'M5' AND x.operation = 'L11_FILE' AND x.client_key = s.client_key;
            IF cu.id IS NOT NULL THEN
                IF cu.request_sha256 IS DISTINCT FROM s.h THEN
                    RAISE EXCEPTION 'IDEMPOTENCY_KHAC: khóa file đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN cu.result_json || jsonb_build_object('bien_nhan_id', cu.id, 'lap_lai', true);
            END IF;
            PERFORM kho.l11_khoa_goc_noi_bo(ARRAY[k.hoa_don_id], ARRAY[k.phieu_id]);
            v_tok := """ + _L11_TOKEN.format(x="kho.l11_co_so_file_noi_bo(k.id)") + """;
            IF q->>'co_so_sha256' IS DISTINCT FROM v_tok OR q->>'co_so_truoc' IS DISTINCT FROM v_tok THEN
                RAISE EXCEPTION 'L11_VERSION_CHANGED: đồ thị số lượng đã đổi so với snapshot của file' USING ERRCODE = 'P0001';
            END IF;
            IF coalesce(q->>'artifact_sha256', '') !~ """ + _L11_HEX + """ OR (q->>'byte_length')::bigint <= 0 THEN
                RAISE EXCEPTION 'LO_M5_SAI_MUC_DICH: artifact file L11 không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, duong_dan, hash, so_dong, nguoi, xuat_luc, trang_thai, du_lieu)
            VALUES (k.phap_nhan_id, q->>'ky', 'L11-' || s.id, 'FILE_SOAT', 'm5-xuat/' || (q->>'artifact_sha256') || '.xlsx', q->>'artifact_sha256',
                    (q->>'so_dong')::integer, ai, now(), 'DA_XUAT',
                    jsonb_build_object('module', 'M5', 'muc_dich', 'FILE_SOAT', 'che_do', 'L11_QUANTITY', 'loai', 'L11_SO_LUONG_SOAT', 'stage_id', s.id,
                                       'lien_ket_id', k.id, 'ten', q->>'ten', 'byte_length', (q->>'byte_length')::bigint,
                                       'snapshot_sha256', q->>'snapshot_sha256', 'co_so_sha256', v_tok))
            RETURNING id INTO v_lo;
            v_ket := jsonb_build_object('id', v_lo, 'ten', q->>'ten', 'sha256', q->>'artifact_sha256', 'byte_length', (q->>'byte_length')::bigint,
                                        'lien_ket_id', k.id, 'che_do', 'L11_QUANTITY', 'co_so_sha256', v_tok);
            INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
            VALUES (k.phap_nhan_id, 'M5', 'L11_FILE', s.client_key, s.h, v_ket, ai) RETURNING id INTO v_bn;
            INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau)
            VALUES (k.phap_nhan_id, ai, 'LO', 'kho.lo_xuat', v_lo, 'XUAT_FILE_SOAT_L11', v_ket);
            RETURN v_ket || jsonb_build_object('bien_nhan_id', v_bn, 'lap_lai', false);
        END $$""",
    # ---- ACL/RLS: thu hồi PUBLIC/kế thừa; app_web chỉ SELECT bảng approved/pool/mã hóa/child theo BOTH READ (không raw candidate); hàm nội bộ không cấp
    """REVOKE EXECUTE ON FUNCTION kho.l11_quyen_noi_bo(uuid, text), kho.l11_khoa_goc_noi_bo(uuid[], uuid[]), kho.l11_khoa_pool_noi_bo(uuid[]),
        kho.luong_da_khop_noi_bo(uuid), kho.l11_ngan_sach_noi_bo(uuid), kho.luong_con_lai(uuid), kho.l11_tieu_thu_bang_chung(uuid, text),
        kho.l11_co_so_bang_chung_noi_bo(uuid, uuid, uuid), kho.l11_danh_sach_bang_chung(), kho.l11_xac_nhan_bang_chung(jsonb), kho.l11_huy_bang_chung(jsonb),
        kho.l11_dong_dung_bang_chung_noi_bo(uuid, uuid), kho.l11_co_so_ma_hoa_noi_bo(text, uuid), kho.l11_co_so_ma_hoa(text, uuid), kho.l11_ma_hoa(jsonb),
        kho.l11_danh_gia_noi_bo(jsonb), kho.l11_xem_truoc(jsonb), kho.l11_ket_qua_dong_noi_bo(uuid), kho.l11_xac_nhan(jsonb), kho.l11_huy(jsonb),
        kho.l11_can_soat_noi_bo(uuid[], text), kho.l11_co_so_file_noi_bo(uuid), kho.l11_co_so_file(uuid), kho.l11_file_bat_dau(jsonb),
        kho.l11_file_tieu_thu(uuid, text), kho.l11_giu_khoa_noi_bo(text), kho.l11_kiem_khoa_dong_noi_bo(uuid[]), kho.l11_khoa_dong_nguon_noi_bo(uuid[], uuid[]),
        kho.l11_dong_anh_xa_noi_bo(uuid), kho.l11_do_luong_dong_noi_bo(uuid), kho.l11_don_vi_xac_minh_noi_bo(uuid), kho.l11_ho_tro_don_vi_noi_bo(uuid, text),
        kho.l11_trang_thai_cap_noi_bo(jsonb) FROM PUBLIC""",
    *(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in _L11_BANG),
    """DO $$
    DECLARE t text; r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_ke_toan','app_cong_ai','app_doc','app_web'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                FOREACH t IN ARRAY ARRAY['kho.bang_chung_ung_vien','kho.bang_chung_quy_doi_luong','kho.dich_so_luong','kho.ma_hoa_luong_nguon',
                                         'kho.lien_ket_dong'] LOOP
                    EXECUTE format('REVOKE ALL ON %s FROM %I', t, r);
                END LOOP;
            END IF;
        END LOOP;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            FOREACH t IN ARRAY ARRAY['bang_chung_quy_doi_luong','dich_so_luong','ma_hoa_luong_nguon','lien_ket_dong'] LOOP
                EXECUTE format('GRANT SELECT ON kho.%I TO app_web', t);
                EXECUTE format('DROP POLICY IF EXISTS %I ON kho.%I', t || '_pham_vi_web', t);
                EXECUTE format('CREATE POLICY %I ON kho.%I FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, %L) AND master.ktt_duoc(phap_nhan_id, %L))',
                               t || '_pham_vi_web', t, 'M2', 'M5');
            END LOOP;
            GRANT EXECUTE ON FUNCTION kho.luong_con_lai(uuid), kho.l11_danh_sach_bang_chung(), kho.l11_xac_nhan_bang_chung(jsonb), kho.l11_huy_bang_chung(jsonb),
                kho.l11_co_so_ma_hoa(text, uuid), kho.l11_ma_hoa(jsonb), kho.l11_xem_truoc(jsonb), kho.l11_xac_nhan(jsonb), kho.l11_huy(jsonb),
                kho.l11_co_so_file(uuid) TO app_web;
            -- parent: nhánh L11 chỉ hiện với BOTH READ hiện hành; app không tạo/sửa hàng L11 (WITH CHECK chỉ nhánh chung M1 như cũ)
            DROP POLICY IF EXISTS lien_ket_chung_tu_pham_vi_web ON kho.lien_ket_chung_tu;
            CREATE POLICY lien_ket_chung_tu_pham_vi_web ON kho.lien_ket_chung_tu TO app_web
                USING (CASE WHEN chu_so_huu_module IS NULL THEN master.ktt_duoc(phap_nhan_id, 'M1')
                            ELSE master.ktt_duoc(phap_nhan_id, 'M2') AND master.ktt_duoc(phap_nhan_id, 'M5') END)
                WITH CHECK (chu_so_huu_module IS NULL AND master.ktt_duoc(phap_nhan_id, 'M1'));
            DROP POLICY IF EXISTS lo_xuat_pham_vi_web ON kho.lo_xuat;
            CREATE POLICY lo_xuat_pham_vi_web ON kho.lo_xuat TO app_web
                USING (CASE WHEN du_lieu->>'che_do' = 'L11_QUANTITY' THEN master.ktt_duoc(phap_nhan_id, 'M2') AND master.ktt_duoc(phap_nhan_id, 'M5')
                            ELSE master.ktt_duoc(phap_nhan_id, coalesce(du_lieu->>'module', 'M1')) END)
                WITH CHECK (master.ktt_duoc(phap_nhan_id, coalesce(du_lieu->>'module', 'M1')) AND du_lieu->>'che_do' IS NULL);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan') THEN
            DROP POLICY IF EXISTS lien_ket_chung_tu_ung_dung_cu ON kho.lien_ket_chung_tu;
            CREATE POLICY lien_ket_chung_tu_ung_dung_cu ON kho.lien_ket_chung_tu TO app_ke_toan USING (chu_so_huu_module IS NULL) WITH CHECK (chu_so_huu_module IS NULL);
            DROP POLICY IF EXISTS lo_xuat_ung_dung_cu ON kho.lo_xuat;
            CREATE POLICY lo_xuat_ung_dung_cu ON kho.lo_xuat TO app_ke_toan
                USING ((coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5')) AND du_lieu->>'che_do' IS NULL)
                WITH CHECK ((coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5')) AND du_lieu->>'che_do' IS NULL);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_doc') THEN
            DROP POLICY IF EXISTS lien_ket_chung_tu_chi_doc ON kho.lien_ket_chung_tu;
            CREATE POLICY lien_ket_chung_tu_chi_doc ON kho.lien_ket_chung_tu FOR SELECT TO app_doc USING (chu_so_huu_module IS NULL);
            DROP POLICY IF EXISTS lo_xuat_chi_doc ON kho.lo_xuat;
            CREATE POLICY lo_xuat_chi_doc ON kho.lo_xuat FOR SELECT TO app_doc
                USING ((coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5')) AND du_lieu->>'che_do' IS NULL);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_cong_ai') THEN
            DROP POLICY IF EXISTS lien_ket_chung_tu_cong_ai ON kho.lien_ket_chung_tu;
            CREATE POLICY lien_ket_chung_tu_cong_ai ON kho.lien_ket_chung_tu FOR SELECT TO app_cong_ai USING (chu_so_huu_module IS NULL);
            DROP POLICY IF EXISTS lo_xuat_cong_ai ON kho.lo_xuat;
            CREATE POLICY lo_xuat_cong_ai ON kho.lo_xuat FOR SELECT TO app_cong_ai
                USING ((coalesce(du_lieu->>'module', 'M1') <> 'M5' OR master.ktt_duoc(phap_nhan_id, 'M5')) AND du_lieu->>'che_do' IS NULL);
        END IF;
    END $$""",
)

def _m16_thay(nguon: tuple, dau: str, cu: str, moi: str) -> str:
    """CREATE OR REPLACE trong 16 sinh từ ĐÚNG statement lịch sử (M14/M15 giữ nguyên byte): chèn đúng một chỗ, assert một lần xuất hiện."""
    stmt = next(s for s in reversed(nguon) if s.startswith(dau))
    assert stmt.count(cu) == 1, (dau, cu)
    return stmt.replace(cu, moi, 1)


_R1_GHI_CHU = "  -- L11 R1 repair02: precollect + khóa closure toàn batch (gốc hai phía → pool → child) trước khóa/ghi nguồn\n"
_R1_PHIEU_KEY = ("            PERFORM kho.l11_khoa_dong_nguon_noi_bo(NULL, ARRAY(SELECT x.id FROM kho.phieu_kho_danh_tinh x\n"
                 "                WHERE x.source_instance_id = {inst} AND x.so_phieu_key = {so}));" + _R1_GHI_CHU)
_R1_HD = "            PERFORM kho.l11_khoa_dong_nguon_noi_bo(ARRAY[d0.id], NULL);" + _R1_GHI_CHU
_R1_GOC_HD = "            PERFORM pg_advisory_xact_lock(hashtextextended('HOA_DON_ROOT|' || d0.id, 0));\n"
# repair03 (R1-L01): CỔNG IDENTITY TOÀN BATCH trước mọi gốc/pool của consumer M2 (XML đơn, XML nhiều, ZIP; danh tính mới/đã có/vừa xuất hiện).
#   Thứ tự: hàng mapping công ty (sorted FOR SHARE, thứ tự R15) → MỌI namespace `HOA_DON|PN|identity` của batch (sorted theo khóa văn bản) →
#   dưới namespace: tạo SKELETON danh tính cho identity mới hợp lệ (chỉ hàng danh tính, cùng giá trị/điều kiện mà vòng lặp lịch sử sẽ chèn;
#   không quan sát/nội dung/con trỏ/core) → resolve TẤT CẢ ID → closure chuẩn (gốc hóa đơn sorted + gốc phiếu ngang hàng → kiểm lại trùng khít →
#   pool → child). Vòng lặp quan sát lịch sử chạy SAU, giữ NGUYÊN thứ tự delivery/occurrence (A,A/A→B→A/ZIP) — mọi khóa nó xin đều tái nhập.
#   Namespace HOA_DON chỉ do consumer này xin; không đường L11/source khác xin namespace sau gốc ⇒ một thứ tự chung namespace → gốc → pool → hàng.
_R1_M2_BATCH = (
    "            -- L11 R1 repair03: cổng identity toàn batch (mapping → namespace sorted → skeleton danh tính → closure) trước vòng lặp lịch sử\n"
    "            DECLARE r1_k text; r1_hd uuid[];\n"
    "            BEGIN\n"
    "                PERFORM 1 FROM master.anh_xa_nguon x WHERE x.id IN (SELECT (e->>'company_mapping_id')::uuid\n"
    "                    FROM jsonb_array_elements(coalesce(s.du_lieu->'promote_m2', '[]'::jsonb)) e) ORDER BY x.id FOR SHARE;\n"
    "                FOR r1_k IN SELECT DISTINCT 'HOA_DON|' || x.phap_nhan_id || '|' || (e->'identity')::text\n"
    "                            FROM jsonb_array_elements(coalesce(s.du_lieu->'promote_m2', '[]'::jsonb)) e\n"
    "                            JOIN master.anh_xa_nguon x ON x.id = (e->>'company_mapping_id')::uuid ORDER BY 1 LOOP\n"
    "                    PERFORM pg_advisory_xact_lock(hashtextextended(r1_k, 0));\n"
    "                END LOOP;\n"
    "                INSERT INTO kho.hoa_don_danh_tinh (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan, source_instance_id, created_by)\n"
    "                SELECT DISTINCT x.phap_nhan_id, 'MUA_VAO', e->'identity'->>2, e->'identity'->>3, e->'identity'->>4, e->'identity'->>5,\n"
    "                       l.source_instance_id, ai\n"
    "                FROM jsonb_array_elements(coalesce(s.du_lieu->'promote_m2', '[]'::jsonb)) e\n"
    "                JOIN master.anh_xa_nguon x ON x.id = (e->>'company_mapping_id')::uuid AND x.subject_kind = 'COMPANY' AND x.subject_key = e->>'company_key'\n"
    "                 AND x.source_instance_id = l.source_instance_id AND x.profile_ref = l.profile_ref AND x.profile_sha256 = l.profile_sha256\n"
    "                 AND x.state = 'DA_DUYET' AND x.valid_from <= now() AND (x.valid_to IS NULL OR x.valid_to > now())\n"
    "                JOIN master.phap_nhan pn ON pn.id = x.phap_nhan_id\n"
    "                WHERE e->>'direction' = 'MUA_VAO' AND jsonb_array_length(e->'identity') = 6 AND e->'identity'->>0 = pn.ma\n"
    "                  AND e->'identity'->>1 = 'MUA_VAO'\n"
    "                ORDER BY 1, 3, 4, 5, 6\n"
    "                ON CONFLICT (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan) DO NOTHING;\n"
    "                SELECT coalesce(array_agg(DISTINCT h.id ORDER BY h.id), '{}') INTO r1_hd\n"
    "                FROM jsonb_array_elements(coalesce(s.du_lieu->'promote_m2', '[]'::jsonb)) e\n"
    "                JOIN master.anh_xa_nguon x ON x.id = (e->>'company_mapping_id')::uuid\n"
    "                JOIN kho.hoa_don_danh_tinh h ON h.phap_nhan_id = x.phap_nhan_id AND h.chieu = 'MUA_VAO' AND h.mst_ban = e->'identity'->>2\n"
    "                 AND h.mau_so = e->'identity'->>3 AND h.ky_hieu = e->'identity'->>4 AND h.so_chuan = e->'identity'->>5;\n"
    "                PERFORM kho.l11_khoa_dong_nguon_noi_bo(r1_hd, NULL);\n"
    "            END;\n"
)
_L11_R1_THAY = (
    # ---- M5 (5 đường): khóa closure ngay TẠI điểm khóa gốc phiếu cũ (sau hàng mapping FOR SHARE theo thứ tự R14); khóa gốc cũ sau đó tái nhập
    _m16_thay(M0014_M5, "CREATE OR REPLACE FUNCTION kho.m5_khoa_phieu(",
              "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || p_so_phieu, 0));\n",
              _R1_PHIEU_KEY.format(inst="l.source_instance_id", so="p_so_phieu")
              + "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || p_so_phieu, 0));\n"),
    _m16_thay(M0014_M5, "CREATE OR REPLACE FUNCTION kho.m5_tieu_thu_quan_sat(",
              "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || v_so, 0));\n",
              _R1_PHIEU_KEY.format(inst="l.source_instance_id", so="v_so")
              + "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || v_so, 0));\n"),
    _m16_thay(M0014_M5, "CREATE OR REPLACE FUNCTION kho.m5_giu_cho_anh_huong(",
              "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || s.source_instance_id || '|' || v_so, 0));\n",
              _R1_PHIEU_KEY.format(inst="s.source_instance_id", so="v_so")
              + "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || s.source_instance_id || '|' || v_so, 0));\n"),
    _m16_thay(M0014_M5, "CREATE OR REPLACE FUNCTION kho.m5_xem_xet_nguon(",
              "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || d0.source_instance_id || '|' || d0.so_phieu_key, 0));\n",
              "            PERFORM kho.l11_khoa_dong_nguon_noi_bo(NULL, ARRAY[d0.id]);" + _R1_GHI_CHU
              + "            PERFORM pg_advisory_xact_lock(hashtextextended('PHIEU_KHO|' || d0.source_instance_id || '|' || d0.so_phieu_key, 0));\n"),
    _m16_thay(M0014_M5, "CREATE OR REPLACE FUNCTION kho.m5_anh_xa_v4(",
              "                -- đóng bản cũ: trigger INVOKER kiểm quyền trên PN CŨ của chính phiên (SOURCE_MAP + CFO V4 + M5)\n",
              "                PERFORM kho.l11_khoa_dong_nguon_noi_bo(NULL, ARRAY(SELECT x.id FROM kho.phieu_kho_danh_tinh x\n"
              "                    WHERE x.source_instance_id = v_inst AND x.ma_kho = v_kho));" + _R1_GHI_CHU
              + "                -- đóng bản cũ: trigger INVOKER kiểm quyền trên PN CŨ của chính phiên (SOURCE_MAP + CFO V4 + M5)\n"),
    # ---- M2 (5 đường)
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION kho.m2_tieu_thu_quan_sat(",
              "            SELECT np.id INTO v_prof FROM master.nguon_profile np WHERE np.source_instance_id = l.source_instance_id AND np.profile_ref = l.profile_ref\n",
              _R1_M2_BATCH
              + "            SELECT np.id INTO v_prof FROM master.nguon_profile np WHERE np.source_instance_id = l.source_instance_id AND np.profile_ref = l.profile_ref\n"),
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION kho.m2_xem_xet_nguon(", _R1_GOC_HD, _R1_HD + _R1_GOC_HD),
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION kho.m2_mapping_dong(", _R1_GOC_HD, _R1_HD + _R1_GOC_HD),
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION kho.m2_route(", _R1_GOC_HD, _R1_HD + _R1_GOC_HD),
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION kho.m2_mapping_cong_ty(",
              "                UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = hien.id;\n",
              "                PERFORM kho.l11_khoa_dong_nguon_noi_bo(ARRAY(SELECT DISTINCT v.hoa_don_id FROM kho.hoa_don_phien_ban v\n"
              "                    WHERE v.company_mapping_id = hien.id), NULL);" + _R1_GHI_CHU
              + "                UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = hien.id;\n"),
    # ---- shared mapping trigger (đường ghi chung của mọi mapping): đóng mapping chỉ khi mọi child bị ảnh hưởng đã được khóa gốc hai phía TRƯỚC tuple
    _m16_thay(M0015_M2_BRIDGE, "CREATE OR REPLACE FUNCTION master.anh_xa_nguon_kiem(",
              "                END IF;\n                RETURN NEW;\n            END IF;\n            IF NOT chu THEN\n",
              "                END IF;\n"
              "                PERFORM kho.l11_kiem_khoa_dong_noi_bo(kho.l11_dong_anh_xa_noi_bo(OLD.id));  -- L11 R1 repair02: kiểm closure đã khóa trước tuple\n"
              "                RETURN NEW;\n            END IF;\n            IF NOT chu THEN\n"),
)

M0016_L11_QUANTITY = (
    "SET LOCAL check_function_bodies = off",
    # ---- COMMON: scope L11_EVIDENCE_SET có PN typed (không giả kho/phiếu/company); stage mục đích L11_PROOF / L11_FILE (đóng, có PN)
    "ALTER TABLE master.nguon_pham_vi ADD COLUMN phap_nhan_id uuid REFERENCES master.phap_nhan(id)",
    "ALTER TABLE master.nguon_pham_vi DROP CONSTRAINT nguon_pham_vi_kind_m2_check",
    """ALTER TABLE master.nguon_pham_vi ADD CONSTRAINT nguon_pham_vi_kind_l11_check CHECK (coalesce(
        (scope_kind = 'KHO10_PHIEU' AND ma_kho IS NOT NULL AND so_phieu IS NOT NULL AND company_keys IS NULL AND phap_nhan_id IS NULL)
        OR (scope_kind = 'INVOICE_SET' AND ma_kho IS NULL AND so_phieu IS NULL AND company_keys IS NOT NULL AND cardinality(company_keys) >= 1
            AND phap_nhan_id IS NULL)
        OR (scope_kind = 'L11_EVIDENCE_SET' AND ma_kho IS NULL AND so_phieu IS NULL AND company_keys IS NULL AND phap_nhan_id IS NOT NULL
            AND sections = ARRAY['L11_PROOF_JSON']::text[]), false))""",
    "ALTER TABLE giao_tiep.stage_tin_cay DROP CONSTRAINT stage_tin_cay_muc_dich_check",
    "ALTER TABLE giao_tiep.stage_tin_cay ADD CONSTRAINT stage_tin_cay_muc_dich_l11_check CHECK (muc_dich IN ('CAPTURE','FILE_SOAT','L11_PROOF','L11_FILE'))",
    "ALTER TABLE giao_tiep.stage_tin_cay ADD CONSTRAINT stage_tin_cay_l11_pn_check CHECK (muc_dich NOT IN ('L11_PROOF','L11_FILE') OR phap_nhan_id IS NOT NULL)",
    # ---- parent dùng lại: kho.lien_ket_chung_tu HD_PHIEU_KHO; nhánh L11 thêm chủ M5 / mục đích EVIDENCE / gốc typed (hóa đơn, phiếu), tiền NULL
    "ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_l11_pn_id_uq UNIQUE (phap_nhan_id, id)",
    """ALTER TABLE kho.lien_ket_chung_tu
        ADD COLUMN chu_so_huu_module text,
        ADD COLUMN muc_dich_lien_ket text,
        ADD COLUMN hoa_don_id uuid REFERENCES kho.hoa_don_danh_tinh(id),
        ADD COLUMN phieu_id uuid REFERENCES kho.phieu_kho_danh_tinh(id)""",
    """ALTER TABLE kho.lien_ket_chung_tu ADD CONSTRAINT lien_ket_l11_check CHECK (coalesce(
        (chu_so_huu_module IS NULL AND muc_dich_lien_ket IS NULL AND hoa_don_id IS NULL AND phieu_id IS NULL)
        OR (chu_so_huu_module = 'M5' AND muc_dich_lien_ket = 'EVIDENCE' AND loai = 'HD_PHIEU_KHO' AND so_tien_khop_minor IS NULL
            AND lich_thu_id IS NULL AND hoa_don_id IS NOT NULL AND phieu_id IS NOT NULL), false))""",
    # parent nhánh L11: chỉ chủ bảng (definer xác nhận) tạo; bất biến hoàn toàn (không HUY chung — HUY parent không giải phóng child);
    # đường chung (chủ NULL) không được trỏ chứng từ core M2/M5 mới (không giả hàng cũ cho graph typed)
    """CREATE OR REPLACE FUNCTION kho.lien_ket_l11_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE a record; b record;
        BEGIN
            IF TG_OP = 'UPDATE' AND (NEW.chu_so_huu_module, NEW.muc_dich_lien_ket, NEW.hoa_don_id, NEW.phieu_id)
                                    IS DISTINCT FROM (OLD.chu_so_huu_module, OLD.muc_dich_lien_ket, OLD.hoa_don_id, OLD.phieu_id) THEN
                RAISE EXCEPTION 'L11_CHA_BAT_BIEN: không đổi chủ/mục đích/gốc typed của liên kết' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP <> 'INSERT' AND OLD.chu_so_huu_module IS NOT NULL THEN
                IF TG_OP = 'DELETE' OR NEW IS DISTINCT FROM OLD THEN
                    RAISE EXCEPTION 'L11_CHA_BAT_BIEN: parent số lượng L11 bất biến — hủy theo từng child bằng thao tác undo có quyền' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            -- R3 repair02: đường chung (chủ NULL) kiểm endpoint MỚI cả INSERT lẫn UPDATE đổi endpoint — hàng cũ M1/CRM không được retarget vào core
            -- M2/M5 rồi đi policy cũ; UPDATE giữ nguyên endpoint (vd HUY liên kết cũ thật) giữ hành vi cũ
            IF NEW.chu_so_huu_module IS NULL AND (TG_OP = 'INSERT' OR (NEW.chung_tu_a_id, NEW.chung_tu_b_id) IS DISTINCT FROM (OLD.chung_tu_a_id, OLD.chung_tu_b_id)) THEN
                IF EXISTS (SELECT 1 FROM kho.chung_tu c WHERE c.id IN (NEW.chung_tu_a_id, NEW.chung_tu_b_id) AND c.module_nghiep_vu IN ('M2','M5')) THEN
                    RAISE EXCEPTION 'L11_LIEN_KET_CHUNG_GIA: liên kết chung không trỏ chứng từ core M2/M5 (dùng nhánh L11 typed)' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_OP = 'INSERT' THEN
                SELECT c.* INTO a FROM kho.chung_tu c WHERE c.id = NEW.chung_tu_a_id;
                SELECT c.* INTO b FROM kho.chung_tu c WHERE c.id = NEW.chung_tu_b_id;
                IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                    RAISE EXCEPTION 'L11_CHA_CHI_CHU: parent L11 chỉ do hàm xác nhận của chủ bảng tạo' USING ERRCODE = 'P0001';
                END IF;
                IF a.module_nghiep_vu IS DISTINCT FROM 'M2' OR a.loai IS DISTINCT FROM 'HD_MUA' OR b.module_nghiep_vu IS DISTINCT FROM 'M5'
                   OR b.loai IS DISTINCT FROM 'PHIEU_KHO' OR a.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR b.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id
                   OR NOT EXISTS (SELECT 1 FROM kho.hoa_don_phien_ban v WHERE v.chung_tu_id = a.id AND v.hoa_don_id = NEW.hoa_don_id)
                   OR NOT EXISTS (SELECT 1 FROM kho.phieu_kho_phien_ban v WHERE v.chung_tu_id = b.id AND v.phieu_id = NEW.phieu_id)
                   OR NEW.trang_thai IS DISTINCT FROM 'DA_KHOP' THEN
                    RAISE EXCEPTION 'L11_CHA_SAI_DO_THI: parent L11 phải là cặp chứng từ HD_MUA M2 ↔ PHIEU_KHO M5 cùng PN của đúng gốc typed' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lien_ket_l11_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.lien_ket_chung_tu FOR EACH ROW EXECUTE FUNCTION kho.lien_ket_l11_kiem()",
    # ---- raw candidate bằng chứng (COMMON capture + stage L11_PROOF): bất biến, KHÔNG phải approval
    """CREATE TABLE kho.bang_chung_ung_vien (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        lan_tiep_nhan_id uuid NOT NULL UNIQUE,
        source_instance_id text NOT NULL,
        snapshot_id uuid NOT NULL,
        source_row_id uuid,
        stage_id uuid NOT NULL UNIQUE REFERENCES giao_tiep.stage_tin_cay(id),
        reference_id text,
        evidence_revision integer CHECK (evidence_revision IS NULL OR evidence_revision >= 1),
        kind text CHECK (kind IS NULL OR kind IN ('GOODS_EQUIVALENCE','CROSS_NATIVE_RATIO','NATIVE_ENCODING')),
        raw_sha256 text CHECK (raw_sha256 IS NULL OR raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint CHECK (byte_length IS NULL OR byte_length >= 1),
        payload_sha256 text CHECK (payload_sha256 IS NULL OR payload_sha256 ~ '^[0-9a-f]{64}$'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('UNG_VIEN','HOLD')),
        issues text[] NOT NULL DEFAULT '{}',
        coverage text NOT NULL,
        coverage_hieu_luc text NOT NULL,
        reported_errors text[] NOT NULL DEFAULT '{}',
        tao_luc timestamptz NOT NULL DEFAULT now(),
        tao_boi text NOT NULL,
        CHECK (trang_thai = 'HOLD' OR (coverage = 'COMPLETE_INPUT' AND coverage_hieu_luc = 'COMPLETE_INPUT' AND cardinality(reported_errors) = 0)),
        CHECK (coalesce((trang_thai = 'UNG_VIEN' AND cardinality(issues) = 0 AND source_row_id IS NOT NULL AND reference_id IS NOT NULL
                         AND evidence_revision IS NOT NULL AND kind IS NOT NULL AND raw_sha256 IS NOT NULL AND byte_length IS NOT NULL
                         AND payload_sha256 IS NOT NULL)
                        OR (trang_thai = 'HOLD' AND cardinality(issues) >= 1), false)),
        FOREIGN KEY (lan_tiep_nhan_id, source_instance_id, snapshot_id) REFERENCES giao_tiep.lan_tiep_nhan_nguon (id, source_instance_id, snapshot_id),
        FOREIGN KEY (source_row_id, snapshot_id) REFERENCES kho.ban_ghi_nguon (id, snapshot_id),
        UNIQUE (phap_nhan_id, id))""",
    # ---- bằng chứng đã xác nhận (CFO BOTH V4): hàng hóa / tỷ lệ cross-native / mã hóa native; facts bất biến, chỉ thu hồi một lần có vết
    """CREATE TABLE kho.bang_chung_quy_doi_luong (
        id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        ung_vien_id uuid NOT NULL UNIQUE,
        reference_id text NOT NULL,
        evidence_revision integer NOT NULL CHECK (evidence_revision >= 1),
        kind text NOT NULL CHECK (kind IN ('GOODS_EQUIVALENCE','CROSS_NATIVE_RATIO','NATIVE_ENCODING')),
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 1),
        payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
        hang_hoa_bang_chung_id uuid,
        hang_hoa_hoa_don text,
        hang_hoa_kho text,
        tu_don_vi_id uuid,
        tu_don_vi_sha256 text,
        den_don_vi_id uuid,
        den_don_vi_sha256 text,
        don_vi_id uuid,
        don_vi_sha256 text,
        tu_so numeric(38,0),
        mau_so numeric(38,0),
        native_xml_sha256 text,
        native_byte_length bigint CHECK (native_byte_length IS NULL OR native_byte_length >= 1),
        quantity_locator text,
        unit_locator text,
        unit_lexeme text,
        quantity_lexeme text,
        mien jsonb,
        rang_buoc jsonb NOT NULL CHECK (jsonb_typeof(rang_buoc) = 'array'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DA_XAC_NHAN','DA_THU_HOI')),
        xac_nhan_boi text NOT NULL,
        xac_nhan_luc timestamptz NOT NULL DEFAULT now(),
        xac_nhan_bien_nhan_id uuid NOT NULL,
        thu_hoi_boi text,
        thu_hoi_luc timestamptz,
        thu_hoi_bien_nhan_id uuid,
        thu_hoi_ly_do text,
        CHECK (coalesce((trang_thai = 'DA_XAC_NHAN' AND thu_hoi_boi IS NULL AND thu_hoi_luc IS NULL AND thu_hoi_bien_nhan_id IS NULL AND thu_hoi_ly_do IS NULL)
                        OR (trang_thai = 'DA_THU_HOI' AND thu_hoi_boi IS NOT NULL AND thu_hoi_luc IS NOT NULL AND thu_hoi_bien_nhan_id IS NOT NULL
                            AND thu_hoi_ly_do IS NOT NULL), false)),
        CHECK (coalesce(
            (kind = 'GOODS_EQUIVALENCE' AND hang_hoa_hoa_don IS NOT NULL AND hang_hoa_kho IS NOT NULL AND hang_hoa_bang_chung_id IS NULL
             AND tu_don_vi_id IS NULL AND den_don_vi_id IS NULL AND don_vi_id IS NULL AND tu_so IS NULL AND mau_so IS NULL AND native_xml_sha256 IS NULL
             AND native_byte_length IS NULL
             AND jsonb_array_length(rang_buoc) >= 1 AND jsonb_typeof(mien->'invoice') = 'object' AND jsonb_typeof(mien->'warehouse') = 'object')
            OR (kind = 'CROSS_NATIVE_RATIO' AND hang_hoa_bang_chung_id IS NOT NULL AND tu_don_vi_id IS NOT NULL AND tu_don_vi_sha256 IS NOT NULL
                AND den_don_vi_id IS NOT NULL AND den_don_vi_sha256 IS NOT NULL AND tu_so IS NOT NULL AND mau_so IS NOT NULL AND tu_so > 0 AND mau_so > 0
                AND gcd(tu_so, mau_so) = 1 AND hang_hoa_hoa_don IS NULL AND hang_hoa_kho IS NULL AND don_vi_id IS NULL AND native_xml_sha256 IS NULL
                AND native_byte_length IS NULL
                AND mien IS NULL)
            -- R2 repair02: mã hóa native → own-pool lưu RIÊNG hai tuple đã xác minh qua MASTER chung: tu_don_vi = định nghĩa đơn vị NATIVE của dòng,
            --   den_don_vi = định nghĩa đơn vị POOL; tỷ lệ tu_so/mau_so là native→pool khai báo độc lập (không suy bắc cầu/không theo nhãn)
            OR (kind = 'NATIVE_ENCODING' AND hang_hoa_bang_chung_id IS NOT NULL AND tu_don_vi_id IS NOT NULL AND tu_don_vi_sha256 IS NOT NULL
                AND den_don_vi_id IS NOT NULL AND den_don_vi_sha256 IS NOT NULL AND don_vi_id IS NULL AND don_vi_sha256 IS NULL
                AND tu_so IS NOT NULL AND mau_so IS NOT NULL AND tu_so > 0 AND mau_so > 0 AND gcd(tu_so, mau_so) = 1
                AND native_xml_sha256 IS NOT NULL AND native_xml_sha256 ~ '^[0-9a-f]{64}$' AND native_byte_length IS NOT NULL
                AND quantity_locator IS NOT NULL AND unit_locator IS NOT NULL
                AND unit_lexeme IS NOT NULL AND hang_hoa_hoa_don IS NULL AND hang_hoa_kho IS NULL AND jsonb_typeof(mien) = 'object'
                AND (tu_don_vi_id <> den_don_vi_id OR (tu_so = 1 AND mau_so = 1))),
            false)),
        FOREIGN KEY (phap_nhan_id, ung_vien_id) REFERENCES kho.bang_chung_ung_vien (phap_nhan_id, id),
        FOREIGN KEY (tu_don_vi_id, tu_don_vi_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        FOREIGN KEY (den_don_vi_id, den_don_vi_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        FOREIGN KEY (don_vi_id, don_vi_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        FOREIGN KEY (phap_nhan_id, xac_nhan_bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, thu_hoi_bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id),
        UNIQUE (phap_nhan_id, reference_id, evidence_revision),
        UNIQUE (phap_nhan_id, id))""",
    """ALTER TABLE kho.bang_chung_quy_doi_luong ADD CONSTRAINT bang_chung_hang_fk
        FOREIGN KEY (phap_nhan_id, hang_hoa_bang_chung_id) REFERENCES kho.bang_chung_quy_doi_luong (phap_nhan_id, id)""",
    # ---- pool số lượng ổn định: một pool mỗi gốc logic typed (dòng logic hóa đơn M2 / dòng logic phiếu M5); đơn vị pool cố định, không theo PB/key
    """CREATE TABLE kho.dich_so_luong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        owner_module text NOT NULL CHECK (owner_module IN ('M2','M5')),
        pool_kind text NOT NULL CHECK (pool_kind = 'L11'),
        hoa_don_id uuid,
        hoa_don_dong_id uuid,
        phieu_id uuid,
        phieu_dong_id uuid,
        don_vi_id uuid NOT NULL,
        don_vi_sha256 text NOT NULL,
        mien_so text NOT NULL DEFAULT 'EXACT_DECIMAL_38_12' CHECK (mien_so = 'EXACT_DECIMAL_38_12'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (coalesce((owner_module = 'M2' AND hoa_don_id IS NOT NULL AND hoa_don_dong_id IS NOT NULL AND phieu_id IS NULL AND phieu_dong_id IS NULL)
                        OR (owner_module = 'M5' AND phieu_id IS NOT NULL AND phieu_dong_id IS NOT NULL AND hoa_don_id IS NULL AND hoa_don_dong_id IS NULL), false)),
        FOREIGN KEY (phap_nhan_id, hoa_don_dong_id, hoa_don_id) REFERENCES kho.hoa_don_dong_danh_tinh (phap_nhan_id, id, hoa_don_id),
        FOREIGN KEY (phieu_dong_id, phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_dong_danh_tinh (id, phap_nhan_id, phieu_id),
        FOREIGN KEY (don_vi_id, don_vi_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        UNIQUE (phap_nhan_id, pool_kind, hoa_don_dong_id),
        UNIQUE (phap_nhan_id, pool_kind, phieu_dong_id),
        UNIQUE (phap_nhan_id, id, owner_module),
        UNIQUE (phap_nhan_id, id, don_vi_id))""",
    # ---- mã hóa native → pool (mỗi PB-line typed, theo revision căn cứ đo lường): bất biến; sức chứa = native × tử / mẫu (exact 38,12)
    """CREATE TABLE kho.ma_hoa_luong_nguon (
        id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        owner_module text NOT NULL CHECK (owner_module IN ('M2','M5')),
        pool_id uuid NOT NULL,
        cau_noi_id uuid REFERENCES kho.hoa_don_dong_phien_ban(id),
        hoa_don_id uuid,
        hoa_don_phien_ban_id uuid,
        hoa_don_dong_id uuid,
        phieu_dong_phien_ban_id uuid REFERENCES kho.phieu_kho_dong_phien_ban(id),
        phieu_id uuid,
        phieu_phien_ban_id uuid,
        phieu_dong_id uuid,
        so_luong_nguon_text text NOT NULL,
        so_luong_nguon numeric(38,12) NOT NULL CHECK (so_luong_nguon > 0),
        don_vi_nguon_text text,
        don_vi_nguon_id uuid NOT NULL,
        don_vi_nguon_sha256 text NOT NULL,
        do_luong_sha256 text CHECK (do_luong_sha256 IS NULL OR do_luong_sha256 ~ '^[0-9a-f]{64}$'),
        don_vi_pool_id uuid NOT NULL,
        don_vi_pool_sha256 text NOT NULL,
        tu_so numeric(38,0) NOT NULL CHECK (tu_so > 0),
        mau_so numeric(38,0) NOT NULL CHECK (mau_so > 0),
        suc_chua numeric(38,12) NOT NULL CHECK (suc_chua > 0),
        can_cu text NOT NULL CHECK (can_cu IN ('SAME_VERIFIED_DEFINITION','APPROVED_NATIVE_ENCODING')),
        bang_chung_ma_hoa_id uuid,
        profile_ref text NOT NULL,
        profile_sha256 text NOT NULL,
        basis_revision integer NOT NULL CHECK (basis_revision >= 1),
        bien_nhan_id uuid NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (coalesce((owner_module = 'M2' AND cau_noi_id IS NOT NULL AND hoa_don_id IS NOT NULL AND hoa_don_phien_ban_id IS NOT NULL
                         AND hoa_don_dong_id IS NOT NULL AND phieu_dong_phien_ban_id IS NULL AND phieu_id IS NULL AND phieu_phien_ban_id IS NULL
                         AND phieu_dong_id IS NULL)
                        OR (owner_module = 'M5' AND phieu_dong_phien_ban_id IS NOT NULL AND phieu_id IS NOT NULL AND phieu_phien_ban_id IS NOT NULL
                            AND phieu_dong_id IS NOT NULL AND cau_noi_id IS NULL AND hoa_don_id IS NULL AND hoa_don_phien_ban_id IS NULL
                            AND hoa_don_dong_id IS NULL), false)),
        CHECK (suc_chua * mau_so = so_luong_nguon * tu_so),
        CHECK (coalesce((can_cu = 'APPROVED_NATIVE_ENCODING') = (bang_chung_ma_hoa_id IS NOT NULL), false)),
        CHECK (can_cu <> 'SAME_VERIFIED_DEFINITION' OR (tu_so = 1 AND mau_so = 1 AND don_vi_nguon_id = don_vi_pool_id)),
        CHECK (owner_module <> 'M5' OR do_luong_sha256 IS NOT NULL),
        FOREIGN KEY (don_vi_nguon_id, don_vi_nguon_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        FOREIGN KEY (phap_nhan_id, pool_id, owner_module) REFERENCES kho.dich_so_luong (phap_nhan_id, id, owner_module),
        FOREIGN KEY (phap_nhan_id, pool_id, don_vi_pool_id) REFERENCES kho.dich_so_luong (phap_nhan_id, id, don_vi_id),
        FOREIGN KEY (don_vi_pool_id, don_vi_pool_sha256) REFERENCES master.dinh_nghia_don_vi_luong (id, definition_sha256),
        FOREIGN KEY (phap_nhan_id, hoa_don_dong_id, hoa_don_id) REFERENCES kho.hoa_don_dong_danh_tinh (phap_nhan_id, id, hoa_don_id),
        FOREIGN KEY (phieu_dong_id, phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_dong_danh_tinh (id, phap_nhan_id, phieu_id),
        FOREIGN KEY (phap_nhan_id, bang_chung_ma_hoa_id) REFERENCES kho.bang_chung_quy_doi_luong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id),
        UNIQUE (phap_nhan_id, cau_noi_id, basis_revision),
        UNIQUE (phap_nhan_id, phieu_dong_phien_ban_id, basis_revision),
        UNIQUE (phap_nhan_id, id, pool_id))""",
    # ---- child số lượng HOA_DON_PHIEU_KHO: một biên nhận xác nhận = một child bất biến; bốn lượng dương exact; CHO/DA_KHOP/HUY × CO_HIEU_LUC/CAN_SOAT
    """CREATE TABLE kho.lien_ket_dong (
        id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        lien_ket_id uuid NOT NULL,
        loai text NOT NULL DEFAULT 'HOA_DON_PHIEU_KHO' CHECK (loai = 'HOA_DON_PHIEU_KHO'),
        xac_nhan_bien_nhan_id uuid NOT NULL,
        hoa_don_id uuid NOT NULL,
        hoa_don_phien_ban_id uuid NOT NULL,
        hoa_don_chung_tu_id uuid NOT NULL,
        cau_noi_id uuid NOT NULL REFERENCES kho.hoa_don_dong_phien_ban(id),
        hoa_don_chung_tu_dong_id uuid NOT NULL,
        hoa_don_dong_id uuid NOT NULL,
        ma_hoa_hoa_don_id uuid NOT NULL,
        pool_hoa_don_id uuid NOT NULL,
        don_vi_hoa_don_id uuid NOT NULL,
        phieu_id uuid NOT NULL,
        phieu_phien_ban_id uuid NOT NULL,
        phieu_chung_tu_id uuid NOT NULL,
        phieu_dong_phien_ban_id uuid NOT NULL REFERENCES kho.phieu_kho_dong_phien_ban(id),
        phieu_chung_tu_dong_id uuid NOT NULL,
        phieu_dong_id uuid NOT NULL,
        ma_hoa_phieu_id uuid NOT NULL,
        pool_phieu_id uuid NOT NULL,
        don_vi_phieu_id uuid NOT NULL,
        tuyen_id uuid NOT NULL REFERENCES kho.mua_dich_dong(id),
        bang_chung_hang_id uuid NOT NULL,
        bang_chung_ty_le_id uuid NOT NULL,
        so_luong_hoa_don_nguon numeric(38,12) NOT NULL CHECK (so_luong_hoa_don_nguon > 0),
        so_luong_phieu_nguon numeric(38,12) NOT NULL CHECK (so_luong_phieu_nguon > 0),
        so_luong_pool_hoa_don numeric(38,12) NOT NULL CHECK (so_luong_pool_hoa_don > 0),
        so_luong_pool_phieu numeric(38,12) NOT NULL CHECK (so_luong_pool_phieu > 0),
        trang_thai text NOT NULL CHECK (trang_thai IN ('CHO','DA_KHOP','HUY')),
        hieu_luc text NOT NULL CHECK (hieu_luc IN ('CO_HIEU_LUC','CAN_SOAT')),
        can_soat_ly_do text[] NOT NULL DEFAULT '{}',
        can_soat_luc timestamptz,
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) >= 1),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        huy_bien_nhan_id uuid,
        huy_boi text,
        huy_luc timestamptz,
        huy_ly_do text,
        CHECK (coalesce((hieu_luc = 'CAN_SOAT') = (cardinality(can_soat_ly_do) >= 1 AND can_soat_luc IS NOT NULL), false)),
        CHECK (coalesce((trang_thai = 'HUY') = (huy_bien_nhan_id IS NOT NULL AND huy_boi IS NOT NULL AND huy_luc IS NOT NULL AND huy_ly_do IS NOT NULL), false)),
        CHECK (pool_hoa_don_id <> pool_phieu_id),
        FOREIGN KEY (phap_nhan_id, lien_ket_id) REFERENCES kho.lien_ket_chung_tu (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, xac_nhan_bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, huy_bien_nhan_id) REFERENCES kho.bien_nhan_thao_tac (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, hoa_don_chung_tu_id) REFERENCES kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id, chung_tu_id),
        FOREIGN KEY (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, hoa_don_chung_tu_dong_id, hoa_don_dong_id)
            REFERENCES kho.hoa_don_dong_phien_ban (phap_nhan_id, hoa_don_id, hoa_don_phien_ban_id, source_dong_id, dong_danh_tinh_id),
        FOREIGN KEY (phap_nhan_id, phieu_id, phieu_phien_ban_id, phieu_chung_tu_id) REFERENCES kho.phieu_kho_phien_ban (phap_nhan_id, phieu_id, id, chung_tu_id),
        FOREIGN KEY (phieu_dong_id, phap_nhan_id, phieu_id) REFERENCES kho.phieu_kho_dong_danh_tinh (id, phap_nhan_id, phieu_id),
        FOREIGN KEY (phap_nhan_id, ma_hoa_hoa_don_id, pool_hoa_don_id) REFERENCES kho.ma_hoa_luong_nguon (phap_nhan_id, id, pool_id),
        FOREIGN KEY (phap_nhan_id, ma_hoa_phieu_id, pool_phieu_id) REFERENCES kho.ma_hoa_luong_nguon (phap_nhan_id, id, pool_id),
        FOREIGN KEY (phap_nhan_id, pool_hoa_don_id, don_vi_hoa_don_id) REFERENCES kho.dich_so_luong (phap_nhan_id, id, don_vi_id),
        FOREIGN KEY (phap_nhan_id, pool_phieu_id, don_vi_phieu_id) REFERENCES kho.dich_so_luong (phap_nhan_id, id, don_vi_id),
        FOREIGN KEY (phap_nhan_id, bang_chung_hang_id) REFERENCES kho.bang_chung_quy_doi_luong (phap_nhan_id, id),
        FOREIGN KEY (phap_nhan_id, bang_chung_ty_le_id) REFERENCES kho.bang_chung_quy_doi_luong (phap_nhan_id, id),
        UNIQUE (phap_nhan_id, xac_nhan_bien_nhan_id))""",
    "CREATE INDEX lien_ket_dong_pool_hd ON kho.lien_ket_dong (pool_hoa_don_id) WHERE trang_thai = 'DA_KHOP'",
    "CREATE INDEX lien_ket_dong_pool_pk ON kho.lien_ket_dong (pool_phieu_id) WHERE trang_thai = 'DA_KHOP'",
    # ---- guards: candidate/pool/mã hóa chỉ chủ bảng ghi thêm; bằng chứng: chỉ thu hồi một lần; child: chỉ CO_HIEU_LUC→CAN_SOAT và DA_KHOP→HUY
    """CREATE OR REPLACE FUNCTION kho.l11_chi_chu_ghi_them() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: % chỉ ghi thêm', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'L11_CHI_CHU: % chỉ do hàm định nghĩa của chủ bảng ghi', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bang_chung_ung_vien_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.bang_chung_ung_vien FOR EACH ROW EXECUTE FUNCTION kho.l11_chi_chu_ghi_them()",
    "CREATE TRIGGER dich_so_luong_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.dich_so_luong FOR EACH ROW EXECUTE FUNCTION kho.l11_chi_chu_ghi_them()",
    "CREATE TRIGGER ma_hoa_luong_nguon_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON kho.ma_hoa_luong_nguon FOR EACH ROW EXECUTE FUNCTION kho.l11_chi_chu_ghi_them()",
    """CREATE OR REPLACE FUNCTION kho.bang_chung_quy_doi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: không xóa bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'L11_CHI_CHU: bằng chứng chỉ do hàm xác nhận/thu hồi của chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'DA_XAC_NHAN' THEN
                    RAISE EXCEPTION 'L11_BAT_BIEN: bằng chứng mới phải ở DA_XAC_NHAN' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.ung_vien_id, NEW.reference_id, NEW.evidence_revision, NEW.kind, NEW.raw_sha256, NEW.byte_length,
                   NEW.payload_sha256, NEW.hang_hoa_bang_chung_id, NEW.hang_hoa_hoa_don, NEW.hang_hoa_kho, NEW.tu_don_vi_id, NEW.tu_don_vi_sha256,
                   NEW.den_don_vi_id, NEW.den_don_vi_sha256, NEW.don_vi_id, NEW.don_vi_sha256, NEW.tu_so, NEW.mau_so, NEW.native_xml_sha256,
                   NEW.quantity_locator, NEW.unit_locator, NEW.unit_lexeme, NEW.quantity_lexeme, NEW.rang_buoc, NEW.xac_nhan_boi, NEW.xac_nhan_luc,
                   NEW.xac_nhan_bien_nhan_id, NEW.mien, NEW.native_byte_length)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.ung_vien_id, OLD.reference_id, OLD.evidence_revision, OLD.kind, OLD.raw_sha256,
                   OLD.byte_length, OLD.payload_sha256, OLD.hang_hoa_bang_chung_id, OLD.hang_hoa_hoa_don, OLD.hang_hoa_kho, OLD.tu_don_vi_id,
                   OLD.tu_don_vi_sha256, OLD.den_don_vi_id, OLD.den_don_vi_sha256, OLD.don_vi_id, OLD.don_vi_sha256, OLD.tu_so, OLD.mau_so,
                   OLD.native_xml_sha256, OLD.quantity_locator, OLD.unit_locator, OLD.unit_lexeme, OLD.quantity_lexeme, OLD.rang_buoc, OLD.xac_nhan_boi,
                   OLD.xac_nhan_luc, OLD.xac_nhan_bien_nhan_id, OLD.mien, OLD.native_byte_length)
               OR NOT (OLD.trang_thai = 'DA_XAC_NHAN' AND NEW.trang_thai = 'DA_THU_HOI') THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: facts bằng chứng bất biến; chỉ thu hồi một lần có vết' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER bang_chung_quy_doi_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.bang_chung_quy_doi_luong FOR EACH ROW EXECUTE FUNCTION kho.bang_chung_quy_doi_kiem()",
    """CREATE OR REPLACE FUNCTION kho.lien_ket_dong_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE b record; lw record; eh record; ep record; ph record; pp record; xr record;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: không xóa child số lượng (undo = HUY có tombstone)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'L11_CHI_CHU: child số lượng chỉ do hàm xác nhận/undo/giữ soát của chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'DA_KHOP' OR NEW.hieu_luc <> 'CO_HIEU_LUC' THEN
                    RAISE EXCEPTION 'L11_CHILD_SAI: child mới phải DA_KHOP + CO_HIEU_LUC' USING ERRCODE = 'P0001';
                END IF;
                SELECT * INTO b FROM kho.hoa_don_dong_phien_ban x WHERE x.id = NEW.cau_noi_id;
                SELECT * INTO lw FROM kho.phieu_kho_dong_phien_ban x WHERE x.id = NEW.phieu_dong_phien_ban_id;
                SELECT * INTO eh FROM kho.ma_hoa_luong_nguon x WHERE x.id = NEW.ma_hoa_hoa_don_id;
                SELECT * INTO ep FROM kho.ma_hoa_luong_nguon x WHERE x.id = NEW.ma_hoa_phieu_id;
                SELECT * INTO ph FROM kho.dich_so_luong x WHERE x.id = NEW.pool_hoa_don_id;
                SELECT * INTO pp FROM kho.dich_so_luong x WHERE x.id = NEW.pool_phieu_id;
                SELECT * INTO xr FROM kho.bang_chung_quy_doi_luong x WHERE x.id = NEW.bang_chung_ty_le_id;
                -- R2: phương trình cross-native trên LƯỢNG NATIVE và định nghĩa đơn vị NATIVE (không trên pool); hai lượng pool dẫn xuất riêng
                IF xr.kind IS DISTINCT FROM 'CROSS_NATIVE_RATIO' OR xr.tu_don_vi_id IS DISTINCT FROM eh.don_vi_nguon_id
                   OR xr.den_don_vi_id IS DISTINCT FROM ep.don_vi_nguon_id
                   OR NEW.so_luong_hoa_don_nguon * xr.tu_so IS DISTINCT FROM NEW.so_luong_phieu_nguon * xr.mau_so THEN
                    RAISE EXCEPTION 'L11_CHILD_DO_THI: lượng native không thỏa tỷ lệ cross-native trên đơn vị native' USING ERRCODE = 'P0001';
                END IF;
                IF b.hoa_don_id IS DISTINCT FROM NEW.hoa_don_id OR b.hoa_don_phien_ban_id IS DISTINCT FROM NEW.hoa_don_phien_ban_id
                   OR b.source_dong_id IS DISTINCT FROM NEW.hoa_don_chung_tu_dong_id OR b.dong_danh_tinh_id IS DISTINCT FROM NEW.hoa_don_dong_id
                   OR lw.phieu_id IS DISTINCT FROM NEW.phieu_id OR lw.phien_ban_id IS DISTINCT FROM NEW.phieu_phien_ban_id
                   OR lw.chung_tu_dong_id IS DISTINCT FROM NEW.phieu_chung_tu_dong_id OR lw.dong_id IS DISTINCT FROM NEW.phieu_dong_id
                   OR eh.owner_module IS DISTINCT FROM 'M2' OR eh.cau_noi_id IS DISTINCT FROM NEW.cau_noi_id
                   OR ep.owner_module IS DISTINCT FROM 'M5' OR ep.phieu_dong_phien_ban_id IS DISTINCT FROM NEW.phieu_dong_phien_ban_id
                   OR ph.owner_module IS DISTINCT FROM 'M2' OR ph.hoa_don_dong_id IS DISTINCT FROM NEW.hoa_don_dong_id
                   OR pp.owner_module IS DISTINCT FROM 'M5' OR pp.phieu_dong_id IS DISTINCT FROM NEW.phieu_dong_id
                   OR NEW.so_luong_pool_hoa_don IS DISTINCT FROM kho.l11_quy_doi(NEW.so_luong_hoa_don_nguon, eh.tu_so, eh.mau_so)
                   OR NEW.so_luong_pool_phieu IS DISTINCT FROM kho.l11_quy_doi(NEW.so_luong_phieu_nguon, ep.tu_so, ep.mau_so)
                   OR NOT EXISTS (SELECT 1 FROM kho.lien_ket_chung_tu k WHERE k.id = NEW.lien_ket_id AND k.chu_so_huu_module = 'M5'
                                  AND k.hoa_don_id = NEW.hoa_don_id AND k.phieu_id = NEW.phieu_id AND k.chung_tu_a_id = NEW.hoa_don_chung_tu_id
                                  AND k.chung_tu_b_id = NEW.phieu_chung_tu_id) THEN
                    RAISE EXCEPTION 'L11_CHILD_DO_THI: child không khớp đồ thị typed cầu nối/dòng phiếu/mã hóa/pool/parent' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.lien_ket_id, NEW.loai, NEW.xac_nhan_bien_nhan_id, NEW.hoa_don_id, NEW.hoa_don_phien_ban_id,
                   NEW.hoa_don_chung_tu_id, NEW.cau_noi_id, NEW.hoa_don_chung_tu_dong_id, NEW.hoa_don_dong_id, NEW.ma_hoa_hoa_don_id, NEW.pool_hoa_don_id,
                   NEW.don_vi_hoa_don_id, NEW.phieu_id, NEW.phieu_phien_ban_id, NEW.phieu_chung_tu_id, NEW.phieu_dong_phien_ban_id, NEW.phieu_chung_tu_dong_id,
                   NEW.phieu_dong_id, NEW.ma_hoa_phieu_id, NEW.pool_phieu_id, NEW.don_vi_phieu_id, NEW.tuyen_id, NEW.bang_chung_hang_id,
                   NEW.bang_chung_ty_le_id, NEW.so_luong_hoa_don_nguon, NEW.so_luong_phieu_nguon, NEW.so_luong_pool_hoa_don, NEW.so_luong_pool_phieu,
                   NEW.ly_do, NEW.tao_boi, NEW.tao_boi_id, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.lien_ket_id, OLD.loai, OLD.xac_nhan_bien_nhan_id, OLD.hoa_don_id, OLD.hoa_don_phien_ban_id,
                   OLD.hoa_don_chung_tu_id, OLD.cau_noi_id, OLD.hoa_don_chung_tu_dong_id, OLD.hoa_don_dong_id, OLD.ma_hoa_hoa_don_id, OLD.pool_hoa_don_id,
                   OLD.don_vi_hoa_don_id, OLD.phieu_id, OLD.phieu_phien_ban_id, OLD.phieu_chung_tu_id, OLD.phieu_dong_phien_ban_id, OLD.phieu_chung_tu_dong_id,
                   OLD.phieu_dong_id, OLD.ma_hoa_phieu_id, OLD.pool_phieu_id, OLD.don_vi_phieu_id, OLD.tuyen_id, OLD.bang_chung_hang_id,
                   OLD.bang_chung_ty_le_id, OLD.so_luong_hoa_don_nguon, OLD.so_luong_phieu_nguon, OLD.so_luong_pool_hoa_don, OLD.so_luong_pool_phieu,
                   OLD.ly_do, OLD.tao_boi, OLD.tao_boi_id, OLD.tao_luc) THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: facts/lượng của child bất biến (không UPDATE lượng cũ)' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'HUY' THEN
                RAISE EXCEPTION 'L11_BAT_BIEN: child đã HUY là tombstone, không mở lại' USING ERRCODE = 'P0001';
            END IF;
            IF NOT ((OLD.trang_thai = 'DA_KHOP' AND NEW.trang_thai = 'DA_KHOP' AND NEW.hieu_luc = 'CAN_SOAT' AND NEW.can_soat_ly_do @> OLD.can_soat_ly_do
                     AND (OLD.hieu_luc = 'CO_HIEU_LUC' OR NEW.can_soat_luc = OLD.can_soat_luc)
                     AND (NEW.huy_bien_nhan_id, NEW.huy_boi, NEW.huy_luc, NEW.huy_ly_do) IS NOT DISTINCT FROM (OLD.huy_bien_nhan_id, OLD.huy_boi, OLD.huy_luc, OLD.huy_ly_do))
                    OR (OLD.trang_thai = 'DA_KHOP' AND NEW.trang_thai = 'HUY' AND NEW.hieu_luc = OLD.hieu_luc AND NEW.can_soat_ly_do = OLD.can_soat_ly_do
                        AND NEW.can_soat_luc IS NOT DISTINCT FROM OLD.can_soat_luc)) THEN
                RAISE EXCEPTION 'L11_CHUYEN_TRANG_THAI_SAI: chỉ CO_HIEU_LUC→CAN_SOAT (giữ lượng) hoặc DA_KHOP→HUY (undo)' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER lien_ket_dong_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.lien_ket_dong FOR EACH ROW EXECUTE FUNCTION kho.lien_ket_dong_kiem()",
) + M0016_L11_HAM + _L11_R1_THAY

# ---------------------------------------------------------------------------
# 0017 M4-01 (docs/GIAO-CODE-M4-01-CONG-HO-SO-VA-TAI-SU-DUNG.md): Cổng hồ sơ xây dựng — schema typed `m4` mới, append sau 13/14/15/16.
#   - Master HĐ duy nhất: hàng M4 là master.hop_dong loai XAY_DUNG + module_chu 'M4' (cột mới, NULL cho mọi hàng cũ → CRM/M9 giữ nguyên hành vi).
#     Hàng M4 chỉ do hàm định nghĩa M4 (chủ bảng) ghi; app/CRM không thấy/sửa hàng M4 ngoài phạm vi dự án (policy RESTRICTIVE mới, không sửa policy CRM).
#   - Phạm vi dự án: m4.quyen_du_an (chủ CSDL seed/thu hồi) + master.ktt_duoc(PN,'M4'); SOAN = vai PHU_TRACH + vai trò DU_AN; REVIEW xem hồ sơ đã nộp.
#   - Không ghi master.hop_dong_phien_ban/hop_dong_tham_so (authority duyệt CRM/CFO) và không ghi kho.chung_tu (discriminator core giữ nguyên;
#     chứng từ nghiệm thu/công nợ là gói M4-03). Tham số M4 do phòng dự án xác nhận ở bảng typed riêng, gắn tệp nguồn/lần trích/danh mục/revision.
#   - Mọi ghi qua hàm SECURITY DEFINER kiểm danh tính phiên + phạm vi + revision mong đợi + biên nhận idempotent; bảng bất biến chỉ ghi thêm.
# ---------------------------------------------------------------------------
_M4_DANH_MUC_THAM_SO = (  # 37 mã danh mục nguồn (trich_xuat/danh_muc.py MAC_DINH), không lấy DS_THAM_SO 36 mã của csdl_hop_dong (thiếu TC-09)
    ("TC-01", "Thông tin chung", "Số hợp đồng"), ("TC-02", "Thông tin chung", "Ngày ký"), ("TC-03", "Thông tin chung", "Gói thầu"),
    ("TC-04", "Thông tin chung", "Dự án"), ("TC-05", "Thông tin chung", "Địa điểm"), ("TC-06", "Thông tin chung", "Bên A (bên giao thầu / chủ đầu tư)"),
    ("TC-07", "Thông tin chung", "Bên B (bên nhận thầu / nhà thầu)"), ("TC-08", "Thông tin chung", "Hiệu lực hợp đồng"),
    ("TC-09", "Thông tin chung", "Loại hợp đồng theo phạm vi công việc"),
    ("TT-01", "Giá hợp đồng", "Loại hợp đồng"), ("TT-02", "Giá hợp đồng", "Giá trị hợp đồng (đồng)"),
    ("TT-03", "Giá hợp đồng", "Giá trị hợp đồng đã gồm VAT hay chưa"), ("TT-04", "Giá hợp đồng", "Thuế suất GTGT (%)"),
    ("TT-05", "Giá hợp đồng", "Cơ sở thanh toán khối lượng"),
    ("TT-10", "Tạm ứng", "Tỷ lệ tạm ứng (%)"), ("TT-11", "Tạm ứng", "Cách thu hồi tạm ứng"), ("TT-12", "Tạm ứng", "Bảo lãnh tạm ứng"),
    ("TT-20", "Thanh toán đợt", "Tỷ lệ thanh toán mỗi đợt (%)"), ("TT-21", "Thanh toán đợt", "Tỷ lệ giữ lại mỗi đợt (%)"),
    ("TT-22", "Thanh toán đợt", "Thời hạn thanh toán"),
    ("TT-30", "Quyết toán - bảo hành", "Tỷ lệ thanh toán khi quyết toán (%)"), ("TT-31", "Quyết toán - bảo hành", "Tỷ lệ bảo hành / bảo lãnh bảo hành (%)"),
    ("TT-32", "Quyết toán - bảo hành", "Thời hạn bảo hành"), ("TT-33", "Quyết toán - bảo hành", "Bảo lãnh thực hiện hợp đồng"),
    ("TT-40", "Điều chỉnh - phát sinh", "Điều kiện điều chỉnh đơn giá / giá hợp đồng"),
    ("TT-41", "Điều chỉnh - phát sinh", "Ngưỡng biến động để điều chỉnh giá (%)"),
    ("TT-42", "Điều chỉnh - phát sinh", "Cách xử lý khối lượng phát sinh, vượt hợp đồng"),
    ("TT-50", "Tiến độ - phạt", "Tiến độ / thời gian thực hiện hợp đồng"), ("TT-51", "Tiến độ - phạt", "Mức phạt vi phạm chất lượng"),
    ("TT-52", "Tiến độ - phạt", "Tạm giữ / phạt chậm tiến độ giai đoạn - mức 1"), ("TT-53", "Tiến độ - phạt", "Tạm giữ / phạt chậm tiến độ giai đoạn - mức 2"),
    ("TT-54", "Tiến độ - phạt", "Phạt chậm hoàn thành tổng tiến độ"), ("TT-55", "Tiến độ - phạt", "Trần tổng mức phạt"),
    ("TT-56", "Tiến độ - phạt", "Cách khấu trừ tiền phạt vào thanh toán"),
    ("TT-60", "Hồ sơ theo HĐ", "Hồ sơ thanh toán mỗi đợt"), ("TT-61", "Hồ sơ theo HĐ", "Hồ sơ quyết toán"),
    ("TT-62", "Hồ sơ theo HĐ", "Số bộ hồ sơ thanh toán phải nộp"),
)
# danh mục tài liệu nguồn (app_kiem_tra_ho_so/danh_muc_tai_lieu.csv): (mã, tên, bắt buộc đợt đầu, bắt buộc đợt sau, ghi chú phạm vi gói 1)
_M4_DANH_MUC_HO_SO = (
    ("A01", "Hợp đồng kèm điều kiện chung, điều kiện riêng", False, False, "Căn cứ cấp hợp đồng (tệp HĐ nguồn + xác nhận tham số)"),
    ("A02", "Bảng chi tiết giá trị hợp đồng (BOQ)", False, False, "Căn cứ cấp hợp đồng (BOQ đã đọc/map)"),
    ("A03", "Phụ lục hợp đồng", False, False, "Căn cứ cấp hợp đồng (khai báo phụ lục)"),
    ("A04", "Văn bản chấp thuận thay đổi, phát sinh", False, False, None), ("A05", "Hồ sơ dự thầu / báo giá, biên bản thương thảo", False, False, None),
    ("A06", "Bảo lãnh (tạm ứng, thực hiện hợp đồng, bảo hành)", False, False, None), ("A07", "Tiến độ thi công được duyệt", False, False, None),
    ("B01", "Bản vẽ thi công được duyệt", False, False, "Bản vẽ/CAD để gói sau (kế hoạch M4 §1) — chưa chặn nộp"),
    ("B02", "Bảng tính khối lượng thiết kế", False, False, None), ("B03", "Bản vẽ hoàn công", False, False, None),
    ("B04", "Hồ sơ thay đổi thiết kế, biên bản xử lý hiện trường", False, False, None),
    ("C01", "Biên bản nghiệm thu khối lượng hoàn thành đợt", True, True, None),
    ("C02", "Biên bản xác nhận khối lượng và giá trị hoàn thành đợt", True, True, None),
    ("C03", "Biên bản nghiệm thu công việc, vật liệu đầu vào", False, False, None), ("C04", "Nhật ký thi công", False, False, None),
    ("C05", "Kết quả thí nghiệm, biên bản lấy mẫu", False, False, None), ("C06", "Hình ảnh hiện trường có ngày chụp", False, False, None),
    ("D01", "Biên bản giao nhận vật tư, thiết bị", False, False, None), ("D02", "CO, CQ, packing list", False, False, None),
    ("D03", "Biên bản lắp đặt, chạy thử", False, False, None),
    ("E01", "Hồ sơ thanh toán đợt trước đã duyệt (bản ký + Excel)", False, True, "Chỉ bắt buộc từ đợt 2"),
    ("E02", "Ủy nhiệm chi / sổ phụ ngân hàng", False, True, "Chỉ bắt buộc từ đợt 2"),
    ("E03", "Hóa đơn GTGT", True, True, None), ("E04", "Công văn / giấy đề nghị thanh toán đợt này", True, True, None),
    ("E05", "File Excel hồ sơ thanh toán đợt này", True, True, None), ("E06", "Biên bản đối chiếu công nợ", False, False, None),
    ("F01", "Biên bản vi phạm chất lượng, tiến độ", False, False, None), ("F02", "Căn cứ thuế suất GTGT", False, False, None),
)


def _m4_sql_lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


_M4_MEDIA = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/pdf", "image/png", "image/jpeg")
_M4_MEDIA_SQL = "(" + ",".join(_m4_sql_lit(m) for m in _M4_MEDIA) + ")"
_M4_HEX = "~ '^[0-9a-f]{64}$'"
_M4_KIEM_SOAN = """
            IF NOT master.m4_duoc({d}, 'SOAN') THEN
                RAISE EXCEPTION 'M4_KHONG_CO_QUYEN_DU_AN: cần quyền soạn hồ sơ (phòng dự án phụ trách) đúng dự án' USING ERRCODE = 'P0001';
            END IF;"""
# khóa + kiểm revision mong đợi của hồ sơ HĐ (thứ tự khóa chung M4: hồ sơ HĐ → đợt)
_M4_KHOA_HO_SO = """
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = {hd} FOR UPDATE;
            IF h.hop_dong_id IS NULL THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hồ sơ hợp đồng M4' USING ERRCODE = 'P0001';
            END IF;""" + _M4_KIEM_SOAN.format(d="h.du_an_id") + """
            IF {rev} IS NULL OR h.revision <> {rev} THEN
                RAISE EXCEPTION 'M4_REVISION_CU: hồ sơ đã đổi (revision hiện tại %) — tải lại rồi thao tác', h.revision USING ERRCODE = 'P0001';
            END IF;"""
_M4_TANG = """
            UPDATE m4.ho_so_hop_dong SET revision = revision + 1{ts}, cap_nhat_luc = now() WHERE hop_dong_id = h.hop_dong_id
                RETURNING revision INTO moi;"""
_M4_NK = "INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet) VALUES ({d}, {hd}, {dot}, '{a}', ai, {ct});"

# M4-01B: bản M17 partial dưới đây CHƯA từng triển khai lên DEMO và KHÔNG còn nằm trong PG_MIGRATIONS (giữ nguyên văn để đối chiếu review).
# M17 hiện hành là `kho_tri_thuc.m4.sql_m17.M0017_M4` (sửa B1–B6: đường ghi nguồn tin cậy, biên nhận do lệnh chốt, BOQ tách lỗi chặn/phát hiện,
# thu hồi phạm vi chỉ ghi thêm, bỏ CHECK chr(0)).
_M0017_M4_PARTIAL_M4_01 = (
    "SET LOCAL check_function_bodies = off",
    "CREATE SCHEMA IF NOT EXISTS m4",
    # --- bảo vệ ghi: bảng M4 chỉ ghi qua hàm định nghĩa (chủ bảng); bảng bất biến chỉ ghi thêm
    """CREATE OR REPLACE FUNCTION m4.chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: % chỉ ghi qua hàm định nghĩa M4', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không xóa % (hủy/thay giữ lịch sử)', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.chi_ghi_them() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: % chỉ ghi thêm, không sửa/xóa', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: % chỉ ghi qua hàm định nghĩa M4', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- danh mục (dữ liệu hợp đồng kỹ thuật, bất biến)
    """CREATE TABLE m4.danh_muc_tham_so (
        ma text PRIMARY KEY CHECK (ma ~ '^(TC|TT)-[0-9]{2}$'),
        nhom text NOT NULL,
        ten text NOT NULL,
        thu_tu integer NOT NULL UNIQUE)""",
    "INSERT INTO m4.danh_muc_tham_so (ma, nhom, ten, thu_tu) VALUES "
    + ", ".join(f"({_m4_sql_lit(m)}, {_m4_sql_lit(n)}, {_m4_sql_lit(t)}, {i})" for i, (m, n, t) in enumerate(_M4_DANH_MUC_THAM_SO, 1)),
    "CREATE TRIGGER danh_muc_tham_so_bat_bien BEFORE UPDATE OR DELETE ON m4.danh_muc_tham_so FOR EACH ROW EXECUTE FUNCTION giao_tiep.chi_ghi_them()",
    """CREATE TABLE m4.danh_muc_ho_so_dot (
        ma text PRIMARY KEY CHECK (ma ~ '^[A-F][0-9]{2}$'),
        ten text NOT NULL,
        bat_buoc_dot_dau boolean NOT NULL,
        bat_buoc_dot_sau boolean NOT NULL,
        ghi_chu text)""",
    "INSERT INTO m4.danh_muc_ho_so_dot (ma, ten, bat_buoc_dot_dau, bat_buoc_dot_sau, ghi_chu) VALUES "
    + ", ".join("(" + ", ".join(_m4_sql_lit(x) for x in r) + ")" for r in _M4_DANH_MUC_HO_SO),
    "CREATE TRIGGER danh_muc_ho_so_dot_bat_bien BEFORE UPDATE OR DELETE ON m4.danh_muc_ho_so_dot FOR EACH ROW EXECUTE FUNCTION giao_tiep.chi_ghi_them()",
    # --- phạm vi dự án (chủ CSDL seed; thu hồi = DELETE bởi chủ; không sửa tại chỗ)
    """CREATE TABLE m4.quyen_du_an (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        vai text NOT NULL CHECK (vai IN ('PHU_TRACH','XEM','REVIEW')),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (nguoi_dung_id, du_an_id, vai))""",
    """CREATE OR REPLACE FUNCTION m4.quyen_du_an_khong_sua() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'M4_QUYEN_BAT_BIEN: phạm vi dự án chỉ thêm hoặc thu hồi (chủ CSDL), không sửa tại chỗ' USING ERRCODE = 'P0001';
        END $$""",
    "CREATE TRIGGER quyen_du_an_khong_sua BEFORE UPDATE ON m4.quyen_du_an FOR EACH ROW EXECUTE FUNCTION m4.quyen_du_an_khong_sua()",
    # quyền M4 của phiên: danh tính ID + login hoạt động, module M4 trên PN của dự án, vai dự án; SOAN cần vai trò DU_AN (không CFO/CRM)
    """CREATE OR REPLACE FUNCTION master.m4_duoc(p_du_an uuid, p_quyen text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND q.du_an_id = p_du_an AND master.ktt_duoc(q.phap_nhan_id, 'M4')
                         AND CASE p_quyen WHEN 'XEM' THEN q.vai IN ('PHU_TRACH','XEM')
                                          WHEN 'SOAN' THEN q.vai = 'PHU_TRACH' AND n.vai_tro = 'DU_AN'
                                          WHEN 'REVIEW' THEN q.vai = 'REVIEW'
                                          ELSE false END)
        $$""",
    # --- master HĐ: discriminator chủ sở hữu M4 (hàng cũ NULL → giữ CRM/M9 như trước)
    "ALTER TABLE master.hop_dong ADD COLUMN module_chu text",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_module_chu_m4 CHECK (module_chu IS NULL OR (module_chu = 'M4' AND loai = 'XAY_DUNG' AND du_an_id IS NOT NULL))",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_id_du_an_uq UNIQUE (id, du_an_id)",
    """CREATE OR REPLACE FUNCTION master.hop_dong_m4_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.module_chu IS DISTINCT FROM OLD.module_chu THEN
                RAISE EXCEPTION 'M4_CHU_SO_HUU_BAT_BIEN: không đổi module chủ sở hữu hợp đồng' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.module_chu = 'M4' AND NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_HOP_DONG_CHI_CHU: hợp đồng M4 chỉ do hàm định nghĩa M4 ghi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hop_dong_m4_chi_chu BEFORE INSERT OR UPDATE ON master.hop_dong FOR EACH ROW EXECUTE FUNCTION master.hop_dong_m4_chi_chu()",
    # RESTRICTIVE (AND với mọi policy hiện có, mọi vai trò): hàng M4 chỉ hiện với phạm vi dự án M4; hàng cũ (module_chu NULL) không đổi
    """CREATE POLICY hop_dong_m4_rang_buoc ON master.hop_dong AS RESTRICTIVE TO PUBLIC
        USING (module_chu IS DISTINCT FROM 'M4' OR master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'))
        WITH CHECK (module_chu IS DISTINCT FROM 'M4')""",
    # --- tệp nguồn (bytes content-addressed do máy chủ ghi m4-raw/<sha>; hàng bất biến, gắn PN/dự án/vai trò tài liệu/hash)
    f"""CREATE TABLE m4.tep (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        vai_tro_tai_lieu text NOT NULL CHECK (vai_tro_tai_lieu IN ('HOP_DONG','PHU_LUC','BOQ','HO_SO_DOT')),
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_M4_HEX}),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        media_type text NOT NULL CHECK (media_type IN {_M4_MEDIA_SQL}),
        ten_goc text NOT NULL CHECK (length(ten_goc) BETWEEN 1 AND 200 AND strpos(ten_goc, '/') = 0 AND strpos(ten_goc, chr(92)) = 0
                                     AND strpos(ten_goc, chr(0)) = 0 AND ten_goc NOT IN ('.', '..')),
        object_key text NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'm4-raw/' || raw_sha256),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (du_an_id, vai_tro_tai_lieu, raw_sha256),
        UNIQUE (id, du_an_id))""",
    """CREATE TABLE m4.ho_so_hop_dong (
        hop_dong_id uuid PRIMARY KEY,
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 300),
        revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
        rev_tham_so integer NOT NULL DEFAULT 1 CHECK (rev_tham_so >= 1),
        tep_hop_dong_id uuid,
        trang_thai_pl text NOT NULL DEFAULT 'CHUA_KHAI' CHECK (trang_thai_pl IN ('CHUA_KHAI','KHONG_CO','CO_CHUA_DU','CO_DU')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES master.hop_dong (id, du_an_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (tep_hop_dong_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        UNIQUE (hop_dong_id, du_an_id))""",
    f"""CREATE TABLE m4.trich_xuat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_M4_HEX}),
        catalog_sha256 text NOT NULL CHECK (catalog_sha256 {_M4_HEX}),
        engine text NOT NULL CHECK (length(engine) BETWEEN 1 AND 200),
        che_do text NOT NULL CHECK (che_do IN ('QUY_TAC_KHONG_AI','AI_LOCAL','AI_GIA_LAP_KHAI_BAO')),
        trang_thai text NOT NULL CHECK (trang_thai IN ('XONG','KHONG_HO_TRO','LOI')),
        ly_do text,
        phieu jsonb NOT NULL,
        ket_qua jsonb NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        CHECK (trang_thai = 'XONG' OR ly_do IS NOT NULL),
        UNIQUE (hop_dong_id, lan))""",
    """CREATE TABLE m4.tham_so (
        hop_dong_id uuid NOT NULL,
        ma text NOT NULL REFERENCES m4.danh_muc_tham_so(ma),
        du_an_id uuid NOT NULL,
        trang_thai text NOT NULL CHECK (trang_thai IN ('CHUA_CO','CO_GIA_TRI','KHONG_AP_DUNG','KHONG_QUY_DINH')),
        gia_tri text CHECK (length(gia_tri) <= 2000),
        don_vi text CHECK (length(don_vi) <= 50),
        dieu_khoan text CHECK (length(dieu_khoan) <= 300),
        trich_dan text CHECK (length(trich_dan) <= 4000),
        kiem_tra text,
        ly_do text CHECK (length(ly_do) <= 1000),
        vi_tri text,
        nguon text NOT NULL CHECK (nguon IN ('QUY_TAC','AI_LOCAL','AI_GIA_LAP_KHAI_BAO','CHUA_CO','SUA_TAY')),
        gia_tri_may text,
        trich_xuat_id uuid NOT NULL REFERENCES m4.trich_xuat(id),
        cap_nhat_boi text NOT NULL,
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (hop_dong_id, ma),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        CHECK (trang_thai <> 'CO_GIA_TRI' OR (coalesce(gia_tri, '') <> '' AND coalesce(trich_dan, '') <> '')),
        CHECK (trang_thai NOT IN ('KHONG_AP_DUNG','KHONG_QUY_DINH') OR (gia_tri IS NULL AND coalesce(ly_do, trich_dan, '') <> '')),
        CHECK (trang_thai <> 'CHUA_CO' OR gia_tri IS NULL))""",
    """CREATE TABLE m4.tham_so_lich_su (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        ma text NOT NULL,
        rev_tham_so integer NOT NULL,
        truoc jsonb,
        sau jsonb NOT NULL,
        ly_do text,
        boi text NOT NULL,
        luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id))""",
    f"""CREATE TABLE m4.xac_nhan_tham_so (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        rev_tham_so integer NOT NULL,
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_M4_HEX}),
        trich_xuat_id uuid NOT NULL REFERENCES m4.trich_xuat(id),
        catalog_sha256 text NOT NULL CHECK (catalog_sha256 {_M4_HEX}),
        tham_so_digest text NOT NULL CHECK (tham_so_digest {_M4_HEX}),
        ly_do text,
        xac_nhan_boi text NOT NULL,
        xac_nhan_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        xac_nhan_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        UNIQUE (hop_dong_id, rev_tham_so))""",
    """CREATE TABLE m4.phu_luc (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        so_pl text NOT NULL CHECK (length(so_pl) BETWEEN 1 AND 100),
        ngay_ky date NOT NULL,
        ngay_hieu_luc date NOT NULL,
        trang_thai text NOT NULL CHECK (trang_thai IN ('DA_KY','DU_THAO','DA_HUY')),
        doi_boq boolean NOT NULL,
        noi_dung text CHECK (length(noi_dung) <= 2000),
        tep_id uuid,
        huy_ly_do text,
        huy_boi text,
        huy_luc timestamptz,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        CHECK (ngay_hieu_luc >= ngay_ky),
        CHECK ((trang_thai = 'DA_HUY') = (huy_ly_do IS NOT NULL AND huy_boi IS NOT NULL AND huy_luc IS NOT NULL)),
        UNIQUE (id, hop_dong_id))""",
    "CREATE UNIQUE INDEX phu_luc_so_hieu_luc_uq ON m4.phu_luc (hop_dong_id, so_pl) WHERE trang_thai <> 'DA_HUY'",
    """CREATE TABLE m4.boq (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        phu_luc_id uuid,
        tep_id uuid NOT NULL,
        sheet text NOT NULL CHECK (length(sheet) BETWEEN 1 AND 100),
        hang_tieu_de integer NOT NULL CHECK (hang_tieu_de >= 1),
        cot jsonb NOT NULL,
        so_dong integer NOT NULL CHECK (so_dong >= 0),
        loi jsonb NOT NULL CHECK (jsonb_typeof(loi) = 'array'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DA_MAP','CO_LOI')),
        bo_doc text NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (phu_luc_id, hop_dong_id) REFERENCES m4.phu_luc (id, hop_dong_id),
        FOREIGN KEY (tep_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        CHECK ((trang_thai = 'DA_MAP') = (so_dong > 0 AND jsonb_array_length(loi) = 0)),
        UNIQUE (hop_dong_id, lan))""",
    """CREATE TABLE m4.boq_dong (
        boq_id uuid NOT NULL REFERENCES m4.boq(id),
        du_an_id uuid NOT NULL,
        dong integer NOT NULL CHECK (dong >= 1),
        ma_hm text NOT NULL CHECK (length(ma_hm) BETWEEN 1 AND 500),
        thao_tac text NOT NULL CHECK (thao_tac IN ('GOC','THEM','THAY')),
        stt text, nhom text, ten text NOT NULL, dvt text NOT NULL,
        kl text, don_gia text, thanh_tien text, ma_rieng text,
        PRIMARY KEY (boq_id, dong))""",
    """CREATE TABLE m4.dot (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        so_dot integer NOT NULL CHECK (so_dot BETWEEN 1 AND 999),
        ngay_nghiem_thu date,
        revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
        trang_thai text NOT NULL DEFAULT 'NHAP' CHECK (trang_thai IN ('NHAP','DA_NOP')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        UNIQUE (hop_dong_id, so_dot))""",
    """CREATE TABLE m4.dot_tep (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        dot_id uuid NOT NULL REFERENCES m4.dot(id),
        du_an_id uuid NOT NULL,
        tep_id uuid NOT NULL,
        muc text NOT NULL REFERENCES m4.danh_muc_ho_so_dot(ma),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (tep_id, du_an_id) REFERENCES m4.tep (id, du_an_id),
        UNIQUE (dot_id, tep_id, muc))""",
    f"""CREATE TABLE m4.nop (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        dot_id uuid NOT NULL UNIQUE REFERENCES m4.dot(id),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        revision_ho_so integer NOT NULL,
        revision_dot integer NOT NULL,
        snapshot jsonb NOT NULL,
        digest text NOT NULL CHECK (digest {_M4_HEX}),
        nop_boi text NOT NULL,
        nop_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        nop_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id))""",
    f"""CREATE TABLE m4.bien_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        du_an_id uuid NOT NULL,
        hanh_dong text NOT NULL CHECK (hanh_dong ~ '^[A-Z_]{{1,40}}$'),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        body_sha256 text NOT NULL CHECK (body_sha256 {_M4_HEX}),
        ket_qua jsonb,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (nguoi_dung_id, khoa))""",
    """CREATE TABLE m4.nhat_ky (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        du_an_id uuid NOT NULL,
        hop_dong_id uuid,
        dot_id uuid,
        hanh_dong text NOT NULL,
        boi text NOT NULL,
        luc timestamptz NOT NULL DEFAULT now(),
        chi_tiet jsonb)""",
    *(f"CREATE TRIGGER {t}_chi_chu BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_chu()"
      for t in ("ho_so_hop_dong", "tham_so", "phu_luc", "dot", "bien_nhan")),
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in ("tep", "trich_xuat", "tham_so_lich_su", "xac_nhan_tham_so", "boq", "boq_dong", "dot_tep", "nop", "nhat_ky")),
    # --- nội bộ: danh tính phiên (ID + login) và digest bộ tham số hiện hành
    """CREATE OR REPLACE FUNCTION m4.ai_id() RETURNS uuid
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE i uuid;
        BEGIN
            SELECT n.id INTO i FROM master.nguoi_dung n WHERE n.dang_nhap = master.ktt_danh_tinh()
                AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '');
            IF i IS NULL THEN
                RAISE EXCEPTION 'M4_DANH_TINH: chưa có danh tính phiên hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            RETURN i;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.digest_tham_so(p_hd uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT encode(sha256(convert_to(coalesce(string_agg(t.ma || chr(31) || t.trang_thai || chr(31) || coalesce(t.gia_tri, '') || chr(31)
                                                     || coalesce(t.don_vi, '') || chr(31) || coalesce(t.trich_dan, '') || chr(31) || coalesce(t.ly_do, '')
                                                     || chr(31) || t.trich_xuat_id::text, chr(30) ORDER BY t.ma), ''), 'UTF8')), 'hex')
        FROM m4.tham_so t WHERE t.hop_dong_id = p_hd
          AND EXISTS (SELECT 1 FROM m4.ho_so_hop_dong h WHERE h.hop_dong_id = p_hd
                      AND (master.m4_duoc(h.du_an_id, 'XEM') OR master.m4_duoc(h.du_an_id, 'REVIEW')))
        $$""",
    # tệp hồ sơ đợt có thuộc một đợt ĐÃ NỘP không (dùng trong RLS của người review; definer để không đệ quy RLS)
    """CREATE OR REPLACE FUNCTION m4.tep_da_nop(p_tep uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.dot_tep k JOIN m4.dot d ON d.id = k.dot_id WHERE k.tep_id = p_tep AND d.trang_thai = 'DA_NOP')
        $$""",
    # --- biên nhận idempotent: quyền kiểm TRƯỚC replay; cùng khóa + cùng thân → trả kết quả cũ; khác thân → từ chối
    """CREATE OR REPLACE FUNCTION m4.bat_dau(p_du_an uuid, p_hanh_dong text, p_khoa text, p_body_sha text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai uuid := m4.ai_id(); b record;
        BEGIN""" + _M4_KIEM_SOAN.format(d="p_du_an") + """
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || ai::text || ':' || coalesce(p_khoa, ''), 0));
            SELECT * INTO b FROM m4.bien_nhan WHERE nguoi_dung_id = ai AND khoa = p_khoa;
            IF b.id IS NOT NULL THEN
                IF (b.hanh_dong, b.body_sha256, b.du_an_id) IS DISTINCT FROM (p_hanh_dong, p_body_sha, p_du_an) THEN
                    RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho nội dung khác' USING ERRCODE = 'P0001';
                END IF;
                IF b.ket_qua IS NULL THEN
                    RAISE EXCEPTION 'M4_DANG_XU_LY: thao tác cùng khóa chưa hoàn tất' USING ERRCODE = 'P0001';
                END IF;
                RETURN jsonb_build_object('ket_qua', b.ket_qua);
            END IF;
            INSERT INTO m4.bien_nhan (nguoi_dung_id, du_an_id, hanh_dong, khoa, body_sha256) VALUES (ai, p_du_an, p_hanh_dong, p_khoa, p_body_sha);
            RETURN NULL;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.ket_thuc(p_khoa text, p_ket_qua jsonb) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai uuid := m4.ai_id();
        BEGIN
            UPDATE m4.bien_nhan SET ket_qua = p_ket_qua WHERE nguoi_dung_id = ai AND khoa = p_khoa AND ket_qua IS NULL;
            IF NOT FOUND OR p_ket_qua IS NULL THEN
                RAISE EXCEPTION 'M4_BIEN_NHAN_SAI: không có thao tác đang mở cho khóa này' USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    # --- hợp đồng: một master duy nhất; số HĐ đã có (module nào cũng vậy) → từ chối, không tạo song song
    """CREATE OR REPLACE FUNCTION m4.tao_hop_dong(p_du_an uuid, p_so_hd text, p_ten text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; hd uuid; cu record;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KIEM_SOAN.format(d="p_du_an") + """
            IF p_so_hd IS NULL OR p_so_hd !~ '^[^[:cntrl:]]{1,100}$' OR btrim(p_so_hd) <> p_so_hd OR p_ten IS NULL OR length(p_ten) NOT BETWEEN 1 AND 300 THEN
                RAISE EXCEPTION 'M4_HOP_DONG_SAI: số hợp đồng (1–100 ký tự, không khoảng trắng đầu/cuối) và tên là bắt buộc' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:hop_dong:' || d.phap_nhan_id::text || ':' || p_so_hd, 0));
            SELECT h.id, h.module_chu, h.du_an_id INTO cu FROM master.hop_dong h WHERE h.phap_nhan_id = d.phap_nhan_id AND h.loai = 'XAY_DUNG' AND h.so_hop_dong = p_so_hd;
            IF cu.id IS NOT NULL THEN
                IF cu.module_chu = 'M4' AND cu.du_an_id = p_du_an THEN
                    RAISE EXCEPTION 'M4_HOP_DONG_DA_CO: hợp đồng % đã có trong dự án — dùng lại hồ sơ hiện có cho đợt sau', p_so_hd USING ERRCODE = 'P0001';
                END IF;
                RAISE EXCEPTION 'M4_HOP_DONG_DA_CO_NOI_KHAC: số hợp đồng đã có ở dự án/module khác của pháp nhân — không tạo master song song' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, du_an_id, module_chu)
                VALUES (d.phap_nhan_id, 'XAY_DUNG', 'M4:' || d.ma_junsky || ':' || p_so_hd, p_so_hd, p_du_an, 'M4') RETURNING id INTO hd;
            INSERT INTO m4.ho_so_hop_dong (hop_dong_id, phap_nhan_id, du_an_id, ten, tao_boi) VALUES (hd, d.phap_nhan_id, p_du_an, p_ten, ai);
            """ + _M4_NK.format(d="p_du_an", hd="hd", dot="NULL", a="TAO_HOP_DONG", ct="jsonb_build_object('so_hop_dong', p_so_hd)") + """
            RETURN hd;
        END $$""",
    f"""CREATE OR REPLACE FUNCTION m4.ghi_tep(p_du_an uuid, p_vai text, p_sha text, p_len bigint, p_media text, p_ten text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d record; t uuid;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KIEM_SOAN.format(d="p_du_an") + """
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            INSERT INTO m4.tep (phap_nhan_id, du_an_id, vai_tro_tai_lieu, raw_sha256, byte_length, media_type, ten_goc, object_key, tao_boi)
                VALUES (d.phap_nhan_id, p_du_an, p_vai, p_sha, p_len, p_media, p_ten, 'm4-raw/' || p_sha, ai)
                ON CONFLICT (du_an_id, vai_tro_tai_lieu, raw_sha256) DO NOTHING RETURNING id INTO t;
            IF t IS NULL THEN
                SELECT id INTO t FROM m4.tep WHERE du_an_id = p_du_an AND vai_tro_tai_lieu = p_vai AND raw_sha256 = p_sha;
                IF (SELECT byte_length FROM m4.tep WHERE id = t) <> p_len THEN
                    RAISE EXCEPTION 'M4_TEP_XUNG_DOT: cùng hash nhưng độ dài khác' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                """ + _M4_NK.format(d="p_du_an", hd="NULL", dot="NULL", a="TAI_TEP", ct="jsonb_build_object('tep_id', t, 'vai', p_vai, 'sha', p_sha)") + """
            END IF;
            RETURN t;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.gan_tep_hop_dong(p_hd uuid, p_rev integer, p_tep uuid) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; t record; moi integer;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            SELECT * INTO t FROM m4.tep WHERE id = p_tep AND du_an_id = h.du_an_id;
            IF t.id IS NULL OR t.vai_tro_tai_lieu <> 'HOP_DONG' THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp hợp đồng đã tải lên đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            IF h.tep_hop_dong_id = p_tep THEN
                RAISE EXCEPTION 'M4_KHONG_DOI: tệp hợp đồng này đang là căn cứ hiện hành' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.ho_so_hop_dong SET tep_hop_dong_id = p_tep WHERE hop_dong_id = h.hop_dong_id;""" + _M4_TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="GAN_TEP_HOP_DONG",
                                ct="jsonb_build_object('tep_cu', h.tep_hop_dong_id, 'tep_moi', p_tep, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    # --- kết quả trích từ lõi nguồn (máy chủ chạy TrichXuat); đúng tệp hiện hành + đúng hash; đủ 37 mã danh mục, mỗi mã một lần
    """CREATE OR REPLACE FUNCTION m4.ghi_trich_xuat(p_hd uuid, p_rev integer, p_tep uuid, p_catalog text, p_engine text, p_che_do text,
                                                     p_trang_thai text, p_ly_do text, p_phieu jsonb, p_ket_qua jsonb) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; t record; moi integer; tx uuid; n integer; r record; cu jsonb;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            IF h.tep_hop_dong_id IS DISTINCT FROM p_tep THEN
                RAISE EXCEPTION 'M4_TRICH_KHAC_TEP: chỉ trích đúng tệp hợp đồng hiện hành' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            INSERT INTO m4.trich_xuat (hop_dong_id, du_an_id, lan, tep_id, raw_sha256, catalog_sha256, engine, che_do, trang_thai, ly_do, phieu, ket_qua, tao_boi)
                VALUES (h.hop_dong_id, h.du_an_id, coalesce((SELECT max(lan) FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id), 0) + 1, p_tep, t.raw_sha256,
                        p_catalog, p_engine, p_che_do, p_trang_thai, p_ly_do, p_phieu, p_ket_qua, ai) RETURNING id INTO tx;
            IF p_trang_thai = 'XONG' THEN
                IF jsonb_typeof(p_ket_qua) <> 'array' THEN
                    RAISE EXCEPTION 'M4_KET_QUA_TRICH_SAI: kết quả trích phải là danh sách' USING ERRCODE = 'P0001';
                END IF;
                SELECT count(*) INTO n FROM jsonb_array_elements(p_ket_qua) e JOIN m4.danh_muc_tham_so c ON c.ma = e->>'ma';
                IF n <> (SELECT count(*) FROM m4.danh_muc_tham_so) OR jsonb_array_length(p_ket_qua) <> n
                   OR (SELECT count(DISTINCT e->>'ma') FROM jsonb_array_elements(p_ket_qua) e) <> n THEN
                    RAISE EXCEPTION 'M4_KET_QUA_TRICH_SAI: kết quả trích phải có đủ mỗi mã danh mục đúng một lần' USING ERRCODE = 'P0001';
                END IF;
                FOR r IN SELECT * FROM jsonb_to_recordset(p_ket_qua) AS x(ma text, trang_thai text, gia_tri text, don_vi text, dieu_khoan text,
                                                                          trich_dan text, kiem_tra text, ly_do text, vi_tri text, nguon text) LOOP
                    SELECT to_jsonb(s) INTO cu FROM m4.tham_so s WHERE s.hop_dong_id = h.hop_dong_id AND s.ma = r.ma;
                    INSERT INTO m4.tham_so (hop_dong_id, ma, du_an_id, trang_thai, gia_tri, don_vi, dieu_khoan, trich_dan, kiem_tra, ly_do, vi_tri, nguon,
                                            gia_tri_may, trich_xuat_id, cap_nhat_boi)
                        VALUES (h.hop_dong_id, r.ma, h.du_an_id, r.trang_thai, r.gia_tri, r.don_vi, r.dieu_khoan, r.trich_dan, r.kiem_tra, r.ly_do, r.vi_tri,
                                r.nguon, r.gia_tri, tx, ai)
                        ON CONFLICT (hop_dong_id, ma) DO UPDATE SET trang_thai = EXCLUDED.trang_thai, gia_tri = EXCLUDED.gia_tri, don_vi = EXCLUDED.don_vi,
                            dieu_khoan = EXCLUDED.dieu_khoan, trich_dan = EXCLUDED.trich_dan, kiem_tra = EXCLUDED.kiem_tra, ly_do = EXCLUDED.ly_do,
                            vi_tri = EXCLUDED.vi_tri, nguon = EXCLUDED.nguon, gia_tri_may = EXCLUDED.gia_tri_may, trich_xuat_id = EXCLUDED.trich_xuat_id,
                            cap_nhat_boi = EXCLUDED.cap_nhat_boi, cap_nhat_luc = now();
                    INSERT INTO m4.tham_so_lich_su (hop_dong_id, du_an_id, ma, rev_tham_so, truoc, sau, ly_do, boi)
                        VALUES (h.hop_dong_id, h.du_an_id, r.ma, h.rev_tham_so + 1, cu, to_jsonb(r), 'TRICH_XUAT ' || tx::text, ai);
                END LOOP;""" + _M4_TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            ELSE""" + _M4_TANG.format(ts="") + """
            END IF;
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="TRICH_XUAT",
                                ct="jsonb_build_object('trich_xuat_id', tx, 'trang_thai', p_trang_thai, 'che_do', p_che_do, 'revision', moi)") + """
            RETURN tx;
        END $$""",
    # --- phòng dự án soát/sửa: giá trị + trích dẫn (máy chủ đã đối chiếu nguyên văn tệp nguồn) hoặc không áp dụng/không quy định có lý do
    """CREATE OR REPLACE FUNCTION m4.sua_tham_so(p_hd uuid, p_rev integer, p_ma text, p_trang_thai text, p_gia_tri text, p_don_vi text,
                                                  p_dieu_khoan text, p_trich_dan text, p_kiem_tra text, p_ly_do text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; s record; moi integer;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            SELECT * INTO s FROM m4.tham_so WHERE hop_dong_id = h.hop_dong_id AND ma = p_ma;
            IF s.ma IS NULL THEN
                RAISE EXCEPTION 'M4_CHUA_TRICH: chưa có bộ tham số từ lần trích — chạy trích trước' USING ERRCODE = 'P0001';
            END IF;
            IF p_trang_thai NOT IN ('CO_GIA_TRI','KHONG_AP_DUNG','KHONG_QUY_DINH') THEN
                RAISE EXCEPTION 'M4_TRANG_THAI_THAM_SO_SAI: chỉ Có giá trị / Không áp dụng / Không quy định' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.tham_so SET trang_thai = p_trang_thai, gia_tri = CASE WHEN p_trang_thai = 'CO_GIA_TRI' THEN p_gia_tri END, don_vi = p_don_vi,
                                  dieu_khoan = p_dieu_khoan, trich_dan = p_trich_dan, kiem_tra = p_kiem_tra, ly_do = p_ly_do, nguon = 'SUA_TAY',
                                  cap_nhat_boi = ai, cap_nhat_luc = now()
                WHERE hop_dong_id = h.hop_dong_id AND ma = p_ma;
            INSERT INTO m4.tham_so_lich_su (hop_dong_id, du_an_id, ma, rev_tham_so, truoc, sau, ly_do, boi)
                SELECT h.hop_dong_id, h.du_an_id, p_ma, h.rev_tham_so + 1, to_jsonb(s), to_jsonb(x), p_ly_do, ai FROM m4.tham_so x
                WHERE x.hop_dong_id = h.hop_dong_id AND x.ma = p_ma;""" + _M4_TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="SUA_THAM_SO", ct="jsonb_build_object('ma', p_ma, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    # --- xác nhận bộ tham số (DU_AN, không CFO): gắn tệp/hash/lần trích/danh mục/revision + digest; sửa sau đó làm xác nhận hết hiệu lực
    """CREATE OR REPLACE FUNCTION m4.xac_nhan_tham_so(p_hd uuid, p_rev integer, p_catalog text, p_ly_do text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; t record; x uuid; con text; n integer;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            IF h.tep_hop_dong_id IS NULL THEN
                RAISE EXCEPTION 'M4_THIEU_HOP_DONG: chưa có tệp hợp đồng nguồn' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO t FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id ORDER BY lan DESC LIMIT 1;
            IF t.id IS NULL OR t.tep_id <> h.tep_hop_dong_id OR t.trang_thai <> 'XONG' THEN
                RAISE EXCEPTION 'M4_CHUA_TRICH_DUNG_NGUON: lần trích mới nhất phải xong và đúng tệp hợp đồng hiện hành' USING ERRCODE = 'P0001';
            END IF;
            IF t.catalog_sha256 <> p_catalog THEN
                RAISE EXCEPTION 'M4_DANH_MUC_DOI: danh mục tham số khác lần trích — trích lại' USING ERRCODE = 'P0001';
            END IF;
            SELECT count(*) INTO n FROM m4.tham_so s WHERE s.hop_dong_id = h.hop_dong_id AND s.trich_xuat_id = t.id;
            IF n <> (SELECT count(*) FROM m4.danh_muc_tham_so) THEN
                RAISE EXCEPTION 'M4_THAM_SO_KHONG_DU_DANH_MUC: bộ tham số không khớp lần trích hiện hành' USING ERRCODE = 'P0001';
            END IF;
            SELECT string_agg(ma, ', ' ORDER BY ma) INTO con FROM m4.tham_so WHERE hop_dong_id = h.hop_dong_id AND trang_thai = 'CHUA_CO';
            IF con IS NOT NULL THEN
                RAISE EXCEPTION 'M4_THAM_SO_CON_TRONG: còn tham số chưa có giá trị/lý do: %', con USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM m4.xac_nhan_tham_so WHERE hop_dong_id = h.hop_dong_id AND rev_tham_so = h.rev_tham_so) THEN
                RAISE EXCEPTION 'M4_DA_XAC_NHAN: bộ tham số revision này đã được xác nhận' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO m4.xac_nhan_tham_so (hop_dong_id, du_an_id, rev_tham_so, tep_id, raw_sha256, trich_xuat_id, catalog_sha256, tham_so_digest, ly_do,
                                             xac_nhan_boi, xac_nhan_boi_id)
                VALUES (h.hop_dong_id, h.du_an_id, h.rev_tham_so, h.tep_hop_dong_id, t.raw_sha256, t.id, t.catalog_sha256, m4.digest_tham_so(h.hop_dong_id),
                        p_ly_do, ai, m4.ai_id()) RETURNING id INTO x;
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="XAC_NHAN_THAM_SO",
                                ct="jsonb_build_object('xac_nhan_id', x, 'rev_tham_so', h.rev_tham_so)") + """
            RETURN x;
        END $$""",
    # --- phụ lục: khai báo không có / có chưa đủ / có đủ; phụ lục giữ nguồn/ngày hiệu lực; hủy giữ lịch sử
    """CREATE OR REPLACE FUNCTION m4.khai_phu_luc(p_hd uuid, p_rev integer, p_khai text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; moi integer;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            IF p_khai NOT IN ('KHONG_CO','CO_CHUA_DU','CO_DU') THEN
                RAISE EXCEPTION 'M4_KHAI_PHU_LUC_SAI: chỉ Không có / Có nhưng chưa đủ / Có và đã cung cấp đủ' USING ERRCODE = 'P0001';
            END IF;
            IF p_khai = 'KHONG_CO' AND EXISTS (SELECT 1 FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai <> 'DA_HUY') THEN
                RAISE EXCEPTION 'M4_KHAI_PHU_LUC_MAU_THUAN: đang có phụ lục chưa hủy — không khai Không có' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.ho_so_hop_dong SET trang_thai_pl = p_khai WHERE hop_dong_id = h.hop_dong_id;""" + _M4_TANG.format(ts="") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="KHAI_PHU_LUC", ct="jsonb_build_object('khai', p_khai, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.them_phu_luc(p_hd uuid, p_rev integer, p_so_pl text, p_ngay_ky date, p_ngay_hl date, p_trang_thai text,
                                                   p_doi_boq boolean, p_noi_dung text, p_tep uuid) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; moi integer; pl uuid;
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            IF p_trang_thai NOT IN ('DA_KY','DU_THAO') OR p_doi_boq IS NULL THEN
                RAISE EXCEPTION 'M4_PHU_LUC_SAI: phụ lục mới là Đã ký hoặc Dự thảo, có khai đổi BOQ' USING ERRCODE = 'P0001';
            END IF;
            IF h.trang_thai_pl = 'KHONG_CO' THEN
                RAISE EXCEPTION 'M4_KHAI_PHU_LUC_MAU_THUAN: hồ sơ đang khai Không có phụ lục — đổi khai báo trước' USING ERRCODE = 'P0001';
            END IF;
            IF p_tep IS NOT NULL AND NOT EXISTS (SELECT 1 FROM m4.tep WHERE id = p_tep AND du_an_id = h.du_an_id AND vai_tro_tai_lieu = 'PHU_LUC') THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp phụ lục đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND so_pl = p_so_pl AND trang_thai <> 'DA_HUY') THEN
                RAISE EXCEPTION 'M4_PHU_LUC_DA_CO: số phụ lục đã có (hủy bản cũ trước nếu cần thay)' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO m4.phu_luc (hop_dong_id, du_an_id, so_pl, ngay_ky, ngay_hieu_luc, trang_thai, doi_boq, noi_dung, tep_id, tao_boi)
                VALUES (h.hop_dong_id, h.du_an_id, p_so_pl, p_ngay_ky, p_ngay_hl, p_trang_thai, p_doi_boq, p_noi_dung, p_tep, ai) RETURNING id INTO pl;""" + _M4_TANG.format(ts="") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="THEM_PHU_LUC", ct="jsonb_build_object('phu_luc_id', pl, 'revision', moi)") + """
            RETURN pl;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.huy_phu_luc(p_pl uuid, p_rev integer, p_ly_do text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; p record; moi integer;
        BEGIN
            PERFORM m4.ai_id();
            SELECT * INTO p FROM m4.phu_luc WHERE id = p_pl;
            IF p.id IS NULL THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_PHU_LUC' USING ERRCODE = 'P0001';
            END IF;""" + _M4_KHOA_HO_SO.format(hd="p.hop_dong_id", rev="p_rev") + """
            IF p.trang_thai = 'DA_HUY' OR coalesce(btrim(p_ly_do), '') = '' THEN
                RAISE EXCEPTION 'M4_HUY_PHU_LUC_SAI: phụ lục đã hủy hoặc thiếu lý do' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.phu_luc SET trang_thai = 'DA_HUY', huy_ly_do = p_ly_do, huy_boi = ai, huy_luc = now() WHERE id = p_pl;""" + _M4_TANG.format(ts="") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="HUY_PHU_LUC", ct="jsonb_build_object('phu_luc_id', p_pl, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    # --- BOQ: kết quả parser nguồn (máy chủ đọc tệp thật); gắn đúng HĐ (gốc) hoặc phụ lục; lỗi đọc/map giữ lại, không coi là đủ
    """CREATE OR REPLACE FUNCTION m4.ghi_boq(p_hd uuid, p_rev integer, p_tep uuid, p_pl uuid, p_sheet text, p_hang integer, p_cot jsonb, p_bo_doc text,
                                              p_dong jsonb, p_loi jsonb) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; moi integer; b uuid; n integer; goc text[];
        BEGIN
            PERFORM m4.ai_id();""" + _M4_KHOA_HO_SO.format(hd="p_hd", rev="p_rev") + """
            IF NOT EXISTS (SELECT 1 FROM m4.tep WHERE id = p_tep AND du_an_id = h.du_an_id AND vai_tro_tai_lieu = 'BOQ') THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp BOQ (.xlsx) đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            IF p_pl IS NOT NULL AND NOT EXISTS (SELECT 1 FROM m4.phu_luc WHERE id = p_pl AND hop_dong_id = h.hop_dong_id AND trang_thai <> 'DA_HUY' AND doi_boq) THEN
                RAISE EXCEPTION 'M4_PHU_LUC_KHONG_DOI_BOQ: BOQ phụ lục chỉ gắn phụ lục còn hiệu lực có khai đổi BOQ' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_typeof(p_dong) <> 'array' OR jsonb_typeof(p_loi) <> 'array' THEN
                RAISE EXCEPTION 'M4_BOQ_SAI: dòng/lỗi BOQ phải là danh sách' USING ERRCODE = 'P0001';
            END IF;
            n := jsonb_array_length(p_dong);
            INSERT INTO m4.boq (hop_dong_id, du_an_id, lan, phu_luc_id, tep_id, sheet, hang_tieu_de, cot, so_dong, loi, trang_thai, bo_doc, tao_boi)
                VALUES (h.hop_dong_id, h.du_an_id, coalesce((SELECT max(lan) FROM m4.boq WHERE hop_dong_id = h.hop_dong_id), 0) + 1, p_pl, p_tep, p_sheet,
                        p_hang, p_cot, n, p_loi, CASE WHEN n > 0 AND jsonb_array_length(p_loi) = 0 THEN 'DA_MAP' ELSE 'CO_LOI' END, p_bo_doc, ai)
                RETURNING id INTO b;
            IF p_pl IS NOT NULL THEN  -- thao tác PL so với BOQ gốc hiện hành: có mã → THAY, chưa có → THEM
                SELECT array_agg(d.ma_hm) INTO goc FROM m4.boq_dong d WHERE d.boq_id = (SELECT x.id FROM m4.boq x WHERE x.hop_dong_id = h.hop_dong_id
                                                                                       AND x.phu_luc_id IS NULL ORDER BY x.lan DESC LIMIT 1);
            END IF;
            INSERT INTO m4.boq_dong (boq_id, du_an_id, dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng)
                SELECT b, h.du_an_id, x.dong, x.ma_hm, CASE WHEN p_pl IS NULL THEN 'GOC' WHEN x.ma_hm = ANY (coalesce(goc, '{}')) THEN 'THAY' ELSE 'THEM' END,
                       x.stt, x.nhom, x.ten, x.dvt, x.kl, x.don_gia, x.thanh_tien, x.ma_rieng
                FROM jsonb_to_recordset(p_dong) AS x(dong integer, ma_hm text, stt text, nhom text, ten text, dvt text, kl text, don_gia text,
                                                     thanh_tien text, ma_rieng text);""" + _M4_TANG.format(ts="") + """
            """ + _M4_NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="NHAP_BOQ", ct="jsonb_build_object('boq_id', b, 'so_dong', n, 'revision', moi)") + """
            RETURN b;
        END $$""",
    # --- đợt thanh toán: dùng lại HĐ/căn cứ đã có; tệp theo checklist; khóa hồ sơ HĐ → đợt
    """CREATE OR REPLACE FUNCTION m4.tao_dot(p_hd uuid, p_so_dot integer, p_ngay date) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); h record; d uuid;
        BEGIN
            PERFORM m4.ai_id();
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd FOR UPDATE;
            IF h.hop_dong_id IS NULL THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hồ sơ hợp đồng M4' USING ERRCODE = 'P0001';
            END IF;""" + _M4_KIEM_SOAN.format(d="h.du_an_id") + """
            IF EXISTS (SELECT 1 FROM m4.dot WHERE hop_dong_id = p_hd AND so_dot = p_so_dot) THEN
                RAISE EXCEPTION 'M4_DOT_DA_CO: đợt % đã có trên hợp đồng này', p_so_dot USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO m4.dot (hop_dong_id, du_an_id, so_dot, ngay_nghiem_thu, tao_boi) VALUES (p_hd, h.du_an_id, p_so_dot, p_ngay, ai) RETURNING id INTO d;
            """ + _M4_NK.format(d="h.du_an_id", hd="p_hd", dot="d", a="TAO_DOT", ct="jsonb_build_object('so_dot', p_so_dot)") + """
            RETURN d;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.khoa_dot(p_dot uuid, p_rev integer) RETURNS m4.dot
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d m4.dot; h record;
        BEGIN
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            IF d.id IS NULL THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_DOT: không thấy đợt' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id FOR UPDATE;
            SELECT * INTO d FROM m4.dot WHERE id = p_dot FOR UPDATE;""" + _M4_KIEM_SOAN.format(d="d.du_an_id") + """
            IF d.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'M4_DOT_DA_NOP: đợt đã nộp chính thức — không sửa (bổ sung là gói sau)' USING ERRCODE = 'P0001';
            END IF;
            IF p_rev IS NULL OR d.revision <> p_rev THEN
                RAISE EXCEPTION 'M4_REVISION_CU: đợt đã đổi (revision hiện tại %) — tải lại', d.revision USING ERRCODE = 'P0001';
            END IF;
            RETURN d;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.sua_dot(p_dot uuid, p_rev integer, p_ngay date) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d m4.dot; moi integer;
        BEGIN
            PERFORM m4.ai_id();
            d := m4.khoa_dot(p_dot, p_rev);
            UPDATE m4.dot SET ngay_nghiem_thu = p_ngay, revision = revision + 1, cap_nhat_luc = now() WHERE id = p_dot RETURNING revision INTO moi;
            """ + _M4_NK.format(d="d.du_an_id", hd="d.hop_dong_id", dot="p_dot", a="SUA_DOT", ct="jsonb_build_object('ngay_nghiem_thu', p_ngay, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.gan_tep_dot(p_dot uuid, p_rev integer, p_tep uuid, p_muc text) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d m4.dot; moi integer;
        BEGIN
            PERFORM m4.ai_id();
            d := m4.khoa_dot(p_dot, p_rev);
            IF NOT EXISTS (SELECT 1 FROM m4.tep WHERE id = p_tep AND du_an_id = d.du_an_id AND vai_tro_tai_lieu = 'HO_SO_DOT') THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp hồ sơ đợt đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM m4.danh_muc_ho_so_dot WHERE ma = p_muc) THEN
                RAISE EXCEPTION 'M4_MUC_HO_SO_SAI: mục hồ sơ không có trong danh mục' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM m4.dot_tep WHERE dot_id = p_dot AND tep_id = p_tep AND muc = p_muc) THEN
                RAISE EXCEPTION 'M4_KHONG_DOI: tệp đã gắn đúng mục này' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO m4.dot_tep (dot_id, du_an_id, tep_id, muc, tao_boi) VALUES (p_dot, d.du_an_id, p_tep, p_muc, ai);
            UPDATE m4.dot SET revision = revision + 1, cap_nhat_luc = now() WHERE id = p_dot RETURNING revision INTO moi;
            """ + _M4_NK.format(d="d.du_an_id", hd="d.hop_dong_id", dot="p_dot", a="GAN_TEP_DOT", ct="jsonb_build_object('tep_id', p_tep, 'muc', p_muc, 'revision', moi)") + """
            RETURN moi;
        END $$""",
    # --- preflight backend: mọi căn cứ bắt buộc; thiếu mục nào nêu đúng mục đó (không biến thiếu thành 0, không cờ của trình duyệt)
    """CREATE OR REPLACE FUNCTION m4.thieu(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d record; h record; t record; x record; b record; p record; c record; ra jsonb := '[]'::jsonb;
        BEGIN
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            IF d.id IS NULL OR NOT (master.m4_duoc(d.du_an_id, 'XEM') OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')) THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_DOT: không thấy đợt' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id;
            IF h.tep_hop_dong_id IS NULL THEN
                ra := ra || jsonb_build_object('ma', 'HD_CHUA_CO_TEP', 'nhom', 'HOP_DONG', 'noi_dung', 'Chưa tải tệp hợp đồng nguồn');
            ELSE
                SELECT * INTO t FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id ORDER BY lan DESC LIMIT 1;
                IF t.id IS NULL THEN
                    ra := ra || jsonb_build_object('ma', 'HD_CHUA_TRICH', 'nhom', 'HOP_DONG', 'noi_dung', 'Chưa chạy trích tham số từ tệp hợp đồng hiện hành');
                ELSIF t.tep_id <> h.tep_hop_dong_id THEN
                    ra := ra || jsonb_build_object('ma', 'HD_TRICH_KHAC_TEP', 'nhom', 'HOP_DONG', 'noi_dung', 'Lần trích gần nhất thuộc tệp hợp đồng cũ — trích lại');
                ELSIF t.trang_thai <> 'XONG' THEN
                    ra := ra || jsonb_build_object('ma', 'HD_TRICH_CHUA_XONG', 'nhom', 'HOP_DONG', 'noi_dung', coalesce(t.ly_do, 'Lần trích chưa xong'));
                ELSE
                    SELECT * INTO x FROM m4.xac_nhan_tham_so WHERE hop_dong_id = h.hop_dong_id ORDER BY rev_tham_so DESC LIMIT 1;
                    IF x.id IS NULL THEN
                        ra := ra || jsonb_build_object('ma', 'HD_CHUA_XAC_NHAN', 'nhom', 'HOP_DONG', 'noi_dung', 'Phòng dự án chưa soát/xác nhận bộ tham số');
                    ELSIF x.rev_tham_so <> h.rev_tham_so OR x.trich_xuat_id <> t.id OR x.tham_so_digest <> m4.digest_tham_so(h.hop_dong_id) THEN
                        ra := ra || jsonb_build_object('ma', 'HD_XAC_NHAN_HET_HIEU_LUC', 'nhom', 'HOP_DONG',
                                                       'noi_dung', 'Tham số/căn cứ đã đổi sau lần xác nhận — xác nhận lại');
                    END IF;
                END IF;
            END IF;
            IF h.trang_thai_pl = 'CHUA_KHAI' THEN
                ra := ra || jsonb_build_object('ma', 'PL_CHUA_KHAI', 'nhom', 'PHU_LUC', 'noi_dung', 'Chưa khai báo tình trạng phụ lục');
            ELSIF h.trang_thai_pl = 'CO_CHUA_DU' THEN
                ra := ra || jsonb_build_object('ma', 'PL_CHUA_DU', 'nhom', 'PHU_LUC', 'noi_dung', 'Đã khai có phụ lục nhưng chưa cung cấp đủ');
            ELSIF h.trang_thai_pl = 'CO_DU' THEN
                IF NOT EXISTS (SELECT 1 FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai = 'DA_KY') THEN
                    ra := ra || jsonb_build_object('ma', 'PL_CHUA_NHAP', 'nhom', 'PHU_LUC', 'noi_dung', 'Khai có phụ lục nhưng chưa nhập phụ lục đã ký nào');
                END IF;
                FOR p IN SELECT * FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai = 'DA_KY' AND tep_id IS NULL ORDER BY so_pl LOOP
                    ra := ra || jsonb_build_object('ma', 'PL_THIEU_TEP', 'nhom', 'PHU_LUC', 'noi_dung', 'Phụ lục ' || p.so_pl || ' chưa có tệp nguồn',
                                                   'phu_luc_id', p.id);
                END LOOP;
            END IF;
            SELECT * INTO b FROM m4.boq WHERE hop_dong_id = h.hop_dong_id AND phu_luc_id IS NULL ORDER BY lan DESC LIMIT 1;
            IF b.id IS NULL THEN
                ra := ra || jsonb_build_object('ma', 'BOQ_CHUA_NHAP', 'nhom', 'BOQ', 'noi_dung', 'Chưa nhập BOQ hợp đồng (đọc + map cột)');
            ELSIF b.trang_thai <> 'DA_MAP' THEN
                ra := ra || jsonb_build_object('ma', 'BOQ_CO_LOI', 'nhom', 'BOQ', 'noi_dung', 'BOQ lần nhập gần nhất còn lỗi đọc/map', 'boq_id', b.id);
            END IF;
            FOR p IN SELECT * FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai = 'DA_KY' AND doi_boq
                       AND (d.ngay_nghiem_thu IS NULL OR ngay_hieu_luc <= d.ngay_nghiem_thu) ORDER BY ngay_hieu_luc, so_pl LOOP
                SELECT * INTO b FROM m4.boq WHERE phu_luc_id = p.id ORDER BY lan DESC LIMIT 1;
                IF b.id IS NULL OR b.trang_thai <> 'DA_MAP' THEN
                    ra := ra || jsonb_build_object('ma', 'BOQ_PL_CHUA_DU', 'nhom', 'BOQ', 'noi_dung', 'Phụ lục ' || p.so_pl || ' đổi BOQ nhưng chưa nhập BOQ hợp lệ',
                                                   'phu_luc_id', p.id);
                END IF;
            END LOOP;
            IF d.ngay_nghiem_thu IS NULL THEN
                ra := ra || jsonb_build_object('ma', 'DOT_CHUA_NGAY', 'nhom', 'DOT', 'noi_dung', 'Chưa nhập ngày nghiệm thu của đợt');
            END IF;
            FOR c IN SELECT * FROM m4.danh_muc_ho_so_dot k WHERE (d.so_dot = 1 AND k.bat_buoc_dot_dau) OR (d.so_dot > 1 AND k.bat_buoc_dot_sau) ORDER BY k.ma LOOP
                IF NOT EXISTS (SELECT 1 FROM m4.dot_tep WHERE dot_id = d.id AND muc = c.ma) THEN
                    ra := ra || jsonb_build_object('ma', 'DOT_THIEU_TAI_LIEU', 'nhom', 'DOT', 'muc', c.ma, 'noi_dung', 'Thiếu ' || c.ma || ' — ' || c.ten);
                END IF;
            END LOOP;
            RETURN ra;
        END $$""",
    # --- nộp chính thức: kiểm lại toàn bộ căn cứ dưới khóa (HĐ → đợt) + revision mong đợi; snapshot/digest do CSDL dựng; một lần mỗi đợt
    """CREATE OR REPLACE FUNCTION m4.nop(p_dot uuid, p_rev_hd integer, p_rev_dot integer) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); d m4.dot; h record; t record; x record; con jsonb; s jsonb; n uuid;
        BEGIN
            PERFORM m4.ai_id();
            d := m4.khoa_dot(p_dot, p_rev_dot);
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id;
            IF p_rev_hd IS NULL OR h.revision <> p_rev_hd THEN
                RAISE EXCEPTION 'M4_REVISION_CU: hồ sơ hợp đồng đã đổi (revision hiện tại %) — kiểm lại trước khi nộp', h.revision USING ERRCODE = 'P0001';
            END IF;
            con := m4.thieu(p_dot);
            IF jsonb_array_length(con) > 0 THEN
                RAISE EXCEPTION 'M4_CHUA_DU_CAN_CU: còn % mục thiếu — xem danh sách cần bổ sung', jsonb_array_length(con) USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO t FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id ORDER BY lan DESC LIMIT 1;
            SELECT * INTO x FROM m4.xac_nhan_tham_so WHERE hop_dong_id = h.hop_dong_id ORDER BY rev_tham_so DESC LIMIT 1;
            s := jsonb_build_object(
                'hop_dong_id', h.hop_dong_id, 'revision_ho_so', h.revision, 'rev_tham_so', h.rev_tham_so,
                'tep_hop_dong', (SELECT jsonb_build_object('id', id, 'raw_sha256', raw_sha256, 'ten', ten_goc) FROM m4.tep WHERE id = h.tep_hop_dong_id),
                'trich_xuat_id', t.id, 'xac_nhan_id', x.id, 'tham_so_digest', x.tham_so_digest, 'khai_phu_luc', h.trang_thai_pl,
                'phu_luc', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', p.id, 'so_pl', p.so_pl, 'ngay_hieu_luc', p.ngay_hieu_luc, 'doi_boq', p.doi_boq,
                                                                   'ap_dung', p.ngay_hieu_luc <= d.ngay_nghiem_thu, 'tep_id', p.tep_id)
                                                ORDER BY p.ngay_hieu_luc, p.so_pl), '[]'::jsonb)
                            FROM m4.phu_luc p WHERE p.hop_dong_id = h.hop_dong_id AND p.trang_thai = 'DA_KY'),
                'boq', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'phu_luc_id', q.phu_luc_id, 'so_dong', q.so_dong) ORDER BY q.lan), '[]'::jsonb)
                        FROM m4.boq q WHERE q.hop_dong_id = h.hop_dong_id AND q.trang_thai = 'DA_MAP'
                          AND q.lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = q.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM q.phu_luc_id)),
                'dot', jsonb_build_object('id', d.id, 'so_dot', d.so_dot, 'ngay_nghiem_thu', d.ngay_nghiem_thu, 'revision', d.revision),
                'tai_lieu', (SELECT coalesce(jsonb_agg(jsonb_build_object('muc', k.muc, 'tep_id', k.tep_id, 'raw_sha256', f.raw_sha256)
                                                       ORDER BY k.muc, f.raw_sha256), '[]'::jsonb)
                             FROM m4.dot_tep k JOIN m4.tep f ON f.id = k.tep_id WHERE k.dot_id = d.id));
            INSERT INTO m4.nop (dot_id, hop_dong_id, du_an_id, revision_ho_so, revision_dot, snapshot, digest, nop_boi, nop_boi_id)
                VALUES (d.id, h.hop_dong_id, h.du_an_id, h.revision, d.revision, s, encode(sha256(convert_to(s::text, 'UTF8')), 'hex'), ai, m4.ai_id())
                RETURNING id INTO n;
            UPDATE m4.dot SET trang_thai = 'DA_NOP', cap_nhat_luc = now() WHERE id = d.id;
            """ + _M4_NK.format(d="d.du_an_id", hd="h.hop_dong_id", dot="d.id", a="NOP", ct="jsonb_build_object('nop_id', n)") + """
            RETURN n;
        END $$""",
    # --- quyền: app_web chỉ SELECT qua RLS phạm vi dự án; ghi chỉ qua hàm định nghĩa; hàm nội bộ không cấp
    "REVOKE EXECUTE ON FUNCTION m4.ai_id(), m4.khoa_dot(uuid, integer), m4.tep_da_nop(uuid) FROM PUBLIC",
    """REVOKE EXECUTE ON FUNCTION m4.digest_tham_so(uuid), m4.bat_dau(uuid, text, text, text), m4.ket_thuc(text, jsonb), m4.tao_hop_dong(uuid, text, text),
        m4.ghi_tep(uuid, text, text, bigint, text, text), m4.gan_tep_hop_dong(uuid, integer, uuid),
        m4.ghi_trich_xuat(uuid, integer, uuid, text, text, text, text, text, jsonb, jsonb),
        m4.sua_tham_so(uuid, integer, text, text, text, text, text, text, text, text), m4.xac_nhan_tham_so(uuid, integer, text, text),
        m4.khai_phu_luc(uuid, integer, text), m4.them_phu_luc(uuid, integer, text, date, date, text, boolean, text, uuid),
        m4.huy_phu_luc(uuid, integer, text), m4.ghi_boq(uuid, integer, uuid, uuid, text, integer, jsonb, text, jsonb, jsonb),
        m4.tao_dot(uuid, integer, date), m4.sua_dot(uuid, integer, date), m4.gan_tep_dot(uuid, integer, uuid, text), m4.thieu(uuid),
        m4.nop(uuid, integer, integer) FROM PUBLIC""",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in ("danh_muc_tham_so", "danh_muc_ho_so_dot", "quyen_du_an", "tep", "ho_so_hop_dong", "trich_xuat",
                                                                "tham_so", "tham_so_lich_su", "xac_nhan_tham_so", "phu_luc", "boq", "boq_dong", "dot",
                                                                "dot_tep", "nop", "bien_nhan", "nhat_ky")),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT USAGE ON SCHEMA m4 TO app_web;
            GRANT SELECT ON m4.danh_muc_tham_so, m4.danh_muc_ho_so_dot, m4.quyen_du_an, m4.tep, m4.ho_so_hop_dong, m4.trich_xuat, m4.tham_so,
                m4.tham_so_lich_su, m4.xac_nhan_tham_so, m4.phu_luc, m4.boq, m4.boq_dong, m4.dot, m4.dot_tep, m4.nop, m4.bien_nhan, m4.nhat_ky TO app_web;
            CREATE POLICY danh_muc_tham_so_web ON m4.danh_muc_tham_so FOR SELECT TO app_web USING (true);
            CREATE POLICY danh_muc_ho_so_dot_web ON m4.danh_muc_ho_so_dot FOR SELECT TO app_web USING (true);
            CREATE POLICY quyen_du_an_web ON m4.quyen_du_an FOR SELECT TO app_web
                USING (master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), ''));
            CREATE POLICY bien_nhan_web ON m4.bien_nhan FOR SELECT TO app_web
                USING (master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), ''));
            CREATE POLICY ho_so_hop_dong_web ON m4.ho_so_hop_dong FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY trich_xuat_web ON m4.trich_xuat FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY tham_so_web ON m4.tham_so FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY tham_so_lich_su_web ON m4.tham_so_lich_su FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY xac_nhan_tham_so_web ON m4.xac_nhan_tham_so FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY phu_luc_web ON m4.phu_luc FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY boq_web ON m4.boq FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY boq_dong_web ON m4.boq_dong FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY nop_web ON m4.nop FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'));
            CREATE POLICY nhat_ky_web ON m4.nhat_ky FOR SELECT TO app_web USING (master.m4_duoc(du_an_id, 'XEM'));
            -- người review chỉ thấy đợt/tệp hồ sơ đợt đã NỘP; phòng dự án thấy cả nháp trong phạm vi dự án
            CREATE POLICY dot_web ON m4.dot FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM') OR (master.m4_duoc(du_an_id, 'REVIEW') AND trang_thai = 'DA_NOP'));
            CREATE POLICY dot_tep_web ON m4.dot_tep FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM')
                       OR (master.m4_duoc(du_an_id, 'REVIEW') AND EXISTS (SELECT 1 FROM m4.dot d WHERE d.id = dot_id AND d.trang_thai = 'DA_NOP')));
            CREATE POLICY tep_web ON m4.tep FOR SELECT TO app_web
                USING (master.m4_duoc(du_an_id, 'XEM')
                       OR (master.m4_duoc(du_an_id, 'REVIEW') AND (vai_tro_tai_lieu <> 'HO_SO_DOT' OR m4.tep_da_nop(id))));
            CREATE POLICY hop_dong_m4_du_an ON master.hop_dong FOR SELECT TO app_web
                USING (module_chu = 'M4' AND (master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW')));
            GRANT EXECUTE ON FUNCTION m4.digest_tham_so(uuid), m4.bat_dau(uuid, text, text, text), m4.ket_thuc(text, jsonb), m4.tao_hop_dong(uuid, text, text),
                m4.ghi_tep(uuid, text, text, bigint, text, text), m4.gan_tep_hop_dong(uuid, integer, uuid),
                m4.ghi_trich_xuat(uuid, integer, uuid, text, text, text, text, text, jsonb, jsonb),
                m4.sua_tham_so(uuid, integer, text, text, text, text, text, text, text, text), m4.xac_nhan_tham_so(uuid, integer, text, text),
                m4.khai_phu_luc(uuid, integer, text), m4.them_phu_luc(uuid, integer, text, date, date, text, boolean, text, uuid),
                m4.huy_phu_luc(uuid, integer, text), m4.ghi_boq(uuid, integer, uuid, uuid, text, integer, jsonb, text, jsonb, jsonb),
                m4.tao_dot(uuid, integer, date), m4.sua_dot(uuid, integer, date), m4.gan_tep_dot(uuid, integer, uuid, text), m4.thieu(uuid),
                m4.nop(uuid, integer, integer), m4.tep_da_nop(uuid) TO app_web;
        END IF;
    END $$""",
)

from ..m4.sql_m17 import M0017_M4  # noqa: E402 — M17 M4-01B (module chỉ hằng SQL, không import ha_tang)

PG_MIGRATIONS: tuple[tuple[str, ...], ...] = (M0001, M0002, M0003, M0004, M0005, M0006, M0007, M0008, M0009, M0010, M0011, M0012, M0013_COMMON, M0014_M5,
                                               M0015_M2_BRIDGE, M0016_L11_QUANTITY, M0017_M4)


def _hash(statements) -> str:
    import hashlib
    return hashlib.sha256("\n".join(statements).encode()).hexdigest()


# Tiền thân được chấp nhận của migration chưa phát hành đã bị thay (chỉ các hash liệt kê chính xác; ghi vào master.migration_tuong_thich).
PG_MIGRATION_TUONG_THICH: dict[int, dict[str, str]] = {
    10: {_hash(M0010_V1_BAN_GIAO_DAU): "M0010 bản bàn giao đầu 19/10/2026 (chưa nghiệm thu) — khác bản hiện hành đúng một CHECK lien_ket_huy_co_vet; "
                                       "M0011 thay CHECK đó bằng bản phân biệt link HUY lịch sử trước v10."},
}
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0018 — CRM-41-02 (APPEND sau đúng 17 migration hiện hành; không sửa định nghĩa/checksum 1–17): G1 mẫu DOCX có phiên bản + ánh xạ +
#        KT kiểm/trả lại + CFO+V4 duyệt hiệu lực; G7 bộ chuẩn dự án tối thiểu (4 cột); action assignment chung; biên nhận chủ bảng;
#        guard K5 typed (OLD-or-NEW) + đọc K5 typed theo quyền hiện hành ở mọi trạng thái. Mọi lệnh ghi là hàm INVOKER chỉ chạy được trên
#        kết nối CHỦ BẢNG của máy chủ (master.la_chu_bang) với danh tính phiên (GUC); app_web/vai cũ không có quyền trên bảng mới.
# ---------------------------------------------------------------------------
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
_G_TOKEN_MAU = """
            IF p_token IS NULL OR master.crm_g_mau_token(v.id) <> p_token THEN
                RAISE EXCEPTION 'CRM_G_TOKEN_CU: phiên bản mẫu đã đổi — tải lại rồi thao tác' """ + _G_LOI + """;
            END IF;"""
_G_TOKEN_CHUAN = """
            IF p_token IS NULL OR master.crm_g_chuan_token(v.id) <> p_token THEN
                RAISE EXCEPTION 'CRM_G_TOKEN_CU: bộ chuẩn đã đổi — tải lại rồi thao tác' """ + _G_LOI + """;
            END IF;"""
_G_NK = "INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do) VALUES ({pn}, ai, {loai}, {bang}, {id}, {hd}, {sau}, {ly});"
_G_KHAI = "ai text := master.ktt_danh_tinh(); aid uuid := master.crm_g_ai_id(); d record; cu jsonb; kq jsonb;"
_G_BANG_MOI = ("crm_danh_muc_truong", "phan_cong_hanh_dong", "crm_mau", "crm_mau_tep", "crm_mau_phien_ban", "crm_mau_anh_xa", "crm_mau_kiem_tra",
               "crm_bo_chuan", "crm_bo_chuan_phien_ban", "crm_bo_chuan_dong", "crm_g_bien_nhan")
_G_TYPED = "('master.crm_mau_phien_ban','master.crm_bo_chuan_phien_ban')"

M0018_CRM_G = (
    "SET LOCAL check_function_bodies = off",
    # --- bảo vệ ghi: chỉ chủ bảng; bảng bất biến chỉ ghi thêm; bảng có vòng đời chỉ sửa qua hàm lệnh (không DELETE)
    """CREATE OR REPLACE FUNCTION master.crm_g_bat_bien() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: % chỉ ghi qua hàm lệnh trên kết nối chủ bảng', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: % chỉ ghi thêm, không sửa/xóa', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_chi_chu() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: % chỉ ghi qua hàm lệnh trên kết nối chủ bảng', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa % (giữ lịch sử)', TG_TABLE_NAME USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    # --- danh mục trường (một catalog có version theo loại hình; dữ liệu khai báo bởi chủ CSDL, bất biến)
    """CREATE TABLE master.crm_danh_muc_truong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        loai_hinh_id uuid NOT NULL,
        danh_muc_ref text NOT NULL CHECK (danh_muc_ref ~ '^[A-Z0-9_]{1,80}$'),
        revision integer NOT NULL CHECK (revision >= 1),
        khoa text NOT NULL CHECK (khoa ~ '^[a-z][a-z0-9_]{0,79}$'),
        nhan text NOT NULL CHECK (length(nhan) BETWEEN 1 AND 300),
        nhom text NOT NULL CHECK (nhom ~ '^[A-Z0-9_]{1,40}$'),
        kieu text NOT NULL CHECK (kieu IN ('text','so','ngay','tien','bang')),
        dinh_dang text NOT NULL CHECK (length(dinh_dang) BETWEEN 1 AND 80),
        nguon text NOT NULL CHECK (nguon ~ '^[A-Z0-9_]{1,40}$'),
        pii boolean NOT NULL,
        bat_buoc boolean NOT NULL,
        xem_thu jsonb NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (danh_muc_ref, revision, loai_hinh_id, khoa))""",
    "CREATE TRIGGER crm_danh_muc_truong_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_danh_muc_truong FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- action assignment chung (không thêm vai_tro): chỉ thêm hoặc ghi dấu thu hồi MỘT lần; cấp lại = hàng mới
    """CREATE TABLE master.phan_cong_hanh_dong (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        module text NOT NULL CHECK (module ~ '^[A-Z0-9]{1,10}$'),
        hanh_dong text NOT NULL CHECK (hanh_dong ~ '^[A-Z0-9_]{1,60}$'),
        loai_hinh_id uuid,
        cap_boi text NOT NULL,
        cap_luc timestamptz NOT NULL DEFAULT now(),
        thu_hoi_luc timestamptz,
        thu_hoi_boi text,
        thu_hoi_ly_do text,
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL) AND (thu_hoi_luc IS NULL) = (thu_hoi_ly_do IS NULL)))""",
    """CREATE UNIQUE INDEX phan_cong_hanh_dong_hien_hanh_uq ON master.phan_cong_hanh_dong (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id)
        NULLS NOT DISTINCT WHERE thu_hoi_luc IS NULL""",
    """CREATE OR REPLACE FUNCTION master.phan_cong_hanh_dong_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_PHAN_CONG_CHI_QUAN_TRI: phân công hành động chỉ do quản trị (chủ CSDL) ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_PHAN_CONG_BAT_BIEN: thu hồi bằng dấu thu hồi, không xóa' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.thu_hoi_luc IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_G_PHAN_CONG_BAT_BIEN: không chèn phân công đã thu hồi' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.thu_hoi_luc IS NOT NULL OR NEW.thu_hoi_luc IS NULL OR coalesce(btrim(NEW.thu_hoi_ly_do), '') = ''
               OR ROW(NEW.id, NEW.nguoi_dung_id, NEW.phap_nhan_id, NEW.module, NEW.hanh_dong, NEW.loai_hinh_id, NEW.cap_boi, NEW.cap_luc)
                  IS DISTINCT FROM ROW(OLD.id, OLD.nguoi_dung_id, OLD.phap_nhan_id, OLD.module, OLD.hanh_dong, OLD.loai_hinh_id, OLD.cap_boi, OLD.cap_luc) THEN
                RAISE EXCEPTION 'CRM_G_PHAN_CONG_BAT_BIEN: chỉ ghi dấu thu hồi một lần, không sửa phân công' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER phan_cong_hanh_dong_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.phan_cong_hanh_dong FOR EACH ROW EXECUTE FUNCTION master.phan_cong_hanh_dong_kiem()",
    # hành động được phân công của PHIÊN: danh tính ID+login hoạt động, module hiện hành trên PN, phân công chưa thu hồi (phạm vi loại hình tùy chọn)
    """CREATE OR REPLACE FUNCTION master.ktt_hanh_dong_duoc(pn uuid, p_module text, p_hanh_dong text, p_loai uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.ktt_duoc(pn, p_module) AND EXISTS (
            SELECT 1 FROM master.phan_cong_hanh_dong a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
            WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
              AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
              AND a.thu_hoi_luc IS NULL AND a.phap_nhan_id = pn AND a.module = p_module AND a.hanh_dong = p_hanh_dong
              AND (a.loai_hinh_id IS NULL OR a.loai_hinh_id IS NOT DISTINCT FROM p_loai))
        $$""",
    # --- G1: gốc mẫu, tệp DOCX + facts phát hiện (máy chủ), phiên bản có vòng đời, ánh xạ có revision, lần KT kiểm
    """CREATE TABLE master.crm_mau (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        ma_mau text NOT NULL CHECK (ma_mau ~ '^[A-Za-z0-9_.-]{1,80}$'),
        loai_hinh_id uuid NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (phap_nhan_id, ma_mau),
        UNIQUE (id, phap_nhan_id, loai_hinh_id))""",
    "CREATE TRIGGER crm_mau_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_mau FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_mau_tep (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        object_key text NOT NULL,
        bo_doc text NOT NULL CHECK (length(bo_doc) BETWEEN 1 AND 80),
        facts jsonb NOT NULL CHECK (jsonb_typeof(facts) = 'object'),
        facts_sha256 text NOT NULL CHECK (facts_sha256 ~ '^[0-9a-f]{64}$'),
        trang_thai_doc text NOT NULL CHECK (trang_thai_doc IN ('DU','INCOMPLETE')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'crm-mau/' || raw_sha256),
        UNIQUE (phap_nhan_id, raw_sha256, bo_doc),
        UNIQUE (id, phap_nhan_id))""",
    "CREATE TRIGGER crm_mau_tep_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_mau_tep FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_mau_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        mau_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        loai_hinh_id uuid NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        tep_id uuid NOT NULL,
        ten_tep text NOT NULL CHECK (length(ten_tep) BETWEEN 1 AND 200 AND strpos(ten_tep, '/') = 0 AND strpos(ten_tep, chr(92)) = 0
                                     AND ten_tep !~ '[[:cntrl:]]'),
        danh_muc_ref text NOT NULL,
        danh_muc_rev integer NOT NULL,
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ '^[0-9a-f]{64}$'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DRAFT','CHO_KIEM','CHO_CFO','HIEU_LUC','TU_CHOI')),
        anh_xa_hien_hanh uuid,
        kiem_hien_hanh uuid,
        viec_id uuid,
        valid_from date,
        valid_to date,
        tai_boi text NOT NULL,
        tai_luc timestamptz NOT NULL DEFAULT now(),
        duyet_boi text,
        duyet_luc timestamptz,
        tu_choi_ly_do text,
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (mau_id, phap_nhan_id, loai_hinh_id) REFERENCES master.crm_mau (id, phap_nhan_id, loai_hinh_id),
        FOREIGN KEY (tep_id, phap_nhan_id) REFERENCES master.crm_mau_tep (id, phap_nhan_id),
        UNIQUE (mau_id, phien_ban),
        UNIQUE (id, phap_nhan_id),
        CHECK ((trang_thai = 'HIEU_LUC') = (valid_from IS NOT NULL)),
        CHECK (valid_to IS NULL OR (valid_from IS NOT NULL AND valid_to > valid_from)),
        CHECK (trang_thai <> 'CHO_CFO' OR kiem_hien_hanh IS NOT NULL))""",
    # phiên bản: chỉ chủ bảng, không xóa; cột định danh/tệp/danh mục bất biến; HIEU_LUC chỉ được đóng valid_to MỘT lần; TU_CHOI là trạng thái cuối
    """CREATE OR REPLACE FUNCTION master.crm_mau_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: phiên bản mẫu chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa phiên bản mẫu' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'DRAFT' OR NEW.anh_xa_hien_hanh IS NOT NULL OR NEW.kiem_hien_hanh IS NOT NULL OR NEW.viec_id IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: phiên bản mới phải là DRAFT trống' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.mau_id, NEW.phap_nhan_id, NEW.loai_hinh_id, NEW.phien_ban, NEW.tep_id, NEW.ten_tep, NEW.danh_muc_ref, NEW.danh_muc_rev,
                   NEW.danh_muc_digest, NEW.tai_boi, NEW.tai_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.mau_id, OLD.phap_nhan_id, OLD.loai_hinh_id, OLD.phien_ban, OLD.tep_id, OLD.ten_tep, OLD.danh_muc_ref,
                   OLD.danh_muc_rev, OLD.danh_muc_digest, OLD.tai_boi, OLD.tai_luc) THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không sửa định danh/tệp/danh mục của phiên bản mẫu' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'TU_CHOI' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: phiên bản đã từ chối là trạng thái cuối' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'HIEU_LUC' THEN
                IF NEW.trang_thai <> 'HIEU_LUC' OR OLD.valid_to IS NOT NULL OR NEW.valid_to IS NULL
                   OR ROW(NEW.anh_xa_hien_hanh, NEW.kiem_hien_hanh, NEW.viec_id, NEW.valid_from, NEW.duyet_boi, NEW.duyet_luc)
                      IS DISTINCT FROM ROW(OLD.anh_xa_hien_hanh, OLD.kiem_hien_hanh, OLD.viec_id, OLD.valid_from, OLD.duyet_boi, OLD.duyet_luc) THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: phiên bản hiệu lực chỉ được đóng hiệu lực một lần bởi phiên bản kế tiếp đã duyệt' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_mau_phien_ban_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_mau_phien_ban FOR EACH ROW EXECUTE FUNCTION master.crm_mau_phien_ban_kiem()",
    """CREATE TABLE master.crm_mau_anh_xa (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        ban_do jsonb NOT NULL CHECK (jsonb_typeof(ban_do) = 'array'),
        ban_do_sha256 text NOT NULL CHECK (ban_do_sha256 ~ '^[0-9a-f]{64}$'),
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ '^[0-9a-f]{64}$'),
        canh_bao jsonb NOT NULL CHECK (jsonb_typeof(canh_bao) = 'array'),
        so_chua_anh_xa integer NOT NULL CHECK (so_chua_anh_xa >= 0),
        so_sai_kieu integer NOT NULL CHECK (so_sai_kieu >= 0),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.crm_mau_phien_ban (id, phap_nhan_id),
        UNIQUE (phien_ban_id, revision),
        UNIQUE (id, phien_ban_id))""",
    "CREATE TRIGGER crm_mau_anh_xa_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_mau_anh_xa FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_mau_kiem_tra (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        anh_xa_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        facts_sha256 text NOT NULL CHECK (facts_sha256 ~ '^[0-9a-f]{64}$'),
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ '^[0-9a-f]{64}$'),
        ban_do_sha256 text NOT NULL CHECK (ban_do_sha256 ~ '^[0-9a-f]{64}$'),
        ket_qua text NOT NULL CHECK (ket_qua = 'DAT'),
        kiem_boi text NOT NULL,
        kiem_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.crm_mau_phien_ban (id, phap_nhan_id),
        FOREIGN KEY (anh_xa_id, phien_ban_id) REFERENCES master.crm_mau_anh_xa (id, phien_ban_id),
        UNIQUE (id, phien_ban_id))""",
    "CREATE TRIGGER crm_mau_kiem_tra_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_mau_kiem_tra FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # con trỏ hiện hành phải thuộc ĐÚNG phiên bản
    """ALTER TABLE master.crm_mau_phien_ban ADD CONSTRAINT crm_mau_phien_ban_anh_xa_cung_pb
        FOREIGN KEY (anh_xa_hien_hanh, id) REFERENCES master.crm_mau_anh_xa (id, phien_ban_id)""",
    """ALTER TABLE master.crm_mau_phien_ban ADD CONSTRAINT crm_mau_phien_ban_kiem_cung_pb
        FOREIGN KEY (kiem_hien_hanh, id) REFERENCES master.crm_mau_kiem_tra (id, phien_ban_id)""",
    # --- G7: bộ chuẩn theo PN/dự án/giai đoạn; phiên bản có vòng đời; dòng 4 cột bất biến (typed, NULL ≠ 0, ngày ≠ sự kiện)
    """CREATE TABLE master.crm_bo_chuan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        giai_doan text NOT NULL CHECK (giai_doan ~ '^[A-Za-z0-9_.-]{1,80}$'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (phap_nhan_id, du_an_id, giai_doan),
        UNIQUE (id, phap_nhan_id))""",
    "CREATE TRIGGER crm_bo_chuan_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bo_chuan FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE TABLE master.crm_bo_chuan_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        bo_chuan_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        phien_ban integer NOT NULL CHECK (phien_ban >= 1),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DRAFT','CHO_CFO','HIEU_LUC')),
        so_dong integer NOT NULL CHECK (so_dong >= 1),
        dong_sha256 text NOT NULL CHECK (dong_sha256 ~ '^[0-9a-f]{64}$'),
        viec_id uuid,
        valid_from date,
        valid_to date,
        lap_boi text NOT NULL,
        lap_luc timestamptz NOT NULL DEFAULT now(),
        gui_boi text,
        gui_luc timestamptz,
        duyet_boi text,
        duyet_luc timestamptz,
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (bo_chuan_id, phap_nhan_id) REFERENCES master.crm_bo_chuan (id, phap_nhan_id),
        UNIQUE (bo_chuan_id, phien_ban),
        UNIQUE (id, phap_nhan_id),
        CHECK ((trang_thai = 'HIEU_LUC') = (valid_from IS NOT NULL)),
        CHECK (valid_to IS NULL OR (valid_from IS NOT NULL AND valid_to > valid_from)))""",
    """CREATE OR REPLACE FUNCTION master.crm_bo_chuan_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: bộ chuẩn chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa phiên bản bộ chuẩn' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'DRAFT' OR NEW.viec_id IS NOT NULL THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: phiên bản bộ chuẩn mới phải là DRAFT' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.bo_chuan_id, NEW.phap_nhan_id, NEW.phien_ban, NEW.so_dong, NEW.dong_sha256, NEW.lap_boi, NEW.lap_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.bo_chuan_id, OLD.phap_nhan_id, OLD.phien_ban, OLD.so_dong, OLD.dong_sha256, OLD.lap_boi, OLD.lap_luc) THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không sửa định danh/dòng của phiên bản bộ chuẩn' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai = 'HIEU_LUC' THEN
                IF NEW.trang_thai <> 'HIEU_LUC' OR OLD.valid_to IS NOT NULL OR NEW.valid_to IS NULL
                   OR ROW(NEW.viec_id, NEW.valid_from, NEW.gui_boi, NEW.gui_luc, NEW.duyet_boi, NEW.duyet_luc)
                      IS DISTINCT FROM ROW(OLD.viec_id, OLD.valid_from, OLD.gui_boi, OLD.gui_luc, OLD.duyet_boi, OLD.duyet_luc) THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: bộ chuẩn hiệu lực chỉ được đóng hiệu lực một lần' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_bo_chuan_phien_ban_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bo_chuan_phien_ban FOR EACH ROW EXECUTE FUNCTION master.crm_bo_chuan_phien_ban_kiem()",
    """CREATE TABLE master.crm_bo_chuan_dong (
        phien_ban_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu >= 1),
        lan text NOT NULL CHECK (length(lan) BETWEEN 1 AND 40),
        gia_tri_loai text CHECK (gia_tri_loai IN ('PERCENT','AMOUNT')),
        gia_tri_thap_phan text CHECK (gia_tri_thap_phan ~ '^-?[0-9]{1,20}(\\.[0-9]{1,12})?$'),
        so_tien_minor text CHECK (so_tien_minor ~ '^-?[0-9]{1,24}$'),
        tien_te char(3) CHECK (tien_te ~ '^[A-Z]{3}$'),
        moc_loai text CHECK (moc_loai IN ('NGAY','SU_KIEN')),
        moc_ngay date,
        moc_su_kien text CHECK (moc_su_kien ~ '^[A-Za-z0-9_.-]{1,80}$'),
        ghi_chu text CHECK (ghi_chu IS NULL OR length(ghi_chu) <= 1000),
        PRIMARY KEY (phien_ban_id, thu_tu),
        FOREIGN KEY (phien_ban_id, phap_nhan_id) REFERENCES master.crm_bo_chuan_phien_ban (id, phap_nhan_id),
        CHECK (CASE gia_tri_loai WHEN 'PERCENT' THEN gia_tri_thap_phan IS NOT NULL AND so_tien_minor IS NULL AND tien_te IS NULL
                                 WHEN 'AMOUNT' THEN so_tien_minor IS NOT NULL AND tien_te IS NOT NULL AND gia_tri_thap_phan IS NULL
                                 ELSE gia_tri_thap_phan IS NULL AND so_tien_minor IS NULL AND tien_te IS NULL END),
        CHECK (CASE moc_loai WHEN 'NGAY' THEN moc_ngay IS NOT NULL AND moc_su_kien IS NULL
                             WHEN 'SU_KIEN' THEN moc_su_kien IS NOT NULL AND moc_ngay IS NULL
                             ELSE moc_ngay IS NULL AND moc_su_kien IS NULL END))""",
    "CREATE TRIGGER crm_bo_chuan_dong_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bo_chuan_dong FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- biên nhận miền (namespace PN + actor + action + khóa), FINAL bất biến do chính lệnh chốt trong cùng giao dịch
    """CREATE TABLE master.crm_g_bien_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        hanh_dong text NOT NULL CHECK (hanh_dong ~ '^[A-Z0-9_]{1,60}$'),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        yeu_cau_sha256 text NOT NULL CHECK (yeu_cau_sha256 ~ '^[0-9a-f]{64}$'),
        ket_qua jsonb NOT NULL CHECK (jsonb_typeof(ket_qua) = 'object'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, nguoi_dung_id, hanh_dong, khoa))""",
    "CREATE TRIGGER crm_g_bien_nhan_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_g_bien_nhan FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- K5 typed: guard INVOKER (OLD typed OR NEW typed) — chỉ chủ bảng, đúng tồn tại/PN/module CRM/V4, cấm đổi đích/xóa/mở lại
    """CREATE OR REPLACE FUNCTION kho.crm_g_viec_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE cu_typed boolean := false; moi_typed boolean := false; ok boolean;
        BEGIN
            IF TG_OP <> 'INSERT' THEN cu_typed := OLD.tham_chieu_bang IN """ + _G_TYPED + """; END IF;
            IF TG_OP <> 'DELETE' THEN moi_typed := NEW.tham_chieu_bang IN """ + _G_TYPED + """; END IF;
            IF NOT (cu_typed OR moi_typed) THEN
                RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END IF;
            IF NOT master.la_chu_bang('kho.viec_can_duyet'::regclass) THEN
                RAISE EXCEPTION 'CRM_G_VIEC_CHI_CHU: việc duyệt mẫu/bộ chuẩn chỉ do lệnh CRM-G trên kết nối chủ bảng ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_VIEC_BAT_BIEN: không xóa việc duyệt mẫu/bộ chuẩn' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF ROW(OLD.tham_chieu_bang, OLD.tham_chieu_id, OLD.phap_nhan_id, OLD.module, OLD.loai)
                   IS DISTINCT FROM ROW(NEW.tham_chieu_bang, NEW.tham_chieu_id, NEW.phap_nhan_id, NEW.module, NEW.loai) THEN
                    RAISE EXCEPTION 'CRM_G_VIEC_DOI_DICH: không đổi đích/PN/module/loại của việc duyệt' USING ERRCODE = 'P0001';
                END IF;
                IF OLD.trang_thai IN ('DA_DUYET','BO_QUA','DONG') THEN
                    RAISE EXCEPTION 'CRM_G_VIEC_DA_DONG: việc duyệt đã đóng — không mở lại/sửa' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            IF NEW.module IS DISTINCT FROM 'CRM' OR NEW.loai IS DISTINCT FROM 'V4' THEN
                RAISE EXCEPTION 'CRM_G_VIEC_SAI_LOAI: việc duyệt mẫu/bộ chuẩn phải là CRM/V4' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.tham_chieu_bang = 'master.crm_mau_phien_ban' THEN
                SELECT EXISTS (SELECT 1 FROM master.crm_mau_phien_ban v WHERE v.id = NEW.tham_chieu_id AND v.phap_nhan_id = NEW.phap_nhan_id) INTO ok;
            ELSE
                SELECT EXISTS (SELECT 1 FROM master.crm_bo_chuan_phien_ban v WHERE v.id = NEW.tham_chieu_id AND v.phap_nhan_id = NEW.phap_nhan_id) INTO ok;
            END IF;
            IF NOT ok THEN
                RAISE EXCEPTION 'CRM_G_VIEC_SAI_DICH: đích việc duyệt không tồn tại hoặc khác pháp nhân' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_g_viec_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.viec_can_duyet FOR EACH ROW EXECUTE FUNCTION kho.crm_g_viec_kiem()",
    # resolver typed CHÍNH XÁC cho đúng hai chủ thể mới: (PN, module 'CRM') của phiên bản mẫu/bộ chuẩn; không có → 0 dòng
    """CREATE OR REPLACE FUNCTION kho.crm_g_chu_the(p_bang text, p_id uuid) RETURNS TABLE (phap_nhan_id uuid, module text)
        LANGUAGE sql STABLE SET search_path = master, kho, pg_temp AS $$
        SELECT v.phap_nhan_id, 'CRM'::text FROM master.crm_mau_phien_ban v WHERE p_bang = 'master.crm_mau_phien_ban' AND v.id = p_id
        UNION ALL
        SELECT v.phap_nhan_id, 'CRM'::text FROM master.crm_bo_chuan_phien_ban v WHERE p_bang = 'master.crm_bo_chuan_phien_ban' AND v.id = p_id
        $$""",
    "REVOKE EXECUTE ON FUNCTION kho.crm_g_chu_the(text, uuid) FROM PUBLIC",
    # Guard chủ thể K5 chung (M0009 dòng viec_chu_so_huu): giữ NGUYÊN mọi nhánh cũ (UPDATE bất biến chủ thể; allowlist cũ; resolver cũ) — chỉ
    # thêm MỘT nhánh INSERT cho đúng hai chủ thể typed, kiểm bằng resolver typed chính xác (tồn tại + cùng PN + module). Không nới allowlist
    # cho chủ thể/module khác; guard typed crm_g_viec_kiem (chạy trước) vẫn buộc chủ bảng + CRM/V4.
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
    # --- quyền đọc/hành động theo QUYỀN HIỆN HÀNH của phiên
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_doc(p_pn uuid, p_loai uuid) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT CASE WHEN NOT master.ktt_duoc(p_pn, 'CRM') THEN NULL
                    WHEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL)
                         OR master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai) THEN 'DAY_DU'
                    ELSE 'HIEU_LUC' END
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_doc_duoc(p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.ktt_duoc(p_pn, 'CRM') AND master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL)
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_duoc(p_hanh_dong text, p_pn uuid, p_loai uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.ktt_duoc(p_pn, 'CRM') AND CASE
            WHEN p_hanh_dong = 'CRM_MAU_TAI' THEN master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai)
            WHEN p_hanh_dong IN ('CRM_MAU_MAP','CRM_MAU_GUI_KIEM') THEN master.ktt_hanh_dong_duoc(p_pn, 'CRM', 'CRM_MAU_TAI', p_loai)
                 OR master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
            WHEN p_hanh_dong IN ('CRM_MAU_KIEM','CRM_MAU_TRA_LAI','CRM_CHUAN_LAP','CRM_CHUAN_GUI_DUYET')
                 THEN master.ktt_co_vai(p_pn, ARRAY['KE_TOAN','KE_TOAN_TRUONG'], NULL)
            WHEN p_hanh_dong IN ('CRM_MAU_DUYET_V4','CRM_MAU_TU_CHOI','CRM_CHUAN_DUYET_V4') THEN master.ktt_co_vai(p_pn, ARRAY['CFO'], 'V4')
            ELSE false END
        $$""",
    # K5 typed: đọc chỉ khi phiên có quyền xem bản nháp/lịch sử hiện hành của đúng đối tượng — áp cho MỌI trạng thái (kể cả đã đóng)
    """CREATE OR REPLACE FUNCTION master.crm_g_viec_doc_duoc(p_bang text, p_id uuid, p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT CASE WHEN p_bang = 'master.crm_mau_phien_ban' THEN
                        coalesce((SELECT master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) = 'DAY_DU' FROM master.crm_mau_phien_ban v
                                  WHERE v.id = p_id AND v.phap_nhan_id = p_pn), false)
                    WHEN p_bang = 'master.crm_bo_chuan_phien_ban' THEN
                        EXISTS (SELECT 1 FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_id AND v.phap_nhan_id = p_pn) AND master.crm_g_chuan_doc_duoc(p_pn)
                    ELSE true END
        $$""",
    """CREATE POLICY viec_can_duyet_crm_g_doc ON kho.viec_can_duyet AS RESTRICTIVE FOR SELECT TO PUBLIC
        USING (tham_chieu_bang NOT IN """ + _G_TYPED + """ OR master.crm_g_viec_doc_duoc(tham_chieu_bang, tham_chieu_id, phap_nhan_id))""",
    # --- nội bộ: danh tính phiên, đích + quyền TRƯỚC tra biên nhận, biên nhận, token CAS, digest danh mục
    """CREATE OR REPLACE FUNCTION master.crm_g_ai_id() RETURNS uuid
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE i uuid;
        BEGIN
            SELECT n.id INTO i FROM master.nguoi_dung n WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '');
            IF i IS NULL THEN
                RAISE EXCEPTION 'CRM_G_DANH_TINH: chưa có danh tính phiên hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            RETURN i;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_dich(p_hanh_dong text, p_dich uuid, OUT pn uuid, OUT loai uuid)
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        BEGIN
            IF p_hanh_dong = 'CRM_MAU_TAI' THEN
                SELECT l.phap_nhan_id, l.id INTO pn, loai FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich;
                IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy loại hình (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF p_hanh_dong IN ('CRM_MAU_MAP','CRM_MAU_GUI_KIEM','CRM_MAU_KIEM','CRM_MAU_TRA_LAI','CRM_MAU_DUYET_V4','CRM_MAU_TU_CHOI') THEN
                SELECT v.phap_nhan_id, v.loai_hinh_id INTO pn, loai FROM master.crm_mau_phien_ban v WHERE v.id = p_dich;
                IF pn IS NULL OR master.crm_g_mau_doc(pn, loai) IS DISTINCT FROM 'DAY_DU' THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy phiên bản mẫu (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF p_hanh_dong = 'CRM_CHUAN_LAP' THEN
                SELECT a.phap_nhan_id INTO pn FROM master.du_an a WHERE a.id = p_dich;
                IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSIF p_hanh_dong IN ('CRM_CHUAN_GUI_DUYET','CRM_CHUAN_DUYET_V4') THEN
                SELECT v.phap_nhan_id INTO pn FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_dich;
                IF pn IS NULL OR NOT master.crm_g_chuan_doc_duoc(pn) THEN
                    RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bộ chuẩn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_g_duoc(p_hanh_dong, pn, loai) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền hiện hành cho %', p_hanh_dong USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_bn_tra(p_pn uuid, p_hanh_dong text, p_khoa text, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE aid uuid := master.crm_g_ai_id(); b record;
        BEGIN
            IF p_khoa IS NULL OR p_khoa !~ '^[A-Za-z0-9_.:-]{1,200}$' THEN
                RAISE EXCEPTION 'CRM_G_KHOA: thiếu hoặc sai khóa thao tác' USING ERRCODE = 'P0001';
            END IF;
            IF p_h IS NULL OR p_h !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: thiếu digest yêu cầu gốc' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g|' || p_pn::text || '|' || aid::text || '|' || p_hanh_dong || '|' || p_khoa, 0));
            SELECT * INTO b FROM master.crm_g_bien_nhan WHERE phap_nhan_id = p_pn AND nguoi_dung_id = aid AND hanh_dong = p_hanh_dong AND khoa = p_khoa;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            IF b.yeu_cau_sha256 <> p_h THEN
                RAISE EXCEPTION 'CRM_G_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
            END IF;
            RETURN b.ket_qua;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_bn_ghi(p_pn uuid, p_hanh_dong text, p_khoa text, p_h text, p_kq jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            INSERT INTO master.crm_g_bien_nhan (phap_nhan_id, nguoi_dung_id, hanh_dong, khoa, yeu_cau_sha256, ket_qua)
                VALUES (p_pn, master.crm_g_ai_id(), p_hanh_dong, p_khoa, p_h, p_kq);
        END $$""",
    # S01: ghim các dòng quyền của phiên (FOR SHARE) đến hết giao dịch — thu hồi đồng thời phải chờ; thu hồi đã commit trước thì lệnh kế
    # (snapshot mới, READ COMMITTED) thấy và từ chối. Không đổi quyền, không ghi gì.
    """CREATE OR REPLACE FUNCTION master.crm_g_ghim_quyen(p_pn uuid) RETURNS void
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE i text := nullif(current_setting('ktt.nguoi_dung_id', true), '');
        BEGIN
            IF i IS NULL OR p_pn IS NULL THEN
                RETURN;
            END IF;
            PERFORM 1 FROM master.nguoi_dung n WHERE n.id::text = i FOR SHARE;
            PERFORM 1 FROM master.phan_quyen q WHERE q.nguoi_dung_id::text = i AND q.phap_nhan_id = p_pn FOR SHARE;
            PERFORM 1 FROM master.phan_cong_hanh_dong a WHERE a.nguoi_dung_id::text = i AND a.phap_nhan_id = p_pn AND a.thu_hoi_luc IS NULL FOR SHARE;
        END $$""",
    # tra biên nhận TRƯỚC parse/stage/blob: ghim quyền → đích + quyền hiện hành → biên nhận dưới khóa namespace (cùng H → FINAL cũ; khác H → 409);
    # không ghi gì. Gọi TRONG CÙNG giao dịch với parse/blob/lệnh: khóa namespace + dòng quyền giữ đến FINAL.
    """CREATE OR REPLACE FUNCTION master.crm_g_tra(p_hanh_dong text, p_khoa text, p_dich uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE d record; cu jsonb; pn_tam uuid;
        BEGIN""" + _G_CHU + """
            pn_tam := CASE WHEN p_hanh_dong = 'CRM_MAU_TAI' THEN (SELECT l.phap_nhan_id FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich)
                           WHEN left(p_hanh_dong, 8) = 'CRM_MAU_' THEN (SELECT v.phap_nhan_id FROM master.crm_mau_phien_ban v WHERE v.id = p_dich)
                           WHEN p_hanh_dong = 'CRM_CHUAN_LAP' THEN (SELECT a.phap_nhan_id FROM master.du_an a WHERE a.id = p_dich)
                           ELSE (SELECT v.phap_nhan_id FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_dich) END;
            PERFORM master.crm_g_ghim_quyen(pn_tam);
            SELECT * INTO d FROM master.crm_g_dich(p_hanh_dong, p_dich);
            cu := master.crm_g_bn_tra(d.pn, p_hanh_dong, p_khoa, p_h);
            RETURN CASE WHEN cu IS NULL THEN NULL ELSE jsonb_build_object('lap_lai', true, 'ket_qua', cu) END;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_danh_muc_digest(p_loai uuid, p_ref text, p_rev integer) RETURNS text
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT encode(sha256(convert_to(coalesce(string_agg(t.khoa || chr(31) || t.kieu || chr(31) || t.bat_buoc::text || chr(31) || t.pii::text
                                                            || chr(31) || t.dinh_dang || chr(31) || t.nhan, chr(30) ORDER BY t.khoa), ''), 'UTF8')), 'hex')
        FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = p_loai AND t.danh_muc_ref = p_ref AND t.revision = p_rev
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_token(p_pb uuid) RETURNS text
        LANGUAGE sql STABLE SET search_path = master, kho, pg_temp AS $$
        SELECT encode(sha256(convert_to(concat_ws('|', v.id::text, v.trang_thai, v.anh_xa_hien_hanh::text, v.kiem_hien_hanh::text, v.viec_id::text,
                                                  v.valid_from::text, v.valid_to::text, (SELECT w.trang_thai FROM kho.viec_can_duyet w WHERE w.id = v.viec_id),
                                                  v.cap_nhat_luc::text), 'UTF8')), 'hex')
        FROM master.crm_mau_phien_ban v WHERE v.id = p_pb
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_token(p_pb uuid) RETURNS text
        LANGUAGE sql STABLE SET search_path = master, kho, pg_temp AS $$
        SELECT encode(sha256(convert_to(concat_ws('|', v.id::text, v.trang_thai, v.viec_id::text, v.valid_from::text, v.valid_to::text,
                                                  (SELECT w.trang_thai FROM kho.viec_can_duyet w WHERE w.id = v.viec_id), v.cap_nhat_luc::text), 'UTF8')), 'hex')
        FROM master.crm_bo_chuan_phien_ban v WHERE v.id = p_pb
        $$""",
    # ======================================================================= lệnh G1
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_tai(p_khoa text, p_h text, p_loai uuid, p_ma_mau text, p_ten_tep text, p_raw_sha text, p_len bigint,
                                                    p_bo_doc text, p_facts jsonb, p_facts_sha text, p_trang_thai_doc text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ m record; tep_moi uuid; pb uuid; n integer; ref text; rev integer;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_TAI', p_loai);""" + _G_REPLAY.format(a="'CRM_MAU_TAI'") + """
            SELECT t.danh_muc_ref, t.revision INTO ref, rev FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = p_loai
                ORDER BY t.revision DESC, t.danh_muc_ref LIMIT 1;
            IF ref IS NULL THEN
                RAISE EXCEPTION 'CRM_G_CHUA_CO_DANH_MUC: loại hình chưa có danh mục trường' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_typeof(p_facts -> 'occurrences') IS DISTINCT FROM 'array' OR p_raw_sha IS DISTINCT FROM p_facts ->> 'raw_sha256' THEN
                RAISE EXCEPTION 'CRM_G_FACTS_SAI: kết quả phát hiện không khớp tệp đã nhận' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('crm_g_mau|' || d.pn::text || '|' || p_ma_mau, 0));  -- tạo gốc cùng mã tuần tự
            SELECT * INTO m FROM master.crm_mau WHERE phap_nhan_id = d.pn AND ma_mau = p_ma_mau FOR UPDATE;
            IF NOT FOUND THEN
                INSERT INTO master.crm_mau (phap_nhan_id, ma_mau, loai_hinh_id, tao_boi) VALUES (d.pn, p_ma_mau, p_loai, ai) RETURNING * INTO m;
            ELSIF m.loai_hinh_id <> p_loai THEN
                RAISE EXCEPTION 'CRM_G_MAU_KHAC_LOAI: mã mẫu đã thuộc loại hình khác' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_mau_tep (phap_nhan_id, raw_sha256, byte_length, object_key, bo_doc, facts, facts_sha256, trang_thai_doc, tao_boi)
                VALUES (d.pn, p_raw_sha, p_len, 'crm-mau/' || p_raw_sha, p_bo_doc, p_facts, p_facts_sha, p_trang_thai_doc, ai)
                ON CONFLICT (phap_nhan_id, raw_sha256, bo_doc) DO NOTHING RETURNING id INTO tep_moi;
            IF tep_moi IS NULL THEN
                SELECT x.id INTO tep_moi FROM master.crm_mau_tep x WHERE x.phap_nhan_id = d.pn AND x.raw_sha256 = p_raw_sha AND x.bo_doc = p_bo_doc
                    AND x.byte_length = p_len AND x.facts_sha256 = p_facts_sha;
                IF tep_moi IS NULL THEN
                    RAISE EXCEPTION 'CRM_G_TEP_XUNG_DOT: cùng hash nhưng độ dài/kết quả phát hiện khác' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            SELECT coalesce(max(phien_ban), 0) + 1 INTO n FROM master.crm_mau_phien_ban WHERE mau_id = m.id;
            INSERT INTO master.crm_mau_phien_ban (mau_id, phap_nhan_id, loai_hinh_id, phien_ban, tep_id, ten_tep, danh_muc_ref, danh_muc_rev, danh_muc_digest,
                                                  trang_thai, tai_boi)
                VALUES (m.id, d.pn, p_loai, n, tep_moi, p_ten_tep, ref, rev, master.crm_g_danh_muc_digest(p_loai, ref, rev), 'DRAFT', ai) RETURNING id INTO pb;
            """ + _G_NK.format(pn="d.pn", loai="'SUA_DANH_MUC'", bang="'master.crm_mau_phien_ban'", id="pb", hd="'CRM_MAU_TAI'",
                               sau="jsonb_build_object('ma_mau', p_ma_mau, 'phien_ban', n, 'raw_sha256', p_raw_sha)", ly="NULL") + """
            kq := jsonb_build_object('mau_id', m.id, 'phien_ban_id', pb, 'phien_ban', n, 'trang_thai', 'DRAFT', 'trang_thai_doc', p_trang_thai_doc,
                                     'raw_sha256', p_raw_sha);""" + _G_KET.format(a="'CRM_MAU_TAI'") + """
        END $$""",
    # ánh xạ: {placeholder: field_key|null}; mỗi lần xuất hiện thực giữ tên/phần/vị trí và trỏ đúng MỘT trường của danh mục hiện hành;
    # trường bắt buộc vắng chỉ cảnh báo; ô chưa ánh xạ/sai kiểu được ghi đếm (chặn kiểm/duyệt); đổi ánh xạ vô hiệu lần kiểm hiện hành
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_anh_xa(p_khoa text, p_h text, p_pb uuid, p_token text, p_ban_do jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; tep record; o record; kieu_tr text; bd jsonb := '[]'::jsonb; cb jsonb := '[]'::jsonb;
                chua integer := 0; sai integer := 0; rev integer; ax uuid; ten text; k text; bd_sha text;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_MAP', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_MAP'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai NOT IN ('DRAFT','CHO_KIEM','CHO_CFO') THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: phiên bản % không còn sửa ánh xạ', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_ban_do IS NULL OR jsonb_typeof(p_ban_do) <> 'object' THEN
                RAISE EXCEPTION 'CRM_G_ANH_XA_SAI: ánh xạ phải là object placeholder → trường' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO tep FROM master.crm_mau_tep WHERE id = v.tep_id;
            FOR k IN SELECT jsonb_object_keys(p_ban_do) LOOP
                IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(tep.facts -> 'occurrences') e WHERE e ->> 'ten' = k) THEN
                    RAISE EXCEPTION 'CRM_G_ANH_XA_THUA: placeholder % không có trong tệp', k USING ERRCODE = 'P0001';
                END IF;
                IF jsonb_typeof(p_ban_do -> k) NOT IN ('string','null') THEN
                    RAISE EXCEPTION 'CRM_G_ANH_XA_SAI: giá trị ánh xạ phải là mã trường hoặc null' USING ERRCODE = 'P0001';
                END IF;
                IF jsonb_typeof(p_ban_do -> k) = 'string' AND NOT EXISTS (SELECT 1 FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = v.loai_hinh_id
                        AND t.danh_muc_ref = v.danh_muc_ref AND t.revision = v.danh_muc_rev AND t.khoa = p_ban_do ->> k) THEN
                    RAISE EXCEPTION 'CRM_G_TRUONG_KHONG_CO: trường % không thuộc danh mục hiện hành của loại hình', p_ban_do ->> k USING ERRCODE = 'P0001';
                END IF;
            END LOOP;
            FOR o IN SELECT e AS occ, ord FROM jsonb_array_elements(tep.facts -> 'occurrences') WITH ORDINALITY AS x(e, ord) ORDER BY ord LOOP
                ten := o.occ ->> 'ten';
                k := p_ban_do ->> ten;
                kieu_tr := NULL;
                IF k IS NULL THEN
                    chua := chua + 1;
                ELSE
                    SELECT t.kieu INTO kieu_tr FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = v.loai_hinh_id AND t.danh_muc_ref = v.danh_muc_ref
                        AND t.revision = v.danh_muc_rev AND t.khoa = k;
                    IF kieu_tr = 'bang' THEN
                        sai := sai + 1;
                    END IF;
                END IF;
                bd := bd || jsonb_build_object('thu_tu', o.ord, 'ten', ten, 'phan', o.occ -> 'phan', 'vi_tri', o.occ -> 'vi_tri', 'truong', k,
                                               'kieu', kieu_tr);
            END LOOP;
            SELECT coalesce(jsonb_agg(jsonb_build_object('ma', 'TRUONG_BAT_BUOC_VANG', 'truong', t.khoa) ORDER BY t.khoa), '[]'::jsonb) INTO cb
                FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = v.loai_hinh_id AND t.danh_muc_ref = v.danh_muc_ref AND t.revision = v.danh_muc_rev
                  AND t.bat_buoc AND NOT EXISTS (SELECT 1 FROM jsonb_each_text(p_ban_do) x WHERE x.value = t.khoa);
            bd_sha := encode(sha256(convert_to(bd::text, 'UTF8')), 'hex');
            SELECT coalesce(max(revision), 0) + 1 INTO rev FROM master.crm_mau_anh_xa WHERE phien_ban_id = v.id;
            INSERT INTO master.crm_mau_anh_xa (phien_ban_id, phap_nhan_id, revision, ban_do, ban_do_sha256, danh_muc_digest, canh_bao, so_chua_anh_xa,
                                               so_sai_kieu, tao_boi)
                VALUES (v.id, d.pn, rev, bd, bd_sha, v.danh_muc_digest, cb, chua, sai, ai) RETURNING id INTO ax;
            UPDATE master.crm_mau_phien_ban SET anh_xa_hien_hanh = ax, kiem_hien_hanh = NULL,
                   trang_thai = CASE WHEN trang_thai = 'CHO_CFO' THEN 'CHO_KIEM' ELSE trang_thai END, cap_nhat_luc = clock_timestamp()
                WHERE id = v.id;
            """ + _G_NK.format(pn="d.pn", loai="'SUA_DANH_MUC'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_MAP'",
                               sau="jsonb_build_object('revision', rev, 'so_chua_anh_xa', chua, 'so_sai_kieu', sai)", ly="NULL") + """
            kq := jsonb_build_object('anh_xa_id', ax, 'revision', rev, 'so_chua_anh_xa', chua, 'so_sai_kieu', sai, 'canh_bao', cb,
                                     'trang_thai', CASE WHEN v.trang_thai = 'CHO_CFO' THEN 'CHO_KIEM' ELSE v.trang_thai END);""" + _G_KET.format(a="'CRM_MAU_MAP'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_gui_kiem(p_khoa text, p_h text, p_pb uuid, p_token text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; w uuid;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_GUI_KIEM', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_GUI_KIEM'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai <> 'DRAFT' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: chỉ gửi kiểm từ DRAFT (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF v.anh_xa_hien_hanh IS NULL THEN
                RAISE EXCEPTION 'CRM_G_CHUA_ANH_XA: chưa lưu ánh xạ' USING ERRCODE = 'P0001';
            END IF;
            IF v.viec_id IS NULL THEN
                INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                    VALUES (d.pn, 'V4', 'CRM_MAU', 'CRM', 'master.crm_mau_phien_ban', v.id, 'CFO', 'Mẫu hợp đồng chờ kiểm/duyệt', '{}') RETURNING id INTO w;
            ELSE
                UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_DUYET', cap_nhat_luc = now() WHERE id = v.viec_id AND trang_thai = 'CHO_BO_SUNG' RETURNING id INTO w;
                IF w IS NULL THEN
                    RAISE EXCEPTION 'CRM_G_VIEC_SAI: việc duyệt của phiên bản không ở trạng thái chờ bổ sung' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            UPDATE master.crm_mau_phien_ban SET trang_thai = 'CHO_KIEM', viec_id = w, cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_GUI_KIEM'",
                               sau="jsonb_build_object('viec_id', w)", ly="NULL") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'CHO_KIEM', 'viec_id', w);""" + _G_KET.format(a="'CRM_MAU_GUI_KIEM'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_kiem(p_khoa text, p_h text, p_pb uuid, p_token text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; ax record; tep record; kt uuid;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_KIEM', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_KIEM'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai <> 'CHO_KIEM' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: chỉ kiểm phiên bản CHO_KIEM (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO ax FROM master.crm_mau_anh_xa WHERE id = v.anh_xa_hien_hanh;
            SELECT * INTO tep FROM master.crm_mau_tep WHERE id = v.tep_id;
            IF ax.id IS NULL OR ax.so_chua_anh_xa > 0 OR ax.so_sai_kieu > 0 OR tep.trang_thai_doc <> 'DU' OR ax.danh_muc_digest <> v.danh_muc_digest
               OR master.crm_g_danh_muc_digest(v.loai_hinh_id, v.danh_muc_ref, v.danh_muc_rev) <> v.danh_muc_digest THEN
                RAISE EXCEPTION 'CRM_G_CHUA_DU_DIEU_KIEN: còn ô chưa ánh xạ/sai kiểu, tệp phát hiện chưa đủ hoặc danh mục đã đổi' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_mau_kiem_tra (phien_ban_id, phap_nhan_id, anh_xa_id, raw_sha256, facts_sha256, danh_muc_digest, ban_do_sha256, ket_qua, kiem_boi)
                VALUES (v.id, d.pn, ax.id, tep.raw_sha256, tep.facts_sha256, v.danh_muc_digest, ax.ban_do_sha256, 'DAT', ai) RETURNING id INTO kt;
            UPDATE master.crm_mau_phien_ban SET trang_thai = 'CHO_CFO', kiem_hien_hanh = kt, cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            UPDATE kho.viec_can_duyet SET kiem_boi = ai, kiem_luc = now(), cap_nhat_luc = now() WHERE id = v.viec_id AND trang_thai = 'CHO_DUYET';
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_KIEM'",
                               sau="jsonb_build_object('kiem_tra_id', kt, 'anh_xa_id', ax.id)", ly="NULL") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'CHO_CFO', 'kiem_tra_id', kt);""" + _G_KET.format(a="'CRM_MAU_KIEM'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_tra_lai(p_khoa text, p_h text, p_pb uuid, p_token text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_TRA_LAI', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_TRA_LAI'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai <> 'CHO_KIEM' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: kế toán chỉ trả lại phiên bản CHO_KIEM (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' OR length(p_ly_do) > 1000 THEN
                RAISE EXCEPTION 'CRM_G_THIEU_LY_DO: trả lại cần lý do' USING ERRCODE = 'P0001';
            END IF;
            UPDATE master.crm_mau_phien_ban SET trang_thai = 'DRAFT', kiem_hien_hanh = NULL, cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_BO_SUNG', ly_do_cho = (SELECT array_agg(DISTINCT u) FROM unnest(ly_do_cho || ARRAY['KT_TRA_LAI']) u),
                   cap_nhat_luc = now() WHERE id = v.viec_id AND trang_thai = 'CHO_DUYET';
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_TRA_LAI'",
                               sau="jsonb_build_object('trang_thai', 'DRAFT')", ly="p_ly_do") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'DRAFT', 'viec_id', v.viec_id);""" + _G_KET.format(a="'CRM_MAU_TRA_LAI'") + """
        END $$""",
    # CFO+V4: ghim đúng lần kiểm (raw/facts/danh mục/ánh xạ); hiệu lực không chồng trong cùng gốc; chỉ phiên bản kế tiếp đã duyệt đóng valid_to
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_duyet(p_khoa text, p_h text, p_pb uuid, p_token text, p_valid_from date) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; ax record; tep record; kt record; cuoi date; truoc uuid;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_DUYET_V4', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_DUYET_V4'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR UPDATE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai <> 'CHO_CFO' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: chỉ duyệt phiên bản CHO_CFO (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO kt FROM master.crm_mau_kiem_tra WHERE id = v.kiem_hien_hanh;
            SELECT * INTO ax FROM master.crm_mau_anh_xa WHERE id = v.anh_xa_hien_hanh;
            SELECT * INTO tep FROM master.crm_mau_tep WHERE id = v.tep_id;
            IF kt.id IS NULL OR kt.anh_xa_id IS DISTINCT FROM ax.id OR kt.raw_sha256 <> tep.raw_sha256 OR kt.facts_sha256 <> tep.facts_sha256
               OR kt.ban_do_sha256 <> ax.ban_do_sha256 OR kt.danh_muc_digest <> v.danh_muc_digest
               OR master.crm_g_danh_muc_digest(v.loai_hinh_id, v.danh_muc_ref, v.danh_muc_rev) <> v.danh_muc_digest
               OR ax.so_chua_anh_xa > 0 OR ax.so_sai_kieu > 0 OR tep.trang_thai_doc <> 'DU' THEN
                RAISE EXCEPTION 'CRM_G_KIEM_HET_HIEU_LUC: lần kiểm không còn khớp tệp/ánh xạ/danh mục hiện hành' USING ERRCODE = 'P0001';
            END IF;
            IF kt.kiem_boi = ai THEN
                RAISE EXCEPTION 'CRM_G_CUNG_NGUOI: người duyệt phải khác người kiểm' USING ERRCODE = 'P0001';
            END IF;
            IF p_valid_from IS NULL THEN
                RAISE EXCEPTION 'CRM_G_THIEU_NGAY: cần ngày hiệu lực' USING ERRCODE = 'P0001';
            END IF;
            SELECT max(valid_from) INTO cuoi FROM master.crm_mau_phien_ban WHERE mau_id = v.mau_id AND trang_thai = 'HIEU_LUC';
            IF cuoi IS NOT NULL AND p_valid_from <= cuoi THEN
                RAISE EXCEPTION 'CRM_G_HIEU_LUC_CHONG: ngày hiệu lực phải sau phiên bản đã duyệt gần nhất (%)', cuoi USING ERRCODE = 'P0001';
            END IF;
            UPDATE master.crm_mau_phien_ban SET valid_to = p_valid_from, cap_nhat_luc = clock_timestamp()
                WHERE mau_id = v.mau_id AND trang_thai = 'HIEU_LUC' AND valid_to IS NULL RETURNING id INTO truoc;
            UPDATE master.crm_mau_phien_ban SET trang_thai = 'HIEU_LUC', valid_from = p_valid_from, duyet_boi = ai, duyet_luc = now(),
                   cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET', duyet_boi = ai, duyet_luc = now(), cap_nhat_luc = now()
                WHERE id = v.viec_id AND trang_thai = 'CHO_DUYET';
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_DUYET_V4'",
                               sau="jsonb_build_object('valid_from', p_valid_from, 'kiem_tra_id', kt.id, 'dong_phien_ban', truoc)", ly="NULL") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'HIEU_LUC', 'valid_from', p_valid_from, 'dong_phien_ban_truoc', truoc);"""
    + _G_KET.format(a="'CRM_MAU_DUYET_V4'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_mau_tu_choi(p_khoa text, p_h text, p_pb uuid, p_token text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_MAU_TU_CHOI', p_pb);""" + _G_REPLAY.format(a="'CRM_MAU_TU_CHOI'") + """
            PERFORM 1 FROM master.crm_mau m WHERE m.id = (SELECT mau_id FROM master.crm_mau_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_MAU + """
            IF v.trang_thai <> 'CHO_CFO' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: CFO chỉ từ chối phiên bản CHO_CFO (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' OR length(p_ly_do) > 1000 THEN
                RAISE EXCEPTION 'CRM_G_THIEU_LY_DO: từ chối cần lý do' USING ERRCODE = 'P0001';
            END IF;
            UPDATE master.crm_mau_phien_ban SET trang_thai = 'TU_CHOI', tu_choi_ly_do = p_ly_do, duyet_boi = ai, duyet_luc = now(),
                   cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'DONG', duyet_boi = ai, duyet_luc = now(), cap_nhat_luc = now()
                WHERE id = v.viec_id AND trang_thai = 'CHO_DUYET';
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_mau_phien_ban'", id="v.id", hd="'CRM_MAU_TU_CHOI'",
                               sau="jsonb_build_object('trang_thai', 'TU_CHOI')", ly="p_ly_do") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'TU_CHOI');""" + _G_KET.format(a="'CRM_MAU_TU_CHOI'") + """
        END $$""",
    # ======================================================================= lệnh G7 (KT lập/gửi → CFO+V4 duyệt; không có nhánh trả lại)
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_lap(p_khoa text, p_h text, p_du_an uuid, p_giai_doan text, p_dong jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ b record; pb uuid; n integer; r record; so integer;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_CHUAN_LAP', p_du_an);""" + _G_REPLAY.format(a="'CRM_CHUAN_LAP'") + """
            IF p_dong IS NULL OR jsonb_typeof(p_dong) <> 'array' OR jsonb_array_length(p_dong) = 0 OR jsonb_array_length(p_dong) > 200 THEN
                RAISE EXCEPTION 'CRM_G_CHUAN_SAI: bộ chuẩn cần 1–200 dòng' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO b FROM master.crm_bo_chuan WHERE phap_nhan_id = d.pn AND du_an_id = p_du_an AND giai_doan = p_giai_doan FOR UPDATE;
            IF NOT FOUND THEN
                INSERT INTO master.crm_bo_chuan (phap_nhan_id, du_an_id, giai_doan, tao_boi) VALUES (d.pn, p_du_an, p_giai_doan, ai) RETURNING * INTO b;
            END IF;
            SELECT coalesce(max(phien_ban), 0) + 1 INTO n FROM master.crm_bo_chuan_phien_ban WHERE bo_chuan_id = b.id;
            so := jsonb_array_length(p_dong);
            INSERT INTO master.crm_bo_chuan_phien_ban (bo_chuan_id, phap_nhan_id, phien_ban, trang_thai, so_dong, dong_sha256, lap_boi)
                VALUES (b.id, d.pn, n, 'DRAFT', so, encode(sha256(convert_to(p_dong::text, 'UTF8')), 'hex'), ai) RETURNING id INTO pb;
            FOR r IN SELECT e, ord FROM jsonb_array_elements(p_dong) WITH ORDINALITY AS x(e, ord) LOOP
                IF jsonb_typeof(r.e) <> 'object' THEN
                    RAISE EXCEPTION 'CRM_G_CHUAN_SAI: mỗi dòng là object' USING ERRCODE = 'P0001';
                END IF;
                INSERT INTO master.crm_bo_chuan_dong (phien_ban_id, phap_nhan_id, thu_tu, lan, gia_tri_loai, gia_tri_thap_phan, so_tien_minor, tien_te,
                                                      moc_loai, moc_ngay, moc_su_kien, ghi_chu)
                    VALUES (pb, d.pn, r.ord, r.e ->> 'lan', r.e ->> 'gia_tri_loai', r.e ->> 'gia_tri_thap_phan', r.e ->> 'so_tien_minor', r.e ->> 'tien_te',
                            r.e ->> 'moc_loai', (r.e ->> 'moc_ngay')::date, r.e ->> 'moc_su_kien', r.e ->> 'ghi_chu');
            END LOOP;
            """ + _G_NK.format(pn="d.pn", loai="'SUA_DANH_MUC'", bang="'master.crm_bo_chuan_phien_ban'", id="pb", hd="'CRM_CHUAN_LAP'",
                               sau="jsonb_build_object('giai_doan', p_giai_doan, 'phien_ban', n, 'so_dong', so)", ly="NULL") + """
            kq := jsonb_build_object('bo_chuan_id', b.id, 'phien_ban_id', pb, 'phien_ban', n, 'trang_thai', 'DRAFT', 'so_dong', so);"""
    + _G_KET.format(a="'CRM_CHUAN_LAP'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_gui(p_khoa text, p_h text, p_pb uuid, p_token text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; w uuid;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_CHUAN_GUI_DUYET', p_pb);""" + _G_REPLAY.format(a="'CRM_CHUAN_GUI_DUYET'") + """
            PERFORM 1 FROM master.crm_bo_chuan b WHERE b.id = (SELECT bo_chuan_id FROM master.crm_bo_chuan_phien_ban WHERE id = p_pb) FOR SHARE;
            SELECT * INTO v FROM master.crm_bo_chuan_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_CHUAN + """
            IF v.trang_thai <> 'DRAFT' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: chỉ gửi duyệt bộ chuẩn DRAFT (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                VALUES (d.pn, 'V4', 'CRM_CHUAN', 'CRM', 'master.crm_bo_chuan_phien_ban', v.id, 'CFO', 'Bộ chuẩn dự án chờ CFO duyệt', '{}') RETURNING id INTO w;
            UPDATE master.crm_bo_chuan_phien_ban SET trang_thai = 'CHO_CFO', viec_id = w, gui_boi = ai, gui_luc = now(), cap_nhat_luc = clock_timestamp()
                WHERE id = v.id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_bo_chuan_phien_ban'", id="v.id", hd="'CRM_CHUAN_GUI_DUYET'",
                               sau="jsonb_build_object('viec_id', w)", ly="NULL") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'CHO_CFO', 'viec_id', w);""" + _G_KET.format(a="'CRM_CHUAN_GUI_DUYET'") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_duyet(p_khoa text, p_h text, p_pb uuid, p_token text, p_valid_from date) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _G_KHAI + """ v record; cuoi date; truoc uuid;
        BEGIN""" + _G_CHU + """
            SELECT * INTO d FROM master.crm_g_dich('CRM_CHUAN_DUYET_V4', p_pb);""" + _G_REPLAY.format(a="'CRM_CHUAN_DUYET_V4'") + """
            PERFORM 1 FROM master.crm_bo_chuan b WHERE b.id = (SELECT bo_chuan_id FROM master.crm_bo_chuan_phien_ban WHERE id = p_pb) FOR UPDATE;
            SELECT * INTO v FROM master.crm_bo_chuan_phien_ban WHERE id = p_pb FOR UPDATE;""" + _G_TOKEN_CHUAN + """
            IF v.trang_thai <> 'CHO_CFO' THEN
                RAISE EXCEPTION 'CRM_G_TRANG_THAI: chỉ duyệt bộ chuẩn CHO_CFO (hiện %)', v.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF v.gui_boi = ai THEN
                RAISE EXCEPTION 'CRM_G_CUNG_NGUOI: người duyệt phải khác người lập/gửi' USING ERRCODE = 'P0001';
            END IF;
            IF p_valid_from IS NULL THEN
                RAISE EXCEPTION 'CRM_G_THIEU_NGAY: cần ngày hiệu lực' USING ERRCODE = 'P0001';
            END IF;
            SELECT max(valid_from) INTO cuoi FROM master.crm_bo_chuan_phien_ban WHERE bo_chuan_id = v.bo_chuan_id AND trang_thai = 'HIEU_LUC';
            IF cuoi IS NOT NULL AND p_valid_from <= cuoi THEN
                RAISE EXCEPTION 'CRM_G_HIEU_LUC_CHONG: ngày hiệu lực phải sau bộ chuẩn đã duyệt gần nhất (%)', cuoi USING ERRCODE = 'P0001';
            END IF;
            UPDATE master.crm_bo_chuan_phien_ban SET valid_to = p_valid_from, cap_nhat_luc = clock_timestamp()
                WHERE bo_chuan_id = v.bo_chuan_id AND trang_thai = 'HIEU_LUC' AND valid_to IS NULL RETURNING id INTO truoc;
            UPDATE master.crm_bo_chuan_phien_ban SET trang_thai = 'HIEU_LUC', valid_from = p_valid_from, duyet_boi = ai, duyet_luc = now(),
                   cap_nhat_luc = clock_timestamp() WHERE id = v.id;
            UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET', duyet_boi = ai, duyet_luc = now(), cap_nhat_luc = now()
                WHERE id = v.viec_id AND trang_thai = 'CHO_DUYET';
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_bo_chuan_phien_ban'", id="v.id", hd="'CRM_CHUAN_DUYET_V4'",
                               sau="jsonb_build_object('valid_from', p_valid_from, 'dong_phien_ban', truoc)", ly="NULL") + """
            kq := jsonb_build_object('phien_ban_id', v.id, 'trang_thai', 'HIEU_LUC', 'valid_from', p_valid_from, 'dong_phien_ban_truoc', truoc);"""
    + _G_KET.format(a="'CRM_CHUAN_DUYET_V4'") + """
        END $$""",
    # đọc bộ chuẩn hiệu lực theo dự án/giai đoạn/ngày: quyền CRM hiện hành; không có → CHUA_CO (không “lệch”, không sinh lịch thu)
    """CREATE OR REPLACE FUNCTION master.crm_g_chuan_doc(p_du_an uuid, p_giai_doan text, p_as_of date) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE pn uuid; v record;
        BEGIN""" + _G_CHU + """
            SELECT a.phap_nhan_id INTO pn FROM master.du_an a WHERE a.id = p_du_an;
            IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy dự án (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            SELECT p.* INTO v FROM master.crm_bo_chuan_phien_ban p JOIN master.crm_bo_chuan b ON b.id = p.bo_chuan_id
                WHERE b.phap_nhan_id = pn AND b.du_an_id = p_du_an AND b.giai_doan = p_giai_doan AND p.trang_thai = 'HIEU_LUC'
                  AND p.valid_from <= p_as_of AND (p.valid_to IS NULL OR p_as_of < p.valid_to)
                ORDER BY p.valid_from DESC LIMIT 1;
            IF v.id IS NULL THEN
                RETURN jsonb_build_object('trang_thai', 'CHUA_CO', 'version', NULL, 'rows', '[]'::jsonb,
                                          'cot', jsonb_build_array('Lần', 'Giá trị', 'Mốc thời gian', 'Ghi chú'));
            END IF;
            RETURN jsonb_build_object('trang_thai', 'HIEU_LUC',
                'version', jsonb_build_object('id', v.id, 'phien_ban', v.phien_ban, 'valid_from', v.valid_from, 'valid_to', v.valid_to),
                'cot', jsonb_build_array('Lần', 'Giá trị', 'Mốc thời gian', 'Ghi chú'),
                'rows', (SELECT coalesce(jsonb_agg(jsonb_build_object('thu_tu', r.thu_tu, 'lan', r.lan, 'gia_tri_loai', r.gia_tri_loai,
                                 'gia_tri_thap_phan', r.gia_tri_thap_phan, 'so_tien_minor', r.so_tien_minor, 'tien_te', r.tien_te, 'moc_loai', r.moc_loai,
                                 'moc_ngay', r.moc_ngay, 'moc_su_kien', r.moc_su_kien, 'ghi_chu', r.ghi_chu) ORDER BY r.thu_tu), '[]'::jsonb)
                         FROM master.crm_bo_chuan_dong r WHERE r.phien_ban_id = v.id));
        END $$""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm lệnh không cấp PUBLIC
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _G_BANG_MOI),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON master.crm_danh_muc_truong, master.phan_cong_hanh_dong, master.crm_mau, master.crm_mau_tep, '
                               'master.crm_mau_phien_ban, master.crm_mau_anh_xa, master.crm_mau_kiem_tra, master.crm_bo_chuan, master.crm_bo_chuan_phien_ban, '
                               'master.crm_bo_chuan_dong, master.crm_g_bien_nhan FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    """REVOKE ALL ON master.crm_danh_muc_truong, master.phan_cong_hanh_dong, master.crm_mau, master.crm_mau_tep, master.crm_mau_phien_ban,
        master.crm_mau_anh_xa, master.crm_mau_kiem_tra, master.crm_bo_chuan, master.crm_bo_chuan_phien_ban, master.crm_bo_chuan_dong,
        master.crm_g_bien_nhan FROM PUBLIC""",
    """REVOKE EXECUTE ON FUNCTION master.crm_g_ai_id(), master.crm_g_dich(text, uuid), master.crm_g_bn_tra(uuid, text, text, text),
        master.crm_g_bn_ghi(uuid, text, text, text, jsonb), master.crm_g_ghim_quyen(uuid), master.crm_g_tra(text, text, uuid, text), master.crm_g_danh_muc_digest(uuid, text, integer),
        master.crm_g_mau_token(uuid), master.crm_g_chuan_token(uuid),
        master.crm_g_mau_tai(text, text, uuid, text, text, text, bigint, text, jsonb, text, text),
        master.crm_g_mau_anh_xa(text, text, uuid, text, jsonb), master.crm_g_mau_gui_kiem(text, text, uuid, text),
        master.crm_g_mau_kiem(text, text, uuid, text), master.crm_g_mau_tra_lai(text, text, uuid, text, text),
        master.crm_g_mau_duyet(text, text, uuid, text, date), master.crm_g_mau_tu_choi(text, text, uuid, text, text),
        master.crm_g_chuan_lap(text, text, uuid, text, jsonb), master.crm_g_chuan_gui(text, text, uuid, text),
        master.crm_g_chuan_duyet(text, text, uuid, text, date), master.crm_g_chuan_doc(uuid, text, date) FROM PUBLIC""",
)

PG_MIGRATIONS = (*PG_MIGRATIONS, M0018_CRM_G)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0019 — M4-02A Review L1/L2 hữu hạn (APPEND sau toàn bộ actual 1–18; không sửa byte/định nghĩa/checksum 1–18, không bật lineage legacy M9).
#        Định nghĩa trong m4/sql_review.py (chỉ hằng SQL): review_run/result/artifact/manual_map + quyền SOAN|REVIEW theo phạm vi + biên nhận.
# ---------------------------------------------------------------------------
from ..m4.sql_review import M0019_M4_REVIEW  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

PG_MIGRATIONS = (*PG_MIGRATIONS, M0019_M4_REVIEW)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0020 — M4-02A FIX04 corrective (APPEND sau 1–19; M19 đã áp dụng ở DB DEMO, giữ nguyên byte/checksum): thay đúng m4.review_quyen không tham
#        chiếu record đợt chưa gán khi không có đợt (SQLSTATE 55000). Chỉ CREATE OR REPLACE một hàm; không bảng/quyền/schema khác.
# ---------------------------------------------------------------------------
from ..m4.sql_review import M0020_M4_REVIEW_QUYEN  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

PG_MIGRATIONS = (*PG_MIGRATIONS, M0020_M4_REVIEW_QUYEN)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0021 — CRM-41-03 G2 Báo giá → G3 Soạn hợp đồng từ mẫu (APPEND sau toàn bộ 1–20; không sửa byte/định nghĩa/checksum 1–20).
#        Báo giá có revision bất biến (dữ liệu nhập tay typed + kết quả kiểm do máy chủ tính + snapshot G7 đọc trong CÙNG giao dịch RR);
#        chuyển sang Soạn tạo/liên kết đúng MỘT master.hop_dong (discriminator crm_giao_ket SOAN_THAO/CHO_KY, không qua enum/trigger cũ,
#        không _tao_phien_ban của luồng B); bản soạn có revision bất biến ghim mẫu/ánh xạ/lần kiểm/raw/danh mục/profile; lần xuất/in ghi
#        bất biến (DOCX+PDF H/len, trạng thái PDF trung thực). Mọi lệnh là hàm INVOKER chỉ chạy trên kết nối CHỦ BẢNG, quyền HIỆN HÀNH
#        kiểm TRƯỚC biên nhận (dùng lại biên nhận/ghim quyền của M0018). Không sinh nghĩa vụ/lịch thu/M1/duyệt.
# ---------------------------------------------------------------------------
_GK_BANG_MOI = ("crm_bao_gia_dieu_khoan", "crm_bao_gia", "crm_bao_gia_rev", "crm_hd_soan", "crm_hd_soan_rev", "crm_gk_xuat", "crm_gk_lan")
_GK_KHAI = "ai text := master.ktt_danh_tinh(); d record; cu jsonb; kq jsonb;"
# FIX01 #6: ghim dòng quyền của phiên (FOR SHARE) TRONG CÙNG giao dịch, TRƯỚC kiểm đích/quyền và trước chờ khóa namespace của biên nhận —
# thu hồi không commit lọt giữa kiểm và hiệu ứng/FINAL (cùng kỷ luật crm_g_tra của M0018).
_GK_GHIM = "\n            PERFORM master.crm_g_ghim_quyen(master.crm_gk_pn({h}, {x}));"
_GK_SHA = "encode(sha256(convert_to({x}::text, 'UTF8')), 'hex')"

M0021_CRM_G2G3 = (
    "SET LOCAL check_function_bodies = off",
    # --- điều khoản tham chiếu in báo giá đã khai theo loại hình (chủ CSDL khai; bất biến). Thiếu → in báo giá báo thiếu, không bịa.
    """CREATE TABLE master.crm_bao_gia_dieu_khoan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        loai_hinh_id uuid NOT NULL,
        ma text NOT NULL CHECK (ma ~ '^[A-Z0-9_]{1,60}$'),
        noi_dung text NOT NULL CHECK (length(noi_dung) BETWEEN 1 AND 4000 AND noi_dung !~ '[[:cntrl:]]'),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (loai_hinh_id, ma))""",
    "CREATE TRIGGER crm_bao_gia_dieu_khoan_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bao_gia_dieu_khoan FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- báo giá (gốc có vòng đời NHAP → DA_CHUYEN | HUY) + revision bất biến
    """CREATE TABLE master.crm_bao_gia (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        loai_hinh_id uuid NOT NULL,
        so_bao_gia text NOT NULL CHECK (so_bao_gia ~ '^BG-[0-9]{4}-[0-9]{5}$'),
        ngay date NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        trang_thai text NOT NULL CHECK (trang_thai IN ('NHAP','DA_CHUYEN','HUY')),
        revision_hien_hanh integer NOT NULL CHECK (revision_hien_hanh >= 1),
        hop_dong_id uuid REFERENCES master.hop_dong(id),
        huy_ly_do text CHECK (huy_ly_do IS NULL OR length(huy_ly_do) BETWEEN 1 AND 1000),
        huy_boi text,
        huy_luc timestamptz,
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (phap_nhan_id, so_bao_gia),
        UNIQUE (id, phap_nhan_id),
        UNIQUE (hop_dong_id),
        CHECK ((trang_thai = 'DA_CHUYEN') = (hop_dong_id IS NOT NULL)),
        CHECK ((trang_thai = 'HUY') = (huy_ly_do IS NOT NULL AND huy_boi IS NOT NULL AND huy_luc IS NOT NULL)))""",
    """CREATE OR REPLACE FUNCTION master.crm_bao_gia_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: báo giá chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa báo giá (giữ lịch sử)' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'NHAP' OR NEW.revision_hien_hanh <> 1 THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: báo giá mới phải là NHAP revision 1' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.loai_hinh_id, NEW.so_bao_gia, NEW.ngay, NEW.tao_boi, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.loai_hinh_id, OLD.so_bao_gia, OLD.ngay, OLD.tao_boi, OLD.tao_luc) THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không sửa định danh báo giá' USING ERRCODE = 'P0001';
            END IF;
            IF OLD.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: báo giá đã chuyển/hủy là trạng thái cuối' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.revision_hien_hanh < OLD.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: revision báo giá không lùi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_bao_gia_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bao_gia FOR EACH ROW EXECUTE FUNCTION master.crm_bao_gia_kiem()",
    """CREATE TABLE master.crm_bao_gia_rev (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        bao_gia_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        du_an_id uuid,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        du_lieu jsonb NOT NULL CHECK (jsonb_typeof(du_lieu) = 'object'),
        du_lieu_sha256 text NOT NULL CHECK (du_lieu_sha256 ~ '^[0-9a-f]{64}$'),
        tinh jsonb NOT NULL CHECK (jsonb_typeof(tinh) = 'object'),
        g7 jsonb CHECK (g7 IS NULL OR jsonb_typeof(g7) = 'object'),
        g7_sha256 text CHECK (g7_sha256 IS NULL OR g7_sha256 ~ '^[0-9a-f]{64}$'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (bao_gia_id, phap_nhan_id) REFERENCES master.crm_bao_gia (id, phap_nhan_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (bao_gia_id, revision),
        UNIQUE (id, bao_gia_id),
        CHECK ((g7 IS NULL) = (g7_sha256 IS NULL)))""",
    "CREATE TRIGGER crm_bao_gia_rev_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_bao_gia_rev FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- discriminator rõ cho hợp đồng soạn từ mẫu (cột mới; hàng cũ NULL → giữ nguyên ngữ nghĩa B/M4/M9). Không thêm giá trị vào enum/trigger cũ.
    """ALTER TABLE master.hop_dong ADD COLUMN crm_giao_ket text CHECK (crm_giao_ket IS NULL OR crm_giao_ket IN ('SOAN_THAO','CHO_KY'))""",
    """CREATE OR REPLACE FUNCTION master.hop_dong_gk_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND OLD.crm_giao_ket IS NULL AND NEW.crm_giao_ket IS NULL THEN
                RETURN NEW;
            END IF;
            IF TG_OP = 'INSERT' AND NEW.crm_giao_ket IS NULL THEN
                RETURN NEW;
            END IF;
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: hợp đồng soạn từ mẫu chỉ ghi qua hàm lệnh G2/G3 trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' AND (OLD.crm_giao_ket IS NULL OR NEW.crm_giao_ket IS NULL) THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không chuyển hợp đồng cũ thành bản soạn hoặc bỏ discriminator' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' AND NEW.crm_giao_ket <> 'SOAN_THAO' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: hợp đồng soạn mới phải ở SOAN_THAO' USING ERRCODE = 'P0001';
            END IF;
            IF NEW.trang_thai IS DISTINCT FROM NEW.crm_giao_ket OR NEW.phien_ban_hien_hanh IS NOT NULL OR NEW.module_chu IS NOT NULL THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: bản soạn chưa ký — không hiệu lực/không phiên bản duyệt/không thuộc M4' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hop_dong_gk_kiem BEFORE INSERT OR UPDATE ON master.hop_dong FOR EACH ROW EXECUTE FUNCTION master.hop_dong_gk_kiem()",
    # --- bản soạn (một-một với master.hop_dong và với báo giá nguồn) + revision bất biến ghim mẫu/ánh xạ/kiểm/raw/danh mục/profile
    """CREATE TABLE master.crm_hd_soan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL UNIQUE,
        bao_gia_id uuid NOT NULL UNIQUE,
        bao_gia_revision integer NOT NULL CHECK (bao_gia_revision >= 1),
        loai_hinh_id uuid NOT NULL,
        revision_hien_hanh integer NOT NULL CHECK (revision_hien_hanh >= 1),
        trang_thai text NOT NULL CHECK (trang_thai IN ('SOAN_THAO','CHO_KY')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (bao_gia_id, phap_nhan_id) REFERENCES master.crm_bao_gia (id, phap_nhan_id),
        FOREIGN KEY (bao_gia_id, bao_gia_revision) REFERENCES master.crm_bao_gia_rev (bao_gia_id, revision),
        FOREIGN KEY (loai_hinh_id, phap_nhan_id) REFERENCES master.loai_hinh_doanh_thu (id, phap_nhan_id),
        UNIQUE (id, phap_nhan_id))""",
    """CREATE OR REPLACE FUNCTION master.crm_hd_soan_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: bản soạn chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa bản soạn' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'SOAN_THAO' OR NEW.revision_hien_hanh <> 1 THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: bản soạn mới phải SOAN_THAO revision 1' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF ROW(NEW.id, NEW.phap_nhan_id, NEW.hop_dong_id, NEW.bao_gia_id, NEW.bao_gia_revision, NEW.loai_hinh_id, NEW.tao_boi, NEW.tao_luc)
               IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.hop_dong_id, OLD.bao_gia_id, OLD.bao_gia_revision, OLD.loai_hinh_id, OLD.tao_boi, OLD.tao_luc)
               OR NEW.revision_hien_hanh < OLD.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không sửa định danh/nguồn bản soạn, revision không lùi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_hd_soan_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_hd_soan FOR EACH ROW EXECUTE FUNCTION master.crm_hd_soan_kiem()",
    """CREATE TABLE master.crm_hd_soan_rev (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        soan_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        nguon text NOT NULL CHECK (nguon = 'MAU'),
        mau_phien_ban_id uuid NOT NULL,
        anh_xa_id uuid NOT NULL,
        kiem_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        facts_sha256 text NOT NULL CHECK (facts_sha256 ~ '^[0-9a-f]{64}$'),
        ban_do_sha256 text NOT NULL CHECK (ban_do_sha256 ~ '^[0-9a-f]{64}$'),
        danh_muc_ref text NOT NULL,
        danh_muc_rev integer NOT NULL,
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ '^[0-9a-f]{64}$'),
        profile_phien_ban integer NOT NULL,
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ '^[0-9a-f]{64}$'),
        renderer text NOT NULL CHECK (length(renderer) BETWEEN 1 AND 80),
        du_lieu jsonb NOT NULL CHECK (jsonb_typeof(du_lieu) = 'object'),
        du_lieu_sha256 text NOT NULL CHECK (du_lieu_sha256 ~ '^[0-9a-f]{64}$'),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) <= 1000),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (soan_id, phap_nhan_id) REFERENCES master.crm_hd_soan (id, phap_nhan_id),
        FOREIGN KEY (mau_phien_ban_id, phap_nhan_id) REFERENCES master.crm_mau_phien_ban (id, phap_nhan_id),
        FOREIGN KEY (anh_xa_id, mau_phien_ban_id) REFERENCES master.crm_mau_anh_xa (id, phien_ban_id),
        FOREIGN KEY (kiem_id, mau_phien_ban_id) REFERENCES master.crm_mau_kiem_tra (id, phien_ban_id),
        UNIQUE (soan_id, revision),
        UNIQUE (id, soan_id))""",
    "CREATE TRIGGER crm_hd_soan_rev_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_hd_soan_rev FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- lần in báo giá / xuất hợp đồng đã CÔNG BỐ (thành công hoặc PDF chưa sẵn sàng/lỗi/cũ — trung thực; DOCX luôn giữ). Bất biến.
    """CREATE TABLE master.crm_gk_xuat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        loai text NOT NULL CHECK (loai IN ('BAO_GIA','HOP_DONG')),
        bao_gia_id uuid,
        soan_id uuid,
        revision integer NOT NULL CHECK (revision >= 1),
        input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
        docx_sha256 text NOT NULL CHECK (docx_sha256 ~ '^[0-9a-f]{64}$'),
        docx_len bigint NOT NULL CHECK (docx_len > 0),
        pdf_sha256 text CHECK (pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$'),
        pdf_len bigint CHECK (pdf_len IS NULL OR pdf_len > 0),
        trang_thai text NOT NULL CHECK (trang_thai IN ('PDF_DAT','PDF_CHUA_SAN_SANG','PDF_LOI','DA_CU')),
        engine text NOT NULL CHECK (length(engine) BETWEEN 1 AND 200),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) <= 2000),
        kiem_pdf jsonb NOT NULL CHECK (jsonb_typeof(kiem_pdf) = 'object'),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (bao_gia_id, phap_nhan_id) REFERENCES master.crm_bao_gia (id, phap_nhan_id),
        FOREIGN KEY (soan_id, phap_nhan_id) REFERENCES master.crm_hd_soan (id, phap_nhan_id),
        CHECK ((loai = 'BAO_GIA') = (bao_gia_id IS NOT NULL AND soan_id IS NULL)),
        CHECK ((loai = 'HOP_DONG') = (soan_id IS NOT NULL AND bao_gia_id IS NULL)),
        CHECK ((trang_thai = 'PDF_DAT') = (pdf_sha256 IS NOT NULL)),
        CHECK ((pdf_sha256 IS NULL) = (pdf_len IS NULL)))""",
    "CREATE TRIGGER crm_gk_xuat_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_gk_xuat FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # --- FIX01 #5: đặt chỗ BỀN của một lần in/xuất (ý định + chủ + pha + ảnh chụp input + định danh lần chạy) ghi dưới khóa namespace TRƯỚC khi
    # nhả giao dịch pha A; render (pha B) chỉ chạy cho lần vừa đặt; cùng khóa/H thấy lần cũ → đối soát, không render mù/UUID mới/Word mới.
    """CREATE TABLE master.crm_gk_lan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        hanh_dong text NOT NULL CHECK (hanh_dong IN ('CRM_BAO_GIA_IN','CRM_SOAN_XUAT')),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{1,200}$'),
        yeu_cau_sha256 text NOT NULL CHECK (yeu_cau_sha256 ~ '^[0-9a-f]{64}$'),
        dich_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DANG_RENDER','DA_CONG_BO')),
        xuat_id uuid REFERENCES master.crm_gk_xuat(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
        UNIQUE (phap_nhan_id, nguoi_dung_id, hanh_dong, khoa),
        CHECK ((trang_thai = 'DA_CONG_BO') = (xuat_id IS NOT NULL)))""",
    """CREATE OR REPLACE FUNCTION master.crm_gk_lan_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_G_CHI_CHU: lần in/xuất chỉ ghi qua hàm lệnh trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: không xóa lần in/xuất' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.trang_thai <> 'DANG_RENDER' THEN
                    RAISE EXCEPTION 'CRM_G_BAT_BIEN: lần mới phải DANG_RENDER' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.trang_thai <> 'DANG_RENDER' OR NEW.trang_thai <> 'DA_CONG_BO'
               OR ROW(NEW.id, NEW.phap_nhan_id, NEW.nguoi_dung_id, NEW.hanh_dong, NEW.khoa, NEW.yeu_cau_sha256, NEW.dich_id, NEW.revision, NEW.input_sha256, NEW.tao_luc)
                  IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.nguoi_dung_id, OLD.hanh_dong, OLD.khoa, OLD.yeu_cau_sha256, OLD.dich_id, OLD.revision,
                                       OLD.input_sha256, OLD.tao_luc) THEN
                RAISE EXCEPTION 'CRM_G_BAT_BIEN: lần in/xuất chỉ chuyển DANG_RENDER → DA_CONG_BO một lần' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_gk_lan_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_gk_lan FOR EACH ROW EXECUTE FUNCTION master.crm_gk_lan_kiem()",
    # ======================================================================= quyền HIỆN HÀNH G2/G3 (bán hàng/kế toán/KTT trên PN có module CRM,
    # hoặc phân công hành động chung). Không vai mới, không IAM thứ hai.
    """CREATE OR REPLACE FUNCTION master.crm_gk_duoc(p_nhom text, p_pn uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT p_nhom IN ('CRM_BAO_GIA','CRM_SOAN') AND master.ktt_duoc(p_pn, 'CRM')
               AND (master.ktt_co_vai(p_pn, ARRAY['BAN_HANG','KE_TOAN','KE_TOAN_TRUONG'], NULL)
                    OR master.ktt_hanh_dong_duoc(p_pn, 'CRM', p_nhom, NULL))
        $$""",
    """CREATE OR REPLACE FUNCTION master.crm_gk_dich(p_hanh_dong text, p_dich uuid, OUT pn uuid, OUT loai uuid)
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE nhom text;
        BEGIN
            IF p_hanh_dong = 'CRM_BAO_GIA_TAO' THEN
                SELECT l.phap_nhan_id, l.id INTO pn, loai FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich AND l.valid_to IS NULL;
                nhom := 'CRM_BAO_GIA';
            ELSIF p_hanh_dong IN ('CRM_BAO_GIA_LUU','CRM_BAO_GIA_HUY','CRM_BAO_GIA_IN','CRM_BAO_GIA_CHUYEN') THEN
                SELECT b.phap_nhan_id, b.loai_hinh_id INTO pn, loai FROM master.crm_bao_gia b WHERE b.id = p_dich;
                nhom := 'CRM_BAO_GIA';
            ELSIF p_hanh_dong IN ('CRM_SOAN_LUU','CRM_SOAN_XUAT') THEN
                SELECT s.phap_nhan_id, s.loai_hinh_id INTO pn, loai FROM master.crm_hd_soan s WHERE s.id = p_dich;
                nhom := 'CRM_SOAN';
            ELSE
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy đối tượng (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_gk_duoc(nhom, pn) OR (p_hanh_dong = 'CRM_BAO_GIA_CHUYEN' AND NOT master.crm_gk_duoc('CRM_SOAN', pn)) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền hiện hành cho %', p_hanh_dong USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    # tra biên nhận TRƯỚC mọi tính/đọc kho/render: ghim quyền → đích + quyền hiện hành → biên nhận (cùng H → FINAL cũ; khác H → 409)
    """CREATE OR REPLACE FUNCTION master.crm_gk_tra(p_hanh_dong text, p_khoa text, p_dich uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE d record; cu jsonb; pn_tam uuid;
        BEGIN""" + _G_CHU + """
            pn_tam := CASE WHEN p_hanh_dong = 'CRM_BAO_GIA_TAO' THEN (SELECT l.phap_nhan_id FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich)
                           WHEN left(p_hanh_dong, 12) = 'CRM_BAO_GIA_' THEN (SELECT b.phap_nhan_id FROM master.crm_bao_gia b WHERE b.id = p_dich)
                           ELSE (SELECT s.phap_nhan_id FROM master.crm_hd_soan s WHERE s.id = p_dich) END;
            PERFORM master.crm_g_ghim_quyen(pn_tam);
            SELECT * INTO d FROM master.crm_gk_dich(p_hanh_dong, p_dich);
            cu := master.crm_g_bn_tra(d.pn, p_hanh_dong, p_khoa, p_h);
            RETURN CASE WHEN cu IS NULL THEN NULL ELSE jsonb_build_object('lap_lai', true, 'ket_qua', cu) END;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_gk_pn(p_hanh_dong text, p_dich uuid) RETURNS uuid
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT CASE WHEN p_hanh_dong = 'CRM_BAO_GIA_TAO' THEN (SELECT l.phap_nhan_id FROM master.loai_hinh_doanh_thu l WHERE l.id = p_dich)
                    WHEN left(p_hanh_dong, 12) = 'CRM_BAO_GIA_' THEN (SELECT b.phap_nhan_id FROM master.crm_bao_gia b WHERE b.id = p_dich)
                    ELSE (SELECT s.phap_nhan_id FROM master.crm_hd_soan s WHERE s.id = p_dich) END
        $$""",
    # FIX01 #5: đặt chỗ lần in/xuất (READ COMMITTED, dưới khóa namespace của biên nhận): FINAL có → trả FINAL; lần đã đặt cùng H → trả lần cũ để
    # ĐỐI SOÁT (không render lại); khác H → 409; chưa có → kiểm revision hiện hành = revision đã chụp rồi ghi lần DANG_RENDER.
    """CREATE OR REPLACE FUNCTION master.crm_gk_dat_lan(p_hanh_dong text, p_khoa text, p_dich uuid, p_h text, p_revision integer, p_input_sha text)
        RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE d record; cu jsonb; lan record; lid uuid; rv integer;
        BEGIN""" + _G_CHU + """
            IF p_hanh_dong NOT IN ('CRM_BAO_GIA_IN','CRM_SOAN_XUAT') THEN
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;""" + _GK_GHIM.format(h="p_hanh_dong", x="p_dich") + """
            SELECT * INTO d FROM master.crm_gk_dich(p_hanh_dong, p_dich);
            cu := master.crm_g_bn_tra(d.pn, p_hanh_dong, p_khoa, p_h);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;
            SELECT * INTO lan FROM master.crm_gk_lan WHERE phap_nhan_id = d.pn AND nguoi_dung_id = master.crm_g_ai_id() AND hanh_dong = p_hanh_dong
                AND khoa = p_khoa FOR UPDATE;
            IF lan.id IS NOT NULL THEN
                IF lan.yeu_cau_sha256 <> p_h THEN
                    RAISE EXCEPTION 'CRM_G_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
                END IF;
                RETURN jsonb_build_object('lan_id', lan.id, 'moi', false, 'trang_thai', lan.trang_thai, 'revision', lan.revision, 'input_sha256', lan.input_sha256);
            END IF;
            rv := CASE WHEN p_hanh_dong = 'CRM_BAO_GIA_IN' THEN (SELECT b.revision_hien_hanh FROM master.crm_bao_gia b WHERE b.id = p_dich)
                       ELSE (SELECT s.revision_hien_hanh FROM master.crm_hd_soan s WHERE s.id = p_dich) END;
            IF rv IS DISTINCT FROM p_revision THEN
                RAISE EXCEPTION 'CRM_GK_REVISION_CU: đối tượng đã có revision mới — tải lại rồi thao tác' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_gk_lan (phap_nhan_id, nguoi_dung_id, hanh_dong, khoa, yeu_cau_sha256, dich_id, revision, input_sha256, trang_thai)
                VALUES (d.pn, master.crm_g_ai_id(), p_hanh_dong, p_khoa, p_h, p_dich, p_revision, p_input_sha, 'DANG_RENDER') RETURNING id INTO lid;
            RETURN jsonb_build_object('lan_id', lid, 'moi', true, 'trang_thai', 'DANG_RENDER', 'revision', p_revision, 'input_sha256', p_input_sha);
        END $$""",
    # ======================================================================= G2 lệnh báo giá
    # lưu nháp: tạo (p_bao_gia NULL) hoặc revision mới (CAS revision). Dự án/đối tác phải cùng PN (đối tác có mã Junsky hiện hành của PN);
    # G7 (nếu chọn theo dự án) đọc LẠI trong cùng giao dịch và phải BẰNG snapshot máy chủ đã dùng để tính (không tin trình duyệt).
    """CREATE OR REPLACE FUNCTION master.crm_gk_bao_gia_luu(p_khoa text, p_h text, p_bao_gia uuid, p_loai uuid, p_expected integer, p_du_an uuid,
                                                         p_doi_tac uuid, p_du_lieu jsonb, p_tinh jsonb, p_g7_du_an uuid, p_g7_giai_doan text,
                                                         p_g7_as_of date, p_g7 jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ b record; n integer; so text; nam text; g7 jsonb; hanh text;
        BEGIN""" + _G_CHU + """
            hanh := CASE WHEN p_bao_gia IS NULL THEN 'CRM_BAO_GIA_TAO' ELSE 'CRM_BAO_GIA_LUU' END;""" + _GK_GHIM.format(h="hanh", x="coalesce(p_bao_gia, p_loai)") + """
            SELECT * INTO d FROM master.crm_gk_dich(hanh, coalesce(p_bao_gia, p_loai));""" + _G_REPLAY.format(a="hanh") + """
            IF p_du_lieu IS NULL OR jsonb_typeof(p_du_lieu) <> 'object' OR p_tinh IS NULL OR jsonb_typeof(p_tinh) <> 'object' THEN
                RAISE EXCEPTION 'CRM_GK_YEU_CAU_SAI: dữ liệu báo giá phải là object' USING ERRCODE = 'P0001';
            END IF;
            IF p_du_an IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.du_an a WHERE a.id = p_du_an AND a.phap_nhan_id = d.pn) THEN
                RAISE EXCEPTION 'CRM_GK_PHAM_VI: dự án không thuộc pháp nhân của báo giá' USING ERRCODE = 'P0001';
            END IF;
            IF p_doi_tac IS NOT NULL AND NOT EXISTS (SELECT 1 FROM master.doi_tac_ma_junsky m WHERE m.doi_tac_id = p_doi_tac AND m.phap_nhan_id = d.pn
                                                       AND m.valid_to IS NULL) THEN
                RAISE EXCEPTION 'CRM_GK_PHAM_VI: khách hàng không có mã hiện hành trong pháp nhân của báo giá' USING ERRCODE = 'P0001';
            END IF;
            IF p_g7_du_an IS NOT NULL THEN
                IF p_g7_du_an IS DISTINCT FROM p_du_an THEN
                    RAISE EXCEPTION 'CRM_GK_PHAM_VI: bộ chuẩn phải thuộc đúng dự án của báo giá' USING ERRCODE = 'P0001';
                END IF;
                g7 := master.crm_g_chuan_doc(p_g7_du_an, p_g7_giai_doan, p_g7_as_of);
                IF g7 IS DISTINCT FROM p_g7 THEN
                    RAISE EXCEPTION 'CRM_GK_G7_DOI: bộ chuẩn đã đổi trong lúc lưu — tải lại rồi lưu' USING ERRCODE = 'P0001';
                END IF;
                g7 := g7 || jsonb_build_object('du_an_id', p_g7_du_an, 'giai_doan', p_g7_giai_doan, 'as_of', p_g7_as_of);
            END IF;
            IF p_bao_gia IS NULL THEN
                nam := to_char(master.ktt_ngay(), 'YYYY');
                PERFORM pg_advisory_xact_lock(hashtextextended('crm_gk_so|' || d.pn::text || '|' || nam, 0));
                SELECT count(*) + 1 INTO n FROM master.crm_bao_gia WHERE phap_nhan_id = d.pn AND so_bao_gia LIKE 'BG-' || nam || '-%';
                so := 'BG-' || nam || '-' || lpad(n::text, 5, '0');
                INSERT INTO master.crm_bao_gia (phap_nhan_id, loai_hinh_id, so_bao_gia, ngay, tao_boi, trang_thai, revision_hien_hanh)
                    VALUES (d.pn, d.loai, so, master.ktt_ngay(), ai, 'NHAP', 1) RETURNING * INTO b;
                n := 1;
            ELSE
                SELECT * INTO b FROM master.crm_bao_gia WHERE id = p_bao_gia FOR UPDATE;
                IF b.trang_thai <> 'NHAP' THEN
                    RAISE EXCEPTION 'CRM_GK_TRANG_THAI: báo giá % không còn sửa', b.trang_thai USING ERRCODE = 'P0001';
                END IF;
                IF p_expected IS DISTINCT FROM b.revision_hien_hanh THEN
                    RAISE EXCEPTION 'CRM_GK_REVISION_CU: báo giá đã có revision mới — tải lại rồi lưu' USING ERRCODE = 'P0001';
                END IF;
                IF p_loai IS DISTINCT FROM b.loai_hinh_id THEN
                    RAISE EXCEPTION 'CRM_GK_PHAM_VI: không đổi loại hình của báo giá đã tạo' USING ERRCODE = 'P0001';
                END IF;
                n := b.revision_hien_hanh + 1;
                UPDATE master.crm_bao_gia SET revision_hien_hanh = n, cap_nhat_luc = clock_timestamp() WHERE id = b.id;
            END IF;
            INSERT INTO master.crm_bao_gia_rev (bao_gia_id, phap_nhan_id, revision, du_an_id, doi_tac_id, du_lieu, du_lieu_sha256, tinh, g7, g7_sha256, tao_boi)
                VALUES (b.id, d.pn, n, p_du_an, p_doi_tac, p_du_lieu, """ + _GK_SHA.format(x="p_du_lieu") + """, p_tinh, g7,
                        CASE WHEN g7 IS NULL THEN NULL ELSE """ + _GK_SHA.format(x="g7") + """ END, ai);
            """ + _G_NK.format(pn="d.pn", loai="'SUA_DANH_MUC'", bang="'master.crm_bao_gia'", id="b.id", hd="hanh",
                               sau="jsonb_build_object('so_bao_gia', b.so_bao_gia, 'revision', n)", ly="NULL") + """
            kq := jsonb_build_object('bao_gia_id', b.id, 'so_bao_gia', b.so_bao_gia, 'revision', n, 'trang_thai', 'NHAP');""" + _G_KET.format(a="hanh") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_gk_bao_gia_huy(p_khoa text, p_h text, p_bao_gia uuid, p_expected integer, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ b record;
        BEGIN""" + _G_CHU + _GK_GHIM.format(h="'CRM_BAO_GIA_HUY'", x="p_bao_gia") + """
            SELECT * INTO d FROM master.crm_gk_dich('CRM_BAO_GIA_HUY', p_bao_gia);""" + _G_REPLAY.format(a="'CRM_BAO_GIA_HUY'") + """
            SELECT * INTO b FROM master.crm_bao_gia WHERE id = p_bao_gia FOR UPDATE;
            IF b.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'CRM_GK_TRANG_THAI: chỉ hủy báo giá nháp (hiện %)', b.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_expected IS DISTINCT FROM b.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_GK_REVISION_CU: báo giá đã có revision mới — tải lại rồi thao tác' USING ERRCODE = 'P0001';
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' OR length(p_ly_do) > 1000 THEN
                RAISE EXCEPTION 'CRM_GK_THIEU_LY_DO: hủy nháp cần lý do' USING ERRCODE = 'P0001';
            END IF;
            UPDATE master.crm_bao_gia SET trang_thai = 'HUY', huy_ly_do = p_ly_do, huy_boi = ai, huy_luc = now(), cap_nhat_luc = clock_timestamp() WHERE id = b.id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_bao_gia'", id="b.id", hd="'CRM_BAO_GIA_HUY'",
                               sau="jsonb_build_object('trang_thai', 'HUY')", ly="p_ly_do") + """
            kq := jsonb_build_object('bao_gia_id', b.id, 'trang_thai', 'HUY', 'revision', b.revision_hien_hanh);""" + _G_KET.format(a="'CRM_BAO_GIA_HUY'") + """
        END $$""",
    # ghim mẫu HIỆU LỰC hôm nay cùng PN/loại hình: lần kiểm hiện hành phải khớp tệp/ánh xạ/danh mục (như duyệt CFO) — trả pin; dùng chung
    # cho chuyển sang Soạn và đổi mẫu tường minh. Không đọc mẫu lịch sử ở đây (picker chỉ mẫu hiệu lực).
    """CREATE OR REPLACE FUNCTION master.crm_gk_ghim_mau(p_pn uuid, p_loai uuid, p_mau_pb uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE v record; ax record; tep record; kt record; l record;
        BEGIN
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_mau_pb;
            IF v.id IS NULL OR v.phap_nhan_id <> p_pn OR master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) IS NULL THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy mẫu (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF v.loai_hinh_id <> p_loai OR v.trang_thai <> 'HIEU_LUC' OR v.valid_from > master.ktt_ngay()
               OR (v.valid_to IS NOT NULL AND master.ktt_ngay() >= v.valid_to) THEN
                RAISE EXCEPTION 'CRM_GK_MAU_KHONG_HIEU_LUC: mẫu không hiệu lực hôm nay hoặc khác loại hình' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO kt FROM master.crm_mau_kiem_tra WHERE id = v.kiem_hien_hanh;
            SELECT * INTO ax FROM master.crm_mau_anh_xa WHERE id = v.anh_xa_hien_hanh;
            SELECT * INTO tep FROM master.crm_mau_tep WHERE id = v.tep_id;
            IF kt.id IS NULL OR kt.anh_xa_id IS DISTINCT FROM ax.id OR kt.raw_sha256 <> tep.raw_sha256 OR kt.facts_sha256 <> tep.facts_sha256
               OR kt.ban_do_sha256 <> ax.ban_do_sha256 OR kt.danh_muc_digest <> v.danh_muc_digest
               OR master.crm_g_danh_muc_digest(v.loai_hinh_id, v.danh_muc_ref, v.danh_muc_rev) <> v.danh_muc_digest
               OR ax.so_chua_anh_xa > 0 OR ax.so_sai_kieu > 0 OR tep.trang_thai_doc <> 'DU' THEN
                RAISE EXCEPTION 'CRM_GK_MAU_KHONG_HOP_LE: mẫu hiệu lực không còn khớp lần kiểm/ánh xạ/danh mục' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO l FROM master.loai_hinh_doanh_thu WHERE id = p_loai;
            RETURN jsonb_build_object('mau_phien_ban_id', v.id, 'anh_xa_id', ax.id, 'kiem_id', kt.id, 'raw_sha256', tep.raw_sha256,
                                      'byte_length', tep.byte_length, 'facts_sha256', tep.facts_sha256, 'ban_do_sha256', ax.ban_do_sha256,
                                      'danh_muc_ref', v.danh_muc_ref, 'danh_muc_rev', v.danh_muc_rev, 'danh_muc_digest', v.danh_muc_digest,
                                      'profile_phien_ban', l.phien_ban, 'profile_sha256', """ + _GK_SHA.format(x="l.cau_hinh") + """,
                                      'loai_hop_dong', l.cau_hinh ->> 'loai_hop_dong');
        END $$""",
    # chuyển báo giá → Soạn: MỘT master.hop_dong + bản soạn revision 1 (lịch/row ID/thứ tự/giá/FX/khách giữ nguyên trong dữ liệu soạn); không
    # đòi điều kiện In (tổng %/FX); không hiệu lực/nghĩa vụ/M1. Báo giá đã chuyển → khóa khác báo 409 (không HĐ thứ hai).
    """CREATE OR REPLACE FUNCTION master.crm_gk_chuyen(p_khoa text, p_h text, p_bao_gia uuid, p_expected integer, p_mau_pb uuid, p_du_lieu jsonb,
                                                    p_renderer text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ b record; r record; pin jsonb; hd uuid; sid uuid; tien char(3);
        BEGIN""" + _G_CHU + _GK_GHIM.format(h="'CRM_BAO_GIA_CHUYEN'", x="p_bao_gia") + """
            SELECT * INTO d FROM master.crm_gk_dich('CRM_BAO_GIA_CHUYEN', p_bao_gia);""" + _G_REPLAY.format(a="'CRM_BAO_GIA_CHUYEN'") + """
            SELECT * INTO b FROM master.crm_bao_gia WHERE id = p_bao_gia FOR UPDATE;
            IF b.trang_thai = 'DA_CHUYEN' THEN
                RAISE EXCEPTION 'CRM_GK_DA_CHUYEN: báo giá đã chuyển sang Soạn — mở bản soạn hiện có' USING ERRCODE = 'P0001';
            END IF;
            IF b.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'CRM_GK_TRANG_THAI: báo giá % không chuyển được', b.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_expected IS DISTINCT FROM b.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_GK_REVISION_CU: báo giá đã có revision mới — tải lại rồi chuyển' USING ERRCODE = 'P0001';
            END IF;
            IF p_du_lieu IS NULL OR jsonb_typeof(p_du_lieu) <> 'object' OR p_renderer IS NULL THEN
                RAISE EXCEPTION 'CRM_GK_YEU_CAU_SAI: thiếu dữ liệu soạn' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO r FROM master.crm_bao_gia_rev WHERE bao_gia_id = b.id AND revision = b.revision_hien_hanh;
            pin := master.crm_gk_ghim_mau(d.pn, b.loai_hinh_id, p_mau_pb);
            IF pin ->> 'loai_hop_dong' IS NULL OR pin ->> 'loai_hop_dong' NOT IN ('XAY_DUNG','THUE_DAT','BAN_NHA','DICH_VU','KHAC') THEN
                RAISE EXCEPTION 'CRM_GK_LOAI_HD_CHUA_KHAI: profile loại hình chưa khai loại hợp đồng hỗ trợ soạn' USING ERRCODE = 'P0001';
            END IF;
            tien := coalesce(r.du_lieu -> 'gia' ->> 'tien_te', 'VND');
            INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, doi_tac_id, du_an_id, loai_hinh_dt_id, ngay_ky, gia_tri_minor, tien_te,
                                         trang_thai, crm_giao_ket)
                VALUES (d.pn, pin ->> 'loai_hop_dong', 'GK-' || b.so_bao_gia, 'SOAN-' || b.so_bao_gia, r.doi_tac_id, r.du_an_id, b.loai_hinh_id, NULL, NULL,
                        tien, 'SOAN_THAO', 'SOAN_THAO') RETURNING id INTO hd;
            INSERT INTO master.crm_hd_soan (phap_nhan_id, hop_dong_id, bao_gia_id, bao_gia_revision, loai_hinh_id, revision_hien_hanh, trang_thai, tao_boi)
                VALUES (d.pn, hd, b.id, b.revision_hien_hanh, b.loai_hinh_id, 1, 'SOAN_THAO', ai) RETURNING id INTO sid;
            INSERT INTO master.crm_hd_soan_rev (soan_id, phap_nhan_id, revision, nguon, mau_phien_ban_id, anh_xa_id, kiem_id, raw_sha256, byte_length,
                                                facts_sha256, ban_do_sha256, danh_muc_ref, danh_muc_rev, danh_muc_digest, profile_phien_ban,
                                                profile_sha256, renderer, du_lieu, du_lieu_sha256, ly_do, tao_boi)
                VALUES (sid, d.pn, 1, 'MAU', (pin ->> 'mau_phien_ban_id')::uuid, (pin ->> 'anh_xa_id')::uuid, (pin ->> 'kiem_id')::uuid, pin ->> 'raw_sha256',
                        (pin ->> 'byte_length')::bigint, pin ->> 'facts_sha256', pin ->> 'ban_do_sha256', pin ->> 'danh_muc_ref',
                        (pin ->> 'danh_muc_rev')::integer, pin ->> 'danh_muc_digest', (pin ->> 'profile_phien_ban')::integer, pin ->> 'profile_sha256',
                        p_renderer, p_du_lieu, """ + _GK_SHA.format(x="p_du_lieu") + """, NULL, ai);
            UPDATE master.crm_bao_gia SET trang_thai = 'DA_CHUYEN', hop_dong_id = hd, cap_nhat_luc = clock_timestamp() WHERE id = b.id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_bao_gia'", id="b.id", hd="'CRM_BAO_GIA_CHUYEN'",
                               sau="jsonb_build_object('hop_dong_id', hd, 'soan_id', sid, 'mau_phien_ban_id', pin ->> 'mau_phien_ban_id')", ly="NULL") + """
            kq := jsonb_build_object('bao_gia_id', b.id, 'hop_dong_id', hd, 'soan_id', sid, 'revision', 1, 'trang_thai', 'SOAN_THAO');"""
    + _G_KET.format(a="'CRM_BAO_GIA_CHUYEN'") + """
        END $$""",
    # lưu bản soạn: revision mới (CAS); giữ pin cũ, hoặc đổi mẫu TƯỜNG MINH sang mẫu hiệu lực hôm nay (pin mới); revision mới đưa về SOAN_THAO
    """CREATE OR REPLACE FUNCTION master.crm_gk_soan_luu(p_khoa text, p_h text, p_soan uuid, p_expected integer, p_du_lieu jsonb, p_mau_pb uuid,
                                                      p_ly_do text, p_renderer text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ s record; cu_rev record; pin jsonb; n integer;
        BEGIN""" + _G_CHU + _GK_GHIM.format(h="'CRM_SOAN_LUU'", x="p_soan") + """
            SELECT * INTO d FROM master.crm_gk_dich('CRM_SOAN_LUU', p_soan);""" + _G_REPLAY.format(a="'CRM_SOAN_LUU'") + """
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan FOR UPDATE;
            PERFORM 1 FROM master.hop_dong WHERE id = s.hop_dong_id FOR UPDATE;
            IF p_expected IS DISTINCT FROM s.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_GK_REVISION_CU: bản soạn đã có revision mới — tải lại rồi lưu' USING ERRCODE = 'P0001';
            END IF;
            IF p_du_lieu IS NULL OR jsonb_typeof(p_du_lieu) <> 'object' THEN
                RAISE EXCEPTION 'CRM_GK_YEU_CAU_SAI: dữ liệu soạn phải là object' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO cu_rev FROM master.crm_hd_soan_rev WHERE soan_id = s.id AND revision = s.revision_hien_hanh;
            IF p_mau_pb IS NULL OR p_mau_pb = cu_rev.mau_phien_ban_id THEN
                pin := jsonb_build_object('mau_phien_ban_id', cu_rev.mau_phien_ban_id, 'anh_xa_id', cu_rev.anh_xa_id, 'kiem_id', cu_rev.kiem_id,
                                          'raw_sha256', cu_rev.raw_sha256, 'byte_length', cu_rev.byte_length, 'facts_sha256', cu_rev.facts_sha256,
                                          'ban_do_sha256', cu_rev.ban_do_sha256, 'danh_muc_ref', cu_rev.danh_muc_ref, 'danh_muc_rev', cu_rev.danh_muc_rev,
                                          'danh_muc_digest', cu_rev.danh_muc_digest, 'profile_phien_ban', cu_rev.profile_phien_ban,
                                          'profile_sha256', cu_rev.profile_sha256);
            ELSE
                pin := master.crm_gk_ghim_mau(d.pn, s.loai_hinh_id, p_mau_pb);  -- đổi mẫu tường minh: chỉ mẫu hiệu lực hôm nay, cùng PN/loại hình
                IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                    RAISE EXCEPTION 'CRM_GK_THIEU_LY_DO: đổi mẫu cần lý do' USING ERRCODE = 'P0001';
                END IF;
            END IF;
            n := s.revision_hien_hanh + 1;
            INSERT INTO master.crm_hd_soan_rev (soan_id, phap_nhan_id, revision, nguon, mau_phien_ban_id, anh_xa_id, kiem_id, raw_sha256, byte_length,
                                                facts_sha256, ban_do_sha256, danh_muc_ref, danh_muc_rev, danh_muc_digest, profile_phien_ban,
                                                profile_sha256, renderer, du_lieu, du_lieu_sha256, ly_do, tao_boi)
                VALUES (s.id, d.pn, n, 'MAU', (pin ->> 'mau_phien_ban_id')::uuid, (pin ->> 'anh_xa_id')::uuid, (pin ->> 'kiem_id')::uuid, pin ->> 'raw_sha256',
                        (pin ->> 'byte_length')::bigint, pin ->> 'facts_sha256', pin ->> 'ban_do_sha256', pin ->> 'danh_muc_ref',
                        (pin ->> 'danh_muc_rev')::integer, pin ->> 'danh_muc_digest', (pin ->> 'profile_phien_ban')::integer, pin ->> 'profile_sha256',
                        p_renderer, p_du_lieu, """ + _GK_SHA.format(x="p_du_lieu") + """, p_ly_do, ai);
            UPDATE master.crm_hd_soan SET revision_hien_hanh = n, trang_thai = 'SOAN_THAO', cap_nhat_luc = clock_timestamp() WHERE id = s.id;
            UPDATE master.hop_dong SET trang_thai = 'SOAN_THAO', crm_giao_ket = 'SOAN_THAO' WHERE id = s.hop_dong_id AND crm_giao_ket IS DISTINCT FROM 'SOAN_THAO';
            """ + _G_NK.format(pn="d.pn", loai="'SUA_DANH_MUC'", bang="'master.crm_hd_soan'", id="s.id", hd="'CRM_SOAN_LUU'",
                               sau="jsonb_build_object('revision', n, 'mau_phien_ban_id', pin ->> 'mau_phien_ban_id')", ly="p_ly_do") + """
            kq := jsonb_build_object('soan_id', s.id, 'hop_dong_id', s.hop_dong_id, 'revision', n, 'trang_thai', 'SOAN_THAO',
                                     'mau_phien_ban_id', pin ->> 'mau_phien_ban_id');""" + _G_KET.format(a="'CRM_SOAN_LUU'") + """
        END $$""",
    # công bố lần in/xuất SAU render dài (ngoài khóa/giao dịch): quyền hiện hành + CAS revision trong giao dịch ngắn. Revision đã đổi → ghi
    # bằng chứng DA_CU (không gắn tệp là hiện hành). Chỉ HOP_DONG + PDF_DAT mới chuyển CHO_KY; không DA_KY/HIEU_LUC/nghĩa vụ.
    """CREATE OR REPLACE FUNCTION master.crm_gk_xuat_ghi(p_khoa text, p_h text, p_hanh_dong text, p_dich uuid, p_revision integer, p_input_sha text,
                                                      p_docx_sha text, p_docx_len bigint, p_pdf_sha text, p_pdf_len bigint, p_trang_thai text,
                                                      p_engine text, p_ly_do text, p_kiem jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ b record; s record; x uuid; tt text; cu_rev boolean; lan record;
        BEGIN""" + _G_CHU + """
            IF p_hanh_dong NOT IN ('CRM_BAO_GIA_IN','CRM_SOAN_XUAT') THEN
                RAISE EXCEPTION 'CRM_G_HANH_DONG_SAI: hành động không hợp lệ' USING ERRCODE = 'P0001';
            END IF;""" + _GK_GHIM.format(h="p_hanh_dong", x="p_dich") + """
            SELECT * INTO d FROM master.crm_gk_dich(p_hanh_dong, p_dich);""" + _G_REPLAY.format(a="p_hanh_dong") + """
            IF p_trang_thai NOT IN ('PDF_DAT','PDF_CHUA_SAN_SANG','PDF_LOI') THEN
                RAISE EXCEPTION 'CRM_GK_YEU_CAU_SAI: trạng thái xuất không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            -- FIX01 #5: chỉ công bố đúng lần render ĐÃ ĐẶT CHỖ bền ở pha A (cùng khóa/H/đích/revision/input chụp); không nhận kết quả lạ
            SELECT * INTO lan FROM master.crm_gk_lan WHERE phap_nhan_id = d.pn AND nguoi_dung_id = master.crm_g_ai_id() AND hanh_dong = p_hanh_dong
                AND khoa = p_khoa FOR UPDATE;
            IF lan.id IS NULL OR lan.yeu_cau_sha256 <> p_h OR lan.dich_id <> p_dich OR lan.revision <> p_revision OR lan.input_sha256 <> p_input_sha
               OR lan.trang_thai <> 'DANG_RENDER' THEN
                RAISE EXCEPTION 'CRM_GK_LAN_KHONG_KHOP: kết quả render không khớp lần đã đặt chỗ — không công bố' USING ERRCODE = 'P0001';
            END IF;
            tt := p_trang_thai;
            IF p_hanh_dong = 'CRM_BAO_GIA_IN' THEN
                SELECT * INTO b FROM master.crm_bao_gia WHERE id = p_dich FOR UPDATE;
                cu_rev := b.revision_hien_hanh <> p_revision OR b.trang_thai = 'HUY';
                IF cu_rev THEN tt := 'DA_CU'; END IF;
                INSERT INTO master.crm_gk_xuat (phap_nhan_id, loai, bao_gia_id, revision, input_sha256, docx_sha256, docx_len, pdf_sha256, pdf_len, trang_thai,
                                                engine, ly_do, kiem_pdf, tao_boi)
                    VALUES (d.pn, 'BAO_GIA', b.id, p_revision, p_input_sha, p_docx_sha, p_docx_len, CASE WHEN tt = 'PDF_DAT' THEN p_pdf_sha END,
                            CASE WHEN tt = 'PDF_DAT' THEN p_pdf_len END, tt, p_engine, p_ly_do, coalesce(p_kiem, '{}'::jsonb), ai) RETURNING id INTO x;
            ELSE
                SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_dich FOR UPDATE;
                PERFORM 1 FROM master.hop_dong WHERE id = s.hop_dong_id FOR UPDATE;
                cu_rev := s.revision_hien_hanh <> p_revision;
                IF cu_rev THEN tt := 'DA_CU'; END IF;
                INSERT INTO master.crm_gk_xuat (phap_nhan_id, loai, soan_id, revision, input_sha256, docx_sha256, docx_len, pdf_sha256, pdf_len, trang_thai,
                                                engine, ly_do, kiem_pdf, tao_boi)
                    VALUES (d.pn, 'HOP_DONG', s.id, p_revision, p_input_sha, p_docx_sha, p_docx_len, CASE WHEN tt = 'PDF_DAT' THEN p_pdf_sha END,
                            CASE WHEN tt = 'PDF_DAT' THEN p_pdf_len END, tt, p_engine, p_ly_do, coalesce(p_kiem, '{}'::jsonb), ai) RETURNING id INTO x;
                IF tt = 'PDF_DAT' THEN
                    UPDATE master.crm_hd_soan SET trang_thai = 'CHO_KY', cap_nhat_luc = clock_timestamp() WHERE id = s.id;
                    UPDATE master.hop_dong SET trang_thai = 'CHO_KY', crm_giao_ket = 'CHO_KY' WHERE id = s.hop_dong_id;
                END IF;
            END IF;
            UPDATE master.crm_gk_lan SET trang_thai = 'DA_CONG_BO', xuat_id = x, cap_nhat_luc = clock_timestamp() WHERE id = lan.id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="CASE WHEN p_hanh_dong = 'CRM_BAO_GIA_IN' THEN 'master.crm_bao_gia' ELSE 'master.crm_hd_soan' END",
                               id="p_dich", hd="p_hanh_dong", sau="jsonb_build_object('xuat_id', x, 'revision', p_revision, 'trang_thai', tt)", ly="p_ly_do") + """
            kq := jsonb_build_object('xuat_id', x, 'revision', p_revision, 'trang_thai', tt, 'docx_sha256', p_docx_sha, 'docx_len', p_docx_len,
                                     'pdf_sha256', CASE WHEN tt = 'PDF_DAT' THEN p_pdf_sha END, 'pdf_len', CASE WHEN tt = 'PDF_DAT' THEN p_pdf_len END,
                                     'da_cu', cu_rev);""" + _G_KET.format(a="p_hanh_dong") + """
        END $$""",
    # ======================================================================= đọc có quyền hiện hành (kết nối chủ bảng)
    # mẫu ĐÃ GHIM của một revision bản soạn — đọc lịch sử hẹp gắn đúng bản soạn/PN (không nới picker/sales sang mọi mẫu lịch sử)
    """CREATE OR REPLACE FUNCTION master.crm_gk_mau_ghim(p_soan uuid, p_revision integer) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE s record; r record; v record; tep record; ax record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan;
            IF s.id IS NULL OR NOT master.ktt_duoc(s.phap_nhan_id, 'CRM') OR NOT master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản soạn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE soan_id = s.id AND revision = p_revision;
            IF r.id IS NULL THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy revision bản soạn' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = r.mau_phien_ban_id;
            SELECT * INTO tep FROM master.crm_mau_tep WHERE id = v.tep_id;
            SELECT * INTO ax FROM master.crm_mau_anh_xa WHERE id = r.anh_xa_id;
            IF tep.raw_sha256 <> r.raw_sha256 OR tep.byte_length <> r.byte_length OR tep.facts_sha256 <> r.facts_sha256 OR ax.ban_do_sha256 <> r.ban_do_sha256 THEN
                RAISE EXCEPTION 'CRM_GK_MAU_LECH_GHIM: mẫu đã ghim không khớp bản lưu' USING ERRCODE = 'P0001';
            END IF;
            RETURN jsonb_build_object('mau_phien_ban_id', v.id, 'ma_mau', (SELECT m.ma_mau FROM master.crm_mau m WHERE m.id = v.mau_id),
                'phien_ban', v.phien_ban, 'ten_tep', v.ten_tep, 'raw_sha256', tep.raw_sha256, 'byte_length', tep.byte_length, 'facts', tep.facts,
                'ban_do', ax.ban_do, 'danh_muc_ref', r.danh_muc_ref, 'danh_muc_rev', r.danh_muc_rev,
                'danh_muc', (SELECT coalesce(jsonb_agg(jsonb_build_object('khoa', t.khoa, 'nhan', t.nhan, 'nhom', t.nhom, 'kieu', t.kieu,
                                                                          'dinh_dang', t.dinh_dang, 'nguon', t.nguon, 'pii', t.pii, 'bat_buoc', t.bat_buoc)
                                                       ORDER BY t.khoa), '[]'::jsonb)
                             FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = v.loai_hinh_id AND t.danh_muc_ref = r.danh_muc_ref
                               AND t.revision = r.danh_muc_rev));
        END $$""",
    # picker: CHỈ phiên bản mẫu HIỆU LỰC hôm nay của đúng PN/loại hình (không mẫu lịch sử/nháp)
    """CREATE OR REPLACE FUNCTION master.crm_gk_mau_hieu_luc(p_loai uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE pn uuid;
        BEGIN""" + _G_CHU + """
            SELECT l.phap_nhan_id INTO pn FROM master.loai_hinh_doanh_thu l WHERE l.id = p_loai;
            IF pn IS NULL OR NOT master.crm_gk_duoc('CRM_SOAN', pn) THEN
                RETURN '[]'::jsonb;
            END IF;
            RETURN (SELECT coalesce(jsonb_agg(jsonb_build_object('mau_phien_ban_id', v.id, 'ma_mau', m.ma_mau, 'phien_ban', v.phien_ban,
                                                                'valid_from', v.valid_from, 'valid_to', v.valid_to, 'ten_tep', v.ten_tep)
                                              ORDER BY m.ma_mau, v.phien_ban), '[]'::jsonb)
                    FROM master.crm_mau_phien_ban v JOIN master.crm_mau m ON m.id = v.mau_id
                    WHERE v.loai_hinh_id = p_loai AND v.phap_nhan_id = pn AND v.trang_thai = 'HIEU_LUC'
                      AND v.valid_from <= master.ktt_ngay() AND (v.valid_to IS NULL OR master.ktt_ngay() < v.valid_to));
        END $$""",
    # tải tệp đã công bố: quyền hiện hành trên PN của đối tượng TRƯỚC khi trả hash/độ dài (máy chủ mới tra kho)
    """CREATE OR REPLACE FUNCTION master.crm_gk_tep(p_xuat uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE x record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO x FROM master.crm_gk_xuat WHERE id = p_xuat;
            IF x.id IS NULL OR NOT master.crm_gk_duoc(CASE WHEN x.loai = 'BAO_GIA' THEN 'CRM_BAO_GIA' ELSE 'CRM_SOAN' END, x.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy tệp (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            RETURN jsonb_build_object('xuat_id', x.id, 'loai', x.loai, 'docx_sha256', x.docx_sha256, 'docx_len', x.docx_len, 'pdf_sha256', x.pdf_sha256,
                                      'pdf_len', x.pdf_len, 'trang_thai', x.trang_thai, 'revision', x.revision,
                                      'ten', CASE WHEN x.loai = 'BAO_GIA' THEN (SELECT b.so_bao_gia FROM master.crm_bao_gia b WHERE b.id = x.bao_gia_id)
                                                  ELSE (SELECT h.ma_noi_bo FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id
                                                        WHERE s.id = x.soan_id) END);
        END $$""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm lệnh không cấp PUBLIC
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _GK_BANG_MOI),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON master.crm_bao_gia_dieu_khoan, master.crm_bao_gia, master.crm_bao_gia_rev, master.crm_hd_soan, '
                               'master.crm_hd_soan_rev, master.crm_gk_xuat, master.crm_gk_lan FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    """REVOKE ALL ON master.crm_bao_gia_dieu_khoan, master.crm_bao_gia, master.crm_bao_gia_rev, master.crm_hd_soan, master.crm_hd_soan_rev,
        master.crm_gk_xuat, master.crm_gk_lan FROM PUBLIC""",
    """REVOKE EXECUTE ON FUNCTION master.crm_gk_pn(text, uuid), master.crm_gk_dat_lan(text, text, uuid, text, integer, text) FROM PUBLIC""",
    """REVOKE EXECUTE ON FUNCTION master.crm_gk_dich(text, uuid), master.crm_gk_tra(text, text, uuid, text),
        master.crm_gk_bao_gia_luu(text, text, uuid, uuid, integer, uuid, uuid, jsonb, jsonb, uuid, text, date, jsonb),
        master.crm_gk_bao_gia_huy(text, text, uuid, integer, text), master.crm_gk_ghim_mau(uuid, uuid, uuid),
        master.crm_gk_chuyen(text, text, uuid, integer, uuid, jsonb, text), master.crm_gk_soan_luu(text, text, uuid, integer, jsonb, uuid, text, text),
        master.crm_gk_xuat_ghi(text, text, text, uuid, integer, text, text, bigint, text, bigint, text, text, text, jsonb),
        master.crm_gk_mau_ghim(uuid, integer), master.crm_gk_mau_hieu_luc(uuid), master.crm_gk_tep(uuid) FROM PUBLIC""",
)

PG_MIGRATIONS = (*PG_MIGRATIONS, M0021_CRM_G2G3)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0022 — M4-02B Chứng từ L3 (APPEND sau toàn bộ 1–21; không sửa byte/định nghĩa/checksum 1–21, không sửa sql_review.py).
#        Định nghĩa trong m4/sql_chung_tu.py (chỉ hằng SQL): chung_tu_run/result/artifact/revision/manual_map/giu_khoa + quyền SOAN|REVIEW theo đợt
#        + biên nhận chung m4.bien_nhan. Không role/quyền nghiệp vụ mới.
# ---------------------------------------------------------------------------
from ..m4.sql_chung_tu import M0022_M4_CHUNG_TU  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

PG_MIGRATIONS = (*PG_MIGRATIONS, M0022_M4_CHUNG_TU)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0023 — CRM-41-04A G4 ký lần đầu (APPEND sau toàn bộ 1–22; không sửa byte/định nghĩa/checksum 1–22, không sửa m4/sql_review.py, M9/B).
#        Bản ký PDF bất biến (content-addressed, máy chủ ghi TRƯỚC commit) + lineage đúng bản xuất G3 HOP_DONG/PDF_DAT MỚI NHẤT của revision
#        hiện hành (hai hash PDF tách riêng) + DA_KY + trạng thái G5 KHỞI TẠO + nhật ký + biên nhận trong MỘT giao dịch, khóa bản soạn/HĐ.
#        Phạm vi ký: ràng buộc mỏng tham chiếu master.phan_cong_hanh_dong + HĐ CRM (cùng PN), đối chiếu dự án/khách (mã hoặc tham chiếu dự thảo)
#        hiện hành — không suy từ người tạo/tên, không vai/IAM mới, không tự cấp. Sau ký: guard backend chặn lưu revision/đặt chỗ xuất/công bố
#        hiện hành (công bố muộn → DA_CU, không hồi trạng thái), không thay/mở lại bản ký (Q-RETURN). Ngày ký KHÔNG là ngày hiệu lực; không
#        hop_dong_phien_ban/lịch thu/nghĩa vụ/M1/Junsky; G5 chỉ PENDING|NOT_SELECTED (không worker/MATCH/chọn mẫu ngẫu nhiên); không G6.
# ---------------------------------------------------------------------------
_KY_BANG_MOI = ("crm_ky_pham_vi", "crm_hd_ky", "crm_hd_ky_g5")
_KY_HIEN_THI = "Đã ký — chờ kế toán kiểm"
# công bố muộn của lần render bắt đầu TRƯỚC khi ký: định nghĩa crm_gk_xuat_ghi của M0021 (giữ nguyên byte ở trên) được tạo lại với đúng MỘT thay đổi —
# bản soạn DA_KY coi như revision đã cũ → ghi bằng chứng DA_CU, không chuyển CHO_KY.
_KY_XG_CU = "                cu_rev := s.revision_hien_hanh <> p_revision;\n"
_KY_XG = next(s for s in M0021_CRM_G2G3 if "FUNCTION master.crm_gk_xuat_ghi(" in s)
if _KY_XG.count(_KY_XG_CU) != 1:
    raise RuntimeError("M0023: không định vị đúng một dòng CAS revision của crm_gk_xuat_ghi")
_KY_XG = _KY_XG.replace(_KY_XG_CU, "                cu_rev := s.revision_hien_hanh <> p_revision OR s.trang_thai = 'DA_KY';\n")
_KY_DU_THAO_SHA = _GK_SHA.format(x="(r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao')")

M0023_CRM_KY = (
    "SET LOCAL check_function_bodies = off",
    # --- trạng thái DA_KY cho discriminator HĐ CRM và bản soạn (giá trị cũ giữ nguyên; hàng cũ NULL không đổi ngữ nghĩa)
    "ALTER TABLE master.hop_dong DROP CONSTRAINT hop_dong_crm_giao_ket_check",
    """ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_crm_giao_ket_check CHECK (crm_giao_ket IS NULL OR crm_giao_ket IN ('SOAN_THAO','CHO_KY','DA_KY'))""",
    "ALTER TABLE master.crm_hd_soan DROP CONSTRAINT crm_hd_soan_trang_thai_check",
    """ALTER TABLE master.crm_hd_soan ADD CONSTRAINT crm_hd_soan_trang_thai_check CHECK (trang_thai IN ('SOAN_THAO','CHO_KY','DA_KY'))""",
    # --- phạm vi ký/đọc (thin scope binding): phân công hiện hành trên master.phan_cong_hanh_dong — CRM_KY_KET (Bán hàng ký) hoặc action hẹp
    # CRM_KY_DOC (KT/KTT/CFO đọc bản ký) — × đúng HĐ CRM/bản soạn cùng PN × snapshot dự án + khách (mã đối tác hoặc digest tham chiếu khách dự
    # thảo của báo giá nguồn). Chỉ quản trị (chủ CSDL) ghi; thu hồi bằng dấu một lần, không xóa/sửa. Không vai/master/IAM mới, không tự cấp.
    """CREATE TABLE master.crm_ky_pham_vi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phan_cong_id uuid NOT NULL REFERENCES master.phan_cong_hanh_dong(id),
        phap_nhan_id uuid NOT NULL REFERENCES master.phap_nhan(id),
        hop_dong_id uuid NOT NULL,
        soan_id uuid NOT NULL,
        du_an_id uuid,
        doi_tac_id uuid REFERENCES master.doi_tac(id),
        khach_du_thao_sha256 text CHECK (khach_du_thao_sha256 IS NULL OR khach_du_thao_sha256 ~ '^[0-9a-f]{64}$'),
        cap_boi text NOT NULL,
        cap_luc timestamptz NOT NULL DEFAULT now(),
        thu_hoi_luc timestamptz,
        thu_hoi_boi text,
        thu_hoi_ly_do text,
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (soan_id, phap_nhan_id) REFERENCES master.crm_hd_soan (id, phap_nhan_id),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        CHECK ((doi_tac_id IS NULL) <> (khach_du_thao_sha256 IS NULL)),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL) AND (thu_hoi_luc IS NULL) = (thu_hoi_ly_do IS NULL)))""",
    """CREATE UNIQUE INDEX crm_ky_pham_vi_hien_hanh_uq ON master.crm_ky_pham_vi (phan_cong_id, hop_dong_id) WHERE thu_hoi_luc IS NULL""",
    """CREATE OR REPLACE FUNCTION master.crm_ky_pham_vi_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE a record; s record; h record;
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'CRM_KY_PHAM_VI_CHI_QUAN_TRI: phạm vi ký chỉ do quản trị (chủ CSDL) ghi' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'CRM_KY_PHAM_VI_BAT_BIEN: thu hồi bằng dấu thu hồi, không xóa' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.thu_hoi_luc IS NOT NULL OR NEW.thu_hoi_luc IS NULL OR coalesce(btrim(NEW.thu_hoi_ly_do), '') = ''
                   OR ROW(NEW.id, NEW.phan_cong_id, NEW.phap_nhan_id, NEW.hop_dong_id, NEW.soan_id, NEW.du_an_id, NEW.doi_tac_id, NEW.khach_du_thao_sha256,
                          NEW.cap_boi, NEW.cap_luc)
                      IS DISTINCT FROM ROW(OLD.id, OLD.phan_cong_id, OLD.phap_nhan_id, OLD.hop_dong_id, OLD.soan_id, OLD.du_an_id, OLD.doi_tac_id,
                                           OLD.khach_du_thao_sha256, OLD.cap_boi, OLD.cap_luc) THEN
                    RAISE EXCEPTION 'CRM_KY_PHAM_VI_BAT_BIEN: chỉ ghi dấu thu hồi một lần, không sửa phạm vi' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.thu_hoi_luc IS NOT NULL THEN
                RAISE EXCEPTION 'CRM_KY_PHAM_VI_BAT_BIEN: không chèn phạm vi đã thu hồi' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO a FROM master.phan_cong_hanh_dong WHERE id = NEW.phan_cong_id;
            IF a.id IS NULL OR a.thu_hoi_luc IS NOT NULL OR a.phap_nhan_id <> NEW.phap_nhan_id OR a.module <> 'CRM'
               OR a.hanh_dong NOT IN ('CRM_KY_KET', 'CRM_KY_DOC') THEN
                RAISE EXCEPTION 'CRM_KY_PHAM_VI_SAI: phạm vi phải gắn phân công CRM_KY_KET (ký) hoặc CRM_KY_DOC (đọc) còn hiệu lực cùng pháp nhân'
                    USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = NEW.soan_id;
            SELECT * INTO h FROM master.hop_dong WHERE id = NEW.hop_dong_id;
            IF s.id IS NULL OR h.id IS NULL OR s.hop_dong_id <> NEW.hop_dong_id OR h.crm_giao_ket IS NULL
               OR (a.loai_hinh_id IS NOT NULL AND a.loai_hinh_id <> s.loai_hinh_id)
               OR NEW.du_an_id IS DISTINCT FROM h.du_an_id
               OR (NEW.doi_tac_id IS NOT NULL AND NEW.doi_tac_id IS DISTINCT FROM h.doi_tac_id)
               OR (NEW.doi_tac_id IS NULL AND h.doi_tac_id IS NOT NULL) THEN
                RAISE EXCEPTION 'CRM_KY_PHAM_VI_SAI: phạm vi không khớp HĐ/bản soạn/dự án/khách hiện hành' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_ky_pham_vi_kiem BEFORE INSERT OR UPDATE OR DELETE ON master.crm_ky_pham_vi FOR EACH ROW EXECUTE FUNCTION master.crm_ky_pham_vi_kiem()",
    # --- bản ký lần đầu: MỘT hàng/HĐ, bất biến (chỉ ghi thêm qua hàm lệnh chủ bảng). Lineage G3 + pin mẫu/ánh xạ/danh mục/profile/dữ liệu của
    # revision đã xuất được chụp NGUYÊN tại thời điểm ký (xem lại không đọc nháp hiện hành). Hai PDF: G3 (bản sinh) và bản ký (bằng chứng) tách riêng.
    """CREATE TABLE master.crm_hd_ky (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        soan_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        soan_rev_id uuid NOT NULL,
        xuat_id uuid NOT NULL REFERENCES master.crm_gk_xuat(id),
        g3_input_sha256 text NOT NULL CHECK (g3_input_sha256 ~ '^[0-9a-f]{64}$'),
        g3_docx_sha256 text NOT NULL CHECK (g3_docx_sha256 ~ '^[0-9a-f]{64}$'),
        g3_docx_len bigint NOT NULL CHECK (g3_docx_len > 0),
        g3_pdf_sha256 text NOT NULL CHECK (g3_pdf_sha256 ~ '^[0-9a-f]{64}$'),
        g3_pdf_len bigint NOT NULL CHECK (g3_pdf_len > 0),
        g3_engine text NOT NULL CHECK (length(g3_engine) BETWEEN 1 AND 200),
        mau_phien_ban_id uuid NOT NULL,
        anh_xa_id uuid NOT NULL,
        kiem_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
        ban_do_sha256 text NOT NULL CHECK (ban_do_sha256 ~ '^[0-9a-f]{64}$'),
        danh_muc_ref text NOT NULL,
        danh_muc_rev integer NOT NULL,
        danh_muc_digest text NOT NULL CHECK (danh_muc_digest ~ '^[0-9a-f]{64}$'),
        profile_phien_ban integer NOT NULL,
        profile_sha256 text NOT NULL CHECK (profile_sha256 ~ '^[0-9a-f]{64}$'),
        du_lieu_sha256 text NOT NULL CHECK (du_lieu_sha256 ~ '^[0-9a-f]{64}$'),
        tom_tat jsonb NOT NULL CHECK (jsonb_typeof(tom_tat) = 'object'),
        ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ '^[0-9a-f]{64}$'),
        ky_pdf_len bigint NOT NULL CHECK (ky_pdf_len > 0),
        ky_so_trang integer NOT NULL CHECK (ky_so_trang >= 1),
        ten_tep text NOT NULL CHECK (length(ten_tep) BETWEEN 5 AND 200 AND lower(ten_tep) LIKE '%.pdf' AND strpos(ten_tep, '/') = 0
                                     AND strpos(ten_tep, chr(92)) = 0 AND ten_tep !~ '[[:cntrl:]]'),
        ngay_ky date NOT NULL,
        nguoi_ky_khach text CHECK (nguoi_ky_khach IS NULL OR (length(nguoi_ky_khach) BETWEEN 1 AND 200 AND nguoi_ky_khach !~ '[[:cntrl:]]')),
        co_sua boolean NOT NULL,
        mo_ta_sua text CHECK (mo_ta_sua IS NULL OR (length(mo_ta_sua) BETWEEN 1 AND 2000 AND btrim(mo_ta_sua) <> '')),
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id),
        FOREIGN KEY (soan_id, phap_nhan_id) REFERENCES master.crm_hd_soan (id, phap_nhan_id),
        FOREIGN KEY (soan_rev_id, soan_id) REFERENCES master.crm_hd_soan_rev (id, soan_id),
        UNIQUE (hop_dong_id),
        UNIQUE (hop_dong_id, ky_pdf_sha256),
        UNIQUE (id, phap_nhan_id),
        CHECK (co_sua = (mo_ta_sua IS NOT NULL)))""",
    # Hai bằng chứng (PDF G3 bản sinh / PDF bản ký) có vai trò, ID, hash, độ dài RIÊNG; không buộc hai digest khác nhau (bản ký trùng byte bản xuất
    # vẫn là bằng chứng ký riêng — hash/bytes KHÔNG chứng minh chữ ký xác thực; G4 không OCR/so nội dung).
    "CREATE TRIGGER crm_hd_ky_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_hd_ky FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    # nhất quán lineage khi chèn (kể cả ordinary SQL chủ bảng bỏ qua hàm lệnh): đúng bản xuất HOP_DONG PDF_DAT của đúng bản soạn CHO_KY/revision hiện hành
    """CREATE OR REPLACE FUNCTION master.crm_hd_ky_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE s record; x record; r record;
        BEGIN
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = NEW.soan_id;
            SELECT * INTO x FROM master.crm_gk_xuat WHERE id = NEW.xuat_id;
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE id = NEW.soan_rev_id;
            IF s.id IS NULL OR x.id IS NULL OR r.id IS NULL
               OR s.trang_thai IS DISTINCT FROM 'CHO_KY' OR s.hop_dong_id IS DISTINCT FROM NEW.hop_dong_id OR s.revision_hien_hanh IS DISTINCT FROM NEW.revision
               OR x.loai IS DISTINCT FROM 'HOP_DONG' OR x.soan_id IS DISTINCT FROM NEW.soan_id OR x.revision IS DISTINCT FROM NEW.revision
               OR x.trang_thai IS DISTINCT FROM 'PDF_DAT' OR x.pdf_sha256 IS DISTINCT FROM NEW.g3_pdf_sha256 OR x.pdf_len IS DISTINCT FROM NEW.g3_pdf_len
               OR x.docx_sha256 IS DISTINCT FROM NEW.g3_docx_sha256 OR x.docx_len IS DISTINCT FROM NEW.g3_docx_len
               OR x.input_sha256 IS DISTINCT FROM NEW.g3_input_sha256 OR x.engine IS DISTINCT FROM NEW.g3_engine
               OR r.revision IS DISTINCT FROM NEW.revision OR r.mau_phien_ban_id IS DISTINCT FROM NEW.mau_phien_ban_id OR r.anh_xa_id IS DISTINCT FROM NEW.anh_xa_id
               OR r.kiem_id IS DISTINCT FROM NEW.kiem_id OR r.raw_sha256 IS DISTINCT FROM NEW.raw_sha256 OR r.ban_do_sha256 IS DISTINCT FROM NEW.ban_do_sha256
               OR r.danh_muc_ref IS DISTINCT FROM NEW.danh_muc_ref OR r.danh_muc_rev IS DISTINCT FROM NEW.danh_muc_rev
               OR r.danh_muc_digest IS DISTINCT FROM NEW.danh_muc_digest OR r.profile_phien_ban IS DISTINCT FROM NEW.profile_phien_ban
               OR r.profile_sha256 IS DISTINCT FROM NEW.profile_sha256 OR r.du_lieu_sha256 IS DISTINCT FROM NEW.du_lieu_sha256 THEN
                RAISE EXCEPTION 'CRM_KY_G3_LECH: bản ký phải gắn đúng bản xuất G3 PDF_DAT và revision đã ghim của bản soạn CHO_KY' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_hd_ky_kiem BEFORE INSERT ON master.crm_hd_ky FOR EACH ROW EXECUTE FUNCTION master.crm_hd_ky_kiem()",
    # --- G5 trạng thái KHỞI TẠO (cùng giao dịch ký; bất biến). Khai Có → PENDING/BAT_BUOC_KHAI_CO (chưa thực thi); Không → NOT_SELECTED/
    # CHUA_AP_DUNG_CHON_MAU. Không worker/MATCH/đối chiếu/chọn mẫu ngẫu nhiên — các chuyển tiếp G5 thuộc gói sau (bảng/hàm riêng, ghi thêm).
    """CREATE TABLE master.crm_hd_ky_g5 (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ky_id uuid NOT NULL UNIQUE,
        phap_nhan_id uuid NOT NULL,
        trang_thai text NOT NULL CHECK (trang_thai IN ('PENDING','NOT_SELECTED')),
        ly_do text NOT NULL CHECK (ly_do IN ('BAT_BUOC_KHAI_CO','CHUA_AP_DUNG_CHON_MAU')),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (ky_id, phap_nhan_id) REFERENCES master.crm_hd_ky (id, phap_nhan_id),
        CHECK ((trang_thai = 'PENDING') = (ly_do = 'BAT_BUOC_KHAI_CO')))""",
    "CREATE TRIGGER crm_hd_ky_g5_bat_bien BEFORE INSERT OR UPDATE OR DELETE ON master.crm_hd_ky_g5 FOR EACH ROW EXECUTE FUNCTION master.crm_g_bat_bien()",
    """CREATE OR REPLACE FUNCTION master.crm_hd_ky_g5_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE k record;
        BEGIN
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = NEW.ky_id;
            IF k.id IS NULL OR (NEW.trang_thai = 'PENDING') IS DISTINCT FROM k.co_sua THEN
                RAISE EXCEPTION 'CRM_KY_G5_SAI: trạng thái G5 khởi tạo phải theo đúng khai báo Có/Không của bản ký' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_hd_ky_g5_kiem BEFORE INSERT ON master.crm_hd_ky_g5 FOR EACH ROW EXECUTE FUNCTION master.crm_hd_ky_g5_kiem()",
    # ======================================================================= khóa G3 sau ký (backend, scoped HĐ CRM có bản ký; không đổi B/CFO/M4/M9)
    # bản soạn: DA_KY là trạng thái cuối của gói này (không sửa/mở lại/correction); chỉ vào DA_KY từ CHO_KY cùng revision khi đã có bản ký
    """CREATE OR REPLACE FUNCTION master.crm_hd_soan_ky_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF OLD.trang_thai = 'DA_KY' THEN
                IF NEW IS DISTINCT FROM OLD THEN
                    RAISE EXCEPTION 'CRM_GK_DA_KY: bản soạn đã ký — không sửa/xuất lại/mở lại (sửa sau ký chờ quy trình Q-RETURN)' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.trang_thai = 'DA_KY' AND (OLD.trang_thai <> 'CHO_KY' OR NEW.revision_hien_hanh <> OLD.revision_hien_hanh
                                             OR NOT EXISTS (SELECT 1 FROM master.crm_hd_ky k WHERE k.soan_id = NEW.id AND k.revision = NEW.revision_hien_hanh)) THEN
                RAISE EXCEPTION 'CRM_KY_TRANG_THAI: chỉ chuyển DA_KY từ CHO_KY cùng revision khi đã có bản ký' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_hd_soan_ky_khoa BEFORE UPDATE ON master.crm_hd_soan FOR EACH ROW EXECUTE FUNCTION master.crm_hd_soan_ky_khoa()",
    """CREATE OR REPLACE FUNCTION master.hop_dong_gk_ky_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF OLD.crm_giao_ket IS NULL THEN
                RETURN NEW;
            END IF;
            IF OLD.crm_giao_ket = 'DA_KY' THEN
                IF NEW IS DISTINCT FROM OLD THEN
                    RAISE EXCEPTION 'CRM_GK_DA_KY: hợp đồng CRM đã ký — không sửa/mở lại (sửa sau ký chờ quy trình Q-RETURN)' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.crm_giao_ket = 'DA_KY' AND (OLD.crm_giao_ket <> 'CHO_KY' OR NOT EXISTS (SELECT 1 FROM master.crm_hd_ky k WHERE k.hop_dong_id = NEW.id)) THEN
                RAISE EXCEPTION 'CRM_KY_TRANG_THAI: chỉ chuyển DA_KY từ CHO_KY khi đã có bản ký' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER hop_dong_gk_ky_khoa BEFORE UPDATE ON master.hop_dong FOR EACH ROW EXECUTE FUNCTION master.hop_dong_gk_ky_khoa()",
    # lưu revision mới / đặt chỗ xuất mới / công bố xuất hiện hành trên bản soạn đã ký → chặn (công bố muộn chỉ được ghi DA_CU)
    """CREATE OR REPLACE FUNCTION master.crm_hd_soan_rev_ky_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM master.crm_hd_soan s WHERE s.id = NEW.soan_id AND s.trang_thai = 'DA_KY') THEN
                RAISE EXCEPTION 'CRM_GK_DA_KY: bản soạn đã ký — không lưu revision mới' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_hd_soan_rev_ky_khoa BEFORE INSERT ON master.crm_hd_soan_rev FOR EACH ROW EXECUTE FUNCTION master.crm_hd_soan_rev_ky_khoa()",
    """CREATE OR REPLACE FUNCTION master.crm_gk_lan_ky_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NEW.hanh_dong = 'CRM_SOAN_XUAT' AND EXISTS (SELECT 1 FROM master.crm_hd_soan s WHERE s.id = NEW.dich_id AND s.trang_thai = 'DA_KY') THEN
                RAISE EXCEPTION 'CRM_GK_DA_KY: bản soạn đã ký — không xuất lần mới' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_gk_lan_ky_khoa BEFORE INSERT ON master.crm_gk_lan FOR EACH ROW EXECUTE FUNCTION master.crm_gk_lan_ky_khoa()",
    """CREATE OR REPLACE FUNCTION master.crm_gk_xuat_ky_khoa() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        BEGIN
            IF NEW.loai = 'HOP_DONG' AND NEW.trang_thai <> 'DA_CU'
               AND EXISTS (SELECT 1 FROM master.crm_hd_soan s WHERE s.id = NEW.soan_id AND s.trang_thai = 'DA_KY') THEN
                RAISE EXCEPTION 'CRM_GK_DA_KY: bản soạn đã ký — lần xuất muộn chỉ được ghi lịch sử DA_CU' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER crm_gk_xuat_ky_khoa BEFORE INSERT ON master.crm_gk_xuat FOR EACH ROW EXECUTE FUNCTION master.crm_gk_xuat_ky_khoa()",
    _KY_XG,
    # ======================================================================= quyền ký/đọc HIỆN HÀNH (không vai mới; không suy từ người tạo)
    # phạm vi hiện hành dùng chung (một predicate, hai action hẹp cố định bởi hàm bọc bên dưới): người dùng hoạt động của phiên + module CRM trên PN
    # + vai hiện hành + phân công p_hanh hiện hành (loại hình) + phạm vi còn hiệu lực khớp HĐ/bản soạn + dự án (HĐ và dữ liệu revision hiện hành)
    # + khách (mã đối tác, hoặc digest khách dự thảo khi chưa có mã). Thiếu/cũ/thu hồi phân công hoặc phạm vi → false (fail closed).
    """CREATE OR REPLACE FUNCTION master.crm_ky_pham_vi_hd(p_soan uuid, p_hanh text, p_vai text[]) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT p_hanh IN ('CRM_KY_KET', 'CRM_KY_DOC') AND EXISTS (
            SELECT 1
            FROM master.crm_hd_soan s
            JOIN master.hop_dong h ON h.id = s.hop_dong_id AND h.phap_nhan_id = s.phap_nhan_id
            JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
            JOIN master.crm_ky_pham_vi b ON b.soan_id = s.id AND b.hop_dong_id = h.id AND b.phap_nhan_id = s.phap_nhan_id AND b.thu_hoi_luc IS NULL
            JOIN master.phan_cong_hanh_dong a ON a.id = b.phan_cong_id AND a.thu_hoi_luc IS NULL AND a.phap_nhan_id = s.phap_nhan_id
                 AND a.module = 'CRM' AND a.hanh_dong = p_hanh AND (a.loai_hinh_id IS NULL OR a.loai_hinh_id = s.loai_hinh_id)
            JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id AND n.trang_thai = 'HOAT_DONG'
            WHERE s.id = p_soan
              AND n.dang_nhap = master.ktt_danh_tinh()
              AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
              AND master.ktt_duoc(s.phap_nhan_id, 'CRM')
              AND master.ktt_co_vai(s.phap_nhan_id, p_vai, NULL)
              AND b.du_an_id IS NOT DISTINCT FROM h.du_an_id
              AND b.du_an_id::text IS NOT DISTINCT FROM nullif(r.du_lieu -> 'bao_gia' ->> 'du_an_id', '')
              AND ((b.doi_tac_id IS NOT NULL AND b.doi_tac_id = h.doi_tac_id
                    AND b.doi_tac_id::text IS NOT DISTINCT FROM (r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id'))
                   OR (b.khach_du_thao_sha256 IS NOT NULL AND h.doi_tac_id IS NULL
                       AND (r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id') IS NULL
                       AND jsonb_typeof(r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao') = 'object'
                       AND b.khach_du_thao_sha256 = """ + _KY_DU_THAO_SHA + """)))
        $$""",
    # người ký: vai BAN_HANG + phân công CRM_KY_KET + phạm vi hiện hành (quyền ký tách riêng quyền đọc)
    """CREATE OR REPLACE FUNCTION master.crm_ky_pham_vi_duoc(p_soan uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT master.crm_ky_pham_vi_hd(p_soan, 'CRM_KY_KET', ARRAY['BAN_HANG'])
        $$""",
    # đọc bản ký/căn cứ/hash/tải: người ký trong phạm vi, HOẶC KT/KTT/CFO có vai hiện hành + phân công hẹp CRM_KY_DOC + phạm vi tường minh còn
    # hiệu lực đúng PN/dự án/khách/HĐ. Vai KT/KTT/CFO + PN + module KHÔNG đủ (không cấp rộng, không suy từ người tạo, không tự cấp DEMO).
    """CREATE OR REPLACE FUNCTION master.crm_ky_doc_duoc(p_soan uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM master.crm_hd_soan s WHERE s.id = p_soan AND master.ktt_duoc(s.phap_nhan_id, 'CRM')
                       AND (master.crm_ky_pham_vi_duoc(s.id)
                            OR master.crm_ky_pham_vi_hd(s.id, 'CRM_KY_DOC', ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'])))
        $$""",
    # đích + quyền ký hiện hành: ngoài PN/module → 404 ẩn; thiếu vai/phân công → 403; thiếu/cũ/thu hồi phạm vi → 403 chưa cấu hình phạm vi
    """CREATE OR REPLACE FUNCTION master.crm_ky_dich(p_soan uuid, OUT pn uuid)
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE s record;
        BEGIN
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan;
            IF s.id IS NULL OR NOT master.ktt_duoc(s.phap_nhan_id, 'CRM') OR NOT master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản soạn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.ktt_co_vai(s.phap_nhan_id, ARRAY['BAN_HANG'], NULL)
               OR NOT master.ktt_hanh_dong_duoc(s.phap_nhan_id, 'CRM', 'CRM_KY_KET', s.loai_hinh_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_CO_QUYEN: phiên không có quyền ký hiện hành (vai Bán hàng + phân công CRM_KY_KET)' USING ERRCODE = 'P0001';
            END IF;
            IF NOT master.crm_ky_pham_vi_duoc(s.id) THEN
                RAISE EXCEPTION 'CRM_KY_CHUA_CO_PHAM_VI: chưa cấu hình phạm vi ký hiện hành cho hợp đồng/dự án/khách này' USING ERRCODE = 'P0001';
            END IF;
            pn := s.phap_nhan_id;
        END $$""",
    # preflight TRONG giao dịch của người gọi: ghim quyền + phạm vi (FOR SHARE) → đích/quyền → biên nhận dưới khóa namespace (cùng H → FINAL cũ;
    # khác H → 409). Không ghi gì; trước mọi đọc căn cứ/kho/bytes.
    """CREATE OR REPLACE FUNCTION master.crm_ky_tra(p_khoa text, p_soan uuid, p_h text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE d record; cu jsonb;
        BEGIN""" + _G_CHU + """
            PERFORM master.crm_g_ghim_quyen((SELECT s.phap_nhan_id FROM master.crm_hd_soan s WHERE s.id = p_soan));
            PERFORM 1 FROM master.crm_ky_pham_vi b WHERE b.soan_id = p_soan AND b.thu_hoi_luc IS NULL FOR SHARE;
            SELECT * INTO d FROM master.crm_ky_dich(p_soan);
            IF p_khoa IS NULL THEN
                RETURN NULL;
            END IF;
            cu := master.crm_g_bn_tra(d.pn, 'CRM_KY_KET', p_khoa, p_h);
            RETURN CASE WHEN cu IS NULL THEN NULL ELSE jsonb_build_object('lap_lai', true, 'ket_qua', cu) END;
        END $$""",
    """CREATE OR REPLACE FUNCTION master.crm_ky_kq(p_ky uuid) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, pg_temp AS $$
        SELECT jsonb_build_object('ky_id', k.id, 'soan_id', k.soan_id, 'hop_dong_id', k.hop_dong_id, 'revision', k.revision, 'xuat_id', k.xuat_id,
                                  'trang_thai', 'DA_KY', 'hien_thi', '""" + _KY_HIEN_THI + """', 'ngay_ky', k.ngay_ky, 'co_sua', k.co_sua,
                                  'ky_pdf_sha256', k.ky_pdf_sha256, 'ky_pdf_len', k.ky_pdf_len, 'g3_pdf_sha256', k.g3_pdf_sha256,
                                  'g5', jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do))
        FROM master.crm_hd_ky k JOIN master.crm_hd_ky_g5 g ON g.ky_id = k.id WHERE k.id = p_ky
        $$""",
    # lệnh ký lần đầu (READ COMMITTED, dưới khóa namespace biên nhận; khóa bản soạn + HĐ FOR UPDATE): quyền/phạm vi → biên nhận → khai báo/ngày →
    # đã ký? (cùng PDF + cùng căn cứ/ngày/khai báo → cùng bản ký, 0 hàng mới; khác → Q-RETURN) → CHO_KY + CAS revision + bản xuất mới nhất =
    # bản đã chụp + PDF_DAT + lineage G3 → ghi bản ký + G5 khởi tạo + DA_KY + nhật ký (không PII) + biên nhận.
    """CREATE OR REPLACE FUNCTION master.crm_ky_ket(p_khoa text, p_h text, p_soan uuid, p_expected integer, p_xuat uuid, p_g3_input_sha text,
                                                 p_g3_pdf_sha text, p_g3_pdf_len bigint, p_ky_sha text, p_ky_len bigint, p_so_trang integer, p_ten text,
                                                 p_ngay date, p_co_sua boolean, p_mo_ta text, p_nguoi_ky text, p_tom_tat jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, kho, pg_temp AS $$
        DECLARE """ + _GK_KHAI + """ s record; h record; k record; xm record; r record; kid uuid;
        BEGIN""" + _G_CHU + """
            PERFORM master.crm_g_ghim_quyen((SELECT s0.phap_nhan_id FROM master.crm_hd_soan s0 WHERE s0.id = p_soan));
            PERFORM 1 FROM master.crm_ky_pham_vi b WHERE b.soan_id = p_soan AND b.thu_hoi_luc IS NULL FOR SHARE;
            SELECT * INTO d FROM master.crm_ky_dich(p_soan);""" + _G_REPLAY.format(a="'CRM_KY_KET'") + """
            IF p_co_sua IS NULL OR (p_co_sua AND (p_mo_ta IS NULL OR btrim(p_mo_ta) = '' OR length(p_mo_ta) > 2000))
               OR (NOT p_co_sua AND p_mo_ta IS NOT NULL) THEN
                RAISE EXCEPTION 'CRM_KY_KHAI_SAI: phải khai Có (kèm mô tả) hoặc Không' USING ERRCODE = 'P0001';
            END IF;
            IF p_ngay IS NULL OR p_ngay > master.ktt_ngay() THEN
                RAISE EXCEPTION 'CRM_KY_NGAY_SAI: ngày ký phải có và không sau hôm nay' USING ERRCODE = 'P0001';
            END IF;
            IF p_expected IS NULL OR p_xuat IS NULL OR p_ky_sha IS NULL OR p_ky_sha !~ '^[0-9a-f]{64}$' OR p_ky_len IS NULL OR p_ky_len <= 0
               OR p_so_trang IS NULL OR p_so_trang < 1 OR p_g3_input_sha IS NULL OR p_g3_pdf_sha IS NULL OR p_g3_pdf_len IS NULL OR p_tom_tat IS NULL
               OR jsonb_typeof(p_tom_tat) <> 'object' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: thiếu căn cứ ký' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan FOR UPDATE;
            SELECT * INTO h FROM master.hop_dong WHERE id = s.hop_dong_id FOR UPDATE;
            SELECT * INTO k FROM master.crm_hd_ky WHERE hop_dong_id = s.hop_dong_id;
            IF k.id IS NOT NULL THEN
                IF k.ky_pdf_sha256 = p_ky_sha AND k.ky_pdf_len = p_ky_len AND k.xuat_id = p_xuat AND k.revision = p_expected AND k.ngay_ky = p_ngay
                   AND k.co_sua = p_co_sua AND k.mo_ta_sua IS NOT DISTINCT FROM p_mo_ta AND k.nguoi_ky_khach IS NOT DISTINCT FROM p_nguoi_ky THEN
                    RETURN jsonb_build_object('lap_lai', true, 'ket_qua', master.crm_ky_kq(k.id));  -- cùng PDF/căn cứ/khai báo, khóa mới: 0 hàng mới
                END IF;
                RAISE EXCEPTION 'CRM_KY_DA_KY: hợp đồng đã ký lần đầu — không thay bản ký/ngày/khai báo (sửa sau ký chờ quy trình Q-RETURN)' USING ERRCODE = 'P0001';
            END IF;
            IF s.trang_thai <> 'CHO_KY' OR h.crm_giao_ket IS DISTINCT FROM 'CHO_KY' THEN
                RAISE EXCEPTION 'CRM_KY_TRANG_THAI: chỉ ký bản soạn đang Chờ ký (hiện %)', s.trang_thai USING ERRCODE = 'P0001';
            END IF;
            IF p_expected IS DISTINCT FROM s.revision_hien_hanh THEN
                RAISE EXCEPTION 'CRM_GK_REVISION_CU: bản soạn đã có revision mới — tải lại căn cứ rồi ký' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO xm FROM master.crm_gk_xuat WHERE soan_id = s.id AND loai = 'HOP_DONG' AND revision = s.revision_hien_hanh
                ORDER BY tao_luc DESC, id DESC LIMIT 1;
            IF xm.id IS NULL OR xm.id <> p_xuat THEN
                RAISE EXCEPTION 'CRM_KY_XUAT_CU: đã có bản xuất mới hơn (hoặc bản xuất không thuộc revision hiện hành) — tải lại căn cứ' USING ERRCODE = 'P0001';
            END IF;
            IF xm.trang_thai <> 'PDF_DAT' OR xm.pdf_sha256 IS NULL THEN
                RAISE EXCEPTION 'CRM_KY_XUAT_CHUA_DAT: bản xuất hiện hành chưa có PDF đạt — chưa ký được' USING ERRCODE = 'P0001';
            END IF;
            IF xm.input_sha256 <> p_g3_input_sha OR xm.pdf_sha256 <> p_g3_pdf_sha OR xm.pdf_len <> p_g3_pdf_len THEN
                RAISE EXCEPTION 'CRM_KY_G3_LECH: căn cứ G3 máy chủ kiểm lại không khớp bản xuất đã công bố' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO r FROM master.crm_hd_soan_rev WHERE soan_id = s.id AND revision = xm.revision;
            IF master.crm_g_danh_muc_digest(s.loai_hinh_id, r.danh_muc_ref, r.danh_muc_rev) IS DISTINCT FROM r.danh_muc_digest THEN
                RAISE EXCEPTION 'CRM_GK_MAU_LECH_GHIM: danh mục đã ghim không còn khớp' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.crm_hd_ky (phap_nhan_id, hop_dong_id, soan_id, revision, soan_rev_id, xuat_id, g3_input_sha256, g3_docx_sha256, g3_docx_len,
                                          g3_pdf_sha256, g3_pdf_len, g3_engine, mau_phien_ban_id, anh_xa_id, kiem_id, raw_sha256, ban_do_sha256,
                                          danh_muc_ref, danh_muc_rev, danh_muc_digest, profile_phien_ban, profile_sha256, du_lieu_sha256, tom_tat,
                                          ky_pdf_sha256, ky_pdf_len, ky_so_trang, ten_tep, ngay_ky, nguoi_ky_khach, co_sua, mo_ta_sua, tao_boi)
                VALUES (d.pn, s.hop_dong_id, s.id, xm.revision, r.id, xm.id, xm.input_sha256, xm.docx_sha256, xm.docx_len, xm.pdf_sha256, xm.pdf_len,
                        xm.engine, r.mau_phien_ban_id, r.anh_xa_id, r.kiem_id, r.raw_sha256, r.ban_do_sha256, r.danh_muc_ref, r.danh_muc_rev,
                        r.danh_muc_digest, r.profile_phien_ban, r.profile_sha256, r.du_lieu_sha256, p_tom_tat, p_ky_sha, p_ky_len, p_so_trang, p_ten,
                        p_ngay, p_nguoi_ky, p_co_sua, p_mo_ta, ai) RETURNING id INTO kid;
            INSERT INTO master.crm_hd_ky_g5 (ky_id, phap_nhan_id, trang_thai, ly_do)
                VALUES (kid, d.pn, CASE WHEN p_co_sua THEN 'PENDING' ELSE 'NOT_SELECTED' END,
                        CASE WHEN p_co_sua THEN 'BAT_BUOC_KHAI_CO' ELSE 'CHUA_AP_DUNG_CHON_MAU' END);
            UPDATE master.crm_hd_soan SET trang_thai = 'DA_KY', cap_nhat_luc = clock_timestamp() WHERE id = s.id;
            UPDATE master.hop_dong SET trang_thai = 'DA_KY', crm_giao_ket = 'DA_KY' WHERE id = s.hop_dong_id;
            """ + _G_NK.format(pn="d.pn", loai="'QUYET_DINH'", bang="'master.crm_hd_ky'", id="kid", hd="'CRM_KY_KET'",
                               sau="jsonb_build_object('soan_id', s.id, 'revision', xm.revision, 'xuat_id', xm.id, 'ky_pdf_sha256', p_ky_sha, 'co_sua', p_co_sua)",
                               ly="NULL") + """
            kq := master.crm_ky_kq(kid);""" + _G_KET.format(a="'CRM_KY_KET'") + """
        END $$""",
    # đọc điều kiện/căn cứ dialog + bản ký + lịch sử: thấy bản soạn theo quyền CRM_SOAN hiện có (hoặc người đọc bản ký); hash/căn cứ/bản ký chỉ
    # trả cho người ký trong phạm vi hoặc KT/KTT/CFO có phân công CRM_KY_DOC + phạm vi tường minh hiện hành (crm_ky_doc_duoc). Đã ký → căn cứ là
    # snapshot của bản xuất đã ký (không đọc nháp hiện hành thay thế).
    """CREATE OR REPLACE FUNCTION master.crm_ky_doc(p_soan uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE s record; h record; k record; g record; xm record; r record; v record; vai boolean; ky boolean; doc boolean; kq jsonb;
        BEGIN""" + _G_CHU + """
            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan;
            IF s.id IS NULL OR NOT master.ktt_duoc(s.phap_nhan_id, 'CRM')
               OR NOT (master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id) OR master.crm_ky_doc_duoc(s.id)) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản soạn (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM master.hop_dong WHERE id = s.hop_dong_id;
            vai := master.ktt_co_vai(s.phap_nhan_id, ARRAY['BAN_HANG'], NULL)
                   AND master.ktt_hanh_dong_duoc(s.phap_nhan_id, 'CRM', 'CRM_KY_KET', s.loai_hinh_id);
            ky := vai AND master.crm_ky_pham_vi_duoc(s.id);
            doc := master.crm_ky_doc_duoc(s.id);
            kq := jsonb_build_object('soan_id', s.id, 'hop_dong_id', s.hop_dong_id, 'ma_noi_bo', h.ma_noi_bo, 'trang_thai', s.trang_thai,
                                     'revision', s.revision_hien_hanh, 'hien_thi', CASE WHEN s.trang_thai = 'DA_KY' THEN '""" + _KY_HIEN_THI + """' END,
                                     'quyen', jsonb_build_object('ky', ky AND s.trang_thai = 'CHO_KY', 'doc', doc,
                                                                 'ly_do', CASE WHEN ky THEN NULL WHEN NOT vai THEN 'CRM_G_KHONG_CO_QUYEN'
                                                                               ELSE 'CRM_KY_CHUA_CO_PHAM_VI' END));
            IF NOT doc THEN
                RETURN kq;
            END IF;
            SELECT * INTO k FROM master.crm_hd_ky WHERE soan_id = s.id;
            IF k.id IS NOT NULL THEN
                SELECT * INTO xm FROM master.crm_gk_xuat WHERE id = k.xuat_id;
            ELSE
                SELECT * INTO xm FROM master.crm_gk_xuat WHERE soan_id = s.id AND loai = 'HOP_DONG' AND revision = s.revision_hien_hanh
                    ORDER BY tao_luc DESC, id DESC LIMIT 1;
            END IF;
            IF xm.id IS NOT NULL THEN
                SELECT * INTO r FROM master.crm_hd_soan_rev WHERE soan_id = s.id AND revision = xm.revision;
                SELECT pv.phien_ban, pv.ten_tep, m.ma_mau INTO v FROM master.crm_mau_phien_ban pv JOIN master.crm_mau m ON m.id = pv.mau_id
                    WHERE pv.id = r.mau_phien_ban_id;
                kq := kq || jsonb_build_object('can_cu', jsonb_build_object(
                    'xuat_id', xm.id, 'revision', xm.revision, 'trang_thai', xm.trang_thai, 'tao_luc', xm.tao_luc, 'pdf_sha256', xm.pdf_sha256,
                    'pdf_len', xm.pdf_len, 'docx_sha256', xm.docx_sha256, 'engine', xm.engine, 'mau_phien_ban_id', r.mau_phien_ban_id,
                    'ma_mau', v.ma_mau, 'phien_ban_mau', v.phien_ban, 'raw_sha256', r.raw_sha256, 'danh_muc_ref', r.danh_muc_ref,
                    'danh_muc_rev', r.danh_muc_rev, 'profile_phien_ban', r.profile_phien_ban, '_bao_gia', r.du_lieu -> 'bao_gia'));
            END IF;
            IF k.id IS NOT NULL THEN
                SELECT * INTO g FROM master.crm_hd_ky_g5 WHERE ky_id = k.id;
                kq := kq || jsonb_build_object('ban_ky', jsonb_build_object(
                    'ky_id', k.id, 'revision', k.revision, 'xuat_id', k.xuat_id, 'ngay_ky', k.ngay_ky, 'nguoi_ky_khach', k.nguoi_ky_khach,
                    'co_sua', k.co_sua, 'mo_ta_sua', k.mo_ta_sua, 'ky_pdf_sha256', k.ky_pdf_sha256, 'ky_pdf_len', k.ky_pdf_len,
                    'ky_so_trang', k.ky_so_trang, 'g3_pdf_sha256', k.g3_pdf_sha256, 'g3_pdf_len', k.g3_pdf_len, 'g3_docx_sha256', k.g3_docx_sha256,
                    'mau_phien_ban_id', k.mau_phien_ban_id, 'raw_sha256', k.raw_sha256, 'profile_phien_ban', k.profile_phien_ban, 'tom_tat', k.tom_tat,
                    'tao_boi', k.tao_boi, 'tao_luc', k.tao_luc, 'hien_thi', '""" + _KY_HIEN_THI + """',
                    'g5', jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do)),
                  'lich_su', (SELECT coalesce(jsonb_agg(jsonb_build_object('luc', e.luc, 'nguoi', e.nguoi, 'hanh_dong', e.hanh_dong) ORDER BY e.id), '[]'::jsonb)
                              FROM nhat_ky.su_kien e WHERE e.doi_tuong_bang = 'master.crm_hd_ky' AND e.doi_tuong_id = k.id));
            END IF;
            RETURN kq;
        END $$""",
    # tải bản ký: quyền đọc hiện hành TRƯỚC trả hash/độ dài (máy chủ mới tra kho); ghi nhật ký truy cập (actor/đối tượng/mục đích/hash/thời điểm;
    # không tên tệp/người ký/PII)
    """CREATE OR REPLACE FUNCTION master.crm_ky_tep(p_ky uuid, p_muc_dich text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); k record;
        BEGIN""" + _G_CHU + """
            SELECT * INTO k FROM master.crm_hd_ky WHERE id = p_ky;
            IF k.id IS NOT NULL THEN  -- ghim quyền + phạm vi hiện hành tới hết giao dịch (thu hồi đồng thời không lọt giữa kiểm và nhật ký/hash)
                PERFORM master.crm_g_ghim_quyen(k.phap_nhan_id);
                PERFORM 1 FROM master.crm_ky_pham_vi b WHERE b.soan_id = k.soan_id AND b.thu_hoi_luc IS NULL FOR SHARE;
            END IF;
            IF k.id IS NULL OR ai IS NULL OR NOT master.crm_ky_doc_duoc(k.soan_id) THEN
                RAISE EXCEPTION 'CRM_G_KHONG_THAY: không thấy bản ký (hoặc ngoài phạm vi)' USING ERRCODE = 'P0001';
            END IF;
            IF p_muc_dich IS DISTINCT FROM 'TAI_BAN_KY' THEN
                RAISE EXCEPTION 'CRM_G_YEU_CAU_SAI: mục đích tải không hợp lệ' USING ERRCODE = 'P0001';
            END IF;
            """ + _G_NK.format(pn="k.phap_nhan_id", loai="'HE_THONG'", bang="'master.crm_hd_ky'", id="k.id", hd="'CRM_KY_TAI'",
                               sau="jsonb_build_object('muc_dich', p_muc_dich, 'ky_pdf_sha256', k.ky_pdf_sha256)", ly="NULL") + """
            RETURN jsonb_build_object('ky_id', k.id, 'sha256', k.ky_pdf_sha256, 'len', k.ky_pdf_len, 'revision', k.revision,
                                      'ten', (SELECT h.ma_noi_bo FROM master.hop_dong h WHERE h.id = k.hop_dong_id));
        END $$""",
    # ======================================================================= quyền: bảng mới không cấp cho vai ứng dụng; hàm không cấp PUBLIC
    *(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY" for t in _KY_BANG_MOI),
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE ALL ON master.crm_ky_pham_vi, master.crm_hd_ky, master.crm_hd_ky_g5 FROM %I', r);
            END IF;
        END LOOP;
    END $$""",
    "REVOKE ALL ON master.crm_ky_pham_vi, master.crm_hd_ky, master.crm_hd_ky_g5 FROM PUBLIC",
    """REVOKE EXECUTE ON FUNCTION master.crm_ky_pham_vi_hd(uuid, text, text[]), master.crm_ky_pham_vi_duoc(uuid), master.crm_ky_doc_duoc(uuid),
        master.crm_ky_dich(uuid), master.crm_ky_tra(text, uuid, text),
        master.crm_ky_kq(uuid), master.crm_ky_ket(text, text, uuid, integer, uuid, text, text, bigint, text, bigint, integer, text, date, boolean, text, text, jsonb),
        master.crm_ky_doc(uuid), master.crm_ky_tep(uuid, text) FROM PUBLIC""",
)

PG_MIGRATIONS = (*PG_MIGRATIONS, M0023_CRM_KY)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0024 — M4-02C duyệt hồ sơ đợt (APPEND sau toàn bộ 1–23; không sửa byte/định nghĩa/checksum 1–23).
#        Định nghĩa trong m4/sql_duyet.py (chỉ hằng SQL): phiên bản hồ sơ đợt, kết luận, chấp thuận (vai dự án DUYET riêng), PDF hồ sơ đã duyệt,
#        seal bất biến + một gốc KT chờ xác nhận/đợt + phong bì/seal. Không AP, không Request, không master mới.
# ---------------------------------------------------------------------------
from ..m4.sql_duyet import M0024_M4_DUYET  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

PG_MIGRATIONS = (*PG_MIGRATIONS, M0024_M4_DUYET)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0025 — CRM-41-06A (G6A) kế toán kiểm hợp đồng đã ký → HIEU_LUC (APPEND sau toàn bộ 1–24; không sửa byte/định nghĩa/checksum 1–24).
#        Định nghĩa trong k2/sql_crm_kiem_hd.py (chỉ hằng SQL, không import ha_tang): đăng ký ĐÚNG MỘT lần, cùng object CRM_G6A_SQL (alias,
#        không sao chép/dựng lại). G5 VAN_HANH vẫn HOLD (UNREGISTERED_G5_PROOF) — registry không tạo producer/policy G5.
# ---------------------------------------------------------------------------
from ..k2.sql_crm_kiem_hd import CRM_G6A_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0025_CRM_G6A = CRM_G6A_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0025_CRM_G6A)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0026 — M4-03A kế toán xác nhận nguồn nghiệm thu (APPEND sau toàn bộ 1–25; không sửa byte/định nghĩa/checksum 1–25).
#        Định nghĩa trong m4/sql_ke_toan_nghiem_thu.py (chỉ hằng SQL, không import ha_tang): đăng ký ĐÚNG MỘT lần, cùng object M4_03A_SQL
#        (alias, không sao chép/dựng lại). Không AP, không Request, không bút toán.
# ---------------------------------------------------------------------------
from ..m4.sql_ke_toan_nghiem_thu import M4_03A_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0026_M4_KT = M4_03A_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0026_M4_KT)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0027 — M4-04C Request nháp từ hồ sơ đợt đã seal (APPEND sau toàn bộ 1–26; không sửa byte/định nghĩa/checksum 1–26).
#        Định nghĩa trong m4/sql_request_nhap.py (chỉ hằng SQL, không import ha_tang): đăng ký ĐÚNG MỘT lần, cùng object M4_REQUEST_NHAP
#        (alias, không sao chép/dựng lại). Backend Request vận hành thật vẫn OFF; không AP, không bút toán.
# ---------------------------------------------------------------------------
from ..m4.sql_request_nhap import M4_REQUEST_NHAP  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0027_M4_REQUEST = M4_REQUEST_NHAP
PG_MIGRATIONS = (*PG_MIGRATIONS, M0027_M4_REQUEST)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0028 — M4 master dùng chung: nhận HĐ master, gắn đối tác, căn cứ master/mapping (APPEND sau toàn bộ 1–27; không sửa byte/định nghĩa/checksum 1–27;
#        định nghĩa trong m4/sql_master_dung_chung.py (chỉ hằng SQL, không import ha_tang): đúng kế M17 (m4 lõi) và M24 (m4.duyet_phien_ban); chỉ THÊM
#        2 bảng ghi-thêm + hàm + trigger quan sát + một policy SELECT hẹp trên master.hop_dong; không sao chép/dựng lại SQL ở đây.
# ---------------------------------------------------------------------------
from ..m4.sql_master_dung_chung import M4_MASTER_DUNG_CHUNG_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0028_M4_MASTER_DUNG_CHUNG = M4_MASTER_DUNG_CHUNG_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0028_M4_MASTER_DUNG_CHUNG)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0029 — M4-03B ghi nhận chung: identity nguồn kinh tế M2–M4 + đối chiếu căn cứ nghiệm thu ↔ hóa đơn do KT xác nhận (APPEND sau toàn bộ 1–28; không sửa
#        byte/định nghĩa/checksum 1–28; định nghĩa trong k2/sql_ghi_nhan_chung.py gồm FIX01–FIX04 (chỉ hằng SQL, không import ha_tang): tham chiếu
#        m4.kt_xac_nhan của M26 nên phải sau M26; nới CHECK module kho.bien_nhan_thao_tac thêm 'M4' + trigger biên nhận chủ bảng; không AP, không Request.
# ---------------------------------------------------------------------------
from ..k2.sql_ghi_nhan_chung import M4_03B_COMMON_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0029_M4_GHI_NHAN_CHUNG = M4_03B_COMMON_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0029_M4_GHI_NHAN_CHUNG)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0030 — BG-1c CRM · Báo giá: bước kiểm khi Ký tính Tổng VND = round(đơn giá × tỷ giá × diện tích, 0) cho báo giá v2 (tien_chinh = VND) và đọc
#        ghi đè tổng (APPEND sau toàn bộ 1–29; không sửa byte/định nghĩa/checksum 1–29, không sửa M0025). Định nghĩa trong k2/sql_crm_bg1c.py
#        (chỉ hằng SQL, không import ha_tang): CHỈ `CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(uuid)` — cùng chữ ký/kiểu trả/hình dạng jsonb.
# ---------------------------------------------------------------------------
from ..k2.sql_crm_bg1c import CRM_BG1C_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0030_CRM_BG1C = CRM_BG1C_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0030_CRM_BG1C)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0031 — DA-1 CRM · Dự án đang bán (QD-20261025-05…09; APPEND sau toàn bộ 1–30; không sửa byte/định nghĩa/checksum 1–30). Định nghĩa trong
#        k2/sql_crm_du_an_ban.py (chỉ hằng SQL, không import ha_tang): thông tin bán hàng của dự án (gắn master.du_an) có phiên bản bất biến + phí
#        tiêu chuẩn + lô/căn có lịch sử; G7 áp dụng ngay cho bán hàng (bỏ CFO, QD-07) + nới đúng một CHECK valid_to của crm_bo_chuan_phien_ban.
# ---------------------------------------------------------------------------
from ..k2.sql_crm_du_an_ban import CRM_DU_AN_BAN_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0031_CRM_DU_AN_BAN = CRM_DU_AN_BAN_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0031_CRM_DU_AN_BAN)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0032 — CRM-41 G5-B đối chiếu bản ký ↔ bản sinh (APPEND sau toàn bộ 1–31; không sửa byte/định nghĩa/checksum 1–31). Định nghĩa trong
#        k2/sql_crm_doi_chieu.py (chỉ hằng SQL, không import ha_tang; module ghi rõ "owner cấp ordinal và APPEND") — lead cấp ordinal 25/10/2026
#        vì S1 (C3) và worker G5 của máy chủ đọc các bảng/hàm này (thiếu thì PostgreSQL báo crm_g5_* không tồn tại). Không seed đăng ký engine;
#        G5 VAN_HANH vẫn HOLD như M0025 ghi.
# ---------------------------------------------------------------------------
from ..k2.sql_crm_doi_chieu import CRM_G5_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang

M0032_CRM_G5 = CRM_G5_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0032_CRM_G5)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0033 — M4 · Nghiệm thu & chi phí dự án: 03B khai một phần bằng số tiền + dữ liệu gợi ý.
# APPEND sau 1–32; không sửa dữ liệu tỷ lệ cũ hoặc module SQL M0029 đã ghim hash.
# ---------------------------------------------------------------------------
from ..k2.sql_ghi_nhan_so_tien import M4_03B_SO_TIEN_SQL  # noqa: E402 — chỉ hằng SQL

M0033_M4_03B_SO_TIEN = M4_03B_SO_TIEN_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0033_M4_03B_SO_TIEN)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0034 — AI-2b: metadata cổng AI (TL 48 §1.1), APPEND sau M0033; không đổi migration cũ.
#        Ánh xạ BanGhiCongAI cần 11 cột mới (không phải 9). Cột mới để NULL cho
#        bản ghi lịch sử khi chưa có metadata; không UPDATE nhật ký cũ.
# ---------------------------------------------------------------------------
M0034_CONG_AI_NHAT_KY = (
    """ALTER TABLE nhat_ky.cong_ai_goi
        ADD COLUMN ma_yeu_cau text,
        ADD COLUMN duong text CHECK (duong IN ('LOCAL', 'CLOUD') AND cloud = (duong = 'CLOUD')),
        ADD COLUMN da_gui boolean,
        ADD COLUMN so_ky_tu_gui integer CHECK (so_ky_tu_gui >= 0),
        ADD COLUMN so_ky_tu_nhan integer CHECK (so_ky_tu_nhan >= 0),
        ADD COLUMN ma_luot_mask text,
        ADD COLUMN ly_do_chuyen_cloud text[],
        ADD COLUMN ly_do_khong_gui text,
        ADD COLUMN ket_qua text CHECK (ket_qua IN ('DAT', 'KHONG_CHAC', 'KHONG_DUNG_DUOC', 'LOI', 'KHONG_GUI')),
        ADD COLUMN ly_do text[],
        ADD COLUMN so_truong_bi_loai integer CHECK (so_truong_bi_loai >= 0)""",
    # Hai cột cũ không dùng: chặn nội dung mới, không xét/sửa dữ liệu lịch sử.
    """ALTER TABLE nhat_ky.cong_ai_goi ADD CONSTRAINT cong_ai_goi_khong_noi_dung
        CHECK (dau_vao_mask_hash IS NULL AND ket_qua_tom_tat IS NULL) NOT VALID""",
    "CREATE INDEX cong_ai_goi_ma_yeu_cau ON nhat_ky.cong_ai_goi (ma_yeu_cau)",
    # Giữ trigger chi_ghi_them/chan_truncate của M0005/M0009; quyền như nhật ký khác.
    "REVOKE ALL ON nhat_ky.cong_ai_goi FROM PUBLIC",
    """DO $$
    DECLARE r text;
    BEGIN
        FOREACH r IN ARRAY ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON nhat_ky.cong_ai_goi FROM %I', r);
                IF r IN ('app_ke_toan', 'app_cong_ai') THEN
                    EXECUTE format('GRANT SELECT, INSERT ON nhat_ky.cong_ai_goi TO %I', r);
                ELSIF r = 'app_doc' THEN
                    EXECUTE format('GRANT SELECT ON nhat_ky.cong_ai_goi TO %I', r);
                END IF;
            END IF;
        END LOOP;
    END $$""",
)

PG_MIGRATIONS = (*PG_MIGRATIONS, M0034_CONG_AI_NHAT_KY)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# 0035 — MDA-1a: mốc thanh toán riêng của dự án (CD-006, CD-007).
# APPEND sau M0034; không đổi migration cũ. Bảng gốc + lịch sử, lệnh và hàm đọc.
# ---------------------------------------------------------------------------
from ..k2.sql_crm_du_an_moc import CRM_DU_AN_MOC_SQL  # noqa: E402 — chỉ hằng SQL

M0035_CRM_DU_AN_MOC = CRM_DU_AN_MOC_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0035_CRM_DU_AN_MOC)

# ---------------------------------------------------------------------------
# 0036 — KY-DOCX (QD-20261025-27, hệ quả QD-26 "Word → PDF mặc định tắt"): CHO KÝ TRÊN BẢN DOCX. APPEND sau M0035 (mốc dự án); không sửa byte/định nghĩa/
#        checksum 1–35. Mọi hàm dưới đây TẠO LẠI định nghĩa HIỆN HÀNH (M0023 cho G3/G4, M0032 cho G5) bằng thay chuỗi đã kiểm đúng MỘT vị trí —
#        không chép tay thân hàm; mọi kiểm khác (quyền, phạm vi, biên nhận, CAS revision, mẫu/danh mục đã ghim, khóa sau ký) giữ nguyên văn.
#        * crm_gk_xuat_ghi: bản soạn sang CHO_KY khi lần xuất ĐÚNG revision hiện hành được công bố — lần xuất công bố luôn có DOCX đã kiểm (không
#          còn ô, kênh an toàn) ở mọi trạng thái PDF_DAT | PDF_CHUA_SAN_SANG | PDF_LOI; DA_CU (revision đã đổi / đã ký) vẫn không. PDF chỉ tham khảo.
#        * crm_hd_ky: g3_pdf_sha256/g3_pdf_len được NULL (cặp cùng có/cùng NULL); trigger crm_hd_ky_kiem gắn bản ký vào bản xuất theo DOCX + input +
#          engine + revision như cũ, PDF khớp khi bản xuất có PDF (IS DISTINCT FROM: bản xuất không PDF thì bản ký phải NULL); DA_CU vẫn bị chặn.
#        * crm_ky_ket: căn cứ = bản xuất MỚI NHẤT của revision hiện hành có DOCX (không còn đòi PDF_DAT); PDF G3 do máy chủ resolve khớp khi có.
#        * G5 (đối chiếu bản ký ↔ bản sinh): hợp đồng lineage E5 hiện cần PDF G3 → bản ký gắn bản sinh CHỈ DOCX chưa đối chiếu tự động được. Thà
#          bỏ sót: crm_kiem_g5_xet HOLD + chặn G5_BAN_SINH_CHI_DOCX (mọi chế độ, không bao giờ tự KHOP); hàng đợi/nhận việc giữ việc MỞ ở
#          CHO_CAU_HINH lý do G5_BAN_SINH_CHI_DOCX (cần kiểm tay; không ý định/engine); màn G5 báo chưa sẵn sàng + tắt Chạy; Chạy thủ công bị từ
#          chối (CRM_G5_CAN_KIEM_TAY). Không viết bộ đối chiếu mới.
# ---------------------------------------------------------------------------
def _m36_ham(goc: tuple, ten: str) -> str:
    """ĐÚNG một định nghĩa CREATE OR REPLACE FUNCTION master.<ten>( trong migration gốc (định nghĩa hiện hành trước M0036)."""
    ds = [s for s in goc if s.lstrip().startswith(f"CREATE OR REPLACE FUNCTION master.{ten}(")]
    if len(ds) != 1:
        raise RuntimeError(f"M0036: không định vị đúng một định nghĩa master.{ten}")
    return ds[0]


def _m36_thay(stmt: str, *cap: tuple) -> str:
    """Thay lần lượt từng cặp (cũ, mới); mỗi chuỗi cũ phải xuất hiện ĐÚNG một lần (lệch nguồn → dừng import, không áp mù)."""
    for cu, moi in cap:
        if stmt.count(cu) != 1:
            raise RuntimeError("M0036: không định vị đúng một vị trí thay: " + cu.strip()[:100])
        stmt = stmt.replace(cu, moi, 1)
    return stmt


_M36_TT = "('PDF_DAT','PDF_CHUA_SAN_SANG','PDF_LOI')"  # lần xuất đã công bố có DOCX của đúng revision (DA_CU bị loại)
_M36_CHI_DOCX = "EXISTS (SELECT 1 FROM master.crm_hd_ky k0 WHERE k0.id = {ky} AND k0.g3_pdf_sha256 IS NULL)"  # bản ký gắn bản sinh chỉ DOCX
_M36_VIEC_CHO = ("{b}UPDATE master.crm_g5_viec SET trang_thai = 'CHO_CAU_HINH', ly_do = 'G5_BAN_SINH_CHI_DOCX', lease_boi = NULL, lease_den = NULL,\n"
                 "{b}                              thu_lai_sau = now() + interval '15 minutes', cap_nhat_luc = now() WHERE id = v.id;\n")

_M36_XUAT_GHI = _m36_thay(
    _m36_ham(M0023_CRM_KY, "crm_gk_xuat_ghi"),
    ("                IF tt = 'PDF_DAT' THEN\n",
     "                IF tt IN " + _M36_TT + " THEN  -- M0036 (QD-27): DOCX đúng revision là căn cứ ký; PDF chỉ tham khảo\n"))

_M36_HD_KY_KIEM = _m36_thay(
    _m36_ham(M0023_CRM_KY, "crm_hd_ky_kiem"),
    ("               OR x.trang_thai IS DISTINCT FROM 'PDF_DAT' OR x.pdf_sha256 IS DISTINCT FROM NEW.g3_pdf_sha256 OR x.pdf_len IS DISTINCT FROM NEW.g3_pdf_len\n",
     "               OR x.trang_thai IS NULL OR x.trang_thai NOT IN " + _M36_TT + "\n"
     "               OR x.pdf_sha256 IS DISTINCT FROM NEW.g3_pdf_sha256 OR x.pdf_len IS DISTINCT FROM NEW.g3_pdf_len\n"),
    ("'CRM_KY_G3_LECH: bản ký phải gắn đúng bản xuất G3 PDF_DAT và revision đã ghim của bản soạn CHO_KY'",
     "'CRM_KY_G3_LECH: bản ký phải gắn đúng bản xuất G3 (DOCX của revision hiện hành, PDF khớp khi có) và revision đã ghim của bản soạn CHO_KY'"))

_M36_KY_KET = _m36_thay(
    _m36_ham(M0023_CRM_KY, "crm_ky_ket"),
    ("OR p_g3_input_sha IS NULL OR p_g3_pdf_sha IS NULL OR p_g3_pdf_len IS NULL OR p_tom_tat IS NULL",
     "OR p_g3_input_sha IS NULL OR (p_g3_pdf_sha IS NULL) <> (p_g3_pdf_len IS NULL) OR p_tom_tat IS NULL"),
    ("            IF xm.trang_thai <> 'PDF_DAT' OR xm.pdf_sha256 IS NULL THEN\n"
     "                RAISE EXCEPTION 'CRM_KY_XUAT_CHUA_DAT: bản xuất hiện hành chưa có PDF đạt — chưa ký được' USING ERRCODE = 'P0001';\n",
     "            IF xm.trang_thai NOT IN " + _M36_TT + " OR xm.docx_sha256 IS NULL OR xm.docx_len IS NULL THEN  -- M0036 (QD-27): ký trên DOCX\n"
     "                RAISE EXCEPTION 'CRM_KY_XUAT_CHUA_DAT: bản xuất hiện hành chưa có DOCX của revision hiện hành — chưa ký được' USING ERRCODE = 'P0001';\n"),
    ("IF xm.input_sha256 <> p_g3_input_sha OR xm.pdf_sha256 <> p_g3_pdf_sha OR xm.pdf_len <> p_g3_pdf_len THEN",
     "IF xm.input_sha256 <> p_g3_input_sha OR xm.pdf_sha256 IS DISTINCT FROM p_g3_pdf_sha OR xm.pdf_len IS DISTINCT FROM p_g3_pdf_len THEN"))

_M36_KIEM_G5_XET = _m36_thay(
    _m36_ham(CRM_G5_SQL, "crm_kiem_g5_xet"),
    ("            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);\n",
     "            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);\n"
     "            -- M0036 (QD-27): bản ký gắn bản sinh chỉ DOCX → chưa đối chiếu được, cần kiểm tay; HOLD ở MỌI chế độ, không bao giờ tự KHOP\n"
     "            IF " + _M36_CHI_DOCX.format(ky="p_ky") + " THEN\n"
     "                RETURN jsonb_build_object('che_do', CASE WHEN p_che_do = 'SYNTHETIC_FIXTURE' THEN 'SYNTHETIC_FIXTURE' ELSE 'VAN_HANH' END,\n"
     "                                          'trang_thai', 'HOLD', 'khoi_tao', v_kt, 'lech', '[]'::jsonb,\n"
     "                                          'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_BAN_SINH_CHI_DOCX')));\n"
     "            END IF;\n"))

_M36_HANG_DOI = _m36_thay(
    _m36_ham(CRM_G5_SQL, "crm_g5_hang_doi"),
    ("                IF v.loai = 'BAT_BUOC' THEN\n",
     "                -- M0036 (QD-27): bản sinh chỉ DOCX → không giao worker (không ý định/engine); giữ việc mở, lý do cần kiểm tay\n"
     "                IF " + _M36_CHI_DOCX.format(ky="v.ky_id") + " THEN\n"
     "                    IF v.trang_thai <> 'CHO_CAU_HINH' OR v.ly_do IS DISTINCT FROM 'G5_BAN_SINH_CHI_DOCX' THEN\n"
     "                        PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', 'HE_THONG', 'hang_doi', jsonb_build_object('ly_do', 'G5_BAN_SINH_CHI_DOCX'));\n"
     "                    END IF;\n"
     + _M36_VIEC_CHO.format(b=" " * 20) +
     "                    CONTINUE;\n"
     "                END IF;\n"
     "                IF v.loai = 'BAT_BUOC' THEN\n"))

_M36_NHAN = _m36_thay(
    _m36_ham(CRM_G5_SQL, "crm_g5_nhan"),
    ("                RETURN jsonb_build_object('nhan', false, 'ly_do', 'KHONG_DEN_HAN', 'trang_thai', v.trang_thai);\n            END IF;\n",
     "                RETURN jsonb_build_object('nhan', false, 'ly_do', 'KHONG_DEN_HAN', 'trang_thai', v.trang_thai);\n            END IF;\n"
     "            -- M0036 (QD-27): bản sinh chỉ DOCX → không nhận (không ý định/engine/lineage); giữ việc mở ở CHO_CAU_HINH, lý do cần kiểm tay\n"
     "            IF " + _M36_CHI_DOCX.format(ky="v.ky_id") + " THEN\n"
     "                IF v.trang_thai <> 'CHO_CAU_HINH' OR v.ly_do IS DISTINCT FROM 'G5_BAN_SINH_CHI_DOCX' THEN\n"
     "                    PERFORM master.crm_g5_ghi_su_kien(v.id, 'CHO_CAU_HINH', 'HE_THONG', coalesce(ai, 'khong_danh_tinh'),\n"
     "                                                      jsonb_build_object('ly_do', 'G5_BAN_SINH_CHI_DOCX'));\n"
     "                END IF;\n"
     + _M36_VIEC_CHO.format(b=" " * 16) +
     "                RETURN jsonb_build_object('nhan', false, 'ly_do', 'G5_BAN_SINH_CHI_DOCX', 'trang_thai', 'CHO_CAU_HINH');\n"
     "            END IF;\n"))

_M36_DOC = _m36_thay(
    _m36_ham(CRM_G5_SQL, "crm_g5_doc"),
    ("            IF k.co_sua AND nc.dang_nhap IS NULL THEN v_ly := v_ly || jsonb_build_array('THIEU_NGUOI_CHAY'); END IF;\n",
     "            IF k.co_sua AND nc.dang_nhap IS NULL THEN v_ly := v_ly || jsonb_build_array('THIEU_NGUOI_CHAY'); END IF;\n"
     "            IF " + _M36_CHI_DOCX.format(ky="k.id") + " THEN  -- M0036 (QD-27): bản sinh chỉ DOCX → cần kiểm tay, không chạy tự động\n"
     "                v_ly := v_ly || jsonb_build_array('G5_BAN_SINH_CHI_DOCX');\n"
     "                v_chay := false;\n"
     "            END IF;\n"))

_M36_CHAY = _m36_thay(
    _m36_ham(CRM_G5_SQL, "crm_g5_chay"),
    ("            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND loai = 'THU_CONG' AND trang_thai IN ",
     "            IF k.g3_pdf_sha256 IS NULL THEN  -- M0036 (QD-27): bản sinh chỉ DOCX → không tạo việc thủ công không chạy được\n"
     "                RAISE EXCEPTION 'CRM_G5_CAN_KIEM_TAY: bản ký gắn bản sinh chỉ có DOCX — chưa đối chiếu tự động được, cần kiểm tay' USING ERRCODE = 'P0001';\n"
     "            END IF;\n"
     "            SELECT * INTO v FROM master.crm_g5_viec WHERE ky_id = p_ky AND loai = 'THU_CONG' AND trang_thai IN "))

M0036_KY_DOCX = (
    # bản ký: PDF G3 tùy chọn (chỉ khi bản xuất có PDF); cặp sha/độ dài cùng có hoặc cùng NULL. Hàng cũ đều có PDF → CHECK hợp lệ ngay.
    "ALTER TABLE master.crm_hd_ky ALTER COLUMN g3_pdf_sha256 DROP NOT NULL, ALTER COLUMN g3_pdf_len DROP NOT NULL",
    "ALTER TABLE master.crm_hd_ky ADD CONSTRAINT crm_hd_ky_g3_pdf_cap CHECK ((g3_pdf_sha256 IS NULL) = (g3_pdf_len IS NULL))",
    _M36_XUAT_GHI,
    _M36_HD_KY_KIEM,
    _M36_KY_KET,
    _M36_KIEM_G5_XET,
    _M36_HANG_DOI,
    _M36_NHAN,
    _M36_DOC,
    _M36_CHAY,
)

PG_MIGRATIONS = (*PG_MIGRATIONS, M0036_KY_DOCX)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# M0037 — CD-010 mục 1: kế toán kiểm tay G5 cho bản sinh chỉ DOCX; E5 giữ nguyên.
from ..k2.sql_crm_g5_tay import CRM_G5_TAY_SQL, G5_TAY_XET, G6_KIEM_CASE_CAP  # noqa: E402


def _m37_ham(ten: str) -> str:
    """Lấy định nghĩa cuối trước M0037, gồm schema master hoặc kho."""
    for migration in reversed(PG_MIGRATIONS):
        ds = [s for s in migration if s.lstrip().startswith(f"CREATE OR REPLACE FUNCTION {ten}(")]
        if ds:
            if len(ds) != 1:
                raise RuntimeError(f"M0037: không định vị đúng một định nghĩa {ten}")
            return ds[0]
    raise RuntimeError(f"M0037: thiếu định nghĩa hiện hành {ten}")


_M37_KIEM_G5_XET = _m36_thay(
    _m37_ham("master.crm_kiem_g5_xet"),
    ("            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);\n",
     "            v_kt := jsonb_build_object('trang_thai', g.trang_thai, 'ly_do', g.ly_do, 'la_bang_chung', false);\n" + G5_TAY_XET))

# Lỗi thật tại dòng 32 của kho.crm_kiem_viec_kiem là IF NOT CASE bị cắt ở
# THEN đầu, không phải guard G5 tự động. Guard hồ sơ cũng dùng cùng cú pháp;
# sửa cả hai để lưu/Hiệu lực chạy được, không thêm ngoại lệ bỏ qua G5 hay G6.
_M37_KIEM_VIEC_KIEM = _m36_thay(_m37_ham("kho.crm_kiem_viec_kiem"), *G6_KIEM_CASE_CAP)
_M37_KIEM_HO_SO_KIEM = _m36_thay(_m37_ham("master.crm_kiem_ho_so_kiem"), *G6_KIEM_CASE_CAP)

M0037_CRM_G5_TAY = (*CRM_G5_TAY_SQL, _M37_KIEM_G5_XET, _M37_KIEM_VIEC_KIEM, _M37_KIEM_HO_SO_KIEM)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0037_CRM_G5_TAY)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# ---------------------------------------------------------------------------
# M4-DL1 — CD-011: chứng cứ nguồn Review SQLite; M0038 (lead đánh số khi gộp 26/10).
# Chỉ append, không đổi migration đã phát hành.
# Lát chưa gộp: vòng 2 sửa trực tiếp SQL sang lần chụp riêng, không thêm migration.
# ---------------------------------------------------------------------------
from ..m4.sql_review_chep import M4_REVIEW_CHEP_SQL  # noqa: E402 — chỉ hằng SQL

M0038_M4_REVIEW_CHEP = M4_REVIEW_CHEP_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0038_M4_REVIEW_CHEP)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-1 — M0039 (lead đánh số khi gộp 26/10). Chưa nối quyền cũ, mặc định tắt.
from ..k2.sql_ma_tran_tham_quyen import MA_TRAN_THAM_QUYEN_SQL  # noqa: E402 — chỉ hằng SQL

M0039_MA_TRAN_THAM_QUYEN = MA_TRAN_THAM_QUYEN_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0039_MA_TRAN_THAM_QUYEN)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# M4-DL1b — CD-011: M0040 (lead đánh số khi gộp 26/10); thời điểm chụp và bản hiện hành có tính HĐ đã xóa.
from ..m4.sql_review_chep import M4_REVIEW_CHEP_B_SQL  # noqa: E402 — chỉ hằng SQL

M0040_M4_REVIEW_CHEP_B = M4_REVIEW_CHEP_B_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0040_M4_REVIEW_CHEP_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4a0 — CD-012: M0041 (lead đánh số khi gộp 26/10); cổng SQL danh tính phiên.
from ..k2.sql_mtq_cong import MTQ_CONG_SQL  # noqa: E402 — chỉ hằng SQL

M0041_MTQ_CONG = MTQ_CONG_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0041_MTQ_CONG)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# M3-1a — CD-013: M0042 (lead đánh số khi gộp 26/10); cơ sở doanh thu/thuế và mapping M2.
from ..k2.sql_m3 import M3_CO_SO_SQL  # noqa: E402 — chỉ hằng SQL

M0042_M3_CO_SO = M3_CO_SO_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0042_M3_CO_SO)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4a0b — CD-012: M0043 (lead đánh số khi gộp 26/10); chống dùng lại request ID cho nhật ký từ chối khác.
from ..k2.sql_mtq_cong import MTQ_CONG_B_SQL  # noqa: E402 — chỉ hằng SQL

M0043_MTQ_CONG_B = MTQ_CONG_B_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0043_MTQ_CONG_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# M3-1c — CD-013: M0044 (lead đánh số khi gộp 26/10); một hóa đơn chỉ có một liên kết đã xác nhận; lead cấp ordinal khi gộp.
from ..k2.sql_m3 import M3_CO_SO_B_SQL  # noqa: E402 — chỉ hằng SQL

M0044_M3_CO_SO_B = M3_CO_SO_B_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0044_M3_CO_SO_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4a3a — CD-012: M0045 (lead đánh số khi gộp 26/10); resolver CRM/M1/file soát.
from ..k2.sql_mtq_cong import MTQ_CONG_C_SQL  # noqa: E402 — chỉ hằng SQL

M0045_MTQ_CONG_C = MTQ_CONG_C_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0045_MTQ_CONG_C)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# M3-1d — CD-013: tiền tố khóa advisory cho xác nhận hóa đơn; lead đánh số khi gộp.
from ..k2.sql_m3 import M3_CO_SO_C_SQL  # noqa: E402 — chỉ hằng SQL

M0046_M3_CO_SO_C = M3_CO_SO_C_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0046_M3_CO_SO_C)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4b1a — CD-012: M0047; resolver bảng riêng G1/G2/G3/G4/G7/dự án.
from ..k2.sql_mtq_cong import MTQ_CONG_D_SQL  # noqa: E402 — chỉ hằng SQL

M0047_MTQ_CONG_D = MTQ_CONG_D_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0047_MTQ_CONG_D)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4f1a — CD-012: resolver phạm vi M4; lead đánh số khi gộp.
from ..k2.sql_mtq_cong import MTQ_CONG_E_SQL  # noqa: E402 — chỉ hằng SQL

M0048_MTQ_CONG_E = MTQ_CONG_E_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0048_MTQ_CONG_E)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4i-a — CD-012: phạm vi NGUON; lead đánh số migration khi gộp.
from ..k2.sql_mtq_lien_module import MTQ_LMOD_A_SQL  # noqa: E402 — chỉ hằng SQL

M0049_MTQ_LMOD_A = MTQ_LMOD_A_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0049_MTQ_LMOD_A)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4b1b — CD-012: guard G1/G7; tên tạm, lead đánh số khi gộp.
from ..k2.sql_mtq_crm import MTQ_CRM_A_SQL  # noqa: E402 — chỉ hằng SQL

# Lấy định nghĩa hiện hành và thay đúng một vị trí; giữ toàn bộ CAS, graph,
# digest, hiệu lực, append-only và tách nhiệm G1 của các hàm lệnh đã phát hành.
M0050_MTQ_CRM_A = (
    *MTQ_CRM_A_SQL,
    _m36_thay(
        _m37_ham("master.crm_g_chuan_doc"),
        ("LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path"),
        ("IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN",
         "IF pn IS NULL OR NOT master.crm_g_chuan_xem(p_du_an, false) THEN")),
    _m36_thay(
        _m37_ham("master.crm_g_chuan_duyet"),
        ("IF v.gui_boi = ai THEN",
         "IF v.gui_boi = ai OR (v.lap_boi = ai AND EXISTS (SELECT 1 FROM master.mtq_kich_hoat "
         "WHERE phap_nhan_id = v.phap_nhan_id AND bat)) THEN")),
)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0050_MTQ_CRM_A)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-NEN-0 — CD-012: resolver chỉ đọc dùng chung; lead đánh số khi gộp.
from ..k2.sql_mtq_cong import MTQ_CONG_F_SQL  # noqa: E402 — chỉ hằng SQL

M0051_MTQ_CONG_F = MTQ_CONG_F_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0051_MTQ_CONG_F)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# XS-1a — CD-017: bus outbox/inbox; tên tạm, lead đánh số khi gộp.
from ..k2.sql_bus_su_kien import BUS_SU_KIEN_SQL  # noqa: E402 — chỉ hằng SQL

M0052_BUS_SU_KIEN = BUS_SU_KIEN_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0052_BUS_SU_KIEN)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4b2a — CD-012: guard G2/G3 (M0053).
from ..k2.sql_mtq_crm import MTQ_CRM_B_SQL  # noqa: E402 — chỉ hằng SQL

M0053_MTQ_CRM_B = (
    *MTQ_CRM_B_SQL,
    # Giữ thân lệnh hiện hành (gồm các sửa G4/BG1c/M0036), chỉ đổi nguồn
    # ghim quyền. Guard đích ở trên kiểm MTQ trước mọi replay/CAS/công bố.
    *(_m36_thay(
        _m37_ham(ten),
        ("PERFORM master.crm_g_ghim_quyen(", "PERFORM master.crm_gk_ghim_quyen("))
      for ten in (
          "master.crm_gk_tra", "master.crm_gk_dat_lan", "master.crm_gk_bao_gia_luu",
          "master.crm_gk_bao_gia_huy", "master.crm_gk_chuyen", "master.crm_gk_soan_luu",
          "master.crm_gk_xuat_ghi")),
    _m36_thay(
        _m37_ham("master.crm_gk_ghim_mau"),
        ("LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path"),
        ("            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_mau_pb;",
         "            PERFORM pg_advisory_xact_lock_shared(742601, 1);\n"
         "            SELECT * INTO v FROM master.crm_mau_phien_ban WHERE id = p_mau_pb;"),
        ("v.phap_nhan_id <> p_pn",
         "(CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = v.phap_nhan_id AND bat) "
         "THEN v.phap_nhan_id IS DISTINCT FROM p_pn ELSE v.phap_nhan_id <> p_pn END)"),
        ("v.loai_hinh_id <> p_loai",
         "(CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = v.phap_nhan_id AND bat) "
         "THEN v.loai_hinh_id IS DISTINCT FROM p_loai ELSE v.loai_hinh_id <> p_loai END)"),
        ("master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) IS NULL",
         "NOT (CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = v.phap_nhan_id AND bat) "
         "THEN master.crm_gk_xem('master.crm_mau_phien_ban', v.id, v.phap_nhan_id) "
         "ELSE master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) IS NOT NULL END)")),
    _m36_thay(
        _m37_ham("master.crm_gk_mau_ghim"),
        ("LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path"),
        ("            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan;",
         "            PERFORM pg_advisory_xact_lock_shared(742601, 1);\n"
         "            SELECT * INTO s FROM master.crm_hd_soan WHERE id = p_soan;"),
        ("NOT master.ktt_duoc(s.phap_nhan_id, 'CRM') OR NOT master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id)",
         "NOT (CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = s.phap_nhan_id AND bat) "
         "THEN master.crm_gk_xem('master.crm_hd_soan', s.id, s.phap_nhan_id) "
         "ELSE master.ktt_duoc(s.phap_nhan_id, 'CRM') AND master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id) END)")),
    _m36_thay(
        _m37_ham("master.crm_gk_mau_hieu_luc"),
        ("LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path"),
        ("            SELECT l.phap_nhan_id INTO pn FROM master.loai_hinh_doanh_thu l WHERE l.id = p_loai;",
         "            PERFORM pg_advisory_xact_lock_shared(742601, 1);\n"
         "            SELECT l.phap_nhan_id INTO pn FROM master.loai_hinh_doanh_thu l WHERE l.id = p_loai;"),
        ("pn IS NULL OR NOT master.crm_gk_duoc('CRM_SOAN', pn)",
         "pn IS NULL OR (NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) "
         "AND NOT master.crm_gk_duoc('CRM_SOAN', pn))"),
        ("WHERE v.loai_hinh_id = p_loai AND v.phap_nhan_id = pn AND v.trang_thai = 'HIEU_LUC'",
         "WHERE v.loai_hinh_id = p_loai AND v.phap_nhan_id = pn AND v.trang_thai = 'HIEU_LUC' "
         "AND CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = pn AND bat) "
         "THEN master.crm_gk_xem('master.crm_mau_phien_ban', v.id, pn) ELSE true END")),
    _m36_thay(
        _m37_ham("master.crm_gk_tep"),
        ("LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path"),
        ("            SELECT * INTO x FROM master.crm_gk_xuat WHERE id = p_xuat;",
         "            PERFORM pg_advisory_xact_lock_shared(742601, 1);\n"
         "            SELECT * INTO x FROM master.crm_gk_xuat WHERE id = p_xuat;"),
        ("NOT master.crm_gk_duoc(CASE WHEN x.loai = 'BAO_GIA' THEN 'CRM_BAO_GIA' ELSE 'CRM_SOAN' END, x.phap_nhan_id)",
         "NOT (CASE WHEN EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id = x.phap_nhan_id AND bat) "
         "THEN master.crm_gk_xem('master.crm_gk_xuat', x.id, x.phap_nhan_id) "
         "ELSE master.crm_gk_duoc(CASE WHEN x.loai = 'BAO_GIA' THEN 'CRM_BAO_GIA' ELSE 'CRM_SOAN' END, x.phap_nhan_id) END)")),
)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0053_MTQ_CRM_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)


# MTQ-NEN-1 — CD-012: quyết định chỉ đọc; M0054.
from ..k2.sql_mtq_nen import MTQ_NEN_A_SQL  # noqa: E402 — chỉ hằng SQL

M0054_MTQ_NEN_A = MTQ_NEN_A_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0054_MTQ_NEN_A)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-4f1b — CD-012: guard từng lệnh hồ sơ M17; M0055.
from ..m4.sql_mtq import MTQ_M4_A_SQL  # noqa: E402 — chỉ hằng SQL
from ..m4.sql_m17 import _SOAN as _M4_A_SOAN  # noqa: E402 — guard CU nguyên bản


def _mtq_m4_a_soan(ten: str, hanh: str, du_an: str, obj: str) -> str:
    """Giữ toàn thân hiện hành; chỉ thay nguồn quyền ở đúng guard SOAN."""
    cu = _M4_A_SOAN.format(d=du_an)
    moi = (f"\n            IF NOT m4._mtq_ho_so_quyen('{hanh}', {obj}) THEN"
           + cu + "\n            END IF;")
    return _m36_thay(_m37_ham("m4." + ten), (cu, moi))


M0055_MTQ_M4_A = (
    *MTQ_M4_A_SQL,
    # Căn cứ nội bộ của lệnh đã có guard: không dùng XEM/vai cũ phủ quyết
    # KIEM/SUA. API đọc công khai và RLS để nguyên cho lát MTQ-4f1c.
    _m36_thay(
        _m37_ham("m4.digest_tham_so"),
        ("CREATE OR REPLACE FUNCTION m4.digest_tham_so(p_hd uuid)",
         "CREATE FUNCTION m4._mtq_ho_so_digest(p_hd uuid)"),
        ("LANGUAGE sql STABLE SECURITY DEFINER", "LANGUAGE sql STABLE"),
        ("\n          AND EXISTS (SELECT 1 FROM m4.ho_so_hop_dong h WHERE h.hop_dong_id = p_hd\n"
         "                      AND (master.m4_duoc(h.du_an_id, 'XEM') OR master.m4_duoc(h.du_an_id, 'REVIEW')))", "")),
    "REVOKE ALL ON FUNCTION m4._mtq_ho_so_digest(uuid) FROM PUBLIC",
    _m36_thay(
        _m37_ham("m4.thieu"),
        ("CREATE OR REPLACE FUNCTION m4.thieu(p_dot uuid)",
         "CREATE FUNCTION m4._mtq_ho_so_thieu(p_dot uuid)"),
        ("LANGUAGE plpgsql STABLE SECURITY DEFINER", "LANGUAGE plpgsql STABLE"),
        ("IF NOT FOUND OR NOT (master.m4_duoc(d.du_an_id, 'XEM') OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')) THEN",
         "IF NOT FOUND THEN"),
        ("m4.digest_tham_so(h.hop_dong_id)", "m4._mtq_ho_so_digest(h.hop_dong_id)")),
    "REVOKE ALL ON FUNCTION m4._mtq_ho_so_thieu(uuid) FROM PUBLIC",
    _m36_thay(
        _m37_ham("m4._khoa_dot"),
        ("CREATE OR REPLACE FUNCTION m4._khoa_dot(p_dot uuid)",
         "CREATE FUNCTION m4._mtq_ho_so_khoa_dot(p_dot uuid, p_hanh_dong text)"),
        (_M4_A_SOAN.format(d="d.du_an_id"),
         "\n            IF NOT m4._mtq_ho_so_quyen(p_hanh_dong, p_dot) THEN"
         + _M4_A_SOAN.format(d="d.du_an_id") + "\n            END IF;")),
    "REVOKE ALL ON FUNCTION m4._mtq_ho_so_khoa_dot(uuid, text) FROM PUBLIC",
    *(_mtq_m4_a_soan(ten, hanh, da, obj) for ten, hanh, da, obj in (
        ("tao_hop_dong", "TAO_HOP_DONG", "p_du_an", "p_du_an"),
        ("ghi_tep", "TAI_TEP", "p_du_an", "p_du_an"),
        ("gan_tep_hop_dong", "GAN_TEP_HOP_DONG", "h.du_an_id", "p_hd"),
        ("ghi_trich_xuat", "TRICH", "h.du_an_id", "p_hd"),
        ("sua_tham_so", "SUA_THAM_SO", "h.du_an_id", "p_hd"),
        ("khai_phu_luc", "KHAI_PHU_LUC", "h.du_an_id", "p_hd"),
        ("them_phu_luc", "THEM_PHU_LUC", "h.du_an_id", "p_hd"),
        ("huy_phu_luc", "HUY_PHU_LUC", "h.du_an_id", "p_pl"),
        ("ghi_boq", "NHAP_BOQ", "h.du_an_id", "p_hd"),
        ("tao_dot", "TAO_DOT", "h.du_an_id", "p_hd"))),
    _m36_thay(
        _mtq_m4_a_soan("xac_nhan_tham_so", "XAC_NHAN_THAM_SO", "h.du_an_id", "p_hd"),
        ("m4.digest_tham_so(h.hop_dong_id)",
         "CASE WHEN m4._mtq_ho_so_quyen('XAC_NHAN_THAM_SO', p_hd) "
         "THEN m4._mtq_ho_so_digest(h.hop_dong_id) ELSE m4.digest_tham_so(h.hop_dong_id) END")),
    *(_m36_thay(
        _m37_ham("m4." + ten),
        ("d := m4._khoa_dot(p_dot);", f"d := m4._mtq_ho_so_khoa_dot(p_dot, '{hanh}');"))
      for ten, hanh in (("sua_dot", "SUA_DOT"), ("gan_tep_dot", "GAN_TEP_DOT"))),
    _m36_thay(
        _m37_ham("m4.nop"),
        ("d := m4._khoa_dot(p_dot);", "d := m4._mtq_ho_so_khoa_dot(p_dot, 'NOP');"),
        ("con := m4.thieu(p_dot);",
         "con := CASE WHEN m4._mtq_ho_so_quyen('NOP', p_dot) "
         "THEN m4._mtq_ho_so_thieu(p_dot) ELSE m4.thieu(p_dot) END;")),
    _m36_thay(
        _m37_ham("m4.tra_bien_nhan"),
        ("LANGUAGE plpgsql STABLE SECURITY DEFINER", "LANGUAGE plpgsql SECURITY DEFINER"),
        (_M4_A_SOAN.format(d="b.du_an_id"),
         "\n            IF NOT m4._mtq_ho_so_replay(b.hanh_dong, b.yeu_cau, b.du_an_id) THEN"
         + _M4_A_SOAN.format(d="b.du_an_id") + "\n            END IF;")),
)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0055_MTQ_M4_A)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)


# XS-4b — CD-017: công tắc module × pháp nhân, S1–S5; M0056.
from ..k2.sql_module import MODULE_CONG_TAC_SQL  # noqa: E402 — chỉ hằng SQL

M0056_MODULE_CONG_TAC = MODULE_CONG_TAC_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0056_MODULE_CONG_TAC)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# MTQ-NEN-2a — CD-012: cổng phiên dùng tập PN; lead đánh số khi gộp.
from ..k2.sql_mtq_cong import MTQ_CONG_G_SQL  # noqa: E402 — chỉ hằng SQL

M0057_MTQ_CONG_G = MTQ_CONG_G_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0057_MTQ_CONG_G)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)


# MTQ-NEN-2b — CD-012: quyết định chỉ đọc dùng tập PN; lead đánh số khi gộp.
from ..k2.sql_mtq_nen import MTQ_NEN_B_SQL  # noqa: E402 — chỉ hằng SQL

M0058_MTQ_NEN_B = MTQ_NEN_B_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0058_MTQ_NEN_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# BO-1a — QD-09: M0059; bỏ dòng và đọc BOQ hiệu lực, giữ writer M0055.
from ..m4.sql_boq_bo import M4_BOQ_BO_SQL  # noqa: E402 — chỉ hằng SQL

M0059_M4_BOQ_BO = M4_BOQ_BO_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0059_M4_BOQ_BO)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# XS-2a — CD-017: hàng việc nền dùng chung; lead đánh số khi gộp.
from ..k2.sql_hang_viec import HANG_VIEC_SQL  # noqa: E402 — chỉ hằng SQL

M0060_HANG_VIEC = HANG_VIEC_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0060_HANG_VIEC)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)


# MTQ-4f1c — CD-012: đọc/master M4 và B6; lead đánh số khi gộp.
from ..m4.sql_mtq import MTQ_M4_B_SQL  # noqa: E402 — chỉ hằng SQL
from ..m4.sql_master_dung_chung import _SOAN as _M4_B_SOAN  # noqa: E402


def _mtq_m4_b_xem(bang: str, obj: str, cu: str, hanh: str = 'XEM') -> str:
    return f"coalesce(m4.mtq_ho_so_doc('{bang}', {obj}, '{hanh}'), ({cu}))"


_M4_B_H_XR = "master.m4_duoc(h.du_an_id, 'XEM') OR master.m4_duoc(h.du_an_id, 'REVIEW')"
_M4_B_P_XR = "master.m4_duoc(p_du_an, 'XEM') OR master.m4_duoc(p_du_an, 'REVIEW')"
_M4_B_D_XR = "master.m4_duoc(d.du_an_id, 'XEM') OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')"


def _mtq_m4_b_bo_chon(ten: str) -> str:
    cu = _M4_B_SOAN.format(d='p_du_an')
    return _m36_thay(
        _m37_ham('m4.' + ten),
        (cu, "\n            IF m4.mtq_ho_so_doc('master.du_an', p_du_an, 'LAP') IS NULL THEN"
         + cu + "\n            ELSIF NOT m4.mau_duoc(p_du_an) THEN"
         "\n                RAISE EXCEPTION 'M4_KHONG_CO_QUYEN_DU_AN: Anh/chị cần chọn dự án và được giao quyền lập hồ sơ tại dự án đó.' USING ERRCODE = 'P0001';"
         "\n            END IF;"))


M0061_MTQ_M4_B = (
    *MTQ_M4_B_SQL,
    _m36_thay(_m37_ham('m4.digest_tham_so'),
        (_M4_B_H_XR, _mtq_m4_b_xem('master.hop_dong', 'h.hop_dong_id', _M4_B_H_XR))),
    _m36_thay(_m37_ham('m4.tep_da_nop'),
        ("master.m4_duoc(f.du_an_id, 'XEM') OR master.m4_duoc(f.du_an_id, 'REVIEW')",
         _mtq_m4_b_xem('m4.tep', 'f.id', "master.m4_duoc(f.du_an_id, 'XEM') OR master.m4_duoc(f.du_an_id, 'REVIEW')"))),
    _m36_thay(_m37_ham('m4.thieu'),
        (_M4_B_D_XR, _mtq_m4_b_xem('m4.dot', 'd.id', _M4_B_D_XR))),
    _m36_thay(_m37_ham('m4.mc_co_ho_so'),
        (_M4_B_P_XR, _mtq_m4_b_xem('master.hop_dong', 'p_hd', _M4_B_P_XR))),
    _m36_thay(_mtq_m4_b_bo_chon('master_hop_dong_ds'),
        ("WHERE h.phap_nhan_id = d.phap_nhan_id AND h.du_an_id = p_du_an AND h.loai = 'XAY_DUNG'",
         "WHERE h.phap_nhan_id = d.phap_nhan_id AND h.du_an_id = p_du_an AND h.loai = 'XAY_DUNG'"
         "\n                   AND coalesce(m4.mtq_ho_so_doc('master.hop_dong', h.id, 'LAP'), true)")),
    _mtq_m4_b_bo_chon('master_doi_tac_ds'),
    _m36_thay(_m37_ham('m4.master_can_cu_doc'),
        (_M4_B_H_XR, _mtq_m4_b_xem('master.hop_dong', 'h.hop_dong_id', _M4_B_H_XR)),
        ("master.m4_duoc(h.du_an_id, 'SOAN')",
         _mtq_m4_b_xem('master.hop_dong', 'h.hop_dong_id', "master.m4_duoc(h.du_an_id, 'SOAN')", 'SUA'))),
    # INVOKER và ACL nguồn/cờ sửa M38/M40 giữ nguyên: không mở nguồn cho app.
    _m36_thay(next(s for s in M0040_M4_REVIEW_CHEP_B if s.startswith('CREATE FUNCTION m4.review_chep_hien_hanh(')),
        ('CREATE FUNCTION m4.review_chep_hien_hanh(', 'CREATE OR REPLACE FUNCTION m4.review_chep_hien_hanh('),
        ('WHERE EXISTS (', "WHERE m4.mtq_ho_so_doc('master.hop_dong', p_hop_dong_id, 'XEM') IS DISTINCT FROM false\n        AND EXISTS (")),
)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0061_MTQ_M4_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# XS-2a2 — CD-017: đọc trạng thái lease/yêu cầu dừng cho worker; không đổi M0060.
from ..k2.sql_hang_viec import HANG_VIEC_B_SQL  # noqa: E402 — chỉ hằng SQL

M0062_HANG_VIEC_B = HANG_VIEC_B_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0062_HANG_VIEC_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# BO-1b — QD-09: thao tác BOQ tường minh; giữ thân writer hiện hành M0055.
from ..m4.sql_boq_bo import M4_BOQ_BO_B_SQL  # noqa: E402 — chỉ các cặp SQL

M0063_M4_BOQ_BO_B = (_m36_thay(_m37_ham("m4.ghi_boq"), *M4_BOQ_BO_B_SQL),)
PG_MIGRATIONS = (*PG_MIGRATIONS, M0063_M4_BOQ_BO_B)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)

# XS-T1a — CD-017: hợp đồng đầu hóa đơn chỉ đọc; lead đánh số khi gộp.
from ..k2.sql_cong_bo_hoa_don import CONG_BO_HOA_DON_SQL  # noqa: E402 — chỉ hằng SQL

M0064_CONG_BO_HOA_DON = CONG_BO_HOA_DON_SQL
PG_MIGRATIONS = (*PG_MIGRATIONS, M0064_CONG_BO_HOA_DON)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)
