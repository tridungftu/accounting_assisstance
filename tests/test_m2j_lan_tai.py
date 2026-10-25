"""M2j: route đọc thuần/mock, manifest DEMO thật; không server/PostgreSQL/cổng thuế."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_m2_00_manifest_tinh import tao_run_demo
from kho_tri_thuc.giao_dien import m2_tai_hoa_don as mod
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import nguon_chung


class LanTai(unittest.TestCase):
    def setUp(self):
        tam = tempfile.TemporaryDirectory(prefix="M2j-DEMO-", ignore_cleanup_errors=True)
        self.addCleanup(tam.cleanup)
        self.goc = Path(tam.name)
        self.run_id, self.handle = "20261024-120000", "ab" * 32
        self.rel = f"DEMO/2026-10/mua_vao/{self.run_id}"
        self.thu_muc = self.goc / self.rel
        self.thu_muc.mkdir(parents=True)
        self.m = tao_run_demo(self.thu_muc)
        self.ghi_manifest()
        self.ctx = {"run_id": self.run_id, "phap_nhan_ma": "DEMO", "source_instance": "DEMO", "scope_ref": "DEMO",
                    "yeu_cau": {"mode": "month", "year": 2026, "month": 10, "types": ["purchase"]}}
        self.duoc = True
        self.doc_da_goi = []

        def kiem(sid, run):
            if sid != "sid-DEMO":
                raise DataError("M2_00B_CAN_DOI_SOAT", "Lần tải thuộc phiên khác.")
            if not self.duoc:
                raise DataError("KHONG_CO_QUYEN_PHAP_NHAN", "Quyền đã thu hồi.")
            self.assertEqual(run, self.handle)

        def status(sid, run):
            kiem(sid, run)
            return {"trang_thai": "REPLAY", "ket_qua": {"trang_thai": "COMPLETE", "runs": [
                {"ky": "2026-10", "chieu": "purchase", "run_rel": self.rel, "trang_thai": "COMPLETE"}]}}

        def duoi_khoa(sid, run, fn):
            kiem(sid, run)
            return fn("DEMO_actor")

        self.dv = SimpleNamespace(status=status, ngu_canh=lambda *_: dict(self.ctx), ghi_duoi_khoa=duoi_khoa,
                                  kiem_run=kiem, cau_hinh=SimpleNamespace(goc_tai=self.goc), goc_hoi_cuu_tin_cay=())
        # Hóa đơn ở trang 2; hai hóa đơn khác có cùng ngày vẫn không được lọt.
        self.rows = [{"id": "DEMO-cu-cung-ngay"}, {"id": "DEMO-lan-khac"}, {"id": "DEMO-dung-lan-tai"}]

        def danh_sach(actor, *, phap_nhan, ky=None, trang=1):
            self.assertEqual((actor, phap_nhan), ("DEMO_actor", "DEMO"))
            self.doc_da_goi.append((ky, trang))
            rows = [] if ky and ky != "2026-10" else self.rows
            return {"hoa_don": rows[(trang - 1) * 2:trang * 2], "co": 2, "tong": len(rows), "trang": trang}

        self.m2 = SimpleNamespace(conn=object(), danh_tinh=lambda actor: {"dang_nhap": actor}, _tx=lambda _: nullcontext(), danh_sach=danh_sach)
        self.app = SimpleNamespace(is_that=False, m2=lambda: self.m2, _crm_db=lambda fn, *a: fn(*a))
        self.app.m2_state = lambda actor, q: {"cau_hinh": True, "nguon": ["DEMO-nguon-hien-co"], **danh_sach(
            actor, phap_nhan=q["phap_nhan"][0], ky=(q.get("ky") or [None])[0])}
        self.h = SimpleNamespace(crm_sid=lambda: "sid-DEMO", send_content=lambda status, body, **_: (status, body))
        self.profile = {"reference_id": "DEMO", "sha256": "0" * 64}
        self.p_doc = patch.object(nguon_chung, "doc_profile", return_value=self.profile)
        self.p_tim = patch.object(nguon_chung, "tim_lan_nhan", side_effect=self.tim_lan_nhan)
        self.tim = self.p_tim.start()
        self.p_doc.start()
        self.addCleanup(self.p_tim.stop)
        self.addCleanup(self.p_doc.stop)
        p = patch.object(mod, "dich_vu", return_value=self.dv)
        p.start()
        self.addCleanup(p.stop)

    def ghi_manifest(self):
        (self.thu_muc / "manifest.json").write_text(json.dumps(self.m, ensure_ascii=False), encoding="utf-8")

    def tim_lan_nhan(self, conn, inst, profile, key):
        self.assertIs(conn, self.m2.conn)
        self.assertEqual((inst, profile), ("DEMO", self.profile))
        # Khóa M2c độc lập với thời điểm tải/nhận, cùng token nhan.py.
        token = json.dumps(["DEMO", "2026-10", "purchase", self.run_id, 1, 1], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(key, "M2c:" + hashlib.sha256(token.encode("utf-8")).hexdigest())
        return {"ket_qua_cuoi": {"promote": {"items": [{"hoa_don_id": "DEMO-dung-lan-tai"}, {"hoa_don_id": "DEMO-dung-lan-tai"}]}}}

    def goi(self, **query):
        q = {"run": [self.handle], **{k: [v] for k, v in query.items()}}
        return mod.dieu_huong(self.h, self.app, False, mod.TIEN_TO + "/hoa-don", q)

    def test_loc_dung_lan_tai_khong_suy_ngay_khong_mat_trang_2(self):
        status, data = self.goi(ky="2026-10")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["hoa_don"], [{"id": "DEMO-dung-lan-tai"}])
        self.assertEqual(data["tong"], 1)
        self.assertEqual(data["nguon"], ["DEMO-nguon-hien-co"])
        self.assertEqual(self.doc_da_goi, [("2026-10", 1), ("2026-10", 2)])
        self.assertEqual(data["lan_tai"]["run_handle"], self.handle)

    def test_chua_nhan_tra_rong_khong_tu_nhan(self):
        self.tim.side_effect = None
        self.tim.return_value = None
        with patch.object(mod, "nhan_vao_k2") as nhan:
            status, data = self.goi()
        self.assertEqual((status, data["tong"], data["hoa_don"]), (200, 0, []))
        nhan.assert_not_called()

    def test_xem_khi_bo_tai_da_dong_khong_goi_rpc(self):
        self.dv.status = lambda *_: self.fail("Không gọi bộ tải để xem hóa đơn đã nhận")
        self.assertEqual(self.goi()[0], 200)

    def test_ca_nam_ca_hai_chieu_chi_doc_manifest_da_co(self):
        self.ctx["yeu_cau"] = {"mode": "year", "year": 2026, "month": None, "types": ["purchase", "sold"]}
        status, data = self.goi()
        self.assertEqual((status, data["tong"]), (200, 1))
        self.assertEqual(self.tim.call_count, 1)

    def test_phan_trang_sau_khi_loc_va_doi_ky(self):
        status, data = self.goi(trang="2")
        self.assertEqual((status, data["trang"], data["tong"], data["hoa_don"]), (200, 2, 1, []))
        status, data = self.goi(ky="2026-09")
        self.assertEqual((status, data["tong"]), (200, 0))

    def test_sai_phien_mat_quyen_va_gia_phap_nhan_bi_chan(self):
        self.h.crm_sid = lambda: "sid-khac"
        self.assertEqual(self.goi()[0], 409)
        self.h.crm_sid = lambda: "sid-DEMO"
        self.duoc = False
        self.assertEqual(self.goi()[0], 403)
        self.duoc = True
        self.assertEqual(self.goi(phap_nhan="DEMO_KHAC")[0], 403)
        self.tim.assert_not_called()

    def test_thu_hoi_quyen_trong_luc_doc_manifest(self):
        that = mod.doc_manifest

        def doc(*a, **kw):
            m = that(*a, **kw)
            self.duoc = False
            return m
        with patch.object(mod, "doc_manifest", side_effect=doc):
            self.assertEqual(self.goi()[0], 403)
        self.tim.assert_not_called()

    def test_manifest_sai_run_cung_thoi_diem_khong_duoc_tra(self):
        self.m["run_id"] = "20261024-120001"
        self.ghi_manifest()
        self.assertEqual(self.goi()[0], 400)
        self.tim.assert_not_called()

    def test_query_khong_hop_le(self):
        for q in ({"run": "khong-hop-le"}, {"ky": "2026-13"}, {"actor": "CFO"}):
            with self.subTest(q=q):
                self.assertEqual(self.goi(**q)[0], 400)

    def test_manifest_tom_tat_dem_tep_khong_lo_du_lieu(self):
        q = {"run": [self.handle], "run_rel": [self.rel]}
        status, data = mod.dieu_huong(self.h, self.app, False, mod.TIEN_TO + "/manifest", q)
        self.assertEqual((status, data["so_tep"], data["tong"]["tong_hd"]), (200, 3, 1))
        self.assertEqual(data["khoang_ngay"], {"tu": "01/10/2026", "den": "31/10/2026"})
        raw = json.dumps(data, ensure_ascii=False)
        for cam in (str(self.goc), "0000000001", "DEMO__", "sha256", "key_raw"):
            self.assertNotIn(cam, raw)

    def test_manifest_tom_tat_thang_nhuan_va_tep_trung_chi_dem_mot(self):
        m = copy.deepcopy(self.m)
        m["ky"] = "2024-02"
        m["hoa_don"].append(copy.deepcopy(m["hoa_don"][0]))
        m["loi_chung"] = [{"code": "DEMO_LIST_FAILED", "http_status": 403, "stage": "LIST"}]
        data = mod.tom_tat_manifest(m, self.rel)
        self.assertEqual(data["so_tep"], 3)
        self.assertEqual(data["khoang_ngay"]["den"], "29/02/2024")
        self.assertEqual(data["loi_chung"][0]["http_status"], 403)

    def test_manifest_thu_hoi_quyen_sau_io(self):
        that = mod.doc_manifest

        def doc(*a, **kw):
            m = that(*a, **kw)
            self.duoc = False
            return m
        with patch.object(mod, "doc_manifest", side_effect=doc):
            status, data = mod.dieu_huong(self.h, self.app, False, mod.TIEN_TO + "/manifest", {"run": [self.handle], "run_rel": [self.rel]})
        self.assertEqual((status, data["error"]), (403, "KHONG_CO_QUYEN_PHAP_NHAN"))


if __name__ == "__main__":
    unittest.main()
