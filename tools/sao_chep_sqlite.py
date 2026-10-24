#!/usr/bin/env python3
"""Sao chép kho SQLite đang có thể mở (WAL) bằng backup API của sqlite3 — bản sao nhất quán — rồi ghi sha256 (review N6).

  python tools/sao_chep_sqlite.py --nguon var/plhn-that/kho.sqlite --dich var/v13/kho-ban-sao.sqlite
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nguon", required=True, type=Path)
    ap.add_argument("--dich", required=True, type=Path)
    a = ap.parse_args()
    a.dich.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(a.nguon.resolve().as_uri() + "?mode=ro", uri=True)
    dst = sqlite3.connect(a.dich)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    h = hashlib.sha256(a.dich.read_bytes()).hexdigest()
    (a.dich.with_suffix(".sha256")).write_text(f"{h}  {a.dich.name}\n", encoding="utf-8")
    print(f"Đã sao chép nhất quán: {a.dich} · {a.dich.stat().st_size} byte · sha256 {h[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
