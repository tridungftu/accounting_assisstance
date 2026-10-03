"""V4 keeps all imported knowledge pending until a separate human approval command."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from test_modules import FeatureCase
from kho_tri_thuc.tri_thuc.human_workbook import HumanKnowledgeWorkbook


class V4HumanKnowledgeTests(FeatureCase):
    def _source(self):
        path = self.root / "BO-QUY-TAC.xlsx"
        wb = Workbook(); ws = wb.active; ws.title = "Quy tắc"
        ws.append(["ma_quy_tac", "bac", "loai_khoa", "chieu", "stk_doi_ung", "ten_doi_ung", "tu_khoa", "tk_doi_ung", "ma_doi_tuong", "ma_du_an", "so_lan_gap", "so_lan_dung", "do_on_dinh", "lan_dau", "lan_cuoi", "han_dung", "trang_thai"])
        ws.append(["R-1", "2", "STK", "CHI", "00009999", None, None, "6427", "P-1", "PROJECT-1", 4, 4, "1", "2026-01-01", "2026-08-01", "2026-12-31", "DE_CU"])
        for name, headers in (("Ánh xạ STK", ["stk_doi_ung", "ma_doi_tuong", "trang_thai"]), ("DM Đối tượng", ["ma", "ten"]), ("DM Tài khoản", ["ma", "ten"]), ("DM Khoản mục CP", ["ma", "ten"]), ("DM Dự án", ["ma", "ten"]), ("DM Trung tâm CP", ["ma", "ten"])):
            sheet = wb.create_sheet(name); sheet.append(headers)
        wb.save(path); wb.close(); return path

    def test_import_pending_export_roundtrip_and_review_request(self):
        service = HumanKnowledgeWorkbook(self.store)
        report = service.import_sources([self._source()], "IMPORTER", "2026-09-16T01:00:00Z")
        self.assertEqual(report["imported"], 1)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM knowledge_events").fetchone()[0], 0)
        path = self.root / "knowledge-human.xlsx"
        exported = service.export_human_workbook(path, "IMPORTER", "2026-09-16T01:01:00Z")
        self.assertEqual(exported["approved"], 0)
        self.assertEqual(service.import_review_requests(path, "REVIEWER", "2026-09-16T01:02:00Z")["events"], 0)
        wb = load_workbook(path); sheet = wb["MAU_DINH_KHOAN"]
        columns = {cell.value: cell.column for cell in sheet[1]}
        sheet.cell(2, columns["Anh duyệt"], "YÊU CẦU DUYỆT")
        wb.save(path); wb.close()
        result = service.import_review_requests(path, "REVIEWER", "2026-09-16T01:03:00Z")
        self.assertEqual(result["events"], 1)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM knowledge_events").fetchone()[0], 0)
        self.assertEqual(self.store.conn.execute("SELECT action FROM knowledge_review_requests").fetchone()[0], "APPROVE_REQUEST")

    def test_changed_operational_columns_are_rejected(self):
        service = HumanKnowledgeWorkbook(self.store)
        service.import_sources([self._source()], "IMPORTER", "2026-09-16T01:00:00Z")
        path = self.root / "knowledge-human.xlsx"; service.export_human_workbook(path, "IMPORTER", "2026-09-16T01:01:00Z")
        wb = load_workbook(path); sheet = wb["MAU_DINH_KHOAN"]
        columns = {cell.value: cell.column for cell in sheet[1]}; sheet.cell(2, columns["TK"], "CHANGED")
        wb.save(path); wb.close()
        # V4 must reject this after the baseline check is enforced below.
        from kho_tri_thuc.ha_tang.primitives import DataError
        with self.assertRaises(DataError):
            service.import_review_requests(path, "REVIEWER", "2026-09-16T01:02:00Z")
