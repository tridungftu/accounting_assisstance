"""CRM-41-06A (G6A) — kiểm HTTP: dispatcher (thuần, handler giả) + luồng thật trên LocalApp/LocalServer với bản sao DEMO SỞ HỮU
(CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

Tầng 1 (không CSDL): route G6A không nhận query/trường quyền/chế độ G5; DTO khách dự thảo NULL/NULL đi nguyên tới tham số SQL; ánh xạ mã → HTTP;
  factory HTTP luôn VAN_HANH; tải tệp có Content-Disposition + no-store.
Tầng 2 (PG thật): CHỈ trên bản sao DEMO sở hữu do người gọi cấp qua cổng ``test_crm_kiem_hd.cong_clone`` (owner DSN + DSN login ứng dụng thường,
  provenance, registry 1–25 + checksum, marker DEMO, quyền hiện hành). Thiếu/thiếu một phần → FAIL ``NOT_VERIFIED`` (không skip). Không tạo
  DB/vai, không SET ROLE, không seed/bootstrap/M9, không tạo mã Junsky/đối tác (chỉ đọc mã CÓ SẴN của seed DEMO). Mẫu/báo giá/soạn/xuất/ký qua
  LUỒNG DỊCH VỤ THẬT (helper G2/G3 mượn từ tests/test_crm_giao_ket_http.py); phân công + phạm vi do CHỦ CSDL khai (vai quản trị).
  G4 cần bản xuất G3 PDF_DAT THẬT (Word) + pypdfium2 — thiếu → FAIL NOT_VERIFIED (Word/GUI vẫn OPEN).
  G5: HTTP luôn VAN_HANH → HOLD UNREGISTERED_G5_PROOF. Ca kích hoạt dương dùng SYNTHETIC_FIXTURE dựng TRỰC TIẾP trong test (GUC giao dịch trên
  kết nối chủ bảng + nguồn phi_van_hanh) — KHÔNG phải bằng chứng vận hành/nghiệm thu; trình duyệt/HTTP không chọn được.

Ánh xạ nghiệm thu: P1-A → n05/n09 · P1-B → n02/n03/n04/n06 (+ tests/crm_kiem_hd_async.cjs H10 cho UI) · kích hoạt + F6/F7 → n07/n08.
Không DROP/DELETE/cleanup — dữ liệu trên bản sao giữ làm bằng chứng. Full CRM acceptance vẫn OPEN tới khi Root có biên nhận độc lập.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

import test_crm_giao_ket_http as GKH  # chỉ mượn helper (không đưa lớp TestCase của file đó vào module này)
import test_crm_kiem_hd as TK
from test_crm_giao_ket import _co_word
from test_crm_ky_ket import pdf_tong_hop

from kho_tri_thuc.giao_dien import crm_g as CG
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_kiem_hd as KH

TAI, KT, CFO, BH = GKH.TAI, GKH.KT, GKH.CFO, GKH.BH
KT_NO_CRM, CFO_B = GKH.KT_NO_CRM, GKH.CFO_B
KT_M1 = "MO_PHONG_KT_A"  # crm_demo: KE_TOAN + CRM + M1 trên PN A (quyền LIEN_KET_TIEN của F7)
ngay = GKH.ngay
KY = TK.KY
CL_DU = TK.CL_DU


# ---------------------------------------------------------------------------------------------------------------- 1. dispatcher (thuần)
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


class _Kiem:
    """Service giả: ghi lại mọi lời gọi (để chứng minh từ chối xảy ra TRƯỚC service)."""
    TEN = ("ds", "doc", "tep", "luu", "check", "xu_ly_lech", "bo_sung", "hieu_luc", "tra_lai", "tim_junsky")

    def __init__(self, loi=None):
        self.goi, self.loi = [], loi

    def __getattr__(self, ten):
        if ten not in _Kiem.TEN:
            raise AttributeError(ten)

        def f(*a, **kw):
            self.goi.append((ten, a, kw))
            if self.loi is not None:
                raise self.loi
            if ten == "tep":
                return "H__01-r2-ban-ky.pdf", b"%PDF-1.7 gia", "application/pdf"
            return [] if ten == "ds" else {"ten": ten}
        return f


class _App:
    def __init__(self, kiem, me=KT):
        self.mutation_lock, self.me = threading.Lock(), me
        self.__dict__["_crm_kiem"] = kiem

    def crm_phien(self, sid, *, tao=False):
        return sid, self.me, False

    @staticmethod
    def _crm_db(fn, *a):
        return fn(*a)


def _than_luu(**sua):
    d = {"ky_id": KY, "expected_revision": 0, "checklist": dict(CL_DU), "doi_tac_id": None, "ma_junsky_id": None, "ngay_hieu_luc": None,
         "can_cu_ngay": None, "trich_dan_ngay": None, "ghi_chu": None, "khoa": "k-1"}
    d.update(sua)
    return d


class DieuHuongKiem(unittest.TestCase):
    def chay(self, post, path, body=None, query=None, kiem=None, raw_path=None, me=KT):
        kiem = _Kiem() if kiem is None else kiem
        h = _H(raw_path or path, body)
        CG.dieu_huong(h, _App(kiem, me), post, path, query or {})
        return h, kiem

    def test_khong_nhan_che_do_g5_va_ket_qua_tu_trinh_duyet(self):
        for k in sorted(CG.KHONG_NHAN_KIEM):
            for ten in ("luu", "check", "hieu-luc", "tim-junsky"):
                h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/" + ten, {"ky_id": KY, k: "SYNTHETIC_FIXTURE"})
                self.assertEqual((h.st, h.data["error"]), (403, "CRM_G_CLIENT_AUTHORITY"), (ten, k))
                self.assertEqual(kiem.goi, [])

    def test_truong_quyen_va_truong_la(self):
        for k in ("actor", "phap_nhan_id", "trang_thai", "viec_id", "ket_qua"):
            h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(**{k: "x"}))
            self.assertEqual((h.st, h.data["error"]), (403, "CRM_G_CLIENT_AUTHORITY"), k)
            self.assertEqual(kiem.goi, [])
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/tim-junsky", {"ky_id": KY, "tu_khoa": "KH_DEMO", "pn": "A"})
        self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"))
        self.assertEqual(kiem.goi, [])
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/check", [KY])
        self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"))
        self.assertEqual(kiem.goi, [])

    def test_khong_nhan_query(self):
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(), query={"che_do": ["SYNTHETIC_FIXTURE"]})
        self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"))
        h, kiem2 = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(), raw_path="/api/crm/giao-ket/kiem/luu?x")
        self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"))
        for p in ("/api/crm/giao-ket/kiem", f"/api/crm/giao-ket/kiem/{KY}", f"/api/crm/giao-ket/kiem/{KY}/tep/ban-ky"):
            h, kiem3 = self.chay(False, p, query={"a": ["1"]})
            self.assertEqual((h.st, h.data["error"]), (400, "CRM_G_YEU_CAU_SAI"), p)
            self.assertEqual(kiem3.goi, [])
        self.assertEqual(kiem.goi + kiem2.goi, [])

    def test_dto_khach_du_thao_null_null_toi_service(self):
        """P1-B NULL-ID DTO: khách dự thảo gửi doi_tac_id/ma_junsky_id null → service nhận đúng None/None, danh tính từ phiên."""
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(), me=KT)
        self.assertEqual(h.st, 200, h.data)
        (ten, a, kw), = kiem.goi
        self.assertEqual((ten, a), ("luu", (KT,)))
        self.assertEqual((kw["doi_tac_id"], kw["ma_junsky_id"], kw["expected_revision"]), (None, None, 0))
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/tim-junsky", {"ky_id": KY, "tu_khoa": "KH_DEMO"})
        self.assertEqual(kiem.goi, [("tim_junsky", (KT, KY, "KH_DEMO"), {})])

    def test_dto_null_null_tham_so_sql_that(self):
        """Dispatcher + service THẬT (kết nối giả): NULL/NULL và chuỗi rỗng → tham số SQL None/None; cặp lệch một phía → 400 trước SQL."""
        for dt, mj in ((None, None), ("", "")):
            c = TK._Conn()
            h, _ = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(doi_tac_id=dt, ma_junsky_id=mj), kiem=KH.CrmKiemHdK2(TK._FakeKy(c)))
            self.assertEqual(h.st, 200, h.data)
            self.assertEqual(h.data, {"ho_so_id": "x", "lap_lai": False})
            (sql, p), = c.calls
            self.assertIn("master.crm_kiem_luu(", sql)
            self.assertEqual((p[5], p[6]), (None, None))
        c = TK._Conn()
        h, _ = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(doi_tac_id=TK.DT), kiem=KH.CrmKiemHdK2(TK._FakeKy(c)))
        self.assertEqual((h.st, h.data["error"], c.calls), (400, "CRM_KIEM_JUNSKY_SAI", []))
        c = TK._Conn()
        h, _ = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(doi_tac_id=TK.DT, ma_junsky_id=TK.MJ), kiem=KH.CrmKiemHdK2(TK._FakeKy(c)))
        self.assertEqual(h.st, 200)
        self.assertEqual((c.calls[0][1][5], c.calls[0][1][6]), (TK.DT, TK.MJ))

    def test_anh_xa_ma_loi(self):
        for ma, st in (("CRM_KIEM_CHUA_CO_PHAM_VI", 403), ("CRM_G_KHONG_CO_QUYEN", 403), ("CRM_G_CUNG_NGUOI", 403), ("CRM_G_KHONG_THAY", 404),
                       ("CRM_KIEM_KHACH_DA_DINH", 409), ("CRM_KIEM_DA_HIEU_LUC", 409), ("CRM_KIEM_CHUA_DU_DIEU_KIEN", 409),
                       ("CRM_KIEM_REVISION_CU", 409), ("CRM_KIEM_CHECK_CU", 409), ("CRM_KIEM_JUNSKY_SAI", 400), ("CRM_KIEM_CHECKLIST_SAI", 400),
                       ("CRM_G_TEP_KHONG_CO", 404), ("CRM_G_TEP_HONG", 409)):
            h, _ = self.chay(True, "/api/crm/giao-ket/kiem/luu", _than_luu(), kiem=_Kiem(DataError(ma, "x")))
            self.assertEqual((h.st, h.data["error"]), (st, ma), ma)

    def test_get_danh_sach_doc_tep(self):
        h, _ = self.chay(False, "/api/crm/giao-ket/kiem")
        self.assertEqual((h.st, h.data), (200, {"ds": [], "nguoi": {"dang_nhap": KT}}))
        h, kiem = self.chay(False, f"/api/crm/giao-ket/kiem/{KY}")
        self.assertEqual((h.st, kiem.goi), (200, [("doc", (KT, KY), {})]))
        h, kiem = self.chay(False, f"/api/crm/giao-ket/kiem/{KY}/tep/g3")
        self.assertEqual((h.st, h.data, h.mime), (200, b"%PDF-1.7 gia", "application/pdf"))
        self.assertEqual(h.hd, {"Content-Disposition": "attachment; filename*=UTF-8''H__01-r2-ban-ky.pdf", "Cache-Control": "no-store"})
        self.assertEqual(kiem.goi, [("tep", (KT, KY, "g3"), {})])
        for p in (f"/api/crm/giao-ket/kiem/{KY}/tep/docx", "/api/crm/giao-ket/kiem/khong-uuid"):
            h, kiem = self.chay(False, p)
            self.assertEqual((h.st, h.data["error"], kiem.goi), (404, "NOT_FOUND", []), p)
        h, kiem = self.chay(True, "/api/crm/giao-ket/kiem/xoa", {"ky_id": KY})
        self.assertEqual((h.st, kiem.goi), (404, []))

    def test_factory_http_luon_van_hanh(self):
        class _Ky:
            mau = object()
        app = type("A", (), {})()
        app.__dict__["_crm_ky"] = _Ky()
        s = CG.dich_vu_kiem(app)
        self.assertEqual(s.g5_che_do, "VAN_HANH")
        self.assertIs(CG.dich_vu_kiem(app), s)


# ---------------------------------------------------------------------------------------------------------------- 2. PG thật — bản sao DEMO sở hữu
LICH = [{"lan": "1", "loai": "PERCENT", "ty_le": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
        {"lan": "2", "loai": "PERCENT", "ty_le": "60", "moc_loai": "NGAY", "moc_ngay": ngay(60)}]  # mốc NGAY: lich_thu có hạn
TRICH_DAN = "Điều 2 (DEMO): hợp đồng có hiệu lực từ ngày ký"


class CrmKiemHttpBanSao(unittest.TestCase):
    """Chạy theo thứ tự n00…n09 trên MỘT bản sao/một máy chủ; trạng thái qua cls.s. Bước trước thiếu → bước sau FAIL NOT_VERIFIED."""

    _G = GKH.CrmGiaoKetHttp
    goi, sid, K, ok, loi, get, q, loai_a, du_an = _G.goi, _G.sid, _G.K, _G.ok, _G.loi, _G.get, _G.q, _G.loai_a, _G.du_an
    mau_hieu_luc, bao_gia = _G.mau_hieu_luc, _G.bao_gia
    khoa_may, _dung, _dong_ket_noi_app = _G.__dict__["khoa_may"], _G.__dict__["_dung"], _G.__dict__["_dong_ket_noi_app"]
    del _G

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.ly_do = TK.cong_clone(can_ghi=True)
        if not cls.ctx:
            return
        cls.addClassCleanup(TK._dong, cls.ctx["owner"], cls.ctx["app"])
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        cls.admin = cls.ctx["owner"]
        env = {LocalApp.CRM_ENV: os.environ[TK.ENV_APP], LocalApp.CRM_ENV_ADMIN: os.environ[TK.ENV_OWNER]}
        if cls.ctx["kiem_thu"]:
            env[LocalApp.CRM_ENV_DB_KIEM_THU] = "1"
        cls.env = patch.dict(os.environ, env)
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crm_g6a_http_"))  # giữ lại
        (cls.tam / "cau_hinh_fixture.toml").write_text(GKH.CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(cls.tam / "cau_hinh_fixture.toml", cls.tam / "web")
        cls.addClassCleanup(cls._dong_ket_noi_app)
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung)
        cls.run_id = uuid.uuid4().hex[:8]
        cls.co_word = _co_word()
        cls.s = {}

    def setUp(self):
        if not self.ctx:
            self.fail("NOT_VERIFIED: " + self.ly_do)

    def can(self, *khoa):
        thieu = [k for k in khoa if k not in self.s]
        if thieu:
            self.fail("NOT_VERIFIED: bước chuẩn bị trước chưa đạt (thiếu " + ", ".join(thieu) + ")")

    # ------------------------------------------------------------------ helpers
    def kiem(self, login, ten, body):
        st, r, _ = self.goi("/api/crm/giao-ket/kiem/" + ten, body, self.sid(login))
        return st, r

    def kiem_loi(self, login, ten, body, status, ma):
        st, r = self.kiem(login, ten, body)
        self.assertEqual((st, r.get("error") if isinstance(r, dict) else r), (status, ma), (login, ten))
        return r

    def tai_tep(self, login, ky, loai):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=120)
        c.request("GET", f"/api/crm/giao-ket/kiem/{ky}/tep/{loai}",
                  headers={"X-KTT-Token": self.app.token, "Cookie": f"{self.app.CRM_COOKIE}={self.sid(login)}"})
        r = c.getresponse()
        out, hd = r.read(), {k.lower(): v for k, v in r.getheaders()}
        c.close()
        return r.status, out, hd

    def ma(self, pn_ma, *, con_hieu_luc=True, tru=()):
        """Mã Junsky CÓ SẴN của seed DEMO (chỉ đọc; không tạo). Trả dict id/doi_tac_id/object hoặc None."""
        r = self.admin.execute("""SELECT j.id::text, j.doi_tac_id::text, j.object_id_junsky FROM master.doi_tac_ma_junsky j
                                  JOIN master.phap_nhan p ON p.id = j.phap_nhan_id
                                  WHERE p.ma = %s AND (CASE WHEN %s THEN j.valid_to IS NULL AND NOT j.dong ELSE j.valid_to IS NOT NULL OR j.dong END)
                                    AND NOT (j.doi_tac_id::text = ANY(%s::text[]))
                                  ORDER BY j.object_id_junsky, j.id LIMIT 1""", (pn_ma, con_hieu_luc, list(tru))).fetchone()
        return None if r is None else {"id": r[0], "doi_tac_id": r[1], "object": r[2]}

    def phan_cong(self, login, hanh, soan):
        """Chủ CSDL khai phân công (dùng lại phân công hiện hành nếu có). Trả (id, đã có sẵn?)."""
        r = self.admin.execute("""SELECT a.id::text FROM master.phan_cong_hanh_dong a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
                                  JOIN master.crm_hd_soan s ON s.id = %s
                                  WHERE n.dang_nhap = %s AND a.hanh_dong = %s AND a.module = 'CRM' AND a.phap_nhan_id = s.phap_nhan_id
                                    AND a.thu_hoi_luc IS NULL AND (a.loai_hinh_id IS NULL OR a.loai_hinh_id = s.loai_hinh_id)
                                  ORDER BY a.id LIMIT 1""", (soan, login, hanh)).fetchone()
        if r:
            return r[0], True
        return str(self.q("""INSERT INTO master.phan_cong_hanh_dong (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id, cap_boi)
                             SELECT n.id, s.phap_nhan_id, 'CRM', %s, s.loai_hinh_id, 'TEST:CRM-41-06A'
                             FROM master.nguoi_dung n, master.crm_hd_soan s WHERE n.dang_nhap = %s AND s.id = %s RETURNING id""",
                          (hanh, login, soan))), False

    def pham_vi_ky(self, pc, soan):
        """Phạm vi ký G4 (chủ CSDL): khách dự thảo → digest du_thao; khách định danh → doi_tac_id của revision hiện hành."""
        return str(self.q("""INSERT INTO master.crm_ky_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, du_an_id, doi_tac_id,
                                                                khach_du_thao_sha256, cap_boi)
                             SELECT %s, s.phap_nhan_id, s.hop_dong_id, s.id, h.du_an_id,
                                    (r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id')::uuid,
                                    CASE WHEN r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id' IS NULL
                                         THEN encode(sha256(convert_to((r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao')::text, 'UTF8')), 'hex') END,
                                    'TEST:CRM-41-06A'
                             FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id
                             JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
                             WHERE s.id = %s RETURNING id""", (pc, soan)))

    def pham_vi_kiem(self, pc, ky):
        """Phạm vi kiểm G6A (chủ CSDL): đúng bản ký/HĐ/dự án hiện hành; trigger từ chối mọi lệch."""
        return str(self.q("""INSERT INTO master.crm_kiem_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, ky_id, du_an_id, cap_boi)
                             SELECT %s, k.phap_nhan_id, k.hop_dong_id, k.id, h.du_an_id, 'TEST:CRM-41-06A'
                             FROM master.crm_hd_ky k JOIN master.hop_dong h ON h.id = k.hop_dong_id WHERE k.id = %s RETURNING id""", (pc, ky)))

    def thu_hoi(self, bang, id_):
        self.admin.execute(f"UPDATE master.{bang} SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST', thu_hoi_ly_do = 'TEST thu hồi' WHERE id = %s", (id_,))

    def dem_kiem(self, ky):
        return tuple(self.q(f"SELECT count(*) FROM master.{t} WHERE ky_id = %s", (ky,))
                     for t in ("crm_kiem_ho_so", "crm_kiem_rev", "crm_kiem_check", "crm_kiem_quyet_dinh", "crm_kiem_hieu_luc"))

    def khach_ky(self, ky):
        """Danh tính khách TRÊN BẢN KÝ G4 (revision đã ký) + đối tác HĐ master."""
        return tuple(self.admin.execute("""SELECT r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id', h.doi_tac_id::text, k.ky_pdf_sha256
                                           FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id
                                           JOIN master.hop_dong h ON h.id = k.hop_dong_id WHERE k.id = %s""", (ky,)).fetchone())

    def viec_thay(self, login, viec_id):
        """P1-A: đếm việc K5 mà LOGIN ỨNG DỤNG THƯỜNG (không chủ bảng/SET ROLE) thấy dưới danh tính phiên `login`."""
        from kho_tri_thuc.k2 import quyen
        a = self.ctx["app"]
        dt = quyen.nap_danh_tinh(a, login, chi_mo_phong=True)
        with a.transaction():
            a.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                      "set_config('ktt.ngay_hieu_luc', %s, true)", (str(dt["id"]), dt["dang_nhap"], ngay(0)))
            if viec_id is None:
                return {str(r["id"]) for r in a.execute("""SELECT id FROM kho.viec_can_duyet
                                                           WHERE tham_chieu_bang NOT IN ('master.crm_kiem_ho_so','master.crm_kiem_hieu_luc')""")}
            return a.execute("SELECT count(*) AS n FROM kho.viec_can_duyet WHERE id = %s", (viec_id,)).fetchone()["n"]

    def k5_khac(self):
        return {str(r[0]): (r[1], str(r[2])) for r in self.admin.execute(
            """SELECT id, trang_thai, cap_nhat_luc FROM kho.viec_can_duyet
               WHERE tham_chieu_bang NOT IN ('master.crm_kiem_ho_so','master.crm_kiem_hieu_luc')""").fetchall()}

    def dung_hop_dong(self, tag, khach):
        """Báo giá → soạn → xuất G3 (PDF_DAT THẬT) → G4 ký lần đầu (BH) qua HTTP. Không PDF_DAT/pypdfium2 → FAIL NOT_VERIFIED."""
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("bg-" + tag),
                                        "du_lieu": self.bao_gia(don_vi={"ma": f"LO-G6A-{tag}-{self.run_id}"}, khach=khach, lich=LICH)})
        a = self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": self.s["pb"],
                                           "khoa": self.K("cv-" + tag)})
        soan = a["soan_id"]
        bg = dict(self.get(BH, "soan/" + soan)["du_lieu"]["bao_gia"])
        bg["fx"] = None
        gt = {"so_hop_dong": f"HĐ-DEMO-G6A-{tag}-{self.run_id}", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(BH, "soan/luu", {"soan_id": soan, "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-" + tag)})
        x = self.ok(BH, "soan/xuat", {"soan_id": soan, "expected_revision": 2, "khoa": self.K("x-" + tag)})
        row = self.admin.execute("SELECT trang_thai, pdf_sha256, pdf_len FROM master.crm_gk_xuat WHERE id = %s", (x["xuat_id"],)).fetchone()
        if x.get("trang_thai") != "PDF_DAT" or row is None or row[0] != "PDF_DAT":
            self.fail(f"NOT_VERIFIED: chưa có bản xuất G3 PDF_DAT thật (trạng thái {x.get('trang_thai')}; probe Word={self.co_word}) — "
                      "không owner-forge PDF_DAT")
        st, g3, _ = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/pdf", cookie=self.sid(BH))
        self.assertEqual((st, hashlib.sha256(g3).hexdigest(), len(g3)), (200, row[1], row[2]))
        pc, _ = self.phan_cong(BH, "CRM_KY_KET", soan)
        self.pham_vi_ky(pc, soan)
        raw = pdf_tong_hop(1, f"BAN KY G6A {tag}")
        info = {"soan_id": soan, "expected_revision": 2, "expected_xuat_id": x["xuat_id"], "ten_tep": "ban-da-ky.pdf", "ngay_ky": ngay(0),
                "co_sua": False, "khoa": self.K("ky-" + tag)}
        st, k, _ = self.goi("/api/crm/giao-ket/ky-ket", cookie=self.sid(BH), raw=raw,
                            headers={"X-CRM-G-Info": quote(json.dumps(info, ensure_ascii=False)), "Content-Type": "application/pdf"})
        self.assertEqual(st, 200, k)
        self.assertEqual(k["g5"], {"trang_thai": "NOT_SELECTED", "ly_do": "CHUA_AP_DUNG_CHON_MAU"})  # khởi tạo G4 — KHÔNG là bằng chứng G5
        return {"soan": soan, "hd": a["hop_dong_id"], "ky": k["ky_id"], "raw": raw, "g3": g3}

    # ------------------------------------------------------------------ n00: chuẩn bị (mã có sẵn, mẫu, hai HĐ đã ký)
    def test_n00_chuan_bi(self):
        try:
            import pypdfium2  # noqa: F401
        except ImportError:
            self.fail("NOT_VERIFIED: máy chủ thiếu pypdfium2 — G4 fail closed, không có bản ký để kiểm")
        self.s["k5_truoc"] = self.k5_khac()
        self.s["k5_kt_truoc"] = self.viec_thay(KT, None)
        a1 = self.ma("PN_DEMO_A")
        a2 = a1 and self.ma("PN_DEMO_A", tru=(a1["doi_tac_id"],))
        b1 = self.ma("PN_DEMO_B")
        dong = self.ma("PN_DEMO_A", con_hieu_luc=False)
        if not (a1 and a2 and b1 and dong):
            self.fail("NOT_VERIFIED: seed DEMO thiếu mã Junsky cần cho ca P1-B (2 đối tác hiệu lực PN A, 1 mã PN B, 1 mã đã đóng/hết hiệu lực PN A) "
                      "— không tự tạo mã")
        self.s.update(a1=a1, a2=a2, b1=b1, dong=dong)
        self.s["pb"], _ = self.mau_hieu_luc("HD_G6A_" + self.run_id, ngay(-2), "MAU G6A")
        self.s["D"] = self.dung_hop_dong("d", {"du_thao": {"ten": "KHÁCH DỰ THẢO DEMO G6A"}})
        self.s["I"] = self.dung_hop_dong("i", {"doi_tac_id": a1["doi_tac_id"]})
        self.assertEqual(self.khach_ky(self.s["D"]["ky"])[:2], (None, None))  # khách dự thảo: bản ký + HĐ đều NULL
        self.assertEqual(self.khach_ky(self.s["I"]["ky"])[0], a1["doi_tac_id"])

    # ------------------------------------------------------------------ n01: quyền/phạm vi hiện hành trước mọi đọc/ghi
    def test_n01_quyen_truoc_pham_vi(self):
        self.can("D", "I")
        D, I = self.s["D"], self.s["I"]
        trc = self.dem_kiem(D["ky"])
        for login in (KT_NO_CRM, CFO_B, BH, TAI):  # ngoài PN/module/vai KT → 404 ẩn (kể cả người ghi bản ký)
            self.get(login, "giao-ket/kiem/" + D["ky"], status=404)
            self.kiem_loi(login, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": self.s["a1"]["object"]}, 404, "CRM_G_KHONG_THAY")
        pc, co_san = self.phan_cong(KT, "CRM_HD_KIEM", D["soan"]) if True else (None, None)
        if not co_san:
            self.fail("NOT_VERIFIED: vừa khai phân công CRM_HD_KIEM — chạy lại cả lớp để ca 'thiếu phân công' đo trước khi khai")  # pragma: no cover
        self.s["pc_kt"] = pc
        self.get(KT, "giao-ket/kiem/" + D["ky"], status=403)  # vai + phân công nhưng CHƯA có phạm vi: không suy từ vai/người tạo
        self.kiem_loi(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": self.s["a1"]["object"]}, 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], khoa=self.K("luu-chua-pv")), 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        st, _, _ = self.tai_tep(KT, D["ky"], "ban-ky")
        self.assertEqual(st, 403)
        self.assertNotIn(D["ky"], [x["ky_id"] for x in self.get(KT, "giao-ket/kiem")["ds"]])
        self.s["pv_d"] = self.pham_vi_kiem(pc, D["ky"])
        self.s["pv_i"] = self.pham_vi_kiem(pc, I["ky"])
        self.assertIn(D["ky"], [x["ky_id"] for x in self.get(KT, "giao-ket/kiem")["ds"]])
        self.assertEqual(self.dem_kiem(D["ky"]), trc)

    # ------------------------------------------------------------------ n02 (P1-B): tra mã CÓ SẴN cho khách dự thảo
    def test_n02_tim_junsky_khach_du_thao(self):
        self.can("pv_d")
        D, a1, b1 = self.s["D"], self.s["a1"], self.s["b1"]
        d = self.get(KT, "giao-ket/kiem/" + D["ky"])
        self.assertEqual((d["khach_du_thao"], d["ma_junsky_ung_vien"], d["rev"], d["g5_che_do"]), (True, [], None, "VAN_HANH"))
        self.assertEqual(d["hop_dong"]["doi_tac_id"], None)
        self.kiem_loi(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": "ab"}, 400, "CRM_G_YEU_CAU_SAI")
        self.kiem_loi(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": "KH_DEMO", "phap_nhan_id": "x"}, 403, "CRM_G_CLIENT_AUTHORITY")
        st, r = self.kiem(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": a1["object"]})
        self.assertEqual(st, 200, r)
        self.assertLessEqual(len(r["ung_vien"]), r["gioi_han"])
        hit = [u for u in r["ung_vien"] if u["id"] == a1["id"]]
        self.assertEqual(len(hit), 1, r)
        self.assertEqual((hit[0]["doi_tac_id"], hit[0]["khop_ma"], hit[0]["object_id"]), (a1["doi_tac_id"], True, a1["object"]))
        st, r = self.kiem(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": b1["object"]})  # mã PN khác: không lộ
        self.assertEqual(st, 200, r)
        self.assertNotIn(b1["id"], [u["id"] for u in r["ung_vien"]])
        nk = self.admin.execute("""SELECT sau FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KIEM_TIM_JUNSKY' AND doi_tuong_id = %s AND nguoi = %s
                                   ORDER BY id DESC LIMIT 1""", (D["ky"], KT)).fetchone()
        self.assertIsNotNone(nk, "tra cứu phải có nhật ký truy cập")
        self.assertIn("tu_khoa_sha256", nk[0])
        self.assertNotIn(b1["object"], json.dumps(nk[0], ensure_ascii=False))  # nhật ký không ghi từ khóa thô
        self.assertEqual(self.dem_kiem(D["ky"]), (0, 0, 0, 0, 0))  # tra cứu không ghi nghiệp vụ

    # ------------------------------------------------------------------ n03 (P1-B): từ chối mã sai PN / đóng / lệch cặp / một phía
    def test_n03_luu_tu_choi_ma_sai(self):
        self.can("pv_d")
        D, a1, a2, b1, dong = (self.s[k] for k in ("D", "a1", "a2", "b1", "dong"))
        for i, (dt, mj) in enumerate(((b1["doi_tac_id"], b1["id"]), (a2["doi_tac_id"], a1["id"]), (dong["doi_tac_id"], dong["id"]),
                                      (a1["doi_tac_id"], str(uuid.uuid4())))):
            self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], doi_tac_id=dt, ma_junsky_id=mj, khoa=self.K(f"luu-sai-{i}")), 400, "CRM_KIEM_JUNSKY_SAI")
        self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], doi_tac_id=a1["doi_tac_id"], khoa=self.K("luu-mot-phia")), 400, "CRM_KIEM_JUNSKY_SAI")
        self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], ma_junsky_id=a1["id"], khoa=self.K("luu-mot-phia-2")), 400, "CRM_KIEM_JUNSKY_SAI")
        self.assertEqual(self.dem_kiem(D["ky"]), (0, 0, 0, 0, 0))  # giao dịch lỗi: không hồ sơ/revision nào
        self.assertEqual(self.khach_ky(D["ky"])[:2], (None, None))

    # ------------------------------------------------------------------ n04 (P1-B): NULL/NULL → chọn cặp có sẵn → lưu đúng cặp; G5 vận hành HOLD
    def test_n04_luu_cap_cho_khach_du_thao_va_g5_hold(self):
        self.can("pv_d")
        D, a1 = self.s["D"], self.s["a1"]
        ngay_hl = {"ngay_hieu_luc": ngay(0), "can_cu_ngay": "DIEU_KHOAN_HD", "trich_dan_ngay": TRICH_DAN}
        r1 = self.ok(KT, "giao-ket/kiem/luu", _than_luu(ky_id=D["ky"], khoa=self.K("luu-1"), **ngay_hl))  # DTO NULL/NULL thật
        self.assertEqual((r1["revision"], r1["trang_thai"], r1["lap_lai"]), (1, "DANG_KIEM", False))
        self.s["viec_d"] = r1["viec_id"]
        c1 = self.ok(KT, "giao-ket/kiem/check", {"ky_id": D["ky"], "expected_revision": 1, "khoa": self.K("check-1")})
        ma1 = {x["ma"] for x in c1["check"]["chan"]}
        self.assertTrue({"THIEU_KHACH_JUNSKY", "UNREGISTERED_G5_PROOF"} <= ma1, ma1)
        r2 = self.ok(KT, "giao-ket/kiem/luu", _than_luu(ky_id=D["ky"], expected_revision=1, doi_tac_id=a1["doi_tac_id"], ma_junsky_id=a1["id"],
                                                        khoa=self.K("luu-2"), **ngay_hl))
        self.assertEqual(r2["revision"], 2)
        r2b = self.ok(KT, "giao-ket/kiem/luu", _than_luu(ky_id=D["ky"], expected_revision=1, doi_tac_id=a1["doi_tac_id"], ma_junsky_id=a1["id"],
                                                         khoa=self.K("luu-2"), **ngay_hl))
        self.assertEqual((r2b["revision"], r2b["lap_lai"]), (2, True))  # cùng khóa + cùng thân: biên nhận cũ, 0 hàng mới
        self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], expected_revision=1, khoa=self.K("luu-2"), **ngay_hl), 409, "CRM_G_IDEMPOTENCY_KHAC")
        self.kiem_loi(KT, "luu", _than_luu(ky_id=D["ky"], expected_revision=1, khoa=self.K("luu-cu"), **ngay_hl), 409, "CRM_KIEM_REVISION_CU")
        d = self.get(KT, "giao-ket/kiem/" + D["ky"])
        self.assertEqual((d["rev"]["revision"], d["rev"]["de_xuat_doi_tac_id"], d["rev"]["de_xuat_ma_junsky_id"]), (2, a1["doi_tac_id"], a1["id"]))
        if len(a1["object"]) > 4:
            self.assertNotEqual(d["rev"]["ma_junsky"], a1["object"])  # PII che
        self.assertIn(a1["id"], [u["id"] for u in d["ma_junsky_ung_vien"]])
        nk = self.admin.execute("""SELECT sau FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KIEM_LUU' AND doi_tuong_id = %s ORDER BY id""",
                                (r1["ho_so_id"],)).fetchall()
        self.assertEqual([x[0]["revision"] for x in nk], [1, 2])  # audit từng revision
        self.assertEqual(self.khach_ky(D["ky"])[:2], (None, None))  # bản ký G4 + HĐ master KHÔNG bị ghi đè trước kích hoạt
        c2 = self.ok(KT, "giao-ket/kiem/check", {"ky_id": D["ky"], "expected_revision": 2, "khoa": self.K("check-2")})
        ma2 = {x["ma"] for x in c2["check"]["chan"]}
        self.assertNotIn("THIEU_KHACH_JUNSKY", ma2)
        self.assertNotIn("JUNSKY_KHONG_HIEU_LUC", ma2)
        self.assertIn("UNREGISTERED_G5_PROOF", ma2)  # G5 vận hành: HOLD (PENDING/NOT_SELECTED không phải bằng chứng)
        self.assertEqual((c2["check"]["ket_luan"], c2["check"]["g5_che_do"]), ("CHUA_DU_DIEU_KIEN", "VAN_HANH"))
        self.assertIn("KHACH_GAN_MA_KHI_KIEM", {x["ma"] for x in c2["check"]["canh_bao"]})
        trc = self.dem_kiem(D["ky"])
        self.kiem_loi(KT, "hieu-luc", {"ky_id": D["ky"], "expected_revision": 2, "check_id": c2["check"]["check_id"],
                                       "do_thi_sha256": c2["check"]["do_thi_sha256"], "khoa": self.K("hl-van-hanh")}, 409, "CRM_KIEM_CHUA_DU_DIEU_KIEN")
        self.kiem_loi(KT, "hieu-luc", {"ky_id": D["ky"], "expected_revision": 2, "check_id": c2["check"]["check_id"], "g5_che_do": "SYNTHETIC_FIXTURE",
                                       "do_thi_sha256": c2["check"]["do_thi_sha256"], "khoa": self.K("hl-ep")}, 403, "CRM_G_CLIENT_AUTHORITY")
        self.assertEqual(self.dem_kiem(D["ky"]), trc)
        self.assertEqual(self.q("SELECT crm_giao_ket FROM master.hop_dong WHERE id = %s", (D["hd"],)), "DA_KY")
        st, raw, hd = self.tai_tep(KT, D["ky"], "ban-ky")  # tải bản ký sau quyền hiện hành + nhật ký
        self.assertEqual((st, raw, hd.get("cache-control")), (200, D["raw"], "no-store"))
        self.assertIn("attachment;", hd.get("content-disposition", ""))
        st, raw, _ = self.tai_tep(KT, D["ky"], "g3")
        self.assertEqual((st, raw), (200, D["g3"]))
        self.assertGreaterEqual(self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KIEM_TAI' AND doi_tuong_id = %s", (D["ky"],)), 2)
        self.s["rev_d"] = 2

    # ------------------------------------------------------------------ n05 (P1-A): K5 đọc bằng login thường theo quyền/phạm vi hiện hành
    def test_n05_k5_doc_thu_hoi_va_ngoai_pham_vi(self):
        self.can("viec_d", "pv_d", "pc_kt")
        D, v = self.s["D"], self.s["viec_d"]
        self.assertEqual(self.viec_thay(KT, v), 1)  # đúng người + phân công + phạm vi
        for login in (CFO, TAI, CFO_B):  # cùng PN không phạm vi / ngoài PN → không thấy (không có đường đọc rộng)
            self.assertEqual(self.viec_thay(login, v), 0, login)
        self.thu_hoi("crm_kiem_pham_vi", self.s["pv_d"])  # thu hồi phạm vi D (phạm vi I vẫn hiện hành)
        self.assertEqual(self.viec_thay(KT, v), 0)  # ngoài chủ thể: phạm vi HĐ khác không mở việc này
        self.get(KT, "giao-ket/kiem/" + D["ky"], status=403)
        self.kiem_loi(KT, "tim-junsky", {"ky_id": D["ky"], "tu_khoa": self.s["a1"]["object"]}, 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        self.kiem_loi(KT, "check", {"ky_id": D["ky"], "expected_revision": 2, "khoa": self.K("check-thu-hoi")}, 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        st, _, _ = self.tai_tep(KT, D["ky"], "ban-ky")
        self.assertEqual(st, 403)
        self.s["pv_d"] = self.pham_vi_kiem(self.s["pc_kt"], D["ky"])  # cấp lại (hàng mới; hàng cũ giữ dấu thu hồi)
        self.assertEqual(self.viec_thay(KT, v), 1)
        with self.assertRaises(psycopg.Error) as cm:  # login thường: hàm lệnh/kích hoạt vẫn không gọi được
            with self.ctx["app"].transaction():
                self.ctx["app"].execute("SELECT master.crm_kiem_luu('k', %s, %s::uuid, 0, '{}'::jsonb, NULL, NULL, NULL, NULL, NULL, NULL)",
                                        ("0" * 64, D["ky"]))
        self.assertIn("permission denied", str(cm.exception))

    # ------------------------------------------------------------------ n06 (P1-B): khách đã định danh không bị thay
    def test_n06_khach_dinh_danh_khong_thay(self):
        self.can("pv_i")
        I, a1, a2 = self.s["I"], self.s["a1"], self.s["a2"]
        self.kiem_loi(KT, "tim-junsky", {"ky_id": I["ky"], "tu_khoa": a2["object"]}, 409, "CRM_KIEM_KHACH_DA_DINH")
        self.kiem_loi(KT, "luu", _than_luu(ky_id=I["ky"], doi_tac_id=a2["doi_tac_id"], ma_junsky_id=a2["id"], khoa=self.K("i-thay")),
                      409, "CRM_KIEM_KHACH_DA_DINH")
        self.assertEqual(self.dem_kiem(I["ky"]), (0, 0, 0, 0, 0))
        d = self.get(KT, "giao-ket/kiem/" + I["ky"])
        self.assertFalse(d["khach_du_thao"])
        r = self.ok(KT, "giao-ket/kiem/luu", _than_luu(ky_id=I["ky"], doi_tac_id=a1["doi_tac_id"], ma_junsky_id=a1["id"], khoa=self.K("i-dung")))
        self.assertEqual(r["revision"], 1)  # cùng đối tác của bản ký: được xác nhận mã có sẵn
        self.assertEqual(self.viec_thay(KT, r["viec_id"]), 1)
        self.assertEqual(self.khach_ky(I["ky"])[0], a1["doi_tac_id"])

    # ------------------------------------------------------------------ n07: SYNTHETIC (phi vận hành) → kích hoạt nguyên tử dùng đúng cặp đã chọn
    def test_n07_synthetic_kich_hoat(self):
        self.can("rev_d", "pv_d")
        from kho_tri_thuc.giao_dien.crm_g import dich_vu_ky
        D, a1 = self.s["D"], self.s["a1"]
        with self.admin.transaction():  # fixture tin cậy: GUC giao dịch trên kết nối CHỦ BẢNG + nguồn phi_van_hanh (không qua HTTP)
            self.admin.execute("SELECT set_config('ktt.crm_kiem_g5', 'SYNTHETIC_FIXTURE', true)")
            ng = self.admin.execute("""INSERT INTO master.crm_kiem_g5_nguon (ma, loai, phi_van_hanh, tao_boi)
                                       VALUES (%s, 'SYNTHETIC_FIXTURE', true, 'TEST:CRM-41-06A') RETURNING id""",
                                    ("SYNTHETIC_G6A_" + self.run_id.upper(),)).fetchone()[0]
            self.admin.execute("""INSERT INTO master.crm_kiem_g5_ket_qua (ky_id, phap_nhan_id, nguon_id, ket_qua, ky_pdf_sha256, g3_pdf_sha256, lech, tao_boi)
                                  SELECT k.id, k.phap_nhan_id, %s, 'KHOP', k.ky_pdf_sha256, k.g3_pdf_sha256, '[]'::jsonb, 'TEST:CRM-41-06A'
                                  FROM master.crm_hd_ky k WHERE k.id = %s""", (ng, D["ky"]))
        c = self.ok(KT, "giao-ket/kiem/check", {"ky_id": D["ky"], "expected_revision": 2, "khoa": self.K("check-sau-syn")})
        self.assertIn("UNREGISTERED_G5_PROOF", {x["ma"] for x in c["check"]["chan"]})  # vận hành vẫn HOLD dù có kết quả tổng hợp
        with self.app.mutation_lock:
            sv = KH.CrmKiemHdK2(dich_vu_ky(self.app), g5_che_do="SYNTHETIC_FIXTURE")
            c = self.app._crm_db(lambda: sv.check(KT, ky_id=D["ky"], expected_revision=2, khoa=self.K("syn-check")))
        self.assertEqual(c["check"]["chan"], [], "SYNTHETIC check còn chặn — không kích hoạt được")
        self.assertEqual((c["check"]["ket_luan"], c["check"]["g5_che_do"]), ("DU_DIEU_KIEN", "SYNTHETIC_FIXTURE"))
        body = dict(ky_id=D["ky"], expected_revision=2, check_id=c["check"]["check_id"], do_thi_sha256=c["check"]["do_thi_sha256"])
        with self.app.mutation_lock:
            hl = self.app._crm_db(lambda: sv.hieu_luc(KT, khoa=self.K("syn-hl"), **body))
        self.assertEqual((hl["trang_thai"], hl["lap_lai"], hl["hieu_luc"]["g5_che_do"]), ("HIEU_LUC", False, "SYNTHETIC_FIXTURE"))
        pb = hl["hieu_luc"]["phien_ban_id"]
        self.s["pb_hl"] = pb
        h = self.admin.execute("SELECT crm_giao_ket, trang_thai, doi_tac_id::text, phien_ban_hien_hanh::text, gia_tri_minor FROM master.hop_dong WHERE id = %s",
                               (D["hd"],)).fetchone()
        self.assertEqual(tuple(h), ("HIEU_LUC", "HIEU_LUC", a1["doi_tac_id"], pb, 1000000000))  # cặp KT chọn → HĐ master
        p = self.admin.execute("""SELECT phien_ban, loai, nguon, trang_thai, ngay_hieu_luc::text, tham_so -> 'crm_g6a' ->> 'g5_che_do', chung_tu_id::text
                                  FROM master.hop_dong_phien_ban WHERE id = %s""", (pb,)).fetchone()
        self.assertEqual(tuple(p[:6]), (1, "GOC", "CRM_MAU", "DA_DUYET", ngay(0), "SYNTHETIC_FIXTURE"))
        self.assertEqual(p[6], hl["hieu_luc"]["chung_tu_id"])
        ct = self.admin.execute("SELECT loai, hash, so_tien_minor, doi_tac_id::text FROM master.chung_tu WHERE id = %s"
                                .replace("master.chung_tu", "kho.chung_tu"), (p[6],)).fetchone()
        self.assertEqual(tuple(ct), ("HOP_DONG_TEP", self.khach_ky(D["ky"])[2], 1000000000, a1["doi_tac_id"]))
        ts = self.admin.execute("SELECT count(*), count(*) FILTER (WHERE do_tin_cay = 'MAU_DA_KY') FROM master.hop_dong_tham_so WHERE phien_ban_id = %s",
                                (pb,)).fetchone()
        self.assertEqual((ts[0], ts[1]), (hl["hieu_luc"]["so_tham_so"], hl["hieu_luc"]["so_tham_so"]))
        self.assertGreater(ts[0], 0)
        lt = self.admin.execute("SELECT khoa_nghia_vu, so_tien_minor, han::text FROM master.lich_thu WHERE phien_ban_id = %s ORDER BY dot",
                                (pb,)).fetchall()
        self.assertEqual([tuple(x) for x in lt], [("CRM-DOT-1", 400000000, None), ("CRM-DOT-2", 600000000, ngay(60))])
        self.assertEqual(self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (self.s["viec_d"],)), "DA_DUYET")
        self.assertEqual(self.khach_ky(D["ky"])[0], None)  # khách trên bản ký G4 (revision đã ký) KHÔNG bị sửa
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (D["soan"],)), "DA_KY")
        trc = self.dem_kiem(D["ky"])
        with self.app.mutation_lock:
            r1 = self.app._crm_db(lambda: sv.hieu_luc(KT, khoa=self.K("syn-hl"), **body))
            r2 = self.app._crm_db(lambda: sv.hieu_luc(KT, khoa=self.K("syn-hl-moi"), **body))
        self.assertEqual((r1["lap_lai"], r2["lap_lai"], r1["hieu_luc"]["phien_ban_id"], r2["hieu_luc"]["phien_ban_id"]), (True, True, pb, pb))
        self.assertEqual(self.dem_kiem(D["ky"]), trc)
        self.kiem_loi(KT, "hieu-luc", {**body, "khoa": self.K("hl-http")}, 409, "CRM_KIEM_DA_HIEU_LUC")  # HTTP (VAN_HANH) không dùng lại được
        self.kiem_loi(KT, "check", {"ky_id": D["ky"], "expected_revision": 2, "khoa": self.K("check-sau-hl")}, 409, "CRM_KIEM_TRANG_THAI")
        self.assertEqual(self.dem_kiem(D["ky"]), trc)
        self.assertEqual(self.viec_thay(KT, self.s["viec_d"]), 1)  # sau kích hoạt: đúng phạm vi vẫn đọc được việc đã đóng

    # ------------------------------------------------------------------ n08: F6 (fact_hop_dong_m1) + F7 (lien_ket) đọc kết quả kích hoạt
    def test_n08_f6_f7(self):
        self.can("pb_hl")
        D, a1, pb = self.s["D"], self.s["a1"], self.s["pb_hl"]
        with self.app.mutation_lock:
            f = self.app._crm_db(self.app.crm().fact_hop_dong_m1, CFO, "PN_DEMO_A")
        e = [x for x in f.get(a1["object"], []) if x["phien_ban_id"] == pb]
        self.assertEqual(len(e), 1, "F6 phải thấy phiên bản HIEU_LUC dưới mã Junsky KT đã chọn")
        self.assertEqual((e[0]["hop_dong_id"], e[0]["hieu_luc_tu"]), (D["hd"], ngay(0)))
        self.assertEqual([d["khoa"] for d in e[0]["dot"]], ["CRM-DOT-1", "CRM-DOT-2"])
        self.assertTrue(str((e[0]["provenance"]["profile"] or {}).get("ma", "")).startswith("CRM_MAU:"))
        self.assertEqual(str(self.q("SELECT master.crm_phien_ban_hieu_luc(%s, %s::date)", (D["hd"], ngay(0)))), pb)
        tien = self.admin.execute("""SELECT c.id::text FROM kho.chung_tu c JOIN master.phap_nhan p ON p.id = c.phap_nhan_id
                                     WHERE p.ma = 'PN_DEMO_A' AND c.loai = 'SAO_KE' AND c.so_tien_minor > 0 ORDER BY c.id LIMIT 1""").fetchone()
        if tien is None:
            self.fail("NOT_VERIFIED: bản sao không có SAO_KE PN_DEMO_A để nối F7 — không tự tạo chứng từ tiền")
        dot1 = e[0]["dot"][0]["lich_id"]
        khoa = self.K("f7")
        with self.app.mutation_lock:
            self.app._crm_db(self.app.crm().lien_ket, KT_M1, tien[0], dot1, 1, khoa)
        lk = self.admin.execute("""SELECT lich_thu_id::text, hop_dong_id::text, trang_thai, so_tien_khop_minor FROM kho.lien_ket_chung_tu
                                   WHERE khoa_idempotency = %s""", (khoa,)).fetchone()
        self.assertEqual(tuple(lk), (dot1, D["hd"], "DA_KHOP", 1))

    # ------------------------------------------------------------------ n09 (P1-A): việc K5 không liên quan không đổi; đọc rộng không mở
    def test_n09_k5_khong_lien_quan_khong_doi(self):
        self.can("k5_truoc", "k5_kt_truoc")
        sau = self.k5_khac()
        doi = sorted(k for k, v in self.s["k5_truoc"].items() if sau.get(k) != v)
        self.assertEqual(doi, [], "việc K5 không thuộc G6A bị đổi/mất")
        self.assertLessEqual(self.s["k5_kt_truoc"], self.viec_thay(KT, None))  # policy G6A không thu hẹp việc khác đã thấy


if __name__ == "__main__":
    unittest.main()
