"""M2b: hợp đồng producer #7, chỉ bytes DEMO tự tạo, không fixture/kho thật."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m2.tai_hoa_don.manifest import RE_GIA_TRI_CAM, doc_manifest, phan_loai_file_tren_dia


def _hash(b):
    return hashlib.sha256(b).hexdigest()


def tao_run_demo(goc):
    """Một XML + PDF xem lại + bảng kê bytes opaque, đúng trường JS v1."""
    xml = b'<HDon><DEMO>0000000001</DEMO>\r\n</HDon>\r\n'
    pdf, bang_ke = b'%PDF-DEMO-view-only', b'DEMO-opaque-excel-bytes'
    for ten, b in (("DEMO__0000000001.xml", xml), ("DEMO.pdf", pdf), ("bang_ke_DEMO.xlsx", bang_ke)):
        (goc / ten).write_bytes(b)
    h = {
        "item_ordinal": 1,
        "key_raw": {"nbmst": "0000000001", "khmshdon": "1", "khhdon": "DEMO", "shdon": "000001"},
        "key_canonical": "0000000001|1|DEMO|000001", "key_thieu": [],
        "scope": "query", "ttxly": 5, "nhom_thu_tu": 1, "tthai_cong": 1,
        "tdlap": "2026-10-24T00:00:00Z", "dvtte_cong": None, "xml_status": "OK",
        "bang_chung": "XML", "can_cu": None, "file_xml": "DEMO__0000000001.xml",
        "hash_xml": _hash(xml), "xml_bytes": len(xml), "ordinal_zip": None, "ten_entry_zip": None,
        "xml_tep": [{"file": "DEMO__0000000001.xml", "sha256": _hash(xml), "bytes": len(xml),
                     "ordinal_zip": None, "ten_entry_zip": None}], "zip": None, "payload": None,
        "file_pdf": "DEMO.pdf", "hash_pdf": _hash(pdf), "vai_tro_pdf": "XEM_LAI", "pdf_loi": False, "loi": None,
    }
    fact = {"trang_thai": "UNKNOWN", "gia_tri": None, "ly_do": "DEMO_CHUA_DO"}
    return {
        "schema": "m2_00a.source7.manifest.v1", "nguon": "TAI_MOI", "run_id": "20261024-120000",
        "phap_nhan": {"uuid": "00000000-0000-0000-0000-000000000001", "ma": "DEMO"},
        "ky": "2026-10", "chieu": "purchase", "thu_muc_chieu": "mua_vao",
        "bat_dau": "2026-10-24T12:00:00.000Z", "ket_thuc": "2026-10-24T12:00:01.000Z",
        "phien_ban_bo_tai": "DEMO-v1", "nguoi_bam": "DEMO",
        "context": {"digest": "0" * 64, "nonce": "DEMO" + "0" * 22,
                    "request_key_sha256": "1" * 64, "profile_ref": "DEMO", "profile_revision": "DEMO-v1",
                    "source_instance": "DEMO", "scope_ref": "DEMO", "selection_digest": "2" * 64,
                    "actor_nguon": "crm_phien", "quyet_dinh_quyen": "NGOAI_PRODUCER_CHUA_KIEM",
                    "profile_khoa_bo_qua": []},
        "dang_nhap": {"captcha_da_go": copy.deepcopy(fact), "token_tai_su_dung": copy.deepcopy(fact),
                      "thoi_gian_cho_dang_nhap_giay": copy.deepcopy(fact), "do_luong": "PARTIAL"},
        "nhom": [{"thu_tu": 1, "path": "/api/demo", "scope": "query", "ttxly": 5,
                  "trang_thai": "OK", "so_ban_ghi": 1, "so_moi": 1, "loi": None}],
        "tong": {"tong_hd": 1, "xml_ok": 1, "khong_xml_goc": 0, "xml_loi": 0, "xml_khong_yeu_cau": 0,
                 "pdf_ok": 1, "pdf_loi": 0, "bang_ke_trang_thai": "OK",
                 "bang_ke": {"file": "bang_ke_DEMO.xlsx", "sha256": _hash(bang_ke), "bytes": len(bang_ke), "so_cot": 20}},
        "hoa_don": [h], "loi_chung": [], "trang_thai": "COMPLETE", "ly_do_partial": [],
        "gioi_han": {"xml_bytes": 16 * 1024 * 1024, "zip_bytes": 64 * 1024 * 1024, "zip_entries": 1000},
    }


class ManifestTinh(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory(prefix="M2b-DEMO-", ignore_cleanup_errors=True)
        self.addCleanup(self.tam.cleanup)
        self.goc = Path(self.tam.name)
        self.m = tao_run_demo(self.goc)

    def ghi(self, m=None):
        (self.goc / "manifest.json").write_text(
            json.dumps(self.m if m is None else m, ensure_ascii=False), encoding="utf-8"
        )

    def tu_choi(self, m=None, ma=None, file=None):
        self.ghi(m)
        with self.assertRaises(DataError) as ctx:
            doc_manifest(self.goc)
        e = ctx.exception
        self.assertTrue(e.code.startswith("M2_00_MANIFEST_"))
        if ma:
            self.assertEqual(e.code, "M2_00_MANIFEST_" + ma)
        if file:
            self.assertEqual(e.locator, file)
        return e

    def test_manifest_hop_le_giu_raw_identity_khong_tu_ten_file(self):
        self.ghi()
        kq = doc_manifest(self.goc)
        self.assertEqual(kq, self.m)
        self.assertEqual(kq["hoa_don"][0]["key_canonical"], "0000000001|1|DEMO|000001")
        self.assertIsNone(kq["hoa_don"][0]["dvtte_cong"])
        self.assertEqual(kq.hoa_don_thieu_khoa, [])
        self.assertEqual(kq.hoa_don_du_khoa, self.m["hoa_don"])

    def test_thieu_tung_truong_bat_buoc(self):
        for k in self.m:
            with self.subTest(truong=k):
                m = copy.deepcopy(self.m)
                m.pop(k)
                self.tu_choi(m, "THIEU_TRUONG")

    def test_thieu_tung_truong_long_nhau(self):
        for duong in (("phap_nhan",), ("context",), ("dang_nhap",), ("gioi_han",), ("tong",),
                      ("tong", "bang_ke"), ("hoa_don", 0), ("hoa_don", 0, "key_raw"),
                      ("hoa_don", 0, "xml_tep", 0), ("nhom", 0)):
            node = self.m
            for k in duong:
                node = node[k]
            for khoa in node:
                with self.subTest(duong=duong, khoa=khoa):
                    m = copy.deepcopy(self.m)
                    node_sai = m
                    for k in duong:
                        node_sai = node_sai[k]
                    node_sai.pop(khoa)
                    self.tu_choi(m, "THIEU_TRUONG")

    def test_sai_kieu_tung_truong_cap_dau(self):
        for k in self.m:
            with self.subTest(truong=k):
                m = copy.deepcopy(self.m)
                m[k] = None
                self.tu_choi(m)

    def test_sai_kieu_cau_truc_va_bool_khong_phai_so(self):
        ca = [((), []), (("hoa_don", 0, "key_raw"), []), (("hoa_don", 0, "xml_tep"), {}),
              (("hoa_don", 0, "pdf_loi"), 1), (("hoa_don", 0, "xml_tep", 0, "bytes"), True),
              (("tong", "tong_hd"), True), (("nhom", 0, "so_ban_ghi"), "1"),
              (("dang_nhap", "captcha_da_go"), False)]
        for duong, v in ca:
            with self.subTest(duong=duong):
                m = copy.deepcopy(self.m)
                if not duong:
                    m = v
                else:
                    node = m
                    for k in duong[:-1]:
                        node = node[k]
                    node[duong[-1]] = v
                self.tu_choi(m)

    def test_ky_chieu_nguon_khong_hop_le(self):
        for k, vals in (("ky", ["2026-1", "2026-00", "2026-13", "26-10", "2026-10\n"]),
                        ("chieu", ["mua_vao", "PURCHASE", "", []]), ("nguon", ["DEMO", "", 1])):
            for v in vals:
                with self.subTest(k=k, v=v):
                    m = copy.deepcopy(self.m)
                    m[k] = v
                    self.tu_choi(m)

    def test_sold_va_hoi_cuu_co_xap_xi(self):
        self.m.update(chieu="sold", thu_muc_chieu="ban_ra", nguon="HOI_CUU", xap_xi=True)
        self.ghi()
        self.assertEqual(doc_manifest(self.goc), self.m)
        self.m["xap_xi"] = False
        self.tu_choi()
        self.m.pop("xap_xi")
        self.tu_choi(ma="THIEU_TRUONG")

    def test_identity_thieu_tung_phan_va_thua_phan(self):
        for key in ("0000000001|1|DEMO", "0000000001|1|DEMO|1|EXTRA"):
            with self.subTest(key=key):
                self.m["hoa_don"][0]["key_canonical"] = key
                self.tu_choi(ma="IDENTITY_THIEU")
        for key in ("|1|DEMO|1", "0000000001||DEMO|1", "0000000001|1||1",
                    "0000000001|1|DEMO|", "0000000001|1| |1"):
            with self.subTest(key=key):
                self.m["hoa_don"][0]["key_canonical"] = key
                self.tu_choi(ma="IDENTITY_KHONG_KHOP")

    def test_thieu_shdon_vao_ngoai_le_khong_chan_hoa_don_khac(self):
        h = copy.deepcopy(self.m["hoa_don"][0])
        h.update(item_ordinal=2, key_canonical="0000000001|1|DEMO|", key_thieu=["shdon"])
        h["key_raw"]["shdon"] = None
        self.m["hoa_don"].append(h)
        self.m["tong"].update(tong_hd=2, xml_ok=2, pdf_ok=2)
        self.m["nhom"][0].update(so_ban_ghi=2, so_moi=2)
        self.ghi()
        kq = doc_manifest(self.goc)
        self.assertEqual(kq, self.m)
        self.assertEqual(kq.hoa_don_thieu_khoa, [h])
        self.assertEqual(kq.hoa_don_thieu_khoa[0]["key_raw"]["shdon"], None)
        self.assertEqual(kq.hoa_don_thieu_khoa[0]["key_thieu"], ["shdon"])
        self.assertEqual(kq.hoa_don_du_khoa, [self.m["hoa_don"][0]])
        self.assertEqual(phan_loai_file_tren_dia(self.goc, kq), [])

    def test_key_thieu_phai_khop_dung_phan_raw_thieu(self):
        for k in ("nbmst", "khmshdon", "khhdon", "shdon"):
            for raw in (None, ""):
                with self.subTest(k=k, raw=raw):
                    m = copy.deepcopy(self.m)
                    h = m["hoa_don"][0]
                    h["key_raw"][k] = raw
                    h["key_canonical"] = "|".join("" if v is None else v for v in h["key_raw"].values())
                    h["key_thieu"] = [k]
                    self.ghi(m)
                    self.assertEqual(doc_manifest(self.goc).hoa_don_thieu_khoa, [h])
                    for sai in ([], ["khac"], [k, k], [k, "khac"]):
                        h["key_thieu"] = sai
                        self.tu_choi(m, "IDENTITY_THIEU")
        self.m["hoa_don"][0]["key_thieu"] = ["shdon"]
        self.tu_choi(ma="IDENTITY_THIEU")

    def test_hoa_don_thieu_khoa_van_kiem_hash(self):
        h = self.m["hoa_don"][0]
        h["key_raw"]["shdon"] = None
        h.update(key_canonical="0000000001|1|DEMO|", key_thieu=["shdon"])
        (self.goc / h["file_xml"]).write_bytes(b"DEMO-HASH-SAI")
        self.tu_choi(ma="HASH_LECH", file=h["file_xml"])

    def test_identity_raw_khong_khop_va_giu_so_khong_dau(self):
        self.m["hoa_don"][0]["key_canonical"] = "0000000001|1|DEMO|1"
        self.tu_choi(ma="IDENTITY_KHONG_KHOP")

    def test_hash_xml_lech_bao_dung_file(self):
        ten = self.m["hoa_don"][0]["file_xml"]
        p = self.goc / ten
        p.write_bytes(p.read_bytes().replace(b"0000000001", b"0000000002"))
        self.tu_choi(ma="HASH_LECH", file=ten)

    def test_sua_tay_hash_xml_khong_khop_xml_tep_bao_dung_file(self):
        self.m["hoa_don"][0]["hash_xml"] = "0" * 64
        self.tu_choi(ma="XML_CHINH_KHONG_KHOP", file="DEMO__0000000001.xml")

    def test_hash_tinh_bytes_khong_chuan_hoa_newline(self):
        ten = self.m["hoa_don"][0]["file_xml"]
        p = self.goc / ten
        p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
        self.tu_choi(ma="HASH_LECH", file=ten)

    def test_hash_bang_ke_lech_khong_parse_excel(self):
        ten = self.m["tong"]["bang_ke"]["file"]
        p = self.goc / ten
        p.write_bytes(p.read_bytes().replace(b"DEMO", b"FAIL"))
        self.tu_choi(ma="HASH_LECH", file=ten)

    def test_hash_pdf_lech(self):
        (self.goc / "DEMO.pdf").write_bytes(b'%PDF-DEMO-view-onlx')
        self.tu_choi(ma="HASH_LECH", file="DEMO.pdf")

    def test_hash_sai_dinh_dang_va_so_bytes_lech(self):
        for gia_tri in ("z" * 64, "0" * 63, None):
            with self.subTest(hash=gia_tri):
                self.m["hoa_don"][0]["xml_tep"][0]["sha256"] = gia_tri
                self.tu_choi()
        self.m = tao_run_demo(self.goc)
        self.m["tong"]["bang_ke"]["bytes"] += 1
        self.tu_choi(ma="BYTES_LECH", file="bang_ke_DEMO.xlsx")

    def test_tep_thieu_va_duong_dan_thoat_run(self):
        self.m["tong"]["bang_ke"]["file"] = "DEMO-khong-ton-tai.xlsx"
        self.tu_choi(ma="TEP_KHONG_AN_TOAN", file="DEMO-khong-ton-tai.xlsx")
        for ten in ("../DEMO.xml", "..\\DEMO.xml", "C:\\DEMO.xml", "/DEMO.xml", "DEMO.xml:secret", "NUL.xml", "DEMO..xml"):
            with self.subTest(ten=ten):
                self.m["tong"]["bang_ke"]["file"] = ten
                self.tu_choi()

    def test_bi_mat_long_nhau_tu_choi_khong_lo_gia_tri(self):
        canary = "DEMO-CANARY-CREDENTIAL"
        for khoa in ("mat_khau", "password", "pass", "token", "PASSWORD", "tax_password", "access_token"):
            with self.subTest(khoa=khoa):
                m = copy.deepcopy(self.m)
                m["hoa_don"][0]["du_lieu_la"] = [{khoa: canary}]
                e = self.tu_choi(m, "CO_BI_MAT")
                self.assertNotIn(canary, str(e) + repr(e) + e.locator)

    def test_bi_mat_trong_gia_tri_chuoi(self):
        for v in ("password=DEMO-CANARY", "token: DEMO-CANARY", "mat_khau=DEMO-CANARY",
                  "Bearer DEMO-CANARY", "abcdefghijk.abcdefghijk.abcdefghijk"):
            with self.subTest(v=v):
                m = copy.deepcopy(self.m)
                m["phien_ban_bo_tai"] = v
                e = self.tu_choi(m, "CO_BI_MAT")
                self.assertNotIn(v, str(e) + repr(e) + e.locator)

    def test_chuoi_40000_ky_tu_tu_choi_truoc_regex_duoi_mot_giay(self):
        self.m["phien_ban_bo_tai"] = "a" * 40000
        self.ghi()
        with patch("kho_tri_thuc.m2.tai_hoa_don.manifest.RE_GIA_TRI_CAM", wraps=RE_GIA_TRI_CAM) as regex:
            bat_dau = time.perf_counter()
            with self.assertRaises(DataError) as cm:
                doc_manifest(self.goc)
            thoi_gian = time.perf_counter() - bat_dau
            self.assertEqual(cm.exception.code, "M2_00_MANIFEST_GIA_TRI_QUA_DAI")
            self.assertTrue(all(len(c.args[0]) <= 4096 for c in regex.search.call_args_list))
            self.assertLess(thoi_gian, 1.0)

    def test_chuoi_dung_nguong_4096_van_duoc_quet_bi_mat(self):
        self.m["phien_ban_bo_tai"] = "!" * (4096 - len("token=DEMO")) + "token=DEMO"
        self.tu_choi(ma="CO_BI_MAT")

    def test_file_ngoai_manifest_chua_ro_nguon_m2_00_10(self):
        (self.goc / "DEMO-la.XML").write_bytes(b"DEMO")
        (self.goc / "DEMO-la.pdf").write_bytes(b"DEMO")
        (self.goc / "DEMO-ignore.txt").write_bytes(b"DEMO")
        (self.goc / "DEMO-sub").mkdir()
        (self.goc / "DEMO-sub" / "DEMO.xml").write_bytes(b"DEMO")
        self.ghi()
        m = doc_manifest(self.goc)
        self.assertEqual(phan_loai_file_tren_dia(self.goc, m),
                         ["DEMO-la.XML", "DEMO-la.pdf", "DEMO-sub/DEMO.xml"])
        self.assertEqual(m, self.m)

    def test_doc_hai_lan_idempotent_khong_ghi_dia(self):
        self.ghi()
        truoc = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.goc.iterdir()}
        a, b = doc_manifest(self.goc), doc_manifest(self.goc)
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertEqual(phan_loai_file_tren_dia(self.goc, a), [])
        self.assertEqual(truoc, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.goc.iterdir()})

    def test_zip_nhieu_xml_kiem_ca_tep_thu_hai(self):
        h = self.m["hoa_don"][0]
        t0 = h["xml_tep"][0]
        b = b"<DEMO>XML-THU-HAI</DEMO>"
        (self.goc / "DEMO_2.xml").write_bytes(b)
        h["xml_tep"].append({"file": "DEMO_2.xml", "sha256": _hash(b), "bytes": len(b),
                             "ordinal_zip": 2, "ten_entry_zip": "DEMO.xml"})
        h.update(ordinal_zip=1, ten_entry_zip="DEMO.xml")
        t0.update(ordinal_zip=1, ten_entry_zip="DEMO.xml")
        h["zip"] = {"file": None, "sha256": "0" * 64, "bytes": 100, "coverage": "COMPLETE", "loi": None,
                    "entries": [{"ordinal": i, "name": t["ten_entry_zip"], "declared_bytes": t["bytes"],
                                 "read_state": "READ_OK", "bytes": t["bytes"], "sha256": t["sha256"],
                                 "loi": None, "trung_ten": True, "file": t["file"]}
                                for i, t in enumerate(h["xml_tep"], 1)]}
        self.ghi()
        self.assertEqual(doc_manifest(self.goc), self.m)
        self.assertEqual(phan_loai_file_tren_dia(self.goc, self.m), [])
        (self.goc / "DEMO_2.xml").write_bytes(b.replace(b"HAI", b"BAD"))
        self.tu_choi(ma="HASH_LECH", file="DEMO_2.xml")

    def test_zip_link_sai_tu_choi(self):
        self.m["hoa_don"][0]["xml_tep"][0]["ordinal_zip"] = 1
        self.tu_choi(ma="ZIP_KHONG_KHOP")

    def test_khong_xml_goc_la_bang_ke_khong_phai_loi(self):
        h = self.m["hoa_don"][0]
        for k in ("file_xml", "hash_xml", "xml_bytes", "file_pdf", "hash_pdf", "vai_tro_pdf"):
            h[k] = None
        h.update(xml_status="KHONG_XML_GOC", bang_chung="BANG_KE", can_cu="DEMO_KHONG_MA", xml_tep=[])
        self.m["tong"].update(xml_ok=0, khong_xml_goc=1, pdf_ok=0)
        self.ghi()
        self.assertEqual(doc_manifest(self.goc)["hoa_don"][0]["bang_chung"], "BANG_KE")
        self.assertEqual(phan_loai_file_tren_dia(self.goc, self.m), ["DEMO.pdf", "DEMO__0000000001.xml"])

    def test_loi_xml_va_partial_khong_bi_bo_qua(self):
        h = self.m["hoa_don"][0]
        for k in ("file_xml", "hash_xml", "xml_bytes", "file_pdf", "hash_pdf", "vai_tro_pdf", "bang_chung"):
            h[k] = None
        h.update(xml_status="LOI", xml_tep=[], loi={"code": "DEMO_LOI", "stage": "XML", "http_status": 429})
        self.m["tong"].update(xml_ok=0, xml_loi=1, pdf_ok=0)
        self.m.update(trang_thai="PARTIAL", ly_do_partial=["XML_LOI"])
        self.ghi()
        self.assertEqual(doc_manifest(self.goc)["trang_thai"], "PARTIAL")
        self.m["trang_thai"] = "COMPLETE"
        self.tu_choi()

    def test_tong_va_trang_thai_sai_tu_choi(self):
        ca = [("tong", "tong_hd", 2), ("tong", "xml_ok", 0), ("tong", "pdf_ok", 0),
              ("tong", "bang_ke_trang_thai", "KHONG_YEU_CAU"), ("tong", "bang_ke", None),
              (None, "ly_do_partial", ["XML_LOI"]), (None, "trang_thai", "PARTIAL")]
        for node, k, v in ca:
            with self.subTest(node=node, k=k):
                m = copy.deepcopy(self.m)
                (m[node] if node else m)[k] = v
                self.tu_choi(m)

    def test_thoi_gian_schema_va_context_sai(self):
        for k, v in (("run_id", "20260230-120000"), ("bat_dau", "2026-02-30T12:00:00.000Z"),
                     ("ket_thuc", "2026-10-24T11:00:00.000Z"), ("schema", "DEMO-v2")):
            with self.subTest(k=k):
                m = copy.deepcopy(self.m)
                m[k] = v
                self.tu_choi(m)
        self.m["context"]["digest"] = "DEMO"
        self.tu_choi()

    def test_dang_nhap_observed_va_so_khong_huu_han(self):
        for k, v in (("captcha_da_go", False), ("token_tai_su_dung", True),
                     ("thoi_gian_cho_dang_nhap_giay", 1.5)):
            self.m["dang_nhap"][k] = {"trang_thai": "OBSERVED", "gia_tri": v, "can_cu": "DEMO_QUAN_SAT"}
        self.m["dang_nhap"]["do_luong"] = "COMPLETE"
        self.ghi()
        self.assertEqual(doc_manifest(self.goc), self.m)
        for v in (True, "1", 10**400):
            with self.subTest(v=str(v)[:20]):
                self.m["dang_nhap"]["thoi_gian_cho_dang_nhap_giay"]["gia_tri"] = v
                self.tu_choi()
        self.m = tao_run_demo(self.goc)
        self.m["hoa_don"][0]["ttxly"] = 10**400
        self.tu_choi(ma="SAI_KIEU")

    def test_json_hong_trung_khoa_khong_finite_va_utf8(self):
        for raw in (b'{', b'{"ky":"2026-10","ky":"2026-11"}', b'{"DEMO":NaN}', b'\xff',
                    b'[' * 1100 + b']' * 1100):
            with self.subTest(raw=raw[:30]):
                (self.goc / "manifest.json").write_bytes(raw)
                with self.assertRaises(DataError):
                    doc_manifest(self.goc)

    def test_truong_la_khong_tu_nguon_suy_gia_tri(self):
        self.m["tong"]["bang_ke"]["hash"] = self.m["tong"]["bang_ke"]["sha256"]
        self.tu_choi(ma="TRUONG_LA")

    def hoi_cuu_ngoai_run(self):
        cu = self.goc / "nguon-cu"
        cu.mkdir()
        h = self.m["hoa_don"][0]
        for ten in (h["file_xml"], h["file_pdf"], self.m["tong"]["bang_ke"]["file"]):
            (cu / ten).write_bytes((self.goc / ten).read_bytes())
        h["file_xml"] = str(cu / h["file_xml"])
        h["file_pdf"] = str(cu / h["file_pdf"])
        h["xml_tep"][0]["file"] = h["file_xml"]
        b = self.m["tong"]["bang_ke"]
        b.update(file=str(cu / b["file"]), so_cot=15)
        self.m.update(nguon="HOI_CUU", xap_xi=True, thu_muc_tep_goc=str(cu))
        return cu

    def test_hoi_cuu_nguon_cu_ngoai_run_15_cot_van_kiem_hash(self):
        cu = self.hoi_cuu_ngoai_run()
        self.ghi()
        self.assertEqual(doc_manifest(self.goc), self.m)
        self.assertEqual(phan_loai_file_tren_dia(self.goc, self.m), [])
        xml = Path(self.m["hoa_don"][0]["file_xml"])
        raw = xml.read_bytes()
        xml.write_bytes(raw.replace(b"0000000001", b"0000000002"))
        self.tu_choi(ma="HASH_LECH", file=str(xml))

    def test_hoi_cuu_khong_cho_tham_chieu_ngoai_goc(self):
        self.hoi_cuu_ngoai_run()
        h = self.m["hoa_don"][0]
        h["file_xml"] = str(self.goc / "DEMO__0000000001.xml")
        h["xml_tep"][0]["file"] = h["file_xml"]
        self.tu_choi(ma="DUONG_DAN_SAI")

    def test_hoi_cuu_chi_nhan_goc_trong_danh_sach_tin_cay(self):
        cu = self.hoi_cuu_ngoai_run()
        khac = self.goc / "goc-khac"
        khac.mkdir()
        self.ghi()
        for ds_goc in (cu, str(cu), [khac, cu], (khac, self.goc)):
            with self.subTest(goc=ds_goc):
                self.assertEqual(doc_manifest(self.goc, goc_hoi_cuu_tin_cay=ds_goc), self.m)

    def test_hoi_cuu_goc_ngoai_danh_sach_bi_tu_choi_truoc_doc_tep(self):
        self.hoi_cuu_ngoai_run()
        # Cùng tiền tố tên không có nghĩa là nằm trong gốc cấu hình.
        tin_cay = self.goc / "nguon"
        tin_cay.mkdir()
        self.ghi()
        for ds_goc in (tin_cay, [tin_cay], []):
            with self.subTest(goc=ds_goc), patch.object(Path, "open", autospec=True,
                                                       side_effect=Path.open) as mo:
                with self.assertRaises(DataError) as cm:
                    doc_manifest(self.goc, goc_hoi_cuu_tin_cay=ds_goc)
                self.assertEqual(cm.exception.code, "M2_00_MANIFEST_HOI_CUU_GOC_KHONG_TIN_CAY")
                self.assertEqual(cm.exception.locator, "$.thu_muc_tep_goc")
                self.assertEqual([c.args[0].name for c in mo.call_args_list], ["manifest.json"])

    def test_hoi_cuu_khong_cho_parent_traversal_va_goc_tuong_doi(self):
        cu = self.hoi_cuu_ngoai_run()
        for file in ("DEMO__0000000001.xml", str(cu / ".." / "DEMO__0000000001.xml")):
            with self.subTest(file=file):
                m = copy.deepcopy(self.m)
                m["hoa_don"][0]["file_xml"] = file
                m["hoa_don"][0]["xml_tep"][0]["file"] = file
                self.tu_choi(m, "DUONG_DAN_SAI")
        self.m["thu_muc_tep_goc"] = "nguon-cu"
        self.tu_choi(ma="TEP_KHONG_AN_TOAN")

    def test_tai_moi_khong_duoc_mo_rong_goc_hoac_bang_ke_15_cot(self):
        self.m["tong"]["bang_ke"]["so_cot"] = 15
        self.tu_choi()
        self.m["tong"]["bang_ke"]["so_cot"] = 20
        self.m["thu_muc_tep_goc"] = str(self.goc)
        self.tu_choi(ma="TRUONG_LA")

    def test_hoi_cuu_ngoai_run_van_quet_credential(self):
        self.hoi_cuu_ngoai_run()
        self.m["nguoi_bam"] = "password=DEMO_SECRET"
        self.tu_choi(ma="CO_BI_MAT")

    def test_hoi_cuu_ngoai_run_chan_symlink(self):
        cu = self.hoi_cuu_ngoai_run()
        link = cu / "DEMO-link.xml"
        try:
            link.symlink_to(self.goc / "DEMO__0000000001.xml")
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"Máy không cho tạo symlink DEMO: {e}")
        h = self.m["hoa_don"][0]
        h["file_xml"] = str(link)
        h["xml_tep"][0]["file"] = str(link)
        self.tu_choi(ma="TEP_KHONG_AN_TOAN")

    @unittest.skipUnless(os.name == "nt", "Junction chỉ có trên Windows")
    def test_hoi_cuu_ngoai_run_chan_junction_khong_can_quyen_admin(self):
        cu = self.hoi_cuu_ngoai_run()
        dich = self.goc / "dich-junction"
        dich.mkdir()
        ten = "DEMO.xml"
        (dich / ten).write_bytes(Path(self.m["hoa_don"][0]["file_xml"]).read_bytes())
        link = cu / "DEMO-junction"
        kq = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(dich)],
                            capture_output=True, timeout=10)
        self.assertEqual(kq.returncode, 0, repr(kq.stderr))
        h = self.m["hoa_don"][0]
        h["file_xml"] = h["xml_tep"][0]["file"] = str(link / ten)
        self.tu_choi(ma="TEP_KHONG_AN_TOAN")
        self.m["thu_muc_tep_goc"] = str(link)
        self.tu_choi(ma="TEP_KHONG_AN_TOAN", file=link.name)


if __name__ == "__main__":
    unittest.main()
