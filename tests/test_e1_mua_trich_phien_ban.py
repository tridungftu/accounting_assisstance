"""E1-4b: danh mục DEMO đã sửa đi vào lượt trích offline và JSON kết quả."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_e1_mua_quy_tac as fixture

D, Q, MODS, TEN = fixture.D, fixture.Q, fixture.MODS, fixture.TEN


class E1TrichPhienBanTests(unittest.TestCase):
    setUp = fixture.E4PhienBanTests.setUp

    def _trich(self, loai, params=None, meta=None, module=Q):
        info = {"text": "DEMO lịch thanh toán", "chunks": ["DEMO lịch thanh toán"],
                "bang_nguon": {"DEMO": True},
                "report": {"file": "DEMO.docx", "words": 4, "articles": 0, "warnings": []}}
        out = self.tam / (loai or "mac_dinh")
        tx = module.TrichXuat(self.params if params is None else params, out_dir=str(out),
                             che_do="RULE_ONLY", loai_hop_dong=loai, meta=meta)
        def ghi(kq, folder):
            Path(folder, "DEMO_KET_QUA.json").write_text(
                json.dumps(kq, ensure_ascii=False), encoding="utf-8")
        with patch.object(module, "read_contract", return_value=copy.deepcopy(info)), \
             patch.object(module, "save"), patch.object(tx, "tc_theo_quy_tac", return_value={}), \
             patch.object(module, "tim_dap_an", return_value=None), \
             patch.object(MODS[TEN + ".xuat"], "ghi_ket_qua_hd", side_effect=ghi):
            kq = tx.xu_ly("DEMO.docx")
        disk = next(out.rglob("DEMO_KET_QUA.json"))
        self.assertEqual(json.loads(disk.read_text(encoding="utf-8")), kq)
        return kq

    def test_sua_danh_muc_trich_noi_dung_moi_va_ghi_sha_hien_hanh(self):
        stale = D.load_params_ban_chup(self.cat)
        stale = [p for p in stale if p["ma"] == "TT-20"]
        D.sua_danh_muc("DV", "TT-20", "mo_ta", "Lịch DEMO mới", "DEMO", "Thử bản mới")
        sha = D.sua_danh_muc("DV", "TT-20", "bk", "demo", "DEMO", "Thử từ khóa")
        self.assertEqual(sha, hashlib.sha256(self.cat.read_bytes()).hexdigest())
        self.assertNotEqual(sha, self.sha)
        kq = self._trich("DV", stale)
        self.assertEqual(kq["phien_ban_danh_muc"], sha)
        self.assertEqual([r["ma"] for r in kq["bang"]], ["TT-20"])
        self.assertEqual(kq["bang"][0]["mo_ta"], "Lịch DEMO mới")
        self.assertTrue(kq["doan_lien_quan"]["TT-20"])
        self.assertEqual(list(self.tam.glob("*.tmp")), [])

    def test_ban_chup_loai_mua_nhan_sha_da_sua(self):
        sha = D.sua_danh_muc("DV", "TT-20", "mo_ta", "DEMO mới", "DEMO", "Thử bản chụp")
        meta = {"loai_hop_dong": "DV", "catalog_id": "DV", "catalog_sha256": sha}
        params = [p for p in D.load_params_ban_chup(self.cat) if p["ma"] == "TT-20"]
        kq = self._trich("DV", params, meta)
        self.assertEqual(kq["phien_ban_danh_muc"], sha)
        self.assertEqual(kq["bang"][0]["mo_ta"], "DEMO mới")

    def test_nhat_ky_sua_tay_chuoi_gay_tu_choi_truoc_doc_hop_dong(self):
        D.sua_danh_muc("DV", "TT-20", "mo_ta", "DEMO mới", "DEMO", "Thử nhật ký")
        path = D.duong_dan_nhat_ky(self.cat)
        event = json.loads(path.read_text(encoding="utf-8"))
        event["phien_ban_cu"] = "0" * 64
        path.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
        with patch.object(Q, "read_contract", side_effect=AssertionError("Không được đọc đầu vào")):
            with self.assertRaisesRegex(ValueError, "Nhật ký danh mục loại DV không hợp lệ.*Chuỗi phiên bản"):
                Q.TrichXuat(self.params, che_do="RULE_ONLY", loai_hop_dong="DV")

    def test_xd_mac_dinh_va_tuong_minh_trung_fixture(self):
        a, b = self._trich(None), self._trich("XD")
        # Hai trường thời gian phụ thuộc lúc chạy; mọi nội dung kết quả còn lại phải bằng nhau.
        for kq in (a, b):
            kq.pop("tao_luc")
            kq["tom_tat"].pop("thoi_gian_giay")
        self.assertEqual(a, b)
        self.assertEqual(a["phien_ban_danh_muc"], self.sha)
        self.assertEqual(a["bang"][0]["mo_ta"], self.params[0]["mo_ta"])


if __name__ == "__main__":
    unittest.main()
