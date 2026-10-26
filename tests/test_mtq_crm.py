"""MTQ-4a/4a2/4a3b: adapter và các điểm CRM/M1 luồng B.

Không khởi động dịch vụ, không xóa CSDL/file. PG tái dùng fixture M0045
tạo kho_test_*; không coi mock là bằng chứng PG bật.
"""

from contextlib import contextmanager, ExitStack
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

    def test_phi_tien_theo_catalog_khong_goi_resolver_khong_so_han_muc(self):
        from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import _CATALOG
        for module, man, actions, money in _CATALOG:
            for action in actions.split():
                if action == "DUYET" and money != "PHI_TIEN":
                    continue
                technical = f"{module}:{man}:{action}"
                with self.subTest(technical=technical):
                    q = matrix(limit="0")
                    q.update(module=module, man=man, hanh_dong=action)
                    old = MagicMock(side_effect=AssertionError("Không fallback"))
                    resolver = MagicMock(side_effect=AssertionError("KHONG_AP_DUNG tiền"))
                    c = Connection(q)
                    out = quyen.kiem_tham_quyen(c, technical, OBJ,
                                               {"kiem_cu": old, "so_tien_vnd": resolver})
                    self.assertIsNone(out["so_tien_vnd"])
                    self.assertTrue(out["cho_phep"])
                    self.assertTrue(all(p[2] is None for s, p in c.calls))
                    old.assert_not_called()
                    resolver.assert_not_called()

    def test_catalog_xin_thanh_toan_cung_bat_buoc_tien(self):
        q = matrix(limit=None)
        q.update(module="M4", man="02C_DUYET")
        old = MagicMock()
        with self.assertRaises(DataError) as cm:
            quyen.kiem_tham_quyen(Connection(q), "M4:02C_DUYET:DUYET", OBJ, {"kiem_cu": old})
        self.assertEqual(cm.exception.code, "MTQ_THIEU_CO_SO_TIEN")
        old.assert_not_called()

    def test_data_error_cua_resolver_giu_nguyen_ca_ma_message_locator(self):
        for code, message in (("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền)."),
                              ("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")):
            with self.subTest(code=code):
                error = DataError(code, message, "$.phien_ban")
                old = MagicMock()
                resolver = MagicMock(side_effect=error)
                c = Connection(matrix(False, "MTQ_THIEU_TIEN"))
                with self.assertRaises(DataError) as cm:
                    quyen.kiem_tham_quyen(c, ACTION, OBJ, {"kiem_cu": old, "so_tien_vnd": resolver})
                self.assertIs(cm.exception, error)
                self.assertEqual((cm.exception.code, str(cm.exception), cm.exception.locator),
                                 (code, message, "$.phien_ban"))
                resolver.assert_called_once_with()
                old.assert_not_called()
                self.assertEqual(len(c.calls), 1)

    def test_loi_cong_ghi_log_exc_info_khong_lo_chi_tiet(self):
        with self.assertLogs(quyen.__name__, level="ERROR") as logs:
            with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                self.call(RuntimeError("Chi tiết SQL DEMO nội bộ"))
        self.assertEqual(cm.exception.code, "MTQ_LOI_QUYET_DINH")
        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertNotIn("Chi tiết SQL", str(cm.exception))
        self.assertNotIn("Cần Anh", str(cm.exception))

    def test_loi_lay_tien_ghi_log_exc_info_khong_lo_chi_tiet(self):
        resolver = MagicMock(side_effect=RuntimeError("Chi tiết khóa DEMO nội bộ"))
        with self.assertLogs(quyen.__name__, level="ERROR") as logs:
            with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                self.call(matrix(), resolver)
        self.assertEqual(cm.exception.code, "MTQ_LOI_QUYET_DINH")
        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertNotIn("Chi tiết khóa", str(cm.exception))
        self.assertNotIn("Cần Anh", str(cm.exception))

    def test_thieu_tien_thong_bao_trung_tinh_giu_ma(self):
        with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
            self.call(matrix(limit=None), None)
        self.assertEqual(cm.exception.code, "MTQ_THIEU_CO_SO_TIEN")
        self.assertEqual(str(cm.exception), "Chưa có tổng giá trị hợp đồng VND từ phiên bản đã khóa; chưa thể duyệt.")
        self.assertNotIn("Cần Anh", str(cm.exception))


class CrmDiemMoi(unittest.TestCase):
    POINTS = (
        ("cap_nhat_mapping", ({},), "MAPPING", "CRM:TIEP_NHAN:SUA"),
        ("xac_nhan_tham_so", ("DEMO_MA", "Căn cứ DEMO"), "KIEM_TRUOC", "CRM:TIEP_NHAN:KIEM"),
        ("kiem_truoc", (), "KIEM_TRUOC", "CRM:TIEP_NHAN:KIEM"),
    )

    def service(self, c, dt):
        svc = crm(c, dt, money=None)
        c.hd["phien_ban_hien_hanh"] = None
        svc._map = MagicMock(return_value=None)
        svc._vo_hieu_kiem = MagicMock()
        svc._viec = MagicMock()
        svc.chan_phien_ban = MagicMock(return_value=[])
        svc._tien_mtq = MagicMock(side_effect=AssertionError("Hành động KHONG_AP_DUNG tiền"))
        return svc

    def check_cu(self, name):
        _, args, command, technical = next(p for p in self.POINTS if p[0] == name)
        oracle = quyen.kiem
        for vai in ("BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"):
            for modules in ((), ("CRM",), ("M1",), ("CRM", "M1")):
                for tasks in ((), ("V3",), ("V4",), ("V3", "V4")):
                    for has_pn in (False, True):
                        dt = actor(vai, tasks, modules)
                        if not has_pn:
                            dt["quyen"] = {}
                        with self.subTest(name=name, vai=vai, modules=modules, tasks=tasks, pn=has_pn):
                            c = Connection()
                            svc = self.service(c, dt)
                            try:
                                oracle(dt, command, PN)
                                expected_error = None
                            except DataError as exc:
                                expected_error = (exc.code, str(exc), exc.locator)
                            with patch.object(quyen, "kiem", wraps=oracle) as old:
                                try:
                                    out = getattr(svc, name)("PHIEN_MAY_CHU", PB, *args)
                                    actual_error = None
                                except DataError as exc:
                                    actual_error = (exc.code, str(exc), exc.locator)
                                old.assert_called_once_with(dt, command, PN)
                            self.assertEqual(actual_error, expected_error)
                            if expected_error is None:
                                self.assertEqual(out, {"kiem_boi": dt["dang_nhap"]} if name == "kiem_truoc" else {"chan": []})
                            else:
                                self.assertFalse(c.writes)
                                svc._su_kien.assert_not_called()
                            gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                            self.assertEqual(gates, [(technical, json.dumps(OBJ, ensure_ascii=False), None)])
                            self.assertFalse(c.journal)
                            svc._tien_mtq.assert_not_called()

    def test_cu_cap_nhat_mapping_oracle_nhieu_vai(self):
        self.check_cu("cap_nhat_mapping")

    def test_cu_xac_nhan_tham_so_oracle_nhieu_vai(self):
        self.check_cu("xac_nhan_tham_so")

    def test_cu_kiem_truoc_oracle_nhieu_vai(self):
        self.check_cu("kiem_truoc")

    def test_bat_moi_diem_khong_fallback_khong_doi_tien(self):
        for name, args, _, technical in self.POINTS:
            for allow in (False, True):
                with self.subTest(name=name, allow=allow):
                    q = matrix(allow, limit="0")
                    q["hanh_dong"] = technical.split(":")[2]
                    c = Connection(q)
                    svc = self.service(c, actor("XEM" if allow else "KE_TOAN"))
                    with patch.object(quyen, "kiem", side_effect=AssertionError("Không fallback")):
                        if allow:
                            out = getattr(svc, name)("PHIEN_MAY_CHU", PB, *args)
                            self.assertEqual(out, {"kiem_boi": actor()["dang_nhap"]} if name == "kiem_truoc" else {"chan": []})
                            self.assertTrue(svc._su_kien.called)
                        else:
                            with self.assertRaises(DataError) as cm:
                                getattr(svc, name)("PHIEN_MAY_CHU", PB, *args)
                            self.assertEqual(cm.exception.code, "MTQ_CHUA_TICK")
                            self.assertFalse(c.writes)
                            svc._su_kien.assert_not_called()
                            self.assertEqual(c.trace, ["begin", "identity", "decision", "rollback", "begin", "identity", "audit", "commit"])
                            self.assertEqual(c.journal[0][1][1:3], (technical, json.dumps(OBJ, ensure_ascii=False)))
                    svc._tien_mtq.assert_not_called()
                    gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                    self.assertEqual(gates, [(technical, json.dumps(OBJ, ensure_ascii=False), None)] * (2 if allow else 1))

    def test_doi_tuong_tu_pb_da_doc_khong_dung_id_cua_request(self):
        request_pb = str(uuid.uuid4())
        for name, args, _, technical in self.POINTS:
            with self.subTest(name=name):
                c = Connection(matrix(False))
                svc = self.service(c, actor())
                with self.assertRaises(DataError):
                    getattr(svc, name)("PHIEN_MAY_CHU", request_pb, *args)
                gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                self.assertEqual(json.loads(gates[0][1]), OBJ)
                self.assertEqual(c.trace[:3], ["begin", "identity", "decision"])

    def test_mat_ban_hoac_hop_dong_chan_truoc_adapter(self):
        for name, args, _, _ in self.POINTS:
            for code in ("PHIEN_BAN", "HOP_DONG"):
                with self.subTest(name=name, code=code):
                    c = Connection(matrix())
                    svc = self.service(c, actor())
                    if code == "PHIEN_BAN":
                        svc._phan_tich_pb.side_effect = DataError(code, "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
                    else:
                        svc._khoa_hop_dong = MagicMock(side_effect=DataError(code, "Không thấy hợp đồng (hoặc ngoài quyền)."))
                    with self.assertRaises(DataError) as cm:
                        getattr(svc, name)("PHIEN_MAY_CHU", PB, *args)
                    self.assertEqual(cm.exception.code, code)
                    self.assertNotIn("decision", c.trace)
                    self.assertFalse(c.writes)


CT, LK, LO, REQUEST = (str(uuid.uuid4()) for _ in range(4))
# Tên, lệnh cũ, khóa catalog, bảng, ID từ dòng đọc được, lỗi ngoài phạm vi.
REMAINING = (
    ("trich_tu_docx", "NOP_HOP_DONG", "CRM:TIEP_NHAN:LAP", "master.phap_nhan", PN, "PHAP_NHAN", "Không có pháp nhân này."),
    ("nhan_ket_qua_6", "NOP_HOP_DONG", "CRM:TIEP_NHAN:LAP", "master.phap_nhan", PN, "PHAP_NHAN", "Không có pháp nhân này."),
    ("bo_sung_ho_so", "BO_SUNG_HO_SO", "CRM:TIEP_NHAN:SUA", "kho.chung_tu", CT, "HO_SO", "Không thấy hồ sơ (hoặc ngoài quyền)."),
    ("_trich_lai", "DOI_CHIEU_TRICH_LAI", "CRM:TIEP_NHAN:KIEM", "kho.chung_tu", CT, "HO_SO", "Không thấy hồ sơ (hoặc ngoài quyền)."),
    ("kiem_nhan_tien", "NHAN_TIEN", "M1:TIEN:LAP", "master.phap_nhan", PN, "PHAP_NHAN", "Không có pháp nhân này."),
    ("lien_ket", "LIEN_KET_TIEN", "M1:TIEN:SUA", "master.hop_dong", HD, "LIEN_KET_THAM_CHIEU", "Không thấy khoản tiền hoặc đợt (hoặc ngoài quyền)."),
    ("go_lien_ket", "LIEN_KET_TIEN", "M1:TIEN:HUY", "kho.lien_ket_chung_tu", LK, "LIEN_KET", "Không thấy liên kết (hoặc ngoài quyền)."),
    ("xuat_file_soat", "XUAT_FILE_SOAT", "CRM:FILE_SOAT:XEM", "master.hop_dong", HD, "HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền)."),
    ("tep_file_soat", "XUAT_FILE_SOAT", "CRM:FILE_SOAT:XEM", "kho.lo_xuat", LO, "FILE_SOAT", "Không thấy file soát CRM (hoặc ngoài quyền)."),
)


class SauKiemQuyen(Exception):
    """Dừng tại bước nghiệp vụ kế tiếp, không chạy engine/ghi/xuất thật."""


class RemainingConnection(Connection):
    def __init__(self, decision=None, missing=False):
        super().__init__(decision)
        self.events, self.missing = [], missing

    def after(self, *args, **kwargs):
        self.events.append("nghiep_vu")
        raise SauKiemQuyen()

    def execute(self, sql, params=()):
        if "mtq_quyet_dinh_phien(" in sql:
            if self.identity is None:
                raise AssertionError("Cổng phải có GUC danh tính trong transaction")
            self.events.append("cong")
        initial = None
        if "SELECT id FROM master.phap_nhan WHERE ma" in sql:
            initial = {"id": PN}
        elif "SELECT * FROM kho.chung_tu WHERE id" in sql:
            initial = {"id": CT, "phap_nhan_id": PN}
        elif "SELECT l.phap_nhan_id, p.hop_dong_id" in sql:
            initial = {"phap_nhan_id": PN, "hop_dong_id": HD}
        elif "SELECT * FROM kho.lien_ket_chung_tu WHERE id" in sql:
            initial = {"id": LK, "phap_nhan_id": PN, "hop_dong_id": HD}
        elif "SELECT h.*, p.ma AS pn_ma" in sql:
            initial = {"id": HD, "phap_nhan_id": PN}
        elif "SELECT * FROM kho.lo_xuat WHERE id" in sql:
            initial = {"id": LO, "phap_nhan_id": PN, "duong_dan": "DEMO.xlsx"}
        if initial is not None:
            self.calls.append((sql, params))
            self.events.append("doc_dong")
            result = MagicMock()
            result.fetchone.return_value = None if self.missing else initial
            return result
        if any(part in sql for part in ("SELECT 1 FROM master.hop_dong_phien_ban",
                                       "SELECT 1 FROM kho.viec_can_duyet",
                                       "SELECT * FROM master.hop_dong_phien_ban WHERE hop_dong_id")):
            self.after()
        return super().execute(sql, params)


class CrmChinDiem(unittest.TestCase):
    @contextmanager
    def service(self, point, dt, decision=None, missing=False):
        c = RemainingConnection(decision, missing)
        svc = crm(c, dt)
        svc._khoa_hop_dong = MagicMock(side_effect=c.after)
        svc._tien_mtq = MagicMock(side_effect=AssertionError("PHI_TIEN không đọc tiền"))
        client = MagicMock()
        with ExitStack() as stack:
            def mock(name, **kwargs):
                return stack.enter_context(patch(name, **kwargs))
            mock("kho_tri_thuc.k2.crm.envelope", return_value={
                "hash_ket_qua": "DEMO", "van_ban_nguon_hash": "DEMO_VB", "phap_nhan": "PN_DEMO"})
            mock("kho_tri_thuc.k2.crm.doc_ket_qua", return_value={})
            mock("kho_tri_thuc.k2.crm.write_immutable", side_effect=lambda *a: c.events.append("raw"))
            mock("kho_tri_thuc.k2.crm.TrichHopDong6Adapter", side_effect=c.after)
            request = mock("kho_tri_thuc.nguon.trich_chung_6.yeu_cau_common", side_effect=c.after)
            if point == "tep_file_soat":
                svc.root = MagicMock()
                svc.root.__truediv__.side_effect = c.after

            def invoke():
                if point == "trich_tu_docx":
                    return svc.trich_tu_docx("PHIEN_MAY_CHU", b"PK\x03\x04DEMO", {"phap_nhan": "PN_DEMO"},
                                            loai_hop_dong="DEMO", tham_so=[], request_id=REQUEST, client=client)
                if point == "nhan_ket_qua_6":
                    return svc.nhan_ket_qua_6("PHIEN_MAY_CHU", b"DEMO", {}, van_ban_nguon="Văn bản DEMO")
                if point == "bo_sung_ho_so":
                    return svc.bo_sung_ho_so("PHIEN_MAY_CHU", REQUEST, {"loai_hinh": "DEMO"})
                if point == "_trich_lai":
                    # Cả doi_chieu_trich_lai/xu_ly_trich_lai đều đã mở _tx.
                    with svc._tx(dt):
                        return svc._trich_lai(dt, REQUEST)
                if point == "kiem_nhan_tien":
                    return svc.kiem_nhan_tien("PHIEN_MAY_CHU", "PN_DEMO")
                if point == "lien_ket":
                    return svc.lien_ket("PHIEN_MAY_CHU", REQUEST, REQUEST, 1, "DEMO_IDEMPOTENCY")
                if point == "go_lien_ket":
                    return svc.go_lien_ket("PHIEN_MAY_CHU", REQUEST, "Lý do DEMO")
                return getattr(svc, point)("PHIEN_MAY_CHU", REQUEST)

            yield c, svc, client, request, invoke

    def check_cu(self, point):
        _, command, technical, table, key, _, _ = next(p for p in REMAINING if p[0] == point)
        oracle = quyen.kiem
        for role in ("BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"):
            for modules in ((), ("CRM",), ("M1",), ("CRM", "M1")):
                for right_pn in (False, True):
                    dt = actor(role, modules=modules)
                    if not right_pn:
                        dt["quyen"] = {REQUEST: dt["quyen"][PN]}
                    with self.subTest(point=point, role=role, modules=modules, pn=right_pn):
                        try:
                            oracle(dt, command, PN)
                            expected = None
                        except DataError as exc:
                            expected = (exc.code, str(exc), exc.locator)
                        with self.service(point, dt) as (c, svc, client, request, invoke):
                            def legacy(*args):
                                c.events.append("cu")
                                return oracle(*args)
                            with patch.object(quyen, "kiem", side_effect=legacy) as old:
                                actual = None
                                try:
                                    out = invoke()
                                    self.assertEqual(out, PN)  # kiem_nhan_tien trả PN thật
                                except SauKiemQuyen:
                                    pass
                                except DataError as exc:
                                    actual = (exc.code, str(exc), exc.locator)
                                self.assertEqual(actual, expected)
                                old.assert_called_once_with(dt, command, PN)
                            self.assertLess(c.events.index("doc_dong"), c.events.index("cu"))
                            if point == "nhan_ket_qua_6":
                                self.assertEqual(c.events[:2], ["raw", "raw"])
                            else:
                                self.assertNotIn("raw", c.events)
                            if expected is not None:
                                self.assertNotIn("nghiep_vu", c.events)
                                request.assert_not_called()
                            elif point != "kiem_nhan_tien":
                                self.assertLess(c.events.index("cu"), c.events.index("nghiep_vu"))
                            client.trich.assert_not_called()
                            self.assertFalse(c.writes or c.journal)
                            gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                            self.assertEqual(gates, [(technical, json.dumps({"bang": table, "id": key}, ensure_ascii=False), None)])
                            svc._tien_mtq.assert_not_called()

    def test_cu_trich_tu_docx_oracle(self):
        self.check_cu("trich_tu_docx")

    def test_cu_nhan_ket_qua_6_oracle(self):
        self.check_cu("nhan_ket_qua_6")

    def test_nhan_ket_qua_6_kiem_va_ghi_cung_giao_dich(self):
        for source in ("CU", "MA_TRAN"):
            for fail in (False, True):
                q = deepcopy(CU) if source == "CU" else {**matrix(), "hanh_dong": "LAP"}
                with self.subTest(source=source, rollback=fail):
                    with self.service("nhan_ket_qua_6", actor("KE_TOAN"), q) as (c, svc, _, _, invoke):
                        execute = c.execute

                        def write(sql, params=()):
                            result = execute(sql, params)
                            for table, key, event in (("kho.tep_goc", REQUEST, "ghi_tep"),
                                                      ("kho.chung_tu", CT, "ghi_chung_tu")):
                                if sql.lstrip().startswith("INSERT INTO " + table):
                                    self.assertEqual(c.identity, (ACTOR, actor()["dang_nhap"]))
                                    c.trace.append(event)
                                    result.fetchone.return_value = {"id": key}
                            return result

                        c.execute = write
                        svc._profile = MagicMock(return_value=None)

                        def adapt(*args):
                            c.trace.append("adapter")
                            return MagicMock(read=MagicMock(return_value=MagicMock(
                                issues=[], records=[MagicMock(core={})])))

                        def create(*args):
                            c.trace.append("lap_ho_so")
                            if fail:
                                raise SauKiemQuyen()
                            return {"ket_qua": "DEMO"}

                        svc._lap_ho_so = MagicMock(side_effect=create)
                        env = {"hash_ket_qua": "DEMO", "van_ban_nguon_hash": "DEMO_VB",
                               "phap_nhan": "PN_DEMO", "loai_hinh": None,
                               "namespace": "DEMO", "loai_ban": "GOC"}
                        with patch("kho_tri_thuc.k2.crm.envelope", return_value=env), \
                             patch("kho_tri_thuc.k2.crm.TrichHopDong6Adapter", side_effect=adapt), \
                             patch.object(quyen, "kiem", wraps=quyen.kiem) as old:
                            if fail:
                                with self.assertRaises(SauKiemQuyen):
                                    invoke()
                            else:
                                self.assertEqual(invoke(), {"trung": False, "chung_tu_id": CT,
                                                           "ket_qua": "DEMO", "issues": []})
                            if source == "CU":
                                old.assert_called_once_with(svc.danh_tinh(), "NOP_HOP_DONG", PN)
                            else:
                                old.assert_not_called()
                        # Không commit/nhả khóa giữa cổng quyền, adapter và các INSERT.
                        self.assertEqual(c.trace, ["begin", "identity"] +
                                         ["decision"] * (1 if source == "CU" else 2) +
                                         ["adapter", "ghi_tep", "ghi_chung_tu", "lap_ho_so",
                                          "rollback" if fail else "commit"])
                        self.assertEqual(len(c.writes), 0 if fail else 2)

    def test_cu_bo_sung_ho_so_oracle(self):
        self.check_cu("bo_sung_ho_so")

    def test_cu_trich_lai_oracle(self):
        self.check_cu("_trich_lai")

    def test_cu_kiem_nhan_tien_oracle(self):
        self.check_cu("kiem_nhan_tien")

    def test_cu_lien_ket_oracle(self):
        self.check_cu("lien_ket")

    def test_cu_go_lien_ket_oracle(self):
        self.check_cu("go_lien_ket")

    def test_cu_xuat_file_soat_oracle(self):
        self.check_cu("xuat_file_soat")

    def test_cu_tep_file_soat_oracle(self):
        self.check_cu("tep_file_soat")

    def test_bat_chin_diem_khong_fallback_phi_tien_audit_sau_rollback(self):
        for point, _, technical, table, key, _, _ in REMAINING:
            for allow in (True, False):
                with self.subTest(point=point, allow=allow):
                    q = matrix(allow, limit="0")
                    q.update(zip(("module", "man", "hanh_dong"), technical.split(":")))
                    with self.service(point, actor("XEM"), q) as (c, svc, client, _, invoke):
                        with patch.object(quyen, "kiem", side_effect=AssertionError("Không fallback")):
                            if allow:
                                if point == "kiem_nhan_tien":
                                    self.assertEqual(invoke(), PN)
                                else:
                                    with self.assertRaises(SauKiemQuyen):
                                        invoke()
                            else:
                                with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                                    invoke()
                                self.assertEqual(cm.exception.code, "MTQ_CHUA_TICK")
                                self.assertNotIn("nghiep_vu", c.events)
                                self.assertLess(c.trace.index("rollback"), c.trace.index("audit"))
                                self.assertEqual(c.trace[-4:], ["begin", "identity", "audit", "commit"])
                                self.assertEqual(c.journal[0][0], (ACTOR, actor()["dang_nhap"]))
                                self.assertEqual(c.journal[0][1][1:],
                                                 (technical, json.dumps({"bang": table, "id": key}, ensure_ascii=False), None))
                        gates = [p for s, p in c.calls if "mtq_quyet_dinh_phien(" in s]
                        self.assertEqual(gates, [(technical, json.dumps({"bang": table, "id": key}, ensure_ascii=False), None)] * (2 if allow else 1))
                        client.trich.assert_not_called()
                        svc._tien_mtq.assert_not_called()

    def test_khong_thay_giu_loi_tung_diem_va_khong_lo_snapshot(self):
        for point, _, _, _, _, code, message in REMAINING:
            for denial in ("MTQ_GAN_VAI", "MTQ_PHAM_VI", "MTQ_PHAP_NHAN"):
                with self.subTest(point=point, denial=denial):
                    with self.service(point, actor(), matrix(False, denial)) as (c, _, _, _, invoke):
                        with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                            invoke()
                        self.assertEqual((cm.exception.code, str(cm.exception)), (code, message))
                        self.assertFalse(hasattr(cm.exception, "revision"))
                        self.assertNotIn("nghiep_vu", c.events)

    def test_mat_dong_rls_chan_truoc_cong(self):
        for point, _, _, _, _, code, message in REMAINING:
            with self.subTest(point=point):
                with self.service(point, actor(), missing=True) as (c, _, client, _, invoke):
                    with self.assertRaises(DataError) as cm:
                        invoke()
                    self.assertEqual((cm.exception.code, str(cm.exception)), (code, message))
                    self.assertNotIn("cong", c.events)
                    client.trich.assert_not_called()

    def test_engine_trich_chi_goi_sau_commit_kiem_quyen(self):
        for decision in (CU, matrix()):
            q = deepcopy(decision)
            if q["nguon"] == "MA_TRAN":
                q.update(hanh_dong="LAP")
            with self.subTest(source=q["nguon"]):
                with self.service("trich_tu_docx", actor("KE_TOAN"), q) as (c, svc, client, request, invoke):
                    request.side_effect = None
                    svc.root = MagicMock()
                    svc.root.__truediv__.return_value.__truediv__.return_value.is_file.return_value = False
                    svc.nhan_ket_qua_6 = MagicMock(return_value={"ket_qua": "DEMO"})
                    def engine(*args, **kwargs):
                        self.assertIsNone(c.identity)
                        self.assertEqual(c.trace[-1], "commit")
                        return {"raw_sha256": "DEMO", "raw_ket_qua": b"DEMO", "ket_qua": {}, "luot": 1,
                                "common": {"contract": "DEMO", "catalog_id": "DEMO", "catalog_sha256": "DEMO",
                                           "loai_hop_dong": "DEMO", "tham_so_da_dung": []}}
                    client.trich.side_effect = engine
                    with patch("kho_tri_thuc.nguon.trich_chung_6.chieu_tham_so", return_value={"adapter": "DEMO"}), \
                         patch("kho_tri_thuc.nguon.trich_chung_6.view_bytes", return_value=b"DEMO"):
                        self.assertEqual(invoke()["ket_qua"], "DEMO")
                    client.trich.assert_called_once()
                    svc.nhan_ket_qua_6.assert_called_once()


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
        with self.assertLogs("kho_tri_thuc.k2.crm", level="ERROR") as logs, self.assertRaises(DataError) as cm:
            svc.duyet("MO_PHONG_PHIEN", PB)
        self.assertEqual(cm.exception.code, "MTQ_NHAT_KY_LOI")
        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertIn("Traceback", logs.output[0])
        self.assertNotIn("DEMO audit indisponible", str(cm.exception))
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


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST"), "NOT_RUN: lead cấp KHO_PG_DSN_TEST; không mở PostgreSQL")
class MtqCrmResolverPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_mtq_cong_c_sql import MtqCongCPostgres
        cls.fixture = MtqCongCPostgres
        cls.fixture.setUpClass()  # CREATE DATABASE kho_test_* từ DSN quản trị

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doClassCleanups()

    def setUp(self):
        self.f = self.fixture("test_chin_diem_dung_pham_vi_khong_can_tien_va_app_web")
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()  # BEGIN + rollback dữ liệu test; không đọc DSN DEMO

    def check_points(self, allow, expected=None):
        from psycopg.rows import dict_row
        f = self.f
        f.c.execute("SET LOCAL ROLE app_web")
        with f.c.cursor(row_factory=dict_row) as cursor:
            for point, _, technical, table, _, code, message in REMAINING:
                old = MagicMock(side_effect=AssertionError("PG bật MTQ không fallback"))
                context = {"kiem_cu": old, "khong_thay": (code, message)}
                with self.subTest(point=point):
                    if allow:
                        q = quyen.kiem_tham_quyen(cursor, technical, f.objects[table], context)
                        self.assertEqual(q["nguon"], "MA_TRAN")
                        self.assertIs(q["cho_phep"], True)
                        self.assertIsNone(q["so_tien_vnd"])
                    else:
                        with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                            quyen.kiem_tham_quyen(cursor, technical, f.objects[table], context)
                        self.assertEqual(cm.exception.code, expected or code)
                        if expected is None:
                            self.assertEqual(str(cm.exception), message)
                    old.assert_not_called()

    def test_bat_chin_diem_du_o_pham_vi_qua_adapter(self):
        self.f.cau_hinh()
        self.check_points(True)

    def test_bat_chin_diem_thieu_o_giu_ma_cong_khong_fallback(self):
        self.f.cau_hinh(tick=False)
        self.check_points(False, "MTQ_CHUA_TICK")

    def test_bat_chin_diem_thieu_pham_vi_giu_loi_service(self):
        self.f.cau_hinh(scope=None)
        self.check_points(False)

    def test_lo_xuat_module_khac_bi_chan_khong_fallback(self):
        from psycopg.rows import dict_row
        f = self.f
        obj = f.obj("kho.lo_xuat", f.lo_xuat(f.pn, module="M5"))
        f.cau_hinh()
        f.c.execute("SET LOCAL ROLE app_web")
        old = MagicMock(side_effect=AssertionError("Không fallback"))
        with f.c.cursor(row_factory=dict_row) as cursor:
            with self.assertRaises(quyen.TuChoiThamQuyen) as cm:
                quyen.kiem_tham_quyen(cursor, "CRM:FILE_SOAT:XEM", obj, {"kiem_cu": old})
        self.assertEqual(cm.exception.code, "MTQ_CAN_RESOLVER_MTQ4")
        old.assert_not_called()


if __name__ == "__main__":
    unittest.main()
