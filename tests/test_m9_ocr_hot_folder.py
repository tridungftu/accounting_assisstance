"""Chỉ dữ liệu DEMO, thư mục tạm và luồng giả ABBYY; không chạy ABBYY thật."""

import hashlib
import io
import json
import os
from pathlib import Path
from queue import Queue
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import zipfile

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m9.ocr_hot_folder import HotFolderM9
from kho_tri_thuc.ha_tang import cong_ocr as OCR


CHO = 20  # Giới hạn phát hiện treo, không phải khoảng ngủ để đoán tiến độ.


def _docx_demo():
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w", zipfile.ZIP_DEFLATED) as tep:
        tep.writestr("[Content_Types].xml", (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        ))
        tep.writestr("_rels/.rels", (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="word/document.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
            '</Relationships>'
        ))
        tep.writestr("word/document.xml", (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>Hợp đồng DEMO</w:t></w:r></w:p></w:body></w:document>'
        ))
    return bo_dem.getvalue()


class HotFolderM9Tests(unittest.TestCase):
    def setUp(self):
        # Giữ lại dữ liệu DEMO; mỗi ca có gốc riêng dù runner đổi thư mục tạm.
        self.goc = Path(tempfile.mkdtemp(prefix=f"m9_ocr_demo_{uuid.uuid4().hex}_"))
        self.giu_tep = os.environ.get("CODEX_NO_DELETE_FILES", "").strip().lower() in (
            "1", "true", "yes", "on")
        self.hot = self.goc / "hot_demo"
        self.du_lieu = self.goc / "du_lieu_demo"
        self.bo_noi = self._moi()
        self.docx = _docx_demo()
        self.pdf = b"%PDF-1.4\n/Type /Pages\n/Type /Page\n%%EOF"
        self.da_thay = []
        self.loi_gia = []

    def _moi(self, **kwargs):
        cau_hinh = dict(cho_nhan=CHO, cho_toi_da=CHO, nghi=0.05, on_dinh=0.1)
        cau_hinh.update(kwargs)
        return HotFolderM9(self.hot, thu_muc_du_lieu=self.du_lieu, **cau_hinh)

    def _gia(self, xu_ly=None):
        """Chuyển file vừa publish qua Queue; xác nhận nhận trước khi OCR tính giờ."""
        d = self.bo_noi.thu_muc()
        dung = threading.Event()
        hang = Queue()
        replace = os.replace
        da_nhan = self.goc / "abbyy_da_nhan_demo"
        da_nhan.mkdir()

        def doi(src, dst):
            ket_qua = replace(src, dst)
            if Path(dst).parent == d["in"]:
                nhan = threading.Event()
                hang.put((Path(dst), nhan))
                self.assertTrue(nhan.wait(CHO), "ABBYY giả chưa nhận file DEMO")
                self.assertEqual(self.loi_gia, [])
            return ket_qua

        def chay():
            try:
                while True:
                    viec = hang.get()
                    if viec is None:
                        return
                    tep, nhan = viec
                    try:
                        self.da_thay.append(tep.read_bytes())
                        ma = tep.stem
                        # ABBYY lấy file khỏi in; vẫn mô phỏng được khi guard giữ tệp.
                        replace(tep, da_nhan / tep.name)
                    finally:
                        nhan.set()
                    if xu_ly:
                        xu_ly(d, ma, dung)
                    else:
                        (d["out"] / f"{ma}.docx").write_bytes(self.docx)
            except Exception as exc:
                self.loi_gia.append(exc)

        luong = threading.Thread(target=chay, daemon=True)
        luong.start()
        thay = patch.object(OCR.os, "replace", side_effect=doi)
        thay.start()

        def don():
            dung.set()
            hang.put(None)
            luong.join(CHO)
            self.assertFalse(luong.is_alive())
            self.assertEqual(self.loi_gia, [])
        self.addCleanup(thay.stop)
        self.addCleanup(don)
        return dung

    def _nen(self, ham):
        xong, ket_qua, loi = threading.Event(), [], []

        def chay():
            try:
                ket_qua.append(ham())
            except Exception as exc:
                loi.append(exc)
            finally:
                xong.set()
        luong = threading.Thread(target=chay, daemon=True)
        luong.start()

        def don():
            luong.join(CHO)
            self.assertFalse(luong.is_alive())
        self.addCleanup(don)
        return xong, ket_qua, loi

    def _sach(self):
        # Chỉ skip phần dọn; các kiểm tra kết quả/sổ trang của ca vẫn chạy tiếp.
        with self.subTest(kiem_tra="don_tep"):
            if self.giu_tep:
                self.skipTest("guard giữ tệp của runner kiểm thử")
            for ten in ("in", "out", "tam", "nhan"):
                with self.subTest(thu_muc=ten):
                    self.assertEqual(list((self.hot / ten).iterdir()), [])

    def _so(self):
        return self.du_lieu / "ocr_abbyy" / "so_trang.json"

    def _dat_so(self, ds):
        self._so().parent.mkdir(parents=True, exist_ok=True)
        self._so().write_text(json.dumps(ds), encoding="utf-8")

    def _trang(self):
        return sum(x[1] for x in json.loads(self._so().read_text(encoding="utf-8")))

    def _loi(self, ma, ham):
        with self.assertRaises(DataError) as bat:
            ham()
        self.assertEqual(bat.exception.code, ma)
        self.assertNotIn(str(self.goc), str(bat.exception))
        self.assertNotIn("Hợp đồng DEMO", str(bat.exception))
        return bat.exception

    def test_thanh_cong_tra_dung_docx_va_don_file(self):
        self._gia()
        self.assertEqual(self.bo_noi.ocr(self.pdf, "pdf"), self.docx)
        self.assertEqual(self.da_thay, [self.pdf])
        self._sach()
        self.assertEqual(self._trang(), 1)

    def test_dem_sha256_ben_vung_khong_ton_lai_trang_ke_ca_het_han_muc(self):
        self._gia()
        self.assertEqual(self.bo_noi.ocr(self.pdf, "pdf"), self.docx)
        tep = self.du_lieu / "ocr_hot_folder_m9" / (hashlib.sha256(self.pdf).hexdigest() + ".docx")
        self.assertEqual(tep.read_bytes(), self.docx)
        self._dat_so([[time.time(), 5000]])
        self.assertEqual(self._moi().ocr(self.pdf, ".PDF"), self.docx)
        self.assertEqual(len(self.da_thay), 1)
        self.assertEqual(self._trang(), 5000)
        self._sach()

    def test_khong_nhan_rut_file_va_hoan_trang(self):
        self._loi("M9_OCR_KHONG_NHAN", lambda: self._moi(cho_nhan=0.2).ocr(self.pdf, "pdf"))
        self._sach()
        self.assertEqual(self._trang(), 0)

    def test_qua_gio_sau_khi_abbyy_nhan_van_tinh_trang(self):
        self._gia(lambda d, ma, dung: None)
        self._loi("M9_OCR_QUA_GIO", lambda: self._moi(cho_toi_da=0.3).ocr(self.pdf, "pdf"))
        self._sach()
        self.assertEqual(self._trang(), 1)

    def test_qua_gio_truoc_khi_nhan_rut_file(self):
        self._loi("M9_OCR_QUA_GIO", lambda: self._moi(cho_toi_da=0.2).ocr(self.pdf, "pdf"))
        self._sach()
        self.assertEqual(self._trang(), 0)

    def test_qua_gio_don_ket_qua_den_muon_chi_dung_ma(self):
        da_ra, qua_gio = threading.Event(), threading.Event()
        hen = []

        class HenGia:
            def __init__(self, giay, ham, args):
                self.lam = lambda: ham(*args)
                hen.append(self)

            def start(self):
                qua_gio.set()  # Kết quả chỉ đến sau khi production hẹn dọn muộn.

        def xu_ly(d, ma, dung):
            if not qua_gio.wait(CHO):
                raise AssertionError("Chưa hẹn dọn kết quả DEMO đến muộn")
            (d["out"] / f"{ma}.docx").write_bytes(self.docx)
            (d["out"] / "nguoi_dung.demo").write_bytes(b"DEMO")
            da_ra.set()
        self._gia(xu_ly)
        with patch.object(OCR.threading, "Timer", HenGia):
            self._loi("M9_OCR_QUA_GIO", lambda: self._moi(cho_toi_da=0.2).ocr(self.pdf, "pdf"))
        self.assertTrue(da_ra.wait(CHO))
        self.assertEqual(len(hen), 1)
        hen[0].lam()
        self.assertEqual((self.hot / "out" / "nguoi_dung.demo").read_bytes(), b"DEMO")
        if self.giu_tep:
            self.assertEqual([p.read_bytes() for p in (self.hot / "out").glob("hd*.docx")], [self.docx])
        else:
            self.assertEqual([p.name for p in (self.hot / "out").iterdir()], ["nguoi_dung.demo"])
        self.assertEqual(self._trang(), 1)

    def test_huy_truoc_khi_gui_khong_tao_file(self):
        huy = threading.Event()
        huy.set()
        self._loi("M9_OCR_HUY", lambda: self.bo_noi.ocr(self.pdf, "pdf", huy=huy))
        self.assertFalse(self.hot.exists())
        self.assertFalse(self.du_lieu.exists())

    def test_huy_dang_cho_nhan_rut_file(self):
        huy, da_gui = threading.Event(), threading.Event()
        replace = os.replace

        def doi(src, dst):
            ket_qua = replace(src, dst)
            if Path(dst).parent == self.hot / "in":
                da_gui.set()
                self.assertTrue(huy.wait(CHO))
            return ket_qua

        with patch.object(OCR.os, "replace", side_effect=doi):
            xong, _, loi = self._nen(lambda: self.bo_noi.ocr(self.pdf, "pdf", huy=huy))
            self.addCleanup(huy.set)
            self.assertTrue(da_gui.wait(CHO))
            self.assertTrue(list((self.hot / "in").iterdir()))
            huy.set()
            self.assertTrue(xong.wait(CHO))
        self.assertEqual([x.code for x in loi], ["M9_OCR_HUY"])
        self.assertNotIn(str(self.goc), str(loi[0]))
        self._sach()
        self.assertEqual(self._trang(), 0)

    def test_huy_sau_nhan_giu_so_trang(self):
        huy = threading.Event()
        self._gia(lambda d, ma, dung: huy.set())
        self._loi("M9_OCR_HUY", lambda: self.bo_noi.ocr(self.pdf, "pdf", huy=huy))
        self._sach()
        self.assertEqual(self._trang(), 1)

    def test_docx_dang_ghi_do_du_dung_yen_van_chua_nhan(self):
        da_ghi, ghi_tiep, da_kiem = threading.Event(), threading.Event(), threading.Event()

        def xu_ly(d, ma, dung):
            with (d["out"] / f"{ma}.docx").open("wb") as f:
                nua = len(self.docx) // 2
                f.write(self.docx[:nua])
                f.flush()
                da_ghi.set()
                if not ghi_tiep.wait(CHO):
                    raise AssertionError("Chưa cho ghi tiếp DOCX DEMO")
                f.write(self.docx[nua:])
        self._gia(xu_ly)
        hop_le = OCR._docx_hop_le

        def kiem(raw):
            ket_qua = hop_le(raw)
            if not ket_qua:
                da_kiem.set()
            return ket_qua

        with patch.object(OCR, "_docx_hop_le", side_effect=kiem):
            xong, ket_qua, loi = self._nen(lambda: self.bo_noi.ocr(self.pdf, "pdf"))
            self.addCleanup(ghi_tiep.set)
            self.assertTrue(da_ghi.wait(CHO))
            self.assertTrue(da_kiem.wait(CHO))  # Đã kiểm sau on_dinh, DOCX dở vẫn bị từ chối.
            self.assertFalse(xong.is_set())
            self.assertEqual(len(list((self.hot / "out").iterdir())), 1)
            self.assertEqual(list((self.hot / "nhan").iterdir()), [])
            ghi_tiep.set()
            self.assertTrue(xong.wait(CHO))
        self.assertEqual(loi, [])
        self.assertEqual(ket_qua, [self.docx])
        self._sach()

    def test_docx_hop_le_nhung_kich_thuoc_con_doi_phai_cho_on_dinh(self):
        bat_dau, da_ghi, da_dong = threading.Event(), threading.Event(), threading.Event()
        lenh = Queue()
        dong_ho, so_lan = [0.0], [0]

        def xu_ly(d, ma, dung):
            with (d["out"] / f"{ma}.docx").open("wb") as f:
                f.write(self.docx)
                f.flush()
                bat_dau.set()
                while lenh.get() == "ghi":
                    f.write(b" ")
                    f.flush()
                    da_ghi.set()
            da_dong.set()
        self._gia(xu_ly)
        self.addCleanup(lenh.put, "dung")

        def nhip(giay):
            self.assertTrue(bat_dau.wait(CHO))
            if so_lan[0] < 6:
                self.assertEqual(list((self.hot / "nhan").iterdir()), [])
                da_ghi.clear()
                lenh.put("ghi")
                self.assertTrue(da_ghi.wait(CHO))
                so_lan[0] += 1
                if so_lan[0] == 6:
                    lenh.put("dung")
                    self.assertTrue(da_dong.wait(CHO))
            dong_ho[0] += giay

        # Thời gian logic: mỗi lần poll đã ghi xong mới tiến giờ, không đua scheduler.
        gia_gio = SimpleNamespace(time=time.time, strftime=time.strftime, monotonic=lambda: dong_ho[0], sleep=nhip)
        with patch.object(OCR, "time", gia_gio):
            self.assertEqual(self.bo_noi.ocr(self.pdf, "pdf"), self.docx + b" " * 6)
        self.assertEqual(so_lan[0], 6)
        self._sach()

    def test_vuot_han_muc_chan_truoc_khi_ghi_vao_in(self):
        self._dat_so([[time.time(), 4999]])
        self._gia()
        doi_trang = self.pdf + b"\n/Type /Page\n"
        thay = []
        replace = os.replace

        def doi(src, dst):
            if Path(dst).parent == self.hot / "in":
                thay.append(dst)
            return replace(src, dst)
        with patch("kho_tri_thuc.ha_tang.cong_ocr.os.replace", side_effect=doi):
            self._loi("M9_OCR_HET_HAN_MUC", lambda: self.bo_noi.ocr(doi_trang, "pdf"))
        self.assertEqual(thay, [])
        self.assertEqual(self.da_thay, [])
        self.assertEqual(self._trang(), 4999)
        self._sach()

    def test_cua_so_30_ngay_va_dem_pdf_khong_dem_pages(self):
        self._dat_so([[time.time() - 31 * 86400, 5000],
                      [time.time(), 4998]])
        self._gia()
        raw = self.pdf + b"\n/Type\n/Page\n/Type /Pages /Type /PageLabel"
        self.assertEqual(self.bo_noi.ocr(raw, "pdf"), self.docx)
        self.assertEqual(self._trang(), 5000)
        self._loi("M9_OCR_HET_HAN_MUC", lambda: self.bo_noi.ocr(b"anh DEMO", "png"))
        self.assertEqual(len(self.da_thay), 1)

    def test_cac_dinh_dang_anh_tinh_mot_trang(self):
        self._gia()
        for duoi in ("jpg", "jpeg", "png", "tif", "tiff"):
            with self.subTest(duoi=duoi):
                raw = ("anh DEMO " + duoi).encode() + b" /Type /Page /Type /Page"
                self.assertEqual(self.bo_noi.ocr(raw, duoi), self.docx)
        self.assertEqual(self._trang(), 5)
        self._sach()

    def test_dinh_dang_la_va_dau_vao_rong(self):
        for raw, duoi in ((self.pdf, "exe"), (self.pdf, "bmp"), (self.pdf, "../pdf"),
                          (self.pdf, None), (b"", "pdf"), ("DEMO", "pdf")):
            with self.subTest(duoi=duoi):
                self._loi("M9_OCR_DINH_DANG", lambda: self.bo_noi.ocr(raw, duoi))
        self.assertFalse(self.hot.exists())

    def test_loi_abbyy_khong_lo_duong_dan_hay_noi_dung_log(self):
        def xu_ly(d, ma, dung):
            (d["out"] / f"{ma}.log").write_text(
                f"{ma} ERROR {self.goc} Hợp đồng DEMO", encoding="utf-16")
        self._gia(xu_ly)
        self._loi("M9_OCR_LOI_ABBYY", lambda: self.bo_noi.ocr(self.pdf, "pdf"))
        self._sach()
        self.assertEqual(self._trang(), 1)

    def test_loi_he_thong_truoc_khi_gui_duoc_an_va_hoan_trang(self):
        replace = os.replace

        def doi(src, dst):
            if Path(dst).parent == self.hot / "in":
                raise OSError(f"{self.goc}: Hợp đồng DEMO")
            return replace(src, dst)
        with patch("kho_tri_thuc.ha_tang.cong_ocr.os.replace", side_effect=doi):
            loi = self._loi("M9_OCR_LOI_ABBYY", lambda: self.bo_noi.ocr(self.pdf, "pdf"))
        self.assertTrue(loi.__suppress_context__)
        self._sach()
        self.assertEqual(self._trang(), 0)

    def test_so_hong_khong_bi_tu_dat_lai_ve_khong(self):
        self._dat_so({"loi": "DEMO"})
        self._gia()
        self._loi("M9_OCR_LOI_ABBYY", lambda: self.bo_noi.ocr(self.pdf, "pdf"))
        self.assertEqual(self.da_thay, [])
        self.assertEqual(json.loads(self._so().read_text(encoding="utf-8")), {"loi": "DEMO"})

    def test_hai_instance_cung_goc_dung_mot_khoa_va_mot_ket_qua_dem(self):
        bo_hai = self._moi()
        self.assertIs(self.bo_noi._khoa, bo_hai._khoa)
        self._gia()
        xong1, kq1, loi1 = self._nen(lambda: self.bo_noi.ocr(self.pdf, "pdf"))
        xong2, kq2, loi2 = self._nen(lambda: bo_hai.ocr(self.pdf, "pdf"))
        self.assertTrue(xong1.wait(CHO))
        self.assertTrue(xong2.wait(CHO))
        self.assertEqual(loi1 + loi2, [])
        self.assertEqual(kq1 + kq2, [self.docx, self.docx])
        self.assertEqual(len(self.da_thay), 1)
        self.assertEqual(self._trang(), 1)

    def test_huy_khi_dang_cho_khoa(self):
        huy = threading.Event()
        self.bo_noi._khoa.acquire()
        try:
            xong, _, loi = self._nen(lambda: self._moi().ocr(self.pdf, "pdf", huy=huy))
            huy.set()
            self.assertTrue(xong.wait(CHO))
            self.assertEqual([x.code for x in loi], ["M9_OCR_HUY"])
        finally:
            self.bo_noi._khoa.release()
        self.assertFalse(self.hot.exists())

    def test_khong_don_file_khong_thuoc_ma(self):
        d = self.bo_noi.thu_muc()
        for ten in ("out", "tam", "nhan"):
            (d[ten] / "nguoi_dung.demo").write_bytes(b"DEMO giu nguyen")
        self._gia()
        self.assertEqual(self.bo_noi.ocr(self.pdf, "pdf"), self.docx)
        for ten in ("out", "tam", "nhan"):
            if not self.giu_tep:
                self.assertEqual([tep.name for tep in d[ten].iterdir()], ["nguoi_dung.demo"])
            self.assertEqual((d[ten] / "nguoi_dung.demo").read_bytes(), b"DEMO giu nguyen")


if __name__ == "__main__":
    unittest.main()
