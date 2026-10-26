"""MTQ-4a: adapter chung + ba điểm duyệt luồng B; PG do lead cấp DSN.

Không khởi động dịch vụ, không xóa CSDL/file. Resolver M1/file/tiếp nhận
chưa có ở M0041 thuộc lát tiếp theo; không coi mock là bằng chứng PG bật.
"""

from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import uuid

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import quyen
from kho_tri_thuc.k2.crm import CrmK2


ACTOR, PN, HD, PB = (str(uuid.uuid4()) for _ in range(4))
OBJ = {"bang": "master.hop_dong", "id": HD}
ACTION = "CRM:TIEP_NHAN:DUYET"
CU = {"nguon": "CU", "ma": "MTQ_TAT", "ly_do": "Giữ đường kiểm quyền cũ"}
COMMANDS = {
    "NOP_HOP_DONG": "CRM:TIEP_NHAN:LAP", "BO_SUNG_HO_SO": "CRM:TIEP_NHAN:SUA",
    "DOI_CHIEU_TRICH_LAI": "CRM:TIEP_NHAN:KIEM", "MAPPING": "CRM:TIEP_NHAN:SUA",
    "KIEM_TRUOC": "CRM:TIEP_NHAN:KIEM", "DUYET": ACTION, "DUYET_V4": ACTION,
    "NHAN_TIEN": "M1:TIEN:LAP", "LIEN_KET_TIEN": "M1:TIEN:SUA",
    "XUAT_FILE_SOAT": "CRM:FILE_SOAT:XEM",
}


def actor(vai="CFO", duyet=("V3", "V4"), modules=("CRM", "M1")):
    return {"id": ACTOR, "dang_nhap": "MO_PHONG_MTQ_CRM", "vai_tro": vai,
            "quyen": {PN: {"module": list(modules), "duyet": list(duyet)}}}


def matrix(ok=True, ma=None, limit="100"):
    return {"nguon": "MA_TRAN", "cho_phep": ok, "ma": ma or ("MTQ_CHO_PHEP" if ok else "MTQ_CHUA_TICK"),
            "ly_do": "Đúng ô quyền" if ok else "Ô quyền bị chặn", "revision": 7,
            "phien_ban_id": str(uuid.uuid4()), "dong_id": str(uuid.uuid4()),
            "module": "CRM", "man": "TIEP_NHAN", "hanh_dong": "DUYET", "gioi_han_vnd": limit}


class Connection:
    """Seam transaction/driver, quyết định SQL được inject; không giả RLS."""

    def __init__(self, decision=None):
        self.decision = deepcopy(CU) if decision is None else decision
        self.calls, self.trace, self.writes, self.journal = [], [], [], []
        self.fail_audit = False
        self.open_v4 = True
        self.pb_count = 1
        self.identity = None
        self.hd = {"id": HD, "phap_nhan_id": PN, "doi_tac_id": "DEMO", "du_an_id": "DEMO"}

    @contextmanager
    def transaction(self):
        self.trace.append("begin")
        old = deepcopy((self.writes, self.journal))
        previous_identity = self.identity
        try:
            yield
        except Exception:
            self.writes, self.journal = old
            self.trace.append("rollback")
            raise
        else:
            self.trace.append("commit")
        finally:
            self.identity = previous_identity

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        r = MagicMock()
        r.fetchone.return_value = None
        r.fetchall.return_value = []
        if "set_config(" in sql:
            self.identity = params[:2]
            self.trace.append("identity")
        elif "mtq_quyet_dinh_phien(" in sql:
            self.trace.append("decision")
            if isinstance(self.decision, Exception):
                raise self.decision
            q = self.decision(params) if callable(self.decision) else deepcopy(self.decision)
            r.fetchone.return_value = {"q": q}
        elif "mtq_ghi_tu_choi_phien(" in sql:
            self.trace.append("audit")
            if self.fail_audit:
                raise RuntimeError("DEMO audit indisponible")
            self.journal.append((self.identity, params))
            r.fetchone.return_value = {"id": str(uuid.uuid4())}
        elif "SELECT * FROM master.hop_dong WHERE" in sql:
            r.fetchone.return_value = deepcopy(self.hd)
        elif "SELECT hop_dong_id FROM master.hop_dong_phien_ban" in sql:
            r.fetchone.return_value = {"hop_dong_id": HD}
        elif "SELECT id FROM master.hop_dong_phien_ban" in sql:
            r.fetchall.return_value = [{"id": PB}] * self.pb_count
        elif "FROM kho.viec_can_duyet" in sql:
            r.fetchone.return_value = {"id": "DEMO", "ly_do_cho": []} if self.open_v4 else None
        elif sql.lstrip().startswith(("UPDATE", "INSERT")):
            self.writes.append((sql, params))
        return r


def crm(conn, dt=None, money=100):
    svc = object.__new__(CrmK2)  # không cần psycopg cho test thuần/mock
    svc.conn, svc.root = conn, Path(".")
    svc.hom_nay = lambda: date(2026, 10, 26)
    svc.danh_tinh = MagicMock(return_value=dt or actor())
    pb = {"id": PB, "hop_dong_id": HD, "phap_nhan_id": PN, "trang_thai": "CHO_DUYET",
          "kiem_luc": "DEMO", "loai": "GOC", "ngay_hieu_luc": None, "thay_cho_id": None}
    total = None if money is None else {"minor": money, "tien_te": "VND"}
    svc._phan_tich_pb = MagicMock(return_value=(pb, [], {"fields": {"gia_tri_hop_dong": total},
                                                       "lich": [], "so_tong": {}}, [], None))
    svc._dong_viec = MagicMock()
    svc._su_kien = MagicMock()
    svc._cap_nhat_trang_thai_lich = MagicMock()
    return svc


class AdapterTat(unittest.TestCase):
    def test_moi_quyen_cu_vai_module_v3_v4_khong_doi(self):
        # Oracle chính là hàm kiem cũ, kể cả code/message lỗi. Các điểm chưa
        # nối được kiểm ở adapter; không khẳng định đã bao phủ route của chúng.
        for command, technical in COMMANDS.items():
            for vai in ("BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"):
                for modules in ((), ("CRM",), ("M1",), ("CRM", "M1")):
                    for tasks in ((), ("V3",), ("V4",), ("V3", "V4")):
                        dt = actor(vai, tasks, modules)
                        with self.subTest(command=command, vai=vai, modules=modules, tasks=tasks):
                            try:
                                quyen.kiem(dt, command, PN)
                                expected = None
                            except DataError as exc:
                                expected = (exc.code, str(exc), exc.locator)
                            resolver = MagicMock(side_effect=AssertionError("CU không đọc tiền"))
                            try:
                                q = quyen.kiem_tham_quyen(Connection(), technical, OBJ,
                                    {"kiem_cu": lambda: quyen.kiem(dt, command, PN), "so_tien_vnd": resolver})
                                actual = None
                                self.assertEqual(q["nguon"], "CU")
                            except DataError as exc:
                                actual = (exc.code, str(exc), exc.locator)
                            self.assertEqual(actual, expected)
                            resolver.assert_not_called()

    def test_callback_cu_giu_ca_ket_qua_phan_cong(self):
        for error in (None, DataError("PHAN_CONG", "Chưa được phân công DEMO")):
            old = MagicMock(side_effect=error)
            if error:
                with self.assertRaises(DataError) as cm:
                    quyen.kiem_tham_quyen(Connection(), "CRM:G1_MAU:LAP", OBJ, {"kiem_cu": old})
                self.assertIs(cm.exception, error)
            else:
                self.assertEqual(quyen.kiem_tham_quyen(Connection(), "CRM:G1_MAU:LAP", OBJ,
                                                     {"kiem_cu": old})["nguon"], "CU")
            old.assert_called_once_with()

    def test_ba_diem_noi_dto_va_loi_cu_giu_nguyen(self):
        for method, args, result in (("duyet", (PB,), {"so_dot": 0, "hieu_luc_tu": None, "ke_hoach": None}),
                                     ("duyet_v4", (HD,), {"v4": "DA_DUYET"}),
                                     ("tu_choi", (PB, "Lý do DEMO"), {"trang_thai": "TU_CHOI"})):
            for vai in ("CFO", "KE_TOAN", "BAN_HANG", "XEM"):
                for tasks in ((), ("V3",), ("V4",), ("V3", "V4")):
                    with self.subTest(method=method, vai=vai, tasks=tasks):
                        c = Connection()
                        svc = crm(c, actor(vai, tasks))
                        command = "DUYET_V4" if method == "duyet_v4" else "DUYET"
                        try:
                            quyen.kiem(svc.danh_tinh(), command, PN)
                            if method == "duyet" and "V4" not in tasks:
                                raise DataError("KHONG_CO_QUYEN_LOAI_VIEC", "Hợp đồng mới còn việc V4 — cần người có quyền V4 duyệt trước hoặc cùng lúc.")
                            expected = None
                        except DataError as exc:
                            expected = exc
                        if expected:
                            with self.assertRaises(DataError) as cm:
                                getattr(svc, method)("phiên máy chủ", *args)
                            self.assertEqual((cm.exception.code, str(cm.exception)), (expected.code, str(expected)))
                        else:
                            self.assertEqual(getattr(svc, method)("phiên máy chủ", *args), result)
                        self.assertFalse(c.journal)
                        self.assertFalse(any("FOR UPDATE" in s and "SELECT id FROM master.hop_dong_phien_ban" in s for s, _ in c.calls))


class AdapterBat(unittest.TestCase):
    def call(self, decision, money=Decimal(100), old=None):
        return quyen.kiem_tham_quyen(Connection(decision), ACTION, OBJ,
                                    {"kiem_cu": old or MagicMock(), "so_tien_vnd": money})

    def test_thieu_o_khong_fallback(self):
        old = MagicMock()
        with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
            self.call(matrix(False), old=old)
        self.assertEqual(cm.exception.code, "MTQ_CHUA_TICK")
        old.assert_not_called()

    def test_quyen_cu_cam_o_bat_van_duoc(self):
        old = MagicMock(side_effect=DataError("KHONG_CO_QUYEN_HANH_DONG", "Cấm theo cũ"))
        q = self.call(matrix(), old=old)
        old.assert_not_called()
        self.assertEqual(q["revision"], 7)
        self.assertIsInstance(q["gioi_han_vnd"], Decimal)
        self.assertIsInstance(q["so_tien_vnd"], Decimal)
        self.assertEqual(q["o_ap_dung"]["hanh_dong"], "DUYET")

    def test_bang_duoi_vuot_han_muc_chinh_xac_decimal(self):
        for amount in (Decimal(99), Decimal(100), Decimal(101), Decimal("10000000000000000001")):
            with self.subTest(amount=amount):
                if amount > 100:
                    with self.assertRaises(DataError) as cm:
                        self.call(matrix(), amount)
                    self.assertEqual(cm.exception.code, "MTQ_VUOT_HAN_MUC")
                else:
                    self.assertTrue(self.call(matrix(), amount)["cho_phep"])
        self.assertTrue(self.call(matrix(limit=None), Decimal("10000000000000000001"))["cho_phep"])
        self.assertTrue(self.call(matrix(limit="0"), Decimal(0))["cho_phep"])

    def test_thieu_am_nan_float_khong_hop_le_deu_chan(self):
        for amount in (None, -1, Decimal("NaN"), Decimal("Infinity"), Decimal("0.1"), 1.0, True, "sai"):
            with self.subTest(amount=amount), self.assertRaises(DataError) as cm:
                self.call(matrix(limit=None), amount)
            self.assertEqual(cm.exception.code, "MTQ_THIEU_CO_SO_TIEN")

    def test_ma_thieu_tien_sql_duoc_anh_xa(self):
        with self.assertRaises(DataError) as cm:
            self.call(matrix(False, "MTQ_THIEU_TIEN"), None)
        self.assertEqual(cm.exception.code, "MTQ_THIEU_CO_SO_TIEN")

    def test_loi_nguon_la_json_sai_khong_fallback(self):
        for decision in (RuntimeError("DEMO SQL detail bí mật"), {}, {"nguon": "LA"},
                         {"nguon": "MA_TRAN", "cho_phep": "true"}, None):
            c = Connection()
            c.decision = decision
            old = MagicMock()
            with self.subTest(decision=decision), self.assertRaises(DataError) as cm:
                quyen.kiem_tham_quyen(c, ACTION, OBJ, {"kiem_cu": old})
            self.assertEqual(cm.exception.code, "MTQ_LOI_QUYET_DINH")
            self.assertNotIn("bí mật", str(cm.exception))
            old.assert_not_called()

    def test_bat_tra_cho_phep_nhung_thieu_snapshot_o_van_chan(self):
        for missing in ("revision", "dong_id", "phien_ban_id", "hanh_dong", "gioi_han_vnd"):
            q = matrix()
            q.pop(missing)
            old = MagicMock()
            with self.subTest(missing=missing), self.assertRaises(DataError) as cm:
                self.call(q, old=old)
            self.assertEqual(cm.exception.code, "MTQ_LOI_QUYET_DINH")
            old.assert_not_called()

    def test_khong_lo_revision_ngoai_pham_vi(self):
        for code in ("MTQ_GAN_VAI", "MTQ_PHAM_VI", "MTQ_PHAP_NHAN"):
            with self.subTest(code=code), self.assertRaises(DataError) as cm:
                self.call(matrix(False, code))
            self.assertEqual((cm.exception.code, str(cm.exception)),
                             ("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền)."))
            self.assertFalse(hasattr(cm.exception, "revision"))
            self.assertFalse(hasattr(cm.exception, "phien_ban_id"))

    def test_thieu_danh_tinh_du_cu_cung_khong_fallback(self):
        old, money = MagicMock(), MagicMock()
        with self.assertRaises(DataError) as cm:
            quyen.kiem_tham_quyen(Connection(matrix(False, "MTQ_DANH_TINH")), ACTION, OBJ,
                                 {"kiem_cu": old, "so_tien_vnd": money})
        self.assertEqual(cm.exception.code, "MTQ_DANH_TINH")
        old.assert_not_called()
        money.assert_not_called()

    def test_json_sai_ke_ca_cu_khong_chay_duong_cu(self):
        for obj in (None, [], {}, {**OBJ, "actor": "CFO_GIA"}, {"bang": "master.hop_dong", "id": "sai"}):
            old = MagicMock()
            with self.subTest(obj=obj), self.assertRaises(DataError) as cm:
                quyen.kiem_tham_quyen(Connection(), ACTION, obj, {"kiem_cu": old})
            self.assertEqual(cm.exception.code, "MTQ_DOI_TUONG")
            old.assert_not_called()

    def test_resolver_loi_va_matran_doi_sang_cu_khong_fallback(self):
        for decision, money in ((matrix(), MagicMock(side_effect=RuntimeError("DEMO lỗi khóa"))),
                                (MagicMock(side_effect=[matrix(), CU]), Decimal(100))):
            old = MagicMock()
            with self.subTest(decision=decision), self.assertRaises(DataError) as cm:
                self.call(decision, money, old)
            self.assertEqual(cm.exception.code, "MTQ_LOI_QUYET_DINH")
            old.assert_not_called()


class CrmBat(unittest.TestCase):
    def test_ba_diem_vai_cu_cam_ma_tran_cho_phep(self):
        for name, args in (("duyet", (PB,)), ("duyet_v4", (HD,)), ("tu_choi", (PB, "DEMO"))):
            with self.subTest(name=name):
                c = Connection(matrix())
                svc = crm(c, actor("XEM", ()))
                with patch.object(quyen, "kiem", side_effect=AssertionError("Không kiểm cũ")), \
                     patch.object(quyen, "duoc", side_effect=AssertionError("Không phủ quyết V4 cũ")):
                    getattr(svc, name)("MO_PHONG_PHIEN", *args)
                self.assertTrue(c.writes or svc._dong_viec.called)
                gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                self.assertEqual(gates[-1], (ACTION, json.dumps(OBJ, ensure_ascii=False), Decimal(100)))
                lock = next(i for i, (s, _) in enumerate(c.calls) if "SELECT id FROM master.hop_dong_phien_ban" in s)
                last = max(i for i, (s, _) in enumerate(c.calls) if "mtq_quyet_dinh_phien(" in s)
                self.assertLess(lock, last)
                self.assertIn("FOR UPDATE", c.calls[lock][0])

    def test_cfo_cu_duoc_nhung_o_tat_chan_truoc_ghi(self):
        for name, args in (("duyet", (PB,)), ("duyet_v4", (HD,)), ("tu_choi", (PB, "DEMO"))):
            with self.subTest(name=name):
                c = Connection(matrix(False))
                svc = crm(c)
                with self.assertRaises(DataError) as cm:
                    getattr(svc, name)("MO_PHONG_PHIEN", *args)
                self.assertEqual(cm.exception.code, "MTQ_CHUA_TICK")
                self.assertFalse(c.writes)
                svc._dong_viec.assert_not_called()
                self.assertEqual(c.trace, ["begin", "identity", "decision", "rollback", "begin", "identity", "audit", "commit"])

    def test_nhat_ky_song_sau_rollback_va_request_may_chu(self):
        c = Connection(matrix(False))
        svc = crm(c)
        for _ in range(2):
            with self.assertRaises(DataError):
                with svc._tx(actor()):
                    c.writes.append("DEMO trước từ chối")
                    svc._kiem_mtq_duyet(actor(), "DUYET", HD, PN, pb_id=PB)
        self.assertFalse(c.writes)
        self.assertEqual(len(c.journal), 2)
        requests = []
        for identity, params in c.journal:
            self.assertEqual(identity, (ACTOR, actor()["dang_nhap"]))
            requests.append(str(uuid.UUID(params[0])))
            self.assertEqual(params[1:3], (ACTION, json.dumps(OBJ, ensure_ascii=False)))
        self.assertNotEqual(*requests)

    def test_loi_audit_khong_cho_phep_va_khong_lo_sql(self):
        c = Connection(matrix(False))
        c.fail_audit = True
        svc = crm(c)
        with self.assertLogs("kho_tri_thuc.k2.crm", level="ERROR"), self.assertRaises(DataError) as cm:
            svc.duyet("MO_PHONG_PHIEN", PB)
        self.assertEqual(cm.exception.code, "MTQ_NHAT_KY_LOI")
        self.assertFalse(c.writes)
        self.assertFalse(c.journal)
        self.assertEqual(c.trace[-1], "rollback")

    def test_khong_bao_ghi_ben_khi_dang_trong_ambient_transaction(self):
        c = Connection(matrix(False))
        c.info = MagicMock(transaction_status=2)
        with self.assertLogs("kho_tri_thuc.k2.crm", level="ERROR"), self.assertRaises(DataError) as cm:
            crm(c).duyet("MO_PHONG_PHIEN", PB)
        self.assertEqual(cm.exception.code, "MTQ_NHAT_KY_LOI")
        self.assertFalse(c.journal)
        self.assertNotIn("audit", c.trace)

    def test_tong_hop_dong_khong_dung_so_tien_dot(self):
        c = Connection(matrix())
        svc = crm(c, money=101)
        with self.assertRaises(DataError) as cm:
            svc.duyet("MO_PHONG_PHIEN", PB)
        self.assertEqual(cm.exception.code, "MTQ_VUOT_HAN_MUC")
        self.assertEqual(c.journal[0][1][-1], Decimal(101))

    def test_tien_thieu_ngoai_te_v4_mo_ho_deu_chan(self):
        for missing in ("thieu", "USD", "nhieu_ban"):
            with self.subTest(missing=missing):
                c = Connection(matrix())
                svc = crm(c, money=None if missing == "thieu" else 100)
                if missing == "USD":
                    svc._phan_tich_pb.return_value[2]["fields"]["gia_tri_hop_dong"]["tien_te"] = "USD"
                if missing == "nhieu_ban":
                    c.pb_count = 2
                with self.assertRaises(DataError) as cm:
                    svc.duyet_v4("MO_PHONG_PHIEN", HD)
                self.assertEqual(cm.exception.code, "MTQ_THIEU_CO_SO_TIEN")

    def test_actor_body_bi_bo_qua_guc_tu_phien(self):
        from kho_tri_thuc.giao_dien.server import LocalApp
        app = object.__new__(LocalApp)
        c = Connection(matrix(False))
        svc = crm(c)
        app.crm = lambda: svc
        app.crm_phien = MagicMock(return_value=("cookie", "MO_PHONG_PHIEN", False))
        body = {"id": PB, "actor": "CFO_GIA_MAO", "nguoi_dung_id": str(uuid.uuid4()),
                "so_tien": 0, "revision": 999}
        # Hợp đồng HTTP cũ từ chối trường actor; giữ nguyên thay vì cho client
        # đổi danh tính. Alias không được dùng ở dưới vẫn không tác động GUC.
        with self.assertRaises(DataError) as rejected:
            app._crm_action("cookie", "duyet", body)
        self.assertEqual(rejected.exception.code, "CRM_CLIENT_IDENTITY")
        svc.danh_tinh.assert_not_called()
        body.pop("actor")
        with self.assertRaises(DataError):
            app._crm_action("cookie", "duyet", body)
        svc.danh_tinh.assert_called_once_with("MO_PHONG_PHIEN")
        self.assertEqual(c.journal[0][0], (ACTOR, actor()["dang_nhap"]))
        for s, p in c.calls:
            if "mtq_" in s:
                self.assertNotIn("CFO_GIA_MAO", repr(p))
                self.assertNotIn("revision", repr(p))


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST"), "NOT_RUN: lead cấp KHO_PG_DSN_TEST; không mở PostgreSQL")
class MtqCrmPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fixture tự tạo DB test mới, không DROP; tái dùng M0041, không copy schema.
        from tests.test_mtq_cong_sql import MtqCongPostgres
        cls.fixture = MtqCongPostgres
        cls.fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doClassCleanups()

    def test_tat_cong_sql_that_giu_ket_qua_cu(self):
        from psycopg.rows import dict_row
        f = self.fixture("test_app_goi_duoc_va_chua_bat_tra_cu")
        # Tên method của TestCase chỉ dùng để tạo fixture; không gọi test khác.
        f.setUp()
        try:
            with f.c.transaction():
                f.actor(f.user)
                f.web()
                with f.c.cursor(row_factory=dict_row) as cursor:
                    for old_command, technical in COMMANDS.items():
                        for role in ("CFO", "KE_TOAN", "XEM"):
                            dt = actor(role)
                            old = MagicMock(side_effect=lambda: quyen.kiem(dt, old_command, PN))
                            try:
                                quyen.kiem(dt, old_command, PN)
                                expected = None
                            except DataError as exc:
                                expected = (exc.code, str(exc))
                            try:
                                q = quyen.kiem_tham_quyen(cursor, technical, f.obj, {"kiem_cu": old})
                                self.assertEqual(q["nguon"], "CU")
                                actual = None
                            except DataError as exc:
                                actual = (exc.code, str(exc))
                            self.assertEqual(actual, expected)
                            old.assert_called_once_with()
        finally:
            f.doCleanups()


if __name__ == "__main__":
    unittest.main()
