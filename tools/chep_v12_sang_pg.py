"""V13 bước 5 — nạp một kho V12 (kho.sqlite) vào schema PostgreSQL để lõi V12 chạy trên engine postgres.

Khác với ``chuyen_sqlite_sang_pg.py`` (bóc sang schema K2 ``master/kho/nhat_ky``), tool này chép **nguyên trạng**
50 bảng V12 vào schema riêng (mặc định ``v12``) và cấp quyền cho vai trò ứng dụng. Chạy bằng DSN chủ CSDL
(``KHO_PG_DSN_ADMIN``). Chạy lại được: ``--lam-lai`` xóa schema rồi nạp lại; không có cờ thì schema đã có sẽ giữ nguyên.
Chỉ in số đếm.

    python tools/chep_v12_sang_pg.py --sqlite var/plhn-thu-T8/kho.sqlite --schema v12_thu_t8 --grant app_ke_toan
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.ha_tang import postgres as pg  # noqa: E402
from kho_tri_thuc.ha_tang.ket_noi import KetNoiPG, kiem_ten_schema, loi_sach  # noqa: E402
from kho_tri_thuc.ha_tang.primitives import DataError  # noqa: E402
from kho_tri_thuc.ha_tang.sao_chep_bang import _cot_pg, chep_sqlite_sang_pg, doi_chieu_noi_dung, khoa_meta_migration, van_tay_pg  # noqa: E402
from kho_tri_thuc.ha_tang import database  # noqa: E402


def _grant(raw, schema: str, role: str) -> bool:
    if not raw.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
        return False
    q = '"' + schema + '"'
    # Quyền hẹp (review lần 2 #20): lõi V12 chỉ DELETE ở cash_account_mappings; nhật ký/migration không cho sửa
    for stmt in (
        f'GRANT USAGE ON SCHEMA {q} TO "{role}"',
        f'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {q} TO "{role}"',
        f'GRANT DELETE ON {q}.cash_account_mappings TO "{role}"',
        f'REVOKE UPDATE ON {q}.activity_log, {q}.audit_events, {q}.schema_migrations, {q}.knowledge_events, {q}.label_events FROM "{role}"',
        f'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA {q} TO "{role}"',
        f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {q} TO "{role}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {q} GRANT SELECT, INSERT, UPDATE ON TABLES TO "{role}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {q} GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO "{role}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {q} GRANT EXECUTE ON FUNCTIONS TO "{role}"',
    ):
        raw.execute(stmt)
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", type=Path, required=True, help="kho.sqlite nguồn (bản sao hoặc kho thử)")
    ap.add_argument("--dsn", default=None, help="DSN chủ CSDL; mặc định KHO_PG_DSN_ADMIN trong .env")
    ap.add_argument("--schema", default="v12")
    ap.add_argument("--grant", default="app_ke_toan", help="vai trò ứng dụng được cấp quyền (bỏ qua nếu chưa có)")
    ap.add_argument("--lam-lai", action="store_true", help="sao lưu schema đã có ra .sqlite rồi xóa và nạp lại (phải kèm --xac-nhan <tên schema>)")
    ap.add_argument("--xac-nhan", default=None, help="gõ lại đúng tên schema để cho phép --lam-lai")
    ap.add_argument("--thu-muc-sao-luu", type=Path, default=Path("var/sao-luu-pg"))
    ap.add_argument("--bao-cao", type=Path, default=None)
    args = ap.parse_args(argv)  # sai cú pháp: argparse tự thoát mã 2
    # Biên runtime (V13 A4): kết nối/migrate/chép/đối chiếu/đóng — lỗi chỉ in bản đã làm sạch, không traceback/DSN/giá trị dòng
    try:
        return _chay(args)
    except Exception as exc:
        print(json.dumps(loi_sach(exc), ensure_ascii=False), file=sys.stderr)
        return 2 if isinstance(exc, DataError) else 3


def _chay(args) -> int:
    kiem_ten_schema(args.schema)  # trước mọi câu DROP (review lần 2 #10)
    if args.lam_lai and args.xac_nhan != args.schema:
        print("--lam-lai cần --xac-nhan <tên schema> gõ lại đúng tên.", file=sys.stderr)
        return 2
    if not args.sqlite.is_file():
        print(f"Không thấy {args.sqlite}", file=sys.stderr)
        return 2
    dsn = args.dsn or pg.dsn_from_env(None, key="KHO_PG_DSN_ADMIN")
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as raw:
        exists = raw.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (args.schema,)).fetchone() is not None
        if exists and args.lam_lai:
            # sao lưu trước khi xóa (review lần 2 #2) — bản .sqlite mở được bằng engine sqlite
            import subprocess
            r = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("sao_luu_pg.py")), "--schema", args.schema,
                                "--dsn", dsn, "--thu-muc", str(args.thu_muc_sao_luu), "--giu", "0"], capture_output=True, text=True)
            if r.returncode != 0:
                print("Sao lưu trước khi làm lại thất bại — không xóa schema.", file=sys.stderr)
                return 1
            raw.execute(f'DROP SCHEMA "{args.schema}" CASCADE')
            exists = False
    src = database.connect(args.sqlite)
    try:
        conn = KetNoiPG(dsn, args.schema)  # tạo schema + migrate nếu chưa có (không tự nạp vì không truyền nhap_tu_sqlite)
        try:
            if exists:
                ket_qua, hanh_dong = None, "GIU_NGUYEN"
            else:
                ket_qua, hanh_dong = chep_sqlite_sang_pg(src, conn), "NAP"
            granted = _grant(conn.raw, args.schema, args.grant) if args.grant else False
            # V13 A5: so nội dung thực (hash tái tính từng bảng), tách khóa workspace_meta do bộ chép thêm (dấu nạp xong)
            theo_bang = doi_chieu_noi_dung(src, van_tay_pg(conn.raw, args.schema), lambda t: _cot_pg(conn.raw, args.schema, t))
            khoa = khoa_meta_migration()
            q = '"' + args.schema + '"'
            meta_migration = sorted(r[0] for r in conn.raw.execute(f"SELECT key FROM {q}.workspace_meta WHERE key IN ({','.join(['%s'] * len(khoa))})", khoa))
        finally:
            conn.close()
    finally:
        src.close()
    khop = all(r["khop"] for r in theo_bang.values())
    report = {"schema": args.schema, "hanh_dong": hanh_dong, "cap_quyen": args.grant if granted else None, "so_bang": len(theo_bang),
              "khop_moi_bang": khop, "bang_lech": sorted(t for t, r in theo_bang.items() if not r["khop"]),
              "tong_dong": {"nguon": sum(r["nguon"] for r in theo_bang.values()), "dich": sum(r["dich"] or 0 for r in theo_bang.values())},
              "metadata_migration": meta_migration, "doi_chieu": "so_dong+hash_noi_dung", "schema_version": database.SCHEMA_VERSION}
    if args.bao_cao:
        args.bao_cao.parent.mkdir(parents=True, exist_ok=True)
        args.bao_cao.write_text(json.dumps({**report, "theo_bang": theo_bang}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if khop else 1


if __name__ == "__main__":
    raise SystemExit(main())
