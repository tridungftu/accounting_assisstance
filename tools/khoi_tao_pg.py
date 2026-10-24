#!/usr/bin/env python3
"""Khởi tạo / nâng cấp schema PostgreSQL theo .env (V13). In số bảng mỗi schema, không in mật khẩu.

  python tools/khoi_tao_pg.py --env .env
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.ha_tang import postgres as pg  # noqa: E402


def doc_env(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():  # chịu được BOM (review C2)
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"')
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", type=Path, default=Path(".env"))
    ap.add_argument("--admin", action="store_true", help="dùng KHO_PG_DSN_ADMIN (chủ CSDL) để chạy migration")
    args = ap.parse_args()
    env = doc_env(args.env)
    key = "KHO_PG_DSN_ADMIN" if args.admin else "KHO_PG_DSN"
    dsn = os.environ.get(key) or env.get(key) or env.get("KHO_PG_DSN")
    if not dsn:
        print(f"Thiếu {key} trong .env", file=sys.stderr)
        return 2
    conn = pg.connect(dsn, autocommit=True)
    try:
        info = pg.integrity(conn)
    finally:
        conn.close()
    print(f"Schema PostgreSQL phiên bản {info['version']} · bảng: {info['tables']} · mở rộng: {info['extensions']} · ok={info['ok']}")
    return 0 if info["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
