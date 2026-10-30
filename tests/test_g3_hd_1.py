"""HD-1: DEMO trong RAM, không dịch vụ, không sửa fixture/test parser cũ."""

from dataclasses import replace
from decimal import Decimal, localcontext
import io
import json
from lzma import LZMAError
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import warnings
import zipfile

from kho_tri_thuc.engines.e_hoa_don import doc
from kho_tri_thuc.ha_tang.engine import TrangThaiEngine
from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.nguon import hoa_don_xml as parser
import test_g2_17 as schema_tests


ROOT = Path(__file__).resolve().parents[1]
XML_ID = "10000000-0000-4000-8000-000000000001"
DETAIL_ID = "10000000-0000-4000-8000-000000000002"
RAW = b"""<HDon><DLHDon><TTChung><PBan>2.1.0</PBan>
<KHMSHDon>01</KHMSHDon><KHHDon>DEMO</KHHDon><SHDon>000001</SHDon>
<NLap>2026-10-30</NLap><DVTTe>VND</DVTTe></TTChung><NDHDon>
<NBan><MST>0000000001</MST></NBan><NMua><MST>0000000002</MST></NMua>
<DSHHDVu><HHDVu><STT>007</STT><TChat>1</TChat><MHHDVu>0007</MHHDVu>
<THHDVu>DEMO</THHDVu><DVTinh>CAI</DVTinh><SLuong>1.250000</SLuong>
<DGia>80.008</DGia><ThTien>100.010000</ThTien><TSuat>10%</TSuat>
</HHDVu></DSHHDVu></NDHDon></DLHDon></HDon>"""
CTX = parser.InvoiceReadContext(
    source_instance="DEMO_HD_1", source_profile_ref=parser.PROFILE_REF,
    profile_document_sha256=parser.PROFILE_DOCUMENT_SHA256,
    profile_payload_sha256="a" * 64, profile_payload_binding="BOUND",
    identity_profile_ref=parser.IDENTITY_PROFILE_REF,
    company=parser.CompanyFact("0000000002", "PN_DEMO", "DEMO_MAP", 1, "DEMO_SCOPE"),
    expected_raw_ref=parser.XmlRawRef(sha256(RAW), len(RAW)),
)


def read(raw=RAW, context=CTX, **kwargs):
    return doc.doc_xml(raw, context, tep_xml_id=XML_ID,
                       chi_tiet_nguon_tep_id=DETAIL_ID, **kwargs)


def pack(*members):
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, raw in members:
                archive.writestr(zipfile.ZipInfo(name, (2026, 10, 30, 0, 0, 0)), raw)
    return buffer.getvalue()


class Hd1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_tests.BundleContractTest.setUpClass()
        cls.validator = schema_tests.BundleContractTest()

    def validate(self, value):
        self.validator.validate("urn:ktt:contract:hoa_don.v1", value)

    def codes(self, payload):
        return {i["ma"] for i in payload["van_de"]}

    def test_demo_schema_decimal_id_va_hash_context(self):
        with localcontext() as ctx:
            ctx.prec = 2
            result = read(revision=7, artifact_name="DEMO.xml")
        self.validate(result.hoa_don)
        self.assertEqual(result.trang_thai, TrangThaiEngine.XONG)
        self.assertEqual(result.hoa_don["revision"], 7)
        self.assertEqual(result.hoa_don["tep_xml_id"], XML_ID)
        self.assertEqual(result.hoa_don["chi_tiet_nguon_tep_id"], DETAIL_ID)
        self.assertEqual(result.hoa_don["nguon_tep_ids"], [XML_ID])
        header = result.hoa_don["dau_hoa_don"]
        self.assertEqual(header["so_hoa_don"], "000001")
        self.assertEqual(header["mau_so"], "01")
        self.assertEqual(header["ma_so_thue_ban"], "0000000001")
        self.assertEqual(result.hoa_don["dinh_danh_nguon"],
                         ["PN_DEMO", "MUA_VAO", "0000000001", "01", "DEMO", "1"])
        direct = parser.doc_hoa_don_xml(RAW, CTX, artifact_name="DEMO.xml")
        self.assertEqual(result.chi_tiet_nguon, direct)
        self.assertIs(result.context, CTX)
        self.assertEqual(result.hoa_don["ma_bam_noi_dung"], direct.semantic_digest)
        self.assertNotEqual(direct.semantic_digest, sha256(RAW))
        self.assertEqual(result.hoa_don["profile_payload_sha256"], "a" * 64)
        self.assertEqual(result.hoa_don["profile_document_sha256"], parser.PROFILE_DOCUMENT_SHA256)
        line = result.hoa_don["dong"][0]
        self.assertEqual(line["so_luong"], {"trang_thai": "EXACT", "gia_tri": "1.250000"})
        self.assertEqual(line["tien_chuan"], {"gia_tri": "100.010000", "don_vi_tien": "VND"})
        self.assertEqual(direct.lines[0].quantity.exact_value, Decimal("1.250000"))
        self.assertEqual(direct.lines[0].field("MHHDVu").duy_nhat.lexeme, "0007")
        self.assertEqual(direct.raw_ref.native_sha256, sha256(RAW))
        self.assertEqual(direct.raw_xml, RAW)
        self.assertEqual(json.loads(json.dumps(parser.ra_json(direct)))["raw_ref"]["native_sha256"], sha256(RAW))

    def test_loi_xml_namespace_va_path_deu_co_ma_va_dat_schema(self):
        for raw, code in ((b"<HDon>DEMO", "XML_MALFORMED"),
                          (b'<HDon xmlns="urn:DEMO"/>', "UNSUPPORTED_NAMESPACE"),
                          (b"<DEMO/>", "UNSUPPORTED_PATH")):
            with self.subTest(code=code):
                result = read(raw, context=None)
                self.validate(result.hoa_don)
                self.assertEqual(result.ma, code)
                self.assertEqual(result.trang_thai, TrangThaiEngine.LOI)
                self.assertIn(code, self.codes(result.hoa_don))
                self.assertEqual(result.chi_tiet_nguon.raw_xml, raw)

    def test_profile_la_context_thieu_va_mau_thuan_khong_duoc_tu_bu(self):
        for context, code in ((None, "CONTEXT_ABSENT"),
                              (replace(CTX, source_profile_ref="DEMO_LA"), "PROFILE_REF_MISMATCH"),
                              (replace(CTX, profile_document_sha256="b" * 64), "PROFILE_DOCUMENT_MISMATCH"),
                              (replace(CTX, identity_profile_ref="DEMO_LA"), "IDENTITY_PROFILE_UNSUPPORTED"),
                              (replace(CTX, expected_raw_ref=parser.XmlRawRef("b" * 64, len(RAW))), "RAW_REF_MISMATCH")):
            with self.subTest(code=code):
                result = read(context=context)
                self.validate(result.hoa_don)
                self.assertIs(result.context, context)
                self.assertIn(code, result.hoa_don["ly_do_ung_vien"])
                self.assertIsNone(result.hoa_don["dinh_danh_nguon"])
                self.assertIsNone(result.hoa_don["ma_bam_noi_dung"])
                if context is not None:
                    self.assertEqual(result.trang_thai, TrangThaiEngine.LOI)
                    self.assertEqual(result.ma, code)
        self.assertEqual(read(context=None).trang_thai, TrangThaiEngine.CHO)

    def test_context_mau_thuan_kem_thieu_van_la_loi(self):
        cases = (
            (replace(CTX, source_profile_ref="DEMO_LA", profile_document_sha256=None),
             "PROFILE_REF_MISMATCH", "PROFILE_DOCUMENT_NOT_BOUND"),
            (replace(CTX, expected_raw_ref=parser.XmlRawRef("b" * 64, len(RAW)), company=None),
             "RAW_REF_MISMATCH", "COMPANY_ABSENT"),
            (replace(CTX, profile_document_sha256="b" * 64, company=None),
             "PROFILE_DOCUMENT_MISMATCH", "COMPANY_ABSENT"),
            (replace(CTX, profile_payload_sha256=parser.PROFILE_DOCUMENT_SHA256, company=None),
             "PROFILE_PAYLOAD_CONFUSED", "COMPANY_ABSENT"),
            (replace(CTX, identity_profile_ref="DEMO_LA", company=None),
             "IDENTITY_PROFILE_UNSUPPORTED", "COMPANY_ABSENT"),
        )
        for context, invalid, missing in cases:
            with self.subTest(invalid=invalid, missing=missing):
                result = read(context=context)
                self.validate(result.hoa_don)
                self.assertIs(result.context, context)
                self.assertEqual(result.chi_tiet_nguon, parser.doc_hoa_don_xml(RAW, context))
                self.assertIn(invalid, result.hoa_don["ly_do_ung_vien"])
                self.assertIn(missing, result.hoa_don["ly_do_ung_vien"])
                self.assertIn(invalid, self.codes(result.hoa_don))
                self.assertIsNone(result.hoa_don["dinh_danh_nguon"])
                self.assertIsNone(result.hoa_don["ma_bam_noi_dung"])
                self.assertEqual((result.trang_thai, result.ma), (TrangThaiEngine.LOI, invalid))

    def test_context_chi_thieu_van_cho(self):
        for context, missing in (
            (replace(CTX, profile_document_sha256=None), "PROFILE_DOCUMENT_NOT_BOUND"),
            (replace(CTX, identity_profile_ref=None), "IDENTITY_PROFILE_ABSENT"),
            (replace(CTX, company=None), "COMPANY_ABSENT"),
        ):
            with self.subTest(missing=missing):
                result = read(context=context)
                self.validate(result.hoa_don)
                self.assertEqual((result.trang_thai, result.ma), (TrangThaiEngine.CHO, missing))

    def test_header_thieu_rong_trung_mixed_sai_ngay_tien_te_so(self):
        cases = (
            (b"<SHDon>000001</SHDon>", b"", "so_hoa_don"),
            (b"<SHDon>000001</SHDon>", b"<SHDon/>", "so_hoa_don"),
            (b"<SHDon>000001</SHDon>", b"<SHDon>000001</SHDon><SHDon>000002</SHDon>", "so_hoa_don"),
            (b"<KHHDon>DEMO</KHHDon>", b"<KHHDon>DEMO<x/>A</KHHDon>", "ky_hieu"),
            (b"<SHDon>000001</SHDon>", b"<SHDon>1e3</SHDon>", "so_hoa_don"),
            (b"2026-10-30", b"2026-02-30", "ngay_lap"),
            (b"<DVTTe>VND</DVTTe>", b"<DVTTe>vnd</DVTTe>", "don_vi_tien"),
            (b"<NBan><MST>0000000001</MST></NBan>", b"<NBan><MST>0000000001</MST></NBan><NBan/>", "ma_so_thue_ban"),
        )
        for old, new, field in cases:
            with self.subTest(field=field, new=new):
                result = read(RAW.replace(old, new), context=None)
                self.validate(result.hoa_don)
                self.assertIsNone(result.hoa_don["dau_hoa_don"][field])
                self.assertEqual(result.chi_tiet_nguon.raw_xml, RAW.replace(old, new))

    def test_so_luong_thieu_rong_sai_va_vuot_mien_khong_thanh_0(self):
        for replacement, state in ((b"", "ABSENT"), (b"<SLuong/>", "EMPTY"),
                                   (b"<SLuong>1e3</SLuong>", "INVALID"),
                                   (b"<SLuong>0.1234567</SLuong>", "OVER_DOMAIN")):
            with self.subTest(state=state):
                value = read(RAW.replace(b"<SLuong>1.250000</SLuong>", replacement)).hoa_don
                self.validate(value)
                self.assertEqual(value["dong"][0]["so_luong"], {"trang_thai": state, "gia_tri": None})

    def test_thue_suat_thieu_rong_trung_mixed_ky_hieu_dac_biet(self):
        for replacement, state, text in (
            (b"", "ABSENT", None), (b"<TSuat/>", "EMPTY", None),
            (b"<TSuat>KCT</TSuat>", "TEXT", "KCT"),
            (b"<TSuat>KKKNT</TSuat>", "TEXT", "KKKNT"),
            (b"<TSuat>10%</TSuat><TSuat>8%</TSuat>", "KHONG_HOP_LE", None),
            (b"<TSuat>10<x/>%</TSuat>", "KHONG_HOP_LE", None),
        ):
            with self.subTest(replacement=replacement):
                value = read(RAW.replace(b"<TSuat>10%</TSuat>", replacement)).hoa_don
                self.validate(value)
                self.assertEqual(value["dong"][0]["thue_suat"], {"trang_thai": state, "gia_tri_nguon": text})
                if state == "KHONG_HOP_LE":
                    self.assertIn("HOADON_TAX_RATE_AMBIGUOUS", self.codes(value))

    def test_tien_vuot_mien_giu_exact_khong_lam_tron(self):
        for text in ("1000000000000000000", "0.1234567"):
            with self.subTest(text=text):
                value = read(RAW.replace(b"100.010000", text.encode())).hoa_don
                self.validate(value)
                self.assertEqual(value["dong"][0]["thanh_tien"]["gia_tri"], text)
                self.assertIsNone(value["dong"][0]["tien_chuan"])
                self.assertIn("HOADON_MONEY_OVER_DOMAIN", self.codes(value))

    def test_tien_thieu_currency_va_so_0_dau(self):
        value = read(RAW.replace(b"<DVTTe>VND</DVTTe>", b"")).hoa_don
        self.validate(value)
        self.assertIsNone(value["dong"][0]["tien_chuan"])
        result = read(RAW.replace(b"100.010000", b"000100.010000"))
        value = result.hoa_don
        self.validate(value)
        self.assertEqual(value["dong"][0]["thanh_tien"]["gia_tri"], "100.010000")
        self.assertEqual(result.chi_tiet_nguon.lines[0].field("ThTien").duy_nhat.lexeme, "000100.010000")
        self.assertEqual(value["dong"][0]["tien_chuan"]["gia_tri"], "100.010000")

    def test_chiet_khau_duong_khong_doi_dau_hoac_bu_tong(self):
        value = read(RAW.replace(b"<TChat>1</TChat>", b"<TChat>3</TChat>")).hoa_don
        self.validate(value)
        self.assertEqual(value["dong"][0]["tinh_chat"], "DISCOUNT")
        self.assertEqual(value["dong"][0]["tien_chuan"]["gia_tri"], "100.010000")
        self.assertEqual(value["tong_tien"], [])

    def test_tong_thue_quan_he_giu_nguon_va_vi_tri_kct(self):
        raw = (ROOT / "tests/fixtures/m2_ban_ra.xml").read_bytes()
        result = read(raw, context=None)
        self.validate(result.hoa_don)
        totals = {x["ma"]: x for x in result.hoa_don["tong_tien"]}
        self.assertEqual(totals["truoc_thue"]["gia_tri_nguon"]["gia_tri"], "600.06")
        self.assertEqual(totals["thanh_toan"]["gia_tri_nguon"]["gia_tri"], "625.0625")
        self.assertEqual(totals["khong_chiu_thue"]["gia_tri_nguon"]["gia_tri"], "300.03")
        self.assertTrue(totals["khong_chiu_thue"]["dinh_vi"].endswith("TGTKCThue"))
        self.assertEqual(result.chi_tiet_nguon.relations.items[0].original_number, "000001")
        self.assertEqual(len(result.chi_tiet_nguon.money.tax_components), 3)
        self.assertEqual(result.hoa_don["trang_thai_thue"], "UNKNOWN")
        self.assertEqual(result.hoa_don["ghi_nhan_nghiep_vu"], "NOT_PERFORMED")
        without_explicit = raw.replace(b"<TGTKCThue>300.03</TGTKCThue>", b"")
        value = read(without_explicit, context=None).hoa_don
        self.validate(value)
        total = next(t for t in value["tong_tien"] if t["ma"] == "khong_chiu_thue")
        self.assertEqual(total["gia_tri_nguon"]["gia_tri"], "300.03")
        self.assertTrue(total["dinh_vi"].endswith("LTSuat[3]/ThTien"))

    def test_metadata_sai_co_ma_khong_tu_sinh_id(self):
        for kwargs, code in (({"tep_xml_id": "DEMO"}, "HOADON_ID_INVALID"),
                             ({"chi_tiet_nguon_tep_id": XML_ID}, "HOADON_FILE_REF_CONFLICT"),
                             ({"revision": True}, "HOADON_REVISION_INVALID"),
                             ({"revision": 0}, "HOADON_REVISION_INVALID")):
            with self.subTest(kwargs=kwargs), self.assertRaises(DataError) as caught:
                doc.doc_xml(RAW, CTX, **({"tep_xml_id": XML_ID, "chi_tiet_nguon_tep_id": DETAIL_ID} | kwargs))
            self.assertEqual(caught.exception.code, code)
        for raw in ("DEMO.xml", io.BytesIO(RAW)):
            with self.assertRaises(DataError) as caught:
                read(raw)
            self.assertEqual(caught.exception.code, "INPUT_NOT_BYTES")

    def test_zip_khong_them_vo_bao_cao_va_giu_context_tung_entry(self):
        raw = pack(("DEMO.xml", RAW))
        context = replace(CTX, expected_raw_ref=parser.XmlRawRef(sha256(RAW), len(RAW),
                          parser.MEDIA_XML, sha256(raw), 1, "DEMO.xml"))
        result = doc.doc_zip(raw, (context,), archive_name="DEMO.zip")
        self.assertIsInstance(result, parser.InvoiceZipReadResult)
        self.assertEqual(result, parser.doc_goi_hoa_don_zip(raw, (context,), archive_name="DEMO.zip"))
        self.assertEqual(result.artifact_coverage, "COMPLETE")
        self.assertEqual(result.period_completeness, "UNKNOWN")
        entry = result.entries[0]
        self.assertEqual(entry.raw_sha256, sha256(RAW))
        self.assertEqual(entry.result.raw_ref.container_sha256, sha256(raw))
        self.assertEqual(entry.result.semantic_digest, read().hoa_don["ma_bam_noi_dung"])
        self.validate(doc.chieu_hoa_don(entry.result, tep_xml_id=XML_ID, chi_tiet_nguon_tep_id=DETAIL_ID))

    def test_zip_hong_crc_trung_entry_partial_giu_du_ma_loi(self):
        malformed = doc.doc_zip(b"DEMO_ZIP_HONG")
        self.assertIn("ZIP_MALFORMED", {i.code for i in malformed.issues})
        self.assertEqual(malformed.artifact_coverage, "PARTIAL")
        duplicate = doc.doc_zip(pack(("DEMO.xml", RAW), ("DEMO.xml", b"<DEMO/>")))
        self.assertEqual([e.entry_ordinal for e in duplicate.entries], [1, 2])
        self.assertIn("ZIP_DUPLICATE_ENTRY_NAME", {i.code for i in duplicate.issues})
        self.assertEqual(duplicate.artifact_coverage, "PARTIAL")
        self.assertIn("UNSUPPORTED_PATH", {i.code for i in duplicate.entries[1].result.issues})
        raw = bytearray(pack(("DEMO.xml", RAW), ("DEMO2.xml", RAW)))
        name_len, extra_len = struct.unpack_from("<HH", raw, 26)
        raw[30 + name_len + extra_len] ^= 1  # CRC sai thực, không mock parser.
        result = doc.doc_zip(bytes(raw))
        self.assertEqual(result.artifact_coverage, "PARTIAL")
        self.assertEqual(result.entries[0].state, "READ_ERROR")
        self.assertIn("ZIP_MEMBER_READ_ERROR", {i.code for i in result.entries[0].issues})
        self.assertIsNotNone(result.entries[1].result)
        self.assertEqual(result.raw_zip, bytes(raw))

    def test_zip_ten_entry_co_thang_khong_chon_mst_tu_cau_truc_trung(self):
        duplicate = RAW.replace(b"</NBan>", b"</NBan><NBan/>")
        for name in ("DEMO.xml", "DEMO#1.xml", "DEMO#1#2.xml"):
            for raw, expected in ((duplicate, None), (RAW, "0000000001")):
                with self.subTest(name=name, duplicate=raw == duplicate):
                    entry = doc.doc_zip(pack((name, raw))).entries[0]
                    self.assertEqual(entry.entry_name, name)
                    self.assertEqual(entry.result.raw_xml, raw)
                    payload = doc.chieu_hoa_don(entry.result, tep_xml_id=XML_ID,
                                                chi_tiet_nguon_tep_id=DETAIL_ID)
                    self.validate(payload)
                    if raw == duplicate:
                        self.assertIn("STRUCTURE_DUPLICATE", self.codes(payload))
                        # Parser vẫn giữ occurrence; phép chiếu không được chọn nó.
                        field = next(f for f in entry.result.header_fields if f.name == "NBan/MST")
                        self.assertEqual(field.duy_nhat.lexeme, "0000000001")
                    self.assertEqual(payload["dau_hoa_don"]["ma_so_thue_mua"], "0000000002")
                    self.assertEqual(payload["dau_hoa_don"]["ma_so_thue_ban"], expected)

    def test_zip_context_khong_khop_va_trung_context_khong_duoc_ghep(self):
        raw = pack(("DEMO.xml", RAW))
        result = doc.doc_zip(raw, (CTX,))
        self.assertIn("CONTEXT_UNMATCHED", {i.code for i in result.issues})
        self.assertIsNone(result.entries[0].result.canonical_identity)
        context = replace(CTX, expected_raw_ref=parser.XmlRawRef(sha256(RAW), len(RAW),
                          parser.MEDIA_XML, sha256(raw), 1, "DEMO.xml"))
        result = doc.doc_zip(raw, (context, context))
        self.assertIn("CONTEXT_AMBIGUOUS", {i.code for i in result.issues})
        self.assertIsNone(result.entries[0].result.canonical_identity)

    def test_gioi_han_xml_zip_va_ngoai_le_lzma_co_ma(self):
        with patch.object(parser, "MAX_XML_BYTES", len(RAW) - 1):
            result = read()
            self.validate(result.hoa_don)
            self.assertEqual(result.ma, "XML_TOO_LARGE")
        with patch.object(doc, "MAX_ZIP_BYTES_CORE", 2), self.assertRaises(DataError) as caught:
            doc.doc_zip(b"DEMO")
        self.assertEqual(caught.exception.code, "ZIP_TOO_LARGE")
        with patch.object(doc, "doc_goi_hoa_don_zip", side_effect=LZMAError), self.assertRaises(DataError) as caught:
            doc.doc_zip(b"DEMO")
        self.assertEqual(caught.exception.code, "HOADON_ZIP_LZMA_HONG")
        with patch.object(doc, "doc_goi_hoa_don_zip", side_effect=RuntimeError("DEMO_BUG")):
            with self.assertRaisesRegex(RuntimeError, "DEMO_BUG"):
                doc.doc_zip(b"DEMO")

    def test_boc_khong_viet_lai_parser_khong_io_hay_dich_vu(self):
        with patch.object(doc, "doc_hoa_don_xml", wraps=parser.doc_hoa_don_xml) as xml_reader, \
             patch.object(doc, "doc_goi_hoa_don_zip", wraps=parser.doc_goi_hoa_don_zip) as zip_reader, \
             patch("socket.socket", side_effect=AssertionError("Cấm mạng")), \
             patch("subprocess.Popen", side_effect=AssertionError("Cấm tiến trình")), \
             patch("builtins.open", side_effect=AssertionError("Cấm đọc tệp")):
            read()
            doc.doc_zip(pack(("DEMO.xml", RAW)))
        xml_reader.assert_called_once_with(RAW, CTX, artifact_name=None)
        self.assertEqual(zip_reader.call_count, 1)


if __name__ == "__main__":
    unittest.main()
