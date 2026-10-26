"""KY-G5TAY: thuần + PG/HTTP (chỉ chạy PG khi lead cấp KHO_PG_DSN_TEST).

Không Word COM: bản sinh mặc định chỉ DOCX. Ca PDF âm dùng fixture trong
giao dịch hoàn tác, không tuyên bố là bằng chứng PDF/engine vận hành.
"""
from __future__ import annotations

import os
import threading
import unittest
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_crm_ky_ket_http as KYH
import test_crm_kiem_hd_http as KIH
from kho_tri_thuc.giao_dien import crm_g as CG
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.crm_ky_ket import CrmKyKetK2

ROUTE = "/api/crm/giao-ket/doi-chieu/xac-nhan-tay"
LY_DO = "DEMO: đã đối chiếu đầy đủ bản ký với DOCX và kiểm tay các điều khoản."
KY = str(uuid.uuid4())


class G5TayThuan(unittest.TestCase):
    def service(self, result=None):
        c = Mock()
        c.execute.return_value.fetchone.return_value = {"r": {"ket_qua": result or {"ky_id": KY}, "lap_lai": False}}

        @contextmanager
        def tx(dt):
            self.assertEqual(dt, "DANH_TINH_PHIEN")
            yield c

        m = SimpleNamespace(danh_tinh=Mock(return_value="DANH_TINH_PHIEN"), _tx=tx)
        return CrmKyKetK2(SimpleNamespace(mau=m, kho=KYH.Path("kho-gia"))), c

    def test_m0037_vi_tri_37_va_khong_sua_m0036(self):
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 37)
        self.assertIs(PM.PG_MIGRATIONS[36], PM.M0037_CRM_G5_TAY)
        self.assertIs(PM.PG_MIGRATIONS[35], PM.M0036_KY_DOCX)
        self.assertNotIn("crm_g5_kiem_tay", "\n".join(PM.M0036_KY_DOCX))

    def test_sql_quyen_revoke_khoa_va_bien_nhan(self):
        sql = "\n".join(PM.M0037_CRM_G5_TAY)
        for can in ("crm_g5_xac_nhan_tay(p_khoa text, p_h text, p_ky uuid, p_ly_do text)",
                    "crm_g_ghim_quyen", "crm_kiem_dich(p_ky, true)", "FOR UPDATE", "FOR SHARE",
                    "crm_g_bn_tra", "crm_g_bn_ghi", "REVOKE EXECUTE ON FUNCTION master.crm_g5_xac_nhan_tay",
                    "REVOKE ALL ON master.crm_g5_kiem_tay", "crm_g_bat_bien()", "nhat_ky.su_kien"):
            self.assertIn(can, sql)
        command = next(s for s in PM.M0037_CRM_G5_TAY if "FUNCTION master.crm_g5_xac_nhan_tay(" in s)
        self.assertLess(command.index("crm_kiem_dich"), command.index("crm_g_bn_tra"))

    def test_sql_khong_noi_e5_va_khong_tu_duyet_g6(self):
        sql = "\n".join(PM.M0037_CRM_G5_TAY)
        self.assertIn("ALTER TABLE master.crm_g5_kiem_tay ENABLE ROW LEVEL SECURITY", sql)
        self.assertNotRegex(sql, r"ALTER TABLE\s+master\.(?:crm_hd_ky|crm_g5_(?!kiem_tay\b)\w+|crm_kiem_g5_\w+)\b")
        self.assertNotIn("INSERT INTO master.crm_g5_ket_qua", sql)
        self.assertNotIn("crm_kiem_hieu_luc(", sql)
        self.assertIn("s.revision_hien_hanh IS DISTINCT FROM k.revision", sql)
        self.assertIn("k.g3_pdf_sha256 IS NOT NULL", sql)
        self.assertIn("length(btrim(p_ly_do)) NOT BETWEEN 10 AND 1000", sql)

    def test_ly_do_bat_buoc_va_bien_10_1000(self):
        svc, c = self.service()
        for value in (None, "", " " * 20, "ngắn", "a" * 1001, 123,
                      *("123456789" + chr(n) + "lý do" for n in (*range(32), *range(127, 160)))):
            with self.subTest(value=repr(value)[:35]), self.assertRaises(DataError) as cm:
                svc.xac_nhan_g5_tay("KT", ky_id=KY, ly_do=value, khoa="k1")
            self.assertEqual((cm.exception.code, cm.exception.locator), ("CRM_G5_TAY_LY_DO", "ly_do"))
        c.execute.assert_not_called()
        for length in (10, 1000):
            svc.xac_nhan_g5_tay("KT", ky_id=KY, ly_do="a" * length, khoa="k1")
        self.assertEqual(c.execute.call_count, 2)

    def test_sql_ly_do_chan_ky_tu_dieu_khien_o_lenh_trigger_va_bang(self):
        sql = "\n".join(PM.M0037_CRM_G5_TAY)
        self.assertIn("p_ly_do ~ '[[:cntrl:]]'", sql)
        self.assertIn("NEW.ly_do ~ '[[:cntrl:]]'", sql)
        self.assertIn("ly_do !~ '[[:cntrl:]]'", sql)

    def test_dich_vu_gui_dung_danh_tinh_va_digest(self):
        svc, c = self.service()
        self.assertFalse(svc.xac_nhan_g5_tay("KT", ky_id=KY, ly_do=LY_DO, khoa="k1")["lap_lai"])
        sql, args = c.execute.call_args.args
        self.assertIn("master.crm_g5_xac_nhan_tay", sql)
        self.assertEqual((args[0], args[2], args[3]), ("k1", KY, LY_DO))
        self.assertEqual(len(args[1]), 64)
        svc.mau.danh_tinh.assert_called_once_with("KT")

    def route(self, body, svc=None, query=None):
        svc = svc or Mock()
        app = SimpleNamespace(mutation_lock=threading.Lock(), crm_phien=lambda sid: (sid, "KT", False),
                              _crm_db=lambda fn, *args: fn(*args))
        h = KIH._H(ROUTE, body)
        with patch.object(CG, "dich_vu_ky", return_value=svc):
            CG.dieu_huong(h, app, True, ROUTE, query or {})
        return h

    def test_route_post_va_loi_theo_truong(self):
        svc, _ = self.service()
        h = self.route({"ky_id": KY, "khoa": "k1"}, svc)
        self.assertEqual((h.st, h.data.get("truong")), (400, "ly_do"))
        for field, value in (("ky_id", "sai"), ("khoa", "k k")):
            h = self.route({"ky_id": KY, "khoa": "k1", "ly_do": LY_DO, field: value}, svc)
            self.assertEqual((h.st, h.data.get("truong")), (400, field))
        h = self.route({"ky_id": KY, "khoa": "k1", "ly_do": LY_DO}, svc)
        self.assertEqual(h.st, 200)

    def test_route_tu_choi_truong_quyen_query_va_than_sai(self):
        svc = Mock()
        body = {"ky_id": KY, "khoa": "k1", "ly_do": LY_DO}
        for bad in (None, [], {**body, "actor": "CFO"}, {**body, "trang_thai": "KHOP"}, {**body, "la": 1}):
            self.assertIn(self.route(bad, svc).st, (400, 403))
        self.assertEqual(self.route(body, svc, {"mode": ["x"]}).st, 400)
        svc.xac_nhan_g5_tay.assert_not_called()

    def test_route_trang_thai_doi_409(self):
        svc = Mock()
        svc.xac_nhan_g5_tay.side_effect = DataError("CRM_G5_TAY_TRANG_THAI", "Đã đổi")
        self.assertEqual(self.route({"ky_id": KY, "ly_do": LY_DO, "khoa": "k1"}, svc).st, 409)


@unittest.skipUnless(KYH.psycopg is not None and os.environ.get("KHO_PG_DSN_TEST"), "NOT_RUN: thiếu psycopg/KHO_PG_DSN_TEST — lead chạy PG")
class G5TayPg(unittest.TestCase):
    # Chỉ mượn helper; không kế thừa/chạy lại các test của G4/G6.
    _H = KYH.CrmKyKetHttp
    goi, sid, K, ok, loi, get, q = _H.goi, _H.sid, _H.K, _H.ok, _H.loi, _H.get, _H.q
    loai_a, du_an, bao_gia, mau_hieu_luc = _H.loai_a, _H.du_an, _H.bao_gia, _H.mau_hieu_luc
    ky, cap_phan_cong, cap_pham_vi = _H.ky, _H.cap_phan_cong, _H.cap_pham_vi
    g3_dat_that, can_pdf, can_cho_ky = _H.g3_dat_that, _H.can_pdf, _H.can_cho_ky
    chen_ky_tho, _CHEN_KY_THO, _XUAT_GIA = _H.chen_ky_tho, _H._CHEN_KY_THO, _H._XUAT_GIA
    khoa_may, _dung, _dong_ket_noi_app = _H.__dict__["khoa_may"], _H.__dict__["_dung"], _H.__dict__["_dong_ket_noi_app"]
    del _H
    phan_cong = KIH.CrmKiemHttpBanSao.phan_cong
    pham_vi_kiem = KIH.CrmKiemHttpBanSao.pham_vi_kiem
    ma = KIH.CrmKiemHttpBanSao.ma

    @classmethod
    def setUpClass(cls):
        env = patch.dict(os.environ, {"KHO_CRM_WORD_PDF": "0"})
        env.start()
        cls.addClassCleanup(env.stop)
        KYH.CrmKyKetHttp.setUpClass.__func__(cls)

    def test_p00_chuan_bi(self):
        KYH.CrmKyKetHttp.test_k01_dung_ban_soan_va_xuat_that(self)
        self.s["pc"] = self.cap_phan_cong(KYH.BH)
        self.assertTrue(self.q("SELECT relrowsecurity FROM pg_class WHERE oid = 'master.crm_g5_kiem_tay'::regclass"))

    def tao_ky(self, tag, co_sua=True):
        self.can_pdf()
        self.can_cho_ky()
        r = self.ok(KYH.BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None,
            "du_lieu": self.bao_gia(don_vi={"ma": "LO-TAY-" + tag + self.run_id},
                lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "100", "moc_loai": "NGAY", "moc_ngay": KYH.ngay(60)}]), "khoa": self.K("bg-" + tag)})
        a = self.ok(KYH.BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1,
            "mau_phien_ban_id": self.s["pb"], "khoa": self.K("cv-" + tag)})
        sid = a["soan_id"]
        bg = dict(self.get(KYH.BH, "soan/" + sid)["du_lieu"]["bao_gia"])
        bg["fx"] = None
        gt = {"so_hop_dong": "HD-DEMO-TAY-" + tag + self.run_id, "ngay_ky": KYH.ngay(0),
            "ten_hien_thi_demo": "NGƯỜI MUA DEMO", "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(KYH.BH, "soan/luu", {"soan_id": sid, "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-" + tag)})
        x = self.ok(KYH.BH, "soan/xuat", {"soan_id": sid, "expected_revision": 2, "khoa": self.K("x-" + tag)})
        self.assertIsNone(x["pdf_sha256"])
        self.cap_pham_vi(self.s["pc"], soan=sid)
        st, k = self.ky(KYH.BH, {"soan_id": sid, "expected_revision": 2, "expected_xuat_id": x["xuat_id"], "ten_tep": "ban-ky-demo.pdf",
            "ngay_ky": KYH.ngay(0), "co_sua": co_sua, "mo_ta": "DEMO sửa điều khoản" if co_sua else None,
            "khoa": self.K("ky-" + tag)}, KYH.pdf_tong_hop(1, "BAN KY DEMO"))
        self.assertEqual(st, 200, k)
        pc, _ = self.phan_cong(KYH.KT, "CRM_HD_KIEM", sid)
        pv = self.pham_vi_kiem(pc, k["ky_id"])
        return {"ky": k["ky_id"], "hd": a["hop_dong_id"], "soan": sid, "pv": pv, "xuat": x["xuat_id"]}

    def xac_nhan(self, d, login=KYH.KT, **sua):
        body = {"ky_id": d["ky"], "ly_do": LY_DO, "khoa": self.K("tay-" + d["ky"])}
        body.update(sua)
        return self.goi(ROUTE, body, self.sid(login))[:2]

    def luu_g6(self, body):
        st, r = self.goi("/api/crm/giao-ket/kiem/luu", body, self.sid(KYH.KT))[:2]
        if st == 400 and r.get("error") == "CSDL_TU_CHOI":
            # Chỉ dữ liệu DEMO của DB test: gọi cùng service/khóa để traceback
            # hiện SQLSTATE + context gốc, thay vì lớp HTTP che lỗi PostgreSQL.
            CG.dich_vu_kiem(self.app).luu(KYH.KT, **body)
        self.assertEqual(st, 200, (KYH.KT, "giao-ket/kiem/luu", r))
        return r

    def test_p01_hold_kiem_tay_g6_hieu_luc_va_nhat_ky(self):
        d = self.tao_ky("hl")
        self.assertEqual(self.q("SELECT master.crm_kiem_g5_xet(%s, 'VAN_HANH')", (d["ky"],))["chan"], [{"ma": "G5_BAN_SINH_CHI_DOCX"}])
        ma = self.ma("PN_DEMO_A")
        self.assertIsNotNone(ma, "Seed DEMO thiếu mã khách thử G6")
        body = KIH._than_luu(ky_id=d["ky"], doi_tac_id=ma["doi_tac_id"], ma_junsky_id=ma["id"],
            ngay_hieu_luc=KYH.ngay(0), can_cu_ngay="DIEU_KHOAN_HD", trich_dan_ngay=KIH.TRICH_DAN, khoa=self.K("luu-hl"))
        self.luu_g6(body)
        before = self.ok(KYH.KT, "giao-ket/kiem/check", {"ky_id": d["ky"], "expected_revision": 1, "khoa": self.K("check-truoc")})["check"]
        self.assertIn("G5_BAN_SINH_CHI_DOCX", {x["ma"] for x in before["chan"]})
        st, r = self.xac_nhan(d)
        self.assertEqual((st, r.get("loai"), r.get("lap_lai")), (200, "KIEM_TAY", False), r)
        g = self.q("SELECT master.crm_kiem_g5_xet(%s, 'VAN_HANH')", (d["ky"],))
        self.assertEqual((g["trang_thai"], g["chan"], g["loai"]), ("KHOP", [], "KIEM_TAY"))
        self.assertEqual(self.q("SELECT crm_giao_ket FROM master.hop_dong WHERE id = %s", (d["hd"],)), "DA_KY")
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_g5_viec WHERE ky_id = %s", (d["ky"],)), "XONG")
        st, again = self.xac_nhan(d)
        self.assertEqual((st, again["ket_qua_id"], again["lap_lai"]), (200, r["ket_qua_id"], True))
        rows = self.admin.execute("SELECT nguoi, ly_do, sau FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_G5_XAC_NHAN_TAY' AND doi_tuong_id = %s", (d["ky"],)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0][0], rows[0][1]), (KYH.KT, LY_DO))
        self.assertEqual(rows[0][2]["xac_nhan_luc"], r["xac_nhan_luc"])
        body.update(expected_revision=1, khoa=self.K("luu-sau-tay"))
        self.assertEqual(self.luu_g6(body)["revision"], 2)
        c = self.ok(KYH.KT, "giao-ket/kiem/check", {"ky_id": d["ky"], "expected_revision": 2, "khoa": self.K("check-sau")})["check"]
        self.assertEqual((c["ket_luan"], c["chan"]), ("DU_DIEU_KIEN", []))
        hl = self.ok(KYH.KT, "giao-ket/kiem/hieu-luc", {"ky_id": d["ky"], "expected_revision": 2,
            "check_id": c["check_id"], "do_thi_sha256": c["do_thi_sha256"], "khoa": self.K("hl")})
        self.assertEqual((hl["trang_thai"], hl["hieu_luc"]["g5_che_do"]), ("HIEU_LUC", "VAN_HANH"))

    def test_p02_ly_do_bat_buoc(self):
        d = self.tao_ky("lydo", False)
        for value in (None, "", "ngắn", "a" * 1001):
            st, e = self.xac_nhan(d, ly_do=value)
            self.assertEqual((st, e.get("truong")), (400, "ly_do"))
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_g5_kiem_tay WHERE ky_id = %s", (d["ky"],)), 0)
        self.assertEqual(self.xac_nhan(d)[0], 200)  # khai Không vẫn HOLD, kiểm tay được

    def test_p03_vai_ban_hang_ngoai_pn_va_thu_hoi_truoc_replay(self):
        d = self.tao_ky("quyen")
        for login in (KYH.BH, KYH.KT_NO_CRM, KYH.CFO_B):
            self.assertIn(self.xac_nhan(d, login)[0], (403, 404))
        self.assertEqual(self.xac_nhan(d)[0], 200)
        self.admin.execute("UPDATE master.crm_kiem_pham_vi SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST', thu_hoi_ly_do = 'DEMO thu hồi' WHERE id = %s", (d["pv"],))
        self.assertEqual(self.xac_nhan(d)[0], 403)

    def test_p04_khoa_khac_khong_ghi_de_ket_qua(self):
        d = self.tao_ky("lap")
        self.assertEqual(self.xac_nhan(d)[0], 200)
        st, e = self.xac_nhan(d, khoa=self.K("tay-moi"))
        self.assertEqual((st, e.get("error")), (409, "CRM_G5_TAY_TRANG_THAI"))
        st, e = self.xac_nhan(d, ly_do=LY_DO + " Thay đổi.")
        self.assertEqual((st, e.get("error")), (409, "CRM_G_IDEMPOTENCY_KHAC"))

    def test_p05_pdf_bi_tu_choi_truc_tiep(self):
        # Fixture âm như k09: chèn bản ký trên PDF giả chỉ trong transaction hoàn tác.
        self.can_cho_ky()
        sid, xid = self.s["soan"], self.s["xuat"]
        pc, _ = self.phan_cong(KYH.KT, "CRM_HD_KIEM", sid)
        svc = CG.dich_vu_ky(self.app)
        with self.assertRaises(KYH._HoanTac):
            with svc.mau._tx(svc.mau.danh_tinh(KYH.KT)) as c:
                # Dùng HĐ Chờ ký ban đầu (chưa ký), không sửa bản ký bất biến đã có.
                xid_gia = str(c.execute(self._XUAT_GIA, ("c" * 64, 100, "PDF_DAT", xid)).fetchone()["id"])
                c.execute(self._CHEN_KY_THO, {"soan": sid, "xuat": xid_gia, "rev": None, "docx": None,
                    "pdf_xuat": True, "pdf_sha": None, "pdf_len": None, "ky": "a" * 64})
                ky = c.execute("SELECT id FROM master.crm_hd_ky WHERE soan_id = %s", (sid,)).fetchone()["id"]
                c.execute("""INSERT INTO master.crm_hd_ky_g5 (ky_id, phap_nhan_id, trang_thai, ly_do)
                    SELECT id, phap_nhan_id, 'NOT_SELECTED', 'CHUA_AP_DUNG_CHON_MAU' FROM master.crm_hd_ky WHERE id = %s""", (ky,))
                c.execute("UPDATE master.crm_hd_soan SET trang_thai = 'DA_KY' WHERE id = %s", (sid,))
                c.execute("UPDATE master.hop_dong SET trang_thai = 'DA_KY', crm_giao_ket = 'DA_KY' WHERE id = %s", (self.s["hd"],))
                c.execute("""INSERT INTO master.crm_kiem_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, ky_id, du_an_id, cap_boi)
                    SELECT %s, k.phap_nhan_id, k.hop_dong_id, k.id, h.du_an_id, 'TEST' FROM master.crm_hd_ky k
                    JOIN master.hop_dong h ON h.id = k.hop_dong_id WHERE k.id = %s""", (pc, ky))
                self.assertNotIn({"ma": "G5_BAN_SINH_CHI_DOCX"}, c.execute("SELECT master.crm_kiem_g5_xet(%s, 'VAN_HANH') AS g", (ky,)).fetchone()["g"]["chan"])
                with self.assertRaises(KYH.psycopg.Error) as cm:
                    with c.transaction():
                        c.execute("SELECT master.crm_g5_xac_nhan_tay(%s, %s, %s, %s)", (self.K("pdf-am-tay"), "a" * 64, ky, LY_DO))
                self.assertIn("CRM_G5_TAY_TRANG_THAI", str(cm.exception))
                raise KYH._HoanTac

    def test_p06_tach_nhiem_va_bat_bien(self):
        d = self.tao_ky("tach")
        pc, _ = self.phan_cong(KYH.BH, "CRM_HD_KIEM", d["soan"])
        self.pham_vi_kiem(pc, d["ky"])
        svc = CG.dich_vu_ky(self.app)
        with self.assertRaises(KYH._HoanTac):
            with svc.mau._tx(svc.mau.danh_tinh(KYH.BH)) as c:
                # Vai KT tạm chỉ để tới được guard tách nhiệm; rollback toàn bộ.
                c.execute("UPDATE master.nguoi_dung SET vai_tro = 'KE_TOAN' WHERE dang_nhap = %s", (KYH.BH,))
                with self.assertRaises(KYH.psycopg.Error) as cm:
                    with c.transaction():
                        c.execute("SELECT master.crm_g5_xac_nhan_tay(%s, %s, %s, %s)", (self.K("cung-nguoi"), "a" * 64, d["ky"], LY_DO))
                self.assertIn("CRM_G_CUNG_NGUOI", str(cm.exception))
                raise KYH._HoanTac
        self.assertEqual(self.xac_nhan(d)[0], 200)
        with self.assertRaises(KYH.psycopg.Error) as cm:
            with self.admin.transaction():
                self.admin.execute("UPDATE master.crm_g5_kiem_tay SET ly_do = 'DEMO sửa trái phép' WHERE ky_id = %s", (d["ky"],))
        self.assertIn("CRM_G_BAT_BIEN", str(cm.exception))

    def test_p07_kiem_tay_truoc_khi_mo_ho_so_g6(self):
        d = self.tao_ky("tay-truoc")
        self.assertEqual(self.xac_nhan(d)[0], 200)
        ma = self.ma("PN_DEMO_A")
        self.assertIsNotNone(ma, "Seed DEMO thiếu mã khách thử G6")
        r = self.luu_g6(KIH._than_luu(ky_id=d["ky"], doi_tac_id=ma["doi_tac_id"], ma_junsky_id=ma["id"],
            ngay_hieu_luc=KYH.ngay(0), can_cu_ngay="DIEU_KHOAN_HD", trich_dan_ngay=KIH.TRICH_DAN, khoa=self.K("luu-tay-truoc")))
        self.assertEqual(r["revision"], 1)
        c = self.ok(KYH.KT, "giao-ket/kiem/check", {"ky_id": d["ky"], "expected_revision": 1, "khoa": self.K("check-tay-truoc")})["check"]
        self.assertEqual((c["ket_luan"], c["chan"]), ("DU_DIEU_KIEN", []))
        hl = self.ok(KYH.KT, "giao-ket/kiem/hieu-luc", {"ky_id": d["ky"], "expected_revision": 1,
            "check_id": c["check_id"], "do_thi_sha256": c["do_thi_sha256"], "khoa": self.K("hl-tay-truoc")})
        self.assertEqual(hl["trang_thai"], "HIEU_LUC")

    def test_p08_sql_truc_tiep_chan_ky_tu_dieu_khien(self):
        d = self.tao_ky("ctrl")
        svc = CG.dich_vu_ky(self.app)
        with svc.mau._tx(svc.mau.danh_tinh(KYH.KT)) as c:
            for n in (9, 10, 13, 31, 127):
                ly_do = "DEMO lý do" + chr(n) + "kiểm tay"
                with self.subTest(ma=n, duong="lenh"), self.assertRaises(KYH.psycopg.Error) as cm:
                    with c.transaction():
                        c.execute("SELECT master.crm_g5_xac_nhan_tay(%s, %s, %s, %s)",
                                  (self.K("ctrl-" + str(n)), "a" * 64, d["ky"], ly_do))
                self.assertIn("CRM_G5_TAY_LY_DO", str(cm.exception))
                with self.subTest(ma=n, duong="insert"), self.assertRaises(KYH.psycopg.Error) as cm:
                    with c.transaction():
                        c.execute("""INSERT INTO master.crm_g5_kiem_tay
                            (ky_id, phap_nhan_id, soan_rev_id, ky_pdf_sha256, g3_docx_sha256, ly_do, xac_nhan_boi)
                            SELECT id, phap_nhan_id, soan_rev_id, ky_pdf_sha256, g3_docx_sha256, %s, master.ktt_danh_tinh()
                            FROM master.crm_hd_ky WHERE id = %s""", (ly_do, d["ky"]))
                self.assertIn("CRM_G5_TAY_LY_DO", str(cm.exception))
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_g5_kiem_tay WHERE ky_id = %s", (d["ky"],)), 0)


if __name__ == "__main__":
    unittest.main()
