"""AI-2b: metadata DEMO, kết nối giả; PG chỉ chạy khi lead cấp KHO_PG_DSN_TEST.

Không gọi AI/Mask thật, không đọc .env. CSDL kho_test_* giữ lại cho runner/lead dọn;
không DROP CSDL hay vai trò. Không đổi quyền của vai trò ở CSDL đang có.
"""
from __future__ import annotations

import json
import os
import re
import unittest
import uuid
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import MagicMock, Mock, patch

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import M0005, M0034_CONG_AI_NHAT_KY, PG_MIGRATIONS, PG_SCHEMA_VERSION
from kho_tri_thuc.tri_thuc import cong_ai as ca

try:
    import psycopg
    from psycopg.conninfo import make_conninfo
except ImportError:
    psycopg = None

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
MOI = {
    "ma_yeu_cau", "duong", "da_gui", "so_ky_tu_gui", "so_ky_tu_nhan", "ma_luot_mask",
    "ly_do_chuyen_cloud", "ly_do_khong_gui", "ket_qua", "ly_do", "so_truong_bi_loai",
}
CU = {
    "id", "phap_nhan_id", "luc", "loai_viec", "model", "nha_cung_cap", "cloud",
    "dau_vao_mask_hash", "token_vao", "token_ra", "chi_phi_uoc", "ket_qua_tom_tat",
    "trich_dan_hop_le", "viec_id", "de_xuat_id", "thoi_gian_ms", "loi",
}
VAN_BAN = "Hợp đồng DEMO có giá trị 123 đồng."
LOCAL_CFG = {"enabled": True, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "demo-local"}


def ban_ghi(**kw):
    return replace(ca.BanGhiCongAI(
        ma_yeu_cau=uuid.uuid4().hex, luc="2026-10-25T12:00:00+00:00",
        loai_viec="BOC_TACH_HOP_DONG", duong=ca.DUONG_LOCAL, nha_cung_cap="local",
        model="demo-local", da_gui=True, ket_qua="DAT",
    ), **kw)


def goi_local_va_cloud_tat(bo_ghi):
    # Local có kết quả hợp lệ nhưng dưới ngưỡng → Cloud không gửi vì công tắc tắt.
    noi_dung = json.dumps({"truong": [{"ten": "gia_tri", "gia_tri": "123 đồng",
                                     "trich_dan": VAN_BAN}], "do_tin_cay": 0.5}, ensure_ascii=False)
    gate = ca.CongAI({"local_ai": LOCAL_CFG}, bo_ghi=bo_ghi, moi_truong={})
    with patch.object(ca.ai_cuc_bo, "ask_local", return_value=noi_dung), \
            patch.object(ca, "MaskV2") as mask, patch.object(ca, "NhaCungCapAnthropic") as cloud:
        kq = gate.goi(ca.YeuCauAI("BOC_TACH_HOP_DONG", VAN_BAN, "Đọc giá trị", ("gia_tri",)))
    mask.assert_not_called()
    cloud.assert_not_called()
    return kq


class BoGhiPostgresThuan(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.__enter__.return_value = self.conn
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.factory = Mock(return_value=self.conn)
        self.bo = ca.BoGhiPostgres(self.factory)

    def test_anh_xa_day_du_va_tham_so_hoa(self):
        b = ban_ghi(so_ky_tu_gui=123, so_ky_tu_nhan=45, token_vao=67, token_ra=8,
                    thoi_gian_ms=91, chi_phi_uoc_usd=0.0123, ma_luot_mask="luot-DEMO",
                    ly_do_chuyen_cloud=("DUOI_NGUONG",), ly_do=("THIEU_TRUONG",),
                    ly_do_khong_gui="CLOUD_TAT", trich_dan_hop_le=True, so_truong_bi_loai=2,
                    loi="LOCAL_LOI", phap_nhan_id=str(uuid.uuid4()), viec_id=str(uuid.uuid4()),
                    de_xuat_id=str(uuid.uuid4()), model="demo-'%s-model")
        self.bo.ghi(b)
        self.cur.execute.assert_called_once()
        sql, args = self.cur.execute.call_args.args
        self.assertNotIn(b.model, sql)
        self.assertEqual(sql.count("%s"), len(args))
        cot = [x.strip() for x in sql.split("(", 1)[1].split(")", 1)[0].split(",")]
        row = dict(zip(cot, (*args, None, None)))
        mong = b.thanh_dict()
        mong["cloud"] = False
        mong["chi_phi_uoc"] = mong.pop("chi_phi_uoc_usd")
        mong["ly_do"] = list(mong["ly_do"])
        mong["ly_do_chuyen_cloud"] = list(mong["ly_do_chuyen_cloud"])
        mong.update(dau_vao_mask_hash=None, ket_qua_tom_tat=None)
        self.assertEqual(row, mong)
        self.conn.transaction.assert_called_once_with()
        self.conn.transaction.return_value.__exit__.assert_called_once_with(None, None, None)
        self.conn.__exit__.assert_called_once_with(None, None, None)

    def test_local_va_cloud_khong_gui_moi_duong_mot_dong_khong_noi_dung(self):
        kq = goi_local_va_cloud_tat(self.bo)
        self.assertTrue(kq.co_ket_qua)
        self.assertEqual(self.factory.call_count, 2)
        self.assertEqual(self.cur.execute.call_count, 2)
        rows = [c.args[1] for c in self.cur.execute.call_args_list]
        self.assertEqual(rows[0][0], rows[1][0])
        self.assertEqual((rows[0][3:5], rows[0][7]), (("LOCAL", False), True))
        self.assertEqual((rows[1][3:5], rows[1][7], rows[1][16:18]),
                         (("CLOUD", True), False, ("CLOUD_TAT", "KHONG_GUI")))
        self.assertNotIn(VAN_BAN, repr(rows))
        self.assertNotIn("123 đồng", repr(rows))

    def test_loi_ket_noi_insert_commit_dong_chi_log_ten_loi(self):
        for buoc in ("ket_noi", "insert", "commit", "dong"):
            with self.subTest(buoc=buoc):
                self.setUp()
                exc = RuntimeError("DEMO-bi-mat-DSN-noi-dung")
                if buoc == "ket_noi":
                    self.factory.side_effect = exc
                elif buoc == "insert":
                    self.cur.execute.side_effect = exc
                elif buoc == "commit":
                    self.conn.transaction.return_value.__exit__.side_effect = exc
                else:
                    self.conn.__exit__.side_effect = exc
                with self.assertLogs(ca.__name__, level="ERROR") as logs:
                    kq = goi_local_va_cloud_tat(self.bo)
                self.assertTrue(kq.co_ket_qua)
                self.assertEqual(len(logs.records), 2)
                for record in logs.records:
                    self.assertEqual(record.getMessage(), "Không ghi được nhật ký cổng AI (RuntimeError).")
                    self.assertIsNone(record.exc_info)
                if buoc == "insert":
                    self.assertIs(self.conn.transaction.return_value.__exit__.call_args.args[1], exc)

    def test_loi_mot_luot_khong_chan_luot_sau(self):
        self.cur.execute.side_effect = [RuntimeError("DEMO"), None]
        with self.assertLogs(ca.__name__, level="ERROR"):
            self.bo.ghi(ban_ghi())
        self.bo.ghi(ban_ghi())
        self.assertEqual(self.factory.call_count, 2)
        self.assertEqual(self.cur.execute.call_count, 2)


class MigrationThuan(unittest.TestCase):
    def test_dang_ky_m34_va_du_cot_khong_them_noi_dung(self):
        self.assertGreaterEqual(PG_SCHEMA_VERSION, 34)
        self.assertIs(PG_MIGRATIONS[33], M0034_CONG_AI_NHAT_KY)
        sql = "\n".join(M0034_CONG_AI_NHAT_KY)
        them = re.findall(r"ADD COLUMN (\w+)", sql)
        self.assertEqual(set(them), MOI)
        self.assertEqual(len(them), 11)
        self.assertNotRegex(sql, r"\b(?:UPDATE|DELETE)\s+nhat_ky\.")
        self.assertNotIn("DISABLE TRIGGER", sql)
        self.assertIn("CHECK (dau_vao_mask_hash IS NULL AND ket_qua_tom_tat IS NULL) NOT VALID", sql)
        # M0005 vẫn chứa trigger chỉ ghi thêm; M0034 không định nghĩa lại.
        self.assertTrue(any("CREATE TRIGGER cong_ai_goi_chi_ghi_them" in s for s in M0005))


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Thiếu psycopg hoặc KHO_PG_DSN_TEST — lead chạy PG")
class NhatKyPostgres(unittest.TestCase):
    @classmethod
    def tao_db(cls):
        ten = "kho_test_ai2b_" + uuid.uuid4().hex[:12]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            admin.execute(psycopg.sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(
                psycopg.sql.Identifier(ten)))
        return make_conninfo(ADMIN_DSN, dbname=ten)

    @classmethod
    def setUpClass(cls):
        # Vai trò có sẵn giữ nguyên thuộc tính; chỉ tạo NOLOGIN nếu chưa có.
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            for role in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
                if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                    admin.execute(psycopg.sql.SQL("CREATE ROLE {} NOLOGIN").format(psycopg.sql.Identifier(role)))
        cls.dsn = cls.tao_db()
        cls.conn = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.version = pg.migrate(cls.conn, target=34)

    @contextmanager
    def ket_noi_app(self):
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute("SET ROLE app_cong_ai")
            yield conn

    def test_migrate_sach_va_lap_lai(self):
        self.assertEqual(self.version, 34)
        self.assertEqual(pg.migrate(self.conn, target=34), 34)
        self.assertEqual(pg.schema_version(self.conn), 34)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM master.schema_migrations").fetchone()[0], 34)

    def test_ghi_local_va_cloud_khong_gui_bang_vai_ung_dung(self):
        kq = goi_local_va_cloud_tat(ca.BoGhiPostgres(self.ket_noi_app))
        rows = self.conn.execute("""SELECT duong, cloud, da_gui, ket_qua, ly_do_chuyen_cloud,
            ly_do_khong_gui, so_ky_tu_gui, so_ky_tu_nhan, dau_vao_mask_hash, ket_qua_tom_tat,
            token_vao, token_ra, chi_phi_uoc, ma_luot_mask
            FROM nhat_ky.cong_ai_goi WHERE ma_yeu_cau = %s ORDER BY duong DESC""", (kq.ma_yeu_cau,)).fetchall()
        self.assertTrue(kq.co_ket_qua)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][:4], ("LOCAL", False, True, "KHONG_CHAC"))
        self.assertEqual(rows[1][:6], ("CLOUD", True, False, "KHONG_GUI", ["DUOI_NGUONG"], "CLOUD_TAT"))
        self.assertGreater(rows[0][6], 0)
        self.assertGreater(rows[0][7], 0)
        self.assertEqual(rows[1][6:8], (0, 0))
        for row in rows:
            self.assertEqual(row[8:], (None,) * 6)

    def test_quyen_cac_vai_va_chan_update_delete_truncate(self):
        b = ban_ghi()
        ca.BoGhiPostgres(self.ket_noi_app).ghi(b)
        for role in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
            with self.subTest(role=role):
                for quyen in ("UPDATE", "DELETE", "TRUNCATE"):
                    self.assertFalse(self.conn.execute("SELECT has_table_privilege(%s, 'nhat_ky.cong_ai_goi', %s)",
                                                       (role, quyen)).fetchone()[0])
        for sql in ("UPDATE nhat_ky.cong_ai_goi SET model = model WHERE ma_yeu_cau = %s",
                    "DELETE FROM nhat_ky.cong_ai_goi WHERE ma_yeu_cau = %s"):
            with self.ket_noi_app() as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(sql, (b.ma_yeu_cau,))
            # Trigger sẵn có vẫn chặn cả chủ bảng.
            with self.assertRaisesRegex(psycopg.Error, "NHAT_KY_CHI_GHI_THEM"):
                self.conn.execute(sql, (b.ma_yeu_cau,))
        with self.ket_noi_app() as conn:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("TRUNCATE nhat_ky.cong_ai_goi")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM nhat_ky.cong_ai_goi WHERE ma_yeu_cau = %s",
                                           (b.ma_yeu_cau,)).fetchone()[0], 1)

    def test_catalog_chi_metadata_hai_cot_cu_buoc_null(self):
        cot = {r[0] for r in self.conn.execute("""SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'nhat_ky' AND table_name = 'cong_ai_goi'""")}
        self.assertEqual(cot, CU | MOI)
        for cot_cu in ("dau_vao_mask_hash", "ket_qua_tom_tat"):
            with self.assertRaises(psycopg.errors.CheckViolation):
                self.conn.execute(psycopg.sql.SQL("""INSERT INTO nhat_ky.cong_ai_goi
                    (loai_viec, model, nha_cung_cap, cloud, {}) VALUES ('DEMO', '', 'local', false, 'DEMO')""").format(
                        psycopg.sql.Identifier(cot_cu)))

    def test_nang_33_len_34_giu_nguyen_lich_su(self):
        with psycopg.connect(self.tao_db(), autocommit=True) as conn:
            self.assertEqual(pg.migrate(conn, target=33), 33)
            ma = conn.execute("""INSERT INTO nhat_ky.cong_ai_goi
                (loai_viec, model, nha_cung_cap, cloud, ket_qua_tom_tat)
                VALUES ('DEMO', 'demo-local', 'local', false, 'DEMO lich su') RETURNING id""").fetchone()[0]
            truoc = conn.execute("SELECT * FROM nhat_ky.cong_ai_goi WHERE id = %s", (ma,)).fetchone()
            hist = conn.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version").fetchall()
            self.assertEqual(pg.migrate(conn, target=34), 34)
            sau = conn.execute("SELECT * FROM nhat_ky.cong_ai_goi WHERE id = %s", (ma,)).fetchone()
            self.assertEqual(sau[:len(truoc)], truoc)
            self.assertEqual(sau[len(truoc):], (None,) * 11)
            self.assertEqual(conn.execute("SELECT version, checksum FROM master.schema_migrations WHERE version <= 33 ORDER BY version").fetchall(), hist)


if __name__ == "__main__":
    unittest.main()
