"""L11 QUANTITY R16 — migration M0016_L11_QUANTITY (append-only) — coder viết, CHƯA CHẠY (CODE_ONLY/UNRUN; repair02 cũng UNRUN).

Tĩnh: literal/generated 1–15 đúng oracle cases (statement count + checksum), M0016 là phần tử cuối (schema 16), finalizer 16 = finalizer 15 + đúng
một nhánh L11, SQL không M9/tiền/DELETE/TRUNCATE/DROP TABLE, mọi SECURITY DEFINER có search_path + REVOKE PUBLIC, thứ tự khóa xác nhận/undo/thu hồi,
số học exact (không làm tròn), RLS BOTH READ, payload profile bằng chứng đúng SHA canonical đã pin.
Repair02: R1 — 11 đường nguồn cũ + trigger mapping chung được CREATE OR REPLACE trong 16 bằng CHỈ CHÈN THÊM (opcode insert-only so với bản lịch sử)
lời gọi closure; trigger giữ soát kiểm khóa gốc thay vì xin khóa muộn. R2 — tỷ lệ cross trên lượng/đơn vị NATIVE, mã hóa hai tuple. R3 — source_ordinal
gốc, đo lường hiện hành, miền hàng, admission preview hai endpoint, parent UPDATE, coverage HOLD.
PostgreSQL (chỉ khi root cấp KHO_PG_DSN_TEST, DB DEMO mới): fresh 0→16; nâng 15→16 giữ hàng cũ; liên kết chung M1 thật vẫn chạy; liên kết chung
trỏ core M2/M5 bị chặn (INSERT và UPDATE); primitive số học. Không DROP/DELETE/cleanup.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import M0014_M5, M0015_M2_BRIDGE, M0016_L11_QUANTITY, PG_MIGRATIONS, PG_SCHEMA_VERSION
from kho_tri_thuc.ha_tang.primitives import sha256

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs" / "L11-QUANTITY-CASES-01.json"
CASES_SHA = "6ab9e6603fc7d3d067f4fd557630a11e84b91cfb4eb30e7c5e077e0a11c1f66f"
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
H = lambda statements: sha256("\n".join(statements).encode())  # noqa: E731
L11_TABLES = {"kho.bang_chung_ung_vien", "kho.bang_chung_quy_doi_luong", "kho.dich_so_luong", "kho.ma_hoa_luong_nguon", "kho.lien_ket_dong"}
# R1: 11 đường nguồn cũ (M5×5, M2×5, trigger mapping chung) — giữ ACL đã cấp ở 14/15 (CREATE OR REPLACE không đổi quyền)
R1_DUONG = {"kho.m5_khoa_phieu": M0014_M5, "kho.m5_tieu_thu_quan_sat": M0014_M5, "kho.m5_giu_cho_anh_huong": M0014_M5, "kho.m5_xem_xet_nguon": M0014_M5,
            "kho.m5_anh_xa_v4": M0014_M5, "kho.m2_tieu_thu_quan_sat": M0015_M2_BRIDGE, "kho.m2_xem_xet_nguon": M0015_M2_BRIDGE,
            "kho.m2_mapping_dong": M0015_M2_BRIDGE, "kho.m2_route": M0015_M2_BRIDGE, "kho.m2_mapping_cong_ty": M0015_M2_BRIDGE,
            "master.anh_xa_nguon_kiem": M0015_M2_BRIDGE}


def _fn(ten: str) -> str:
    return next(s for s in M0016_L11_QUANTITY if f"FUNCTION {ten}(" in s)


def _lich_su(ten: str, nguon: tuple) -> str:
    return next(s for s in reversed(nguon) if s.startswith(f"CREATE OR REPLACE FUNCTION {ten}("))


class TinhM0016(unittest.TestCase):
    def test_append_only_1_15_dung_oracle(self):
        raw = CASES.read_bytes()
        self.assertEqual(sha256(raw), CASES_SHA)
        pins = json.loads(raw.decode("utf-8"))["R15_final_interfaces"]["preserve_generated_migrations_1_to_15"]
        self.assertEqual(len(pins), 15)
        for p in pins:
            m = PG_MIGRATIONS[p["version"] - 1]
            self.assertEqual((len(m), H(m)), (p["statement_count"], p["checksum"]), p["version"])
        self.assertGreaterEqual(len(PG_MIGRATIONS), 16)
        self.assertEqual(PG_SCHEMA_VERSION, len(PG_MIGRATIONS))
        self.assertIs(PG_MIGRATIONS[14], M0015_M2_BRIDGE)
        self.assertIs(PG_MIGRATIONS[15], M0016_L11_QUANTITY)
        hist = [(i + 1, H(m)) for i, m in enumerate(PG_MIGRATIONS)]
        self.assertEqual(pg.kiem_lich_su(hist[:16]), 16)
        self.assertEqual(pg.kiem_lich_su(hist), PG_SCHEMA_VERSION)
        self.assertEqual(pg.kiem_lich_su(hist[:15]), 15)  # DB 15 đúng lineage vẫn nâng cấp được

    def test_sql_pham_vi_va_definer(self):
        sql = "\n".join(M0016_L11_QUANTITY)
        for cam in ("'M9'", "vay_", "lich_tra_no", "lien_ket_phan_bo", "dich_phan_bo_tien", "tien_con_lai", "kho.khoa(", "so_tien_khop_minor >",
                    "DELETE FROM", "TRUNCATE", "DROP TABLE", "TO PUBLIC", "ALTER TABLE kho.lien_ket_dong DISABLE", "DISABLE TRIGGER", "331", "BANK"):
            self.assertNotIn(cam, sql, cam)
        for bang in L11_TABLES:
            self.assertIn(f"CREATE TABLE {bang} (", sql, bang)
            self.assertIn(f"ALTER TABLE {bang} ENABLE ROW LEVEL SECURITY", sql, bang)
        revoked = "\n".join(s for s in M0016_L11_QUANTITY if s.startswith("REVOKE EXECUTE"))
        for stmt in M0016_L11_QUANTITY:
            if "SECURITY DEFINER" not in stmt or not stmt.startswith("CREATE OR REPLACE FUNCTION"):
                continue
            fn = re.match(r"CREATE OR REPLACE FUNCTION ([\w.]+)\(", stmt).group(1)
            with self.subTest(fn=fn):
                self.assertIn("SET search_path =", stmt)
                if "RETURNS trigger" not in stmt and fn != "giao_tiep.nguon_chot_ket_qua" and fn not in R1_DUONG:  # finalizer/đường cũ giữ ACL 13–15
                    self.assertIn(fn + "(", revoked)
        grants = "\n".join(s for s in M0016_L11_QUANTITY if "GRANT EXECUTE" in s)
        for noi_bo in ("l11_quyen_noi_bo(", "l11_danh_gia_noi_bo(", "l11_can_soat_noi_bo(", "l11_tieu_thu_bang_chung(", "l11_file_bat_dau(",
                       "l11_file_tieu_thu(", "luong_da_khop_noi_bo(", "l11_ngan_sach_noi_bo(", "l11_khoa_goc_noi_bo("):
            self.assertNotIn(noi_bo, grants, noi_bo)

    def test_finalizer_16_chi_them_nhanh_l11(self):
        f15 = next(s for s in M0015_M2_BRIDGE if s.startswith("CREATE OR REPLACE FUNCTION giao_tiep.nguon_chot_ket_qua"))
        f16 = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE OR REPLACE FUNCTION giao_tiep.nguon_chot_ket_qua"))
        neo = "            IF s.module = 'M2' THEN\n"
        self.assertEqual((f15.count(neo), f16.count(neo)), (1, 1))
        dau = f15.split(neo)[0]
        self.assertTrue(f16.startswith(dau))
        nhanh = f16[len(dau):].split(neo)[0]  # phần chèn thêm ngay trước nhánh M2
        self.assertTrue(nhanh.startswith("            IF s.du_lieu ? 'l11_proof' THEN"))
        self.assertEqual(f16.replace(nhanh, "", 1), f15)  # bỏ đúng nhánh L11 → trùng từng ký tự finalizer 15
        self.assertIn("kết quả L11 do CSDL dẫn xuất", nhanh)

    def test_thu_tu_khoa_va_replay(self):
        xn = _fn("kho.l11_xac_nhan")
        thu_tu = ["KHONG_CO_QUYEN_L11_LIEN_KET", "kho.l11_trang_thai_cap_noi_bo(p)", "'BIEN_NHAN|'", "FROM kho.bien_nhan_thao_tac", "kho.l11_khoa_goc_noi_bo(",
                  "kho.l11_khoa_pool_noi_bo(", "WHERE x.id = b0.hoa_don_id FOR SHARE", "ORDER BY q.id FOR SHARE", "kho.l11_danh_gia_noi_bo(p)",
                  "L11_VERSION_CHANGED", "INSERT INTO kho.lien_ket_chung_tu", "INSERT INTO kho.bien_nhan_thao_tac", "INSERT INTO kho.lien_ket_dong"]
        for a, b in zip(thu_tu, thu_tu[1:]):
            self.assertLess(xn.index(a), xn.index(b), (a, b))
        self.assertIn("kho.l11_ket_qua_dong_noi_bo((SELECT c.id FROM kho.lien_ket_dong c", xn)  # replay trả trạng thái HIỆN HÀNH
        huy = _fn("kho.l11_huy")
        for a, b in (("KHONG_CO_QUYEN_L11_LIEN_KET", "FROM kho.bien_nhan_thao_tac"), ("FROM kho.bien_nhan_thao_tac", "kho.l11_khoa_goc_noi_bo("),
                     ("kho.l11_khoa_pool_noi_bo(", "FOR UPDATE"), ("FOR UPDATE", "UPDATE kho.lien_ket_dong SET trang_thai = 'HUY'")):
            self.assertLess(huy.index(a), huy.index(b), (a, b))
        thu = _fn("kho.l11_huy_bang_chung")
        for a, b in (("FROM kho.bien_nhan_thao_tac", "kho.l11_khoa_goc_noi_bo("), ("kho.l11_khoa_goc_noi_bo(", "L11_CLOSURE_MO_RONG"),
                     ("kho.l11_khoa_goc_noi_bo(", "FOR UPDATE"), ("FOR UPDATE", "UPDATE kho.bang_chung_quy_doi_luong")):
            self.assertLess(thu.index(a), thu.index(b), (a, b))
        goc = _fn("kho.l11_khoa_goc_noi_bo")
        self.assertLess(goc.index("'HOA_DON_ROOT|'"), goc.index("'PHIEU_KHO|'"))  # cùng tên khóa với entrypoint M2/M5 cũ, thứ tự chuẩn

    def test_r1_11_duong_chi_chen_closure(self):
        """Mỗi đường nguồn cũ trong 16 = bản lịch sử 14/15 + CHỈ dòng chèn thêm (không sửa/xóa dòng cũ); dòng chèn gọi closure TRƯỚC khóa gốc/ghi."""
        for ten, nguon in R1_DUONG.items():
            with self.subTest(fn=ten):
                cu, moi = _lich_su(ten, nguon), _fn(ten)
                ops = difflib.SequenceMatcher(None, cu.splitlines(), moi.splitlines(), autojunk=False).get_opcodes()
                self.assertEqual({op[0] for op in ops} - {"equal"}, {"insert"})
                chen = "\n".join(ln for op in ops if op[0] == "insert" for ln in moi.splitlines()[op[3]:op[4]])
                ky_vong = "kho.l11_kiem_khoa_dong_noi_bo(" if ten == "master.anh_xa_nguon_kiem" else "kho.l11_khoa_dong_nguon_noi_bo("
                self.assertIn(ky_vong, chen)
                for cam in ("DELETE", "pg_advisory_unlock", "SET hieu_luc", "so_luong_pool"):
                    self.assertNotIn(cam, chen)
        # điểm chèn: trước khóa gốc cũ / trước UPDATE đóng mapping
        for ten, moc in (("kho.m5_xem_xet_nguon", "hashtextextended('PHIEU_KHO|' || d0.source_instance_id"),
                         ("kho.m5_tieu_thu_quan_sat", "hashtextextended('PHIEU_KHO|' || l.source_instance_id || '|' || v_so"),
                         ("kho.m2_route", "hashtextextended('HOA_DON_ROOT|' || d0.id"), ("kho.m2_xem_xet_nguon", "hashtextextended('HOA_DON_ROOT|' || d0.id"),
                         ("kho.m5_anh_xa_v4", "UPDATE master.anh_xa_nguon SET state = 'DONG'"),
                         ("kho.m2_mapping_cong_ty", "UPDATE master.anh_xa_nguon SET state = 'DONG'"),
                         ("kho.m2_tieu_thu_quan_sat", "FOR it IN SELECT * FROM jsonb_array_elements")):
            with self.subTest(moc=ten):
                f = _fn(ten)
                self.assertLess(f.index("kho.l11_khoa_dong_nguon_noi_bo("), f.index(moc))
        cl = _fn("kho.l11_khoa_dong_nguon_noi_bo")
        for a, b in (("kho.l11_khoa_goc_noi_bo(v_hd, v_pk)", "L11_CLOSURE_MO_RONG"), ("L11_CLOSURE_MO_RONG", "kho.l11_khoa_pool_noi_bo(v_pool)"),
                     ("kho.l11_khoa_pool_noi_bo(v_pool)", "FOR UPDATE")):  # repair03: kiểm lại trùng khít TRƯỚC pool/hàng
            self.assertLess(cl.index(a), cl.index(b), (a, b))
        cs = _fn("kho.l11_can_soat_noi_bo")
        self.assertLess(cs.index("kho.l11_kiem_khoa_dong_noi_bo(p_dong)"), cs.index("UPDATE kho.lien_ket_dong"))  # kiểm khóa, không xin khóa muộn
        self.assertNotIn("pg_advisory_xact_lock", cs)
        self.assertIn("pg_locks", _fn("kho.l11_giu_khoa_noi_bo"))
        self.assertTrue(M0016_L11_QUANTITY[-1].startswith("CREATE OR REPLACE FUNCTION master.anh_xa_nguon_kiem("))

    def test_r1_repair03_cong_identity_va_kiem_lai_trung_khit(self):
        """Cổng identity toàn batch của consumer M2: mapping → MỌI namespace HOA_DON sorted → skeleton → closure, TRƯỚC vòng lặp lịch sử (giữ thứ tự
        quan sát); helper/revoke đọc lại tập child TRÙNG KHÍT ngay sau gốc, TRƯỚC khi xin pool (không truy vấn pool mới sau chờ gốc)."""
        m2 = _fn("kho.m2_tieu_thu_quan_sat")
        thu_tu = ["ORDER BY x.id FOR SHARE", "pg_advisory_xact_lock(hashtextextended(r1_k, 0))", "INSERT INTO kho.hoa_don_danh_tinh",
                  "kho.l11_khoa_dong_nguon_noi_bo(r1_hd, NULL)", "FOR it IN SELECT * FROM jsonb_array_elements",
                  "hashtextextended('HOA_DON|' || m.phap_nhan_id", "hashtextextended('HOA_DON_ROOT|' || d.id"]
        for a, b in zip(thu_tu, thu_tu[1:]):
            self.assertLess(m2.index(a), m2.index(b), (a, b))
        self.assertIn("ORDER BY 1 LOOP", m2[m2.index("FOR r1_k IN"):m2.index("pg_advisory_xact_lock(hashtextextended(r1_k, 0))")])
        self.assertEqual(m2.count("HOA_DON|"), 2)  # namespace lịch sử trong vòng lặp nay chỉ tái nhập khóa đã giữ
        cl = _fn("kho.l11_khoa_dong_nguon_noi_bo")
        for a, b in (("kho.l11_khoa_goc_noi_bo(v_hd, v_pk)", "v_dong2 IS DISTINCT FROM v_dong"), ("v_dong2 IS DISTINCT FROM v_dong", "kho.l11_khoa_pool_noi_bo(v_pool)")):
            self.assertLess(cl.index(a), cl.index(b), (a, b))
        self.assertLess(cl.index("INTO v_pool"), cl.index("kho.l11_khoa_goc_noi_bo(v_hd, v_pk)"))  # pool bind lúc precollect
        thu = _fn("kho.l11_huy_bang_chung")
        for a, b in (("INTO v_pool", "kho.l11_khoa_goc_noi_bo(v_hd, v_pk)"), ("kho.l11_khoa_goc_noi_bo(v_hd, v_pk)", "v_dong IS DISTINCT FROM v_dong0"),
                     ("v_dong IS DISTINCT FROM v_dong0", "kho.l11_khoa_pool_noi_bo(v_pool)"), ("kho.l11_khoa_pool_noi_bo(v_pool)", "FOR UPDATE")):
            self.assertLess(thu.index(a), thu.index(b), (a, b))
        self.assertNotIn("kho.l11_khoa_pool_noi_bo(ARRAY(SELECT DISTINCT", thu)

    def test_c_native_ma_hoa_do_dai_va_ho_tro_truoc_duyet(self):
        xn = _fn("kho.l11_xac_nhan_bang_chung")
        nhanh = xn[xn.index("ELSIF u.kind = 'NATIVE_ENCODING' THEN"):]
        chen = nhanh.index("INSERT INTO kho.bang_chung_quy_doi_luong")
        for ma in ("L11_DO_DAI_NATIVE_SAI", "'^[1-9][0-9]{0,17}$'", "L11_HO_TRO_CHUA_CAPTURE", "L11_HO_TRO_DON_VI_KHONG_KHOP",
                   "kho.l11_ho_tro_don_vi_noi_bo(v_dv.id, v_gq.hang_hoa_hoa_don)"):
            self.assertLess(nhanh.index(ma), chen, ma)
        self.assertIn("native_xml_sha256, native_byte_length, quantity_locator", nhanh)
        bc = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.bang_chung_quy_doi_luong"))
        self.assertIn("native_byte_length bigint CHECK (native_byte_length IS NULL OR native_byte_length >= 1)", bc)
        self.assertIn("AND native_byte_length IS NOT NULL", bc)
        self.assertIn("NEW.native_byte_length", _fn("kho.bang_chung_quy_doi_kiem"))
        self.assertIn("q.native_byte_length IS DISTINCT FROM (rw->>'byte_length')::bigint", _fn("kho.l11_ma_hoa"))

    def test_r2_ty_le_native_va_hai_tuple(self):
        dg = _fn("kho.l11_danh_gia_noi_bo")
        self.assertIn("v_a * x.tu_so <> v_b * x.mau_so", dg)
        self.assertNotIn("v_pa * x.tu_so", dg)
        self.assertIn("x.tu_don_vi_id IS DISTINCT FROM ei.don_vi_nguon_id OR x.den_don_vi_id IS DISTINCT FROM ew.don_vi_nguon_id", dg)
        self.assertIn("kho.l11_quy_doi(v_a, ei.tu_so, ei.mau_so); v_pb := kho.l11_quy_doi(v_b, ew.tu_so, ew.mau_so)", dg)  # pool dẫn xuất riêng
        bc = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.bang_chung_quy_doi_luong"))
        self.assertIn("kind = 'NATIVE_ENCODING' AND hang_hoa_bang_chung_id IS NOT NULL AND tu_don_vi_id IS NOT NULL", bc)
        self.assertIn("don_vi_id IS NULL AND don_vi_sha256 IS NULL", bc)
        mh = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.ma_hoa_luong_nguon"))
        self.assertIn("don_vi_nguon_id uuid NOT NULL", mh)
        self.assertIn("don_vi_nguon_id = don_vi_pool_id", mh)
        xn = _fn("kho.l11_xac_nhan_bang_chung")
        self.assertNotIn("r->>'pool_unit_definition_ref' IS DISTINCT FROM v_dv.reference_id", xn)  # không còn ép pool = native
        self.assertIn("v_fu.id, v_fu.definition_sha256, v_tu, v_mau", xn)
        ld = _fn("kho.lien_ket_dong_kiem")
        self.assertIn("NEW.so_luong_hoa_don_nguon * xr.tu_so IS DISTINCT FROM NEW.so_luong_phieu_nguon * xr.mau_so", ld)

    def test_r3_nguon_that_quyen_rieng_tu_va_coverage(self):
        dg = _fn("kho.l11_danh_gia_noi_bo")
        self.assertNotIn("lw.stt", dg)
        self.assertEqual(dg.count("(lw.source_ordinal + 1)::text"), 2)
        self.assertEqual(dg.count("e->>'measurement_payload_sha256' IS NOT DISTINCT FROM v_do_luong"), 2)
        self.assertIn("L11_BANG_CHUNG_HANG_NGOAI_MIEN", dg)
        self.assertLess(dg.index("kho.l11_trang_thai_cap_noi_bo(p) IS NULL"), dg.index("SELECT y.* INTO hd FROM"))
        xt = _fn("kho.l11_xem_truoc")
        self.assertLess(xt.index("kho.l11_trang_thai_cap_noi_bo(p)"), xt.index("kho.l11_danh_gia_noi_bo(p)"))
        pr = _fn("kho.lien_ket_l11_kiem")
        self.assertIn("TG_OP = 'INSERT' OR (NEW.chung_tu_a_id, NEW.chung_tu_b_id) IS DISTINCT FROM (OLD.chung_tu_a_id, OLD.chung_tu_b_id)", pr)
        tt = _fn("kho.l11_tieu_thu_bang_chung")
        for ma in ("L11_COVERAGE_", "L11_COVERAGE_HIEU_LUC_CHUA_DU", "L11_LOI_BAO_CAO_NGUON"):
            self.assertIn(ma, tt)
        uv = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.bang_chung_ung_vien"))
        self.assertIn("trang_thai = 'HOLD' OR (coverage = 'COMPLETE_INPUT' AND coverage_hieu_luc = 'COMPLETE_INPUT'", uv)
        mh = _fn("kho.l11_ma_hoa")
        for ma in ("kho.l11_ho_tro_don_vi_noi_bo(dv.id, lw.ma_hang_raw)", "kho.l11_do_luong_dong_noi_bo(lw.id)", "q.mien->>'source_instance'"):
            self.assertIn(ma, mh)

    def test_so_hoc_exact_va_tu_choi_number(self):
        qd = _fn("kho.l11_quy_doi")
        self.assertIn("q * mau <> x * tu", qd)
        self.assertIn("RETURN NULL", qd)
        self.assertNotIn("abs(", "\n".join(M0016_L11_QUANTITY))
        tl = _fn("kho.l11_so_ty_le")
        self.assertIn("jsonb_typeof(v) = 'string'", tl)
        self.assertIn("'^[1-9][0-9]{0,37}$'", tl)
        self.assertIn("'^(0|[1-9][0-9]{0,25})(\\.[0-9]{1,12})?$'", _fn("kho.l11_so_nguon"))
        bc = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.bang_chung_quy_doi_luong"))
        self.assertIn("gcd(tu_so, mau_so) = 1", bc)
        ld = next(s for s in M0016_L11_QUANTITY if s.startswith("CREATE TABLE kho.lien_ket_dong"))
        for ma in ("UNIQUE (phap_nhan_id, xac_nhan_bien_nhan_id)", "numeric(38,12) NOT NULL CHECK (so_luong_pool_phieu > 0)", "CHECK (trang_thai IN ('CHO','DA_KHOP','HUY'))",
                   "CHECK (hieu_luc IN ('CO_HIEU_LUC','CAN_SOAT'))"):
            self.assertIn(ma, ld)
        ns = _fn("kho.l11_ngan_sach_noi_bo")
        self.assertIn("v_cap - dung.da_xac_nhan - dung.dang_giu", ns)  # used = confirmed + held, không clamp
        self.assertNotIn("greatest(", ns)

    def test_rls_both_read_va_parent(self):
        sql = "\n".join(M0016_L11_QUANTITY)
        self.assertIn("FOR SELECT TO app_web USING (master.ktt_duoc(phap_nhan_id, %L) AND master.ktt_duoc(phap_nhan_id, %L))'", sql)
        self.assertIn("t || '_pham_vi_web', t, 'M2', 'M5')", sql)
        self.assertIn("ELSE master.ktt_duoc(phap_nhan_id, 'M2') AND master.ktt_duoc(phap_nhan_id, 'M5') END)", sql)  # parent L11 cần BOTH READ
        self.assertIn("WITH CHECK (chu_so_huu_module IS NULL AND master.ktt_duoc(phap_nhan_id, 'M1'))", sql)
        self.assertIn("L11_LIEN_KET_CHUNG_GIA", sql)
        self.assertIn("L11_CHA_BAT_BIEN", sql)
        self.assertNotIn("'kho.bang_chung_ung_vien'\n", "\n".join(s for s in M0016_L11_QUANTITY if "GRANT SELECT" in s))

    def test_profile_bang_chung_dung_sha(self):
        from kho_tri_thuc.k2 import l11_demo
        from kho_tri_thuc.k2.nguon_chung import digest_payload
        self.assertEqual(digest_payload(l11_demo.EVIDENCE_PROFILE_PAYLOAD), "3cc2d403d3ae7986c75fd21767763c2fe23678d59290618225463c870e3d9251")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL L11 không chạy (không tính đạt)")
class PgM0016(unittest.TestCase):
    def ket_noi(self, prefix):
        name = prefix + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
        c = psycopg.connect(ADMIN_DSN.rsplit("/", 1)[0] + "/" + name, autocommit=True)
        self.addCleanup(c.close)  # chỉ đóng kết nối; DB giữ làm bằng chứng
        return c

    @staticmethod
    def bang(c):
        return {r[0] for r in c.execute("""SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                           WHERE c.relkind IN ('r','v') AND n.nspname IN ('master','kho','giao_tiep','nhat_ky','bao_mat')""")}

    def test_fresh_0_den_16_va_primitive(self):
        c = self.ket_noi("kho_test_l11mig_moi_")
        self.assertEqual(pg.migrate(c), 16)
        self.assertEqual(pg.migrate(c), 16)
        self.assertTrue(L11_TABLES <= self.bang(c))
        q = lambda s, p=None: c.execute(s, p).fetchone()[0]  # noqa: E731
        self.assertIsNone(q("SELECT kho.l11_quy_doi(1, 1, 12)"))  # 1/12 không biểu diễn được → NULL, không làm tròn
        self.assertEqual(q("SELECT kho.l11_quy_doi(0.5, 12, 1)::text"), "6.000000000000")
        self.assertEqual(q("SELECT kho.l11_quy_doi(6, 1, 1)::text"), "6.000000000000")
        for v, ky_vong in (('"12"', "12"), ('"1"', "1"), ("12", None), ('"1.5"', None), ('"0"', None), ('"012"', None), ('"' + "9" * 39 + '"', None),
                           ("true", None), ("null", None)):
            with self.subTest(v=v):
                self.assertEqual(q("SELECT kho.l11_so_ty_le(%s::jsonb)::text", (v,)), ky_vong)
        for t, ky_vong in (("8", "8.000000000000"), ("0.5", "0.500000000000"), ("0", None), ("-1", None), ("1e2", None), ("1.0000000000001", None), (" 8", None)):
            with self.subTest(t=t):
                self.assertEqual(q("SELECT kho.l11_so_nguon(%s)::text", (t,)), ky_vong)

    def test_nang_cap_15_den_16_giu_hang_cu_va_lien_ket_m1(self):
        c = self.ket_noi("kho_test_l11mig_up_")
        self.assertEqual(pg.migrate(c, target=15), 15)
        pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('L11_UP_PN','PN nâng cấp') RETURNING id").fetchone()[0]
        a = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'HD_MUA','UP-A','2026-08-01',%s)
                         RETURNING id""", (pn, "1" * 64)).fetchone()[0]
        # PHIEU_KHO mới từ 14 được gắn M5 → liên kết chung M1 dùng cặp chứng từ M1 (HD_MUA không khai M2 + SAO_KE)
        b = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'SAO_KE','UP-B','2026-08-01',%s)
                         RETURNING id""", (pn, "2" * 64)).fetchone()[0]
        lk = c.execute("""INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'HD_PHIEU_KHO') RETURNING id""",
                       (pn, a, b)).fetchone()[0]
        cu = c.execute("SELECT to_jsonb(x)::text FROM kho.lien_ket_chung_tu x WHERE x.id = %s", (lk,)).fetchone()[0]
        self.assertEqual(pg.migrate(c), 16)
        sau = json.loads(c.execute("SELECT to_jsonb(x)::text FROM kho.lien_ket_chung_tu x WHERE x.id = %s", (lk,)).fetchone()[0])
        self.assertEqual({k: v for k, v in sau.items() if k not in ("chu_so_huu_module", "muc_dich_lien_ket", "hoa_don_id", "phieu_id")}, json.loads(cu))
        self.assertEqual([sau[k] for k in ("chu_so_huu_module", "muc_dich_lien_ket", "hoa_don_id", "phieu_id")], [None] * 4)
        # liên kết chung M1 thật (hai chứng từ M1) vẫn tạo được sau 16
        b2 = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'SAO_KE','UP-C','2026-08-02',%s)
                          RETURNING id""", (pn, "3" * 64)).fetchone()[0]
        c.execute("INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'HD_PHIEU_KHO')", (pn, a, b2))
        # liên kết chung trỏ core M2 bị chặn (không giả hàng cũ cho graph typed)
        m2 = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash, module_nghiep_vu) VALUES (%s,'HD_MUA','UP-M2','2026-08-03',%s,'M2')
                          RETURNING id""", (pn, "4" * 64)).fetchone()[0]
        with self.assertRaises(psycopg.Error) as cm:
            c.execute("INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'HD_PHIEU_KHO')", (pn, m2, b2))
        self.assertIn("L11_LIEN_KET_CHUNG_GIA", str(cm.exception))
        # hàng chung cũ (chủ NULL, M1) không được UPDATE retarget endpoint vào core M2 rồi đi policy cũ; hàng giữ nguyên byte.
        # repair03 (D): native02 cho thấy trigger LỊCH SỬ `lien_ket_kiem` từ chối TRƯỚC bằng P0001 LIEN_KET_KHONG_SUA — assert đúng mã thực đó,
        # không đổi thứ tự trigger/quyền để ép mã L11 (guard L11 UPDATE vẫn tồn tại, ca INSERT ở trên kiểm mã L11 riêng)
        with self.assertRaises(psycopg.Error) as cm:
            c.execute("UPDATE kho.lien_ket_chung_tu SET chung_tu_a_id = %s WHERE id = %s", (m2, lk))
        self.assertEqual((cm.exception.sqlstate, cm.exception.diag.message_primary.split(":", 1)[0]), ("P0001", "LIEN_KET_KHONG_SUA"))
        self.assertEqual({k: v for k, v in json.loads(c.execute("SELECT to_jsonb(x)::text FROM kho.lien_ket_chung_tu x WHERE x.id = %s", (lk,)).fetchone()[0]).items()
                          if k not in ("chu_so_huu_module", "muc_dich_lien_ket", "hoa_don_id", "phieu_id")}, json.loads(cu))
        # nhánh L11 thiếu chủ bảng/đồ thị: owner chèn parent L11 không đúng cặp → L11_CHA_SAI_DO_THI
        with self.assertRaises(psycopg.Error) as cm:
            c.execute("""INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, trang_thai, chu_so_huu_module, muc_dich_lien_ket,
                         hoa_don_id, phieu_id) VALUES (%s,%s,%s,'HD_PHIEU_KHO','DA_KHOP','M5','EVIDENCE',%s,%s)""",
                      (pn, a, b, str(uuid.uuid4()), str(uuid.uuid4())))
        self.assertTrue(any(m in str(cm.exception) for m in ("L11_CHA_SAI_DO_THI", "violates foreign key")), str(cm.exception))


if __name__ == "__main__":
    unittest.main()
