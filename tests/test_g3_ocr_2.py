"""OCR-2: HotFolder giả, DOCX DEMO, không dịch vụ/COM/AI hoặc xóa tệp.

Test thuần dùng seam; nhóm DocxNguonTests chạy nguyên parser khi package
mask_ocr có trên PYTHONPATH cùng dependency sẵn có. Không cài thư viện.
"""

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from kho_tri_thuc.engines.e_ocr import van_ban
from kho_tri_thuc.ha_tang.cong_ocr import CongOCR
from kho_tri_thuc.ha_tang.primitives import DataError
import test_g2_17 as contract_tests

try:
    from mask_ocr import extraction, layout
except ImportError:
    extraction = layout = None

ROOT = Path(__file__).resolve().parents[1]
TEP = "10000000-0000-4000-8000-000000000001"
DOCX = "10000000-0000-4000-8000-000000000002"
PHAN_HOI = "10000000-0000-4000-8000-000000000003"
RAW = b"%PDF-1.4 DEMO OCR-2"
TEXT = "DEMO số 00007, giá trị 0 VND, ngày 31/10/2026."
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def tham_chieu(**changes):
    ref = dict(contract="tham_chieu_tep.v1", phien_ban="1.0.0", tep_id=TEP,
               ten_tep="DEMO.pdf", mime="application/pdf", kich_thuoc=len(RAW),
               sha256=hashlib.sha256(RAW).hexdigest(), het_han_luc=None)
    ref.update(changes)
    return ref


def tao_docx(body=None, *, image=False, header=False):
    body = body if body is not None else f"<w:p><w:r><w:t>{TEXT}</w:t></w:r></w:p>"
    if image:
        body += '<w:p><w:r><a:blip r:embed="img1"/></w:r></w:p>'
    xml = (f'<w:document xmlns:w="{W}" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           f'<w:body>{body}<w:sectPr/></w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)
        if image:
            z.writestr("word/_rels/document.xml.rels",
                       '<Relationships><Relationship Id="img1" Target="media/demo.png"/></Relationships>')
            # Không cần ảnh hợp lệ: byte này tuyệt đối không được gửi OCR.
            z.writestr("word/media/demo.png", b"DEMO embedded image")
        if header:
            z.writestr("word/header1.xml", f'<w:hdr xmlns:w="{W}"><w:p><w:r>'
                       '<w:t>DEMO đầu trang</w:t></w:r></w:p></w:hdr>')
    return buf.getvalue()


class _AdapterFixture:
    @classmethod
    def setUpClass(cls):
        contract_tests.BundleContractTest.setUpClass()
        cls.core = contract_tests.BundleContractTest()
        cls.manifest = json.loads((ROOT / "src/kho_tri_thuc/engines/e_ocr/engine.json").read_text("utf-8"))

    def setUp(self):
        self.docx = tao_docx()
        self.cong = Mock(spec=CongOCR)
        self.cong.ocr.return_value = self.docx
        self.legacy = SimpleNamespace(text=TEXT, warnings=["DEMO cần soát"], ocr_pages=0)
        self.source_layout = {"number": 1, "width": 595.3, "height": 841.9,
                              "units": [{"id": "p1-u0", "text": TEXT,
                                         "bbox": [0, 0, 515, 14], "source": "native"}]}
        self.extract = Mock(return_value=self.legacy)
        self.layout = Mock(return_value=self.source_layout)

    def run_adapter(self, ref=None, **changes):
        args = dict(cong_ocr=self.cong, tep_docx_id=DOCX,
                    phan_hoi_nguon_tep_id=PHAN_HOI, revision=7,
                    extract_docx=self.extract, word_layout=self.layout)
        args.update(changes)
        with patch.object(socket, "socket", side_effect=AssertionError("OCR-2 cấm mạng")), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("OCR-2 cấm tiến trình ngoài")):
            return van_ban.trich_van_ban(RAW, tham_chieu() if ref is None else ref, **args)


class OCR2Tests(_AdapterFixture, unittest.TestCase):
    def test_hotfolder_gia_sang_contract_hash_revision_nguon(self):
        ref = tham_chieu()
        result = self.run_adapter(ref)
        self.core.validate("urn:ktt:contract:van_ban_tai_lieu.v1", result.van_ban)
        self.cong.ocr.assert_called_once_with(RAW, "pdf", huy=None)
        self.assertEqual(result.docx, self.docx)
        self.assertEqual(result.van_ban["van_ban"], TEXT)
        self.assertEqual(result.van_ban["revision"], 7)
        self.assertEqual(result.van_ban["nguon_tep_ids"], [TEP, DOCX])
        self.assertEqual(result.van_ban["phan_hoi_nguon_tep_id"], PHAN_HOI)
        source = result.phan_hoi_nguon
        self.assertEqual(source["tham_chieu_tep"], ref)
        self.assertEqual(source["docx"]["sha256"], hashlib.sha256(self.docx).hexdigest())
        self.assertEqual(source["docx"]["kich_thuoc"], len(self.docx))
        self.assertEqual(source["revision"], 7)
        self.assertEqual(source["khoi"], [{"ma_nguon": "p1-u0", "van_ban": TEXT,
                         "vi_tri": {"tep_id": DOCX, "dinh_vi": "word_layout/p1-u0"}}])
        json.dumps(source, ensure_ascii=False, allow_nan=False)

    def test_khong_dung_trang_va_bbox_docx_gia_khong_tu_duyet(self):
        result = self.run_adapter()
        self.assertEqual(result.van_ban["trang"], [])
        self.assertIn(van_ban.CANH_BAO_TRANG, result.van_ban["canh_bao"])
        self.assertEqual(result.van_ban["soat_ocr"], "can_soat")
        self.assertIs(result.van_ban["da_doi_chieu"], False)
        self.assertNotIn("da_duyet", result.van_ban)
        vi_tri = result.phan_hoi_nguon["khoi"][0]["vi_tri"]
        self.assertNotIn("trang", vi_tri)
        self.assertNotIn("bbox", vi_tri)
        self.assertNotIn("khung_toa_do", vi_tri)
        self.assertEqual(result.phan_hoi_nguon["layout"], self.source_layout)

    def test_chi_anh_nhung_khong_goi_reader_va_giu_canh_bao(self):
        self.legacy.ocr_pages = 1
        result = self.run_adapter()
        reader = self.extract.call_args.kwargs["image_reader"]
        self.assertEqual(reader(b"DEMO image"), "")
        self.layout.assert_called_once_with(self.docx, self.legacy, embedded_pages=[])
        self.assertTrue(any("chưa được nhận dạng" in w for w in result.van_ban["canh_bao"]))

    def test_snapshot_khong_doi_tham_chieu_va_layout_nguon(self):
        ref = tham_chieu()
        result = self.run_adapter(ref)
        result.phan_hoi_nguon["tham_chieu_tep"]["sha256"] = "DEMO changed"
        result.phan_hoi_nguon["layout"]["units"].clear()
        self.assertEqual(ref, tham_chieu())
        self.assertEqual(len(self.source_layout["units"]), 1)
        self.assertNotIn(TEXT, repr(result))

    def test_metadata_sai_bi_chan_truoc_gui_hotfolder(self):
        cases = [dict(sha256="0" * 64), dict(kich_thuoc=len(RAW) + 1),
                 dict(kich_thuoc=True), dict(tep_id="DEMO-invalid"), dict(phien_ban="2.0.0"),
                 dict(mime="image/tiff"), dict(mime=[]), dict(ten_tep="../DEMO.pdf"),
                 dict(ten_tep="DEMO\n.pdf"), dict(het_han_luc="2020-01-01T00:00:00Z"),
                 dict(het_han_luc="2026-02-30T00:00:00Z"), dict(url="DEMO"),
                 dict(contract="DEMO")]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                self.run_adapter(tham_chieu(**changes))
        for rev in (0, -1, True, "7"):
            with self.subTest(revision=rev), self.assertRaises(DataError):
                self.run_adapter(revision=rev)
        for changes in (dict(tep_docx_id=TEP), dict(phan_hoi_nguon_tep_id=DOCX),
                        dict(phan_hoi_nguon_tep_id="DEMO")):
            with self.subTest(changes=changes), self.assertRaises(DataError):
                self.run_adapter(**changes)
        self.cong.ocr.assert_not_called()

    def test_bytes_rong_qua_lon_va_tham_chieu_thieu_truong_bi_chan(self):
        for raw in (b"", b"D" * (van_ban.MAX_BYTES + 1), "DEMO"):
            with self.subTest(size=len(raw)), self.assertRaises(DataError):
                van_ban.trich_van_ban(raw, tham_chieu(), cong_ocr=self.cong,
                                     tep_docx_id=DOCX, phan_hoi_nguon_tep_id=PHAN_HOI,
                                     extract_docx=self.extract, word_layout=self.layout)
        for field in tham_chieu():
            ref = tham_chieu()
            ref.pop(field)
            with self.subTest(field=field), self.assertRaises(DataError):
                self.run_adapter(ref)
        self.cong.ocr.assert_not_called()

    def test_huy_truoc_va_sau_hotfolder_khong_tu_gui_lai(self):
        huy = threading.Event()
        huy.set()
        with self.assertRaisesRegex(DataError, "Đã hủy"):
            self.run_adapter(huy=huy)
        self.cong.ocr.assert_not_called()
        huy.clear()
        def convert(*args, **kwargs):
            huy.set()
            return self.docx
        self.cong.ocr.side_effect = convert
        with self.assertRaisesRegex(DataError, "Đã hủy"):
            self.run_adapter(huy=huy)
        self.cong.ocr.assert_called_once_with(RAW, "pdf", huy=huy)
        self.extract.assert_not_called()

    def test_loi_cong_giu_nguyen_khong_retry_hoan_han_muc(self):
        error = DataError("OCR_HET_HAN_MUC", "DEMO hết hạn mức")
        self.cong.ocr.side_effect = error
        with self.assertRaises(DataError) as caught:
            self.run_adapter()
        self.assertIs(caught.exception, error)
        self.cong.ocr.assert_called_once()
        self.extract.assert_not_called()

    def test_loi_docx_khong_lo_du_lieu_va_khong_retry(self):
        self.extract.side_effect = ValueError("DEMO nội dung và đường dẫn nội bộ")
        with self.assertRaises(DataError) as caught:
            self.run_adapter()
        self.assertEqual(caught.exception.code, "OCR_DOCX_INVALID")
        self.assertNotIn("nội bộ", str(caught.exception))
        self.cong.ocr.assert_called_once()

    def test_khoi_trung_va_phan_hoi_parser_sai_bi_chan(self):
        self.source_layout["units"].append(deepcopy(self.source_layout["units"][0]))
        with self.assertRaises(DataError):
            self.run_adapter()
        self.source_layout["units"].pop()
        self.legacy.text = None
        with self.assertRaises(DataError):
            self.run_adapter()

    def test_cac_mime_cong_bo_dung_duoi_cong(self):
        for mime, duoi in van_ban.MIME_DUOI.items():
            with self.subTest(mime=mime):
                self.cong.reset_mock()
                self.run_adapter(tham_chieu(mime=mime))
                self.cong.ocr.assert_called_once_with(RAW, duoi, huy=None)

    def test_manifest_chi_capability_da_co_adapter_va_schema_dung(self):
        self.core.validate("urn:ktt:manifest:engine.v1", self.manifest)
        cap, = self.manifest["capability"]
        self.assertEqual(cap["ma"], "ocr.trich_van_ban@1")
        self.assertEqual(cap["dau_vao"], "tham_chieu_tep.v1")
        self.assertEqual(cap["dau_ra"], "van_ban_tai_lieu.v1")
        self.assertEqual(set(cap["mime"]), set(van_ban.MIME_DUOI))
        self.assertEqual(cap["tep_toi_da_mib"] * 1024**2, van_ban.MAX_BYTES)
        profile = self.manifest["ho_so_chay_mau"]
        self.assertIs(profile["headless"], False)
        self.assertEqual(profile["ngoai_le_man_hinh"]["ma_quyet_dinh"], "CD-038-ENGINE-3A")
        self.assertIs(profile["login_csdl"], False)

    def test_manifest_thieu_ngoai_le_va_capability_rong_deu_bi_chan(self):
        candidate = deepcopy(self.manifest)
        candidate["ho_so_chay_mau"].pop("ngoai_le_man_hinh")
        self.core.reject("urn:ktt:manifest:engine.v1", candidate)
        candidate = deepcopy(self.manifest)
        candidate["capability"] = []
        self.core.reject("urn:ktt:manifest:engine.v1", candidate)

    @unittest.skipUnless(contract_tests.Draft202012Validator,
                         "CHUA_KIEM: thiếu jsonschema; fallback không thay meta-schema 2020-12")
    def test_schema_2020_12_day_du(self):
        for key in ("urn:ktt:manifest:engine.v1", "urn:ktt:contract:van_ban_tai_lieu.v1"):
            contract_tests.Draft202012Validator.check_schema(self.core.schemas[key])
        self.core.validate("urn:ktt:manifest:engine.v1", self.manifest)
        self.core.validate("urn:ktt:contract:van_ban_tai_lieu.v1", self.run_adapter().van_ban)


@unittest.skipUnless(extraction and layout, "CHUA_KIEM: cần package mask_ocr nguồn và dependency sẵn có")
class DocxNguonTests(_AdapterFixture, unittest.TestCase):
    def test_import_mac_dinh_chi_parser_nguon(self):
        result = self.run_adapter(extract_docx=None, word_layout=None)
        self.assertEqual(result.van_ban["van_ban"], TEXT)
        self.core.validate("urn:ktt:contract:van_ban_tai_lieu.v1", result.van_ban)

    def run_source(self, docx):
        self.cong.ocr.return_value = docx
        with patch.object(extraction, "image_text", side_effect=AssertionError("Cấm OCR ảnh nhúng")), \
                patch.object(extraction, "require_ocr", side_effect=AssertionError("Cấm OCR khác")):
            return self.run_adapter(extract_docx=extraction.extract_docx, word_layout=layout.word_layout)

    def test_docx_demo_bang_o_rong_header_va_nguon_vi_tri(self):
        docx = tao_docx(f'<w:p><w:r><w:t>{TEXT}</w:t></w:r></w:p>'
                        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>00007</w:t></w:r></w:p></w:tc>'
                        '<w:tc><w:p/></w:tc><w:tc><w:p><w:r><w:t>0</w:t></w:r></w:p></w:tc>'
                        '</w:tr></w:tbl>', header=True)
        result = self.run_source(docx)
        self.core.validate("urn:ktt:contract:van_ban_tai_lieu.v1", result.van_ban)
        self.assertIn("00007\t\t0", result.van_ban["van_ban"])
        self.assertIn("DEMO đầu trang", result.van_ban["van_ban"])
        source = result.phan_hoi_nguon
        self.assertEqual([u["id"] for u in source["layout"]["units"]],
                         [k["ma_nguon"] for k in source["khoi"]])
        self.assertEqual(len({k["ma_nguon"] for k in source["khoi"]}), len(source["khoi"]))
        self.assertTrue(all(k["vi_tri"]["tep_id"] == DOCX for k in source["khoi"]))
        self.assertEqual(result.van_ban["trang"], [])

    def test_docx_anh_nhung_khong_chay_ocr_khac(self):
        result = self.run_source(tao_docx(image=True))
        self.assertIn(TEXT, result.van_ban["van_ban"])
        self.assertTrue(any("chưa được nhận dạng" in w for w in result.van_ban["canh_bao"]))
        self.assertTrue(all(u["source"] == "native" for u in result.phan_hoi_nguon["layout"]["units"]))

    def test_docx_hong_track_changes_va_bang_long_bi_tu_choi(self):
        samples = [b"DEMO not a zip", tao_docx('<w:p><w:ins><w:r><w:t>DEMO</w:t></w:r></w:ins></w:p>'),
                   tao_docx('<w:tbl><w:tr><w:tc><w:tbl/></w:tc></w:tr></w:tbl>')]
        for docx in samples:
            with self.subTest(size=len(docx)), self.assertRaises(DataError):
                self.run_source(docx)

    def test_cong_repo_hotfolder_gia_dung_mot_so_trang_va_dem(self):
        root = Path(tempfile.mkdtemp(prefix="ktt_demo_ocr2_"))
        cong = CongOCR(root / "hotfolder", tep_so_trang=root / "so_trang.json", thu_muc_dem=root / "dem")
        docx = tao_docx()
        self.cong = cong
        # Không khởi động HotFolder thread; thay đúng seam xử lý ABBYY.
        with patch.dict("os.environ", {"CODEX_NO_DELETE_FILES": "1"}), \
                patch.object(cong, "_chay_hot_folder", return_value=docx) as hotfolder:
            first = self.run_source_cong()
            second = self.run_source_cong()
        hotfolder.assert_called_once()
        self.assertEqual(first.docx, second.docx)
        self.assertEqual(first.van_ban["van_ban"], TEXT)
        self.assertEqual(sum(x[1] for x in json.loads((root / "so_trang.json").read_text("utf-8"))), 1)

    def run_source_cong(self):
        return self.run_adapter(extract_docx=extraction.extract_docx, word_layout=layout.word_layout)


if __name__ == "__main__":
    unittest.main()
