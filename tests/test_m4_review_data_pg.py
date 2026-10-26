"""M4-DL2: chỉ dữ liệu DEMO; PG do lead cấp DSN, không mở server/xóa DB.

PG tạo kho_test_* riêng, migrate sạch; login app_web thường, không SET ROLE.
Giữ DB/role DEMO để lead kiểm/dọn ngoài sandbox.
"""

from __future__ import annotations

import copy
import os
import secrets
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from unittest.mock import MagicMock, Mock, patch

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4.review_data_pg import (
    ReviewDataPG, dong_sha256, dto_man_hinh, real_sang_decimal,
)

try:
    import psycopg
    from psycopg import conninfo, sql
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None


DSN = os.environ.get("KHO_PG_DSN_TEST")
CHUP = "2026-10-26T07:00:00+07:00"
BANG = ("nguon", "che_do", "hop_dong", "tham_so", "tham_so_nguon")
ANH_XA_DEMO = {"DEMO-HD": (uuid.UUID(int=1), uuid.UUID(int=2))}
# 36 mã chuẩn + mã bổ sung: repository không được lọc theo enum vận hành.
MA_DEMO = (
    *(f"TC-{n:02d}" for n in range(1, 9)),
    *(f"TT-{n:02d}" for n in (1, 2, 3, 4, 5, 10, 11, 12, 20, 21, 22,
                              30, 31, 32, 33, 40, 41, 42, 50, 51, 52, 53,
                              54, 55, 56, 60, 61, 62)),
    "Y-DEMO-37",
)


def _demo():
    """Không đọc fixture, DB nguồn hay catalog Excel."""
    return {
        "che_do": [{"id": 1, "sua": 1}],
        "hop_dong": [dict(ma_hd="DEMO-HD", so_hd="DEMO/HĐ/01",
                          phan_loai="DEMO xây dựng", loai_gia="DEMO đơn giá",
                          ngay_ky="DEMO ngày chưa chuẩn hóa", goi_thau=None,
                          gia_tri_hd=-1234.125, gom_vat="", vat=0.08,
                          file_nguon="DEMO/private/hop-dong.docx", ngay_nap="")],
        "tham_so": [dict(ma_hd="DEMO-HD", ma_ts=ma, ten="DEMO " + ma,
                         gia_tri=None if i % 3 == 0 else "", don_vi=None,
                         dieu_khoan="DEMO Điều 1", trich_dan=" DEMO\nnguyên văn ",
                         trang_thai="DEMO chưa xác nhận") for i, ma in enumerate(MA_DEMO)],
        "tham_so_nguon": [dict(
            ma_hd="DEMO-HD", ma_ts=ma, gia_tri_ai="DEMO AI gốc", gia_tri="",
            kiem_tra=None, muc=i % 4, nguon="DEMO Local",
            da_xac_nhan=i % 2, da_sua_tay=(i // 2) % 2,
            nguoi_xac_nhan="DEMO người soát" if i % 2 else None,
            luc_xac_nhan="DEMO 26/10/2026 07:00" if i % 2 else None,
            ghi_chu_soat=" DEMO giữ nguyên " if i % 2 else "",
            lich_su='{"DEMO_login":"DEMO/private"}', model="DEMO model",
            may_ai="DEMO máy", luot="DEMO lượt", file_hop_dong="DEMO/private/hd.docx",
            sha1_file="a" * 40, luc_trich="DEMO không múi giờ", luc_nap=None,
        ) for i, ma in enumerate(MA_DEMO)],
    }


class ReviewDataTinh(unittest.TestCase):
    def test_hash_on_dinh_khong_phu_thuoc_thu_tu_khoa(self):
        first = {"DEMO": {"b": 0.1 + 0.2, "a": None}, "chuoi": " DEMO\n"}
        second = {"chuoi": " DEMO\n", "DEMO": {"a": None, "b": Decimal(repr(0.1 + 0.2))}}
        self.assertEqual(dong_sha256(first), dong_sha256(second))
        self.assertRegex(dong_sha256(first), r"^[0-9a-f]{64}$")
        self.assertNotEqual(dong_sha256({"a": None}), dong_sha256({"a": ""}))
        self.assertNotEqual(dong_sha256({"a": 1}), dong_sha256({"a": "1"}))

    def test_hash_decimal_khong_phu_thuoc_context_va_khong_sua_chuoi(self):
        number = Decimal("123456789012345678901234567890.12000")
        expected = dong_sha256({"DEMO": number})
        with localcontext() as ctx:
            ctx.prec = 2
            self.assertEqual(dong_sha256({"DEMO": number}), expected)
        self.assertEqual(expected, dong_sha256({"DEMO": Decimal("123456789012345678901234567890.12")}))
        self.assertNotEqual(dong_sha256({"DEMO": "é"}), dong_sha256({"DEMO": "e\u0301"}))

    def test_hash_am_zero_cung_hash_zero(self):
        expected = dong_sha256({"DEMO": Decimal("0")})
        for value in (Decimal("-0"), Decimal("-0.000"), Decimal("0E+8"), -0.0, 0.0):
            with self.subTest(value=repr(value)):
                self.assertEqual(dong_sha256({"DEMO": value}), expected)

    def test_real_decimal_repr_giu_am_zero_null(self):
        for value in (0.1, 0.1 + 0.2, -1234.125, -0.0):
            self.assertEqual(real_sang_decimal(value).as_tuple(), Decimal(repr(value)).as_tuple())
        self.assertIsNone(real_sang_decimal(None))
        self.assertEqual(real_sang_decimal(0), Decimal(0))
        self.assertNotEqual(real_sang_decimal(0.1), Decimal(0.1))
        for bad in (float("nan"), float("inf"), Decimal("NaN"), True, "0.1"):
            with self.subTest(bad=repr(bad)), self.assertRaises(DataError):
                real_sang_decimal(bad)

    def test_dto_allowlist_khong_lo_tep_actor_hay_ma_noi_bo(self):
        data = _demo()
        forbidden = dict(file_nguon="DEMO/private", file_hop_dong="DEMO/private",
                         sha1_file="DEMO", nhap_boi="DEMO_login", login="DEMO_login",
                         ma_hd="DEMO-HD", hop_dong_id="DEMO_UUID", du_an_id="DEMO_UUID",
                         chep_id="DEMO_UUID", dong_sha256="DEMO", nguon_id="DEMO")
        hd = dict(data["hop_dong"][0], **{k: v for k, v in forbidden.items() if k not in data["hop_dong"][0]})
        result = dto_man_hinh(hd, [dict(data["tham_so"][0], **{k: v for k, v in forbidden.items() if k not in data["tham_so"][0]})], data["tham_so_nguon"])

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & set(forbidden))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(result)
        self.assertIsInstance(result["hop_dong"]["gia_tri_hd"], Decimal)
        self.assertEqual(result["hop_dong"]["ngay_ky"], "DEMO ngày chưa chuẩn hóa")
        self.assertIsNone(result["hop_dong"]["goi_thau"])
        self.assertEqual(result["hop_dong"]["gom_vat"], "")
        self.assertNotIn("lich_su", result["tham_so_nguon"][0])
        self.assertEqual(len(result["tham_so_nguon"]), 37)

    def test_dto_khong_tao_xac_nhan_gia_hay_bo_ma_bo_sung(self):
        data = _demo()
        result = dto_man_hinh(data["hop_dong"][0], data["tham_so"], data["tham_so_nguon"])
        self.assertEqual(len(result["tham_so"]), 37)
        for actual, original in zip(result["tham_so_nguon"], data["tham_so_nguon"]):
            for key, value in actual.items():
                self.assertEqual(value, original[key])
        self.assertEqual(dto_man_hinh(data["hop_dong"][0], [], [])["tham_so"], [])

    def test_dto_null_bat_buoc_phan_biet_ba_trang_thai(self):
        messages = {
            "CHUA_CO_LAN_CHUP": "Chưa nạp dữ liệu Review.",
            "CHUA_CO_TRONG_NGUON": "Hợp đồng chưa có trong dữ liệu Review.",
            "DA_XOA_O_NGUON": "Hợp đồng đã bị xóa ở dữ liệu Review (lần chụp mới nhất).",
        }
        for state, message in messages.items():
            with self.subTest(state=state):
                self.assertEqual(dto_man_hinh(None, [], [], trang_thai=state), {
                    "trang_thai": state, "thong_bao": message,
                    "hop_dong": None, "tham_so": [], "tham_so_nguon": []})
        with self.assertRaises(DataError):
            dto_man_hinh(None, [], [])

    def test_chuan_bi_hash_gom_anh_xa_khong_sua_input(self):
        data = _demo()
        original = copy.deepcopy(data)
        rows = ReviewDataPG._chuan_bi(data, ANH_XA_DEMO)
        self.assertEqual(data, original)
        hd = rows["hop_dong"][("DEMO-HD",)]
        self.assertEqual(hd["gia_tri_hd"], Decimal(repr(data["hop_dong"][0]["gia_tri_hd"])))
        reordered = {t: [dict(reversed(list(r.items()))) for r in reversed(rs)] for t, rs in reversed(list(data.items()))}
        self.assertEqual(rows, ReviewDataPG._chuan_bi(reordered, ANH_XA_DEMO))
        other = ReviewDataPG._chuan_bi(data, {"DEMO-HD": (uuid.UUID(int=3), uuid.UUID(int=2))})
        self.assertNotEqual(hd["dong_sha256"], other["hop_dong"][("DEMO-HD",)]["dong_sha256"])

    def test_thieu_anh_xa_dung_truoc_giao_dich(self):
        conn = Mock()
        repo = ReviewDataPG(conn)
        with self.assertRaises(DataError) as caught:
            repo.ghi_lan_chup(_demo(), nguon_id="DEMO", chup_luc=CHUP, nhap_boi="DEMO", anh_xa={})
        self.assertEqual(caught.exception.code, "M4_REVIEW_THIEU_ANH_XA")
        conn.transaction.assert_not_called()
        conn.execute.assert_not_called()

    def test_hai_ma_hd_trung_hop_dong_id_dung_truoc_giao_dich(self):
        conn, data = Mock(), _demo()
        data["hop_dong"].append(dict(data["hop_dong"][0], ma_hd="DEMO-KHAC", so_hd="DEMO/02"))
        mapping = dict(ANH_XA_DEMO, **{"DEMO-KHAC": tuple(str(v) for v in ANH_XA_DEMO["DEMO-HD"])})
        with self.assertRaisesRegex(DataError, "Hai ma_hd ánh xạ vào cùng hop_dong_id") as caught:
            ReviewDataPG(conn).ghi_lan_chup(data, nguon_id="DEMO", chup_luc=CHUP,
                                           nhap_boi="DEMO", anh_xa=mapping)
        self.assertEqual(caught.exception.code, "M4_REVIEW_DU_LIEU_SAI")
        conn.transaction.assert_not_called()
        conn.execute.assert_not_called()

    def test_doc_bat_buoc_phien_va_chan_truoc_doc_chu_bang(self):
        owner, session = Mock(), Mock()
        repo = ReviewDataPG(owner)
        with self.assertRaises(TypeError):
            repo.doc_hien_hanh(uuid.UUID(int=1))
        for denied in (None, owner, session):
            for result in ((False,), {"duoc": False}):
                session.execute.return_value.fetchone.return_value = result
                with self.subTest(denied=denied, result=result), self.assertRaises(DataError) as caught:
                    repo.doc_hien_hanh(uuid.UUID(int=1), conn_phien=denied)
                self.assertEqual(caught.exception.code, "404")
                self.assertEqual(str(caught.exception), "Không tìm thấy hợp đồng.")
        query, params = session.execute.call_args.args
        self.assertIn("master.hop_dong", query)
        self.assertIn("master.m4_duoc(h.du_an_id, 'XEM')", query)
        self.assertIn("master.m4_duoc(h.du_an_id, 'REVIEW')", query)
        self.assertEqual(params, (str(uuid.UUID(int=1)),))
        owner.transaction.assert_not_called()
        owner.execute.assert_not_called()

    def test_doc_null_hai_exists_cung_giao_dich_sau_kiem_quyen(self):
        for session_result in ((True,), {"duoc": True}):
            for co_nguon, co_hd, state in (
                (False, False, "CHUA_CO_LAN_CHUP"),
                (True, False, "CHUA_CO_TRONG_NGUON"),
                (True, True, "DA_XOA_O_NGUON"),
            ):
                owner, session = MagicMock(), Mock()
                session.execute.return_value.fetchone.return_value = session_result
                repo, active = ReviewDataPG(owner), []
                owner.transaction.return_value.__enter__.side_effect = lambda: active.append(True)
                owner.transaction.return_value.__exit__.side_effect = lambda *args: active.pop() and False
                values = iter(([{"nguon_id": None}], [{"co": co_nguon}], [{"co": co_hd}]))

                def read(query, params=()):
                    self.assertEqual(active, [True])
                    session.execute.assert_called_once()
                    return next(values)

                with self.subTest(state=state, session_result=session_result), patch.object(repo, "_rows", side_effect=read) as rows:
                    result = repo.doc_hien_hanh(uuid.UUID(int=1), conn_phien=session)
                self.assertEqual(result, dto_man_hinh(None, [], [], trang_thai=state))
                self.assertEqual(rows.call_count, 3)
                self.assertIn("SELECT EXISTS (SELECT 1 FROM m4.review_chep_nguon)", rows.call_args_list[1].args[0])
                self.assertIn("WHERE hop_dong_id=%s::uuid", rows.call_args_list[2].args[0])
                self.assertEqual(rows.call_args_list[2].args[1], (str(uuid.UUID(int=1)),))
                self.assertEqual(active, [])

    def test_replay_bao_ro_truong_khac_khong_ghi(self):
        for field in ("chup_luc", "nhap_boi", "mo_ta", "dong_sha256", "hop_dong_id", "du_an_id"):
            owner = MagicMock()
            repo = ReviewDataPG(owner)
            prepared = repo._chuan_bi(_demo(), ANH_XA_DEMO)
            metadata = {"mo_ta": None, "chup_luc": datetime(2026, 10, 26, tzinfo=timezone.utc), "nhap_boi": "DEMO"}
            if field in metadata:
                metadata[field] = None if field == "chup_luc" else "DEMO khác"
            responses = [[metadata]]
            if field not in metadata:
                for table in ("che_do", "hop_dong"):
                    rows = [dict(r) for r in prepared[table].values()]
                    if table == "hop_dong":
                        rows[0][field] = "b" * 64 if field == "dong_sha256" else str(uuid.UUID(int=9))
                    responses.append(rows)
            with self.subTest(field=field), patch.object(repo, "_rows", side_effect=responses):
                with self.assertRaises(DataError) as caught:
                    repo.ghi_lan_chup(_demo(), nguon_id="DEMO", chup_luc=CHUP,
                                       nhap_boi="DEMO", anh_xa=ANH_XA_DEMO)
                self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
                self.assertIn(field, str(caught.exception))
                self.assertEqual(owner.execute.call_count, 1)  # chỉ khóa tư vấn, chưa INSERT

    def test_khong_tu_suy_timezone_hay_bo_cot_bang_la(self):
        conn = Mock()
        repo = ReviewDataPG(conn)
        base = dict(nguon_id="DEMO", chup_luc=CHUP, nhap_boi="DEMO", anh_xa=ANH_XA_DEMO)
        for moment in (None, "2026-10-26 07:00", datetime(2026, 10, 26), "DEMO ngày sai"):
            with self.subTest(moment=moment), self.assertRaises(DataError):
                repo.ghi_lan_chup(_demo(), **dict(base, chup_luc=moment))
        data = _demo()
        data["hop_dong"][0]["DEMO_cot_la"] = "DEMO"
        with self.assertRaises(DataError):
            repo.ghi_lan_chup(data, **base)
        data = _demo()
        data.pop("tham_so_nguon")
        with self.assertRaises(DataError):
            repo.ghi_lan_chup(data, **base)
        conn.transaction.assert_not_called()

    def test_trung_khoa_va_orphan_bi_tu_choi(self):
        data = _demo()
        data["tham_so"].append(dict(data["tham_so"][0]))
        with self.assertRaises(DataError):
            ReviewDataPG._chuan_bi(data, ANH_XA_DEMO)
        data = _demo()
        data["hop_dong"] = []
        with self.assertRaises(DataError):
            ReviewDataPG._chuan_bi(data, ANH_XA_DEMO)


@unittest.skipUnless(DSN and psycopg is not None, "Thiếu KHO_PG_DSN_TEST/psycopg — PG do lead chạy (NOT_RUN)")
class ReviewDataPGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_m4_dl2_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = conninfo.make_conninfo(DSN, dbname=cls.db)
        cls.con = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.con.close)
        pg.migrate(cls.con)
        cls.pn = cls.con.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES ('DEMO_DL2','Pháp nhân DEMO DL2') RETURNING id").fetchone()[0]
        cls.da = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_DL2','Dự án DEMO DL2') RETURNING id", (cls.pn,)).fetchone()[0]
        cls.da_khac = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_DL2_KHAC','Dự án DEMO khác') RETURNING id", (cls.pn,)).fetchone()[0]
        cls.actors = {}
        for name, project, permission in (("XEM", cls.da, "XEM"), ("REVIEW", cls.da, "REVIEW"), ("KHAC", cls.da_khac, "XEM")):
            login = "MO_PHONG_DL2_" + name
            actor = cls.con.execute("""INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro)
                VALUES (%s,%s,'XEM') RETURNING id""", (login, login)).fetchone()[0]
            cls.con.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['M4'])", (actor, cls.pn))
            cls.con.execute("""INSERT INTO m4.quyen_du_an (nguoi_dung_id,phap_nhan_id,du_an_id,vai)
                VALUES (%s,%s,%s,%s)""", (actor, cls.pn, project, permission))
            cls.actors[name] = (str(actor), login)
        cls.role, password = "ktt_test_dl2_" + uuid.uuid4().hex[:12], secrets.token_hex(16)
        cls.con.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web").format(
            sql.Identifier(cls.role), sql.Literal(password)))
        cls.web = psycopg.connect(conninfo.make_conninfo(cls.dsn, user=cls.role, password=password), autocommit=True)
        cls.addClassCleanup(cls.web.close)

    def setUp(self):
        self.repo = ReviewDataPG(self.con)
        # Master HĐ phải hiển thị trên login thường trước giao dịch chép rollback.
        self.hd = self._master_hd()
        self.enterContext(self.con.transaction(force_rollback=True))
        self.enterContext(self.web.transaction(force_rollback=True))
        self._phien("XEM")
        self.mapping = {"DEMO-HD": (self.hd, self.da)}
        self.source = "DEMO-DL2-" + uuid.uuid4().hex

    def _phien(self, name):
        self.web.execute("""SELECT set_config('ktt.nguoi_dung_id',%s,true),
            set_config('ktt.nguoi_dung_dang_nhap',%s,true)""", self.actors[name])

    def _doc(self, hop_dong_id=None):
        return self.repo.doc_hien_hanh(self.hd if hop_dong_id is None else hop_dong_id, conn_phien=self.web)

    def _master_hd(self):
        code = "DEMO-DL2-" + uuid.uuid4().hex
        hd = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()[0]
        self.con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'Hồ sơ DEMO DL2','MO_PHONG_DEMO')""", (hd, self.pn, self.da))
        return hd

    def _ghi(self, data=None, **changes):
        args = dict(nguon_id=self.source, chup_luc=CHUP, nhap_boi="MO_PHONG_DEMO", anh_xa=self.mapping, mo_ta="DEMO DL2")
        args.update(changes)
        return self.repo.ghi_lan_chup(_demo() if data is None else data, **args)

    def _counts(self, source=None):
        return {t: self.con.execute(f"SELECT count(*) FROM m4.review_chep_{t} WHERE {'id' if t == 'nguon' else 'nguon_id'}=%s",
                                    (self.source if source is None else source,)).fetchone()[0] for t in BANG}

    def test_ghi_doc_du_37_tham_so_va_decimal(self):
        self.assertEqual(self._ghi(), 77)
        dto = self._doc()
        self.assertEqual(dto["trang_thai"], "HIEN_HANH")
        self.assertEqual(len(dto["tham_so"]), 37)
        self.assertEqual(len(dto["tham_so_nguon"]), 37)
        self.assertEqual(dto["hop_dong"]["gia_tri_hd"], Decimal("-1234.125"))
        self.assertEqual(dto["hop_dong"]["vat"], Decimal("0.08"))
        self.assertEqual(dto["hop_dong"]["ngay_ky"], "DEMO ngày chưa chuẩn hóa")
        self.assertEqual(self._counts(), dict(nguon=1, che_do=1, hop_dong=1, tham_so=37, tham_so_nguon=37))

    def test_replay_khong_tang_dong_ke_ca_thu_tu_khac(self):
        self._ghi()
        before = self._counts()
        data = {t: list(reversed(rows)) for t, rows in _demo().items()}
        self.assertEqual(self._ghi(data, chup_luc="2026-10-26T00:00:00+00:00"), 0)
        self.assertEqual(self._counts(), before)

    def test_cung_khoa_khac_hash_khong_ghi_de(self):
        self._ghi()
        before = self._doc()
        data = _demo()
        data["tham_so_nguon"][0]["da_xac_nhan"] = 1
        with self.assertRaises(DataError) as caught:
            self._ghi(data)
        self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
        self.assertIn("dong_sha256", str(caught.exception))
        self.assertEqual(self._doc(), before)
        self.assertEqual(self._counts()["tham_so_nguon"], 37)

    def test_replay_khong_cho_them_bot_dong_hay_doi_metadata(self):
        self._ghi()
        before = self._counts()
        for change in ("them", "bot", "chup_luc", "anh_xa", "nhap_boi"):
            data, args = _demo(), {}
            if change == "them":
                data["tham_so"].append(dict(data["tham_so"][0], ma_ts="Y-DEMO-38"))
            elif change == "bot":
                data["tham_so"] = data["tham_so"][:-1]
            elif change == "chup_luc":
                args["chup_luc"] = "2026-10-27T07:00:00+07:00"
            elif change == "anh_xa":
                args["anh_xa"] = {"DEMO-HD": (self._master_hd(), self.da)}
            else:
                args["nhap_boi"] = "MO_PHONG_DEMO_KHAC"
            with self.subTest(change=change), self.assertRaises(DataError) as caught:
                self._ghi(data, **args)
            expected = "tập khóa" if change in ("them", "bot") else "ánh xạ" if change == "anh_xa" else change
            self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
            self.assertIn(expected, str(caught.exception))
            self.assertEqual(self._counts(), before)

    def test_thieu_anh_xa_dung_ca_lan_chup_khong_ghi(self):
        data = _demo()
        data["hop_dong"].append(dict(data["hop_dong"][0], ma_hd="DEMO-THIEU", so_hd="DEMO/THIEU"))
        with self.assertRaises(DataError):
            self._ghi(data)
        self.assertEqual(set(self._counts().values()), {0})

    def test_lan_chup_moi_vang_hd_tra_da_xoa(self):
        self._ghi()
        empty = {t: [] for t in _demo()}
        self._ghi(empty, nguon_id="DEMO-MOI", chup_luc="2026-10-27T07:00:00+07:00")
        self.assertEqual(self._doc(), dto_man_hinh(None, [], [], trang_thai="DA_XOA_O_NGUON"))
        self.assertEqual(self._counts()["hop_dong"], 1)

    def test_chua_co_lan_chup(self):
        self.assertEqual(self._doc(), dto_man_hinh(None, [], [], trang_thai="CHUA_CO_LAN_CHUP"))

    def test_hop_dong_chua_tung_co_trong_nguon(self):
        self._ghi({t: [] for t in _demo()})
        self.assertEqual(self._doc(), dto_man_hinh(None, [], [], trang_thai="CHUA_CO_TRONG_NGUON"))

    def test_khong_quyen_du_an_tra_404_khong_lo_hop_dong(self):
        self._ghi()
        self._phien("KHAC")  # Có XEM + module M4, nhưng thuộc dự án khác.
        errors = []
        with patch.object(self.repo, "_rows", wraps=self.repo._rows) as rows:
            for hd in (self.hd, uuid.uuid4()):
                with self.assertRaises(DataError) as caught:
                    self._doc(hd)
                errors.append((caught.exception.code, str(caught.exception)))
            rows.assert_not_called()
        self.assertEqual(errors, [("404", "Không tìm thấy hợp đồng.")] * 2)

    def test_co_xem_doc_duoc_bang_login_thuong(self):
        self._ghi()
        self.assertEqual(self.web.execute("SELECT current_user").fetchone()[0], self.role)
        self.assertTrue(self.web.execute("SELECT master.m4_duoc(%s,'XEM')", (self.da,)).fetchone()[0])
        self.assertEqual(self._doc()["trang_thai"], "HIEN_HANH")
        # Quyền đọc bảng nguồn vẫn không cấp cho app_web.
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.web.transaction():
                self.web.execute("SELECT * FROM m4.review_chep_nguon")

    def test_chi_co_review_van_doc_duoc(self):
        self._ghi()
        self._phien("REVIEW")
        self.assertFalse(self.web.execute("SELECT master.m4_duoc(%s,'XEM')", (self.da,)).fetchone()[0])
        self.assertTrue(self.web.execute("SELECT master.m4_duoc(%s,'REVIEW')", (self.da,)).fetchone()[0])
        self.assertEqual(self._doc()["trang_thai"], "HIEN_HANH")

    def test_anh_xa_trung_hop_dong_id_la_data_error(self):
        data = _demo()
        data["hop_dong"].append(dict(data["hop_dong"][0], ma_hd="DEMO-KHAC", so_hd="DEMO/02"))
        mapping = dict(self.mapping, **{"DEMO-KHAC": (self.hd, self.da)})
        with self.assertRaisesRegex(DataError, "cùng hop_dong_id"):
            self._ghi(data, anh_xa=mapping)
        self.assertEqual(set(self._counts().values()), {0})

    def test_xac_nhan_tung_o_khong_bi_suy_tu_trang_thai_hd(self):
        data = _demo()
        self._ghi(data)
        actual = {r["ma_ts"]: r for r in self._doc()["tham_so_nguon"]}
        for row in data["tham_so_nguon"]:
            for key, value in actual[row["ma_ts"]].items():
                self.assertEqual(value, row[key], (row["ma_ts"], key))

    def test_loi_giua_chung_rollback_ca_nguon_va_cac_bang(self):
        data = _demo()
        # HĐ + 37 tham số + 36 nguồn gốc đã INSERT trước NOT NULL cuối cùng.
        data["tham_so_nguon"][-1]["da_xac_nhan"] = None
        with self.assertRaises(psycopg.errors.NotNullViolation):
            self._ghi(data)
        self.assertEqual(set(self._counts().values()), {0})
        # Kết nối vẫn dùng được; retry đúng phải nạp đủ, không còn hàng dở.
        self.assertEqual(self._ghi(), 77)

    def test_nap_bu_cu_khong_lui_hien_hanh_va_null_khong_thanh_zero(self):
        self._ghi()
        data = _demo()
        data["hop_dong"][0]["gia_tri_hd"] = None
        data["hop_dong"][0]["vat"] = None
        self._ghi(data, nguon_id="DEMO-CU", chup_luc="2026-10-25T07:00:00+07:00")
        self.assertEqual(self._doc()["hop_dong"]["gia_tri_hd"], Decimal("-1234.125"))
        self._ghi(data, nguon_id="DEMO-MOI", chup_luc="2026-10-27T07:00:00+07:00")
        hd = self._doc()["hop_dong"]
        self.assertIsNone(hd["gia_tri_hd"])
        self.assertIsNone(hd["vat"])

    def test_dict_row_va_real_repr_toi_numeric(self):
        # Một connection riêng chứng minh đường top-level transaction + dict_row.
        # Master HĐ commit trước để login thường thấy; bản chép vẫn rollback.
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as con:
            code = "DEMO-DICT-" + uuid.uuid4().hex
            hd = con.execute("""INSERT INTO master.hop_dong
                (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
                VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()["id"]
            con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
                VALUES (%s,%s,%s,'DEMO dict','MO_PHONG_DEMO')""", (hd, self.pn, self.da))
            with con.transaction(force_rollback=True):
                repo, data = ReviewDataPG(con), _demo()
                data["hop_dong"][0]["gia_tri_hd"] = 0.1 + 0.2
                repo.ghi_lan_chup(data, nguon_id="DEMO-DICT", chup_luc=CHUP,
                                  nhap_boi="MO_PHONG_DEMO", anh_xa={"DEMO-HD": (hd, self.da)})
                self.assertEqual(repo.doc_hien_hanh(hd, conn_phien=self.web)["hop_dong"]["gia_tri_hd"], Decimal(repr(0.1 + 0.2)))


if __name__ == "__main__":
    unittest.main()
