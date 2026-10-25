"""Kiểm tra schema PostgreSQL V13 (tài liệu 38 §7): migration, nhật ký chỉ ghi thêm, máy trạng thái,
điều kiện Đồng ý, LLM tối đa Vàng, tham số có trích dẫn, khóa sau xuất, nhãn học, một đề xuất một lô.

Chạy khi có PostgreSQL thật: đặt KHO_PG_DSN_TEST (vd postgresql://postgres:pw@127.0.0.1:5432/postgres).
Không có thì bỏ qua (SQLite vẫn là engine mặc định). Dữ liệu trong test là DEMO, không có số liệu thật."""

from __future__ import annotations

import os
import unittest
import uuid

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import PG_SCHEMA_VERSION

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")


def _admin():
    return psycopg.connect(ADMIN_DSN, autocommit=True)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — bỏ qua test PostgreSQL")
class PostgresSchemaTest(unittest.TestCase):
    """Các test chạy theo thứ tự tên (unittest sắp xếp theo chữ cái) trên cùng một chứng từ DEMO."""

    @classmethod
    def setUpClass(cls):
        cls.runner_cap = bool(os.environ.get("KHO_PG_DEMO_SO"))
        cls.db_name = os.environ.get("KHO_PG_DEMO_DB") if cls.runner_cap else "kho_test_" + uuid.uuid4().hex[:8]
        if not cls.db_name:
            raise unittest.SkipTest("--pg-demo chưa cấp CSDL có sổ sở hữu cho test_pg_schema")
        if not cls.runner_cap:
            with _admin() as a:
                a.execute(psycopg.sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(psycopg.sql.Identifier(cls.db_name)))
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db_name
        cls.conn = pg.connect(cls.dsn, autocommit=True)
        c = cls.conn
        cls.pn = c.execute(
            "INSERT INTO master.phap_nhan (ma, ten, ma_don_vi_junsky) VALUES ('DEMO','Pháp nhân DEMO','99') RETURNING id"
        ).fetchone()[0]
        for ma, ten, cap, cong_no, tien in (
            ("131", "Phải thu KH", 1, True, False), ("131171", "Phải thu KH: hạ tầng DEMO", 2, True, False),
            ("112111", "Tiền gửi NH DEMO", 2, False, True), ("6427", "Dịch vụ mua ngoài", 2, False, False),
        ):
            c.execute(
                "INSERT INTO master.tai_khoan (phap_nhan_id, ma_junsky, ten, cap, tk_cong_no, tk_tien) VALUES (%s,%s,%s,%s,%s,%s)",
                (cls.pn, ma, ten, cap, cong_no, tien),
            )
        cls.ct = c.execute(
            """INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, chieu, mo_ta, hash, ky, trang_thai)
               VALUES (%s,'SAO_KE','DEMO-0001','2026-08-05','VND',1000000,'THU','DEMO thu tien','0'||repeat('a',63),'2026-08','CHO_DUYET') RETURNING id""",
            (cls.pn,),
        ).fetchone()[0]
        cls.dx = c.execute(
            "INSERT INTO kho.de_xuat (chung_tu_id, phien_ban, muc, nguon_suy_luan) VALUES (%s,1,'VANG','LICH_SU') RETURNING id", (cls.ct,)
        ).fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if cls.runner_cap:
            return  # runner DROP qua sổ sở hữu sau khi module kết thúc
        with _admin() as a:
            a.execute(psycopg.sql.SQL("DROP DATABASE {}").format(psycopg.sql.Identifier(cls.db_name)))

    # ---- tiện ích
    def _dong(self, offset, no_co, acct, amt, obj=None):
        self.conn.execute(
            """INSERT INTO kho.de_xuat_dong (de_xuat_id, "offset", no_co, acct_id, base_deb, base_crd, object_id_junsky)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (self.dx, offset, no_co, acct, amt if no_co == "N" else 0, amt if no_co == "C" else 0, obj),
        )

    def _state(self, state):
        self.conn.execute("UPDATE kho.chung_tu SET trang_thai=%s WHERE id=%s", (state, self.ct))

    def _raises(self, code, fn):
        with self.assertRaises(psycopg.Error) as ctx:
            fn()
        self.assertIn(code, str(ctx.exception))

    # ---- test (thứ tự theo tên t01…)
    def test_t01_migrate_idempotent(self):
        self.assertEqual(pg.schema_version(self.conn), PG_SCHEMA_VERSION)
        self.assertEqual(pg.migrate(self.conn), PG_SCHEMA_VERSION)
        info = pg.integrity(self.conn)
        self.assertTrue(info["ok"])
        self.assertGreaterEqual(info["tables"]["kho"], 15)
        self.assertEqual(info["tables"]["nhat_ky"], 3)
        self.assertEqual(info["tables"]["bao_mat"], 1)

    def test_t02_nhat_ky_chi_ghi_them(self):
        sk = self.conn.execute(
            "INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, hanh_dong) VALUES (%s,'DEMO','QUYET_DINH','chung_tu','DONG_Y') RETURNING id",
            (self.pn,),
        ).fetchone()[0]
        self._raises("NHAT_KY_CHI_GHI_THEM", lambda: self.conn.execute("UPDATE nhat_ky.su_kien SET ly_do='x' WHERE id=%s", (sk,)))
        self._raises("NHAT_KY_CHI_GHI_THEM", lambda: self.conn.execute("DELETE FROM nhat_ky.su_kien WHERE id=%s", (sk,)))

    def test_t02b_nhat_ky_chan_truncate(self):
        self._raises("NHAT_KY_CHI_GHI_THEM", lambda: self.conn.execute("TRUNCATE nhat_ky.su_kien"))

    def test_t03_llm_toi_da_vang(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute(
                "INSERT INTO kho.de_xuat (chung_tu_id, phien_ban, hien_hanh, muc, nguon_suy_luan) VALUES (%s,2,false,'XANH','LLM')", (self.ct,)
            )

    def test_t04_tham_so_llm_phai_co_trich_dan(self):
        hd = self.conn.execute(
            "INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'THUE_DAT','HD-DEMO-1','01/DEMO') RETURNING id", (self.pn,)
        ).fetchone()[0]
        pb = self.conn.execute("INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon) VALUES (%s,1,'LLM') RETURNING id", (hd,)).fetchone()[0]
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, nguon) VALUES (%s,'dien_tich','1000','LLM')", (pb,))
        self.conn.execute("INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, nguon) VALUES (%s,'dien_tich',NULL,'LLM')", (pb,))

    def test_t05_trang_thai_khong_nhay_coc(self):
        self._raises("TRANG_THAI_KHONG_HOP_LE", lambda: self._state("DA_NAP"))

    def test_t06_dong_y_can_no_bang_co(self):
        self._dong(1, "N", "112111", 1000000)
        self._raises("NO_KHONG_BANG_CO", lambda: self._state("DA_DUYET"))

    def test_t06b_dong_y_can_tk_co_trong_danh_muc(self):
        self._dong(9, "C", "ZZZ-DEMO-KHONG-CO", 1000000)
        self._raises("TK_KHONG_CO_TRONG_DANH_MUC", lambda: self._state("DA_DUYET"))
        self.conn.execute('DELETE FROM kho.de_xuat_dong WHERE de_xuat_id=%s AND "offset"=9', (self.dx,))

    def test_t07_dong_y_can_doi_tuong_cho_tk_cong_no(self):
        self._dong(2, "C", "131171", 1000000, obj=None)
        self._raises("THIEU_DOI_TUONG", lambda: self._state("DA_DUYET"))
        self.conn.execute('UPDATE kho.de_xuat_dong SET object_id_junsky=%s WHERE de_xuat_id=%s AND "offset"=2', ("DEMO.KH.01", self.dx))

    def test_t08_dong_y_can_tk_chi_tiet(self):
        self.conn.execute('UPDATE kho.de_xuat_dong SET acct_id=%s WHERE de_xuat_id=%s AND "offset"=2', ("131", self.dx))
        self._raises("TK_CHUA_CHI_TIET", lambda: self._state("DA_DUYET"))
        self.conn.execute('UPDATE kho.de_xuat_dong SET acct_id=%s WHERE de_xuat_id=%s AND "offset"=2', ("131171", self.dx))

    def test_t09_dong_y_bi_chan_khi_ky_khoa(self):
        self.conn.execute("INSERT INTO kho.khoa_ky (phap_nhan_id, ky, nguoi) VALUES (%s,'2026-08','DEMO')", (self.pn,))
        self._raises("KY_DA_KHOA", lambda: self._state("DA_DUYET"))
        self.conn.execute("DELETE FROM kho.khoa_ky WHERE phap_nhan_id=%s", (self.pn,))

    def test_t10_dong_y_hop_le_va_khoa_sau_xuat(self):
        self._state("DA_DUYET")
        self._state("CHO_DUYET")  # hoàn tác được khi chưa xuất
        self._state("DA_DUYET")
        self._state("DA_XUAT")
        self._raises("DA_XUAT_KHONG_SUA", lambda: self._dong(3, "N", "6427", 1))
        self._raises("TRANG_THAI_KHONG_HOP_LE", lambda: self._state("CHO_DUYET"))

    def test_t11_mot_de_xuat_mot_lo_junsky(self):
        lo1 = self.conn.execute(
            "INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, nguoi) VALUES (%s,'2026-08','DEMO-2608-01','JUNSKY','DEMO') RETURNING id", (self.pn,)
        ).fetchone()[0]
        lo2 = self.conn.execute(
            "INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, nguoi) VALUES (%s,'2026-08','DEMO-2608-02','JUNSKY','DEMO') RETURNING id", (self.pn,)
        ).fetchone()[0]
        self.conn.execute("INSERT INTO kho.lo_xuat_dong (lo_id, loai_lo, de_xuat_id) VALUES (%s,'JUNSKY',%s)", (lo1, self.dx))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.conn.execute("INSERT INTO kho.lo_xuat_dong (lo_id, loai_lo, de_xuat_id) VALUES (%s,'JUNSKY',%s)", (lo2, self.dx))

    def test_t12_nhan_hoc_chi_khi_doi_chieu_khop(self):
        ins = lambda: self.conn.execute(  # noqa: E731
            "INSERT INTO kho.nhan_hoc (chung_tu_id, de_xuat_id, trang_thai, business_date, known_at) VALUES (%s,%s,'DU_DIEU_KIEN','2026-08-05',now())",
            (self.ct, self.dx),
        )
        self._raises("CHUA_DOI_CHIEU", ins)
        self._state("DA_NAP")
        self._state("DA_DOI_CHIEU")
        self._raises("CHUA_KHOP_JUNSKY", ins)
        self.conn.execute("UPDATE kho.lo_xuat_dong SET doi_chieu='KHOP' WHERE de_xuat_id=%s", (self.dx,))
        ins()

    def test_t13_dinh_danh_stk_phai_ma_hoa(self):
        dt = self.conn.execute(
            "INSERT INTO master.doi_tac (ten_phap_ly, ten_chuan_hoa, loai, vai_tro) VALUES ('CTY DEMO','CTY DEMO','TC','{KH}') RETURNING id"
        ).fetchone()[0]
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute(
                "INSERT INTO master.doi_tac_dinh_danh (doi_tac_id, loai, gia_tri, gia_tri_hash, nguon) VALUES (%s,'STK','000','h1','sao_ke')", (dt,)
            )
        self.conn.execute(
            "INSERT INTO master.doi_tac_dinh_danh (doi_tac_id, loai, gia_tri_mh, gia_tri_hash, nguon) VALUES (%s,'STK',pgp_sym_encrypt('000','k'),'h1','sao_ke')",
            (dt,),
        )
        self.assertEqual(self.conn.execute("SELECT pgp_sym_decrypt(gia_tri_mh,'k') FROM master.doi_tac_dinh_danh WHERE gia_tri_hash='h1'").fetchone()[0], "000")

    def test_t14_chuan_hoa_ten(self):
        self.assertEqual(self.conn.execute("SELECT master.chuan_hoa_ten('Công  ty DEMO Đầu tư')").fetchone()[0], "CONG TY DEMO DAU TU")

    def test_t15_vai_tro_ke_toan_khong_thay_bao_mat(self):
        """Tạo vai trò DEMO tạm (mật khẩu ngẫu nhiên) kế thừa app_ke_toan; kiểm quyền thật (review N8)."""
        if os.environ.get("KHO_PG_DEMO_SO"):
            self.skipTest("--pg-demo chỉ quản lý CSDL; ca tạo/xóa vai trò cấp cụm chưa đi qua sổ sở hữu")
        if self.conn.execute("SELECT 1 FROM pg_roles WHERE rolname='app_ke_toan'").fetchone() is None:
            self.skipTest("chưa có vai trò app_ke_toan (CÀI POSTGRESQL.cmd tạo)")
        role = "ktt_test_" + uuid.uuid4().hex; pw = uuid.uuid4().hex
        self.conn.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{pw}' IN ROLE app_ke_toan")
        self.conn.execute(f'GRANT CONNECT ON DATABASE "{self.db_name}" TO {role}')
        try:
            base = self.dsn.split("@", 1)[1]
            with psycopg.connect(f"postgresql://{role}:{pw}@{base}", autocommit=True) as kt:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    kt.execute("SELECT count(*) FROM bao_mat.mask_bi_danh")
                self.assertGreaterEqual(kt.execute("SELECT count(*) FROM kho.chung_tu").fetchone()[0], 1)
                with self.assertRaises(psycopg.Error):
                    kt.execute("DELETE FROM nhat_ky.su_kien")
                with self.assertRaises(psycopg.Error):
                    kt.execute("UPDATE nhat_ky.su_kien SET ly_do='x'")
                with self.assertRaises(psycopg.Error):
                    kt.execute("TRUNCATE nhat_ky.su_kien")
                kt.execute("INSERT INTO nhat_ky.su_kien (nguoi, loai, doi_tuong_bang, hanh_dong) VALUES ('DEMO','HE_THONG','test','GHI')")
        finally:
            self.conn.execute(f"DROP OWNED BY {role}")
            self.conn.execute(f"DROP ROLE {role}")

    def test_t16_bo_chuyen_demo(self):
        """Bộ chuyển trên kho SQLite DEMO: 5 trạng thái quick_items → trạng thái chứng từ; chạy lại idempotent."""
        import json, os, subprocess, sys, tempfile
        from kho_tri_thuc.ha_tang import database
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp = tempfile.mkdtemp(prefix="kho_demo_")
        path = os.path.join(tmp, "kho-demo.sqlite")
        sc = database.connect(__import__("pathlib").Path(path))
        H = "0" * 64; T = "2026-08-01T00:00:00.000000Z"
        sc.execute("INSERT INTO workspace_meta VALUES ('entity_id','DEMO')")
        sc.execute("INSERT INTO config_history VALUES (?,?,?)", (H, b"x", T))
        sc.execute("INSERT INTO artifacts VALUES (?,?,?,?)", (H, "raw/demo.bin", 1, T))
        sc.execute("INSERT INTO attempts (id, artifact_hash, original_name, config_hash, parser_version, state, started_at) VALUES ('a1',?,?,?,?,?,?)", (H, "demo.xlsx", H, "v", "COMMITTED", T))
        sc.execute("INSERT INTO quick_runs (id, source_attempt_id, source_kind, created_at, actor) VALUES ('r1','a1','sao_ke',?, 'DEMO')", (T,))
        sc.execute("INSERT INTO documents VALUES ('j1','DEMO','JOURNAL','J-1','2026-08-01','VND',100,?,?, 'a1')",
                   (json.dumps({"unit_code": "99", "voucher_type": "BR", "voucher_number": "99BR2608-0001", "book": "Sổ NKC có đối ưng", "description": "DEMO", "counterparty": "DEMO.KH.01"}), H))
        sc.execute("INSERT INTO document_lines VALUES ('l1','j1','1',100,?,?)", (json.dumps({"account": "112111", "debit_minor": 100, "credit_minor": 0}), H))
        sc.execute("INSERT INTO document_lines VALUES ('l2','j1','2',100,?,?)", (json.dumps({"account": "131171", "debit_minor": 0, "credit_minor": 100}), H))
        sc.execute("INSERT INTO documents VALUES ('cp1','DEMO','COUNTERPARTY','DEMO.KH.01','2026-08-01',NULL,NULL,?,?, 'a1')", (json.dumps({"code": "DEMO.KH.01", "name": "CTY DEMO", "tax_id": "0000000000"}), H))
        states = ["WAIT", "APPROVE", "SKIP", "EXISTING", "EXPORTED"]
        for i, st in enumerate(states, 1):
            sc.execute("INSERT INTO documents VALUES (?,'DEMO','BANK',?,'2026-08-05','VND',?,?,?, 'a1')",
                       (f"b{i}", f"B-{i}", -1000 if i % 2 else 1000, json.dumps({"description": f"DEMO {i}", "counterparty_name": "CTY DEMO"}), H))
            prop = {"amount_minor": -1000 if i % 2 else 1000, "completeness": "FULL", "fields": {"debit_account": "6427", "credit_account": "112111", "counterparty": None}, "cash_leg": {"account": "112111"}, "why": "DEMO"}
            sc.execute("INSERT INTO quick_items (id, run_id, document_id, proposal_json, state) VALUES (?,?,?,?,?)", (f"q{i}", "r1", f"b{i}", json.dumps(prop), st))
        sc.execute("INSERT INTO knowledge_versions (id, category, logical_key, revision, payload_json, content_hash, valid_from, known_at, evidence_json, created_at, actor) VALUES ('k1','KEYWORD','DEMO',1,'{}',?,?,?,'{}',?, 'DEMO')", (H, T, T, T))
        sc.execute("INSERT INTO knowledge_events (version_id, action, event_at, actor, reason) VALUES ('k1','APPROVE',?,'DEMO','')", (T,))
        sc.execute("INSERT INTO knowledge_events (version_id, action, event_at, actor, reason) VALUES ('k1','REVOKE',?,'DEMO','')", (T.replace("08-01", "08-02"),))
        sc.commit(); sc.close()
        env = dict(os.environ, KHO_PG_DSN=self.dsn, PYTHONPATH=os.path.join(root, "src"))
        for lan in (1, 2):
            r = subprocess.run([sys.executable, os.path.join(root, "tools", "chuyen_sqlite_sang_pg.py"), "--sqlite", path], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
        got = dict(self.conn.execute("SELECT khoa_nguon, trang_thai FROM kho.chung_tu WHERE loai='SAO_KE' AND khoa_nguon LIKE 'B-%' AND phap_nhan_id = (SELECT id FROM master.phap_nhan WHERE ma='DEMO')").fetchall())
        self.assertEqual(got, {"B-1": "CHO_DUYET", "B-2": "DA_DUYET", "B-3": "BO_QUA", "B-4": "DA_CO_JUNSKY", "B-5": "DA_XUAT"})
        self.assertEqual(self.conn.execute("SELECT trang_thai FROM kho.tri_thuc WHERE khoa_logic='DEMO'").fetchone()[0], "THU_HOI")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM kho.viec_can_duyet WHERE trang_thai='CHO_DUYET' AND tham_chieu_bang='kho.de_xuat' AND phap_nhan_id=(SELECT id FROM master.phap_nhan WHERE ma='DEMO')").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id=x.chung_tu_id WHERE c.khoa_nguon='B-5'").fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
