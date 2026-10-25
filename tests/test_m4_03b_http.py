"""03B HTTP: gọi router thật, service giả; không socket/PG/dữ liệu thật.

PG native giữ ở test_m4_03b_common_pg/test_m4_03a_pg với cổng môi trường có sẵn.
"""
import copy
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kho_tri_thuc.giao_dien import m4 as M
from kho_tri_thuc.k2 import ghi_nhan_chung as GN
from kho_tri_thuc.m4 import ghi_nhan_nghiem_thu as NT
from kho_tri_thuc.ha_tang.primitives import DataError


def uid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


REF = {"kind": "NT", "occurrence_id": uid(1), "source_version_id": uid(2), "part_id": None}
SAVE = {"doi_chieu_id": None, "thanh_phan": [{"nguon": REF, "phan": "TOAN_PHAN", "so_tien_khai": None, "tien_te": None}],
        "can_cu_tep": [], "expected_graph": "a" * 64, "expected_revision": 0, "ly_do": "Căn cứ thử nghiệm", "khoa": "03b-test"}
CONFIRM = {"doi_chieu_id": uid(3), "phien_ban_id": uid(4), "expected_revision": 1, "expected_graph": "b" * 64, "khoa": "03b-xn"}


class Handler:
    headers = {}

    def __init__(self, body):
        self.body = body
        self.sent = None

    def crm_sid(self):
        return "phien-thu"

    def json_body(self):
        if not isinstance(self.body, dict):
            raise ValueError("Yêu cầu không phải object")
        return self.body

    def send_content(self, status, data, mime=None, headers=None):
        self.sent = status, data, headers or {}


class Route03B(unittest.TestCase):
    def setUp(self):
        self.svc = SimpleNamespace(kt_xem=Mock(return_value={"context": {"kt_pending_id": uid(1), "phong_bi_id": uid(2), "dot_id": uid(5)},
                                                          "quyen": {"xem": True}}))
        self.gn = Mock()
        for name in ("xem_doi_chieu", "goi_y_hoa_don", "lich_su", "luu_doi_chieu", "xac_nhan_doi_chieu"):
            getattr(self.gn, name).return_value = {"schema": GN.SCHEMA, "loai": name}
        self.app = SimpleNamespace(mutation_lock=threading.Lock(), _m4=self.svc,
                                   crm_phien=lambda sid: (sid, "ke_toan_phien", False), _crm_db=lambda fn, *a: fn(*a))
        self.factory = patch.object(NT, "dich_vu", return_value=self.gn).start()
        self.rieng = patch.object(M, "_rieng", side_effect=lambda app, svc, fn: fn(svc)).start()
        self.addCleanup(patch.stopall)

    def route(self, path, body=None, query=None):
        h = Handler(body)
        M.dieu_huong(h, self.app, body is not None, "/api/m4/doi-chieu/" + path, query or {})
        return h.sent

    def test_doc_theo_dot_va_con_thieu_lay_nguon_tu_03a(self):
        for path in ("dot/", "con-thieu/"):
            with self.subTest(path=path):
                st, d, headers = self.route(path + uid(1))
                self.assertEqual(st, 200)
                self.assertEqual(d["nguon_nt"], REF)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.svc.kt_xem.assert_called_with("ke_toan_phien", kt_pending_id=uid(1), phong_bi_id=None)
                self.gn.xem_doi_chieu.assert_called_with("ke_toan_phien", {"nguon": [REF]})
                self.gn.goi_y_hoa_don.assert_called_with("ke_toan_phien", uid(5))

    def test_lich_su_chuyen_dung_id_va_danh_tinh_phien(self):
        self.assertEqual(self.route("lich-su/" + uid(3))[0], 200)
        self.gn.lich_su.assert_called_once_with("ke_toan_phien", uid(3))

    def test_ba_post_giu_nguyen_body_va_ket_noi_rieng(self):
        for path, body, method in (("xem", {"nguon": [REF]}, "xem_doi_chieu"), ("luu", SAVE, "luu_doi_chieu"),
                                    ("xac-nhan", CONFIRM, "xac_nhan_doi_chieu")):
            with self.subTest(path=path):
                self.assertEqual(self.route(path, copy.deepcopy(body))[0], 200)
                getattr(self.gn, method).assert_called_once_with("ke_toan_phien", body)
        self.assertEqual(self.rieng.call_count, 3)

    def test_tham_so_get_la_lap_va_authority_deu_400(self):
        for path in ("dot/", "lich-su/", "con-thieu/"):
            for query in ({"q": ["x"]}, {"actor": ["gia"]}, {"phap_nhan_id": [uid(9)]}, {"q": ["1", "2"]}):
                with self.subTest(path=path, query=query):
                    self.assertEqual(self.route(path + uid(1), query=query)[0], 400)
        self.factory.assert_not_called()

    def test_tham_so_post_la_400_khong_goi_dich_vu(self):
        for path, body in (("xem", {"nguon": [REF]}), ("luu", SAVE), ("xac-nhan", CONFIRM)):
            self.assertEqual(self.route(path, {**body, "truong_la": True})[0], 400)
            self.assertEqual(self.route(path, body, {"q": ["x"]})[0], 400)
        self.factory.assert_not_called()

    def test_query_tho_giu_tham_so_rong_khong_bi_dispatcher_bo_qua(self):
        for suffix in ("?actor=", "?la=", "?la=&la=x"):
            h = Handler(None)
            path = "/api/m4/doi-chieu/dot/" + uid(1)
            h.path = path + suffix
            M.dieu_huong(h, self.app, False, path, {})
            self.assertEqual(h.sent[0], 400)
        self.factory.assert_not_called()

    def test_authority_va_truong_long_bi_chan(self):
        for key in ("actor", "phap_nhan_id", "dang_nhap", "ghi_nhan", "request"):
            self.assertEqual(self.route("luu", {**SAVE, key: "gia"})[0], 403)
        for key in ("actor", "phap_nhan_id"):
            body = copy.deepcopy(SAVE)
            body["thanh_phan"][0]["nguon"][key] = "gia"
            self.assertEqual(self.route("luu", body)[0], 403)
        self.factory.assert_not_called()

    def test_quyen_doc_tu_03a_truoc_doc_hoa_don(self):
        self.svc.kt_xem.return_value["quyen"]["xem"] = False
        self.assertEqual(self.route("dot/" + uid(1))[0], 403)
        self.factory.assert_not_called()

    def test_quyen_va_xung_dot_do_dich_vu_quyet(self):
        for code, status in (("DC_PHAM_VI", 403), ("M4_KT_PHAM_VI", 403), ("DC_KHONG_THAY", 404),
                             ("DC_HOA_DON_DA_GAN", 409), ("DC_REVISION_CU", 409), ("DC_CAN_KIEM_LAI", 409)):
            with self.subTest(code=code):
                self.gn.luu_doi_chieu.side_effect = DataError(code, "Hóa đơn đã gắn ở đối chiếu khác.", "thanh_phan.1.nguon")
                st, data, _ = self.route("luu", SAVE)
                self.assertEqual(st, status)
                self.assertEqual(data["field"], "thanh_phan.1.nguon")

    def test_mot_phan_thieu_tien_luu_nhap_duoc_tien_sai_bi_chan(self):
        body = copy.deepcopy(SAVE)
        body["thanh_phan"][0].update(phan="MOT_PHAN", so_tien_khai=None, tien_te="VND")
        self.assertEqual(self.route("luu", body)[0], 200)
        for value in ("0", "-1", "1.1", "1,000"):
            body["thanh_phan"][0]["so_tien_khai"] = value
            self.assertEqual(self.route("luu", body)[0], 422)
        self.assertEqual(self.gn.luu_doi_chieu.call_count, 1)

    def test_id_va_duong_dan_la_khong_goi_dich_vu(self):
        for path in ("dot/sai", "lich-su/" + uid(3) + "/du", "khong-co"):
            self.assertEqual(self.route(path)[0], 404)
        self.factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
