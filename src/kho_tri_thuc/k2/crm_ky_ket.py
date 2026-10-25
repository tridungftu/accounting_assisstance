"""CRM-41-04A — service G4 ký lần đầu (hẹp) trên CHÍNH service G2/G3 (CrmGiaoKetK2 → CrmMauK2): cùng danh tính phiên, kết nối CHỦ BẢNG, giao dịch có
GUC danh tính, biên nhận/ghim quyền M0018, kho bất biến write_immutable. Hàm SQL M0023 là nơi quyết định quyền/phạm vi/CAS/trạng thái/khóa sau ký.

- Trình duyệt gửi: soan_id, expected_revision, expected_xuat_id (bản xuất có DOCX của revision hiện hành dialog đã chụp — QD-20261025-27 ký trên
  DOCX, PDF G3 nếu có chỉ tham khảo và phải khớp), PDF bản ký (raw), tên tệp thuần, ngày ký, co_sua
  (boolean bắt buộc — false là khai Không hợp lệ), mô tả khi Có, người ký phía khách (tùy chọn), khóa. KHÔNG actor/PN/trạng thái/hash/đường dẫn/biên nhận.
- Thứ tự: kiểm dạng yêu cầu → quyền + phạm vi HIỆN HÀNH (giao dịch ngắn) → parse PDF (pypdfium2, cấu trúc + có trang; scan nhận, hỏng/mã hóa
  fail closed; không OCR/so nội dung) → MỘT giao dịch: ghim quyền/phạm vi + biên nhận → căn cứ G3 do máy chủ resolve (hash/độ dài tệp G3 + input
  lineage + mẫu đã ghim kiểm lại) → ghi PDF bản ký bất biến TRƯỚC commit → hàm lệnh crm_ky_ket (bản ký + G5 khởi tạo + DA_KY + nhật ký + biên nhận).
- Ngày ký KHÔNG là ngày hiệu lực; khai Có KHÔNG là đã trích/đã duyệt. Không G5 thực thi, không G6, không correction/ký lại, không engine.
"""

from __future__ import annotations

import json
import re

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable
from .crm_giao_ket import CrmGiaoKetK2, tinh_bao_gia
from .crm_mau import _chuoi, _h, _khoa, _ngay, _uuid, _v

HANH = "CRM_KY_KET"
HANH_DOC = "CRM_KY_DOC"  # action hẹp đọc bản ký (KT/KTT/CFO) trên master.phan_cong_hanh_dong + phạm vi crm_ky_pham_vi — chỉ quản trị cấp, không tự cấp
TEP_KY_TOI_DA = 50 * 1024 * 1024  # cùng cap tệp tải lên của máy chủ (giao_dien/intake.MAX_FILE_SIZE)
HIEN_THI_DA_KY = "Đã ký — chờ kế toán kiểm"
MUC_DICH_TAI = "TAI_BAN_KY"
# QD-20261025-27 (M0035): lần xuất đã công bố của đúng revision luôn có DOCX đã kiểm → ký được ở mọi trạng thái PDF; DA_CU (revision cũ/đã ký) không.
XUAT_KY_DUOC = frozenset({"PDF_DAT", "PDF_CHUA_SAN_SANG", "PDF_LOI"})


def _loi(ma: str, msg: str):
    raise DataError(ma, msg)


def kiem_pdf_ky(raw) -> int:
    """PDF bản ký: chữ ký `%PDF-` + mở được bằng PDFium (parser sẵn có của crm_docx) + có ít nhất một trang tải được. Trả số trang.
    Scan không có lớp chữ VẪN hợp lệ (G4 không OCR, không so nội dung với bản sinh). Hỏng/mã hóa cần mật khẩu/không trang → CRM_KY_PDF_HONG."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        _loi("CRM_KY_PDF_RONG", "Chưa có tệp PDF bản ký.")
    if len(raw) > TEP_KY_TOI_DA:
        _loi("CRM_KY_TEP_QUA_LON", f"PDF bản ký tối đa {TEP_KY_TOI_DA // (1024 * 1024)} MB.")
    raw = bytes(raw)
    if not raw.startswith(b"%PDF-"):
        _loi("CRM_KY_PDF_HONG", "Tệp không phải PDF (đuôi .pdf chưa đủ).")
    try:
        import pypdfium2 as pdfium
    except ImportError:
        _loi("CRM_KY_PDF_CHUA_KIEM_DUOC", "Máy chủ thiếu bộ đọc PDF — không nhận bản ký chưa kiểm được.")
    try:
        pdf = pdfium.PdfDocument(raw)
        try:
            n = len(pdf)
            if n < 1:
                raise ValueError("không có trang")
            trang = pdf[0]
            trang.close()
        finally:
            pdf.close()
    except Exception:  # noqa: BLE001 — mọi lỗi parse/mã hóa/trang → fail closed, không lộ chi tiết
        _loi("CRM_KY_PDF_HONG", "PDF bản ký hỏng, đã mã hóa hoặc không có trang đọc được — không nhận.")
    return n


def _ten_pdf(v) -> str:
    v = _chuoi(v, "tên tệp", 200)
    if (v != v.strip() or len(v) < 5 or any(c in v for c in '/\\:*?"<>|') or any(ord(c) < 32 for c in v) or not v.lower().endswith(".pdf")
            or v in (".", "..")):
        _loi("CRM_G_YEU_CAU_SAI", "Tên tệp bản ký phải là .pdf, không đường dẫn/ký tự đặc biệt.")
    return v


def chuan_hoa(*, soan_id, expected_revision, expected_xuat_id, ten_tep, ngay_ky, co_sua, mo_ta=None, nguoi_ky_khach=None, khoa) -> dict:
    """Kiểm dạng yêu cầu (thuần, không CSDL). co_sua phải là bool THẬT: thiếu/null/chuỗi/số → CRM_KY_KHAI_SAI; False = khai Không hợp lệ."""
    sid, xid, khoa = _uuid(soan_id, "soan_id"), _uuid(expected_xuat_id, "expected_xuat_id"), _khoa(khoa)
    if type(expected_revision) is not int or expected_revision < 1:
        _loi("CRM_G_YEU_CAU_SAI", "expected_revision phải là số nguyên dương.")
    if type(co_sua) is not bool:
        _loi("CRM_KY_KHAI_SAI", "Phải chọn Có hoặc Không cho câu hỏi bản ký có sửa so với bản xuất.")
    mo_ta = _chuoi(mo_ta, "mô tả sửa", 2000, bat_buoc=False)
    if co_sua and (mo_ta is None or not mo_ta.strip()):
        _loi("CRM_KY_KHAI_SAI", "Khai Có cần mô tả nội dung đã sửa.")
    if not co_sua and mo_ta is not None:
        _loi("CRM_KY_KHAI_SAI", "Khai Không thì không gửi mô tả sửa.")
    nguoi = _chuoi(nguoi_ky_khach, "người ký phía khách", 200, bat_buoc=False)
    if nguoi is not None and (not nguoi.strip() or "\n" in nguoi or "\t" in nguoi):
        _loi("CRM_G_YEU_CAU_SAI", "Người ký phía khách không hợp lệ.")
    return {"soan_id": sid, "expected_revision": expected_revision, "expected_xuat_id": xid, "ten_tep": _ten_pdf(ten_tep),
            "ngay_ky": _ngay(ngay_ky, "Ngày ký"), "co_sua": co_sua, "mo_ta": mo_ta, "nguoi_ky_khach": nguoi, "khoa": khoa}


def _tom_tat(bao_gia: dict) -> dict:
    """Snapshot số dòng/tổng/tiền tệ của revision đã xuất (cùng phép tính G2/G3, số nguyên đơn vị nhỏ nhất)."""
    t = tinh_bao_gia(bao_gia, None)
    return {"so_dong": len(t["dong"]), "tong_minor": t["tong_minor"], "tien_te": t["tien_te"]}


class CrmKyKetK2:
    """G4 ký lần đầu trên CHÍNH CrmGiaoKetK2 (kho `giao-ket/`): bản G3 đọc ở `giao-ket/tep/<sha>`, bản ký ghi ở `giao-ket/ky/<sha>`."""

    def __init__(self, gk: CrmGiaoKetK2):
        self.gk = gk
        self.mau = gk.mau
        self.kho_ky = gk.kho / "ky"

    # ------------------------------------------------------------------ hạ tầng
    def kiem_quyen(self, dang_nhap: str, soan_id) -> None:
        """Preflight quyền + phạm vi ký HIỆN HÀNH (giao dịch ngắn, không biên nhận, không ghi) — gọi TRƯỚC khi parse bytes PDF."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            c.execute("SELECT master.crm_ky_tra(NULL, %s::uuid, NULL) AS r", (_uuid(soan_id, "soan_id"),)).fetchone()

    def _doc_g3(self, sha, dai) -> bytes:
        p = self.gk.kho / "tep" / str(sha)
        if not re.fullmatch(r"[0-9a-f]{64}", str(sha or "")) or not p.is_file():
            _loi("CRM_KY_G3_LECH", "Tệp G3 của bản xuất không có trong kho — không ký trên căn cứ thiếu.")
        raw = p.read_bytes()
        if sha256(raw) != sha or len(raw) != int(dai):
            _loi("CRM_KY_G3_LECH", "Tệp G3 trong kho khác hash/độ dài đã công bố — không ký.")
        return raw

    # ------------------------------------------------------------------ lệnh ký lần đầu
    def ky(self, dang_nhap: str, raw, *, soan_id, expected_revision, expected_xuat_id, ten_tep, ngay_ky, co_sua, mo_ta=None, nguoi_ky_khach=None,
           khoa, so_trang: int | None = None) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        y = chuan_hoa(soan_id=soan_id, expected_revision=expected_revision, expected_xuat_id=expected_xuat_id, ten_tep=ten_tep, ngay_ky=ngay_ky,
                      co_sua=co_sua, mo_ta=mo_ta, nguoi_ky_khach=nguoi_ky_khach, khoa=khoa)
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            _loi("CRM_KY_PDF_RONG", "Chưa có tệp PDF bản ký.")
        if len(raw) > TEP_KY_TOI_DA:
            _loi("CRM_KY_TEP_QUA_LON", f"PDF bản ký tối đa {TEP_KY_TOI_DA // (1024 * 1024)} MB.")
        raw = bytes(raw)
        if so_trang is None:  # gọi trực tiếp service: quyền TRƯỚC parse bytes (HTTP đã preflight + parse ngoài mutation lock)
            self.kiem_quyen(dang_nhap, y["soan_id"])
            so_trang = kiem_pdf_ky(raw)
        sha, dai = sha256(raw), len(raw)
        h = _h(HANH, {"soan_id": y["soan_id"], "expected_revision": y["expected_revision"], "expected_xuat_id": y["expected_xuat_id"],
                      "ky_pdf_sha256": sha, "ky_pdf_len": dai, "ten_tep": y["ten_tep"], "ngay_ky": y["ngay_ky"], "co_sua": y["co_sua"],
                      "mo_ta": y["mo_ta"], "nguoi_ky_khach": y["nguoi_ky_khach"]})
        # MỘT giao dịch READ COMMITTED: ghim quyền/phạm vi + khóa namespace biên nhận giữ tới FINAL; mọi đọc căn cứ/kho SAU quyền hiện hành.
        with m._tx(dt) as c:
            cu = _v(dict(c.execute("SELECT master.crm_ky_tra(%s, %s::uuid, %s) AS r", (y["khoa"], y["soan_id"], h)).fetchone()))["r"]
            if cu is not None:
                return {**cu["ket_qua"], "lap_lai": True}
            x = m._mot(c, """SELECT x.id, x.revision, x.trang_thai, x.input_sha256, x.docx_sha256, x.docx_len, x.pdf_sha256, x.pdf_len, x.engine,
                                    r.du_lieu, r.du_lieu_sha256, r.raw_sha256, r.ban_do_sha256, r.danh_muc_digest, r.profile_sha256
                             FROM master.crm_gk_xuat x JOIN master.crm_hd_soan_rev r ON r.soan_id = x.soan_id AND r.revision = x.revision
                             WHERE x.id = %s::uuid AND x.soan_id = %s::uuid AND x.loai = 'HOP_DONG'""", (y["expected_xuat_id"], y["soan_id"]))
            if x is None:
                _loi("CRM_KY_XUAT_CU", "Bản xuất đã chụp không thuộc bản soạn này — tải lại căn cứ.")
            if x["trang_thai"] not in XUAT_KY_DUOC or not x["docx_sha256"]:
                _loi("CRM_KY_XUAT_CHUA_DAT", "Bản xuất đã chụp chưa có DOCX của revision hiện hành — chưa ký được.")
            self._doc_g3(x["docx_sha256"], x["docx_len"])  # DOCX = căn cứ ký (QD-27)
            if x["pdf_sha256"] is not None or x["pdf_len"] is not None:  # PDF G3 chỉ tham khảo: có thì phải khớp kho
                self._doc_g3(x["pdf_sha256"], x["pdf_len"])
            m.mau_ghim_trong(c, y["soan_id"], x["revision"])  # mẫu ĐÃ GHIM còn đúng raw/hash/bản đồ (lỗi → không ký)
            input_sha = sha256(canonical_json({"soan_id": y["soan_id"], "revision": x["revision"], "du_lieu_sha256": x["du_lieu_sha256"],
                                               "raw_sha256": x["raw_sha256"], "ban_do_sha256": x["ban_do_sha256"],
                                               "danh_muc_digest": x["danh_muc_digest"], "profile_sha256": x["profile_sha256"],
                                               "renderer": x["engine"]}).encode("utf-8"))
            if input_sha != x["input_sha256"]:
                _loi("CRM_KY_G3_LECH", "Input lineage của bản xuất không khớp revision đã ghim — không ký.")
            tom_tat = _tom_tat(x["du_lieu"]["bao_gia"])
            # TRƯỚC commit; lỗi/rollback sau đó vẫn giữ raw (không cleanup). Bản ký lưu ở `ky/` (vai trò bằng chứng ký), tách khỏi G3 `tep/`:
            # bytes trùng bản xuất vẫn là bằng chứng riêng (ID/hash/độ dài riêng) — hash/bytes không chứng minh chữ ký xác thực.
            write_immutable(self.kho_ky / sha, raw)
            r =_v(dict(c.execute("""SELECT master.crm_ky_ket(%s, %s, %s::uuid, %s, %s::uuid, %s, %s, %s::bigint, %s, %s::bigint, %s, %s, %s::date, %s,
                                                              %s, %s, %s::jsonb) AS r""",
                                  (y["khoa"], h, y["soan_id"], y["expected_revision"], y["expected_xuat_id"], input_sha, x["pdf_sha256"], x["pdf_len"],
                                   sha, dai, so_trang, y["ten_tep"], y["ngay_ky"], y["co_sua"], y["mo_ta"], y["nguoi_ky_khach"],
                                   json.dumps(tom_tat, ensure_ascii=False))).fetchone()))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    # ------------------------------------------------------------------ đọc
    def doc(self, dang_nhap: str, soan_id) -> dict:
        """Điều kiện/căn cứ dialog + bản ký + lịch sử theo quyền HIỆN HÀNH (giao dịch RR). Người không đọc được bản ký chỉ nhận trạng thái/quyền.
        Đọc chi tiết: người ký trong phạm vi, hoặc KT/KTT/CFO có phân công hẹp CRM_KY_DOC + phạm vi tường minh hiện hành (M0023 crm_ky_doc_duoc)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            d = _v(dict(c.execute("SELECT master.crm_ky_doc(%s::uuid) AS r", (_uuid(soan_id, "soan_id"),)).fetchone()))["r"]
        cc = d.get("can_cu")
        if cc is not None:
            bg = cc.pop("_bao_gia", None)  # chỉ để tính snapshot; không trả dữ liệu khách qua khối căn cứ
            cc["tom_tat"] = (d.get("ban_ky") or {}).get("tom_tat") or (_tom_tat(bg) if isinstance(bg, dict) else None)
        return d

    def tep(self, dang_nhap: str, ky_id) -> tuple[str, bytes, str]:
        """Tải PDF bản ký: quyền đọc hiện hành + nhật ký truy cập TRƯỚC tra hash/kho; kiểm lại hash/độ dài; tên tải do máy chủ đặt (không tên gốc)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            x = _v(dict(c.execute("SELECT master.crm_ky_tep(%s::uuid, %s) AS r", (_uuid(ky_id, "ky_id"), MUC_DICH_TAI)).fetchone()))["r"]
        sha, dai = x["sha256"], x["len"]
        p = self.kho_ky / str(sha)
        if not re.fullmatch(r"[0-9a-f]{64}", str(sha)) or not p.is_file():
            _loi("CRM_G_TEP_KHONG_CO", "PDF bản ký không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != sha or len(raw) != int(dai):
            _loi("CRM_G_TEP_HONG", "PDF bản ký trong kho khác hash đã ghi — không trả.")
        ten = re.sub(r"[^A-Za-z0-9_.-]", "_", str(x["ten"] or "hop-dong"))[:80] or "hop-dong"
        return f"{ten}-r{x['revision']}-ban-ky.pdf", raw, "application/pdf"
