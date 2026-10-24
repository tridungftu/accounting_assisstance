"""CRM G5-B — kiểm HTTP dispatcher (thuần: handler/app/service GIẢ, không CSDL/engine/mạng) cho route đối chiếu trên CHÍNH ``giao_dien/crm_g.py``
(CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

Phủ: route GET VIEW / POST chay + doi-soat; không nhận query; trường thẩm quyền (expected/catalog/principal/kết quả/chế độ) → 403 TRƯỚC service;
trường lạ → 400; ánh xạ mã → 403/404/409/503/400; lỗi → KHÔNG đánh thức worker; factory dùng ``app.trich6_client`` + worker khởi tạo MỘT lần;
G4 ký-kết đánh thức worker mà KHÔNG đổi ACK (kể cả khi factory lỗi); FIX02: first entry từng factory G/Gk/Ky/Kiem/G5 (tuần tự + đồng thời
hỗn hợp) → một chuỗi identity + một constructor mỗi tầng + một worker; service thật + kết nối giả → đúng tham số SQL (khóa, digest, ky, ngữ cảnh);
golden khóa VIEW/ACK khớp chuỗi SQL ``crm_g5_doc``/``crm_g5_ack``.
Luồng PG/LocalServer thật nằm ở tests/test_crm_doi_chieu_pg.py. NHÃN: mọi service/ACK ở đây là GIẢ (DEMO) — không phải bằng chứng vận hành.
"""

from __future__ import annotations

import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_crm_doi_chieu_tinh as T

from kho_tri_thuc.giao_dien import crm_g as CG
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_doi_chieu as DC
from kho_tri_thuc.k2.crm_mau import _h
from kho_tri_thuc.k2.sql_crm_doi_chieu import CRM_G5_SQL

KY, CTX = T.KY, T.CTX
ME = "MO_PHONG_KT_A"
SQL_TXT = "\n".join(CRM_G5_SQL)
VIEW_KHOA = {"kieu", "ky_id", "context_sha256", "bat_buoc", "khoi_tao", "quyen", "readiness", "current_job", "current_result", "history", "g6"}
JOB_KHOA = {"job_id", "loai", "trang_thai", "ly_do", "request_id", "the_he", "so_lan", "khoi_tao_loai", "cap_nhat_luc"}
KQ_KHOA = {"result_id", "trang_thai", "hien_hanh", "nhan_dang_ky", "tac_nhan_loai", "so_phu", "so_ma", "so_lech", "so_thieu", "tham_so", "tao_luc"}
TS_KHOA = {"ma", "crm_truong", "muc", "kieu", "gia_tri_ky_vong", "gia_tri_ban_ky", "trich_dan", "vi_tri_do_duoc", "trang_thai"}
LS_KHOA = {"result_id", "trang_thai", "tac_nhan_loai", "hien_hanh", "so_lech", "so_thieu", "tao_luc"}
ACK_SQL_KHOA = {"kieu", "ky_id", "context_sha256", "job_id", "request_id", "state", "current_result_id"}
ACK_KHOA = ACK_SQL_KHOA | {"tao_moi", "replay"}
ACK = {"kieu": "CRM_G5_ACK_V1", "ky_id": KY, "context_sha256": CTX, "job_id": T.VIEC, "request_id": f"crm-g5-{T.VIEC}-1", "state": "CHO",
       "current_result_id": None, "tao_moi": True}


class _H:
    def __init__(self, path, body=None):
        self.path, self.body, self.headers = path, body, {}
        self.st = self.data = self.mime = self.hd = None

    def json_body(self):
        return self.body

    def crm_sid(self):
        return "sid-gia"

    def send_content(self, status, data, mime=None, headers=None):
        self.st, self.data, self.mime, self.hd = status, data, mime, headers


class _Dc:
    """Service đối chiếu GIẢ: ghi lời gọi (chứng minh từ chối xảy ra TRƯỚC service)."""

    def __init__(self, loi=None):
        self.goi, self.loi = [], loi

    def _f(self, ten, *a, **kw):
        self.goi.append((ten, a, kw))
        if self.loi is not None:
            raise self.loi
        return {"kieu": "CRM_G5_VIEW_V1", "ky_id": KY} if ten == "doc" else {**ACK, "replay": False}

    def doc(self, *a, **kw):
        return self._f("doc", *a, **kw)

    def chay(self, *a, **kw):
        return self._f("chay", *a, **kw)

    def doi_soat(self, *a, **kw):
        return self._f("doi_soat", *a, **kw)


class _HD:
    def __init__(self):
        self.danh = 0

    def danh_thuc(self):
        self.danh += 1


class _App:
    def __init__(self, dv=None, hd=None, me=ME):
        self.mutation_lock, self.me, self.phien = threading.Lock(), me, 0
        if dv is not None:
            self.__dict__["_crm_g5"] = dv
        if hd is not None:
            self.__dict__["_crm_g5_hang_doi"] = hd

    def crm_phien(self, sid, *, tao=False):
        self.phien += 1
        return sid, self.me, False

    @staticmethod
    def _crm_db(fn, *a):
        return fn(*a)

    def trich6_client(self, goc):  # client Source6 của app (baseline: không gọi trong test này)
        raise AssertionError("factory không được gọi client khi khởi tạo")


def _than(**sua):
    d = {"ky_id": KY, "expected_context_sha256": CTX, "khoa": "dc-1"}
    d.update(sua)
    return d


class DieuHuongDoiChieu(unittest.TestCase):
    def chay(self, post, path, body=None, query=None, dv=None, hd=None, raw_path=None):
        dv = _Dc() if dv is None else dv
        hd = _HD() if hd is None else hd
        h = _H(raw_path or path, body)
        CG.dieu_huong(h, _App(dv, hd), post, path, query or {})
        return h, dv, hd

    def test_route_thuoc_module(self):
        for post, p in ((False, "/api/crm/giao-ket/doi-chieu/" + KY), (True, "/api/crm/giao-ket/doi-chieu/chay"),
                        (True, "/api/crm/giao-ket/doi-chieu/doi-soat")):
            self.assertTrue(CG.la_route(post, p), p)
        self.assertEqual(set(CG.TRUONG_DC), {"giao-ket/doi-chieu/chay", "giao-ket/doi-chieu/doi-soat"})
        for v in CG.TRUONG_DC.values():
            self.assertEqual(v, {"ky_id", "expected_context_sha256", "khoa"})  # chỉ đích + ngữ cảnh CAS + khóa

    def test_get_view(self):
        h, dv, hd = self.chay(False, "/api/crm/giao-ket/doi-chieu/" + KY)
        self.assertEqual((h.st, h.data["kieu"]), (200, "CRM_G5_VIEW_V1"))
        self.assertEqual(dv.goi, [("doc", (ME, KY), {})])
        self.assertEqual(hd.danh, 0)  # đọc không đánh thức worker

    def test_get_khong_nhan_query(self):
        for q, raw in (({"nguoi_chay": ["x"]}, None), ({}, "/api/crm/giao-ket/doi-chieu/" + KY + "?x")):
            h, dv, _ = self.chay(False, "/api/crm/giao-ket/doi-chieu/" + KY, query=q, raw_path=raw)
            self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"))
            self.assertEqual(dv.goi, [])

    def test_get_ky_sai_dang(self):
        h, dv, _ = self.chay(False, "/api/crm/giao-ket/doi-chieu/KHONG-PHAI-UUID")
        self.assertEqual(h.st, 404)
        self.assertEqual(dv.goi, [])

    def test_post_chay_va_doi_soat(self):
        for ten, ham in (("chay", "chay"), ("doi-soat", "doi_soat")):
            h, dv, hd = self.chay(True, "/api/crm/giao-ket/doi-chieu/" + ten, _than(khoa="dc-" + ten))
            self.assertEqual(h.st, 200, h.data)
            self.assertEqual(dv.goi, [(ham, (ME,), {"ky_id": KY, "expected_context_sha256": CTX, "khoa": "dc-" + ten})])
            self.assertEqual(h.data, {**ACK, "replay": False})
            self.assertEqual(hd.danh, 1)  # đánh thức worker SAU commit (một lần)

    def test_truong_tham_quyen_403_truoc_service(self):
        cam = sorted(CG.KHONG_NHAN_DC | CG.KHONG_NHAN_KIEM | {"phap_nhan_id"})
        for k in cam:
            for ten in ("chay", "doi-soat"):
                h, dv, hd = self.chay(True, "/api/crm/giao-ket/doi-chieu/" + ten, _than(**{k: "x"}))
                self.assertEqual((h.st, h.data["error"]), (403, "CRM_G_CLIENT_AUTHORITY"), k)
                self.assertEqual((dv.goi, hd.danh), ([], 0), k)
        for k in ("expected", "catalog_binding", "nguoi_chay", "principal", "request_id", "result_id", "mode", "lineage", "soan_rev_id", "g5"):
            self.assertIn(k, cam)  # expected/catalog/principal/kết quả/chế độ — không bao giờ từ trình duyệt

    def test_than_sai_400(self):
        for body in (_than(them="x"), [1, 2], "chuoi", None):
            h, dv, hd = self.chay(True, "/api/crm/giao-ket/doi-chieu/chay", body)
            self.assertEqual(h.st, 400, body)
            self.assertEqual((dv.goi, hd.danh), ([], 0))
        h, dv, _ = self.chay(True, "/api/crm/giao-ket/doi-chieu/chay", _than(), query={"khoa": ["x"]})
        self.assertEqual((h.st, h.data["error"], dv.goi), (400, "CRM_G_YEU_CAU_SAI", []))
        h, dv, _ = self.chay(True, "/api/crm/giao-ket/doi-chieu/xoa", _than())
        self.assertEqual((h.st, dv.goi), (404, []))

    def test_anh_xa_ma_va_khong_danh_thuc_khi_loi(self):
        ca = [(c, 409) for c in sorted(CG.MA_409_DC)] + [("CRM_G_IDEMPOTENCY_KHAC", 409), ("CRM_KIEM_CHUA_CO_PHAM_VI", 403), ("CRM_G_KHONG_THAY", 404),
                                                          ("CRM_G_CHUA_SAN_SANG", 503), ("CRM_G_YEU_CAU_SAI", 400), ("CRM_G5_EXPECTED_SAI", 400)]
        for ma, st in ca:
            for post, p, body in ((True, "/api/crm/giao-ket/doi-chieu/chay", _than()), (False, "/api/crm/giao-ket/doi-chieu/" + KY, None)):
                h, dv, hd = self.chay(post, p, body, dv=_Dc(DataError(ma, "giả")))
                self.assertEqual((h.st, h.data["error"]), (st, ma), (ma, p))
                self.assertEqual(hd.danh, 0, ma)  # lỗi: không đánh thức (không có commit)

    def test_danh_thuc_loi_khong_doi_ack(self):
        class _HDLoi:
            def danh_thuc(self):
                raise RuntimeError("worker hỏng")
        h, _, _ = self.chay(True, "/api/crm/giao-ket/doi-chieu/chay", _than(), hd=_HDLoi())
        self.assertEqual((h.st, h.data), (200, {**ACK, "replay": False}))  # lệnh đã commit: ACK giữ nguyên, hàng đợi bền drain sau


class FactoryDoiChieu(unittest.TestCase):
    def _app(self):
        app = _App()
        app.__dict__["_crm_kiem"] = T._Kiem(T._Conn())  # service G6A giả (CHÍNH chuỗi kiem → ky → gk.kho)
        return app

    def test_mot_service_mot_worker_client_cua_app(self):
        app = self._app()
        goi = []
        with patch.object(DC.HangDoiG5, "bat_dau", lambda self_: goi.append(self_)), \
             patch.object(DC.HangDoiG5, "danh_thuc", lambda self_: goi.append("danh")):
            dv = CG.dich_vu_doi_chieu(app)
            self.assertIs(CG.dich_vu_doi_chieu(app), dv)
            self.assertIs(CG.dich_vu_doi_chieu(app), dv)
        self.assertIsInstance(dv, DC.CrmDoiChieuK2)
        self.assertIs(dv.kiem, app.__dict__["_crm_kiem"])
        self.assertEqual(dv.client_fn, app.trich6_client)  # MỘT client Source6 của app — không client/engine thứ hai
        hd = app.__dict__["_crm_g5_hang_doi"]
        self.assertIsInstance(hd, DC.HangDoiG5)
        self.assertEqual(goi, [hd, "danh"])  # worker khởi động đúng một lần + đánh thức để drain/recover
        self.assertIs(hd.lock, app.mutation_lock)
        self.assertEqual(hd.db, app._crm_db)
        self.assertEqual(dv.kho, dv.ky.gk.kho / "doi-chieu")

    def test_khong_co_trich6_client_la_cho_cau_hinh(self):
        app = self._app()
        app.__dict__["trich6_client"] = None
        with patch.object(DC.HangDoiG5, "bat_dau", lambda self_: None):
            dv = CG.dich_vu_doi_chieu(app)
        self.assertIsNone(dv.client_fn)
        loai, ma = dv.goi_engine(T._p(body=T._body()))
        self.assertEqual((loai, ma), ("CHO_CAU_HINH", "E5_CHUA_GHEP"))  # chưa ghép E5 → chờ cấu hình, không MATCH giả

    def test_ky_ket_danh_thuc_khong_doi_ack(self):
        ack_g4 = {"ky_id": KY, "g5": {"trang_thai": "PENDING", "ly_do": "BAT_BUOC_KHAI_CO"}, "lap_lai": False}
        hd = _HD()
        h = _H("/api/crm/giao-ket/ky-ket")
        with patch.object(CG, "_ky_ket", return_value=dict(ack_g4)):
            CG.dieu_huong(h, _App(_Dc(), hd), True, "/api/crm/giao-ket/ky-ket", {})
        self.assertEqual((h.st, h.data, hd.danh), (200, ack_g4, 1))
        h = _H("/api/crm/giao-ket/ky-ket")
        app = _App()  # không service G6A/worker: factory lỗi → nuốt, ACK G4 không đổi (việc bắt buộc đã ghi trong giao dịch ký)
        with patch.object(CG, "_ky_ket", return_value=dict(ack_g4)), patch.object(CG, "dich_vu_kiem", side_effect=RuntimeError("chưa cấu hình")):
            CG.dieu_huong(h, app, True, "/api/crm/giao-ket/ky-ket", {})
        self.assertEqual((h.st, h.data), (200, ack_g4))

    def test_ky_ket_loi_khong_danh_thuc(self):
        hd = _HD()
        h = _H("/api/crm/giao-ket/ky-ket")
        with patch.object(CG, "_ky_ket", side_effect=DataError("CRM_KY_DA_KY", "giả")):
            CG.dieu_huong(h, _App(_Dc(), hd), True, "/api/crm/giao-ket/ky-ket", {})
        self.assertEqual((h.st, h.data["error"], hd.danh), (409, "CRM_KY_DA_KY", 0))


# ---------------------------------------------------------------------------------------------------------------- FIX01-C (bổ sung)
class _AppThuong(_App):
    """App giả có ĐÚNG giao diện LocalApp mà factory THẬT dùng (crm()/_m5_ket_noi_chu/root/mutation_lock/_crm_db/trich6_client).
    Factory G/Gk/Ky/Kiem/G5 cần kiểm KHÔNG bị thay; chỉ lớp CrmMauK2 (cần psycopg + PG) được thay bằng mẫu giả trên T._Conn."""

    def __init__(self, loi_chu=None):
        super().__init__()
        self.root = Path(tempfile.mkdtemp(prefix="ktt_g5b_fix01_"))  # giữ lại (không xóa)
        self.goi_crm, self.loi_chu = 0, loi_chu

    def crm(self):
        self.goi_crm += 1
        return type("Crm", (), {"conn": "kn-login-ung-dung", "hom_nay": None})()

    def _m5_ket_noi_chu(self, conn):
        if self.loi_chu is not None:
            raise DataError(self.loi_chu, "giả: chưa kết nối được chủ bảng")
        return "kn-chu-bang"


def _mau_gia(conn, ghi, cho=None):
    class _MauGia(T._Mau):
        def __init__(self, app_conn, root, *, conn_tin_cay=None, hom_nay=None):
            if cho is not None:
                cho()  # giữ luồng GIỮA check và create để chứng minh đồng bộ thực
            super().__init__(conn)
            self.app_conn, self.root, self.conn_tin_cay, self.hom_nay = app_conn, root, conn_tin_cay, hom_nay
            ghi.append(self)

        def _c(self):  # như CrmMauK2: thiếu kết nối chủ bảng → CRM_G_CHUA_SAN_SANG (trạng thái thật, không fallback)
            if self.conn_tin_cay is None:
                raise DataError("CRM_G_CHUA_SAN_SANG", "giả: chưa có kết nối chủ bảng")
            return super()._c()
    return _MauGia


def _bat_dau_mot_chu_ky(ghi):
    """Thay thread nền bằng ĐÚNG một chu kỳ thân `_vong` chạy đồng bộ (deterministic): mot_luot thật, lỗi → loi_cuoi."""
    def bat_dau(self_):
        ghi.append(self_)
        try:
            self_.mot_luot()
            self_.loi_cuoi = None
        except Exception as exc:  # noqa: BLE001 — giống _vong
            self_.loi_cuoi = getattr(exc, "code", type(exc).__name__)
    return bat_dau


class FactoryKhoiTaoThuong(unittest.TestCase):
    MAU = "kho_tri_thuc.k2.crm_mau.CrmMauK2"

    def test_dich_vu_thuong_khoi_tao_worker_va_drain_mot_lan(self):
        conn = T._Conn({"crm_g5_hang_doi": [[]]})  # đúng MỘT lượt drain được phép (lượt thứ hai → IndexError)
        mau, bat = [], []
        app = _AppThuong()
        with patch(self.MAU, _mau_gia(conn, mau)), patch.object(DC.HangDoiG5, "bat_dau", _bat_dau_mot_chu_ky(bat)):
            svc = CG.dich_vu(app)  # CHỈ factory G thường — không gọi route G5, không ký G4
            hd = app.__dict__["_crm_g5_hang_doi"]
            for _ in range(3):  # gọi lại/refresh: không service/worker/drain thứ hai
                self.assertIs(CG.dich_vu(app), svc)
                self.assertIs(CG.dich_vu_kiem(app), app.__dict__["_crm_kiem"])
                self.assertIs(CG.dich_vu_doi_chieu(app), app.__dict__["_crm_g5"])
                CG._danh_thuc_g5(app)
                self.assertIs(app.__dict__["_crm_g5_hang_doi"], hd)
        self.assertEqual((len(mau), app.goi_crm), (1, 1))
        self.assertEqual(bat, [hd])
        self.assertEqual(conn.goi, [("crm_g5_hang_doi", (hd.lo,), None)])  # drain đúng một lần, kết nối chủ bảng, không mượn danh tính
        self.assertIsNone(hd.loi_cuoi)
        dv = app.__dict__["_crm_g5"]
        self.assertIs(dv.kiem, app.__dict__["_crm_kiem"])  # CHÍNH chuỗi factory G → Gk → Ky → Kiem → G5
        self.assertIs(dv.ky, app.__dict__["_crm_ky"])
        self.assertIs(dv.ky.gk, app.__dict__["_crm_gk"])
        self.assertIs(dv.mau, svc)
        self.assertEqual((svc.app_conn, svc.conn_tin_cay), ("kn-login-ung-dung", "kn-chu-bang"))
        self.assertEqual(dv.client_fn, app.trich6_client)  # client Source6 của app, không client thay thế; không gọi khi init
        self.assertIs(hd.lock, app.mutation_lock)
        self.assertFalse(app.mutation_lock.locked())
        self.assertIsNone(app.__dict__["_crm_g5_loi_khoi_tao"])

    def test_khoi_tao_dong_thoi_mot_service_mot_worker(self):
        conn = T._Conn({"crm_g5_hang_doi": [[]]})
        mau, bat, kq = [], [], {}
        vao, di = threading.Event(), threading.Event()

        def cho():
            vao.set()
            di.wait(10)
        app = _AppThuong()
        with patch(self.MAU, _mau_gia(conn, mau, cho)), patch.object(DC.HangDoiG5, "bat_dau", _bat_dau_mot_chu_ky(bat)):
            ta = threading.Thread(target=lambda: kq.__setitem__("a", CG.dich_vu(app)), daemon=True)
            tb = threading.Thread(target=lambda: kq.__setitem__("b", CG.dich_vu_doi_chieu(app)), daemon=True)
            ta.start()
            self.assertTrue(vao.wait(10))  # A đang GIỮA check và create
            tb.start()
            tb.join(0.2)
            self.assertTrue(tb.is_alive())  # B chờ _KHOI_TAO (không tự dựng service/worker thứ hai)
            di.set()
            ta.join(10)
            tb.join(10)
        self.assertFalse(ta.is_alive() or tb.is_alive())
        self.assertEqual(len(mau), 1)
        self.assertIs(kq["a"], mau[0])
        self.assertIs(kq["b"], app.__dict__["_crm_g5"])
        self.assertEqual(bat, [app.__dict__["_crm_g5_hang_doi"]])
        self.assertEqual([h for h, _, _ in conn.goi], ["crm_g5_hang_doi"])

    def test_chua_cau_hinh_giu_trang_thai_that(self):
        conn = T._Conn({})
        mau, bat = [], []
        app = _AppThuong(loi_chu="PG_KHONG_KET_NOI")
        with patch(self.MAU, _mau_gia(conn, mau)), patch.object(DC.HangDoiG5, "bat_dau", _bat_dau_mot_chu_ky(bat)):
            svc = CG.dich_vu(app)
        self.assertEqual((svc.conn_tin_cay, svc.ly_do_chua_san_sang), (None, "PG_KHONG_KET_NOI"))  # G vẫn trả service, lý do thật
        hd = app.__dict__["_crm_g5_hang_doi"]
        self.assertEqual((bat, hd.loi_cuoi), ([hd], "CRM_G_CHUA_SAN_SANG"))  # worker giữ lỗi thật; không SQL, không fallback
        self.assertEqual(conn.goi, [])

    def test_loi_khoi_tao_g5_khong_hong_g_va_danh_thuc_khong_tao(self):
        conn = T._Conn({})
        mau, bat = [], []
        app = _AppThuong()
        del app.__dict__["mutation_lock"]  # thiếu thuộc tính worker cần → lỗi khởi tạo G5
        with patch(self.MAU, _mau_gia(conn, mau)), patch.object(DC.HangDoiG5, "bat_dau", _bat_dau_mot_chu_ky(bat)):
            svc = CG.dich_vu(app)
            self.assertIs(CG.dich_vu(app), svc)
            CG._danh_thuc_g5(app)  # chỉ đánh thức worker đã có — không dựng mới ngoài factory
        self.assertEqual(app.__dict__["_crm_g5_loi_khoi_tao"], "AttributeError")
        self.assertIsNone(app.__dict__.get("_crm_g5_hang_doi"))
        self.assertEqual((bat, conn.goi, len(mau)), ([], [], 1))
        self.assertFalse(app.__dict__.get("_crm_g5_dang_tao"))


# ---------------------------------------------------------------------------------------------------------------- FIX02 (bổ sung)
# (factory, khóa cache app) — đủ 5 factory G/Gk/Ky/Kiem/G5
_FACTORY = (("dich_vu", "_crm_g"), ("dich_vu_gk", "_crm_gk"), ("dich_vu_ky", "_crm_ky"), ("dich_vu_kiem", "_crm_kiem"),
            ("dich_vu_doi_chieu", "_crm_g5"))
_LOP = {"_crm_gk": "kho_tri_thuc.k2.crm_giao_ket.CrmGiaoKetK2", "_crm_ky": "kho_tri_thuc.k2.crm_ky_ket.CrmKyKetK2",
        "_crm_kiem": "kho_tri_thuc.k2.crm_kiem_hd.CrmKiemHdK2", "_crm_g5": "kho_tri_thuc.k2.crm_doi_chieu.CrmDoiChieuK2"}


def _dem(duong_dan: str, ghi: list):
    """Lớp THẬT + đếm constructor (không đổi hành vi): factory thật gọi lớp qua import tại chỗ nên patch module là đủ."""
    mod, ten = duong_dan.rsplit(".", 1)
    goc = getattr(__import__(mod, fromlist=[ten]), ten)

    class _Dem(goc):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            ghi.append(self)
    return _Dem


class FactoryFirstEntry(unittest.TestCase):
    """FIX02: bằng chứng độc lập — first entry Gk/Ky/Kiem để constructor NGOÀI ghi đè đối tượng mà khởi tạo G (qua G5) đã dựng bên trong.
    Chỉ thay lớp mẫu (kết nối chủ bảng giả) và thread nền (một chu kỳ đồng bộ); 5 factory + 4 lớp Gk/Ky/Kiem/G5 là THẬT (chỉ đếm)."""
    MAU = FactoryKhoiTaoThuong.MAU

    def _moi(self, cho=None):
        self.conn = T._Conn({"crm_g5_hang_doi": [[]]})  # đúng MỘT lượt drain được phép
        self.mau, self.bat = [], []
        self.lop = {k: [] for k in _LOP}
        ps = [patch(self.MAU, _mau_gia(self.conn, self.mau, cho)), patch.object(DC.HangDoiG5, "bat_dau", _bat_dau_mot_chu_ky(self.bat))]
        ps += [patch(duong, _dem(duong, self.lop[k])) for k, duong in _LOP.items()]
        return _AppThuong(), ps

    def _chuoi(self, app):
        d = app.__dict__
        dv = d["_crm_g5"]
        self.assertIs(dv.mau, d["_crm_g"])
        self.assertIs(dv.ky.gk, d["_crm_gk"])
        self.assertIs(dv.ky, d["_crm_ky"])
        self.assertIs(dv.kiem, d["_crm_kiem"])
        self.assertEqual(len(self.mau), 1)
        self.assertIs(self.mau[0], d["_crm_g"])
        for k, ds in self.lop.items():  # đúng MỘT constructor mỗi tầng, và đối tượng duy nhất đó là đối tượng trong cache
            self.assertEqual(len(ds), 1, k)
            self.assertIs(ds[0], d[k], k)
        hd = d["_crm_g5_hang_doi"]
        self.assertEqual(self.bat, [hd])  # một worker, khởi động một lần
        self.assertIs(hd.lock, app.mutation_lock)
        self.assertEqual(self.conn.goi, [("crm_g5_hang_doi", (hd.lo,), None)])  # một drain, kết nối chủ bảng
        self.assertIsNone(d["_crm_g5_loi_khoi_tao"])
        self.assertFalse(d.get("_crm_g5_dang_tao"))
        self.assertFalse(app.mutation_lock.locked())

    def test_moi_factory_la_first_entry_mot_chuoi(self):
        for ten, khoa in _FACTORY:
            with self.subTest(first_entry=ten):
                app, ps = self._moi()
                for p in ps:
                    p.start()
                try:
                    dau = getattr(CG, ten)(app)
                    self.assertIs(dau, app.__dict__[khoa])  # first entry trả CHÍNH đối tượng trong cache (không bị ghi đè sau)
                    snap = {**{k: app.__dict__[k] for _, k in _FACTORY}, "hd": app.__dict__["_crm_g5_hang_doi"]}
                    for _ in range(3):  # lặp lại mọi factory + đánh thức: không đổi identity, không dựng thêm
                        for t, k in _FACTORY:
                            self.assertIs(getattr(CG, t)(app), snap[k], t)
                        CG._danh_thuc_g5(app)
                    self.assertIs(app.__dict__["_crm_g5_hang_doi"], snap["hd"])
                finally:
                    for p in reversed(ps):
                        p.stop()
                self._chuoi(app)

    def test_first_entry_hon_hop_dong_thoi(self):
        """Mỗi factory lần lượt là luồng giữ khóa (dừng GIỮA check và create của CrmMauK2); 4 factory còn lại vào đồng thời và phải chờ."""
        for ten_giu, _ in _FACTORY:
            with self.subTest(giu=ten_giu):
                vao, di = threading.Event(), threading.Event()

                def cho():
                    vao.set()
                    di.wait(10)
                app, ps = self._moi(cho)
                kq, loi = {}, []

                def chay(t):
                    try:
                        for _ in range(3):
                            kq.setdefault(t, []).append(getattr(CG, t)(app))
                    except Exception as exc:  # noqa: BLE001 — ghi để assert, không nuốt
                        loi.append((t, exc))
                for p in ps:
                    p.start()
                try:
                    giu = threading.Thread(target=chay, args=(ten_giu,), daemon=True)
                    giu.start()
                    self.assertTrue(vao.wait(10))
                    khac = [threading.Thread(target=chay, args=(t,), daemon=True) for t, _ in _FACTORY if t != ten_giu]
                    for th in khac:
                        th.start()
                    for th in khac:
                        th.join(0.2)
                        self.assertTrue(th.is_alive())  # chờ _KHOI_TAO, không dựng chuỗi/worker thứ hai
                    di.set()
                    for th in [giu, *khac]:
                        th.join(10)
                        self.assertFalse(th.is_alive())
                finally:
                    di.set()
                    for p in reversed(ps):
                        p.stop()
                self.assertEqual(loi, [])
                for t, k in _FACTORY:
                    self.assertEqual(len(kq[t]), 3, t)
                    for x in kq[t]:
                        self.assertIs(x, app.__dict__[k], t)
                self._chuoi(app)


class ServiceThatKetNoiGia(unittest.TestCase):
    """Route → service THẬT (CrmDoiChieuK2) → kết nối GIẢ: chứng minh tham số SQL và danh tính giao dịch."""

    def test_chay_tham_so_sql(self):
        for ten, ham, hanh in (("chay", "crm_g5_chay", "CRM_G5_CHAY"), ("doi-soat", "crm_g5_doi_soat", "CRM_G5_DOI_SOAT")):
            conn = T._Conn({ham: [{"lap_lai": False, "ket_qua": {k: v for k, v in ACK.items()}}]})
            dv = DC.CrmDoiChieuK2(T._Kiem(conn))
            hd = _HD()
            h = _H("/api/crm/giao-ket/doi-chieu/" + ten, _than(khoa="dc-sql"))
            CG.dieu_huong(h, _App(dv, hd), True, "/api/crm/giao-ket/doi-chieu/" + ten, {})
            self.assertEqual(h.st, 200, h.data)
            self.assertEqual(h.data, {**ACK, "replay": False})
            self.assertEqual(set(h.data), ACK_KHOA)
            self.assertEqual(conn.goi, [(ham, ("dc-sql", _h(hanh, {"ky_id": KY, "expected_context_sha256": CTX}), KY, CTX), ME)])
            self.assertEqual(hd.danh, 1)

    def test_replay(self):
        conn = T._Conn({"crm_g5_chay": [{"lap_lai": True, "ket_qua": dict(ACK)}]})
        h = _H("/api/crm/giao-ket/doi-chieu/chay", _than())
        CG.dieu_huong(h, _App(DC.CrmDoiChieuK2(T._Kiem(conn)), _HD()), True, "/api/crm/giao-ket/doi-chieu/chay", {})
        self.assertEqual((h.st, h.data["replay"], h.data["job_id"]), (200, True, T.VIEC))

    def test_ngu_canh_sai_dang_truoc_sql(self):
        conn = T._Conn({})
        for ctx in ("", "C" * 64, "c" * 63, None, 1):
            h = _H("/api/crm/giao-ket/doi-chieu/chay", _than(expected_context_sha256=ctx))
            CG.dieu_huong(h, _App(DC.CrmDoiChieuK2(T._Kiem(conn)), _HD()), True, "/api/crm/giao-ket/doi-chieu/chay", {})
            self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"), ctx)
        self.assertEqual(conn.goi, [])

    def test_doc_tham_so_sql(self):
        view = {"kieu": "CRM_G5_VIEW_V1", "ky_id": KY}
        conn = T._Conn({"crm_g5_doc": [view]})
        h = _H("/api/crm/giao-ket/doi-chieu/" + KY)
        CG.dieu_huong(h, _App(DC.CrmDoiChieuK2(T._Kiem(conn)), _HD()), False, "/api/crm/giao-ket/doi-chieu/" + KY, {})
        self.assertEqual((h.st, h.data), (200, view))
        self.assertEqual(conn.goi, [("crm_g5_doc", (KY,), ME)])


def _ham(ten: str) -> str:
    """Thân một hàm trong CRM_G5_SQL (chuỗi — không chạy SQL)."""
    i = SQL_TXT.index(f"FUNCTION master.{ten}(")
    j = SQL_TXT.find("CREATE OR REPLACE FUNCTION", i + 10)
    return SQL_TXT[i:j if j > 0 else len(SQL_TXT)]


class GoldenView(unittest.TestCase):
    def _co(self, than, khoa):
        thieu = sorted(k for k in khoa if f"'{k}'" not in than)
        self.assertEqual(thieu, [])

    def test_view_khoa_trong_sql(self):
        doc = _ham("crm_g5_doc")
        for bo in (VIEW_KHOA, JOB_KHOA, KQ_KHOA, TS_KHOA, LS_KHOA, {"trang_thai", "ly_do", "la_bang_chung"}, {"chay", "doi_soat"}, {"san_sang"}):
            self._co(doc, bo)
        self.assertIn("'CRM_G5_VIEW_V1'", doc)
        self.assertIn("'la_bang_chung', false", doc)  # khởi tạo G4 KHÔNG là bằng chứng
        self.assertIn("crm_kiem_g5_xet(p_ky, 'VAN_HANH')", doc)  # G6 trên màn hình luôn VAN_HANH

    def test_ack_khoa_trong_sql(self):
        ack = _ham("crm_g5_ack")
        self._co(ack, ACK_SQL_KHOA)
        self.assertIn("'tao_moi', v_moi", _ham("crm_g5_chay"))
        self.assertIn("'tao_moi', false", _ham("crm_g5_doi_soat"))
        self.assertIn('"replay": bool(r["lap_lai"])', open(DC.__file__, encoding="utf-8").read())

    def test_view_khong_lo_tham_quyen(self):
        doc = _ham("crm_g5_doc")
        m = re.search(r"RETURN jsonb_build_object\(\s*'kieu', 'CRM_G5_VIEW_V1'(.*)\$\$", doc, re.S)
        self.assertIsNotNone(m)
        for k in ("'implementation_sha256'", "'mapping_sha256'", "'nguoi_chay'", "'lease_boi'", "'raw_sha256'", "'body'"):
            self.assertNotIn(k, m.group(1))


if __name__ == "__main__":
    unittest.main()
