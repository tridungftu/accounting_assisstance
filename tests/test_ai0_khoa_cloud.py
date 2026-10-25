"""AI-0b: Cloud trực tiếp luôn bị khóa trước đọc khóa/mạng; Local tiếp tục chạy."""

import copy
import hashlib
import importlib
import os
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR


LY_DO = "CHO_NOI_MASK_V2"
THONG_BAO = LY_DO + ": Đường Cloud tạm khóa: chờ nối qua Mask file v2"
GOI = "kho_tri_thuc.m4.review_goc.trich_xuat."


class KhoaCloudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Các test chặn mạng vẫn chạy khi worktree thiếu catalog/checklist bị gitignore.
        cls.cloud = importlib.import_module(GOI + "cloud")
        cls.ai_cloud = importlib.import_module(GOI + "ai_cloud")
        cls.ai_local = importlib.import_module(GOI + "ai_local")

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "khoa-gia-anthropic-DEMO",
            "OPENAI_API_KEY": "khoa-gia-openai-DEMO",
            "HD_CLOUD": "1", "HD_CLOUD_TY_LE": "100",
            "HD_CLOUD_URL_ANTHROPIC": "https://cloud-demo.invalid/messages",
            "HD_CLOUD_URL_OPENAI": "https://cloud-demo.invalid/completions",
        }))
        self.cam = []
        for ten in ("urllib.request.urlopen", "http.client.HTTPConnection.connect",
                    "http.client.HTTPSConnection.connect", "socket.create_connection"):
            self.cam.append(self.stack.enter_context(patch(ten, side_effect=AssertionError("Không được gọi mạng"))))
        for module in (self.cloud, self.ai_cloud):
            self.cam.append(self.stack.enter_context(patch.object(
                module, "doc_khoa", side_effect=AssertionError("Không được đọc khóa"))))

    def tearDown(self):
        for mock in self.cam:
            mock.assert_not_called()

    def test_goi_api_chan_moi_nha_cung_cap_va_bien_moi_truong(self):
        for ncc in ("anthropic", "openai", "NHA_CUNG_CAP_KHAC"):
            for co_khoa in (True, False):
                with self.subTest(ncc=ncc, co_khoa=co_khoa):
                    env = dict(os.environ) if co_khoa else {}
                    with patch.dict(os.environ, env, clear=True):
                        with self.assertRaises(self.cloud.CloudLoi) as exc:
                            self.cloud.goi_api(ncc, "model-DEMO", "khoa-gia", "Nội dung DEMO")
                    self.assertEqual(str(exc.exception), THONG_BAO)

    def test_thu_ket_noi_tra_khong_kha_dung(self):
        for ncc in ("anthropic", "openai"):
            with self.subTest(ncc=ncc):
                kq = self.cloud.thu_ket_noi(ncc, "model-DEMO")
                self.assertFalse(kq["ok"])
                self.assertEqual(kq["ma_loi"], LY_DO)
                self.assertEqual(kq["loi"], THONG_BAO)

    def test_buoc_8_bo_qua_khi_cau_hinh_bat_khong_sua_local(self):
        bang = [{"ma": "TT-02", "gia_tri": "1000000000", "nguon": "Local", "muc": 3}]
        truoc = copy.deepcopy(bang)
        for ncc in ("anthropic", "openai"):
            with self.subTest(ncc=ncc):
                log = []
                kq = self.cloud.kiem_tra_cloud(
                    bang, [], {}, {}, {}, "", "", "khong-tao-nhat-ky",
                    {"bat": True, "nha_cung_cap": ncc, "ty_le": 100}, ghi_log=log.append)
                self.assertFalse(kq["bat"])
                self.assertEqual(kq["ma_loi"], LY_DO)
                self.assertEqual(kq["loi"], THONG_BAO)
                self.assertEqual(kq["so_o_gui"], 0)
                self.assertEqual((kq["token_vao"], kq["token_ra"], kq["nhat_ky"]), (0, 0, ""))
                self.assertEqual(bang, truoc)
                self.assertEqual(log, ["Bỏ qua kiểm tra chéo cloud: " + THONG_BAO])

    def test_may_cloud_chan_truoc_doc_khoa_che_va_tao_luong(self):
        for ncc in ("anthropic", "openai"):
            for da_dung in (False, True):
                with self.subTest(ncc=ncc, da_dung=da_dung):
                    dung = threading.Event()
                    if da_dung:
                        dung.set()
                    ai = self.ai_cloud.MayCloud(ncc, dung=dung)
                    ai._khoa = "khoa-gia-da-cache"
                    with patch.object(ai.an, "che") as che, patch.object(self.ai_cloud.threading, "Thread") as luong:
                        for goi in (ai.models, lambda: ai._goi("DEMO"),
                                    lambda: ai.chat_json("DEMO", {}, "ket_qua"), lambda: ai.hoi_trich("DEMO")):
                            with self.assertRaises(self.ai_local.AILoi) as exc:
                                goi()
                            self.assertEqual(str(exc.exception), THONG_BAO)
                        che.assert_not_called()
                        luong.assert_not_called()
                    self.assertEqual((ai.tok_vao, ai.tok_ra, ai.so_lan_goi), (0, 0, 0))

    def test_hai_pin_khop_byte_lf(self):
        for ten in ("cloud", "ai_cloud"):
            rel = "trich_xuat/" + ten + ".py"
            raw = (NR.GOC / rel).read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), NR.PIN[rel])

    def test_nguon_review_nap_dung_hai_pin(self):
        thieu = [rel for rel in NR.PIN if not (NR.GOC / rel).is_file()]
        if thieu:
            self.skipTest("NOT_RUN: thiếu tệp lõi nguồn: " + ", ".join(thieu))
        NR.nap()
        for ten in ("cloud", "ai_cloud"):
            module = NR._m("trich_xuat." + ten)
            self.assertTrue(NR._BO.hop_le("trich_xuat." + ten, module))

    def test_local_gia_lap_tiep_tuc_xu_ly_khi_buoc_8_bi_khoa(self):
        qt = importlib.import_module(GOI + "quy_trinh")
        xuat = importlib.import_module(GOI + "xuat")
        dm = importlib.import_module(GOI + "danh_muc")
        params = [dm.to_param("TT-02", "Giá hợp đồng", "Giá trị hợp đồng (đồng)",
                              "giá hợp đồng", "giá trị hợp đồng", muc=3)]
        tra_loi = {"ma": "TT-02", "gia_tri": "1.000.000.000", "don_vi": "đồng",
                   "trich_dan": "Giá trị hợp đồng là 1.000.000.000 đồng, đã bao gồm thuế VAT 8%."}
        ai = SimpleNamespace(model="Local-DEMO", url="local-gia-lap", tok_vao=0, tok_ra=0,
                             hoi_trich=Mock(return_value=([tra_loi], 0, 0)))
        tam = Path(tempfile.mkdtemp(prefix="ai0b_local_demo_"))  # giữ bằng chứng, không xóa
        tep = tam / "hop-dong-DEMO.docx"
        tep.write_bytes(F.hop_dong_docx())
        log = []
        with patch.object(xuat, "ghi_ket_qua_hd"):
            kq = qt.TrichXuat(params, ai=ai, out_dir=str(tam), ra_lai=False,
                             cloud={"bat": True, "nha_cung_cap": "openai", "ty_le": 100},
                             ghi_log=log.append).xu_ly(str(tep))
        ai.hoi_trich.assert_called_once()
        self.assertEqual(kq["bang"][0]["gia_tri"], "1.000.000.000")
        self.assertEqual(kq["bang"][0]["nguon"], "Local")
        self.assertEqual(kq["tom_tat"]["loi_ai"], 0)
        self.assertEqual(kq["tom_tat"]["cloud"]["ma_loi"], LY_DO)
        self.assertTrue(any(THONG_BAO in dong for dong in log))
        self.assertEqual(list(tam.rglob("GUI_RA_NGOAI_*")), [])


if __name__ == "__main__":
    unittest.main()
