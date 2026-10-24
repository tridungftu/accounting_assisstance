"""CRM-41-06A (G6A) — service kế toán kiểm hợp đồng đã ký từ mẫu + kích hoạt HIEU_LUC, trên CHÍNH service G4 (CrmKyKetK2 → CrmGiaoKetK2 → CrmMauK2):
cùng danh tính phiên, kết nối CHỦ BẢNG, giao dịch có GUC danh tính, biên nhận/ghim quyền. Hàm SQL ``CRM_G6A_SQL`` (k2/sql_crm_kiem_hd.py) là nơi
quyết định quyền/phạm vi/CAS/trạng thái/đánh giá lại; service chỉ kiểm dạng yêu cầu, tính digest yêu cầu gốc và đọc tệp kho SAU quyền hiện hành.

- Trình duyệt gửi: ky_id, expected_revision, checklist 5 mục, đối tác + mã Junsky CÓ SẴN, ngày hiệu lực + căn cứ, lý do, check_id + sha256 đồ thị
  đã xem, khóa. KHÔNG actor/PN/trạng thái/kết quả check/chế độ G5/đường dẫn/biên nhận.
- G5: HTTP luôn dùng ``VAN_HANH`` → HOLD ``UNREGISTERED_G5_PROOF`` (chưa có producer/policy/kết quả tin cậy đăng ký). ``SYNTHETIC_FIXTURE`` chỉ
  dựng trực tiếp trong fixture kiểm thử (đặt GUC giao dịch) — KHÔNG phải bằng chứng vận hành/nghiệm thu; trình duyệt không chọn được.
- Trả lại KHÔNG mở khóa/sửa bản ký/PDF G4 và không "về nháp": chỉ chặn phụ thuộc (ký lại = gói kế tiếp).
"""

from __future__ import annotations

import json
import re

from ..ha_tang.primitives import DataError, sha256
from .crm_giao_ket import tinh_bao_gia
from .crm_ky_ket import CrmKyKetK2
from .crm_mau import _chuoi, _h, _khoa, _ngay, _uuid, _v

HANH = "CRM_HD_KIEM"
CHE_DO_G5 = ("VAN_HANH", "SYNTHETIC_FIXTURE")
CHECKLIST = ("ban_ky_dung_ban_xuat", "ben_ky_dung", "dieu_khoan_dung", "gia_tri_lich_dung", "khach_dung")
CHECKLIST_GIA_TRI = ("XAC_NHAN", "CO_VAN_DE")
CAN_CU_NGAY = ("DIEU_KHOAN_HD", "TRUONG_HOP_DONG")
LOAI_LECH = ("G5_LECH", "G7_LECH")
LOAI_TEP = {"ban-ky": "BAN_KY", "g3": "G3_PDF"}
RE_MA_LECH = re.compile(r"[A-Z0-9_]{1,60}(:[0-9]{1,4})?")
RE_SHA = re.compile(r"[0-9a-f]{64}")


def _loi(ma: str, msg: str):
    raise DataError(ma, msg)


def _rev(v) -> int:
    if type(v) is not int or v < 0:
        _loi("CRM_G_YEU_CAU_SAI", "expected_revision phải là số nguyên không âm.")
    return v


def _ly_do(v) -> str:
    v = _chuoi(v, "lý do", 1000)
    if not v.strip() or any(ord(c) < 32 for c in v):
        _loi("CRM_G_YEU_CAU_SAI", "Cần lý do (1–1000 ký tự, không ký tự điều khiển).")
    return v


def chuan_hoa_luu(*, ky_id, expected_revision, checklist, doi_tac_id=None, ma_junsky_id=None, ngay_hieu_luc=None, can_cu_ngay=None,
                  trich_dan_ngay=None, ghi_chu=None, khoa) -> dict:
    """Kiểm dạng lưu kiểm (thuần, không CSDL). Checklist đúng 5 mục; mỗi mục XAC_NHAN/CO_VAN_DE/null (chưa xác nhận — không mặc định đạt)."""
    if not isinstance(checklist, dict) or set(checklist) != set(CHECKLIST):
        _loi("CRM_KIEM_CHECKLIST_SAI", "Checklist phải đúng 5 mục kiểm.")
    if any(v is not None and v not in CHECKLIST_GIA_TRI for v in checklist.values()):
        _loi("CRM_KIEM_CHECKLIST_SAI", "Mỗi mục checklist là Xác nhận / Có vấn đề / chưa chọn.")
    dt = None if doi_tac_id in (None, "") else _uuid(doi_tac_id, "doi_tac_id")
    mj = None if ma_junsky_id in (None, "") else _uuid(ma_junsky_id, "ma_junsky_id")
    if (dt is None) != (mj is None):
        _loi("CRM_KIEM_JUNSKY_SAI", "Chọn khách bằng mã Junsky CÓ SẴN (đối tác + mã cùng lúc) — không tạo mã.")
    ngay = None if ngay_hieu_luc in (None, "") else _ngay(ngay_hieu_luc, "Ngày hiệu lực")
    cc = None if can_cu_ngay in (None, "") else can_cu_ngay
    td = _chuoi(trich_dan_ngay, "trích dẫn căn cứ ngày hiệu lực", 1000, bat_buoc=False)
    if cc is not None and cc not in CAN_CU_NGAY:
        _loi("CRM_G_YEU_CAU_SAI", "Căn cứ ngày hiệu lực không hợp lệ.")
    if td is not None and (not td.strip() or any(ord(c) < 32 for c in td)):
        _loi("CRM_G_YEU_CAU_SAI", "Trích dẫn căn cứ ngày hiệu lực không hợp lệ.")
    if len({ngay is None, cc is None, td is None}) != 1:
        _loi("CRM_KIEM_NGAY_SAI", "Ngày hiệu lực cần đủ ngày + căn cứ + trích dẫn (hoặc để trống cả ba).")
    return {"ky_id": _uuid(ky_id, "ky_id"), "expected_revision": _rev(expected_revision), "checklist": {k: checklist[k] for k in CHECKLIST},
            "doi_tac_id": dt, "ma_junsky_id": mj, "ngay_hieu_luc": ngay, "can_cu_ngay": cc, "trich_dan_ngay": td,
            "ghi_chu": _chuoi(ghi_chu, "ghi chú", 2000, bat_buoc=False), "khoa": _khoa(khoa)}


class CrmKiemHdK2:
    """G6A trên CHÍNH CrmKyKetK2: bản ký đọc ở `giao-ket/ky/<sha>`, PDF G3 ở `giao-ket/tep/<sha>` — chỉ sau quyền hiện hành + nhật ký truy cập."""

    def __init__(self, ky: CrmKyKetK2, *, g5_che_do: str = "VAN_HANH"):
        if g5_che_do not in CHE_DO_G5:
            raise ValueError("g5_che_do")
        self.ky = ky
        self.mau = ky.mau
        self.g5_che_do = g5_che_do  # SYNTHETIC_FIXTURE: chỉ fixture dựng trực tiếp; HTTP factory luôn VAN_HANH

    # ------------------------------------------------------------------ hạ tầng
    def _mo(self, c) -> None:
        if self.g5_che_do == "SYNTHETIC_FIXTURE":  # GUC cục bộ giao dịch; vận hành không bao giờ đặt
            c.execute("SELECT set_config('ktt.crm_kiem_g5', 'SYNTHETIC_FIXTURE', true)").fetchone()

    def _lenh(self, dang_nhap: str, sql: str, tham_so: tuple) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:  # READ COMMITTED: hàm lệnh ghim quyền/phạm vi rồi khóa biên nhận/hồ sơ
            self._mo(c)
            r = _v(dict(c.execute(sql, tham_so).fetchone()))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    # ------------------------------------------------------------------ đọc
    def ds(self, dang_nhap: str) -> list:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            return _v(dict(c.execute("SELECT master.crm_kiem_ds() AS r").fetchone()))["r"]

    def doc(self, dang_nhap: str, ky_id) -> dict:
        """Bản ký + căn cứ + đánh giá hiện hành (PII che, nhật ký truy cập) theo quyền HIỆN HÀNH. Tóm tắt báo giá chỉ để hiển thị đối chiếu."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            self._mo(c)
            d = _v(dict(c.execute("SELECT master.crm_kiem_doc(%s::uuid, %s) AS r", (_uuid(ky_id, "ky_id"), self.g5_che_do)).fetchone()))["r"]
        bg = d.pop("_bao_gia", None)
        if isinstance(bg, dict):
            t = tinh_bao_gia(bg, None)
            d["tom_tat"] = {"so_dong": len(t["dong"]), "tong_minor": t["tong_minor"], "tien_te": t["tien_te"]}
        d["g5_che_do"] = self.g5_che_do
        return d

    def tep(self, dang_nhap: str, ky_id, loai: str) -> tuple[str, bytes, str]:
        """PDF bản ký / PDF G3: quyền + phạm vi hiện hành + nhật ký TRƯỚC tra hash/kho; kiểm lại hash/độ dài; tên do máy chủ đặt."""
        lt = LOAI_TEP.get(loai)
        if lt is None:
            _loi("CRM_G_YEU_CAU_SAI", "Loại tệp không hợp lệ.")
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            x = _v(dict(c.execute("SELECT master.crm_kiem_tep(%s::uuid, %s) AS r", (_uuid(ky_id, "ky_id"), lt)).fetchone()))["r"]
        sha, dai = str(x["sha256"]), x["len"]
        p = (self.ky.kho_ky if lt == "BAN_KY" else self.ky.gk.kho / "tep") / sha
        if not RE_SHA.fullmatch(sha) or not p.is_file():
            _loi("CRM_G_TEP_KHONG_CO", "Tệp không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != sha or len(raw) != int(dai):
            _loi("CRM_G_TEP_HONG", "Tệp trong kho khác hash đã ghi — không trả.")
        ten = re.sub(r"[^A-Za-z0-9_.-]", "_", str(x["ten"] or "hop-dong"))[:80] or "hop-dong"
        return f"{ten}-r{x['revision']}-{'ban-ky' if lt == 'BAN_KY' else 'g3'}.pdf", raw, "application/pdf"

    def tim_junsky(self, dang_nhap: str, ky_id, tu_khoa) -> dict:
        """P1-B: khách DỰ THẢO (bản ký + HĐ chưa có đối tác) — tra mã Junsky CÓ SẴN cùng PN theo quyền lệnh + phạm vi hiện hành (SQL kiểm trước
        tra cứu, che PII, nhật ký). Không tạo mã/đối tác; khách đã định danh → CRM_KIEM_KHACH_DA_DINH."""
        kid = _uuid(ky_id, "ky_id")
        if not isinstance(tu_khoa, str) or not 3 <= len(tu_khoa.strip()) <= 60 or any(ord(c) < 32 for c in tu_khoa):
            _loi("CRM_G_YEU_CAU_SAI", "Từ khóa tìm mã Junsky 3–60 ký tự.")
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            return _v(dict(c.execute("SELECT master.crm_kiem_tim_junsky(%s::uuid, %s) AS r", (kid, tu_khoa)).fetchone()))["r"]

    # ------------------------------------------------------------------ lệnh
    def luu(self, dang_nhap: str, *, ky_id, expected_revision, checklist, doi_tac_id=None, ma_junsky_id=None, ngay_hieu_luc=None, can_cu_ngay=None,
            trich_dan_ngay=None, ghi_chu=None, khoa) -> dict:
        y = chuan_hoa_luu(ky_id=ky_id, expected_revision=expected_revision, checklist=checklist, doi_tac_id=doi_tac_id, ma_junsky_id=ma_junsky_id,
                          ngay_hieu_luc=ngay_hieu_luc, can_cu_ngay=can_cu_ngay, trich_dan_ngay=trich_dan_ngay, ghi_chu=ghi_chu, khoa=khoa)
        h = _h("CRM_KIEM_LUU", {k: v for k, v in y.items() if k != "khoa"})
        return self._lenh(dang_nhap, """SELECT master.crm_kiem_luu(%s, %s, %s::uuid, %s, %s::jsonb, %s::uuid, %s::uuid, %s::date, %s, %s, %s) AS r""",
                          (y["khoa"], h, y["ky_id"], y["expected_revision"], json.dumps(y["checklist"]), y["doi_tac_id"], y["ma_junsky_id"],
                           y["ngay_hieu_luc"], y["can_cu_ngay"], y["trich_dan_ngay"], y["ghi_chu"]))

    def check(self, dang_nhap: str, *, ky_id, expected_revision, khoa) -> dict:
        kid, rev, khoa = _uuid(ky_id, "ky_id"), _rev(expected_revision), _khoa(khoa)
        h = _h("CRM_KIEM_CHECK", {"ky_id": kid, "expected_revision": rev, "g5_che_do": self.g5_che_do})
        return self._lenh(dang_nhap, "SELECT master.crm_kiem_chay_check(%s, %s, %s::uuid, %s, %s) AS r", (khoa, h, kid, rev, self.g5_che_do))

    def xu_ly_lech(self, dang_nhap: str, *, ky_id, expected_revision, loai, muc_tieu_id, ma_lech, ly_do, khoa) -> dict:
        kid, rev, khoa, ld = _uuid(ky_id, "ky_id"), _rev(expected_revision), _khoa(khoa), _ly_do(ly_do)
        if loai not in LOAI_LECH:
            _loi("CRM_G_YEU_CAU_SAI", "Loại lệch không hợp lệ.")
        if not isinstance(ma_lech, str) or not RE_MA_LECH.fullmatch(ma_lech):
            _loi("CRM_G_YEU_CAU_SAI", "Mã lệch không hợp lệ.")
        mt = _uuid(muc_tieu_id, "muc_tieu_id")
        h = _h("CRM_KIEM_XU_LY_LECH", {"ky_id": kid, "expected_revision": rev, "loai": loai, "muc_tieu_id": mt, "ma_lech": ma_lech, "ly_do": ld})
        return self._lenh(dang_nhap, "SELECT master.crm_kiem_xu_ly_lech(%s, %s, %s::uuid, %s, %s, %s::uuid, %s, %s) AS r",
                          (khoa, h, kid, rev, loai, mt, ma_lech, ld))

    def bo_sung(self, dang_nhap: str, *, ky_id, expected_revision, ly_do, khoa) -> dict:
        kid, rev, khoa, ld = _uuid(ky_id, "ky_id"), _rev(expected_revision), _khoa(khoa), _ly_do(ly_do)
        h = _h("CRM_KIEM_BO_SUNG", {"ky_id": kid, "expected_revision": rev, "ly_do": ld})
        return self._lenh(dang_nhap, "SELECT master.crm_kiem_bo_sung(%s, %s, %s::uuid, %s, %s) AS r", (khoa, h, kid, rev, ld))

    def tra_lai(self, dang_nhap: str, *, ky_id, expected_revision, ly_do, khoa) -> dict:
        """Chặn phụ thuộc — KHÔNG mở khóa/sửa bản ký/PDF G4, không về nháp (g4_trang_thai trả về vẫn DA_KY)."""
        kid, rev, khoa, ld = _uuid(ky_id, "ky_id"), _rev(expected_revision), _khoa(khoa), _ly_do(ly_do)
        h = _h("CRM_KIEM_TRA_LAI", {"ky_id": kid, "expected_revision": rev, "ly_do": ld})
        return self._lenh(dang_nhap, "SELECT master.crm_kiem_tra_lai(%s, %s, %s::uuid, %s, %s) AS r", (khoa, h, kid, rev, ld))

    def hieu_luc(self, dang_nhap: str, *, ky_id, expected_revision, check_id, do_thi_sha256, khoa) -> dict:
        """Kích hoạt nguyên tử theo ĐÚNG lần check đã xem (check_id + sha256 đồ thị); máy chủ đánh giá lại tại chỗ, lệch → CRM_KIEM_CHECK_CU."""
        kid, rev, khoa, cid = _uuid(ky_id, "ky_id"), _rev(expected_revision), _khoa(khoa), _uuid(check_id, "check_id")
        if not isinstance(do_thi_sha256, str) or not RE_SHA.fullmatch(do_thi_sha256):
            _loi("CRM_G_YEU_CAU_SAI", "Thiếu sha256 đồ thị check.")
        h = _h("CRM_KIEM_HIEU_LUC", {"ky_id": kid, "expected_revision": rev, "check_id": cid, "do_thi_sha256": do_thi_sha256,
                                     "g5_che_do": self.g5_che_do})
        return self._lenh(dang_nhap, "SELECT master.crm_kiem_hieu_luc(%s, %s, %s::uuid, %s, %s::uuid, %s, %s) AS r",
                          (khoa, h, kid, rev, cid, do_thi_sha256, self.g5_che_do))
