"""M4-04A/04B — HTTP mỏng cho Request nháp từ hồ sơ đợt đã seal, trên LocalApp hiện có (cùng token X-KTT-Token, phiên cookie HttpOnly, mutation lock,
factory M4 `giao_dien/m4.dich_vu` và cặp kết nối riêng `_ket_noi_review`). M4-04B: `server.Handler.handle_route` chuyển ĐÚNG ba route dưới đây vào
`dieu_huong` TRƯỚC dispatcher `/api/m4*` chung; widget `/m4/m4_request_nhap.js` đọc route này.

Route:
  GET  /api/m4-request?dot_id=…[&version_id=…]            → trạng thái intent/lịch sử (không mạng) + `context` HTTP của hồ sơ đang chọn
  POST /api/m4-request/tao      {dot_id, version_id, khoa} → tạo nháp → đọc trạng thái thật → tải PDF đã seal → đối soát
  POST /api/m4-request/doi-soat {dot_id, version_id, khoa} → tiếp tục/đối soát intent đã có (UNKNOWN/chờ quét/trạng thái thật)
Trình duyệt KHÔNG gửi actor/nguoiTao/pháp nhân/số tiền/tiền tệ/nhóm/trường/endpoint/khóa/đường dẫn/PDF — có là 403 M4_CLIENT_AUTHORITY.
Cấu hình + transport do máy chủ tiêm qua seam `app._m4_request = {"cau_hinh": CauHinhRequest, "transport": …}` (server.LocalApp.gan_request_nhap);
vắng → 503 CHUA_CAU_HINH có cấu trúc (sau khi kiểm quyền), không gọi mạng. Lệnh chạy NGOÀI mutation lock trên kết nối riêng (HTTP Request có thể lâu).

M4-04B — `context` thuộc tầng HTTP (domain DTO `m4.request.nhap/1` giữ nguyên mọi key/giá trị cũ):
  {schema:"M4_REQUEST_HTTP_CONTEXT_V1", dot_id, version_id|null, dang_nhap, phap_nhan_id, seal_id|null, hien_hanh}
  lấy từ CHÍNH DuyetDot.xem cùng actor phiên (sau kiểm quyền xem Request), không từ trình duyệt/intent cũ/placeholder `d.request`.
Cổng phiên bản ở biên máy chủ (không sửa domain/API/SQL):
  - TAO: phiên bản trong body phải hiện hành + có seal thật khớp; không → 409 HOLD `PHIEN_BAN_KHONG_HIEN_HANH`, 0 mạng, không intent. Trong lúc chạy,
    mặt tiền transport kiểm lại hiện hành trước MỖI POST nguồn.
  - DOI_SOAT lịch sử: chỉ intent đã có của đúng seal; bước kế cần TAO/TAI → HOLD `LICH_SU_CAN_TAO`/`LICH_SU_CAN_TAI`, thiếu intent → HOLD
    `LICH_SU_CHUA_CO_Y_DINH` (không gọi domain → không biên nhận/sự kiện mới); còn lại chạy domain qua mặt tiền CHẶN MỌI POST (GET/tải về vẫn được).
  - Sau lệnh dài: phiên sid/login đã chụp phải còn nguyên; đổi/hết → 409 M4_REQUEST_PHIEN_DOI, không trả dữ liệu, không đụng intent đã lưu.
"""

from __future__ import annotations

import re

from ..ha_tang.primitives import DataError
from . import m4 as M4

TIEN_TO = "/api/m4-request"
TRUONG_LENH = {"dot_id", "version_id", "khoa"}
TRUONG_GET = {"dot_id", "version_id"}
ROUTE = frozenset({TIEN_TO, f"{TIEN_TO}/tao", f"{TIEN_TO}/doi-soat"})  # đúng ba đường server.py chuyển vào đây
CONTEXT_SCHEMA = "M4_REQUEST_HTTP_CONTEXT_V1"
KHONG_NHAN = M4.KHONG_NHAN | frozenset({
    "nguoiTao", "nguoi_tao", "creator", "nguoi_dung_id", "so_tien", "so_xin_thanh_toan", "gia_tri_nt", "amount", "currency", "tien_te", "giaTri",
    "gia_tri", "nhom", "phien_ban", "truong", "truongMayDien", "ma_truong", "maTruong", "khuChung", "endpoint", "origin", "host", "api_key",
    "khoa_api", "token", "bearer", "authorization", "pdf", "pdf_id", "raw", "bytes", "tep", "seal_id", "remote_id", "idem_key", "idempotency_key",
    "anh_xa", "mapping", "cau_hinh", "transport"})
_LENH = {f"{TIEN_TO}/tao": "tao", f"{TIEN_TO}/doi-soat": "doi_soat"}
_UUID_RE = re.compile(M4._UUID)
# trạng thái intent mà bước kế tiếp của domain (buoc_tiep) là POST nguồn: TAO = tạo/gửi lại cùng key; TAI = tải PDF lên
CAN_TAO = frozenset({"MOI", "CHUA_RO_TAO", "TU_CHOI_TAO"})
CAN_TAI = frozenset({"DA_TAO_NHAP"})


def cau_hinh_may_chu(app):
    """Seam máy chủ: (CauHinhRequest | None, transport | None). Không đọc .env/cấu hình thật ở gói này; không nhận gì từ request."""
    s = app.__dict__.get("_m4_request")
    if not isinstance(s, dict):
        return None, None
    return s.get("cau_hinh"), s.get("transport")


class CongTruyen:
    """Mặt tiền transport do biên máy chủ sở hữu: GET (đọc chi tiết/danh mục/tải về) đi thẳng transport gốc; mọi phương thức khác bị chặn khi
    `chan_post` hoặc khi `kiem_post()` không trả đúng True — chặn = LoiRequest REQUEST_TRANSPORT_TAT (chắc chắn CHƯA gửi), 0 byte ra dây."""

    def __init__(self, goc, *, chan_post: bool, kiem_post=None):
        self._goc, self._chan, self._kiem = goc, bool(chan_post), kiem_post
        self.bi_chan = []

    @property
    def kich_hoat(self):
        return bool(getattr(self._goc, "kich_hoat", False))

    def __repr__(self):  # không lộ transport gốc/khóa
        return f"CongTruyen(chan_post={self._chan}, kich_hoat={self.kich_hoat})"

    def gui(self, phuong_thuc, duong_dan, headers, body, toi_da_byte):
        if str(phuong_thuc).upper() != "GET":
            duoc = not self._chan
            if duoc and self._kiem is not None:
                try:
                    duoc = self._kiem() is True
                except Exception:  # không kiểm được hiện hành = không gửi
                    duoc = False
            if not duoc:
                from ..m4.request_api import LoiRequest
                self.bi_chan.append(str(phuong_thuc).upper())
                raise LoiRequest("REQUEST_TRANSPORT_TAT")
        return self._goc.gui(phuong_thuc, duong_dan, headers, body, toi_da_byte)


def _than(payload: dict, cho_phep: set) -> dict:
    cam = sorted(k for k in payload if k in KHONG_NHAN)
    if cam:
        raise DataError("M4_CLIENT_AUTHORITY", "Danh tính, người đứng tên, pháp nhân, số tiền, nhóm/trường, endpoint/khóa và PDF do máy chủ xác định; "
                                               "không nhận từ trình duyệt.")
    la = sorted(k for k in payload if k not in cho_phep)
    if la:
        raise DataError("M4_YEU_CAU_SAI", "Yêu cầu có trường ngoài phạm vi: " + ", ".join(la[:5]))
    for k, v in payload.items():
        if not isinstance(v, str):
            raise DataError("M4_YEU_CAU_SAI", f"Trường {k} phải là chuỗi.")
    return payload


def _uuid_q(query: dict, q: dict, k: str, bat_buoc: bool):
    """Tham số GET UUID chuẩn (chữ thường, có gạch). Có khóa mà rỗng/sai dạng → 400; thiếu khóa bắt buộc → 400."""
    v = q.get(k)
    if v is None:
        if bat_buoc or k in query:
            raise DataError("M4_YEU_CAU_SAI", f"Tham số {k} thiếu hoặc rỗng.")
        return None
    if not _UUID_RE.fullmatch(v):
        raise DataError("M4_YEU_CAU_SAI", f"Tham số {k} phải là UUID chuẩn.")
    return v


def _id(v):
    if v is None:
        return None
    s = str(v)
    if not _UUID_RE.fullmatch(s):
        raise DataError("M4_REQUEST_CANONICAL_SAI", "Hồ sơ duyệt trả định danh sai kiểu — không dựng ngữ cảnh Request.")
    return s


def ngu_canh(xd, me: str, dot_id: str, version_id: str | None):
    """Context HTTP từ CHÍNH DuyetDot.xem (cùng actor/quyền, phiên bản đã chọn; None = mới nhất). Trả (context, hồ sơ DTO)."""
    from ..m4 import duyet_dot as DD
    hs = DD.DuyetDot(xd).xem(me, dot_id=dot_id, version_id=version_id)
    if not (hs.get("quyen") or {}).get("xem"):
        raise DataError("M4_REQUEST_PHAM_VI", "Vai hiện hành không được xem hồ sơ duyệt của đợt này.")
    c = hs.get("context") or {}
    chua_nop = hs.get("chua_nop") is True
    dot, pb, pn = _id(c.get("dot_id")), _id(c.get("version_id")), _id(c.get("phap_nhan_id"))
    if dot != dot_id or pn is None or (version_id is not None and pb != version_id) or (chua_nop and pb is not None) or (not chua_nop and pb is None):
        raise DataError("M4_REQUEST_CANONICAL_SAI", "Hồ sơ duyệt không khớp đợt/phiên bản đã chọn — không dựng ngữ cảnh Request.")
    seal = hs.get("seal") if isinstance(hs.get("seal"), dict) else None
    seal_id = None
    if seal is not None and not chua_nop and _id(seal.get("version_id")) == pb:
        seal_id = _id(seal.get("id"))
    hien = hs.get("phien_ban_hien_hanh") is True and not chua_nop
    return {"schema": CONTEXT_SCHEMA, "dot_id": dot, "version_id": pb, "dang_nhap": me, "phap_nhan_id": pn, "seal_id": seal_id,
            "hien_hanh": hien}, hs


def _status_ket_qua(r: dict) -> int:
    tt = r.get("trang_thai")
    return 503 if tt == "CHUA_CAU_HINH" else 409 if tt in ("CAU_HINH_LECH", "HOLD") else 502 if tt == "LOI_REQUEST" else 200


def _hold(chan: str, y: dict | None = None) -> dict:
    """HOLD có cấu trúc của biên HTTP (cùng schema domain): không gọi domain, không biên nhận/intent/sự kiện mới, giữ nguyên intent gốc."""
    from ..m4.request_nhap import SCHEMA
    return {"schema": SCHEMA, "trang_thai": "HOLD", "lap_lai": False, "chan": chan, "buoc": [], "loi": [],
            "y_dinh": None if y is None else {k: v for k, v in y.items() if k != "su_kien"}}


def _lenh(xd, ch, t, me: str, ten: str, p: dict) -> dict:
    """Một lệnh trên kết nối riêng: quyền → context canonical → cổng hiện hành/lịch sử → domain qua mặt tiền transport."""
    from ..m4 import duyet_dot as DD
    from ..m4.request_nhap import RequestNhap
    dot, pb = DD._uuid(p.get("dot_id"), "dot_id"), DD._uuid(p.get("version_id"), "version_id")
    x = RequestNhap(xd, ch, None).xem(me, dot_id=dot)  # quyền thấy đợt (KHONG_THAY) + intent đã lưu; không mạng
    if not x["quyen"]["tai_pdf"]:
        raise DataError("M4_REQUEST_PHAM_VI", "Vai hiện hành không được tạo/đối soát Request từ hồ sơ đã duyệt.")
    ctx, _ = ngu_canh(xd, me, dot, pb)
    if ten == "tao" or ctx["hien_hanh"]:
        if not ctx["hien_hanh"]:
            return {**_hold("PHIEN_BAN_KHONG_HIEN_HANH"), "context": ctx}

        def con_hien_hanh():  # trước MỖI POST nguồn: phiên bản body vẫn mới nhất và seal thật vẫn là seal đã chụp
            c2, _ = ngu_canh(xd, me, dot, pb)
            return c2["hien_hanh"] is True and c2["seal_id"] is not None and c2["seal_id"] == ctx["seal_id"]
        cong, chan = (None if t is None else CongTruyen(t, chan_post=False, kiem_post=con_hien_hanh)), "PHIEN_BAN_KHONG_HIEN_HANH"
    else:
        if ctx["seal_id"] is None:
            raise DataError("M4_REQUEST_CHUA_SEAL", "Phiên bản đã chọn chưa có seal — không có Request để đối soát.")
        ds = [y for y in x["y_dinh"] if y.get("phien_ban_id") == pb and y.get("seal_id") == ctx["seal_id"]]
        if not ds:
            return {**_hold("LICH_SU_CHUA_CO_Y_DINH"), "context": ctx}
        can = next((y for y in reversed(ds) if y.get("trang_thai") in CAN_TAO | CAN_TAI), None)
        if can is not None:
            return {**_hold("LICH_SU_CAN_TAO" if can["trang_thai"] in CAN_TAO else "LICH_SU_CAN_TAI", can), "context": ctx}
        cong, chan = (None if t is None else CongTruyen(t, chan_post=True)), "LICH_SU_CHAN_POST"
    rq = RequestNhap(xd, ch, cong)
    fn = rq.tao if ten == "tao" else rq.doi_soat
    r = fn(me, dot_id=dot, version_id=pb, khoa=p.get("khoa"))
    if cong is not None and cong.bi_chan:  # mặt tiền đã chặn POST: không coi là tiến triển; intent giữ trạng thái domain đã ghi
        r = {**r, "trang_thai": "HOLD", "chan": chan}
    return {**r, "context": ctx}


def _rieng(app, svc, me: str, ten: str, p: dict) -> dict:
    """Kết nối riêng (login ứng dụng + chủ bảng đã kiểm) cho một lệnh; người gọi không giữ mutation lock. Đóng ở mọi nhánh, không xóa gì."""
    from ..k2.xay_dung import XayDungK2
    ch, t = cau_hinh_may_chu(app)
    web, chu = M4._ket_noi_review(app)
    try:
        xd = XayDungK2(web, svc.root, conn_tin_cay=chu, chi_mo_phong=svc.chi_mo_phong, hom_nay=svc.hom_nay)
        return app._crm_db(lambda: _lenh(xd, ch, t, me, ten, p))
    finally:
        chu.close()
        web.close()


def _con_phien(app, sid, me) -> bool:
    with app.mutation_lock:
        return sid is not None and app.__dict__.get("_crm_phien", {}).get(sid) == me


def dieu_huong(h, app, post: bool, path: str, query: dict):
    from ..m4.request_nhap import RequestNhap, ma_http
    try:
        if not post and path == TIEN_TO:
            q = M4._q(query, TRUONG_GET)
            dot, pb = _uuid_q(query, q, "dot_id", True), _uuid_q(query, q, "version_id", False)
            ch, t = cau_hinh_may_chu(app)
            with app.mutation_lock:
                _, me, _ = app.crm_phien(h.crm_sid())
                svc = M4.dich_vu(app)

                def doc():
                    r = RequestNhap(svc, ch, t).xem(me, dot_id=dot)  # kiểm quyền Request TRƯỚC khi dựng context
                    ctx, _ = ngu_canh(svc, me, dot, pb)
                    return {**r, "context": ctx}
                r = app._crm_db(doc)
            return h.send_content(200, r, headers={"Cache-Control": "no-store"})
        if post and path in _LENH:
            # FIX02: đọc body ĐÚNG MỘT LẦN, có giới hạn 16 KiB, TRƯỚC khi từ chối query — để không đóng kết nối HTTP/1.0 với payload chưa đọc
            # (Win10053); sau đó query vẫn strict và guard authority/shape vẫn chạy trước mọi app/phiên/service/DB/transport
            body = h.json_body(16 * 1024)
            M4._q(query, set())
            payload = _than(body, TRUONG_LENH)
            with app.mutation_lock:  # chỉ chụp danh tính phiên + service; HTTP Request chạy ngoài lock
                sid, me, _ = app.crm_phien(h.crm_sid())
                svc = M4.dich_vu(app)
            loi, r = None, None
            try:
                r = _rieng(app, svc, me, _LENH[path], payload)
            except DataError as exc:
                loi = exc
            if not _con_phien(app, sid, me):  # phiên đổi/hết trong lúc chạy: không echo actor cũ, intent đã lưu giữ nguyên
                return h.send_content(409, {"error": "M4_REQUEST_PHIEN_DOI", "message": "Phiên đăng nhập đã đổi trong lúc xử lý — kết quả không hiển "
                                                                                        "thị cho phiên mới; tải lại trạng thái Request để đối soát."},
                                      headers={"Cache-Control": "no-store"})
            if loi is not None:
                raise loi
            return h.send_content(_status_ket_qua(r), r, headers={"Cache-Control": "no-store"})
        return h.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
    except DataError as exc:
        st = ma_http(exc.code)
        if st == 400:
            st = (403 if exc.code in M4.MA_403 else 404 if exc.code in M4.MA_404 else 409 if exc.code in M4.MA_409 else 503 if exc.code in M4.MA_503
                  else 413 if exc.code in M4.MA_413 else 400)
        return h.send_content(st, {"error": exc.code, "message": str(exc)})
    except (ValueError, TypeError, KeyError, RecursionError):
        return h.send_content(400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; chưa xử lý."})
    except OSError:
        return h.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc được kho trên máy. Dữ liệu đã lưu vẫn được giữ."})
