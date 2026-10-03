"""V7 readers use only temporary synthetic files shaped like the observed layouts."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.cli import parser
from kho_tri_thuc.nguon.that import SourceMetadata, ThatAdapter
from kho_tri_thuc.tri_thuc.human_workbook import HumanKnowledgeWorkbook


ROOT = Path(__file__).resolve().parents[1]


def metadata(**changes):
    defaults = dict(as_of="2026-08-31", exported_at="2026-09-02T01:00:00+07:00", known_at_basis="synthetic V7 test",
                    coverage_from="2026-08-01", coverage_to_exclusive="2026-09-01", snapshot_id="SYNTHETIC_V7",
                    posting_evidence_complete=True)
    defaults.update(changes)
    return SourceMetadata(**defaults)


class V7ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-v7-synthetic-")
        self.root = Path(self.temp.name)
        self.config = Config.load(ROOT / "cau_hinh.that.toml", self.root / "that")

    def tearDown(self):
        self.temp.cleanup()

    def _bank_workbook(self, path: Path):
        wb = Workbook(); ws = wb.active; ws.title = "LICH SU GIAO DICH"
        ws.append(["Số tài khoản/ Account No.:", "0000123456"])
        ws.append(["Số dư đầu kỳ/Opening Balance:", 100])
        ws.append(["Tổng giá trị ghi có/ Total credits:", 50])
        ws.append(["Tổng giá trị ghi nợ/ Total debits:", 20])
        ws.append(["Tổng số giao dịch ghi có/Total number of credit :", 1])
        ws.append(["Tổng số giao dịch ghi nợ/Total number of debits:", 1])
        ws.append(["Số dư cuối kỳ/Closing Balance:", 130])
        ws.append(["Chu kỳ yêu cầu/From date- to date:", "01/08/2026-31/08/2026"])
        ws.append(["STT/No.", "Ngày hạch toán/Accounting date", "Mô tả giao dịch/ Transaction description", "Nợ/ Debit", "Có / Credit", "Số dư TK/ Account Balance", "Số giao dịch/ Transaction number", "Số tài khoản đối ứng/ Corresponsive account", "Tên tài khoản đối ứng/ Corresponsive name", "MTID/ CITAD", "Mã định danh TK thụ hưởng/ To virtual account", "Ngày phát sinh giao dịch/ Transaction date"])
        ws.append([0, "01-08-2026 08:00:00", "synthetic credit", 0.0, 50.0, 150.0, "REF-C", "0009", "Synthetic", "M-1", None, "01-08-2026 08:00:00"])
        ws.append([None, "02-08-2026 09:00:00", "synthetic debit", 20.0, 0.0, 130.0, "REF-D", "0008", "Synthetic", "M-2", None, "02-08-2026 09:00:00"])
        ws.append([None, "footer", "not a transaction"])
        wb.save(path); wb.close()

    def test_efast_bilingual_headers_controls_and_xls_fallback_are_synthetic(self):
        xlsx = self.root / "bank.xlsx"; self._bank_workbook(xlsx)
        batch = ThatAdapter("sao_ke", xlsx, metadata()).read(b"", self.config)
        self.assertTrue(batch.valid, batch.issues)
        self.assertEqual(len(batch.records), 2)
        self.assertEqual(batch.records[0].core["account"], "0000123456")
        self.assertIn("mtid_citad", batch.records[0].core)
        self.assertEqual(batch.controls["bank"]["net_minor"], 30)
        xls = self.root / "bank.xls"; xls.write_bytes(b"synthetic placeholder; reader must choose adjacent xlsx")
        # Do not let a developer's locally installed xlrd change this
        # fallback-contract test.  The adjacent .xlsx is the prescribed
        # behavior when the approved offline wheel is unavailable.
        with patch.dict("sys.modules", {"xlrd": None}):
            fallback = ThatAdapter("sao_ke", xls, metadata()).read(b"", self.config)
        self.assertTrue(fallback.valid)
        self.assertEqual([(r.key, r.amount_minor) for r in fallback.records], [(r.key, r.amount_minor) for r in batch.records])
        self.assertTrue(any(issue.code == "XLRD_OFFLINE_WHEEL_MISSING" for issue in fallback.issues))

    def test_xml_and_gateway_share_key_model_two_and_keep_source_mismatch_warning(self):
        xml = self.root / "2K26-0007.xml"
        xml.write_text(f"""<HDon><TTChung><KHMSHDon>2</KHMSHDon><KHHDon>K26</KHHDon><SHDon>0007</SHDon><NLap>2026-08-20</NLap></TTChung><NBan><MST>SELLER_SYN</MST></NBan><NMua><MST>{self.config.entity_tax_id}</MST></NMua><TToan><TGTKhac>0.000000</TGTKhac><TgTTTBSo>90000.000000</TgTTTBSo></TToan><TTHDLQuan><TCHDon>1</TCHDon><KHMSHDCLQuan>1</KHMSHDCLQuan><KHHDCLQuan>C26</KHHDCLQuan><SHDCLQuan>0001</SHDCLQuan><NLHDCLQuan>2026-01-01</NLHDCLQuan></TTHDLQuan></HDon>""", encoding="utf-8")
        xml_batch = ThatAdapter("hoa_don", xml, metadata()).read(b"", self.config)
        self.assertTrue(xml_batch.valid, xml_batch.issues)
        self.assertEqual(xml_batch.records[0].core["tax_status"], "NO_VAT_MODEL_2")
        self.assertEqual(xml_batch.records[0].core["number"], "7")
        self.assertEqual(xml_batch.records[0].core["related_invoice"]["series"], "C26")
        table = self.root / "gateway.xlsx"; wb = Workbook(); ws = wb.active
        ws.append(["STT", "Ky hieu mau so", "Ky hieu HD", "So HD", "Ngay lap", "MST nguoi ban", "Ten nguoi ban", "MST nguoi mua", "Ten nguoi mua", "So giay to (CCCD)", "Tien chua thue", "Tien thue", "Tong thanh toan", "Don vi tien te", "Trang thai"])
        ws.append([1, 2, "K26", 7, "20/08/2026", "SELLER_SYN", "Synthetic", self.config.entity_tax_id, "Synthetic", "", "", "", 90000, "VND", 1])
        wb.save(table); wb.close()
        table_batch = ThatAdapter("bang_ke", table, metadata()).read(b"", self.config)
        self.assertTrue(table_batch.valid, table_batch.issues)
        self.assertEqual(xml_batch.records[0].key, table_batch.records[0].key)

    def test_base_new_json_and_quarantine_commit_under_configured_ratio(self):
        base = self.root / "base"; base.mkdir(); good = base / "request_SYN001"; good.mkdir(); bad = base / "request_SYN002"; bad.mkdir()
        payload = {"get": {"request": {"id": "SYN001", "name": "Synthetic", "status": "approved", "state": "done", "last_update": 1788138000, "form": [{"id": "tong_thanh_tien", "value": "100 vnd"}, {"id": "du_an", "value": "P_SYN"}, {"id": "chi_phi", "value": "E_SYN"}]}}, "custom_table": {"custom_table": {"custom_tai_khoan_thu_huong": {"headers": ["Số tài khoản"], "data": [["00001234"]]}, "custom_b_k_c_t": {"headers": ["Số hóa đơn"], "data": [["7"]]}}}, "_attachment_results": [{"name": "synthetic.pdf", "size": 1}], "fetched_at": "2026-09-01T00:00:00+07:00"}
        (good / "request_SYN001.json").write_text(json.dumps(payload), encoding="utf-8")
        payload["get"]["request"]["id"] = "SYN002"; payload["get"]["request"]["form"] = []
        (bad / "request_SYN002.json").write_text(json.dumps(payload), encoding="utf-8")
        batch = ThatAdapter("base", base, metadata()).read(b"", self.config)
        self.assertTrue(batch.valid, batch.issues)
        self.assertEqual((len(batch.raw_records), len(batch.records)), (2, 2))
        with Store(replace(self.config, quarantine_max_ratio=0.6)) as store:
            report = store.ingest(base, ThatAdapter("base", base, metadata()))
            self.assertEqual(report["state"], "COMMITTED", report)
            self.assertEqual(report["quarantine"]["by_code"], {"BASE_AMOUNT_MISSING": 1})
            self.assertEqual(store.quarantined(report["attempt_id"])["count"], 1)

    def test_junsky_two_header_rows_pair_journal_and_all_roles(self):
        folder = self.root / "DANH MỤC"; folder.mkdir()
        def book(name, headers, rows, prefix=()):
            wb = Workbook(); ws = wb.active
            for row in prefix: ws.append(row)
            ws.append(headers)
            for row in rows: ws.append(row)
            wb.save(folder / name); wb.close()
        book("Danh mục khách hàng PLHN 2026-09-01.xlsx", ["", "Mã đối tượng", "Tên đối tượng", "Mã số thuế"], [[None, "CP_SYN", "Synthetic", "TAX_SYN"]])
        book("Khoản mục chi phí.xlsx", ["Mã chi phí", "Tên chi phí"], [["E_SYN", "Synthetic"]])
        book("Mã dự án.xlsx", ["Mã dự án", "Tên dự án"], [["P_SYN", "Synthetic"]])
        book("Trung tâm chi phí.xlsx", ["Mã TTCP", "Tên TTCP"], [["C_SYN", "Synthetic"]])
        book("Bảng cân đối phát sinh.xlsx", ["Nhóm", "Mã tài khoản", "Tên tài khoản", "Tính chất"], [["N", "331", "Synthetic", "Có"]], prefix=[["report"], ["as of"]])
        book("Danh sách chứng từ công nợ.xlsx", ["Mã đơn vị", "Chứng từ công nợ", "Mã NV", "Ngày", "Đối tượng", "Tài khoản", "Số tiền (HT)", "Mã dự án", "Ký hiệu HD", "Số hóa đơn"], [["U_SYN", "DEBT_SYN", "NV_SYN", "01/01/2026", "CP_SYN", "331", 100, "P_SYN", "K26", 7]])
        book("dgbList.xlsx", ["Mã đơn vị", "Mã NV", "Số chứng từ", "Ngày c.từ", "Số hóa đơn", "Nội dung", "Ghi nợ", "Ghi có", "Số tiền", "Mã đối tượng", "Tên đối tượng", "Mã dự án", "Tên dự án", "Mã TTCP"], [["U_SYN", "NV_SYN", "V_SYN", "20/08/2026", 7, "Synthetic", "6427", "331", 100, "CP_SYN", "Synthetic", "P_SYN", "Synthetic", "C_SYN"]], prefix=[["report"], ["as of"]])
        batch = ThatAdapter("junsky", folder, metadata(coverage_from="2026-01-01")).read(b"", self.config)
        self.assertTrue(batch.valid, batch.issues)
        kinds = {record.kind for record in batch.records}
        self.assertTrue({"OPEN_ITEM", "COUNTERPARTY", "EXPENSE", "PROJECT", "COST_CENTER", "ACCOUNT", "JOURNAL"} <= kinds)
        item = next(record for record in batch.records if record.kind == "OPEN_ITEM")
        self.assertEqual(item.amount_minor, -100)
        journal = next(record for record in batch.records if record.kind == "JOURNAL")
        self.assertEqual(len(journal.lines), 2)

    def test_workbook_decision_is_explicit_and_dry_run_does_not_approve(self):
        source = self.root / "BO-QUY-TAC.xlsx"; wb = Workbook(); ws = wb.active; ws.title = "Quy tắc"
        ws.append(["ma_quy_tac", "bac", "loai_khoa", "chieu", "stk_doi_ung", "ten_doi_ung", "tu_khoa", "tk_doi_ung", "ma_doi_tuong", "ma_du_an", "so_lan_gap", "so_lan_dung", "do_on_dinh", "lan_dau", "lan_cuoi", "han_dung", "trang_thai"])
        ws.append(["RULE_SYN", "2", "STK", "CHI", "00001234", "", "", "6427", "CP_SYN", "P_SYN", 1, 1, 1, "2026-01-01", "2026-08-01", "2026-12-31", "DE_CU"])
        for name, headers in (("Ánh xạ STK", ["stk_doi_ung", "ma_doi_tuong", "trang_thai"]), ("DM Đối tượng", ["ma", "ten"]), ("DM Tài khoản", ["ma", "ten"]), ("DM Khoản mục CP", ["ma", "ten"]), ("DM Dự án", ["ma", "ten"]), ("DM Trung tâm CP", ["ma", "ten"])):
            wb.create_sheet(name).append(headers)
        wb.save(source); wb.close()
        with Store(self.config) as store:
            service = HumanKnowledgeWorkbook(store)
            service.import_sources([source], "IMPORTER", "2026-09-10T00:00:00Z")
            human = self.root / "human.xlsx"; service.export_human_workbook(human, "IMPORTER", "2026-09-10T00:01:00Z")
            wb = load_workbook(human); sheet = wb["MAU_DINH_KHOAN"]; columns = {cell.value: cell.column for cell in sheet[1]}
            sheet.cell(2, columns["quyet_dinh"], "APPROVE"); wb.save(human); wb.close()
            self.assertEqual(service.apply_human_decisions(human, "CFO_SYN", "2026-09-10T00:02:00Z", dry_run=True)["approved"], 1)
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM knowledge_events").fetchone()[0], 0)
            self.assertEqual(service.apply_human_decisions(human, "CFO_SYN", "2026-09-10T00:02:00Z")["approved"], 1)
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM knowledge_events WHERE action='APPROVE'").fetchone()[0], 1)

    def test_v7_operational_commands_are_exposed_with_required_identifiers(self):
        commands = parser()
        self.assertEqual(commands.parse_args(["duyet-tri-thuc", "review.xlsx", "--actor", "CFO_SYN", "--at", "2026-09-10T00:00:00Z"]).command, "duyet-tri-thuc")
        self.assertEqual(commands.parse_args(["xem-cach-ly", "--attempt-id", "ATTEMPT_SYN", "--output", "out.json"]).command, "xem-cach-ly")
        self.assertEqual(commands.parse_args(["liet-ke-sao-ke", "--tu", "2026-08-01", "--den", "2026-08-31", "--output", "out.json"]).command, "liet-ke-sao-ke")
        self.assertEqual(commands.parse_args(["mo-phien-that", "--attempt-id", "ATTEMPT_SYN", "--tu", "2026-08-01", "--den", "2026-08-31", "--cutoff", "2026-09-10T00:00:00Z", "--actor", "OPERATOR_SYN"]).mode, "shadow")


if __name__ == "__main__":
    unittest.main()
