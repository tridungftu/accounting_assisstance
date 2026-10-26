"""M3-1b: DEMO thuần và PG tùy chọn, không mở server/không nới schema M2.

PG hiện chỉ kiểm được hợp đồng và mapping ứng viên: CHECK của M2 chặn bán
ra và tiền chuẩn hóa. Không giả một hóa đơn bán hợp lệ bằng cách bỏ guard.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid

from kho_tri_thuc.k2.m3 import M3K2, tinh_ba_dang_thuc

try:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
except ImportError:
    psycopg = None


D = Decimal


def demo():
    c = dict(id="DEMO-co-so", revision=1, phap_nhan_id="DEMO-phap-nhan",
             hop_dong_id="DEMO-hop-dong", hop_dong_phien_ban_id="DEMO-hop-dong-v1",
             hop_dong_phien_ban=1, pham_vi="Lô DEMO", nguon="Hợp đồng DEMO",
             trang_thai="DA_XAC_NHAN", crm_trang_thai="DA_DUYET", currency="VND",
             gia_tri_truoc_vat=D("100"), tong_thanh_toan=D("108"),
             tong_gia_dat_duoc_tru=D("20"), phan_chiu_thue=D("80"))
    links = []
    for i in (1, 2):
        hd = dict(id=f"DEMO-hoa-don-{i}", phien_ban_id=f"DEMO-hoa-don-{i}-v1",
                  phien_ban=1, chieu="BAN_RA", currency="VND", nguon=f"Hóa đơn DEMO {i}",
                  tong_thanh_toan=D("54"), khong_chiu_thue=D("10"), net_chiu_thue=D("40"))
        links.append(dict(id=f"DEMO-lien-ket-{i}", revision=1, co_so_id=c["id"],
                          phap_nhan_id=c["phap_nhan_id"], trang_thai="DA_XAC_NHAN",
                          nguon=f"Xác nhận nối hóa đơn DEMO {i}", can_cu="Đợt DEMO đã xác nhận",
                          hoa_don_id=hd["id"], hoa_don_phien_ban_id=hd["phien_ban_id"],
                          hoa_don_quan_sat_id=f"DEMO-quan-sat-{i}", hoa_don=hd))
    evidence = dict(id="DEMO-du-dot", revision=2, nguon="Xác nhận đủ đợt DEMO",
                    co_so_id=c["id"], trang_thai="DA_XAC_NHAN",
                    lien_ket_ids=[l["id"] for l in links])
    policy = dict(id="DEMO-policy-thue", revision=3, nguon="Căn cứ thuế DEMO số 7",
                  co_so_id=c["id"], trang_thai="DA_XAC_NHAN")
    return c, links, dict(can_cu_du_dot=evidence, policy_thue=policy)


class BaDangThucThuan(unittest.TestCase):
    def setUp(self):
        self.c, self.links, self.kw = demo()

    def run_demo(self):
        return tinh_ba_dang_thuc(self.c, self.links, **self.kw)

    def test_khop_va_nguon_phien_ban_khong_doi_du_lieu(self):
        before = deepcopy((self.c, self.links, self.kw))
        result = self.run_demo()
        self.assertEqual([r.trang_thai for r in result], ["KHOP"] * 3)
        self.assertEqual([r.ve_trai for r in result], [D(108), D(20), D(80)])
        self.assertEqual([r.chenh for r in result], [D(0)] * 3)
        self.assertEqual((self.c, self.links, self.kw), before)
        for r in result:
            self.assertTrue(all(n.phien_ban is not None or n.revision is not None for n in r.nguon))
            self.assertEqual(sum(n.loai == "Hóa đơn" for n in r.nguon), 2)
        self.assertEqual(result[1].nguon[-1].id, "DEMO-policy-thue")
        self.assertEqual(result[1].nguon[-1].revision, 3)

    def test_hoa_don_xuat_sai_co_so_khong_sua_vat_tong_hay_doanh_thu(self):
        self.links[1]["hoa_don"]["khong_chiu_thue"] = D(9)
        self.links[1]["hoa_don"]["net_chiu_thue"] = D(41)
        result = self.run_demo()
        self.assertEqual([r.trang_thai for r in result], ["KHOP", "LECH", "LECH"])
        self.assertEqual([r.chenh for r in result], [D(0), D(-1), D(1)])
        self.assertEqual(self.c["gia_tri_truoc_vat"], D(100))

    def test_thieu_xac_nhan_hoac_crm_chua_duyet(self):
        for field, value in (("trang_thai", "PENDING"), ("crm_trang_thai", "CHO_DUYET")):
            with self.subTest(field=field):
                c = {**self.c, field: value}
                self.assertEqual([r.trang_thai for r in tinh_ba_dang_thuc(c, self.links, **self.kw)], ["PENDING"] * 3)

    def test_ung_vien_khong_tinh_ke_ca_co_so_tien(self):
        self.links[1]["trang_thai"] = "PENDING"
        self.links[1]["hoa_don"]["tong_thanh_toan"] = D("999999")
        result = self.run_demo()
        self.assertEqual([r.ve_trai for r in result], [D(54), D(10), D(40)])
        self.assertEqual([r.trang_thai for r in result], ["PENDING"] * 3)
        self.assertFalse(next(n for n in result[0].nguon if n.id == self.links[1]["id"]).duoc_tinh)

    def test_chi_ung_vien_hoac_khong_hoa_don_khong_thanh_0(self):
        for links in ([], [{**l, "trang_thai": "PENDING"} for l in self.links]):
            with self.subTest(links=bool(links)):
                for r in tinh_ba_dang_thuc(self.c, links, **self.kw):
                    self.assertIsNone(r.ve_trai)
                    self.assertIsNone(r.chenh)
                    self.assertEqual(r.trang_thai, "PENDING")

    def test_khac_currency_khong_cong_hoac_tinh_chenh(self):
        self.links[1]["hoa_don"]["currency"] = "USD"
        for r in self.run_demo():
            self.assertEqual(r.trang_thai, "PENDING")
            self.assertIsNone(r.ve_trai)
            self.assertIsNone(r.chenh)
            self.assertTrue(any("đồng tiền khác nhau" in reason for reason in r.ly_do))
            self.assertFalse(any(n.duoc_tinh for n in r.nguon))

    def test_currency_thieu_khong_duoc_khop(self):
        self.c["currency"] = None
        for r in self.run_demo():
            self.assertEqual(r.trang_thai, "PENDING")
            self.assertIsNone(r.chenh)

    def test_so_thieu_khong_thanh_0_tung_dang_thuc_doc_lap(self):
        self.links[0]["hoa_don"]["khong_chiu_thue"] = None
        self.c["phan_chiu_thue"] = None
        result = self.run_demo()
        self.assertEqual([r.trang_thai for r in result], ["KHOP", "PENDING", "PENDING"])
        self.assertIsNone(result[1].ve_trai)
        self.assertIsNone(result[1].chenh)
        self.assertFalse(any(n.duoc_tinh for n in result[1].nguon))
        self.assertTrue(any("phần không chịu thuế" in why for why in result[1].ly_do))
        self.assertIsNone(result[2].ve_phai)
        self.assertIsNone(result[2].chenh)

    def test_zero_tuong_minh_la_so_hop_le(self):
        self.c["tong_gia_dat_duoc_tru"] = D(0)
        for link in self.links:
            link["hoa_don"]["khong_chiu_thue"] = D(0)
        self.assertEqual(self.run_demo()[1].trang_thai, "KHOP")

    def test_thieu_policy_7_chi_chan_dang_thuc_2_va_3(self):
        for policy in (None, {**self.kw["policy_thue"], "trang_thai": "PENDING"},
                       {**self.kw["policy_thue"], "co_so_id": "DEMO-khac"},
                       {**self.kw["policy_thue"], "revision": None}):
            with self.subTest(policy=policy):
                self.kw["policy_thue"] = policy
                self.assertEqual([r.trang_thai for r in self.run_demo()], ["KHOP", "PENDING", "PENDING"])

    def test_chua_du_dot_hien_so_luy_ke_chenh_tam(self):
        self.kw["can_cu_du_dot"] = None
        self.links[0]["hoa_don"]["tong_thanh_toan"] = D(53)
        result = self.run_demo()
        self.assertEqual(result[0].trang_thai, "CHUA_DU_DOT")
        self.assertEqual(result[0].chenh, D(-1))
        self.assertEqual([r.trang_thai for r in result[1:]], ["KHOP", "KHOP"])

    def test_can_cu_du_dot_phai_ghim_dung_co_so_tap_hoa_don_va_revision(self):
        evidence = self.kw["can_cu_du_dot"]
        for changes in ({"co_so_id": "DEMO-khac"}, {"lien_ket_ids": []},
                        {"lien_ket_ids": None}, {"lien_ket_ids": "DEMO"},
                        {"revision": None}, {"revision": -1}, {"revision": True},
                        {"trang_thai": "PENDING"}, {"nguon": None}):
            with self.subTest(changes=changes):
                self.kw["can_cu_du_dot"] = {**evidence, **changes}
                self.assertEqual(self.run_demo()[0].trang_thai, "CHUA_DU_DOT")

    def test_decimal_khong_dung_sai_khong_bi_precision_context(self):
        self.c["tong_thanh_toan"] = D("1000000000000000000000000000000.3")
        self.links[0]["hoa_don"]["tong_thanh_toan"] = D("1000000000000000000000000000000.1")
        self.links[1]["hoa_don"]["tong_thanh_toan"] = D("0.2")
        with localcontext() as ctx:
            ctx.prec = 6
            self.assertEqual(self.run_demo()[0].trang_thai, "KHOP")
            self.links[1]["hoa_don"]["tong_thanh_toan"] = D("0.200000000000000000000000000001")
            r = self.run_demo()[0]
            self.assertEqual(r.trang_thai, "LECH")
            self.assertEqual(r.chenh, D("0.000000000000000000000000000001"))

    def test_float_nan_infinity_chuoi_khong_duoc_tinh(self):
        for amount in (0.0, "0", D("NaN"), D("Infinity"), D("-Infinity")):
            with self.subTest(amount=str(amount)):
                self.links[0]["hoa_don"]["tong_thanh_toan"] = amount
                r = self.run_demo()[0]
                self.assertIsNone(r.ve_trai)
                self.assertIsNone(r.chenh)
                self.assertEqual(r.trang_thai, "PENDING")

    def test_hoa_don_trung_khong_tinh_hai_lan_va_pending(self):
        self.links.append(deepcopy(self.links[0]))
        result = self.run_demo()
        self.assertEqual(result[0].ve_trai, D(108))
        self.assertEqual([r.trang_thai for r in result], ["PENDING"] * 3)

    def test_ghim_sai_phien_ban_phap_nhan_co_so_khong_tinh(self):
        original = deepcopy(self.links[0])
        for changes in ({"hoa_don_phien_ban_id": "DEMO-khac"},
                        {"phap_nhan_id": "DEMO-khac"}, {"co_so_id": "DEMO-khac"},
                        {"hoa_don_quan_sat_id": None}):
            with self.subTest(changes=changes):
                self.links[0] = {**original, **changes}
                r = self.run_demo()[0]
                self.assertEqual(r.trang_thai, "PENDING")
                self.assertEqual(r.ve_trai, D(54))

    def test_dto_tieng_viet_tien_co_don_vi_khong_khoa_ky_thuat(self):
        self.c["tong_thanh_toan"] = D("1234567.89")
        view = self.run_demo()[0].ra_man_hinh()
        self.assertEqual(view["ve_phai"], "1.234.567,89 VND")
        self.assertEqual(view["chenh"], "−1.234.459,89 VND")
        text = json.dumps(view, ensure_ascii=False)
        for token in ("DEMO-co-so", "DEMO-lien-ket-", "DA_XAC_NHAN", "LECH", "PENDING"):
            self.assertNotIn(token, text)
        self.c["tong_thanh_toan"] = None
        self.assertEqual(self.run_demo()[0].ra_man_hinh()["ve_phai"], "Chưa đủ dữ liệu")

    def test_reader_chi_mot_select_tham_so_khong_ghi_khong_quay_ve_ban_duyet_cu(self):
        c = {**self.c, "revision": 2, "trang_thai": "PENDING", "lien_ket_id": None}
        names = list(c)
        calls = []

        class Connection:
            def execute(inner, query, params):
                calls.append((query, params))
                return SimpleNamespace(description=[SimpleNamespace(name=n) for n in names],
                                       fetchall=lambda: [tuple(c.values())])

        scope = "Lô DEMO ' không nội suy SQL"
        result = M3K2(Connection()).ba_dang_thuc("DEMO-pn", "DEMO-hd", "DEMO-pb", pham_vi=scope)
        self.assertEqual([r.trang_thai for r in result], ["PENDING"] * 3)
        self.assertEqual(result[0].nguon[0].revision, 2)
        self.assertEqual(len(calls), 1)
        query, params = calls[0]
        self.assertNotIn(scope, query)
        self.assertEqual(params, ("DEMO-pn", "DEMO-hd", "DEMO-pb", scope, None, None))
        self.assertTrue(query.strip().startswith("WITH co_so"))
        for word in ("INSERT", "UPDATE", "DELETE", "COMMIT", "SET "):
            self.assertNotIn(word, query.upper())
        self.assertIn("newer.revision > l.revision", query)
        self.assertNotIn("c.trang_thai = 'DA_XAC_NHAN'", query)

    def test_reader_khong_thay_co_so_van_pending(self):
        conn = SimpleNamespace(execute=lambda *args: SimpleNamespace(description=[], fetchall=lambda: []))
        for r in M3K2(conn).ba_dang_thuc("DEMO", "DEMO", "DEMO", pham_vi="DEMO"):
            self.assertIsNone(r.ve_trai)
            self.assertIsNone(r.ve_phai)
            self.assertEqual(r.trang_thai, "PENDING")

    def test_utf8_khong_bom(self):
        root = Path(__file__).resolve().parents[1]
        for path in (Path(__file__), root / "src/kho_tri_thuc/k2/m3.py"):
            data = path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            data.decode("utf-8", errors="strict")


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST") and psycopg is not None,
                     "Thiếu KHO_PG_DSN_TEST hoặc psycopg — bỏ qua PG")
class BaDangThucPostgres(unittest.TestCase):
    """Dùng CSDL test đã migrate; chỉ INSERT DEMO trong transaction rollback.

    Cần Anh: đường PG khớp số chờ M2 hỗ trợ hóa đơn bán và tiền exact. Không
    sửa CHECK/migration để giả đường này đã chạy được.
    """

    def setUp(self):
        dsn = os.environ["KHO_PG_DSN_TEST"]
        db = conninfo_to_dict(dsn).get("dbname", "")
        if not db.startswith("kho_test_"):
            self.skipTest("Chỉ dùng CSDL test có tên kho_test_* đã migrate")
        self.conn = psycopg.connect(dsn)
        self.addCleanup(self.conn.close)
        self.addCleanup(self.conn.rollback)
        self.pn = self.conn.execute("""INSERT INTO master.phap_nhan (ma,ten)
            VALUES (%s,'Pháp nhân DEMO đẳng thức') RETURNING id""",
                                    ("DEMO_M31B_" + uuid.uuid4().hex,)).fetchone()[0]
        self.hd = self.conn.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,loai,ma_noi_bo,so_hop_dong)
            VALUES (%s,'THUE_DAT','DEMO-M31B','DEMO/M31B') RETURNING id""", (self.pn,)).fetchone()[0]
        self.pb = self.conn.execute("""INSERT INTO master.hop_dong_phien_ban
            (hop_dong_id,phien_ban,nguon) VALUES (%s,1,'TAY') RETURNING id""", (self.hd,)).fetchone()[0]
        self.basis = self.conn.execute("""INSERT INTO m3.hop_dong_co_so
            (phap_nhan_id,hop_dong_id,hop_dong_phien_ban_id,pham_vi,revision,
             gia_tri_truoc_vat,tong_gia_dat_duoc_tru,phan_chiu_thue,vat,tong_thanh_toan,
             currency,nguon,tao_boi)
            VALUES (%s,%s,%s,'Lô DEMO',1,100.01,20.001,80.009,8,108.01,'VND','Hợp đồng DEMO','DEMO')
            RETURNING id""", (self.pn, self.hd, self.pb)).fetchone()[0]
        self.link = self.conn.execute("""INSERT INTO m3.hoa_don_hop_dong
            (phap_nhan_id,co_so_id,revision,nguon,nguon_ref,tao_boi)
            VALUES (%s,%s,1,'Hóa đơn ứng viên DEMO','DEMO/source/1','DEMO') RETURNING id""",
                                      (self.pn, self.basis)).fetchone()[0]

    def test_ba_dang_thuc_doc_dung_co_so_va_ung_vien_tu_bang(self):
        result = M3K2(self.conn).ba_dang_thuc(self.pn, self.hd, self.pb, pham_vi="Lô DEMO", revision=1)
        self.assertEqual([r.ve_phai for r in result], [D("108.01"), D("20.001"), D("80.009")])
        for r in result:
            self.assertEqual(r.trang_thai, "PENDING")
            self.assertIsNone(r.ve_trai)
            self.assertIsNone(r.chenh)
            self.assertEqual(r.nguon[0].id, str(self.basis))
            self.assertEqual(r.nguon[0].phien_ban, 1)
            link = next(n for n in r.nguon if n.loai == "Liên kết hóa đơn")
            self.assertEqual(link.id, str(self.link))
            self.assertEqual(link.revision, 1)
            self.assertFalse(link.duoc_tinh)


if __name__ == "__main__":
    unittest.main()
