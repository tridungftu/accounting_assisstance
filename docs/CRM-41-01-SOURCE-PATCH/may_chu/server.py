# -*- coding: utf-8 -*-
"""
server.py — Máy chủ web trên máy anh Dũng (chỉ thư viện chuẩn Python): http://localhost:8600
  - Phục vụ giao diện (thư mục giao_dien\\: index.html khi đã ghép thiết kế; chưa có thì trang tạm tam.html).
  - API JSON cho mọi chức năng (xem API.md).
Bảo mật: chỉ nghe 127.0.0.1; chặn yêu cầu từ trang web khác (kiểm tra Host, Origin; POST/PUT/PATCH/DELETE phải có
header X-HD: 1). Tải xuống chỉ trong thư mục ket_qua_AI\\.
"""
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from trich_xuat import PHIEN_BAN
from trich_xuat.cau_hinh import GOC

from . import dich_vu as dv

PORT = int(os.environ.get("HD_PORT", "8600"))
GIAO_DIEN = GOC / "giao_dien"
LOAI_TEP = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".png": "image/png", ".svg": "image/svg+xml",
            ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".ico": "image/x-icon",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ROUTES = []


def route(method, pattern):
    rx = re.compile("^" + pattern + "$")

    def deco(f):
        ROUTES.append((method, rx, f))
        return f
    return deco


def _q(req, k, mac_dinh=None):
    return (req.query.get(k) or [mac_dinh])[0]


# ------------------------------------------------------------------ hệ thống
@route("GET", r"/api/phien_ban")
def _pb(req):
    return {"phien_ban": PHIEN_BAN, "dang_chay": len(dv.QLV.dang_chay())}


@route("GET", r"/api/he_thong")
def _ht(req):
    return dv.he_thong()


@route("GET", r"/api/tong_quan")
def _tq(req):
    return dv.tong_quan()


@route("GET", r"/api/ai")
def _ai(req):
    return dv.trang_thai_ai(lam_moi=_q(req, "lam_moi") == "1")


# ------------------------------------------------------------------ cài đặt
@route("GET", r"/api/cai_dat")
def _cd(req):
    return dv.lay_cai_dat()


@route("POST", r"/api/cai_dat")
def _cd_luu(req):
    return dv.luu_cai_dat(req.json())


@route("POST", r"/api/cai_dat/kiem_tra_ai")
def _cd_kt(req):
    return dv.kiem_tra_may_ai(req.json())


@route("POST", r"/api/cai_dat/thu_cloud")
def _cd_thu_cloud(req):
    return dv.thu_cloud(req.json())


@route("POST", r"/api/cai_dat/tim_may_ai")
def _cd_tim(req):
    return dv.tim_may_ai(req.json().get("cong"))


@route("POST", r"/api/cai_dat/khoa")
def _cd_khoa(req):
    return dv.luu_khoa(req.json())


@route("DELETE", r"/api/cai_dat/khoa/(anthropic|openai)")
def _cd_xoa_khoa(req, ncc):
    return dv.xoa_khoa(ncc)


@route("GET", r"/api/ocr/trang_thai")
def _ocr_tt(req):
    return dv.trang_thai_ocr(lam_moi=_q(req, "lam_moi") == "1")


@route("POST", r"/api/phu_luc_ai/tai_len")
def _plai_tl(req):
    return dv.pl_ai_tai_len(_q(req, "ten", ""), req.raw())


@route("POST", r"/api/phu_luc_ai/chay")
def _plai_chay(req):
    return dv.pl_ai_chay(req.json())


@route("GET", r"/api/phu_luc_ai")
def _plai_ds(req):
    return dv.pl_ai_ds()


@route("GET", r"/api/phu_luc_ai/(\d{14}_[0-9a-f]{8})")
def _plai_xem(req, id_):
    return dv.pl_ai_xem(id_)


@route("POST", r"/api/phu_luc_ai/(\d{14}_[0-9a-f]{8})/cap_nhat")
def _plai_cn(req, id_):
    return dv.pl_ai_cap_nhat(id_, req.json())


@route("POST", r"/api/phu_luc_ai/(\d{14}_[0-9a-f]{8})/hoi_lai_ai")
def _plai_hl(req, id_):
    return dv.pl_ai_hoi_lai(id_)


@route("POST", r"/api/phu_luc_ai/(\d{14}_[0-9a-f]{8})/nap")
def _plai_nap(req, id_):
    return dv.pl_ai_nap(id_)


@route("DELETE", r"/api/phu_luc_ai/(\d{14}_[0-9a-f]{8})")
def _plai_xoa(req, id_):
    return dv.pl_ai_xoa(id_)


@route("POST", r"/api/chung_tu/tai_len")
def _ct_tl(req):
    return dv.ct_tai_len(_q(req, "ten", ""), req.raw())


@route("POST", r"/api/chung_tu/chay")
def _ct_chay(req):
    return dv.ct_chay(req.json())


@route("GET", r"/api/chung_tu")
def _ct_ds(req):
    return dv.ct_ds()


@route("GET", r"/api/chung_tu/(\d{14}_[0-9a-f]{8})")
def _ct_xem(req, id_):
    return dv.ct_xem(id_)


@route("POST", r"/api/chung_tu/(\d{14}_[0-9a-f]{8})/cap_nhat")
def _ct_cn(req, id_):
    return dv.ct_cap_nhat(id_, req.json())


@route("DELETE", r"/api/chung_tu/(\d{14}_[0-9a-f]{8})")
def _ct_xoa(req, id_):
    return dv.ct_xoa(id_)


@route("POST", r"/api/ocr/chay_thu")
def _ocr_thu(req):
    return dv.chay_thu_ocr()


@route("GET", r"/api/cai_dat/nhat_ky_gui_ngoai")
def _cd_nk(req):
    return {"ds": dv.danh_sach_nhat_ky_gui_ngoai()}


@route("POST", r"/api/csdl/sao_luu")
def _cd_sl(req):
    return dv.sao_luu_csdl()


# ------------------------------------------------------------------ danh mục tham số
@route("GET", r"/api/tham_so")
def _ts(req):
    return dv.lay_tham_so()


@route("PUT", r"/api/tham_so")
def _ts_luu(req):
    return dv.luu_tham_so(req.json())


# ------------------------------------------------------------------ việc chạy nền
@route("GET", r"/api/viec")
def _viec(req):
    return {"ds": dv.QLV.danh_sach()}


@route("GET", r"/api/viec/([\w\-]+)")
def _viec1(req, id_):
    try:
        return dv.QLV.lay(id_).to_dict(day_du=True)
    except KeyError as e:
        raise dv.LoiNguoiDung(404, str(e)) from None


@route("POST", r"/api/viec/([\w\-]+)/dung")
def _viec_dung(req, id_):
    try:
        return dv.QLV.dung(id_)
    except KeyError as e:
        raise dv.LoiNguoiDung(404, str(e)) from None


# ------------------------------------------------------------------ trích tham số hợp đồng
@route("GET", r"/api/trich_xuat/common")
def _tx_nang_luc(req):
    # CRM-41-01 FIX04 R5: preflight chỉ đọc của common/v1 (client chung kiểm TRƯỚC create); server cũ không có route này → client fail closed
    return dv.nang_luc_common()


@route("GET", r"/api/trich_xuat")
def _tx_ds(req):
    return {"ds": dv.ds_luot(int(_q(req, "gioi_han", "50")))}


@route("POST", r"/api/trich_xuat")
def _tx_moi(req):
    b = req.json()
    if "contract" in b:                   # CRM-41-01 FIX01: create common/v1 idempotent theo request_id + yêu cầu đầy đủ; body {} cũ giữ nguyên
        return dv.luot_moi_common(b)
    return dv.luot_moi()


@route("GET", r"/api/trich_xuat/([\d_]+)")
def _tx(req, luot):
    return dv.chi_tiet_luot(luot)


@route("DELETE", r"/api/trich_xuat/([\d_]+)")
def _tx_xoa(req, luot):
    return dv.xoa_luot(luot)


@route("POST", r"/api/trich_xuat/([\d_]+)/tep")
def _tx_tep(req, luot):
    return dv.tai_len_hop_dong(luot, _q(req, "ten", ""), req.raw())


@route("DELETE", r"/api/trich_xuat/([\d_]+)/tep/(.+)")
def _tx_xoa_tep(req, luot, ten):
    return dv.xoa_tep_luot(luot, urllib.parse.unquote(ten))


@route("POST", r"/api/trich_xuat/([\d_]+)/chay")
def _tx_chay(req, luot):
    return dv.chay_luot(luot, req.json())


@route("POST", r"/api/trich_xuat/([\d_]+)/chay_lai")
def _tx_chay_lai(req, luot):
    return dv.chay_lai_luot(luot, req.json())


@route("POST", r"/api/trich_xuat/([\d_]+)/dung")
def _tx_dung(req, luot):
    try:
        return dv.QLV.dung(f"TX-{luot}")
    except KeyError:
        raise dv.LoiNguoiDung(404, "Lượt này không chạy") from None


@route("POST", r"/api/trich_xuat/([\d_]+)/danh_muc")
def _tx_dm(req, luot):
    return dv.ghi_lai_danh_muc(luot, _q(req, "ten"))


@route("GET", r"/api/trich_xuat/([\d_]+)/hd/([^/]+)")
def _tx_hd(req, luot, ten):
    return dv.ket_qua_hd(luot, urllib.parse.unquote(ten))


@route("PATCH", r"/api/trich_xuat/([\d_]+)/hd/([^/]+)/o/([\w\-]+)")
def _tx_o(req, luot, ten, ma):
    return dv.sua_o(luot, urllib.parse.unquote(ten), ma, req.json())


@route("POST", r"/api/trich_xuat/([\d_]+)/hd/([^/]+)/xac_nhan")
def _tx_xn(req, luot, ten):
    return dv.xac_nhan_nhieu(luot, urllib.parse.unquote(ten), req.json())


@route("POST", r"/api/trich_xuat/([\d_]+)/hd/([^/]+)/nap_csdl")
def _tx_nap(req, luot, ten):
    return dv.nap_csdl_tu_ket_qua(luot, urllib.parse.unquote(ten), req.json())


# ------------------------------------------------------------------ CSDL hợp đồng / phụ lục / BOQ / đợt
@route("GET", r"/api/hop_dong")
def _hd_ds(req):
    return {"ds": dv.ds_hop_dong()}


@route("GET", r"/api/hop_dong/([\w\-]+)")
def _hd(req, ref):
    return dv.chi_tiet_hop_dong(ref, _q(req, "ngay"))


@route("GET", r"/api/hop_dong/([\w\-]+)/boq")
def _hd_boq(req, ref):
    return dv.boq_hieu_luc(ref, _q(req, "ngay"))


@route("POST", r"/api/hop_dong/([\w\-]+)/phieu_phu_luc")
def _hd_phieu(req, ref):
    return dv.tao_phieu_phu_luc(ref)


@route("POST", r"/api/hop_dong/([\w\-]+)/phu_luc/([\w\-]+)/huy")
def _hd_huy(req, ref, so_pl):
    return dv.huy_phu_luc(ref, so_pl, req.json().get("ly_do", ""))


@route("POST", r"/api/hop_dong/([\w\-]+)/kiem_dot")
def _hd_dot(req, ref):
    dot = _q(req, "dot")
    return dv.kiem_tra_dot(ref, _q(req, "ten", ""), req.raw(), _q(req, "ngay_nghiem_thu"),
                           int(dot) if dot and dot.isdigit() else None)


@route("POST", r"/api/phu_luc/(kiem_tra|nap)")
def _pl(req, lenh):
    return dv.nap_phieu_phu_luc(_q(req, "ten", ""), req.raw(), chi_kiem_tra=(lenh == "kiem_tra"))


@route("POST", r"/api/toan_ven")
def _tv(req):
    return dv.kiem_tra_toan_ven(_q(req, "ten", ""), req.raw(), _q(req, "o"))


@route("POST", r"/api/hop_dong/([\w\-]+)/tham_so/([\w\-]+)/xac_nhan")
def _hd_ts_xn(req, ref, ma_ts):
    return dv.xac_nhan_tham_so_csdl(ref, ma_ts, req.json())


@route("GET", r"/api/hop_dong/([\w\-]+)/phu_luc/([\w\-]+)")
def _hd_pl(req, ref, so_pl):
    return dv.chi_tiet_phu_luc(ref, so_pl)


@route("GET", r"/api/kiem_tra/(kiem_tra_dot|toan_ven)")
def _kt_ds(req, loai):
    return dv.ket_qua_kiem_tra(loai)


@route("GET", r"/api/kiem_tra/(kiem_tra_dot|toan_ven)/([\w\-]+)")
def _kt(req, loai, ma):
    return dv.ket_qua_kiem_tra(loai, ma)


@route("POST", r"/api/kiem_tra/kiem_tra_dot/([\w\-]+)/nap")
def _kt_nap(req, ma):
    return dv.nap_dot_da_duyet(ma, req.json())


@route("POST", r"/api/kiem_tra/kiem_tra_dot/([\w\-]+)/ghep")
def _kt_ghep(req, ma):
    return dv.ghep_hang_muc(ma, req.json())


@route("POST", r"/api/kiem_tra/kiem_tra_dot/([\w\-]+)/chay_lai")
def _kt_chay_lai(req, ma):
    return dv.chay_lai_kiem_tra_dot(ma)


@route("POST", r"/api/boq/tai_len")
def _boq_tl(req):
    return dv.boq_tai_len(_q(req, "ten", ""), req.raw())


@route("POST", r"/api/boq/sheet")
def _boq_sh(req):
    return dv.boq_xem_sheet(req.json())


@route("POST", r"/api/boq/kiem_tra")
def _boq_kt(req):
    return dv.boq_kiem_tra(req.json())


@route("POST", r"/api/boq/ghi")
def _boq_ghi(req):
    return dv.boq_ghi(req.json())


@route("POST", r"/api/csdl/xuat_excel")
def _csdl_xuat(req):
    d = req.json()
    return dv.xuat_csdl_excel(d.get("ref"), d.get("ngay"))


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "ReviewXayDung/1"
    _body = None

    def log_message(self, fmt, *a):
        pass

    def _hop_le(self, ghi):
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"localhost:{PORT}", f"127.0.0.1:{PORT}"):
            return False
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return False
        return not ghi or self.headers.get("X-HD") == "1"

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    # dữ liệu gửi lên
    def raw(self):
        if self._body is None:
            n = int(self.headers.get("Content-Length") or 0)
            if n > dv.MAX_FILE + 1024:
                raise dv.LoiNguoiDung(413, "File quá lớn")
            self._body = self.rfile.read(n) if n > 0 else b""
        return self._body

    def json(self):
        b = self.raw()
        if not b:
            return {}
        try:
            d = json.loads(b.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise dv.LoiNguoiDung(400, "Dữ liệu JSON không hợp lệ") from None
        if not isinstance(d, dict):
            raise dv.LoiNguoiDung(400, "Dữ liệu JSON phải là object")
        return d

    def _xu_ly(self, method):
        u = urllib.parse.urlsplit(self.path)
        self.query = urllib.parse.parse_qs(u.query)
        path = u.path
        if not self._hop_le(method != "GET"):
            return self._send(403, {"loi": f"Chỉ mở từ http://localhost:{PORT}"})
        try:
            if method == "GET" and not path.startswith("/api/"):
                return self._tinh(path)
            for m, rx, f in ROUTES:
                if m == method:
                    mt = rx.match(path)
                    if mt:
                        return self._send(200, f(self, *mt.groups()))
            return self._send(404, {"loi": "Không có chức năng này"})
        except dv.LoiNguoiDung as e:
            return self._send(e.ma, {"loi": e.thong_bao, "chi_tiet": e.chi_tiet})
        except SystemExit as e:                    # csdl_hop_dong báo lỗi người dùng bằng SystemExit
            return self._send(400, {"loi": str(e)})
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            return self._send(500, {"loi": f"Lỗi máy chủ: {type(e).__name__}: {str(e)[:300]}"})

    def do_GET(self):
        self._xu_ly("GET")

    def do_POST(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/api/tat":
            if not self._hop_le(True):
                return self._send(403, {"loi": "Yêu cầu không hợp lệ"})
            if dv.QLV.dang_chay():
                return self._send(409, {"loi": "Đang có việc chạy — chờ xong rồi mở lại"})
            self._send(200, {"ok": True})
            srv = self.server
            threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()
            return
        self._xu_ly("POST")

    def do_PUT(self):
        self._xu_ly("PUT")

    def do_PATCH(self):
        self._xu_ly("PATCH")

    def do_DELETE(self):
        self._xu_ly("DELETE")

    # file tĩnh + tải xuống
    def _tinh(self, path):
        if path.startswith("/tai/"):
            p = dv.file_tai(urllib.parse.unquote(path[5:]))
            ten = p.name
            ctype = LOAI_TEP.get(p.suffix.lower(), "application/octet-stream")
            disp = "inline" if _q(self, "xem") else "attachment"
            return self._send(200, p.read_bytes(), ctype,
                              {"Content-Disposition": f"{disp}; filename=\"{ten.encode('ascii', 'replace').decode()}\"; "
                                                      f"filename*=UTF-8''{urllib.parse.quote(ten)}"})
        if path in ("/", "/index.html"):
            p = GIAO_DIEN / "index.html"
            if not p.exists():
                p = GIAO_DIEN / "tam.html"
            if not p.exists():
                return self._send(200, f"<h1>Máy chủ đang chạy (phiên bản {PHIEN_BAN})</h1><p>Chưa có giao diện.</p>",
                                  "text/html; charset=utf-8")
            return self._send(200, p.read_bytes(), "text/html; charset=utf-8")
        rel = urllib.parse.unquote(path.lstrip("/"))
        goc = GIAO_DIEN.resolve()
        p = (goc / rel).resolve()
        if goc in p.parents and p.is_file() and p.suffix.lower() in LOAI_TEP:
            return self._send(200, p.read_bytes(), LOAI_TEP[p.suffix.lower()])
        return self._send(404, {"loi": "Không có trang này"})


class MayChu(ThreadingHTTPServer):
    """Windows: tắt SO_REUSEADDR, dùng SO_EXCLUSIVEADDRUSE để không có 2 bản cùng nghe một cổng."""
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def tao_may_chu(port=None):
    global PORT
    if port is not None:
        PORT = port
    srv = MayChu(("127.0.0.1", PORT), Handler)
    PORT = srv.server_address[1]
    return srv


def _hoi_cong(path, method="GET"):
    """Gọi chương trình đang giữ cổng PORT → (mã HTTP, header Server, JSON hoặc None). Lỗi kết nối → (None, "", None)."""
    hdr = {"X-HD": "1", "Host": f"localhost:{PORT}"}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", headers=hdr, method=method,
                                 data=b"{}" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            b, ma, sv = r.read(), r.status, r.headers.get("Server", "")
    except urllib.error.HTTPError as e:
        b, ma, sv = e.read(), e.code, e.headers.get("Server", "")
    except Exception:  # noqa: BLE001
        return None, "", None
    try:
        return ma, sv, json.loads(b.decode("utf-8"))
    except ValueError:
        return ma, sv, None


def _pid_giu_cong():
    """Windows: (pid, tên tiến trình, dòng lệnh) của chương trình đang nghe cổng PORT; máy khác / không tìm được → None."""
    if os.name != "nt":
        return None
    import subprocess
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=15,
                             errors="replace").stdout
        pid = next((int(c[-1]) for c in (dong.split() for dong in out.splitlines())
                    if len(c) >= 5 and c[1].endswith(f":{PORT}") and c[3].upper() in ("LISTENING", "ABHÖREN", "ĐANG NGHE")
                    and c[-1].isdigit()), None)
        if not pid:
            pid = next((int(c[-1]) for c in (dong.split() for dong in out.splitlines())
                        if len(c) >= 5 and c[1].endswith(f":{PORT}") and c[2].endswith(":0") and c[-1].isdigit()), None)
        if not pid:
            return None
        ten = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             timeout=15, errors="replace").stdout.strip().split(",")[0].strip('"')
        lenh = subprocess.run(["powershell", "-NoProfile", "-Command",
                               f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                              capture_output=True, text=True, timeout=20, errors="replace").stdout.strip()
        return pid, ten, lenh
    except Exception:  # noqa: BLE001
        return None


def _cho_cong_trong(lan=20):
    for _ in range(lan):
        time.sleep(0.5)
        try:
            return tao_may_chu()
        except OSError:
            continue
    return None


def _thay_ban_cu(url):
    """Cổng 8600 đang bận: bản này đang mở → mở trình duyệt; bản cũ của phần mềm → xin tắt / tắt hẳn rồi chạy bản mới;
    chương trình khác → chạy bản mới ở cổng trống kế tiếp (8601…). Trả máy chủ đã mở, hoặc None."""
    ma, sv, d = _hoi_cong("/api/phien_ban")
    cua_minh = sv.startswith("ReviewXayDung")
    if d and d.get("phien_ban") == PHIEN_BAN:
        print(f"Phần mềm (phiên bản {PHIEN_BAN}) đã mở sẵn → mở trình duyệt: {url}")
        webbrowser.open(url)
        return None
    ten_cu = f"bản {d['phien_ban']}" if d and d.get("phien_ban") else ("bản cũ của phần mềm" if cua_minh else
                                                                        "một chương trình khác (hoặc bản cũ bị treo)")
    print(f"Cổng {PORT} đang được {ten_cu} dùng → tắt để chạy bản {PHIEN_BAN}…")
    if cua_minh or ma is not None:
        ma_tat, _, d_tat = _hoi_cong("/api/tat", "POST")
        if ma_tat == 409:
            print("  Bản cũ đang chạy dở một việc (trích hợp đồng / kiểm tra đợt). Chờ việc xong, đóng cửa sổ đen cũ rồi mở lại.")
            return None
        srv = _cho_cong_trong(10)
        if srv:
            print("  Đã tắt bản cũ.")
            return srv
    tt = _pid_giu_cong()
    if tt:
        pid, ten, lenh = tt
        la_phan_mem = ten.lower().startswith("python") and any(k in lenh.lower() for k in ("chay.py", "may_chu", "trich_xuat"))
        if la_phan_mem:
            import subprocess
            print(f"  Tắt hẳn bản cũ (tiến trình {ten}, PID {pid})…")
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=15)
            srv = _cho_cong_trong(20)
            if srv:
                print("  Đã tắt bản cũ.")
                return srv
        else:
            print(f"  Cổng {PORT} thuộc chương trình khác: {ten} (PID {pid}) — không tắt chương trình này.")
    goc = PORT
    for p in range(goc + 1, goc + 20):
        try:
            srv = tao_may_chu(p)
            print(f"  → Chạy bản mới ở cổng {p}. Muốn dùng lại cổng {goc}: đóng chương trình đang giữ cổng rồi mở lại.")
            return srv
        except OSError:
            continue
    print(f"KHÔNG MỞ ĐƯỢC cổng nào từ {goc} đến {goc + 19}. Đóng các cửa sổ đen cũ (hoặc Task Manager → python.exe) rồi mở lại.")
    return None


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            if (s.encoding or "").lower().replace("-", "") != "utf8":
                s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(mo_trinh_duyet=True):
    _utf8()
    url = f"http://localhost:{PORT}"
    try:
        srv = tao_may_chu()
    except OSError:
        srv = _thay_ban_cu(url)
        if srv is None:
            return
    url = f"http://localhost:{PORT}"
    ai = dv.trang_thai_ai(lam_moi=True)
    print(f"PHẦN MỀM REVIEW HỒ SƠ THANH TOÁN — phiên bản {PHIEN_BAN}")
    print(f"  Giao diện: {url}" + ("   (đã tự mở trình duyệt)" if mo_trinh_duyet else ""))
    print(f"  Máy AI {ai['ip']}:{ai['cong']} · {ai['model']}: "
          + ("KẾT NỐI ĐƯỢC" if ai["ket_noi"] and ai["co_model"] else f"CHƯA SẴN SÀNG — {ai['loi']} (sửa trong Cài đặt)"))
    print("  GIỮ CỬA SỔ NÀY MỞ khi dùng. Đóng cửa sổ = tắt phần mềm.")
    if mo_trinh_duyet:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
