"""M4-03A — kế toán xác nhận nguồn nghiệm thu (inbox KT trên gốc/phong bì M24). CHỈ hằng SQL, export `M4_03A_SQL`.

KHÔNG tự import/đăng ký/apply, KHÔNG đoán ordinal: Root integration owner append vào registry SAU nguyên prefix M24 và mọi migration đã cấp
ordinal. Không DROP/sửa bảng/hàm/dòng cũ; không đổi checksum 1–24. Thay đổi trên đối tượng cũ CHỈ gồm: nới CHECK vai của m4.quyen_du_an thêm
'KE_TOAN' (giữ PHU_TRACH/XEM/REVIEW/DUYET, không cấp cho ai) và thêm UNIQUE(id, cho_id) trên m4.duyet_kt_phong_bi làm đích FK tổ hợp (cấm
reparent chéo gốc). Hàng gốc/phong bì M24 không bị UPDATE.

- Quyền KT riêng: master.m4_kt_duoc(du_an) = danh tính ID + login hoạt động + module M4 trên PN + vai dự án 'KE_TOAN' chưa thu hồi + vai trò
  toàn cục KE_TOAN/KE_TOAN_TRUONG. master.m4_duoc / m4_duyet_duoc / hàm PDF/duyệt cũ KHÔNG đổi; REVIEW/DUYET/XEM không ngụ ý KT.
- m4.kt_xac_nhan: revision KT chỉ ghi thêm theo gốc (UNIQUE(cho_id, revision), truoc_id = revision trước cùng gốc), ghim phong bì/SHA/seal/
  phiên bản; loai NHAP (nháp, được thiếu) hoặc XAC_NHAN (đúng một/phong bì, sao y nguyên dữ liệu của nháp mới nhất đã lưu). Tiền là chuỗi thập
  phân chuẩn hoặc NULL (thiếu ≠ 0), KHÔNG copy số nguồn, không FX/VAT suy diễn/tài khoản/sổ cái.
- Đọc: hàm SECURITY DEFINER (kiểm quyền KT hiện hành bên trong) — EXECUTE chỉ cấp app_web; lệnh ghi = hàm SECURITY INVOKER chỉ chạy trên kết nối
  CHỦ BẢNG (master.la_chu_bang), EXECUTE thu hồi khỏi PUBLIC, không cấp lại. Khóa: HĐ → đợt → phiên bản mới nhất → gốc KT → revision KT → biên nhận
  (m4._bn_tra dùng chung). Không AP, không Request, không bút toán.
- Hiện hành nguồn (m4._kt_hien_hanh — đọc, lệnh, phát lại, trigger): phong bì mới nhất + phiên bản mới nhất + đồ thị L3 đã seal vẫn là kết quả L3
  công bố mới nhất (m4._kt_do_thi_hien_hanh, cùng quy tắc chọn của producer M24). L3 chạy lại + công bố sau seal → HOLD; seal/PDF/lịch sử giữ nguyên.
- Hiện hành TOÀN căn cứ (m4._kt_co_so_hien_hanh): đồ thị producer M24 THẬT (Python duyet_dot.do_thi, dựng trên kết nối chủ bảng sau quyền KT + khóa
  HĐ) được ghim bằng chứng thực SET LOCAL hữu hạn `ktt.kt_chung_thuc` (m4._kt_chung_thuc_ghi — nội bộ, không GRANT) gắn backend PID + txid + actor
  KT + gốc/đợt/HĐ/PN/dự án + phiên bản mới nhất + phong bì/seal/kết luận + SHA đồ thị + co_so_l3_sha256; bên đọc dựng lại mẫu từ ngữ cảnh hiện tại và
  SHA đồ thị/co_so đã seal rồi so ĐÚNG chuỗi, chỉ khi session_user thật là chủ bảng KT. Thiếu/hỏng/khác giao dịch/khác ngữ cảnh/app tự SET → HOLD
  (CAN_CU_DOI_SAU_SEAL), không fallback run/hash. Sửa metadata chứng từ không chạy lại L3 (L3 CU) → HOLD; không bảng/secret/vai mới.
"""

from __future__ import annotations

from .sql_duyet import TIEN, VAI_PDF, _HEX, _TIEN

_LOI = "USING ERRCODE = 'P0001'"
VAI_KT = "KE_TOAN"
VAI_TRO_KT = ("KE_TOAN", "KE_TOAN_TRUONG")
CO_SO = ("TRUOC_VAT", "GOM_VAT", "CHUA_RO")
VAT = ("CHUA_DU", "CO_CAN_CU", "KHONG_AP_DUNG")
LOAI = ("NHAP", "XAC_NHAN")
TIEN_KT = ("gia_tri_nt_xac_nhan", "tam_ung_xac_nhan", "thu_hoi_xac_nhan", "giu_lai_xac_nhan")
TIEN_NGUON = dict(zip(TIEN_KT, ("gia_tri_nt", "tam_ung", "thu_hoi", "giu_lai")))  # cặp so sánh KT ↔ số nguồn đã seal (chỉ để đòi lý do khi khác)
HANH_DONG = ("KT_LUU", "KT_XAC_NHAN")
QUYEN_LENH = ("XEM", "LUU", "XAC_NHAN", "PDF")
# mã thiếu (sắp theo collation "C" — Python sorted() trên ASCII cho cùng thứ tự)
THIEU = ("CO_SO_CHUA_XAC_DINH", "GIA_TRI_NT_THIEU", "LY_DO_KHAC_NGUON", "TIEN_TE_THIEU", "VAT_CAN_CU_THIEU", "VAT_CHUA_DU", "VAT_LY_DO_THIEU")
TT_DA_XAC_NHAN = "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"
AP_SQL = "jsonb_build_object('trang_thai', 'CHUA_TRIEN_KHAI_M4_03B', 'da_ghi_cong_no', false)"
REQUEST_SQL = "jsonb_build_object('trang_thai', 'CHUA_NOI_M4_04')"
BANG = ("kt_xac_nhan",)
HAM_DOC = ("master.m4_kt_duoc(uuid)", "m4.kt_doc_cho(uuid)", "m4.kt_kiem(uuid, text)", "m4.kt_danh_sach()", "m4.kt_chi_tiet(uuid, uuid)",
           "m4.kt_pdf(uuid, uuid)")
HAM_NOI_BO = ("m4._kt_tep_can_cu(uuid)", "m4._kt_toan_ven(uuid)", "m4._kt_ngu_canh(uuid)", "m4._kt_hien_hanh(uuid)",
              "m4._kt_thieu(m4.kt_xac_nhan, jsonb)", "m4._kt_dong(m4.kt_xac_nhan, jsonb)", "m4._kt_do_thi_hien_hanh(uuid)",
              "m4._kt_phien_chu()", "m4._kt_chung_thuc_mau(uuid, uuid, text, text)", "m4._kt_chung_thuc_ghi(uuid, uuid, uuid, text, text)",
              "m4._kt_co_so_hien_hanh(uuid)", "m4._kt_khoa_doc(uuid)")
# lý do HOLD của phong bì mới nhất (m4._kt_hien_hanh → kt_chi_tiet.ly_do_hold): phiên bản kế tiếp chưa seal / kết quả Chứng từ L3 đã công bố lại sau seal
# (đồ thị nguồn hiện hành của producer M24 không còn là đồ thị đã seal — chờ phiên bản đính chính được kết luận/duyệt/seal lại)
LY_DO_PHIEN_BAN = "PHIEN_BAN_KE_TIEP_CHUA_SEAL"
LY_DO_DO_THI = "L3_CONG_BO_LAI_SAU_SEAL"
LY_DO_HOLD = (LY_DO_PHIEN_BAN, LY_DO_DO_THI)
# căn cứ đầy đủ mà producer M24 thấy NGAY BÂY GIỜ khác đồ thị đã seal (vd sửa metadata chứng từ không chạy lại L3 → L3 CU), hoặc giao dịch này không có
# chứng thực producer hợp lệ của phiên chủ bảng (thiếu/cũ/sai ngữ cảnh/app tự SET) → HOLD, không fallback run/hash
LY_DO_CO_SO = "CAN_CU_DOI_SAU_SEAL"
LY_DO_HOLD_DAY_DU = (*LY_DO_HOLD, LY_DO_CO_SO)
GUC_CHUNG_THUC = "ktt.kt_chung_thuc"
# chọn kết quả L3 đã công bố MỚI NHẤT của đợt — ĐÚNG quy tắc producer M24 (duyet_dot._l3_cong_bo): chưa công bố/FAILED/STALE không tính
L3_CONG_BO_MOI_NHAT = ("SELECT r.id AS run_id, x.ket_qua_sha256 FROM m4.chung_tu_run r JOIN m4.chung_tu_result x ON x.run_id = r.id "
                       "WHERE r.dot_id = b.dot_id AND r.trang_thai IN ('SUCCEEDED','PARTIAL') AND x.cong_bo "
                       "ORDER BY r.xong_luc DESC NULLS LAST, r.tao_luc DESC, r.id LIMIT 1")
HAM_LENH = ("m4.kt_khoa(uuid, text)",
            "m4.kt_luu(text, jsonb, uuid, uuid, text, integer, jsonb)",
            "m4.kt_xac_nhan_lenh(text, jsonb, uuid, uuid, text, uuid, integer)")


def _sql_tuple(xs) -> str:
    return "(" + ",".join(f"'{x}'" for x in xs) + ")"


_TIN_CAY = """
            IF NOT master.la_chu_bang('m4.kt_xac_nhan'::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chỉ đường tin cậy của máy chủ ghi xác nhận kế toán' """ + _LOI + """;
            END IF;"""
_KB = "ai text := master.ktt_danh_tinh(); aid uuid := m4.ai_id(); cu jsonb; kq jsonb; rid uuid; h jsonb;"
_TIEN_COT = ",\n        ".join(f"{t} text CHECK ({t} IS NULL OR {t} {_TIEN})" for t in TIEN_KT)
_VND = " AND ".join(f"({t} IS NULL OR strpos({t}, '.') = 0)" for t in TIEN_KT)
_VND_NEW = " OR ".join(f"strpos(coalesce(NEW.{t}, ''), '.') > 0" for t in TIEN_KT)
_KHAC_NGUON = " OR ".join(f"(r.{k} IS NOT NULL AND r.{k} IS DISTINCT FROM p_nd->>'{n}')" for k, n in TIEN_NGUON.items())
_COT_DU_LIEU = ("tien_te", *TIEN_KT, "co_so_gia_tri", "vat_trang_thai", "vat_can_cu_tep_id", "vat_can_cu_sha256", "vat_trich_dan", "ly_do")
_COT_GHI = ("cho_id, dot_id, phap_nhan_id, du_an_id, hop_dong_id, phong_bi_id, phong_bi_sha256, seal_id, phien_ban_id, revision, truoc_id, loai, "
            "nhap_id, " + ", ".join(_COT_DU_LIEU) + ", tao_boi, tao_boi_id")
_ROW_NEW = "ROW(" + ", ".join(f"NEW.{c}" for c in _COT_DU_LIEU) + ")"
_ROW_N = "ROW(" + ", ".join(f"n.{c}" for c in _COT_DU_LIEU) + ")"
# lần phát lại (cùng actor + khóa + đúng body): quyền đã kiểm lại trong m4.kt_khoa; nguồn phải VẪN hiện hành và đúng phong bì của kết quả cũ
_LAP_LAI = """
            IF cu IS NOT NULL THEN
                IF NOT coalesce((h->>'toan_ven')::boolean, false) OR NOT coalesce((h->>'hien_hanh')::boolean, false)
                   OR (cu->'context'->>'phong_bi_id') IS DISTINCT FROM (h->>'phong_bi_id') THEN
                    RAISE EXCEPTION 'M4_KT_NGUON_CU: nguồn nghiệm thu đã đổi/không còn hiện hành — kết quả cũ chỉ còn trong lịch sử, tải lại' """ + _LOI + """;
                END IF;
                SELECT bn.id INTO rid FROM m4.bien_nhan bn WHERE bn.nguoi_dung_id = aid AND bn.khoa = p_khoa;
                RETURN jsonb_build_object('lap_lai', true, 'ket_qua', cu, 'receipt_id', rid);
            END IF;"""
# phong bì người dùng chọn: thuộc ĐÚNG gốc, toàn vẹn, là phong bì MỚI NHẤT, phiên bản hồ sơ chưa có kế tiếp chưa seal, SHA = lúc xem (CAS nguồn)
_PHONG_BI = """
            SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.id = p_phong_bi AND x.cho_id = p_cho;
            IF b.id IS NULL THEN
                RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy phong bì nguồn thuộc đúng gốc KT' """ + _LOI + """;
            END IF;
            IF NOT coalesce((h->>'toan_ven')::boolean, false) OR NOT m4._kt_toan_ven(b.id) THEN
                RAISE EXCEPTION 'M4_KT_NGUON_HONG: phong bì/seal/PDF nguồn không toàn vẹn — không dùng' """ + _LOI + """;
            END IF;
            IF b.id::text IS DISTINCT FROM (h->>'phong_bi_id') THEN
                RAISE EXCEPTION 'M4_KT_NGUON_CU: đã có phong bì nguồn mới hơn trên cùng gốc — phong bì này chỉ còn là lịch sử' """ + _LOI + """;
            END IF;
            IF NOT coalesce((h->>'hien_hanh')::boolean, false) THEN
                RAISE EXCEPTION 'M4_KT_CAN_KIEM_LAI: nguồn đã seal không còn hiện hành (phiên bản kế tiếp chưa seal / L3 công bố lại / căn cứ đổi sau seal) — chờ duyệt/seal lại, không xác nhận nguồn cũ' """ + _LOI + """;
            END IF;
            IF p_expected_sha IS NULL OR p_expected_sha IS DISTINCT FROM b.noi_dung_sha256 THEN
                RAISE EXCEPTION 'M4_KT_NGUON_DOI: SHA phong bì nguồn khác lúc xem — tải lại' """ + _LOI + """;
            END IF;"""
_KET = """
            PERFORM m4._bn_ghi(aid, p_khoa, '{a}', c.du_an_id, p_yc, kq);
            SELECT bn.id INTO rid FROM m4.bien_nhan bn WHERE bn.nguoi_dung_id = aid AND bn.khoa = p_khoa;
            RETURN jsonb_build_object('lap_lai', false, 'ket_qua', kq, 'receipt_id', rid);"""


def _kq(hanh: str, x: str, trang_thai: str, thieu: str, trung: str) -> str:
    return (f"jsonb_build_object('hanh_dong', '{hanh}', 'context', m4._kt_ngu_canh(b.id), 'kt_revision_id', {x}.id, 'revision', {x}.revision, "
            f"'loai', {x}.loai, 'nhap_id', {x}.nhap_id, 'trang_thai', {trang_thai}, 'thieu', {thieu}, 'trung_xac_nhan', {trung}, "
            f"'ap', {AP_SQL}, 'request', {REQUEST_SQL})")


# mảnh SQL dựng sẵn (không lồng biểu thức chứa dấu nháy trong f-string nhiều dòng)
_TIEN_MANG = ", ".join(f"'{x}'" for x in TIEN)
_DONG_KV = ", ".join(f"'{c}', r.{c}" for c in _COT_DU_LIEU)
_ND_TIEN = ", ".join(f"p_nd->>'{t}'" for t in TIEN_KT)
_N_COT = ", ".join(f"n.{c}" for c in _COT_DU_LIEU)
_KQ_LUU = _kq("LUU", "moi", "CASE WHEN jsonb_array_length(th) = 0 THEN 'CHO_XAC_NHAN' ELSE 'CHO_BO_SUNG' END", "th", "false")
_KQ_TRUNG = _kq("XAC_NHAN", "xn", "'" + TT_DA_XAC_NHAN + "'", "'[]'::jsonb", "true")
_KQ_XAC_NHAN = _kq("XAC_NHAN", "moi", "'" + TT_DA_XAC_NHAN + "'", "'[]'::jsonb", "false")
_VAI_TRO_KT_SQL = _sql_tuple(VAI_TRO_KT)
_LOAI_SQL = _sql_tuple(LOAI)
_CO_SO_SQL = _sql_tuple(CO_SO)
_VAT_SQL = _sql_tuple(VAT)
_QUYEN_LENH_SQL = _sql_tuple(QUYEN_LENH)


M4_03A_SQL = (
    "SET LOCAL check_function_bodies = off",
    # --- vai dự án KE_TOAN riêng (nới CHECK; tên ràng buộc tìm theo định nghĩa hiện hành của M24 — chứa 'vai' và 'DUYET'). Không cấp cho ai.
    """DO $$
    DECLARE r record;
    BEGIN
        FOR r IN SELECT c.conname FROM pg_catalog.pg_constraint c WHERE c.conrelid = 'm4.quyen_du_an'::regclass AND c.contype = 'c'
                   AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%vai%' AND pg_catalog.pg_get_constraintdef(c.oid) LIKE '%DUYET%' LOOP
            EXECUTE format('ALTER TABLE m4.quyen_du_an DROP CONSTRAINT %I', r.conname);
        END LOOP;
    END $$""",
    "ALTER TABLE m4.quyen_du_an ADD CONSTRAINT quyen_du_an_vai_check CHECK (vai IN ('PHU_TRACH','XEM','REVIEW','DUYET','KE_TOAN'))",
    f"""CREATE OR REPLACE FUNCTION master.m4_kt_duoc(p_du_an uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                       WHERE n.trang_thai = 'HOAT_DONG' AND n.dang_nhap = master.ktt_danh_tinh()
                         AND n.id::text = nullif(current_setting('ktt.nguoi_dung_id', true), '')
                         AND q.du_an_id = p_du_an AND q.thu_hoi_luc IS NULL AND master.ktt_duoc(q.phap_nhan_id, 'M4')
                         AND q.vai = '{VAI_KT}' AND n.vai_tro IN {_VAI_TRO_KT_SQL})
        $$""",
    # --- đích FK tổ hợp trên phong bì M24 (không đổi dữ liệu): revision KT không thể trỏ phong bì của gốc khác
    "ALTER TABLE m4.duyet_kt_phong_bi ADD CONSTRAINT duyet_kt_phong_bi_id_cho_uq UNIQUE (id, cho_id)",
    f"""CREATE TABLE m4.kt_xac_nhan (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        cho_id uuid NOT NULL,
        dot_id uuid NOT NULL,
        phap_nhan_id uuid NOT NULL,
        du_an_id uuid NOT NULL,
        hop_dong_id uuid NOT NULL,
        phong_bi_id uuid NOT NULL,
        phong_bi_sha256 text NOT NULL CHECK (phong_bi_sha256 {_HEX}),
        seal_id uuid NOT NULL,
        phien_ban_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        truoc_id uuid UNIQUE,
        loai text NOT NULL CHECK (loai IN {_LOAI_SQL}),
        nhap_id uuid UNIQUE,
        tien_te text CHECK (tien_te IS NULL OR tien_te ~ '^[A-Z]{{3}}$'),
        {_TIEN_COT},
        co_so_gia_tri text NOT NULL CHECK (co_so_gia_tri IN {_CO_SO_SQL}),
        vat_trang_thai text NOT NULL CHECK (vat_trang_thai IN {_VAT_SQL}),
        vat_can_cu_tep_id uuid,
        vat_can_cu_sha256 text CHECK (vat_can_cu_sha256 IS NULL OR vat_can_cu_sha256 {_HEX}),
        vat_trich_dan text CHECK (vat_trich_dan IS NULL OR (length(btrim(vat_trich_dan)) >= 1 AND length(vat_trich_dan) <= 2000)),
        ly_do text CHECK (ly_do IS NULL OR (length(btrim(ly_do)) >= 1 AND length(ly_do) <= 2000)),
        tao_boi text NOT NULL,
        tao_boi_id uuid NOT NULL REFERENCES master.nguoi_dung(id),
        tao_luc timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (du_an_id, phap_nhan_id) REFERENCES master.du_an (id, phap_nhan_id),
        FOREIGN KEY (hop_dong_id, du_an_id) REFERENCES m4.ho_so_hop_dong (hop_dong_id, du_an_id),
        FOREIGN KEY (cho_id, dot_id) REFERENCES m4.duyet_kt_cho (id, dot_id),
        FOREIGN KEY (phong_bi_id, cho_id) REFERENCES m4.duyet_kt_phong_bi (id, cho_id),
        FOREIGN KEY (seal_id, dot_id) REFERENCES m4.duyet_seal (id, dot_id),
        FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id),
        FOREIGN KEY (vat_can_cu_tep_id, du_an_id, vat_can_cu_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256),
        CHECK ((revision = 1) = (truoc_id IS NULL)),
        CHECK ((loai = 'XAC_NHAN') = (nhap_id IS NOT NULL)),
        CHECK ((vat_can_cu_tep_id IS NULL) = (vat_can_cu_sha256 IS NULL)),
        CHECK (vat_trang_thai = 'CO_CAN_CU' OR (vat_can_cu_tep_id IS NULL AND vat_trich_dan IS NULL)),
        CHECK (tien_te IS DISTINCT FROM 'VND' OR ({_VND})),
        CHECK (loai = 'NHAP' OR (gia_tri_nt_xac_nhan IS NOT NULL AND tien_te IS NOT NULL AND co_so_gia_tri IN ('TRUOC_VAT','GOM_VAT')
                                 AND ((vat_trang_thai = 'CO_CAN_CU' AND vat_can_cu_tep_id IS NOT NULL AND vat_trich_dan IS NOT NULL)
                                      OR (vat_trang_thai = 'KHONG_AP_DUNG' AND ly_do IS NOT NULL)))),
        UNIQUE (cho_id, revision),
        UNIQUE (id, cho_id),
        UNIQUE (id, phong_bi_id))""",
    "ALTER TABLE m4.kt_xac_nhan ADD CONSTRAINT kt_xac_nhan_truoc_fk FOREIGN KEY (truoc_id, cho_id) REFERENCES m4.kt_xac_nhan (id, cho_id)",
    "ALTER TABLE m4.kt_xac_nhan ADD CONSTRAINT kt_xac_nhan_nhap_fk FOREIGN KEY (nhap_id, phong_bi_id) REFERENCES m4.kt_xac_nhan (id, phong_bi_id)",
    "CREATE UNIQUE INDEX kt_xac_nhan_mot_xac_nhan_uq ON m4.kt_xac_nhan (phong_bi_id) WHERE loai = 'XAC_NHAN'",
    "CREATE INDEX kt_xac_nhan_phong_bi_idx ON m4.kt_xac_nhan (phong_bi_id, revision)",
    # --- ứng viên căn cứ VAT: m4.tep CÓ SẴN đúng PN + dự án của gốc, liên quan hồ sơ/HĐ: tệp chụp trong snapshot phiên bản của phong bì (HĐ/PL/
    #     tài liệu đợt), tệp đợt, tệp HĐ hiện hành, tệp PL đã ký. Không uploader/master mới; PDF hồ sơ đã duyệt (m4.duyet_pdf) không tự là căn cứ VAT.
    """CREATE OR REPLACE FUNCTION m4._kt_tep_can_cu(p_phong_bi uuid)
        RETURNS TABLE (id uuid, ten text, raw_sha256 text, media_type text, byte_length bigint)
        LANGUAGE sql STABLE SET search_path = master, m4, pg_temp AS $$
        WITH b AS (SELECT pb.id, pb.dot_id, pb.du_an_id, pb.phien_ban_id, c.phap_nhan_id, c.hop_dong_id
                   FROM m4.duyet_kt_phong_bi pb JOIN m4.duyet_kt_cho c ON c.id = pb.cho_id WHERE pb.id = p_phong_bi),
             s AS (SELECT v.snapshot FROM m4.duyet_phien_ban v JOIN b ON v.id = b.phien_ban_id),
             ids AS (SELECT s.snapshot->'tep_hop_dong'->>'id' AS tid FROM s
                     UNION SELECT x->>'tep_id' FROM s, jsonb_array_elements(CASE WHEN jsonb_typeof(s.snapshot->'phu_luc') = 'array'
                                                                                 THEN s.snapshot->'phu_luc' ELSE '[]'::jsonb END) x
                     UNION SELECT x->>'tep_id' FROM s, jsonb_array_elements(CASE WHEN jsonb_typeof(s.snapshot->'tai_lieu') = 'array'
                                                                                 THEN s.snapshot->'tai_lieu' ELSE '[]'::jsonb END) x
                     UNION SELECT k.tep_id::text FROM m4.dot_tep k JOIN b ON k.dot_id = b.dot_id
                     UNION SELECT h.tep_hop_dong_id::text FROM m4.ho_so_hop_dong h JOIN b ON h.hop_dong_id = b.hop_dong_id
                     UNION SELECT p.tep_id::text FROM m4.phu_luc p JOIN b ON p.hop_dong_id = b.hop_dong_id WHERE p.trang_thai = 'DA_KY')
        SELECT t.id, t.ten_goc, t.raw_sha256, t.media_type, t.byte_length
        FROM m4.tep t JOIN b ON t.du_an_id = b.du_an_id AND t.phap_nhan_id = b.phap_nhan_id
        WHERE t.id::text IN (SELECT ids.tid FROM ids WHERE ids.tid IS NOT NULL)
        ORDER BY t.ten_goc, t.id
        $$""",
    # --- toàn vẹn phong bì: SHA nội dung/số liệu tính lại khớp; seal/quyết định/PDF cùng kết luận/đồ thị/phiên bản; PDF đúng vai + hash/độ dài;
    #     tiền/dòng của phong bì = số liệu đã seal. Không sửa gì — sai → false (người gọi từ chối, không trả bằng chứng hỏng).
    f"""CREATE OR REPLACE FUNCTION m4._kt_toan_ven(p_phong_bi uuid) RETURNS boolean
        LANGUAGE plpgsql STABLE SET search_path = master, m4, pg_temp AS $$
        DECLARE b m4.duyet_kt_phong_bi%ROWTYPE; c m4.duyet_kt_cho%ROWTYPE; s m4.duyet_seal%ROWTYPE; p m4.duyet_pdf%ROWTYPE;
                q m4.duyet_quyet_dinh%ROWTYPE; t text;
        BEGIN
            SELECT * INTO b FROM m4.duyet_kt_phong_bi WHERE id = p_phong_bi;
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = b.cho_id;
            SELECT * INTO s FROM m4.duyet_seal WHERE id = b.seal_id;
            SELECT * INTO p FROM m4.duyet_pdf WHERE id = s.pdf_id;
            SELECT * INTO q FROM m4.duyet_quyet_dinh WHERE id = s.quyet_dinh_id;
            IF b.id IS NULL OR c.id IS NULL OR s.id IS NULL OR p.id IS NULL OR q.id IS NULL THEN
                RETURN false;
            END IF;
            IF b.noi_dung_sha256 IS DISTINCT FROM encode(sha256(convert_to(b.noi_dung::text, 'UTF8')), 'hex')
               OR s.so_lieu_sha256 IS DISTINCT FROM encode(sha256(convert_to(s.so_lieu::text, 'UTF8')), 'hex') THEN
                RETURN false;
            END IF;
            IF (b.dot_id, b.du_an_id, b.phien_ban_id) IS DISTINCT FROM (c.dot_id, c.du_an_id, s.phien_ban_id)
               OR (s.dot_id, s.du_an_id, s.phap_nhan_id, s.hop_dong_id) IS DISTINCT FROM (c.dot_id, c.du_an_id, c.phap_nhan_id, c.hop_dong_id)
               OR (q.ket_luan_id, q.graph_sha256, q.phien_ban_id) IS DISTINCT FROM (s.ket_luan_id, s.graph_sha256, s.phien_ban_id)
               OR (p.ket_luan_id, p.graph_sha256, p.phien_ban_id, p.raw_sha256, p.vai, p.media_type)
                  IS DISTINCT FROM (s.ket_luan_id, s.graph_sha256, s.phien_ban_id, s.pdf_sha256, '{VAI_PDF}', 'application/pdf')
               OR (b.noi_dung->>'seal_id') IS DISTINCT FROM s.id::text
               OR (b.noi_dung->>'phien_ban_id') IS DISTINCT FROM s.phien_ban_id::text
               OR (b.noi_dung->>'quyet_dinh_id') IS DISTINCT FROM q.id::text
               OR (b.noi_dung->>'ket_luan_id') IS DISTINCT FROM s.ket_luan_id::text
               OR (b.noi_dung->'pdf'->>'id') IS DISTINCT FROM p.id::text
               OR (b.noi_dung->'pdf'->>'raw_sha256') IS DISTINCT FROM p.raw_sha256
               OR (b.noi_dung->'pdf'->>'byte_length') IS DISTINCT FROM p.byte_length::text THEN
                RETURN false;
            END IF;
            FOREACH t IN ARRAY ARRAY['tien_te', {_TIEN_MANG}, 'dong'] LOOP
                IF (b.noi_dung->t) IS DISTINCT FROM (s.so_lieu->t) THEN
                    RETURN false;
                END IF;
            END LOOP;
            RETURN true;
        END $$""",
    # --- ngữ cảnh typed của MỘT phong bì (định danh server-resolve từ gốc/phong bì/seal đã chốt; lịch sử giữ đúng định danh cũ)
    """CREATE OR REPLACE FUNCTION m4._kt_ngu_canh(p_phong_bi uuid) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, m4, pg_temp AS $$
        SELECT jsonb_build_object('phap_nhan_id', c.phap_nhan_id, 'du_an_id', c.du_an_id, 'hop_dong_id', c.hop_dong_id, 'dot_id', c.dot_id,
                                  'kt_pending_id', c.id, 'phong_bi_id', b.id, 'seal_id', s.id, 'version_id', s.phien_ban_id,
                                  'ket_luan_id', s.ket_luan_id, 'pdf_id', s.pdf_id, 'phong_bi_sha256', b.noi_dung_sha256,
                                  'graph_sha256', s.graph_sha256, 'pdf_sha256', s.pdf_sha256)
        FROM m4.duyet_kt_phong_bi b JOIN m4.duyet_kt_cho c ON c.id = b.cho_id JOIN m4.duyet_seal s ON s.id = b.seal_id
        WHERE b.id = p_phong_bi
        $$""",
    # --- đồ thị nguồn của phong bì còn hiện hành? Thành phần L3 của đồ thị đã seal (kết luận của seal: l3_run_id + ket_qua_sha256 trong graph) phải
    #     ĐÚNG là kết quả L3 đã công bố mới nhất của đợt theo quy tắc producer M24. L3 chạy lại và công bố B (cùng phiên bản) → đồ thị khác → false.
    #     Chỉ đọc; seal/phong bì/PDF/lịch sử A giữ nguyên. Không có kết quả công bố nào (bất thường sau seal) → false (HOLD, không đoán).
    """CREATE OR REPLACE FUNCTION m4._kt_do_thi_hien_hanh(p_phong_bi uuid) RETURNS boolean
        LANGUAGE sql STABLE SET search_path = master, m4, pg_temp AS $$
        SELECT coalesce((SELECT l.run_id = k.l3_run_id AND l.ket_qua_sha256 IS NOT DISTINCT FROM (k.graph->'l3'->>'ket_qua_sha256')
                         FROM m4.duyet_kt_phong_bi b JOIN m4.duyet_seal s ON s.id = b.seal_id JOIN m4.duyet_ket_luan k ON k.id = s.ket_luan_id
                         JOIN LATERAL (""" + L3_CONG_BO_MOI_NHAT + """) l ON true
                         WHERE b.id = p_phong_bi), false)
        $$""",
    # --- phiên SQL hiện tại có phải ĐĂNG NHẬP THẬT của chủ bảng KT? Dùng session_user (không phải current_user — bên trong hàm SECURITY DEFINER đọc,
    #     current_user luôn là chủ hàm). Login ứng dụng thường → false.
    """CREATE OR REPLACE FUNCTION m4._kt_phien_chu() RETURNS boolean
        LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $$
        SELECT coalesce((SELECT c.relowner = (SELECT r.oid FROM pg_catalog.pg_roles r WHERE r.rolname = session_user)
                         FROM pg_catalog.pg_class c WHERE c.oid = 'm4.kt_xac_nhan'::regclass), false)
        $$""",
    # --- mẫu chứng thực (chuỗi jsonb chuẩn của PostgreSQL): backend + giao dịch + actor KT của phiên + ngữ cảnh server-resolve của phong bì + phiên bản +
    #     SHA đồ thị + co_so_l3_sha256. Bên ghi điền SHA producer thật; bên đọc điền SHA đã seal — hai chuỗi bằng nhau ⇔ đồ thị hiện tại = đồ thị đã seal.
    """CREATE OR REPLACE FUNCTION m4._kt_chung_thuc_mau(p_phong_bi uuid, p_version uuid, p_graph_sha text, p_co_so_sha text) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, m4, pg_temp AS $$
        SELECT jsonb_build_object('pid', pg_catalog.pg_backend_pid(), 'txid', pg_catalog.txid_current(),
                                  'actor', nullif(current_setting('ktt.nguoi_dung_id', true), ''),
                                  'kt_pending_id', c.id, 'dot_id', c.dot_id, 'hop_dong_id', c.hop_dong_id, 'phap_nhan_id', c.phap_nhan_id,
                                  'du_an_id', c.du_an_id, 'version_id', p_version, 'phong_bi_id', b.id, 'seal_id', s.id, 'ket_luan_id', s.ket_luan_id,
                                  'graph_sha256', p_graph_sha, 'co_so_l3_sha256', p_co_so_sha)
        FROM m4.duyet_kt_phong_bi b JOIN m4.duyet_kt_cho c ON c.id = b.cho_id JOIN m4.duyet_seal s ON s.id = b.seal_id
        WHERE b.id = p_phong_bi
        $$""",
    # --- GHI chứng thực producer (chỉ đường chủ bảng, sau quyền KT + khóa HĐ của người gọi): session_user thật là chủ bảng → danh tính phiên ĐÃ
    #     khôi phục về actor KT (sau khi producer tạm đổi sang người công bố L3) → quyền KT hiện hành của actor đó → SET LOCAL mẫu của phong bì MỚI
    #     NHẤT. Hết giao dịch là mất; không bảng/proof bền. Không SET clause ở hàm này (SET LOCAL phải sống tới hết giao dịch) — mọi tên đều đủ schema.
    f"""CREATE OR REPLACE FUNCTION m4._kt_chung_thuc_ghi(p_cho uuid, p_actor uuid, p_version uuid, p_graph_sha text, p_co_so_sha text) RETURNS jsonb
        LANGUAGE plpgsql AS $$
        DECLARE a jsonb; moi uuid;
        BEGIN
            IF NOT m4._kt_phien_chu() THEN
                RAISE EXCEPTION 'M4_CHI_MAY_CHU_NGUON: chứng thực nguồn kế toán chỉ ghi trên phiên đăng nhập chủ bảng của máy chủ' {_LOI};
            END IF;
            IF p_actor IS NULL OR p_actor::text IS DISTINCT FROM nullif(pg_catalog.current_setting('ktt.nguoi_dung_id', true), '') THEN
                RAISE EXCEPTION 'M4_KT_DANH_TINH: danh tính phiên chưa khôi phục về kế toán sau khi dựng đồ thị nguồn — không ghim' {_LOI};
            END IF;
            PERFORM m4.kt_kiem(p_cho, 'XEM');
            IF p_version IS NULL OR p_graph_sha IS NULL OR p_co_so_sha IS NULL OR NOT (p_graph_sha {_HEX}) OR NOT (p_co_so_sha {_HEX}) THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: chứng thực đồ thị nguồn không đúng hình dạng' {_LOI};
            END IF;
            SELECT x.id INTO moi FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = p_cho ORDER BY x.thu_tu DESC LIMIT 1;
            a := m4._kt_chung_thuc_mau(moi, p_version, p_graph_sha, p_co_so_sha);
            IF a IS NULL THEN
                RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy phong bì nguồn thuộc đúng gốc KT' {_LOI};
            END IF;
            PERFORM pg_catalog.set_config('{GUC_CHUNG_THUC}', a::text, true);
            RETURN a;
        END $$""",
    # --- ĐỌC chứng thực: chỉ phiên chủ bảng thật; mẫu dựng lại từ ngữ cảnh hiện tại + phiên bản của phong bì + SHA đồ thị/co_so ĐÃ SEAL (kết luận của
    #     seal, cùng graph_sha256) phải trùng ĐÚNG chuỗi đã ghi trong cùng backend/giao dịch/actor. Thiếu/hỏng/khác → false (HOLD), không fallback.
    f"""CREATE OR REPLACE FUNCTION m4._kt_co_so_hien_hanh(p_phong_bi uuid) RETURNS boolean
        LANGUAGE plpgsql STABLE SET search_path = master, m4, pg_temp AS $$
        DECLARE a text := nullif(current_setting('{GUC_CHUNG_THUC}', true), ''); mau jsonb;
        BEGIN
            IF a IS NULL OR NOT m4._kt_phien_chu() THEN
                RETURN false;
            END IF;
            SELECT m4._kt_chung_thuc_mau(b.id, b.phien_ban_id, s.graph_sha256, k.graph->>'co_so_l3_sha256') INTO mau
            FROM m4.duyet_kt_phong_bi b JOIN m4.duyet_seal s ON s.id = b.seal_id JOIN m4.duyet_ket_luan k ON k.id = s.ket_luan_id
            WHERE b.id = p_phong_bi AND k.graph_sha256 = s.graph_sha256;
            RETURN mau IS NOT NULL AND a = mau::text;
        END $$""",
    # --- khóa ĐỌC (đường chủ bảng của xem/danh sách): quyền KT hiện hành TRƯỚC → HĐ FOR SHARE suốt giao dịch đọc (sửa metadata/ghép chứng từ giữ HĐ
    #     FOR UPDATE phải chờ) để đồ thị producer + chi tiết KT cùng một trạng thái căn cứ. Lệnh ghi dùng m4.kt_khoa (FOR UPDATE).
    """CREATE OR REPLACE FUNCTION m4._kt_khoa_doc(p_cho uuid) RETURNS text
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE q text; c m4.duyet_kt_cho%ROWTYPE;
        BEGIN""" + _TIN_CAY + """
            q := m4.kt_kiem(p_cho, 'XEM');
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = p_cho;
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = c.hop_dong_id FOR SHARE;
            RETURN q;
        END $$""",
    # --- hiện hành của gốc: phong bì mới nhất + phiên bản mới nhất của đợt + đồ thị L3 đã seal vẫn là đồ thị công bố mới nhất + căn cứ đầy đủ của producer
    #     (chứng thực của giao dịch này) = đồ thị đã seal; phiên bản kế tiếp chưa seal, L3 công bố lại hoặc căn cứ đổi sau seal → hien_hanh=false
    #     (HOLD/CAN_KIEM_LAI). Lệnh gọi hàm này SAU m4.kt_khoa (dưới khóa) — guard tại thời điểm ghi.
    f"""CREATE OR REPLACE FUNCTION m4._kt_hien_hanh(p_cho uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, m4, pg_temp AS $$
        DECLARE c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE; v_moi uuid; dt boolean; cs boolean;
        BEGIN
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = p_cho;
            IF c.id IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = p_cho ORDER BY x.thu_tu DESC LIMIT 1;
            SELECT v.id INTO v_moi FROM m4.duyet_phien_ban v WHERE v.dot_id = c.dot_id ORDER BY v.so DESC LIMIT 1;
            dt := b.id IS NOT NULL AND m4._kt_do_thi_hien_hanh(b.id);
            cs := b.id IS NOT NULL AND m4._kt_co_so_hien_hanh(b.id);
            RETURN jsonb_build_object('phong_bi_id', b.id, 'phong_bi_sha256', b.noi_dung_sha256, 'thu_tu', b.thu_tu, 'version_id', b.phien_ban_id,
                                      'version_moi_nhat_id', v_moi, 'toan_ven', b.id IS NOT NULL AND m4._kt_toan_ven(b.id),
                                      'do_thi_hien_hanh', dt, 'co_so_hien_hanh', cs,
                                      'hien_hanh', b.id IS NOT NULL AND v_moi IS NOT DISTINCT FROM b.phien_ban_id AND dt AND cs,
                                      'ly_do', CASE WHEN v_moi IS DISTINCT FROM b.phien_ban_id THEN '{LY_DO_PHIEN_BAN}'
                                                    WHEN NOT dt THEN '{LY_DO_DO_THI}'
                                                    WHEN NOT cs THEN '{LY_DO_CO_SO}' END);
        END $$""",
    # --- điều kiện xác nhận (thiếu → HOLD/CHO_BO_SUNG, không bao giờ 0): số NT + tiền tệ + cơ sở xác định + VAT có căn cứ (tệp + trích dẫn) hoặc
    #     không áp dụng có lý do; số KT khác số nguồn đã seal phải có lý do. Các số KT khác vẫn nullable (03B mới chốt cơ sở hạch toán).
    f"""CREATE OR REPLACE FUNCTION m4._kt_thieu(r m4.kt_xac_nhan, p_nd jsonb) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, m4, pg_temp AS $$
        DECLARE x text[] := ARRAY[]::text[];
        BEGIN
            IF r.gia_tri_nt_xac_nhan IS NULL THEN
                x := array_append(x, 'GIA_TRI_NT_THIEU');
            END IF;
            IF r.tien_te IS NULL THEN
                x := array_append(x, 'TIEN_TE_THIEU');
            END IF;
            IF r.co_so_gia_tri IS NULL OR r.co_so_gia_tri NOT IN ('TRUOC_VAT','GOM_VAT') THEN
                x := array_append(x, 'CO_SO_CHUA_XAC_DINH');
            END IF;
            IF r.vat_trang_thai = 'CO_CAN_CU' THEN
                IF r.vat_can_cu_tep_id IS NULL OR r.vat_trich_dan IS NULL THEN
                    x := array_append(x, 'VAT_CAN_CU_THIEU');
                END IF;
            ELSIF r.vat_trang_thai = 'KHONG_AP_DUNG' THEN
                IF r.ly_do IS NULL THEN
                    x := array_append(x, 'VAT_LY_DO_THIEU');
                END IF;
            ELSE
                x := array_append(x, 'VAT_CHUA_DU');
            END IF;
            IF r.ly_do IS NULL AND ({_KHAC_NGUON}) THEN
                x := array_append(x, 'LY_DO_KHAC_NGUON');
            END IF;
            RETURN (SELECT coalesce(jsonb_agg(e ORDER BY e COLLATE "C"), '[]'::jsonb) FROM unnest(x) e);
        END $$""",
    # --- dữ kiện một revision KT (máy chủ đọc; Python dựng DTO typed + đối chiếu thiếu)
    f"""CREATE OR REPLACE FUNCTION m4._kt_dong(r m4.kt_xac_nhan, p_nd jsonb) RETURNS jsonb
        LANGUAGE sql STABLE SET search_path = master, m4, pg_temp AS $$
        SELECT jsonb_build_object('kt_revision_id', r.id, 'revision', r.revision, 'loai', r.loai, 'nhap_id', r.nhap_id, 'phong_bi_id', r.phong_bi_id,
                                  {_DONG_KV},
                                  'thieu', m4._kt_thieu(r, p_nd), 'tao_boi', r.tao_boi, 'tao_luc', r.tao_luc)
        $$""",
    # --- trigger: chỉ chủ bảng; chỉ ghi thêm; định danh = gốc/phong bì; phong bì mới nhất + phiên bản hiện hành; revision = max+1 nối truoc_id;
    #     một xác nhận/phong bì; tiền tệ = nguồn; VND không lẻ; căn cứ VAT trong tập ứng viên; xác nhận = sao y nháp mới nhất, đủ điều kiện.
    f"""CREATE OR REPLACE FUNCTION m4.kt_xac_nhan_kiem() RETURNS trigger
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE; cuoi m4.kt_xac_nhan%ROWTYPE; n m4.kt_xac_nhan%ROWTYPE;
                tt_moi integer; v_moi uuid;
        BEGIN
            IF NOT master.la_chu_bang(TG_RELID::regclass) THEN
                RAISE EXCEPTION 'M4_CHI_CHU: xác nhận kế toán chỉ ghi qua hàm định nghĩa trên kết nối chủ bảng' {_LOI};
            END IF;
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'M4_BAT_BIEN: revision kế toán chỉ ghi thêm, không sửa/xóa' {_LOI};
            END IF;
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = NEW.cho_id;
            SELECT * INTO b FROM m4.duyet_kt_phong_bi WHERE id = NEW.phong_bi_id AND cho_id = NEW.cho_id;
            IF c.id IS NULL OR b.id IS NULL
               OR (NEW.dot_id, NEW.du_an_id, NEW.phap_nhan_id, NEW.hop_dong_id) IS DISTINCT FROM (c.dot_id, c.du_an_id, c.phap_nhan_id, c.hop_dong_id)
               OR (NEW.phong_bi_sha256, NEW.seal_id, NEW.phien_ban_id) IS DISTINCT FROM (b.noi_dung_sha256, b.seal_id, b.phien_ban_id) THEN
                RAISE EXCEPTION 'M4_KT_NGUON_SAI: định danh revision KT không khớp gốc/phong bì nguồn' {_LOI};
            END IF;
            SELECT max(x.thu_tu) INTO tt_moi FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = c.id;
            IF b.thu_tu <> tt_moi THEN
                RAISE EXCEPTION 'M4_KT_NGUON_CU: chỉ ghi KT trên phong bì nguồn mới nhất của gốc' {_LOI};
            END IF;
            SELECT v.id INTO v_moi FROM m4.duyet_phien_ban v WHERE v.dot_id = c.dot_id ORDER BY v.so DESC LIMIT 1;
            IF v_moi IS DISTINCT FROM b.phien_ban_id THEN
                RAISE EXCEPTION 'M4_KT_CAN_KIEM_LAI: hồ sơ đợt có phiên bản kế tiếp chưa seal' {_LOI};
            END IF;
            IF NOT m4._kt_do_thi_hien_hanh(b.id) THEN
                RAISE EXCEPTION 'M4_KT_CAN_KIEM_LAI: Chứng từ L3 đã công bố lại sau seal — đồ thị nguồn khác đồ thị đã seal' {_LOI};
            END IF;
            IF NOT m4._kt_co_so_hien_hanh(b.id) THEN
                RAISE EXCEPTION 'M4_KT_CAN_KIEM_LAI: căn cứ đầy đủ producer hiện tại khác đồ thị đã seal (hoặc thiếu chứng thực producer của giao dịch này)' {_LOI};
            END IF;
            SELECT * INTO cuoi FROM m4.kt_xac_nhan x WHERE x.cho_id = c.id ORDER BY x.revision DESC LIMIT 1;
            IF NEW.revision IS DISTINCT FROM coalesce(cuoi.revision, 0) + 1 OR NEW.truoc_id IS DISTINCT FROM cuoi.id THEN
                RAISE EXCEPTION 'M4_KT_REVISION_CU: revision KT phải nối tiếp revision mới nhất của gốc' {_LOI};
            END IF;
            IF EXISTS (SELECT 1 FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id AND x.loai = 'XAC_NHAN') THEN
                RAISE EXCEPTION 'M4_KT_DA_XAC_NHAN: phong bì nguồn đã được kế toán xác nhận — không ghi đè' {_LOI};
            END IF;
            IF NEW.tien_te IS NOT NULL AND NEW.tien_te IS DISTINCT FROM (b.noi_dung->>'tien_te') THEN
                RAISE EXCEPTION 'M4_KT_TIEN_TE_KHAC: tiền tệ KT phải đúng tiền tệ nguồn đã seal (không quy đổi)' {_LOI};
            END IF;
            IF (b.noi_dung->>'tien_te') = 'VND' AND ({_VND_NEW}) THEN
                RAISE EXCEPTION 'M4_KT_SO_SAI: VND không có phần lẻ' {_LOI};
            END IF;
            IF NEW.vat_can_cu_tep_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM m4._kt_tep_can_cu(b.id) t
                                                                  WHERE t.id = NEW.vat_can_cu_tep_id AND t.raw_sha256 = NEW.vat_can_cu_sha256) THEN
                RAISE EXCEPTION 'M4_KT_CAN_CU_VAT_SAI: tệp căn cứ VAT không thuộc hồ sơ/HĐ của nguồn trong phạm vi' {_LOI};
            END IF;
            IF NEW.loai = 'XAC_NHAN' THEN
                SELECT * INTO n FROM m4.kt_xac_nhan x WHERE x.id = NEW.nhap_id;
                IF n.id IS NULL OR n.loai <> 'NHAP' OR n.phong_bi_id <> NEW.phong_bi_id OR NEW.truoc_id IS DISTINCT FROM n.id
                   OR {_ROW_NEW} IS DISTINCT FROM {_ROW_N} THEN
                    RAISE EXCEPTION 'M4_KT_XAC_NHAN_KHAC_NHAP: xác nhận phải sao y đúng bản nháp mới nhất đã lưu' {_LOI};
                END IF;
                IF jsonb_array_length(m4._kt_thieu(NEW, b.noi_dung)) > 0 THEN
                    RAISE EXCEPTION 'M4_KT_CHO_BO_SUNG: bản KT chưa đủ điều kiện xác nhận' {_LOI};
                END IF;
            END IF;
            RETURN NEW;
        END $$""",
    "CREATE TRIGGER kt_xac_nhan_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.kt_xac_nhan FOR EACH ROW EXECUTE FUNCTION m4.kt_xac_nhan_kiem()",
    "CREATE TRIGGER kt_xac_nhan_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.kt_xac_nhan FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()",
    # ============================================================== đọc (SECURITY DEFINER; quyền KT hiện hành kiểm bên trong; không lộ tồn tại)
    """CREATE OR REPLACE FUNCTION m4.kt_doc_cho(p_cho uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        SELECT EXISTS (SELECT 1 FROM m4.duyet_kt_cho c WHERE c.id = p_cho AND master.m4_kt_duoc(c.du_an_id))
        $$""",
    # kiểm quyền KT hiện hành cho MỘT hành động — gọi TRƯỚC nguồn/biên nhận/blob/lịch sử. Không thấy → 404; thấy gốc qua quyền M24 (XEM/REVIEW/DUYET)
    # nhưng không có vai KE_TOAN → 403. Một vai KE_TOAN cho mọi hành động KT (xem/lưu/xác nhận/tải PDF).
    f"""CREATE OR REPLACE FUNCTION m4.kt_kiem(p_cho uuid, p_hanh text) RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE d_du_an uuid; d_dot uuid;
        BEGIN
            IF p_hanh IS NULL OR p_hanh NOT IN {_QUYEN_LENH_SQL} THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: hành động kế toán không hợp lệ' {_LOI};
            END IF;
            PERFORM m4.ai_id();
            SELECT c.du_an_id, c.dot_id INTO d_du_an, d_dot FROM m4.duyet_kt_cho c WHERE c.id = p_cho;
            IF d_du_an IS NULL THEN
                RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy hồ sơ chờ kế toán (hoặc ngoài phạm vi hiện hành)' {_LOI};
            END IF;
            IF master.m4_kt_duoc(d_du_an) THEN
                RETURN '{VAI_KT}';
            END IF;
            IF m4.duyet_doc_dot(d_dot) THEN
                RAISE EXCEPTION 'M4_KT_PHAM_VI: cần vai dự án KE_TOAN hiện hành (xem/duyệt/review không ngụ ý quyền kế toán)' {_LOI};
            END IF;
            RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy hồ sơ chờ kế toán (hoặc ngoài phạm vi hiện hành)' {_LOI};
        END $$""",
    # inbox: mỗi gốc trong phạm vi KT hiện hành MỘT dòng — phong bì mới nhất + revision KT mới nhất của chính phong bì đó (hoặc null)
    """CREATE OR REPLACE FUNCTION m4.kt_danh_sach() RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE; k m4.kt_xac_nhan%ROWTYPE; h jsonb; ds jsonb := '[]'::jsonb;
        BEGIN
            PERFORM m4.ai_id();
            FOR c IN SELECT * FROM m4.duyet_kt_cho x WHERE master.m4_kt_duoc(x.du_an_id) ORDER BY x.tao_luc, x.id LOOP
                h := m4._kt_hien_hanh(c.id);
                SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.id = (h->>'phong_bi_id')::uuid;
                SELECT * INTO k FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id ORDER BY x.revision DESC LIMIT 1;
                ds := ds || jsonb_build_array(jsonb_build_object(
                    'kt_pending_id', c.id, 'dot_id', c.dot_id, 'phong_bi_id', b.id, 'phong_bi_sha256', b.noi_dung_sha256,
                    'hien_hanh', coalesce((h->>'hien_hanh')::boolean, false), 'toan_ven', coalesce((h->>'toan_ven')::boolean, false),
                    'kt', CASE WHEN k.id IS NULL THEN NULL ELSE m4._kt_dong(k, b.noi_dung) END));
            END LOOP;
            RETURN ds;
        END $$""",
    # chi tiết một gốc (phong bì đang chọn hoặc mới nhất) trong MỘT snapshot câu lệnh: ngữ cảnh, nguồn đã seal (chỉ đọc), PDF metadata, ứng viên
    # căn cứ VAT, revision KT mới nhất CỦA phong bì đó, lịch sử phong bì + revision KT thật (append-only). Mọi phong bì của gốc phải toàn vẹn.
    """CREATE OR REPLACE FUNCTION m4.kt_chi_tiet(p_cho uuid, p_phong_bi uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE h jsonb; b m4.duyet_kt_phong_bi%ROWTYPE; p m4.duyet_pdf%ROWTYPE; k m4.kt_xac_nhan%ROWTYPE; moi uuid; hh boolean;
        BEGIN
            PERFORM m4.kt_kiem(p_cho, 'XEM');
            h := m4._kt_hien_hanh(p_cho);
            moi := (h->>'phong_bi_id')::uuid;
            hh := coalesce((h->>'hien_hanh')::boolean, false);
            IF EXISTS (SELECT 1 FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = p_cho AND NOT m4._kt_toan_ven(x.id)) THEN
                RAISE EXCEPTION 'M4_KT_NGUON_HONG: phong bì/seal/PDF nguồn không toàn vẹn — không trả bằng chứng' USING ERRCODE = 'P0001';
            END IF;
            SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.cho_id = p_cho AND x.id = coalesce(p_phong_bi, moi);
            IF b.id IS NULL THEN
                RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy phong bì nguồn thuộc đúng gốc KT' USING ERRCODE = 'P0001';
            END IF;
            SELECT x.* INTO p FROM m4.duyet_pdf x JOIN m4.duyet_seal s ON s.pdf_id = x.id WHERE s.id = b.seal_id;
            SELECT * INTO k FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id ORDER BY x.revision DESC LIMIT 1;
            RETURN jsonb_build_object(
                'context', m4._kt_ngu_canh(b.id),
                'can_cu_hien_hanh', b.id = moi AND hh,
                'phong_bi_moi_nhat', b.id = moi,
                'ly_do_hold', CASE WHEN b.id = moi AND NOT hh THEN h->>'ly_do' END,
                'nguon', b.noi_dung,
                'pdf', jsonb_build_object('id', p.id, 'ten', p.ten, 'media_type', p.media_type, 'raw_sha256', p.raw_sha256, 'byte_length', p.byte_length),
                'tep_can_cu', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', t.id, 'ten', t.ten, 'raw_sha256', t.raw_sha256, 'media_type', t.media_type,
                                                                            'byte_length', t.byte_length) ORDER BY t.ten, t.id), '[]'::jsonb)
                               FROM m4._kt_tep_can_cu(b.id) t),
                'kt', CASE WHEN k.id IS NULL THEN NULL ELSE m4._kt_dong(k, b.noi_dung) END,
                'da_xac_nhan', EXISTS (SELECT 1 FROM m4.kt_xac_nhan z WHERE z.phong_bi_id = b.id AND z.loai = 'XAC_NHAN'),
                'lich_su_phong_bi', (SELECT coalesce(jsonb_agg(jsonb_build_object('context', m4._kt_ngu_canh(x.id), 'thu_tu', x.thu_tu, 'truoc_id', x.truoc_id,
                                                                                  'phien_ban_so', v.so, 'can_cu_hien_hanh', x.id = moi AND hh)
                                                               ORDER BY x.thu_tu), '[]'::jsonb)
                                     FROM m4.duyet_kt_phong_bi x JOIN m4.duyet_phien_ban v ON v.id = x.phien_ban_id WHERE x.cho_id = p_cho),
                'lich_su_kt', (SELECT coalesce(jsonb_agg(jsonb_build_object('context', m4._kt_ngu_canh(z.phong_bi_id), 'kt', m4._kt_dong(z, x.noi_dung),
                                                                            'nguon', x.noi_dung - 'dong')
                                                         ORDER BY z.revision), '[]'::jsonb)
                               FROM m4.kt_xac_nhan z JOIN m4.duyet_kt_phong_bi x ON x.id = z.phong_bi_id WHERE z.cho_id = p_cho));
        END $$""",
    # metadata PDF hồ sơ đã duyệt ĐÚNG seal của phong bì (gồm phong bì lịch sử cùng gốc) — kiểm quyền KT TRƯỚC tra cứu; không object_key/đường dẫn
    f"""CREATE OR REPLACE FUNCTION m4.kt_pdf(p_cho uuid, p_phong_bi uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = master, m4, pg_temp AS $$
        DECLARE b m4.duyet_kt_phong_bi%ROWTYPE; p m4.duyet_pdf%ROWTYPE;
        BEGIN
            PERFORM m4.kt_kiem(p_cho, 'PDF');
            SELECT * INTO b FROM m4.duyet_kt_phong_bi x WHERE x.id = p_phong_bi AND x.cho_id = p_cho;
            IF b.id IS NULL THEN
                RAISE EXCEPTION 'M4_KT_KHONG_THAY: không thấy phong bì nguồn thuộc đúng gốc KT' {_LOI};
            END IF;
            IF NOT m4._kt_toan_ven(b.id) THEN
                RAISE EXCEPTION 'M4_KT_NGUON_HONG: phong bì/seal/PDF nguồn không toàn vẹn — không tải' {_LOI};
            END IF;
            SELECT x.* INTO p FROM m4.duyet_pdf x JOIN m4.duyet_seal s ON s.pdf_id = x.id WHERE s.id = b.seal_id AND x.vai = '{VAI_PDF}';
            RETURN jsonb_build_object('pdf_id', p.id, 'ten', p.ten, 'media_type', p.media_type, 'raw_sha256', p.raw_sha256, 'byte_length', p.byte_length);
        END $$""",
    # ============================================================== lệnh (SECURITY INVOKER, chỉ kết nối chủ bảng)
    # bước khóa chung: quyền KT hiện hành → HĐ → đợt → phiên bản mới nhất → gốc KT → revision KT mới nhất (FOR UPDATE). Biên nhận khóa SAU (m4._bn_tra).
    f"""CREATE OR REPLACE FUNCTION m4.kt_khoa(p_cho uuid, p_hanh text) RETURNS text
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE q text; c m4.duyet_kt_cho%ROWTYPE;
        BEGIN""" + _TIN_CAY + """
            q := m4.kt_kiem(p_cho, p_hanh);
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = p_cho;
            PERFORM 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = c.hop_dong_id FOR UPDATE;
            PERFORM 1 FROM m4.dot WHERE id = c.dot_id FOR UPDATE;
            PERFORM 1 FROM m4.duyet_phien_ban v WHERE v.dot_id = c.dot_id ORDER BY v.so DESC LIMIT 1 FOR UPDATE;
            PERFORM 1 FROM m4.duyet_kt_cho WHERE id = c.id FOR UPDATE;
            PERFORM 1 FROM m4.kt_xac_nhan x WHERE x.cho_id = c.id ORDER BY x.revision DESC LIMIT 1 FOR UPDATE;
            -- lần chạy L3 chưa kết thúc của đợt: chờ giao dịch công bố đang dở (m4.chung_tu_cong_bo khóa FOR UPDATE) xong rồi mới đọc đồ thị hiện hành
            PERFORM 1 FROM m4.chung_tu_run r WHERE r.dot_id = c.dot_id AND r.trang_thai IN ('PENDING','RUNNING') FOR SHARE;
            RETURN q;
        END $$""",
    # LƯU NHÁP: revision KT mới (NHAP) trên phong bì hiện hành; CAS = SHA phong bì + revision KT mới nhất CỦA phong bì (0 = chưa có — chỉ lần đầu).
    # Thiếu được lưu; không tự xác nhận. Căn cứ VAT: id do máy chủ resolve trong tập ứng viên, SHA lấy từ m4.tep (không nhận hash từ trình duyệt).
    """CREATE OR REPLACE FUNCTION m4.kt_luu(p_khoa text, p_yc jsonb, p_cho uuid, p_phong_bi uuid, p_expected_sha text, p_expected_rev integer,
                                         p_nd jsonb) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE; cuoi m4.kt_xac_nhan%ROWTYPE; moi m4.kt_xac_nhan%ROWTYPE;
                rv integer; ttep uuid; tsha text; th jsonb;
        BEGIN""" + _TIN_CAY + """
            PERFORM m4.kt_khoa(p_cho, 'LUU');
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = p_cho;
            cu := m4._bn_tra(aid, p_khoa, 'KT_LUU', c.du_an_id, p_yc);
            h := m4._kt_hien_hanh(p_cho);""" + _LAP_LAI + _PHONG_BI + f"""
            IF EXISTS (SELECT 1 FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id AND x.loai = 'XAC_NHAN') THEN
                RAISE EXCEPTION 'M4_KT_DA_XAC_NHAN: phong bì nguồn đã được kế toán xác nhận — đính chính là phụ thuộc riêng' {_LOI};
            END IF;
            SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id;
            IF p_expected_rev IS NULL OR p_expected_rev <> rv THEN
                RAISE EXCEPTION 'M4_KT_REVISION_CU: bản KT của phong bì đã có revision mới (hiện tại %) — tải lại', rv {_LOI};
            END IF;
            IF p_nd IS NULL OR jsonb_typeof(p_nd) <> 'object' THEN
                RAISE EXCEPTION 'M4_THAM_SO_SAI: nội dung KT không đúng hình dạng' {_LOI};
            END IF;
            ttep := nullif(p_nd->>'vat_can_cu_tep_id', '')::uuid;
            IF ttep IS NOT NULL THEN
                SELECT t.raw_sha256 INTO tsha FROM m4._kt_tep_can_cu(b.id) t WHERE t.id = ttep;
                IF tsha IS NULL THEN
                    RAISE EXCEPTION 'M4_KT_CAN_CU_VAT_SAI: tệp căn cứ VAT không thuộc hồ sơ/HĐ của nguồn trong phạm vi' {_LOI};
                END IF;
            END IF;
            SELECT * INTO cuoi FROM m4.kt_xac_nhan x WHERE x.cho_id = c.id ORDER BY x.revision DESC LIMIT 1;
            INSERT INTO m4.kt_xac_nhan ({_COT_GHI})
                VALUES (c.id, c.dot_id, c.phap_nhan_id, c.du_an_id, c.hop_dong_id, b.id, b.noi_dung_sha256, b.seal_id, b.phien_ban_id,
                        coalesce(cuoi.revision, 0) + 1, cuoi.id, 'NHAP', NULL, p_nd->>'tien_te',
                        {_ND_TIEN}, p_nd->>'co_so_gia_tri', p_nd->>'vat_trang_thai', ttep, tsha,
                        p_nd->>'vat_trich_dan', p_nd->>'ly_do', ai, aid)
                RETURNING * INTO moi;
            th := m4._kt_thieu(moi, b.noi_dung);
            INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                VALUES (c.du_an_id, c.hop_dong_id, c.dot_id, 'KT_LUU', ai, jsonb_build_object('kt_revision_id', moi.id, 'revision', moi.revision,
                                                                                              'phong_bi_id', b.id, 'so_thieu', jsonb_array_length(th)));
            kq := {_KQ_LUU};"""
    + _KET.format(a="KT_LUU") + """
        END $$""",
    # XÁC NHẬN: đúng revision NHAP mới nhất đã lưu của phong bì hiện hành (CAS id + revision + SHA phong bì), đủ điều kiện → revision XAC_NHAN sao y.
    # Phong bì đã xác nhận: cùng nháp + cùng revision (khóa mới / người khác / đồng thời) → trả CÙNG xác nhận (trung_xac_nhan); khác → 409, không ghi đè.
    """CREATE OR REPLACE FUNCTION m4.kt_xac_nhan_lenh(p_khoa text, p_yc jsonb, p_cho uuid, p_phong_bi uuid, p_expected_sha text, p_kt_rev uuid,
                                                   p_expected_rev integer) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = master, m4, pg_temp AS $$
        DECLARE """ + _KB + """ c m4.duyet_kt_cho%ROWTYPE; b m4.duyet_kt_phong_bi%ROWTYPE; cuoi m4.kt_xac_nhan%ROWTYPE; moi m4.kt_xac_nhan%ROWTYPE;
                n m4.kt_xac_nhan%ROWTYPE; xn m4.kt_xac_nhan%ROWTYPE; rv integer; th jsonb;
        BEGIN""" + _TIN_CAY + """
            PERFORM m4.kt_khoa(p_cho, 'XAC_NHAN');
            SELECT * INTO c FROM m4.duyet_kt_cho WHERE id = p_cho;
            cu := m4._bn_tra(aid, p_khoa, 'KT_XAC_NHAN', c.du_an_id, p_yc);
            h := m4._kt_hien_hanh(p_cho);""" + _LAP_LAI + _PHONG_BI + f"""
            SELECT * INTO xn FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id AND x.loai = 'XAC_NHAN';
            IF xn.id IS NOT NULL THEN
                SELECT * INTO n FROM m4.kt_xac_nhan x WHERE x.id = xn.nhap_id;
                IF n.id IS DISTINCT FROM p_kt_rev OR n.revision IS DISTINCT FROM p_expected_rev THEN
                    RAISE EXCEPTION 'M4_KT_DA_XAC_NHAN: phong bì nguồn đã được xác nhận từ bản KT khác — không ghi đè' {_LOI};
                END IF;
                kq := {_KQ_TRUNG};
            ELSE
                SELECT * INTO n FROM m4.kt_xac_nhan x WHERE x.id = p_kt_rev AND x.phong_bi_id = b.id;
                SELECT coalesce(max(x.revision), 0) INTO rv FROM m4.kt_xac_nhan x WHERE x.phong_bi_id = b.id;
                IF n.id IS NULL OR n.loai <> 'NHAP' OR n.revision <> rv OR p_expected_rev IS NULL OR p_expected_rev <> rv THEN
                    RAISE EXCEPTION 'M4_KT_REVISION_CU: chỉ xác nhận đúng bản KT mới nhất đã lưu của phong bì (hiện tại %) — tải lại', rv {_LOI};
                END IF;
                th := m4._kt_thieu(n, b.noi_dung);
                IF jsonb_array_length(th) > 0 THEN
                    RAISE EXCEPTION 'M4_KT_CHO_BO_SUNG: bản KT chưa đủ điều kiện xác nhận (%)', th::text {_LOI};
                END IF;
                IF n.vat_can_cu_tep_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM m4._kt_tep_can_cu(b.id) t
                                                                    WHERE t.id = n.vat_can_cu_tep_id AND t.raw_sha256 = n.vat_can_cu_sha256) THEN
                    RAISE EXCEPTION 'M4_KT_CAN_CU_VAT_SAI: tệp căn cứ VAT không còn thuộc phạm vi nguồn' {_LOI};
                END IF;
                SELECT * INTO cuoi FROM m4.kt_xac_nhan x WHERE x.cho_id = c.id ORDER BY x.revision DESC LIMIT 1;
                INSERT INTO m4.kt_xac_nhan ({_COT_GHI})
                    VALUES (c.id, c.dot_id, c.phap_nhan_id, c.du_an_id, c.hop_dong_id, b.id, b.noi_dung_sha256, b.seal_id, b.phien_ban_id,
                            coalesce(cuoi.revision, 0) + 1, cuoi.id, 'XAC_NHAN', n.id, {_N_COT}, ai, aid)
                    RETURNING * INTO moi;
                INSERT INTO m4.nhat_ky (du_an_id, hop_dong_id, dot_id, hanh_dong, boi, chi_tiet)
                    VALUES (c.du_an_id, c.hop_dong_id, c.dot_id, 'KT_XAC_NHAN', ai, jsonb_build_object('kt_revision_id', moi.id, 'revision', moi.revision,
                                                                                                       'nhap_id', n.id, 'phong_bi_id', b.id));
                kq := {_KQ_XAC_NHAN};
            END IF;""" + _KET.format(a="KT_XAC_NHAN") + """
        END $$""",
    # --- quyền thực thi + RLS đọc: lệnh/nội bộ KHÔNG cấp; app_web chỉ EXECUTE hàm đọc + SELECT kỹ thuật qua RLS theo quyền KT hiện hành
    "REVOKE EXECUTE ON FUNCTION " + ", ".join((*HAM_LENH, *HAM_NOI_BO, *HAM_DOC)) + " FROM PUBLIC",
    "REVOKE ALL ON m4.kt_xac_nhan FROM PUBLIC",
    "ALTER TABLE m4.kt_xac_nhan ENABLE ROW LEVEL SECURITY",
    """DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web') THEN
            GRANT SELECT ON m4.kt_xac_nhan TO app_web;
            CREATE POLICY kt_xac_nhan_web ON m4.kt_xac_nhan FOR SELECT TO app_web USING (m4.kt_doc_cho(cho_id));
            GRANT EXECUTE ON FUNCTION """ + ", ".join(HAM_DOC) + """ TO app_web;
        END IF;
    END $$""",
)
