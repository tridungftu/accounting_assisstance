"""M4 bridge DEMO (R_REV): kết quả kiem_tra_dot #5 → hồ sơ NGHIEM_THU → xác nhận kế toán → đề xuất noncash → file soát.

Dữ liệu DEMO, người thao tác MO_PHONG_. Không chạy/import phần mềm #5, không dữ liệu thật."""

from __future__ import annotations

import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from kho_tri_thuc.de_xuat.nghiem_thu import NghiemThu
from kho_tri_thuc.giao_dien.quick import QuickPosting
from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.kiem_chung.fixtures import review_dot_fixture
from kho_tri_thuc.nguon.review_xay_dung import ReviewXayDungAdapter

ROOT = Path(__file__).resolve().parents[1]
DU = {"phap_nhan": "PLHN_FIXTURE", "ma_hd_chung": "HDXD-DEMO-0001", "du_an": "DA_DEMO_01", "doi_tuong": "NT_DEMO_01"}
SO = {"chap_nhan_truoc_vat": "115000000", "giu_lai_dot": "5750000", "thue_suat_vat": "8", "co_so": "TRUOC_VAT", "thu_hoi_tam_ung": "10000000"}


class _Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-nt-")
        self.app = LocalApp(ROOT / "cau_hinh.toml", Path(self.temp.name) / "web")

    def tearDown(self):
        self.temp.cleanup()

    def items(self, app=None):
        return (app or self.app).nt_list()["ho_so"]

    def by_review(self, ma):
        return next(h for h in self.items() if h["ma_review"] == ma)

    def receive(self, payload, name="review.json"):
        return self.app.nt_receive(canonical_json(payload).encode("utf-8"), name)

    def confirm_and_approve(self, item_id, mapping=DU, so=SO):
        self.app.nt_confirm({"id": item_id, "mapping": mapping, "so": so})
        return self.app.nt_decide({"id": item_id, "hanh_dong": "dong_y"})


class NhanVaLuuTests(_Base):
    def test_nhan_dung_shape_giu_raw_hash_provenance_va_restart(self):
        self.app.nt_seed("danh_muc")
        raw = self.app.nt_sample("review")
        report = self.app.nt_receive(raw, "review_MO_PHONG.json")
        self.assertEqual((report["state"], report["inserted_documents"]), ("COMMITTED", 1))
        [h] = self.items()
        self.assertEqual((h["trang_thai"], h["trang_thai_nguon"], h["ma_review"], h["dot"], h["ngay_nghiem_thu"]), ("WAIT", "DA_NAP_CSDL_REVIEW", "KTD-DEMO-0001", "3", "2026-09-18"))
        self.assertEqual(h["hash_raw"], sha256(raw))
        self.assertEqual(h["instance"], "REVIEW_XD_DEMO")
        self.assertEqual(h["de_nghi"]["minor"], "120000000")  # tiền qua API là chuỗi (lossless)
        tong_hop = {t["khoa"]: t for t in h["tong_hop"]}
        self.assertEqual(tong_hop["tt_ky_nay"]["minor"], None)  # không đọc được → NULL, không thành 0
        self.assertEqual(tong_hop["tt_ky_nay"]["goc"], "không đọc được")
        self.assertEqual(tong_hop["giu_lai"]["nhan"], "Giữ lại đợt (nguồn)")
        self.assertIn("tong_hop.tt_ky_nay", h["thieu"])
        self.assertIsNone(h["xac_nhan"])
        with Store(self.app.demo_config) as store:
            row = store.conn.execute("SELECT amount_minor,currency FROM documents WHERE kind='NGHIEM_THU'").fetchone()
            self.assertEqual((row[0], row[1]), (None, None))  # không có số chấp nhận trong nguồn → NULL
            raw_json = store.conn.execute("SELECT s.raw_json FROM evidence e JOIN source_records s ON s.id=e.source_record_id JOIN documents d ON d.id=e.document_id WHERE d.kind='NGHIEM_THU'").fetchone()[0]
            self.assertEqual(json.loads(raw_json), json.loads(raw))
            self.assertTrue(store.conn.execute("SELECT COUNT(*) FROM activity_log WHERE action='NT_NHAN'").fetchone()[0] >= 1)
        restarted = LocalApp(ROOT / "cau_hinh.toml", self.app.root)
        [again] = self.items(restarted)
        self.assertEqual((again["id"], again["hash_raw"]), (h["id"], h["hash_raw"]))

    def test_chi_nhan_kiem_tra_dot_demo_va_tu_choi_kho_that(self):
        rejected = self.receive({**review_dot_fixture(), "loai": "toan_ven"})
        self.assertEqual(rejected["state"], "REJECTED")
        self.assertIn("REVIEW_KIND", [i["code"] for i in rejected["issues"]])
        real_like = self.receive(review_dot_fixture(ma="KTD-0009"))
        self.assertIn("DEMO_ONLY", [i["code"] for i in real_like["issues"]])
        self.assertEqual(self.items(), [])
        config = Config.load(ROOT / "cau_hinh.toml", Path(self.temp.name) / "that")
        with self.assertRaises(DataError) as ctx:
            ReviewXayDungAdapter("X").read(canonical_json(review_dot_fixture()).encode(), replace(config, environment="that"))
        self.assertEqual(ctx.exception.code, "REVIEW_PRODUCTION_GATE")


class ChanVaXacNhanTests(_Base):
    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc")

    def test_chua_nap_hoac_thieu_mapping_so_vat_thi_chan_dong_y_va_xuat(self):
        self.app.nt_seed("review_chua_nap")
        h = self.by_review("KTD-DEMO-0002")
        self.assertEqual({c["ma"] for c in h["chan"]}, {"NGUON_CHUA_NAP", "CHUA_XAC_NHAN"})
        self.assertFalse(h["dong_y_duoc"])
        with self.assertRaises(DataError) as ctx:
            self.app.nt_decide({"id": h["id"], "hanh_dong": "dong_y"})
        self.assertEqual(ctx.exception.code, "NT_CHUA_DU_DIEU_KIEN")
        self.app.nt_seed("review")
        h = self.by_review("KTD-DEMO-0001")
        thieu = self.app.nt_confirm({"id": h["id"], "mapping": {**DU, "doi_tuong": None, "du_an": "DA_KHONG_CO"}, "so": {"chap_nhan_truoc_vat": "115000000"}})
        self.assertEqual({c["ma"] for c in thieu["chan"]}, {"MAPPING_DOI_TUONG", "MAPPING_DU_AN", "SO_VAT", "SO_GIU_LAI_CHUA_XAC_NHAN", "SO_THU_HOI_CHUA_XAC_NHAN"})
        self.assertIsNone(thieu["but_toan"])
        with self.assertRaises(DataError):
            self.app.nt_decide({"id": h["id"], "hanh_dong": "dong_y"})
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_RONG")
        with self.assertRaises(DataError) as ctx:
            self.app.nt_confirm({"id": h["id"], "mapping": DU, "so": {**SO, "chap_nhan_truoc_vat": 1.5}})
        self.assertEqual(ctx.exception.code, "NT_SO_KHONG_HOP_LE")

    def test_xac_nhan_du_tao_de_xuat_noncash_can_bang_va_file_soat(self):
        self.app.nt_seed("review")
        h = self.by_review("KTD-DEMO-0001")
        confirmed = self.app.nt_confirm({"id": h["id"], "mapping": DU, "so": SO})
        self.assertEqual(confirmed["chan"], [])
        lines = confirmed["but_toan"]
        self.assertTrue(all(isinstance(l["so_tien"], str) for l in lines))  # API lossless
        no = sum(int(l["so_tien"]) for l in lines if l["no_co"] == "N")
        co = sum(int(l["so_tien"]) for l in lines if l["no_co"] == "C")
        self.assertEqual((no, co), (115_000_000, 115_000_000))
        self.assertEqual({l["tai_khoan"] for l in lines}, {"2412_DEMO", "331_DEMO", "3388_DEMO"})
        self.assertTrue(all(l["doi_tuong"] == "NT_DEMO_01" and l["du_an"] == "DA_DEMO_01" for l in lines))
        giu_lai = next(l for l in lines if l["tai_khoan"] == "3388_DEMO")
        self.assertEqual(giu_lai["so_tien"], "5750000")
        self.assertIn("không phải bảo hành", giu_lai["dien_giai"])
        approved = self.app.nt_decide({"id": h["id"], "hanh_dong": "dong_y"})
        self.assertEqual(approved["trang_thai"], "APPROVE")
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({"muc_2": True})
        self.assertEqual(ctx.exception.code, "MUC_2_KHOA")
        result = self.app.nt_export({})
        name, raw = self.app.nt_file(result["id"])
        self.assertTrue(name.startswith("FILE-SOAT-NGHIEM-THU-"))
        wb = load_workbook(BytesIO(raw))
        ws = wb["FILE_SOAT_NGHIEM_THU"]
        headers = [c.value for c in ws[1]]
        rows = [dict(zip(headers, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["loai_chung_tu"] == "Nghiệm thu — không phát sinh thu/chi tiền" for r in rows))
        self.assertEqual(sorted(r["so_tien_vnd"] for r in rows), [5_750_000, 109_250_000, 115_000_000])  # số thường vẫn là số trong Excel
        self.assertEqual({r["thu_hoi_tam_ung_xac_nhan"] for r in rows}, {10_000_000})
        self.assertEqual({r["no_co"] for r in rows}, {"Nợ", "Có"})
        self.assertFalse(any("112" in str(r["tai_khoan"]) for r in rows))
        self.assertTrue(all("KTD-DEMO-0001" in r["nguon"] and r["nguoi_xac_nhan_so"] == "MO_PHONG_KE_TOAN" for r in rows))
        self.assertNotIn("Thu", {r["no_co"] for r in rows} | {"x"})
        self.assertIn("CANH_BAO", wb.sheetnames)
        wb.close()
        self.assertEqual(self.by_review("KTD-DEMO-0001")["trang_thai"], "EXPORTED")
        with self.assertRaises(DataError):
            self.app.nt_decide({"id": h["id"], "hanh_dong": "hoan_tac"})  # sau xuất không hoàn tác; phải điều chỉnh

    def test_but_toan_da_duyet_bi_sua_lech_thi_khong_xuat(self):
        self.app.nt_seed("review")
        h = self.by_review("KTD-DEMO-0001")
        self.confirm_and_approve(h["id"])
        with Store(self.app.demo_config) as store:
            lines = json.loads(store.conn.execute("SELECT decision_lines_json FROM quick_items WHERE id=?", (h["id"],)).fetchone()[0])
            lines[0]["so_tien"] += 1
            store.conn.execute("UPDATE quick_items SET decision_lines_json=? WHERE id=?", (canonical_json(lines), h["id"]))
            store.conn.commit()
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NO_CO_LECH")


class NhanLaiVaBanThayTests(_Base):
    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc")

    def test_nhan_lai_khong_trung(self):
        first = self.app.nt_seed("review")
        again = self.app.nt_seed("review")
        self.assertEqual((first["inserted_documents"], again["inserted_documents"], again["duplicate_documents"]), (1, 0, 1))
        self.assertEqual(len(self.items()), 1)

    def test_ban_thay_giu_quyet_dinh_cu_va_khong_ghi_cong_no_hai_lan(self):
        self.app.nt_seed("review")
        old = self.by_review("KTD-DEMO-0001")
        self.confirm_and_approve(old["id"])
        self.app.nt_seed("review_ban_thay")  # cùng HĐ/đợt, anh_huong khác, review mới hơn
        old, new = self.by_review("KTD-DEMO-0001"), self.by_review("KTD-DEMO-0001B")
        self.assertEqual(old["trang_thai"], "APPROVE")
        self.assertEqual(old["xac_nhan"]["so"]["chap_nhan_truoc_vat"], "115000000")  # đổi anh_huong không đổi số đã xác nhận
        self.assertIn("BAN_MOI_HON", {c["ma"] for c in old["chan"]})
        self.assertEqual((new["trang_thai"], new["thay_cho"]), ("WAIT", old["id"]))
        self.assertIsNone(new["xac_nhan"])  # số kế toán không tự chép sang bản mới
        self.assertEqual(new["goi_y_mapping"]["doi_tuong"], "NT_DEMO_01")
        self.app.nt_confirm({"id": new["id"], "mapping": DU, "so": SO})
        self.assertIn("BAN_KHAC_DANG_DUYET", {c["ma"] for c in self.by_review("KTD-DEMO-0001B")["chan"]})
        self.app.nt_decide({"id": old["id"], "hanh_dong": "hoan_tac"})
        self.app.nt_decide({"id": old["id"], "hanh_dong": "bo_qua", "ly_do": "Thay bằng review KTD-DEMO-0001B"})
        self.app.nt_decide({"id": new["id"], "hanh_dong": "dong_y"})
        self.app.nt_export({})
        self.receive(review_dot_fixture(ma="KTD-DEMO-0001C", luc="2026-09-22T08:00:00+07:00"))
        third = self.by_review("KTD-DEMO-0001C")
        self.assertIn("BAN_KHAC_DA_XUAT", {c["ma"] for c in third["chan"]})
        with self.assertRaises(DataError) as ctx:
            self.app.nt_confirm({"id": third["id"], "mapping": DU, "so": SO})
        self.assertEqual(ctx.exception.code, "NT_SU_KIEN_DA_XUAT")
        old = self.by_review("KTD-DEMO-0001")
        self.assertEqual((old["trang_thai"], old["xac_nhan"]["so"]["chap_nhan_truoc_vat"]), ("SKIP", "115000000"))

    def test_ban_cho_bi_thay_chuyen_bo_qua_va_ban_cu_den_muon(self):
        self.app.nt_seed("review_chua_nap")  # đợt 4, chưa nạp
        self.receive(review_dot_fixture(ma="KTD-DEMO-0002B", dot="4", luc="2026-09-21T08:00:00+07:00"))  # đã nạp, mới hơn
        old, new = self.by_review("KTD-DEMO-0002"), self.by_review("KTD-DEMO-0002B")
        self.assertEqual(old["trang_thai"], "SKIP")
        self.assertIn("Bị thay", old["ly_do"])
        self.assertEqual(new["thay_cho"], old["id"])
        self.receive(review_dot_fixture(ma="KTD-DEMO-0002A", dot="4", luc="2026-09-19T08:00:00+07:00"))  # cũ hơn, đến muộn
        self.assertEqual(self.by_review("KTD-DEMO-0002A")["trang_thai"], "SKIP")
        self.assertEqual(self.by_review("KTD-DEMO-0002B")["trang_thai"], "WAIT")


class AnToanVaHoiQuyTests(_Base):
    def test_actor_trang_thai_client_va_moi_truong_bi_chan(self):
        self.app.nt_seed("danh_muc"); self.app.nt_seed("review")
        h = self.by_review("KTD-DEMO-0001")
        for payload, code in (({"id": h["id"], "mapping": DU, "so": SO, "actor": "CFO_NTD"}, "ACTOR_SERVER_LOCKED"),
                              ({"id": h["id"], "mapping": DU, "so": SO, "but_toan": []}, "NT_CLIENT_STATE")):
            with self.assertRaises(DataError) as ctx:
                self.app.nt_confirm(payload)
            self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(DataError) as ctx:
            self.app.nt_confirm({"id": h["id"], "mapping": {**DU, "ma_junsky_la": "x"}, "so": SO})
        self.assertEqual(ctx.exception.code, "NT_TRUONG_LA")
        with Store(self.app.demo_config) as store:
            with self.assertRaises(DataError) as ctx:
                NghiemThu(store).quyet_dinh(h["id"], "dong_y", "CFO_NTD")
            self.assertEqual(ctx.exception.code, "ACTOR_MO_PHONG")
        that_config = replace(Config.load(ROOT / "cau_hinh.toml", Path(self.temp.name) / "kho-that"), environment="that")
        with Store(that_config) as store, self.assertRaises(DataError) as ctx:
            NghiemThu(store)
        self.assertEqual(ctx.exception.code, "NT_DEMO_ONLY")
        self.app.is_that = True
        with self.assertRaises(DataError) as ctx:
            self.app.nt_list()
        self.assertEqual(ctx.exception.code, "THAT_UI")

    def test_chuoi_nguon_giu_nguyen_la_du_lieu_va_giao_dien_khong_dung_innerhtml(self):
        self.app.nt_seed("danh_muc")
        payload = review_dot_fixture(ma="KTD-DEMO-XSS")
        payload["hop_dong"]["so_hd"] = "<img src=x onerror=alert(1)>"
        self.receive(payload)
        self.assertEqual(self.by_review("KTD-DEMO-XSS")["hop_dong"]["so_hd"], "<img src=x onerror=alert(1)>")
        script = (ROOT / "src" / "kho_tri_thuc" / "giao_dien" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)

    def test_luong_tien_quickposting_khong_dung_run_nghiem_thu(self):
        self.app.nt_seed("danh_muc"); self.app.nt_seed("review")
        with Store(self.app.demo_config) as store:
            run_id = store.conn.execute("SELECT id FROM quick_runs WHERE source_kind='NGHIEM_THU'").fetchone()[0]
            quick = QuickPosting(store)
            self.assertEqual([r for r in quick.runs() if r["id"] == run_id], [])
            for call in (lambda: quick.rows(run_id), lambda: quick.decide(run_id, [{"id": "x"}], "MO_PHONG_KE_TOAN", "2026-09-20T00:00:00Z"),
                         lambda: quick.repropose(run_id, "MO_PHONG_KE_TOAN")):
                with self.assertRaises(DataError) as ctx:
                    call()
                self.assertEqual(ctx.exception.code, "QUICK_PROFILE")


def _set_state(app, item_id, state):
    """Mô phỏng trạng thái cũ/đua (vd hai tab) để kiểm export tự kiểm lại trong giao dịch."""
    with Store(app.demo_config) as store:
        store.conn.execute("UPDATE quick_items SET state=? WHERE id=?", (state, item_id))
        store.conn.commit()


def _so_file_soat(app):
    with Store(app.demo_config) as store:
        return store.conn.execute("SELECT COUNT(DISTINCT files_json) FROM quick_exports e JOIN quick_runs r ON r.id=e.run_id WHERE r.source_kind='NGHIEM_THU'").fetchone()[0]


class SuKienDongTests(_Base):
    """P1: điều kiện cấp sự kiện tính động; một sự kiện chỉ xuất đầy đủ một lần."""

    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc"); self.app.nt_seed("review")
        self.a = self.by_review("KTD-DEMO-0001")["id"]

    def chan(self, ma):
        return {c["ma"] for c in self.by_review(ma)["chan"]}

    def test_dong_y_A_nhan_B_xuat_A_roi_B_khong_xuat_duoc(self):
        self.confirm_and_approve(self.a)
        self.app.nt_seed("review_ban_thay")
        b = self.by_review("KTD-DEMO-0001B")["id"]
        with self.assertRaises(DataError) as ctx:  # có bản mới hơn chưa xử lý → không xuất bản cũ (kiểm lại lúc xuất)
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_CHAN")
        self.assertEqual(_so_file_soat(self.app), 0)
        self.app.nt_decide({"id": b, "hanh_dong": "bo_qua", "ly_do": "Giữ bản A đã kiểm"})
        self.app.nt_export({})  # A xuất
        self.assertEqual(_so_file_soat(self.app), 1)
        _set_state(self.app, b, "WAIT")  # B bị đưa về chờ (trạng thái cũ/đua)
        self.assertIn("BAN_KHAC_DA_XUAT", self.chan("KTD-DEMO-0001B"))
        with self.assertRaises(DataError) as ctx:
            self.app.nt_confirm({"id": b, "mapping": DU, "so": SO})
        self.assertEqual(ctx.exception.code, "NT_SU_KIEN_DA_XUAT")
        with self.assertRaises(DataError):
            self.app.nt_decide({"id": b, "hanh_dong": "dong_y"})
        with Store(self.app.demo_config) as store:  # B mang xác nhận/bút toán hợp lệ như đã duyệt
            row = store.conn.execute("SELECT decision_json,decision_lines_json FROM quick_items WHERE id=?", (self.a,)).fetchone()
            store.conn.execute("UPDATE quick_items SET decision_json=?,decision_lines_json=? WHERE id=?", (row[0], row[1], b))
            store.conn.commit()
        _set_state(self.app, b, "APPROVE")  # trạng thái cũ/đua: export phải tự kiểm lại
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_CHAN")
        self.assertEqual(_so_file_soat(self.app), 1)
        self.assertEqual(self.by_review("KTD-DEMO-0001B")["trang_thai"], "APPROVE")  # không đổi trạng thái khi chặn

    def test_dong_y_A_nhan_B_hoan_tac_A_xuat_B_thi_A_khong_song_lai(self):
        self.confirm_and_approve(self.a)
        self.app.nt_seed("review_ban_thay")
        b = self.by_review("KTD-DEMO-0001B")["id"]
        self.app.nt_decide({"id": self.a, "hanh_dong": "hoan_tac"})
        self.assertIn("BAN_MOI_HON", self.chan("KTD-DEMO-0001"))
        with self.assertRaises(DataError):  # bản cũ không Đồng ý lại khi có bản mới hơn chưa bỏ qua
            self.app.nt_decide({"id": self.a, "hanh_dong": "dong_y"})
        self.confirm_and_approve(b)
        self.app.nt_export({})
        self.assertIn("BAN_KHAC_DA_XUAT", self.chan("KTD-DEMO-0001"))
        with self.assertRaises(DataError):
            self.app.nt_decide({"id": self.a, "hanh_dong": "dong_y"})
        with self.assertRaises(DataError) as ctx:
            self.app.nt_confirm({"id": self.a, "mapping": DU, "so": SO})
        self.assertEqual(ctx.exception.code, "NT_SU_KIEN_DA_XUAT")
        _set_state(self.app, self.a, "APPROVE")
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_CHAN")
        self.assertEqual(_so_file_soat(self.app), 1)

    def test_hai_ban_cung_da_dong_y_do_dua_thi_khong_xuat_ca_hai(self):
        self.app.nt_seed("review_ban_thay")
        b = self.by_review("KTD-DEMO-0001B")["id"]
        self.confirm_and_approve(b)
        _set_state(self.app, self.a, "APPROVE")
        with Store(self.app.demo_config) as store:  # A có xác nhận + bút toán như đã duyệt
            row = store.conn.execute("SELECT decision_json,decision_lines_json FROM quick_items WHERE id=?", (b,)).fetchone()
            store.conn.execute("UPDATE quick_items SET decision_json=?,decision_lines_json=? WHERE id=?", (row[0], row[1], self.a))
            store.conn.commit()
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_CHAN")
        self.assertEqual(_so_file_soat(self.app), 0)


class DaNapTests(_Base):
    """P1: `da_nap` phải là bằng chứng nạp đúng shape #5, đúng đợt, thời điểm đọc được."""

    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc")

    def test_bang_chung_nap_hong_giu_ho_so_nhung_chan(self):
        hop_le = {"luc": "2026-09-20T10:00:00", "dot": "3", "so_hang_muc": 12, "khong_khop": 1, "ghi_chu": "DEMO", "nap_lai": False}
        ca = {"rong": {}, "sai_dot": {**hop_le, "dot": "2"}, "luc_hong": {**hop_le, "luc": "khong-phai-thoi-diem"},
              "thieu_luc": {k: v for k, v in hop_le.items() if k != "luc"}, "sai_kieu": {**hop_le, "so_hang_muc": "12"}}
        for i, (ten, da_nap) in enumerate(ca.items()):
            payload = review_dot_fixture(ma=f"KTD-DEMO-NAP{i}", ma_hd=f"HD-DEMO-NAP{i}")
            payload["da_nap"] = da_nap
            with self.subTest(ca=ten):
                report = self.receive(payload)
                self.assertEqual(report["inserted_documents"], 1)  # hồ sơ/raw vẫn giữ
                h = self.by_review(f"KTD-DEMO-NAP{i}")
                self.assertEqual(h["trang_thai_nguon"], "BANG_CHUNG_NAP_KHONG_HOP_LE")
                self.assertTrue(h["da_nap_loi"])
                self.app.nt_confirm({"id": h["id"], "mapping": DU, "so": SO})
                self.assertEqual({c["ma"] for c in self.by_review(f"KTD-DEMO-NAP{i}")["chan"]}, {"NGUON_CHUA_NAP"})
                with self.assertRaises(DataError):
                    self.app.nt_decide({"id": h["id"], "hanh_dong": "dong_y"})
        with self.assertRaises(DataError) as ctx:
            self.app.nt_export({})
        self.assertEqual(ctx.exception.code, "NT_XUAT_RONG")

    def test_thoi_diem_nap_local_hoac_co_offset_hop_le(self):
        for i, luc in enumerate(("2026-09-20T10:00:00", "2026-09-20T10:00:00+07:00", "2026-09-20T03:00:00Z")):
            payload = review_dot_fixture(ma=f"KTD-DEMO-LUC{i}", ma_hd=f"HD-DEMO-LUC{i}")
            payload["da_nap"]["luc"] = luc
            self.receive(payload)
            h = self.by_review(f"KTD-DEMO-LUC{i}")
            self.assertEqual((h["trang_thai_nguon"], h["da_nap_loi"]), ("DA_NAP_CSDL_REVIEW", []))


class NullVaKhongTests(_Base):
    """P1: số giữ lại/thu hồi chưa xác nhận là NULL, không thành 0; 0 tường minh hợp lệ."""

    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc"); self.app.nt_seed("review")
        self.h = self.by_review("KTD-DEMO-0001")["id"]

    def test_giu_lai_null_chan_khong_dung_but_toan(self):
        view = self.app.nt_confirm({"id": self.h, "mapping": DU, "so": {**SO, "giu_lai_dot": None}})
        self.assertIn("SO_GIU_LAI_CHUA_XAC_NHAN", {c["ma"] for c in view["chan"]})
        self.assertIsNone(view["but_toan"])
        self.assertIsNone(view["xac_nhan"]["so"]["giu_lai_dot"])
        with self.assertRaises(DataError):
            self.app.nt_decide({"id": self.h, "hanh_dong": "dong_y"})
        view = self.app.nt_confirm({"id": self.h, "mapping": DU, "so": {**SO, "thu_hoi_tam_ung": ""}})
        self.assertIn("SO_THU_HOI_CHUA_XAC_NHAN", {c["ma"] for c in view["chan"]})

    def test_khong_tuong_minh_hop_le_va_ghi_ro_trong_file(self):
        view = self.app.nt_confirm({"id": self.h, "mapping": DU, "so": {**SO, "giu_lai_dot": "0", "thu_hoi_tam_ung": "0"}})
        self.assertEqual(view["chan"], [])
        self.assertEqual([(l["tai_khoan"], l["so_tien"]) for l in view["but_toan"]], [("2412_DEMO", "115000000"), ("331_DEMO", "115000000")])
        self.app.nt_decide({"id": self.h, "hanh_dong": "dong_y"})
        _, raw = self.app.nt_file(self.app.nt_export({})["id"])
        ws = load_workbook(BytesIO(raw))["FILE_SOAT_NGHIEM_THU"]
        col = [c.value for c in ws[1]].index("thu_hoi_tam_ung_xac_nhan")
        self.assertEqual({r[col].value for r in ws.iter_rows(min_row=2)}, {0})


class SoChinhXacTests(_Base):
    """P1/P2: số JSON đọc chính xác; hash phân biệt; tiền lớn không mất chữ số qua API và XLSX."""

    def setUp(self):
        super().setUp()
        self.app.nt_seed("danh_muc")

    def test_decimal_khong_gom_qua_float_va_hash_khac(self):
        base = canonical_json(review_dot_fixture(ma="KTD-DEMO-DEC"))
        self.assertIn('"de_nghi":120000000', base)
        r1 = self.app.nt_receive(base.replace('"de_nghi":120000000', '"de_nghi":1000000000000.00001').encode(), "dec1.json")
        r2 = self.app.nt_receive(base.replace('"de_nghi":120000000', '"de_nghi":1000000000000.0').encode(), "dec2.json")
        self.assertEqual((r1["inserted_documents"], r2["inserted_documents"]), (1, 1))  # hai giá trị khác → hai phiên bản, không trùng khóa
        views = [h for h in self.items() if h["ma_review"] == "KTD-DEMO-DEC"]
        de_nghi = sorted(((h["de_nghi"]["minor"], h["de_nghi"]["goc"]) for h in views), key=repr)
        self.assertEqual(de_nghi, sorted([(None, {"$so_thap_phan": "1000000000000.00001"}), ("1000000000000", "1000000000000")], key=repr))  # phần lẻ → NULL, giữ chuỗi chính xác
        self.assertEqual(len({h["hash_noi_dung"] for h in views}), 2)
        for bad, code in (('{"a":1,"a":2}', "DUPLICATE_JSON_KEY"), (base.replace('"de_nghi":120000000', '"de_nghi":NaN'), "INVALID_JSON")):
            report = self.app.nt_receive(bad.encode(), "bad.json")
            self.assertEqual(report["state"], "REJECTED")
            self.assertIn(code, [i["code"] for i in report["issues"]])

    def test_tien_lon_giu_chinh_xac_qua_api_va_xlsx(self):
        self.app.nt_seed("review")
        h = self.by_review("KTD-DEMO-0001")["id"]
        big = "100000000000000001"
        view = self.app.nt_confirm({"id": h, "mapping": DU, "so": {**SO, "chap_nhan_truoc_vat": big, "giu_lai_dot": "0", "thu_hoi_tam_ung": "0"}})
        self.assertEqual({l["so_tien"] for l in view["but_toan"]}, {big})
        self.assertEqual(view["xac_nhan"]["so"]["chap_nhan_truoc_vat"], big)
        self.app.nt_decide({"id": h, "hanh_dong": "dong_y"})
        result = self.app.nt_export({})
        self.assertEqual(result["tong_chap_nhan"], big)
        _, raw = self.app.nt_file(result["id"])
        ws = load_workbook(BytesIO(raw))["FILE_SOAT_NGHIEM_THU"]
        col = [c.value for c in ws[1]].index("so_tien_vnd")
        cells = [r[col] for r in ws.iter_rows(min_row=2)]
        self.assertEqual([(c.value, c.data_type) for c in cells], [(big, "s"), (big, "s")])  # không thành 1e+17
        script = (ROOT / "src" / "kho_tri_thuc" / "giao_dien" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("Number(v)", script)  # client không ép tiền qua Number
        self.assertIn("l.htmlFor = input.id", script)  # nhãn gắn với ô nhập


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-nt-http-")
        self.app = LocalApp(ROOT / "cau_hinh.toml", Path(self.temp.name) / "web")
        self.server = LocalServer(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.temp.cleanup()

    def call(self, path, body=None, token=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        headers = {"X-KTT-Token": self.app.token} if token else {}
        connection.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        status, raw = response.status, response.read()
        connection.close()
        return status, raw

    def test_luong_bam_qua_http_va_cac_chan_server(self):
        self.assertEqual(self.call("/api/nghiem-thu", token=False)[0], 403)
        self.assertEqual(self.call("/api/nghiem-thu/mau", {"mau": "review"}, token=False)[0], 403)
        for kind in ("danh_muc", "review"):
            status, raw = self.call("/api/nghiem-thu/mau", {"mau": kind})
            self.assertEqual(status, 200, raw)
        status, raw = self.call("/api/nghiem-thu")
        [h] = json.loads(raw)["ho_so"]
        status, raw = self.call("/api/nghiem-thu/xac-nhan", {"id": h["id"], "mapping": DU, "so": SO, "actor": "CFO_NTD"})
        self.assertEqual((status, json.loads(raw)["error"]), (400, "ACTOR_SERVER_LOCKED"))
        status, raw = self.call("/api/nghiem-thu/xac-nhan", {"id": h["id"], "mapping": DU, "so": {**SO, "chap_nhan_truoc_vat": "100000000000000001", "giu_lai_dot": "0"}})
        self.assertEqual(status, 200)
        self.assertIn(b'"chap_nhan_truoc_vat":"100000000000000001"', raw)  # JSON thô giữ chuỗi — JSON.parse không làm tròn
        self.assertNotIn(b":100000000000000001", raw)
        self.assertEqual(self.call("/api/nghiem-thu/quyet-dinh", {"id": h["id"], "hanh_dong": "dong_y"})[0], 200)
        status, raw = self.call("/api/nghiem-thu/xuat", {"muc_2": True})
        self.assertEqual((status, json.loads(raw)["error"]), (400, "MUC_2_KHOA"))
        status, raw = self.call("/api/nghiem-thu/xuat", {})
        self.assertEqual(status, 200, raw)
        status, content = self.call(f"/api/nghiem-thu/file-soat/{json.loads(raw)['id']}")
        self.assertEqual(status, 200)
        self.assertTrue(content.startswith(b"PK"))
        status, page = self.call("/")
        self.assertIn("Hồ sơ nghiệm thu".encode(), page)
        self.assertIn("<title>Hỗ trợ kế toán".encode(), page)
        self.assertNotIn("giao_tiep".encode(), page)


if __name__ == "__main__":
    unittest.main()
