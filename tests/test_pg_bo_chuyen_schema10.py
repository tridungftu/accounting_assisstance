"""Chẩn đoán hồi quy: bộ chuyển K2 (tools/chuyen_sqlite_sang_pg.py) trên schema PostgreSQL mới nhất với kho SQLite DEMO như
test_pg_schema.t16. In bảng đối chiếu tổng hợp (chỉ số đếm/cờ khớp, không dữ liệu dòng) để phân biệt lỗi do migration mới với
lỗi A5 đã biết. Giữ DB `kho_test_*`, không DROP."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có KHO_PG_DSN_TEST — không chạy (không tính đạt)")
class BoChuyenSchemaMoiTest(unittest.TestCase):
    def test_bo_chuyen_demo_tren_schema_moi_nhat(self):
        from kho_tri_thuc.ha_tang import database, postgres as pg
        db = "kho_test_chuyen_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{db}" ENCODING \'UTF8\' TEMPLATE template0')
        dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + db
        pg.connect(dsn, autocommit=True).close()
        root = Path(__file__).resolve().parents[1]
        path = Path(tempfile.mkdtemp(prefix="kho_demo_chuyen_")) / "kho-demo.sqlite"
        sc = database.connect(path)
        H, T = "0" * 64, "2026-08-01T00:00:00.000000Z"
        sc.execute("INSERT INTO workspace_meta VALUES ('entity_id','DEMO')")
        sc.execute("INSERT INTO config_history VALUES (?,?,?)", (H, b"x", T))
        sc.execute("INSERT INTO artifacts VALUES (?,?,?,?)", (H, "raw/demo.bin", 1, T))
        sc.execute("INSERT INTO attempts (id, artifact_hash, original_name, config_hash, parser_version, state, started_at) VALUES ('a1',?,?,?,?,?,?)", (H, "demo.xlsx", H, "v", "COMMITTED", T))
        sc.execute("INSERT INTO quick_runs (id, source_attempt_id, source_kind, created_at, actor) VALUES ('r1','a1','sao_ke',?, 'DEMO')", (T,))
        sc.execute("INSERT INTO documents VALUES ('j1','DEMO','JOURNAL','J-1','2026-08-01','VND',100,?,?, 'a1')",
                   (json.dumps({"unit_code": "99", "voucher_type": "BR", "voucher_number": "99BR2608-0001", "description": "DEMO", "counterparty": "DEMO.KH.01"}), H))
        sc.execute("INSERT INTO document_lines VALUES ('l1','j1','1',100,?,?)", (json.dumps({"account": "112111", "debit_minor": 100, "credit_minor": 0}), H))
        sc.execute("INSERT INTO document_lines VALUES ('l2','j1','2',100,?,?)", (json.dumps({"account": "131171", "debit_minor": 0, "credit_minor": 100}), H))
        sc.execute("INSERT INTO documents VALUES ('cp1','DEMO','COUNTERPARTY','DEMO.KH.01','2026-08-01',NULL,NULL,?,?, 'a1')", (json.dumps({"code": "DEMO.KH.01", "name": "CTY DEMO", "tax_id": "0000000000"}), H))
        for i, st in enumerate(["WAIT", "APPROVE", "SKIP", "EXISTING", "EXPORTED"], 1):
            sc.execute("INSERT INTO documents VALUES (?,'DEMO','BANK',?,'2026-08-05','VND',?,?,?, 'a1')",
                       (f"b{i}", f"B-{i}", -1000 if i % 2 else 1000, json.dumps({"description": f"DEMO {i}", "counterparty_name": "CTY DEMO"}), H))
            prop = {"amount_minor": -1000 if i % 2 else 1000, "completeness": "FULL", "fields": {"debit_account": "6427", "credit_account": "112111", "counterparty": None}, "cash_leg": {"account": "112111"}, "why": "DEMO"}
            sc.execute("INSERT INTO quick_items (id, run_id, document_id, proposal_json, state) VALUES (?,?,?,?,?)", (f"q{i}", "r1", f"b{i}", json.dumps(prop), st))
        sc.commit(); sc.close()
        env = dict(os.environ, KHO_PG_DSN=dsn, PYTHONPATH=str(root / "src"))
        r = subprocess.run([sys.executable, "-X", "utf8", str(root / "tools" / "chuyen_sqlite_sang_pg.py"), "--sqlite", str(path)], env=env, capture_output=True, text=True)
        try:
            report = json.loads(r.stdout)
        except ValueError:
            self.fail(f"Bộ chuyển không trả JSON (mã {r.returncode}); stderr: {r.stderr[-300:]}")
        lech_dem = [x["bang"] for x in report["doi_chieu"] if not x["khop"]]
        lech_noi_dung = {k: {kk: vv for kk, vv in v.items() if kk != "khop"} for k, v in report["doi_chieu_noi_dung"].items() if not v.get("khop", True)}
        print("\nBO_CHUYEN_SCHEMA_MOI", json.dumps({"ma_thoat": r.returncode, "lech_dem": lech_dem, "lech_noi_dung": lech_noi_dung}, ensure_ascii=False))
        # Trên schema mới nhất (gồm 0010 CRM-01): mọi bảng khớp số đếm và nội dung. Mã thoát 1 chỉ do fixture DEMO dùng core_hash giả
        # "000…" cho 6 chứng từ — kiểm tra nguồn của A5 báo đúng; không phải lỗi migration (test_pg_schema.t16 dùng cùng fixture).
        self.assertEqual(lech_dem, [])
        self.assertEqual(lech_noi_dung, {"core_hash_nguon": {"sai": 6}})
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
