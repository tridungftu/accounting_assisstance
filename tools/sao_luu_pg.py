"""V13 — sao lưu một kho V12 trên PostgreSQL (schema v12_*) ra **bản DB legacy dự phòng**: thư mục bundle ``<ten>/`` gồm
``<ten>.sqlite`` + ``<ten>.sqlite.sha256``.

Đây là đường lùi DB-only "engine = sqlite" (TL 39): KHÔNG phải backup đầy đủ (không gồm raw/artifact/config ngoài DB) và không
phải backup K2 (nhãn ``LEGACY_DB_FALLBACK``).
- Nguồn mở CHỈ ĐỌC, không migrate/bootstrap: lịch sử phải đúng và đúng phiên bản hiện hành; nguồn cũ/lạ bị từ chối (F5).
- Chép + đối chiếu nội dung độc lập (giá trị có kiểu + rowid thực, đọc lại tệp vừa chép bằng kết nối chỉ đọc riêng) trên CÙNG một
  ảnh chụp PostgreSQL: người ghi hợp lệ commit giữa chừng không làm hỏng/chặn sai bản sao lưu (F3, F4).
- Công bố (F2): staging ``<ten>.partial-<uuid>/`` tạo độc quyền; trong đó DB tạo độc quyền, integrity + đối chiếu, checkpoint, rồi
  SHA tính + ghi độc quyền + đọc lại kiểm TRƯỚC khi công bố; công bố = MỘT lần đổi tên thư mục staging → ``<ten>/`` (đích tồn tại →
  lỗi, không ghi đè). Lỗi ở bất kỳ bước nào: không có bản công bố một nửa; biên nhận lỗi liệt kê đúng tệp/thư mục còn lại.
- Không ghi đè, không xóa, không di chuyển/xoay vòng bản cũ hay partial cũ; ``--giu`` chỉ được nhận để tương thích và báo không áp dụng.
- Lỗi: in JSON đã làm sạch (mã/sqlstate, không DSN/dòng/traceback), exit 2.
    python tools/sao_luu_pg.py --schema v12_thu_t8 --thu-muc var/sao-luu-pg
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.ha_tang import database, postgres as pg  # noqa: E402
from kho_tri_thuc.ha_tang.ket_noi import KetNoiPG, kiem_ten_schema, loi_sach  # noqa: E402
from kho_tri_thuc.ha_tang.primitives import DataError, sha256  # noqa: E402
from kho_tri_thuc.ha_tang.sao_chep_bang import _cot_pg, chep_pg_sang_sqlite, doi_chieu_noi_dung, van_tay_pg  # noqa: E402

LOAI = "LEGACY_DB_FALLBACK"
MO_TA = "Bản DB legacy dự phòng (đường lùi engine=sqlite) — không phải backup đầy đủ/K2/artifact"


def _tao_doc_quyen(path: Path) -> None:
    with open(path, "xb"):  # tạo mới độc quyền: tồn tại → FileExistsError, không mở lại tệp cũ/partial
        pass


def _kiem_noi_dung(raw, schema: str, db: Path) -> dict:
    """Đối chiếu độc lập trong ảnh chụp PG của lần chép: hash giá trị có kiểu + rowid từng bảng tính lại từ PostgreSQL và từ tệp
    SQLite vừa chép (kết nối CHỈ ĐỌC riêng, không dùng kết nối đã ghi)."""
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as doc:
        return doi_chieu_noi_dung(doc, van_tay_pg(raw, schema), lambda t: _cot_pg(raw, schema, t))


def _ghi_sha(staging: Path, db: Path) -> str:
    """SHA-256 của DB đã đóng: ghi độc quyền rồi đọc lại cả DB lẫn SHA để kiểm — trước khi công bố."""
    digest = sha256(db.read_bytes())
    sha_path = staging / (db.name + ".sha256")
    with open(sha_path, "x", encoding="utf-8") as f:
        f.write(digest + "  " + db.name + "\n")
    if sha_path.read_text(encoding="utf-8").split()[0] != digest or sha256(db.read_bytes()) != digest:
        raise DataError("BACKUP_SHA", "SHA-256 vừa ghi không khớp DB — không công bố.")
    return digest


def _cong_bo(staging: Path, final: Path, trang: dict) -> None:
    """Công bố nguyên tử bundle của chính lần chạy: một lần đổi tên thư mục (Windows: đích tồn tại → lỗi, không ghi đè).
    ``trang`` ghi trạng thái CỦA LẦN CHẠY NÀY: chỉ ``da_cong_bo=True`` sau khi rename của chính nó hoàn tất; final có sẵn do bên khác
    tạo → ``final_ben_khac=True`` (không nhận sở hữu, không đụng tới). Bên khác có thể tạo final SAU precheck: chính ``os.rename``
    (Windows từ chối đích tồn tại) ném ``FileExistsError`` → cùng xử lý va chạm. Mọi OSError khác giữ nguyên lỗi gốc, không quy thành va
    chạm; trạng thái công bố ghi UNKNOWN (không suy final vắng/của ai). Không thử lại, không ghi đè/di chuyển/xóa gì."""
    if final.exists():
        trang["final_ben_khac"], trang["trang_thai_cong_bo"] = True, "VA_CHAM_BEN_KHAC"
        raise DataError("DESTINATION_EXISTS", "Tên bản sao lưu vừa được tạo bởi tiến trình khác; không ghi đè.")
    try:
        os.rename(staging, final)
    except FileExistsError:
        trang["final_ben_khac"], trang["trang_thai_cong_bo"] = True, "VA_CHAM_BEN_KHAC"
        raise DataError("DESTINATION_EXISTS", "Tên bản sao lưu được tạo bởi tiến trình khác ngay trước khi công bố; không ghi đè.") from None
    except OSError:
        trang["trang_thai_cong_bo"] = "UNKNOWN"
        raise
    trang["da_cong_bo"], trang["trang_thai_cong_bo"] = True, "DA_CONG_BO"


def _liet_ke(p: Path) -> list[str]:
    return sorted(c.name for c in p.iterdir())


def _ma_loi(e: BaseException) -> str:
    code = getattr(e, "code", None)
    return f"{type(e).__name__}:{code}" if isinstance(code, str) and code.isupper() else type(e).__name__


def _bien_nhan(staging: Path, final: Path, trang: dict) -> dict:
    """Biên nhận lỗi trung thực cho tài sản CỦA LẦN CHẠY NÀY: phần đã xác nhận tồn tại (``con_lai``) tách khỏi phần không đọc được
    metadata (``khong_xac_dinh`` + ``kiem_ke=UNKNOWN``); không suy "không có" từ việc không quan sát được. Final của bên khác không liệt kê."""
    out = {"da_cong_bo": bool(trang.get("da_cong_bo")), "final_ben_khac": bool(trang.get("final_ben_khac")),
           "trang_thai_cong_bo": trang.get("trang_thai_cong_bo", "CHUA_CONG_BO"), "partial_giu_lai": None,
           "con_lai": [], "khong_xac_dinh": [], "kiem_ke": "DAY_DU", "kiem_ke_loi": []}
    if out["trang_thai_cong_bo"] == "UNKNOWN":  # rename lỗi không phải va chạm: không khẳng định final vắng hay của ai
        out["khong_xac_dinh"].append(final.name + "/")
    cua_minh = [staging] + ([final] if out["da_cong_bo"] else [])
    for p in cua_minh:
        try:
            co = p.exists()
        except OSError as e:
            out["khong_xac_dinh"].append(p.name + "/")
            out["kiem_ke_loi"].append(_ma_loi(e))
            continue
        if not co:
            continue
        out["con_lai"].append(p.name + "/")
        if p == staging:
            out["partial_giu_lai"] = staging.name
        try:
            out["con_lai"] += [f"{p.name}/{n}" for n in _liet_ke(p)]
        except OSError as e:
            out["khong_xac_dinh"].append(p.name + "/*")
            out["kiem_ke_loi"].append(_ma_loi(e))
    if out["khong_xac_dinh"]:
        out["kiem_ke"] = "UNKNOWN"
    return out


def sao_luu(dsn: str, schema: str, thu_muc: Path) -> dict:
    thu_muc.mkdir(parents=True, exist_ok=True)
    ten = f"{schema}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:12]}"
    final, staging = thu_muc / ten, thu_muc / f"{ten}.partial-{uuid.uuid4().hex}"
    if final.exists():
        raise DataError("DESTINATION_EXISTS", "Tên bản sao lưu đã tồn tại; không ghi đè.")
    staging.mkdir()  # độc quyền: tồn tại → FileExistsError
    trang = {"da_cong_bo": False, "final_ben_khac": False}
    try:
        return _chep_kiem_cong_bo(dsn, schema, staging, final, ten, trang)
    except Exception as exc:
        try:  # kiểm kê không được thay lỗi gốc; giữ nguyên mọi tệp để điều tra (không xóa)
            exc.bien_nhan = _bien_nhan(staging, final, trang)
        except Exception as e2:  # noqa: BLE001
            exc.bien_nhan = {"da_cong_bo": bool(trang.get("da_cong_bo")), "final_ben_khac": bool(trang.get("final_ben_khac")),
                             "trang_thai_cong_bo": trang.get("trang_thai_cong_bo", "CHUA_CONG_BO"), "partial_giu_lai": "UNKNOWN", "con_lai": [], "khong_xac_dinh": [staging.name + "/"], "kiem_ke": "UNKNOWN",
                             "kiem_ke_loi": [_ma_loi(e2)]}
        raise


def _chep_kiem_cong_bo(dsn: str, schema: str, staging: Path, final: Path, ten: str, trang: dict) -> dict:
    db = staging / f"{ten}.sqlite"
    _tao_doc_quyen(db)
    conn = KetNoiPG.mo_nguon_sao_luu(dsn, schema)  # chỉ đọc: không migrate/bootstrap nguồn
    doi_chieu = {}
    try:
        dst = database.connect(db)  # tệp rỗng vừa tạo độc quyền → khởi tạo kho V12 mới (guard chép kiểm lại là kho mới)
        try:
            ket_qua = chep_pg_sang_sqlite(conn, dst, kiem_trong_anh_chup=lambda raw: doi_chieu.update(_kiem_noi_dung(raw, schema, db)))
            ok = database.integrity(dst)["ok"]
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dst.execute("PRAGMA journal_mode=DELETE")  # tệp tự chứa; SQLite tự xử lý WAL của chính nó (công cụ không unlink)
        finally:
            dst.close()
    finally:
        conn.close()
    lech = sorted(t for t, v in doi_chieu.items() if not v["khop"])
    khop_dem = all(v["nguon"] == v["dich"] for v in ket_qua.values())
    if not doi_chieu or lech or not khop_dem or not ok:
        raise DataError("BACKUP_VERIFY", f"Bản chép chưa khớp nguồn (bảng lệch: {len(lech)}, integrity: {ok}) — giữ thư mục partial, không công bố.")
    digest = _ghi_sha(staging, db)
    _cong_bo(staging, final, trang)
    return {"schema": schema, "loai": LOAI, "mo_ta": MO_TA, "thu_muc_ban": final.name, "file": f"{final.name}/{db.name}",
            "sha256": digest, "so_bang": len(ket_qua), "tong_dong": sum(v["dich"] for v in ket_qua.values()),
            "bang_doi_chieu_noi_dung": len(doi_chieu), "khop": True, "integrity": ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="v12_thu_t8")
    ap.add_argument("--dsn-key", default="KHO_PG_DSN_ADMIN")
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--thu-muc", type=Path, required=True)
    ap.add_argument("--giu", type=int, default=None, help="(giữ để tương thích) KHÔNG áp dụng: công cụ không xoay vòng/dọn bản cũ")
    args = ap.parse_args(argv)
    import psycopg

    try:
        kiem_ten_schema(args.schema)
        dsn = args.dsn or pg.dsn_from_env(None, key=args.dsn_key)
        with psycopg.connect(dsn, autocommit=True) as raw:
            if not raw.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (args.schema,)).fetchone():
                print(json.dumps({"schema": args.schema, "bo_qua": "chưa có schema"}, ensure_ascii=False))
                return 0
        out = sao_luu(dsn, args.schema, args.thu_muc)
    except Exception as exc:  # noqa: BLE001 — biên CLI: chỉ lỗi đã làm sạch + biên nhận tệp
        # lỗi trước khi tạo staging: chưa có tài sản nào của lần chạy này (kiem_ke=KHONG_AP_DUNG)
        bien_nhan = getattr(exc, "bien_nhan", {"partial_giu_lai": None, "da_cong_bo": False, "final_ben_khac": False,
                                               "trang_thai_cong_bo": "CHUA_CONG_BO", "con_lai": [],
                                               "khong_xac_dinh": [], "kiem_ke": "KHONG_AP_DUNG", "kiem_ke_loi": []})
        print(json.dumps({"schema": args.schema, "ok": False, "loai": LOAI, **bien_nhan, **loi_sach(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.giu is not None:
        out["giu"] = {"yeu_cau": args.giu, "ap_dung": False, "ly_do": "Không xoay vòng/dọn bản cũ; mọi bản sao lưu được giữ nguyên."}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
