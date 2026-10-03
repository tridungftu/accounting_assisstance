"""V3 source readers are exercised only with temporary synthetic files, never PLHN data."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.nguon.that import SourceMetadata, ThatAdapter

ROOT = Path(__file__).resolve().parents[1]
REUSE = Path(r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\bo_quy_tac")


def metadata(day="2026-08-31", **changes):
    return SourceMetadata(day, "2026-09-01T01:00:00+07:00", "synthetic unit-test receipt", "2026-08-01", "2026-09-01", **changes)


class ThatReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-that-")
        self.root = Path(self.temp.name)
        self.config = Config.load(ROOT / "cau_hinh.that.toml", self.root / "data")

    def tearDown(self):
        self.temp.cleanup()

    def test_xlsx_bank_reader_uses_header_labels_and_reingest_is_idempotent(self):
        path = self.root / "bank.xlsx"
        wb = Workbook(); ws = wb.active; ws.title = "LICH SU GIAO DICH"
        ws.append(["Tài khoản số: 0000123456"])
        ws.append(["STT", "Ngày", "Diễn giải", "Nợ", "Có", "Số dư", "Số giao dịch", "MTID"])
        ws.append([1, "31/08/2026", "synthetic payment", 100, 0, 900, "REF-001", "MTID-001"])
        wb.save(path); wb.close()
        adapter = ThatAdapter("sao_ke", path, metadata())
        with Store(self.config) as store:
            first = store.ingest(path, adapter)
            second = store.ingest(path, adapter)
            self.assertEqual(first["state"], "COMMITTED", first)
            self.assertEqual(second["inserted_documents"], 0)
            self.assertEqual(store.status()["environment"], "that")

    def test_xml_reader_reuses_v12_parser_and_emits_invoice_tax_contract(self):
        path = self.root / "invoice.xml"
        path.write_text("""<HDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26</KHHDon><SHDon>0001</SHDon><NLap>2026-08-31</NLap></TTChung><NBan><MST>0100000000</MST><Ten>Seller</Ten></NBan><NMua><MST>0700850958</MST><Ten>PLHN</Ten></NMua><TToan><TgTCThue>90</TgTCThue><TgTThue>10</TgTThue><TgTTTBSo>100</TgTTTBSo></TToan><DSHHDVu><HHDVu><STT>1</STT><THHDVu>service</THHDVu><ThTien>90</ThTien><TSuat>10%</TSuat><TThue>10</TThue></HHDVu></DSHHDVu></HDon>""", encoding="utf-8")
        adapter = ThatAdapter("hoa_don", path, metadata(), reuse_root=REUSE)
        batch = adapter.read(b"ignored", self.config)
        self.assertTrue(batch.valid, batch.issues)
        self.assertEqual(batch.records[0].core["tax_minor"], 10)
        self.assertEqual(batch.records[0].lines[0]["tax_rate"], "10")

    def test_xls_without_offline_xlrd_fails_explicitly(self):
        path = self.root / "bank.xls"; path.write_bytes(b"not-a-real-xls")
        adapter = ThatAdapter("sao_ke", path, metadata())
        # The workstation can have xlrd installed while the offline runtime
        # used in production does not.  Force the missing-wheel branch so the
        # assertion remains an input-contract test rather than an environment
        # probe.
        with patch.dict("sys.modules", {"xlrd": None}):
            with self.assertRaises(DataError) as error:
                adapter.read(path.read_bytes(), self.config)
        self.assertEqual(error.exception.code, "XLRD_OFFLINE_WHEEL_MISSING")

    def test_base_vnd_and_open_item_reader_keep_declared_snapshot(self):
        base = self.root / "base"; base.mkdir()
        (base / "request.json").write_text('{"ma_de_nghi":"REQ-1","so_tien":"669600 vnd","ngay_duyet":"2026-08-31","trang_thai":"approved"}', encoding="utf-8")
        adapter = ThatAdapter("base", base, metadata())
        batch = adapter.read(b"ignored", self.config)
        self.assertTrue(batch.valid, batch.issues)
        self.assertEqual(batch.records[0].amount_minor, 669600)
        folder = self.root / "DANH MUC"; folder.mkdir()
        path = folder / "Danh sách chứng từ công nợ.xlsx"
        wb = Workbook(); ws = wb.active
        ws.append(["Chứng từ công nợ", "Ngày", "Đối tượng", "Tài khoản", "Số tiền (HT)", "Mã dự án", "Ký hiệu hđ", "Số hóa đơn", "Ngày hóa đơn", "Nội dung", "Hợp đồng vay"])
        ws.append(["DEBT-1", "31/08/2026", "PARTY-1", "331", -100, "P-1", "C26", "0001", "31/08/2026", "synthetic", "LOAN-1"])
        wb.save(path); wb.close()
        junsky = ThatAdapter("junsky", folder, metadata(snapshot_id="DECLARED-SNAPSHOT"))
        batch = junsky.read(b"ignored", self.config)
        self.assertTrue(batch.valid, batch.issues)
        self.assertEqual(batch.records[0].core["snapshot_id"], "DECLARED-SNAPSHOT")
        self.assertTrue(any(issue.code == "OUTSIDE_CATALOG_CODE" for issue in batch.issues))


if __name__ == "__main__":
    unittest.main()
