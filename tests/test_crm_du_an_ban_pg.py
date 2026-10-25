"""DA-1 — CRM · Dự án đang bán trên PostgreSQL THẬT (CSDL DEMO riêng, schema ≥ 31).

Điều kiện: biến môi trường KTT_DU_AN_BAN_KET_NOI = tệp ket-noi.local.json của CSDL DEMO (kho_crm_demo*, vd kho_crm_demo_lt_p8793 do
tools/mo_demo_worktree.ps1 -CsdlRieng tạo và đã chạy bước chuẩn bị/seed). Thiếu → SKIP (NOT_VERIFIED, KHÔNG PASS). Không in DSN.
Dữ liệu: mỗi lần chạy tạo một dự án kế toán DEMO MỚI (mã DA_DEMO_KT_<run>) rồi đi hết luồng bằng service thật (kết nối chủ bảng + login ứng
dụng, đúng như máy chủ) — giữ lại làm bằng chứng, không xóa. Kiểm bất biến bằng lệnh trực tiếp trong giao dịch bị CSDL từ chối (không để lại gì).

Luồng (t01…t12): bật bán + idempotent + quyền; sửa → phiên bản mới (CAS, không đổi); phí; lô/căn (lịch sử, CAS lần); G7 áp dụng ngay (bỏ CFO,
QD-20261025-07) và MỌI chỗ đọc bộ chuẩn hiệu lực đọc được (crm_g_chuan_doc, tính báo giá, truy vấn G6A crm_kiem_g7); phiên bản G7 CFO đã duyệt
cũ giữ nguyên nghĩa; ảnh chụp mặc định cho báo giá; ngừng/mở bán; lịch sử; bất biến + vai ứng dụng không đọc bảng mới; seed DEMO idempotent.
"""

from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_du_an_ban as D
from kho_tri_thuc.k2 import sql_crm_kiem_hd as SK
from kho_tri_thuc.k2.crm_giao_ket import CrmGiaoKetK2
from kho_tri_thuc.k2.crm_mau import CrmMauK2

ENV = "KTT_DU_AN_BAN_KET_NOI"
BH, KT, XEM, KT_B, KT_NO_CRM, CFO = ("MO_PHONG_BAN_HANG", "MO_PHONG_KT_A", "MO_PHONG_XEM_A", "MO_PHONG_KT_B", "MO_PHONG_KT_KHONG_CRM_A",
                                     "MO_PHONG_CRM_G_CFO_A")


def _g7(*pt):
    moc = ("KY_HD", "SAU_KY_90", "BAN_GIAO")
    return [{"lan": str(i + 1), "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": p, "moc_loai": "SU_KIEN", "moc_su_kien": moc[i]} for i, p in enumerate(pt)]


DONG1, DONG2 = _g7("30", "40", "30"), _g7("20", "50", "30")
PHI = [{"ten": "Phí bảo trì kiểm thử DEMO", "loai": "BAO_TRI", "muc": "0.5", "don_vi_tinh": "M2_NAM", "tien_te": "USD", "co_so_tinh": "Diện tích"},
       {"ten": "Phí đấu nối kiểm thử DEMO", "loai": "KHAC", "muc": "5000000", "don_vi_tinh": "LAN", "tien_te": "VND"}]


def _ma_pg(exc) -> str:
    return ((getattr(getattr(exc, "diag", None), "message_primary", "") or "").split(":", 1)[0]) or type(exc).__name__


@unittest.skipUnless(os.environ.get(ENV), "NOT_VERIFIED: thiếu KTT_DU_AN_BAN_KET_NOI — PostgreSQL thật không chạy (skip, KHÔNG PASS)")
class DuAnBanPostgres(unittest.TestCase):
    s: dict = {}

    @classmethod
    def setUpClass(cls):
        from psycopg.rows import dict_row

        from kho_tri_thuc.giao_dien.server import LocalApp
        from kho_tri_thuc.k2.crm_khoi_dong import chuan_hoa_dsn, doc_ket_noi, nap_driver
        kn = doc_ket_noi(Path(os.environ[ENV]))  # chỉ CSDL DEMO kho_crm_demo*; không in DSN
        cls.psycopg = psycopg = nap_driver()
        cls.db = LocalApp._crm_db  # cùng ánh xạ lỗi CSDL → DataError(mã) của máy chủ
        cls.admin = psycopg.connect(chuan_hoa_dsn(kn["admin_dsn"])["conninfo"], autocommit=True, row_factory=dict_row)
        cls.admin_t = psycopg.connect(chuan_hoa_dsn(kn["admin_dsn"])["conninfo"], autocommit=True)  # tuple row cho seed
        cls.app = psycopg.connect(chuan_hoa_dsn(kn["app_dsn"])["conninfo"], autocommit=True, row_factory=dict_row)
        for c in (cls.admin, cls.admin_t, cls.app):
            cls.addClassCleanup(c.close)
        cls.schema = cls.admin.execute("SELECT max(version) AS v FROM master.schema_migrations").fetchone()["v"]
        if cls.schema < 31:
            return
        cls.mau = CrmMauK2(cls.app, Path(tempfile.mkdtemp(prefix="ktt_da1_pg_")), conn_tin_cay=cls.admin)
        cls.dv = D.CrmDuAnBanK2(cls.mau)
        cls.gk = CrmGiaoKetK2(cls.mau)
        cls.run = uuid.uuid4().hex[:8].upper()
        cls.hom_nay = cls.mau.hom_nay()
        q = cls.admin.execute
        cls.pn = q("SELECT id::text AS id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'").fetchone()["id"]
        cls.lh = q("""SELECT id::text AS id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND ma = 'DT-KCN-THUE-DAT-DEMO'
                      AND valid_to IS NULL""", (cls.pn,)).fetchone()["id"]
        cls.du_an, cls.du_an_2 = (q("INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s, %s, %s) RETURNING id::text AS id",
                                    (cls.pn, f"DA_DEMO_KT_{cls.run}{x}", f"Dự án kiểm thử DA-1 DEMO {cls.run}{x}")).fetchone()["id"] for x in ("", "B"))
        cls.gd = f"GD{cls.run}"

    def setUp(self):
        if self.schema < 31:
            self.fail(f"NOT_VERIFIED: CSDL ở schema {self.schema} (< 31) — chạy bước chuẩn bị DEMO của worktree trước")

    # ------------------------------------------------------------------ helpers
    def K(self, x):
        return f"da1-{self.run}-{x}"

    def ma(self, fn, *a, **kw):
        try:
            self.db(lambda: fn(*a, **kw))
        except DataError as exc:
            return exc.code
        self.fail("không bị từ chối")

    def can(self, *khoa):
        thieu = [k for k in khoa if k not in self.s]
        if thieu:
            self.fail("NOT_VERIFIED: bước trước chưa đạt (thiếu " + ", ".join(thieu) + ")")

    def tt(self, **sua):
        return {"vi_tri": "Khu kiểm thử DEMO", "mo_ta": "Dự án kiểm thử DA-1 — DEMO", "don_gia_niem_yet": "120", "tien_te": "USD", "loai_hinh_id": self.lh,
                "co_so_thue": "NET", "vat_phan_tram": "10", "giai_doan_g7": self.gd, **sua}

    def chuan_doc(self, gd, ngay):
        return self.admin.execute("SELECT master.crm_g_chuan_doc(%s::uuid, %s, %s::date) AS r", (self.du_an, gd, ngay)).fetchone()["r"]

    def pb_g7(self, gd):
        return self.admin.execute("""SELECT v.id::text AS id, v.phien_ban, v.trang_thai, v.valid_from, v.valid_to, v.duyet_boi FROM master.crm_bo_chuan_phien_ban v
                                     JOIN master.crm_bo_chuan b ON b.id = v.bo_chuan_id WHERE b.du_an_id = %s AND b.giai_doan = %s ORDER BY v.phien_ban""",
                                  (self.du_an, gd)).fetchall()

    # ------------------------------------------------------------------ luồng
    def test_t01_bat_ban_idempotent_quyen(self):
        r = self.db(lambda: self.dv.bat_ban(BH, du_an_id=self.du_an, thong_tin=self.tt(), phi=PHI, khoa=self.K("bb")))
        self.assertEqual((r["phien_ban"], r["dang_ban"], r["lap_lai"], r["hieu_luc_tu"]), (1, True, False, self.hom_nay.isoformat()))
        r2 = self.db(lambda: self.dv.bat_ban(BH, du_an_id=self.du_an, thong_tin=self.tt(don_gia_niem_yet="120.0"), phi=PHI, khoa=self.K("bb")))
        self.assertEqual((r2["lap_lai"], r2["da_ban_id"], r2["phien_ban_id"]), (True, r["da_ban_id"], r["phien_ban_id"]))  # cùng yêu cầu (đã chuẩn hóa)
        self.assertEqual(self.ma(self.dv.bat_ban, BH, du_an_id=self.du_an, thong_tin=self.tt(don_gia_niem_yet="121"), khoa=self.K("bb")),
                         "CRM_G_IDEMPOTENCY_KHAC")
        self.assertEqual(self.ma(self.dv.bat_ban, BH, du_an_id=self.du_an, thong_tin=self.tt(), khoa=self.K("bb2")), "CRM_DA_DA_CO")
        self.assertEqual(self.ma(self.dv.bat_ban, XEM, du_an_id=self.du_an_2, thong_tin=self.tt(), khoa=self.K("x")), "CRM_G_KHONG_CO_QUYEN")
        self.assertEqual(self.ma(self.dv.bat_ban, "MO_PHONG_CFO", du_an_id=self.du_an_2, thong_tin=self.tt(), khoa=self.K("x")), "CRM_G_KHONG_CO_QUYEN")
        self.assertEqual(self.ma(self.dv.bat_ban, KT_B, du_an_id=self.du_an_2, thong_tin=self.tt(), khoa=self.K("x")), "CRM_G_KHONG_THAY")
        self.assertEqual(self.ma(self.dv.bat_ban, KT_NO_CRM, du_an_id=self.du_an_2, thong_tin=self.tt(), khoa=self.K("x")), "CRM_G_KHONG_THAY")
        self.assertEqual(self.ma(self.dv.chi_tiet, KT_B, r["da_ban_id"]), "CRM_G_KHONG_THAY")
        self.assertEqual(self.db(lambda: self.dv.chi_tiet(XEM, r["da_ban_id"]))["duoc_sua"], False)  # XEM đọc được, không sửa được
        self.s["da"], self.s["pb1"] = r["da_ban_id"], r["phien_ban_id"]

    def test_t02_cap_nhat_phien_ban_moi(self):
        self.can("da")
        da = self.s["da"]
        r = self.db(lambda: self.dv.cap_nhat(KT, da_ban_id=da, expected_phien_ban=1, thong_tin=self.tt(don_gia_niem_yet="125.5"), ly_do="giá mới DEMO",
                                             khoa=self.K("cn")))
        self.assertEqual((r["phien_ban"], r["khac"], r["khong_doi"], r["dong_phien_ban_truoc"]), (2, ["don_gia_niem_yet"], False, self.s["pb1"]))
        rows = self.admin.execute("SELECT phien_ban, hieu_luc_tu, hieu_luc_den FROM master.crm_da_ban_phien_ban WHERE da_ban_id = %s ORDER BY phien_ban",
                                  (da,)).fetchall()
        self.assertEqual([(x["phien_ban"], x["hieu_luc_den"]) for x in rows], [(1, self.hom_nay), (2, None)])  # đóng cũ tại hôm nay, mới đang mở
        self.assertEqual(self.ma(self.dv.cap_nhat, KT, da_ban_id=da, expected_phien_ban=1, thong_tin=self.tt(), khoa=self.K("cn2")), "CRM_DA_PHIEN_BAN_CU")
        k = self.db(lambda: self.dv.cap_nhat(BH, da_ban_id=da, expected_phien_ban=2, thong_tin=self.tt(don_gia_niem_yet="125.50"), khoa=self.K("cn3")))
        self.assertEqual((k["khong_doi"], k["phien_ban"]), (True, 2))
        self.assertEqual(self.ma(self.dv.cap_nhat, BH, da_ban_id=da, expected_phien_ban=2, thong_tin=self.tt(loai_hinh_id=str(uuid.uuid4())),
                                 khoa=self.K("cn4")), "CRM_DA_LOAI_HINH_SAI")

    def test_t03_phi(self):
        self.can("da")
        da = self.s["da"]
        r = self.db(lambda: self.dv.sua_phi(BH, da_ban_id=da, expected_phien_ban=2, phi=PHI + [{"ten": "Phí sử dụng kiểm thử DEMO", "loai": "SU_DUNG",
                                                                                             "muc": "0.05", "don_vi_tinh": "M2_THANG", "tien_te": "USD"}],
                                            khoa=self.K("phi")))
        self.assertEqual((r["phien_ban"], r["khac"]), (3, ["phi"]))
        ac = self.db(lambda: self.dv.chi_tiet(BH, da))["anh_chup"]
        self.assertEqual((ac["don_gia"], len(ac["phi"]), {p["don_vi_tinh"] for p in ac["phi"]}), ("125.5", 3, {"M2_NAM", "LAN", "M2_THANG"}))
        self.s["pb3"] = r["phien_ban_id"]

    def test_t04_lo_lich_su(self):
        self.can("da")
        da = self.s["da"]
        r = self.db(lambda: self.dv.ghi_lo(BH, da_ban_id=da, lo=[{"ma": f"L1-{self.run}", "dien_tich": "15000"},
                                                                {"ma": f"L2-{self.run}", "dien_tich": "820.25", "trang_thai": "GIU_CHO"}], khoa=self.K("lo")))
        self.assertEqual((r["moi"], r["doi"], r["giu"]), (2, 0, 0))
        r = self.db(lambda: self.dv.ghi_lo(BH, da_ban_id=da, lo=[{"ma": f"l1-{self.run}".lower(), "dien_tich": "15000", "trang_thai": "DA_BAN", "expected_lan": 1},
                                                                {"ma": f"L2-{self.run}", "dien_tich": "820.25", "trang_thai": "GIU_CHO", "expected_lan": 1}],
                                           ly_do="đã ký DEMO", khoa=self.K("lo2")))
        self.assertEqual((r["moi"], r["doi"], r["giu"]), (0, 1, 1))
        self.assertEqual(self.ma(self.dv.ghi_lo, BH, da_ban_id=da, lo=[{"ma": f"L1-{self.run}", "dien_tich": "1", "expected_lan": 1}], khoa=self.K("lo3")),
                         "CRM_DA_LO_LAN_CU")
        self.assertEqual(self.ma(self.dv.ghi_lo, BH, da_ban_id=da, lo=[{"ma": f"L9-{self.run}", "dien_tich": "1", "expected_lan": 1}], khoa=self.K("lo4")),
                         "CRM_DA_LO_LAN_CU")
        ls = self.db(lambda: self.dv.lich_su(BH, da))["lo"]
        l1 = next(x for x in ls if x["ma"] == f"L1-{self.run}")
        self.assertEqual([(h["lan"], h["trang_thai"]) for h in l1["lich_su"]], [(1, "CON_TRONG"), (2, "DA_BAN")])  # đổi = dòng lịch sử, không ghi đè

    def test_t05_g7_ap_dung_ngay_moi_cho_doc_thay(self):
        self.can("da")
        g = self.db(lambda: self.dv.ap_dung_tien_do(BH, du_an_id=self.du_an, dong=DONG1, khoa=self.K("g7")))  # giai đoạn mặc định = của dự án
        self.assertEqual((g["giai_doan"], g["trang_thai"], g["valid_from"], g["can_cu"], g["khong_doi"]),
                         (self.gd, "HIEU_LUC", self.hom_nay.isoformat(), "QD-20261025-07", False))
        x = self.admin.execute("SELECT can_cu, ap_dung_boi, hieu_luc_tu FROM master.crm_bo_chuan_ap_dung WHERE phien_ban_id = %s", (g["phien_ban_id"],)).fetchone()
        self.assertEqual((x["can_cu"], x["ap_dung_boi"], x["hieu_luc_tu"]), ("QD-20261025-07", BH, self.hom_nay))
        nk = self.admin.execute("""SELECT loai, can_cu, ly_do FROM nhat_ky.su_kien WHERE doi_tuong_bang = 'master.crm_bo_chuan_phien_ban'
                                   AND doi_tuong_id = %s AND hanh_dong = 'CRM_CHUAN_AP_DUNG'""", (g["phien_ban_id"],)).fetchone()
        self.assertEqual((nk["loai"], nk["can_cu"]), ("QUYET_DINH", {"quyet_dinh": "QD-20261025-07"}))
        self.assertIn("bỏ bước CFO duyệt", nk["ly_do"])
        self.assertEqual(self.pb_g7(self.gd)[0]["duyet_boi"], None)  # không giả là CFO đã duyệt
        # (1) hàm đọc G7 duy nhất
        self.assertEqual(self.chuan_doc(self.gd, self.hom_nay)["version"]["id"], g["phien_ban_id"])
        self.assertEqual(self.chuan_doc(self.gd, self.hom_nay - timedelta(days=1))["trang_thai"], "CHUA_CO")
        self.assertEqual(self.db(lambda: self.mau.doc_bo_chuan(BH, self.du_an, self.gd))["version"]["id"], g["phien_ban_id"])
        # (2) báo giá (giao kết): tính thử nguồn lịch theo dự án đọc phiên bản áp dụng ngay
        bg = {"loai_hinh_id": self.lh, "du_an_id": self.du_an, "giai_doan_g7": self.gd, "nguon_lich": "DU_AN",
              "gia": {"tien_te": "VND", "don_gia": "1000", "dien_tich": "100", "co_so_thue": "NET"},
              "lich": [{"gia_tri_nhap": p + "%", "moc_loai": "SU_KIEN", "moc_su_kien": m} for p, m in (("30", "KY_HD"), ("40", "SAU_KY_90"), ("30", "BAN_GIAO"))]}
        t = self.db(lambda: self.gk.xem_truoc(BH, du_lieu=bg))["tinh"]
        self.assertEqual(([c["ma"] for c in t["canh_bao"] if c["ma"] == "THIEU_G7"], t["g7_lech"]), ([], []))
        bg["lich"][0]["gia_tri_nhap"], bg["lich"][1]["gia_tri_nhap"] = "20%", "50%"
        self.assertIn("LECH_G7_TY_LE", {c["ma"] for c in self.db(lambda: self.gk.xem_truoc(BH, du_lieu=bg))["tinh"]["g7_lech"]})
        # (3) bước kiểm G6A (crm_kiem_g7, M0025): đúng truy vấn chọn bộ chuẩn hiệu lực theo ngày ký, lấy nguyên văn từ M0025
        f = next(s for s in SK.CRM_G6A_SQL if "FUNCTION master.crm_kiem_g7(" in s)
        i = f.index("SELECT v.* INTO pb FROM master.crm_bo_chuan b")
        cau = (f[i:f.index("LIMIT 1;", i) + len("LIMIT 1")].replace("SELECT v.* INTO pb ", "SELECT v.id::text AS id ")
               .replace("k.phap_nhan_id", "%(pn)s::uuid").replace("(v_bg ->> 'du_an_id')", "%(da)s").replace("(v_bg ->> 'giai_doan_g7')", "%(gd)s")
               .replace("k.ngay_ky", "%(ngay)s::date"))
        self.s["g6a"] = lambda gd, ngay: (self.admin.execute(cau, {"pn": self.pn, "da": self.du_an, "gd": gd, "ngay": ngay}).fetchone() or {}).get("id")
        self.assertEqual(self.s["g6a"](self.gd, self.hom_nay), g["phien_ban_id"])
        # cùng dòng → không tạo phiên bản; dòng khác CÙNG NGÀY → phiên bản mới, phiên bản cũ thành khoảng rỗng, mọi chỗ đọc chọn phiên bản mới
        self.assertTrue(self.db(lambda: self.dv.ap_dung_tien_do(BH, du_an_id=self.du_an, giai_doan=self.gd, dong=DONG1, khoa=self.K("g7b")))["khong_doi"])
        g2 = self.db(lambda: self.dv.ap_dung_tien_do(KT, du_an_id=self.du_an, giai_doan=self.gd, dong=DONG2, khoa=self.K("g7c")))
        v = self.pb_g7(self.gd)
        self.assertEqual([(x["phien_ban"], x["valid_from"], x["valid_to"]) for x in v], [(1, self.hom_nay, self.hom_nay), (2, self.hom_nay, None)])
        self.assertEqual((self.chuan_doc(self.gd, self.hom_nay)["version"]["id"], self.s["g6a"](self.gd, self.hom_nay)), (g2["phien_ban_id"],) * 2)
        self.assertEqual(self.ma(self.dv.ap_dung_tien_do, XEM, du_an_id=self.du_an, dong=DONG1, khoa=self.K("g7x")), "CRM_G_KHONG_CO_QUYEN")
        self.assertEqual(self.ma(self.dv.ap_dung_tien_do, BH, du_an_id=self.du_an_2, giai_doan="GD1", dong=DONG1, khoa=self.K("g7y")), "CRM_DA_CHUA_BAT_BAN")
        self.s["g7"] = g2["phien_ban_id"]

    def test_t06_g7_cfo_cu_giu_nguyen_nghia(self):
        self.can("da")
        m = self.mau

        def tok(pb):
            return next(x["token"] for x in self.db(lambda: m.danh_sach_bo_chuan(KT))["phien_ban"] if x["id"] == pb)

        def cfo_duyet(gd, valid_from):
            r = self.db(lambda: m.lap_bo_chuan(KT, du_an_id=self.du_an, giai_doan=gd, dong=DONG1, khoa=self.K("lap" + gd)))
            self.db(lambda: m.gui_duyet_bo_chuan(KT, version_id=r["phien_ban_id"], expected_graph=tok(r["phien_ban_id"]), khoa=self.K("gui" + gd)))
            self.db(lambda: m.duyet_bo_chuan(CFO, version_id=r["phien_ban_id"], valid_from=valid_from.isoformat(), expected_graph=tok(r["phien_ban_id"]),
                                             khoa=self.K("duyet" + gd)))
            return r["phien_ban_id"]
        gd = f"CFO{self.run}"
        cfo = cfo_duyet(gd, self.hom_nay - timedelta(days=5))
        moi = self.db(lambda: self.dv.ap_dung_tien_do(BH, du_an_id=self.du_an, giai_doan=gd, dong=DONG2, khoa=self.K("g7cfo")))["phien_ban_id"]
        v = {x["id"]: x for x in self.pb_g7(gd)}
        self.assertEqual((v[cfo]["trang_thai"], v[cfo]["duyet_boi"], v[cfo]["valid_from"], v[cfo]["valid_to"]),
                         ("HIEU_LUC", CFO, self.hom_nay - timedelta(days=5), self.hom_nay))  # nghĩa cũ giữ nguyên, chỉ đóng tại hôm nay
        self.assertEqual(self.chuan_doc(gd, self.hom_nay - timedelta(days=1))["version"]["id"], cfo)  # quá khứ vẫn là bản CFO đã duyệt
        self.assertEqual(self.chuan_doc(gd, self.hom_nay)["version"]["id"], moi)
        self.assertEqual((self.s["g6a"](gd, self.hom_nay - timedelta(days=1)) if "g6a" in self.s else cfo), cfo)
        nguon = {x["id"]: x["nguon_hieu_luc"] for x in self.db(lambda: m.danh_sach_bo_chuan(KT))["phien_ban"]}
        self.assertEqual((nguon[cfo], nguon[moi]), ("CFO_DUYET", "AP_DUNG_NGAY"))
        tl = f"CFT{self.run}"
        cfo_duyet(tl, self.hom_nay + timedelta(days=5))  # CFO duyệt hiệu lực TƯƠNG LAI → bán hàng không áp dụng chồng
        self.assertEqual(self.ma(self.dv.ap_dung_tien_do, BH, du_an_id=self.du_an, giai_doan=tl, dong=DONG2, khoa=self.K("g7tl")), "CRM_G_HIEU_LUC_CHONG")

    def test_t07_anh_chup_mac_dinh(self):
        self.can("da", "g7")
        a = self.db(lambda: self.dv.anh_chup_mac_dinh(BH, self.du_an))
        self.assertEqual((a["kieu"], a["trang_thai"], a["phien_ban"]["so"], a["don_gia"], a["tien_te"], a["thue"], a["giai_doan_g7"]),
                         ("CRM_DA_ANH_CHUP_V1", "DANG_BAN", 3, "125.5", "USD", {"co_so_thue": "NET", "vat_phan_tram": "10"}, self.gd))
        self.assertEqual((a["loai_hinh"]["id"], a["loai_hinh"]["con_hieu_luc"], len(a["phi"]), len(a["lo"])), (self.lh, True, 3, 2))
        self.assertEqual((a["bo_chuan"]["version"]["id"], a["bo_chuan"]["nguon"], len(a["bo_chuan"]["rows"])), (self.s["g7"], "AP_DUNG_NGAY", 3))
        self.assertIn(self.gd, a["giai_doan_co_chuan"])
        self.assertEqual(self.db(lambda: self.dv.anh_chup_mac_dinh(BH, self.du_an, self.hom_nay.isoformat()))["anh_chup_sha256"], a["anh_chup_sha256"])
        self.assertEqual(self.db(lambda: self.dv.anh_chup_mac_dinh(BH, self.du_an, (self.hom_nay - timedelta(days=1)).isoformat()))["trang_thai"],
                         "CHUA_CO_PHIEN_BAN")
        self.assertEqual(self.db(lambda: self.dv.anh_chup_mac_dinh(BH, self.du_an_2))["trang_thai"], "CHUA_BAT_BAN")
        self.assertEqual(self.ma(self.dv.anh_chup_mac_dinh, KT_B, self.du_an), "CRM_G_KHONG_THAY")
        p1 = self.db(lambda: self.dv.chi_tiet(BH, self.s["da"], phien_ban="1"))["anh_chup"]
        self.assertEqual((p1["phien_ban"]["so"], p1["don_gia"], len(p1["phi"])), (1, "120", 2))  # phiên bản cũ đọc đúng nội dung cũ
        self.s["sha"] = a["anh_chup_sha256"]

    def test_t08_ngung_mo_ban(self):
        self.can("da")
        da = self.s["da"]
        self.assertEqual(self.ma(self.dv.ngung_ban, BH, da_ban_id=da, expected_phien_ban=3, ly_do=None, khoa=self.K("ng0")), "CRM_DA_THIEU_LY_DO")
        r = self.db(lambda: self.dv.ngung_ban(BH, da_ban_id=da, expected_phien_ban=3, ly_do="Tạm dừng kiểm thử DEMO", khoa=self.K("ng")))
        self.assertEqual((r["phien_ban"], r["dang_ban"]), (4, False))
        self.assertNotIn(da, [x["da_ban_id"] for x in self.db(lambda: self.dv.danh_sach(BH, dang_ban=True))["du_an_ban"]])
        self.assertIn(da, [x["da_ban_id"] for x in self.db(lambda: self.dv.danh_sach(BH))["du_an_ban"]])
        self.assertEqual(self.ma(self.dv.ngung_ban, BH, da_ban_id=da, expected_phien_ban=4, ly_do="x", khoa=self.K("ng2")), "CRM_DA_TRANG_THAI")
        r = self.db(lambda: self.dv.mo_ban_lai(BH, da_ban_id=da, expected_phien_ban=4, khoa=self.K("mo")))
        self.assertEqual((r["phien_ban"], r["dang_ban"]), (5, True))
        self.assertIn(da, [x["da_ban_id"] for x in self.db(lambda: self.dv.danh_sach(BH, dang_ban=True))["du_an_ban"]])
        self.assertNotIn(self.du_an, [x["du_an_id"] for x in self.db(lambda: self.dv.danh_sach(BH))["du_an_chua_ban"]])
        self.assertIn(self.du_an_2, [x["du_an_id"] for x in self.db(lambda: self.dv.danh_sach(BH))["du_an_chua_ban"]])
        self.s["mo"] = True

    def test_t09_lich_su(self):
        self.can("da", "mo")
        ls = self.db(lambda: self.dv.lich_su(BH, self.s["da"]))
        self.assertEqual([x["phien_ban"] for x in ls["phien_ban"]], [1, 2, 3, 4, 5])
        self.assertEqual([x["hanh_dong"] for x in ls["su_kien"]], ["CRM_DA_BAT_BAN", "CRM_DA_CAP_NHAT", "CRM_DA_PHI", "CRM_DA_LO", "CRM_DA_LO",
                                                                    "CRM_DA_NGUNG_BAN", "CRM_DA_MO_BAN_LAI"])
        self.assertTrue(all("noi_dung" not in (x["sau"] or {}) for x in ls["su_kien"]))
        self.assertEqual([x["ly_do"] for x in ls["su_kien"] if x["hanh_dong"] == "CRM_DA_NGUNG_BAN"], ["Tạm dừng kiểm thử DEMO"])
        td = [x for x in ls["tien_do"] if x["giai_doan"] == self.gd]
        self.assertEqual([(x["phien_ban"], x["nguon"], x["khoang_rong"]) for x in td], [(1, "AP_DUNG_NGAY", True), (2, "AP_DUNG_NGAY", False)])

    def test_t10_bat_bien_va_vai_ung_dung(self):
        self.can("da", "pb1")
        for sql, p in (("UPDATE master.crm_da_ban_phien_ban SET mo_ta = 'sửa' WHERE id = %s", (self.s["pb1"],)),
                       ("UPDATE master.crm_da_ban_phien_ban SET hieu_luc_den = '2099-01-01' WHERE id = %s", (self.s["pb1"],)),
                       ("DELETE FROM master.crm_da_ban_phien_ban WHERE id = %s", (self.s["pb1"],)),
                       ("UPDATE master.crm_da_ban_phi SET muc = '0' WHERE phien_ban_id = %s", (self.s["pb1"],)),
                       ("DELETE FROM master.crm_da_ban WHERE id = %s", (self.s["da"],)),
                       ("UPDATE master.crm_bo_chuan_ap_dung SET can_cu = 'QD-20261025-07' WHERE da_ban_id = %s", (self.s["da"],))):
            with self.subTest(sql=sql[:50]):
                with self.assertRaises(self.psycopg.Error) as cm:
                    with self.admin.transaction():
                        self.admin.execute(sql, p)
                self.assertEqual(_ma_pg(cm.exception), "CRM_G_BAT_BIEN")
        for t in ("crm_da_ban", "crm_da_ban_phien_ban", "crm_da_ban_phi", "crm_da_ban_lo", "crm_da_ban_lo_ls", "crm_bo_chuan_ap_dung"):
            with self.subTest(bang=t):
                with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                    self.app.execute(f"SELECT 1 FROM master.{t} LIMIT 1")
        with self.assertRaises(self.psycopg.Error):  # hàm lệnh không cấp cho login ứng dụng
            self.app.execute("SELECT master.crm_da_anh_chup(%s::uuid, current_date)", (self.du_an,))

    def test_t11_noi_dung_sha(self):
        self.can("da")
        r = self.admin.execute("""SELECT bool_and(encode(sha256(convert_to(master.crm_da_noi_dung(id)::text, 'UTF8')), 'hex') = noi_dung_sha256) AS ok, count(*) AS n
                                  FROM master.crm_da_ban_phien_ban WHERE da_ban_id = %s""", (self.s["da"],)).fetchone()
        self.assertEqual((r["ok"], r["n"] >= 5), (True, True))

    def test_t12_seed_demo_idempotent(self):
        dem = lambda: self.admin.execute("SELECT (SELECT count(*) FROM master.crm_da_ban_phien_ban) + (SELECT count(*) FROM master.crm_da_ban_lo_ls) "  # noqa: E731
                                         "+ (SELECT count(*) FROM master.crm_bo_chuan_phien_ban) AS n").fetchone()["n"]
        for ma in ("DA_KCN_DEMO", "DA_NHA_DEMO"):
            with self.subTest(du_an=ma):
                da = self.admin.execute("""SELECT a.id::text AS du_an_id FROM master.du_an a JOIN master.crm_da_ban d ON d.du_an_id = a.id WHERE a.ma_junsky = %s""",
                                        (ma,)).fetchone()
                if da is None:
                    self.fail(f"NOT_VERIFIED: chưa có seed dự án đang bán {ma} — chạy bước chuẩn bị DEMO (tools/chuan_bi_crm_demo.py)")
                a = self.db(lambda: self.dv.anh_chup_mac_dinh(BH, da["du_an_id"]))
                self.assertEqual(a["trang_thai"], "DANG_BAN")
                self.assertIn("DEMO", a["du_an"]["ma"])
                self.assertGreaterEqual(len({p["don_vi_tinh"] for p in a["phi"]}), 2)
                self.assertGreaterEqual(len(a["lo"]), 2)
                self.assertEqual((a["bo_chuan"]["trang_thai"], a["bo_chuan"]["nguon"]), ("HIEU_LUC", "AP_DUNG_NGAY"))
        truoc = dem()
        kq = D.khoi_tao_demo(self.admin_t)
        self.assertEqual((kq["trang_thai"], [x["trang_thai"] for x in kq["du_an"]]), ("DU", ["DU", "DU"]))
        self.assertEqual(dem(), truoc)  # mở lại không thêm phiên bản/dòng


if __name__ == "__main__":
    unittest.main()
