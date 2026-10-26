"""M4-DL4: dữ liệu DEMO, không đọc Review thật hay khởi động dịch vụ.

PG dùng KHO_PG_DSN_TEST quản trị để tự tạo kho_test_* và login thường.
Không xóa CSDL/role; lead kiểm/dọn sau. Thiếu DSN/driver thì báo NOT_RUN.
"""

from __future__ import annotations

import copy
import os
import secrets
import unittest
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, Mock

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4.review_data_pg import MA_HTTP
from kho_tri_thuc.m4.review_dot_pg import ReviewDotPG, chuan_bi_dong, dto_dot
from kho_tri_thuc.m4.sql_review_chep import BANG_NGUON

try:
    import psycopg
    from psycopg import conninfo, sql
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None


DSN = os.environ.get("KHO_PG_DSN_TEST")
CHUP = "2026-10-26T07:00:00+07:00"
THOI_DIEM = " 26/10/2026 07:00:01\nkhông múi giờ "
CHI_TIET = ' { "DEMO": [null, "Đã nộp", ""] }\n'
CONTRACTS = {"DEMO-HD": dict(hop_dong_id=uuid.UUID(int=1), du_an_id=uuid.UUID(int=2))}


def _demo():
    return dict(
        dot_thanh_toan=[
            dict(ma_hd="DEMO-HD", dot=1, ngay_nghiem_thu="DEMO ngày chưa chuẩn",
                 ngay_nhan_hs="", gt_ky=0.1 + 0.2, gt_luy_ke=-123.125,
                 giu_lai=None, thu_hoi_tu=0, gt_tt_ky=91.25,
                 file_nguon="DEMO/private/hs.xlsx", ngay_nap=None),
            dict(ma_hd="DEMO-HD", dot=2, gt_ky=None, gt_luy_ke=20.5),
        ],
        kl_thanh_toan=[
            dict(ma_hd="DEMO-HD", dot=1, ma_hm="DEMO-A", kl_ky=-0.1,
                 kl_luy_ke=None, don_gia_tt=123.4, vi_tri_nguon="DEMO/private/hs.xlsx!A1"),
            dict(ma_hd="DEMO-HD", dot=2, ma_hm="DEMO-B", kl_ky=None),
        ],
        khop_hang_muc=[
            dict(ma_hd="DEMO-HD", khoa_hstt="DEMO-khoa", ma_hm="DEMO-A",
                 cach_khop="DEMO tay", nguoi_xac_nhan=" DEMO người lịch sử ", ngay=THOI_DIEM),
            dict(ma_hd="DEMO-MO-COI", khoa_hstt="DEMO-orphan", ma_hm="DEMO-O"),
        ],
        canh_bao=[
            dict(id=1, ma_hd="DEMO-HD", pl_id=999, dot=1, ma_kt="DEMO-K01",
                 muc_do="DEMO đỏ", noi_dung=" DEMO cảnh báo\n ", thoi_diem=THOI_DIEM),
            dict(id=2, ma_hd="DEMO-MO-COI", noi_dung="DEMO orphan"),
            dict(id=3, ma_hd=None, noi_dung="DEMO toàn cục"),
        ],
        nhat_ky=[
            dict(id=1, ma_hd="DEMO-HD", thoi_diem=THOI_DIEM,
                 nguoi=" DEMO người cũ ", thao_tac="DA_NOP", chi_tiet=CHI_TIET),
            dict(id=2, ma_hd="DEMO-MO-COI", chi_tiet="DEMO không phải JSON"),
            dict(id=3, ma_hd="", thoi_diem="", chi_tiet=None),
        ],
    )


def _base():
    return dict(che_do=[dict(id=1, sua=0)],
                hop_dong=[dict(ma_hd="DEMO-HD", so_hd="DEMO/DL4", gia_tri_hd=100.1)],
                tham_so=[dict(ma_hd="DEMO-HD", ma_ts="DEMO-TS", gia_tri=None)],
                tham_so_nguon=[dict(ma_hd="DEMO-HD", ma_ts="DEMO-TS", gia_tri="")])


def _dl3():
    return dict(phu_luc=[dict(id=1, ma_hd="DEMO-HD", so_pl="DEMO-PL",
                            ngay_ky="2026-10-01", ngay_hieu_luc="2026-10-01",
                            doi_boq=0, trang_thai="Đã ký")],
                thay_doi_tham_so=[dict(pl_id=1, ma_ts="DEMO-TS", gia_tri_moi="DEMO mới")],
                boq_dong=[dict(id=1, ma_hd="DEMO-HD", ma_hm="DEMO-A", thao_tac="GOC", kl=1.25)])


def _dto(data=None):
    data = _demo() if data is None else data
    # Chỉ các dòng thuộc HĐ đang đọc, không đưa orphan vào DTO của HĐ.
    return dto_dot(**{t: [r for r in rows if r.get("ma_hd") == "DEMO-HD"] for t, rows in data.items()})


class ReviewDotTinh(unittest.TestCase):
    def test_chuan_hoa_decimal_repr_null_chuoi_va_khong_sua_input(self):
        data = _demo()
        before = copy.deepcopy(data)
        prepared = chuan_bi_dong(data, CONTRACTS)
        self.assertEqual(data, before)
        dot = prepared["dot_thanh_toan"][("DEMO-HD", 1)]
        self.assertEqual(dot["gt_ky"], Decimal(repr(0.1 + 0.2)))
        self.assertEqual(dot["gt_luy_ke"], Decimal("-123.125"))
        self.assertIsNone(dot["giu_lai"])
        self.assertEqual(dot["thu_hoi_tu"], Decimal(0))
        self.assertEqual(dot["ngay_nhan_hs"], "")
        self.assertEqual(dot["ngay_nghiem_thu"], "DEMO ngày chưa chuẩn")
        self.assertEqual(dot["hop_dong_id"], str(uuid.UUID(int=1)))
        self.assertEqual(prepared["kl_thanh_toan"][("DEMO-HD", 1, "DEMO-A")]["du_an_id"], str(uuid.UUID(int=2)))
        self.assertEqual(prepared["nhat_ky"][(1,)]["chi_tiet"], CHI_TIET)
        self.assertEqual(prepared, chuan_bi_dong({t: list(reversed(r)) for t, r in data.items()}, CONTRACTS))

    def test_so_thieu_khong_thanh_khong_trong_luu_va_dto(self):
        prepared = chuan_bi_dong(_demo(), CONTRACTS)
        dto = _dto()
        for col in ("gt_ky", "giu_lai", "thu_hoi_tu", "gt_tt_ky"):
            self.assertIsNone(prepared["dot_thanh_toan"][("DEMO-HD", 2)][col])
            self.assertIsNone(dto["dot_thanh_toan"][1][col])
        for col in ("kl_ky", "kl_luy_ke", "don_gia_tt"):
            self.assertIsNone(dto["kl_thanh_toan"][1][col])
        self.assertIsInstance(dto["dot_thanh_toan"][0]["gt_tt_ky"], Decimal)

    def test_orphan_khong_gan_nham_anh_xa_hd_cu(self):
        # Mapping đầu vào chỉ có HĐ của lần chụp, không suy dự án cho orphan.
        prepared = chuan_bi_dong(_demo(), CONTRACTS)
        for table in ("khop_hang_muc", "canh_bao", "nhat_ky"):
            for row in prepared[table].values():
                with self.subTest(table=table, code=row["ma_hd"]):
                    if row["ma_hd"] != "DEMO-HD":
                        self.assertIsNone(row["hop_dong_id"])
                        self.assertIsNone(row["du_an_id"])

    def test_dto_khong_lo_truong_cam_khong_suy_actor_hay_duyet(self):
        forbidden = {"file_nguon", "vi_tri_nguon", "nhap_boi", "id", "pl_id", "ma_hd",
                     "nguon_id", "hop_dong_id", "du_an_id", "chep_id", "dong_sha256",
                     "khoa_hstt", "m4_dot_id", "m4_map_id", "m4_run_id", "m4_nhat_ky_id",
                     "actor", "actor_id", "da_duyet", "seal", "trang_thai_duyet"}
        data = _demo()
        for rows in data.values():
            for row in rows:
                row.update({c: "DEMO/private" for c in forbidden if c not in row})
        result = dto_dot(**data)
        for rows in result.values():
            for row in rows:
                self.assertFalse(set(row) & forbidden)
                self.assertNotIn("DEMO/private", row.values())
        self.assertEqual(result["khop_hang_muc"][0]["nguoi_xac_nhan"], " DEMO người lịch sử ")
        self.assertEqual(result["nhat_ky"][0], dict(thoi_diem=THOI_DIEM,
                         nguoi=" DEMO người cũ ", thao_tac="DA_NOP", chi_tiet=CHI_TIET))

    def test_hash_bao_toan_file_chuoi_va_null_khac_rong(self):
        before = chuan_bi_dong(_demo(), CONTRACTS)
        for table, col, value in (("dot_thanh_toan", "file_nguon", "DEMO/khac.xlsx"),
                                  ("nhat_ky", "chi_tiet", CHI_TIET.strip()),
                                  ("nhat_ky", "thoi_diem", THOI_DIEM.strip()),
                                  ("canh_bao", "noi_dung", None),
                                  ("dot_thanh_toan", "ngay_nhan_hs", None)):
            data = _demo()
            data[table][0][col] = value
            key = next(iter(before[table]))
            with self.subTest(table=table, col=col):
                self.assertNotEqual(before[table][key]["dong_sha256"],
                                    chuan_bi_dong(data, CONTRACTS)[table][key]["dong_sha256"])

    def test_chan_thieu_bang_trung_khoa_fk_va_kieu_sai(self):
        for change in ("bang", "trung", "cot", "fk_dot", "anh_xa", "nan", "inf",
                       "bool", "chuoi_so", "ngay", "id", "id_lon", "ma_hm"):
            data, contracts = _demo(), CONTRACTS
            if change == "bang":
                data.pop("canh_bao")
            elif change == "trung":
                data["nhat_ky"].append(dict(data["nhat_ky"][0]))
            elif change == "cot":
                data["nhat_ky"][0]["actor_id"] = "DEMO"
            elif change == "fk_dot":
                data["kl_thanh_toan"][0]["dot"] = 999
            elif change == "anh_xa":
                contracts = {}
            elif change in ("nan", "inf", "bool", "chuoi_so"):
                data["dot_thanh_toan"][0]["gt_ky"] = dict(nan=float("nan"), inf=float("inf"),
                                                           bool=True, chuoi_so="1.23")[change]
            elif change == "ngay":
                data["nhat_ky"][0]["thoi_diem"] = 123
            elif change in ("id", "id_lon"):
                data["canh_bao"][0]["id"] = True if change == "id" else 2**63
            else:
                data["khop_hang_muc"][0]["ma_hm"] = None
            with self.subTest(change=change), self.assertRaises(DataError):
                chuan_bi_dong(data, contracts)

    def test_ghi_rieng_can_transaction_va_replay_bool(self):
        for status, replay in ((0, False), (2, 0), (2, None)):
            owner = Mock()
            owner.info.transaction_status = status
            with self.subTest(status=status, replay=replay), self.assertRaises(DataError):
                ReviewDotPG(owner).ghi_trong_giao_dich(_demo(), nguon_id="DEMO", nhap_boi="DEMO", replay=replay)
            owner.execute.assert_not_called()


class ReviewDotDocTinh(unittest.TestCase):
    def test_thieu_phien_khong_quyen_uuid_sai_deu_404_truoc_doc_owner(self):
        owner, session = Mock(), Mock()
        repo = ReviewDotPG(owner)
        for allowed in ((False,), {"duoc": False}):
            session.execute.return_value.fetchone.return_value = allowed
            for conn in (None, owner, session):
                for identity in (uuid.UUID(int=1), uuid.uuid4(), "DEMO-sai-uuid"):
                    with self.subTest(conn=conn, identity=identity), self.assertRaises(DataError) as caught:
                        repo.doc_hien_hanh(identity, conn_phien=conn)
                    self.assertEqual(caught.exception.code, "M4_REVIEW_KHONG_THAY")
                    self.assertEqual(MA_HTTP[caught.exception.code], 404)
        with self.assertRaises(DataError):
            repo.doc_hien_hanh(uuid.UUID(int=1))
        owner.execute.assert_not_called()
        owner.transaction.assert_not_called()
        query = session.execute.call_args.args[0]
        self.assertIn("master.m4_duoc(h.du_an_id, 'XEM')", query)
        self.assertIn("master.m4_duoc(h.du_an_id, 'REVIEW')", query)

    def _owner(self, session, batches, tuple_rows=False):
        owner = MagicMock()

        def execute(query, params=()):
            session.execute.assert_called_once()
            rows = batches.pop(0)
            cursor = Mock()
            columns = list(rows[0]) if rows else []
            cursor.description = [Mock(name=c) for c in columns]
            for desc, col in zip(cursor.description, columns):
                desc.name = col
            cursor.fetchall.return_value = [tuple(r.get(c) for c in columns) for r in rows] if tuple_rows else rows
            return cursor

        owner.execute.side_effect = execute
        return owner

    def test_ba_trang_thai_null_cua_dl2(self):
        for co_nguon, co_hd, state in ((False, False, "CHUA_CO_LAN_CHUP"),
                                     (True, False, "CHUA_CO_TRONG_NGUON"),
                                     (True, True, "DA_XOA_O_NGUON")):
            session = Mock()
            session.execute.return_value.fetchone.return_value = (True,)
            current = [dict(nguon_id=None, co_nguon=co_nguon, co_hd=co_hd)]
            batches = [current, current]
            owner = self._owner(session, batches)
            with self.subTest(state=state):
                actual = ReviewDotPG(owner).doc_hien_hanh(uuid.UUID(int=1), conn_phien=session)
                self.assertEqual(actual, dict(dto_dot([], [], [], [], []), trang_thai=state))
                self.assertEqual(batches, [])
                for call in owner.execute.call_args_list:
                    self.assertEqual(call.args[0].count("EXISTS"), 2)

    def test_doc_ghim_mot_nguon_sau_kiem_quyen_ca_tuple_va_dict(self):
        for tuple_rows in (False, True):
            session = Mock()
            session.execute.return_value.fetchone.return_value = {"duoc": True}
            current = [dict(nguon_id="DEMO-MOI", co_nguon=True, co_hd=True)]
            data = {t: [r for r in rows if r.get("ma_hd") == "DEMO-HD"] for t, rows in _demo().items()}
            # Public DL2: nguồn, HĐ, tham số, nguồn từng ô; DL4: nguồn rồi 5 bảng.
            batches = [current, _base()["hop_dong"], [], [], current, *data.values()]
            owner = self._owner(session, batches, tuple_rows)
            with self.subTest(tuple_rows=tuple_rows):
                actual = ReviewDotPG(owner).doc_hien_hanh(uuid.UUID(int=1), conn_phien=session)
                self.assertEqual(actual, dict(_dto(), trang_thai="HIEN_HANH"))
                self.assertEqual(batches, [])
                for call in owner.execute.call_args_list[-5:]:
                    self.assertEqual(call.args[1], ("DEMO-MOI", str(uuid.UUID(int=1))))


class ReviewDotGhiTinh(unittest.TestCase):
    """Kiểm SQL/giá trị gửi driver khi không có DSN; không thay test PG."""

    def _owner(self, existing=None, source=True):
        owner = Mock()
        owner.info.transaction_status = 2
        inserts = []

        def execute(query, params=()):
            cursor = Mock()
            rows = []
            if query.startswith("SELECT nhap_boi"):
                rows = [dict(nhap_boi="DEMO")] if source else []
            elif query.startswith("SELECT ma_hd,hop_dong_id"):
                rows = [dict(ma_hd=code, **mapping) for code, mapping in CONTRACTS.items()]
            elif query.startswith("SELECT ") and "dong_sha256 FROM" in query:
                table = query.split("m4.review_chep_", 1)[1].split()[0]
                rows = list((existing or {}).get(table, {}).values())
            elif query.startswith("INSERT "):
                table = query.split("m4.review_chep_", 1)[1].split()[0]
                columns = query.split(" (", 1)[1].split(")", 1)[0].split(",")
                inserts.append((table, dict(zip(columns, params))))
                cursor.rowcount = 0 if existing is not None else 1
            cursor.description = [Mock() for _ in (rows[0] if rows else ())]
            for desc, column in zip(cursor.description, rows[0] if rows else ()):
                desc.name = column
            cursor.fetchall.return_value = rows
            return cursor

        owner.execute.side_effect = execute
        return owner, inserts

    def test_ghi_du_nam_bang_giu_decimal_null_chuoi_va_orphan(self):
        owner, inserts = self._owner()
        count = ReviewDotPG(owner).ghi_trong_giao_dich(
            _demo(), nguon_id="DEMO-NGUON", nhap_boi="DEMO", replay=False)
        self.assertEqual(count, 12)
        self.assertEqual({t for t, _ in inserts}, set(_demo()))
        for table, row in inserts:
            self.assertEqual(row["nguon_id"], "DEMO-NGUON")
            self.assertEqual(row["nhap_boi"], "DEMO")
            self.assertNotIn("nhap_luc", row)
            self.assertFalse(any(c.startswith("m4_") for c in row))
            if table == "dot_thanh_toan" and row["dot"] == 1:
                self.assertEqual(row["gt_ky"], Decimal(repr(0.1 + 0.2)))
                self.assertIsNone(row["giu_lai"])
            if table == "nhat_ky" and row["id"] == 1:
                self.assertEqual(row["chi_tiet"], CHI_TIET)
                self.assertEqual(row["thoi_diem"], THOI_DIEM)
            if table in ("khop_hang_muc", "canh_bao", "nhat_ky") and row["ma_hd"] != "DEMO-HD":
                self.assertIsNone(row["hop_dong_id"])
                self.assertIsNone(row["du_an_id"])

    def test_replay_khop_hash_tra_khong_va_khong_update(self):
        owner, inserts = self._owner(chuan_bi_dong(_demo(), CONTRACTS))
        count = ReviewDotPG(owner).ghi_trong_giao_dich(
            {t: list(reversed(r)) for t, r in _demo().items()},
            nguon_id="DEMO-NGUON", nhap_boi="DEMO", replay=True)
        self.assertEqual(count, 0)
        self.assertEqual(len(inserts), 12)
        for call in owner.execute.call_args_list:
            query = call.args[0]
            if query.startswith("INSERT "):
                self.assertIn("ON CONFLICT", query)
                self.assertTrue(query.endswith("DO NOTHING"))

    def test_replay_khac_hash_tu_choi_truoc_moi_insert(self):
        columns = dict(dot_thanh_toan="gt_ky", kl_thanh_toan="kl_ky",
                       khop_hang_muc="nguoi_xac_nhan", canh_bao="noi_dung", nhat_ky="chi_tiet")
        for table, column in columns.items():
            owner, inserts = self._owner(chuan_bi_dong(_demo(), CONTRACTS))
            changed = _demo()
            changed[table][0][column] = 999.125 if table in ("dot_thanh_toan", "kl_thanh_toan") else "DEMO khác"
            with self.subTest(table=table), self.assertRaises(DataError) as caught:
                ReviewDotPG(owner).ghi_trong_giao_dich(
                    changed, nguon_id="DEMO-NGUON", nhap_boi="DEMO", replay=True)
            self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
            self.assertEqual(inserts, [])

    def test_thieu_nguon_dl2_khong_duoc_ghi_dl4(self):
        owner, inserts = self._owner(source=False)
        with self.assertRaises(DataError) as caught:
            ReviewDotPG(owner).ghi_trong_giao_dich(
                _demo(), nguon_id="DEMO-NGUON", nhap_boi="DEMO", replay=False)
        self.assertEqual(caught.exception.code, "M4_REVIEW_DU_LIEU_SAI")
        self.assertEqual(inserts, [])


@unittest.skipUnless(DSN and psycopg is not None,
                     "Thiếu KHO_PG_DSN_TEST/psycopg — PG do lead chạy (NOT_RUN)")
class ReviewDotPGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_m4_dl4_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = conninfo.make_conninfo(DSN, dbname=cls.db)
        cls.con = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.con.close)
        pg.migrate(cls.con)
        cls.pn = cls.con.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES ('DEMO_DL4','Pháp nhân DEMO DL4') RETURNING id").fetchone()[0]
        cls.da = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_DL4','Dự án DEMO DL4') RETURNING id", (cls.pn,)).fetchone()[0]
        cls.actors = {}
        for name, grant in (("XEM", True), ("KHONG_QUYEN", False)):
            login = "MO_PHONG_DL4_" + name
            actor = cls.con.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) VALUES (%s,%s,'XEM') RETURNING id", (login, login)).fetchone()[0]
            cls.actors[name] = (str(actor), login)
            cls.con.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['M4'])", (actor, cls.pn))
            if grant:
                cls.con.execute("INSERT INTO m4.quyen_du_an (nguoi_dung_id,phap_nhan_id,du_an_id,vai) VALUES (%s,%s,%s,'XEM')", (actor, cls.pn, cls.da))
        role, password = "ktt_test_dl4_" + uuid.uuid4().hex[:12], secrets.token_hex(16)
        cls.con.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web").format(sql.Identifier(role), sql.Literal(password)))
        cls.web = psycopg.connect(conninfo.make_conninfo(cls.dsn, user=role, password=password), autocommit=True)
        cls.addClassCleanup(cls.web.close)

    def setUp(self):
        code = "DEMO-DL4-" + uuid.uuid4().hex
        self.hd = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()[0]
        self.con.execute("INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi) VALUES (%s,%s,%s,'DEMO DL4','MO_PHONG_DEMO')", (self.hd, self.pn, self.da))
        self.enterContext(self.con.transaction(force_rollback=True))
        self.enterContext(self.web.transaction(force_rollback=True))
        self._phien("XEM")
        self.repo = ReviewDotPG(self.con)
        self.source = "DEMO-DL4-" + uuid.uuid4().hex

    def _phien(self, name):
        self.web.execute("""SELECT set_config('ktt.nguoi_dung_id',%s,true),
            set_config('ktt.nguoi_dung_dang_nhap',%s,true)""", self.actors[name])

    def _ghi(self, data=None, *, base=None, dl3=None, **changes):
        args = dict(nguon_id=self.source, chup_luc=CHUP, nhap_boi="MO_PHONG_DEMO",
                    anh_xa={"DEMO-HD": (self.hd, self.da)}, mo_ta="DEMO DL4")
        args.update(changes)
        return self.repo.ghi_lan_chup(_demo() if data is None else data,
                                     du_lieu_dl2=_base() if base is None else base,
                                     du_lieu_dl3=_dl3() if dl3 is None else dl3, **args)

    def _counts(self):
        return {t: self.con.execute(f"SELECT count(*) FROM m4.review_chep_{t} WHERE {'id' if t == 'nguon' else 'nguon_id'}=%s", (self.source,)).fetchone()[0]
                for t in ("nguon", *BANG_NGUON)}

    def _doc(self):
        return self.repo.doc_hien_hanh(self.hd, conn_phien=self.web)

    def test_ghi_doc_du_nam_bang_va_orphan(self):
        self.assertEqual(self._ghi(), 20)
        self.assertEqual(self._doc(), dict(_dto(), trang_thai="HIEN_HANH"))
        for table in ("khop_hang_muc", "canh_bao", "nhat_ky"):
            rows = self.con.execute(f"SELECT hop_dong_id,du_an_id FROM m4.review_chep_{table} WHERE nguon_id=%s AND ma_hd IS DISTINCT FROM 'DEMO-HD'", (self.source,)).fetchall()
            self.assertTrue(rows)
            self.assertTrue(all(r == (None, None) for r in rows))
        self.assertEqual(self._counts()["nhat_ky"], 3)

    def test_replay_khong_tang_dong_va_khong_sua_audit(self):
        self._ghi()
        before = self._counts()
        audit = self.con.execute("SELECT * FROM m4.review_chep_nhat_ky WHERE nguon_id=%s ORDER BY id", (self.source,)).fetchall()
        self.assertEqual(self._ghi({t: list(reversed(r)) for t, r in _demo().items()}), 0)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.con.execute("SELECT * FROM m4.review_chep_nhat_ky WHERE nguon_id=%s ORDER BY id", (self.source,)).fetchall(), audit)

    def test_replay_tu_choi_khac_hash_ca_nam_bang(self):
        self._ghi()
        before = self._counts()
        for table, col, value in (("dot_thanh_toan", "gt_ky", 999),
                                  ("kl_thanh_toan", "kl_ky", 999),
                                  ("khop_hang_muc", "nguoi_xac_nhan", "DEMO khác"),
                                  ("canh_bao", "noi_dung", "DEMO khác"),
                                  ("nhat_ky", "chi_tiet", "DEMO khác")):
            data = _demo()
            data[table][0][col] = value
            with self.subTest(table=table), self.assertRaises(DataError) as caught:
                self._ghi(data)
            self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
            self.assertEqual(self._counts(), before)

    def test_replay_tu_choi_them_bot_va_noi_vao_bang_rong(self):
        self._ghi()
        before = self._counts()
        for change in ("them", "bot"):
            data = _demo()
            if change == "them":
                data["nhat_ky"].append(dict(id=999, chi_tiet="DEMO mới"))
            else:
                data["nhat_ky"].pop()
            with self.subTest(change=change), self.assertRaises(DataError):
                self._ghi(data)
            self.assertEqual(self._counts(), before)
        empty = {t: [] for t in _demo()}
        self._ghi(empty, nguon_id=self.source + "-rong")
        self.assertEqual(self._ghi(empty, nguon_id=self.source + "-rong"), 0)
        with self.assertRaises(DataError):
            self._ghi(nguon_id=self.source + "-rong")

    def test_khong_quyen_hoac_thieu_phien_tra_404(self):
        self._ghi()
        self._phien("KHONG_QUYEN")
        for conn in (None, self.con, self.web):
            for identity in (self.hd, uuid.uuid4()):
                with self.subTest(conn=conn, identity=identity), self.assertRaises(DataError) as caught:
                    self.repo.doc_hien_hanh(identity, conn_phien=conn)
                self.assertEqual(MA_HTTP[caught.exception.code], 404)

    def test_lan_chup_hai_mat_dot_khong_lui_ve_cu(self):
        self._ghi()
        data = _demo()
        data["dot_thanh_toan"] = data["dot_thanh_toan"][1:]
        data["kl_thanh_toan"] = data["kl_thanh_toan"][1:]
        self._ghi(data, nguon_id=self.source + "-moi", chup_luc="2026-10-27T07:00:00+07:00")
        self.assertEqual(self._doc(), dict(_dto(data), trang_thai="HIEN_HANH"))
        self.assertEqual(self._counts()["dot_thanh_toan"], 2)

    def test_nhat_ky_nguyen_chuoi_khong_suy_duyet_tu_da_nop(self):
        self._ghi()
        log = self._doc()["nhat_ky"][0]
        self.assertEqual(log, dict(thoi_diem=THOI_DIEM, nguoi=" DEMO người cũ ",
                                  thao_tac="DA_NOP", chi_tiet=CHI_TIET))
        self.assertEqual(self.con.execute("SELECT count(*) FROM m4.dot WHERE hop_dong_id=%s", (self.hd,)).fetchone()[0], 0)
        for table, ref in (("dot_thanh_toan", "m4_dot_id"), ("khop_hang_muc", "m4_map_id"),
                           ("canh_bao", "m4_run_id"), ("nhat_ky", "m4_nhat_ky_id")):
            self.assertEqual(self.con.execute(f"SELECT count(*) FROM m4.review_chep_{table} WHERE nguon_id=%s AND {ref} IS NOT NULL", (self.source,)).fetchone()[0], 0)

    def test_loi_dl4_rollback_ca_nguon_dl2_dl3(self):
        data = _demo()
        data["kl_thanh_toan"][0]["dot"] = 999
        with self.assertRaises(DataError):
            self._ghi(data)
        self.assertEqual(set(self._counts().values()), {0})
        # Lỗi DB ở bảng cuối sau khi đã INSERT bốn bảng trước vẫn rollback đủ.
        data = _demo()
        data["nhat_ky"][0]["chi_tiet"] = "DEMO\x00không lưu được trong PG TEXT"
        with self.assertRaises((psycopg.Error, ValueError)):
            self._ghi(data)
        self.assertEqual(set(self._counts().values()), {0})
        self.assertEqual(self._ghi(), 20)

    def test_ba_trang_thai_null_va_hd_da_xoa(self):
        self.assertEqual(self._doc()["trang_thai"], "CHUA_CO_LAN_CHUP")
        empty = {t: [] for t in _demo()}
        base = {t: [] for t in _base()}
        dl3 = {t: [] for t in _dl3()}
        self._ghi(empty, base=base, dl3=dl3, anh_xa={})
        self.assertEqual(self._doc()["trang_thai"], "CHUA_CO_TRONG_NGUON")
        self._ghi(nguon_id=self.source + "-co", chup_luc="2026-10-27T07:00:00+07:00")
        self._ghi(empty, base=base, dl3=dl3, anh_xa={}, nguon_id=self.source + "-xoa",
                  chup_luc="2026-10-28T07:00:00+07:00")
        self.assertEqual(self._doc(), dict(dto_dot([], [], [], [], []), trang_thai="DA_XOA_O_NGUON"))

    def test_dict_row_doc_ghi(self):
        before = self.con.row_factory
        try:
            self.con.row_factory = dict_row
            self._ghi()
            self.assertEqual(self._doc(), dict(_dto(), trang_thai="HIEN_HANH"))
        finally:
            self.con.row_factory = before


if __name__ == "__main__":
    unittest.main()
