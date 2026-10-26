"""XS-1B: wrapper và PG riêng, dữ liệu giả, giữ nguyên FK/trigger/RLS thật.

PYTHONPATH=src python -B -X utf8 -m unittest discover -s tests -p test_xs1_bus.py -v
PG chỉ dùng KHO_PG_DSN_TEST (quản trị), tự tạo kho_test_*; không mở server,
không đọc cấu hình/DSN DEMO, không xóa tệp/role/CSDL, kể cả lúc cleanup.
Thiếu Python: NOT_RUN; thiếu psycopg/DSN: skip PG, lead chạy sau.
"""

from __future__ import annotations

import inspect
import json
import os
import unittest
from unittest.mock import MagicMock
import uuid

from kho_tri_thuc.ha_tang.bus_su_kien import ack, nhan, phat

try:
    import psycopg
except ImportError:
    psycopg = None


DSN = os.environ.get("KHO_PG_DSN_TEST")


class BusPython(unittest.TestCase):
    def setUp(self):
        # spec cấm wrapper tự quản lý giao dịch hoặc kết nối khác.
        self.conn = MagicMock(spec=["cursor"])
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.pn = uuid.uuid4()
        self.event = uuid.uuid4()

    def test_tham_so_nguon_phap_nhan_va_module_la_keyword_only(self):
        for fn in (phat, nhan, ack):
            self.assertEqual(inspect.signature(fn).parameters["phap_nhan_id"].kind,
                             inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(inspect.signature(phat).parameters["ben_phat"].kind,
                         inspect.Parameter.KEYWORD_ONLY)

    def test_phat_tham_so_hoa_json_khong_sua_dau_vao(self):
        payload = {"chung_tu_id": str(uuid.uuid4()), "lien_ket_ids": []}
        self.cur.fetchone.return_value = (self.event,)
        self.assertEqual(phat(self.conn, "GIA_'_%s", 2, "khoa_'_%s", payload,
                              phap_nhan_id=self.pn, ben_phat="M2"), self.event)
        statement, params = self.cur.execute.call_args.args
        self.assertEqual(statement, "SELECT bus.phat(%s,%s,%s,%s,%s,%s::jsonb) AS id")
        self.assertEqual(params[:5], (self.pn, "M2", "GIA_'_%s", 2, "khoa_'_%s"))
        self.assertEqual(json.loads(params[5]), payload)
        self.assertEqual(payload["lien_ket_ids"], [])
        self.conn.cursor.return_value.__exit__.assert_called_once()

    def test_dict_row_va_nhan_giu_nguyen_row_factory(self):
        self.cur.fetchone.return_value = {"id": self.event}
        self.assertEqual(phat(self.conn, "GIA", 1, "gia", {"chung_tu_ids": []},
                              phap_nhan_id=self.pn, ben_phat="M2"), self.event)
        rows = [{"id": self.event, "phap_nhan_id": self.pn}]
        self.cur.fetchall.return_value = rows
        self.assertIs(nhan(self.conn, "M4", phap_nhan_id=self.pn), rows)
        self.cur.execute.assert_called_with("SELECT * FROM bus.nhan(%s,%s,%s,%s)",
                                            (self.pn, "M4", None, 100))
        for value in (True, False):
            self.cur.fetchone.return_value = {"da_ack": value}
            self.assertIs(ack(self.conn, "M4", self.event, phap_nhan_id=self.pn), value)

    def test_loi_sql_truyen_nguyen_khong_tu_rollback_hay_thu_lai(self):
        error = RuntimeError("lỗi SQL giả")
        self.cur.execute.side_effect = error
        calls = (
            lambda: phat(self.conn, "GIA", 1, "gia", {"chung_tu_ids": []},
                         phap_nhan_id=self.pn, ben_phat="M2"),
            lambda: nhan(self.conn, "M4", phap_nhan_id=self.pn),
            lambda: ack(self.conn, "M4", self.event, phap_nhan_id=self.pn),
        )
        for call in calls:
            self.cur.execute.reset_mock()
            with self.assertRaises(RuntimeError) as cm:
                call()
            self.assertIs(cm.exception, error)
            self.cur.execute.assert_called_once()


@unittest.skipUnless(DSN and psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class BusPythonPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_xs1b_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")
        self.pn = self.them_pn()
        self.pn2 = self.them_pn()
        self.login = "XS1B_GIA_" + uuid.uuid4().hex
        self.user = self.them_user(self.login)
        self.quyen(self.user, self.pn)
        self.du_an = self.c.execute(
            "INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) "
            "VALUES (%s,%s,'Dự án giả XS1B') RETURNING id",
            (self.pn, "XS1B_" + uuid.uuid4().hex)).fetchone()[0]
        # Kết quả giả của consumer, chỉ trong giao dịch test; không sửa schema app.
        self.c.execute("CREATE TEMP TABLE ket_qua_xs1b "
                       "(su_kien_id uuid PRIMARY KEY, ket_qua text NOT NULL)")
        self.c.execute("GRANT SELECT, INSERT ON ket_qua_xs1b TO app_web")
        self.dat_phien(self.user, self.login)
        # Lấy PN từ đối tượng đã đọc qua RLS trong phiên app_web.
        self.pn = self.c.execute("SELECT phap_nhan_id FROM master.du_an WHERE id=%s",
                                 (self.du_an,)).fetchone()[0]
        self.payload = {"du_an_id": str(self.du_an)}

    def them_pn(self):
        return self.c.execute(
            "INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,'Pháp nhân giả XS1B') RETURNING id",
            ("XS1B_" + uuid.uuid4().hex,)).fetchone()[0]

    def them_user(self, login):
        return self.c.execute(
            "INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
            "VALUES ('Người giả XS1B',%s,'XEM') RETURNING id", (login,)).fetchone()[0]

    def quyen(self, user, pn):
        self.c.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) "
                       "VALUES (%s,%s,%s)", (user, pn, ["M2", "M3", "M4"]))

    def dat_phien(self, user, login):
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true), "
                       "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(user), login))
        self.c.execute("SET LOCAL ROLE app_web")

    def phat(self, khoa="gia-1", loai="HOA_DON_DA_NHAN", payload=None):
        return phat(self.c, loai, 1, khoa, self.payload if payload is None else payload,
                    phap_nhan_id=self.pn, ben_phat="M2")

    def ids(self, ben="M4", loai=None, gioi_han=100, pn=None):
        return [r[0] for r in nhan(self.c, ben, loai, gioi_han,
                                  phap_nhan_id=self.pn if pn is None else pn)]

    def dem_inbox(self):
        return self.c.execute("SELECT count(*) FROM bus.inbox").fetchone()[0]

    def test_phat_cung_nghiep_vu_rollback_khong_con(self):
        with self.assertRaisesRegex(RuntimeError, "rollback giả"):
            with self.c.transaction():
                # Một ghi nghiệp vụ giả và phát trên chính kết nối.
                nghiep_vu = uuid.uuid4()
                self.c.execute("INSERT INTO ket_qua_xs1b VALUES (%s,'giả')", (nghiep_vu,))
                event = self.phat()
                self.assertEqual(self.ids(), [event])
                raise RuntimeError("rollback giả")
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.dem_inbox(), 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM ket_qua_xs1b").fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien WHERE id=%s",
                                        (event,)).fetchone()[0], 0)

    def test_phat_dedupe_va_xung_dot_khong_them_dong(self):
        event = self.phat()
        self.assertEqual(self.phat(), event)
        with self.assertRaisesRegex(psycopg.Error, "BUS_DEDUPE_XUNG_DOT"):
            with self.c.transaction():
                self.phat(payload={"chung_tu_id": str(uuid.uuid4())})
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien").fetchone()[0], 1)

    def test_hai_ben_nhan_doc_lap_nhan_lai_khong_them_inbox(self):
        event = self.phat()
        self.assertEqual(self.ids(), [event])
        self.assertEqual(self.ids(), [event])
        self.assertEqual(self.dem_inbox(), 1)
        self.assertEqual(self.ids("M3"), [event])
        self.assertTrue(ack(self.c, "M4", event, phap_nhan_id=self.pn))
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.ids("M3"), [event])
        self.assertEqual(self.dem_inbox(), 2)

    def test_ack_lap_khong_nhan_doi_ket_qua_hay_doi_metadata(self):
        event = self.phat()
        for row in nhan(self.c, "M4", phap_nhan_id=self.pn):
            self.c.execute("INSERT INTO ket_qua_xs1b VALUES (%s,'xong giả')", (row[0],))
            self.assertTrue(ack(self.c, "M4", row[0], phap_nhan_id=self.pn))
        before = self.c.execute("SELECT ack_luc,ack_boi FROM bus.inbox").fetchall()
        self.assertFalse(ack(self.c, "M4", event, phap_nhan_id=self.pn))
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.c.execute("SELECT ack_luc,ack_boi FROM bus.inbox").fetchall(), before)
        self.assertEqual(self.c.execute("SELECT count(*) FROM ket_qua_xs1b").fetchone()[0], 1)

    def test_loi_truoc_va_sau_ack_rollback_ca_ket_qua_va_ack(self):
        event = self.phat()
        self.assertEqual(self.ids(), [event])
        for sau_ack in (False, True):
            with self.subTest(sau_ack=sau_ack):
                with self.assertRaisesRegex(RuntimeError, "rollback giả"):
                    with self.c.transaction():
                        self.c.execute("INSERT INTO ket_qua_xs1b VALUES (%s,'xong giả')", (event,))
                        if sau_ack:
                            self.assertTrue(ack(self.c, "M4", event, phap_nhan_id=self.pn))
                        raise RuntimeError("rollback giả")
                self.assertEqual(self.c.execute("SELECT count(*) FROM ket_qua_xs1b").fetchone()[0], 0)
                self.assertEqual(self.c.execute("SELECT trang_thai,ack_luc,ack_boi FROM bus.inbox")
                                 .fetchone(), ("CHO", None, None))
                self.assertEqual(self.ids(), [event])
        # Retry thành công ghi đúng một kết quả và không giao lại.
        with self.c.transaction():
            self.c.execute("INSERT INTO ket_qua_xs1b VALUES (%s,'xong giả')", (event,))
            self.assertTrue(ack(self.c, "M4", event, phap_nhan_id=self.pn))
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.c.execute("SELECT count(*) FROM ket_qua_xs1b").fetchone()[0], 1)

    def test_loc_loai_gioi_han_va_ack_chua_nhan(self):
        event = self.phat()
        self.phat("khac", "KHAC")
        self.assertEqual(self.ids(loai="HOA_DON_DA_NHAN", gioi_han=1), [event])
        with self.assertRaisesRegex(psycopg.Error, "BUS_CHUA_NHAN"):
            with self.c.transaction():
                ack(self.c, "M3", event, phap_nhan_id=self.pn)
        for gioi_han in (0, 1001):
            with self.assertRaisesRegex(psycopg.Error, "BUS_GIOI_HAN"):
                with self.c.transaction():
                    self.ids(gioi_han=gioi_han)

    def test_sai_phap_nhan_khong_thay_va_khong_phat_nhan_ack(self):
        event = self.phat()
        self.ids()
        self.c.execute("RESET ROLE")
        login = "XS1B_KHAC_" + uuid.uuid4().hex
        user = self.them_user(login)
        self.quyen(user, self.pn2)
        self.dat_phien(user, login)
        self.assertIsNone(self.c.execute("SELECT phap_nhan_id FROM master.du_an WHERE id=%s",
                                          (self.du_an,)).fetchone())
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien").fetchone()[0], 0)
        self.assertEqual(self.dem_inbox(), 0)
        self.assertEqual(self.ids(pn=self.pn2), [])
        for call in (self.phat, self.ids,
                     lambda: ack(self.c, "M4", event, phap_nhan_id=self.pn)):
            with self.assertRaisesRegex(psycopg.errors.InsufficientPrivilege, "BUS_PHAM_VI"):
                with self.c.transaction():
                    call()


if __name__ == "__main__":
    unittest.main()
