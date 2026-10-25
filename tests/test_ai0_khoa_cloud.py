"""AI-0b/AI-3: Cloud chỉ qua cổng AI và Mask v2; Local tiếp tục chạy. Chỉ DEMO, không mạng."""

import copy
import hashlib
import importlib
import json
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
from kho_tri_thuc.tri_thuc import cong_ai as ca
from tests.test_cong_ai import MaskGia, KHOA_MASK


LY_DO = "CLOUD_TAT"
THONG_BAO = "Cloud đang tắt; phần mềm dùng Local AI."
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
        ch = importlib.import_module(GOI + "cau_hinh")
        self.cam.append(self.stack.enter_context(patch.object(
            ch, "doc_khoa", side_effect=AssertionError("Không được đọc khóa nguồn"))))
        self.stack.enter_context(patch.object(self.cloud, "doc_cau_hinh",
                                             return_value={"local_ai": {}, "cong_ai": {"cloud_bat": False}}))
        self.an = self.stack.enter_context(patch.object(
            self.cloud, "AnDanh", side_effect=AssertionError("Cloud không dùng bộ che riêng")))


    def tearDown(self):
        self.an.assert_not_called()
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
                    self.assertIn("đi qua cổng AI", str(exc.exception))

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
            with self.subTest(ncc=ncc):
                ai = self.ai_cloud.MayCloud(ncc)
                with patch.object(self.ai_cloud.threading, "Thread") as luong:
                    for goi in (ai.models, lambda: ai._goi("DEMO"),
                                lambda: ai.chat_json("DEMO", {}, "ket_qua"), lambda: ai.hoi_trich("DEMO")):
                        with self.assertRaisesRegex(self.ai_local.AILoi, "Cloud đang tắt"):
                            goi()
                    luong.assert_not_called()
                self.assertEqual((ai.tok_vao, ai.tok_ra, ai.so_lan_goi), (0, 0, 0))

    def test_da_dung_khong_goi_cong(self):
        dung = threading.Event()
        dung.set()
        cong, mask, provider, _ = self.cong_gia()
        ai = self.ai_cloud.MayCloud(cong_ai=cong, dung=dung)
        with self.assertRaises(self.ai_local.DaDung):
            ai.hoi_trich("DEMO")
        mask._goi.assert_not_called()
        provider.tra_loi.assert_not_called()

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

    def cong_gia(self, *, cloud_bat=True, con_sot=(), ro_ri=False, local=None, loi_trich=False):
        """Cổng thật + MaskV2 parser thật, transport và nhà cung cấp giả, không socket."""
        gia = MaskGia(con_sot=con_sot, ro_ri=ro_ri)
        mask = ca.MaskV2("http://127.0.0.1:8017", "")
        mask.co_khoa = Mock(return_value=True)

        def mask_goi(path, body):
            status, data = gia.xu_ly("POST" if body is not None else "GET", path,
                                     {"Authorization": "Bearer " + KHOA_MASK}, body)
            self.assertEqual(status, 200)
            return data

        mask._goi = Mock(side_effect=mask_goi)
        provider = Mock()

        def tra_loi(system, user, **kw):
            dong_b = next(x for x in user.splitlines() if x.startswith("Bên B:"))
            value = dong_b.split(": ", 1)[1].rstrip(".")
            data = {"truong": [{"ten": "TC-07", "gia_tri": value,
                                "trich_dan": dong_b.replace("Bên B:", "Bên bán:") if loi_trich else dong_b},
                               {"ten": "TT-02", "gia_tri": "1.250.000.000 đồng",
                                "trich_dan": "Giá trị hợp đồng: 1.250.000.000 đồng."}], "do_tin_cay": 0.95}
            return ca.PhanHoiCloud(json.dumps(data, ensure_ascii=False), kw["model"], 120, 30)

        provider.tra_loi.side_effect = tra_loi
        cfg = {"local_ai": {"enabled": bool(local), "url": "http://127.0.0.1:1234/v1/chat/completions",
                            "model": "DEMO-local"},
               "cong_ai": {"cloud_bat": cloud_bat}}
        ghi = ca.BoGhiBoNho()
        cong = ca.CongAI(cfg, bo_ghi=ghi, mask=mask, nha_cung_cap=provider,
                        moi_truong={"ANTHROPIC_API_KEY": "DEMO"},
                        local_transport=Mock(return_value=local))
        return cong, mask, provider, ghi

    def may_gia(self, cong):
        ai = self.ai_cloud.MayCloud(cong_ai=cong, nhat_ky="khong-ghi-van-ban.txt")
        ai.dat_dinh_danh({"BEN_B": ["Công ty DEMO Beta"], "SO_HD": ["HĐ-DEMO-01"],
                          "MST": ["0109999999"], "BEN_A": ["", None]})
        return ai

    def prompt_demo(self):
        return self.cloud._prompt([{"ma": "TC-07", "mo_ta": "Bên B"},
                                   {"ma": "TT-02", "mo_ta": "Giá trị hợp đồng"}],
                                  ["Hợp đồng số HĐ-DEMO-01, MST 0109999999, ngày 15/03/2026.",
                                   "Bên B: Công ty DEMO Beta.",
                                   "Giá trị hợp đồng: 1.250.000.000 đồng."])

    def test_quet_review_khong_con_dau_noi_nha_cung_cap(self):
        cam = ("api.anthropic.com", "api.openai.com", "x-api-key", "Authorization: Bearer")
        for tep in NR.GOC.rglob("*.py"):
            src = tep.read_text(encoding="utf-8")
            for chuoi in cam:
                self.assertNotIn(chuoi, src, str(tep))

    def test_cong_tat_khong_goi_mask_cloud_hay_doc_khoa(self):
        cong, mask, provider, _ = self.cong_gia(cloud_bat=False)
        with patch.object(cong, "_env", side_effect=AssertionError("Không đọc khóa")):
            ai = self.may_gia(cong)
            with self.assertRaisesRegex(self.ai_local.AILoi, "Cloud đang tắt"):
                ai.hoi_trich(self.prompt_demo())
            self.assertFalse(self.cloud.thu_ket_noi("anthropic", cong_ai=cong)["ok"])
        mask.co_khoa.assert_not_called()
        mask._goi.assert_not_called()
        provider.tra_loi.assert_not_called()

    def test_mask_con_sot_khong_gui_cloud(self):
        cong, mask, provider, ghi = self.cong_gia(con_sot=[{"cum": "DEMO", "so_lan": 1}])
        with self.assertRaisesRegex(self.ai_local.AILoi, "còn sót"):
            self.may_gia(cong).hoi_trich(self.prompt_demo())
        provider.tra_loi.assert_not_called()
        self.assertTrue(mask._goi.called)
        self.assertEqual(ghi.ban_ghi[-1].ly_do_khong_gui, "MASK_CON_SOT")
        self.assertFalse(ghi.ban_ghi[-1].da_gui)

    def test_mask_bao_dat_nhung_con_dinh_danh_cong_van_chan(self):
        cong, _, provider, ghi = self.cong_gia(ro_ri=True)
        with self.assertRaisesRegex(self.ai_local.AILoi, "còn định danh"):
            self.may_gia(cong).hoi_trich(self.prompt_demo())
        provider.tra_loi.assert_not_called()
        self.assertEqual(ghi.ban_ghi[-1].ly_do_khong_gui, "CON_SOT_DINH_DANH")

    def test_mask_dat_gui_ban_che_mo_che_kiem_tren_goc(self):
        cong, mask, provider, ghi = self.cong_gia()
        ai = self.may_gia(cong)
        with patch("builtins.open", side_effect=AssertionError("Không ghi nhật ký văn bản")):
            data, _, _ = ai.hoi_trich(self.prompt_demo())
        self.assertEqual({x["ma"]: x["gia_tri"] for x in data},
                         {"TC-07": "Công ty DEMO Beta", "TT-02": "1.250.000.000 đồng"})
        user = provider.tra_loi.call_args.args[1]
        for goc in ("Công ty DEMO Beta", "HĐ-DEMO-01", "0109999999"):
            self.assertNotIn(goc, user)
        self.assertIn("1.250.000.000 đồng", user)
        self.assertIn("15/03/2026", user)
        che = next(c.args[1] for c in mask._goi.call_args_list if c.args[0] == "/api/v1/che")
        self.assertIn({"gia_tri": "HĐ-DEMO-01", "nhom": "HOP_DONG"}, che["dinh_danh_da_biet"])
        self.assertIn({"gia_tri": "0109999999", "nhom": "MA_SO_THUE"}, che["dinh_danh_da_biet"])
        self.assertTrue(ghi.ban_ghi[-1].trich_dan_hop_le)
        self.assertEqual((ghi.ban_ghi[-1].token_vao, ghi.ban_ghi[-1].token_ra), (120, 30))
        self.assertTrue(any(c.args[0] == "/api/v1/mo-che" for c in mask._goi.call_args_list))
        self.assertEqual(ai.so_lan_goi, 1)
        self.assertNotIn("Công ty DEMO Beta", repr([b.thanh_dict() for b in ghi.ban_ghi]))

    def test_trich_dan_sai_bi_loai_sau_mo_che(self):
        cong, _, _, ghi = self.cong_gia(loi_trich=True)
        data, _, _ = self.may_gia(cong).hoi_trich(self.prompt_demo())
        self.assertEqual([x["ma"] for x in data], ["TT-02"])
        self.assertFalse(ghi.ban_ghi[-1].trich_dan_hop_le)

    def test_khong_chap_nhan_cau_trich_chi_co_trong_chi_dan(self):
        cong, _, provider, _ = self.cong_gia()
        provider.tra_loi.side_effect = None
        provider.tra_loi.return_value = ca.PhanHoiCloud(
            json.dumps({"truong": [{"ten": "TT-02", "gia_tri": "999",
                                    "trich_dan": "Giá giả DEMO 999"}], "do_tin_cay": 1}), "DEMO", 1, 1)
        prompt = self.cloud._prompt([{"ma": "TT-02", "mo_ta": "Giá giả DEMO 999"}],
                                    ["Giá thật DEMO 123."])
        with self.assertRaises(self.ai_local.AILoi):
            self.may_gia(cong).hoi_trich(prompt)

    def test_mac_dinh_dung_cai_dat_chung_khong_bat_tu_cloud_cu(self):
        settings = {"local_ai": {}, "cloud": {"bat": True}, "cong_ai": {"cloud_bat": False}}
        with patch.object(self.cloud, "doc_cau_hinh", return_value=settings) as doc:
            ai = self.ai_cloud.MayCloud()
        doc.assert_called_once_with(dung_env=False)
        self.assertFalse(ai.cong_ai.cai_dat["cloud_bat"])
        self.assertIn("BOC_TACH_HOP_DONG", ca.LOAI_VIEC)

    def test_cau_hinh_engine_thieu_cong_ai_khong_lay_model_local_cho_cloud(self):
        settings = {"model": "qwen-DEMO-local", "nha_cung_cap": "openai", "cloud_bat": True,
                    "local_ai": {"model": "qwen-DEMO-local"}, "cloud": {"bat": True}}
        for cfg in (settings, {"settings": settings}):
            with self.subTest(long_settings="settings" in cfg):
                cong = self.cloud.tao_cong_ai(cfg)
                self.assertEqual(cong.cai_dat, ca.cong_ai_settings({"cong_ai": {}}))
                self.assertNotEqual(cong.cai_dat["model"], settings["model"])
                self.assertEqual(cong.local_ai, settings["local_ai"])
                self.assertFalse(cong.cai_dat["cloud_bat"])
        cong = self.cloud.tao_cong_ai({"cong_ai": None, "local_ai": None, "model": "Local-DEMO"})
        self.assertEqual(cong.cai_dat, ca.cong_ai_settings({"cong_ai": {}}))
        self.assertEqual(cong.local_ai, {})

    def test_thu_ket_noi_dung_trang_thai_mask_khong_goi_model(self):
        cong, mask, provider, _ = self.cong_gia()
        self.assertTrue(self.cloud.thu_ket_noi("anthropic", cong_ai=cong)["ok"])
        mask._goi.assert_called_once_with("/api/v1/trang-thai", None)
        provider.tra_loi.assert_not_called()

    def test_chat_json_vi_tri_qua_cong_va_chi_nhan_id_co_that(self):
        cong, _, _, _ = self.cong_gia()
        yc = []
        def goi(req):
            yc.append(req)
            return ca.KetQuaAI(req.loai_viec, "VANG", {
                "TT-02": ca.TruongAI("TT-02", "r01", "r01 | Điều 1 | Giá trị", "CLOUD")},
                "CLOUD", "DEMO")
        cong.goi = Mock(side_effect=goi)
        data, _, _ = self.may_gia(cong).chat_json(
            "THAM SỐ:\n- TT-02 | Giá trị\nMỤC LỤC HỢP ĐỒNG:\nr01 | Điều 1 | Giá trị", {}, "vi_tri")
        self.assertEqual(data, {"vi_tri": [{"ma": "TT-02", "ids": ["r01"]}]})
        self.assertEqual(yc[0].truong, ("TT-02",))
        self.assertNotIn("THAM SỐ", yc[0].van_ban)

    def buoc8(self, cong):
        kt = importlib.import_module(GOI + "kiem_tra")
        text = ("Bên B: Công ty DEMO Beta.\n"
                "Giá trị hợp đồng: 1.250.000.000 đồng.")
        row = {"id": "r01", "dieu": "1", "khoan": "", "tieu_de_khoan": "", "tieu_de_dieu": "Giá hợp đồng",
               "noi_dung": text}
        bang = [{"ma": "TT-02", "gia_tri": "1.250.000.000 đồng", "nguon": "Local", "muc": 3,
                 "kiem_tra": "KIỂM TRA", "kiem_tra_tu": "KIỂM TRA"}]
        truoc = copy.deepcopy(bang)
        with patch("builtins.open", side_effect=AssertionError("Không ghi văn bản hợp đồng")):
            kq = self.cloud.kiem_tra_cloud(
                bang, [{"ma": "TT-02", "mo_ta": "Giá trị hợp đồng", "luon_cloud": True}],
                {"TC-07": {"gia_tri": "Công ty DEMO Beta"}}, {"TT-02": [row]}, {"r01": row},
                kt.norm(text), kt.loose(text), "khong-ghi-van-ban", {"ty_le": 100}, cong_ai=cong)
        return bang, truoc, kq

    def test_buoc8_qua_mask_va_kiem_tra_trich_dan_goc(self):
        cong, _, provider, _ = self.cong_gia()
        bang, _, kq = self.buoc8(cong)
        self.assertEqual((kq["so_o_gui"], kq["xac_nhan"]), (1, 1))
        self.assertEqual(bang[0]["nguon"], "Local – cloud xác nhận")
        self.assertEqual(bang[0]["dieu_khoan"], "Điều 1")
        self.assertNotIn("Công ty DEMO Beta", provider.tra_loi.call_args.args[1])
        self.assertEqual(kq["nhat_ky"], "")

    def test_buoc8_mask_con_sot_giu_nguyen_local(self):
        cong, _, provider, _ = self.cong_gia(con_sot=[{"cum": "DEMO", "so_lan": 1}])
        bang, truoc, kq = self.buoc8(cong)
        self.assertEqual(bang, truoc)
        self.assertEqual(kq["so_o_gui"], 0)
        self.assertIn("còn sót", kq["loi"])
        provider.tra_loi.assert_not_called()

    def test_buoc8_khong_goi_ket_qua_local_la_cloud_xac_nhan(self):
        local = json.dumps({"truong": [{"ten": "TT-02", "gia_tri": "1.250.000.000 đồng",
                                       "trich_dan": "Giá trị hợp đồng: 1.250.000.000 đồng."}],
                            "do_tin_cay": 0.95})
        cong, mask, provider, _ = self.cong_gia(local=local)
        bang, truoc, kq = self.buoc8(cong)
        self.assertEqual(bang, truoc)
        self.assertEqual((kq["so_o_gui"], kq["xac_nhan"]), (0, 0))
        mask._goi.assert_not_called()
        provider.tra_loi.assert_not_called()

    def test_buoc8_nhom_dau_loi_van_hoi_nhom_sau(self):
        kt = importlib.import_module(GOI + "kiem_tra")
        text = "Giá trị hợp đồng: 1.250.000.000 đồng."
        row = {"id": "r01", "dieu": "1", "khoan": "", "tieu_de_khoan": "",
               "tieu_de_dieu": "Giá hợp đồng", "noi_dung": text}
        for loi in ("AILoi", "Mask còn sót", "Cloud trả không hợp lệ"):
            with self.subTest(loi=loi):
                cong, mask, provider, ghi = self.cong_gia()
                ai = self.ai_cloud.MayCloud(cong_ai=cong)
                goi_that = cong.goi
                lan_goi = []

                def goi(req):
                    lan_goi.append(req.truong)
                    if len(lan_goi) == 1 and loi == "AILoi":
                        raise self.ai_local.AILoi("Lỗi cổng DEMO")
                    return goi_that(req)

                cong.goi = Mock(side_effect=goi)
                mask_goi_that = mask._goi.side_effect

                def mask_goi(path, body):
                    if path == "/api/v1/che" and len(lan_goi) == 1 and loi == "Mask còn sót":
                        gia = MaskGia(con_sot=[{"cum": "DEMO", "so_lan": 1}])
                        return gia.xu_ly("POST", path, {"Authorization": "Bearer " + KHOA_MASK}, body)[1]
                    return mask_goi_that(path, body)

                mask._goi.side_effect = mask_goi

                def tra_loi(system, user, **kw):
                    data = ("không phải JSON" if len(lan_goi) == 1 else
                            json.dumps({"truong": [{"ten": "TT-03", "gia_tri": "1.250.000.000 đồng",
                                                    "trich_dan": text}], "do_tin_cay": 0.95}))
                    return ca.PhanHoiCloud(data, kw["model"], 1, 1)

                provider.tra_loi.side_effect = tra_loi
                bang = [{"ma": ma, "gia_tri": "1.250.000.000 đồng", "nguon": "Local", "muc": 3,
                         "kiem_tra": "KIỂM TRA", "kiem_tra_tu": "KIỂM TRA"} for ma in ("TT-02", "TT-03")]
                truoc = copy.deepcopy(bang)
                params = [{"ma": d["ma"], "mo_ta": "Giá trị hợp đồng", "luon_cloud": True} for d in bang]
                log = []
                with patch.object(self.cloud, "GROUP_MAX", 1), patch.object(self.ai_cloud, "MayCloud", return_value=ai):
                    kq = self.cloud.kiem_tra_cloud(
                        bang, params, {}, {d["ma"]: [row] for d in bang}, {"r01": row},
                        kt.norm(text), kt.loose(text), "khong-ghi-van-ban", {"ty_le": 100},
                        cong_ai=cong, ghi_log=log.append)
                self.assertEqual(lan_goi, [("TT-02",), ("TT-03",)])
                self.assertEqual(bang[0], truoc[0])
                self.assertEqual(bang[1]["nguon"], "Local – cloud xác nhận")
                self.assertEqual((kq["so_o_chon"], kq["so_o_gui"], kq["xac_nhan"]), (2, 1, 1))
                self.assertEqual(len(kq["khong_gui"]), 1)
                self.assertTrue(kq["khong_gui"][0].startswith("TT-02: bỏ nhóm vì cổng AI chưa có kết quả:"))
                self.assertTrue(log[-1].endswith("không gửi 1"))
                self.assertEqual(ai.so_khong_gui, int(loi == "Mask còn sót"))
                self.assertEqual(provider.tra_loi.call_count, 2 if loi == "Cloud trả không hợp lệ" else 1)
                if loi == "Cloud trả không hợp lệ":
                    cloud_logs = [b for b in ghi.ban_ghi if b.duong == "CLOUD"]
                    self.assertTrue(all(b.da_gui for b in cloud_logs))

    def test_may_cloud_da_ghim_goi_duoc_cong_o_ngoai_review(self):
        thieu = [rel for rel in NR.PIN if not (NR.GOC / rel).is_file()]
        if thieu:
            self.skipTest("NOT_RUN: thiếu tệp lõi nguồn: " + ", ".join(thieu))
        NR.nap()
        cong, _, _, _ = self.cong_gia()
        ai = NR._m("trich_xuat.ai_cloud").MayCloud(cong_ai=cong)
        ai.dat_dinh_danh({"BEN_B": ["Công ty DEMO Beta"], "SO_HD": ["HĐ-DEMO-01"], "MST": ["0109999999"]})
        items, _, _ = ai.hoi_trich(self.prompt_demo())
        self.assertEqual(items[0]["gia_tri"], "Công ty DEMO Beta")



if __name__ == "__main__":
    unittest.main()
