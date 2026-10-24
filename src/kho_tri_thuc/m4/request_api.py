"""M4-04A — client stdlib typed cho Request API #2 (`/api/v1`): nhóm, danh mục, tạo nháp, chi tiết, danh sách, tải tệp lên, tải tệp về.

- Chỉ origin đã cấu hình phía máy chủ (https; http CHỈ loopback khi kiểm thử khai báo), route tương đối cố định do client dựng — không nhận URL/path
  từ trình duyệt, không userinfo/query/fragment trong origin, không theo redirect (http.client không tự theo; 3xx = lỗi).
- Khóa API (Bearer) chỉ nằm trong transport; client/fake/log/lỗi không thấy và không in khóa. Lỗi typed theo mã HTTP + Retry-After, không mang câu
  lỗi thô của nguồn (`loi`/`chiTiet`/`loiTheoTruong`) ra ngoài — chỉ mã trường (khóa của loiTheoTruong) đã lọc.
- Giới hạn hữu hạn: timeout kết nối/đọc, kích thước phản hồi. KHÔNG tự retry; POST mất phản hồi sau khi đã gửi → `LoiRequest(khong_ro=True)`.
- Transport thật mặc định TẮT (`kich_hoat=False`): chỉ máy chủ bật sau khi Root xác minh mapping/khóa/retention (nhánh infected→storage.remove của
  nguồn chưa được kiểm). API không có gửi/duyệt/từ chối/trả lại/xóa — client này cũng không có.
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import re
import secrets
import ssl
import uuid
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

TIEN_TO = "/api/v1"
TRANG_THAI_REQUEST = ("draft", "in_review", "returned", "approved", "rejected")
TRANG_THAI_QUET = ("pending", "clean", "infected", "error")
KIEU_TRUONG = ("text", "number", "date", "choice", "user_or_department", "table", "attachment", "tieu_de")
IDEM_TOI_DA = 200
MA_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}")
MA_LOI_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}")
PHAN_HOI_TOI_DA = 4 * 1024 * 1024
TEP_TOI_DA = 64 * 1024 * 1024
LOOPBACK = ("localhost",)


class LoiRequest(Exception):
    """Lỗi typed. `ma`: REQUEST_401/403/404/409/422/429/503, REQUEST_HTTP_<n>, REQUEST_KHONG_RO, REQUEST_KET_NOI, REQUEST_PHAN_HOI_SAI,
    REQUEST_CHUYEN_HUONG, REQUEST_TRANSPORT_TAT, REQUEST_THAM_SO_SAI. `khong_ro`: đã gửi nhưng không biết nguồn đã thực hiện hay chưa."""

    def __init__(self, ma: str, *, status: int | None = None, retry_after: int | None = None, khong_ro: bool = False, truong: tuple = ()):
        super().__init__(ma)
        self.ma, self.status, self.retry_after, self.khong_ro, self.truong = ma, status, retry_after, khong_ro, tuple(truong)

    def tom_tat(self) -> dict:
        """Dạng an toàn để ghi lịch sử/trả UI: không câu lỗi thô, không khóa."""
        return {"ma": self.ma, "status": self.status, "retry_after": self.retry_after, "khong_ro": self.khong_ro, "truong": list(self.truong)}

    def __repr__(self):
        return f"LoiRequest({self.ma!r}, status={self.status!r}, khong_ro={self.khong_ro!r})"


class LoiTruyen(Exception):
    """Lỗi tầng transport. da_gui=False: chắc chắn CHƯA gửi (kết nối/TLS thất bại); True: có thể đã tới nguồn (gửi/đọc dở, timeout đọc)."""

    def __init__(self, da_gui: bool, ma: str = "TRUYEN"):
        super().__init__(ma)
        self.da_gui, self.ma = da_gui, ma


@dataclass(frozen=True)
class PhanHoi:
    status: int
    headers: dict  # khóa chữ thường
    body: bytes


class HttpsTransport:
    """Transport stdlib. Khóa API chỉ ở đây; mỗi lần gửi thêm `Authorization: Bearer`. Một kết nối mới mỗi lệnh (không pool, không giữ socket)."""

    def __init__(self, origin: str, khoa_bi_mat: str, *, kich_hoat: bool = False, cho_http_loopback: bool = False, ket_noi_giay: float = 5.0,
                 doc_giay: float = 30.0, ssl_context: ssl.SSLContext | None = None):
        self.scheme, self.host, self.port = kiem_origin(origin, cho_http_loopback=cho_http_loopback)
        if not isinstance(khoa_bi_mat, str) or not 16 <= len(khoa_bi_mat) <= 512 or any(ord(c) < 33 or ord(c) > 126 for c in khoa_bi_mat):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        if not (0 < ket_noi_giay <= 60 and 0 < doc_giay <= 300):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        self._khoa = khoa_bi_mat
        self.kich_hoat = bool(kich_hoat)
        self.ket_noi_giay, self.doc_giay = ket_noi_giay, doc_giay
        self._ssl = ssl_context or ssl.create_default_context()

    def __repr__(self):  # không lộ khóa
        return f"HttpsTransport({self.scheme}://{self.host}:{self.port}, kich_hoat={self.kich_hoat})"

    def gui(self, phuong_thuc: str, duong_dan: str, headers: dict, body: bytes | None, toi_da_byte: int) -> PhanHoi:
        if not self.kich_hoat:
            raise LoiRequest("REQUEST_TRANSPORT_TAT")
        if not kiem_duong_dan(duong_dan):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        if self.scheme == "https":
            c = http.client.HTTPSConnection(self.host, self.port, timeout=self.ket_noi_giay, context=self._ssl)
        else:
            c = http.client.HTTPConnection(self.host, self.port, timeout=self.ket_noi_giay)
        try:
            try:
                c.connect()
                c.sock.settimeout(self.doc_giay)
            except (OSError, ssl.SSLError, http.client.HTTPException):
                raise LoiTruyen(False, "KET_NOI") from None
            h = {**headers, "Authorization": "Bearer " + self._khoa, "Host": self.host if self.port in (80, 443) else f"{self.host}:{self.port}",
                 "Accept": "application/json", "Connection": "close"}
            try:
                c.request(phuong_thuc, duong_dan, body=body, headers=h)
                r = c.getresponse()
                data = r.read(toi_da_byte + 1)
            except (OSError, ssl.SSLError, http.client.HTTPException):
                raise LoiTruyen(True, "GUI_DO") from None
            if len(data) > toi_da_byte:
                raise LoiTruyen(True, "QUA_LON")
            return PhanHoi(r.status, {k.lower(): v for k, v in r.getheaders()}, data)
        finally:
            c.close()


def kiem_origin(origin, *, cho_http_loopback: bool = False) -> tuple[str, str, int]:
    """Origin tin cậy: https://host[:port] (không userinfo/path/query/fragment). http chỉ cho loopback khi máy chủ khai báo kiểm thử."""
    if not isinstance(origin, str) or len(origin) > 300 or any(ord(c) <= 32 for c in origin):
        raise LoiRequest("REQUEST_THAM_SO_SAI")
    u = urlsplit(origin)
    if u.username is not None or u.password is not None or "@" in u.netloc or u.query or u.fragment or u.path not in ("", "/") or not u.hostname:
        raise LoiRequest("REQUEST_THAM_SO_SAI")
    try:
        port = u.port
    except ValueError:
        raise LoiRequest("REQUEST_THAM_SO_SAI") from None
    host = u.hostname
    if u.scheme == "https":
        return "https", host, port or 443
    if u.scheme == "http" and cho_http_loopback and _la_loopback(host):
        return "http", host, port or 80
    raise LoiRequest("REQUEST_THAM_SO_SAI")


DUONG_DAN_RE = re.compile(r"/api/v1/(nhom|danh-muc/[A-Za-z0-9_.%-]{1,300}|de-xuat|de-xuat/[0-9a-f-]{36}|de-xuat/[0-9a-f-]{36}/tep|tep/[0-9a-f-]{36})"
                          r"(\?[A-Za-z0-9_.%=&-]{1,400})?")


def kiem_duong_dan(duong_dan) -> bool:
    """Chỉ các route API #2 client dùng (tương đối, cố định); không '..', không '//', không ký tự điều khiển."""
    return isinstance(duong_dan, str) and DUONG_DAN_RE.fullmatch(duong_dan) is not None and ".." not in duong_dan


def _la_loopback(host: str) -> bool:
    if host in LOOPBACK:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# ================================================================================================== DTO typed
def _sai():
    raise LoiRequest("REQUEST_PHAN_HOI_SAI")


def _s(v, *, rong=False, toi_da=2000) -> str:
    if not isinstance(v, str) or (not rong and v == "") or len(v) > toi_da:
        _sai()
    return v


def _so(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        _sai()
    return v


def _id(v) -> str:
    if not isinstance(v, str):
        _sai()
    try:
        u = str(uuid.UUID(v))
    except ValueError:
        _sai()
    if u != v.lower():
        _sai()
    return u


@dataclass(frozen=True)
class TruongRequest:
    ma: str
    nhan: str
    kieu: str
    bat_buoc: bool
    cau_hinh: dict
    danh_muc: str | None

    @property
    def toi_da_tep(self) -> int | None:
        v = self.cau_hinh.get("maxFiles")
        return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None

    @staticmethod
    def tu(x) -> "TruongRequest":
        if not isinstance(x, dict):
            _sai()
        kieu = x.get("kieu")
        if kieu not in KIEU_TRUONG:
            _sai()
        ch = x.get("cauHinh") if x.get("cauHinh") is not None else {}
        dm = x.get("danhMuc")
        if not isinstance(ch, dict) or not isinstance(x.get("batBuoc", False), bool) or (dm is not None and not isinstance(dm, str)):
            _sai()
        return TruongRequest(_s(x.get("ma"), toi_da=100), _s(x.get("nhan", ""), rong=True), kieu, bool(x.get("batBuoc", False)), ch, dm)

    def dau_van(self) -> dict:
        """Phần định nghĩa dùng để phát hiện drift (không gồm nhãn hiển thị)."""
        return {"ma": self.ma, "kieu": self.kieu, "bat_buoc": self.bat_buoc, "cau_hinh": self.cau_hinh, "danh_muc": self.danh_muc}


@dataclass(frozen=True)
class NhomRequest:
    ma: str
    ten: str
    phien_ban: int
    truong_tong_tien: str | None
    truong_phap_nhan: str | None
    truong: tuple

    def truong_theo_ma(self, ma: str) -> TruongRequest | None:
        return next((t for t in self.truong if t.ma == ma), None)

    @staticmethod
    def tu(x) -> "NhomRequest":
        if not isinstance(x, dict) or not isinstance(x.get("truong"), list):
            _sai()
        pb = x.get("phienBan")
        if isinstance(pb, bool) or not isinstance(pb, int) or pb < 1:
            _sai()
        tt, pn = x.get("truongTongTien"), x.get("truongPhapNhan")
        if (tt is not None and not isinstance(tt, str)) or (pn is not None and not isinstance(pn, str)):
            _sai()
        truong = tuple(TruongRequest.tu(t) for t in x["truong"])
        if len({t.ma for t in truong}) != len(truong):
            _sai()
        return NhomRequest(_s(x.get("ma"), toi_da=100), _s(x.get("ten", ""), rong=True), pb, tt, pn, truong)


@dataclass(frozen=True)
class GiaTriDanhMuc:
    ma: str
    dang_dung: bool


@dataclass(frozen=True)
class DanhMucRequest:
    ma: str
    gia_tri: tuple

    def co(self, ma: str) -> bool:
        return any(g.ma == ma and g.dang_dung for g in self.gia_tri)

    @staticmethod
    def tu(x) -> "DanhMucRequest":
        if not isinstance(x, dict) or not isinstance(x.get("giaTri"), list):
            _sai()
        gt = []
        for g in x["giaTri"]:
            if not isinstance(g, dict) or not isinstance(g.get("dangDung"), bool):
                _sai()
            gt.append(GiaTriDanhMuc(_s(g.get("ma"), toi_da=200), g["dangDung"]))
        return DanhMucRequest(_s(x.get("ma"), toi_da=100), tuple(gt))


@dataclass(frozen=True)
class NhapTao:
    id: str
    ma: str | None
    trang_thai_bao: str  # nguồn hard-code 'draft' cả khi phát lại — KHÔNG dùng làm trạng thái thật (luôn GET chi tiết)
    moi: bool  # 201 = mới; 200 = phát lại cùng Idempotency-Key trong 24h

    @staticmethod
    def tu(x, status: int) -> "NhapTao":
        if not isinstance(x, dict):
            _sai()
        ma = x.get("ma")
        if ma is not None and not isinstance(ma, str):
            _sai()
        return NhapTao(_id(x.get("id")), ma, _s(x.get("trangThai", ""), rong=True, toi_da=40), status == 201)


@dataclass(frozen=True)
class TepRequest:
    id: str
    ten_tep: str
    ma_truong: str | None
    khu_chung: bool
    kich_thuoc: int
    mime: str | None
    trang_thai_quet: str

    @staticmethod
    def tu(x) -> "TepRequest":
        if not isinstance(x, dict) or x.get("trangThaiQuet") not in TRANG_THAI_QUET or not isinstance(x.get("khuChung"), bool):
            _sai()
        mt, mime = x.get("maTruong"), x.get("mime")
        if (mt is not None and not isinstance(mt, str)) or (mime is not None and not isinstance(mime, str)):
            _sai()
        return TepRequest(_id(x.get("id")), _s(x.get("tenTep"), toi_da=500), mt, x["khuChung"], _so(x.get("kichThuoc")), mime, x["trangThaiQuet"])


@dataclass(frozen=True)
class ChiTietRequest:
    id: str
    ma: str | None
    tieu_de: str
    nhom_ma: str
    trang_thai: str
    nguoi_tao_dang_nhap: str | None
    tong_tien: dict | None
    gia_tri: dict
    truong: tuple  # mã trường thấy trong chi tiết (định nghĩa rút gọn {ma, kieu})
    truong_may_dien: tuple
    tao_qua_api: bool | None
    tep: tuple = field(default=())

    @staticmethod
    def tu(x) -> "ChiTietRequest":
        if not isinstance(x, dict) or x.get("trangThai") not in TRANG_THAI_REQUEST or not isinstance(x.get("nhom"), dict):
            _sai()
        nt = x.get("nguoiTao") if isinstance(x.get("nguoiTao"), dict) else {}
        dn = nt.get("tenDangNhap")
        tong = x.get("tongTien")
        if tong is not None and (not isinstance(tong, dict) or not isinstance(tong.get("amount"), str) or not isinstance(tong.get("currency"), str)):
            _sai()
        gt = x.get("giaTri") if x.get("giaTri") is not None else {}
        tr = x.get("truong") if x.get("truong") is not None else []
        md = x.get("truongMayDien") if x.get("truongMayDien") is not None else []
        tep = x.get("tep") if x.get("tep") is not None else []
        if not isinstance(gt, dict) or not isinstance(tr, list) or not isinstance(md, list) or not isinstance(tep, list):
            _sai()
        truong = tuple((_s(t.get("ma"), toi_da=100), t.get("kieu")) for t in tr if isinstance(t, dict))
        may = tuple(_s(m.get("ma"), toi_da=100) for m in md if isinstance(m, dict))
        tq = x.get("taoQuaApi")
        return ChiTietRequest(_id(x.get("id")), x.get("ma") if isinstance(x.get("ma"), str) else None, _s(x.get("tieuDe", ""), rong=True),
                              _s(x["nhom"].get("ma"), toi_da=100), x["trangThai"], dn if isinstance(dn, str) else None, tong, gt, truong, may,
                              tq if isinstance(tq, bool) else None, tuple(TepRequest.tu(t) for t in tep))


# ================================================================================================== client
class RequestClient:
    def __init__(self, transport):
        self.t = transport

    # -------------------------------------------------------------- lõi
    def _goi(self, phuong_thuc: str, duong_dan: str, *, body: bytes | None = None, headers: dict | None = None, ghi: bool = False,
             toi_da: int = PHAN_HOI_TOI_DA, json_ra: bool = True):
        try:
            r = self.t.gui(phuong_thuc, duong_dan, dict(headers or {}), body, toi_da)
        except LoiTruyen as exc:
            if exc.da_gui:
                raise LoiRequest("REQUEST_KHONG_RO", khong_ro=True) from None
            raise LoiRequest("REQUEST_KET_NOI") from None
        if not isinstance(r, PhanHoi):
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", khong_ro=ghi)
        st = r.status
        if 300 <= st < 400:
            raise LoiRequest("REQUEST_CHUYEN_HUONG", status=st, khong_ro=ghi)
        if st >= 400:
            ra = _retry_after(r.headers.get("retry-after")) if st in (429, 503) else None
            truong = _ma_truong_loi(r.body) if st == 422 else ()
            ma = f"REQUEST_{st}" if st in (400, 401, 403, 404, 409, 413, 415, 422, 429, 503) else f"REQUEST_HTTP_{st}"
            # lệnh ghi gặp 5xx (trừ 503 'chưa có khóa' trả trước xử lý) có thể đã thực hiện một phần → chưa rõ
            raise LoiRequest(ma, status=st, retry_after=ra, khong_ro=ghi and st >= 500 and st != 503, truong=truong)
        if not json_ra:
            return st, r.headers, r.body
        try:
            data = json.loads(r.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=ghi) from None
        if not isinstance(data, dict) or "duLieu" not in data:
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=ghi)
        return st, data

    # -------------------------------------------------------------- đọc cấu hình nguồn
    def nhom(self) -> tuple:
        _, d = self._goi("GET", f"{TIEN_TO}/nhom")
        if not isinstance(d["duLieu"], list):
            _sai()
        return tuple(NhomRequest.tu(x) for x in d["duLieu"])

    def danh_muc(self, ma: str) -> DanhMucRequest:
        if not isinstance(ma, str) or not MA_RE.fullmatch(ma):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        _, d = self._goi("GET", f"{TIEN_TO}/danh-muc/{quote(ma, safe='')}")
        dm = DanhMucRequest.tu(d["duLieu"])
        if dm.ma != ma:
            _sai()
        return dm

    # -------------------------------------------------------------- đề xuất
    def tao_nhap(self, body: dict, idem_key: str) -> NhapTao:
        """POST tạo nháp. Không tự retry. Mất phản hồi → LoiRequest(khong_ro=True): caller giữ NGUYÊN key + body để đối soát/gửi lại."""
        if not isinstance(idem_key, str) or not 1 <= len(idem_key) <= IDEM_TOI_DA or not re.fullmatch(r"[A-Za-z0-9_.:-]+", idem_key):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        if not isinstance(body, dict) or set(body) - {"nhom", "tieuDe", "nguoiTao", "giaTri", "truongMayDien"} or not {"nhom", "tieuDe", "nguoiTao"} <= set(body):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        st, d = self._goi("POST", f"{TIEN_TO}/de-xuat", body=raw, ghi=True,
                          headers={"Content-Type": "application/json; charset=utf-8", "Idempotency-Key": idem_key})
        if st not in (200, 201):
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=True)
        try:
            return NhapTao.tu(d["duLieu"], st)
        except LoiRequest:
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=True) from None

    def chi_tiet(self, request_id: str) -> ChiTietRequest:
        rid = _id_vao(request_id)
        _, d = self._goi("GET", f"{TIEN_TO}/de-xuat/{rid}")
        ct = ChiTietRequest.tu(d["duLieu"])
        if ct.id != rid:
            _sai()
        return ct

    def danh_sach(self, *, nhom: str | None = None, trang: int = 1, so_dong: int = 50) -> dict:
        """Danh sách phân trang — CHỈ để hiển thị; rỗng KHÔNG chứng minh chưa tạo (không có tra theo idem key)."""
        if isinstance(trang, bool) or not isinstance(trang, int) or not 1 <= trang <= 10 ** 6 or isinstance(so_dong, bool) \
                or not isinstance(so_dong, int) or not 1 <= so_dong <= 200 or (nhom is not None and not MA_RE.fullmatch(str(nhom))):
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        q = f"?trang={trang}&soDong={so_dong}" + (f"&nhom={quote(nhom, safe='')}" if nhom else "")
        _, d = self._goi("GET", f"{TIEN_TO}/de-xuat{q}")
        if not isinstance(d["duLieu"], list):
            _sai()
        return {"duLieu": d["duLieu"], "tongSo": d.get("tongSo")}

    def tai_tep(self, request_id: str, ten_tep: str, data: bytes, *, ma_truong: str, mime: str = "application/pdf") -> TepRequest:
        """Multipart `tep` + `maTruong` (ô kiểu tệp; không dùng khu chung thay ô bắt buộc). Không idem/dedup ở nguồn → mất phản hồi = khong_ro."""
        rid = _id_vao(request_id)
        if not isinstance(ma_truong, str) or not MA_RE.fullmatch(ma_truong) or not isinstance(data, (bytes, bytearray)) or not 0 < len(data) <= TEP_TOI_DA:
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        if mime != "application/pdf":
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        bd, raw = multipart({"maTruong": ma_truong}, "tep", ten_an_toan(ten_tep), mime, bytes(data))
        st, d = self._goi("POST", f"{TIEN_TO}/de-xuat/{rid}/tep", body=raw, ghi=True,
                          headers={"Content-Type": f"multipart/form-data; boundary={bd}", "Content-Length": str(len(raw))})
        if st != 201:
            raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=True)
        x = d["duLieu"]
        if isinstance(x, dict) and "khuChung" in x and "trangThaiQuet" in x:
            try:
                return TepRequest.tu({**x, "mime": x.get("mime")})
            except LoiRequest:
                pass
        raise LoiRequest("REQUEST_PHAN_HOI_SAI", status=st, khong_ro=True)

    def tai_ve(self, tep_id: str, toi_da: int) -> bytes:
        """Bytes tệp — nguồn chỉ trả khi clean (khác → 409). Giới hạn byte do caller (độ dài PDF gốc + biên nhỏ)."""
        tid = _id_vao(tep_id)
        if isinstance(toi_da, bool) or not isinstance(toi_da, int) or not 0 < toi_da <= TEP_TOI_DA:
            raise LoiRequest("REQUEST_THAM_SO_SAI")
        try:
            _, _, body = self._goi("GET", f"{TIEN_TO}/tep/{tid}", toi_da=toi_da, json_ra=False)
        except LoiRequest as exc:
            if exc.ma == "REQUEST_KHONG_RO":  # GET không có side effect: đọc dở/quá lớn = không đọc được, không phải chưa rõ ghi
                raise LoiRequest("REQUEST_DOC_DO") from None
            raise
        return body


def _id_vao(v) -> str:
    try:
        return _id(v)
    except LoiRequest:
        raise LoiRequest("REQUEST_THAM_SO_SAI") from None


def _retry_after(v) -> int | None:
    if isinstance(v, str) and v.strip().isdigit() and len(v.strip()) <= 6:
        n = int(v.strip())
        return n if n <= 86400 else None
    return None


def _ma_truong_loi(body: bytes) -> tuple:
    """Chỉ lấy MÃ trường từ loiTheoTruong (đã lọc), không câu lỗi."""
    try:
        d = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ()
    lt = d.get("loiTheoTruong") if isinstance(d, dict) else None
    if not isinstance(lt, dict):
        return ()
    return tuple(sorted(k for k in lt if isinstance(k, str) and MA_LOI_RE.fullmatch(k)))[:50]


def ten_an_toan(ten) -> str:
    if not isinstance(ten, str):
        ten = ""
    t = "".join(c if (c.isascii() and (c.isalnum() or c in "._-")) else "_" for c in ten)[:150].strip("._")
    if not t:
        t = "ho-so"
    return t if t.lower().endswith(".pdf") else t + ".pdf"


def multipart(fields: dict, ten_file_field: str, ten_tep: str, mime: str, data: bytes) -> tuple[str, bytes]:
    while True:
        bd = "m4req" + secrets.token_hex(16)
        if bd.encode("ascii") not in data:
            break
    out = []
    for k, v in fields.items():
        out.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    out.append(f'--{bd}\r\nContent-Disposition: form-data; name="{ten_file_field}"; filename="{ten_tep}"\r\nContent-Type: {mime}\r\n\r\n'.encode("utf-8"))
    out.append(data)
    out.append(f"\r\n--{bd}--\r\n".encode("ascii"))
    return bd, b"".join(out)
