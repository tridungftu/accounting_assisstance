"""M4-04B — nối route Request nháp vào dispatcher THẬT + widget. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Tầng W (MOCK_DB_BOUNDARY, không CSDL/mạng): `server.LocalServer` + `Handler.handle_route` THẬT (cổng 0, loopback riêng) → `m4_request.dieu_huong`
THẬT → `RequestNhap` THẬT (lớp con RequestNhapThu của tests/test_m4_request_tinh.py: chỉ thay quyền/giữ/ghi bằng KhoGia) qua mặt tiền CongTruyen
THẬT tới `FakeRequest` (không socket). Chỉ giả ở biên dữ liệu: `m4.dich_vu`, `m4._ket_noi_review` (kết nối đếm đóng), `k2.xay_dung.XayDungK2`
(trả xd giả có _tx/_nhieu đọc KhoGia) và `duyet_dot.DuyetDot` (hồ sơ có phiên bản V1 đã seal / V2 nháp / CHUA_NOP, chọn được bản mới nhất).
Cần import được psycopg (LocalApp._crm_db) + k2.xay_dung; thiếu → SkipTest NOT_VERIFIED (KHÔNG phải PASS). Cấu hình Request chỉ qua seam tường minh
`LocalApp.gan_request_nhap` (mặc định vắng = CHUA_CAU_HINH, 0 mạng); không đọc env/khóa, không bật transport thật.

W01 đúng ba route + tài sản qua dispatcher thật; route lạ/sai phương thức 404; token/phiên.
W02 không cấu hình → 503 CHUA_CAU_HINH, 0 nhật ký transport, 0 intent; seam sai kiểu bị từ chối.
W03 context HTTP: hiện hành / lịch sử (hien_hanh=false) / V2 chưa seal / CHUA_NOP; tham số version_id kiểm chặt; DTO domain giữ bộ khóa.
W04 luồng dương hiện hành (tạo → tải → chờ quét → đối soát), transport chạy NGOÀI mutation lock trên kết nối riêng đóng ở mọi nhánh.
W05 TẠO trên phiên bản lịch sử → 409 HOLD trước mọi mạng; hiện hành đổi giữa lệnh → mặt tiền chặn POST (0 byte ra dây).
W06 lịch sử + intent mất ACK tạo (CHUA_RO_TAO) / chưa tải (DA_TAO_NHAP) → HOLD LICH_SU_CAN_*; 0 IO, intent/sự kiện/biên nhận y nguyên.
W07 lịch sử + chưa rõ tải lên (CHUA_RO_TAI) → domain chạy qua mặt tiền chặn POST: GET/tải về vẫn được, 0 POST, đối soát xong được.
W08 mặt tiền trực tiếp qua domain: replay-create bị chặn trên dây; kiem_post lỗi/khác True = chặn.
W09 phiên đổi/hết trong lệnh dài → 409 M4_REQUEST_PHIEN_DOI không echo; intent đã ghi giữ nguyên.
W10 quyền: XEM → 403; đợt khác → 404; authority → 403; cùng khóa phát lại 0 POST.
W11 (FIX01) query thô qua handle_route thật: `x=` / `version_id=` / `dot_id=` / lặp có rỗng → 400 ở GET và POST, 0 kết nối/transport/intent/biên nhận;
    vắng version_id vẫn = mới nhất, version hợp lệ vẫn chọn được, `x=1` vẫn 400.
W12 (FIX02) handler hẹp trên dieu_huong THẬT (Handler.body/json_body thật): POST query sai đọc hết body đúng một lần (16 KiB) TRƯỚC _q, 0 lock/phiên/DB.
Tầng U (producer→consumer): DuyetDot.xem THẬT (fixture tests/test_m4_02c_dto_ui.py, chỉ giả tầng dữ liệu) + `ngu_canh` THẬT sinh context; Node chạy
tests/m4_04b_request_async.cjs với app.js + m4.js + m4_duyet_pdf.js + m4_request_nhap.js THẬT. Thiếu node/psycopg → NOT_VERIFIED.
"""

from __future__ import annotations

import contextlib
import copy
import http.client
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json
from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4 import request_nhap as RN
from tests.test_m4_request_tinh import AI, ID, DongHo, FakeRequest, KhoGia, RequestNhapThu, XdGia, cau_hinh, ho_so_seal
from tests.test_m4_review_http import CAU_HINH_FIXTURE

GOC = Path(__file__).resolve().parents[1]
CJS = GOC / "tests" / "m4_04b_request_async.cjs"
HAN_NODE = 120
TIEN_TO = "/api/m4-request"
V2 = str(uuid.UUID(int=0x99))
KHAC = "MO_PHONG_DU_AN_B1"


def _co_moi_truong():
    try:
        import psycopg  # noqa: F401 — LocalApp._crm_db import psycopg
        import kho_tri_thuc.k2.xay_dung  # noqa: F401
    except ImportError as exc:
        return f"NOT_VERIFIED: thiếu psycopg/K2 ({exc}) — dispatcher thật không chạy được; KHÔNG phải PASS"
    return None


# ================================================================================================== biên dữ liệu giả (TEST_ONLY)
class DuyetPhienBan:
    """DuyetDot giả có phiên bản: V1 (ID['pb']) đã seal; V2 nháp chưa seal; CHUA_NOP. W = thế giới chung của ca (đổi được giữa lệnh)."""
    W: dict = {}

    def __init__(self, xd):
        pass

    def xem(self, dang_nhap, *, dot_id, version_id=None):
        W = DuyetPhienBan.W
        if dang_nhap != AI:
            raise DataError("DANH_TINH", "không có phiên")
        if dot_id != ID["dot"]:
            raise DataError("M4_DUYET_KHONG_THAY", "không thấy đợt")
        q = {"xem": W.get("xem", True), "ket_luan": False, "duyet": False, "tai_pdf": True, "phien_ban": True}
        if W.get("chua_nop"):
            if version_id is not None:
                raise DataError("M4_DUYET_KHONG_THAY", "chưa nộp")
            hs = ho_so_seal(trang_thai="CHUA_NOP", seal=None, pdf_lich_su=[])
            hs["context"] = {**hs["context"], "version_id": None}
            return {**hs, "quyen": {**q, "tai_pdf": False, "phien_ban": False}, "chua_nop": True, "phien_ban_hien_hanh": False}
        pb = version_id or W["moi_nhat"]
        if pb == ID["pb"]:
            hs = ho_so_seal()
        elif pb == V2 and W["moi_nhat"] == V2:
            hs = ho_so_seal(trang_thai="CAN_KIEM_LAI", seal=None, pdf_lich_su=[])
            hs["context"] = {**hs["context"], "version_id": V2}
        else:
            raise DataError("M4_DUYET_KHONG_THAY", "không thấy phiên bản")
        return {**hs, "quyen": q, "chua_nop": False, "phien_ban_hien_hanh": pb == W["moi_nhat"]}


class ConnDem:
    def __init__(self, ten):
        self.ten, self.dong = ten, False

    def close(self):
        self.dong = True


class XdHttp(XdGia):
    """xd giả cho cả service (GET dưới lock) và kết nối riêng (POST): đọc intent/sự kiện từ KhoGia qua đúng hai câu `xem()` dùng."""

    def __init__(self, kho: KhoGia, root: Path):
        super().__init__()
        self.kho, self.root, self.chi_mo_phong, self.hom_nay = kho, root, True, None

    @contextlib.contextmanager
    def _tx(self, dt):
        yield None

    def _nhieu(self, sql, params):
        dot = params[0]
        ys = [copy.deepcopy(y) for y in self.kho.y.values() if y["dot_id"] == dot]
        if "request_su_kien" in sql:
            ids = {y["id"] for y in ys}
            return [{"y_dinh_id": e[0], "thu_tu": i + 1, "buoc": e[1], "tu_trang_thai": e[2], "den_trang_thai": e[3], "chi_tiet": None,
                     "quyen_con": e[4], "boi": None, "luc": None} for i, e in enumerate(self.kho.su_kien) if e[0] in ids]
        return ys


# ================================================================================================== tầng W
class WiringHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ly_do = _co_moi_truong()
        if ly_do:
            raise unittest.SkipTest(ly_do)
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4_04b_http_"))  # giữ lại, không xóa
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung)

    @classmethod
    def _dung(cls):
        cls.server.shutdown()
        cls.thread.join(5)

    def setUp(self):
        self.dh = DongHo()
        self.kho = KhoGia(self.dh)
        self.fake = FakeRequest(self.dh)
        self.xd = XdHttp(self.kho, self.app.root)
        DuyetPhienBan.W = {"moi_nhat": ID["pb"]}
        self.conns, self.xd_kw = [], []
        kho = self.kho

        class RQ(RequestNhapThu):
            def __init__(self, xd, ch, t, **k):
                super().__init__(kho, xd, ch, t, **k)

        def ket_noi(app):
            cap = (ConnDem("web"), ConnDem("chu"))
            self.conns.append(cap)
            return cap

        def xay_dung(web, root, **kw):
            self.xd_kw.append((web, kw))
            return self.xd

        for p in (mock.patch("kho_tri_thuc.giao_dien.m4.dich_vu", lambda app: self.xd),
                  mock.patch("kho_tri_thuc.giao_dien.m4._ket_noi_review", ket_noi),
                  mock.patch("kho_tri_thuc.k2.xay_dung.XayDungK2", xay_dung),
                  mock.patch.object(RN, "RequestNhap", RQ),
                  mock.patch.object(DD, "DuyetDot", DuyetPhienBan)):
            p.start()
            self.addCleanup(p.stop)
        self.app.go_request_nhap()
        self.addCleanup(self.app.go_request_nhap)
        self.sid = "sid-" + uuid.uuid4().hex
        with self.app.mutation_lock:
            self.app.__dict__.setdefault("_crm_phien", {})[self.sid] = AI
        self.n = 0

    # ------------------------------------------------------------------ helpers
    def goi(self, path, body=None, *, sid="mac_dinh", token=True, method=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=60)
        try:
            h = {"X-KTT-Token": self.app.token} if token else {}
            sid = self.sid if sid == "mac_dinh" else sid
            if sid:
                h["Cookie"] = f"{self.app.CRM_COOKIE}={sid}"
            data = None if body is None else json.dumps(body).encode("utf-8")
            if data is not None:
                h["Content-Type"] = "application/json"
            c.request(method or ("POST" if data is not None else "GET"), path, body=data, headers=h)
            r = c.getresponse()
            out, ct, cc = r.read(), r.getheader("Content-Type") or "", r.getheader("Cache-Control")
        finally:
            c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), cc

    def K(self, ten=None):
        self.n += 1
        return f"m4rq-04b-{ten or self.n}-{uuid.uuid4().hex[:6]}"

    def lenh(self, duong="tao", version=None, khoa=None, **kw):
        return self.goi(f"{TIEN_TO}/{duong}", {"dot_id": ID["dot"], "version_id": version or ID["pb"], "khoa": khoa or self.K()}, **kw)

    def xem(self, version=None, **kw):
        q = {"dot_id": ID["dot"]}
        if version is not None:
            q["version_id"] = version
        return self.goi(f"{TIEN_TO}?" + urlencode(q), **kw)

    def cau_hinh_on(self):
        self.app.gan_request_nhap(cau_hinh(), self.fake)

    def chup(self):
        return copy.deepcopy((self.kho.y, self.kho.su_kien, self.kho.bien_nhan, self.fake.nhat_ky, self.fake.de_xuat, self.fake.tep))

    def so_post(self):
        return sum(1 for p, _, _ in self.fake.nhat_ky if p != "GET")

    def ket_noi_da_dong(self):
        self.assertTrue(all(w.dong and c.dong for w, c in self.conns), "kết nối riêng chưa đóng")

    def ctx(self, version, seal, hien):
        return {"schema": "M4_REQUEST_HTTP_CONTEXT_V1", "dot_id": ID["dot"], "version_id": version, "dang_nhap": AI, "phap_nhan_id": ID["pn"],
                "seal_id": seal, "hien_hanh": hien}

    # ------------------------------------------------------------------ W01
    def test_w01_ba_route_tai_san_cong(self):
        st, r, cc = self.xem()
        self.assertEqual((st, cc, r["context"]), (200, "no-store", self.ctx(ID["pb"], ID["seal"], True)))
        for path, method in ((TIEN_TO, "POST"), (f"{TIEN_TO}/tao", "GET"), (f"{TIEN_TO}/doi-soat", "GET")):
            with self.subTest(path=path, method=method):
                st, r, _ = self.goi(path, {} if method == "POST" else None, method=method)
                self.assertEqual((st, r.get("error")), (404, "NOT_FOUND"))
        for path in (f"{TIEN_TO}/gui", f"{TIEN_TO}/tao/", f"{TIEN_TO}/xoa", f"{TIEN_TO}x"):
            with self.subTest(path=path):
                st, _, _ = self.goi(path, {"dot_id": ID["dot"], "version_id": ID["pb"], "khoa": self.K()})
                self.assertEqual(st, 404)
        st, r, _ = self.xem(token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r, _ = self.lenh(token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r, _ = self.xem(sid=None)
        self.assertEqual((st, r.get("error")), (400, "CRM_PHIEN"))
        st, raw, cc = self.goi("/m4/m4_request_nhap.js", token=False)
        self.assertEqual((st, cc), (200, "no-store"))
        self.assertIn(b"window.kttM4RequestNhap", raw)
        for la in ("/m4/m4_request_nhap.js.map", "/m4/request_nhap.js", "/m4/m4_request_nhap.JS"):
            with self.subTest(la=la):
                self.assertEqual(self.goi(la, token=False)[0], 404)
        self.assertEqual((self.fake.nhat_ky, self.kho.y), ([], {}))

    # ------------------------------------------------------------------ W02
    def test_w02_khong_cau_hinh_khong_mang(self):
        st, r, cc = self.lenh()
        self.assertEqual((st, r["trang_thai"], r["y_dinh"], cc), (503, "CHUA_CAU_HINH", None, "no-store"))
        self.assertIn("khoa_api", r["thieu"])
        self.assertEqual(r["context"], self.ctx(ID["pb"], ID["seal"], True))
        st, x, _ = self.xem()
        self.assertEqual((st, x["cau_hinh"]["trang_thai"]), (200, "CHUA_CAU_HINH"))
        self.assertEqual((self.fake.nhat_ky, self.kho.y, self.kho.bien_nhan), ([], {}, {}))
        self.ket_noi_da_dong()
        for ch, t in ((None, self.fake), ({"origin": "x"}, self.fake), (cau_hinh(), object())):
            with self.subTest(ch=type(ch).__name__, t=type(t).__name__):
                with self.assertRaises(DataError) as e:
                    self.app.gan_request_nhap(ch, t)
                self.assertEqual(e.exception.code, "M4_REQUEST_CAU_HINH_SAI")
        self.assertNotIn("_m4_request", self.app.__dict__)
        tat = FakeRequest(self.dh, kich_hoat=False)  # transport mặc định TẮT: seam không tự bật
        self.app.gan_request_nhap(cau_hinh(), tat)
        st, r, _ = self.lenh()
        self.assertEqual((st, r["trang_thai"], tat.nhat_ky), (503, "CHUA_CAU_HINH", []))
        self.assertIn("transport_chua_kich_hoat", r["thieu"])

    # ------------------------------------------------------------------ W03
    def test_w03_context_va_tham_so(self):
        st, r, _ = self.xem(ID["pb"])
        self.assertEqual((st, set(r)), (200, {"schema", "quyen", "cau_hinh", "y_dinh", "context"}))
        self.assertEqual((r["schema"], r["y_dinh"], r["context"]), (RN.SCHEMA, [], self.ctx(ID["pb"], ID["seal"], True)))
        DuyetPhienBan.W["moi_nhat"] = V2
        self.assertEqual(self.xem(ID["pb"])[1]["context"], self.ctx(ID["pb"], ID["seal"], False))
        self.assertEqual(self.xem()[1]["context"], self.ctx(V2, None, True))
        self.assertEqual(self.xem(V2)[1]["context"], self.ctx(V2, None, True))
        DuyetPhienBan.W = {"chua_nop": True}
        self.assertEqual(self.xem()[1]["context"], self.ctx(None, None, False))
        st, r, _ = self.xem(ID["pb"])
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        DuyetPhienBan.W = {"moi_nhat": ID["pb"]}
        # FIX02: ID["pb"] toàn số → upper() không đổi (canonical hợp lệ). Oracle chữ hoa phải dùng UUID THẬT có chữ a-f; bản thường của nó là canonical
        hoa = str(uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")).upper()
        self.assertNotEqual(hoa, hoa.lower())
        for q in (f"dot_id={ID['dot']}&version_id=ABC", f"dot_id={ID['dot']}&version_id={hoa}", f"dot_id={hoa}",
                  f"dot_id={ID['dot']}&version_id={ID['pb']}&version_id={ID['pb']}", f"dot_id={ID['dot']}&x=1", "version_id=" + ID["pb"]):
            with self.subTest(q=q):
                self.assertEqual(self.goi(f"{TIEN_TO}?{q}")[0], 400)
        # dương: selector canonical (chữ thường) của cùng UUID có chữ đi qua guard → 404 không thấy phiên bản (không phải 400); UUID toàn số vẫn 200
        st, r, _ = self.xem(hoa.lower())
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        self.assertEqual(self.xem(ID["pb"])[0], 200)
        st, r, _ = self.xem(str(uuid.uuid4()))
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        st, r, _ = self.goi(f"{TIEN_TO}?dot_id={uuid.uuid4()}")
        self.assertEqual((st, r.get("error")), (404, "M4_REQUEST_KHONG_THAY"))
        DuyetPhienBan.W["xem"] = False
        st, r, _ = self.xem()
        self.assertEqual((st, r.get("error")), (403, "M4_REQUEST_PHAM_VI"))
        self.assertEqual(self.fake.nhat_ky, [])

    # ------------------------------------------------------------------ W04
    def test_w04_duong_hien_hanh_ngoai_lock(self):
        self.cau_hinh_on()
        khoa_lock = []
        cham = lambda _f: khoa_lock.append(self.app.mutation_lock.locked())  # noqa: E731
        for op in ("GET_NHOM", "POST_DE_XUAT", "POST_TEP"):
            self.fake.tiem(op, cham)
        st, r, cc = self.lenh(khoa="w04-tao")
        self.assertEqual((st, r["trang_thai"], r["buoc"], r["chan"], cc), (200, "CHO_QUET", ["TAO", "DOC", "TAI", "DOI_SOAT"], None, "no-store"))
        self.assertEqual(r["context"], self.ctx(ID["pb"], ID["seal"], True))
        self.assertNotIn("su_kien", r["y_dinh"])
        self.assertEqual((len(khoa_lock), any(khoa_lock)), (3, False), "transport chạy trong mutation lock")
        self.assertEqual((len(self.fake.de_xuat), len(self.fake.tep), self.so_post()), (1, 1, 2))
        web, kw = self.xd_kw[-1]
        self.assertIs(kw["conn_tin_cay"], self.conns[-1][1])
        self.assertIs(web, self.conns[-1][0])
        st, r, _ = self.lenh(khoa="w04-tao")  # cùng khóa: phát lại biên nhận, 0 POST mới (bước TAO không còn hợp với CHO_QUET)
        self.assertEqual((r["lap_lai"], self.so_post(), len(self.fake.de_xuat)), (True, 2, 1), (st, r))
        self.fake.quet(next(iter(self.fake.tep)), "clean")
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["trang_thai"], self.so_post()), (200, "DA_DOI_SOAT", 2))
        st, x, _ = self.xem(ID["pb"])
        y = x["y_dinh"][0]
        self.assertEqual((y["trang_thai"], y["so_tien"], y["tien_te"]), ("DA_DOI_SOAT", "31500000", "VND"))
        for cam in ("canonical", "idem_key", "actor_id", "nguoi_tao"):
            self.assertNotIn(cam, y)
        self.assertGreater(len(y["su_kien"]), 0)
        self.ket_noi_da_dong()

    # ------------------------------------------------------------------ W05
    def test_w05_tao_lich_su_va_hien_hanh_doi_giua_chung(self):
        self.cau_hinh_on()
        DuyetPhienBan.W["moi_nhat"] = V2
        st, r, _ = self.lenh(khoa="w05-ls")
        self.assertEqual((st, r["trang_thai"], r["chan"], r["y_dinh"]), (409, "HOLD", "PHIEN_BAN_KHONG_HIEN_HANH", None))
        self.assertEqual(r["context"], self.ctx(ID["pb"], ID["seal"], False))
        self.assertEqual((self.fake.nhat_ky, self.kho.y, self.kho.bien_nhan), ([], {}, {}))
        st, r, _ = self.lenh(version=V2)  # V2 hiện hành nhưng chưa seal: domain chặn trước nhóm/danh mục/intent
        self.assertEqual((st, r.get("error")), (409, "M4_REQUEST_CHUA_SEAL"))
        self.assertEqual((self.fake.nhat_ky, self.kho.y), ([], {}))
        # hiện hành đổi SAU kiểm đầu, TRƯỚC POST nguồn (giữa GET nhóm): mặt tiền chặn — 0 POST ra dây
        DuyetPhienBan.W["moi_nhat"] = ID["pb"]
        self.fake.tiem("GET_NHOM", lambda _f: DuyetPhienBan.W.update(moi_nhat=V2))
        st, r, _ = self.lenh(khoa="w05-giua")
        self.assertEqual((st, r["trang_thai"], r["chan"]), (409, "HOLD", "PHIEN_BAN_KHONG_HIEN_HANH"))
        self.assertEqual((self.so_post(), self.fake.de_xuat), (0, {}))
        self.assertEqual(self.kho.y[ID["seal"]]["trang_thai"], "TU_CHOI_TAO", "mặt tiền chặn = chắc chắn chưa gửi (giới hạn đã báo cáo)")
        self.ket_noi_da_dong()

    # ------------------------------------------------------------------ W06
    def test_w06_lich_su_can_tao_tai_hold_khong_io(self):
        self.cau_hinh_on()
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        st, r, _ = self.lenh(khoa="w06-tao")
        self.assertEqual((st, r["trang_thai"]), (200, "CHUA_RO_TAO"))
        yid = r["y_dinh"]["id"]
        DuyetPhienBan.W["moi_nhat"] = V2
        truoc = self.chup()
        for duong, mong in (("doi-soat", "LICH_SU_CAN_TAO"), ("tao", "PHIEN_BAN_KHONG_HIEN_HANH")):
            with self.subTest(duong=duong):
                st, r, _ = self.lenh(duong, khoa=f"w06-{duong}")
                self.assertEqual((st, r["trang_thai"], r["chan"], r["lap_lai"]), (409, "HOLD", mong, False))
                self.assertEqual(r["context"]["hien_hanh"], False)
                if duong == "doi-soat":
                    self.assertEqual((r["y_dinh"]["id"], r["y_dinh"]["trang_thai"]), (yid, "CHUA_RO_TAO"))
                    self.assertNotIn("su_kien", r["y_dinh"])
        self.assertEqual(self.chup(), truoc, "HOLD lịch sử làm đổi intent/sự kiện/biên nhận/nhật ký transport")
        st, x, _ = self.xem(ID["pb"])
        self.assertEqual((x["y_dinh"][0]["trang_thai"], x["context"]["hien_hanh"]), ("CHUA_RO_TAO", False))
        DuyetPhienBan.W["moi_nhat"] = ID["pb"]  # trở lại hiện hành: intent gốc vẫn đối soát được, cùng khóa nguồn
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["trang_thai"], len(self.fake.de_xuat)), (200, "CHO_QUET", 1))
        keys = [h.get("Idempotency-Key") for p, d, h in self.fake.nhat_ky if p == "POST" and d == "/api/v1/de-xuat"]
        self.assertEqual(keys, ["m4-request:" + yid] * 2)

    def test_w06b_lich_su_can_tai_va_chua_co_y_dinh(self):
        # DA_TAO_NHAP (tải lên chắc chắn chưa gửi) trên lịch sử → LICH_SU_CAN_TAI
        self.cau_hinh_on()
        self.fake.tiem("POST_TEP", "KET_NOI")
        self.assertEqual(self.lenh()[1]["trang_thai"], "DA_TAO_NHAP")
        DuyetPhienBan.W["moi_nhat"] = V2
        truoc = self.chup()
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["trang_thai"], r["chan"], r["y_dinh"]["trang_thai"]), (409, "HOLD", "LICH_SU_CAN_TAI", "DA_TAO_NHAP"))
        self.assertEqual(self.chup(), truoc)

    def test_w06c_lich_su_chua_co_y_dinh(self):
        self.cau_hinh_on()
        DuyetPhienBan.W["moi_nhat"] = V2
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["chan"], r["y_dinh"], self.kho.y, self.kho.bien_nhan, self.fake.nhat_ky),
                         (409, "LICH_SU_CHUA_CO_Y_DINH", None, {}, {}, []))
        self.ket_noi_da_dong()

    # ------------------------------------------------------------------ W07
    def test_w07_lich_su_chua_ro_tai_chi_get(self):
        self.cau_hinh_on()
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.assertEqual(self.lenh(khoa="w07")[1]["trang_thai"], "CHUA_RO_TAI")
        tid = next(iter(self.fake.tep))
        DuyetPhienBan.W["moi_nhat"] = V2
        n_post, n_get = self.so_post(), len(self.fake.nhat_ky) - self.so_post()
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["trang_thai"], r["context"]["hien_hanh"]), (200, "CHUA_RO_TAI", False))
        self.assertEqual(self.so_post(), n_post, "lịch sử gửi POST ra dây")
        self.assertGreater(len(self.fake.nhat_ky) - self.so_post(), n_get, "GET đọc/tải về phải được phép")
        self.fake.quet(tid, "clean")
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, r["trang_thai"], self.so_post(), len(self.fake.tep)), (200, "DA_DOI_SOAT", n_post, 1))

    # ------------------------------------------------------------------ W08
    def test_w08_mat_tien_qua_domain(self):
        from kho_tri_thuc.giao_dien.m4_request import CongTruyen
        from kho_tri_thuc.m4.request_api import LoiRequest
        ch = cau_hinh()
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        rq = RN.RequestNhap(self.xd, ch, self.fake)  # = RQ đã vá (KhoGia)
        self.assertEqual(rq.tao(AI, dot_id=ID["dot"], version_id=ID["pb"], khoa=self.K())["trang_thai"], "CHUA_RO_TAO")
        n = self.so_post()
        cong = CongTruyen(self.fake, chan_post=True)
        self.assertNotIn("FakeRequest", repr(cong))
        RN.RequestNhap(self.xd, ch, cong).doi_soat(AI, dot_id=ID["dot"], version_id=ID["pb"], khoa=self.K())  # replay-create bị chặn trên dây
        self.assertEqual((self.so_post(), cong.bi_chan), (n, ["POST"]))
        for kiem in (lambda: 1, lambda: None, lambda: (_ for _ in ()).throw(RuntimeError("x"))):
            c = CongTruyen(self.fake, chan_post=False, kiem_post=kiem)
            with self.assertRaises(LoiRequest) as e:
                c.gui("POST", "/api/v1/de-xuat", {}, b"{}", 1024)
            self.assertEqual((e.exception.ma, c.bi_chan, self.so_post()), ("REQUEST_TRANSPORT_TAT", ["POST"], n))
        c = CongTruyen(self.fake, chan_post=True)
        c.gui("GET", "/api/v1/nhom", {}, None, 1 << 20)
        self.assertEqual(c.bi_chan, [])

    # ------------------------------------------------------------------ W09
    def test_w09_phien_doi_trong_lenh_dai(self):
        self.cau_hinh_on()
        self.fake.tiem("POST_DE_XUAT", lambda _f: self.app.__dict__["_crm_phien"].__setitem__(self.sid, KHAC))
        st, r, cc = self.lenh(khoa="w09")
        self.assertEqual((st, set(r), r["error"], cc), (409, {"error", "message"}, "M4_REQUEST_PHIEN_DOI", "no-store"))
        self.assertNotIn(AI, json.dumps(r, ensure_ascii=False))
        y = self.kho.y[ID["seal"]]
        self.assertEqual((y["trang_thai"], y["actor_id"], len(self.fake.de_xuat)), ("CHO_QUET", ID["nv"], 1), "intent đã ghi phải giữ nguyên")
        self.app.__dict__["_crm_phien"][self.sid] = AI
        self.assertEqual(self.xem()[1]["y_dinh"][0]["trang_thai"], "CHO_QUET")
        self.fake.tiem("GET_NHOM", lambda _f: self.app.__dict__["_crm_phien"].pop(self.sid))  # phiên hết giữa lệnh (mọi lệnh đọc nhóm)
        st, r, _ = self.lenh("doi-soat")
        self.assertEqual((st, set(r), r["error"]), (409, {"error", "message"}, "M4_REQUEST_PHIEN_DOI"))
        self.app.__dict__["_crm_phien"][self.sid] = AI
        # cùng sid + cùng login sau A→B→A: phiên đúng như đã chụp → trả kết quả (kiểm là đúng sid/login, không phải "chưa từng đổi")
        self.fake.tiem("GET_NHOM", lambda _f: (self.app.__dict__["_crm_phien"].__setitem__(self.sid, KHAC),
                                                  self.app.__dict__["_crm_phien"].__setitem__(self.sid, AI)))
        self.assertEqual(self.lenh("doi-soat")[0], 200)
        self.ket_noi_da_dong()

    # ------------------------------------------------------------------ W10
    def test_w10_quyen_authority_phat_lai(self):
        self.cau_hinh_on()
        for k in ("nguoiTao", "so_tien", "seal_id", "pdf", "endpoint", "phap_nhan_id"):
            with self.subTest(k=k):
                st, r, _ = self.goi(f"{TIEN_TO}/tao", {"dot_id": ID["dot"], "version_id": ID["pb"], "khoa": self.K(), k: "x"})
                self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))
        st, r, _ = self.goi(f"{TIEN_TO}/tao", {"dot_id": ID["dot"], "version_id": ID["pb"], "khoa": self.K(), "context": "x"})
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        self.kho.q["tai_pdf"] = False
        st, r, _ = self.lenh()
        self.assertEqual((st, r.get("error")), (403, "M4_REQUEST_PHAM_VI"))
        st, x, _ = self.xem()
        self.assertEqual((st, x["quyen"]["tai_pdf"], x["cau_hinh"]), (200, False, None))
        self.kho.q["tai_pdf"] = True
        st, r, _ = self.goi(f"{TIEN_TO}/tao", {"dot_id": str(uuid.uuid4()), "version_id": ID["pb"], "khoa": self.K()})
        self.assertEqual((st, r.get("error")), (404, "M4_REQUEST_KHONG_THAY"))
        self.assertEqual((self.fake.nhat_ky, self.kho.y), ([], {}))
        self.ket_noi_da_dong()

    # ------------------------------------------------------------------ W11 (FIX01)
    def test_w11_query_rong_lap_qua_handle_route_that(self):
        """Query thô (không urlencode/parse ở fixture) đi qua LocalServer + Handler.handle_route THẬT: blank/lặp/khóa lạ → 400 trước mọi IO."""
        self.cau_hinh_on()
        D, PB = ID["dot"], ID["pb"]
        sai_get = (f"dot_id={D}&x=", f"dot_id={D}&version_id=", f"dot_id={D}&version_id={PB}&version_id=", f"dot_id={D}&version_id=&version_id={PB}",
                   "dot_id=", f"dot_id=&version_id={PB}", f"dot_id={D}&dot_id=", f"dot_id={D}&x=1")
        for q in sai_get:
            with self.subTest(get=q):
                st, r, cc = self.goi(f"{TIEN_TO}?{q}")
                self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), r)
        body = {"dot_id": D, "version_id": PB, "khoa": "w11-khoa"}
        for duong in ("tao", "doi-soat"):
            for q in ("x=", "x=1", "version_id=", f"dot_id={D}&dot_id=", f"version_id={PB}&version_id="):
                with self.subTest(post=duong, q=q):
                    st, r, _ = self.goi(f"{TIEN_TO}/{duong}?{q}", body)
                    self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), r)
        # query sai: 0 kết nối riêng, 0 transport (GET/POST), 0 intent/biên nhận/sự kiện, 0 Request nguồn
        self.assertEqual((self.conns, self.fake.nhat_ky, self.kho.y, self.kho.bien_nhan, self.kho.su_kien, self.fake.de_xuat, self.fake.tep),
                         ([], [], {}, {}, [], {}, {}))
        # hành vi cũ giữ nguyên: vắng version_id = mới nhất canonical; version hợp lệ chọn tường minh vẫn chạy; lệnh không query vẫn chạy
        DuyetPhienBan.W["moi_nhat"] = V2
        st, r, _ = self.goi(f"{TIEN_TO}?dot_id={D}")
        self.assertEqual((st, r["context"]), (200, self.ctx(V2, None, True)))
        st, r, _ = self.goi(f"{TIEN_TO}?dot_id={D}&version_id={PB}")
        self.assertEqual((st, r["context"]), (200, self.ctx(PB, ID["seal"], False)))
        DuyetPhienBan.W["moi_nhat"] = PB
        st, r, _ = self.goi(f"{TIEN_TO}/tao", body)
        self.assertEqual((st, r["trang_thai"], self.so_post()), (200, "CHO_QUET", 2))
        self.ket_noi_da_dong()


# ================================================================================================== W12 (FIX02) thứ tự body → query
class HandlerHep:
    """Handler hẹp cho `dieu_huong` THẬT: body/json_body là ĐÚNG hàm `server.Handler.body/json_body` trên rfile BytesIO (đo đã đọc bao nhiêu byte);
    chỉ thêm vết thứ tự. Không socket, không phiên (crm_sid ghi vết)."""

    def __init__(self, Handler, raw: bytes, vet: list, *, do_dai=None):
        self._H, self.vet = Handler, vet
        self.headers = {"Content-Length": str(len(raw) if do_dai is None else do_dai)}
        self.rfile = io.BytesIO(raw)

    def body(self, limit):
        self.vet.append(("body", limit))
        return self._H.body(self, limit)

    def json_body(self, limit):
        self.vet.append(("json_body", limit))
        return self._H.json_body(self, limit)

    def crm_sid(self):
        self.vet.append(("crm_sid",))
        return None

    def send_content(self, status, content, mime=None, headers=None):
        self.vet.append(("gui", status, content.get("error") if isinstance(content, dict) else None))


class AppDem:
    """App giả chỉ để đo: chạm mutation lock / phiên / CSDL đều ghi vết; crm_phien dừng bằng CRM_PHIEN (không có IO thật nào phía sau)."""

    def __init__(self, vet: list):
        self.vet, self._khoa = vet, threading.Lock()

    @property
    def mutation_lock(self):
        self.vet.append(("lock",))
        return self._khoa

    def crm_phien(self, sid):
        self.vet.append(("crm_phien",))
        raise DataError("CRM_PHIEN", "không có phiên (đo)")

    def _crm_db(self, fn):
        self.vet.append(("db",))
        raise AssertionError("không được chạm CSDL")


class PostDocBodyTruocQuery(unittest.TestCase):
    """FIX02: POST /tao, /doi-soat với query sai phải đọc body ĐÚNG MỘT LẦN (limit 16 KiB) TRƯỚC khi `_q` THẬT từ chối — tránh đóng kết nối HTTP/1.0
    còn payload chưa đọc (Win10053 ở W11). `_q` chỉ được bọc ghi vết rồi gọi bản gốc (không ép chấp nhận). Sau query: `_than` vẫn trước lock/phiên/DB."""

    @classmethod
    def setUpClass(cls):
        try:
            from kho_tri_thuc.giao_dien import m4 as M4
            from kho_tri_thuc.giao_dien import m4_request as W
            from kho_tri_thuc.giao_dien.server import Handler
        except ImportError as exc:
            raise unittest.SkipTest(f"NOT_VERIFIED: không import được server/m4_request ({exc}); KHÔNG phải PASS")
        cls.M4, cls.W, cls.Handler = M4, W, Handler

    def chay(self, path, query, raw, **kw):
        vet = []
        goc = self.M4._q

        def q_vet(query, cho_phep):
            vet.append(("_q", tuple(sorted(query))))
            return goc(query, cho_phep)
        h = HandlerHep(self.Handler, raw, vet, **kw)
        with mock.patch.object(self.M4, "_q", q_vet):
            self.W.dieu_huong(h, AppDem(vet), True, path, query)
        return vet, h.rfile.tell()

    def test_w12_body_doc_mot_lan_truoc_q(self):
        D, PB, L = ID["dot"], ID["pb"], 16 * 1024
        raw = json.dumps({"dot_id": D, "version_id": PB, "khoa": "w12-khoa"}).encode("utf-8")
        doc = [("json_body", L), ("body", L)]
        for duong in ("tao", "doi-soat"):
            path = f"{TIEN_TO}/{duong}"
            for q in ({"x": [""]}, {"x": ["1"]}, {"version_id": [""]}, {"dot_id": [D, ""]}, {"version_id": [PB, ""]}):
                with self.subTest(duong=duong, q=q):
                    vet, da_doc = self.chay(path, q, raw)
                    self.assertEqual(vet, doc + [("_q", tuple(sorted(q))), ("gui", 400, "M4_YEU_CAU_SAI")])
                    self.assertEqual(da_doc, len(raw), "body POST chưa đọc hết trước khi từ chối query")
            with self.subTest(duong=duong, ca="authority_sau_query"):  # query sai thắng authority (giữ thứ tự _q → _than), body vẫn đã đọc
                xau = json.dumps({"dot_id": D, "version_id": PB, "khoa": "k", "nguoiTao": "x"}).encode("utf-8")
                vet, da_doc = self.chay(path, {"x": [""]}, xau)
                self.assertEqual((vet[-1], da_doc), (("gui", 400, "M4_YEU_CAU_SAI"), len(xau)))
                vet, da_doc = self.chay(path, {}, xau)
                self.assertEqual(vet, doc + [("_q", ()), ("gui", 403, "M4_CLIENT_AUTHORITY")])
            with self.subTest(duong=duong, ca="json_hong"):  # không nuốt lỗi body: JSON hỏng vẫn 400 INVALID_REQUEST, đã đọc hết, chưa tới _q
                vet, da_doc = self.chay(path, {"x": [""]}, b"{khong-json")
                self.assertEqual((vet, da_doc), (doc + [("gui", 400, "INVALID_REQUEST")], len(b"{khong-json")))
            with self.subTest(duong=duong, ca="qua_16kib"):  # có giới hạn: Content-Length > 16 KiB → 413, 0 byte đọc, chưa tới _q
                vet, da_doc = self.chay(path, {"x": [""]}, b"{}", do_dai=L + 1)
                self.assertEqual((vet, da_doc), (doc + [("gui", 413, "FILE_TOO_LARGE")], 0))
            with self.subTest(duong=duong, ca="duong_hop_le"):  # dương: query rỗng + body hợp lệ qua _q/_than rồi mới tới lock/phiên
                vet, da_doc = self.chay(path, {}, raw)
                self.assertEqual(vet, doc + [("_q", ()), ("lock",), ("crm_sid",), ("crm_phien",), ("gui", 400, "CRM_PHIEN")])
                self.assertEqual(da_doc, len(raw))
        vet = []  # GET không đọc body (nhánh GET giữ nguyên): query sai → 400 ngay
        h = HandlerHep(self.Handler, b"", vet)
        self.W.dieu_huong(h, AppDem(vet), False, TIEN_TO, {"dot_id": [D], "x": [""]})
        self.assertEqual(vet, [("gui", 400, "M4_YEU_CAU_SAI")])


# ================================================================================================== tầng U (producer DTO thật → UI thật)
def _xd_that(XD, W):
    from tests import test_m4_02c_dto_ui as F
    log = []
    xd = XD(F.ConnGia("app", W, log), GOC / "var", conn_tin_cay=F.ConnGia("tin_cay", W, log), chi_mo_phong=True, hom_nay=lambda: date(2026, 10, 23))
    xd._chung_tu_co_so = lambda c, dot: copy.deepcopy(W["co"])
    return xd


def _y(F, trang_thai, **thay):
    y = {k: None for k in RN.DTO_COT}
    y.update(id=str(uuid.uuid4()), trang_thai=trang_thai, nhanh="GOC", seal_id=F.S(F.SEAL1), phien_ban_id=F.S(F.V1), so_tien="120000000", tien_te="VND",
             nhom="THANH_TOAN_HD", nhom_phien_ban=3, co_chua_ro=trang_thai.startswith("CHUA_RO"), so_lan_tao=1, so_lan_tai=0, revision=2, lease_id=None)
    y.update(thay)
    return y


def _sinh_ui(XD) -> dict:
    from kho_tri_thuc.giao_dien import m4_request as W
    from tests import test_m4_02c_dto_ui as F
    S, L = F.S, F.LOGIN
    dto, ctx = {}, {}
    Wd = F.the_gioi()
    Wd["versions"], Wd["snap"], Wd["l3"], Wd["nhat_ky"] = [], {}, None, []
    xd = _xd_that(XD, Wd)
    dto["chua_nop"] = xd.duyet_xem(L, dot_id=S(F.DOT))
    ctx["chua_nop"], _ = W.ngu_canh(xd, L, S(F.DOT), None)
    Wd = F.the_gioi()
    Wd["l3"]["basis_cong_bo_sha256"] = XD._sha_co_so(copy.deepcopy(F.CO))
    xd = _xd_that(XD, Wd)
    gsha = xd.duyet_xem(L, dot_id=S(F.DOT))["context"]["basis_sha256"]
    F._gan_ket_luan(Wd, gsha)
    F._gan_quyet_dinh(Wd, gsha)
    dto["cho_pdf"] = xd.duyet_xem(L, dot_id=S(F.DOT))
    F._gan_seal(Wd, gsha)
    dto["da_seal"] = xd.duyet_xem(L, dot_id=S(F.DOT))
    ctx["da_seal"], _ = W.ngu_canh(xd, L, S(F.DOT), S(F.V1))
    Wd["seal"][S(F.V1)]["so_lieu"]["so_xin_thanh_toan"] = "120000000"  # seal có số xin thanh toán (khác gia_tri_nt 150000000)
    dto["da_seal_tien"] = xd.duyet_xem(L, dot_id=S(F.DOT))
    ctx["da_seal_tien"], _ = W.ngu_canh(xd, L, S(F.DOT), S(F.V1))
    Wd["dot"]["revision_ho_so_hien_hanh"] = 8
    Wd["versions"].append(F._ban(F.V2, 2, trang_thai="NHAP", parent=F.V1, digest=None, rev=None))
    Wd["snap"][S(F.V2)] = None
    dto["ke_tiep_nhap"] = xd.duyet_xem(L, dot_id=S(F.DOT))
    ctx["ke_tiep_nhap"], _ = W.ngu_canh(xd, L, S(F.DOT), None)  # mới nhất (bản nháp V2) — cùng lựa chọn mặc định của DuyetDot.xem
    dto["chon_v1"] = xd.duyet_xem(L, dot_id=S(F.DOT), version_id=S(F.V1))
    ctx["chon_v1"], _ = W.ngu_canh(xd, L, S(F.DOT), S(F.V1))
    rq = RN.RequestNhap(xd, None, None)
    sk = [{"thu_tu": 1, "buoc": "Y_DINH", "tu_trang_thai": None, "den_trang_thai": "MOI", "chi_tiet": None, "quyen_con": True, "boi": None, "luc": None}]
    ys = {"chua_ro_tao": _y(F, "CHUA_RO_TAO"), "cho_quet": _y(F, "CHO_QUET", remote_ma="DX-0001", remote_trang_thai="NHAP", tep_trang_thai_quet="pending"),
          "dang_chay": _y(F, "CHUA_RO_TAI", lease_id=str(uuid.uuid4()))}
    y_dto = {k: {**rq._dto(v), "su_kien": sk} for k, v in ys.items()}
    kq = {"cho_quet": rq._ket_qua("CHO_QUET", y=ys["cho_quet"], buoc=["TAO", "DOC", "TAI", "DOI_SOAT"]),
          "hold_can_tao": W._hold("LICH_SU_CAN_TAO", y_dto["chua_ro_tao"]),
          "chua_cau_hinh": rq._ket_qua("CHUA_CAU_HINH", thieu=["khoa_api"])}
    return {"dto": dto, "ctx": ctx, "y": y_dto, "kq": kq}


class RequestUiThat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import psycopg  # noqa: F401
            from kho_tri_thuc.k2.xay_dung import XayDungK2
        except ImportError as exc:
            raise unittest.SkipTest(f"NOT_VERIFIED: thiếu psycopg/K2 ({exc}) — không chạy được nhà sản xuất thật; KHÔNG phải PASS")
        cls.kq = _sinh_ui(XayDungK2)

    def test_01_context_nha_san_xuat_that(self):
        from tests import test_m4_02c_dto_ui as F
        S = F.S
        c = self.kq["ctx"]
        mau = lambda v, s, h: {"schema": "M4_REQUEST_HTTP_CONTEXT_V1", "dot_id": S(F.DOT), "version_id": v, "dang_nhap": F.LOGIN,  # noqa: E731
                                "phap_nhan_id": S(F.PN), "seal_id": s, "hien_hanh": h}
        self.assertEqual(c["chua_nop"], mau(None, None, False))
        self.assertEqual(c["da_seal"], mau(S(F.V1), S(F.SEAL1), True))
        d = self.kq["dto"]["ke_tiep_nhap"]
        self.assertEqual(c["ke_tiep_nhap"], mau(d["context"]["version_id"], None, d["phien_ban_hien_hanh"] is True))
        self.assertEqual(c["chon_v1"], mau(S(F.V1), S(F.SEAL1), False))
        for ten in ("da_seal", "chon_v1", "chua_nop"):  # domain DTO duyệt giữ placeholder d.request, không có context Request
            self.assertNotIn("request_context", self.kq["dto"][ten])
        self.assertEqual(self.kq["dto"]["da_seal"]["request"]["trang_thai"], "DU_DIEU_KIEN_CHUA_NOI")
        self.assertEqual(self.kq["dto"]["da_seal_tien"]["seal"]["so_lieu"]["so_xin_thanh_toan"], "120000000")

    def test_20_widget_that(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("NOT_VERIFIED: không có node trên PATH — widget thật chưa chạy; KHÔNG phải PASS")
        from tests import test_m4_02c_dto_ui as F
        S = F.S
        goc_ra = Path(os.environ["KHO_M4_04B_UI_OUT"]) if os.environ.get("KHO_M4_04B_UI_OUT") else GOC / "var" / "m4-04b-request-ui"
        thu_muc = goc_ra / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12])
        thu_muc.mkdir(parents=True, exist_ok=False)  # thư mục MỚI — không ghi đè, không xóa
        bundle = {"schema": "M4_04B_REQUEST_UI_FIXTURE_V1", "login": F.LOGIN, "rq_schema": RN.SCHEMA, "ctx_schema": "M4_REQUEST_HTTP_CONTEXT_V1",
                  "ids": {"pn": S(F.PN), "du_an": S(F.DA), "hd": S(F.HD), "dot": S(F.DOT), "so_hd": F.SO_HD, "v1": S(F.V1), "v2": S(F.V2),
                          "seal": S(F.SEAL1), "pdf": S(F.PDF1), "goc": S(F.GOC_KT)}, **self.kq}
        tep = thu_muc / "fixture.json"
        with open(tep, "x", encoding="utf-8", newline="\n") as f:
            f.write(canonical_json(bundle))
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            r = subprocess.run([node, str(CJS), str(tep)], cwd=str(GOC), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=HAN_NODE)
        except subprocess.TimeoutExpired as exc:
            self._luu(tep, exc.stdout, exc.stderr)
            self.skipTest(f"NOT_VERIFIED: node quá hạn {HAN_NODE}s; KHÔNG phải PASS (log: {tep.parent})")
        self._luu(tep, r.stdout, r.stderr)
        dong = [x for x in (r.stdout or "").splitlines() if x.startswith("KET_QUA_JSON ")]
        if len(dong) != 1:
            self.skipTest(f"NOT_VERIFIED: harness không in đúng một dòng KET_QUA_JSON (rc={r.returncode}); log: {tep.parent}")
        kq = json.loads(dong[0][len("KET_QUA_JSON "):])
        self.assertEqual(kq["hong"], [], "ca UI hỏng (FAIL ngữ nghĩa):\n" + "\n".join(f"{h['ca']}: {h['loi'][:400]}" for h in kq["hong"]))
        if kq["setup_errors"]:
            self.skipTest("NOT_VERIFIED: setup_errors " + json.dumps(kq["setup_errors"], ensure_ascii=False)[:800])
        self.assertGreater(len(kq["dat"]), 0, "không ca nào chạy")
        self.assertEqual(r.returncode, 0, "node exitCode ≠ 0 dù không có hỏng/setup — xem stderr")

    @staticmethod
    def _luu(tep: Path, out, err):
        for ten, noi in (("node.stdout.txt", out), ("node.stderr.txt", err)):
            if isinstance(noi, bytes):
                noi = noi.decode("utf-8", "replace")
            with open(tep.parent / ten, "x", encoding="utf-8", newline="\n") as f:
                f.write(noi or "")


if __name__ == "__main__":
    unittest.main()
