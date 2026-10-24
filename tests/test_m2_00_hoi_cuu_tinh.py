"""M2d / M2-00-09: XML, bảng kê và hai gốc hoàn toàn DEMO tự tạo."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m2.tai_hoa_don.hoi_cuu import dem_doi_chieu, sinh_manifest_hoi_cuu
from kho_tri_thuc.m2.tai_hoa_don.manifest import doc_manifest, phan_loai_file_tren_dia
from kho_tri_thuc.m2.tai_hoa_don.nhan import lap_ke_hoach_nhan


HEAD = ["STT", "Ky hieu mau so", "Ky hieu HD", "So HD", "Ngay lap", "MST nguoi ban",
        "Ten nguoi ban", "MST nguoi mua", "Ten nguoi mua", "So giay to (CCCD)",
        "Tien chua thue", "Tien thue", "Tong thanh toan", "Don vi tien te", "Trang thai"]


def xml_demo(mst="0000000001", so="000007"):
    return (f'<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>DEMO</KHHDon>'
            f'<SHDon>{so}</SHDon><NLap>2026-09-01</NLap><DVTTe>VND</DVTTe></TTChung>'
            f'<NDHDon><NBan><MST>{mst}</MST></NBan><NMua><MST>0000000002</MST></NMua>'
            '<DSHHDVu><HHDVu><STT>1</STT><TChat>1</TChat><THHDVu>DEMO</THHDVu>'
            '<DVTinh>CAI</DVTinh><SLuong>1</SLuong><DGia>10</DGia><ThTien>10</ThTien>'
            '<TSuat>0</TSuat></HHDVu></DSHHDVu></NDHDon></DLHDon></HDon>').encode("utf-8")


def bang_ke_demo(p, rows=None, head=None):
    wb = Workbook()
    ws = wb.active
    ws.append(HEAD if head is None else head)
    for row in ([("0000000001", 7, 1), ("0000000003", 7, 2), ("0000000004", 8, 3)] if rows is None else rows):
        mst, so, tthai = row
        ws.append([ws.max_row, "1", "DEMO", so, "2026-09-01", mst, "Bán DEMO", "0000000002",
                   "Mua DEMO", None, 10, 0, 10, "VND", tthai])
    wb.save(p)
    wb.close()


def cay_nguon(p):
    """Hash cây trước/sau: cả đường dẫn, mtime và bytes; không xét atime đọc."""
    return {f.relative_to(p).as_posix(): (f.stat().st_mtime_ns, hashlib.sha256(f.read_bytes()).hexdigest())
            for f in p.rglob("*") if f.is_file()}


class HoiCuuTinh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="M2d-DEMO-", ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.nguon = self.root / "goc-PN" / "DEMO" / "2026-09"
        self.nguon.mkdir(parents=True)
        self.ra = self.root / "manifest-rieng"
        # Tên cố tình sai số và không có MST: identity phải lấy từ nội dung.
        (self.nguon / "1DEMO-999_1.xml").write_bytes(xml_demo())
        (self.nguon / "1DEMO-999_2.xml").write_bytes(xml_demo("0000000003"))
        (self.nguon / "hong.xml").write_bytes(b"<HDon><DEMO>")
        (self.nguon / "1DEMO-999_1.pdf").write_bytes(b"%PDF-DEMO-view-only")
        self.excel = self.nguon / "bang_ke_purchase_2026-09.xlsx"
        bang_ke_demo(self.excel)
        for i, p in enumerate(sorted(self.nguon.iterdir())):
            ns = 1_759_276_800_000_000_000 + i * 1_000_000_000
            os.utime(p, ns=(ns, ns))

    def sinh(self, nguon=None, ra=None, chieu="purchase"):
        return sinh_manifest_hoi_cuu(nguon or self.nguon, ma_phap_nhan="DEMO", chieu=chieu,
                                     ky="2026-09", thu_muc_ra=ra or self.ra)

    def test_m2_00_09_so_dem_va_m2_nhan_du_du_lieu_demo(self):
        run = self.sinh()
        m = doc_manifest(run)
        dem = dem_doi_chieu(self.nguon, m)
        self.assertEqual(dem, {"file_xml_tren_dia": 3, "muc_trong_manifest": 4,
                               "dong_bang_ke": 3, "khong_xml_goc": 1})
        self.assertEqual(dem["file_xml_tren_dia"], dem["muc_trong_manifest"] - dem["khong_xml_goc"])
        self.assertEqual(dem_doi_chieu(self.nguon, run), dem)
        self.assertEqual(m["nguon"], "HOI_CUU")
        self.assertTrue(m["xap_xi"])
        self.assertEqual(m["tong"]["bang_ke"]["so_cot"], 15)
        plan = lap_ke_hoach_nhan(run, ma_phap_nhan="DEMO")
        self.assertEqual(len(plan["muc"]), 3)
        self.assertEqual(sum(h["bang_chung"] == "BANG_KE" for h in plan["muc"]), 1)
        self.assertEqual(sum(e["ma"] == "TAI_LOI" for e in plan["ngoai_le"]), 1)
        self.assertTrue(plan["xap_xi"])
        self.assertEqual(plan["chua_ro_nguon"], [])

    def test_identity_noi_dung_va_ghep_bang_ke_khong_mat_zero_xml(self):
        m = doc_manifest(self.sinh())
        ok = [h for h in m["hoa_don"] if h["xml_status"] == "OK"]
        self.assertEqual({h["key_canonical"] for h in ok},
                         {"0000000001|1|DEMO|000007", "0000000003|1|DEMO|000007"})
        self.assertEqual([h["tthai_cong"] for h in ok], [1, 2])
        self.assertTrue(all(h["ordinal_zip"] is None and h["zip"] is None for h in ok))

    def test_chi_co_bang_ke_la_khong_xml_goc(self):
        h = next(h for h in doc_manifest(self.sinh())["hoa_don"] if h["xml_status"] == "KHONG_XML_GOC")
        self.assertEqual(h["key_canonical"], "0000000004|1|DEMO|8")
        self.assertEqual(h["bang_chung"], "BANG_KE")
        self.assertIsNone(h["loi"])
        self.assertEqual(h["tthai_cong"], 3)

    def test_xml_hong_giu_payload_hash_va_ly_do(self):
        m = doc_manifest(self.sinh())
        h = next(h for h in m["hoa_don"] if h["xml_status"] == "LOI")
        self.assertEqual(h["loi"]["code"], "XML_MALFORMED")
        self.assertEqual(h["payload"]["sha256"], hashlib.sha256((self.nguon / "hong.xml").read_bytes()).hexdigest())
        self.assertEqual(m["tong"]["xml_loi"], 1)
        self.assertIn("XML_LOI", m["ly_do_partial"])

    def test_lap_lai_khong_nhan_ban_nguon_cu_khong_doi(self):
        truoc = cay_nguon(self.nguon)
        run1 = self.sinh()
        data, st = (run1 / "manifest.json").read_bytes(), (run1 / "manifest.json").stat()
        run2 = self.sinh()
        self.assertEqual(run1, run2)
        self.assertEqual((run2 / "manifest.json").read_bytes(), data)
        self.assertEqual((run2 / "manifest.json").stat().st_mtime_ns, st.st_mtime_ns)
        self.assertEqual(cay_nguon(self.nguon), truoc)
        self.assertEqual(len(list(self.ra.rglob("manifest.json"))), 1)
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertFalse((self.nguon / "manifest.json").exists())

    def test_hai_goc_cung_thang_cung_bytes_mtime_hai_run(self):
        khac = self.root / "goc-cong-cu" / "2026-09"
        shutil.copytree(self.nguon, khac, copy_function=shutil.copy2)
        run1, run2 = self.sinh(), self.sinh(khac)
        m1, m2 = doc_manifest(run1), doc_manifest(run2)
        self.assertNotEqual(m1["run_id"], m2["run_id"])
        self.assertNotEqual(m1["context"]["source_instance"], m2["context"]["source_instance"])
        self.assertEqual(len(lap_ke_hoach_nhan(run2, ma_phap_nhan="DEMO")["muc"]), 3)

    def test_mtime_min_max_khong_lay_gio_hien_tai(self):
        m = doc_manifest(self.sinh())
        self.assertEqual(m["bat_dau"], "2025-10-01T00:00:00.000Z")
        self.assertEqual(m["ket_thuc"], "2025-10-01T00:00:04.000Z")
        self.assertEqual(m["dang_nhap"]["do_luong"], "PARTIAL")
        self.assertEqual(m["nhom"], [])

    def test_nguon_doi_hash_bi_m2b_va_m2c_tu_choi(self):
        run = self.sinh()
        (self.nguon / "1DEMO-999_1.xml").write_bytes(xml_demo(so="000008"))
        for doc in (lambda: doc_manifest(run), lambda: lap_ke_hoach_nhan(run, ma_phap_nhan="DEMO")):
            with self.subTest(doc=doc), self.assertRaises(DataError) as cm:
                doc()
            self.assertEqual(cm.exception.code, "M2_00_MANIFEST_HASH_LECH")
        moi = self.sinh()
        self.assertNotEqual(run, moi)

    def test_payload_hong_bang_ke_pdf_deu_kiem_hash(self):
        run = self.sinh()
        for p in (self.nguon / "hong.xml", self.excel, self.nguon / "1DEMO-999_1.pdf"):
            raw = p.read_bytes()
            try:
                # Cùng kích thước để chứng minh kiểm hash, không chỉ số bytes.
                p.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                with self.subTest(file=p.name), self.assertRaises(DataError) as cm:
                    doc_manifest(run)
                self.assertEqual(cm.exception.code, "M2_00_MANIFEST_HASH_LECH")
            finally:
                p.write_bytes(raw)

    def test_tham_chieu_tuyet_doi_nguon_rieng_va_pdf_chua_ro(self):
        (self.nguon / "ngoai-manifest.pdf").write_bytes(b"%PDF-DEMO")
        run = self.sinh()
        m = doc_manifest(run)
        self.assertEqual(Path(m["thu_muc_tep_goc"]), self.nguon)
        for h in m["hoa_don"]:
            for t in h["xml_tep"]:
                self.assertTrue(Path(t["file"]).is_relative_to(self.nguon))
                self.assertEqual(Path(t["file"]).read_bytes(), xml_demo(h["key_raw"]["nbmst"]))
        self.assertEqual(phan_loai_file_tren_dia(run, m), ["ngoai-manifest.pdf"])

    def test_khong_cho_ghi_trong_nguon_ke_ca_thu_muc_con(self):
        truoc = cay_nguon(self.nguon)
        for ra in (self.nguon, self.nguon / "ra", self.root):
            with self.subTest(ra=ra), self.assertRaises(DataError) as cm:
                self.sinh(ra=ra)
            self.assertEqual(cm.exception.code, "M2_00_HOI_CUU_THU_MUC_RA_CHONG_NGUON")
        self.assertEqual(cay_nguon(self.nguon), truoc)

    def test_khong_ghi_de_manifest_da_co(self):
        run = self.sinh()
        p = run / "manifest.json"
        p.write_bytes(b"DEMO-da-ton-tai")
        with self.assertRaises(DataError) as cm:
            self.sinh()
        self.assertEqual(cm.exception.code, "M2_00_HOI_CUU_RUN_DA_CO_KHAC_NOI_DUNG")
        self.assertEqual(p.read_bytes(), b"DEMO-da-ton-tai")

    def test_nhieu_bang_ke_khong_tu_chon_hoac_bo_dong(self):
        bang_ke_demo(self.nguon / "bang_ke_purchase_2026-09_120000.xlsx")
        with self.assertRaises(DataError) as cm:
            self.sinh()
        self.assertEqual(cm.exception.code, "M2_00_HOI_CUU_NHIEU_BANG_KE_CUNG_CHIEU")
        self.assertFalse(self.ra.exists())

    def test_header_tieng_viet_va_thieu_header_bi_tu_choi(self):
        head = ["STT", "Ký hiệu mẫu số", "Ký hiệu HĐ", "Số HĐ", "Ngày lập", "MST người bán",
                *HEAD[6:]]
        bang_ke_demo(self.excel, head=head)
        self.assertEqual(doc_manifest(self.sinh())["tong"]["khong_xml_goc"], 1)
        head[5] = "DEMO-khong-ro"
        bang_ke_demo(self.excel, head=head)
        with self.assertRaises(DataError) as cm:
            self.sinh()
        self.assertEqual(cm.exception.code, "M2_00_HOI_CUU_BANG_KE_HEADER_KHONG_RO")

    def test_thu_muc_thang_hai_chieu_va_ban_ra(self):
        thang = self.root / "hai-chieu" / "2026-09"
        for chieu in ("mua_vao", "ban_ra"):
            goc = thang / chieu
            goc.mkdir(parents=True)
            (goc / "DEMO.xml").write_bytes(xml_demo())
            bang_ke_demo(goc / "bang_ke.xlsx", rows=[("0000000001", 7, 2)])
        run = self.sinh(thang, chieu="sold")
        m = doc_manifest(run)
        self.assertEqual(m["thu_muc_tep_goc"], str(thang / "ban_ra"))
        self.assertEqual(dem_doi_chieu(thang, m)["file_xml_tren_dia"], 1)
        p = lap_ke_hoach_nhan(run, ma_phap_nhan="DEMO")
        self.assertEqual(p["chieu"], "BAN_RA")
        self.assertEqual(len(p["muc"]), 1)

    def test_xml_rong_va_xml_thieu_khoa_khong_lam_mat_file(self):
        (self.nguon / "rong.xml").write_bytes(b"")
        (self.nguon / "thieu.xml").write_bytes(xml_demo().replace(b"<MST>0000000001</MST>", b""))
        run = self.sinh()
        m = doc_manifest(run)
        self.assertEqual(m["tong"]["xml_loi"], 2)
        self.assertTrue(any(h["key_thieu"] == ["nbmst"] for h in m["hoa_don"]))
        self.assertEqual(dem_doi_chieu(self.nguon, m)["file_xml_tren_dia"], 5)
        self.assertTrue(any(e["ma"] == "THIEU_KHOA" for e in lap_ke_hoach_nhan(run, ma_phap_nhan="DEMO")["ngoai_le"]))

    def test_nguon_phang_co_bang_ke_hai_chieu_khong_gan_nham_xml(self):
        bang_ke_demo(self.nguon / "bang_ke_sold_2026-09.xlsx")
        with self.assertRaises(DataError) as cm:
            self.sinh()
        self.assertEqual(cm.exception.code, "M2_00_HOI_CUU_NGUON_TRON_HAI_CHIEU")
        self.assertFalse(self.ra.exists())


if __name__ == "__main__":
    unittest.main()
