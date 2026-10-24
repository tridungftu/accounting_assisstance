"""V13 A4 + A5 — lỗi bộ chuyển không lộ dữ liệu; đối chiếu nội dung thực nguồn/đích (dữ liệu DEMO, actor MO_PHONG_).

Phần không cần máy chủ: biên lỗi CLI (kết nối, migrate, đóng, mở nguồn, argparse), vân tay K2 dựng độc lập từ nguồn so với
MỌI cột nghiệp vụ đã ánh xạ ở đích (mutation từng cột trong khi JSON giữ nguyên), hash bảng V12 tách khóa do migration thêm.
Phần cần PostgreSQL (KHO_PG_DSN_TEST + psycopg, không có thì skip): chạy thật hai tool trên CSDL tạm."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang import database
from kho_tri_thuc.ha_tang.ket_noi import DAU_NAP_XONG
from kho_tri_thuc.ha_tang.primitives import canonical_json, sha256
from kho_tri_thuc.ha_tang.sao_chep_bang import _cot_sqlite, doi_chieu_noi_dung, van_tay_sqlite

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
BI_MAT = "MO_PHONG_BI_MAT_0912345678"  # chuỗi DEMO "nhạy cảm": không được xuất hiện ở stdout/stderr/báo cáo
T = "2026-09-01T00:00:00Z"
COT_DONG_KHONG_ANH_XA = ("mo_ta", "so_luong", "don_gia_minor", "tien_truoc_thue_minor", "thue_suat", "tien_thue_minor", "doi_tac_id",
                         "doi_tac_junsky", "du_an_id", "du_an_junsky", "ttcp", "khoan_muc", "dich")


def _tool(name: str):
    spec = importlib.util.spec_from_file_location(f"_tool_{name}", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _core(obj) -> tuple[str, str]:
    text = canonical_json(obj)
    return text, sha256(text.encode())


def tao_kho_demo(path: Path, *, ngay_bank: str = "2026-09-02", day_du: bool = True) -> None:
    """kho.sqlite V12 DEMO hợp lệ khóa ngoại: đối tác có/không MST, dự án, JOURNAL 2 dòng, BANK có bản ghi nguồn + trạng thái
    quick_items; day_du thêm OPEN_ITEM + hai phiên bản tri thức (bản 2 thay bản 1, có sự kiện duyệt)."""
    conn = database.connect(path)
    try:
        conn.execute("BEGIN")
        conn.execute("INSERT INTO workspace_meta VALUES ('entity_id', '\"PLHN_FIXTURE\"')")
        conn.execute("INSERT INTO config_history VALUES (?,?,?)", ("c" * 64, b"DEMO", T))
        conn.execute("INSERT INTO artifacts VALUES (?,?,?,?)", ("a" * 64, f"raw/{'a' * 64}.bin", 4, T))
        conn.execute("INSERT INTO attempts (id, artifact_hash, original_name, config_hash, parser_version, state, started_at) VALUES ('AT1',?,'demo.json',?,'demo','COMMITTED',?)",
                     ("a" * 64, "c" * 64, T))
        conn.execute("INSERT INTO source_records VALUES ('SR1',?,'$.records[0]',?)", ("a" * 64, json.dumps({"mo_ta": "MO_PHONG_SAO_KE", "so_tien": "100"})))
        docs = [("DC1", "COUNTERPARTY", "DT_DEMO_1", "2026-01-01", None, {"code": "331.MO_PHONG_NCC", "name": "MO_PHONG NCC", "tax_id": "0100000001"}),
                ("DC2", "COUNTERPARTY", "DT_DEMO_2", "2026-01-01", None, {"code": "331.MO_PHONG_LE", "name": "MO_PHONG LE"}),
                ("DP1", "PROJECT", "DA_DEMO_1", "2026-01-01", None, {"code": "KCN-DEMO", "name": "MO_PHONG DU AN"}),
                ("DJ1", "JOURNAL", "NK_DEMO_1", "2026-09-01", 100, {"description": "MO_PHONG_BUT_TOAN", "voucher_type": "BP", "voucher_number": "BP_DEMO_1",
                                                                   "counterparty": "331.MO_PHONG_NCC", "project": "KCN-DEMO"}),
                ("DB1", "BANK", "SK_DEMO_1", ngay_bank, -100, {"description": "MO_PHONG_CHI", "counterparty_name": "MO_PHONG_DOI_TAC"})]
        if day_du:
            docs.append(("DO1", "OPEN_ITEM", "CN_DEMO_1", "2026-08-31", 50, {"account": "331", "item_type": "INVOICE", "counterparty": "331.MO_PHONG_LE",
                                                                             "project": "KCN-DEMO", "transaction_code": "MO_PHONG_NV", "document_date": "2026-08-01",
                                                                             "invoice_date": "2026-08-02"}))
        for doc_id, kind, key, day, amount, core in docs:
            text, digest = _core(core)
            conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)", (doc_id, "PLHN_FIXTURE", kind, key, day, "VND", amount, text, digest, "AT1"))
        for n, (acct, debit, credit) in enumerate((("6427", 100, 0), ("1121", 0, 100)), 1):
            text, digest = _core({"line_key": str(n), "account": acct, "debit_minor": debit, "credit_minor": credit, "amount_minor": debit or credit})
            conn.execute("INSERT INTO document_lines VALUES (?,?,?,?,?,?)", (f"L{n}", "DJ1", str(n), debit or credit, text, digest))
        conn.execute("INSERT INTO evidence (document_id, source_record_id, scope_key, known_at, known_at_basis, attempt_id) VALUES ('DB1','SR1','doc',?,'DEMO','AT1')", (T,))
        conn.execute("INSERT INTO quick_runs (id, source_attempt_id, source_kind, created_at, actor) VALUES ('QR1','AT1','sao_ke',?,'MO_PHONG_KT')", (T,))
        conn.execute("INSERT INTO quick_items (id, run_id, document_id, proposal_json, state) VALUES ('QI1','QR1','DB1','{}','APPROVE')")
        if day_du:
            p1, h1 = _core({"tu_khoa": "MO_PHONG_TU_KHOA", "tk": "6427"})
            p2, h2 = _core({"tu_khoa": "MO_PHONG_TU_KHOA", "tk": "6428"})
            conn.execute("INSERT INTO knowledge_versions VALUES ('KV1','KEYWORD','MO_PHONG_K',1,?,?,'2026-01-01',NULL,?,'[]',NULL,?,'MO_PHONG_KT')", (p1, h1, T, T))
            conn.execute("INSERT INTO knowledge_versions VALUES ('KV2','KEYWORD','MO_PHONG_K',2,?,?,'2026-02-01',NULL,?,'[\"MO_PHONG_CC\"]','KV1',?,'MO_PHONG_KT')",
                         (p2, h2, "2026-09-02T01:02:03Z", "2026-09-02T01:02:03Z"))
            conn.execute("INSERT INTO knowledge_events (version_id, action, event_at, actor, reason) VALUES ('KV2','APPROVE','2026-09-03T00:00:00Z','MO_PHONG_CFO','DEMO')")
        conn.execute("INSERT INTO activity_log(module,action,subject_id,actor,event_at,recorded_at,details_json) VALUES ('M1','DEMO','s','MO_PHONG_KT',?,?,'{}')", (T, T))
        conn.commit()
    finally:
        conn.close()


def _utc(s):
    return None if s is None else datetime.fromisoformat(s.replace("Z", "+00:00") if "T" in s else s + "T00:00:00+00:00")


def mo_phong_dich(src: sqlite3.Connection) -> dict:
    """Dòng đích như bộ chuyển K2 ghi, cùng tên cột với doc_dich (kiểu PostgreSQL: date/datetime UTC, char(3)) — thay PostgreSQL
    trong test không máy chủ. Khóa ngoại trả về dạng join: MST/ghi chú đối tác, mã dự án, hash tệp gốc, _sqlite_id bản bị thay."""
    doi_tac = {}
    for doc_id, core in src.execute("SELECT id, core_json FROM documents WHERE kind='COUNTERPARTY'"):
        d = json.loads(core)
        doi_tac[d["code"]] = {"co_doi_tac": True, "dt_mst": d.get("tax_id"), "dt_ghi_chu": f"_sqlite_id:{doc_id}"}
    khong = {"co_doi_tac": False, "dt_mst": None, "dt_ghi_chu": None}
    du_an = {json.loads(c)["code"] for (c,) in src.execute("SELECT core_json FROM documents WHERE kind='PROJECT'")}
    raw = {r[0]: (json.loads(r[1]), r[2]) for r in src.execute("SELECT e.document_id, s.raw_json, s.artifact_hash FROM evidence e JOIN source_records s ON s.id = e.source_record_id")}
    trang_thai = {"APPROVE": "DA_DUYET", "WAIT": "CHO_DUYET"}
    state = {r[0]: trang_thai[r[1]] for r in src.execute("SELECT document_id, state FROM quick_items")}
    rows = {"kho.chung_tu": [], "kho.chung_tu_dong": [], "kho.cong_no_mo": [], "kho.tri_thuc": []}
    for doc_id, kind, key, day, cur, amount, core, digest in src.execute(
            "SELECT id, kind, natural_key, business_date, currency, amount_minor, core_json, core_hash FROM documents WHERE kind IN ('JOURNAL','BANK','OPEN_ITEM')"):
        d = json.loads(core)
        if kind == "OPEN_ITEM":
            rows["kho.cong_no_mo"].append({"du_lieu": d | {"_sqlite_id": doc_id}, "ngay_chup": date.fromisoformat(day), "tai_khoan": d["account"],
                                           "doi_tac_junsky": d["counterparty"], "item_key": key, "loai": d["item_type"], "so_tien_minor": amount,
                                           "con_lai_minor": amount, "tien_te": cur, "hoa_don_ref": d["transaction_code"], "du_an_junsky": d["project"],
                                           "ngay_chung_tu": date.fromisoformat(d["document_date"]), "ngay_hoa_don": date.fromisoformat(d["invoice_date"]),
                                           **doi_tac.get(d["counterparty"], khong), "du_an_ma": d["project"] if d["project"] in du_an else None})
            continue
        journal = kind == "JOURNAL"
        du_lieu = d | {"_sqlite_id": doc_id}
        r_raw, ahash = raw.get(doc_id, (None, None))
        if r_raw is not None:
            du_lieu["_raw"] = r_raw
        tho = d.get("counterparty") if journal else d.get("counterparty_name")
        rows["kho.chung_tu"].append({"du_lieu": du_lieu, "hash": digest, "loai": "SO_JUNSKY" if journal else "SAO_KE", "khoa_nguon": key,
                                     "ngay_nghiep_vu": date.fromisoformat(day), "tien_te": cur, "so_tien_minor": abs(amount),
                                     "chieu": None if journal else ("THU" if amount > 0 else "CHI"), "doi_tac_tho": tho, "mo_ta": d.get("description"),
                                     "ky": day[:7], "trang_thai": "DA_NAP" if journal else state.get(doc_id, "CHO_DUYET"),
                                     "voucher_type": d.get("voucher_type"), "so_chung_tu_junsky": d.get("voucher_number"), "tep_goc_hash": ahash,
                                     **doi_tac.get(tho, khong), "du_an_ma": d.get("project") if d.get("project") in du_an else None})
    for doc_id, line_key, core in src.execute("SELECT document_id, line_key, core_json FROM document_lines"):
        l = json.loads(core)
        rows["kho.chung_tu_dong"].append({"sid": doc_id, "stt": int(line_key), "du_lieu": l | {"line_key": line_key}, "tai_khoan": l["account"],
                                          "no_minor": l["debit_minor"], "co_minor": l["credit_minor"], **{c: None for c in COT_DONG_KHONG_ANH_XA}})
    events = {}
    for e in src.execute("SELECT version_id, action, event_at, actor, reason FROM knowledge_events"):
        events.setdefault(e[0], []).append(dict(zip(("version_id", "action", "event_at", "actor", "reason"), e)))
    for (kv_id, cat, lk, rev, payload, digest, vf, vt, ka, evidence, sup, created, actor) in src.execute(
            "SELECT id, category, logical_key, revision, payload_json, content_hash, valid_from, valid_to, known_at, evidence_json, supersedes_id, created_at, actor FROM knowledge_versions"):
        ev = events.get(kv_id, [])
        rows["kho.tri_thuc"].append({"bang_chung": {"_sqlite_id": kv_id, "evidence": json.loads(evidence), "events": ev}, "noi_dung": json.loads(payload),
                                     "nhom": {"KEYWORD": "TU_KHOA"}[cat], "khoa_logic": lk, "phien_ban": rev,
                                     "trang_thai": "DA_DUYET" if ev and ev[-1]["action"] == "APPROVE" else "CHO_DUYET", "actor": actor,
                                     "valid_from": _utc(vf), "valid_to": _utc(vt), "known_at": _utc(ka), "content_hash": digest, "tao_luc": _utc(created),
                                     "supersedes_sid": sup})
    return rows


def _mo_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _doi(v):
    """Giá trị khác cùng kiểu (mutation một cột)."""
    if v is None:
        return "MO_PHONG_X"
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 1
    if isinstance(v, datetime):
        return v + timedelta(seconds=1)
    if isinstance(v, date):
        return v + timedelta(days=1)
    return str(v) + "X"


class _Chay:
    def __init__(self, tool, argv):
        self.out, self.err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
            self.rc = tool.main(argv)
        self.text = self.out.getvalue() + self.err.getvalue()


class LoiSachTests(unittest.TestCase):
    """A4 — không máy chủ: biên lỗi của cả CLI."""

    def setUp(self):
        self.tool = _tool("chuyen_sqlite_sang_pg")
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name) / "kho.sqlite"
        tao_kho_demo(self.src)
        self.bao_cao = Path(self.tmp.name) / "bao-cao.json"
        self.argv = ["--sqlite", str(self.src), "--dsn", "postgresql://demo/khong_ket_noi", "--bao-cao", str(self.bao_cao)]

    def tearDown(self):
        self.tmp.cleanup()

    def _khong_lo(self, chay, rc=3):
        self.assertEqual(chay.rc, rc)
        self.assertNotIn(BI_MAT, chay.text)
        self.assertNotIn("Traceback", chay.text)
        self.assertNotIn("postgresql://", chay.text)
        self.assertEqual(chay.out.getvalue(), "")  # không có báo cáo thành công
        self.assertFalse(self.bao_cao.exists())

    def test_loi_psycopg_chi_con_sqlstate_va_ten_rang_buoc(self):
        class Diag:
            sqlstate = "22007"
            constraint_name = "chung_tu_trang_thai_check"
            table_name = "chung_tu"
            message_primary = f'invalid input syntax for type date: "{BI_MAT}"'
            message_detail = f"Failing row contains ({BI_MAT})."

        class LoiGia(Exception):
            diag = Diag()
        out = self.tool.loi_sach(LoiGia(Diag.message_primary))
        self.assertNotIn(BI_MAT, json.dumps(out, ensure_ascii=False))
        self.assertEqual((out["loi"], out["sqlstate"], out["rang_buoc"], out["bang"]), ("PSYCOPG", "22007", "chung_tu_trang_thai_check", "chung_tu"))
        Diag.constraint_name, Diag.sqlstate = BI_MAT, f"x{BI_MAT}"  # trường định danh lạ cũng không được đi qua
        out = self.tool.loi_sach(LoiGia())
        self.assertNotIn(BI_MAT, json.dumps(out, ensure_ascii=False))
        self.assertEqual((out["sqlstate"], out["rang_buoc"]), ("?", None))

    def test_loi_python_khong_in_thong_diep(self):
        out = self.tool.loi_sach(ValueError(f"invalid literal for int() with base 10: '{BI_MAT}'"))
        self.assertEqual(out["kieu"], "ValueError")
        self.assertNotIn(BI_MAT, json.dumps(out, ensure_ascii=False))

    def test_loi_giua_chuyen_doi(self):
        class Diag:
            sqlstate, constraint_name, table_name = "22P02", None, "chung_tu_dong"
            message_primary = f'invalid input syntax for type bigint: "{BI_MAT}"'

        class LoiGia(Exception):
            diag = Diag()

        class ConnGia:
            def close(self):
                pass
        for loi in (LoiGia(Diag.message_primary), ValueError(BI_MAT), KeyError(BI_MAT)):
            with self.subTest(loi=type(loi).__name__), patch.object(self.tool.pg, "connect", return_value=ConnGia()), \
                    patch.object(self.tool, "_chuyen", side_effect=loi):
                self._khong_lo(_Chay(self.tool, self.argv))

    def test_loi_ket_noi_va_migrate(self):
        class Diag:
            sqlstate, constraint_name, table_name = "42P07", None, None
            message_primary = f'relation "{BI_MAT}" already exists'

        class LoiMigrate(Exception):
            diag = Diag()
        for loi in (Exception(f"connection to {BI_MAT} failed: postgresql://u:{BI_MAT}@h/db"), LoiMigrate(Diag.message_primary)):
            with self.subTest(loi=type(loi).__name__), patch.object(self.tool.pg, "connect", side_effect=loi):
                chay = _Chay(self.tool, self.argv)
                self._khong_lo(chay)
                self.assertTrue(json.loads(chay.err.getvalue().strip())["loi"] in ("KHAC", "PSYCOPG"))

    def test_loi_dong_ket_noi_khong_bao_thanh_cong(self):
        class ConnGia:
            def close(self):
                raise RuntimeError(f"close failed {BI_MAT}")
        with patch.object(self.tool.pg, "connect", return_value=ConnGia()), patch.object(self.tool, "_chuyen", return_value=None):
            self._khong_lo(_Chay(self.tool, self.argv))

    def test_loi_mo_nguon(self):
        argv = ["--sqlite", str(Path(self.tmp.name) / BI_MAT / "khong-co.sqlite"), "--dsn", "postgresql://demo/x", "--bao-cao", str(self.bao_cao)]
        with patch.object(self.tool.pg, "connect", side_effect=AssertionError("không được kết nối")):
            self._khong_lo(_Chay(self.tool, argv))

    def test_sai_cu_phap_khong_thanh_cong_va_kiem_tra_van_chay(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            self.tool.main([])
        self.assertNotEqual(ctx.exception.code, 0)
        with patch.object(self.tool.pg, "connect", side_effect=AssertionError("không được kết nối")):
            chay = _Chay(self.tool, ["--sqlite", str(self.src), "--kiem-tra"])
        self.assertEqual(chay.rc, 0)
        self.assertEqual(json.loads(chay.out.getvalue())["documents_theo_kind"]["BANK"], 1)

    def test_chep_v12_loi_ket_noi_khong_lo(self):
        tool = _tool("chep_v12_sang_pg")
        gia = types.ModuleType("psycopg")

        def connect(*_a, **_k):
            raise Exception(f"connection to {BI_MAT} failed")
        gia.connect = connect
        with patch.dict(sys.modules, {"psycopg": gia}):
            chay = _Chay(tool, ["--sqlite", str(self.src), "--schema", "t_demo_a4", "--dsn", f"postgresql://u:{BI_MAT}@h/db"])
        self.assertEqual(chay.rc, 3)
        self.assertNotIn(BI_MAT, chay.text)
        self.assertNotIn("Traceback", chay.text)


class DoiChieuK2Tests(unittest.TestCase):
    """A5 bộ chuyển K2 — vân tay dựng từ nguồn so với mọi cột đã ánh xạ ở đích, không máy chủ (đích mô phỏng)."""

    def setUp(self):
        self.tool = _tool("chuyen_sqlite_sang_pg")
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "kho.sqlite"
        tao_kho_demo(path)
        self.src = _mo_ro(path)
        self.rows = mo_phong_dich(self.src)

    def tearDown(self):
        self.src.close()
        self.tmp.cleanup()

    def _doi_chieu(self, rows):
        return self.tool.doi_chieu_noi_dung(self.tool.van_tay_nguon(self.src), self.tool.van_tay_dich(rows))

    def test_dich_dung_thi_khop_va_chay_lai_on_dinh(self):
        lan1, lan2 = self._doi_chieu(self.rows), self._doi_chieu(copy.deepcopy(self.rows))
        self.assertEqual(lan1, lan2)
        self.assertTrue(all(r["khop"] for r in lan1.values()), lan1)
        self.assertEqual({t: lan1[t]["nguon"] for t in ("kho.chung_tu", "kho.chung_tu_dong", "kho.cong_no_mo", "kho.tri_thuc")},
                         {"kho.chung_tu": 2, "kho.chung_tu_dong": 2, "kho.cong_no_mo": 1, "kho.tri_thuc": 2})

    def test_doi_tung_cot_typed_khi_json_giu_nguyen_deu_bi_phat_hien(self):
        """Mỗi cột nghiệp vụ (kể cả khóa ngoại quy về khóa ổn định, cột bộ chuyển phải để NULL) đổi riêng → lệch đúng 1 bản ghi."""
        json_cot = {"du_lieu", "bang_chung", "noi_dung", "sid"}
        da_thu = set()
        for bang, ds in self.rows.items():
            for i, row in enumerate(ds):
                for cot in row:
                    if cot in json_cot or (cot == "dt_ghi_chu" and row["dt_mst"]) or (cot in ("dt_mst", "dt_ghi_chu") and not row["co_doi_tac"]):
                        continue  # ghi chú không là khóa khi đã có MST; MST/ghi chú vô nghĩa khi không trỏ đối tác
                    rows = copy.deepcopy(self.rows)
                    rows[bang][i][cot] = _doi(rows[bang][i][cot])
                    with self.subTest(bang=bang, dong=i, cot=cot):
                        kq = self._doi_chieu(rows)
                        self.assertEqual((kq[bang]["lech"], kq[bang]["khop"]), (1, False))
                        self.assertTrue(all(r["khop"] for t, r in kq.items() if t != bang))
                    da_thu.add((bang, cot))
        # các cột trong probe review phải nằm trong tập đã thử
        for bang, cot in (("kho.cong_no_mo", "tai_khoan"), ("kho.cong_no_mo", "con_lai_minor"), ("kho.tri_thuc", "trang_thai"), ("kho.tri_thuc", "known_at"),
                          ("kho.chung_tu", "tien_te"), ("kho.chung_tu", "chieu"), ("kho.chung_tu", "trang_thai"), ("kho.chung_tu", "dt_mst"),
                          ("kho.chung_tu", "du_an_ma"), ("kho.cong_no_mo", "dt_ghi_chu"), ("kho.tri_thuc", "supersedes_sid"), ("kho.chung_tu_dong", "dich")):
            self.assertIn((bang, cot), da_thu)

    def test_sua_json_hoac_hash_dich_bi_phat_hien(self):
        def sua(fn):
            rows = copy.deepcopy(self.rows)
            fn(rows)
            return self._doi_chieu(rows)
        def dong_co_raw(r):  # chọn theo khóa nguồn ổn định: DB1 là chứng từ duy nhất có bằng chứng raw (evidence SR1)
            dong = next(d for d in r["kho.chung_tu"] if d["du_lieu"]["_sqlite_id"] == "DB1")
            self.assertIn("_raw", dong["du_lieu"])
            return dong

        ca = {
            "kho.chung_tu": lambda r: r["kho.chung_tu"][0]["du_lieu"].update(description="MO_PHONG_SUA"),
            "kho.chung_tu#raw": lambda r: dong_co_raw(r)["du_lieu"]["_raw"].update(so_tien="999"),
            "kho.chung_tu_dong": lambda r: r["kho.chung_tu_dong"][0]["du_lieu"].update(account="6428"),
            "kho.cong_no_mo": lambda r: r["kho.cong_no_mo"][0]["du_lieu"].update(account="3311"),
            "kho.tri_thuc": lambda r: r["kho.tri_thuc"][0]["noi_dung"].update(tk="6429"),
            "kho.tri_thuc#bang_chung": lambda r: r["kho.tri_thuc"][1]["bang_chung"]["events"].clear(),
        }
        for ten, fn in ca.items():
            bang = ten.split("#")[0]
            with self.subTest(ten=ten):
                kq = sua(fn)
                self.assertEqual((kq[bang]["lech"], kq[bang]["khop"]), (1, False))

    def test_thieu_thua_trung_bi_phat_hien(self):
        rows = copy.deepcopy(self.rows)
        rows["kho.chung_tu_dong"].pop()
        rows["kho.chung_tu"].append(copy.deepcopy(rows["kho.chung_tu"][0]))  # chạy lại mà ghi trùng
        la = copy.deepcopy(rows["kho.tri_thuc"][0])
        la["bang_chung"]["_sqlite_id"] = "KV_LA"
        rows["kho.tri_thuc"].append(la)
        kq = self._doi_chieu(rows)
        self.assertEqual(kq["kho.chung_tu_dong"]["thieu"], 1)
        self.assertEqual((kq["kho.chung_tu"]["trung"], kq["kho.chung_tu"]["khop"]), (1, False))
        self.assertEqual(kq["kho.tri_thuc"]["thua"], 1)

    def test_core_hash_nguon_sai_duoc_bao(self):
        path = Path(self.tmp.name) / "kho-sai.sqlite"
        tao_kho_demo(path)
        conn = sqlite3.connect(path)
        conn.execute("UPDATE documents SET core_hash=? WHERE id='DJ1'", ("0" * 64,))
        conn.commit()
        conn.close()
        src = _mo_ro(path)
        try:
            kq = self.tool.doi_chieu_noi_dung(self.tool.van_tay_nguon(src), self.tool.van_tay_dich(mo_phong_dich(src)))
        finally:
            src.close()
        self.assertEqual(kq["core_hash_nguon"], {"sai": 1, "khop": False})

    def test_thoi_diem_va_kieu_char_chuan_hoa(self):
        t = self.tool
        self.assertEqual(t._thoi_diem("2026-01-01"), t._thoi_diem(datetime(2026, 1, 1, tzinfo=timezone.utc)))
        self.assertEqual(t._thoi_diem("2026-09-02T08:02:03+07:00"), t._thoi_diem("2026-09-02T01:02:03Z"))
        self.assertNotEqual(t._thoi_diem("2026-09-02T01:02:03Z"), t._thoi_diem("2026-09-02T01:02:04Z"))
        self.assertEqual(t._tien_te("US "), "US")


class DoiChieuV12Tests(unittest.TestCase):
    """A5 bộ chép V12 nguyên trạng — hash nội dung từng bảng, tách dấu nạp xong; đích SQLite thay PostgreSQL (không máy chủ)."""

    def test_dau_nap_xong_khong_lam_lech_va_sua_mot_gia_tri_bi_phat_hien(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_path, dst_path = Path(tmp) / "nguon.sqlite", Path(tmp) / "dich.sqlite"
            tao_kho_demo(src_path)
            src = database.connect(src_path)
            dst = sqlite3.connect(dst_path)
            try:
                src.backup(dst)
                dst.execute("INSERT INTO workspace_meta VALUES (?,?)", (DAU_NAP_XONG, '{"luc":"2026-09-01T00:00:00Z"}'))  # như chep_sqlite_sang_pg
                dst.commit()
                dem = lambda c: c.execute("SELECT count(*) FROM workspace_meta").fetchone()[0]
                self.assertEqual(dem(dst), dem(src) + 1)  # số đếm thô lệch +1 — lỗi cũ của chep_v12_sang_pg
                cot = lambda t: _cot_sqlite(dst, t)[0]
                lan1 = doi_chieu_noi_dung(src, van_tay_sqlite(dst), cot)
                lan2 = doi_chieu_noi_dung(src, van_tay_sqlite(dst), cot)
                self.assertEqual(lan1, lan2)
                self.assertTrue(all(r["khop"] for r in lan1.values()), [t for t, r in lan1.items() if not r["khop"]])
                self.assertEqual(lan1["workspace_meta"], {"nguon": 1, "dich": 1, "khop": True})
                dst.execute("UPDATE activity_log SET action='MO_PHONG_SUA'")  # cùng số dòng, khác nội dung
                dst.execute("UPDATE workspace_meta SET value='\"KHAC\"' WHERE key='entity_id'")
                dst.commit()
                kq = doi_chieu_noi_dung(src, van_tay_sqlite(dst), cot)
                self.assertEqual(sorted(t for t, r in kq.items() if not r["khop"]), ["activity_log", "workspace_meta"])
                self.assertEqual(kq["activity_log"]["nguon"], kq["activity_log"]["dich"])
            finally:
                src.close()
                dst.close()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — bỏ qua test PostgreSQL (Codex chạy PG thật)")
class HaiToolTrenPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pgk2

        cls.db_name = "kho_test_a45_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db_name}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db_name
        pgk2.connect(cls.dsn, autocommit=True).close()  # schema K2

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'DROP DATABASE "{cls.db_name}" WITH (FORCE)')

    def test_a4_loi_ep_kieu_that_khong_lo_chuoi(self):
        tool = _tool("chuyen_sqlite_sang_pg")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "kho.sqlite"
            tao_kho_demo(src, ngay_bank=BI_MAT, day_du=False)  # SQLite nhận, PostgreSQL từ chối ép kiểu date
            bao_cao = Path(tmp) / "bc.json"
            chay = _Chay(tool, ["--sqlite", str(src), "--dsn", self.dsn, "--bao-cao", str(bao_cao)])
        self.assertEqual(chay.rc, 3)
        self.assertNotIn(BI_MAT, chay.text)
        self.assertEqual(json.loads(chay.err.getvalue().strip().splitlines()[-1])["loi"], "PSYCOPG")
        self.assertFalse(bao_cao.exists())

    def test_a5_k2_hai_lan_khop_va_sua_cot_typed_bi_phat_hien(self):
        tool = _tool("chuyen_sqlite_sang_pg")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "kho.sqlite"
            tao_kho_demo(src)
            for _ in range(2):  # idempotent: lần hai không trùng
                chay = _Chay(tool, ["--sqlite", str(src), "--dsn", self.dsn])
                self.assertEqual(chay.rc, 0, chay.err.getvalue())
                kq = json.loads(chay.out.getvalue())
                self.assertTrue(all(r["khop"] for r in kq["doi_chieu_noi_dung"].values()), kq["doi_chieu_noi_dung"])
            sua = {"kho.chung_tu": "UPDATE kho.chung_tu SET chieu = 'THU' WHERE du_lieu->>'_sqlite_id' = 'DB1'",
                   "kho.cong_no_mo": "UPDATE kho.cong_no_mo SET con_lai_minor = con_lai_minor + 1 WHERE du_lieu->>'_sqlite_id' = 'DO1'",
                   "kho.tri_thuc": "UPDATE kho.tri_thuc SET known_at = known_at + interval '1 second' WHERE bang_chung->>'_sqlite_id' = 'KV1'"}
            for bang, sql in sua.items():
                with self.subTest(bang=bang), psycopg.connect(self.dsn) as c:  # giao dịch rồi hoàn tác, không để lại thay đổi
                    c.execute("SET LOCAL TIME ZONE 'UTC'")
                    c.execute(sql)
                    pn = c.execute("SELECT id FROM master.phap_nhan WHERE ma = 'PLHN_FIXTURE'").fetchone()[0]
                    s = _mo_ro(src)
                    try:
                        kq = tool.doi_chieu_noi_dung(tool.van_tay_nguon(s), tool.van_tay_dich(tool.doc_dich(c.cursor(), pn)))
                    finally:
                        s.close()
                    c.rollback()
                    self.assertEqual((kq[bang]["lech"], kq[bang]["khop"]), (1, False))

    def test_a5_chep_v12_dau_nap_xong_tach_rieng_va_phat_hien_sua(self):
        tool = _tool("chep_v12_sang_pg")
        schema = "t_" + uuid.uuid4().hex[:10]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "kho.sqlite"
            tao_kho_demo(src)
            argv = ["--sqlite", str(src), "--schema", schema, "--dsn", self.dsn, "--grant", ""]
            chay = _Chay(tool, argv)
            self.assertEqual(chay.rc, 0, chay.err.getvalue())
            bc = json.loads(chay.out.getvalue())
            self.assertEqual((bc["hanh_dong"], bc["khop_moi_bang"], bc["metadata_migration"]), ("NAP", True, [DAU_NAP_XONG]))
            bc = json.loads(_Chay(tool, argv).out.getvalue())  # chạy lại: giữ nguyên, không trùng
            self.assertEqual((bc["hanh_dong"], bc["khop_moi_bang"]), ("GIU_NGUYEN", True))
            with psycopg.connect(self.dsn, autocommit=True) as c:
                c.execute(f'UPDATE "{schema}".activity_log SET action = %s', ("MO_PHONG_SUA",))
            chay = _Chay(tool, argv)
            bc = json.loads(chay.out.getvalue())
            self.assertEqual((chay.rc, bc["khop_moi_bang"], bc["bang_lech"]), (1, False, ["activity_log"]))


if __name__ == "__main__":
    unittest.main()
