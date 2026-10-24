"""V13 legacy backup safety (GIAO-SUA-V13-LEGACY-BACKUP-01/02) — phần không cần PostgreSQL.

- Fixture DEMO tự chứa (F1): cấu hình DEMO viết mới (tạo độc quyền), tệp raw DEMO tạo độc quyền, kho SQLite migrate mới rồi seed
  TRỰC TIẾP bằng SQL legacy vào ĐỦ 49 bảng (không qua ``Store.ingest`` — tránh ``write_immutable`` unlink tệp tạm dưới guard).
  Có documents.amount_minor = 0 / NULL / 9007199254740993 và rowid ẩn 9007199254740993. Không xóa gì.
- Hợp đồng đích mới: 49 bảng ứng dụng + schema_migrations, seed duy nhất knowledge_epoch=(1,'initial'); bảng INTEGER PRIMARY KEY.
- Phân loại đích SQLite: mới đúng seed nhận; cash-only / knowledge-only / seed đổi / dòng thêm / dấu nạp / bảng lạ / schema cũ /
  schema_migrations sai shape (không PK, dòng trùng) từ chối — không đọc lịch sử qua dict.
- Đối chiếu nội dung (F4): đổi giá trị rowid nhưng giữ nguyên thứ tự/nội dung bị phát hiện; bản sao nguyên vẹn khớp (control dương).
- Chép PG → SQLite: đích có dữ liệu bị từ chối TRƯỚC mọi lệnh tới PostgreSQL (nguồn giả); control dương tới bước đọc PG.
Tệp nằm trong thư mục tạm riêng được giữ lại (không xóa).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import an_toan_sao_chep as at
from kho_tri_thuc.ha_tang import database
from kho_tri_thuc.ha_tang.ket_noi import DAU_NAP_XONG
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.sao_chep_bang import bang_theo_thu_tu, chep_pg_sang_sqlite, doi_chieu_noi_dung, van_tay_sqlite

ROOT_TMP = Path(tempfile.mkdtemp(prefix="ktt_v13_backup_safety_"))  # giữ lại làm bằng chứng

# ---------------------------------------------------------------------------------------------- fixture DEMO tự chứa (F1)
ENTITY = "DEMO_V13_FIXTURE"
CONFIG_DEMO = (f'[app]\nentity_id = "{ENTITY}"\nenvironment = "fixture"\ndata_dir = "kho"\n\n[money]\ncurrency = "VND"\nscale = 0\n').encode("utf-8")
RAW_DEMO = b"DEMO V13 BACKUP RAW FIXTURE\nkhong phai du lieu that\n"
INT_LON = 9007199254740993  # 2^53 + 1: không biểu diễn đúng bằng số thực
_GHI_DE = {  # giá trị thỏa CHECK/khóa; còn lại sinh theo kiểu cột
    ("attempts", "state"): "COMMITTED", ("knowledge_versions", "supersedes_id"): None, ("knowledge_events", "action"): "APPROVE",
    ("historical_links", "level"): "LINK_A", ("sessions", "mode"): "fixture", ("sessions", "state"): "CLOSED",
    ("allocations", "state"): "RESERVED", ("decisions", "action"): "APPROVE", ("export_batches", "state"): "EXPORTED",
    ("export_batches", "target"): "fixture", ("label_events", "action"): "ACTIVATE", ("document_observations", "status"): "MATCHED",
    ("export_item_lines", "state"): "READY", ("shadow_exports", "state"): "SHADOW_PREPARED",
    ("knowledge_review_requests", "action"): "APPROVE_REQUEST", ("quick_items", "state"): "WAIT", ("quick_items", "excluded_from_export"): 0,
    ("cash_account_mappings", "source"): "MANUAL", ("bank_journal_matches", "state"): "UNIQUE",
    ("bank_journal_matches", "excluded_from_export"): 1, ("quick_condition_learning", "condition_type"): "KEYWORD",
    ("quick_condition_learning", "active"): 1,
}


def _tao_doc_quyen(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:  # tạo mới độc quyền, không ghi đè, không tệp tạm
        f.write(data)


def seed_49(conn: sqlite3.Connection, raw_hash: str, raw_len: int, cfg_digest: str, cfg_bytes: bytes) -> None:
    """Seed TRỰC TIẾP bằng SQL legacy vào đủ 49 bảng (FK hợp lệ, CHECK thỏa). knowledge_epoch giữ seed migration (trigger tự đổi)."""
    them = {
        "workspace_meta": [{"key": "entity_id", "value": ENTITY}, {"key": "environment", "value": "fixture"}],
        "config_history": [{"hash": cfg_digest, "contents": cfg_bytes}],
        "artifacts": [{"hash": raw_hash, "relative_path": f"raw/{raw_hash}.bin", "byte_length": raw_len}],
        "documents": [{"rowid": 1, "id": "DOC-0", "natural_key": "N0", "amount_minor": 0},
                      {"rowid": 2, "id": "DOC-NULL", "natural_key": "N1", "amount_minor": None, "currency": None},
                      {"rowid": INT_LON, "id": "DOC-LON", "natural_key": "N2", "amount_minor": INT_LON}],
        "cash_account_mappings": [{"bank_account": "SRC-00009001"}, {"bank_account": "SRC-00009002"}],
    }
    dong: dict[str, dict] = {}
    conn.execute("BEGIN IMMEDIATE")
    for t in at.bang_ung_dung():
        if t == "knowledge_epoch":
            continue
        info = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        fks = {r[3]: (r[2], r[4]) for r in conn.execute(f'PRAGMA foreign_key_list("{t}")')}
        for k, extra in enumerate(them.get(t, [{}])):
            vals = {}
            for _, name, typ, _, _, pk in info:
                if (t, name) in _GHI_DE:
                    v = _GHI_DE[(t, name)]
                elif name in fks:
                    v = dong[fks[name][0]][fks[name][1]]
                elif typ.upper() == "INTEGER":
                    v = 1 if pk else 7
                elif typ.upper() == "REAL":
                    v = 0.5
                elif typ.upper() == "BLOB":
                    v = b"DEMO"
                else:
                    v = f"DEMO-{t}-{name}"
                vals[name] = v
            vals.update(extra)
            cols = list(vals)
            conn.execute(f'INSERT INTO "{t}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({",".join("?" * len(cols))})',
                         [vals[c] for c in cols])
            if k == 0:
                dong[t] = vals
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise AssertionError("FIXTURE_FK")
    conn.execute("COMMIT")


def tao_kho_demo(thu_muc: Path) -> dict:
    """Thư mục DEMO mới: cấu hình DEMO (bytes viết mới), raw DEMO, kho.sqlite đủ 49 bảng. Trả đường dẫn + hash; không xóa gì."""
    cfg = thu_muc / "cau_hinh.demo.toml"
    _tao_doc_quyen(cfg, CONFIG_DEMO)
    kho = thu_muc / "kho"
    raw_hash = hashlib.sha256(RAW_DEMO).hexdigest()
    _tao_doc_quyen(kho / "raw" / f"{raw_hash}.bin", RAW_DEMO)
    with contextlib.closing(database.connect(kho / "kho.sqlite")) as conn:
        seed_49(conn, raw_hash, len(RAW_DEMO), hashlib.sha256(CONFIG_DEMO).hexdigest(), CONFIG_DEMO)
        dem = {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in at.bang_ung_dung()}
    if len(dem) != 49 or not all(dem.values()):
        raise AssertionError("FIXTURE_CHUA_DU_49")
    return {"config": cfg, "kho": kho, "db": kho / "kho.sqlite", "raw_hash": raw_hash, "dem": dem}


def chuan_tac_sqlite(conn: sqlite3.Connection) -> dict:
    """Oracle độc lập: 49 bảng, [rowid, giá trị] có tag kiểu, theo rowid; workspace_meta bỏ đúng khóa dấu nạp."""
    out = {}
    for t in at.bang_ung_dung():
        cols = at.hop_dong()["cols"][t]
        where = f" WHERE key <> '{DAU_NAP_XONG}'" if t == "workspace_meta" else ""
        out[t] = [tuple((type(v).__name__, v) for v in r) for r in conn.execute(
            f'SELECT rowid, {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{t}"{where} ORDER BY rowid')]
    return out


# ---------------------------------------------------------------------------------------------- tiện ích
def _kho_moi(ten: str) -> sqlite3.Connection:
    return database.connect(ROOT_TMP / f"{ten}.sqlite")


def _anh(conn) -> dict:
    """Ảnh độc lập của đích: mọi bảng (gồm schema_migrations) theo rowid + giá trị có tag kiểu, PRAGMA, đối tượng schema."""
    out = {}
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        h = hashlib.sha256()
        for row in conn.execute(f'SELECT rowid, * FROM "{t}" ORDER BY rowid'):
            h.update(json.dumps([[type(v).__name__, v.hex() if isinstance(v, bytes) else v] for v in row]).encode())
        out[t] = h.hexdigest()
    out["__pragma__"] = [conn.execute(f"PRAGMA {p}").fetchone()[0] for p in ("foreign_keys", "user_version", "application_id")]
    out["__schema__"] = sorted(tuple(r) for r in conn.execute("SELECT type, name, sql FROM sqlite_master"))
    return out


class _NguonGia:
    """Nguồn PostgreSQL giả: ghi lại mọi lệnh tới raw; schema_version đúng phiên bản; không có kết nối thật (không phải full PG)."""

    schema = "v12_demo_gia"
    in_transaction = False

    def __init__(self):
        self.lenh = []
        nguon = self

        class _Raw:
            def execute(self, sql, params=None):
                nguon.lenh.append(sql.split()[0])
                raise RuntimeError("DUNG_O_DOC_PG")  # control dương dừng tại đây (đã qua guard)

            def cursor(self, *a, **k):
                nguon.lenh.append("cursor")
                raise RuntimeError("DUNG_O_DOC_PG")

        self.raw = _Raw()

    def schema_version(self):
        return database.SCHEMA_VERSION


class HopDongTests(unittest.TestCase):
    def test_49_bang_va_seed_duy_nhat(self):
        hd = at.hop_dong()
        self.assertEqual(len(hd["tables"]), 49)
        self.assertNotIn("schema_migrations", hd["tables"])
        self.assertEqual(hd["seed"], {"knowledge_epoch": [(1, "initial")]})
        self.assertEqual(bang_theo_thu_tu(), list(hd["tables"]))  # một nguồn danh sách bảng
        self.assertEqual(len(hd["history"]), database.SCHEMA_VERSION)
        self.assertEqual(at.cot_alias_rowid("issues"), "id")  # INTEGER PRIMARY KEY: rowid canonical là cột id
        self.assertIsNone(at.cot_alias_rowid("documents"))  # TEXT PK: rowid ẩn
        cu = at.hop_dong(database.SCHEMA_VERSION - 1)
        self.assertEqual(cu["version"], database.SCHEMA_VERSION - 1)
        self.assertLessEqual(len(cu["tables"]), 49)

    def test_shape_schema_migrations_hang_khop_ddl(self):
        """Hằng shape schema_migrations khớp đúng câu tạo bảng trong hợp đồng SQLite (cùng chữ ký cột/PK)."""
        sql = next(o[3] for o in at.hop_dong()["sqlite_objects"] if o[1] == "schema_migrations")
        self.assertIn("version INTEGER PRIMARY KEY", sql)
        self.assertEqual([c[0] for c in at.SCHEMA_MIGRATIONS_COT], ["version", "checksum", "applied_at"])
        self.assertEqual(at.SCHEMA_MIGRATIONS_RANG_BUOC, (("p", "PRIMARY KEY (version)"),))


class FixtureDemoTests(unittest.TestCase):
    def test_fixture_tu_chua_du_49_bang_khong_rong(self):
        d = tao_kho_demo(ROOT_TMP / "fixture-49")
        self.assertEqual((len(d["dem"]), all(d["dem"].values())), (49, True))
        self.assertTrue(d["config"].read_bytes() == CONFIG_DEMO and (d["kho"] / "raw" / f"{d['raw_hash']}.bin").read_bytes() == RAW_DEMO)
        with contextlib.closing(sqlite3.connect(d["db"])) as c:  # chỉ SELECT
            docs = {r[0]: (r[1], r[2]) for r in c.execute("SELECT id, rowid, amount_minor FROM documents")}
            self.assertEqual(docs, {"DOC-0": (1, 0), "DOC-NULL": (2, None), "DOC-LON": (INT_LON, INT_LON)})
            self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])


class DoiChieuRowidTests(unittest.TestCase):
    def test_doi_gia_tri_rowid_giu_thu_tu_bi_phat_hien(self):
        d = tao_kho_demo(ROOT_TMP / "rowid-nguon")
        cot = lambda t: at.hop_dong()["cols"][t]  # noqa: E731
        with contextlib.closing(sqlite3.connect(d["db"])) as src:
            for ten, sua in (("nguyen", None), ("doi_rowid_cash", "UPDATE cash_account_mappings SET rowid = rowid + 1000"),
                             ("doi_rowid_documents", f"UPDATE documents SET rowid = rowid + 5 WHERE rowid < {INT_LON}")):
                with self.subTest(ten):
                    dst_path = ROOT_TMP / f"rowid-{ten}.sqlite"
                    with contextlib.closing(sqlite3.connect(dst_path)) as dst:
                        src.backup(dst)
                        if sua:
                            dst.execute(sua)
                            dst.commit()
                        kq = doi_chieu_noi_dung(src, van_tay_sqlite(dst), cot)
                    lech = sorted(t for t, v in kq.items() if not v["khop"])
                    mong = [] if sua is None else [sua.split()[1]]
                    self.assertEqual(lech, mong)  # cùng số dòng, cùng thứ tự, cùng nội dung; chỉ giá trị rowid khác
                    self.assertTrue(all(v["nguon"] == v["dich"] for v in kq.values()))


class PhanLoaiSqliteTests(unittest.TestCase):
    def test_moi_dung_seed_duoc_nhan(self):
        c = _kho_moi("moi")
        self.assertEqual(at.phan_loai_sqlite(c)["trang_thai"], at.MOI_KHOP)
        at.tu_choi_neu_khong_moi(at.phan_loai_sqlite(c), dich="sqlite")

    def test_cac_dich_co_du_lieu_bi_tu_choi_PG_NAP_DO(self):
        ca = {
            "cash_only": "INSERT INTO cash_account_mappings VALUES ('00009001','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')",
            "knowledge_only": "INSERT INTO knowledge_versions (id,category,logical_key,revision,payload_json,content_hash,valid_from,known_at,evidence_json,created_at,actor) "
                              "VALUES ('k-demo','KEYWORD','DEMO',1,'{}','h','2026-01-01','2026-01-01T00:00:00Z','{}','2026-01-01T00:00:00Z','MO_PHONG')",
            "seed_doi": "UPDATE knowledge_epoch SET revision='khac' WHERE id=1",
            "seed_xoa": "DELETE FROM knowledge_epoch",
            "dong_them": "INSERT INTO workspace_meta VALUES ('ghi_chu','DEMO')",
            "dau_nap": f"INSERT INTO workspace_meta VALUES ('{DAU_NAP_XONG}','{{}}')",
        }
        for ten, sql in ca.items():
            with self.subTest(ten):
                c = _kho_moi("co-du-lieu-" + ten)
                c.execute(sql)
                tt = at.phan_loai_sqlite(c)
                self.assertEqual(tt["trang_thai"], at.CO_DU_LIEU)
                self.assertEqual(tt["dau"], ten == "dau_nap")
                with self.assertRaises(DataError) as ctx:
                    at.tu_choi_neu_khong_moi(tt, dich="sqlite")
                self.assertEqual(ctx.exception.code, "PG_NAP_DO")

    def test_bang_la_va_schema_cu(self):
        c = _kho_moi("bang-la")
        c.execute("CREATE TABLE demo_la (a INTEGER)")
        self.assertEqual(at.phan_loai_sqlite(c)["trang_thai"], at.KHONG_TUONG_THICH)
        with self.assertRaises(DataError) as ctx:
            at.tu_choi_neu_khong_moi(at.phan_loai_sqlite(c), dich="sqlite")
        self.assertEqual(ctx.exception.code, "SQLITE_DICH_KHONG_TUONG_THICH")
        c.execute("INSERT INTO demo_la VALUES (1)")
        self.assertEqual(at.phan_loai_sqlite(c)["trang_thai"], at.CO_DU_LIEU)  # bảng lạ có dòng cũng là dữ liệu đích
        cu = sqlite3.connect(ROOT_TMP / "cu.sqlite", isolation_level=None)
        database.migrate(cu, database.SCHEMA_VERSION - 1)
        self.assertEqual(at.phan_loai_sqlite(cu)["trang_thai"], at.CU)
        with self.assertRaises(DataError) as ctx:
            at.tu_choi_neu_khong_moi(at.phan_loai_sqlite(cu), dich="sqlite")
        self.assertEqual(ctx.exception.code, "SQLITE_DICH_SCHEMA_CU")

    def test_schema_migrations_sai_shape_va_dong_trung_khong_bi_dict_che(self):
        """schema_migrations không PK với dòng version trùng (checksum đúng) → không tương thích, không đọc lịch sử qua dict."""
        hd = at.hop_dong()
        c = sqlite3.connect(ROOT_TMP / "sm-trung.sqlite", isolation_level=None)
        c.execute("CREATE TABLE schema_migrations (version INTEGER, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
        for v, h in hd["history"].items():
            c.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (v, h, "2026-01-01"))
        c.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (1, hd["history"][1], "2026-01-02"))
        c.execute(f"PRAGMA user_version={database.SCHEMA_VERSION}")
        c.execute(f"PRAGMA application_id={database.APPLICATION_ID}")
        tt = at.phan_loai_sqlite(c)
        self.assertEqual((tt["trang_thai"], "SCHEMA_MIGRATIONS_LECH" in tt["chi_tiet"]), (at.KHONG_TUONG_THICH, True))
        with self.assertRaises(DataError) as ctx:
            at.tu_choi_neu_khong_moi(tt, dich="sqlite")
        self.assertEqual(ctx.exception.code, "SQLITE_DICH_KHONG_TUONG_THICH")
        self.assertEqual(at._lich_su([(1, "a"), (1, "a")])[0], "LICH_SU_TRUNG")  # danh sách, không dict


class RowidAliasGuardTests(unittest.TestCase):
    """03/R1 — logic guard trên nguồn PG GIẢ (chỉ trả số đếm theo bảng; không phải PG thật): mọi bảng INTEGER PRIMARY KEY của hợp
    đồng đều được hỏi; một bảng lệch → ``PG_ROWID_ALIAS_LECH``; không lệch → qua."""

    class _Raw:
        def __init__(self, lech):
            self.lech, self.hoi = lech, []

        def execute(self, sql, params=None):
            t = sql.split('"."')[1].split('"')[0]
            self.hoi.append(t)
            n = 2 if t in self.lech else 0

            class _C:
                def fetchone(self_inner):
                    return (n,)
            return _C()

    def test_moi_bang_alias_duoc_kiem_va_lech_bi_tu_choi(self):
        from kho_tri_thuc.ha_tang.sao_chep_bang import kiem_rowid_alias_pg
        alias = sorted(at.hop_dong()["alias"])
        self.assertTrue({"issues", "audit_events", "evidence"} <= set(alias))
        ok = self._Raw(set())
        kiem_rowid_alias_pg(ok, "v12_demo_gia")
        self.assertEqual(ok.hoi, alias)  # toàn nhóm alias thực, không chọn mẫu
        with self.assertRaises(DataError) as ctx:
            kiem_rowid_alias_pg(self._Raw({"audit_events"}), "v12_demo_gia")
        self.assertEqual(ctx.exception.code, "PG_ROWID_ALIAS_LECH")


class BienNhanCliTests(unittest.TestCase):
    """03/R2 — biên nhận lỗi CLI trên thư mục tạm DEMO (không PG): sở hữu theo trạng thái của chính lần chạy; UNKNOWN khi không đọc
    được metadata; lỗi kiểm kê không thay lỗi gốc."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("sao_luu_pg_v13_unit", Path(__file__).resolve().parents[1] / "tools" / "sao_luu_pg.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def _thu_muc(self, ten):
        d = ROOT_TMP / ten
        st, fi = d / "ban.partial-abc", d / "ban"
        _tao_doc_quyen(st / "ban.sqlite", b"DEMO")
        return st, fi

    def test_final_ben_khac_khong_nhan_so_huu(self):
        st, fi = self._thu_muc("bn-ben-khac")
        _tao_doc_quyen(fi / "cua-ben-khac.txt", b"X")
        trang = {"da_cong_bo": False, "final_ben_khac": False}
        with self.assertRaises(DataError) as ctx:
            self.mod._cong_bo(st, fi, trang)
        self.assertEqual(ctx.exception.code, "DESTINATION_EXISTS")
        bn = self.mod._bien_nhan(st, fi, trang)
        self.assertEqual((bn["da_cong_bo"], bn["final_ben_khac"], bn["con_lai"], bn["kiem_ke"]),
                         (False, True, ["ban.partial-abc/", "ban.partial-abc/ban.sqlite"], "DAY_DU"))
        self.assertEqual((st.is_dir(), (fi / "cua-ben-khac.txt").read_bytes()), (True, b"X"))

    def test_cong_bo_cua_minh_moi_bao_da_cong_bo(self):
        st, fi = self._thu_muc("bn-cong-bo")
        trang = {"da_cong_bo": False, "final_ben_khac": False}
        self.mod._cong_bo(st, fi, trang)
        bn = self.mod._bien_nhan(st, fi, trang)
        self.assertEqual((bn["da_cong_bo"], bn["partial_giu_lai"], bn["con_lai"]), (True, None, ["ban/", "ban/ban.sqlite"]))

    # ---- 04: va chạm muộn tại CHÍNH os.rename thật (bên khác tạo final SAU precheck của _cong_bo, ngay trước rename)
    DB_BYTES, SHA_BYTES, BEN_KHAC = b"DEMO-DB-04-KHONG-RONG", b"abc123  ban.sqlite\n", b"BEN-KHAC-04-BYTES"

    def _staging_db_sha(self, ten):
        d = ROOT_TMP / ten
        st, fi = d / "ban.partial-04", d / "ban"
        _tao_doc_quyen(st / "ban.sqlite", self.DB_BYTES)
        _tao_doc_quyen(st / "ban.sqlite.sha256", self.SHA_BYTES)
        return st, fi

    @staticmethod
    def _h(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def test_va_cham_muon_tai_rename_that(self):
        import os as _os
        from unittest.mock import patch
        st, fi = self._staging_db_sha("bn04-va-cham-muon")
        h_db, h_sha = self._h(st / "ban.sqlite"), self._h(st / "ban.sqlite.sha256")
        rename_that, goi = _os.rename, []

        def rename_boc(src, dst):  # phối hợp fixture: bên khác xuất hiện SAU precheck, rồi gọi rename THẬT của Windows
            self.assertFalse(Path(dst).exists())  # precheck của _cong_bo đã thấy đích vắng
            _tao_doc_quyen(Path(dst) / "cua-ben-khac.bin", self.BEN_KHAC)
            try:
                return rename_that(src, dst)
            except BaseException as e:
                goi.append(type(e).__name__)
                raise
        trang = {"da_cong_bo": False, "final_ben_khac": False}
        with patch.object(self.mod.os, "rename", rename_boc):
            with self.assertRaises(DataError) as ctx:
                self.mod._cong_bo(st, fi, trang)
        self.assertEqual(goi, ["FileExistsError"])  # rename thật đã được gọi và chính nó từ chối đích tồn tại
        self.assertEqual((ctx.exception.code, trang["da_cong_bo"], trang["final_ben_khac"], trang["trang_thai_cong_bo"]),
                         ("DESTINATION_EXISTS", False, True, "VA_CHAM_BEN_KHAC"))
        bn = self.mod._bien_nhan(st, fi, trang)
        self.assertEqual((bn["da_cong_bo"], bn["final_ben_khac"], bn["partial_giu_lai"], bn["kiem_ke"], bn["khong_xac_dinh"]),
                         (False, True, "ban.partial-04", "DAY_DU", []))
        self.assertEqual(bn["con_lai"], ["ban.partial-04/", "ban.partial-04/ban.sqlite", "ban.partial-04/ban.sqlite.sha256"])  # đúng, đủ, không có tài sản bên khác
        self.assertEqual((self._h(st / "ban.sqlite"), self._h(st / "ban.sqlite.sha256")), (h_db, h_sha))  # staging DB+SHA nguyên
        self.assertEqual(([p.name for p in fi.iterdir()], (fi / "cua-ben-khac.bin").read_bytes()), (["cua-ben-khac.bin"], self.BEN_KHAC))
        # mã nghiệp vụ qua lớp làm sạch của CLI
        self.assertEqual(self.mod.loi_sach(ctx.exception).get("ma"), "DESTINATION_EXISTS")

    def test_loi_rename_khong_phai_va_cham_giu_loi_goc_unknown(self):
        from unittest.mock import patch
        st, fi = self._staging_db_sha("bn04-loi-quyen")
        h_db = self._h(st / "ban.sqlite")

        def rename_loi(src, dst):  # tiêm PermissionError tại rename (không phải đích tồn tại)
            raise PermissionError(13, "DEMO")
        trang = {"da_cong_bo": False, "final_ben_khac": False}
        with patch.object(self.mod.os, "rename", rename_loi):
            with self.assertRaises(PermissionError) as ctx:  # lỗi gốc giữ nguyên loại, KHÔNG thành DESTINATION_EXISTS
                self.mod._cong_bo(st, fi, trang)
        self.assertEqual((trang["da_cong_bo"], trang["final_ben_khac"], trang["trang_thai_cong_bo"]), (False, False, "UNKNOWN"))
        bn = self.mod._bien_nhan(st, fi, trang)
        self.assertEqual((bn["kiem_ke"], bn["khong_xac_dinh"], bn["trang_thai_cong_bo"], bn["da_cong_bo"], bn["final_ben_khac"]),
                         ("UNKNOWN", ["ban/"], "UNKNOWN", False, False))
        self.assertEqual(bn["con_lai"], ["ban.partial-04/", "ban.partial-04/ban.sqlite", "ban.partial-04/ban.sqlite.sha256"])
        ls = self.mod.loi_sach(ctx.exception)
        self.assertEqual((ls.get("kieu"), "ma" in ls, "DEMO" in json.dumps(ls)), ("PermissionError", False, False))  # đã làm sạch
        self.assertEqual((self._h(st / "ban.sqlite"), fi.exists()), (h_db, False))

    def test_cong_bo_that_khong_va_cham_db_sha(self):
        st, fi = self._staging_db_sha("bn04-duong")
        trang = {"da_cong_bo": False, "final_ben_khac": False}
        self.mod._cong_bo(st, fi, trang)  # rename thật, không va chạm
        self.assertEqual((trang["da_cong_bo"], trang["final_ben_khac"], trang["trang_thai_cong_bo"], st.exists()), (True, False, "DA_CONG_BO", False))
        self.assertEqual(((fi / "ban.sqlite").read_bytes(), (fi / "ban.sqlite.sha256").read_bytes()), (self.DB_BYTES, self.SHA_BYTES))

    def test_loi_metadata_unknown_va_giu_loi_goc(self):
        from unittest.mock import patch
        st, fi = self._thu_muc("bn-unknown")
        with patch.object(self.mod, "_liet_ke", side_effect=OSError("DEMO")):
            bn = self.mod._bien_nhan(st, fi, {})
        self.assertEqual((bn["kiem_ke"], bn["partial_giu_lai"], bn["con_lai"], bn["khong_xac_dinh"], bn["kiem_ke_loi"]),
                         ("UNKNOWN", "ban.partial-abc", ["ban.partial-abc/"], ["ban.partial-abc/*"], ["OSError"]))
        # lỗi trong chính hàm kiểm kê: sao_luu giữ lỗi gốc (mã DataError của bước chép), biên nhận UNKNOWN
        d = ROOT_TMP / "bn-goc"
        d.mkdir()
        with patch.object(self.mod, "_chep_kiem_cong_bo", side_effect=DataError("DEMO_LOI_GOC", "x")), \
                patch.object(self.mod, "_bien_nhan", side_effect=RuntimeError("DEMO_KIEM_KE")):
            with self.assertRaises(DataError) as ctx:
                self.mod.sao_luu("khong-dung", "v12_demo", d)
        self.assertEqual((ctx.exception.code, ctx.exception.bien_nhan["kiem_ke"], ctx.exception.bien_nhan["partial_giu_lai"]),
                         ("DEMO_LOI_GOC", "UNKNOWN", "UNKNOWN"))
        self.assertEqual(len([p for p in d.iterdir() if ".partial-" in p.name]), 1)  # staging thực vẫn còn


class ChepPgSangSqliteGuardTests(unittest.TestCase):
    def test_dich_co_du_lieu_tu_choi_truoc_doc_pg_va_giu_nguyen(self):
        for ten, sql in (("cash", "INSERT INTO cash_account_mappings VALUES ('00009001','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')"),
                         ("knowledge", "INSERT INTO knowledge_versions (id,category,logical_key,revision,payload_json,content_hash,valid_from,known_at,evidence_json,created_at,actor) "
                                       "VALUES ('k-demo','KEYWORD','DEMO',1,'{}','h','2026-01-01','2026-01-01T00:00:00Z','{}','2026-01-01T00:00:00Z','MO_PHONG')")):
            with self.subTest(ten):
                dst = _kho_moi("pg-sqlite-" + ten)
                dst.execute(sql)
                truoc = _anh(dst)
                nguon = _NguonGia()
                with self.assertRaises(DataError) as ctx:
                    chep_pg_sang_sqlite(nguon, dst)
                self.assertEqual(ctx.exception.code, "PG_NAP_DO")
                self.assertEqual(nguon.lenh, [])  # từ chối trước mọi lệnh tới PostgreSQL
                self.assertFalse(dst.in_transaction)
                self.assertEqual(_anh(dst), truoc)  # dữ liệu, lịch sử, PRAGMA foreign_keys/user_version/application_id giữ nguyên

    def test_control_duong_dich_moi_qua_guard(self):
        dst = _kho_moi("pg-sqlite-moi")
        truoc = _anh(dst)
        nguon = _NguonGia()
        with self.assertRaises(RuntimeError):
            chep_pg_sang_sqlite(nguon, dst)
        self.assertEqual(nguon.lenh, ["BEGIN"])  # đã qua guard, tới bước mở ảnh chụp đọc PostgreSQL
        self.assertEqual(_anh(dst), truoc)  # lỗi giữa chừng: hoàn tác trong giao dịch, seed giữ nguyên
        self.assertFalse(dst.in_transaction)

    def test_dich_dang_trong_giao_dich_cua_nguoi_goi(self):
        dst = _kho_moi("pg-sqlite-giao-dich")
        dst.execute("BEGIN")
        with self.assertRaises(DataError) as ctx:
            chep_pg_sang_sqlite(_NguonGia(), dst)
        self.assertEqual(ctx.exception.code, "ACTIVE_TRANSACTION")
        self.assertTrue(dst.in_transaction)  # không tự commit/rollback giao dịch của người gọi
        dst.execute("ROLLBACK")


if __name__ == "__main__":
    unittest.main()
