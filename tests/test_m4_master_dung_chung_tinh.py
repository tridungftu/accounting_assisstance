"""M4 MASTER-REUSE-02 — kiểm TĨNH/thuần (không CSDL, không driver, không mạng). CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Nhãn từng lớp:
  [STATIC_SQL]  hằng `M4_MASTER_DUNG_CHUNG_SQL` (m4/sql_master_dung_chung.py) chỉ THÊM đối tượng mới, không import/đăng ký, không sửa/drop trigger/policy
                hiện hữu, không GUC/SET ROLE, ACL đúng danh sách; mọi mã lỗi của lệnh mới có trạng thái HTTP định sẵn.
  [DOMAIN_MOCK] XayDungK2.master_* / nhan_master_hop_dong / gan_doi_tac_hop_dong kiểm hình dạng DTO TRƯỚC CSDL (kết nối giả ghi lại SQL).
  [DISPATCH_MOCK] giao_dien/m4.dieu_huong với app/service giả: allowlist body/query, trường authority → 403, mã → HTTP, Cache-Control no-store.
Không lớp nào ở đây là bằng chứng PG/HTTP thật/GUI — xem tests/test_m4_master_dung_chung_pg.py, _http.py, m4_master_dung_chung_async.cjs.
Đăng ký (M4-4/7): hằng này là M0028 trong ha_tang/pg_migrations.py — kiểm ordinal/byte ở tests/test_m4_master_m28_integration.py; module hằng vẫn không import/đăng ký.
"""

from __future__ import annotations

import ast
import re
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path

from kho_tri_thuc.giao_dien import m4 as GM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4 import sql_master_dung_chung as MC

GOC = Path(__file__).resolve().parents[1]
SQL_PY = GOC / "src" / "kho_tri_thuc" / "m4" / "sql_master_dung_chung.py"
JS = GOC / "src" / "kho_tri_thuc" / "m4" / "giao_dien" / "m4.js"
SQL = MC.M4_MASTER_DUNG_CHUNG_SQL
TOAN = "\n".join(SQL)
HD, DA, DT, MP = ("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333",
                  "44444444-4444-4444-8444-444444444444")
SHA = "a" * 64
TRIGGER_MOI = {"master_can_cu_chi_ghi_them", "master_can_cu_phien_ban_chi_ghi_them", "ho_so_hop_dong_master_can_cu", "hop_dong_m4_master_can_cu",
               "doi_tac_ma_junsky_m4_can_cu", "duyet_phien_ban_master_can_cu_chen", "duyet_phien_ban_master_can_cu_nop"}
POLICY_MOI = {"master_can_cu_web", "master_can_cu_phien_ban_web", "hop_dong_m4_ho_so"}


def _ham(ten: str) -> str:
    """Thân câu CREATE FUNCTION của đúng một hàm (tên đầy đủ schema.ten)."""
    ds = [s for s in SQL if re.search(r"CREATE OR REPLACE FUNCTION " + re.escape(ten) + r"\(", s)]
    if len(ds) != 1:
        raise AssertionError(f"{ten}: {len(ds)} định nghĩa")
    return ds[0]


def _ten(sig: str) -> str:
    return sig.split("(", 1)[0]


# ================================================================================================== [STATIC_SQL]
class TinhSql(unittest.TestCase):
    def test_module_chi_hang_khong_import_khong_dang_ky(self):
        cay = ast.parse(SQL_PY.read_text(encoding="utf-8"))
        self.assertFalse([n for n in ast.walk(cay) if isinstance(n, (ast.Import, ast.ImportFrom))], "module hằng SQL không được import")
        src = SQL_PY.read_text(encoding="utf-8")
        self.assertNotIn("PG_MIGRATIONS", src)
        self.assertIsNone(re.search(r"M00(2[89]|[3-9][0-9])", src), "không tự author ordinal 28/29")
        self.assertIsInstance(SQL, tuple)
        self.assertTrue(SQL and all(isinstance(s, str) and s.strip() for s in SQL))
        self.assertEqual(SQL[0], "SET LOCAL check_function_bodies = off")
        self.assertIn("M4_CHI_CHU", SQL[1])  # cổng chủ bảng trước mọi DDL

    def test_khong_sua_doi_tuong_hien_huu(self):
        self.assertIsNone(re.search(r"(?i)\bDROP\s", TOAN))
        self.assertIsNone(re.search(r"(?i)\b(ALTER\s+POLICY|ALTER\s+TRIGGER|DISABLE\s+TRIGGER|NO\s+FORCE|ALTER\s+FUNCTION|CREATE\s+OR\s+REPLACE\s+TRIGGER)", TOAN))
        self.assertIsNone(re.search(r"(?i)\b(SET\s+ROLE|SET\s+SESSION|set_config|RESET\s+ROLE|BYPASSRLS|session_replication_role)", TOAN))
        self.assertIsNone(re.search(r"(?i)\b(TRUNCATE|DELETE\s+FROM)\b", TOAN))
        for m in re.finditer(r"ALTER TABLE ([a-z0-9_.]+)", TOAN):
            self.assertIn(m.group(1), {"m4.master_can_cu", "m4.master_can_cu_phien_ban"}, "chỉ ALTER bảng mới của gói")
        self.assertEqual(set(re.findall(r"CREATE TRIGGER ([a-z0-9_]+)", TOAN)), TRIGGER_MOI)
        self.assertEqual(set(re.findall(r"CREATE POLICY ([a-z0-9_]+)", TOAN)), POLICY_MOI)
        self.assertEqual(set(re.findall(r"CREATE TABLE ([a-z0-9_.]+)", TOAN)), {"m4.master_can_cu", "m4.master_can_cu_phien_ban"})
        # observer trên bảng nguồn hiện hữu chỉ AFTER ROW (không BEFORE — không chặn/sửa đường ghi nguồn)
        for ten in ("ho_so_hop_dong_master_can_cu", "hop_dong_m4_master_can_cu", "doi_tac_ma_junsky_m4_can_cu", "duyet_phien_ban_master_can_cu_chen",
                    "duyet_phien_ban_master_can_cu_nop"):
            cau = next(s for s in SQL if f"CREATE TRIGGER {ten} " in s)
            self.assertRegex(cau, r"\bAFTER\b")
            self.assertRegex(cau, r"FOR EACH ROW")
        # policy master.hop_dong mới: permissive SELECT TO app_web hẹp (không AS RESTRICTIVE, không FOR ALL/UPDATE)
        p = re.search(r"CREATE POLICY hop_dong_m4_ho_so ON master\.hop_dong ([^;]+)", TOAN).group(1)
        self.assertIn("FOR SELECT TO app_web", p)
        self.assertIn("m4.mc_co_ho_so(id, du_an_id)", p)
        self.assertNotIn("RESTRICTIVE", p)

    def test_moi_ham_co_search_path_co_dinh_va_definer_dung_cho(self):
        for sig in MC.HAM_LENH + MC.HAM_DOC + MC.HAM_NOI_BO + MC.HAM_TRIGGER:
            than = _ham(_ten(sig))
            self.assertRegex(than, r"SET search_path = [a-z0-9_, ]*pg_temp", sig)
        for sig in MC.HAM_LENH + MC.HAM_DOC + MC.HAM_TRIGGER:
            self.assertIn("SECURITY DEFINER", _ham(_ten(sig)).split("AS $$", 1)[0], sig)
        for sig in ("m4._mc_sha(jsonb)", "m4._mc_meta(uuid, uuid, boolean)", "m4._mc_mapping_sha(uuid)"):
            self.assertNotIn("SECURITY DEFINER", _ham(_ten(sig)).split("AS $$", 1)[0], sig)
        # observer chỉ chạy từ đúng trigger nguồn đã khai báo (TG_RELID/TG_OP/AFTER/ROW)
        for sig in MC.HAM_TRIGGER:
            self.assertIn("TG_RELID <>", _ham(_ten(sig)), sig)
        # meta không phụ thuộc now() (hash chỉ đổi khi nguồn thật đổi)
        self.assertNotIn("now()", _ham("m4._mc_meta"))
        self.assertIn("VOLATILE", _ham("m4._mc_meta").split("AS $$", 1)[0])

    def test_acl_dung_danh_sach(self):
        rv = next(s for s in SQL if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        for sig in MC.HAM_LENH + MC.HAM_DOC + MC.HAM_NOI_BO + MC.HAM_TRIGGER:
            self.assertIn(sig, rv)
        self.assertTrue(rv.endswith("FROM PUBLIC"))
        do = SQL[-1]
        self.assertIn("rolname = 'app_web'", do)
        grant = re.search(r"GRANT EXECUTE ON FUNCTION ([^;]+) TO app_web", do).group(1)
        self.assertEqual({x.strip() for x in re.split(r",\s*(?=m4\.)", grant)}, set(MC.HAM_LENH + MC.HAM_DOC))
        rv_web = re.search(r"REVOKE EXECUTE ON FUNCTION ([^;]+) FROM app_web", do).group(1)
        self.assertEqual({x.strip() for x in re.split(r",\s*(?=m4\.)", rv_web)}, set(MC.HAM_NOI_BO + MC.HAM_TRIGGER))
        self.assertIn("GRANT SELECT ON m4.master_can_cu, m4.master_can_cu_phien_ban TO app_web", do)
        self.assertIsNone(re.search(r"(?i)GRANT\s+(INSERT|UPDATE|DELETE|ALL)", TOAN), "không cấp DML trực tiếp")
        for t in MC.BANG:
            self.assertIn(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY", SQL)

    def test_lenh_kiem_soan_truoc_replay_va_khoa_master_truoc_ho_so(self):
        for ten, hd in (("m4.nhan_master_hop_dong", "NHAN_MASTER_HOP_DONG"), ("m4.gan_doi_tac_hop_dong", "GAN_DOI_TAC_HOP_DONG")):
            t = _ham(ten)
            i_soan, i_replay = t.index("master.m4_duoc("), t.index(f"'{hd}'")
            self.assertLess(i_soan, i_replay, ten)
            i_master = re.search(r"FROM master\.hop_dong x\s+WHERE x\.id = p_hd[^;]*FOR UPDATE", t).start()
            i_ho_so = t.index("FROM m4.ho_so_hop_dong WHERE hop_dong_id = p_hd FOR UPDATE")
            self.assertLess(i_replay, i_master, ten)
            self.assertLess(i_master, i_ho_so, ten)
            self.assertNotIn("doi_tac_ma_junsky WHERE id = p_mapping FOR", t, "lệnh M4 không khóa hàng mapping")
        g = _ham("m4.gan_doi_tac_hop_dong")
        self.assertLess(g.index("m4._mc_ghi(p_hd, g, 'GAN_DOI_TAC'"), g.index("UPDATE master.hop_dong SET doi_tac_id"),
                        "căn cứ ghi TRƯỚC UPDATE master để observer thấy cùng hash (không bump hai lần)")
        self.assertNotRegex(g, r"UPDATE master\.hop_dong SET [^;]*(module_chu|trang_thai|crm_giao_ket|phien_ban_hien_hanh)")
        self.assertNotRegex(_ham("m4.nhan_master_hop_dong"), r"(?i)(INSERT INTO|UPDATE) master\.")
        # observer mapping: khóa master FOR SHARE theo id tăng dần rồi hồ sơ FOR UPDATE; không khóa mapping, không UPDATE mapping
        o = _ham("m4._mc_quan_sat_mapping")
        self.assertRegex(o, r"ORDER BY [a-z.]*id\s+FOR SHARE")
        self.assertNotRegex(o, r"(?i)UPDATE master\.doi_tac_ma_junsky")

    def test_ma_loi_lenh_deu_co_trang_thai_http(self):
        ma = set()
        for sig in MC.HAM_LENH + MC.HAM_DOC + ("m4._mc_chup_phien_ban()",):
            ma |= set(re.findall(r"RAISE EXCEPTION '([A-Z0-9_]+):", _ham(_ten(sig))))
        self.assertTrue(ma)
        for code in ma:
            co = (code in GM.MA_403 or code in GM.MA_404 or code in GM.MA_409 or code in GM.MA_422_MASTER or code == "M4_THAM_SO_SAI")
            self.assertTrue(co, f"{code} chưa có trạng thái HTTP định sẵn")
        self.assertIn("M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH", GM.MA_409)
        self.assertIn("M4_MASTER_CAN_SUA_TAI_NGUON", GM.MA_409)
        self.assertIn("M4_MAPPING_MO_HO", GM.MA_422_MASTER)

    def test_trang_thai_nhan_va_nguon_dong(self):
        self.assertEqual(MC.TRANG_THAI_NHAN, ("SOAN_THAO", "CHO_KY", "DA_KY", "HIEU_LUC"))
        self.assertNotIn("HUY", MC.TRANG_THAI_NHAN)
        for n in MC.NGUON:
            self.assertIn(f"'{n}'", TOAN)
        # baseline di trú: chỉ 'biết tại thời điểm nhận', không bump, không ghi liên kết phiên bản lịch sử
        base = next(s for s in SQL if "FOR r IN SELECT s.hop_dong_id FROM m4.ho_so_hop_dong" in s)
        self.assertIn("'BASELINE_BIET_TAI_NHAN'", base)
        self.assertIn("false)", base)
        self.assertNotIn("master_can_cu_phien_ban", base)


# ================================================================================================== [DOMAIN_MOCK]
class _Conn:
    """Kết nối giả: ghi lại câu lệnh; trả hàng cấu hình sẵn."""

    def __init__(self, tra=None):
        self.cau, self.tra = [], tra or {}

    def execute(self, sql, params=None):
        self.cau.append((sql, params))
        conn = self

        class _R:
            def fetchone(self_):
                for k, v in conn.tra.items():
                    if k in sql:
                        return v
                return {"r": {"items": []}}
        return _R()

    @contextmanager
    def transaction(self):
        yield


def _svc(tra=None):
    from kho_tri_thuc.k2.xay_dung import XayDungK2
    s = XayDungK2.__new__(XayDungK2)
    s.conn = _Conn(tra)
    s.danh_tinh = lambda dn: {"id": "00000000-0000-4000-8000-000000000001", "dang_nhap": dn}
    s.hom_nay = lambda: __import__("datetime").date(2026, 10, 23)
    return s


class DomainMock(unittest.TestCase):
    def ma(self, fn, **kw):
        with self.assertRaises(DataError) as cm:
            fn(**kw)
        return cm.exception.code

    def test_tim_gioi_han_q_limit(self):
        s = _svc()
        for q, lim in (("x" * 101, 25), ("a\x01", 25), ("", "0"), ("", "51"), ("", "100"), ("", "abc"), ("", 0), ("", True), (5, 25)):
            self.assertEqual(self.ma(lambda **k: s.master_hop_dong("A", **k), du_an_id=DA, q=q, limit=lim), "M4_THAM_SO_SAI", (q, lim))
        self.assertEqual(s.conn.cau, [], "sai hình dạng → không chạm CSDL")
        s.master_hop_dong("A", du_an_id=DA, q="HĐ 12", limit="7")
        sql, p = s.conn.cau[-1]
        self.assertIn("m4.master_hop_dong_ds(%s::uuid, %s, %s)", sql)
        self.assertEqual(p, (DA, "HĐ 12", 7))
        s.master_doi_tac("A", du_an_id=DA, q=None, limit=None)
        self.assertEqual(s.conn.cau[-1][1], (DA, "", 25))
        self.assertEqual(self.ma(lambda **k: s.master_doi_tac("A", **k), du_an_id="khong-uuid"), "M4_THAM_SO_SAI")

    def test_nhan_master_dto_truoc_csdl(self):
        s = _svc()
        goc = dict(du_an_id=DA, hop_dong_id=HD, ten="Gói A", expected_master=SHA, khoa="k-1")
        for sua in ({"expected_master": "A" * 64}, {"expected_master": "a" * 63}, {"hop_dong_id": "x"}, {"ten": "x" * 301}, {"khoa": "có dấu"}):
            self.assertIn(self.ma(lambda **k: s.nhan_master_hop_dong("A", **k), **{**goc, **sua}), ("M4_THAM_SO_SAI", "M4_KHOA_THAO_TAC"), sua)
        self.assertFalse([c for c in s.conn.cau if "nhan_master_hop_dong" in c[0]])

    def test_gan_doi_tac_dto_truoc_csdl(self):
        s = _svc()
        goc = dict(hop_dong_id=HD, doi_tac_id=DT, mapping_id=MP, revision=3, expected_master=SHA, expected_mapping="b" * 64, ly_do="Đổi NCC", khoa="k-2")
        self.assertEqual(self.ma(lambda **k: s.gan_doi_tac_hop_dong("A", **k), **{**goc, "ly_do": "   "}), "M4_LY_DO_BAT_BUOC")
        self.assertEqual(self.ma(lambda **k: s.gan_doi_tac_hop_dong("A", **k), **{**goc, "ly_do": None}), "M4_THIEU_THONG_TIN")
        for sua in ({"revision": 0}, {"revision": "3"}, {"revision": True}, {"mapping_id": None}, {"expected_mapping": "z" * 64}, {"ly_do": "x" * 1001}):
            self.assertEqual(self.ma(lambda **k: s.gan_doi_tac_hop_dong("A", **k), **{**goc, **sua}), "M4_THAM_SO_SAI", sua)
        self.assertEqual(s.conn.cau, [])


# ================================================================================================== [DISPATCH_MOCK]
class _H:
    def __init__(self, body=None):
        self.body_, self.headers, self.st, self.data, self.hd = body, {}, None, None, None

    def json_body(self):
        return self.body_

    def crm_sid(self):
        return "sid"

    def send_content(self, status, data, mime=None, headers=None):
        self.st, self.data, self.hd = status, data, headers


class _Svc:
    def __init__(self, loi=None):
        self.goi, self.loi = [], loi

    def _ghi(self, ten, a, kw):
        self.goi.append((ten, a, kw))
        if self.loi:
            raise self.loi
        return {"ten": ten}

    def master_hop_dong(self, *a, **kw):
        return self._ghi("master_hop_dong", a, kw)

    def master_doi_tac(self, *a, **kw):
        return self._ghi("master_doi_tac", a, kw)

    def nhan_master_hop_dong(self, *a, **kw):
        return self._ghi("nhan_master_hop_dong", a, kw)

    def gan_doi_tac_hop_dong(self, *a, **kw):
        return self._ghi("gan_doi_tac_hop_dong", a, kw)


class _App:
    def __init__(self, svc, me="MO_PHONG_DU_AN_A1"):
        self.mutation_lock, self.me = threading.Lock(), me
        self.__dict__["_m4"] = svc

    def crm_phien(self, sid, *, tao=False):
        return sid, self.me, False

    @staticmethod
    def _crm_db(fn, *a):
        return fn(*a)


class DispatchMock(unittest.TestCase):
    def chay(self, post, path, body=None, query=None, svc=None):
        svc = _Svc() if svc is None else svc
        h = _H(body)
        GM.dieu_huong(h, _App(svc), post, path, query or {})
        return h, svc

    def test_get_master_dung_tham_so_va_no_store(self):
        for path, ten in (("/api/m4/master-hop-dong", "master_hop_dong"), ("/api/m4/master-doi-tac", "master_doi_tac")):
            h, svc = self.chay(False, path, query={"du_an_id": [DA], "q": ["12"], "limit": ["5"]})
            self.assertEqual(h.st, 200)
            self.assertEqual(h.hd, {"Cache-Control": "no-store"})
            self.assertEqual(svc.goi, [(ten, ("MO_PHONG_DU_AN_A1",), {"du_an_id": DA, "q": "12", "limit": "5"})])
            h, svc = self.chay(False, path, query={"du_an_id": [DA]})
            self.assertEqual(svc.goi[0][2], {"du_an_id": DA, "q": "", "limit": None})
            for q in ({"du_an_id": [DA], "actor": ["x"]}, {"du_an_id": [DA, DA]}, {"du_an_id": [DA], "phap_nhan_id": ["x"]}):
                h, svc = self.chay(False, path, query=q)
                self.assertEqual((h.st, h.data["error"]), (400, "M4_YEU_CAU_SAI"), q)
                self.assertEqual(svc.goi, [])

    def test_post_allowlist_va_truong_authority(self):
        nhan = {"du_an_id": DA, "hop_dong_id": HD, "ten": "Gói", "expected_master": SHA, "khoa": "k"}
        gan = {"hop_dong_id": HD, "doi_tac_id": DT, "mapping_id": MP, "revision": 2, "expected_master": SHA, "expected_mapping": SHA, "ly_do": "x", "khoa": "k"}
        for path, body, ten in (("/api/m4/hop-dong/nhan-master", nhan, "nhan_master_hop_dong"), ("/api/m4/hop-dong/gan-doi-tac", gan, "gan_doi_tac_hop_dong")):
            h, svc = self.chay(True, path, body)
            self.assertEqual(h.st, 200)
            self.assertEqual(svc.goi[0][0], ten)
            self.assertEqual(svc.goi[0][2], {k: v for k, v in body.items()})
            for k in ("actor", "phap_nhan_id", "trang_thai"):
                h, svc = self.chay(True, path, {**body, k: "x"})
                self.assertEqual((h.st, h.data["error"]), (403, "M4_CLIENT_AUTHORITY"), (path, k))
                self.assertEqual(svc.goi, [])
            for k in ("module_chu", "doi_tac_ten", "mapping_trang_thai"):
                h, svc = self.chay(True, path, {**body, k: "x"})
                self.assertEqual((h.st, h.data["error"]), (400, "M4_YEU_CAU_SAI"), (path, k))
                self.assertEqual(svc.goi, [])

    def test_ma_loi_sang_http(self):
        bang = {"M4_KHONG_CO_QUYEN_DU_AN": 403, "M4_MASTER_KHONG_THAY": 404, "M4_MAPPING_KHONG_THAY": 404, "M4_KHONG_THAY_HOP_DONG": 404,
                "M4_MASTER_DA_DOI": 409, "M4_MAPPING_DA_DOI": 409, "M4_REVISION_CU": 409, "M4_IDEMPOTENCY_KHAC": 409, "M4_KHONG_DOI": 409,
                "M4_MASTER_CAN_SUA_TAI_NGUON": 409, "M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH": 409, "M4_MASTER_CAN_CU_DOI": 409,
                "M4_MAPPING_KHONG_HIEN_HANH": 422, "M4_MAPPING_MO_HO": 422, "M4_MASTER_TRANG_THAI_KHONG_NHAN": 422, "M4_DOI_TAC_KHONG_HOP_LE": 422,
                "M4_LY_DO_BAT_BUOC": 422, "M4_THAM_SO_SAI": 400}
        body = {"hop_dong_id": HD, "doi_tac_id": DT, "mapping_id": MP, "revision": 2, "expected_master": SHA, "expected_mapping": SHA, "ly_do": "x",
                "khoa": "k"}
        for code, st in bang.items():
            h, _ = self.chay(True, "/api/m4/hop-dong/gan-doi-tac", body, svc=_Svc(DataError(code, "CSDL từ chối thao tác (" + code + ")")))
            self.assertEqual((h.st, h.data["error"]), (st, code), code)
            self.assertNotIn("SELECT", h.data["message"])

    def test_js_chi_textcontent_khong_localstorage(self):
        js = JS.read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("localStorage", js)
        for s in ('"hop-dong/nhan-master"', '"hop-dong/gan-doi-tac"', "/api/m4/master-hop-dong?", "/api/m4/master-doi-tac?",
                  "Dùng hợp đồng đã có", "Tạo hồ sơ mới"):
            self.assertIn(s, js)


if __name__ == "__main__":
    unittest.main()
