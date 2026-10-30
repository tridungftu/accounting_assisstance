"""TRICH-1a: DOCX DEMO/AI giả, không COM/OCR/Cloud/dịch vụ ngoài.

Tệp thử nằm ở mkdtemp và giữ lại, không cleanup/xóa. Không chạy test gốc
ngoài repo vì bộ đó có nhánh đọc hợp đồng thật và máy chủ HTTP riêng.
Không sửa/nới test gốc; các ca dưới kiểm seam và contract mới.
"""

from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.request
import zipfile

from kho_tri_thuc.engines.e_trich_xuat import docx, tham_so
from kho_tri_thuc.m4.review_goc.trich_xuat import danh_muc, doc_hop_dong, quy_trinh
from kho_tri_thuc.m4.review_goc.trich_xuat import ai_local, cloud

ROOT = Path(__file__).resolve().parents[1]
TEP = "10000000-0000-4000-8000-000000000001"
PHAN_HOI = "10000000-0000-4000-8000-000000000002"
MA = tuple(f"TC-{i:02d}" for i in range(1, 10)) + (
    "TT-01", "TT-02", "TT-03", "TT-04", "TT-05", "TT-10", "TT-11", "TT-12",
    "TT-20", "TT-21", "TT-22", "TT-30", "TT-31", "TT-32", "TT-33", "TT-40",
    "TT-41", "TT-42", "TT-50", "TT-51", "TT-52", "TT-53", "TT-54", "TT-55",
    "TT-56", "TT-60", "TT-61", "TT-62",
)
NS = doc_hop_dong.W_NS
TEXT = "DEMO hợp đồng số 00007, giá trị chưa xác định; tỷ lệ 0."


def tao_docx(inner, prefix="w"):
    path = Path(tempfile.mkdtemp(prefix="ktt_demo_trich_1a_")) / "DEMO.docx"
    xml = f'<{prefix}:document xmlns:{prefix}="{NS}"><{prefix}:body>{inner}</{prefix}:body></{prefix}:document>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)
    return path


class AIGia:
    la_cloud = False
    tok_vao = tok_ra = 0
    model = "DEMO-gia"
    url = "DEMO-khong-ket-noi"

    def __init__(self):
        self.goi = 0

    def chat_json(self, prompt, schema, key, *args):
        self.goi += 1
        ids = re.findall(r"^(R\d+) \|", prompt, re.MULTILINE)
        return {"vi_tri": [{"ma": ma, "ids": ids[:1]} for ma in MA]}, 0, 0

    def hoi_trich(self, prompt, *args):
        self.goi += 1
        return [{"ma": ma, "gia_tri": "00007", "don_vi": "",
                 "dieu_khoan": "Đoạn 1", "trich_dan": TEXT,
                 "ghi_chu": "DEMO AI giả"} for ma in MA], 0, 0


def anh_xa(phan_hoi, **changes):
    kwargs = dict(tep_id=TEP, phan_hoi_nguon_tep_id=PHAN_HOI, van_ban=TEXT,
                  loai_hop_dong="XD", danh_muc_id="XD",
                  danh_muc_sha256=tham_so.DANH_MUC_SHA256)
    kwargs.update(changes)
    return tham_so.anh_xa_tham_so(phan_hoi, **kwargs)


def dong(value="00007", **changes):
    row = dict(ma="TC-01", gia_tri=value, trich_dan=TEXT, dieu_khoan="Đoạn 1",
               kiem_tra="OK", ghi_chu="DEMO ghi chú", vi_tri_do_duoc="Đoạn 1")
    row.update(changes)
    return {"bang": [row]}


class DocxTests(unittest.TestCase):
    def test_track_changes_khong_doi_tep_va_khong_chuyen_word(self):
        path = tao_docx('<w:p><w:del w:id="1"><w:r><w:delText>DEMO cũ</w:delText></w:r></w:del>'
                        '<w:ins w:id="2"><w:r><w:t>DEMO mới</w:t></w:r></w:ins></w:p>')
        before = path.read_bytes()
        with patch.object(doc_hop_dong, "_word") as word, \
                patch.object(subprocess, "run") as process, \
                patch.object(doc_hop_dong, "chuyen_docx") as convert:
            info = docx.read_contract(path)
        self.assertEqual(info["text"], "DEMO mới")
        self.assertEqual(info["report"]["track_changes_accepted"], 2)
        self.assertEqual(info["report"]["accept_by"], "Python")
        self.assertEqual(path.read_bytes(), before)
        for mock in (word, process, convert):
            mock.assert_not_called()

    def test_alias_namespace_va_move_changes(self):
        path = tao_docx('<a:p><a:moveFrom><a:r><a:t>DEMO bỏ</a:t></a:r></a:moveFrom>'
                        '<a:moveTo><a:r><a:t>DEMO giữ</a:t></a:r></a:moveTo></a:p>', "a")
        info = docx.read_contract(path)
        self.assertEqual(info["text"], "DEMO giữ")
        self.assertEqual(info["report"]["track_changes_accepted"], 2)

    def test_xoa_dong_bang_va_doi_dinh_dang_thuan(self):
        path = tao_docx('<w:tbl><w:tr><w:trPr><w:del/></w:trPr><w:tc><w:p><w:r>'
                        '<w:t>DEMO dòng bỏ</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
                        '<w:p><w:r><w:rPr><w:rPrChange><w:rPr/></w:rPrChange></w:rPr>'
                        '<w:t>DEMO còn</w:t></w:r></w:p>')
        self.assertEqual(docx.read_contract(path)["text"], "DEMO còn")

    def test_word_bi_chan_tuong_minh(self):
        with patch.object(subprocess, "run") as process:
            with self.assertRaisesRegex(ValueError, "TRICH_WORD_BI_CHAN"):
                docx._word("DEMO.docx", "DEMO.docx")
        process.assert_not_called()

    def test_khong_doc_pdf_doc_hay_duoi_gia(self):
        with patch.object(doc_hop_dong, "read_pdf") as pdf:
            for name in ("DEMO.pdf", "DEMO.doc", "DEMO.docx.exe"):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "TRICH_CHI_DOCX"):
                    docx.read_contract(name)
        pdf.assert_not_called()

    def test_docx_hong_khong_thu_com(self):
        path = tao_docx("<w:p>")
        with patch.object(subprocess, "run") as process:
            with self.assertRaises(docx.ET.ParseError):
                docx.read_contract(path)
        process.assert_not_called()

    def test_giu_cau_truc_va_phieu_cua_nguon_khong_track(self):
        path = tao_docx('<w:p><w:r><w:t>DEMO mở đầu</w:t></w:r></w:p>'
                        '<w:p><w:r><w:t>Điều 1. DEMO giá</w:t></w:r></w:p>'
                        '<w:p><w:r><w:t>DEMO nội dung</w:t></w:r></w:p>')
        self.assertEqual(docx.read_contract(path), doc_hop_dong.read_contract(str(path)))

    def test_khong_sua_globals_nguon(self):
        self.assertIs(doc_hop_dong.read_contract.__globals__["read_docx"], doc_hop_dong.read_docx)
        self.assertIs(quy_trinh.TrichXuat.xu_ly.__globals__["read_contract"], doc_hop_dong.read_contract)


class ThamSoTests(unittest.TestCase):
    def test_catalog_37_ma_va_hash_nguon_repo(self):
        params = tham_so.danh_muc_xd()
        self.assertEqual(tuple(p["ma"] for p in params), MA)
        self.assertEqual(tuple(p[0] for p in danh_muc.MAC_DINH), MA)
        for name, digest in tham_so.BAN_REPO_SHA256.items():
            self.assertEqual(hashlib.sha256((Path(danh_muc.__file__).parent / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256(Path(doc_hop_dong.__file__).read_bytes()).hexdigest(), docx.NGUON_SHA256)

    def test_catalog_khong_tu_tao_khi_thieu_hoac_sai_hash(self):
        missing = Path(tempfile.mkdtemp(prefix="ktt_demo_catalog_")) / "DEMO.xlsx"
        with patch.object(danh_muc, "DANH_MUC_THAM_SO", missing), \
                patch.object(danh_muc, "create_catalog") as create:
            with self.assertRaises(FileNotFoundError):
                tham_so.danh_muc_xd()
            create.assert_not_called()
        with patch.object(tham_so, "DANH_MUC_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "SAI_HASH"):
                tham_so.danh_muc_xd()

    def test_anh_xa_du_37_khong_mat_nguon_va_khong_doi_dau_vao(self):
        raw = dong()
        before = deepcopy(raw)
        result = anh_xa(raw)
        self.assertEqual(raw, before)
        self.assertEqual(tuple(row["ma"] for row in result["tham_so"]), MA)
        row = result["tham_so"][0]
        self.assertEqual(row["gia_tri"], {"kieu": "van_ban", "gia_tri": "00007"})
        self.assertEqual(row["dan_chung"][0]["vi_tri"]["tep_id"], TEP)
        self.assertIn("ghi_chu: DEMO ghi chú", row["canh_bao"])
        self.assertIn("vi_tri_do_duoc: Đoạn 1", row["canh_bao"])
        self.assertEqual(result["phan_hoi_nguon_tep_id"], PHAN_HOI)

    def test_khong_dong_nhat_thieu_rong_chua_ro_va_so_khong(self):
        for value, kind in ((None, "chua_ro"), ("", "chua_ro"), ("Không quy định", "chua_ro"),
                            ("Không tìm thấy trong HĐ", "chua_ro"), ("0", "van_ban")):
            with self.subTest(value=value):
                row = anh_xa(dong(value))["tham_so"][0]
                self.assertEqual(row["gia_tri"]["kieu"], kind)
                self.assertEqual(row["nguyen_van"], value)

    def test_khong_doan_tien_ngay_tu_chuoi(self):
        for value in ("1.000.000", "31/02/2026", "Không áp dụng"):
            text = "DEMO " + value
            raw = dong(value, trich_dan=text)
            row = anh_xa(raw, van_ban=text)["tham_so"][0]
            self.assertEqual(row["gia_tri"], {"kieu": "van_ban", "gia_tri": value})

    def test_thieu_dan_chung_hoac_vi_tri_chi_la_ung_vien(self):
        for changes in ({"trich_dan": "DEMO bịa"}, {"trich_dan": ""}, {"dieu_khoan": ""}):
            with self.subTest(changes=changes):
                row = anh_xa(dong(**changes))["tham_so"][0]
                self.assertEqual(row["gia_tri"]["kieu"], "chua_ro")
                self.assertTrue(row["can_soat"])
                self.assertEqual(row["dan_chung"], [])

    def test_ma_la_trung_va_gia_tri_sai_kieu_bi_chan(self):
        for raw in ({"bang": [{"ma": "LA"}]}, {"bang": dong()["bang"] * 2}, dong(0)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                anh_xa(raw)

    def test_metadata_sai_khong_fallback_xd(self):
        for changes in ({"loai_hop_dong": ""}, {"loai_hop_dong": "MUA_HH"},
                        {"danh_muc_id": "DEMO_KHAC"}, {"danh_muc_sha256": "f" * 64},
                        {"tep_id": "DEMO"}, {"phan_hoi_nguon_tep_id": TEP},
                        {"revision": True}, {"revision": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                anh_xa(dong(), **changes)

    def test_uuid_32_ky_tu_khong_co_gach_noi_bi_chan(self):
        for field, value in (("tep_id", TEP), ("phan_hoi_nguon_tep_id", PHAN_HOI)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "TRICH_TEP_ID_SAI"):
                anh_xa(dong(), **{field: value.replace("-", "")})

    def test_cung_uuid_khac_hoa_thuong_khong_phai_tep_rieng(self):
        value = "abcdef00-0000-4000-8000-000000000001"
        for original, response in ((value, value.upper()), (value.upper(), value)):
            with self.subTest(original=original), self.assertRaisesRegex(
                    ValueError, "TRICH_PHAN_HOI_PHAI_LA_TEP_RIENG"):
                anh_xa(dong(), tep_id=original, phan_hoi_nguon_tep_id=response)

    def test_uuid_dung_format_khac_nhau_dat_schema_ke_ca_viet_hoa(self):
        original = "ABCDEF00-0000-4000-8000-000000000001"
        response = "abcdef00-0000-4000-8000-000000000002"
        result = anh_xa(dong(), tep_id=original, phan_hoi_nguon_tep_id=response)
        self.assertEqual(result["nguon_tep_ids"], [original])
        self.assertEqual(result["phan_hoi_nguon_tep_id"], response)
        self.assertEqual(result["tham_so"][0]["dan_chung"][0]["vi_tri"]["tep_id"], original)
        self._kiem_schema(result)

    def test_cloud_va_ocr_bi_chan_ca_truoc_lan_chay(self):
        for ai, cfg in ((None, None), (Mock(la_cloud=True), None), (AIGia(), {})):
            with self.subTest(ai=ai, cfg=cfg), self.assertRaisesRegex(ValueError, "CLOUD_BI_CHAN"):
                tham_so.TrichXuat(ai=ai, out_dir="DEMO", cloud=cfg)
        tx = tham_so.TrichXuat(ai=AIGia(), out_dir="DEMO")
        with self.assertRaisesRegex(ValueError, "OCR_BI_CHAN"):
            tx.ocr_pdf("DEMO.pdf")
        with self.assertRaisesRegex(ValueError, "CHI_DOCX"):
            tx.xu_ly("DEMO.pdf")
        tx.ai.la_cloud = True
        with self.assertRaisesRegex(ValueError, "CLOUD_BI_CHAN"):
            tx.xu_ly("DEMO.docx")

    def test_pipeline_ai_gia_track_changes_khong_com_ocr_cloud(self):
        path = tao_docx('<w:p><w:del w:id="1"><w:r><w:delText>DEMO cũ</w:delText></w:r></w:del>'
                        f'<w:ins w:id="2"><w:r><w:t>{TEXT}</w:t></w:r></w:ins></w:p>')
        ai = AIGia()
        before = path.read_bytes()
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch.object(obj, name, side_effect=AssertionError(name)))
                     for obj, name in ((doc_hop_dong, "_word"), (subprocess, "run"),
                                       (urllib.request, "urlopen"), (cloud, "kiem_tra_cloud"),
                                       (quy_trinh, "kiem_tra_cloud"), (ai_local.MayAI, "hoi_trich"),
                                       (quy_trinh.TrichXuat, "ocr_pdf"))]
            tx = tham_so.TrichXuat(ai=ai, cloud=None, out_dir=path.parent / "DEMO-out")
            raw = tx.xu_ly(path)
            for mock in mocks:
                mock.assert_not_called()
        self.assertGreater(ai.goi, 0)
        self.assertIsNone(tx.cloud)
        self.assertFalse(tx.ai.la_cloud)
        self.assertEqual(len(raw["bang"]), 37)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(raw["phieu_kiem_tra"]["accept_by"], "Python")
        self.assertEqual(raw["phieu_kiem_tra"]["track_changes_accepted"], 2)
        self.assertEqual(tuple(row["ma"] for row in raw["bang"]), MA)
        self.assertTrue(all(row["gia_tri"] == "00007" for row in raw["bang"]))
        source = path.parent / "DEMO-out" / "DEMO" / raw["tep"]["json"]
        self.assertEqual(json.loads(source.read_text(encoding="utf-8")), raw)
        result = anh_xa(raw)
        self.assertTrue(all(row["gia_tri"]["kieu"] == "van_ban" for row in result["tham_so"]))
        self._kiem_schema(result)

    def _kiem_schema(self, value):
        # Dùng bộ phân giải offline G2-17, kể cả fallback nếu thiếu jsonschema.
        from test_g2_17 import _minimal
        schemas = json.loads((ROOT / "src/kho_tri_thuc/core/contract/ky_thuat.json").read_text(encoding="utf-8"))
        schema = schemas["urn:ktt:contract:tham_so.v1"]
        _minimal(value, schema, schema, schemas)
        try:
            from jsonschema import Draft202012Validator, FormatChecker
            from referencing import Registry, Resource
        except ImportError:
            return
        registry = Registry().with_resources((key, Resource.from_contents(item)) for key, item in schemas.items())
        Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).validate(value)


if __name__ == "__main__":
    unittest.main()
