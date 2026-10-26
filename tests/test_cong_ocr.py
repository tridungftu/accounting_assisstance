"""Chỉ dữ liệu DEMO; mỗi ca một gốc tạm, không import/chạy Review hoặc ABBYY."""

from collections import Counter
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from kho_tri_thuc.ha_tang import cong_ocr as OCR
from kho_tri_thuc.ha_tang.cong_ocr import CongOCR
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m9.ocr_hot_folder import HotFolderM9


CHO = 20


def _ghi_tien_trinh(goc, ten, bat_dau, san_sang, ket_qua):
    """Target cấp module cho multiprocessing spawn, không đụng Hot Folder thật."""
    try:
        goc = Path(goc)
        cong = CongOCR(goc / ("hot_demo_" + ten),
                      tep_so_trang=goc / "review_demo" / "ocr_abbyy" / "so_trang.json",
                      thu_muc_dem=goc / ("dem_demo_" + ten), nghi=0.01)
        san_sang.put(ten)
        if not bat_dau.wait(CHO):
            raise AssertionError("Chưa bắt đầu ghi DEMO")
        for i in range(20):
            cong._giu_trang(i % 3 + 1, ten + str(i))
        ket_qua.put(("ok", ten))
    except Exception:
        ket_qua.put(("loi", ten))
        raise


def _giu_khoa_tep(tep, da_giu, nha):
    with OCR._khoa_tep(Path(tep), 0.01):
        da_giu.set()
        if not nha.wait(CHO):
            raise AssertionError("Chưa nhả khóa DEMO")


class CongOCRTests(unittest.TestCase):
    def setUp(self):
        self.goc = Path(tempfile.mkdtemp(prefix=f"cong_ocr_demo_{uuid.uuid4().hex}_"))
        self.hot = self.goc / "hot_demo"
        self.so = self.goc / "review_demo" / "ocr_abbyy" / "so_trang.json"
        self.dem = self.goc / "dem_demo"
        self.cong = self._moi()
        self.pdf = b"%PDF-1.4\n/Type /Pages\n/Type /Page\n%%EOF"

    def _moi(self, **kwargs):
        cau_hinh = dict(thu_muc_goc=self.hot, tep_so_trang=self.so,
                        thu_muc_dem=self.dem, nghi=0.01, cho_nhan=0.05,
                        cho_toi_da=1, on_dinh=0.02)
        cau_hinh.update(kwargs)
        return CongOCR(**cau_hinh)

    def _dat_so(self, ds):
        self.so.parent.mkdir(parents=True, exist_ok=True)
        self.so.write_text(json.dumps(ds), encoding="utf-8")

    def _doc_so(self):
        return json.loads(self.so.read_text(encoding="utf-8"))

    def _loi(self, ma, ham):
        with self.assertRaises(DataError) as bat:
            ham()
        self.assertEqual(bat.exception.code, ma)
        self.assertNotIn(str(self.goc), str(bat.exception))
        self.assertNotIn("noi dung DEMO", str(bat.exception))
        return bat.exception

    def _don_tien_trinh(self, tien_trinh, nha):
        nha.set()
        for p in tien_trinh:
            p.join(CHO)
            if p.is_alive():
                p.terminate()
                p.join(CHO)
                self.fail("Tiến trình DEMO không dừng")

    def test_hai_tien_trinh_cung_ghi_khong_mat_ban_ghi(self):
        ctx = multiprocessing.get_context("spawn")
        bat_dau, san_sang, ket_qua = ctx.Event(), ctx.Queue(), ctx.Queue()
        ds = [ctx.Process(target=_ghi_tien_trinh,
                          args=(str(self.goc), ten, bat_dau, san_sang, ket_qua))
              for ten in ("mot", "hai")]
        for p in ds:
            p.start()
        self.addCleanup(self._don_tien_trinh, ds, bat_dau)
        self.assertEqual({san_sang.get(timeout=CHO) for _ in ds}, {"mot", "hai"})
        bat_dau.set()
        self.assertEqual({ket_qua.get(timeout=CHO) for _ in ds}, {("ok", "mot"), ("ok", "hai")})
        for p in ds:
            p.join(CHO)
            self.assertEqual(p.exitcode, 0)
        so = self._doc_so()
        self.assertEqual(len(so), 40)
        self.assertEqual(sum(x[1] for x in so), 2 * sum(i % 3 + 1 for i in range(20)))
        self.assertTrue(all(len(x) == 2 for x in so))

    def test_khoa_in_chan_tien_trinh_khac_va_nha_sau_do(self):
        ctx = multiprocessing.get_context("spawn")
        da_giu, nha = ctx.Event(), ctx.Event()
        p = ctx.Process(target=_giu_khoa_tep, args=(str(self.hot / "in.lock"), da_giu, nha))
        p.start()
        self.addCleanup(self._don_tien_trinh, [p], nha)
        self.assertTrue(da_giu.wait(CHO))
        # Cho nhả khóa sau khi đã quan sát OS từ chối, không đoán bằng sleep.
        if os.name == "nt":
            import msvcrt
            module, ten = msvcrt, "locking"
        else:
            import fcntl
            module, ten = fcntl, "lockf"
        khoa_that = getattr(module, ten)
        tranh_chap = []

        def khoa(*args, **kwargs):
            try:
                return khoa_that(*args, **kwargs)
            except OSError:
                tranh_chap.append(True)
                nha.set()
                raise

        with patch.object(module, ten, side_effect=khoa):
            with OCR._khoa_tep(self.hot / "in.lock", 0.01):
                self.assertTrue(tranh_chap)
        p.join(CHO)
        self.assertEqual(p.exitcode, 0)

    def test_huy_khi_cho_khoa_so_khong_gui_tep(self):
        ctx = multiprocessing.get_context("spawn")
        da_giu, nha = ctx.Event(), ctx.Event()
        p = ctx.Process(target=_giu_khoa_tep,
                        args=(str(self.so.with_suffix(".lock")), da_giu, nha))
        p.start()
        self.addCleanup(self._don_tien_trinh, [p], nha)
        self.assertTrue(da_giu.wait(CHO))
        huy = threading.Event()
        if os.name == "nt":
            import msvcrt
            module, ten = msvcrt, "locking"
        else:
            import fcntl
            module, ten = fcntl, "lockf"
        khoa_that = getattr(module, ten)

        def khoa(*args, **kwargs):
            try:
                return khoa_that(*args, **kwargs)
            except OSError:
                huy.set()  # Hủy đúng khi đã quan sát tranh chấp sổ.
                raise

        with patch.object(module, ten, side_effect=khoa):
            self._loi("OCR_HUY", lambda: self.cong.ocr(self.pdf, "pdf", huy=huy))
        self.assertFalse(self.so.exists())
        self.assertEqual(list((self.hot / "in").iterdir()), [])
        nha.set()
        p.join(CHO)
        self.assertEqual(p.exitcode, 0)

    def test_doc_dung_so_review_va_cong_trang(self):
        cu = [time.time() - 10, 8]
        self._dat_so([cu])
        self.cong._giu_trang(2, "viec_demo")
        so = self._doc_so()
        self.assertIn(cu, so)
        self.assertEqual(sum(x[1] for x in so), 10)
        self.assertTrue(all(len(x) == 2 for x in so))

    def test_vuot_tong_chung_chan_truoc_khi_dua_tep(self):
        self._dat_so([[time.time(), 4999]])
        with patch.object(self.cong, "_chay_hot_folder") as chay:
            self._loi("OCR_HET_HAN_MUC",
                      lambda: self.cong.ocr(self.pdf + b"\n/Type /Page", "pdf"))
        chay.assert_not_called()
        self.assertEqual(list((self.hot / "in").iterdir()), [])
        self.assertEqual(sum(x[1] for x in self._doc_so()), 4999)

    def test_ban_ghi_qua_30_ngay_khong_tinh(self):
        self._dat_so([[time.time() - 31 * 86400, 5000], [time.time(), 4998]])
        self.cong._giu_trang(2, "viec_demo")
        self.assertEqual(sum(x[1] for x in self._doc_so()), 5000)
        self._loi("OCR_HET_HAN_MUC", lambda: self.cong._giu_trang(1, "vuot_demo"))

    def test_ma_viec_dung_mau_review(self):
        for _ in range(50):
            self.assertRegex(OCR._ma_moi(), r"^hd\d{14}_[0-9a-f]{6}$")

    def test_ma_thuc_te_gui_vao_hot_folder_dung_mau_review(self):
        da_gui = []
        replace = os.replace

        def doi(src, dst):
            if Path(dst).parent == self.hot / "in":
                da_gui.append(Path(dst).stem)
            return replace(src, dst)

        with patch.object(OCR.os, "replace", side_effect=doi):
            self._loi("OCR_KHONG_NHAN", lambda: self.cong.ocr(self.pdf, "pdf"))
        self.assertEqual(len(da_gui), 1)
        self.assertRegex(da_gui[0], r"^hd\d{14}_[0-9a-f]{6}$")
        self.assertEqual(self._doc_so(), [])

    def test_khong_nhan_rut_hoac_don_tep_ma_khac(self):
        ma_khac = "hd20261026000000_abcdef"
        d = self.cong.thu_muc()
        tep_khac = []
        for thu_muc in d.values():
            for ten in (ma_khac + ".pdf", ma_khac + ".docx", ma_khac + ".log",
                        "nguoi_dung.demo"):
                tep = thu_muc / ten
                tep.write_bytes(b"noi dung DEMO")
                tep_khac.append(tep)
        self._loi("OCR_KHONG_NHAN", lambda: self.cong.ocr(self.pdf, "pdf"))
        for tep in tep_khac:
            self.assertEqual(tep.read_bytes(), b"noi dung DEMO")
        self.assertEqual(self._doc_so(), [])

    def test_log_ma_khac_khong_bi_nhan_nham(self):
        d = self.cong.thu_muc()
        ma = "hd20261026000000_123456"
        (d["out"] / "hd20261026000000_abcdef.log").write_text(
            ma + " ERROR noi dung DEMO", encoding="utf-8")
        self.assertFalse(self.cong._loi_abbyy(d["out"], ma))

    def test_gop_review_ghi_chen_ngay_truoc_replace_giu_ca_cap_trung(self):
        cap = [time.time() - 10, 2]
        self._dat_so([cap, cap])
        doc_that, lan = self.cong._doc_so, [0]

        def doc():
            lan[0] += 1
            if lan[0] == 2:
                self._dat_so([cap, cap, cap])
            return doc_that()

        with patch.object(self.cong, "_doc_so", side_effect=doc):
            self.cong._giu_trang(1, "viec_demo")
        self.assertEqual(Counter(tuple(x) for x in self._doc_so())[tuple(cap)], 3)
        self.assertEqual(sum(x[1] for x in self._doc_so()), 7)

    def test_review_ghi_chen_lam_het_han_muc_van_chan_truoc_khi_gui(self):
        cu, moi = [time.time() - 10, 4998], [time.time() - 5, 2]
        self._dat_so([cu])
        doc_that, lan = self.cong._doc_so, [0]

        def doc():
            lan[0] += 1
            if lan[0] == 2:
                self._dat_so([cu, moi])
            return doc_that()

        with patch.object(self.cong, "_doc_so", side_effect=doc):
            with patch.object(self.cong, "_chay_hot_folder") as chay:
                self._loi("OCR_HET_HAN_MUC", lambda: self.cong.ocr(self.pdf, "pdf"))
        chay.assert_not_called()
        self.assertEqual(self._doc_so(), [cu, moi])
        self.assertEqual(list((self.hot / "in").iterdir()), [])

    def test_mat_ban_ghi_sau_ghi_thu_lai_mot_lan_va_log_an_toan(self):
        review = [time.time() - 10, 3]
        replace, lan = os.replace, []

        def doi(src, dst):
            ket_qua = replace(src, dst)
            if Path(dst) == self.so:
                lan.append(True)
                if len(lan) == 1:
                    self._dat_so([review])
            return ket_qua

        with patch.object(OCR.os, "replace", side_effect=doi):
            with self.assertLogs(OCR.__name__, level="WARNING") as log:
                self.cong._giu_trang(2, "viec_demo")
        self.assertEqual(len(lan), 2)
        self.assertIn(review, self._doc_so())
        self.assertEqual(sum(x[1] for x in self._doc_so()), 5)
        self.assertEqual(len(log.output), 1)
        self.assertNotIn(str(self.goc), "".join(log.output))
        self.assertNotIn("noi dung DEMO", "".join(log.output))

    def test_mat_ca_sau_thu_lai_dung_khong_gui_tep(self):
        replace, lan = os.replace, []

        def doi(src, dst):
            ket_qua = replace(src, dst)
            if Path(dst) == self.so:
                lan.append(True)
                self._dat_so([])
            return ket_qua

        with patch.object(OCR.os, "replace", side_effect=doi):
            with self.assertLogs(OCR.__name__, level="WARNING"):
                with patch.object(self.cong, "_chay_hot_folder") as chay:
                    self._loi("OCR_LOI_ABBYY", lambda: self.cong.ocr(self.pdf, "pdf"))
        self.assertEqual(len(lan), 2)
        chay.assert_not_called()
        self.assertEqual(list((self.hot / "in").iterdir()), [])

    def test_hoan_chi_ban_ghi_cua_minh_du_cung_epoch_va_so_trang(self):
        now = time.time()
        review = [now, 2]
        self._dat_so([review, review])
        cong_hai = self._moi(thu_muc_dem=self.goc / "dem_hai_demo")
        with patch.object(OCR.time, "time", return_value=now):
            self.cong._giu_trang(2, "mot_demo")
            cong_hai._giu_trang(2, "hai_demo")
            ban_ghi_hai = cong_hai._giu_cho["hai_demo"][:]
            self.cong._hoan_trang("mot_demo")
        so = self._doc_so()
        self.assertIn(ban_ghi_hai, so)
        self.assertEqual(so.count(review), 2)
        self.assertEqual(sum(x[1] for x in so), 6)

    def test_hoan_van_gop_ban_ghi_review_moi(self):
        self.cong._giu_trang(2, "viec_demo")
        review = [time.time() - 10, 3]
        doc_that, lan = self.cong._doc_so, [0]

        def doc():
            lan[0] += 1
            if lan[0] == 2:
                self._dat_so(doc_that() + [review])
            return doc_that()

        with patch.object(self.cong, "_doc_so", side_effect=doc):
            self.cong._hoan_trang("viec_demo")
        self.assertEqual(self._doc_so(), [review])

    def test_so_hong_khong_tu_dat_lai_ve_khong(self):
        for sai in ({"loi": "DEMO"}, [[time.time(), 2, "ma_cu"]],
                    [[time.time(), -1]], [[True, 2]], [[time.time(), True]]):
            with self.subTest(so=sai):
                self._dat_so(sai)
                self._loi("OCR_LOI_ABBYY", lambda: self.cong.ocr(self.pdf, "pdf"))
                self.assertEqual(self._doc_so(), sai)

    def test_huy_khi_cho_khoa_tep_khong_gui_va_nha_khoa(self):
        huy = threading.Event()
        huy.set()
        with self.assertRaises(DataError) as bat:
            with OCR._khoa_tep(self.hot / "in.lock", 0.01, huy):
                self.fail("Không được vào khóa khi đã hủy")
        self.assertEqual(bat.exception.code, "OCR_HUY")
        self.assertFalse(self.hot.exists())
        with OCR._khoa_tep(self.hot / "in.lock", 0.01):
            pass

    def test_hai_module_chia_se_so_nhung_dem_rieng_va_ma_loi_m9(self):
        m9 = HotFolderM9(self.hot, thu_muc_du_lieu=self.goc / "m9_demo",
                        tep_so_trang=self.so, thu_muc_dem=self.goc / "m9_dem_demo",
                        nghi=0.01)
        self._dat_so([[time.time(), 4999]])
        self.cong._giu_trang(1, "viec_demo")
        self.assertEqual(m9.tep_so_trang, self.cong.tep_so_trang)
        self.assertNotEqual(m9.thu_muc_dem, self.cong.thu_muc_dem)
        self._loi("M9_OCR_HET_HAN_MUC", lambda: m9.ocr(self.pdf, "pdf"))

    def test_guard_khong_goi_unlink(self):
        tep = self.goc / "giu_demo"
        tep.write_bytes(b"DEMO")
        with patch.dict(os.environ, {"CODEX_NO_DELETE_FILES": "1"}):
            with patch.object(Path, "unlink", side_effect=AssertionError("Không được xóa")):
                OCR._xoa(tep)
        self.assertEqual(tep.read_bytes(), b"DEMO")


if __name__ == "__main__":
    unittest.main()
