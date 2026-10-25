"""Dữ liệu DEMO cho clone sở hữu 03A/03B; chỉ gọi sau CREATE + bootstrap hiện hành.

Không SQL nghiệp vụ tự viết, không thay SQL/service, không giả lịch sử migration.
M4 chưa có seed kế toán tham số hóa: nạp chính seed hiện có trong namespace riêng,
chỉ cấu hình marker/ma trận DEMO cho khoi_tao_duyet; giữ nguyên module sản phẩm.
Hóa đơn/dòng logic đi qua nhan + mapping_line thật với fixture được m2_demo kiểm pin.
Không sửa MST đối tác để ép ca dương; không tạo thành phần tỷ lệ trước M0033.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import tempfile
from pathlib import Path

KT1, KT2, KT_KHAC = "MO_PHONG_KT1_03A", "MO_PHONG_KT2_03A", "MO_PHONG_KT_M4"
CFO, XEM, INTAKE = "MO_PHONG_CFO_MUA_A", "MO_PHONG_VIEW_MUA_A", "MO_PHONG_M0_HD_INTAKE"
ACTOR = (
    (KT1, "KE_TOAN", {"PN_DEMO_A": ["M4", "M2"]}, [("DA_XD_A1", "KE_TOAN")]),
    (KT2, "KE_TOAN", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "KE_TOAN")]),
)


def dac_ta(provenance: str) -> tuple[dict, dict]:
    """Ghim checksum/ordinal từ registry phần mềm; không ghi schema_migrations."""
    from kho_tri_thuc.ha_tang.pg_migrations import PG_MIGRATIONS
    from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET
    from kho_tri_thuc.m4.sql_ke_toan_nghiem_thu import M4_03A_SQL
    from kho_tri_thuc.k2.sql_ghi_nhan_chung import M4_03B_COMMON_SQL
    from kho_tri_thuc.k2.sql_ghi_nhan_so_tien import M4_03B_SO_TIEN_SQL

    ordinal = [i for i, sql in enumerate(PG_MIGRATIONS, 1) if sql is M4_03A_SQL]
    if (len(ordinal) != 1 or ordinal[0] <= 24 or PG_MIGRATIONS[23] is not M0024_M4_DUYET
            or not any(sql is M4_03B_COMMON_SQL for sql in PG_MIGRATIONS)
            or not any(sql is M4_03B_SO_TIEN_SQL for sql in PG_MIGRATIONS)):
        raise ValueError("Registry thiếu/sai migration 03A/03B; không cấp cờ đã áp dụng.")

    def sha(sql):
        return hashlib.sha256("\n".join(sql).encode("utf-8")).hexdigest()

    return {"m4_03a_clone_provenance": provenance}, {
        "KHO_M4_03A_CLONE_PROVENANCE": provenance,
        "KHO_M4_03A_M24_SHA256": sha(M0024_M4_DUYET),
        "KHO_M4_03A_VERSION": str(ordinal[0]), "KHO_M4_03A_SHA256": sha(M4_03A_SQL),
        "KHO_M4_03A_KT1": KT1, "KHO_M4_03A_KT2": KT2, "KHO_M4_03A_KT_KHAC": KT_KHAC,
        "KHO_M4_03B_DA_AP_DUNG": "1", "KHO_M4_03B_CFO": CFO, "KHO_M4_03B_XEM": XEM,
    }


def _seed_ke_toan(admin):
    from kho_tri_thuc.k2 import m4_demo

    if m4_demo.khoi_tao_duyet(admin)["trang_thai"] != "DU":
        raise ValueError("Duyệt viên M4 DEMO chưa đủ quyền; không tự cấp lại.")
    spec = importlib.util.spec_from_file_location("_pg_demo_03a_seed_m4", m4_demo.__file__)
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed.MARKER_DUYET = "demo_seed_m4_03a_ke_toan"
    seed.NGUOI_DUNG_DUYET = ACTOR
    if seed.khoi_tao_duyet(admin)["trang_thai"] != "DU":
        raise ValueError("Kế toán M4 DEMO chưa đủ quyền; không tự cấp lại.")


def _nhan_hoa_don(admin, svc) -> dict:
    from kho_tri_thuc.k2 import m2_demo

    d = m2_demo.doc_khai_bao()
    rel = "inputs/G01-wrapped-positive.xml"
    _, raw = m2_demo.mau(rel)
    # Dùng khai báo literal đã pin, không đọc workflow/oracle hoặc tự dựng UUID/mapping.
    fact = next(f for f in m2_demo.doc_ung_vien_dong(d) if f["source_artifact_relative_path"] == rel)
    svc.nhan(INTAKE, source_instance=d["source_instance"], scope_ref=fact["scope_ref"],
             coverage="COMPLETE_INPUT", client_key="pg-demo-03a-g01", native=raw)
    hd = admin.execute("""SELECT h.id::text FROM kho.hoa_don_danh_tinh h
                          JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
                          WHERE p.ma = %s AND h.chieu = %s AND h.mst_ban = %s
                            AND h.mau_so = %s AND h.ky_hieu = %s AND h.so_chuan = %s""",
                       tuple(fact["identity_tuple"])).fetchone()
    if hd is None:
        return {}  # không có hóa đơn chính thức → cổng cross-source tự skip NOT_VERIFIED
    env = {"KHO_M4_03B_HOA_DON_ID": hd[0]}
    ct = svc.chi_tiet(CFO, hd[0])
    row = next((r for r in ct["dong_nguon_hien_hanh"]
                if r["source_ordinal"] == fact["source_ordinal"] and r["locator"] == fact["source_locator"]), None)
    if row is not None:
        svc.mapping_line(CFO, client_key="pg-demo-03a-map-g01", hoa_don_id=hd[0], expected_graph=ct["expected_graph"],
                         source_row_id=row["source_row_id"], logical_line_key=fact["logical_line_key"],
                         evidence_ref=fact["mapping_ref"], evidence_revision=fact["revision"], reason="CFO DEMO map dòng cho test 03B")
        dong = admin.execute("""SELECT id::text FROM kho.hoa_don_dong_danh_tinh
                                WHERE hoa_don_id = %s AND logical_line_key = %s""",
                             (hd[0], fact["logical_line_key"])).fetchone()
        if dong is not None:
            env["KHO_M4_03B_DONG_ID"] = dong[0]
    return env


def dung_du_lieu(admin_dsn: str, app_dsn: str, db: str) -> dict:
    """Chỉ bản sao kho_test_pgd_* mới của runner; DSN không đi vào kết quả/nhật ký."""
    from kho_tri_thuc.k2 import crm_khoi_dong as KD
    from kho_tri_thuc.ha_tang import postgres as pg
    from kho_tri_thuc.k2.hoa_don import HoaDonK2
    import psycopg
    from psycopg.rows import dict_row

    if not re.fullmatch(r"kho_test_pgd_[a-f0-9]{12}", db):
        raise ValueError("Dữ liệu 03A chỉ được dựng trên clone test riêng.")
    cap = KD.kiem_cap(app_dsn, admin_dsn, KD.TIEN_TO_DB_KIEM_THU)
    if cap["db"] != db:
        raise ValueError("Cặp kết nối không trỏ clone test mong đợi.")
    with psycopg.connect(cap["admin"]["conninfo"], autocommit=True) as admin:
        pg.kiem_lineage_ung_dung(admin)  # toàn chuỗi hiện hành trước seed/cấp cờ 03B
        _seed_ke_toan(admin)
        with psycopg.connect(cap["app"]["conninfo"], autocommit=True, row_factory=dict_row) as app, \
                psycopg.connect(cap["admin"]["conninfo"], autocommit=True, row_factory=dict_row) as chu:
            KD.kiem_ket_noi_chu(chu, app)
            root = Path(tempfile.mkdtemp(prefix="ktt_pg_demo_03a_"))
            return _nhan_hoa_don(admin, HoaDonK2(app, root, conn_chu=chu))
