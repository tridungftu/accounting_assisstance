"""Chuẩn bị PostgreSQL DEMO cho CRM-01 khi bấm nút mở DEMO (chỉ môi trường fixture; kho thật không đi qua đây).

Giao diện cấu hình cục bộ (Codex tạo, đặt quyền tệp; Claude/người dùng không gõ DSN):
  tệp JSON `<DataRoot>/crm-demo/ket-noi.local.json` (hoặc đường dẫn trong biến môi trường KTT_CRM_DEMO_KET_NOI):
    {"phien_ban": 1,
     "app_dsn":   "<login thường, thành viên app_web, NOSUPERUSER, NOBYPASSRLS, không sở hữu DB/bảng; host + port + dbname tường minh>",
     "admin_dsn": "<quyền quản trị cục bộ tới CÙNG endpoint + DB — chỉ cho bước chuẩn bị (tạo DB nếu thiếu, migrate, seed) và bộ chiếu M1>"}

Một lớp chuẩn hóa/kiểm DSN dùng chung cho tệp JSON, bootstrap trực tiếp và biến môi trường của server (review khởi động 03):
  - chỉ nhận các khóa host, port, dbname, user, password, sslmode, connect_timeout, application_name — service/servicefile/hostaddr/
    multihost/options… bị từ chối (fail closed, không đọc tệp service);
  - host, port, dbname phải TƯỜNG MINH (không để libpq lấy PGHOST/PGHOSTADDR/PGPORT/PGDATABASE/PGSERVICE); host chỉ một trong
    127.0.0.1 / localhost / ::1; chuỗi dùng để kết nối được dựng lại với hostaddr loopback tường minh (localhost → 127.0.0.1) nên biến
    môi trường không đổi được đích sau khi kiểm;
  - app và admin phải cùng (hostaddr, port, dbname) đã chuẩn hóa; tên DB theo tiền tố DEMO (`kho_crm_demo`) hoặc tiền tố fixture
    kiểm thử được truyền rõ.
Tất cả kiểm xong TRƯỚC mọi connect/CREATE/migrate/seed. Sau khi kết nối, so đích thực (địa chỉ/cổng máy chủ, OID DB) của hai kết nối và
kiểm login ứng dụng không superuser/BYPASSRLS, thuộc app_web, không là (thành viên của) chủ DB/schema/bảng nghiệp vụ.
Mở lại dùng lại cùng DB/hồ sơ/lô. Module này không khởi động/cài cluster (bước bảo đảm cluster ở `ha_tang/pg_cum.py`), không xóa tệp.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from ..ha_tang.primitives import DataError

PHIEN_BAN_KET_NOI = 1
HOSTADDR_LOOPBACK = {"127.0.0.1": "127.0.0.1", "localhost": "127.0.0.1", "::1": "::1"}
KHOA_DSN_CHO_PHEP = frozenset({"host", "port", "dbname", "user", "password", "sslmode", "connect_timeout", "application_name"})
TIEN_TO_DB = ("kho_crm_demo",)
TIEN_TO_DB_KIEM_THU = ("kho_test_",)
_TEN_DB = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
SCHEMA_NGHIEP_VU = ("master", "kho", "nhat_ky", "bao_mat", "giao_tiep")


def duong_dan_ket_noi(root) -> Path:
    return Path(os.environ.get("KTT_CRM_DEMO_KET_NOI") or Path(root) / "crm-demo" / "ket-noi.local.json")


def nap_driver():
    """psycopg của runtime app (runtime.local.json); thiếu → mã sạch thay vì ImportError/đứt HTTP."""
    try:
        import psycopg
    except ImportError:
        raise DataError("RUNTIME_THIEU_DRIVER", "Python đang chạy chưa có driver PostgreSQL (psycopg) — cần runtime app đã cài (crm-demo/runtime.local.json).") from None
    return psycopg


def chuan_hoa_dsn(dsn: str, tien_to=TIEN_TO_DB) -> dict:
    """{host, hostaddr, port, dbname, conninfo} đã kiểm; idempotent: chuan_hoa_dsn(kq["conninfo"]) == kq. Lỗi không chứa nội dung DSN."""
    nap_driver()
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    if not isinstance(dsn, str) or not dsn.strip():
        raise DataError("KET_NOI_SAI_DINH_DANG", "Thiếu chuỗi kết nối CRM DEMO.")
    try:
        d = {k: v for k, v in conninfo_to_dict(dsn).items() if v is not None}
    except Exception:  # noqa: BLE001 — không lộ nội dung DSN
        raise DataError("KET_NOI_SAI_DINH_DANG", "Chuỗi kết nối CRM DEMO không đọc được.") from None
    la = set(d) - KHOA_DSN_CHO_PHEP - {"hostaddr"}
    if la:
        raise DataError("KET_NOI_KHOA_KHONG_HO_TRO", "Chuỗi kết nối có tham số không được hỗ trợ (" + ", ".join(sorted(la)) + ").")
    host, port, db = str(d.get("host") or ""), str(d.get("port") or ""), str(d.get("dbname") or "")
    if not host or not port or not db:
        raise DataError("KET_NOI_THIEU_ENDPOINT", "Chuỗi kết nối phải ghi rõ host, port và dbname (không lấy từ môi trường/service).")
    if "," in host or "," in port or host.lower() not in HOSTADDR_LOOPBACK:
        raise DataError("KET_NOI_KHONG_LOCAL", "CRM DEMO chỉ kết nối một PostgreSQL trên chính máy này (127.0.0.1 / localhost / ::1).")
    # Idempotent trên đầu ra của chính hàm này: hostaddr chỉ nhận đúng literal loopback mà host đã ghi chuẩn hóa thành
    # (127.0.0.1→127.0.0.1, localhost→127.0.0.1, ::1→::1). Hostaddr khác/remote/nhiều địa chỉ vẫn bị từ chối như trước.
    if "hostaddr" in d and str(d["hostaddr"]) != HOSTADDR_LOOPBACK[host.lower()]:
        raise DataError("KET_NOI_KHOA_KHONG_HO_TRO", "hostaddr chỉ được là địa chỉ loopback khớp đúng host đã ghi.")
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise DataError("KET_NOI_SAI_DINH_DANG", "Cổng PostgreSQL không hợp lệ.")
    if not _TEN_DB.match(db) or not db.startswith(tuple(tien_to)):
        raise DataError("KET_NOI_DB_KHONG_DEMO", "Tên cơ sở dữ liệu không phải DB CRM DEMO đã định danh.")
    hostaddr = HOSTADDR_LOOPBACK[host.lower()]
    khac = {k: d[k] for k in sorted(d) if k not in ("host", "hostaddr", "port", "dbname")}  # thứ tự cố định → đầu ra idempotent
    conninfo = make_conninfo("", **{"host": host.lower(), "hostaddr": hostaddr, "port": str(int(port)), "dbname": db, **khac})
    return {"host": host.lower(), "hostaddr": hostaddr, "port": int(port), "dbname": db, "conninfo": conninfo}


def kiem_dsn(dsn: str, tien_to=TIEN_TO_DB) -> str:
    return chuan_hoa_dsn(dsn, tien_to)["dbname"]


def kiem_cap(app_dsn: str, admin_dsn: str | None, tien_to=TIEN_TO_DB) -> dict:
    """Kiểm cả hai DSN và cùng đích (hostaddr, port, dbname) TRƯỚC mọi kết nối."""
    app = chuan_hoa_dsn(app_dsn, tien_to)
    admin = chuan_hoa_dsn(admin_dsn, tien_to) if admin_dsn else None
    if admin and (admin["dbname"] != app["dbname"]):
        raise DataError("KET_NOI_KHAC_DB", "Hai kết nối CRM DEMO phải cùng một DB.")
    if admin and (admin["hostaddr"], admin["port"]) != (app["hostaddr"], app["port"]):
        raise DataError("KET_NOI_KHAC_ENDPOINT", "Hai kết nối CRM DEMO phải cùng một máy chủ PostgreSQL (địa chỉ + cổng).")
    return {"db": app["dbname"], "endpoint": (app["hostaddr"], app["port"]), "app": app, "admin": admin}


def doc_ket_noi(path, tien_to=TIEN_TO_DB) -> dict:
    path = Path(path)
    if not path.is_file():
        raise DataError("CRM_CHUA_CAU_HINH", "Chưa có cấu hình kết nối CRM DEMO cục bộ (do Codex/cài đặt chuẩn bị).")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise DataError("KET_NOI_SAI_DINH_DANG", "Tệp cấu hình kết nối CRM DEMO không đọc được.") from None
    if not isinstance(value, dict) or set(value) - {"phien_ban", "app_dsn", "admin_dsn"} or value.get("phien_ban") != PHIEN_BAN_KET_NOI \
            or not isinstance(value.get("app_dsn"), str) or not isinstance(value.get("admin_dsn", ""), str):
        raise DataError("KET_NOI_SAI_DINH_DANG", "Tệp cấu hình kết nối CRM DEMO sai định dạng (phien_ban 1, app_dsn, admin_dsn).")
    cap = kiem_cap(value["app_dsn"], value.get("admin_dsn") or None, tien_to)
    return {"db": cap["db"], "endpoint": cap["endpoint"], "app_dsn": cap["app"]["conninfo"],
            "admin_dsn": cap["admin"]["conninfo"] if cap["admin"] else None}


def _dong(row) -> list:
    return list(row.values()) if isinstance(row, dict) else list(row)


def dich_thuc(conn) -> tuple:
    """Đích thực của một kết nối đã mở: (địa chỉ máy chủ, cổng, OID DB, tên DB)."""
    return tuple(_dong(conn.execute("""SELECT host(inet_server_addr()) AS dia_chi, inet_server_port() AS cong,
                                       (SELECT oid FROM pg_database WHERE datname = current_database())::bigint AS db_oid, current_database()::text AS db""").fetchone()))


def kiem_role_ung_dung(conn) -> dict:
    """Login ứng dụng phải là role thường: không superuser, không BYPASSRLS, thuộc app_web, không là/không thuộc chủ DB, schema hay bảng
    nghiệp vụ (chủ bảng bỏ qua RLS)."""
    # mọi cột có alias riêng: kết nối dùng dict_row sẽ gộp cột trùng tên
    vals = _dong(conn.execute("""SELECT current_user::text AS ten, current_database()::text AS db, r.rolsuper AS sup, r.rolbypassrls AS byp,
                                        pg_has_role(current_user, 'app_web', 'MEMBER') AS app_web,
                                        (SELECT pg_has_role(current_user, d.datdba, 'MEMBER') FROM pg_database d WHERE d.datname = current_database()) AS chu_db,
                                        (SELECT count(*) FROM pg_namespace n WHERE n.nspname = ANY(%s) AND pg_has_role(current_user, n.nspowner, 'MEMBER')) AS chu_schema,
                                        (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                          WHERE n.nspname = ANY(%s) AND pg_has_role(current_user, c.relowner, 'MEMBER')) AS chu_bang
                                 FROM pg_roles r WHERE r.rolname = current_user""", (list(SCHEMA_NGHIEP_VU), list(SCHEMA_NGHIEP_VU))).fetchone())
    info = {"ten": vals[0], "db": vals[1], "superuser": bool(vals[2]), "bypassrls": bool(vals[3]), "app_web": bool(vals[4]),
            "chu_db": bool(vals[5]), "chu_schema": int(vals[6] or 0), "chu_bang": int(vals[7] or 0)}
    if info["superuser"] or info["bypassrls"] or not info["app_web"]:
        raise DataError("ROLE_UNG_DUNG_SAI", "Login ứng dụng CRM phải là role thường thuộc app_web, không superuser/BYPASSRLS.")
    if info["chu_db"] or info["chu_schema"] or info["chu_bang"]:
        raise DataError("ROLE_UNG_DUNG_LA_CHU", "Login ứng dụng CRM không được là (thành viên của) chủ DB/schema/bảng nghiệp vụ.")
    return info


def kiem_ket_noi_chu(chu, app) -> dict:
    """Kết nối máy chủ (chủ bảng) cho intake/FILE_SOAT M5: DSN đã qua cùng validator loopback/endpoint (kiem_cap) TRƯỚC khi kết nối; sau kết nối
    kiểm đích thực (địa chỉ/cổng/OID DB) trùng login ứng dụng và current_user ĐÚNG là chủ các bảng stage/typed (không suy từ membership/GUC).
    Không log/trả DSN; không dùng cho route đọc thường."""
    if dich_thuc(chu) != dich_thuc(app):
        raise DataError("KET_NOI_KHAC_DB", "Kết nối máy chủ không trỏ đúng máy chủ/DB của login ứng dụng.")
    # mỗi cột một alias riêng và đọc theo tên cột (tuple hoặc dict_row): dict_row gộp cột trùng tên → phải không thể trùng
    row = _theo_ten(chu.execute("""SELECT current_user::text AS hien_tai,
                                      (SELECT pg_get_userbyid(c.relowner)::text FROM pg_class c WHERE c.oid = 'giao_tiep.stage_tin_cay'::regclass) AS chu_stage,
                                      (SELECT pg_get_userbyid(c.relowner)::text FROM pg_class c WHERE c.oid = 'kho.phieu_kho_danh_tinh'::regclass) AS chu_phieu,
                                      (SELECT pg_get_userbyid(c.relowner)::text FROM pg_class c WHERE c.oid = 'kho.lo_xuat'::regclass) AS chu_lo""").fetchone(),
                    _COT_CHU)
    if row["hien_tai"] is None or not (row["hien_tai"] == row["chu_stage"] == row["chu_phieu"] == row["chu_lo"]):
        raise DataError("KET_NOI_CHU_SAI", "Kết nối máy chủ không phải đúng chủ bảng stage/typed/registry lô.")
    return {"chu": row["hien_tai"]}


_COT_CHU = ("hien_tai", "chu_stage", "chu_phieu", "chu_lo")


def _theo_ten(row, cot: tuple) -> dict:
    """Đọc một dòng kết quả theo đúng danh sách cột: dict_row phải có đủ đúng các khóa; tuple phải đúng số cột. Sai dạng → lỗi rõ, không IndexError."""
    if isinstance(row, dict):
        if set(row) != set(cot):
            raise DataError("KET_NOI_CHU_SAI", "Kết quả kiểm chủ bảng sai cấu trúc cột.")
        return {k: row[k] for k in cot}
    vals = list(row) if row is not None else []
    if len(vals) != len(cot):
        raise DataError("KET_NOI_CHU_SAI", "Kết quả kiểm chủ bảng sai cấu trúc cột.")
    return dict(zip(cot, vals))


def chuan_bi(ket_noi: dict, tien_to=TIEN_TO_DB) -> dict:
    """Kiểm cặp DSN (trước mọi side effect) → tạo DB DEMO nếu thiếu, migrate + seed bằng quyền quản trị → kiểm đích thực + login ứng dụng.
    Trả trạng thái không chứa bí mật."""
    if not ket_noi.get("admin_dsn"):
        raise DataError("CRM_CHUA_CAU_HINH_QUAN_TRI", "Thiếu kết nối quản trị cục bộ cho bước chuẩn bị CRM DEMO.")
    cap = kiem_cap(ket_noi.get("app_dsn"), ket_noi["admin_dsn"], tien_to)  # cả hai DSN, cùng đích — trước connect/CREATE/migrate/seed
    psycopg = nap_driver()
    from psycopg.conninfo import make_conninfo
    from ..ha_tang import postgres as pg
    from ..ha_tang.pg_migrations import PG_SCHEMA_VERSION
    from . import crm_demo, crm_g_demo, l11_demo, m2_demo, m4_demo, m5_demo, mtq_demo
    db, admin_ci, app_ci = cap["db"], cap["admin"]["conninfo"], cap["app"]["conninfo"]
    tao_moi = False
    try:
        admin = psycopg.connect(admin_ci, autocommit=True)
    except psycopg.OperationalError as exc:
        if getattr(exc, "sqlstate", None) != "3D000" and "does not exist" not in str(exc):
            raise DataError("PG_KHONG_KET_NOI", "Không kết nối được PostgreSQL DEMO trên máy (dịch vụ chưa chạy hoặc cấu hình chưa đúng).") from None
        with psycopg.connect(make_conninfo(admin_ci, dbname="postgres"), autocommit=True) as boot:
            boot.execute(f'CREATE DATABASE "{db}" ENCODING \'UTF8\' TEMPLATE template0')  # tên đã kiểm regex + tiền tố DEMO
        tao_moi = True
        admin = psycopg.connect(admin_ci, autocommit=True)
    try:
        dich_admin = dich_thuc(admin)
        truoc = pg.schema_version(admin)
        # SR5: migrate (lineage kiểm trước DDL) + khởi tạo DEMO MỘT LẦN; mở lại chỉ thêm, giữ nguyên vai trò/quyền/module/thu hồi hiện hành,
        # không UPSERT/cấp lại quyền đã thu hồi, không cấp/chạy M9
        ids = crm_demo.khoi_tao(admin)
        m5 = m5_demo.khoi_tao(admin)
        m2 = m2_demo.khoi_tao(admin)  # R15: chỉ thêm, một lần; không đổi actor/quyền/thu hồi M5
        l11 = l11_demo.khoi_tao(admin)  # R16: cấu hình/raw + 2 actor một lần; không approval/pool/child, không regrant M2/M5
        # M4-01C: dự án/actor MO_PHONG_ M4 + phạm vi dự án MỘT LẦN (m4_demo giữ thu hồi, không cấp lại); trả nguyên trạng thái DU/THIEU/
        # CHUA_SAN_SANG/DA_THU_HOI để chẩn đoán — không đổi thành DU, không chặn CRM/M2/M5/L11 khi M4 chưa đủ
        m4 = m4_demo.khoi_tao(admin)
        # CRM-41-02: actor MO_PHONG_CRM_G_* + danh mục G1 + phân công CRM_MAU_TAI MỘT LẦN theo literal DEMO; không seed mẫu/duyệt/bộ chuẩn/K5;
        # trạng thái DU/THIEU/DA_THU_HOI/XUNG_DOT/CHUA_SAN_SANG trả nguyên để chẩn đoán, không chặn CRM/M2/M4/M5/L11
        crm_g = crm_g_demo.khoi_tao(admin)
        # MTQ-5a: cùng bootstrap DEMO đã kiểm cặp DSN, sau master CRM/M4.
        # Seed lỗi rollback riêng và ghi log, không chặn các module đã sẵn sàng.
        try:
            mtq = mtq_demo.khoi_tao(admin, demo=True)
        except Exception as exc:  # noqa: BLE001 — không đưa nội dung lỗi/DSN vào log
            logging.getLogger(__name__).warning("Seed MTQ DEMO lỗi (%s); CRM tiếp tục khởi động.", type(exc).__name__)
            mtq = {"trang_thai": "LOI", "can_anh": "Kiểm tra seed MTQ DEMO bằng kết nối chủ bảng."}
        else:
            if mtq["trang_thai"] not in ("DU", "DA_SEED"):
                logging.getLogger(__name__).warning("Seed MTQ DEMO: %s", mtq["trang_thai"])
        sau = pg.schema_version(admin)
        profile = [f"{r[0]}@v{r[1]}" for r in admin.execute("""SELECT l.ma, l.phien_ban FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                                               WHERE p.ma LIKE 'PN_DEMO_%' AND l.valid_to IS NULL ORDER BY 1""")]
    finally:
        admin.close()
    with psycopg.connect(app_ci, autocommit=True) as app:
        if dich_thuc(app) != dich_admin:
            raise DataError("KET_NOI_KHAC_DB", "Login ứng dụng không trỏ đúng máy chủ/DB của bước chuẩn bị.")
        role = kiem_role_ung_dung(app)
        ver = pg.kiem_lineage_ung_dung(app)  # đúng lineage mặc định + bản mới nhất, không chỉ max(version)
    if sau != PG_SCHEMA_VERSION or ver != PG_SCHEMA_VERSION:
        raise DataError("CRM_SCHEMA_KHONG_KHOP", "Phiên bản schema CRM DEMO không khớp phần mềm.")
    return {"trang_thai": "SAN_SANG", "db": db, "endpoint": f"{cap['endpoint'][0]}:{cap['endpoint'][1]}", "tao_db_moi": tao_moi,
            "schema_truoc": truoc, "schema_sau": sau, "phap_nhan": sorted(ids), "profile": profile, "m5_seed": m5, "m2_seed": m2, "l11_seed": l11, "m4_seed": m4, "crm_g_seed": crm_g,
            "mtq_seed": mtq, "role_ung_dung": {k: role[k] for k in ("ten", "superuser", "bypassrls", "app_web", "chu_db")}}
