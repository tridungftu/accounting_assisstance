"""MTQ-4d1b: Python G1/G7, oracle CU và quyền trước blob/replay.

PG chỉ dùng KHO_PG_DSN_TEST, tự tạo kho_test_*; không xóa DB/tệp.
Đọc danh tính bằng app_web, nghiệp vụ qua kết nối chủ bảng và GUC phiên thật.
Giữ giới hạn HIEU_LUC của M0050 khi bật, không mở nháp/lịch sử.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest
from unittest import mock
import uuid

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_mau as M
from tests import test_mtq_crm_sql as crm
from tests import test_mtq_sql as nen


G1 = {
    "CRM_MAU_MAP": "SUA", "CRM_MAU_GUI_KIEM": "SUA",
    "CRM_MAU_KIEM": "KIEM", "CRM_MAU_TRA_LAI": "KIEM",
    "CRM_MAU_DUYET_V4": "DUYET", "CRM_MAU_TU_CHOI": "DUYET",
}
TODAY = date(2026, 10, 27)
ALL = crm.WRITE_ACTIONS | crm.READ_ACTIONS


class MtqMauThuTu(unittest.TestCase):
    def test_thieu_xem_tu_choi_truoc_moi_sql_metadata_va_token(self):
        pb = str(uuid.uuid4())
        expected_sql = ("SELECT master.mtq_duoc_doc('CRM:G1_MAU:XEM', "
                        "jsonb_build_object('bang', 'master.crm_mau_phien_ban', 'id', %s::uuid)) AS ok")
        for method in ("chi_tiet", "tep_mau"):
            with self.subTest(method=method):
                service = object.__new__(M.CrmMauK2)
                service.hom_nay = lambda: TODAY
                conn = mock.Mock()
                executed = []

                def execute(sql, params):
                    executed.append((sql, params))
                    # Mọi SELECT metadata/token sẽ lỗi nếu chạy trước từ chối.
                    self.assertEqual(sql, expected_sql)
                    self.assertEqual(params, (pb,))
                    return mock.Mock(fetchone=mock.Mock(return_value={"ok": False}))

                conn.execute.side_effect = execute
                with mock.patch.object(service, "danh_tinh", return_value={}), \
                        mock.patch.object(service, "_tx") as tx:
                    tx.return_value.__enter__.return_value = conn
                    with self.assertRaises(DataError) as cm:
                        getattr(service, method)("MO_PHONG_MTQ", pb)
                    self.assertEqual(cm.exception.code, "CRM_G_KHONG_THAY")
                self.assertEqual(executed, [(expected_sql, (pb,))])

    def test_ba_gia_tri_khong_or_and_quyen_cu(self):
        service = object.__new__(M.CrmMauK2)
        for matrix, legacy, full, expected in (
                (True, False, False, True), (False, True, True, False),
                (None, True, True, True), (None, False, True, False),
                (None, True, False, False)):
            with self.subTest(matrix=matrix, legacy=legacy, full=full):
                with mock.patch.object(service, "_mot", side_effect=[{"ok": matrix}, {"ok": legacy}]) as query:
                    self.assertIs(service._co_quyen(object(), "CRM:G1_MAU:SUA", "master.crm_mau_phien_ban",
                                                   str(uuid.uuid4()), "CRM_MAU_MAP", str(uuid.uuid4()),
                                                   str(uuid.uuid4()), day_du=full), expected)
                    self.assertEqual(query.call_count, 2 if matrix is None and full else 1)

    def test_tai_xuong_khong_doc_blob_khi_chi_tiet_tu_choi(self):
        service = object.__new__(M.CrmMauK2)
        service.root = Path("kho_test_mtq_khong_doc")
        with mock.patch.object(service, "chi_tiet", side_effect=DataError("CRM_G_KHONG_THAY", "Ngoài phạm vi.")), \
                mock.patch.object(Path, "is_file") as exists, mock.patch.object(Path, "read_bytes") as read:
            with self.assertRaises(DataError):
                service.tep_mau("MO_PHONG_MTQ", str(uuid.uuid4()))
            exists.assert_not_called()
            read.assert_not_called()


@unittest.skipUnless(nen.DSN and nen.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqMauPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    insert = crm.MtqCrmSqlPostgres.insert
    insert_dong = crm.MtqCrmSqlPostgres.insert_dong
    legacy = crm.MtqCrmSqlPostgres.legacy
    cau_hinh = crm.MtqCrmSqlPostgres.cau_hinh

    def fixture(self, pn):
        # Chỉ đổi nội dung tệp mẫu; giữ nguyên cách dựng fixture G1/G7 dùng chung.
        raw = b"MTQ_G1_G7_SYNTHETIC_" + uuid.uuid4().hex.encode("ascii")
        sha = M.sha256(raw)
        insert = self.insert

        def insert_unique_file(table, **data):
            if table == "master.crm_mau_tep":
                data.update(raw_sha256=sha, byte_length=len(raw),
                            object_key="crm-mau/" + sha, facts_sha256=sha)
            elif table == "master.crm_bo_chuan_phien_ban":
                data["dong_sha256"] = sha
            return insert(table, **data)

        with mock.patch.object(self, "insert", side_effect=insert_unique_file):
            result = crm.MtqCrmSqlPostgres.fixture(self, pn)
        result["sha"] = sha
        return result

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_giao_ket_" + uuid.uuid4().hex[:12]
        with nen.psycopg.connect(nen.DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        dsn = make_conninfo(nen.DSN, dbname=cls.db)
        cls.c = nen.psycopg.connect(dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)  # Không ghim migration cuối.
        cls.owner = nen.psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.owner.close)
        cls.app = nen.psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.app.close)
        cls.app.execute("SET ROLE app_web")
        login = "MO_PHONG_MTQ_ADMIN_" + uuid.uuid4().hex
        with cls.c.transaction():
            uid = cls.c.execute("INSERT INTO master.nguoi_dung(ten,dang_nhap,vai_tro) "
                                "VALUES ('Admin giả MTQ',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
            cls.admin = (uid, login)
            cls.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Bootstrap test tổng hợp')", (uid, uuid.uuid4()))

    def setUp(self):
        self.assertEqual(self.app.execute("SELECT current_user AS r").fetchone()["r"], "app_web")
        with self.c.transaction():
            self.pn = self.insert("master.phap_nhan", ma=uuid.uuid4().hex, ten="Pháp nhân A giả")
            self.pn2 = self.insert("master.phap_nhan", ma=uuid.uuid4().hex, ten="Pháp nhân B giả")
            self.user, self.sender, self.approver = (self.nguoi("XEM") for _ in range(3))
            self.actor(self.admin)
            self.phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn), "ma": "KT", "ten": "Phòng giả 1"})["id"]
            self.phong2 = self.ghi("PHONG", {"phap_nhan_id": str(self.pn), "ma": "DA", "ten": "Phòng giả 2"})["id"]
            self.f, self.f2 = self.fixture(self.pn), self.fixture(self.pn2)
            for pn, f in ((self.pn, self.f), (self.pn2, self.f2)):
                # Các trigger crm_*_phien_ban_kiem bắt INSERT DRAFT; chỉ sau đó
                # chủ bảng dựng trạng thái hiệu lực, không tắt trigger/ràng buộc.
                self.c.execute("UPDATE master.crm_mau_phien_ban SET trang_thai='HIEU_LUC',valid_from=%s WHERE id=%s",
                               (TODAY, f["mv"]))
                self.c.execute("UPDATE master.crm_bo_chuan_phien_ban SET trang_thai='HIEU_LUC',valid_from=%s WHERE id=%s",
                               (TODAY, f["cv"]))
                self.insert("master.crm_danh_muc_truong", phap_nhan_id=pn, loai_hinh_id=f["lh"],
                            danh_muc_ref="MTQ_PICKER", revision=1, khoa="ten", nhan="Tên giả", nhom="TEST",
                            kieu="text", dinh_dang="text", nguon="TEST", pii=False, bat_buoc=False,
                            xem_thu=nen.psycopg.types.json.Jsonb("Tên tổng hợp"))
        # Không ghi blob: tải bị chặn phải kết thúc trước mọi lần chạm filesystem.
        self.service = M.CrmMauK2(self.app, Path("kho_test_mtq_blob_khong_ton_tai"),
                                 conn_tin_cay=self.owner, chi_mo_phong=False, hom_nay=lambda: TODAY)

    def enable(self, actions=ALL, **kwargs):
        with self.c.transaction():
            return self.cau_hinh(actions=actions, **kwargs)

    def grant_old(self, who, pn=None, f=None):
        with self.c.transaction():
            self.legacy(who, pn or self.pn, f or self.f)

    def oracle(self, who, f, pn):
        """Nguyên SELECT M0018 trước M0050, không chép lại công thức vai cũ."""
        names = ("crm_g_mau_doc", "crm_g_chuan_doc_duoc", "crm_g_duoc")
        result = {}
        with self.c.transaction():
            self.actor(who)
            for name in names:
                body = crm.BEFORE["master." + name].split("AS $$", 1)[1].rsplit("$$", 1)[0].strip()
                sql = body + " FROM (SELECT %s::text AS p_hanh_dong,%s::uuid AS p_pn,%s::uuid AS p_loai) args"
                if name == "crm_g_duoc":
                    for command in crm.COMMANDS:
                        result[command] = self.c.execute(sql, (command, pn, f["lh"])).fetchone()[0]
                else:
                    result[name] = self.c.execute(sql, (None, pn, f["lh"])).fetchone()[0]
        return result

    def capture(self, who, f, pn):
        login = who[1]
        o = self.oracle(who, f, pn)
        detail = self.service.chi_tiet(login, str(f["mv"]))
        self.assertEqual(detail["quyen_doc"], o["crm_g_mau_doc"])
        self.assertEqual(detail["kha_nang"], {a: bool(o[a] and o["crm_g_mau_doc"] == "DAY_DU") for a in G1})
        listing = self.service.danh_sach(login)
        lh = next(a for a in listing["loai_hinh"] if a["id"] == str(f["lh"]))
        self.assertEqual(lh["duoc_tai"], o["CRM_MAU_TAI"])
        self.assertIn(str(f["mv"]), {v["phien_ban_id"] for v in listing["phien_ban"]})
        g7 = self.service.danh_sach_bo_chuan(login)
        da = next(a for a in g7["du_an"] if a["id"] == str(f["da"]))
        self.assertEqual(da["duoc_lap"], o["CRM_CHUAN_LAP"])
        versions = [v for v in g7["phien_ban"] if v["id"] == str(f["cv"])]
        self.assertEqual(bool(versions), o["crm_g_chuan_doc_duoc"])
        if versions:
            self.assertEqual(versions[0]["duoc_gui"], o["CRM_CHUAN_GUI_DUYET"])
            self.assertEqual(versions[0]["duoc_duyet"], o["CRM_CHUAN_DUYET_V4"])
        effective = self.service.doc_bo_chuan(login, str(f["da"]), "MTQ_TEST")
        self.assertEqual(effective["version"]["id"], str(f["cv"]))
        return detail, listing, g7, effective

    def test_pn_tat_co_va_ket_qua_dung_oracle_cu(self):
        for role in ("XEM", "BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO"):
            with self.subTest(role=role):
                who = self.nguoi(role)
                self.grant_old(who)
                self.capture(who, self.f, self.pn)

    def test_pn_tat_nguoi_chi_doc_hieu_luc_khong_duoc_nang_quyen(self):
        with self.c.transaction():
            self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['CRM'])",
                           (self.user[0], self.pn))
        self.capture(self.user, self.f, self.pn)

    def test_pn_tat_khong_quyen_cu_khong_doc_duoc_mau(self):
        o = self.oracle(self.user, self.f, self.pn)
        self.assertIsNone(o["crm_g_mau_doc"])
        with self.assertRaises(DataError):
            self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        self.assertNotIn(str(self.f["mv"]), {v["phien_ban_id"] for v in self.service.danh_sach(self.user[1])["phien_ban"]})

    def test_pn_bat_co_du_o_khong_can_module_vai_cu(self):
        self.enable()
        ct = self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        self.assertEqual(ct["quyen_doc"], "HIEU_LUC")  # Không tự mở facts/nháp/lịch sử.
        self.assertIsNone(ct["phat_hien"])
        self.assertTrue(all(ct["kha_nang"].values()))
        ds = self.service.danh_sach(self.user[1])
        self.assertTrue(next(a for a in ds["loai_hinh"] if a["id"] == str(self.f["lh"]))["duoc_tai"])
        g7 = self.service.danh_sach_bo_chuan(self.user[1])
        self.assertTrue(next(a for a in g7["du_an"] if a["id"] == str(self.f["da"]))["duoc_lap"])
        v = next(v for v in g7["phien_ban"] if v["id"] == str(self.f["cv"]))
        self.assertTrue(v["duoc_gui"])
        self.assertTrue(v["duoc_duyet"])

    def test_pn_bat_thieu_o_chan_du_vai_cu_cho_phep(self):
        self.user = self.nguoi("CFO")
        self.grant_old(self.user)
        self.enable(actions=crm.READ_ACTIONS)
        ct = self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        self.assertFalse(any(ct["kha_nang"].values()))
        ds = self.service.danh_sach(self.user[1])
        self.assertFalse(next(a for a in ds["loai_hinh"] if a["id"] == str(self.f["lh"]))["duoc_tai"])
        g7 = self.service.danh_sach_bo_chuan(self.user[1])
        self.assertFalse(next(a for a in g7["du_an"] if a["id"] == str(self.f["da"]))["duoc_lap"])
        v = next(v for v in g7["phien_ban"] if v["id"] == str(self.f["cv"]))
        self.assertFalse(v["duoc_gui"])
        self.assertFalse(v["duoc_duyet"])

    def test_o_khac_hanh_dong_khong_cap_cheo(self):
        self.enable(actions=crm.READ_ACTIONS | {"CRM:G1_MAU:KIEM", "CRM:G7_CHUAN:SUA"})
        ct = self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        self.assertEqual(ct["kha_nang"], {a: action == "KIEM" for a, action in G1.items()})
        g7 = self.service.danh_sach_bo_chuan(self.user[1])
        v = next(v for v in g7["phien_ban"] if v["id"] == str(self.f["cv"]))
        self.assertTrue(v["duoc_gui"])
        self.assertFalse(v["duoc_duyet"])

    def test_lap_khong_bi_doi_them_o_xem(self):
        self.enable(actions={"CRM:G1_MAU:LAP", "CRM:G7_CHUAN:LAP"})
        ds = self.service.danh_sach(self.user[1])
        self.assertTrue(next(a for a in ds["loai_hinh"] if a["id"] == str(self.f["lh"]))["duoc_tai"])
        g7 = self.service.danh_sach_bo_chuan(self.user[1])
        self.assertTrue(next(a for a in g7["du_an"] if a["id"] == str(self.f["da"]))["duoc_lap"])
        self.assertFalse(g7["phien_ban"])

    def test_xem_khong_tu_mo_nhap_va_lich_su(self):
        with self.c.transaction():
            draft = self.fixture(self.pn)
            self.c.execute("UPDATE master.crm_mau_phien_ban SET valid_to=%s WHERE id=%s", (date(2026, 10, 28), self.f["mv"]))
            self.c.execute("UPDATE master.crm_bo_chuan_phien_ban SET valid_to=%s WHERE id=%s", (date(2026, 10, 28), self.f["cv"]))
        self.enable()
        with self.assertRaises(DataError):
            self.service.chi_tiet(self.user[1], str(draft["mv"]))
        self.assertNotIn(str(draft["cv"]), {v["id"] for v in self.service.danh_sach_bo_chuan(self.user[1])["phien_ban"]})
        self.service.hom_nay = lambda: date(2026, 10, 28)
        with self.assertRaises(DataError):
            self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        self.assertNotIn(str(self.f["cv"]), {v["id"] for v in self.service.danh_sach_bo_chuan(self.user[1])["phien_ban"]})

    def test_tai_mau_bi_chan_truoc_blob_va_metadata_tep(self):
        self.user = self.nguoi("CFO")
        self.grant_old(self.user)
        self.enable(actions=crm.WRITE_ACTIONS)  # Thiếu XEM dù vai/assignment cũ đủ.
        with mock.patch.object(self.service, "_mot", wraps=self.service._mot) as query, \
                mock.patch.object(Path, "is_file") as exists, mock.patch.object(Path, "read_bytes") as read:
            with self.assertRaises(DataError) as cm:
                self.service.tep_mau(self.user[1], str(self.f["mv"]))
            self.assertEqual(cm.exception.code, "CRM_G_KHONG_THAY")
            self.assertEqual(query.call_count, 1)
            sql = query.call_args.args[1]
            self.assertIn("SELECT master.mtq_duoc_doc('CRM:G1_MAU:XEM'", sql)
            self.assertNotIn("FROM", sql.upper())
            self.assertNotIn("crm_g_mau_token", sql)
            self.assertFalse(any("FROM master.crm_mau_tep" in call.args[1] for call in query.call_args_list))
            exists.assert_not_called()
            read.assert_not_called()

    def test_tai_len_bi_chan_truoc_replay_parser_va_blob(self):
        self.enable(actions=crm.READ_ACTIONS)
        with mock.patch.object(self.service, "_tra_trong") as replay, \
                mock.patch.object(M, "doc_mau_docx") as parser, mock.patch.object(M, "write_immutable") as write:
            with self.assertRaises(DataError) as cm:
                self.service.tai_mau(self.user[1], b"synthetic", loai_hinh_id=str(self.f["lh"]),
                                     ma_mau="TEST", ten_tep="test.docx", khoa="MTQ_TEST")
            self.assertEqual(cm.exception.code, "CRM_G_KHONG_CO_QUYEN")
            replay.assert_not_called()
            parser.assert_not_called()
            write.assert_not_called()

    def replay_upload(self):
        raw, key = b"MTQ_UPLOAD_SYNTHETIC", "MTQ_REPLAY"
        args = {"loai_hinh_id": str(self.f["lh"]), "ma_mau": "TEST", "ten_tep": "test.docx", "khoa": key}
        digest = M._h("CRM_MAU_TAI", {k: v for k, v in args.items() if k != "khoa"} |
                      {"raw_sha256": M.sha256(raw), "byte_length": len(raw)})
        result = {"phien_ban_id": str(self.f["mv"]), "synthetic": True}
        with self.c.transaction():
            self.actor(self.user)
            self.c.execute("SELECT master.crm_g_bn_ghi(%s,'CRM_MAU_TAI',%s,%s,%s)",
                           (self.pn, key, digest, nen.psycopg.types.json.Jsonb(result)))
        with mock.patch.object(M, "doc_mau_docx") as parser, mock.patch.object(M, "write_immutable") as write:
            self.assertEqual(self.service.tai_mau(self.user[1], raw, **args), {**result, "lap_lai": True})
            parser.assert_not_called()
            write.assert_not_called()
        return raw, args

    def test_pn_tat_tai_len_giu_replay_cu_truoc_parser_blob(self):
        self.grant_old(self.user)
        self.replay_upload()

    def test_thu_hoi_khong_tra_replay_tai_len_da_co(self):
        grants = self.enable(actions={"CRM:G1_MAU:LAP"})
        raw, args = self.replay_upload()
        with self.c.transaction():
            self.actor(self.admin)
            self.ghi("THU_HOI_VAI", {"id": grants[0]["id"]}, grants[0]["revision"])
        with mock.patch.object(self.service, "_tra_trong") as replay, \
                mock.patch.object(M, "doc_mau_docx") as parser, mock.patch.object(M, "write_immutable") as write:
            with self.assertRaises(DataError) as cm:
                self.service.tai_mau(self.user[1], raw, **args)
            self.assertEqual(cm.exception.code, "CRM_G_KHONG_CO_QUYEN")
            replay.assert_not_called()
            parser.assert_not_called()
            write.assert_not_called()

    def test_thu_hoi_truoc_tai_xuong_khong_doc_blob(self):
        grants = self.enable()
        self.service.chi_tiet(self.user[1], str(self.f["mv"]))
        with self.c.transaction():
            self.actor(self.admin)
            self.ghi("THU_HOI_VAI", {"id": grants[0]["id"]}, grants[0]["revision"])
        with mock.patch.object(Path, "is_file") as exists, mock.patch.object(Path, "read_bytes") as read:
            with self.assertRaises(DataError):
                self.service.tep_mau(self.user[1], str(self.f["mv"]))
            exists.assert_not_called()
            read.assert_not_called()

    def test_pn_a_bat_khong_doi_pn_b_tat(self):
        self.user = self.nguoi("CFO")
        self.grant_old(self.user, self.pn2, self.f2)
        before = self.capture(self.user, self.f2, self.pn2)
        self.enable(actions=())
        self.assertEqual(self.capture(self.user, self.f2, self.pn2), before)

    def test_pham_vi_hep_khong_lo_du_an_ngoai_pham_vi(self):
        with self.c.transaction():
            other = self.fixture(self.pn)
        self.enable(scope="DU_AN", key=self.f["da"])
        g7 = self.service.danh_sach_bo_chuan(self.user[1])
        self.assertIn(str(self.f["da"]), {a["id"] for a in g7["du_an"]})
        self.assertNotIn(str(other["da"]), {a["id"] for a in g7["du_an"]})
        with self.assertRaises(DataError):
            self.service.chi_tiet(self.user[1], str(self.f["mv"]))  # G1 không thuộc scope DU_AN.


if __name__ == "__main__":
    unittest.main()
