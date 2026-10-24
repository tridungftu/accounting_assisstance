#!/usr/bin/env python3
"""Probe khả năng THỰC của một Python ứng viên cho app (chạy BÊN TRONG chính Python đó, với đúng môi trường con mà launcher sẽ dùng).

Chỉ thư viện chuẩn; không đọc/ghi tệp, không kết nối mạng/CSDL. In đúng một dòng JSON:
  python [major, minor, micro], isolated, ignore_env, dont_write_bytecode, openpyxl, psycopg (import thật để phát hiện thiếu libpq),
  phu_thuoc_tren_path (mọi thư mục kỳ vọng có trong sys.path), khoi_dong (sitecustomize đã nạp từ đúng thư mục kỳ vọng; null nếu không yêu cầu).
Dùng: python -X utf8 tools/kiem_runtime.py '<json {"phu_thuoc": [...], "khoi_dong": "..."|null}>'
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys


def _chuan(p: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def kiem(expect: dict) -> dict:
    out = {"python": list(sys.version_info[:3]), "executable": sys.executable, "isolated": bool(sys.flags.isolated),
           "ignore_env": bool(sys.flags.ignore_environment), "dont_write_bytecode": bool(sys.dont_write_bytecode),
           "openpyxl": importlib.util.find_spec("openpyxl") is not None}
    try:
        import psycopg  # noqa: F401 — import thật: bản binary thiếu libpq sẽ lỗi ở đây
        out["psycopg"] = True
    except Exception:  # noqa: BLE001
        out["psycopg"] = False
    path = {_chuan(p) for p in sys.path if p}
    out["phu_thuoc_tren_path"] = all(_chuan(d) in path for d in expect.get("phu_thuoc") or [])
    kd = expect.get("khoi_dong")
    if kd:
        mod = sys.modules.get("sitecustomize")
        f = getattr(mod, "__file__", None) if mod else None
        out["khoi_dong"] = bool(f) and _chuan(os.path.dirname(f)) == _chuan(kd)
    else:
        out["khoi_dong"] = None
    return out


if __name__ == "__main__":
    print(json.dumps(kiem(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {})))
