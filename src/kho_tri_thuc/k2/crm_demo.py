"""Khởi tạo DEMO CRM-01 trên K2 PostgreSQL (chạy bằng tài khoản chủ CSDL): hai pháp nhân DEMO, danh mục DEMO, người dùng mô phỏng MO_PHONG_*
có phân quyền theo pháp nhân/module, profile loại hình DEMO có version. Không dữ liệu thật.

SR5 (sửa 02): khởi tạo người dùng/phân quyền là MỘT LẦN và CHỈ THÊM. Mở lại (đã có marker hoặc đã có dữ liệu DEMO) không UPSERT vai trò, không ghi
đè mảng duyet_loai_viec/module, không cấp lại quyền đã thu hồi; thiếu quyền KHÔNG phải lý do khởi tạo lại. Seed ban đầu không cấp module M9
(chuỗi mặc định không cài M9). Pháp nhân/danh mục/đối tác/profile loại hình chỉ thêm khi thiếu; profile đã có khác nội dung → từ chối."""

from __future__ import annotations

import json

from ..ha_tang import postgres as pg
from ..ha_tang.primitives import DataError
from .loai_hinh_demo import KCN_THUE_DAT_DEMO, NHA_O_DEMO

PHAP_NHAN = (("PN_DEMO_A", "Pháp nhân DEMO A — KCN", "DEMO_A", KCN_THUE_DAT_DEMO, "DA_KCN_DEMO"),
             ("PN_DEMO_B", "Pháp nhân DEMO B — nhà ở", "DEMO_B", NHA_O_DEMO, "DA_NHA_DEMO"))
DOI_TAC = (("CÔNG TY DEMO THUÊ ĐẤT", {"PN_DEMO_A": "KH_DEMO.A01"}),
           ("KHÁCH DEMO NHÀ Ở", {"PN_DEMO_B": "KH_DEMO.B01"}),
           ("CÔNG TY DEMO CHUNG", {"PN_DEMO_A": "KH_DEMO.CHUNG_A", "PN_DEMO_B": "KH_DEMO.CHUNG_B"}),
           ("NGÂN HÀNG DEMO CHO VAY", {"PN_DEMO_A": "NH_DEMO.A", "PN_DEMO_B": "NH_DEMO.B"}))
NGUOI_DUNG = (  # dang_nhap, vai_tro, {pháp nhân: duyệt loại việc}, module — seed ban đầu KHÔNG cấp M9
    ("MO_PHONG_BAN_HANG", "BAN_HANG", {"PN_DEMO_A": [], "PN_DEMO_B": []}, ["CRM"]),
    ("MO_PHONG_KT_A", "KE_TOAN", {"PN_DEMO_A": ["V1", "V2"]}, ["CRM", "M1"]),
    ("MO_PHONG_KT_B", "KE_TOAN", {"PN_DEMO_B": ["V1", "V2"]}, ["CRM", "M1"]),
    ("MO_PHONG_CFO", "CFO", {"PN_DEMO_A": ["V3", "V4", "V6"], "PN_DEMO_B": ["V3", "V4", "V6"]}, ["CRM", "M1"]),
    ("MO_PHONG_CFO_CHI_V3", "CFO", {"PN_DEMO_A": ["V3"], "PN_DEMO_B": ["V3"]}, ["CRM", "M1"]),
    ("MO_PHONG_XEM_A", "XEM", {"PN_DEMO_A": []}, ["CRM"]),
    ("MO_PHONG_KT_KHONG_CRM_A", "KE_TOAN", {"PN_DEMO_A": ["V1"]}, ["M1"]),
)
MARKER = "demo_seed_crm_nguoi_dung"


def _da_khoi_tao(admin_conn) -> bool:
    """Đã khởi tạo nếu có marker, hoặc DB DEMO cũ đã có người dùng mô phỏng/phân quyền (không dùng việc thiếu quyền để khởi tạo lại)."""
    if admin_conn.execute("SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)).fetchone():
        return True
    return admin_conn.execute("""SELECT EXISTS (SELECT 1 FROM master.nguoi_dung n WHERE n.mo_phong)
                                   OR EXISTS (SELECT 1 FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id WHERE n.mo_phong)""").fetchone()[0]


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL (migrate + seed). Trả id pháp nhân DEMO. Mở lại không đổi người dùng/quyền hiện hành."""
    pg.migrate(admin_conn)
    ids = {}
    with admin_conn.transaction():
        for ma, ten, don_vi, profile, du_an in PHAP_NHAN:
            admin_conn.execute("INSERT INTO master.phap_nhan (ma, ten, ma_don_vi_junsky) VALUES (%s,%s,%s) ON CONFLICT (ma) DO NOTHING", (ma, ten, don_vi))
            pn = admin_conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (ma,)).fetchone()[0]
            ids[ma] = pn
            row = admin_conn.execute("SELECT cau_hinh FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND ma = %s AND phien_ban = %s",
                                     (pn, profile["ma"], profile["phien_ban"])).fetchone()
            if row is None:  # phiên bản mới: đóng hiệu lực bản cũ (giữ lại làm lịch sử, không ghi đè)
                admin_conn.execute("UPDATE master.loai_hinh_doanh_thu SET valid_to = now() WHERE phap_nhan_id = %s AND ma = %s AND phien_ban < %s AND valid_to IS NULL",
                                   (pn, profile["ma"], profile["phien_ban"]))
                admin_conn.execute("INSERT INTO master.loai_hinh_doanh_thu (phap_nhan_id, ma, ten, cau_hinh, phien_ban) VALUES (%s,%s,%s,%s,%s)",
                                   (pn, profile["ma"], profile["ten"], json.dumps(profile, ensure_ascii=False), profile["phien_ban"]))
            elif row[0] != json.loads(json.dumps(profile)):
                raise DataError("PROFILE_DOI_NOI_DUNG", f"Profile {profile['ma']} v{profile['phien_ban']} đã có nội dung khác — tăng phiên bản, không ghi đè.")
            admin_conn.execute("INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s,%s,%s) ON CONFLICT (phap_nhan_id, ma_junsky) DO NOTHING",
                               (pn, du_an, "Dự án " + du_an))
        for ten, mas in DOI_TAC:
            dt = admin_conn.execute("SELECT id FROM master.doi_tac WHERE ghi_chu = %s", ("DEMO_CRM:" + ten,)).fetchone()
            dt = dt[0] if dt else admin_conn.execute("""INSERT INTO master.doi_tac (ten_phap_ly, ten_chuan_hoa, loai, vai_tro, ghi_chu)
                                                        VALUES (%s, master.chuan_hoa_ten(%s), 'TC', '{KH}', %s) RETURNING id""", (ten, ten, "DEMO_CRM:" + ten)).fetchone()[0]
            for pn_ma, obj in mas.items():
                admin_conn.execute("""INSERT INTO master.doi_tac_ma_junsky (doi_tac_id, phap_nhan_id, object_id_junsky, ten_junsky)
                                      VALUES (%s,%s,%s,%s) ON CONFLICT (phap_nhan_id, object_id_junsky) DO NOTHING""", (dt, ids[pn_ma], obj, ten))
        if not _da_khoi_tao(admin_conn):
            for dang_nhap, vai_tro, quyen, modules in NGUOI_DUNG:
                admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                      ON CONFLICT (dang_nhap) DO NOTHING""", (dang_nhap, dang_nhap, vai_tro))
                nd = admin_conn.execute("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()[0]
                for pn_ma, duyet in quyen.items():
                    admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module) VALUES (%s,%s,%s,%s)
                                          ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""", (nd, ids[pn_ma], duyet, modules))
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'v2') ON CONFLICT (key) DO NOTHING", (MARKER,))
    return {k: str(v) for k, v in ids.items()}
