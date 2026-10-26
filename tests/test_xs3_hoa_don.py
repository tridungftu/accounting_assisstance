"""XS-3d: test thuần, chỉ fixture DEMO/ZIP trong RAM; không ghi/xóa file.

Chạy được với CODEX_NO_DELETE_FILES=1; không DB, server, mạng hay M2/M3.
"""

from dataclasses import asdict, replace
from decimal import Decimal
import io
from lzma import LZMAError
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zipfile

from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import TrangThaiEngine, hash_du_lieu
from kho_tri_thuc.ha_tang.engine_hoa_don import (
    ANH_XA_MA_DATAERROR_HOA_DON, ANH_XA_NGOAI_LE_HOA_DON,
    DauVaoHoaDon, EngineHoaDon, dang_ky_engine_hoa_don,
)
from kho_tri_thuc.nguon.hoa_don_xml import (
    CompanyFact, IDENTITY_PROFILE_REF, InvoiceReadContext, MEDIA_XML,
    PROFILE_DOCUMENT_SHA256, PROFILE_REF, XmlRawRef,
    doc_goi_hoa_don_zip, doc_hoa_don_xml,
)
from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from test_xs3_engine import BoTestHopDongEngine, MauEngine, kiem_tra_mau_engine


_FIX = Path(__file__).resolve().parent / "fixtures"
_RAW = (_FIX / "m2_invoice_xml" / "inputs" / "G01-wrapped-positive.xml").read_bytes()
_BAN_RA = (_FIX / "m2_ban_ra.xml").read_bytes()
_CTX = InvoiceReadContext(
    source_instance="DEMO_XS3D", source_profile_ref=PROFILE_REF,
    profile_document_sha256=PROFILE_DOCUMENT_SHA256, identity_profile_ref=IDENTITY_PROFILE_REF,
    company=CompanyFact("DEMO_M2_COMPANY_A", "PN_DEMO_A", "DEMO_MAP", 1, "DEMO_SCOPE"),
)
_DA_DOC = "Đã đọc hóa đơn bằng bộ đọc hiện có."
_CHO = "Chờ ngữ cảnh đọc hóa đơn còn thiếu theo bộ đọc."
_LOI = "Bộ đọc không đọc được tệp hóa đơn trong phạm vi hỗ trợ."


def _goi(*members):
    """ZIP giả có timestamp cố định; tuyệt đối không giải nén ra đĩa."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, raw in members:
            archive.writestr(zipfile.ZipInfo(name, (2026, 10, 26, 0, 0, 0)), raw)
    return buffer.getvalue()


def _contexts(raw_zip, *members):
    return tuple(replace(_CTX, expected_raw_ref=XmlRawRef(
        sha256(raw), len(raw), MEDIA_XML, sha256(raw_zip), ordinal, name,
    )) for ordinal, (name, raw) in enumerate(members, 1))


class HopDongHoaDonTests(BoTestHopDongEngine, unittest.TestCase):
    cac_mau = (
        MauEngine(DauVaoHoaDon(_RAW, _CTX, "DEMO.xml"), TrangThaiEngine.XONG,
                  "DA_DOC_HOA_DON", _DA_DOC,
                  asdict(doc_hoa_don_xml(_RAW, _CTX, artifact_name="DEMO.xml"))),
        MauEngine(DauVaoHoaDon(_RAW), TrangThaiEngine.CHO, "CONTEXT_ABSENT", _CHO,
                  asdict(doc_hoa_don_xml(_RAW))),
        MauEngine(DauVaoHoaDon(b"<HDon>DEMO"), TrangThaiEngine.LOI, "XML_MALFORMED", _LOI,
                  asdict(doc_hoa_don_xml(b"<HDon>DEMO"))),
    )

    def tao_engine(self):
        return EngineHoaDon()


class HoaDonTests(unittest.TestCase):
    def setUp(self):
        self.engine = EngineHoaDon()

    def test_xml_bang_tung_truong_reader_giu_decimal_va_raw(self):
        for raw in (_RAW, _BAN_RA):
            with self.subTest(raw=sha256(raw)):
                direct = doc_hoa_don_xml(raw, _CTX, artifact_name="DEMO.xml")
                actual = self.engine.chay(DauVaoHoaDon(raw, _CTX, "DEMO.xml"))
                self.assertEqual(actual.trang_thai, TrangThaiEngine.XONG)
                self.assertEqual(actual.du_lieu, asdict(direct))
                self.assertEqual(actual.du_lieu["raw_xml"], raw)
                self.assertEqual(actual.du_lieu["raw_ref"]["native_sha256"], sha256(raw))
                number = next(f for f in actual.du_lieu["header_fields"] if f["name"] == "SHDon")
                self.assertEqual(number["occurrences"][0]["lexeme"], direct.header("SHDon").duy_nhat.lexeme)
                self.assertEqual(actual.du_lieu["issues"], tuple(asdict(i) for i in direct.issues))
                self.assertEqual(actual.du_lieu["lines"][0]["source_locator"], direct.lines[0].source_locator)
        self.assertEqual(actual.du_lieu["money"]["total_amount"]["exact_value"], Decimal("625.0625"))

    def test_loi_nghiep_vu_dong_van_xong_khong_suy_so(self):
        raw = _RAW.replace(b"<SLuong>10</SLuong>", b"<SLuong>DEMO_SAI</SLuong>")
        direct = doc_hoa_don_xml(raw, _CTX)
        self.assertTrue(direct.lines[0].issues)
        actual = self.engine.chay(DauVaoHoaDon(raw, _CTX))
        self.assertEqual(actual.trang_thai, TrangThaiEngine.XONG)
        self.assertEqual(actual.du_lieu, asdict(direct))
        self.assertIsNone(actual.du_lieu["lines"][0]["quantity"]["exact_value"])

    def test_thieu_context_reader_bao_ro_tra_cho(self):
        for field, reason in (("company", "COMPANY_ABSENT"),
                              ("identity_profile_ref", "IDENTITY_PROFILE_ABSENT"),
                              ("profile_document_sha256", "PROFILE_DOCUMENT_NOT_BOUND")):
            with self.subTest(field=field):
                ctx = replace(_CTX, **{field: None})
                direct = doc_hoa_don_xml(_RAW, ctx)
                self.assertIn(reason, direct.candidate_reasons)
                kiem_tra_mau_engine(self, self.engine, MauEngine(
                    DauVaoHoaDon(_RAW, ctx), TrangThaiEngine.CHO, reason, _CHO, asdict(direct)))

    def test_context_mau_thuan_khong_bi_sua_hay_gan_thieu(self):
        ctx = replace(_CTX, source_profile_ref="DEMO_SAI_PROFILE")
        direct = doc_hoa_don_xml(_RAW, ctx)
        self.assertIn("PROFILE_REF_MISMATCH", direct.candidate_reasons)
        result = self.engine.chay(DauVaoHoaDon(_RAW, ctx))
        self.assertEqual(result.trang_thai, TrangThaiEngine.XONG)
        self.assertEqual(result.du_lieu, asdict(direct))

    def test_zip_nhieu_tep_bang_reader_ca_coverage_locator(self):
        members = (("a.xml", _RAW), ("b.xml", _BAN_RA))
        raw = _goi(*members, ("DEMO.txt", b"DEMO"))
        contexts = _contexts(raw, *members)
        direct = doc_goi_hoa_don_zip(raw, contexts, archive_name="DEMO.zip")
        actual = kiem_tra_mau_engine(self, self.engine, MauEngine(
            DauVaoHoaDon(raw, contexts, "DEMO.zip", "ZIP"), TrangThaiEngine.XONG,
            "DA_DOC_HOA_DON", _DA_DOC, asdict(direct)))
        self.assertEqual(actual.du_lieu["artifact_coverage"], "COMPLETE")
        self.assertEqual(actual.du_lieu["raw_zip"], raw)
        for ordinal, entry in enumerate(actual.du_lieu["entries"][:2], 1):
            self.assertEqual(entry["entry_ordinal"], ordinal)
            self.assertEqual(entry["result"]["raw_ref"]["container_sha256"], sha256(raw))
            self.assertEqual(entry["result"]["lines"][0]["source_locator"],
                             direct.entries[ordinal - 1].result.lines[0].source_locator)
            self.assertTrue(entry["result"]["lines"][0]["issues"][0]["locator"].startswith(
                f"zip:{sha256(raw)}!{ordinal}:"))

    def test_zip_thieu_context_tra_cho_giu_coverage(self):
        raw = _goi(("DEMO.xml", _RAW))
        actual = self.engine.chay(DauVaoHoaDon(raw, dinh_dang="ZIP"))
        self.assertEqual((actual.trang_thai, actual.ma), (TrangThaiEngine.CHO, "CONTEXT_ABSENT"))
        self.assertEqual(actual.du_lieu, asdict(doc_goi_hoa_don_zip(raw)))
        self.assertEqual(actual.du_lieu["artifact_coverage"], "COMPLETE")

    def test_zip_loi_uu_tien_hon_cho_va_giu_ket_qua_phan_doc_duoc(self):
        raw = _goi(("a.xml", _RAW), ("hong.xml", b"<HDon>DEMO"))
        actual = self.engine.chay(DauVaoHoaDon(raw, dinh_dang="ZIP"))
        self.assertEqual((actual.trang_thai, actual.ma), (TrangThaiEngine.LOI, "XML_MALFORMED"))
        self.assertEqual(actual.du_lieu, asdict(doc_goi_hoa_don_zip(raw)))
        self.assertEqual(actual.du_lieu["artifact_coverage"], "PARTIAL")
        self.assertEqual(len(actual.du_lieu["entries"]), 2)

    def test_zip_hong_va_xml_ngoai_profile_tra_loi_nguyen_ket_qua(self):
        for raw, format_, code in ((b"PK_DEMO_HONG", "ZIP", "ZIP_MALFORMED"),
                                   (b"<DEMO/>", "XML", "UNSUPPORTED_PATH"),
                                   (b'<!DOCTYPE HDon><HDon/>', "XML", "XML_DOCTYPE_UNSUPPORTED")):
            with self.subTest(format_=format_, code=code):
                actual = self.engine.chay(DauVaoHoaDon(raw, dinh_dang=format_))
                direct = doc_goi_hoa_don_zip(raw) if format_ == "ZIP" else doc_hoa_don_xml(raw)
                self.assertEqual((actual.trang_thai, actual.ma), (TrangThaiEngine.LOI, code))
                self.assertEqual(actual.du_lieu, asdict(direct))

    def test_zip_member_crc_hong_giu_read_error(self):
        raw = _goi(("DEMO.xml", _RAW)).replace(b"<HDon>", b"<XDon>", 1)
        direct = doc_goi_hoa_don_zip(raw)
        self.assertEqual(direct.entries[0].state, "READ_ERROR")
        actual = self.engine.chay(DauVaoHoaDon(raw, dinh_dang="ZIP"))
        self.assertEqual((actual.trang_thai, actual.ma),
                         (TrangThaiEngine.LOI, "ZIP_MEMBER_READ_ERROR"))
        self.assertEqual(actual.du_lieu, asdict(direct))

    def test_ngoai_le_giu_loai_goc_khong_lo_noi_dung(self):
        cac_loi = {
            LZMAError: (LZMAError("DEMO_NOI_DUNG_HOA_DON"), "HOADON_ZIP_LZMA_HONG",
                        "Dữ liệu nén trong gói hóa đơn không hợp lệ."),
        }
        self.assertEqual(set(ANH_XA_NGOAI_LE_HOA_DON), set(cac_loi))
        for format_, reader in (("XML", "doc_hoa_don_xml"), ("ZIP", "doc_goi_hoa_don_zip")):
            for loai, (exc, code, ly_do) in cac_loi.items():
                with self.subTest(format_=format_, code=code), patch(
                    "kho_tri_thuc.ha_tang.engine_hoa_don." + reader, side_effect=exc
                ):
                    self.assertEqual(ANH_XA_NGOAI_LE_HOA_DON[loai],
                                     (TrangThaiEngine.LOI, code, ly_do))
                    actual = self.engine.chay(DauVaoHoaDon(_RAW, dinh_dang=format_))
                    self.assertEqual((actual.trang_thai, actual.ma), (TrangThaiEngine.LOI, code))
                    self.assertEqual(actual.ly_do, ly_do)
                    self.assertIsNone(actual.du_lieu)
                    self.assertNotIn("DEMO_NOI_DUNG_HOA_DON", repr(actual))

    def test_moi_ma_dataerror_dau_vao_duoc_anh_xa_khong_lo_noi_dung(self):
        self.assertEqual(set(ANH_XA_MA_DATAERROR_HOA_DON),
                         {"INPUT_NOT_BYTES", "INPUT_NAME_TYPE", "CONTEXT_FIELD_TYPE"})
        for format_, reader in (("XML", "doc_hoa_don_xml"), ("ZIP", "doc_goi_hoa_don_zip")):
            for code, mapping in ANH_XA_MA_DATAERROR_HOA_DON.items():
                exc = DataError(code, "DEMO_NOI_DUNG_HOA_DON", "DEMO_LOCATOR")
                with self.subTest(format_=format_, code=code), patch(
                    "kho_tri_thuc.ha_tang.engine_hoa_don." + reader, side_effect=exc
                ):
                    self.assertEqual(mapping, (TrangThaiEngine.LOI, code,
                                               "Đầu vào bộ đọc hóa đơn chưa hợp lệ."))
                    actual = self.engine.chay(DauVaoHoaDon(_RAW, dinh_dang=format_))
                    self.assertEqual((actual.trang_thai, actual.ma, actual.ly_do), mapping)
                    self.assertIsNone(actual.du_lieu)
                    self.assertNotIn("DEMO_NOI_DUNG_HOA_DON", repr(actual))
                    self.assertNotIn("DEMO_LOCATOR", repr(actual))

    def test_moi_ma_dataerror_dau_vao_thuc_tu_reader(self):
        for format_, raw in (("XML", _RAW), ("ZIP", _goi(("DEMO.xml", _RAW)))):
            for code, data in (
                ("INPUT_NOT_BYTES", DauVaoHoaDon("DEMO", dinh_dang=format_)),
                ("INPUT_NAME_TYPE", DauVaoHoaDon(raw, ten_tep=123, dinh_dang=format_)),
                ("CONTEXT_FIELD_TYPE", DauVaoHoaDon(raw, context="DEMO", dinh_dang=format_)),
            ):
                with self.subTest(format_=format_, code=code):
                    with self.assertRaises(DataError) as caught:
                        if format_ == "XML":
                            doc_hoa_don_xml(data.raw, data.context, artifact_name=data.ten_tep)
                        else:
                            doc_goi_hoa_don_zip(data.raw, () if data.context is None else data.context,
                                              archive_name=data.ten_tep)
                    self.assertEqual(caught.exception.code, code)
                    actual = self.engine.chay(data)
                    self.assertEqual((actual.trang_thai, actual.ma, actual.ly_do),
                                     ANH_XA_MA_DATAERROR_HOA_DON[code])
                    self.assertIsNone(actual.du_lieu)

    def test_dataerror_bat_bien_va_ma_la_noi_len_nguyen_ven(self):
        for format_, reader in (("XML", "doc_hoa_don_xml"), ("ZIP", "doc_goi_hoa_don_zip")):
            for code in ("DECIMAL_INVARIANT", "FIELD_VALUE_INVARIANT", "RESULT_INVARIANT",
                         "ISSUE_SEVERITY", "DEMO_INVARIANT", "DEMO_MA_LA",
                         "CONTEXT_FORBIDDEN_FIELD", "CONTEXT_UNKNOWN_FIELD",
                         "AMBIGUOUS_DATE", "INVALID_DATE"):
                exc = DataError(code, "DEMO_LOI_NOI_BO", "DEMO_LOCATOR")
                with self.subTest(format_=format_, code=code), patch(
                    "kho_tri_thuc.ha_tang.engine_hoa_don." + reader, side_effect=exc
                ), self.assertRaises(DataError) as caught:
                    self.engine.chay(DauVaoHoaDon(_RAW, dinh_dang=format_))
                self.assertIs(caught.exception, exc)
                self.assertEqual(caught.exception.locator, "DEMO_LOCATOR")

    def test_ngoai_le_ngoai_bang_noi_len(self):
        class LoiDataChuaBiet(DataError):
            pass

        for format_, reader in (("XML", "doc_hoa_don_xml"), ("ZIP", "doc_goi_hoa_don_zip")):
            for exc in (TypeError("DEMO_LOI_LAP_TRINH"), AttributeError("DEMO_LOI_LAP_TRINH"),
                        RuntimeError("DEMO_NOI_DUNG_HOA_DON"), ValueError("DEMO_LOI_LAP_TRINH"),
                        LoiDataChuaBiet("DEMO_CHUA_BIET", "DEMO_NOI_DUNG_HOA_DON"),
                        LoiDataChuaBiet("INPUT_NOT_BYTES", "DEMO_NOI_DUNG_HOA_DON")):
                with self.subTest(format_=format_, loai=type(exc)), patch(
                    "kho_tri_thuc.ha_tang.engine_hoa_don." + reader, side_effect=exc
                ), self.assertRaises(type(exc)) as caught:
                    self.engine.chay(DauVaoHoaDon(_RAW, dinh_dang=format_))
                self.assertIs(caught.exception, exc)

    def test_zip_lzma_hong_anh_xa_loi_thuc_tu_reader(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_LZMA) as archive:
            archive.writestr("DEMO.xml", _RAW)
        raw = bytearray(buffer.getvalue())
        name_len, extra_len = struct.unpack_from("<HH", raw, 26)
        data_offset = 30 + name_len + extra_len
        props_len, = struct.unpack_from("<H", raw, data_offset + 2)
        # Byte đầu luồng LZMA phải bằng 0; làm hỏng dữ liệu sau phần properties.
        raw[data_offset + 4 + props_len] = 0xff
        raw = bytes(raw)
        with self.assertRaises(LZMAError):
            doc_goi_hoa_don_zip(raw)
        actual = self.engine.chay(DauVaoHoaDon(raw, dinh_dang="ZIP"))
        self.assertEqual((actual.trang_thai, actual.ma),
                         (TrangThaiEngine.LOI, "HOADON_ZIP_LZMA_HONG"))
        self.assertIsNone(actual.du_lieu)

    def test_context_sai_kieu_giu_dataerror(self):
        actual = self.engine.chay(DauVaoHoaDon(_RAW, ()))
        self.assertEqual(actual.ma, "CONTEXT_FIELD_TYPE")
        self.assertEqual(actual.trang_thai, TrangThaiEngine.LOI)
        self.assertIsNone(actual.du_lieu)

    def test_hash_lap_lai_va_doi_dung_mot_byte(self):
        changed = _RAW.replace(b"<SHDon>000001", b"<SHDon>000002")
        self.assertEqual(sum(a != b for a, b in zip(_RAW, changed)), 1)
        a = self.engine.chay(DauVaoHoaDon(_RAW, _CTX))
        b = self.engine.chay(DauVaoHoaDon(_RAW, _CTX))
        c = self.engine.chay(DauVaoHoaDon(changed, _CTX))
        self.assertEqual(a.du_lieu, b.du_lieu)
        for field in ("hash_vao", "hash_ra"):
            self.assertEqual(getattr(a.bang_chung, field), getattr(b.bang_chung, field))
            self.assertNotEqual(getattr(a.bang_chung, field), getattr(c.bang_chung, field))
        self.assertEqual(a.bang_chung.hash_vao, hash_du_lieu(DauVaoHoaDon(_RAW, _CTX)))
        d = self.engine.chay(DauVaoHoaDon(_RAW, replace(_CTX, source_instance="DEMO_KHAC")))
        self.assertNotEqual(a.bang_chung.hash_vao, d.bang_chung.hash_vao)

    def test_dang_ky_rieng_va_trung_bi_tu_choi(self):
        registry = DanhBaEngine()
        engine = dang_ky_engine_hoa_don(registry)
        self.assertIs(registry.tra_cuu("E-HOADON", "v1"), engine)
        self.assertEqual(registry.liet_ke(), (engine.khai_bao,))
        with self.assertRaises(ValueError):
            dang_ky_engine_hoa_don(registry)
        with self.assertRaises(ValueError):
            registry.dang_ky(EngineHoaDon(), phien_ban_moi=True)
        self.assertEqual(registry.liet_ke(), (engine.khai_bao,))

    def test_dinh_dang_khong_ho_tro_khong_goi_reader(self):
        with patch("kho_tri_thuc.ha_tang.engine_hoa_don.doc_hoa_don_xml") as reader:
            actual = self.engine.chay(DauVaoHoaDon(_RAW, dinh_dang="PDF"))
        reader.assert_not_called()
        self.assertEqual((actual.trang_thai, actual.ma),
                         (TrangThaiEngine.LOI, "DINH_DANG_KHONG_HO_TRO"))


if __name__ == "__main__":
    unittest.main()
