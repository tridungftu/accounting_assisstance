"""Migration 17 — M4 Cổng hồ sơ xây dựng (bản sửa M4-01B; M17 chưa triển khai lên DEMO nên sửa tại chỗ, prefix 1–16 giữ nguyên byte).

Đầu bài: docs/GIAO-CODE-M4-01-CONG-HO-SO-VA-TAI-SU-DUNG.md + docs/GIAO-CODE-M4-01B-SUA-GATE-VA-BO-SUNG-KIEM.md (B1–B6).
Module chỉ chứa hằng chuỗi SQL (không import ha_tang để tránh vòng import); `ha_tang/pg_migrations.py` nối `M0017_M4` vào PG_MIGRATIONS.

Ranh giới quyền:
- Lệnh người dùng thường (app_web, SECURITY DEFINER): tạo HĐ, gắn tệp HĐ, xác nhận tham số, khai/thêm/hủy PL, đợt, gắn tệp đợt, nộp.
  Danh tính phiên + phạm vi dự án hiện hành (master.m4_duoc) kiểm TRƯỚC tra biên nhận; biên nhận tra TRƯỚC kiểm revision/làm việc.
- Đường ghi nguồn tin cậy (SECURITY INVOKER, chỉ chạy được bằng kết nối CHỦ BẢNG của máy chủ — cùng kết nối ghi nguồn M5/M2): ghi tệp đã nhận bytes,
  kết quả trích, kết quả đọc BOQ, sửa tham số kèm kết quả máy kiểm trích dẫn. app_web KHÔNG có EXECUTE; trusted worker vẫn kiểm danh tính/phạm vi của
  nhân viên trong phiên và không tự xác nhận/duyệt thay phòng dự án hay CFO.
- Biên nhận FINAL do chính lệnh ghi trong cùng giao dịch (m4._bn_ghi nội bộ); không còn hàm công khai cho caller tự chốt JSON.
- Thu hồi phạm vi dự án = dấu thu hồi chỉ ghi một lần (không DELETE); quyền/biên nhận đọc lifecycle hiện hành.
"""

from __future__ import annotations

DANH_MUC_THAM_SO = (  # 37 mã danh mục nguồn (trich_xuat/danh_muc.py MAC_DINH), không lấy DS_THAM_SO 36 mã của csdl_hop_dong (thiếu TC-09)
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
DANH_MUC_HO_SO = (
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
MEDIA = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/pdf", "image/png", "image/jpeg")
# hàm đường ghi nguồn tin cậy (chỉ kết nối chủ bảng); lệnh thường cho app_web; hàm đọc cho app_web; nội bộ không cấp
HAM_TIN_CAY = ("m4.ghi_tep(text, uuid, text, text, bigint, text, text)",
               "m4.ghi_trich_xuat(text, uuid, integer, uuid, text, text, text, text, text, text, jsonb, jsonb)",
               "m4.sua_tham_so(text, uuid, integer, text, text, text, text, text, text, text, text)",
               "m4.ghi_boq(text, uuid, integer, uuid, text, uuid, text, integer, jsonb, text, jsonb, jsonb, jsonb)",
               "m4.thu_hoi_quyen_du_an(uuid, text, text)")
HAM_LENH = ("m4.tao_hop_dong(text, uuid, text, text)", "m4.gan_tep_hop_dong(text, uuid, integer, uuid)",
            "m4.xac_nhan_tham_so(text, uuid, integer, text, text)", "m4.khai_phu_luc(text, uuid, integer, text)",
            "m4.them_phu_luc(text, uuid, integer, text, date, date, text, boolean, text, uuid)", "m4.huy_phu_luc(text, uuid, integer, text)",
            "m4.tao_dot(text, uuid, integer, date)", "m4.sua_dot(text, uuid, integer, date)", "m4.gan_tep_dot(text, uuid, integer, uuid, text)",
            "m4.nop(text, uuid, integer, integer)")
HAM_DOC = ("m4.thieu(uuid)", "m4.digest_tham_so(uuid)", "m4.tra_bien_nhan(text)", "m4.tep_da_nop(uuid)")
HAM_NOI_BO = ("m4.ai_id()", "m4._bn_tra(uuid, text, text, uuid, jsonb)", "m4._bn_ghi(uuid, text, text, uuid, jsonb, jsonb)", "m4._khoa_dot(uuid)")


def _lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


_MEDIA_SQL = "(" + ",".join(_lit(m) for m in MEDIA) + ")"
_HEX = "~ '^[0-9a-f]{64}$'"
_LOI = "USING ERRCODE = 'P0001'"
_SOAN = """
            IF NOT master.m4_duoc({d}, 'SOAN') THEN
                RAISE EXCEPTION 'M4_KHONG_CO_QUYEN_DU_AN: cần quyền soạn hồ sơ hiện hành (phòng dự án phụ trách) đúng dự án' """ + _LOI + """;
            END IF;"""
# khóa hồ sơ HĐ + quyền hiện hành (KHÔNG kiểm revision ở đây — biên nhận phải tra trước revision)
_HO_SO = """
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = {hd} FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_HOP_DONG: không thấy hồ sơ hợp đồng M4' """ + _LOI + """;
            END IF;""" + _SOAN.format(d="h.du_an_id")
_REPLAY = """
            cu := m4._bn_tra(aid, p_khoa, '{a}', {d}, yc);
            IF cu IS NOT NULL THEN
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu);
            END IF;"""
_REV = """
            IF {rev} IS NULL OR h.revision <> {rev} THEN
                RAISE EXCEPTION 'M4_REVISION_CU: hồ sơ đã đổi (revision hiện tại %) — tải lại rồi thao tác', h.revision """ + _LOI + """;
            END IF;"""
_TANG = """
            UPDATE m4.ho_so_hop_dong SET revision = revision + 1{ts}, cap_nhat_luc = now() WHERE hop_dong_id = h.hop_dong_id
                RETURNING revision INTO moi;"""
_KET = """
            PERFORM m4._bn_ghi(aid, p_khoa, '{a}', {d}, yc, kq);
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq);"""
_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.tep'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường ghi nguồn tin cậy của máy chủ được ghi kết quả nguồn/kiểm máy' """ + _LOI + """;
            END IF;"""
_NK = "INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet) VALUES ({d}, {hd}, {dot}, '{a}', ai, {ct});"
_KHAI_BAO = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); yc jsonb; cu jsonb; kq jsonb;"


def _tep_ten_hop_le(v: str) -> str:
    """Điều kiện SQL cho tên tệp (không dùng chr(0): PostgreSQL text không chứa NUL, máy chủ chặn NUL trước khi ghi)."""
    return (f"length({v}) BETWEEN 1 AND 200 AND strpos({v}, '/') = 0 AND strpos({v}, chr(92)) = 0 AND {v} !~ '[[:cntrl:]]' "
            f"AND {v} NOT IN ('.', '..') AND btrim({v}) = {v}")


M0017_M4 = (
    "SET LOCAL check_function_bodies = off",
    "CREATE SCHEMA IF NOT EXISTS m4",
    # --- bảo vệ ghi: bảng M4 chỉ ghi qua hàm định nghĩa/đường tin cậy (chủ bảng); bảng bất biến chỉ ghi thêm
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
    + ", ".join(f"({_lit(m)}, {_lit(n)}, {_lit(t)}, {i})" for i, (m, n, t) in enumerate(DANH_MUC_THAM_SO, 1)),
    "CREATE TRIGGER danh_muc_tham_so_bat_bien BEFORE UPDATE OR DELETE ON m4.danh_muc_tham_so FOR EACH ROW EXECUTE FUNCTION giao_tiep.chi_ghi_them()",
    """CREATE TABLE m4.danh_muc_ho_so_dot (
        ma text PRIMARY KEY CHECK (ma ~ '^[A-F][0-9]{2}$'),
        ten text NOT NULL,
        bat_buoc_dot_dau boolean NOT NULL,
        bat_buoc_dot_sau boolean NOT NULL,
        ghi_chu text)""",
    "INSERT INTO m4.danh_muc_ho_so_dot (ma, ten, bat_buoc_dot_dau, bat_buoc_dot_sau, ghi_chu) VALUES "
    + ", ".join("(" + ", ".join(_lit(x) for x in r) + ")" for r in DANH_MUC_HO_SO),
    "CREATE TRIGGER danh_muc_ho_so_dot_bat_bien BEFORE UPDATE OR DELETE ON m4.danh_muc_ho_so_dot FOR EACH ROW EXECUTE FUNCTION giao_tiep.chi_ghi_them()",
    # --- phạm vi dự án: chủ CSDL/quản trị cấu hình; thu hồi = dấu thu hồi ghi MỘT lần (giữ lịch sử, không DELETE); cấp lại = hàng mới
    """CREATE TABLE m4.quyen_du_an (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        vai text NOT NULL CHECK (vai IN ('PHU_TRACH','XEM','REVIEW')),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        thu_hoi_luc timestamptz,
        thu_hoi_boi text,
        thu_hoi_ly_do text,
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        CHECK ((thu_hoi_luc IS NULL) = (thu_hoi_boi IS NULL) AND (thu_hoi_luc IS NULL) = (thu_hoi_ly_do IS NULL)))""",
    "CREATE UNIQUE INDEX quyen_du_an_hien_hanh_uq ON m4.quyen_du_an (nguoi_dung_id, du_an_id, vai) WHERE thu_hoi_luc IS NULL",
    """CREATE OR REPLACE FUNCTION m4.quyen_du_an_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_QUYEN_CHI_QUAN_TRI: phạm vi dự án chỉ do quản trị (chủ CSDL) cấu hình' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'M4_QUYEN_BAT_BIEN: thu hồi bằng dấu thu hồi, không xóa' USING ERRCODE = 'P0001';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.thu_hoi_luc IS NOT NULL THEN
                    RAISE EXCEPTION 'M4_QUYEN_BAT_BIEN: không chèn quyền đã thu hồi' USING ERRCODE = 'P0001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.thu_hoi_luc IS NOT NULL OR NEW.thu_hoi_luc IS NULL OR coalesce(btrim(NEW.thu_hoi_ly_do), '') = ''
               OR ROW(NEW.id, NEW.nguoi_dung_id, NEW.phap_nhan_id, NEW.du_an_id, NEW.vai, NEW.tao_luc)
                  IS DISTINCT FROM ROW(OLD.id, OLD.nguoi_dung_id, OLD.phap_nhan_id, OLD.du_an_id, OLD.vai, OLD.tao_luc) THEN
                RAISE EXCEPTION 'M4_QUYEN_BAT_BIEN: chỉ ghi dấu thu hồi một lần, không sửa phạm vi' USING ERRCODE = 'P0001';
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER quyen_du_an_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.quyen_du_an FOR EACH ROW EXECUTE FUNCTION m4.quyen_du_an_kiem()",
    """CREATE OR REPLACE FUNCTION m4.thu_hoi_quyen_du_an(p_id uuid, p_boi text, p_ly_do text) RETURNS void
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            IF NOT master.la_chu_bang('m4.quyen_du_an'::regclass) THEN
                RAISE EXCEPTION 'M4_QUYEN_CHI_QUAN_TRI: chỉ quản trị thu hồi phạm vi dự án' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.quyen_du_an SET thu_hoi_luc = now(), thu_hoi_boi = p_boi, thu_hoi_ly_do = p_ly_do WHERE id = p_id AND thu_hoi_luc IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_QUYEN_KHONG_THAY: không có quyền hiện hành với id này' USING ERRCODE = 'P0001';
            END IF;
        END $$""",
    # quyền M4 của phiên: danh tính ID + login hoạt động, module M4 hiện hành trên PN, vai dự án CHƯA thu hồi; SOAN cần vai trò DU_AN
    """CREATE OR REPLACE FUNCTION master.m4_duoc(p_du_an uuid, p_quyen text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND q.du_an_id = p_du_an AND q.thu_hoi_luc IS NULL AND master.ktt_duoc(q.phap_nhan_id, 'M4')
                         AND CASE p_quyen WHEN 'XEM' THEN q.vai IN ('PHU_TRACH','XEM')
                                          WHEN 'SOAN' THEN q.vai = 'PHU_TRACH' AND n.vai_tro = 'DU_AN'
                                          WHEN 'REVIEW' THEN q.vai = 'REVIEW'
                                          ELSE false END)
        $$""",
    # --- master HĐ: discriminator chủ sở hữu M4 (hàng cũ NULL → giữ CRM/M9 như trước)
    "ALTER TABLE master.hop_dong ADD COLUMN module_chu text",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_module_chu_m4 CHECK (module_chu IS NULL OR (module_chu = 'M4' AND loai = 'XAY_DUNG' AND du_an_id IS NOT NULL))",
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_id_du_an_uq UNIQUE (id, du_an_id)",
    # M4-01B5: khóa đích cho FK (phap_nhan_id, hop_dong_id) của m4.ho_so_hop_dong — chuỗi neutral COMMON 1–16 chưa có UNIQUE này (chỉ nhánh M13
    # legacy đầy đủ có hop_dong_pn_id_uq). Tên riêng M4 để không trùng tên legacy; đặt TRƯỚC mọi bảng có FK tham chiếu cặp cột này.
    "ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_m4_pn_id_uq UNIQUE (phap_nhan_id, id)",
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
    """CREATE POLICY hop_dong_m4_rang_buoc ON master.hop_dong AS RESTRICTIVE TO PUBLIC
        USING (module_chu IS DISTINCT FROM 'M4' OR master.m4_duoc(du_an_id, 'XEM') OR master.m4_duoc(du_an_id, 'REVIEW'))
        WITH CHECK (module_chu IS DISTINCT FROM 'M4')""",
    # --- tệp nguồn: hàng chỉ do đường tin cậy ghi SAU khi máy chủ nhận bytes thật (hash/độ dài/media/tên do máy chủ tính & kiểm)
    f"""CREATE TABLE m4.tep (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        vai_tro_tai_lieu text NOT NULL CHECK (vai_tro_tai_lieu IN ('HOP_DONG','PHU_LUC','BOQ','HO_SO_DOT')),
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        byte_length bigint NOT NULL CHECK (byte_length > 0),
        media_type text NOT NULL CHECK (media_type IN {_MEDIA_SQL}),
        ten_goc text NOT NULL CHECK ({_tep_ten_hop_le('ten_goc')}),
        object_key text NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        CHECK (object_key = 'm4-raw/' || raw_sha256),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        UNIQUE (du_an_id, vai_tro_tai_lieu, raw_sha256),
        UNIQUE (id, du_an_id),
        UNIQUE (id, du_an_id, raw_sha256))""",
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
    # lineage: lần trích gắn ĐÚNG tệp + hash đã nhận (FK ba cột), không nhận hash/status khai từ caller thường
    f"""CREATE TABLE m4.trich_xuat (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        catalog_sha256 text NOT NULL CHECK (catalog_sha256 {_HEX}),
        engine text NOT NULL CHECK (length(engine) BETWEEN 1 AND 200),
        che_do text NOT NULL CHECK (che_do IN ('QUY_TAC_KHONG_AI','AI_LOCAL','AI_GIA_LAP_KHAI_BAO')),
        trang_thai text NOT NULL CHECK (trang_thai IN ('XONG','KHONG_HO_TRO','LOI')),
        ly_do text,
        phieu jsonb NOT NULL,
        ket_qua jsonb NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id, raw_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
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
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        trich_xuat_id uuid NOT NULL REFERENCES m4.trich_xuat(id),
        catalog_sha256 text NOT NULL CHECK (catalog_sha256 {_HEX}),
        tham_so_digest text NOT NULL CHECK (tham_so_digest {_HEX}),
        ly_do text,
        xac_nhan_boi text NOT NULL,
        xac_nhan_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        xac_nhan_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (tep_id, du_an_id, raw_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
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
    # BOQ (B5): lỗi đọc/map/căn cứ CHẶN (loi_chan) tách khỏi phát hiện nghiệp vụ (phat_hien, vd KL×ĐG ≠ thành tiền) — phát hiện KHÔNG chặn nộp
    f"""CREATE TABLE m4.boq (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        hop_dong_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        lan integer NOT NULL CHECK (lan >= 1),
        phu_luc_id uuid,
        tep_id uuid NOT NULL,
        raw_sha256 text NOT NULL CHECK (raw_sha256 {_HEX}),
        sheet text NOT NULL CHECK (length(sheet) BETWEEN 1 AND 100),
        hang_tieu_de integer NOT NULL CHECK (hang_tieu_de >= 1),
        cot jsonb NOT NULL,
        so_dong integer NOT NULL CHECK (so_dong >= 0),
        loi_chan jsonb NOT NULL CHECK (jsonb_typeof(loi_chan) = 'array'),
        phat_hien jsonb NOT NULL CHECK (jsonb_typeof(phat_hien) = 'array'),
        trang_thai text NOT NULL CHECK (trang_thai IN ('DA_MAP','CO_LOI')),
        bo_doc text NOT NULL,
        tao_boi text NOT NULL,
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (phu_luc_id, hop_dong_id) REFERENCES m4.phu_luc (id, hop_dong_id),
        FOREIGN KEY (tep_id, du_an_id, raw_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
        CHECK ((trang_thai = 'DA_MAP') = (so_dong > 0 AND jsonb_array_length(loi_chan) = 0)),
        UNIQUE (hop_dong_id, lan))""",
    # dòng BOQ: số typed (kl/don_gia/thanh_tien NULL khi ô trống — không biến trống thành 0) + o_goc giữ ô gốc và loại ô (TRONG/SO/CHU)
    """CREATE TABLE m4.boq_dong (
        boq_id uuid NOT NULL REFERENCES m4.boq(id),
        du_an_id uuid NOT NULL,
        dong integer NOT NULL CHECK (dong >= 1),
        ma_hm text NOT NULL CHECK (length(ma_hm) BETWEEN 1 AND 500),
        thao_tac text NOT NULL CHECK (thao_tac IN ('GOC','THEM','THAY')),
        stt text, nhom text, ten text NOT NULL, dvt text NOT NULL,
        kl text, don_gia text, thanh_tien text, ma_rieng text,
        o_goc jsonb NOT NULL CHECK (jsonb_typeof(o_goc) = 'object'),
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
        digest text NOT NULL CHECK (digest {_HEX}),
        nop_boi text NOT NULL,
        nop_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        nop_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id))""",
    # biên nhận (B2): ghi MỘT lần trong cùng giao dịch của lệnh hợp lệ, gồm yêu cầu gốc bất biến + kết quả do lệnh dẫn xuất; chỉ ghi thêm
    f"""CREATE TABLE m4.bien_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nguoi_dung_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        du_an_id uuid NOT NULL,
        hanh_dong text NOT NULL CHECK (hanh_dong ~ '^[A-Z_]{{1,40}}$'),
        khoa text NOT NULL CHECK (khoa ~ '^[A-Za-z0-9_.:-]{{1,200}}$'),
        yeu_cau jsonb NOT NULL CHECK (jsonb_typeof(yeu_cau) = 'object'),
        body_sha256 text NOT NULL CHECK (body_sha256 {_HEX}),
        ket_qua jsonb NOT NULL CHECK (jsonb_typeof(ket_qua) = 'object'),
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
      for t in ("ho_so_hop_dong", "tham_so", "phu_luc", "dot")),
    *(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t} FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()"
      for t in ("tep", "trich_xuat", "tham_so_lich_su", "xac_nhan_tham_so", "boq", "boq_dong", "dot_tep", "nop", "bien_nhan", "nhat_ky")),
    # --- nội bộ
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
    # tra biên nhận dưới khóa tư vấn theo (người, khóa): cùng hành động + dự án + yêu cầu gốc → kết quả cũ; khác → từ chối; chưa có → NULL
    """CREATE OR REPLACE FUNCTION m4._bn_tra(p_ai uuid, p_khoa text, p_hanh_dong text, p_du_an uuid, p_yc jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE b record;
        BEGIN
            IF p_khoa IS NULL OR p_khoa !~ '^[A-Za-z0-9_.:-]{1,200}$' THEN
                RAISE EXCEPTION 'M4_KHOA_THAO_TAC: thiếu hoặc sai khóa thao tác' USING ERRCODE = 'P0001';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:bien_nhan:' || p_ai::text || ':' || p_khoa, 0));
            SELECT * INTO b FROM m4.bien_nhan WHERE nguoi_dung_id = p_ai AND khoa = p_khoa;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            IF (b.hanh_dong, b.du_an_id, b.yeu_cau) IS DISTINCT FROM (p_hanh_dong, p_du_an, p_yc) THEN
                RAISE EXCEPTION 'M4_IDEMPOTENCY_KHAC: khóa thao tác đã dùng cho yêu cầu khác' USING ERRCODE = 'P0001';
            END IF;
            RETURN b.ket_qua;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4._bn_ghi(p_ai uuid, p_khoa text, p_hanh_dong text, p_du_an uuid, p_yc jsonb, p_kq jsonb) RETURNS void
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        BEGIN
            INSERT INTO m4.bien_nhan (nguoi_dung_id, du_an_id, hanh_dong, khoa, yeu_cau, body_sha256, ket_qua)
                VALUES (p_ai, p_du_an, p_hanh_dong, p_khoa, p_yc, encode(sha256(convert_to(p_hanh_dong || chr(31) || p_yc::text, 'UTF8')), 'hex'), p_kq);
        END $$""",
    # đọc biên nhận của chính phiên trước khi làm việc tốn kém: quyền dự án HIỆN HÀNH kiểm trước (thu hồi → chặn replay)
    """CREATE OR REPLACE FUNCTION m4.tra_bien_nhan(p_khoa text) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE aid uuid := m4.ai_id(); b record;
        BEGIN
            SELECT * INTO b FROM m4.bien_nhan WHERE nguoi_dung_id = aid AND khoa = p_khoa;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;""" + _SOAN.format(d="b.du_an_id") + """
            RETURN jsonb_build_object('hanh_dong', b.hanh_dong, 'yeu_cau', b.yeu_cau, 'ket_qua', b.ket_qua);
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
    # M4-01B2 (sửa 5): bit "đã nộp" chỉ trả cho phiên có quyền HIỆN HÀNH (XEM/REVIEW) trên đúng dự án của tệp; ngoài phạm vi/sau thu hồi → false
    # (không lộ trạng thái UUID lạ). Giữ nguyên ý nghĩa policy tep_web cho người xem/review hợp lệ.
    """CREATE OR REPLACE FUNCTION m4.tep_da_nop(p_tep uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.tep f JOIN m4.dot_tep k ON k.tep_id = f.id AND k.du_an_id = f.du_an_id
                       JOIN m4.dot d ON d.id = k.dot_id AND d.du_an_id = f.du_an_id
                       WHERE f.id = p_tep AND d.trang_thai = 'DA_NOP'
                         AND (master.m4_duoc(f.du_an_id, 'XEM') OR master.m4_duoc(f.du_an_id, 'REVIEW')))
        $$""",
    # ======================================================================= lệnh người dùng thường (app_web)
    """CREATE OR REPLACE FUNCTION m4.tao_hop_dong(p_khoa text, p_du_an uuid, p_so_hd text, p_ten text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ d record; hd uuid; c record;
        BEGIN
            yc := jsonb_build_object('du_an_id', p_du_an, 'so_hop_dong', p_so_hd, 'ten', p_ten);""" + _SOAN.format(d="p_du_an")
    + _REPLAY.format(a="TAO_HOP_DONG", d="p_du_an") + """
            IF p_so_hd IS NULL OR p_so_hd !~ '^[^[:cntrl:]]{1,100}$' OR btrim(p_so_hd) <> p_so_hd OR p_ten IS NULL OR length(p_ten) NOT BETWEEN 1 AND 300 THEN
                RAISE EXCEPTION 'M4_HOP_DONG_SAI: số hợp đồng (1–100 ký tự, không khoảng trắng đầu/cuối) và tên là bắt buộc' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            PERFORM pg_advisory_xact_lock(hashtextextended('m4:hop_dong:' || d.phap_nhan_id::text || ':' || p_so_hd, 0));
            SELECT h.id, h.module_chu, h.du_an_id INTO c FROM master.hop_dong h WHERE h.phap_nhan_id = d.phap_nhan_id AND h.loai = 'XAY_DUNG' AND h.so_hop_dong = p_so_hd;
            IF c.id IS NOT NULL THEN
                IF c.module_chu = 'M4' AND c.du_an_id = p_du_an THEN
                    RAISE EXCEPTION 'M4_HOP_DONG_DA_CO: hợp đồng % đã có trong dự án — dùng lại hồ sơ hiện có cho đợt sau', p_so_hd USING ERRCODE = 'P0001';
                END IF;
                RAISE EXCEPTION 'M4_HOP_DONG_DA_CO_NOI_KHAC: số hợp đồng đã có ở dự án/module khác của pháp nhân — không tạo master song song' USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, du_an_id, module_chu)
                VALUES (d.phap_nhan_id, 'XAY_DUNG', 'M4:' || d.ma_junsky || ':' || p_so_hd, p_so_hd, p_du_an, 'M4') RETURNING id INTO hd;
            INSERT INTO m4.ho_so_hop_dong (hop_dong_id, phap_nhan_id, du_an_id, ten, tao_boi) VALUES (hd, d.phap_nhan_id, p_du_an, p_ten, ai);
            """ + _NK.format(d="p_du_an", hd="hd", dot="NULL", a="TAO_HOP_DONG", ct="jsonb_build_object('so_hop_dong', p_so_hd)") + """
            kq := jsonb_build_object('hop_dong_id', hd);""" + _KET.format(a="TAO_HOP_DONG", d="p_du_an") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.gan_tep_hop_dong(p_khoa text, p_hd uuid, p_rev integer, p_tep uuid) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; t record; moi integer;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'tep_id', p_tep);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="GAN_TEP_HOP_DONG", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            SELECT * INTO t FROM m4.tep WHERE id = p_tep AND du_an_id = h.du_an_id;
            IF NOT FOUND OR t.vai_tro_tai_lieu <> 'HOP_DONG' THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp hợp đồng đã tải lên đúng dự án' USING ERRCODE = 'P0001';
            END IF;
            IF h.tep_hop_dong_id = p_tep THEN
                RAISE EXCEPTION 'M4_KHONG_DOI: tệp hợp đồng này đang là căn cứ hiện hành' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.ho_so_hop_dong SET tep_hop_dong_id = p_tep WHERE hop_dong_id = h.hop_dong_id;""" + _TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="GAN_TEP_HOP_DONG",
                             ct="jsonb_build_object('tep_cu', h.tep_hop_dong_id, 'tep_moi', p_tep, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi);""" + _KET.format(a="GAN_TEP_HOP_DONG", d="h.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.xac_nhan_tham_so(p_khoa text, p_hd uuid, p_rev integer, p_catalog text, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; t record; x uuid; con text; n integer;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'ly_do', p_ly_do);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="XAC_NHAN_THAM_SO", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            IF h.tep_hop_dong_id IS NULL THEN
                RAISE EXCEPTION 'M4_THIEU_HOP_DONG: chưa có tệp hợp đồng nguồn' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO t FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id ORDER BY lan DESC LIMIT 1;
            IF NOT FOUND OR t.tep_id <> h.tep_hop_dong_id OR t.trang_thai <> 'XONG' THEN
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
                        p_ly_do, ai, aid) RETURNING id INTO x;
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="XAC_NHAN_THAM_SO",
                             ct="jsonb_build_object('xac_nhan_id', x, 'rev_tham_so', h.rev_tham_so)") + """
            kq := jsonb_build_object('xac_nhan_id', x, 'rev_tham_so', h.rev_tham_so);""" + _KET.format(a="XAC_NHAN_THAM_SO", d="h.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.khai_phu_luc(p_khoa text, p_hd uuid, p_rev integer, p_khai text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; moi integer;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'khai', p_khai);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="KHAI_PHU_LUC", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            IF p_khai IS NULL OR p_khai NOT IN ('KHONG_CO','CO_CHUA_DU','CO_DU') THEN
                RAISE EXCEPTION 'M4_KHAI_PHU_LUC_SAI: chỉ Không có / Có nhưng chưa đủ / Có và đã cung cấp đủ' USING ERRCODE = 'P0001';
            END IF;
            IF p_khai = 'KHONG_CO' AND EXISTS (SELECT 1 FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai <> 'DA_HUY') THEN
                RAISE EXCEPTION 'M4_KHAI_PHU_LUC_MAU_THUAN: đang có phụ lục chưa hủy — không khai Không có' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.ho_so_hop_dong SET trang_thai_pl = p_khai WHERE hop_dong_id = h.hop_dong_id;""" + _TANG.format(ts="") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="KHAI_PHU_LUC", ct="jsonb_build_object('khai', p_khai, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi);""" + _KET.format(a="KHAI_PHU_LUC", d="h.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.them_phu_luc(p_khoa text, p_hd uuid, p_rev integer, p_so_pl text, p_ngay_ky date, p_ngay_hl date, p_trang_thai text,
                                                   p_doi_boq boolean, p_noi_dung text, p_tep uuid) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; moi integer; pl uuid;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'so_pl', p_so_pl, 'ngay_ky', p_ngay_ky, 'ngay_hieu_luc', p_ngay_hl,
                                     'trang_thai', p_trang_thai, 'doi_boq', p_doi_boq, 'noi_dung', p_noi_dung, 'tep_id', p_tep);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="THEM_PHU_LUC", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            IF p_trang_thai IS NULL OR p_trang_thai NOT IN ('DA_KY','DU_THAO') OR p_doi_boq IS NULL THEN
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
                VALUES (h.hop_dong_id, h.du_an_id, p_so_pl, p_ngay_ky, p_ngay_hl, p_trang_thai, p_doi_boq, p_noi_dung, p_tep, ai) RETURNING id INTO pl;"""
    + _TANG.format(ts="") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="THEM_PHU_LUC", ct="jsonb_build_object('phu_luc_id', pl, 'revision', moi)") + """
            kq := jsonb_build_object('phu_luc_id', pl, 'revision', moi);""" + _KET.format(a="THEM_PHU_LUC", d="h.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.huy_phu_luc(p_khoa text, p_pl uuid, p_rev integer, p_ly_do text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; p record; moi integer;
        BEGIN
            yc := jsonb_build_object('phu_luc_id', p_pl, 'revision', p_rev, 'ly_do', p_ly_do);
            SELECT * INTO p FROM m4.phu_luc WHERE id = p_pl;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_PHU_LUC: không thấy phụ lục' USING ERRCODE = 'P0001';
            END IF;""" + _HO_SO.format(hd="p.hop_dong_id") + _REPLAY.format(a="HUY_PHU_LUC", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            SELECT * INTO p FROM m4.phu_luc WHERE id = p_pl FOR UPDATE;
            IF p.trang_thai = 'DA_HUY' OR coalesce(btrim(p_ly_do), '') = '' THEN
                RAISE EXCEPTION 'M4_HUY_PHU_LUC_SAI: phụ lục đã hủy hoặc thiếu lý do' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.phu_luc SET trang_thai = 'DA_HUY', huy_ly_do = p_ly_do, huy_boi = ai, huy_luc = now() WHERE id = p_pl;""" + _TANG.format(ts="") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="HUY_PHU_LUC", ct="jsonb_build_object('phu_luc_id', p_pl, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi);""" + _KET.format(a="HUY_PHU_LUC", d="h.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.tao_dot(p_khoa text, p_hd uuid, p_so_dot integer, p_ngay date) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; d uuid;
        BEGIN
            yc := jsonb_build_object('hop_dong_id', p_hd, 'so_dot', p_so_dot, 'ngay_nghiem_thu', p_ngay);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="TAO_DOT", d="h.du_an_id") + """
            IF p_so_dot IS NULL OR p_so_dot NOT BETWEEN 1 AND 999 THEN
                RAISE EXCEPTION 'M4_DOT_SAI: số đợt 1–999' USING ERRCODE = 'P0001';
            END IF;
            IF EXISTS (SELECT 1 FROM m4.dot WHERE hop_dong_id = p_hd AND so_dot = p_so_dot) THEN
                RAISE EXCEPTION 'M4_DOT_DA_CO: đợt % đã có trên hợp đồng này', p_so_dot USING ERRCODE = 'P0001';
            END IF;
            INSERT INTO m4.dot (hop_dong_id, du_an_id, so_dot, ngay_nghiem_thu, tao_boi) VALUES (p_hd, h.du_an_id, p_so_dot, p_ngay, ai) RETURNING id INTO d;
            """ + _NK.format(d="h.du_an_id", hd="p_hd", dot="d", a="TAO_DOT", ct="jsonb_build_object('so_dot', p_so_dot)") + """
            kq := jsonb_build_object('dot_id', d);""" + _KET.format(a="TAO_DOT", d="h.du_an_id") + """
        END $$""",
    # khóa HĐ → đợt + quyền hiện hành; trạng thái/revision kiểm ở lệnh SAU khi tra biên nhận
    """CREATE OR REPLACE FUNCTION m4._khoa_dot(p_dot uuid) RETURNS m4.dot
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d m4.dot; h record;
        BEGIN
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_DOT: không thấy đợt' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id FOR UPDATE;
            SELECT * INTO d FROM m4.dot WHERE id = p_dot FOR UPDATE;""" + _SOAN.format(d="d.du_an_id") + """
            RETURN d;
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.sua_dot(p_khoa text, p_dot uuid, p_rev integer, p_ngay date) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ d m4.dot; moi integer;
        BEGIN
            yc := jsonb_build_object('dot_id', p_dot, 'revision', p_rev, 'ngay_nghiem_thu', p_ngay);
            d := m4._khoa_dot(p_dot);""" + _REPLAY.format(a="SUA_DOT", d="d.du_an_id") + """
            IF d.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'M4_DOT_DA_NOP: đợt đã nộp chính thức — không sửa (bổ sung là gói sau)' USING ERRCODE = 'P0001';
            END IF;
            IF p_rev IS NULL OR d.revision <> p_rev THEN
                RAISE EXCEPTION 'M4_REVISION_CU: đợt đã đổi (revision hiện tại %) — tải lại', d.revision USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.dot SET ngay_nghiem_thu = p_ngay, revision = revision + 1, cap_nhat_luc = now() WHERE id = p_dot RETURNING revision INTO moi;
            """ + _NK.format(d="d.du_an_id", hd="d.hop_dong_id", dot="p_dot", a="SUA_DOT", ct="jsonb_build_object('ngay_nghiem_thu', p_ngay, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi);""" + _KET.format(a="SUA_DOT", d="d.du_an_id") + """
        END $$""",
    """CREATE OR REPLACE FUNCTION m4.gan_tep_dot(p_khoa text, p_dot uuid, p_rev integer, p_tep uuid, p_muc text) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ d m4.dot; moi integer;
        BEGIN
            yc := jsonb_build_object('dot_id', p_dot, 'revision', p_rev, 'tep_id', p_tep, 'muc', p_muc);
            d := m4._khoa_dot(p_dot);""" + _REPLAY.format(a="GAN_TEP_DOT", d="d.du_an_id") + """
            IF d.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'M4_DOT_DA_NOP: đợt đã nộp chính thức — không sửa (bổ sung là gói sau)' USING ERRCODE = 'P0001';
            END IF;
            IF p_rev IS NULL OR d.revision <> p_rev THEN
                RAISE EXCEPTION 'M4_REVISION_CU: đợt đã đổi (revision hiện tại %) — tải lại', d.revision USING ERRCODE = 'P0001';
            END IF;
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
            """ + _NK.format(d="d.du_an_id", hd="d.hop_dong_id", dot="p_dot", a="GAN_TEP_DOT", ct="jsonb_build_object('tep_id', p_tep, 'muc', p_muc, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi);""" + _KET.format(a="GAN_TEP_DOT", d="d.du_an_id") + """
        END $$""",
    # --- preflight backend (giữ M4-01): phát hiện BOQ không chặn; lỗi đọc/map/căn cứ chặn
    """CREATE OR REPLACE FUNCTION m4.thieu(p_dot uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d record; h record; t record; x record; b record; p record; c record; ra jsonb := '[]'::jsonb;
        BEGIN
            SELECT * INTO d FROM m4.dot WHERE id = p_dot;
            IF NOT FOUND OR NOT (master.m4_duoc(d.du_an_id, 'XEM') OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')) THEN
                RAISE EXCEPTION 'M4_KHONG_THAY_DOT: không thấy đợt' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO h FROM m4.ho_so_hop_dong WHERE hop_dong_id = d.hop_dong_id;
            IF h.tep_hop_dong_id IS NULL THEN
                ra := ra || jsonb_build_object('ma', 'HD_CHUA_CO_TEP', 'nhom', 'HOP_DONG', 'noi_dung', 'Chưa tải tệp hợp đồng nguồn');
            ELSE
                SELECT * INTO t FROM m4.trich_xuat WHERE hop_dong_id = h.hop_dong_id ORDER BY lan DESC LIMIT 1;
                IF NOT FOUND THEN
                    ra := ra || jsonb_build_object('ma', 'HD_CHUA_TRICH', 'nhom', 'HOP_DONG', 'noi_dung', 'Chưa chạy trích tham số từ tệp hợp đồng hiện hành');
                ELSIF t.tep_id <> h.tep_hop_dong_id THEN
                    ra := ra || jsonb_build_object('ma', 'HD_TRICH_KHAC_TEP', 'nhom', 'HOP_DONG', 'noi_dung', 'Lần trích gần nhất thuộc tệp hợp đồng cũ — trích lại');
                ELSIF t.trang_thai <> 'XONG' THEN
                    ra := ra || jsonb_build_object('ma', 'HD_TRICH_CHUA_XONG', 'nhom', 'HOP_DONG', 'noi_dung', coalesce(t.ly_do, 'Lần trích chưa xong'));
                ELSE
                    SELECT * INTO x FROM m4.xac_nhan_tham_so WHERE hop_dong_id = h.hop_dong_id ORDER BY rev_tham_so DESC LIMIT 1;
                    IF NOT FOUND THEN
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
            IF NOT FOUND THEN
                ra := ra || jsonb_build_object('ma', 'BOQ_CHUA_NHAP', 'nhom', 'BOQ', 'noi_dung', 'Chưa nhập BOQ hợp đồng (đọc + map cột)');
            ELSIF b.trang_thai <> 'DA_MAP' THEN
                ra := ra || jsonb_build_object('ma', 'BOQ_CO_LOI', 'nhom', 'BOQ', 'noi_dung', 'BOQ lần nhập gần nhất còn lỗi đọc/map/căn cứ', 'boq_id', b.id);
            END IF;
            FOR p IN SELECT * FROM m4.phu_luc WHERE hop_dong_id = h.hop_dong_id AND trang_thai = 'DA_KY' AND doi_boq
                       AND (d.ngay_nghiem_thu IS NULL OR ngay_hieu_luc <= d.ngay_nghiem_thu) ORDER BY ngay_hieu_luc, so_pl LOOP
                SELECT * INTO b FROM m4.boq WHERE phu_luc_id = p.id ORDER BY lan DESC LIMIT 1;
                IF NOT FOUND OR b.trang_thai <> 'DA_MAP' THEN
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
    """CREATE OR REPLACE FUNCTION m4.nop(p_khoa text, p_dot uuid, p_rev_hd integer, p_rev_dot integer) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ d m4.dot; h record; t record; x record; con jsonb; s jsonb; n uuid; dg text;
        BEGIN
            yc := jsonb_build_object('dot_id', p_dot, 'revision_ho_so', p_rev_hd, 'revision_dot', p_rev_dot);
            d := m4._khoa_dot(p_dot);""" + _REPLAY.format(a="NOP", d="d.du_an_id") + """
            IF d.trang_thai <> 'NHAP' THEN
                RAISE EXCEPTION 'M4_DOT_DA_NOP: đợt đã nộp chính thức' USING ERRCODE = 'P0001';
            END IF;
            IF p_rev_dot IS NULL OR d.revision <> p_rev_dot THEN
                RAISE EXCEPTION 'M4_REVISION_CU: đợt đã đổi (revision hiện tại %) — tải lại', d.revision USING ERRCODE = 'P0001';
            END IF;
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
                'boq', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', q.id, 'phu_luc_id', q.phu_luc_id, 'so_dong', q.so_dong,
                                                                     'so_phat_hien', jsonb_array_length(q.phat_hien)) ORDER BY q.lan), '[]'::jsonb)
                        FROM m4.boq q WHERE q.hop_dong_id = h.hop_dong_id AND q.trang_thai = 'DA_MAP'
                          AND q.lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = q.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM q.phu_luc_id)),
                'dot', jsonb_build_object('id', d.id, 'so_dot', d.so_dot, 'ngay_nghiem_thu', d.ngay_nghiem_thu, 'revision', d.revision),
                'tai_lieu', (SELECT coalesce(jsonb_agg(jsonb_build_object('muc', k.muc, 'tep_id', k.tep_id, 'raw_sha256', f.raw_sha256)
                                                       ORDER BY k.muc, f.raw_sha256), '[]'::jsonb)
                             FROM m4.dot_tep k JOIN m4.tep f ON f.id = k.tep_id WHERE k.dot_id = d.id));
            dg := encode(sha256(convert_to(s::text, 'UTF8')), 'hex');
            INSERT INTO m4.nop (dot_id, hop_dong_id, du_an_id, revision_ho_so, revision_dot, snapshot, digest, nop_boi, nop_boi_id)
                VALUES (d.id, h.hop_dong_id, h.du_an_id, h.revision, d.revision, s, dg, ai, aid) RETURNING id INTO n;
            UPDATE m4.dot SET trang_thai = 'DA_NOP', cap_nhat_luc = now() WHERE id = d.id;
            """ + _NK.format(d="d.du_an_id", hd="h.hop_dong_id", dot="d.id", a="NOP", ct="jsonb_build_object('nop_id', n)") + """
            kq := jsonb_build_object('nop_id', n, 'digest', dg);""" + _KET.format(a="NOP", d="d.du_an_id") + """
        END $$""",
    # ======================================================================= đường ghi nguồn tin cậy (SECURITY INVOKER, chỉ kết nối chủ bảng)
    # tệp: máy chủ đã nhận bytes, tính SHA/độ dài, kiểm tên/đuôi/chữ ký/media, ghi m4-raw/<sha> bất biến TRƯỚC khi gọi; nhân viên của phiên phải có SOAN
    """CREATE OR REPLACE FUNCTION m4.ghi_tep(p_khoa text, p_du_an uuid, p_vai text, p_sha text, p_len bigint, p_media text, p_ten text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ d record; t uuid; moi boolean := false;
        BEGIN""" + _TIN_CAY + """
            yc := jsonb_build_object('du_an_id', p_du_an, 'vai_tro', p_vai, 'ten', p_ten, 'media_type', p_media, 'sha256', p_sha, 'byte_length', p_len);"""
    + _SOAN.format(d="p_du_an") + _REPLAY.format(a="TAI_TEP", d="p_du_an") + """
            SELECT * INTO d FROM master.du_an WHERE id = p_du_an;
            INSERT INTO m4.tep (phap_nhan_id, du_an_id, vai_tro_tai_lieu, raw_sha256, byte_length, media_type, ten_goc, object_key, tao_boi)
                VALUES (d.phap_nhan_id, p_du_an, p_vai, p_sha, p_len, p_media, p_ten, 'm4-raw/' || p_sha, ai)
                ON CONFLICT (du_an_id, vai_tro_tai_lieu, raw_sha256) DO NOTHING RETURNING id INTO t;
            IF t IS NULL THEN
                SELECT id INTO t FROM m4.tep WHERE du_an_id = p_du_an AND vai_tro_tai_lieu = p_vai AND raw_sha256 = p_sha AND byte_length = p_len;
                IF t IS NULL THEN
                    RAISE EXCEPTION 'M4_TEP_XUNG_DOT: cùng hash nhưng độ dài khác' USING ERRCODE = 'P0001';
                END IF;
            ELSE
                moi := true;
                """ + _NK.format(d="p_du_an", hd="NULL", dot="NULL", a="TAI_TEP", ct="jsonb_build_object('tep_id', t, 'vai', p_vai, 'sha', p_sha)") + """
            END IF;
            kq := jsonb_build_object('tep_id', t, 'sha256', p_sha, 'byte_length', p_len, 'hang_moi', moi);""" + _KET.format(a="TAI_TEP", d="p_du_an") + """
        END $$""",
    # kết quả trích: worker đã đọc ĐÚNG bytes của tệp hiện hành (p_raw_sha phải khớp tệp đã nhận), chạy lõi nguồn thật; đủ 37 mã
    """CREATE OR REPLACE FUNCTION m4.ghi_trich_xuat(p_khoa text, p_hd uuid, p_rev integer, p_tep uuid, p_raw_sha text, p_catalog text, p_engine text,
                                                     p_che_do text, p_trang_thai text, p_ly_do text, p_phieu jsonb, p_ket_qua jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; t record; moi integer; tx uuid; n integer; r record; truoc jsonb;
        BEGIN""" + _TIN_CAY + """
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="TRICH", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            IF h.tep_hop_dong_id IS DISTINCT FROM p_tep THEN
                RAISE EXCEPTION 'M4_TRICH_KHAC_TEP: chỉ trích đúng tệp hợp đồng hiện hành' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO t FROM m4.tep WHERE id = p_tep;
            IF t.raw_sha256 IS DISTINCT FROM p_raw_sha THEN
                RAISE EXCEPTION 'M4_TRICH_HASH_KHAC: bytes đã xử lý không phải tệp đã nhận' USING ERRCODE = 'P0001';
            END IF;
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
                    SELECT to_jsonb(s) INTO truoc FROM m4.tham_so s WHERE s.hop_dong_id = h.hop_dong_id AND s.ma = r.ma;
                    INSERT INTO m4.tham_so (hop_dong_id, ma, du_an_id, trang_thai, gia_tri, don_vi, dieu_khoan, trich_dan, kiem_tra, ly_do, vi_tri, nguon,
                                            gia_tri_may, trich_xuat_id, cap_nhat_boi)
                        VALUES (h.hop_dong_id, r.ma, h.du_an_id, r.trang_thai, r.gia_tri, r.don_vi, r.dieu_khoan, r.trich_dan, r.kiem_tra, r.ly_do, r.vi_tri,
                                r.nguon, r.gia_tri, tx, ai)
                        ON CONFLICT (hop_dong_id, ma) DO UPDATE SET trang_thai = EXCLUDED.trang_thai, gia_tri = EXCLUDED.gia_tri, don_vi = EXCLUDED.don_vi,
                            dieu_khoan = EXCLUDED.dieu_khoan, trich_dan = EXCLUDED.trich_dan, kiem_tra = EXCLUDED.kiem_tra, ly_do = EXCLUDED.ly_do,
                            vi_tri = EXCLUDED.vi_tri, nguon = EXCLUDED.nguon, gia_tri_may = EXCLUDED.gia_tri_may, trich_xuat_id = EXCLUDED.trich_xuat_id,
                            cap_nhat_boi = EXCLUDED.cap_nhat_boi, cap_nhat_luc = now();
                    INSERT INTO m4.tham_so_lich_su (hop_dong_id, du_an_id, ma, rev_tham_so, truoc, sau, ly_do, boi)
                        VALUES (h.hop_dong_id, h.du_an_id, r.ma, h.rev_tham_so + 1, truoc, to_jsonb(r), 'TRICH_XUAT ' || tx::text, ai);
                END LOOP;""" + _TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            ELSE""" + _TANG.format(ts="") + """
            END IF;
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="TRICH_XUAT",
                             ct="jsonb_build_object('trich_xuat_id', tx, 'trang_thai', p_trang_thai, 'che_do', p_che_do, 'revision', moi)") + """
            kq := jsonb_build_object('trich_xuat_id', tx, 'trang_thai', p_trang_thai, 'che_do', p_che_do, 'ly_do', p_ly_do, 'revision', moi);"""
    + _KET.format(a="TRICH", d="h.du_an_id") + """
        END $$""",
    # sửa tham số: kết quả kiểm trích dẫn (p_kiem_tra) do máy chủ đối chiếu văn bản nguồn thật sinh ra — caller thường không gọi được hàm này
    """CREATE OR REPLACE FUNCTION m4.sua_tham_so(p_khoa text, p_hd uuid, p_rev integer, p_ma text, p_trang_thai text, p_gia_tri text, p_don_vi text,
                                                  p_dieu_khoan text, p_trich_dan text, p_ly_do text, p_kiem_tra text) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; s record; moi integer;
        BEGIN""" + _TIN_CAY + """
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'ma', p_ma, 'trang_thai', p_trang_thai, 'gia_tri', p_gia_tri,
                                     'don_vi', p_don_vi, 'dieu_khoan', p_dieu_khoan, 'trich_dan', p_trich_dan, 'ly_do', p_ly_do);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="SUA_THAM_SO", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            SELECT * INTO s FROM m4.tham_so WHERE hop_dong_id = h.hop_dong_id AND ma = p_ma;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'M4_CHUA_TRICH: chưa có bộ tham số từ lần trích — chạy trích trước' USING ERRCODE = 'P0001';
            END IF;
            IF p_trang_thai IS NULL OR p_trang_thai NOT IN ('CO_GIA_TRI','KHONG_AP_DUNG','KHONG_QUY_DINH') THEN
                RAISE EXCEPTION 'M4_TRANG_THAI_THAM_SO_SAI: chỉ Có giá trị / Không áp dụng / Không quy định' USING ERRCODE = 'P0001';
            END IF;
            UPDATE m4.tham_so SET trang_thai = p_trang_thai, gia_tri = CASE WHEN p_trang_thai = 'CO_GIA_TRI' THEN p_gia_tri END, don_vi = p_don_vi,
                                  dieu_khoan = p_dieu_khoan, trich_dan = p_trich_dan, kiem_tra = p_kiem_tra, ly_do = p_ly_do, nguon = 'SUA_TAY',
                                  cap_nhat_boi = ai, cap_nhat_luc = now()
                WHERE hop_dong_id = h.hop_dong_id AND ma = p_ma;
            INSERT INTO m4.tham_so_lich_su (hop_dong_id, du_an_id, ma, rev_tham_so, truoc, sau, ly_do, boi)
                SELECT h.hop_dong_id, h.du_an_id, p_ma, h.rev_tham_so + 1, to_jsonb(s), to_jsonb(x), p_ly_do, ai FROM m4.tham_so x
                WHERE x.hop_dong_id = h.hop_dong_id AND x.ma = p_ma;""" + _TANG.format(ts=", rev_tham_so = rev_tham_so + 1") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="SUA_THAM_SO", ct="jsonb_build_object('ma', p_ma, 'revision', moi)") + """
            kq := jsonb_build_object('revision', moi, 'kiem_tra', p_kiem_tra);""" + _KET.format(a="SUA_THAM_SO", d="h.du_an_id") + """
        END $$""",
    # BOQ: worker đã đọc ĐÚNG bytes tệp BOQ (hash khớp) bằng parser nguồn, phân loại lỗi chặn/phát hiện, giữ ô gốc; DA_MAP khi có dòng và 0 lỗi chặn
    """CREATE OR REPLACE FUNCTION m4.ghi_boq(p_khoa text, p_hd uuid, p_rev integer, p_tep uuid, p_raw_sha text, p_pl uuid, p_sheet text, p_hang integer,
                                              p_cot jsonb, p_bo_doc text, p_dong jsonb, p_loi_chan jsonb, p_phat_hien jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KHAI_BAO + """ h record; moi integer; b uuid; n integer; goc text[]; tt text;
        BEGIN""" + _TIN_CAY + """
            yc := jsonb_build_object('hop_dong_id', p_hd, 'revision', p_rev, 'tep_id', p_tep, 'phu_luc_id', p_pl, 'sheet', p_sheet,
                                     'hang_tieu_de', p_hang, 'cot', p_cot);""" + _HO_SO.format(hd="p_hd")
    + _REPLAY.format(a="NHAP_BOQ", d="h.du_an_id") + _REV.format(rev="p_rev") + """
            IF NOT EXISTS (SELECT 1 FROM m4.tep WHERE id = p_tep AND du_an_id = h.du_an_id AND vai_tro_tai_lieu = 'BOQ' AND raw_sha256 = p_raw_sha) THEN
                RAISE EXCEPTION 'M4_TEP_SAI_VAI_TRO: cần tệp BOQ (.xlsx) đúng dự án và đúng bytes đã đọc' USING ERRCODE = 'P0001';
            END IF;
            IF p_pl IS NOT NULL AND NOT EXISTS (SELECT 1 FROM m4.phu_luc WHERE id = p_pl AND hop_dong_id = h.hop_dong_id AND trang_thai <> 'DA_HUY' AND doi_boq) THEN
                RAISE EXCEPTION 'M4_PHU_LUC_KHONG_DOI_BOQ: BOQ phụ lục chỉ gắn phụ lục còn hiệu lực có khai đổi BOQ' USING ERRCODE = 'P0001';
            END IF;
            IF jsonb_typeof(p_dong) <> 'array' OR jsonb_typeof(p_loi_chan) <> 'array' OR jsonb_typeof(p_phat_hien) <> 'array' THEN
                RAISE EXCEPTION 'M4_BOQ_SAI: dòng/lỗi/phát hiện BOQ phải là danh sách' USING ERRCODE = 'P0001';
            END IF;
            n := jsonb_array_length(p_dong);
            tt := CASE WHEN n > 0 AND jsonb_array_length(p_loi_chan) = 0 THEN 'DA_MAP' ELSE 'CO_LOI' END;
            INSERT INTO m4.boq (hop_dong_id, du_an_id, lan, phu_luc_id, tep_id, raw_sha256, sheet, hang_tieu_de, cot, so_dong, loi_chan, phat_hien, trang_thai,
                                bo_doc, tao_boi)
                VALUES (h.hop_dong_id, h.du_an_id, coalesce((SELECT max(lan) FROM m4.boq WHERE hop_dong_id = h.hop_dong_id), 0) + 1, p_pl, p_tep, p_raw_sha,
                        p_sheet, p_hang, p_cot, n, p_loi_chan, p_phat_hien, tt, p_bo_doc, ai)
                RETURNING id INTO b;
            IF p_pl IS NOT NULL THEN
                SELECT array_agg(d.ma_hm) INTO goc FROM m4.boq_dong d WHERE d.boq_id = (SELECT x.id FROM m4.boq x WHERE x.hop_dong_id = h.hop_dong_id
                                                                                       AND x.phu_luc_id IS NULL ORDER BY x.lan DESC LIMIT 1);
            END IF;
            INSERT INTO m4.boq_dong (boq_id, du_an_id, dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng, o_goc)
                SELECT b, h.du_an_id, x.dong, x.ma_hm, CASE WHEN p_pl IS NULL THEN 'GOC' WHEN x.ma_hm = ANY (coalesce(goc, '{}')) THEN 'THAY' ELSE 'THEM' END,
                       x.stt, x.nhom, x.ten, x.dvt, x.kl, x.don_gia, x.thanh_tien, x.ma_rieng, x.o_goc
                FROM jsonb_to_recordset(p_dong) AS x(dong integer, ma_hm text, stt text, nhom text, ten text, dvt text, kl text, don_gia text,
                                                     thanh_tien text, ma_rieng text, o_goc jsonb);""" + _TANG.format(ts="") + """
            """ + _NK.format(d="h.du_an_id", hd="h.hop_dong_id", dot="NULL", a="NHAP_BOQ", ct="jsonb_build_object('boq_id', b, 'so_dong', n, 'revision', moi)") + """
            -- M4-01B2 (sửa 6): FINAL bất biến gồm ĐỦ mảng lỗi chặn/phát hiện của chính lần đọc này (replay trả nguyên, không đọc lại BOQ hiện tại)
            kq := jsonb_build_object('boq_id', b, 'so_dong', n, 'trang_thai', tt, 'so_loi_chan', jsonb_array_length(p_loi_chan),
                                     'so_phat_hien', jsonb_array_length(p_phat_hien), 'loi_chan', p_loi_chan, 'phat_hien', p_phat_hien,
                                     'revision', moi);""" + _KET.format(a="NHAP_BOQ", d="h.du_an_id") + """
        END $$""",
    # ======================================================================= quyền thực thi
    "REVOKE EXECUTE ON FUNCTION " + ", ".join(HAM_TIN_CAY + HAM_LENH + HAM_DOC + HAM_NOI_BO) + " FROM PUBLIC",
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
            -- B6: biên nhận chỉ đọc được khi người của phiên còn quyền dự án hiện hành (thu hồi → không đọc kết quả cũ)
            CREATE POLICY bien_nhan_web ON m4.bien_nhan FOR SELECT TO app_web
                USING (master.ktt_danh_tinh() IS NOT NULL AND nguoi_dung_id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                       AND master.m4_duoc(du_an_id, 'XEM'));
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
            -- người review (vai REVIEW theo assignment dự án) thấy đợt/tệp hồ sơ đợt đã NỘP; phòng dự án (PHU_TRACH/XEM) thấy cả nháp trong phạm vi
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
            GRANT EXECUTE ON FUNCTION """ + ", ".join(HAM_LENH + HAM_DOC) + """ TO app_web;
        END IF;
    END $$""",
)
