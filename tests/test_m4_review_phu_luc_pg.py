"""M4-DL3: dữ liệu DEMO thuần; PG chỉ chạy khi lead cấp DSN, không mở server.

PG tạo kho_test_* riêng giống DL2, không xóa DB; lead kiểm/dọn ngoài sandbox.
"""

from __future__ import annotations

import copy
import os
import unittest
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4.review_phu_luc_pg import (
    ReviewPhuLucPG, _chuan_bi, dto_phu_luc,
)

try:
    import psycopg
    from psycopg import conninfo, sql
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None


DSN = os.environ.get("KHO_PG_DSN_TEST")
CHUP = "2026-10-26T07:00:00+07:00"
BANG = ("nguon", "hop_dong", "phu_luc", "thay_doi_tham_so", "boq_dong")


def _pl(identity, day, **changes):
    result = dict(id=identity, ma_hd="DEMO-HD", so_pl=f"DEMO-PL-{identity}",
                  ngay_ky="2026-01-01", ngay_hieu_luc=day, doi_boq=1,
                  trang_thai="Đã ký", gt_truoc_vat=-0.1, gt_sau_vat=None,
                  gt_hd_sau_pl=1000.125, ly_do_huy=None,
                  file_nguon="DEMO/private/pl.docx", nguoi_nhap="DEMO người nhập",
                  phieu='{"DEMO_path":"DEMO/private"}')
    result.update(changes)
    return result


def _dong(identity, code, op="GOC", parent=None, **changes):
    result = dict(id=identity, ma_hd="DEMO-HD", ma_hm=code, pl_id=parent,
                  thao_tac=op, ten="DEMO hạng mục", dvt="DEMO m2",
                  kl=1.25, don_gia=10.1, thanh_tien_ghi=None,
                  vi_tri_nguon="DEMO/private/boq.xlsx!A1", khoa="DEMO-khoa-noi-bo")
    result.update(changes)
    return result


def _demo():
    return {
        "phu_luc": [
            _pl(1, "2026-02-01"), _pl(2, "2026-03-01", gt_hd_sau_pl=None),
            _pl(3, "2026-02-01", so_pl="DEMO-PL-1", trang_thai="Đã hủy", ly_do_huy="DEMO hủy bản gốc"),
        ],
        "thay_doi_tham_so": [
            dict(pl_id=1, ma_ts="DEMO-TS", gia_tri_cu=None, gia_tri_moi="", trich_dan="DEMO Điều 1"),
            dict(pl_id=3, ma_ts="DEMO-TS", gia_tri_cu="DEMO cũ", gia_tri_moi="DEMO đã hủy"),
        ],
        "boq_dong": [
            _dong(1, "DEMO-A"), _dong(2, "DEMO-B"),
            _dong(3, "DEMO-A", "THAY", 1, kl=2.5, don_gia=None, ten=""),
            _dong(4, "DEMO-C", "THEM", 1, kl=-0.1),
            _dong(5, "DEMO-B", "BO", 2),
            _dong(6, "DEMO-A", "BO", 3),
        ],
    }


def _base():
    return dict(che_do=[], hop_dong=[dict(ma_hd="DEMO-HD", so_hd="DEMO/HĐ/DL3", gia_tri_hd=123.4)],
                tham_so=[], tham_so_nguon=[])


def _dto(data=None, day="2026-03-01"):
    data = _demo() if data is None else data
    return dto_phu_luc(data["phu_luc"], data["thay_doi_tham_so"], data["boq_dong"], day)


class ReviewPhuLucTinh(unittest.TestCase):
    def test_thay_them_bo_tai_ba_moc_ngay(self):
        for day, codes, quantity in (
            ("2026-01-31", ["DEMO-A", "DEMO-B"], "1.25"),
            ("2026-02-01", ["DEMO-A", "DEMO-B", "DEMO-C"], "2.5"),
            ("2026-03-01", ["DEMO-A", "DEMO-C"], "2.5"),
        ):
            with self.subTest(day=day):
                result = _dto(day=day)
                self.assertFalse(result["can_xem_lai"])
                self.assertEqual([r["ma_hm"] for r in result["boq"]], codes)
                self.assertEqual(result["boq"][0]["kl"], Decimal(quantity))

    def test_thay_giu_o_null_rong_nhung_ap_zero_theo_nguon(self):
        data = _demo()
        data["boq_dong"][2]["kl"] = 0
        actual = _dto(data)["boq"][0]
        self.assertEqual(actual["kl"], Decimal(0))
        self.assertEqual(actual["don_gia"], Decimal("10.1"))
        self.assertEqual(actual["ten"], "DEMO hạng mục")
        self.assertIsNone(actual["thanh_tien_ghi"])

    def test_hai_pl_cung_ngay_khong_chon_theo_id_hay_so(self):
        data = _demo()
        data["phu_luc"][1]["ngay_hieu_luc"] = "2026-02-01"
        for rows in (data["phu_luc"], list(reversed(data["phu_luc"]))):
            data["phu_luc"] = rows
            result = _dto(data)
            self.assertTrue(result["can_xem_lai"])
            self.assertIsNone(result["boq"])
            self.assertIsNone(result["gt_hd_sau_pl"])
        self.assertFalse(_dto(data, "2026-01-31")["can_xem_lai"])

    def test_phu_luc_huy_va_du_thao_khong_ap(self):
        data = _demo()
        data["phu_luc"][1]["trang_thai"] = "Dự thảo"
        actual = _dto(data)
        self.assertFalse(actual["can_xem_lai"])
        self.assertEqual([r["ma_hm"] for r in actual["boq"]], ["DEMO-A", "DEMO-B", "DEMO-C"])
        self.assertEqual(actual["phu_luc"][2]["ly_do_huy"], "DEMO hủy bản gốc")
        self.assertEqual(actual["phu_luc"][0]["so_pl"], actual["phu_luc"][2]["so_pl"])
        self.assertEqual(actual["phu_luc"][0]["thay_doi_tham_so"][0]["gia_tri_moi"], "")
        self.assertEqual(actual["phu_luc"][2]["thay_doi_tham_so"][0]["gia_tri_moi"], "DEMO đã hủy")
        self.assertNotIn("ngay_huy", actual["phu_luc"][2])
        self.assertNotIn("nguoi_huy", actual["phu_luc"][2])

    def test_gt_hd_lay_nguyen_nguon_khong_cong_khong_fallback_null(self):
        self.assertIsNone(_dto(day="2026-01-01")["gt_hd_sau_pl"])
        self.assertEqual(_dto(day="2026-02-01")["gt_hd_sau_pl"], Decimal("1000.125"))
        self.assertIsNone(_dto()["gt_hd_sau_pl"])
        self.assertIsNone(_dto()["phu_luc"][0]["gt_sau_vat"])

    def test_allowlist_khong_lo_file_actor_id_hash_phieu(self):
        data = _demo()
        forbidden = {"id", "pl_id", "ma_hd", "nguon_id", "nhap_boi", "file_nguon",
                     "vi_tri_nguon", "khoa", "phieu", "nguoi_nhap", "dong_sha256",
                     "chep_id", "hop_dong_id", "du_an_id"}
        for rows in data.values():
            for row in rows:
                row.update(nhap_boi="DEMO/private", nguon_id="DEMO/private", dong_sha256="DEMO/private")

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & forbidden)
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(_dto(data))

    def test_ngay_sai_trang_thai_la_orphan_bat_co_khong_tra_bo_phan(self):
        for change in ("ngay", "trang_thai", "orphan", "thay_thieu", "them_trung"):
            data = _demo()
            if change == "ngay":
                data["phu_luc"][0]["ngay_hieu_luc"] = "01/02/2026"
            elif change == "trang_thai":
                data["phu_luc"][0]["trang_thai"] = "DEMO chưa biết"
            elif change == "orphan":
                data["boq_dong"][2]["pl_id"] = 999
            elif change == "thay_thieu":
                data["boq_dong"][2]["ma_hm"] = "DEMO-THIEU"
            else:
                data["boq_dong"][3]["ma_hm"] = "DEMO-B"
            with self.subTest(change=change):
                actual = _dto(data)
                self.assertTrue(actual["can_xem_lai"])
                self.assertIsNone(actual["boq"])
        for bad in (None, "20260201", "01/02/2026"):
            with self.subTest(bad=bad), self.assertRaises(DataError):
                _dto(day=bad)
        self.assertEqual(_dto(day=date(2026, 3, 1)), _dto())

    def test_projection_khong_sua_input_va_giu_thu_tu_dong(self):
        data = _demo()
        before = copy.deepcopy(data)
        self.assertEqual(_dto(data), _dto(dict(data, boq_dong=list(reversed(data["boq_dong"])))))
        self.assertEqual(data, before)

    def test_chuan_bi_decimal_null_hash_va_anh_xa(self):
        data = _demo()
        before = copy.deepcopy(data)
        contracts = {"DEMO-HD": dict(hop_dong_id=uuid.UUID(int=1), du_an_id=uuid.UUID(int=2))}
        prepared = _chuan_bi(data, contracts)
        self.assertEqual(data, before)
        self.assertEqual(prepared["phu_luc"][(1,)]["gt_truoc_vat"], Decimal(repr(-0.1)))
        self.assertIsNone(prepared["phu_luc"][(1,)]["gt_sau_vat"])
        self.assertEqual(prepared["thay_doi_tham_so"][(1, "DEMO-TS")]["gia_tri_moi"], "")
        shuffled = {t: list(reversed(rows)) for t, rows in data.items()}
        self.assertEqual(prepared, _chuan_bi(shuffled, contracts))
        data["phu_luc"][0]["file_nguon"] = "DEMO/private/khac.docx"
        self.assertNotEqual(prepared["phu_luc"][(1,)]["dong_sha256"],
                            _chuan_bi(data, contracts)["phu_luc"][(1,)]["dong_sha256"])

    def test_chuan_bi_chan_thieu_bang_anh_xa_va_fk(self):
        contracts = {"DEMO-HD": dict(hop_dong_id=uuid.UUID(int=1), du_an_id=uuid.UUID(int=2))}
        for change in ("bang", "anh_xa", "fk", "trung", "cot", "nan"):
            data, mapping = _demo(), contracts
            if change == "bang":
                data.pop("boq_dong")
            elif change == "anh_xa":
                mapping = {}
            elif change == "fk":
                data["thay_doi_tham_so"][0]["pl_id"] = 999
            elif change == "trung":
                data["phu_luc"].append(dict(data["phu_luc"][0]))
            elif change == "cot":
                data["phu_luc"][0]["DEMO_cot_la"] = None
            else:
                data["boq_dong"][0]["kl"] = float("nan")
            with self.subTest(change=change), self.assertRaises(DataError):
                _chuan_bi(data, mapping)

    def test_ghi_rieng_bat_buoc_transaction_dang_mo(self):
        conn = Mock()
        conn.info.transaction_status = 0
        with self.assertRaises(DataError):
            ReviewPhuLucPG(conn).ghi_trong_giao_dich(_demo(), nguon_id="DEMO", nhap_boi="DEMO", replay=False)
        conn.execute.assert_not_called()


@unittest.skipUnless(DSN and psycopg is not None, "Thiếu KHO_PG_DSN_TEST/psycopg — PG do lead chạy (NOT_RUN)")
class ReviewPhuLucPGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_m4_dl3_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = conninfo.make_conninfo(DSN, dbname=cls.db)
        cls.con = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.con.close)
        pg.migrate(cls.con)
        cls.pn = cls.con.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES ('DEMO_DL3','Pháp nhân DEMO DL3') RETURNING id").fetchone()[0]
        cls.da = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_DL3','Dự án DEMO DL3') RETURNING id", (cls.pn,)).fetchone()[0]

    def setUp(self):
        self.enterContext(self.con.transaction(force_rollback=True))
        code = "DEMO-DL3-" + uuid.uuid4().hex
        self.hd = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()[0]
        self.con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'DEMO DL3','MO_PHONG_DEMO')""", (self.hd, self.pn, self.da))
        self.repo = ReviewPhuLucPG(self.con)
        self.source = "DEMO-DL3-" + uuid.uuid4().hex

    def _ghi(self, data=None, **changes):
        args = dict(nguon_id=self.source, chup_luc=CHUP, nhap_boi="MO_PHONG_DEMO",
                    anh_xa={"DEMO-HD": (self.hd, self.da)}, mo_ta="DEMO DL3")
        args.update(changes)
        return self.repo.ghi_lan_chup(_demo() if data is None else data, du_lieu_dl2=_base(), **args)

    def _counts(self):
        return {t: self.con.execute(f"SELECT count(*) FROM m4.review_chep_{t} WHERE {'id' if t == 'nguon' else 'nguon_id'}=%s",
                                    (self.source,)).fetchone()[0] for t in BANG}

    def test_ghi_doc_boq_hai_ngay_tham_so_huy_va_decimal(self):
        self.assertEqual(self._ghi(), 13)
        for day in ("2026-02-01", "2026-03-01"):
            self.assertEqual(self.repo.doc_hien_hanh(self.hd, ngay=day), dict(_dto(day=day), trang_thai="HIEN_HANH"))
        value = self.con.execute("SELECT don_gia FROM m4.review_chep_boq_dong WHERE nguon_id=%s AND id=3", (self.source,)).fetchone()[0]
        self.assertIsNone(value)

    def test_replay_doi_thu_tu_khong_tang_dong(self):
        self._ghi()
        before = self._counts()
        self.assertEqual(self._ghi({t: list(reversed(rows)) for t, rows in _demo().items()}), 0)
        self.assertEqual(self._counts(), before)

    def test_replay_chan_khac_hash_them_bot_ke_ca_bang_rong(self):
        self._ghi()
        before = self._counts()
        for change in ("hash", "them", "bot", "rong"):
            data = _demo()
            if change == "hash":
                data["phu_luc"][0]["gt_hd_sau_pl"] = 12345
            elif change == "them":
                data["boq_dong"].append(_dong(99, "DEMO-THEM"))
            elif change == "bot":
                data["boq_dong"].pop()
            else:
                data = {t: [] for t in data}
            with self.subTest(change=change), self.assertRaises(DataError) as caught:
                self._ghi(data)
            self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
            self.assertEqual(self._counts(), before)

    def test_lan_chup_hai_mat_pl_khong_lay_lai_ban_cu(self):
        self._ghi()
        data = dict(phu_luc=[], thay_doi_tham_so=[], boq_dong=_demo()["boq_dong"][:2])
        self._ghi(data, nguon_id="DEMO-DL3-MOI", chup_luc="2026-10-27T07:00:00+07:00")
        result = self.repo.doc_hien_hanh(self.hd, ngay="2026-03-01")
        self.assertEqual(result["phu_luc"], [])
        self.assertEqual([r["ma_hm"] for r in result["boq"]], ["DEMO-A", "DEMO-B"])
        self.assertEqual(self._counts()["phu_luc"], 3)

    def test_loi_dl3_rollback_ca_dl2_va_nguon(self):
        data = _demo()
        # Vi phạm UQ phụ lục chưa hủy sau khi DL2 đã ghi nguồn/HĐ.
        data["phu_luc"][1]["so_pl"] = data["phu_luc"][0]["so_pl"]
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self._ghi(data)
        self.assertEqual(set(self._counts().values()), {0})
        self.assertEqual(self._ghi(), 13)

    def test_replay_ba_bang_rong_khong_cho_noi_them(self):
        empty = {t: [] for t in _demo()}
        self.assertEqual(self._ghi(empty), 2)
        self.assertEqual(self._ghi(empty), 0)
        with self.assertRaises(DataError):
            self._ghi()
        self.assertEqual(self._counts()["phu_luc"], 0)

    def test_phan_biet_chua_chup_va_hd_vang_nguon(self):
        self.assertEqual(self.repo.doc_hien_hanh(self.hd, ngay="2026-03-01")["trang_thai"], "CHUA_CO_LAN_CHUP")
        self.repo.ghi_lan_chup({t: [] for t in _demo()}, du_lieu_dl2={t: [] for t in _base()},
                              nguon_id=self.source, chup_luc=CHUP, nhap_boi="MO_PHONG_DEMO", anh_xa={})
        self.assertEqual(self.repo.doc_hien_hanh(self.hd, ngay="2026-03-01")["trang_thai"], "DA_XOA_O_NGUON")

    def test_dict_row_doc_ghi(self):
        # Đổi row_factory trên cùng conn vẫn nằm trong transaction rollback test.
        before = self.con.row_factory
        try:
            self.con.row_factory = dict_row
            self._ghi()
            self.assertEqual(self.repo.doc_hien_hanh(self.hd, ngay="2026-03-01"), dict(_dto(), trang_thai="HIEN_HANH"))
        finally:
            self.con.row_factory = before


if __name__ == "__main__":
    unittest.main()
