"""M4-02C — M24 (append sau actual 1–23): duyệt hồ sơ đợt / PDF hồ sơ đã duyệt / seal / KT chờ xác nhận. CHỈ hằng SQL (không import ha_tang;
pg_migrations.py import và append registry). Không DROP bảng/hàm cũ, không đổi định nghĩa/checksum 1–23 (chỉ nới CHECK vai của m4.quyen_du_an).

- Phiên bản hồ sơ (m4.duyet_phien_ban): bản 1 = đúng lần nộp M17 (m4.nop, UNIQUE(dot) giữ nguyên — trigger AFTER INSERT + backfill); bản kế tiếp
  là NHÁP rõ ràng của CÙNG đợt (parent tuyến tính, UNIQUE(parent_id)), nộp/kiểm lại bằng lệnh riêng (snapshot cùng mẫu m4.nop). Không mở khóa đợt
  DA_NOP, không sửa snapshot/so_dot, không master mới.
- Quyền DUYET riêng: thêm vai 'DUYET' vào m4.quyen_du_an + master.m4_duyet_duoc (cùng kiểm danh tính/PN/module/thu hồi như master.m4_duoc —
  m4_duoc KHÔNG đổi; REVIEW/SOAN không ngụ ý DUYET). Không cấp vai này cho ai trong migration.
- Kết luận (m4.duyet_ket_luan + _dong): revision theo phiên bản, đồ thị nguồn/review (L3 đã công bố + L2 tham chiếu) + SHA, tiền NT/TT/tạm ứng/thu
  hồi/giữ lại là chuỗi thập phân chuẩn hoặc NULL (thiếu ≠ 0), lượng chấp nhận theo dòng tách khỏi đề xuất nguồn, xử lý phát hiện có lý do.
- Chấp thuận (m4.duyet_quyet_dinh): một quyết định/phiên bản, gắn ĐÚNG kết luận + SHA đồ thị; KHÔNG phải review đã công bố/DA_NOP.
- PDF (m4.duyet_pdf): bytes do máy chủ nhận/kiểm/lưu m4-raw/<sha>; ứng viên gắn phiên bản + ĐÚNG kết luận (revision) + SHA đồ thị của kết luận
  (FK tổ hợp); vai 'HO_SO_DOT_DA_DUYET' (không phải PDF HĐ/báo cáo). Seal chỉ dùng ứng viên gắn đúng kết luận được chấp thuận.
- Vật liệu: kết luận/chấp thuận/PDF/seal yêu cầu revision hồ sơ HĐ hiện hành = revision lúc nộp phiên bản (đổi HĐ/PL/BOQ/tham số sau nộp →
  M4_DUYET_CAN_PHIEN_BAN_MOI, cần phiên bản kế tiếp + nộp/kiểm lại; bản cũ bất biến).
- Seal: MỘT hàm nội bộ m4._duyet_seal dùng chung cho cả hai thứ tự (duyệt→PDF, PDF→duyệt): seal bất biến + MỘT gốc KT chờ theo đợt + MỘT phong bì
  bất biến mỗi seal (đính chính = phong bì con trên cùng gốc). Thiếu PDF → không seal, không KT chờ. Không AP, không Request.
- Lệnh = hàm SECURITY INVOKER chỉ chạy trên kết nối CHỦ BẢNG của máy chủ (master.la_chu_bang), EXECUTE thu hồi khỏi PUBLIC; quyền HIỆN HÀNH kiểm
  trong hàm TRƯỚC biên nhận; thứ tự khóa HĐ → đợt → phiên bản → biên nhận. Bảng: chỉ chủ bảng ghi, chỉ ghi thêm (trừ chuyển NHAP→DA_NOP một lần
  của phiên bản), RLS + GRANT SELECT kỹ thuật cho app_web hiện hữu.
"""

from __future__ import annotations

_LOI = "USING ERRCODE = 'P0001'"
_HEX = "~ '^[0-9a-f]{64}$'"
# thập phân chuẩn KHÔNG âm (không số 0 thừa, không mũ): tiền ≤ 2 chữ số lẻ, khối lượng ≤ 6 chữ số lẻ
_TIEN = r"~ '^(0|[1-9][0-9]{0,17})(\.[0-9]?[1-9])?$'"
_KL = r"~ '^(0|[1-9][0-9]{0,17})(\.[0-9]{0,5}[1-9])?$'"
TIEN = ("gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai")
HANH_DONG = ("DUYET_KET_LUAN", "DUYET_CHAP_THUAN", "DUYET_PDF", "DUYET_PHIEN_BAN", "DUYET_PHIEN_BAN_NOP")
QUYEN_LENH = ("XEM", "KET_LUAN", "CHAP_THUAN", "PDF", "PHIEN_BAN", "PHIEN_BAN_NOP")
VAI_PDF = "HO_SO_DOT_DA_DUYET"
_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.duyet_phien_ban'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường tin cậy của máy chủ ghi duyệt hồ sơ đợt' """ + _LOI + """;
            END IF;"""
_KB = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); cu jsonb; kq jsonb; rid uuid;"
# phiên bản phải là bản MỚI NHẤT (không có con) của đợt và đã nộp — bản cũ/bị thay chỉ còn là lịch sử
_PB_HIEN_HANH = """
            IF v.trang_thai <> 'DA_NOP' THEN
                RAISE EXCEPTION 'M4_DUYET_PHIEN_BAN_NHAP: phiên bản đang là nháp — nộp/kiểm lại phiên bản trước' """ + _LOI + """;
            END IF;
            IF EXISTS (SELECT 1 FROM m4.duyet_phien_ban z WHERE z.parent_id = v.id) THEN
                RAISE EXCEPTION 'M4_DUYET_PHIEN_BAN_CU: phiên bản đã có bản kế tiếp — thao tác trên phiên bản mới nhất' """ + _LOI + """;
            END IF;"""
_CAS = """
            IF p_expected IS NULL OR p_expected IS DISTINCT FROM p_graph_hien_tai THEN
                RAISE EXCEPTION 'M4_DUYET_CO_SO_DOI: căn cứ/review của hồ sơ đã đổi so với lúc xem — tải lại rồi thao tác' """ + _LOI + """;
            END IF;"""
# vật liệu hồ sơ (HĐ/tham số/PL/BOQ — mọi lệnh đổi đều tăng m4.ho_so_hop_dong.revision; tệp đợt khóa sau DA_NOP) phải còn ĐÚNG như lúc nộp phiên bản.
# Đổi sau nộp → phiên bản cũ chỉ còn lịch sử; muốn kết luận/duyệt/PDF phải tạo phiên bản kế tiếp rồi nộp/kiểm lại (một L3 mới trên căn cứ mới KHÔNG đủ).
_VAT_LIEU = """
            IF v.revision_ho_so IS DISTINCT FROM (SELECT hh.revision FROM m4.ho_so_hop_dong hh WHERE hh.hop_dong_id = v.hop_dong_id) THEN
                RAISE EXCEPTION 'M4_DUYET_CAN_PHIEN_BAN_MOI: hồ sơ HĐ/tham số/PL/BOQ đã đổi sau khi nộp phiên bản này — tạo phiên bản kế tiếp rồi nộp/kiểm lại' """ + _LOI + """;
            END IF;"""
_LAP_LAI = """
            IF cu IS NOT NULL THEN
                SELECT b.id INTO rid FROM m4.bien_nhan b WHERE b.nguoi_dung_id = aid AND b.khoa = p_khoa;
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu, 'receipt_id', rid);
            END IF;"""
_KET = """
            PERFORM m4._bn_ghi(aid, p_khoa, '{a}', v.du_an_id, p_yc, kq);
            SELECT b.id INTO rid FROM m4.bien_nhan b WHERE b.nguoi_dung_id = aid AND b.khoa = p_khoa;
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq, 'receipt_id', rid);"""
# ngữ cảnh GỐC của yêu cầu (phiên bản/revision/căn cứ mà người dùng đã gửi) — echo trong ACK và cả khi phát lại
_NGU_CANH = ("jsonb_build_object('dot_id', v.dot_id, 'hop_dong_id', v.hop_dong_id, 'du_an_id', v.du_an_id, 'phap_nhan_id', v.phap_nhan_id, "
             "'version_id', v.id, 'revision', p_revision, 'basis_sha256', p_expected)")


def _sql_tuple(xs) -> str:
    return "(" + ",".join(f"'{x}'" for x in xs) + ")"


def _tien_check(cot: str) -> str:
    return f"CHECK ({cot} IS NULL OR {cot} {_TIEN})"


_TIEN_COT = ",\n        ".join(f"{t} text {_tien_check(t)}" for t in TIEN)
_VND = " AND ".join(f"({t} IS NULL OR strpos({t}, '.') = 0)" for t in TIEN)
_TIEN_DU = " AND ".join(f"k.{t} IS NOT NULL" for t in TIEN)

HAM_LENH = ("m4.duyet_khoa(uuid, uuid, text)",
            "m4.duyet_tra(text, text, uuid, jsonb)",
            "m4.duyet_ghi_ket_luan(text, jsonb, uuid, uuid, integer, text, text, jsonb, jsonb, text)",
            "m4.duyet_chap_thuan(text, jsonb, uuid, uuid, integer, text, text, uuid, text)",
            "m4.duyet_ghi_pdf(text, jsonb, uuid, uuid, integer, text, text, text, bigint, text)",
            "m4.duyet_tao_phien_ban(text, jsonb, uuid, uuid, integer, text, text, text)",
            "m4.duyet_nop_phien_ban(text, jsonb, uuid, uuid, integer, text, text, jsonb)",
            "m4._duyet_seal(uuid, text, uuid)")
HAM_DOC = ("master.m4_duyet_duoc(uuid)", "m4.duyet_doc_dot(uuid)", "m4.duyet_quyen(uuid)", "m4.duyet_kiem(uuid, text)")
BANG = ("duyet_phien_ban", "duyet_ket_luan", "duyet_ket_luan_dong", "duyet_quyet_dinh", "duyet_pdf", "duyet_seal", "duyet_kt_cho", "duyet_kt_phong_bi")
BANG_GHI_THEM = BANG[1:]

M0024_M4_DUYET = (
    "SET LOCAL check_function_bodies = off",
    # --- quyền DUYET riêng (không đổi m4_duoc; tên ràng buộc tìm theo định nghĩa để không phụ thuộc tên tự sinh)
    """DO $$
    DECLARE r record;
    BEGIN
        FOR r IN SELECT c.conname FROM pg_catalog.pg_constraint c WHERE c.conrelid = 'm4.quyen_du_an'::regclass AND c.contype = 'c'
                   AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%vai%' AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%REVIEW%' LOOP
            EXECUTE format('ALTER TABLE m4.quyen_du_an DROP CONSTRAINT %I', r.conname);
        END LOOP;
    END $$""",
    "ALTER TABLE m4.quyen_du_an ADD CONSTRAINT quyen_du_an_vai_check CHECK (vai IN ('PHU_TRACH','XEM','REVIEW','DUYET'))",
    """CREATE OR REPLACE FUNCTION master.m4_duyet_duoc(p_du_an uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND q.du_an_id = p_du_an AND q.thu_hoi_luc IS NULL AND master.ktt_duoc(q.phap_nhan_id, 'M4')
                         AND q.vai = 'DUYET')
        $$""",
    # --- phiên bản hồ sơ đợt: bản 1 = lần nộp M17; bản sau = nháp → nộp/kiểm lại (một lần). Không xóa, không đổi định danh.
    f"""CREATE TABLE m4.duyet_phien_ban (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL REFERENCES m4.dot(id),
        so integer NOT NULL CHECK (so BETWEEN 1 AND 999),
        parent_id uuid,
        nop_id uuid UNIQUE REFERENCES m4.nop(id),
        trang_thai text NOT NULL CHECK (trang_thai IN ('NHAP','DA_NOP')),
        ly_do text CHECK (ly_do IS NULL OR length(btrim(ly_do)) BETWEEN 1 AND 1000),
        revision_ho_so integer CHECK (revision_ho_so IS NULL OR revision_ho_so >= 1),
        snapshot jsonb CHECK (snapshot IS NULL OR jsonb_typeof(snapshot) = 'object'),
        digest text CHECK (digest IS NULL OR digest {_HEX}),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        nop_boi text,
        nop_boi_id uuid REFERENCES master.nguoi_dung(id),
        nop_luc timestamptz,
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        CHECK ((so = 1) = (parent_id IS NULL)),
        CHECK ((so = 1) = (nop_id IS NOT NULL)),
        CHECK (so > 1 OR trang_thai = 'DA_NOP'),
        CHECK (so = 1 OR ly_do IS NOT NULL),
        CHECK ((trang_thai = 'DA_NOP') = (snapshot IS NOT NULL AND digest IS NOT NULL AND revision_ho_so IS NOT NULL AND nop_boi IS NOT NULL
                                          AND nop_boi_id IS NOT NULL AND nop_luc IS NOT NULL)),
        UNIQUE (dot_id, so),
        UNIQUE (parent_id),
        UNIQUE (id, dot_id),
        UNIQUE (id, du_an_id))""",
    "ALTER TABLE m4.duyet_phien_ban ADD CONSTRAINT duyet_phien_ban_parent_fk FOREIGN KEY (parent_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id)",
    "CREATE UNIQUE INDEX duyet_phien_ban_mot_nhap_uq ON m4.duyet_phien_ban (dot_id) WHERE trang_thai = 'NHAP'",
    """CREATE OR REPLACE FUNCTION m4.duyet_phien_ban_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: phiên bản hồ sơ đợt chỉ ghi qua hàm định nghĩa trên kết nối chủ bảng' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: không xóa phiên bản hồ sơ đợt (giữ lịch sử)' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF (NEW.so = 1 AND NEW.trang_thai <> 'DA_NOP') OR (NEW.so > 1 AND NEW.trang_thai <> 'NHAP') THEN
                    RAISE EXCEPTION 'M4_BAT_BIEN: bản 1 sinh từ lần nộp; bản sau phải bắt đầu là nháp' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.trang_thai <> 'NHAP' OR NEW.trang_thai <> 'DA_NOP'
               OR ROW(NEW.id, NEW.phap_nhan_id, NEW.du_an_id, NEW.hop_dong_id, NEW.dot_id, NEW.so, NEW.parent_id, NEW.nop_id, NEW.ly_do, NEW.tao_boi,
                      NEW.tao_boi_id, NEW.tao_luc)
                  IS DISTINCT FROM ROW(OLD.id, OLD.phap_nhan_id, OLD.du_an_id, OLD.hop_dong_id, OLD.dot_id, OLD.so, OLD.parent_id, OLD.nop_id, OLD.ly_do,
                      OLD.tao_boi, OLD.tao_boi_id, OLD.tao_luc) THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: phiên bản đã nộp bất biến; nháp chỉ chuyển một lần sang đã nộp' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER duyet_phien_ban_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.duyet_phien_ban FOR EACH ROW EXECUTE FUNCTION m4.duyet_phien_ban_kiem()",
    # lần nộp M17 (m4.nop chỉ ghi thêm, UNIQUE(dot)) → phiên bản 1 trong CÙNG giao dịch; không đổi hàm m4.nop
    """CREATE OR REPLACE FUNCTION m4.duyet_phien_ban_tu_nop() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            INSERT INTO m4.duyet_phien_ban (phap_nhan_id, du_an_id, hop_dong_id, dot_id, so, parent_id, nop_id, trang_thai, revision_ho_so, snapshot, digest,
                                            tao_boi, tao_boi_id, tao_luc, nop_boi, nop_boi_id, nop_luc)
                SELECT a.phap_nhan_id, NEW.du_an_id, NEW.hop_dong_id, NEW.dot_id, 1, NULL, NEW.id, 'DA_NOP', NEW.revision_ho_so, NEW.snapshot, NEW.digest,
                       NEW.nop_boi, NEW.nop_boi_id, NEW.nop_luc, NEW.nop_boi, NEW.nop_boi_id, NEW.nop_luc
                FROM master.du_an a WHERE a.id = NEW.du_an_id;
            RETURN NULL;
        END $$""",
    "CREATE TRIGGER nop_duyet_phien_ban AFTER INSERT ON m4.nop FOR EACH ROW EXECUTE FUNCTION m4.duyet_phien_ban_tu_nop()",
    """INSERT INTO m4.duyet_phien_ban (phap_nhan_id, du_an_id, hop_dong_id, dot_id, so, parent_id, nop_id, trang_thai, revision_ho_so, snapshot, digest,
                                      tao_boi, tao_boi_id, tao_luc, nop_boi, nop_boi_id, nop_luc)
        SELECT a.phap_nhan_id, n.du_an_id, n.hop_dong_id, n.dot_id, 1, NULL, n.id, 'DA_NOP', n.revision_ho_so, n.snapshot, n.digest,
               n.nop_boi, n.nop_boi_id, n.nop_luc, n.nop_boi, n.nop_boi_id, n.nop_luc
        FROM m4.nop n JOIN master.du_an a ON a.id = n.du_an_id
        WHERE NOT EXISTS (SELECT 1 FROM m4.duyet_phien_ban z WHERE z.nop_id = n.id)""",
    # --- kết luận reviewer/duyệt viên (revision theo phiên bản; chỉ ghi thêm)
    f"""CREATE TABLE m4.duyet_ket_luan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        graph jsonb NOT NULL CHECK (jsonb_typeof(graph) = 'object'),
        graph_sha256 text NOT NULL CHECK (graph_sha256 {_HEX}),
        l3_run_id uuid NOT NULL,
        l2_run_id uuid,
        tien_te text CHECK (tien_te IS NULL OR tien_te ~ '^[A-Z]{{3}}$'),
        {_TIEN_COT},
        xu_ly_phat_hien jsonb NOT NULL CHECK (jsonb_typeof(xu_ly_phat_hien) = 'array'),
        de_xuat_nguon jsonb NOT NULL CHECK (jsonb_typeof(de_xuat_nguon) = 'object'),
        thieu jsonb NOT NULL CHECK (jsonb_typeof(thieu) = 'array'),
        canh_bao jsonb NOT NULL CHECK (jsonb_typeof(canh_bao) = 'array'),
        ly_do text CHECK (ly_do IS NULL OR length(ly_do) <= 2000),
        quyen text NOT NULL CHECK (quyen IN ('REVIEW','DUYET')),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        FOREIGN KEY (phien_ban_id, du_an_id) REFERENCES m4.duyet_phien_ban (id, du_an_id),
        FOREIGN KEY (l3_run_id, du_an_id) REFERENCES m4.chung_tu_run (id, du_an_id),
        FOREIGN KEY (l2_run_id, du_an_id) REFERENCES m4.review_run (id, du_an_id),
        CHECK (tien_te IS DISTINCT FROM 'VND' OR ({_VND})),
        UNIQUE (phien_ban_id, revision),
        UNIQUE (id, phien_ban_id),
        UNIQUE (id, du_an_id),
        UNIQUE (id, graph_sha256))""",
    f"""CREATE TABLE m4.duyet_ket_luan_dong (
        ket_luan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        row_id text NOT NULL CHECK (length(row_id) BETWEEN 1 AND 600),
        ma_hm text CHECK (ma_hm IS NULL OR length(ma_hm) <= 500),
        ten text CHECK (ten IS NULL OR length(ten) <= 1000),
        dvt text CHECK (dvt IS NULL OR length(dvt) <= 100),
        de_xuat jsonb NOT NULL CHECK (jsonb_typeof(de_xuat) = 'object'),
        khoi_luong_chap_nhan text CHECK (khoi_luong_chap_nhan IS NULL OR khoi_luong_chap_nhan {_KL}),
        PRIMARY KEY (ket_luan_id, row_id),
        FOREIGN KEY (ket_luan_id, du_an_id) REFERENCES m4.duyet_ket_luan (id, du_an_id))""",
    # --- quyết định chấp thuận: một/phiên bản, gắn đúng kết luận + SHA đồ thị (đính chính sau duyệt = phiên bản kế tiếp)
    f"""CREATE TABLE m4.duyet_quyet_dinh (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL UNIQUE,
        ket_luan_id uuid NOT NULL UNIQUE,
        graph_sha256 text NOT NULL CHECK (graph_sha256 {_HEX}),
        ly_do text NOT NULL CHECK (length(btrim(ly_do)) BETWEEN 1 AND 2000),
        duyet_boi text NOT NULL,
        duyet_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        duyet_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        FOREIGN KEY (ket_luan_id, phien_ban_id) REFERENCES m4.duyet_ket_luan (id, phien_ban_id),
        FOREIGN KEY (ket_luan_id, graph_sha256) REFERENCES m4.duyet_ket_luan (id, graph_sha256),
        UNIQUE (id, phien_ban_id),
        UNIQUE (id, ket_luan_id))""",
    # --- PDF hồ sơ thanh toán đã duyệt: bytes thật do máy chủ nhận/lưu; ỨNG VIÊN gắn ĐÚNG phiên bản + kết luận (revision) + SHA đồ thị của kết luận đó
    # (FK tổ hợp — đồ thị/kết luận mới cần tải/gắn lại; cùng bytes dưới kết luận mới là MỘT ứng viên mới, không thừa kế gắn cũ). Nhiều ứng viên = lịch sử.
    f"""CREATE TABLE m4.duyet_pdf (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        ket_luan_id uuid NOT NULL,
        ket_luan_revision integer NOT NULL CHECK (ket_luan_revision >= 1),
        graph_sha256 text NOT NULL CHECK (graph_sha256 {_HEX}),
        vai text NOT NULL CHECK (vai = '{VAI_PDF}'),
        ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 200 AND strpos(ten, '/') = 0 AND strpos(ten, chr(92)) = 0 AND ten !~ '[[:cntrl:]]'
                                 AND ten NOT IN ('.', '..') AND btrim(ten) = ten),
        media_type text NOT NULL CHECK (media_type = 'application/pdf'),
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        object_key text NOT NULL,
        tai_boi text NOT NULL,
        tai_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tai_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'm4-raw/' || raw_sha256),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        FOREIGN KEY (ket_luan_id, phien_ban_id) REFERENCES m4.duyet_ket_luan (id, phien_ban_id),
        FOREIGN KEY (ket_luan_id, graph_sha256) REFERENCES m4.duyet_ket_luan (id, graph_sha256),
        UNIQUE (ket_luan_id, raw_sha256),
        UNIQUE (id, phien_ban_id),
        UNIQUE (id, ket_luan_id))""",
    # --- seal bất biến: một/phiên bản, một/quyết định; số liệu chốt (tiền + dòng chấp nhận + xử lý phát hiện); thuế chờ gói M4-03
    f"""CREATE TABLE m4.duyet_seal (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL UNIQUE,
        quyet_dinh_id uuid NOT NULL UNIQUE,
        ket_luan_id uuid NOT NULL,
        pdf_id uuid NOT NULL,
        graph_sha256 text NOT NULL CHECK (graph_sha256 {_HEX}),
        pdf_sha256 text NOT NULL CHECK (pdf_sha256 {_HEX}),
        so_lieu jsonb NOT NULL CHECK (jsonb_typeof(so_lieu) = 'object'),
        so_lieu_sha256 text NOT NULL CHECK (so_lieu_sha256 {_HEX}),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        FOREIGN KEY (quyet_dinh_id, phien_ban_id) REFERENCES m4.duyet_quyet_dinh (id, phien_ban_id),
        FOREIGN KEY (ket_luan_id, phien_ban_id) REFERENCES m4.duyet_ket_luan (id, phien_ban_id),
        FOREIGN KEY (pdf_id, phien_ban_id) REFERENCES m4.duyet_pdf (id, phien_ban_id),
        FOREIGN KEY (quyet_dinh_id, ket_luan_id) REFERENCES m4.duyet_quyet_dinh (id, ket_luan_id),
        FOREIGN KEY (pdf_id, ket_luan_id) REFERENCES m4.duyet_pdf (id, ket_luan_id),
        FOREIGN KEY (ket_luan_id, graph_sha256) REFERENCES m4.duyet_ket_luan (id, graph_sha256),
        UNIQUE (id, dot_id))""",
    # --- MỘT gốc KT chờ xác nhận theo đợt (nghiệp vụ logic) + MỘT phong bì bất biến mỗi seal (đính chính = phong bì con, cùng gốc)
    """CREATE TABLE m4.duyet_kt_cho (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        dot_id uuid NOT NULL UNIQUE REFERENCES m4.dot(id),
        nguon text NOT NULL CHECK (nguon = 'M4'),
        trang_thai text NOT NULL CHECK (trang_thai = 'CHO_XAC_NHAN'),
        seal_dau_id uuid NOT NULL UNIQUE,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (seal_dau_id, dot_id) REFERENCES m4.duyet_seal (id, dot_id),
        UNIQUE (id, dot_id))""",
    f"""CREATE TABLE m4.duyet_kt_phong_bi (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        cho_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        seal_id uuid NOT NULL UNIQUE,
        phien_ban_id uuid NOT NULL,
        thu_tu integer NOT NULL CHECK (thu_tu >= 1),
        truoc_id uuid UNIQUE REFERENCES m4.duyet_kt_phong_bi(id),
        noi_dung jsonb NOT NULL CHECK (jsonb_typeof(noi_dung) = 'object'),
        noi_dung_sha256 text NOT NULL CHECK (noi_dung_sha256 {_HEX}),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (cho_id, dot_id) REFERENCES m4.duyet_kt_cho (id, dot_id),
        FOREIGN KEY (seal_id, dot_id) REFERENCES m4.duyet_seal (id, dot_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        CHECK ((thu_tu = 1) = (truoc_id IS NULL)),
        UNIQUE (cho_id, thu_tu))""",
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()" for t in BANG_GHI_THEM),
    # --- đọc: XEM dự án (gồm phụ trách), hoặc REVIEW/DUYET khi đợt DA_NOP. Không raise, không lộ tồn tại.
    """CREATE OR REPLACE FUNCTION m4.duyet_doc_dot(p_dot uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.dot d WHERE d.id = p_dot AND (master.m4_duoc(d.du_an_id, 'XEM')
                       OR (d.trang_thai = 'DA_NOP' AND (master.m4_duoc(d.du_an_id, 'REVIEW') OR master.m4_duyet_duoc(d.du_an_id)))))
        $$""",
    # cờ quyền hiện hành của phiên trên một đợt (booleans tường minh cho DTO; máy chủ vẫn kiểm lại ở mọi lệnh)
    """CREATE OR REPLACE FUNCTION m4.duyet_quyen(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d_du_an m4.dot.du_an_id%TYPE; d_tt m4.dot.trang_thai%TYPE; xem boolean; soan boolean; rv boolean; du boolean;
        BEGIN
            SELECT x.du_an_id, x.trang_thai INTO d_du_an, d_tt FROM m4.dot x WHERE x.id = p_dot;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('xem', false, 'ket_luan', false, 'duyet', false, 'tai_pdf', false, 'phien_ban', false);
            END IF;
            soan := master.m4_duoc(d_du_an, 'SOAN');
            rv := master.m4_duoc(d_du_an, 'REVIEW');
            du := master.m4_duyet_duoc(d_du_an);
            xem := master.m4_duoc(d_du_an, 'XEM') OR (d_tt = 'DA_NOP' AND (rv OR du));
            RETURN jsonb_build_object('xem', xem, 'ket_luan', d_tt = 'DA_NOP' AND (rv OR du), 'duyet', d_tt = 'DA_NOP' AND du,
                                      'tai_pdf', d_tt = 'DA_NOP' AND (soan OR du), 'phien_ban', d_tt = 'DA_NOP' AND soan);
        END $$""",
    # kiểm quyền hiện hành cho MỘT hành động (raise mã chính xác) — gọi TRƯỚC biên nhận/blob/bằng chứng. Không thấy → 404, thấy nhưng thiếu vai → 403.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_kiem(p_dot uuid, p_hanh text) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d_du_an m4.dot.du_an_id%TYPE; d_tt m4.dot.trang_thai%TYPE;
        BEGIN
            IF p_hanh IS NULL OR p_hanh NOT IN {_sql_tuple(QUYEN_LENH)} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động duyệt không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.ai_id();
            SELECT x.du_an_id, x.trang_thai INTO d_du_an, d_tt FROM m4.dot x WHERE x.id = p_dot;
            IF NOT FOUND OR NOT m4.duyet_doc_dot(p_dot) THEN
                RAISE EXCEPTION 'M4_DUYET_KHONG_THAY: không thấy đợt (hoặc ngoài phạm vi hiện hành)' {_LOI};
            END IF;
            IF p_hanh = 'XEM' THEN
                RETURN 'XEM';
            END IF;
            IF d_tt = 'DA_NOP' THEN
                IF p_hanh = 'KET_LUAN' AND master.m4_duyet_duoc(d_du_an) THEN
                    RETURN 'DUYET';
                ELSIF p_hanh = 'KET_LUAN' AND master.m4_duoc(d_du_an, 'REVIEW') THEN
                    RETURN 'REVIEW';
                ELSIF p_hanh = 'CHAP_THUAN' AND master.m4_duyet_duoc(d_du_an) THEN
                    RETURN 'DUYET';
                ELSIF p_hanh = 'PDF' AND master.m4_duoc(d_du_an, 'SOAN') THEN
                    RETURN 'SOAN';
                ELSIF p_hanh = 'PDF' AND master.m4_duyet_duoc(d_du_an) THEN
                    RETURN 'DUYET';
                ELSIF p_hanh IN ('PHIEN_BAN','PHIEN_BAN_NOP') AND master.m4_duoc(d_du_an, 'SOAN') THEN
                    RETURN 'SOAN';
                END IF;
            END IF;
            RAISE EXCEPTION 'M4_DUYET_PHAM_VI: vai hiện hành không được % trên đợt này (kết luận: review/duyệt; chấp thuận: duyệt; PDF: soạn/duyệt; phiên bản: soạn; đợt phải đã nộp)', p_hanh {_LOI};
        END $$""",
    # bước khóa chung: quyền hiện hành → HĐ FOR UPDATE → đợt FOR UPDATE → phiên bản FOR UPDATE (bắt buộc thuộc đợt). Trả quyền + định danh.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_khoa(p_dot uuid, p_phien_ban uuid, p_hanh text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE q text; d m4.dot%ROWTYPE; v_id uuid; pn uuid;
        BEGIN""" + _TIN_CAY + f"""
            q := m4.duyet_kiem(p_dot, p_hanh);
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id FOR UPDATE;
            SELECT * INTO d FROM m4.dot WHERE id = p_dot FOR UPDATE;
            SELECT z.id INTO v_id FROM m4.duyet_phien_ban z WHERE z.id = p_phien_ban AND z.dot_id = p_dot FOR UPDATE;
            IF v_id IS NULL THEN
                RAISE EXCEPTION 'M4_DUYET_KHONG_THAY: không thấy phiên bản hồ sơ của đợt' {_LOI};
            END IF;
            SELECT phap_nhan_id INTO pn FROM master.du_an WHERE id = d.du_an_id;
            RETURN jsonb_build_object('quyen', q, 'dot_id', d.id, 'hop_dong_id', d.hop_dong_id, 'du_an_id', d.du_an_id, 'phap_nhan_id', pn,
                                      'so_dot', d.so_dot, 'trang_thai_dot', d.trang_thai);
        END $$""",
    # tra biên nhận dưới khóa giao dịch (actor, khóa) — sau quyền + khóa nghiệp vụ; trả FINAL cũ + receipt_id hoặc NULL
    f"""CREATE OR REPLACE FUNCTION m4.duyet_tra(p_khoa text, p_hanh text, p_dot uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE aid uuid; cu jsonb; rid uuid; d_du_an m4.dot.du_an_id%TYPE;
        BEGIN""" + _TIN_CAY + f"""
            IF p_hanh NOT IN {_sql_tuple(HANH_DONG)} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động duyệt không hợp lệ' {_LOI};
            END IF;
            aid := m4.ai_id();
            SELECT x.du_an_id INTO d_du_an FROM m4.dot x WHERE x.id = p_dot;
            cu := m4._bn_tra(aid, p_khoa, p_hanh, d_du_an, p_yc);
            IF cu IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT b.id INTO rid FROM m4.bien_nhan b WHERE b.nguoi_dung_id = aid AND b.khoa = p_khoa;
            RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu, 'receipt_id', rid);
        END $$""",
    # ============================================================== seal DÙNG CHUNG cho cả hai thứ tự (gọi trong giao dịch đã giữ khóa HĐ→đợt→phiên bản)
    # Có quyết định (đồ thị hiện hành, vật liệu còn đúng lúc nộp) + có PDF ỨNG VIÊN gắn ĐÚNG kết luận được duyệt (cùng SHA đồ thị — FK) + chưa seal →
    # seal + gốc KT (nếu chưa có) + phong bì; thiếu gì → trả trạng thái, KHÔNG tạo gì. p_pdf: ứng viên vừa tải (lệnh PDF) hoặc NULL (lệnh duyệt → ứng
    # viên gắn đúng kết luận mới nhất). PDF tải trên đồ thị/kết luận khác KHÔNG bao giờ được seal.
    f"""CREATE OR REPLACE FUNCTION m4._duyet_seal(p_phien_ban uuid, p_graph_hien_tai text, p_pdf uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id();
                v m4.duyet_phien_ban%ROWTYPE; q m4.duyet_quyet_dinh%ROWTYPE; k m4.duyet_ket_luan%ROWTYPE; p m4.duyet_pdf%ROWTYPE;
                s_id uuid; s_pdf uuid; goc uuid; moi uuid; pb_truoc uuid; pb_tt integer; sl jsonb; nd jsonb;
        BEGIN""" + _TIN_CAY + f"""
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_phien_ban FOR UPDATE;
            IF v.id IS NULL THEN
                RAISE EXCEPTION 'M4_DUYET_KHONG_THAY: không thấy phiên bản hồ sơ' {_LOI};
            END IF;
            SELECT x.id, x.pdf_id INTO s_id, s_pdf FROM m4.duyet_seal x WHERE x.phien_ban_id = v.id;
            IF s_id IS NOT NULL THEN
                SELECT c.id INTO goc FROM m4.duyet_kt_cho c WHERE c.dot_id = v.dot_id;
                RETURN jsonb_build_object('trang_thai', 'DA_SEAL', 'seal_id', s_id, 'pdf_id', s_pdf, 'kt_pending_id', goc, 'moi', false);
            END IF;
            SELECT * INTO q FROM m4.duyet_quyet_dinh WHERE phien_ban_id = v.id;
            IF q.id IS NULL THEN
                RETURN jsonb_build_object('trang_thai', 'CHO_DUYET', 'seal_id', NULL, 'kt_pending_id', NULL, 'moi', false);
            END IF;
            IF q.graph_sha256 IS DISTINCT FROM p_graph_hien_tai OR v.trang_thai <> 'DA_NOP'
               OR v.revision_ho_so IS DISTINCT FROM (SELECT hh.revision FROM m4.ho_so_hop_dong hh WHERE hh.hop_dong_id = v.hop_dong_id) THEN
                RETURN jsonb_build_object('trang_thai', 'CAN_KIEM_LAI', 'seal_id', NULL, 'kt_pending_id', NULL, 'moi', false);
            END IF;
            IF p_pdf IS NOT NULL THEN
                SELECT * INTO p FROM m4.duyet_pdf WHERE id = p_pdf AND phien_ban_id = v.id AND ket_luan_id = q.ket_luan_id AND graph_sha256 = q.graph_sha256;
            ELSE
                SELECT * INTO p FROM m4.duyet_pdf WHERE phien_ban_id = v.id AND ket_luan_id = q.ket_luan_id AND graph_sha256 = q.graph_sha256
                    ORDER BY tai_luc DESC, id DESC LIMIT 1;
            END IF;
            IF p.id IS NULL THEN
                RETURN jsonb_build_object('trang_thai', 'CHO_PDF', 'seal_id', NULL, 'kt_pending_id', NULL, 'moi', false);
            END IF;
            SELECT * INTO k FROM m4.duyet_ket_luan WHERE id = q.ket_luan_id;
            IF k.tien_te IS NULL OR NOT ({_TIEN_DU}) OR jsonb_array_length(k.thieu) > 0
               OR EXISTS (SELECT 1 FROM m4.duyet_ket_luan_dong x WHERE x.ket_luan_id = k.id AND x.khoi_luong_chap_nhan IS NULL) THEN
                RAISE EXCEPTION 'M4_DUYET_THIEU_CAN_CU: kết luận được duyệt còn thiếu số liệu bắt buộc — không seal' {_LOI};
            END IF;
            sl := jsonb_build_object('tien_te', k.tien_te, 'gia_tri_nt', k.gia_tri_nt, 'so_xin_thanh_toan', k.so_xin_thanh_toan, 'tam_ung', k.tam_ung,
                                     'thu_hoi', k.thu_hoi, 'giu_lai', k.giu_lai, 'ket_luan_id', k.id, 'ket_luan_revision', k.revision,
                                     'dong', (SELECT coalesce(jsonb_agg(jsonb_build_object('row_id', x.row_id, 'ma_hm', x.ma_hm, 'dvt', x.dvt,
                                                                                          'khoi_luong_chap_nhan', x.khoi_luong_chap_nhan) ORDER BY x.row_id), '[]'::jsonb)
                                              FROM m4.duyet_ket_luan_dong x WHERE x.ket_luan_id = k.id),
                                     'xu_ly_phat_hien', k.xu_ly_phat_hien, 'thue', 'CHO_GOI_M4_03');
            INSERT INTO m4.duyet_seal (phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, quyet_dinh_id, ket_luan_id, pdf_id, graph_sha256, pdf_sha256,
                                       so_lieu, so_lieu_sha256, tao_boi, tao_boi_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, v.id, q.id, k.id, p.id, q.graph_sha256, p.raw_sha256, sl,
                        encode(sha256(convert_to(sl::text, 'UTF8')), 'hex'), ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.duyet_kt_cho (phap_nhan_id, du_an_id, hop_dong_id, dot_id, nguon, trang_thai, seal_dau_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, 'M4', 'CHO_XAC_NHAN', moi)
                ON CONFLICT (dot_id) DO NOTHING;
            SELECT c.id INTO goc FROM m4.duyet_kt_cho c WHERE c.dot_id = v.dot_id;
            SELECT b.id, b.thu_tu INTO pb_truoc, pb_tt FROM m4.duyet_kt_phong_bi b WHERE b.cho_id = goc ORDER BY b.thu_tu DESC LIMIT 1;
            nd := sl || jsonb_build_object('nguon', 'M4', 'seal_id', moi, 'phien_ban_id', v.id, 'phien_ban_so', v.so, 'quyet_dinh_id', q.id,
                                           'pdf', jsonb_build_object('id', p.id, 'raw_sha256', p.raw_sha256, 'byte_length', p.byte_length),
                                           'ap', 'CHUA_NOI_GOI_M4_03', 'request', 'CHUA_NOI_GOI_M4_04');
            INSERT INTO m4.duyet_kt_phong_bi (cho_id, dot_id, du_an_id, seal_id, phien_ban_id, thu_tu, truoc_id, noi_dung, noi_dung_sha256)
                VALUES (goc, v.dot_id, v.du_an_id, moi, v.id, coalesce(pb_tt, 0) + 1, pb_truoc, nd, encode(sha256(convert_to(nd::text, 'UTF8')), 'hex'));
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_SEAL', ai, jsonb_build_object('seal_id', moi, 'phien_ban_id', v.id, 'quyet_dinh_id', q.id,
                                                                                                   'pdf_id', p.id, 'kt_pending_id', goc));
            RETURN jsonb_build_object('trang_thai', 'DA_SEAL', 'seal_id', moi, 'pdf_id', p.id, 'kt_pending_id', goc, 'moi', true);
        END $$""",
    # ============================================================== lệnh (SECURITY INVOKER, chỉ kết nối chủ bảng; máy chủ dựng đồ thị + SHA hiện hành)
    # LƯU KẾT LUẬN: REVIEW/DUYET trên đợt đã nộp; phiên bản mới nhất chưa duyệt; revision + đồ thị CAS; L3 đã công bố khớp căn cứ hiện hành.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_ghi_ket_luan(p_khoa text, p_yc jsonb, p_dot uuid, p_phien_ban uuid, p_revision integer, p_expected text,
                                                        p_graph_hien_tai text, p_graph jsonb, p_nd jsonb, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + f""" q text; v m4.duyet_phien_ban%ROWTYPE; rv integer; moi uuid; e jsonb;
        BEGIN""" + _TIN_CAY + f"""
            q := (m4.duyet_khoa(p_dot, p_phien_ban, 'KET_LUAN'))->>'quyen';
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_phien_ban;
            cu := m4._bn_tra(aid, p_khoa, 'DUYET_KET_LUAN', v.du_an_id, p_yc);""" + _LAP_LAI + _PB_HIEN_HANH + _VAT_LIEU + f"""
            IF EXISTS (SELECT 1 FROM m4.duyet_quyet_dinh x WHERE x.phien_ban_id = v.id) THEN
                RAISE EXCEPTION 'M4_DUYET_DA_CHAP_THUAN: phiên bản đã được chấp thuận — đính chính bằng phiên bản kế tiếp' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.duyet_ket_luan x WHERE x.phien_ban_id = v.id;
            IF p_revision IS NULL OR p_revision <> rv THEN
                RAISE EXCEPTION 'M4_REVISION_CU: kết luận của phiên bản đã có revision mới (hiện tại %) — tải lại', rv {_LOI};
            END IF;""" + _CAS + f"""
            IF p_graph IS NULL OR jsonb_typeof(p_graph) <> 'object' OR (p_graph->'l3'->>'trang_thai') IS DISTINCT FROM 'CO' THEN
                RAISE EXCEPTION 'M4_DUYET_CHUA_CO_REVIEW: chưa có kết quả Chứng từ L3 đã công bố khớp căn cứ hiện hành — chạy lại L3 trước khi kết luận' {_LOI};
            END IF;
            IF p_nd IS NULL OR jsonb_typeof(p_nd) <> 'object' OR jsonb_typeof(p_nd->'dong') <> 'array' OR jsonb_typeof(p_nd->'xu_ly_phat_hien') <> 'array'
               OR jsonb_typeof(p_nd->'thieu') <> 'array' OR jsonb_typeof(p_nd->'canh_bao') <> 'array' OR jsonb_typeof(p_nd->'de_xuat_nguon') <> 'object' THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: nội dung kết luận không đúng hình dạng' {_LOI};
            END IF;
            INSERT INTO m4.duyet_ket_luan (phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, revision, graph, graph_sha256, l3_run_id, l2_run_id,
                                           tien_te, gia_tri_nt, so_xin_thanh_toan, tam_ung, thu_hoi, giu_lai, xu_ly_phat_hien, de_xuat_nguon, thieu,
                                           canh_bao, ly_do, quyen, tao_boi, tao_boi_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, v.id, rv + 1, p_graph, p_graph_hien_tai, (p_graph->'l3'->>'run_id')::uuid,
                        nullif(p_nd->>'l2_run_id', '')::uuid, p_nd->>'tien_te', p_nd->>'gia_tri_nt', p_nd->>'so_xin_thanh_toan', p_nd->>'tam_ung',
                        p_nd->>'thu_hoi', p_nd->>'giu_lai', p_nd->'xu_ly_phat_hien', p_nd->'de_xuat_nguon', p_nd->'thieu', p_nd->'canh_bao', p_ly_do, q, ai, aid)
                RETURNING id INTO moi;
            FOR e IN SELECT * FROM jsonb_array_elements(p_nd->'dong') LOOP
                INSERT INTO m4.duyet_ket_luan_dong (ket_luan_id, du_an_id, row_id, ma_hm, ten, dvt, de_xuat, khoi_luong_chap_nhan)
                    VALUES (moi, v.du_an_id, e->>'row_id', e->>'ma_hm', e->>'ten', e->>'dvt', coalesce(e->'de_xuat', '{{}}'::jsonb), e->>'khoi_luong_chap_nhan');
            END LOOP;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_KET_LUAN', ai, jsonb_build_object('ket_luan_id', moi, 'phien_ban_id', v.id, 'revision', rv + 1,
                                                                                                       'quyen', q, 'so_thieu', jsonb_array_length(p_nd->'thieu')));
            -- kết luận mới: chưa quyết định, chưa ứng viên PDF gắn nó (PDF cũ gắn kết luận cũ chỉ còn lịch sử), chưa seal/KT cho phiên bản này
            kq := jsonb_build_object('hanh_dong', 'KET_LUAN', 'context', {_NGU_CANH}, 'phien_ban_id', v.id, 'ket_luan_id', moi, 'ket_luan_revision', rv + 1,
                                     'quyet_dinh_id', NULL, 'pdf_id', NULL, 'seal_id', NULL, 'kt_pending_id', NULL,
                                     'trang_thai', CASE WHEN jsonb_array_length(p_nd->'thieu') = 0 THEN 'CHO_DUYET' ELSE 'CHO_KET_LUAN' END,
                                     'thieu', p_nd->'thieu');""" + _KET.format(a="DUYET_KET_LUAN") + """
        END $$""",
    # CHẤP THUẬN: chỉ DUYET; kết luận MỚI NHẤT của đúng phiên bản, cùng đồ thị hiện hành, đủ số liệu bắt buộc; rồi seal dùng chung (thiếu PDF → CHO_PDF).
    f"""CREATE OR REPLACE FUNCTION m4.duyet_chap_thuan(p_khoa text, p_yc jsonb, p_dot uuid, p_phien_ban uuid, p_revision integer, p_expected text,
                                                      p_graph_hien_tai text, p_ket_luan uuid, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + f""" v m4.duyet_phien_ban%ROWTYPE; k m4.duyet_ket_luan%ROWTYPE; rv integer; moi uuid; sr jsonb;
        BEGIN""" + _TIN_CAY + f"""
            PERFORM m4.duyet_khoa(p_dot, p_phien_ban, 'CHAP_THUAN');
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_phien_ban;
            cu := m4._bn_tra(aid, p_khoa, 'DUYET_CHAP_THUAN', v.du_an_id, p_yc);""" + _LAP_LAI + _PB_HIEN_HANH + _VAT_LIEU + f"""
            IF EXISTS (SELECT 1 FROM m4.duyet_quyet_dinh x WHERE x.phien_ban_id = v.id) THEN
                RAISE EXCEPTION 'M4_DUYET_DA_CHAP_THUAN: phiên bản đã có quyết định chấp thuận (một quyết định/phiên bản)' {_LOI};
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                RAISE EXCEPTION 'M4_THIEU_LY_DO: chấp thuận cần lý do/ý kiến' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.duyet_ket_luan x WHERE x.phien_ban_id = v.id;
            IF p_revision IS NULL OR p_revision <> rv THEN
                RAISE EXCEPTION 'M4_REVISION_CU: kết luận của phiên bản đã có revision mới (hiện tại %) — tải lại', rv {_LOI};
            END IF;""" + _CAS + f"""
            SELECT * INTO k FROM m4.duyet_ket_luan WHERE id = p_ket_luan AND phien_ban_id = v.id;
            IF k.id IS NULL OR k.revision <> rv THEN
                RAISE EXCEPTION 'M4_DUYET_KET_LUAN_CU: chỉ chấp thuận kết luận mới nhất của đúng phiên bản' {_LOI};
            END IF;
            IF k.graph_sha256 IS DISTINCT FROM p_graph_hien_tai THEN
                RAISE EXCEPTION 'M4_DUYET_KET_LUAN_CU: kết luận dựa trên căn cứ/review cũ — kết luận lại trên căn cứ hiện hành' {_LOI};
            END IF;
            IF k.tien_te IS NULL OR NOT ({_TIEN_DU}) OR jsonb_array_length(k.thieu) > 0
               OR NOT EXISTS (SELECT 1 FROM m4.duyet_ket_luan_dong x WHERE x.ket_luan_id = k.id)
               OR EXISTS (SELECT 1 FROM m4.duyet_ket_luan_dong x WHERE x.ket_luan_id = k.id AND x.khoi_luong_chap_nhan IS NULL) THEN
                RAISE EXCEPTION 'M4_DUYET_THIEU_CAN_CU: kết luận còn thiếu tiền/khối lượng chấp nhận/xử lý phát hiện bắt buộc (% mục) — không chấp thuận',
                    jsonb_array_length(k.thieu) {_LOI};
            END IF;
            INSERT INTO m4.duyet_quyet_dinh (phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, ket_luan_id, graph_sha256, ly_do, duyet_boi, duyet_boi_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, v.id, k.id, k.graph_sha256, p_ly_do, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_CHAP_THUAN', ai, jsonb_build_object('quyet_dinh_id', moi, 'ket_luan_id', k.id,
                                                                                                         'phien_ban_id', v.id));
            sr := m4._duyet_seal(v.id, p_graph_hien_tai, NULL);
            kq := jsonb_build_object('hanh_dong', 'CHAP_THUAN', 'context', {_NGU_CANH}, 'phien_ban_id', v.id, 'ket_luan_id', k.id, 'quyet_dinh_id', moi,
                                     'pdf_id', sr->'pdf_id', 'seal_id', sr->'seal_id', 'kt_pending_id', sr->'kt_pending_id', 'trang_thai', sr->>'trang_thai');"""
    + _KET.format(a="DUYET_CHAP_THUAN") + """
        END $$""",
    # PDF hồ sơ đã duyệt: SOAN/DUYET trên đợt đã nộp; bytes đã lưu m4-raw/<sha> TRƯỚC khi gọi; không phải tệp HĐ/PL; phiên bản chưa seal; rồi seal dùng chung.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_ghi_pdf(p_khoa text, p_yc jsonb, p_dot uuid, p_phien_ban uuid, p_revision integer, p_expected text,
                                                   p_graph_hien_tai text, p_sha text, p_len bigint, p_ten text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + f""" v m4.duyet_phien_ban%ROWTYPE; k m4.duyet_ket_luan%ROWTYPE; rv integer; moi uuid; sr jsonb; qd uuid;
        BEGIN""" + _TIN_CAY + f"""
            PERFORM m4.duyet_khoa(p_dot, p_phien_ban, 'PDF');
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_phien_ban;
            cu := m4._bn_tra(aid, p_khoa, 'DUYET_PDF', v.du_an_id, p_yc);""" + _LAP_LAI + _PB_HIEN_HANH + f"""
            IF EXISTS (SELECT 1 FROM m4.duyet_seal x WHERE x.phien_ban_id = v.id) THEN
                RAISE EXCEPTION 'M4_DUYET_DA_SEAL: phiên bản đã seal — PDF đã chốt; đính chính bằng phiên bản kế tiếp' {_LOI};
            END IF;""" + _VAT_LIEU + f"""
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.duyet_ket_luan x WHERE x.phien_ban_id = v.id;
            IF p_revision IS NULL OR p_revision <> rv THEN
                RAISE EXCEPTION 'M4_REVISION_CU: kết luận của phiên bản đã có revision mới (hiện tại %) — tải lại', rv {_LOI};
            END IF;""" + _CAS + f"""
            -- ứng viên PDF gắn ĐÚNG kết luận mới nhất (đang xem) + SHA đồ thị của nó = đồ thị hiện hành; chưa kết luận / kết luận cũ → chưa gắn được
            SELECT * INTO k FROM m4.duyet_ket_luan x WHERE x.phien_ban_id = v.id AND x.revision = rv;
            IF k.id IS NULL THEN
                RAISE EXCEPTION 'M4_DUYET_CHUA_KET_LUAN: PDF hồ sơ đã duyệt gắn với một kết luận — lưu kết luận trước rồi tải PDF' {_LOI};
            END IF;
            IF k.graph_sha256 IS DISTINCT FROM p_graph_hien_tai THEN
                RAISE EXCEPTION 'M4_DUYET_KET_LUAN_CU: kết luận dựa trên căn cứ/review cũ — kết luận lại trên căn cứ hiện hành rồi tải PDF' {_LOI};
            END IF;
            IF p_sha IS NULL OR p_sha !{_HEX} OR p_len IS NULL OR p_len <= 0 THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hash/độ dài PDF do máy chủ tính không hợp lệ' {_LOI};
            END IF;
            IF EXISTS (SELECT 1 FROM m4.tep t WHERE t.du_an_id = v.du_an_id AND t.raw_sha256 = p_sha AND t.vai_tro_tai_lieu IN ('HOP_DONG','PHU_LUC')) THEN
                RAISE EXCEPTION 'M4_DUYET_PDF_SAI_VAI_TRO: đây là tệp hợp đồng/phụ lục, không phải PDF hồ sơ thanh toán đã duyệt' {_LOI};
            END IF;
            INSERT INTO m4.duyet_pdf (phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, ket_luan_id, ket_luan_revision, graph_sha256, vai, ten,
                                      media_type, raw_sha256, byte_length, object_key, tai_boi, tai_boi_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, v.id, k.id, k.revision, k.graph_sha256, '{VAI_PDF}', p_ten, 'application/pdf',
                        p_sha, p_len, 'm4-raw/' || p_sha, ai, aid)
                ON CONFLICT (ket_luan_id, raw_sha256) DO NOTHING
                RETURNING id INTO moi;
            IF moi IS NULL THEN  -- cùng bytes cho CÙNG kết luận/đồ thị (khóa khác/người khác) → một ứng viên; kết luận khác luôn là hàng mới
                SELECT x.id INTO moi FROM m4.duyet_pdf x WHERE x.ket_luan_id = k.id AND x.raw_sha256 = p_sha AND x.byte_length = p_len;
                IF moi IS NULL THEN
                    RAISE EXCEPTION 'M4_TEP_XUNG_DOT: cùng hash nhưng độ dài khác' {_LOI};
                END IF;
            ELSE
                INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                    VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_PDF', ai, jsonb_build_object('pdf_id', moi, 'phien_ban_id', v.id, 'sha', p_sha,
                                                                                                  'ket_luan_id', k.id, 'ket_luan_revision', k.revision,
                                                                                                  'graph_sha256', k.graph_sha256));
            END IF;
            sr := m4._duyet_seal(v.id, p_graph_hien_tai, moi);
            SELECT x.id INTO qd FROM m4.duyet_quyet_dinh x WHERE x.phien_ban_id = v.id;
            kq := jsonb_build_object('hanh_dong', 'PDF', 'context', {_NGU_CANH}, 'phien_ban_id', v.id, 'ket_luan_id', k.id, 'quyet_dinh_id', qd,
                                     'pdf_id', moi, 'seal_id', sr->'seal_id', 'kt_pending_id', sr->'kt_pending_id', 'trang_thai', sr->>'trang_thai');"""
    + _KET.format(a="DUYET_PDF") + """
        END $$""",
    # PHIÊN BẢN KẾ TIẾP (nháp): chỉ SOAN; cha = bản mới nhất đã nộp; không tạo quyết định/seal/KT/AP/Request; lịch sử bản cũ giữ nguyên.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_tao_phien_ban(p_khoa text, p_yc jsonb, p_dot uuid, p_parent uuid, p_revision integer, p_expected text,
                                                         p_graph_hien_tai text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + f""" v m4.duyet_phien_ban%ROWTYPE; rv integer; moi uuid;
        BEGIN""" + _TIN_CAY + f"""
            PERFORM m4.duyet_khoa(p_dot, p_parent, 'PHIEN_BAN');
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_parent;
            cu := m4._bn_tra(aid, p_khoa, 'DUYET_PHIEN_BAN', v.du_an_id, p_yc);""" + _LAP_LAI + _PB_HIEN_HANH + f"""
            IF EXISTS (SELECT 1 FROM m4.duyet_phien_ban z WHERE z.dot_id = v.dot_id AND z.trang_thai = 'NHAP') THEN
                RAISE EXCEPTION 'M4_DUYET_DA_CO_NHAP: đợt đã có phiên bản nháp đang mở' {_LOI};
            END IF;
            IF p_ly_do IS NULL OR btrim(p_ly_do) = '' THEN
                RAISE EXCEPTION 'M4_THIEU_LY_DO: tạo phiên bản kế tiếp cần lý do' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.duyet_ket_luan x WHERE x.phien_ban_id = v.id;
            IF p_revision IS NULL OR p_revision <> rv THEN
                RAISE EXCEPTION 'M4_REVISION_CU: kết luận của phiên bản cha đã có revision mới (hiện tại %) — tải lại', rv {_LOI};
            END IF;""" + _CAS + f"""
            INSERT INTO m4.duyet_phien_ban (phap_nhan_id, du_an_id, hop_dong_id, dot_id, so, parent_id, trang_thai, ly_do, tao_boi, tao_boi_id)
                VALUES (v.phap_nhan_id, v.du_an_id, v.hop_dong_id, v.dot_id, v.so + 1, v.id, 'NHAP', p_ly_do, ai, aid)
                RETURNING id INTO moi;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_PHIEN_BAN', ai, jsonb_build_object('phien_ban_id', moi, 'parent_id', v.id, 'so', v.so + 1));
            kq := jsonb_build_object('hanh_dong', 'PHIEN_BAN', 'context', {_NGU_CANH}, 'phien_ban_id', moi, 'phien_ban_so', v.so + 1, 'parent_id', v.id,
                                     'ket_luan_id', NULL, 'quyet_dinh_id', NULL, 'pdf_id', NULL, 'seal_id', NULL, 'kt_pending_id', NULL,
                                     'trang_thai', 'CAN_KIEM_LAI');"""
    + _KET.format(a="DUYET_PHIEN_BAN") + """
        END $$""",
    # NỘP/KIỂM LẠI phiên bản nháp: chỉ SOAN; dùng lại gate nộp thật (m4.thieu: HĐ/tham số/PL/BOQ/ngày/checklist) + L3 đã công bố khớp căn cứ (đồ thị);
    # snapshot cùng mẫu m4.nop (không sửa m4.nop/đợt). Thiếu điều kiện → chặn đúng lệnh này.
    f"""CREATE OR REPLACE FUNCTION m4.duyet_nop_phien_ban(p_khoa text, p_yc jsonb, p_dot uuid, p_phien_ban uuid, p_revision integer, p_expected text,
                                                         p_graph_hien_tai text, p_graph jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + f""" v m4.duyet_phien_ban%ROWTYPE; d m4.dot%ROWTYPE; h record; t record; x record; con jsonb; s jsonb; dg text;
        BEGIN""" + _TIN_CAY + f"""
            PERFORM m4.duyet_khoa(p_dot, p_phien_ban, 'PHIEN_BAN_NOP');
            SELECT * INTO v FROM m4.duyet_phien_ban WHERE id = p_phien_ban;
            cu := m4._bn_tra(aid, p_khoa, 'DUYET_PHIEN_BAN_NOP', v.du_an_id, p_yc);""" + _LAP_LAI + f"""
            IF v.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'M4_DUYET_PHIEN_BAN_CU: phiên bản đã nộp — không nộp lại' {_LOI};
            END IF;
            IF p_revision IS NULL OR p_revision <> 0 THEN
                RAISE EXCEPTION 'M4_REVISION_CU: phiên bản nháp chưa có kết luận (revision 0)' {_LOI};
            END IF;""" + _CAS + f"""
            con := m4.thieu(p_dot);
            IF jsonb_array_length(con) > 0 THEN
                RAISE EXCEPTION 'M4_CHUA_DU_CAN_CU: còn % mục thiếu — xem danh sách cần bổ sung', jsonb_array_length(con) {_LOI};
            END IF;
            IF p_graph IS NULL OR (p_graph->'l3'->>'trang_thai') IS DISTINCT FROM 'CO' THEN
                RAISE EXCEPTION 'M4_DUYET_CHUA_CO_REVIEW: chưa có kết quả Chứng từ L3 đã công bố khớp căn cứ hiện hành — chạy lại L3 rồi nộp phiên bản' {_LOI};
            END IF;
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id;
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
                'boq', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'phu_luc_id', q.phu_luc_id, 'so_dong', q.so_dong,
                                                                     'so_phat_hien', jsonb_array_length(q.phat_hien)) ORDER BY q.lan), '[]'::jsonb)
                        FROM m4.boq q WHERE q.hop_dong_id = h.hop_dong_id AND q.trang_thai = 'DA_MAP'
                          AND q.lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = q.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM q.phu_luc_id)),
                'dot', jsonb_build_object('id', d.id, 'so_dot', d.so_dot, 'ngay_nghiem_thu', d.ngay_nghiem_thu, 'revision', d.revision),
                'tai_lieu', (SELECT coalesce(jsonb_agg(jsonb_build_object('muc', k.muc, 'tep_id', k.tep_id, 'raw_sha256', f.raw_sha256)
                                                       ORDER BY k.muc, f.raw_sha256), '[]'::jsonb)
                             FROM m4.dot_tep k JOIN m4.tep f ON f.id = k.tep_id WHERE k.dot_id = d.id),
                'phien_ban', jsonb_build_object('id', v.id, 'so', v.so, 'parent_id', v.parent_id),
                'review_l3', p_graph->'l3');
            dg := encode(sha256(convert_to(s::text, 'UTF8')), 'hex');
            UPDATE m4.duyet_phien_ban SET trang_thai = 'DA_NOP', revision_ho_so = h.revision, snapshot = s, digest = dg, nop_boi = ai, nop_boi_id = aid,
                   nop_luc = now()
                WHERE id = v.id;
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (v.du_an_id, v.hop_dong_id, v.dot_id, 'DUYET_PHIEN_BAN_NOP', ai, jsonb_build_object('phien_ban_id', v.id, 'so', v.so, 'digest', dg));
            kq := jsonb_build_object('hanh_dong', 'PHIEN_BAN_NOP', 'context', {_NGU_CANH}, 'phien_ban_id', v.id, 'phien_ban_so', v.so, 'digest', dg,
                                     'ket_luan_id', NULL, 'quyet_dinh_id', NULL, 'pdf_id', NULL, 'seal_id', NULL, 'kt_pending_id', NULL,
                                     'trang_thai', 'CHO_KET_LUAN');"""
    + _KET.format(a="DUYET_PHIEN_BAN_NOP") + """
        END $$""",
    # --- quyền thực thi + RLS đọc (GRANT SELECT kỹ thuật cho app_web hiện hữu, luôn qua RLS; không role/quyền nghiệp vụ mới ngoài vai dự án DUYET)
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_LENH) + " FROM PUBLIC",
    "REVOKE ALL ON " + ", ".join(f"m4.{t}" for t in BANG) + " FROM PUBLIC",
    *(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY" for t in BANG),
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON """ + ", ".join(f"m4.{t}" for t in BANG) + """ TO app_web;
            CREATE POLICY duyet_phien_ban_web ON m4.duyet_phien_ban FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_ket_luan_web ON m4.duyet_ket_luan FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_ket_luan_dong_web ON m4.duyet_ket_luan_dong FOR SELECT TO app_web
                USING (EXISTS (SELECT 1 FROM m4.duyet_ket_luan k WHERE k.id = ket_luan_id AND m4.duyet_doc_dot(k.dot_id)));
            CREATE POLICY duyet_quyet_dinh_web ON m4.duyet_quyet_dinh FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_pdf_web ON m4.duyet_pdf FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_seal_web ON m4.duyet_seal FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_kt_cho_web ON m4.duyet_kt_cho FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
            CREATE POLICY duyet_kt_phong_bi_web ON m4.duyet_kt_phong_bi FOR SELECT TO app_web USING (m4.duyet_doc_dot(dot_id));
        END IF;
    END $$""",
)
