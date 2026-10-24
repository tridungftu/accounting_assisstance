"""CRM-41-01 — client CHUNG của engine trích tham số #6 (contract `trich-tham-so-common/v1`) + MỘT projection `bang[] → tham_so[]`.

Một lõi duy nhất ở dự án nguồn #6 (`review_xaydung/trich_xuat`), gọi qua API HTTP loopback của chính nó; central KHÔNG import/copy lõi trích.
Hai consumer thật dùng file này: M4 (`m4/nguon_review.trich_hop_dong` → `k2/xay_dung.trich`) và CRM (`k2/crm.trich_tu_docx`).

Đường gọi (bám API nguồn thật, docs/CRM-41-01-SOURCE-PATCH/API.md + may_chu/server.py):
  POST /api/trich_xuat {} → {luot}; POST /api/trich_xuat/{luot}/tep?ten=<urlencoded .docx> (raw bytes);
  POST /api/trich_xuat/{luot}/chay {contract, mode, loai_hop_dong, catalog_id, catalog_sha256, source_sha256, request_id, tham_so} → {viec, ...};
  GET /api/trich_xuat/{luot} → trạng thái + hd[].tai.json; GET <tai.json> → bytes JSON GỐC (không dùng view GET hd/{ten});
  POST /api/trich_xuat/{luot}/dung — chỉ dừng lượt thuộc ý định của client. Lỗi nguồn: {"loi", "chi_tiet"}.
Header X-HD: 1 và Host khớp nguồn. Base URL do HOST cấp tường minh (KHO_TRICH6_URL hoặc constructor): chỉ http://127.0.0.1|localhost:<port>,
không mặc định cổng, không redirect, không LAN; thiếu → NOT_READY. Không gọi nap_csdl/xác nhận/duyệt/cài đặt/DELETE.

Ý định bền vững (không dựng queue thứ hai): mỗi request_id có thư mục chỉ-ghi-thêm `<goc>/trich6-y-dinh/<sha256(request_id)>/` (FIX01 F1: tên băm,
an toàn Windows; ID logic giữ trong 00_yeu_cau.json) lưu bytes + yêu cầu gốc, lượt (create common idempotent ở nguồn — FIX01 F2),
phản hồi start và raw kết quả (write_immutable). Thử lại CÙNG ý định đối soát lượt/kết quả đã biết; khác body/catalog/mã → xung đột; kết nối
đứt sau khi gửi lệnh có hiệu lực → ChuaRo (UNKNOWN), không tự tạo/chạy lại khi chưa rõ. Lệnh start nguồn idempotent theo request_id+body.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable

CONTRACT = "trich-tham-so-common/v1"
MODE = "RULE_ONLY"
ADAPTER_VERSION = "trich-chung-6-projection-v1"
ENV_URL = "KHO_TRICH6_URL"
HEADER_TOKEN = "X-Trich6-Token"  # CRM-41-01-06: header quyền nội bộ của engine DEMO do host sở hữu (giá trị chỉ trong bộ nhớ)
# Catalog đã bind (binding CRM-41-01): chỉ XD có danh mục thật. Loại khác chưa có catalog → không hỗ trợ, KHÔNG mượn XD.
CATALOG = {"XD": {"catalog_id": "XD", "catalog_sha256": "05846a2acd60f2cde708d13a163a137ee3fb0b4e08fd84f85a7e14e7ef861bcd"}}
RE_REQUEST_ID = re.compile(r"[A-Za-z0-9_.:-]{1,200}")
RE_LUOT = re.compile(r"\d{8}_\d{6}(?:_\d+)?")
TRANG_THAI_XONG = ("xong",)
TRANG_THAI_HONG = ("loi", "da_dung")
THAM_SO_KEYS = ("ma", "nhom", "tham_so", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu", "kiem_tra", "vi_tri_do_duoc")


class LoiNguon(DataError):
    """Nguồn #6 trả lỗi rõ ({loi, chi_tiet}) — không phải UNKNOWN."""
    def __init__(self, status: int, ma: str, thong_bao: str, chi_tiet=None):
        super().__init__(ma, thong_bao)
        self.status, self.chi_tiet = status, chi_tiet


class ChuaRo(DataError):
    """UNKNOWN: lệnh có hiệu lực đã gửi nhưng không nhận được phản hồi (đứt kết nối/timeout) hoặc lượt chưa kết thúc trong hạn chờ.
    Ý định giữ nguyên; thử lại cùng ý định sẽ đối soát, không tự tạo/chạy lại."""


def _kiem_url(url: str | None) -> tuple[str, int] | None:
    if url in (None, ""):
        return None
    u = urlsplit(str(url))
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost") or u.port is None or u.username or u.password \
            or u.path not in ("", "/") or u.query or u.fragment:
        raise DataError("TRICH6_URL_SAI", "Địa chỉ engine #6 phải là http://127.0.0.1:<cổng> (loopback, có cổng, không đường dẫn).")
    return u.hostname, u.port


def _kiem_tham_so(tham_so):
    """Hình thức tập mã ở phía client (nguồn kiểm lại): 'ALL' tường minh hoặc danh sách mã không rỗng, không trùng, kiểu chuỗi."""
    if tham_so == "ALL":
        return "ALL"
    if not isinstance(tham_so, list):
        raise DataError("TRICH6_THAM_SO_SAI_KIEU", "tham_so phải là danh sách mã hoặc 'ALL'.")
    if not tham_so:
        raise DataError("TRICH6_THAM_SO_RONG", "tham_so rỗng — chọn ít nhất một mã hoặc 'ALL'.")
    if any(not isinstance(m, str) or not m.strip() or m != m.strip() for m in tham_so):
        raise DataError("TRICH6_THAM_SO_SAI_KIEU", "Mỗi mã tham số phải là chuỗi không rỗng.")
    if len(set(tham_so)) != len(tham_so):
        raise DataError("TRICH6_THAM_SO_TRUNG", "Mã tham số bị trùng.")
    return list(tham_so)


def yeu_cau_common(*, source_sha256: str, loai_hop_dong: str, tham_so, request_id: str) -> dict:
    """Body start common/v1 tường minh. Loại chưa có catalog → không hỗ trợ (không mượn XD)."""
    if loai_hop_dong not in CATALOG:
        raise DataError("TRICH6_LOAI_CHUA_CO_DANH_MUC", f"Loại hợp đồng {loai_hop_dong!r} chưa có danh mục tham số trong engine — chưa hỗ trợ trích.")
    if not isinstance(request_id, str) or not RE_REQUEST_ID.fullmatch(request_id):
        raise DataError("TRICH6_REQUEST_ID", "request_id không hợp lệ.")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise DataError("TRICH6_SOURCE_SHA", "source_sha256 phải là SHA-256 hex của tệp hợp đồng.")
    cat = CATALOG[loai_hop_dong]
    return {"contract": CONTRACT, "mode": MODE, "loai_hop_dong": loai_hop_dong, "catalog_id": cat["catalog_id"],
            "catalog_sha256": cat["catalog_sha256"], "source_sha256": source_sha256, "request_id": request_id,
            "tham_so": _kiem_tham_so(tham_so)}


def body_sha256(yc: dict) -> str:
    """FIX03 R2: hash body canonical của ý định — CÙNG quy tắc nguồn (JSON sort_keys, không khoảng trắng, UTF-8) trên đúng tám trường contract."""
    return sha256(canonical_json({k: yc[k] for k in ("contract", "mode", "loai_hop_dong", "catalog_id", "catalog_sha256", "source_sha256",
                                                     "request_id", "tham_so")}).encode("utf-8"))


def seal_hop_le(cm, luot: str, yc: dict) -> dict | None:
    """FIX03 R1: niêm phong typed của nguồn đúng ý định (request_id + body H), ref tương đối chuẩn trong lượt, SHA/độ dài kiểu đúng. Không đủ → None
    (KHÔNG phải kết quả tốt, cũng KHÔNG phải lỗi cuối)."""
    if not isinstance(cm, dict) or cm.get("tt") != "done":
        return None
    s = cm.get("seal")
    if not isinstance(s, dict) or s.get("kieu") != "seal_common/v1":
        return None
    ref, h, n = s.get("ref"), s.get("sha256"), s.get("byte_length")
    if not isinstance(ref, str) or not ref or ref.startswith("/") or "\\" in ref or any(x in ("", ".", "..") for x in ref.split("/")):
        return None
    if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) or not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        return None
    if (s.get("request_id"), s.get("body_sha256")) != (yc["request_id"], body_sha256(yc)):
        return None
    if (cm.get("request_id"), cm.get("body_sha256")) != (yc["request_id"], body_sha256(yc)):
        return None
    return s


_RE_TIEN_TO_O = re.compile(r"\\\\\?\\([A-Za-z]:\\)")


def dang_chuan_duong_dan(p) -> str:
    """FIX05 R1: dạng so sánh của một đường dẫn ĐÃ resolve. Chỉ bỏ tiền tố extended-length đúng mẫu `\\\\?\\X:\\` → `X:\\` và
    `\\\\?\\UNC\\` → `\\\\`; mọi tiền tố khác (vd `\\\\?\\Volume{…}`, `\\\\.\\`) giữ nguyên nên KHÔNG bằng đường thường. normcase theo hệ điều hành."""
    s = os.fspath(p)
    if s.startswith("\\\\?\\UNC\\"):
        s = "\\\\" + s[8:]
    elif _RE_TIEN_TO_O.match(s):
        s = s[4:]
    return os.path.normcase(s)


def cung_duong_dan(a, b) -> bool:
    return dang_chuan_duong_dan(a) == dang_chuan_duong_dan(b)


def _http_transport(host: str, port: int, timeout: float):
    def gui(method: str, path: str, headers: dict, body: bytes | None):
        c = http.client.HTTPConnection(host, port, timeout=timeout)  # không theo redirect
        try:
            c.request(method, path, body=body, headers=headers)
            r = c.getresponse()
            return r.status, (r.getheader("Content-Type") or ""), r.read()
        finally:
            c.close()
    return gui


class Trich6Client:
    """Client duy nhất của engine #6. `transport(method, path, headers, body) -> (status, content_type, bytes)` có thể tiêm trong kiểm thử
    đơn vị (IO-mock); mặc định HTTP loopback thật."""

    def __init__(self, base_url: str | None = None, *, goc: Path | None = None, timeout: float = 60.0, cho_toi_da: float = 1800.0,
                 nghi: float = 1.0, transport=None, ngu=time.sleep, dong_ho=time.monotonic, token: str | None = None):
        # base_url "" (tường minh) = chế độ do máy chủ QUẢN LÝ mà engine chưa sẵn sàng → KHÔNG rơi về biến môi trường (CRM-41-01-06)
        dia_chi = _kiem_url(base_url if base_url is not None else os.environ.get(ENV_URL))
        self.dia_chi = dia_chi
        self.goc = Path(goc) if goc is not None else None
        self.cho_toi_da, self.nghi, self.ngu, self.dong_ho = cho_toi_da, nghi, ngu, dong_ho
        self._gui = transport if transport is not None else (_http_transport(dia_chi[0], dia_chi[1], timeout) if dia_chi else None)
        # CRM-41-01-06: token quyền nội bộ của engine DEMO do host sở hữu — chỉ trong bộ nhớ, gửi bằng header riêng; không vào URL/log/lỗi/ý định
        self._token = token if isinstance(token, str) and token else None

    def __repr__(self):
        return f"Trich6Client(san_sang={self.san_sang})"  # không lộ token/địa chỉ

    @property
    def san_sang(self) -> bool:
        return self.dia_chi is not None and self._gui is not None

    def _can_san_sang(self):
        if not self.san_sang:
            raise DataError("TRICH6_CHUA_SAN_SANG", "Engine trích #6 chưa được máy chủ cấu hình (KHO_TRICH6_URL) — chưa trích; không dùng lõi chép.")

    def _co_y_dinh(self, request_id) -> bool:
        """Đã có ý định bền (00_yeu_cau) cho request_id này ở gốc client — CHỈ ĐỌC, không tạo gì."""
        if self.goc is None or not isinstance(request_id, str) or not RE_REQUEST_ID.fullmatch(request_id):
            return False
        return (self._thu_muc(request_id) / "00_yeu_cau.json").is_file()

    def kiem_giai_doan(self, request_id) -> None:
        """CRM-41-01-06 — kiểm sẵn sàng THEO GIAI ĐOẠN, chỉ đọc, trước khi caller ghi gì: engine cấu hình được → None; chưa cấu hình mà ý định
        này CHƯA từng giữ → DataError TRICH6_CHUA_SAN_SANG (lỗi rõ, zero POST/zero ghi); ĐÃ giữ (create có thể đã có hiệu lực) → ChuaRo (UNKNOWN),
        cấu hình lại sẽ đối soát đúng lượt cũ."""
        if self.san_sang:
            return
        if self._co_y_dinh(request_id):
            raise ChuaRo("TRICH6_CHUA_RO", "Ý định đã giữ nhưng engine #6 hiện chưa cấu hình/không sẵn sàng — chưa rõ; giữ nguyên ý định, thử lại "
                                           "khi engine sẵn sàng.")
        self._can_san_sang()

    # ------------------------------------------------------------------ HTTP thấp
    def _goi(self, method: str, path: str, *, json_body=None, raw: bytes | None = None, co_hieu_luc: bool):
        self._can_san_sang()
        host, port = self.dia_chi
        headers = {"Host": f"{host}:{port}", "X-HD": "1"}
        if self._token is not None:
            headers[HEADER_TOKEN] = self._token
        body = None
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif raw is not None:
            body = bytes(raw)
            headers["Content-Type"] = "application/octet-stream"
        try:
            status, ctype, data = self._gui(method, path, headers, body)
        except (OSError, http.client.HTTPException, TimeoutError) as exc:
            if co_hieu_luc:
                raise ChuaRo("TRICH6_CHUA_RO", f"Mất kết nối engine #6 sau khi gửi {method} {path.split('?')[0]} ({type(exc).__name__}) — chưa rõ kết quả; "
                                               "thử lại cùng yêu cầu để đối soát.") from None
            raise DataError("TRICH6_KHONG_KET_NOI", f"Không kết nối được engine #6 ({type(exc).__name__}).") from None
        if 300 <= status < 400:
            raise DataError("TRICH6_REDIRECT", "Engine #6 trả chuyển hướng — không theo.")
        if status >= 400:
            try:
                e = json.loads(data.decode("utf-8")) if data else {}
            except ValueError:
                e = {}
            ct = e.get("chi_tiet") if isinstance(e, dict) else None
            ma = (ct or {}).get("ma") if isinstance(ct, dict) else None
            raise LoiNguon(status, "TRICH6_" + (ma or f"HTTP_{status}"), str((e or {}).get("loi") or f"Engine #6 trả {status}"), ct)
        return ctype, data

    def _json(self, method, path, **kw):
        ctype, data = self._goi(method, path, **kw)
        try:
            v = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise DataError("TRICH6_PHAN_HOI_SAI", "Engine #6 trả phản hồi không phải JSON.") from None
        if not isinstance(v, dict):
            raise DataError("TRICH6_PHAN_HOI_SAI", "Engine #6 trả JSON không phải object.")
        return v

    # ------------------------------------------------------------------ năm thao tác được phép
    def nang_luc(self, loai_hop_dong: str) -> dict:
        """FIX04 R5 — preflight CHỈ ĐỌC trước mọi POST: GET /api/trich_xuat/common phải công bố typed đúng common/v1, RULE_ONLY, loại/catalog đã
        ghim và sẵn sàng (tính từ catalog/implementation thật của engine). Endpoint cũ (404/không JSON)/thiếu/sai kiểu/khác mode/catalog/chưa sẵn
        sàng → DataError TRICH6_KHONG_HO_TRO_COMMON (TRƯỚC side effect — không phải UNKNOWN), không fallback API cũ."""
        try:
            v = self._json("GET", "/api/trich_xuat/common", co_hieu_luc=False)
        except LoiNguon as exc:
            raise DataError("TRICH6_KHONG_HO_TRO_COMMON", f"Engine #6 không công bố common/v1 (HTTP {exc.status}) — không gọi API cũ.") from None
        except DataError as exc:
            if exc.code == "TRICH6_PHAN_HOI_SAI":
                raise DataError("TRICH6_KHONG_HO_TRO_COMMON", "Preflight common/v1 không phải JSON object — không gọi API cũ.") from None
            raise  # TRICH6_KHONG_KET_NOI: chưa gửi lệnh có hiệu lực nào → lỗi kết nối rõ, không UNKNOWN

        def sai(ly_do):
            return DataError("TRICH6_KHONG_HO_TRO_COMMON", f"Preflight common/v1 không đạt: {ly_do} — không tạo/tải/chạy.")
        if v.get("kieu") != "nang_luc_common/v1" or v.get("contract") != CONTRACT:
            raise sai("kiểu/contract")
        if not isinstance(v.get("modes"), list) or MODE not in v["modes"]:
            raise sai("mode RULE_ONLY")
        if v.get("san_sang") is not True:
            raise sai("engine chưa sẵn sàng")
        if not isinstance(v.get("create_ack"), list) or not {"luot", "lap_lai", "request_id"} <= set(x for x in v["create_ack"] if isinstance(x, str)):
            raise sai("ACK create")
        lo = v.get("loai")
        mot = lo.get(loai_hop_dong) if isinstance(lo, dict) else None
        cat = CATALOG[loai_hop_dong]
        if not isinstance(mot, dict) or mot.get("san_sang") is not True or \
                (mot.get("catalog_id"), mot.get("catalog_sha256")) != (cat["catalog_id"], cat["catalog_sha256"]):
            raise sai(f"loại {loai_hop_dong}/catalog đã ghim")
        return v

    def tao_luot(self, yeu_cau: dict | None = None) -> str:
        """FIX01 F2: có `yeu_cau` → create common/v1 idempotent ở route create sẵn có ({contract, request_id, yeu_cau}): nguồn ghi bền ý định trước
        ACK, thử lại cùng ý định trả ĐÚNG lượt cũ, khác body → 409. Không có → body {} cũ (một lượt mới mỗi lần).
        FIX04 R5: ACK common phải đúng DTO nguồn — `request_id` bằng ID logic đã gửi, `lap_lai` kiểu bool, `luot` hợp lệ; sai/thiếu SAU khi POST
        (có thể đã tạo lượt) → ChuaRo, không lưu lượt, không tải/chạy, không thử API cũ."""
        body = {} if yeu_cau is None else {"contract": CONTRACT, "request_id": yeu_cau["request_id"], "yeu_cau": yeu_cau}
        ack = self._json("POST", "/api/trich_xuat", json_body=body, co_hieu_luc=True)
        luot = ack.get("luot")
        if yeu_cau is not None and (ack.get("request_id") != yeu_cau["request_id"] or type(ack.get("lap_lai")) is not bool
                                    or not isinstance(luot, str) or not RE_LUOT.fullmatch(luot)):
            raise ChuaRo("TRICH6_ACK_SAI", "ACK create không đúng common/v1 (request_id/lap_lai/luot) — chưa rõ lượt đã tạo hay chưa; giữ ý định.")
        if not isinstance(luot, str) or not RE_LUOT.fullmatch(luot):
            raise DataError("TRICH6_PHAN_HOI_SAI", "Engine #6 không trả mã lượt hợp lệ.")
        return luot

    def tai_len(self, luot: str, ten: str, raw: bytes) -> dict:
        return self._json("POST", f"/api/trich_xuat/{luot}/tep?ten={quote(ten, safe='')}", raw=raw, co_hieu_luc=True)

    def chay(self, luot: str, body: dict) -> dict:
        return self._json("POST", f"/api/trich_xuat/{luot}/chay", json_body=body, co_hieu_luc=True)

    def doc(self, luot: str) -> dict:
        return self._json("GET", f"/api/trich_xuat/{luot}", co_hieu_luc=False)

    def doc_raw(self, duong_dan_tai: str) -> bytes:
        if not isinstance(duong_dan_tai, str) or not duong_dan_tai.startswith("/tai/") or ".." in duong_dan_tai.split("/"):
            raise DataError("TRICH6_DUONG_DAN_TAI", "Đường dẫn tải kết quả engine #6 không hợp lệ.")
        return self._goi("GET", quote(duong_dan_tai, safe="/"), co_hieu_luc=False)[1]

    def dung(self, luot: str) -> dict:
        return self._json("POST", f"/api/trich_xuat/{luot}/dung", json_body={}, co_hieu_luc=True)

    # ------------------------------------------------------------------ ý định bền vững
    def _thu_muc(self, request_id: str) -> Path | None:
        """FIX01 F1: ID logic (vd 'm4:…' có ':' — không hợp lệ làm tên thư mục Windows) KHÔNG dùng trực tiếp làm đường dẫn: tên thư mục là
        SHA-256 hex của ID (không ký tự đặc biệt, không '.'/'..', luôn nằm trong gốc). ID logic giữ nguyên trong body/biên nhận."""
        if self.goc is None:
            return None
        goc = (self.goc / "trich6-y-dinh").resolve()
        ten = sha256(request_id.encode("utf-8"))
        d = (goc / ten).resolve()
        # FIX05 R1: Windows có thể trả CÙNG thư mục ở hai biểu diễn (`D:\…` và extended `\\?\D:\…`, nhất là khi thư mục dài vừa xuất hiện) → so
        # dạng CHUẨN (chỉ bỏ đúng tiền tố extended-length của ổ đĩa/UNC, normcase). Vẫn dùng đường đã resolve (junction/symlink ra ngoài → khác cha).
        if d.name != ten or not cung_duong_dan(d.parent, goc):
            raise DataError("TRICH6_DUONG_DAN_Y_DINH", "Đường dẫn ý định ra ngoài thư mục gốc.")
        return d

    @staticmethod
    def _doc_neu_co(p: Path):
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    @staticmethod
    def _la_chua_ro(exc: Exception) -> bool:
        """Phân loại theo vòng đời: SAU khi đã gửi create (ý định có thể đã có hiệu lực ở nguồn), mất kết nối/đọc dở/5xx không mã/lượt mồ côi
        đều là UNKNOWN — không biến thành lỗi cuối (LOI)."""
        if isinstance(exc, ChuaRo):
            return True
        if isinstance(exc, LoiNguon):
            return exc.status >= 500 and exc.code.startswith("TRICH6_HTTP_") or exc.code in ("TRICH6_COMMON_MO_COI", "TRICH6_COMMON_CHUA_RO")
        return isinstance(exc, DataError) and exc.code in ("TRICH6_KHONG_KET_NOI", "TRICH6_PHAN_HOI_SAI")

    def trich(self, raw: bytes, *, ten_tep: str, loai_hop_dong: str, tham_so, request_id: str) -> dict:
        """Một lần trích qua engine #6 trên ĐÚNG MỘT tệp .docx. Gọi ngoài giao dịch K2/khóa toàn cục. Trả
        {luot, raw_ket_qua (bytes gốc), raw_sha256, ket_qua (dict), common (bản chụp nguồn), yeu_cau}.
        Vòng đời (FIX01 F2): create common idempotent (một lượt mỗi ý định, kể cả mất ACK/hai caller đồng thời) → upload (bỏ qua nếu đầu vào đã
        có/đã giữ chỗ; nguồn nhận lại cùng bytes là idempotent) → start (idempotent) → đọc/chờ → tải raw. Mọi lỗi chưa rõ SAU khi gửi create → ChuaRo
        với ý định/lượt giữ nguyên; thử lại cùng ý định đối soát tiếp, không tạo/chạy lần hai."""
        if not ten_tep.lower().endswith(".docx"):
            raise DataError("TRICH6_CHI_DOCX", "Engine common/v1 chỉ nhận đúng một tệp .docx.")
        yc = yeu_cau_common(source_sha256=sha256(bytes(raw)), loai_hop_dong=loai_hop_dong, tham_so=tham_so, request_id=request_id)
        d = self._thu_muc(request_id)
        goc = None
        if d is not None:  # FIX05 R2: tra ý định bền CHỈ ĐỌC trước preflight (không ghi gì)
            goc = self._doc_neu_co(d / "00_yeu_cau.json")
            if goc is not None and goc != {"request_id": request_id, "yeu_cau": yc}:
                raise DataError("TRICH6_XUNG_DOT", "Cùng ý định (request_id) nhưng yêu cầu khác (tệp/loại/danh mục/mã) — không chạy.")
        if not self.san_sang:  # CRM-41-01-06: kiểm cấu hình THEO GIAI ĐOẠN (sau tra ý định chỉ đọc), không chặn sớm ngoài phân loại
            if goc is not None:
                raise ChuaRo("TRICH6_CHUA_RO", f"Ý định {request_id} đã giữ nhưng engine #6 hiện chưa cấu hình — chưa rõ; giữ nguyên ý định, thử lại "
                                               "khi engine sẵn sàng.")
            self._can_san_sang()  # ý định mới: lỗi rõ, zero POST, không ghi ý định
        try:
            self.nang_luc(loai_hop_dong)  # FIX04 R5: preflight chỉ đọc TRƯỚC mọi create/upload/start; không đạt → lỗi rõ trước side effect
        except DataError as exc:
            if goc is not None:
                # FIX05 R2: ý định này ĐÃ được giữ bền (create có thể đã có hiệu lực ở nguồn) → preflight/engine không sẵn sàng lúc này KHÔNG phải lỗi
                # cuối: UNKNOWN, không POST thêm, không đổi bytes/body/khóa; thử lại khi engine đúng common sẽ đối soát đúng lượt cũ
                raise ChuaRo("TRICH6_CHUA_RO", f"Ý định {request_id} đã giữ nhưng preflight common hiện không đạt ({exc.code}) — chưa rõ; "
                                               "giữ nguyên ý định, thử lại khi engine sẵn sàng.") from None
            raise
        if d is not None:  # bytes gốc + yêu cầu gốc giữ TRƯỚC mọi tác động ra nguồn
            if goc is None:
                write_immutable(d / f"01_nguon_{yc['source_sha256']}.docx", bytes(raw))
                write_immutable(d / "00_yeu_cau.json", canonical_json({"request_id": request_id, "yeu_cau": yc}).encode("utf-8"))
        try:
            luot = self.tao_luot(yc)
            if d is not None:
                da_biet = (self._doc_neu_co(d / "10_luot.json") or {}).get("luot")
                if da_biet is not None and da_biet != luot:
                    raise DataError("TRICH6_XUNG_DOT", "Nguồn trả lượt khác lượt đã ghi cho cùng ý định.")
                if da_biet is None:
                    write_immutable(d / "10_luot.json", canonical_json({"luot": luot}).encode("utf-8"))
            s0 = self.doc(luot)
            if not s0.get("tep_dau_vao") and not s0.get("common"):  # đầu vào đã có/đã giữ chỗ → không tải lại
                try:
                    self.tai_len(luot, ten_tep, raw)  # nguồn: cùng bytes của ý định là replay (kể cả lượt đã chạy), bytes khác → 409 có mã
                except LoiNguon as exc:
                    # FIX02 R1: GET cũ thấy "chưa có đầu vào" nhưng caller khác cùng ý định đã upload/start (409 KHÔNG mã của nguồn chưa patch hoặc lịch
                    # chen) → ĐỐI SOÁT lại lượt của chính ý định, không biến thành lỗi cuối. 409 có mã (vd bytes khác) vẫn là lỗi rõ.
                    if not (exc.status == 409 and exc.code == "TRICH6_HTTP_409"):
                        raise
                    s1 = self.doc(luot)
                    if not (s1.get("tep_dau_vao") or s1.get("common")):
                        raise ChuaRo("TRICH6_CHUA_RO", "Upload bị từ chối không mã và lượt chưa có đầu vào — chưa rõ.") from None
            self.chay(luot, yc)  # nguồn idempotent theo request_id+body: lặp lại → lap_lai, không chạy lại
            if d is not None:    # biên nhận start: nội dung ỔN ĐỊNH theo ý định (không phụ thuộc lap_lai của từng caller) → ghi bất biến không va nhau
                write_immutable(d / "20_bat_dau.json", canonical_json({"luot": luot, "request_id": request_id, "contract": CONTRACT}).encode("utf-8"))
            s, seal = self._cho_xong(luot, yc)
            # FIX03 R1: chỉ tải ĐÚNG tài nguyên mà niêm phong trỏ tới (ref tương đối đầy đủ trong lượt), không chọn theo basename
            hd = [h for h in s.get("hd") or [] if isinstance(h, dict) and isinstance((h.get("tai") or {}).get("json"), str)
                  and h["tai"]["json"].endswith(f"/{luot}/{seal['ref']}")]
            if len(hd) != 1:
                raise ChuaRo("TRICH6_KET_QUA_LECH_NIEM_PHONG", "Đường tải kết quả không khớp đúng một ref đã niêm phong — chưa rõ.")
            raw_kq = self.doc_raw(hd[0]["tai"]["json"])
            if (sha256(raw_kq), len(raw_kq)) != (seal["sha256"], seal["byte_length"]):
                # FIX02 R3 + FIX03: bytes tải về khác niêm phong nguồn (đọc dở/hỏng/đổi) → UNKNOWN, không nhận
                raise ChuaRo("TRICH6_KET_QUA_LECH_NIEM_PHONG", "Kết quả tải về khác niêm phong của engine — chưa rõ, thử lại cùng yêu cầu.")
        except DataError as exc:
            if self._la_chua_ro(exc):
                raise ChuaRo("TRICH6_CHUA_RO", f"Chưa rõ kết quả engine #6 ({exc.code}) — ý định {request_id} giữ nguyên; thử lại cùng yêu cầu "
                                               "để đối soát (không tạo/chạy lần hai).") from None
            raise
        h_kq = sha256(raw_kq)
        if d is not None:
            write_immutable(d / f"30_ket_qua_{h_kq}.json", raw_kq)
        try:
            kq = json.loads(raw_kq.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise DataError("TRICH6_KET_QUA_SAI", "Kết quả engine #6 không phải JSON.") from None
        common = kiem_ket_qua(kq, yc)
        return {"luot": luot, "raw_ket_qua": raw_kq, "raw_sha256": h_kq, "ket_qua": kq, "common": common, "yeu_cau": yc}

    def _cho_xong(self, luot: str, yc: dict) -> tuple[dict, dict]:
        """FIX03 R1: chỉ nhận khi trạng thái common 'done' CÓ niêm phong hợp lệ đúng ý định. Top-level xong, thiếu common hoặc thiếu/sai niêm phong
        KHÔNG đủ — chờ tiếp, hết hạn → ChuaRo (không phải kết quả tốt, không phải lỗi cuối). Lỗi cuối chỉ khi common khẳng định loi/da_dung."""
        het = self.dong_ho() + self.cho_toi_da
        while True:
            s = self.doc(luot)
            cm = s.get("common") if isinstance(s.get("common"), dict) else {}
            if cm.get("tt") == "loi_capture":
                raise DataError("TRICH6_CHUP_LOI", "Engine #6 không chụp được đầu vào: " + str(cm.get("loi") or ""))
            if cm.get("tt") in ("unknown", "orphaned") or s.get("tt") == "unknown":  # toàn vẹn không kiểm được / mồ côi → UNKNOWN
                raise ChuaRo("TRICH6_CHUA_RO", f"Lượt {luot} ở trạng thái {cm.get('tt') or s.get('tt')}: {cm.get('loi') or ''}")
            seal = seal_hop_le(cm, luot, yc)
            if s.get("tt") in TRANG_THAI_XONG and seal is not None:
                return s, seal
            if cm.get("tt") in TRANG_THAI_HONG and s.get("tt") == cm.get("tt"):
                raise DataError("TRICH6_LUOT_" + str(cm.get("tt")).upper(), "Lượt engine #6 kết thúc không thành công: " + str(s.get("thong_bao") or cm.get("tt")))
            if self.dong_ho() >= het:  # chưa xong / xong chưa niêm phong / thiếu common / niêm phong sai ý định → UNKNOWN có lý do
                ly_do = "chưa niêm phong hợp lệ" if s.get("tt") in TRANG_THAI_XONG or cm.get("tt") == "done" else "chưa xong"
                raise ChuaRo("TRICH6_CHUA_XONG", f"Lượt {luot} {ly_do} trong hạn chờ — giữ ý định; thử lại cùng yêu cầu để đọc tiếp.")
            self.ngu(self.nghi)


def kiem_ket_qua(kq: dict, yc: dict) -> dict:
    """Kết quả gốc phải mang đúng bản chụp của CHÍNH yêu cầu này (request/source/catalog/mã) và chế độ RULE_ONLY; trả `common`."""
    if not isinstance(kq, dict) or not isinstance(kq.get("bang"), list):
        raise DataError("TRICH6_KET_QUA_SAI", "Kết quả engine #6 thiếu bang[].")
    cm = kq.get("common")
    if not isinstance(cm, dict):
        raise DataError("TRICH6_KET_QUA_KHONG_COMMON", "Kết quả không mang bản chụp common/v1 — không nhận (không trộn với đường cũ).")
    for k in ("contract", "request_id", "source_sha256", "catalog_sha256", "loai_hop_dong", "catalog_id"):
        if cm.get(k) != yc[k]:
            raise DataError("TRICH6_KET_QUA_KHAC_YEU_CAU", f"Bản chụp kết quả khác yêu cầu ở trường {k}.")
    if cm.get("body_sha256") != body_sha256(yc):  # FIX03 R2: toàn bộ body canonical, không chỉ từng trường
        raise DataError("TRICH6_KET_QUA_KHAC_YEU_CAU", "Bản chụp kết quả khác body canonical của yêu cầu.")
    if kq.get("che_do") != MODE or cm.get("mode") != MODE:
        raise DataError("TRICH6_KET_QUA_KHAC_YEU_CAU", "Kết quả không phải chế độ RULE_ONLY đã yêu cầu.")
    dung = cm.get("tham_so_da_dung")
    if not isinstance(dung, list) or not dung or (yc["tham_so"] != "ALL" and sorted(dung) != sorted(yc["tham_so"])):
        raise DataError("TRICH6_KET_QUA_KHAC_YEU_CAU", "Tập mã đã dùng khác tập mã đã yêu cầu.")
    if sorted(d.get("ma") for d in kq["bang"]) != sorted(dung):
        raise DataError("TRICH6_KET_QUA_KHAC_YEU_CAU", "bang[] không đúng tập mã đã dùng.")
    return cm


# ================================================================================================== projection DUY NHẤT bang[] → tham_so[]
def _khong_ap_dung(v: str) -> bool:
    return v.strip().lower().startswith(("không áp dụng", "khong ap dung"))


def _khong_quy_dinh(v: str) -> bool:
    return v.strip().lower().startswith(("không quy định", "khong quy dinh"))


def chieu_tham_so(kq: dict, *, raw_sha256: str, danh_muc_ma=None) -> dict:
    """bang[] nguồn → view `tham_so[]` có version adapter, liên kết về raw bằng `nguon_sha256` (KHÔNG đặt lại hash nguồn bằng hash view).
    Trạng thái mỗi mã: CO_GIA_TRI (giá trị + trích dẫn nguyên văn từ engine) / KHONG_AP_DUNG / KHONG_QUY_DINH (có trích dẫn) / CHUA_CO
    (engine chưa trích được — không điền 0) / NOT_REQUESTED (mã danh mục không được yêu cầu ở lượt này; chỉ khi truyền danh_muc_ma).
    Giữ nguyên trích dẫn/vị trí/kiểm tra/nguồn mà engine trả; không tự dựng dòng bảng typed (chưa có E3)."""
    cm = kq.get("common") or {}
    dung = list(cm.get("tham_so_da_dung") or [d.get("ma") for d in kq.get("bang") or []])
    ra = []
    for d in kq.get("bang") or []:
        v, q = str(d.get("gia_tri") or "").strip(), str(d.get("trich_dan") or "").strip()
        tt = "CHUA_CO"
        if v and q:
            tt = "KHONG_AP_DUNG" if _khong_ap_dung(v) else "KHONG_QUY_DINH" if _khong_quy_dinh(v) else "CO_GIA_TRI"
        ra.append({**{k: d.get(k) for k in THAM_SO_KEYS}, "nguon": d.get("nguon"), "trang_thai": tt})
    if danh_muc_ma is not None:
        co = {r["ma"] for r in ra}
        ra += [{**{k: None for k in THAM_SO_KEYS}, "ma": m, "nguon": None, "trang_thai": "NOT_REQUESTED"} for m in danh_muc_ma if m not in co]
    return {"adapter": ADAPTER_VERSION, "contract": cm.get("contract"), "nguon_sha256": raw_sha256, "che_do": kq.get("che_do"),
            "hop_dong": kq.get("hop_dong"), "tao_luc": kq.get("tao_luc"), "model": None, "phieu_kiem_tra": kq.get("phieu_kiem_tra"),
            "tham_so_da_dung": dung, "common": {k: v for k, v in cm.items() if k != "tham_so_snapshot"}, "tham_so": ra}


def view_bytes(view: dict) -> bytes:
    """Bytes của view chuẩn hóa (hash riêng, khác raw nguồn)."""
    return canonical_json(view).encode("utf-8")
