"""M4-04A — dịch vụ tạo nháp Request thanh toán từ hồ sơ đợt ĐÃ SEAL: intent bền vững 2 pha + tạo nháp → đọc trạng thái thật → tải PDF đã seal →
đối soát bytes sạch. Compose XayDungK2 (danh tính/GUC/kết nối app + chủ bảng) và DuyetDot (DTO seal, pdf_tai có kiểm quyền trước/sau blob).

Luồng một lệnh `tao` (hoặc `doi_soat`), mỗi bước đi qua m4.request_giu → I/O ngoài giao dịch → m4.request_ghi:
  quyền hiện hành → cấu hình (thiếu → CHUA_CAU_HINH, không biên nhận/mạng) → seal DA_SEAL → snapshot nhóm/danh mục Request → canonical
  → TAO (POST, Idempotency-Key cố định `m4-request:<intent>`) → DOC (GET chi tiết: draft/nhóm/người đứng tên/số tiền/pháp nhân/trường)
  → TAI (PDF seal đúng SHA/độ dài, multipart vào ô tệp đã cấu hình) → DOI_SOAT (metadata; chỉ clean mới tải bytes, SHA/độ dài khớp DUY NHẤT).
- Số tiền: seal.so_lieu.so_xin_thanh_toan + tien_te đúng chuỗi; KHÔNG gia_tri_nt, không trừ tạm ứng/thu hồi/giữ lại, không VAT/FX/AP.
- Người đứng tên: mapping máy chủ (m4.request_anh_xa) của CHÍNH người bấm, khác chủ khóa API; không lấy từ trình duyệt/email/tên.
- Mất ACK: TAO → CHUA_RO_TAO (gửi lại ĐÚNG key + body trong cửa sổ 20h; quá hạn → HOLD); TAI → CHUA_RO_TAI (chỉ đối soát, không tải lại mù).
- Lệch nhóm/trường/phiên bản/người tạo/số tiền, Request không còn draft, quét pending/error/infected, hash lệch/trùng → giữ trạng thái/HOLD rõ.
- Quyền kiểm trong CSDL trước mỗi bước (request_kiem) và sau I/O (request_ghi trả quyen_con): mất quyền → bằng chứng đã ghi, trả lỗi phạm vi.
- KHÔNG gửi/duyệt/từ chối/trả lại/xóa Request, không AP/KT; Request bị trả lại/từ chối không đụng nhánh kế toán.
"""

from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from ..ha_tang.primitives import DataError, canonical_json, sha256
from . import duyet_dot as DD
from . import request_api as RA
from .sql_request_nhap import TRANG_THAI

SCHEMA = "m4.request.nhap/1"
LEASE_GIAY = 180  # > tổng timeout một bước HTTP (kết nối + đọc) của transport; lease hết hạn chưa ghi = chưa rõ
BUOC_TOI_DA = 8
HANH_TAO, HANH_DOI_SOAT = "REQUEST_TAO", "REQUEST_DOI_SOAT"
# lỗi tạo nháp CHẮC CHẮN chưa tạo (nguồn trả trước khi xử lý / chưa gửi được)
TAO_CHUA_GUI = ("REQUEST_KET_NOI", "REQUEST_429", "REQUEST_503", "REQUEST_TRANSPORT_TAT")
TAI_CHUA_GUI = ("REQUEST_KET_NOI", "REQUEST_429", "REQUEST_503", "REQUEST_TRANSPORT_TAT")
DTO_COT = ("id", "trang_thai", "hold_ma", "nhanh", "parent_id", "seal_id", "phien_ban_id", "so_tien", "tien_te", "nhom", "nhom_phien_ban",
           "remote_id", "remote_ma", "remote_trang_thai", "remote_tep_id", "tep_trang_thai_quet", "co_chua_ro", "so_lan_tao", "so_lan_tai",
           "lan_tao_dau", "pdf_sha256", "pdf_byte_length", "doi_soat_sha256", "revision", "tao_luc", "cap_nhat_luc")
MA_HTTP = {  # mã lỗi service → HTTP (wrapper dùng)
    403: frozenset({"M4_REQUEST_PHAM_VI", "M4_REQUEST_PHAM_VI_DA_DOI", "M4_REQUEST_NGUOI_KHAC", "M4_DANH_TINH", "M4_CHI_MAY_CHU_NGUON", "M4_CHI_CHU",
                    "M4_DUYET_PHAM_VI", "M4_CLIENT_AUTHORITY"}),
    404: frozenset({"M4_REQUEST_KHONG_THAY", "M4_DUYET_KHONG_THAY", "M4_REQUEST_CHUA_CO_Y_DINH", "NOT_FOUND"}),
    409: frozenset({"M4_IDEMPOTENCY_KHAC", "M4_REQUEST_DANG_XU_LY", "M4_REQUEST_LEASE_MAT", "M4_REQUEST_CHUA_SEAL", "M4_REQUEST_PHIEN_BAN_CU",
                    "M4_REQUEST_NGUON_LECH", "M4_REQUEST_REMOTE_ID_KHAC", "M4_REQUEST_CHUYEN_SAI", "M4_REQUEST_THIEU_SO_TIEN", "M4_TEP_HONG_LUU_TRU",
                    "M4_REQUEST_CHUA_ANH_XA", "M4_REQUEST_CANONICAL_SAI", "M4_REQUEST_BANG_CHUNG_KHAC"}),
    503: frozenset({"M4_KET_QUA_CHUA_RO", "M4_CHUA_SAN_SANG_GHI_NGUON", "PG_KHONG_KET_NOI", "CRM_CHUA_CAU_HINH"}),
}


@dataclass(frozen=True)
class CauHinhRequest:
    """Cấu hình máy chủ (không bí mật). Khóa API nằm trong transport. Thiếu bất kỳ mục nào → CHUA_CAU_HINH trước biên nhận/mạng."""
    origin: str | None = None
    khoa_ref: str | None = None  # tham chiếu định danh khóa API (không phải khóa) — đổi khóa = đổi khoa_ref → không gửi lại POST cũ
    khoa_chu_dang_nhap: str | None = None  # người chịu trách nhiệm khóa API — phải KHÁC người đứng tên
    nhom: str | None = None
    phien_ban: int | None = None
    truong_tien: str | None = None
    truong_phap_nhan: str | None = None
    truong_tep: str | None = None
    danh_muc_phap_nhan: str | None = None
    phap_nhan_ma: dict = field(default_factory=dict)  # {phap_nhan_id: mã giá trị danh mục pháp nhân bên Request}
    luu_giu_da_kiem: bool = False  # Root đã xác minh no-delete/quarantine của nhánh infected (attachments.ts) trên nguồn/deployment

    def thieu(self) -> list:
        t = [k for k in ("origin", "khoa_ref", "khoa_chu_dang_nhap", "nhom", "truong_tien", "truong_phap_nhan", "truong_tep", "danh_muc_phap_nhan")
             if not isinstance(getattr(self, k), str) or not getattr(self, k)]
        if isinstance(self.phien_ban, bool) or not isinstance(self.phien_ban, int) or self.phien_ban < 1:
            t.append("phien_ban")
        if not isinstance(self.phap_nhan_ma, dict) or not self.phap_nhan_ma:
            t.append("phap_nhan_ma")
        if isinstance(self.khoa_ref, str) and self.khoa_ref and not all(c.isalnum() or c in "_.:-" for c in self.khoa_ref):
            t.append("khoa_ref")
        for k in ("nhom", "truong_tien", "truong_phap_nhan", "truong_tep", "danh_muc_phap_nhan"):
            v = getattr(self, k)
            if isinstance(v, str) and v and not RA.MA_RE.fullmatch(v):
                t.append(k)
        if self.luu_giu_da_kiem is not True:
            t.append("luu_giu_tep_nhiem")
        return sorted(set(t))

    def sha256(self) -> str:
        return sha256(canonical_json({"origin": self.origin, "khoa_ref": self.khoa_ref, "khoa_chu": (self.khoa_chu_dang_nhap or "").casefold(),
                                      "nhom": self.nhom, "phien_ban": self.phien_ban, "truong_tien": self.truong_tien,
                                      "truong_phap_nhan": self.truong_phap_nhan, "truong_tep": self.truong_tep,
                                      "danh_muc_phap_nhan": self.danh_muc_phap_nhan,
                                      "phap_nhan_ma": {str(k): v for k, v in sorted((self.phap_nhan_ma or {}).items())}}).encode("utf-8"))


def _uuid(v, ten: str) -> str:
    return DD._uuid(v, ten)


def _json_hoa(v):
    """Giá trị hàng CSDL (uuid/timestamptz/numeric) → kiểu JSON cho DTO (canonical_json của máy chủ không nhận uuid/datetime)."""
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def tieu_de(so_hop_dong, so_dot) -> str:
    """Tiêu đề xác định (cùng hồ sơ → cùng chuỗi), ≤200 ký tự, không ký tự điều khiển."""
    s = f"Thanh toán HĐ {so_hop_dong} — đợt {so_dot}"
    s = "".join(c if ord(c) >= 32 else " " for c in s).strip()
    return s[:200]


def dau_van_nhom(nhom: RA.NhomRequest) -> str:
    return sha256(canonical_json({"ma": nhom.ma, "phien_ban": nhom.phien_ban, "truong_tong_tien": nhom.truong_tong_tien,
                                  "truong_phap_nhan": nhom.truong_phap_nhan,
                                  "truong": sorted((t.dau_van() for t in nhom.truong), key=lambda x: x["ma"])}).encode("utf-8"))


def kiem_nhom(ch: CauHinhRequest, nhom: RA.NhomRequest | None) -> list:
    """Snapshot nhóm đã quan sát phải khớp cấu hình: đúng phiên bản ban hành, ô tiền/pháp nhân/tệp tồn tại đúng kiểu. Trả danh sách mã lệch.
    Nhóm thanh toán PHẢI khai báo tường minh truongTongTien/truongPhapNhan đúng ô đã cấu hình (thiếu/None/rỗng/khác → lệch, không tự chọn ô thay)."""
    if nhom is None:
        return ["NHOM_KHONG_THAY"]
    lech = []
    if nhom.phien_ban != ch.phien_ban:
        lech.append("NHOM_PHIEN_BAN_DOI")
    tt, pn, tep = nhom.truong_theo_ma(ch.truong_tien), nhom.truong_theo_ma(ch.truong_phap_nhan), nhom.truong_theo_ma(ch.truong_tep)
    if tt is None or tt.kieu != "number" or nhom.truong_tong_tien != ch.truong_tien:
        lech.append("TRUONG_TIEN_LECH")
    if pn is None or pn.kieu != "choice" or pn.danh_muc != ch.danh_muc_phap_nhan or nhom.truong_phap_nhan != ch.truong_phap_nhan:
        lech.append("TRUONG_PHAP_NHAN_LECH")
    if tep is None or tep.kieu != "attachment" or tep.toi_da_tep == 0:
        lech.append("TRUONG_TEP_LECH")
    return lech


TRUONG_CHINH_KIEU = (("truong_tien", "number"), ("truong_phap_nhan", "choice"), ("truong_tep", "attachment"))


def truong_chinh_lech(truong, ch: dict) -> list:
    """Trường chính (tiền/pháp nhân/tệp theo cấu hình đã chốt trong canonical) phải xuất hiện ĐÚNG một lần trong chi tiết, đúng kiểu.
    truong: các cặp (mã, kiểu) của RA.ChiTietRequest.truong. Rỗng/thiếu/sai kiểu/trùng mã → trả mã trường lệch; trường khác không xét."""
    return [ch[k] for k, kieu in TRUONG_CHINH_KIEU if [kk for m, kk in truong if m == ch[k]] != [kieu]]


def buoc_tiep(trang_thai: str, da_lam: set, co_remote: bool) -> str | None:
    """Bước kế tiếp trong MỘT lệnh; mỗi bước tối đa một lần/lệnh (không vòng gửi lại)."""
    b = {"MOI": "TAO", "CHUA_RO_TAO": "TAO", "TU_CHOI_TAO": "TAO", "DA_TAO": "DOC", "DA_TAO_NHAP": "TAI", "CHO_QUET": "DOI_SOAT",
         "CHUA_RO_TAI": "DOI_SOAT"}.get(trang_thai)
    if b is None and trang_thai in ("DA_DOI_SOAT", "HOLD") and co_remote:
        b = "DOC"  # luôn đọc trạng thái thật của Request đã biết ID
    return None if b is None or b in da_lam else b


class RequestNhap:
    def __init__(self, xd, cau_hinh: CauHinhRequest | None, transport, *, lease_giay: int = LEASE_GIAY):
        """xd: XayDungK2 (conn app + conn_tin_cay). transport: đối tượng có `gui(...)` + `kich_hoat`; None = chưa có khóa/endpoint."""
        self.xd, self.ch, self.t = xd, cau_hinh or CauHinhRequest(), transport
        self.client = RA.RequestClient(transport) if transport is not None else None
        self.lease_giay = lease_giay

    # ------------------------------------------------------------------ hạ tầng
    def _db(self, fn, *a):
        """Lỗi CSDL dạng 'MA: …' → DataError(MA); mất kết nối/commit chưa rõ → M4_KET_QUA_CHUA_RO (bước sẽ thành chưa rõ khi lease hết hạn)."""
        try:
            import psycopg
        except ImportError:  # môi trường kiểm thuần không có driver: không có lỗi psycopg để chuyển mã
            return fn(*a)
        try:
            return fn(*a)
        except psycopg.Error as exc:
            ma = self.xd._ma_loi_pg(exc)
            if self.xd._loi_ket_noi(exc, self.xd.conn_tin_cay) or self.xd._loi_ket_noi(exc, self.xd.conn):
                raise DataError("M4_KET_QUA_CHUA_RO", "Mất kết nối CSDL giữa chừng — chưa rõ đã ghi hay chưa. Xem lại trạng thái Request của hồ sơ "
                                                      "(cùng khóa) để đối soát; không tạo khóa mới.") from None
            if ma.startswith("M4_"):
                raise DataError(ma, (getattr(exc.diag, "message_primary", "") or ma).split(":", 1)[-1].strip()) from None
            raise

    def _quyen(self, dt, dot: str) -> dict:
        xd = self.xd

        def f():
            with xd._tx(dt):
                return xd._mot("SELECT m4.request_quyen(%s::uuid) AS q", (dot,))["q"]
        return self._db(f)

    def _kiem_dau(self, dt, dot: str) -> dict:
        q = self._quyen(dt, dot)
        if not q.get("thay"):
            raise DataError("M4_REQUEST_KHONG_THAY", "Không thấy đợt (hoặc ngoài phạm vi hiện hành).")
        if not q.get("tai_pdf"):
            raise DataError("M4_REQUEST_PHAM_VI", "Vai hiện hành không được tạo Request từ hồ sơ đã duyệt (cần soạn/duyệt trên đợt đã nộp).")
        return q

    def thieu_cau_hinh(self, q: dict | None = None) -> list:
        t = list(self.ch.thieu())
        if self.t is None:
            t.append("khoa_api")
        elif not getattr(self.t, "kich_hoat", False):
            t.append("transport_chua_kich_hoat")
        if q is not None:
            if not q.get("anh_xa"):
                t.append("anh_xa_nhan_vien")
            elif self.ch.khoa_chu_dang_nhap and str(q.get("nguoi_tao") or "").casefold() == self.ch.khoa_chu_dang_nhap.casefold():
                t.append("anh_xa_trung_chu_khoa")
            pn = q.get("phap_nhan_id")
            if pn and not (isinstance(self.ch.phap_nhan_ma, dict) and isinstance(self.ch.phap_nhan_ma.get(pn), str) and self.ch.phap_nhan_ma.get(pn)):
                t.append("ma_phap_nhan")
        return sorted(set(t))

    @staticmethod
    def _dto(y: dict | None) -> dict | None:
        if y is None:
            return None
        d = {k: _json_hoa(y.get(k)) for k in DTO_COT}
        d["dang_xu_ly"] = y.get("lease_id") is not None
        return d

    def _ket_qua(self, trang_thai: str, *, y=None, lap_lai=False, chan=None, buoc=(), loi=(), thieu=None, canh_bao=None) -> dict:
        out = {"schema": SCHEMA, "trang_thai": trang_thai, "lap_lai": bool(lap_lai), "chan": chan, "buoc": list(buoc), "loi": list(loi),
               "y_dinh": self._dto(y)}
        if thieu is not None:
            out["thieu"] = thieu
        if canh_bao:
            out["canh_bao"] = canh_bao
        return out

    # ------------------------------------------------------------------ đọc
    def xem(self, dang_nhap: str, *, dot_id) -> dict:
        """Trạng thái Request của đợt (đọc qua RLS login ứng dụng) — không mạng, không lộ người đứng tên/khóa/canonical."""
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        dot = _uuid(dot_id, "dot_id")
        q = self._quyen(dt, dot)
        if not q.get("thay"):
            raise DataError("M4_REQUEST_KHONG_THAY", "Không thấy đợt (hoặc ngoài phạm vi hiện hành).")

        def f():
            with xd._tx(dt):
                ys = xd._nhieu("SELECT * FROM m4.request_y_dinh WHERE dot_id = %s::uuid ORDER BY tao_luc, id", (dot,))
                sk = xd._nhieu("""SELECT s.y_dinh_id, s.thu_tu, s.buoc, s.tu_trang_thai, s.den_trang_thai, s.chi_tiet, s.quyen_con, s.boi, s.luc
                                  FROM m4.request_su_kien s JOIN m4.request_y_dinh y ON y.id = s.y_dinh_id
                                  WHERE y.dot_id = %s::uuid ORDER BY s.y_dinh_id, s.thu_tu""", (dot,))
            return ys, sk
        ys, sk = self._db(f)
        thieu = self.thieu_cau_hinh(q) if q.get("tai_pdf") else None
        return {"schema": SCHEMA, "quyen": {"tao": bool(q.get("tao")), "tai_pdf": bool(q.get("tai_pdf")), "anh_xa": bool(q.get("anh_xa"))},
                "cau_hinh": None if thieu is None else {"trang_thai": "CHUA_CAU_HINH" if thieu else "SAN_SANG", "thieu": thieu},
                "y_dinh": [{**self._dto(y), "su_kien": [{k: _json_hoa(v) for k, v in s.items() if k != "y_dinh_id"} for s in sk if s["y_dinh_id"] == y["id"]]}
                           for y in ys]}

    # ------------------------------------------------------------------ lệnh
    def tao(self, dang_nhap: str, *, dot_id, version_id, khoa) -> dict:
        return self._lenh(dang_nhap, HANH_TAO, dot_id=dot_id, version_id=version_id, khoa=khoa)

    def doi_soat(self, dang_nhap: str, *, dot_id, version_id, khoa) -> dict:
        """Tiếp tục/đối soát intent đã có (UNKNOWN, chờ quét, xem trạng thái thật) — không tạo intent mới."""
        return self._lenh(dang_nhap, HANH_DOI_SOAT, dot_id=dot_id, version_id=version_id, khoa=khoa)

    def _lenh(self, dang_nhap: str, hanh: str, *, dot_id, version_id, khoa) -> dict:
        xd, ch = self.xd, self.ch
        dt = xd.danh_tinh(dang_nhap)
        dot, pb = _uuid(dot_id, "dot_id"), _uuid(version_id, "version_id")
        khoa = xd._khoa(khoa)
        # (1) quyền hiện hành TRƯỚC cấu hình/biên nhận/intent/mạng
        q = self._kiem_dau(dt, dot)
        # (2) cấu hình + mapping: thiếu → CHUA_CAU_HINH có cấu trúc, không side effect
        thieu = self.thieu_cau_hinh(q)
        if thieu:
            return self._ket_qua("CHUA_CAU_HINH", thieu=thieu)
        # (3) hồ sơ đã seal của ĐÚNG phiên bản (DTO DuyetDot: quyền + một snapshot)
        hs = self._db(lambda: DD.DuyetDot(xd).xem(dang_nhap, dot_id=dot, version_id=pb))
        seal = hs.get("seal")
        if hs.get("trang_thai") != "DA_SEAL" or not seal or seal.get("version_id") != pb:
            raise DataError("M4_REQUEST_CHUA_SEAL", "Phiên bản này chưa có chấp thuận + PDF hồ sơ đã duyệt đã seal — chưa tạo Request.")
        pdf = next((p for p in hs.get("pdf_lich_su") or [] if p["id"] == seal["pdf_id"]), None)
        if pdf is None or pdf["sha256"] != seal["pdf_sha256"]:
            raise DataError("M4_REQUEST_NGUON_LECH", "PDF đã seal không khớp lịch sử PDF của phiên bản.")
        sl = seal.get("so_lieu") or {}
        tien_te = DD.kiem_tien_te(sl.get("tien_te"))
        so_tien = DD.tien(sl.get("so_xin_thanh_toan"), "Số xin thanh toán", vnd=tien_te == "VND")
        if so_tien is None or tien_te is None:
            raise DataError("M4_REQUEST_THIEU_SO_TIEN", "Seal không có số xin thanh toán/tiền tệ — không tạo Request.")
        ctx = hs["context"]
        # (4) snapshot nhóm + danh mục pháp nhân đã quan sát (đọc, không side effect)
        pn_ma = ch.phap_nhan_ma[ctx["phap_nhan_id"]]
        try:
            nhom = next((n for n in self.client.nhom() if n.ma == ch.nhom), None)
            lech = kiem_nhom(ch, nhom)
            if not lech and not self.client.danh_muc(ch.danh_muc_phap_nhan).co(pn_ma):
                lech = ["MA_PHAP_NHAN_KHONG_CO"]
        except RA.LoiRequest as exc:
            return self._ket_qua("LOI_REQUEST", loi=[{"buoc": "CAU_HINH", **exc.tom_tat()}])
        if lech:
            return self._ket_qua("CAU_HINH_LECH", thieu=lech)
        body = {"nhom": ch.nhom, "tieuDe": tieu_de(hs["dot"]["so_hop_dong"], hs["dot"]["so_dot"]), "nguoiTao": q["nguoi_tao"],
                "giaTri": {ch.truong_tien: {"amount": so_tien, "currency": tien_te}, ch.truong_phap_nhan: pn_ma},
                "truongMayDien": sorted([ch.truong_tien, ch.truong_phap_nhan])}
        canonical = {
            "schema": SCHEMA,
            "nguon": {"dot_id": ctx["dot_id"], "hop_dong_id": ctx["hop_dong_id"], "du_an_id": ctx["du_an_id"], "phap_nhan_id": ctx["phap_nhan_id"],
                      "phien_ban_id": seal["version_id"], "seal_id": seal["id"], "quyet_dinh_id": seal["quyet_dinh_id"],
                      "ket_luan_id": seal["ket_luan_id"], "graph_sha256": seal["graph_sha256"], "so_lieu_sha256": seal["so_lieu_sha256"],
                      "so_tien": so_tien, "tien_te": tien_te, "pdf_id": seal["pdf_id"], "pdf_sha256": seal["pdf_sha256"],
                      "pdf_byte_length": pdf["byte_length"], "nhanh": "GOC"},
            "actor": {"id": dt["id"], "dang_nhap": dt["dang_nhap"]},
            "anh_xa": {"id": q["anh_xa_id"], "revision": q["anh_xa_revision"], "nguoi_tao": q["nguoi_tao"]},
            "cau_hinh": {"sha256": ch.sha256(), "khoa_ref": ch.khoa_ref, "nhom": ch.nhom, "phien_ban": ch.phien_ban, "truong_tien": ch.truong_tien,
                         "truong_phap_nhan": ch.truong_phap_nhan, "truong_tep": ch.truong_tep, "ma_phap_nhan": pn_ma,
                         "nhom_sha256": dau_van_nhom(nhom)},
            "body": body,
        }
        cj = json.loads(canonical_json(canonical))
        csha = sha256(canonical_json(canonical).encode("utf-8"))
        tep_def = nhom.truong_theo_ma(ch.truong_tep)
        return self._chay(dt, dang_nhap, hanh, khoa, {"dot_id": dot, "version_id": pb, "seal_id": seal["id"]}, dot, seal["id"], cj, csha,
                          pdf_ten=pdf["name"], toi_da_tep=tep_def.toi_da_tep)

    # ------------------------------------------------------------------ máy trạng thái
    def _giu(self, dt, khoa, hanh, yc, dot, seal_id, cj, csha, buoc) -> dict:
        xd = self.xd

        def f():
            with xd._tx_review(dt) as c:
                return xd._r1(c, "SELECT m4.request_giu(%s, %s, %s::jsonb, %s::uuid, %s::uuid, %s::jsonb, %s, %s, %s) AS r",
                              (khoa, hanh, json.dumps(yc), dot, seal_id, json.dumps(cj, ensure_ascii=False), csha, buoc, self.lease_giay))["r"]
        return self._db(f)

    def _ghi(self, dt, y: dict, lease: str, kq: dict) -> dict:
        """Danh tính phiên đặt lại (GUC) để CSDL tính quyền HIỆN HÀNH sau I/O; ghi bằng chứng không phụ thuộc quyền còn hay mất."""
        xd = self.xd

        def f():
            with xd._tx_review(dt) as c:
                return xd._r1(c, "SELECT m4.request_ghi(%s::uuid, %s::uuid, %s, %s::jsonb) AS r",
                              (y["id"], lease, y["revision"], json.dumps(kq, ensure_ascii=False)))["r"]
        return self._db(f)

    def _chay(self, dt, dang_nhap, hanh, khoa, yc, dot, seal_id, cj, csha, *, pdf_ten, toi_da_tep) -> dict:
        da_lam, loi, buoc_ds = set(), [], []
        lap_lai, y = None, None
        buoc = "TAO" if hanh == HANH_TAO else "DOC"
        for _ in range(BUOC_TOI_DA):
            g = self._giu(dt, khoa, hanh, yc, dot, seal_id, cj, csha, buoc)
            lap_lai = g["lap_lai"] if lap_lai is None else lap_lai
            y = g["y_dinh"]
            chan = g.get("chan")
            if chan == "BUOC_KHONG_HOP":  # bước không nhận ở trạng thái này: chọn bước kế, KHÔNG coi bước bị từ chối là đã làm
                buoc = buoc_tiep(y["trang_thai"], da_lam | {buoc}, y.get("remote_id") is not None)
                if buoc is None:
                    break
                continue
            if chan:
                if y["trang_thai"] == "DA_DOI_SOAT":  # đã xong; cấu hình/mapping đổi sau đó chỉ là cảnh báo
                    return self._ket_qua(y["trang_thai"], y=y, lap_lai=lap_lai, buoc=buoc_ds, loi=loi, canh_bao=chan)
                return self._ket_qua("HOLD" if chan != "CHUA_RO_QUA_HAN_IDEM" else y["trang_thai"], y=y, lap_lai=lap_lai, chan=chan, buoc=buoc_ds, loi=loi)
            da_lam.add(buoc)
            buoc_ds.append(buoc)
            kq = self._bang_chung_xong(y, self._thuc_hien(dang_nhap, buoc, y, toi_da_tep=toi_da_tep, pdf_ten=pdf_ten, loi=loi))
            r = self._ghi(dt, y, g["lease_id"], kq)
            y = r["y_dinh"]
            if not r["quyen_con"]:
                # bằng chứng (ID/trạng thái) ĐÃ ghi vào intent; không trả kết quả ngoài quyền hiện hành, không undo
                raise DataError("M4_REQUEST_PHAM_VI_DA_DOI", "Quyền/mapping hiện hành đã đổi trong lúc xử lý — kết quả kỹ thuật đã lưu để đối soát, "
                                                             "không hiển thị.")
            buoc = buoc_tiep(y["trang_thai"], da_lam, y.get("remote_id") is not None)
            if buoc is None:
                break
        return self._ket_qua(y["trang_thai"] if y else "MOI", y=y, lap_lai=bool(lap_lai), buoc=buoc_ds, loi=loi)

    @staticmethod
    def _bang_chung_xong(y: dict, kq: dict) -> dict:
        """Intent ĐÃ đối soát: lần ghi quan sát (DOC/đọc lỗi/phát lại) mang theo bằng chứng đã lưu — không suy từ PDF nguồn, không xóa, không bịa."""
        if y["trang_thai"] == "DA_DOI_SOAT" and kq.get("den") == "DA_DOI_SOAT":
            kq.setdefault("doi_soat_sha256", y["doi_soat_sha256"])
            kq.setdefault("doi_soat_byte_length", y["doi_soat_byte_length"])
        return kq

    def _thuc_hien(self, dang_nhap, buoc: str, y: dict, *, toi_da_tep, pdf_ten, loi: list) -> dict:
        """I/O một bước NGOÀI giao dịch/khóa. Trả kết quả chuẩn hóa cho m4.request_ghi (không câu lỗi thô, không khóa)."""
        try:
            if buoc == "TAO":
                return self._tao(y, loi)
            if buoc == "DOC":
                return self._doc(y, loi)
            if buoc == "TAI":
                return self._tai(dang_nhap, y, toi_da_tep, pdf_ten, loi)
            return self._doi_soat(y, loi)
        except DataError as exc:
            # lỗi cục bộ (vd PDF hỏng/mất quyền tải blob) TRƯỚC khi gửi: giữ trạng thái, ghi sự kiện, báo lỗi rõ
            loi.append({"buoc": buoc, "ma": exc.code})
            ct = {"loi_cuc_bo": exc.code}
            if buoc == "TAO":  # chưa gửi; không che dấu vết chưa rõ trước đó
                return {"den": "CHUA_RO_TAO" if y.get("co_chua_ro") else "TU_CHOI_TAO", "chi_tiet": ct}
            if buoc == "TAI":  # lỗi đọc/kiểm PDF hoặc quyền tải blob TRƯỚC khi gửi
                return {"den": "DA_TAO_NHAP", "chi_tiet": ct}
            return {"den": y["trang_thai"], "chi_tiet": ct}

    # ---- TAO: POST cùng key + body đã lưu (không đổi), không tự retry
    def _tao(self, y: dict, loi: list) -> dict:
        try:
            nt = self.client.tao_nhap(y["canonical"]["body"], y["idem_key"])
        except RA.LoiRequest as exc:
            loi.append({"buoc": "TAO", **exc.tom_tat()})
            if exc.khong_ro:
                return {"den": "CHUA_RO_TAO", "chi_tiet": exc.tom_tat()}
            if exc.ma in TAO_CHUA_GUI or exc.status is not None and 400 <= exc.status < 500:
                return {"den": "TU_CHOI_TAO", "chi_tiet": exc.tom_tat()}
            return {"den": "CHUA_RO_TAO", "chi_tiet": exc.tom_tat()}
        return {"den": "DA_TAO", "remote_id": nt.id, "remote_ma": nt.ma, "chi_tiet": {"status": 201 if nt.moi else 200, "moi": nt.moi}}

    # ---- DOC: GET chi tiết — trạng thái thật + đối chiếu bản nháp với canonical
    def _doc(self, y: dict, loi: list) -> dict:
        try:
            ct = self.client.chi_tiet(y["remote_id"])
        except RA.LoiRequest as exc:
            loi.append({"buoc": "DOC", **exc.tom_tat()})
            if y["trang_thai"] == "DA_TAO" and exc.status == 404:
                return {"den": "HOLD", "hold_ma": "REQUEST_KHONG_THAY", "chi_tiet": exc.tom_tat()}
            return {"den": y["trang_thai"], "chi_tiet": exc.tom_tat()}
        if y["trang_thai"] != "DA_TAO":  # quan sát: chỉ cập nhật trạng thái thật của Request
            kq = {"den": y["trang_thai"], "remote_trang_thai": ct.trang_thai, "chi_tiet": {"remote_trang_thai": ct.trang_thai}}
            if y["trang_thai"] == "DA_DOI_SOAT":  # bằng chứng là LỊCH SỬ; quan sát hiện tại báo riêng, không hạ/undo hoàn tất
                lech = self.quan_sat_xong(y, ct)
                kq["chi_tiet"].update(bang_chung="LICH_SU", lech_hien_tai=lech)
                if lech:
                    loi.append({"buoc": "DOC", "ma": "QUAN_SAT_LECH", "lech": lech})
            return kq
        lech = self.lech_nhap(y, ct)
        kq = {"remote_trang_thai": ct.trang_thai, "chi_tiet": {"remote_trang_thai": ct.trang_thai, "lech": lech}}
        if ct.trang_thai != "draft":
            return {**kq, "den": "HOLD", "hold_ma": "KHONG_CON_NHAP"}
        if lech:
            return {**kq, "den": "HOLD", "hold_ma": lech[0]}
        return {**kq, "den": "DA_TAO_NHAP"}

    @staticmethod
    def lech_nhap(y: dict, ct: RA.ChiTietRequest, tep_rieng=frozenset()) -> list:
        """Đối chiếu bản nháp nguồn trả về với canonical: nhóm, người đứng tên (mapping), số tiền + tiền tệ đúng chuỗi, mã pháp nhân, trường, tạo qua API.
        tep_rieng: ID tệp (có thể) do CHÍNH intent tải — không tính là TEP_DA_CO_KHONG_RO; mọi tệp khác trong ô tệp vẫn bị báo."""
        c = y["canonical"]
        ch, body = c["cau_hinh"], c["body"]
        tien = body["giaTri"][ch["truong_tien"]]
        lech = []
        if ct.nhom_ma != ch["nhom"]:
            lech.append("NHOM_LECH")
        if ct.nguoi_tao_dang_nhap is None or ct.nguoi_tao_dang_nhap.casefold() != str(body["nguoiTao"]).casefold():
            lech.append("NGUOI_TAO_LECH")
        if ct.gia_tri.get(ch["truong_tien"]) != tien:
            lech.append("SO_TIEN_LECH")
        if ct.tong_tien != tien:  # tổng tiền header đã lưu phải CÓ và đúng chuỗi số tiền + tiền tệ; None/thiếu là lệch (sau mã số tiền body)
            lech.append("TONG_TIEN_LECH")
        if ct.gia_tri.get(ch["truong_phap_nhan"]) != body["giaTri"][ch["truong_phap_nhan"]]:
            lech.append("PHAP_NHAN_LECH")
        if truong_chinh_lech(ct.truong, ch):
            lech.append("TRUONG_LECH")
        if ct.tao_qua_api is not True:
            lech.append("KHONG_TAO_QUA_API")
        if any(t.ma_truong == ch["truong_tep"] and not t.khu_chung and t.id not in tep_rieng for t in ct.tep):
            lech.append("TEP_DA_CO_KHONG_RO")
        return lech

    @staticmethod
    def kiem_tep_biet(y: dict, ct: RA.ChiTietRequest, tep_id) -> tuple:
        """Tệp đã biết ID của intent: phải còn, thuộc ĐÚNG ô tệp đã cấu hình, không khu chung. Trả (tệp | None, mã lệch | None)."""
        t = next((t for t in ct.tep if t.id == str(tep_id)), None)
        if t is None:
            return None, "TEP_MAT"
        if t.ma_truong != y["canonical"]["cau_hinh"]["truong_tep"] or t.khu_chung:
            return t, "TEP_LECH"
        return t, None

    def quan_sat_xong(self, y: dict, ct: RA.ChiTietRequest) -> list:
        """Quan sát Request đã đối soát xong: canonical + tệp của chính intent (còn, đúng ô, đúng độ dài, sạch). Chỉ báo, không đổi bằng chứng."""
        biet = str(y.get("remote_tep_id") or "")
        lech = self.lech_nhap(y, ct, tep_rieng={biet})
        t, ma = self.kiem_tep_biet(y, ct, biet)
        if ma:
            lech.append(ma)
        elif t.kich_thuoc != y["pdf_byte_length"] or t.trang_thai_quet != "clean":
            lech.append("TEP_KHONG_CON_KHOP")
        return lech

    # ---- TAI: PDF đã seal (quyền trước/sau blob + SHA/độ dài) → kiểm draft/maxFiles → multipart vào đúng ô tệp
    def _tai(self, dang_nhap, y: dict, toi_da_tep, pdf_ten, loi: list) -> dict:
        ten, media, raw = self._db(self.xd.duyet_pdf_tai, dang_nhap, str(y["phien_ban_id"]), str(y["pdf_id"]))
        if sha256(raw) != y["pdf_sha256"] or len(raw) != y["pdf_byte_length"] or media != "application/pdf":
            return {"den": "HOLD", "hold_ma": "PDF_SEAL_LECH", "chi_tiet": {"byte_length": len(raw)}}
        ma_tep = y["canonical"]["cau_hinh"]["truong_tep"]
        try:
            ct = self.client.chi_tiet(y["remote_id"])
        except RA.LoiRequest as exc:
            loi.append({"buoc": "TAI", **exc.tom_tat()})
            return {"den": "DA_TAO_NHAP", "chi_tiet": {"doc_truoc_tai": exc.tom_tat()}}
        if ct.trang_thai != "draft":
            return {"den": "HOLD", "hold_ma": "KHONG_CON_NHAP", "remote_trang_thai": ct.trang_thai, "chi_tiet": {"remote_trang_thai": ct.trang_thai}}
        dang_co = [t for t in ct.tep if t.ma_truong == ma_tep and not t.khu_chung]
        if toi_da_tep is not None and len(dang_co) >= toi_da_tep:
            return {"den": "HOLD", "hold_ma": "TEP_DAY", "chi_tiet": {"dang_co": len(dang_co), "toi_da": toi_da_tep}}
        lech = self.lech_nhap(y, ct)  # canonical đầy đủ NGAY trước khi gắn PDF: bản nháp đổi sau DOC → không tải, không hoàn tất
        if lech:
            return {"den": "HOLD", "hold_ma": lech[0], "remote_trang_thai": ct.trang_thai,
                    "chi_tiet": {"remote_trang_thai": ct.trang_thai, "lech": lech, "truoc_tai": True}}
        try:
            t = self.client.tai_tep(y["remote_id"], ten or pdf_ten, raw, ma_truong=ma_tep)
        except RA.LoiRequest as exc:
            loi.append({"buoc": "TAI", **exc.tom_tat()})
            if exc.khong_ro:
                return {"den": "CHUA_RO_TAI", "chi_tiet": exc.tom_tat()}
            if exc.ma in TAI_CHUA_GUI:
                return {"den": "DA_TAO_NHAP", "chi_tiet": exc.tom_tat()}
            if exc.status == 409:
                return {"den": "HOLD", "hold_ma": "KHONG_CON_NHAP", "chi_tiet": exc.tom_tat()}
            return {"den": "HOLD", "hold_ma": f"TAI_TU_CHOI_{exc.status or 0}", "chi_tiet": exc.tom_tat()}
        kq = {"remote_tep_id": t.id, "tep_trang_thai_quet": t.trang_thai_quet,
              "chi_tiet": {"tep_id": t.id, "kich_thuoc": t.kich_thuoc, "ma_truong": t.ma_truong, "trang_thai_quet": t.trang_thai_quet}}
        if t.ma_truong != ma_tep or t.khu_chung or t.kich_thuoc != len(raw):
            return {**kq, "den": "HOLD", "hold_ma": "TEP_LECH"}
        if t.trang_thai_quet == "infected":
            return {**kq, "den": "HOLD", "hold_ma": "TEP_NHIEM"}
        return {**kq, "den": "CHO_QUET"}

    # ---- DOI_SOAT: metadata → chỉ clean mới tải bytes → SHA/độ dài so PDF seal; một khớp DUY NHẤT mới xác nhận
    def _doi_soat(self, y: dict, loi: list) -> dict:
        ma_tep, dai, sha_goc = y["canonical"]["cau_hinh"]["truong_tep"], y["pdf_byte_length"], y["pdf_sha256"]
        try:
            ct = self.client.chi_tiet(y["remote_id"])
        except RA.LoiRequest as exc:
            loi.append({"buoc": "DOI_SOAT", **exc.tom_tat()})
            return {"den": y["trang_thai"], "chi_tiet": exc.tom_tat()}
        biet = y.get("remote_tep_id")
        if biet:  # tệp đã biết ID vẫn phải thuộc đúng ô tệp đã cấu hình, không khu chung
            t_biet, ma = self.kiem_tep_biet(y, ct, biet)
            if ma:
                return {"den": "HOLD", "hold_ma": ma, "remote_trang_thai": ct.trang_thai,
                        "chi_tiet": {"tep_id": str(biet), "remote_trang_thai": ct.trang_thai}}
            ung = [t_biet]
        else:  # lost ACK upload: ứng viên = tệp trong ô tệp đã cấu hình; kích thước chỉ để lọc, KHÔNG là bằng chứng
            ung = [t for t in ct.tep if t.ma_truong == ma_tep and not t.khu_chung and t.kich_thuoc == dai]
        ct_chung = {"remote_trang_thai": ct.trang_thai, "ung_vien": [{"id": t.id, "quet": t.trang_thai_quet, "kich_thuoc": t.kich_thuoc} for t in ung]}
        # canonical đầy đủ: bytes PDF đúng KHÔNG chứng minh đúng Request/trường; chỉ (ứng viên) tệp của chính intent được miễn TEP_DA_CO_KHONG_RO
        lech = self.lech_nhap(y, ct, tep_rieng={t.id for t in ung})
        if lech:
            return {"den": "HOLD", "hold_ma": lech[0], "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "lech": lech}}
        if not ung:
            return {"den": y["trang_thai"], "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "ly_do": "KHONG_THAY_UNG_VIEN"}}
        if any(t.trang_thai_quet == "infected" for t in ung):
            return {"den": "HOLD", "hold_ma": "TEP_NHIEM", "remote_trang_thai": ct.trang_thai, "chi_tiet": ct_chung}
        if any(t.trang_thai_quet == "error" for t in ung):
            return {"den": "HOLD", "hold_ma": "TEP_QUET_LOI", "remote_trang_thai": ct.trang_thai, "chi_tiet": ct_chung}
        if any(t.trang_thai_quet == "pending" for t in ung):
            den = "CHO_QUET" if biet else "CHUA_RO_TAI"
            return {"den": den, "remote_trang_thai": ct.trang_thai, "tep_trang_thai_quet": "pending" if biet else None, "chi_tiet": ct_chung}
        khop = []
        for t in ung:
            if t.kich_thuoc != dai:
                continue
            try:
                b = self.client.tai_ve(t.id, dai)
            except RA.LoiRequest as exc:
                loi.append({"buoc": "DOI_SOAT", **exc.tom_tat()})
                return {"den": y["trang_thai"], "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "tai_ve": exc.tom_tat()}}
            if len(b) == dai and sha256(b) == sha_goc:
                khop.append(t)
        if len(khop) == 1 and len(ung) > 1:  # lost ACK: ứng viên cùng kích thước nhưng khác bytes là tệp lạ trong ô tệp → không nhận mù
            return {"den": "HOLD", "hold_ma": "TEP_DA_CO_KHONG_RO", "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "so_khop": 1}}
        if len(khop) == 1:
            t = khop[0]
            return {"den": "DA_DOI_SOAT", "remote_tep_id": t.id, "tep_trang_thai_quet": "clean", "doi_soat_sha256": sha_goc,
                    "doi_soat_byte_length": dai, "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "khop": t.id}}
        hm = "TEP_TRUNG_KHOP" if len(khop) > 1 else ("TEP_HASH_LECH" if biet or ung else "KHONG_KHOP")
        return {"den": "HOLD", "hold_ma": hm, "remote_trang_thai": ct.trang_thai, "chi_tiet": {**ct_chung, "so_khop": len(khop)}}


def trang_thai_hop_le(tt: str) -> bool:
    return tt in TRANG_THAI


def ma_http(code: str) -> int:
    for st, s in MA_HTTP.items():
        if code in s:
            return st
    return 400
