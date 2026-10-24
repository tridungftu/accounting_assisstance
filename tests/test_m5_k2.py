"""M5 phiếu kho — service K2 (KhoSoLuongK2) + intake trung tính (nguon_chung) + seed DEMO (m5_demo), bản sửa 02.

Phần thuần (không DB): context do máy chủ dựng từ bytes đã pin + registry → reader final; facts đo lường chỉ resolve đúng điều kiện pin;
capture H `m0-capture/v1` tách khỏi reader H; bundle vai trò; reported_errors chặt (vắng = [], hiện diện phải là list mã); coverage hiệu lực
tách claim; dòng nguồn giữ token số lượng; ma trận hành động M5; workbook file soát text/formula-safe từ snapshot.
Phần PostgreSQL (chỉ khi root cấp KHO_PG_DSN_TEST): login ứng dụng thật thuộc app_web + kết nối chủ bảng cho intake/file (đúng kiến trúc sửa 02).
K01–K10, retry/409/fresh, quyền nguồn trước tra cứu, core PHIEU_KHO quantity-only (owner M5, tiền NULL), review chỉ quan sát mới nhất (stale A
là âm), A→B đảo→A cũ, partial, NULL≠0/Number, UOM, SQL trực tiếp/forgery stage-biên nhận-lô-core bị chặn + consume stage hợp lệ của chủ
(dương), hai kết nối cùng khóa, mapping SOURCE_MAP+V4 qua hàm định nghĩa, file soát idempotent/expected graph/cells, sentinel non-M5 nguyên,
kỳ khóa, seed mở lại giữ quyền/thu hồi, thu hồi trước replay. Không DROP DB/role, không xóa thư mục tạm: giữ làm bằng chứng.

Sửa 03 (regression theo review02): validator chủ bảng tuple + dict_row (dương) / sai chủ / cột gộp (âm, không IndexError); replay capture trả ĐÚNG
kết quả cuối đã chốt (promote/stage/snapshot_moi, kể cả HOLD kỳ khóa) với 0 delta; K08/09/10 nguồn Đã duyệt được chấp nhận nhưng eligible NULL
(K01 exact dương); token basis FILE: basis đổi khi ba con trỏ giữ nguyên → 409 0 delta, kỳ khóa kiểm TRƯỚC cached FILE; namespace biên nhận
FILE/MAP hai yêu cầu đồng thời có observer nhân quả (backend đang chờ advisory lock) + positive control — hết giờ/treo là KHÔNG đạt;
nguồn DUNG không qua getter SOURCE_MAP. Root chạy riêng; coder không chạy.

Sửa 04: chi_tiet + token cùng snapshot (interleave thật với kết nối chủ thứ hai sau SELECT mapping; view cũ → FILE 409 0 delta, view mới dương);
oracle partial theo đúng phieu_id+PN (A/B cùng native line IDs); namespace FILE với HAI phiếu thật cùng PN qua intake thật, cả hai thứ tự thắng
(thay test winner mô phỏng của 03).
"""

from __future__ import annotations

import io
import json
import os
import secrets
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.k2 import m5_demo, nguon_chung, quyen
from kho_tri_thuc.k2.kho_so_luong import KhoSoLuongK2
from kho_tri_thuc.nguon.kho_10 import doc_phieu_kho

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
GOLDEN = json.loads((ROOT / "tests" / "fixtures" / "kho_10" / "observer" / "expected-fingerprints.json").read_text("utf-8"))["cases"]
M0A, M0B, KTA, KTB = "MO_PHONG_M0_KHO_A", "MO_PHONG_M0_KHO_B", "MO_PHONG_KT_KHO_A", "MO_PHONG_KT_KHO_B"
CFOA, CFOB, VIEWA, M1A = "MO_PHONG_CFO_KHO_A", "MO_PHONG_CFO_KHO_B", "MO_PHONG_VIEW_KHO_A", "MO_PHONG_M1_ONLY_KHO_A"
FULL = "FULL_FOR_SINGLE_DETAIL_AND_REFERENCED_MASTER_ONLY"


def registry():
    return m5_demo.doc_registry()


def profile_cua(reg, inst):
    s = next(x for x in reg["source_instances"] if x["source_instance"] == inst)
    p = next(x for x in reg["source_profiles"] if x["reference_id"] == s["profile_ref"])
    return {"reference_id": p["reference_id"], "sha256": p["sha256"], "payload": p["payload"]}


def scope_cua(reg, inst):
    c = next(x for x in reg["configured_scopes"] if x["source_instance"] == inst)
    return {"scope_ref": c["scope_ref"], "MaKho": c["MaKho"], "SoPhieu": c["SoPhieu"], "sections": sorted(set(c["sections"]))}


def facts_cua(reg, inst):
    return [{"payload": f["payload"], "dieu_kien": {"resolution_preconditions": f["resolution_preconditions"], "non_matching_resolution": f["non_matching_resolution"]}}
            for f in reg["measurement_facts"] if f["source_instance"] == inst]


def mapping_cua(reg, inst):
    m = next(x for x in reg["warehouse_mappings"] if x["source_instance"] == inst)
    return {"id": None, "reference_id": m["reference_id"], "revision": m["revision"], "phap_nhan_ma": m["phap_nhan_ma"]}


def doc_thuan(case, *, co_mapping=True):
    """Pipeline thuần của service: context máy chủ (không DB) → reader lần 1 → resolve facts → reader lần 2."""
    reg, mm = registry(), m5_demo.mau(case)
    inst = mm["source_instance"]
    rows, _, _ = KhoSoLuongK2._doc_master(mm["master"])
    tham = dict(inst=inst, profile=profile_cua(reg, inst), scope=scope_cua(reg, inst), coverage=mm["coverage"], errors=mm["reported_errors"],
                receipt_id=str(uuid.uuid4()), so_phieu="NK20260814001", mapping=mapping_cua(reg, inst) if co_mapping else None,
                master_ref=mm["master_reference_id"], master_sha=sha256(mm["master"]), master_rows=rows)
    lan1 = doc_phieu_kho(mm["native"], KhoSoLuongK2._boi_canh(None, **tham, facts=None))
    facts, ly_do = KhoSoLuongK2._giai_do_luong(facts_cua(reg, inst), sha256(mm["master"]), rows, lan1)
    kq = doc_phieu_kho(mm["native"], KhoSoLuongK2._boi_canh(None, **tham, facts=facts)) if facts else lan1
    return kq, facts, ly_do


class _HenGio:
    """Ủy quyền NGUYÊN SQL/tham số/kết quả cho kết nối thật (không mock quyền/kết quả); chỉ chèn MỘT hook thời điểm ngay trước statement đầu tiên
    chứa `mau` — dùng để tạo interleave thật với kết nối thứ hai (đột biến đã commit, hoặc giữ giao dịch của request thắng)."""

    def __init__(self, conn, mau, hook):
        self._c, self._mau, self._hook, self.da_chay = conn, mau, hook, False

    def execute(self, sql, params=None, **kw):
        if not self.da_chay and self._mau in str(sql):
            self.da_chay = True
            self._hook()
        return self._c.execute(sql, params, **kw)

    def __getattr__(self, ten):
        return getattr(self._c, ten)


class ThuanM5(unittest.TestCase):
    def test_registry_va_mau_dung_pin(self):
        reg = registry()
        self.assertEqual(len(reg["actors"]), 8)
        self.assertEqual(sorted(m5_demo.dang_nhap_m5()), sorted([M0A, M0B, KTA, KTB, CFOA, CFOB, VIEWA, M1A]))
        for p in reg["source_profiles"]:
            self.assertEqual(nguon_chung.digest_payload(p["payload"]), p["sha256"])
        mm = m5_demo.mau("K01")
        self.assertEqual((sha256(mm["native"]), sha256(mm["master"])), (GOLDEN["K01"]["raw_sha256"], "3a806526917dac322ee9ba4c6f7ea5ed88e02b780ea282c0300465e980e16801"))
        self.assertEqual((m5_demo.mau("K07")["coverage"], m5_demo.mau("K07")["reported_errors"]), ("PARTIAL", ["DETAIL_CAPTURE_INTERRUPTED_AFTER_FIRST_LINE"]))
        with self.assertRaises(DataError):
            m5_demo.mau("K99")

    def test_context_may_chu_va_facts_dung_dieu_kien(self):
        k01, f01, _ = doc_thuan("K01")
        self.assertIsNotNone(f01)
        self.assertEqual(k01.semantic_digest, GOLDEN["K01"]["semantic_digest"])
        self.assertIsNotNone(k01.request_digest)
        self.assertNotEqual(k01.request_digest, GOLDEN["K01"]["request_digest"])  # PN alias đã resolve + claim máy chủ: không là golden pure
        self.assertEqual([ln.normalized_quantity_text for ln in k01.lines], ["8", "2"])
        k02, f02, _ = doc_thuan("K02")
        self.assertEqual((f02["source_instance"], k02.semantic_digest), ("DEMO_KHO_B", GOLDEN["K02"]["semantic_digest"]))
        for case, ly in (("K08", "DO_LUONG_LOAI_TOKEN_KHAC"), ("K09", "DO_LUONG_MASTER_KHAC"), ("K10", "DO_LUONG_MASTER_KHAC")):
            with self.subTest(case=case):
                kq, facts, ly_do = doc_thuan(case)
                self.assertIsNone(facts)
                self.assertIn(ly, ly_do)
                self.assertEqual(kq.semantic_digest, GOLDEN[case]["semantic_digest"])
                self.assertIsNotNone(kq.request_digest)
                self.assertEqual({ln.normalized_quantity_text for ln in kq.lines}, {None})
        self.assertIn("KHO_UOM_UNKNOWN", {i.code for i in doc_thuan("K10")[0].issues})
        self.assertIsNone(doc_thuan("K06")[0].semantic_digest)
        k07, _, _ = doc_thuan("K07")
        self.assertEqual(k07.semantic_digest, GOLDEN["K07"]["semantic_digest"])
        self.assertIn("KHO_SOURCE_PARTIAL", {i.code for i in k07.issues})
        khong_map, _, _ = doc_thuan("K01", co_mapping=False)
        self.assertEqual((khong_map.semantic_digest, khong_map.request_digest), (GOLDEN["K01"]["semantic_digest"], None))

    def test_dong_nguon_giu_token_va_null(self):
        k08, _, _ = doc_thuan("K08")
        rows = [r for r in KhoSoLuongK2._dong_nguon_native(k08) if r["section"] == "GD_Dong"]
        self.assertEqual([(r["quantity_json_kind"], r["quantity_text"]) for r in rows],
                         [("NULL", None), ("NUMBER", "0"), ("NUMBER", "2.5"), ("NUMBER", "9007199254740992")])
        self.assertEqual({r["validation_state"] for r in KhoSoLuongK2._dong_nguon_native(doc_thuan("K06")[0]) if r["section"] == "GD_Dong"}, {"XUNG_DOT"})

    def test_master_sai_kieu_khong_vao_context(self):
        rows, nguon, loi = KhoSoLuongK2._doc_master(json.dumps({"DM_HangHoa": [{"MaHang": " X", "DVT_Goc": "CAI"}], "DM_Kho": [], "DM_DoiTac": []}).encode())
        self.assertEqual((rows, loi, nguon[0]["validation_state"]), (None, "MASTER_ROW_INVALID", "LOI"))
        self.assertEqual(KhoSoLuongK2._doc_master(None)[2], "ARTIFACT_ROLE_ABSENT")
        self.assertEqual(KhoSoLuongK2._doc_master(b"[1]")[2], "MASTER_SHAPE")

    def test_reported_errors_chat_va_coverage_hieu_luc(self):
        self.assertEqual(nguon_chung.kiem_ma_loi(), [])
        self.assertEqual(nguon_chung.kiem_ma_loi([]), [])
        self.assertEqual(nguon_chung.kiem_ma_loi(["A_B", "C1"]), ["A_B", "C1"])
        for xau in (None, False, 0, "AB", {"AB": 1}, [1], ["ab"], ["A B"], [None]):
            with self.subTest(xau=repr(xau)):
                with self.assertRaises(DataError) as cm:
                    nguon_chung.kiem_ma_loi(xau)
                self.assertEqual(cm.exception.code, "NGUON_MA_LOI")
        reg, mm = registry(), m5_demo.mau("K01")
        p = profile_cua(reg, "DEMO_KHO_A")
        du = nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"], "MASTER_RAW": mm["master"]})
        vang = nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"]})
        self.assertEqual(nguon_chung.coverage_hieu_luc(FULL, du, []), (FULL, []))
        self.assertEqual(nguon_chung.coverage_hieu_luc(FULL, vang, []), ("PARTIAL", ["ARTIFACT_ROLE_ABSENT_REQUIRED"]))  # claim gốc vẫn FULL trong H

    def test_capture_h_tach_va_on_dinh(self):
        reg, mm = registry(), m5_demo.mau("K01")
        p, s = profile_cua(reg, "DEMO_KHO_A"), scope_cua(reg, "DEMO_KHO_A")
        arts = nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"], "MASTER_RAW": mm["master"]})
        env = nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, [], arts)
        self.assertEqual(set(env), {"contract", "source_instance", "source_profile", "source_scope", "coverage", "reported_errors", "artifacts"})
        h = nguon_chung.bam_capture(env)
        self.assertEqual(h, nguon_chung.bam_capture(nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, nguon_chung.VANG, arts)))  # vắng ≡ []
        khac = [nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, "PARTIAL", [], arts),
                nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, ["X_LOI"], arts),
                nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, [],
                                             nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"], "MASTER_RAW": m5_demo.mau("K09")["master"]})),
                nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, [], nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"]}))]
        self.assertEqual(len({h} | {nguon_chung.bam_capture(e) for e in khac}), 5)
        self.assertEqual([a["role"] for a in khac[3]["artifacts"]], ["NATIVE_DETAIL"])
        with self.assertRaises(DataError):
            nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, "AB", arts)  # chuỗi không bị tách thành ['A','B']
        with self.assertRaises(DataError):
            nguon_chung.artifacts(p, {"KHAC": b"{}"})
        with self.assertRaises(DataError):
            nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, "TU_KHAI", [], arts)
        with self.assertRaises(DataError):
            nguon_chung.kiem_khoa("có dấu cách")

    def test_ma_tran_hanh_dong_m5(self):
        def dt(vai, module, duyet=()):
            return {"vai_tro": vai, "quyen": {"pn": {"ma": "PN", "module": list(module), "duyet": list(duyet)}}}
        self.assertTrue(quyen.duoc(dt("XEM", ["M5"]), "M5_READ", "pn"))
        self.assertFalse(quyen.duoc(dt("XEM", ["M5"]), "M5_FILE_SOAT", "pn"))
        self.assertTrue(quyen.duoc(dt("KE_TOAN", ["M5"]), "M5_FILE_SOAT", "pn"))
        self.assertFalse(quyen.duoc(dt("KE_TOAN", ["M5"]), "M5_SOURCE_REVIEW_V8", "pn"))
        self.assertFalse(quyen.duoc(dt("CFO", ["M5"], ["V4"]), "M5_SOURCE_REVIEW_V8", "pn"))
        self.assertTrue(quyen.duoc(dt("CFO", ["M5"], ["V4", "V8"]), "M5_SOURCE_REVIEW_V8", "pn"))
        self.assertFalse(quyen.duoc(dt("KE_TOAN", ["M1"]), "M5_READ", "pn"))
        with self.assertRaises(DataError):
            quyen.kiem_nguon(None, "A", "r", "s", "INTAKE", "pn")
        with self.assertRaises(DataError):
            quyen.kiem_nguon(None, "A", "r", "s", "SOURCE_MAP", None)

    def test_workbook_text_formula_safe(self):
        from openpyxl import load_workbook
        snap = {"phap_nhan": "PN_DEMO_A", "source_instance_id": "DEMO_KHO_A", "so_phieu": "=1+1", "ma_kho": "@KHO", "latest_observation_id": "o", "ky": "2026-08",
                "accepted_source_observation_id": None, "eligible_content_id": None,
                "noi_dung": [{"version": 1, "semantic_sha256": "a" * 64, "ngay_chung_tu": "2026-08-14", "trang_thai_raw": "+Đã duyệt", "trang_thai_nguon": "DA_DUYET",
                              "khoa_nguon_chieu": "KHO10_PHIEU:v1:" + "b" * 64, "chung_tu_id": "c",
                              "dong": [{"stt": 1, "id_dong": "-ID", "source_ordinal": 0, "ma_hang": "HH", "loai_so_luong": "NULL", "so_luong_nguon": None,
                                        "co_chuan_hoa": False, "do_chinh_xac": "UNKNOWN", "dvt_nguon": None, "don_vi": None, "chung_tu_dong_id": "d"},
                                       {"stt": 2, "id_dong": "ID2", "source_ordinal": 1, "ma_hang": "HH", "loai_so_luong": "NUMBER", "so_luong_nguon": "0",
                                        "co_chuan_hoa": False, "do_chinh_xac": "UNPROVEN", "dvt_nguon": "CAI", "don_vi": None, "chung_tu_dong_id": "e"}]}],
                "quan_sat": []}
        raw, so_dong = KhoSoLuongK2._workbook(snap)
        wb = load_workbook(io.BytesIO(raw), data_only=False)
        ws = wb["DONG_NGUON"]
        hang = [[c.value for c in r] for r in ws.iter_rows(min_row=2)]
        self.assertEqual(so_dong, 2)
        self.assertEqual((hang[0][6], hang[0][10], hang[0][11]), ("-ID", None, None))  # NULL ≠ 0, không tự điền
        self.assertEqual((hang[1][10], hang[1][11]), ("0", None))  # "0" là text nguồn; Number không chuẩn hóa
        self.assertTrue(all(c.data_type != "f" for r in ws.iter_rows() for c in r))
        self.assertEqual(wb["PHIEU"]["C2"].value, "=1+1")
        self.assertEqual(wb["PHIEU"]["C2"].data_type, "s")

    def test_workbook_co_so_provenance(self):
        from openpyxl import load_workbook
        co_so = {"contract": "m5-file-basis/v1", "mapping": {"id": "m1", "reference_id": "=MAP", "revision": 1, "state": "DA_DUYET", "dong": False},
                 "mapping_hien_hanh": [{"id": "m1"}], "noi_dung_chon": {"id": "v1", "semantic_sha256": "a" * 64, "master_raw_sha256": None},
                 "quan_sat_chon": {"id": "o1", "phan_loai": ["KHO_MEASUREMENT_UNRESOLVED", "+X"], "history_state": "KNOWN", "can_xem_xet": True},
                 "capture": {"id": "c1", "capture_sha256": "b" * 64, "coverage": "PARTIAL", "reported_errors": ["E1"], "bundle_sha256": "c" * 64,
                             "vai_tro": [{"vai_tro": "MASTER_RAW", "co_mat": False, "raw_sha256": None, "byte_length": None, "media_type": None,
                                          "ly_do_vang": "ARTIFACT_ROLE_ABSENT_REQUIRED"}]},
                 "master": None, "do_luong": [{"id": "f1", "declaration_ref": "D1", "payload_sha256": "d" * 64}], "du_dieu_kien_so_luong": False,
                 "ky": {"ky": "2026-08", "da_khoa": False}, "con_tro": {"latest": "o1", "accepted": "o1", "eligible": None},
                 "dong_nguon": [{"vai_tro": "NATIVE_DETAIL", "section": "GD_Dong", "locator": "/lines/0", "thu_tu": 0, "row_raw_sha256": "e" * 64,
                                 "quantity_json_kind": "NUMBER", "quantity_text": "-0", "validation_state": "LOI", "error_codes": ["KHO_FIELD_TYPE"]},
                                {"vai_tro": "NATIVE_DETAIL", "section": "GD_Dong", "locator": "/lines/1", "thu_tu": 1, "row_raw_sha256": "f" * 64,
                                 "quantity_json_kind": "NULL", "quantity_text": None, "validation_state": "HOP_LE", "error_codes": []}]}
        snap = {"phap_nhan": "PN_DEMO_A", "source_instance_id": "DEMO_KHO_A", "so_phieu": "S", "ma_kho": "K", "latest_observation_id": "o1", "ky": "2026-08",
                "accepted_source_observation_id": "o1", "eligible_content_id": None, "noi_dung": [], "quan_sat": [], "co_so": co_so, "co_so_sha256": "9" * 64}
        raw, _ = KhoSoLuongK2._workbook(snap)
        wb = load_workbook(io.BytesIO(raw), data_only=False)
        cs = {r[0].value: r[1].value for r in wb["CO_SO"].iter_rows(min_row=2)}
        self.assertEqual(cs["co_so_sha256"], "9" * 64)
        self.assertEqual((cs["mapping.reference_id"], cs["mapping.dong"], cs["noi_dung_chon.master_raw_sha256"]), ("=MAP", "FALSE", None))  # NULL trống
        self.assertEqual((cs["capture.coverage"], cs["capture.reported_errors"], cs["du_dieu_kien_so_luong"], cs["con_tro.eligible"]),
                         ("PARTIAL", "E1", "FALSE", None))
        self.assertIn("ly_do_vang=ARTIFACT_ROLE_ABSENT_REQUIRED", cs["capture.vai_tro.MASTER_RAW"])
        self.assertEqual(cs["do_luong.D1"], "id=f1;payload_sha256=" + "d" * 64)
        dn = [[c.value for c in r] for r in wb["DONG_NGUON_CAPTURE"].iter_rows(min_row=2)]
        self.assertEqual((dn[0][6], dn[0][7], dn[0][8]), ("-0", "LOI", "KHO_FIELD_TYPE"))  # raw token nguyên văn, lỗi giữ
        self.assertEqual((dn[1][5], dn[1][6]), ("NULL", None))  # NULL ≠ 0
        for ws in wb.worksheets:
            self.assertTrue(all(c.data_type != "f" for r in ws.iter_rows() for c in r), ws.title)

    def test_kiem_ket_noi_chu_tuple_va_dict_row(self):
        """SR02-0: validator đọc theo TÊN cột (alias duy nhất) cho cả tuple và dict_row; sai chủ/cột gộp/khác đích → lỗi rõ, không IndexError."""
        from kho_tri_thuc.k2.crm_khoi_dong import kiem_ket_noi_chu

        class Res:
            def __init__(self, row):
                self.row = row

            def fetchone(self):
                return self.row

        class Conn:
            def __init__(self, dich, chu):
                self.dich, self.chu, self.sql = dich, chu, []

            def execute(self, sql, params=None):
                self.sql.append(sql)
                return Res(self.dich if "inet_server_addr" in sql else self.chu)

        dich_t, dich_d = ("127.0.0.1", 5432, 99, "kho_demo"), {"dia_chi": "127.0.0.1", "cong": 5432, "db_oid": 99, "db": "kho_demo"}
        app = Conn(dich_d, None)
        dung_t = ("chu_db", "chu_db", "chu_db", "chu_db")
        dung_d = {"hien_tai": "chu_db", "chu_stage": "chu_db", "chu_phieu": "chu_db", "chu_lo": "chu_db"}
        self.assertEqual(kiem_ket_noi_chu(Conn(dich_t, dung_t), app), {"chu": "chu_db"})
        c = Conn(dich_d, dung_d)
        self.assertEqual(kiem_ket_noi_chu(c, app), {"chu": "chu_db"})
        for alias in ("AS hien_tai", "AS chu_stage", "AS chu_phieu", "AS chu_lo"):
            self.assertIn(alias, c.sql[-1])
        sai = [("Conn tuple sai chủ", Conn(dich_t, ("app_role", "chu_db", "chu_db", "chu_db"))),
               ("dict sai chủ một bảng", Conn(dich_d, {**dung_d, "chu_lo": "khac"})),
               ("dict cột gộp kiểu cũ", Conn(dich_d, {"current_user": "chu_db", "pg_get_userbyid": "chu_db"})),
               ("tuple thiếu cột", Conn(dich_t, ("chu_db", "chu_db"))),
               ("hien_tai NULL", Conn(dich_d, {"hien_tai": None, "chu_stage": None, "chu_phieu": None, "chu_lo": None}))]
        for ten, conn in sai:
            with self.subTest(ten=ten):
                with self.assertRaises(DataError) as cm:
                    kiem_ket_noi_chu(conn, app)
                self.assertEqual(cm.exception.code, "KET_NOI_CHU_SAI")
        with self.assertRaises(DataError) as cm:
            kiem_ket_noi_chu(Conn(("127.0.0.1", 5433, 99, "kho_demo"), dung_t), app)
        self.assertEqual(cm.exception.code, "KET_NOI_KHAC_DB")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL M5 không chạy (không tính đạt)")
class M5K2Pg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.k2 import crm_demo
        from kho_tri_thuc.k2.crm_khoi_dong import kiem_ket_noi_chu
        cls.db = "kho_test_m5_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        cls.seed1 = m5_demo.khoi_tao(cls.admin)
        cls.seed2 = m5_demo.khoi_tao(cls.admin)
        cls.tao_sentinel()
        cls.role, pw = "ktt_test_m5_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        opts = "-c lock_timeout=20000 -c statement_timeout=60000"
        cls.app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.app2 = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.chu2 = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.chu_info = kiem_ket_noi_chu(cls.chu, cls.app)
        cls.root = Path(tempfile.mkdtemp(prefix="ktt_m5_k2_"))
        cls.m5 = KhoSoLuongK2(cls.app, cls.root, conn_chu=cls.chu)
        cls.m5b = KhoSoLuongK2(cls.app2, cls.root, conn_chu=cls.chu2)
        cls.state = {}
        cls.nen = cls.sentinel_snapshot()

    @classmethod
    def tearDownClass(cls):
        for c in (cls.app, cls.app2, cls.chu, cls.chu2, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng

    @classmethod
    def q(cls, sql, params=()):
        return cls.admin.execute(sql, params).fetchone()[0]

    @classmethod
    def tao_sentinel(cls):
        """Hàng non-M5 không rỗng (HD_MUA/HD_BAN/SAO_KE-BANK/công nợ mở/đề xuất 331/liên kết) — phải giữ nguyên tuyệt đối sau mọi thao tác M5."""
        a = cls.admin
        pn = cls.q("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")
        ids = {}
        for loai, khoa, tien, chieu in (("HD_MUA", "SENT-HDMUA", 1100, None), ("HD_BAN", "SENT-HDBAN", 2200, None), ("SAO_KE", "SENT-BANK", 3300, "THU")):
            ids[loai] = a.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, chieu, hash)
                                     VALUES (%s,%s,%s,'2026-08-01','VND',%s,%s,%s) RETURNING id""", (pn, loai, khoa, tien, chieu, "1" * 64)).fetchone()[0]
        a.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, so_luong, no_minor, co_minor) VALUES (%s,1,'sentinel',10,1100,0)", (ids["HD_MUA"],))
        x = a.execute("INSERT INTO kho.de_xuat (chung_tu_id, phien_ban, muc) VALUES (%s,1,'VANG') RETURNING id", (ids["HD_MUA"],)).fetchone()[0]
        a.execute("""INSERT INTO kho.de_xuat_dong (de_xuat_id, "offset", no_co, acct_id, base_crd) VALUES (%s,1,'C','331',1100)""", (x,))
        a.execute("INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'KHAC')", (pn, ids["SAO_KE"], ids["HD_BAN"]))
        a.execute("""INSERT INTO kho.cong_no_mo (phap_nhan_id, ngay_chup, tai_khoan, item_key, loai, so_tien_minor) VALUES (%s,'2026-08-01','331','SENT-CN','INVOICE',1100)""",
                  (pn,))

    @classmethod
    def sentinel_snapshot(cls):
        out = {}
        for ten, sql in (("chung_tu", "SELECT to_jsonb(x)::text FROM kho.chung_tu x WHERE x.module_nghiep_vu <> 'M5' ORDER BY x.id"),
                         ("chung_tu_dong", """SELECT to_jsonb(x)::text FROM kho.chung_tu_dong x JOIN kho.chung_tu c ON c.id = x.chung_tu_id
                                              WHERE c.module_nghiep_vu <> 'M5' ORDER BY x.id"""),
                         ("de_xuat", "SELECT to_jsonb(x)::text FROM kho.de_xuat x ORDER BY x.id"),
                         ("de_xuat_dong", "SELECT to_jsonb(x)::text FROM kho.de_xuat_dong x ORDER BY x.id"),
                         ("lien_ket", "SELECT to_jsonb(x)::text FROM kho.lien_ket_chung_tu x ORDER BY x.id"),
                         ("cong_no_mo", "SELECT to_jsonb(x)::text FROM kho.cong_no_mo x ORDER BY x.id"),
                         ("hop_dong", "SELECT to_jsonb(x)::text FROM master.hop_dong x ORDER BY x.id"),
                         ("lo_khac", "SELECT to_jsonb(x)::text FROM kho.lo_xuat x WHERE coalesce(x.du_lieu->>'module','') <> 'M5' ORDER BY x.id"),
                         ("bien_nhan_khac", "SELECT to_jsonb(x)::text FROM kho.bien_nhan_thao_tac x WHERE x.module <> 'M5' ORDER BY x.id")):
            out[ten] = [r[0] for r in cls.admin.execute(sql)]
        return out

    @classmethod
    def counts(cls):
        return {t: cls.q(f"SELECT count(*) FROM {t}") for t in ("giao_tiep.stage_tin_cay", "giao_tiep.tep_tiep_nhan", "giao_tiep.lan_tiep_nhan_nguon",
                                                                "kho.anh_chup_nguon", "kho.ban_ghi_nguon", "kho.phieu_kho_danh_tinh", "kho.phieu_kho_phien_ban",
                                                                "kho.phieu_kho_quan_sat", "kho.phieu_kho_dong_danh_tinh", "kho.phieu_kho_dong_phien_ban",
                                                                "kho.bien_nhan_thao_tac", "kho.lo_xuat", "giao_tiep.ket_qua_cuoi_tiep_nhan")} | {
            "core_m5": cls.q("SELECT count(*) FROM kho.chung_tu WHERE module_nghiep_vu = 'M5'"),
            "core_dong_m5": cls.q("SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M5'")}

    def nhan(self, actor, case, khoa=None, svc=None, **sua):
        mm = m5_demo.mau(case)
        # phạm vi cấu hình của registry đã pin (tường minh): t18d thêm một phạm vi sibling trong DB test nên không dựa vào "duy nhất một phạm vi"
        tham = dict(source_instance=mm["source_instance"], scope_ref=scope_cua(registry(), mm["source_instance"])["scope_ref"], coverage=mm["coverage"],
                    reported_errors=mm["reported_errors"],
                    client_key=khoa or "k-" + uuid.uuid4().hex[:12], native=mm["native"], master=mm["master"])
        tham.update(sua)
        return (svc or self.m5).nhan(actor, **tham)

    def raises(self, code, fn):
        with self.assertRaises((DataError, psycopg.Error)) as ctx:
            fn()
        self.assertIn(code, (getattr(ctx.exception, "code", "") or "") + " " + str(ctx.exception))

    def sql(self, login, sql, params=(), *, id_cua=None):
        nd = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (id_cua or login,))
        with self.app.transaction():
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, login))
            cur = self.app.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount

    def phieu_a(self):
        return self.q("SELECT id::text FROM kho.phieu_kho_danh_tinh WHERE source_instance_id = 'DEMO_KHO_A' AND so_phieu_key = 'NK20260814001'")

    def con_tro(self, pid):
        return self.m5.chi_tiet(CFOA, pid)["con_tro"]

    def obs_cua(self, receipt):
        return self.q("SELECT id::text FROM kho.phieu_kho_quan_sat WHERE lan_tiep_nhan_id = %s", (receipt,))

    def files_xuat(self):
        d = self.root / "m5-xuat"
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []

    def body_file(self, actor, pid, khoa):
        ct = self.m5.chi_tiet(actor, pid)
        return {"phieu_id": pid, "khoa": khoa, "latest_truoc": ct["con_tro"]["latest_observation_id"],
                "accepted_truoc": ct["con_tro"]["accepted_source_observation_id"], "eligible_truoc": ct["con_tro"]["eligible_content_id"],
                "co_so_truoc": ct["co_so_file"]["co_so_sha256"]}

    def cho_advisory(self, pid_backend, giay=30.0):
        """Observer nhân quả: backend đích ĐANG CHỜ một advisory lock (pg_locks granted = false). Hết giờ → False (không tính đạt)."""
        het = time.monotonic() + giay
        while time.monotonic() < het:
            if self.q("SELECT count(*) FROM pg_locks WHERE pid = %s AND locktype = 'advisory' AND NOT granted", (pid_backend,)) > 0:
                return True
            time.sleep(0.05)
        return False

    def review(self, actor, obs, qd="CHAP_NHAN_NGUON", khoa=None, **sua):
        pid = self.phieu_a()
        ct = self.con_tro(pid)
        body = {"phieu_id": pid, "observation_id": obs, "quyet_dinh": qd, "accepted_truoc": ct["accepted_source_observation_id"],
                "eligible_truoc": ct["eligible_content_id"], "latest_truoc": ct["latest_observation_id"], "ly_do": "DEMO review", "khoa": khoa or "r-" + uuid.uuid4().hex[:10]}
        body.update(sua)
        return self.m5.kiem_lai_nguon(actor, body)

    # ------------------------------------------------------------------ seed + K01 / core / retry / 409 / quyền nguồn
    def test_t01_seed_mot_lan_khong_m9(self):
        self.assertEqual({k: v for k, v in self.seed2.items() if k != "mo_lai_giu_quyen_hien_hanh"}, {k: 0 for k in self.seed2 if k != "mo_lai_giu_quyen_hien_hanh"})
        self.assertTrue(self.seed2["mo_lai_giu_quyen_hien_hanh"])
        self.assertEqual((self.seed1["actor"], self.seed1["nang_luc"]), (8, 6))
        self.assertEqual(self.q("""SELECT count(*) FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id WHERE n.mo_phong
                                   AND 'M9' = ANY (q.module)"""), 0)  # seed ban đầu không cấp M9 cho bất kỳ actor DEMO nào
        self.assertEqual(self.chu_info["chu"], self.q("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = 'kho.phieu_kho_danh_tinh'::regclass"))
        # SR02-0: cùng validator trên kết nối chủ dạng tuple (dương) và trên login ứng dụng giả làm chủ (âm, không IndexError)
        from kho_tri_thuc.k2.crm_khoi_dong import kiem_ket_noi_chu
        with psycopg.connect(self.dsn, autocommit=True) as tuple_chu:
            self.assertEqual(kiem_ket_noi_chu(tuple_chu, self.app), self.chu_info)
        with self.assertRaises(DataError) as cm:
            kiem_ket_noi_chu(self.app2, self.app)
        self.assertEqual(cm.exception.code, "KET_NOI_CHU_SAI")

    def test_t02_k01_nhan_promote_typed_va_core_quantity_only(self):
        r = self.nhan(M0A, "K01", "k01")
        self.state["k01"] = r
        self.assertEqual((r["lap_lai"], r["semantic_digest"], r["giu_cho"], r["coverage_hieu_luc"]), (False, GOLDEN["K01"]["semantic_digest"], [], FULL))
        self.assertEqual((r["promote"]["trang_thai"], r["promote"]["phan_loai"]), ("DA_GHI_QUAN_SAT", ["FIRST_OBSERVATION_CANDIDATE"]))
        ct = self.m5.chi_tiet(KTA, r["promote"]["phieu_id"])
        self.assertEqual([(l["so_luong_nguon"], l["so_luong_chuan_hoa"], l["don_vi"]) for l in ct["noi_dung"][0]["dong"]],
                         [("8", "8", "DEMO_UNIT_CAI_A"), ("2", "2", "DEMO_UNIT_CAI_A")])
        core = self.admin.execute("""SELECT c.loai, c.module_nghiep_vu, c.so_tien_minor, c.tien_te, c.chieu, c.trang_thai, c.ngay_nghiep_vu::text, c.khoa_nguon
                                     FROM kho.chung_tu c JOIN kho.phieu_kho_phien_ban v ON v.chung_tu_id = c.id AND v.phap_nhan_id = c.phap_nhan_id
                                     WHERE v.id = %s""", (ct["noi_dung"][0]["id"],)).fetchone()
        self.assertEqual(core[:7], ("PHIEU_KHO", "M5", None, None, None, "DANG_XU_LY", "2026-08-14"))
        self.assertEqual(core[7], ct["noi_dung"][0]["khoa_nguon_chieu"])
        dong = self.admin.execute("""SELECT d.stt, d.so_luong::text, d.no_minor, d.co_minor, d.don_gia_minor, d.tai_khoan FROM kho.chung_tu_dong d
                                     JOIN kho.phieu_kho_dong_phien_ban lv ON lv.chung_tu_dong_id = d.id WHERE lv.phien_ban_id = %s ORDER BY d.stt""",
                                  (ct["noi_dung"][0]["id"],)).fetchall()
        self.assertEqual([(s, q[:1], n, c, g, t) for s, q, n, c, g, t in dong], [(1, "8", None, None, None, None), (2, "2", None, None, None, None)])
        _, raw = self.m5.nguon_raw(M0A, r["lan_tiep_nhan_id"], "NATIVE_DETAIL")
        self.assertEqual(raw, m5_demo.mau("K01")["native"])
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.m5.nguon_raw(KTA, r["lan_tiep_nhan_id"], "NATIVE_DETAIL"))

    def test_t03_cung_khoa_cung_h_0_delta_khac_h_409_truoc_stage_va_blob(self):
        truoc, blobs = self.counts(), sorted(p.name for p in (self.root / "m0-raw").iterdir())
        r = self.nhan(M0A, "K01", "k01")
        self.assertEqual((r["lap_lai"], r["lan_tiep_nhan_id"]), (True, self.state["k01"]["lan_tiep_nhan_id"]))
        # SR02-1: replay trả ĐÚNG kết quả cuối đã chốt (refs/trạng thái), không chỉ receipt ID
        dau = self.state["k01"]
        for k in ("promote", "stage_id", "snapshot_moi", "capture_sha256", "semantic_digest", "request_digest", "giu_cho", "coverage_hieu_luc"):
            self.assertEqual(r[k], dau[k], k)
        self.assertEqual((r["promote"]["phieu_id"], r["promote"]["observation_id"], r["promote"]["content_id"]),
                         (dau["promote"]["phieu_id"], dau["promote"]["observation_id"], dau["promote"]["content_id"]))
        for sua in ({"native": m5_demo.mau("K04")["native"]}, {"master": m5_demo.mau("K09")["master"]}, {"master": None}, {"coverage": "PARTIAL"},
                    {"reported_errors": ["LOI_MOI"]}):
            with self.subTest(sua=list(sua)):
                self.raises("CAPTURE_KHAC_NOI_DUNG", lambda: self.nhan(M0A, "K01", "k01", **sua))
        for xau in (None, "AB", {"A": 1}, False):
            with self.subTest(errors=repr(xau)):
                self.raises("NGUON_MA_LOI", lambda: self.nhan(M0A, "K01", "k01", reported_errors=xau))
        self.assertEqual((self.counts(), sorted(p.name for p in (self.root / "m0-raw").iterdir())), (truoc, blobs))

    def test_t04_quyen_nguon_truoc_tra_cuu(self):
        truoc = self.counts()
        for actor in (KTA, M0B, CFOA, VIEWA, M1A):
            with self.subTest(actor=actor):
                self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.nhan(actor, "K01", "k01"))  # khóa đã có cũng không lộ biên nhận
        self.assertEqual(self.counts(), truoc)
        self.raises("KHONG_CO_QUYEN_MODULE", lambda: self.m5.danh_sach(M0A))
        self.assertEqual(len(self.m5.nguon_danh_sach(M0A)), 1)
        self.assertEqual(self.m5.nguon_danh_sach(KTA), [])

    def test_t05_ma_tran_doc_va_core_khong_lot_m1(self):
        pid = self.phieu_a()
        self.assertEqual([p["id"] for p in self.m5.danh_sach(KTA)["phieu"]], [pid])
        self.assertEqual([p["id"] for p in self.m5.danh_sach(VIEWA)["phieu"]], [pid])
        self.assertEqual(self.m5.danh_sach(KTB)["phieu"], [])
        self.raises("KHONG_CO_QUYEN_MODULE", lambda: self.m5.danh_sach(M1A))
        self.raises("PHIEU_KHO", lambda: self.m5.chi_tiet(KTB, pid))
        self.assertEqual(self.sql(M1A, "SELECT count(*) AS n FROM kho.chung_tu WHERE module_nghiep_vu = 'M5'")[0]["n"], 0)
        self.assertEqual(self.sql(M1A, """SELECT count(*) AS n FROM kho.chung_tu_dong d WHERE d.chung_tu_id IN
                                           (SELECT v.chung_tu_id FROM kho.phieu_kho_phien_ban v)""")[0]["n"], 0)
        self.assertGreater(self.sql(KTA, "SELECT count(*) AS n FROM kho.chung_tu WHERE module_nghiep_vu = 'M5'")[0]["n"], 0)
        self.assertGreater(self.sql(M1A, "SELECT count(*) AS n FROM kho.chung_tu WHERE khoa_nguon LIKE 'SENT-%%'")[0]["n"], 0)  # M1 vẫn thấy hàng M1 cũ

    # ------------------------------------------------------------------ review V8 (latest-only), fresh, ABA
    def test_t06_review_tren_quan_sat_moi_nhat(self):
        obs1 = self.obs_cua(self.state["k01"]["lan_tiep_nhan_id"])
        pid = self.phieu_a()
        truoc = self.con_tro(pid)
        self.assertEqual(truoc["latest_observation_id"], obs1)
        body = {"phieu_id": pid, "observation_id": obs1, "quyet_dinh": "CHAP_NHAN_NGUON", "accepted_truoc": None, "eligible_truoc": None,
                "latest_truoc": obs1, "ly_do": "DEMO review", "khoa": "rv-a"}
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.m5.kiem_lai_nguon(KTA, body))
        self.raises("PHIEU_KHO", lambda: self.m5.kiem_lai_nguon(CFOB, body))
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.kiem_lai_nguon(CFOA, {**body, "latest_truoc": None, "khoa": "rv-cu"}))
        r = self.m5.kiem_lai_nguon(CFOA, body)
        ct = self.con_tro(pid)
        self.assertEqual((r["lap_lai"], ct["accepted_source_observation_id"]), (False, obs1))
        self.assertIsNotNone(ct["eligible_content_id"])  # K01 exact: positive eligible UUID
        self.assertTrue(self.q("SELECT kho.m5_quan_sat_du_dieu_kien(%s::uuid)", (obs1,)))
        lai = self.m5.kiem_lai_nguon(CFOA, body)
        self.assertEqual((lai["lap_lai"], self.con_tro(pid)), (True, ct))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m5.kiem_lai_nguon(CFOA, {**body, "ly_do": "khác"}))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.m5.kiem_lai_nguon(KTA, body))  # quyền trước replay: KT không thấy kết quả cũ

    def test_t07_khoa_moi_cung_bytes_la_fresh_khong_core_moi(self):
        truoc = self.counts()
        r = self.nhan(M0A, "K03", "k03")
        self.state["k03"] = r
        sau = self.counts()
        self.assertEqual((r["lap_lai"], r["snapshot_moi"]), (False, False))
        self.assertIn("SAME_CONTENT_FRESH_OBSERVATION", r["promote"]["phan_loai"])
        self.assertEqual({k: sau[k] - truoc[k] for k in ("giao_tiep.lan_tiep_nhan_nguon", "giao_tiep.stage_tin_cay", "kho.anh_chup_nguon",
                                                         "giao_tiep.tep_tiep_nhan", "kho.phieu_kho_phien_ban", "kho.phieu_kho_quan_sat", "core_m5", "core_dong_m5")},
                         {"giao_tiep.lan_tiep_nhan_nguon": 1, "giao_tiep.stage_tin_cay": 1, "kho.anh_chup_nguon": 0, "giao_tiep.tep_tiep_nhan": 0,
                          "kho.phieu_kho_phien_ban": 0, "kho.phieu_kho_quan_sat": 1, "core_m5": 0, "core_dong_m5": 0})

    def test_t08_stale_a_cu_khong_duoc_chap_nhan_lai(self):
        obs1 = self.obs_cua(self.state["k01"]["lan_tiep_nhan_id"])
        truoc = self.con_tro(self.phieu_a())
        self.raises("KHO_SOURCE_REAPPROVAL_REVIEW", lambda: self.review(CFOA, obs1))  # quan sát cũ, expected đúng hiện hành → vẫn âm
        self.assertEqual(self.con_tro(self.phieu_a()), truoc)

    def test_t09_dao_b_roi_a_cu_reappearance(self):
        pid = self.phieu_a()
        core_truoc = self.counts()["core_m5"]
        r4 = self.nhan(M0A, "K04", "k04")
        self.assertIn("REVERSED", r4["promote"]["phan_loai"])
        self.assertIsNone(self.con_tro(pid)["eligible_content_id"])
        self.assertEqual(self.counts()["core_m5"], core_truoc + 1)
        obs4 = self.obs_cua(r4["lan_tiep_nhan_id"])
        self.review(CFOA, obs4)
        ct = self.con_tro(pid)
        self.assertEqual((ct["accepted_source_observation_id"], ct["eligible_content_id"]), (obs4, None))
        r5 = self.nhan(M0A, "K05", "k05")
        self.assertIn("REAPPEARANCE_HOLD", r5["promote"]["phan_loai"])
        ct2 = self.con_tro(pid)
        self.assertEqual((ct2["accepted_source_observation_id"], ct2["eligible_content_id"]), (obs4, None))
        self.raises("KHO_SOURCE_REAPPROVAL_REVIEW", lambda: self.review(CFOA, self.obs_cua(r5["lan_tiep_nhan_id"])))
        self.raises("KHO_SOURCE_REAPPROVAL_REVIEW", lambda: self.review(CFOA, self.obs_cua(self.state["k01"]["lan_tiep_nhan_id"])))
        self.assertEqual(self.counts()["core_m5"], core_truoc + 1)  # A cũ dùng lại content/core cũ, không core mới
        self.assertEqual(self.q("SELECT count(*) FROM kho.phieu_kho_danh_tinh"), 1)

    def test_t10_k02_instance_b_tach_pn(self):
        r = self.nhan(M0B, "K02", "k02")
        self.assertEqual((r["semantic_digest"], r["phap_nhan"]), (GOLDEN["K02"]["semantic_digest"], "PN_DEMO_B"))
        self.assertEqual([p["nguon"] for p in self.m5.danh_sach(KTB)["phieu"]], ["DEMO_KHO_B"])
        self.assertNotIn("DEMO_KHO_B", {p["nguon"] for p in self.m5.danh_sach(KTA)["phieu"]})

    def test_t11_k06_trung_id_giu_ung_vien(self):
        truoc = self.counts()
        r = self.nhan(M0A, "K06", "k06")
        self.assertEqual((r["semantic_digest"], r["promote"]["trang_thai"]), (None, "GIU_CHO_UNG_VIEN"))
        sau = self.counts()
        self.assertEqual({k: sau[k] - truoc[k] for k in ("kho.phieu_kho_quan_sat", "core_m5", "giao_tiep.lan_tiep_nhan_nguon")},
                         {"kho.phieu_kho_quan_sat": 0, "core_m5": 0, "giao_tiep.lan_tiep_nhan_nguon": 1})

    def dong_logic(self, pid, pn_ma):
        """Tập logical line IDs của ĐÚNG một phiếu (phieu_id + PN) — không đếm prefix toàn bảng (A và B cố ý dùng cùng native line IDs)."""
        return [r[0] for r in self.admin.execute("""SELECT d.id_dong_nguon FROM kho.phieu_kho_dong_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                                                    WHERE d.phieu_id = %s AND p.ma = %s ORDER BY d.id_dong_nguon""", (pid, pn_ma))]

    def test_t12_k07_partial_khong_xoa_dong(self):
        pid = self.phieu_a()
        pid_b = self.q("SELECT id::text FROM kho.phieu_kho_danh_tinh WHERE source_instance_id = 'DEMO_KHO_B'")
        truoc_a, truoc_b = self.dong_logic(pid, "PN_DEMO_A"), self.dong_logic(pid_b, "PN_DEMO_B")
        b_rows = self.q("SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id)::text FROM kho.phieu_kho_dong_danh_tinh d WHERE d.phieu_id = %s", (pid_b,))
        self.assertGreaterEqual(len(truoc_a), 2)
        r = self.nhan(M0A, "K07", "k07")
        self.assertIn("KHO_SOURCE_PARTIAL", r["promote"]["phan_loai"])
        self.assertEqual(r["promote"]["trang_thai"], "DA_GHI_QUAN_SAT")
        sau_a = self.dong_logic(pid, "PN_DEMO_A")
        self.assertEqual(sau_a, truoc_a)  # partial không xóa dòng thiếu, không clone thêm danh tính dòng
        self.assertEqual(len(sau_a), len(set(sau_a)))
        partial = [r0[0] for r0 in self.admin.execute("""SELECT dd.id_dong_nguon FROM kho.phieu_kho_dong_phien_ban lv JOIN kho.phieu_kho_dong_danh_tinh dd
                                                          ON dd.id = lv.dong_id WHERE lv.phien_ban_id = %s""", (r["promote"]["content_id"],))]
        self.assertTrue(set(partial) < set(truoc_a), (partial, truoc_a))  # nội dung partial chỉ có dòng đã nhận; dòng thiếu vẫn là danh tính của phiếu
        self.assertEqual((self.dong_logic(pid_b, "PN_DEMO_B"), self.q("SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id)::text FROM kho.phieu_kho_dong_danh_tinh d "
                                                                      "WHERE d.phieu_id = %s", (pid_b,))), (truoc_b, b_rows))  # instance B nguyên

    def test_t13_k08_null_khac_0_number_unproven_core_null(self):
        self.nhan(M0A, "K08", "k08")
        v = next(x for x in self.m5.chi_tiet(KTA, self.phieu_a())["noi_dung"] if x["semantic_sha256"] == GOLDEN["K08"]["semantic_digest"])
        self.assertEqual([(l["loai_so_luong"], l["so_luong_nguon"], l["so_luong_chuan_hoa"], l["do_chinh_xac"]) for l in v["dong"]],
                         [("NULL", None, None, "UNKNOWN"), ("NUMBER", "0", None, "UNPROVEN"), ("NUMBER", "2.5", None, "UNPROVEN"),
                          ("NUMBER", "9007199254740992", None, "UNPROVEN")])
        self.assertEqual({r[0] for r in self.admin.execute("""SELECT d.so_luong FROM kho.chung_tu_dong d JOIN kho.phieu_kho_dong_phien_ban lv
                                                               ON lv.chung_tu_dong_id = d.id WHERE lv.phien_ban_id = %s""", (v["id"],))}, {None})
        self.chap_nhan_khong_eligible("K08")

    def chap_nhan_khong_eligible(self, case):
        """I-M05: quan sát mới nhất của nguồn Đã duyệt + lịch sử KNOWN, không mang mã chặn chấp nhận → CFO chấp nhận được (accepted = obs)
        nhưng eligible PHẢI NULL vì proof/UOM/precision chưa exact (cổng số lượng ở CSDL)."""
        pid = self.phieu_a()
        obs = self.con_tro(pid)["latest_observation_id"]
        o = self.admin.execute("SELECT trang_thai_nguon, history_state, phan_loai FROM kho.phieu_kho_quan_sat WHERE id = %s", (obs,)).fetchone()
        self.assertEqual((o[0], o[1]), ("DA_DUYET", "KNOWN"), case)
        chan = set(o[2]) & {"REAPPEARANCE_HOLD", "KHO_RECEIPT_CONFLICT", "HISTORY_UNAVAILABLE", "HISTORY_UNBOUND", "HISTORY_MISMATCH", "KHO_SOURCE_PARTIAL",
                            "KHO_CONTEXT_UNRESOLVED", "KHO_CONTEXT_SCOPE_MISMATCH", "KHO_CONTEXT_PROOF_MISMATCH"}
        self.assertFalse(chan, f"{case}: quan sát mang mã chặn chấp nhận {chan} — không phải ca accepted-but-noneligible")
        r = self.review(CFOA, obs)
        ct = self.con_tro(pid)
        self.assertEqual((r["accepted_source_observation_id"], ct["accepted_source_observation_id"], ct["eligible_content_id"]), (obs, obs, None), case)
        self.assertFalse(self.q("SELECT kho.m5_quan_sat_du_dieu_kien(%s::uuid)", (obs,)), case)

    def test_t14_k09_k10_uom(self):
        self.assertFalse(self.nhan(M0A, "K09", "k09")["do_luong"]["da_giai"])
        self.chap_nhan_khong_eligible("K09")
        self.assertIn("KHO_UOM_UNKNOWN", self.nhan(M0A, "K10", "k10")["reader_issues"])
        self.chap_nhan_khong_eligible("K10")
        # trực tiếp bằng chủ bảng cũng không đặt được eligible cho quan sát không đủ căn cứ (trigger con trỏ dùng cùng cổng)
        pid = self.phieu_a()
        v = self.q("""SELECT o.content_id::text FROM kho.phieu_kho_danh_tinh d JOIN kho.phieu_kho_quan_sat o ON o.id = d.accepted_source_observation_id
                      WHERE d.id = %s""", (pid,))
        self.raises("CON_TRO_ELIGIBLE_SAI", lambda: self.admin.execute("UPDATE kho.phieu_kho_danh_tinh SET eligible_content_id = %s::uuid WHERE id = %s::uuid",
                                                                       (v, pid)))

    # ------------------------------------------------------------------ forgery/direct SQL + consume stage hợp lệ của chủ
    def _stage_hop_le(self, khoa):
        """Chủ bảng (máy chủ) dựng stage CAPTURE hợp lệ cho M0A từ bytes thật, commit; không tiêu thụ."""
        reg, mm = registry(), m5_demo.mau("K01")
        p, s = profile_cua(reg, "DEMO_KHO_A"), scope_cua(reg, "DEMO_KHO_A")
        arts = nguon_chung.artifacts(p, {"NATIVE_DETAIL": mm["native"], "MASTER_RAW": mm["master"]})
        env = nguon_chung.phong_bi_capture("DEMO_KHO_A", p, s, FULL, [], arts)
        h = nguon_chung.bam_capture(env)
        kq = doc_thuan("K01")[0]
        rows = KhoSoLuongK2._dong_nguon_native(kq) + KhoSoLuongK2._doc_master(mm["master"])[1]
        du = nguon_chung.du_lieu_stage_capture(receipt_id=str(uuid.uuid4()), scope=s, coverage=FULL, coverage_hl=FULL, envelope=env, arts=arts, rows=rows,
                                               ket_qua={"ghi_chu": "stage-test"}, promote=None)
        dt = self.m5.danh_tinh(M0A)
        with self.m5._tx_chu(dt) as c:
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="CAPTURE", client_key=khoa, h=h, source_instance="DEMO_KHO_A", profile_ref=p["reference_id"],
                                          profile_sha256=p["sha256"], du_lieu=du)
        return stage, h

    def test_t15_forgery_bi_chan_va_consume_stage_hop_le(self):
        pid = self.phieu_a()
        pn = self.q("SELECT id::text FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")
        sha_raw = self.state["k01"]["raw_sha256"]
        for login, sql, params, ma in (
                (M0A, "INSERT INTO giao_tiep.stage_tin_cay (muc_dich, client_key, h, actor_id, actor, source_instance_id, profile_ref, profile_sha256, du_lieu) "
                      "SELECT 'CAPTURE','x',%s,id,dang_nhap,'DEMO_KHO_A','r','s','{}' FROM master.nguoi_dung WHERE dang_nhap = %s", ("0" * 64, M0A), "permission denied"),
                (M0A, "SELECT * FROM giao_tiep.nguon_tieu_thu_capture(gen_random_uuid(), %s)", ("0" * 64,), "STAGE_KHONG_HOP_LE"),
                (M0A, "SELECT kho.m5_tieu_thu_quan_sat(gen_random_uuid(), %s)", ("0" * 64,), "STAGE_KHONG_HOP_LE"),
                (CFOA, "INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                       "VALUES (%s,'M5','SOURCE_REVIEW_V8','prefill',%s,'{}',%s)", (pn, "0" * 64, CFOA), "BIEN_NHAN_M5_CHI_CHU"),
                (KTA, "INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, duong_dan, hash, nguoi, du_lieu) VALUES (%s,'2026-08','FORGE','FILE_SOAT',%s,%s,%s,%s)",
                 (pn, f"m0-raw/{sha_raw}", sha_raw, KTA, json.dumps({"module": "M5", "muc_dich": "FILE_SOAT", "ten": "x"})), "LO_M5_CHI_CHU"),
                (KTA, "INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'PHIEU_KHO','FORGE','2026-08-14',%s)",
                 (pn, "0" * 64), "CHUNG_TU_M5_CHI_CHU"),
                (CFOA, "INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, phap_nhan_id, "
                       "valid_from, nguon_quyet_dinh, duyet_boi) SELECT 'F', 9, source_instance_id, profile_ref, profile_sha256, 'WAREHOUSE', 'KHO_F', phap_nhan_id, now(), "
                       "'CFO_V4', %s FROM master.anh_xa_nguon LIMIT 1", (CFOA,), "permission denied"),
                (KTA, f"UPDATE kho.phieu_kho_danh_tinh SET eligible_content_id = NULL WHERE id = '{pid}'", (), "permission denied"),
                (KTA, "SELECT * FROM master.nguon_master_noi_dung", (), "permission denied"),
                (KTA, "SELECT * FROM giao_tiep.lan_tiep_nhan_nguon", (), "permission denied")):
            with self.subTest(sql=sql[:50]):
                self.raises(ma, lambda: self.sql(login, sql, params))
        self.raises("KHONG_CO_QUYEN_SOURCE_REVIEW", lambda: self.sql(KTA, "SELECT kho.m5_xem_xet_nguon(%s::jsonb)", (json.dumps({"phieu_id": pid}),)))
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.sql(KTA, "SELECT * FROM giao_tiep.nguon_tim_lan_nhan('DEMO_KHO_A','x','y','k01')"))
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.sql(KTA, "SELECT * FROM giao_tiep.nguon_tim_lan_nhan('DEMO_KHO_A','x','y','k01')", id_cua=M0A))  # ID/login lệch
        self.assertEqual(len(self.sql(KTA, "SELECT * FROM master.nguon_profile")), 0)  # metadata nguồn chỉ theo năng lực nguồn
        self.assertEqual(len(self.sql(M0A, "SELECT * FROM master.nguon_profile")), 1)
        self.assertEqual(len(self.sql(M1A, "SELECT * FROM master.nguon_instance")), 0)
        # dương: stage hợp lệ do chủ bảng chuẩn bị → app thường (đúng actor) tiêu thụ được; actor khác/H sai bị chặn
        stage, h = self._stage_hop_le("k-stage-chu")
        self.raises("STAGE_ACTOR_SAI", lambda: self.sql(M0B, "SELECT * FROM giao_tiep.nguon_tieu_thu_capture(%s::uuid, %s)", (stage, h)))
        self.raises("STAGE_KHONG_HOP_LE", lambda: self.sql(M0A, "SELECT * FROM giao_tiep.nguon_tieu_thu_capture(%s::uuid, %s)", (stage, "f" * 64)))
        out = self.sql(M0A, "SELECT * FROM giao_tiep.nguon_tieu_thu_capture(%s::uuid, %s)", (stage, h))
        self.assertEqual((out[0]["moi"], out[0]["snapshot_moi"]), (True, False))
        self.assertEqual(self.sql(M0A, "SELECT * FROM giao_tiep.nguon_tieu_thu_capture(%s::uuid, %s)", (stage, h))[0]["moi"], False)

    def test_t16_hai_ket_noi_cung_khoa_mot_occurrence(self):
        barrier, out = threading.Barrier(2), {}

        def chay(ten, svc):
            barrier.wait(10)
            try:
                out[ten] = self.nhan(M0A, "K01", "k-dong-thoi", svc=svc)
            except Exception as exc:  # noqa: BLE001
                out[ten] = exc
        t = [threading.Thread(target=chay, args=(n, s), daemon=True) for n, s in (("a", self.m5), ("b", self.m5b))]
        [x.start() for x in t]
        [x.join(90) for x in t]
        self.assertFalse(any(x.is_alive() for x in t), "worker treo — không tính đạt")
        self.assertTrue(all(isinstance(v, dict) for v in out.values()), out)
        self.assertEqual(sorted(v["lap_lai"] for v in out.values()), [False, True])
        self.assertEqual(out["a"]["promote"], out["b"]["promote"])  # kẻ thua replay đúng kết quả cuối của người thắng
        self.assertEqual(out["a"]["stage_id"], out["b"]["stage_id"])
        self.assertEqual(self.q("SELECT count(*) FROM giao_tiep.lan_tiep_nhan_nguon WHERE client_key = 'k-dong-thoi'"), 1)

    # ------------------------------------------------------------------ mapping / file soát / sentinel / kỳ khóa / seed mở lại / thu hồi
    def test_t17_mapping_can_ca_nguon_va_v4_qua_ham_dinh_nghia(self):
        body = {"source_instance": "DEMO_KHO_A", "ma_kho": "KHO_MOI_DEMO", "phap_nhan": "PN_DEMO_A", "revision_hien_tai": 0, "ly_do": "DEMO", "khoa": "map-1"}
        r = self.m5.cap_nhat_mapping(CFOA, body)
        self.assertEqual((r["revision"], r["lap_lai"]), (1, False))
        self.assertTrue(self.m5.cap_nhat_mapping(CFOA, body)["lap_lai"])
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m5.cap_nhat_mapping(CFOA, {**body, "ly_do": "khác"}))
        self.raises("ANH_XA_DA_CO", lambda: self.m5.cap_nhat_mapping(CFOA, {**body, "revision_hien_tai": 1, "khoa": "map-2"}))
        self.raises("KHONG_CO_QUYEN_PHAP_NHAN", lambda: self.m5.cap_nhat_mapping(CFOA, {**body, "phap_nhan": "PN_DEMO_B", "khoa": "map-3"}))
        self.raises("ANH_XA_KHONG_CO_QUYEN", lambda: self.m5.cap_nhat_mapping(CFOB, {**body, "phap_nhan": "PN_DEMO_B", "khoa": "map-4"}))  # SOURCE_MAP sai nguồn
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.m5.cap_nhat_mapping(KTA, {**body, "khoa": "map-5"}))
        self.raises("ANH_XA_KHONG_CO_QUYEN", lambda: self.sql(KTA, "SELECT kho.m5_anh_xa_v4(%s::jsonb)", (json.dumps({**body, "client_key": "map-6"}),)))

    def test_t17b_map_namespace_dong_thoi_cung_khoa_cung_payload_replay(self):
        """Yêu cầu 1 (kết nối riêng) giữ giao dịch đã ghi mapping+biên nhận chưa commit; yêu cầu 2 qua service cùng khóa/payload phải CHỜ ở namespace
        (observer thấy backend app2 chờ advisory) rồi REPLAY đúng biên nhận/mapping của yêu cầu 1 — không ANH_XA_DA_CO. Positive control: khóa khác
        cùng payload sau commit → ANH_XA_DA_CO (chứng minh replay là do namespace, không do bỏ qua kiểm mapping)."""
        body = {"source_instance": "DEMO_KHO_A", "ma_kho": "KHO_NS_DEMO", "phap_nhan": "PN_DEMO_A", "revision_hien_tai": 0, "ly_do": "DEMO ns", "khoa": "map-ns"}
        cfo_id = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (CFOA,))
        out = {}
        holder = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row, options="-c lock_timeout=20000 -c statement_timeout=60000")
        try:
            with holder.transaction():
                holder.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (cfo_id, CFOA))
                r1 = holder.execute("SELECT kho.m5_anh_xa_v4(%s::jsonb) AS v",
                                    (json.dumps({k: v for k, v in body.items() if k != "khoa"} | {"client_key": "map-ns"}),)).fetchone()["v"]
                self.assertFalse(r1["lap_lai"])

                def chay():
                    try:
                        out["r2"] = self.m5b.cap_nhat_mapping(CFOA, body)
                    except Exception as exc:  # noqa: BLE001
                        out["r2"] = exc
                t = threading.Thread(target=chay, daemon=True)
                t.start()
                self.assertTrue(self.cho_advisory(self.app2.info.backend_pid), "không quan sát được yêu cầu 2 chờ namespace — không tính đạt")
                self.assertTrue(t.is_alive())
                self.assertNotIn("r2", out)
            t.join(60)
        finally:
            holder.close()
        self.assertFalse(t.is_alive(), "worker treo — không tính đạt")
        r2 = out["r2"]
        self.assertIsInstance(r2, dict, r2)
        self.assertEqual((r2["lap_lai"], r2["mapping_id"], r2["bien_nhan_id"]), (True, r1["mapping_id"], r1["bien_nhan_id"]))
        self.assertEqual(self.q("SELECT count(*) FROM kho.bien_nhan_thao_tac WHERE module = 'M5' AND operation = 'MAP_V4' AND client_key = 'map-ns'"), 1)
        self.assertEqual(self.q("SELECT count(*) FROM master.anh_xa_nguon WHERE subject_key = 'KHO_NS_DEMO'"), 1)
        self.raises("ANH_XA_DA_CO", lambda: self.m5.cap_nhat_mapping(CFOA, {**body, "khoa": "map-ns-2"}))

    def test_t18_file_soat_idempotent_expected_va_cells(self):
        from openpyxl import load_workbook
        pid = self.phieu_a()
        body = self.body_file(KTA, pid, "file-1")
        self.assertRegex(body["co_so_truoc"], r"^[0-9a-f]{64}$")
        self.assertEqual(self.m5.chi_tiet(KTA, pid)["co_so_file"]["co_so_sha256"], body["co_so_truoc"])  # deterministic: đọc lại cùng token
        truoc, files = self.counts(), self.files_xuat()
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, {**body, "latest_truoc": None, "khoa": "file-cu"}))
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, {**body, "co_so_truoc": "0" * 64, "khoa": "file-cu2"}))
        self.raises("M5_CO_SO_FILE", lambda: self.m5.xuat_file_soat(KTA, {k: v for k, v in body.items() if k != "co_so_truoc"}))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.m5.xuat_file_soat(VIEWA, body))
        self.assertEqual((self.counts(), self.files_xuat()), (truoc, files))
        lo = self.m5.xuat_file_soat(KTA, body)
        self.assertEqual(lo["co_so_sha256"], body["co_so_truoc"])
        lai = self.m5.xuat_file_soat(KTA, body)
        self.assertEqual((lai["lap_lai"], lai["id"], lai["sha256"]), (True, lo["id"], lo["sha256"]))
        # cùng khóa + expected con trỏ sai: guard hiện hành chạy TRƯỚC tra biên nhận → stale (không cached success, không 409 che stale)
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, {**body, "eligible_truoc": "00000000-0000-0000-0000-000000000000"}))
        sau_lo = self.counts()
        self.assertEqual(sau_lo["kho.lo_xuat"], truoc["kho.lo_xuat"] + 1)
        ten, raw = self.m5.tep_file_soat(KTA, lo["id"])
        self.assertEqual((raw[:2], sha256(raw), len(raw)), (b"PK", lo["sha256"], lo["byte_length"]))
        wb = load_workbook(io.BytesIO(raw))
        ws = wb["DONG_NGUON"]
        self.assertTrue(all(c.data_type != "f" for w in wb.worksheets for r in w.iter_rows() for c in r))
        so_luong = [r[10].value for r in ws.iter_rows(min_row=2)]
        self.assertIn(None, so_luong)  # K08 NULL giữ trống, không 0
        self.assertIn("9007199254740992", so_luong)
        cs = {r[0].value: r[1].value for r in wb["CO_SO"].iter_rows(min_row=2)}
        self.assertEqual((cs["co_so_sha256"], cs["con_tro.latest"], cs["ky"]), (body["co_so_truoc"], body["latest_truoc"], "2026-08"))
        self.assertEqual(self.q("SELECT du_lieu->>'co_so_sha256' FROM kho.lo_xuat WHERE id = %s", (lo["id"],)), body["co_so_truoc"])
        self.raises("FILE_SOAT", lambda: self.m5.tep_file_soat(KTB, lo["id"]))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.m5.tep_file_soat(VIEWA, lo["id"]))
        # basis đổi trong khi BA CON TRỎ giữ nguyên: thêm (bởi chủ CSDL) một khai báo đo lường KHÔNG khớp điều kiện cho cùng profile — không đổi kết
        # quả resolve của intake nhưng thuộc basis ⇒ retry khóa cũ/expected cũ bị từ chối với 0 delta; file cũ vẫn tải đúng bytes cũ.
        f = self.admin.execute("""SELECT f.source_instance_id, f.profile_ref, f.profile_sha256, f.declaration_ref, f.payload, f.dieu_kien
                                  FROM master.nguon_su_kien_do_luong f WHERE f.source_instance_id = 'DEMO_KHO_A' ORDER BY f.declaration_ref LIMIT 1""").fetchone()
        payload = {**f[4], "test_stale_basis_marker": "repair03"}
        dk = json.loads(json.dumps(f[5]))
        dk["resolution_preconditions"]["actual_master_sha256"] = "0" * 64
        self.admin.execute("""INSERT INTO master.nguon_su_kien_do_luong (source_instance_id, profile_ref, profile_sha256, declaration_ref, payload_sha256, payload,
                              dieu_kien) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
                           (f[0], f[1], f[2], f[3] + "#STALE_BASIS_TEST", nguon_chung.digest_payload(payload), json.dumps(payload), json.dumps(dk)))
        self.assertEqual(self.con_tro(pid), {"latest_observation_id": body["latest_truoc"], "accepted_source_observation_id": body["accepted_truoc"],
                                             "eligible_content_id": body["eligible_truoc"]})
        moi = self.m5.chi_tiet(KTA, pid)["co_so_file"]["co_so_sha256"]
        self.assertNotEqual(moi, body["co_so_truoc"])
        truoc2, files2 = self.counts(), self.files_xuat()
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, body))  # cùng khóa, expected cũ: KHÔNG trả cached success
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, {**body, "khoa": "file-stale-moi"}))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m5.xuat_file_soat(KTA, {**body, "co_so_truoc": moi}))  # cùng khóa, basis hiện hành khác H
        self.assertEqual((self.counts(), self.files_xuat()), (truoc2, files2))
        self.assertEqual(self.m5.tep_file_soat(KTA, lo["id"])[1], raw)
        body2 = self.body_file(KTA, pid, "file-2")
        lo2 = self.m5.xuat_file_soat(KTA, body2)
        self.assertEqual((lo2["lap_lai"], lo2["co_so_sha256"]), (False, moi))
        self.assertNotEqual(lo2["id"], lo["id"])
        self.state["file_body"], self.state["file_lo"] = body2, lo2

    def test_t18b_chi_tiet_va_token_cung_snapshot(self):
        """Repair04 mục1: interleave THẬT với kết nối thứ hai. chi_tiet đã đọc mapping A (đang mở) → kết nối chủ khác (CFO_A hiện hành, trigger bật,
        0 grant mới) đóng A + nối successor B cùng PN rồi COMMIT (observer xác nhận) → các SELECT còn lại + token. Phải trả trọn A + tokenA (không
        displayA + tokenB). Ba con trỏ giữ nguyên; FILE với view cũ bị từ chối 0 delta; view mới/token mới xuất được."""
        pid = self.phieu_a()
        goc = self.m5.chi_tiet(CFOA, pid)
        self.assertTrue(goc["noi_dung"] and goc["lich_su"] and goc["noi_dung"][0]["dong"])  # preview không rỗng
        self.assertEqual(self.m5.chi_tiet(CFOA, pid)["co_so_file"], goc["co_so_file"])  # không đột biến: cùng token
        map_a = self.q("SELECT mapping_revision_id::text FROM kho.phieu_kho_danh_tinh WHERE id = %s", (pid,))
        self.assertEqual(self.q("SELECT state FROM master.anh_xa_nguon WHERE id = %s", (map_a,)), "DA_DUYET")
        cfo_id = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (CFOA,))
        quan_sat = {}

        def dot_bien():
            with psycopg.connect(self.dsn, autocommit=True) as c2:
                with c2.transaction():
                    c2.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                               "set_config('ktt.ngay_hieu_luc', current_date::text, true)", (cfo_id, CFOA))
                    c2.execute("UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = %s", (map_a,))
                    c2.execute("""INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind,
                                      subject_key, phap_nhan_id, valid_from, thay_cho_id, nguon_quyet_dinh, duyet_boi, ly_do)
                                  SELECT m.reference_id, (SELECT max(x.revision) FROM master.anh_xa_nguon x WHERE x.source_instance_id = m.source_instance_id
                                             AND x.profile_ref = m.profile_ref AND x.profile_sha256 = m.profile_sha256 AND x.subject_kind = m.subject_kind
                                             AND x.subject_key = m.subject_key) + 1,
                                         m.source_instance_id, m.profile_ref, m.profile_sha256, m.subject_kind, m.subject_key, m.phap_nhan_id, now(), m.id,
                                         'ROOT_SEED_DEMO', 'ROOT_SEED_DEMO', 'repair04 coherent-preview interleave'
                                  FROM master.anh_xa_nguon m WHERE m.id = %s""", (map_a,))
            # observer độc lập: đột biến đã commit TRƯỚC khi chi_tiet chạy các SELECT còn lại và token
            quan_sat["state"] = self.q("SELECT state FROM master.anh_xa_nguon WHERE id = %s", (map_a,))
            quan_sat["ke_tiep"] = self.q("SELECT count(*) FROM master.anh_xa_nguon WHERE thay_cho_id = %s AND state = 'DA_DUYET'", (map_a,))

        hen = _HenGio(self.app, "FROM kho.viec_can_duyet WHERE tham_chieu_id", dot_bien)  # sau khi SELECT mapping đã đọc xong
        cu = KhoSoLuongK2(hen, self.root, conn_chu=self.chu).chi_tiet(CFOA, pid)
        self.assertTrue(hen.da_chay)
        self.assertEqual(quan_sat, {"state": "DONG", "ke_tiep": 1})
        m_cu = {m["id"]: m for m in cu["anh_xa"]}
        self.assertEqual((m_cu[map_a]["state"], m_cu[map_a]["valid_to"], len(cu["anh_xa"])), ("DA_DUYET", None, len(goc["anh_xa"])))  # trọn view A
        self.assertEqual((cu["co_so_file"], cu["con_tro"]), (goc["co_so_file"], goc["con_tro"]))  # token A đi cùng display A
        moi = self.m5.chi_tiet(CFOA, pid)
        m_moi = {m["id"]: m for m in moi["anh_xa"]}
        self.assertEqual((m_moi[map_a]["state"], len(moi["anh_xa"])), ("DONG", len(goc["anh_xa"]) + 1))
        self.assertEqual(moi["con_tro"], goc["con_tro"])  # ba con trỏ giữ nguyên
        self.assertNotEqual(moi["co_so_file"]["co_so_sha256"], cu["co_so_file"]["co_so_sha256"])
        than = lambda ct, khoa: {"phieu_id": pid, "khoa": khoa, "latest_truoc": ct["con_tro"]["latest_observation_id"],  # noqa: E731
                                 "accepted_truoc": ct["con_tro"]["accepted_source_observation_id"], "eligible_truoc": ct["con_tro"]["eligible_content_id"],
                                 "co_so_truoc": ct["co_so_file"]["co_so_sha256"]}
        truoc, files = self.counts(), self.files_xuat()
        self.raises("KHO_VERSION_CHANGED", lambda: self.m5.xuat_file_soat(KTA, than(cu, "file-xem-cu")))
        self.assertEqual((self.counts(), self.files_xuat()), (truoc, files))
        lo = self.m5.xuat_file_soat(KTA, than(moi, "file-xem-moi"))
        self.assertEqual((lo["lap_lai"], lo["co_so_sha256"]), (False, moi["co_so_file"]["co_so_sha256"]))
        _, raw = self.m5.tep_file_soat(KTA, lo["id"])
        self.assertEqual((sha256(raw), len(raw)), (lo["sha256"], lo["byte_length"]))

    def test_t18c_file_namespace_hai_phieu_that_ca_hai_thu_tu(self):
        """Repair04 mục5: phiếu sibling THẬT cùng PN qua intake thật (phạm vi cấu hình thêm trong DB test mới + bytes K01 đổi SoPhieu; không đổi
        fixture/registry file/actor/grant). Hai kết nối chủ của service xuất FILE cùng khóa nghiệp vụ cho HAI phiếu khác nhau: request thắng giữ giao
        dịch (đã khóa namespace, trước stage); observer thấy backend kẻ thua chờ advisory NOT granted, 0 stage/lô/file của kẻ thua; thả → thắng commit,
        thua 409 IDEMPOTENCY_KHAC với 0 artifact/stage/lô. Cả hai thứ tự thắng bằng khóa mới; replay thắng = cùng lô; timeout/treo KHÔNG đạt."""
        pid1 = self.phieu_a()
        sc = scope_cua(registry(), "DEMO_KHO_A")["scope_ref"]
        sc2 = sc + ":SIBLING_REPAIR04"
        self.admin.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho, so_phieu, sections,
                                  coverage_binding)
                              SELECT source_instance_id, profile_ref, profile_sha256, %s, ma_kho, 'NK20260814002', sections, coverage_binding
                              FROM master.nguon_pham_vi WHERE source_instance_id = 'DEMO_KHO_A' AND scope_ref = %s""", (sc2, sc))
        goc = m5_demo.mau("K01")["native"]
        native2 = goc.replace(b"NK20260814001", b"NK20260814002")
        self.assertNotEqual(native2, goc)
        r = self.nhan(M0A, "K01", "k-sibling-repair04", scope_ref=sc2, native=native2)
        self.assertEqual((r["promote"]["trang_thai"], r["phap_nhan"], r["giu_cho"]), ("DA_GHI_QUAN_SAT", "PN_DEMO_A", []))
        pid2 = r["promote"]["phieu_id"]
        self.assertNotEqual(pid2, pid1)
        self.assertEqual(self.q("SELECT count(DISTINCT phap_nhan_id) FROM kho.phieu_kho_danh_tinh WHERE id IN (%s, %s)", (pid1, pid2)), 1)
        for thu_tu, (thang, thua) in enumerate(((pid1, pid2), (pid2, pid1))):
            with self.subTest(thu_tu=thu_tu):
                khoa = f"file-2phieu-{thu_tu}"
                b_thang, b_thua = self.body_file(KTA, thang, khoa), self.body_file(KTA, thua, khoa)
                dang_giu, tha, out, t2 = threading.Event(), threading.Event(), {}, None

                def giu():
                    dang_giu.set()
                    if not tha.wait(60):
                        raise AssertionError("request thắng không được thả — timeout, không tính đạt")

                svc_thang = KhoSoLuongK2(self.app, self.root, conn_chu=_HenGio(self.chu, "INSERT INTO giao_tiep.stage_tin_cay", giu))

                def chay(ten, svc, body):
                    try:
                        out[ten] = svc.xuat_file_soat(KTA, body)
                    except Exception as exc:  # noqa: BLE001
                        out[ten] = exc
                truoc = self.counts()
                t1 = threading.Thread(target=chay, args=("thang", svc_thang, b_thang), daemon=True)
                t1.start()
                try:
                    self.assertTrue(dang_giu.wait(60), "request thắng chưa tới điểm giữ — không tính đạt")
                    dem_giu, files_giu = self.counts(), self.files_xuat()
                    self.assertEqual(dem_giu, truoc)  # thắng đang giữ: đã khóa namespace + ghi file, chưa stage/lô/biên nhận
                    t2 = threading.Thread(target=chay, args=("thua", self.m5b, b_thua), daemon=True)
                    t2.start()
                    self.assertTrue(self.cho_advisory(self.chu2.info.backend_pid), "không quan sát được kẻ thua chờ namespace — không tính đạt")
                    self.assertTrue(t2.is_alive())
                    self.assertEqual((self.counts(), self.files_xuat()), (dem_giu, files_giu))  # kẻ thua chưa tạo gì
                finally:
                    tha.set()
                t1.join(60)
                if t2 is not None:
                    t2.join(60)
                self.assertFalse(t1.is_alive() or (t2 is not None and t2.is_alive()), "worker treo — không tính đạt")
                self.assertIsInstance(out["thang"], dict, out.get("thang"))
                self.assertEqual((out["thang"]["lap_lai"], out["thang"]["phieu_id"]), (False, thang))
                self.assertIsInstance(out["thua"], (DataError, psycopg.Error), out.get("thua"))
                self.assertIn("IDEMPOTENCY_KHAC", (getattr(out["thua"], "code", "") or "") + " " + str(out["thua"]))
                sau = self.counts()
                self.assertEqual({k: sau[k] - truoc[k] for k in sau if sau[k] != truoc[k]},
                                 {"giao_tiep.stage_tin_cay": 1, "kho.lo_xuat": 1, "kho.bien_nhan_thao_tac": 1})  # chỉ của request thắng
                self.assertEqual(self.files_xuat(), files_giu)  # 0 artifact của kẻ thua
                lai = self.m5.xuat_file_soat(KTA, b_thang)
                self.assertEqual((lai["lap_lai"], lai["id"]), (True, out["thang"]["id"]))  # cùng phiếu/cùng H: replay
                self.raises("IDEMPOTENCY_KHAC", lambda: self.m5.xuat_file_soat(KTA, b_thua))
                self.assertEqual(self.counts(), sau)

    def test_t19_sentinel_non_m5_nguyen_va_core_m5_dung_so(self):
        self.assertEqual(self.sentinel_snapshot(), self.nen)
        self.assertEqual(self.q("SELECT count(*) FROM kho.chung_tu WHERE module_nghiep_vu = 'M5'"), self.q("SELECT count(*) FROM kho.phieu_kho_phien_ban"))
        self.assertEqual(self.q("""SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M5'"""),
                         self.q("SELECT count(*) FROM kho.phieu_kho_dong_phien_ban"))
        self.assertEqual(self.q("SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M5' "
                                "AND (d.no_minor IS NOT NULL OR d.co_minor IS NOT NULL)"), 0)

    def test_t20_ky_khoa_giu_capture_0_nghiep_vu(self):
        pn = self.q("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")
        pid = self.phieu_a()
        ct = self.con_tro(pid)
        body_ky = self.body_file(KTA, pid, "file-ky")
        self.admin.execute("INSERT INTO kho.khoa_ky (phap_nhan_id, ky, nguoi) VALUES (%s, '2026-08', 'TEST_ROOT_DEMO') ON CONFLICT DO NOTHING", (pn,))
        truoc = self.counts()
        r = self.nhan(M0A, "K01", "k-ky-khoa")
        self.assertEqual((r["promote"]["trang_thai"], r["promote"]["ly_do"]), ("GIU_CHO", "KY_DA_KHOA"))
        sau = self.counts()
        self.assertEqual({k: sau[k] - truoc[k] for k in sau if sau[k] != truoc[k]},
                         {"giao_tiep.lan_tiep_nhan_nguon": 1, "giao_tiep.stage_tin_cay": 1, "giao_tiep.ket_qua_cuoi_tiep_nhan": 1})  # 0 typed/core/pointer/lô
        self.assertEqual(self.con_tro(pid), ct)
        # SR02-1: replay cùng key/H trả ĐÚNG HOLD kỳ khóa đã chốt (không tính lại), 0 delta
        lai = self.nhan(M0A, "K01", "k-ky-khoa")
        self.assertEqual((lai["lap_lai"], lai["promote"], lai["stage_id"], lai["snapshot_moi"]), (True, r["promote"], r["stage_id"], r["snapshot_moi"]))
        self.assertEqual(self.counts(), sau)
        self.raises("KY_DA_KHOA", lambda: self.m5.xuat_file_soat(KTA, body_ky))
        # kỳ HIỆN HÀNH kiểm TRƯỚC cached FILE: retry đúng khóa/basis của lô đã xuất ở t18 → từ chối, không trả cached success; file cũ vẫn tải đúng bytes
        self.raises("KY_DA_KHOA", lambda: self.m5.xuat_file_soat(KTA, self.state["file_body"]))
        self.assertEqual(self.counts(), sau)
        _, raw = self.m5.tep_file_soat(KTA, self.state["file_lo"]["id"])
        self.assertEqual(sha256(raw), self.state["file_lo"]["sha256"])

    def test_t21_seed_mo_lai_giu_quyen_va_thu_hoi(self):
        from kho_tri_thuc.k2 import crm_demo
        self.admin.execute("""DELETE FROM master.nang_luc_nguon c USING master.nguoi_dung n WHERE n.id = c.nguoi_dung_id AND n.dang_nhap = %s
                              AND c.hanh_dong = 'INTAKE'""", (M0B,))  # thu hồi = thao tác chủ CSDL
        self.admin.execute("""UPDATE master.phan_quyen q SET module = '{CRM}' FROM master.nguoi_dung n WHERE n.id = q.nguoi_dung_id AND n.dang_nhap = 'MO_PHONG_KT_A'""")
        truoc = self.q("""SELECT jsonb_agg(to_jsonb(q) ORDER BY q.id)::text FROM master.phan_quyen q""")
        crm_demo.khoi_tao(self.admin)
        m5_demo.khoi_tao(self.admin)
        self.assertEqual(self.q("""SELECT jsonb_agg(to_jsonb(q) ORDER BY q.id)::text FROM master.phan_quyen q"""), truoc)
        self.assertEqual(self.q("""SELECT count(*) FROM master.nang_luc_nguon c JOIN master.nguoi_dung n ON n.id = c.nguoi_dung_id
                                   WHERE n.dang_nhap = %s AND c.hanh_dong = 'INTAKE'""", (M0B,)), 0)
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.nhan(M0B, "K02", "k02"))  # thu hồi chặn cả replay

    def test_t22_thu_hoi_nang_luc_chan_ca_replay(self):
        self.admin.execute("""DELETE FROM master.nang_luc_nguon c USING master.nguoi_dung n WHERE n.id = c.nguoi_dung_id AND n.dang_nhap = %s
                              AND c.hanh_dong = 'INTAKE'""", (M0A,))
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.nhan(M0A, "K01", "k01"))
        print("\nM5_K2_AGGREGATE", canonical_json({"db": self.db, "role": self.role, "counts": self.counts(), "seed": self.seed1}))

    def test_t23_nguon_dung_khong_qua_getter_source_map(self):
        """I-S01: CFO chỉ có SOURCE_MAP (không INTAKE/READ_SOURCE) đọc được mapping hiện hành khi nguồn HOAT_DONG (dương, đúng PN đích);
        chủ CSDL chuyển instance sang DUNG → cùng getter bị từ chối dù hàng năng lực còn nguyên; quyền/biên nhận 0 delta. (Chạy cuối: đổi lifecycle.)"""
        reg = registry()
        p, s = profile_cua(reg, "DEMO_KHO_A"), scope_cua(reg, "DEMO_KHO_A")
        self.assertEqual({r["hanh_dong"] for r in self.m5.nang_luc_cua_toi(CFOA)}, {"SOURCE_MAP"})
        sql = "SELECT * FROM giao_tiep.nguon_anh_xa_hien_hanh(%s, %s, %s, 'WAREHOUSE', %s)"
        tham = ("DEMO_KHO_A", p["reference_id"], p["sha256"], s["MaKho"])
        rows = self.sql(CFOA, sql, tham)
        self.assertEqual([r["phap_nhan_ma"] for r in rows], ["PN_DEMO_A"])
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.sql(KTA, sql, tham))  # không năng lực nguồn → âm
        quyen_truoc = self.q("SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id)::text FROM master.nang_luc_nguon c")
        dem_truoc = self.counts()
        self.admin.execute("UPDATE master.nguon_instance SET trang_thai = 'DUNG' WHERE source_instance_id = 'DEMO_KHO_A'")
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.sql(CFOA, sql, tham))
        self.assertEqual((self.q("SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id)::text FROM master.nang_luc_nguon c"), self.counts()), (quyen_truoc, dem_truoc))


if __name__ == "__main__":
    unittest.main()
