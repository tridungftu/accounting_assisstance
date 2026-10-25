"""M2-00E — HTTP "Tải từ cổng thuế" qua máy chủ cục bộ THẬT (`LocalServer`) + điều phối M2-00B THẬT + bộ tải GIẢ (NodeGia/TienTrinhGia của test M2-00B).

Không PostgreSQL, không Node, không cổng thuế, không mạng ngoài loopback. Dữ liệu chỉ DEMO. Kết nối CSDL là fake literal của test_m2_00b_tinh; K2 nhận (ca nhận kết quả)
dùng consumer giả của test M2c ngay quanh lời gọi `nhan_vao_k2` thật. Bộ tải thật #7 chưa có trong repo nên các ca "chạy thật" thuộc gói M2f.

Ca nghiệm thu chứng minh trên bộ tải giả: M2-00-01 (bấm nút → bộ tải mở ngầm, tiến trình/log hiện qua API; tắt theo máy chủ), M2-00-05 (lỗi bộ tải/HTTP cổng/429/nhóm
bỏ qua hiện đúng mã, không im lặng), M2-00-08 (quyền theo pháp nhân; không mật khẩu/capability/nonce trong mọi response).
"""

from __future__ import annotations

import http.client
import json
import re
import secrets
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_m2_00_nhan_tinh as nhan_test
from test_m2_00_manifest_tinh import tao_run_demo
from test_m2_00b_tinh import CAP, CTY_A, CTY_B, INST, MA_A, MA_B, PN_A, PN_B, SCOPE, SID_KT, SID_KT2, SID_XA, AppGia, KetNoiGia, NodeGia, TienTrinhGia, tao_cau_hinh

from kho_tri_thuc.giao_dien import m2_tai_hoa_don as mod
from kho_tri_thuc.giao_dien.server import LocalServer
from kho_tri_thuc.ha_tang.config import Config, doc_tai_hoa_don
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m2.tai_hoa_don import LoiTienTrinh

RAIZ = Path(__file__).resolve().parent.parent
SID_BH = "sid-demo-ban-hang-0001"
MAT_KHAU_CANARY = "DEMO_CANARY_PASS_7f3a91"
JWT_CANARY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJERU1PX0NBTkFSWSJ9.DEMOsignatureCANARYabc123"
TIEN_TO = "/api/m2/tai-hoa-don"


class AppHttp(AppGia):
    """AppGia + phần LocalApp mà Handler/module HTTP dùng (token, khóa thao tác, phiên có cấp cookie)."""
    CRM_COOKIE = "ktt_crm"
    CRM_MAC_DINH = "MO_PHONG_KE_TOAN"

    def __init__(self, conn, root):
        super().__init__(conn, root)
        self.token = "TOKEN-DEMO-" + secrets.token_urlsafe(12)
        self.mutation_lock = threading.Lock()
        self.is_that = False
        self.root_id = "demo"
        self.demo_config = SimpleNamespace(tai_hoa_don=None)

    def crm_phien(self, sid, *, tao=False):
        phien = self.__dict__.setdefault("_crm_phien", {})
        if sid and sid in phien:
            return sid, phien[sid], False
        if not tao:
            raise DataError("CRM_PHIEN", "Phiên CRM chưa có hoặc đã hết — tải lại trang để nhận phiên mới.")
        sid = secrets.token_urlsafe(24)
        phien[sid] = self.CRM_MAC_DINH
        return sid, phien[sid], True

    @staticmethod
    def _crm_db(fn, *args):
        return fn(*args)

    def trich6_suc_khoe(self):
        return {"quan_ly": False}


class Phan:
    """Phản hồi HTTP đã đọc: status, header, body thô, JSON (nếu có)."""

    def __init__(self, status, headers, raw):
        self.status, self.headers, self.raw = status, headers, raw
        self.text = raw.decode("utf-8", "replace")
        try:
            self.json = json.loads(self.text) if "json" in headers.get("Content-Type", "") else None
        except ValueError:
            self.json = None


class Co(unittest.TestCase):
    """Dựng app/fake DB/bộ tải giả/máy chủ HTTP thật (cổng 0 = hệ điều hành cấp)."""

    def setUp(self):
        self._tam = tempfile.TemporaryDirectory(prefix="m2-00e-", ignore_cleanup_errors=True)
        self.addCleanup(self._tam.cleanup)
        self.goc = Path(self._tam.name).resolve()
        self.conn = KetNoiGia()
        self.moi_phan_hoi = []
        self.app = AppHttp(self.conn, self.goc / "app")
        for sid, login in ((SID_KT, "MO_PHONG_KE_TOAN"), (SID_KT2, "MO_PHONG_KE_TOAN"), (SID_XA, "MO_PHONG_XEM_A"), (SID_BH, "MO_PHONG_BAN_HANG")):
            self.app.dat_phien(sid, login)
        self.cfg = tao_cau_hinh(self.goc / "cfg")
        self.node = NodeGia()
        self.tt = TienTrinhGia(self.node, self.cfg.gioi_han, san_sang=False)
        self.app._tai_hoa_don = {"cau_hinh": self.cfg, "tien_trinh": self.tt}
        self.mo_may_chu()

    def mo_may_chu(self):
        self.may_chu = LocalServer(self.app, 0)
        threading.Thread(target=self.may_chu.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

        def dong():
            self.may_chu.shutdown()
            self.may_chu.server_close()
        self.addCleanup(dong)

    def goi(self, phuong_thuc, duong, body=None, sid=SID_KT, token=True):
        c = http.client.HTTPConnection("127.0.0.1", self.may_chu.server_port, timeout=20)
        try:
            h = {}
            if token:
                h["X-KTT-Token"] = self.app.token
            if sid:
                h["Cookie"] = f"ktt_crm={sid}"
            data = None
            if body is not None:
                data = json.dumps(body).encode("utf-8")
                h.update({"Content-Type": "application/json", "Content-Length": str(len(data))})
            c.request(phuong_thuc, duong, body=data, headers=h)
            r = c.getresponse()
            p = Phan(r.status, dict(r.getheaders()), r.read())
            self.moi_phan_hoi.append(p)
            return p
        finally:
            c.close()

    def chon(self, cty=CTY_A, khoa="khoa-demo-0001", thang=9, **kw):
        return {"source_instance": INST, "scope_ref": SCOPE, "company_key": cty, "mode": "month", "year": 2026, "month": thang,
                "types": ["purchase"], "formats": ["xml"], "khoa": khoa, **kw}

    def mo_bo_tai(self):
        self.node.san_sang = {MA_A: (True, None), MA_B: (True, None)}
        p = self.goi("POST", TIEN_TO + "/khoi-dong", {})
        self.assertEqual(p.status, 200, p.text)
        return p

    def bat_dau(self, **kw):
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon(**kw))
        self.assertEqual(p.status, 200, p.text)
        return p.json

    def hanh_dong(self):
        return [r["hanh_dong"] for r in self.conn.nhat_ky]

    def ma_loi(self, p):
        return p.json["error"] if p.json else None


class CauHinhTest(unittest.TestCase):
    def test_config_vang_muc_la_none(self):
        self.assertIsNone(Config.load(RAIZ / "cau_hinh.toml").tai_hoa_don)

    def test_config_doc_muc_va_tu_choi_sai(self):
        with tempfile.TemporaryDirectory(prefix="m2-00e-cfg-", ignore_cleanup_errors=True) as tam:
            goc = (RAIZ / "cau_hinh.toml").read_text(encoding="utf-8-sig")
            sha = "a" * 64

            def nap(them):
                p = Path(tam) / "cau_hinh.toml"
                p.write_text(goc + "\n" + them, encoding="utf-8")
                return Config.load(p, Path(tam) / "d")
            c = nap(f'[tai_hoa_don]\ngoc_bo_tai = "C:/bo-tai"\ncong = 0\nnode_sha256 = "{sha}"\n[tai_hoa_don.tep_pin]\n"src/server.js" = "{sha}"\n')
            self.assertEqual(c.tai_hoa_don, {"goc_bo_tai": "C:/bo-tai", "cong": 0, "node_sha256": sha, "tep_pin": {"src/server.js": sha}})
            self.assertEqual(nap("[tai_hoa_don]\n").tai_hoa_don, {})  # có mục nhưng rỗng: đọc được, giao diện báo thiếu gì
            for sai in ('khoa_la = "x"', "cong = 80", 'cong = "0"', 'node_sha256 = "ABC"', 'goc_bo_tai = ""', "goc_bo_tai = 5"):
                with self.subTest(sai=sai), self.assertRaises(DataError) as e:
                    nap("[tai_hoa_don]\n" + sai + "\n")
                self.assertEqual(e.exception.code, "INVALID_TAI_HOA_DON")

    def test_config_goc_hoi_cuu_tin_cay(self):
        with tempfile.TemporaryDirectory(prefix="m2-00e-cfg2-", ignore_cleanup_errors=True) as tam:
            goc = (RAIZ / "cau_hinh.toml").read_text(encoding="utf-8-sig")

            def nap(them):
                p = Path(tam) / "cau_hinh.toml"
                p.write_text(goc + "\n" + them, encoding="utf-8")
                return Config.load(p, Path(tam) / "d")
            self.assertEqual(nap('[tai_hoa_don]\ngoc_hoi_cuu_tin_cay = ["D:/cu/PLHN", "D:/cu/khac"]\n').tai_hoa_don, {"goc_hoi_cuu_tin_cay": ["D:/cu/PLHN", "D:/cu/khac"]})
            for sai in ('goc_hoi_cuu_tin_cay = []', 'goc_hoi_cuu_tin_cay = "D:/cu"', "goc_hoi_cuu_tin_cay = [1]", 'goc_hoi_cuu_tin_cay = [""]'):
                with self.subTest(sai=sai), self.assertRaises(DataError) as e:
                    nap("[tai_hoa_don]\n" + sai + "\n")
                self.assertEqual(e.exception.code, "INVALID_TAI_HOA_DON")

    def test_doc_tai_hoa_don_tep_pin_sai(self):
        for pin in ({}, {"a": "xyz"}, {"": "a" * 64}, "chuoi"):
            with self.subTest(pin=pin), self.assertRaises(DataError):
                doc_tai_hoa_don({"tep_pin": pin})

    def test_dung_cau_hinh_thieu_va_dung(self):
        with self.assertRaises(DataError) as e:
            mod.dung_cau_hinh(None)
        self.assertEqual(e.exception.code, "TAI_HOA_DON_CHUA_CAU_HINH")
        self.assertIn("chưa cấu hình", str(e.exception))
        with self.assertRaises(DataError) as e:
            mod.dung_cau_hinh({"goc_bo_tai": "C:/x", "cong": 0})
        self.assertIn("node_exe", str(e.exception))
        self.assertIn("tep_pin", str(e.exception))
        with tempfile.TemporaryDirectory(prefix="m2-00e-dc-", ignore_cleanup_errors=True) as tam:
            ch = tao_cau_hinh(Path(tam))
            ts = thong_so_tu(ch)
            dung = mod.dung_cau_hinh(ts)
            self.assertEqual((dung.goc_7, dung.goc_tai, dung.cong, dung.phien_ban_bo_tai), (ch.goc_7, ch.goc_tai, 0, ch.phien_ban_bo_tai))
            with self.assertRaises(DataError) as e:
                mod.dung_cau_hinh({**ts, "thu_muc_tai": str(Path(tam) / "khong-ton-tai")})
            self.assertEqual(e.exception.code, "TAI_HOA_DON_CAU_HINH_SAI")
            self.assertNotIn(tam, str(e.exception))  # không lộ đường dẫn


def thong_so_tu(ch) -> dict:
    return {"goc_bo_tai": str(ch.goc_7), "node_exe": str(ch.node_exe), "node_sha256": ch.node_sha256, "phien_ban_bo_tai": ch.phien_ban_bo_tai,
            "thu_muc_tai": str(ch.goc_tai), "thu_muc_trinh_duyet": str(ch.goc_trinh_duyet), "thu_muc_profile": str(ch.goc_profile),
            "thu_muc_dieu_phoi": str(ch.goc_dieu_phoi), "tep_pin": {t.rel: t.sha256 for t in ch.tep_pin}, "cong": 0}


class ChuaCauHinh(Co):
    def test_trang_thai_chua_cau_hinh_khong_loi_va_khong_cham_csdl(self):
        del self.app._tai_hoa_don
        p = self.goi("GET", TIEN_TO, sid=None)
        self.assertEqual(p.status, 200)
        self.assertIs(p.json["cau_hinh"], False)
        self.assertEqual(p.json["ma"], "TAI_HOA_DON_CHUA_CAU_HINH")
        self.assertIn("chưa cấu hình", p.json["ly_do"])
        self.assertEqual(p.json["muc"], [])
        self.assertIn("ktt_crm=", p.headers.get("Set-Cookie", ""))  # cấp phiên như /api/m2
        self.assertEqual(self.conn.sql, [])
        self.assertEqual(self.conn.nhat_ky, [])

    def test_muc_thieu_khoa_noi_ro_thieu_gi(self):
        del self.app._tai_hoa_don
        self.app.demo_config = SimpleNamespace(tai_hoa_don={"goc_bo_tai": "C:/x"})
        p = self.goi("GET", TIEN_TO)
        self.assertIs(p.json["cau_hinh"], False)
        self.assertIn("node_exe", p.json["ly_do"])

    def test_cac_lenh_khac_tra_503_co_ma_va_goi_y(self):
        del self.app._tai_hoa_don
        for duong, body in (("/khoi-dong", {}), ("/bat-dau", self.chon())):
            p = self.goi("POST", TIEN_TO + duong, body)
            self.assertEqual((p.status, p.json["error"]), (503, "TAI_HOA_DON_CHUA_CAU_HINH"), p.text)
            self.assertIn("chưa cấu hình", p.json["message"])
            self.assertIn("[tai_hoa_don]", p.json["goi_y"])

    def test_cau_hinh_that_tu_config_dung_tien_trinh_that_khong_spawn(self):
        del self.app._tai_hoa_don
        self.app.demo_config = SimpleNamespace(tai_hoa_don=thong_so_tu(self.cfg))
        p = self.goi("GET", TIEN_TO)
        self.assertEqual(p.status, 200, p.text)
        self.assertIs(p.json["cau_hinh"], True)
        self.assertEqual(p.json["bo_tai"], {"san_sang": False, "trang_thai": "CHUA_KHOI_DONG"})
        self.assertEqual({m["company_key"] for m in p.json["muc"]}, {CTY_A, CTY_B})
        self.assertTrue(all(m["san_sang"] is False and m["ly_do"] == "NODE_CHUA_SAN_SANG" for m in p.json["muc"]))

    def test_kho_that_khong_mo(self):
        self.app.is_that = True
        p = self.goi("GET", TIEN_TO)
        self.assertEqual((p.status, p.json["error"]), (403, "THAT_UI"))


class LuongTai(Co):
    def test_m2_00_01_nut_mo_bo_tai_ngam_tien_trinh_va_log_hien_trong_m2(self):
        # trước khi mở: danh sách có nhưng chưa sẵn sàng; bấm tải sớm bị từ chối rõ ràng, 0 lệnh tới bộ tải
        p = self.goi("GET", TIEN_TO)
        self.assertEqual(p.status, 200)
        self.assertIs(p.json["bo_tai"]["san_sang"], False)
        self.assertEqual([m["phap_nhan_ma"] for m in p.json["muc"]], [MA_A, MA_B])
        self.assertTrue(all(m["san_sang"] is False and "Bộ tải chưa mở" in m["ly_do_vi"] for m in p.json["muc"]))
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon())
        self.assertEqual((p.status, p.json["error"]), (503, "M2_00B_NODE_CHUA_SAN_SANG"))
        self.assertIn("Mở bộ tải", p.json["goi_y"])
        self.assertEqual([x for _, x in self.node.goi if x == "/api/start"], [])
        # mở bộ tải (idempotent: lần hai không spawn thêm)
        self.mo_bo_tai()
        self.assertEqual(self.tt.so_start, 1)
        self.assertEqual(self.goi("POST", TIEN_TO + "/khoi-dong", {}).json["bo_tai"]["san_sang"], True)
        self.assertEqual(self.tt.so_start, 1)
        p = self.goi("GET", TIEN_TO)
        self.assertIs(p.json["bo_tai"]["san_sang"], True)
        self.assertEqual([(m["phap_nhan_ma"], m["san_sang"]) for m in p.json["muc"]], [(MA_A, True), (MA_B, True)])
        # bấm "Tải từ cổng thuế"
        r = self.bat_dau()
        self.assertEqual((r["trang_thai"], r["phap_nhan_ma"], r["company_key"]), ("STARTED", MA_A, CTY_A))
        self.assertRegex(r["run_handle"], r"^[0-9a-f]{64}$")
        self.assertEqual(r["yeu_cau"], {"mode": "month", "year": 2026, "month": 9, "types": ["purchase"], "formats": ["xml"]})
        self.assertEqual(self.hanh_dong(), ["M2_00B_YEU_CAU_TAI", "M2_00B_KET_QUA_START"])
        # bấm lại cùng khóa: cùng run, không chạy mù lần hai
        self.assertEqual(self.bat_dau()["run_handle"], r["run_handle"])
        self.assertEqual(self.node.so_start, 1)
        # trạng thái + tiến trình/log qua API (SSE đã lọc)
        t = self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}")
        self.assertEqual((t.status, t.json["trang_thai"]), (200, "RUNNING"))
        s = self.goi("GET", f"{TIEN_TO}/su-kien?run={r['run_handle']}&cursor=0")
        self.assertEqual(s.status, 200)
        self.assertTrue(s.headers["Content-Type"].startswith("text/event-stream"))
        khung = khung_sse(s.text)
        self.assertEqual([(k["ten"], k["du_lieu"].get("type")) for k in khung if k["ten"] == "su-kien"], [("su-kien", "phase"), ("su-kien", "log")])
        self.assertEqual(khung[-1]["ten"], "ket-thuc")
        # bộ tải xong: biên nhận (REPLAY) với thư mục run, nhật ký kết thúc, sự kiện done
        self.node.ket_thuc()
        t = self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}").json
        self.assertEqual(t["trang_thai"], "REPLAY")
        self.assertEqual(t["ket_qua"]["trang_thai"], "HOAN_TAT")
        run_rel = t["ket_qua"]["runs"][0]["run_rel"]
        self.assertEqual(run_rel, f"{MA_A}/2026-09/mua_vao/{r['run_id']}")
        self.assertIn("M2_00B_KET_THUC", self.hanh_dong())
        s = khung_sse(self.goi("GET", f"{TIEN_TO}/su-kien?run={r['run_handle']}&cursor=2").text)
        self.assertEqual([k["du_lieu"].get("type") for k in s if k["ten"] == "su-kien"], ["done"])
        self.assertEqual(s[-1]["du_lieu"], {"ly_do": "DONE"})
        # mở thư mục: chỉ run của chính lần tải này
        self.assertEqual(self.goi("POST", TIEN_TO + "/mo-thu-muc", {"run": r["run_handle"], "run_rel": run_rel}).json, {"phien_ban": "m2_00e.v1", "da_mo": True})
        self.assertEqual(self.node.mo, [run_rel])
        sai = self.goi("POST", TIEN_TO + "/mo-thu-muc", {"run": r["run_handle"], "run_rel": f"{MA_B}/2026-09/mua_vao/{r['run_id']}"})
        self.assertEqual((sai.status, self.ma_loi(sai)), (400, "M2_00B_RUN_REL_SAI"))
        # phiên khác không thấy kết quả của phiên này
        khac = self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}", sid=SID_KT2)
        self.assertEqual((khac.status, self.ma_loi(khac)), (409, "M2_00B_CAN_DOI_SOAT"))
        # đóng máy chủ → tắt bộ tải
        self.assertEqual(self.tt.so_dung, 0)
        mod.dung(self.app)
        self.assertEqual(self.tt.so_dung, 1)

    def test_doi_soat_khi_mat_ket_noi_luc_bat_dau(self):
        self.mo_bo_tai()
        self.node.ngat = True
        r = self.bat_dau()
        self.assertEqual((r["trang_thai"], r["can_doi_soat"], r["ma"]), ("UNKNOWN", True, "KHACH_KHONG_KET_NOI"))
        self.assertIn("Đối soát", r["goi_y"])
        self.node.ngat = False
        d = self.goi("POST", TIEN_TO + "/doi-soat", {"run": r["run_handle"]})
        self.assertEqual(d.status, 200, d.text)
        self.assertEqual(d.json["trang_thai"], "NOT_FOUND")  # Node chưa từng nhận lệnh: không tự chạy lại

    def test_khoi_dong_loi_co_ma_va_tieng_viet(self):
        def hong():
            raise LoiTienTrinh("NODE_SHA_SAI", "x")
        self.tt.start = hong
        p = self.goi("POST", TIEN_TO + "/khoi-dong", {})
        self.assertEqual((p.status, self.ma_loi(p)), (503, "M2_00B_NODE_SHA_SAI"))
        self.assertIn("Báo Claude", p.json["goi_y"])
        self.assertTrue(re.search(r"[ăâêôơưđ]", p.json["message"]))

    def test_khong_nhan_tu_trinh_duyet_dinh_danh_duong_dan_mat_khau(self):
        self.mo_bo_tai()
        for them in ({"actor": "MO_PHONG_KE_TOAN"}, {"phap_nhan": MA_B}, {"profile": "X"}, {"duong_dan": "C:/x"}, {"mat_khau": "x"}, {"captcha": "1234"},
                     {"cong": 47000}, {"run_id": "20260101-000000"}, {"client_key": "khoa-demo-9999"}):
            with self.subTest(them=them):
                p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon(**them))
                self.assertEqual((p.status, self.ma_loi(p)), (403, "M2_CLIENT_AUTHORITY"), p.text)
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon(la_hoac="x"))
        self.assertEqual((p.status, self.ma_loi(p)), (400, "M2_YEU_CAU_SAI"))
        thieu = self.chon()
        del thieu["mode"]
        self.assertEqual(self.goi("POST", TIEN_TO + "/bat-dau", thieu).status, 400)
        self.assertEqual(self.ma_loi(self.goi("POST", TIEN_TO + "/bat-dau", self.chon(khoa="x"))), "M2_00B_KHOA_SAI")
        self.assertEqual(self.ma_loi(self.goi("POST", TIEN_TO + "/bat-dau", self.chon(thang=13))), "M2_00B_KY_SAI")
        self.assertEqual(self.ma_loi(self.goi("POST", TIEN_TO + "/bat-dau", self.chon(types=["khac"]))), "M2_00B_CHON_SAI")
        self.assertEqual([x for _, x in self.node.goi if x == "/api/start"], [])
        self.assertEqual(self.conn.nhat_ky, [])
        for duong in ("/trang-thai?run=khong-phai-hex", "/trang-thai", "/su-kien?run=" + "0" * 64 + "&cursor=-1", "/trang-thai?run=" + "0" * 64 + "&la=1"):
            self.assertEqual(self.goi("GET", TIEN_TO + duong).status, 400, duong)
        self.assertEqual(self.ma_loi(self.goi("GET", f"{TIEN_TO}/trang-thai?run={'0' * 64}")), "M2_00B_RUN_KHONG_CO")

    def test_token_phien_bat_buoc(self):
        self.assertEqual(self.ma_loi(self.goi("GET", TIEN_TO, token=False)), "SESSION_TOKEN")
        self.assertEqual(self.goi("POST", TIEN_TO + "/khoi-dong", {}, token=False).status, 403)
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon(), sid="phien-khong-ton-tai")
        self.assertEqual((p.status, self.ma_loi(p)), (400, "CRM_PHIEN"))


class Quyen(Co):
    def test_m2_00_08_nguoi_khong_co_quyen_phap_nhan_khong_thay_va_khong_tai_duoc(self):
        self.mo_bo_tai()
        kt = self.goi("GET", TIEN_TO).json
        self.assertEqual([m["phap_nhan_ma"] for m in kt["muc"]], [MA_A, MA_B])
        xem = self.goi("GET", TIEN_TO, sid=SID_XA)
        self.assertEqual([m["phap_nhan_ma"] for m in xem.json["muc"]], [MA_A])  # chỉ có quyền DEMO_A
        for bi_mat in (MA_B, CTY_B, PN_B):
            self.assertNotIn(bi_mat, xem.text)
        truoc = len(self.node.goi)
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon(CTY_B), sid=SID_XA)
        self.assertEqual((p.status, self.ma_loi(p)), (403, "KHONG_CO_QUYEN_PHAP_NHAN"), p.text)
        self.assertIn("Vai hiện tại", p.json["goi_y"])
        self.assertEqual([x for _, x in self.node.goi[truoc:] if x == "/api/start"], [])
        self.assertEqual(self.conn.nhat_ky, [])
        self.assertEqual(self.goi("POST", TIEN_TO + "/bat-dau", self.chon(CTY_A), sid=SID_XA).status, 200)  # đúng pháp nhân của mình thì được

    def test_vai_khong_co_quyen_nao_thi_khong_mo_duoc_bo_tai(self):
        p = self.goi("GET", TIEN_TO, sid=SID_BH)
        self.assertEqual((p.status, p.json["muc"]), (200, []))
        p = self.goi("POST", TIEN_TO + "/khoi-dong", {}, sid=SID_BH)
        self.assertEqual((p.status, self.ma_loi(p)), (403, "KHONG_CO_QUYEN_TAI_CONG_THUE"))
        self.assertEqual(self.tt.so_start, 0)  # chưa spawn Node cho người không có quyền

    def test_mat_quyen_giua_chung_dung_run_va_khong_tra_ket_qua(self):
        self.mo_bo_tai()
        r = self.bat_dau()
        u_kt = self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["id"]
        self.conn.phan_quyen = [q for q in self.conn.phan_quyen if not (q["phap_nhan_id"] == PN_A and q["nguoi_dung_id"] == u_kt)]
        p = self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}")
        self.assertEqual((p.status, self.ma_loi(p)), (403, "KHONG_CO_QUYEN_PHAP_NHAN"))
        self.assertEqual(self.tt.so_dung, 1)
        self.assertNotIn("ket_qua", p.text)


class KhongBiMat(Co):
    def test_khong_mat_khau_capability_nonce_phien_trong_moi_response(self):
        self.mo_bo_tai()
        r = self.bat_dau()
        job = self.node.jobs[self.node.running]
        self.node._su_kien(job, "log", {"msg": "TAX_PASSWORD=" + MAT_KHAU_CANARY + " token " + JWT_CANARY})
        self.node._su_kien(job, "phase", {"type": "purchase", "label": "Mua vao", "monthTag": "2026-09", "mat_khau": MAT_KHAU_CANARY})
        self.node._su_kien(job, "progress", {"type": "purchase", "monthTag": "2026-09", "index": 3, "total": 12, "password": MAT_KHAU_CANARY})
        self.node._su_kien(job, "la", {"password": MAT_KHAU_CANARY})
        s = self.goi("GET", f"{TIEN_TO}/su-kien?run={r['run_handle']}&cursor=0")
        khung = [k for k in khung_sse(s.text) if k["ten"] == "su-kien"]
        self.assertEqual([k["du_lieu"]["type"] for k in khung], ["phase", "log", "log", "phase", "progress"])  # loại "la" bị bỏ
        self.assertEqual(khung[2]["du_lieu"]["payload"]["msg"], "[AN] token [AN]")
        self.assertEqual(khung[4]["du_lieu"]["payload"], {"type": "purchase", "monthTag": "2026-09", "index": 3, "total": 12})
        self.node.ket_thuc()
        self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}")
        self.goi("GET", TIEN_TO)
        ctx = self.context_gui()
        bi_mat = [MAT_KHAU_CANARY, JWT_CANARY, CAP, ctx["run"]["nonce"], ctx["run"]["request_key"], SID_KT, PN_A, str(self.goc), "capability", "password"]
        self.assertGreaterEqual(len(self.moi_phan_hoi), 5)  # khởi động, bắt đầu, sự kiện, trạng thái, danh sách
        for p in self.moi_phan_hoi:
            for x in bi_mat:
                self.assertNotIn(x, p.text, f"lộ {x[:12]} trong {p.status}")

    def context_gui(self):
        return [v for p, v in self.node.than if p == "/api/start"][0]["context"]


class LoiBoTai(Co):
    def test_m2_00_05_job_busy_va_loi_http_cong_thue_hien_dung_ma_va_goi_y(self):
        self.mo_bo_tai()
        self.node.loi_start = (409, "JOB_BUSY")
        p = self.goi("POST", TIEN_TO + "/bat-dau", self.chon())
        self.assertEqual((p.status, self.ma_loi(p)), (409, "M2_00B_JOB_BUSY"), p.text)
        self.assertIn("Bộ tải", p.json["message"])
        self.assertIn("Đợi lần đó xong", p.json["goi_y"])
        self.node.loi_start = None
        r = self.bat_dau(khoa="khoa-demo-0002")
        self.node.ket_thuc()
        job = self.node.jobs[next(iter(self.node.jobs))]
        job["receipt"]["trang_thai"] = "PARTIAL"
        runs = job["receipt"]["runs"]
        runs[0].update(trang_thai="FAILED", loi=[{"code": "LIST_FAILED", "stage": "LIST", "http_status": 401}, {"code": "EXPORT_XML_FAILED", "stage": "EXPORT_XML", "http_status": 429},
                                                 {"code": "LIST_FAILED", "stage": "LIST", "http_status": 404}, {"code": "LOGIN_TIMEOUT", "stage": "LOGIN", "http_status": None},
                                                 {"code": "ZIP_HONG", "stage": "ZIP", "http_status": None}])
        t = self.goi("GET", f"{TIEN_TO}/trang-thai?run={r['run_handle']}").json
        loi = t["ket_qua"]["runs"][0]["loi"]
        self.assertEqual([(x["code"], x["stage"], x["http_status"]) for x in loi],
                         [("LIST_FAILED", "LIST", 401), ("EXPORT_XML_FAILED", "EXPORT_XML", 429), ("LIST_FAILED", "LIST", 404), ("LOGIN_TIMEOUT", "LOGIN", None), ("ZIP_HONG", "ZIP", None)])
        self.assertIn("Token cổng thuế đã hết hạn", loi[0]["goi_y"])
        self.assertIn("giới hạn tốc độ", loi[1]["goi_y"])
        self.assertIn("đổi API", loi[2]["goi_y"])
        self.assertIn("Quá hạn chờ đăng nhập", loi[3]["goi_y"])
        self.assertIsNone(loi[4]["goi_y"])
        self.assertEqual(t["ket_qua"]["trang_thai"], "PARTIAL")

    def test_sse_loi_giua_chung_la_khung_loi_khong_phai_im_lang(self):
        self.mo_bo_tai()
        r = self.bat_dau()
        self.conn.phan_quyen = []
        p = self.goi("GET", f"{TIEN_TO}/su-kien?run={r['run_handle']}&cursor=0")
        self.assertEqual(p.status, 403)  # lỗi trước khi mở luồng = JSON thường, không phải luồng hỏng
        self.assertEqual(p.json["error"], "KHONG_CO_QUYEN_PHAP_NHAN")


# ---------------------------------------------------------------------------------------------- nhận kết quả theo manifest
class Nhan(Co):
    def tao_run_tren_dia(self, run_id, *, kieu="XML"):
        d = self.cfg.goc_tai / MA_A / "2026-09" / "mua_vao" / run_id
        d.mkdir(parents=True)
        m = tao_run_demo(d)
        m.update(run_id=run_id, ky="2026-09", chieu="purchase", thu_muc_chieu="mua_vao")
        m["phap_nhan"]["ma"] = MA_A
        m["context"].update(source_instance=INST, scope_ref=SCOPE)
        nhan_test.NhanTinh.doi_xml(d, m, nhan_test.xml_demo())
        h = m["hoa_don"][0]
        if kieu == "LOI_429":
            h.update(xml_status="LOI", bang_chung=None, file_xml=None, hash_xml=None, xml_bytes=None, xml_tep=[], file_pdf=None, hash_pdf=None, vai_tro_pdf=None,
                     loi={"code": "EXPORT_XML_FAILED", "stage": "EXPORT_XML", "http_status": 429})
            m["tong"].update(xml_ok=0, pdf_ok=0, xml_loi=1)
            m.update(trang_thai="PARTIAL", ly_do_partial=["XML_LOI"])
        elif kieu == "KHONG_MA":
            h.update(xml_status="KHONG_XML_GOC", bang_chung="BANG_KE", can_cu="DEMO_KHONG_XML_GOC", file_xml=None, hash_xml=None, xml_bytes=None, xml_tep=[],
                     file_pdf=None, hash_pdf=None, vai_tro_pdf=None)
            m["tong"].update(xml_ok=0, pdf_ok=0, khong_xml_goc=1)
        nhan_test.NhanTinh.ghi(d, m)
        return d

    def tai_xong(self, **kw):
        self.mo_bo_tai()
        r = self.bat_dau(**kw)
        self.node.ket_thuc()
        return r

    def nhan_voi_k2_gia(self, run_handle, sid=SID_KT):
        """Giữ nguyên plan/nhan_vao_k2 THẬT; chỉ thay dịch vụ K2 bằng consumer giả của test M2c ngay quanh lời gọi."""
        goc = mod.nhan_vao_k2
        tc = nhan_test.NhanTinh("test_03_replay_cung_manifest_khong_them_ban_ghi")
        tc.root = self.goc

        def nhan_gia(ke_hoach, _k2, **kw):
            with tc.k2_gia(pn=MA_A, company_key="0000000002") as (service, _):
                return goc(ke_hoach, service, **kw)
        with patch.object(mod, "nhan_vao_k2", nhan_gia):
            return self.goi("POST", TIEN_TO + "/nhan", {"run": run_handle}, sid=sid)

    def test_nhan_xml_moi_tom_tat_dung_va_ghi_nhat_ky(self):
        r = self.tai_xong()
        self.tao_run_tren_dia(r["run_id"])
        p = self.nhan_voi_k2_gia(r["run_handle"])
        self.assertEqual(p.status, 200, p.text)
        self.assertEqual(p.json["tom_tat"], {"moi": 1, "doi_trang_thai": 0, "khong_ma": 0, "loi": 0, "khong_doi": 0, "giu_cho_tien_te": 0})
        self.assertEqual(p.json["trang_thai_tai"], "HOAN_TAT")
        run = p.json["runs"][0]
        self.assertEqual((run["run_rel"], run["ky"], run["chieu"], run["nguon"], run["so_muc"]), (f"{MA_A}/2026-09/mua_vao/{r['run_id']}", "2026-09", "purchase", "TAI_MOI", 1))
        self.assertEqual(run["ket_qua"][0]["items"][0]["classification"], ["FIRST_OBSERVATION"])
        self.assertEqual(p.json["nhat_ky"], "DA_GHI")
        self.assertIn("M2_00E_NHAN_KET_QUA", self.hanh_dong())
        self.assertNotIn(str(self.goc), p.text)
        self.assertNotIn("0000000001", p.text)  # MST/định danh từng hóa đơn không đi ra trình duyệt

    def test_nhan_khong_ma_la_bang_ke_khong_phai_loi(self):
        r = self.tai_xong()
        self.tao_run_tren_dia(r["run_id"], kieu="KHONG_MA")
        p = self.nhan_voi_k2_gia(r["run_handle"])
        self.assertEqual(p.json["tom_tat"], {"moi": 0, "doi_trang_thai": 0, "khong_ma": 1, "loi": 0, "khong_doi": 0, "giu_cho_tien_te": 0}, p.text)

    def test_m2_00_05_loi_429_trong_manifest_hien_la_ngoai_le_khong_im_lang(self):
        r = self.tai_xong()
        self.tao_run_tren_dia(r["run_id"], kieu="LOI_429")
        p = self.nhan_voi_k2_gia(r["run_handle"])
        self.assertEqual(p.status, 200, p.text)
        ma = {e["ma"]: e for e in p.json["runs"][0]["ngoai_le"]}
        self.assertEqual(set(ma), {"TAI_LOI", "RUN_PARTIAL"})
        self.assertEqual((ma["TAI_LOI"]["loi"]["code"], ma["TAI_LOI"]["loi"]["http_status"]), ("EXPORT_XML_FAILED", 429))
        self.assertIn("giới hạn tốc độ", ma["TAI_LOI"]["loi"]["goi_y"])
        self.assertEqual((p.json["tom_tat"]["moi"], p.json["tom_tat"]["loi"]), (0, 2))

    def test_thieu_thu_muc_hoac_manifest_hong_la_loi_cua_run_do_khong_hong_ca_yeu_cau(self):
        r = self.tai_xong()
        p = self.nhan_voi_k2_gia(r["run_handle"])  # biên nhận có run nhưng thư mục chưa có trên đĩa
        self.assertEqual(p.status, 200, p.text)
        self.assertEqual(p.json["tom_tat"]["loi"], 1)
        self.assertEqual(p.json["runs"][0]["loi"]["ma"], "M2_00B_DUONG_DAN")
        d = self.tao_run_tren_dia(r["run_id"])
        (d / "DEMO__0000000001.xml").write_bytes(b"<HDon>doi sau khi ghi manifest</HDon>")  # hash lệch manifest
        p = self.nhan_voi_k2_gia(r["run_handle"])
        self.assertEqual(p.json["runs"][0]["loi"]["ma"], "M2_00_MANIFEST_HASH_LECH")
        self.assertEqual(p.json["tom_tat"]["moi"], 0)

    def test_dang_chay_va_khac_phien_va_khong_quyen(self):
        self.mo_bo_tai()
        r = self.bat_dau()
        p = self.goi("POST", TIEN_TO + "/nhan", {"run": r["run_handle"]})
        self.assertEqual((p.status, self.ma_loi(p)), (409, "M2_00E_DANG_CHAY"))
        self.node.ket_thuc()
        self.assertEqual(self.ma_loi(self.goi("POST", TIEN_TO + "/nhan", {"run": r["run_handle"]}, sid=SID_KT2)), "M2_00B_CAN_DOI_SOAT")
        self.assertEqual(self.ma_loi(self.goi("POST", TIEN_TO + "/nhan", {"run": r["run_handle"], "path": "C:/x"})), "M2_CLIENT_AUTHORITY")
        self.conn.phan_quyen = []
        self.assertEqual(self.goi("POST", TIEN_TO + "/nhan", {"run": r["run_handle"]}).status, 403)

    def tao_run_hoi_cuu(self, run_id):
        """Run kiểu HOI_CUU: manifest nằm trong thư mục tải, tệp XML/PDF/bảng kê để tại chỗ ở một thư mục dữ liệu cũ (đường dẫn tuyệt đối trong manifest)."""
        d = self.tao_run_tren_dia(run_id)
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        cu = self.goc / "nguon-cu"
        cu.mkdir()
        h, bk = m["hoa_don"][0], m["tong"]["bang_ke"]
        for ten in (h["file_xml"], h["file_pdf"], bk["file"]):
            (cu / ten).write_bytes((d / ten).read_bytes())
        h["file_xml"] = h["xml_tep"][0]["file"] = str(cu / h["file_xml"])
        h["file_pdf"] = str(cu / h["file_pdf"])
        bk.update(file=str(cu / bk["file"]), so_cot=15)
        m.update(nguon="HOI_CUU", xap_xi=True, thu_muc_tep_goc=str(cu))
        nhan_test.NhanTinh.ghi(d, m)
        return cu

    def test_duong_nhan_tu_dong_truyen_goc_hoi_cuu_tin_cay_tu_cau_hinh(self):
        cu = self.goc / "nguon-cu"
        self.app._tai_hoa_don["goc_hoi_cuu_tin_cay"] = [str(cu)]
        r = self.tai_xong()
        self.tao_run_tren_dia(r["run_id"])
        goi = []
        that = mod.lap_ke_hoach_nhan

        def ghi_nhan(*a, **kw):
            goi.append(kw.get("goc_hoi_cuu_tin_cay"))
            return that(*a, **kw)
        with patch.object(mod, "lap_ke_hoach_nhan", ghi_nhan):
            self.goi("POST", TIEN_TO + "/nhan", {"run": r["run_handle"]})
            self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}&run_rel={MA_A}/2026-09/mua_vao/{r['run_id']}")
        self.assertEqual(goi, [(str(self.cfg.goc_tai), str(cu))])  # không bao giờ để trống; luôn gồm thư mục tải
        self.assertEqual(mod.dich_vu(self.app).goc_hoi_cuu_tin_cay, (str(self.cfg.goc_tai), str(cu)))

    def test_hoi_cuu_chi_nhan_khi_goc_cu_nam_trong_cau_hinh(self):
        r = self.tai_xong()
        cu = self.tao_run_hoi_cuu(r["run_id"])
        p = self.nhan_voi_k2_gia(r["run_handle"])  # cấu hình chỉ có thư mục tải: gốc cũ do manifest tự khai báo KHÔNG được tin
        self.assertEqual(p.status, 200, p.text)
        self.assertEqual(p.json["runs"][0]["loi"]["ma"], "M2_00_MANIFEST_HOI_CUU_GOC_KHONG_TIN_CAY")
        self.assertEqual(p.json["tom_tat"]["moi"], 0)
        self.assertNotIn(str(cu), p.text)
        run_rel = f"{MA_A}/2026-09/mua_vao/{r['run_id']}"
        m = self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}&run_rel={run_rel}")
        self.assertEqual((m.status, self.ma_loi(m)), (400, "M2_00_MANIFEST_HOI_CUU_GOC_KHONG_TIN_CAY"))
        self.app.__dict__.pop("_tai_hoa_don_dv")  # dựng lại điều phối với gốc cũ được khai trong cấu hình
        self.app._tai_hoa_don["goc_hoi_cuu_tin_cay"] = [str(cu)]
        p = self.nhan_voi_k2_gia(r["run_handle"])
        self.assertEqual(p.status, 200, p.text)
        self.assertEqual((p.json["runs"][0].get("loi"), p.json["runs"][0]["nguon"]), (None, "HOI_CUU"), p.text)
        self.assertEqual(p.json["tom_tat"]["moi"], 1)
        m = self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}&run_rel={run_rel}")
        self.assertEqual((m.status, m.json["nguon"]), (200, "HOI_CUU"), m.text)
        self.assertNotIn(str(cu), m.text)

    def test_xem_manifest_chi_so_dem_khong_noi_dung_hoa_don(self):
        r = self.tai_xong()
        self.tao_run_tren_dia(r["run_id"])
        run_rel = f"{MA_A}/2026-09/mua_vao/{r['run_id']}"
        p = self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}&run_rel={run_rel}")
        self.assertEqual(p.status, 200, p.text)
        j = p.json
        self.assertEqual((j["run_rel"], j["nguon"], j["ky"], j["chieu"], j["trang_thai"]), (run_rel, "TAI_MOI", "2026-09", "purchase", "COMPLETE"))
        self.assertEqual((j["tong"]["tong_hd"], j["tong"]["xml_ok"], j["tong"]["khong_xml_goc"]), (1, 1, 0))
        self.assertIs(j["co_bang_ke"], True)
        self.assertIn("captcha_da_go", j["dang_nhap"])
        self.assertEqual(j["nhom"][0]["so_ban_ghi"], 1)
        for cam in ("hoa_don", "key_raw", "0000000001", "DEMO__", "bang_ke_DEMO", str(self.goc), "sha256", "hash"):
            self.assertNotIn(cam, p.text)
        sai = self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}&run_rel={MA_B}/2026-09/mua_vao/{r['run_id']}")
        self.assertEqual((sai.status, self.ma_loi(sai)), (400, "M2_00B_RUN_REL_SAI"))
        self.assertEqual(self.goi("GET", f"{TIEN_TO}/manifest?run={r['run_handle']}").status, 400)


class TomTatNhan(unittest.TestCase):
    def test_phan_loai_dem(self):
        def it(ls, cls=None, **kw):
            return {"trang_thai": "DA_GHI_QUAN_SAT" if cls else "GIU_CHO_K2", "ly_do": ls, "items": [{"classification": cls}] if cls else []} | kw
        run = {"ket_qua": [it(None, ["FIRST_OBSERVATION"]), it(None, "FIRST_OBSERVATION"), it(None, ["CHANGED_CONTENT_HOLD"]), it(None, ["ANCESTOR_REAPPEARANCE_HOLD"]),
                           it(None, ["SAME_CONTENT_REPEAT"]), it("K2_CHUA_NHAN_BANG_KE"), it("TIEN_TE_CHUA_RO"), it("M2_LOI_KHAC")],
               "ngoai_le": [{"ma": "TAI_LOI"}, {"ma": "TIEN_TE_CHUA_RO"}, {"ma": "QUAN_HE_CHUA_RO"}]}
        self.assertEqual(mod.tom_tat_nhan([run, {"loi": {"ma": "X"}}]),
                         {"moi": 2, "doi_trang_thai": 2, "khong_ma": 1, "loi": 3, "khong_doi": 1, "giu_cho_tien_te": 1})

    def test_ma_loi_http_va_goi_y(self):
        for ma, st in (("M2_00B_PN_MAPPING_ABSENT", 409), ("KHONG_CO_QUYEN_PHAP_NHAN", 403), ("M2_00B_NODE_SHA_SAI", 503), ("M2_00B_KHACH_QUA_HAN", 502),
                       ("M2_00B_RUN_KHONG_CO", 404), ("CRM_PHIEN", 400), ("MA_LA_KHONG_BIET", 400)):
            self.assertEqual(mod.trang_thai_http(ma), st, ma)
        self.assertIn("CFO", mod.goi_y_ma("M2_00B_PN_MAPPING_ABSENT"))
        self.assertIsNone(mod.goi_y_ma("MA_LA_KHONG_BIET"))

    def test_an_toan_che_bi_mat(self):
        self.assertEqual(mod.an_toan("TAX_PASSWORD=abc mat_khau: xyz bearer ABCDEF"), "[AN] [AN] [AN]")
        self.assertEqual(mod.an_toan("Dang mo cong thue ..."), "Dang mo cong thue ...")
        self.assertEqual(len(mod.an_toan("x" * 1000)), 400)


def khung_sse(text: str) -> list:
    out = []
    for blok in text.split("\n\n"):
        ten, du_lieu = None, None
        for dong in blok.split("\n"):
            if dong.startswith("event: "):
                ten = dong[7:]
            elif dong.startswith("data: "):
                du_lieu = json.loads(dong[6:])
        if ten:
            out.append({"ten": ten, "du_lieu": du_lieu})
    return out


if __name__ == "__main__":
    unittest.main()
