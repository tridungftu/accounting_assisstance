# -*- coding: utf-8 -*-
"""
Dòng lệnh (dự phòng — cách dùng chính là giao diện CHAY_PHAN_MEM.bat):

    python -m trich_xuat <file.docx|.doc|thư mục> [...] [--model gpt-oss:20b] [--may-ai 192.168.5.67]
                         [--khong-ra-lai] [--cloud anthropic|openai] [--chay-lai] [--chi-cau-truc]
Kết quả: ket_qua_AI\\trich_xuat\\<ngày_giờ>\\ ; danh mục: ket_qua_AI\\DANH_MUC_HD\\DANH_MUC_HOP_DONG.xlsx
"""
import argparse
import glob
import os
import sys
import threading
import time

from .cau_hinh import doc_cau_hinh, thu_muc_ket_qua
from .danh_muc import doc_yeu_cau_them, load_params
from .lo import LuotChay


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            if (s.encoding or "").lower().replace("-", "") != "utf8":
                s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _utf8()
    cfg = doc_cau_hinh()
    ap = argparse.ArgumentParser(prog="python -m trich_xuat", description="Trích tham số hợp đồng bằng Local AI (v3)")
    ap.add_argument("duong_dan", nargs="+")
    ap.add_argument("--model", default=cfg["model"])
    ap.add_argument("--may-ai", default=cfg["may_ai"])
    ap.add_argument("--khong-ra-lai", action="store_true")
    ap.add_argument("--cloud", choices=["anthropic", "openai"])
    ap.add_argument("--ty-le-cloud", type=float, default=cfg["cloud"]["ty_le"])
    ap.add_argument("--chay-lai", action="store_true", default=os.environ.get("HD_CHAY_LAI", "").strip() in ("1", "co", "có"))
    ap.add_argument("--chi-cau-truc", action="store_true", help="không có AI vẫn tách cấu trúc + dò vị trí")
    a = ap.parse_args(argv)
    files = []
    for p in a.duong_dan:
        if os.path.isdir(p):
            files += sorted(f for f in glob.glob(os.path.join(p, "*")) if f.lower().endswith((".docx", ".doc", ".pdf"))
                            and not os.path.basename(f).startswith("~$"))
        elif p.lower().endswith((".docx", ".doc", ".pdf")):
            files.append(p)
    if not files:
        print("Không có file .docx/.doc nào.")
        return 1
    url = a.may_ai if a.may_ai.startswith("http") else f"http://{a.may_ai}" + ("" if ":" in a.may_ai else ":11434")
    them = []
    for d in {os.path.dirname(os.path.abspath(f)) for f in files}:
        them += doc_yeu_cau_them(d)
    params = load_params(them=them)
    cloud = None
    if a.cloud or cfg["cloud"]["bat"]:
        cloud = {"nha_cung_cap": a.cloud or cfg["cloud"]["nha_cung_cap"], "model": cfg["cloud"]["model"],
                 "ty_le": a.ty_le_cloud}
    nhan = time.strftime("%Y%m%d_%H%M%S")
    out = os.path.join(str(thu_muc_ket_qua()), nhan)
    luot = LuotChay(files, out, params, url, a.model, ra_lai=cfg["ra_lai"] and not a.khong_ra_lai, cloud=cloud,
                    chay_lai=a.chay_lai, chi_cau_truc=a.chi_cau_truc, timeout=cfg.get("timeout_giay", 1800),
                    nhan_luot=nhan)
    print(f"{len(files)} hợp đồng | {len(params)} tham số | model {a.model} | {url}\nKết quả: {out}")
    t = threading.Thread(target=luot.chay, daemon=True)
    t.start()
    da_in = 0
    try:
        while t.is_alive():
            t.join(1)
            s = luot.trang_thai()
            for _, m in s["log"][da_in:]:
                print("  " + m)
            da_in = len(s["log"])
    except KeyboardInterrupt:
        luot.dung.set()
        print("Đang dừng…")
        t.join(30)
    s = luot.trang_thai()
    for _, m in s["log"][da_in:]:
        print("  " + m)
    print(f"\n{s['thong_bao']}")
    for h in s["hd"]:
        print(f"  {h['tt']:<26} {h['file']}" + (f"  OK {h['so_ok']} | cần xem {h['so_vang']}" if h["so_ok"] is not None else "")
              + (f"  {h['loi']}" if h["loi"] else ""))
    return 0 if s["tt"] == "xong" else 2


if __name__ == "__main__":
    sys.exit(main())
