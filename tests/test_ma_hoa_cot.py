"""MH-1: chỉ dữ liệu giả; DPAPI thật trên Windows, không server/CSDL.

Chạy: python -B -m unittest discover -s tests -p test_ma_hoa_cot.py -v
(cần src trong PYTHONPATH hoặc package đã được cài).
Mỗi ca dùng mkdtemp riêng, giữ lại thư mục giả theo lệnh không xóa file.
Không đọc/tạo khóa mặc định; không có fallback DPAPI giả.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import importlib
import io
import logging
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.giao_dien.v9b import bank_account
from kho_tri_thuc.ha_tang import ma_hoa_cot as mh


class _CaTam(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mh1-gia-"))
        self.cot = self.root / "cot"
        self.lookup = self.root / "tra-cuu"
        self.cot.mkdir()
        self.lookup.mkdir()
        self.source = mh.NguonKhoa(self.cot, self.lookup)

    def loi(self, code, callback):
        with self.assertRaises(mh.LoiMaHoaCot) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)
        self.assertNotIn(str(self.root), str(caught.exception))
        return caught.exception


class ChuanHoaTests(_CaTam):
    def test_import_va_khoi_tao_khong_doc_ghi_dia(self):
        with patch.object(Path, "open", side_effect=AssertionError("Cam I/O")):
            importlib.reload(mh)
            source = mh.NguonKhoa(self.cot, self.lookup)
            self.assertEqual(str(source), "<NguonKhoa: da che>")

    def test_stk_dung_lai_hop_dong_bank_account(self):
        for raw in ("00 1234-5678", "TK 0012345678, GD 12", "(0012).345_678"):
            with self.subTest(raw=raw):
                self.assertEqual(mh.chuan_hoa("STK", raw), bank_account(raw))
        self.assertEqual(mh.chuan_hoa("BANK_ACCOUNT", "00 1234-5678"), "0012345678")

    def test_cccd_mst_sdt_email(self):
        cases = (
            ("CCCD", " 001 234.567-890 ", "001234567890"),
            ("MST", " 0012345678-001 ", "0012345678001"),
            ("SĐT", " (090) 123-45.67 ", "0901234567"),
            ("PHONE", " +84 (90) 123-4567 ", "+84901234567"),
            ("email", " Ten.Nguoi+KeToan@EXAMPLE.COM ", "ten.nguoi+ketoan@example.com"),
        )
        for kind, raw, expected in cases:
            with self.subTest(kind=kind):
                self.assertEqual(mh.chuan_hoa(kind, raw), expected)
                self.assertEqual(mh.chuan_hoa(kind, expected), expected)

    def test_khong_tu_quy_doi_so_dien_thoai_quoc_te(self):
        self.assertNotEqual(mh.chuan_hoa("SDT", "0901234567"),
                            mh.chuan_hoa("SDT", "+84901234567"))

    def test_tu_choi_kieu_so_va_gia_tri_hong_khong_nuot_ky_tu(self):
        for kind, raw in (("CCCD", 123), ("MST", "001A234"), ("SDT", "09/0123"),
                          ("EMAIL", "a@@example.com"), ("EMAIL", "a b@example.com"),
                          ("EMAIL", "a\x00@example.com"), ("STK", ""), ("MST", "---")):
            with self.subTest(kind=kind):
                self.loi("MH_GIA_TRI", lambda: mh.chuan_hoa(kind, raw))
        self.loi("MH_LOAI_DU_LIEU", lambda: mh.chuan_hoa("CANARY_VALUE", "001234"))

    def test_che_hien_thi(self):
        cases = (
            ("STK", "0012345678", "******5678"),
            ("CCCD", "001234567890", "********7890"),
            ("EMAIL", "NguoiDung@Example.com", "n***g@example.com"),
            ("EMAIL", "ab@example.com", "***@example.com"),
            ("SDT", "0901234567", "090***567"),
            ("SDT", "1234", "***"),
            ("CCCD", "0012", "****"),
        )
        for kind, raw, expected in cases:
            with self.subTest(kind=kind):
                self.assertEqual(mh.che_hien_thi(kind, raw), expected)

    def test_thieu_khoa_tra_dung_ma_ca_hai_loai(self):
        self.loi("MH_THIEU_KHOA", lambda: self.source.tham_so_ma_hoa(1))
        self.loi("MH_THIEU_KHOA", lambda: self.source.tra_cuu("STK", "0012345678", 1))

    def test_phien_ban_khong_hop_le_khong_cham_dia(self):
        with patch.object(Path, "open", side_effect=AssertionError("Cam I/O")):
            for ver in (0, -1, True, 32768, "v01", "../v01", None):
                with self.subTest(ver=ver):
                    self.loi("MH_PHIEN_BAN", lambda: self.source.tham_so_ma_hoa(ver))
                    self.loi("MH_PHIEN_BAN", lambda: mh.tao_khoa_moi(self.cot, ver, loai="cot"))
        self.loi("MH_LOAI_KHOA", lambda: mh.tao_khoa_moi(self.cot, 1, loai="sai"))

    def test_sql_chi_chua_placeholder(self):
        self.assertEqual(mh.SQL_MA_HOA,
                         "SELECT pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256,compress-algo=0')")
        self.assertEqual(mh.SQL_GIAI_MA, "SELECT pgp_sym_decrypt(%s, %s)")

    def test_repr_khong_lo_duong_dan(self):
        self.assertNotIn(str(self.root), repr(self.source))
        self.assertNotIn(str(self.root), str(self.source))
        self.assertEqual(str(mh.LoiMaHoaCot("VALUE_CANARY")), "MH_LOI_NOI_BO")


@unittest.skipUnless(hasattr(ctypes, "WinDLL"), "NOT_RUN: cần Windows DPAPI thật")
class DPAPIThucTests(_CaTam):
    def tao_hai_khoa(self, cot_ver=1, lookup_ver=1):
        mh.tao_khoa_moi(self.cot, cot_ver, loai="cot")
        mh.tao_khoa_moi(self.lookup, lookup_ver, loai="tra-cuu")

    def test_tao_doc_lai_va_bind_dung_base64url(self):
        self.assertEqual(mh.tao_khoa_moi(self.cot, 1, loai="cot"), 1)
        params = self.source.tham_so_ma_hoa(1)
        fresh = mh.NguonKhoa(self.cot, self.lookup)
        self.assertTrue(params == fresh.tham_so_giai_ma(1), "Khóa đọc lại phải bằng nhau")
        self.assertEqual(params[1], 1)
        self.assertEqual(len(base64.urlsafe_b64decode(params[0])), 32)
        wrapped = (self.cot / "v01.dpapi").read_bytes()
        self.assertNotIn(params[0].encode("ascii"), wrapped)

    def test_tao_trung_tu_choi_va_khong_ghi_de(self):
        mh.tao_khoa_moi(self.cot, 1, loai="cot")
        before = (self.cot / "v01.dpapi").read_bytes()
        self.loi("MH_KHOA_DA_TON_TAI", lambda: mh.tao_khoa_moi(self.cot, 1, loai="cot"))
        self.assertTrue((self.cot / "v01.dpapi").read_bytes() == before)

    def test_hai_loai_khoa_doc_lap(self):
        self.tao_hai_khoa()
        self.assertTrue(self.source._doc("cot", 1)._bytes != self.source._doc("tra-cuu", 1)._bytes,
                        "Khóa cột và lookup phải độc lập")

    def test_cache_giu_khoa_khong_doc_lai(self):
        self.tao_hai_khoa()
        before = self.source.tham_so_ma_hoa(1)
        token = self.source.tra_cuu("STK", "0012345678", 1)
        with patch.object(Path, "open", side_effect=AssertionError("Cam doc lai")):
            self.assertTrue(before == self.source.tham_so_giai_ma(1))
            self.assertEqual(token, self.source.tra_cuu("STK", "0012345678", 1))

    def test_hmac_on_dinh_qua_doc_lai_va_chuan_hoa_tung_loai(self):
        self.tao_hai_khoa()
        fresh = mh.NguonKhoa(self.cot, self.lookup)
        cases = (
            ("STK", "00 1234-5678", "0012345678"),
            ("CCCD", "001 234.567-890", "001234567890"),
            ("MST", "0012345678-001", "0012345678001"),
            ("SĐT", "090 123-4567", "0901234567"),
            ("EMAIL", " USER@EXAMPLE.COM ", "user@example.com"),
        )
        for kind, raw, normalized in cases:
            with self.subTest(kind=kind):
                result = self.source.tra_cuu(kind, raw, 1)
                self.assertEqual(result, fresh.tra_cuu(kind, normalized, 1))
                self.assertRegex(result[0], r"^[0-9a-f]{64}$")
                self.assertEqual(result[1], 1)

    def test_hmac_giu_so_khong_dau_va_tach_mien_loai(self):
        self.tao_hai_khoa()
        token = self.source.tra_cuu("STK", "0012345678", 1)
        self.assertNotEqual(token, self.source.tra_cuu("STK", "12345678", 1))
        self.assertNotEqual(token, self.source.tra_cuu("CCCD", "0012345678", 1))
        self.assertEqual(token, self.source.tra_cuu("BANK_ACCOUNT", "0012345678", 1))

    def test_xoay_version_hai_loai_doc_lap(self):
        self.tao_hai_khoa(cot_ver=2, lookup_ver=3)
        self.assertEqual(self.source.tham_so_ma_hoa(2)[1], 2)
        self.assertEqual(self.source.tra_cuu("STK", "0012345678", 3)[1], 3)
        self.loi("MH_THIEU_KHOA", lambda: self.source.tham_so_ma_hoa(3))
        mh.tao_khoa_moi(self.lookup, 4, loai="tra-cuu")
        old = self.source.tra_cuu("STK", "0012345678", 3)[0]
        new = self.source.tra_cuu("STK", "0012345678", 4)[0]
        self.assertNotEqual(old, new)

    def test_tu_choi_doi_ten_phien_ban_va_copy_sai_loai(self):
        mh.tao_khoa_moi(self.cot, 1, loai="cot")
        wrapped = (self.cot / "v01.dpapi").read_bytes()
        (self.cot / "v02.dpapi").write_bytes(wrapped)
        (self.lookup / "v01.dpapi").write_bytes(wrapped)
        self.loi("MH_KHOA_KHONG_HOP_LE", lambda: self.source.tham_so_ma_hoa(2))
        self.loi("MH_KHOA_KHONG_HOP_LE", lambda: self.source.tra_cuu("STK", "0012345678", 1))

    def test_dpapi_hong_tra_ma_sach(self):
        (self.cot / "v01.dpapi").write_bytes(b"CANARY_FAKE_BROKEN_DPAPI")
        error = self.loi("MH_GIAI_DPAPI", lambda: self.source.tham_so_ma_hoa(1))
        self.assertNotIn("CANARY", repr(error))

    def test_tu_choi_khoa_khong_du_32_byte(self):
        wrapped = mh._dpapi(b"MH1\x00cot\x00\x00\x01too-short", boc=True)
        (self.cot / "v01.dpapi").write_bytes(wrapped)
        self.loi("MH_KHOA_KHONG_HOP_LE", lambda: self.source.tham_so_ma_hoa(1))

    def test_khong_tu_tao_thu_muc_khi_thieu(self):
        absent = self.root / "chua-cap-acl"
        self.loi("MH_GHI_KHOA", lambda: mh.tao_khoa_moi(absent, 1, loai="cot"))
        self.assertFalse(absent.exists())

    def test_canary_khong_lo_repr_loi_sql_va_log(self):
        canary = b"MH1_CANARY_FAKE_KEY_012345678901"
        self.assertEqual(len(canary), 32)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger()
        previous_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        try:
            with patch.object(mh.secrets, "token_bytes", return_value=canary) as random_bytes:
                self.tao_hai_khoa()
                self.assertEqual(random_bytes.call_count, 2)
                random_bytes.assert_called_with(32)
            params = self.source.tham_so_ma_hoa(1)
            expected = hmac.new(canary, b"STK\x000012345678", hashlib.sha256).hexdigest()
            self.assertEqual(self.source.tra_cuu("STK", "0012345678", 1), (expected, 1))
            self.assertTrue(base64.urlsafe_b64decode(params[0]) == canary)
            errors = [self.loi("MH_THIEU_KHOA", lambda: self.source.tham_so_ma_hoa(9))]
            errors.append(self.loi("MH_GIA_TRI", lambda: self.source.tra_cuu("CCCD", canary.decode(), 1)))
            errors.append(self.loi("MH_KHOA_DA_TON_TAI", lambda: mh.tao_khoa_moi(self.cot, 1, loai="cot")))
            # Lỗi OS có đường dẫn/giá trị phải bị chặn cả khi format traceback.
            with patch.object(Path, "open", side_effect=OSError(canary.decode())):
                errors.append(self.loi("MH_DOC_KHOA", lambda: self.source.tham_so_ma_hoa(8)))
                errors.append(self.loi("MH_GHI_KHOA", lambda: mh.tao_khoa_moi(self.cot, 8, loai="cot")))
            rendered = "\n".join([
                repr(self.source), str(self.source), repr(self.source._cache),
                mh.SQL_MA_HOA, mh.SQL_GIAI_MA, stream.getvalue(),
                *(repr(error) + str(error) + "".join(traceback.format_exception(error)) for error in errors),
            ])
            for representation in (canary.decode(), params[0], canary.hex()):
                self.assertTrue(representation not in rendered, "Canary bị lộ")
            self.assertEqual(stream.getvalue(), "")
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)


if __name__ == "__main__":
    unittest.main()
