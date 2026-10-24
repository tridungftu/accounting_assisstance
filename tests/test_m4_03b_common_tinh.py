"""M4-03B-01 — kiểm TĨNH + THUẦN identity nguồn dùng chung + đối chiếu căn cứ NT ↔ hóa đơn (không PostgreSQL, không mạng). WRITTEN_NOT_RUN.

Phân loại (nhãn trung thực):
- `SqlTinh`: chuỗi `M4_03B_COMMON_SQL` (hằng, KHÔNG đăng ký registry/ordinal): chỉ thêm đối tượng mới + nới CHECK module biên nhận chung; không chạm
  bảng tiền/de_xuat/chung_tu/lien_ket_phan_bo/AP; financial_owner IS NULL; REVOKE PUBLIC; RLS; app chỉ EXECUTE hàm đọc sớm; lệnh không SECURITY DEFINER.
- `KiemDauVao`: validator thật (allowlist, khóa thẩm quyền/khớp/tiền → DC_CLIENT_AUTHORITY, UUID chuẩn, NT không part, trùng/chồng phần, CAS).
- `MienThuan`: gương `thieu` (mã + thứ tự = kho._dc_thieu), `trang_thai` dẫn xuất CAN_KIEM_LAI.
- `DtoBien`: builder DTO thật trên khung VIẾT TAY — chỉ chứng minh serializer, KHÔNG phải bằng chứng producer/PG (đó là test_m4_03b_common_pg.py).
- `ThuTuDichVu`: `GhiNhanChungK2` với FAKE_XD/FAKE_NT có nhãn — chỉ thứ tự biên (validate trước danh tính; kiểm sớm login thường; refs/quyền
  trước ghim; ghim trước lệnh; một giao dịch chủ bảng).
- `PhamVi`: không file cũ nào bị import-sửa: module mới không gọi writer tiền/AP, không route/UI.
FIX01 (static/mock, KHÔNG phải bằng chứng native): đổi tập nguồn là revision cùng gốc (không còn từ chối khoa_goc ≠ tập), alias tập UNIQUE(PN, tap),
không UNIQUE theo nguồn đơn lẻ, namespace biên nhận theo gốc, closure union trước khóa + kiểm revision đã đọc dưới khóa, gương `hop_refs`.
FIX02 (`TenPlpgsql`, static — KHÔNG phải bằng chứng native): hồi quy 42702 AmbiguousColumn — `_REFS`/`_HIEN_HANH` alias tường minh `dc_ref(value)`;
mọi hàm/khối plpgsql của hằng common không có alias quan hệ/cột SQL hay cột bảng mới trùng tham số/biến; bộ dò tự kiểm trên mẫu lỗi đã thấy.
"""

from __future__ import annotations

import copy
import json
import re
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import ghi_nhan_chung as GN
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as SG
from kho_tri_thuc.m4 import ghi_nhan_nghiem_thu as AD

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
NOI = "\n".join(SG.M4_03B_COMMON_SQL)


def _ma(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except DataError as exc:
        return exc.code
    return None


def _ham(ten: str) -> str:
    i = NOI.index(f"CREATE OR REPLACE FUNCTION {ten}(")
    a = NOI.index("$$", i)
    return NOI[i:NOI.index("$$", a + 2)]


def _id(n: int) -> str:
    return str(uuid.UUID(int=n))


SHA = "a" * 64


def _ref(kind="NT", occ=1, ver=2, part=None):
    return {"kind": kind, "occurrence_id": _id(occ), "source_version_id": _id(ver), "part_id": None if part is None else _id(part)}


def _tp(ref, phan="TOAN_PHAN", ty=None):
    return {"nguon": ref, "phan": phan, "ty_le_khai": ty}


def _luu(**du):
    b = {"doi_chieu_id": None, "thanh_phan": [_tp(_ref()), _tp(_ref("HOA_DON", 10, 11))], "can_cu_tep": [], "expected_graph": SHA,
         "expected_revision": 0, "ly_do": "KT đối chiếu hóa đơn với nghiệm thu đợt 1", "khoa": "k-1"}
    b.update(du)
    return b


def _xn(**du):
    b = {"doi_chieu_id": _id(50), "phien_ban_id": _id(51), "expected_revision": 1, "expected_graph": SHA, "khoa": "x-1"}
    b.update(du)
    return b


# ================================================================================================== SQL tĩnh
class SqlTinh(unittest.TestCase):
    def test_mot_hang_tuple_chuoi(self):
        self.assertIsInstance(SG.M4_03B_COMMON_SQL, tuple)
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in SG.M4_03B_COMMON_SQL))
        self.assertEqual(SG.M4_03B_COMMON_SQL[0], "SET LOCAL check_function_bodies = off")

    def test_khong_dang_ky_khong_ordinal(self):
        src = (SRC / "k2" / "sql_ghi_nhan_chung.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r"^\s*(from|import)\s+.*pg_migrations", "không import registry")
        self.assertNotIn("MIGRATIONS", src)
        self.assertNotRegex(NOI, r"(?i)schema_migrations|kho_migration")

    def test_bang_moi_du_va_chi_ghi_them(self):
        for t in SG.BANG:
            self.assertIn(f"CREATE TABLE kho.{t} (", NOI)
            self.assertIn(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON kho.{t}", NOI)
            self.assertIn(f"REVOKE ALL ON kho.{t} FROM PUBLIC", NOI)
            self.assertIn(f"ALTER TABLE kho.{t} ENABLE ROW LEVEL SECURITY", NOI)

    def test_khong_cham_bang_cu_ngoai_bien_nhan(self):
        alter = re.findall(r"ALTER TABLE (\S+)", NOI)
        self.assertEqual({a for a in alter if not a.startswith("kho.mua_")}, {"kho.bien_nhan_thao_tac"})
        self.assertNotRegex(NOI, r"\bUPDATE\s+(kho|m4|master)\.|\bDELETE\s+FROM\b|\bTRUNCATE\b|\bDROP\s+(TABLE|FUNCTION|TRIGGER|INDEX)\b")
        for cam in ("kho.de_xuat", "kho.lien_ket_phan_bo", "kho.dich_phan_bo_tien", "kho.mua_nghia_vu", "INSERT INTO kho.chung_tu",
                    "m4.kt_luu", "m4.kt_xac_nhan_lenh", "INSERT INTO m4.", "INSERT INTO master."):
            self.assertNotIn(cam, NOI)

    def test_bien_nhan_giu_module_cu(self):
        self.assertIn("CHECK (module IN ('CRM','M1','M2','M5','M4'))", NOI)
        self.assertIn("LIKE '%''M5''%'", NOI)
        b = _ham("kho.bien_nhan_dc_chi_chu")
        self.assertIn("NEW.module = 'M4'", b)
        self.assertIn("master.la_chu_bang(TG_RELID::regclass)", b)

    def test_tai_chinh_chua_chung_minh(self):
        self.assertIn("financial_owner text CHECK (financial_owner IS NULL)", NOI)
        self.assertIn(f"CHECK (ghi_nhan = '{SG.GHI_NHAN_TT}')", NOI)
        self.assertNotRegex(NOI, r"_minor\s+(bigint|numeric)")
        self.assertNotIn("total_minor", NOI)
        for k in ("'claim', 0", "'proposal', 0", "'ap', 0", "'financial_owner', NULL::text"):
            self.assertIn(k, SG.GHI_NHAN_SQL)

    def test_lenh_khong_definer_co_tin_cay(self):
        for h in ("kho.dc_luu", "kho.dc_xac_nhan"):
            b = _ham(h)
            self.assertNotIn("SECURITY DEFINER", b.split("$$")[0])
            self.assertIn("m4._kt_phien_chu()", b)
            self.assertIn("master.ktt_danh_tinh()", b)
            self.assertIn("kho._dc_quyen(hop, true)", b)
            self.assertIn("kho._dc_khoa_hoa_don(hop)", b)
            self.assertIn("kho._dc_bn_tra(", b)
            self.assertIn("module := goc.module_bien_nhan", b)
        self.assertNotIn("SECURITY DEFINER", _ham("kho._dc_nt_ghi").split("$$")[0])
        self.assertNotIn("SET search_path", _ham("kho._dc_nt_ghi").split("$$")[0])

    def test_thu_tu_quyen_truoc_bien_nhan_truoc_cas(self):
        b = _ham("kho.dc_luu")
        i_c0, i_cu, i_hop = (b.index("INTO v_cuoi0"), b.index("kho._dc_nguon_cua(v_goc, v_cuoi0)"), b.index("kho._dc_hop(refs, cu_refs)"))
        i_q, i_k, i_g = b.index("kho._dc_quyen(hop, true)"), b.index("kho._dc_khoa_hoa_don(hop)"), b.index("kho._dc_do_thi(refs)")
        i_tap, i_goc = b.index("'DC_TAP|'"), b.index("x.id = v_goc AND x.phap_nhan_id = pn FOR UPDATE")
        i_cuoi, i_bn, i_cas = b.index("cuoi.id IS DISTINCT FROM v_cuoi0"), b.index("kho._dc_bn_tra("), b.index("DC_DO_THI_DOI")
        i_alias, i_khac = b.index("FROM kho.mua_doi_chieu_can_cu_tap a WHERE a.phap_nhan_id = pn AND a.tap_sha256 = kg"), b.index("DC_TAP_THUOC_GOC_KHAC")
        thu_tu = [i_c0, i_cu, i_hop, i_q, i_k, i_g, i_tap, i_goc, i_cuoi, i_bn, i_cas, i_alias, i_khac]
        self.assertEqual(thu_tu, sorted(thu_tu))
        self.assertLess(i_cuoi, b.index("kho._dc_quyen(hop, true)", i_q + 1), "quyền ghi union kiểm lại dưới khóa gốc")
        self.assertIn("DC_DA_CO_GOC", b)
        self.assertIn("DC_REVISION_CU", b)
        self.assertIn("DC_NGUON_CU", b)
        # FIX01: không còn từ chối đổi tập nguồn; không dựng gốc thay thế khi revision
        self.assertNotIn("khoa_goc_sha256 IS DISTINCT FROM kg", b)
        self.assertNotIn("DC_GOC|", b)
        self.assertEqual(b.count("INSERT INTO kho.mua_doi_chieu_can_cu ("), 1)
        self.assertLess(b.index("IF goc.id IS NULL THEN\n                IF erev <> 0"), b.index("INSERT INTO kho.mua_doi_chieu_can_cu ("))
        x = _ham("kho.dc_xac_nhan")
        thu_tu = [x.index("kho._dc_nguon_cua(goc.id, (p_yc->>'phien_ban_id')::uuid)"), x.index("kho._dc_hop(refs, kho._dc_nguon_cua(goc.id, NULL))"),
                  x.index("kho._dc_quyen(hop, true)"), x.index("kho._dc_khoa_hoa_don(hop)"), x.index("FOR UPDATE"), x.index("kho._dc_bn_tra(")]
        self.assertEqual(thu_tu, sorted(thu_tu))
        self.assertIn("n.tap_sha256", x)
        self.assertIn("DC_CHO_BO_SUNG", x)
        self.assertIn("trung_xac_nhan", x)

    def test_alias_tap_va_namespace_bien_nhan(self):
        alias = next(s for s in SG.M4_03B_COMMON_SQL if s.startswith("CREATE TABLE kho.mua_doi_chieu_can_cu_tap ("))
        self.assertIn("UNIQUE (phap_nhan_id, tap_sha256))", alias)
        self.assertEqual(alias.count("UNIQUE"), 1, "alias chỉ duy nhất theo (PN, tập) — không theo nguồn đơn lẻ")
        # nhiều-nhiều: không UNIQUE theo nguồn/occurrence đơn lẻ trong bảng đối chiếu
        j = NOI.index("CREATE TABLE kho.mua_doi_chieu_can_cu_thanh_phan (")
        tp = NOI[j:NOI.index("CREATE TABLE kho.mua_doi_chieu_can_cu_nhat_ky (")]
        self.assertEqual(re.findall(r"UNIQUE \(([^)]*)\)", tp), ["phien_ban_id, phan_id"])
        self.assertNotRegex(NOI, r"CREATE UNIQUE INDEX \S+ ON kho\.mua_doi_chieu")
        self.assertIn("module_bien_nhan text NOT NULL CHECK (module_bien_nhan IN ('M4','M2'))", NOI)
        self.assertIn("tap_sha256 text NOT NULL CHECK (tap_sha256 ~ '^[0-9a-f]{64}$')", NOI)
        bn = _ham("kho.bien_nhan_dc_chi_chu")
        self.assertIn("BIEN_NHAN_DC_MODULE", bn)
        self.assertIn("g.module_bien_nhan", bn)
        b = _ham("kho.dc_luu")
        self.assertIn("IF ma_goc IS NULL THEN\n                INSERT INTO kho.mua_doi_chieu_can_cu_tap", b)
        self.assertIn("VALUES (pn, kg, module, ai, aid)", b)
        self.assertIn("th, kg, hd, dtac", b)
        self.assertIn("txid_current()", _ham("kho._dc_tap_kiem"))
        self.assertIn("v.tap_sha256 IS DISTINCT FROM NEW.tap_sha256", _ham("kho._dc_tap_kiem"))
        pk = _ham("kho._dc_phien_ban_kiem")
        self.assertIn("NEW.tap_sha256 IS DISTINCT FROM kho._dc_khoa_goc(", pk)
        self.assertIn("n.tap_sha256", pk)
        h = _ham("kho._dc_phien_ban_hoan_tat")
        self.assertIn("a.doi_chieu_id = NEW.doi_chieu_id", h)
        self.assertIn("g.khoa_goc_sha256 = NEW.tap_sha256", h)
        self.assertIn("DC_TAP_THUOC_GOC_KHAC", h)
        xem = _ham("kho._dc_xem")
        self.assertIn("'goc_cua_tap', gt", xem)
        self.assertIn("kho._dc_doc_duoc(", xem[xem.index("INTO gt"):])
        ls = _ham("kho._dc_lich_su")
        for k in ("'bo_tap'", "'module_bien_nhan'", "'tap_sha256', v.tap_sha256"):
            self.assertIn(k, ls)
        hop = _ham("kho._dc_hop")
        self.assertIn("DISTINCT ON (w.k)", hop)
        self.assertIn("ORDER BY w.k, w.n", hop)

    def test_quyen_hoa_don_ghi_can_kt_toan_cuc(self):
        q = _ham("kho._dc_quyen")
        self.assertIn("m4.kt_kiem((e->>'occurrence_id')::uuid, 'XEM')", q)
        self.assertIn("kho._dc_m2_doc(v_pn)", q)
        self.assertIn("p_ghi AND NOT kho._dc_kt_toan_cuc(v_pn)", q)
        self.assertIn("ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO','XEM']", _ham("kho._dc_m2_doc"))
        kt = _ham("kho._dc_kt_toan_cuc")
        self.assertIn("ARRAY['KE_TOAN','KE_TOAN_TRUONG']", kt)
        self.assertNotIn("CFO", kt)
        self.assertNotIn("M2_MAP", NOI)

    def test_khong_matching_ten_ngay_tien(self):
        dt = _ham("kho._dc_do_thi")
        for cam in ("ngay_lap", "ten_ben_ban", "similarity", "levenshtein", "ILIKE", "total_minor", "net_minor"):
            self.assertNotIn(cam, dt)
        self.assertIn("kho.m2_co_so(d.id)", dt)
        self.assertIn("kho._dc_nt_hien_hanh(c.id)", dt)

    def test_guard_deferred_va_xmin(self):
        self.assertIn("DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION kho._dc_phien_ban_hoan_tat()", NOI)
        h = _ham("kho._dc_phien_ban_hoan_tat")
        self.assertIn("kho._dc_quyen(refs, true)", h)
        self.assertIn("kho._dc_do_thi(refs)", h)
        self.assertIn("kho._dc_thieu(", h)
        self.assertIn("txid_current()", _ham("kho._dc_thanh_phan_kiem"))

    def test_grant_chi_ham_doc(self):
        grants = re.findall(r"GRANT ([^;]+?) TO app_web", NOI)
        self.assertEqual(len(grants), 1)
        self.assertIn("EXECUTE ON FUNCTION kho.dc_doc_hoa_don(uuid)", grants[0])
        rv = next(s for s in SG.M4_03B_COMMON_SQL if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        for h in (*SG.HAM_LENH, *SG.HAM_NOI_BO, *SG.HAM_DOC, *SG.HAM_TRIGGER):
            self.assertIn(h, rv)

    def test_moi_ham_tao_deu_revoke(self):
        tao = set(re.findall(r"CREATE OR REPLACE FUNCTION (kho\.[a-z_0-9]+)\(", NOI))
        khai = {h.split("(")[0] for h in (*SG.HAM_LENH, *SG.HAM_NOI_BO, *SG.HAM_DOC, *SG.HAM_TRIGGER)}
        self.assertEqual(tao, khai)

    def test_ma_thieu_sql_bang_python(self):
        t = _ham("kho._dc_thieu")
        self.assertEqual(set(re.findall(r"array_append\(x, '([A-Z_0-9]+)'\)", t)), set(SG.THIEU))
        self.assertEqual(list(SG.THIEU), sorted(SG.THIEU))


# ================================================================================================== FIX02: tên PL/pgSQL ↔ SQL
# PL/pgSQL (variable_conflict mặc định = error) báo 42702 khi một tên trong statement nhúng vừa là biến/tham số vừa là alias quan hệ/cột SQL.
# Bộ dò tĩnh: với mỗi hàm/khối plpgsql, tập (tham số + biến DECLARE) phải rời tập (alias quan hệ + alias cột + cột bảng mới được FROM/JOIN).
_SRF = ("jsonb_array_elements", "jsonb_array_elements_text", "_kt_tep_can_cu", "unnest")
_ID = r"[a-z_][a-z_0-9]*"
_TU_KHOA = frozenset(("as", "on", "where", "join", "left", "cross", "lateral", "order", "limit", "for", "loop", "then", "and", "or", "is", "in",
                      "into", "from", "group", "union", "all", "select", "using", "returning", "values", "not", "case", "when", "else", "end",
                      "desc", "asc", "collate", "filter", "nulls", "exists"))


def _bo_chuoi(s: str) -> str:
    s = re.sub(r"--[^\n]*", "", s)
    return re.sub(r"'(?:[^']|'')*'", "''", s)


def _ngoac_dong(s: str, i: int) -> int:
    sau = 0
    for j in range(i, len(s)):
        sau += {"(": 1, ")": -1}.get(s[j], 0)
        if sau == 0:
            return j
    raise AssertionError("ngoặc không cân")


def _ten_khai(than: str, tham_so: str) -> set:
    ten = {p.split()[0] for p in tham_so.split(",") if p.strip()}
    m = re.match(r"\s*DECLARE(.*?)\bBEGIN\b", than, re.S)
    if m:
        ten |= {k.split()[0] for k in m.group(1).split(";") if k.strip()}
    return ten


def _alias_sql(than: str) -> set:
    """Alias quan hệ (bảng/hàm SRF/truy vấn con), alias cột `(c, ...)` và `AS c` trong phần thân sau BEGIN."""
    s = _bo_chuoi(than)
    s = s[re.search(r"\bBEGIN\b", s).end():]
    ra = set(re.findall(rf"\b(?:kho|m4|master)\.[a-z_0-9]+\s+(?:AS\s+)?({_ID})\b(?!\s*\()", s))
    for m in re.finditer(r"\(", s):
        truoc = re.search(rf"({_ID})\s*$", s[:m.start()])
        if not ((truoc and truoc.group(1) in _SRF) or re.match(r"\(\s*SELECT\b", s[m.start():])):
            continue
        sau = re.match(rf"\s*(?:AS\s+)?({_ID})(?:\(([a-z_0-9, ]+)\))?", s[_ngoac_dong(s, m.start()) + 1:])
        if sau and sau.group(1) not in _TU_KHOA:
            ra.add(sau.group(1))
            if sau.group(2):
                ra |= {c.strip() for c in sau.group(2).split(",")}
            elif truoc and truoc.group(1) in _SRF[:2]:
                ra.add("value")  # cột ngầm của jsonb_array_elements*
    ra |= set(re.findall(rf"\bAS\s+({_ID})\b", s))
    return ra - _TU_KHOA


def _cot_bang_moi() -> dict:
    cot = {}
    for t in SG.BANG:
        s = next(x for x in SG.M4_03B_COMMON_SQL if x.startswith(f"CREATE TABLE kho.{t} ("))
        cot[t] = set(re.findall(r"^\s+([a-z_0-9]+) (?:uuid|text|integer|jsonb|timestamptz)\b", s, re.M))
    return cot


def _plpgsql():
    """(tên, tên khai, thân) của mọi hàm + khối DO plpgsql trong hằng common."""
    for i, s in enumerate(SG.M4_03B_COMMON_SQL):
        m = re.match(r"\s*CREATE OR REPLACE FUNCTION (kho\.[a-z_0-9]+)\(([^)]*)\)", s)
        if m and "LANGUAGE plpgsql" in s.split("$$")[0]:
            than = s.split("$$")[1]
            yield m.group(1), _ten_khai(than, m.group(2)), than
        elif s.startswith("DO $$"):
            than = s.split("$$")[1]
            yield f"DO@{i}", _ten_khai(than, ""), than


def _xung_dot(ten: set, than: str, cot: dict) -> set:
    s = _bo_chuoi(than)
    dung = set().union(*(cot[t] for t in cot if re.search(rf"\b(?:FROM|JOIN|,)\s+kho\.{t}\b", s)))
    return ten & (_alias_sql(than) | dung)


class TenPlpgsql(unittest.TestCase):
    def test_bo_do_bat_dung_mau_loi_native05(self):
        # mẫu lỗi đã có bằng chứng native: biến jsonb `t` + alias `t` của _REFS cũ; biến `x` + alias `x` của _HIEN_HANH cũ
        cu = ("\n        DECLARE refs jsonb; t jsonb; x jsonb; ref jsonb;\n        BEGIN\n"
              "            refs := (SELECT jsonb_agg(t->'nguon' ORDER BY t->'nguon'->>'kind') FROM jsonb_array_elements(tp) t);\n"
              "            SELECT x INTO ref FROM jsonb_array_elements(refs) x WHERE x->>'kind' = 'NT';\n        END ")
        self.assertEqual(_xung_dot(_ten_khai(cu, ""), cu, {}), {"t", "x"})
        sach = cu.replace("t jsonb; x jsonb;", "v_muc jsonb; v_cap jsonb;")
        self.assertEqual(_xung_dot(_ten_khai(sach, ""), sach, {}), set())
        # cột bảng mới FROM trực tiếp cũng tính (biến trùng tên cột không qualify)
        cot = "\n DECLARE revision integer;\n BEGIN\n SELECT 1 FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.id IS NULL;\n END "
        self.assertEqual(_xung_dot(_ten_khai(cot, ""), cot, _cot_bang_moi()), {"revision"})

    def test_khong_ham_plpgsql_nao_trung_ten(self):
        cot = _cot_bang_moi()
        ham = {ten: (khai, than) for ten, khai, than in _plpgsql()}
        for can in ("kho.dc_luu", "kho.dc_xac_nhan", "kho._dc_phien_ban_hoan_tat", "kho._dc_phien_ban_kiem", "kho._dc_nguon_cua",
                    "kho._dc_do_thi", "kho._dc_cap_nguon", "kho._dc_xem", "kho._dc_thieu"):
            self.assertIn(can, ham)
        self.assertEqual(len([k for k in ham if k.startswith("DO@")]), 2)
        self.assertEqual(ham["DO@1"][0], {"r"})
        # bộ dò không rỗng trên hàm thật (không kiểm cho có)
        al = _alias_sql(ham["kho.dc_luu"][1])
        self.assertTrue({"dc_ref", "dc_hh", "dc_ghim", "value", "x", "z", "i", "a", "e"} <= al, al)
        self.assertTrue({"v_muc", "v_cap", "refs", "tp", "module", "p_khoa", "p_yc"} <= ham["kho.dc_luu"][0])
        loi = {ten: sorted(_xung_dot(khai, than, cot)) for ten, (khai, than) in ham.items()}
        self.assertEqual({k: v for k, v in loi.items() if v}, {})

    def test_refs_va_hien_hanh_alias_tuong_minh(self):
        self.assertIn("FROM jsonb_array_elements({x}) AS dc_ref(value))", SG._REFS)
        self.assertIn("jsonb_agg(dc_ref.value->'nguon' ORDER BY dc_ref.value->'nguon'->>'kind'", SG._REFS)
        self.assertNotRegex(SG._REFS, r"\bt->|\) t\)")
        self.assertIn("AS dc_hh(value)", SG._HIEN_HANH)
        self.assertIn("SELECT dc_ghim.value INTO ref FROM jsonb_array_elements({refs}) AS dc_ghim(value)", SG._HIEN_HANH)
        self.assertNotRegex(SG._HIEN_HANH, r"\bSELECT x INTO|\bx->>")
        b = _ham("kho.dc_luu")
        self.assertIn("refs := (SELECT jsonb_agg(dc_ref.value->'nguon'", b)
        self.assertIn("FROM jsonb_array_elements(tp) AS dc_ref(value))", b)
        dk = b[b.index("DECLARE"):b.index("BEGIN")]
        self.assertNotRegex(dk, r"[;\s]t jsonb|[;\s]x jsonb")
        self.assertIn("v_cap := kho._dc_cap_nguon(it, ai, aid)", b)
        self.assertIn("FOR v_muc IN SELECT z FROM jsonb_array_elements(tp) z LOOP", b)
        # cùng macro ở mọi nơi dùng (thân hàm trên clone phải bằng byte hằng)
        for h in ("kho._dc_phien_ban_kiem", "kho._dc_nguon_cua", "kho._dc_phien_ban_hoan_tat"):
            self.assertIn("AS dc_ref(value))", _ham(h))
        for h in ("kho.dc_luu", "kho.dc_xac_nhan", "kho._dc_phien_ban_hoan_tat"):
            self.assertIn("AS dc_ghim(value)", _ham(h))

    def test_khong_giau_loi_bang_cau_hinh(self):
        self.assertNotRegex(NOI, r"(?i)variable_conflict|use_variable|use_column")
        self.assertNotRegex(NOI, r"(?i)plpgsql\.")
        # guard/statement giữ nguyên: CAS nguồn + hiện hành NT vẫn ở cả ba nơi dùng _HIEN_HANH
        for h, ma in (("kho.dc_luu", "DC_NGUON_CU"), ("kho.dc_xac_nhan", "DC_CAN_KIEM_LAI"), ("kho._dc_phien_ban_hoan_tat", "DC_CAN_KIEM_LAI")):
            b = _ham(h)
            self.assertIn(f"RAISE EXCEPTION '{ma}: nguồn đã có phiên bản/phong bì mới hơn", b)
            self.assertIn("(ref->>'source_version_id') IS DISTINCT FROM (it->>'current')", b)
            self.assertIn("DC_CAN_KIEM_LAI: nguồn nghiệm thu không còn hiện hành", b)


# ================================================================================================== đầu vào
class KiemDauVao(unittest.TestCase):
    def test_luu_hop_le(self):
        y = GN.yeu_cau_luu(_luu())
        self.assertEqual([t["nguon"]["kind"] for t in y["thanh_phan"]], ["HOA_DON", "NT"])
        self.assertEqual(y["khoa"], "k-1")

    def test_khoa_tham_quyen_va_matching(self):
        for k in ("phap_nhan_id", "hop_dong_id", "doi_tac_id", "financial_owner", "claim", "ap", "khop", "score", "goi_y", "ten", "ngay_lap",
                  "so_tien", "graph_sha256", "trang_thai", "actor", "module", "capacity", "tap_sha256", "module_bien_nhan"):
            self.assertEqual(_ma(GN.yeu_cau_luu, _luu(**{k: "x"})), "DC_CLIENT_AUTHORITY", k)
        r = _ref()
        r["khop"] = True
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(r)])), "DC_CLIENT_AUTHORITY")

    def test_thieu_truong_la_truong(self):
        b = _luu()
        del b["ly_do"]
        self.assertEqual(_ma(GN.yeu_cau_luu, b), "DC_YEU_CAU_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(la="x")), "DC_YEU_CAU_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, []), "DC_YEU_CAU_SAI")

    def test_uuid_chuan(self):
        r = _ref()
        r["occurrence_id"] = r["occurrence_id"].replace("-", "")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(r)])), "DC_THAM_SO_SAI")

    def test_nt_khong_part_hoa_don_trung_chong(self):
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(part=9))])), "DC_PHAN_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref()), _tp(_ref())])), "DC_THAM_SO_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref("HOA_DON", 10, 11)), _tp(_ref("HOA_DON", 10, 11, 12))])), "DC_PHAN_SAI")

    def test_phan_va_ty_le_tho(self):
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(), "TOAN_PHAN", "50%")])), "DC_PHAN_SAI")
        self.assertIsNone(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(), "MOT_PHAN", "50%")])))
        self.assertIsNone(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(), "MOT_PHAN", None)])))
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(), "MOT_PHAN", "x" * 101)])), "DC_YEU_CAU_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(thanh_phan=[_tp(_ref(), "NUA", None)])), "DC_THAM_SO_SAI")

    def test_cas_va_revision(self):
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(expected_graph="A" * 64)), "DC_THAM_SO_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(expected_revision=1)), "DC_THAM_SO_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(doi_chieu_id=_id(5), expected_revision=0)), "DC_THAM_SO_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(expected_revision=True)), "DC_THAM_SO_SAI")
        self.assertIsNone(_ma(GN.yeu_cau_luu, _luu(doi_chieu_id=_id(5), expected_revision=3)))
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(khoa="có dấu")), "DC_KHOA_THAO_TAC")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(can_cu_tep=[_id(1), _id(1)])), "DC_CAN_CU_SAI")
        self.assertEqual(_ma(GN.yeu_cau_luu, _luu(ly_do="  ")), "DC_YEU_CAU_SAI")

    def test_xac_nhan_khong_gui_lai_noi_dung(self):
        self.assertIsNone(_ma(GN.yeu_cau_xac_nhan, _xn()))
        for k in ("thanh_phan", "ly_do", "can_cu_tep", "nguon", "graph_sha256"):
            self.assertEqual(_ma(GN.yeu_cau_xac_nhan, _xn(**{k: "x"})), "DC_CLIENT_AUTHORITY", k)
        self.assertEqual(_ma(GN.yeu_cau_xac_nhan, _xn(expected_revision=0)), "DC_THAM_SO_SAI")


# ================================================================================================== miền thuần
def _g(*ns):
    return {"contract": SG.CONTRACT_DO_THI, "nguon": list(ns)}


def _nt(**du):
    x = {"kind": "NT", "occurrence_id": _id(1), "part_id": None, "part_kind": "TOAN_BO", "current": _id(2), "hop_dong_id": _id(3),
         "doi_tac_mst": "0101", "hien_hanh": True, "toan_ven": True, "kt_xac_nhan_id": _id(4)}
    x.update(du)
    return x


def _hd(**du):
    x = {"kind": "HOA_DON", "occurrence_id": _id(10), "part_id": None, "part_kind": "TOAN_BO", "current": _id(11), "mst_ban": "0101",
         "cau_noi": [], "money_basis_state": "UNPROVEN_NO_MINOR"}
    x.update(du)
    return x


class MienThuan(unittest.TestCase):
    def test_du_can_cu(self):
        self.assertEqual(GN.thieu(_g(_nt(), _hd()), None), [])

    def test_tung_ma(self):
        self.assertEqual(GN.thieu(_g(_nt()), None), ["THIEU_HOA_DON"])
        self.assertEqual(GN.thieu(_g(_hd()), None), ["THIEU_NT"])
        self.assertEqual(GN.thieu(_g(_nt(hien_hanh=False), _hd()), None), ["NT_KHONG_HIEN_HANH"])
        self.assertEqual(GN.thieu(_g(_nt(kt_xac_nhan_id=None), _hd()), None), ["NT_CHUA_KT_XAC_NHAN"])
        self.assertEqual(GN.thieu(_g(_nt(), _nt(occurrence_id=_id(5), hop_dong_id=_id(6)), _hd()), None), ["NT_KHAC_HOP_DONG"])
        self.assertEqual(GN.thieu(_g(_nt(doi_tac_mst=None), _hd()), None), ["BEN_BAN_HD_THIEU"])
        self.assertEqual(GN.thieu(_g(_nt(), _hd(mst_ban="0999")), None), ["BEN_BAN_KHAC"])
        self.assertEqual(GN.thieu(_g(_nt(), _hd(current=None)), None), ["HOA_DON_CHUA_CO_PHIEN_BAN"])
        self.assertEqual(GN.thieu(_g(_nt(), _hd(part_id=_id(12), part_kind="DONG_LOGIC")), None), ["CHO_MAPPING_M2"])
        self.assertEqual(GN.thieu(_g(_nt(), _hd()), [{"phan": "MOT_PHAN", "ty_le_khai": None}]), ["PHAN_KHAI_THIEU"])

    def test_nhieu_ma_sap_ascii(self):
        x = GN.thieu(_g(_nt(hien_hanh=False, kt_xac_nhan_id=None)), [{"phan": "MOT_PHAN", "ty_le_khai": None}])
        self.assertEqual(x, sorted(x))
        self.assertEqual(x, ["NT_CHUA_KT_XAC_NHAN", "NT_KHONG_HIEN_HANH", "PHAN_KHAI_THIEU", "THIEU_HOA_DON"])

    def test_khong_khop_theo_ten_hay_tien(self):
        # cùng tên/ngày/tiền KHÔNG làm đủ căn cứ: chỉ dữ kiện MST master của HĐ vs mst_ban hóa đơn
        self.assertEqual(GN.thieu(_g(_nt(doi_tac_mst=None, ten="Cty A"), _hd(ten_ben_ban="Cty A")), None), ["BEN_BAN_HD_THIEU"])

    def test_hop_refs_closure(self):
        # gương kho._dc_hop: hợp theo (kind, occurrence, part), trùng khóa giữ refs yêu cầu, sắp theo khóa; thứ tự đầu vào không đổi kết quả
        moi = [_ref("HOA_DON", 10, 21), _ref()]
        cu = [_ref(ver=3), _ref("HOA_DON", 10, 11, 12), _ref("NT", 5, 6)]
        h = GN.hop_refs(moi, cu)
        self.assertEqual([GN._khoa_ref(r) for r in h], sorted(GN._khoa_ref(r) for r in h))
        self.assertEqual(len(h), 4)
        self.assertIn(_ref(), h, "trùng khóa giữ phiên bản của yêu cầu")
        self.assertNotIn(_ref(ver=3), h)
        self.assertIn(_ref("HOA_DON", 10, 11, 12), h, "nguồn bị bớt vẫn trong closure để khóa/kiểm quyền")
        self.assertEqual(GN.hop_refs(list(reversed(moi)), list(reversed(cu))), h)
        self.assertEqual(GN.hop_refs(moi, []), sorted(moi, key=GN._khoa_ref))

    def test_trang_thai_dan_xuat(self):
        self.assertEqual(GN.trang_thai("NHAP", SHA, SHA), SG.TT_NHAP)
        self.assertEqual(GN.trang_thai("XAC_NHAN", SHA, SHA), SG.TT_XAC_NHAN)
        self.assertEqual(GN.trang_thai("XAC_NHAN", SHA, "b" * 64), SG.TT_CAN_KIEM_LAI)
        self.assertEqual(GN.trang_thai("XAC_NHAN", SHA, None), SG.TT_CAN_KIEM_LAI)


# ================================================================================================== DTO (khung viết tay)
def _ket_qua(**du):
    k = {"hanh_dong": "LUU", "doi_chieu_id": _id(50), "phien_ban_id": _id(51), "revision": 1, "loai": "NHAP", "nhap_id": None,
         "trang_thai": SG.TT_NHAP, "thieu": ["NT_CHUA_KT_XAC_NHAN"], "graph_sha256": SHA, "noi_dung_sha256": "c" * 64, "trung_xac_nhan": False,
         "ghi_nhan": dict(GN.GHI_NHAN), "request": dict(GN.REQUEST)}
    k.update(du)
    return {"lap_lai": False, "ket_qua": k, "receipt_id": _id(60), "hien_tai": {"graph_sha256": SHA, "khop": True}}


class DtoBien(unittest.TestCase):
    def test_ack(self):
        a = GN.ack_dto(_ket_qua(tap_sha256="d" * 64), "k-1")
        self.assertEqual(a["doi_chieu"]["trang_thai"], SG.TT_NHAP)
        self.assertEqual(a["doi_chieu"]["tap_sha256"], "d" * 64)
        self.assertEqual(a["ghi_nhan"]["financial_owner"], None)
        self.assertEqual(a["request"], {"trang_thai": "CHUA_NOI_M4_04"})

    def test_ack_tai_chinh_khac_la_loi(self):
        k = _ket_qua()
        k["ket_qua"]["ghi_nhan"] = {**GN.GHI_NHAN, "financial_owner": "M4"}
        self.assertEqual(_ma(GN.ack_dto, k, "k"), "DC_SAI_DTO")
        k = _ket_qua(trang_thai=SG.TT_XAC_NHAN, loai="XAC_NHAN")
        self.assertEqual(_ma(GN.ack_dto, k, "k"), "DC_SAI_DTO", "xác nhận còn thiếu")

    def test_ack_do_thi_doi_la_can_kiem_lai(self):
        k = _ket_qua(trang_thai=SG.TT_XAC_NHAN, loai="XAC_NHAN", thieu=[])
        k["hien_tai"] = {"graph_sha256": "b" * 64, "khop": False}
        self.assertEqual(GN.ack_dto(k, "k")["doi_chieu"]["trang_thai"], SG.TT_CAN_KIEM_LAI)

    def test_xem_thieu_phai_bang_guong(self):
        g = _g(_nt(), _hd())
        r = {"do_thi": g, "graph_sha256": SHA, "thieu": [], "goc_lien_quan": [], "duoc_ghi": True, "goc_cua_tap": _id(50)}
        self.assertEqual(GN.xem_dto(r)["kt"]["thieu"], [])
        self.assertEqual(GN.xem_dto(r)["doi_chieu"]["goc_cua_tap"], _id(50))
        r2 = copy.deepcopy(r)
        r2["thieu"] = ["THIEU_NT"]
        self.assertEqual(_ma(GN.xem_dto, r2), "DC_SAI_DTO")

    def test_do_thi_khong_mang_tien(self):
        r = {"do_thi": _g(_nt(), _hd(total_minor=1)), "graph_sha256": SHA, "thieu": [], "goc_lien_quan": []}
        self.assertEqual(_ma(GN.xem_dto, r), "DC_SAI_DTO")

    def test_lich_su_financial_owner(self):
        r = {"doi_chieu_id": _id(50), "do_thi": _g(_nt(), _hd()), "graph_sha256": SHA,
             "module_bien_nhan": "M4", "bo_tap": [{"tap_sha256": "d" * 64, "phien_ban_id": _id(51)}],
             "phien_ban": [{"loai": "NHAP", "graph_sha256": SHA, "ghi_nhan": SG.GHI_NHAN_TT, "financial_owner": None}]}
        ls = GN.lich_su_dto(r)
        self.assertEqual(ls["doi_chieu"]["phien_ban"][0]["trang_thai"], SG.TT_NHAP)
        self.assertEqual(ls["module_bien_nhan"], "M4")
        self.assertEqual(ls["doi_chieu"]["bo_tap"], r["bo_tap"])
        r["phien_ban"][0]["financial_owner"] = "X"
        self.assertEqual(_ma(GN.lich_su_dto, r), "DC_SAI_DTO")


# ================================================================================================== thứ tự dịch vụ (FAKE có nhãn)
class FAKE_XD:
    """Giả lập ghi nhật ký gọi — KHÔNG phải PostgreSQL."""

    def __init__(self, tra: dict):
        self.log, self.tra = [], tra

    def danh_tinh(self, dn):
        self.log.append(("danh_tinh", dn))
        return {"id": _id(99), "dang_nhap": dn}

    @contextmanager
    def _tx(self, dt):
        self.log.append(("tx",))
        yield

    @contextmanager
    def _tx_review(self, dt, rr=False):
        self.log.append(("tx_review",))
        yield "C"

    @contextmanager
    def _chua_ro(self):
        yield

    def _mot(self, sql, params=()):
        self.log.append(("mot", sql.split("(")[0]))
        return {"ok": True}

    def _r1(self, c, sql, params=()):
        ten = re.search(r"SELECT (\S+?)\(", sql).group(1)
        self.log.append(("r1", ten, params))
        return {"r": self.tra.get(ten), "d": self.tra.get(ten), "q": "ok", "h": {}}


class FAKE_NT:
    def __init__(self, log):
        self.log = log

    def kiem_som(self, dt, cho):
        self.log.append(("nt_kiem_som", cho))

    def khoa_ghim(self, c, dt, chos, ghi):
        self.log.append(("nt_khoa_ghim", tuple(chos), ghi))


class ThuTuDichVu(unittest.TestCase):
    def _svc(self, tra):
        xd = FAKE_XD(tra)
        return GN.GhiNhanChungK2(xd, FAKE_NT(xd.log)), xd

    def test_validate_truoc_danh_tinh(self):
        s, xd = self._svc({})
        self.assertEqual(_ma(s.luu_doi_chieu, "kt1", _luu(phap_nhan_id=_id(1))), "DC_CLIENT_AUTHORITY")
        self.assertEqual(xd.log, [])

    def test_luu_thu_tu(self):
        s, xd = self._svc({"kho._dc_thu_tu_nt": [_id(1)], "kho.dc_luu": _ket_qua()})
        a = s.luu_doi_chieu("kt1", _luu())
        self.assertFalse(a["lap_lai"])
        buoc = [x[0] if x[0] != "r1" else x[1] for x in xd.log]
        self.assertEqual(buoc, ["danh_tinh", "tx", "mot", "nt_kiem_som", "tx_review", "kho._dc_thu_tu_nt", "nt_khoa_ghim", "kho.dc_luu"])
        self.assertIn(("nt_khoa_ghim", (_id(1),), True), xd.log)

    def test_luu_doi_tap_ghim_closure_union(self):
        # FIX01: revision đổi tập — refs revision mới nhất (NT 5 bị bớt) ∪ yêu cầu được ghim TRƯỚC lệnh, cùng giao dịch
        cu = [_ref("NT", 5, 6), _ref("HOA_DON", 10, 11)]
        s, xd = self._svc({"kho._dc_nguon_cua": cu, "kho._dc_thu_tu_nt": [_id(1), _id(5)], "kho.dc_luu": _ket_qua(revision=2)})
        s.luu_doi_chieu("kt1", _luu(doi_chieu_id=_id(50), expected_revision=1))
        buoc = [x[0] if x[0] != "r1" else x[1] for x in xd.log]
        self.assertEqual(buoc, ["danh_tinh", "tx", "mot", "nt_kiem_som", "tx_review", "kho._dc_nguon_cua", "kho._dc_thu_tu_nt", "nt_khoa_ghim",
                                "kho.dc_luu"])
        nc = next(x for x in xd.log if x[0] == "r1" and x[1] == "kho._dc_nguon_cua")
        self.assertEqual(nc[2], (_id(50), None), "closure đọc revision mới nhất của gốc")
        tt = next(x for x in xd.log if x[0] == "r1" and x[1] == "kho._dc_thu_tu_nt")
        self.assertEqual(json.loads(tt[2][0]), GN.hop_refs([_ref(), _ref("HOA_DON", 10, 11)], cu))
        self.assertIn(("nt_khoa_ghim", (_id(1), _id(5)), True), xd.log)
        lenh = next(x for x in xd.log if x[0] == "r1" and x[1] == "kho.dc_luu")
        than = json.loads(lenh[2][1])
        self.assertEqual(than["doi_chieu_id"], _id(50))
        self.assertEqual([t["nguon"] for t in than["thanh_phan"]], sorted([_ref(), _ref("HOA_DON", 10, 11)], key=GN._khoa_ref),
                         "body gửi SQL là tập yêu cầu, không phải union")
        self.assertNotIn("module", than)

    def test_xac_nhan_refs_truoc_ghim(self):
        s, xd = self._svc({"kho._dc_nguon_cua": [_ref()], "kho._dc_thu_tu_nt": [_id(1)],
                           "kho.dc_xac_nhan": _ket_qua(loai="XAC_NHAN", trang_thai=SG.TT_XAC_NHAN, thieu=[])})
        s.xac_nhan_doi_chieu("kt1", _xn())
        buoc = [x[1] if x[0] == "r1" else x[0] for x in xd.log]
        self.assertEqual(buoc, ["danh_tinh", "tx_review", "kho._dc_nguon_cua", "kho._dc_nguon_cua", "kho._dc_thu_tu_nt", "nt_khoa_ghim",
                                "kho.dc_xac_nhan"])
        nc = [x[2] for x in xd.log if x[0] == "r1" and x[1] == "kho._dc_nguon_cua"]
        self.assertEqual(nc, [(_id(50), _id(51)), (_id(50), None)], "nháp chỉ định ∪ revision mới nhất")

    def test_khong_adapter_tu_choi_nt(self):
        xd = FAKE_XD({})
        self.assertEqual(_ma(GN.GhiNhanChungK2(xd).luu_doi_chieu, "kt1", _luu()), "DC_PHAM_VI")

    def test_adapter_khoa_het_roi_moi_ghim(self):
        xd = FAKE_XD({})
        goi = []
        orig = AD.KT._ghim_do_thi
        AD.KT._ghim_do_thi = lambda x, c, dt, cho: goi.append(("ghim", cho))
        try:
            AD.NguonNghiemThu(xd).khoa_ghim("C", {"id": _id(9)}, [_id(1), _id(2)], True)
        finally:
            AD.KT._ghim_do_thi = orig
        ten = [x[1] for x in xd.log if x[0] == "r1"]
        self.assertEqual(ten[:2], ["m4.kt_khoa", "m4.kt_khoa"])
        self.assertEqual(ten[2:], ["kho._dc_nt_ghi", "kho._dc_nt_ghi"])
        self.assertEqual(goi, [("ghim", _id(1)), ("ghim", _id(2))])


# ================================================================================================== phạm vi file
class PhamVi(unittest.TestCase):
    def test_module_moi_khong_goi_writer_tien(self):
        for p in (SRC / "k2" / "ghi_nhan_chung.py", SRC / "m4" / "ghi_nhan_nghiem_thu.py"):
            s = p.read_text(encoding="utf-8")
            for cam in ("lien_ket_phan_bo", "de_xuat", "kt_luu", "kt_xac_nhan_lenh", "tien_con_lai", "INSERT INTO", "UPDATE kho", "UPDATE m4", "DELETE FROM"):
                self.assertNotIn(cam, s, f"{p.name}: {cam}")

    def test_ref_tu_kt(self):
        r = AD.ref_tu_kt({"context": {"kt_pending_id": _id(1), "phong_bi_id": _id(2)}})
        self.assertEqual(r, {"kind": "NT", "occurrence_id": _id(1), "source_version_id": _id(2), "part_id": None})
        self.assertEqual(_ma(AD.ref_tu_kt, {"context": {}}), "DC_THAM_SO_SAI")


if __name__ == "__main__":
    unittest.main()
