#!/usr/bin/env python3
"""Bước chuẩn bị CRM DEMO do `start-web.ps1` gọi khi mở bản DEMO (không gọi khi mở kho thật).

Dùng: python -X utf8 tools/chuan_bi_crm_demo.py --config <cau_hinh.toml> --root <DataRoot>
- environment = that → BO_QUA (mã 0), không đọc cấu hình kết nối, không đụng cluster.
- Có cấu hình: kiểm cả hai DSN → bảo đảm cluster PostgreSQL ĐÃ CÓ chạy (ha_tang/pg_cum.py: dùng lại đúng cluster hoặc pg_ctl start
  cluster đang dừng; không stop/kill/xóa/initdb/cài) → tạo DB nếu thiếu, migrate, seed, kiểm login ứng dụng.
  Seed gồm cả duyệt viên M4 DEMO (`m4_demo.khoi_tao_duyet`, L0-7: một lần, chỉ DB DEMO; lỗi bước này chỉ ghi `m4_duyet_seed`, không chặn mở DEMO)
  và dự án đang bán DEMO (`crm_du_an_ban.khoi_tao_demo`, DA-1: qua hàm lệnh M0031, idempotent; lỗi chỉ ghi `du_an_ban_seed`).
- Chưa có tệp kết nối cục bộ → CHUA_CAU_HINH (mã 2): app vẫn mở, trang CRM báo chưa cấu hình.
- Lỗi → mã 3, chỉ thông điệp đã làm sạch (không DSN/mật khẩu/giá trị dòng).
Mỗi lần chạy ghi một tệp trạng thái RIÊNG `<root>/crm-demo/chuan-bi-<UTC>-<pid>.json` (không ghi đè, không xóa tệp cũ) và in đúng một
dòng JSON trạng thái (không bí mật) cho launcher.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.ha_tang.config import Config  # noqa: E402
from kho_tri_thuc.ha_tang.ket_noi import loi_sach  # noqa: E402
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json  # noqa: E402
from kho_tri_thuc.ha_tang.store import write_immutable  # noqa: E402
from kho_tri_thuc.ha_tang.pg_cum import bao_dam_cum, doc_cum  # noqa: E402
from kho_tri_thuc.k2.crm_khoi_dong import chuan_bi, chuan_hoa_dsn, doc_ket_noi, duong_dan_ket_noi, nap_driver  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def bo_sung_duyet_vien_m4(kn: dict) -> dict:
    """L0-7: seed DEMO (`crm_khoi_dong.chuan_bi`) chỉ gọi `m4_demo.khoi_tao` nên DEMO thiếu duyệt viên M4 (MO_PHONG_DUYET_M4, vai dự án DUYET).
    Gọi tường minh `m4_demo.khoi_tao_duyet` (một lần, chỉ thêm, có marker — chạy lại không thêm gì; không cấp lại quyền đã thu hồi).
    CHỈ DB DEMO: chỉ gọi sau `chay` đã loại kho thật (`environment = that` → BO_QUA) và sau `chuan_bi` thành công; DSN quản trị được kiểm lại là
    loopback + tên DB có tiền tố DEMO (`chuan_hoa_dsn`) TRƯỚC khi kết nối. Không bao giờ ném lỗi: thất bại chỉ ghi trạng thái (DEMO vẫn mở như M4 chưa đủ)."""
    from kho_tri_thuc.k2 import m4_demo
    try:
        admin_dsn = kn.get("admin_dsn")
        if not admin_dsn:
            return {"trang_thai": "BO_QUA", "ly_do": "Không có kết nối quản trị cục bộ."}
        conninfo = chuan_hoa_dsn(admin_dsn)["conninfo"]       # DB DEMO + loopback, kiểm lại ngay trước khi kết nối
        psycopg = nap_driver()
        admin = psycopg.connect(conninfo, autocommit=True)
        try:
            kq = m4_demo.khoi_tao_duyet(admin)
        finally:
            admin.close()
        return {"trang_thai": kq.get("trang_thai"), "ly_do": kq.get("ly_do"), "dem": kq.get("dem"), "mo_lai_khong_them": kq.get("mo_lai_khong_them")}
    except Exception as exc:  # noqa: BLE001 — biên CLI: chỉ lỗi đã làm sạch, không chặn mở DEMO
        return {"trang_thai": "LOI", **loi_sach(exc)}


def bo_sung_du_an_ban(kn: dict) -> dict:
    """DA-1: seed DEMO dự án đang bán (`crm_du_an_ban.khoi_tao_demo`: 2 dự án DEMO, phí khác đơn vị tính, lô/căn, tiến độ tiêu chuẩn áp dụng ngay).
    QD-20261025-20: giá/phí chưa VAT, thuế suất 10; KCN trừ đất 24/120 USD/m², nhà ở trừ đất 0 VND/m².
    QUA CHÍNH hàm lệnh M0031 dưới danh tính bán hàng DEMO, khóa idempotent cố định (mở lại → replay, không thêm phiên bản). CHỈ DB DEMO: DSN quản
    trị kiểm lại là loopback + tiền tố DEMO (`chuan_hoa_dsn`) trước khi kết nối. Không bao giờ ném lỗi: thất bại chỉ ghi trạng thái."""
    from kho_tri_thuc.k2 import crm_du_an_ban
    try:
        admin_dsn = kn.get("admin_dsn")
        if not admin_dsn:
            return {"trang_thai": "BO_QUA", "ly_do": "Không có kết nối quản trị cục bộ."}
        conninfo = chuan_hoa_dsn(admin_dsn)["conninfo"]
        psycopg = nap_driver()
        admin = psycopg.connect(conninfo, autocommit=True)
        try:
            kq = crm_du_an_ban.khoi_tao_demo(admin)
        finally:
            admin.close()
        return {"trang_thai": kq.get("trang_thai"), "ly_do": kq.get("ly_do"), "du_an": kq.get("du_an")}
    except Exception as exc:  # noqa: BLE001 — biên CLI: chỉ lỗi đã làm sạch, không chặn mở DEMO
        return {"trang_thai": "LOI", **loi_sach(exc)}


def chuan_bi_day_du(kn: dict) -> dict:
    """Bootstrap mặc định của `chay`: seed DEMO chuẩn rồi bổ sung duyệt viên M4 (L0-7) và dự án đang bán DEMO (DA-1, chỉ khi bước chuẩn bị đã
    migrate xong — có `schema_sau`)."""
    kq = chuan_bi(kn)
    kq["m4_duyet_seed"] = bo_sung_duyet_vien_m4(kn)
    kq["du_an_ban_seed"] = (bo_sung_du_an_ban(kn) if isinstance(kq.get("schema_sau"), int)
                            else {"trang_thai": "BO_QUA", "ly_do": "Bước chuẩn bị CRM chưa báo schema đã migrate."})
    return kq


def chay(config_path: Path, root: Path, *, hdh=None, bootstrap=None, thu_muc_khoa: Path | None = None, repo_root: Path = REPO_ROOT) -> tuple[int, dict]:
    """Thứ tự: kho thật → bỏ qua hoàn toàn; kiểm cấu hình kết nối (cả hai DSN, không side effect); kiểm đích kết nối = cluster đã định
    danh; bảo đảm cluster đã có đang chạy (dùng lại/khởi động, không dừng/xóa gì); rồi mới tạo DB/migrate/seed."""
    import tempfile
    if Config.load(config_path).environment == "that":
        return 0, {"trang_thai": "BO_QUA_KHO_THAT"}
    path = duong_dan_ket_noi(root)
    try:
        kn = doc_ket_noi(path)
        cum = doc_cum(root, repo_root)
        if kn["endpoint"] != (cum.host, cum.port):
            raise DataError("KET_NOI_KHONG_DUNG_CUM", "Cấu hình kết nối CRM DEMO không trỏ đúng cluster PostgreSQL đã định danh.")
        cum_kq = bao_dam_cum(cum, Path(root) / "logs", thu_muc_khoa or Path(tempfile.gettempdir()) / "kho-tri-thuc", hdh=hdh)
        return 0, {**(bootstrap or chuan_bi_day_du)(kn), "cum": cum_kq}
    except DataError as exc:
        return (2 if exc.code == "CRM_CHUA_CAU_HINH" else 3), {"trang_thai": "CHUA_CAU_HINH" if exc.code == "CRM_CHUA_CAU_HINH" else "LOI",
                                                              "ma": exc.code, "thong_diep": str(exc)}
    except Exception as exc:  # noqa: BLE001 — biên CLI: chỉ lỗi đã làm sạch
        return 3, {"trang_thai": "LOI", **loi_sach(exc)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--root", required=True, type=Path)
    args = ap.parse_args(argv)
    code, status = chay(args.config.resolve(), args.root.resolve())
    status = {"luc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ma_thoat": code, **status}
    if status.get("trang_thai") != "BO_QUA_KHO_THAT":
        name = f"chuan-bi-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{os.getpid()}.json"
        try:
            write_immutable(args.root.resolve() / "crm-demo" / name, canonical_json(status).encode("utf-8"))
            status["tep_trang_thai"] = name
        except (OSError, DataError):
            status["tep_trang_thai"] = None
    print(json.dumps(status, ensure_ascii=True))  # JSON máy qua Windows PowerShell 5.1: chỉ ASCII (\uXXXX); tệp trạng thái UTF-8 giữ chữ Việt
    return code


if __name__ == "__main__":
    raise SystemExit(main())
